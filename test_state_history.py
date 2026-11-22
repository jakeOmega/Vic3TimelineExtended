"""state_history: who owns each state at game start (#901), without a game.

The reader runs on text here; the facts about vanilla's real start map are
checked against the committed `vanilla_parsed/history/states.json`.
"""
import json
import os
import tempfile
import unittest

import state_history as sh
import vanilla_parsed

HISTORY = """
# a comment
STATES = {
	s:STATE_SPLIT = {
		create_state = {
			country = c:AAA
			owned_provinces = { x0000A1 "x0000a2" }
		}
		create_state = {
			country = "c:BBB"
			owned_provinces = { x0000B1 }
			state_type = unincorporated
		}
		add_homeland = cu:alpha
		add_homeland = cu:beta
		add_claim = c:CCC
		set_variable = { name = x value = 1 }
	}
	"s:STATE_WHOLE" = {
		create_state = {
			country = c:AAA
			owned_provinces = { x0000C1 x0000C2 x0000C3 }
		}
		add_homeland = cu:alpha
	}
}
"""
REGIONS = """
STATE_SPLIT = {
	id = 1
	provinces = { "x0000A1" "x0000A2" "x0000B1" "x0000D1" }
	city = "x0000B1"
	farm = "x0000a1"
	mine = "x0000D1"
}
STATE_WHOLE = {
	id = 2
	provinces = { "x0000C1" "x0000C2" "x0000C3" }
	city = "x0000C2"
	port = "x0000C3"
}
"""


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(text)


class ParseTests(unittest.TestCase):
    def test_every_part_of_a_split_state_survives(self):
        states = sh.parse_text(HISTORY)
        split = states["STATE_SPLIT"]
        self.assertEqual([p["country"] for p in split["parts"]], ["AAA", "BBB"])
        # One spelling for province ids, whatever the file's case and quoting.
        self.assertEqual(split["parts"][0]["provinces"], ["x0000A1", "x0000A2"])
        self.assertEqual(split["parts"][1]["state_types"], ["unincorporated"])
        self.assertNotIn("state_types", split["parts"][0])
        self.assertEqual(split["homelands"], ["alpha", "beta"])
        self.assertEqual(split["claims"], ["CCC"])

    def test_quoted_state_key_and_single_part(self):
        whole = sh.parse_text(HISTORY)["STATE_WHOLE"]
        self.assertEqual(len(whole["parts"]), 1)
        self.assertEqual(whole["parts"][0]["country"], "AAA")

    def test_a_second_states_block_and_a_repeated_state_both_count(self):
        # The parser's own top-level merge would keep one STATES block.
        text = HISTORY + """
STATES = {
	s:STATE_SPLIT = { create_state = { country = c:DDD owned_provinces = { x0000D1 } } add_homeland = cu:alpha }
	s:STATE_LATE = { create_state = { country = c:DDD owned_provinces = { x0000E1 } } }
}
"""
        states = sh.parse_text(text)
        self.assertEqual([p["country"] for p in states["STATE_SPLIT"]["parts"]], ["AAA", "BBB", "DDD"])
        self.assertEqual(states["STATE_SPLIT"]["homelands"], ["alpha", "beta"])
        self.assertIn("STATE_LATE", states)
        self.assertIn("STATE_WHOLE", states)

    def test_state_with_no_owner_keeps_its_homelands(self):
        states = sh.parse_text("STATES = { s:STATE_EMPTY = { add_homeland = cu:alpha } }")
        self.assertEqual(states["STATE_EMPTY"], {"parts": [], "homelands": ["alpha"], "claims": []})

    def test_other_top_level_blocks_are_ignored(self):
        self.assertEqual(sh.parse_text("COUNTRIES = { c:AAA = { set_tax_level = high } }"), {})


class DirectoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.vanilla = os.path.join(self.tmp.name, "game")
        self.mod = os.path.join(self.tmp.name, "mod")
        _write(os.path.join(self.vanilla, sh.REL_DIR, "00_states.txt"), HISTORY)
        _write(os.path.join(self.vanilla, sh.STATE_REGIONS_REL_DIR, "00_regions.txt"), REGIONS)

    def test_parse_dir_keeps_the_file_and_merge_flattens_it(self):
        by_file = sh.parse_dir(os.path.join(self.vanilla, sh.REL_DIR))
        self.assertEqual(list(by_file), ["00_states.txt"])
        self.assertEqual(sh.merge(by_file), by_file["00_states.txt"])
        # Plain JSON: what the snapshot stores is what the reader returned.
        self.assertEqual(json.loads(json.dumps(by_file)), by_file)

    def test_missing_directory_is_an_empty_table(self):
        self.assertEqual(sh.parse_dir(os.path.join(self.mod, sh.REL_DIR)), {})

    def test_mod_file_of_the_same_name_replaces_vanillas(self):
        _write(os.path.join(self.mod, sh.REL_DIR, "00_states.txt"),
               "STATES = { s:STATE_WHOLE = { create_state = { country = c:ZZZ owned_provinces = { x0000C1 } } } }")
        states = sh.merge(sh.parse_dir(os.path.join(self.vanilla, sh.REL_DIR)),
                          sh.parse_dir(os.path.join(self.mod, sh.REL_DIR)))
        self.assertEqual(list(states), ["STATE_WHOLE"])
        self.assertEqual(states["STATE_WHOLE"]["parts"][0]["country"], "ZZZ")

    def test_mod_file_of_another_name_adds_to_vanillas(self):
        _write(os.path.join(self.mod, sh.REL_DIR, "zz_extra.txt"),
               "STATES = { s:STATE_WHOLE = { add_claim = c:QQQ } }")
        vanilla = sh.parse_dir(os.path.join(self.vanilla, sh.REL_DIR))
        states = sh.merge(vanilla, sh.parse_dir(os.path.join(self.mod, sh.REL_DIR)))
        self.assertEqual(states["STATE_WHOLE"]["claims"], ["QQQ"])
        self.assertEqual(len(states["STATE_SPLIT"]["parts"]), 2)
        # merge copies: the vanilla table is not written through.
        self.assertEqual(vanilla["00_states.txt"]["STATE_WHOLE"]["claims"], [])

    def test_hubs_say_which_part_holds_the_city(self):
        states = sh.merge(sh.parse_dir(os.path.join(self.vanilla, sh.REL_DIR)))
        regions = sh.state_regions(os.path.join(self.vanilla, sh.STATE_REGIONS_REL_DIR))
        out = sh.describe("STATE_SPLIT", states["STATE_SPLIT"], regions)
        self.assertTrue(out["split"])
        parts = {p["country"]: p for p in out["parts"]}
        self.assertEqual(parts["AAA"]["hubs"], ["farm"])   # lower-case id in the map file
        self.assertEqual(parts["BBB"]["hubs"], ["city"])
        self.assertEqual(parts["AAA"]["provinces"], 2)
        self.assertEqual(out["unowned_hubs"], ["mine"])
        self.assertEqual(out["unowned_provinces"], 1)
        self.assertNotIn("province_ids", parts["AAA"])
        with_ids = sh.describe("STATE_SPLIT", states["STATE_SPLIT"], regions, provinces=True)
        self.assertEqual(with_ids["parts"][1]["province_ids"], ["x0000B1"])

    def test_a_province_listed_by_two_parts_is_reported(self):
        text = ("STATES = { s:STATE_SPLIT = {"
                " create_state = { country = c:AAA owned_provinces = { x0000A1 x0000B1 } }"
                " create_state = { country = c:BBB owned_provinces = { x0000B1 } } } }")
        regions = sh.state_regions(os.path.join(self.vanilla, sh.STATE_REGIONS_REL_DIR))
        out = sh.describe("STATE_SPLIT", sh.parse_text(text)["STATE_SPLIT"], regions)
        self.assertEqual(out["double_listed_provinces"], 1)
        self.assertEqual([p["hubs"] for p in out["parts"]], [["city", "farm"], ["city"]])
        clean = sh.describe("STATE_WHOLE", sh.parse_text(HISTORY)["STATE_WHOLE"], regions)
        self.assertNotIn("double_listed_provinces", clean)

    def test_a_later_state_regions_directory_replaces_a_same_named_file(self):
        _write(os.path.join(self.mod, sh.STATE_REGIONS_REL_DIR, "00_regions.txt"),
               REGIONS.replace('city = "x0000B1"', 'city = "x0000A2"'))
        regions = sh.state_regions(os.path.join(self.vanilla, sh.STATE_REGIONS_REL_DIR),
                                   os.path.join(self.mod, sh.STATE_REGIONS_REL_DIR))
        self.assertEqual(regions["STATE_SPLIT"]["hubs"]["city"], "x0000A2")

    def test_owned_by_lists_a_tags_parts(self):
        states = sh.merge(sh.parse_dir(os.path.join(self.vanilla, sh.REL_DIR)))
        regions = sh.state_regions(os.path.join(self.vanilla, sh.STATE_REGIONS_REL_DIR))
        rows = sh.owned_by(states, "AAA", regions)
        self.assertEqual([r["state"] for r in rows], ["STATE_SPLIT", "STATE_WHOLE"])
        self.assertEqual(rows[0]["other_owners"], ["BBB"])
        self.assertEqual(rows[1]["hubs"], ["city", "port"])
        self.assertEqual(sh.owned_by(states, "NOPE", regions), [])
        self.assertEqual(sh.summary(states), {
            "states": 2, "parts": 3, "split_states": 1, "unowned_states": 0, "countries": 2})

    def test_load_prefers_game_files_and_falls_back_to_the_snapshot(self):
        states, regions, source = sh.load(self.tmp.name, None)
        self.assertEqual((source, sorted(states)), ("game_files", ["STATE_SPLIT", "STATE_WHOLE"]))
        self.assertIn("STATE_SPLIT", regions)
        snap = os.path.join(self.tmp.name, "snap")
        _write(os.path.join(self.tmp.name, "launcher/launcher-settings.json"),
               json.dumps({"rawVersion": "1.0.0"}))
        _write(os.path.join(self.vanilla, "common/laws/00.txt"), "law_x = { }\n")
        vanilla_parsed.build(self.tmp.name, snap)
        states2, _regions, source2 = sh.load(None, None, snapshot_dir=snap)
        self.assertEqual((source2, states2), ("vanilla_parsed", states))
        with self.assertRaises(FileNotFoundError):
            sh.load(None, None, snapshot_dir=os.path.join(self.tmp.name, "nowhere"))


class CommittedSnapshotTests(unittest.TestCase):
    """Vanilla's start map as the repo carries it. A vanilla patch that moves
    one of these borders fails here, which is the prompt to re-read whatever
    was placed by them (Grand Monuments' 1836 seeds, #901)."""

    @classmethod
    def setUpClass(cls):
        by_file = vanilla_parsed.load_state_history()
        if by_file is None:
            raise unittest.SkipTest("vanilla_parsed/ has no state history")
        cls.states = sh.merge(by_file)
        cls.regions = sh.state_regions(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    *sh.STATE_REGIONS_REL_DIR.split("/")))

    def _owners(self, state):
        return [p["country"] for p in self.states[state]["parts"]]

    def _hub_owner(self, state, hub):
        out = sh.describe(state, self.states[state], self.regions)
        return next((p["country"] for p in out["parts"] if hub in p["hubs"]), None)

    def test_every_part_has_an_owner_and_land(self):
        self.assertGreater(len(self.states), 600)
        for state, rec in self.states.items():
            # Not asserted: that no province is listed by two parts. Vanilla's
            # own file gives three Alaskan provinces to two countries.
            for part in rec["parts"]:
                self.assertRegex(part["country"] or "", r"^[A-Z0-9]{3}$", state)
                self.assertTrue(part["provinces"], state)

    def test_owned_provinces_belong_to_their_state_region(self):
        # The hub lookup rests on both files naming provinces the same way.
        for state in ("STATE_LOMBARDY", "STATE_RAJPUTANA", "STATE_PUNJAB", "STATE_GONDER"):
            region = set(self.regions[state]["provinces"])
            owned = {p for part in self.states[state]["parts"] for p in part["provinces"]}
            self.assertTrue(owned and owned <= region, state)

    def test_the_issues_open_questions(self):
        # Lombardy is Austria's; Lahore (Punjab's city) is Punjab's; Tigray
        # holds part of Gonder; Rajputana's parts include Jaipur.
        self.assertEqual(self._owners("STATE_LOMBARDY"), ["AUS"])
        self.assertEqual(self._hub_owner("STATE_PUNJAB", "city"), "PAN")
        self.assertIn("TGR", self._owners("STATE_GONDER"))
        self.assertIn("JAI", self._owners("STATE_RAJPUTANA"))
        self.assertGreater(len(self._owners("STATE_RAJPUTANA")), 5)

    def test_manifest_counts_match_the_stored_table(self):
        info = vanilla_parsed.read_manifest(vanilla_parsed.DEFAULT_DIR)["state_history"]
        counts = sh.summary(self.states)
        self.assertEqual({k: info[k] for k in counts}, counts)


if __name__ == "__main__":
    unittest.main()
