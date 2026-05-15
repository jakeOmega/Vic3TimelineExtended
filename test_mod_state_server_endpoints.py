"""Tests for the mod_state_server endpoints added to close issues #35–#38:

- #35: `Country Formation` entity registration (assertion against module globals).
- #38: `_loc_keys_for` pure helper covering the LOC_KEY_FAMILIES seed set.
- #37: `_diplomatic_actions` summary logic — exercised against the live server
       via HTTP if it's up, skipped otherwise (90s cold-start makes spinning a
       fresh ModState per test too expensive; the helpers are pure-Python and
       reachable through the existing service).
- #36: `_build_gui_render_index` pure function over a tempdir of hand-written
       `.gui` files — covers both the loc-attr scan and the [DataType.Method]
       walker without needing real game files.

Pattern mirrors test_engine_docs_server.py (direct module import, no HTTP
spin-up required for the pure paths).
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

import mod_state_server as mss


SERVER = "http://127.0.0.1:8950"


def _server_up() -> bool:
    try:
        urlopen(f"{SERVER}/status", timeout=2)
        return True
    except (URLError, OSError):
        return False


def _get(path: str):
    with urlopen(f"{SERVER}{path}", timeout=10) as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# #35 — Country Formation entity registration
# ---------------------------------------------------------------------------
class CountryFormationRegistryTests(unittest.TestCase):
    def test_registered_in_base_game_paths(self):
        self.assertIn("Country Formation", mss.base_game_paths)
        self.assertTrue(mss.base_game_paths["Country Formation"].endswith("country_formation"))

    def test_registered_in_mod_paths(self):
        self.assertIn("Country Formation", mss.mod_paths)
        self.assertTrue(mss.mod_paths["Country Formation"].endswith("country_formation"))

    @unittest.skipUnless(_server_up(), "mod_state_server not running")
    def test_raw_endpoint_returns_AFU(self):
        data = _get("/raw/" + quote("Country Formation") + "/AFU")
        # Shape is ['=', {...}] post-serialize. Inner dict has is_major_formation.
        self.assertIsInstance(data, list)
        self.assertEqual(data[0], "=")
        inner = data[1]
        self.assertEqual(inner["is_major_formation"], ["=", "yes"])
        self.assertEqual(inner["unification_play"], ["=", "dp_unify_african_union"])


# ---------------------------------------------------------------------------
# #38 — loc-key family helper (pure, no ms dependency)
# ---------------------------------------------------------------------------
class LocKeysFamilyTests(unittest.TestCase):
    def test_treaty_article_family(self):
        loc = {
            "money_transfer": "Money Transfer",
            "money_transfer_desc": "",
            "money_transfer_effects_desc": "• transfers cash",
            # article_short_desc intentionally absent
        }
        result = mss._loc_keys_for("Treaty Articles", "money_transfer", loc)
        self.assertEqual(result["type"], "Treaty Articles")
        self.assertEqual(result["id"], "money_transfer")
        keys = result["keys"]
        self.assertTrue(keys["name"]["found"])
        self.assertEqual(keys["name"]["value"], "Money Transfer")
        # empty-but-defined: found=True, value=""
        self.assertTrue(keys["desc"]["found"])
        self.assertEqual(keys["desc"]["value"], "")
        # absent: found=False
        self.assertFalse(keys["article_short_desc"]["found"])
        # present with content
        self.assertTrue(keys["effects_desc"]["found"])

    def test_unknown_entity_type_returns_error(self):
        result = mss._loc_keys_for("Bogus Type", "foo", {})
        self.assertIn("error", result)
        self.assertIn("Treaty Articles", result["known_types"])

    def test_journal_entries_family_size(self):
        # JE family currently has 4 suffixes (name/desc/reason/goal).
        family = mss.LOC_KEY_FAMILIES["Journal Entries"]
        self.assertEqual(len(family), 4)
        roles = {r for r, _ in family}
        self.assertSetEqual(roles, {"name", "desc", "reason", "goal"})

    @unittest.skipUnless(_server_up(), "mod_state_server not running")
    def test_treaty_articles_loc_keys_via_http(self):
        data = _get("/loc-keys/" + quote("Treaty Articles") + "/money_transfer")
        self.assertEqual(data["type"], "Treaty Articles")
        # money_transfer_effects_desc is non-empty in vanilla — robust signal.
        self.assertTrue(data["keys"]["effects_desc"]["found"])

    @unittest.skipUnless(_server_up(), "mod_state_server not running")
    def test_treaty_articles_sub_route(self):
        data = _get("/treaty-articles/money_transfer/loc-keys")
        self.assertEqual(data["type"], "Treaty Articles")
        self.assertEqual(data["id"], "money_transfer")


# ---------------------------------------------------------------------------
# #37 — diplomatic-actions catalog (live-server tests only)
# ---------------------------------------------------------------------------
@unittest.skipUnless(_server_up(), "mod_state_server not running")
class DiplomaticActionsCatalogTests(unittest.TestCase):
    def test_list_returns_many_entries(self):
        data = _get("/diplomatic-actions")
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 40)  # vanilla has ~60+
        ids = {e["id"] for e in data}
        self.assertIn("increase_relations", ids)
        self.assertIn("puppet", ids)

    def test_general_action_category(self):
        data = _get("/diplomatic-actions/increase_relations")
        self.assertEqual(data["category"], "general")
        self.assertIn("general", data["groups"])
        self.assertFalse(data["is_subject_relation"])

    def test_subject_action_flagged_via_subject_type(self):
        data = _get("/diplomatic-actions/puppet")
        # puppet's groups field says "general" but its pact.subject_type
        # makes it a subject relation — verify the heuristic catches it.
        self.assertTrue(data["is_subject_relation"])
        self.assertEqual(data["category"], "subject_relation")
        self.assertEqual(data["subject_type"], "subject_type_puppet")

    def test_detail_includes_pact_block(self):
        data = _get("/diplomatic-actions/increase_relations")
        self.assertIn("pact", data)
        self.assertIn("raw", data)


# ---------------------------------------------------------------------------
# #36 — GUI render-site index over a tempdir of hand-written .gui files
# ---------------------------------------------------------------------------
class GuiRenderIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vic3_gui_test_")
        gui_a = os.path.join(cls.tmp, "panel_a.gui")
        gui_b = os.path.join(cls.tmp, "panel_b.gui")
        # Two GUI files exercising:
        #  - text = "<key>"   (direct loc ref)
        #  - tooltip = "<key>" (loc ref via another attr)
        #  - [Article.GetName] (entity-method walker)
        #  - [Article.GetNameNoFormatting] (variant)
        #  - text = "Some literal." (NOT a key — has space + period; must be ignored)
        with open(gui_a, "w") as f:
            f.write(
                'widget = {\n'
                '\tname = "my_widget"\n'
                '\ttext = "money_transfer_desc"\n'
                '\ttooltip = "concept_binding_period_desc"\n'
                '}\n'
            )
        with open(gui_b, "w") as f:
            f.write(
                'widget = {\n'
                '\ttext = "[Article.GetNameNoFormatting]"\n'
                '\tdescription = "[Article.GetDesc]"\n'
                '\traw_text = "Some literal."\n'  # should be ignored (non-id value)
                '}\n'
            )
        cls.index = mss._build_gui_render_index([(cls.tmp, cls.tmp)])

    def test_loc_key_indexed(self):
        sites = self.index["by_key"].get("money_transfer_desc")
        self.assertIsNotNone(sites)
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0]["attr"], "text")
        self.assertEqual(sites[0]["file"], "panel_a.gui")

    def test_tooltip_attr_indexed(self):
        sites = self.index["by_key"].get("concept_binding_period_desc")
        self.assertIsNotNone(sites)
        self.assertEqual(sites[0]["attr"], "tooltip")

    def test_literal_string_not_indexed(self):
        # "Some literal." is not a loc key (has spaces/punctuation) -> ignored.
        self.assertNotIn("Some literal.", self.index["by_key"])
        # Also the attr `name = "my_widget"` is in loc-attrs? No, "name" is NOT
        # in _GUI_LOC_ATTRS (widget names are not loc refs). Verify.
        self.assertNotIn("my_widget", self.index["by_key"])

    def test_datatype_method_indexed(self):
        article_getname = self.index["by_method"].get(("Article", "GetNameNoFormatting"))
        self.assertIsNotNone(article_getname)
        self.assertEqual(len(article_getname), 1)
        self.assertEqual(article_getname[0]["file"], "panel_b.gui")

        article_getdesc = self.index["by_method"].get(("Article", "GetDesc"))
        self.assertIsNotNone(article_getdesc)

    def test_nested_dataref_indexed(self):
        # Vanilla pattern: `visible = "[Not(StringIsEmpty(Article.GetX))]"`
        # The DataType.Method ref is buried inside two function calls.
        nested = os.path.join(self.tmp, "nested.gui")
        with open(nested, "w") as f:
            f.write(
                'widget = {\n'
                '\tvisible = "[Not(StringIsEmpty(Article.GetEffectsDesc))]"\n'
                '}\n'
            )
        index = mss._build_gui_render_index([(self.tmp, self.tmp)])
        hits = index["by_method"].get(("Article", "GetEffectsDesc"))
        self.assertIsNotNone(hits, "regex must traverse nested [Foo(Bar(Type.Method))]")
        self.assertEqual(hits[0]["file"], "nested.gui")


@unittest.skipUnless(_server_up(), "mod_state_server not running")
class GuiRenderEndpointsTests(unittest.TestCase):
    def test_render_sites_endpoint(self):
        data = _get("/gui/render-sites/concept_binding_period_desc")
        # The mod's treaty_panel.gui (or similar) references this tooltip.
        self.assertIn("sites", data)
        # At least some site must reference it.
        self.assertGreaterEqual(data["count"], 1)

    def test_render_paths_treaty_article_name(self):
        data = _get("/gui/render-paths/" + quote("Treaty Articles") + "?field=name")
        self.assertEqual(data["entity_type"], "Treaty Articles")
        self.assertEqual(data["datatype"], "Article")
        # Vanilla custom_tooltip.gui renders [Article.GetNameNoFormatting] —
        # so we expect at least one site.
        self.assertGreaterEqual(data["count"], 1)
        self.assertIn("GetNameNoFormatting", data["methods_matched"])

    def test_render_paths_unknown_type(self):
        data = _get("/gui/render-paths/" + quote("Bogus") + "?field=name")
        self.assertIn("error", data)
        self.assertIn("Treaty Articles", data["supported_entity_types"])


if __name__ == "__main__":
    unittest.main()
