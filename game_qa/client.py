"""The session's command-line verbs: thin clients of the session server (`game_qa/server.py`), and a session's
real wiring (its paths, `run_cli`, `spawn_watch`, the Windows helper).

    python3 -m game_qa start --permission "asked 12:40" [--as TAG] [--save NAME] [--setup NAME=FILE]...
                       [--playset mod_only|current] [--switch-rule RULE=SETTING]... [--owner-confirmed-busy]
                       [--game-arg FLAG]... [--add-mod WINDOWS_PATH]...
                                             # a game on the deployed build, on the fixture or on NAME; a
                                             # switched rule is switched in a copy of the fixture, as of its
                                             # second day (the reply's `rules` says what the save holds); a
                                             # game arg from session.GAME_ARGS; a variant mod folder, loaded
                                             # after the playset and before the overlay
    python3 -m game_qa console "<text>"      # one console command, with its reply
    python3 -m game_qa run-setup NAME        # a setup, through its event: its log lines
    python3 -m game_qa add-setup NAME=FILE   # a new setup for the running game: it reloads the overlay's effects
                                             # (about 90 s), and the reply says the game logged the new revision
    python3 -m game_qa press esc             # one key in the game itself (a probe's verb: shot before and after)
    python3 -m game_qa events                # the pending events
    python3 -m game_qa pick INDEX [EVENT]    # an option of a pending event (the oldest, or EVENT's)
    python3 -m game_qa read "<expr>"...      # triggers and values, evaluated at the debugger's breakpoint
    python3 -m game_qa tag TAG               # play another country
    python3 -m game_qa enter-game            # the two clicks past the country-select screen, proven
    python3 -m game_qa advance DAYS          # let at least DAYS game days pass
    python3 -m game_qa shot                  # a screenshot of the game's window, into the run folder
    python3 -m game_qa click X Y             # one click at fractions of the window (0.5 0.5 is its middle),
                                             # then a screenshot: for the engine's tool windows
    python3 -m game_qa click [X Y] --console [--input-line X Y]
                                             # then a click on the console's input line, which gives the
                                             # keyboard back (a click into a tool window takes it)
    python3 -m game_qa wheel X Y N           # N notches of the mouse wheel at X, Y (positive scrolls up), then a shot
    python3 -m game_qa drag X1 Y1 X2 Y2      # press at X1, Y1, move, release at X2, Y2, then a shot
    python3 -m game_qa profiler-roots [--box L T R B] [--as-shown]
                                             # the script profiler at its roots, shot at the window's own size,
                                             # and its call graph cropped out of the shot (--as-shown: as it is,
                                             # nothing typed)
    python3 -m game_qa try-event EVENT [--setup NAME] --read "<expr>"...
                                             # each option of EVENT: setup, fire, read, pick, read; exit 0 only
                                             # when every option fired and was picked
    python3 -m game_qa stop                  # end the game, put the owner's files back, end the server (it
                                             # serves on when the stop can be run again: `stop` again)
    python3 -m game_qa status                # the server and its session
    python3 -m game_qa selfchecks [--run ID] # the verdicts of the mod's TE_SELF_CHECK lines in a run (the newest
                                             # by default), the fixture's run's included; needs no session
    python3 -m game_qa profile start         # clear the tick timings and turn the script profiler on
    python3 -m game_qa profile dump [LABEL]  # both dumps, copied into the run folder as tt_LABEL.csv, sp_LABEL.txt
    python3 -m game_qa profile summary [LABEL [LABEL2]] [--run ID] [--top N]
                                             # wall clock per frame type, top tick tasks, script by file, for the
                                             # window up to LABEL or between the two; needs no session
    python3 -m game_qa doctor                # is this machine ready for a session? (starts nothing)
    python3 -m game_qa remove-overlay        # the overlay folder an earlier run left, once nothing can use it

`start` refuses `session_running` while `<backup root>/session.json` names a server that is up, removes a stale one
(nothing listens on its port and its process is gone) and says so, spawns `python3 -m game_qa session-serve`
detached (its own session and process group, stdin closed, its output to `<backup root>/runs/session-serve-*.log`),
waits for it to listen, and posts `start`. Every other verb posts to the port in session.json: no file, or nothing
listening there, is `no_session`; no answer in time is `no_answer`, and nothing is ended for it. Every request
carries its expiry, the moment this client stops waiting: the server never begins it after that (`expired`), so a
verb given up on is never run later. Each verb prints one JSON object and exits 0, or 2 for a refusal, a hold or an
error.
"""
from __future__ import annotations

import http.client
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from game_qa import gate, overlay, restore, server, session, snapshot
from game_qa.helper import ProcessHelper, to_windows_path
from game_qa.report import read_steps, utc_now
from game_qa import profiling, selfchecks

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS = "runs"
WATCH_LOG = "watch.log"
SERVER_WAIT_S = 30.0                    # from spawning the server to its session.json
POLL_S = 0.2
STATUS_TIMEOUT_S = 10.0                 # a server that has not answered `status` by then is busy, not dead
VERB_TIMEOUT_S = 300.0                  # a console command may wait 120 s for the game to come to the front
ENTER_TIMEOUT_S = 1500.0
# add-setup waits session.RELOAD_WAIT_S (300 s) for the reload (about 90 s, live), a last look may take a console
# command's 30 s and LOADED_WAIT_S more, and the debugger is attached again: about 350 s, with room.
ADD_SETUP_TIMEOUT_S = 600.0
LONG_TIMEOUT_S = 900.0                  # try-event, and advance's rounds
ADVANCE_TIMEOUT_S = ENTER_TIMEOUT_S + LONG_TIMEOUT_S     # advance enters the fixture's game first if need be
# The worst cases, from the waits the session and the fixture allow themselves:
#   enter-game, with each ensure_open and console run counted with one foreground wait (FOREGROUND_WAIT_S 120),
#   the attach's requests at dap's 30 s, and the sends, closes, hotkeys and resumes as quick: the two ensure_opens
#   before the clicks (2 x (30 + 120 + PROBE_ARRIVAL_S 6) = 312), the settles (CLICK_SETTLE_S 1 + ENTER_SETTLE_S
#   10), the console after Start (ENTER_WAIT_S 90 + one try in flight, 156: 246), the new attach (4 requests, and
#   DRAIN_S: 121), the tag (120 + ARRIVAL_S 5 + its reply 30: 155), the date (STOP_WAIT_S 15 + DATE_WAIT_S 5), and
#   the unpaused proof with its second pause key (PROOF_S 3; twice the close's 0.5, an ensure_open 156, and two
#   dates and PROOF_PAUSE_S 2, 42: 400): about 1265 s, under ENTER_TIMEOUT_S with about 235 s for the rest (the
#   resumes are requests too). By the same count the flow before the re-attach and re-tag took about 735 s, so its
#   600 was already short where the first pause key did not take. Someone at the machine for most of 120 s at
#   several calls can take longer still: the client then answers no_answer, the verb runs on, and `status`
#   answers once it ends.
#   stop: kill and adopt (about 10 s, twice with a fresh helper), watch (WATCH_WAIT_S 60), restore's retries
#   (30 + 60 + 95 s), the restore itself and the closes (about 35 s): about 300 s, under STOP_TIMEOUT_S.
#   start: the fixture's run (FIXTURE_LIMIT_S 900, its restore's retries 30 + 60 s, and its snapshot, launch,
#   restore and rename, about 160 s: 1150 s), the session's snapshot and launch (about 120 s), the window
#   (WINDOW_WAIT_S 300), the console's first answer, retried while a late save loads (LOAD_WAIT_S 600, the last
#   try ending at its deadline, plus a probe round), the debugger (about 30 s), and the stop a failure runs (300 s):
#   about 2500 s, under START_TIMEOUT_S. A `--save` start makes no fixture and takes 1150 s less.
START_TIMEOUT_S = 2800.0
STOP_TIMEOUT_S = 600.0
EXIT_WAIT_S = 120.0                     # after a failed start or a stop: for the server to exit
MIN_FREE_BYTES = 2 * 1024**3            # what `snapshot` wants free under the backup root
PATH_NAMES = ("game_user_data_path", "game_qa_backup_path", "mod_deploy_target", "base_game_path")
GAME_EXE = Path("binaries") / "victoria3.exe"
LAUNCHER_SETTINGS = Path("launcher") / "launcher-settings.json"

RECOVER_HINT = ("a run is unfinished: its session ended without `stop` (its server died, or was killed). If its game "
                "is still up, its `watch` still records it. Once no game of that run is running and its `watch` has "
                "returned, run `python3 -m game_qa recover`, which finishes the run, then `python3 -m game_qa "
                "remove-overlay` (the run's overlay folder), then `start` again")
OVERLAY_LEFT_HINT = ("the overlay folder is an earlier run's, and that run's playset may still name it, so `start` "
                     "neither replaces nor removes it. Once no game of that run is running, finish the run "
                     "(`python3 -m game_qa recover`, or `restore <id>` for a run whose stop ended game_left_up or "
                     "refused), then run `python3 -m game_qa remove-overlay`, which removes the folder once nothing "
                     "can still use it, and `start` again")
DEAD_SERVER = ("%s names a session server (pid %s, port %s) that nothing answers for: it has died. " + RECOVER_HINT
               + ". `doctor` says what is left")


# ---- talking to the server

def call(backup_root: Path, verb: str, body: Mapping | None = None, timeout: float = VERB_TIMEOUT_S) -> tuple[dict, int]:
    """Post `verb` to the server session.json names: (its reply, the exit code its verb gives)."""
    path = Path(backup_root) / server.SESSION_FILE
    info = server.read_info(backup_root)
    if info is None:
        return {"refused": "no_session", "detail": "no session is running (there is no readable %s): `start` one"
                                                   % path}, 2
    try:
        return _post(info, verb, dict(body or {}), timeout)
    except ConnectionRefusedError:
        return {"refused": "no_session", "detail": DEAD_SERVER % (path, info["pid"], info["port"])}, 2
    except TimeoutError:
        return {"refused": "no_answer", "detail": "the session server did not answer %s within %g s. It may have "
                                                  "begun %s, which may still be running, or a verb in front of it is: "
                                                  "the server never begins a request after its client stops "
                                                  "waiting, so this one will not run later. `status` answers once "
                                                  "the server is free; look at it before running %s again"
                                                  % (verb, timeout, verb, verb)}, 2
    except (OSError, http.client.HTTPException, ValueError) as e:
        return {"refused": "no_answer", "detail": "the session server's answer to %s was lost (%s: %s): it may have "
                                                  "stopped. `status` says" % (verb, type(e).__name__, e)}, 2


def _post(info: Mapping, verb: str, body: Mapping, timeout: float) -> tuple[dict, int]:
    """One request. Raises OSError (ConnectionRefusedError: nothing listens; TimeoutError: no answer in time),
    http.client.HTTPException, or ValueError for an answer that is not the server's."""
    conn = http.client.HTTPConnection(server.HOST, int(info["port"]), timeout=timeout)
    expires = server.machine_clock() + timeout      # when this client stops waiting: the server never begins it after
    try:
        conn.request("POST", "/" + verb, body=json.dumps(body).encode("utf-8"),
                     headers={"Content-Type": "application/json", server.TOKEN_HEADER: str(info.get("token", "")),
                              server.EXPIRES_HEADER: "%.3f" % expires})
        data = conn.getresponse().read()
    finally:
        conn.close()
    answer = json.loads(data.decode("utf-8"))
    if not isinstance(answer, dict) or not isinstance(answer.get("reply"), dict) or not isinstance(answer.get("code"), int):
        raise ValueError("not an answer of the session server: %r" % data[:200])
    return answer["reply"], answer["code"]


def server_state(info: Mapping | None, timeout: float | None = None) -> str:
    """`live` (it answers `status`), `busy` (it has not answered in time, or nothing answers on its port while its
    process still runs: deep in a verb, starting, or stopping) or `stale` (nothing answers on its port and its
    process is gone: it died). A busy server is never taken for a dead one: its file would be removed and a second
    server's start would build its overlay over the running game's."""
    if info is None:
        return "stale"
    try:
        _post(info, "status", {}, STATUS_TIMEOUT_S if timeout is None else timeout)
        return "live"
    except TimeoutError:
        return "busy"
    except (OSError, http.client.HTTPException, ValueError):
        return "busy" if _serving(info.get("pid")) else "stale"


def _serving(pid: Any) -> bool:
    """Whether `pid` is a running `game_qa session-serve`, by its command line."""
    try:
        argv = Path("/proc/%d/cmdline" % int(pid)).read_bytes().split(b"\0")
    except (OSError, TypeError, ValueError):
        return False
    return b"session-serve" in argv


# ---- start

def start_session(backup_root: Path, body: Mapping, spawn: Callable[[Path, Path], Any],
                  sleep=time.sleep, clock=time.monotonic) -> tuple[dict, int]:
    """Spawn a server (`spawn(backup_root, log)`, returning a process handle), wait for it to listen, post `start`.
    A failed start's server has stopped the session before it answered; this waits for it to exit, unless that
    stop can be run again (`server.final_stop`): then the server serves on for `stop`, and `next` says so."""
    backup_root = Path(backup_root)
    notes: dict = {}
    path = backup_root / server.SESSION_FILE
    if path.exists():
        judged, info = _text(path), server.read_info(backup_root)
        if info is None:                    # being written this moment, or what a crash left
            sleep(1.0)
            judged, info = _text(path), server.read_info(backup_root)
        state = server_state(info)
        if state != "stale":
            return {"refused": "session_running", "session": _public(info),
                    "detail": "a session is running (pid %s, port %s): `stop` it first, or use it" % (
                        info["pid"], info["port"]) if state == "live" else
                    "a session server (pid %s, port %s) is up but has not answered within %g s: it is deep in a "
                    "verb, or stopping. Wait, then `status`" % (info["pid"], info["port"], STATUS_TIMEOUT_S)}, 2
        if _text(path) == judged:           # never a file a new server wrote meanwhile
            path.unlink(missing_ok=True)
        notes["stale_session"] = dict(_public(info or {}), removed=True,
                                      detail="removed %s: it named a server that has died. %s" % (path, RECOVER_HINT))
    try:
        runs = _runs_folder(backup_root)
    except OSError as e:
        return {"refused": "backup_root_unusable", "detail": str(e), **notes}, 2
    log = runs / ("session-serve-%s.log" % utc_now().strftime("%Y%m%dT%H%M%SZ"))
    handle = spawn(backup_root, log)
    where = {"pid": handle.pid, "log": str(log)}
    info = _await_listening(backup_root, handle, log, sleep, clock)
    if "refused" in info:
        return {**info, **notes, "server": where}, 2
    where["port"] = info["port"]
    reply, code = call(backup_root, "start", body, START_TIMEOUT_S)
    if code != 0 and reply.get("refused") != "no_answer" and server.final_stop(reply.get("stop")):
        try:
            handle.wait(timeout=EXIT_WAIT_S)
        except subprocess.TimeoutExpired:
            notes["server_still_running"] = ("the server had not exited %g s after it answered: it may still be "
                                             "stopping" % EXIT_WAIT_S)
    out = dict(reply)
    out.update(notes)
    out["server"] = where
    if (reply.get("reply") or {}).get("refused") == "unfinished_run" or reply.get("refused") == "no_session":
        out["next"] = RECOVER_HINT
    elif reply.get("refused") == "overlay_left":
        out["next"] = OVERLAY_LEFT_HINT
    elif reply.get("refused") == "no_answer":
        out["next"] = ("the start may still be running: `status` answers once it is done. Do not run `recover` "
                       "meanwhile: it would finish this start's own snapshot")
    elif isinstance(reply.get("stop"), dict) and reply["stop"].get("next") and "next" not in out:
        out["next"] = reply["stop"]["next"]          # what the failed start's stop left to do, where it is read
    return out, code


def _await_listening(backup_root: Path, handle, log: Path, sleep, clock) -> dict:
    deadline = clock() + SERVER_WAIT_S
    while True:
        info = server.read_info(backup_root)
        if info is not None and info.get("pid") == handle.pid:
            return info
        exited = handle.poll()
        if exited is not None:
            return {"refused": "server_failed", "detail": "the session server exited (code %s) before it listened: %s"
                                                          % (exited, _tail(log))}
        if clock() >= deadline:
            handle.terminate()          # it was asked nothing, so there is nothing of a session to stop
            try:
                handle.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            return {"refused": "server_did_not_start",
                    "detail": "the session server was not listening %g s after it was spawned, so it was ended "
                              "before it was asked anything. Its log: %s" % (SERVER_WAIT_S, _tail(log))}
        sleep(POLL_S)


def _runs_folder(backup_root: Path) -> Path:
    """`<backup root>/runs`, made if need be; the backup root itself only when its parent is there (as `snapshot`
    makes it), so a drive that is not mounted is not papered over with a folder."""
    if not backup_root.is_dir():
        if not backup_root.parent.is_dir():
            raise FileNotFoundError("neither the backup root %s nor the folder that would hold it exists"
                                    % backup_root)
        backup_root.mkdir(exist_ok=True)
    runs = backup_root / RUNS
    runs.mkdir(exist_ok=True)
    return runs


def _read_setups(specs: Sequence[str]) -> dict[str, str]:
    """`--setup NAME=FILE`s as {NAME: the text of FILE}. Raises ValueError, naming the one at fault."""
    setups: dict[str, str] = {}
    for spec in specs:
        name, sep, file = spec.partition("=")
        if not sep or not name or not file:
            raise ValueError("--setup takes NAME=FILE (a WSL path), not %r" % spec)
        if name in setups:
            raise ValueError("--setup %s is given twice" % name)
        try:
            setups[name] = Path(file).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as e:
            raise ValueError("--setup %s: %s cannot be read as UTF-8 text (%s)" % (name, file, e)) from None
    return setups


def _public(info: Mapping | None) -> dict:
    return {k: v for k, v in (info or {}).items() if k != "token"}


def _text(path: Path) -> str | None:
    try:
        return path.read_text("utf-8", errors="replace")
    except OSError:
        return None


def _tail(log: Path, size: int = 800) -> str:
    text = (_text(log) or "").strip()
    return ("...%s" % text[-size:] if len(text) > size else text) or "(the log %s is empty)" % log


# ---- selfchecks

def self_checks(backup_root: Path, run: str | None = None) -> tuple[dict, int]:
    """`selfchecks [--run ID]`: the verdicts of the mod's TE_SELF_CHECK lines in a run, the newest session's by
    default, with those of the run that made its fixture (`selfchecks.of_run`). It reads files under the backup
    root only, so it needs no session and works after `stop`.

    When session.json names a session whose run this is (`live`), the session is asked first, since it pushes
    the game's log out before it reads (`Session.self_checks`; `flushed` says whether that worked). If it does
    not answer, the files are read as they are and `not_flushed` carries its refusal. Exit 0 whenever the run
    was read, whatever the verdicts: `broken` names the checks that logged BROKEN. A run that is not there is
    refused `no_run`, and one whose files are there but cannot be read `unreadable_run`."""
    backup_root = Path(backup_root)
    try:
        run_id = selfchecks.resolve_run(backup_root, run)
    except selfchecks.SelfCheckError as e:
        return {"refused": e.code, "detail": e.detail}, 2
    info = server.read_info(backup_root)
    live = info is not None and info.get("snapshot") == run_id
    head: dict = {"live": live}
    if live:
        reply, code = call(backup_root, "selfchecks")
        if code == 0:
            return reply, 0
        head.update(flushed=False, not_flushed=reply)
    try:
        return {**head, **selfchecks.of_run(backup_root, run_id)}, 0
    except OSError as e:
        return {"refused": "unreadable_run", "run": run_id,
                "detail": "a file of run %s is there and cannot be read (%s: %s)" % (run_id, type(e).__name__, e)}, 2


# ---- profile summary

def profile_summary(backup_root: Path, run: str | None, labels: Sequence[str], top: int = 25,
                    roots: Callable[[], Sequence[tuple[str, Path]]] | None = None) -> tuple[dict, int]:
    """`profile summary [LABEL [LABEL2]] [--run ID] [--top N]`: what a run's profile says (`profiling.summary`), read
    from the run folder alone, the newest session's run by default, so it needs no session and works after `stop`.
    A script file is told apart by where such a file is now: among the run's variant folders (as its `start`
    recorded them), the deployed mod (`mod`), vanilla's `game/`, else `other` (`roots` gives the last two; by
    default from path_constants, and a path that is not set is left out). Refused `no_run` and `unreadable_run` as
    `selfchecks` is, and with `profiling.ProfileError`'s code otherwise."""
    backup_root = Path(backup_root)
    if not isinstance(top, int) or top < 1:
        return {"refused": "bad_argument", "detail": "--top takes a positive number, not %r" % (top,)}, 2
    try:
        run_id = selfchecks.resolve_run(backup_root, run)
    except selfchecks.SelfCheckError as e:
        return {"refused": e.code, "detail": e.detail}, 2
    run_dir = backup_root / RUNS / run_id
    steps = read_steps(run_dir)
    start = next((step for step in steps if step.get("verb") == "start" and step.get("outcome") == "ok"), {})
    folders = [("add_mod", Path(mod["wsl"])) for mod in start.get("add_mods") or ()
               if isinstance(mod, dict) and isinstance(mod.get("wsl"), str)]
    folders += list(roots() if roots is not None else _profile_roots())
    try:
        out = profiling.summary(run_dir, steps, list(labels), profiling.origin_of(folders), top)
    except profiling.ProfileError as e:
        return {"refused": e.code, "detail": e.detail, "run": run_id}, 2
    except OSError as e:
        return {"refused": "unreadable_run", "run": run_id,
                "detail": "a file of run %s is there and cannot be read (%s: %s)" % (run_id, type(e).__name__, e)}, 2
    return {"run": run_id, **out}, 0


def _profile_roots() -> list[tuple[str, Path]]:
    roots = []
    for label, name, below in (("mod", "mod_deploy_target", ""), ("vanilla", "base_game_path", "game")):
        try:
            path = _resolve(name)
        except Exception:
            continue
        roots.append((label, path / below if below else path))
    return roots


# ---- doctor

def doctor(resolve: Callable[[str], Any], ping: Callable[[], str], sample_gpu: Callable[[], Sequence]) -> tuple[dict, int]:
    """Is this machine ready for a session? One line per check, `<check>: ok…` or what is wrong. It starts no game,
    and changes nothing: `resolve` gives a path constant (raising when it is not set), `ping` asks the Windows
    python.exe for its version through the helper, `sample_gpu` gives one nvidia-smi reading. Exit 0 only when
    every check is ok."""
    lines: list[str] = []
    problems: list[str] = []

    def note(name: str, problem: str | None, ok: str = "ok") -> None:
        line = "%s: %s" % (name, ok if problem is None else problem)
        lines.append(line)
        if problem is not None:
            problems.append(line)

    paths: dict[str, Path] = {}
    missing = []
    for name in PATH_NAMES:
        try:
            paths[name] = Path(resolve(name))
        except Exception as e:
            missing.append("%s is not set (%s)" % (name, e))
            continue
        if name != "game_qa_backup_path" and not paths[name].is_dir():      # the backup root has a line of its own
            missing.append("%s: %s does not exist" % (name, paths[name]))
    note("paths", "; ".join(missing) or None)

    base = paths.get("base_game_path")
    exe = base / GAME_EXE if base is not None else None
    note("game binary", None if exe is not None and exe.is_file() else
         "no game at %s" % (exe if exe is not None else "(base_game_path is not set)"))

    try:
        note("windows python", None, "ok (Python %s)" % ping())
    except Exception as e:
        note("windows python", "python.exe did not answer the helper's ping: %s" % e)

    try:
        samples = list(sample_gpu())
    except Exception:
        samples = []
    if samples:
        s = samples[0]
        note("nvidia-smi", None, "ok (%g%% load, %d of %d MiB in use)" % (s.util_pct, s.mem_used_mib, s.mem_total_mib))
    else:
        note("nvidia-smi", "no reading: nvidia-smi is missing or failed, so `launch` takes the GPU for busy until "
                           "the owner confirms (--owner-confirmed-busy)")

    backups = paths.get("game_qa_backup_path")
    note("backup root", _backup_root_problem(backups) if backups is not None else "game_qa_backup_path is not set")

    try:
        held = [s.id for s in restore.held(backups)] if backups is not None and backups.is_dir() else []
        note("held snapshots", "held: %s. Only the owner resolves a hold, and `start` refuses while one is held"
             % ", ".join(held) if held else None, "ok (none)")
    except Exception as e:
        note("held snapshots", "could not be read: %s" % e)
    try:
        unfinished = _open_runs(backups) if backups is not None else []
        note("unfinished runs", "%s: taken for a run and neither restored nor held, so `snapshot` (and `start`) "
                                "refuse. %s" % (", ".join(unfinished), RECOVER_HINT) if unfinished else None,
             "ok (none)")
    except Exception as e:
        note("unfinished runs", "could not be read: %s" % e)

    info_path = backups / server.SESSION_FILE if backups is not None else None
    info = server.read_info(backups) if info_path is not None and info_path.exists() else None
    state = server_state(info) if info_path is not None and info_path.exists() else None
    user = paths.get("game_user_data_path")
    left = user / "mod" / overlay.OVERLAY_NAME if user is not None else None
    if left is not None and os.path.lexists(left):
        note("overlay folder", None if state in ("live", "busy") else
             "%s is there, left by a session that ended without its stop or whose stop kept it: `start` refuses "
             "(overlay_left). %s" % (left, OVERLAY_LEFT_HINT),
             "ok (the running session's)")
    else:
        note("overlay folder", None, "ok (none)")
    if state is None:
        note("session file", None, "ok (none)")
    elif state == "stale":
        note("session file", "stale: %s names pid %s on port %s, which nothing answers for (a server that died). "
                             "`start` removes it; its run is in `unfinished runs`" % (
                                 info_path, (info or {}).get("pid"), (info or {}).get("port")))
    else:
        note("session file", "a session is running (pid %s, port %s, %s): `stop` it before a new `start`" % (
            info["pid"], info["port"], state))
    ok = not problems
    return {"ok": ok, "checks": lines, "problems": problems}, 0 if ok else 2


# ---- remove-overlay

def remove_overlay(user_data: Path, backup_root: Path, list_games: Callable[[], Sequence],
                   sleep=time.sleep) -> tuple[dict, int]:
    """`remove-overlay`: delete the overlay folder (`mod/te_qa_overlay`) an earlier run left, and any temp folder
    a cut-short `build` left beside it, only through `overlay.remove` and `overlay.remove_build` (the exact name,
    the harness's marker, no symlink followed). Refused, with nothing removed, while anything may still use it:
    a backup root that cannot be seen (`backup_root`: an unmounted drive hides the runs), a session server that
    answers or may (`session_running`), a Victoria 3 process, or a process listing that
    did not finish (`game_running`, `cannot_list_games`), an unfinished run (`unfinished_run`: its game may be
    up, and `recover` finishes it), or a held snapshot whose run's playset was never put back (`playset_held`:
    the launcher may still name the overlay, and only the owner resolves a hold). A folder of that name that is
    not the harness's is left (`not_ours`). Exit 0 only when nothing of the overlay, nor any build folder, is
    left."""
    mod = Path(user_data) / "mod"
    dest = mod / overlay.OVERLAY_NAME
    builds = overlay.leftover_builds(mod)
    if not os.path.lexists(dest) and not builds:
        return {"ok": True, "removed": [], "detail": "there is no overlay folder at %s, nor a build's temp folder "
                                                     "beside it: nothing to remove" % dest}, 0
    refused = _overlay_in_use(Path(backup_root), list_games, sleep)
    if refused is not None:
        return dict(refused, ok=False, removed=[], overlay=str(dest)), 2
    if _server_named(Path(backup_root), sleep) is not None:     # one started meanwhile: it may be building its own
        return {"ok": False, "refused": "session_running", "removed": [], "overlay": str(dest),
                "detail": "a session server started while this looked: its run builds this overlay. Nothing was "
                          "removed"}, 2
    removed, left = [], []
    try:
        if os.path.lexists(dest):
            if overlay.remove(dest):
                removed.append(str(dest))
            else:
                left.append({"path": str(dest), "why": "not_ours: it is not a real folder carrying the harness's "
                                                       "marker (%s), so it is the owner's to judge" % overlay.MARKER})
        for build in builds:
            if overlay.remove_build(build):
                removed.append(str(build))
            else:
                left.append({"path": str(build), "why": "not_ours: a build's temp folder by its name, but it carries "
                                                        "no marker of the harness's (a build killed before its first "
                                                        "write, or not a build's at all): the owner's to judge"})
    except OSError as e:
        # The marker is deleted last, so a folder cut short here still reads as the harness's: run it again.
        return {"ok": False, "refused": "remove_failed", "removed": removed, "left": left, "overlay": str(dest),
                "detail": "removing failed partway (%s: %s), with the marker kept: run `remove-overlay` again once "
                          "nothing holds a file in it" % (type(e).__name__, e)}, 2
    out = {"ok": not left, "removed": removed, "overlay": str(dest)}
    if left:
        out.update(refused="not_ours", left=left, detail="nothing that is not provably the harness's was removed")
    return out, 0 if not left else 2


def _overlay_in_use(backups: Path, list_games: Callable[[], Sequence], sleep) -> dict | None:
    """Why the overlay may still be used (a refusal: `refused`, `detail`, and `next` where there is one), or
    None when nothing can use it."""
    if not backups.is_dir():
        # X2: an unmounted drive hides the journals (an unfinished run whose playset names the overlay) and any
        # server's session.json. The wording is part 1's for an unusable backup root (`__main__._backup_error`).
        where = ("the backup root's folder %s does not exist" % backups.parent if not backups.parent.is_dir() else
                 "the backup root %s does not exist" % backups)
        return {"refused": "backup_root", "detail": "%s, so a run whose playset names the overlay cannot be ruled "
                                                    "out: once it is there again, run this again" % where}
    info = _server_named(backups, sleep)
    if info is not None:
        return {"refused": "session_running", "session": _public(info),
                "detail": "a session server (pid %s, port %s) is up: its run may be using the overlay. `stop` it "
                          "(or let it finish), then run this again" % (info.get("pid"), info.get("port"))}
    try:
        games = list(list_games())
    except gate.GateError as e:
        return {"refused": "cannot_list_games", "detail": "the Victoria 3 processes could not be listed (%s), so a "
                                                          "game that loaded the overlay cannot be ruled out" % e}
    if games:
        return {"refused": "game_running", "games": [{"pid": g.pid, "created": g.created} for g in games],
                "detail": "a Victoria 3 process is running, and it may have loaded the overlay: once none runs, "
                          "run this again"}
    try:
        unfinished = _open_runs(backups)
        held = restore.held(backups) if backups.is_dir() else []
        unanswered = [snap.id for snap in held if _playset_unanswered(snapshot.journal(snap))]
    except Exception as e:
        return {"refused": "cannot_read_runs", "detail": "the snapshots' journals could not be read (%s: %s), so a "
                                                         "run that still names the overlay cannot be ruled out"
                                                         % (type(e).__name__, e)}
    if unfinished:
        return {"refused": "unfinished_run", "unfinished": unfinished, "next": RECOVER_HINT,
                "detail": "%s: taken for a run and neither restored nor held; that run's game may be up, and its "
                          "playset names the overlay" % ", ".join(unfinished)}
    if unanswered:
        return {"refused": "playset_held", "held": unanswered,
                "detail": "%s: held for the owner with the run's playset never put back, so the launcher may still "
                          "name the overlay. Only the owner resolves a hold; this can run once they have"
                          % ", ".join(unanswered)}
    return None


def _server_named(backups: Path, sleep) -> dict | None:
    """What session.json says when it names a server that is up or may be (`server_state` live or busy), else
    None. A file that does not read is looked at again after a second (a server writes it in one call), and is
    taken for a server while it stays unreadable: only `start` judges and removes such a file."""
    path = backups / server.SESSION_FILE
    if not os.path.lexists(path):
        return None
    info = server.read_info(backups)
    if info is None:
        sleep(1.0)
        if not os.path.lexists(path):
            return None
        info = server.read_info(backups)
        if info is None:
            return {"pid": None, "port": None, "detail": "%s does not read as a server's" % path}
    return info if server_state(info) != "stale" else None


def _playset_unanswered(journal: list[dict]) -> bool:
    """Whether a `playset` entry has no `playset_restored` or `restored` after it (the rule of part 1's
    `_answered`): the run's playset, which names the overlay, may never have been put back."""
    for i, entry in enumerate(journal):
        if entry.get("event") == "playset" and not any(
                later.get("event") in ("playset_restored", "restored") for later in journal[i + 1:]):
            return True
    return False


def _backup_root_problem(path: Path) -> str | None:
    folder = path if path.is_dir() else path.parent
    if not folder.is_dir():
        return "neither %s nor the folder that would hold it exists" % path
    if not os.access(folder, os.W_OK):
        return "%s is not writable" % folder
    free = shutil.disk_usage(folder).free
    if free < MIN_FREE_BYTES:
        return "only %d MB free under %s (a snapshot wants %d GB)" % (free // 1024**2, folder, MIN_FREE_BYTES // 1024**3)
    return None


def _open_runs(backups: Path) -> list[str]:
    """Snapshots taken for a run (`armed`, or already `started`) with no verdict: what `snapshot` refuses on."""
    if not backups.is_dir():
        return []
    found = []
    for snap in snapshot.all_snapshots(backups):
        events = {e.get("event") for e in snapshot.journal(snap)}
        if events & {"armed", "started"} and not events & {"restored", "held"}:
            found.append(snap.id)
    return found


# ---- the real wiring

def _resolve(name: str) -> Path:
    import path_constants

    value = path_constants.refresh(name)
    if not value:
        raise ValueError("%s is not set" % name)
    return Path(value)


def _backup_root() -> Path:
    return _resolve("game_qa_backup_path")


def _child_env() -> dict:
    return dict(os.environ, PYTHONIOENCODING="utf-8")


def run_cli(argv: Sequence[str]) -> tuple[dict, int]:
    """`python3 -m game_qa <argv>` from the repository root: (the JSON object it printed, its exit code)."""
    done = subprocess.run([sys.executable, "-m", "game_qa", *argv], cwd=REPO_ROOT, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=_child_env())
    try:
        reply = json.loads(done.stdout)
    except ValueError:
        reply = None
    if not isinstance(reply, dict):
        return {"refused": "bad_reply", "detail": "`game_qa %s` printed no JSON object (exit %d): %s" % (
            " ".join(argv[:1]), done.returncode, (done.stdout + done.stderr)[-600:])}, 2
    return reply, done.returncode


def spawn_watch(snapshot_id: str, run_root: Path) -> subprocess.Popen:
    """`python3 -m game_qa watch <id>` in its own session and process group, so it outlives the server; its output
    goes to watch.log in the run's folder."""
    folder = Path(run_root) / snapshot_id
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / WATCH_LOG, "ab") as out:
        return subprocess.Popen([sys.executable, "-m", "game_qa", "watch", snapshot_id], cwd=REPO_ROOT,
                                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True, env=_child_env())


def spawn_server(backup_root: Path, log: Path) -> subprocess.Popen:
    """`python3 -m game_qa session-serve`, detached: its own session and process group, stdin closed, its output to
    `log`. It finds the backup root as every verb does (path_constants)."""
    with open(log, "ab") as out:
        return subprocess.Popen([sys.executable, "-m", "game_qa", "session-serve"], cwd=REPO_ROOT,
                                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True, env=_child_env())


def game_version(base_game: Path) -> str:
    """The game's version as its launcher settings give it (`rawVersion`)."""
    path = Path(base_game) / LAUNCHER_SETTINGS
    version = json.loads(path.read_text("utf-8-sig")).get("rawVersion")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("%s has no rawVersion" % path)
    return version.strip()


def enabled_mods(user_data: Path) -> list[str]:
    """The mod folders the owner's playset enables, in order (`content_load.json`); [] when it cannot be read."""
    try:
        data = json.loads((Path(user_data) / "content_load.json").read_text("utf-8-sig"))
    except (OSError, ValueError):
        return []
    mods = data.get("enabledMods") if isinstance(data, dict) else None
    return [m["path"] for m in mods or [] if isinstance(m, dict) and isinstance(m.get("path"), str)]


def disabled_dlc(user_data: Path) -> list:
    """The DLC the owner's playset switches off (`content_load.json`'s `disabledDLC`, which `launch` keeps as it
    is), each entry as the file gives it; [] when it cannot be read."""
    try:
        data = json.loads((Path(user_data) / "content_load.json").read_text("utf-8-sig"))
    except (OSError, ValueError):
        return []
    dlc = data.get("disabledDLC") if isinstance(data, dict) else None
    return list(dlc) if isinstance(dlc, list) else []


def real_paths() -> session.Paths:
    user, base, deploy = _resolve("game_user_data_path"), _resolve("base_game_path"), _resolve("mod_deploy_target")
    # wslpath can fail on a path that does not exist yet: the overlay's folder is made at `start`.
    overlay_windows = to_windows_path(user / "mod").rstrip("\\") + "\\" + overlay.OVERLAY_NAME
    return session.Paths(user_data=user, backup_root=_backup_root(), deploy_dir=deploy,
                         base_game=base, overlay_windows_path=overlay_windows,
                         events_file_windows_path=to_windows_path, game_version=game_version(base),
                         enabled_mods=enabled_mods(user), deployed_mod_windows_path=to_windows_path(deploy),
                         disabled_dlc=disabled_dlc(user))


def _ping_windows_python() -> str:
    helper = ProcessHelper()
    try:
        return helper.ping()
    finally:
        helper.close()


# ---- the verbs

def cmd_start(args) -> tuple[dict, int]:
    try:
        setups = _read_setups(args.setup)
    except ValueError as e:
        return {"refused": "bad_argument", "detail": str(e)}, 2
    switches: dict[str, str] = {}
    for spec in args.switch_rule:
        rule, eq, setting = spec.partition("=")
        if not eq or not rule or not setting or rule in switches:
            return {"refused": "bad_argument", "detail": "--switch-rule takes RULE=SETTING, each rule once, not %r"
                                                         % spec}, 2
        switches[rule] = setting
    body = {"permission": args.permission, "as_tag": args.as_tag, "save": args.save, "setups": setups,
            "playset": args.playset, "owner_confirmed_busy": args.owner_confirmed_busy}
    if switches:
        body["switch_rules"] = switches
    if args.game_arg:
        body["game_args"] = list(args.game_arg)
    if args.add_mod:
        body["add_mods"] = list(args.add_mod)
    return start_session(_backup_root(), body, spawn_server)


def cmd_stop(args) -> tuple[dict, int]:
    backups = _backup_root()
    before = server.read_info(backups)
    reply, code = call(backups, "stop", {}, STOP_TIMEOUT_S)
    if before is not None and "outcome" in reply and server.final_stop(reply):
        deadline = time.monotonic() + EXIT_WAIT_S       # the server exits once it has answered a final stop
        while (server.read_info(backups) or {}).get("pid") == before["pid"]:
            if time.monotonic() > deadline:
                reply = dict(reply, server_still_running="the server had not exited %g s after it answered"
                                                         % EXIT_WAIT_S)
                break
            time.sleep(POLL_S)
    return reply, code


def cmd_console(args) -> tuple[dict, int]:
    return call(_backup_root(), "console", {"text": args.text})


def cmd_run_setup(args) -> tuple[dict, int]:
    return call(_backup_root(), "run-setup", {"name": args.name})


def cmd_add_setup(args) -> tuple[dict, int]:
    try:
        setups = _read_setups([args.setup])
    except ValueError as e:
        return {"refused": "bad_argument", "detail": str(e).replace("--setup", "add-setup")}, 2
    (name, script), = setups.items()
    return call(_backup_root(), "add-setup", {"name": name, "script": script}, ADD_SETUP_TIMEOUT_S)


def cmd_press(args) -> tuple[dict, int]:
    return call(_backup_root(), "press", {"key": args.key})


def cmd_events(args) -> tuple[dict, int]:
    return call(_backup_root(), "events")


def cmd_pick(args) -> tuple[dict, int]:
    return call(_backup_root(), "pick", {"index": args.index, "event": args.event})


def cmd_read(args) -> tuple[dict, int]:
    return call(_backup_root(), "read", {"exprs": args.exprs})


def cmd_tag(args) -> tuple[dict, int]:
    return call(_backup_root(), "tag", {"tag": args.tag})


def cmd_enter_game(args) -> tuple[dict, int]:
    return call(_backup_root(), "enter-game", {"via": args.via}, timeout=ENTER_TIMEOUT_S)


def cmd_advance(args) -> tuple[dict, int]:
    return call(_backup_root(), "advance", {"days": args.days}, ADVANCE_TIMEOUT_S)


def cmd_shot(args) -> tuple[dict, int]:
    return call(_backup_root(), "shot")


def cmd_click(args) -> tuple[dict, int]:
    body = {"x": args.x, "y": args.y}
    if args.console:
        body["console"] = True
    if args.input_line is not None:
        body["input_line"] = args.input_line
    return call(_backup_root(), "click", body)


def cmd_wheel(args) -> tuple[dict, int]:
    return call(_backup_root(), "wheel", {"x": args.x, "y": args.y, "notches": args.notches})


def cmd_drag(args) -> tuple[dict, int]:
    return call(_backup_root(), "drag", {"x1": args.x1, "y1": args.y1, "x2": args.x2, "y2": args.y2})


def cmd_profiler_roots(args) -> tuple[dict, int]:
    body = {"box": args.box}
    if args.as_shown:
        body["as_shown"] = True
    return call(_backup_root(), "profiler-roots", body)


def cmd_try_event(args) -> tuple[dict, int]:
    return call(_backup_root(), "try-event", {"event": args.event, "setup": args.setup, "reads": args.reads},
                LONG_TIMEOUT_S)


def cmd_status(args) -> tuple[dict, int]:
    return call(_backup_root(), "status", timeout=STATUS_TIMEOUT_S)


def cmd_selfchecks(args) -> tuple[dict, int]:
    return self_checks(_backup_root(), args.run_id)


def cmd_profile_start(args) -> tuple[dict, int]:
    return call(_backup_root(), "profile-start")


def cmd_profile_dump(args) -> tuple[dict, int]:
    return call(_backup_root(), "profile-dump", {"label": args.label})


def cmd_profile_summary(args) -> tuple[dict, int]:
    return profile_summary(_backup_root(), args.run_id, args.labels, args.top)


def cmd_doctor(args) -> tuple[dict, int]:
    return doctor(_resolve, _ping_windows_python, lambda: gate.sample_gpu(n=1))


def cmd_remove_overlay(args) -> tuple[dict, int]:
    return remove_overlay(_resolve("game_user_data_path"), _backup_root(), gate.list_games)


def cmd_session_serve(args) -> tuple[dict, int]:
    paths = real_paths()
    sess = session.Session(ProcessHelper(), run_cli, lambda snapshot_id: spawn_watch(snapshot_id, paths.run_root), paths,
                           helper_factory=ProcessHelper)
    result = server.SessionServer(sess, paths.backup_root, port=args.port, log=sys.stderr).serve(signals=True)
    return result, 0 if server.clean_stop(result.get("stop") or {}) else 2


def add_verbs(sub) -> None:
    """Add the session's verbs to `python3 -m game_qa`'s subparsers."""
    p = sub.add_parser("start", help="start a session: a game on the deployed build, through snapshot, launch and "
                                     "watch, driven by the verbs below until `stop`")
    p.add_argument("--permission", required=True,
                   help="where the permission to launch came from (asked, or granted for this session)")
    p.add_argument("--as", dest="as_tag", metavar="TAG", help="the country to play, by tag (FRA)")
    p.add_argument("--save", metavar="NAME", help="load this save from save games/ instead of the fixture")
    p.add_argument("--setup", action="append", default=[], metavar="NAME=FILE",
                   help="a setup effect: its name, and the file (a WSL path) holding its script (repeatable)")
    p.add_argument("--switch-rule", action="append", default=[], metavar="RULE=SETTING",
                   help="load a copy of the fresh save with this game rule switched (repeatable; not with "
                        "--save). The rule changes on the save's second day, after the game's setup ran")
    p.add_argument("--playset", choices=session.PLAYSETS, default="mod_only",
                   help="mod_only (the default): only this mod's deployed folder; current: the owner's playset. "
                        "The overlay is added to either")
    p.add_argument("--owner-confirmed-busy", action="store_true",
                   help="the owner was asked about the busy GPU and said to go ahead")
    p.add_argument("--game-arg", action="append", default=[], metavar="FLAG",
                   help="add one of %s to the game's arguments (repeatable). Write it without its dash, or as "
                        "--game-arg=-FLAG. The fixture's own run never gets it" % ", ".join(session.GAME_ARGS))
    p.add_argument("--add-mod", action="append", default=[], metavar="WINDOWS_PATH",
                   help="a variant mod folder (a Windows drive path outside the user-data folder, holding "
                        ".metadata/metadata.json), loaded after the run's playset and before the overlay, for an A/B "
                        "run (repeatable). Without --save it is part of the fixture's world and key")
    p.set_defaults(run=cmd_start)

    p = sub.add_parser("console", help="one console command, with its reply")
    p.add_argument("text")
    p.set_defaults(run=cmd_console)
    p = sub.add_parser("add-setup", help="add a setup to the running game: the overlay's effects file is "
                                         "rewritten and the game reloads it (about 90 s)")
    p.add_argument("setup", metavar="NAME=FILE", help="its name, and the file (a WSL path) holding its script")
    p.set_defaults(run=cmd_add_setup)
    p = sub.add_parser("run-setup", help="run a setup, given at start or added since, through its event; its "
                                         "log lines")
    p.add_argument("name")
    p.set_defaults(run=cmd_run_setup)
    p = sub.add_parser("press", help="press one key in the game itself, the console closed first (a probe: "
                                     "take a shot before and after)")
    p.add_argument("key", choices=["esc"])
    p.set_defaults(run=cmd_press)
    sub.add_parser("events", help="the pending events").set_defaults(run=cmd_events)
    p = sub.add_parser("pick", help="pick an option of a pending event")
    p.add_argument("index", type=int)
    p.add_argument("event", nargs="?", help="an event id (its oldest pending instance) or a numeric id")
    p.set_defaults(run=cmd_pick)
    p = sub.add_parser("read", help="evaluate triggers and values at the debugger's breakpoint, for the played "
                                    "country: a trigger is written bare (has_technology_researched = railways; "
                                    "c:TAG.<trigger> = x answers \"Unknown trigger type\"), and a variable that is "
                                    "not set reads 0")
    p.add_argument("exprs", nargs="+", metavar="EXPR")
    p.set_defaults(run=cmd_read)
    p = sub.add_parser("tag", help="play another country")
    p.add_argument("tag")
    p.set_defaults(run=cmd_tag)
    p = sub.add_parser("enter-game", help="the two clicks past the country-select screen, proven by the date "
                                          "moving")
    p.add_argument("--via", choices=("country", "back"), default="country",
                   help="country: click the country the camera is on, then Start (the default); back: click the "
                        "screen's Back button once (#1598; run live 2026-11-13)")
    p.set_defaults(run=cmd_enter_game)
    p = sub.add_parser("advance", help="let at least DAYS game days pass (entering the game first if need be)")
    p.add_argument("days", type=int)
    p.set_defaults(run=cmd_advance)
    sub.add_parser("shot", help="a screenshot of the game's window, into the run folder").set_defaults(run=cmd_shot)
    p = sub.add_parser("click", help="one left click at X, Y (fractions of the game window's client area from its "
                                     "top left), then a screenshot: for the engine's own tool windows, such as the "
                                     "script profiler's")
    p.add_argument("x", type=float, nargs="?")
    p.add_argument("y", type=float, nargs="?")
    p.add_argument("--console", action="store_true",
                   help="then click the console's input line, which gives the keyboard back after a click into a "
                        "tool window took it, and prove it with one probe (alone: only that click)")
    p.add_argument("--input-line", nargs=2, type=float, metavar=("X", "Y"),
                   help="where the console's input line is, as fractions of the window (default: 0.1125 0.544, "
                        "measured live with the console open on the left in a 3840x2160 window)")
    p.set_defaults(run=cmd_click)
    p = sub.add_parser("wheel", help="turn the mouse wheel N notches at X, Y (fractions of the window; positive "
                                     "scrolls a list up), then a screenshot: for the engine's own tool windows")
    p.add_argument("x", type=float)
    p.add_argument("y", type=float)
    p.add_argument("notches", type=int, metavar="N")
    p.set_defaults(run=cmd_wheel)
    p = sub.add_parser("drag", help="press the left button at X1, Y1, move to X2, Y2 and release (fractions of the "
                                    "window), then a screenshot: for the engine's own tool windows")
    for name in ("x1", "y1", "x2", "y2"):
        p.add_argument(name, type=float)
    p.set_defaults(run=cmd_drag)
    p = sub.add_parser("profiler-roots", help="open the script profiler at its roots (Script.Profiling.Gui), take "
                                              "a shot at the window's own size and crop the call graph out of it")
    p.add_argument("--box", nargs=4, type=float, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
                   help="the crop, as fractions of the window (default: the call graph of the overlay's enlarged "
                        "window, measured in a 3840x2160 window)")
    p.add_argument("--as-shown", action="store_true",
                   help="type nothing: shoot and crop the window as it is (after a click on a row, or a wheel)")
    p.set_defaults(run=cmd_profiler_roots)
    p = sub.add_parser("try-event", help="the owner's first check: for each option of EVENT, run the setup, fire "
                                         "the event, read, pick that option, read again; one table in the report")
    p.add_argument("event")
    p.add_argument("--setup", metavar="NAME", help="a setup given at start, run before each option")
    p.add_argument("--read", dest="reads", action="append", required=True, metavar="EXPR",
                   help="a trigger or value read before and after each pick (repeatable)")
    p.set_defaults(run=cmd_try_event)
    for name, fn, text in (("stop", cmd_stop, "end the game, put the owner's files back, end the session server "
                                              "(unless the stop can be run again: then `stop` again runs it)"),
                           ("status", cmd_status, "the session server and its session"),
                           ("doctor", cmd_doctor, "is this machine ready for a session? (starts nothing, changes "
                                                  "nothing)"),
                           ("remove-overlay", cmd_remove_overlay, "remove the overlay folder an earlier run left, "
                                                                  "once no server, game, unfinished run or held "
                                                                  "playset can still use it")):
        sub.add_parser(name, help=text).set_defaults(run=fn)
    p = sub.add_parser("selfchecks", help="the verdicts of the mod's TE_SELF_CHECK lines in a run, every BROKEN "
                                          "first, with those of the run that made its fixture; a live session's "
                                          "log is flushed first")
    p.add_argument("--run", dest="run_id", metavar="ID",       # not `run`: that is the verb's function
                   help="a run's snapshot id (default: the newest session's run)")
    p.set_defaults(run=cmd_selfchecks)
    p = sub.add_parser("profile", help="profile the running game (#1700): `start`, `dump [LABEL]`, then `summary "
                                       "[LABEL [LABEL2]]`, which needs no session")
    actions = p.add_subparsers(dest="action", required=True, metavar="ACTION")
    actions.add_parser("start", help="clear the tick-task timings and turn the script profiler on, noting the "
                                     "game date").set_defaults(run=cmd_profile_start)
    q = actions.add_parser("dump", help="dump the tick-task timings and the script profile, and copy both into the "
                                        "run folder at once")
    q.add_argument("label", nargs="?", help="what to call the dump (default: the game date)")
    q.set_defaults(run=cmd_profile_dump)
    q = actions.add_parser("summary", help="the wall clock per frame type, the top tick tasks and the script time by "
                                           "file, mod against vanilla: up to LABEL (default: the newest dump) from "
                                           "the profile's start, or between LABEL and LABEL2")
    q.add_argument("labels", nargs="*", metavar="LABEL")
    q.add_argument("--run", dest="run_id", metavar="ID", help="a run's snapshot id (default: the newest session's run)")
    q.add_argument("--top", type=int, default=25, help="how many tasks and files to list (default 25)")
    q.set_defaults(run=cmd_profile_summary)
    p = sub.add_parser("session-serve", help="the session server (`start` runs it detached; not for direct use)")
    p.add_argument("--port", type=int, default=server.PORT)
    p.set_defaults(run=cmd_session_serve)
