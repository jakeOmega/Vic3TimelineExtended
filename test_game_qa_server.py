"""game_qa/server.py and game_qa/client.py: the session server and the command-line verbs that talk to it.

Each server here is a real `http.server` on an ephemeral 127.0.0.1 port. Most hold `FakeSession`, the public
face of a `Session` answering from what the test sets, and run in a thread of this process. A server that must
be killed or signalled runs in a child process (`CHILD`), over a double whose `start` runs the protective verbs
for real (`snapshot`, `launch`, in-process, with `gate` patched). Where those verbs must judge a real run, the
session is a real `Session` over `fakes.FakeHelper` with the same in-process `python3 -m game_qa`. No game, no
Windows program and no PowerShell is started; every path is a temp folder.
"""
import contextlib
import datetime as dt
import http.client
import io
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from game_qa import __main__ as cli
from game_qa import client, fakes, gate, overlay, server, session, snapshot
from game_qa.console import ConsoleError, Reply
from game_qa.dap import DebuggerError
from game_qa.helper import HelperError
from game_qa.logtail import Pending

REPO = Path(__file__).resolve().parent
SNAP = "20261110T150000Z"
PERMISSION = "the owner granted launches for this session"
OVERLAY_WIN = r"C:\Users\someone\Documents\Paradox Interactive\Victoria 3\mod\te_qa_overlay"
OWNER_MOD = r"C:\Users\someone\Documents\Paradox Interactive\Victoria 3\mod\Vic3TimelineExtended"
IDLE = [gate.GpuSample(14, 1607, 10240)] * 5
RESTORED = {"restored": ["content_load.json"], "removed": [], "held": False, "reason": "", "outcome": "restored",
            "snapshot": SNAP, "overlay_removed": True, "report": "/backups/runs/%s/summary.md" % SNAP}


class FakeSession:
    """`Session`'s public face. Each verb records its call, then raises what `raises` holds for it or answers.
    `advance` waits for `release` (set by default), so a test can hold the server inside a verb. `stop` is
    idempotent like the real one: `stops` counts the stops that did anything."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.raises: dict[str, BaseException] = {}
        self.stop_reply = dict(RESTORED)
        self.stops = 0
        self._stopped = None
        self.release = threading.Event()
        self.release.set()

    def _call(self, verb, *args):
        self.calls.append((verb, *args))
        if verb in self.raises:
            raise self.raises[verb]

    def start(self, permission, as_tag=None, setups=None, save=None, playset="mod_only", owner_confirmed_busy=False):
        self._call("start", permission, as_tag, setups, save, playset, owner_confirmed_busy)
        return {"snapshot": SNAP, "pid": 7, "country": as_tag, "run_dir": "/backups/runs/" + SNAP}

    def console(self, text):
        self._call("console", text)
        return Reply(text, True, ["done"])

    def run_setup(self, name):
        self._call("run_setup", name)
        return ["first line", "second line"]

    def events(self):
        self._call("events")
        return [Pending(10, "x.1", 2)]

    def pick(self, index, event=None):
        self._call("pick", index, event)
        return {"event": "x.1", "numeric_id": 10, "index": index, "options": 2, "ambiguous": False,
                "reply": ["Selected option %d of x.1" % index]}

    def read(self, exprs):
        self._call("read", list(exprs))
        return [session.Read(e, True, "1.5", 1.5) for e in exprs]

    def tag(self, tag):
        self._call("tag", tag)

    def enter_game(self):
        self._call("enter_game")
        return {"entered": True, "clicks": [[945, 708], [1769, 1053]], "before": (1836, 1, 11), "after": (1836, 1, 15)}

    def advance(self, days):
        self._call("advance", days)
        self.release.wait(10)
        return (1836, 2, 1)

    def shot(self):
        self._call("shot")
        return Path("/backups/runs/%s/shot_01.png" % SNAP)

    def try_event(self, event, setup, reads):
        self._call("try_event", event, setup, list(reads))
        return dict(self.try_event_reply, event=event, setup=setup)

    try_event_reply = {"shared_state": True, "option_count": 2, "complete": True, "options": []}

    def status(self):
        self._call("status")
        return {"started": True, "stopped": self._stopped is not None, "snapshot": SNAP}

    def stop(self):
        self._call("stop")
        if self._stopped is None:
            self.stops += 1
            self._stopped = dict(self.stop_reply)
        return self._stopped


class Retrying(FakeSession):
    """`Session.stop` as it is: a stop that ended refused or game_left_up runs again at the next call; each run
    answers the next of `replies`."""

    def __init__(self, replies):
        super().__init__()
        self.replies = list(replies)

    def stop(self):
        self._call("stop")
        if self._stopped is None or self._stopped.get("outcome") in ("refused", "game_left_up"):
            self.stops += 1
            self._stopped = dict(self.replies.pop(0))
        return self._stopped


LEFT_UP = {"outcome": "game_left_up", "snapshot": SNAP, "stop_again": True, "overlay_kept": True,
           "next": "`python3 -m game_qa stop` again tries again to end it"}
BUSY = {"held": False, "refused": "busy", "outcome": "refused", "snapshot": SNAP, "stop_again": True}


class Handle:
    """What `client.spawn_server` returns, for a server in a thread of this process: its pid is this process's."""

    def __init__(self, srv: server.SessionServer):
        self.pid = os.getpid()
        self.thread = threading.Thread(target=srv.serve, daemon=True)
        self.thread.start()

    def poll(self):
        return None if self.thread.is_alive() else 0

    def wait(self, timeout=None):
        self.thread.join(timeout)
        if self.thread.is_alive():
            raise subprocess.TimeoutExpired("session-serve", timeout)
        return 0

    def terminate(self):
        pass


class ThreadSpawner:
    """`client.spawn_server` replaced: a `SessionServer` over the session `make` builds, in a thread."""

    def __init__(self, make):
        self.make = make
        self.handles: list[Handle] = []
        self.logs: list[Path] = []

    def __call__(self, backup_root, log):
        self.logs.append(Path(log))
        handle = Handle(server.SessionServer(self.make(), backup_root, port=0))
        self.handles.append(handle)
        return handle


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def tree(folder: Path) -> list:
    return sorted((str(p.relative_to(folder)), p.stat().st_mtime_ns, p.read_bytes())
                  for p in folder.rglob("*") if p.is_file())


def in_process_cli(argv):
    """`python3 -m game_qa <argv>` in this process, as `run_cli` gives it: (the reply, the exit code)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(list(argv))
    return json.loads(out.getvalue()), code


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.backups = self.root / "backups"
        self.backups.mkdir()
        patch = mock.patch.dict(os.environ, {"VIC3_QA_BACKUPS": str(self.backups)})
        patch.start()
        self.addCleanup(patch.stop)
        self.threads: list[threading.Thread] = []
        self.addCleanup(self._end_servers)

    def _end_servers(self):
        if server.read_info(self.backups) is not None and client.server_state(server.read_info(self.backups)) == "live":
            client.call(self.backups, "stop", {}, timeout=10)
        for thread in self.threads:
            thread.join(10)
            self.assertFalse(thread.is_alive(), "a server thread was left running")

    @property
    def info_path(self) -> Path:
        return self.backups / server.SESSION_FILE

    def serve(self, fake: FakeSession | None = None) -> tuple[FakeSession, threading.Thread]:
        """A server over `fake` in a thread; returns once its session.json is there."""
        fake, thread, _srv = self.serve_with_server(fake)
        return fake, thread

    def serve_with_server(self, fake=None) -> tuple[FakeSession, threading.Thread, server.SessionServer]:
        fake = fake or FakeSession()
        srv = server.SessionServer(fake, self.backups, port=0)
        thread = threading.Thread(target=srv.serve, daemon=True)
        thread.start()
        self.threads.append(thread)
        self.wait_for(lambda: server.read_info(self.backups) is not None, "the server's session.json")
        return fake, thread, srv

    def wait_for(self, done, what: str, seconds: float = 10.0) -> None:
        deadline = time.monotonic() + seconds
        while not done():
            if time.monotonic() > deadline:
                self.fail("no %s within %g s" % (what, seconds))
            time.sleep(0.02)

    def run_cli(self, *argv):
        return in_process_cli(argv)

    def write_info(self, port: int, pid: int) -> dict:
        info = {"port": port, "pid": pid, "started": "2026-11-10T15:00:00Z", "token": "0" * 32}
        self.info_path.write_text(json.dumps(info), encoding="utf-8")
        return info


class VerbTest(ServerTestCase):
    def test_a_verb_round_trips_json(self):
        fake, _thread = self.serve()
        reply, code = self.run_cli("read", "c:FRA.gdp", "is_player = yes")
        self.assertEqual(code, 0)
        self.assertEqual(reply, {"reads": [{"expr": "c:FRA.gdp", "ok": True, "raw": "1.5", "value": 1.5},
                                           {"expr": "is_player = yes", "ok": True, "raw": "1.5", "value": 1.5}]})
        self.assertEqual(fake.calls[-1], ("read", ["c:FRA.gdp", "is_player = yes"]))
        self.assertEqual(self.run_cli("pick", "1", "x.1")[0]["index"], 1)
        self.assertEqual(fake.calls[-1], ("pick", 1, "x.1"))
        self.run_cli("pick", "0")
        self.assertEqual(fake.calls[-1], ("pick", 0, None))
        self.assertEqual(self.run_cli("console", "money 1000"),
                         ({"command": "money 1000", "ok": True, "lines": ["done"]}, 0))
        self.assertEqual(self.run_cli("events"), ({"pending": [{"numeric_id": 10, "event_id": "x.1", "options": 2}]}, 0))
        self.assertEqual(self.run_cli("run-setup", "border"), ({"name": "border", "lines": ["first line", "second line"]}, 0))
        self.assertEqual(self.run_cli("tag", "FRA"), ({"tag": "FRA"}, 0))
        self.assertEqual(self.run_cli("advance", "30"), ({"reached": [1836, 2, 1]}, 0))
        self.assertEqual(fake.calls[-1], ("advance", 30))
        self.assertEqual(self.run_cli("enter-game")[0]["after"], [1836, 1, 15])
        self.assertEqual(self.run_cli("shot"), ({"path": "/backups/runs/%s/shot_01.png" % SNAP}, 0))
        status, code = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertEqual(status["server"]["pid"], os.getpid())
        self.assertEqual(status["session"]["snapshot"], SNAP)
        self.assertEqual(fake.stops, 0)

    def test_the_server_listens_on_localhost_only_and_wants_its_token(self):
        fake, _thread, srv = self.serve_with_server()
        info = server.read_info(self.backups)
        self.assertEqual(set(info), {"port", "pid", "started", "token"})
        self.assertEqual((info["pid"], srv.address), (os.getpid(), ("127.0.0.1", info["port"])))
        reply, code = client._post(dict(info, token="f" * 32), "events", {}, timeout=5)
        self.assertEqual((reply["refused"], code), ("forbidden", 2))
        self.assertNotIn(("events",), fake.calls)

    def test_no_session_is_refused(self):
        for argv in (("events",), ("read", "c:FRA.gdp"), ("stop",), ("status",), ("try-event", "x.1", "--read", "a")):
            with self.subTest(argv=argv):
                reply, code = self.run_cli(*argv)
                self.assertEqual((reply["refused"], code), ("no_session", 2))
        self.write_info(free_port(), os.getpid())     # names a port nothing listens on
        reply, code = self.run_cli("events")
        self.assertEqual((reply["refused"], code), ("no_session", 2))
        self.assertIn("recover", reply["detail"])

    def test_an_error_inside_a_verb_is_a_refusal_not_a_crash(self):
        fake, thread = self.serve()
        fake.raises = {
            "read": session.SessionError("no_stop", "the game did not stop", arrived=True),
            "console": ConsoleError("no_ack", "it never arrived", entered=None),
            "shot": HelperError("not_foreground", "the game's window is not in front"),
            "enter_game": DebuggerError("recv failed"),
            "tag": ZeroDivisionError("division by zero"),
        }
        self.assertEqual(self.run_cli("read", "c:FRA.gdp"),
                         ({"refused": "no_stop", "detail": "the game did not stop", "arrived": True}, 2))
        self.assertEqual(self.run_cli("console", "money 1"),
                         ({"refused": "no_ack", "detail": "it never arrived", "entered": None}, 2))
        self.assertEqual(self.run_cli("shot"),
                         ({"refused": "helper: not_foreground", "detail": "the game's window is not in front"}, 2))
        self.assertEqual(self.run_cli("enter-game"), ({"refused": "debugger", "detail": "recv failed"}, 2))
        self.assertEqual(self.run_cli("tag", "FRA"),
                         ({"refused": "error", "detail": "ZeroDivisionError: division by zero"}, 2))
        self.assertEqual(self.run_cli("advance", "0")[1], 0)          # the session judges its arguments, not the server
        reply, code = client.call(self.backups, "no_such_verb", {})
        self.assertEqual((reply["refused"], code), ("unknown_verb", 2))
        reply, code = client.call(self.backups, "pick", {"event": "x.1"})
        self.assertEqual((reply["refused"], code), ("bad_argument", 2))
        # still serving, and nothing was stopped
        self.assertEqual(self.run_cli("events")[1], 0)
        self.assertTrue(thread.is_alive())
        self.assertEqual(fake.stops, 0)

    def test_try_event_exits_0_only_when_every_option_was_picked(self):
        fake, _thread = self.serve()
        reply, code = self.run_cli("try-event", "x.1", "--setup", "border", "--read", "c:FRA.infamy", "--read", "a = b")
        self.assertEqual((reply["complete"], code), (True, 0))
        self.assertEqual(fake.calls[-1], ("try_event", "x.1", "border", ["c:FRA.infamy", "a = b"]))
        fake.try_event_reply = dict(FakeSession.try_event_reply, complete=False,
                                    options=[{"index": 0, "fired": False, "did_not_fire": True}])
        reply, code = self.run_cli("try-event", "x.1", "--read", "c:FRA.infamy")
        self.assertEqual((reply["options"][0]["did_not_fire"], code), (True, 2))
        self.assertEqual(fake.calls[-1], ("try_event", "x.1", None, ["c:FRA.infamy"]))

    def test_a_verb_that_outlasts_its_timeout_is_no_answer_and_ends_nothing(self):
        fake, thread = self.serve()
        fake.release.clear()
        reply, code = client.call(self.backups, "advance", {"days": 5}, timeout=0.3)
        self.assertEqual((reply["refused"], code), ("no_answer", 2))
        fake.release.set()
        self.wait_for(lambda: client.call(self.backups, "status", {}, timeout=2)[1] == 0, "an answer to status")
        self.assertTrue(thread.is_alive())
        self.assertEqual(fake.stops, 0)


class ExpiryTest(ServerTestCase):
    """R1: every request carries its client's expiry; the server never begins one whose time is up."""

    def test_a_request_whose_client_gave_up_never_runs(self):
        fake, _thread = self.serve()
        fake.release.clear()
        busy = threading.Thread(target=client.call, args=(self.backups, "advance", {"days": 5}, 10))
        busy.start()
        self.wait_for(lambda: ("advance", 5) in fake.calls, "the advance under way")
        reply, code = client.call(self.backups, "console", {"text": "money 1000"}, timeout=0.3)
        self.assertEqual((reply["refused"], code), ("no_answer", 2))
        self.assertIn("will not run later", reply["detail"])
        self.assertNotIn("Nothing was ended", reply["detail"])
        fake.release.set()
        busy.join(10)
        self.wait_for(lambda: client.call(self.backups, "status", {}, timeout=2)[1] == 0, "an answer to status")
        self.assertNotIn(("console", "money 1000"), fake.calls)

    def test_a_stop_whose_client_gave_up_never_runs(self):
        fake, thread = self.serve()
        fake.release.clear()
        busy = threading.Thread(target=client.call, args=(self.backups, "advance", {"days": 5}, 10))
        busy.start()
        self.wait_for(lambda: ("advance", 5) in fake.calls, "the advance under way")
        self.assertEqual(client.call(self.backups, "stop", {}, timeout=0.3)[0]["refused"], "no_answer")
        fake.release.set()
        busy.join(10)
        self.wait_for(lambda: client.call(self.backups, "status", {}, timeout=2)[1] == 0, "an answer to status")
        self.assertEqual(fake.stops, 0)
        self.assertTrue(thread.is_alive())

    def test_a_request_without_an_expiry_is_refused_unrun(self):
        fake, _thread = self.serve()
        info = server.read_info(self.backups)
        for headers in ({}, {server.EXPIRES_HEADER: "soon"}):
            with self.subTest(headers=headers):
                conn = http.client.HTTPConnection(server.HOST, info["port"], timeout=5)
                conn.request("POST", "/events", body=b"{}", headers={server.TOKEN_HEADER: info["token"], **headers})
                response = conn.getresponse()
                answer = json.loads(response.read())
                conn.close()
                self.assertEqual((response.status, answer["reply"]["refused"]), (400, "bad_request"))
        self.assertNotIn(("events",), fake.calls)

    def test_expiry_is_judged_by_the_servers_clock(self):
        fake = FakeSession()
        srv = server.SessionServer(fake, self.backups, port=0, now=lambda: server.machine_clock() + 3600)
        thread = threading.Thread(target=srv.serve, daemon=True)
        thread.start()
        self.threads.append(thread)
        self.wait_for(lambda: server.read_info(self.backups) is not None, "the server's session.json")
        reply, code = client._post(server.read_info(self.backups), "events", {}, timeout=5)
        self.assertEqual((reply["refused"], code), ("expired", 2))
        self.assertNotIn(("events",), fake.calls)
        srv._now = server.machine_clock
        self.assertEqual(client.call(self.backups, "stop", {}, timeout=5)[1], 0)


class HardeningTest(ServerTestCase):
    def test_session_json_stays_readable_by_its_owner_only(self):
        self.serve()
        self.assertEqual(self.info_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(client.call(self.backups, "start", {"permission": PERMISSION})[1], 0)
        self.assertEqual(server.read_info(self.backups)["snapshot"], SNAP)          # rewritten with the snapshot
        self.assertEqual(self.info_path.stat().st_mode & 0o777, 0o600)

    def test_a_token_of_any_text_is_refused_not_a_crash(self):
        fake, thread = self.serve()
        info = server.read_info(self.backups)
        for token in ("é" * 32, "", info["token"][:-1]):
            with self.subTest(token=token):
                reply, code = client._post(dict(info, token=token), "events", {}, timeout=5)
                self.assertEqual((reply["refused"], code), ("forbidden", 2))
        self.assertNotIn(("events",), fake.calls)
        self.assertTrue(thread.is_alive())

    def test_a_connection_that_sends_nothing_does_not_stall_stop(self):
        self.assertIsNotNone(server._Handler.timeout)              # the real server's, not only this test's
        self.assertLess(server._Handler.timeout, client.STATUS_TIMEOUT_S / 1.5)   # status answers past one
        with mock.patch.object(server._Handler, "timeout", 0.5):
            fake, thread = self.serve()
            silent = socket.create_connection(("127.0.0.1", server.read_info(self.backups)["port"]))
            self.addCleanup(silent.close)
            time.sleep(0.1)
            self.assertEqual(client.call(self.backups, "stop", {}, timeout=5), (RESTORED, 0))
            thread.join(10)
        self.assertEqual(fake.stops, 1)


class CleanStopTest(unittest.TestCase):
    def test_a_clean_stop_leaves_nothing_of_the_run(self):
        self.assertTrue(server.clean_stop(RESTORED))
        self.assertTrue(server.clean_stop({"outcome": None, "snapshot": None, "overlay_removed": True}))
        for reply in (dict(RESTORED, overlay_kept=True, overlay_kept_because="removing it failed"),
                      {"outcome": None, "snapshot": None, "snapshot_unknown": True, "overlay_removed": True},
                      {"outcome": "game_left_up", "snapshot": SNAP}, dict(RESTORED, held=True, outcome="held"),
                      {"outcome": "refused", "refused": "busy"}):
            with self.subTest(reply=reply):
                self.assertFalse(server.clean_stop(reply))


class StopTest(ServerTestCase):
    def test_stop_answers_then_the_server_exits_and_removes_its_file(self):
        fake, thread = self.serve()
        port = server.read_info(self.backups)["port"]
        reply, code = self.run_cli("stop")
        self.assertEqual((reply, code), (RESTORED, 0))
        thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertFalse(self.info_path.exists())
        with self.assertRaises(ConnectionRefusedError):
            socket.create_connection(("127.0.0.1", port), timeout=2).close()
        self.assertEqual(fake.stops, 1)
        self.assertEqual(self.run_cli("status")[0]["refused"], "no_session")

    def test_a_final_stop_that_held_or_failed_exits_2_and_ends_the_server(self):
        for stop_reply in ({"restored": [], "removed": [], "held": True, "reason": "other_game_ran", "outcome": "held"},
                           {"snapshot": SNAP, "outcome": "error", "notes": ["stop failed: OSError()"]},
                           dict(LEFT_UP, stop_again=False, next="once no Victoria 3 process runs: `recover`")):
            with self.subTest(outcome=stop_reply["outcome"]):
                fake = FakeSession()
                fake.stop_reply = stop_reply
                _fake, thread = self.serve(fake)
                self.assertEqual(self.run_cli("stop"), (stop_reply, 2))
                thread.join(10)
                self.assertFalse(thread.is_alive())
                self.assertFalse(self.info_path.exists())

    def test_a_stop_that_can_be_retried_keeps_the_server_and_stop_again_runs_it_again(self):
        # R7, B3: `next` says "`stop` again", so the server must still be there to run it.
        fake = Retrying([LEFT_UP, BUSY, RESTORED])
        _fake, thread = self.serve(fake)
        self.assertEqual(self.run_cli("stop"), (LEFT_UP, 2))
        self.assertTrue(thread.is_alive())
        self.assertEqual(self.run_cli("status")[1], 0)
        self.assertEqual(self.run_cli("stop"), (BUSY, 2))
        self.assertTrue(thread.is_alive())
        self.assertEqual(self.run_cli("stop"), (RESTORED, 0))
        thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertFalse(self.info_path.exists())
        self.assertEqual(fake.stops, 3)

    def test_a_signal_with_a_stop_still_retryable_leaves_word_of_what_works(self):
        fake = Retrying([LEFT_UP, LEFT_UP])
        log = io.StringIO()
        srv = server.SessionServer(fake, self.backups, port=0, log=log)
        thread = threading.Thread(target=srv.serve, daemon=True)
        thread.start()
        self.threads.append(thread)
        self.wait_for(lambda: server.read_info(self.backups) is not None, "the server's session.json")
        self.assertEqual(self.run_cli("stop"), (LEFT_UP, 2))
        srv._signalled = signal.SIGTERM
        client.call(self.backups, "status", {}, timeout=5)
        thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(fake.stops, 2)
        self.assertIn("left unfinished", log.getvalue())
        self.assertIn("`python3 -m game_qa recover`", log.getvalue())

    def test_a_signal_after_a_stop_that_can_be_retried_runs_the_stop_once_more(self):
        fake = Retrying([LEFT_UP, RESTORED])
        _fake, thread, srv = self.serve_with_server(fake)
        self.assertEqual(self.run_cli("stop"), (LEFT_UP, 2))
        srv._signalled = signal.SIGTERM         # as if noted during a verb: the loop ends at its next turn
        client.call(self.backups, "status", {}, timeout=5)      # wakes the loop, if it is waiting for a request
        thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(fake.stops, 2)

    def test_a_server_never_removes_a_file_it_did_not_write(self):
        _fake, thread = self.serve()
        own = server.read_info(self.backups)
        theirs = dict(own, pid=1, token="e" * 32)
        self.info_path.write_text(json.dumps(theirs), encoding="utf-8")     # as if another server had written it
        self.assertEqual(client._post(own, "stop", {}, timeout=10)[1], 0)
        thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(server.read_info(self.backups), theirs)
        self.info_path.unlink()


class StartTest(ServerTestCase):
    def setUp(self):
        super().setUp()
        self.setup_file = self.root / "border.txt"
        self.setup_file.write_text("\ufeffset_variable = te_x\n", encoding="utf-8")

    def test_start_spawns_the_server_then_posts_start(self):
        fake = FakeSession()
        spawn = ThreadSpawner(lambda: fake)
        with mock.patch.object(client, "spawn_server", spawn):
            reply, code = self.run_cli("start", "--permission", PERMISSION, "--as", "FRA",
                                       "--setup", "border=%s" % self.setup_file, "--playset", "current",
                                       "--owner-confirmed-busy")
        self.assertEqual(code, 0, reply)
        self.assertEqual(fake.calls[0], ("start", PERMISSION, "FRA", {"border": "set_variable = te_x\n"}, None,
                                         "current", True))
        self.assertEqual(reply["snapshot"], SNAP)
        self.assertEqual(reply["server"]["pid"], os.getpid())
        self.assertEqual(Path(reply["server"]["log"]).parent, self.backups / "runs")
        self.assertEqual(server.read_info(self.backups)["snapshot"], SNAP)      # session.json names the run now
        self.threads.extend(h.thread for h in spawn.handles)
        self.assertEqual(self.run_cli("events")[1], 0)

    def test_a_setup_file_that_cannot_be_read_spawns_nothing(self):
        spawn = ThreadSpawner(FakeSession)
        with mock.patch.object(client, "spawn_server", spawn):
            reply, code = self.run_cli("start", "--permission", PERMISSION, "--setup", "border=%s" % (self.root / "no"))
            self.assertEqual((reply["refused"], code), ("bad_argument", 2))
            reply, code = self.run_cli("start", "--permission", PERMISSION, "--setup", "border")
            self.assertEqual((reply["refused"], code), ("bad_argument", 2))
        self.assertEqual(spawn.handles, [])

    def test_a_second_start_is_refused_while_one_runs(self):
        fake, _thread = self.serve()
        before = self.info_path.read_bytes()
        spawn = ThreadSpawner(FakeSession)
        with mock.patch.object(client, "spawn_server", spawn):
            reply, code = self.run_cli("start", "--permission", PERMISSION)
        self.assertEqual((reply["refused"], code), ("session_running", 2))
        self.assertEqual(spawn.handles, [])
        self.assertEqual(self.info_path.read_bytes(), before)
        # A second `start` posted to a server whose session has started touches nothing.
        self.assertEqual(client.call(self.backups, "start", {"permission": PERMISSION})[1], 0)
        reply, code = client.call(self.backups, "start", {"permission": PERMISSION})
        self.assertEqual((reply["refused"], code), ("session_running", 2))
        self.assertEqual([c[0] for c in fake.calls].count("start"), 1)
        self.assertEqual(fake.stops, 0)
        # A server deep in a verb answers nothing for now: it is running all the same.
        fake.release.clear()
        busy = threading.Thread(target=client.call, args=(self.backups, "advance", {"days": 5}, 10))
        busy.start()
        self.wait_for(lambda: ("advance", 5) in fake.calls, "the advance under way")
        with mock.patch.object(client, "STATUS_TIMEOUT_S", 0.3), mock.patch.object(client, "spawn_server", spawn):
            reply, code = self.run_cli("start", "--permission", PERMISSION)
        fake.release.set()
        busy.join(10)
        self.assertEqual((reply["refused"], code), ("session_running", 2))
        self.assertEqual(spawn.handles, [])
        self.assertEqual(self.info_path.read_bytes().decode("utf-8").count('"port"'), 1)

    def test_a_failed_start_whose_stop_can_be_retried_keeps_the_server_for_stop(self):
        fake = Retrying([RESTORED])
        fake.raises["start"] = session.SessionError("fixture_failed", "the fixture's run may have left its game up",
                                                    stop=LEFT_UP)
        spawn = ThreadSpawner(lambda: fake)
        with mock.patch.object(client, "spawn_server", spawn), mock.patch.object(client, "EXIT_WAIT_S", 0.5):
            reply, code = self.run_cli("start", "--permission", PERMISSION)
        self.threads.extend(h.thread for h in spawn.handles)
        self.assertEqual((reply["refused"], code), ("fixture_failed", 2))
        self.assertEqual(reply["next"], LEFT_UP["next"])           # the stop's own next, at the top
        self.assertNotIn("server_still_running", reply)            # it was not waited for: it serves on
        self.assertTrue(spawn.handles[0].thread.is_alive())
        self.assertEqual(self.run_cli("stop"), (RESTORED, 0))
        spawn.handles[0].thread.join(10)
        self.assertFalse(self.info_path.exists())

    def test_a_failed_start_runs_stop(self):
        for error, stops_itself in ((session.SessionError("no_permission", "say where the go-ahead came from"), False),
                                    (session.SessionError("launch_refused", "gpu_busy", reply={"refused": "gpu_busy"},
                                                          stop={"outcome": "restored"}), True)):
            with self.subTest(code=error.code):
                fake = FakeSession()
                fake.raises["start"] = error
                spawn = ThreadSpawner(lambda: fake)
                with mock.patch.object(client, "spawn_server", spawn):
                    reply, code = self.run_cli("start", "--permission", PERMISSION, "--as", "FRA")
                self.assertEqual((reply["refused"], code), (error.code, 2))
                # once: by the session's own start when it says so (its reply is final), else by the server
                self.assertEqual(fake.stops, 0 if stops_itself else 1)
                self.assertIn("stop", reply)
                if stops_itself:
                    self.assertEqual(reply["reply"], {"refused": "gpu_busy"})
                    self.assertEqual(reply["stop"], {"outcome": "restored"})
                # the client waited for the server to exit, and its file is gone
                self.assertFalse(spawn.handles[0].thread.is_alive())
                self.assertFalse(self.info_path.exists())

    def test_a_server_that_does_not_come_up_is_reported_with_its_log(self):
        class Dead:
            pid = 999_999

            def poll(self):
                return 1

            def wait(self, timeout=None):
                return 1

            def terminate(self):
                pass

        def spawn(backup_root, log):
            Path(log).write_text("Traceback: cannot read the game version\n", encoding="utf-8")
            return Dead()
        with mock.patch.object(client, "spawn_server", spawn):
            reply, code = self.run_cli("start", "--permission", PERMISSION)
        self.assertEqual((reply["refused"], code), ("server_failed", 2))
        self.assertIn("cannot read the game version", reply["detail"])


# A server in a child process, so that it can be killed or signalled. Its double's `start` builds the overlay and
# runs `snapshot` and `launch` for real (in-process, `gate` patched: the "game" is a record, nothing starts).
CHILD = r'''
import contextlib, io, json, sys, time
from pathlib import Path
from unittest import mock

from game_qa import __main__ as cli, gate, overlay, server

cfg = json.loads(sys.argv[1])
user, backups, marks = Path(cfg["user"]), Path(cfg["backups"]), Path(cfg["marks"])
game = gate.ProcId(4242, cfg["created"])
up = []


def mark(text):
    with open(marks, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def run_cli(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(list(argv))
    return json.loads(out.getvalue()), code


class Double:
    def start(self, permission, as_tag=None, setups=None, save=None, playset="mod_only", owner_confirmed_busy=False):
        overlay.build(user / "mod" / overlay.OVERLAY_NAME, {}, "1.15.0")
        snap, code = run_cli(["snapshot", "--save", save])
        assert code == 0, snap
        launched, code = run_cli(["launch", snap["id"], "--permission", permission, "--add-mod", cfg["overlay_win"],
                                  "--", "-gdpr-compliant", "-debug_mode", "-script_debugger", "-loadsave=" + save])
        assert code == 0, launched
        mark("launched")
        return {"snapshot": snap["id"], "pid": launched["pid"]}

    def advance(self, days):
        mark("advance began")
        time.sleep(1.0)
        mark("advance done")
        return (1836, 2, 1)

    def status(self):
        return {"started": True}

    def stop(self):
        mark("stop")
        return {"outcome": "restored", "held": False, "restored": [], "removed": [], "reason": ""}


def start_game(exe, args, cwd, *a, **k):
    up.append(game)
    return game


with mock.patch.object(gate, "list_games", lambda *a, **k: list(up)), \
        mock.patch.object(gate, "start_game", start_game), \
        mock.patch.object(gate, "sample_gpu", lambda *a, **k: [gate.GpuSample(14, 1607, 10240)] * 5), \
        mock.patch.object(gate, "windows_path", lambda path, *a, **k: "W:" + str(path)):
    mark("serving")
    result = server.SessionServer(Double(), backups, port=0).serve(signals=True)
    mark("exited after signal %s" % result.get("signal"))
'''


class ChildServerTestCase(ServerTestCase):
    """A user-data folder the protective verbs can work on, and a server in a child process over it."""

    def setUp(self):
        super().setUp()
        self.user = self.root / "Victoria 3"
        (self.user / "save games").mkdir(parents=True)
        (self.user / "logs").mkdir()
        (self.user / "mod").mkdir()
        (self.user / "save games" / "autosave.v3").write_bytes(b"the owner's autosave")
        (self.user / "save games" / "owner_save.v3").write_bytes(b"the owner's named save")
        (self.user / "continue_game.json").write_text('{"title": "autosave"}', encoding="utf-8")
        (self.user / "console_history.txt").write_text("money 1000\n", encoding="utf-8")
        (self.user / "logs" / "debug.log").write_text("the owner's log\n", encoding="utf-8")
        (self.user / "content_load.json").write_text(json.dumps({"enabledMods": [{"path": OWNER_MOD}]}, indent=2),
                                                     encoding="utf-8")
        self.base_game = self.root / "game"
        (self.base_game / "binaries").mkdir(parents=True)
        (self.base_game / "binaries" / "victoria3.exe").write_bytes(b"MZ")
        self.deploy = self.root / "deploy"
        (self.deploy / "events").mkdir(parents=True)
        self.marks = self.root / "marks.txt"
        env = {"VIC3_USER_DATA": str(self.user), "VIC3_BASE_GAME": str(self.base_game)}
        patch = mock.patch.dict(os.environ, env)
        patch.start()
        self.addCleanup(patch.stop)
        self.created = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")

    def spawn_child(self) -> subprocess.Popen:
        cfg = {"user": str(self.user), "backups": str(self.backups), "marks": str(self.marks),
               "created": self.created, "overlay_win": OVERLAY_WIN}
        log = open(self.root / "child.log", "wb")
        self.addCleanup(log.close)
        child = subprocess.Popen([sys.executable, "-c", CHILD, json.dumps(cfg)], cwd=REPO, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT)
        self.addCleanup(self._reap, child)
        self.wait_for(lambda: (server.read_info(self.backups) or {}).get("pid") == child.pid or child.poll() is not None,
                      "the child server's session.json", seconds=30)
        self.assertIsNone(child.poll(), self.child_log())
        return child

    def _reap(self, child):
        if child.poll() is None:
            child.kill()
        child.wait(10)

    def child_log(self) -> str:
        return (self.root / "child.log").read_text("utf-8", errors="replace")

    def marked(self) -> list[str]:
        return self.marks.read_text("utf-8").splitlines() if self.marks.exists() else []


class DeadServerTest(ChildServerTestCase):
    def real_session(self) -> session.Session:
        """A real Session over this user-data folder: its protective verbs are `python3 -m game_qa`, in-process."""
        helper = fakes.FakeHelper(history=self.user / "console_history.txt", log=self.user / "logs" / "debug.log")
        paths = session.Paths(
            user_data=self.user, backup_root=self.backups, deploy_dir=self.deploy, base_game=self.base_game,
            overlay_windows_path=OVERLAY_WIN, events_file_windows_path=lambda path: "W:" + str(path),
            game_version="1.15.0", enabled_mods=[OWNER_MOD, OVERLAY_WIN], deployed_mod_windows_path=OWNER_MOD)

        def no_watch(snapshot_id):
            raise AssertionError("watch spawned for %s: nothing may be launched" % snapshot_id)
        return session.Session(helper, in_process_cli, no_watch, paths, sleep=helper.sleep, clock=helper.clock)

    def test_a_dead_server_leaves_the_run_to_recover(self):
        child = self.spawn_child()
        reply, code = client.call(self.backups, "start", {"permission": PERMISSION, "save": "owner_save"}, timeout=60)
        self.assertEqual(code, 0, (reply, self.child_log()))
        dead_run = reply["snapshot"]
        self.assertEqual(self.marked(), ["serving", "launched"])
        child.send_signal(signal.SIGKILL)               # killed outright: no handler, no finally
        child.wait(10)
        self.assertEqual(self.marked(), ["serving", "launched"])        # it stopped nothing
        stale = server.read_info(self.backups)
        self.assertEqual(stale["pid"], child.pid)
        self.assertEqual(client.server_state(stale), "stale")
        before = tree(self.user)
        overlay_dir = self.user / "mod" / overlay.OVERLAY_NAME
        self.assertTrue((overlay_dir / ".metadata" / "metadata.json").is_file())      # the dead run's overlay

        game = gate.ProcId(4242, self.created)          # the dead run's game is still up
        spawn = ThreadSpawner(self.real_session)
        with mock.patch.object(gate, "list_games", return_value=[game]), \
                mock.patch.object(gate, "sample_gpu", return_value=IDLE), \
                mock.patch.object(gate, "start_game", side_effect=AssertionError("a game was started")), \
                mock.patch.object(gate, "windows_path", side_effect=lambda path, *a, **k: "W:" + str(path)), \
                mock.patch.object(client, "spawn_server", spawn):
            reply, code = self.run_cli("start", "--permission", PERMISSION, "--save", "owner_save", "--playset", "current")

        # refused before anything, because the dead run's overlay is there (its playset may still name it); the
        # caller is told to run `recover`, then `remove-overlay`
        self.assertEqual((reply["refused"], code), ("overlay_left", 2), reply)
        self.assertIn("recover", reply["detail"])
        self.assertIn("recover", reply["next"])
        for text in (reply["detail"], reply["next"]):
            self.assertIn("`python3 -m game_qa remove-overlay`", text)
        self.assertEqual(reply["stale_session"]["pid"], child.pid)
        self.assertIn("recover", reply["stale_session"]["detail"])
        # the new server is gone, and so is its file
        self.assertFalse(spawn.handles[0].thread.is_alive())
        self.assertFalse(self.info_path.exists())
        # nothing changed, the dead run's overlay included: it is neither replaced nor removed
        self.assertEqual(tree(self.user), before)
        self.assertTrue((overlay_dir / ".metadata" / "metadata.json").is_file())
        # the dead run is still unfinished: no verdict was given, and no snapshot was taken over it
        events = [e["event"] for e in snapshot.journal(snapshot.all_snapshots(self.backups)[-1])]
        self.assertIn("started", events)
        self.assertFalse({"restored", "held"} & set(events))
        self.assertEqual([s.id for s in snapshot.all_snapshots(self.backups)], [dead_run])

        # R4: `remove-overlay` refuses while that run is unfinished (its game may be up, and its playset names the
        # overlay), and says to `recover` it first (RemoveOverlayTest has the rest)
        with mock.patch.object(gate, "list_games", return_value=[]):
            refused, code = self.run_cli("remove-overlay")
        self.assertEqual((refused["refused"], code), ("unfinished_run", 2), refused)
        self.assertIn("recover", refused["next"])
        self.assertEqual(tree(self.user), before)


class SignalTest(ChildServerTestCase):
    def test_a_signal_stops_the_session_and_removes_the_file(self):
        for signum in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=signum):
                self.marks.unlink(missing_ok=True)
                child = self.spawn_child()
                child.send_signal(signum)
                self.assertEqual(child.wait(30), 0, self.child_log())
                self.assertEqual(self.marked(), ["serving", "stop", "exited after signal %d" % signum])
                self.assertFalse(self.info_path.exists())

    def test_a_signal_during_a_verb_lets_it_finish_then_stops(self):
        child = self.spawn_child()
        answer = {}
        talk = threading.Thread(target=lambda: answer.update(reply=client.call(self.backups, "advance", {"days": 3}, 30)))
        talk.start()
        self.wait_for(lambda: "advance began" in self.marked(), "the advance under way")
        child.send_signal(signal.SIGTERM)
        talk.join(30)
        self.assertEqual(answer["reply"], ({"reached": [1836, 2, 1]}, 0))       # answered, not cut short
        self.assertEqual(child.wait(30), 0, self.child_log())
        self.assertEqual(self.marked(), ["serving", "advance began", "advance done", "stop",
                                         "exited after signal %d" % signal.SIGTERM])
        self.assertFalse(self.info_path.exists())


class RemoveOverlayTest(ServerTestCase):
    """R4: `remove-overlay` removes the overlay an earlier run left, and a cut-short build's temp folder, only
    through overlay.remove's checks, and only once no server, game, unfinished run or held playset can use it."""

    def setUp(self):
        super().setUp()
        self.user = self.root / "Victoria 3"
        self.mod = self.user / "mod"
        self.mod.mkdir(parents=True)
        (self.mod / "Vic3TimelineExtended").mkdir()
        (self.mod / "Vic3TimelineExtended" / "descriptor.txt").write_bytes(b"the owner's mod")
        self.dest = self.mod / overlay.OVERLAY_NAME
        self.games: list = []
        patch = mock.patch.dict(os.environ, {"VIC3_USER_DATA": str(self.user)})
        patch.start()
        self.addCleanup(patch.stop)

    def list_games(self):
        if isinstance(self.games, Exception):
            raise self.games
        return list(self.games)

    def remove(self):
        return client.remove_overlay(self.user, self.backups, self.list_games, sleep=lambda s: None)

    def build_temp(self, name=".te_qa_overlay.tmp-k3j_9x2a") -> Path:
        """What a build killed between its first write and its rename leaves: a marked overlay under the temp name."""
        overlay.build(self.mod / overlay.OVERLAY_NAME, {}, "1.15.0").dir.rename(self.mod / name)
        return self.mod / name

    def run_snapshot(self, *events):
        snap = snapshot.take(self.user, self.backups)
        for event in events:
            snapshot.record(snap, event, **({"pid": 4242, "created": "c"} if event == "started" else {}))
        return snap.id

    def owner_files(self):
        ours = ("mod/" + overlay.OVERLAY_NAME, "mod/." + overlay.OVERLAY_NAME)
        return [(p, d) for p, _t, d in tree(self.user) if not p.startswith(ours)]

    def test_it_removes_the_overlay_and_a_marked_build_folder_and_nothing_else(self):
        temp = self.build_temp()
        overlay.build(self.dest, {"a": "set_variable = x"}, "1.15.0")
        self.run_snapshot("armed", "started", "playset", "playset_restored", "held")    # its playset is back
        self.run_snapshot("armed", "started", "playset", "restored")
        before = self.owner_files()
        reply, code = self.remove()
        self.assertEqual(code, 0, reply)
        self.assertEqual(sorted(reply["removed"]), sorted([str(self.dest), str(temp)]))
        self.assertFalse(os.path.lexists(self.dest))
        self.assertFalse(os.path.lexists(temp))
        self.assertEqual(self.owner_files(), before)
        self.assertEqual(sorted(os.listdir(self.mod)), ["Vic3TimelineExtended"])

    def test_with_nothing_there_it_says_so(self):
        self.assertEqual(self.remove()[1], 0)
        self.assertEqual(self.remove()[0]["removed"], [])

    def test_it_refuses_while_anything_may_still_use_the_overlay(self):
        cases = (
            ("game_running", lambda: setattr(self, "games", [gate.ProcId(4242, "2026-11-10T14:00:00.0000000Z")])),
            ("cannot_list_games", lambda: setattr(self, "games", gate.GateError("the listing did not finish"))),
            ("unfinished_run", lambda: self.run_snapshot("armed", "started")),
            ("playset_held", lambda: self.run_snapshot("armed", "started", "playset", "held")),
            ("playset_held", lambda: self.run_snapshot("armed", "started", "playset", "playset_written", "held")),
        )
        for code_name, arrange in cases:
            with self.subTest(refused=code_name):
                self.setUp()
                temp = self.build_temp()
                overlay.build(self.dest, {}, "1.15.0")
                arrange()
                before = tree(self.user)
                reply, code = self.remove()
                self.assertEqual((reply["refused"], code, reply["removed"]), (code_name, 2, []), reply)
                self.assertEqual(tree(self.user), before)
                self.assertTrue(temp.is_dir())

    def test_it_refuses_when_the_backup_root_cannot_be_seen(self):
        # X2: with the backup root's drive not mounted, the unfinished run whose playset names the overlay (and any
        # server's session.json) cannot be seen, so nothing may be removed
        self.run_snapshot("armed", "started", "playset")
        overlay.build(self.dest, {}, "1.15.0")
        self.assertEqual(self.remove()[0]["refused"], "unfinished_run")        # seen while the root is there
        before = tree(self.user)
        for root in (self.root / "not mounted" / "backups", self.root / "no backups here"):
            with self.subTest(root=root):
                reply, code = client.remove_overlay(self.user, root, self.list_games, sleep=lambda s: None)
                self.assertEqual((reply["refused"], code, reply["removed"]), ("backup_root", 2, []))
                self.assertIn(str(root if root.parent.is_dir() else root.parent), reply["detail"])
                self.assertEqual(tree(self.user), before)
        reply, _code = client.remove_overlay(self.user, self.root / "not mounted" / "backups", self.list_games,
                                             sleep=lambda s: None)
        self.assertIn("the backup root's folder %s does not exist" % (self.root / "not mounted"), reply["detail"])

    def test_it_refuses_while_a_session_server_answers_or_may(self):
        self.serve()
        overlay.build(self.dest, {}, "1.15.0")
        reply, code = self.remove()
        self.assertEqual((reply["refused"], code), ("session_running", 2))
        self.assertTrue(self.dest.is_dir())
        client.call(self.backups, "stop", {}, timeout=10)
        self.threads[0].join(10)
        self.info_path.write_text("{ half written", encoding="utf-8")          # what a server writes in one call
        self.assertEqual(self.remove()[0]["refused"], "session_running")
        self.assertTrue(self.dest.is_dir())
        self.info_path.unlink()
        self.write_info(free_port(), os.getpid())        # a dead server's file (this pid is no session-serve)
        self.assertEqual(self.remove()[1], 0)
        self.assertFalse(self.dest.exists())

    def test_a_folder_that_is_not_provably_the_harnesss_is_left(self):
        self.dest.mkdir()
        (self.dest / "notes.txt").write_bytes(b"someone else's")
        unmarked = self.mod / ".te_qa_overlay.tmp-zz9"
        unmarked.mkdir()                                      # a build killed before its first write
        before = tree(self.user)
        reply, code = self.remove()
        self.assertEqual((reply["refused"], code, reply["removed"]), ("not_ours", 2, []))
        self.assertEqual(sorted(entry["path"] for entry in reply["left"]), sorted([str(self.dest), str(unmarked)]))
        self.assertEqual(tree(self.user), before)
        self.assertTrue(unmarked.is_dir())

    def test_the_verb_runs_through_the_command_line_with_the_process_listing(self):
        overlay.build(self.dest, {}, "1.15.0")
        with mock.patch.object(gate, "list_games", return_value=[gate.ProcId(7, "c")]):
            reply, code = self.run_cli("remove-overlay")
        self.assertEqual((reply["refused"], code), ("game_running", 2))
        with mock.patch.object(gate, "list_games", return_value=[]):
            reply, code = self.run_cli("remove-overlay")
        self.assertEqual((reply["removed"], code), ([str(self.dest)], 0))
        self.assertFalse(self.dest.exists())

    def test_no_hint_says_to_remove_a_folder_by_hand(self):
        for text in (client.OVERLAY_LEFT_HINT, client.RECOVER_HINT, server.__doc__, session.__doc__):
            self.assertNotIn("by hand", text)
            self.assertNotIn("remove the folder", text)
        for hint in (client.OVERLAY_LEFT_HINT, client.RECOVER_HINT):
            self.assertIn("`python3 -m game_qa remove-overlay`", hint)


class DoctorTest(ServerTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.root / "Victoria 3"
        (self.user / "mod").mkdir(parents=True)
        self.deploy = self.root / "deploy"
        self.deploy.mkdir()
        self.base_game = self.root / "game"
        (self.base_game / "binaries").mkdir(parents=True)
        (self.base_game / "binaries" / "victoria3.exe").write_bytes(b"MZ")
        self.paths = {"game_user_data_path": self.user, "game_qa_backup_path": self.backups,
                      "mod_deploy_target": self.deploy, "base_game_path": self.base_game}

    def resolve(self, name):
        value = self.paths[name]
        if isinstance(value, Exception):
            raise value
        return value

    def run_snapshot(self, *events):
        snap = snapshot.take(self.user, self.backups)
        for event in events:
            snapshot.record(snap, event, **({"pid": 4242, "created": "c"} if event == "started" else {}))
        return snap.id

    def test_doctor_passes_a_ready_machine(self):
        reply, code = client.doctor(self.resolve, ping=lambda: "3.11.9", sample_gpu=lambda: IDLE[:1])
        self.assertEqual(code, 0, reply)
        self.assertTrue(reply["ok"])
        self.assertEqual(reply["problems"], [])
        self.assertIn("windows python: ok (Python 3.11.9)", reply["checks"])

    def test_doctor_names_what_is_missing(self):
        (self.base_game / "binaries" / "victoria3.exe").unlink()
        self.paths["mod_deploy_target"] = self.root / "not deployed"
        (self.user / "save games").mkdir()
        held = self.run_snapshot("armed", "started", "held")
        unfinished = self.run_snapshot("armed", "started")
        never_launched = self.run_snapshot("armed")
        overlay.build(self.user / "mod" / overlay.OVERLAY_NAME, {}, "1.15.0")
        self.write_info(free_port(), os.getpid())

        def no_python():
            raise HelperError("helper_gone", "could not start python.exe")
        before = tree(self.user), tree(self.backups)
        reply, code = client.doctor(self.resolve, ping=no_python, sample_gpu=lambda: [])
        self.assertEqual(code, 2)
        self.assertFalse(reply["ok"])
        problems = "\n".join(reply["problems"])
        for needle in ("not deployed", "victoria3.exe", "helper_gone", "nvidia-smi", held, unfinished,
                       never_launched, overlay.OVERLAY_NAME, "stale", "overlay_left"):
            self.assertIn(needle, problems)
        self.assertNotIn("replaces it", problems)              # `start` refuses a left overlay; it never replaces it
        self.assertEqual(len(reply["checks"]), 9)
        self.assertEqual((tree(self.user), tree(self.backups)), before)          # it changed nothing

    def test_doctor_says_when_a_path_is_not_set(self):
        self.paths["base_game_path"] = RuntimeError("base_game_path is not configured")
        reply, code = client.doctor(self.resolve, ping=lambda: "3.11.9", sample_gpu=lambda: IDLE[:1])
        self.assertEqual(code, 2)
        self.assertTrue(any("base_game_path" in p and "not configured" in p for p in reply["problems"]))


if __name__ == "__main__":
    unittest.main()
