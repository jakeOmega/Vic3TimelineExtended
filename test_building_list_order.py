"""Building list order and production method group order.

The building browser's default sort, and its Building Type column, is the
engine's database order: the order building definitions load. File names load
in ASCII order, vanilla's and the mod's in one list, so a mod building sits
after vanilla's `NN_*.txt` when its file is named `NN_zz_te_*.txt` (the mod's
new mines after Gold Fields, its power plants after Power Plant). `zz` sorts
after every lowercase vanilla stem, so one scheme serves `06_urban_center.txt`,
which a `06_te_` name would precede. The building must be a bare definition: a
`*_OR_CREATE` applies after every bare definition is read, so the entry it
creates may land at the end. A REPLACE keeps the vanilla building's place;
INJECT never moves one.

An INJECT appends its production method groups in file order too, so the
generated carbon capture injects load last (`zz_te_carbon_capture_injects.txt`)
and every pollution control group follows the production groups in the panel.

Rule and file map: docs/guides/scripting_best_practices.md § Load Order (probed
2026-10-26), "Building list order".

Run: python3 test_building_list_order.py
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILDINGS = ROOT / "common" / "buildings"
SECTOR_FILE = re.compile(r"^(\d\d)_zz_te_[a-z0-9_]+\.txt$")
DEFINITION = re.compile(r"^(?:([A-Z_]+):)?(\w+)\s*=\s*\{", re.M)

# Files whose new buildings may load after every vanilla building: the company
# buildings follow vanilla's last file (14_companies.txt, Company Headquarters);
# the hidden solar sites and the construction market site are never listed.
TAIL_FILES = {"company_buildings.txt", "sr_site_buildings_generated.txt", "te_construction_market_site.txt"}
# The space buildings and megastructures, which close the list as a block of their own.
TAIL_BUILDINGS = {
    "extra_buildings.txt": {
        "building_space_program", "building_space_mine",
        "building_space_elevator_construction_site", "building_space_elevator",
        "building_solar_collector_construction_site", "building_solar_collector", "building_solar_receiver",
        "building_orbital_battlestation_construction_site", "building_orbital_battlestation",
        "building_mind_upload_nexus_construction_site", "building_mind_upload_nexus",
        "building_antimatter_facility_construction_site", "building_antimatter_facility",
        "building_antimatter_engine", "building_antimatter_warhead_plant",
        "building_nanofabrication_center_construction_site", "building_nanofabrication_center",
        "building_consciousness_network_construction_site", "building_consciousness_network",
    },
}
# A production method group that cuts pollution or greenhouse gas, with no method making goods.
CUT = re.compile(r"^state_(pollution_generation|greenhouse_gas_emissions)_(add|mult)$")


def _vanilla_files():
    manifest = json.loads((ROOT / "vanilla_parsed" / "manifest.json").read_text(encoding="utf-8"))
    return sorted(Path(source).name for source in manifest["sources"] if source.startswith("game/common/buildings/"))


def _mod_files():
    return sorted(path.name for path in BUILDINGS.glob("*.txt"))


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


class SectorFileTest(unittest.TestCase):
    def test_vanilla_building_files_are_known(self):
        self.assertIn("01_industry.txt", _vanilla_files())
        self.assertIn("14_companies.txt", _vanilla_files())

    def test_no_mod_file_replaces_a_vanilla_file(self):
        self.assertEqual(sorted(set(_vanilla_files()) & set(_mod_files())), [])

    def test_a_numbered_mod_file_is_a_sector_file(self):
        numbers = {name[:2] for name in _vanilla_files()}
        for name in _mod_files():
            if name[0].isdigit():
                match = SECTOR_FILE.match(name)
                self.assertIsNotNone(match, f"{name}: name a mod building file NN_zz_te_<topic>.txt")
                self.assertIn(match.group(1), numbers, f"{name}: no vanilla file {match.group(1)}_*.txt to follow")

    def test_each_sector_file_follows_its_vanilla_file(self):
        """File names compare in ASCII byte order (§ Load Order, fact 1)."""
        vanilla = _vanilla_files()
        for name in _mod_files():
            if not SECTOR_FILE.match(name):
                continue
            own = next(v for v in vanilla if v[:2] == name[:2])
            merged = sorted(vanilla + [name], key=lambda file: file.encode())
            before = merged[merged.index(name) - 1]
            self.assertEqual(before, own, f"{name}: follows {before}, not {own}")

    def test_a_sector_file_creates_no_entry_by_directive(self):
        """A `*_OR_CREATE` applies after every bare definition (§ Load Order, facts 4
        and 7), so a building it creates may not take the file's place."""
        for name in _mod_files():
            if SECTOR_FILE.match(name):
                text = _strip_comments((BUILDINGS / name).read_text(encoding="utf-8-sig"))
                created = [f"{directive}:{key}" for directive, key in DEFINITION.findall(text)
                           if directive.endswith("_OR_CREATE")]
                self.assertEqual(created, [], f"{name}: write these as bare definitions")

    def test_the_carbon_capture_injects_load_last(self):
        """INJECTs apply in ASCII file order (§ Load Order, fact 9)."""
        names = sorted(_mod_files() + _vanilla_files(), key=lambda file: file.encode())
        self.assertEqual(names[-1], "zz_te_carbon_capture_injects.txt")


class NewBuildingPlacementTest(unittest.TestCase):
    def test_a_new_building_sits_in_its_sector(self):
        """A building the mod adds outside a sector file loads after every vanilla
        building, at the bottom of the list. Put it in the NN_zz_te_*.txt file of
        its vanilla peers, or list it here if it belongs at the end."""
        vanilla = set(json.loads((ROOT / "vanilla_parsed" / "common" / "buildings.json").read_text(encoding="utf-8")))
        strays = []
        for name in _mod_files():
            if SECTOR_FILE.match(name) or name in TAIL_FILES:
                continue
            text = _strip_comments((BUILDINGS / name).read_text(encoding="utf-8-sig"))
            for directive, building in DEFINITION.findall(text):
                if directive == "INJECT" or building in vanilla:
                    continue
                if building not in TAIL_BUILDINGS.get(name, set()):
                    strays.append(f"{name}: {building}")
        self.assertEqual(strays, [])

    def test_tail_buildings_still_exist(self):
        for name, buildings in TAIL_BUILDINGS.items():
            text = _strip_comments((BUILDINGS / name).read_text(encoding="utf-8-sig"))
            defined = {building for _, building in DEFINITION.findall(text)}
            self.assertEqual(sorted(buildings - defined), [], name)


class ProductionMethodGroupOrderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT))
        from pm_emissions import load_state, unwrap
        cls.unwrap = staticmethod(unwrap)
        state = load_state(ROOT)
        cls.buildings = state.mod_parsers["Buildings"].data
        cls.groups = state.mod_parsers["PM Groups"].data
        cls.methods = state.mod_parsers["PMs"].data

    def _leaves(self, node, key=None):
        node = self.unwrap(node)
        if isinstance(node, dict):
            for child_key, child in node.items():
                yield from self._leaves(child, child_key)
        elif isinstance(node, list):
            for child in node:
                yield from self._leaves(child, key)
        else:
            yield key, node

    def _is_control(self, group):
        """A group whose methods cut pollution or greenhouse gas and make no goods:
        carbon capture, scrubbers, filters, emission standards."""
        listed = self.unwrap(self.unwrap(self.groups.get(group, {})).get("production_methods", []))
        cuts = makes = False
        for method in listed:
            for key, value in self._leaves(self.methods.get(method, {})):
                try:
                    number = float(str(value))
                except ValueError:
                    continue
                if key and CUT.match(key) and number < 0:
                    cuts = True
                if key and key.startswith("goods_output_") and key != "goods_output_electricity_add" and number > 0:
                    makes = True
        return cuts and not makes

    def _building_groups(self, building):
        groups = self.unwrap(self.unwrap(self.buildings[building]).get("production_method_groups", []))
        return list(groups) if isinstance(groups, list) else []

    def test_the_classifier_finds_carbon_capture_and_the_hand_written_controls(self):
        used = {group for building in self.buildings for group in self._building_groups(building)}
        controls = {group for group in used if self._is_control(group)}
        self.assertTrue({group for group in used if group.startswith("pmg_carbon_capture_")} <= controls)
        for group in ("pmg_emissions_control", "pmg_industrial_synthesis_scrubbing", "pmg_effluent_filtration"):
            self.assertIn(group, controls)
        for group in ("pmg_synthetic_coal", "pmg_base_building_national_park"):
            self.assertNotIn(group, controls)

    def test_pollution_controls_follow_the_production_groups(self):
        """Maintenance groups are hidden in the panel, so their place doesn't count."""
        late = []
        for building in self.buildings:
            shown = [group for group in self._building_groups(building) if not group.startswith("pmg_maintenance")]
            seen_control = None
            for group in shown:
                if self._is_control(group):
                    seen_control = seen_control or group
                elif seen_control:
                    late.append(f"{building}: {group} after {seen_control}")
        self.assertEqual(late, [])


if __name__ == "__main__":
    os.chdir(ROOT)
    unittest.main()
