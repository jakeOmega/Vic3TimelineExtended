"""game_qa/win_helper.py, helper.py and fakes.py: the Windows-side helper and its refusals.

Nothing here starts a Windows program or needs the game: `handle` runs over
`fakes.FakeBackend`, `ProcessHelper` over a fake `popen` and `wslpath`.
"""
import ast
import base64
import ctypes
import io
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from collections import deque
from pathlib import Path

from game_qa import fakes, helper, win_helper
from game_qa.gate import ProcId

ROOT = Path(__file__).resolve().parent


class BackendCase(unittest.TestCase):
    def setUp(self):
        self.backend = fakes.FakeBackend()
        self.state = win_helper.State()

    def call(self, op, **fields):
        return win_helper.handle({"id": 1, "op": op, **fields}, self.backend, self.state)


class RefusalTest(BackendCase):
    def test_keys_refused_when_the_game_is_not_in_front(self):
        self.backend.foreground = 999
        out = self.call("keys", pid=7, steps=[{"text": "event x"}, {"scan": 0x1C}])
        self.assertEqual(out["error"], "not_foreground"); self.assertEqual(self.backend.sent, [])

    def test_keys_stop_at_the_step_where_focus_is_lost(self):
        self.backend.lose_focus_after = 1
        out = self.call("keys", pid=7, steps=[{"text": "a"}, {"scan": 0x1C}])
        self.assertEqual(out["error"], "not_foreground"); self.assertEqual(self.backend.sent, [("text", "a")])

    def test_a_refused_keys_request_says_how_many_steps_ran(self):
        self.backend.lose_focus_after = 1
        out = self.call("keys", pid=7, steps=[{"text": "a"}, {"scan": 0x1C}])
        self.assertEqual(out["steps_done"], 1)
        self.backend.foreground = 999
        self.assertEqual(self.call("keys", pid=7, steps=[{"scan": 1}])["steps_done"], 0)

    def test_text_with_a_newline_is_refused_before_any_step(self):
        out = self.call("keys", pid=7, steps=[{"scan": 0x29}, {"text": "a\nb"}])
        self.assertEqual(out["error"], "bad_text"); self.assertEqual(self.backend.sent, [])

    def test_text_with_a_carriage_return_is_refused_before_any_step(self):
        out = self.call("keys", pid=7, steps=[{"scan": 0x29}, {"text": "a\rb"}])
        self.assertEqual(out["error"], "bad_text"); self.assertEqual(self.backend.sent, [])

    def test_a_malformed_step_is_refused_before_any_step(self):
        for steps in ([{"scan": 0x29}, {"nope": 1}], [{"scan": "x"}], [{"text": 5}], [{"wait_ms": -1}],
                      [{"scan": 1, "text": "a"}], ["scan"], "scan", [{"scan": True}]):
            with self.subTest(steps=steps):
                out = self.call("keys", pid=7, steps=steps)
                self.assertEqual(out["error"], "bad_request"); self.assertEqual(self.backend.sent, [])

    def test_no_window_is_not_in_front(self):
        self.backend.windows.clear()
        out = self.call("keys", pid=7, steps=[{"scan": 0x29}])
        self.assertEqual(out["error"], "not_foreground"); self.assertEqual(self.backend.sent, [])

    def test_a_zero_handle_is_never_in_front(self):
        # A pid with no usable window has hwnd 0, and a locked desktop can report a foreground of 0.
        self.backend.windows[7]["hwnd"] = 0
        self.backend.foreground = 0
        out = self.call("keys", pid=7, steps=[{"scan": 0x29}])
        self.assertEqual(out["error"], "not_foreground"); self.assertEqual(self.backend.sent, [])

    def test_the_window_is_looked_up_again_before_every_step(self):
        looked = []
        real = self.backend.window_of
        self.backend.window_of = lambda pid: looked.append(pid) or real(pid)
        self.call("keys", pid=7, steps=[{"scan": 1}, {"wait_ms": 5}, {"scan": 2}])
        self.assertEqual(looked, [7, 7, 7])

    def test_kill_refuses_a_process_it_did_not_start(self):
        self.assertEqual(self.call("kill", pid=4242)["error"], "not_ours"); self.assertEqual(self.backend.terminated, [])

    def test_kill_refuses_a_reused_pid(self):
        pid = self.call("launch", exe="victoria3.exe", args=[], cwd="C:\\g")["pid"]
        self.backend.creation[pid] = "2026-11-10T15:00:00.0000000Z"       # another process now has the id
        self.assertEqual(self.call("kill", pid=pid)["error"], "not_ours")

    def test_a_reused_pid_is_not_terminated(self):
        pid = self.call("launch", exe="victoria3.exe", args=[], cwd="C:\\g")["pid"]
        self.backend.creation[pid] = "2026-11-10T15:00:00.0000000Z"
        self.call("kill", pid=pid)
        self.assertEqual(self.backend.terminated, []); self.assertEqual(self.backend.terminate_args, [])

    def test_kill_of_a_process_it_started_that_has_already_exited_is_ok_and_forgets_it(self):
        pid = self.call("launch", exe="victoria3.exe", args=[], cwd="C:\\g")["pid"]
        del self.backend.creation[pid]                  # it ended on its own
        out = self.call("kill", pid=pid)
        self.assertTrue(out["ok"]); self.assertIs(out["already_exited"], True)
        self.assertEqual(self.backend.terminated, []); self.assertEqual(self.state.ours, {})
        self.assertEqual(self.call("kill", pid=pid)["error"], "not_ours")       # and is no longer one it may end

    def test_kill_of_an_exited_process_lets_the_backend_let_go_of_its_handle(self):
        # The real backend keeps a Popen (a handle) for each child it started, to pin the pid.
        pid = self.call("launch", exe="victoria3.exe", args=[], cwd="C:\\g")["pid"]
        del self.backend.creation[pid]
        self.call("kill", pid=pid)
        self.assertEqual(self.backend.forgotten, [pid])

    def test_a_kill_that_ends_the_process_does_not_say_it_had_exited(self):
        pid = self.call("launch", exe="victoria3.exe", args=[], cwd="C:\\g")["pid"]
        self.assertNotIn("already_exited", self.call("kill", pid=pid))

    def test_kill_ends_what_it_started_and_forgets_it(self):
        pid = self.call("launch", exe="victoria3.exe", args=[], cwd="C:\\g")["pid"]
        self.assertTrue(self.call("kill", pid=pid)["ok"])
        self.assertEqual(self.backend.terminated, [pid]); self.assertEqual(self.state.ours, {})

    def test_kill_hands_the_recorded_creation_time_to_the_backend(self):
        # The real backend re-reads it through the handle it ends, which closes the pid-reuse window.
        pid = self.call("launch", exe="victoria3.exe", args=[], cwd="C:\\g")["pid"]
        recorded = self.state.ours[pid]
        self.call("kill", pid=pid)
        self.assertEqual(self.backend.terminate_args, [(pid, recorded)])

    def test_kill_reports_a_process_whose_handle_changed_underneath(self):
        pid = self.call("launch", exe="victoria3.exe", args=[], cwd="C:\\g")["pid"]
        self.backend.terminate_result = False
        self.assertEqual(self.call("kill", pid=pid)["error"], "not_ours")
        self.assertIn(pid, self.state.ours)

    def test_adopt_checks_the_creation_time(self):
        self.backend.creation[55] = "A"
        self.assertEqual(self.call("adopt", pid=55, created="B")["error"], "not_ours")
        self.assertTrue(self.call("adopt", pid=55, created="A")["ok"])

    def test_adopt_records_the_pair_only_when_it_matches(self):
        self.backend.creation[55] = "A"
        self.call("adopt", pid=55, created="B")
        self.assertEqual(self.state.ours, {})
        self.call("adopt", pid=55, created="A")
        self.assertEqual(self.state.ours, {55: "A"})

    def test_adopt_of_a_missing_process_is_not_ours(self):
        self.assertEqual(self.call("adopt", pid=56, created="A")["error"], "not_ours")

    def test_adopted_process_can_be_killed(self):
        self.backend.creation[55] = "A"
        self.call("adopt", pid=55, created="A")
        self.assertTrue(self.call("kill", pid=55)["ok"]); self.assertEqual(self.backend.terminated, [55])

    def test_unknown_op_and_bad_json_do_not_raise(self):
        self.assertEqual(self.call("nope")["error"], "unknown_op")

    def test_requests_that_are_not_requests_do_not_raise(self):
        self.assertEqual(win_helper.handle([1, 2], self.backend, self.state)["error"], "bad_request")
        self.assertEqual(win_helper.handle({"id": 3}, self.backend, self.state)["error"], "unknown_op")
        self.assertEqual(win_helper.handle({"op": 5}, self.backend, self.state)["error"], "unknown_op")

    def test_missing_or_mistyped_fields_are_bad_requests(self):
        for op, fields in (("kill", {}), ("kill", {"pid": "7"}), ("kill", {"pid": True}), ("window", {}),
                           ("launch", {"exe": "x", "args": "-a", "cwd": ""}), ("adopt", {"pid": 5}),
                           ("tcp_open", {"port": 0}), ("tcp_open", {"port": 70000}), ("tcp_send", {"b64": 5})):
            with self.subTest(op=op, fields=fields):
                self.assertEqual(self.call(op, **fields)["error"], "bad_request")

    def test_a_backend_exception_becomes_a_backend_error(self):
        def boom(pid):
            raise OSError("access denied")

        self.backend.window_of = boom
        out = self.call("window", pid=7)
        self.assertEqual((out["ok"], out["error"]), (False, "backend_error"))
        self.assertIn("access denied", out["detail"]); self.assertEqual(out["id"], 1)

    def test_replies_carry_the_request_id(self):
        self.assertEqual(self.call("ping")["id"], 1)
        self.assertIsNone(win_helper.handle({"op": "ping"}, self.backend, self.state)["id"])


class LaunchWindowTest(BackendCase):
    def test_ping_names_the_python(self):
        out = self.call("ping")
        self.assertTrue(out["ok"]); self.assertRegex(out["python"], r"^\d+\.\d+")

    def test_launch_records_the_pair(self):
        out = self.call("launch", exe="victoria3.exe", args=["-debug_mode"], cwd="C:\\g")
        self.assertTrue(out["ok"])
        self.assertRegex(out["created"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{7}Z$")
        self.assertEqual(self.state.ours, {out["pid"]: out["created"]})
        self.assertEqual(self.backend.launched, [("victoria3.exe", ["-debug_mode"], "C:\\g")])

    def test_a_process_gone_at_launch_is_a_launch_failure(self):
        self.backend.vanish_on_launch = True
        self.assertEqual(self.call("launch", exe="victoria3.exe", args=[], cwd="")["error"], "launch_failed")
        self.assertEqual(self.state.ours, {})

    def test_window_of_a_running_game(self):
        out = self.call("window", pid=7)
        self.assertEqual((out["exists"], out["hwnd"], out["title"], out["foreground"], out["responding"]),
                         (True, 70, "Victoria 3", True, True))
        self.assertEqual(out["client"], [0, 0, 1920, 1080])

    def test_window_not_in_front(self):
        self.backend.foreground = 999
        self.assertFalse(self.call("window", pid=7)["foreground"])

    def test_window_that_does_not_respond(self):
        self.backend.windows[7]["responding"] = False
        self.assertFalse(self.call("window", pid=7)["responding"])

    def test_pid_without_a_window_is_not_an_error(self):
        out = self.call("window", pid=8)
        self.assertTrue(out["ok"])
        self.assertEqual((out["exists"], out["hwnd"], out["title"], out["foreground"], out["responding"], out["client"]),
                         (False, 0, "", False, False, [0, 0, 0, 0]))

    def test_focus_brings_the_window_to_the_front(self):
        self.backend.foreground = 999
        self.assertTrue(self.call("focus", pid=7)["foreground"]); self.assertEqual(self.backend.foreground, 70)

    def test_focus_reports_a_refusal_by_windows(self):
        self.backend.foreground = 999; self.backend.focus_succeeds = False
        self.assertFalse(self.call("focus", pid=7)["foreground"])

    def test_focus_leaves_a_window_already_in_front_alone(self):
        self.assertTrue(self.call("focus", pid=7)["foreground"]); self.assertEqual(self.backend.set_foreground_calls, 0)

    def test_focus_of_a_pid_without_a_window(self):
        out = self.call("focus", pid=8)
        self.assertTrue(out["ok"]); self.assertFalse(out["foreground"]); self.assertEqual(self.backend.set_foreground_calls, 0)


class KeysTest(BackendCase):
    def test_steps_run_in_order_while_the_game_is_in_front(self):
        out = self.call("keys", pid=7, steps=[{"scan": 0x29}, {"text": "event é1"}, {"wait_ms": 250}, {"scan": 0x1C}])
        self.assertTrue(out["ok"]); self.assertEqual(out["steps_done"], 4)
        self.assertEqual(self.backend.sent, [("scan", 0x29), *[("text", c) for c in "event é1"], ("scan", 0x1C)])
        self.assertEqual(self.backend.slept, [250])

    def test_an_empty_list_of_steps_is_fine(self):
        self.assertTrue(self.call("keys", pid=7, steps=[])["ok"]); self.assertEqual(self.backend.sent, [])

    def test_text_goes_out_one_character_at_a_time(self):
        self.call("keys", pid=7, steps=[{"text": "0123456789abcdefghij"}])
        self.assertEqual(self.backend.sent, [("text", c) for c in "0123456789abcdefghij"])

    def test_one_character_is_one_chunk(self):
        self.call("keys", pid=7, steps=[{"text": "a"}])
        self.assertEqual(self.backend.sent, [("text", "a")])

    def test_chunks_never_split_a_character(self):
        self.call("keys", pid=7, steps=[{"text": "a\U0001F600b"}])
        self.assertEqual(self.backend.sent, [("text", "a"), ("text", "\U0001F600"), ("text", "b")])

    def test_the_foreground_is_checked_before_every_character(self):
        looked = []
        self.backend.on_foreground_check = lambda: looked.append(1)
        self.call("keys", pid=7, steps=[{"text": "0123456789abcdefghij"}])
        self.assertEqual(len(looked), 20)

    def test_focus_lost_mid_string_stops_the_rest_and_says_how_much_went_out(self):
        self.backend.lose_focus_after = 3
        out = self.call("keys", pid=7, steps=[{"scan": 1}, {"text": "0123456789abcdefghij"}, {"scan": 2}])
        self.assertEqual(out["error"], "not_foreground")
        self.assertEqual((out["steps_done"], out["chars_sent"]), (1, 2))
        self.assertEqual(self.backend.sent, [("scan", 1), ("text", "0"), ("text", "1")])

    def test_a_refusal_before_the_first_character_says_zero_went_out(self):
        self.backend.foreground = 999
        out = self.call("keys", pid=7, steps=[{"text": "abc"}])
        self.assertEqual((out["error"], out["steps_done"], out["chars_sent"]), ("not_foreground", 0, 0))

    def test_an_empty_text_sends_nothing_but_still_needs_the_game_in_front(self):
        self.assertTrue(self.call("keys", pid=7, steps=[{"text": ""}])["ok"]); self.assertEqual(self.backend.sent, [])
        self.backend.foreground = 999
        self.assertEqual(self.call("keys", pid=7, steps=[{"text": ""}])["error"], "not_foreground")

    def test_the_last_input_is_looked_at_after_the_foreground_check_not_before(self):
        # A person types in the gap between the check and our key: the look must come after the check.
        self.backend.now = 100_000; self.backend.last_input = 40_000
        checks = []

        def person_types_during_the_second_check():
            checks.append(1)
            if len(checks) == 2:
                self.backend.now += 500; self.backend.last_input = self.backend.now

        self.backend.on_foreground_check = person_types_during_the_second_check
        self.call("keys", pid=7, steps=[{"scan": 1}, {"scan": 2}])
        self.backend.on_foreground_check = None
        self.backend.now = 101_500
        self.assertEqual(self.call("idle_ms")["idle_ms"], 1_000)

    def test_focus_lost_during_a_wait_stops_the_next_key(self):
        self.backend.lose_focus_after_sleep = True
        out = self.call("keys", pid=7, steps=[{"scan": 1}, {"wait_ms": 10}, {"scan": 2}])
        self.assertEqual(out["error"], "not_foreground"); self.assertEqual(self.backend.sent, [("scan", 1)])


class IdleTest(BackendCase):
    def test_idle_discounts_the_helpers_own_keys(self):
        self.backend.now = 100_000; self.backend.last_input = 40_000          # a person, 60 s ago
        self.assertEqual(self.call("idle_ms")["idle_ms"], 60_000)
        self.call("keys", pid=7, steps=[{"scan": 0x29}]); self.backend.now = 101_000   # our key at 100 s
        self.assertEqual(self.call("idle_ms")["idle_ms"], 61_000)

    def test_idle_sees_a_person_after_our_keys(self):
        self.call("keys", pid=7, steps=[{"scan": 0x29}])
        self.backend.now += 5_000; self.backend.last_input = self.backend.now - 1_000
        self.assertEqual(self.call("idle_ms")["idle_ms"], 1_000)

    def test_a_person_typing_during_a_wait_is_not_overwritten_by_the_next_key(self):
        self.backend.now = 100_000; self.backend.last_input = 40_000
        # someone types at the end of the wait, before our next key lands on top of it
        self.backend.on_sleep = lambda ms: setattr(self.backend, "last_input", self.backend.now)
        self.call("keys", pid=7, steps=[{"scan": 1}, {"wait_ms": 1_000}, {"scan": 2}])
        self.backend.now = 102_000
        self.assertEqual(self.call("idle_ms")["idle_ms"], 1_000)

    def test_a_person_within_the_allowance_is_taken_for_the_helper(self):
        before = self.backend.last_input
        self.call("keys", pid=7, steps=[{"scan": 0x29}])
        sent_at = self.backend.now
        self.backend.last_input = sent_at + 50; self.backend.now = sent_at + 10_000
        self.assertEqual(self.call("idle_ms")["idle_ms"], sent_at + 10_000 - before)

    def test_a_person_just_beyond_the_allowance_counts(self):
        self.call("keys", pid=7, steps=[{"scan": 0x29}])
        sent_at = self.backend.now
        self.backend.last_input = sent_at + 51; self.backend.now = sent_at + 10_000
        self.assertEqual(self.call("idle_ms")["idle_ms"], 10_000 - 51)

    def test_our_own_focus_attempt_is_not_a_person(self):
        self.backend.now = 100_000; self.backend.last_input = 40_000; self.backend.foreground = 999
        self.call("focus", pid=7)
        self.backend.now = 101_000
        self.assertEqual(self.backend.last_input, 100_000)        # the fake taps ALT, as Windows would see it
        self.assertEqual(self.call("idle_ms")["idle_ms"], 61_000)

    def test_no_alt_tap_when_the_plain_attempt_works(self):
        # A bare ALT lands in whatever window is in front, often the owner's, and can open its menu bar.
        self.backend.now = 100_000; self.backend.last_input = 40_000; self.backend.foreground = 999
        self.backend.needs_alt = False
        out = self.call("focus", pid=7)
        self.assertTrue(out["foreground"])
        self.assertEqual((self.backend.alt_taps, self.backend.set_foreground_calls), (0, 1))
        self.assertEqual(self.backend.last_input, 40_000); self.assertIsNone(self.state.last_sent_tick)
        self.backend.now = 101_000
        self.assertEqual(self.call("idle_ms")["idle_ms"], 61_000)

    def test_alt_is_tapped_once_when_the_plain_attempt_fails(self):
        self.backend.foreground = 999; self.backend.needs_alt = True
        self.assertTrue(self.call("focus", pid=7)["foreground"])
        self.assertEqual(self.backend.alt_taps, 1)

    def test_the_tap_not_the_end_of_the_wait_is_when_the_helper_last_sent(self):
        self.backend.now = 100_000; self.backend.last_input = 40_000; self.backend.foreground = 999
        # a person types while the helper waits for the window to come forward
        self.backend.during_focus_wait = lambda: setattr(self.backend, "last_input", self.backend.now)
        self.call("focus", pid=7)
        self.assertEqual(self.state.last_sent_tick, 100_000)
        self.backend.now = 101_000
        self.assertEqual(self.call("idle_ms")["idle_ms"], 700)

    def test_a_person_before_our_focus_attempt_still_counts(self):
        self.backend.now = 100_000; self.backend.last_input = 99_000; self.backend.foreground = 999
        self.call("focus", pid=7)
        self.backend.now = 100_500
        self.assertEqual(self.call("idle_ms")["idle_ms"], 1_500)

    def test_idle_is_never_negative(self):
        self.backend.now = 100; self.backend.last_input = 500
        self.assertEqual(self.call("idle_ms")["idle_ms"], 0)


class TcpTest(BackendCase):
    def test_tcp_only_to_loopback(self):
        self.assertTrue(self.call("tcp_open", port=6111)["ok"]); self.assertEqual(self.backend.connected, ("127.0.0.1", 6111))

    def test_a_host_in_the_request_is_ignored(self):
        self.call("tcp_open", port=6111, host="10.1.2.3")
        self.assertEqual(self.backend.connected, ("127.0.0.1", 6111))

    def test_connection_refused(self):
        self.backend.connect_error = ConnectionRefusedError("no listener")
        out = self.call("tcp_open", port=6111)
        self.assertEqual((out["ok"], out["error"]), (False, "connect_failed")); self.assertIn("no listener", out["detail"])
        self.assertIsNone(self.state.sock)

    def test_send_and_receive_carry_bytes_as_base64(self):
        self.call("tcp_open", port=6111)
        payload = b"Content-Length: 2\r\n\r\n{}\xff"
        self.assertTrue(self.call("tcp_send", b64=base64.b64encode(payload).decode())["ok"])
        self.assertEqual(self.backend.sock.sent, [payload])
        self.backend.sock.incoming.append(b"\x00reply\xfe")
        out = self.call("tcp_recv", timeout_ms=200)
        self.assertEqual(base64.b64decode(out["b64"]), b"\x00reply\xfe"); self.assertEqual(self.backend.sock.timeout, 0.2)

    def test_receive_timeout_is_empty_not_an_error(self):
        self.call("tcp_open", port=6111)
        out = self.call("tcp_recv", timeout_ms=10)
        self.assertEqual((out["ok"], out["b64"]), (True, ""))

    def test_a_closed_peer_is_an_error_distinct_from_a_timeout(self):
        self.call("tcp_open", port=6111)
        self.backend.sock.peer_closed = True
        self.assertEqual(self.call("tcp_recv", timeout_ms=10)["error"], "tcp_closed")
        self.assertIsNone(self.state.sock)

    def test_no_connection_is_not_open(self):
        for op, fields in (("tcp_send", {"b64": ""}), ("tcp_recv", {"timeout_ms": 1})):
            with self.subTest(op=op):
                self.assertEqual(self.call(op, **fields)["error"], "not_open")

    def test_bad_base64_is_a_bad_request(self):
        self.call("tcp_open", port=6111)
        self.assertEqual(self.call("tcp_send", b64="!!!")["error"], "bad_request")

    def test_a_failed_send_drops_the_connection(self):
        self.call("tcp_open", port=6111)
        self.backend.sock.send_error = BrokenPipeError("gone")
        self.assertEqual(self.call("tcp_send", b64="AA==")["error"], "tcp_closed")
        self.assertIsNone(self.state.sock)

    def test_a_send_does_not_inherit_the_receive_timeout(self):
        self.call("tcp_open", port=6111)
        self.call("tcp_recv", timeout_ms=1)          # leaves the socket at 1 ms
        self.call("tcp_send", b64="AA==")
        self.assertEqual(self.backend.sock.timeout_at_send, [win_helper.SEND_TIMEOUT_S])
        self.assertGreaterEqual(win_helper.SEND_TIMEOUT_S, 1)

    def test_close_is_idempotent(self):
        self.call("tcp_open", port=6111); sock = self.backend.sock
        self.assertTrue(self.call("tcp_close")["ok"]); self.assertTrue(sock.closed)
        self.assertTrue(self.call("tcp_close")["ok"])

    def test_opening_again_closes_the_old_connection(self):
        self.call("tcp_open", port=6111); first = self.backend.sock
        self.backend.sock = fakes.FakeSocket()
        self.call("tcp_open", port=6112)
        self.assertTrue(first.closed); self.assertIs(self.state.sock, self.backend.sock)


class ScreenshotTest(BackendCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.backend.windows[7]["client"] = (10, 20, 200, 100)

    def png_size(self, path):
        data = Path(path).read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        return struct.unpack(">II", data[16:24])

    def test_writes_a_png_of_the_client_area(self):
        path = str(Path(self.tmp.name) / "shots" / "a.png")
        out = self.call("screenshot", pid=7, path=path, max_width=1600)
        self.assertEqual((out["ok"], out["path"], out["width"], out["height"]), (True, path, 200, 100))
        self.assertEqual(self.png_size(path), (200, 100)); self.assertEqual(self.backend.captured, [(10, 20, 200, 100)])

    def test_scaled_down_to_the_requested_width(self):
        path = str(Path(self.tmp.name) / "b.png")
        out = self.call("screenshot", pid=7, path=path, max_width=50)
        self.assertEqual((out["width"], out["height"]), (50, 25)); self.assertEqual(self.png_size(path), (50, 25))

    def test_no_window_and_no_client_area(self):
        path = str(Path(self.tmp.name) / "c.png")
        self.assertEqual(self.call("screenshot", pid=8, path=path, max_width=100)["error"], "no_window")
        self.backend.windows[7]["client"] = (0, 0, 0, 0)
        self.assertEqual(self.call("screenshot", pid=7, path=path, max_width=100)["error"], "no_client_area")
        self.assertFalse(Path(path).exists())


class PureFunctionTest(unittest.TestCase):
    def chunks(self, data):
        pos, out = 8, []
        while pos < len(data):
            length, kind = struct.unpack(">I4s", data[pos:pos + 8])
            body = data[pos + 8:pos + 8 + length]
            (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
            self.assertEqual(crc, zlib.crc32(kind + body))
            out.append((kind, body)); pos += 12 + length
        return out

    def test_png_signature_and_header(self):
        data = win_helper.encode_png(3, 2, bytes(range(18)))
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        kinds = [k for k, _ in self.chunks(data)]
        self.assertEqual(kinds, [b"IHDR", b"IDAT", b"IEND"])
        self.assertEqual(struct.unpack(">IIBBBBB", self.chunks(data)[0][1]), (3, 2, 8, 2, 0, 0, 0))

    def test_png_pixels_round_trip(self):
        rgb = bytes(range(18))
        idat = b"".join(b for k, b in self.chunks(win_helper.encode_png(3, 2, rgb)) if k == b"IDAT")
        raw = zlib.decompress(idat)
        self.assertEqual(raw, b"\x00" + rgb[:9] + b"\x00" + rgb[9:])

    def test_png_refuses_the_wrong_amount_of_pixels(self):
        with self.assertRaises(ValueError):
            win_helper.encode_png(3, 2, b"\x00" * 17)

    def test_no_scaling_when_it_already_fits(self):
        rgb = bytes(range(12))
        self.assertEqual(win_helper.scale_rgb(2, 2, rgb, 2), (2, 2, rgb))
        self.assertEqual(win_helper.scale_rgb(2, 2, rgb, 1600), (2, 2, rgb))

    def test_nearest_neighbour_scaling(self):
        # a 4x2 image, pixel (x, y) = (x, y, 0); halved, it keeps the second column of each pair of columns
        rgb = b"".join(bytes((x, y, 0)) for y in range(2) for x in range(4))
        w, h, out = win_helper.scale_rgb(4, 2, rgb, 2)
        self.assertEqual((w, h), (2, 1))
        self.assertEqual(out, bytes((1, 1, 0, 3, 1, 0)))

    def test_scaling_keeps_a_row(self):
        w, h, out = win_helper.scale_rgb(1000, 1, b"\x01\x02\x03" * 1000, 10)
        self.assertEqual((w, h, len(out)), (10, 1, 30))

    def test_bgra_to_rgb(self):
        self.assertEqual(win_helper.bgra_to_rgb(2, 1, bytes([1, 2, 3, 255, 4, 5, 6, 255])), bytes([3, 2, 1, 6, 5, 4]))
        two_rows = bytes([10, 20, 30, 0, 40, 50, 60, 0])
        self.assertEqual(win_helper.bgra_to_rgb(1, 2, two_rows), bytes([30, 20, 10, 60, 50, 40]))

    def test_bgra_to_rgb_refuses_the_wrong_amount_of_pixels(self):
        with self.assertRaises(ValueError):
            win_helper.bgra_to_rgb(2, 1, b"\x00" * 7)

    def test_tick_age(self):
        self.assertEqual(win_helper.tick_age_ms(100, 40), 60)
        self.assertEqual(win_helper.tick_age_ms(7, 7), 0)

    def test_tick_age_across_the_32_bit_wrap(self):
        self.assertEqual(win_helper.tick_age_ms(5, 0xFFFFFFFB), 10)

    def test_last_input_on_the_64_bit_clock(self):
        self.assertEqual(win_helper.last_input_tick_from(10_000, 10_000, 4_000), 4_000)
        # the 64-bit clock is 3 ms past the wrap, the last input 19 ms ago, just before it
        self.assertEqual(win_helper.last_input_tick_from(2**32 + 3, 3, 0xFFFFFFF0), 2**32 - 16)

    def test_text_chunks(self):
        self.assertEqual(win_helper.text_chunks(""), [""])
        self.assertEqual(win_helper.text_chunks("abc"), ["a", "b", "c"])
        self.assertEqual(win_helper.text_chunks("a\U0001F600b"), ["a", "\U0001F600", "b"])
        self.assertEqual(win_helper.text_chunks("a" * 17, 8), ["a" * 8, "a" * 8, "a"])
        self.assertEqual(win_helper.text_chunks("abcdef", 4), ["abcd", "ef"])

    def test_a_key_is_released_after_it_is_pressed(self):
        calls, naps = [], []
        win_helper.tap_key(lambda code, flags: calls.append((code, flags)), naps.append, 0x29, win_helper.KEYEVENTF_SCANCODE, 0.04)
        self.assertEqual(calls, [(0x29, 0x0008), (0x29, 0x0008 | 0x0002)]); self.assertEqual(naps, [0.04])

    def test_a_key_is_released_even_if_the_wait_between_fails(self):
        calls = []

        def nap(seconds):
            raise RuntimeError("interrupted")

        with self.assertRaises(RuntimeError):
            win_helper.tap_key(lambda code, flags: calls.append((code, flags)), nap, 0x29, 0x0008, 0.04)
        self.assertEqual(calls, [(0x29, 0x0008), (0x29, 0x000A)])

    def test_a_failed_release_is_attempted_once_and_reported(self):
        calls = []

        def send(code, flags):
            calls.append(flags)
            if flags & win_helper.KEYEVENTF_KEYUP:
                raise OSError("SendInput refused")

        with self.assertRaises(OSError):
            win_helper.tap_key(send, lambda seconds: None, 0x29, 0x0008, 0.04)
        self.assertEqual(calls, [0x0008, 0x000A])

    def test_a_key_that_never_went_down_is_not_released(self):
        calls = []

        def send(code, flags):
            calls.append(flags)
            raise OSError("SendInput refused")

        with self.assertRaises(OSError):
            win_helper.tap_key(send, lambda seconds: None, 0x29, 0x0008, 0.04)
        self.assertEqual(calls, [0x0008])

    def test_filetime_epoch_and_a_real_moment(self):
        self.assertEqual(win_helper.filetime_to_iso(116444736000000000), "1970-01-01T00:00:00.0000000Z")
        ticks = (11644473600 + 1_794_337_162) * 10_000_000 + 1234567
        self.assertEqual(win_helper.filetime_to_iso(ticks), "2026-11-10T18:59:22.1234567Z")

    def test_filetime_keeps_seven_digits(self):
        self.assertEqual(win_helper.filetime_to_iso(116444736000000005), "1970-01-01T00:00:00.0000005Z")

    @unittest.skipUnless(ctypes.sizeof(ctypes.c_void_p) == 8, "the layout below is the 64-bit one")
    def test_input_structure_matches_64_bit_windows(self):
        self.assertEqual(ctypes.sizeof(win_helper.INPUT), 40)
        self.assertEqual(ctypes.sizeof(win_helper.KEYBDINPUT), 24)
        self.assertEqual(ctypes.sizeof(win_helper.MOUSEINPUT), 32)
        self.assertEqual(win_helper.INPUT.ki.offset, 8)
        offsets = {name: getattr(win_helper.KEYBDINPUT, name).offset for name, _ in win_helper.KEYBDINPUT._fields_}
        self.assertEqual(offsets, {"wVk": 0, "wScan": 2, "dwFlags": 4, "time": 8, "dwExtraInfo": 16})

    def test_other_structures(self):
        self.assertEqual(ctypes.sizeof(win_helper.RECT), 16)
        self.assertEqual(ctypes.sizeof(win_helper.POINT), 8)
        self.assertEqual(ctypes.sizeof(win_helper.BITMAPINFOHEADER), 40)
        self.assertEqual(ctypes.sizeof(win_helper.LASTINPUTINFO), 8)

    def test_input_flags(self):
        self.assertEqual((win_helper.KEYEVENTF_SCANCODE, win_helper.KEYEVENTF_UNICODE, win_helper.KEYEVENTF_KEYUP),
                         (0x0008, 0x0004, 0x0002))

    def test_text_is_sent_as_utf16_code_units(self):
        self.assertEqual(win_helper.utf16_units("a\u00e9"), [0x61, 0xE9])
        self.assertEqual(win_helper.utf16_units("\U0001F600"), [0xD83D, 0xDE00])

    @unittest.skipIf(sys.platform == "win32", "the refusal is for other platforms")
    def test_the_real_backend_is_not_built_off_windows(self):
        with self.assertRaises(RuntimeError):
            win_helper.make_backend()


class SourceRulesTest(unittest.TestCase):
    """win_helper.py runs alone under the Windows python.exe: no package imports, nothing Windows-only at import."""

    def setUp(self):
        self.source = (ROOT / "game_qa" / "win_helper.py").read_text(encoding="utf-8")
        self.tree = ast.parse(self.source, feature_version=(3, 11))

    def test_imports_nothing_from_the_package(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] if node.level == 0 else ["." * node.level]
            else:
                continue
            for name in names:
                self.assertFalse(name.startswith(("game_qa", ".")), name)

    def test_imports_only_the_standard_library(self):
        stdlib = sys.stdlib_module_names
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertIn(a.name.split(".")[0], stdlib)
            elif isinstance(node, ast.ImportFrom):
                self.assertIn((node.module or "").split(".")[0], stdlib)

    def test_windows_only_calls_live_inside_the_backend_class(self):
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "WindowsBackend":
                continue
            dumped = ast.dump(node)
            for name in ("windll", "WinDLL", "WINFUNCTYPE", "oledll"):
                self.assertNotIn(name, dumped, name)

    def test_no_module_beside_it_shadows_a_standard_one(self):
        # Run as a lone script, game_qa/ is first on sys.path: a sibling named like a stdlib module would win.
        for path in (ROOT / "game_qa").glob("*.py"):
            if path.stem not in ("__init__", "__main__"):
                self.assertNotIn(path.stem, sys.stdlib_module_names, path.name)

    @unittest.skipIf(sys.platform == "win32", "on Windows this would build the real backend")
    def test_it_starts_as_a_lone_script_and_stops_only_for_lack_of_windows(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            done = subprocess.run([sys.executable, str(ROOT / "game_qa" / "win_helper.py")], cwd=elsewhere,
                                  stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("RuntimeError", done.stderr); self.assertNotIn("ImportError", done.stderr)
        self.assertNotIn("ModuleNotFoundError", done.stderr)

    def test_the_backend_class_body_has_no_windows_calls(self):
        cls = next(n for n in self.tree.body if isinstance(n, ast.ClassDef) and n.name == "WindowsBackend")
        for node in cls.body:
            if not isinstance(node, ast.FunctionDef):
                self.assertNotIn("WinDLL", ast.dump(node))


def reply_line(**fields):
    return json.dumps({"ok": True, **fields}).encode("ascii") + b"\n"


class FakePipeIn:
    def __init__(self):
        self.lines, self.closed, self.broken = [], False, False

    def write(self, data):
        if self.broken:
            raise BrokenPipeError("pipe closed")
        self.lines.append(data)
        return len(data)

    def flush(self):
        if self.broken:
            raise BrokenPipeError("pipe closed")

    def close(self):
        self.closed = True


class FakePipeOut:
    def __init__(self, replies):
        self.replies = deque(replies)

    def readline(self):
        return self.replies.popleft() if self.replies else b""


class FakeProc:
    def __init__(self, replies):
        self.stdin, self.stdout = FakePipeIn(), FakePipeOut(replies)
        self.killed = False

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.killed = True


class FakePopen:
    def __init__(self, replies):
        self.proc, self.calls = FakeProc(replies), []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.proc


def fake_wslpath(argv, **kwargs):
    assert argv[:2] == ["wslpath", "-w"], argv
    return subprocess.CompletedProcess(argv, 0, stdout="\\\\wsl.localhost\\Ubuntu" + argv[2].replace("/", "\\") + "\n", stderr="")


class ProcessHelperTest(unittest.TestCase):
    def make(self, *replies):
        self.popen = FakePopen(replies)
        self.ph = helper.ProcessHelper("python.exe", popen=self.popen, run=fake_wslpath)
        return self.ph

    def sent(self):
        return [json.loads(line) for line in self.popen.proc.stdin.lines]

    def test_it_starts_the_script_by_its_windows_path(self):
        ph = self.make(reply_line(python="3.11.9"))
        self.assertEqual(self.popen.calls, [])             # nothing starts until the first call
        self.assertEqual(ph.ping(), "3.11.9")
        argv, kwargs = self.popen.calls[0]
        self.assertEqual(argv[:2], ["python.exe", "-u"])
        self.assertTrue(argv[2].startswith("\\\\wsl.localhost\\Ubuntu\\") and argv[2].endswith("\\game_qa\\win_helper.py"))
        self.assertEqual(kwargs["stdin"], subprocess.PIPE); self.assertEqual(kwargs["stdout"], subprocess.PIPE)
        self.assertFalse(kwargs.get("text") or kwargs.get("universal_newlines"))       # binary pipes: no cp1252, no CRLF

    def test_one_json_line_per_call(self):
        ph = self.make(reply_line(pid=44, created="2026-11-10T12:00:00.0000000Z"), reply_line(foreground=True))
        proc = ph.launch("victoria3.exe", ["-debug_mode", "-script_debugger"], "C:\\g")
        self.assertEqual(proc, ProcId(44, "2026-11-10T12:00:00.0000000Z"))
        self.assertTrue(ph.focus(44))
        raw = self.popen.proc.stdin.lines
        self.assertEqual(len(raw), 2); self.assertTrue(all(line.endswith(b"\n") and line.count(b"\n") == 1 for line in raw))
        first, second = self.sent()
        self.assertEqual((first["op"], first["exe"], first["args"], first["cwd"]),
                         ("launch", "victoria3.exe", ["-debug_mode", "-script_debugger"], "C:\\g"))
        self.assertEqual((second["op"], second["pid"]), ("focus", 44)); self.assertNotEqual(first["id"], second["id"])

    def test_non_ascii_text_stays_ascii_on_the_wire(self):
        ph = self.make(reply_line())
        ph.keys(7, [{"text": 'event "é".1'}, {"scan": 0x1C}])
        raw = self.popen.proc.stdin.lines[0]
        raw.decode("ascii")
        self.assertEqual(self.sent()[0]["steps"], [{"text": 'event "é".1'}, {"scan": 0x1C}])

    def test_an_error_reply_raises_with_its_code(self):
        ph = self.make(json.dumps({"id": 1, "ok": False, "error": "not_foreground", "steps_done": 2}).encode() + b"\n")
        with self.assertRaises(helper.HelperError) as ctx:
            ph.keys(7, [{"scan": 1}])
        self.assertEqual(ctx.exception.code, "not_foreground")

    def test_the_backend_detail_is_kept(self):
        ph = self.make(json.dumps({"ok": False, "error": "backend_error", "detail": "OSError('x')"}).encode() + b"\n")
        with self.assertRaises(helper.HelperError) as ctx:
            ph.focus(7)
        self.assertEqual(ctx.exception.code, "backend_error"); self.assertIn("OSError", str(ctx.exception))

    def test_a_closed_pipe_is_helper_gone(self):
        ph = self.make()
        with self.assertRaises(helper.HelperError) as ctx:
            ph.idle_ms()
        self.assertEqual(ctx.exception.code, "helper_gone")
        with self.assertRaises(helper.HelperError) as again:          # and it stays gone
            ph.idle_ms()
        self.assertEqual(again.exception.code, "helper_gone"); self.assertEqual(len(self.popen.calls), 1)

    def test_a_broken_pipe_on_write_is_helper_gone(self):
        ph = self.make(reply_line(idle_ms=5))
        self.popen.proc.stdin.broken = True
        with self.assertRaises(helper.HelperError) as ctx:
            ph.idle_ms()
        self.assertEqual(ctx.exception.code, "helper_gone")

    def test_garbage_from_the_helper_is_a_bad_reply(self):
        ph = self.make(b"Traceback (most recent call last):\n")
        with self.assertRaises(helper.HelperError) as ctx:
            ph.idle_ms()
        self.assertEqual(ctx.exception.code, "bad_reply")

    def test_window_idle_adopt_kill(self):
        ph = self.make(
            reply_line(exists=True, hwnd=70, title="Victoria 3", foreground=False, responding=True, client=[1, 2, 3, 4]),
            reply_line(idle_ms=61_000), reply_line(), reply_line())
        self.assertEqual(ph.window(7), helper.Window(True, False, True, "Victoria 3", (1, 2, 3, 4)))
        self.assertEqual(ph.idle_ms(), 61_000)
        ph.adopt(ProcId(7, "T")); self.assertIs(ph.kill(ProcId(7, "T")), False)
        sent = self.sent()
        self.assertEqual([s["op"] for s in sent], ["window", "idle_ms", "adopt", "kill"])
        self.assertEqual((sent[2]["pid"], sent[2]["created"]), (7, "T")); self.assertEqual(sent[3]["pid"], 7)

    def test_kill_says_whether_the_process_had_already_exited(self):
        ph = self.make(reply_line(already_exited=True), reply_line(already_exited=False), reply_line())
        self.assertIs(ph.kill(ProcId(7, "T")), True)
        self.assertIs(ph.kill(ProcId(7, "T")), False)
        self.assertIs(ph.kill(ProcId(7, "T")), False)

    def test_screenshot_converts_the_folder_and_asks_for_the_width(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run 1" / "shot.png"
            ph = self.make(reply_line(path="x", width=800, height=450))
            self.assertEqual(ph.screenshot(7, target, max_width=800), target)
            self.assertTrue(target.parent.is_dir())
            req = self.sent()[0]
            self.assertEqual((req["op"], req["pid"], req["max_width"]), ("screenshot", 7, 800))
            self.assertEqual(req["path"], "\\\\wsl.localhost\\Ubuntu" + str(target.parent).replace("/", "\\") + "\\shot.png")

    def test_the_default_width_is_1600(self):
        with tempfile.TemporaryDirectory() as tmp:
            ph = self.make(reply_line(path="x", width=1, height=1))
            ph.screenshot(7, Path(tmp) / "a.png")
            self.assertEqual(self.sent()[0]["max_width"], 1600)

    def test_tcp_carries_bytes_as_base64(self):
        ph = self.make(reply_line(), reply_line(), reply_line(b64=base64.b64encode(b"\x00\xffhi").decode()),
                       reply_line(b64=""), reply_line())
        ph.tcp_open(6111); ph.tcp_send(b"\x01\x02")
        self.assertEqual(ph.tcp_recv(0.5), b"\x00\xffhi"); self.assertEqual(ph.tcp_recv(0.1), b""); ph.tcp_close()
        sent = self.sent()
        self.assertEqual([s["op"] for s in sent], ["tcp_open", "tcp_send", "tcp_recv", "tcp_recv", "tcp_close"])
        self.assertEqual(sent[0]["port"], 6111); self.assertEqual(base64.b64decode(sent[1]["b64"]), b"\x01\x02")
        self.assertEqual((sent[2]["timeout_ms"], sent[3]["timeout_ms"]), (500, 100))

    def test_close_ends_the_helper(self):
        ph = self.make(reply_line(python="3.11"))
        ph.ping(); ph.close()
        self.assertTrue(self.popen.proc.stdin.closed)

    def test_to_windows_path_asks_wslpath(self):
        seen = []

        def run(argv, **kwargs):
            seen.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout="C:\\Users\\me\\a.png\r\n", stderr="")

        self.assertEqual(helper.to_windows_path(Path("/mnt/c/Users/me/a.png"), run=run), "C:\\Users\\me\\a.png")
        self.assertEqual(seen[0][0], ["wslpath", "-w", "/mnt/c/Users/me/a.png"])
        self.assertTrue(seen[0][1].get("check"))


class CountingBytesIO(io.BytesIO):
    def __init__(self):
        super().__init__()
        self.flushes = 0

    def flush(self):
        self.flushes += 1
        super().flush()


class ServeTest(unittest.TestCase):
    def run_helper(self, *lines):
        stdin = io.BytesIO(b"".join(lines))
        stdout = CountingBytesIO()
        win_helper.serve(stdin, stdout, fakes.FakeBackend(), win_helper.State())
        return [json.loads(line) for line in stdout.getvalue().splitlines()], stdout.flushes

    def test_bad_json_is_answered_and_the_loop_goes_on(self):
        out, _ = self.run_helper(b"{not json\n", b'{"id": 2, "op": "ping"}\n', b"\n", b"[1]\n", b'{"id": 3, "op": "nope"}\n')
        self.assertEqual(out[0], {"ok": False, "error": "bad_json"})
        self.assertEqual((out[1]["id"], out[1]["ok"]), (2, True))
        self.assertEqual(out[2]["error"], "bad_request")
        self.assertEqual((out[3]["id"], out[3]["error"]), (3, "unknown_op"))
        self.assertEqual(len(out), 4)

    def test_invalid_utf8_is_bad_json(self):
        out, _ = self.run_helper(b'\xff\xfe{"op": "ping"}\n')
        self.assertEqual(out, [{"ok": False, "error": "bad_json"}])

    def test_it_exits_when_stdin_closes_and_flushes_each_line(self):
        out, flushes = self.run_helper(b'{"id": 1, "op": "ping"}\n', b'{"id": 2, "op": "idle_ms"}\n')
        self.assertEqual([o["id"] for o in out], [1, 2]); self.assertEqual(flushes, 2)

    def test_replies_are_ascii_lines(self):
        stdin = io.BytesIO(b'{"id": 1, "op": "window", "pid": 7}\n')
        stdout = io.BytesIO()
        backend = fakes.FakeBackend(); backend.windows[7]["title"] = "Viktoria \u00e9"
        win_helper.serve(stdin, stdout, backend, win_helper.State())
        stdout.getvalue().decode("ascii")
        self.assertEqual(json.loads(stdout.getvalue())["title"], "Viktoria \u00e9"); self.assertNotIn(b"\r", stdout.getvalue())

    def test_the_socket_is_closed_when_the_loop_ends(self):
        backend, state = fakes.FakeBackend(), win_helper.State()
        win_helper.serve(io.BytesIO(b'{"id": 1, "op": "tcp_open", "port": 6111}\n'), io.BytesIO(), backend, state)
        self.assertTrue(backend.sock.closed); self.assertIsNone(state.sock)

    def test_main_uses_the_streams_and_backend_it_is_given(self):
        stdout = io.BytesIO()
        stdin = type("In", (), {"buffer": io.BytesIO(b'{"id": 9, "op": "ping"}\n')})()
        out = type("Out", (), {"buffer": stdout})()
        win_helper.main(stdin=stdin, stdout=out, backend=fakes.FakeBackend())
        self.assertEqual(json.loads(stdout.getvalue())["id"], 9)


class RealPipeTest(unittest.TestCase):
    """ProcessHelper against a real child process over real pipes: the Linux Python stands in for python.exe
    and runs the helper's own serve loop over a FakeBackend."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)

    def helper_for(self, body):
        script = Path(self.tmp.name) / "stand_in.py"
        script.write_text(body, encoding="utf-8")
        ph = helper.ProcessHelper(sys.executable, run=lambda argv, **kw: subprocess.CompletedProcess(argv, 0, stdout=argv[2] + "\n"),
                                  script=script)
        self.addCleanup(ph.close)
        return ph

    def serving(self):
        return "import sys\nsys.path.insert(0, %r)\nfrom game_qa import fakes, win_helper\nwin_helper.main(backend=fakes.FakeBackend())\n" % str(ROOT)

    def test_round_trip_over_binary_pipes(self):
        ph = self.helper_for(self.serving())
        self.assertRegex(ph.ping(), r"^\d+\.\d+")
        self.assertEqual(ph.window(7), helper.Window(True, True, True, "Victoria 3", (0, 0, 1920, 1080)))
        self.assertFalse(ph.window(8).exists)
        ph.keys(7, [{"text": 'event "\u00e9".1'}, {"scan": 0x1C}])
        with self.assertRaises(helper.HelperError) as ctx:
            ph.kill(ProcId(4242, "T"))
        self.assertEqual(ctx.exception.code, "not_ours")
        proc = ph.launch("victoria3.exe", ["-debug_mode"], "C:\\g")
        self.assertIs(ph.kill(proc), False)

    def test_a_helper_that_exits_is_helper_gone(self):
        ph = self.helper_for("pass\n")
        with self.assertRaises(helper.HelperError) as ctx:
            ph.idle_ms()
        self.assertEqual(ctx.exception.code, "helper_gone")

    def test_a_helper_that_cannot_start_is_helper_gone(self):
        ph = helper.ProcessHelper("no-such-python-4242", run=lambda argv, **kw: subprocess.CompletedProcess(argv, 0, stdout="x\n"))
        with self.assertRaises(helper.HelperError) as ctx:
            ph.ping()
        self.assertEqual(ctx.exception.code, "helper_gone")


class FakeHelperTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.history = Path(self.tmp.name) / "console_history.txt"
        self.game = fakes.FakeHelper(history=self.history)

    def test_it_is_a_helper(self):
        for name in ("launch", "adopt", "window", "idle_ms", "focus", "keys", "click", "presence", "screenshot",
                     "kill", "tcp_open", "tcp_send", "tcp_recv", "tcp_close"):
            self.assertTrue(callable(getattr(self.game, name)), name)

    def test_window_reflects_its_flags(self):
        self.game.foreground = False
        w = self.game.window(7)
        self.assertEqual((w.exists, w.foreground, w.responding), (True, False, True))
        self.game.exists = False
        self.assertFalse(self.game.window(7).exists)

    def test_idle_is_a_plain_value(self):
        self.game.idle = 45_000
        self.assertEqual(self.game.idle_ms(), 45_000)

    def test_focus_counts_and_brings_it_forward(self):
        self.game.foreground = False
        self.assertTrue(self.game.focus(7)); self.assertEqual(self.game.focus_calls, 1); self.assertTrue(self.game.foreground)

    def test_a_refused_focus_stays_back(self):
        self.game.foreground = False; self.game.focus_succeeds = False
        self.assertFalse(self.game.focus(7))

    def test_keys_are_recorded_as_given(self):
        steps = [{"scan": 0x29}, {"text": "a"}, {"wait_ms": 5}]
        self.game.keys(7, steps)
        self.assertEqual(self.game.steps, steps)

    def test_keys_are_refused_when_not_in_front_like_the_real_helper(self):
        self.game.foreground = False
        with self.assertRaises(helper.HelperError) as ctx:
            self.game.keys(7, [{"scan": 0x29}])
        self.assertEqual(ctx.exception.code, "not_foreground"); self.assertEqual(self.game.steps, [])

    def test_newline_text_is_refused_like_the_real_helper(self):
        with self.assertRaises(helper.HelperError) as ctx:
            self.game.keys(7, [{"text": "a\nb"}])
        self.assertEqual(ctx.exception.code, "bad_text"); self.assertEqual(self.game.steps, [])

    def test_enter_writes_the_typed_text_to_the_history_while_the_console_is_open(self):
        self.game.console_open = True
        self.game.keys(7, [{"text": "tag FRA"}, {"scan": 0x1C}, {"text": "tag GBR"}, {"scan": 0x1C}])
        self.assertEqual(self.history.read_text(), "tag FRA\ntag GBR\n")

    def test_a_closed_console_records_nothing(self):
        self.game.console_open = False
        self.game.keys(7, [{"text": "tag FRA"}, {"scan": 0x1C}])
        self.assertFalse(self.history.exists()); self.assertEqual(self.game.typed, "")

    def test_launch_adopt_kill(self):
        proc = self.game.launch("victoria3.exe", ["-a"], "C:\\g")
        self.assertIsInstance(proc, ProcId)
        self.game.adopt(proc); self.assertIs(self.game.kill(proc), False)
        self.assertEqual((self.game.launched, self.game.adopted, self.game.killed),
                         ([("victoria3.exe", ["-a"], "C:\\g")], [proc], [proc]))
        self.assertFalse(self.game.window(proc.pid).exists)
        self.assertIs(self.game.kill(proc), True)               # and once it is gone, killing it says so

    def test_screenshot_writes_a_png(self):
        path = Path(self.tmp.name) / "s" / "a.png"
        self.assertEqual(self.game.screenshot(7, path, max_width=100), path)
        self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_tcp_queue(self):
        self.game.tcp_open(6111); self.game.tcp_send(b"abc"); self.game.tcp_in.append(b"reply")
        self.assertEqual((self.game.tcp_port, self.game.tcp_sent), (6111, [b"abc"]))
        self.assertEqual(self.game.tcp_recv(1.0), b"reply"); self.assertEqual(self.game.tcp_recv(1.0), b"")
        self.game.tcp_close(); self.assertIsNone(self.game.tcp_port)


if __name__ == "__main__":
    unittest.main()
