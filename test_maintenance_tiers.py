"""The construction-maintenance tiers: one rate per group (pmg_maintenance,
_light, _heavy, _intensive), the mines' equipment-driven group (_mine), the
method-driven group of power plants, railways and ports (_graded), every tier
switched off by the no-maintenance settings of free_market_construction_rule,
and every group hidden in the PM panels (docs/systems/mod_systems/construction.md,
"Maintenance tiers")."""
import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

# group -> (its PM, construction input per level)
TIERS = {
    "pmg_maintenance_light": ("pm_maintenance_light", 0.05),
    "pmg_maintenance": ("pm_maintenance", 0.1),
    "pmg_maintenance_heavy": ("pm_maintenance_heavy", 0.15),
    "pmg_maintenance_intensive": ("pm_maintenance_intensive", 0.2),
}
MINE_GROUP = "pmg_maintenance_mine"
MINE_PMS = ["pm_maintenance_traditional", "pm_maintenance_mechanized_mine"]
MINE_TYPES = ["coal", "iron", "lead", "sulfur", "gold"]
# Discoverable mines that run one of those mines' equipment groups, picks and shovels
# included, so they take the same group. The tech metals mines (no hand-worked method)
# stay on pmg_maintenance_light.
DISCOVERABLE_ON_MINE_GROUP = ["manganese", "chromium", "specialty_alloy_metal", "copper", "bauxite",
                              "precious_minor_base_metal", "graphite", "phosphate", "potash",
                              "industrial_mineral_salt"]
TECH_METALS_MINES = ["lithium", "nickel_cobalt", "rare_earth_metals", "platinum_group_metals"]
GRADED_GROUP = "pmg_maintenance_graded"
GRADED_PMS = ["pm_maintenance_graded_light", "pm_maintenance_graded_standard", "pm_maintenance_graded_heavy"]
GRADED_RATES = [0.05, 0.1, 0.15]
# building -> (its base group, {base method: tier index}); a method not listed is light
GRADED_BUILDINGS = {
    "building_power_plant": ("pmg_base_building_power_plant", {
        "pm_oil-fired_plant": 1, "pm_modern_coal-fired_plant": 1, "pm_modern_oil-fired_plant": 1}),
    "building_railway": ("pmg_base_building_railway", {
        "pm_electric_trains": 1, "pm_electric_trains_principle_transport_3": 1,
        "pm_diesel_trains": 1, "pm_diesel_trains_principle_transport_3": 1,
        "pm_centralized_traffic_control": 1, "pm_containerized_cargo": 2,
        "pm_automated_loading_and_unloading": 2, "pm_autonomous_trains": 2}),
    "building_port": ("pmg_base_building_port", {
        "pm_modern_port": 1, "pm_container_ports": 2, "pm_global_ports": 2, "pm_magnetic_drive_ports": 2}),
}
# Equipment PMs from the condensing engine pump on: the ones that make a mine mechanized.
MECHANIZED_STEMS = ["condensing_engine_pump", "diesel_pump", "high_pressure_hydraulic_pump",
                    "continuous_miners", "smart_miners"]
HIDING_GUI = ["production_methods.gui", "building_details_panel.gui",
              "building_browser_panel.gui", "goods_state_panel.gui"]
TOP_LEVEL = re.compile(r"^(?:[A-Z_]+:)?(\w+) = \{", re.M)


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _top_level_blocks(text):
    """{name: body} for each unindented `name = {` entry (REPLACE:/INJECT:
    prefixes dropped). Entries in these files end at the next unindented key."""
    marks = [(m.start(), m.end(), m.group(1)) for m in TOP_LEVEL.finditer(text)]
    blocks = {}
    for i, (_, end, name) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        blocks.setdefault(name, "")
        blocks[name] += text[end:stop]
    return blocks


def _buildings():
    blocks = {}
    for fn in ("extra_buildings.txt", "grand_monuments.txt", "te_construction_market_site.txt"):
        for name, body in _top_level_blocks(_read("common", "buildings", fn)).items():
            blocks[name] = blocks.get(name, "") + body
    return blocks


def _group_methods(group):
    """A PM group's methods: vanilla's (the committed snapshot) plus the mod's INJECTs,
    or the mod's own list for a group it creates or replaces."""
    text = _read("common", "production_method_groups", "extra_pm_groups.txt")
    mod = re.search(rf"(?m)^(REPLACE_OR_CREATE:|REPLACE:|INJECT:)?{re.escape(group)} = \{{(.*?)^\}}", text, re.S)
    methods = []
    if mod is None or mod.group(1) == "INJECT:":
        with open(os.path.join(REPO, "vanilla_parsed", "common", "pm_groups.json"), encoding="utf-8") as f:
            methods = list(json.load(f)[group][1]["production_methods"][1])
    if mod is not None:
        listed = re.search(r"production_methods = \{(.*?)\}", mod.group(2), re.S)
        if listed:
            methods += listed.group(1).split()
    return methods


def _rule_settings():
    rule = _top_level_blocks(_read("common", "game_rules", "extra_game_rules.txt"))[
        "free_market_construction_rule"]
    settings = {}
    for m in re.finditer(r"^\t(free_market_construction_\w+) = \{(.*?)^\t\}", rule, re.M | re.S):
        settings[m.group(1)] = set(re.findall(r"flag = ((?:disable|force)_\w+)", m.group(2)))
    return settings


class MaintenanceTiers(unittest.TestCase):
    def test_each_group_is_one_rate_plus_no_maintenance(self):
        groups = _top_level_blocks(_read("common", "production_method_groups", "extra_pm_groups.txt"))
        pms = _top_level_blocks(_read("common", "production_methods", "extra_pms.txt"))
        for group, (pm, rate) in TIERS.items():
            with self.subTest(group=group):
                listed = re.search(r"production_methods = \{(.*?)\}", groups[group], re.S).group(1).split()
                self.assertEqual(listed, [pm, "pm_no_maintenance"])
                self.assertIn("is_hidden_when_unavailable = yes", pms[pm])
                value = re.search(r"goods_input_construction_add = ([\d.]+)", pms[pm])
                self.assertIsNotNone(value, f"{pm} has no construction input")
                self.assertAlmostEqual(float(value.group(1)), rate)

    def test_a_building_takes_at_most_one_tier(self):
        for name, body in _buildings().items():
            found = [g for g in list(TIERS) + [MINE_GROUP, GRADED_GROUP] if re.search(rf"(?m)^\s*{g}\s*$", body)]
            with self.subTest(building=name):
                self.assertLessEqual(len(found), 1, found)

    def test_mine_group_follows_the_equipment(self):
        groups = _top_level_blocks(_read("common", "production_method_groups", "extra_pm_groups.txt"))
        pms = _top_level_blocks(_read("common", "production_methods", "extra_pms.txt"))
        listed = re.search(r"production_methods = \{(.*?)\}", groups[MINE_GROUP], re.S).group(1).split()
        self.assertEqual(listed, MINE_PMS + ["pm_no_maintenance"])
        # free method first (the default and the fallback) and swapping to the paid one
        self.assertIn("replacement_if_valid = pm_maintenance_mechanized_mine", pms[MINE_PMS[0]])
        self.assertNotIn("goods_input_construction_add", pms[MINE_PMS[0]])
        paid = pms[MINE_PMS[1]]
        self.assertAlmostEqual(float(re.search(r"goods_input_construction_add = ([\d.]+)", paid).group(1)), 0.05)
        unlocked = re.search(r"unlocking_production_methods = \{(.*?)\}", paid, re.S).group(1).split()
        expected = [f"pm_{s}_building_{t}_mine" for t in MINE_TYPES for s in MECHANIZED_STEMS]
        self.assertCountEqual(unlocked, expected)
        # every unlocking PM is a real method: vanilla's, or one this mod defines
        with open(os.path.join(REPO, "vanilla_parsed", "common", "pms.json"), encoding="utf-8") as f:
            known = set(json.load(f))
        known |= set(_top_level_blocks(_read("common", "production_methods", "extra_pms.txt")))
        for pm in unlocked:
            with self.subTest(pm=pm):
                self.assertIn(pm, known)
        # the five original mines use it, and each of their equipment groups lists those PMs
        buildings = _buildings()
        for t in MINE_TYPES:
            with self.subTest(mine=t):
                self.assertRegex(buildings[f"building_{t}_mine"], rf"(?m)^\s*{MINE_GROUP}\s*$")
        # so do the discoverable mines on those equipment groups, whose mechanized methods
        # are the same PMs; the tech metals mines, with their own all-mechanized group, don't
        for t in DISCOVERABLE_ON_MINE_GROUP:
            with self.subTest(mine=t):
                body = buildings[f"building_{t}_mine"]
                self.assertRegex(body, rf"(?m)^\s*{MINE_GROUP}\s*$")
                equipment = re.search(r"pmg_mining_equipment_building_(\w+)_mine", body).group(1)
                self.assertIn(equipment, MINE_TYPES)
        for t in TECH_METALS_MINES:
            with self.subTest(mine=t):
                body = buildings[f"building_{t}_mine"]
                self.assertRegex(body, r"(?m)^\s*pmg_maintenance_light\s*$")
                self.assertIn("pmg_mining_equipment_building_tech_metals_mine", body)

    def test_graded_group_follows_the_base_method(self):
        groups = _top_level_blocks(_read("common", "production_method_groups", "extra_pm_groups.txt"))
        pms = _top_level_blocks(_read("common", "production_methods", "extra_pms.txt"))
        listed = re.search(r"production_methods = \{(.*?)\}", groups[GRADED_GROUP], re.S).group(1).split()
        self.assertEqual(listed, GRADED_PMS + ["pm_no_maintenance"])
        unlocks = []
        for i, (pm, rate) in enumerate(zip(GRADED_PMS, GRADED_RATES)):
            body = pms[pm]
            with self.subTest(pm=pm):
                self.assertIn("is_hidden_when_unavailable = yes", body)
                self.assertAlmostEqual(float(re.search(r"goods_input_construction_add = ([\d.]+)", body).group(1)), rate)
                # each tier hands over to the next
                if i + 1 < len(GRADED_PMS):
                    self.assertIn(f"replacement_if_valid = {GRADED_PMS[i + 1]}", body)
                else:
                    self.assertNotIn("replacement_if_valid", body)
            block = re.search(r"unlocking_production_methods = \{(.*?)\}", body, re.S)
            unlocks.append(set(re.sub(r"#[^\n]*", "", block.group(1)).split()) if block else set())
        # light needs no other method (the default and the fallback); standard's list
        # holds heavy's, so light can step up to heavy through it
        self.assertEqual(unlocks[0], set())
        self.assertLessEqual(unlocks[2], unlocks[1])
        buildings = _buildings()
        covered = set()
        for building, (base_group, tiers) in GRADED_BUILDINGS.items():
            with self.subTest(building=building):
                self.assertRegex(buildings[building], rf"(?m)^\s*{GRADED_GROUP}\s*$")
            for method in _group_methods(base_group):
                tier = tiers.get(method, 0)
                # the dearest tier whose list holds the method is the one it settles on
                settled = max([i for i in (1, 2) if method in unlocks[i]], default=0)
                with self.subTest(building=building, method=method):
                    self.assertEqual(settled, tier)
                covered.add(method)
        # nothing in the lists that isn't one of these buildings' base methods
        self.assertLessEqual(unlocks[1], covered)
        # a Transport principle variant pays what its base method pays
        for base in ("pm_steam_trains", "pm_electric_trains", "pm_diesel_trains"):
            variant = base + "_principle_transport_3"
            tiers = GRADED_BUILDINGS["building_railway"][1]
            with self.subTest(variant=variant):
                self.assertEqual(tiers.get(variant, 0), tiers.get(base, 0))

    def test_assignments(self):
        expected = {
            "pmg_maintenance_light": ["building_trade_center", "building_art_academy",
                                      "building_state_youth_centers", "building_software_industry",
                                      "building_lithium_mine"],
            "pmg_maintenance": ["building_steel_mill", "building_motor_industry",
                                "building_skyscraper", "building_construction_sector"],
            "pmg_maintenance_heavy": ["building_highway", "building_airport",
                                      "building_network_infrastructure", "building_hydro_plant",
                                      "building_renewable_energy_plant", "building_oil_rig"],
            "pmg_maintenance_intensive": ["building_nuclear_plant", "building_fusion_plant",
                                          "building_ocean_mine", "building_space_mine"],
        }
        buildings = _buildings()
        for group, names in expected.items():
            for name in names:
                with self.subTest(building=name):
                    self.assertRegex(buildings[name], rf"(?m)^\s*{group}\s*$")

    def test_no_maintenance_settings_switch_every_tier_off(self):
        settings = _rule_settings()
        pm_keys = [pm for pm, _ in TIERS.values()] + MINE_PMS + GRADED_PMS
        for setting in ("free_market_construction_no_maintenance", "free_market_construction_disabled"):
            with self.subTest(setting=setting):
                self.assertIn("force_pm_no_maintenance", settings[setting])
                for pm in pm_keys:
                    self.assertIn(f"disable_{pm}", settings[setting])
        for setting in ("free_market_construction_enabled", "free_market_construction_no_ai_retooling",
                        "free_market_construction_no_retooling"):
            with self.subTest(setting=setting):
                self.assertIn("disable_pm_no_maintenance", settings[setting])
                for pm in pm_keys:
                    self.assertNotIn(f"disable_{pm}", settings[setting])

    def test_every_group_is_hidden_in_the_pm_panels(self):
        for fn in HIDING_GUI:
            text = _read("gui", fn)
            base = text.count("'pmg_maintenance')")
            self.assertGreater(base, 0, fn)
            for group in list(TIERS) + [MINE_GROUP, GRADED_GROUP]:
                if group != "pmg_maintenance":
                    with self.subTest(gui=fn, group=group):
                        self.assertEqual(text.count(f"'{group}')"), base)

    def test_names_are_localized(self):
        loc = _read("localization", "english", "te_production_methods_l_english.yml")
        for group, (pm, _) in TIERS.items():
            if group != "pmg_maintenance":
                self.assertIn(f" {group}:0 ", loc)
                self.assertIn(f" {pm}:0 ", loc)
                self.assertIn(f" {pm}_desc:0 ", loc)
        self.assertIn(f" {MINE_GROUP}:0 ", loc)
        self.assertIn(f" {GRADED_GROUP}:0 ", loc)
        for pm in MINE_PMS + GRADED_PMS:
            self.assertIn(f" {pm}:0 ", loc)
            self.assertIn(f" {pm}_desc:0 ", loc)


if __name__ == "__main__":
    unittest.main()
