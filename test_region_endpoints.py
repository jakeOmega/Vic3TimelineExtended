"""/strategic-regions, /state-region, /state-history and /prestige-goods
(#917, #901, #749), without a game install."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mod_state_server as mss
import vanilla_parsed
from mod_state import ModState

REGIONS = """
region_north = { states = { STATE_SPLIT STATE_WHOLE } }
region_south = { states = { STATE_FAR } }
"""
MOD_REGIONS = "REPLACE:region_south = { states = { STATE_FAR STATE_NEW } }\n"
HISTORY = """
STATES = {
	s:STATE_SPLIT = {
		create_state = { country = c:AAA owned_provinces = { x0000A1 x0000A2 } }
		create_state = { country = c:BBB owned_provinces = { x0000B1 } state_type = unincorporated }
		add_homeland = cu:alpha
		add_claim = c:CCC
	}
	s:STATE_WHOLE = { create_state = { country = c:AAA owned_provinces = { x0000C1 } } }
}
"""
STATE_REGIONS = """
STATE_SPLIT = { provinces = { "x0000A1" "x0000A2" "x0000B1" } city = "x0000B1" farm = "x0000A1" }
STATE_WHOLE = { provinces = { "x0000C1" "x0000C9" } city = "x0000C1" mine = "x0000C9" }
"""
PRESTIGE = """
prestige_good_v1 = { base_good = steel prestige_bonus = 0.1 }
prestige_good_v2 = { base_good = steel prestige_bonus = 0.1 }
"""
MOD_PRESTIGE = "prestige_good_m1 = { base_good = steel prestige_bonus = 0.2 }\n"
COMPANIES = "company_a = { possible_prestige_goods = { prestige_good_v1 prestige_good_m1 } }\n"
GOODS = "steel = { cost = 50 }\ntools = { cost = 40 }\n"


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class RegionEndpointTests(unittest.TestCase):
    TYPES = {
        "Strategic Regions": "strategic_regions", "Prestige Goods": "prestige_goods",
        "Company Types": "company_types", "Goods": "goods",
    }

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base, self.mod = self.root / "install", self.root / "mod"
        game = self.base / "game"
        _write(game / "common/strategic_regions/00.txt", REGIONS)
        _write(self.mod / "common/strategic_regions/zz.txt", MOD_REGIONS)
        _write(game / "common/history/states/00_states.txt", HISTORY)
        _write(self.mod / "map_data/state_regions/00.txt", STATE_REGIONS)
        _write(game / "common/prestige_goods/00.txt", PRESTIGE)
        _write(self.mod / "common/prestige_goods/extra.txt", MOD_PRESTIGE)
        _write(self.mod / "common/company_types/c.txt", COMPANIES)
        _write(game / "common/goods/00.txt", GOODS)
        # ModState skips a type whose vanilla folder is missing, mod side included.
        (game / "common/company_types").mkdir()
        # A populated game/common, so the server counts the tree as present.
        for i in range(12):
            (game / "common" / f"pad_{i}").mkdir()
        self.base_dirs = {et: str(game / "common" / rel) for et, rel in self.TYPES.items()}
        self.mod_dirs = {et: str(self.mod / "common" / rel) for et, rel in self.TYPES.items()}
        self.state = ModState(self.base_dirs, self.mod_dirs)
        self.state.localization = {"AAA": "Alphaland", "region_north": "The North", "STATE_SPLIT": "Split"}
        self.patch(ms=self.state, mod_path=str(self.mod), base_game_path=str(self.base),
                   mod_paths=self.mod_dirs, base_game_paths=self.base_dirs,
                   _vanilla_source={"kind": "game_files"}, _state_history_cache=None)
        self.handler = object.__new__(mss.ModStateHandler)

    def patch(self, **values):
        for name, value in values.items():
            p = mock.patch.object(mss, name, value)
            p.start()
            self.addCleanup(p.stop)

    def request(self, path):
        self.handler.path = path
        self.handler._local_request_ok = mock.Mock(return_value=True)
        self.handler._respond_json = mock.Mock()
        self.handler.do_GET()
        args = self.handler._respond_json.call_args.args
        json.dumps(args[0])
        return (args[1] if len(args) > 1 else 200), args[0]

    # ---- strategic regions -------------------------------------------------

    def test_strategic_region_lists_its_states_with_the_mods_replace(self):
        status, body = self.request("/strategic-regions/region_south")
        self.assertEqual((status, body["states"]), (200, ["STATE_FAR", "STATE_NEW"]))
        status, body = self.request("/strategic-regions")
        self.assertEqual({r["name"]: r["states"] for r in body}, {"region_north": 2, "region_south": 2})
        self.assertEqual(body[0]["localized"], "The North")

    def test_state_region_names_its_strategic_region(self):
        status, body = self.request("/state-region/STATE_NEW")
        self.assertEqual((status, body["strategic_region"]), (200, "region_south"))
        status, body = self.request("/state-region/STATE_SPLT")
        self.assertEqual(status, 404)
        self.assertIn("STATE_SPLIT", body["did_you_mean"])
        self.assertEqual(self.request("/state-region")[0], 400)
        self.assertEqual(self.request("/strategic-regions/region_nope")[0], 404)

    # ---- state history -----------------------------------------------------

    def test_split_state_names_each_part_and_its_hubs(self):
        status, body = self.request("/state-history/STATE_SPLIT")
        self.assertEqual(status, 200)
        self.assertTrue(body["split"])
        parts = {p["country"]: p for p in body["parts"]}
        self.assertEqual(parts["AAA"]["hubs"], ["farm"])
        self.assertEqual(parts["BBB"]["hubs"], ["city"])
        self.assertEqual(parts["AAA"]["country_name"], "Alphaland")
        self.assertEqual(parts["BBB"]["state_types"], ["unincorporated"])
        self.assertEqual((body["homelands"], body["claims"]), (["alpha"], ["CCC"]))
        self.assertEqual((body["strategic_region"], body["vanilla_source"]), ("region_north", "game_files"))
        self.assertNotIn("province_ids", parts["AAA"])
        _status, body = self.request("/state-history/STATE_SPLIT?provinces=true")
        self.assertEqual(body["parts"][0]["province_ids"], ["x0000A1", "x0000A2"])

    def test_unowned_land_and_hubs_are_counted(self):
        _status, body = self.request("/state-history/STATE_WHOLE")
        self.assertEqual((body["unowned_provinces"], body["unowned_hubs"]), (1, ["mine"]))

    def test_country_query_lists_what_a_tag_starts_with(self):
        status, body = self.request("/state-history?country=AAA")
        self.assertEqual(status, 200)
        self.assertEqual([r["state"] for r in body["states"]], ["STATE_SPLIT", "STATE_WHOLE"])
        self.assertEqual(body["states"][0]["other_owners"], ["BBB"])
        self.assertEqual(body["states"][0]["strategic_region"], "region_north")
        self.assertEqual(self.request("/state-history?country=ZZZ")[0], 404)
        self.assertEqual(self.request("/state-history/STATE_NOPE")[0], 404)

    def test_bare_request_is_a_summary(self):
        _status, body = self.request("/state-history")
        self.assertEqual((body["states"], body["parts"], body["split_states"]), (2, 3, 1))
        self.assertEqual(body["owners"]["STATE_SPLIT"], ["AAA", "BBB"])

    def test_snapshot_serves_the_history_without_game_files(self):
        _write(self.base / "launcher/launcher-settings.json", json.dumps({"rawVersion": "1.0.0"}))
        snap = str(self.root / "snap")
        vanilla_parsed.build(str(self.base), snap)
        self.patch(_vanilla_source={"kind": "vanilla_parsed"}, VANILLA_PARSED_DIR=snap,
                   base_game_path=str(self.root / "nowhere"), _state_history_cache=None)
        status, body = self.request("/state-history/STATE_SPLIT")
        self.assertEqual((status, body["vanilla_source"]), (200, "vanilla_parsed"))
        self.assertEqual([p["country"] for p in body["parts"]], ["AAA", "BBB"])
        # The hub table is the mod's own map_data, so it is there too.
        self.assertEqual(body["parts"][1]["hubs"], ["city"])

    def test_no_history_anywhere_is_a_503(self):
        self.patch(_vanilla_source={"kind": "vanilla_parsed"},
                   VANILLA_PARSED_DIR=str(self.root / "no_snapshot"), _state_history_cache=None)
        self.assertEqual(self.request("/state-history/STATE_SPLIT")[0], 503)

    def test_mod_history_file_layers_on_vanilla(self):
        _write(self.mod / "common/history/states/zz_mod.txt",
               "STATES = { s:STATE_WHOLE = { add_claim = c:QQQ } }")
        _status, body = self.request("/state-history/STATE_WHOLE")
        self.assertEqual(body["claims"], ["QQQ"])

    # ---- prestige goods ----------------------------------------------------

    def test_prestige_goods_count_against_the_cap(self):
        status, body = self.request("/prestige-goods?base_good=steel")
        self.assertEqual(status, 200)
        self.assertEqual((body["count"], body["cap"], body["free"]), (3, 3, 0))
        by_name = {g["name"]: g for g in body["prestige_goods"]}
        self.assertEqual(by_name["prestige_good_v1"]["origin"], "vanilla")
        self.assertEqual(by_name["prestige_good_m1"]["origin"], "mod")
        self.assertEqual(by_name["prestige_good_m1"]["companies"], ["company_a"])
        self.assertEqual(by_name["prestige_good_v2"]["companies"], [])

    def test_good_with_no_prestige_goods_has_every_slot_free(self):
        status, body = self.request("/prestige-goods?base_good=tools")
        self.assertEqual((status, body["count"], body["free"]), (200, 0, 3))
        self.assertEqual(self.request("/prestige-goods?base_good=nope")[0], 404)
        _status, rows = self.request("/prestige-goods")
        self.assertEqual([r["base_good"] for r in rows], ["steel"])


if __name__ == "__main__":
    unittest.main()
