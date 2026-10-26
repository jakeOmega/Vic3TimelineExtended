# -*- coding: utf-8 -*-
"""Construction Cost Scaling: the GDP part times the share of it that applies, which follows slack (#1034 follow-up).

The share is 1 at slack (peasants and unemployed over the workforce) construction_cost_slack_full or less, 0 at
construction_cost_slack_none or more, a straight line between, and moves construction_cost_slack_ease of the way
toward that at each yearly pulse (te_cc_yearly_update). The scripts/analysis tools model the same rule
(econ_growth_sim.slack_target and eased_slack_factor); these tests keep the script's arithmetic, its wiring and its
self-check whole, and the two in step. The engine reports none of it.
"""

import os
import unittest

from scripts.analysis import econ_growth_sim as G
from scripts.analysis import econ_sim_data as D
from test_unemployment_share import REPO, _body, _read, _squash, _top_blocks

VALUES = os.path.join(REPO, "common", "script_values", "extra_script_values.txt")
COUNTRY_VALUES = os.path.join(REPO, "common", "script_values", "te_unemployment_values.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_construction_cost_effects.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "extra_on_actions.txt")


def _value(text, name):
    return _squash(_body(text, name))


class TheArithmetic(unittest.TestCase):
    def setUp(self):
        self.values = _read(VALUES)

    def test_every_reader_takes_the_product(self):
        self.assertEqual(_value(self.values, "construction_cost_scaling_mult"),
                         "value = construction_cost_scaling_gdp_mult multiply = te_cc_slack_factor_now")

    def test_before_the_first_reading_the_share_carries_the_scaling_in_force(self):
        # A save from before the rule keeps its old X until the pulse (GDP part x carried share = old raw X);
        # a new game has no prior_construction_scaling, so it starts from 0.
        self.assertEqual(_value(self.values, "te_cc_slack_factor_now"),
                         "value = 0 if = { limit = { has_variable = te_cc_slack_factor } value = var:te_cc_slack_factor }"
                         " else_if = { limit = { has_variable = prior_construction_scaling } "
                         "value = te_cc_slack_factor_carried }")
        self.assertEqual(_value(self.values, "te_cc_slack_factor_carried"),
                         "value = var:prior_construction_scaling divide = { value = te_cc_other_sources add = 1 "
                         "multiply = construction_cost_scaling_gdp_mult min = 0.001 } max = 1 min = 0")

    def test_the_tooltip_total_is_the_cost_in_force(self):
        # One plus every construction-cost modifier, this scaling included; the other factor is the quotient,
        # so the product always equals the cost in force and the engine's breakdown adds up to it less one.
        self.assertEqual(_value(self.values, "te_cc_total_factor"), "value = te_cc_modifier_total add = 1 min = 0")
        self.assertEqual(_value(self.values, "te_cc_others_factor"),
                         "value = te_cc_total_factor divide = { value = te_cc_scaling_factor min = 1 }")
        self.assertIn("modifier:country_construction_goods_cost_mult", _value(self.values, "te_cc_modifier_total"))
        # the scaling as the pulse set it; before the first reading, today's GDP part x the carried share (the X in force)
        self.assertEqual(_value(self.values, "te_cc_scaling_factor"),
                         "value = te_cc_gdp_part_now multiply = te_cc_slack_factor_now add = 1")
        for name, var, live in (("te_cc_gdp_part_now", "te_cc_gdp_part", "construction_cost_scaling_gdp_mult"),
                                ("te_cc_gdppc_now", "te_cc_gdppc", "country_gdp_per_capita")):
            self.assertEqual(_value(self.values, name), "value = " + live + " if = { limit = { has_variable = "
                             "te_cc_slack_factor } value = var:" + var + " }")
        self.assertIn("modifier:goods_input_construction_mult", _value(self.values, "te_cc_modifier_total"))

    def test_target_and_easing(self):
        self.assertEqual(_value(self.values, "te_cc_slack_target"),
                         "value = construction_cost_slack_none subtract = te_cc_slack_now divide = { "
                         "value = construction_cost_slack_none subtract = construction_cost_slack_full min = 0.001 } "
                         "max = 1 min = 0")
        self.assertEqual(_value(self.values, "te_cc_slack_factor_eased"),
                         "value = te_cc_slack_target subtract = te_cc_slack_factor_now "
                         "multiply = construction_cost_slack_ease add = te_cc_slack_factor_now max = 1 min = 0")

    def test_the_tools_model_the_same_rule(self):
        # The script's formulas above, evaluated by hand, against econ_growth_sim's.
        c = D.CurveConstants(1.0, 1.0, 100.0, 10.0, 0.03, 0.15, 0.33333)
        for slack in (0.0, 0.03, 0.05, 0.09, 0.149, 0.15, 0.4):
            target = min(1.0, max(0.0, (0.15 - slack) / max(0.15 - 0.03, 0.001)))
            self.assertAlmostEqual(G.slack_target(c, slack), target)
            for prev in (0.0, 0.4, 1.0):
                eased = min(1.0, max(0.0, (target - prev) * 0.33333 + prev))
                self.assertAlmostEqual(G.eased_slack_factor(c, prev, slack), eased)

    def test_the_country_sums_skip_unwalked_states(self):
        country = _read(COUNTRY_VALUES)
        for name, var in (("te_country_walked_workforce", "te_unemp_wf_count"),
                          ("te_country_slack_share", "te_unemp_slack_count"),
                          ("te_country_peasant_share", "te_unemp_peasant_count")):
            body = _value(country, name)
            self.assertIn("every_scope_state = { limit = { has_variable = te_unemp_slack_count } add = var:"
                          + var + " }", body, name)


class TheWiring(unittest.TestCase):
    def test_the_pulse_reads_the_slack_before_it_sets_the_modifier(self):
        body = _squash(_body(_read(ON_ACTIONS), "construction_cost_scaling_on_action"))
        self.assertTrue(body.startswith("effect = { te_cc_yearly_update = yes "), body[:80])

    def test_the_update(self):
        body = _squash(_top_blocks(_read(EFFECTS))["te_cc_yearly_update"])
        self.assertIn("if = { limit = { te_country_walked_workforce > 0 } "
                      "set_variable = { name = te_cc_slack value = te_country_slack_share } "
                      "set_variable = { name = te_cc_peasants value = te_country_peasant_share } "
                      "set_variable = { name = te_cc_slack_factor value = te_cc_slack_factor_eased } }", body)
        # the tooltip shows the scaling in force: the GDP part the pulse used, stored after the share moved
        self.assertIn("set_variable = { name = te_cc_gdp_part value = construction_cost_scaling_gdp_mult }", body)
        self.assertLess(body.index("te_cc_slack_factor_eased"), body.index("te_cc_gdp_part"))
        self.assertTrue(body.endswith("te_cc_slack_selfcheck = yes"), body[-60:])

    def test_the_tooltip_reads_stored_figures_only(self):
        # A GUI read that iterated every state would run every frame: the tooltip's values read variables.
        values = _read(VALUES)
        for name in ("te_cc_slack_now", "te_cc_peasants_now", "te_cc_unemployed_now", "te_cc_slack_target",
                     "te_cc_gdppc_now", "te_cc_gdp_part_now", "te_cc_scaling_factor", "te_cc_others_factor",
                     "te_cc_total_factor", "te_cc_modifier_total", "te_cc_other_sources", "te_cc_direct_rule",
                     "te_cc_has_reading", "te_cc_slack_factor_now", "te_cc_slack_factor_carried"):
            body = _value(values, name)
            self.assertNotIn("every_", body, name)
            self.assertNotIn("te_country_", body, name)


class TheSelfCheck(unittest.TestCase):
    def setUp(self):
        self.body = _squash(_top_blocks(_read(EFFECTS))["te_cc_slack_selfcheck"])

    def test_once_a_game_and_only_where_it_can_tell(self):
        self.assertIn("NOT = { has_global_variable = te_cc_slack_check_done }", self.body)
        # a reading at an earlier pulse: every state walked at least once, so an old save's first year can't spend it
        self.assertIn("has_local_variable = te_cc_had_reading", self.body)
        update = _squash(_top_blocks(_read(EFFECTS))["te_cc_yearly_update"])
        self.assertTrue(update.startswith("if = { limit = { has_variable = te_cc_slack } "
                                          "set_local_variable = { name = te_cc_had_reading value = 1 } }"), update[:120])
        self.assertIn("te_country_walked_workforce >= 100000", self.body)
        self.assertIn("var:te_cc_slack >= 0.02", self.body)
        self.assertIn("var:te_cc_slack <= 0.98", self.body)

    def test_it_recounts_by_the_walks_own_rule(self):
        self.assertIn("every_scope_state = { every_scope_pop = { te_unemp_count_pop = yes } }", self.body)
        # a peasant count of 0 reads BROKEN: the recount shares the walk's rule, so only this catches a dead branch.
        # 10 points, not 5: a new game's first year moves the peasant share 5.3 points (log triage 2026-10-25)
        self.assertIn("var:te_cc_chk_diff <= 0.10 var:te_cc_chk_diff >= -0.10 var:te_cc_chk_fresh_peasants > 0",
                      self.body)
        self.assertIn("TE_SELF_CHECK OK construction_slack_read", self.body)
        self.assertIn("TE_SELF_CHECK BROKEN construction_slack_read", self.body)

    def test_it_cleans_up(self):
        for name in ("te_cc_chk_fresh", "te_cc_chk_fresh_peasants", "te_cc_chk_wf", "te_cc_chk_walked_wf",
                     "te_cc_chk_target", "te_cc_chk_diff"):
            self.assertIn("set_variable = { name = " + name, self.body)
            self.assertIn("remove_variable = " + name, self.body)


if __name__ == "__main__":
    unittest.main()
