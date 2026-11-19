"""The mods-off `script_docs` dump a vanilla bump needs (#1907): where it goes, the checks before it is kept, and the
copy. `Session.script_docs` drives the game; this module only reads and writes files, and touches nothing of the
game's.

`script_docs`, typed into the console of a game run with `-debug_mode`, writes six logs into the user-data folder's
`docs/` and answers `console_success: Logs created in directory: docs/`. The owner's hand-taken dump of 1.15.2
(2026-11-19, at the main menu with every mod off) logged the command and that answer in the same second. The session
does not wait for that answer (the log is block-buffered, and the command that flushes it has not been run at the
menu): the rewritten logs are the proof. A dump
taken with this mod loaded also lists the mod's own modifier types, so engine-doc origin tagging would call them
vanilla: `MOD_MARKER` must be absent from `modifiers.log` (the runbook's check, docs/guides/vanilla_patch_runbook.md
§ 0).

A log counts as written by the run when its (size, mtime_ns) differ from what they were just before the command and
its time is later. Both readings come from the same drive, so no clock of this machine is compared with one of
Windows (WSL steps its clock by seconds, #1604).

The dump is kept outside the Modding-Digests clone, which upstream rewrites, at `<root>/<version>/docs` by default:
`/status` reads `versions.engine_docs_source` from the last dotted number in the pinned path, so another folder
name must still end in the version. Pinning it (`vanilla_snapshot_docs_path` in `paths.local.json`) stays a step of
the runbook's: `path_constants` caches that file, and a pin in the main checkout re-renders `docs/engine/` there at
the next server start.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
from pathlib import Path

COMMAND = "script_docs"
DOCS_FOLDER = "docs"                                    # under the user-data folder
LOGS = ("effects.log", "triggers.log", "modifiers.log", "event_targets.log", "on_actions.log",
        "custom_localization.log")
# A modifier type only this mod registers (common/modifier_type_definitions/): in modifiers.log, the dump had the
# mod loaded.
MOD_MARKER = "country_add_anticolonial_ideology_to_igs_bool"
DEFAULT_ROOT = "~/src/vic3-engine-docs"
_VERSION = re.compile(r"\d+\.\d+(?:\.\d+)?")            # mod_state_server._VERSION_RE, read the same way
_CHUNK = 1024 * 1024

Stat = tuple[int, int]                                  # (st_size, st_mtime_ns)


class DocsRefused(Exception):
    """A refusal: `code` names it, `detail` says why and what to do, `info` carries what was found."""

    def __init__(self, code: str, detail: str, **info) -> None:
        super().__init__("%s: %s" % (code, detail))
        self.code, self.detail, self.info = code, detail, info


def version_of(text: str | os.PathLike | None) -> str | None:
    """The last dotted number in `text` (a version, or a path ending in one), as `/status` reads a docs path."""
    found = _VERSION.findall(str(text)) if text else []
    return found[-1] if found else None


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def plan(installed: str, version: str | None, out: str | os.PathLike | None, force: bool = False,
         digests: str | os.PathLike | None = None, root: str | os.PathLike = DEFAULT_ROOT) -> Path:
    """The folder the dump goes to, once nothing stands in the way; raises DocsRefused, having done nothing.

    `installed` is the installed game's version (`launcher-settings.json` `rawVersion`): the dump is that binary's,
    so `version`, when given, must be it (`version_mismatch`). `out` defaults to `<root>/<installed>/docs`; one
    given must name the version as its last dotted number (`out_version`), since that is what `/status` reads, and
    must not lie inside the Modding-Digests clone `digests` (`inside_digests`). A folder already there is refused
    (`out_exists`) unless `force`: a second dump of one version replaces the first only when asked."""
    if not isinstance(installed, str) or version_of(installed) != installed:
        raise DocsRefused("no_version", "the installed game's version reads %r, not a dotted number" % (installed,))
    if version is not None and version != installed:
        raise DocsRefused("version_mismatch", "--version %s is not the installed game's %s (launcher-settings.json "
                          "rawVersion): the dump is of the binary that runs, so update the game first or leave "
                          "--version out" % (version, installed), installed=installed)
    target = Path(out).expanduser() if out is not None else Path(root).expanduser() / installed / DOCS_FOLDER
    target = Path(os.path.abspath(target))
    if version_of(target) != installed:
        raise DocsRefused("out_version", "%s does not end in the version %s: `/status` reads the engine docs' version "
                          "from the last dotted number in the pinned path (`versions.engine_docs_source`)"
                          % (target, installed), out=str(target))
    if digests:
        clone = Path(os.path.abspath(Path(digests).expanduser()))
        if target == clone or clone in target.parents:
            raise DocsRefused("inside_digests", "%s is inside the Modding-Digests clone %s, which upstream rewrites "
                              "and the server auto-pulls: keep the dump outside it" % (target, clone),
                              out=str(target))
    if os.path.lexists(target) and not force:
        raise DocsRefused("out_exists", "%s is there already: pass --force to replace it with a new dump of %s"
                          % (target, installed), out=str(target))
    return target


def stats(folder: str | os.PathLike) -> dict[str, Stat | None]:
    """Each log's (size, mtime_ns) in `folder`, None for one missing or not a plain file."""
    out: dict[str, Stat | None] = {}
    for name in LOGS:
        try:
            st = os.lstat(Path(folder) / name)
        except FileNotFoundError:
            out[name] = None
            continue
        out[name] = (st.st_size, st.st_mtime_ns) if stat.S_ISREG(st.st_mode) else None
    return out


def unwritten(before: dict[str, Stat | None], now: dict[str, Stat | None]) -> list[str]:
    """The logs not written since `before`: missing now, or with the same size and time, or an earlier time."""
    left = []
    for name in LOGS:
        was, is_ = before.get(name), now.get(name)
        if is_ is None or is_ == was or (was is not None and is_[1] <= was[1]):
            left.append(name)
    return left


def sha256(path: str | os.PathLike) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stage(source: str | os.PathLike, dest: str | os.PathLike, expected: dict[str, Stat | None]) -> dict[str, dict]:
    """Copy the six logs from the game's `docs/` into `dest` (the run's folder), each only while it is the one
    `expected` describes (its size and time before and after the copy); the copies' size and SHA-256 by name.
    Raises DocsRefused (`changed_while_copied`) when a log moved under the copy: the game may still be writing."""
    source, dest = Path(source), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict] = {}
    for name in LOGS:
        want = expected.get(name)
        if want is None or stats(source)[name] != want:
            raise DocsRefused("changed_while_copied", "docs/%s changed after it was seen written: the game may still "
                              "be writing the dump" % name, file=name)
        shutil.copyfile(source / name, dest / name)
        if stats(source)[name] != want:
            raise DocsRefused("changed_while_copied", "docs/%s changed while it was copied" % name, file=name)
        files[name] = {"size": os.path.getsize(dest / name), "sha256": sha256(dest / name)}
    return files


def check(folder: str | os.PathLike) -> dict:
    """The checks before a dump in `folder` is kept, or DocsRefused: every log there and not empty (`missing`,
    `empty`), and `MOD_MARKER` nowhere in `modifiers.log` as a whole name (`mod_loaded`). Returns what was
    checked, for the reply."""
    folder = Path(folder)
    missing = [name for name in LOGS if not (folder / name).is_file()]
    if missing:
        raise DocsRefused("missing", "the dump lacks %s" % ", ".join(missing), files=missing)
    empty = [name for name in LOGS if (folder / name).stat().st_size == 0]
    if empty:
        raise DocsRefused("empty", "the dump's %s is empty" % ", ".join(empty), files=empty)
    data = (folder / "modifiers.log").read_bytes()
    if re.search(rb"(?<![A-Za-z0-9_])" + MOD_MARKER.encode() + rb"(?![A-Za-z0-9_])", data):
        raise DocsRefused("mod_loaded", "modifiers.log lists %s, a modifier type only this mod registers: the game "
                          "ran with the mod loaded, so origin tagging would call the mod's types vanilla. Nothing "
                          "was kept" % MOD_MARKER, marker=MOD_MARKER)
    return {"logs": list(LOGS), "mod_marker_absent": MOD_MARKER}


def install(staged: str | os.PathLike, out: str | os.PathLike, files: dict[str, dict], force: bool = False) -> None:
    """Copy the staged logs to `out`, by a temp folder beside it and a rename, each copy's SHA-256 checked against
    `files`. An `out` already there is refused (`out_exists`) unless `force`, which replaces it whole only once the
    new copy is complete. Raises DocsRefused (`copy_failed`) with `out` left as it was."""
    staged, out = Path(staged), Path(out)
    temp = out.with_name(".%s.part-%s" % (out.name, os.urandom(4).hex()))
    old = out.with_name(".%s.old-%s" % (out.name, os.urandom(4).hex()))
    if os.path.lexists(out) and not force:
        raise DocsRefused("out_exists", "%s appeared while the dump was taken: the copy is in %s; pass --force to "
                          "replace it" % (out, staged), out=str(out), staged=str(staged))
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        temp.mkdir()
        for name in LOGS:
            shutil.copyfile(staged / name, temp / name)
            if sha256(temp / name) != files[name]["sha256"]:
                raise DocsRefused("copy_failed", "the copy of %s does not match the staged one" % name, file=name)
        if os.path.lexists(out):
            os.replace(out, old)
        os.replace(temp, out)
    except DocsRefused:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    except OSError as e:
        shutil.rmtree(temp, ignore_errors=True)
        if os.path.lexists(old) and not os.path.lexists(out):
            os.replace(old, out)
        raise DocsRefused("copy_failed", "copying the dump to %s failed (%s): it is in %s" % (out, e, staged),
                          out=str(out), staged=str(staged)) from e
    shutil.rmtree(old, ignore_errors=True)


def previous(root: str | os.PathLike, version: str, out: str | os.PathLike | None = None) -> Path | None:
    """The newest dump under `root` older than `version` (`<root>/<version>/docs` holding all six logs), the old
    side of the diff the runbook runs next; None if there is none. `out` is never its own previous."""
    root = Path(root).expanduser()
    best: tuple[tuple[int, ...], Path] | None = None
    try:
        children = list(root.iterdir())
    except OSError:
        return None
    for child in children:
        if version_of(child.name) != child.name or _key(child.name) >= _key(version):
            continue
        docs = child / DOCS_FOLDER
        if out is not None and Path(os.path.abspath(docs)) == Path(os.path.abspath(out)):
            continue
        if all((docs / name).is_file() for name in LOGS) and (best is None or _key(child.name) > best[0]):
            best = (_key(child.name), docs)
    return best[1] if best else None


def next_steps(out: Path, old: Path | None) -> dict:
    """What the runbook does with the dump: pin it, and diff it against the one before."""
    steps = {"pin": '"vanilla_snapshot_docs_path": "%s"' % out,
             "pin_note": "in paths.local.json, then restart the server: path_constants caches that file, and a pin "
                         "in the main checkout re-renders docs/engine/ there at the next server start"}
    if old is not None:
        steps["diff"] = ("python3 scripts/analysis/vanilla_patch_diff.py docs %s %s --mod-uses --show-changed"
                         % (old, out))
    return steps
