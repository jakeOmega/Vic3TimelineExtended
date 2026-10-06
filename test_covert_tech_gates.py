"""Covert operations' technology gates: which operation needs which
technology before it can be launched.

The operations that can break a great power (financial subversion,
destabilization, regime change) sit deep in the tree, so a small country
can't rush one before the great powers have had time to build services of
their own. GATES is the table; every operation type in the registry is
either gated here or named in UNGATED, so a new type has to take a side.

Each gate is a custom_tooltip, first in the action's `possible` block,
around `has_technology_researched`: launch only, like the Tradecraft
unlocks. The tooltip, the action's description and the Covert Operations
concept all name the technology.

Run: python3 -m unittest test_covert_tech_gates -v
"""

import re
import unittest
from pathlib import Path

from test_covert_op_registry import TYPES

ROOT = Path(__file__).resolve().parent
ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
TECH_DIR = ROOT / "common/technology/technologies"
LOC_DIR = ROOT / "localization/english"

# operation type -> (technology, era)
GATES = {
    "influence_campaign": ("mass_media", "era_6"),
    "comms_disruption": ("cryptography", "era_6"),
    "election_interference": ("television_broadcasting", "era_7"),
    "ideological_subversion": ("pop_culture", "era_7"),
    "regime_change": ("satellite_communications", "era_7"),
    "financial_subversion": ("computer_networks", "era_8"),
    "destabilization": ("social_media", "era_9"),
}

# No technology: the journal entry is their gate, or they have one of
# their own (a war or play with the target, a target ahead in space, a
# proliferating programme, loose warheads).
UNGATED = {
    "cultivate_assets",
    "industrial_espionage",
    "military_espionage",
    "infrastructure_sabotage",
    "space_espionage",
    "nuclear_sabotage",
    "secure_material",
}


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _action(typ):
    body = _text(ACTIONS)
    m = re.search(r"^covert_%s_action = \{\n.*?^\}" % typ, body, re.S | re.M)
    assert m, typ
    return m.group(0)


def _section(block, header):
    """The `header = { ... }` sub-block, by brace counting."""
    start = block.index(header)
    depth = 0
    for i in range(start, len(block)):
        if block[i] == "{":
            depth += 1
        elif block[i] == "}":
            depth -= 1
            if depth == 0:
                return block[start:i + 1]
    raise AssertionError("unbalanced " + header)


def _loc():
    out = {}
    for path in sorted(LOC_DIR.rglob("*.yml")):
        if path.name.startswith("te_unused"):
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"^ ([A-Za-z0-9_.]+):\d* (.*)$", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def _tech_eras():
    eras = {}
    for path in TECH_DIR.glob("era_*.txt"):
        for m in re.finditer(r"^(\w+) = \{\n(.*?)^\}", _text(path), re.S | re.M):
            era = re.search(r"\bera = (era_\d+)", m.group(2))
            if era:
                eras[m.group(1)] = era.group(1)
    return eras


class TechGateTableTest(unittest.TestCase):
    def test_every_type_takes_a_side(self):
        self.assertEqual(set(GATES) | UNGATED, set(TYPES))
        self.assertFalse(set(GATES) & UNGATED)

    def test_gate_technologies_exist_in_their_era(self):
        eras = _tech_eras()
        for typ, (tech, era) in GATES.items():
            with self.subTest(typ):
                self.assertEqual(eras.get(tech), era)


class TechGateScriptTest(unittest.TestCase):
    def test_gated_actions_check_their_technology_first(self):
        for typ, (tech, _era) in GATES.items():
            with self.subTest(typ):
                possible = _section(_action(typ), "possible = {")
                first = _section(possible[1:], "custom_tooltip = {")
                self.assertIn("text = covert_op_tech_%s_tt" % typ, first)
                self.assertIn("has_technology_researched = %s" % tech, first)

    def test_gate_is_launch_only(self):
        for typ in GATES:
            with self.subTest(typ):
                pact = _section(_action(typ), "pact = {")
                self.assertNotIn("has_technology_researched", pact)

    def test_ungated_actions_check_no_technology(self):
        for typ in UNGATED:
            with self.subTest(typ):
                self.assertNotIn("has_technology_researched", _action(typ))


class TechGateLocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = _loc()

    def test_tooltip_names_the_technology(self):
        for typ, (tech, _era) in GATES.items():
            with self.subTest(typ):
                text = self.loc.get("covert_op_tech_%s_tt" % typ)
                self.assertIsNotNone(text)
                self.assertIn("[GetTechnology('%s').GetName]" % tech, text)

    def test_description_names_the_technology(self):
        for typ, (tech, _era) in GATES.items():
            with self.subTest(typ):
                desc = self.loc["covert_%s_action_desc" % typ]
                self.assertIn("[GetTechnology('%s').GetName]" % tech, desc)

    def test_concept_lists_every_gate(self):
        concept = self.loc["concept_covert_operations_desc"]
        names = re.findall(r"\[GetTechnology\('(\w+)'\)\.GetName\]", concept)
        self.assertEqual(sorted(names), sorted(tech for tech, _era in GATES.values()))

    def test_ungated_descriptions_name_no_technology(self):
        for typ in UNGATED:
            with self.subTest(typ):
                self.assertNotIn("GetTechnology(", self.loc["covert_%s_action_desc" % typ])


if __name__ == "__main__":
    unittest.main()
