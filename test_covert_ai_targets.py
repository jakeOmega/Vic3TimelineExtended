"""The AI's covert target selection: much weaker targets only with money to burn.

An operation's upkeep scales with the operator's GDP, so against a much
smaller country it costs more than it returns. The operations whose payoff
scales with the target's size carry covert_ai_target_worth_the_upkeep in their
will_propose; the ones whose payoff is our own progress or a threat removed do
not. Every operation type must be on one list or the other, so a new type
forces the choice.

Run: python3 -m unittest test_covert_ai_targets -v
"""

import re
import unittest

from test_covert_new_ops import ACTIONS, TRIGGERS, VALUES, _section, _text, _top_level_block
from test_covert_op_registry import TYPES

GATE = "covert_ai_target_worth_the_upkeep = { TARGET = scope:target_country }"
LOSING = "is_losing_war_against = { ENEMY = scope:target_country }"

# The payoff scales with the target's size: its politics, economy, movements,
# bloc pull, our network there, or its war effort.
GATED = {
    "election_interference",
    "financial_subversion",
    "influence_campaign",
    "ideological_subversion",
    "destabilization",
    "regime_change",
    "cultivate_assets",
    "infrastructure_sabotage",
    "comms_disruption",
}
# The payoff is our research or space progress, or the threat removed.
EXEMPT = {
    "industrial_espionage",
    "military_espionage",
    "space_espionage",
    "nuclear_sabotage",
    "secure_material",
}
WARTIME = {"infrastructure_sabotage", "comms_disruption"}


def _will_propose(op_type):
    block = _top_level_block(_text(ACTIONS), "covert_%s_action = {" % op_type)
    return _section(_section(block, "\tai = {"), "will_propose = {")


class ClassificationTests(unittest.TestCase):
    def test_every_type_is_classified_once(self):
        self.assertEqual(GATED | EXEMPT, set(TYPES))
        self.assertFalse(GATED & EXEMPT)


class GateTests(unittest.TestCase):
    def test_gated_types_take_the_test(self):
        for op_type in sorted(GATED):
            with self.subTest(op_type):
                self.assertIn(GATE, _will_propose(op_type))

    def test_exempt_types_do_not(self):
        for op_type in sorted(EXEMPT):
            with self.subTest(op_type):
                self.assertNotIn("covert_ai_target", _will_propose(op_type))

    def test_wartime_types_waive_it_when_losing_to_the_target(self):
        for op_type in sorted(WARTIME):
            with self.subTest(op_type):
                will = _will_propose(op_type)
                gate_or = will[will.rindex("OR = {", 0, will.index(GATE)):will.index(GATE)]
                self.assertIn(LOSING, gate_or)

    def test_peacetime_types_have_no_waiver(self):
        for op_type in sorted(GATED - WARTIME):
            with self.subTest(op_type):
                self.assertNotIn("is_losing_war_against", _will_propose(op_type))


class HelperTests(unittest.TestCase):
    def test_constants(self):
        body = _text(VALUES)
        self.assertRegex(body, r"(?m)^covert_ai_much_weaker_gdp_factor = 10$")
        self.assertRegex(body, r"(?m)^covert_ai_spare_reserves_ratio = 0\.5$")

    def test_much_weaker_compares_gdp_by_the_factor(self):
        block = _top_level_block(_text(TRIGGERS), "covert_ai_target_much_weaker = {")
        self.assertIn("gdp >= {", block)
        self.assertIn("value = $TARGET$.gdp", block)
        self.assertIn("multiply = covert_ai_much_weaker_gdp_factor", block)

    def test_money_to_burn_needs_full_reserves_and_a_surplus(self):
        block = _top_level_block(_text(TRIGGERS), "covert_ai_has_money_to_burn = {")
        self.assertIn("scaled_gold_reserves >= covert_ai_spare_reserves_ratio", block)
        self.assertIn("net_fixed_income > 0", block)

    def test_gate_passes_comparable_targets_or_a_rich_operator(self):
        block = _top_level_block(_text(TRIGGERS), "covert_ai_target_worth_the_upkeep = {")
        self.assertIn("NOT = { covert_ai_target_much_weaker = { TARGET = $TARGET$ } }", block)
        self.assertIn("covert_ai_has_money_to_burn = yes", block)
        self.assertEqual(len(re.findall(r"\bOR = \{", block)), 1)


if __name__ == "__main__":
    unittest.main()
