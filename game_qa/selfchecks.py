"""The mod's self-check lines: kept with the fixture, and reported for a run (#1601).

The mod's script answers its own engine questions once a game with `debug_log` lines of the form
`TE_SELF_CHECK OK|BROKEN|START <name> ...` (CLAUDE.md, "In-game checks"); the play-test lists wait for them.

    <backup root>/runs/<id>/debug.log          a session's copy of the game's log, appended at each verb (session.py)
    <backup root>/fixtures/<key>/lines.log     the TE_SELF_CHECK and TE_MONUMENTS lines of the run that made the
                                               fixture `te_qa_fixture_<key>.v3`, as logged, oldest first
    <backup root>/fixtures/<key>/record.json   which run that was and what was kept; written last, so a record
                                               means its lines are whole

The lines the game logs while it sets a new game up exist only in the log of the run that makes the fixture: the
save is made after them, so no session logs them again. That log is in the run's snapshot (`run_logs/`), which is
pruned after five more snapshots, while the fixture is used for as long as the build is unchanged. So they are
kept here when the fixture is made (`keep_fixture_lines`) and go when the fixture's save has gone (`drop_orphans`).

Nothing here writes outside `<backup root>/fixtures/`, and of the user-data folder only the names of the
fixtures in `save games/` are looked at. The line's pattern is `scripts/analysis/log_triage.py`'s, so the two
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
BROKEN, START, OK = "BROKEN", "START", "OK"

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


def marked_lines(path: Path, markers: tuple[str, ...] = KEPT_MARKERS) -> tuple[list[str], int]:
    """(the lines of the log `path` that hold one of `markers`, in order; how often the session's follower
    lost lines to rotation, which a run folder's copy marks with GAP_MARKER). A file that is not there has none."""
    wanted = [marker.encode("utf-8") for marker in markers]
    gap = GAP_MARKER.encode("utf-8")
    lines: list[str] = []
    gaps = 0
    try:
        with open(path, "rb") as f:
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


def keep_fixture_lines(backup_root: Path, key: str, snapshot_id: str) -> dict:
    """Keep the TE_SELF_CHECK and TE_MONUMENTS lines of the run that made fixture `key`, from the logs its restore
    copied to `snapshots/<snapshot_id>/run_logs/`, in `fixtures/<key>/`; return the record written.

    Every generation of `debug.log` there is read, oldest first, except one whose bytes the snapshot recorded
    among the owner's logs, under any name: the generations a short run did not push out are the owner's
    earlier games (kept as they were, or the last log renamed into them: which of the two a launch does is not
    verified, and both leave the snapshot's bytes), and their lines are not this run's. When the snapshot's
    manifest cannot be read to tell them apart, only `debug.log` itself is read. The fixture run's `debug.log`
    of 2026-11-11 held that run's lines alone, so a launch does not append to the log it finds.

    Raises SelfCheckError when that folder holds no `debug.log` of the run's, and OSError when the lines cannot
    be written; a record already there is replaced (the fixture was made again under the same key)."""
    folder = fixture_dir(backup_root, key)
    if not isinstance(snapshot_id, str) or _RUN_ID.fullmatch(snapshot_id) is None:
        raise SelfCheckError("bad_argument", "%r is not a snapshot's id" % (snapshot_id,))
    snap_dir = Path(backup_root) / "snapshots" / snapshot_id
    logs = snap_dir / restore.RUN_LOGS_NAME
    try:
        owners = {entry.sha256 for rel, entry in snapshot.load(snap_dir).files.items() if rel.startswith("logs/")}
    except (OSError, ValueError):
        owners = None
    read: list[str] = []
    skipped: list[str] = []
    lines: list[str] = []
    for path in _generations(logs):
        if owners is None and path.name != RUN_LOG:
            skipped.append(path.name)
            continue
        if owners is not None and _sha256(path) in owners:
            skipped.append(path.name)
            continue
        lines += marked_lines(path)[0]
        read.append(path.name)
    if not read:
        raise SelfCheckError("no_run_log", "%s holds no %s of the run's own, so there is nothing to keep" % (logs, RUN_LOG))
    record = {"key": key, "save": fixture.FIXTURE_PREFIX + key, "snapshot": snapshot_id,
              "kept_at": stamp(utc_now()), "read": read, "skipped": skipped, "lines": len(lines),
              "self_checks": sum(1 for line in lines if SELF_CHECK in line)}
    folder.mkdir(parents=True, exist_ok=True)
    # The record goes first and comes back last, so that no record ever vouches for another run's lines.
    (folder / RECORD_FILE).unlink(missing_ok=True)
    _write(folder / LINES_FILE, "".join(line + "\n" for line in lines))
    _write(folder / RECORD_FILE, json.dumps(record, indent=1) + "\n")
    return record


def fixture_record(backup_root: Path, key: str) -> dict | None:
    """The record `keep_fixture_lines` wrote for `key`, or None: none was kept, or it does not read."""
    try:
        record = json.loads((fixture_dir(backup_root, key) / RECORD_FILE).read_text("utf-8"))
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def drop_orphans(backup_root: Path, user_data: Path) -> list[str]:
    """Remove the kept lines of every fixture whose save, `save games/te_qa_fixture_<key>.v3`, is gone (pruned
    by `fixture.prune`, or deleted by the owner), and return their keys. Only this module's own files are
    removed, and a folder only once it is empty. Nothing is removed while `save games/` cannot be seen: a
    folder that is not mounted would read as every fixture gone."""
    saves = Path(user_data) / fixture.SAVE_FOLDER
    root = Path(backup_root) / FIXTURES_FOLDER
    if not saves.is_dir():
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
        for name in (RECORD_FILE, LINES_FILE, RECORD_FILE + _TEMP_SUFFIX, LINES_FILE + _TEMP_SUFFIX):
            (folder / name).unlink(missing_ok=True)
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
    temp = path.with_name(path.name + _TEMP_SUFFIX)
    with open(temp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


# ---- a run's verdicts

def resolve_run(backup_root: Path, run_id: str | None = None) -> str:
    """`run_id` once its folder is known to be there, or with None the newest session's run: the newest folder
    of `runs/` that holds a step record (the folder of a run that only made a fixture holds none)."""
    runs = Path(backup_root) / RUNS_FOLDER
    if run_id is not None:
        if not isinstance(run_id, str) or _RUN_ID.fullmatch(run_id) is None or not (runs / run_id).is_dir():
            raise SelfCheckError("no_run", "there is no run %r under %s" % (run_id, runs))
        return run_id
    try:
        names = os.listdir(runs)
    except (FileNotFoundError, NotADirectoryError):
        names = []
    found = []
    for name in names:
        match = _RUN_ID.fullmatch(name)
        if match is not None and (runs / name / STEPS_FILE).is_file():
            found.append(((match.group(1), int(match.group(2) or 1)), name))
    if not found:
        raise SelfCheckError("no_run", "no session has left a run folder under %s yet" % runs)
    return max(found)[1]


def of_run(backup_root: Path, run_id: str) -> dict:
    """The self-check verdicts of run `run_id` (see `resolve_run`), read from files alone:

        run       the run's id
        broken    the names of the checks that logged BROKEN
        counts    how many checks ended on each verdict
        checks    one entry per check and source (`verdicts`): every BROKEN first, then a START with no verdict
        fixture   the lines of the run that made the fixture this run loaded: `key`, `kept`, and when kept
                  `file` and the record's `snapshot`, `kept_at`, `lines` (TE_MONUMENTS lines too) and
                  `self_checks`; else `detail` says why there are none
        session   the session's own lines: `file` (the run folder's debug.log), `lines`, and `gaps`, how often
                  lines were lost to the log's rotation, when that happened

    A check the fixture's run and the session both logged is listed once for each."""
    run_dir = Path(backup_root) / RUNS_FOLDER / run_id
    log = run_dir / RUN_LOG
    session_lines, gaps = marked_lines(log, (SELF_CHECK,))
    kept, fixture_lines = _fixture_part(Path(backup_root), read_steps(run_dir))
    checks = verdicts(fixture_lines, "fixture") + verdicts(session_lines, "session")
    checks.sort(key=_rank)
    session_part: dict = {"file": str(log), "lines": len(session_lines)}
    if gaps:
        session_part["gaps"] = gaps
    return {"run": run_id, "broken": [check["name"] for check in checks if check["verdict"] == BROKEN],
            "counts": dict(Counter(check["verdict"] for check in checks)), "checks": checks,
            "fixture": kept, "session": session_part}


def _fixture_part(backup_root: Path, steps: list[dict]) -> tuple[dict, list[str]]:
    """(what the reply says of the fixture's lines, the lines), from the run's `fixture` step."""
    step = next((s for s in reversed(steps) if s.get("verb") == "fixture"), None)
    save = step.get("save") if step is not None else None
    if step is None or step.get("outcome") not in ("found", "made") or not isinstance(save, str):
        why = ("the game ran on a save of the owner's, not on the fixture" if step is not None
               and step.get("outcome") == "not_used" else "the run's steps name no fixture that was loaded")
        return {"key": None, "kept": False, "detail": why}, []
    key = save[len(fixture.FIXTURE_PREFIX):] if save.startswith(fixture.FIXTURE_PREFIX) else ""
    record = fixture_record(backup_root, key) if _KEY.fullmatch(key) else None
    if record is None:
        return {"key": key or None, "kept": False,
                "detail": "no lines were kept for %s: it was made before they were kept (#1601), or keeping them "
                          "failed (the `fixture_lines` step of the run that made it says). The lines a new game "
                          "logs at its setup are then only in that run's snapshot, `run_logs/debug.log`, while "
                          "it lasts" % save}, []
    file = fixture_dir(backup_root, key) / LINES_FILE
    lines = marked_lines(file)[0]
    part = {"key": key, "kept": True, "file": str(file)}
    part.update((name, record.get(name)) for name in ("snapshot", "kept_at", "lines", "self_checks"))
    return part, lines
