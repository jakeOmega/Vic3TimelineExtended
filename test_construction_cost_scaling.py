# -*- coding: utf-8 -*-
"""Construction Cost Scaling: the GDP part times the share of it that applies, which follows slack (#1034 follow-up),
its own factor capped at a tenth a year, and the optional small-economy factor (2026-11-13).

The share is 1 at slack (peasants and unemployed over the workforce) construction_cost_slack_full or less, 0 at
construction_cost_slack_none or more, a straight line between, and moves construction_cost_slack_ease of the way
toward that at each yearly pulse (te_cc_yearly_update). The scripts/analysis tools model the same rule
(econ_growth_sim.slack_target and eased_slack_factor); these tests keep the script's arithmetic, its wiring and its
self-check whole, and the two in step. The engine reports none of it.

The scaling's own factor, one plus the GDP part times the share, is stored at the pulse (var:te_cc_scale) and moves
at most construction_cost_max_yearly_move of itself a year: a step in the share of a rich country moved every
building's use of the construction good on one day. Under te_small_economy_construction_rule (off by default) the
factor is multiplied by one that runs from construction_cost_small_economy_min_factor at no GDP to 1 at
construction_cost_small_economy_full_gdp, which the cap does not touch. TheCapAndTheSmallEconomy runs the script's
own text (the values, te_cc_yearly_update and te_cc_apply_market) with the evaluator of
test_construction_market_budget_step.
"""

import os
import re
import unittest

from scripts.analysis import econ_growth_sim as G
from scripts.analysis import econ_sim_data as D
from test_construction_market_budget_step import Env, parse_block, tokenize
from test_unemployment_share import REPO, _body, _read, _squash, _top_blocks

VALUES = os.path.join(REPO, "common", "script_values", "extra_script_values.txt")
COUNTRY_VALUES = os.path.join(REPO, "common", "script_values", "te_unemployment_values.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_construction_cost_effects.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "extra_on_actions.txt")
START_HOOK = os.path.join(REPO, "common", "on_actions", "te_construction_market_on_actions.txt")
START_EVENTS = os.path.join(REPO, "events", "te_construction_market_recalc_events.txt")
RULES = os.path.join(REPO, "common", "game_rules", "extra_game_rules.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "te_construction_cost_triggers.txt")
MARKET_PRICE = os.path.join(REPO, "common", "script_values", "te_construction_market_current_values.txt")
MARKET_TARGETS = os.path.join(REPO, "common", "script_values", "te_construction_market_target_values.txt")
RULE_LOC = os.path.join(REPO, "localization", "english", "te_game_rules_l_english.yml")
MISC_LOC = os.path.join(REPO, "localization", "english", "te_miscellaneous_l_english.yml")


def _value(text, name):
    return _squash(_body(text, name))


class TheArithmetic(unittest.TestCase):
    def setUp(self):
        self.values = _read(VALUES)

    def test_every_reader_takes_the_product(self):
        # X: the scaling's own factor in force (capped a year) times the small-economy factor in force, less one.
        self.assertEqual(_value(self.values, "construction_cost_scaling_mult"),
                         "value = te_cc_scale_now multiply = te_cc_small_factor_now subtract = 1")
        self.assertEqual(_value(self.values, "te_cc_scale_target"),
                         "value = te_cc_gdp_part_now multiply = te_cc_slack_factor_now add = 1")
        # stored figures once the pulse has run; before it, the scaling already in force
        self.assertEqual(_value(self.values, "te_cc_scale_now"),
                         "value = te_cc_scale_target if = { limit = { has_variable = te_cc_scale } "
                         "value = var:te_cc_scale }")
        self.assertEqual(_value(self.values, "te_cc_small_factor_now"),
                         "value = 1 if = { limit = { has_variable = te_cc_small_factor } "
                         "value = var:te_cc_small_factor }")

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
                         "value = te_cc_total_factor divide = { value = te_cc_scaling_factor "
                         "min = construction_cost_small_economy_min_factor }")
        self.assertIn("modifier:country_construction_goods_cost_mult", _value(self.values, "te_cc_modifier_total"))
        # the scaling in force: one plus the X every reader takes
        self.assertEqual(_value(self.values, "te_cc_scaling_factor"),
                         "value = construction_cost_scaling_mult add = 1")
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
        # The factor: a country with none stored gets the scaling in force BEFORE the share moves (a save from
        # before the cap must not jump), and the capped move comes after the share and the GDP part are stored.
        first = ("if = { limit = { NOT = { has_variable = te_cc_scale } } "
                 "set_variable = { name = te_cc_scale value = te_cc_scale_target } }")
        move = "set_variable = { name = te_cc_scale value = te_cc_scale_next }"
        self.assertIn(first, body)
        self.assertIn(move, body)
        self.assertLess(body.index(first), body.index("te_cc_slack_factor_eased"))
        self.assertLess(body.index("name = te_cc_gdp_part"), body.index(move))
        self.assertIn("set_variable = { name = te_cc_small_factor value = te_cc_small_economy_factor }", body)

    def test_the_pulse_and_the_game_start_share_the_two_apply_effects(self):
        # One refresh site a modifier: the on_action picks a half by the rule, and the game-start pass calls the
        # same two.
        body = _squash(_body(_read(ON_ACTIONS), "construction_cost_scaling_on_action"))
        self.assertTrue(body.endswith("if = { limit = { te_free_market_construction_off = yes } "
                                      "te_cc_apply_direct = yes } else = { te_cc_apply_market = yes } }"), body[-160:])
        self.assertNotIn("add_modifier", body)
        effects = _top_blocks(_read(EFFECTS))
        for name, modifier in (("te_cc_apply_direct", "construction_cost_scaling_direct"),
                               ("te_cc_apply_market", "construction_cost_scaling")):
            block = _squash(effects[name])
            self.assertIn("remove_modifier = " + modifier + " ", block)
            self.assertIn("add_modifier = { name = " + modifier + " ", block)
            # a negative multiplier (the small-economy rule) must reach the modifier
            self.assertNotIn("> 0", block)
        start = _squash(effects["te_cc_game_start_country"])
        self.assertIn("te_cc_yearly_update = yes", start)
        self.assertIn("te_cc_apply_direct = yes", start)
        self.assertIn("te_cc_apply_market = yes", start)

    def test_the_tooltip_reads_stored_figures_only(self):
        # A GUI read that iterated every state would run every frame: the tooltip's values read variables.
        values = _read(VALUES)
        for name in ("te_cc_slack_now", "te_cc_peasants_now", "te_cc_unemployed_now", "te_cc_slack_target",
                     "te_cc_gdppc_now", "te_cc_gdp_part_now", "te_cc_scaling_factor", "te_cc_others_factor",
                     "te_cc_total_factor", "te_cc_modifier_total", "te_cc_other_sources", "te_cc_direct_rule",
                     "te_cc_has_reading", "te_cc_slack_factor_now", "te_cc_slack_factor_carried",
                     "te_cc_scale_now", "te_cc_scale_target", "te_cc_small_factor_now",
                     "te_cc_small_factor_applies", "construction_cost_scaling_mult"):
            body = _value(values, name)
            self.assertNotIn("every_", body, name)
            self.assertNotIn("te_country_", body, name)
        # ... and the small-economy factor in force, not today's GDP: only the pulse reads te_cc_small_economy_factor
        for name in ("construction_cost_scaling_mult", "te_cc_scaling_factor", "te_cc_small_factor_now",
                     "te_cc_small_factor_applies"):
            self.assertNotIn("te_cc_small_economy_factor", _value(values, name), name)


# ---------------------------------------------------------------------------
# The cap and the small-economy factor, by running the script's own text.
# ---------------------------------------------------------------------------
CONSTANTS = ("construction_cost_gdppc_reference", "construction_cost_floor_ratio", "construction_cost_ceiling_ratio",
             "construction_cost_max_mult", "construction_cost_slack_full", "construction_cost_slack_none",
             "construction_cost_slack_ease", "construction_cost_max_yearly_move",
             "construction_cost_small_economy_min_factor", "construction_cost_small_economy_full_gdp")
NAMED = ("construction_cost_gdppc_floor", "construction_cost_gdppc_ceiling", "construction_cost_scaling_gdp_mult",
         "te_cc_slack_factor_now", "te_cc_slack_factor_carried", "te_cc_slack_now", "te_cc_slack_target",
         "te_cc_slack_factor_eased", "te_cc_scale_target", "te_cc_scale_now", "te_cc_scale_next",
         "te_cc_small_economy_factor", "te_cc_small_factor_now", "te_cc_small_factor_applies",
         "construction_cost_scaling_mult", "te_cc_modifier_total", "te_cc_other_sources", "te_cc_gdp_part_now",
         "te_cc_scaling_factor", "construction_cost_scaling_adjusted_mult",
         "construction_cost_scaling_direct_adjusted_mult")


def _parse(text):
    return parse_block(tokenize(text), 0)[0]


class Country:
    """A country's variables, modifiers and engine figures, with the script's values and effects run over them."""

    def __init__(self, rule=False, gdp=50e6, gdppc=1.0, slack=0.5, walked=1e6, others=0.0, **variables):
        text = _read(VALUES)
        self.constants = {name: float(re.search(r"^%s\s*=\s*([\d.]+)" % name, text, re.M).group(1))
                          for name in CONSTANTS}
        self.values = {name: _parse(_body(text, name)) for name in NAMED}
        self.values["te_construction_market_goods_per_point"] = _parse(
            _body(_read(MARKET_TARGETS), "te_construction_market_goods_per_point"))
        blocks = _top_blocks(_read(EFFECTS))  # not the self-checks: their log lines are not script
        self.effects = {name: _parse(blocks[name])
                        for name in ("te_cc_yearly_update", "te_cc_apply_market", "te_cc_apply_direct")}
        self.rule, self.gdp, self.gdppc, self.slack, self.walked, self.others = rule, gdp, gdppc, slack, walked, others
        self.variables = dict(variables)
        self.modifiers = {}  # the scaling's two modifiers: name -> multiplier
        self.seen = None     # what a modifier: read returns while an effect runs

    def env(self):
        own = sum(self.modifiers.values()) if self.seen is None else self.seen
        env = Env.__new__(Env)
        env.memo = {}
        env.constants, env.values = self.constants, self.values
        env.names = {
            "gdp": self.gdp, "country_gdp_per_capita": self.gdppc,
            "te_country_walked_workforce": self.walked, "te_country_slack_share": self.slack,
            "te_country_peasant_share": self.slack,
            "modifier:goods_input_construction_mult": self.others + own,
            "modifier:country_construction_goods_cost_mult": self.others + own,
        }
        env.variables = self.variables
        env.flags = {"te_small_economy_construction_on": self.rule, "te_free_market_construction_off": False}
        env.triggers = {}
        return env

    def value(self, name):
        return self.env().value(name)

    def run(self, name):
        # add_modifier and remove_modifier are not visible to a modifier: read inside the same effect, which is
        # why the adjusted multipliers back var:prior_construction_scaling out of the read.
        self.seen = sum(self.modifiers.values())
        try:
            self._run(self.effects[name])
        finally:
            self.seen = None

    def _run(self, items):
        done = False
        for key, _op, val in items:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    done = False
                if not done:
                    limit = next((v for k, _o, v in val if k == "limit"), None)
                    if limit is None or self.env().cond(limit):
                        self._run([item for item in val if item[0] != "limit"])
                        done = True
            elif key == "set_variable":
                fields = {k: v for k, _o, v in val}
                self.variables[fields["name"]] = self.env().operand(fields["value"])
            elif key == "remove_modifier":
                self.modifiers.pop(val, None)
            elif key == "add_modifier":
                fields = {k: v for k, _o, v in val}
                self.modifiers[fields["name"]] = self.env().operand(fields["multiplier"])
            elif key in ("set_local_variable", "te_cc_slack_selfcheck"):
                pass  # the self-check's own state
            else:
                raise AssertionError("the effect runner does not know %r" % key)

    def pulse(self):
        self.run("te_cc_yearly_update")
        self.run("te_cc_apply_market")
        return self.variables["te_cc_scale"]


class TheCapAndTheSmallEconomy(unittest.TestCase):
    def test_the_constants(self):
        c = Country().constants
        self.assertEqual(c["construction_cost_max_yearly_move"], 0.1)
        self.assertEqual(c["construction_cost_small_economy_min_factor"], 0.1)
        self.assertEqual(c["construction_cost_small_economy_full_gdp"], 10e6)

    def test_the_factor_rises_a_tenth_a_year(self):
        # Full employment in a rich country: the share is already 1, the GDP part +100%, so the target is 2.
        country = Country(gdppc=10.9, slack=0.0, te_cc_scale=1.0, te_cc_slack_factor=1.0, te_cc_gdp_part=1.0)
        self.assertAlmostEqual(country.value("te_cc_scale_target"), 2.0, places=3)
        seen = [country.pulse() for _ in range(9)]
        for year, factor in enumerate(seen[:7], start=1):
            self.assertAlmostEqual(factor, 1.1 ** year, places=3, msg=year)
        self.assertAlmostEqual(seen[7], 2.0, places=3)  # arrives: 1.1 ** 8 is past it
        self.assertAlmostEqual(seen[8], 2.0, places=3)  # and stays
        # the modifier in force is the factor less one
        self.assertAlmostEqual(country.modifiers["construction_cost_scaling"], 1.0, places=3)

    def test_the_factor_falls_a_tenth_a_year(self):
        # The same country with idle labour: the share eases to 0, the target toward 1.
        country = Country(gdppc=10.9, slack=0.5, te_cc_scale=2.0, te_cc_slack_factor=0.0, te_cc_gdp_part=1.0)
        self.assertAlmostEqual(country.pulse(), 1.8, places=4)
        self.assertAlmostEqual(country.pulse(), 1.62, places=4)
        for _ in range(8):
            last = country.pulse()
        self.assertAlmostEqual(last, 1.0, places=4)
        self.assertNotIn("construction_cost_scaling", country.modifiers)  # no modifier at X = 0

    def test_a_move_inside_the_cap_is_taken_whole(self):
        # GDP part +30%, share 0.9 easing toward 1: the target is 1 + 0.3 x 0.9333, under a tenth above 1.25.
        country = Country(gdppc=3.97, slack=0.0, te_cc_scale=1.25, te_cc_slack_factor=0.9, te_cc_gdp_part=0.3)
        self.assertAlmostEqual(country.pulse(), 1 + 0.3 * (0.9 + 0.1 * 0.33333), places=3)

    def test_a_new_game_starts_from_one(self):
        # No variable at all. The share eases from 0 toward 1 (a third), the GDP part is +60%: the target is 1.2,
        # and the first move is capped from 1, the scaling in force in a new game.
        country = Country(gdppc=6.94, slack=0.0)
        self.assertAlmostEqual(country.value("construction_cost_scaling_mult"), 0.0, places=5)
        self.assertAlmostEqual(country.pulse(), 1.1, places=3)
        self.assertAlmostEqual(country.variables["te_cc_slack_factor"], 0.33333, places=4)

    def test_a_save_from_before_the_cap_moves_from_the_scaling_in_force(self):
        # The pulse of the older version stored a share of 0.9 and a GDP part of +200%: 2.8 in force, with no
        # stored factor. Now labour is idle and the share drops to 0.6: the target is 2.2, the factor 2.8 x 0.9.
        country = Country(gdppc=20.8, slack=0.5, te_cc_slack_factor=0.9, te_cc_gdp_part=2.0, te_cc_slack=0.0,
                          prior_construction_scaling=1.8)
        country.modifiers["construction_cost_scaling"] = 1.8
        self.assertAlmostEqual(country.value("construction_cost_scaling_mult"), 1.8, places=4)  # what readers take
        self.assertAlmostEqual(country.pulse(), 2.52, places=3)
        self.assertAlmostEqual(country.modifiers["construction_cost_scaling"], 1.52, places=3)

    def test_a_save_from_before_the_slack_rule_too(self):
        # Only the old modifier's value: +50% at a GDP part of +100%, so the carried share is a half and the
        # scaling in force 1.5. Full employment: the target is 1 + 1 x (0.5 + 0.5 / 3), capped at 1.65.
        country = Country(gdppc=10.9, slack=0.0, prior_construction_scaling=0.5)
        country.modifiers["construction_cost_scaling"] = 0.5
        self.assertAlmostEqual(country.value("te_cc_scale_now"), 1.5, places=3)
        self.assertAlmostEqual(country.pulse(), 1.65, places=3)

    def test_the_small_economy_factor(self):
        for gdp, factor in ((0, 0.1), (1e6, 0.19), (5e6, 0.55), (10e6, 1.0), (80e6, 1.0)):
            with self.subTest(gdp=gdp):
                self.assertAlmostEqual(Country(rule=True, gdp=gdp).value("te_cc_small_economy_factor"), factor,
                                       places=4)
                self.assertEqual(Country(rule=False, gdp=gdp).value("te_cc_small_economy_factor"), 1.0)

    def test_the_factor_in_force_is_the_stored_one(self):
        # A rule switched in a running game reaches a country at its next pulse, with the modifier.
        self.assertEqual(Country(rule=True, gdp=1e6).value("te_cc_small_factor_now"), 1.0)
        self.assertEqual(Country(rule=True, gdp=1e6).value("construction_cost_scaling_mult"), 0.0)
        country = Country(rule=False, gdp=1e6, te_cc_small_factor=0.19, te_cc_scale=1.0)
        self.assertAlmostEqual(country.value("construction_cost_scaling_mult"), -0.81, places=4)
        country.pulse()  # the rule is off now
        self.assertEqual(country.variables["te_cc_small_factor"], 1.0)
        self.assertAlmostEqual(country.value("construction_cost_scaling_mult"), 0.0, places=5)

    def test_a_small_economy_gets_a_negative_modifier_at_once(self):
        # A poor small country, rule on: no cap on the small-economy factor, so the first application is the
        # whole discount.
        country = Country(rule=True, gdp=1e6, gdppc=0.4, slack=0.6)
        country.pulse()
        self.assertAlmostEqual(country.variables["te_cc_scale"], 1.0, places=5)
        self.assertAlmostEqual(country.variables["te_cc_small_factor"], 0.19, places=4)
        self.assertAlmostEqual(country.modifiers["construction_cost_scaling"], -0.81, places=4)
        self.assertAlmostEqual(country.variables["prior_construction_scaling"], -0.81, places=4)
        self.assertAlmostEqual(country.value("te_construction_market_goods_per_point"), 0.19, places=4)
        self.assertEqual(country.value("te_cc_small_factor_applies"), 1.0)

    def test_the_discount_multiplies_with_the_other_modifiers(self):
        # +20% from elsewhere: the total is 1.2 x 0.19 - 1, above -1 because both factors are positive.
        country = Country(rule=True, gdp=1e6, gdppc=0.4, slack=0.6, others=0.2)
        country.pulse()  # the first run adds the raw X
        country.pulse()  # the next one sets it to multiply with the rest
        total = country.others + country.modifiers["construction_cost_scaling"]
        self.assertAlmostEqual(total, 1.2 * 0.19 - 1, places=4)
        self.assertAlmostEqual(country.value("te_cc_scaling_factor"), 0.19, places=4)

    def test_the_discount_and_the_scaling_multiply(self):
        # A small rich country at full employment: the scaling's factor 1.5 in force, the small factor 0.55.
        country = Country(rule=True, gdp=5e6, gdppc=10.9, slack=0.0, te_cc_scale=1.5, te_cc_slack_factor=0.5,
                          te_cc_gdp_part=1.0)
        self.assertAlmostEqual(country.pulse(), 1.65, places=3)
        self.assertAlmostEqual(country.value("construction_cost_scaling_mult"), 1.65 * 0.55 - 1, places=3)

    def test_the_market_price_and_goods_per_point_follow_the_discount_to_its_floor(self):
        for path, name in ((MARKET_PRICE, "te_construction_market_price"),
                           (MARKET_TARGETS, "te_construction_market_goods_per_point")):
            body = _value(_read(path), name)
            self.assertIn("add = construction_cost_scaling_mult", body, name)
            self.assertIn("min = construction_cost_small_economy_min_factor", body, name)
            self.assertNotIn("min = 1", body, name)
        country = Country(te_cc_scale=1.0, te_cc_small_factor=0.02)  # below the floor, however it got there
        self.assertAlmostEqual(country.value("te_construction_market_goods_per_point"), 0.1, places=5)


class TheSmallEconomyRule(unittest.TestCase):
    def test_off_by_default_and_read_positively(self):
        rule = _squash(_body(_read(RULES), "te_small_economy_construction_rule"))
        self.assertTrue(rule.startswith("default = te_small_economy_construction_disabled "), rule[:80])
        for setting in ("te_small_economy_construction_enabled", "te_small_economy_construction_disabled"):
            self.assertIn(setting + " = { flag = " + setting + " }", rule)
        # a save from before the rule stores neither flag, and must read as off
        self.assertEqual(_squash(_body(_read(TRIGGERS), "te_small_economy_construction_on")),
                         "has_game_rule = te_small_economy_construction_enabled")
        for folder in ("common", "events"):
            for root, _dirs, files in os.walk(os.path.join(REPO, folder)):
                for name in files:
                    path = os.path.join(root, name)
                    if name.endswith(".txt") and path not in (RULES, TRIGGERS):
                        self.assertNotIn("has_game_rule = te_small_economy_construction", _read(path), path)

    def test_it_is_applied_at_game_start_through_a_country_event(self):
        # ROOT is none in on_game_started_after_lobby and add_modifier's multiplier resolves against ROOT.
        hook = _squash(_body(_read(START_HOOK), "te_construction_market_on_game_started_after_lobby"))
        self.assertIn("te_direct_construction_convert_sectors = yes te_cc_game_start = yes", hook)
        effects = _top_blocks(_read(EFFECTS))
        start = _squash(effects["te_cc_game_start"])
        self.assertTrue(start.startswith("if = { limit = { te_small_economy_construction_on = yes } "), start[:80])
        self.assertIn("every_country = {", start)
        self.assertIn("trigger_event = { id = te_construction_market_recalc_events.3 }", start)
        self.assertNotIn("add_modifier", start)
        event = _squash(_body(_read(START_EVENTS), "te_construction_market_recalc_events.3"))
        self.assertEqual(event, "type = country_event hidden = yes immediate = { te_cc_game_start_country = yes }")
        country = _squash(effects["te_cc_game_start_country"])
        # once a country, and never on a GDP the engine has not computed (it would read as the largest discount)
        self.assertIn("NOT = { has_variable = te_cc_small_factor }", country)
        self.assertIn("if = { limit = { gdp > 0 } te_cc_yearly_update = yes", country)
        self.assertIn("trigger_event = { id = te_construction_market_recalc_events.3 days = 7 }", country)

    def test_the_text_names_the_figures_the_script_uses(self):
        constants = Country().constants
        self.assertEqual(constants["construction_cost_small_economy_min_factor"], 0.1)  # "a tenth"
        self.assertEqual(constants["construction_cost_small_economy_full_gdp"], 10e6)   # "10 million"
        with open(RULE_LOC, encoding="utf-8-sig") as f:
            rules = f.read()
        desc = re.search(r'setting_te_small_economy_construction_enabled_desc:0 "([^"]*)"', rules).group(1)
        self.assertTrue(desc.startswith("Experimental. "), desc)
        for phrase in ("a tenth", "10 million", "AI countries"):
            self.assertIn(phrase, desc)
        with open(MISC_LOC, encoding="utf-8-sig") as f:
            misc = f.read()
        small = re.search(r'te_nation_construction_scale_small:0 "([^\n]*)"', misc).group(1)
        self.assertIn("10 million", small)
        self.assertIn("te_cc_small_factor_now", small)
        for key in ("te_nation_construction_row_tt", "te_nation_ov_construction_tt"):
            line = re.search(key + r':0 "([^\n]*)"', misc).group(1)
            self.assertIn("'te_nation_construction_scale_small', 'te_nation_construction_scale_plain'", line, key)
            self.assertIn("construction_cost_max_yearly_move", line, key)


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
