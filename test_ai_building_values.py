"""Building `ai_value` where vanilla gives the same role one and the mod's building had none (#1822).

A building with no `ai_value` scores the engine's base (NAI GOVERNMENT_BUILDING_BASE_VALUE and
PRODUCTION_BUILDING_BASE_VALUE, both 1000) and the engine logs nothing. So:

- every government-funded building the mod adds that the construction queue can start carries an `ai_value`, or is on
  PLACED_BY_SCRIPT with what places it (the mod's own checklist: scripting_best_practices.md § Checklist for New
  Buildings/Goods, item 6);
- the mod's four power plants take vanilla's first-plant bonus, and "the state has a power plant" names every
  building of the power group, for vanilla's plant too, whose restated `ai_value` is held to vanilla's;
- Highway, Airport and Network Infrastructure carry vanilla's railway base, the wonders vanilla's monument value,
  and the megaprojects' sites a value that is nothing in default.

The numbers are in common/script_values/te_ai_coverage_values.txt; docs/systems/mod_systems/ai.md § AI Coverage of
the Mod's Content says what each stands on. Every value is written `ai_value = { value = <script value> }`, the
form the company flagships already use; a bare name there is a form no vanilla or mod building has.
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


def script_value_number(name):
    text = re.sub(r"#[^\n]*", "", VALUES.read_text(encoding="utf-8-sig"))
    m = re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*(-?[\d.]+)\s*$", text)
    return float(m.group(1)) if m else None


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
        cls.groups = building_groups()
        cls.buildings = mod_buildings()
        cls.vanilla_buildings = vanilla("buildings")

    def ai_value(self, name):
        return plain(field(self.buildings[name][1], "ai_value"))

    def test_clean_power_plants_take_vanillas_power_plant_value(self):
        for name in CLEAN_POWER:
            with self.subTest(building=name):
                self.assertEqual(self.ai_value(name), [["value", "te_clean_power_plant_ai_value"]])
        vanilla_value = vanilla_block(self.vanilla_buildings["building_power_plant"])
        ai = dict((k, v) for k, v in field_pairs(vanilla_value, "ai_value"))
        self.assertEqual(float(ai["value"]), script_value_number("te_ai_power_plant_base_value"))
        first = [v for k, v in field_pairs(vanilla_value, "ai_value") if k == "if"][0]
        self.assertEqual(float(dict(first)["add"]), script_value_number("te_ai_first_power_plant_bonus"))
        value = plain(field(parse(VALUES), "te_clean_power_plant_ai_value"))
        self.assertEqual(value, [["value", "te_ai_power_plant_base_value"],
                                 ["if", [["limit", [["te_state_has_a_power_plant", "no"]]],
                                         ["add", "te_ai_first_power_plant_bonus"]]]])

    def test_every_power_building_counts_as_a_power_plant(self):
        power = {name for name, entry in self.vanilla_buildings.items()
                 if "bg_power" in chain(field(entry[1], "building_group"), self.groups)}
        power |= {name for name, (_, block) in self.buildings.items()
                  if "bg_power" in chain(field(block, "building_group"), self.groups)}
        self.assertEqual(power, {"building_power_plant", *CLEAN_POWER})
        trigger = field(parse(TRIGGERS), "te_state_has_a_power_plant")
        either = field(trigger, "OR")
        built = {v for k, _, v in entries(either) if k == "has_building"}
        under_way = field(either, "any_scope_building")
        self.assertEqual(field(under_way, "is_under_construction"), "yes")
        queued = {v for k, _, v in entries(field(under_way, "OR")) if k == "is_building_type"}
        self.assertEqual(built, queued)
        self.assertLessEqual(power, built, "a power building the first-plant test does not count")
        self.assertEqual(built - power, {"building_solar_receiver"})  # makes Electricity outside the power group

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
        # The one change: vanilla's NOR on building_power_plant alone becomes the any-plant test, at vanilla's 4000.
        self.assertEqual(theirs[1][1][0][0], "limit")
        self.assertEqual(theirs[1][1][0][1][0][0], "NOR")
        self.assertEqual(theirs[1][1][1], ["add", "4000"])
        self.assertEqual(injected[1], ["if", [["limit", [["te_state_has_a_power_plant", "no"]]],
                                              ["add", "te_ai_first_power_plant_bonus"]]])

    def test_infrastructure_takes_vanillas_railway_base(self):
        for name in INFRASTRUCTURE:
            with self.subTest(building=name):
                self.assertEqual(self.ai_value(name), [["value", "te_infrastructure_ai_value"]])
        railway = dict(field_pairs(vanilla_block(self.vanilla_buildings["building_railway"]), "ai_value"))
        self.assertEqual(float(railway["value"]), script_value_number("te_infrastructure_ai_value"))

    def test_wonders_take_vanillas_monument_value(self):
        names = [name for name, _, _ in entries(parse(WONDERS))]
        self.assertGreaterEqual(len(names), 39)
        for name in names:
            with self.subTest(building=name):
                self.assertEqual(self.ai_value(name), [["value", "te_wonder_ai_value"]])
        eiffel = field(self.vanilla_buildings["building_eiffel_tower"][1], "ai_value")
        self.assertEqual(float(eiffel), script_value_number("te_wonder_ai_value"))

    def test_megaproject_sites_are_worth_nothing_in_default(self):
        for name in MEGAPROJECT_VALUED:
            with self.subTest(building=name):
                self.assertEqual(self.ai_value(name), [["value", "te_megaproject_ai_value"]])
        value = plain(field(parse(VALUES), "te_megaproject_ai_value"))
        self.assertEqual(value[0], ["value", "te_ai_megaproject_base_value"])
        self.assertEqual(script_value_number("te_ai_megaproject_base_value"), 1000)  # NAI GOVERNMENT_BUILDING_BASE_VALUE
        self.assertEqual(value[1], ["if", [["limit", [["owner", [["OR", [["in_default", "yes"],
                                                                         ["has_modifier", "declared_bankruptcy"]]]]]]],
                                           ["multiply", "0"]]])


def field_pairs(block, key):
    """The [key, value] pairs inside the first `key` block of a `plain`-shaped block."""
    return next(value for k, value in block if k == key)


if __name__ == "__main__":
    unittest.main()
