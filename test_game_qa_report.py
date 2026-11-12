"""game_qa/report.py: the run folder's step log and its summary."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from game_qa import report


class ReportTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.run_dir = Path(tmp.name) / "runs" / "20261110T150000Z"
        self.times = iter(dt.datetime(2026, 11, 10, 15, 0, s, tzinfo=dt.timezone.utc) for s in range(60))
        self.report = report.Report(self.run_dir, now=lambda: next(self.times))

    def summary(self, restore, outcome):
        return {"restore": restore, "outcome": outcome, "permission": "the owner granted launches for this session",
                "snapshot": "20261110T150000Z", "save": "te_qa_fixture_0123456789ab", "country": "FRA"}

    def test_steps_are_appended_and_the_summary_leads_with_the_restore(self):
        self.report.step("start", outcome="ok", snapshot="20261110T150000Z")
        self.report.step("read", outcome="no_stop", exprs=["c:FRA.gdp"])
        lines = (self.run_dir / "steps.jsonl").read_text("utf-8").splitlines()
        self.assertEqual([json.loads(line) for line in lines], [
            {"time": "2026-11-10T15:00:00Z", "verb": "start", "outcome": "ok", "snapshot": "20261110T150000Z"},
            {"time": "2026-11-10T15:00:01Z", "verb": "read", "outcome": "no_stop", "exprs": ["c:FRA.gdp"]},
        ])
        path = self.report.close(self.summary({"restored": [], "removed": [], "held": True,
                                               "reason": "other_game_ran"}, "held"))
        self.assertEqual(path, self.run_dir / "summary.md")
        text = path.read_text("utf-8")
        first = text.split("\n")[0]
        self.assertTrue(first.startswith("Restore: HELD (other_game_ran)"), first)
        self.assertIn("only the owner", first)
        head = text.split("| #")[0]
        for needle in ("the owner granted launches for this session", "20261110T150000Z",
                       "te_qa_fixture_0123456789ab", "FRA"):
            self.assertIn(needle, head)
        self.assertIn("| 1 | start | ok |", text)
        self.assertIn("| 2 | read | no_stop |", text)

    def test_a_restored_run_a_refused_one_and_one_with_no_snapshot_say_so(self):
        cases = (
            ({"restored": ["a", "b"], "removed": ["c"], "held": False, "reason": ""}, "restored",
             "Restore: restored (2 files put back, 1 removed)"),
            ({"held": False, "refused": "game_still_up", "detail": "the game is running"}, "refused",
             "Restore: REFUSED (game_still_up)"),
            (None, None, "Restore: not run"),
        )
        for restore, outcome, start in cases:
            with self.subTest(outcome=outcome):
                first = self.report.close(self.summary(restore, outcome)).read_text("utf-8").split("\n")[0]
                self.assertTrue(first.startswith(start), first)

    def test_a_hold_says_whether_the_owners_playset_was_put_back(self):
        put_back = {"restored": ["content_load.json"], "removed": [], "held": True, "reason": "other_game_ran",
                    "playset_restored": True}
        left = {"restored": [], "removed": [], "held": True, "reason": "other_game_running", "playset_left": True}
        first = self.report.close(self.summary(put_back, "held")).read_text("utf-8").split("\n")[0]
        self.assertTrue(first.startswith("Restore: HELD (other_game_ran)"), first)
        self.assertIn("content_load.json was put back", first)        # the playset: the game starts as before
        self.assertNotIn("Nothing was put back", first)
        first = self.report.close(self.summary(left, "held")).read_text("utf-8").split("\n")[0]
        self.assertIn("Nothing was put back", first)
        self.assertIn("run's playset is still in place", first)

    def test_a_hold_that_put_files_back_never_says_nothing_was(self):
        # N8: part 1 can put files back and then hold for the rest
        partial = {"restored": ["continue_game.json", "pdx_settings.json"], "removed": ["save games/autosave.v3"],
                   "held": True, "reason": "file_changed", "playset_left": True}
        first = self.report.close(self.summary(partial, "held")).read_text("utf-8").split("\n")[0]
        self.assertTrue(first.startswith("Restore: HELD (file_changed)"), first)
        self.assertNotIn("Nothing was put back", first)
        self.assertIn("2 files were put back and 1 removed before the hold", first)
        self.assertIn("run's playset is still in place", first)
        both = dict(partial, playset_restored=True, playset_left=False,
                    restored=["content_load.json", "continue_game.json"])
        first = self.report.close(self.summary(both, "held")).read_text("utf-8").split("\n")[0]
        self.assertIn("content_load.json was put back", first)
        self.assertIn("2 files put back and 1 removed in all", first)

    def test_a_game_left_up_says_restore_was_not_run_and_how_to_finish(self):
        summary = dict(self.summary(None, "game_left_up"), overlay_removed=False,
                       overlay_kept="the game may still be up, and the run's playset names the overlay")
        text = self.report.close(summary).read_text("utf-8")
        first = text.split("\n")[0]
        self.assertTrue(first.startswith("Restore: NOT RUN"), first)
        self.assertIn("python3 -m game_qa restore 20261110T150000Z", first)
        self.assertIn("once no game is running", first)
        self.assertIn("- Overlay kept: the game may still be up", text)
        # the stop's own `next`, when it gives one, is what the line says (recover, `stop` again, ...)
        told = "once no Victoria 3 process runs: `python3 -m game_qa recover`, then `python3 -m game_qa remove-overlay`"
        first = self.report.close(dict(summary, next=told)).read_text("utf-8").split("\n")[0]
        self.assertTrue(first.endswith("Next: " + told), first)
        self.assertNotIn("restore 20261110T150000Z", first)
        refused = self.report.close(dict(self.summary({"held": False, "refused": "game_still_up"}, "refused"),
                                         next="`python3 -m game_qa stop` again")).read_text("utf-8")
        self.assertIn("Next: `python3 -m game_qa stop` again", refused.split("\n")[0])

    def test_the_self_checks_are_listed_before_the_steps_in_the_order_given(self):
        # #1601: `selfchecks.of_run` orders them, every BROKEN first; the summary keeps that order
        found = {"run": "20261110T150000Z", "broken": ["unemployment_share_read"],
                 "counts": {"OK": 2, "BROKEN": 1, "START": 1, "ODD": 1},
                 "checks": [
                     {"name": "unemployment_share_read", "verdict": "BROKEN", "source": "fixture",
                      "line": "common/scripted_effects/te_unemployment_effects.txt:110: TE_SELF_CHECK BROKEN "
                              "unemployment_share_read state=Corsica | read=0.000"},
                     {"name": "cm_census_yearly", "verdict": "START", "source": "session",
                      "line": "common/x.txt:1: TE_SELF_CHECK START cm_census_yearly"},
                     {"name": "primate_state_flag", "verdict": "OK", "source": "fixture",
                      "line": "common/x.txt:2: TE_SELF_CHECK OK primate_state_flag tag=GBR"},
                     {"name": "ch_board_rows", "verdict": "OK", "source": "session",
                      "line": "common/x.txt:3: TE_SELF_CHECK OK ch_board_rows ranked=70"},
                     {"name": "odd_one", "verdict": "ODD", "source": "session", "line": "TE_SELF_CHECK ODD odd_one"}],
                 "fixture": {"key": "0123456789ab", "kept": True, "file": "/backups/fixtures/0123456789ab/lines.log",
                             "snapshot": "20261110T145500Z", "kept_at": "2026-11-10T14:56:00Z", "lines": 114,
                             "self_checks": 11},
                 "session": {"file": "/backups/runs/20261110T150000Z/debug.log", "lines": 4, "gaps": 2}}
        self.report.step("start", outcome="ok")
        restored = {"restored": ["a"], "removed": [], "held": False, "reason": ""}
        text = self.report.close(dict(self.summary(restored, "restored"), self_checks=found)).read_text("utf-8")
        self.assertTrue(text.startswith("Restore: restored"), text[:60])
        head, section = text.split("## Self-checks")
        section, steps = section.split("| # | Verb | Outcome |")
        self.assertIn("- Country: FRA", head)
        self.assertIn("| 1 | start | ok |", steps)
        self.assertIn("1 BROKEN, 1 START (no verdict was logged after it), 2 OK, 1 ODD.", section)
        self.assertIn("- Session: 4 TE_SELF_CHECK lines in /backups/runs/20261110T150000Z/debug.log; lines were lost "
                      "to the log's rotation (2 times), and a verdict logged then is not here.", section)
        self.assertIn("- The run that made the fixture: 114 lines kept from snapshot 20261110T145500Z, 11 of them "
                      "TE_SELF_CHECK (/backups/fixtures/0123456789ab/lines.log).", section)
        rows = [line for line in section.splitlines() if line.startswith("| ")][1:]
        self.assertEqual([row.split(" | ")[:3] for row in rows], [
            ["| unemployment_share_read", "BROKEN", "fixture"], ["| cm_census_yearly", "START", "session"],
            ["| primate_state_flag", "OK", "fixture"], ["| ch_board_rows", "OK", "session"],
            ["| odd_one", "ODD", "session"]])
        self.assertTrue(rows[0].endswith("state=Corsica \\| read=0.000 |"), rows[0])

    def test_a_run_with_no_self_check_line_says_so_and_one_never_read_has_no_section(self):
        found = {"run": "20261110T150000Z", "broken": [], "counts": {}, "checks": [],
                 "fixture": {"key": None, "kept": False, "detail": "the game ran on a save of the owner's, not on "
                                                                   "the fixture"},
                 "session": {"file": "/backups/runs/20261110T150000Z/debug.log", "lines": 0}}
        text = self.report.close(dict(self.summary(None, None), self_checks=found)).read_text("utf-8")
        section = text.split("## Self-checks")[1]
        self.assertIn("No TE_SELF_CHECK line was read.", section)
        self.assertIn("- The run that made the fixture: no lines (the game ran on a save of the owner's, not on the "
                      "fixture).", section)
        self.assertNotIn("| Check |", section)
        for absent in (None, "not a mapping"):
            text = self.report.close(dict(self.summary(None, None), self_checks=absent)).read_text("utf-8")
            self.assertNotIn("Self-checks", text)

    def test_a_try_event_step_is_a_table_of_its_options(self):
        rows = [
            {"index": 0, "fired": True, "fired_by": "console", "pending_options": 2,
             "before": [{"expr": "c:FRA.infamy", "ok": True, "raw": "5", "value": 5.0},
                        {"expr": "is_player = yes", "ok": True, "raw": "yes - Yes: \nYes: is_player", "value": True}],
             "after": [{"expr": "c:FRA.infamy", "ok": True, "raw": "10.5", "value": 10.5},
                       {"expr": "gdp", "ok": False, "raw": "not a valid trigger or script value", "value": None}],
             "picked": {"index": 0, "numeric_id": 10, "event": "x.1"},
             "new_errors": ["[12:00:00][jomini_script_system.cpp:247]: Script system error!", "  Error: x"],
             "did_not_fire": False},
            {"index": 1, "fired": False, "fired_by": "console", "pending_options": None, "before": [], "after": [],
             "picked": None, "new_errors": [], "did_not_fire": True},
        ]
        self.report.step("try_event", outcome="ok", event="x.1", setup="border", option_count=2, complete=False,
                         shared_state=True, options=rows)
        text = self.report.close(self.summary(None, None)).read_text("utf-8")
        self.assertIn("## try-event x.1 (setup border)", text)
        self.assertIn("State is shared between options", text)
        self.assertIn("| Option | Fired | Before | After | Picked | New errors |", text)
        self.assertIn("| 0 | yes | c:FRA.infamy = 5; is_player = yes = yes | "
                      "c:FRA.infamy = 10.5; gdp = refused (not a valid trigger or script value) | option 0 | 2 |", text)
        self.assertIn("| 1 | did not fire |  |  |  | 0 |", text)
        self.assertIn("Not a pass: option 1 did not fire", text)

    def test_a_value_is_printed_as_the_game_gave_it(self):
        # R2: %g printed 21570770 and 21570790 both as 2.15708e+07, so a change of 20 read as no change
        def read(raw, value):
            return {"expr": "c:FRA.gdp", "ok": True, "raw": raw, "value": value}
        rows = [{"index": 0, "fired": True, "fired_by": "console", "pending_options": 1,
                 "before": [read("21570770", 21570770.0), read("0.000012345678", 0.000012345678)],
                 "after": [read("21570790\nmore text", 21570790.0), read("", 1234567.25)],
                 "picked": {"index": 0, "numeric_id": 10, "event": "x.1"}, "new_errors": [], "did_not_fire": False}]
        self.report.step("try_event", outcome="ok", event="x.1", setup=None, option_count=1, complete=True,
                         shared_state=True, options=rows)
        text = self.report.close(self.summary(None, None)).read_text("utf-8")
        self.assertIn("| 0 | yes | c:FRA.gdp = 21570770; c:FRA.gdp = 0.000012345678 | "
                      "c:FRA.gdp = 21570790; c:FRA.gdp = 1234567.25 | option 0 | 0 |", text)
        self.assertNotIn("e+07", text)

    def test_an_event_that_ran_but_was_never_pending_is_not_called_unfired(self):
        # A hidden event (or one resolved at once) runs and is never pending: the console's reply says it ran.
        rows = [{"index": 0, "fired": False, "fired_by": "console", "pending_options": None, "before": [],
                 "after": [], "picked": None, "new_errors": [], "did_not_fire": False, "ran_not_pending": True}]
        self.report.step("try_event", outcome="ok", event="x.1", setup=None, option_count=None, complete=False,
                         shared_state=True, options=rows)
        text = self.report.close(self.summary(None, None)).read_text("utf-8")
        self.assertIn("| 0 | ran, not pending |  |  |  | 0 |", text)
        self.assertNotIn("did not fire", text)
        self.assertIn("Not a pass: option 0 ran (the console says Executed) but was never pending", text)
        self.assertIn("hidden", text)

    def test_a_try_event_that_ended_on_an_error_says_so(self):
        self.report.step("try_event", outcome="not_selected", detail="select_event_option 1 11 answered nothing",
                         event="x.1", setup=None, options=[])
        text = self.report.close(self.summary(None, None)).read_text("utf-8")
        self.assertIn("## try-event x.1\n", text)
        self.assertIn("Not a pass: it ended on not_selected (select_event_option 1 11 answered nothing)", text)

    def test_a_pipe_or_a_line_break_in_a_step_does_not_break_the_table(self):
        self.report.step("console", outcome="a | b\nc")
        text = self.report.close(self.summary(None, None)).read_text("utf-8")
        self.assertIn("| 1 | console | a \\| b c |", text)


if __name__ == "__main__":
    unittest.main()
