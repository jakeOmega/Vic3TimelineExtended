"""game_qa/dap.py: Debug Adapter Protocol framing and the debugger client.

`Server` stands in for the game: it decodes what the client sends and answers
from what the test queued. The recorded replies in
test_fixtures/game_qa/debugger_messages.json are the game's own (2026-11-10).
"""
import json
import unittest
from pathlib import Path

from game_qa import dap

RECORDED = json.loads(
    (Path(__file__).resolve().parent / "test_fixtures" / "game_qa" / "debugger_messages.json").read_text("utf-8")
)


def recorded(command: str) -> list[dict]:
    return [m for m in RECORDED if m.get("type") == "response" and m.get("command") == command]


class Server:
    """Answers each request with the next queued reply for its command."""

    def __init__(self):
        self.requests: list[dict] = []
        self._decoder = dap.Decoder()
        self._out = b""
        self._replies: dict[str, list[dict]] = {}
        self._before: list[dict] = []
        self._seq = 0

    # the client's two callables
    def send(self, data: bytes) -> None:
        for req in self._decoder.feed(data):
            self.requests.append(req)
            for event in self._before:
                self.push(event)
            self._before = []
            queue = self._replies.get(req["command"])
            if queue:
                reply = dict(queue.pop(0))
                reply.update(type="response", request_seq=req["seq"], command=req["command"])
                self.push(reply)

    def recv(self, timeout: float) -> bytes:
        data, self._out = self._out, b""
        return data

    # what a test queues
    def push(self, msg: dict) -> None:
        self._seq += 1
        self._out += dap.encode(dict(msg, seq=self._seq))

    def reply(self, command: str, body: dict | None = None, success: bool = True, message: str = "") -> None:
        msg: dict = {"success": success, "body": body or {}}
        if message:
            msg["message"] = message
        self._replies.setdefault(command, []).append(msg)

    def before_next_reply(self, events: list[dict]) -> None:
        self._before = list(events)

    def script_attach(self, verified: bool) -> None:
        self.reply("initialize", {"supportsConfigurationDoneRequest": True})
        self.reply("launch")
        self.reply("setBreakpoints", {"breakpoints": [{"verified": verified, "line": 9}]})
        self.reply("configurationDone")


class FramingTest(unittest.TestCase):
    def test_encode_then_decode(self):
        msg = {"seq": 1, "type": "request", "command": "threads"}
        self.assertEqual(dap.Decoder().feed(dap.encode(msg)), [msg])

    def test_header_counts_bytes_not_characters(self):
        data = dap.encode({"b": "é"})
        head, body = data.split(b"\r\n\r\n")
        self.assertEqual(head, b"Content-Length: %d" % len(body))

    def test_decoder_handles_split_and_joined_messages(self):
        data = dap.encode({"a": 1}) + dap.encode({"b": "é"})
        d = dap.Decoder()
        self.assertEqual(d.feed(data[:10]), [])
        self.assertEqual(d.feed(data[10:]), [{"a": 1}, {"b": "é"}])

    def test_garbage_header_raises(self):
        with self.assertRaises(dap.DebuggerError):
            dap.Decoder().feed(b"Hello\r\n\r\n{}")


class DebuggerTest(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.dbg = dap.Debugger(self.server.send, self.server.recv)

    def test_attach_sends_the_probe_sequence(self):
        self.server.script_attach(verified=True)
        out = self.dbg.attach({"C:\\m\\events\\te_qa.txt": [9]})
        self.assertEqual([m["command"] for m in self.server.requests],
                         ["initialize", "launch", "setBreakpoints", "configurationDone"])
        self.assertEqual(out, {"C:\\m\\events\\te_qa.txt": [True]})
        bp = self.server.requests[2]["arguments"]
        self.assertEqual(bp, {"source": {"path": "C:\\m\\events\\te_qa.txt"}, "breakpoints": [{"line": 9}]})

    def test_attach_reports_an_unverified_breakpoint(self):
        self.server.script_attach(verified=False)
        self.assertEqual(self.dbg.attach({"C:\\x.txt": [9]}), {"C:\\x.txt": [False]})

    def test_reply_is_found_behind_nine_hundred_events(self):
        noise = {"type": "event", "event": "output",
                 "body": {"category": "stderr", "output": "Flag 'KAT' is set but is never used\n"}}
        self.server.before_next_reply([noise] * 900)
        self.server.reply("evaluate", {"result": "yes - Yes: \nYes: is_player; Subject: Country Great Britain (1); "})
        self.assertIs(self.dbg.evaluate("is_player = yes").value, True)
        self.assertEqual(len(self.dbg.errors()), 900)
        self.assertEqual(self.dbg.errors(), [])

    def test_the_recorded_evaluations(self):
        replies = recorded("evaluate")
        self.assertGreaterEqual(len(replies), 5)
        for reply in replies:
            self.server.reply("evaluate", reply.get("body"), reply["success"], reply.get("message", ""))
        got = [self.dbg.evaluate("x") for _ in replies]
        self.assertIn(True, [e.value for e in got])           # is_player = yes
        self.assertIn(False, [e.value for e in got])          # has_variable = te_qa_nonexistent
        self.assertIn(21570770.55692, [e.value for e in got])  # c:FRA.gdp
        refused = [e for e in got if not e.ok]
        self.assertTrue(refused)
        self.assertEqual({e.raw for e in refused}, {"not a valid trigger or script value"})
        self.assertEqual({e.value for e in refused}, {None})

    def test_number_and_refusals(self):
        self.server.reply("evaluate", {"result": "21570770.55692"})
        self.assertEqual(self.dbg.evaluate("c:FRA.gdp").value, 21570770.55692)
        self.server.reply("evaluate", success=False, message="not a valid trigger or script value")
        e = self.dbg.evaluate("gdp")
        self.assertEqual((e.ok, e.value, e.raw), (False, None, "not a valid trigger or script value"))
        self.server.reply("evaluate", success=False, message="not stopped")
        self.assertEqual(self.dbg.evaluate("c:FRA.gdp").raw, "not stopped")

    def test_text_that_is_neither_is_none(self):
        self.server.reply("evaluate", {"result": "Country Great Britain (1)"})
        e = self.dbg.evaluate("c:GBR")
        self.assertEqual((e.ok, e.value), (True, None))

    def test_evaluate_sends_the_frame(self):
        self.server.reply("evaluate", {"result": "1"})
        self.dbg.evaluate("c:FRA.gdp", frame=2)
        self.assertEqual(self.server.requests[0]["arguments"],
                         {"expression": "c:FRA.gdp", "frameId": 2, "context": "watch"})

    def test_wait_stopped(self):
        self.server.push({"type": "event", "event": "stopped", "body": {"reason": "breakpoint", "threadId": 1}})
        self.assertTrue(self.dbg.wait_stopped(1.0))
        self.assertFalse(self.dbg.wait_stopped(0.01))

    def test_scopes(self):
        self.server.reply("scopes", recorded("scopes")[0]["body"])
        for reply in recorded("variables"):
            self.server.reply("variables", reply["body"])
        got = self.dbg.scopes()
        self.assertEqual(got["Scope"]["this"], "Country Great Britain (1)")
        self.assertEqual(got["Scope"]["root"], "Country Great Britain (1)")
        self.assertEqual(got["Saved Scopes"], {})

    def test_resume(self):
        self.server.reply("continue")
        self.dbg.resume()
        self.assertEqual(self.server.requests[0]["arguments"], {"threadId": 1})

    def test_no_reply_raises(self):
        with self.assertRaises(dap.DebuggerError):
            self.dbg.evaluate("x", timeout=0.01)

    def test_a_refused_request_raises(self):
        self.server.reply("continue", success=False, message="not stopped")
        with self.assertRaises(dap.DebuggerError):
            self.dbg.resume()


if __name__ == "__main__":
    unittest.main()
