"""The session's command-line verbs: thin clients of the session server (`game_qa/server.py`), and a session's
real wiring (its paths, `run_cli`, `spawn_watch`, the Windows helper).

    python3 -m game_qa start --permission "asked 12:40" [--as TAG] [--save NAME] [--setup NAME=FILE]...
                       [--playset mod_only|current] [--owner-confirmed-busy]
                                             # a game on the deployed build, on the fixture or on NAME
    python3 -m game_qa console "<text>"      # one console command, with its reply
    python3 -m game_qa run-setup NAME        # a setup given at start, through its event: its log lines
    python3 -m game_qa events                # the pending events
    python3 -m game_qa pick INDEX [EVENT]    # an option of a pending event (the oldest, or EVENT's)
    python3 -m game_qa read "<expr>"...      # triggers and values, evaluated at the debugger's breakpoint
    python3 -m game_qa tag TAG               # play another country
    python3 -m game_qa enter-game            # the two clicks past the country-select screen, proven
    python3 -m game_qa advance DAYS          # let at least DAYS game days pass
    python3 -m game_qa shot                  # a screenshot of the game's window, into the run folder
    python3 -m game_qa try-event EVENT [--setup NAME] --read "<expr>"...
                                             # each option of EVENT: setup, fire, read, pick, read; exit 0 only
                                             # when every option fired and was picked
    python3 -m game_qa stop                  # end the game, put the owner's files back, end the server
    python3 -m game_qa status                # the server and its session
    python3 -m game_qa doctor                # is this machine ready for a session? (starts nothing)

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
from game_qa.report import utc_now

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS = "runs"
WATCH_LOG = "watch.log"
SERVER_WAIT_S = 30.0                    # from spawning the server to its session.json
POLL_S = 0.2
STATUS_TIMEOUT_S = 10.0                 # a server that has not answered `status` by then is busy, not dead
VERB_TIMEOUT_S = 300.0                  # a console command may wait 120 s for the game to come to the front
ENTER_TIMEOUT_S = 600.0
LONG_TIMEOUT_S = 900.0                  # advance and try-event
# The worst cases, from the waits the session and the fixture allow themselves (the report sums them):
#   start: the fixture's run (FIXTURE_LIMIT_S 900, then its restore's retries, up to 30 + 60 s, and the
#   verbs around them, about 160 s), the session's own snapshot and launch (minutes), the window (300 s), the
#   console's first answer (180 s), and a stop when any of it fails (about 380 s): about 1810 s, under 2400.
#   stop: a kill, watch (60 s), restore's retries (30 + 60 + 95 s), the restore itself: about 380 s, under 600.
START_TIMEOUT_S = 2400.0
STOP_TIMEOUT_S = 600.0
EXIT_WAIT_S = 120.0                     # after a failed start or a stop: for the server to exit
MIN_FREE_BYTES = 2 * 1024**3            # what `snapshot` wants free under the backup root
PATH_NAMES = ("game_user_data_path", "game_qa_backup_path", "mod_deploy_target", "base_game_path")
GAME_EXE = Path("binaries") / "victoria3.exe"
LAUNCHER_SETTINGS = Path("launcher") / "launcher-settings.json"

RECOVER_HINT = ("a run is unfinished: its session ended without `stop` (its server died, or was killed). If its game "
                "is still up, its `watch` still records it. Once no game of that run is running and its `watch` has "
                "returned, run `python3 -m game_qa recover`, which finishes the run, then `start` again")
OVERLAY_LEFT_HINT = ("the overlay folder is an earlier run's, and that run's playset may still name it, so `start` "
                     "neither replaces nor removes it. Once no game of that run is running, finish the run "
                     "(`python3 -m game_qa recover`, or `restore <id>` for a run whose stop ended game_left_up or "
                     "refused), then remove the folder and `start` again")
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
    expires = time.time() + timeout         # when this client stops waiting: the server never begins it after
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


def real_paths() -> session.Paths:
    user, base, deploy = _resolve("game_user_data_path"), _resolve("base_game_path"), _resolve("mod_deploy_target")
    # wslpath can fail on a path that does not exist yet: the overlay's folder is made at `start`.
    overlay_windows = to_windows_path(user / "mod").rstrip("\\") + "\\" + overlay.OVERLAY_NAME
    return session.Paths(user_data=user, backup_root=_backup_root(), deploy_dir=deploy,
                         base_game=base, overlay_windows_path=overlay_windows,
                         events_file_windows_path=to_windows_path, game_version=game_version(base),
                         enabled_mods=enabled_mods(user), deployed_mod_windows_path=to_windows_path(deploy))


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
    body = {"permission": args.permission, "as_tag": args.as_tag, "save": args.save, "setups": setups,
            "playset": args.playset, "owner_confirmed_busy": args.owner_confirmed_busy}
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


def cmd_events(args) -> tuple[dict, int]:
    return call(_backup_root(), "events")


def cmd_pick(args) -> tuple[dict, int]:
    return call(_backup_root(), "pick", {"index": args.index, "event": args.event})


def cmd_read(args) -> tuple[dict, int]:
    return call(_backup_root(), "read", {"exprs": args.exprs})


def cmd_tag(args) -> tuple[dict, int]:
    return call(_backup_root(), "tag", {"tag": args.tag})


def cmd_enter_game(args) -> tuple[dict, int]:
    return call(_backup_root(), "enter-game", timeout=ENTER_TIMEOUT_S)


def cmd_advance(args) -> tuple[dict, int]:
    return call(_backup_root(), "advance", {"days": args.days}, LONG_TIMEOUT_S)


def cmd_shot(args) -> tuple[dict, int]:
    return call(_backup_root(), "shot")


def cmd_try_event(args) -> tuple[dict, int]:
    return call(_backup_root(), "try-event", {"event": args.event, "setup": args.setup, "reads": args.reads},
                LONG_TIMEOUT_S)


def cmd_status(args) -> tuple[dict, int]:
    return call(_backup_root(), "status", timeout=STATUS_TIMEOUT_S)


def cmd_doctor(args) -> tuple[dict, int]:
    return doctor(_resolve, _ping_windows_python, lambda: gate.sample_gpu(n=1))


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
    p.add_argument("--playset", choices=session.PLAYSETS, default="mod_only",
                   help="mod_only (the default): only this mod's deployed folder; current: the owner's playset. "
                        "The overlay is added to either")
    p.add_argument("--owner-confirmed-busy", action="store_true",
                   help="the owner was asked about the busy GPU and said to go ahead")
    p.set_defaults(run=cmd_start)

    p = sub.add_parser("console", help="one console command, with its reply")
    p.add_argument("text")
    p.set_defaults(run=cmd_console)
    p = sub.add_parser("run-setup", help="run a setup given at start, through its event; its log lines")
    p.add_argument("name")
    p.set_defaults(run=cmd_run_setup)
    sub.add_parser("events", help="the pending events").set_defaults(run=cmd_events)
    p = sub.add_parser("pick", help="pick an option of a pending event, by its numeric id")
    p.add_argument("index", type=int)
    p.add_argument("event", nargs="?", help="an event id (its oldest pending instance) or a numeric id")
    p.set_defaults(run=cmd_pick)
    p = sub.add_parser("read", help="evaluate triggers and values at the debugger's breakpoint")
    p.add_argument("exprs", nargs="+", metavar="EXPR")
    p.set_defaults(run=cmd_read)
    p = sub.add_parser("tag", help="play another country")
    p.add_argument("tag")
    p.set_defaults(run=cmd_tag)
    sub.add_parser("enter-game", help="the two clicks past the country-select screen, proven by the date "
                                      "moving").set_defaults(run=cmd_enter_game)
    p = sub.add_parser("advance", help="let at least DAYS game days pass (entering the game first if need be)")
    p.add_argument("days", type=int)
    p.set_defaults(run=cmd_advance)
    sub.add_parser("shot", help="a screenshot of the game's window, into the run folder").set_defaults(run=cmd_shot)
    p = sub.add_parser("try-event", help="the owner's first check: for each option of EVENT, run the setup, fire "
                                         "the event, read, pick that option, read again; one table in the report")
    p.add_argument("event")
    p.add_argument("--setup", metavar="NAME", help="a setup given at start, run before each option")
    p.add_argument("--read", dest="reads", action="append", required=True, metavar="EXPR",
                   help="a trigger or value read before and after each pick (repeatable)")
    p.set_defaults(run=cmd_try_event)
    for name, fn, text in (("stop", cmd_stop, "end the game, put the owner's files back, end the session server"),
                           ("status", cmd_status, "the session server and its session"),
                           ("doctor", cmd_doctor, "is this machine ready for a session? (starts nothing, changes "
                                                  "nothing)")):
        sub.add_parser(name, help=text).set_defaults(run=fn)
    p = sub.add_parser("session-serve", help="the session server (`start` runs it detached; not for direct use)")
    p.add_argument("--port", type=int, default=server.PORT)
    p.set_defaults(run=cmd_session_serve)
