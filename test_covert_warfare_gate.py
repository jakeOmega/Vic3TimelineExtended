"""The Covert Warfare entry opens on a named slot source, and the list stays whole.

The late gate, `covert_warfare_slot_source` (the entry's `possible` under the late unlock, and where the
early unlock's budget cap lifts), names every source of an operation slot
(`country_covert_operation_slot_add`) beyond the base slot every country holds
(`base_values`) and its rank's bonus (`common/country_ranks`): a technology by
`has_technology_researched`, a law by `has_law`, an institution by the law that
establishes it. Until 2026-11-08 it counted slots against the rank's instead,
and Two Sicilies opened the entry in 1836 (Workshop report).

This fails when a slot source is added that the gate doesn't name, when the gate
names something that grants no slot, and on a source of a kind it can't map to
a trigger: then add the kind to `source_tests` and its trigger to the gate, and name it in
the unlock tooltips (`covert_warfare_unlock_tt` and `_early_tt`, which
test_covert_layout.py holds to the names).

Run: python3 -m unittest test_covert_warfare_gate -v
"""

import json
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
VANILLA_LAWS = ROOT / "vanilla_parsed/common/laws.json"
MODIFIER = "country_covert_operation_slot_add"
# The definition of the modifier type, not a source.
SKIP_DIRS = {"modifier_type_definitions"}
DIRECTIVES = ("INJECT:", "REPLACE:", "TRY_REPLACE:", "REPLACE_OR_CREATE:", "INJECT_OR_CREATE:", "TRY_INJECT:")


def parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(path), apply_directives=False)
    return parser.data


def bare(name):
    for prefix in DIRECTIVES:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def pairs(value):
    return value if isinstance(value, list) else [value]


def grants(value):
    """True when a block holds the modifier at a positive value, at any depth."""
    if isinstance(value, tuple):
        return grants(value[1])
    if isinstance(value, list):
        return any(grants(v) for v in value)
    if not isinstance(value, dict):
        return False
    for key, inner in value.items():
        if key == MODIFIER:
            for _, number in pairs(inner):
                try:
                    if float(number) > 0:
                        return True
                except (TypeError, ValueError):
                    raise AssertionError(f"{MODIFIER} = {number!r} is not a literal; teach this test to read it")
        elif grants(inner):
            return True
    return False


def slot_sources():
    """(directory under common/, entity name) for every mod definition that grants a slot."""
    found = set()
    for path in sorted((ROOT / "common").rglob("*.txt")):
        kind = path.relative_to(ROOT / "common").parts[0]
        if kind in SKIP_DIRS or MODIFIER not in path.read_text(encoding="utf-8-sig"):
            continue
        for name, value in parse(path).items():
            if grants(value):
                found.add((kind, bare(name)))
    return found


def laws_establishing(institution):
    laws = set()
    for name, value in json.loads(VANILLA_LAWS.read_text(encoding="utf-8")).items():
        if value[1].get("institution", [None, None])[1] == institution:
            laws.add(name)
    for path in sorted((ROOT / "common/laws").glob("*.txt")):
        for name, value in parse(path).items():
            body = value[1] if isinstance(value, tuple) else None
            if isinstance(body, dict) and "institution" in body and body["institution"][1] == institution:
                laws.add(bare(name))
    return laws


def source_tests(sources):
    """The triggers the gate must hold, and the baseline sources it leaves out."""
    tests, baseline, unknown = set(), set(), []
    for kind, name in sources:
        if (kind, name) == ("static_modifiers", "base_values") or kind == "country_ranks":
            baseline.add((kind, name))
        elif kind == "technology":
            tests.add(("has_technology_researched", name))
        elif kind == "laws":
            tests.add(("has_law", "law_type:" + name))
        elif kind == "institutions":
            laws = laws_establishing(name)
            if not laws:
                unknown.append((kind, name, "no law establishes it"))
            tests.update(("has_law", "law_type:" + law) for law in laws)
        else:
            unknown.append((kind, name, "no trigger for this kind of source"))
    return tests, baseline, unknown


def gate_tests():
    """The late gate, covert_warfare_slot_source, which the entry's `possible` reaches through
    covert_warfare_entry_unlocked under either unlock (test_covert_layout.py and test_rule_unlock_settings.py
    hold that wiring)."""
    gate = parse(TRIGGERS)["covert_warfare_slot_source"][1]
    assert list(gate) == ["OR"], f"covert_warfare_slot_source should be one OR of the sources, not {list(gate)}"
    return {(key, value) for key, inner in gate["OR"][1].items() for _, value in pairs(inner)}


class CovertGateTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tests, cls.baseline, cls.unknown = source_tests(slot_sources())

    def test_the_scan_finds_the_baseline(self):
        # Without these the scan read nothing, and the rest would pass on empty sets.
        self.assertEqual(self.baseline, {("static_modifiers", "base_values"), ("country_ranks", "great_power"),
                                         ("country_ranks", "major_power")})

    def test_every_source_is_of_a_known_kind(self):
        self.assertEqual(self.unknown, [], "a slot source this test can't map to a trigger: add the kind to "
                                           "source_tests, and the trigger to covert_warfare_slot_source")

    def test_the_gate_names_every_source_and_nothing_else(self):
        gate = gate_tests()
        self.assertEqual(sorted(self.tests - gate), [],
                         "these grant an operation slot but don't open the entry: add them to "
                         "covert_warfare_slot_source and the two unlock tooltips")
        self.assertEqual(sorted(gate - self.tests), [],
                         "the entry opens on these, but they grant no operation slot: take them out")


if __name__ == "__main__":
    unittest.main()
