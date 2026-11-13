"""game_qa/session.py: one game's life, from start to restore.

No game and no Windows program is needed. `Game` is `fakes.FakeHelper` plus the parts of the game the session
drives: the read event stopping at the debugger's breakpoint and logging the date once resumed, `tag`, the
country-select screen and its two clicks, the pause key, and time passing while unpaused. `Adapter` is the
game's side of the debugger, reached through the helper's relay as in the real harness. `Cli` stands in for
`python3 -m game_qa` and `Watch` for the `watch` subprocess. Every wait runs on the fake's one clock, except
the debugger client's own, which the fakes answer at once.
"""
import contextlib
import datetime as dt
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game_qa import __main__ as cli
from game_qa import dap, fakes, fixture, gate, logtail, overlay, server, session, snapshot
from game_qa.client import enabled_mods
from game_qa.console import UNRESPONSIVE_S, ConsoleError
from game_qa.gate import ProcId
from game_qa.helper import HelperError

SNAP = "20261110T150000Z"
FIXTURE_SNAP = "20261110T145500Z"
PID, CREATED = 7, "2026-11-10T14:00:00.0000000Z"
OVERLAY_WIN = r"C:\Users\someone\Documents\Paradox Interactive\Victoria 3\mod\te_qa_overlay"
DEPLOYED_WIN = r"C:\Users\someone\mod\Vic3TimelineExtended"
OTHER_MOD_WIN = r"C:\Users\someone\mod\SomeoneElsesMod"
FIXTURE_GAME = ProcId(9, "2026-11-10T14:55:05.0000000Z")
EVENTS_WIN = OVERLAY_WIN + r"\events\te_qa_events.txt"
PERMISSION = "the owner granted launches for this session"
SPACE = 0x39
START_DATE = dt.date(1836, 1, 11)
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
STOPPED = {"type": "event", "event": "stopped", "body": {"reason": "breakpoint", "threadId": 1}}
RESTORED = ({"restored": ["content_load.json", "console_history.txt"], "removed": [], "held": False, "reason": ""}, 0)
HELD = ({"restored": [], "removed": [], "held": True, "reason": "other_game_ran"}, 2)


class Adapter:
    """The game's debug adapter: it answers the session's requests, and the game calls `stop` when it passes the
    breakpoint. A `continue` lets the game finish the read event (`Game.finish_read`)."""

    def __init__(self, game):
        self.game = game
        self.requests: list[dict] = []
        self.breakpoints: dict[str, list[int]] = {}
        self.verified = True
        self.values: dict[str, str] = {}
        self.stopped = False
        self.burst: list[str] = []              # what each evaluation makes the validator write ({n}: its number)
        self.burst_lag = False                  # error.log gets each burst only at the next evaluation
        self.stop_reason = "breakpoint"         # the reason the game's stops give
        self.failing_continues = 0              # this many `continue` requests are lost on the way (a broken relay)
        self._evaluations = 0
        self._late: list[str] = []
        self._decoder = dap.Decoder()
        self._out = b""
        self._seq = 0

    @property
    def commands(self) -> list[str]:
        return [r["command"] for r in self.requests]

    def reset_connection(self) -> None:
        """The relay was closed: what the old connection had not delivered is gone, and the next one starts afresh
        (a new client numbers its requests from 1 again)."""
        self._decoder = dap.Decoder()
        self._out = b""
        self._seq = 0

    def send(self, data: bytes) -> None:
        for req in self._decoder.feed(data):
            self.requests.append(req)
            if req["command"] == "continue" and self.failing_continues:
                self.failing_continues -= 1
                raise OSError("the relay dropped the request")
            self._answer(req)

    def recv(self, timeout: float) -> bytes:
        data, self._out = self._out, b""
        return data

    def push(self, msg: dict) -> None:
        self._seq += 1
        self._out += dap.encode(dict(msg, seq=self._seq))

    def stop(self, reason: str | None = None) -> None:
        self.stopped = True
        self.push(dict(STOPPED, body=dict(STOPPED["body"], reason=reason or self.stop_reason)))

    def output(self, text: str) -> None:
        """An error-log line streamed to the debugger, as the bare message (debugger_transcript.txt:51-53)."""
        self.push({"type": "event", "event": "output", "body": {"category": "stderr", "output": text + "\n"}})

    def _answer(self, req: dict) -> None:
        command, args = req["command"], req.get("arguments") or {}
        success, body, message, resumed = True, {}, "", False
        if command == "setBreakpoints":
            lines = [b["line"] for b in args["breakpoints"]]
            self.breakpoints[args["source"]["path"]] = lines
            body = {"breakpoints": [{"verified": self.verified, "line": n} for n in lines]}
        elif command == "evaluate":
            expr = args["expression"]
            if self.stopped:                    # streamed before the answer, as live; written to error.log too
                lines = [line.format(n=self._evaluations) for line in self.burst]
                self._evaluations += 1
                for line in lines:
                    self.output(line)
                late, self._late = self._late, lines
                for line in late if self.burst_lag else lines:
                    self.game.error(line)
            if not self.stopped:
                success, message = False, "not stopped"
            elif expr in self.values:
                body = {"result": self.values[expr]}
            else:
                success, message = False, "not a valid trigger or script value"
        elif command == "continue":
            if self.stopped:
                self.stopped, resumed = False, True
            else:
                success, message = False, "not stopped"
        reply = {"type": "response", "request_seq": req["seq"], "command": command, "success": success, "body": body}
        if message:
            reply["message"] = message
        self.push(reply)
        if resumed:
            self.push({"type": "event", "event": "continued", "body": {"threadId": 1}})
            self.game.finish_read()


class Game(fakes.FakeHelper):
    """`FakeHelper` with the game behind it. `order` is the shared log of what happened, for the order tests."""

    def __init__(self, user_data: Path, order: list):
        logs = user_data / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        super().__init__(history=user_data / "console_history.txt", log=logs / "debug.log")
        self.order = order
        self.adapter = Adapter(self)
        self.played: str | None = None
        self.camera = "DEN"                     # the country the country click lands on, whatever was tagged (live)
        self.selected: str | None = None        # the country selected on the country-select screen
        self.entered = False                    # Start was pressed: time can pass
        self.paused = True
        self.clicks_work = True
        self.days_per_second = 1.5
        self.elapsed = 0.0                      # game days since START_DATE
        self.stops = True                       # the read event stops at a breakpoint set on its line
        self.exited = False                     # the game ended by itself
        self.process_gone = False               # no live process has the game's pid and start time: adopt refuses
        self.tcp_error: Exception | None = None
        self.tcp_open_refusal: HelperError | None = None       # what tcp_open raises, while set
        self.closed = False
        self.setups: dict[str, tuple[str, list[str]]] = {}     # setup event -> (its name, the lines its body logs)
        self.on_command = None                  # called with each command the game runs, before it answers
        self.on_sleep = None                    # called with each sleep's seconds, before the time passes
        self.dropped_pauses = 0                 # this many pause keys (space, the game running) are lost
        self.logs_date = True                   # the read event logs its date line once resumed
        self.error_log = logs / "error.log"
        # The game reloads the overlay's effects file `reload_s` after it changes on disk. Live (2026-11-12) that
        # took about 90 s and the window did not respond for all of it (`freezes`); the probes of 2026-11-10 saw
        # console commands entered meanwhile dropped, which is what happens here with `freezes` off. The reload
        # drops the breakpoint.
        self.effects_file = user_data / "mod" / overlay.OVERLAY_NAME / overlay.EFFECTS_FILE
        self.reloads = True
        self.reload_s = 90.0
        self.freezes = True
        self.stops_after_reload = True          # the reload ends with the game stopped at the debugger
        self.law_windows = 0                    # "We now have <law>!" windows over the country-select screen
        self.bare_esc = 0                       # Esc presses with no such window to close
        self.panel_shots = True                 # a screenshot shows the lobby's side panel (else 1x1, unreadable)
        self.reload_stopped = False             # it is at that stop: its window does not respond
        self.loaded_revision = 0                # the revision of te_qa_effects.txt in force
        self.reload_due: tuple[float, int] | None = None       # (when, the revision it brings)
        self.dropped: list[str] = []            # the commands entered during a reload
        self.on("tag FRA", success=["Now Playing - France"])

    def error(self, message: str, streamed: bool = False) -> None:
        """An error the game writes to error.log (each line of `message`; the first with the log's prefix) and,
        when `streamed`, sends the debugger too, as it does every error-log line (spec § 3.5)."""
        first, *rest = message.split("\n")
        clock = int(self.now)
        with open(self.error_log, "a", encoding="utf-8", newline="\n") as f:
            f.write("[%02d:%02d:%02d][jomini_script_system.cpp:247]: %s\n" % (12, clock // 60 % 60, clock % 60, first))
            f.write("".join(line + "\n" for line in rest))
        if streamed:
            self.adapter.output(message)

    @property
    def date(self) -> dt.date:
        return START_DATE + dt.timedelta(days=int(self.elapsed))

    def sleep(self, seconds: float) -> None:
        if self.on_sleep is not None:
            self.on_sleep(seconds)
        if self.entered and not self.paused:
            self.elapsed += seconds * self.days_per_second
        super().sleep(seconds)
        self._reload_tick()

    def _reload_tick(self) -> None:
        try:
            found = re.search(r"TE_QA overlay rev (\d+)", self.effects_file.read_text(encoding="utf-8-sig"))
        except OSError:
            found = None
        on_disk = int(found.group(1)) if found else self.loaded_revision
        if self.reloads and on_disk != self.loaded_revision and (self.reload_due or (0, None))[1] != on_disk:
            self.reload_due = (self.now + self.reload_s, on_disk)
        if self.reload_due is not None and self.now >= self.reload_due[0]:
            self.loaded_revision, self.reload_due = self.reload_due[1], None
            self.adapter.breakpoints.clear()
            if self.stops_after_reload:         # live, 2026-11-12: frozen until the debugger resumes it
                self.adapter.stop("pause")
                self.reload_stopped = True

    def window(self, pid):
        win = super().window(pid)
        frozen = self.freezes and self.reload_due is not None
        self.reload_stopped = self.reload_stopped and self.adapter.stopped
        if (frozen or self.reload_stopped) and win.exists:
            return type(win)(win.exists, win.foreground, False, win.title, win.client)
        return win

    def _enter(self) -> None:
        if self.reload_due is not None and self.console_open and self.typed:
            self.dropped.append(self.typed)     # "You can't add new commands while the console is still running"
            self.typed = ""
            return
        super()._enter()

    def keys(self, pid, steps):
        super().keys(pid, steps)
        for step in steps:
            if step.get("scan") == 1 and not self.console_open:
                if self.law_windows:
                    self.law_windows -= 1
                else:
                    self.bare_esc += 1
            if step.get("scan") == SPACE:
                self.order.append("space")
                if not self.console_open:
                    if not self.paused and self.dropped_pauses:
                        self.dropped_pauses -= 1
                        continue
                    self.paused = not self.paused

    def screenshot(self, pid, path, max_width=1600):
        """A small picture of the country-select screen: the side panel on the right is dark until a country is
        selected, and a law window sits in the middle while one is up."""
        if not self.panel_shots:
            return super().screenshot(pid, path, max_width)
        width, height = 100, 60
        rows = []
        for y in range(height):
            for x in range(width):
                if x >= 85:
                    rows.append(bytes((120, 90, 60)) if self.selected and 10 <= y < 40 else bytes((30, 30, 30)))
                elif self.law_windows and 36 <= x < 64 and 15 <= y < 45:
                    rows.append(bytes((80, 20, 20)))
                else:
                    rows.append(bytes((10, 40, 90)))
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fakes.win_helper.encode_png(width, height, b"".join(rows)))
        self.screenshots.append((pid, path, max_width))
        return path

    def click(self, pid, x, y):
        super().click(pid, x, y)
        self.order.append("click")
        if not self.clicks_work:
            return
        _left, _top, width, height = self.client
        if abs(x - width * 0.492) < 2 and abs(y - height * 0.656) < 2:
            if self.law_windows:                # the click lands on the window, not on the map
                return
            self.selected = self.camera
        elif abs(x - width * 0.9216) < 2 and abs(y - height * 0.975) < 2 and self.selected:
            # As live (2026-11-11): the game is the selected country's, the script reloads and drops the
            # debugger's breakpoint, and the console is shut while the game loads.
            self.entered = True
            self.played = self.selected
            self.adapter.breakpoints.clear()
            self.console_open = False

    def adopt(self, proc):
        if self.process_gone:                   # as win_helper._op_adopt: the creation time is compared
            raise HelperError("not_ours", "no live process %d was created at %s" % (proc.pid, proc.created))
        super().adopt(proc)
        self.order.append("adopt")

    def kill(self, proc):
        self.order.append("kill")
        if self.exited:                         # as win_helper._op_kill: a process that ended has nothing to end
            self.exists = False
        return super().kill(proc)

    def tcp_open(self, port):
        if self.tcp_open_refusal is not None:   # as win_helper._op_tcp_open: the old connection is closed first
            super().tcp_close()
            raise self.tcp_open_refusal
        super().tcp_open(port)
        self.adapter.reset_connection()         # win_helper._op_tcp_open closes any connection first
        self.order.append("tcp_open %d" % port)

    def tcp_send(self, data):
        if self.tcp_error is not None:
            raise self.tcp_error
        self._relay()
        self.adapter.send(data)

    def tcp_recv(self, timeout):
        if self.tcp_error is not None:
            raise self.tcp_error
        self._relay()
        return self.adapter.recv(timeout)

    def _relay(self) -> None:
        if self.tcp_port is None:               # as win_helper._open_socket
            raise HelperError("not_open", "no TCP connection is open")

    def tcp_close(self):
        super().tcp_close()
        self.adapter.reset_connection()
        self.order.append("tcp_close")

    def close(self):
        self.closed = True
        self.order.append("helper_close")

    def _run(self, text):
        if self.on_command is not None:
            self.on_command(text)
        super()._run(text)
        if text.startswith("tag "):
            self.played = text[4:].strip()
        if text == "event " + overlay.READ_EVENT:
            if self.stops and EVENTS_WIN in self.adapter.breakpoints:
                self.adapter.stop()
            else:
                self.finish_read()
        elif text == "event " + overlay.LOADED_EVENT:
            self.script("TE_QA overlay rev %d" % self.loaded_revision)
            self.pad()
        elif text.startswith("event te_qa.") and int(text[12:]) >= overlay.FIRST_SLOT_EVENT:
            slot = int(text[12:]) - overlay.FIRST_SLOT_EVENT
            if self.loaded_revision > slot and text[6:] in self.setups:     # the slot's body is in force
                name, lines = self.setups[text[6:]]
                self.script("TE_QA setup %s start" % name, *lines, "TE_QA setup %s done" % name)
            else:
                self.script("TE_QA slot %d is empty" % slot)
            self.pad()
        elif text.startswith("event ") and text[6:] in self.setups:
            name, lines = self.setups[text[6:]]
            self.script("TE_QA setup %s start" % name, *lines, "TE_QA setup %s done" % name)
            self.pad()

    def script(self, *lines: str) -> None:
        for line in lines:
            self._logged("jomini_effect_impl.cpp:459", "events/te_qa_events.txt:12: " + line)

    def finish_read(self) -> None:
        """The rest of the read event: its debug_log line, then the padding that flushes the log."""
        when = self.date
        if self.logs_date:
            self.script("TE_QA read country=%s date=%s %d, %d" % (self.played or "", MONTHS[when.month - 1],
                                                                 when.day, when.year))
        self.pad()

    def pad(self) -> None:
        for _ in range(overlay.PAD_LINES):
            self._logged("jomini_effect_impl.cpp:459", "common/scripted_effects/te_qa_effects.txt:5: TE_QA PAD x")
        out, self.unwritten = self.unwritten[:-5], self.unwritten[-5:]
        with open(self.log, "a", encoding="utf-8", newline="\n") as f:
            f.write("".join(line + "\n" for line in out))


class FixtureWatch:
    """The fixture run's `watch`: the unattended game writes its save and quits by itself (-run_until), so by
    default it returns 0 at its first look. With `code` 2 it stopped without recording the exit (as for a launch
    that recorded no `started`); with `hangs` it follows a game that never quits, until that game is ended."""

    def __init__(self, test):
        self.test = test
        self.code = test.fixture_watch_code
        self.hangs = test.fixture_watch_hangs
        self.polls = 0
        self.saved = False

    def poll(self):
        self.polls += 1
        on_poll = getattr(self.test, "on_fixture_poll", None)       # a dated run writes its logs as it goes
        if on_poll is not None and on_poll(self.polls) is False:
            return None
        if self.hangs:
            return 0 if self.test.game.killed else None
        if self.code == 0 and self.polls == 1 or on_poll is not None and self.code == 0:
            name = getattr(self.test, "fixture_run_save", "TEST_FAIL_te_qa_fixture_2 January, 1836.v3")
            data = getattr(self.test, "fixture_run_bytes", b"a fresh game")
            if not (self.test.user / "save games" / name).exists() and not self.saved:
                (self.test.user / "save games" / name).write_bytes(data)
                self.saved = True
        return self.code


class Watch:
    """The `watch` subprocess: it returns once the game is gone (ended by the helper, or exited), unless it hangs."""

    def __init__(self, game: Game, order: list):
        self.game, self.order = game, order
        self.hangs = False
        self.dies = False                       # it ends while the game is still up
        self.returned = False

    def poll(self):
        if self.dies:
            return 1
        if self.hangs or not (self.game.killed or self.game.exited):
            return None
        if not self.returned:
            self.returned = True
            self.order.append("watch_returned")
        return 0

    def wait(self, timeout):
        code = self.poll()
        if code is None:
            raise subprocess.TimeoutExpired("watch", timeout)
        return code


class Cli:
    """`python3 -m game_qa <argv>`: records each call and answers from what the test queued, then the defaults.

    `restore` removes the saves a run made, as the real one does, and notes whether the overlay was still there.
    (`watch` is never called through here: the session and the fixture both spawn it.)"""

    def __init__(self, test):
        self.test = test
        self.calls: list[list[str]] = []
        self.queued: dict[str, list[tuple[dict, int]]] = {}
        self.raise_on: str | None = None
        self.on_call = None                     # called with each argv before it is answered
        self.overlay_at_restore: list[bool] = []
        self.clock_at: dict[str, float] = {}

    @property
    def verbs(self) -> list[str]:
        return [c[0] for c in self.calls]

    def queue(self, verb: str, reply: dict, code: int) -> None:
        self.queued.setdefault(verb, []).append((reply, code))

    def __call__(self, argv):
        argv = list(argv)
        verb = argv[0]
        self.calls.append(argv)
        self.test.order.append("cli " + verb)
        self.clock_at[verb] = self.test.game.now
        if self.on_call is not None:
            self.on_call(argv)
        if verb == self.raise_on:
            raise OSError("python3 could not be started")
        saves = self.test.user / "save games"
        if verb == "restore":
            self.overlay_at_restore.append(self.test.paths.overlay_dir.exists())
            for path in saves.glob("TEST_FAIL_*.v3"):
                path.unlink()
        queued = self.queued.get(verb)
        if queued:
            return queued.pop(0)
        return {
            "held": ({"held": []}, 0),
            "snapshot": ({"id": SNAP, "files": 12, "pruned": [], "held": []}, 0),
            "launch": ({"id": SNAP, "pid": PID, "created": CREATED, "args": []}, 0),
            "restore": RESTORED,
        }[verb]


class SessionTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.user = base / "user data"
        (self.user / "mod").mkdir(parents=True)
        (self.user / "save games").mkdir()
        deploy = base / "deploy"
        (deploy / "events").mkdir(parents=True)
        (deploy / "events" / "te_events.txt").write_text("namespace = te\n", encoding="utf-8")
        (base / "backups").mkdir()
        self.windows_paths_asked: list[Path] = []
        self.paths = session.Paths(
            user_data=self.user, backup_root=base / "backups", deploy_dir=deploy, base_game=base / "game",
            overlay_windows_path=OVERLAY_WIN, events_file_windows_path=self.windows_path, game_version="1.15.0",
            enabled_mods=[DEPLOYED_WIN, OTHER_MOD_WIN], deployed_mod_windows_path=DEPLOYED_WIN)
        # mod_only: the deployed mod alone, then the overlay (what `launch --playset mod_only --add-mod` writes)
        self.key = fixture.key(self.paths.game_version, [DEPLOYED_WIN, OVERLAY_WIN], deploy, playset="mod_only")
        self.fixture_save = self.user / "save games" / ("te_qa_fixture_%s.v3" % self.key)
        self.fixture_save.write_bytes(b"a fresh game")
        self.order: list[str] = []
        self.game = Game(self.user, self.order)
        self.cli = Cli(self)
        self.watches: list[Watch] = []
        self.fixture_watches: list[FixtureWatch] = []
        self.fixture_snaps = {FIXTURE_SNAP}     # the snapshots the fixture's run takes: its watch is a FixtureWatch
        self.fixture_watch_code = 0
        self.fixture_watch_hangs = False
        self.spawn_error: Exception | None = None
        self.fresh_helper: fakes.FakeHelper | None = None     # what the helper factory hands out, if anything
        # The drain before each read waits on the debugger client's own clock (real seconds): keep it short here.
        patcher = mock.patch.object(session, "DRAIN_S", 0.005)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.session = session.Session(self.game, self.cli, self.spawn_watch, self.paths,
                                       sleep=self.game.sleep, clock=self.game.clock, helper_factory=self.new_helper)

    def new_helper(self) -> fakes.FakeHelper:
        if self.fresh_helper is None:
            raise HelperError("helper_gone", "no Windows python.exe in the tests")
        return self.fresh_helper

    def windows_path(self, path: Path) -> str:
        self.windows_paths_asked.append(Path(path))
        return EVENTS_WIN

    def spawn_watch(self, snapshot_id: str) -> Watch:
        self.order.append("spawn_watch " + snapshot_id)
        self.spawned_at = self.game.now
        if self.spawn_error is not None:
            raise self.spawn_error
        if snapshot_id in self.fixture_snaps:
            fixture_watch = FixtureWatch(self)
            self.fixture_watches.append(fixture_watch)
            return fixture_watch
        watch = Watch(self.game, self.order)
        self.watches.append(watch)
        return watch

    def start(self, **kwargs) -> dict:
        kwargs.setdefault("as_tag", "FRA")
        return self.session.start(PERMISSION, **kwargs)

    def started(self, **kwargs) -> dict:
        """A started session, with the order log and the calls cleared."""
        reply = self.start(**kwargs)
        self.order.clear()
        self.cli.calls.clear()
        return reply

    def typed(self) -> list[str]:
        return [step["text"] for step in self.game.steps if "text" in step]

    def journal_a_start(self, proc: ProcId) -> str:
        """A real snapshot under the backup root whose journal records `proc` as started; its id."""
        snap = snapshot.take(self.user, self.paths.backup_root)
        snapshot.record(snap, "armed")
        snapshot.record(snap, "started", pid=proc.pid, created=proc.created, args=[])
        return snap.id

    def session_error(self, fn, *args, **kwargs) -> session.SessionError:
        with self.assertRaises(session.SessionError) as caught:
            fn(*args, **kwargs)
        return caught.exception


class StartTest(SessionTestCase):
    def test_start_runs_the_verbs_in_order_and_watch_at_once(self):
        reply = self.start()
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch"])
        save = "te_qa_fixture_" + self.key
        self.assertEqual(self.cli.calls[1], ["snapshot", "--save", save])
        self.assertEqual(self.cli.calls[2], [
            "launch", SNAP, "--permission", PERMISSION, "--playset", "mod_only", "--add-mod", OVERLAY_WIN,
            "--", "-gdpr-compliant", "-debug_mode", "-script_debugger", "-loadsave=" + save])
        # watch is spawned the moment launch returns, before the helper is asked anything
        self.assertEqual(self.order[:5], ["cli held", "cli snapshot", "cli launch", "spawn_watch " + SNAP, "adopt"])
        self.assertEqual(self.spawned_at, self.cli.clock_at["launch"])
        self.assertEqual(set(self.game.adopted), {self.game.proc})       # and again before each key (X1)
        self.assertIn("tcp_open 6111", self.order)
        # the overlay was there before the snapshot, so the run's playset can name it
        self.assertTrue((self.paths.overlay_dir / ".metadata" / "metadata.json").is_file())
        # the console was opened and the country tagged before the debugger was attached
        self.assertIn("tag FRA", self.typed())
        self.assertEqual(self.game.played, "FRA")
        self.assertEqual(self.game.adapter.commands, ["initialize", "launch", "setBreakpoints", "configurationDone"])
        read_line = reply["overlay"]["read_line"]
        self.assertEqual(self.game.adapter.breakpoints, {EVENTS_WIN: [read_line]})
        self.assertEqual(self.windows_paths_asked, [self.paths.overlay_dir / "events" / "te_qa_events.txt"])
        events = (self.paths.overlay_dir / "events" / "te_qa_events.txt").read_text("utf-8-sig").split("\n")
        self.assertIn("TE_QA read", events[read_line - 1])
        self.assertEqual(reply["snapshot"], SNAP)
        self.assertEqual((reply["pid"], reply["created"], reply["save"]), (PID, CREATED, save))
        self.assertEqual((reply["fixture_made"], reply["country"]), (False, "FRA"))
        self.assertEqual(Path(reply["run_dir"]), self.paths.backup_root / "runs" / SNAP)
        self.assertTrue((Path(reply["run_dir"]) / "steps.jsonl").is_file())

    def test_start_makes_the_fixture_when_there_is_none(self):
        self.fixture_save.unlink()
        self.cli.queue("snapshot", {"id": FIXTURE_SNAP}, 0)
        reply = self.start()
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch", "restore", "snapshot", "launch"])
        self.assertEqual(self.order[2:5], ["cli launch", "spawn_watch " + FIXTURE_SNAP, "cli restore"])
        self.assertEqual(self.cli.calls[2][-6:], ["--", *fixture.FIXTURE_ARGS])
        self.assertTrue(reply["fixture_made"])
        self.assertTrue(self.fixture_save.is_file())
        self.assertEqual(self.cli.calls[5][-1], "-loadsave=te_qa_fixture_" + self.key)

    def test_start_with_a_named_save_loads_it_and_snapshots_it(self):
        (self.user / "save games" / "france_1850.v3").write_bytes(b"the owner's own save")
        reply = self.start(save="france_1850.v3")
        self.assertEqual(self.cli.calls[1], ["snapshot", "--save", "france_1850"])
        self.assertEqual(self.cli.calls[2][-1], "-loadsave=france_1850")
        self.assertEqual((reply["save"], reply["fixture_made"]), ("france_1850", False))

    def test_a_window_that_stops_responding_while_the_save_loads_is_waited_for(self):
        # Live 2026-11-12: a 47 MB save of 1931 kept the window from responding past UNRESPONSIVE_S once it had
        # first answered, and one ensure_open took that for a game that had gone.
        loading = {}

        def load(seconds):
            if "until" not in loading:
                loading["until"] = self.game.now + UNRESPONSIVE_S + 30
            self.game.responding = self.game.now >= loading["until"]
        self.game.on_sleep = load
        reply = self.start()
        self.game.on_sleep = None
        self.assertEqual(reply["country"], "FRA")
        lines = (self.paths.backup_root / "runs" / SNAP / "steps.jsonl").read_text("utf-8").splitlines()
        ready = next(step for step in map(json.loads, lines) if step["verb"] == "console_ready")
        self.assertEqual(ready["outcome"], "ok")
        self.assertGreaterEqual(ready["tries"], 2)
        self.assertEqual(ready["last_refusal"], "game_gone")

    def test_a_window_that_never_answers_again_ends_the_start_after_the_load_wait(self):
        def hang(seconds):
            self.game.responding = False
        self.game.on_sleep = hang
        started_at = self.game.now
        error = self.session_error(self.start)
        self.game.on_sleep = None
        self.assertEqual(error.code, "game_gone")
        self.assertGreaterEqual(self.game.now - started_at, session.LOAD_WAIT_S - session.ENTER_RETRY_S)
        self.assertLessEqual(self.game.now - started_at, session.LOAD_WAIT_S + session.CONSOLE_READY_S)
        self.assertEqual(error.info["stop"]["outcome"], "restored")

    def _console_ready(self):
        lines = (self.paths.backup_root / "runs" / SNAP / "steps.jsonl").read_text("utf-8").splitlines()
        return next(step for step in map(json.loads, lines) if step["verb"] == "console_ready")

    def test_a_game_that_ends_while_its_save_loads_stops_the_wait_at_once(self):
        # Once the window is gone, ensure_open answers game_gone before any key, so only the loop's own look at
        # `watch` ends the wait: without it the start would press on for LOAD_WAIT_S against a dead game.
        began = {}

        def ends(seconds):
            began.setdefault("at", self.game.now)
            if self.game.now - began["at"] > 3:
                self.game.exited = True
                self.game.exists = False
        self.game.on_sleep = ends
        started_at = self.game.now
        error = self.session_error(self.start)
        self.game.on_sleep = None
        self.assertEqual(error.code, "watch_ended")
        self.assertLess(self.game.now - started_at, session.LOAD_WAIT_S / 4)
        self.assertEqual(error.info["stop"]["outcome"], "restored")

    def test_a_stop_asked_while_the_save_loads_ends_the_wait(self):
        inner = []

        def hang(seconds):
            self.game.responding = False
            if seconds == session.ENTER_RETRY_S and not inner:
                inner.append(self.session.stop())
        self.game.on_sleep = hang
        started_at = self.game.now
        error = self.session_error(self.start)
        self.game.on_sleep = None
        self.assertEqual((error.code, inner[0]["outcome"]), ("stopped", "deferred_to_start"))
        self.assertLess(self.game.now - started_at, session.LOAD_WAIT_S / 2)
        self.assertEqual(self._console_ready()["tries"], 1)
        self.assertEqual(error.info["stop"]["outcome"], "restored")

    def test_someone_at_the_machine_while_the_save_loads_is_not_retried(self):
        self.game.foreground = False

        def someone(reading):
            self.game.cursor = (10 * reading, 5 * reading)
        self.game.on_presence = someone
        error = self.session_error(self.start)
        self.assertEqual(error.code, "not_foreground")
        self.assertEqual(self._console_ready()["tries"], 1)
        self.assertEqual(error.info["stop"]["outcome"], "restored")

    def test_a_console_that_never_opens_is_tried_twice_not_for_the_whole_wait(self):
        self.game.console_never_opens = True
        error = self.session_error(self.start)
        self.assertEqual(error.code, "no_ack")
        self.assertEqual(self._console_ready()["tries"], session.LOAD_NO_ACK_TRIES)

    def test_a_save_that_is_not_there_is_refused_before_anything(self):
        error = self.session_error(self.start, save="nowhere")
        self.assertEqual(error.code, "no_save")
        self.assertEqual(self.cli.verbs, [])
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_start_refuses_while_a_snapshot_is_held(self):
        self.cli.queue("held", {"held": ["20261109T100000Z"]}, 0)
        error = self.session_error(self.start)
        self.assertEqual(error.code, "held_snapshot")
        self.assertIn("20261109T100000Z", error.detail)
        self.assertEqual(self.cli.verbs, ["held"])
        self.assertFalse(self.paths.overlay_dir.exists())      # built only once `held` has answered none
        self.cli.calls.clear()                  # the owner resolves the hold; the same session may start then
        self.assertEqual(self.start()["snapshot"], SNAP)
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch"])

    def test_an_overlay_left_by_an_earlier_run_is_refused_before_anything(self):
        # An earlier run's playset may still name it, so it is neither replaced nor removed here.
        earlier = overlay.build(self.paths.overlay_dir, {"old": "set_variable = x"}, "1.15.0")
        before = sorted(p.relative_to(earlier.dir).as_posix() for p in earlier.dir.rglob("*"))
        error = self.session_error(self.start)
        self.assertEqual(error.code, "overlay_left")
        self.assertIn("recover", error.detail)
        self.assertIn("`python3 -m game_qa remove-overlay`", error.detail)      # R4: a verb, never "by hand"
        self.assertEqual(self.cli.calls, [])
        self.session.stop()
        self.assertEqual(sorted(p.relative_to(earlier.dir).as_posix() for p in earlier.dir.rglob("*")), before)
        self.assertEqual(self.cli.calls, [])
        overlay.remove(earlier.dir)             # once it is gone, the same session may start
        self.assertEqual(self.start()["snapshot"], SNAP)

    def test_a_held_list_that_cannot_be_read_is_refused_too(self):
        self.cli.queue("held", {"refused": "BackupRootError", "detail": "no backup root"}, 2)
        self.assertEqual(self.session_error(self.start).code, "held_unknown")
        self.assertEqual(self.cli.verbs, ["held"])
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_a_refused_snapshot_starts_nothing_and_removes_the_overlay(self):
        self.cli.queue("snapshot", {"refused": "unfinished_run", "unfinished": ["X"]}, 2)
        error = self.session_error(self.start)
        self.assertEqual(error.code, "snapshot_refused")
        self.assertEqual(error.info["reply"]["refused"], "unfinished_run")
        self.assertEqual(self.cli.verbs, ["held", "snapshot"])
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_a_refused_launch_starts_nothing_else(self):
        self.cli.queue("launch", {"refused": "gpu_busy", "id": SNAP, "detail": "the GPU is at 80% load"}, 2)
        error = self.session_error(self.start)
        self.assertEqual(error.code, "launch_refused")
        self.assertEqual(error.info["reply"]["refused"], "gpu_busy")
        self.assertEqual(self.watches, [])
        self.assertEqual((self.game.adopted, self.game.killed, self.game.steps), ([], [], []))
        self.assertIsNone(self.game.tcp_port)
        self.assertEqual(self.game.adapter.requests, [])
        # the armed snapshot is finished (it would block every later one) and the overlay goes
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch", "restore"])
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertEqual(error.info["stop"]["outcome"], "restored")

    def test_a_failure_after_launch_still_stops_and_restores(self):
        self.game.exists = False                # the window never appears
        error = self.session_error(self.start)
        self.assertEqual(error.code, "no_window")
        self.assertGreaterEqual(self.game.now, session.WINDOW_WAIT_S)
        self.assertEqual(self.game.killed, [self.game.proc])
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch", "restore"])
        self.assertEqual(self.cli.overlay_at_restore, [True])
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertEqual(error.info["stop"]["outcome"], "restored")
        self.assertEqual(self.session.stop(), error.info["stop"])
        self.assertEqual(self.session_error(self.start).code, "already_started")

    def test_a_console_error_after_launch_stops_too(self):
        self.game.console_never_opens = True
        error = self.session_error(self.start)
        self.assertEqual(error.code, "no_ack")
        self.assertEqual(self.game.killed, [self.game.proc])
        self.assertEqual(self.cli.verbs[-1], "restore")

    def test_an_unverified_breakpoint_fails_the_start(self):
        self.game.adapter.verified = False
        self.assertEqual(self.session_error(self.start).code, "breakpoint_unverified")
        self.assertEqual(self.game.killed, [self.game.proc])
        self.assertEqual(self.cli.verbs[-1], "restore")

    def test_a_launch_reply_without_a_start_time_still_gets_its_watch_then_stops(self):
        self.cli.queue("launch", {"id": SNAP, "pid": PID, "created": "unknown"}, 0)
        error = self.session_error(self.start)
        self.assertEqual(error.code, "unknown_start")
        self.assertEqual(len(self.watches), 1)
        # a pid alone may be another game's: nothing is adopted or ended by it, and the game may still be up,
        # so restore is left for later (beside a running game it would hold) and the overlay stays
        self.assertEqual((self.game.adopted, self.game.killed), ([], []))
        stop = error.info["stop"]
        self.assertTrue(any("no start time" in note for note in stop["notes"]))
        self.assertEqual(stop["outcome"], "game_left_up")
        self.assertIn("restore %s" % SNAP, stop["next"])
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch"])
        self.assertTrue(stop["overlay_kept"])
        self.assertTrue(self.paths.overlay_dir.exists())

    def test_a_watch_that_cannot_be_spawned_still_ends_the_game(self):
        self.spawn_error = OSError("python3 could not be started")
        error = self.session_error(self.start)
        self.assertEqual(error.code, "OSError")
        self.assertEqual(self.game.killed, [self.game.proc])         # adopted by launch's record, then ended
        self.assertEqual(self.cli.verbs[-1], "restore")
        self.assertIn("no watch was running", error.info["stop"]["notes"])

    def test_a_session_starts_once(self):
        self.started()
        self.assertEqual(self.session_error(self.start).code, "already_started")
        self.assertEqual(self.cli.calls, [])

    def test_status_says_how_far_the_session_is(self):
        self.assertEqual(self.session.status(), {
            "started": False, "stopped": False, "snapshot": None, "save": None, "country": None, "entered": False,
            "entered_unproved": False, "game": None, "watch_returned": False, "run_dir": None, "maybe_stopped": False,
            "left_running": False, "watch_respawns": 0})
        self.started()
        status = self.session.status()
        self.assertEqual((status["started"], status["snapshot"], status["country"]), (True, SNAP, "FRA"))
        self.assertEqual(status["game"], {"pid": PID, "created": CREATED})
        self.assertEqual(Path(status["run_dir"]), self.paths.backup_root / "runs" / SNAP)
        self.session.stop()
        self.assertEqual((self.session.status()["stopped"], self.session.status()["watch_returned"]), (True, True))
        self.assertEqual(self.cli.calls, [["restore", SNAP]])     # status itself runs nothing


class ReadTest(SessionTestCase):
    def test_read_evaluates_at_the_breakpoint_and_resumes(self):
        self.started()
        self.game.adapter.values = {"c:FRA.gdp": "22625834.0308", "is_player = yes": "yes - Yes: "}
        reads = self.session.read(["c:FRA.gdp", "is_player = yes", "gdp"])
        self.assertEqual([(r.expr, r.ok, r.value) for r in reads],
                         [("c:FRA.gdp", True, 22625834.0308), ("is_player = yes", True, True), ("gdp", False, None)])
        self.assertEqual(reads[2].raw, "not a valid trigger or script value")
        self.assertEqual(self.game.adapter.commands[-4:], ["evaluate", "evaluate", "evaluate", "continue"])
        self.assertFalse(self.game.adapter.stopped)
        self.assertEqual(self.typed().count("event te_qa.1"), 1)

    def test_read_without_a_stop_resumes_and_raises(self):
        self.started()
        self.game.stops = False
        with mock.patch.object(session, "STOP_WAIT_S", 0.01):
            error = self.session_error(self.session.read, ["c:FRA.gdp"])
        self.assertEqual(error.code, "no_stop")
        self.assertEqual(self.game.adapter.commands[-1], "continue")
        self.assertNotIn("evaluate", self.game.adapter.commands)
        self.assertEqual(self.typed().count("event te_qa.1"), 1)

    def test_a_closed_relay_is_an_error_of_the_verb_not_a_crash(self):
        self.started()
        self.game.tcp_error = HelperError("tcp_closed", "the peer closed the connection")
        error = self.session_error(self.session.read, ["c:FRA.gdp"])
        self.assertEqual(error.code, "debugger")
        self.assertTrue(error.info["maybe_stopped"])
        self.assertEqual(self.typed().count("event te_qa.1"), 0)         # the drain before it failed: nothing typed
        self.assertEqual(self.session.stop()["outcome"], "restored")

    def test_a_read_that_may_have_been_entered_is_not_typed_again_and_its_stop_is_released(self):
        self.started()
        keys = self.game.keys

        def keys_then_fail(pid, steps):
            keys(pid, steps)                    # the keys went out, the game ran the command and stopped...
            if {"text": "event te_qa.1"} in steps:
                raise HelperError("helper_gone", "the pipe broke")      # ...but the helper could not say so
        self.game.keys = keys_then_fail
        with self.assertRaises(ConsoleError) as caught:
            self.session.read(["c:FRA.gdp"])
        self.assertIsNone(caught.exception.entered)
        self.assertEqual(self.typed().count("event te_qa.1"), 1)
        self.assertFalse(self.game.adapter.stopped)
        self.assertEqual(self.game.adapter.commands[-1], "continue")

    def test_the_console_verb_refuses_the_read_event(self):
        self.started()
        for text in ("event te_qa.1", "event te_qa.1 FRA", "EVENT TE_QA.1", "  event   te_qa.1x", "Event Te_Qa.1 c:FRA"):
            with self.subTest(text=text):
                self.assertEqual(self.session_error(self.session.console, text).code, "use_read")
        self.assertFalse([t for t in self.typed() if "te_qa.1" in t.lower()])

    def test_run_setup_returns_the_lines_between_its_markers(self):
        reply = self.started(setups={"border": "set_variable = te_x"})
        event = reply["overlay"]["setup_events"]["border"]
        self.game.setups = {event: ("border", ["first line", "second line"])}
        self.assertEqual(self.session.run_setup("border"), ["first line", "second line"])
        self.assertEqual(self.session_error(self.session.run_setup, "nothing").code, "unknown_setup")


RULE_FILES = {
    "game/game/common/game_rules/00_rules.txt": "fantasy = {\n\tdefault = allow_fantasy\n\tallow_fantasy = { }\n"
                                                 "\tno_fantasy = { }\n}\n",
    "deploy/common/game_rules/extra.txt": "tax_rule = {\n\tdefault = tax_off\n\ttax_off = { }\n\ttax_light = { }\n}\n",
}


def text_save(settings) -> bytes:
    """A fresh save in the real one's shape (test_game_qa_rules.save_bytes)."""
    listed = (' "" ' + " ".join(settings) + " ").encode()
    meta = b"meta_data={\n\tgame_rules={\n\t\tsettings={" + listed + b"}\n\t}\n}\n"
    state = b"game_rules={\n\tsetting={" + listed + b"}\n}\ncountry_manager={\n}\n"
    return b"SAV010000000000%08x" % len(meta) + b"\n" + meta + state


class SwitchRulesTest(SessionTestCase):
    """`start --switch-rule` loads a copy of the fixture with a rule switched (#1599)."""

    def setUp(self):
        super().setUp()
        base = self.user.parent
        for rel, text in RULE_FILES.items():
            path = base / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        # The rule file is part of the deployed mod's script, so the fixture's key follows it.
        self.fixture_save.unlink()
        self.key = fixture.key(self.paths.game_version, [DEPLOYED_WIN, OVERLAY_WIN], self.paths.deploy_dir,
                               playset="mod_only")
        self.fixture_save = self.user / "save games" / ("te_qa_fixture_%s.v3" % self.key)
        self.fixture_save.write_bytes(text_save(["no_fantasy", "tax_light"]))

    def saves(self) -> list[str]:
        return sorted(p.name for p in (self.user / "save games").iterdir())

    def test_a_plain_start_reports_the_rules_the_fixture_holds(self):
        reply = self.start()
        self.assertEqual(reply["rules"], {"settings": ["no_fantasy", "tax_light"]})
        self.assertEqual(self.saves(), [self.fixture_save.name])

    def test_a_switched_rule_loads_a_copy_and_says_what_it_is(self):
        before = self.fixture_save.read_bytes()
        reply = self.start(switch_rules={"tax_rule": "tax_off"})
        stem = "te_qa_fixture_%s" % rules_key(self.key, {"tax_rule": "tax_off"})
        self.assertEqual(reply["save"], stem)
        self.assertEqual(reply["rules"]["settings"], ["no_fantasy", "tax_off"])
        self.assertEqual(reply["rules"]["switched"], {"tax_rule": {"from": "tax_light", "to": "tax_off"}})
        self.assertIn("2 January 1836", reply["rules"]["switched_at"])
        self.assertFalse(reply["fixture_made"])
        self.assertEqual(self.fixture_save.read_bytes(), before)
        self.assertEqual(self.saves(), [self.fixture_save.name, stem + ".v3"])
        # The game was started on the copy, and the snapshot took it by name.
        launch = next(c for c in self.cli.calls if c[0] == "launch")
        self.assertIn("-loadsave=" + stem, launch)
        self.assertEqual(next(c for c in self.cli.calls if c[0] == "snapshot"), ["snapshot", "--save", stem])

    def test_the_copy_about_to_load_survives_the_prune(self):
        # Review finding: with three copies and the oldest asked for, prune removed the save the reply named.
        first = self.start(switch_rules={"tax_rule": "tax_off"})["save"]
        saves = self.user / "save games"
        os.utime(saves / (first + ".v3"), (1_600_000_000,) * 2)
        for n in (1, 2):
            other = saves / ("te_qa_fixture_%s_s%08x.v3" % (self.key, n))
            other.write_bytes(text_save(["no_fantasy", "tax_off"]))
        self.setUp_second_session()
        reply = self.start(switch_rules={"tax_rule": "tax_off"})
        self.assertEqual(reply["save"], first)
        self.assertTrue((saves / (first + ".v3")).is_file())
        self.assertTrue(self.fixture_save.is_file())
        self.assertNotIn(first + ".v3", reply.get("fixtures_pruned", []))

    def setUp_second_session(self):
        """A new session over the same folders (a session runs one game)."""
        self.session.stop()
        self.game = Game(self.user, self.order)
        self.cli = Cli(self)
        self.session = session.Session(self.game, self.cli, self.spawn_watch, self.paths,
                                       sleep=self.game.sleep, clock=self.game.clock, helper_factory=self.new_helper)

    def test_a_rule_or_setting_the_game_does_not_define_starts_nothing(self):
        for switches, code in (({"nope": "x"}, "bad_rule"), ({"tax_rule": "no_fantasy"}, "bad_rule"),
                               ({"tax rule": "tax_off"}, "bad_rule"), ("tax_rule=tax_off", "bad_argument")):
            with self.subTest(switches=switches):
                self.assertEqual(self.session_error(self.start, switch_rules=switches).code, code)
        self.assertEqual((self.cli.calls, self.saves()), ([], [self.fixture_save.name]))
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertTrue(self.start()["rules"])      # and the session can still be started

    def test_a_switch_with_the_owners_save_is_refused(self):
        (self.user / "save games" / "mine.v3").write_bytes(b"the owner's")
        error = self.session_error(self.start, save="mine", switch_rules={"tax_rule": "tax_off"})
        self.assertEqual(error.code, "bad_argument")
        self.assertIn("never edited or copied", str(error))
        self.assertEqual(self.cli.calls, [])
        self.assertEqual((self.user / "save games" / "mine.v3").read_bytes(), b"the owner's")

    def test_a_fixture_whose_rules_cannot_be_switched_stops_the_start(self):
        self.fixture_save.write_bytes(b"a fresh game")       # not a plain-text save
        error = self.session_error(self.start, switch_rules={"tax_rule": "tax_off"})
        self.assertEqual(error.code, "rules_refused")
        self.assertEqual(self.saves(), [self.fixture_save.name])
        self.assertNotIn("launch", self.cli.verbs)

    def test_the_fixture_key_follows_the_owners_last_applied_rules(self):
        presets = self.user / "player" / "game_rules" / "presets.txt"
        presets.parent.mkdir(parents=True)
        presets.write_text('game_rules_preset={\n\tname="LastAppliedRules"\n\tsetting={ no_fantasy tax_light }\n}\n',
                           encoding="utf-8")
        before = presets.read_bytes()
        # The fixture in the folder was made under other rules (none recorded): a new one is made for these.
        self.cli.queue("snapshot", {"id": FIXTURE_SNAP}, 0)
        reply = self.start()
        self.assertTrue(reply["fixture_made"])
        with_rules = fixture.key(self.paths.game_version, [DEPLOYED_WIN, OVERLAY_WIN], self.paths.deploy_dir,
                                 playset="mod_only", rules=["no_fantasy", "tax_light"])
        self.assertEqual(reply["save"], "te_qa_fixture_%s" % with_rules)
        self.assertNotEqual(with_rules, self.key)
        self.assertEqual(presets.read_bytes(), before)


def rules_key(base: str, switches: dict) -> str:
    from game_qa import rules
    return rules.switched_key(base, switches)


class AddSetupTest(SessionTestCase):
    """A setup added to a running game (#1600): the overlay's effects file is rewritten, the game reloads it,
    and the verb returns once the game has logged the new revision."""

    BODY = "set_variable = te_late"

    def effects(self) -> str:
        return (self.paths.overlay_dir / overlay.EFFECTS_FILE).read_text(encoding="utf-8-sig")

    def test_an_added_setup_runs_once_the_game_has_reloaded(self):
        self.started(setups={"border": "set_variable = te_x"})
        before = self.game.now
        reply = self.session.add_setup("late", self.BODY)
        self.assertEqual((reply["name"], reply["event"], reply["revision"], reply["loaded"]),
                         ("late", "te_qa.100", 1, True))
        self.assertEqual(reply["slots_left"], overlay.SLOT_COUNT - 1)
        self.assertGreaterEqual(self.game.now - before, self.game.reload_s)
        self.assertGreater(reply["tries"], 1)
        self.assertIn("TE_QA setup late start", self.effects())
        # The reload dropped the breakpoint; it is set again, so a read still stops.
        self.assertEqual(self.game.adapter.breakpoints, {EVENTS_WIN: [self.session._overlay.read_line]})
        self.game.adapter.values["c:FRA.gdp"] = "12"
        self.assertEqual(self.session.read(["c:FRA.gdp"])[0].raw, "12")
        self.game.setups = {"te_qa.100": ("late", ["one line"])}
        self.assertEqual(self.session.run_setup("late"), ["one line"])
        # A second one takes the next slot and the next revision.
        second = self.session.add_setup("later", self.BODY)
        self.assertEqual((second["event"], second["revision"]), ("te_qa.101", 2))

    def test_a_window_frozen_by_the_reload_is_waited_out(self):
        # Live, 2026-11-12: the window did not respond for the reload's 90 s, and the console called that
        # game_gone after 10 s. The game was up all along.
        self.started()
        typed_before = len(self.typed())
        reply = self.session.add_setup("late", self.BODY)
        self.assertTrue(reply["loaded"])
        self.assertGreaterEqual(reply["waited_s"], self.game.reload_s)
        self.assertEqual(self.game.dropped, [], "nothing was typed at the frozen window")
        self.assertEqual(self.typed()[typed_before:].count("event te_qa.3"), 1)
        self.game.setups = {"te_qa.100": ("late", ["one line"])}
        self.assertEqual(self.session.run_setup("late"), ["one line"])

    def test_the_stop_a_reload_ends_with_is_released(self):
        # Live, 2026-11-12: after its reload the game stayed frozen for four minutes, until a verb resumed it.
        self.started()
        reply = self.session.add_setup("late", self.BODY)
        self.assertTrue(reply["loaded"])
        self.assertLess(reply["waited_s"], self.game.reload_s + 60)
        self.assertFalse(self.game.adapter.stopped)
        lines = (self.paths.backup_root / "runs" / SNAP / "steps.jsonl").read_text("utf-8").splitlines()
        step = [s for s in map(json.loads, lines) if s["verb"] == "add_setup"][-1]
        self.assertEqual(step["released"], ["pause"])

    def test_a_window_that_is_gone_is_not_waited_for(self):
        self.started()
        self.game.reloads = False

        def gone(seconds):
            self.game.exists = False
        self.game.on_sleep = gone
        with self.assertRaises((session.SessionError, ConsoleError)) as caught:
            self.session.add_setup("late", self.BODY)
        self.assertIn(caught.exception.code, ("game_gone", "watch_ended"))
        self.assertLess(self.game.now, 2 * session.RELOAD_FIRST_S + 30)

    def test_run_setup_during_the_reload_says_the_setup_is_not_loaded_yet(self):
        self.started()
        self.game.reload_s = 10_000.0           # still reloading when add-setup gives up
        self.assertEqual(self.session_error(self.session.add_setup, "late", self.BODY).code, "not_reloaded")
        error = self.session_error(self.session.run_setup, "late")
        self.assertEqual(error.code, "setup_not_loaded")
        self.assertIn("does not respond", str(error))

    def test_the_first_look_waits_and_dropped_commands_are_tried_again(self):
        self.started()
        self.game.freezes = False               # the 2026-11-10 behaviour: the console takes keys and drops them
        typed_before = len(self.typed())
        reply = self.session.add_setup("late", self.BODY)
        looks = self.typed()[typed_before:].count("event te_qa.3")
        self.assertGreaterEqual(looks, reply["tries"])      # the console types a command that did not arrive again
        self.assertGreater(reply["tries"], 1)
        self.assertTrue(self.game.dropped, "the game dropped the looks made while it reloaded")
        # Its own looks, and the console's flush and probe commands around them: nothing else was typed.
        self.assertIn("event te_qa.3", self.game.dropped)
        self.assertLessEqual(set(self.game.dropped),
                             {"event te_qa.3", fakes.FLUSH_COMMAND, session.PENDING_COMMAND})
        self.assertTrue(reply["loaded"])

    def test_a_reload_that_is_already_done_takes_one_look(self):
        self.started()
        self.game.reload_s = 1.0
        reply = self.session.add_setup("late", self.BODY)
        self.assertLessEqual(reply["tries"], 2)     # one more when the stop the reload ends with is seen late
        self.assertLess(reply["waited_s"], 60)

    def test_a_name_or_body_the_overlay_refuses_writes_and_types_nothing(self):
        self.started(setups={"border": "set_variable = te_x"})
        before, steps = self.effects(), len(self.game.steps)
        for name, body in (("border", self.BODY), ("Bad Name", self.BODY), ("late", "x = {")):
            with self.subTest(name=name, body=body):
                self.assertEqual(self.session_error(self.session.add_setup, name, body).code, "overlay_refused")
        self.assertEqual((self.effects(), len(self.game.steps)), (before, steps))

    def test_a_game_that_never_reloads_is_not_reloaded_and_the_setup_is_refused_until_it_has(self):
        self.started()
        self.game.reloads = False
        before = self.game.now
        error = self.session_error(self.session.add_setup, "late", self.BODY)
        self.assertEqual(error.code, "not_reloaded")
        self.assertEqual((error.info["revision"], error.info["seen"]), (1, 0))
        self.assertGreaterEqual(self.game.now - before, session.RELOAD_WAIT_S - session.RELOAD_RETRY_S)
        self.assertLess(self.game.now - before, session.RELOAD_WAIT_S + 60)
        # The setup is in the file, but the game still runs the old one: its slot would log nothing.
        self.assertIn("TE_QA setup late start", self.effects())
        self.game.setups = {"te_qa.100": ("late", ["one line"])}
        typed = len(self.typed())
        self.assertEqual(self.session_error(self.session.run_setup, "late").code, "setup_not_loaded")
        self.assertNotIn("event te_qa.100", self.typed()[typed:])
        # Once the game has reloaded, run-setup's own look sees it, sets the breakpoint again and runs the setup.
        self.game.loaded_revision = 1
        self.game.adapter.breakpoints.clear()
        self.assertEqual(self.session.run_setup("late"), ["one line"])
        self.assertIn(EVENTS_WIN, self.game.adapter.breakpoints)

    def test_a_read_after_a_late_reload_attaches_again_first(self):
        # Review finding: after not_reloaded nothing attached the debugger again once the reload came, and every
        # read failed.
        self.started()
        self.game.reloads = False
        self.assertEqual(self.session_error(self.session.add_setup, "late", self.BODY).code, "not_reloaded")
        self.game.loaded_revision = 1               # the reload lands, and drops the breakpoint
        self.game.adapter.breakpoints.clear()
        self.game.adapter.values["c:FRA.gdp"] = "12"
        self.assertEqual(self.session.read(["c:FRA.gdp"])[0].raw, "12")
        self.assertIn(EVENTS_WIN, self.game.adapter.breakpoints)

    def test_a_revision_the_overlay_never_wrote_is_not_believed(self):
        # Review finding: a log line naming a later revision latched "loaded" for every setup after it.
        self.started()
        self.game.reloads = False
        real = self.game._run

        def forged(text):
            real(text)
            if text == "event te_qa.3":
                self.game.script("TE_QA overlay rev 99")
                self.game.pad()
        self.game._run = forged
        error = self.session_error(self.session.add_setup, "late", self.BODY)
        self.assertEqual((error.code, error.info["seen"]), ("not_reloaded", 0))
        self.assertEqual(self.session._loaded_revision, 0)

    def test_a_game_that_ends_during_the_wait_stops_the_looks(self):
        self.started()
        self.game.reloads = False

        def gone(seconds):
            if self.game.now > 60 and self.watches:
                self.watches[-1].returned = True
                self.game.exists = False
        self.game.on_sleep = gone
        with self.assertRaises((session.SessionError, ConsoleError)) as caught:
            self.session.add_setup("late", self.BODY)
        self.assertIn(caught.exception.code, ("game_gone", "watch_ended"))
        self.assertLess(self.game.now, session.RELOAD_WAIT_S)

    def test_add_setup_needs_a_started_session(self):
        self.assertEqual(self.session_error(self.session.add_setup, "late", self.BODY).code, "not_started")


class EnterPastAWindowTest(SessionTestCase):
    """#1598: a setup that changes a law on the country-select screen raises the game's "We now have …" window
    where the country click lands. The click then selects nothing, which the lobby's side panel shows. Live,
    2026-11-12, no key closed the window once the click had landed on it, so nothing is pressed: the miss is
    refused before Start, and the session goes on."""

    def test_a_covered_screen_is_refused_before_start_and_can_be_tried_again(self):
        self.started()
        self.game.law_windows = 2
        steps = len(self.game.steps)
        error = self.session_error(self.session.enter_game)
        self.assertEqual(error.code, "no_country_selected")
        self.assertEqual(len(error.info["clicks"]), 1, "only the country click: Start was never clicked")
        self.assertTrue(Path(error.info["screenshot"]).is_file())
        self.assertFalse(self.game.entered)
        self.assertEqual((self.game.law_windows, self.game.bare_esc), (2, 0), "nothing was pressed to close it")
        self.assertNotIn({"scan": 1}, self.game.steps[steps:])
        status = self.session.status()
        self.assertEqual((status["entered"], status["entered_unproved"], status["left_running"]), (False, False, False))
        # The session is not locked: reads still work, and with the window gone it enters.
        self.game.adapter.values["c:FRA.gdp"] = "12"
        self.assertEqual(self.session.read(["c:FRA.gdp"])[0].raw, "12")
        self.game.law_windows = 0
        self.assertTrue(self.session.enter_game()["entered"])

    def test_advance_on_a_covered_screen_gets_the_same_refusal_and_is_not_left_running(self):
        self.started()
        self.game.law_windows = 1
        self.assertEqual(self.session_error(self.session.advance, 3).code, "no_country_selected")
        self.assertFalse(self.session.status()["left_running"])
        self.game.law_windows = 0
        start = self.game.date
        self.session.advance(3)
        self.assertGreaterEqual((self.game.date - start).days, 3)

    def test_the_first_look_at_the_panel_comes_with_the_game_in_front(self):
        # A screenshot is of the screen: with another window over the game the first look would be of that
        # window, and every later look would differ from it.
        self.started()
        self.game.foreground = False
        in_front = []
        real = self.game.screenshot

        def shot(pid, path, max_width=1600):
            in_front.append(self.game.foreground)
            return real(pid, path, max_width)
        self.game.screenshot = shot
        self.assertTrue(self.session.enter_game()["entered"])
        self.assertTrue(in_front and all(in_front))

    def test_a_selected_country_goes_on_to_start(self):
        self.started()
        result = self.session.enter_game()
        self.assertTrue(result["entered"])
        self.assertEqual(len(result["clicks"]), 2)
        self.assertEqual(self.game.bare_esc, 0)

    def test_a_screenshot_that_cannot_be_read_goes_on_as_before(self):
        self.started()
        self.game.panel_shots = False           # a 1x1 picture: the panel cannot be found in it
        result = self.session.enter_game()
        self.assertTrue(result["entered"])
        self.assertEqual(len(result["clicks"]), 2)
        self.assertIn("enter_panel", [s["verb"] for s in self.steps()])

    def steps(self) -> list[dict]:
        lines = (self.paths.backup_root / "runs" / SNAP / "steps.jsonl").read_text("utf-8").splitlines()
        return [json.loads(line) for line in lines]


class PressTest(SessionTestCase):
    def test_press_closes_the_console_and_sends_the_key_to_the_game(self):
        self.started()
        before = len(self.game.steps)
        self.assertEqual(self.session.press("esc"), {"key": "esc", "scan": 1})
        sent = self.game.steps[before:]
        self.assertEqual(sent[-1], {"scan": 1})
        self.assertFalse(self.game.console_open, "the key did not go into the console's input line")
        # The next verb that types opens the console again.
        self.game.adapter.values["c:FRA.gdp"] = "12"
        self.assertEqual(self.session.read(["c:FRA.gdp"])[0].raw, "12")

    def test_any_other_key_is_refused_and_nothing_is_sent(self):
        self.started()
        before = len(self.game.steps)
        self.assertEqual(self.session_error(self.session.press, "f4").code, "bad_argument")
        self.assertEqual(len(self.game.steps), before)
        self.assertEqual(self.session_error(session.Session.press, self.session, "enter").code, "bad_argument")


class PickTest(SessionTestCase):
    def test_pick_always_passes_the_numeric_id(self):
        self.started()
        self.game.on("select_event_option list", success=["10 te_qa_probe.2 options=3"])
        self.game.on("select_event_option 2 10", success=["Selected option 2 of te_qa_probe.2"])
        self.game.on("select_event_option 1 10", success=["Selected option 1 of te_qa_probe.2"])
        first = self.session.pick(2)
        second = self.session.pick(1, "te_qa_probe.2")
        self.assertIn("select_event_option 2 10", self.typed())
        self.assertIn("select_event_option 1 10", self.typed())
        self.assertEqual((first["numeric_id"], first["event"], first["ambiguous"]), (10, "te_qa_probe.2", False))
        self.assertEqual(second["index"], 1)
        self.assertEqual(self.session.events(), [logtail.Pending(10, "te_qa_probe.2", 3)])

    def test_pick_by_name_with_two_pending_takes_the_oldest_and_says_so(self):
        self.started()
        self.game.on("select_event_option list", success=["12 x.1 options=2", "11 x.1 options=2", "13 y.1 options=1"])
        self.game.on("select_event_option 0 11", success=["Selected option 0 of x.1"])
        result = self.session.pick(0, "x.1")
        self.assertEqual((result["numeric_id"], result["ambiguous"]), (11, True))
        self.assertIn("select_event_option 0 11", self.typed())
        self.assertNotIn("select_event_option 0 12", self.typed())

    def test_pick_with_nothing_pending_is_an_error(self):
        self.started()
        self.game.on("select_event_option list", success=["No pending events"])
        self.assertEqual(self.session_error(self.session.pick, 0).code, "nothing_pending")
        self.assertEqual(self.session_error(self.session.pick, 0, "x.1").code, "nothing_pending")
        self.game.on("select_event_option list", success=["10 x.1 options=2"])
        self.assertEqual(self.session_error(self.session.pick, 0, "y.1").code, "nothing_pending")
        self.assertEqual(self.session_error(self.session.pick, 2, "x.1").code, "bad_index")
        self.assertEqual(self.session_error(self.session.pick, -1).code, "bad_index")
        self.assertFalse([t for t in self.typed() if t.startswith("select_event_option ") and t[20:21].isdigit()])

    def test_a_pick_the_game_did_not_confirm_is_an_error(self):
        self.started()
        self.game.on("select_event_option list", success=["10 x.1 options=2"])
        self.assertEqual(self.session_error(self.session.pick, 1).code, "not_selected")
        self.assertEqual(self.typed().count("select_event_option 1 10"), 1)

    def test_a_reply_that_is_not_a_list_is_not_taken_for_nothing_pending(self):
        self.started()
        self.game.on("select_event_option list", failure=["Unknown command"])
        self.assertEqual(self.session_error(self.session.events).code, "bad_reply")


class EnterGameTest(SessionTestCase):
    def test_enter_game_clicks_the_two_points_of_the_client_area(self):
        for client, country, start in (((0, 0, 3840, 2160), (1889, 1417), (3539, 2106)),
                                       ((40, 30, 1920, 1080), (945, 708), (1769, 1053))):
            with self.subTest(client=client):
                self.setUp()
                self.game.client = client
                self.started()
                result = self.session.enter_game()
                self.assertEqual(self.game.clicks, [country, start])
                self.assertTrue(result["entered"])
                self.assertEqual(self.game.played, "FRA")
                self.assertEqual(result["before"], (1836, 1, 11))
                self.assertEqual(result["after"], (1836, 1, 15))        # 3 s at 1.5 days a second
                self.assertTrue(self.game.paused)
                self.assertEqual(self.order.count("space"), 2)

    def test_clicks_that_select_nothing_are_refused_before_start(self):
        # With the side panel readable (#1598) a country click that selects nothing is seen at once.
        self.started()
        self.game.clicks_work = False
        error = self.session_error(self.session.enter_game)
        self.assertEqual(error.code, "no_country_selected")
        self.assertTrue(Path(error.info["screenshot"]).is_file())
        self.assertFalse(self.session.status()["entered_unproved"])

    def test_enter_game_that_does_not_move_the_date_raises_with_a_screenshot(self):
        self.started()
        self.game.clicks_work = False
        self.game.panel_shots = False           # the panel cannot be read: only the date can tell
        error = self.session_error(self.session.enter_game)
        self.assertEqual(error.code, "not_entered")
        shot = Path(error.info["screenshot"])
        self.assertTrue(shot.is_file())
        self.assertEqual(shot.parent, self.paths.backup_root / "runs" / SNAP)
        self.assertEqual(len(self.game.clicks), 2)

    def test_a_date_that_stayed_locks_nothing_and_enter_game_can_be_tried_again(self):
        # #1598: a window over the country-select screen took the country click, so Start did nothing. The proof
        # ran to its end (unpaused 3 s, paused again, the pause proved) and the date had not moved: the game is
        # where it was, so the session is not left refusing enter_game and advance until stop. (With the side
        # panel readable the miss is seen before Start, EnterPastAWindowTest; this is the path when it is not.)
        self.started()
        self.game.clicks_work = False
        self.game.panel_shots = False
        error = self.session_error(self.session.enter_game)
        self.assertEqual(error.code, "not_entered")
        self.assertIn("the date stayed", error.detail)
        self.assertNotIn("cause", error.info)
        self.assertEqual(error.info["clicks"], [list(c) for c in self.game.clicks])
        status = self.session.status()
        self.assertEqual((status["entered"], status["entered_unproved"], status["left_running"]), (False, False, False))
        self.assertTrue(self.game.paused)
        self.assertEqual(self.session.read([]), [])              # the debugger attached again still stops
        self.game.clicks_work = True                              # the window is gone
        result = self.session.enter_game()
        self.assertTrue(result["entered"])
        self.assertEqual(len(self.game.clicks), 4)                # the two points, clicked again
        self.assertEqual(self.game.clicks[2:], self.game.clicks[:2])
        self.assertEqual(self.game.played, "FRA")
        self.assertGreater(session._game_day(result["after"]), session._game_day(result["before"]))
        status = self.session.status()
        self.assertEqual((status["entered"], status["entered_unproved"], status["left_running"]), (True, False, False))
        self.assertGreaterEqual(session._game_day(self.session.advance(3)), session._game_day(result["after"]) + 3)

    def test_advance_after_a_date_that_stayed_enters_again_instead_of_refusing(self):
        self.started()
        self.game.clicks_work = False
        self.game.panel_shots = False           # the panel cannot tell, so the date has to
        self.assertEqual(self.session_error(self.session.advance, 3).code, "not_entered")
        self.assertEqual(self.session_error(self.session.advance, 3).code, "not_entered")     # not left_running
        self.assertEqual(len(self.game.clicks), 4)
        self.game.clicks_work = True
        start = self.game.date
        reached = self.session.advance(3)
        self.assertGreaterEqual(session._game_day(reached), session._game_day((start.year, start.month, start.day)) + 3)
        self.assertEqual(self.session.stop()["outcome"], "restored")

    def test_a_click_waits_for_the_presence_rule_and_never_focuses_on_its_own(self):
        self.started()
        self.game.foreground = False

        def someone_moves_the_mouse(reading):
            self.game.cursor = (10 * reading, 5 * reading)
        self.game.on_presence = someone_moves_the_mouse
        with self.assertRaises(ConsoleError) as caught:
            self.session.enter_game()
        self.assertEqual(caught.exception.code, "not_foreground")
        self.assertEqual((self.game.clicks, self.game.focus_calls), ([], 0))

    def test_enter_game_needs_a_country(self):
        self.started(as_tag=None)
        self.assertEqual(self.session_error(self.session.enter_game).code, "no_country")
        self.assertEqual(self.game.clicks, [])

    # After live session 2 (2026-11-11): the clicks entered the game as the country the camera was on, not the
    # tagged one, and no read stopped at the breakpoint after them, though the console answered.

    def steps(self) -> list[dict]:
        lines = (self.paths.backup_root / "runs" / SNAP / "steps.jsonl").read_text("utf-8").splitlines()
        return [json.loads(line) for line in lines]

    def after_start(self) -> list[str]:
        """The order log from the Start click on."""
        return self.order[[i for i, what in enumerate(self.order) if what == "click"][1] + 1:]

    def test_entering_attaches_the_debugger_again_and_tags_the_country_again(self):
        reply = self.started()
        self.assertFalse(self.session.status()["entered_unproved"])
        result = self.session.enter_game()
        self.assertTrue(result["entered"])
        self.assertEqual(self.game.played, "FRA")              # the click entered DEN; the tag after it plays FRA
        self.assertEqual(self.game.adapter.breakpoints, {EVENTS_WIN: [reply["overlay"]["read_line"]]})
        self.assertEqual([what for what in self.after_start() if what.startswith("tcp")], ["tcp_close", "tcp_open 6111"])
        attach = ["initialize", "launch", "setBreakpoints", "configurationDone"]
        self.assertEqual(self.game.adapter.commands[:8], attach + attach)     # start's, then the new connection's
        self.assertEqual(self.typed().count("tag FRA"), 2)
        verbs = [step["verb"] for step in self.steps()]
        self.assertEqual(verbs[verbs.index("start") + 1:], ["console_after_start", "reattach", "tag", "enter_game"])
        reattach = next(step for step in self.steps() if step["verb"] == "reattach")
        self.assertEqual((reattach["outcome"], reattach["verified"]), ("ok", [True]))
        status = self.session.status()
        self.assertEqual((status["entered"], status["entered_unproved"], status["left_running"]), (True, False, False))

    def assert_left_after_start(self, error, code: str, again: str = "left_running") -> None:
        """`again`: what enter_game and advance answer afterwards (refused either way, before any click)."""
        self.assertEqual(error.code, code)
        self.assertEqual(error.info["clicks"], [list(c) for c in self.game.clicks])
        self.assertEqual(len(self.game.clicks), 2)
        status = self.session.status()
        self.assertEqual((status["entered"], status["entered_unproved"], status["left_running"]), (False, True, True))
        self.assertEqual(self.session_error(self.session.enter_game).code, again)
        self.assertEqual(self.session_error(self.session.advance, 3).code, again)
        self.assertEqual(len(self.game.clicks), 2)            # nothing is clicked again

    def test_a_breakpoint_not_verified_again_is_left_running_with_the_clicks(self):
        self.started()
        self.game.adapter.verified = False                    # only the second setBreakpoints is answered so
        error = self.session_error(self.session.enter_game)
        self.assert_left_after_start(error, "breakpoint_unverified")
        self.assertEqual([step["outcome"] for step in self.steps() if step["verb"] == "reattach"],
                         ["breakpoint_unverified"])

    def test_a_console_that_does_not_answer_after_start_is_not_entered_once_the_wait_is_over(self):
        self.started()

        def load(seconds):
            if self.game.entered:
                self.game.console_never_opens = True
        self.game.on_sleep = load
        began = self.game.now
        error = self.session_error(self.session.enter_game)
        self.game.on_sleep = None
        self.assert_left_after_start(error, "not_entered")
        self.assertEqual(error.info["cause"], "no_ack")
        waited = self.game.now - began
        self.assertGreaterEqual(waited, session.CLICK_SETTLE_S + session.ENTER_SETTLE_S + session.ENTER_WAIT_S)
        self.assertLess(waited, session.CLICK_SETTLE_S + session.ENTER_SETTLE_S + session.ENTER_WAIT_S + 60)
        self.assertNotIn("tcp_close", self.after_start())     # neither re-attached nor tagged: the console never came
        self.assertEqual(self.typed().count("tag FRA"), 1)
        tried = next(step for step in self.steps() if step["verb"] == "console_after_start")
        self.assertEqual(tried["outcome"], "no_ack")
        self.assertGreaterEqual(tried["tries"], 2)

    def test_a_console_refusal_a_load_cannot_cause_is_not_tried_again(self):
        self.started()

        def load(seconds):
            if self.game.entered:
                self.game.foreground = False                  # and the window will not come to the front
        self.game.on_sleep = load
        self.game.focus_succeeds = False
        error = self.session_error(self.session.enter_game)
        self.game.on_sleep = None
        self.assert_left_after_start(error, "not_entered")
        self.assertEqual(error.info["cause"], "not_foreground")
        tried = next(step for step in self.steps() if step["verb"] == "console_after_start")
        self.assertEqual((tried["outcome"], tried["tries"]), ("not_foreground", 1))

    def test_a_console_that_answers_late_after_start_is_waited_for(self):
        self.started()
        loading = {}

        def load(seconds):
            if self.game.entered and "until" not in loading:
                loading["until"] = self.game.now + 50       # past one ensure_open's 30 s, within ENTER_WAIT_S
            self.game.console_never_opens = "until" in loading and self.game.now < loading["until"]
        self.game.on_sleep = load
        result = self.session.enter_game()
        self.game.on_sleep = None
        self.assertTrue(result["entered"])
        self.assertEqual(self.game.played, "FRA")
        tried = next(step for step in self.steps() if step["verb"] == "console_after_start")
        self.assertGreaterEqual(tried["tries"], 2)

    def test_a_game_that_exits_while_the_console_is_awaited_types_nothing_more(self):
        self.started()
        marks = {}

        def gone(seconds):
            if self.game.entered and "steps" not in marks:
                self.game.exited = True                       # watch records it at its next look
                marks["steps"], marks["at"] = len(self.game.steps), self.game.now
        self.game.on_sleep = gone
        error = self.session_error(self.session.enter_game)
        self.game.on_sleep = None
        self.assertEqual(error.code, "watch_ended")
        self.assertEqual(error.info["clicks"], [list(c) for c in self.game.clicks])
        self.assertEqual(len(self.game.steps), marks["steps"])
        self.assertLess(self.game.now - marks["at"], session.ENTER_SETTLE_S + session.ENTER_RETRY_S)  # no 90 s

    def test_a_tag_refused_after_start_is_tag_failed_and_left_running(self):
        self.started()

        def on_command(text):
            if text == "tag FRA" and self.game.entered:
                self.game.on("tag FRA", failure=["Unknown country tag"])
        self.game.on_command = on_command
        error = self.session_error(self.session.enter_game)
        self.game.on_command = None
        self.assert_left_after_start(error, "tag_failed")
        self.assertEqual([step["outcome"] for step in self.steps() if step["verb"] == "tag"], ["ok", "tag_failed"])

    def test_a_stop_pending_when_the_debugger_is_attached_again_is_released_before_the_relay_closes(self):
        self.started()

        def stops(seconds):
            if self.game.entered and not self.game.adapter.stopped and "continue" not in self.game.adapter.commands:
                self.game.adapter.stop()                       # the game passed the breakpoint by itself
        self.game.on_sleep = stops
        self.session.enter_game()
        self.game.on_sleep = None
        commands = self.game.adapter.commands
        self.assertEqual(commands[4:6], ["continue", "initialize"])     # released on the old connection, then anew
        self.assertFalse(self.session.status()["maybe_stopped"])

    def test_a_second_connection_the_relay_refuses_is_not_entered_and_the_verbs_that_need_it_refuse(self):
        self.started()
        self.game.tcp_open_refusal = HelperError("connect_failed", "ConnectionRefusedError(10061)")
        error = self.session_error(self.session.enter_game)
        steps = len(self.game.steps)
        # The old client is left on a closed relay: every verb that looks for a stop refuses `debugger` first,
        # enter_game and advance too, and nothing is typed or clicked.
        self.assert_left_after_start(error, "not_entered", again="debugger")
        self.assertEqual(error.info["cause"], "helper: connect_failed")
        self.assertEqual([step["outcome"] for step in self.steps() if step["verb"] == "reattach"],
                         ["helper: connect_failed"])
        self.assertEqual(self.session_error(self.session.console, "money 1000").code, "debugger")
        self.assertEqual(self.session_error(self.session.shot).code, "debugger")      # maybe_stopped is set now
        self.assertEqual(len(self.game.steps), steps)
        self.assertEqual(self.session.stop()["outcome"], "restored")

    def test_a_window_that_stops_responding_while_the_game_loads_is_waited_for(self):
        self.started()
        loading = {}

        def load(seconds):
            if self.game.entered and "until" not in loading:
                loading["until"] = self.game.now + session.ENTER_SETTLE_S + 10      # past UNRESPONSIVE_S, once
            self.game.responding = "until" not in loading or self.game.now >= loading["until"]
        self.game.on_sleep = load
        result = self.session.enter_game()
        self.game.on_sleep = None
        self.assertTrue(result["entered"])
        tried = next(step for step in self.steps() if step["verb"] == "console_after_start")
        self.assertEqual((tried["outcome"], tried["tries"]), ("ok", 2))

    def test_a_proof_that_cannot_pause_the_game_is_left_running_with_the_clicks(self):
        self.started()
        self.game.dropped_pauses = 99
        error = self.session_error(self.session.enter_game)
        self.assert_left_after_start(error, "left_running")
        self.assertIn("still moved after a second pause key", error.detail)     # _run_for's own words


class ClickTest(SessionTestCase):
    """`click X Y`: one click at fractions of the client area, for the engine's tool windows (#1701)."""

    def test_a_click_lands_at_its_fraction_of_the_client_area_and_takes_a_screenshot(self):
        for client, at, pixel in (((0, 0, 3840, 2160), (0.5, 0.25), (1920, 540)),
                                  ((40, 30, 1920, 1080), (0.1, 0.9), (192, 972)),
                                  ((0, 0, 1920, 1080), (0.9999, 0.0), (1919, 0))):
            with self.subTest(client=client, at=at):
                self.setUp()
                self.game.client = client
                self.started()
                console_open = self.game.console_open
                steps = len(self.game.steps)
                reply = self.session.click(*at)
                self.assertEqual(self.game.clicks, [pixel])
                self.assertEqual(reply["pixel"], list(pixel))
                self.assertTrue(Path(reply["screenshot"]).is_file())
                # The console is neither opened nor closed for it: no key went out.
                self.assertEqual((len(self.game.steps), self.game.console_open), (steps, console_open))

    def test_a_point_off_the_window_is_refused_and_nothing_is_pressed(self):
        self.started()
        for bad in (-0.1, 1, 1.0, 2.5, True, "0.5", None, float("nan"), float("inf"), float("-inf"), 1e308):
            with self.subTest(bad=bad):
                self.assertEqual(self.session_error(self.session.click, bad, 0.5).code, "bad_argument")
                self.assertEqual(self.session_error(self.session.click, 0.5, bad).code, "bad_argument")
        self.assertEqual(self.game.clicks, [])

    def test_a_click_waits_for_the_presence_rule_and_never_focuses_on_its_own(self):
        self.started()
        self.game.foreground = False

        def someone_moves_the_mouse(reading):
            self.game.cursor = (10 * reading, 5 * reading)
        self.game.on_presence = someone_moves_the_mouse
        with self.assertRaises(ConsoleError) as caught:
            self.session.click(0.5, 0.5)
        self.assertEqual(caught.exception.code, "not_foreground")
        self.assertEqual((self.game.clicks, self.game.focus_calls), ([], 0))

    def test_a_game_that_cannot_be_proved_gets_no_click(self):
        self.started()
        self.game.process_gone = True
        self.assertEqual(self.session_error(self.session.click, 0.5, 0.5).code, "watch_ended")
        self.assertEqual(self.game.clicks, [])

    def test_a_refused_click_says_so(self):
        self.started()
        for code in session.CLICK_REFUSED_BEFORE_PRESS:
            with self.subTest(code=code):
                self.game.click = mock.Mock(side_effect=HelperError(code, "refused"))
                error = self.session_error(self.session.click, 0.5, 0.5)
                self.assertEqual(error.code, "click_refused")
                self.assertIn(code, error.detail)

    def test_an_error_that_may_follow_the_press_is_not_called_a_refusal(self):
        # SendInput failing on the press or the release, the helper ending, a timeout: the button may have gone down.
        self.started()
        for code in ("backend_error", "helper_gone", "timeout"):
            with self.subTest(code=code):
                self.game.click = mock.Mock(side_effect=HelperError(code, "failed"))
                error = self.session_error(self.session.click, 0.5, 0.5)
                self.assertEqual(error.code, "click_unknown")
                self.assertIn(code, error.detail)
                self.assertEqual(error.info["pixel"], [960, 540])

    def test_a_screenshot_that_fails_after_the_click_still_answers_with_the_click(self):
        # A refusal here would have the caller click again, undoing what the first click did.
        self.started()
        self.game.screenshot = mock.Mock(side_effect=HelperError("no_client_area", "minimized?"))
        reply = self.session.click(0.5, 0.5)
        self.assertEqual(self.game.clicks, [(960, 540)])
        self.assertEqual((reply["pixel"], reply["screenshot"]), ([960, 540], None))
        self.assertIn("no_client_area", reply["screenshot_error"])


class AdvanceTest(SessionTestCase):
    def test_advance_reaches_at_least_the_days_asked(self):
        self.started()
        self.game.days_per_second = 1.0         # slower than the first guess: the second wait is sized from it
        reached = self.session.advance(30)
        entered_at = dt.date(1836, 1, 14)       # the 3 s that proved the game was entered
        self.assertGreaterEqual(dt.date(*reached), entered_at + dt.timedelta(days=30))
        self.assertEqual(dt.date(*reached), self.game.date)
        self.assertEqual(self.order.count("space"), 2 + 4)     # enter_game's proof, then two rounds
        self.assertTrue(self.game.paused)

    def test_advance_across_29_february_counts_the_days_the_game_has(self):
        # The game's year is 365 days with no leap day; datetime's 1836 has one.
        self.started()
        self.session.enter_game()
        # From 20 February the first round's 10 calendar days end on 1 March: 9 of the game's days.
        self.game.elapsed = (dt.date(1836, 2, 20) - START_DATE).days + 0.5
        reached = self.session.advance(10)
        self.assertGreaterEqual(dt.date(*reached), dt.date(1836, 3, 2))

    def test_advance_gives_up_after_twenty_rounds(self):
        self.started()
        self.session.enter_game()
        self.game.days_per_second = 0.0
        self.assertEqual(self.session_error(self.session.advance, 5).code, "stalled")
        self.assertEqual(self.order.count("space"), 2 + 2 * session.MAX_ROUNDS)
        self.assertTrue(self.game.paused)

    def test_a_bad_day_count_is_refused_before_any_key(self):
        self.started()
        steps = len(self.game.steps)
        for days in (0, -3, 2.5, True):
            self.assertEqual(self.session_error(self.session.advance, days).code, "bad_days")
        self.assertEqual(len(self.game.steps), steps)


class Events:
    """The game's pending events, for try-event. `event <id>` fires one instance (while `fires`; `fires_left`
    counts down for an event that fires only so often), and so does a setup event in `fired_by`; the console
    answers `Executed "<id>"` only when it fired. A `hidden` event runs (Executed) but is never pending.
    `select_event_option list` lists the pending ones; `select_event_option <i> <n>` picks one and runs
    `effects[i]`."""

    def __init__(self, game: Game, event: str = "x.1", options: int = 3):
        self.game, self.event, self.options = game, event, options
        self.pending: list[int] = []
        self.next_id = 10
        self.fires = True
        self.fires_left: int | None = None
        self.hidden = False
        self.fired_by: set[str] = set()
        self.effects: dict = {}
        game.on_command = self.command

    def fire(self) -> bool:
        if not self.fires or self.fires_left == 0:
            return False
        if self.fires_left is not None:
            self.fires_left -= 1
        if not self.hidden:
            self.pending.append(self.next_id)
            self.next_id += 1
        return True

    def command(self, text: str) -> None:
        if text == "event " + self.event:
            fired = self.fire()
            self.game.on(text, success=['Executed "%s"' % self.event] if fired else [])
        elif text.startswith("event ") and text[6:] in self.fired_by:
            self.fire()
        elif text == "select_event_option list":
            self.game.on(text, success=["%d %s options=%d" % (n, self.event, self.options) for n in self.pending]
                         or ["No pending events"])
        else:
            m = re.fullmatch(r"select_event_option (\d+) (\d+)", text)
            if m and int(m.group(2)) in self.pending:
                index = int(m.group(1))
                self.pending.remove(int(m.group(2)))
                self.game.on(text, success=["Selected option %d of %s" % (index, self.event)])
                if index in self.effects:
                    self.effects[index]()


class TryEventTest(SessionTestCase):
    def setUp(self):
        super().setUp()
        self.events = Events(self.game)
        self.game.adapter.values = {"c:FRA.infamy": "5", "is_player = yes": "yes - Yes: "}

        def option(i):
            def effect():
                self.game.adapter.values["c:FRA.infamy"] = str(10 * (i + 1))
            return effect
        self.events.effects = {i: option(i) for i in range(3)}

    def started(self, **kwargs) -> dict:
        reply = super().started(**kwargs)
        self.game.steps.clear()                 # the console's own probe at start is `select_event_option list` too
        return reply

    def commands(self) -> list[str]:
        """The event and option commands typed since the start, in order (not the console's own flushes)."""
        return [t for t in self.typed() if t.startswith(("event ", "select_event_option"))]

    def try_event_steps(self) -> list[dict]:
        lines = (self.paths.backup_root / "runs" / SNAP / "steps.jsonl").read_text("utf-8").splitlines()
        return [step for step in map(json.loads, lines) if step["verb"] == "try_event"]

    def test_each_option_is_fired_read_picked_and_read_again(self):
        self.started()
        reply = self.session.try_event("x.1", None, ["c:FRA.infamy"])
        self.assertEqual((reply["event"], reply["option_count"], reply["shared_state"], reply["complete"]),
                         ("x.1", 3, True, True))
        rows = reply["options"]
        self.assertEqual([r["index"] for r in rows], [0, 1, 2])
        for row in rows:
            self.assertEqual((row["fired"], row["did_not_fire"], row["fired_by"], row["pending_options"]),
                             (True, False, "console", 3))
        # the reads before and after each pick; each option runs on the state the one before left
        self.assertEqual([(r["before"][0]["raw"], r["after"][0]["raw"]) for r in rows],
                         [("5", "10"), ("10", "20"), ("20", "30")])
        self.assertEqual(rows[0]["before"], [{"expr": "c:FRA.infamy", "ok": True, "raw": "5", "value": 5.0}])
        self.assertEqual([(r["picked"]["index"], r["picked"]["numeric_id"]) for r in rows], [(0, 10), (1, 11), (2, 12)])

        def option(i, n):
            return ["event x.1", "select_event_option list", "event te_qa.1",
                    "select_event_option list", "select_event_option %d %d" % (i, n), "event te_qa.1"]
        # one look before the first firing (nothing of x.1 may be pending), then each option in turn
        self.assertEqual(self.commands(), ["select_event_option list", *option(0, 10), *option(1, 11), *option(2, 12)])
        self.assertEqual(self.events.pending, [])
        # the run folder's record holds the rows, and its summary the table
        [step] = self.try_event_steps()
        self.assertEqual((step["outcome"], step["complete"]), ("ok", True))
        self.assertEqual(step["options"], json.loads(json.dumps(rows)))
        summary = Path(self.session.stop()["report"]).read_text("utf-8")
        self.assertIn("## try-event x.1", summary)
        self.assertIn("| 1 | yes | c:FRA.infamy = 10 | c:FRA.infamy = 20 | option 1 | 0 |", summary)

    def test_the_setup_runs_before_each_option(self):
        reply = self.started(setups={"border": "set_variable = te_x"})
        setup_event = reply["overlay"]["setup_events"]["border"]
        self.game.setups = {setup_event: ("border", ["x.17 is not this event", "nor is x.1.2"])}
        result = self.session.try_event("x.1", "border", ["c:FRA.infamy"])
        self.assertTrue(result["complete"])
        commands = self.commands()
        setups = [i for i, c in enumerate(commands) if c == "event " + setup_event]
        firings = [i for i, c in enumerate(commands) if c == "event x.1"]
        self.assertEqual(len(setups), 3)
        self.assertEqual([i + 1 for i in setups], firings)     # each option: its setup, then the firing
        self.assertEqual([r["fired_by"] for r in result["options"]], ["console"] * 3)

    def test_a_setup_that_fires_the_event_itself_is_not_followed_by_a_firing(self):
        reply = self.started(setups={"border": "trigger_event = x.1"})
        setup_event = reply["overlay"]["setup_events"]["border"]
        self.game.setups = {setup_event: ("border", ["fired x.1."])}
        self.events.fired_by = {setup_event}
        result = self.session.try_event("x.1", "border", ["c:FRA.infamy"])
        self.assertTrue(result["complete"])
        self.assertNotIn("event x.1", self.commands())
        self.assertEqual([r["fired_by"] for r in result["options"]], ["setup"] * 3)

    def test_an_event_that_does_not_fire_is_reported_and_never_a_pass(self):
        self.started()
        self.events.fires = False
        reply = self.session.try_event("x.1", None, ["c:FRA.infamy"])
        self.assertEqual((reply["complete"], reply["option_count"]), (False, None))
        self.assertEqual(reply["options"], [{
            "index": 0, "fired": False, "fired_by": "console", "pending_options": None, "before": [], "after": [],
            "picked": None, "new_errors": [], "did_not_fire": True, "ran_not_pending": False}])
        self.assertEqual(self.commands(), ["select_event_option list", "event x.1", "select_event_option list"])
        # An event that fires once only: its first option is picked, and the second did not fire.
        self.events.fires, self.events.fires_left = True, 1
        reply = self.session.try_event("x.1", None, ["c:FRA.infamy"])
        self.assertEqual((reply["complete"], reply["option_count"]), (False, 3))
        self.assertEqual([(r["fired"], r["did_not_fire"], r["picked"] is not None) for r in reply["options"]],
                         [(True, False, True), (False, True, False)])
        self.assertEqual([s["complete"] for s in self.try_event_steps()], [False, False])

    def test_a_hidden_event_that_ran_is_not_called_unfired_and_is_never_a_pass(self):
        # It runs (the console answers Executed) but is never pending, so there is no option to pick.
        self.started()
        self.events.hidden = True
        reply = self.session.try_event("x.1", None, ["c:FRA.infamy"])
        self.assertEqual((reply["complete"], reply["option_count"]), (False, None))
        [row] = reply["options"]
        self.assertEqual((row["fired"], row["did_not_fire"], row["ran_not_pending"], row["picked"]),
                         (False, False, True, None))
        self.assertEqual(self.commands(), ["select_event_option list", "event x.1", "select_event_option list"])
        summary = Path(self.session.stop()["report"]).read_text("utf-8")
        self.assertIn("ran, not pending", summary)
        self.assertNotIn("did not fire", summary)

    def test_an_event_already_pending_is_refused_before_anything(self):
        self.started()
        self.events.fire()                      # pending already: a firing that did nothing would look like one
        error = self.session_error(self.session.try_event, "x.1", None, ["c:FRA.infamy"])
        self.assertEqual(error.code, "already_pending")
        self.assertEqual(self.commands(), ["select_event_option list"])

    def test_bad_arguments_are_refused_before_anything_is_typed(self):
        self.started()
        for args, code in ((("x.1", "nothing", ["a"]), "unknown_setup"), (("te_qa.1", None, ["a"]), "use_read"),
                           (("x.1", None, "c:FRA.gdp"), "bad_argument"), (("x 1", None, ["a"]), "bad_argument"),
                           (("x." + "1" * 60, None, ["a"]), "bad_argument")):
            with self.subTest(args=args):
                self.assertEqual(self.session_error(self.session.try_event, *args).code, code)
        self.assertEqual(self.commands(), [])

    def test_an_error_on_the_way_keeps_the_rows_so_far_and_types_nothing_again(self):
        self.started()
        self.events.options = 2
        command = self.events.command

        def second_pick_unconfirmed(text):
            command(text)
            if text == "select_event_option 1 11":
                self.game.on(text, success=["Something else happened"])
        self.game.on_command = second_pick_unconfirmed
        error = self.session_error(self.session.try_event, "x.1", None, ["c:FRA.infamy"])
        self.assertEqual(error.code, "not_selected")
        rows = error.info["options"]
        self.assertEqual([(r["index"], r["fired"], r["picked"] is not None) for r in rows], [(0, True, True), (1, True, False)])
        self.assertEqual(self.commands().count("select_event_option 1 11"), 1)
        [step] = self.try_event_steps()
        self.assertEqual((step["outcome"], len(step["options"])), ("not_selected", 2))

    def test_new_errors_leave_out_the_debuggers_own_burst(self):
        self.started()
        self.events.options = 2
        # Each evaluation makes the validator write its burst. The debugger streams it at once; error.log gets each
        # one a read late, so the last option's log also holds the burst of the option before it.
        self.game.adapter.burst = ["Flag 'K{n}' is set but is never used. Note that use in localization doesn't count"]
        self.game.adapter.burst_lag = True
        genuine = "Script system error!\n  Error: x.1 option %d divided by zero\n  Script location: events/x.txt:12\n"

        def option(i):
            def effect():                       # in the log, and streamed to the debugger before the next stop
                self.game.error(genuine % i, streamed=True)
            return effect
        self.events.effects = {0: option(0), 1: option(1)}
        self.game.error("an error from before the check")
        reply = self.session.try_event("x.1", None, ["is_player = yes"])
        self.assertTrue(reply["complete"])
        for i, row in enumerate(reply["options"]):
            with self.subTest(option=i):
                self.assertEqual([logtail.parse(line).text for line in row["new_errors"]],
                                 ["Script system error!", "  Error: x.1 option %d divided by zero" % i,
                                  "  Script location: events/x.txt:12"])
        # the burst was there to be left out: in error.log, and in the run folder's copy of it
        for log in (self.game.error_log, self.paths.backup_root / "runs" / SNAP / "error.log"):
            text = log.read_text("utf-8")
            self.assertIn("Flag 'K0'", text)
            self.assertIn("Flag 'K2'", text)


class StopTest(SessionTestCase):
    def test_stop_kills_waits_for_watch_restores_and_removes_the_overlay_in_that_order(self):
        self.started()
        reply = self.session.stop()
        self.assertEqual(self.order, ["kill", "watch_returned", "cli restore", "tcp_close", "helper_close"])
        self.assertEqual(self.cli.calls, [["restore", SNAP]])
        self.assertEqual(self.cli.overlay_at_restore, [True])
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertEqual(reply["restored"], RESTORED[0]["restored"])
        self.assertEqual((reply["outcome"], reply["snapshot"], reply["overlay_removed"]), ("restored", SNAP, True))
        summary = Path(reply["report"])
        self.assertEqual(summary, self.paths.backup_root / "runs" / SNAP / "summary.md")
        self.assertTrue(summary.read_text("utf-8").startswith("Restore: restored"))

    def test_stop_reports_a_hold_and_does_not_raise(self):
        self.started()
        self.cli.queue("restore", *HELD)
        reply = self.session.stop()
        self.assertEqual((reply["outcome"], reply["held"], reply["reason"]), ("held", True, "other_game_ran"))
        first = Path(reply["report"]).read_text("utf-8").split("\n")[0]
        self.assertIn("HELD", first)
        self.assertIn("other_game_ran", first)

    def test_stop_twice_is_harmless(self):
        self.started()
        first = self.session.stop()
        second = self.session.stop()
        self.assertEqual(first, second)
        self.assertEqual(self.cli.calls, [["restore", SNAP]])
        self.assertEqual(self.game.killed, [self.game.proc])
        self.assertEqual(self.session_error(self.session.read, []).code, "stopped")

    def test_stop_retries_restore_while_watch_is_still_recording(self):
        self.started()
        still = {"held": False, "refused": "watch_still_recording", "id": SNAP}
        self.cli.queue("restore", still, 2)
        self.cli.queue("restore", still, 2)
        now = self.game.now
        self.assertEqual(self.session.stop()["outcome"], "restored")
        self.assertEqual(self.cli.verbs, ["restore"] * 3)
        self.assertEqual(self.game.now - now, 2 * session.RESTORE_RETRY_S)

    def test_a_refused_restore_is_reported_not_retried(self):
        self.started()
        self.cli.queue("restore", {"held": False, "refused": "game_still_up", "id": SNAP}, 2)
        reply = self.session.stop()
        self.assertEqual((reply["outcome"], reply["refused"]), ("refused", "game_still_up"))
        self.assertEqual(self.cli.verbs, ["restore"])
        self.assertIn("REFUSED", Path(reply["report"]).read_text("utf-8").split("\n")[0])
        self.assertTrue(reply["overlay_kept"])             # the run's playset may still name it
        self.assertTrue(self.paths.overlay_dir.exists())

    def test_a_watch_that_does_not_return_is_noted_and_restore_still_runs(self):
        self.started()
        self.watches[0].hangs = True
        now = self.game.now
        reply = self.session.stop()
        self.assertGreaterEqual(self.game.now - now, session.WATCH_WAIT_S)
        self.assertTrue(any("watch" in note for note in reply["notes"]))
        self.assertEqual(self.cli.verbs, ["restore"])

    def test_a_kill_that_fails_leaves_the_game_up_and_keeps_the_overlay(self):
        self.started()

        def kill(proc):
            self.order.append("kill")
            raise HelperError("not_ours", "process 7 changed under its id before it could be ended")
        self.game.kill = kill
        reply = self.session.stop()
        self.assertEqual(reply["outcome"], "game_left_up")
        self.assertTrue(any("not_ours" in note for note in reply["notes"]))
        self.assertTrue(any("still finds process 7" in note for note in reply["notes"]))
        self.assertEqual(self.cli.verbs, [])                   # beside a game that may be the run's: no restore
        self.assertIn("`python3 -m game_qa stop` again", reply["next"])         # it is known: a later stop can end it
        self.assertIn(SNAP, reply["next"])
        self.assertTrue(reply["overlay_kept"])
        self.assertTrue(self.paths.overlay_dir.exists())
        # #1588: the refused kill is followed by one adopt, which proved the game alive, so it is not counted as
        # ended; then nothing of the session's own is left
        self.assertEqual(self.order, ["kill", "adopt", "tcp_close", "helper_close"])
        first = Path(reply["report"]).read_text("utf-8").split("\n")[0]
        self.assertIn("NOT RUN", first)
        self.assertIn("Next: " + reply["next"], first)                      # the reply's own next, not another
        self.assertIn("`python3 -m game_qa stop` again", first)

    def test_a_restore_that_raises_is_a_refusal_and_stop_does_not_raise(self):
        self.started()
        self.cli.raise_on = "restore"
        reply = self.session.stop()
        self.assertEqual(reply["outcome"], "refused")
        self.assertTrue(self.paths.overlay_dir.exists())       # it may not have run: the playset may name it

    def test_stop_before_start_does_nothing(self):
        reply = self.session.stop()
        self.assertEqual(self.cli.calls, [])
        self.assertIsNone(reply["snapshot"])
        self.assertIsNone(reply["report"])

    def test_the_report_has_a_line_per_step(self):
        self.started()
        self.game.adapter.values = {"c:FRA.gdp": "1"}
        self.session.read(["c:FRA.gdp"])
        report = Path(self.session.stop()["report"])
        steps = [json.loads(line) for line in (report.parent / "steps.jsonl").read_text("utf-8").splitlines()]
        verbs = [s["verb"] for s in steps]
        for verb in ("held", "fixture", "snapshot", "launch", "tag", "start", "read", "restore", "stop"):
            self.assertIn(verb, verbs)
        self.assertLess(verbs.index("snapshot"), verbs.index("read"))
        self.assertIn("| read | ok |", report.read_text("utf-8"))


class LaunchOutcomeTest(SessionTestCase):
    """C1: a launch that may have started a game is watched at once and its game ended by launch's own record."""

    def test_a_launch_that_started_a_game_it_could_not_record_still_ends_it(self):
        self.cli.queue("launch", {"refused": "not_recorded", "id": SNAP, "pid": PID, "created": CREATED,
                                  "detail": "the game started but its start could not be recorded"}, 2)
        error = self.session_error(self.start)
        self.assertEqual(error.code, "launch_refused")
        self.assertTrue(error.info["game_may_be_up"])
        self.assertEqual(self.order[2:4], ["cli launch", "spawn_watch " + SNAP])     # watched at once
        self.assertEqual(self.game.adopted, [self.game.proc])      # by the pid and start time the reply gave
        self.assertEqual(self.game.killed, [self.game.proc])
        self.assertEqual(self.cli.verbs[-1], "restore")
        self.assertEqual(self.game.steps, [])

    def test_restore_waits_out_launch_in_flight_once_the_game_launch_named_is_ended(self):
        # The start was never recorded, so restore gives no verdict until LAUNCH_IN_FLIGHT_S after the claim.
        self.cli.queue("launch", {"refused": "not_recorded", "id": SNAP, "pid": PID, "created": CREATED}, 2)
        in_flight = {"held": False, "refused": "launch_in_flight", "id": SNAP}
        for _ in range(3):
            self.cli.queue("restore", in_flight, 2)
        before = self.game.now
        stop = self.session_error(self.start).info["stop"]
        self.assertEqual(stop["outcome"], "restored")
        self.assertEqual(self.cli.verbs.count("restore"), 4)
        self.assertEqual(self.game.now - before, 3 * session.RESTORE_RETRY_S)
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_launch_in_flight_for_longer_is_reported(self):
        self.started()
        for _ in range(40):
            self.cli.queue("restore", {"held": False, "refused": "launch_in_flight", "id": SNAP}, 2)
        before = self.game.now
        stop = self.session.stop()
        self.assertEqual((stop["outcome"], stop["refused"]), ("refused", "launch_in_flight"))
        self.assertEqual(self.game.now - before, session.LAUNCH_IN_FLIGHT_RETRY_TOTAL_S)
        self.assertTrue(stop["overlay_kept"])

    def test_a_launch_whose_reply_was_lost_may_have_started_a_game(self):
        for how in ("raised", "not_json"):
            with self.subTest(how=how):
                self.setUp()
                if how == "raised":
                    self.cli.raise_on = "launch"
                else:
                    self.cli.queue("launch", "Traceback (most recent call last): ...", 0)
                error = self.session_error(self.start)
                self.assertEqual(error.code, "launch_refused")
                self.assertTrue(error.info["game_may_be_up"])
                self.assertEqual(len(self.watches), 1)
                stop = error.info["stop"]
                # no pid to end it by: it is left up, with restore for once no game runs, and the overlay stays
                self.assertEqual(stop["outcome"], "game_left_up")
                self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch"])
                self.assertTrue(self.paths.overlay_dir.exists())

    def test_a_lost_launch_reply_of_the_sessions_own_ends_the_game_its_journal_names(self):
        # N7: the session's own launch, its reply lost after `started` was journaled
        snap = self.journal_a_start(ProcId(PID, CREATED))
        self.cli.queue("snapshot", {"id": snap}, 0)
        self.cli.raise_on = "launch"
        error = self.session_error(self.start)
        self.assertEqual(error.code, "launch_refused")
        self.assertEqual(self.game.killed, [ProcId(PID, CREATED)])
        stop = error.info["stop"]
        self.assertEqual(stop["outcome"], "restored")
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_which_launch_refusals_mean_that_no_game_started(self):
        claimed = ("x could not be written (e), so it is as it was. Nothing was started. The snapshot stays claimed, "
                   "so `launch` refuses it: `restore <id>` or `recover` finishes it 90 s after the claim")
        cases = (("gpu_busy", "the GPU is at 80% load", False), ("busy", "another session is in `restore`", False),
                 ("playset_not_restored", "content_load.json still holds another run's playset", False),
                 ("stale_snapshot", "the folder has changed since the snapshot was taken", False),
                 ("playset_unwritable", "content_load.json could not be read (e). Nothing was written", False),
                 ("playset_unwritable", claimed, True), ("start_unconfirmed", "PowerShell's reply was lost", True),
                 ("refusal_of_a_later_launch", "a name this session does not know", True))
        for refused, detail, may_be_up in cases:
            with self.subTest(refused=refused, may_be_up=may_be_up):
                self.setUp()
                self.cli.queue("launch", {"refused": refused, "id": SNAP, "detail": detail}, 2)
                error = self.session_error(self.start)
                self.assertEqual(error.code, "launch_refused")
                self.assertEqual(bool(error.info.get("game_may_be_up")), may_be_up)
                self.assertEqual(len(self.watches), 1 if may_be_up else 0)
                self.assertEqual(error.info["stop"]["outcome"], "game_left_up" if may_be_up else "restored")


class StopDuringStartTest(SessionTestCase):
    """C2 and I6: a stop asked while `start` runs is left to `start`, which stops once; a stop inside a stop."""

    def stop_inside(self, verb):
        inner = []
        self.cli.on_call = lambda argv: inner.append(self.session.stop()) if argv[0] == verb else None
        return inner

    def test_a_stop_during_launch_is_deferred_and_start_stops_once(self):
        inner = self.stop_inside("launch")
        error = self.session_error(self.start)
        self.assertEqual(error.code, "stopped")
        self.assertEqual(inner[0]["outcome"], "deferred_to_start")
        self.assertEqual(len(self.watches), 1)                  # the game launch started is watched...
        self.assertEqual(self.game.killed, [self.game.proc])    # ...and ended, by launch's own record
        self.assertEqual(self.game.steps, [])                   # and nothing was typed into it
        self.assertEqual(self.cli.verbs.count("restore"), 1)
        self.assertEqual(error.info["stop"]["outcome"], "restored")
        self.assertEqual(self.session.stop(), error.info["stop"])
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_a_stop_during_held_starts_nothing(self):
        inner = self.stop_inside("held")
        error = self.session_error(self.start)
        self.assertEqual((error.code, inner[0]["outcome"]), ("stopped", "deferred_to_start"))
        self.assertEqual(self.cli.verbs, ["held"])
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertEqual(self.watches, [])

    def test_a_stop_during_a_held_that_refuses_is_forgotten_with_it(self):
        inner = self.stop_inside("held")
        self.cli.queue("held", {"held": ["20261109T100000Z"]}, 0)
        self.assertEqual(self.session_error(self.start).code, "held_snapshot")
        self.assertEqual(inner[0]["outcome"], "deferred_to_start")
        self.cli.on_call = None                 # nothing was begun, so the stop asked has nothing left to stop
        self.assertEqual(self.start()["snapshot"], SNAP)

    def test_a_stop_during_the_snapshot_launches_nothing(self):
        inner = self.stop_inside("snapshot")
        error = self.session_error(self.start)
        self.assertEqual((error.code, inner[0]["outcome"]), ("stopped", "deferred_to_start"))
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "restore"])
        self.assertEqual(self.watches, [])
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_a_stop_while_the_window_is_awaited_ends_the_start(self):
        self.game.exists = False
        sleeps = []

        def on_sleep(seconds):
            sleeps.append(seconds)
            if len(sleeps) == 3:
                self.inner = self.session.stop()
        self.game.on_sleep = on_sleep
        error = self.session_error(self.start)
        self.assertEqual((error.code, self.inner["outcome"]), ("stopped", "deferred_to_start"))
        self.assertLess(self.game.now, session.WINDOW_WAIT_S)
        self.assertEqual(self.game.killed, [self.game.proc])
        self.assertEqual(self.cli.verbs.count("restore"), 1)

    def test_an_interrupt_during_launch_leaves_a_game_that_may_be_up_watched_and_unrestored(self):
        def interrupted(argv):
            if argv[0] == "launch":
                raise KeyboardInterrupt
        self.cli.on_call = interrupted
        with self.assertRaises(KeyboardInterrupt):
            self.start()
        self.assertEqual(len(self.watches), 1)          # the launch may have got as far as the game: it is watched
        stop = self.session.stop()
        self.assertEqual(stop["outcome"], "game_left_up")
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch"])
        self.assertTrue(self.paths.overlay_dir.exists())

    def test_a_stop_inside_a_stop_does_not_run_the_teardown_twice(self):
        self.started()
        self.watches[0].hangs = True
        inner = []

        def on_sleep(seconds):
            if not inner:
                self.watches[0].hangs = False
                inner.append(self.session.stop())
        self.game.on_sleep = on_sleep
        outer = self.session.stop()
        self.assertEqual((inner[0]["outcome"], outer["outcome"]), ("in_progress", "restored"))
        self.assertEqual((self.cli.verbs.count("restore"), len(self.game.killed)), (1, 1))
        self.assertEqual(self.session.stop(), outer)

    def test_an_interrupt_during_start_stops_and_is_raised_again(self):
        self.game.exists = False                # waiting for the window
        sleeps = []

        def on_sleep(seconds):
            sleeps.append(seconds)
            if len(sleeps) == 3:
                raise KeyboardInterrupt
        self.game.on_sleep = on_sleep
        with self.assertRaises(KeyboardInterrupt):
            self.start()
        self.assertEqual(self.game.killed, [self.game.proc])
        self.assertEqual(self.cli.verbs[-1], "restore")
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertTrue(self.session.status()["stopped"])


class GameLeftUpTest(SessionTestCase):
    """I1: a game that may still be up is not restored beside; a helper that has ended is replaced once."""

    def gone(self, proc):
        self.order.append("kill")
        raise HelperError("helper_gone", "the helper has ended")

    def test_a_helper_gone_at_the_kill_is_retried_through_a_fresh_helper(self):
        self.started()
        self.game.kill = self.gone
        fresh = fakes.FakeHelper()
        fresh_kill = fresh.kill

        def kill(proc):
            self.game.exited = True             # the game's process ends, whichever helper ended it
            return fresh_kill(proc)
        fresh.kill = kill
        self.fresh_helper = fresh
        reply = self.session.stop()
        self.assertEqual((fresh.adopted, fresh.killed), ([self.game.proc], [self.game.proc]))
        self.assertEqual(reply["outcome"], "restored")
        self.assertEqual(self.cli.verbs, ["restore"])
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_with_no_fresh_helper_the_game_is_left_up(self):
        self.started()
        self.game.kill = self.gone
        reply = self.session.stop()
        self.assertEqual(reply["outcome"], "game_left_up")
        self.assertEqual(self.cli.verbs, [])
        self.assertTrue(self.paths.overlay_dir.exists())

    def test_a_later_stop_tries_again_once_the_game_can_be_ended(self):
        self.started()
        self.game.kill = self.gone
        first = self.session.stop()
        self.assertEqual(first["outcome"], "game_left_up")
        del self.game.kill                      # the helper answers again
        second = self.session.stop()
        self.assertEqual(second["outcome"], "restored")
        self.assertEqual(self.cli.verbs, ["restore"])
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertEqual(self.session.stop(), second)
        self.assertTrue(Path(second["report"]).read_text("utf-8").startswith("Restore: restored"))


    def test_a_later_stop_finds_through_a_fresh_helper_that_the_game_has_ended(self):
        # The real helper is closed by the first stop, so a later one goes through a fresh helper, whose adopt
        # refuses a process that is no longer alive (win_helper._op_adopt): that is the game known ended.
        self.started()
        self.game.kill = self.gone
        self.assertEqual(self.session.stop()["outcome"], "game_left_up")
        self.game.exited = True                 # it ended by itself since
        fresh = fakes.FakeHelper()

        def adopt(proc):
            raise HelperError("not_ours", "no live process %d was created at %s" % (proc.pid, proc.created))
        fresh.adopt = adopt
        self.fresh_helper = fresh
        second = self.session.stop()
        self.assertEqual(second["outcome"], "restored")
        self.assertEqual((fresh.killed, self.cli.verbs), ([], ["restore"]))
        self.assertTrue(any("no live process" in note for note in second["notes"]))
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_with_no_process_to_end_the_next_step_does_not_promise_a_later_stop(self):
        self.cli.queue("launch", {"refused": "start_unconfirmed", "id": SNAP}, 2)
        stop = self.session_error(self.start).info["stop"]
        self.assertEqual(stop["outcome"], "game_left_up")
        self.assertIn("recover", stop["next"])
        self.assertIn(SNAP, stop["next"])
        self.assertNotIn("stop` again", stop["next"])


class ReusedPidStopTest(SessionTestCase):
    """#1588: the game died and another program took its process id before `stop`. `kill` refuses not_ours, which
    alone proves nothing (it refuses a live game it could not open, too), so `adopt` is asked again: refused
    not_ours as well, no live process has the game's pid and start time, and the stop restores as for a game
    found gone, instead of answering game_left_up for as long as that other program runs."""

    def reused(self, proc):
        self.order.append("kill")
        raise HelperError("not_ours", "process 7 is not the one this helper started (its id was reused)")

    def test_a_stop_after_the_pid_was_reused_finds_the_game_ended_and_restores(self):
        self.started()
        self.game.exited = True                 # the game died; watch records its exit
        self.game.process_gone = True           # and adopt finds no live process with its pid and start time
        self.game.kill = self.reused
        reply = self.session.stop()
        self.assertEqual((reply["outcome"], reply["stop_again"]), ("restored", False))
        self.assertEqual(self.order, ["kill", "watch_returned", "cli restore", "tcp_close", "helper_close"])
        self.assertEqual(self.cli.calls, [["restore", SNAP]])
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertNotIn("next", reply)
        note = next(note for note in reply["notes"] if "the game has ended" in note)
        self.assertIn("kill refused", note)
        self.assertIn("no live process 7", note)
        steps = [json.loads(line) for line in
                 (self.paths.backup_root / "runs" / SNAP / "steps.jsonl").read_text("utf-8").splitlines()]
        kill = next(step for step in steps if step["verb"] == "kill")
        self.assertEqual(kill["outcome"], "already_exited")
        self.assertEqual(self.session.stop(), reply)                    # final: not run again

    def test_the_restore_still_refuses_beside_a_game_it_finds_itself(self):
        # The helper's two refusals end the wait for the kill, not part 1's own look for a running game.
        self.started()
        self.game.exited = self.game.process_gone = True
        self.game.kill = self.reused
        self.cli.queue("restore", {"held": False, "refused": "game_still_up", "id": SNAP}, 2)
        reply = self.session.stop()
        self.assertEqual((reply["outcome"], reply["refused"], reply["stop_again"]), ("refused", "game_still_up", True))
        self.assertTrue(self.paths.overlay_dir.exists())

    def test_an_adopt_that_fails_otherwise_after_the_refused_kill_proves_nothing(self):
        self.started()
        self.game.kill = self.reused

        def adopt(proc):
            self.order.append("adopt")
            raise HelperError("backend_error", "OSError('access denied')")
        self.game.adopt = adopt
        reply = self.session.stop()
        self.assertEqual((reply["outcome"], reply["stop_again"]), ("game_left_up", True))
        self.assertEqual(self.cli.verbs, [])                            # no restore beside a game that may be up
        self.assertTrue(self.paths.overlay_dir.exists())
        self.assertEqual(self.order, ["kill", "adopt", "tcp_close", "helper_close"])
        self.assertTrue(any("backend_error" in note for note in reply["notes"]))

    def test_a_helper_that_ends_at_the_second_look_is_replaced_once_as_at_the_kill(self):
        self.started()
        self.game.exited = True
        self.game.kill = self.reused

        def adopt(proc):
            raise HelperError("helper_gone", "the helper has ended")
        self.game.adopt = adopt
        fresh = fakes.FakeHelper()

        def not_ours(proc):
            raise HelperError("not_ours", "no live process %d was created at %s" % (proc.pid, proc.created))
        fresh.adopt = not_ours
        self.fresh_helper = fresh
        reply = self.session.stop()
        self.assertEqual(reply["outcome"], "restored")
        self.assertEqual((fresh.killed, self.cli.verbs), ([], ["restore"]))

    def test_a_later_stop_finds_the_pid_reused_since_and_restores(self):
        # First the kill is refused beside a live game (game_left_up); the game then dies and its id is reused.
        self.started()
        self.game.kill = self.reused
        first = self.session.stop()
        self.assertEqual((first["outcome"], first["stop_again"]), ("game_left_up", True))
        self.game.exited = self.game.process_gone = True
        second = self.session.stop()
        self.assertEqual((second["outcome"], second["stop_again"]), ("restored", False))
        self.assertEqual(self.cli.verbs, ["restore"])
        self.assertFalse(self.paths.overlay_dir.exists())


class StopAgainTest(SessionTestCase):
    """R7, N3, N12: `stop_again` says whether a later stop can change anything, `next` names a verb that can work
    then, and a stop run again keeps what the one before found."""

    def failing_kill(self, proc):
        raise HelperError("not_ours", "process 7 changed under its id before it could be ended")

    def test_each_outcome_says_whether_a_later_stop_can_change_it(self):
        self.started()
        self.assertFalse(self.session.stop()["stop_again"])                 # restored: final
        self.setUp()
        self.started()
        self.cli.queue("restore", {"held": False, "refused": "game_still_up", "id": SNAP}, 2)
        refused = self.session.stop()
        self.assertEqual(refused["outcome"], "refused")
        self.assertTrue(refused["stop_again"])
        self.assertIn("`python3 -m game_qa stop` again", refused["next"])
        self.setUp()
        self.started()
        self.game.kill = self.failing_kill
        left_up = self.session.stop()
        self.assertEqual(left_up["outcome"], "game_left_up")
        self.assertTrue(left_up["stop_again"])                              # known by pid and start time
        self.assertIn("`python3 -m game_qa stop` again", left_up["next"])
        self.assertIn(SNAP, left_up["next"])

    def test_a_refusal_waiting_cannot_clear_is_final_and_names_recover(self):
        # X5: a damaged or missing stored file (`error`), or a restore that printed no JSON (`bad_reply`), stays
        # refused however often `stop` runs it again: the server must not keep serving for ever.
        for reply in ({"held": False, "refused": "error", "detail": "a copy in the store is damaged"},
                      "Traceback (most recent call last): ...",
                      {"refused": "BackupRootError", "detail": "the backups' folder does not exist"}):
            with self.subTest(reply=reply):
                self.setUp()
                self.started()
                self.cli.queue("restore", reply, 2)
                stop = self.session.stop()
                self.assertEqual(stop["outcome"], "refused")
                self.assertFalse(stop["stop_again"])
                self.assertTrue(server.final_stop(stop))
                self.assertNotIn("stop` again", stop["next"])
                self.assertIn("`python3 -m game_qa recover`", stop["next"])
                self.assertIn("`python3 -m game_qa remove-overlay`", stop["next"])
                self.assertIn(SNAP, stop["next"])
        for code in ("busy", "watch_still_recording", "launch_in_flight", "game_still_up", "GateError"):
            with self.subTest(clears_by_waiting=code):
                self.assertTrue(session._clears_by_waiting({"held": False, "refused": code}))

    def test_a_restored_stop_that_could_not_remove_the_overlay_says_what_to_run(self):
        # X3: restore put everything back, but a file in the overlay was held open
        self.started()
        with mock.patch.object(overlay, "remove", side_effect=PermissionError("a file is held open")):
            stop = self.session.stop()
        self.assertEqual((stop["outcome"], stop["overlay_kept"], stop["stop_again"]), ("restored", True, False))
        self.assertFalse(server.clean_stop(stop))
        self.assertIn("`python3 -m game_qa remove-overlay`", stop["next"])
        self.assertTrue(self.paths.overlay_dir.exists())

    def test_a_game_nothing_can_end_is_final_and_names_what_works_instead(self):
        for launch in ({"id": SNAP, "pid": PID, "created": "unknown"}, {"refused": "start_unconfirmed", "id": SNAP}):
            with self.subTest(launch=launch):
                self.setUp()
                self.cli.queue("launch", launch, 0 if "pid" in launch else 2)
                stop = self.session_error(self.start).info["stop"]
                self.assertEqual(stop["outcome"], "game_left_up")
                self.assertFalse(stop["stop_again"])
                self.assertNotIn("stop` again", stop["next"])
                self.assertIn("once no victoria 3 process runs", stop["next"].lower())
                self.assertIn("`python3 -m game_qa remove-overlay`", stop["next"])
                self.assertNotIn(str(self.paths.overlay_dir), stop["next"])

    def test_no_verb_reaches_the_game_after_a_stop_that_can_be_run_again(self):
        # The server now serves on after such a stop, so verbs can arrive: each is refused before any key, watch,
        # adopt or debugger call (the helper and the relay are closed, and the pid may be another program's).
        verbs = (("console", ("money 1000",)), ("run_setup", ("border",)), ("add_setup", ("late", "x = 1")),
                 ("events", ()), ("pick", (0,)),
                 ("read", (["c:FRA.gdp"],)), ("tag", ("GBR",)), ("enter_game", ()), ("advance", (5,)), ("shot", ()),
                 ("click", (0.5, 0.5)), ("try_event", ("x.1", None, ["c:FRA.gdp"])))
        for state in ("game_left_up", "refused"):
            with self.subTest(state=state):
                self.setUp()
                self.started()
                if state == "game_left_up":
                    self.game.kill = self.failing_kill
                else:
                    self.cli.queue("restore", {"held": False, "refused": "game_still_up", "id": SNAP}, 2)
                stop = self.session.stop()
                self.assertEqual((stop["outcome"], stop["stop_again"]), (state, True))
                before = (len(self.game.steps), len(self.watches), list(self.game.adopted), list(self.game.killed),
                          list(self.cli.verbs), list(self.game.order))
                for name, args in verbs:
                    self.assertEqual(self.session_error(getattr(self.session, name), *args).code, "stopped", name)
                self.assertEqual((len(self.game.steps), len(self.watches), list(self.game.adopted),
                                  list(self.game.killed), list(self.cli.verbs), list(self.game.order)), before)

    def test_a_stop_run_again_keeps_the_notes_of_the_one_before(self):
        self.started()
        self.game.kill = self.failing_kill
        first = self.session.stop()
        self.assertTrue(any("not_ours" in note for note in first["notes"]))
        del self.game.kill
        second = self.session.stop()
        self.assertEqual(second["outcome"], "restored")
        self.assertFalse(second["stop_again"])
        for note in first["notes"]:
            self.assertIn(note, second["notes"])
        self.assertTrue(any(note.startswith("stop was run again at ") and "game_left_up" in note
                            for note in second["notes"]))
        summary = Path(second["report"]).read_text("utf-8")
        self.assertIn("not_ours", summary)
        self.assertIn("stop was run again", summary)
        self.assertEqual(self.session.stop(), second)                       # final: not run a third time


class ClosingGame(Game):
    """As the real ProcessHelper: once closed, every call raises helper_gone."""

    def _gone(self):
        if self.closed:
            raise HelperError("helper_gone", "the helper has ended")

    def adopt(self, proc):
        self._gone()
        return super().adopt(proc)

    def kill(self, proc):
        self._gone()
        return super().kill(proc)


class SecondStopThroughAClosedHelperTest(SessionTestCase):
    """R7 (the re-review's script): the first stop's kill is refused while the helper's adopt still answers for
    the process, so game_left_up with stop_again, and that stop closed the helper. (When adopt refuses too, as it
    does once the pid really is another program's, the first stop already restores: `ReusedPidStopTest`.) The
    second stop goes helper_gone, the factory, a fresh adopt refused not_ours: the game counts as ended, watch is
    waited for, and only then is the snapshot restored, once."""

    def setUp(self):
        super().setUp()
        self.game = ClosingGame(self.user, self.order)
        self.session = session.Session(self.game, self.cli, self.spawn_watch, self.paths,
                                       sleep=self.game.sleep, clock=self.game.clock, helper_factory=self.new_helper)

    def test_the_second_stop_finds_the_game_gone_through_a_fresh_helper_and_restores_once(self):
        self.started()
        self.game.exited = True                         # the game has exited; watch recorded it (exit 0)

        def reused(proc):
            self.game._gone()
            raise HelperError("not_ours", "process 7 is not the one this helper started (its id was reused)")
        self.game.kill = reused
        first = self.session.stop()
        self.assertEqual((first["outcome"], first["stop_again"]), ("game_left_up", True))
        self.assertTrue(self.game.closed)
        self.assertNotIn("restore", self.cli.verbs)
        fresh = fakes.FakeHelper()

        def not_ours(proc):
            raise HelperError("not_ours", "no live process %d was created at %s" % (proc.pid, proc.created))
        fresh.adopt = not_ours
        self.fresh_helper = fresh
        second = self.session.stop()
        self.assertEqual((second["outcome"], second["stop_again"]), ("restored", False))
        self.assertTrue(any("helper had ended" in note for note in second["notes"]))
        self.assertEqual(self.cli.verbs.count("restore"), 1)    # never restored while it may have been up
        self.assertEqual(fresh.killed, [])


class OverlayVerdictTest(SessionTestCase):
    """I2: the overlay goes only once the game is known ended and the owner's playset is known back."""

    def test_the_overlay_goes_only_when_the_owners_playset_is_known_back(self):
        put_back = {"restored": ["content_load.json"], "removed": [], "held": True, "reason": "other_game_ran",
                    "playset_restored": True}
        left = {"restored": [], "removed": [], "held": True, "reason": "other_game_running", "playset_left": True}
        cases = ((RESTORED, True), ((put_back, 2), True), ((left, 2), False), (HELD, False),
                 (({"held": False, "refused": "game_still_up", "id": SNAP}, 2), False),
                 (({"held": False, "refused": "error", "detail": "a copy in the store is damaged"}, 2), False))
        for restore, removed in cases:
            with self.subTest(reply=restore[0]):
                self.setUp()
                self.started()
                self.cli.queue("restore", *restore)
                reply = self.session.stop()
                self.assertEqual(reply["overlay_removed"], removed)
                self.assertEqual(self.paths.overlay_dir.exists(), not removed)
                self.assertEqual(reply.get("overlay_kept", False), not removed)
                if not removed:
                    self.assertTrue(reply["overlay_kept_because"])

    def test_a_fixture_run_that_may_have_left_its_playset_keeps_the_overlay(self):
        held = {"held": True, "reason": "unwatched_stretch", "restored": [], "removed": []}
        cases = ((("launch", {"refused": "gpu_busy", "id": FIXTURE_SNAP}, 2), True, "restored"),
                 (("restore", held, 2), False, "held"),
                 # its game is ended by pid and start time, then the snapshot restored: the playset is back
                 (("launch", {"refused": "not_recorded", "id": FIXTURE_SNAP, "pid": FIXTURE_GAME.pid,
                              "created": FIXTURE_GAME.created}, 2), True, "restored"))
        for (verb, reply, code), removed, outcome in cases:
            with self.subTest(verb=verb, reply=reply):
                self.setUp()
                self.fixture_save.unlink()
                self.fixture_watch_code = 2         # for not_recorded: watch finds no `started`
                self.cli.queue("snapshot", {"id": FIXTURE_SNAP}, 0)
                self.cli.queue(verb, reply, code)
                error = self.session_error(self.start)
                self.assertEqual(error.code, "fixture_failed")
                self.assertEqual(self.paths.overlay_dir.exists(), not removed)
                stop = error.info["stop"]
                self.assertEqual((stop["outcome"], stop["snapshot"]), (outcome, FIXTURE_SNAP))
                self.assertEqual(server.clean_stop(error.info["stop"]), outcome == "restored")


class FixtureGameTest(SessionTestCase):
    """R6, N2, N7, R5: a game the fixture's own launch may have started is treated as the session's own: ended by
    its pid and start time, its watch waited for, its snapshot restored, and only then the overlay rules; with no
    process known, it is left up, and the stop reply never reads as clean."""

    def setUp(self):
        super().setUp()
        self.fixture_save.unlink()
        self.cli.queue("snapshot", {"id": FIXTURE_SNAP}, 0)

    def test_a_fixture_launch_not_recorded_is_ended_by_its_pid_and_start_time_then_restored(self):
        # B2, not_recorded: launch's reply names the game; watch finds no `started` and returns at once
        self.cli.queue("launch", {"refused": "not_recorded", "id": FIXTURE_SNAP, "pid": FIXTURE_GAME.pid,
                                  "created": FIXTURE_GAME.created, "detail": "the game started but ..."}, 2)
        self.fixture_watch_code = 2
        error = self.session_error(self.start)
        self.assertEqual(error.code, "fixture_failed")
        self.assertTrue(error.info["game_may_be_up"])
        self.assertEqual(error.info["game"], {"pid": FIXTURE_GAME.pid, "created": FIXTURE_GAME.created})
        self.assertEqual(len(self.fixture_watches), 1)                 # watched at once
        self.assertEqual((self.game.adopted, self.game.killed), ([FIXTURE_GAME], [FIXTURE_GAME]))
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch", "restore"])
        self.assertEqual(self.cli.calls[-1], ["restore", FIXTURE_SNAP])
        self.assertLess(self.order.index("kill"), self.order.index("cli restore"))    # never restored beside it
        stop = error.info["stop"]
        self.assertEqual((stop["outcome"], stop["snapshot"]), ("restored", FIXTURE_SNAP))
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertTrue((self.paths.run_root / FIXTURE_SNAP / "summary.md").is_file())

    def test_a_fixture_game_whose_process_is_not_known_is_left_up_and_the_stop_says_so(self):
        # B2, start_unconfirmed or a lost reply with nothing journaled: no pid and start time to end it by
        for how in ("start_unconfirmed", "lost"):
            with self.subTest(how=how):
                self.setUp()
                if how == "lost":
                    self.cli.raise_on = "launch"
                else:
                    self.cli.queue("launch", {"refused": "start_unconfirmed", "id": FIXTURE_SNAP}, 2)
                self.fixture_watch_code = 2
                error = self.session_error(self.start)
                stop = error.info["stop"]
                self.assertEqual((stop["outcome"], stop["snapshot"]), ("game_left_up", FIXTURE_SNAP))
                self.assertFalse(server.clean_stop(stop))
                self.assertIn(FIXTURE_SNAP, stop["next"])
                self.assertIn("recover", stop["next"])
                self.assertTrue(stop["game_unwatched"])         # N10: its watch has returned, recording no exit
                self.assertTrue(any("no `watch` follows" in note for note in stop["notes"]))
                self.assertNotIn("restore", self.cli.verbs)
                self.assertEqual(self.game.killed, [])
                self.assertTrue(self.paths.overlay_dir.exists())

    def test_a_fixture_game_that_outlasts_the_time_limit_is_ended_and_its_watch_waited_for(self):
        self.cli.queue("launch", {"id": FIXTURE_SNAP, "pid": FIXTURE_GAME.pid, "created": FIXTURE_GAME.created}, 0)
        self.fixture_watch_hangs = True         # the game never quits by itself
        error = self.session_error(self.start)
        self.assertGreaterEqual(self.game.now, fixture.FIXTURE_LIMIT_S)
        self.assertEqual(self.game.killed, [FIXTURE_GAME])
        stop = error.info["stop"]
        self.assertEqual(stop["outcome"], "restored")
        self.assertNotIn("watch had not returned", " ".join(stop.get("notes", [])))   # it recorded the exit
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_a_lost_fixture_launch_reply_ends_the_game_its_journal_names(self):
        # N7 for the fixture: the reply was lost after launch journaled `started`
        snap = self.journal_a_start(FIXTURE_GAME)
        self.cli.queued["snapshot"] = [({"id": snap}, 0)]
        self.fixture_snaps.add(snap)
        self.cli.raise_on = "launch"
        self.fixture_watch_code = 2
        error = self.session_error(self.start)
        self.assertEqual(error.info["game"], {"pid": FIXTURE_GAME.pid, "created": FIXTURE_GAME.created})
        self.assertEqual(self.game.killed, [FIXTURE_GAME])
        self.assertEqual(error.info["stop"]["outcome"], "restored")
        self.assertEqual(self.cli.calls[-1], ["restore", snap])

    def test_a_fixture_run_interrupted_while_its_game_runs_leaves_it_to_the_stop(self):
        self.cli.queue("launch", {"id": FIXTURE_SNAP, "pid": FIXTURE_GAME.pid, "created": FIXTURE_GAME.created}, 0)
        self.fixture_watch_hangs = True

        def on_sleep(_seconds):
            if self.game.now > 10:
                raise KeyboardInterrupt
        self.game.on_sleep = on_sleep
        with self.assertRaises(KeyboardInterrupt):
            self.start()
        self.game.on_sleep = None
        self.assertEqual(self.game.killed, [FIXTURE_GAME])              # the stop start ran ended it
        self.assertEqual(self.cli.verbs.count("restore"), 1)
        self.assertEqual(self.session.stop()["outcome"], "restored")

class LostSnapshotReplyTest(SessionTestCase):
    """B7, N14: a snapshot whose reply was lost may have been taken and left armed; the stop says so and how to
    finish it, and does not read as clean."""

    def test_a_lost_snapshot_reply_says_a_snapshot_may_have_been_taken(self):
        for how in ("raised", "not_json", "fixture_raised"):
            with self.subTest(how=how):
                self.setUp()
                if how == "raised":
                    self.cli.raise_on = "snapshot"
                elif how == "not_json":
                    self.cli.queue("snapshot", "Traceback ... (the id was printed to nobody)", 0)
                else:
                    self.fixture_save.unlink()
                    self.cli.raise_on = "snapshot"
                with self.assertRaises(Exception) as caught:
                    self.start()
                stop = caught.exception.info["stop"] if isinstance(caught.exception, session.SessionError) else \
                    self.session.stop()
                self.assertTrue(stop["snapshot_unknown"])
                self.assertIn("recover", stop["next"])
                self.assertFalse(server.clean_stop(stop))
                self.assertNotIn("restore", self.cli.verbs)
                self.assertFalse(self.paths.overlay_dir.exists())     # no launch ran: nothing names it

    def test_a_refused_snapshot_is_not_taken_for_a_lost_one(self):
        self.cli.queue("snapshot", {"refused": "unfinished_run", "unfinished": ["X"]}, 2)
        stop = self.session_error(self.start).info["stop"]
        self.assertNotIn("snapshot_unknown", stop)
        self.assertTrue(server.clean_stop(stop))


class FixtureKeyTest(SessionTestCase):
    """R3: the fixture's key covers the run's playset, its mode and the mods it loads, and the fixture's own
    launch uses that playset."""

    def key_for(self, playset, mods=None):
        loads = session.run_playset(playset, mods or self.paths.enabled_mods, DEPLOYED_WIN, OVERLAY_WIN)
        return fixture.key("1.15.0", loads, self.paths.deploy_dir, playset=playset)

    def test_a_fixture_made_for_one_playset_is_not_used_for_another(self):
        self.assertEqual(self.key_for("mod_only"), self.key)
        self.cli.queue("snapshot", {"id": FIXTURE_SNAP}, 0)
        reply = self.start(playset="current")           # the mod_only fixture is there: not this run's
        self.assertTrue(reply["fixture_made"])
        launch = self.cli.calls[2]
        self.assertEqual(launch[launch.index("--playset") + 1], "current")
        self.assertTrue((self.user / "save games" / ("te_qa_fixture_%s.v3" % self.key_for("current"))).is_file())

    def test_mod_only_leaves_out_the_owners_other_mods_and_current_does_not(self):
        more = [*self.paths.enabled_mods, r"C:\Users\someone\mod\AThirdMod"]
        self.assertEqual(self.key_for("mod_only", more), self.key_for("mod_only"))
        self.assertNotEqual(self.key_for("current", more), self.key_for("current"))
        self.assertNotEqual(self.key_for("current"), self.key_for("mod_only"))

    def test_a_dlc_switched_off_in_the_owners_playset_makes_another_fixture(self):
        # X4: launch keeps the owner's disabledDLC, and a DLC changes what a new game sets up
        self.paths.disabled_dlc = [{"paradoxAppId": "dlc_voice_of_the_people"}]
        self.cli.queue("snapshot", {"id": FIXTURE_SNAP}, 0)
        reply = self.start()                                # the fixture made with every DLC on is not this run's
        self.assertTrue(reply["fixture_made"])
        loads = session.run_playset("mod_only", self.paths.enabled_mods, DEPLOYED_WIN, OVERLAY_WIN)
        dlc_key = fixture.key("1.15.0", loads, self.paths.deploy_dir, playset="mod_only",
                              disabled_dlc=self.paths.disabled_dlc)
        self.assertNotEqual(dlc_key, self.key)
        self.assertTrue((self.user / "save games" / ("te_qa_fixture_%s.v3" % dlc_key)).is_file())

    def test_the_run_playset_is_what_launch_writes(self):
        self.assertEqual(session.run_playset("mod_only", [OTHER_MOD_WIN, DEPLOYED_WIN.lower() + "\\"], DEPLOYED_WIN,
                                             OVERLAY_WIN), [DEPLOYED_WIN.lower() + "\\", OVERLAY_WIN])
        self.assertEqual(session.run_playset("current", [OTHER_MOD_WIN, OVERLAY_WIN.upper()], DEPLOYED_WIN,
                                             OVERLAY_WIN), [OTHER_MOD_WIN, OVERLAY_WIN.upper()])


class RunPlaysetPinTest(unittest.TestCase):
    """`session.run_playset` copies `launch`'s rule (`__main__._plan_playset`, which the session cannot import):
    pinned against the `enabled` list a real in-process `launch` journals, so a drift fails here. gate's
    list_games, start_game, windows_path and sample_gpu are fakes: nothing is started."""

    WORKSHOP = "C:\\Program Files (x86)\\Steam\\steamapps\\workshop\\content\\529340\\"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.user, self.backups, base_game = root / "Victoria 3", root / "backups", root / "game"
        (self.user / "save games").mkdir(parents=True)
        self.deploy = self.user / "mod" / "Vic3TimelineExtended"
        self.deploy.mkdir(parents=True)
        (base_game / "binaries").mkdir(parents=True)
        (base_game / "binaries" / "victoria3.exe").write_bytes(b"MZ")
        self.this_mod = self.windows(self.deploy)
        env = {"VIC3_USER_DATA": str(self.user), "VIC3_QA_BACKUPS": str(self.backups),
               "VIC3_BASE_GAME": str(base_game), "VIC3_MOD_DEPLOY_TARGET": str(self.deploy)}
        started = ProcId(4242, "2026-11-10T14:00:00.0000000Z")
        for patch in (mock.patch.dict("os.environ", env), mock.patch.object(gate, "list_games", return_value=[]),
                      mock.patch.object(gate, "sample_gpu", return_value=[gate.GpuSample(14, 1607, 10240)] * 5),
                      mock.patch.object(gate, "start_game", return_value=started),
                      mock.patch.object(gate, "windows_path", side_effect=lambda path, *a, **k: self.windows(path))):
            patch.start()
            self.addCleanup(patch.stop)

    @staticmethod
    def windows(path) -> str:
        return "W:" + str(path).replace("/", "\\")

    def cli(self, *argv) -> tuple[dict, int]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return json.loads(out.getvalue()), code

    def test_the_run_playset_is_the_list_launch_writes(self):
        cases = {"the owner's mods, this one among them": [self.WORKSHOP + "1", self.WORKSHOP + "2", self.this_mod],
                 "this mod spelled otherwise": [self.WORKSHOP + "1", self.this_mod.lower() + "\\"],
                 "the overlay enabled already": [self.this_mod, OVERLAY_WIN.upper()]}
        runs = [(label, owner, mode) for label, owner in cases.items() for mode in session.PLAYSETS]
        for n, (label, owner, mode) in enumerate(runs):
            with self.subTest(owners=label, mode=mode):
                os.environ["VIC3_QA_BACKUPS"] = str(self.backups) + str(n)      # one run each: nothing to finish
                (self.user / "content_load.json").write_text(
                    "\ufeff" + json.dumps({"enabledMods": [{"path": m} for m in owner], "disabledDLC": []}),
                    encoding="utf-8")
                snap, code = self.cli("snapshot")
                self.assertEqual(code, 0, snap)
                launched, code = self.cli("launch", snap["id"], "--permission", PERMISSION, "--playset", mode,
                                          "--add-mod", OVERLAY_WIN, "--", "-gdpr-compliant")
                self.assertEqual(code, 0, launched)
                self.assertEqual(session.run_playset(mode, enabled_mods(self.user), self.this_mod,
                                                     OVERLAY_WIN), launched["playset"]["enabled"])


class StopsTest(SessionTestCase):
    """I3: a stop left over is released before anything is typed; only a breakpoint stop is evaluated at."""

    def test_a_late_stop_is_released_before_the_next_read(self):
        self.started()
        self.game.stops = False
        with mock.patch.object(session, "STOP_WAIT_S", 0.01):
            error = self.session_error(self.session.read, ["c:FRA.gdp"])
        self.assertEqual(error.code, "no_stop")
        self.assertTrue(error.info["maybe_stopped"])
        self.game.stops = True
        self.game.adapter.stop()                # the first read's stop comes after all
        self.game.adapter.values = {"c:FRA.gdp": "7"}
        self.assertEqual([r.value for r in self.session.read(["c:FRA.gdp"])], [7.0])
        self.assertFalse(self.game.adapter.stopped)            # not left frozen at the breakpoint
        self.assertEqual(self.typed().count("event te_qa.1"), 2)
        self.assertFalse(self.session.status()["maybe_stopped"])

    def test_a_stop_for_another_reason_is_not_taken_for_the_reads(self):
        self.started()
        self.game.adapter.stop_reason = "pause"
        error = self.session_error(self.session.read, ["c:FRA.gdp"])
        self.assertEqual((error.code, error.info["reason"]), ("unexpected_stop", "pause"))
        self.assertNotIn("evaluate", self.game.adapter.commands)
        self.assertFalse(self.game.adapter.stopped)
        self.assertTrue(error.info["maybe_stopped"])           # the read's own stop may still come
        self.game.adapter.stop_reason = "breakpoint"
        self.game.adapter.values = {"c:FRA.gdp": "7"}
        self.assertEqual([r.value for r in self.session.read(["c:FRA.gdp"])], [7.0])

    def test_a_resume_that_fails_twice_says_maybe_stopped_and_the_next_verb_drains_first(self):
        self.started()
        self.game.adapter.values = {"c:FRA.gdp": "7"}
        self.game.adapter.failing_continues = 2
        error = self.session_error(self.session.read, ["c:FRA.gdp"])
        self.assertEqual(error.code, "debugger")
        self.assertTrue(error.info["maybe_stopped"])
        self.assertTrue(self.game.adapter.stopped)
        self.assertTrue(self.session.status()["maybe_stopped"])
        typed_before = len(self.game.steps)

        def resumed_before_any_key(sent):
            self.assertFalse(self.game.adapter.stopped)
        self.game.on_step = resumed_before_any_key
        self.game.on("select_event_option list", success=["No pending events"])
        self.assertEqual(self.session.events(), [])
        self.assertGreater(len(self.game.steps), typed_before)
        self.assertFalse(self.session.status()["maybe_stopped"])

    def test_a_game_that_stays_stopped_refuses_the_next_verb_before_any_key(self):
        self.started()
        self.game.adapter.values = {"c:FRA.gdp": "7"}
        self.game.adapter.failing_continues = 4
        self.session_error(self.session.read, ["c:FRA.gdp"])
        steps = len(self.game.steps)
        error = self.session_error(self.session.events)
        self.assertEqual(error.code, "maybe_stopped")
        self.assertEqual(len(self.game.steps), steps)


class SendGuardTest(SessionTestCase):
    """X1: inside one call too (start's console-ready loop, advance's rounds, enter_game's clicks), no key, focus or
    click goes out once `watch` has recorded the game's exit, or once the helper cannot prove the process is the
    game by its pid and start time: the helper itself sends by pid alone, and a pid may be another program's."""

    def test_start_types_nothing_once_the_watch_has_recorded_the_exit(self):
        self.game.console_never_opens = True        # the probes never land: the loop would run its whole 180 s
        marks = {}

        def on_sleep(seconds):
            # The game dies as its save loads, while the console waits for its first probe; watch records it
            # (exit 0), and the fake's window still answers for the pid, as a reused pid's program's would.
            if self.game.steps and "exit_at" not in marks:
                self.game.exited = True
                marks["exit_at"] = len(self.game.steps)
        self.game.on_sleep = on_sleep
        error = self.session_error(self.start)
        self.game.on_sleep = None
        self.assertEqual(error.code, "watch_ended")
        self.assertEqual(self.watches[0].poll(), 0)
        self.assertEqual(len(self.game.steps), marks["exit_at"])      # not one key more (83 before the guard)
        self.assertEqual(self.cli.verbs[-1], "restore")                # start failed into its normal stop
        self.assertEqual(self.session_error(self.session.events).code, "stopped")

    def test_advance_types_nothing_once_the_watch_has_recorded_the_exit(self):
        self.started()
        self.session.enter_game()
        self.game.days_per_second = 0.5             # several rounds
        marks = {}

        def on_sleep(seconds):
            # During the first unpaused wait the game exits, and watch records it (poll() -> 0); the fake's window
            # still answers for the pid, as one a reused pid's program has would.
            if not self.game.paused and "exit_at" not in marks:
                self.game.exited = True
                marks["exit_at"] = len(self.game.steps)
        self.game.on_sleep = on_sleep
        error = self.session_error(self.session.advance, 30)
        self.game.on_sleep = None
        self.assertEqual(self.watches[0].poll(), 0)
        self.assertEqual(len(self.game.steps), marks["exit_at"])
        self.assertIn(error.code, ("watch_ended", "left_running"))     # it may have been left unpaused
        self.assertEqual(self.session_error(self.session.events).code, "watch_ended")

    def test_enter_game_clicks_nothing_once_the_game_cannot_be_proved(self):
        for how in ("exited", "process_gone"):
            with self.subTest(how=how):
                self.setUp()
                self.started()
                clicks = self.game.order.count("click")

                def on_command(text, how=how):
                    # the console's own front check before the first click: then the game is gone
                    setattr(self.game, how, True)
                self.game.on_command = on_command
                error = self.session_error(self.session.enter_game)
                self.game.on_command = None
                self.assertEqual(error.code, "watch_ended")
                self.assertEqual(self.game.order.count("click"), clicks)
                steps = len(self.game.steps)
                self.assertEqual(self.session_error(self.session.console, "money 1000").code, "watch_ended")
                self.assertEqual(len(self.game.steps), steps)

    def test_focus_is_proved_too(self):
        self.started()
        focus_calls = self.game.focus_calls
        self.game.process_gone = True
        with self.assertRaises(session.SessionError) as caught:
            self.session._sends.focus(self.game.proc.pid)
        self.assertEqual(caught.exception.code, "watch_ended")
        self.assertEqual(self.game.focus_calls, focus_calls)              # the helper's focus was never reached
        self.game.process_gone = False
        self.assertEqual(self.session_error(self.session._sends.focus, self.game.proc.pid).code, "watch_ended")
        self.assertEqual(self.game.focus_calls, focus_calls)

    def test_the_console_and_the_clicks_send_through_the_proof(self):
        self.started()
        self.assertIsInstance(self.session._console._helper, session._ProvedHelper)
        self.assertIs(self.session._sends._session, self.session)

    def test_the_proved_helper_passes_on_only_the_calls_that_send_nothing(self):
        # #1588: a call added to the helper later must not reach the game unproved through the pass-through.
        self.started()
        sends = self.session._sends
        self.assertEqual(sends.window(PID), self.game.window(PID))
        self.assertEqual(sends.presence().foreground, fakes.GAME_HWND)
        self.game.type_unicode = lambda pid, text: self.fail("an input call the proof does not know went out")
        for name in ("type_unicode", "kill", "launch", "adopt", "screenshot", "idle_ms", "tcp_open", "tcp_send",
                     "tcp_recv", "tcp_close", "close"):
            with self.subTest(name=name):
                with self.assertRaises(AttributeError) as caught:
                    getattr(sends, name)
                self.assertIn(name, str(caught.exception))
        self.assertFalse(hasattr(sends, "type_unicode"))
        self.assertEqual(session._ProvedHelper._UNPROVED, {"window", "presence"})

    def test_the_console_uses_no_helper_call_the_proved_helper_refuses(self):
        # What the Console calls on its helper, read from its source: each is proved here or on the list, so
        # the refusal above can never be the Console's own in a path the other tests do not reach.
        source = Path(session.__file__).with_name("console.py").read_text(encoding="utf-8")
        used = set(re.findall(r"self\._helper\.(\w+)", source))
        self.assertIn("keys", used)
        proved = {name for name in ("keys", "focus", "click") if name in vars(session._ProvedHelper)}
        self.assertEqual(proved, {"keys", "focus", "click"})
        self.assertLessEqual(used, proved | session._ProvedHelper._UNPROVED)

    def test_a_pid_whose_start_time_no_longer_matches_gets_no_key_though_watch_still_runs(self):
        self.started()
        steps = len(self.game.steps)
        self.game.process_gone = True               # watch has not looked yet; the helper's adopt refuses not_ours
        self.assertIsNone(self.watches[0].poll())
        error = self.session_error(self.session.console, "money 1000")
        self.assertEqual(error.code, "watch_ended")
        self.assertIn("not_ours", error.detail)
        self.assertEqual(len(self.game.steps), steps)
        self.game.process_gone = False              # latched: a later verb types nothing either
        self.assertEqual(self.session_error(self.session.events).code, "watch_ended")
        self.assertEqual(len(self.game.steps), steps)


class WatchCheckTest(SessionTestCase):
    """N1: before any key or click, `watch` must still be following the game. A watch that recorded the exit ends
    the verbs for good; one that stopped without recording it is run again only once the game is proved alive by
    its pid and start time (never by a window that has its pid: a pid may be another program's by now)."""

    def typed_by(self, verb) -> int:
        before = len(self.game.steps)
        self.assertEqual(self.session_error(verb).code, "watch_ended")
        return len(self.game.steps) - before

    def test_a_watch_that_recorded_the_exit_ends_the_verbs_for_good(self):
        # B1: the game exited (watch returned 0) and another program with a window took its pid
        self.started()
        adopted = len(self.game.adopted)
        self.game.exited = True
        self.game.on("select_event_option list", success=["No pending events"])
        self.assertEqual(self.typed_by(self.session.events), 0)
        self.assertEqual(len(self.watches), 1)                  # never run again
        self.assertEqual(len(self.game.adopted), adopted)       # nor adopted again: there is nothing to prove
        for _ in range(session.WATCH_RESPAWNS + 1):
            self.assertEqual(self.typed_by(self.session.events), 0)
        self.assertEqual(len(self.watches), 1)

    def test_a_watch_that_failed_beside_the_game_is_run_again_once_the_game_is_proved_alive(self):
        self.started()
        self.watches[0].dies = True                             # exit 1: it stopped without recording an exit
        self.game.adapter.values = {"c:FRA.gdp": "1"}
        mark = len(self.order)
        self.session.read(["c:FRA.gdp"])
        self.assertEqual(len(self.watches), 2)
        later = self.order[mark:]
        self.assertEqual(later[:2], ["adopt", "spawn_watch " + SNAP])     # proved by pid and start time first
        self.assertEqual(self.session.status()["watch_respawns"], 1)
        reply = self.session.stop()
        self.assertTrue(any("run again" in note for note in reply["notes"]))
        self.assertIn("watch_respawned", Path(reply["report"]).read_text("utf-8"))

    def test_a_watch_that_failed_with_the_game_gone_ends_the_verbs(self):
        self.started()
        self.watches[0].dies = True
        self.game.process_gone = True                           # the window may still answer for the pid
        self.assertEqual(self.typed_by(lambda: self.session.read(["c:FRA.gdp"])), 0)
        self.assertEqual(len(self.watches), 1)
        self.game.process_gone = False                          # a later look proves nothing: it stays ended
        self.assertEqual(self.typed_by(lambda: self.session.read(["c:FRA.gdp"])), 0)
        self.assertEqual(len(self.watches), 1)

    def test_any_doubt_about_the_game_ends_the_verbs(self):
        self.started()
        self.watches[0].dies = True

        def adopt(proc):
            raise HelperError("helper_gone", "the helper has ended")
        self.game.adopt = adopt
        self.assertEqual(self.typed_by(self.session.events), 0)
        self.assertEqual(len(self.watches), 1)

    def test_a_watch_that_keeps_failing_is_run_again_only_so_often(self):
        self.started()
        self.game.on("select_event_option list", success=["No pending events"])
        for n in range(session.WATCH_RESPAWNS):
            self.watches[-1].dies = True
            self.assertEqual(self.session.events(), [])
        self.watches[-1].dies = True
        self.assertEqual(self.typed_by(self.session.events), 0)
        self.assertEqual(len(self.watches), 1 + session.WATCH_RESPAWNS)


class FrozenGame(Game):
    """While the debugger has the game stopped, a read command typed into it waits; it runs (and stops at the
    breakpoint) once the game is resumed (seen live: the answer to `continue`, then `continued`, then `stopped`)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.waiting: list[str] = []

    def _run(self, text):
        if text == "event " + overlay.READ_EVENT and self.adapter.stopped:
            self.waiting.append(text)
            return
        super()._run(text)


class LateStopTest(SessionTestCase):
    """N5 (B6): a stop that comes after its read gave up is taken by the next read, whose own command then runs
    once the game is resumed, and stops it again. The next verb that types releases that stop first, without
    waiting for one."""

    def setUp(self):
        super().setUp()
        self.game = FrozenGame(self.user, self.order)
        self.session = session.Session(self.game, self.cli, self.spawn_watch, self.paths,
                                       sleep=self.game.sleep, clock=self.game.clock, helper_factory=self.new_helper)
        adapter, answer = self.game.adapter, self.game.adapter._answer

        def _answer(req):
            was_stopped = adapter.stopped
            answer(req)
            if req["command"] == "continue" and was_stopped and self.game.waiting:
                self.game.waiting.clear()       # resumed: the read command typed while frozen runs, and stops
                adapter.stop()
        adapter._answer = _answer

    def test_the_next_verb_releases_a_stop_left_by_a_late_one_before_any_key(self):
        self.started()
        self.game.adapter.values = {"c:FRA.gdp": "7"}
        self.game.stops = False
        with mock.patch.object(session, "STOP_WAIT_S", 0.01):
            self.assertEqual(self.session_error(self.session.read, ["c:FRA.gdp"]).code, "no_stop")
        self.game.stops = True
        armed = [True]

        def late(_n):
            if armed[0]:                        # read #1's stop lands as read #2's command is being typed
                armed[0] = False
                self.game.adapter.stop()
        self.game.on_step = late
        self.assertEqual([r.value for r in self.session.read(["c:FRA.gdp"])], [7.0])
        self.game.on_step = None
        self.assertTrue(self.game.adapter.stopped)              # frozen at read #2's own breakpoint
        frozen_at_key = []
        self.game.on_step = lambda _n: frozen_at_key.append(self.game.adapter.stopped)
        self.game.on("select_event_option list", success=["No pending events"])
        self.assertEqual(self.session.events(), [])
        self.assertTrue(frozen_at_key)
        self.assertFalse(any(frozen_at_key))                    # released before the first key
        self.assertFalse(self.game.adapter.stopped)

    def test_a_stop_that_cannot_be_released_types_nothing(self):
        self.started()
        self.game.adapter.stop()                                # a stop nobody has taken
        self.game.adapter.failing_continues = 4
        steps = len(self.game.steps)
        error = self.session_error(self.session.events)
        self.assertEqual(error.code, "maybe_stopped")
        self.assertEqual(len(self.game.steps), steps)
        self.assertTrue(self.session.status()["maybe_stopped"])


class PauseTest(SessionTestCase):
    """I4: a round that may have left the game running says so and refuses more time; the pause is proved."""

    def test_a_helper_failure_after_the_unpause_key_is_left_running_and_refuses_more_time(self):
        self.started()
        self.session.enter_game()
        keys = self.game.keys
        armed = [True]

        def keys_then_fail(pid, steps):
            keys(pid, steps)
            if armed[0] and {"scan": SPACE} in steps:
                armed[0] = False
                raise HelperError("helper_gone", "the pipe broke after the key went out")
        self.game.keys = keys_then_fail
        error = self.session_error(self.session.advance, 5)
        self.assertEqual(error.code, "left_running")
        self.assertIn("unpaused", error.detail)
        self.assertFalse(self.game.paused)                  # and so it is
        spaces, clicks = self.order.count("space"), len(self.game.clicks)
        self.assertEqual(self.session_error(self.session.advance, 5).code, "left_running")
        self.assertEqual(self.session_error(self.session.enter_game).code, "left_running")
        self.assertEqual((self.order.count("space"), len(self.game.clicks)), (spaces, clicks))
        self.assertTrue(self.session.status()["left_running"])

    def test_a_pause_that_did_not_take_is_sent_once_more_and_proved(self):
        self.started()
        self.session.enter_game()
        self.game.dropped_pauses = 1
        spaces = self.order.count("space")
        reached = self.session.advance(5)
        self.assertTrue(self.game.paused)
        self.assertEqual(self.order.count("space") - spaces, 3)        # unpause, the lost pause, one more
        self.assertEqual(dt.date(*reached), self.game.date)

    def test_a_game_that_will_not_pause_is_left_running(self):
        self.started()
        self.session.enter_game()
        self.game.dropped_pauses = 99
        spaces = self.order.count("space")
        self.assertEqual(self.session_error(self.session.advance, 5).code, "left_running")
        self.assertEqual(self.order.count("space") - spaces, 3)
        self.assertTrue(self.session.status()["left_running"])

    def test_a_date_that_cannot_be_read_after_the_clicks_is_not_entered_and_clicks_no_more(self):
        self.started()
        self.game.logs_date = False
        error = self.session_error(self.session.enter_game)
        self.assertEqual(error.code, "not_entered")
        self.assertEqual(len(self.game.clicks), 2)
        self.game.logs_date = True
        self.assertEqual(self.session_error(self.session.enter_game).code, "left_running")
        self.assertEqual(self.session_error(self.session.advance, 3).code, "left_running")
        self.assertEqual(len(self.game.clicks), 2)


class RestoreRetryTest(SessionTestCase):
    """I5: `busy` is retried for a minute; a later stop after a refusal runs restore again."""

    BUSY = {"held": False, "refused": "busy", "detail": "another session is in `snapshot`"}

    def test_busy_is_retried_every_five_seconds(self):
        self.started()
        self.cli.queue("restore", self.BUSY, 2)
        self.cli.queue("restore", self.BUSY, 2)
        now = self.game.now
        self.assertEqual(self.session.stop()["outcome"], "restored")
        self.assertEqual(self.cli.verbs, ["restore"] * 3)
        self.assertEqual(self.game.now - now, 2 * session.RESTORE_RETRY_S)

    def test_busy_for_longer_is_reported_and_a_later_stop_runs_restore_again(self):
        self.started()
        for _ in range(int(session.BUSY_RETRY_TOTAL_S / session.RESTORE_RETRY_S) + 1):
            self.cli.queue("restore", self.BUSY, 2)
        now = self.game.now
        first = self.session.stop()
        self.assertEqual((first["outcome"], first["refused"]), ("refused", "busy"))
        self.assertEqual(self.game.now - now, session.BUSY_RETRY_TOTAL_S)
        self.assertTrue(self.paths.overlay_dir.exists())
        second = self.session.stop()
        self.assertEqual(second["outcome"], "restored")
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertEqual(len(self.game.killed), 1)              # the game was ended once
        self.assertEqual(self.session.stop(), second)
        self.assertEqual(self.cli.verbs.count("restore"), 14)


class MinorsTest(SessionTestCase):
    def test_a_bad_setup_is_refused_before_anything_and_the_session_can_start_after(self):
        error = self.session_error(self.start, setups={"border": "set_variable = { x"})
        self.assertEqual(error.code, "overlay_refused")
        self.assertEqual(self.cli.calls, [])
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertEqual(self.start(setups={"border": "set_variable = x"})["snapshot"], SNAP)

    def test_with_an_owners_save_there_is_no_country_select_to_click(self):
        (self.user / "save games" / "france_1850.v3").write_bytes(b"the owner's own save")
        self.started(save="france_1850")
        self.game.entered = True                # the owner's save opens in play
        self.assertEqual(self.session_error(self.session.enter_game).code, "not_on_country_select")
        reached = self.session.advance(3)
        self.assertGreaterEqual(dt.date(*reached), START_DATE + dt.timedelta(days=3))
        self.assertEqual(self.game.clicks, [])


class SelfChecksTest(SessionTestCase):
    """#1601: the mod's TE_SELF_CHECK lines are kept with the fixture, read by a verb, and listed at the stop."""

    @staticmethod
    def logged(*messages: str) -> list[str]:
        return ["[18:27:01][jomini_effect_impl.cpp:459]: " + message for message in messages]

    def game_logs(self, *messages: str) -> None:
        """The game logs these and has not written them to its file yet."""
        for message in messages:
            self.game._logged("jomini_effect_impl.cpp:459", message)

    def game_wrote(self, *messages: str) -> None:
        with open(self.user / "logs" / "debug.log", "a", encoding="utf-8", newline="\n") as f:
            f.write("".join(line + "\n" for line in self.logged(*messages)))

    def run_log(self) -> str:
        path = self.paths.run_root / SNAP / "debug.log"
        return path.read_text("utf-8") if path.exists() else ""

    def steps(self, verb: str) -> list[dict]:
        lines = (self.paths.run_root / SNAP / "steps.jsonl").read_text("utf-8").splitlines()
        return [step for step in map(json.loads, lines) if step["verb"] == verb]

    def a_fixture_run(self, *messages: str) -> str:
        """The fixture is missing, and the run that makes it logs `messages`: a real snapshot of the folder,
        whose `restore` leaves the run's log in its `run_logs/`, as part 1's does. Its id."""
        self.fixture_save.unlink()
        snap = snapshot.take(self.user, self.paths.backup_root,
                             now=dt.datetime(2026, 11, 10, 14, 55, tzinfo=dt.timezone.utc))
        self.assertEqual(snap.id, FIXTURE_SNAP)             # taken before the session's own, as in a real start
        self.cli.queue("snapshot", {"id": snap.id}, 0)

        def restore(argv):
            if argv[:2] == ["restore", snap.id] and messages:
                (snap.dir / "run_logs").mkdir()
                (snap.dir / "run_logs" / "debug.log").write_text(
                    "".join(line + "\n" for line in self.logged(*messages)), encoding="utf-8")
        self.cli.on_call = restore
        return snap.id

    SETUP_LINES = ("common/on_actions/te_decentralized_laws_selfcheck_on_actions.txt:46: TE_SELF_CHECK OK "
                   "decentralized_law_baseline (the history baseline reached them)",
                   "common/scripted_effects/gm_landmark_effects.txt:145: TE_MONUMENTS: landmark arc_de_triomphe "
                   "placed in Ile-de-France for FRA: 15 levels recorded",
                   "common/scripted_effects/te_unemployment_effects.txt:110: TE_SELF_CHECK BROKEN "
                   "unemployment_share_read state=Corsica conv=0.000 exact=0.038")

    def test_making_the_fixture_keeps_its_runs_lines_beside_it_under_the_backup_root(self):
        fixture_snap = self.a_fixture_run(*self.SETUP_LINES)
        reply = self.start()
        self.assertTrue(reply["fixture_made"])
        folder = self.paths.backup_root / "fixtures" / self.key
        self.assertEqual((folder / "lines.log").read_text("utf-8").splitlines(), self.logged(*self.SETUP_LINES))
        record = json.loads((folder / "record.json").read_text("utf-8"))
        self.assertEqual((record["kept"], record["snapshot"], record["lines"], record["self_checks"]),
                         (True, fixture_snap, 3, 2))
        (step,) = self.steps("fixture_lines")
        self.assertEqual((step["outcome"], step["snapshot"], step["lines"]), ("kept", fixture_snap, 3))
        # nothing of it is in the game's folder
        self.assertEqual([p for p in self.user.rglob("*") if p.name in ("lines.log", "record.json", "fixtures")], [])
        # and the session's verdicts include them, though no session ever logs them again
        found = self.session.self_checks()
        self.assertEqual(found["broken"], ["unemployment_share_read"])
        self.assertEqual([(c["name"], c["verdict"], c["source"]) for c in found["checks"]], [
            ("unemployment_share_read", "BROKEN", "fixture"), ("decentralized_law_baseline", "OK", "fixture")])
        self.assertEqual((found["fixture"]["snapshot"], found["fixture"]["lines"]), (fixture_snap, 3))

    def test_a_fixture_whose_lines_cannot_be_kept_is_still_the_fixture(self):
        self.a_fixture_run()                    # its restore leaves no run_logs
        reply = self.start()
        self.assertTrue(reply["fixture_made"])
        (step,) = self.steps("fixture_lines")
        self.assertEqual(step["outcome"], "failed")
        self.assertIn("debug.log", step["detail"])
        folder = self.paths.backup_root / "fixtures" / self.key
        self.assertEqual([p.name for p in folder.iterdir()], ["record.json"])       # a record that nothing is kept
        found = self.session.self_checks()
        self.assertEqual((found["fixture"]["key"], found["fixture"]["kept"]), (self.key, False))
        self.assertIn("could not be kept from snapshot %s" % FIXTURE_SNAP, found["fixture"]["detail"])
        self.assertEqual(found["checks"], [])

    def stale_record(self, key: str, snap: str = "20261109T120000Z") -> Path:
        """What an earlier fixture of `key` left: its run's lines, with a record that vouches for them."""
        kept = self.paths.backup_root / "fixtures" / key
        kept.mkdir(parents=True)
        (kept / "lines.log").write_text("".join(line + "\n" for line in self.logged(
            "common/a.txt:1: TE_SELF_CHECK OK from_an_earlier_fixtures_run")), encoding="utf-8")
        (kept / "record.json").write_text(json.dumps({"key": key, "kept": True, "snapshot": snap, "lines": 1,
                                                      "self_checks": 1, "at": "2026-11-09T12:01:00Z"}), "utf-8")
        return kept

    def test_a_fixture_made_again_under_its_key_never_shows_the_earlier_runs_lines(self):
        # Blocking 2 of #1650's review: the owner deleted the save, the same build makes it again under the same
        # key, and this time nothing can be kept. The old record must not vouch for the new fixture.
        kept = self.stale_record(self.key)
        self.a_fixture_run()                    # its restore leaves no run_logs: keeping fails
        self.start()
        self.assertNotIn("from_an_earlier_fixtures_run", "".join(p.read_text("utf-8") for p in kept.iterdir()))
        found = self.session.self_checks()
        self.assertEqual((found["fixture"]["kept"], found["checks"]), (False, []))

    def test_a_fixture_whose_run_was_held_after_the_save_was_kept_has_no_lines_and_says_why(self):
        # `fixture.make` renames the save, then its restore holds: `keep_lines` is never called, and the save
        # is there for the next start to find. The earlier record of that key is gone by then.
        kept = self.stale_record(self.key)
        self.a_fixture_run(*self.SETUP_LINES)
        self.cli.queue("restore", {"restored": [], "removed": [], "held": True, "reason": "other_game_ran"}, 2)
        error = self.session_error(self.start)
        self.assertEqual(error.code, "fixture_failed")
        self.assertTrue(self.fixture_save.is_file())
        record = json.loads((kept / "record.json").read_text("utf-8"))
        self.assertEqual(record["kept"], False)
        self.assertFalse((kept / "lines.log").exists())
        run = self.paths.run_root / "20261110T160000Z"
        run.mkdir(parents=True)
        (run / "steps.jsonl").write_text(json.dumps({"verb": "fixture", "outcome": "found",
                                                     "save": self.fixture_save.stem}) + "\n", encoding="utf-8")
        found = session.selfchecks.of_run(self.paths.backup_root, run.name)
        self.assertEqual((found["fixture"]["kept"], found["checks"]), (False, []))
        self.assertIn("restore held or was refused", found["fixture"]["detail"])

    def test_the_lines_of_a_fixture_that_is_gone_are_dropped_before_a_new_one_is_made(self):
        gone = self.stale_record("000000000009")
        self.a_fixture_run(*self.SETUP_LINES)
        made_with: list[bool] = []
        restore = self.cli.on_call

        def on_call(argv):
            if argv[0] == "snapshot" and not made_with:
                made_with.append(gone.exists())             # the fixture run's first verb
            restore(argv)
        self.cli.on_call = on_call
        self.start()
        self.assertEqual(made_with, [False])

    def test_the_kept_lines_go_with_the_fixture_prune_removes(self):
        saves = self.user / "save games"
        for age, key in ((300, "000000000001"), (200, "000000000002")):
            path = saves / ("te_qa_fixture_%s.v3" % key)
            path.write_bytes(b"an older fixture")
            os.utime(path, (path.stat().st_atime - age, path.stat().st_mtime - age))
            kept = self.paths.backup_root / "fixtures" / key
            kept.mkdir(parents=True)
            (kept / "lines.log").write_text("x\n", encoding="utf-8")
            (kept / "record.json").write_text("{}\n", encoding="utf-8")
        self.a_fixture_run(*self.SETUP_LINES)
        reply = self.start()
        self.assertEqual(reply["fixtures_pruned"], ["te_qa_fixture_000000000001.v3"])
        self.assertEqual(sorted(p.name for p in (self.paths.backup_root / "fixtures").iterdir()),
                         sorted(["000000000002", self.key]))
        self.assertEqual([(s["outcome"], s.get("keys")) for s in self.steps("fixture_lines")],
                         [("kept", None), ("dropped", ["000000000001"])])

    def test_a_start_on_a_fixture_already_there_keeps_its_lines(self):
        kept = self.paths.backup_root / "fixtures" / self.key
        kept.mkdir(parents=True)
        (kept / "lines.log").write_text("".join(line + "\n" for line in self.logged(*self.SETUP_LINES)), "utf-8")
        (kept / "record.json").write_text(json.dumps({"key": self.key, "kept": True, "snapshot": FIXTURE_SNAP,
                                                      "lines": 3, "self_checks": 2, "at": "2026-11-10T14:56:00Z"}),
                                          "utf-8")
        self.started()
        self.assertEqual(self.steps("fixture_lines"), [])
        found = self.session.self_checks()
        self.assertEqual(found["broken"], ["unemployment_share_read"])
        self.assertEqual(found["fixture"]["snapshot"], FIXTURE_SNAP)

    def test_the_verb_pushes_the_games_log_out_before_it_reads(self):
        self.started()
        self.game_logs("common/scripted_effects/cultural_hegemony_effects.txt:162: TE_SELF_CHECK OK ch_board_rows "
                       "ranked=70 date=January 3, 1836",
                       "events/te_debug_demog_events.txt:1298: TE_SELF_CHECK BROKEN delayed_state_event (a state "
                       "event triggered with days = 7 never ran) date=January 17, 1836")
        self.assertNotIn("TE_SELF_CHECK", (self.user / "logs" / "debug.log").read_text("utf-8"))
        typed = len(self.typed())
        found = self.session.self_checks()
        self.assertEqual(self.typed()[typed:], ["event " + overlay.READ_EVENT])       # the flush: one empty read
        self.assertEqual((found["live"], found["flushed"], found["run"]), (True, True, SNAP))
        self.assertNotIn("not_flushed", found)
        self.assertEqual(found["broken"], ["delayed_state_event"])
        self.assertEqual([(c["name"], c["verdict"], c["source"]) for c in found["checks"]],
                         [("delayed_state_event", "BROKEN", "session"), ("ch_board_rows", "OK", "session")])
        self.assertEqual(found["checks"][0]["line"],
                         "events/te_debug_demog_events.txt:1298: TE_SELF_CHECK BROKEN delayed_state_event (a state "
                         "event triggered with days = 7 never ran) date=January 17, 1836")
        self.assertEqual(found["session"]["file"], str(self.paths.run_root / SNAP / "debug.log"))
        self.assertIn("TE_SELF_CHECK OK ch_board_rows", self.run_log())
        (step,) = self.steps("selfchecks")
        self.assertEqual((step["outcome"], step["flushed"], step["broken"]), ("ok", True, ["delayed_state_event"]))
        self.assertFalse(self.game.adapter.stopped)             # the read's stop was released

    def test_when_the_flush_fails_beside_a_live_game_what_is_written_is_still_read(self):
        self.started()
        self.game_wrote("common/a.txt:1: TE_SELF_CHECK OK written_already")
        self.game.stops = False                 # the read event runs, but nothing stops at the breakpoint
        with mock.patch.object(session, "STOP_WAIT_S", 0.05):    # the debugger client's own clock: real seconds
            found = self.session.self_checks()
        self.assertEqual((found["live"], found["flushed"]), (True, False))
        self.assertEqual(found["not_flushed"]["refused"], "no_stop")
        self.assertNotIn("log_not_read", found)
        self.assertEqual([c["name"] for c in found["checks"]], ["written_already"])

    def another_game_starts(self) -> None:
        """The owner starts a game of their own: the launch moves the run's log on, and its lines go to a new
        `debug.log` (as a rename; a game that appended instead is `FoundLogTest`'s)."""
        log = self.user / "logs" / "debug.log"
        os.replace(log, log.with_name("debug.1.log"))
        log.write_text("".join(line + "\n" for line in self.logged(
            "common/a.txt:9: TE_SELF_CHECK OK from_the_owners_own_game")), encoding="utf-8")

    def test_the_verb_never_reads_logs_once_the_game_has_ended_by_itself(self):
        # Blocking 1 of #1650's review: the game crashed or was closed, and a game started before the verb
        self.started()
        self.game_logs("common/a.txt:1: TE_SELF_CHECK OK the_runs_own")
        self.session.read([])                   # a verb while the game lived: its copy is the run's
        self.game_wrote("common/a.txt:2: TE_SELF_CHECK OK logged_after_the_last_verb")
        self.game.exited = True
        self.another_game_starts()
        typed = len(self.typed())
        found = self.session.self_checks()
        self.assertEqual(self.typed()[typed:], [])
        self.assertEqual((found["live"], found["flushed"]), (True, False))
        self.assertEqual(found["not_flushed"]["refused"], "watch_ended")
        self.assertIn("another game may have written", found["log_not_read"])
        self.assertEqual([(c["name"], c["source"]) for c in found["checks"]], [("the_runs_own", "session")])
        self.assertNotIn("from_the_owners_own_game", self.run_log())
        self.assertTrue(self.steps("selfchecks")[-1]["log_not_read"])

    def test_an_ordinary_verb_never_copies_lines_polled_after_the_game_died(self):
        # #1650's second review (V6): every verb polls the logs before its first proved key. The game is dead,
        # `watch` has not looked yet, and another launch has moved the log on: the poll reads that game's
        # lines, and the proof that follows the poll drops them.
        self.started()
        self.game_logs("common/a.txt:1: TE_SELF_CHECK OK the_runs_own")
        self.session.read([])
        self.game_wrote("common/a.txt:2: TE_SELF_CHECK OK logged_after_the_last_verb")
        self.game.process_gone = True
        self.another_game_starts()
        typed = len(self.typed())
        self.assertEqual(self.session_error(self.session.read, []).code, "watch_ended")
        self.assertEqual(self.typed()[typed:], [])
        for foreign in ("from_the_owners_own_game", "logged_after_the_last_verb"):   # read in the same poll: dropped
            self.assertNotIn(foreign, self.run_log())
        (step,) = self.steps("log_lines")
        self.assertEqual(step["outcome"], "dropped")
        found = self.session.self_checks()
        self.assertIn("log_not_read", found)
        self.assertEqual([(c["name"], c["source"]) for c in found["checks"]], [("the_runs_own", "session")])
        reply = self.session.stop()
        text = Path(reply["report"]).read_text("utf-8")
        self.assertNotIn("from_the_owners_own_game", text)
        self.assertNotIn("from_the_owners_own_game", self.run_log())
        self.assertTrue(any("read and dropped" in note for note in reply["notes"]))
        self.assertIn("read and dropped", text)

    def test_run_setup_has_the_same_guard(self):
        reply = self.started(setups={"border": "set_variable = te_x"})
        self.game.setups = {reply["overlay"]["setup_events"]["border"]: ("border", ["a line"])}
        self.game.process_gone = True
        self.another_game_starts()
        typed = len(self.typed())
        self.assertEqual(self.session_error(self.session.run_setup, "border").code, "watch_ended")
        self.assertEqual(self.typed()[typed:], [])
        self.assertNotIn("from_the_owners_own_game", self.run_log())

    def test_a_death_between_the_flushs_first_key_and_its_date_line_drops_what_was_read(self):
        # V1: proved alive, then dead, then another game's log, all inside one `selfchecks`
        self.started()
        self.game_logs("common/a.txt:1: TE_SELF_CHECK OK the_runs_own")
        self.session.read([])

        def dies(text):                         # as the game takes the read event's command
            if text == "event " + overlay.READ_EVENT and not self.game.process_gone:
                self.game.process_gone = True
                self.another_game_starts()      # the fake goes on writing the date line, into that game's log
        self.game.on_command = dies
        found = self.session.self_checks()
        self.assertEqual((found["flushed"], found["not_flushed"]["refused"]), (False, "watch_ended"))
        self.assertIn("log_not_read", found)
        self.assertEqual([c["name"] for c in found["checks"]], ["the_runs_own"])
        self.assertNotIn("from_the_owners_own_game", self.run_log())

    def test_a_live_games_lines_are_written_after_one_proof_and_an_empty_poll_asks_nothing(self):
        self.started()
        self.session.read([])
        adopts = self.order.count("adopt")
        self.assertEqual(self.session._new_lines(), [])                 # nothing new: no helper call
        self.assertEqual(self.order.count("adopt"), adopts)
        self.game_wrote("common/a.txt:1: TE_SELF_CHECK OK written_by_the_live_game")
        (line,) = self.session._new_lines()
        self.assertIn("written_by_the_live_game", line)
        self.assertEqual(self.order.count("adopt"), adopts + 1)         # one proof for a poll that read lines
        self.assertIn("written_by_the_live_game", self.run_log())
        self.game.error("an error the game logged")                     # error.log alone counts as lines read
        self.assertEqual(self.session._new_lines(), [])
        self.assertEqual(self.order.count("adopt"), adopts + 2)
        self.assertEqual(self.steps("log_lines"), [])

    def test_another_game_seen_beside_the_runs_marks_the_sessions_rows(self):
        # no proof of the run's own game rules out a second one writing the same logs: `watch` journals it
        self.started()
        self.game_logs("common/a.txt:1: TE_SELF_CHECK OK the_runs_own")
        journal = self.paths.backup_root / "snapshots" / SNAP / "journal.jsonl"
        journal.parent.mkdir(parents=True)
        journal.write_text(json.dumps({"event": "other_game", "at": "2026-11-10T15:02:00Z", "pid": 4242,
                                       "created": "2026-11-10T15:01:55.0000000Z"}) + "\n", encoding="utf-8")
        found = self.session.self_checks()
        self.assertIn("pid 4242", found["session"]["unvouched"])
        self.assertEqual([(c["name"], c["unvouched"]) for c in found["checks"]], [("the_runs_own", True)])
        text = Path(self.session.stop()["report"]).read_text("utf-8")
        self.assertIn("The session's rows cannot be vouched for", text)
        self.assertIn("| the_runs_own | OK | session (not vouched for) |", text)

    def test_the_verb_does_not_read_logs_of_a_game_it_cannot_prove_alive(self):
        self.started()
        self.game.process_gone = True           # the game died; its watch has not returned yet
        self.another_game_starts()
        found = self.session.self_checks()
        self.assertEqual((found["flushed"], found["not_flushed"]["refused"]), (False, "watch_ended"))
        self.assertIn("log_not_read", found)
        self.assertEqual(found["checks"], [])
        self.assertNotIn("from_the_owners_own_game", self.run_log())

    def test_stop_never_reads_logs_once_the_game_had_ended_by_itself(self):
        # Blocking 1, the other way in: `kill` finds the game gone already, at a time nobody knows
        self.started()
        self.game_logs("common/a.txt:1: TE_SELF_CHECK OK the_runs_own")
        self.session.read([])
        self.game_wrote("common/a.txt:2: TE_SELF_CHECK OK logged_after_the_last_verb")
        self.game.exited = True
        self.another_game_starts()
        reply = self.session.stop()
        self.assertEqual(reply["outcome"], "restored")
        text = Path(reply["report"]).read_text("utf-8")
        self.assertIn("the_runs_own", text)
        for missing in ("from_the_owners_own_game", "logged_after_the_last_verb"):
            self.assertNotIn(missing, text)
            self.assertNotIn(missing, self.run_log())
        note = [n for n in reply["notes"] if "log was not read" in n]
        self.assertEqual(len(note), 1)
        self.assertIn("had ended before the stop", note[0])
        self.assertIn("- Note: " + note[0], text)                # the summary says what it lacks
        found = self.session.self_checks()      # and the verb, after the stop, reads nothing either
        self.assertEqual([c["name"] for c in found["checks"]], ["the_runs_own"])

    def test_a_game_that_appended_to_the_log_it_found_does_not_lend_the_run_the_owners_lines(self):
        # Not seen live (2026-11-11's logs began with their own run), but a patch could bring it: the snapshot
        # knows the bytes of the log the game found, and the session's copy never takes them for the run's.
        log = self.user / "logs" / "debug.log"
        log.write_text("".join(line + "\n" for line in self.logged(
            "common/a.txt:9: TE_SELF_CHECK BROKEN from_the_owners_own_game")), encoding="utf-8")
        owners = log.stat().st_size
        snap = snapshot.take(self.user, self.paths.backup_root,
                             now=dt.datetime(2026, 11, 10, 15, 0, tzinfo=dt.timezone.utc))
        self.assertEqual(snap.id, SNAP)         # the session's own snapshot, as `snapshot` answers it here
        self.started()                          # the fake game appends to the log it finds
        self.game_logs("common/a.txt:1: TE_SELF_CHECK OK the_runs_own")
        found = self.session.self_checks()
        self.assertEqual([(c["name"], c["verdict"]) for c in found["checks"]], [("the_runs_own", "OK")])
        self.assertNotIn("from_the_owners_own_game", self.run_log())
        (step,) = self.steps("found_log")
        self.assertEqual((step["outcome"], step["bytes"]), ("prefix_skipped", owners))
        reply = self.session.stop()
        self.assertTrue(any("appended to the debug.log it found" in note for note in reply["notes"]))
        self.assertNotIn("from_the_owners_own_game", Path(reply["report"]).read_text("utf-8"))

    def test_before_a_run_folder_exists_the_verb_is_refused(self):
        self.assertEqual(self.session_error(self.session.self_checks).code, "not_started")

    def test_stop_lists_the_verdicts_in_the_summary_with_every_broken_first(self):
        self.started()
        self.session.read([])                   # a verb's flush brings the first two
        self.game_wrote("common/a.txt:1: TE_SELF_CHECK OK first_ok n=1",
                        "common/a.txt:2: TE_SELF_CHECK START waiting (the verdict follows in a week)",
                        "common/a.txt:3: TE_SELF_CHECK BROKEN the_broken_one | read=0.000")
        reply = self.session.stop()             # no verb since: the stop takes the log's last lines itself
        self.assertEqual(reply["outcome"], "restored")
        text = Path(reply["report"]).read_text("utf-8")
        self.assertTrue(text.startswith("Restore: restored"), text[:80])       # the owner's files still come first
        section = text.split("## Self-checks")[1].split("| # | Verb | Outcome |")[0]
        self.assertIn("1 BROKEN, 1 START (no verdict was logged after it), 1 OK.", section)
        rows = [line for line in section.splitlines() if line.startswith("| ") and "Check" not in line]
        self.assertEqual([row.split(" | ")[0:3] for row in rows], [
            ["| the_broken_one", "BROKEN", "session"], ["| waiting", "START", "session"],
            ["| first_ok", "OK", "session"]])
        self.assertIn("TE_SELF_CHECK BROKEN the_broken_one \\| read=0.000 |", rows[0])     # a pipe cannot end the cell
        self.assertIn("- Session: 3 TE_SELF_CHECK lines in %s." % (self.paths.run_root / SNAP / "debug.log"), section)
        self.assertIn("- The run that made the fixture: no lines (te_qa_fixture_%s: it was made before the lines "
                      "of a fixture's run were kept" % self.key, section)
        self.assertNotIn("log was not read", text)              # the usual stop ends a live game and reads at once
        self.assertNotIn("self-check lines could not be read", text)

    def test_the_owners_logs_are_never_read_as_the_runs_once_a_restore_was_tried(self):
        self.started()
        self.game_wrote("common/a.txt:1: TE_SELF_CHECK OK the_runs_own")
        log = self.user / "logs" / "debug.log"

        def restore(argv):                      # part 1's restore renames the owner's log back over the run's
            if argv[0] == "restore":
                temp = log.with_name("debug.log.te_qa_restore.tmp")
                temp.write_text("".join(line + "\n" for line in self.logged(
                    "common/a.txt:9: TE_SELF_CHECK BROKEN from_the_owners_own_game")), encoding="utf-8")
                os.replace(temp, log)
        self.cli.on_call = restore
        self.cli.queue("restore", {"held": False, "refused": "error", "detail": "a stored copy is damaged"}, 2)
        first = self.session.stop()
        self.assertEqual(first["outcome"], "refused")
        second = self.session.stop()            # run again: it must not take the logs a second time
        for text in (self.run_log(), Path(second["report"]).read_text("utf-8")):
            self.assertIn("the_runs_own", text)
            self.assertNotIn("from_the_owners_own_game", text)
        found = self.session.self_checks()      # nor does the verb, after the stop
        self.assertEqual((found["flushed"], found["not_flushed"]["refused"]), (False, "stopped"))
        self.assertEqual([c["name"] for c in found["checks"]], ["the_runs_own"])
        self.assertNotIn("from_the_owners_own_game", self.run_log())

    def test_a_game_left_up_keeps_its_log_open_for_the_stop_that_ends_it(self):
        self.started()
        self.game.kill = mock.Mock(side_effect=HelperError("kill_failed", "access denied"))
        self.game_wrote("common/a.txt:1: TE_SELF_CHECK OK before_the_first_stop")
        first = self.session.stop()
        self.assertEqual(first["outcome"], "game_left_up")
        self.assertEqual(self.cli.verbs, [])                    # nothing was restored beside the game
        self.assertNotIn("before_the_first_stop", self.run_log())       # nor read: it was not ended by this stop
        self.assertTrue(any("log was not read" in n and "left up" in n for n in first["notes"]))
        self.game_wrote("common/a.txt:2: TE_SELF_CHECK OK logged_while_left_up")
        del self.game.kill
        second = self.session.stop()
        self.assertEqual(second["outcome"], "restored")
        text = Path(second["report"]).read_text("utf-8")
        self.assertIn("before_the_first_stop", text)
        self.assertIn("logged_while_left_up", text)

    def test_summary_lines_that_cannot_be_read_are_a_note_not_a_lost_summary(self):
        self.started()
        with mock.patch.object(session.selfchecks, "of_run", side_effect=OSError("the drive went away")):
            reply = self.session.stop()
        self.assertEqual(reply["outcome"], "restored")
        self.assertTrue(any("self-check lines could not be read" in note for note in reply["notes"]))
        text = Path(reply["report"]).read_text("utf-8")
        self.assertTrue(text.startswith("Restore: restored"))
        self.assertNotIn("## Self-checks", text)


DATED_SAVE_NAME = "TEST_FAIL_te_qa_fixture_1 January, 1900.v3"
GRANT_WORDS = "the owner, 21:40: run it to 1900 overnight, up to 8 hours"


def dated_save(settings, date="1900.1.1") -> bytes:
    """A dated fixture's save: the shape `text_save` gives, with its date in meta_data as the engine writes it."""
    listed = (' "" ' + " ".join(settings) + " ").encode()
    meta = (b"meta_data={\n\tgame_date=" + date.encode() + b"\n\tgame_rules={\n\t\tsettings={" + listed
            + b"}\n\t}\n}\n")
    state = b"game_rules={\n\tsetting={" + listed + b"}\n}\ncountry_manager={\n}\n"
    return b"SAV010000000000%08x" % len(meta) + b"\n" + meta + state


class DatedFixtureTest(SessionTestCase):
    """#1602: a fixture made by an unattended run to a later date (`make_fixture`), and a session started on it
    (`start(fixture_date=...)`), which never makes one."""

    def setUp(self):
        super().setUp()
        base = self.user.parent
        for rel, text in RULE_FILES.items():
            path = base / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        defines = self.paths.deploy_dir / "common" / "defines" / "extra_defines.txt"
        defines.parent.mkdir(parents=True, exist_ok=True)
        defines.write_text('NGame = {\n\tEND_DATE = "2136.1.1"\n}\n', encoding="utf-8")
        self.fixture_save.unlink()
        self.key = fixture.key(self.paths.game_version, [DEPLOYED_WIN, OVERLAY_WIN], self.paths.deploy_dir,
                               playset="mod_only")
        self.fixture_save = self.user / "save games" / ("te_qa_fixture_%s.v3" % self.key)
        self.fixture_save.write_bytes(text_save(["no_fantasy", "tax_light"]))
        self.dated_key = self.key + "_d19000101"
        self.dated_path = self.user / "save games" / ("te_qa_fixture_%s.v3" % self.dated_key)
        self.fixture_run_save = DATED_SAVE_NAME
        self.fixture_run_bytes = dated_save(["no_fantasy", "tax_light"])
        self.log = self.user / "logs" / "debug.log"
        self.log.parent.mkdir(exist_ok=True)
        self.log.write_text("[10:00:00][x.cpp:1]: the owner's last game\n", encoding="utf-8")
        self.fixture_snap = None

    def a_dated_run(self, years=6, restore_reply=None):
        """The run that makes the 1900 fixture: a real snapshot of the folder; while `watch` follows the game, it
        logs a setup line, then a year at a time, rotating `debug.log` past every generation, and its restore
        leaves only the last generations and its own `gametimer_*.tsv` in `run_logs/`."""
        snap = snapshot.take(self.user, self.paths.backup_root,
                             now=dt.datetime(2026, 11, 10, 14, 55, tzinfo=dt.timezone.utc))
        self.assertEqual(snap.id, FIXTURE_SNAP)
        self.fixture_snap = snap
        self.cli.queue("snapshot", {"id": snap.id}, 0)
        if restore_reply is not None:
            self.cli.queue("restore", *restore_reply)
        logs = self.user / "logs"

        def write(text, mode="a"):
            with open(self.log, mode, encoding="utf-8", newline="\n") as f:
                f.write(text)

        def rotate():
            for k in range(5, 0, -1):
                older = logs / ("debug.%d.log" % (k - 1)) if k > 1 else self.log
                if older.exists():
                    os.replace(older, logs / ("debug.%d.log" % k))

        def on_poll(n):
            # One poll is two seconds and RunLogs copies every ten, so the game writes a year each five polls.
            if n == 1:
                rotate()
                write("[10:00:01][x.cpp:46]: common/on_actions/x.txt:46: TE_SELF_CHECK OK decentralized_law_baseline"
                      "\n", "w")
            elif n % 5 == 0 and n // 5 <= years:
                rotate()
                write("[10:01:00][x.cpp:9]: common/x.txt:9: year %d\n" % (n // 5), "w")
            elif n // 5 > years:
                write("[10:02:00][x.cpp:3]: common/x.txt:3: TE_SELF_CHECK BROKEN a_late_one\n")
                return True
            return False
        self.on_fixture_poll = on_poll

        def restore(argv):
            if argv[:2] == ["restore", snap.id]:
                run_logs = snap.dir / "run_logs"
                run_logs.mkdir(exist_ok=True)
                for path in logs.glob("debug*.log"):
                    shutil.copy2(path, run_logs / path.name)
                (run_logs / "gametimer_20261112_214000.tsv").write_text(
                    "Game Date \tTime Unit \tSeconds\n1836_01_01\tDay\t0.5\n1899_12_31\tDay\t0.7\n", encoding="utf-8")
        self.cli.on_call = restore
        return snap.id

    def make(self, **kwargs):
        kwargs.setdefault("max_hours", 8)
        return self.session.make_fixture(PERMISSION, "1900.1.1", **kwargs)

    # ---- make_fixture

    def test_making_a_dated_fixture_runs_to_its_date_copies_its_log_and_stops(self):
        snap = self.a_dated_run()
        reply = self.make()
        self.assertTrue(reply["made"], reply)
        self.assertEqual(reply["save"], "te_qa_fixture_" + self.dated_key)
        self.assertEqual(self.dated_path.read_bytes(), self.fixture_run_bytes)
        launch = next(c for c in self.cli.calls if c[0] == "launch")
        self.assertEqual(launch[launch.index("--") + 1:], list(fixture.fixture_args((1900, 1, 1))))
        self.assertIn("granted at most 8 hours", launch[launch.index("--long-run") + 1])
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch", "restore"])     # the session launches nothing
        # the copy holds what rotated out of logs/ long before the end, and the owner's line is not in it
        copy = self.paths.run_root / snap / "fixture_debug.log"
        text = copy.read_text("utf-8")
        self.assertIn("decentralized_law_baseline", text)
        self.assertIn("a_late_one", text)
        self.assertNotIn("the owner's last game", text)
        self.assertFalse(any("decentralized" in p.read_text("utf-8")
                             for p in (self.paths.backup_root / "snapshots" / snap / "run_logs").glob("debug*.log")))
        lines = reply["lines"]
        self.assertEqual((lines["kept"], lines["source"], lines["self_checks"]), (True, "followed", 2))
        kept = (self.paths.backup_root / "fixtures" / self.dated_key / "lines.log").read_text("utf-8")
        self.assertIn("decentralized_law_baseline", kept)
        self.assertEqual(reply["logs"]["gaps"], 0)
        # the game's own timing, copied beside the run's log
        self.assertEqual((reply["timing"]["days"], reply["timing"]["years"]), (2, {"1836": 0.5, "1899": 0.7}))
        self.assertTrue((self.paths.run_root / snap / "gametimer_20261112_214000.tsv").is_file())
        self.assertEqual(reply["rules"], {"settings": ["no_fantasy", "tax_light"]})
        self.assertEqual((reply["save_facts"]["save_found"], reply["save_facts"]["game_date"],
                          reply["save_facts"]["date_matches"]), (DATED_SAVE_NAME, "1900.1.1", True))
        self.assertNotIn("build_changed", reply)
        # and the session stopped: the overlay is gone, nothing was restored twice
        self.assertFalse(self.paths.overlay_dir.exists())
        self.assertEqual(reply["stop"]["outcome"], None)
        on_disk = json.loads((self.paths.run_root / snap / "fixture.json").read_text("utf-8"))
        self.assertEqual((on_disk["save"], on_disk["stop"]), (reply["save"], reply["stop"]))

    def test_the_overlay_carries_the_dated_test_while_the_run_goes(self):
        self.a_dated_run()
        seen = []
        original = self.cli.on_call

        def look(argv):
            if argv[0] == "launch":
                seen.append((self.paths.overlay_dir / overlay.SCRIPTED_TEST_FILE).read_text("utf-8-sig"))
            original(argv)
        self.cli.on_call = look
        self.make()
        self.assertIn('fail = { game_date > "1899.12.31" }', seen[0])

    def test_a_fixture_already_there_is_reused_and_nothing_is_started(self):
        self.dated_path.write_bytes(self.fixture_run_bytes)
        reply = self.make()
        self.assertEqual((reply["made"], reply["found"], reply["save"]), (False, True, self.dated_path.stem))
        self.assertEqual(self.cli.calls, [])
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_a_long_run_needs_the_hours_granted_and_an_estimate_inside_them(self):
        for kwargs, code in (({"max_hours": None}, "no_max_hours"), ({"max_hours": 1}, "over_grant"),
                             ({"max_hours": 0}, "bad_argument"), ({"max_hours": "8"}, "bad_argument")):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.session_error(self.make, **kwargs).code, code)
        self.assertEqual(self.cli.calls, [])
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_a_date_no_run_can_end_on_is_refused_before_anything(self):
        for until in ("1836.1.1", "2135.12.31", "1900.2.29", "soon"):
            with self.subTest(until=until):
                error = self.session_error(self.session.make_fixture, PERMISSION, until, max_hours=8)
                self.assertEqual(error.code, "bad_date")
        self.assertEqual(self.cli.calls, [])

    def test_the_watch_limit_is_the_grant_when_the_grant_is_shorter(self):
        plan = self.session.fixture_plan((1900, 1, 1), max_hours=4)
        self.assertEqual(plan["limit_s"], 4 * 3600)
        self.assertGreater(self.session.fixture_plan((1900, 1, 1))["limit_s"], 4 * 3600)
        self.assertTrue(plan["long_run"])
        self.assertIn("quarterly autosaves", plan["autosaves"])
        self.assertEqual(plan["rules"], {"last_applied": []})

    def test_a_restore_that_holds_after_the_rename_says_the_fixture_is_there_and_keeps_no_lines(self):
        self.a_dated_run(restore_reply=({"held": True, "reason": "unwatched_stretch", "id": FIXTURE_SNAP,
                                         "restored": [], "removed": []}, 2))
        error = self.session_error(self.make)
        self.assertEqual((error.code, error.info["step"], error.info["saved"]),
                         ("fixture_failed", "restore", self.dated_path.stem))
        self.assertTrue(self.dated_path.is_file())
        self.assertFalse(error.info["logs"]["vouched"])
        self.assertEqual(error.info["stop"]["outcome"], "held")
        record = json.loads((self.paths.backup_root / "fixtures" / self.dated_key / "record.json").read_text("utf-8"))
        self.assertFalse(record["kept"])
        # the run's folder says so for whoever reads it after the client has gone
        on_disk = json.loads((self.paths.run_root / FIXTURE_SNAP / "fixture.json").read_text("utf-8"))
        self.assertEqual((on_disk["refused"], on_disk["saved"], on_disk["stop"]["outcome"]),
                         ("fixture_failed", self.dated_path.stem, "held"))

    def test_a_build_deployed_during_the_run_is_reported(self):
        self.a_dated_run()
        original = self.cli.on_call

        def deploy(argv):
            original(argv)
            if argv[0] == "restore":
                (self.paths.deploy_dir / "events" / "te_events.txt").write_text("namespace = te\n# changed\n")
        self.cli.on_call = deploy
        reply = self.make()
        self.assertTrue(reply["made"])
        self.assertIn("--save " + self.dated_path.stem, reply["build_changed"])

    # ---- start on a dated fixture

    def test_start_on_a_missing_dated_fixture_is_refused_with_nothing_done(self):
        other = self.user / "save games" / "te_qa_fixture_000000000000_d19000101.v3"
        other.write_bytes(self.fixture_run_bytes)
        error = self.session_error(self.start, fixture_date="1900")
        self.assertEqual(error.code, "no_fixture")
        self.assertEqual(error.info["stale"], [other.stem])
        self.assertIn("fixture --until 1900.1.1", error.info["next"])
        self.assertIn("--save " + other.stem, error.info["next"])
        self.assertEqual(self.cli.calls, [])
        self.assertFalse(self.paths.overlay_dir.exists())

    def test_start_on_a_dated_fixture_loads_it_and_never_makes_one(self):
        self.dated_path.write_bytes(self.fixture_run_bytes)
        reply = self.start(fixture_date="1900.1.1")
        self.assertEqual((reply["save"], reply["fixture_made"], reply["fixture_date"]),
                         (self.dated_path.stem, False, "1900.1.1"))
        launch = next(c for c in self.cli.calls if c[0] == "launch")
        self.assertEqual(launch[-1], "-loadsave=" + self.dated_path.stem)
        self.assertNotIn("--long-run", launch)
        self.assertEqual(reply["rules"], {"settings": ["no_fantasy", "tax_light"]})

    def kept_lines(self, key, *messages, source=None):
        """Lines kept with the fixture `key`, from the run of FIXTURE_SNAP, as `selfchecks.keep_fixture_lines`
        leaves them."""
        folder = self.paths.backup_root / "fixtures" / key
        folder.mkdir(parents=True)
        (folder / "lines.log").write_text("".join("[10:00:01][x.cpp:1]: %s\n" % m for m in messages), "utf-8")
        record = {"key": key, "kept": True, "snapshot": FIXTURE_SNAP, "lines": len(messages), "self_checks":
                  len(messages), "at": "2026-11-10T14:56:00Z"}
        if source:
            record.update(source=source, gaps=0)
        (folder / "record.json").write_text(json.dumps(record), "utf-8")

    def dated_session_lines(self, switch=None) -> dict:
        """`self_checks` of a session on the 1900 fixture (or a switched copy of it), with lines kept for both it
        and the 1836 fixture of the same build."""
        self.dated_path.write_bytes(self.fixture_run_bytes)
        self.kept_lines(self.key, "common/a.txt:1: TE_SELF_CHECK BROKEN the_1836_runs_check")
        self.kept_lines(self.dated_key, "common/b.txt:2: TE_SELF_CHECK OK the_1900_runs_check", source="followed")
        self.started(fixture_date="1900", switch_rules=switch)
        return self.session.self_checks()

    def test_a_session_on_a_dated_fixture_shows_the_lines_of_the_run_that_made_it(self):
        found = self.dated_session_lines()
        self.assertEqual([(c["name"], c["source"]) for c in found["checks"]], [("the_1900_runs_check", "fixture")])
        self.assertEqual((found["fixture"]["key"], found["fixture"]["kept"], found["fixture"]["source"]),
                         (self.dated_key, True, "followed"))
        self.assertEqual(found["broken"], [])

    def test_a_switched_copy_of_a_dated_fixture_shows_the_dated_runs_lines(self):
        found = self.dated_session_lines({"tax_rule": "tax_off"})
        self.assertEqual([(c["name"], c["source"]) for c in found["checks"]], [("the_1900_runs_check", "fixture")])
        self.assertEqual(found["fixture"]["key"], self.dated_key)

    def test_the_plain_fixtures_date_is_the_plain_fixture(self):
        reply = self.start(fixture_date="1836.1.2")
        self.assertEqual(reply["save"], self.fixture_save.stem)
        self.assertNotIn("fixture_date", reply)

    def test_a_dated_fixture_with_an_owners_save_is_refused(self):
        (self.user / "save games" / "mine.v3").write_bytes(b"the owner's")
        self.assertEqual(self.session_error(self.start, save="mine", fixture_date="1900").code, "bad_argument")
        self.assertEqual(self.cli.calls, [])

    def test_a_rule_switched_in_a_dated_fixture_is_switched_on_its_date(self):
        self.dated_path.write_bytes(self.fixture_run_bytes)
        reply = self.start(fixture_date="1900", switch_rules={"tax_rule": "tax_off"})
        stem = "te_qa_fixture_%s" % rules_key(self.dated_key, {"tax_rule": "tax_off"})
        self.assertEqual(reply["save"], stem)
        self.assertEqual(reply["rules"]["settings"], ["no_fantasy", "tax_off"])
        self.assertTrue(reply["rules"]["switched_at"].startswith("1 January 1900"))
        self.assertEqual(self.dated_path.read_bytes(), self.fixture_run_bytes)
        self.assertTrue(self.fixture_save.is_file())


if __name__ == "__main__":
    unittest.main()
