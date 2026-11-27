"""The vanilla tables no merged entity type holds, through the server: vanilla
scripted triggers and effects by name (`?source=vanilla`) and war goal types
(#1860), each country's history (#1628) and the defines (#1879). Fixture game
and mod trees in a tempdir; no game install needed."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mod_state_server as mss
import vanilla_parsed
from mod_state import ModState

TRIGGERS = """
country_has_monarchy_law = {
	OR = {
		has_law = law_type:law_monarchy
		has_law = law_type:law_social_monarchy
	}
}
country_is_big = { gdp > $SIZE$ }
"""
EFFECTS = "effect_starting_technology_tier_2_tech = {\n\tadd_technology_researched = enclosure\n}\n"
WAR_GOALS = "make_personal_union = {\n\tkind = make_subject\n}\ncommon_goal = {\n\tkind = annex_country\n}\n"
MOD_WAR_GOALS = "te_seize_strait = {\n\tkind = custom\n}\ncommon_goal = {\n\tkind = conquer_state\n}\n"
COUNTRY = """
COUNTRIES = {
	c:AAA ?= {
		effect_starting_technology_tier_2_tech = yes
		activate_law = law_type:law_monarchy
		ig:ig_landowners ?= { add_ruling_interest_group = yes }
		if = {
			limit = { has_dlc_feature = rp1_content }
			add_journal_entry = { type = je_alpha }
		}
	}
}
"""
DEFINES = "NAI = {\n\tGATE = 0.1\n\tKEEP = 2\n}\nNPops = {\n\tA = 1\n}\n"
MOD_DEFINES = "NAI = {\n\tGATE = 0.02 # lowered\n}\n"
MOD_TRIGGERS = "te_has_x = { always = yes }\n"


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class VanillaLookupEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base, self.mod = self.root / "install", self.root / "mod"
        game = self.base / "game"
        _write(game / "common/scripted_triggers/00_ep2_victoria_scripted_triggers.txt", TRIGGERS)
        _write(game / "common/scripted_effects/00_starting_inventions.txt", EFFECTS)
        _write(game / "common/war_goal_types/34_make_personal_union.txt", WAR_GOALS)
        _write(game / "common/history/countries/aaa - alpha.txt", COUNTRY)
        _write(game / "common/defines/00_ai.txt", DEFINES)
        _write(game / "common/laws/00.txt", "law_monarchy = { group = g }\n")
        _write(self.mod / "common/war_goal_types/te_seize_strait.txt", MOD_WAR_GOALS)
        _write(self.mod / "common/defines/extra_defines.txt", MOD_DEFINES)
        _write(self.mod / "common/scripted_triggers/te.txt", MOD_TRIGGERS)
        _write(self.mod / "common/history/extra_history.txt", "GLOBAL = { every_country = { } }\n")
        # A populated game/common, so the server counts the tree as present.
        for i in range(12):
            (game / "common" / f"pad_{i}").mkdir(exist_ok=True)
        base_dirs = {"Laws": str(game / "common/laws")}
        mod_dirs = {"Laws": str(self.mod / "common/laws"),
                    "Scripted Triggers": str(self.mod / "common/scripted_triggers"),
                    "Scripted Effects": str(self.mod / "common/scripted_effects")}
        self.state = ModState(base_dirs, mod_dirs)
        self.state.localization = {"AAA": "Alphaland", "war_goal_te_seize_strait": "Seize the Strait"}
        self.patch(ms=self.state, mod_path=str(self.mod), base_game_path=str(self.base),
                   _vanilla_source={"kind": "game_files"}, _vanilla_tables_cache={})
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

    def use_snapshot(self):
        """Build the fixture's snapshot and serve vanilla from it, with no game files."""
        _write(self.base / "launcher/launcher-settings.json", json.dumps({"rawVersion": "1.0.0"}))
        snap = str(self.root / "snap")
        vanilla_parsed.build(str(self.base), snap)
        self.patch(_vanilla_source={"kind": "vanilla_parsed"}, VANILLA_PARSED_DIR=snap,
                   base_game_path=str(self.root / "nowhere"), _vanilla_tables_cache={})
        return snap

    # ---- scripted triggers and effects --------------------------------------

    def test_vanilla_trigger_by_name(self):
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                if snapshot:
                    self.use_snapshot()
                status, body = self.request("/scripted-triggers/country_has_monarchy_law?source=vanilla")
                self.assertEqual(status, 200)
                self.assertEqual(body["file"], "game/common/scripted_triggers/00_ep2_victoria_scripted_triggers.txt")
                self.assertEqual(body["raw"], ["=", {"OR": ["=", {"has_law": [
                    ["=", "law_type:law_monarchy"], ["=", "law_type:law_social_monarchy"]]}]}])
                self.assertEqual((body["source"], body["in_mod"]), ("vanilla", False))
                self.assertEqual(body["vanilla_source"], "vanilla_parsed" if snapshot else "game_files")
                self.assertNotIn("callers", body)
                _status, body = self.request("/scripted-triggers/country_is_big?source=vanilla")
                self.assertEqual(body["parameters"], ["SIZE"])

    def test_the_merged_table_stays_mod_only(self):
        status, rows = self.request("/scripted-triggers")
        self.assertEqual((status, [r["id"] for r in rows]), (200, ["te_has_x"]))
        status, body = self.request("/scripted-triggers/country_has_monarchy_law")
        self.assertEqual(status, 404)
        self.assertIn("source=vanilla", body["hint"])
        status, body = self.request("/scripted-triggers/no_such_trigger")
        self.assertEqual(status, 404)
        self.assertNotIn("source=vanilla", body["hint"])
        status, rows = self.request("/scripted-effects?source=vanilla")
        self.assertEqual([(r["id"], r["file"]) for r in rows], [
            ("effect_starting_technology_tier_2_tech", "game/common/scripted_effects/00_starting_inventions.txt")])
        status, body = self.request("/scripted-triggers/country_has_monarchy_lw?source=vanilla")
        self.assertEqual(status, 404)
        self.assertIn("country_has_monarchy_law", body["did_you_mean"])
        self.assertEqual(self.request("/scripted-triggers?source=both")[0], 400)

    def test_a_snapshot_without_the_table_is_a_503(self):
        snap = self.use_snapshot()
        manifest = vanilla_parsed.read_manifest(snap)
        del manifest["lookup_types"]
        (Path(snap) / vanilla_parsed.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(self.request("/scripted-triggers/country_has_monarchy_law?source=vanilla")[0], 503)
        # The mod's table still answers, its 404 without the vanilla hint.
        self.assertEqual(self.request("/scripted-triggers/country_has_monarchy_law")[0], 404)

    # ---- war goal types ------------------------------------------------------

    def test_war_goal_types_vanilla_and_mod(self):
        status, body = self.request("/war-goal-types/make_personal_union")
        self.assertEqual(status, 200)
        self.assertEqual((body["source"], body["kind"], body["file"]),
                         ("vanilla", "make_subject", "game/common/war_goal_types/34_make_personal_union.txt"))
        status, body = self.request("/war-goal-types/te_seize_strait")
        self.assertEqual((body["source"], body["kind"], body["name"]), ("mod", "custom", "Seize the Strait"))
        self.assertEqual(body["file"], "common/war_goal_types/te_seize_strait.txt")
        # A key both define: the mod's by default, either on request.
        _status, body = self.request("/war-goal-types/common_goal")
        self.assertEqual((body["source"], body["kind"], body["in_vanilla"]), ("mod", "conquer_state", True))
        _status, body = self.request("/war-goal-types/common_goal?source=vanilla")
        self.assertEqual(body["kind"], "annex_country")
        status, body = self.request("/war-goal-types")
        self.assertEqual({r["id"]: r["source"] for r in body["war_goal_types"]},
                         {"common_goal": "both", "make_personal_union": "vanilla", "te_seize_strait": "mod"})
        _status, body = self.request("/war-goal-types?source=mod")
        self.assertEqual(sorted(r["id"] for r in body["war_goal_types"]), ["common_goal", "te_seize_strait"])
        self.assertEqual(self.request("/war-goal-types/te_seize_strait?source=vanilla")[0], 404)
        self.assertEqual(self.request("/war-goal-types?source=x")[0], 400)

    # ---- country history -----------------------------------------------------

    def test_country_history(self):
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                if snapshot:
                    self.use_snapshot()
                status, body = self.request("/country-history/AAA")
                self.assertEqual(status, 200)
                self.assertEqual(body["country_name"], "Alphaland")
                [rec] = body["history"]
                self.assertEqual((rec["file"], rec["laws"], rec["tech_tier_effects"], rec["ruling_interest_groups"]),
                                 ("aaa - alpha.txt", ["law_monarchy"], ["effect_starting_technology_tier_2_tech"],
                                  ["ig_landowners"]))
                self.assertEqual(rec["conditional"], [{"kind": "if", "limit": "has_dlc_feature = rp1_content",
                                                       "effects": ["add_journal_entry = { type = je_alpha }"]}])
                self.assertEqual((rec["technologies"], rec["tax_level"], rec["institutions"]), ([], None, {}))
                self.assertEqual(body["mod_global_history"], ["common/history/extra_history.txt"])
                self.assertIn("extra_history.txt", body["note"])
                self.assertEqual(body["vanilla_source"], "vanilla_parsed" if snapshot else "game_files")
        _status, body = self.request("/country-history")
        self.assertEqual((body["countries"], body["tags"]), (1, ["AAA"]))
        status, body = self.request("/country-history/AAB")
        self.assertEqual(status, 404)
        self.assertIn("AAA", body["did_you_mean"])

    def test_a_mod_country_history_file_layers_on(self):
        _write(self.mod / "common/history/countries/bbb.txt",
               "COUNTRIES = { c:AAA ?= { add_technology_researched = te_tech } }\n")
        _status, body = self.request("/country-history/AAA")
        self.assertEqual([(r["file"], r["technologies"]) for r in body["history"]],
                         [("aaa - alpha.txt", []), ("bbb.txt", ["te_tech"])])

    # ---- defines -------------------------------------------------------------

    def test_defines(self):
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                if snapshot:
                    self.use_snapshot()
                status, body = self.request("/defines/NAI/GATE")
                self.assertEqual(status, 200)
                self.assertEqual((body["vanilla"], body["mod"], body["effective"], body["mod_file"]),
                                 ("0.1", "0.02", "0.02", "common/defines/extra_defines.txt"))
                _status, body = self.request("/defines/NAI/KEEP")
                self.assertEqual((body["vanilla"], body["mod"], body["effective"], body["mod_file"]),
                                 ("2", None, "2", None))
        _status, body = self.request("/defines/NAI")
        self.assertEqual(body["vanilla"], {"GATE": "0.1", "KEEP": "2"})
        self.assertEqual(body["mod"], {"GATE": {"value": "0.02", "file": "common/defines/extra_defines.txt",
                                                "vanilla": "0.1"}})
        _status, body = self.request("/defines")
        self.assertEqual(body["namespaces"], {"NAI": {"vanilla": 2, "mod": 1}, "NPops": {"vanilla": 1, "mod": 0}})
        self.assertEqual(self.request("/defines/NAI/GAT")[1]["did_you_mean"], ["GATE"])
        self.assertEqual(self.request("/defines/NOPE")[0], 404)

    def test_vanilla_tables_are_read_once_per_load(self):
        self.request("/defines/NAI/GATE")
        _write(self.base / "game/common/defines/00_ai.txt", "NAI = {\n\tGATE = 0.5\n}\n")
        self.assertEqual(self.request("/defines/NAI/GATE")[1]["vanilla"], "0.1")
        mss._vanilla_tables_cache.clear()
        self.assertEqual(self.request("/defines/NAI/GATE")[1]["vanilla"], "0.5")


if __name__ == "__main__":
    unittest.main()
