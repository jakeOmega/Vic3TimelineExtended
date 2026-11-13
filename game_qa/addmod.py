"""A variant mod folder for an A/B run (#1702, item 2): `start --add-mod <Windows path>`.

A session loads the deployed mod, then each variant folder, then the overlay, so a folder that overrides one
system (a performance fix, say) can be measured against the same save without deploying a build the owner does
not play. `launch --add-mod` only checks that a path begins like a Windows path (`path_problem`, shared with it);
`check` holds a session's variant to more, before anything is started:

- a drive path (`D:\\…`), not a UNC one, of a folder below the drive's root, with no empty, `.` or `..` part, no part
  ending in a dot or a space (Windows drops those, so the game would read another folder than the one checked),
  no 8.3 short name (`PARADO~1`: one more spelling of a folder), no reserved device name and none of `<>:"/|?*`;
- outside the user-data folder, and not holding it: judged on the Windows spellings (case and separators aside) and
  again on the folder itself, by its identity on the drive up every parent, so neither a spelling nor a link gets a
  folder inside it past the check. The deployed mod and the overlay live there; so do the owner's own mods;
- a real folder, reached through no symbolic link or junction at any part of the path (WSL shows an NTFS junction
  on a drive as a symlink: a `mklink /J` on D: was refused so on 2026-11-13), holding a `.metadata/metadata.json`
  that reads as a JSON object (the file the game reads a mod by);
- under `--playset current`, not a folder the owner's playset already enables: launch would leave it where it is,
  which may be before the deployed mod, and the run would not be the A/B it says it is.

The Windows path is what the playset gets, as given; the WSL path (`wslpath -u`) is what is checked and what the
fixture key reads the folder's files from.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# An --add-mod path as `launch` takes it: a drive path (`C:\…`) or a UNC path (`\\server\…`), as the launcher writes them.
WINDOWS_PATH = re.compile(r"[A-Za-z]:\\|\\\\[^\\]")
METADATA = PurePosixPath(".metadata") / "metadata.json"
_DRIVE_PATH = re.compile(r"([A-Za-z]):\\(.*)\Z", re.S)
_BAD_CHARS = re.compile(r'[<>:"/|?*]')
_SHORT_NAME = re.compile(r"~\d")
_DEVICE = re.compile(r"(CON|PRN|AUX|NUL|COM\d|LPT\d)(\..*)?\Z", re.I)


class AddModError(Exception):
    """A variant folder `check` refuses. `code`: bad_argument, inside_user_data, holds_user_data, is_deployed_mod,
    already_enabled, symlink, no_folder, no_metadata, bad_metadata."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__("%s: %s" % (code, detail))
        self.code, self.detail = code, detail


@dataclass(frozen=True)
class AddMod:
    windows: str                # as given: what `launch --add-mod` and the playset get
    wsl: str                    # the same folder from WSL: what was checked, and what the fixture key reads
    name: str | None            # metadata.json's `name` and `version`, for the run's record
    version: str | None


def path_problem(path: str) -> str | None:
    """Why `launch` refuses `path` as an --add-mod, as the end of a sentence that begins with the path, or None:
    it cannot be written whole (a lone surrogate, which UTF-8 cannot hold, or a control character), or it is not a
    Windows path (`C:\\…` or `\\\\server\\…`; the caller converts a WSL path with `wslpath -w`)."""
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        return "cannot be written as UTF-8"
    if any(ord(c) < 32 or ord(c) == 127 for c in path):
        return "has a control character in it"
    if not WINDOWS_PATH.match(path):
        return "is not a Windows path (C:\\… or \\\\server\\…): convert a WSL path with `wslpath -w`"
    return None


def folder_key(path: str) -> str:
    """A Windows folder path as `launch` compares it (__main__._folder_key): in any case, with either separator, with
    or without a trailing one."""
    return path.replace("/", "\\").rstrip("\\").lower()


def to_wsl_path(path: str, run=subprocess.run) -> Path:
    """`path` (a Windows drive path) as WSL names it (`wslpath -u`)."""
    done = run(["wslpath", "-u", path], capture_output=True, text=True, check=True)
    return Path(done.stdout.rstrip("\r\n"))


def _parts(path: str) -> tuple[str, list[str]]:
    """The drive letter and the parts of a drive path, refusing every spelling that is not one plain folder."""
    problem = path_problem(path)
    if problem is not None:
        raise AddModError("bad_argument", "the --add-mod path %r %s" % (path, problem))
    match = _DRIVE_PATH.match(path)
    if match is None:
        raise AddModError("bad_argument", "the --add-mod path %r is a UNC path: give the folder by its drive letter "
                                          "(D:\\…)" % path)
    rest = match.group(2)
    if rest.endswith("\\"):
        rest = rest[:-1]
    parts = rest.split("\\") if rest else []
    if not parts:
        raise AddModError("bad_argument", "the --add-mod path %r is a drive's root, not a mod's folder" % path)
    for part in parts:
        why = None
        if part in ("", ".", ".."):
            why = "an empty, `.` or `..` part"
        elif part.endswith((".", " ")):
            why = "a part ending in a dot or a space, which Windows drops (another folder than the one checked)"
        elif _BAD_CHARS.search(part):
            why = "one of <>:\"/|?* (give the path with backslashes only)"
        elif _SHORT_NAME.search(part):
            why = "an 8.3 short name (%s): spell the folder out" % part
        elif _DEVICE.match(part):
            why = "a device name (%s)" % part
        if why is not None:
            raise AddModError("bad_argument", "the --add-mod path %r has %s" % (path, why))
    return match.group(1), parts


def _within(inner: str, outer: str) -> bool:
    """Whether the Windows folder `inner` is `outer` or inside it, as launch compares folders."""
    inner, outer = folder_key(inner), folder_key(outer)
    return inner == outer or inner.startswith(outer + "\\")


def _same(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def check(path: str, user_data: Path, user_data_windows: str | None, *, to_wsl: Callable[[str], Path] = to_wsl_path,
          playset: str = "mod_only", owner_mods: Sequence[str] = (), deployed: Path | None = None,
          deployed_windows: str | None = None) -> AddMod:
    """`path` as a session's variant folder (see the module's rules), or AddModError. `user_data` is the user-data
    folder from WSL and `user_data_windows` as Windows names it (None when not known: the identity test then stands
    alone); `deployed` and `deployed_windows` the deployed mod's folder, which can be configured outside it."""
    if not isinstance(path, str):
        raise AddModError("bad_argument", "an --add-mod is a Windows path, not %r" % (path,))
    _drive, parts = _parts(path)
    for name, inside in ((user_data_windows, "inside_user_data"), (deployed_windows, "is_deployed_mod")):
        if name is None:
            continue
        if _within(path, name):
            raise AddModError(inside, "%s is inside %s (or is it): give a folder outside the user-data folder, on D: "
                                      "say" % (path, name))
        if _within(name, path):
            raise AddModError("holds_user_data", "%s holds %s: give the variant's own folder" % (path, name))
    if playset == "current" and any(folder_key(m) == folder_key(path) for m in owner_mods):
        raise AddModError("already_enabled", "the owner's playset already enables %s, and launch would leave it "
                                             "where it is: take it out of the playset, or use --playset mod_only"
                          % path)
    try:
        wsl = Path(to_wsl(path))
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        raise AddModError("bad_argument", "%s could not be converted to a WSL path: %s" % (path, e)) from None
    if not wsl.is_absolute() or len(wsl.parts) < len(parts) + 1 or [p.lower() for p in wsl.parts[-len(parts):]] \
            != [p.lower() for p in parts]:
        raise AddModError("bad_argument", "%s converts to %s, which does not end in the same folders" % (path, wsl))
    # Every part from the drive's mount down, as the drive holds it: no link, no junction, the last a real folder.
    mount = Path(*wsl.parts[:len(wsl.parts) - len(parts)])
    here = mount
    for part in parts:
        here = here / part
        if not os.path.lexists(here):
            raise AddModError("no_folder", "%s (%s) is not there" % (path, here))
        if os.path.islink(here):
            raise AddModError("symlink", "%s is reached through a link or a junction at %s: give the folder itself"
                              % (path, here))
        if not os.path.isdir(here):
            raise AddModError("no_folder", "%s is not a folder" % here)
    if os.path.realpath(wsl) != os.path.abspath(wsl):        # the mount itself, or anything the walk could not see
        raise AddModError("symlink", "%s resolves to %s: give the folder itself" % (wsl, os.path.realpath(wsl)))
    for folder, what in ((user_data, "the user-data folder"), (deployed, "the deployed mod")):
        if folder is None:
            continue
        if any(_same(parent, folder) for parent in (wsl, *wsl.parents)):
            raise AddModError("inside_user_data" if what == "the user-data folder" else "is_deployed_mod",
                              "%s is %s or inside it, by the drive's own identity of the folder" % (path, what))
        if any(_same(parent, wsl) for parent in (Path(folder), *Path(folder).parents)):
            raise AddModError("holds_user_data", "%s holds %s" % (path, what))
    meta = wsl / METADATA
    if os.path.islink(meta) or os.path.islink(meta.parent) or not meta.is_file():
        raise AddModError("no_metadata", "%s has no %s (a real file): the game reads a mod by it" % (path, METADATA))
    try:
        data = json.loads(meta.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise AddModError("bad_metadata", "%s does not read as JSON: %s" % (meta, e)) from None
    if not isinstance(data, dict):
        raise AddModError("bad_metadata", "%s is not a JSON object" % meta)

    def text(key):
        value = data.get(key)
        return value if isinstance(value, str) else None
    return AddMod(windows=path, wsl=str(wsl), name=text("name"), version=text("version"))


def check_all(paths: Sequence[str], **kwargs) -> list[AddMod]:
    """`check` for each, in order; a folder given twice (as launch compares folders) is refused."""
    seen: list[str] = []
    found = []
    for path in paths:
        if isinstance(path, str) and folder_key(path) in seen:
            raise AddModError("bad_argument", "%s is given twice" % path)
        found.append(check(path, **kwargs))
        seen.append(folder_key(path))
    return found
