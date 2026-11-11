"""game_qa/session.py: one game's life, from start to restore.

No game and no Windows program is needed. `Game` is `fakes.FakeHelper` plus the parts of the game the session
drives: the read event stopping at the debugger's breakpoint and logging the date once resumed, `tag`, the
country-select screen and its two clicks, the pause key, and time passing while unpaused. `Adapter` is the
game's side of the debugger, reached through the helper's relay as in the real harness. `Cli` stands in for
`python3 -m game_qa` and `Watch` for the `watch` subprocess. Every wait runs on the fake's one clock, except
the debugger client's own, which the fakes answer at once.
"""
import datetime as dt
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game_qa import dap, fakes, fixture, logtail, overlay, session
from game_qa.console import ConsoleError
from game_qa.helper import HelperError

SNAP = "20261110T150000Z"
FIXTURE_SNAP = "20261110T145500Z"
PID, CREATED = 7, "2026-11-10T14:00:00.0000000Z"
OVERLAY_WIN = r"C:\Users\someone\Documents\Paradox Interactive\Victoria 3\mod\te_qa_overlay"
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
        self.selected = False                   # a country is selected on the country-select screen
        self.entered = False                    # Start was pressed: time can pass
        self.paused = True
        self.clicks_work = True
        self.days_per_second = 1.5
        self.elapsed = 0.0                      # game days since START_DATE
        self.stops = True                       # the read event stops at a breakpoint set on its line
        self.exited = False                     # the game ended by itself
        self.tcp_error: Exception | None = None
        self.closed = False
        self.setups: dict[str, tuple[str, list[str]]] = {}     # setup event -> (its name, the lines its body logs)
        self.on_command = None                  # called with each command the game runs, before it answers
        self.on_sleep = None                    # called with each sleep's seconds, before the time passes
        self.dropped_pauses = 0                 # this many pause keys (space, the game running) are lost
        self.logs_date = True                   # the read event logs its date line once resumed
        self.error_log = logs / "error.log"
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

    def keys(self, pid, steps):
        super().keys(pid, steps)
        for step in steps:
            if step.get("scan") == SPACE:
                self.order.append("space")
                if not self.console_open:
                    if not self.paused and self.dropped_pauses:
                        self.dropped_pauses -= 1
                        continue
                    self.paused = not self.paused

    def click(self, pid, x, y):
        super().click(pid, x, y)
        self.order.append("click")
        if not self.clicks_work:
            return
        _left, _top, width, height = self.client
        if abs(x - width * 0.492) < 2 and abs(y - height * 0.656) < 2 and self.played:
            self.selected = True
        elif abs(x - width * 0.9216) < 2 and abs(y - height * 0.975) < 2 and self.selected:
            self.entered = True

    def adopt(self, proc):
        super().adopt(proc)
        self.order.append("adopt")

    def kill(self, proc):
        self.order.append("kill")
        return super().kill(proc)

    def tcp_open(self, port):
        super().tcp_open(port)
        self.order.append("tcp_open %d" % port)

    def tcp_send(self, data):
        if self.tcp_error is not None:
            raise self.tcp_error
        self.adapter.send(data)

    def tcp_recv(self, timeout):
        if self.tcp_error is not None:
            raise self.tcp_error
        return self.adapter.recv(timeout)

    def tcp_close(self):
        super().tcp_close()
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

    `watch` (only the fixture's run calls it through here) writes the run's save; `restore` removes the saves a
    run made, as the real one does, and notes whether the overlay was still there."""

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
        if verb == "watch":
            (saves / "TEST_FAIL_te_qa_fixture_2 January, 1836.v3").write_bytes(b"a fresh game")
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
            "watch": ({"id": FIXTURE_SNAP, "exited": True}, 0),
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
            enabled_mods=[r"C:\Users\someone\mod\Vic3TimelineExtended", OVERLAY_WIN])
        self.key = fixture.key(self.paths.game_version, self.paths.enabled_mods, deploy)
        self.fixture_save = self.user / "save games" / ("te_qa_fixture_%s.v3" % self.key)
        self.fixture_save.write_bytes(b"a fresh game")
        self.order: list[str] = []
        self.game = Game(self.user, self.order)
        self.cli = Cli(self)
        self.watches: list[Watch] = []
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
        self.assertEqual(self.game.adopted, [self.game.proc])
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
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch", "watch", "restore", "snapshot", "launch"])
        self.assertEqual(self.cli.calls[2][-6:], ["--", *fixture.FIXTURE_ARGS])
        self.assertTrue(reply["fixture_made"])
        self.assertTrue(self.fixture_save.is_file())
        self.assertEqual(self.cli.calls[6][-1], "-loadsave=te_qa_fixture_" + self.key)

    def test_start_with_a_named_save_loads_it_and_snapshots_it(self):
        (self.user / "save games" / "france_1850.v3").write_bytes(b"the owner's own save")
        reply = self.start(save="france_1850.v3")
        self.assertEqual(self.cli.calls[1], ["snapshot", "--save", "france_1850"])
        self.assertEqual(self.cli.calls[2][-1], "-loadsave=france_1850")
        self.assertEqual((reply["save"], reply["fixture_made"]), ("france_1850", False))

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
            "game": None, "watch_returned": False, "run_dir": None, "maybe_stopped": False, "left_running": False,
            "watch_respawns": 0})
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
                self.assertEqual(result["before"], (1836, 1, 11))
                self.assertEqual(result["after"], (1836, 1, 15))        # 3 s at 1.5 days a second
                self.assertTrue(self.game.paused)
                self.assertEqual(self.order.count("space"), 2)

    def test_enter_game_that_does_not_move_the_date_raises_with_a_screenshot(self):
        self.started()
        self.game.clicks_work = False
        error = self.session_error(self.session.enter_game)
        self.assertEqual(error.code, "not_entered")
        shot = Path(error.info["screenshot"])
        self.assertTrue(shot.is_file())
        self.assertEqual(shot.parent, self.paths.backup_root / "runs" / SNAP)
        self.assertEqual(len(self.game.clicks), 2)

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
    counts down for an event that fires only so often), and so does a setup event in `fired_by`.
    `select_event_option list` lists the pending ones; `select_event_option <i> <n>` picks one and runs
    `effects[i]`."""

    def __init__(self, game: Game, event: str = "x.1", options: int = 3):
        self.game, self.event, self.options = game, event, options
        self.pending: list[int] = []
        self.next_id = 10
        self.fires = True
        self.fires_left: int | None = None
        self.fired_by: set[str] = set()
        self.effects: dict = {}
        game.on_command = self.command

    def fire(self) -> None:
        if not self.fires or self.fires_left == 0:
            return
        if self.fires_left is not None:
            self.fires_left -= 1
        self.pending.append(self.next_id)
        self.next_id += 1

    def command(self, text: str) -> None:
        if text == "event " + self.event:
            self.game.on(text, success=['Executed "%s"' % self.event])
            self.fire()
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
            "picked": None, "new_errors": [], "did_not_fire": True}])
        self.assertEqual(self.commands(), ["select_event_option list", "event x.1", "select_event_option list"])
        # An event that fires once only: its first option is picked, and the second did not fire.
        self.events.fires, self.events.fires_left = True, 1
        reply = self.session.try_event("x.1", None, ["c:FRA.infamy"])
        self.assertEqual((reply["complete"], reply["option_count"]), (False, 3))
        self.assertEqual([(r["fired"], r["did_not_fire"], r["picked"] is not None) for r in reply["options"]],
                         [(True, False, True), (False, True, False)])
        self.assertEqual([s["complete"] for s in self.try_event_steps()], [False, False])

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
        self.assertEqual(self.cli.verbs, [])                   # beside a game that may be the run's: no restore
        self.assertIn("restore %s" % SNAP, reply["next"])
        self.assertTrue(reply["overlay_kept"])
        self.assertTrue(self.paths.overlay_dir.exists())
        self.assertEqual(self.order, ["kill", "tcp_close", "helper_close"])   # nothing of the session's own left
        first = Path(reply["report"]).read_text("utf-8").split("\n")[0]
        self.assertIn("NOT RUN", first)
        self.assertIn("restore %s" % SNAP, first)

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
        self.assertIn("restore %s" % SNAP, stop["next"])
        self.assertNotIn("stop` again", stop["next"])


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
        cases = ((("launch", {"refused": "gpu_busy", "id": FIXTURE_SNAP}, 2), True),
                 (("restore", {"held": True, "reason": "unwatched_stretch", "restored": [], "removed": []}, 2), False),
                 (("launch", {"refused": "not_recorded", "id": FIXTURE_SNAP, "pid": 9, "created": CREATED}, 2), False))
        for (verb, reply, code), removed in cases:
            with self.subTest(verb=verb, reply=reply):
                self.setUp()
                self.fixture_save.unlink()
                self.cli.queue("snapshot", {"id": FIXTURE_SNAP}, 0)
                self.cli.queue(verb, reply, code)
                self.assertEqual(self.session_error(self.start).code, "fixture_failed")
                self.assertEqual(self.paths.overlay_dir.exists(), not removed)


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

    def test_a_watch_that_ends_while_the_game_is_up_is_run_again(self):
        self.started()
        self.watches[0].dies = True
        self.game.adapter.values = {"c:FRA.gdp": "1"}
        self.session.read(["c:FRA.gdp"])
        self.assertEqual(len(self.watches), 2)
        self.assertEqual(self.session.status()["watch_respawns"], 1)
        reply = self.session.stop()
        self.assertTrue(any("run again" in note for note in reply["notes"]))
        self.assertIn("watch_respawned", Path(reply["report"]).read_text("utf-8"))

    def test_a_watch_that_returned_with_the_game_gone_ends_the_verbs(self):
        self.started()
        self.watches[0].dies = True
        self.game.exists = False
        self.assertEqual(self.session_error(self.session.read, ["c:FRA.gdp"]).code, "watch_ended")
        self.assertEqual(len(self.watches), 1)

    def test_with_an_owners_save_there_is_no_country_select_to_click(self):
        (self.user / "save games" / "france_1850.v3").write_bytes(b"the owner's own save")
        self.started(save="france_1850")
        self.game.entered = True                # the owner's save opens in play
        self.assertEqual(self.session_error(self.session.enter_game).code, "not_on_country_select")
        reached = self.session.advance(3)
        self.assertGreaterEqual(dt.date(*reached), START_DATE + dt.timedelta(days=3))
        self.assertEqual(self.game.clicks, [])


if __name__ == "__main__":
    unittest.main()
