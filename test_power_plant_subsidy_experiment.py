"""The should_remove experiment's strategies and its self-check agree (#933).

te_power_plant_subsidy_strategies.txt INJECTs building_power_plant =
should_remove into every administrative strategy. The self-check sorts AI
countries by te_ai_subsidy_clean_strategy (no subsidies block in vanilla) and
te_ai_subsidy_merged_strategy (one in vanilla); together they must name exactly
the INJECTed strategies, once each, or a group reads the wrong countries.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(r"^(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class TestShouldRemoveExperiment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.strategies = _strip_comments(
            (ROOT / "common/ai_strategies/te_power_plant_subsidy_strategies.txt").read_text(encoding="utf-8-sig"))
        cls.injected = re.findall(r"(?m)^INJECT:(ai_strategy_\w+)\s*=\s*\{", cls.strategies)
        triggers = _strip_comments(
            (ROOT / "common/scripted_triggers/te_ai_subsidy_selfcheck_triggers.txt").read_text(encoding="utf-8-sig"))
        cls.clean = re.findall(r"has_strategy\s*=\s*(ai_strategy_\w+)", _block(triggers, "te_ai_subsidy_clean_strategy"))
        cls.merged = re.findall(r"has_strategy\s*=\s*(ai_strategy_\w+)", _block(triggers, "te_ai_subsidy_merged_strategy"))

    def test_each_inject_sets_should_remove(self):
        self.assertTrue(self.injected)
        for name in self.injected:
            with self.subTest(strategy=name):
                self.assertRegex(_block(self.strategies, name), r"\bbuilding_power_plant\s*=\s*should_remove\b")

    def test_the_triggers_name_the_injected_strategies(self):
        self.assertFalse(set(self.clean) & set(self.merged))
        self.assertEqual(sorted(self.clean + self.merged), sorted(self.injected))

    def test_the_default_strategy_sets_it_too(self):
        default = _strip_comments(
            (ROOT / "common/ai_strategies/edited_default_strategy.txt").read_text(encoding="utf-8-sig"))
        self.assertRegex(default, r"\bbuilding_power_plant\s*=\s*should_remove\b")


if __name__ == "__main__":
    unittest.main()
