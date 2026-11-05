"""The sv_treasury_event_<tier> script values: one-off payments a share of income.

They read gold_reserves until 2026-10-24. A country living on loans has no
reserves, so "Allocate the full budget" in The Budget Debate
(ministry_law_events.2) charged it nothing. They now follow the convention every
other one-off payment uses (gm_event_cost, te_demog_wave_cost_*): a share of
yearly_gross_income, positive, negated where the option is a cost.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VALUES = ROOT / "common/script_values/extra_script_values.txt"
MINISTRY_EVENTS = ROOT / "events/ministry_law_events.txt"

TIERS = {"tiny": 0.005, "small": 0.02, "medium": 0.05, "large": 0.15, "huge": 0.30}


def option_body(text, name):
    """The body of the option block whose `name = <name>`."""
    start = text.index(f"name = {name}\n")
    open_brace = text.rindex("option = {", 0, start) + len("option = ")
    depth = 0
    for i in range(open_brace, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[open_brace:i + 1]
    raise AssertionError(f"unclosed option {name}")


class TreasuryEventTierTest(unittest.TestCase):
    def setUp(self):
        self.values = VALUES.read_text(encoding="utf-8-sig")
        self.events = MINISTRY_EVENTS.read_text(encoding="utf-8-sig")

    def test_each_tier_is_a_positive_share_of_yearly_gross_income(self):
        for tier, share in TIERS.items():
            with self.subTest(tier=tier):
                m = re.search(rf"^sv_treasury_event_{tier}\s*=\s*\{{([^}}]*)\}}", self.values, re.M)
                self.assertIsNotNone(m, f"sv_treasury_event_{tier} is missing")
                body = m.group(1).split()
                self.assertEqual(body, ["value", "=", "yearly_gross_income", "multiply", "=", body[-1]])
                self.assertAlmostEqual(float(body[-1]), share)

    def test_spending_options_pay_and_the_saving_option_gains(self):
        cost = re.compile(r"add_treasury = \{\s*value = sv_treasury_event_medium\s*multiply = -1\s*\}")
        for option in ("ministry_law_events.2.a", "ministry_law_events.40.b"):
            with self.subTest(option=option):
                self.assertRegex(option_body(self.events, option), cost)
        self.assertIn("add_treasury = sv_treasury_event_small\n",
                      option_body(self.events, "ministry_law_events.42.b"))


if __name__ == "__main__":
    unittest.main()
