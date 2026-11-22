"""The Resort Colony as a building of its own (issue #1948).

Design: docs/superpowers/specs/2026-11-21-resort-colony-building-design.md.
The Resort Colony method left the Extraplanetary Base for building_space_resort,
whose levels work their own room at each world (the RESORTS table in
gen_solar_sites.py, plus 10 a staffed Off-World Resort level, plus 10 in Earth
orbit) best draw first, -75% past it: the twin of base room.

Run: python3 -m pytest test_resort_colony.py -q
"""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import gen_solar_sites as gss  # noqa: E402
from test_solar_sites import _block, _raw, _strip  # noqa: E402

# The owner-reviewed draws (design § 6.2), in percent.
DRAWS = {
    "tranquility": 30,
    "olympus_mons": 25, "valles_marineris": 25,
    "shackleton": 15, "marius_hills": 15, "venus": 15, "iapetus": 15, "enceladus": 15,
    "imbrium": 10, "peary": 10, "vesta": 10, "callisto": 10, "titan": 10,
    "hellas_planitia": 5, "ceres": 5, "rhea": 5, "mimas": 5,
    "daedalus": 0, "utopia_planitia": 0, "arcadia_planitia": 0, "psyche": 0, "europa": 0, "ganymede": 0,
    "miranda": 0,
    "mercury": -5, "pallas": -5, "io": -5, "amalthea": -5, "triton": -5,
    "hygiea": -10, "pluto": -10,
    "himalia": -15, "titania": -15, "oberon": -15, "ariel": -15,
    "proteus": -25, "haumea": -25,
    "eris": -30, "makemake": -30,
    "sedna": -35,
}


def _values():
    return _strip(_raw(*gss.VALUES_OUT.parts))


def _effects():
    return _strip(_raw(*gss.EFFECTS_OUT.parts))


class ResortTableTest(unittest.TestCase):
    def test_every_site_has_a_resort_row(self):
        self.assertEqual(set(gss.RESORTS), {s.key for s in gss.SITES})

    def test_room_is_the_worlds_room_for_now(self):
        # The design's starting value (§ 6.1): a world that houses more people
        # houses more guests. A later tune of one world changes this test on purpose.
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertEqual(site.resort_room, site.room)
        self.assertEqual(sum(s.resort_room for s in gss.SITES), 945)

    def test_draws_are_the_designs(self):
        self.assertEqual({s.key: s.resort_draw for s in gss.SITES}, DRAWS)
        for draw in DRAWS.values():
            self.assertEqual(draw % 5, 0)
            self.assertTrue(-35 <= draw <= 30)

    def test_constants(self):
        self.assertEqual(gss.ORBIT_RESORT_ROOM, 10)
        self.assertEqual(gss.RESORT_TECH, "space_colonization")
        self.assertEqual(gss.RESORT_OVERFLOW_DRAW, -75)

    def test_tiers_best_draw_first(self):
        tiers = gss.resort_tiers()
        self.assertEqual(tiers[0].key, "tranquility")
        self.assertEqual(tiers[-1].key, "sedna")
        self.assertEqual(tiers.count(None), 1)
        orbit = tiers.index(None)
        for i, tier in enumerate(tiers):
            if tier is None:
                continue
            with self.subTest(site=tier.key):
                if tier.resort_draw > 0:
                    self.assertLess(i, orbit)
                else:
                    self.assertGreater(i, orbit)
        draws = [0 if t is None else t.resort_draw for t in tiers]
        self.assertEqual(draws, sorted(draws, reverse=True))


class ResortRoomTest(unittest.TestCase):
    def test_room_total(self):
        room = _block(_values(), "sr_resort_room_total")
        self.assertIn("value = 0", room)
        self.assertIn("if = { limit = { has_technology_researched = space_colonization } add = 10 }", room)
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"{gss.site_serves(site)} }} add = sr_site_resort_room_{site.key} }}", room)

    def test_site_room(self):
        values = _values()
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                world = _block(values, f"sr_site_resort_room_{k}")
                self.assertIn(f"value = {site.resort_room}", world)
                self.assertIn(f"add = {{ value = sr_site_resort_staffed_{k} multiply = sr_mod_resort_room floor = yes }}",
                              world)

    def test_fill_and_next_fill(self):
        effects = _effects()
        fill = _block(effects, "sr_resort_fill")
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertEqual(fill.count(f"max = sr_site_resort_room_{site.key} "), 1)
        self.assertEqual(fill.count("max = 10 "), 1)
        self.assertIn("multiply = -75 add = local_var:sr_rs_sum", fill)
        # A tier's levels x draw join the sum; a draw of 0 adds nothing.
        self.assertIn("multiply = 30 add = local_var:sr_rs_sum", fill)
        nxt = _block(effects, "sr_resort_next_fill")
        self.assertIn("value = sr_resort_queued_levels", nxt)
        self.assertIn("set_variable = { name = sr_resort_next_draw value = -75 }", nxt)
        self.assertIn("set_variable = { name = sr_resort_next_draw value = 30 }", nxt)

    def test_hand_values(self):
        values = _strip(_raw("common", "script_values", "sr_colony_module_values.txt"))
        self.assertRegex(values, r"(?m)^sr_mod_resort_room = \{ value = 10 \}")
        levels = _block(values, "sr_resort_levels")
        self.assertIn("is_building_type = building_space_resort", levels)
        self.assertIn("add = level", levels)
        queued = _block(values, "sr_resort_queued_levels")
        self.assertIn("is_building_type = building_space_resort", queued)
        self.assertIn("add = level_after_queued_constructions", queued)

    def test_display(self):
        display = _strip(_raw(*gss.DISPLAY_OUT.parts))
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"sr_disp_site_resort_room_{site.key} = {{ value = sr_site_resort_room_{site.key} }}",
                              display)


def _goods():
    """{good: (base price, local)} from vanilla_parsed and the mod's goods files,
    prices as pm_costs.py reads them."""
    import json
    import pm_costs
    prices = pm_costs.load_goods()
    local = set()
    with open(os.path.join(REPO, "vanilla_parsed", "common", "goods.json"), encoding="utf-8") as f:
        for key, value in json.load(f).items():
            if value[1].get("local", [None, None])[1] == "yes":
                local.add(key)
    goods_dir = os.path.join(REPO, "common", "goods")
    for name in os.listdir(goods_dir):
        text = _strip(_raw("common", "goods", name))
        for m in re.finditer(r"(?m)^(?:\w+:)?(\w+)\s*=\s*\{", text):
            if re.search(r"\blocal\s*=\s*yes", _block(text, m.group(0).split("=")[0].strip())):
                local.add(m.group(1))
    return {good: (price, good in local) for good, price in prices.items()}


class ResortBuildingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.buildings = _strip(_raw("common", "buildings", "extra_buildings.txt"))
        cls.groups = _strip(_raw("common", "production_method_groups", "extra_pm_groups.txt"))
        cls.pms = _strip(_raw("common", "production_methods", "extra_pms.txt"))

    def test_building_shape(self):
        resort = _block(self.buildings, "REPLACE_OR_CREATE:building_space_resort")
        self.assertIn("building_group = bg_exotic", resort)
        self.assertIn("space_colonization", _block(resort, "unlocking_technologies"))
        groups = _block(resort, "production_method_groups").split()
        self.assertEqual(groups, ["pmg_base_building_space_resort", "pmg_launch_to_orbit_building_space_mine",
                                  "pmg_transport_in_space_building_space_mine", "pmg_maintenance_intensive"])
        self.assertIn("required_construction = construction_cost_space_mine", resort)
        self.assertIn("ownership_type = self", resort)
        self.assertIn("owner ?= { sr_resort_may_build_government = yes }", _block(resort, "can_build_government"))
        self.assertIn("owner ?= { sr_resort_may_build_private = yes }", _block(resort, "can_build_private"))

    def test_base_group_is_the_four_mining_methods(self):
        base = _block(self.groups, "REPLACE_OR_CREATE:pmg_base_building_space_mine")
        self.assertEqual(_block(base, "production_methods").split(),
                         ["pm_regolith_processing", "pm_space_mine", "pm_space_colony_mining",
                          "pm_self_replicating_miners"])
        resort = _block(self.groups, "REPLACE_OR_CREATE:pmg_base_building_space_resort")
        self.assertEqual(_block(resort, "production_methods").split(), ["pm_space_colony_vacation"])

    def test_method_figures(self):
        goods = _goods()
        body = _block(_block(self.pms, "pm_space_colony_vacation"), "workforce_scaled")
        inputs = {g: float(n) for g, n in re.findall(r"goods_input_(\w+)_add = ([\d.]+)", body)}
        outputs = {g: float(n) for g, n in re.findall(r"goods_output_(\w+)_add = ([\d.]+)", body)}
        self.assertEqual(inputs, {"electronic_components": 15, "radios": 30, "digital_access": 10,
                                  "advanced_materials": 0.5, "launch_capacity": 480, "wine": 50,
                                  "luxury_furniture": 30, "fruit": 30})
        self.assertEqual(outputs, {"fine_art": 300, "tourism": 900})
        cost = sum(n * goods[g][0] for g, n in inputs.items())
        value = sum(n * goods[g][0] for g, n in outputs.items())
        self.assertEqual((cost, value, value - cost), (108000, 150000, 42000))
        # Call 4: no services (a local good), and no local good added; Digital
        # Access, local, stays as the required input.
        self.assertNotIn("services", inputs)
        self.assertEqual([g for g in inputs if goods[g][1]], ["digital_access"])
        self.assertIn("required_input_goods = digital_access", _block(self.pms, "pm_space_colony_vacation"))
        self.assertEqual(inputs["advanced_materials"], 2.5 / 5)

    def test_axiom_lists_the_resort(self):
        companies = _strip(_raw("common", "company_types", "extra_companies_flavored.txt"))
        types = _block(_block(companies, "company_axiom_space"), "building_types").split()
        self.assertIn("building_space_resort", types)
        self.assertIn("building_space_mine", types)

    def test_lists_name_the_resort(self):
        misc = _strip(_raw("common", "scripted_triggers", "misc_triggers.txt"))
        self.assertIn("is_building_type = building_space_resort", _block(misc, "is_privately_expandable_building_type"))
        debris = _strip(_raw("common", "scripted_triggers", "te_orbital_debris_triggers.txt"))
        self.assertIn("is_building_type = building_space_resort", _block(debris, "te_debris_uses_orbit"))

    def test_loc(self):
        buildings = _raw("localization", "english", "te_buildings_l_english.yml")
        self.assertIn(' building_space_resort:0 "Resort Colony"', buildings)
        methods = _raw("localization", "english", "te_production_methods_l_english.yml")
        self.assertIn(' pm_space_colony_vacation:0 "Luxury Resorts"', methods)
        self.assertIn(" pmg_base_building_space_resort:0 ", methods)


class ResortRefreshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw("common", "scripted_effects", "sr_colony_module_effects.txt"))
        cls.triggers = _strip(_raw("common", "scripted_triggers", "sr_colony_module_triggers.txt"))
        cls.modifiers = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))

    def test_refresh_removes_first_and_averages(self):
        refresh = _block(self.effects, "sr_resort_refresh")
        adds = refresh.index("add_modifier")
        for name in ("sr_resort_room_bonus", "sr_resort_room_penalty"):
            self.assertLess(refresh.index(f"remove_modifier = {name}"), adds)
            # Removed before the rule's test, so Races Only mid-game drops them (Review Focus 3).
            self.assertLess(refresh.index(f"remove_modifier = {name}"),
                            refresh.index("sr_colonies_contested_enabled = yes"))
        self.assertIn("sr_resort_fill = yes", refresh)
        self.assertIn("sr_resort_next_fill = yes", refresh)
        self.assertRegex(refresh, r"value = local_var:sr_rs_sum\s+divide = local_var:sr_rs_levels")
        self.assertIn("set_local_variable = { name = sr_rs_levels value = sr_resort_levels }", refresh)
        self.assertIn("add_modifier = { name = sr_resort_room_bonus multiplier = var:sr_resort_units }", refresh)
        self.assertIn("add_modifier = { name = sr_resort_room_penalty multiplier = var:sr_resort_units }", refresh)

    def test_modifier_pair(self):
        self.assertIn("building_space_resort_throughput_add = 0.01", _block(self.modifiers, "sr_resort_room_bonus"))
        self.assertIn("building_space_resort_throughput_add = -0.01", _block(self.modifiers, "sr_resort_room_penalty"))
        types = _strip(_raw("common", "modifier_type_definitions", "mod_entity_modifier_types.txt"))
        self.assertIn("percent = yes", _block(types, "building_space_resort_throughput_add"))
        loc = _raw("localization", "english", "te_buildings_l_english.yml")
        self.assertIn(' building_space_resort_throughput_add:0 "$building_space_resort$ [concept_throughput]"', loc)

    def test_gates(self):
        room = _block(self.triggers, "sr_resort_has_room")
        self.assertIn("NOT = { sr_colonies_contested_enabled = yes }", room)
        self.assertIn("sr_resort_queued_levels < sr_resort_room_total", room)
        self.assertIn("is_ai = no", _block(self.triggers, "sr_resort_may_build_government"))
        self.assertIn("sr_resort_has_room = yes", _block(self.triggers, "sr_resort_may_build_government"))
        private = _block(self.triggers, "sr_resort_may_build_private")
        self.assertNotIn("is_ai", private)
        self.assertIn("sr_resort_has_room = yes", private)
        self.assertIn("text = sr_resort_room_full_tt", private)

    def test_monthly_and_hook(self):
        monthly = _strip(_raw("common", "on_actions", "space_race_on_actions.txt"))
        self.assertRegex(monthly, r"limit = \{ has_technology_researched = space_colonization \}\s+sr_resort_refresh = yes")
        hooks = _strip(_raw("common", "on_actions", "extra_on_actions.txt"))
        for name in ("te_on_building_built", "te_on_building_expanded"):
            with self.subTest(on_action=name):
                self.assertRegex(_block(hooks, name), r"is_building_type = building_space_resort\s+exists = owner\s+\}"
                                                      r"\s+owner = \{ sr_resort_hook_fire = yes \}")
        fire = _block(self.effects, "sr_resort_hook_fire")
        self.assertIn("NOT = { has_variable = sr_resort_hook_pending }", fire)
        self.assertIn("set_variable = { name = sr_resort_hook_pending value = yes days = 2 }", fire)
        self.assertIn("trigger_event = { id = space_race_events.112 days = 1 }", fire)
        events = _raw("events", "space_race_events.txt")
        event = _block(_strip(events), "space_race_events.112")
        self.assertIn("hidden = yes", event)
        self.assertIn("has_technology_researched = space_colonization", _block(event, "trigger"))
        self.assertIn("remove_variable = sr_resort_hook_pending", event)
        self.assertIn("sr_resort_refresh = yes", event)
        self.assertRegex(events, r"space_race_events\.112 = \{[^}]*# REVIEWED 2026-11-21 \(delayed_trigger\)")

    def test_carry_over_lines(self):
        debris = _strip(_raw("common", "static_modifiers", "te_orbital_debris_modifiers.txt"))
        pms = _strip(_raw("common", "production_methods", "extra_pms.txt"))
        for name, body in (("sr_commercial_space_dividend", _block(self.modifiers, "sr_commercial_space_dividend")),
                           ("te_orbital_debris", _block(debris, "te_orbital_debris")),
                           ("pm_spaceport", _block(_block(pms, "pm_spaceport"), "state_modifiers"))):
            with self.subTest(modifier=name):
                mine = re.search(r"building_space_mine_throughput_add = (-?[\d.]+)", body).group(1)
                resort = re.search(r"building_space_resort_throughput_add = (-?[\d.]+)", body).group(1)
                self.assertEqual(float(mine), float(resort))

    def test_no_mining_bonus_reaches_the_resort(self):
        for path in (("common", "static_modifiers", "space_race_modifiers.txt"),
                     ("common", "static_modifiers", "space_race_discovery_modifiers.txt")):
            text = _strip(_raw(*path))
            for m in re.finditer(r"(?m)^(\w+) = \{", text):
                name = m.group(1)
                if (name.startswith(("sr_colony_", "sr_discovery_"))
                        or name in ("sr_mars_robotic_precursor", "sr_extraplanetary_commercial")):
                    with self.subTest(modifier=name):
                        self.assertNotIn("building_space_resort_throughput_add", _block(text, name))

    def test_nation_tab_lists_the_pair(self):
        import gen_nation_tab
        self.assertIn("sr_resort_room_*", str(gen_nation_tab.SECTIONS["science_and_space"]))


class ResortModuleTest(unittest.TestCase):
    def test_facility_is_a_hook(self):
        resort = gss.FACILITY["resort"]
        self.assertFalse(resort.modifier)
        self.assertTrue(resort.ships)
        self.assertEqual(gss.MODULE_CODES["resort"], 10)
        self.assertNotIn("sr_module_resort", _raw(*gss.ENTRY_OUT.parts))
        modifiers = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))
        self.assertNotRegex(modifiers, r"(?m)^sr_module_resort\s*=")

    def test_queue_needs_the_technology(self):
        triggers = _strip(_raw(*gss.TRIGGERS_OUT.parts))
        for site in gss.SITES:
            for t in gss.generic_types(site):
                with self.subTest(site=site.key, type=t):
                    body = _block(triggers, f"sr_mod_can_queue_{t}_{site.key}")
                    if t == "resort":
                        self.assertIn("has_technology_researched = space_colonization", body)
                    else:
                        self.assertNotIn("space_colonization", body)

    def test_reason_line(self):
        sguis = _strip(_raw("common", "scripted_guis", "sr_colony_sguis.txt"))
        self.assertRegex(sguis, r"limit = \{ scope:op = 10 \}\s+custom_tooltip = \{\s+text = sr_mod_req_resort_tech_tt"
                                r"\s+has_technology_researched = space_colonization")
        loc = _raw("localization", "english", "te_miscellaneous_l_english.yml")
        self.assertIn(" sr_mod_req_resort_tech_tt:0 ", loc)

    def test_ai_plans_a_resort_when_room_is_full(self):
        effects = _strip(_raw(*gss.EFFECTS_OUT.parts))
        for site in gss.SITES:
            with self.subTest(site=site.key):
                plan = _block(effects, f"sr_mod_ai_plan_{site.key}")
                resort = plan.index(f"sr_mod_can_queue_resort_{site.key} = yes")
                self.assertLess(plan.index(f"sr_mod_can_queue_mine_{site.key} = yes"), resort)
                branch = plan[resort:plan.index("}", plan.index("sr_resort_queued_levels", resort))]
                self.assertIn("sr_resort_queued_levels >= sr_resort_room_total", branch)

    def test_no_three_percent_text(self):
        for path, key in ((("localization", "english", "te_journal_entries_l_english.yml"),
                           "je_space_race_widget_mod_resort_tt"),
                          (("localization", "english", "te_miscellaneous_l_english.yml"), "sr_mod_queue_resort_tt")):
            with self.subTest(key=key):
                line = re.search(rf"(?m)^ {key}:0 \"(.*)\"$", _raw(*path)).group(1)
                self.assertNotIn("+3%", line)
                self.assertIn("$building_space_resort$", line)
        concepts = _raw("localization", "english", "te_concepts_l_english.yml")
        self.assertNotIn(" sr_module_resort:0", concepts)
        self.assertNotIn(" sr_module_resort_desc:0", concepts)


if __name__ == "__main__":
    unittest.main()
