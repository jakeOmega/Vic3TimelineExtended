# -*- coding: utf-8 -*-
"""The megaproject sub-building slot gates (#1964, #1965).

The Orbital Solar Collector opens slots for Solar Power Receivers, and the
Antimatter Containment Facility for Antimatter Engines and Warhead Plants
(`docs/systems/mod_systems/wonder_buildings.md`, "Slot gates"). These tests
hold:

- `possible` reads only the slot modifier: the weekly private investment pass
  reads a private type's `possible` in every state, so the exact count, which
  walks the owner's states, sits in `can_build_government` (#1964);
- the count implies the modifier test, so `possible` refuses nothing
  `can_build_government` would allow;
- every level takes a slot: no `has_building` branch, and the branch for a
  level under construction holds the count at `>= 0` (#1965);
- each consumer's -1 is level scaled, a whole slot for every built level,
  staffed or not (#1965).
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

BUILDINGS = os.path.join("common", "buildings", "extra_buildings.txt")
PMS = os.path.join("common", "production_methods", "extra_pms.txt")
VALUES = os.path.join("common", "script_values", "extra_script_values.txt")
LOC = os.path.join("localization", "english", "te_buildings_l_english.yml")

# building: (slot modifier, slot count value, possible's tooltip, the count's tooltip)
GATES = {
    "building_solar_receiver": (
        "country_solar_receiver_max_level_add",
        "solar_receiver_slots_remaining",
        "building_solar_receiver_any_slot_tt",
        "building_solar_receiver_slots_tt",
    ),
    "building_antimatter_engine": (
        "country_antimatter_facility_max_level_add",
        "antimatter_sub_building_slots_remaining",
        "building_antimatter_sub_any_slot_tt",
        "building_antimatter_sub_slots_tt",
    ),
    "building_antimatter_warhead_plant": (
        "country_antimatter_facility_max_level_add",
        "antimatter_sub_building_slots_remaining",
        "building_antimatter_sub_any_slot_tt",
        "building_antimatter_sub_slots_tt",
    ),
}

# The privately built ones; the warhead plant's group is government funded.
PRIVATE = ("building_solar_receiver", "building_antimatter_engine")

# consumer PM: the slot modifier it takes one of a level
CONSUMER_PMS = {
    "pm_solar_receiver": "country_solar_receiver_max_level_add",
    "pm_antimatter_engine": "country_antimatter_facility_max_level_add",
    "pm_antimatter_warhead_plant": "country_antimatter_facility_max_level_add",
}

ITERATOR_RE = re.compile(r"\b(?:any|every|ordered|random)_\w+\s*=")


def _raw(path):
    with open(os.path.join(REPO, path), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block_at(text, start):
    """The body of the brace block whose opening `{` ends at `start`."""
    depth, i = 1, start
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[start:i - 1]


def _top(text, name):
    m = re.search(rf"(?m)^(?:REPLACE_OR_CREATE:|REPLACE:|INJECT:)?{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no top-level block {name}")
    return _block_at(text, m.end())


def _child(body, key):
    """The one direct child block `key = { ... }` of `body`."""
    found = []
    depth, i = 0, 0
    pat = re.compile(rf"\b{re.escape(key)}\s*=\s*\{{")
    while i < len(body):
        c = body[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 0:
            m = pat.match(body, i)
            if m and (i == 0 or not (body[i - 1].isalnum() or body[i - 1] == "_")):
                found.append(_block_at(body, m.end()))
                i = m.end() + len(found[-1]) + 1
                continue
        i += 1
    if len(found) != 1:
        raise AssertionError(f"{key}: expected one direct block, found {len(found)}")
    return found[0]


def _has_child(body, key):
    try:
        _child(body, key)
    except AssertionError:
        return False
    return True


class GateShapeTest(unittest.TestCase):
    def setUp(self):
        self.text = _strip(_raw(BUILDINGS))

    def test_possible_reads_only_the_slot_modifier(self):
        for building, (modifier, count, _tt, _count_tt) in GATES.items():
            with self.subTest(building=building):
                possible = _child(_top(self.text, building), "possible")
                self.assertRegex(possible, rf"modifier:{modifier}\s*>\s*0")
                self.assertNotIn(count, possible, "the walk belongs in can_build_government (#1964)")
                self.assertIsNone(ITERATOR_RE.search(possible))

    def test_can_build_government_holds_the_count(self):
        for building, (_modifier, count, _tt, _count_tt) in GATES.items():
            with self.subTest(building=building):
                gate = _child(_top(self.text, building), "can_build_government")
                self.assertRegex(gate, rf"\b{count}\s*>\s*0")
                self.assertRegex(
                    gate,
                    rf"AND\s*=\s*\{{\s*b:{building}\s*\?=\s*\{{\s*is_under_construction\s*=\s*yes\s*\}}"
                    rf"\s*owner\s*=\s*\{{\s*{count}\s*>=\s*0\s*\}}\s*\}}",
                )

    def test_every_level_takes_a_slot(self):
        for building in GATES:
            with self.subTest(building=building):
                body = _top(self.text, building)
                for block in ("possible", "can_build_government"):
                    self.assertNotIn("has_building", _child(body, block),
                                     f"{block}: an existing building expands past the cap (#1965)")
                self.assertNotIn("has_max_level", body)

    def test_investors_never_build_them(self):
        for building in PRIVATE:
            with self.subTest(building=building):
                private = _child(_top(self.text, building), "can_build_private")
                self.assertRegex(private, r"^\s*always\s*=\s*no\s*$")

    def test_tooltips_have_loc(self):
        loc = _raw(LOC)
        for building, (_modifier, _count, tt, count_tt) in GATES.items():
            body = _top(self.text, building)
            for block, key in (("possible", tt), ("can_build_government", count_tt)):
                with self.subTest(building=building, block=block):
                    self.assertIn(f"text = {key}", _child(body, block))
                    self.assertRegex(loc, rf"(?m)^ {key}:0 \"")


class CountImpliesModifierTest(unittest.TestCase):
    """The count is the modifier less the queued levels, so it can't pass where
    possible's `modifier > 0` fails: possible refuses nothing the gate allows."""

    def test_count_only_subtracts_queued_levels(self):
        text = _strip(_raw(VALUES))
        for _building, (modifier, count, _tt, _count_tt) in GATES.items():
            with self.subTest(value=count):
                body = _top(text, count)
                self.assertRegex(body, rf"^\s*value\s*=\s*modifier:{modifier}\s")
                walks = re.findall(r"every_scope_state\s*=\s*\{", body)
                self.assertTrue(walks)
                rest = re.sub(rf"^\s*value\s*=\s*modifier:{modifier}\s", "", body)
                for m in re.finditer(r"every_scope_state\s*=\s*\{", rest):
                    walk = _block_at(rest, m.end())
                    target = re.search(r"exists\s*=\s*b:(\w+)", walk)
                    self.assertIsNotNone(target, walk)
                    b = target.group(1)
                    lines = sorted(re.findall(r"\b(subtract|add)\s*=\s*(\S+)", walk))
                    self.assertEqual(lines, [
                        ("add", f"b:{b}.level"),
                        ("subtract", f"b:{b}.level_after_queued_constructions"),
                    ])


class ConsumerScalingTest(unittest.TestCase):
    def test_consumers_take_a_whole_slot_a_level(self):
        text = _strip(_raw(PMS))
        for pm, modifier in CONSUMER_PMS.items():
            with self.subTest(pm=pm):
                country = _child(_top(text, pm), "country_modifiers")
                self.assertRegex(_child(country, "level_scaled"), rf"\b{modifier}\s*=\s*-1\b")
                if _has_child(country, "workforce_scaled"):
                    self.assertNotIn(modifier, _child(country, "workforce_scaled"),
                                     "an understaffed level frees its slot (#1965)")


if __name__ == "__main__":
    unittest.main()
