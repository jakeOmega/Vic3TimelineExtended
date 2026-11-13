"""Snapshots of the owner's saves, settings and logs, kept in a content store.

Layout under the backup root:

    store/<sha256[:2]>/<sha256>     one copy of each distinct file content, shared by every snapshot
    snapshots/<id>/manifest.json    the files taken (size, mtime, hash), the listing of the folders, and the size
                                    and mtime of everything listed in `save games/` (`save_stats`)
    snapshots/<id>/journal.jsonl    what the run did: armed, playset, playset_written, started, watching,
                                    watch_resumed, heartbeat, look_failed, other_game, game_exited,
                                    playset_restored, restored, held
    snapshots/<id>/.clock           a marker whose modification time is the drive's clock (journal times)
    snapshots/.clock                the same, for the id of a new snapshot

A snapshot is complete once its manifest exists. The manifest is written last, by rename from a
temp name, so a half-written snapshot has no manifest and never loads. The store is only ever
added to here, so every snapshot stays restorable on its own while others are pruned.
"""

from __future__ import annotations

import contextlib
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

# Patterns are relative to the user-data folder and match files directly in the named folder.
SNAPSHOT_SET = (
    "save games/autosave*.v3",
    "continue_game.json",
    "console_history.txt",
    "pdx_settings.json",
    "content_load.json",
    "logs/*",
)

# `Snapshot.listing` holds every file directly in these folders ("" is the user-data root).
LISTED_FOLDERS = ("", "save games", "logs")
# The folder whose listed entries also get their size and time recorded (`Snapshot.save_stats`): the owner's own
# saves there are never copied (they run to hundreds of MB), so a change to one is told by these alone (#1725).
SAVE_FOLDER = "save games"

# take() refuses unless the backup drive has the bytes it must copy plus this much to spare.
FREE_SPACE_MARGIN = 1024**3

MANIFEST_VERSION = 1
MANIFEST_NAME = "manifest.json"
JOURNAL_NAME = "journal.jsonl"
CLOCK_MARKER = ".clock"  # rewritten by record() to read the drive's clock; not part of a snapshot's content

_ID_PATTERN = re.compile(r"^(\d{8}T\d{6}Z)(?:-(\d+))?$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CHUNK = 1024 * 1024
_READ_ATTEMPTS = 3


class SaveNotListed(ValueError):
    """A save named for a run (`extra`) that `save games/` does not list under that name (`unlisted_save`)."""


class BackupRootError(Exception):
    """The backup folder cannot be used: its parent is missing, it is not a folder, it lies
    inside the user-data folder, or the drive is too full."""


@dataclass(frozen=True)
class Entry:
    size: int
    mtime_ns: int
    sha256: str


@dataclass
class Snapshot:
    id: str  # UTC, "20261110T204035Z"; a second snapshot in the same second gets "-2"
    dir: Path  # <backup_root>/snapshots/<id>
    files: dict[str, Entry]  # user-data-relative POSIX path -> entry
    listing: frozenset[str]  # every file directly in user_data, save games/ and logs/ when taken
    # (st_size, st_mtime_ns) of each `listing` name in save games/, from the same lstat as the listing; None for a
    # manifest written before they were recorded, or one whose record does not read (see `load`).
    save_stats: dict[str, tuple[int, int]] | None = None


# --- small helpers ---------------------------------------------------------------------------


def _utc(now: datetime | None) -> datetime:
    """`now` as an aware UTC time; a naive one is taken to be UTC already."""
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _clean_relative(text: str) -> str:
    """A user-data-relative POSIX path in its plain form; refuses absolute paths and `..`."""
    pure = PurePosixPath(text)
    if not pure.parts or pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"not a path inside the user-data folder: {text!r}")
    return pure.as_posix()


def _blob_path(store: Path, sha256: str) -> Path:
    return store / sha256[:2] / sha256


def _blob_is_intact(store: Path, entry: Entry) -> bool:
    """True if the store holds this entry's content at the right size (a cheap check, not a rehash)."""
    try:
        return _blob_path(store, entry.sha256).stat().st_size == entry.size
    except OSError:
        return False


def _scan_folder(user_data: Path, folder: str) -> dict[str, os.stat_result]:
    """Everything directly in `folder` except subfolders, keyed by relative path, with its own lstat.

    Symlinks and other non-regular entries are kept so that `listing` errs toward naming too much:
    a name missing from it reads, at restore time, as something the run created.
    """
    found: dict[str, os.stat_result] = {}
    try:
        iterator = os.scandir(user_data / folder if folder else user_data)
    except (FileNotFoundError, NotADirectoryError):
        return found
    with iterator as entries:
        for entry in entries:
            try:
                if not entry.is_dir(follow_symlinks=False):
                    found[f"{folder}/{entry.name}" if folder else entry.name] = entry.stat(follow_symlinks=False)
            except FileNotFoundError:  # gone between the listing and the stat
                continue
    return found


def unlisted_save(user_data: Path, rel: str, scan: dict[str, os.stat_result] | None = None) -> str | None:
    """Why `rel`, a save directly in `save games/` that a run will load, may not be named so; None if it may.

    It may when the folder lists an entry of that name, compared with str.lower(): the owner's drive matches names
    in any letter case, so `--save Mine` is mine.v3. The drive also answers to names it does not list, such as a
    short 8.3 name (`FRENCH~1.V3` for `french republic_1867_08_16.v3`). Such a save would be the run's under one
    name and an owner's save in the listing under the other, so `restore` would compare it twice: by its hash, and
    by a size and time that its own put-back (a time set from WSL keeps whole seconds) would then never match. It is
    refused, naming the listed entry that is the same file (the same device and inode) when there is one. `scan` is
    `_scan_folder(user_data, SAVE_FOLDER)` when the caller has it. A path not directly in `save games/` is not
    judged here."""
    folder, _, name = rel.rpartition("/")
    if folder != SAVE_FOLDER:
        return None
    scan = _scan_folder(user_data, SAVE_FOLDER) if scan is None else scan
    if name.lower() in {listed.rpartition("/")[2].lower() for listed in scan}:
        return None
    why = (f"{rel!r} is not a name {SAVE_FOLDER}/ lists (the drive also answers to names it does not list, such as "
           "a short 8.3 name): name the save as the folder lists it")
    try:
        target = os.lstat(user_data / rel)
    except OSError:
        return why
    same = sorted(listed.rpartition("/")[2] for listed, st in scan.items()
                  if target.st_ino and (st.st_dev, st.st_ino) == (target.st_dev, target.st_ino))
    return why + (f": it is the same file as {same[0]!r}" if same else "")


def _check_backup_root(user_data: Path, backup_root: Path) -> None:
    if not backup_root.parent.is_dir():
        raise BackupRootError(f"the folder that should hold the backups does not exist: {backup_root.parent}")
    if backup_root.exists() and not backup_root.is_dir():
        raise BackupRootError(f"the backup root is not a folder: {backup_root}")
    resolved_root, resolved_user = backup_root.resolve(), user_data.resolve()
    if resolved_root == resolved_user or resolved_user in resolved_root.parents:
        raise BackupRootError(f"the backup root {backup_root} lies inside the user-data folder {user_data}")


def _store_file(path: Path, store: Path) -> Entry:
    """Copy `path` into the store under its content hash and return its entry.

    The hash is taken from the bytes as they are copied, so a blob's name always matches its
    content. If the file changes while it is read, read it again; if it will not settle, fail.
    """
    for _ in range(_READ_ATTEMPTS):
        before = os.stat(path)
        digest, size = hashlib.sha256(), 0
        fd, temp_name = tempfile.mkstemp(dir=store, prefix=".incoming-")
        try:
            with os.fdopen(fd, "wb") as target, open(path, "rb") as source:
                while chunk := source.read(_CHUNK):
                    digest.update(chunk)
                    target.write(chunk)
                    size += len(chunk)
                target.flush()
                os.fsync(target.fileno())
            after = os.stat(path)
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or size != after.st_size:
                continue
            sha256 = digest.hexdigest()
            blob = _blob_path(store, sha256)
            blob.parent.mkdir(exist_ok=True)
            os.replace(temp_name, blob)  # also over a blob already there: the fresh, fsynced copy heals a bad one
            return Entry(size=size, mtime_ns=after.st_mtime_ns, sha256=sha256)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temp_name)
    raise OSError(f"{path} kept changing while it was being read")


def _new_snapshot_dir(snapshots: Path, base_id: str, first_number: int = 1) -> tuple[str, Path]:
    """Create the first free `<base_id>`, `<base_id>-2`, `<base_id>-3`, ... folder, from number `first_number` on."""
    number = first_number
    while True:
        snapshot_id = base_id if number == 1 else f"{base_id}-{number}"
        folder = snapshots / snapshot_id
        try:
            folder.mkdir()
        except FileExistsError:
            number += 1
            continue
        return snapshot_id, folder


def _ordered_id(taken: datetime, previous: Sequence[Snapshot]) -> tuple[str, int]:
    """The id's time part and the number to start numbering from, so that the new id sorts after every
    existing snapshot's. If `taken` is not later than the newest one's time (a clock that stands still or
    was stepped back), the newest one's time is used again with the next number."""
    base_id = taken.strftime("%Y%m%dT%H%M%SZ")
    if previous:
        match = _ID_PATTERN.match(previous[-1].id)
        if match and base_id <= match.group(1):
            return match.group(1), int(match.group(2) or 1) + 1
    return base_id, 1


def _write_manifest(folder: Path, taken: datetime, files: dict[str, Entry], listing: frozenset[str],
                    save_stats: dict[str, tuple[int, int]]) -> None:
    manifest = {
        "version": MANIFEST_VERSION,
        "created": taken.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": {
            name: {"size": entry.size, "mtime_ns": entry.mtime_ns, "sha256": entry.sha256}
            for name, entry in files.items()
        },
        "listing": sorted(listing),
        # A key older code does not read, so the manifest version stays 1 and every checkout still loads it.
        "save_stats": {
            name: {"size": size, "mtime_ns": mtime_ns} for name, (size, mtime_ns) in sorted(save_stats.items())
        },
    }
    temp = folder / (MANIFEST_NAME + ".tmp")
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, folder / MANIFEST_NAME)


# --- the public interface --------------------------------------------------------------------


def take(
    user_data: Path,
    backup_root: Path,
    extra: Sequence[str] = (),
    now: datetime | None = None,
) -> Snapshot:
    """Snapshot the files of SNAPSHOT_SET plus `extra` (user-data-relative saves the run will load).

    Raises FileNotFoundError if `user_data` or an `extra` file is missing, ValueError if an `extra`
    path leaves `user_data`, SaveNotListed (a ValueError) if an `extra` save is not a name `save games/`
    lists (`unlisted_save`), and BackupRootError if the backup folder cannot be used. Every
    refusal comes before anything is written.

    Only regular files are copied. `listing` also names symlinks and other non-directories. `save_stats` gives
    the size and mtime_ns of every `listing` name in `save games/`, as the scan's lstat saw it (a link's own).

    A file whose size and mtime_ns both match the previous snapshot's entry, and whose content is
    still in the store, keeps that entry's hash without being read. Every other file is hashed.
    The free-space check counts the whole size of every file that will be read, which is an upper
    bound on the bytes copied, since a file whose content is already stored is not copied.

    The id is the UTC second of `now`, or without `now` of the backup drive's clock (see `_drive_clock`;
    the machine's own clock drifts and steps). It always sorts after the id of every existing loadable
    snapshot: if the time is not later than the newest one's, that one's time is used again with the
    next `-N` suffix. So `all_snapshots` order is the order of taking, whatever a clock does.
    """
    user_data, backup_root = Path(user_data), Path(backup_root)
    if not user_data.is_dir():
        raise FileNotFoundError(f"the user-data folder does not exist: {user_data}")
    _check_backup_root(user_data, backup_root)
    extra_paths = [_clean_relative(text) for text in extra]

    scans = {folder: _scan_folder(user_data, folder) for folder in LISTED_FOLDERS}
    wanted: dict[str, os.stat_result] = {}
    for pattern in SNAPSHOT_SET:
        folder, _, name_pattern = pattern.rpartition("/")
        for rel, st in scans[folder].items():
            if stat.S_ISREG(st.st_mode) and fnmatch.fnmatchcase(rel.rpartition("/")[2], name_pattern):
                wanted[rel] = st
    for rel in extra_paths:
        target = user_data / rel
        if not target.is_file():
            raise FileNotFoundError(f"cannot snapshot {rel!r}: not a file in {user_data}")
        problem = unlisted_save(user_data, rel, scans[SAVE_FOLDER])
        if problem is not None:
            raise SaveNotListed(f"cannot snapshot {problem}")
        wanted[rel] = target.stat()
    listing = frozenset(rel for found in scans.values() for rel in found)
    save_stats = {rel: (st.st_size, st.st_mtime_ns) for rel, st in scans[SAVE_FOLDER].items()}

    store, snapshots = backup_root / "store", backup_root / "snapshots"
    previous = all_snapshots(backup_root)
    previous_files = previous[-1].files if previous else {}
    files: dict[str, Entry] = {}
    to_read: dict[str, os.stat_result] = {}
    for rel in sorted(wanted):
        st, old = wanted[rel], previous_files.get(rel)
        if old and old.size == st.st_size and old.mtime_ns == st.st_mtime_ns and _blob_is_intact(store, old):
            files[rel] = old
        else:
            to_read[rel] = st

    needed = sum(st.st_size for st in to_read.values())
    free = shutil.disk_usage(backup_root if backup_root.exists() else backup_root.parent)[2]
    if free < needed + FREE_SPACE_MARGIN:
        raise BackupRootError(
            f"{backup_root} needs {needed + FREE_SPACE_MARGIN} free bytes (the files to copy plus "
            f"{FREE_SPACE_MARGIN}); it has {free}"
        )

    backup_root.mkdir(exist_ok=True)
    store.mkdir(exist_ok=True)
    snapshots.mkdir(exist_ok=True)
    for rel in to_read:
        files[rel] = _store_file(user_data / rel, store)
    files = {rel: files[rel] for rel in sorted(files)}

    taken = _utc(now) if now is not None else _drive_clock(snapshots)
    base_id, first_number = _ordered_id(taken, previous)
    snapshot_id, folder = _new_snapshot_dir(snapshots, base_id, first_number)
    try:
        _write_manifest(folder, taken, files, listing, save_stats)
    except BaseException:
        # Clear our own unfinished folder. rmdir cannot remove one that holds a manifest, so
        # a snapshot that was committed before the failure is never deleted by the run that made it.
        with contextlib.suppress(FileNotFoundError):
            os.unlink(folder / (MANIFEST_NAME + ".tmp"))
        with contextlib.suppress(OSError):
            folder.rmdir()
        raise
    return Snapshot(id=snapshot_id, dir=folder, files=files, listing=listing, save_stats=save_stats)


def _int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _read_save_stats(raw, listing: frozenset[str]) -> dict[str, tuple[int, int]] | None:
    """The manifest's `save_stats` as `Snapshot.save_stats`, or None when there is none (a manifest written before
    #1725) or it does not read: not a mapping of exactly the listing's `save games/` names to whole-number sizes and
    times. It never makes a manifest unloadable, since the rest of the snapshot restores without it; `restore`
    then says it could not tell a changed save."""
    if not isinstance(raw, dict):
        return None
    folder = SAVE_FOLDER + "/"
    if set(raw) != {name for name in listing if name.startswith(folder) and "/" not in name[len(folder):]}:
        return None
    stats = {}
    for name, value in raw.items():
        if not isinstance(value, dict) or not _int(value.get("size")) or not _int(value.get("mtime_ns")):
            return None
        stats[name] = (value["size"], value["mtime_ns"])
    return stats


def load(snapshot_dir: Path) -> Snapshot:
    """Read a finished snapshot. FileNotFoundError if it has no manifest, ValueError if it is unreadable.

    A `save_stats` that is missing or does not read leaves `save_stats` None and is no reason to refuse the rest."""
    snapshot_dir = Path(snapshot_dir)
    text = (snapshot_dir / MANIFEST_NAME).read_text(encoding="utf-8")
    try:
        manifest = json.loads(text)
        if manifest["version"] != MANIFEST_VERSION:
            raise ValueError(f"unknown manifest version {manifest['version']!r}")
        files = {}
        for name, raw in manifest["files"].items():
            if _clean_relative(name) != name or not _SHA256_PATTERN.match(raw["sha256"]):
                raise ValueError(f"bad manifest entry {name!r}")
            files[name] = Entry(size=int(raw["size"]), mtime_ns=int(raw["mtime_ns"]), sha256=raw["sha256"])
        listing = frozenset(manifest["listing"])
        if any(not isinstance(name, str) or _clean_relative(name) != name for name in listing):
            raise ValueError("bad manifest listing")
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ValueError(f"unreadable manifest in {snapshot_dir}: {error!r}") from error
    save_stats = _read_save_stats(manifest.get("save_stats"), listing)
    return Snapshot(id=snapshot_dir.name, dir=snapshot_dir, files=files, listing=listing, save_stats=save_stats)


def all_snapshots(backup_root: Path) -> list[Snapshot]:
    """Every loadable snapshot, oldest first. Folders that do not load are skipped."""
    snapshots = Path(backup_root) / "snapshots"
    try:
        names = os.listdir(snapshots)
    except (FileNotFoundError, NotADirectoryError):
        return []
    found = []
    for name in names:
        match = _ID_PATTERN.match(name)
        if not match:
            continue
        try:
            snap = load(snapshots / name)
        except (OSError, ValueError):
            continue
        found.append(((match.group(1), int(match.group(2) or 1)), snap))
    found.sort(key=lambda item: item[0])
    return [snap for _, snap in found]


def _drive_clock(folder: Path) -> datetime:
    """The time on the clock of the drive `folder` lives on, read by writing a marker file there and
    taking its modification time. WSL's own clock drifts after the host sleeps; the file times the hold
    rule compares journal times with are stamped by the drive, so the journal uses the same clock."""
    marker = folder / CLOCK_MARKER
    with open(marker, "wb") as handle:
        handle.write(b"clock")  # a write, so that the filesystem stamps its own time
    return datetime.fromtimestamp(os.stat(marker).st_mtime, timezone.utc)


def record(snap: Snapshot, event: str, now: datetime | None = None, **fields) -> None:
    """Append one event to the snapshot's journal, with `at` set to the UTC time as ISO-8601.

    Without `now`, `at` is the backup drive's own clock (see `_drive_clock`), not the machine's.
    """
    if "at" in fields:
        raise ValueError("'at' is the timestamp; name the field something else")
    at = _utc(now) if now is not None else _drive_clock(snap.dir)
    entry = {"event": event, "at": at.strftime("%Y-%m-%dT%H:%M:%SZ"), **fields}
    data = (json.dumps(entry) + "\n").encode("ascii")
    fd = os.open(snap.dir / JOURNAL_NAME, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        if os.lseek(fd, 0, os.SEEK_END):
            os.lseek(fd, -1, os.SEEK_END)
            if os.read(fd, 1) != b"\n":
                data = b"\n" + data  # a crash left half a line: start a fresh one rather than glue onto it
        os.write(fd, data)  # O_APPEND: lands at the end whatever the position
        os.fsync(fd)
    finally:
        os.close(fd)


def journal(snap: Snapshot) -> list[dict]:
    """The recorded events in order. A line that does not parse (a write cut short) is skipped."""
    try:
        raw = (snap.dir / JOURNAL_NAME).read_bytes()
    except FileNotFoundError:
        return []
    events = []
    for line in raw.split(b"\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            events.append(entry)
    return events
