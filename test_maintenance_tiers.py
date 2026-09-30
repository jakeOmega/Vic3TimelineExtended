"""The construction-maintenance tiers: one rate per group (pmg_maintenance,
_light, _heavy, _intensive), every tier switched off by the no-maintenance
settings of free_market_construction_rule, and every group hidden in the PM
panels (docs/systems/mod_systems.md, "Maintenance tiers")."""
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
            found = [g for g in TIERS if re.search(rf"(?m)^\s*{g}\s*$", body)]
            with self.subTest(building=name):
                self.assertLessEqual(len(found), 1, found)

    def test_assignments(self):
        expected = {
            "pmg_maintenance_light": ["building_trade_center", "building_art_academy",
                                      "building_state_youth_centers", "building_software_industry",
                                      "building_copper_mine", "building_lithium_mine"],
            "pmg_maintenance": ["building_steel_mill", "building_motor_industry",
                                "building_skyscraper", "building_construction_sector"],
            "pmg_maintenance_heavy": ["building_railway", "building_highway", "building_port",
                                      "building_airport", "building_network_infrastructure",
                                      "building_power_plant", "building_oil_rig"],
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
        pm_keys = [pm for pm, _ in TIERS.values()]
        for setting in ("free_market_construction_no_maintenance", "free_market_construction_disabled"):
            with self.subTest(setting=setting):
                self.assertIn("force_pm_no_maintenance", settings[setting])
                for pm in pm_keys:
                    self.assertIn(f"disable_{pm}", settings[setting])
        for setting in ("free_market_construction_enabled", "free_market_construction_no_retooling"):
            with self.subTest(setting=setting):
                self.assertIn("disable_pm_no_maintenance", settings[setting])
                for pm in pm_keys:
                    self.assertNotIn(f"disable_{pm}", settings[setting])

    def test_every_group_is_hidden_in_the_pm_panels(self):
        for fn in HIDING_GUI:
            text = _read("gui", fn)
            base = text.count("'pmg_maintenance')")
            self.assertGreater(base, 0, fn)
            for group in TIERS:
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


if __name__ == "__main__":
    unittest.main()
