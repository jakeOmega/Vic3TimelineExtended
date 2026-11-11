"""game_qa/dap.py: Debug Adapter Protocol framing and the debugger client.

`Server` stands in for the game: it decodes what the client sends and answers
from what the test queued. The recorded replies in
test_fixtures/game_qa/debugger_messages.json are the game's own (2026-11-10).
"""
import json
import unittest
from pathlib import Path

from game_qa import dap

STOPPED = {"type": "event", "event": "stopped", "body": {"reason": "breakpoint", "threadId": 1}}
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
        self._after: list[dict] = []
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
            for event in self._after:
                self.push(event)
            self._after = []

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

    def after_next_reply(self, events: list[dict]) -> None:
        self._after = list(events)

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

    def raw(self, body: bytes) -> bytes:
        return b"Content-Length: %d\r\n\r\n" % len(body) + body

    def test_a_header_block_without_a_length_is_dropped_and_the_stream_goes_on(self):
        d = dap.Decoder()
        self.assertEqual(d.feed(b"Hello\r\n\r\n" + dap.encode({"a": 1}) + b"X-Other: 1\r\n\r\n" + dap.encode({"b": 2})),
                         [{"a": 1}, {"b": 2}])
        self.assertEqual(d.skipped, 2)
        self.assertEqual(d.feed(dap.encode({"c": 3})), [{"c": 3}])

    def test_a_body_that_is_not_json_is_skipped_and_the_messages_around_it_are_returned(self):
        d = dap.Decoder()
        data = dap.encode({"a": 1}) + self.raw(b"{not json") + dap.encode({"b": 2})
        self.assertEqual(d.feed(data), [{"a": 1}, {"b": 2}])
        self.assertEqual(d.skipped, 1)
        self.assertEqual(d.feed(dap.encode({"c": 3})), [{"c": 3}])         # not wedged on the same bytes
        self.assertEqual(d.skipped, 1)

    def test_a_body_that_is_not_utf8_is_read_with_replacement_characters(self):
        d = dap.Decoder()
        data = self.raw(b'{"event":"output","body":{"output":"caf\xe9"}}') + dap.encode({"b": 2})
        self.assertEqual(d.feed(data), [{"event": "output", "body": {"output": "caf\ufffd"}}, {"b": 2}])
        self.assertEqual(d.skipped, 0)

    def test_bytes_that_are_neither_utf8_nor_json_are_skipped_not_raised(self):
        d = dap.Decoder()
        self.assertEqual(d.feed(self.raw(b"\xff\xfe\x00") + dap.encode({"b": 2})), [{"b": 2}])
        self.assertEqual(d.skipped, 1)

    def test_json_that_is_not_an_object_is_skipped(self):
        d = dap.Decoder()
        self.assertEqual(d.feed(self.raw(b"[1, 2]") + self.raw(b"7") + dap.encode({"b": 2})), [{"b": 2}])
        self.assertEqual(d.skipped, 2)

    def test_a_skipped_message_split_across_feeds_is_still_skipped_once(self):
        d = dap.Decoder()
        data = self.raw(b"{not json") + dap.encode({"b": 2})
        self.assertEqual(d.feed(data[:20]), [])
        self.assertEqual(d.feed(data[20:]), [{"b": 2}])
        self.assertEqual(d.skipped, 1)


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

    def test_poll_stopped_reads_what_has_arrived_without_waiting(self):
        waits = []
        recv = self.server.recv
        dbg = dap.Debugger(self.server.send, lambda timeout: (waits.append(timeout), recv(timeout))[1])
        self.assertFalse(dbg.poll_stopped())
        self.server.push({"type": "event", "event": "stopped", "body": {"reason": "breakpoint", "threadId": 1}})
        self.assertTrue(dbg.poll_stopped())
        self.assertEqual(dbg.last_stop_reason, "breakpoint")
        self.assertFalse(dbg.poll_stopped())
        self.assertEqual(waits, [0, 0, 0])                  # one look each, and none of them waits

    def test_a_stop_seen_before_a_resume_does_not_satisfy_the_next_wait(self):
        stopped = {"type": "event", "event": "stopped", "body": {"reason": "breakpoint", "threadId": 1}}
        self.server.push(stopped)
        self.server.reply("evaluate", {"result": "1"})
        self.dbg.evaluate("x")                      # reads the stop on the way to its own reply
        self.server.reply("continue")
        self.dbg.resume()
        self.assertFalse(self.dbg.wait_stopped(0.01))
        self.server.push(stopped)                   # the next real one still counts
        self.assertTrue(self.dbg.wait_stopped(1.0))

    def test_a_stop_that_arrives_ahead_of_the_continue_reply_is_not_the_next_one_either(self):
        stopped = {"type": "event", "event": "stopped", "body": {"reason": "breakpoint", "threadId": 1}}
        self.server.before_next_reply([stopped])
        self.server.reply("continue")
        self.dbg.resume()
        self.assertFalse(self.dbg.wait_stopped(0.01))

    def test_a_stop_that_follows_the_continue_reply_in_the_same_chunk_counts(self):
        # The live order: the continue reply, `continued`, then `stopped` (a breakpoint the game passes again at once).
        self.server.after_next_reply([{"type": "event", "event": "continued", "body": {"threadId": 1}}, STOPPED])
        self.server.reply("continue")
        self.dbg.resume()
        self.assertTrue(self.dbg.wait_stopped(0.01))
        self.assertFalse(self.dbg.wait_stopped(0.01))

    def test_only_the_stop_after_the_reply_counts_when_one_comes_before_it_in_the_same_chunk(self):
        self.server.before_next_reply([STOPPED])
        self.server.after_next_reply([STOPPED])
        self.server.reply("continue")
        self.dbg.resume()
        self.assertTrue(self.dbg.wait_stopped(0.01))
        self.assertFalse(self.dbg.wait_stopped(0.01))

    def test_a_resume_that_could_not_be_sent_forgets_the_stops(self):
        self.server.push(STOPPED)
        self.server.reply("evaluate", {"result": "1"})
        calls = []

        def send(data):
            calls.append(data)
            if len(calls) == 1:
                self.server.send(data)
            else:
                raise OSError("tcp_closed")
        dbg = dap.Debugger(send, self.server.recv)
        dbg.evaluate("x")                           # reads the stop on the way to its own reply
        with self.assertRaises(dap.DebuggerError):
            dbg.resume()
        self.assertFalse(dbg.wait_stopped(0.01))
        self.server.push(STOPPED)                   # and the marker is gone: a later stop counts
        self.assertTrue(dbg.wait_stopped(1.0))

    def test_a_refused_resume_forgets_the_stops_too(self):
        stopped = {"type": "event", "event": "stopped", "body": {"reason": "breakpoint", "threadId": 1}}
        self.server.before_next_reply([stopped])
        self.server.reply("continue", success=False, message="not stopped")
        with self.assertRaises(dap.DebuggerError):
            self.dbg.resume()
        self.assertFalse(self.dbg.wait_stopped(0.01))

    def test_every_stopped_event_is_a_stop(self):
        for reason in ("breakpoint", "step", "pause"):
            self.server.push({"type": "event", "event": "stopped", "body": {"reason": reason, "threadId": 1}})
        self.assertEqual([self.dbg.wait_stopped(1.0) for _ in range(4)], [True, True, True, False])

    def test_the_reason_of_the_stop_last_taken_is_kept(self):
        self.assertIsNone(self.dbg.last_stop_reason)
        for reason in ("pause", "breakpoint"):
            self.server.push({"type": "event", "event": "stopped", "body": {"reason": reason, "threadId": 1}})
        taken = []
        while self.dbg.wait_stopped(0.01):
            taken.append(self.dbg.last_stop_reason)
        self.assertEqual(taken, ["pause", "breakpoint"])         # each stop's own, in order, not the latest seen
        self.server.push({"type": "event", "event": "stopped", "body": {"threadId": 1}})
        self.assertTrue(self.dbg.wait_stopped(0.01))
        self.assertIsNone(self.dbg.last_stop_reason)              # a stop that gave no reason
        self.server.push(STOPPED)
        self.server.reply("continue")
        self.dbg.resume()                                          # the stops forgotten: no reason is left over
        self.assertIsNone(self.dbg.last_stop_reason)

    def test_a_bad_message_among_the_replies_does_not_wedge_the_client(self):
        self.server._out += b"Content-Length: 9\r\n\r\n{not json"
        self.server._out += b"Content-Length: 2\r\n\r\n\xff\xfe"
        self.server.reply("evaluate", {"result": "yes - Yes"})
        self.assertIs(self.dbg.evaluate("is_player = yes").value, True)
        self.server.reply("evaluate", {"result": "no - No"})
        self.assertIs(self.dbg.evaluate("is_player = yes").value, False)

    def test_messages_of_odd_shapes_are_skipped_and_counted_and_the_rest_of_the_chunk_is_kept(self):
        for odd in ({"type": "response", "request_seq": [1], "command": "evaluate", "success": True},
                    {"type": "response", "request_seq": {"a": 1}, "command": "evaluate", "success": True},
                    {"type": "event", "event": "output", "body": "just a string"},
                    {"type": "event", "event": "stopped", "body": [1, 2]},
                    {"type": "response", "request_seq": 99, "command": "evaluate", "success": True, "body": [1]}):
            self.server.push(odd)
        self.server.push(STOPPED)
        self.server.reply("evaluate", {"result": "7"})
        self.assertEqual(self.dbg.evaluate("x").value, 7.0)
        self.assertTrue(self.dbg.wait_stopped(0.01))
        self.assertFalse(self.dbg.wait_stopped(0.01))
        self.assertEqual(self.dbg.skipped, 5)

    def test_an_error_of_the_send_callable_is_a_debugger_error(self):
        boom = OSError("tcp_closed")

        def send(data):
            raise boom
        dbg = dap.Debugger(send, self.server.recv)
        with self.assertRaises(dap.DebuggerError) as e:
            dbg.evaluate("x")
        self.assertIs(e.exception.__cause__, boom)

    def test_an_error_of_the_recv_callable_is_a_debugger_error(self):
        boom = ConnectionResetError("the peer closed the connection")

        def recv(timeout):
            raise boom
        dbg = dap.Debugger(self.server.send, recv)
        with self.assertRaises(dap.DebuggerError) as e:
            dbg.wait_stopped(0.5)
        self.assertIs(e.exception.__cause__, boom)
        with self.assertRaises(dap.DebuggerError) as e:
            dbg.evaluate("x")
        self.assertIs(e.exception.__cause__, boom)

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
