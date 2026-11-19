"""The game's crash reporter (#1905): keep it away from a run, and close the one a run's crash left up.

A crash brings up the "Paradox Crash Reporter" (`CrashReporter.exe`, in the install's
`binaries/crash_reporter/binaries/`), which waits on the desktop for someone to answer it. While it is up it holds
the crashed game's `logs/` open, so the restore cannot rename the owner's logs back over the run's (`Permission
denied` on `logs/code_revisions.log`, twice on 2026-11-19), and an unattended night stops at the first crash until
someone closes the dialog in the morning. The owner asked for the harness to be able to close it (2026-11-19).

Two things keep that from happening:

* Every launch passes NO_CRASH_REPORTER (`with_flag`, added by `launch` itself, whatever the caller gave). The
  1.15.2 binary describes it as "Never launch the crash reporter app on a crash, so an unattended run leaves no
  modal window behind". Live on 2026-11-19 (run 2 of docs/testing/game-qa-results-2026-11-19.md) a game started
  with it crashed, no reporter came up and the restore went through.
* `restore` and `recover` close a reporter the run's own crash left up (`settle`). They call it only once every
  hold has been decided and the restore is about to make its first change (restore.restore's `before_changes`), and
  once more after a log's rename was refused anyway (a reporter that came up after the first look; the logs go
  back last, so that too comes after every hold). So a run that is held (the owner may have played since, `watch`
  lost sight of the game, another game ran) never has a reporter closed. A reporter is the run's when its
  executable is this install's reporter, it started at or after the run's game (both Windows process times) and at
  most AFTER_EXIT_S after the run's end as the journal knows it (`game_exited`, else the last sign of life), the
  snapshot has no verdict yet, no Victoria 3 process is running, and `watch` neither saw another game nor failed a
  look. Any other reporter of the install is listed (`reporters_left`, with `why`) and left alone: it may be the
  crash of the owner's own game.

Closing one ends its process (PowerShell `Stop-Process -Force`, the owner's End Task) once its pid, name and start
time are proved, through the one process object, the reporter listed; nothing is answered in its window, so no
report is sent. The crash's own folder under the user data's `crashes/` (its dump, `exception.txt` and the copied
logs) is the game's and stays. Nothing here ever raises into a restore: whatever goes wrong is a note.
"""
from __future__ import annotations

import base64
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath

from game_qa import gate, snapshot

NO_CRASH_REPORTER = "-no_crash_reporter"
# The install's reporter, under base_game_path (1.15.2, 2026-11-19). The game's binary names the same parts
# (`crash_reporter/`, `/binaries/CrashReporter.exe`). An install without it starts no reporter, and nothing is
# looked for (a game-less machine, and every test that does not make one).
REPORTER_EXE = Path("binaries", "crash_reporter", "binaries", "CrashReporter.exe")
PROCESS_NAME = "CrashReporter"
# How long after the run's end (`game_exited`, else the last sign of life) a reporter may have started and still be
# the run's: the reporter comes up as the game dies, and `watch` sees the exit at its next look (10 s apart at
# most). Windows' process times are compared with the backup drive's journal times, both the host's clock.
AFTER_EXIT_S = 120.0
CLOSE_WAIT_S = 10                       # from Stop-Process to the process gone, inside the one PowerShell call
CLOSED, GONE, STILL_UP = "closed", "gone", "still_up"
# The journal's signs that the run's game was alive, for its end when `game_exited` is missing.
_SIGNS_OF_LIFE = ("started", "watching", "watch_resumed", "heartbeat")
_VERDICTS = ("restored", "held")
_run = subprocess.run                   # every PowerShell call goes through this (conftest.py guards it in tests)

# PowerShell writes a pipe in the console's code page (437 here, live 2026-11-19), in which a path's `ö` is no UTF-8
# byte: the output is switched to UTF-8 first, and anything that still does not decode is replaced, so an odd path
# reads as a path that matches nothing rather than an error.
_UTF8_OUT = "try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }; "
# One line per reporter, `<pid> <start time> <parent pid> <executable path>`, then gate.LIST_END. A start time or
# parent that cannot be read is `unknown`, and a path that cannot be read is left empty: such a reporter is never
# taken for the run's. The path comes last, since it holds spaces. The parent is recorded, not judged: which
# process starts the reporter has not been seen yet.
LIST_REPORTERS = (
    "powershell.exe",
    "-NoProfile",
    "-Command",
    "$ErrorActionPreference = 'Stop'; " + _UTF8_OUT +
    "foreach ($p in @(Get-Process -Name CrashReporter -ErrorAction SilentlyContinue)) { "
    "$start = 'unknown'; try { $start = $p.StartTime.ToUniversalTime().ToString('o') } catch { }; "
    "$parent = 'unknown'; try { $c = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $p.Id); "
    "if ($c) { $parent = [string]$c.ParentProcessId } } catch { }; "
    "$path = ''; try { $path = [string]$p.Path } catch { }; "
    "'{0} {1} {2} {3}' -f $p.Id, $start, $parent, $path }; "
    "'te_qa_end'",
)

_FRACTION = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?Z?$")


@dataclass(frozen=True)
class Reporter:
    pid: int
    created: str                        # UTC ISO-8601 as Windows reports it, or gate.UNKNOWN_START
    parent: int | None                  # the parent process id, None when it could not be read
    path: str                           # the executable, "" when it could not be read

    def as_dict(self) -> dict:
        return asdict(self)


def with_flag(game_args: Sequence[str]) -> list[str]:
    """`game_args` with NO_CRASH_REPORTER at the end, unless one is there already in any spelling (without its
    leading `-` or `/`, in any case)."""
    args = list(game_args)
    if not any(arg.lstrip("-/").lower() == NO_CRASH_REPORTER.lstrip("-") for arg in args):
        args.append(NO_CRASH_REPORTER)
    return args


def _powershell(argv: list[str], what: str, timeout: float, run=None) -> list[str]:
    """Run `argv` and return its non-empty output lines, stripped. Raises gate.GateError when it could not be run,
    or its output could not be read."""
    try:
        out = (run or _run)(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise gate.GateError(f"could not {what}: {exc!r}") from exc
    lines = [line.strip() for line in (out.stdout or "").splitlines() if line.strip()]
    if not lines or lines[-1] != gate.LIST_END:
        raise gate.GateError(f"{what} did not finish (exit {out.returncode}): {(out.stdout or '').strip()[:300]!r} "
                             f"{(out.stderr or '').strip()[:300]!r}")
    return lines[:-1]


def list_reporters(run=None) -> list[Reporter]:
    """Every running CrashReporter process, whoever's (the name is matched in any case: another program's
    `crashreporter.exe` too). Raises gate.GateError unless the listing ran to its end (as `gate.list_games`)."""
    found = []
    for line in _powershell(list(LIST_REPORTERS), "list the crash reporter processes", 30, run):
        parts = line.split(maxsplit=3)
        if len(parts) < 3 or not parts[0].isdigit():
            raise gate.GateError(f"a line of the crash reporter listing does not read as one: {line!r}")
        parent = int(parts[2]) if parts[2].isdigit() else None
        found.append(Reporter(int(parts[0]), parts[1], parent, parts[3] if len(parts) == 4 else ""))
    return found


def close(reporter: Reporter, run=None) -> str:
    """End `reporter`'s process: CLOSED once it is gone, GONE when no process with its pid, name and start time was
    there to end (it had exited, or the pid is another program's by now), STILL_UP when it outlived CLOSE_WAIT_S.
    The process is looked up once, checked, and that same process object is stopped, so a pid reused in between is
    never ended; it is checked again after. Raises gate.GateError unless the call ran to its end."""
    same = (f"$q = Get-Process -Id {int(reporter.pid)} -ErrorAction SilentlyContinue; $same = $false; "
            f"if ($q) {{ try {{ $same = ($q.ProcessName -eq '{PROCESS_NAME}') -and "
            f"($q.StartTime.ToUniversalTime().ToString('o') -eq {gate._powershell_quoted(reporter.created)}) }} "
            "catch { } }; ")
    script = ("$ErrorActionPreference = 'Stop'; " + same +
              "if (-not $same) { 'gone' } else { "
              "try { Stop-Process -InputObject $q -Force } catch { }; "
              f"$deadline = (Get-Date).AddSeconds({CLOSE_WAIT_S}); "
              "do { Start-Sleep -Milliseconds 200; " + same + "} while ($same -and (Get-Date) -lt $deadline); "
              "if ($same) { 'still_up' } else { 'closed' } }; "
              "'te_qa_end'")
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    lines = _powershell(["powershell.exe", "-NoProfile", "-EncodedCommand", encoded],
                        f"end crash reporter pid {reporter.pid}", CLOSE_WAIT_S + 30, run)
    if len(lines) != 1 or lines[0] not in (CLOSED, GONE, STILL_UP):
        raise gate.GateError(f"ending crash reporter pid {reporter.pid} answered {lines!r}")
    return lines[0]


def windows_key(path: str) -> str:
    """A Windows path as compared here: backslashes, no trailing one, lower case (Windows paths ignore case)."""
    return str(PureWindowsPath(path.replace("/", "\\"))).rstrip("\\").lower()


def this_installs(reporters: Sequence[Reporter], exe_windows: str) -> list[Reporter]:
    """The reporters whose executable is this install's (`exe_windows`), and those whose path could not be read:
    those may be too. Another Paradox game's reporter carries the same name from its own folder."""
    key = windows_key(exe_windows)
    return [r for r in reporters if not r.path or windows_key(r.path) == key]


def runs_own(journal: Sequence[dict], reporters: Sequence[Reporter],
             exe_windows: str) -> tuple[list[Reporter], list[dict]]:
    """The reporters (of this install's, `this_installs`) that the run's own crash left up, and the others, each
    a dict with `why`. The rules are the module docstring's; the caller has made sure no Victoria 3 process runs and
    the snapshot has no verdict."""
    ours: list[Reporter] = []
    left: list[dict] = []
    starts = [e for e in journal if e.get("event") == "started"]
    game = _time(str(starts[-1].get("created"))) if starts else None
    exits = [t for t in (_time(str(e.get("at"))) for e in journal if e.get("event") == "game_exited") if t]
    alive = [t for t in (_time(str(e.get("at"))) for e in journal if e.get("event") in _SIGNS_OF_LIFE) if t]
    end = exits[-1] if exits else (max(alive) if alive else None)
    events = {e.get("event") for e in journal}
    key = windows_key(exe_windows)
    for reporter in this_installs(reporters, exe_windows):
        when = _time(reporter.created)
        if windows_key(reporter.path) != key:
            why = "its executable could not be read, so it cannot be told from another program's"
        elif game is None or end is None:
            why = "this run recorded no start time for its game, so the reporter cannot be told to be its"
        elif when is None:
            why = "its start time could not be read"
        elif when < game:
            why = "it started before this run's game did: an earlier crash, perhaps of the owner's own game"
        elif "other_game" in events:
            why = "`watch` saw another game during this run: the reporter may be that game's"
        elif "look_failed" in events:
            why = "`watch` failed a look during this run, and another game may have run then"
        elif when > end + timedelta(seconds=AFTER_EXIT_S):
            why = (f"it started {(when - end).total_seconds():.0f} s after this run's game was last known alive or "
                   f"exited, more than {AFTER_EXIT_S:g} s: another game's crash")
        else:
            ours.append(reporter)
            continue
        left.append(dict(reporter.as_dict(), why=why))
    return ours, left


def settle(snap: snapshot.Snapshot, games: Sequence, exe: Path | None,
           windows_path: Callable[[Path], str] | None = None) -> dict:
    """Close the crash reporters the run's own crash left up (`runs_own`). Callers run it only once every hold has
    been decided (the module docstring). Returns the notes for the reply: `reporters_closed` (each ended one, with
    `outcome` CLOSED or GONE, and `not_journaled` when its journal entry could not be written), `reporters_left`
    (the others of this install, with `why`; also one that outlived its stop, or whose stop could not be run) and
    `reporters_unlisted` (they could not be listed: nothing was closed). Each one ended is journaled
    (`reporter_closed`). Nothing is looked for, and {} returned, when `exe` (this install's reporter) is None or not
    there, a Victoria 3 process is running (`games`: the reporter may be the running game's), the snapshot has a
    verdict already, or the run recorded no `started`. Never raises: a failure is a note, so that the restore goes
    on as it would have without this."""
    try:
        journal = snapshot.journal(snap)
        events = {e.get("event") for e in journal}
        if games or exe is None or events & set(_VERDICTS) or "started" not in events or not exe.is_file():
            return {}
        exe_windows = (windows_path or gate.windows_path)(exe)
        ours, left = runs_own(journal, list_reporters(), exe_windows)
    except Exception as exc:        # never in the restore's way
        return {"reporters_unlisted": str(exc) if isinstance(exc, gate.GateError) else f"{type(exc).__name__}: {exc}"}
    closed: list[dict] = []
    for reporter in ours:
        try:
            outcome = close(reporter)
        except Exception as exc:
            left.append(dict(reporter.as_dict(), why=f"the run's, but ending it failed: {exc}"))
            continue
        if outcome == STILL_UP:
            left.append(dict(reporter.as_dict(), why=f"the run's, and still up {CLOSE_WAIT_S} s after it was ended"))
            continue
        entry = dict(reporter.as_dict(), outcome=outcome)
        try:
            snapshot.record(snap, "reporter_closed", pid=reporter.pid, created=reporter.created,
                            parent=reporter.parent, path=reporter.path, outcome=outcome)
        except OSError as exc:
            entry["not_journaled"] = str(exc)
        closed.append(entry)
    notes: dict = {}
    if closed:
        notes["reporters_closed"] = closed
    if left:
        notes["reporters_left"] = left
    return notes


def merge(notes: dict, more: dict) -> None:
    """Add `settle`'s notes `more` to `notes`: the lists are joined (a reporter listed twice is kept once, by pid
    and start time), and the latest `reporters_left` and `reporters_unlisted` stand, since they say what is up now."""
    if more.get("reporters_closed"):
        seen = {(r["pid"], r["created"]) for r in notes.get("reporters_closed", [])}
        notes["reporters_closed"] = [*notes.get("reporters_closed", []),
                                     *(r for r in more["reporters_closed"] if (r["pid"], r["created"]) not in seen)]
    for name in ("reporters_left", "reporters_unlisted"):
        if name in more:
            notes[name] = more[name]
        else:
            notes.pop(name, None)


def held_open_hint(exc: OSError, notes: dict) -> str:
    """What to add to a restore's `Permission denied` detail: who may hold the file. Empty for any other error."""
    if not isinstance(exc, PermissionError):
        return ""
    left = notes.get("reporters_left") or []
    if left:
        named = "; ".join(f"pid {r['pid']} (started {r['created']}): {r['why']}" for r in left)
        return (f". A crash reporter is up and was left alone, not being this run's ({named}): a crashed game's "
                "reporter holds its logs open. Ask the owner to close it, then run `python3 -m game_qa recover`")
    if notes.get("reporters_unlisted"):
        return (f". The crash reporters could not be listed ({notes['reporters_unlisted']}): one may hold the file "
                "open. `python3 -m game_qa doctor` lists them; once nothing holds the file, `recover`")
    return (". Windows refused the change, most likely because another program has the file open (an editor, a "
            "virus scan): once it is closed, `python3 -m game_qa recover`")


def _time(text: str) -> datetime | None:
    """A Windows creation time (`2026-11-10T23:06:35.4149252Z`) or a journal time (`2026-11-10T23:06:15Z`) as a
    datetime; None for anything else (gate.UNKNOWN_START among them, and a date no calendar has)."""
    found = _FRACTION.match(text or "")
    if not found:
        return None
    try:
        when = datetime.strptime(found.group(1), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return when + timedelta(seconds=float("0." + found.group(2))) if found.group(2) else when
