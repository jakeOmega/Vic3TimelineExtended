"""The AI conscript refresh (common/scripted_effects/te_ai_conscript_refresh_effects.txt, #1877 trap 5).

The AI never upgrades a conscript battalion once it exists, though it keeps each formation's default unit types at its
best unlocked type. So once a year an AI country at peace (no war, no formation mobilized, no diplomatic play) has its
conscription centres removed wherever one holds a battalion three or more eras behind a type of the same unit group
it has unlocked, and the AI rebuilds them in its current defaults (measured 2026-11-18: within a month, in modern
types). A cleared state waits five years before it can be cleared again. TE_SELF_CHECK ai_conscript_refresh follows
the first cleared state for three months. Design: docs/superpowers/specs/2026-11-18-ai-conscript-refresh-design.md.

The stale rule is one trigger line per old type, and the test below derives those lines from the unit-type and
technology data, so a unit type the mod adds later fails here until its line is written.

Run: python3 -m pytest test_ai_conscript_refresh.py -q
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/te_ai_conscript_refresh_triggers.txt"
EFFECTS = ROOT / "common/scripted_effects/te_ai_conscript_refresh_effects.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_ai_conscript_refresh_on_actions.txt"
VALUES = ROOT / "common/script_values/te_ai_conscript_refresh_values.txt"
UNIT_DIR = ROOT / "common/combat_unit_types"
TECH_DIR = ROOT / "common/technology/technologies"
VANILLA_UNITS = ROOT / "vanilla_parsed/common/combat_unit_types.json"
VANILLA_TECHS = ROOT / "vanilla_parsed/common/technologies.json"

# The land groups whose conscripts the pass reads; ship groups have no conscripts.
LAND_GROUPS = {"combat_unit_group_infantry", "combat_unit_group_cavalry", "combat_unit_group_artillery",
               "combat_unit_group_tanks", "combat_unit_group_marines", "combat_unit_group_aircraft"}
# Owner-approved design, 2026-11-18: stale at three eras behind.
ERA_GAP = 3


def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text(encoding="utf-8-sig").splitlines())


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


def _block(text, name):
    """The body of the top-level block `name = { ... }`, by brace count."""
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if m is None:
        raise KeyError(name)
    return _body(text, m.end())


def _body(text, start):
    depth, i = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[start:i - 1]


def _top_blocks(text):
    """(directive, name, body) for every top-level `NAME = {`."""
    for m in re.finditer(r"(?m)^(INJECT:|REPLACE:)?([A-Za-z0-9_]+) = \{", text):
        yield m.group(1) or "", m.group(2), _body(text, m.end())


def _field_list(body, key):
    m = re.search(rf"\b{key} = \{{([^}}]*)\}}", body)
    return m.group(1).split() if m else None


def tech_eras():
    """{technology: era number}, vanilla's snapshot with the mod's technology files over it."""
    eras = {name: int(entry[1]["era"][1].split("_")[1])
            for name, entry in json.loads(VANILLA_TECHS.read_text(encoding="utf-8")).items()
            if isinstance(entry[1], dict) and "era" in entry[1]}
    for path in sorted(TECH_DIR.glob("*.txt")):
        for _, name, body in _top_blocks(_code(path)):
            era = re.search(r"\bera = era_(\d+)", body)
            if era:
                eras[name] = int(era.group(1))
    return eras


def land_unit_types():
    """{unit type: (group, unlocking technologies)} for the land groups: vanilla's, then the mod's over it."""
    types = {}
    for name, entry in json.loads(VANILLA_UNITS.read_text(encoding="utf-8")).items():
        block = entry[1]
        types[name] = (block["group"][1], list((block.get("unlocking_technologies") or [None, []])[1]))
    for path in sorted(UNIT_DIR.glob("*.txt")):
        for directive, name, body in _top_blocks(_code(path)):
            group = re.search(r"\bgroup = (\w+)", body)
            techs = _field_list(body, "unlocking_technologies")
            if directive == "INJECT:":
                old_group, old_techs = types[name]
                types[name] = (group.group(1) if group else old_group, techs if techs is not None else old_techs)
            else:
                types[name] = (group.group(1) if group else None, techs or [])
    return {name: value for name, value in types.items() if value[0] in LAND_GROUPS}


def unit_era(techs, eras):
    """A unit type's era: its earliest unlocking technology's; Irregular Infantry, which none unlocks, is era 0."""
    return min(eras[t] for t in techs) if techs else 0


def expected_rule():
    """{old type: the technologies that make it stale}: every technology unlocking a type of its group at least
    ERA_GAP eras newer."""
    eras, types = tech_eras(), land_unit_types()
    rule = {}
    for name, (group, techs) in types.items():
        era = unit_era(techs, eras)
        stale = {tech for other, (other_group, other_techs) in types.items()
                 if other_group == group and unit_era(other_techs, eras) >= era + ERA_GAP for tech in other_techs}
        if stale:
            rule[name] = stale
    return rule


def trigger_rule():
    """The same table as te_ai_conscript_unit_stale writes it."""
    body = _norm(_block(_code(TRIGGERS), "te_ai_conscript_unit_stale"))
    rule = {}
    for m in re.finditer(r"AND = \{ has_unit_type = unit_type:(combat_unit_type_\w+) "
                         r"owner = \{ OR = \{ ((?:has_technology_researched = \w+ ?)+)\} \} \}", body):
        rule[m.group(1)] = set(re.findall(r"has_technology_researched = (\w+)", m.group(2)))
    return rule


class TheStaleRule(unittest.TestCase):
    def test_stale_rule_matches_the_unit_and_technology_data(self):
        expected, written = expected_rule(), trigger_rule()
        missing = {t: sorted(v) for t, v in expected.items() if written.get(t) != v}
        extra = sorted(set(written) - set(expected))
        self.assertEqual((missing, extra), ({}, []),
                         "te_ai_conscript_unit_stale must hold one line per old type, its OR the technologies "
                         "unlocking a same-group type at least three eras newer")

    def test_the_trigger_is_nothing_but_those_lines(self):
        body = _norm(_block(_code(TRIGGERS), "te_ai_conscript_unit_stale"))
        self.assertTrue(body.startswith("OR = {"))
        self.assertEqual(body.count("has_unit_type"), len(trigger_rule()))

    def test_the_types_the_owner_was_shown(self):
        rule = expected_rule()
        for old, tech in (("combat_unit_type_irregular_infantry", "trench_works"),
                          ("combat_unit_type_line_infantry", "trench_works"),
                          ("combat_unit_type_skirmish_infantry", "nco_training"),
                          ("combat_unit_type_lancers", "mobile_armor"),
                          ("combat_unit_type_hussars", "mobile_armor"),
                          ("combat_unit_type_cannon_artillery", "defense_in_depth"),
                          ("combat_unit_type_shrapnel_artillery", "motorized_artillery"),
                          ("combat_unit_type_low_tier_marines", "landing_craft")):
            with self.subTest(old=old):
                self.assertIn(tech, rule[old])
        # One or two eras behind is not stale.
        self.assertNotIn("mobile_armor", rule["combat_unit_type_trench_infantry"])
        self.assertNotIn("trench_works", rule["combat_unit_type_skirmish_infantry"])
        self.assertNotIn("breech_loading_artillery", rule["combat_unit_type_cannon_artillery"])

    def test_a_centre_is_stale_when_any_of_its_battalions_is(self):
        body = _norm(_block(_code(TRIGGERS), "te_ai_conscript_centre_stale"))
        self.assertEqual(body, "has_building = building_conscription_center b:building_conscription_center = { "
                               "any_combat_unit = { te_ai_conscript_unit_stale = yes } }")


class WhoAndWhen(unittest.TestCase):
    def test_the_pass_runs_only_for_an_ai_at_peace(self):
        may = _norm(_block(_code(TRIGGERS), "te_ai_conscript_refresh_may"))
        for part in ("is_ai = yes", "is_at_war = no", "is_diplomatic_play_committed_participant = no",
                     "is_diplomatic_play_undecided_participant = no",
                     "NOT = { any_military_formation = { is_mobilized = yes } }"):
            with self.subTest(part=part):
                self.assertIn(part, may)


if __name__ == "__main__":
    unittest.main()
