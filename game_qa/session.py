"""One game's life: start it on the deployed build, drive it, and stop it with the owner's files put back.

The session never touches the owner's files itself. The protective verbs of part 1 do, and only through the
`run_cli` it is given (`python3 -m game_qa <argv>`, returning its JSON reply and exit code): `held`, `snapshot`,
`launch`, `restore`, and `watch` as the subprocess `spawn_watch` starts. A refusal or a hold from any of them is
reported, never worked around. Under the user-data folder the session itself writes only the overlay mod
(`overlay.build` and `overlay.remove`) and, through `fixture`, the `te_qa_fixture_*` saves. Under the backup root
it writes the run's folder and, through `selfchecks`, the lines kept with a fixture (`fixtures/<key>/`).

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
2026-11-10 (spec § 12): the fixture opens on the country-select screen, where time does not advance; a click at
COUNTRY_CLICK then START_CLICK (fractions of the client area) enters the game; the game is paused when a save
loads, and space toggles the pause only with the console closed. From the live session of 2026-11-11: the click
selects the country the camera is on, which need not be the tagged one (FRA was tagged, the game began as DEN),
and no read stopped at the breakpoint after Start, so `enter_game` attaches the debugger again and tags the
country again before its proof. Each round of time ends by proving the pause: two date reads PROOF_PAUSE_S apart
must agree.
"""
from __future__ import annotations

import math
import os
import re
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from game_qa import fixture, overlay, pixels, rules, snapshot
from game_qa.console import CLEAR_BACKSPACES, KEYBOARD_AWAY, Console, ConsoleError, Reply
from game_qa.dap import Debugger, DebuggerError
from game_qa.fixture import RunCli
from game_qa.gate import UNKNOWN_START, ProcId
from game_qa.helper import Helper, HelperError
from game_qa.logtail import GAP_MARKER, LogFollower, Pending, parse, pending_events
from game_qa.report import Report, stamp, utc_now
from game_qa import selfchecks          # the mod's TE_SELF_CHECK lines: kept with the fixture, reported for a run

COUNTRY_CLICK = (0.492, 0.656)          # the country the camera is on, tagged or not (3840x2160, spec § 12.1 A2)
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
LOAD_WAIT_S = 600.0                     # from the first answering window to a console that takes commands, retrying
                                        # while a late save's load keeps the window from responding (a guess, generous)
STOP_WAIT_S = 15.0                      # from typing the read event to the debugger's stop (real seconds: dap's clock)
DATE_WAIT_S = 5.0                       # from the resume to the read event's line in the log
SETUP_WAIT_S = 10.0                     # from a setup's command to its done marker in the log
# add-setup (#1600): the game reloads te_qa_effects.txt once it is rewritten. Live on 1.15.1 (2026-11-12, twice:
# on the country-select screen and in an entered game) a reload took about 90 s, and for all of it the game's
# window did not respond; the probes of 2026-11-10 saw 40 s, console commands dropped and every debug.log
# generation rotated (spec § 3.3).
RELOAD_FIRST_S = 20.0                   # after the rewrite, before the first look: the window is frozen by then
RELOAD_RETRY_S = 5.0                    # between looks (a look at a frozen window takes the console's 10 s itself)
RELOAD_WAIT_S = 300.0                   # for the game to log the new revision, in all
LOADED_WAIT_S = 5.0                     # from the revision event's command to its line in the log
LOADED_COMMAND = "event " + overlay.LOADED_EVENT
# What a look may fail with while the game reloads, and so is tried again: the command was dropped (no_ack),
# or the reload's burst swallowed its lines (no_reply, log_gap). The event only logs, so a second run costs nothing.
RELOAD_RETRIED = ("no_ack", "no_reply", "log_gap")
# The console calls a window that has not responded for 10 s `game_gone`. During a reload that is the game being
# busy, so it is tried again too, but only while the window is still there (`_reloading`); `watch` is looked at
# between tries, and ends them when the game really has gone.
RELOAD_FROZEN = "game_gone"
# Live, 2026-11-12: in the second session the game stayed frozen for four minutes after its reload, its log
# silent, until a verb that reads the debugger's connection was run; then it answered at once. In the third,
# with the connection read before every look, the wait ended after 66 s and no stop was ever reported. So the
# game is most likely held by a debugger connection nobody reads (it streams every error-log line there, and a
# reload writes tens of thousands), not stopped at a breakpoint; the mechanism was not looked at further. The
# wait reads the connection before each look, and resumes a stop if it does find one.
PRESS_KEYS = {"esc": 0x01}              # what `press` may send: a probe's key, in the game itself
LOG_POLL_S = 0.2
CLICK_SETTLE_S = 1.0                    # after the country click, before Start (unverified)
# enter-game's check that the country click selected a country (#1598). The country-select screen's side panel
# reads "Click on a country to select it." until one is selected, then shows that country; a click that lands on
# a window (the game's "We now have <law>!" after a setup changed a law there) changes nothing in it: across the
# real shots of 2026-11-12, with and without such a window, the panel did not differ by one pixel.
# Nothing is pressed to close the window. Live, the same day: after the click had landed on it, neither Esc nor
# Enter closed it (three and two presses), though in an earlier session, with the cursor elsewhere, two windows
# went after two `press esc`; what closed them there is not established. And a console probe typed while the
# console is closed goes to the game, where its letters move the camera off the country.
PANEL_BOX = (0.87, 0.06, 0.99, 0.80)    # the side panel, clear of the date above and the buttons below
PANEL_CHANGED = 0.01                    # this share of its pixels differing is a country selected

# The helper's refusals of a click that come before the button goes down (win_helper._op_click: the window in
# front and the process the recorded one, the point inside the client area, the cursor on it, the game's window
# under it). Any other error may follow the press.
CLICK_REFUSED_BEFORE_PRESS = ("not_foreground", "bad_point", "cursor_misplaced", "covered", "not_ours")
# Where the console's input line is, as fractions of the client area: measured, not derived. Live on 2026-11-12, in
# the owner's 3840x2160 window at his UI scale with the console open on the left, a click here gave the keyboard
# back after a click into the script profiler had taken it (#1710). Another window size or UI scale moves it:
# `click --console --input-line X Y`, aimed from a shot.
CONSOLE_INPUT_LINE = (0.1125, 0.544)
MAX_NOTCHES = 40                        # what one `wheel` turns at most, either way (win_helper.MAX_NOTCHES)
# profiler-roots (#1701, #1710). `Script.Profiling.Gui` opens the script profiler at its roots ("No parent" as
# Current, the top-level entries as its callees), even when an entry was Current before (live, 2026-11-12), and
# the call graph is cropped out of a shot. The box is fractions of the client area, measured on the overlay's
# enlarged window in the owner's 3840x2160 window at his UI scale: shot_09.png of run 20261112T195545Z, a
# 1600x900 shot of the roots, where the frames run from y 292 to 845, Current from x 473 (385 once an entry is
# Current) and Callees to x 1377. The console, open on the left, covers most of the Callers column, so the box
# starts at Current. Another window size or UI scale moves it: `profiler_roots(box=...)`.
PROFILER_COMMAND = "Script.Profiling.Gui"
PROFILER_OPENED = "Opened Script.Profiling.Gui"     # its reply, live
PROFILER_ROOTS_BOX = (0.235, 0.303, 0.866, 0.945)
PROFILER_SETTLE_S = 1.0                 # from the command's reply to the shot (a guess: the window was drawn by then)
# Its shot is taken at the window's own width, not at the 1600 pixels of `shot`: that downscale drops whole pixel
# columns, and with them the thin stroke of a 1 (2801.163 read 280'.163 in the crops of 2026-11-12). The crop then
# has at least PROFILER_CROP_RESOLUTION times the 1600-pixel shot's resolution, which is what was legible live,
# each pixel repeated as often as that takes: not at all at 3840 pixels wide, twice at 1920.
SHOT_WIDTH = 1600                       # what `shot` takes (the helper's default)
PROFILER_CROP_RESOLUTION = 2.0
PROFILER_MAX_SCALE = 4
ENTER_SETTLE_S = 10.0                   # after Start, before the console is looked for: the game loads (a guess; live
                                        # 2026-11-11 the console answered after Start, how soon is unmeasured)
ENTER_WAIT_S = 90.0                     # then, for the console to take commands again (a guess, generous)
ENTER_RETRY_S = 5.0                     # between its tries
# The console's refusals a game still loading after Start can cause, retried within ENTER_WAIT_S: no command taken
# (no_ack), and a window that stopped responding for UNRESPONSIVE_S (game_gone). `watch` is looked at before each
# retry, so a game that really ended stops the tries there (watch_ended): once its window is gone `ensure_open`
# answers game_gone before any key, so the keys' own proof (`_prove_game`) never gets the chance. Any other refusal
# (not_foreground after FOREGROUND_WAIT_S of someone at the machine, stranded_text) is not retried.
ENTER_RETRIED = ("no_ack", "game_gone")
# While a late save loads (`_console_when_loaded`) a no_ack is retried once only: the live evidence (2026-11-12) is
# game_gone, and a console that never opens would otherwise be pressed for the whole of LOAD_WAIT_S.
LOAD_NO_ACK_TRIES = 2
# The errors after Start whose own code `enter_game` keeps (with the clicks added): they say more than not_entered.
ENTER_KEPT = ("breakpoint_unverified", "tag_failed", "debugger", "watch_ended", "left_running")
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
WATCH_RESPAWNS = 3                      # a watch that failed while the game is proved alive is run again, this often

_RETRIED = ("refused", "game_left_up")  # a stop that ended so is run again by the next stop()
# restore's refusals that waiting, or the game's end, can clear: only these leave `stop` worth running again. A
# damaged or missing stored file (`error`), a reply that was no JSON (`bad_reply`) or an unreachable backup root
# stays refused however often it is run.
RESTORE_WAITS = ("busy", "watch_still_recording", "launch_in_flight", "game_still_up", "GateError")

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
    not_on_country_select, click_refused, click_unknown, console_not_open,
    keyboard_away, keyboard_not_returned, wheel_refused, wheel_unknown, drag_refused, drag_unknown, not_entered, left_running, bad_days, stalled, not_started, stopped
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
    disabled_dlc: Sequence = ()                     # the owner's playset's disabledDLC, which launch keeps as it is

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
    """The helper as everything that sends input sees it (X1): `keys`, `focus`, `click`, `wheel` and `drag` go out
    only once `Session._prove_game` has passed, just before each one, since a pid may be another program's once the
    game has died (the helper compares the start time again before each step it sends, win_helper._prove_ours). Of
    the helper's other calls only those in `_UNPROVED` pass through, to the session's current helper (a fresh one
    from `_new_helper` too): they send nothing. Any other name is an AttributeError, so a call added to the
    helper later reaches the game through here only once someone has decided whether it needs the proof."""

    _UNPROVED = frozenset({"window", "presence"})      # what the Console reads; neither sends input

    def __init__(self, session: Session) -> None:
        self._session = session

    def __getattr__(self, name: str):
        if name not in self._UNPROVED:
            raise AttributeError("the proved helper passes on only %s unproved, not %r: give it a method here that "
                                 "calls Session._prove_game first if it sends input, or add it to _UNPROVED if it "
                                 "sends none" % (", ".join(sorted(self._UNPROVED)), name))
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

    def wheel(self, pid: int, x: int, y: int, notches: int) -> None:
        self._session._prove_game()
        return self._session._helper.wheel(pid, x, y, notches)

    def drag(self, pid: int, x1: int, y1: int, x2: int, y2: int) -> None:
        self._session._prove_game()
        return self._session._helper.drag(pid, x1, y1, x2, y2)


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
        self._logs_closed = False           # the logs are read no more: `logs/` may be another game's by now
        self._ended_alive = False           # the stop under way ended the game while it was alive
        self._console: Console | None = None
        self._relay_open = False
        self._debugger: Debugger | None = None
        self._country: str | None = None
        self._entered = False
        self._entered_unproved = False      # Start was clicked and a failure came before the proof: maybe in play
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
        self._loaded_revision = 0           # the newest revision of te_qa_effects.txt the game has logged (add-setup)
        self._rules: dict | None = None     # the rule settings of the fixture loaded, and what was switched in it
        self._profiler_window: dict = {"enlarged": False, "why": "the overlay has not been built"}

    # ---- start

    def start(self, permission: str, as_tag: str | None = None, setups: Mapping[str, str] | None = None,
              save: str | None = None, playset: str = "mod_only", owner_confirmed_busy: bool = False,
              switch_rules: Mapping[str, str] | None = None) -> dict:
        """Get a game up on the fixture (made first if missing) or on `save`, played as `as_tag`.

        `switch_rules` ({rule: setting}) loads a copy of the fixture in which those rules are switched (#1599,
        `game_qa.rules`): a game whose rule changed on 2 January 1836, a day after it began, not one made under
        that setting. It is refused with `save` (the owner's save is never edited or copied), and for a rule
        or setting the game's rule files do not define (`bad_rule`), before anything is done.

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
        switch_rules = self._check_switches(switch_rules, save)
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
            result = self._start(permission, as_tag, setups, save, playset, owner_confirmed_busy, switch_rules)
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
               busy: bool, switch_rules: dict[str, str] | None = None) -> dict:
        self._check_abort()
        # The profiler window, enlarged (#1710): read from the game's install, never stops a start (`why` says).
        gui, self._profiler_window = overlay.profiler_gui(self._paths.base_game)
        try:
            self._overlay = overlay.build(self._paths.overlay_dir, setups, self._paths.game_version, profiler_gui=gui)
        except overlay.OverlayError as e:
            raise SessionError("overlay_refused", str(e)) from e
        if self._overlay.profiler_gui is not None:
            self._profiler_window = dict(self._profiler_window, file=str(self._overlay.profiler_gui))
        self._record("overlay", outcome="built", setups=sorted(self._overlay.setup_events),
                     profiler_window=self._profiler_window)
        save, made, pruned = self._the_save(save, permission, playset, busy, switch_rules or {})
        self._save = save
        self._drop_fixture_lines()
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

        self._debug_log = LogFollower(self._paths.logs / "debug.log", found=self._found_log(snap))
        self._error_log = LogFollower(self._paths.logs / "error.log")
        self._console = Console(self._sends, self._proc, self._paths.history,
                                LogFollower(self._paths.logs / "debug.log"), sleep=self._sleep, clock=self._clock)
        self._console_when_loaded()
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
        if self._rules is not None:
            result["rules"] = self._rules
        result["profiler_window"] = self._profiler_window
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

    def _rule_table(self) -> dict[str, dict]:
        """The rules the run's game loads: vanilla's, then the deployed mod's (another mod's, under `--playset
        current`, are not read, so a rule of theirs cannot be switched)."""
        return rules.load_rules([Path(self._paths.base_game) / "game" / rules.RULES_FOLDER,
                                 Path(self._paths.deploy_dir) / rules.RULES_FOLDER])

    def _check_switches(self, switch_rules: Mapping[str, str] | None, save: str | None) -> dict[str, str]:
        if switch_rules is None or switch_rules == {}:
            return {}
        if not isinstance(switch_rules, Mapping):
            raise SessionError("bad_argument", "switch_rules maps a rule to a setting, not %r" % (switch_rules,))
        if save is not None:
            raise SessionError("bad_argument", "a rule is switched in a copy of the harness's own fresh save: with "
                               "--save the game is the owner's save, which is never edited or copied")
        try:
            rules.check_switches(switch_rules)
            table = self._rule_table()
        except rules.RulesError as e:
            raise SessionError("bad_rule", str(e)) from e
        for rule, option in switch_rules.items():
            if rule not in table:
                raise SessionError("bad_rule", "no rule %r in the game's rule files; the rules are %s"
                                   % (rule, ", ".join(sorted(table))), rules=sorted(table))
            if option not in table[rule]["settings"]:
                raise SessionError("bad_rule", "%r is not a setting of %s; its settings are %s"
                                   % (option, rule, ", ".join(table[rule]["settings"])),
                                   settings=list(table[rule]["settings"]))
        return dict(switch_rules)

    def _the_save(self, save: str | None, permission: str, playset: str, busy: bool,
                  switch_rules: Mapping[str, str] | None = None) -> tuple[str, bool, list[str]]:
        """(the save to load, whether the fixture was made now, the fixtures pruned). With `switch_rules` the
        save is the fixture's copy with those rules switched, made from the fixture if it is not there yet."""
        if save is not None:
            self._record("fixture", outcome="not_used", save=save)
            return save, False, []
        self._fixture_loaded = True
        user = Path(self._paths.user_data)
        loads = run_playset(playset, self._paths.enabled_mods, self._paths.deployed_mod_windows_path,
                            self._paths.overlay_windows_path)
        key = fixture.key(self._paths.game_version, loads, self._paths.deploy_dir, playset=playset,
                          disabled_dlc=self._paths.disabled_dlc, rules=rules.last_applied(user))
        stem, made, pruned = self._base_fixture(user, key, permission, playset, busy)
        if switch_rules:
            try:
                path, changed, settings = rules.switched_fixture(user, key, switch_rules, self._rule_table())
            except rules.RulesError as e:
                self._record("switch_rules", outcome="refused", detail=str(e))
                raise SessionError("rules_refused", str(e)) from e
            stem = path.stem
            self._rules = {"settings": settings, "switched": changed, "switched_at": rules.SWITCHED_AT}
            self._record("switch_rules", outcome="ok", save=stem, switched=changed)
            pruned = pruned + self._prune(user, in_use=(path.name, fixture.FIXTURE_PREFIX + key + ".v3"))
        else:
            try:
                self._rules = {"settings": rules.settings_of((user / fixture.SAVE_FOLDER / (stem + ".v3"))
                                                             .read_bytes())}
            except (OSError, rules.RulesError) as e:
                self._record("rules", outcome="unread", detail=str(e))
        return stem, made, pruned

    def _prune(self, user: Path, in_use: Sequence[str] = ()) -> list[str]:
        """Trim the old fixtures, never one of `in_use` (file names): the save about to be loaded, and the
        fixture it was copied from."""
        try:
            return fixture.prune(user, keep=FIXTURES_KEPT, in_use=in_use)
        except OSError as e:
            self._record("fixture_prune", outcome="failed", detail=str(e))
            return []

    def _base_fixture(self, user: Path, key: str, permission: str, playset: str,
                      busy: bool) -> tuple[str, bool, list[str]]:
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
        self._forget_fixture_lines(key)
        try:
            made = fixture.make(run_cli, user, key, self._paths.overlay_windows_path, permission, playset,
                                owner_confirmed_busy=busy, sleep=self._sleep, spawn_watch=spawn_watch,
                                clock=self._clock, started=self._journaled_proc,
                                keep_lines=lambda snap: self._keep_fixture_lines(key, snap))
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
        pruned = self._prune(user, in_use=(made.name,))
        self._record("fixture", outcome="made", save=made.stem, pruned=pruned)
        return made.stem, True, pruned

    def _forget_fixture_lines(self, key: str) -> None:
        """Before a fixture is made under `key`: nothing kept for an earlier fixture of that key, or for one whose
        save is gone, may be left to be shown as the new one's (a deleted fixture is made again under its key).
        The orphans go first, then `key`'s own, which leaves a record that nothing is kept yet. Never raises; a
        record that could not be removed is a step, and `keep_fixture_lines` removes it again."""
        self._drop_fixture_lines()
        try:
            selfchecks.forget_fixture_lines(self._paths.backup_root, key)
        except Exception as e:
            self._record("fixture_lines", outcome="forget_failed", key=key, detail=_describe(e))

    def _keep_fixture_lines(self, key: str, snap: str) -> None:
        """Once the fixture is made: keep its run's TE_SELF_CHECK and TE_MONUMENTS lines under the backup root
        (`selfchecks.keep_fixture_lines`). Never raises: a fixture whose lines could not be kept is still the
        fixture, and the step says what went wrong."""
        try:
            record = selfchecks.keep_fixture_lines(self._paths.backup_root, key, snap)
        except Exception as e:
            self._record("fixture_lines", outcome="failed", snapshot=snap, detail=_describe(e))
            return
        self._record("fixture_lines", outcome="kept", **record)

    def _drop_fixture_lines(self) -> None:
        """The kept lines go with their fixture: those of a fixture `fixture.prune` has just removed, or that is
        gone from `save games/` for any other reason. Only files under `<backup root>/fixtures/` are removed.
        Never raises: lines left behind are swept at the next start."""
        try:
            dropped = selfchecks.drop_orphans(self._paths.backup_root, self._paths.user_data)
        except Exception as e:
            self._record("fixture_lines", outcome="drop_failed", detail=_describe(e))
            return
        if dropped:
            self._record("fixture_lines", outcome="dropped", keys=dropped)

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

    def _found_log(self, snap: str) -> tuple[int, str] | None:
        """The size and hash of the `logs/debug.log` the run's snapshot recorded: the log the game found when it
        was launched. A game that appended to it would hand the session an earlier game's lines as its own, so
        the follower skips a beginning with exactly those bytes (`LogFollower`). None when the snapshot's
        manifest cannot be read or holds no such log."""
        try:
            entry = snapshot.load(Path(self._paths.backup_root) / "snapshots" / snap).files.get(selfchecks.OWNERS_LOG)
        except (OSError, ValueError):
            return None
        return (entry.size, entry.sha256) if entry is not None else None

    def _console_when_loaded(self) -> None:
        """Wait for the console to take commands once the window has first answered: `ensure_open` is tried
        every ENTER_RETRY_S while it refuses game_gone, until LOAD_WAIT_S has passed, and once more after a
        no_ack (LOAD_NO_ACK_TRIES); any other error is raised at once, and `watch` (and a stop asked meanwhile) is looked at before each retry,
        so a game that ended stops the tries. A save from late in a game keeps the window from responding for
        longer than UNRESPONSIVE_S while it loads (live 2026-11-12: a 47 MB save of 1931 ended the first start
        `game_gone` 75 s after the launch), which one `ensure_open` takes for a game that has gone. Recorded as
        the step `console_ready`, with the tries made."""
        deadline = self._clock() + LOAD_WAIT_S
        with self._step("console_ready") as out:
            tries = no_acks = 0
            while True:
                tries += 1
                out["tries"] = tries
                try:
                    self._console.ensure_open(max(1.0, min(CONSOLE_READY_S, deadline - self._clock())))
                    return
                except ConsoleError as e:
                    no_acks += e.code == "no_ack"
                    if (e.code not in ENTER_RETRIED or no_acks >= LOAD_NO_ACK_TRIES
                            or self._clock() + ENTER_RETRY_S > deadline):
                        raise
                    out["last_refusal"] = e.code
                self._sleep(ENTER_RETRY_S)
                self._check_watch()
                self._check_abort()

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

    def _attach(self, step: str = "debugger") -> None:
        """Open the debugger's relay and attach with the read event's breakpoint, which the game must verify
        (`breakpoint_unverified` otherwise), recorded as the step `step`, a failure too. `start` attaches once;
        `_enter` attaches again once Start is pressed (`reattach`): live (2026-11-11) no read stopped at the
        breakpoint after entering from the country-select screen, though the console answered and events ran,
        which a reload of the script dropping the breakpoint would explain (unverified). A connection already open
        is closed first, once any stop it holds is released (`_drain`, or `_release_pending`, as `_require_game`
        does: N5), since a game left stopped behind a closed connection has nobody to resume it. A close that fails
        is noted and not fatal: `tcp_open` closes the old connection itself (win_helper._op_tcp_open)."""
        path = self._paths.events_file_windows_path(self._overlay.events_file)
        with self._step(step, breakpoint=path, line=self._overlay.read_line) as out:
            if self._relay_open:
                if self._maybe_stopped:
                    self._drain()
                else:
                    self._release_pending()
                notes: list[str] = []
                self._close_relay(notes)
                if notes:
                    out["notes"] = notes
            self._helper.tcp_open(DEBUGGER_PORT)
            self._relay_open = True
            # dap turns whatever the relay raises (a HelperError on a closed peer) into a DebuggerError.
            self._debugger = Debugger(self._helper.tcp_send, self._helper.tcp_recv)
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

    def add_setup(self, name: str, body: str) -> dict:
        """Add a setup to the running game (#1600): its body goes into a spare slot of the overlay's
        `te_qa_effects.txt`, and the verb returns once the game has logged that file's new revision, which is the
        proof that it reloaded the file. `run_setup(name)` then runs it like a setup given at start.

        A name or body the overlay refuses is `overlay_refused`, with nothing written. When the game has not
        logged the new revision within RELOAD_WAIT_S the error is `not_reloaded`: the setup is in the file, and
        `run_setup` looks once more before it would run it, so a slow reload costs a wait and not the setup.
        The debugger is attached again once the reload is seen, because a reload of the script may drop the
        read event's breakpoint (as entering the game does)."""
        self._require_game()
        with self._step("add_setup", name=name) as out:
            try:
                event, revision = overlay.add_setup(self._overlay, name, body)
            except overlay.OverlayError as e:
                raise SessionError("overlay_refused", str(e)) from e
            out.update(event=event, revision=revision)
            began = self._clock()
            self._sleep(RELOAD_FIRST_S)
            self._await_revision(revision, began + RELOAD_WAIT_S, out)
            out["waited_s"] = round(self._clock() - began, 1)
            result = {"name": name, "event": event, "revision": revision, "loaded": True,
                      "tries": out["tries"], "waited_s": out["waited_s"],
                      "slots_left": overlay.SLOT_COUNT - len(self._overlay.added)}
        self._attach("reattach")
        return result

    def _await_revision(self, revision: int, deadline: float, out: dict) -> None:
        """Ask the game which revision of `te_qa_effects.txt` it has loaded, every RELOAD_RETRY_S, until it says
        `revision` or later; `not_reloaded` once `deadline` has passed. `out` gets the tries made and the last
        revision seen."""
        tries = 0
        while True:
            tries += 1
            out.update(tries=tries, seen=self._loaded_revision)
            failed = None
            self._resume_after_reload(out)
            try:
                self._look_for_revision()
            except ConsoleError as e:
                if not self._reloading(e):
                    raise
                failed = "%s: %s" % (e.code, e)
            out["seen"] = self._loaded_revision
            if self._loaded_revision >= revision:
                return
            if self._clock() + RELOAD_RETRY_S > deadline:
                raise SessionError(
                    "not_reloaded", "the game had not loaded revision %d of %s after %d looks (it last logged "
                    "revision %d%s). The setup is in the file: run-setup and read look again before they run, "
                    "and attach the debugger again once the reload has come"
                    % (revision, overlay.EFFECTS_FILE, tries, self._loaded_revision,
                       "; the last look failed with " + failed if failed else ""),
                    revision=revision, seen=self._loaded_revision, tries=tries)
            self._sleep(RELOAD_RETRY_S)
            self._check_watch()

    def _resume_after_reload(self, out: dict) -> None:
        """Read what the debugger's connection holds, which is what lets a game frozen after a reload go on (see
        the note above PRESS_KEYS), and resume a stop if one is there. `out` gets the reason of each stop
        released (`released`; none was, live), and what the debugger said if the look itself failed
        (`debugger`): the relay may not survive a reload, and the wait goes on either way, since the debugger
        is attached again at its end."""
        dbg = self._debugger
        try:
            stopped = dbg.poll_stopped()
        except DebuggerError as e:
            out.setdefault("debugger", []).append(str(e)[:200])
            return
        if not stopped:
            return
        out.setdefault("released", []).append(dbg.last_stop_reason)
        if not self._resume(dbg):
            self._maybe_stopped = True
            raise SessionError("maybe_stopped", "the reload left the game stopped at the debugger, and it did not "
                               "take a resume, twice", maybe_stopped=True)

    def _reloading(self, e: ConsoleError) -> bool:
        """Whether a console error during a look is what a reloading game gives, so the look can be made again:
        one of RELOAD_RETRIED, or a window that does not respond (RELOAD_FROZEN) while the window still exists.
        Nothing was typed that could run twice: the look's command only logs."""
        if e.code in RELOAD_RETRIED:
            return True
        if e.code != RELOAD_FROZEN:
            return False
        try:
            return bool(self._helper.window(self._proc.pid).exists)
        except HelperError:
            return False

    def _look_for_revision(self) -> None:
        """Run the revision event once and take the newest revision the log names into `_loaded_revision`."""
        self._new_lines()
        self._console.run(LOADED_COMMAND, reply=False)
        deadline = self._clock() + LOADED_WAIT_S
        while True:
            found = [overlay.loaded_revision(parse(line).text) for line in self._new_lines() if line != GAP_MARKER]
            # Only a revision this overlay has written counts: a setup's own log line could carry the text.
            found = [rev for rev in found if rev is not None and rev <= self._overlay.revision]
            if found:
                self._loaded_revision = max(self._loaded_revision, found[-1])
                return
            if self._clock() >= deadline:
                return
            self._sleep(LOG_POLL_S)

    def _catch_up_reload(self) -> bool:
        """After an `add_setup` whose reload was not seen: look once more, and when the game has moved on to a
        newer revision attach the debugger again (the reload may have dropped the breakpoint). True when it had."""
        if self._loaded_revision >= self._overlay.revision:
            return False
        before = self._loaded_revision
        self._resume_after_reload({})
        try:
            self._look_for_revision()
        except ConsoleError as e:
            if not self._reloading(e):
                raise
        if self._loaded_revision == before:
            return False
        self._attach("reattach")
        return True

    def run_setup(self, name: str) -> list[str]:
        """Run a setup through its event; return its log lines between its start and done markers. A setup added
        with `add_setup` whose reload was never seen is looked for once more first, and refused
        (`setup_not_loaded`) while the game still runs the older file: its slot would log nothing."""
        self._require_game()
        with self._step("run_setup", name=name) as out:
            event = self._overlay.setup_events.get(name)
            if event is None:
                raise SessionError("unknown_setup", "no setup %r; the overlay has %s"
                                   % (name, sorted(self._overlay.setup_events) or "none"))
            if self._catch_up_reload():
                out["reloaded"] = True
            added = self._overlay.added.get(name)
            if added is not None and self._loaded_revision < added[0] + 1:
                needed = added[0] + 1       # slot n was filled by revision n + 1
                raise SessionError("setup_not_loaded", "the game has not reloaded %s since setup %s was added "
                                   "(it logs revision %d, the setup came with %d; a reload takes about 90 s, "
                                   "and the game's window does not respond during it): wait and run it again"
                                   % (overlay.EFFECTS_FILE, name, self._loaded_revision, needed),
                                   revision=needed, seen=self._loaded_revision)
            self._new_lines()                   # what was logged before is not this setup's
            self._console.run("event " + event, reply=False)
            lines = self._setup_lines(name)
            out["lines"] = len(lines)
        return lines

    def press(self, key: str) -> dict:
        """Press one key of PRESS_KEYS in the game itself, the console closed first so the key does not go into
        its input line. A probe's verb: what the key does is for the caller to see (`shot` before and after).
        The console is left closed, and the next verb that types finds that out by typing: its first probe goes
        to the game, where the letters move the camera (seen live, 2026-11-12), before the console key is
        pressed. So take the `shot` first, and expect the view to have moved afterwards."""
        self._require_game()
        with self._step("press", key=key) as out:
            scan = PRESS_KEYS.get(str(key).lower())
            if scan is None:
                raise SessionError("bad_argument", "press takes one of %s, not %r" % (", ".join(sorted(PRESS_KEYS)), key))
            self._console.ensure_open()         # so its state is known, and the game is in front
            self._console.close()
            self._console.hotkey(scan)
            out["scan"] = scan
        return {"key": str(key).lower(), "scan": scan}

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
        """Each trigger or value evaluated at the read event's breakpoint, in the played country's scope. A
        trigger is written bare and is checked for the played country (`tag` another to read it):
        `has_technology_researched = railways` works, while `c:FRA.has_technology_researched = railways` answers
        "Unknown trigger type". A variable that is not set reads 0, not an error (`c:FRA.var:x` gave "0", live
        2026-11-11), so a 0 does not prove the variable set."""
        self._require_game()
        self._catch_up_reload()             # a reload still due after add-setup may have dropped the breakpoint
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
        (`not_on_country_select`), and `advance` needs no entering.

        After Start (live, 2026-11-11, the clicks entered the game as the country the camera was on, and no read
        stopped at the breakpoint after them): wait ENTER_SETTLE_S, wait for the console (`_console_after_start`,
        up to ENTER_WAIT_S), attach the debugger again on a new connection (`reattach`), tag the session's country
        again (`tag`), and only then read the date and run the unpaused proof. Any failure from the Start click on
        sets `left_running` and `entered_unproved`, clicks nothing more, and carries the clicks: its own code for
        breakpoint_unverified, tag_failed, debugger, watch_ended or left_running, else not_entered with the code as
        `cause`.

        One not_entered sets neither and has no `cause`: the proof ran to its end, the pause proved, and the date
        had not moved ("the date stayed"). The game is then where it was, on the country-select screen with time
        stopped, as when a window covered the country click (#1598), so `enter_game` may be called again, and
        `advance` calls it again."""
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

    def click(self, x: float | None = None, y: float | None = None, console: bool = False,
              input_line: Sequence[float] | None = None) -> dict:
        """One left click at (x, y), fractions of the game window's client area from its top left, then a
        screenshot of what it did; with `console`, then a click on the console's input line, which gives the
        keyboard back. It is for the engine's own tool windows that no console command reads, such as the script
        profiler's call graph (#1701), and for the console's input line (the owner's go-ahead of 2026-11-12); it
        can press anything a player can, so what it is aimed at is the caller's to know, from a `shot` first.

        Each click waits for the presence rule as a key does, and goes through the pid proof as enter-game's do
        (`_ProvedHelper.click`). A click the helper refused before the button went down (CLICK_REFUSED_BEFORE_PRESS)
        is `click_refused` and pressed nothing; any other helper error (`backend_error`, `helper_gone`, a timeout)
        is `click_unknown`, since it may have come after the press: take a `shot` before clicking again. A
        screenshot that fails after a click is not a refusal: the reply has `screenshot: null` and
        `screenshot_error`, as enter-game's does.

        A click takes the keyboard (live, 2026-11-12: after a click into the profiler, the next typed command never
        reached the console, a read's `no_stop` with `arrived: false`, until the console's input line was clicked).
        So a click made while the console is known open latches the keyboard away (`Console.clicked`; the reply's
        `keyboard_away`): every verb that types is refused `keyboard_away`, before anything is typed or written,
        until `console` gives it back. That clicks `input_line` (CONSOLE_INPUT_LINE by default, measured live) and
        types the console's probe once: arrived, the latch is lifted; not arrived, `keyboard_not_returned`, the
        latch stays, and the console key is not pressed. Nothing is clicked unless the console is open as far as is
        known, or a click made while it was has latched the keyboard away (`_refuse_unless_console_open`;
        `console_not_open` otherwise): with it shut, the input line's point is the map, and a click into a tool
        window would take the keyboard with no way to give it back.

        The restore does not cover the owner's manual saves (only the autosaves and a `--save` file), so a click
        must never be aimed at the game's own menus (save, load, settings, exit)."""
        self._require_game(keyboard=False)
        if (x is None) != (y is None) or (x is None and not console):
            raise SessionError("bad_argument", "click takes X and Y, --console, or both")
        target = None if x is None else (_fraction("x", x), _fraction("y", y))
        if input_line is not None and not console:
            raise SessionError("bad_argument", "an input line's point goes with --console")
        line = CONSOLE_INPUT_LINE if input_line is None else _pair("the input line", input_line)
        self._refuse_unless_console_open("click", line if console else None)
        with self._step("click", x=x, y=y, console=console) as out:
            result: dict[str, Any] = {}
            if target is not None:
                result.update(self._one_click(target))
                out.update(result)
            if console:
                try:
                    result["console"] = out["console"] = self._one_click(line, tool=False)
                except SessionError as e:
                    e.info.update(first=result or None, keyboard_away=self._console.keyboard_away)
                    raise
                if not self._console.take_keyboard_back():
                    out["keyboard_away"] = True
                    raise SessionError(
                        "keyboard_not_returned", "the console's probe, typed after the click on its input line at "
                        "%s, did not reach the console: the click missed the line (another window size or UI scale "
                        "moves it: aim --input-line X Y from the shot), or something else holds the keyboard. The "
                        "console key was not pressed; every verb that types is refused until a `click --console` "
                        "gets the probe through" % (list(line),), **result, keyboard_away=True)
            result["keyboard_away"] = out["keyboard_away"] = self._console.keyboard_away
        return result

    def _refuse_unless_console_open(self, verb: str, line: tuple[float, float] | None = None) -> None:
        """Before `click`, `wheel` or `drag` sends anything: the console is open as far as is known, or a click made
        while it was has latched the keyboard away (`Console.input_line_there`). Otherwise `console_not_open`,
        nothing sent. A click into a tool window takes the keyboard, and `Console.clicked` latches it away only
        while the console is known open, since only then can `click --console` click the input line to give it
        back. With the console shut or not known, the next verb that types would type into that window and press
        the console key (`press esc`, a click on a profiler row, then a `read`).
        `line`: the input line's point, when the verb would click it. enter-game's own clicks do not come here."""
        if self._console.input_line_there:
            return
        if line is not None:
            why = ("its input line may not be at %s: with the console shut that point is the map" % (list(line),))
        else:
            why = ("a %s into a tool window would take the keyboard with no way to give it back: the verbs that "
                   "type would type into that window, and `click --console` clicks the input line only while the "
                   "console is open" % verb)
        raise SessionError("console_not_open", "the console is not known to be open, so %s. Nothing was sent. Run "
                           "a verb that types first, such as `events`, which opens the console, then the %s again"
                           % (why, verb), keyboard_away=False, next="python3 -m game_qa events")

    def _one_click(self, fraction: tuple[float, float], tool: bool = True) -> dict:
        """One click at `fraction` of the client area, then its shot: {"pixel", "screenshot"} (and
        `screenshot_error`). A click that went out latches the keyboard away (`Console.clicked`), unless it was on
        the console's input line (`tool` false), whose probe decides; a click that may have gone out latches it
        either way."""
        self._console.front()
        px, py = self._point(fraction)
        try:
            self._sends.click(self._proc.pid, px, py)
        except HelperError as e:
            if e.code in CLICK_REFUSED_BEFORE_PRESS:
                raise SessionError("click_refused", "%s: %s" % (e.code, e.detail),
                                   keyboard_away=self._console.keyboard_away) from e
            self._console.clicked()
            raise SessionError("click_unknown", "%s: %s; the button may have been pressed: take a shot before "
                                                "clicking again" % (e.code, e.detail), pixel=[px, py],
                               keyboard_away=self._console.keyboard_away) from e
        if tool:
            self._console.clicked()
        return self._shot_after({"pixel": [px, py]})

    def _shot_after(self, done: dict) -> dict:
        """`done` with the screenshot that follows a click, a wheel or a drag (`screenshot`, or `screenshot: null`
        and `screenshot_error`: the input stands either way, so a failed shot is no refusal)."""
        self._sleep(CLICK_SETTLE_S)
        try:
            done["screenshot"] = str(self._shot())
        except HelperError as e:
            done["screenshot"], done["screenshot_error"] = None, "%s: %s" % (e.code, e.detail)
        return done

    def wheel(self, x: float, y: float, notches: int) -> dict:
        """Turn the mouse wheel `notches` notches at (x, y), fractions of the client area: positive away from the
        user, which scrolls a list up; negative scrolls it down. Then a screenshot. For a list in a tool window that
        is longer than the window (the script profiler's roots past the 27th, #1710), with `click`'s scope and
        rules: the presence rule, the pid proof, never the game's own menus (a wheel over the map zooms it). It
        latches the keyboard away as a click does, since whether a wheel moves the keyboard is not known.
        `wheel_refused` turned nothing; `wheel_unknown` may have turned some notches (`notches_done` when the
        helper said). Like a click, it is refused `console_not_open` unless the console is open as far as is known."""
        self._require_game(keyboard=False)
        point = (_fraction("x", x), _fraction("y", y))
        if isinstance(notches, bool) or not isinstance(notches, int) or not 0 < abs(notches) <= MAX_NOTCHES:
            raise SessionError("bad_argument", "notches is a whole number from -%d to %d other than 0, not %r"
                               % (MAX_NOTCHES, MAX_NOTCHES, notches))
        self._refuse_unless_console_open("wheel")
        with self._step("wheel", x=x, y=y, notches=notches) as out:
            self._console.front()
            px, py = self._point(point)
            try:
                self._sends.wheel(self._proc.pid, px, py, notches)
            except HelperError as e:
                done = e.reply.get("notches_done")
                if e.code in CLICK_REFUSED_BEFORE_PRESS and done == 0:
                    raise SessionError("wheel_refused", "%s: %s" % (e.code, e.detail),
                                       keyboard_away=self._console.keyboard_away) from e
                self._console.clicked()
                raise SessionError("wheel_unknown", "%s: %s; some notches may have turned: take a shot before "
                                   "turning again" % (e.code, e.detail), pixel=[px, py], notches_done=done,
                                   keyboard_away=self._console.keyboard_away) from e
            self._console.clicked()
            result = self._shot_after({"pixel": [px, py], "notches": notches})
            result["keyboard_away"] = self._console.keyboard_away
            out.update(result)
        return result

    def drag(self, x1: float, y1: float, x2: float, y2: float) -> dict:
        """Press the left button at (x1, y1), move to (x2, y2) and release there (fractions of the client area),
        then a screenshot: to resize or scroll a tool window whose `.gui` cannot be overridden (#1710), with
        `click`'s scope and rules (a drag over the map pans it or draws a selection). It latches the keyboard
        away as a click does. `drag_refused` pressed nothing; `drag_unknown` may have pressed, and then the
        helper released the button where the cursor was (`pressed` when the helper said). Like a click, it is
        refused `console_not_open` unless the console is open as far as is known."""
        self._require_game(keyboard=False)
        start, end = (_fraction("x1", x1), _fraction("y1", y1)), (_fraction("x2", x2), _fraction("y2", y2))
        self._refuse_unless_console_open("drag")
        with self._step("drag", x1=x1, y1=y1, x2=x2, y2=y2) as out:
            self._console.front()
            (ax, ay), (bx, by) = self._point(start), self._point(end)
            try:
                self._sends.drag(self._proc.pid, ax, ay, bx, by)
            except HelperError as e:
                pressed = e.reply.get("pressed")
                if e.code in CLICK_REFUSED_BEFORE_PRESS and pressed is False:
                    raise SessionError("drag_refused", "%s: %s" % (e.code, e.detail),
                                       keyboard_away=self._console.keyboard_away) from e
                self._console.clicked()
                raise SessionError("drag_unknown", "%s: %s; the button may have gone down (the helper releases "
                                   "it where the cursor is): take a shot before dragging again" % (e.code, e.detail),
                                   pixels=[[ax, ay], [bx, by]], pressed=pressed,
                                   keyboard_away=self._console.keyboard_away) from e
            self._console.clicked()
            result = self._shot_after({"pixels": [[ax, ay], [bx, by]]})
            result["keyboard_away"] = self._console.keyboard_away
            out.update(result)
        return result

    def profiler_roots(self, box: Sequence[float] | None = None, as_shown: bool = False) -> dict:
        """Open the script profiler at its roots (`Script.Profiling.Gui`, through the console), take a shot at the
        window's own resolution, and crop the call graph out of it: `screenshot` and `crop` in the run folder.
        With `as_shown` nothing is typed: the window is shot and cropped as it is, after a click on a row or a
        `wheel`, and the keyboard need not be given back first.

        The crop is `box` (left, top, right, bottom: fractions of the client area), PROFILER_ROOTS_BOX by default,
        measured on the overlay's enlarged window (`enlarged` says whether this run's overlay has it; without it the
        window is small and elsewhere, and the default box shows the map). It is scaled up, a pixel repeated
        `scale` times, until it has PROFILER_CROP_RESOLUTION times the resolution of a 1600-pixel shot. A shot that
        fails is not a refusal (`screenshot: null` and `screenshot_error`: the window is open all the same), nor is
        a crop that cannot be made (`crop: null` and `crop_error`). The command is typed like any other, so after a
        click into a tool window it is refused until the keyboard is given back (`click --console`)."""
        self._require_game(types=not as_shown)
        box = PROFILER_ROOTS_BOX if box is None else _box(box)
        with self._step("profiler_roots", box=list(box), as_shown=as_shown) as out:
            result: dict[str, Any] = {"box": list(box), "enlarged": self._profiler_window.get("enlarged") is True}
            if not as_shown:
                reply = self._console.run(PROFILER_COMMAND)
                result.update(lines=reply.lines, opened=PROFILER_OPENED in [line.strip() for line in reply.lines])
            self._sleep(PROFILER_SETTLE_S)
            try:
                width = self._helper.window(self._proc.pid).client[2]
                shot = self._shot(max_width=max(1, width))
            except HelperError as e:
                result.update(screenshot=None, screenshot_error="%s: %s" % (e.code, e.detail), crop=None)
                out.update(result)
                return result
            result["screenshot"] = str(shot)
            crop = shot.with_name("profiler_roots_%02d.png" % self._shots)
            try:
                image = pixels.decode_png(shot.read_bytes())
                scale = min(PROFILER_MAX_SCALE,
                            max(1, math.ceil(PROFILER_CROP_RESOLUTION * SHOT_WIDTH / image[0] - 1e-9)))
                part = pixels.scaled_up(pixels.region(image, box), scale)
                crop.write_bytes(pixels.encode_png(part))
                result.update(crop=str(crop), scale=scale, crop_size=[part[0], part[1]])
            except (OSError, pixels.PixelsError) as e:
                result.update(crop=None, crop_error=str(e))
            out.update(result)
        return result

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
        """How far this session is, from what it holds: nothing is asked of the game or of a verb. `entered` is
        true once `enter_game` proved the game in play; `entered_unproved` once Start was clicked and a failure
        came before that proof, so the game may be in play though `entered` is false (`left_running` is set too)."""
        proc = self._proc
        return {"started": self._ready, "stopped": self._stopped is not None, "snapshot": self._snapshot,
                "save": self._save, "country": self._country, "entered": self._entered,
                "entered_unproved": self._entered_unproved,
                "game": {"pid": proc.pid, "created": proc.created} if proc is not None else None,
                "watch_returned": self._watch_returned(),
                "run_dir": str(self._report.dir) if self._report is not None else None,
                "maybe_stopped": self._maybe_stopped, "left_running": self._left_running,
                "watch_respawns": self._watch_respawns}

    def self_checks(self) -> dict:
        """The verdicts of the mod's TE_SELF_CHECK lines in this run so far, the fixture's run's included
        (`selfchecks.of_run`, read from the run folder's copy of the log and the lines kept with the fixture).

        The game's log is pushed out first, since the game writes it in blocks: an empty read fires the read
        event, whose padding flushes what was logged before it, and its date line is waited for as the proof.
        `flushed` says whether that worked. When it did not (the game is not in front, the debugger did not
        stop), `not_flushed` says why, and the lines already in the game's log are taken without typing
        anything, while `watch` still follows the game and nothing has said it ended. Every line read, here as
        in any verb, is kept only if the game is proved alive after the read (`_new_lines`). When the logs are
        not read, or what was read had to be dropped (the game has ended, `watch` recorded its exit, the
        session is stopped), `log_not_read` says so. The verdicts are given in every case, from what the run
        folder holds: a line logged since the last verb may then be missing."""
        if self._snapshot is None or self._report is None:
            raise SessionError("not_started", "this session has no run folder yet: start() has not got that far")
        with self._step("selfchecks") as out:
            found: dict = {"live": True, "flushed": False}
            try:
                self._require_game()
                self._date()
                found["flushed"] = True
            except (SessionError, ConsoleError, DebuggerError, HelperError) as e:
                found["not_flushed"] = {"refused": _code_of(e), "detail": str(e)}
                watched = (self._stopped is None and not self._stopping and self._watch_ended is None
                           and not self._watch_returned() and self._debug_log is not None)
                if watched:
                    try:
                        self._new_lines()
                    except Exception:
                        pass                    # dropped and closed (`_vouch_for_polled`), or not readable
                if not watched or self._logs_closed:
                    found["log_not_read"] = ("the run's game is not proved alive (it has ended, or the session is "
                                             "stopped), so `logs/` was not read, or what was read was dropped: "
                                             "another game may have written it since. These are the lines the "
                                             "run folder already held")
            found.update(selfchecks.of_run(self._paths.backup_root, self._snapshot))
            out.update(flushed=found["flushed"], not_flushed=found.get("not_flushed"), counts=found["counts"],
                       broken=found["broken"])
            if "log_not_read" in found:
                out["log_not_read"] = True
        return found

    # ---- stop

    def stop(self) -> dict:
        """End the game this session started and put the owner's files back; never raises.

        In order: end the game (`kill`; adopted first if a failure came before `adopt`; through a fresh helper
        from `helper_factory` once if the helper has ended; a `kill` refused not_ours is followed by `adopt`, and
        the game counts as ended, its pid being another program's by now, only if that refuses not_ours too),
        wait for `watch` to return (up to WATCH_WAIT_S),
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
        `stop_again` says whether a later call can change anything: true after a restore refused for a reason that
        waiting or the game's end can clear (RESTORE_WAITS; any other refusal names `recover`), and after a game
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
        self._ended_alive = False
        if self._launched and not self._game_ended:
            self._end_game(notes)
        left_up = self._launched and not self._game_ended
        self._last_log_lines(left_up, notes)
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
        reply["stop_again"] = outcome == "refused" and _clears_by_waiting(restore)
        if left_up:
            reply["game_unwatched"] = self._watch is None or self._watch_returned()
            reply["next"], reply["stop_again"] = self._left_up_next()
        elif outcome == "refused" and reply["stop_again"]:
            reply["next"] = ("`python3 -m game_qa stop` again runs `restore %s` again, once what refused it is "
                             "cleared (a Victoria 3 process running, another verb in the backup root): the server "
                             "answers until a stop ends restored or held" % self._snapshot)
        elif outcome == "refused":
            reply["next"] = ("restore refused %s, which no wait clears, so the server ends here: once its cause is "
                             "fixed (the detail says what; the owner may need to look), and no Victoria 3 process "
                             "runs, `python3 -m game_qa recover` finishes snapshot %s, then `python3 -m game_qa "
                             "remove-overlay`" % (_text((restore or {}).get("refused") or "?"), self._snapshot))
        elif kept is not None and self._keep_overlay(restore, outcome) is None:
            # X3: nothing may name the overlay any more, but removing it failed (a file held open, say)
            reply["next"] = ("the overlay was kept (%s): `python3 -m game_qa remove-overlay` removes it once "
                             "nothing holds a file in it" % kept)
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
            if self._found_gone(proc, notes):
                return
            self._adopted = True
        try:
            gone = self._helper.kill(proc)
        except HelperError as e:
            if e.code != "not_ours":
                raise
            # `kill` refuses not_ours when the pid is another program's by now (the game died and its id was
            # reused), but also when it could not open a live game to end it (win_helper._op_kill, terminate), so
            # its refusal alone proves nothing. `adopt` is asked again: only if it too finds no live process with
            # that pid and start time has the game ended. If it proves the game alive, ending it failed.
            if not self._found_gone(proc, notes, after="kill refused (%s), and " % _describe(e)):
                notes.append("the helper still finds process %d started at %s alive, so that refusal was not the "
                             "game's end" % (proc.pid, proc.created))
                raise
            return
        self._game_ended = True
        self._ended_alive = not gone        # this call ended a process proved the game by its pid and start time
        self._record("kill", outcome="already_exited" if gone else "ok")

    def _found_gone(self, proc: ProcId, notes: list[str], after: str = "") -> bool:
        """Ask the helper to adopt `proc`. Refused `not_ours`, no live process has that pid and start time
        (win_helper._op_adopt): the game has ended, which is recorded, and True is returned. Part 1's restore
        still looks for a running game itself. False once the helper has proved the game alive; any other
        failure of `adopt` is raised."""
        try:
            self._helper.adopt(proc)
        except HelperError as e:
            if e.code != "not_ours":
                raise
            self._game_ended = True
            notes.append("%sthe helper finds no live process %d started at %s (%s): the game has ended"
                         % (after, proc.pid, proc.created, e.detail))
            self._record("kill", outcome="already_exited", detail="%sadopt: %s" % (after, _describe(e)))
            return True
        return False

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
            try:
                found = selfchecks.of_run(self._paths.backup_root, self._snapshot)
            except Exception as e:              # the summary is written all the same, with a note
                found = None
                notes.append("the run's self-check lines could not be read: %s" % _describe(e))
            self._record("stop", outcome=outcome or "not_run", overlay_removed=removed, overlay_kept=kept,
                         notes=list(notes))
            path = self._report.close({"restore": restore, "outcome": outcome, "permission": self._permission,
                                       "snapshot": self._snapshot, "save": self._save, "country": self._country,
                                       "overlay_removed": removed, "overlay_kept": kept, "notes": notes,
                                       "next": next_step, "self_checks": found})
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

    def _new_lines(self, ended_here: bool = False) -> list[str]:
        """The debug.log lines since the last call; both logs' new lines are copied into the run folder.

        Nothing polled is copied, or returned, unless the run's game is proved alive by its pid and start time
        AFTER the poll that read it (`_vouch_for_polled`; one `adopt`, and none for a poll that read nothing).
        Alive after the read is alive at the read, so no line of a game started once ours had died can be
        among them; a proof before the read would leave the time between the two. `ended_here` is the one
        exception, for the stop's single read right after its own `kill` ended the game alive. Once the logs
        are closed nothing is read."""
        if self._logs_closed:
            return []
        lines = self._debug_log.poll()
        errors = self._error_log.poll()
        if (lines or errors) and not ended_here:
            self._vouch_for_polled()
        if self._debug_log.skipped:
            skipped, self._debug_log.skipped = self._debug_log.skipped, 0
            self._notes.append("the game appended to the debug.log it found: its first %d bytes are an earlier "
                               "game's (the run's snapshot recorded them) and were not read as this run's" % skipped)
            self._record("found_log", outcome="prefix_skipped", bytes=skipped)
        self._copy("debug.log", lines)
        self._copy("error.log", errors)
        if self._errors_seen is not None:
            self._errors_seen.extend(errors)
        return lines

    def _vouch_for_polled(self) -> None:
        """After a poll that read lines: the game must still be the run's own, alive (`adopt` compares the pid
        and the start time, and sends nothing). If it cannot be proved, the lines just read are dropped, the
        logs are closed for good, a note says so, and the verbs end (`watch_ended`): the game died at a time
        nobody knows, and a game started since may have written what was read."""
        try:
            self._helper.adopt(self._proc)
        except Exception as e:
            self._logs_closed = True
            why = ("the game could not be proved alive by its pid and start time after its log was read (%s), so "
                   "the lines read were dropped: another game may have written them. Stop the session"
                   % _describe(e))
            self._notes.append("at %s log lines were read and dropped, since the game could not be proved alive "
                               "afterwards and they may be another game's; the game's logs were not read again. "
                               "Self-check lines logged after the verb before are not in the summary"
                               % stamp(utc_now()))
            self._record("log_lines", outcome="dropped", detail=_describe(e))
            if self._watch_ended is None:
                self._watch_ended = why
            raise SessionError("watch_ended", why) from e

    def _last_log_lines(self, left_up: bool, notes: list[str]) -> None:
        """At a stop, before any restore: the last lines the game wrote, for the report's self-checks.

        They are read only when this very call ended the run's game while it was alive (`kill` ended a process
        it had proved the game by pid and start time), and then the logs are closed: a restore follows, and
        afterwards `logs/` holds the owner's logs again. A game that had ended before this call (it crashed,
        the owner closed it, `watch` recorded its exit) ended at a time nobody knows, and another game may have
        started since: a launch moves the logs on, and the follower would read that game's lines as a rotation
        of the run's. Then nothing is read, the logs are closed for good, and a note says so. A game left up is
        not read either, and the logs stay open for the stop that ends it. Never raises."""
        if self._logs_closed or self._debug_log is None or self._error_log is None:
            return
        if self._ended_alive:
            try:
                self._new_lines(ended_here=True)
            except Exception:
                pass                            # the copy is a convenience
            self._logs_closed = True
            return
        self._logs_closed = not left_up
        note = ("the game's log was not read at this stop: %s. Self-check lines the game logged after the last "
                "verb are not in the summary" % (
                    "the game was left up, and its log is read by the stop that ends it" if left_up else
                    "the game had ended before the stop came to end it, so another game may have written `logs/` "
                    "since"))
        if note not in notes:
            notes.append(note)

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
            raise SessionError("no_country", "tag a country first: the click enters whichever country the camera is "
                               "on, and the tagged one is tagged again once the game is entered")
        clicks: list[list[int]] = []
        # The game in front first (the console's own check, as before each click): a screenshot of the screen
        # with another window over the game would be that window, and any later look would differ from it.
        self._console.ensure_open()
        unselected = self._panel()              # the side panel with no country selected, or None: cannot tell
        self._click(COUNTRY_CLICK, clicks)
        self._sleep(CLICK_SETTLE_S)
        if unselected is not None:
            now = self._panel()
            if now is not None and pixels.changed(unselected, now) < PANEL_CHANGED:
                # Start is not clicked on a lobby with no country: nothing was entered, nothing is left in doubt,
                # and the session can go on (a refused click after Start would end `advance` for good).
                raise SessionError(
                    "no_country_selected", "the country click selected no country: the lobby's side panel did "
                    "not change. Something covers the middle of the country-select screen (a setup that changes "
                    "a law there raises the game's \"We now have …\" window, #1598), or the camera is not on a "
                    "country. Start was not clicked, so nothing changed and enter-game can be tried again; no "
                    "verb closes that window, so run such a setup after entering",
                    clicks=clicks, screenshot=self._enter_shot_path())
        self._click(START_CLICK, clicks)
        # Start may have been pressed: from here on the game may be entered, and running. Nothing is clicked again.
        try:
            self._sleep(ENTER_SETTLE_S)
            self._console_after_start()
            self._attach("reattach")
            with self._step("tag", tag=self._country):
                self._tag(self._country)    # the click entered the country the camera was on (live: DEN, not FRA)
            before = self._date()
            after = self._run_for(PROOF_S)
        except BaseException as e:
            self._left_running = True
            self._entered_unproved = True
            if not isinstance(e, Exception):
                raise
            raise self._after_start_error(e, clicks) from e
        if _game_day(after) <= _game_day(before):
            try:
                shot = str(self._shot())
            except Exception as e:
                shot = "the screenshot failed: %s" % e
            raise SessionError("not_entered", "the date stayed at %s while unpaused for %g s" % (before, PROOF_S),
                               screenshot=shot, before=before, after=after, clicks=clicks)
        self._entered = True
        return {"entered": True, "clicks": clicks, "before": before, "after": after}

    def _click(self, where: tuple[float, float], clicks: list[list[int]]) -> None:
        # The console's own front check, so the presence rule decides whether the foreground may be taken.
        self._console.ensure_open()
        x, y = self._point(where)
        try:
            self._sends.click(self._proc.pid, x, y)
        except HelperError as e:            # refused before the button went down: nothing was pressed
            raise SessionError("click_refused", "%s: %s" % (e.code, e.detail), clicks=clicks) from e
        clicks.append([x, y])

    def _enter_shot_path(self) -> str:
        return str(self._report.dir / "enter_panel.png") if self._report is not None else ""

    def _panel(self) -> tuple[int, int, bytes] | None:
        """The country-select screen's side panel as it looks now (PANEL_BOX of a screenshot kept as
        `enter_panel.png` in the run folder), or None when it cannot be had: a screenshot that fails or cannot
        be read is not a reason to stop entering, only to go on without the check."""
        if self._report is None:
            return None
        path = self._report.dir / "enter_panel.png"
        try:
            self._helper.screenshot(self._proc.pid, path)
            return pixels.region(pixels.decode_png(path.read_bytes()), PANEL_BOX)
        except (HelperError, OSError, pixels.PixelsError) as e:
            self._record("enter_panel", outcome="unread", detail=str(e)[:200])
            return None

    def _console_after_start(self) -> None:
        """Wait for the console to take commands again once Start is pressed: `ensure_open` is tried every
        ENTER_RETRY_S while it refuses for a reason in ENTER_RETRIED, until ENTER_WAIT_S has passed; any other
        error is raised at once, and `watch` is looked at before each retry, so a game that ended stops the tries.
        Recorded as the step `console_after_start`, with the tries made."""
        deadline = self._clock() + ENTER_WAIT_S
        with self._step("console_after_start") as out:
            tries = 0
            while True:
                tries += 1
                out["tries"] = tries
                try:
                    self._console.ensure_open()
                    return
                except ConsoleError as e:
                    if e.code not in ENTER_RETRIED or self._clock() + ENTER_RETRY_S > deadline:
                        raise
                self._sleep(ENTER_RETRY_S)
                self._check_watch()

    def _after_start_error(self, e: Exception, clicks: list[list[int]]) -> SessionError:
        """What a failure after the Start click raises: its own code when it says more (ENTER_KEPT), else
        not_entered with the code as `cause`; with the clicks, and the warning that nothing proved the game in
        play or not."""
        code = _code_of(e)
        info = dict(e.info) if isinstance(e, SessionError) else {}
        info["clicks"] = clicks
        if isinstance(e, ConsoleError):
            info["entered"] = e.entered
        warning = ("Start was clicked before this, so the game may be entered and running unpaused (nothing proved "
                   "it either way); enter_game and advance are refused until stop")
        if isinstance(e, SessionError) and code in ENTER_KEPT:
            detail = e.detail if code == "left_running" else "%s. %s" % (e.detail, warning)
            return SessionError(code, detail, **info)       # left_running keeps the `cause` _run_for gave it
        info["cause"] = code
        return SessionError("not_entered", "after the clicks, %s. %s" % (_describe(e), warning), **info)

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

    def _shot(self, max_width: int | None = None) -> Path:
        self._shots += 1
        path = self._report.dir / ("shot_%02d.png" % self._shots)
        if max_width is None:
            return self._helper.screenshot(self._proc.pid, path)
        return self._helper.screenshot(self._proc.pid, path, max_width=max_width)

    # ---- plumbing

    def _require_game(self, types: bool = True, keyboard: bool = True) -> None:
        """Before any verb: the session is running and watched, and the game is not left stopped at the
        breakpoint. When it may be (`_maybe_stopped`) the stop is drained first; otherwise a verb that `types`
        (or clicks) still takes one look, without waiting, for a stop the game made since the last verb (a read's
        own command run once the game was resumed) and releases it: a frozen game takes no key, and the keys
        would run later. A verb that types (`keyboard`: all but `click`) is then refused `keyboard_away` while a
        click may have taken the keyboard, before it types or writes anything (`Console` refuses the keys too)."""
        if self._stopped is not None or self._stopping:
            raise SessionError("stopped", "this session's game has been stopped")
        if not self._ready:
            raise SessionError("not_started", "start() has not finished")
        self._check_watch()
        if self._maybe_stopped:
            self._drain()
        elif types:
            self._release_pending()
        if types and keyboard and self._console is not None and self._console.keyboard_away:
            raise SessionError("keyboard_away", KEYBOARD_AWAY, keyboard_away=True,
                               next="python3 -m game_qa click --console")

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
        self._notes.append("watch returned at %s without recording an exit, with the game proved alive by its pid "
                           "and start time, and was run again at once" % stamp(utc_now()))
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


def _clears_by_waiting(restore: Mapping | None) -> bool:
    """Whether a refused restore can end otherwise when run again later (RESTORE_WAITS)."""
    return isinstance(restore, Mapping) and restore.get("refused") in RESTORE_WAITS


def _describe(e: BaseException) -> str:
    """An error as `code: detail`, its code said once."""
    if isinstance(e, HelperError):
        return "helper: %s" % e
    if isinstance(e, (SessionError, ConsoleError)):
        return str(e)
    return "%s: %s" % (_code_of(e), e)


def _text(value) -> str:
    return " ".join(str(value).split())


def _fraction(name: str, value) -> float:
    """A click's coordinate: a fraction of the client area, at least 0 and below 1."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value < 1:
        raise SessionError("bad_argument", "%s is a fraction of the window, at least 0 and below 1, not %r"
                           % (name, value))
    return float(value)


def _box(box) -> tuple[float, float, float, float]:
    """A crop's box: left, top, right, bottom, fractions of the client area, left below right and top below bottom."""
    if isinstance(box, (str, bytes)) or not isinstance(box, Sequence) or len(box) != 4:
        raise SessionError("bad_argument", "a box is four fractions of the window (left top right bottom), not %r"
                           % (box,))
    for name, value in zip(("left", "top", "right", "bottom"), box):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise SessionError("bad_argument", "the box's %s is a fraction of the window from 0 to 1, not %r"
                               % (name, value))
    left, top, right, bottom = (float(value) for value in box)
    if not (left < right and top < bottom):
        raise SessionError("bad_argument", "a box's left is below its right and its top below its bottom: %r"
                           % (box,))
    return left, top, right, bottom


def _pair(name: str, value) -> tuple[float, float]:
    """A point given as two fractions of the client area (x, y)."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 2:
        raise SessionError("bad_argument", "%s is two fractions of the window (x y), not %r" % (name, value))
    return _fraction(name + "'s x", value[0]), _fraction(name + "'s y", value[1])


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
