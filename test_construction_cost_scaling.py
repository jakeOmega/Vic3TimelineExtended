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
factor is multiplied by one that runs from the setting's factor at no GDP (construction_cost_small_economy_mild_factor,
_standard_factor or _strong_factor) to 1 at construction_cost_small_economy_full_gdp, which the cap does not touch.
TheCapAndTheSmallEconomy and TheStrengths run the script's own text (the values, the rule's triggers,
te_cc_yearly_update and te_cc_apply_scaling) with the evaluator of test_construction_market_budget_step, reading
has_game_rule against the setting a test picks.
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
STATIC = os.path.join(REPO, "common", "static_modifiers", "extra_modifiers.txt")
WEEKLY_PULSE = os.path.join(REPO, "common", "scripted_effects", "te_construction_market_pulse_effects.txt")


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
        self.assertIn("set_variable = { name = te_cc_small_factor value = te_cc_small_economy_factor } "
                      "set_variable = { name = te_cc_small_min value = te_cc_small_economy_min_factor }", body)

    def test_the_pulse_and_the_game_start_share_the_apply_effect(self):
        # One refresh site: the pulse, the rule switch (test_construction_rule_switch.py) and the game-start pass
        # all call te_cc_apply_scaling.
        body = _squash(_body(_read(ON_ACTIONS), "construction_cost_scaling_on_action"))
        self.assertTrue(body.endswith("te_cc_apply_scaling = yes }"), body[-80:])
        self.assertNotIn("add_modifier", body)
        effects = _top_blocks(_read(EFFECTS))
        block = _squash(effects["te_cc_apply_scaling"])
        for modifier in ("construction_cost_scaling_direct", "construction_cost_scaling"):
            self.assertIn("remove_modifier = " + modifier + " ", block)
            self.assertIn("add_modifier = { name = " + modifier + " ", block)
        # a negative multiplier (the small-economy rule) must reach the modifier
        self.assertNotIn("> 0", block)
        start = _squash(effects["te_cc_game_start_country"])
        self.assertIn("te_cc_yearly_update = yes te_cc_apply_scaling = yes", start)

    def test_the_tooltip_reads_stored_figures_only(self):
        # A GUI read that iterated every state would run every frame: the tooltip's values read variables.
        values = _read(VALUES)
        for name in ("te_cc_slack_now", "te_cc_peasants_now", "te_cc_unemployed_now", "te_cc_slack_target",
                     "te_cc_gdppc_now", "te_cc_gdp_part_now", "te_cc_scaling_factor", "te_cc_others_factor",
                     "te_cc_total_factor", "te_cc_modifier_total", "te_cc_other_sources", "te_cc_direct_rule",
                     "te_cc_has_reading", "te_cc_slack_factor_now", "te_cc_slack_factor_carried",
                     "te_cc_scale_now", "te_cc_scale_target", "te_cc_small_factor_now",
                     "te_cc_small_factor_applies", "te_cc_small_min_now", "te_cc_small_setting_changed",
                     "te_cc_small_economy_min_factor", "construction_cost_scaling_mult"):
            body = _value(values, name)
            self.assertNotIn("every_", body, name)
            self.assertNotIn("te_country_", body, name)
        # ... and the small-economy factor in force, not today's GDP: only the pulse reads te_cc_small_economy_factor
        for name in ("construction_cost_scaling_mult", "te_cc_scaling_factor", "te_cc_small_factor_now",
                     "te_cc_small_factor_applies", "te_cc_small_min_now", "te_cc_small_setting_changed"):
            self.assertNotIn("te_cc_small_economy_factor", _value(values, name), name)
        # the setting's minimum reads the game rule only (through its triggers), never the country's GDP
        self.assertNotIn("gdp", _value(values, "te_cc_small_economy_min_factor"))


# ---------------------------------------------------------------------------
# The cap and the small-economy factor, by running the script's own text.
# ---------------------------------------------------------------------------
CONSTANTS = ("construction_cost_gdppc_reference", "construction_cost_floor_ratio", "construction_cost_ceiling_ratio",
             "construction_cost_max_mult", "construction_cost_slack_full", "construction_cost_slack_none",
             "construction_cost_slack_ease", "construction_cost_max_yearly_move",
             "construction_cost_small_economy_min_factor", "construction_cost_small_economy_full_gdp",
             "construction_cost_small_economy_mild_factor", "construction_cost_small_economy_standard_factor",
             "construction_cost_small_economy_strong_factor")
NAMED = ("construction_cost_gdppc_floor", "construction_cost_gdppc_ceiling", "construction_cost_scaling_gdp_mult",
         "te_cc_slack_factor_now", "te_cc_slack_factor_carried", "te_cc_slack_now", "te_cc_slack_target",
         "te_cc_slack_factor_eased", "te_cc_scale_target", "te_cc_scale_now", "te_cc_scale_next",
         "te_cc_small_economy_min_factor", "te_cc_small_economy_factor", "te_cc_small_factor_now",
         "te_cc_small_factor_applies", "te_cc_small_min_now", "te_cc_small_setting_changed",
         "construction_cost_scaling_mult", "te_cc_modifier_total", "te_cc_other_sources", "te_cc_gdp_part_now",
         "te_cc_scaling_factor", "construction_cost_scaling_adjusted_mult",
         "construction_cost_scaling_direct_adjusted_mult")

# The rule's settings, as a test names them, and the setting name has_game_rule reads. True is the rule's one "on"
# setting before the strengths (2026-11-13), kept under its name as the strongest.
RULE_PREFIX = "te_small_economy_construction_"
SETTINGS = {False: RULE_PREFIX + "disabled", True: RULE_PREFIX + "enabled", "disabled": RULE_PREFIX + "disabled",
            "mild": RULE_PREFIX + "mild", "standard": RULE_PREFIX + "standard", "strong": RULE_PREFIX + "enabled",
            None: None}  # None: a save from before the rule, which stores no setting for it
# The factor at no GDP each setting is meant to give, as the rules screen says it.
MINIMUM = {"disabled": 1.0, "mild": 0.5, "standard": 0.2, "strong": 0.1}


def _parse(text):
    return parse_block(tokenize(text), 0)[0]


class _CountryEnv(Env):
    """Env, with has_modifier (the scaling's modifiers the country held when the effect began: a modifier change is
    not visible inside the effect that makes it) and has_game_rule (the setting the test picked)."""

    def one_cond(self, key, op, val):
        if key == "has_modifier":
            return val in self.held
        if key == "is_country_type":
            return val == self.country_type
        if key == "has_game_rule":
            return val == self.setting
        return super().one_cond(key, op, val)


class Country:
    """A country's variables, modifiers and engine figures, with the script's values and effects run over them.

    rule picks the setting of te_small_economy_construction_rule (SETTINGS), and the rule's own scripted triggers
    (te_construction_cost_triggers.txt) are run against it, so a test of a setting also tests how the script reads it.
    Assign .rule between steps to switch the rule in a running game."""

    def __init__(self, rule=False, gdp=50e6, gdppc=1.0, slack=0.5, walked=1e6, others=0.0, direct=False,
                 country_type="recognized", **variables):
        text = _read(VALUES)
        self.constants = {name: float(re.search(r"^%s\s*=\s*([\d.]+)" % name, text, re.M).group(1))
                          for name in CONSTANTS}
        self.values = {name: _parse(_body(text, name)) for name in NAMED}
        self.values["te_construction_market_goods_per_point"] = _parse(
            _body(_read(MARKET_TARGETS), "te_construction_market_goods_per_point"))
        blocks = _top_blocks(_read(EFFECTS))  # not the self-checks: their log lines are not script
        self.effects = {name: _parse(blocks[name])
                        for name in ("te_cc_yearly_update", "te_cc_apply_scaling", "te_cc_weekly_new_country")}
        self.rule_triggers = {name: _parse(body) for name, body in _top_blocks(_read(TRIGGERS)).items()}
        self.country_type = country_type
        self.rule, self.gdp, self.gdppc, self.slack, self.walked, self.others = rule, gdp, gdppc, slack, walked, others
        self.direct = direct  # free_market_construction_rule disabled
        self.variables = dict(variables)
        self.modifiers = {}  # the scaling's two modifiers: name -> multiplier
        self.seen = None     # what a modifier: read returns while an effect runs
        self.held = None     # the modifiers has_modifier sees while an effect runs

    def env(self):
        own = sum(self.modifiers.values()) if self.seen is None else self.seen
        env = _CountryEnv.__new__(_CountryEnv)
        env.held = set(self.modifiers) if self.held is None else self.held
        env.country_type = self.country_type
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
        env.setting = SETTINGS[self.rule]
        env.flags = {"te_free_market_construction_off": self.direct}
        env.triggers = {name: (lambda body=body: env.cond(body)) for name, body in self.rule_triggers.items()}
        return env

    def value(self, name):
        return self.env().value(name)

    def run(self, name):
        # add_modifier and remove_modifier are not visible to a modifier: read inside the same effect, which is
        # why the adjusted multipliers back var:prior_construction_scaling out of the read.
        self.seen = sum(self.modifiers.values())
        self.held = set(self.modifiers)
        try:
            self._run(self.effects[name])
        finally:
            self.seen = self.held = None

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
            elif key == "remove_variable":
                self.variables.pop(val, None)
            elif key == "add_modifier":
                fields = {k: v for k, _o, v in val}
                self.modifiers[fields["name"]] = self.env().operand(fields["multiplier"])
            elif key in ("set_local_variable", "te_cc_slack_selfcheck"):
                pass  # the self-check's own state
            elif key in self.effects and val == "yes":
                self._run(self.effects[key])
            else:
                raise AssertionError("the effect runner does not know %r" % key)

    def pulse(self):
        self.run("te_cc_yearly_update")
        self.run("te_cc_apply_scaling")
        return self.variables["te_cc_scale"]


class TheCapAndTheSmallEconomy(unittest.TestCase):
    def test_the_constants(self):
        c = Country().constants
        self.assertEqual(c["construction_cost_max_yearly_move"], 0.1)
        self.assertEqual(c["construction_cost_small_economy_mild_factor"], 0.5)
        self.assertEqual(c["construction_cost_small_economy_standard_factor"], 0.2)
        self.assertEqual(c["construction_cost_small_economy_strong_factor"], 0.1)
        self.assertEqual(c["construction_cost_small_economy_full_gdp"], 10e6)
        # The floor of the price and goods per point is the lowest any setting gives, not the setting in force's:
        # after a switch to a milder setting a country keeps its stronger factor until its next pulse.
        self.assertEqual(c["construction_cost_small_economy_min_factor"],
                         min(c["construction_cost_small_economy_%s_factor" % s] for s in ("mild", "standard", "strong")))

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

    def test_a_small_economy_in_a_direct_game(self):
        # free_market_construction_rule disabled: the same discount, on the direct lever.
        country = Country(rule=True, gdp=1e6, gdppc=0.4, slack=0.6, direct=True, others=0.2)
        country.pulse()
        country.pulse()
        self.assertNotIn("construction_cost_scaling", country.modifiers)
        total = country.others + country.modifiers["construction_cost_scaling_direct"]
        self.assertAlmostEqual(total, 1.2 * 0.19 - 1, places=4)

    def test_the_discount_and_the_scaling_multiply(self):
        # A small rich country at full employment: the scaling's factor 1.5 in force, the small factor 0.55.
        country = Country(rule=True, gdp=5e6, gdppc=10.9, slack=0.0, te_cc_scale=1.5, te_cc_slack_factor=0.5,
                          te_cc_gdp_part=1.0)
        self.assertAlmostEqual(country.pulse(), 1.65, places=3)
        self.assertAlmostEqual(country.value("construction_cost_scaling_mult"), 1.65 * 0.55 - 1, places=3)

    def test_a_revolutions_winner_gets_the_scaling_it_is_owed(self):
        # A revolution's winner inherits the loser's variables and none of its modifiers, so it arrives with
        # var:prior_construction_scaling and without the modifier the prior stands for. Backing the prior out of
        # a modifier read that never held it shrank a positive scaling for a year and carried a small economy's
        # negative one past -1 (review of #1770). The prior is set to 0, which is what the winner holds, so it
        # gets at once what an ordinary country has from its second pulse: X times one plus the other sources.
        cases = (
            dict(rule=True, gdp=2e6, gdppc=0.4, slack=0.6, others=0.2, te_cc_scale=1.0, te_cc_small_factor=0.28),
            dict(rule=False, gdp=50e6, gdppc=10.9, slack=0.0, others=0.2, te_cc_scale=2.0, te_cc_small_factor=1.0),
        )
        for direct in (False, True):
            name = "construction_cost_scaling_direct" if direct else "construction_cost_scaling"
            for case in cases:
                with self.subTest(direct=direct, rule=case["rule"]):
                    x = case["te_cc_scale"] * case["te_cc_small_factor"] - 1
                    winner = Country(direct=direct, prior_construction_scaling=x, **case)
                    self.assertEqual(winner.modifiers, {})
                    winner.run("te_cc_apply_scaling")
                    self.assertAlmostEqual(winner.modifiers[name], x * (1 + winner.others), places=5)
                    self.assertAlmostEqual(winner.variables["prior_construction_scaling"], winner.modifiers[name],
                                           places=5)
                    # the cost in force is the two factors multiplied, above nothing
                    self.assertAlmostEqual(1 + winner.others + winner.modifiers[name],
                                           (1 + winner.others) * (1 + x), places=5)
                    self.assertGreater(1 + winner.others + winner.modifiers[name], 0)
                    # the same as a settled country of the same figures, which took two pulses to get there
                    settled = Country(direct=direct, **case)
                    settled.run("te_cc_apply_scaling")
                    settled.run("te_cc_apply_scaling")
                    self.assertAlmostEqual(winner.modifiers[name], settled.modifiers[name], places=5)
                    # and it stays there
                    winner.run("te_cc_apply_scaling")
                    self.assertAlmostEqual(winner.modifiers[name], x * (1 + winner.others), places=5)
        # The variable is set, never removed: the direct modifier's multiplier is the variable itself, which
        # the engine reads again on later ticks (modifier_multiplier_var_audit).
        self.assertNotIn("remove_variable", _squash(_top_blocks(_read(EFFECTS))["te_cc_apply_scaling"]))

    def test_a_prior_with_its_modifier_is_kept(self):
        # The ordinary country: the prior is backed out of the modifier that holds it.
        country = Country(rule=True, gdp=1e6, gdppc=0.4, slack=0.6, others=0.2)
        country.pulse()
        country.pulse()
        before = dict(country.modifiers)
        country.pulse()
        self.assertAlmostEqual(country.modifiers["construction_cost_scaling"], before["construction_cost_scaling"],
                               places=5)
        # A prior of 0 has no modifier beside it and is not a stale one: the adjusted path is still taken.
        idle = Country(gdppc=0.5, slack=0.6, prior_construction_scaling=0.0)
        idle.run("te_cc_apply_scaling")
        self.assertEqual(idle.variables["prior_construction_scaling"], 0.0)
        self.assertEqual(idle.modifiers, {})

    def test_the_market_price_and_goods_per_point_follow_the_discount_to_its_floor(self):
        for path, name in ((MARKET_PRICE, "te_construction_market_price"),
                           (MARKET_TARGETS, "te_construction_market_goods_per_point")):
            body = _value(_read(path), name)
            self.assertIn("add = construction_cost_scaling_mult", body, name)
            self.assertIn("min = construction_cost_small_economy_min_factor", body, name)
            self.assertNotIn("min = 1", body, name)
        country = Country(te_cc_scale=1.0, te_cc_small_factor=0.02)  # below the floor, however it got there
        self.assertAlmostEqual(country.value("te_construction_market_goods_per_point"), 0.1, places=5)


class TheStrengths(unittest.TestCase):
    """The rule's three strengths (2026-11-16): each setting's factor, the default, the old setting's meaning, and a
    switch in a running game, which reaches a country at its next yearly pulse like the switch on and off."""

    def test_each_settings_factor(self):
        for setting, minimum in MINIMUM.items():
            for gdp in (0, 75e3, 1e6, 5e6, 9.99e6, 10e6, 80e6):
                with self.subTest(setting=setting, gdp=gdp):
                    country = Country(rule=setting, gdp=gdp)
                    self.assertAlmostEqual(country.value("te_cc_small_economy_min_factor"), minimum, places=5)
                    self.assertAlmostEqual(country.value("te_cc_small_economy_factor"),
                                           min(1.0, minimum + (1 - minimum) * gdp / 10e6), places=4)
        # the full price returns at the same GDP under every strength
        for setting in MINIMUM:
            self.assertEqual(Country(rule=setting, gdp=10e6).value("te_cc_small_economy_factor"), 1.0, setting)

    def test_the_default_and_a_save_from_before_the_rule_are_off(self):
        rule = _squash(_body(_read(RULES), "te_small_economy_construction_rule"))
        self.assertTrue(rule.startswith("default = " + SETTINGS["disabled"] + " "), rule[:80])
        for rule_value in (False, "disabled", None):  # None: no setting stored, so no has_game_rule passes
            with self.subTest(rule=rule_value):
                country = Country(rule=rule_value, gdp=1e5, gdppc=0.4, slack=0.6)
                self.assertEqual(country.value("te_cc_small_economy_min_factor"), 1.0)
                self.assertEqual(country.value("te_cc_small_economy_factor"), 1.0)
                country.run("te_cc_weekly_new_country")
                self.assertEqual((country.variables, country.modifiers), ({}, {}))
                country.pulse()
                self.assertEqual(country.variables["te_cc_small_factor"], 1.0)
                self.assertEqual(country.variables["te_cc_small_min"], 1.0)
                self.assertEqual(country.modifiers, {})

    def test_the_old_setting_keeps_its_meaning(self):
        # A preset or a save made with the rule on between 2026-11-13 and 2026-11-16 names
        # te_small_economy_construction_enabled: still a tenth with almost no GDP, the strongest setting.
        self.assertEqual(SETTINGS[True], RULE_PREFIX + "enabled")
        self.assertEqual(SETTINGS["strong"], SETTINGS[True])
        country = Country(rule=True, gdp=1e6, gdppc=0.4, slack=0.6)
        self.assertAlmostEqual(country.value("te_cc_small_economy_min_factor"), 0.1, places=5)
        country.pulse()
        self.assertAlmostEqual(country.variables["te_cc_small_factor"], 0.19, places=4)  # 2026-11-13's figure
        self.assertAlmostEqual(country.modifiers["construction_cost_scaling"], -0.81, places=4)
        self.assertEqual(min(MINIMUM.values()), MINIMUM["strong"])

    def test_every_strength_reaches_a_new_country_at_the_weekly_pulse(self):
        for setting, minimum in MINIMUM.items():
            if setting == "disabled":
                continue
            with self.subTest(setting=setting):
                new = Country(rule=setting, gdp=1e6, gdppc=0.4, slack=0.6)
                new.run("te_cc_weekly_new_country")
                factor = minimum + (1 - minimum) * 0.1
                self.assertAlmostEqual(new.variables["te_cc_small_factor"], factor, places=4)
                self.assertAlmostEqual(new.variables["te_cc_small_min"], minimum, places=5)
                self.assertAlmostEqual(new.modifiers["construction_cost_scaling"], factor - 1, places=4)

    def test_a_switch_waits_for_the_countrys_next_pulse(self):
        # Strong, then mild, standard, off and strong again, a pulse after each, in either construction setting.
        for direct in (False, True):
            name = "construction_cost_scaling_direct" if direct else "construction_cost_scaling"
            with self.subTest(direct=direct):
                country = Country(rule="strong", gdp=1e6, gdppc=0.4, slack=0.6, direct=direct)
                country.pulse()
                self.assertAlmostEqual(country.modifiers[name], -0.81, places=4)
                self.assertEqual(country.value("te_cc_small_setting_changed"), 0.0)
                for setting, after in (("mild", 0.55), ("standard", 0.28), ("disabled", 1.0), ("strong", 0.19)):
                    before = country.value("te_cc_small_factor_now")
                    stored_min = country.variables["te_cc_small_min"]
                    country.rule = setting
                    # Until the pulse the country keeps the factor, the modifier, the price and goods per point it
                    # had, and the tooltip names the minimum that factor came from, with a note that the setting
                    # has changed.
                    self.assertAlmostEqual(country.value("te_cc_small_factor_now"), before, places=5)
                    self.assertAlmostEqual(country.value("construction_cost_scaling_mult"), before - 1, places=4)
                    self.assertAlmostEqual(country.value("te_construction_market_goods_per_point"), before, places=4)
                    self.assertAlmostEqual(country.value("te_cc_small_min_now"), stored_min, places=5)
                    self.assertEqual(country.value("te_cc_small_setting_changed"), 1.0, setting)
                    country.pulse()
                    self.assertAlmostEqual(country.variables["te_cc_small_factor"], after, places=4)
                    self.assertAlmostEqual(country.variables["te_cc_small_min"], MINIMUM[setting], places=5)
                    self.assertAlmostEqual(country.value("te_cc_small_min_now"), MINIMUM[setting], places=5)
                    self.assertEqual(country.value("te_cc_small_setting_changed"), 0.0, setting)
                    if after < 1:
                        self.assertAlmostEqual(country.modifiers[name], after - 1, places=4)
                        self.assertEqual(country.value("te_cc_small_factor_applies"), 1.0)
                    else:
                        self.assertNotIn(name, country.modifiers)
                        self.assertEqual(country.value("te_cc_small_factor_applies"), 0.0)

    def test_the_tooltip_before_a_countrys_first_pulse(self):
        # No stored minimum: the setting chosen now, and no note (the factor in force is 1 until the pulse).
        for setting, minimum in MINIMUM.items():
            country = Country(rule=setting, gdp=1e6)
            self.assertAlmostEqual(country.value("te_cc_small_min_now"), minimum, places=5, msg=setting)
            self.assertEqual(country.value("te_cc_small_setting_changed"), 0.0, setting)


class TheSmallEconomyRule(unittest.TestCase):
    def test_off_by_default_and_read_positively(self):
        rule = _squash(_body(_read(RULES), "te_small_economy_construction_rule"))
        self.assertTrue(rule.startswith("default = te_small_economy_construction_disabled "), rule[:80])
        # Four settings, in the order the rules screen lists them: off, then each strength from the mildest. The
        # strongest keeps the name of the rule's one "on" setting before the strengths, so a preset or a save made
        # with the rule on still means a tenth.
        settings = re.findall(r"(te_small_economy_construction_\w+) = \{ flag = \1 \}", rule)
        self.assertEqual(settings, [RULE_PREFIX + s for s in ("disabled", "mild", "standard", "enabled")])
        # Read positively: a save from before the rule stores no setting, and must read as off.
        triggers = _top_blocks(_read(TRIGGERS))
        self.assertEqual(_squash(triggers["te_small_economy_construction_on"]),
                         "OR = { has_game_rule = te_small_economy_construction_mild "
                         "has_game_rule = te_small_economy_construction_standard "
                         "has_game_rule = te_small_economy_construction_enabled }")
        for name, setting in (("mild", "mild"), ("standard", "standard"), ("strong", "enabled")):
            self.assertEqual(_squash(triggers["te_small_economy_construction_%s_on" % name]),
                             "has_game_rule = te_small_economy_construction_" + setting)
        self.assertNotIn("NOT", " ".join(triggers.values()))
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

    def test_a_country_made_during_play_gets_the_factor_at_the_weekly_pulse(self):
        # A release or an uprising's rebels hold no te_cc_small_factor until their first yearly pulse, up to a
        # year of full prices for the countries the rule is for (review of #1770). The weekly pulse, which runs in
        # the country's own event under either construction setting, gives them the yearly steps once.
        pulse = _squash(_body(_read(WEEKLY_PULSE), "te_construction_market_on_weekly_pulse"))
        self.assertTrue(pulse.startswith("te_cc_weekly_new_country = yes if = { limit = { "
                                         "te_free_market_construction_off = yes }"), pulse[:120])
        body = _squash(_top_blocks(_read(EFFECTS))["te_cc_weekly_new_country"])
        self.assertEqual(body, "if = { limit = { te_small_economy_construction_on = yes "
                               "NOT = { is_country_type = decentralized } NOT = { has_variable = te_cc_small_factor } "
                               "gdp > 0 } te_cc_yearly_update = yes te_cc_apply_scaling = yes }")
        for direct in (False, True):
            name = "construction_cost_scaling_direct" if direct else "construction_cost_scaling"
            with self.subTest(direct=direct):
                new = Country(rule=True, gdp=1e6, gdppc=0.4, slack=0.6, direct=direct)
                new.run("te_cc_weekly_new_country")
                self.assertAlmostEqual(new.variables["te_cc_small_factor"], 0.19, places=4)
                self.assertAlmostEqual(new.modifiers[name], -0.81, places=4)
                # once: the next week finds the factor stored and leaves the country to its yearly pulse
                before = (dict(new.variables), dict(new.modifiers))
                new.run("te_cc_weekly_new_country")
                self.assertEqual((new.variables, new.modifiers), before)
        # Not with the rule off, not before the engine has a GDP for it, not a decentralized country.
        for kwargs in (dict(rule=False, gdp=1e6), dict(rule=True, gdp=0),
                       dict(rule=True, gdp=1e6, country_type="decentralized")):
            with self.subTest(**kwargs):
                other = Country(gdppc=0.4, slack=0.6, **kwargs)
                other.run("te_cc_weekly_new_country")
                self.assertEqual((other.variables, other.modifiers), ({}, {}))

    def test_the_start_self_check_reads_the_modifier_two_days_on(self):
        # It used to read only the variable the same effect stored, which is right whatever ROOT the modifier's
        # multiplier resolved against (review of #1770). The verdict now reads the modifier, from a hidden event
        # two days later: a modifier set in an effect is not visible inside it.
        effects = _top_blocks(_read(EFFECTS))
        arm = _squash(effects["te_cc_small_start_selfcheck"])
        self.assertIn("global_var:te_cc_small_start_queued < 3", arm)
        self.assertIn("var:te_cc_small_factor < 0.8", arm)  # a discount nothing else on the country can hide
        # above the minimum of the setting the factor was worked out from: a GDP above nothing, under every strength
        self.assertIn("var:te_cc_small_factor > var:te_cc_small_min", arm)
        constants = Country().constants
        for strength in ("mild", "standard", "strong"):
            self.assertLess(constants["construction_cost_small_economy_%s_factor" % strength], 0.8, strength)
        self.assertIn("trigger_event = { id = te_construction_market_recalc_events.5 days = 2 }", arm)
        self.assertNotIn("debug_log", arm)
        event = _squash(_body(_read(START_EVENTS), "te_construction_market_recalc_events.5"))
        # no trigger: a delayed event whose trigger is false when queued is dropped (#1596)
        self.assertEqual(event, "type = country_event hidden = yes immediate = { te_cc_small_start_verdict = yes }")
        verdict = _squash(effects["te_cc_small_start_verdict"])
        self.assertIn("set_variable = { name = te_cc_chk_total value = te_cc_modifier_total }", verdict)
        # both lines carry the setting's minimum, so the factor can be checked by eye under any strength
        self.assertEqual(verdict.count("min=[THIS.Var('te_cc_small_min').GetValue|3]"), 2)
        self.assertIn("limit = { NOT = { has_variable = te_cc_start_retried } var:te_cc_chk_total < 0 "
                      "var:te_cc_chk_stored < 0 } debug_log = \"TE_SELF_CHECK OK small_economy_start ", verdict)
        self.assertIn("else = { debug_log = \"TE_SELF_CHECK BROKEN small_economy_start ", verdict)
        self.assertEqual(verdict.count("set_global_variable = { name = te_cc_small_start_check_done value = yes }"), 1)
        # what it reads is the lever of the construction setting in force
        total = _value(_read(VALUES), "te_cc_modifier_total")
        self.assertIn("modifier:country_construction_goods_cost_mult", total)
        self.assertIn("modifier:goods_input_construction_mult", total)
        # A wrong ROOT resolves the multiplier to 1: the static modifiers' own value, a rise, never a discount.
        with open(STATIC, encoding="utf-8-sig") as f:
            static = f.read()
        self.assertRegex(static, r"construction_cost_scaling = \{[^}]*goods_input_construction_mult = 1\b")
        self.assertRegex(static, r"construction_cost_scaling_direct = \{[^}]*country_construction_goods_cost_mult = 1\b")

    def test_the_text_names_the_figures_the_script_uses(self):
        constants = Country().constants
        self.assertEqual(constants["construction_cost_small_economy_full_gdp"], 10e6)   # "10 million"
        with open(RULE_LOC, encoding="utf-8-sig") as f:
            rules = f.read()
        # Each strength's name and description give its price with almost no GDP, and the description the GDP at
        # which the full price returns, from the constant the script reads.
        words = {0.5: ("Half", "half the price"), 0.2: ("A Fifth", "a fifth of the price"),
                 0.1: ("A Tenth", "a tenth of the price")}
        for strength, setting in (("mild", "mild"), ("standard", "standard"), ("strong", "enabled")):
            with self.subTest(strength=strength):
                name_word, desc_words = words[constants["construction_cost_small_economy_%s_factor" % strength]]
                key = "setting_te_small_economy_construction_" + setting
                name = re.search(key + r':0 "([^"]*)"', rules).group(1)
                desc = re.search(key + r'_desc:0 "([^"]*)"', rules).group(1)
                self.assertTrue(name.startswith(name_word + " "), name)
                self.assertTrue(name.endswith(" for Small Economies"), name)
                self.assertTrue(desc.startswith("Experimental. "), desc)
                for phrase in (desc_words, "almost no [concept_gdp]", "full price at a GDP of 10 million",
                               "AI countries get the same", "next yearly update"):
                    self.assertIn(phrase, desc)
        with open(MISC_LOC, encoding="utf-8-sig") as f:
            misc = f.read()
        small = re.search(r'te_nation_construction_scale_small:0 "([^\n]*)"', misc).group(1)
        self.assertIn("10 million", small)
        self.assertIn("te_cc_small_factor_now", small)
        # the minimum the factor in force was worked out from, not a constant: it reads right under every strength
        self.assertIn("ScriptValue('te_cc_small_min_now')|%0] with almost no GDP", small)
        self.assertNotIn("construction_cost_small_economy", small)
        # and after the rule is changed, both sentences say the new setting arrives at the next yearly update
        pending = ("[SelectLocalization( GreaterThan_CFixedPoint( Country.MakeScope.ScriptValue("
                   "'te_cc_small_setting_changed'), '(CFixedPoint)0' ), 'te_nation_construction_small_pending', "
                   "'te_nation_construction_small_settled' )]")
        plain = re.search(r'te_nation_construction_scale_plain:0 "([^\n]*)"', misc).group(1)
        for line in (small, plain):
            self.assertTrue(line.endswith("." + pending), line[-200:])
        self.assertRegex(misc, r'te_nation_construction_small_pending:0 " The \$rule_te_small_economy_construction_'
                               r'rule\$ game rule has been changed since the last yearly update')
        self.assertIn('te_nation_construction_small_settled:0 ""', misc)
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
