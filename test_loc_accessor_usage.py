"""Tests for loc_accessor_usage (#1246): which accessors vanilla chains on a
data type, behind `GET /loc-accessors/<Type>`.

Run: python3 test_loc_accessor_usage.py
"""
import os
import tempfile
import unittest

import localization_accessor_audit as audit
import loc_accessor_usage as lau

CATALOG = {
    "scope_object": {
        "sPoliticalLobby": "political_lobby",
        "gsInterestGroup": "interest_group",
        "GetInterestGroup": "interest_group",
        "sCountry": "country",
    },
    "political_lobby": {
        "GetName": "value",
        "GetMembersDesc": "value",
        "GetCountry": "country",
        "GetTargetCountry": "value",
    },
    "interest_group": {"GetName": "value", "GetCountry": "country"},
    "country": {"GetName": "value", "Self": "country", "GetRuler": "character"},
    "character": {"GetFullName": "value"},
    "state_goods": {"GetName": "value"},
    "hq": {"GetName": "value"},
}

LOC = {
    # An event: SCOPE and ROOT resolve, a lobby is reached by a saved scope.
    "lobby_events.1.d": "[SCOPE.sPoliticalLobby('l').GetName] and "
                        "[SCOPE.sPoliticalLobby('l').GetCountry.GetName]",
    "lobby_events.2.d": "[SCOPE.sPoliticalLobby('l').GetName]",
    # A notification: GetMembersDesc, never used in an event.
    "notification_lobby_created_desc": "[SCOPE.sPoliticalLobby('l').GetMembersDesc]",
    # An ALL-CAPS GUI string with the bare data type, then a nested argument.
    "LOBBY_ENTRY": "[PoliticalLobby.GetName|U] [Concept('lobby','x')] [$VAR$] [concept_lobby]",
    "LOBBY_ROW": "[ObjectsEqual(PoliticalLobby.Self, GetPlayer.Self)]",
    "OTHER_KEY": "plain text, no chain",
    "some_other_key": "[PoliticalLobby.GetTargetCountry.GetName]",
    "ig_event.1.t": "[SCOPE.gsInterestGroup('ig').GetName] [SCOPE.sInterestGroup('ig').GetName]",
}


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(text)


class WalkTests(unittest.TestCase):
    def setUp(self):
        self.aliases = lau._type_aliases(CATALOG)

    def steps(self, text, context="events"):
        chain = audit.extract_chains(text)[0]
        return list(lau.typed_steps(chain.steps, context, CATALOG, self.aliases))

    def test_steps_are_counted_under_their_receiver_type(self):
        self.assertEqual(
            self.steps("[SCOPE.sPoliticalLobby('l').GetCountry.GetName]"),
            [("scope_object", "sPoliticalLobby", True),
             ("political_lobby", "GetCountry", True),
             ("country", "GetName", True)])

    def test_steps_after_a_value_are_unattributed(self):
        self.assertEqual(
            self.steps("[SCOPE.sPoliticalLobby('l').GetTargetCountry.GetName]")[1:],
            [("political_lobby", "GetTargetCountry", True),
             ("unknown", "GetName", False)])

    def test_unknown_first_step_attributes_nothing(self):
        self.assertEqual(self.steps("[Nonsense.GetName]"), [("unknown", "GetName", False)])

    def test_magic_scope_follows_the_context(self):
        self.assertEqual(self.steps("[POLITICAL_LOBBY.GetName]"),
                         [("political_lobby", "GetName", True)])

    def test_camelcase_data_type_falls_back_to_the_catalog(self):
        # `StateGoods` isn't a constructor the audit knows; the catalog has it.
        self.assertEqual(self.steps("[StateGoods.GetName]"),
                         [("state_goods", "GetName", True)])
        # An ALL-CAPS name is a magic scope, never looked up as a data type
        # (`HQ` is no context's magic scope).
        self.assertEqual(self.steps("[HQ.GetName]"), [("unknown", "GetName", False)])
        self.assertEqual(self.steps("[STATE_GOODS.GetName]"),
                         [("market_goods", "GetName", True)])

    def test_nested_argument_chains_are_walked(self):
        self.assertEqual(
            self.steps("[ObjectsEqual(PoliticalLobby.Self, GetPlayer.GetRuler.GetFullName)]"),
            [("political_lobby", "Self", True),
             ("country", "GetRuler", True),
             ("character", "GetFullName", True)])

    def test_string_and_number_arguments_are_skipped(self):
        self.assertEqual(self.steps("[Concept('a.b,c','d')]"), [])
        self.assertEqual(self.steps("[Func(1, -2, 'x', $Y$)]"), [])

    def test_call_args_split_at_depth_zero_outside_quotes(self):
        self.assertEqual(lau._call_args("F(a, G(b, c), 'x,y')"), ["a", "G(b, c)", "'x,y'"])
        self.assertEqual(lau._call_args("GetName"), [])


class ContextTests(unittest.TestCase):
    def test_audit_contexts_pass_through(self):
        self.assertEqual(lau.usage_context("lobby_events.1.d", set()), ("events", "events"))
        self.assertEqual(lau.usage_context("je_x_goal", set())[1], "journal_entries")
        self.assertEqual(lau.usage_context("my_action_desc", {"my_action"})[1],
                         "diplomatic_action_descs")

    def test_permissive_keys_split_by_shape_but_resolve_permissively(self):
        self.assertEqual(lau.usage_context("notification_x_desc", set()),
                         ("permissive", "notification"))
        self.assertEqual(lau.usage_context("IG_TT_LOBBY_ENTRY", set()), ("permissive", "ui"))
        self.assertEqual(lau.usage_context("some_other_key", set()), ("permissive", "other"))


class IndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        _write(cls.tmp.name, "game/gui/panel.gui",
               "# [PoliticalLobby.GetMembersDesc] in a comment\n"
               "text = \"[PoliticalLobby.GetName]\"\n"
               "tooltip = \"[Not(StringIsEmpty(PoliticalLobby.GetMembersDesc))]\"\n")
        _write(cls.tmp.name, "game/gui/sub/other.gui",
               "text = \"[SCOPE.sPoliticalLobby('x').GetName]\"\n")
        cls.index = lau.build_index(LOC, CATALOG,
                                    gui_dirs=[os.path.join(cls.tmp.name, "game", "gui")])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def lookup(self, query="PoliticalLobby", **kw):
        return lau.lookup(self.index, CATALOG, query, **kw)

    def accessors(self, **kw):
        return {a["name"]: a for a in self.lookup(**kw)["accessors"]}

    def test_counts_and_contexts(self):
        got = self.accessors()
        # `lobby_events.1.d` also ends a chain in the country's GetName, which isn't counted.
        self.assertEqual(got["GetName"]["uses"], 5)
        self.assertEqual(got["GetName"]["contexts"],
                         {"events": 2, "gui": 2, "ui": 1})
        self.assertEqual(got["GetMembersDesc"]["contexts"], {"gui": 1, "notification": 1})
        self.assertEqual(got["Self"]["contexts"], {"ui": 1})
        self.assertEqual(got["GetCountry"]["returns"], "country")
        self.assertEqual(got["GetName"]["returns"], "value")

    def test_accessors_are_sorted_by_uses_then_name(self):
        rows = self.lookup()["accessors"]
        self.assertEqual([r["name"] for r in rows],
                         sorted((r["name"] for r in rows),
                                key=lambda n: (-next(r["uses"] for r in rows if r["name"] == n), n)))

    def test_type_spellings_resolve_to_one_type(self):
        for query in ("PoliticalLobby", "political_lobby", "politicallobby", "POLITICAL_LOBBY"):
            with self.subTest(query=query):
                self.assertEqual(self.lookup(query)["type"], "political_lobby")
        self.assertEqual(self.lookup()["name"], "PoliticalLobby")

    def test_unknown_type_is_none_and_suggests(self):
        self.assertIsNone(self.lookup("PoliticalLobbi"))
        self.assertIn("PoliticalLobby", lau.suggest(self.index, CATALOG, "PoliticalLobbi"))
        self.assertIsNone(self.lookup("value"))
        self.assertIsNone(self.lookup(""))

    def test_context_filter(self):
        got = self.accessors(context="events")
        self.assertEqual(sorted(got), ["GetCountry", "GetName"])
        self.assertEqual(got["GetName"]["contexts"], {"events": 2})
        self.assertEqual(self.lookup(context="events")["uses"], 3)
        # A type with uses elsewhere but none in the context is empty, not unknown.
        self.assertEqual(self.lookup("StateGoods", context="events")["accessors"], [])

    def test_min_uses(self):
        self.assertEqual([a["name"] for a in self.lookup(min_uses=5)["accessors"]], ["GetName"])

    def test_scope_accessor_is_the_catalogs_saved_scope_form(self):
        ig = lau.lookup(self.index, CATALOG, "InterestGroup")
        # `sInterestGroup` isn't in the catalog; `GetInterestGroup` reads, not builds.
        self.assertEqual(ig["scope_accessor"], "SCOPE.gsInterestGroup")
        self.assertEqual(ig["scope_accessors"], [{"name": "SCOPE.gsInterestGroup", "uses": 1}])
        self.assertEqual(self.lookup()["scope_accessor"], "SCOPE.sPoliticalLobby")
        self.assertIsNone(self.lookup("StateGoods")["scope_accessor"])

    def test_accessor_unknown_to_the_catalog_has_null_returns(self):
        # Used in LOC on a type the catalog models, but unlisted for it.
        index = lau.build_index({"x.1.d": "[SCOPE.sPoliticalLobby('l').GetNothing]"}, CATALOG)
        row = lau.lookup(index, CATALOG, "political_lobby")["accessors"][0]
        self.assertEqual((row["name"], row["returns"]), ("GetNothing", None))

    def test_examples_come_from_each_context_in_turn(self):
        shown = self.accessors(examples=3)["GetName"]["examples"]
        self.assertEqual(len(shown), 3)
        self.assertEqual({e["context"] for e in shown}, {"events", "gui", "ui"})
        self.assertEqual(self.accessors(examples=0)["GetName"]["examples"], [])
        for e in shown:
            self.assertEqual(set(e), {"context", "source", "expression"})

    def test_examples_name_the_source(self):
        by_ctx = {e["context"]: e for e in self.accessors(examples=9)["GetName"]["examples"]}
        self.assertEqual(by_ctx["ui"]["source"], "LOBBY_ENTRY")
        self.assertEqual(by_ctx["ui"]["expression"], "[PoliticalLobby.GetName|U]")
        self.assertTrue(by_ctx["gui"]["source"].startswith("gui/"))
        self.assertRegex(by_ctx["gui"]["source"], r":\d+$")

    def test_gui_comment_lines_are_skipped(self):
        sources = [e["source"] for e in self.accessors(examples=9)["GetMembersDesc"]["examples"]
                   if e["context"] == "gui"]
        self.assertEqual(len(sources), 1)
        self.assertTrue(sources[0].endswith("panel.gui:3"))

    def test_coverage_and_listing(self):
        self.assertTrue(self.lookup()["gui_scanned"])
        self.assertEqual(self.index.coverage["gui_files"], 2)
        self.assertEqual(self.index.coverage["loc_keys"], len(LOC))
        listing = lau.list_types(self.index)
        names = {r["name"] for r in listing["types"]}
        self.assertLessEqual({"PoliticalLobby", "Country", "ScopeObject"}, names)
        self.assertNotIn("Value", names)
        self.assertNotIn("Unknown", names)
        self.assertIn("gui", listing["contexts"])
        uses = [r["uses"] for r in listing["types"]]
        self.assertEqual(uses, sorted(uses, reverse=True))

    def test_without_game_gui_is_reported_unscanned(self):
        index = lau.build_index(LOC, CATALOG, gui_dirs=["/nonexistent/gui"])
        self.assertFalse(lau.lookup(index, CATALOG, "PoliticalLobby")["gui_scanned"])
        self.assertNotIn("gui", lau.list_types(index)["contexts"])


class SnapshotTests(unittest.TestCase):
    """The committed vanilla snapshot, which CI has. Asserts only facts that
    don't move with a vanilla patch."""

    @classmethod
    def setUpClass(cls):
        from path_constants import mod_path
        cls.catalog = audit._load_engine_catalog(os.path.join(mod_path, "docs", "engine"))
        cls.index = lau.build_index(lau.load_snapshot_loc(), cls.catalog)

    def test_political_lobby_members_desc_is_notification_only(self):
        # The question #1245 needed answered.
        row = next(a for a in lau.lookup(self.index, self.catalog, "PoliticalLobby")["accessors"]
                   if a["name"] == "GetMembersDesc")
        self.assertGreater(row["uses"], 0)
        self.assertIn("notification", row["contexts"])
        self.assertNotIn("events", row["contexts"])

    def test_interest_group_scope_accessor_is_gs(self):
        got = lau.lookup(self.index, self.catalog, "InterestGroup")
        self.assertEqual(got["scope_accessor"], "SCOPE.gsInterestGroup")
        self.assertNotIn("sInterestGroup", self.index.types["scope_object"])

    def test_country_is_the_most_chained_type(self):
        types = lau.list_types(self.index)["types"]
        self.assertEqual(types[0]["type"], "country")


if __name__ == "__main__":
    unittest.main()
