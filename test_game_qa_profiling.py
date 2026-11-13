"""game_qa/profiling.py: the game's profiling dumps, read back from the run folder (#1700).

Every input is synthetic, built in the shapes the 2026-11-12 sessions logged (docs/audits/late_game_performance.md):
the tick-task CSV's header and frames, the server log's `Processing Tick` and `Pause Toggled` lines, the script dump's
header. No game, no real user-data folder, and no file time compared with the real clock: the copy helpers run on a
fake clock, and file times are set with os.utime.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from game_qa import profiling as p
from game_qa.logtail import GAP_MARKER

TT_HEAD = "\ufeffframe,task,milliseconds,calls,longest_lock\n"
SP_HEAD = "# type, location, time (seconds), call count\n"
SRC = "[jominiapplication.cpp:539]"


def tt_text(rows) -> str:
    """A ticktask_timings.csv: rows of (frame, task, ms, calls)."""
    return TT_HEAD + "".join("%d,%s,%d,%d,0\n" % row for row in rows)


def frames(year, month, day, days):
    """Every frame (four a day) of `days` days from the date."""
    first = p.frame_of(year, month, day)
    return [first + 6 * n for n in range(days * 4)]


def log_line(second: int, text: str) -> str:
    second %= 24 * 3600
    return "[%02d:%02d:%02d]%s: %s" % (second // 3600, second // 60 % 60, second % 60, SRC, text)


def tick(frame: int) -> str:
    return "Processing Tick: " + p.frame_text(frame)


class DatesTest(unittest.TestCase):
    def test_a_frame_is_the_date_in_hours_with_365_day_years(self):
        # tt_A.csv of 2026-11-12: its frame 60719946 is the tick the server log calls 1931.7.2.18
        self.assertEqual(p.frame_of(1931, 7, 2, 18), 60719946)
        self.assertEqual(p.date_of_frame(60719946), (1931, 7, 2, 18))
        self.assertEqual(p.frame_text(p.frame_of(1931, 12, 31)), "1931.12.31")
        self.assertEqual(p.frame_text(p.frame_of(1932, 1, 1) - 6), "1931.12.31.18")
        for frame in frames(1931, 1, 1, 400):
            with self.subTest(frame=frame):
                self.assertEqual(p.frame_of(*p.date_of_frame(frame)), frame)

    def test_frame_kinds(self):
        weekly_day = next(d for d in range(2, 9) if p.day_number(1931, 7, d) % 7 == p.WEEKLY_PHASE)
        self.assertEqual(p.frame_kind(p.frame_of(1931, 7, weekly_day), p.WEEKLY_PHASE), "weekly")
        self.assertEqual(p.frame_kind(p.frame_of(1931, 7, weekly_day + 1), p.WEEKLY_PHASE), "ordinary")
        self.assertEqual(p.frame_kind(p.frame_of(1931, 7, weekly_day, 12), p.WEEKLY_PHASE), "sub")
        first_on_phase = next((y, m) for y in range(1931, 1940) for m in range(1, 13)
                              if p.day_number(y, m, 1) % 7 == p.WEEKLY_PHASE)
        # the 1st is the month's frame whatever the weekday (gaps.py's order)
        self.assertEqual(p.frame_kind(p.frame_of(*first_on_phase, 1), p.WEEKLY_PHASE), "month_start")

    def test_the_console_answers(self):
        self.assertEqual(p.rows_written(["Wrote 7785 rows to C:/Users/x/Documents/Paradox Interactive/Victoria 3/"
                                         "ticktask_timings.csv"]),
                         (7785, "C:/Users/x/Documents/Paradox Interactive/Victoria 3/ticktask_timings.csv"))
        self.assertIsNone(p.rows_written(["Discarded 0 recorded frames"]))
        self.assertTrue(p.names_file(r"C:\Users\x\Victoria 3\TickTask_Timings.CSV", p.TT_FILE))
        self.assertTrue(p.names_file("logs/script_profiling.txt", "script_profiling.txt"))
        self.assertFalse(p.names_file("C:/elsewhere/ticktask_timings.csv.bak", p.TT_FILE))


class TickTasksTest(unittest.TestCase):
    def setUp(self):
        days = frames(1931, 7, 1, 14)
        weekly = [f for f in days if f % 24 == 0 and (f // 24) % 7 == p.WEEKLY_PHASE and p.date_of_frame(f)[2] != 1]
        self.weekly = weekly
        rows = []
        for f in days:
            rows.append((f, "RecalculateModifierNodes", 130 if f % 24 == 0 else 0, 1))
            rows.append((f, "HandleAutonomousInvestment", 1100 if f in weekly else 13, 1))
            if f in weekly:
                rows.append((f, p.WEEKLY_TASK, 110, 1))
            if p.date_of_frame(f)[2] == 1 and f % 24 == 0:
                rows.append((f, "MonthlyPulseJournalEntries", 1060, 1))
        self.text = tt_text(rows)

    def test_rows_read_with_the_bom(self):
        rows = p.parse_tick_tasks(self.text)
        self.assertEqual(rows[0].task, "RecalculateModifierNodes")
        self.assertEqual(rows[0].frame, p.frame_of(1931, 7, 1))

    def test_another_header_or_a_cut_row_is_refused(self):
        with self.assertRaises(p.ProfileError) as caught:
            p.parse_tick_tasks("frame;task\n1;x\n")
        self.assertEqual(caught.exception.code, "bad_tick_tasks")
        with self.assertRaises(p.ProfileError) as caught:
            p.parse_tick_tasks(TT_HEAD + "60719946,MoveArmies,0,1,0\n60719946,MoveFl")
        self.assertEqual(caught.exception.code, "bad_tick_tasks")

    def test_the_weekly_phase_comes_from_the_weekly_task(self):
        rows = p.parse_tick_tasks(self.text)
        self.assertEqual(p.weekly_phase(rows), p.WEEKLY_PHASE)
        shifted = [p.TaskRow(r.frame + 24, r.task, r.ms, r.calls, 0) for r in rows]
        self.assertEqual(p.weekly_phase(shifted), (p.WEEKLY_PHASE + 1) % 7)
        self.assertIsNone(p.weekly_phase([r for r in rows if r.task != p.WEEKLY_TASK]))

    def test_the_summary_splits_by_frame_type(self):
        rows = p.parse_tick_tasks(self.text)
        out = p.tick_tasks(rows, p.WEEKLY_PHASE, top=2)
        self.assertEqual((out["frames"], out["days"]), (56, 14.0))
        self.assertEqual(out["first"], "1931.7.1")
        self.assertEqual(out["last"], "1931.7.14.18")
        self.assertEqual(out["kinds"]["weekly"]["frames"], len(self.weekly))
        self.assertEqual(out["kinds"]["weekly"]["top"][0], {"task": "HandleAutonomousInvestment", "ms_each": 1100})
        self.assertEqual(out["kinds"]["month_start"]["frames"], 1)
        self.assertEqual(out["kinds"]["sub"]["ms_each"], 13)
        self.assertEqual([t["task"] for t in out["top"]], ["HandleAutonomousInvestment", "RecalculateModifierNodes"])
        investment = out["top"][0]
        self.assertEqual(investment["calls"], 56)
        self.assertEqual(investment["ms"], 1100 * len(self.weekly) + 13 * (56 - len(self.weekly)))
        self.assertAlmostEqual(investment["ms_per_day"], investment["ms"] / 14, places=1)


class ServerLogTest(unittest.TestCase):
    def test_lines_become_events(self):
        f = p.frame_of(1931, 7, 1, 6)
        lines = [log_line(100, "Changing game speed to: 4"), log_line(130, "Pause Toggled! Paused: false, PlayerID: 0"),
                 log_line(130, tick(f)), log_line(131, tick(f + 6)), "a line with no stamp",
                 log_line(133, "Pause Toggled! Paused: true, PlayerID: 1"), GAP_MARKER]
        events = p.parse_server_log(lines)
        self.assertEqual([e.kind for e in events], ["speed", "run", "tick", "tick", "pause", "break"])
        self.assertEqual(events[0].value, 4)
        self.assertEqual((events[2].frame, events[2].second), (f, 130))
        self.assertEqual(events[3].frame, f + 6)

    def test_midnight_is_crossed_and_a_clock_step_back_breaks_the_chain(self):
        f = p.frame_of(1931, 7, 1)
        lines = [log_line(86398, tick(f)), log_line(86401, tick(f + 6)),        # 23:59:58, then 00:00:01
                 log_line(86400 + 3, tick(f + 12)), log_line(86400 + 1, tick(f + 18))]  # stepped back 2 s
        events = p.parse_server_log(lines)
        self.assertEqual([e.second for e in events if e.kind == "tick"], [86398, 86401, 86403, 86401])
        self.assertEqual([e.kind for e in events], ["tick", "tick", "tick", "break", "tick"])

    def test_a_tick_with_an_impossible_date_is_skipped(self):
        self.assertEqual(p.parse_server_log([log_line(1, "Processing Tick: 1931.13.1"),
                                             log_line(2, "Processing Tick: 1931.7.1.30")]), [])


class WallClockTest(unittest.TestCase):
    def setUp(self):
        self.first = p.frame_of(1931, 7, 3)
        self.weekly = next(f for f in frames(1931, 7, 3, 8) if f % 24 == 0 and (f // 24) % 7 == p.WEEKLY_PHASE)

    def run_log(self, segments):
        """A log of `segments`: each a list of (frame, seconds that frame takes); a pause after each, 20 s paused."""
        lines, t = [log_line(0, "Changing game speed to: 4")], 10
        for segment in segments:
            lines.append(log_line(t, "Pause Toggled! Paused: false, PlayerID: 0"))
            for frame, cost in segment:
                lines.append(log_line(t, tick(frame)))
                t += cost
            lines.append(log_line(t, "Pause Toggled! Paused: true, PlayerID: 1"))
            t += 20
        return p.parse_server_log(lines)

    def test_a_pause_never_counts_and_a_frame_before_one_is_uncounted(self):
        f = self.first
        events = self.run_log([[(f, 1), (f + 6, 0), (f + 12, 1), (f + 18, 3)],     # 23 s paused after 3 s of it
                               [(f + 24, 1), (f + 30, 0)]])
        out = p.wall_clock(events, (f, f + 30), p.WEEKLY_PHASE)
        # counted: f, f+6, f+12 (1 + 0 + 1) and f+24 (1); f+18's 3 s and f+30 end in a pause
        self.assertEqual(out["gaps"], {"frames": 4, "seconds": 3, "seconds_per_day": 3.0})
        self.assertEqual(out["running"], {"seconds": 6, "ticks": 6, "seconds_per_day": 4.0})
        self.assertEqual(out["kinds"]["sub"]["uncounted"], 2)            # f+18 and f+30: a pause followed each
        self.assertEqual([(s["from"], s["to"], s["ticks"], s["seconds"]) for s in out["segments"]],
                         [("1931.7.3", "1931.7.3.18", 4, 5), ("1931.7.4", "1931.7.4.6", 2, 1)])
        self.assertEqual(out["covered"], {"first": "1931.7.3", "last": "1931.7.4.6", "ticks": 6})
        self.assertEqual(out["speed_before"], 4)
        self.assertNotIn("short_by", out)

    def test_only_the_windows_frames_count(self):
        f = self.first
        events = self.run_log([[(f - 6, 9), (f, 1), (f + 6, 2), (f + 12, 5), (f + 18, 1)]])
        out = p.wall_clock(events, (f, f + 6), p.WEEKLY_PHASE)
        self.assertEqual(out["gaps"]["frames"], 2)                         # f and f+6: f-6's 9 s is not the window's
        self.assertEqual(out["gaps"]["seconds"], 3)
        self.assertEqual(out["covered"]["ticks"], 2)

    def test_a_weekly_frame_is_its_own_kind_and_a_long_gap_is_set_apart(self):
        w = self.weekly
        events = self.run_log([[(w - 6, 0), (w, 4), (w + 6, 0), (w + 12, 70), (w + 18, 0), (w + 24, 0)]])
        out = p.wall_clock(events, (w - 6, w + 24), p.WEEKLY_PHASE)
        self.assertEqual(out["kinds"]["weekly"]["each"], 4.0)
        self.assertEqual(out["long_gaps"], [{"frame": p.frame_text(w + 12), "seconds": 70}])
        self.assertEqual(out["kinds"]["sub"]["uncounted"], 1)              # the long gap's frame

    def test_a_long_gap_is_out_of_running_too(self):
        # #1742 review: the note said a long gap was left out of the wall clock, and `running` still held it
        f = self.first
        lines = [log_line(0, "Pause Toggled! Paused: false, PlayerID: 0"), log_line(1, tick(f)),
                 log_line(1, tick(f + 6)), log_line(301, tick(f + 12)), log_line(301, tick(f + 18)),
                 log_line(302, "Pause Toggled! Paused: true, PlayerID: 1")]
        out = p.wall_clock(p.parse_server_log(lines), (f, f + 18), p.WEEKLY_PHASE)
        self.assertEqual(out["long_gaps"], [{"frame": "1931.7.3.6", "seconds": 300}])
        # cut at f+6, whose frame is the gap's; play resumes at f+12
        self.assertEqual(out["segments"], [
            {"from": "1931.7.3", "to": "1931.7.3.6", "ticks": 1, "seconds": 1, "opened_by": "run",
             "closed_by": "long_gap"},
            {"from": "1931.7.3.12", "to": "1931.7.3.18", "ticks": 2, "seconds": 1, "opened_by": "long_gap",
             "closed_by": "pause"}])
        self.assertEqual(out["running"], {"seconds": 2, "ticks": 3, "seconds_per_day": 2.667})
        self.assertEqual(out["breaks"], 0)

    def test_lines_lost_in_rotation_cut_a_stretch_at_the_tick_before_them(self):
        # #1742 review: the stretch ran on across the gap marker, 600 s for 8 ticks, and nothing said so
        f, g = self.first, self.first + 18 * 24
        lines = [log_line(0, "Pause Toggled! Paused: false, PlayerID: 0")]
        lines += [log_line(1, tick(f + 6 * n)) for n in range(4)] + [GAP_MARKER]
        lines += [log_line(599, tick(g + 6 * n)) for n in range(4)]
        lines += [log_line(600, "Pause Toggled! Paused: true, PlayerID: 1")]
        out = p.wall_clock(p.parse_server_log(lines), (f, g + 18), p.WEEKLY_PHASE)
        self.assertEqual([(s["from"], s["to"], s["ticks"], s["seconds"], s["opened_by"], s["closed_by"])
                          for s in out["segments"]],
                         [("1931.7.3", "1931.7.3.18", 3, 1, "run", "break"),
                          ("1931.7.21", "1931.7.21.18", 4, 1, "break", "pause")])
        self.assertEqual(out["running"], {"seconds": 2, "ticks": 7, "seconds_per_day": 1.143})
        self.assertEqual(out["breaks"], 1)

    def test_a_clock_step_back_cuts_a_stretch_too(self):
        # the pause line's stamp is on the stepped-back clock: across the step it gave -47 s
        f = self.first
        lines = [log_line(100, "Pause Toggled! Paused: false, PlayerID: 0")]
        lines += [log_line(101 + n, tick(f + 6 * n)) for n in range(4)]
        lines += [log_line(50, tick(f + 24)), log_line(51, tick(f + 30)),
                  log_line(53, "Pause Toggled! Paused: true, PlayerID: 1")]
        out = p.wall_clock(p.parse_server_log(lines), (f, f + 30), p.WEEKLY_PHASE)
        self.assertEqual([(s["ticks"], s["seconds"], s["closed_by"]) for s in out["segments"]],
                         [(3, 4, "break"), (2, 3, "pause")])
        self.assertEqual(out["running"], {"seconds": 7, "ticks": 5, "seconds_per_day": 5.6})
        self.assertEqual(out["breaks"], 1)

    def test_ticks_after_a_break_are_play_and_a_break_outside_the_window_is_not_counted(self):
        # the lines lost may hold the run line: the ticks after the break are play from the first of them
        f = self.first
        lines = [GAP_MARKER, log_line(10, tick(f)), log_line(11, tick(f + 6)), log_line(12, tick(f + 12)),
                 log_line(13, "Pause Toggled! Paused: true, PlayerID: 1"), GAP_MARKER]
        out = p.wall_clock(p.parse_server_log(lines), (f, f + 12), p.WEEKLY_PHASE)
        self.assertEqual([(s["ticks"], s["seconds"], s["opened_by"]) for s in out["segments"]], [(3, 3, "break")])
        self.assertEqual(out["running"]["seconds_per_day"], 4.0)
        self.assertEqual(out["breaks"], 0)                  # one before the window's first tick, one after its last

    def test_a_log_that_ends_early_says_by_how_much(self):
        f = self.first
        out = p.wall_clock(self.run_log([[(f, 1), (f + 6, 1)]]), (f, f + 30), p.WEEKLY_PHASE)
        self.assertEqual(out["short_by"], 4)
        empty = p.wall_clock([], (f, f + 30), p.WEEKLY_PHASE)
        self.assertIsNone(empty["covered"])
        self.assertIsNone(empty["running"]["seconds_per_day"])

    def test_a_speed_change_inside_the_window_is_listed(self):
        f = self.first
        lines = [log_line(1, "Pause Toggled! Paused: false, PlayerID: 0"), log_line(1, tick(f)),
                 log_line(2, "Changing game speed to: 3"), log_line(3, tick(f + 6)),
                 log_line(4, "Changing game speed to: 2"), log_line(5, "Pause Toggled! Paused: true, PlayerID: 1")]
        out = p.wall_clock(p.parse_server_log(lines), (f, f + 6), p.WEEKLY_PHASE)
        self.assertEqual(out["speeds"], [{"speed": 3, "after": "1931.7.3"}])   # the second came after the window


class ScriptProfileTest(unittest.TestCase):
    TEXT = (SP_HEAD + "trigger common/scripted_buttons/un_buttons.txt:1296 2.75 1015\n"
            "trigger common/scripted_buttons/un_buttons.txt:506 0.5 1015\n"
            "script_value common/ai_strategies/00_default_strategy.txt:1773 0.6 12203\n"
            "trigger " + p.REFERENCE_LOCATION + " 0.01 4000\n"
            "effect <unknown>:0 0.1 5\n"
            "a line that does not read\n")

    def origin(self, name):
        return {"common/scripted_buttons/un_buttons.txt": "mod"}.get(name, "vanilla" if name.startswith("common/")
                                                                     else "other")

    def test_rows(self):
        rows = p.parse_script_profile(self.TEXT)
        self.assertEqual(rows[("trigger", "common/scripted_buttons/un_buttons.txt:1296")], (2.75, 1015))
        self.assertEqual(len(rows), 5)
        with self.assertRaises(p.ProfileError) as caught:
            p.parse_script_profile("frame,task\n")
        self.assertEqual(caught.exception.code, "bad_script_profile")

    def test_by_file_with_origins_per_day(self):
        out = p.script_by_file(p.parse_script_profile(self.TEXT), self.origin, days=10, top=2)
        self.assertEqual(out["top"][0], {"file": "common/scripted_buttons/un_buttons.txt", "origin": "mod",
                                         "seconds": 3.25, "calls": 2030, "ms_per_day": 325.0})
        self.assertEqual(len(out["top"]), 2)
        self.assertEqual(out["by_origin"]["mod"]["seconds"], 3.25)
        self.assertEqual(out["by_origin"]["vanilla"]["seconds"], 0.61)
        self.assertEqual(out["by_origin"]["other"]["seconds"], 0.1)
        self.assertEqual(out["reference"]["calls"], 4000)
        self.assertEqual(out["reference"]["calls_per_day"], 400.0)
        self.assertEqual(out["counts_fell"], 0)

    def test_the_later_dump_minus_the_earlier(self):
        later = p.parse_script_profile(self.TEXT)
        earlier = {("trigger", "common/scripted_buttons/un_buttons.txt:1296"): (2.0, 1000)}
        out = p.script_by_file(later, self.origin, days=1, since=earlier)
        self.assertEqual(out["top"][0]["seconds"], 1.25)
        self.assertEqual(out["top"][0]["calls"], 1030)
        restarted = {("trigger", "common/scripted_buttons/un_buttons.txt:1296"): (9.0, 5000)}
        self.assertEqual(p.script_by_file(later, self.origin, days=1, since=restarted)["counts_fell"], 1)

    def test_origin_by_root_the_last_loaded_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for where, name in (("variant", "common/a.txt"), ("mod", "common/a.txt"), ("mod", "common/b.txt"),
                                ("game", "common/b.txt"), ("game", "common/c.txt")):
                (root / where / name).parent.mkdir(parents=True, exist_ok=True)
                (root / where / name).write_text("x")
            origin = p.origin_of([("add_mod", root / "variant"), ("mod", root / "mod"), ("vanilla", root / "game")])
            self.assertEqual([origin(n) for n in ("common/a.txt", "common/b.txt", "common/c.txt", "common/d.txt",
                                                  "<unknown>", "../mod/common/a.txt")],
                             ["add_mod", "mod", "vanilla", "other", "other", "other"])


class SummaryTest(unittest.TestCase):
    """`summary` over a run folder the session would leave: steps, tt_/sp_ copies, the server log copy."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.run = Path(tmp.name)
        self.days = frames(1931, 7, 3, 20)       # 80 frames
        self.steps = [{"verb": "profile_start", "outcome": "ok", "date": [1931, 7, 3]}]
        self.second = 10
        self.log: list[str] = []

    def play(self, days, ms=10):
        """The game runs over `days` frames (1 s each) between two pause lines, and the profile's state moves on."""
        self.log.append(log_line(self.second, "Pause Toggled! Paused: false, PlayerID: 0"))
        for f in days:
            self.log.append(log_line(self.second, tick(f)))
            self.second += 1
        self.log.append(log_line(self.second, "Pause Toggled! Paused: true, PlayerID: 1"))
        self.second += 30
        (self.run / p.RUN_SERVER_LOG).write_text("\n".join(self.log) + "\n", encoding="utf-8")

    def dump(self, label, upto, calls):
        """The dump `label`: every frame up to `upto` since the start, and the script counts so far."""
        tt, sp = p.dump_paths(self.run, label)
        tt.write_text(tt_text([(f, "UpdateEmployment", 5, 1) for f in self.days[:upto]]), encoding="utf-8")
        sp.write_text(SP_HEAD + "trigger common/x.txt:1 %g %d\n" % (calls / 1000, calls), encoding="utf-8")
        self.steps.append({"verb": "profile_dump", "outcome": "ok", "label": label})

    def summary(self, *labels):
        return p.summary(self.run, self.steps, labels, lambda name: "mod")

    def test_one_label_is_from_the_profile_start(self):
        self.play(self.days[:40])
        self.dump("A", 40, 1000)
        out = self.summary("A")
        self.assertEqual(out["window"]["from"], "profile start")
        self.assertEqual(out["window"]["start_date"], [1931, 7, 3])
        self.assertEqual((out["window"]["first_frame"], out["window"]["last_frame"]), ("1931.7.3", "1931.7.12.18"))
        self.assertEqual(out["window"]["days"], 10.0)
        self.assertEqual(out["tick_tasks"]["ms"], 200)
        self.assertEqual(out["wall_clock"]["running"]["ticks"], 40)
        self.assertEqual(out["wall_clock"]["running"]["seconds_per_day"], 4.0)
        self.assertEqual(out["script"]["seconds"], 1.0)
        self.assertEqual(out["weekly_phase"]["source"][:7], "default")
        self.assertEqual(out["notes"], [])
        json.dumps(out)                          # the verb prints it

    def test_no_label_is_the_newest_dump_and_two_are_the_window_between(self):
        self.play(self.days[:40])
        self.dump("A", 40, 1000)
        self.play(self.days[40:60])
        self.dump("B", 60, 1500)
        self.assertEqual(self.summary()["window"]["to"], "B")
        out = self.summary("A", "B")
        self.assertEqual(out["window"]["from"], "A")
        self.assertEqual(out["window"]["first_frame"], "1931.7.13")
        self.assertEqual(out["window"]["days"], 5.0)
        self.assertEqual(out["tick_tasks"]["frames"], 20)
        self.assertEqual(out["wall_clock"]["running"]["ticks"], 20)       # only the second stretch of play
        self.assertEqual(out["script"]["top"][0]["calls"], 500)
        self.assertEqual(out["script"]["top"][0]["ms_per_day"], 100.0)

    def test_refusals(self):
        with self.assertRaises(p.ProfileError) as caught:
            p.summary(self.run, [], (), lambda n: "mod")
        self.assertEqual(caught.exception.code, "no_profile")
        with self.assertRaises(p.ProfileError) as caught:
            self.summary()
        self.assertEqual(caught.exception.code, "no_dump")
        self.play(self.days[:40])
        self.dump("A", 40, 1000)
        self.play(self.days[40:60])
        self.dump("B", 60, 1500)
        for labels, code in ((("C",), "no_dump"), (("B", "A"), "bad_label"), (("A", "A"), "bad_label"),
                             (("a/b",), "bad_label"), (("A", "B", "B"), "bad_label")):
            with self.subTest(labels=labels), self.assertRaises(p.ProfileError) as caught:
                self.summary(*labels)
            self.assertEqual(caught.exception.code, code)
        p.dump_paths(self.run, "A")[1].unlink()
        with self.assertRaises(p.ProfileError) as caught:
            self.summary("A")
        self.assertEqual(caught.exception.code, "no_dump")

    def test_a_restart_between_two_dumps_is_refused_and_noted_after(self):
        self.play(self.days[:40])
        self.dump("A", 40, 1000)
        self.steps.append({"verb": "profile_start", "outcome": "ok", "date": [1931, 7, 13]})
        self.days = self.days[40:]
        self.play(self.days[:20])
        self.dump("B", 20, 300)
        with self.assertRaises(p.ProfileError) as caught:
            self.summary("A", "B")
        self.assertEqual(caught.exception.code, "restarted_between")
        out = self.summary("B")
        self.assertEqual(out["window"]["start_date"], [1931, 7, 13])
        self.assertIn("started 2 times", out["notes"][0])

    def test_a_failed_step_does_not_count(self):
        self.steps.append({"verb": "profile_dump", "outcome": "not_written", "label": "X"})
        with self.assertRaises(p.ProfileError) as caught:
            self.summary("X")
        self.assertEqual(caught.exception.code, "no_dump")

    def test_without_the_server_log_the_wall_clock_is_unknown(self):
        self.dump("A", 40, 1000)
        out = self.summary("A")
        self.assertIsNone(out["wall_clock"])
        self.assertIn("no dedicated_server.log", out["notes"][0])

    def test_a_break_and_a_long_gap_are_noted(self):
        # one stretch of play, 1 s a frame, with lines lost after its 20th tick and 191 s between its 30th and 31st
        d = self.days
        lines = [log_line(10, "Pause Toggled! Paused: false, PlayerID: 0")]
        lines += [log_line(10 + n, tick(f)) for n, f in enumerate(d[:20])] + [GAP_MARKER]
        lines += [log_line(100 + n, tick(f)) for n, f in enumerate(d[20:30])]
        lines += [log_line(300 + n, tick(f)) for n, f in enumerate(d[30:40])]
        lines += [log_line(310, "Pause Toggled! Paused: true, PlayerID: 1")]
        (self.run / p.RUN_SERVER_LOG).write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.dump("A", 40, 1000)
        out = self.summary("A")
        self.assertEqual((out["wall_clock"]["breaks"], len(out["wall_clock"]["long_gaps"])), (1, 1))
        self.assertEqual(out["wall_clock"]["running"], {"seconds": 38, "ticks": 38, "seconds_per_day": 4.0})
        self.assertEqual(out["notes"], [
            "1 gaps of 60 s or more between two ticks are left out of the wall clock, with the frame before each",
            "the server log copy breaks 1 times inside the window (lines lost in its rotation, or its clock "
            "stepping back): no time across a break is counted, and the frame before one that cut a stretch of "
            "play is left out of `running`"])


class CopyTest(unittest.TestCase):
    """The dump's copy: the file must be newly written (its own signature against what was there before), then
    held still, then copied whole. Times are set with os.utime and the clock is a fake one."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.source = self.dir / "ticktask_timings.csv"
        self.now = 0.0
        self.on_sleep = None

    def sleep(self, seconds):
        self.now += seconds
        if self.on_sleep is not None:
            self.on_sleep()

    def write(self, text: str, mtime_ns: int) -> None:
        self.source.write_text(text, encoding="utf-8")
        os.utime(self.source, ns=(mtime_ns, mtime_ns))

    def await_written(self, before):
        return p.await_written(self.source, before, self.sleep, lambda: self.now, wait_s=3, settle_s=0.5)

    def test_a_file_that_appeared_is_new(self):
        self.write("rows", 5_000_000_000)
        self.assertEqual(self.await_written(None), (4, 5_000_000_000))

    def test_the_same_signature_is_not_a_new_dump(self):
        self.write("rows", 5_000_000_000)
        with self.assertRaises(p.ProfileError) as caught:
            self.await_written(p.signature(self.source))
        self.assertEqual(caught.exception.code, "not_written")
        self.assertGreaterEqual(self.now, 3)

    def test_a_new_time_with_the_same_size_is_new(self):
        self.write("rows", 5_000_000_000)
        before = p.signature(self.source)
        os.utime(self.source, ns=(6_000_000_000, 6_000_000_000))
        self.assertEqual(self.await_written(before), (4, 6_000_000_000))

    def test_a_file_still_being_written_is_waited_for(self):
        self.write("ro", 5_000_000_000)
        sizes = iter(["rows", "rows and more", "rows and more"])

        def grow():
            text = next(sizes, None)
            if text is not None and text != self.source.read_text("utf-8"):
                self.write(text, 7_000_000_000 + len(text))
        self.on_sleep = grow
        self.assertEqual(self.await_written(None)[0], len("rows and more"))

    def test_a_missing_or_not_regular_file_is_not_written(self):
        with self.assertRaises(p.ProfileError):
            self.await_written(None)
        self.source.mkdir()
        self.assertIsNone(p.signature(self.source))

    def test_the_copy_lands_whole_or_not_at_all(self):
        self.write("frame,task\n", 5_000_000_000)
        written = p.signature(self.source)
        target = self.dir / "run" / "tt_A.csv"
        target.parent.mkdir()
        self.assertEqual(p.copy_written(self.source, target, written), 11)
        self.assertEqual(target.read_text("utf-8"), "frame,task\n")
        with self.assertRaises(p.ProfileError) as caught:
            p.copy_written(self.source, target, written)
        self.assertEqual(caught.exception.code, "label_used")
        other = target.with_name("tt_B.csv")
        os.utime(self.source, ns=(9_000_000_000, 9_000_000_000))       # rewritten since it was judged new
        with self.assertRaises(p.ProfileError) as caught:
            p.copy_written(self.source, other, written)
        self.assertEqual(caught.exception.code, "changed")
        self.assertEqual(sorted(x.name for x in target.parent.iterdir()), ["tt_A.csv"])

    def test_labels(self):
        for good in ("A", "1931_08_02", "base-2"):
            self.assertEqual(p.check_label(good), good)
        for bad in ("", "_x", "a/b", "a.b", "x" * 33, None):
            with self.subTest(label=bad), self.assertRaises(p.ProfileError):
                p.check_label(bad)


if __name__ == "__main__":
    unittest.main()
