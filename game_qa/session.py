"""One game's life: start it on the deployed build, drive it, and stop it with the owner's files put back.

The session never touches the owner's files itself. The protective verbs of part 1 do, and only through the
`run_cli` it is given (`python3 -m game_qa <argv>`, returning its JSON reply and exit code): `held`, `snapshot`,
`launch`, `restore`, and `watch` as the subprocess `spawn_watch` starts. A refusal or a hold from any of them is
reported, never worked around. Under the user-data folder the session itself writes only the overlay mod
(`overlay.build` and `overlay.remove`) and, through `fixture`, the `te_qa_fixture_*` saves.

    start   overlay left?  held?  overlay  fixture  snapshot  launch  watch at once  adopt  window  logs  console
            tag  debugger
    stop    kill  wait for watch  restore  overlay.remove  close the relay and the helper  close the report

A game that may still be up is never restored beside (part 1 would hold): `stop` then ends `game_left_up`, and
its `next` says what can work: `stop` again for a game known by pid and start time, else `restore <id>` or
`recover` once no game is running. The overlay goes only once the game is known ended and the
owner's playset is known back; otherwise it stays, and the next `start` refuses (`overlay_left`) until that run
is finished and `python3 -m game_qa remove-overlay` has removed the folder. A `stop` that ended refused or
game_left_up is run again by the next `stop`.

Keys and clicks go out only through `Console` and the helper, which check that the game is in front; a click
is preceded by a console call that needs the game in front, so the presence rule decides whether the foreground
may be taken, never a bare `focus`. A console command is typed once: nothing here types one again after an error.

Reads go through the overlay's read event (`overlay.READ_EVENT`): console `event te_qa.1` runs its `immediate`
at once, the debugger stops on its `debug_log` line, and each expression is evaluated there; once resumed, the
event logs `TE_QA read country=FRA date=January 11, 1836` and its padding flushes the log. That line is how the
session reads the date (`enter_game`, `advance`). Before each read a stop left over from an earlier one is
released, and only a stop whose reason is "breakpoint" is evaluated at. Facts from the live session of
2026-11-10 (spec § 12): the fixture opens on the country-select screen, where time does not advance; after `tag`
the camera is on that country, and a click at COUNTRY_CLICK then START_CLICK (fractions of the client area)
enters the game; the game is paused when a save loads, and space toggles the pause only with the console closed.
Each round of time ends by proving the pause: two date reads PROOF_PAUSE_S apart must agree.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from game_qa import fixture, overlay, snapshot
from game_qa.console import CLEAR_BACKSPACES, Console, ConsoleError, Reply
from game_qa.dap import Debugger, DebuggerError
from game_qa.fixture import RunCli
from game_qa.gate import UNKNOWN_START, ProcId
from game_qa.helper import Helper, HelperError
from game_qa.logtail import GAP_MARKER, LogFollower, Pending, parse, pending_events
from game_qa.report import Report, stamp, utc_now

COUNTRY_CLICK = (0.492, 0.656)          # the country the camera is on after `tag` (3840x2160 measured, spec § 12.1 A2)
START_CLICK = (0.9216, 0.975)           # the country-select screen's Start button
SCAN_SPACE = 0x39                       # toggles the pause, with the console closed
DEBUGGER_PORT = 6111
SESSION_ARGS = ("-gdpr-compliant", "-debug_mode", "-script_debugger")
PLAYSETS = ("current", "mod_only")
READ_COMMAND = "event " + overlay.READ_EVENT
FIRE_COMMAND = "event %s"               # console `event` fires whatever the trigger and cooldown say (spec § 12.1 A6)
READ_PREFIX = "TE_QA read "
PENDING_COMMAND = "select_event_option list"
NO_PENDING = "No pending events"
FIXTURES_KEPT = 2

WINDOW_WAIT_S = 300.0                   # from launch to a window that responds
WINDOW_POLL_S = 1.0
CONSOLE_READY_S = 180.0                 # the first round trip: a save took about 2 minutes to a usable console
STOP_WAIT_S = 15.0                      # from typing the read event to the debugger's stop (real seconds: dap's clock)
DATE_WAIT_S = 5.0                       # from the resume to the read event's line in the log
SETUP_WAIT_S = 10.0                     # from a setup's command to its done marker in the log
LOG_POLL_S = 0.2
CLICK_SETTLE_S = 1.0                    # after the country click, before Start (unverified)
ENTER_SETTLE_S = 2.0                    # after Start, before the first read (unverified)
PROOF_S = 3.0                           # unpaused, to prove the game was entered
FIRST_RATE = 1.5                        # game days a second at the speed the game loads with (live, 2026-11-10)
MIN_WAIT_S = 1.0
MAX_WAIT_S = 20.0
MAX_ROUNDS = 20
WATCH_WAIT_S = 60.0                     # stop: for `watch` to see the game gone and return
WATCH_POLL_S = 1.0
RESTORE_RETRY_S = fixture.RESTORE_RETRY_S                 # stop: while `restore` refuses one of the reasons below
RESTORE_RETRY_TOTAL_S = fixture.RESTORE_RETRY_TOTAL_S     # for watch_still_recording
BUSY_RETRY_TOTAL_S = fixture.BUSY_RETRY_TOTAL_S   # for busy: another session's verb holds the backup root's lock
LAUNCH_IN_FLIGHT_RETRY_TOTAL_S = 95.0   # for launch_in_flight: 90 s from the claim (__main__.LAUNCH_IN_FLIGHT_S); only
                                        # once the game is ended here, which the fixture cannot do
DRAIN_S = 0.5                           # before a read: a stop left over from an earlier one (real seconds: dap's clock)
PROOF_PAUSE_S = 2.0                     # after a round: two date reads this far apart must agree, or the game runs
WATCH_RESPAWNS = 3                      # a watch that returns while the game's window is up is run again, this often

_RETRIED = ("refused", "game_left_up")  # a stop that ended so is run again by the next stop()

_TAG = re.compile(r"[A-Za-z0-9_]{1,16}")
_EVENT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.]*")
_DAYS_BEFORE = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


class SessionError(Exception):
    """A verb that did not go through. `code` names why; `info` holds what goes with it (`reply`: a protective
    verb's reply; `stop`: the reply of the `stop` a failed start ran; `screenshot`, …).

    Codes: already_started, overlay_left, no_permission, bad_argument, bad_tag, no_save, held_snapshot,
    held_unknown, overlay_refused, fixture_failed, snapshot_refused, launch_refused (with `game_may_be_up` when a
    game may have started all the same), bad_launch_reply, unknown_start, game_gone, no_window,
    breakpoint_unverified, debugger, no_stop, unexpected_stop, maybe_stopped, no_date, bad_date, tag_failed,
    use_read, unknown_setup, setup_not_logged, bad_reply, nothing_pending, bad_index, not_selected, no_country,
    not_on_country_select, click_refused, not_entered, left_running, bad_days, stalled, not_started, stopped
    (also `start`'s, when a stop was asked while it ran), watch_ended, already_pending. A read-side error carries
    `maybe_stopped` when the game may still be stopped at the breakpoint (the next verb then releases it first,
    or refuses `maybe_stopped`). After `launch`, a console error that ended `start` keeps its own code (no_ack,
    not_foreground, …) and `entered`, as does one that ended `try_event` (whose error also carries the rows so
    far, `options`)."""

    def __init__(self, code: str, detail: str = "", **info: Any) -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code, self.detail, self.info = code, detail, info


@dataclass
class Read:
    expr: str
    ok: bool
    raw: str
    value: bool | float | None


@dataclass
class Paths:
    """Where things are. The Windows forms are given, not worked out here, so tests need no `wslpath`."""
    user_data: Path
    backup_root: Path
    deploy_dir: Path
    base_game: Path
    overlay_windows_path: str                       # the overlay folder as Windows names it, for `launch --add-mod`
    events_file_windows_path: Callable[[Path], str]  # a file of the overlay as Windows names it: the breakpoint's path
    game_version: str
    enabled_mods: Sequence[str]                     # the owner's playset (content_load.json), in order
    deployed_mod_windows_path: str                  # the deployed mod's folder as Windows names it: what mod_only keeps

    @property
    def overlay_dir(self) -> Path:
        return Path(self.user_data) / "mod" / overlay.OVERLAY_NAME

    @property
    def run_root(self) -> Path:
        return Path(self.backup_root) / "runs"

    @property
    def history(self) -> Path:
        return Path(self.user_data) / "console_history.txt"

    @property
    def logs(self) -> Path:
        return Path(self.user_data) / "logs"


class _ProvedHelper:
    """The helper as everything that sends input sees it (X1): `keys`, `focus` and `click` go out only once
    `Session._prove_game` has passed, just before each one, since the helper sends by pid alone and a pid may be
    another program's once the game has died. Every other call goes to the session's current helper (a fresh one
    from `_new_helper` too)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __getattr__(self, name: str):
        return getattr(self._session._helper, name)

    def keys(self, pid: int, steps: Sequence[dict]) -> None:
        self._session._prove_game()
        return self._session._helper.keys(pid, steps)

    def focus(self, pid: int) -> bool:
        self._session._prove_game()
        return self._session._helper.focus(pid)

    def click(self, pid: int, x: int, y: int) -> None:
        self._session._prove_game()
        return self._session._helper.click(pid, x, y)


class Session:
    """One game's session. Single-threaded by contract: one call at a time, as the session server makes them (a
    plain HTTPServer, one request at a time in its main thread). The `_starting`, `_abort` and `_stopping` flags
    only answer a `stop()` made from inside a running verb (a signal handler's, a test's); nothing here locks."""

    def __init__(self, helper: Helper, run_cli: RunCli, spawn_watch: Callable[[str], Any], paths: Paths,
                 sleep=time.sleep, clock=time.monotonic, helper_factory: Callable[[], Helper] | None = None) -> None:
        """`helper_factory` makes a new helper when the one in use has ended (`helper_gone`) as `stop` ends the
        game: the new one adopts the game by launch's record, then ends it. Without it the game is left up."""
        self._helper, self._run_cli, self._spawn_watch, self._paths = helper, run_cli, spawn_watch, paths
        self._sleep, self._clock = sleep, clock
        self._helper_factory = helper_factory
        self._began = False                 # start() got past its refusals
        self._starting = False              # start() is running: a stop() is left to it
        self._abort = False                 # a stop() came while start() ran
        self._stopping = False              # stop() is running: a stop() inside it does nothing
        self._ready = False                 # start() finished: the other verbs may run
        self._permission: str | None = None
        self._overlay: overlay.Overlay | None = None     # built by this session, so stop removes it
        self._save: str | None = None
        self._snapshot: str | None = None
        self._report: Report | None = None
        self._early: list[tuple[str, dict]] = []         # steps from before the run folder existed
        self._launched = False              # `launch` answered other than a no-game refusal: a game may be up
        self._launch_reply: dict = {}
        self._game_ended = False            # the launched game is known to be over: ended here, or gone already
        self._fixture_loaded = False        # the save is the fixture, which opens on the country-select screen
        self._verdict: tuple[dict, int] | None = None    # the fixture's own restore's verdict, for stop to report
        self._snapshot_unknown = False      # a snapshot's reply was lost: one may have been taken and left armed
        self._watch: Any = None
        self._proc: ProcId | None = None
        self._adopted = False
        self._debug_log: LogFollower | None = None       # the session's own followers: Console consumes its own
        self._error_log: LogFollower | None = None
        self._console: Console | None = None
        self._relay_open = False
        self._debugger: Debugger | None = None
        self._country: str | None = None
        self._entered = False
        self._shots = 0
        self._stopped: dict | None = None
        self._maybe_stopped = False         # the game may be stopped at the breakpoint: the next verb releases it
        self._left_running = False          # a round may have left the game unpaused: no more time until stop
        self._watch_respawns = 0
        self._watch_ended: str | None = None     # why the verbs ended for good: watch saw the exit, or a doubt
        self._sends = _ProvedHelper(self)       # the only way a key, focus or click goes out (`_prove_game`)
        self._notes: list[str] = []         # for the stop's reply and the summary
        self._errors_seen: list[str] | None = None       # while try_event collects: the error.log lines polled
        self._burst: list[str] | None = None             # while try_event collects: the debugger's own output

    # ---- start

    def start(self, permission: str, as_tag: str | None = None, setups: Mapping[str, str] | None = None,
              save: str | None = None, playset: str = "mod_only", owner_confirmed_busy: bool = False) -> dict:
        """Get a game up on the fixture (made first if missing) or on `save`, played as `as_tag`.

        Refused with nothing done, and the session left as it was: an overlay folder already there (an earlier
        run's playset may still name it: `overlay_left`, and it is neither replaced nor removed), an empty
        permission, a bad argument or setup, a save that is not there, and any held snapshot (only the owner
        resolves a hold, and a hold leaves the run's playset in place). A second start, or one after `stop`, is
        refused. A refused snapshot or launch raises with the verb's reply and starts nothing further. Every
        failure once the session has begun runs `stop()` before raising (its reply is the error's `info["stop"]`),
        an interrupt (KeyboardInterrupt, SystemExit) too, which is then raised again. A `stop()` called while this
        runs is left to it: it answers `deferred_to_start`, and this ends at its next step with `stopped`."""
        if self._began or self._stopped is not None:
            raise SessionError("already_started", "a session runs one game: stop it and start a new session")
        if os.path.lexists(self._paths.overlay_dir):
            raise SessionError("overlay_left", "%s is there already, left by an earlier run whose playset may still "
                               "name it: finish that run (`python3 -m game_qa recover`, or `restore <id>` once no "
                               "game is running), then run `python3 -m game_qa remove-overlay`. Nothing was done"
                               % self._paths.overlay_dir)
        if not isinstance(permission, str) or not permission.strip():
            raise SessionError("no_permission", "say where the go-ahead to launch came from")
        if playset not in PLAYSETS:
            raise SessionError("bad_argument", "playset is one of %s, not %r" % (", ".join(PLAYSETS), playset))
        if as_tag is not None:
            _check_tag(as_tag)
        if setups is not None and not isinstance(setups, Mapping):
            raise SessionError("bad_argument", "setups maps a setup's name to its script, not %r" % (setups,))
        setups = dict(setups or {})
        try:
            overlay.check_setups(setups)
        except overlay.OverlayError as e:
            raise SessionError("overlay_refused", str(e)) from e
        if save is not None:
            save = self._check_save(save)
        self._starting = True                   # from `held` on, a stop() is left to this
        try:
            self._refuse_if_held()
        except BaseException:
            # Nothing was begun, so a stop asked meanwhile has nothing to stop: it is forgotten with the start.
            self._starting = self._abort = False
            raise
        self._began = True
        self._permission = permission
        try:
            result = self._start(permission, as_tag, setups, save, playset, owner_confirmed_busy)
            self._check_abort()
            return result
        except BaseException as e:
            self._starting = False
            stopped = self.stop()
            if not isinstance(e, Exception):
                raise
            if isinstance(e, SessionError):
                e.info["stop"] = stopped
                raise
            extra = {"entered": e.entered} if isinstance(e, ConsoleError) else {}
            raise SessionError(_code_of(e), str(e), stop=stopped, **extra) from e
        finally:
            self._starting = False

    def _start(self, permission: str, as_tag: str | None, setups: dict[str, str], save: str | None, playset: str,
               busy: bool) -> dict:
        self._check_abort()
        try:
            self._overlay = overlay.build(self._paths.overlay_dir, setups, self._paths.game_version)
        except overlay.OverlayError as e:
            raise SessionError("overlay_refused", str(e)) from e
        self._record("overlay", outcome="built", setups=sorted(self._overlay.setup_events))
        save, made, pruned = self._the_save(save, permission, playset, busy)
        self._save = save
        self._check_abort()
        try:
            reply, code = self._cli(["snapshot", "--save", save])
        except BaseException:
            self._snapshot_unknown = True       # it may have been taken, and armed, before the reply was lost
            raise
        snap = reply.get("id")
        if code != 0 or not isinstance(snap, str) or not snap:
            self._snapshot_unknown = _reply_lost(reply, code)
            self._record("snapshot", outcome="refused", reply=reply)
            raise SessionError("snapshot_refused", _why(reply), reply=reply)
        self._snapshot = snap
        self._open_report(snap)
        self._record("snapshot", outcome="ok", reply=reply)
        self._check_abort()

        argv = ["launch", snap, "--permission", permission, "--playset", playset,
                "--add-mod", self._paths.overlay_windows_path]
        if busy:
            argv.append("--owner-confirmed-busy")
        argv += ["--", *SESSION_ARGS, "-loadsave=" + save]
        try:
            reply, code = self._cli(argv)
        except Exception as e:
            reply, code = {"refused": "no_reply", "detail": "launch could not be run, or its reply was lost: %r"
                           % e}, 2
        except BaseException:
            # Interrupted: the launch may have got as far as starting the game. Watched, and never restored beside.
            self._launched = True
            try:
                self._watch = self._spawn_watch(snap)
            except Exception:
                pass
            raise
        if code != 0 and fixture.no_game(reply):
            self._record("launch", outcome="refused", reply=reply)
            raise SessionError("launch_refused", _why(reply), reply=reply)
        # From here a game of this run may be up, whatever the reply says: it is watched, and stop ends it by
        # launch's own record of it when the reply gives one.
        self._launched = True
        self._launch_reply = reply
        # At once: part 1 holds a run whose first look came more than 120 s after the start.
        self._watch = self._spawn_watch(snap)
        self._record("launch", outcome="ok" if code == 0 else "refused", reply=reply)
        self._check_abort()
        if code != 0:
            raise SessionError("launch_refused", "%s; a game may have started all the same, so it is watched and "
                               "ended by the pid and start time the reply gives, if it gives them" % _why(reply),
                               reply=reply, game_may_be_up=True)
        self._proc = _proc_of(reply)
        self._helper.adopt(self._proc)
        self._adopted = True
        self._await_window()

        self._debug_log = LogFollower(self._paths.logs / "debug.log")
        self._error_log = LogFollower(self._paths.logs / "error.log")
        self._console = Console(self._sends, self._proc, self._paths.history,
                                LogFollower(self._paths.logs / "debug.log"), sleep=self._sleep, clock=self._clock)
        with self._step("console_ready"):
            self._console.ensure_open(CONSOLE_READY_S)
        if as_tag is not None:
            with self._step("tag", tag=as_tag):
                self._tag(as_tag)
        self._attach()
        self._check_abort()
        self._ready = True
        ov = self._overlay
        result = {
            "snapshot": snap, "pid": self._proc.pid, "created": self._proc.created, "save": save,
            "fixture_made": made, "country": self._country,
            "overlay": {"dir": str(ov.dir), "events_file": str(ov.events_file), "read_line": ov.read_line,
                        "setup_events": dict(ov.setup_events)},
            "run_dir": str(self._report.dir),
        }
        if pruned:
            result["fixtures_pruned"] = pruned
        self._record("start", outcome="ok", **result)
        return result

    def _check_abort(self) -> None:
        if self._abort:
            raise SessionError("stopped", "stop was asked while start ran: start has stopped the session")

    def _refuse_if_held(self) -> None:
        try:
            reply, code = self._cli(["held"])
        except Exception as e:
            raise SessionError("held_unknown", "`held` could not be run, so a hold cannot be ruled out: %r" % e) from e
        held = reply.get("held")
        if code != 0 or not isinstance(held, list):
            raise SessionError("held_unknown", "`held` did not answer, so a hold cannot be ruled out: %s"
                               % _why(reply), reply=reply)
        if held:
            raise SessionError("held_snapshot", "held: %s. Only the owner resolves a hold (the run's playset is "
                               "still in place); nothing was started" % ", ".join(map(str, held)), reply=reply)
        self._record("held", outcome="none")

    def _check_save(self, save: str) -> str:
        """The save's name as `-loadsave` takes it (no `.v3`), once it is known to be in `save games/`."""
        name = save[:-3] if isinstance(save, str) and save.endswith(".v3") else save
        if (not isinstance(name, str) or not name.strip() or name != Path(name).name or name.startswith("-")
                or not name.isprintable()):
            raise SessionError("bad_argument", "a save is a file name in save games/, not %r" % (save,))
        if not (Path(self._paths.user_data) / fixture.SAVE_FOLDER / (name + ".v3")).is_file():
            raise SessionError("no_save", "there is no save games/%s.v3" % name)
        return name

    def _the_save(self, save: str | None, permission: str, playset: str, busy: bool) -> tuple[str, bool, list[str]]:
        """(the save to load, whether the fixture was made now, the fixtures pruned)."""
        if save is not None:
            self._record("fixture", outcome="not_used", save=save)
            return save, False, []
        self._fixture_loaded = True
        user = Path(self._paths.user_data)
        loads = run_playset(playset, self._paths.enabled_mods, self._paths.deployed_mod_windows_path,
                            self._paths.overlay_windows_path)
        key = fixture.key(self._paths.game_version, loads, self._paths.deploy_dir, playset=playset)
        found = fixture.find(user, key)
        if found is not None:
            self._record("fixture", outcome="found", save=found.stem)
            return found.stem, False, []
        calls: list[tuple[str, dict | None, int | None]] = []      # the fixture's own verbs, as they answered
        watches: list[Any] = []                                     # the watch it spawned

        def run_cli(argv):
            try:
                reply, code = self._run_cli(argv)
            except BaseException:
                calls.append((argv[0], None, None))
                raise
            calls.append((argv[0], reply if isinstance(reply, dict) else None, code))
            return reply, code

        def spawn_watch(snapshot_id):
            watch = self._spawn_watch(snapshot_id)
            watches.append(watch)
            return watch
        try:
            made = fixture.make(run_cli, user, key, self._paths.overlay_windows_path, permission, playset,
                                owner_confirmed_busy=busy, sleep=self._sleep, spawn_watch=spawn_watch,
                                clock=self._clock, started=self._journaled_proc)
        except fixture.FixtureError as e:
            up = e.code == fixture.GAME_MAY_BE_UP
            self._take_fixture_run(e.snapshot or _fixture_snapshot(calls), up, e.proc, e.watch, e.restore, calls)
            self._record("fixture", outcome="failed", step=e.step, code=e.code, reply=e.reply, snapshot=e.snapshot)
            info: dict[str, Any] = {"step": e.step, "reply": e.reply, "snapshot": e.snapshot}
            if up:
                info.update(game_may_be_up=True,
                            game={"pid": e.proc.pid, "created": e.proc.created} if e.proc is not None else None)
            raise SessionError("fixture_failed", str(e), **info) from e
        except BaseException:
            launches = [reply for verb, reply, _code in calls if verb == "launch"]
            self._take_fixture_run(_fixture_snapshot(calls), bool(launches), _named_proc(launches[-1] or {})
                                   if launches else None, watches[-1] if watches else None, None, calls)
            raise
        try:
            pruned = fixture.prune(user, keep=FIXTURES_KEPT)
        except OSError as e:
            pruned = []
            self._record("fixture_prune", outcome="failed", detail=str(e))
        self._record("fixture", outcome="made", save=made.stem, pruned=pruned)
        return made.stem, True, pruned

    def _take_fixture_run(self, snap: str | None, may_be_up: bool, proc: ProcId | None, watch: Any,
                          restore: tuple[dict, int] | None, calls: list[tuple[str, dict | None, int | None]]) -> None:
        """After the fixture's run failed, the session takes its snapshot as the one to finish, and a game the run
        may have left up as its own launched game: `stop` then ends that game by its pid and start time (from
        launch's reply, else the snapshot's journal), waits for the fixture's watch, and restores that snapshot
        before any overlay rule applies. A verdict the fixture's own restore gave (restored, held) is reported,
        not asked for again. The run's folder is that snapshot's."""
        if snap is None:
            snaps = [(reply, code) for verb, reply, code in calls if verb == "snapshot"]
            self._snapshot_unknown = bool(snaps) and _reply_lost(*snaps[-1])
            return
        self._snapshot = snap
        try:
            self._open_report(snap)
        except OSError:
            pass                                # the record is a convenience: stop still finishes the snapshot
        if may_be_up:
            self._launched = True
            self._launch_reply = {"pid": proc.pid, "created": proc.created} if proc is not None else {}
            self._watch = watch
        elif restore is not None and (restore[1] == 0 or restore[0].get("held") is True):
            self._verdict = restore

    def _journaled_proc(self, snap_id: str | None) -> ProcId | None:
        """The game process the snapshot's journal last records as `started` (launch writes it the moment the game
        exists), or None: no such snapshot, no `started`, or one that cannot be read. A start time recorded as
        unknown comes back as such, and nothing is ended by it."""
        if not snap_id:
            return None
        try:
            for snap in snapshot.all_snapshots(self._paths.backup_root):
                if snap.id == snap_id:
                    starts = [e for e in snapshot.journal(snap) if e.get("event") == "started"]
                    return _named_proc(starts[-1]) if starts else None
        except OSError:
            pass
        return None

    def _await_window(self) -> None:
        deadline = self._clock() + WINDOW_WAIT_S
        while True:
            self._check_abort()
            win = self._helper.window(self._proc.pid)
            if win.exists and win.responding:
                self._record("window", outcome="ok", client=list(win.client))
                return
            if self._watch_returned():
                raise SessionError("game_gone", "`watch` returned before the game's window answered: the game ended")
            if self._clock() >= deadline:
                raise SessionError("no_window", "no responding window within %g s of the launch" % WINDOW_WAIT_S)
            self._sleep(WINDOW_POLL_S)

    def _attach(self) -> None:
        self._helper.tcp_open(DEBUGGER_PORT)
        self._relay_open = True
        # dap turns whatever the relay raises (a HelperError on a closed peer) into a DebuggerError.
        self._debugger = Debugger(self._helper.tcp_send, self._helper.tcp_recv)
        path = self._paths.events_file_windows_path(self._overlay.events_file)
        with self._step("debugger", breakpoint=path, line=self._overlay.read_line) as out:
            try:
                verified = self._debugger.attach({path: [self._overlay.read_line]})
            except DebuggerError as e:
                raise SessionError("debugger", str(e)) from e
            out["verified"] = verified.get(path)
            if verified.get(path) != [True]:
                raise SessionError("breakpoint_unverified", "the game did not verify the breakpoint at %s:%d, so no "
                                   "read would stop there" % (path, self._overlay.read_line))

    # ---- the verbs

    def console(self, text: str) -> Reply:
        """One console command, with its reply. Any text that starts `event te_qa.1`, in any case and spacing and
        whatever follows, is refused: the read event would stop at the breakpoint with nobody to resume it (`read`
        is its verb)."""
        self._require_game()
        with self._step("console", text=text) as out:
            if " ".join(str(text).split()).lower().startswith(READ_COMMAND.lower()):
                raise SessionError("use_read", "%r may run the read event, which stops at the debugger's "
                                   "breakpoint: use read" % text)
            reply = self._console.run(text)
            out.update(ok=reply.ok, lines=reply.lines)
        return reply

    def run_setup(self, name: str) -> list[str]:
        """Run a setup through its event; return its log lines between its start and done markers."""
        self._require_game()
        with self._step("run_setup", name=name) as out:
            event = self._overlay.setup_events.get(name)
            if event is None:
                raise SessionError("unknown_setup", "no setup %r; the overlay has %s"
                                   % (name, sorted(self._overlay.setup_events) or "none"))
            self._new_lines()                   # what was logged before is not this setup's
            self._console.run("event " + event, reply=False)
            lines = self._setup_lines(name)
            out["lines"] = len(lines)
        return lines

    def events(self) -> list[Pending]:
        self._require_game()
        with self._step("events") as out:
            pending = self._pending()
            out["pending"] = [asdict(p) for p in pending]
        return pending

    def pick(self, index: int, event: str | None = None) -> dict:
        """Pick option `index` of a pending event, always by its numeric id. `event` is an event id or a numeric
        id; by event id the oldest pending instance is taken (the lowest numeric id: the game hands them out in
        order, assumed) and `ambiguous` says there was more than one; with no `event`, the oldest of all."""
        self._require_game()
        with self._step("pick", index=index, event=event) as out:
            pending = self._pending()
            if event is None:
                matches = pending
            elif str(event).isdigit():
                matches = [p for p in pending if p.numeric_id == int(event)]
            else:
                matches = [p for p in pending if p.event_id == event]
            if not matches:
                raise SessionError("nothing_pending", "%s is pending; pending: %s" % (
                    "nothing" if event is None else repr(event),
                    ", ".join("%d %s" % (p.numeric_id, p.event_id) for p in pending) or "none"))
            chosen = min(matches, key=lambda p: p.numeric_id)
            if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < chosen.options:
                raise SessionError("bad_index", "%s has %d options (0 to %d), not %r"
                                   % (chosen.event_id, chosen.options, chosen.options - 1, index))
            command = "select_event_option %d %d" % (index, chosen.numeric_id)
            reply = self._console.run(command)
            if "Selected option %d of %s" % (index, chosen.event_id) not in [line.strip() for line in reply.lines]:
                raise SessionError("not_selected", "%r answered %r" % (command, reply.lines), lines=reply.lines)
            result = {"event": chosen.event_id, "numeric_id": chosen.numeric_id, "index": index,
                      "options": chosen.options, "ambiguous": len(matches) > 1, "reply": reply.lines}
            out.update(result)
        return result

    def read(self, exprs: Sequence[str]) -> list[Read]:
        """Each trigger or value evaluated at the read event's breakpoint, in the played country's scope."""
        self._require_game()
        if isinstance(exprs, str):
            raise SessionError("bad_argument", "read takes a list of expressions, not one string")
        exprs = list(exprs)
        with self._step("read", exprs=exprs) as out:
            reads, info = self._fire_read(exprs)
            when = self._date_in(self._new_lines())
            out.update(info, values=[[r.expr, r.ok, r.raw] for r in reads], date=when)
        return reads

    def tag(self, tag: str) -> None:
        self._require_game()
        with self._step("tag", tag=tag):
            self._tag(tag)

    def enter_game(self) -> dict:
        """Click the country the camera is on, then Start, and prove it by the date moving while unpaused. Only
        the fixture opens on the country-select screen: with an owner's save it is refused
        (`not_on_country_select`), and `advance` needs no entering."""
        self._require_game()
        self._refuse_if_left_running()
        if not self._fixture_loaded:
            raise SessionError("not_on_country_select", "the game was started on a save of the owner's, which "
                               "opens in play: there is no country-select screen to click (advance works as it is)")
        with self._step("enter_game") as out:
            result = self._enter()
            out.update(result)
        return result

    def advance(self, days: int) -> tuple[int, int, int]:
        """Let at least `days` game days pass (entering the fixture's game first if need be); return the date
        reached."""
        self._require_game()
        self._refuse_if_left_running()
        if isinstance(days, bool) or not isinstance(days, int) or days < 1:
            raise SessionError("bad_days", "days is a whole number of at least 1, not %r" % (days,))
        if self._fixture_loaded and not self._entered:
            start = tuple(self.enter_game()["after"])
        else:
            start = None
        with self._step("advance", days=days) as out:
            reached = self._advance(days, start, out)
        return reached

    def shot(self) -> Path:
        self._require_game(types=False)
        with self._step("shot") as out:
            path = self._shot()
            out["path"] = str(path)
        return path

    def try_event(self, event: str, setup: str | None, reads: Sequence[str]) -> dict:
        """The owner's first check: each option of `event` in turn, fired, read, picked and read again.

        Before anything else, `event` must not be pending already: a firing that did nothing would then look like
        one that worked. Then for option 0, 1, …: run `setup` when given; fire the event with console `event <id>`,
        unless the setup's own log lines name it (the setup fired it); list the pending events; if `event` is not
        pending the loop stops, which is never a pass, and the row says `ran_not_pending` when the console's reply
        says it ran (`Executed "<id>"`: a hidden event, or one that resolved at once, whose options cannot be
        picked), else `did_not_fire`; else read `reads`, pick the option, read them again. The number of options
        is the first `events` reply's for `event`.

        The options share one game: each runs on the state the one before left, re-running the setup first
        (console `event` ignores the trigger and the cooldown, spec § 12.1 A6), and the reply says so
        (`shared_state`). A row's `new_errors` are the error-log lines seen during that option, less blank lines
        and less what the debugger reported as its own output while stopped for this call's reads (the
        validator burst each trigger evaluation causes): its file lags its stream, so a burst may land in the
        next option's lines. An error in a step raises like any verb's, carrying the rows so far (`options`),
        and nothing is typed again. `complete` is true only when every option fired and was picked."""
        self._require_game()
        if isinstance(reads, str) or not all(isinstance(r, str) for r in reads):
            raise SessionError("bad_argument", "reads is a list of expressions, not %r" % (reads,))
        reads = list(reads)
        if (not isinstance(event, str) or _EVENT.fullmatch(event) is None
                or len(FIRE_COMMAND % event) > CLEAR_BACKSPACES):
            raise SessionError("bad_argument", "an event id is letters, digits, _ and ., such as x.1, and short "
                               "enough to type into the console, not %r" % (event,))
        if event == overlay.READ_EVENT:
            raise SessionError("use_read", "%s is the read event: `read` is its verb" % event)
        if setup is not None and setup not in self._overlay.setup_events:
            raise SessionError("unknown_setup", "no setup %r; the overlay has %s"
                               % (setup, sorted(self._overlay.setup_events) or "none"))
        rows: list[dict] = []
        with self._step("try_event", event=event, setup=setup, reads=reads) as out:
            out.update(shared_state=True, options=rows)
            already = [p for p in self._pending() if p.event_id == event]
            if already:
                raise SessionError("already_pending", "%s is pending already (%s): pick it first, or a firing that "
                                   "did nothing would look like one that worked"
                                   % (event, ", ".join(str(p.numeric_id) for p in already)))
            count = None
            self._burst = []
            try:
                while count is None or len(rows) < count:
                    row = {"index": len(rows), "fired": False, "fired_by": None, "pending_options": None,
                           "before": [], "after": [], "picked": None, "new_errors": [], "did_not_fire": False,
                           "ran_not_pending": False}
                    rows.append(row)
                    self._try_option(event, setup, reads, row)
                    if row["did_not_fire"] or row["ran_not_pending"]:
                        break
                    if count is None:
                        count = row["pending_options"]
            except SessionError as e:
                e.info["options"] = rows
                raise
            except (ConsoleError, DebuggerError, HelperError) as e:
                extra = {"entered": e.entered} if isinstance(e, ConsoleError) else {}
                raise SessionError(_code_of(e), str(e), options=rows, **extra) from e
            finally:
                self._burst = None
            complete = (count is not None and len(rows) == count
                        and all(r["fired"] and r["picked"] is not None for r in rows))
            out.update(option_count=count, complete=complete)
        return {"event": event, "setup": setup, "shared_state": True, "option_count": count, "complete": complete,
                "options": rows}

    def _try_option(self, event: str, setup: str | None, reads: list[str], row: dict) -> None:
        """One option of `try_event`, filling `row`; its new errors are filled in however it ends."""
        self._new_lines()                       # what the logs held before is not this option's
        self._errors_seen = []
        try:
            fired_by_setup = setup is not None and any(_names_event(line, event) for line in self.run_setup(setup))
            ran = False
            if not fired_by_setup:
                executed = 'Executed "%s"' % event
                ran = any(line.strip() == executed for line in self.console(FIRE_COMMAND % event).lines)
            row["fired_by"] = "setup" if fired_by_setup else "console"
            mine = [p for p in self.events() if p.event_id == event]
            if not mine:
                row["ran_not_pending" if ran else "did_not_fire"] = True
                return
            row["fired"] = True
            row["pending_options"] = min(mine, key=lambda p: p.numeric_id).options
            if reads:
                row["before"] = [asdict(r) for r in self.read(reads)]
            row["picked"] = self.pick(row["index"], event)
            if reads:
                row["after"] = [asdict(r) for r in self.read(reads)]
        finally:
            try:
                self._new_lines()               # the option's last lines
            except Exception:
                pass                            # an error of its own must not hide the one that ended the option
            seen, self._errors_seen = self._errors_seen, None
            row["new_errors"] = _new_errors(seen, self._burst or [])

    def status(self) -> dict:
        """How far this session is, from what it holds: nothing is asked of the game or of a verb."""
        proc = self._proc
        return {"started": self._ready, "stopped": self._stopped is not None, "snapshot": self._snapshot,
                "save": self._save, "country": self._country, "entered": self._entered,
                "game": {"pid": proc.pid, "created": proc.created} if proc is not None else None,
                "watch_returned": self._watch_returned(),
                "run_dir": str(self._report.dir) if self._report is not None else None,
                "maybe_stopped": self._maybe_stopped, "left_running": self._left_running,
                "watch_respawns": self._watch_respawns}

    # ---- stop

    def stop(self) -> dict:
        """End the game this session started and put the owner's files back; never raises.

        In order: end the game (`kill`; adopted first if a failure came before `adopt`; through a fresh helper
        from `helper_factory` once if the helper has ended), wait for `watch` to return (up to WATCH_WAIT_S),
        `restore <id>` (retried every RESTORE_RETRY_S while it refuses watch_still_recording, up to
        RESTORE_RETRY_TOTAL_S; busy, up to BUSY_RETRY_TOTAL_S; or launch_in_flight, which a launch that was not
        recorded leaves for 90 s after its claim, up to LAUNCH_IN_FLIGHT_RETRY_TOTAL_S: by now the launch call
        has returned), remove the overlay this session built, close
        the debugger's relay and the helper, close the report. With no launch, a snapshot taken is still
        restored: an armed one blocks every later one. After a failed fixture run its snapshot is the one
        finished, and a game it may have left up is this session's own (`_take_fixture_run`). A snapshot whose
        reply was lost is reported (`snapshot_unknown`, and `next`: `recover`), never taken for none.

        A game that may still be up (no start time to end it by, a kill refused, the helper gone) is not
        restored beside: `outcome` is game_left_up and `next` says what can work (`stop` again for a game known
        by pid and start time; else `restore <id>`, or `recover` when no process is known, once no game runs).
        The overlay is removed only once the game is known ended and restore put the owner's playset back
        (`restored`, or `held` with `playset_restored`); otherwise `overlay_kept` is true and
        `overlay_kept_because` says why.

        The reply is restore's reply plus `outcome` (restored, held, refused, game_left_up, or None with no
        snapshot), `snapshot`, `overlay_removed`, `overlay_kept`, `report` (the summary's path) and any `notes`.
        `stop_again` says whether a later call can change anything: true after a refused restore, and after a game
        left up whose pid and start time are known (a later call may end it, or find it gone); false otherwise,
        since a process nothing can name is never ended here, and the caller is then told what to do instead.
        A later call returns that reply again, unless it ended refused or game_left_up: then it is run again,
        from ending the game if that was not done, keeping the notes of the stop before (with a note that it ran
        again). Called while `start` runs, it answers `deferred_to_start` and `start` stops the session itself;
        called inside a stop under way, it answers `in_progress`."""
        if self._stopping:
            return {"outcome": "in_progress", "snapshot": self._snapshot, "detail": "a stop is under way"}
        if self._starting:
            self._abort = True
            return {"outcome": "deferred_to_start", "snapshot": self._snapshot,
                    "detail": "start is running: it stops the session at its next step and raises `stopped`"}
        if not self._began:
            return {"outcome": None, "snapshot": None, "overlay_removed": False, "report": None}
        if self._stopped is not None and self._stopped.get("outcome") not in _RETRIED:
            return self._stopped
        self._stopping = True
        previous = self._stopped
        try:
            self._stopped = self._stop(previous)
        except Exception as e:      # a backstop: each stage below already catches its own failures
            self._stopped = {"snapshot": self._snapshot, "outcome": "error", "stop_again": False,
                             "notes": [*((previous or {}).get("notes") or []), "stop failed: %r" % e]}
        finally:
            self._stopping = False
        return self._stopped

    def _stop(self, previous: dict | None = None) -> dict:
        notes = list(self._notes)
        if previous is not None:            # N12: what the stop before found stays in the reply and the report
            kept = [n for n in previous.get("notes") or () if isinstance(n, str)]
            notes = kept + [n for n in notes if n not in kept]
            notes.append("stop was run again at %s: the stop before ended %s" % (stamp(utc_now()),
                                                                                 previous.get("outcome")))
        if self._launched and not self._game_ended:
            self._end_game(notes)
        left_up = self._launched and not self._game_ended
        restore, outcome = None, None
        if left_up:
            outcome = "game_left_up"
            self._record("restore", outcome="not_run", detail="the game may still be up")
        else:
            if self._launched:
                self._await_watch(notes)
            if self._snapshot is not None and self._verdict is not None:
                restore, outcome = self._fixture_verdict()
            elif self._snapshot is not None:
                restore, outcome = self._restore(notes)
        if left_up and (self._watch is None or self._watch_returned()):
            notes.append("no `watch` follows that game: its exit will not be recorded, so a restore of snapshot %s "
                         "will likely be held for the owner" % self._snapshot)
        removed, kept = self._settle_overlay(restore, outcome, notes)
        self._close_relay(notes)
        self._close_helper(notes)
        reply = dict(restore) if restore is not None else {}
        reply.update(outcome=outcome, snapshot=self._snapshot, overlay_removed=removed)
        if self._overlay is not None:
            reply["overlay_kept"] = kept is not None
        if kept is not None:
            reply["overlay_kept_because"] = kept
        reply["stop_again"] = outcome == "refused"
        if left_up:
            reply["game_unwatched"] = self._watch is None or self._watch_returned()
            reply["next"], reply["stop_again"] = self._left_up_next()
        elif outcome == "refused":
            reply["next"] = ("`python3 -m game_qa stop` again runs `restore %s` again, once what refused it is "
                             "cleared (a Victoria 3 process running, another verb in the backup root): the server "
                             "answers until a stop ends restored or held" % self._snapshot)
        if self._snapshot_unknown:
            reply["snapshot_unknown"] = True
            notes.append("a snapshot's reply was lost, so a snapshot may have been taken and left armed")
            reply["next"] = ("a snapshot may have been taken (its reply was lost) and left armed: `start` refuses "
                             "(unfinished_run) until `python3 -m game_qa recover` finishes it, once no Victoria 3 "
                             "process runs")
        reply["report"] = self._close_report(restore, outcome, removed, kept, notes, reply.get("next"))
        if notes:
            reply["notes"] = notes
        return reply

    def _left_up_next(self) -> tuple[str, bool]:
        """What to do about a game left up, by what is known of its process, and whether `stop` again can help:
        only a process named by pid and start time can be ended, or found gone, by a later stop."""
        proc = self._proc or _named_proc(self._launch_reply) or self._journaled_proc(self._snapshot)
        if proc is None:
            return ("a game of this run may still be up, and neither launch's reply nor the snapshot's journal names "
                    "its process, so nothing here can end it or tell when it has gone. Once no Victoria 3 process "
                    "runs: `python3 -m game_qa recover` (it finishes snapshot %s), then `python3 -m game_qa "
                    "remove-overlay`" % self._snapshot), False
        if proc.created == UNKNOWN_START:
            return ("the harness's game (pid %d) may still be up, and its start time is not known, so it was not "
                    "ended: a pid alone may be another game's. Once no Victoria 3 process runs: `python3 -m game_qa "
                    "restore %s`, then `python3 -m game_qa remove-overlay`" % (proc.pid, self._snapshot)), False
        return ("the harness's game (pid %d, started %s) may still be up: ending it failed. `python3 -m game_qa stop` "
                "again tries again to end it by its pid and start time (or finds it gone), then restores snapshot %s; "
                "if it keeps failing, ask the owner to close the game" % (proc.pid, proc.created, self._snapshot)), True

    def _end_game(self, notes: list[str]) -> None:
        """End the game, setting `_game_ended` once it is known to be over; any doubt leaves it up, noted."""
        # `launch`'s own record of the game, if the failure came before it was taken as `_proc`: its reply, else
        # (a reply lost after the start was journaled) the snapshot's journal. The helper adopts a process only
        # when its creation time matches (win_helper._op_adopt).
        proc = self._proc or _named_proc(self._launch_reply) or self._journaled_proc(self._snapshot)
        if proc is None:
            notes.append("the game's process is not known (neither launch's reply nor the snapshot's journal names "
                         "it), so it was not ended and may still be up")
            return
        if proc.created == UNKNOWN_START:
            # A pid alone may be another game's by now: wait for no game at all, then restore (part 1's rule).
            notes.append("launch recorded no start time for pid %d, so it was not ended: a pid alone may be "
                         "another game's" % proc.pid)
            return
        try:
            self._kill(proc, notes)
            return
        except HelperError as e:
            if e.code != "helper_gone" or self._helper_factory is None:
                self._kill_failed(notes, e)
                return
            notes.append("the helper had ended (%s), so a new one adopts the game and ends it" % e.detail)
        except Exception as e:
            self._kill_failed(notes, e)
            return
        try:
            self._new_helper()
            self._kill(proc, notes)
        except Exception as e:
            self._kill_failed(notes, e)

    def _kill(self, proc: ProcId, notes: list[str]) -> None:
        if not self._adopted:
            try:
                self._helper.adopt(proc)
            except HelperError as e:
                if e.code != "not_ours":
                    raise
                # No live process has that pid and start time (win_helper._op_adopt): the game has ended. Part 1's
                # restore still looks for a running game itself.
                self._game_ended = True
                notes.append("the helper finds no live process %d started at %s (%s): the game has ended"
                             % (proc.pid, proc.created, e.detail))
                self._record("kill", outcome="already_exited", detail="adopt: " + _describe(e))
                return
            self._adopted = True
        gone = self._helper.kill(proc)
        self._game_ended = True
        self._record("kill", outcome="already_exited" if gone else "ok")

    def _kill_failed(self, notes: list[str], e: Exception) -> None:
        notes.append("ending the game failed (%s), so it may still be up" % _describe(e))
        self._record("kill", outcome="failed", detail=_describe(e))

    def _new_helper(self) -> None:
        """Swap in a helper from the factory. It remembers no process, so the game is adopted again; the relay was
        the old helper's."""
        old, self._helper = self._helper, self._helper_factory()
        self._adopted = False
        self._relay_open = False
        close = getattr(old, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass                            # it has ended already

    def _await_watch(self, notes: list[str]) -> None:
        if self._watch is None:
            notes.append("no watch was running")
            return
        deadline = self._clock() + WATCH_WAIT_S
        try:
            while self._watch.poll() is None:
                if self._clock() >= deadline:
                    notes.append("watch had not returned %g s after the game was ended" % WATCH_WAIT_S)
                    return
                self._sleep(WATCH_POLL_S)
        except Exception as e:
            notes.append("looking at watch failed: %s" % e)

    def _restore(self, notes: list[str]) -> tuple[dict, str]:
        # launch_in_flight is waited out too: by now the game launch may have started is known ended here.
        retries = {"watch_still_recording": RESTORE_RETRY_TOTAL_S, "busy": BUSY_RETRY_TOTAL_S,
                   "launch_in_flight": LAUNCH_IN_FLIGHT_RETRY_TOTAL_S}
        reply, code = fixture.restore_retried(self._cli, self._snapshot, self._sleep, retries)
        outcome = "held" if reply.get("held") is True else ("restored" if code == 0 else "refused")
        self._record("restore", outcome=outcome, reply=reply)
        return reply, outcome

    def _fixture_verdict(self) -> tuple[dict, str]:
        reply, code = self._verdict
        outcome = "held" if reply.get("held") is True else "restored"
        self._record("restore", outcome=outcome, reply=reply, by="the fixture's run")
        return dict(reply), outcome

    def _settle_overlay(self, restore: dict | None, outcome: str | None, notes: list[str]) -> tuple[bool, str | None]:
        """(removed, why it was kept). The overlay goes only when nothing may still name it."""
        if self._overlay is None:
            return False, None
        kept = self._keep_overlay(restore, outcome)
        if kept is not None:
            return False, kept
        try:
            return overlay.remove(self._paths.overlay_dir), None
        except Exception as e:
            notes.append("removing the overlay failed: %s" % e)
            return False, "removing it failed: %s" % e

    def _keep_overlay(self, restore: dict | None, outcome: str | None) -> str | None:
        """Why the overlay must stay (a running game or a playset may still name it), or None."""
        if self._launched and not self._game_ended:
            return "the game may still be up, and the run's playset names the overlay"
        if restore is None or outcome == "restored":
            return None
        why = _text(restore.get("refused") or restore.get("reason") or "no reason given")
        if outcome == "held":
            if restore.get("playset_restored") is True:
                return None
            if restore.get("playset_left"):
                return "restore held (%s) and left the run's playset, which names the overlay, in place" % why
            return "restore held (%s) without saying the owner's playset is back: it may still name the overlay" % why
        return "restore did not finish (%s): the run's playset may still name the overlay" % why

    def _close_relay(self, notes: list[str]) -> None:
        if not self._relay_open:
            return
        self._relay_open = False
        try:
            self._helper.tcp_close()
        except Exception as e:
            notes.append("closing the debugger's relay failed: %s" % e)

    def _close_helper(self, notes: list[str]) -> None:
        close = getattr(self._helper, "close", None)      # ProcessHelper has one; the protocol does not
        if not callable(close):
            return
        try:
            close()
        except Exception as e:
            notes.append("closing the helper failed: %s" % e)

    def _close_report(self, restore: dict | None, outcome: str | None, removed: bool, kept: str | None,
                      notes: list[str], next_step: str | None = None) -> str | None:
        if self._report is None:
            return None
        try:
            self._record("stop", outcome=outcome or "not_run", overlay_removed=removed, overlay_kept=kept,
                         notes=list(notes))
            path = self._report.close({"restore": restore, "outcome": outcome, "permission": self._permission,
                                       "snapshot": self._snapshot, "save": self._save, "country": self._country,
                                       "overlay_removed": removed, "overlay_kept": kept, "notes": notes,
                                       "next": next_step})
            return str(path)
        except Exception as e:
            notes.append("writing the report failed: %s" % e)
            return None

    # ---- reads and the date

    def _fire_read(self, exprs: list[str]) -> tuple[list[Read], dict]:
        """Release any stop left over, fire the read event, evaluate `exprs` at its breakpoint, let the game run
        on. Only a stop whose reason is "breakpoint" is evaluated at. Once the game may have stopped, a resume is
        always attempted (twice if need be), so no failure leaves it frozen without `_maybe_stopped` saying so."""
        dbg = self._debugger
        self._drain()
        self._new_lines()                       # a date line from before is not this read's
        try:
            self._console.send(READ_COMMAND)
        except ConsoleError as e:
            if e.entered is not False:          # it may have run: release a stop rather than leave the game in it
                self._release(dbg)
            raise
        try:
            stopped = dbg.wait_stopped(STOP_WAIT_S)
        except DebuggerError as e:
            self._maybe_stopped = True
            raise SessionError("debugger", str(e), maybe_stopped=True) from e
        if not stopped:
            self._resume(dbg)                   # a stop may come late: a resume answered "not stopped" does no harm
            self._maybe_stopped = True          # and it may come later still: the next verb releases it first
            raise SessionError("no_stop", "the game did not stop at the read event within %g s" % STOP_WAIT_S,
                               arrived=self._console.arrived(READ_COMMAND), maybe_stopped=True)
        reason = dbg.last_stop_reason
        if reason != "breakpoint":
            self._resume(dbg)
            self._maybe_stopped = True          # the read's own stop may still come
            raise SessionError("unexpected_stop", "the game stopped for %r, not at the read event's breakpoint, so "
                               "nothing was evaluated; it was resumed" % (reason,), reason=reason, maybe_stopped=True)
        # Streamed before the stop: error-log lines of the game's own (the debugger streams every one), which the
        # log follower yields too. From the stop to the resume the game is frozen, so what streams then is the
        # validator burst the evaluations cause.
        stray = dbg.errors()
        reads: list[Read] = []
        failure: DebuggerError | None = None
        resumed = False
        try:
            for expr in exprs:
                got = dbg.evaluate(expr)
                reads.append(Read(expr, got.ok, got.raw, got.value))
        except DebuggerError as e:
            failure = e
        finally:
            resumed = self._resume(dbg)
            self._maybe_stopped = not resumed
        if failure is not None:
            raise SessionError("debugger", str(failure), maybe_stopped=not resumed) from failure
        if not resumed:
            raise SessionError("debugger", "the reads were made, but the game did not take the resume, twice: it may "
                               "still be stopped at the breakpoint", maybe_stopped=True,
                               reads=[asdict(r) for r in reads])
        burst = dbg.errors()
        if self._burst is not None:
            self._burst.extend(burst)
        # The stop proved the command ran; a history that did not gain it (it skips a repeat) is only noted.
        return reads, {"arrived": self._console.arrived(READ_COMMAND), "debugger_errors": len(stray) + len(burst)}

    def _drain(self) -> None:
        """Release a stop left over from an earlier read before anything is typed (a frozen game takes no key).
        With `_maybe_stopped` set (a resume that may not have reached the game, a stop that may come late) a
        resume is sent whether or not a stop is seen; answered "not stopped", the game is running."""
        dbg = self._debugger
        try:
            stopped = dbg.wait_stopped(DRAIN_S)
        except DebuggerError as e:
            self._maybe_stopped = True
            raise SessionError("debugger", "%s (looking for a stop left over from an earlier read; nothing was "
                               "typed)" % e, maybe_stopped=True) from e
        if (stopped or self._maybe_stopped) and not self._resume(dbg):
            self._maybe_stopped = True
            raise SessionError("maybe_stopped", "the game may be stopped at the read event's breakpoint, and did not "
                               "take a resume, twice: nothing was typed", maybe_stopped=True)
        self._maybe_stopped = False

    @staticmethod
    def _resume(dbg: Debugger) -> bool:
        """Let the game run on; True once it is known to run: it took the resume, or answered that it was not
        stopped. A resume that may not have reached it is tried once more."""
        for _ in range(2):
            try:
                dbg.resume()
                return True
            except DebuggerError as e:
                if str(e).startswith("continue refused"):      # the game's own answer (dap's `_must`)
                    return True
        return False

    def _release(self, dbg: Debugger) -> None:
        """After a read command that may have been entered: release its stop, or leave the next verb to."""
        try:
            stopped = dbg.wait_stopped(STOP_WAIT_S)
        except DebuggerError:
            stopped = False
        if stopped and self._resume(dbg):
            return
        self._maybe_stopped = True

    def _date(self) -> tuple[int, int, int]:
        """The game's date, from the read event's line, which its padding flushes once the game is resumed."""
        self._fire_read([])
        deadline = self._clock() + DATE_WAIT_S
        while True:
            when = self._date_in(self._new_lines())
            if when is not None:
                return when
            if self._clock() >= deadline:
                raise SessionError("no_date", "no %r line in the log within %g s of the resume"
                                   % (READ_PREFIX.strip(), DATE_WAIT_S))
            self._sleep(LOG_POLL_S)

    @staticmethod
    def _date_in(lines: list[str]) -> tuple[int, int, int] | None:
        for line in lines:
            parsed = parse(line)
            if parsed.kind == "debug_log" and parsed.text.startswith(READ_PREFIX):
                when = overlay.parse_date(parsed.text)
                if when is not None:
                    return when
        return None

    def _new_lines(self) -> list[str]:
        """The debug.log lines since the last call; both logs' new lines are copied into the run folder."""
        lines = self._debug_log.poll()
        self._copy("debug.log", lines)
        errors = self._error_log.poll()
        self._copy("error.log", errors)
        if self._errors_seen is not None:
            self._errors_seen.extend(errors)
        return lines

    def _copy(self, name: str, lines: list[str]) -> None:
        if not lines or self._report is None:
            return
        try:
            with open(self._report.dir / name, "a", encoding="utf-8") as f:
                f.write("".join(line + "\n" for line in lines))
        except OSError:
            pass                                # the copy is a convenience; the game's own logs go to run_logs/

    def _setup_lines(self, name: str) -> list[str]:
        start, done = "TE_QA setup %s start" % name, "TE_QA setup %s done" % name
        seen: list[tuple[str, str]] = []        # (kind, text) of each line since the command
        deadline = self._clock() + SETUP_WAIT_S
        while True:
            for line in self._new_lines():
                parsed = parse(line)
                seen.append((parsed.kind, line if line == GAP_MARKER else parsed.text))
            ends = [i for i, (kind, text) in enumerate(seen) if kind == "debug_log" and text == done]
            if ends:
                begins = [i for i, (kind, text) in enumerate(seen[:ends[-1]]) if kind == "debug_log" and text == start]
                if not begins:
                    raise SessionError("setup_not_logged", "setup %s logged its done marker but its start was lost"
                                       % name)
                return [text for _kind, text in seen[begins[-1] + 1:ends[-1]]]
            if self._clock() >= deadline:
                raise SessionError("setup_not_logged", "setup %s logged no done marker within %g s"
                                   % (name, SETUP_WAIT_S))
            self._sleep(LOG_POLL_S)

    def _pending(self) -> list[Pending]:
        reply = self._console.run(PENDING_COMMAND)
        found = pending_events(reply.lines)
        if not found and NO_PENDING not in [line.strip() for line in reply.lines]:
            raise SessionError("bad_reply", "%r answered %r" % (PENDING_COMMAND, reply.lines))
        return found

    def _tag(self, tag: str) -> None:
        _check_tag(tag)
        reply = self._console.run("tag " + tag)
        if not any(line.startswith("Now Playing") for line in reply.lines):
            raise SessionError("tag_failed", "tag %s answered %r" % (tag, reply.lines))
        self._country = tag

    # ---- entering the game, and time

    def _enter(self) -> dict:
        if self._entered:
            return {"entered": True, "already": True}
        if self._country is None:
            raise SessionError("no_country", "tag a country first: the click selects the one the camera is on")
        clicks: list[list[int]] = []
        for where, settle in ((COUNTRY_CLICK, CLICK_SETTLE_S), (START_CLICK, ENTER_SETTLE_S)):
            # The console's own front check, so the presence rule decides whether the foreground may be taken.
            self._console.ensure_open()
            x, y = self._point(where)
            try:
                self._sends.click(self._proc.pid, x, y)
            except HelperError as e:        # refused before the button went down: nothing was pressed
                raise SessionError("click_refused", "%s: %s" % (e.code, e.detail), clicks=clicks) from e
            clicks.append([x, y])
            self._sleep(settle)
        try:
            before = self._date()
        except Exception as e:
            # Start may have been pressed: the game may be entered, and running. Nothing is clicked again.
            self._left_running = True
            raise SessionError("not_entered", "the clicks went out but the date could not be read after them (%s): "
                               "the game may be entered and running unpaused; enter_game and advance are refused "
                               "until stop" % _describe(e), clicks=clicks) from e
        after = self._run_for(PROOF_S)
        if _game_day(after) <= _game_day(before):
            try:
                shot = str(self._shot())
            except Exception as e:
                shot = "the screenshot failed: %s" % e
            raise SessionError("not_entered", "the date stayed at %s while unpaused for %g s" % (before, PROOF_S),
                               screenshot=shot, before=before, after=after, clicks=clicks)
        self._entered = True
        return {"entered": True, "clicks": clicks, "before": before, "after": after}

    def _point(self, fraction: tuple[float, float]) -> tuple[int, int]:
        """A point of the client area, in client pixels, from fractions of its width and height."""
        _left, _top, width, height = self._helper.window(self._proc.pid).client
        if width <= 0 or height <= 0:
            raise SessionError("no_window", "the game's window has no client area to click")
        return min(round(width * fraction[0]), width - 1), min(round(height * fraction[1]), height - 1)

    def _run_for(self, seconds: float) -> tuple[int, int, int]:
        """Close the console, unpause, wait, pause, reopen the console, and prove the pause: two date reads
        PROOF_PAUSE_S apart must agree. If they do not, the pause key goes once more and the pause is proved again.
        From the first key on, any failure is `left_running`, as is a date still moving after the second pause
        key; the flag then refuses `enter_game` and `advance` until `stop`. Return the date the game paused at."""
        self._console.close()
        try:
            self._console.hotkey(SCAN_SPACE)
            self._sleep(seconds)
            self._console.hotkey(SCAN_SPACE)
            self._console.ensure_open()
            when = self._paused_date()
            if when is None:                # the pause did not take: once more
                self._console.close()
                self._console.hotkey(SCAN_SPACE)
                self._console.ensure_open()
                when = self._paused_date()
            if when is None:
                raise SessionError("left_running", "the date still moved after a second pause key: the game is "
                                   "running unpaused")
            return when
        except BaseException as e:
            self._left_running = True
            if not isinstance(e, Exception) or (isinstance(e, SessionError) and e.code == "left_running"):
                raise
            extra = {"entered": e.entered} if isinstance(e, ConsoleError) else {}
            raise SessionError("left_running", "a round failed once its first pause key had been tried (%s): the "
                               "game may be running unpaused; enter_game and advance are refused until stop"
                               % _describe(e), cause=_code_of(e), **extra) from e

    def _paused_date(self) -> tuple[int, int, int] | None:
        """The date, if two reads PROOF_PAUSE_S apart agree on it (the game is paused); else None."""
        first = self._date()
        self._sleep(PROOF_PAUSE_S)
        second = self._date()
        return second if second == first else None

    def _refuse_if_left_running(self) -> None:
        if self._left_running:
            raise SessionError("left_running", "an earlier round may have left the game running unpaused, so no more "
                               "time is let pass and nothing is clicked: stop the session")

    def _advance(self, days: int, start: tuple[int, int, int] | None, out: dict) -> tuple[int, int, int]:
        start = start or self._date()
        rate, waited = FIRST_RATE, 0.0
        current = start
        for round_no in range(1, MAX_ROUNDS + 1):
            missing = days - (_game_day(current) - _game_day(start))
            wait = min(max(missing / rate, MIN_WAIT_S), MAX_WAIT_S)
            current = self._run_for(wait)
            waited += wait
            passed = _game_day(current) - _game_day(start)
            out.update(start=start, reached=current, passed=passed, rounds=round_no)
            if passed >= days:
                return current
            if passed > 0:
                rate = passed / waited
        raise SessionError("stalled", "%d of %d days passed in %d rounds" % (passed, days, MAX_ROUNDS),
                           start=start, reached=current)

    def _shot(self) -> Path:
        self._shots += 1
        return self._helper.screenshot(self._proc.pid, self._report.dir / ("shot_%02d.png" % self._shots))

    # ---- plumbing

    def _require_game(self, types: bool = True) -> None:
        """Before any verb: the session is running and watched, and the game is not left stopped at the
        breakpoint. When it may be (`_maybe_stopped`) the stop is drained first; otherwise a verb that `types`
        (or clicks) still takes one look, without waiting, for a stop the game made since the last verb (a read's
        own command run once the game was resumed) and releases it: a frozen game takes no key, and the keys
        would run later."""
        if self._stopped is not None or self._stopping:
            raise SessionError("stopped", "this session's game has been stopped")
        if not self._ready:
            raise SessionError("not_started", "start() has not finished")
        self._check_watch()
        if self._maybe_stopped:
            self._drain()
        elif types:
            self._release_pending()

    def _release_pending(self) -> None:
        dbg = self._debugger
        try:
            stopped = dbg.poll_stopped()
        except DebuggerError as e:
            self._maybe_stopped = True
            raise SessionError("debugger", "%s (looking for a stop left pending; nothing was typed)" % e,
                               maybe_stopped=True) from e
        if stopped and not self._resume(dbg):
            self._maybe_stopped = True
            raise SessionError("maybe_stopped", "the game is stopped at the read event's breakpoint, and did not take "
                               "a resume, twice: nothing was typed", maybe_stopped=True)

    def _prove_game(self) -> None:
        """Just before each key, focus or click, inside a verb as between them: `watch` has not recorded the game's
        exit (`_check_watch`), and the helper proves the process is the game by its pid and start time (`adopt`,
        win_helper._op_adopt). Any doubt latches `watch_ended`, so nothing more goes out in any verb, and is
        raised before the send."""
        self._check_watch()
        try:
            self._helper.adopt(self._proc)
        except Exception as e:
            self._watch_ended = ("the game could not be proved alive by its pid and start time before a key or click "
                                 "(%s): stop the session" % _describe(e))
            raise SessionError("watch_ended", self._watch_ended) from e

    def _check_watch(self) -> None:
        """`watch` must still be following the game before any key or click goes out.

        A watch that returned 0 recorded the game's exit: the verbs end (`watch_ended`), for good, whatever
        window now has the game's pid. One that returned anything else stopped without recording an exit (a
        failed look, a journal it could not write): it is run again at once (up to WATCH_RESPAWNS times), and
        noted, but only once the helper has proved the game alive by its pid and start time (`adopt` compares
        the creation time, win_helper._op_adopt). Any doubt there (refused `not_ours`, a helper error) ends the
        verbs for good too: a pid alone may be another program's by now."""
        if self._watch_ended is not None:
            raise SessionError("watch_ended", self._watch_ended)
        code = self._watch.poll() if self._watch is not None else None
        if code is None:
            return
        why = None
        if code == 0:
            why = "`watch` has recorded the game's exit: the game has ended. Stop the session"
        elif self._watch_respawns >= WATCH_RESPAWNS:
            why = ("`watch` stopped (exit %s) without recording an exit, %d times now: stop the session"
                   % (code, self._watch_respawns + 1))
        else:
            try:
                self._helper.adopt(self._proc)
            except Exception as e:
                why = ("`watch` stopped (exit %s) without recording an exit, and the game could not be proved alive "
                       "by its pid and start time (%s): stop the session" % (code, _describe(e)))
        if why is None:
            try:
                self._watch = self._spawn_watch(self._snapshot)
            except Exception as e:
                why = "`watch` stopped (exit %s) and could not be run again (%s): stop the session" % (code, e)
        if why is not None:
            self._watch_ended = why
            raise SessionError("watch_ended", why)
        self._watch_respawns += 1
        self._notes.append("watch returned at %s while the game's window was still up, and was run again at once"
                           % stamp(utc_now()))
        self._record("watch_respawned", outcome="ok", respawns=self._watch_respawns)

    def _cli(self, argv: list[str]) -> tuple[dict, int]:
        reply, code = self._run_cli(list(argv))
        if not isinstance(reply, dict):
            return {"refused": "bad_reply", "detail": repr(reply)[:300]}, 2
        return reply, code

    def _open_report(self, snap: str) -> None:
        self._report = Report(self._paths.run_root / snap)
        early, self._early = self._early, []
        for verb, fields in early:
            self._record(verb, **fields)

    def _record(self, verb: str, **fields) -> None:
        if self._report is None:
            self._early.append((verb, dict(fields, time=stamp(utc_now()))))
            return
        try:
            self._report.step(verb, **fields)
        except OSError:
            pass

    @contextmanager
    def _step(self, verb: str, **fields):
        """Record one verb: the block fills `out`; an error is recorded with its code, then raised."""
        out = dict(fields)
        try:
            yield out
        except Exception as e:
            extra = {"entered": e.entered} if isinstance(e, ConsoleError) else {}
            self._record(verb, **{**out, "outcome": _code_of(e), "detail": str(e), **extra})
            raise
        outcome = out.pop("outcome", "ok")
        self._record(verb, **{"outcome": outcome, **out})

    def _watch_returned(self) -> bool:
        return self._watch is not None and self._watch.poll() is not None


def _names_event(text: str, event: str) -> bool:
    """Whether `text` names `event` as a whole id: x.1 is not named by x.17, x.1.2 or y.x.1 (a full stop after
    it, ending a sentence, still names it)."""
    return re.search(r"(?<![\w.])%s(?!\w|\.\w)" % re.escape(event), text) is not None


def _new_errors(lines: list[str], burst: list[str]) -> list[str]:
    """`lines` (error.log's) less blank ones and those whose message the debugger reported in `burst`. A burst
    line is the bare message; the log's first line of an entry carries a `[time][file.cpp:n]: ` prefix."""
    own = {piece.strip() for text in burst for piece in text.split("\n")} - {""}
    return [line for line in lines if line.strip() and parse(line).text.strip() not in own]


def run_playset(mode: str, owner_mods: Sequence[str], deployed_mod: str, overlay_path: str) -> list[str]:
    """The mod folders a run loads, in order, as `launch --playset <mode> --add-mod <overlay_path>` writes them
    (game_qa/__main__.py `_plan_playset`, which cannot be imported from here): the owner's enabled mods (with
    mod_only, only those at the deployed mod's folder), then the overlay unless it is among them already.
    Folders are compared as launch compares them (`_folder_key`)."""
    kept = [m for m in owner_mods if mode != "mod_only" or _folder_key(m) == _folder_key(deployed_mod)]
    if all(_folder_key(m) != _folder_key(overlay_path) for m in kept):
        kept.append(overlay_path)
    return kept


def _folder_key(path: str) -> str:
    """A Windows folder path as `launch` compares it (__main__._folder_key): in any case, with either separator,
    with or without a trailing one."""
    return path.replace("/", "\\").rstrip("\\").lower()


def _fixture_snapshot(calls: list[tuple[str, dict | None, int | None]]) -> str | None:
    """The snapshot the fixture's run took, from its `snapshot` call's reply, or None."""
    for verb, reply, code in calls:
        if verb == "snapshot" and code == 0 and isinstance(reply, dict) and isinstance(reply.get("id"), str):
            return reply["id"] or None
    return None


def _reply_lost(reply: dict | None, code: int | None) -> bool:
    """Whether a `snapshot` reply was lost or unreadable, so that a snapshot may have been taken (and armed) all
    the same: the call raised, or printed no JSON object, or said 0 without an id."""
    if not isinstance(reply, dict) or reply.get("refused") == "bad_reply":
        return True
    return code == 0 and not reply.get("id")


def _describe(e: BaseException) -> str:
    """An error as `code: detail`, its code said once."""
    if isinstance(e, HelperError):
        return "helper: %s" % e
    if isinstance(e, (SessionError, ConsoleError)):
        return str(e)
    return "%s: %s" % (_code_of(e), e)


def _text(value) -> str:
    return " ".join(str(value).split())


def _check_tag(tag: str) -> None:
    if not isinstance(tag, str) or _TAG.fullmatch(tag) is None:
        raise SessionError("bad_tag", "a country tag is letters, digits and _, such as FRA, not %r" % (tag,))


def _named_proc(reply: dict) -> ProcId | None:
    try:
        return ProcId(int(reply["pid"]), str(reply["created"]))
    except (KeyError, TypeError, ValueError):
        return None


def _proc_of(reply: dict) -> ProcId:
    proc = _named_proc(reply)
    if proc is None:
        raise SessionError("bad_launch_reply", "launch's reply names no process: %r" % (reply,))
    if proc.created == UNKNOWN_START:
        raise SessionError("unknown_start", "launch could not read the game's start time, so the helper cannot "
                           "adopt it and watch refuses it")
    return proc


def _game_day(when: tuple[int, int, int]) -> int:
    """A day number on the game's calendar: 365 days a year, no leap day (scripting_best_practices.md, monthly
    pulse). A 29 February, which the game never shows, counts as 1 March, so a count never runs ahead of the game."""
    year, month, day = when
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        raise SessionError("bad_date", "%r is not a date" % (when,))
    return year * 365 + _DAYS_BEFORE[month - 1] + day


def _code_of(e: BaseException) -> str:
    if isinstance(e, SessionError):
        return e.code
    if isinstance(e, ConsoleError):
        return e.code
    if isinstance(e, DebuggerError):
        return "debugger"
    if isinstance(e, HelperError):
        return "helper: " + e.code
    if isinstance(e, subprocess.SubprocessError):
        return "subprocess"
    return type(e).__name__


def _why(reply: dict) -> str:
    for field in ("refused", "reason", "error"):
        if reply.get(field):
            detail = reply.get("detail")
            return "%s (%s)" % (reply[field], detail) if detail else str(reply[field])
    return repr(reply)[:300]
