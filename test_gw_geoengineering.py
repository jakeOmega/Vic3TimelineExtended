"""Geoengineering: the Stratospheric Aerosol Injection climate policy (era 13 spec § 7.5).

The policy masks warming for the whole world while someone runs it, at a share of
GDP a year; emissions keep accumulating underneath, the harms read the masked
temperature, and when nobody runs it the masked warming returns within a few
years (termination shock). The engine notices none of the ways this can come
apart: a harm reading the unmasked figure, a mask step that rounds to nothing,
a cost re-applied without its removal, a cooling event fired by the haze. This
checks the wiring, and runs the mask's monthly step as the script writes it.
"""

import math
import re
import unittest
from pathlib import Path

from test_tax_code_rule import load

ROOT = Path(__file__).resolve().parent
AEROSOL = "common/script_values/global_warming_aerosol_values.txt"
EFFECTS = "common/scripted_effects/global_warming_effects.txt"
TRIGGERS = "common/scripted_triggers/global_warming_triggers.txt"
MODIFIERS = "common/static_modifiers/extra_modifiers.txt"
EXTRA_VALUES = "common/script_values/extra_script_values.txt"
JE = "common/journal_entries/je_global_warming.txt"
ON_ACTIONS = "common/on_actions/extra_on_actions.txt"
EVENTS = "events/environmentalism_events.txt"


def _text(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def _loc(key):
    for path in sorted((ROOT / "localization/english").glob("*_l_english.yml")):
        m = re.search(rf'(?m)^ {re.escape(key)}:\d+ "(.*)"', path.read_text(encoding="utf-8-sig"))
        if m:
            return m.group(1)
    raise AssertionError(f"no loc for {key}")


def _round(x):
    """The engine's `round = yes`: to the nearest whole number."""
    return math.floor(x + 0.5)


class TechnologyTest(unittest.TestCase):
    def test_era_12_society_after_environmental_movement_and_globalization(self):
        tech = load("common/technology/technologies/era_12.txt")["geoengineering"]
        self.assertEqual(tech["era"], "era_12")
        self.assertEqual(tech["category"], "society")
        self.assertEqual(sorted(tech["unlocking_technologies"]), ["environmental_movement", "globalization"])
        self.assertEqual(tech["ai_weight"], {"value": "1"})
        self.assertRegex(_text("common/technology/technologies/era_12.txt"),
                         r'geoengineering = \{[^}]*texture = "[^"]+" # Placeholder Icon')
        self.assertTrue(_loc("geoengineering"))
        self.assertIn("Stratospheric Aerosol Injection", _loc("geoengineering_desc"))

    def test_its_tooltip_names_the_policy(self):
        """The policy is all it unlocks, and the engine lists no climate policy,
        so a display-only marker says so; it shipped without one and read as a
        technology that did nothing (2026-11-01). The gate reads the technology
        (test_the_policy_needs_it), so the marker must sit on that technology."""
        tech = load("common/technology/technologies/era_12.txt")["geoengineering"]
        self.assertEqual(tech["modifier"]["country_gw_aerosol_injection_bool"], "yes")
        possible = load(TRIGGERS)["gw_possible_aerosol_injection"]
        self.assertEqual(possible["has_technology_researched"], "geoengineering")
        marker = load("common/modifier_type_definitions/global_warming_modifier_types.txt")[
            "country_gw_aerosol_injection_bool"]
        self.assertEqual(marker["boolean"], "yes")
        self.assertEqual(marker["script_only"], "yes")
        self.assertEqual(marker["color"], "good")
        self.assertIn("Stratospheric Aerosol Injection", _loc("country_gw_aerosol_injection_bool"))
        desc = _loc("country_gw_aerosol_injection_bool_desc")
        self.assertIn("1.0 °C", desc)
        self.assertIn("2 °C", desc)
        self.assertIn("one percent of GDP", desc)

    def test_weather_modification_eases_droughts_and_hail(self):
        """Cloud seeding and hail suppression (owner, 2026-11-01): milder than
        Reforestation Subsidies, a policy that costs, and the figures the
        player guide gives."""
        mods = load("common/technology/technologies/era_12.txt")["geoengineering"]["modifier"]
        self.assertEqual(
            {k: float(v) for k, v in mods.items() if k.startswith("state_")},
            {
                "state_harvest_condition_drought_impact_mult": -0.10,
                "state_harvest_condition_drought_duration_mult": -0.10,
                "state_harvest_condition_hailstorm_impact_mult": -0.20,
            },
        )
        reforestation = load(MODIFIERS)["reforestation_subsidies_modifier"]
        self.assertLess(float(reforestation["state_harvest_condition_drought_impact_mult"]),
                        float(mods["state_harvest_condition_drought_impact_mult"]))
        guide = _text("docs/player_guide/15-climate.md")
        self.assertRegex(guide, r"droughts are 10% milder and 10% shorter, and hailstorms\s+20% weaker")
        self.assertIn("hail", _loc("geoengineering_desc"))

    def test_the_policy_needs_it(self):
        possible = load(TRIGGERS)["gw_possible_aerosol_injection"]
        self.assertEqual(possible["has_technology_researched"], "geoengineering")
        # Measured beneath any haze, so a country can join others' injections.
        self.assertEqual(possible["custom_tooltip"]["text"], "gw_cond_unmasked_warming_moderate")
        self.assertRegex(_text(TRIGGERS), r"text = gw_cond_unmasked_warming_moderate\s*gw_unmasked_temperature >= 1\.0")
        self.assertIn("1.0 °C", _loc("gw_cond_unmasked_warming_moderate"))


class MaskedTemperatureTest(unittest.TestCase):
    def test_the_felt_anomaly_is_the_warming_less_the_mask(self):
        values = load(EXTRA_VALUES)
        felt = values["temperature_anomaly_display"]
        self.assertEqual(felt["value"], "gw_unmasked_temperature")
        text = _text(EXTRA_VALUES)
        body = text[text.index("temperature_anomaly_display = {"):]
        body = body[: body.index("\n}") + 2]
        self.assertRegex(body, r"limit = \{ gw_aerosol_mask > 0 \}\s*subtract = gw_aerosol_mask\s*min = 0")
        # The emissions still accumulate into the unmasked figure, unchanged.
        raw = values["gw_unmasked_temperature"]
        self.assertEqual(raw["value"], "global_var:greenhouse_gas_emissions")

    def test_the_harms_read_the_felt_anomaly(self):
        je = _text(JE)
        self.assertIn("add_modifier = { name = global_warming multiplier = temperature_anomaly_display }", je)
        self.assertIn("temperature_anomaly_display >= $THRESHOLD$", _text("common/scripted_effects/extra_effects.txt"))

    def test_cooling_events_and_the_ai_read_the_warming_beneath(self):
        helpers = _text("common/scripted_effects/extra_effects.txt")
        cooling = helpers[helpers.index("gw_fire_cooling_threshold_event = {"):]
        self.assertIn("gw_unmasked_temperature < $THRESHOLD$", cooling[: cooling.index("\n}")])
        urgency = load("common/script_values/global_warming_ai_values.txt")["gw_ai_will_urgency"]
        self.assertEqual(urgency["value"], "gw_unmasked_temperature")


class MaskStepTest(unittest.TestCase):
    """The monthly step as gw_aerosol_mask_next writes it."""

    @classmethod
    def setUpClass(cls):
        cls.values = load(AEROSOL)
        cls.rate = float(cls.values["gw_aerosol_mask_rate"])
        cls.cap = float(cls.values["gw_aerosol_max_mask"])
        cls.per_gdp = float(cls.values["gw_aerosol_degrees_per_world_gdp"])

    def step(self, mask, target):
        gap = target - mask
        move = gap * self.rate
        if gap > 0:
            move = min(max(move, 0.01), gap)
        elif gap < 0:
            move = max(min(move, -0.01), gap)
        return max(_round((mask + move) * 100) / 100, 0)

    def target(self, share, unmasked):
        return _round(min(share * self.per_gdp, self.cap, unmasked) * 100) / 100

    def test_the_script_is_the_model(self):
        # The parsed form drops comparison operators and groups repeated
        # keys, so the order of operations is read off the text.
        text = _text(AEROSOL)
        nxt = text[text.index("gw_aerosol_mask_next = {"):]
        nxt = re.sub(r"\s+", " ", nxt[: nxt.index("\n}")])
        self.assertIn("value = gw_aerosol_mask_gap multiply = gw_aerosol_mask_rate "
                      "if = { limit = { gw_aerosol_mask_gap > 0 } min = 0.01 max = gw_aerosol_mask_gap } "
                      "else_if = { limit = { gw_aerosol_mask_gap < 0 } max = -0.01 min = gw_aerosol_mask_gap } "
                      "add = gw_aerosol_mask multiply = 100 round = yes divide = 100 min = 0", nxt)
        self.assertEqual(self.values["gw_aerosol_mask_gap"], {"value": "gw_aerosol_target", "subtract": "gw_aerosol_mask"})
        target = text[text.index("gw_aerosol_target_value = {"):]
        target = re.sub(r"\s+", " ", target[: target.index("\n}")])
        self.assertIn("add = global_var:gw_g_aerosol_gdp divide = global_var:gw_g_gdp_sum "
                      "multiply = gw_aerosol_degrees_per_world_gdp max = gw_aerosol_ceiling "
                      "multiply = 100 round = yes divide = 100", target)
        ceiling = self.values["gw_aerosol_ceiling"]
        self.assertEqual((ceiling["value"], ceiling["max"]), ("gw_aerosol_max_mask", "gw_unmasked_temperature"))

    def test_a_fifth_of_world_gdp_masks_a_degree(self):
        self.assertEqual(self.target(0.2, 3.0), 1.0)
        self.assertEqual(self.target(0.9, 3.0), self.cap)
        self.assertEqual(self.target(0.9, 0.4), 0.4)   # never more than the warming there is

    def test_it_builds_up_over_a_year_or_two(self):
        mask = 0.0
        for _ in range(12):
            mask = self.step(mask, 1.0)
        self.assertAlmostEqual(mask, 0.63, delta=0.03)
        for _ in range(12):
            mask = self.step(mask, 1.0)
        self.assertGreater(mask, 0.8)
        for _ in range(60):
            mask = self.step(mask, 1.0)
        self.assertEqual(mask, 1.0)   # the hundredth floor lets it arrive exactly

    def test_termination_returns_the_warming_within_a_few_years(self):
        mask = 1.5
        months = 0
        while mask > 0:
            mask = self.step(mask, 0.0)
            months += 1
            if months == 12:
                self.assertLess(mask, 1.5 * 0.4)   # two thirds back within a year
            if months == 36:
                self.assertLess(mask, 1.5 * 0.1)   # nearly all within three
        self.assertLess(months, 72)

    def test_the_mask_always_moves(self):
        """Without the hundredth floor a small gap rounds to no step at all."""
        for mask, target in ((0.97, 1.0), (1.0, 0.98), (0.0, 0.01), (0.02, 0.0)):
            self.assertNotEqual(self.step(mask, target), mask, (mask, target))


class UpdateWiringTest(unittest.TestCase):
    def test_one_writer_after_the_counts_under_the_rule(self):
        pulse = load(ON_ACTIONS)["global_warming_events_on_action"]["effect"]
        rule = pulse["if"]
        keys = list(rule)
        self.assertLess(keys.index("gw_refresh_global_counts_effect"), keys.index("gw_aerosol_update_mask_effect"))
        self.assertEqual(pulse["else"]["gw_aerosol_clear_mask_effect"], "yes")
        writers = [p for p in (ROOT / "common").rglob("*.txt")
                   if re.search(r"name = gw_g_aerosol_mask value", p.read_text(encoding="utf-8-sig"))]
        self.assertEqual([p.name for p in writers], ["global_warming_effects.txt"])

    def test_the_counts_take_world_gdp_and_the_deployers(self):
        text = _text(EFFECTS)
        counts = text[text.index("gw_refresh_global_counts_effect = {"):]
        counts = counts[: counts.index("\n}")]
        for line in ("name = gw_g_gdp_sum add = gdp", "name = gw_g_aerosol_gdp add = gdp",
                     "name = gw_g_n_aerosol_injection add = 1"):
            self.assertIn(line, counts)

    def test_termination_shock_fires_once_when_nobody_runs_it(self):
        text = _text(EFFECTS)
        update = text[text.index("gw_aerosol_update_mask_effect = {"):]
        update = re.sub(r"\s+", " ", update[: update.index("\n}")])
        self.assertIn("limit = { gw_aerosol_deployers < 1 gw_aerosol_mask >= gw_aerosol_shock_min_mask "
                      "NOT = { has_global_variable = gw_g_aerosol_shock_fired } } "
                      "set_global_variable = { name = gw_g_aerosol_shock_fired value = 1 }", update)
        self.assertIn("trigger_event = { id = environmentalism_events.24 }", update)
        # Cleared once someone flies it again, so a second ending shocks again.
        self.assertIn("else_if = { limit = { gw_aerosol_deployers > 0 has_global_variable = gw_g_aerosol_shock_fired } "
                      "remove_global_variable = gw_g_aerosol_shock_fired }", update)
        events = load(EVENTS)
        event = events["environmentalism_events.24"]
        self.assertEqual(event["event_image"]["texture"].strip('"'), "gfx/event_pictures/heatwave.dds")
        modifier = event["option"]["add_modifier"]
        self.assertEqual((modifier["name"], modifier["days"], modifier["multiplier"]),
                         ("gw_termination_shock_modifier", "normal_modifier_time", "gw_aerosol_mask"))
        for key in ("t", "d", "f", "a"):
            self.assertTrue(_loc(f"environmentalism_events.24.{key}"))

    def test_objectors_relations_match_the_tooltip(self):
        values = load(AEROSOL)
        start = int(values["gw_aerosol_objection_at_start"])
        yearly = int(values["gw_aerosol_objection_yearly"])
        tt = _loc("gw_aerosol_objection_tt")
        self.assertIn(f"#R {-start}#!", tt)
        self.assertIn(f"#R {-yearly}#!", tt)
        effects = _text(EFFECTS)
        self.assertIn("value = gw_aerosol_objection_at_start", effects)
        self.assertIn("value = gw_aerosol_objection_yearly", effects)
        # Never relations with oneself (scripting_best_practices.md).
        self.assertEqual(effects.count("NOT = { THIS = scope:gw_aerosol_deployer }"), 2)
        objects = load(TRIGGERS)["gw_aerosol_objects"]
        self.assertIn({"gw_policy_aerosol_injection_active": "yes"}, objects["NOT"])
        self.assertEqual(objects["OR"]["gw_country_in_monsoon_region"], "yes")
        self.assertRegex(_text(TRIGGERS), r"gw_country_in_monsoon_region = yes\s*gw_ai_repeal_margin_aerosol_injection > 0")


class PolicyTest(unittest.TestCase):
    COST = "aerosol_injection_cost_modifier"

    def test_cost_is_one_percent_of_gdp_a_year_like_renewable_investment(self):
        modifiers = load(MODIFIERS)
        self.assertEqual(modifiers[self.COST], {
            "icon": "gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds",
            "country_expenses_add": "1", "country_te_budget_expense_climate_add": "1"})
        self.assertEqual(load("common/script_values/global_warming_cost_values.txt")["gw_aerosol_injection_cost_value"],
                         {"value": "gdp", "multiply": "0.01", "divide": "52", "min": "0"})
        effects = load(EFFECTS)
        self.assertEqual(list(effects["gw_aerosol_injection_cost_apply"]),
                         ["remove_modifier_if_exists_effect", "add_modifier"])
        self.assertEqual(effects["gw_aerosol_injection_cost_apply"]["add_modifier"],
                         {"name": self.COST, "multiplier": "gw_aerosol_injection_cost_value"})
        adopt = effects["gw_effect_aerosol_injection"]
        self.assertEqual(adopt["gw_aerosol_injection_cost_apply"], "yes")
        repeal = effects["gw_effect_remove_aerosol_injection"]["custom_tooltip"]
        self.assertEqual(repeal["remove_modifier"], self.COST)
        sweep = effects["gw_refresh_policy_costs_effect"]["every_country"]
        self.assertEqual(sweep["gw_aerosol_injection_cost_sync"], "yes")
        self.assertIn(self.COST, sweep["limit"]["OR"]["has_modifier"])
        from scripts.generators.gen_budget_breakdown import SOURCES
        self.assertIn(self.COST, SOURCES["expense"]["climate"][1])
        for key in (self.COST, self.COST + "_desc", "aerosol_injection_modifier", "aerosol_injection_modifier_desc"):
            self.assertTrue(_loc(key), key)

    def test_a_revolutions_winner_keeps_it(self):
        effects = load(EFFECTS)
        adopt = effects["gw_effect_aerosol_injection"]["custom_tooltip"]
        adopt = adopt[0] if isinstance(adopt, list) else adopt
        self.assertEqual(adopt["hidden_effect"]["set_variable"]["name"], "gw_aerosol_injection_policy")
        restore = effects["gw_restore_aerosol_injection_policy_effect"]["if"]
        self.assertEqual(restore["limit"]["has_variable"], "gw_aerosol_injection_policy")
        self.assertIn("gw_restore_aerosol_injection_policy_effect = yes", _text(JE))

    def test_it_stirs_the_movement_and_the_movement_does_not_want_it(self):
        modifier = load(MODIFIERS)["aerosol_injection_modifier"]
        self.assertGreater(float(modifier["country_environmental_movement_radicalism_add"]), 0)
        self.assertNotIn("gw_possible_aerosol_injection",
                         _text("common/political_movements/new_ideological_movements.txt"))

    def test_weakened_monsoons_scale_with_the_mask(self):
        je = _text(JE)
        self.assertIn("add_modifier = { name = gw_aerosol_monsoon_modifier multiplier = gw_aerosol_mask }", je)
        self.assertRegex(je, r"gw_aerosol_mask >= 0\.01\s*gw_country_in_monsoon_region = yes")
        monsoon = load(MODIFIERS)["gw_aerosol_monsoon_modifier"]
        warming = load(MODIFIERS)["global_warming"]
        # Half the farm relief back, none of the drought relief, per degree masked.
        self.assertEqual(float(monsoon["building_group_bg_agriculture_throughput_add"]),
                         float(warming["building_group_bg_agriculture_throughput_add"]) / 2)
        self.assertEqual(monsoon["state_harvest_condition_drought_impact_mult"],
                         warming["state_harvest_condition_drought_impact_mult"])


if __name__ == "__main__":
    unittest.main()
