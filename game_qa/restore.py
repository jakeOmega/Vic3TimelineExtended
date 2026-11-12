"""Put the owner's files back after a run, or hold the snapshot when they have changed since.

`compare` says how the user-data folder differs from a snapshot. `restore` puts the folder back, unless the
owner may have played since, in which case it changes nothing and records the snapshot as held. `recover`
finishes the runs a dead driver left behind, `held` names the snapshots waiting for the owner, and `prune`
trims old snapshots (and the store files only they used).

The rules (spec section 5.3):

- A file is changed when its SHA-256 differs from the manifest's. Size and time are never enough.
- The run's end is the journal's `game_exited`, else its last `heartbeat`, else `started`. A changed, added or
  created file modified more than SLACK_SECONDS after it means someone else has used the folder: hold. Logs
  (`logs/*`) are never judged: the game writes them to the last moment, and the saves tell the story.
- A file whose bytes are still the snapshot's is never rewritten. If the run moved its time (the game writes
  `pdx_settings.json` again at launch with the same bytes), a restore that finishes puts the snapshot's time back
  on it, judging the time as the hold rule does: one later than the run's end by more than SLACK_SECONDS is
  someone else's and stays, as does every time when the journal gives no end.
- Journal times come from the backup drive's clock (see `snapshot.record`), as file times do.
- A snapshot is never deleted unless its journal ends in `restored` (or says nothing at all), and never by
  the run that made it.
"""

from __future__ import annotations

import contextlib
import fnmatch
import hashlib
import os
import re
import shutil
import stat
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
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

# prune() leaves alone every store file younger than this, named or not: a take in another session
# copies its files into the store before its manifest names them.
SWEEP_MIN_AGE_SECONDS = 24 * 60 * 60

# Where restore() keeps the run's logs when it is not told a folder: beside the snapshot's journal.
RUN_LOGS_NAME = "run_logs"

_TEMP_SUFFIX = ".te_qa_restore.tmp"
_CHUNK = 1024 * 1024
_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_BUCKET_NAME = re.compile(r"^[0-9a-f]{2}$")
_BLOB_NAME = re.compile(r"^[0-9a-f]{64}$")
# In `save games/` only the game's own rotation names may be taken for something the run pushed in. OneDrive
# makes conflict copies such as `autosave-Manfred.v3` and `autosave_1-Manfred.v3`; they are the owner's.
_ROTATION_NAME = re.compile(r"^autosave(_\d+|_exit)?\.v3$")


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
    # "" | "other_game_running" | "modified_after_exit" | "no_reference_time" | "modified_during_restore"
    # | "already_restored" (another game is running and the journal already ends in `restored`: left as it is,
    # nothing recorded, held False). recover() adds "game_still_up" (left alone, nothing recorded) and
    # "error: <message>" (restore, or own_game_up, raised). The command line (game_qa/__main__.py) builds
    # Outcomes too: held "other_game_ran" and "unwatched_stretch" (recorded), and, with nothing recorded and
    # held False, "launch_in_flight" and "watch_still_recording" (its `recover`, which runs its own loop).
    reason: str
    # Files left as they were, bytes and all, that got the snapshot's modification time back (`_retime`).
    retimed: list[str] = field(default_factory=list)


# A file's size and mtime_ns as compare saw them, or None if it was absent.
_Signature = tuple[int, int] | None


# --- small helpers ---------------------------------------------------------------------------


def _matches(rel: str, patterns: Sequence[str]) -> bool:
    folder, _, name = rel.rpartition("/")
    for pattern in patterns:
        pattern_folder, _, name_pattern = pattern.rpartition("/")
        if folder == pattern_folder and fnmatch.fnmatchcase(name, name_pattern):
            return True
    return False


def _is_pushed_in(name: str) -> bool:
    """A name in SNAPSHOT_SET that the run could have added (and that restore may therefore remove)."""
    if not _matches(name, snapshot.SNAPSHOT_SET):
        return False
    folder, _, base = name.rpartition("/")
    return folder != "save games" or bool(_ROTATION_NAME.match(base))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _signature(path: Path, follow: bool = True) -> _Signature:
    try:
        st = os.stat(path) if follow else os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    return (st.st_size, st.st_mtime_ns)


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


def _reference_time(snap: Snapshot) -> datetime | None:
    """When the run ended, as far as the journal knows: game_exited, else the last heartbeat, else started.

    None if the journal has none of them. No other clock is borrowed: the time in the snapshot's id is the
    machine's, and the hold rule compares only the drive's times.
    """
    entries = snapshot.journal(snap)
    for kind in ("game_exited", "heartbeat", "started"):
        times = [t for t in (_parse_time(e.get("at")) for e in entries if e.get("event") == kind) if t]
        if times:
            return times[-1]
    return None


def _state(snap: Snapshot) -> str:
    """What the journal says about the run.

    "restored" or "held" (whichever it records last); "unfinished" (started, and neither); "idle" (no journal,
    or a zero-byte one: taken and never launched, nothing will ever restore it); "" for anything else, that is
    a journal with events but no start, or one that exists but yields no event (a write cut short). A snapshot
    in state "" is neither pruned nor recovered.
    """
    try:
        size = os.stat(snap.dir / snapshot.JOURNAL_NAME).st_size
    except FileNotFoundError:
        return "idle"
    if size == 0:
        return "idle"
    names = [entry.get("event") for entry in snapshot.journal(snap)]
    ended = [name for name in names if name in ("restored", "held")]
    if ended:
        return ended[-1]
    return "unfinished" if "started" in names else ""


# --- compare ---------------------------------------------------------------------------------


def _compare(snap: Snapshot, user_data: Path) -> tuple[Diff, dict[str, _Signature]]:
    """`compare`, plus what it saw of every file it may later replace or remove, for the last-moment check."""
    if not user_data.is_dir():
        raise FileNotFoundError(f"the user-data folder does not exist: {user_data}")
    seen: dict[str, _Signature] = {}
    changed, missing = [], []
    for rel, entry in sorted(snap.files.items()):
        path = user_data / rel
        try:
            st = os.stat(path)
        except (FileNotFoundError, NotADirectoryError):
            seen[rel] = None
            missing.append(rel)
            continue
        seen[rel] = (st.st_size, st.st_mtime_ns)
        if not stat.S_ISREG(st.st_mode) or _sha256(path) != entry.sha256:
            changed.append(rel)
    # A name in `listing` was there when the snapshot was taken, so it is not the run's, even if it is a
    # symlink or other thing that `files` does not hold. A leftover temp of ours is nobody's.
    new = [
        name
        for name in _live_names(user_data)
        if name not in snap.files and name not in snap.listing and not name.endswith(_TEMP_SUFFIX)
    ]
    added_in_set = sorted(name for name in new if _is_pushed_in(name))
    created = sorted(
        name for name in new if _matches(name, HARNESS_CREATED) and not _matches(name, HARNESS_KEPT)
    )
    for name in (*added_in_set, *created):
        seen[name] = _signature(user_data / name, follow=False)
    return Diff(changed, missing, added_in_set, created), seen


def compare(snap: Snapshot, user_data: Path) -> Diff:
    """How `user_data` differs from `snap`. Reads every manifest file to hash it; changes nothing.

    Raises FileNotFoundError if `user_data` is not a folder, so that a wrong path is never read as
    "everything was deleted". Subfolders are not looked at, as in `snapshot.take`. In `save games/` only
    the game's rotation names (`autosave.v3`, `autosave_2.v3`, `autosave_exit.v3`) can be `added_in_set`.
    """
    return _compare(snap, Path(user_data))[0]


# --- restore ---------------------------------------------------------------------------------


def _hold_reason(snap: Snapshot, user_data: Path, diff: Diff) -> tuple[str, list[str]]:
    """("", []) if the folder may be put back, else the reason and the files that were modified late.

    Judged are the changed, added and created files, except logs: a missing file has no time, and the game
    writes logs up to its last moment. With nothing to judge there is nothing to hold for, even without a
    reference time.
    """
    judged = sorted(
        name for name in {*diff.changed, *diff.added_in_set, *diff.created} if not name.startswith("logs/")
    )
    if not judged:
        return "", []
    reference = _reference_time(snap)
    if reference is None:
        return "no_reference_time", []
    limit = reference.timestamp() + SLACK_SECONDS
    late = []
    for rel in judged:
        modified = _mtime(user_data / rel)
        if modified is not None and modified > limit:
            late.append(rel)
    return ("modified_after_exit", late) if late else ("", [])


def _hold(snap: Snapshot, reason: str, now: datetime | None, **fields: list[str]) -> Outcome:
    fields = {name: value for name, value in fields.items() if value}
    snapshot.record(snap, "held", now=now, reason=reason, **fields)
    return Outcome(list(fields.get("restored", [])), list(fields.get("removed", [])), True, reason)


def _remove_stale_temps(user_data: Path) -> None:
    """Delete the temp files of a restore that was killed; they are this module's own."""
    for rel in _live_names(user_data):
        if rel.endswith(_TEMP_SUFFIX):
            with contextlib.suppress(FileNotFoundError):
                os.unlink(user_data / rel)


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


def _copy_logs_out(snap: Snapshot, user_data: Path, run_logs_dir: Path) -> None:
    """Copy every live `logs/*` file to `run_logs_dir`, which is made only if there is something to copy.

    A log that is already there is copied again, except when the live file is by now the snapshot's own
    version (a restore that ran before put the owner's log back): that copy is the run's and stays.
    """
    try:
        entries = sorted(os.scandir(user_data / "logs"), key=lambda entry: entry.name)
    except (FileNotFoundError, NotADirectoryError):
        return
    for entry in entries:
        if not entry.is_file() or entry.name.endswith(_TEMP_SUFFIX):
            continue
        target = run_logs_dir / entry.name
        if target.exists():
            owners = snap.files.get(f"logs/{entry.name}")
            if owners is not None and _sha256(Path(entry.path)) == owners.sha256:
                continue
        run_logs_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry.path, target)


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


def _put_back(
    backup_root: Path, snap: Snapshot, names: Sequence[str], user_data: Path, seen: dict[str, _Signature]
) -> tuple[list[str], str | None]:
    """Put `names` back; return the ones done and, if it stopped early, the file that had changed.

    Stages every file first, so that a bad store file stops the restore before the folder is touched; then
    renames each over its target, so that an interrupted restore never leaves a half-written file. Just
    before each rename the target is looked at again: if it is not as `compare` saw it, the restore stops.
    """
    staged: list[tuple[str, Path, Path]] = []
    done: list[str] = []
    try:
        for rel in names:
            target = user_data / rel
            entry = snap.files[rel]
            staged.append((rel, _stage(_store_blob(backup_root, entry.sha256), entry, target), target))
        for rel, temp, target in staged:
            if _signature(target) != seen[rel]:
                return done, rel
            os.replace(temp, target)
            done.append(rel)
    finally:
        for _, temp, _ in staged:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temp)
    return done, None


def _remove(names: Sequence[str], user_data: Path, seen: dict[str, _Signature]) -> tuple[list[str], str | None]:
    """Remove `names`; return the ones done and, if it stopped early, the file that had changed."""
    done: list[str] = []
    for rel in names:
        path = user_data / rel
        current = _signature(path, follow=False)
        if current is None:
            continue  # already gone
        if current != seen[rel]:
            return done, rel
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path)
        done.append(rel)
    return done, None


def _retouched(snap: Snapshot, diff: Diff, seen: dict[str, _Signature], logs: bool) -> list[str]:
    """The manifest's files that the run wrote again with the same bytes: `compare` found their content the
    snapshot's, and their time is later than the manifest's but not later than the run's end by more than
    SLACK_SECONDS. A later time is someone else's, as in the hold rule, and without a recorded end none can be
    told from the run's, so then there are none. With `logs` False, `logs/` is left out."""
    reference = _reference_time(snap)
    if reference is None:
        return []
    limit_ns = int((reference.timestamp() + SLACK_SECONDS) * 1_000_000_000)
    differ = {*diff.changed, *diff.missing}
    names = []
    for rel, entry in sorted(snap.files.items()):
        signature = seen.get(rel)
        if rel in differ or signature is None or (not logs and rel.startswith("logs/")):
            continue
        size, mtime_ns = signature
        if size == entry.size and entry.mtime_ns < mtime_ns <= limit_ns:
            names.append(rel)
    return names


def _retime(snap: Snapshot, names: Sequence[str], user_data: Path, seen: dict[str, _Signature]) -> list[str]:
    """Give `names` (from `_retouched`) the modification times the snapshot recorded; return the ones done.

    No byte is written. Just before, each file is looked at again, itself and not what a link points to: one
    that is no longer a regular file of the size and time `compare` saw has been written since, and is left
    with the time it has. Once the time is set the file is hashed again: if someone wrote other bytes in that
    moment, it gets the present time instead, so that no file is left with the snapshot's size and time over
    other bytes (`snapshot.take` trusts that pair for a file it has stored before). A file whose time cannot be
    set is left too: the time is a courtesy, and never a reason to fail or hold a restore whose files are back.
    """
    done: list[str] = []
    for rel in names:
        path = user_data / rel
        entry = snap.files[rel]
        try:
            st = os.lstat(path)
            if not stat.S_ISREG(st.st_mode) or (st.st_size, st.st_mtime_ns) != seen[rel]:
                continue
            os.utime(path, ns=(st.st_atime_ns, entry.mtime_ns), follow_symlinks=False)
            if _sha256(path) != entry.sha256:
                os.utime(path, follow_symlinks=False)
                continue
        except OSError:
            continue
        done.append(rel)
    return done


def restore(
    snap: Snapshot,
    user_data: Path,
    other_game_running: bool,
    run_logs_dir: Path | None = None,
    now: datetime | None = None,
    logs: bool = True,
) -> Outcome:
    """Put `user_data` back as `snap` found it, or hold.

    A snapshot whose journal already ends in `restored` is left as it is while another game is running:
    `Outcome([], [], False, "already_restored")`, nothing recorded (it must not turn up as held).

    Holds, changing nothing, if another game is running (checked before any file is read) or a changed,
    added or created file, logs excepted, was modified more than SLACK_SECONDS after the run's end, or such a
    file exists and the journal gives no end at all (reasons `other_game_running`, `modified_after_exit`,
    `no_reference_time`). A hold records `held` with the reason, and the late files when there are some.

    Otherwise: clears the leftover temp files of a killed restore; copies the live `logs/*` to `run_logs_dir`
    (by default `<snapshot folder>/run_logs`); copies the changed and missing files back from the store with
    their recorded times; removes the files the run added or created; puts the recorded time back on the files
    the run wrote again with the same bytes (`_retouched`; listed as `retimed`, in the Outcome and, when there
    are some, in the journal entry); records `restored` with the names.

    Just before each change the file is looked at again. If it is no longer as it was compared, the restore
    stops, records `held` with the reason `modified_during_restore` and the file, and returns what it had
    done so far; those files stay put back, since they are the owner's own bytes.

    Raises, recording neither `restored` nor `held`, if the folder is missing or a stored file is missing,
    the wrong size or damaged. The store is checked before the first change. `now` stamps the journal entry.
    With `logs` False, `logs/` is left alone entirely: nothing is copied out, put back or removed there.
    """
    user_data = Path(user_data)
    if other_game_running:
        if _state(snap) == "restored":
            return Outcome([], [], False, "already_restored")  # finished: another game does not make it held
        return _hold(snap, "other_game_running", now)
    diff, seen = _compare(snap, user_data)
    if not logs:
        diff = Diff(*([n for n in part if not n.startswith("logs/")] for part in vars(diff).values()))
    reason, late = _hold_reason(snap, user_data, diff)
    if reason:
        return _hold(snap, reason, now, files=late)

    _remove_stale_temps(user_data)
    to_restore = sorted([*diff.changed, *diff.missing])
    to_remove = sorted([*diff.added_in_set, *diff.created])
    backup_root = _backup_root(snap)
    _check_store(backup_root, snap, to_restore)
    if logs:
        _copy_logs_out(snap, user_data, Path(run_logs_dir) if run_logs_dir is not None else snap.dir / RUN_LOGS_NAME)
    restored, changed_file = _put_back(backup_root, snap, to_restore, user_data, seen)
    removed: list[str] = []
    if changed_file is None:
        removed, changed_file = _remove(to_remove, user_data, seen)
    if changed_file is not None:
        return _hold(snap, "modified_during_restore", now, files=[changed_file], restored=restored, removed=removed)
    retimed = _retime(snap, _retouched(snap, diff, seen, logs), user_data, seen)
    done = {"restored": restored, "removed": removed, **({"retimed": retimed} if retimed else {})}
    snapshot.record(snap, "restored", now=now, **done)
    return Outcome(restored, removed, False, "", retimed)


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
    """Run `restore` for each unfinished snapshot, newest first, like a stack.

    A later snapshot is taken over the leftovers of an earlier run, so its manifest holds them; unwinding
    newest first removes one layer at a time and ends in the oldest snapshot's files. Oldest first would end
    in the leftovers.

    `own_game_up` is asked about every unfinished snapshot first, with that snapshot's last `started` journal
    entry (the game's pid and creation time). If it says any run's game is still up, nothing is restored:
    every unfinished snapshot is reported with reason "game_still_up" and held False, and nothing is recorded.
    If it raises for a snapshot (a `started` entry it cannot read), nothing is restored either, since that
    run's game cannot be ruled out: the result is that snapshot alone, with reason "error: <message>".

    Then the snapshots are restored one by one, and the unwinding stops at the first that does not finish:
    - a hold: the snapshot is reported (held True, with its reason) and the older ones stay unfinished for a
      later call;
    - an error from `restore`: the snapshot is reported with held False and reason "error: <message>", its
      journal untouched, and the older ones stay unfinished.
    The results gathered before the stop are kept.
    """
    runs = []
    for snap in reversed(unfinished(backup_root)):
        started = [entry for entry in snapshot.journal(snap) if entry.get("event") == "started"][-1]
        try:
            up = own_game_up(started)
        except Exception as error:
            return [(snap.id, Outcome([], [], False, f"error: {error}"))]
        runs.append((snap, up))
    if any(up for _, up in runs):
        return [(snap.id, Outcome([], [], False, "game_still_up")) for snap, _ in runs]
    results = []
    for snap, _ in runs:
        try:
            outcome = restore(snap, user_data, other_game_running)
        except Exception as error:
            results.append((snap.id, Outcome([], [], False, f"error: {error}")))
            break
        results.append((snap.id, outcome))
        if outcome.held:
            break
    return results


# --- prune -----------------------------------------------------------------------------------


def _remove_snapshot(snap: Snapshot) -> None:
    # The manifest goes first: a folder without one no longer loads, so a removal cut short is still a removal.
    with contextlib.suppress(FileNotFoundError):
        os.unlink(snap.dir / snapshot.MANIFEST_NAME)
    shutil.rmtree(snap.dir, ignore_errors=True)


def _sweep_store(backup_root: Path) -> None:
    """Delete store files that no snapshot on disk names and that are older than SWEEP_MIN_AGE_SECONDS.

    Does nothing if what the snapshots name cannot be known.
    """
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
    cutoff = time.time() - SWEEP_MIN_AGE_SECONDS
    for bucket in buckets:
        if not bucket.is_dir(follow_symlinks=False) or not _BUCKET_NAME.match(bucket.name):
            continue
        for blob in os.scandir(bucket.path):
            if not (_BLOB_NAME.match(blob.name) and blob.name[:2] == bucket.name and blob.name not in named):
                continue
            with contextlib.suppress(FileNotFoundError):
                if blob.is_file(follow_symlinks=False) and blob.stat(follow_symlinks=False).st_mtime < cutoff:
                    os.unlink(blob.path)


def prune(backup_root: Path, keep: int = 5, current: str | None = None) -> list[str]:
    """Remove the oldest finished snapshots beyond `keep`; return their ids, oldest first.

    Finished means the journal ends in `restored`, or is missing or empty (taken and never launched). `current`
    (the run's own snapshot, which the caller has just taken) takes one of the `keep` places whatever its
    journal says and is never removed; held and unfinished snapshots, and any whose journal exists but does not
    parse, are never removed and take no place. Then the store files that no remaining manifest names and
    that are older than SWEEP_MIN_AGE_SECONDS are deleted: a take being written by another session has stored
    its files but not yet named them.
    """
    backup_root = Path(backup_root)
    snaps = snapshot.all_snapshots(backup_root)
    finished = {snap.id for snap in snaps if _state(snap) in ("restored", "idle")}
    kept_places = [snap for snap in snaps if snap.id == current or snap.id in finished]
    removable = [snap for snap in kept_places if snap.id != current and snap.id in finished]
    victims = removable[: max(len(kept_places) - keep, 0)]
    for snap in victims:
        _remove_snapshot(snap)
    _sweep_store(backup_root)
    return [snap.id for snap in victims]
