"""scripts/analysis/ai_law_cadence_report.py: the pure helpers (the save readers need a save, which CI lacks)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts" / "analysis"))
import ai_law_cadence_report as report  # noqa: E402


class TestPolitical(unittest.TestCase):
    def test_picks_the_political_strategy(self):
        names = ["ai_strategy_industrial_expansion", "ai_strategy_conservative_agenda", "ai_strategy_armed_isolationism"]
        self.assertEqual(report.political(names), "ai_strategy_conservative_agenda")

    def test_the_named_reform_strategies_count(self):
        for name in ("ai_strategy_tanzimat_reforms", "ai_strategy_great_reforms", "ai_strategy_meiji_restoration",
                     "ai_strategy_maintain_mandate_of_heaven"):
            with self.subTest(name=name):
                self.assertEqual(report.political([name]), name)

    def test_administrative_and_diplomatic_do_not(self):
        self.assertIsNone(report.political(["ai_strategy_placate_population", "ai_strategy_territorial_expansion"]))


class TestSamePhaseShare(unittest.TestCase):
    def test_starts_on_one_phase(self):
        by_country = {1: [6, 6 + 1200, 6 + 3600], 2: [18, 18 + 2400]}
        self.assertEqual(report.same_phase_share(by_country, 1200), 1.0)
        self.assertAlmostEqual(report.same_phase_share(by_country, 2400), 2 / 4)

    def test_no_pairs(self):
        self.assertIsNone(report.same_phase_share({1: [6]}, 1200))

    def test_the_candidate_periods_include_fifty_days(self):
        self.assertIn(1200, report.PERIODS)
        self.assertIn(2400, report.PERIODS)


if __name__ == "__main__":
    unittest.main()
