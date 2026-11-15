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


def type_string(word):
    return b"\xf7\x31\x01\x00\x0f\x00" + bytes([len(word), 0]) + word


class TestCountryTypes(unittest.TestCase):
    def test_each_country_takes_the_first_type_after_its_header(self):
        blob = (b"head-of-7 " + type_string(b"decentralized") + type_string(b"recognized")
                + b" head-of-9 " + type_string(b"other_word") + type_string(b"colonial"))
        heads = [(0, 7, None, None), (blob.index(b"head-of-9"), 9, None, None)]
        self.assertEqual(report.country_types(blob, heads), {7: "decentralized", 9: "colonial"})


class TestSelfCheckLine(unittest.TestCase):
    def test_conservatives_against_the_rest_over_countries_not_decentralized(self):
        table = {"conservative_agenda": [120, 20, 90, 20, 100, 20], "nationalist_agenda": [50, 20, 45, 20, 40, 20],
                 "egalitarian_agenda": [30, 10, 25, 10, 20, 9]}
        self.assertEqual(report.self_check_line(table),
                         "self-check count: conservative 20/100 = 0.20   rest 29/60 = 0.48")

    def test_no_conservatives(self):
        self.assertIn("conservative 0/0 = 0.00", report.self_check_line({"nationalist_agenda": [1, 0, 1, 0, 1, 0]}))


if __name__ == "__main__":
    unittest.main()
