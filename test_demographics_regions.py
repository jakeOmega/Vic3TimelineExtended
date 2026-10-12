"""scripts/analysis/demographics_regions.py: the strategic-region snapshot the practices' start tables and the
regional report read (docs/superpowers/plans/2026-10-11-demographics-late-marriage.md, Task 1)."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_regions as R  # noqa: E402


def _land_state_regions():
    out = set()
    for path in (ROOT / "map_data" / "state_regions").glob("*.txt"):
        if path.name == "99_seas.txt":
            continue
        out |= set(re.findall(r"^(STATE_[A-Z0-9_]+)\s*=\s*\{", path.read_text(encoding="utf-8-sig"), re.M))
    return out


class TestSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = R.load_table()
        cls.of = R.strategic_region_of()

    def test_every_land_state_region_is_in_exactly_one(self):
        self.assertEqual(set(self.of), _land_state_regions())
        named = [s for states in self.table.values() for s in states]
        self.assertEqual(len(named), len(set(named)))

    def test_the_mods_replacements_are_applied(self):
        mod = R.parse(R.MOD_OVERRIDE.read_text(encoding="utf-8-sig"))
        for region, states in mod.items():
            for state in states:
                self.assertEqual(self.of[state], region, state)

    def test_parse_reads_replace_and_skips_comments(self):
        text = ("region_a = {\n\tstates = { STATE_X # STATE_COMMENTED\n STATE_Y }\n}\n"
                "REPLACE:region_b = {\n\tcapital_province = x1\n\tstates = { STATE_Z }\n}\n")
        self.assertEqual(R.parse(text), {"region_a": ["STATE_X", "STATE_Y"], "region_b": ["STATE_Z"]})

    def test_report_regions_cover_every_land_strategic_region_once(self):
        named = [r for _label, regions, _hist in R.REPORT_REGIONS for r in regions]
        self.assertEqual(len(named), len(set(named)))
        self.assertEqual(set(named), set(self.table))


if __name__ == "__main__":
    unittest.main()
