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

    def test_a_pipe_or_a_line_break_in_a_step_does_not_break_the_table(self):
        self.report.step("console", outcome="a | b\nc")
        text = self.report.close(self.summary(None, None)).read_text("utf-8")
        self.assertIn("| 1 | console | a \\| b c |", text)


if __name__ == "__main__":
    unittest.main()
