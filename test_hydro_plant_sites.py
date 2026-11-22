"""Where a Hydro Plant may be built: on a river, or in a state whose great dam is built.

The four dam wonders (Hoover, Aswan High, Itaipu, Three Gorges) raise their state's Hydro Plant cap and throughput.
Nevada, the Hoover Dam's state, is not on a river in the engine's map data, so with `possible = { on_river = yes }`
alone that wonder's bonus had nothing to apply to (2026-11-18). The plant's `possible` now also accepts a state with
one of the dams built. These tests hold that list to the buildings whose methods grant
`state_building_hydro_plant_max_level_add`, so a new dam wonder can't repeat the dead end.
"""
import re
import unittest
from pathlib import Path

import test_ai_building_values as buildings

ROOT = Path(__file__).resolve().parent
CLEAN_POWER = ROOT / "common/buildings/06_zz_te_clean_power.txt"
LOC = ROOT / "localization/english/te_buildings_l_english.yml"
GRANT = "state_building_hydro_plant_max_level_add"


def grants(block):
    for key, _, value in buildings.entries(block):
        if key == GRANT or (isinstance(value, (dict, list)) and grants(value)):
            return True
    return False


def cap_raisers():
    """The mod's buildings with a production method that raises the Hydro Plant cap of its state."""
    methods = set()
    for path in buildings.METHOD_FILES:
        for name, _, block in buildings.entries(buildings.parse(path)):
            if isinstance(block, (dict, list)) and grants(block):
                methods.add(buildings.bare(name))
    groups = set()
    for path in buildings.GROUP_FILES:
        for name, _, block in buildings.entries(buildings.parse(path)):
            if set(buildings.field(block, "production_methods") or ()) & methods:
                groups.add(buildings.bare(name))
    return {name for name, (_, block) in buildings.mod_buildings().items()
            if set(buildings.field(block, "production_method_groups") or ()) & groups}


class HydroPlantSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plant = buildings.mod_buildings()["building_hydro_plant"][1]
        cls.possible = buildings.field(cls.plant, "possible")
        cls.tooltip = buildings.field(cls.possible, "custom_tooltip")
        cls.sites = buildings.field(cls.tooltip, "OR")

    def test_a_river_still_qualifies(self):
        self.assertEqual(buildings.field(self.sites, "on_river"), "yes")

    def test_every_building_that_raises_the_cap_is_a_site(self):
        raisers = cap_raisers()
        self.assertIn("building_wonder_hoover_dam", raisers)
        listed = {value for key, _, value in buildings.entries(self.sites) if key == "has_building"}
        self.assertEqual(listed, raisers)

    def test_the_tooltip_has_text_naming_every_dam(self):
        key = buildings.field(self.tooltip, "text")
        text = LOC.read_text(encoding="utf-8-sig")
        line = re.search(rf"^ {key}:0 \"(.*)\"$", text, re.M)
        self.assertIsNotNone(line, f"{key} has no English text")
        for name in cap_raisers():
            self.assertIn(f"${name}$", line.group(1))


if __name__ == "__main__":
    unittest.main()
