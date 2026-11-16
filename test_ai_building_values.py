"""Building `ai_value` for the mod's government buildings, and the first-plant test on vanilla's power plant (#1822).

A building with no `ai_value` scores the engine's base (NAI GOVERNMENT_BUILDING_BASE_VALUE and
PRODUCTION_BUILDING_BASE_VALUE, both 1000) and the engine logs nothing. AI governments queue one construction at a
time and most are insolvent, so nothing here asks for more than that base (docs/systems/mod_systems/ai.md § AI
Coverage of the Mod's Content). What the tests hold is each rule, not a number the play-test list says to tune:

- every government-funded building the mod adds that the construction queue can start carries an `ai_value`, or is on
  PLACED_BY_SCRIPT with what places it (the mod's own checklist: scripting_best_practices.md § Checklist for New
  Buildings/Goods, item 6);
- the wonders and the megaprojects' sites use a named value that is nothing for a country in default;
- Highway, Airport and Network Infrastructure use a named value, so the size can be tuned in one place;
- vanilla's power plant is restated with one change: its first-plant bonus asks whether anything in the state makes
  Electricity (te_state_has_a_power_plant), and that trigger names every building whose methods output Electricity;
- the mod's own power plants carry no `ai_value` (no first-plant bonus: they cost 2,000 to 10,000 points).

Every value is written `ai_value = { value = <script value> }`, the form the company flagships already use; a bare
name there is a form no vanilla or mod building has.
"""
import json
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
BUILDING_FILES = sorted((ROOT / "common/buildings").glob("*.txt"))
VALUES = ROOT / "common/script_values/te_ai_coverage_values.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_ai_coverage_triggers.txt"
WONDERS = ROOT / "common/buildings/08_zz_te_wonders.txt"

# Government-funded buildings the queue can't start, or that script starts for the AI, and what places each.
PLACED_BY_SCRIPT = {
    "building_solar_collector": "generic_wonder_construction_base, when its construction site completes",
    "building_orbital_battlestation": "generic_wonder_construction_base, when its construction site completes",
    "building_antimatter_facility": "generic_wonder_construction_base, when its construction site completes",
    "building_consciousness_network": "generic_wonder_construction_base, when its construction site completes",
    "building_space_program": "te_decision_found_space_program (its ai_chance carries the AI's conditions)",
}
# The four megaprojects above can't be started from the queue: `potential` asks for the building itself, and the
# only max level comes from the building's own method, a level at a time.
SELF_POTENTIAL = ("building_solar_collector", "building_orbital_battlestation", "building_antimatter_facility",
                  "building_consciousness_network")

MEGAPROJECT_VALUED = tuple(
    f"building_{name}_construction_site"
    for name in ("space_elevator", "solar_collector", "orbital_battlestation", "mind_upload_nexus",
                 "antimatter_facility", "nanofabrication_center", "consciousness_network")
) + ("building_antimatter_warhead_plant",)
CLEAN_POWER = ("building_hydro_plant", "building_nuclear_plant", "building_renewable_energy_plant",
               "building_fusion_plant")
METHOD_FILES = sorted((ROOT / "common/production_methods").glob("*.txt"))
GROUP_FILES = sorted((ROOT / "common/production_method_groups").glob("*.txt"))
INSOLVENT = [["owner", [["OR", [["in_default", "yes"], ["has_modifier", "declared_bankruptcy"]]]]]]
INFRASTRUCTURE = ("building_airport", "building_highway", "building_network_infrastructure")


def entries(node):
    for part in node if isinstance(node, list) else [node]:
        if isinstance(part, dict):
            for key, (op, value) in part.items():
                yield key, op, value


def parse_text(text):
    parser = ParadoxFileParser()
    return parser.parse_object(parser.tokenize("{" + text + "}"))[0]


def parse(path):
    return parse_text(path.read_text(encoding="utf-8-sig"))


def field(block, key):
    return next((value for k, _, value in entries(block) if k == key), None)


def bare(name):
    return name.split(":")[-1]


def plain(node):
    """A parsed block as nested lists of [key, value], so the mod's parse compares with the snapshot's JSON."""
    if isinstance(node, (dict, list)):
        return [[key, plain(value)] for key, _, value in entries(node)]
    return node


def vanilla(name):
    return json.loads((ROOT / f"vanilla_parsed/common/{name}.json").read_text(encoding="utf-8"))


def vanilla_block(entry):
    """A snapshot entry ([op, {key: [op, value]}], repeated keys as lists) in the shape `plain` gives."""
    def walk(value):
        if isinstance(value, dict):
            out = []
            for key, item in value.items():
                items = item if isinstance(item[0], list) else [item]
                out.extend([key, walk(v)] for _, v in items)
            return out
        return value
    return walk(entry[1])


def building_groups():
    """{group: (parent, is_government_funded)} over vanilla's snapshot and the mod's files."""
    groups = {name: (field(entry[1], "parent_group"), field(entry[1], "is_government_funded"))
              for name, entry in vanilla("building_groups").items()}
    for path in sorted((ROOT / "common/building_groups").glob("*.txt")):
        for name, _, block in entries(parse(path)):
            parent, funded = groups.get(bare(name), (None, None))
            groups[bare(name)] = (field(block, "parent_group") or parent,
                                  field(block, "is_government_funded") or funded)
    return groups


def chain(group, groups):
    seen = []
    while group and group not in seen:
        seen.append(group)
        group = groups.get(group, (None, None))[0]
    return seen


def government_funded(group, groups):
    for name in chain(group, groups):
        funded = groups.get(name, (None, None))[1]
        if funded is not None:
            return funded == "yes"
    return False


def mod_buildings():
    """{building: (file, block)} for the buildings the mod defines or replaces; INJECTs are left to vanilla."""
    out = {}
    for path in BUILDING_FILES:
        for name, _, block in entries(parse(path)):
            if not name.startswith("INJECT:"):
                out[bare(name)] = (path.name, block)
    return out


def outputs_electricity(block):
    for key, _, value in entries(block):
        if key == "goods_output_electricity_add":
            try:
                if float(value) > 0:
                    return True
            except (TypeError, ValueError):
                return True  # a script value: count it
        elif isinstance(value, (dict, list)) and outputs_electricity(value):
            return True
    return False


def electricity_makers():
    """Every building, vanilla's or the mod's, with a production method that outputs Electricity."""
    methods = {name for name, entry in vanilla("pms").items() if outputs_electricity(entry[1])}
    for path in METHOD_FILES:
        for name, _, block in entries(parse(path)):
            if isinstance(block, (dict, list)) and outputs_electricity(block):
                methods.add(bare(name))
    groups = {name: set(field(entry[1], "production_methods") or ()) for name, entry in vanilla("pm_groups").items()}
    for path in GROUP_FILES:
        for name, _, block in entries(parse(path)):
            listed = set(field(block, "production_methods") or ())
            if name.startswith("INJECT:"):
                groups.setdefault(bare(name), set()).update(listed)
            else:
                groups[bare(name)] = listed
    making = {name for name, listed in groups.items() if listed & methods}
    buildings = {name: set(field(entry[1], "production_method_groups") or ())
                 for name, entry in vanilla("buildings").items()}
    for path in BUILDING_FILES:
        for name, _, block in entries(parse(path)):
            listed = set(field(block, "production_method_groups") or ())
            if name.startswith("INJECT:"):
                buildings.setdefault(bare(name), set()).update(listed)
            else:
                buildings[bare(name)] = listed
    return {name for name, listed in buildings.items() if listed & making}


class GovernmentBuildingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = building_groups()
        cls.buildings = mod_buildings()

    def test_every_buildable_government_building_has_an_ai_value_or_is_placed_by_script(self):
        missing, checked = [], 0
        for name, (file, block) in self.buildings.items():
            if not government_funded(field(block, "building_group"), self.groups):
                continue
            if field(block, "buildable") == "no":
                continue  # never offered to the queue
            checked += 1
            if field(block, "ai_value") is None and name not in PLACED_BY_SCRIPT:
                missing.append(f"{file}: {name}")
        self.assertGreater(checked, 60)
        self.assertEqual(missing, [], "a government building with no ai_value scores the engine's base wherever "
                                      "`possible` allows: give it one, or list what places it")

    def test_the_placed_by_script_list_is_current(self):
        for name in PLACED_BY_SCRIPT:
            with self.subTest(building=name):
                self.assertIn(name, self.buildings)
                self.assertIsNone(field(self.buildings[name][1], "ai_value"),
                                  "it has an ai_value now: take it off PLACED_BY_SCRIPT")

    def test_megaprojects_cannot_be_started_from_the_queue(self):
        effects = (ROOT / "common/scripted_effects/extra_effects.txt").read_text(encoding="utf-8-sig")
        self.assertIn("create_building = { building = building_$WONDER$ level = 1 }", effects)
        methods = (ROOT / "common/production_methods/extra_pms.txt").read_text(encoding="utf-8-sig")
        for name in SELF_POTENTIAL:
            with self.subTest(building=name):
                block = self.buildings[name][1]
                self.assertEqual(field(field(block, "potential"), "has_building"), name)
                self.assertEqual(field(block, "has_max_level"), "yes")
                grants = re.findall(r"state_" + name + r"_max_level_add\s*=\s*(\S+)", methods)
                self.assertEqual(grants, ["1"], "its only max level is the one its own method grants per level")
                short = name.removeprefix("building_")
                self.assertRegex(effects, r"(?m)^" + short + r"_construction\s*=\s*\{\s*generic_wonder_construction_base")

    def test_the_space_program_is_placed_by_its_decision(self):
        decisions = (ROOT / "common/decisions/extra_decisions.txt").read_text(encoding="utf-8-sig")
        self.assertRegex(decisions, r"building\s*=\s*building_space_program\b")


class ValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.buildings = mod_buildings()
        cls.vanilla_buildings = vanilla("buildings")
        cls.values = parse(VALUES)
        cls.triggers = parse(TRIGGERS)

    def ai_value(self, name):
        return plain(field(self.buildings[name][1], "ai_value"))

    def assert_nothing_in_default(self, name, base):
        """`name` is a script value: a named base, times 0 while the state's owner is insolvent."""
        value = plain(field(self.values, name))
        self.assertEqual(value, [["value", base],
                                 ["if", [["limit", [["te_state_owner_is_insolvent", "yes"]]], ["multiply", "0"]]]])
        self.assertGreater(float(field(self.values, base)), 0)

    def test_insolvent_means_in_default_or_bankrupt(self):
        self.assertEqual(plain(field(self.triggers, "te_state_owner_is_insolvent")), INSOLVENT)
        text = re.sub(r"#[^\n]*", "", TRIGGERS.read_text(encoding="utf-8-sig"))
        self.assertRegex(text, r"te_state_owner_is_insolvent\s*=\s*\{\s*owner\s*\?=")  # state scope: guard the link

    def test_wonders_use_a_value_that_is_nothing_in_default(self):
        names = [name for name, _, _ in entries(parse(WONDERS))]
        self.assertGreaterEqual(len(names), 39)
        for name in names:
            with self.subTest(building=name):
                self.assertEqual(self.ai_value(name), [["value", "te_wonder_ai_value"]])
        self.assert_nothing_in_default("te_wonder_ai_value", "te_ai_wonder_base_value")

    def test_a_wonder_does_not_outrank_a_university(self):
        # One government construction is queued at a time: a wonder (5,000 points, 10,000 government employees)
        # must not score above the building that makes innovation. Vanilla's university is 2000.
        university = field(self.vanilla_buildings["building_university"][1], "ai_value")
        self.assertLess(float(field(self.values, "te_ai_wonder_base_value")), float(field(university, "value")))

    def test_megaproject_sites_are_worth_nothing_in_default(self):
        for name in MEGAPROJECT_VALUED:
            with self.subTest(building=name):
                self.assertEqual(self.ai_value(name), [["value", "te_megaproject_ai_value"]])
        self.assert_nothing_in_default("te_megaproject_ai_value", "te_ai_megaproject_base_value")

    def test_infrastructure_uses_its_named_value(self):
        for name in INFRASTRUCTURE:
            with self.subTest(building=name):
                self.assertEqual(self.ai_value(name), [["value", "te_infrastructure_ai_value"]])
        self.assertGreater(float(field(self.values, "te_infrastructure_ai_value")), 0)

    def test_the_mods_power_plants_take_no_first_plant_bonus(self):
        for name in CLEAN_POWER:
            with self.subTest(building=name):
                self.assertIsNone(field(self.buildings[name][1], "ai_value"))

    def test_every_electricity_maker_counts_as_a_power_plant(self):
        makers = electricity_makers()
        self.assertGreaterEqual(len(makers), 16)
        self.assertLessEqual({"building_power_plant", "building_grid_transfer_station", *CLEAN_POWER}, makers)
        either = field(field(self.triggers, "te_state_has_a_power_plant"), "OR")
        built = {v for k, _, v in entries(either) if k == "has_building"}
        under_way = field(either, "any_scope_building")
        self.assertEqual(field(under_way, "is_under_construction"), "yes")
        queued = {v for k, _, v in entries(field(under_way, "OR")) if k == "is_building_type"}
        self.assertEqual(built, queued)
        self.assertEqual(built, makers, "the first-plant test and the buildings that output Electricity differ")

    def test_vanillas_power_plant_is_restated_with_the_wider_test(self):
        injected = None
        for path in BUILDING_FILES:
            for name, _, block in entries(parse(path)):
                if name == "INJECT:building_power_plant" and field(block, "ai_value") is not None:
                    self.assertIsNone(injected, "two INJECTs restate the field")
                    injected = plain(field(block, "ai_value"))
        self.assertIsNotNone(injected)
        theirs = [v for k, v in vanilla_block(self.vanilla_buildings["building_power_plant"]) if k == "ai_value"][0]
        self.assertEqual([k for k, _ in injected], [k for k, _ in theirs])
        self.assertEqual(injected[0], theirs[0])   # value = 1000
        self.assertEqual(injected[2], theirs[2])   # the Five-Year Plan branch, unchanged
        # The one change: vanilla's NOR on building_power_plant alone becomes the any-maker test; the bonus is vanilla's.
        self.assertEqual(theirs[1][1][0][0], "limit")
        self.assertEqual(theirs[1][1][0][1][0][0], "NOR")
        self.assertEqual(injected[1], ["if", [["limit", [["te_state_has_a_power_plant", "no"]]], theirs[1][1][1]]])


if __name__ == "__main__":
    unittest.main()
