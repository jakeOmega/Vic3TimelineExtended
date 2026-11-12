"""Clicks and the presence reading: the helper's `click` and `presence` ops, the `Helper` calls that carry them,
and the fakes that stand in for both.

Nothing here starts a Windows program: `handle` runs over `fakes.FakeBackend`, `ProcessHelper` over a fake `popen`.
(How the console uses the presence reading is in test_game_qa_console.py.)
"""
import inspect
import json
import unittest

from game_qa import fakes, helper, win_helper
from test_game_qa_win_helper import FakePopen, fake_wslpath, reply_line

DOWN, UP = win_helper.MOUSEEVENTF_LEFTDOWN, win_helper.MOUSEEVENTF_LEFTUP


class BackendCase(unittest.TestCase):
    def setUp(self):
        self.backend = fakes.FakeBackend()
        self.state = win_helper.State()
        # The game is adopted, as the session adopts it before anything is sent: input goes to no other process.
        self.assertTrue(self.call("adopt", pid=fakes.GAME_PID, created=fakes.GAME_CREATED)["ok"])

    def call(self, op, **fields):
        return win_helper.handle({"id": 1, "op": op, **fields}, self.backend, self.state)

    def click(self, x, y, pid=7):
        return self.call("click", pid=pid, x=x, y=y)

    def assert_nothing_touched(self):
        self.assertEqual(self.backend.mouse, [])
        self.assertEqual(self.backend.cursor, (640, 360))


class ClickTest(BackendCase):
    def test_a_click_moves_to_the_point_then_presses_and_releases_the_left_button(self):
        out = self.click(300, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(self.backend.mouse, [("move", 300, 200), ("button", DOWN), ("button", UP)])

    def test_the_point_is_in_client_pixels_and_goes_out_in_screen_pixels(self):
        self.backend.windows[7]["client"] = (100, 50, 800, 600)
        self.click(10, 20)
        self.assertEqual(self.backend.mouse[0], ("move", 110, 70))
        self.assertEqual(self.backend.cursor, (110, 70))

    def test_the_cursor_settles_before_the_press_and_the_press_is_held(self):
        self.click(1, 1)
        self.assertEqual(self.backend.slept, [win_helper.CLICK_SETTLE_MS, win_helper.CLICK_HOLD_MS])

    def test_the_window_is_the_one_asked_for(self):
        self.backend.windows[8] = {"hwnd": 80, "title": "other", "responding": True, "client": (500, 500, 100, 100)}
        self.backend.creation[8] = "A"                            # a second process of the helper's own
        self.call("adopt", pid=8, created="A")
        out = self.click(1, 1, pid=8)
        self.assertEqual(out["error"], "not_foreground")          # window 80 is not the one in front
        self.assert_nothing_touched()

    def test_click_refused_when_the_game_is_not_in_front(self):
        self.backend.foreground = 999
        out = self.click(300, 200)
        self.assertEqual(out["error"], "not_foreground")
        self.assertFalse(out["ok"])
        self.assert_nothing_touched()
        self.assertEqual(self.state.helper_cursor, None)

    def test_click_with_no_window_is_not_in_front(self):
        self.backend.windows.clear()
        self.assertEqual(self.click(300, 200)["error"], "not_foreground")
        self.assert_nothing_touched()

    def test_a_zero_handle_is_never_in_front(self):
        self.backend.windows[7]["hwnd"] = 0
        self.backend.foreground = 0
        self.assertEqual(self.click(300, 200)["error"], "not_foreground")
        self.assert_nothing_touched()

    def test_click_outside_the_client_area_is_bad_point(self):
        for x, y in ((-1, 0), (0, -1), (1920, 0), (0, 1080), (5000, 5000), (-50, -50)):
            with self.subTest(x=x, y=y):
                out = self.click(x, y)
                self.assertEqual((out["ok"], out["error"]), (False, "bad_point"))
                self.assert_nothing_touched()

    def test_the_first_and_last_pixel_of_the_client_area_are_inside_it(self):
        self.assertTrue(self.click(0, 0)["ok"])
        self.assertTrue(self.click(1919, 1079)["ok"])

    def test_bad_point_is_measured_in_the_client_area_not_on_the_screen(self):
        self.backend.windows[7]["client"] = (100, 50, 800, 600)
        self.assertEqual(self.click(800, 0)["error"], "bad_point")
        self.assertEqual(self.click(0, 600)["error"], "bad_point")
        self.assertTrue(self.click(799, 599)["ok"])

    def test_an_empty_client_area_has_no_point_in_it(self):
        self.backend.windows[7]["client"] = (0, 0, 0, 0)         # minimized
        self.assertEqual(self.click(0, 0)["error"], "bad_point")

    def test_fields_that_are_missing_or_mistyped_are_bad_requests(self):
        for fields in ({"pid": 7, "y": 1}, {"pid": 7, "x": 1}, {"x": 1, "y": 1}, {"pid": 7, "x": "1", "y": 1},
                       {"pid": 7, "x": 1, "y": 1.5}, {"pid": 7, "x": True, "y": 1}, {"pid": "7", "x": 1, "y": 1}):
            with self.subTest(fields=fields):
                self.assertEqual(self.call("click", **fields)["error"], "bad_request")
                self.assert_nothing_touched()

    def test_the_foreground_is_looked_at_again_after_the_cursor_settles(self):
        # The probe waits 120 ms between the move and the press; a window that takes the front in that time must not
        # get the click.
        self.backend.lose_focus_after_sleep = True
        out = self.click(300, 200)
        self.assertEqual(out["error"], "not_foreground")
        self.assertEqual(self.backend.mouse, [("move", 300, 200)])

    # #1588: the process is proved by its creation time at both looks, so a click never goes to a program that
    # took the game's id (its window where the game's was, in front, under the point).

    def test_a_process_replaced_before_the_click_is_not_ours_and_nothing_moves(self):
        self.backend.creation[7] = fakes.REUSED_CREATED
        out = self.click(300, 200)
        self.assertEqual((out["ok"], out["error"]), (False, "not_ours"))
        self.assert_nothing_touched()
        self.assertEqual(self.state.helper_cursor, None)

    def test_a_process_replaced_while_the_cursor_settles_is_not_pressed(self):
        def dies(ms):
            self.backend.creation[7] = fakes.REUSED_CREATED
        self.backend.on_sleep = dies
        out = self.click(300, 200)
        self.assertEqual(out["error"], "not_ours")
        self.assertEqual(self.backend.mouse, [("move", 300, 200)])          # the cursor moved; no button went down

    def test_a_process_that_exited_while_the_cursor_settles_is_not_pressed(self):
        self.backend.on_sleep = lambda ms: self.backend.creation.pop(7, None)
        self.assertEqual(self.click(300, 200)["error"], "not_ours")
        self.assertEqual(self.backend.mouse, [("move", 300, 200)])

    def test_click_releases_the_button_when_the_press_raises(self):
        self.backend.fail_mouse_on = DOWN
        out = self.click(300, 200)
        self.assertEqual((out["ok"], out["error"]), (False, "backend_error"))
        self.assertIn(("button", UP), self.backend.mouse)

    def test_click_releases_the_button_when_the_hold_is_interrupted(self):
        def interrupted(ms):
            if self.backend.mouse and self.backend.mouse[-1] == ("button", DOWN):
                raise OSError("interrupted")
        self.backend.on_sleep = interrupted
        out = self.click(300, 200)
        self.assertEqual(out["error"], "backend_error")
        self.assertEqual(self.backend.mouse[-2:], [("button", DOWN), ("button", UP)])

    def test_a_failed_move_presses_nothing(self):
        self.backend.fail_move = True
        out = self.click(300, 200)
        self.assertEqual(out["error"], "backend_error")
        self.assertEqual(self.backend.mouse, [])

    def test_the_click_remembers_where_the_cursor_was_put(self):
        self.backend.windows[7]["client"] = (100, 50, 800, 600)
        self.click(10, 20)
        self.assertEqual(self.state.helper_cursor, (110, 70))

    def test_what_is_remembered_is_where_the_cursor_ended_up_not_where_it_was_sent(self):
        # Windows clamps SetCursorPos to the screen, and the presence rule compares exactly. A click whose cursor
        # did not land on its point is refused, but the cursor was moved, so where it went is still remembered.
        self.backend.cursor_clamp = (1000, 1000)
        out = self.click(1500, 900)
        self.assertEqual(out["error"], "cursor_misplaced")
        self.assertEqual(self.backend.cursor, (999, 900))
        self.assertEqual(self.state.helper_cursor, (999, 900))
        self.assertNotIn("button", [event[0] for event in self.backend.mouse])

    def test_a_cursor_moved_by_a_person_while_it_settled_is_cursor_misplaced_and_nothing_is_pressed(self):
        self.backend.on_sleep = lambda ms: setattr(self.backend, "cursor", (1, 1))
        out = self.click(300, 200)
        self.assertEqual((out["ok"], out["error"]), (False, "cursor_misplaced"))
        self.assertEqual(self.backend.mouse, [("move", 300, 200)])

    def test_a_window_that_moved_while_the_cursor_settled_is_bad_point_and_nothing_is_pressed(self):
        def moves(ms):
            self.backend.windows[7]["client"] = (200, 100, 1920, 1080)
        self.backend.on_sleep = moves
        out = self.click(300, 200)
        self.assertEqual((out["ok"], out["error"]), (False, "bad_point"))
        self.assertEqual(self.backend.mouse, [("move", 300, 200)])

    def test_a_window_that_shrank_below_the_point_while_the_cursor_settled_is_bad_point(self):
        def shrinks(ms):
            self.backend.windows[7]["client"] = (0, 0, 200, 200)
        self.backend.on_sleep = shrinks
        self.assertEqual(self.click(300, 200)["error"], "bad_point")
        self.assertEqual(self.backend.mouse, [("move", 300, 200)])

    def test_a_window_covering_the_point_is_covered_and_nothing_is_pressed(self):
        self.backend.covered_by = 999                           # another top-level window is under the cursor
        out = self.click(300, 200)
        self.assertEqual((out["ok"], out["error"]), (False, "covered"))
        self.assertEqual(self.backend.mouse, [("move", 300, 200)])
        self.assertEqual(self.state.helper_cursor, (300, 200))

    def test_a_window_with_nothing_under_the_point_is_covered(self):
        self.backend.covered_by = 0
        self.assertEqual(self.click(300, 200)["error"], "covered")

    def test_the_games_own_window_under_the_point_is_not_covered(self):
        self.assertTrue(self.click(300, 200)["ok"])

    def test_the_window_under_the_point_is_asked_about_at_the_screen_point(self):
        asked = []
        real = self.backend.window_at
        self.backend.windows[7]["client"] = (100, 50, 800, 600)
        self.backend.window_at = lambda x, y: asked.append((x, y)) or real(x, y)
        self.click(10, 20)
        self.assertEqual(asked, [(110, 70)])

    def test_a_client_area_left_of_the_primary_screen_has_negative_screen_pixels(self):
        # The owner's desktop starts at x = -3072.
        self.backend.windows[7]["client"] = (-3072, 0, 3072, 1728)
        self.assertTrue(self.click(10, 20)["ok"])
        self.assertEqual(self.backend.mouse[0], ("move", -3062, 20))
        out = self.call("presence")
        self.assertEqual((out["cursor"], out["helper_cursor"]), ([-3062, 20], [-3062, 20]))
        self.assertEqual(self.click(3072, 0)["error"], "bad_point")
        self.assertEqual(self.click(-1, 0)["error"], "bad_point")
        self.assertTrue(self.click(3071, 1727)["ok"])
        self.assertEqual(self.backend.cursor, (-1, 1727))

    def test_the_cursor_is_remembered_even_when_the_press_fails(self):
        self.backend.fail_mouse_on = DOWN
        self.click(300, 200)
        self.assertEqual(self.state.helper_cursor, (300, 200))

    def test_a_refused_click_leaves_the_remembered_cursor_alone(self):
        self.click(300, 200)
        self.backend.foreground = 999
        self.click(5, 5)
        self.assertEqual(self.state.helper_cursor, (300, 200))

    def test_a_click_is_not_a_persons_input(self):
        self.backend.now = 100_000
        self.backend.last_input = 40_000                         # a person, 60 s ago
        self.assertEqual(self.call("idle_ms")["idle_ms"], 60_000)
        self.click(300, 200)
        self.backend.now = 101_000
        self.assertEqual(self.call("idle_ms")["idle_ms"], 61_000)

    def test_a_person_clicking_just_after_ours_is_seen(self):
        self.click(300, 200)
        self.backend.now += 5_000
        self.backend.last_input = self.backend.now - 1_000
        self.assertEqual(self.call("idle_ms")["idle_ms"], 1_000)


class PresenceTest(BackendCase):
    def test_presence_reports_cursor_foreground_and_the_helpers_own_cursor(self):
        out = self.call("presence")
        self.assertEqual((out["ok"], out["cursor"], out["foreground"], out["helper_cursor"]),
                         (True, [640, 360], 70, None))
        self.click(300, 200)
        out = self.call("presence")
        self.assertEqual((out["cursor"], out["helper_cursor"]), ([300, 200], [300, 200]))
        self.backend.cursor = (5, 6)                             # a person moves the mouse
        out = self.call("presence")
        self.assertEqual((out["cursor"], out["helper_cursor"]), ([5, 6], [300, 200]))

    def test_the_foreground_is_the_window_in_front_whoever_it_is(self):
        self.backend.foreground = 999
        self.assertEqual(self.call("presence")["foreground"], 999)

    def test_a_locked_desktop_has_no_foreground_window(self):
        self.backend.foreground = 0
        self.assertEqual(self.call("presence")["foreground"], 0)

    def test_a_cursor_left_of_the_primary_screen_reads_as_negative(self):
        self.backend.cursor = (-2000, 300)
        self.assertEqual(self.call("presence")["cursor"], [-2000, 300])

    def test_presence_needs_no_window_and_no_pid(self):
        self.backend.windows.clear()
        self.assertTrue(self.call("presence")["ok"])

    def test_presence_sends_no_input(self):
        self.call("presence")
        self.assertEqual((self.backend.mouse, self.backend.sent), ([], []))

    def test_the_reply_is_plain_json(self):
        self.click(300, 200)
        json.dumps(self.call("presence"))

    def test_a_backend_failure_becomes_a_backend_error(self):
        def boom():
            raise OSError("GetCursorPos failed")
        self.backend.cursor_pos = boom
        out = self.call("presence")
        self.assertEqual((out["ok"], out["error"]), (False, "backend_error"))


class TapButtonTest(unittest.TestCase):
    def test_down_then_up_with_the_hold_between(self):
        log = []
        win_helper.tap_button(lambda flags: log.append(("send", flags)), lambda ms: log.append(("sleep", ms)), 60)
        self.assertEqual(log, [("send", DOWN), ("sleep", 60), ("send", UP)])

    def test_the_button_is_released_when_the_press_raises(self):
        log = []

        def send(flags):
            log.append(flags)
            if flags == DOWN:
                raise OSError("SendInput sent 0 of 1 events")
        with self.assertRaises(OSError):
            win_helper.tap_button(send, lambda ms: None, 60)
        self.assertEqual(log, [DOWN, UP])

    def test_the_button_is_released_when_the_wait_raises(self):
        log = []

        def sleep(ms):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            win_helper.tap_button(log.append, sleep, 60)
        self.assertEqual(log, [DOWN, UP])

    def test_the_mouse_flags_are_the_mouse_ones(self):
        self.assertEqual((DOWN, UP, win_helper.INPUT_MOUSE), (0x0002, 0x0004, 0))
        self.assertNotEqual(win_helper.INPUT_MOUSE, win_helper.INPUT_KEYBOARD)


class ProcessHelperTest(unittest.TestCase):
    def make(self, *replies):
        self.popen = FakePopen(replies)
        return helper.ProcessHelper("python.exe", popen=self.popen, run=fake_wslpath)

    def sent(self):
        return [json.loads(line) for line in self.popen.proc.stdin.lines]

    def test_a_click_is_one_json_line(self):
        ph = self.make(reply_line())
        ph.click(7, 120, 340)
        self.assertEqual(self.sent(), [{"id": 1, "op": "click", "pid": 7, "x": 120, "y": 340}])

    def test_a_refused_click_raises_with_the_code(self):
        ph = self.make(json.dumps({"ok": False, "error": "bad_point", "detail": "outside"}).encode() + b"\n")
        with self.assertRaises(helper.HelperError) as ctx:
            ph.click(7, 5000, 5)
        self.assertEqual(ctx.exception.code, "bad_point")

    def test_presence_is_read_into_a_presence(self):
        ph = self.make(reply_line(cursor=[10, 20], foreground=70, helper_cursor=None),
                       reply_line(cursor=[10, 20], foreground=70, helper_cursor=[3, 4]))
        self.assertEqual(ph.presence(), helper.Presence((10, 20), 70, None))
        self.assertEqual(ph.presence(), helper.Presence((10, 20), 70, (3, 4)))
        self.assertEqual(self.sent()[0], {"id": 1, "op": "presence"})

    def test_a_presence_with_negative_coordinates_is_read_as_given(self):
        ph = self.make(reply_line(cursor=[-3062, 20], foreground=70, helper_cursor=[-3062, 20]))
        self.assertEqual(ph.presence(), helper.Presence((-3062, 20), 70, (-3062, 20)))

    def test_a_presence_can_be_compared_and_hashed(self):
        a = helper.Presence((1, 2), 3, None)
        self.assertEqual(a, helper.Presence((1, 2), 3, None))
        self.assertEqual(len({a, helper.Presence((1, 2), 3, None)}), 1)


class FakeHelperTest(unittest.TestCase):
    def setUp(self):
        self.game = fakes.FakeHelper()

    def test_a_click_is_recorded_and_moves_the_cursor(self):
        self.game.client = (100, 50, 800, 600)
        self.game.click(7, 10, 20)
        self.assertEqual(self.game.clicks, [(10, 20)])
        self.assertEqual((self.game.cursor, self.game.helper_cursor), ((110, 70), (110, 70)))

    def test_a_click_is_refused_when_the_game_is_not_in_front_like_the_real_helper(self):
        self.game.foreground = False
        with self.assertRaises(helper.HelperError) as ctx:
            self.game.click(7, 10, 20)
        self.assertEqual(ctx.exception.code, "not_foreground")
        self.assertEqual((self.game.clicks, self.game.cursor, self.game.helper_cursor),
                         ([], (640, 360), None))

    def test_a_click_in_a_client_area_with_a_negative_origin_moves_the_cursor_there(self):
        self.game.client = (-3072, 0, 3072, 1728)
        self.game.click(7, 10, 20)
        self.assertEqual((self.game.cursor, self.game.helper_cursor), ((-3062, 20), (-3062, 20)))

    def test_a_click_outside_the_client_area_is_bad_point(self):
        for x, y in ((-1, 0), (0, 1080), (1920, 5)):
            with self.subTest(x=x, y=y), self.assertRaises(helper.HelperError) as ctx:
                self.game.click(7, x, y)
            self.assertEqual(ctx.exception.code, "bad_point")
        self.assertEqual(self.game.clicks, [])

    def test_a_click_with_no_window_is_not_in_front(self):
        self.game.exists = False
        with self.assertRaises(helper.HelperError) as ctx:
            self.game.click(7, 10, 20)
        self.assertEqual(ctx.exception.code, "not_foreground")

    def test_presence_reads_the_cursor_and_the_window_in_front(self):
        self.assertEqual(self.game.presence(), helper.Presence((640, 360), fakes.GAME_HWND, None))
        self.game.foreground = False
        self.assertEqual(self.game.presence().foreground, self.game.other_hwnd)
        self.assertNotEqual(self.game.other_hwnd, fakes.GAME_HWND)

    def test_a_scripted_cursor_and_foreground_go_one_value_to_a_reading_and_then_hold(self):
        self.game.foreground = False
        self.game.cursor_script.extend([(1, 1), (2, 2)])
        self.game.other_hwnd_script.extend([500, 600])
        readings = [self.game.presence() for _ in range(3)]
        self.assertEqual([(r.cursor, r.foreground) for r in readings], [((1, 1), 500), ((2, 2), 600), ((2, 2), 600)])

    def test_a_hook_sees_each_reading_and_may_move_things_first(self):
        seen = []
        self.game.on_presence = lambda n: (seen.append(n), setattr(self.game, "cursor", (n, n)))
        self.assertEqual(self.game.presence().cursor, (1, 1))
        self.assertEqual(self.game.presence().cursor, (2, 2))
        self.assertEqual((seen, self.game.presence_calls), ([1, 2], 2))

    def test_focus_brings_the_game_into_the_readings(self):
        self.game.foreground = False
        self.game.focus(7)
        self.assertEqual(self.game.presence().foreground, fakes.GAME_HWND)

    def test_the_fake_still_reports_idle_time(self):
        self.game.idle = 45_000
        self.assertEqual(self.game.idle_ms(), 45_000)


class ProtocolTest(unittest.TestCase):
    """Neither helper may lack a call the protocol names, or take other arguments for it."""

    def members(self):
        return {name: inspect.signature(fn) for name, fn in vars(helper.Helper).items()
                if callable(fn) and not name.startswith("_")}

    def test_the_protocol_has_click_and_presence(self):
        self.assertTrue({"click", "presence"} <= set(self.members()))

    def test_both_helpers_take_what_the_protocol_names(self):
        for cls in (helper.ProcessHelper, fakes.FakeHelper):
            for name, sig in self.members().items():
                with self.subTest(cls=cls.__name__, call=name):
                    mine = inspect.signature(getattr(cls, name))
                    self.assertEqual(list(mine.parameters), list(sig.parameters))


class BackendParityTest(unittest.TestCase):
    """The real backend is not run on Linux, so its surface is held to the fake's: what `handle` calls must exist."""

    def public(self, cls):
        return {name: inspect.signature(fn) for name, fn in vars(cls).items()
                if inspect.isfunction(fn) and not name.startswith("_")}

    def test_the_real_backend_has_every_call_the_fake_has_with_the_same_arguments(self):
        real, fake = self.public(win_helper.WindowsBackend), self.public(fakes.FakeBackend)
        for name, sig in fake.items():
            with self.subTest(call=name):
                self.assertIn(name, real)
                self.assertEqual(list(real[name].parameters), list(sig.parameters))

    def test_the_new_calls_are_among_them(self):
        for name in ("set_cursor", "cursor_pos", "send_mouse", "window_at"):
            self.assertIn(name, self.public(win_helper.WindowsBackend))
            self.assertIn(name, self.public(fakes.FakeBackend))


if __name__ == "__main__":
    unittest.main()
