"""One game's life: start it on the deployed build, drive it, and stop it with the owner's files put back.

The session never touches the owner's files itself. The protective verbs of part 1 do, and only through the
`run_cli` it is given (`python3 -m game_qa <argv>`, returning its JSON reply and exit code): `held`, `snapshot`,
`launch`, `restore`, and `watch` as the subprocess `spawn_watch` starts. A refusal or a hold from any of them is
reported, never worked around. Under the user-data folder the session itself writes only the overlay mod
(`overlay.build` and `overlay.remove`) and, through `fixture`, the `te_qa_fixture_*` saves.

    start   held?  overlay  fixture  snapshot  launch  watch at once  adopt  window  logs  console  tag  debugger
    stop    kill  wait for watch  restore  overlay.remove  close the relay and the helper  close the report

Keys and clicks go out only through `Console` and the helper, which check that the game is in front; a click
is preceded by a console call that needs the game in front, so the presence rule decides whether the foreground
may be taken, never a bare `focus`. A console command is typed once: nothing here types one again after an error.

Reads go through the overlay's read event (`overlay.READ_EVENT`): console `event te_qa.1` runs its `immediate`
at once, the debugger stops on its `debug_log` line, and each expression is evaluated there; once resumed, the
event logs `TE_QA read country=FRA date=January 11, 1836` and its padding flushes the log. That line is how the
session reads the date (`enter_game`, `advance`). Facts from the live session of 2026-11-10 (spec § 12): the
fixture opens on the country-select screen, where time does not advance; after `tag` the camera is on that
country, and a click at COUNTRY_CLICK then START_CLICK (fractions of the client area) enters the game; the game
is paused when a save loads, and space toggles the pause only with the console closed.
"""
from __future__ import annotations

import re
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from game_qa import fixture, overlay
from game_qa.console import Console, ConsoleError, Reply
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
RESTORE_RETRY_S = 5.0                   # stop: while `restore` refuses watch_still_recording
RESTORE_RETRY_TOTAL_S = 30.0

_TAG = re.compile(r"[A-Za-z0-9_]{1,16}")
_DAYS_BEFORE = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


class SessionError(Exception):
    """A verb that did not go through. `code` names why; `info` holds what goes with it (`reply`: a protective
    verb's reply; `stop`: the reply of the `stop` a failed start ran; `screenshot`, …).

    Codes: already_started, no_permission, bad_argument, bad_tag, no_save, held_snapshot, held_unknown,
    overlay_refused, fixture_failed, snapshot_refused, launch_refused, bad_launch_reply, unknown_start, game_gone,
    no_window, breakpoint_unverified, debugger, no_stop, no_date, bad_date, tag_failed, use_read, unknown_setup,
    setup_not_logged, bad_reply, nothing_pending, bad_index, not_selected, no_country, click_refused, not_entered,
    left_running, bad_days, stalled, not_started, stopped, watch_ended; after `launch`, a console error that ended
    `start` keeps its own code (no_ack, not_foreground, …) and `entered`."""

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
    enabled_mods: Sequence[str]                     # the run's playset, in order: part of the fixture's key

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


class Session:
    def __init__(self, helper: Helper, run_cli: RunCli, spawn_watch: Callable[[str], Any], paths: Paths,
                 sleep=time.sleep, clock=time.monotonic) -> None:
        self._helper, self._run_cli, self._spawn_watch, self._paths = helper, run_cli, spawn_watch, paths
        self._sleep, self._clock = sleep, clock
        self._began = False                 # start() was called
        self._ready = False                 # start() finished: the other verbs may run
        self._permission: str | None = None
        self._overlay: overlay.Overlay | None = None     # built by this session, so stop removes it
        self._save: str | None = None
        self._snapshot: str | None = None
        self._report: Report | None = None
        self._early: list[tuple[str, dict]] = []         # steps from before the run folder existed
        self._launched = False              # `launch` succeeded: a game of this run may be up
        self._launch_reply: dict = {}
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

    # ---- start

    def start(self, permission: str, as_tag: str | None = None, setups: Mapping[str, str] | None = None,
              save: str | None = None, playset: str = "mod_only", owner_confirmed_busy: bool = False) -> dict:
        """Get a game up on the fixture (made first if missing) or on `save`, played as `as_tag`.

        Refused with nothing done, and the session left as it was: an empty permission, a bad argument, a save
        that is not there, and any held snapshot (only the owner resolves a hold, and a hold leaves the run's
        playset in place). A second start, or one after `stop`, is refused. A refused snapshot or launch raises with
        the verb's reply and starts nothing further. Every failure once the overlay is built runs `stop()` before
        raising (its reply is the error's `info["stop"]`)."""
        if self._began or self._stopped is not None:
            raise SessionError("already_started", "a session runs one game: stop it and start a new session")
        if not isinstance(permission, str) or not permission.strip():
            raise SessionError("no_permission", "say where the go-ahead to launch came from")
        if playset not in PLAYSETS:
            raise SessionError("bad_argument", "playset is one of %s, not %r" % (", ".join(PLAYSETS), playset))
        if as_tag is not None:
            _check_tag(as_tag)
        if save is not None:
            save = self._check_save(save)
        self._refuse_if_held()
        self._began = True
        self._permission = permission
        try:
            self._overlay = overlay.build(self._paths.overlay_dir, dict(setups or {}), self._paths.game_version)
        except overlay.OverlayError as e:
            raise SessionError("overlay_refused", str(e)) from e
        self._record("overlay", outcome="built", setups=sorted(self._overlay.setup_events))
        try:
            return self._start(permission, as_tag, save, playset, owner_confirmed_busy)
        except Exception as e:
            stopped = self.stop()
            if isinstance(e, SessionError):
                e.info["stop"] = stopped
                raise
            extra = {"entered": e.entered} if isinstance(e, ConsoleError) else {}
            raise SessionError(_code_of(e), str(e), stop=stopped, **extra) from e

    def _start(self, permission: str, as_tag: str | None, save: str | None, playset: str, busy: bool) -> dict:
        save, made, pruned = self._the_save(save, permission, playset, busy)
        self._save = save
        reply, code = self._cli(["snapshot", "--save", save])
        snap = reply.get("id")
        if code != 0 or not isinstance(snap, str) or not snap:
            self._record("snapshot", outcome="refused", reply=reply)
            raise SessionError("snapshot_refused", _why(reply), reply=reply)
        self._snapshot = snap
        self._open_report(snap)
        self._record("snapshot", outcome="ok", reply=reply)

        argv = ["launch", snap, "--permission", permission, "--playset", playset,
                "--add-mod", self._paths.overlay_windows_path]
        if busy:
            argv.append("--owner-confirmed-busy")
        argv += ["--", *SESSION_ARGS, "-loadsave=" + save]
        reply, code = self._cli(argv)
        if code != 0:
            self._record("launch", outcome="refused", reply=reply)
            raise SessionError("launch_refused", _why(reply), reply=reply)
        self._launched = True
        self._launch_reply = reply
        # At once: part 1 holds a run whose first look came more than 120 s after the start.
        self._watch = self._spawn_watch(snap)
        self._record("launch", outcome="ok", reply=reply)
        self._proc = _proc_of(reply)
        self._helper.adopt(self._proc)
        self._adopted = True
        self._await_window()

        self._debug_log = LogFollower(self._paths.logs / "debug.log")
        self._error_log = LogFollower(self._paths.logs / "error.log")
        self._console = Console(self._helper, self._proc, self._paths.history,
                                LogFollower(self._paths.logs / "debug.log"), sleep=self._sleep, clock=self._clock)
        with self._step("console_ready"):
            self._console.ensure_open(CONSOLE_READY_S)
        if as_tag is not None:
            with self._step("tag", tag=as_tag):
                self._tag(as_tag)
        self._attach()
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
        user = Path(self._paths.user_data)
        key = fixture.key(self._paths.game_version, self._paths.enabled_mods, self._paths.deploy_dir)
        found = fixture.find(user, key)
        if found is not None:
            self._record("fixture", outcome="found", save=found.stem)
            return found.stem, False, []
        try:
            made = fixture.make(self._run_cli, user, key, self._paths.overlay_windows_path, permission, playset,
                                owner_confirmed_busy=busy, sleep=self._sleep)
        except fixture.FixtureError as e:
            self._record("fixture", outcome="failed", step=e.step, reply=e.reply, snapshot=e.snapshot)
            raise SessionError("fixture_failed", str(e), step=e.step, reply=e.reply, snapshot=e.snapshot) from e
        try:
            pruned = fixture.prune(user, keep=FIXTURES_KEPT)
        except OSError as e:
            pruned = []
            self._record("fixture_prune", outcome="failed", detail=str(e))
        self._record("fixture", outcome="made", save=made.stem, pruned=pruned)
        return made.stem, True, pruned

    def _await_window(self) -> None:
        deadline = self._clock() + WINDOW_WAIT_S
        while True:
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
        """One console command, with its reply. The read event is refused: it would stop at the breakpoint with
        nobody to resume it (`read` is its verb)."""
        self._require_game()
        with self._step("console", text=text) as out:
            if text.split() == ["event", overlay.READ_EVENT]:
                raise SessionError("use_read", "%r stops at the debugger's breakpoint: use read" % text)
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
        """Click the country the camera is on, then Start, and prove it by the date moving while unpaused."""
        self._require_game()
        with self._step("enter_game") as out:
            result = self._enter()
            out.update(result)
        return result

    def advance(self, days: int) -> tuple[int, int, int]:
        """Let at least `days` game days pass (entering the game first if need be); return the date reached."""
        self._require_game()
        if isinstance(days, bool) or not isinstance(days, int) or days < 1:
            raise SessionError("bad_days", "days is a whole number of at least 1, not %r" % (days,))
        if not self._entered:
            start = tuple(self.enter_game()["after"])
        else:
            start = None
        with self._step("advance", days=days) as out:
            reached = self._advance(days, start, out)
        return reached

    def shot(self) -> Path:
        self._require_game()
        with self._step("shot") as out:
            path = self._shot()
            out["path"] = str(path)
        return path

    # ---- stop

    def stop(self) -> dict:
        """End the game this session started and put the owner's files back; never raises.

        In order: end the game (`kill`; adopted first if a failure came before `adopt`), wait for `watch` to
        return (up to WATCH_WAIT_S), `restore <id>` (retried while it refuses watch_still_recording, up to
        RESTORE_RETRY_TOTAL_S), remove the overlay this session built, close the debugger's relay and the helper,
        close the report. With no launch, a snapshot taken is still restored: an armed one blocks every later one.
        The reply is restore's reply plus `outcome` (restored, held or refused), `snapshot`, `overlay_removed`,
        `report` (the summary's path) and any `notes`; a second call returns the first one's reply."""
        if self._stopped is None:
            try:
                self._stopped = self._stop()
            except Exception as e:      # a backstop: each stage below already catches its own failures
                self._stopped = {"snapshot": self._snapshot, "outcome": "error", "notes": ["stop failed: %r" % e]}
        return self._stopped

    def _stop(self) -> dict:
        notes: list[str] = []
        if self._launched:
            self._end_game(notes)
            self._await_watch(notes)
        restore, outcome = self._restore(notes) if self._snapshot is not None else (None, None)
        removed = self._remove_overlay(notes)
        self._close_relay(notes)
        self._close_helper(notes)
        reply = dict(restore) if restore is not None else {}
        reply.update(outcome=outcome, snapshot=self._snapshot, overlay_removed=removed)
        reply["report"] = self._close_report(restore, outcome, removed, notes)
        if notes:
            reply["notes"] = notes
        return reply

    def _end_game(self, notes: list[str]) -> None:
        # `launch`'s own record of the game, if the failure came before it was taken as `_proc`: the helper
        # adopts a process only when its creation time matches, so a wrong or unknown time ends nothing.
        proc = self._proc or _named_proc(self._launch_reply)
        if proc is None:
            notes.append("the game's process is not known (launch's reply did not name it), so it was not ended")
            return
        if not self._adopted:
            try:
                self._helper.adopt(proc)
                self._adopted = True
            except Exception as e:
                notes.append("adopting the game before ending it failed: %s" % e)
        try:
            gone = self._helper.kill(proc)
            self._record("kill", outcome="already_exited" if gone else "ok")
        except Exception as e:
            notes.append("ending the game failed: %s" % e)
            self._record("kill", outcome="failed", detail=str(e))

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
        waited = 0.0
        while True:
            try:
                reply, code = self._cli(["restore", self._snapshot])
            except Exception as e:
                reply, code = {"held": False, "refused": "error", "detail": "restore could not be run: %r" % e}, 2
            if code == 0 or reply.get("refused") != "watch_still_recording" or waited >= RESTORE_RETRY_TOTAL_S:
                break
            self._sleep(RESTORE_RETRY_S)
            waited += RESTORE_RETRY_S
        outcome = "held" if reply.get("held") is True else ("restored" if code == 0 else "refused")
        self._record("restore", outcome=outcome, reply=reply)
        return reply, outcome

    def _remove_overlay(self, notes: list[str]) -> bool:
        if self._overlay is None:
            return False
        try:
            return overlay.remove(self._paths.overlay_dir)
        except Exception as e:
            notes.append("removing the overlay failed: %s" % e)
            return False

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

    def _close_report(self, restore: dict | None, outcome: str | None, removed: bool, notes: list[str]) -> str | None:
        if self._report is None:
            return None
        try:
            self._record("stop", outcome=outcome or "not_run", overlay_removed=removed, notes=list(notes))
            path = self._report.close({"restore": restore, "outcome": outcome, "permission": self._permission,
                                       "snapshot": self._snapshot, "save": self._save, "country": self._country,
                                       "overlay_removed": removed, "notes": notes})
            return str(path)
        except Exception as e:
            notes.append("writing the report failed: %s" % e)
            return None

    # ---- reads and the date

    def _fire_read(self, exprs: list[str]) -> tuple[list[Read], dict]:
        """Fire the read event, evaluate `exprs` at its breakpoint, let the game run on. Once the game has
        stopped, a resume is always attempted, so no failure leaves it frozen at the breakpoint."""
        dbg = self._debugger
        self._new_lines()                       # a date line from before is not this read's
        try:
            self._console.send(READ_COMMAND)
        except ConsoleError as e:
            if e.entered is not False:          # it may have run: release a stop rather than leave the game in it
                self._release(dbg)
            raise
        owed = False                            # stopped and not yet resumed
        try:
            if not dbg.wait_stopped(STOP_WAIT_S):
                self._try_resume(dbg)           # a stop may come late: a refused resume does no harm
                raise SessionError("no_stop", "the game did not stop at the read event within %g s" % STOP_WAIT_S,
                                   arrived=self._console.arrived(READ_COMMAND))
            owed = True
            reads = []
            for expr in exprs:
                got = dbg.evaluate(expr)
                reads.append(Read(expr, got.ok, got.raw, got.value))
            owed = False
            dbg.resume()
            errors = dbg.errors()
        except DebuggerError as e:
            raise SessionError("debugger", str(e)) from e
        finally:
            if owed:
                self._try_resume(dbg)
        # The stop proved the command ran; a history that did not gain it (it skips a repeat) is only noted.
        return reads, {"arrived": self._console.arrived(READ_COMMAND), "debugger_errors": len(errors)}

    @staticmethod
    def _try_resume(dbg: Debugger) -> None:
        try:
            dbg.resume()
        except DebuggerError:
            pass

    def _release(self, dbg: Debugger) -> None:
        try:
            if dbg.wait_stopped(STOP_WAIT_S):
                dbg.resume()
        except DebuggerError:
            pass

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
        self._copy("error.log", self._error_log.poll())
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
                self._helper.click(self._proc.pid, x, y)
            except HelperError as e:        # refused before the button went down: nothing was pressed
                raise SessionError("click_refused", "%s: %s" % (e.code, e.detail), clicks=clicks) from e
            clicks.append([x, y])
            self._sleep(settle)
        before = self._date()
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
        """Close the console, unpause, wait, pause, reopen the console; return the date then."""
        self._console.close()
        self._console.hotkey(SCAN_SPACE)
        self._sleep(seconds)
        try:
            self._console.hotkey(SCAN_SPACE)
        except ConsoleError as e:
            raise SessionError("left_running", "the pause key did not go out (%s): the game is running"
                               % e.code, console=e.code) from e
        self._console.ensure_open()
        return self._date()

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

    def _require_game(self) -> None:
        if self._stopped is not None:
            raise SessionError("stopped", "this session's game has been stopped")
        if not self._ready:
            raise SessionError("not_started", "start() has not finished")
        if self._watch is not None and self._watch.poll() is not None:
            raise SessionError("watch_ended", "`watch` has returned, so the game has ended (or watch failed): stop")

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
        if self._stopped is not None:
            return
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
