"""vanilla_refs: who in vanilla's script names a thing, and where vanilla tests a culture (#1563).

The lookups read the installed game, so the tests build a small vanilla tree; one test, skipped without an
install, holds the primary-culture reads equal to the scan the culture merges commit."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mod_state_server as mss
import vanilla_refs as vr

FILES = {
    "common/journal_entries/00_je.txt": """
je_unify = {
	possible = { country_has_primary_culture = cu:alpha }
	on_monthly_pulse = { events = { unify.1 } }
}
je_other = { complete = { always = yes } }
""",
    "events/unify_events.txt": """
namespace = unify
unify.1 = {
	type = country_event
	trigger = { is_alpha_people = yes }
	option = { trigger_event = { id = unify.2 } }
}
unify.2 = {
	immediate = { helper_effect = yes }	# cu:alpha in a comment is not a read
}
""",
    "common/scripted_triggers/00_triggers.txt": """
is_alpha_people = {
	OR = {
		country_has_primary_culture = cu:alpha
		any_primary_culture = { this = cu:beta }
	}
}
""",
    "common/scripted_effects/00_effects.txt": """
helper_effect = {
	every_scope_pop = { limit = { culture = cu:alpha } add_pop_wealth = 1 }
	random_state = { limit = { is_homeland = cu:alpha } add_homeland = cu:beta }
}
""",
    "common/on_actions/00_on_actions.txt": """
on_yearly_pulse_country = { effect = { helper_effect = yes } }
""",
    "common/decisions/00_decisions.txt": """
decision_x = { when_taken = { trigger_event = { id = unify.2 } } }
""",
    "common/country_definitions/00_countries.txt": """
AAA = { color = { 1 2 3 } cultures = { alpha beta } capital = STATE_X }
BBB = { cultures = { beta } }
CCC = { cultures = { gamma } }
""",
    "common/country_formation/00_formables.txt": """
AAA = { use_culture_states = yes possible = { always = yes } }
BBB = { states = { STATE_X } }
""",
    "common/history/states/00_states.txt": """
STATES = { s:STATE_X = { create_state = { country = c:BBB owned_provinces = { x1 } } add_homeland = cu:alpha } }
""",
    "common/customizable_localization/00_loc.txt": """
GetWord = { text = { trigger = { country_has_primary_culture = cu:alpha } localization_key = w } }
""",
}
MOD_FILES = {
    "common/country_definitions/te.txt": "INJECT:AAA = { cultures = { alpha beta cm_ab } }\nDDD = { cultures = { alpha } }\n",
    "common/country_formation/te.txt": "DDD = { use_culture_states = no }\n",
}


def _tree(root, files):
    for rel, text in files.items():
        path = Path(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class _Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.install = Path(tmp.name) / "install"
        self.game = self.install / "game"
        self.mod = Path(tmp.name) / "mod"
        _tree(self.game, FILES)
        _tree(self.mod, MOD_FILES)
        self.vs = vr.load(self.game)


class RefsTests(_Case):
    def test_direct_mentions_with_their_kind(self):
        out = vr.refs(self.vs, "helper_effect")
        self.assertEqual(out["defined_in"], ["common/scripted_effects/00_effects.txt"])
        self.assertEqual([(r["entity"], r["kind"], r["depth"]) for r in out["referenced_by"]],
                         [("on_yearly_pulse_country", "on_actions", 1), ("unify.2", "events", 1)])
        self.assertEqual(out["roots"], {"journal_entries": [], "on_actions": ["on_yearly_pulse_country"],
                                        "decisions": []})
        self.assertTrue(out["more"], "unify.2 has callers of its own one step further up")

    def test_depth_follows_the_callers_up_to_the_roots(self):
        out = vr.refs(self.vs, "helper_effect", depth=4)
        found = {r["entity"]: r["depth"] for r in out["referenced_by"]}
        self.assertEqual(found, {"on_yearly_pulse_country": 1, "unify.2": 1, "decision_x": 2, "unify.1": 2,
                                 "je_unify": 3})
        self.assertEqual(out["roots"], {"journal_entries": ["je_unify"], "on_actions": ["on_yearly_pulse_country"],
                                        "decisions": ["decision_x"]})
        self.assertFalse(out["more"])

    def test_a_root_is_not_followed_and_a_name_nobody_mentions_is_empty(self):
        out = vr.refs(self.vs, "je_other", depth=5)
        self.assertEqual((out["referenced_by"], out["defined_in"]), ([], ["common/journal_entries/00_je.txt"]))
        self.assertEqual(vr.refs(self.vs, "no_such_thing")["defined_in"], [])
        self.assertEqual(vr.refs(self.vs, "x", depth=99)["depth"], vr.MAX_DEPTH)

    def test_folders_that_only_name_things_are_not_callers(self):
        # customizable localization and history mention names without running them
        out = vr.refs(self.vs, "country_has_primary_culture")
        self.assertNotIn("GetWord", [r["entity"] for r in out["referenced_by"]])


class CultureReadTests(_Case):
    def rows(self, culture, mode):
        return {(r["file"].split("/")[1] if r["file"].startswith("common") else "events", r["entity"]): r
                for r in vr.culture_reads(self.vs, culture, mode)}

    def test_primary_reads_and_the_entries_that_reach_them(self):
        rows = self.rows("alpha", "primary")
        self.assertEqual(sorted(rows), [("customizable_localization", "GetWord"), ("journal_entries", "je_unify"),
                                        ("scripted_triggers", "is_alpha_people")])
        self.assertEqual(rows[("journal_entries", "je_unify")]["entries"], ["je_unify"])
        self.assertEqual(rows[("scripted_triggers", "is_alpha_people")]["entries"], ["je_unify"])
        self.assertEqual(rows[("scripted_triggers", "is_alpha_people")]["count"], 1)
        beta = self.rows("beta", "primary")
        self.assertEqual(list(beta), [("scripted_triggers", "is_alpha_people")], "inside any_primary_culture")

    def test_pop_and_homeland_reads_name_their_key(self):
        pop = self.rows("alpha", "pop")
        self.assertEqual({k: r["keys"] for k, r in pop.items()}, {("scripted_effects", "helper_effect"): ["culture"]})
        # An on-action reaches the helper too, so it is not only a journal entry's.
        self.assertEqual(pop[("scripted_effects", "helper_effect")]["entries"], [])
        home = self.rows("alpha", "homeland")
        self.assertEqual({k: r["keys"] for k, r in home.items()},
                         {("scripted_effects", "helper_effect"): ["is_homeland"], ("history", "STATES"): ["add_homeland"]})
        self.assertEqual(self.rows("beta", "homeland")[("scripted_effects", "helper_effect")]["keys"], ["add_homeland"])

    def test_any_is_every_mention_outside_comments(self):
        rows = self.rows("alpha", "any")
        self.assertEqual(len(rows), 5)
        self.assertNotIn(("events", "unify.2"), rows)
        self.assertEqual(sum(r["count"] for r in rows.values()), 6)

    def test_a_bad_mode_or_name_is_refused(self):
        with self.assertRaises(ValueError):
            vr.culture_reads(self.vs, "alpha", "ruler")
        with self.assertRaises(ValueError):
            vr.culture_reads(self.vs, "cu:alpha", "primary")


class FormableTests(_Case):
    def test_tags_whose_definition_lists_the_culture(self):
        rows = {r["tag"]: r for r in vr.formables(self.vs, "alpha", self.mod)}
        self.assertEqual(sorted(rows), ["AAA", "DDD"])
        self.assertEqual(rows["AAA"], {"tag": "AAA", "cultures": ["alpha", "beta", "cm_ab"], "exists_at_start": False,
                                       "use_culture_states": True, "source": "both",
                                       "vanilla_cultures": ["alpha", "beta"]})
        self.assertEqual((rows["DDD"]["source"], rows["DDD"]["use_culture_states"]), ("mod", False))

    def test_a_tag_that_owns_a_state_exists_at_start_and_ccc_is_no_formable(self):
        rows = {r["tag"]: r for r in vr.formables(self.vs, "beta", self.mod)}
        self.assertEqual(sorted(rows), ["AAA", "BBB"])
        self.assertTrue(rows["BBB"]["exists_at_start"])
        self.assertEqual(rows["BBB"]["source"], "vanilla")
        self.assertEqual(vr.formables(self.vs, "gamma", self.mod), [])

    def test_no_culture_lists_every_formable_and_vanilla_alone_works(self):
        self.assertEqual([r["tag"] for r in vr.formables(self.vs, None, self.mod)], ["AAA", "BBB", "DDD"])
        self.assertEqual([r["tag"] for r in vr.formables(self.vs, None, None)], ["AAA", "BBB"])


class LoadTests(_Case):
    def test_no_game_is_said_plainly(self):
        for game in (None, self.install / "nowhere"):
            with self.assertRaisesRegex(vr.NoGame, "no installed game"):
                vr.load(game)

    def test_the_install_is_read_once_until_it_changes(self):
        _tree(self.install, {"launcher/launcher-settings.json": '{"rawVersion": "1.0.0"}'})
        vr._CACHE.clear()
        self.addCleanup(vr._CACHE.clear)
        first = vr.cached(self.game)
        self.assertIs(vr.cached(self.game), first)
        os.utime(self.install / "launcher" / "launcher-settings.json", (1_700_000_000, 1_700_000_000))
        self.assertIsNot(vr.cached(self.game), first)
        self.assertEqual(len(vr._CACHE), 1)


class EndpointTests(_Case):
    def setUp(self):
        super().setUp()
        vr._CACHE.clear()
        self.addCleanup(vr._CACHE.clear)
        self.present = True
        for name, value in (("base_game_path", str(self.install)), ("mod_path", str(self.mod)),
                            ("_vanilla_tree_present", lambda: self.present)):
            p = mock.patch.object(mss, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.handler = object.__new__(mss.ModStateHandler)

    def request(self, path):
        self.handler.path = path
        self.handler._local_request_ok = mock.Mock(return_value=True)
        self.handler._respond_json = mock.Mock()
        self.handler.do_GET()
        args = self.handler._respond_json.call_args.args
        json.dumps(args[0])
        return (args[1] if len(args) > 1 else 200), args[0]

    def test_vanilla_refs(self):
        status, body = self.request("/vanilla-refs/helper_effect?depth=4")
        self.assertEqual((status, body["roots"]["journal_entries"]), (200, ["je_unify"]))
        self.assertEqual(self.request("/vanilla-refs")[0], 400)
        self.assertEqual(self.request("/vanilla-refs/x?depth=two")[0], 400)

    def test_culture_reads(self):
        status, body = self.request("/culture-reads/alpha?as=pop")
        self.assertEqual((status, body["as"], body["count"]), (200, "pop", 1))
        status, body = self.request("/culture-reads/alpha")
        self.assertEqual((body["as"], len(body["reads"])), ("primary", 3))
        self.assertEqual(self.request("/culture-reads/alpha?as=ruler")[0], 400)
        self.assertEqual(self.request("/culture-reads")[0], 400)

    def test_formables(self):
        status, body = self.request("/formables?lists_culture=alpha")
        self.assertEqual((status, [r["tag"] for r in body]), (200, ["AAA", "DDD"]))
        self.assertEqual(len(self.request("/formables")[1]), 3)

    def test_without_the_game_each_says_it_needs_one(self):
        self.present = False
        for path in ("/vanilla-refs/helper_effect", "/culture-reads/alpha", "/formables"):
            status, body = self.request(path)
            self.assertEqual((status, body["error"]), (503, "needs the installed game"), path)
            self.assertIn("culture_merge_primary_reads.json", body["hint"])


def _installed_game():
    try:
        import path_constants
        game = Path(path_constants.base_game_path) / "game"
    except Exception:  # noqa: BLE001 - no paths configured
        return None
    return game if (game / "common" / "country_definitions").is_dir() else None


@unittest.skipUnless(_installed_game() and os.environ.get("VIC3_RUN_VANILLA_TESTS") == "1",
                     "needs the game install and VIC3_RUN_VANILLA_TESTS=1 (reads 3,500 files)")
class InstallTests(unittest.TestCase):
    def test_primary_reads_match_the_culture_merges_committed_scan(self):
        import culture_merge_primary_reads as scan

        inventory = scan.load()
        vs = vr.cached(_installed_game())
        for part in inventory["parts"]:
            mine = {(r["file"], r["entity"]): (r["count"], r["entries"]) for r in vr.culture_reads(vs, part, "primary")}
            theirs = {(r["file"], r["entity"]): (r["count"], r["entries"]) for r in inventory["reads"]
                      if r["part"] == part}
            self.assertEqual(mine, theirs, part)


if __name__ == "__main__":
    unittest.main()
