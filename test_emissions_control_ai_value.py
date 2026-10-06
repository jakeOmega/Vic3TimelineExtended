"""The emissions-control tiers are ranked for the AI so it moves up, not down.

The three tiers make no goods, so the engine treats every switch among them as
a downgrade and applies PRODUCTION_METHOD_STICKINESS_DOWNGRADE to the
challenger. Under the default most_profitable the near-equal pure-cost tiers
flipped every few months in the 2015 observer run (ports: 35 basic/advanced
switches in four months, each a five-year retool). Owner ruling 2026-10-06:
up, never down. The group takes ai_selection = most_productive (the tiers then
tie, so the stickiness holds them) and each tier carries an ai_value.

`ai_weight`, which production_methods.md documents, is rejected by the 1.14.5
parser ("Unexpected token: ai_weight"); `ai_value` is the field vanilla's
pm_simple_organization sets. What ai_value does is undocumented, so the values
must rank the tiers whether it replaces the method's base score
(NAI PRODUCTION_METHOD_BASE_VALUE), adds to it, or multiplies the score.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIERS = ("pm_no_emissions_control", "pm_basic_emissions_control", "pm_advanced_emissions_control")

# Vanilla game/common/defines/00_ai.txt (1.14.5), unless extra_defines.txt overrides them.
VANILLA_BASE_VALUE = 1000.0          # PRODUCTION_METHOD_BASE_VALUE
VANILLA_SHORTAGE_FACTOR = 10.0       # PRODUCTION_METHOD_REDUCE_OUTPUT_PENALTY_FACTOR


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(r"^(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def _define(defines, key, default):
    m = re.search(r"\b" + key + r"\s*=\s*([\d.]+)", defines)
    return float(m[1]) if m else default


class TestEmissionsControlAiValue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pms = _strip_comments((ROOT / "common/production_methods/extra_pms.txt").read_text(encoding="utf-8-sig"))
        cls.values = [float(re.search(r"\bai_value\s*=\s*([\d.]+)", _block(pms, t))[1]) for t in TIERS]
        groups = _strip_comments(
            (ROOT / "common/production_method_groups/extra_pm_groups.txt").read_text(encoding="utf-8-sig"))
        cls.group = _block(groups, "pmg_emissions_control")
        defines = _strip_comments((ROOT / "common/defines/extra_defines.txt").read_text(encoding="utf-8-sig"))
        cls.stickiness = _define(defines, "PRODUCTION_METHOD_STICKINESS_DOWNGRADE", 0.75)
        cls.base = _define(defines, "PRODUCTION_METHOD_BASE_VALUE", VANILLA_BASE_VALUE)
        cls.shortage = _define(defines, "PRODUCTION_METHOD_REDUCE_OUTPUT_PENALTY_FACTOR", VANILLA_SHORTAGE_FACTOR)

    def _scores(self):
        # ai_value as the method's score itself (or a multiplier on it: same ratios),
        # and ai_value added to the base score.
        return {"replaces or multiplies": self.values,
                "adds to the base": [self.base + v for v in self.values]}

    def test_the_group_ignores_profit(self):
        self.assertRegex(self.group, r"\bai_selection\s*=\s*most_productive\b")
        for tier in TIERS:
            self.assertRegex(self.group, r"\b" + tier + r"\b")

    def test_the_values_are_positive(self):
        # A negative score turns a ratio around ("magnifies the wrong way").
        for v in self.values:
            self.assertGreater(v, 0)

    def test_each_tier_outweighs_the_one_below_past_the_stickiness(self):
        # The higher tier, as the challenger, is multiplied by the downgrade
        # stickiness and must still win; then the lower one can never win back.
        for reading, scores in self._scores().items():
            for lower, higher in zip(scores, scores[1:]):
                with self.subTest(reading=reading, lower=lower, higher=higher):
                    self.assertGreater(higher * self.stickiness, lower)

    def test_the_values_stay_moderate(self):
        # A huge ratio would make cost irrelevant even at extreme prices, and an
        # input shortage (score x shortage factor for the method that avoids it)
        # must still be able to move a building down a tier.
        for lower, higher in zip(self.values, self.values[1:]):
            self.assertLessEqual(higher / lower, 4)
            self.assertLess(higher / lower, self.shortage)


class TestNoProductionMethodAiWeight(unittest.TestCase):
    def test_no_method_or_group_sets_ai_weight(self):
        # 1.14.5: "Unexpected token: ai_weight" on a production method, so the
        # line is dropped at load. The field is ai_value.
        offenders = []
        for folder in ("common/production_methods", "common/production_method_groups"):
            for path in sorted((ROOT / folder).glob("*.txt")):
                text = _strip_comments(path.read_text(encoding="utf-8-sig"))
                for n, line in enumerate(text.splitlines(), 1):
                    if re.match(r"\s*ai_weight\s*=", line):
                        offenders.append(f"{path.relative_to(ROOT)}:{n}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
