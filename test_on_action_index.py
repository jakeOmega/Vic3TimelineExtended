"""Merge-aware GET /on-actions and GET /on-action-callers (#333):
on_action_index over small mod trees and the mod's own files, and the server's
handlers called in-process. No game install and no running server needed."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import external_mod_overlap as ext
import mod_state_server as mss
import on_action_index as oai
from mod_state import ModState

REPO = Path(__file__).resolve().parent

# Three mod files hooking the same pulse, as ten of the mod's did in #333.
MOD_FILES = {
    "common/on_actions/a_first_on_actions.txt": """
on_monthly_pulse_country = {
	on_actions = {
		first_monthly_on_action
		first_delayed_on_action
	}
	events = { first_events.1 }
}
first_monthly_on_action = {
	effect = {
		te_first_update = yes
	}
}
first_delayed_on_action = {
	trigger = { is_player = yes }
	effect = { te_wrapper_update = { WHO = root } }
}
""",
    "common/on_actions/b_second_on_actions.txt": """
on_monthly_pulse_country = { on_actions = { second_monthly_on_action } }
second_monthly_on_action = {
	random_events = {
		chance_to_happen = 50
		100 = 0
		10 = second_events.1
		5 = second_events.2
	}
	effect = {
		if = {
			limit = { has_variable = second_armed }
			trigger_event = { id = second_events.3 }
		}
	}
}
on_yearly_events = {
	random_events = { 10 = second_events.4 }
}
""",
    "common/on_actions/c_third_on_actions.txt": """
on_monthly_pulse_country = {
	on_actions = { third_monthly_on_action }
	effect = { te_first_update = yes }
}
third_monthly_on_action = { effect = { te_event_helper = yes } }
on_yearly_events = {
	random_events = { 5 = third_events.1 100 = 0 }
}
""",
    # A console harness hooking a live pulse (te_debug_tax_on_actions.txt).
    "common/on_actions/te_debug_probe_on_actions.txt": """
on_monthly_pulse_country = { on_actions = { te_probe_pulse } }
te_probe_pulse = { effect = { te_first_update = yes } }
""",
    "common/scripted_effects/test_effects.txt": """
te_first_update = { add_treasury = 1 }
te_wrapper_update = { $WHO$ = { te_first_update = yes } }
te_event_helper = { trigger_event = { id = third_events.2 } }
te_unused_effect = { add_treasury = 2 }
""",
    "events/second_events.txt": """
namespace = second_events
second_events.3 = { type = country_event }
""",
}

VANILLA_FILES = {
    "common/on_actions/00_code_on_actions.txt": """
on_monthly_pulse_country = {
	on_actions = {
		vanilla_monthly_on_action
		delay = { days = 5 }
		vanilla_delayed_on_action
	}
	events = { vanilla_events.1 }
	effect = { vanilla_effect = yes }
}
on_vanilla_only = { events = { vanilla_events.2 } }
""",
}


def _write(root: Path, files: dict) -> Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


class _Trees(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.mod = _write(Path(cls.tmp.name) / "mod", MOD_FILES)
        cls.game = _write(Path(cls.tmp.name) / "install" / "game", VANILLA_FILES)


class BlockItemsTests(unittest.TestCase):
    def test_bare_tokens_and_pairs(self):
        self.assertEqual(oai.block_items("{ a b.1 c }"), (["a", "b.1", "c"], []))
        self.assertEqual(oai.block_items("{ 100 = 0 10 = ev.1 chance_to_happen = 50 }"),
                         ([], [("100", "0"), ("10", "ev.1"), ("chance_to_happen", "50")]))

    def test_a_nested_block_is_skipped_whole(self):
        self.assertEqual(oai.block_items("{ a delay = { days = 5 } b { x y } c }"),
                         (["a", "b", "c"], [("delay", None)]))

    def test_a_scalar_or_nothing_gives_nothing(self):
        self.assertEqual(oai.block_items("some_on_action"), ([], []))
        self.assertEqual(oai.block_items(None), ([], []))

    def test_scan_script_keeps_a_long_block_whole_on_request(self):
        names = " ".join(f"some_long_on_action_name_{i}" for i in range(40))
        text = "hook = {\n\ton_actions = { " + names + " }\n}\n"
        capped = ext.scan_script(text)[0][0].children[0][2]
        whole = ext.scan_script(text, block_cap=None)[0][0].children[0][2]
        self.assertLessEqual(len(capped), 200)
        self.assertTrue(capped.endswith("…"))
        self.assertEqual(oai.block_items(whole)[0], names.split())


class ScanTests(_Trees):
    def test_every_declaration_is_kept_with_file_and_line(self):
        index = oai.scan(str(self.mod))
        entry = index.entry("on_monthly_pulse_country")
        self.assertEqual(entry["declarations"], 4)
        self.assertEqual(
            [(s["file"], s["line"]) for s in entry["sources"]],
            [("common/on_actions/a_first_on_actions.txt", 2),
             ("common/on_actions/b_second_on_actions.txt", 2),
             ("common/on_actions/c_third_on_actions.txt", 2),
             ("common/on_actions/te_debug_probe_on_actions.txt", 2)])
        self.assertEqual(entry["sources"][0], {
            "file": "common/on_actions/a_first_on_actions.txt", "line": 2, "origin": "mod",
            "on_actions": ["first_monthly_on_action", "first_delayed_on_action"],
            "events": ["first_events.1"], "random_events": {},
            "fields": ["on_actions", "events"],
        })

    def test_lists_merge_in_file_order(self):
        merged = oai.scan(str(self.mod)).entry("on_monthly_pulse_country")["merged"]
        self.assertEqual(merged["on_actions"], [
            "first_monthly_on_action", "first_delayed_on_action",
            "second_monthly_on_action", "third_monthly_on_action", "te_probe_pulse"])
        self.assertEqual(merged["events"], ["first_events.1"])
        self.assertEqual(merged["random_events"], {})

    def test_without_vanilla_the_origin_says_so(self):
        entry = oai.scan(str(self.mod), "/nonexistent/game").entry("on_monthly_pulse_country")
        self.assertEqual(entry["origin"], "mod (vanilla not indexed)")
        self.assertIs(entry["vanilla_indexed"], False)
        self.assertIn("vanilla", entry["note"])
        self.assertEqual({s["origin"] for s in entry["sources"]}, {"mod"})

    def test_with_the_game_files_vanilla_comes_first(self):
        index = oai.scan(str(self.mod), str(self.game))
        entry = index.entry("on_monthly_pulse_country")
        self.assertEqual(entry["origin"], "mod+vanilla")
        self.assertIs(entry["vanilla_indexed"], True)
        self.assertNotIn("note", entry)
        self.assertEqual(entry["sources"][0]["file"],
                         "game/common/on_actions/00_code_on_actions.txt")
        self.assertEqual(entry["sources"][0]["origin"], "vanilla")
        # Vanilla's `delay = { days = 5 }` entry is not an on-action name.
        self.assertEqual(entry["merged"]["on_actions"][:3], [
            "vanilla_monthly_on_action", "vanilla_delayed_on_action", "first_monthly_on_action"])
        self.assertEqual(entry["merged"]["events"], ["vanilla_events.1", "first_events.1"])
        self.assertEqual(index.entry("on_vanilla_only")["origin"], "vanilla")
        self.assertEqual(index.entry("first_monthly_on_action")["origin"], "mod")

    def test_an_effect_set_twice_names_the_later_file_as_winner(self):
        index = oai.scan(str(self.mod), str(self.game))
        rows = index.entry("on_monthly_pulse_country")["fields_set_more_than_once"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["field"], "effect")
        self.assertEqual(row["rule"], oai.RULE_OVERWRITES)
        self.assertEqual([d["origin"] for d in row["declarations"]], ["vanilla", "mod"])
        # The mod's block replaces vanilla's: the case the scripting guide warns of.
        self.assertEqual(row["winner"],
                         {"file": "common/on_actions/c_third_on_actions.txt", "line": 4})

    def test_the_additive_lists_are_not_reported(self):
        index = oai.scan(str(self.mod))
        self.assertEqual(index.entry("on_monthly_pulse_country")["fields_set_more_than_once"], [])

    def test_a_field_with_no_recorded_rule_has_no_winner(self):
        row, = oai.scan(str(self.mod)).entry("on_yearly_events")["fields_set_more_than_once"]
        self.assertEqual(row["field"], "random_events")
        self.assertEqual(row["rule"], oai.RULE_UNKNOWN)
        self.assertIsNone(row["winner"])

    def test_random_events_weights(self):
        index = oai.scan(str(self.mod))
        source, = index.entry("second_monthly_on_action")["sources"]
        self.assertEqual(source["random_events"],
                         {"0": 100, "second_events.1": 10, "second_events.2": 5})
        self.assertEqual(source["chance_to_happen"], "50")
        self.assertEqual(source["fields"], ["random_events", "effect"])
        self.assertEqual(index.entry("on_yearly_events")["merged"]["random_events"],
                         {"second_events.4": 10, "third_events.1": 5, "0": 100})

    def test_fired_by_names_the_declaration_listing_it(self):
        index = oai.scan(str(self.mod))
        self.assertEqual(index.entry("second_monthly_on_action")["fired_by"], [{
            "on_action": "on_monthly_pulse_country",
            "file": "common/on_actions/b_second_on_actions.txt", "line": 2, "origin": "mod"}])
        self.assertEqual(index.entry("on_monthly_pulse_country")["fired_by"], [])

    def test_listing_is_the_mods_on_actions(self):
        index = oai.scan(str(self.mod), str(self.game))
        rows = {row["id"]: row for row in index.listing()}
        self.assertNotIn("on_vanilla_only", rows)
        self.assertEqual(rows["on_monthly_pulse_country"]["declarations"], 5)
        self.assertEqual(rows["on_yearly_events"]["files"], [
            "common/on_actions/b_second_on_actions.txt",
            "common/on_actions/c_third_on_actions.txt"])

    def test_unknown_name_and_missing_folder(self):
        self.assertIsNone(oai.scan(str(self.mod)).entry("on_nope"))
        empty = oai.scan("/nonexistent/mod")
        self.assertEqual(empty.declarations, {})
        self.assertIs(empty.vanilla_indexed, False)


class CallersTests(_Trees):
    def callers(self, target):
        return oai.callers(str(self.mod), target)

    def test_effect_called_directly_through_a_helper_and_from_a_harness(self):
        out = self.callers("te_first_update")
        self.assertEqual(out["kind"], "scripted_effect")
        self.assertEqual(out["on_actions"], [
            "first_delayed_on_action", "first_monthly_on_action",
            "on_monthly_pulse_country", "te_probe_pulse"])
        self.assertEqual(out["count"], 4)
        rows = {row["on_action"]: row for row in out["callers"]}
        direct = rows["first_monthly_on_action"]
        self.assertEqual((direct["file"], direct["line"], direct["via"], direct["through"]),
                         ("common/on_actions/a_first_on_actions.txt", 11, "effect", []))
        self.assertEqual(direct["hooks"], ["on_monthly_pulse_country"])
        self.assertEqual(rows["first_delayed_on_action"]["through"], ["te_wrapper_update"])
        # Guards read as /event-dispatch gives them: the tokens, without the `=`.
        self.assertEqual(rows["first_delayed_on_action"]["guards"], "is_player yes")
        self.assertEqual(rows["te_probe_pulse"]["file"],
                         "common/on_actions/te_debug_probe_on_actions.txt")
        # The hook's own effect block calls it too: a root is its own hook.
        self.assertEqual(rows["on_monthly_pulse_country"]["hooks"], ["on_monthly_pulse_country"])

    def test_effect_no_on_action_runs(self):
        out = self.callers("te_unused_effect")
        self.assertEqual((out["count"], out["on_actions"], out["callers"]), (0, [], []))

    def test_event_from_a_list_an_effect_block_and_a_scripted_effect(self):
        listed = self.callers("second_events.1")
        self.assertEqual(listed["kind"], "event")
        self.assertEqual([(r["on_action"], r["via"]) for r in listed["callers"]],
                         [("second_monthly_on_action", "random_events")])
        fired = self.callers("second_events.3")["callers"][0]
        self.assertEqual((fired["on_action"], fired["via"], fired["guards"]),
                         ("second_monthly_on_action", "trigger_event", "has_variable second_armed"))
        helper = self.callers("third_events.2")["callers"][0]
        self.assertEqual((helper["on_action"], helper["via"], helper["through"]),
                         ("third_monthly_on_action", "trigger_event", ["te_event_helper"]))

    def test_on_action_target_gives_the_declarations_listing_it(self):
        out = self.callers("third_monthly_on_action")
        self.assertEqual(out["kind"], "on_action")
        self.assertEqual([(r["on_action"], r["file"], r["via"]) for r in out["callers"]], [
            ("on_monthly_pulse_country", "common/on_actions/c_third_on_actions.txt", "on_actions")])

    def test_unknown_target_is_none(self):
        self.assertIsNone(self.callers("te_no_such_thing"))

    def test_says_it_is_mod_only(self):
        out = self.callers("te_first_update")
        self.assertEqual(out["origin"], "mod (vanilla not indexed)")
        self.assertIn("Mod script only", out["note"])


class HandlerTests(_Trees):
    """ModStateHandler.route on /on-actions and /on-action-callers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.state = ModState({}, {"On Actions": str(cls.mod / "common" / "on_actions")})

    def get(self, *parts, game=None, engine_docs=None):
        handler = object.__new__(mss.ModStateHandler)
        with mock.patch.object(mss, "ms", self.state), \
                mock.patch.object(mss, "mod_path", str(self.mod)), \
                mock.patch.object(mss, "base_game_path", game or "/nonexistent"), \
                mock.patch.object(mss, "engine_docs", engine_docs or {}):
            return handler.route(list(parts), {})

    def test_the_store_is_last_wins_and_the_endpoint_is_not(self):
        out = self.get("on-actions", "on_monthly_pulse_country")
        # The parsed store keeps the last file's block (#333's complaint) ...
        self.assertEqual(out["raw"], ["=", {"on_actions": ["=", ["te_probe_pulse"]]}])
        self.assertIn("last declaration", out["raw_note"])
        # ... and the endpoint now shows every file's.
        self.assertEqual(out["type"], "On Actions")
        self.assertEqual(out["id"], "on_monthly_pulse_country")
        self.assertEqual(len(out["sources"]), 4)
        self.assertEqual(len(out["merged"]["on_actions"]), 5)
        self.assertEqual(out["origin"], "mod (vanilla not indexed)")
        json.dumps(out)

    def test_a_single_declaration_has_no_raw_note(self):
        out = self.get("on-actions", "first_monthly_on_action")
        self.assertEqual(out["declarations"], 1)
        self.assertIn("raw", out)
        self.assertNotIn("raw_note", out)

    def test_vanilla_is_read_from_the_install_when_there_is_one(self):
        out = self.get("on-actions", "on_monthly_pulse_country",
                       game=str(self.game.parent))
        self.assertEqual(out["origin"], "mod+vanilla")
        self.assertEqual(out["sources"][0]["origin"], "vanilla")
        only = self.get("on-actions", "on_vanilla_only", game=str(self.game.parent))
        self.assertEqual(only["origin"], "vanilla")
        self.assertNotIn("raw", only)   # the store is mod-only

    def test_engine_docs_entry_is_attached(self):
        docs = {"on-actions": [{"name": "on_monthly_pulse_country", "from_code": True,
                                "scopes": ["country"]}]}
        out = self.get("on-actions", "on_monthly_pulse_country", engine_docs=docs)
        self.assertEqual(out["engine"], {"from_code": True, "scopes": ["country"]})
        self.assertNotIn("engine", self.get("on-actions", "on_monthly_pulse_country"))

    def test_listing_keeps_type_and_id_and_adds_the_files(self):
        rows = self.get("on-actions")
        self.assertEqual({row["type"] for row in rows}, {"On Actions"})
        by_id = {row["id"]: row for row in rows}
        self.assertEqual(set(by_id), set(self.state.get_data("On Actions")))
        self.assertEqual(by_id["on_monthly_pulse_country"]["declarations"], 4)

    def test_unknown_on_action_is_404(self):
        with self.assertRaises(mss.NotFound):
            self.get("on-actions", "on_nope")

    def test_a_name_only_the_stale_store_has_is_still_served(self):
        handler = object.__new__(mss.ModStateHandler)
        stub = mock.Mock()
        stub.get_data.return_value = {"oa_gone": ("=", {})}
        with mock.patch.object(mss, "ms", stub), \
                mock.patch.object(mss, "mod_path", str(self.mod)), \
                mock.patch.object(mss, "base_game_path", "/nonexistent"), \
                mock.patch.object(mss, "engine_docs", {}):
            out = handler.route(["on-actions", "oa_gone"], {})
            listing = handler.route(["on-actions"], {})
        self.assertEqual((out["declarations"], out["sources"]), (0, []))
        self.assertIn("reload", out["note"])
        self.assertIn({"type": "On Actions", "id": "oa_gone", "declarations": 0, "files": []},
                      listing)

    def test_nothing_loaded_and_nothing_on_disk_is_503(self):
        handler = object.__new__(mss.ModStateHandler)
        stub = mock.Mock()
        stub.get_data.return_value = None
        with mock.patch.object(mss, "ms", stub), \
                mock.patch.object(mss, "mod_path", "/nonexistent/mod"), \
                mock.patch.object(mss, "base_game_path", "/nonexistent"):
            with self.assertRaises(mss.DataNotLoaded):
                handler.route(["on-actions"], {})

    def test_callers_route(self):
        out = self.get("on-action-callers", "te_first_update")
        self.assertEqual(out["target"], "te_first_update")
        self.assertEqual(out["count"], 4)
        with self.assertRaises(mss.NotFound):
            self.get("on-action-callers", "te_no_such_thing")
        with self.assertRaises(mss.BadRequest):
            self.get("on-action-callers")

    def test_both_endpoints_are_in_the_help_index(self):
        paths = [row["path"] for row in object.__new__(mss.ModStateHandler)._help()["get"]]
        for prefix in ("/on-actions/", "/on-action-callers/", "/building-groups/<id>"):
            self.assertTrue(any(p.startswith(prefix) for p in paths), prefix)


class ModFilesTests(unittest.TestCase):
    """The mod's own on-actions: what #333 had to grep for."""

    @classmethod
    def setUpClass(cls):
        cls.index = oai.scan(str(REPO))

    def test_the_monthly_country_pulse_shows_every_declaring_file(self):
        entry = self.index.entry("on_monthly_pulse_country")
        files = {s["file"] for s in entry["sources"]}
        for name in ("extra_on_actions.txt", "sol_expectations_on_actions.txt",
                     "space_race_on_actions.txt", "wonder_events_on_actions.txt"):
            self.assertIn(f"common/on_actions/{name}", files)
        self.assertGreaterEqual(entry["declarations"], 10)
        for name in ("sol_expectations_monthly_on_action", "space_race_on_action",
                     "wonder_events_on_action"):
            self.assertIn(name, entry["merged"]["on_actions"])

    def test_game_start_merges_every_files_hook(self):
        merged = self.index.entry("on_game_started")["merged"]["on_actions"]
        self.assertIn("te_init_global_state", merged)
        self.assertIn("te_monetary_on_game_started", merged)


if __name__ == "__main__":
    unittest.main()
