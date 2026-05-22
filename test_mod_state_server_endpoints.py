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


# ---------------------------------------------------------------------------
# #128 — reverse modifier-grant lookup (_scan_file_for_grants /
#        _grant_block_label / _find_modifier_grants). Pure file-scan helpers,
#        exercised over hand-written tempfiles; live lookup gated behind import.
# ---------------------------------------------------------------------------
class ModifierGrantBlockLabelTests(unittest.TestCase):
    def test_direct_mode_depth_one(self):
        self.assertEqual(mss._grant_block_label(["base_values"], "direct"), "direct")
        self.assertIsNone(mss._grant_block_label(["base_values", "modifier"], "direct"))

    def test_wrapped_known_bag(self):
        self.assertEqual(mss._grant_block_label(["law_x", "modifier"], "wrapped"), "modifier")
        self.assertEqual(
            mss._grant_block_label(["p_x", "member_modifier"], "wrapped"), "member_modifier")

    def test_wrapped_rejects_non_bag(self):
        # possible/ai_weight blocks are not modifier bags.
        self.assertIsNone(mss._grant_block_label(["law_x", "possible"], "wrapped"))
        self.assertIsNone(mss._grant_block_label(["law_x"], "wrapped"))

    def test_wrapped_scaling_wrapper_nested(self):
        self.assertEqual(
            mss._grant_block_label(["b", "construction_modifier", "workforce_scaled"], "wrapped"),
            "construction_modifier/workforce_scaled",
        )


class ModifierGrantScanTests(unittest.TestCase):
    def _scan(self, body, entity_type="Laws", mode="wrapped", target="target_mod"):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f.txt")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(body)
            return list(mss._scan_file_for_grants(
                p, "common/x/f.txt", entity_type, mode, "mod", target))

    def test_law_modifier_block(self):
        out = self._scan(
            "law_x = {\n\tmodifier = {\n\t\ttarget_mod = 0.5\n\t}\n}\n")
        self.assertEqual(len(out), 1)
        g = out[0]
        self.assertEqual(g["entity_id"], "law_x")
        self.assertEqual(g["block"], "modifier")
        self.assertEqual(g["value"], 0.5)
        self.assertEqual(g["line"], 3)

    def test_static_modifier_direct_with_inject_prefix(self):
        out = self._scan(
            "INJECT:base_values = {\n\tother = 1\n\ttarget_mod = 0.6\n}\n",
            entity_type="Modifiers", mode="direct")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["entity_id"], "base_values")  # prefix stripped
        self.assertEqual(out[0]["block"], "direct")
        self.assertEqual(out[0]["value"], 0.6)

    def test_principle_two_tiers_and_other_block(self):
        body = (
            "p_x = {\n"
            "\tmember_modifier = {\n\t\ttarget_mod = 0.2\n\t}\n"
            "\tmember_modifier = {\n\t\ttarget_mod = 0.4\n\t}\n"
            "\tinstitution_modifier = {\n\t\ttarget_mod = 0.1\n\t}\n"
            "}\n")
        out = self._scan(body, entity_type="Principles")
        self.assertEqual(len(out), 3)
        self.assertEqual([g["block"] for g in out],
                         ["member_modifier", "member_modifier", "institution_modifier"])
        self.assertEqual([g["value"] for g in out], [0.2, 0.4, 0.1])

    def test_rejects_nested_non_modifier_scopes(self):
        body = (
            "p_x = {\n"
            "\tpossible = {\n\t\ttarget_mod = 5\n\t}\n"
            "\tai_weight = {\n\t\ttarget_mod = 9\n\t}\n"
            "\tmodifier = {\n\t\ttarget_mod = 0.3\n\t}\n"
            "}\n")
        out = self._scan(body)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["value"], 0.3)
        self.assertEqual(out[0]["block"], "modifier")

    def test_whole_word_match_not_substring(self):
        out = self._scan(
            "law_x = {\n\tmodifier = {\n\t\ttarget_mod_extra = 1\n\t}\n}\n")
        self.assertEqual(out, [])

    def test_boolean_value(self):
        out = self._scan(
            "law_x = {\n\tmodifier = {\n\t\ttarget_mod = yes\n\t}\n}\n")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["value"], "yes")

    def test_target_none_captures_all_keys(self):
        out = self._scan(
            "law_x = {\n\tmodifier = {\n\t\ta_add = 1\n\t\tb_mult = 2\n\t}\n}\n",
            target=None)
        self.assertEqual(len(out), 2)

    def test_trailing_comment_stripped(self):
        out = self._scan(
            "law_x = {\n\tmodifier = {\n\t\ttarget_mod = 0.5 # note\n\t}\n}\n")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["value"], 0.5)


class ModifierGrantLookupTests(unittest.TestCase):
    """Live import-level test against the real mod tree (no server needed)."""
    def test_invalid_identifier(self):
        r = mss._find_modifier_grants("Not Valid")
        self.assertIn("error", r)
        self.assertEqual(r["grants"], [])

    def test_bad_scope(self):
        r = mss._find_modifier_grants("state_assimilation_mult", scope="bogus")
        self.assertIn("error", r)

    def test_empty_result(self):
        r = mss._find_modifier_grants("phantom_modifier_does_not_exist_xyz")
        self.assertEqual(r["returned"], 0)

    @unittest.skipUnless(os.path.isdir(mss._MOD_COMMON), "mod common/ not found")
    def test_homeland_modifier_grants_from_mod(self):
        r = mss._find_modifier_grants(
            "state_homeland_creation_threshold_add", scope="mod", limit=300)
        self.assertGreater(r["returned"], 0)
        types = {g["entity_type"] for g in r["grants"]}
        # Mod's homelands system grants this from laws + the base_values static.
        self.assertIn("Laws", types)
        self.assertIn("Modifiers", types)
        for g in r["grants"]:
            self.assertTrue(g["file"] and g["line"] >= 1)
            self.assertIn("block", g)
            self.assertEqual(g["origin"], "mod")

    @unittest.skipUnless(os.path.isdir(mss._MOD_COMMON), "mod common/ not found")
    def test_limit_truncates(self):
        r = mss._find_modifier_grants(
            "state_homeland_creation_threshold_add", scope="mod", limit=2)
        self.assertEqual(r["returned"], 2)
        self.assertTrue(r["truncated"])


# ---------------------------------------------------------------------------
# #131 — Principles / Amendments registration + structured endpoints
# ---------------------------------------------------------------------------
class PrinciplesAmendmentsRegistryTests(unittest.TestCase):
    def test_registered_in_both_path_dicts(self):
        for et, sub in (
            ("Principles", "power_bloc_principles"),
            ("Principle Groups", "power_bloc_principle_groups"),
            ("Amendments", "amendments"),
        ):
            self.assertIn(et, mss.base_game_paths)
            self.assertIn(et, mss.mod_paths)
            self.assertTrue(mss.base_game_paths[et].endswith(sub))
            self.assertTrue(mss.mod_paths[et].endswith(sub))

    @unittest.skipUnless(_server_up(), "mod_state_server not running")
    def test_principle_detail_has_modifier_blocks(self):
        d = _get("/principles/principle_food_standardization_2")
        self.assertEqual(d["type"], "Principles")
        self.assertIn("modifier_blocks", d)
        blocks = {b["block"] for b in d["modifier_blocks"]}
        self.assertIn("member_modifier", blocks)
        self.assertIn("group_levels", d)  # reverse-looked-up from Principle Groups

    @unittest.skipUnless(_server_up(), "mod_state_server not running")
    def test_amendment_detail_resolves_parent_and_modifiers(self):
        d = _get("/amendments/amendment_geheime_staatskonferenz_metternich")
        self.assertEqual(d["parent"]["id"], "law_autocracy")
        self.assertIn("country_legitimacy_base_add", d["modifiers"])
        self.assertEqual(d["allowed_laws"][0]["id"], "law_autocracy")


# ---------------------------------------------------------------------------
# #132 — scripted-effects / scripted-triggers caller index
# ---------------------------------------------------------------------------
class ScriptedHelperEndpointTests(unittest.TestCase):
    def test_extract_parameters_finds_placeholders(self):
        raw = ("=", {"add_modifier": ("=", {"name": ("=", "$GOOD$_mod")}),
                     "x_$RANK$_add": ("=", "$RANK$")})
        self.assertEqual(mss._extract_parameters(raw), ["GOOD", "RANK"])

    def test_caller_type_classification(self):
        self.assertEqual(mss._caller_type("events/foo_events.txt"), "Events")
        self.assertEqual(
            mss._caller_type("common/scripted_effects/x.txt"), "Scripted Effects")
        self.assertEqual(
            mss._caller_type("common/on_actions/x.txt"), "On Actions")

    def test_scan_file_for_calls_captures_args(self):
        from collections import defaultdict
        with tempfile.TemporaryDirectory() as td:
            fp = os.path.join(td, "ev.txt")
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write(
                    "homeland.3 = {\n"
                    "\timmediate = {\n"
                    "\t\tte_apply_homeland_deltas = {\n"
                    "\t\t\tGOOD = grain\n"
                    "\t\t\tRANK = 2\n"
                    "\t\t}\n"
                    "\t\tsome_trigger = yes\n"
                    "\t}\n"
                    "}\n"
                )
            index: dict = defaultdict(list)
            callables = frozenset({"te_apply_homeland_deltas", "some_trigger"})
            mss._scan_file_for_calls(fp, "events/ev.txt", "mod", callables, index)
            self.assertEqual(len(index["te_apply_homeland_deltas"]), 1)
            rec = index["te_apply_homeland_deltas"][0]
            self.assertEqual(rec["id"], "homeland.3")
            self.assertEqual(rec["line"], 3)
            self.assertEqual(rec["args"], {"GOOD": "grain", "RANK": 2})
            self.assertEqual(len(index["some_trigger"]), 1)
            self.assertEqual(index["some_trigger"][0]["args"], {})

    @unittest.skipUnless(_server_up(), "mod_state_server not running")
    def test_scripted_effect_detail_has_callers(self):
        listing = _get("/scripted-effects")
        withp = [e for e in listing if e.get("parameters")]
        self.assertTrue(withp)
        d = _get("/scripted-effects/" + withp[0]["id"])
        self.assertIn("callers", d)
        self.assertIn("parameters", d)
        self.assertIn("raw", d)


# ---------------------------------------------------------------------------
# #133 — mod-vs-vanilla diff
# ---------------------------------------------------------------------------
class DiffEndpointTests(unittest.TestCase):
    def test_diff_entity_fields_flattens_and_keeps_both_sides(self):
        # Operates on raw parser data: dict values are ('=', value) tuples.
        vanilla = {"modifier": ("=", {"a_mult": ("=", "0.1"),
                                      "b_add": ("=", "5")})}
        mod = {"modifier": ("=", {"a_mult": ("=", "0.2"),
                                  "c_add": ("=", "3")})}
        added, removed, changed = mss._diff_entity_fields(vanilla, mod)
        self.assertEqual(added, {"modifier.c_add": "3"})
        self.assertEqual(removed, {"modifier.b_add": "5"})
        self.assertEqual(
            changed, {"modifier.a_mult": {"vanilla": "0.1", "mod": "0.2"}})

    def test_diff_entity_fields_mod_only_all_added(self):
        added, removed, changed = mss._diff_entity_fields(
            {}, {"type": ("=", "country_event"), "hidden": ("=", "yes")})
        self.assertEqual(set(added), {"type", "hidden"})
        self.assertEqual(removed, {})
        self.assertEqual(changed, {})

    def test_paradox_text_renders_nested_block(self):
        text = mss._paradox_text(
            "x", ("=", {"modifier": ("=", {"a_mult": ("=", "0.1")})}))
        self.assertIn("x = {", text)
        self.assertIn("\tmodifier = {", text)
        self.assertIn("\t\ta_mult = 0.1", text)

    @unittest.skipUnless(_server_up(), "mod_state_server not running")
    def test_diff_replaced_principle(self):
        d = _get("/diff/Principles/principle_food_standardization_2")
        self.assertTrue(d["in_vanilla"])
        self.assertIn("added", d)
        self.assertIn("removed", d)
        self.assertIn("changed", d)


if __name__ == "__main__":
    unittest.main()
