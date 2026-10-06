"""The emissions-control tiers are ranked for the AI so it moves up, not down.

The three tiers make no goods, so the engine treats every switch among them as
a downgrade and applies PRODUCTION_METHOD_STICKINESS_DOWNGRADE to the
challenger. Unweighted, the near-equal pure-cost tiers flipped every few
months in the 2015 observer run (ports: 35 basic/advanced switches in four
months, each a five-year retool). Owner ruling 2026-10-06: up, never down.
Each tier's ai_weight must beat the one below it by more than 1 / stickiness,
so the lower tier, weighted down and multiplied by the stickiness, cannot win
on an equal raw score; and the weights stay moderate, so cost still counts.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIERS = ("pm_no_emissions_control", "pm_basic_emissions_control", "pm_advanced_emissions_control")


def _block(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class TestEmissionsControlAiWeight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pms = re.sub(r"#[^\n]*", "", (ROOT / "common/production_methods/extra_pms.txt").read_text(encoding="utf-8-sig"))
        cls.weights = [float(re.search(r"\bai_weight\s*=\s*([\d.]+)", _block(pms, t))[1]) for t in TIERS]
        defines = (ROOT / "common/defines/extra_defines.txt").read_text(encoding="utf-8-sig")
        cls.stickiness = float(re.search(r"PRODUCTION_METHOD_STICKINESS_DOWNGRADE\s*=\s*([\d.]+)", defines)[1])

    def test_each_tier_outweighs_the_one_below_past_the_stickiness(self):
        for lower, higher in zip(self.weights, self.weights[1:]):
            self.assertGreater(higher / lower, 1 / self.stickiness)

    def test_the_weights_stay_moderate(self):
        # A huge ratio would make cost irrelevant ("always the highest tier").
        for lower, higher in zip(self.weights, self.weights[1:]):
            self.assertLessEqual(higher / lower, 4)


if __name__ == "__main__":
    unittest.main()
