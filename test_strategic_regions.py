"""strategic_regions: state region <-> strategic region (#917), without a game."""
import json
import os
import unittest

import strategic_regions as sr
import vanilla_parsed
from mod_state import VANILLA_COMMON_DIRS, ModState

ROOT = os.path.dirname(os.path.abspath(__file__))


class LookupTests(unittest.TestCase):
    DATA = {
        "region_a": ("=", {"graphical_culture": ("=", '"x"'),
                           "states": ("=", ["STATE_ONE", '"STATE_TWO"'])}),
        "region_b": ("=", {"states": ("=", ["STATE_THREE"])}),
        "region_sea": ("=", {"states": ("=", [])}),
        "not_a_region": ("=", "junk"),
    }

    def test_region_states_and_inverse(self):
        self.assertEqual(sr.region_states(self.DATA), {
            "region_a": ["STATE_ONE", "STATE_TWO"], "region_b": ["STATE_THREE"], "region_sea": []})
        self.assertEqual(sr.region_of(self.DATA)["STATE_TWO"], "region_a")
        self.assertEqual(sr.duplicates(self.DATA), {})
        self.assertEqual(sr.region_states(None), {})

    def test_a_state_in_two_regions_is_reported(self):
        data = dict(self.DATA, region_c=("=", {"states": ("=", ["STATE_ONE"])}))
        self.assertEqual(sr.duplicates(data), {"STATE_ONE": ["region_a", "region_c"]})
        self.assertEqual(sr.region_of(data)["STATE_ONE"], "region_c")


class CommittedDataTests(unittest.TestCase):
    """The snapshot plus the mod's REPLACEs, against the table the
    demographics harness commits (built from the game's raw files)."""

    @classmethod
    def setUpClass(cls):
        vanilla = vanilla_parsed.parsed_entities(["Strategic Regions"])
        rel = VANILLA_COMMON_DIRS["Strategic Regions"]
        ms = ModState({"Strategic Regions": ""},
                      {"Strategic Regions": os.path.join(ROOT, "common", rel)},
                      vanilla_data=vanilla)
        cls.data = ms.get_data("Strategic Regions")

    def test_matches_the_demographics_table(self):
        path = os.path.join(ROOT, "scripts", "analysis", "demographics_strategic_regions.json")
        with open(path, encoding="utf-8") as f:
            want = json.load(f)
        table = sr.region_states(self.data)
        self.assertEqual({r: sorted(table[r]) for r in want}, want)

    def test_no_state_region_sits_in_two_strategic_regions(self):
        self.assertEqual(sr.duplicates(self.data), {})
        self.assertEqual(sr.region_of(self.data)["STATE_SVEALAND"], "region_northern_europe")


if __name__ == "__main__":
    unittest.main()
