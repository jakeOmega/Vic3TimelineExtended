"""scripts/analysis/demographics_regions.py: the strategic-region snapshot the practices' start tables and the
regional report read (docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md, Task 1)."""

import re
import sys
import tempfile
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


class TestMalariaLevels(unittest.TestCase):
    """Calibration step 3 (the spec's §2.2): vanilla's malaria traits by state region, from the map files."""

    def test_the_traits_cover_africa_oceania_and_three_indonesian_regions(self):
        levels, of = R.malaria_levels(), R.strategic_region_of()
        self.assertEqual((levels["STATE_CONGO"], levels["STATE_GOLD_COAST"]), (2, 1))
        self.assertNotIn("STATE_JAVA", levels)
        africa = dict((label, regions) for label, regions, _band in R.REPORT_REGIONS)["Africa"]
        where = {of[s] for s in levels}
        self.assertLessEqual(where, set(africa) | {"region_oceania", "region_indonesia"})
        self.assertEqual(sum(1 for s in levels if of[s] == "region_indonesia"), 3)
        # Vanilla's 75 and 26, after state_trait_config.json's fixes (Local Climate, 2026-11-01): Fiji, Tonga and
        # Namaqualand lose Severe Malaria, and Zambezi and Botswana take the mild trait instead.
        self.assertEqual((len(levels), sum(1 for v in levels.values() if v == 2)), (72, 21))

    def test_a_region_with_both_traits_takes_the_severe_one(self):
        levels = {"state_trait_malaria": 1, "state_trait_severe_malaria": 2}
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "00_test.txt").write_text(
                'STATE_A = {\n\ttraits = { "state_trait_malaria" "state_trait_severe_malaria" }\n}\n'
                'STATE_B = {\n\ttraits = { "state_trait_natural_harbors" }\n}\nSTATE_C = {\n\tid = 3\n}\n',
                encoding="utf-8")
            self.assertEqual(R.malaria_levels(levels, state_regions=d), {"STATE_A": 2})


if __name__ == "__main__":
    unittest.main()
