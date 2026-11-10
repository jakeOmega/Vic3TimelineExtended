"""Snapshots of the owner's saves, settings and logs, kept in a content store.

Layout under the backup root:

    store/<sha256[:2]>/<sha256>     one copy of each distinct file content, shared by every snapshot
    snapshots/<id>/manifest.json    the files taken (size, mtime, hash) and the listing of the folders
    snapshots/<id>/journal.jsonl    what the run did: started, heartbeat, game_exited, restored, held

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

# take() refuses unless the backup drive has the bytes it must copy plus this much to spare.
FREE_SPACE_MARGIN = 1024**3

MANIFEST_VERSION = 1
MANIFEST_NAME = "manifest.json"
JOURNAL_NAME = "journal.jsonl"

_ID_PATTERN = re.compile(r"^(\d{8}T\d{6}Z)(?:-(\d+))?$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CHUNK = 1024 * 1024
_READ_ATTEMPTS = 3


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
            entry = Entry(size=size, mtime_ns=after.st_mtime_ns, sha256=sha256)
            if not _blob_is_intact(store, entry):
                blob = _blob_path(store, sha256)
                blob.parent.mkdir(exist_ok=True)
                os.replace(temp_name, blob)
            return entry
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temp_name)
    raise OSError(f"{path} kept changing while it was being read")


def _new_snapshot_dir(snapshots: Path, base_id: str) -> tuple[str, Path]:
    """Create the first free `<base_id>`, `<base_id>-2`, `<base_id>-3`, ... folder."""
    number = 1
    while True:
        snapshot_id = base_id if number == 1 else f"{base_id}-{number}"
        folder = snapshots / snapshot_id
        try:
            folder.mkdir()
        except FileExistsError:
            number += 1
            continue
        return snapshot_id, folder


def _write_manifest(folder: Path, taken: datetime, files: dict[str, Entry], listing: frozenset[str]) -> None:
    manifest = {
        "version": MANIFEST_VERSION,
        "created": taken.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": {
            name: {"size": entry.size, "mtime_ns": entry.mtime_ns, "sha256": entry.sha256}
            for name, entry in files.items()
        },
        "listing": sorted(listing),
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
    path leaves `user_data`, and BackupRootError if the backup folder cannot be used. Every
    refusal comes before anything is written.

    Only regular files are copied. `listing` also names symlinks and other non-directories.

    A file whose size and mtime_ns both match the previous snapshot's entry, and whose content is
    still in the store, keeps that entry's hash without being read. Every other file is hashed.
    The free-space check counts the whole size of every file that will be read, which is an upper
    bound on the bytes copied, since a file whose content is already stored is not copied.
    """
    user_data, backup_root = Path(user_data), Path(backup_root)
    taken = _utc(now)
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
        wanted[rel] = target.stat()
    listing = frozenset(rel for found in scans.values() for rel in found)

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

    snapshot_id, folder = _new_snapshot_dir(snapshots, taken.strftime("%Y%m%dT%H%M%SZ"))
    try:
        _write_manifest(folder, taken, files, listing)
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)  # our own unfinished folder, with no manifest
        raise
    return Snapshot(id=snapshot_id, dir=folder, files=files, listing=listing)


def load(snapshot_dir: Path) -> Snapshot:
    """Read a finished snapshot. FileNotFoundError if it has no manifest, ValueError if it is unreadable."""
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
    return Snapshot(id=snapshot_dir.name, dir=snapshot_dir, files=files, listing=listing)


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


def record(snap: Snapshot, event: str, now: datetime | None = None, **fields) -> None:
    """Append one event to the snapshot's journal, with `at` set to the UTC time as ISO-8601."""
    if "at" in fields:
        raise ValueError("'at' is the timestamp; name the field something else")
    entry = {"event": event, "at": _utc(now).strftime("%Y-%m-%dT%H:%M:%SZ"), **fields}
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
