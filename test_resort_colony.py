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


if __name__ == "__main__":
    unittest.main()
