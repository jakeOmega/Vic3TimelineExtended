# -*- coding: utf-8 -*-
"""An overdrawn intervention budget lifts tools until it balances (2026-11-14).

Every intervention in force holds its cost in points
(``country_banking_intervention_max_add``, negative on the tool's modifier),
and ``banking_crash_check_overdrawn_interventions`` (banking_cycle_effects.txt,
the banking entry's monthly pulse) lifts one a month while the sum is below
zero. Until 2026-11-14 its chain ended at the five External & Currency tools,
so a budget cut left every other tool running on points the country no longer
had: enact a generous banking law, switch the tools on, go back to Unregulated
Banking and keep them. The points a common currency gives its issuer come and
go with the bloc, so they would have run through the same hole.

The engine checks none of this: a tool the chain leaves out simply stays on.
So:

* every modifier that holds points is in the chain, except the Bank Holiday,
  which is left to run out its ninety days;
* each branch asks for the tool it lifts, and lifts it with that tool's own
  history marker;
* the chain's earlier branches are as they were, and the standing tools follow
  them cheapest first within each economy's family;
* one tool a pulse, and only while the budget is overdrawn;
* the cycle simulator's port lifts in the same order.
"""

import re
import unittest
from pathlib import Path

from test_monetary_union_leader import definitions

ROOT = Path(__file__).resolve().parent
EFFECT = "banking_crash_check_overdrawn_interventions"
LEFT_OUT = {"banking_bank_holiday": "timed: it ends on its own within ninety days"}
FAMILIES = (("banking_", "market"), ("planning_", "command"), ("cooperative_", "coop"))


def field(body, name):
    return next(val for key, _, val in body if key == name)


def point_holders():
    """{modifier: cost} for every static modifier with a negative points line."""
    holders = {}
    for name, body in definitions("common/static_modifiers/extra_modifiers.txt").items():
        for key, _, val in body:
            if key == "country_banking_intervention_max_add" and float(val) < 0:
                holders[name] = -float(val)
    return holders


def tool_triggers():
    """{trigger: modifier} for the banking_tool_*_active family (market_triggers.txt)."""
    out = {}
    text = (ROOT / "common/scripted_triggers/market_triggers.txt").read_text(encoding="utf-8-sig")
    for m in re.finditer(r"(?m)^(banking_tool_\w+_active)\s*=\s*\{ je:je_banking_cycle \?= \{ has_modifier = (\w+) \} \}", text):
        out[m.group(1)] = m.group(2)
    return out


def disable_effects():
    """{modifier: (effect name, off marker)} from every banking_effect_*_disable_* pair."""
    out = {}
    for path in ("common/scripted_effects/banking_policy_effects.txt",
                 "common/scripted_effects/banking_external_effects.txt"):
        for name, body in definitions(path).items():
            if not re.match(r"banking_effect_c[bew]_disable_", name):
                continue
            mark = modifier = None
            for key, _, val in body:
                if key == "te_history_record_banking_marker":
                    mark = field(val, "MARK")
                elif key == "je:je_banking_cycle":
                    for k, _, v in val:
                        if k == "remove_modifier":
                            modifier = v
            if modifier:
                out[modifier] = (name, mark)
    return out


def chain():
    """The chain's branches in order: (the modifier asked for, how it is lifted, marker or None)."""
    body = definitions("common/scripted_effects/banking_cycle_effects.txt")[EFFECT]
    assert [key for key, _, _ in body] == ["if"], "the effect is one guarded chain"
    guard = body[0][2]
    limit = field(guard, "limit")
    assert limit == [("modifier:country_banking_intervention_max_add", "<", "0")], limit
    triggers, disables = tool_triggers(), disable_effects()
    by_effect = {effect: modifier for modifier, (effect, _) in disables.items()}
    branches = []
    keys = [key for key, _, _ in guard if key != "limit"]
    assert keys[0] == "if" and set(keys[1:]) == {"else_if"}, "one if, then else_ifs: one lift a pulse"
    for key, _, val in guard:
        if key == "limit":
            continue
        (asked, _, answer), = field(val, "limit")
        assert answer == "yes" or asked == "has_modifier", (asked, answer)
        asked_modifier = answer if asked == "has_modifier" else triggers[asked]
        (action, _, arg), = [item for item in val if item[0] != "limit"]
        if action == "remove_modifier":
            lifted, how, mark = arg, "remove", None
        elif action == "banking_strip_tool":
            lifted, how, mark = field(arg, "MODIFIER"), "strip", field(arg, "MARK")
        else:
            lifted, how, mark = by_effect[action], "disable", disables[by_effect[action]][1]
        assert lifted == asked_modifier, f"the branch asks for {asked_modifier} and lifts {lifted}"
        branches.append((lifted, how, mark))
    return branches


class ChainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.holders = point_holders()
        cls.chain = chain()
        cls.order = [modifier for modifier, _, _ in cls.chain]

    def test_every_tool_that_holds_points_is_in_the_chain(self):
        self.assertGreater(len(self.holders), 45)
        missing = sorted(set(self.holders) - set(self.order) - set(LEFT_OUT))
        self.assertEqual(missing, [], "these hold intervention points and are never lifted on an overdraft")
        self.assertEqual(sorted(set(self.order) - set(self.holders)), [], "in the chain, but holds no points")
        self.assertEqual(len(self.order), len(set(self.order)), "a tool is in the chain twice")

    def test_the_bank_holiday_is_the_one_tool_left_out(self):
        self.assertEqual(set(self.holders) - set(self.order), set(LEFT_OUT))

    def test_the_branches_that_were_there_come_first_and_unchanged(self):
        # Crash interventions (bare removes), then the External & Currency tools through
        # their own Disable: exactly what an overdraft did before the standing tools joined.
        crash = [m for m, how, _ in self.chain if how == "remove"]
        self.assertEqual(self.order[:len(crash)], crash)
        self.assertTrue(all(m.startswith("banking_crash_intervention_") for m in crash))
        self.assertEqual(sorted(crash), sorted(m for m in self.holders if m.startswith("banking_crash_intervention_")))
        external = self.order[len(crash):len(crash) + 5]
        self.assertEqual(external, ["banking_emergency_import_financing", "banking_sterilize_inflows",
                                    "banking_fx_surrender", "banking_restrict_inflows",
                                    "banking_foreign_borrowing_limits"])
        self.assertTrue(all(how == "disable" for _, how, _ in self.chain[len(crash):len(crash) + 5]))

    def standing(self):
        crash = sum(1 for _, how, _ in self.chain if how == "remove")
        return self.chain[crash + 5:]

    def test_the_standing_tools_go_cheapest_first_within_each_family(self):
        standing = [m for m, _, _ in self.standing()]
        seen = []
        for prefix, _ in FAMILIES:
            family = [m for m in standing if m.startswith(prefix)]
            costs = [self.holders[m] for m in family]
            with self.subTest(family=prefix):
                self.assertGreater(len(family), 7)
                self.assertEqual(costs, sorted(costs), f"not cheapest first: {list(zip(family, costs))}")
            seen += family
        # The families are not interleaved (a country runs one at a time).
        self.assertEqual(standing, seen)

    def test_a_standing_tool_is_lifted_as_a_law_lifts_it(self):
        # banking_strip_tool: the history marker and none of the Disable's reactions; the
        # marker is the one the tool's own Disable writes. Emergency Liquidity goes through
        # its Disable, for the refund of what it lent.
        disables = disable_effects()
        for modifier, how, mark in self.standing():
            with self.subTest(tool=modifier):
                self.assertEqual(mark, disables[modifier][1], "not the tool's own off marker")
                if modifier == "banking_emergency_liquidity_program":
                    self.assertEqual(how, "disable")
                else:
                    self.assertEqual(how, "strip")
        eliq = dict((k, v) for k, _, v in definitions("common/scripted_effects/banking_policy_effects.txt")
                    ["banking_effect_cb_disable_emergency_liquidity_program"])
        self.assertEqual(eliq.get("add_treasury"), "emergency_liquidity_program_deactivation_refund")

    def test_the_strip_helper_costs_nothing(self):
        strip = definitions("common/scripted_effects/extra_effects.txt")["banking_strip_tool"]
        (key, _, body), = strip
        self.assertEqual(key, "if")
        self.assertEqual([k for k, _, _ in body], ["limit", "te_history_record_banking_marker", "je:je_banking_cycle"])


class PulseTest(unittest.TestCase):
    """One lift a pulse, in the chain's order, and none on a balanced budget."""

    def lifted(self, active, budget):
        if budget >= 0:
            return None
        return next((m for m, _, _ in chain() if m in active), None)

    def test_one_tool_a_month_until_the_budget_balances(self):
        holders = point_holders()
        # A central bank at 12 points holding 11, which loses the issuer's four.
        active = {"banking_expand_deposit_guarantee", "banking_reserve_requirements",
                  "banking_raise_margin_requirements", "banking_countercyclical_capital_buffer",
                  "banking_moral_suasion"}
        total, lifts = 8, []
        while True:
            budget = total - sum(holders[m] for m in active)
            gone = self.lifted(active, budget)
            if gone is None:
                break
            lifts.append(gone)
            active.discard(gone)
        self.assertEqual(lifts, ["banking_moral_suasion", "banking_reserve_requirements"])
        self.assertEqual(total - sum(holders[m] for m in active), 0)
        self.assertIn("banking_expand_deposit_guarantee", active, "the dearest tool is the last to go")

    def test_a_crash_intervention_goes_before_any_standing_tool(self):
        active = {"banking_moral_suasion", "banking_crash_intervention_open_market"}
        self.assertEqual(self.lifted(active, -1), "banking_crash_intervention_open_market")

    def test_a_balanced_budget_lifts_nothing(self):
        self.assertIsNone(self.lifted({"banking_moral_suasion"}, 0))

    def test_a_bank_holiday_alone_is_left_to_expire(self):
        self.assertIsNone(self.lifted({"banking_bank_holiday"}, -2))


class SimulatorPortTest(unittest.TestCase):
    """scripts/analysis/banking_cycle_sim.py's prune_overdrawn_tools lifts in the script's order."""

    def test_the_port_follows_the_chain(self):
        from scripts.analysis import banking_cycle_sim as sim
        names = dict(sim.TOOL_MODIFIER_NAMES)
        names.update(sim.ALT_TOOL_MODIFIER_NAMES)
        order = [m for m, how, _ in chain() if how != "remove"]
        for prefix, economy in FAMILIES:
            script = [m for m in order if m.startswith(prefix)]
            port = [names[tool] for tool in sim.OVERDRAFT_SHED_ORDER[economy]]
            with self.subTest(economy=economy):
                self.assertEqual(port, script)
        self.assertNotIn("bank_holiday", sim.OVERDRAFT_SHED_ORDER["market"])


if __name__ == "__main__":
    unittest.main()
