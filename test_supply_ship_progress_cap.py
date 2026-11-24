"""With Naval Convoy Defense a supply ship's weekly cap is its cost: one week (#1984).

Vanilla's `ship_type_supply_ship` costs 25 points (`base_construction_cost`)
and its own modifier caps the progress a ship takes in a week at 5
(`ship_construction_progress_max_add`). So a ship took five weeks and five
times as many were in progress as the week's points could finish. The time
controls' ship construction readout was half of the 2030 United States' week
(docs/audits/late_game_performance.md), and its cost is thought to follow that
queue. The era 6 technology `naval_convoy_defense` adds the difference,
`country_supply_ship_construction_progress_max_add`, so a country that has it
builds a ship in a week. It sits on a late technology so the early game keeps
vanilla's pace (owner, 2026-11-24). The add alone reaches the cost, without the
technology's own +25%, in case that multiplies only the add.

This fails when vanilla changes the type's cost or cap: re-derive the add in
`common/technology/technologies/era_6.txt`. It also fails when the mod
redefines the type, which the full rescale
(docs/superpowers/plans/2026-11-24-supply-ship-scale.md) would do: then hold
the add to the mod's own cost and cap instead.

Run: .venv/bin/python -m pytest test_supply_ship_progress_cap.py -q
"""

import json
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
VANILLA_SHIP_TYPES = ROOT / "vanilla_parsed/common/ship_types.json"
MOD_SHIP_TYPES = ROOT / "common/ship_types"
TECH_FILE = ROOT / "common/technology/technologies/era_6.txt"
TECH = "naval_convoy_defense"
SUPPLY_SHIP = "ship_type_supply_ship"
CAP_ADD = "country_supply_ship_construction_progress_max_add"


def value(entry):
    """The value of a parsed `key = value` (vanilla_parsed's ["=", v], the parser's ("=", v))."""
    if isinstance(entry, (list, tuple)) and len(entry) == 2 and entry[0] == "=":
        return entry[1]
    return entry


def parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(path), apply_directives=False)
    return parser.data


class SupplyShipProgressCapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        vanilla = json.loads(VANILLA_SHIP_TYPES.read_text(encoding="utf-8"))
        cls.vanilla_type = value(vanilla[SUPPLY_SHIP])

    def test_vanilla_type_is_what_the_add_was_derived_from(self):
        cost = float(value(self.vanilla_type["base_construction_cost"]))
        cap = float(value(value(self.vanilla_type["modifier"])["ship_construction_progress_max_add"]))
        self.assertEqual((cost, cap), (25.0, 5.0), f"vanilla's supply ship changed: re-derive the add on {TECH}")

    def test_technology_adds_cost_less_cap(self):
        modifier = value(value(parse(TECH_FILE)[TECH])["modifier"])
        add = float(value(modifier[CAP_ADD]))
        cost = float(value(self.vanilla_type["base_construction_cost"]))
        cap = float(value(value(self.vanilla_type["modifier"])["ship_construction_progress_max_add"]))
        self.assertEqual(cap + add, cost)

    def test_no_other_source_of_the_add(self):
        """One source, so the early game keeps vanilla's five weeks."""
        sources = []
        for path in sorted((ROOT / "common").rglob("*.txt")):
            if "modifier_type_definitions" in path.parts:
                continue
            if CAP_ADD in path.read_text(encoding="utf-8-sig"):
                sources.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(sources, [TECH_FILE.relative_to(ROOT).as_posix()])

    def test_mod_does_not_redefine_the_type(self):
        for path in sorted(MOD_SHIP_TYPES.glob("*.txt")):
            for key in parse(path):
                self.assertNotEqual(key.split(":")[-1], SUPPLY_SHIP, f"{path.name} redefines {key}")


if __name__ == "__main__":
    unittest.main()
