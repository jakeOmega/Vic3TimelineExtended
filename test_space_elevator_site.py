"""The Space Elevator's construction site keeps its hand-kept list of state regions.

#1672 replaced the list in `building_space_elevator_construction_site`'s `possible`
with `in_tropics = yes`; the engine's band roughly doubled the eligible states
(about 183 against 92), and the owner restored the list (2026-11-12). These tests
pin the list: no latitude trigger stands in for it, it names 92 distinct state
regions, and each one exists on the map, so a renamed region can't silently drop
a site (`state_region = s:X` on an unknown X matches nothing).

Run: python3 -m pytest test_space_elevator_site.py -q
"""

import re
import unittest
from pathlib import Path

from test_nuclear_deterrence import block, read, strip_comments

ROOT = Path(__file__).resolve().parent
BUILDINGS = ROOT / "common/buildings/extra_buildings.txt"
STATE_REGIONS = ROOT / "map_data/state_regions"


def site_possible():
    text = strip_comments(read(BUILDINGS))
    return block(block(text, "REPLACE_OR_CREATE:building_space_elevator_construction_site"), "possible")


def map_state_regions():
    out = set()
    for p in STATE_REGIONS.glob("*.txt"):
        out |= set(re.findall(r"(?m)^(STATE_[A-Z0-9_]+)\s*=\s*\{", p.read_text(encoding="utf-8-sig")))
    return out


class SpaceElevatorSiteTest(unittest.TestCase):
    def setUp(self):
        self.possible = site_possible()
        self.listed = re.findall(r"state_region\s*=\s*s:(STATE_[A-Z0-9_]+)", self.possible)

    def test_no_latitude_trigger(self):
        for trigger in ("in_tropics", "in_north_hemisphere", "in_south_hemisphere"):
            self.assertNotIn(trigger, self.possible, trigger)

    def test_list_of_92_distinct_regions(self):
        self.assertEqual(len(self.listed), 92)
        self.assertEqual(len(set(self.listed)), 92)

    def test_every_listed_region_is_on_the_map(self):
        missing = sorted(set(self.listed) - map_state_regions())
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
