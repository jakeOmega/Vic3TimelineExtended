"""Public Housing's level cap: technology-granted, sized to the era's largest rich city.

Design (owner, 2026-11-02): at its cap, a state's Public Housing on the newest
method it has the technology for, multiplied by the crowding tolerance the
technologies give by then, houses between half and all of the world's largest
rich city of that era. The cap is state_building_public_housing_max_level_add
from technologies; each method grants Urban Engineering a level, each point
houses migration_crowding_urban_engineering_pop people, and the threshold
multiplies it by 1 + state_migration_crowding_density_mult. Only the
technologies' tolerance counts here: the Ministry of Urban Planning, the Urban
Planning principle and highways add more where a country invests in them.

For every era this test assumes the technologies of that era and every earlier
one, adds up their cap and tolerance grants, multiplies by the best method's
points and the people a point houses, and checks the result against TARGETS.
A change to a method's points, a cap grant or a tolerance grant that moves an
era out of its band fails here.

docs/systems/mod_systems/pops_and_migration.md § Public Housing has the table.

Run: python3 -m unittest test_public_housing_cap -v
"""
import json
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
BUILDING = "building_public_housing"
CAP = "state_building_public_housing_max_level_add"
POINTS = "state_building_construction_sector_max_level_add"  # Urban Engineering
TOLERANCE = "state_migration_crowding_density_mult"

# Era -> (people, the city it stands for). Urban areas: Greater London's
# censuses to 1911, New York's metropolitan district in the 1930 and 1940
# censuses, then the UN's World Urbanization Prospects (2018) for New York-Newark
# and Tokyo. "Rich" leaves out Tokyo until Japan was (about 1970).
TARGETS = {
    1: (2.0e6, "London in 1836"),
    2: (2.9e6, "London in 1856"),
    3: (4.3e6, "London in 1876"),
    4: (6.1e6, "London in 1896"),
    5: (7.2e6, "London in 1911"),
    6: (11.0e6, "New York in the 1930s"),
    7: (13.5e6, "New York in 1956"),
    8: (27.0e6, "Tokyo in 1977"),
    9: (34.4e6, "Tokyo in 2000"),
    10: (37.4e6, "Tokyo in 2020"),
}
# Eras 11-13 have no real city to aim at; their grants are in the system doc.
BAND = (0.5, 1.0)


def _unwrap(value):
    while isinstance(value, (tuple, list)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def _parse(rel):
    parser = ParadoxFileParser()
    parser.parse_file(str(ROOT / rel), apply_directives=False)
    return {name: _unwrap(body) for name, body in parser.data.items()}


def _number(block, key):
    value = _unwrap(block.get(key)) if isinstance(block, dict) else None
    return float(value) if value is not None else None


def _era(name, mod_eras, vanilla):
    if name in mod_eras:
        return mod_eras[name]
    era = _unwrap(_unwrap(vanilla[name]).get("era"))
    return int(era.removeprefix("era_"))


class PublicHousingCapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vanilla = json.loads((ROOT / "vanilla_parsed/common/technologies.json").read_text(encoding="utf-8"))
        cls.mod_eras, cls.grants, cls.tolerance = {}, {}, {}
        for path in sorted((ROOT / "common/technology/technologies").glob("*.txt")):
            for name, body in _parse(path.relative_to(ROOT)).items():
                if not isinstance(body, dict):
                    continue
                tech = name.split(":")[-1]
                era = _unwrap(body.get("era"))
                if era and not name.startswith(("INJECT:", "REPLACE:")):
                    cls.mod_eras[tech] = int(era.removeprefix("era_"))
                modifier = _unwrap(body.get("modifier"))
                for key, into in ((CAP, cls.grants), (TOLERANCE, cls.tolerance)):
                    grant = _number(modifier, key)
                    if grant:
                        into[tech] = into.get(tech, 0) + grant
        cls.building = _parse("common/buildings/extra_buildings.txt")[BUILDING]
        pms = _parse("common/production_methods/extra_pms.txt")
        group = _parse("common/production_method_groups/extra_pm_groups.txt")["pmg_base_building_public_housing"]
        cls.methods = {}
        for pm in _unwrap(group["production_methods"]):
            body = pms[pm]
            techs = _unwrap(body.get("unlocking_technologies")) or []
            points = _number(_unwrap(_unwrap(body["state_modifiers"]).get("workforce_scaled")), POINTS)
            cls.methods[pm] = (techs, points)
        values = (ROOT / "common/script_values/extra_script_values.txt").read_text(encoding="utf-8-sig")
        cls.people_per_point = float(re.search(r"(?m)^migration_crowding_urban_engineering_pop = (\d+)", values)[1])

    def era(self, tech):
        return _era(tech, self.mod_eras, self.vanilla)

    def test_the_building_has_a_max_level(self):
        self.assertEqual(_unwrap(self.building.get("has_max_level")), "yes")

    def test_the_cap_modifier_is_registered(self):
        # the engine ignores an unregistered state_building_<X>_max_level_add, so no cap would apply
        types = _parse("common/modifier_type_definitions/mod_entity_modifier_types.txt")
        self.assertIn(CAP, types)
        self.assertEqual(_unwrap(types[CAP].get("percent")), "no")

    def test_the_unlocking_technology_grants_levels(self):
        # with no grant from it, the building would unlock at a cap of 0
        for tech in _unwrap(self.building["unlocking_technologies"]):
            with self.subTest(tech=tech):
                self.assertGreater(self.grants.get(tech, 0), 0)

    def test_no_grant_outside_technologies(self):
        base = _parse("common/static_modifiers/extra_modifiers.txt")["INJECT:base_values"]
        self.assertIsNone(_number(base, CAP))

    def test_capacity_at_cap_tracks_the_largest_rich_city(self):
        for era, (target, city) in TARGETS.items():
            cap = sum(n for tech, n in self.grants.items() if self.era(tech) <= era)
            points = max(p for techs, p in self.methods.values()
                         if all(self.era(t) <= era for t in techs))
            tolerance = sum(n for tech, n in self.tolerance.items() if self.era(tech) <= era)
            housed = cap * points * self.people_per_point * (1 + tolerance)
            with self.subTest(era=era, city=city, cap=cap, points=points, tolerance=tolerance, housed=housed):
                self.assertGreaterEqual(housed / target, BAND[0])
                self.assertLessEqual(housed / target, BAND[1])


if __name__ == "__main__":
    unittest.main()
