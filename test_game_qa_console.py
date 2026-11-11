"""game_qa/console.py: a console command as a confirmed round trip.

Everything runs against `fakes.FakeHelper`, which imitates what was seen of the
real game: the console key toggles the console, a command entered while it is
open goes into `console_history.txt` at once, and its `debug.log` lines stay in
the game's buffer until a `help ndefines.ngui` pushes them out. The fake's one
clock serves `Console` for both `sleep` and `clock`, so no test really waits.
"""
import tempfile
import unittest
from pathlib import Path

from game_qa import console, fakes, logtail

TEXT = {"text": "tag FRA"}
ENTER = {"scan": 0x1C}
CONSOLE_KEY = {"scan": 0x29}
FLUSH = {"text": "help ndefines.ngui"}


class ConsoleTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.history = Path(self.tmp.name) / "console_history.txt"
        self.log = Path(self.tmp.name) / "debug.log"
        self.game = fakes.FakeHelper(history=self.history, log=self.log)
        self.console = console.Console(self.game, self.game.proc, self.history, logtail.LogFollower(self.log),
                                       sleep=self.game.sleep, clock=self.game.clock)

    def lose_foreground_before_step(self, count, once=False):
        """The game drops to the back just before the step after `count` steps have been sent."""
        def hook(sent):
            if sent == count:
                self.game.foreground = False
                if once:
                    self.game.on_step = None
        self.game.on_step = hook

    def fail_code(self, *args, **kwargs):
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run(*args, **kwargs)
        return e.exception.code


class RoundTripTest(ConsoleTestCase):
    def test_round_trip_returns_the_reply(self):
        self.game.console_open = True
        self.game.on("tag FRA", success=["Now Playing - France"])
        r = self.console.run("tag FRA")
        self.assertEqual((r.ok, r.lines), (True, ["Now Playing - France"]))

    def test_failure_reply(self):
        self.game.console_open = True
        self.game.on("save x", failure=["Command available only for developers."])
        self.assertIs(self.console.run("save x").ok, False)

    def test_newline_is_refused_before_any_key(self):
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("event a\nevent b")
        self.assertEqual(e.exception.code, "bad_text")
        self.assertEqual(self.game.steps, [])

    def test_quotes_and_non_ascii_are_typed_verbatim(self):
        self.game.console_open = True
        self.console.run('event "é".1', reply=False)
        self.assertIn({"text": 'event "é".1'}, self.game.steps)

    def test_a_text_longer_than_clear_line_can_clear_is_refused_before_any_key(self):
        self.game.console_open = True
        self.assertEqual(self.fail_code("x" * (console.CLEAR_BACKSPACES + 1)), "bad_text")
        self.assertEqual(self.game.steps, [])
        self.console.run("x" * console.CLEAR_BACKSPACES, reply=False)           # the longest that is allowed
        self.assertEqual(self.game.steps, [{"text": "x" * console.CLEAR_BACKSPACES}, ENTER])

    def test_game_exit_mid_command_raises_game_gone(self):
        self.game.console_open = True
        self.game.exit_after_steps = 1
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("tag FRA")
        self.assertEqual(e.exception.code, "game_gone")
        self.assertEqual(self.game.clock(), 0.0)            # a window that is gone ends everything at once

    def test_repeated_command_acks_from_the_log(self):
        self.game.console_open = True
        self.game.history_skips_repeats = True
        self.game.on("select_event_option list", success=["No pending events"])
        first = self.console.run("select_event_option list")
        second = self.console.run("select_event_option list")
        self.assertEqual((first.ok, second.ok), (True, True))
        self.assertEqual(second.lines, ["No pending events"])

    def test_blank_and_carriage_return_texts_are_refused_before_any_key(self):
        for text in ("", "   ", "tag\rFRA", "\n"):
            self.assertEqual(self.fail_code(text), "bad_text", repr(text))
        self.assertEqual(self.game.steps, [])

    def test_every_reply_line_comes_back_in_order(self):
        self.game.console_open = True
        self.game.on("event a.1", success=["first", "second"])
        r = self.console.run("event a.1")
        self.assertEqual((r.command, r.ok, r.lines), ("event a.1", True, ["first", "second"]))

    def test_one_failure_among_successes_is_a_failure(self):
        self.game.console_open = True
        self.game.on("event a.1", success=["fine"], failure=["not fine"])
        r = self.console.run("event a.1")
        self.assertIs(r.ok, False)
        self.assertCountEqual(r.lines, ["fine", "not fine"])

    def test_a_command_with_no_reply_line_has_no_verdict(self):
        self.game.console_open = True
        r = self.console.run("tag FRA")
        self.assertEqual((r.ok, r.lines), (None, []))

    def test_without_a_reply_nothing_is_flushed_and_there_is_no_verdict(self):
        self.game.console_open = True
        self.game.on("tag FRA", success=["Now Playing - France"])
        r = self.console.run("tag FRA", reply=False)
        self.assertEqual((r.ok, r.lines), (None, []))
        self.assertEqual(self.game.steps, [TEXT, ENTER])

    def test_the_flush_follows_the_command_when_a_reply_is_wanted(self):
        self.game.console_open = True
        self.console.run("tag FRA")
        self.assertEqual(self.game.steps, [TEXT, ENTER, FLUSH, ENTER])

    def test_the_tail_of_the_last_flush_is_not_the_next_reply(self):
        self.game.console_open = True
        self.game.on("tag FRA", success=["Now Playing - France"])
        self.game.on("tag GBR", failure=["no such tag"])
        self.assertEqual(self.console.run("tag FRA").lines, ["Now Playing - France"])
        r = self.console.run("tag GBR")
        self.assertEqual((r.ok, r.lines), (False, ["no such tag"]))

    def test_the_newest_run_of_the_same_text_is_the_one_answered(self):
        self.game.console_open = True
        self.game.on("tag FRA", success=["old"])
        self.console.run("tag FRA")
        self.game.on("tag FRA", success=["new"])
        self.assertEqual(self.console.run("tag FRA").lines, ["new"])

    def test_lines_of_an_unflushed_command_are_not_the_next_reply(self):
        self.game.console_open = True
        self.game.on("tag FRA", success=["from the first run"])
        self.console.run("tag FRA", reply=False)
        self.game.on("tag FRA", success=["from the second run"])
        self.assertEqual(self.console.run("tag FRA").lines, ["from the second run"])

    def test_script_debug_lines_between_command_and_flush_are_not_reply_lines(self):
        self.game.console_open = True
        self.game.on("event a.1", success=['Executed "a.1"'], script=["events/a.txt:3: TE_QA_PROBE x"])
        self.assertEqual(self.console.run("event a.1").lines, ['Executed "a.1"'])

    def test_no_reply_when_the_log_never_shows_it(self):
        self.game.console_open = True
        self.game.log = None
        self.assertEqual(self.fail_code("tag FRA"), "no_reply")
        self.assertGreaterEqual(self.game.clock(), 30.0)

    def test_the_reply_wait_follows_the_given_timeout(self):
        self.game.console_open = True
        self.game.log = None
        self.assertEqual(self.fail_code("tag FRA", timeout=8.0), "no_reply")
        self.assertAlmostEqual(self.game.clock(), 8.0, delta=console.POLL_S)

    def test_game_exit_while_waiting_for_the_reply_raises_game_gone(self):
        self.game.console_open = True
        self.game.log = None
        self.game.exit_after_steps = 4          # the text, Enter, the flush, Enter
        self.assertEqual(self.fail_code("tag FRA"), "game_gone")
        self.assertEqual(self.game.clock(), 0.0)

    def test_the_flush_command_itself_is_just_run(self):
        self.game.console_open = True
        r = self.console.run(console.FLUSH_COMMAND)
        self.assertEqual((r.ok, r.lines), (None, []))
        self.assertEqual(self.game.steps, [FLUSH, ENTER])


class ForegroundTest(ConsoleTestCase):
    def test_person_at_the_machine_makes_it_wait_then_fail(self):
        self.game.foreground = False
        self.game.idle = 2_000                  # stays 2 s: someone keeps typing
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("tag FRA")
        self.assertEqual(e.exception.code, "not_foreground")
        self.assertEqual(self.game.steps, [])
        self.assertEqual(self.game.focus_calls, 0)
        self.assertGreaterEqual(self.game.clock(), 120.0)

    def test_nobody_at_the_machine_takes_the_foreground_back(self):
        self.game.foreground = False
        self.game.idle = 45_000
        self.game.console_open = True
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.game.focus_calls, 1)

    def test_a_person_who_stops_typing_lets_it_through_after_the_wait(self):
        self.game.foreground = False
        self.game.idle = 2_000
        self.game.console_open = True
        gone_quiet = []

        def sleep(seconds):
            self.game.sleep(seconds)
            if self.game.clock() >= 40.0:
                self.game.idle = 31_000
                gone_quiet.append(True)
        cons = console.Console(self.game, self.game.proc, self.history, logtail.LogFollower(self.log),
                               sleep=sleep, clock=self.game.clock)
        cons.run("tag FRA", reply=False)
        self.assertTrue(gone_quiet)
        self.assertEqual(self.game.focus_calls, 1)
        self.assertGreaterEqual(self.game.clock(), 40.0)
        self.assertLess(self.game.clock(), 60.0)

    def test_a_focus_the_system_refuses_is_not_foreground(self):
        self.game.foreground = False
        self.game.idle = 45_000
        self.game.focus_succeeds = False
        self.assertEqual(self.fail_code("tag FRA"), "not_foreground")
        self.assertEqual((self.game.steps, self.game.focus_calls), ([], 1))

    def test_the_console_key_is_not_sent_to_a_window_behind_a_person(self):
        self.game.foreground = False
        self.game.idle = 2_000
        with self.assertRaises(console.ConsoleError) as e:
            self.console.ensure_open()
        self.assertEqual(e.exception.code, "not_foreground")
        self.assertEqual(self.game.steps, [])

    def test_a_missing_window_is_game_gone_at_once(self):
        self.game.exists = False
        self.assertEqual(self.fail_code("tag FRA"), "game_gone")
        self.assertEqual((self.game.steps, self.game.clock()), ([], 0.0))

    def test_a_window_that_stays_unresponsive_is_game_gone_after_ten_seconds(self):
        self.game.responding = False
        self.assertEqual(self.fail_code("tag FRA"), "game_gone")
        self.assertEqual(self.game.steps, [])
        self.assertGreaterEqual(self.game.clock(), 10.0)
        self.assertLess(self.game.clock(), 15.0)

    def test_a_window_that_recovers_in_time_gets_the_command(self):
        self.game.responding = False
        self.game.console_open = True

        def sleep(seconds):
            self.game.sleep(seconds)
            if self.game.clock() >= 4.0:
                self.game.responding = True
        cons = console.Console(self.game, self.game.proc, self.history, logtail.LogFollower(self.log),
                               sleep=sleep, clock=self.game.clock)
        cons.run("tag FRA", reply=False)
        self.assertEqual(self.game.steps, [TEXT, ENTER])

    def test_losing_the_front_after_the_text_is_not_retyped(self):
        self.game.console_open = True
        self.lose_foreground_before_step(1)     # the text went in; Enter is refused
        self.assertEqual(self.fail_code("tag FRA"), "not_foreground")
        self.assertEqual(self.game.steps, [TEXT])
        self.assertEqual(self.game.focus_calls, 0)

    def test_losing_the_front_before_any_key_goes_back_through_the_wait_once(self):
        self.game.console_open = True
        self.lose_foreground_before_step(0, once=True)
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.game.steps, [TEXT, ENTER])
        self.assertEqual(self.game.focus_calls, 1)

    def test_losing_the_front_again_on_the_retry_is_not_foreground(self):
        self.game.console_open = True
        self.lose_foreground_before_step(0)
        self.assertEqual(self.fail_code("tag FRA"), "not_foreground")
        self.assertEqual(self.game.steps, [])


class ArrivalTest(ConsoleTestCase):
    def test_closed_console_is_opened_and_the_command_retyped(self):
        self.game.console_open = False
        self.game.on("tag FRA", success=["Now Playing - France"])
        self.assertTrue(self.console.run("tag FRA").ok)
        self.assertEqual(self.game.steps.count(CONSOLE_KEY), 1)

    def test_no_ack_after_one_retry(self):
        self.game.console_open = False
        self.game.console_never_opens = True
        self.assertEqual(self.fail_code("tag FRA"), "no_ack")

    def test_a_console_that_will_not_open_is_not_typed_into_again(self):
        self.game.console_open = False
        self.game.console_never_opens = True
        self.fail_code("tag FRA")
        self.assertEqual(self.game.steps.count(TEXT), 1)

    def test_the_command_is_typed_again_only_once(self):
        self.game.console_open = False

        def shut_after_the_probe(sent):
            if sent == 7:                       # text+Enter, probe+Enter, key, probe+Enter: now the retyped text
                self.game.console_open = False
        self.game.on_step = shut_after_the_probe
        self.assertEqual(self.fail_code("tag FRA"), "no_ack")
        self.assertEqual(self.game.steps.count(TEXT), 2)

    def test_a_command_that_did_arrive_is_not_typed_twice_when_only_the_flush_fails(self):
        self.game.console_open = True

        def close_after_the_text(sent):
            if sent == 2:                       # the text and Enter are in; the console shuts before the flush
                self.game.console_open = False
                self.game.on_step = None
        self.game.on_step = close_after_the_text
        self.game.on("tag FRA", success=["Now Playing - France"])
        r = self.console.run("tag FRA")
        self.assertTrue(r.ok)
        self.assertEqual(self.game.steps.count(TEXT), 1)

    def test_a_repeat_the_history_does_write_is_acked_by_it_and_typed_once(self):
        self.game.console_open = True
        self.console.run("tag FRA", reply=False)
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.game.steps, [TEXT, ENTER, TEXT, ENTER])
        self.assertEqual(self.history.read_text(encoding="utf-8"), "tag FRA\ntag FRA\n")

    def test_a_repeat_the_history_will_not_show_is_acked_by_the_log(self):
        self.game.console_open = True
        self.game.history_skips_repeats = True
        self.game.on("tag FRA", success=["Now Playing - France"])
        self.console.run("tag FRA", reply=False)
        self.assertNotIn(FLUSH, self.game.steps)        # a new text needs no flush when no reply is wanted
        r = self.console.run("tag FRA", reply=False)
        self.assertEqual((r.ok, r.lines), (None, []))
        self.assertIn(FLUSH, self.game.steps)           # the repeat did
        self.assertNotIn(CONSOLE_KEY, self.game.steps)
        self.assertLess(self.game.clock(), console.ARRIVAL_S)       # a repeat is not waited for as a new text is

    def test_a_flush_only_vouches_for_the_command_typed_right_before_it(self):
        parsed = [logtail.parse("[12:00:00][console.cpp:1175]: Running console command: " + text)
                  for text in ("tag FRA", console.PROBE_COMMAND, console.FLUSH_COMMAND)]
        self.console._seen = parsed
        self.assertIsNone(self.console._find_reply("tag FRA", adjacent=True))
        self.assertEqual(self.console._find_reply("tag FRA"), [])       # a command known to have run: any later flush
        self.assertEqual(self.console._find_reply(console.PROBE_COMMAND, adjacent=True), [])

    def test_an_older_line_of_the_same_text_is_not_this_commands_proof(self):
        self.game.console_open = True
        self.game.history_skips_repeats = True
        self.console.ensure_open()                      # the probe is in the history now, so it will be a repeat
        self.game.on("tag FRA", success=["old"])
        self.console.run("tag FRA", reply=False)        # its lines wait in the game's buffer
        self.game.console_open = False
        self.game.on("tag FRA", success=["new"])
        r = self.console.run("tag FRA")                 # lost in the closed console; the probe's flush must not
        self.assertEqual(r.lines, ["new"])              # pair with the old line
        self.assertEqual(self.game.steps.count(CONSOLE_KEY), 1)

    def test_a_text_with_non_ascii_characters_is_proved_by_the_log_when_the_history_does_not_show_it(self):
        # The history file's encoding is unverified: if the game writes it in another one the text never turns up
        # there, which must not read as "did not arrive" (that retypes it, and runs it twice).
        self.game.console_open = True
        self.game.history_encoding = "cp1252"
        self.game.on('event "\u00e9".1', success=["Executed"])
        r = self.console.run('event "\u00e9".1')
        self.assertEqual((r.ok, r.lines), (True, ["Executed"]))
        self.assertEqual(self.game.steps.count({"text": 'event "\u00e9".1'}), 1)
        self.assertNotIn(CONSOLE_KEY, self.game.steps)

    def test_a_text_with_non_ascii_characters_that_the_history_does_show_needs_no_flush(self):
        self.game.console_open = True
        self.console.run('event "\u00e9".1', reply=False)
        self.assertEqual(self.game.steps, [{"text": 'event "\u00e9".1'}, ENTER])

    def test_a_repeat_into_a_closed_console_opens_it_and_goes_again(self):
        self.game.console_open = True
        self.game.history_skips_repeats = True
        self.console.run("tag FRA", reply=False)
        self.game.console_open = False
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.game.steps.count(CONSOLE_KEY), 1)
        self.assertTrue(self.game.console_open)

    def test_a_repeat_that_never_arrives_is_no_ack(self):
        self.game.console_open = True
        self.game.history_skips_repeats = True
        self.console.run("tag FRA", reply=False)
        self.game.console_open = False
        self.game.console_never_opens = True
        self.assertEqual(self.fail_code("tag FRA", reply=False), "no_ack")

    def test_a_typing_counts_as_landed_even_when_a_later_one_landed_after_it(self):
        self.history.write_text("tag FRA\nselect_event_option list\n", encoding="utf-8")
        self.assertTrue(self.console._landed(console._Typed("tag FRA", [], False)))
        # a repeat: only the lines gained since the snapshot count
        self.assertFalse(self.console._landed(console._Typed("tag FRA", ["tag FRA"], True)))
        self.assertTrue(self.console._landed(console._Typed("select_event_option list", ["tag FRA"], False)))

    def test_a_history_file_that_does_not_exist_yet_is_empty(self):
        self.assertFalse(self.history.exists())
        self.game.console_open = True
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.history.read_text(encoding="utf-8"), "tag FRA\n")

    def test_the_game_leaving_during_the_arrival_wait_is_game_gone(self):
        self.game.console_open = False
        self.game.exit_after_steps = 2
        self.assertEqual(self.fail_code("tag FRA", reply=False), "game_gone")
        self.assertEqual(self.game.clock(), 0.0)


class EnsureOpenTest(ConsoleTestCase):
    def test_open_console_is_never_toggled(self):
        self.game.console_open = True
        self.console.ensure_open()
        self.assertNotIn(CONSOLE_KEY, self.game.steps)

    def test_a_closed_console_is_toggled_once_and_the_probe_typed_again(self):
        self.game.console_open = False
        self.console.ensure_open()
        self.assertTrue(self.game.console_open)
        self.assertEqual(self.game.steps.count(CONSOLE_KEY), 1)
        self.assertEqual(self.game.steps.count({"text": console.PROBE_COMMAND}), 2)

    def test_an_open_console_stays_open_when_the_history_hides_a_repeated_probe(self):
        self.game.console_open = True
        self.game.history_skips_repeats = True
        self.console.ensure_open()
        self.console.ensure_open()
        self.console.ensure_open()
        self.assertNotIn(CONSOLE_KEY, self.game.steps)
        self.assertTrue(self.game.console_open)

    def test_a_console_that_will_not_open_is_no_ack_after_the_timeout(self):
        self.game.console_open = False
        self.game.console_never_opens = True
        with self.assertRaises(console.ConsoleError) as e:
            self.console.ensure_open()
        self.assertEqual(e.exception.code, "no_ack")
        self.assertGreaterEqual(self.game.clock(), 30.0)
        self.assertLess(self.game.clock(), 60.0)

    def test_the_names_and_numbers_the_spec_fixes(self):
        self.assertEqual(console.PROBE_COMMAND, "select_event_option list")
        self.assertEqual(console.FLUSH_COMMAND, "help ndefines.ngui")
        self.assertEqual((console.SCAN_CONSOLE, console.SCAN_ENTER), (0x29, 0x1C))
        self.assertEqual((console.PERSON_IDLE_MS, console.FOREGROUND_WAIT_S), (30_000, 120.0))


class FakeGameTest(ConsoleTestCase):
    """The fake has to behave like the game, or the tests above prove nothing."""

    def type_command(self, text):
        self.game.keys(7, [{"text": text}, ENTER])

    def test_the_log_lines_stay_in_the_buffer_until_a_flush(self):
        self.game.console_open = True
        self.game.on("tag FRA", success=["Now Playing - France"])
        self.type_command("tag FRA")
        self.assertFalse(self.log.exists() and self.log.read_text(encoding="utf-8"))
        self.type_command(console.FLUSH_COMMAND)
        written = self.log.read_text(encoding="utf-8")
        self.assertIn("[console.cpp:1175]: Running console command: tag FRA\n", written)
        self.assertIn("[console.cpp:1203]: console_success: Now Playing - France\n", written)
        self.assertIn("[console.cpp:1175]: Running console command: help ndefines.ngui\n", written)

    def test_the_tail_of_the_flushs_own_output_stays_in_the_buffer(self):
        self.game.console_open = True
        self.type_command(console.FLUSH_COMMAND)
        self.assertTrue(self.game.unwritten)
        in_file = len(self.log.read_text(encoding="utf-8").splitlines())
        self.assertGreater(in_file, 100)

    def test_the_console_key_toggles_and_a_closed_console_does_nothing(self):
        self.type_command("tag FRA")
        self.assertFalse(self.history.exists())
        self.game.keys(7, [CONSOLE_KEY])
        self.assertTrue(self.game.console_open)
        self.type_command("tag FRA")
        self.assertEqual(self.history.read_text(encoding="utf-8"), "tag FRA\n")
        self.game.keys(7, [CONSOLE_KEY])
        self.assertFalse(self.game.console_open)

    def test_a_console_that_never_opens_ignores_the_key(self):
        self.game.console_never_opens = True
        self.game.keys(7, [CONSOLE_KEY])
        self.assertFalse(self.game.console_open)

    def test_the_history_can_skip_a_repeat_but_the_game_still_runs_it(self):
        self.game.console_open = True
        self.game.history_skips_repeats = True
        self.type_command("tag FRA")
        self.type_command("tag GBR")
        self.type_command("tag FRA")
        self.assertEqual(self.history.read_text(encoding="utf-8"), "tag FRA\ntag GBR\n")
        self.type_command(console.FLUSH_COMMAND)
        written = self.log.read_text(encoding="utf-8")
        self.assertEqual(written.count("Running console command: tag FRA\n"), 2)

    def test_the_window_goes_after_the_given_number_of_steps(self):
        self.game.exit_after_steps = 1
        with self.assertRaises(fakes.HelperError) as e:
            self.type_command("tag FRA")
        self.assertEqual(e.exception.code, "not_foreground")
        self.assertEqual(e.exception.reply, {"steps_done": 1, "chars_sent": 0})
        self.assertFalse(self.game.window(7).exists)

    def test_a_refusal_before_the_first_step_says_nothing_was_sent(self):
        self.game.foreground = False
        with self.assertRaises(fakes.HelperError) as e:
            self.type_command("tag FRA")
        self.assertEqual(e.exception.reply, {"steps_done": 0, "chars_sent": 0})

    def test_latency_delays_the_history_and_a_busy_game_does_not_respond(self):
        self.game.console_open = True
        self.game.latency = 3.0
        self.game.busy_while_late = True
        self.type_command("tag FRA")
        self.assertFalse(self.history.exists())
        self.assertFalse(self.game.window(7).responding)
        self.game.sleep(2.9)
        self.assertFalse(self.history.exists())
        self.game.sleep(0.2)
        self.assertEqual(self.history.read_text(encoding="utf-8"), "tag FRA\n")
        self.assertTrue(self.game.window(7).responding)

    def test_a_game_with_latency_still_responds_when_it_is_not_busy(self):
        self.game.latency = 3.0
        self.type_command("tag FRA")
        self.assertTrue(self.game.window(7).responding)

    def test_a_late_game_takes_its_input_in_order(self):
        self.game.latency = 2.0
        self.game.keys(7, [CONSOLE_KEY])                # opens the console, but 2 s from now
        self.type_command("tag FRA")                    # so this is typed into a closed one, as far as the sender knows
        self.game.sleep(2.0)
        self.assertTrue(self.game.console_open)
        self.assertEqual(self.history.read_text(encoding="utf-8"), "tag FRA\n")

    def test_backspace_takes_a_typed_character_back(self):
        self.game.keys(7, [{"text": "tag"}, {"scan": 0x0E}])
        self.assertEqual(self.game.typed, "ta")

    def test_one_clock_serves_sleep_and_clock(self):
        self.assertEqual(self.game.clock(), 0.0)
        self.game.sleep(2.5)
        self.game.sleep(1.0)
        self.assertEqual(self.game.clock(), 3.5)


class LateArrivalTest(ConsoleTestCase):
    """A game stalled by a monthly pulse takes the Enter seconds late; the command must still run once."""

    def history_lines(self):
        return self.history.read_text(encoding="utf-8").splitlines() if self.history.exists() else []

    def assert_ran_once_on_an_open_console(self):
        self.assertEqual(self.history_lines().count("tag FRA"), 1)
        self.assertEqual(self.game.steps.count(TEXT), 1)
        self.assertNotIn(CONSOLE_KEY, self.game.steps)
        self.assertTrue(self.game.console_open)

    def test_an_enter_2_seconds_late_is_seen_in_the_first_wait(self):
        self.game.console_open = True
        self.game.latency = 2.0
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.game.steps, [TEXT, ENTER])
        self.assert_ran_once_on_an_open_console()

    def test_an_enter_6_seconds_late_is_not_retyped_and_the_console_key_stays_unpressed(self):
        self.game.console_open = True
        self.game.latency = 6.0
        self.console.run("tag FRA", reply=False)
        self.assert_ran_once_on_an_open_console()

    def test_an_enter_6_seconds_late_still_gets_its_reply(self):
        self.game.console_open = True
        self.game.latency = 6.0
        self.game.on("tag FRA", success=["Now Playing - France"])
        r = self.console.run("tag FRA")
        self.assertEqual((r.ok, r.lines), (True, ["Now Playing - France"]))
        self.assert_ran_once_on_an_open_console()

    def test_an_enter_6_seconds_late_in_a_window_that_stops_responding_is_waited_for(self):
        self.game.console_open = True
        self.game.latency = 6.0
        self.game.busy_while_late = True
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.game.steps, [TEXT, ENTER])
        self.assert_ran_once_on_an_open_console()

    def test_an_enter_8_seconds_late_in_a_window_that_stops_responding_is_waited_for(self):
        self.game.console_open = True
        self.game.latency = 8.0
        self.game.busy_while_late = True
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.game.steps, [TEXT, ENTER])        # no probe: the first wait simply held its clock
        self.assert_ran_once_on_an_open_console()

    def test_an_enter_8_seconds_late_in_a_busy_window_still_gets_its_reply(self):
        self.game.console_open = True
        self.game.latency = 8.0
        self.game.busy_while_late = True
        self.game.on("tag FRA", success=["Now Playing - France"])
        r = self.console.run("tag FRA")
        self.assertEqual((r.ok, r.lines), (True, ["Now Playing - France"]))
        self.assert_ran_once_on_an_open_console()

    def test_the_wait_holds_its_clock_only_up_to_ten_seconds_of_not_responding(self):
        self.game.console_open = True
        self.game.latency = 12.0
        self.game.busy_while_late = True
        self.assertEqual(self.fail_code("tag FRA", reply=False), "game_gone")
        self.assertEqual(self.game.steps, [TEXT, ENTER])
        self.assertGreaterEqual(self.game.clock(), 10.0)
        self.assertLess(self.game.clock(), 12.0)

    def test_a_late_probe_in_a_busy_window_leaves_an_open_console_alone(self):
        self.game.console_open = True
        self.game.latency = 8.0
        self.game.busy_while_late = True
        self.console.ensure_open()
        self.assertNotIn(CONSOLE_KEY, self.game.steps)
        self.assertTrue(self.game.console_open)

    def test_a_probe_4_or_5_and_a_half_seconds_late_in_a_responsive_window_leaves_an_open_console_alone(self):
        for latency in (4.0, 5.5):
            with self.subTest(latency=latency):
                self.history.unlink(missing_ok=True)
                self.game.steps.clear()
                self.game.console_open = True
                self.game.latency = latency
                self.console.ensure_open()
                self.assertEqual(self.game.steps, [{"text": console.PROBE_COMMAND}, ENTER])
                self.assertEqual(self.history_lines(), [console.PROBE_COMMAND])
                self.assertTrue(self.game.console_open)

    def test_a_late_repeat_is_found_by_the_log_and_not_retyped(self):
        self.game.console_open = True
        self.game.history_skips_repeats = True
        self.console.run("tag FRA", reply=False)
        self.game.latency = 6.0
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.game.steps.count(TEXT), 2)        # once a run
        self.assertNotIn(CONSOLE_KEY, self.game.steps)
        self.assertTrue(self.game.console_open)

    def test_a_late_command_next_to_a_probe_before_its_flush_still_gets_its_own_reply(self):
        self.game.console_open = True
        self.game.latency = 6.0
        self.game.on("tag FRA", success=["mine"])
        self.assertEqual(self.console.run("tag FRA").lines, ["mine"])


class StrandedTextTest(ConsoleTestCase):
    def strand(self):
        """Text goes in, Enter is refused: the console keeps half a command."""
        self.game.console_open = True
        self.lose_foreground_before_step(1, once=True)
        self.assertEqual(self.fail_code("event france.1", reply=False), "not_foreground")
        self.game.foreground = True
        self.game.steps.clear()

    def test_the_next_call_refuses_rather_than_glue_onto_the_half_command(self):
        self.strand()
        self.assertEqual(self.fail_code("tag GBR", reply=False), "stranded_text")
        with self.assertRaises(console.ConsoleError) as e:
            self.console.ensure_open()
        self.assertEqual(e.exception.code, "stranded_text")
        self.assertEqual(self.game.steps, [])
        self.assertFalse(self.history.exists())

    def test_clear_line_empties_the_line_and_lets_the_next_call_through(self):
        self.strand()
        self.assertEqual(self.game.typed, "event france.1")
        self.console.clear_line()
        self.assertEqual(self.game.steps, [{"scan": 0x0E}] * 64)
        self.assertEqual(self.game.typed, "")
        self.console.run("tag GBR", reply=False)
        self.assertEqual(self.history.read_text(encoding="utf-8"), "tag GBR\n")

    def test_nothing_clears_the_line_by_itself(self):
        self.strand()
        self.assertEqual(self.fail_code("tag GBR"), "stranded_text")
        self.assertNotIn({"scan": 0x0E}, self.game.steps)
        self.assertEqual(self.game.typed, "event france.1")

    def test_clear_line_checks_the_foreground_first(self):
        self.strand()
        self.game.foreground = False
        self.game.idle = 2_000
        with self.assertRaises(console.ConsoleError) as e:
            self.console.clear_line()
        self.assertEqual(e.exception.code, "not_foreground")
        self.assertEqual(self.game.steps, [])
        self.assertEqual(self.fail_code("tag GBR"), "stranded_text")      # still not cleared

    def test_a_refusal_that_sent_nothing_does_not_strand(self):
        self.game.console_open = True
        self.lose_foreground_before_step(0, once=True)
        self.console.run("tag FRA", reply=False)
        self.console.run("tag GBR", reply=False)
        self.assertEqual(self.history.read_text(encoding="utf-8"), "tag FRA\ntag GBR\n")


class HelperErrorMidTextTest(ConsoleTestCase):
    """A helper error that is not a refusal to start: some of the text may be in the line."""

    def fail_after_three_characters(self, code="backend_error"):
        def keys(pid, steps):
            self.game.steps.append(steps[0])
            self.game.typed += steps[0].get("text", "")[:3]
            raise console.HelperError(code, "OSError('SendInput sent 0 of 1 events')")
        self.game.keys = keys

    def test_a_backend_error_after_some_of_the_text_strands_it(self):
        self.game.console_open = True
        self.fail_after_three_characters()
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("event france.1", reply=False)
        self.assertEqual(e.exception.code, "helper: backend_error")
        self.assertEqual(self.game.typed, "eve")
        del self.game.keys                              # the helper works again
        self.assertEqual(self.fail_code("tag GBR", reply=False), "stranded_text")
        self.assertFalse(self.history.exists())         # not "evetag GBR"
        self.console.clear_line()
        self.assertEqual(self.game.typed, "")
        self.console.run("tag GBR", reply=False)
        self.assertEqual(self.history.read_text(encoding="utf-8"), "tag GBR\n")

    def test_a_refusal_of_the_text_itself_strands_nothing(self):
        self.game.console_open = True
        self.fail_after_three_characters("bad_text")
        self.assertEqual(self.fail_code("tag FRA", reply=False), "bad_text")
        del self.game.keys
        self.console.run("tag GBR", reply=False)

    def test_a_backend_error_in_a_key_press_strands_nothing(self):
        # Only text can leave half a command in the line.
        self.game.console_open = True
        self.game.keys = lambda pid, steps: (_ for _ in ()).throw(console.HelperError("backend_error", "boom"))
        with self.assertRaises(console.ConsoleError):
            self.console.clear_line()
        del self.game.keys
        self.console.run("tag GBR", reply=False)


class EnteredFlagTest(ConsoleTestCase):
    def test_it_defaults_to_false(self):
        self.assertIs(console.ConsoleError("no_ack").entered, False)

    def test_it_can_be_unknown(self):
        self.assertIsNone(console.ConsoleError("log_gap", entered=None).entered)

    def test_a_command_that_never_arrived_is_not_entered(self):
        self.game.console_open = False
        self.game.console_never_opens = True
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("tag FRA")
        self.assertEqual((e.exception.code, e.exception.entered), ("no_ack", False))

    def test_refusing_bad_text_is_not_entered(self):
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("a\nb")
        self.assertIs(e.exception.entered, False)

    def test_no_reply_is_entered(self):
        self.game.console_open = True
        self.game.log = None
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("tag FRA")
        self.assertEqual((e.exception.code, e.exception.entered), ("no_reply", True))

    def test_a_refusal_during_the_flush_is_entered(self):
        self.game.console_open = True
        self.lose_foreground_before_step(3)             # the flush's text is in; its Enter is refused
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("tag FRA")
        self.assertEqual((e.exception.code, e.exception.entered), ("not_foreground", True))

    def test_the_game_leaving_while_waiting_for_the_reply_is_entered(self):
        self.game.console_open = True
        self.game.log = None
        self.game.exit_after_steps = 4
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("tag FRA")
        self.assertEqual((e.exception.code, e.exception.entered), ("game_gone", True))

    def test_a_refusal_after_the_text_but_before_it_arrived_is_not_entered(self):
        self.game.console_open = True
        self.lose_foreground_before_step(1)
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("tag FRA")
        self.assertIs(e.exception.entered, False)


class FlakyPath:
    """Stands in for the history path: the numbered reads fail the way a file held open by the game can."""

    def __init__(self, path, fail_reads):
        self.path, self.fail_reads, self.reads = Path(path), set(fail_reads), 0

    def read_bytes(self):
        self.reads += 1
        if self.reads in self.fail_reads:
            raise PermissionError("sharing violation")
        return self.path.read_bytes()


class HistoryReadTest(ConsoleTestCase):
    def test_a_history_that_cannot_be_read_is_not_an_empty_one(self):
        self.console._history_path = FlakyPath(self.history, range(1, 100))
        self.game.console_open = True
        self.assertEqual(self.fail_code("tag FRA"), "history_unreadable")
        self.assertEqual(self.game.steps, [])

    def test_the_read_is_tried_again_a_few_times_with_the_injected_sleep(self):
        flaky = FlakyPath(self.history, [1, 2])
        self.console._history_path = flaky
        self.game.console_open = True
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.game.steps, [TEXT, ENTER])
        self.assertGreater(self.game.clock(), 0.0)
        self.assertLess(self.game.clock(), 1.0)

    def test_a_failed_read_while_waiting_for_the_arrival_is_not_an_arrival_or_an_error(self):
        flaky = FlakyPath(self.history, [2, 3])          # read 1 is the snapshot before typing
        self.console._history_path = flaky
        self.game.console_open = True
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.game.steps, [TEXT, ENTER])

    def test_a_history_that_does_not_exist_yet_is_still_empty(self):
        self.console._history_path = FlakyPath(self.history, [])
        self.game.console_open = True
        self.console.run("tag FRA", reply=False)
        self.assertEqual(self.history.read_text(encoding="utf-8"), "tag FRA\n")


class LogGapTest(ConsoleTestCase):
    def test_lost_log_lines_during_the_reply_wait_are_log_gap_not_a_reply(self):
        self.game.console_open = True
        self.game.on("tag FRA", success=["Now Playing - France"])

        def lose_lines_before_the_flush(sent):
            if sent == 2:
                with open(self.log, "a", encoding="utf-8") as f:
                    f.write(logtail.GAP_MARKER + "\n")
                self.game.on_step = None
        self.game.on_step = lose_lines_before_the_flush
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("tag FRA")
        self.assertEqual((e.exception.code, e.exception.entered), ("log_gap", True))

    def test_lost_lines_seen_while_looking_for_a_late_reply_are_log_gap_not_a_reply(self):
        # A text the history will not show again, in a game 6 s slow: the reply is found by the late-arrival check.
        self.game.console_open = True
        self.game.history_skips_repeats = True
        self.game.on("event x.1", success=["first line"], failure=["the failure that gets lost"])
        self.console.run("event x.1", reply=False)
        real_run = self.game._run

        def run_and_lose_a_line(text):
            real_run(text)
            if text == "event x.1":                 # the command, its first reply line, the loss, the rest
                at = max(i for i, line in enumerate(self.game.unwritten) if line.endswith("command: event x.1"))
                self.game.unwritten[at + 2:at + 3] = [logtail.GAP_MARKER]
        self.game._run = run_and_lose_a_line
        self.game.latency = 6.0
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("event x.1")
        self.assertEqual(e.exception.code, "log_gap")

    def test_lost_lines_before_the_command_has_any_proof_leave_it_unknown_whether_it_was_entered(self):
        # entered=False would invite a retry of a command that may have run; None says: do not.
        self.game.console_open = True
        self.game.history_skips_repeats = True
        self.console.run("tag FRA", reply=False)

        def lose_lines_after_the_second_typing(sent):
            if sent == 4:
                with open(self.log, "a", encoding="utf-8") as f:
                    f.write(logtail.GAP_MARKER + "\n")
                self.game.on_step = None
        self.game.on_step = lose_lines_after_the_second_typing
        with self.assertRaises(console.ConsoleError) as e:
            self.console.run("tag FRA", reply=False)
        self.assertEqual(e.exception.code, "log_gap")
        self.assertIsNone(e.exception.entered)

    def test_a_gap_from_before_the_call_is_no_gap(self):
        self.game.console_open = True
        self.log.write_text(logtail.GAP_MARKER + "\n", encoding="utf-8")
        self.game.on("tag FRA", success=["Now Playing - France"])
        self.assertEqual(self.console.run("tag FRA").lines, ["Now Playing - France"])


class HelperErrorTest(ConsoleTestCase):
    def boom(self, *args, **kwargs):
        raise console.HelperError("helper_gone", "the helper has ended")

    def assert_wrapped(self, call):
        with self.assertRaises(console.ConsoleError) as e:
            call()
        self.assertEqual(e.exception.code, "helper: helper_gone")
        self.assertIsInstance(e.exception.__cause__, console.HelperError)

    def test_keys(self):
        self.game.keys = self.boom
        self.assert_wrapped(lambda: self.console.run("tag FRA"))

    def test_window(self):
        self.game.window = self.boom
        self.assert_wrapped(lambda: self.console.run("tag FRA"))

    def test_idle_and_focus(self):
        self.game.foreground = False
        self.game.idle_ms = self.boom
        self.assert_wrapped(lambda: self.console.run("tag FRA"))
        self.game.idle_ms = lambda: 45_000
        self.game.focus = self.boom
        self.assert_wrapped(lambda: self.console.run("tag FRA"))

    def test_clear_line_and_ensure_open(self):
        self.game.keys = self.boom
        self.assert_wrapped(self.console.clear_line)
        self.assert_wrapped(self.console.ensure_open)


if __name__ == "__main__":
    unittest.main()
