"""The AI's covert target selection, and when it calls an operation off.

An operation's upkeep scales with the operator's GDP, so against a much
smaller country it costs more than it returns. The operations whose payoff
scales with the target's size carry covert_ai_target_worth_the_upkeep in their
will_propose; the ones whose payoff is our own progress or a threat removed do
not. Every operation type must be on one list or the other, so a new type
forces the choice.

An operation pays nothing for six months, so every action spells out its AI
will_break: kept until fully operational (covert_ai_op_settled), then ended
only once its reason has gone, or never by choice where requirement_to_maintain
already ends it. Every type must have one break rule here too.

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


TARGET = "TARGET = scope:target_country"
SETTLED = "covert_ai_op_settled = { TYPE = %s " + TARGET + " }"
HOSTILITY_GONE = "covert_ai_hostility_gone = { " + TARGET + " }"
NET_DONE = (
    "NOT = { covert_net_weaker_than = { " + TARGET
    + " STRENGTH = covert_cultivate_ai_net_done } }"
)
NEVER = "will_break = { always = no }"

# Called off once settled, when what the operation is for has gone.
BREAK_WHEN = {
    "election_interference": [HOSTILITY_GONE],
    "financial_subversion": [HOSTILITY_GONE],
    "ideological_subversion": [HOSTILITY_GONE],
    "destabilization": [HOSTILITY_GONE],
    "regime_change": [HOSTILITY_GONE],
    "nuclear_sabotage": [HOSTILITY_GONE],
    "cultivate_assets": [HOSTILITY_GONE],
    "industrial_espionage": [
        "NOT = { covert_tech_stealable_production = { " + TARGET + " } }"
    ],
    "military_espionage": [
        "NOT = { covert_tech_stealable_military = { " + TARGET + " } }"
    ],
    "space_espionage": ["sr_has_running_milestone = no"],
}
# Never by choice: requirement_to_maintain ends them when their purpose goes.
NEVER_BREAK = {"infrastructure_sabotage", "comms_disruption", "influence_campaign", "secure_material"}
# Launch-only tests: none of them is a reason to end a running operation.
LAUNCH_ONLY = (
    "covert_operations_available_slots",
    "iw_funding_level",
    "in_default",
    "intelligence_capacity_total",
    "covert_ai_target",
    "country_rank",
)


def _ai(op_type):
    block = _top_level_block(_text(ACTIONS), "covert_%s_action = {" % op_type)
    return _section(block, "\tai = {")


def _will_propose(op_type):
    return _section(_ai(op_type), "will_propose = {")


def _will_break(op_type):
    return _section(_ai(op_type), "will_break = {")


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


class WillBreakTests(unittest.TestCase):
    def test_every_type_has_one_break_rule(self):
        self.assertEqual(set(BREAK_WHEN) | NEVER_BREAK, set(TYPES))
        self.assertFalse(set(BREAK_WHEN) & NEVER_BREAK)
        for op_type in TYPES:
            with self.subTest(op_type):
                self.assertEqual(_ai(op_type).count("will_break = {"), 1)

    def test_breakable_types_wait_until_settled(self):
        for op_type, reasons in sorted(BREAK_WHEN.items()):
            with self.subTest(op_type):
                will = _will_break(op_type)
                self.assertIn(SETTLED % op_type, will)
                for reason in reasons:
                    self.assertIn(reason, will)

    def test_never_break_types(self):
        for op_type in sorted(NEVER_BREAK):
            with self.subTest(op_type):
                self.assertEqual(_will_break(op_type), NEVER)

    def test_launch_only_tests_never_break(self):
        for op_type in TYPES:
            with self.subTest(op_type):
                will = _will_break(op_type)
                for key in LAUNCH_ONLY:
                    self.assertNotIn(key, will)

    def test_cultivate_stops_at_a_strong_network_whatever_its_age(self):
        will = _will_break("cultivate_assets")
        settled = _section(will, "AND = {")
        self.assertIn(SETTLED % "cultivate_assets", settled)
        self.assertIn(HOSTILITY_GONE, settled)
        self.assertIn(NET_DONE, will)
        self.assertNotIn(NET_DONE, settled)

    def test_settled_means_fully_operational(self):
        block = _top_level_block(_text(TRIGGERS), "covert_ai_op_settled = {")
        self.assertIn("variable = iw_ops", block)
        self.assertIn("has_tag = iw_op_$TYPE$", block)
        self.assertIn("var:iw_target ?= $TARGET$", block)
        self.assertIn("covert_op_is_fully_operational = yes", block)

    def test_hostility_gone_is_looser_than_the_launch_test(self):
        block = _top_level_block(_text(TRIGGERS), "covert_ai_hostility_gone = {")
        nor = _section(block, "NOR = {")
        for clause in (
            "has_diplomatic_pact = { who = $TARGET$ type = rivalry }",
            "$TARGET$ = { has_diplomatic_pact = { who = root type = rivalry } }",
            "has_attitude = { who = $TARGET$ attitude = antagonistic }",
            "has_attitude = { who = $TARGET$ attitude = belligerent }",
            "has_attitude = { who = $TARGET$ attitude = domineering }",
            "$TARGET$.relations:root <= relations_threshold:poor",
        ):
            self.assertIn(clause, nor)

    def test_cultivate_stops_above_where_it_starts(self):
        body = _text(VALUES)
        ceiling = int(re.search(r"(?m)^covert_cultivate_ai_net_ceiling = (\d+)$", body).group(1))
        done = int(re.search(r"(?m)^covert_cultivate_ai_net_done = (\d+)$", body).group(1))
        self.assertEqual(done, 75)
        self.assertGreater(done, ceiling)


if __name__ == "__main__":
    unittest.main()
