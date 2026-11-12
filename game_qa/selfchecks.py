"""The mod's self-check lines: kept with the fixture, and reported for a run (#1601).

The mod's script answers its own engine questions once a game with `debug_log` lines of the form
`TE_SELF_CHECK OK|BROKEN|START <name> ...` (CLAUDE.md, "In-game checks"); the play-test lists wait for them.

    <backup root>/runs/<id>/debug.log          a session's copy of the game's log, appended at each verb (session.py)
    <backup root>/fixtures/<key>/lines.log     the TE_SELF_CHECK and TE_MONUMENTS lines of the run that made the
                                               fixture `te_qa_fixture_<key>.v3`, as logged, oldest first
    <backup root>/fixtures/<key>/record.json   which run that was and what was kept (`kept: true`), or why nothing
                                               is (`kept: false`, `detail`)

The lines the game logs while it sets a new game up exist only in the log of the run that makes the fixture: the
save is made after them, so no session logs them again. That log is in the run's snapshot (`run_logs/`), which is
pruned after five more snapshots, while the fixture is used for as long as the build is unchanged. So they are
kept here when the fixture is made (`keep_fixture_lines`) and go when the fixture's save has gone (`drop_orphans`).

The one thing this must never do is report a line of another game, or of another fixture's run, as this run's:
a stale OK would pass an engine fact nobody checked. So:

- A record says `kept: true` only for the lines written just before it. Whatever was kept under a key goes
  before a fixture is made under that key (`forget_fixture_lines`) and again before its lines are read
  (`keep_fixture_lines`); every failure in between leaves a record that says nothing is kept, and why.
- A log, or the beginning of one, whose bytes the run's snapshot recorded among the owner's logs is the owner's
  earlier game, and is not read.
- A run is shown a fixture's lines only if they were kept from a run before it (`_fixture_part`).

- A run beside whose game `watch` saw another Victoria 3 process, or whose restore held for one, has its
  session's rows marked `unvouched`: whether two games can share `logs/` is not known (`_other_game`).

Nothing here writes outside `<backup root>/fixtures/`: a `fixtures` folder or a key's folder that is a symlink
is refused, never followed (`_own_folder`). Of the user-data folder only the names of the fixtures in
`save games/` are looked at. The line's pattern is `scripts/analysis/log_triage.py`'s, so the two
tools cannot come to read a line differently.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from game_qa import fixture, restore, snapshot
from game_qa.logtail import GAP_MARKER, GENERATIONS, parse
from game_qa.report import STEPS_FILE, read_steps, stamp, utc_now

REPO_ROOT = Path(__file__).resolve().parent.parent
SELF_CHECK = "TE_SELF_CHECK"
KEPT_MARKERS = (SELF_CHECK, "TE_MONUMENTS")     # what is kept of a fixture run's log
FIXTURES_FOLDER = "fixtures"
LINES_FILE = "lines.log"
RECORD_FILE = "record.json"
RUNS_FOLDER = "runs"
RUN_LOG = "debug.log"                           # in a run folder: the session's copy; in run_logs/: the game's own
OWNERS_LOG = "logs/" + RUN_LOG                  # in a snapshot's manifest: the log the run's game found
BROKEN, START, OK = "BROKEN", "START", "OK"
BEING_MADE = ("its lines were not kept: the run that made it did not get as far as keeping them (its restore held "
              "or was refused, or the start ended first; the `fixture` step of the run that made it says)")

_KEY = re.compile(r"[A-Za-z0-9_]{1,64}")                    # a fixture key, as fixture.py takes one
_RUN_ID = re.compile(r"(\d{8}T\d{6}Z)(?:-(\d+))?")          # a run folder's name: its snapshot's id (snapshot.py)
_TEMP_SUFFIX = ".tmp"
_CHUNK = 1024 * 1024


class SelfCheckError(Exception):
    """Lines that could not be kept, or a run that is not there. `code` is the refusal's name."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code, self.detail = code, detail


# ---- reading lines

def _pattern() -> re.Pattern:
    """`TE_SELF_CHECK <verdict> <name>`, as log triage reads it (`log_triage.SELF_CHECK_RE`)."""
    folder = str(REPO_ROOT / "scripts" / "analysis")
    if folder not in sys.path:
        sys.path.append(folder)
    import log_triage

    return log_triage.SELF_CHECK_RE


def marked_lines(path: Path, markers: tuple[str, ...] = KEPT_MARKERS, start: int = 0) -> tuple[list[str], int]:
    """(the lines of the log `path`, from byte `start` on, that hold one of `markers`, in order; how often the
    session's follower lost lines to rotation, which a run folder's copy marks with GAP_MARKER). A file that is
    not there has none; one that cannot be read raises OSError."""
    wanted = [marker.encode("utf-8") for marker in markers]
    gap = GAP_MARKER.encode("utf-8")
    lines: list[str] = []
    gaps = 0
    try:
        with open(path, "rb") as f:
            f.seek(start)
            for raw in f:
                if any(marker in raw for marker in wanted):
                    lines.append(raw.rstrip(b"\r\n").decode("utf-8", errors="replace"))
                elif raw.rstrip(b"\r\n") == gap:
                    gaps += 1
    except FileNotFoundError:
        pass
    return lines, gaps


def verdicts(lines: list[str], source: str) -> list[dict]:
    """One entry per check named in `lines`, in the order each was first logged: `name`, `verdict`, `line`,
    `source`, and `seen` (how often each verdict was logged) when the check logged more than one line.

    The verdict is BROKEN if any line says so, else OK if any does, else the last one logged (a START whose
    verdict never came). `line` is the first line with that verdict, without the log's own `[time][file.cpp:n]: `
    prefix when it reads as a `debug_log` line."""
    pattern = _pattern()
    found: dict[str, dict] = {}
    for line in lines:
        match = pattern.search(line)
        if match is None:
            continue
        verdict, name = match.group(1), match.group(2)
        entry = found.setdefault(name, {"seen": Counter(), "first": {}, "last": verdict})
        entry["seen"][verdict] += 1
        entry["first"].setdefault(verdict, line)
        entry["last"] = verdict
    out = []
    for name, entry in found.items():
        seen = entry["seen"]
        verdict = BROKEN if seen[BROKEN] else OK if seen[OK] else entry["last"]
        check = {"name": name, "verdict": verdict, "line": _message(entry["first"][verdict]), "source": source}
        if sum(seen.values()) > 1:
            check["seen"] = dict(seen)
        out.append(check)
    return out


def _message(line: str) -> str:
    parsed = parse(line)
    if parsed.kind == "debug_log":
        return "%s:%d: %s" % (parsed.file, parsed.lineno, parsed.text)
    return parsed.text.strip()


def _rank(check: dict) -> int:
    """Every BROKEN first, then a START that got no verdict, then the rest."""
    return {BROKEN: 0, START: 1}.get(check["verdict"], 2)


# ---- the fixture's lines

def fixture_dir(backup_root: Path, key: str) -> Path:
    if not isinstance(key, str) or _KEY.fullmatch(key) is None:
        raise ValueError("a fixture key is letters, digits and _ (it becomes a folder's name): %r" % (key,))
    return Path(backup_root) / FIXTURES_FOLDER / key


def _own_folder(backup_root: Path, key: str) -> Path:
    """`fixture_dir`, once neither it nor `fixtures/` itself is a symlink: a link would take what is written or
    removed here somewhere else, and nothing here may touch a file outside the backup root. SelfCheckError
    `not_ours` otherwise."""
    folder = fixture_dir(backup_root, key)
    for path in (folder.parent, folder):
        if path.is_symlink():
            raise SelfCheckError("not_ours", "%s is a symlink, not a folder of the harness's: it is not followed, "
                                             "and nothing is kept, read or removed through it" % path)
    return folder


def forget_fixture_lines(backup_root: Path, key: str, detail: str = BEING_MADE) -> None:
    """Before a fixture is made under `key`: whatever was kept for an earlier fixture of that key goes, and a
    record that nothing is kept, with `detail` as the reason, takes its place until `keep_fixture_lines` has kept
    the new run's. So a run that fails anywhere after this leaves no lines of another run to be shown as its
    own. Raises OSError when the old record cannot be removed (the new one is then not written), and
    SelfCheckError for a folder that is a symlink."""
    folder = _own_folder(backup_root, key)
    _forget(folder)
    _say_not_kept(folder, key, detail)


def keep_fixture_lines(backup_root: Path, key: str, snapshot_id: str) -> dict:
    """Keep the TE_SELF_CHECK and TE_MONUMENTS lines of the run that made fixture `key`, from the logs its restore
    copied to `snapshots/<snapshot_id>/run_logs/`, in `fixtures/<key>/`; return the record written.

    First of all, whatever was kept under `key` before is removed. Whatever then fails (SelfCheckError when the
    folder holds no `debug.log` of the run's, OSError when a log cannot be read or the lines cannot be written)
    leaves a record saying that nothing is kept and why, never the lines of an earlier run of that key.

    Every generation of `debug.log` there is read, oldest first, except one whose bytes the snapshot recorded
    among the owner's logs, under any name: the generations a short run did not push out are the owner's
    earlier games (kept as they were, or the last log renamed into them: which of the two a launch does is not
    verified, and both leave the snapshot's bytes), and their lines are not this run's. A log that begins with
    exactly the bytes of the `logs/debug.log` the snapshot recorded was appended to rather than started anew:
    that beginning is skipped, and the record's `prefix_skipped` says so (the fixture run's `debug.log` of
    2026-11-11 held that run's lines alone, so this is a guard, not something seen). When the snapshot's
    manifest cannot be read to tell the owner's bytes apart, nothing is kept. A `fixtures/<key>` that is a
    symlink is refused before anything is removed or written (SelfCheckError `not_ours`)."""
    folder = _own_folder(backup_root, key)
    _forget(folder)
    try:
        record, lines = _run_lines(Path(backup_root), key, snapshot_id)
        folder.mkdir(parents=True, exist_ok=True)
        _write(folder / LINES_FILE, "".join(line + "\n" for line in lines))
        _write(folder / RECORD_FILE, json.dumps(record, indent=1) + "\n")      # last: it vouches for the lines
    except Exception as error:
        try:
            _forget(folder)
            _say_not_kept(folder, key, "its lines could not be kept from snapshot %s: %s" % (snapshot_id, error),
                          snapshot=snapshot_id if isinstance(snapshot_id, str) else None)
        except OSError:
            pass                                # no record at all is read as nothing kept, too
        raise
    return record


def _run_lines(backup_root: Path, key: str, snapshot_id: str) -> tuple[dict, list[str]]:
    """(the record to write, the lines to keep) for the fixture run under `snapshot_id`."""
    if not isinstance(snapshot_id, str) or _RUN_ID.fullmatch(snapshot_id) is None:
        raise SelfCheckError("bad_argument", "%r is not a snapshot's id" % (snapshot_id,))
    snap_dir = backup_root / "snapshots" / snapshot_id
    logs = snap_dir / restore.RUN_LOGS_NAME
    try:
        files = snapshot.load(snap_dir).files
    except (OSError, ValueError) as error:
        raise SelfCheckError("no_manifest", "the manifest of snapshot %s cannot be read (%s), so the owner's logs "
                             "cannot be told from the run's" % (snapshot_id, error)) from error
    owners = {entry.sha256 for rel, entry in files.items() if rel.startswith("logs/")}
    found = files.get(OWNERS_LOG)
    read: list[str] = []
    skipped: list[str] = []
    prefixes: dict[str, int] = {}
    lines: list[str] = []
    for path in _generations(logs):
        if _sha256(path) in owners:
            skipped.append(path.name)
            continue
        start = _found_prefix(path, found)
        if start:
            prefixes[path.name] = start
        lines += marked_lines(path, start=start)[0]
        read.append(path.name)
    if not read:
        raise SelfCheckError("no_run_log", "%s holds no %s of the run's own" % (logs, RUN_LOG))
    record = {"key": key, "save": fixture.FIXTURE_PREFIX + key, "kept": True, "snapshot": snapshot_id,
              "at": stamp(utc_now()), "read": read, "skipped": skipped, "lines": len(lines),
              "self_checks": sum(1 for line in lines if SELF_CHECK in line)}
    if prefixes:
        record["prefix_skipped"] = prefixes
    return record, lines


def _found_prefix(path: Path, found: snapshot.Entry | None) -> int:
    """How many bytes at the start of the log `path` are the log the run's game found (`found`, the snapshot's
    entry for it): its size when `path` begins with exactly those bytes, else 0."""
    if found is None or found.size <= 0 or path.stat().st_size < found.size:
        return 0
    digest = hashlib.sha256()
    left = found.size
    with open(path, "rb") as f:
        while left > 0 and (chunk := f.read(min(_CHUNK, left))):
            digest.update(chunk)
            left -= len(chunk)
    return found.size if left == 0 and digest.hexdigest() == found.sha256 else 0


def _forget(folder: Path) -> None:
    """Remove what was kept in `folder`: the record first, so that no record outlives its lines."""
    for name in (RECORD_FILE, RECORD_FILE + _TEMP_SUFFIX, LINES_FILE, LINES_FILE + _TEMP_SUFFIX):
        (folder / name).unlink(missing_ok=True)


def _say_not_kept(folder: Path, key: str, detail: str, snapshot: str | None = None) -> None:
    record = {"key": key, "save": fixture.FIXTURE_PREFIX + key, "kept": False, "at": stamp(utc_now()),
              "detail": detail}
    if snapshot is not None:
        record["snapshot"] = snapshot
    folder.mkdir(parents=True, exist_ok=True)
    _write(folder / RECORD_FILE, json.dumps(record, indent=1) + "\n")


def fixture_record(backup_root: Path, key: str) -> dict | None:
    """The record written for `key`, or None: there is none, it does not read as one, or its folder is a
    symlink."""
    try:
        record = json.loads((_own_folder(backup_root, key) / RECORD_FILE).read_text("utf-8"))
    except (OSError, ValueError, SelfCheckError):
        return None
    return record if isinstance(record, dict) else None


def drop_orphans(backup_root: Path, user_data: Path) -> list[str]:
    """Remove the kept lines of every fixture whose save, `save games/te_qa_fixture_<key>.v3`, is gone (pruned
    by `fixture.prune`, or deleted by the owner), and return their keys. Only this module's own files are
    removed, and a folder only once it is empty. Nothing is removed while `save games/` cannot be seen: a
    folder that is not mounted would read as every fixture gone."""
    saves = Path(user_data) / fixture.SAVE_FOLDER
    root = Path(backup_root) / FIXTURES_FOLDER
    if not saves.is_dir() or root.is_symlink():
        return []
    try:
        names = sorted(os.listdir(root))
    except (FileNotFoundError, NotADirectoryError):
        return []
    dropped = []
    for key in names:
        folder = root / key
        if _KEY.fullmatch(key) is None or folder.is_symlink() or not folder.is_dir():
            continue
        if os.path.lexists(saves / ("%s%s.v3" % (fixture.FIXTURE_PREFIX, key))):
            continue
        _forget(folder)
        try:
            folder.rmdir()
        except OSError:
            pass                                # something else is in it: not ours to remove
        dropped.append(key)
    return dropped


def _generations(logs: Path) -> list[Path]:
    """`debug.5.log` … `debug.1.log`, `debug.log`: the generations that are there, oldest first."""
    stem, _, suffix = RUN_LOG.partition(".")
    names = ["%s.%d.%s" % (stem, k, suffix) for k in range(GENERATIONS, 0, -1)] + [RUN_LOG]
    return [logs / name for name in names if (logs / name).is_file()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path: Path, text: str) -> None:
    """Write `path` by rename from a temp file made anew: a link left under either name is replaced, not
    followed."""
    temp = path.with_name(path.name + _TEMP_SUFFIX)
    temp.unlink(missing_ok=True)
    with open(temp, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


# ---- a run's verdicts

def _order(run_id) -> tuple[str, int] | None:
    """Where a snapshot's id sorts among the others (snapshot.all_snapshots: the order of taking), or None."""
    match = _RUN_ID.fullmatch(run_id) if isinstance(run_id, str) else None
    return (match.group(1), int(match.group(2) or 1)) if match is not None else None


def resolve_run(backup_root: Path, run_id: str | None = None) -> str:
    """`run_id` once its folder is known to be there, or with None the newest session's run: the newest folder
    of `runs/` that holds a step record (the folder of a run that only made a fixture holds none)."""
    runs = Path(backup_root) / RUNS_FOLDER
    if run_id is not None:
        if _order(run_id) is None or not (runs / run_id).is_dir():
            raise SelfCheckError("no_run", "there is no run %r under %s" % (run_id, runs))
        return run_id
    try:
        names = os.listdir(runs)
    except (FileNotFoundError, NotADirectoryError):
        names = []
    found = [(_order(name), name) for name in names
             if _order(name) is not None and (runs / name / STEPS_FILE).is_file()]
    if not found:
        raise SelfCheckError("no_run", "no session has left a run folder under %s yet" % runs)
    return max(found)[1]


def of_run(backup_root: Path, run_id: str) -> dict:
    """The self-check verdicts of run `run_id` (see `resolve_run`), read from files alone:

        run       the run's id
        broken    the names of the checks that logged BROKEN, each once, whichever source logged it
        counts    how many rows of `checks` ended on each verdict
        checks    one row per check and source (`verdicts`): every BROKEN first, then a START with no verdict.
                  A check the fixture's run and the session both logged has a row for each
        fixture   the lines of the run that made the fixture this run loaded: `key`, `kept`, and when kept
                  `file` and the record's `snapshot`, `at`, `lines` (TE_MONUMENTS lines too), `self_checks` and
                  `prefix_skipped`; else `detail` says why this run is shown none (`_fixture_part`)
        session   the session's own lines: `file` (the run folder's debug.log), `lines`, `gaps`, how often
                  lines were lost to the log's rotation, when that happened, and `unvouched`, why the session's
                  rows cannot be vouched for, when another game ran beside the run's (`_other_game`); each
                  such row then carries `unvouched: true`

    Raises OSError when a file of the run is there and cannot be read."""
    run_dir = Path(backup_root) / RUNS_FOLDER / run_id
    log = run_dir / RUN_LOG
    session_lines, gaps = marked_lines(log, (SELF_CHECK,))
    kept, fixture_lines = _fixture_part(Path(backup_root), run_id, read_steps(run_dir))
    session_checks = verdicts(session_lines, "session")
    session_part: dict = {"file": str(log), "lines": len(session_lines)}
    if gaps:
        session_part["gaps"] = gaps
    other = _other_game(Path(backup_root), run_id)
    if other is not None:
        session_part["unvouched"] = other
        for check in session_checks:
            check["unvouched"] = True
    checks = verdicts(fixture_lines, "fixture") + session_checks
    checks.sort(key=_rank)
    return {"run": run_id, "broken": list(dict.fromkeys(c["name"] for c in checks if c["verdict"] == BROKEN)),
            "counts": dict(Counter(check["verdict"] for check in checks)), "checks": checks,
            "fixture": kept, "session": session_part}


def _other_game(backup_root: Path, run_id: str) -> str | None:
    """Why the session's lines of run `run_id` cannot be vouched for, or None. The run's journal (its snapshot's)
    says another Victoria 3 process was seen beside the run's game (`watch` records `other_game`), or its restore
    held for one (`other_game_ran`, `other_game_running`). No proof of the run's own game being alive rules out
    a second game writing the same `logs/`, and whether two can share them is not verified, so such a run's
    lines are shown and marked. A snapshot that is gone was restored, which a run with another game seen never
    is: None."""
    snap = snapshot.Snapshot(id=run_id, dir=backup_root / "snapshots" / run_id, files={}, listing=frozenset())
    try:
        journal = snapshot.journal(snap)
    except OSError:
        return None
    seen = ["pid %s (started %s)" % (e.get("pid"), e.get("created")) for e in journal if e.get("event") == "other_game"]
    if seen:
        return ("`watch` saw another Victoria 3 process beside the run's game (%s): it may have written the same "
                "logs, so the session's lines may not all be the run's" % ", ".join(seen))
    held = [e.get("reason") for e in journal
            if e.get("event") == "held" and e.get("reason") in ("other_game_ran", "other_game_running")]
    if held:
        return ("the run's restore held for another game (%s): it may have written the same logs, so the "
                "session's lines may not all be the run's" % held[-1])
    return None


def _fixture_part(backup_root: Path, run_id: str, steps: list[dict]) -> tuple[dict, list[str]]:
    """(what the reply says of the fixture's lines, the lines), from the run's `fixture` step and the record
    kept for that fixture. The lines are shown only when the record says they were kept, they are still there,
    and they were kept from a run before this one: a fixture made again under its key after this run is another
    world's, and its lines are not this run's."""
    step = next((s for s in reversed(steps) if s.get("verb") == "fixture"), None)
    save = step.get("save") if step is not None else None
    if step is None or step.get("outcome") not in ("found", "made") or not isinstance(save, str):
        why = ("the game ran on a save of the owner's, not on the fixture" if step is not None
               and step.get("outcome") == "not_used" else "the run's steps name no fixture that was loaded")
        return {"key": None, "kept": False, "detail": why}, []
    key = save[len(fixture.FIXTURE_PREFIX):] if save.startswith(fixture.FIXTURE_PREFIX) else ""
    if _KEY.fullmatch(key) is None:
        return {"key": None, "kept": False, "detail": "the run's `fixture` step names no fixture's save"}, []

    def none(detail: str) -> tuple[dict, list[str]]:
        return {"key": key, "kept": False, "detail": "%s: %s" % (save, detail)}, []

    try:
        folder = _own_folder(backup_root, key)
    except SelfCheckError as error:
        return none(error.detail)
    record = fixture_record(backup_root, key)
    if record is None:
        if os.path.lexists(folder / RECORD_FILE):
            return none("its record, %s, does not read as one" % (folder / RECORD_FILE))
        return none("it was made before the lines of a fixture's run were kept (#1601). The lines a new game logs "
                    "at its setup are then only in the snapshot of the run that made it, `run_logs/debug.log`, "
                    "while that lasts")
    if record.get("kept") is not True:
        return none(str(record.get("detail") or "its record does not say its lines were kept"))
    kept_from, this = _order(record.get("snapshot")), _order(run_id)
    if kept_from is None or this is None or kept_from >= this:
        return none("it was made again after this run (by the run of snapshot %s), so the lines kept are not "
                    "those of the fixture this run loaded" % record.get("snapshot"))
    file = folder / LINES_FILE
    if not file.is_file():
        return none("its record says %s lines were kept from snapshot %s, but %s is gone"
                    % (record.get("lines"), record.get("snapshot"), file))
    lines = marked_lines(file)[0]
    part = {"key": key, "kept": True, "file": str(file)}
    part.update((name, record.get(name)) for name in ("snapshot", "at", "lines", "self_checks"))
    if record.get("prefix_skipped"):
        part["prefix_skipped"] = record["prefix_skipped"]
    return part, lines
