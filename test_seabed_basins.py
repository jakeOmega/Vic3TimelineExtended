"""The seabed basins (Global Commons, spec § 2.1): every coastal state region
maps to one basin, every sea region of 99_seas.txt is in the generator's
table, and the committed effect is current.

Game-free: reads only map_data/ and the generated file.
"""
import os
import re
import sys
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import gen_seabed_basins as gen  # noqa: E402


class SeaTableTest(unittest.TestCase):
    def test_every_sea_region_has_a_basin(self):
        seas = set(gen.read_seas().values())
        self.assertEqual(len(seas), 106)
        self.assertEqual(seas - set(gen.SEA_BASIN), set(), "sea regions with no basin")
        self.assertEqual(set(gen.SEA_BASIN) - seas, set(), "table rows naming no sea region")

    def test_basins_are_the_five(self):
        self.assertEqual(set(gen.SEA_BASIN.values()), set(gen.BASINS.values()))
        self.assertEqual(gen.BASINS, {1: "pacific", 2: "atlantic", 3: "indian", 4: "arctic", 5: "southern"})

    def test_the_specs_named_seas(self):
        """§ 2.1 names these; a later edit of the table must not move them."""
        expect = {
            "atlantic": ["WESTERN_MEDITERRANEAN_SEA", "CENTRAL_MEDITERRANEAN_SEA", "EASTERN_MEDITERRANEAN_SEA",
                         "WESTERN_BLACK_SEA", "EASTERN_BLACK_SEA", "NORTHERN_BALTIC_SEA", "SOUTHERN_BALTIC_SEA",
                         "NORTH_SEA", "WESTERN_CARIBBEAN_SEA", "EASTERN_CARIBBEAN_SEA", "GULF_OF_MEXICO"],
            "indian": ["RED_SEA", "PERSIAN_GULF", "ARABIAN_SEA"],
            "pacific": ["SEA_OF_JAPAN", "EAST_CHINA_SEA", "SOUTH_CHINA_SEA"],
            "arctic": ["BARENTS_SEA", "KARA_SEA", "LAPTEV_SEA", "EAST_SIBERIAN_SEA", "CHUCKCHI_SEA",
                       "BEAUFORT_SEA", "GREENLAND_SEA", "NORWEGIAN_SEA", "NORTHWEST_PASSAGE", "BAFFIN_BAY",
                       "DAVIS_STRAIT", "HUDSON_BAY"],
            "southern": ["PATAGONIAN_SEA", "PATAGONIAN_CHANNELS", "CAPE_OF_GOOD_HOPE",
                         "GREAT_AUSTRALIAN_BIGHT", "TASMAN_SEA"],
        }
        for basin, seas in expect.items():
            for sea in seas:
                self.assertEqual(gen.SEA_BASIN["STATE_" + sea], basin, sea)


class OverrideTest(unittest.TestCase):
    """STATE_BASIN_OVERRIDE pins the few states whose sea would split a country."""

    def test_new_zealand_is_one_basin(self):
        """The North Island exits to the Tasman Sea (Southern) and the South
        Island to the Western Polynesian Sea (Pacific). New Zealand is a
        south-west Pacific country, so both are Pacific."""
        basins = gen.state_basins()
        self.assertEqual(basins["STATE_NORTH_ISLAND"], basins["STATE_SOUTH_ISLAND"])
        self.assertEqual(gen.BASINS[basins["STATE_NORTH_ISLAND"]], "pacific")

    def test_the_australian_tasman_coast_stays_southern(self):
        """The spec's Tasman Sea is south-east Australia; the pin moves only
        the North Island, not the sea."""
        basins = gen.state_basins()
        for state in ("STATE_NEW_SOUTH_WALES", "STATE_VICTORIA", "STATE_TASMANIA"):
            self.assertEqual(gen.BASINS[basins[state]], "southern", state)

    def test_every_override_changes_its_state(self):
        """state_basins raises on a pin that is redundant; this names the rule."""
        seas = gen.read_seas()
        exits = gen.read_naval_exits()
        for state, basin in gen.STATE_BASIN_OVERRIDE.items():
            sea = seas[exits[state][0]]
            self.assertNotEqual(gen.SEA_BASIN[sea], basin, f"{state} is already {basin} by {sea}")

    def test_a_bad_override_raises(self):
        for bad, why in (({"STATE_NO_SUCH_PLACE": "pacific"}, "not a coastal"),
                         ({"STATE_NORTH_ISLAND": "lunar"}, "unknown basin"),
                         ({"STATE_SOUTH_ISLAND": "pacific"}, "already pacific")):
            with mock.patch.object(gen, "STATE_BASIN_OVERRIDE", bad):
                with self.assertRaisesRegex(ValueError, why):
                    gen.state_basins()


class CoastalStatesTest(unittest.TestCase):
    def test_every_coastal_state_maps_to_a_basin(self):
        exits = gen.read_naval_exits()
        coastal = {s for s, ids in exits.items() if ids}
        basins = gen.state_basins()   # raises on an unmapped sea or a double exit
        self.assertEqual(set(basins), coastal)
        self.assertEqual(len(coastal), 371)   # 1.15 merged coastal Chukotka into Kamchatka
        for state, n in basins.items():
            self.assertIn(n, gen.BASINS, state)

    def test_every_basin_has_coastal_states(self):
        basins = gen.state_basins()
        for n in gen.BASINS:
            self.assertGreater(sum(1 for b in basins.values() if b == n), 0, gen.BASINS[n])

    def test_the_land_files_are_the_whole_map(self):
        """The mod ships all sixteen land files and the seas (resources.py
        rewrites every vanilla state_regions file), so no vanilla state region
        is outside the generator's reach."""
        files = sorted(os.listdir(os.path.join(REPO, "map_data", "state_regions")))
        self.assertEqual(len([f for f in files if f.endswith(".txt")]), 17)
        self.assertIn("99_seas.txt", files)


class GeneratedFileTest(unittest.TestCase):
    def test_the_committed_file_is_current(self):
        result = gen.regenerate(dry_run=True)
        self.assertFalse(result["changed"], "run python3 scripts/generators/gen_seabed_basins.py")

    def test_the_file_has_one_bom_and_sets_each_coastal_state_once(self):
        with open(os.path.join(REPO, gen.OUT), "rb") as f:
            raw = f.read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))
        text = raw.decode("utf-8-sig")
        named = re.findall(r"state_region = s:(STATE_\w+)", text)
        self.assertEqual(len(named), len(set(named)))
        self.assertEqual(set(named), set(gen.state_basins()))
        self.assertEqual(re.findall(r"value = (\d)", text), ["1", "2", "3", "4", "5"])


if __name__ == "__main__":
    unittest.main()
