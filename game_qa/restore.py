"""Put the owner's files back after a run, or hold the snapshot when they have changed since.

`compare` says how the user-data folder differs from a snapshot. `restore` puts the folder back, unless the
owner may have played since, in which case it changes nothing and records the snapshot as held. `recover`
finishes the runs a dead driver left behind, `held` names the snapshots waiting for the owner, and `prune`
trims old snapshots (and the store files only they used).

The rules (spec section 5.3):

- A file is changed when its SHA-256 differs from the manifest's. Size and time are never enough.
- The run's end is the journal's `game_exited`, else its last `heartbeat`, else `started`. A changed, added or
  created file modified more than SLACK_SECONDS after it means someone else has used the folder: hold.
- A snapshot is never deleted unless its journal ends in `restored`, and never by the run that made it.
"""

from __future__ import annotations

import contextlib
import fnmatch
import hashlib
import os
import re
import shutil
import stat
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from game_qa import snapshot
from game_qa.snapshot import Entry, Snapshot

# Patterns are relative to the user-data folder and match files directly in the named folder.
HARNESS_CREATED = ("save games/TEST_FAIL_*.v3", "save games/te_qa_*.v3", "tests.txt")
HARNESS_KEPT = ("save games/te_qa_fixture_*.v3",)

# A file counts as modified after the run only if it is newer than the run's end by more than this.
# Journal times have one-second resolution and the game's last write may follow its exit by a moment.
SLACK_SECONDS = 2.0

_TEMP_SUFFIX = ".te_qa_restore.tmp"
_CHUNK = 1024 * 1024
_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_ID_TIME_FORMAT = "%Y%m%dT%H%M%SZ"
_ID_TIME_LENGTH = len("20261110T204035Z")
_BUCKET_NAME = re.compile(r"^[0-9a-f]{2}$")
_BLOB_NAME = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class Diff:
    changed: list[str]  # in the manifest, present now, with other bytes
    missing: list[str]  # in the manifest, gone now
    added_in_set: list[str]  # matches SNAPSHOT_SET, not in the manifest (an autosave pushed in, a new log)
    created: list[str]  # a harness name (HARNESS_CREATED, not HARNESS_KEPT) that was not there before


@dataclass
class Outcome:
    restored: list[str]
    removed: list[str]
    held: bool  # True only if this call recorded the snapshot as held
    reason: str  # "" | "other_game_running" | "modified_after_exit" | "game_still_up" (recover: left alone)


# --- small helpers ---------------------------------------------------------------------------


def _matches(rel: str, patterns: Sequence[str]) -> bool:
    folder, _, name = rel.rpartition("/")
    for pattern in patterns:
        pattern_folder, _, name_pattern = pattern.rpartition("/")
        if folder == pattern_folder and fnmatch.fnmatchcase(name, name_pattern):
            return True
    return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _store_blob(backup_root: Path, sha256: str) -> Path:
    return backup_root / "store" / sha256[:2] / sha256


def _backup_root(snap: Snapshot) -> Path:
    return snap.dir.parent.parent  # <backup_root>/snapshots/<id>


def _live_names(user_data: Path) -> list[str]:
    """Everything that is not a folder directly in the folders the snapshot lists, as `take` scans them."""
    found = []
    for folder in snapshot.LISTED_FOLDERS:
        try:
            iterator = os.scandir(user_data / folder if folder else user_data)
        except (FileNotFoundError, NotADirectoryError):
            continue
        with iterator as entries:
            for entry in entries:
                try:
                    if not entry.is_dir(follow_symlinks=False):
                        found.append(f"{folder}/{entry.name}" if folder else entry.name)
                except FileNotFoundError:  # gone between the listing and the stat
                    continue
    return found


def _mtime(path: Path) -> float | None:
    """The file's modification time (a symlink's target's, or its own if the target is gone); None if absent."""
    try:
        return os.stat(path).st_mtime
    except FileNotFoundError:
        pass
    try:
        return os.lstat(path).st_mtime
    except FileNotFoundError:
        return None


def _parse_time(text) -> datetime | None:
    try:
        return datetime.strptime(text, _TIME_FORMAT).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _reference_time(snap: Snapshot) -> datetime:
    """When the run ended, as far as the journal knows: game_exited, else the last heartbeat, else started.

    A journal with none of those (a snapshot that was taken and never launched) falls back to the time the
    snapshot was taken, which is the earliest the run can have begun. That errs toward holding.
    """
    entries = snapshot.journal(snap)
    for kind in ("game_exited", "heartbeat", "started"):
        times = [t for t in (_parse_time(e.get("at")) for e in entries if e.get("event") == kind) if t]
        if times:
            return times[-1]
    try:
        return datetime.strptime(snap.id[:_ID_TIME_LENGTH], _ID_TIME_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise ValueError(f"nothing says when the run behind snapshot {snap.id!r} ended") from error


def _state(snap: Snapshot) -> str:
    """"restored" or "held" (whichever the journal records last), "unfinished" (started, neither), or ""."""
    names = [entry.get("event") for entry in snapshot.journal(snap)]
    ended = [name for name in names if name in ("restored", "held")]
    if ended:
        return ended[-1]
    return "unfinished" if "started" in names else ""


# --- compare ---------------------------------------------------------------------------------


def compare(snap: Snapshot, user_data: Path) -> Diff:
    """How `user_data` differs from `snap`. Reads every manifest file to hash it; changes nothing.

    Raises FileNotFoundError if `user_data` is not a folder, so that a wrong path is never read as
    "everything was deleted". Subfolders are not looked at, as in `snapshot.take`.
    """
    user_data = Path(user_data)
    if not user_data.is_dir():
        raise FileNotFoundError(f"the user-data folder does not exist: {user_data}")
    changed, missing = [], []
    for rel, entry in sorted(snap.files.items()):
        path = user_data / rel
        try:
            mode = os.stat(path).st_mode
        except (FileNotFoundError, NotADirectoryError):
            missing.append(rel)
            continue
        if not stat.S_ISREG(mode) or _sha256(path) != entry.sha256:
            changed.append(rel)
    # A name in `listing` was there when the snapshot was taken, so it is not the run's, even if it is
    # a symlink or other thing that `files` does not hold.
    new = [name for name in _live_names(user_data) if name not in snap.files and name not in snap.listing]
    added_in_set = sorted(name for name in new if _matches(name, snapshot.SNAPSHOT_SET))
    created = sorted(
        name for name in new if _matches(name, HARNESS_CREATED) and not _matches(name, HARNESS_KEPT)
    )
    return Diff(changed, missing, added_in_set, created)


# --- restore ---------------------------------------------------------------------------------


def _hold_reason(
    snap: Snapshot, user_data: Path, diff: Diff, other_game_running: bool
) -> tuple[str, list[str]]:
    """("", []) if the folder may be put back, else the reason and the files that were modified late."""
    if other_game_running:
        return "other_game_running", []
    present = sorted({*diff.changed, *diff.added_in_set, *diff.created})  # a missing file has no time
    if not present:
        return "", []
    limit = _reference_time(snap).timestamp() + SLACK_SECONDS
    late = []
    for rel in present:
        modified = _mtime(user_data / rel)
        if modified is not None and modified > limit:
            late.append(rel)
    return ("modified_after_exit", late) if late else ("", [])


def _check_store(backup_root: Path, snap: Snapshot, names: Sequence[str]) -> None:
    """Raise unless the store holds every file `names` needs, at the right size."""
    for rel in names:
        entry = snap.files[rel]
        path = _store_blob(backup_root, entry.sha256)
        try:
            size = path.stat().st_size
        except FileNotFoundError as error:
            raise FileNotFoundError(f"the stored copy of {rel!r} is missing: {path}") from error
        if size != entry.size:
            raise OSError(f"the stored copy of {rel!r} has {size} bytes, not {entry.size}: {path}")


def _copy_logs_out(user_data: Path, run_logs_dir: Path) -> None:
    try:
        entries = list(os.scandir(user_data / "logs"))
    except (FileNotFoundError, NotADirectoryError):
        return
    run_logs_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        if entry.is_file():
            shutil.copy2(entry.path, run_logs_dir / entry.name)


def _stage(source: Path, entry: Entry, target: Path) -> Path:
    """Copy a stored file to a temp name beside `target`, checked against its hash, with its recorded time."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + _TEMP_SUFFIX)
    digest = hashlib.sha256()
    try:
        with open(source, "rb") as reader, open(temp, "wb") as writer:
            while chunk := reader.read(_CHUNK):
                digest.update(chunk)
                writer.write(chunk)
            writer.flush()
            os.fsync(writer.fileno())
        if digest.hexdigest() != entry.sha256:
            raise OSError(f"the stored copy of {target.name!r} does not match its recorded hash: {source}")
        os.utime(temp, ns=(entry.mtime_ns, entry.mtime_ns))
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp)
        raise
    return temp


def _put_back(backup_root: Path, snap: Snapshot, names: Sequence[str], user_data: Path) -> None:
    """Stage every file first, so that a bad store file stops the restore before the folder is touched;
    then rename each over its target, so that an interrupted restore never leaves a half-written file."""
    staged: list[tuple[Path, Path]] = []
    try:
        for rel in names:
            target = user_data / rel
            staged.append((_stage(_store_blob(backup_root, snap.files[rel].sha256), snap.files[rel], target), target))
        for temp, target in staged:
            os.replace(temp, target)
    finally:
        for temp, _ in staged:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temp)


def restore(
    snap: Snapshot,
    user_data: Path,
    other_game_running: bool,
    run_logs_dir: Path | None = None,
    now: datetime | None = None,
) -> Outcome:
    """Put `user_data` back as `snap` found it, or hold.

    Holds, changing nothing, if another game is running or a changed, added or created file was modified
    more than SLACK_SECONDS after the run's end; records `held` and says why. Otherwise copies the changed and
    missing files back from the store with their recorded times, removes the files the run added or created,
    and records `restored` with the names. With `run_logs_dir` the live `logs/*` are copied there first.

    Raises, recording neither `restored` nor `held`, if the folder is missing or a stored file is missing,
    the wrong size or damaged. The store is checked before the first change. `now` stamps the journal entry.
    """
    user_data = Path(user_data)
    diff = compare(snap, user_data)
    reason, late = _hold_reason(snap, user_data, diff, other_game_running)
    if reason:
        snapshot.record(snap, "held", now=now, reason=reason, **({"files": late} if late else {}))
        return Outcome([], [], True, reason)

    to_restore = sorted([*diff.changed, *diff.missing])
    to_remove = sorted([*diff.added_in_set, *diff.created])
    backup_root = _backup_root(snap)
    _check_store(backup_root, snap, to_restore)
    if run_logs_dir is not None:
        _copy_logs_out(user_data, Path(run_logs_dir))
    _put_back(backup_root, snap, to_restore, user_data)
    for rel in to_remove:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(user_data / rel)
    snapshot.record(snap, "restored", now=now, restored=to_restore, removed=to_remove)
    return Outcome(to_restore, to_remove, False, "")


# --- unfinished runs -------------------------------------------------------------------------


def unfinished(backup_root: Path) -> list[Snapshot]:
    """Snapshots whose run `started` and was neither `restored` nor `held`, oldest first."""
    return [snap for snap in snapshot.all_snapshots(backup_root) if _state(snap) == "unfinished"]


def held(backup_root: Path) -> list[Snapshot]:
    """Snapshots held for the owner (their journal's last verdict is `held`), oldest first."""
    return [snap for snap in snapshot.all_snapshots(backup_root) if _state(snap) == "held"]


def recover(
    backup_root: Path,
    user_data: Path,
    other_game_running: bool,
    own_game_up: Callable[[dict], bool],
) -> list[tuple[str, Outcome]]:
    """Run `restore` for each unfinished snapshot, oldest first.

    `own_game_up` is given the snapshot's `started` journal entry (with the game's pid and creation time).
    A run it says is still up is left untouched, with nothing recorded, and reported with reason
    "game_still_up" and held False. An error from `restore` propagates; runs already dealt with stay so.
    """
    results = []
    for snap in unfinished(backup_root):
        started = [entry for entry in snapshot.journal(snap) if entry.get("event") == "started"][-1]
        if own_game_up(started):
            results.append((snap.id, Outcome([], [], False, "game_still_up")))
        else:
            results.append((snap.id, restore(snap, user_data, other_game_running)))
    return results


# --- prune -----------------------------------------------------------------------------------


def _remove_snapshot(snap: Snapshot) -> None:
    # The manifest goes first: a folder without one no longer loads, so a removal cut short is still a removal.
    with contextlib.suppress(FileNotFoundError):
        os.unlink(snap.dir / snapshot.MANIFEST_NAME)
    shutil.rmtree(snap.dir, ignore_errors=True)


def _sweep_store(backup_root: Path) -> None:
    """Delete store files that no snapshot on disk names. Does nothing if that cannot be known."""
    named: set[str] = set()
    try:
        children = list(os.scandir(backup_root / "snapshots"))
    except (FileNotFoundError, NotADirectoryError):
        children = []
    for child in children:
        if not child.is_dir():
            continue
        try:
            snap = snapshot.load(Path(child.path))
        except FileNotFoundError:
            continue  # no manifest: a snapshot still being written, or one that never finished; it names nothing
        except (OSError, ValueError):
            return  # a manifest that will not load may name anything
        named.update(entry.sha256 for entry in snap.files.values())
    try:
        buckets = list(os.scandir(backup_root / "store"))
    except (FileNotFoundError, NotADirectoryError):
        return
    for bucket in buckets:
        if not bucket.is_dir(follow_symlinks=False) or not _BUCKET_NAME.match(bucket.name):
            continue
        for blob in os.scandir(bucket.path):
            if (
                blob.is_file(follow_symlinks=False)
                and _BLOB_NAME.match(blob.name)
                and blob.name[:2] == bucket.name
                and blob.name not in named
            ):
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(blob.path)


def prune(backup_root: Path, keep: int = 5, current: str | None = None) -> list[str]:
    """Remove the oldest finished snapshots beyond `keep`; return their ids, oldest first.

    Only snapshots whose journal ends in `restored` can go. `current` (the run's own snapshot, which the
    caller has just taken) takes one of the `keep` places whatever its journal says and is never removed;
    held and unfinished snapshots are never removed and take no place. Then the store files that no
    remaining manifest names are deleted. Call it when no other `take` is in progress: a snapshot being
    written has stored its files but not yet named them.
    """
    backup_root = Path(backup_root)
    snaps = snapshot.all_snapshots(backup_root)
    states = {snap.id: _state(snap) for snap in snaps}
    kept_places = [snap for snap in snaps if snap.id == current or states[snap.id] == "restored"]
    removable = [snap for snap in kept_places if snap.id != current and states[snap.id] == "restored"]
    victims = removable[: max(len(kept_places) - keep, 0)]
    for snap in victims:
        _remove_snapshot(snap)
    _sweep_store(backup_root)
    return [snap.id for snap in victims]
