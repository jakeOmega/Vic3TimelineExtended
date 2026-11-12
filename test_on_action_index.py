"""Merge-aware GET /on-actions and GET /on-action-callers (#333):
on_action_index over small mod trees and the mod's own files, and the server's
handlers called in-process. No game install and no running server needed."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import event_context_audit as eca
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
	random_events = {
		chance_to_happen = 65
		10 = second_events.4
		10 = shared_events.1
	}
}
""",
    "common/on_actions/c_third_on_actions.txt": """
on_monthly_pulse_country = {
	on_actions = { third_monthly_on_action }
	effect = { te_first_update = yes }
}
third_monthly_on_action = {
	effect = {
		te_event_helper = yes
		te_guarded_helper = yes
	}
}
on_yearly_events = {
	random_events = { 5 = third_events.1 5 = shared_events.1 100 = 0 }
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
te_event_helper = {
	if = {
		limit = { has_variable = helper_armed }
		trigger_event = { id = third_events.2 }
	}
}
te_guarded_helper = {
	if = {
		limit = { te_full_system = yes }
		te_guarded_inner = yes
	}
}
te_guarded_inner = { add_treasury = 3 }
te_event_run_effect = { add_treasury = 4 }
te_je_only_effect = { add_treasury = 5 }
te_console_only_effect = { add_treasury = 6 }
te_unused_effect = { add_treasury = 2 }
""",
    # second_events.3 is fired by an on-action and runs an effect from its
    # immediate and from an option; second_events.9 is fired by nothing.
    "events/second_events.txt": """
namespace = second_events
second_events.3 = {
	type = country_event
	immediate = {
		te_event_run_effect = yes
	}
	option = {
		name = second_events.3.a
		trigger = { is_ai = no }
		te_event_run_effect = yes
		trigger_event = { id = second_events.5 }
	}
}
second_events.5 = {
	type = country_event
	immediate = { te_je_only_effect = yes }
}
second_events.9 = {
	type = country_event
	immediate = { te_console_only_effect = yes }
}
""",
    "common/journal_entries/je_test.txt": """
je_test = {
	on_monthly_pulse = {
		effect = {
			te_je_only_effect = yes
			if = {
				limit = { always = yes }
				te_je_only_effect = yes
			}
		}
	}
}
""",
    "common/scripted_buttons/test_buttons.txt": """
test_button = {
	effect = { te_guarded_helper = yes }
}
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
    # Sorts after every mod file: vanilla's files are not read first.
    "common/on_actions/zz_late_on_actions.txt": """
on_monthly_pulse_country = {
	on_actions = { vanilla_late_on_action }
	effect = { vanilla_late_effect = yes }
}
""",
    # The mod ships a file at this path, so the game never reads this one.
    "common/on_actions/b_second_on_actions.txt": """
on_shadowed = { events = { vanilla_events.3 } }
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

    def test_vanilla_and_mod_files_load_as_one_list_by_file_name(self):
        # Load Order fact 2 (probed): vanilla is not read first.
        index = oai.scan(str(self.mod), str(self.game))
        entry = index.entry("on_monthly_pulse_country")
        self.assertEqual(entry["origin"], "mod+vanilla")
        self.assertIs(entry["vanilla_indexed"], True)
        self.assertNotIn("note", entry)
        self.assertEqual([(s["origin"], s["file"]) for s in entry["sources"]], [
            ("vanilla", "game/common/on_actions/00_code_on_actions.txt"),
            ("mod", "common/on_actions/a_first_on_actions.txt"),
            ("mod", "common/on_actions/b_second_on_actions.txt"),
            ("mod", "common/on_actions/c_third_on_actions.txt"),
            ("mod", "common/on_actions/te_debug_probe_on_actions.txt"),
            ("vanilla", "game/common/on_actions/zz_late_on_actions.txt"),
        ])
        # Vanilla's `delay = { days = 5 }` entry is not an on-action name.
        self.assertEqual(entry["merged"]["on_actions"], [
            "vanilla_monthly_on_action", "vanilla_delayed_on_action",
            "first_monthly_on_action", "first_delayed_on_action", "second_monthly_on_action",
            "third_monthly_on_action", "te_probe_pulse", "vanilla_late_on_action"])
        self.assertEqual(entry["merged"]["events"], ["vanilla_events.1", "first_events.1"])
        self.assertEqual(index.entry("on_vanilla_only")["origin"], "vanilla")
        self.assertEqual(index.entry("first_monthly_on_action")["origin"], "mod")

    def test_a_vanilla_file_the_mod_ships_at_the_same_path_is_not_read(self):
        index = oai.scan(str(self.mod), str(self.game))
        self.assertIsNone(index.entry("on_shadowed"))
        self.assertEqual(index.shadowed_vanilla_files,
                         ["game/common/on_actions/b_second_on_actions.txt"])
        self.assertEqual(index.entry("on_monthly_pulse_country")["shadowed_vanilla_files"],
                         ["game/common/on_actions/b_second_on_actions.txt"])
        self.assertNotIn("shadowed_vanilla_files", oai.scan(str(self.mod)).entry("on_yearly_events"))

    def test_an_effect_set_twice_names_the_later_file_and_the_rules_status(self):
        index = oai.scan(str(self.mod), str(self.game))
        rows = index.entry("on_monthly_pulse_country")["fields_set_more_than_once"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["field"], "effect")
        self.assertEqual(row["rule"], oai.RULE_OVERWRITES)
        self.assertEqual([d["origin"] for d in row["declarations"]], ["vanilla", "mod", "vanilla"])
        # The later file is vanilla's here: a mod file does not win by being the mod's.
        self.assertEqual(row["winner"],
                         {"file": "game/common/on_actions/zz_late_on_actions.txt", "line": 4})
        # "The later file's wins" is a documented claim, not a probed one.
        self.assertEqual(row["rule_status"], ext.LOAD_ORDER_MODEL["on_actions"]["status"])
        self.assertEqual(row["rule_status"], "documented")
        self.assertIn("LOAD_ORDER_MODEL", row["rule_see"])

    def test_a_mod_file_sorting_first_loses_the_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _write(Path(tmp) / "mod", {
                "common/on_actions/aa_mod.txt": "on_x = {\n\teffect = { mod_effect = yes }\n}\n"})
            game = _write(Path(tmp) / "install" / "game", {
                "common/on_actions/zz_vanilla.txt": "on_x = {\n\teffect = { v = yes }\n}\n"})
            entry = oai.scan(str(mod), str(game)).entry("on_x")
        self.assertEqual([s["origin"] for s in entry["sources"]], ["mod", "vanilla"])
        row, = entry["fields_set_more_than_once"]
        self.assertEqual(row["winner"], {"file": "game/common/on_actions/zz_vanilla.txt", "line": 2})

    def test_the_additive_lists_are_not_reported(self):
        index = oai.scan(str(self.mod))
        self.assertEqual(index.entry("on_monthly_pulse_country")["fields_set_more_than_once"], [])

    def test_a_field_with_no_recorded_rule_has_no_winner(self):
        row, = oai.scan(str(self.mod)).entry("on_yearly_events")["fields_set_more_than_once"]
        self.assertEqual(row["field"], "random_events")
        self.assertEqual(row["rule"], oai.RULE_UNKNOWN)
        self.assertIsNone(row["winner"])
        self.assertNotIn("rule_status", row)

    def test_one_random_events_pool_is_given_with_its_chance(self):
        index = oai.scan(str(self.mod))
        entry = index.entry("second_monthly_on_action")
        source, = entry["sources"]
        self.assertEqual(source["random_events"],
                         {"0": 100, "second_events.1": 10, "second_events.2": 5})
        self.assertEqual(source["chance_to_happen"], 50)
        self.assertEqual(source["fields"], ["random_events", "effect"])
        self.assertEqual(entry["merged"]["random_events"], source["random_events"])
        self.assertEqual(entry["merged"]["chance_to_happen"], 50)

    def test_several_random_events_pools_are_not_merged_into_one(self):
        entry = oai.scan(str(self.mod)).entry("on_yearly_events")
        # How the engine combines two pools is not recorded: no summed table.
        self.assertIsNone(entry["merged"]["random_events"])
        self.assertEqual(entry["merged"]["random_events_note"], oai.RANDOM_EVENTS_NOTE)
        self.assertNotIn("chance_to_happen", entry["merged"])
        # Each source keeps its own pool and its own chance_to_happen; an
        # event both pools list keeps each pool's weight.
        self.assertEqual([(s["random_events"], s.get("chance_to_happen")) for s in entry["sources"]], [
            ({"second_events.4": 10, "shared_events.1": 10}, 65),
            ({"third_events.1": 5, "shared_events.1": 5, "0": 100}, None),
        ])
        self.assertEqual(entry["merged"]["on_actions"], [])

    def test_a_directive_leaves_the_declarations_unmerged(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _write(Path(tmp), {"common/on_actions/a.txt": (
                "REPLACE:on_z = { on_actions = { r1 } }\n"
                "on_z = { on_actions = { r0 } }\n"
                "on_plain = { on_actions = { p } }\n")})
            index = oai.scan(str(mod))
        entry = index.entry("on_z")
        self.assertIsNone(entry["merged"])
        self.assertEqual(entry["merged_note"], oai.DIRECTIVE_NOTE)
        self.assertEqual(entry["directive_declarations"], [{
            "file": "common/on_actions/a.txt", "line": 1, "directive": "REPLACE",
            "rule": oai.RULE_DIRECTIVE}])
        self.assertEqual([s["on_actions"] for s in entry["sources"]], [["r1"], ["r0"]])
        row, = entry["fields_set_more_than_once"]
        self.assertEqual((row["field"], row["rule"], row["winner"]),
                         ("on_actions", oai.RULE_DIRECTIVE, None))
        plain = index.entry("on_plain")
        self.assertEqual(plain["merged"]["on_actions"], ["p"])
        self.assertNotIn("directive_declarations", plain)

    def test_a_broken_file_is_named_on_what_it_touches(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _write(Path(tmp), {
                "common/on_actions/a_broken.txt": (
                    "on_first = {\n\teffect = { x = yes\n}\n"
                    "on_swallowed = { on_actions = { a } }\n"),
                "common/on_actions/b_fine.txt": "on_fine = { on_actions = { b } }\n"})
            index = oai.scan(str(mod))
        warning = {"file": "common/on_actions/a_broken.txt",
                   "warning": "1 block(s) still open at the end of the file"}
        self.assertEqual(index.warnings, [warning])
        self.assertIsNone(index.entry("on_swallowed"))   # read as a field of on_first
        self.assertEqual(index.entry("on_first")["warnings"], [warning])
        self.assertNotIn("warnings", index.entry("on_fine"))
        rows = {row["id"]: row for row in index.listing()}
        self.assertEqual(rows["on_first"]["warnings"], [warning])
        self.assertNotIn("warnings", rows["on_fine"])

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
        self.assertEqual(rows["on_monthly_pulse_country"]["declarations"], 6)
        self.assertEqual(rows["on_yearly_events"]["files"], [
            "common/on_actions/b_second_on_actions.txt",
            "common/on_actions/c_third_on_actions.txt"])

    def test_unknown_name_and_missing_folder(self):
        self.assertIsNone(oai.scan(str(self.mod)).entry("on_nope"))
        empty = oai.scan("/nonexistent/mod")
        self.assertEqual(empty.declarations, {})
        self.assertIs(empty.vanilla_indexed, False)


class CallersTests(_Trees):
    def callers(self, target, code=None):
        return oai.callers(str(self.mod), target, code)

    def test_effect_called_directly_through_a_helper_and_from_a_harness(self):
        out = self.callers("te_first_update")
        self.assertEqual(out["kind"], "scripted_effect")
        self.assertEqual(out["on_actions"], [
            "first_delayed_on_action", "first_monthly_on_action",
            "on_monthly_pulse_country", "te_probe_pulse"])
        self.assertEqual(out["count"], 4)
        self.assertEqual((out["not_followed"], out["unreached"]), ([], []))
        rows = {row["on_action"]: row for row in out["callers"]}
        direct = rows["first_monthly_on_action"]
        self.assertEqual((direct["file"], direct["line"], direct["via"], direct["through"]),
                         ("common/on_actions/a_first_on_actions.txt", 11, "effect", []))
        self.assertEqual(direct["guards"], [""])
        self.assertEqual(direct["roots"], ["on_monthly_pulse_country"])
        self.assertEqual(rows["first_delayed_on_action"]["through"], ["te_wrapper_update"])
        self.assertEqual(rows["te_probe_pulse"]["file"],
                         "common/on_actions/te_debug_probe_on_actions.txt")
        # The hook's own effect block calls it too: a root is its own root.
        self.assertEqual(rows["on_monthly_pulse_country"]["roots"], ["on_monthly_pulse_country"])

    def test_guards_are_given_for_every_hop(self):
        # Guards read as /event-dispatch gives them: the tokens, without the `=`.
        wrapper = {r["on_action"]: r for r in self.callers("te_first_update")["callers"]}
        self.assertEqual(wrapper["first_delayed_on_action"]["guards"], ["is_player yes", ""])
        row, = self.callers("te_guarded_inner")["callers"]
        self.assertEqual(row["on_action"], "third_monthly_on_action")
        self.assertEqual(row["through"], ["te_guarded_helper"])
        # The on-action calls the helper unconditionally; the helper's own
        # `if` guards the target.
        self.assertEqual(row["guards"], ["", "te_full_system yes"])
        self.assertEqual([(h["in"], h["kind"], h["path"]) for h in row["hops"]], [
            ("third_monthly_on_action", "on_action", ["effect"]),
            ("te_guarded_helper", "scripted_effect", ["if"])])

    def test_an_effect_behind_an_event_an_on_action_fires(self):
        out = self.callers("te_event_run_effect")
        self.assertEqual(out["on_actions"], ["second_monthly_on_action"])
        row, = out["callers"]
        self.assertEqual((row["via"], row["through"]), ("trigger_event", ["second_events.3"]))
        self.assertEqual(row["guards"], ["has_variable second_armed", ""])
        event_hop = row["hops"][1]
        self.assertEqual((event_hop["in"], event_hop["kind"], event_hop["path"]),
                         ("second_events.3", "event", ["immediate"]))
        # The same event also runs it from an option.
        self.assertEqual(event_hop["other_sites"], 1)
        self.assertIn("1 on-action(s) reach it", out["summary"])

    def test_an_effect_only_a_journal_entry_pulse_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _write(Path(tmp), {
                "common/scripted_effects/e.txt": "te_pulse_effect = { add_treasury = 1 }\n",
                "common/journal_entries/je.txt": (
                    "je_pulse = {\n\ton_monthly_pulse = {\n\t\teffect = { te_pulse_effect = yes }\n\t}\n}\n"),
            })
            out = oai.callers(str(mod), "te_pulse_effect")
        self.assertEqual((out["count"], out["callers"], out["on_actions"]), (0, [], []))
        self.assertEqual(out["not_followed_count"], 1)
        self.assertEqual(out["not_followed_kinds"], {"journal_entry": 1})
        self.assertEqual(out["not_followed"], [{
            "kind": "journal_entry", "id": "je_pulse", "file": "common/journal_entries/je.txt",
            "line": 3, "path": ["on_monthly_pulse", "effect"], "sites": 1, "through": []}])
        self.assertIn("also called from 1 journal_entry", out["summary"])

    def test_callers_and_not_followed_together(self):
        # A journal entry's pulse calls it twice, and an on-action reaches it
        # through an event's option and a second event.
        out = self.callers("te_je_only_effect")
        self.assertEqual(out["on_actions"], ["second_monthly_on_action"])
        self.assertEqual(out["callers"][0]["through"], ["second_events.3", "second_events.5"])
        self.assertEqual(out["callers"][0]["guards"], ["has_variable second_armed", "is_ai no", ""])
        self.assertEqual(out["callers"][0]["hops"][1]["path"], ["option"])
        row, = out["not_followed"]
        self.assertEqual((row["kind"], row["id"], row["sites"]), ("journal_entry", "je_test", 2))
        # A button reaching the target through a helper names the helper.
        nested, = self.callers("te_guarded_inner")["not_followed"]
        self.assertEqual((nested["kind"], nested["id"], nested["through"]),
                         ("button", "test_button", ["te_guarded_helper"]))

    def test_a_truly_unused_effect_reads_differently_from_an_unfollowed_one(self):
        out = self.callers("te_unused_effect")
        self.assertEqual((out["count"], out["not_followed_count"], out["unreached"]), (0, 0, []))
        self.assertEqual(out["summary"],
                         "no on-action reaches it: nothing in the mod's script calls it")

    def test_an_effect_only_an_unfired_event_runs(self):
        out = self.callers("te_console_only_effect")
        self.assertEqual((out["count"], out["not_followed"]), (0, []))
        self.assertEqual(out["unreached"], [{"kind": "event", "id": "second_events.9"}])
        self.assertIn("unreached", out["summary"])

    def test_event_from_a_list_an_effect_block_and_a_scripted_effect(self):
        listed = self.callers("second_events.1")
        self.assertEqual(listed["kind"], "event")
        self.assertEqual([(r["on_action"], r["via"]) for r in listed["callers"]],
                         [("second_monthly_on_action", "random_events")])
        fired = self.callers("second_events.3")["callers"][0]
        self.assertEqual((fired["on_action"], fired["via"], fired["guards"]),
                         ("second_monthly_on_action", "trigger_event", ["has_variable second_armed"]))
        helper = self.callers("third_events.2")["callers"][0]
        self.assertEqual((helper["on_action"], helper["via"], helper["through"]),
                         ("third_monthly_on_action", "effect", ["te_event_helper"]))
        # The event is fired under the helper's own limit.
        self.assertEqual(helper["guards"], ["", "has_variable helper_armed"])
        self.assertEqual(helper["hops"][1]["via"], "trigger_event")

    def test_on_action_target_gives_the_declarations_listing_it(self):
        out = self.callers("third_monthly_on_action")
        self.assertEqual(out["kind"], "on_action")
        self.assertEqual([(r["on_action"], r["file"], r["via"]) for r in out["callers"]], [
            ("on_monthly_pulse_country", "common/on_actions/c_third_on_actions.txt", "on_actions")])

    def test_roots_are_engine_hooks_only_when_the_engine_docs_say_so(self):
        row = self.callers("te_first_update")["callers"][0]
        self.assertIsNone(row["engine_hooks"])   # no engine docs: not claimed
        row = self.callers("te_first_update", {"on_monthly_pulse_country"})["callers"][0]
        self.assertEqual(row["engine_hooks"], ["on_monthly_pulse_country"])
        row = self.callers("te_first_update", {"on_something_else"})["callers"][0]
        self.assertEqual((row["roots"], row["engine_hooks"]), (["on_monthly_pulse_country"], []))

    def test_unknown_target_is_none(self):
        self.assertIsNone(self.callers("te_no_such_thing"))

    def test_says_it_is_mod_only_and_what_it_does_not_follow(self):
        out = self.callers("te_first_update")
        self.assertEqual(out["origin"], "mod (vanilla not indexed)")
        self.assertIn("Mod script only", out["note"])
        self.assertIn("not_followed", out["note"])


class HandlerTests(_Trees):
    """ModStateHandler.route on /on-actions and /on-action-callers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.state = ModState({}, {"On Actions": str(cls.mod / "common" / "on_actions")})

    def get(self, *parts, game=None, engine_docs=None, mod=None):
        handler = object.__new__(mss.ModStateHandler)
        with mock.patch.object(mss, "ms", self.state), \
                mock.patch.object(mss, "mod_path", str(mod or self.mod)), \
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
        self.assertEqual([s["origin"] for s in out["sources"]],
                         ["vanilla", "mod", "mod", "mod", "mod", "vanilla"])
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
        with self.assertRaises(mss.NotFound) as ctx:
            self.get("on-actions", "on_nope")
        self.assertNotIn("scan_warnings", ctx.exception.payload)

    def test_a_404_names_the_file_that_may_hide_the_on_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = _write(Path(tmp), {"common/on_actions/a_broken.txt": (
                "on_first = {\n\teffect = { x = yes\n}\non_swallowed = { on_actions = { a } }\n")})
            with self.assertRaises(mss.NotFound) as ctx:
                self.get("on-actions", "on_swallowed", mod=mod)
            listing = self.get("on-actions", mod=mod)
        self.assertEqual(ctx.exception.payload["scan_warnings"], [{
            "file": "common/on_actions/a_broken.txt",
            "warning": "1 block(s) still open at the end of the file"}])
        first = next(row for row in listing if row["id"] == "on_first")
        self.assertEqual(first["warnings"], ctx.exception.payload["scan_warnings"])

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
        self.assertIsNone(out["callers"][0]["engine_hooks"])
        with self.assertRaises(mss.NotFound):
            self.get("on-action-callers", "te_no_such_thing")
        with self.assertRaises(mss.BadRequest):
            self.get("on-action-callers")

    def test_callers_route_takes_from_code_from_the_engine_docs(self):
        docs = {"on-actions": [
            {"name": "on_monthly_pulse_country", "from_code": True, "scopes": ["country"]},
            {"name": "on_yearly_events", "from_code": False, "scopes": []}]}
        out = self.get("on-action-callers", "te_first_update", engine_docs=docs)
        self.assertEqual(out["callers"][0]["engine_hooks"], ["on_monthly_pulse_country"])
        # Listed in the docs but not fired from code: a root, not an engine hook.
        row, = self.get("on-action-callers", "second_events.4", engine_docs=docs)["callers"]
        self.assertEqual((row["roots"], row["engine_hooks"]), (["on_yearly_events"], []))

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

    def test_no_on_action_gets_a_single_pool_from_several(self):
        several = 0
        for name, decls in self.index.declarations.items():
            pools = [d for d in decls if "random_events" in d.field_names()]
            if len(pools) > 1:
                several += 1
                entry = self.index.entry(name)
                self.assertIsNone(entry["merged"]["random_events"], name)
                self.assertEqual([s["random_events"] for s in entry["sources"]],
                                 [d.random_events for d in decls], name)
        self.assertGreater(several, 0)   # on_yearly_events: one pool a file

    def test_an_effect_something_calls_never_reads_as_uncalled(self):
        """Zero callers must not look complete: every scripted effect the
        dispatch graph sees a call of has an on-action caller, a not_followed
        entity or an unreached link to show for it."""
        graph = eca.build_graph(str(REPO), include_console=True)
        silent, through_events = [], 0
        with mock.patch.object(eca, "build_graph", return_value=graph):
            for effect in graph.effect_file:
                out = oai.callers(str(REPO), effect)
                called = any(entity != effect for _r, _l, _p, _s, _c, entity, _k, _a
                             in graph.effect_calls.get(effect, []))
                if called and not (out["callers"] or out["not_followed"] or out["unreached"]):
                    silent.append(effect)
                through_events += any("." in name for row in out["callers"]
                                      for name in row["through"])
                self.assertEqual(out["count"] == 0 and not out["not_followed"]
                                 and not out["unreached"],
                                 out["summary"].endswith("nothing in the mod's script calls it"),
                                 effect)
        self.assertEqual(silent, [])
        # The mod runs many effects from the immediate of an event an on-action fires.
        self.assertGreater(through_events, 0)


if __name__ == "__main__":
    unittest.main()
