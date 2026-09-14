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


def _get(path: str, timeout: int = 10):
    with urlopen(f"{SERVER}{path}", timeout=timeout) as resp:
        return json.loads(resp.read())


def _post(path: str):
    from urllib.request import Request
    req = Request(f"{SERVER}{path}", method="POST", data=b"")
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _server_has_new_code() -> bool:
    """True only if the running server exposes the #227/#229 additions (the
    `versions` block in /status). HTTP tests for the new endpoints skip cleanly
    when the server is still on pre-restart code — the orchestrator restart then
    activates them — so they never spuriously fail against stale code."""
    if not _server_up():
        return False
    try:
        st = _get("/status")
        return isinstance(st, dict) and "versions" in st
    except (URLError, OSError, ValueError):
        return False


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

    def test_scan_file_for_calls_skips_file_with_no_callable(self):
        # The #293 prefilter: a file that never writes `<helper> =` is rejected
        # before the line scan. Must not change what the scan finds.
        from collections import defaultdict
        with tempfile.TemporaryDirectory() as td:
            fp = os.path.join(td, "ev.txt")
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write("vanilla.1 = {\n\timmediate = {\n"
                         "\t\tadd_modifier = { name = x }\n\t}\n}\n")
            index: dict = defaultdict(list)
            mss._scan_file_for_calls(
                fp, "events/ev.txt", "vanilla",
                frozenset({"te_helper_that_is_absent"}), index)
            self.assertEqual(dict(index), {})

    @unittest.skipUnless(_server_up(), "mod_state_server not running")
    def test_scripted_effect_detail_has_callers(self):
        listing = _get("/scripted-effects")
        withp = [e for e in listing if e.get("parameters")]
        self.assertTrue(withp)
        # The callers index is warmed in the background after each (re)load, but
        # a request that races that warm still pays the full mod+vanilla scan —
        # more than the default 10 s. Don't call a cold build a failure (#293).
        d = _get("/scripted-effects/" + withp[0]["id"], timeout=60)
        self.assertIn("callers", d)
        self.assertIn("parameters", d)
        self.assertIn("raw", d)

    @unittest.skipUnless(_server_has_new_code(), "server lacks #288 endpoint")
    def test_scripted_helpers_unresolved(self):
        d = _get("/scripted-helpers/unresolved", timeout=60)
        self.assertIn("unresolved_helper_calls", d)
        self.assertEqual(d["count"], len(d["unresolved_helper_calls"]))
        self.assertFalse(d["include_reviewed"])
        for row in d["unresolved_helper_calls"]:
            self.assertEqual(set(row) >= {"name", "file", "line", "kind"}, True)

    def test_reload_during_index_build_does_not_cache_stale_index(self):
        # A warm thread that started before a reload must not overwrite the
        # freshly-invalidated cache with its pre-reload scan (#293).
        saved_build = mss._build_call_index
        saved_cache, saved_gen = mss._call_index_cache, mss._call_index_generation
        try:
            mss._call_index_cache = None

            def _build_then_reload():
                mss._invalidate_call_index()     # a reload lands mid-scan
                return {"stale": []}

            mss._build_call_index = _build_then_reload
            self.assertEqual(mss._get_call_index(), {"stale": []})
            self.assertIsNone(mss._call_index_cache)
        finally:
            mss._build_call_index = saved_build
            mss._call_index_cache = saved_cache
            mss._call_index_generation = saved_gen

    @unittest.skipUnless(_server_up(), "mod_state_server not running")
    def test_status_reports_call_index_readiness(self):
        st = _get("/status")
        if "call_index_ready" not in st:
            self.skipTest("server predates #293")
        self.assertIsInstance(st["call_index_ready"], bool)


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


# ---------------------------------------------------------------------------
# #227 — version-aware /status (pure helpers; no server needed)
# ---------------------------------------------------------------------------
class VersionStatusHelperTests(unittest.TestCase):
    def test_version_from_text_extracts_last(self):
        self.assertEqual(mss._version_from_text("1.13.9 (Matcha)"), "1.13.9")
        self.assertEqual(
            mss._version_from_text("/home/x/Modding-Digests/1.13.9/docs"), "1.13.9")
        self.assertEqual(mss._version_from_text("1.13"), "1.13")
        self.assertIsNone(mss._version_from_text(""))
        self.assertIsNone(mss._version_from_text(None))
        self.assertIsNone(mss._version_from_text("mod_loaded"))

    def test_versions_mismatch(self):
        self.assertFalse(mss._versions_mismatch("1.13.9", "1.13.9", "1.13.9"))
        self.assertTrue(mss._versions_mismatch("1.13.9", "1.13.8", "1.13.9"))
        self.assertFalse(mss._versions_mismatch("1.13.9", None, None))
        self.assertFalse(mss._versions_mismatch(None, None, None))

    def test_read_live_game_version_type(self):
        v = mss._read_live_game_version()
        self.assertTrue(v is None or isinstance(v, str))

    def test_repo_head_info_has_subject_and_preserves_date(self):
        rh = mss._load_vanilla_repo_head_info()
        if not rh:
            self.skipTest("vanilla source mirror not present")
        # Additive keys.
        self.assertIn("subject", rh)
        self.assertIn("version", rh)
        # Pre-existing keys the staleness check depends on are intact and the
        # subject didn't bleed into date_iso (the %ai%n%s parse trap).
        self.assertIn("sha", rh)
        self.assertIsInstance(rh["date_unix"], int)
        self.assertNotIn(rh.get("subject") or "\0", rh["date_iso"])

    def test_compute_version_status_shape(self):
        vs = mss._compute_version_status()
        for k in ("live_game", "vanilla_clone_head", "engine_docs_source", "mismatch"):
            self.assertIn(k, vs)
        self.assertIsInstance(vs["mismatch"], bool)


# ---------------------------------------------------------------------------
# #229 — entity-type resolver (pure; no server needed)
# ---------------------------------------------------------------------------
class EntityTypeResolverTests(unittest.TestCase):
    KNOWN = ["Amendments", "Buildings", "Cultures", "Law Groups", "Laws",
             "PMs", "PM Groups", "Technologies", "Country Formation",
             "Ship Name Definitions", "Treaty Articles"]

    def _r(self, s):
        return mss._resolve_entity_type(s, self.KNOWN)

    def test_exact_and_case_insensitive(self):
        self.assertEqual(self._r("Laws"), "Laws")
        self.assertEqual(self._r("laws"), "Laws")
        self.assertEqual(self._r("LAWS"), "Laws")

    def test_singular_plural_trailing_s(self):
        self.assertEqual(self._r("Building"), "Buildings")
        self.assertEqual(self._r("culture"), "Cultures")
        self.assertEqual(self._r("PM"), "PMs")

    def test_ies_to_y(self):
        self.assertEqual(self._r("Technology"), "Technologies")
        self.assertEqual(self._r("technologies"), "Technologies")

    def test_multi_word(self):
        self.assertEqual(self._r("Law Group"), "Law Groups")
        self.assertEqual(self._r("law group"), "Law Groups")
        self.assertEqual(self._r("pm group"), "PM Groups")
        self.assertEqual(self._r("Ship Name Definition"), "Ship Name Definitions")

    def test_singular_key_plural_query(self):
        self.assertEqual(self._r("Country Formations"), "Country Formation")
        self.assertEqual(self._r("country formation"), "Country Formation")

    def test_miss_returns_none(self):
        self.assertIsNone(self._r("Bogus Type"))
        self.assertIsNone(self._r("xyz"))


# ---------------------------------------------------------------------------
# /tech-unlocks record copy must isolate the cached index from ?annotate=
# ---------------------------------------------------------------------------
class TechUnlocksRecordCopyTests(unittest.TestCase):
    def test_annotating_copy_leaves_cached_entries_untouched(self):
        cached = {
            "by_type": {"PMs": [{"type": "PMs", "id": "pm_x"}]},
            "summary": {"PMs": 1},
            "n_total": 1,
        }
        copied = mss.ModStateHandler._copy_unlocks_record(cached)
        # Stand-in for annotators.annotate_entries, which does e.update(extra).
        copied["by_type"]["PMs"][0]["flag"] = "OK"
        self.assertNotIn("flag", cached["by_type"]["PMs"][0])


# ---------------------------------------------------------------------------
# #227 / #229 — HTTP surfaces (skip until the server is restarted on new code)
# ---------------------------------------------------------------------------
class VersionAwareStatusHTTPTests(unittest.TestCase):
    @unittest.skipUnless(_server_has_new_code(), "requires restarted server (#227/#229)")
    def test_status_has_versions_block(self):
        st = _get("/status")
        v = st["versions"]
        for k in ("live_game", "vanilla_clone_head", "engine_docs_source", "mismatch"):
            self.assertIn(k, v)
        self.assertIn("last_reload", st)


class EntityTypesEndpointHTTPTests(unittest.TestCase):
    @unittest.skipUnless(_server_has_new_code(), "requires restarted server (#227/#229)")
    def test_wrapped_by_default(self):
        d = _get("/entity-types")
        self.assertIsInstance(d, dict)
        self.assertIn("entity_types", d)
        self.assertIn("Laws", d["entity_types"])

    @unittest.skipUnless(_server_has_new_code(), "requires restarted server (#227/#229)")
    def test_bare_flag_returns_list(self):
        d = _get("/entity-types?bare=true")
        self.assertIsInstance(d, list)
        self.assertIn("Laws", d)


class RawResolverHTTPTests(unittest.TestCase):
    @unittest.skipUnless(_server_has_new_code(), "requires restarted server (#227/#229)")
    def test_case_insensitive_type_resolves(self):
        # `laws` (lowercase) and `Law` (singular) resolve to the canonical `Laws`
        # and return the identical raw dict.
        canonical = _get("/raw/Laws")
        self.assertIsInstance(canonical, dict)
        self.assertEqual(_get("/raw/laws"), canonical)
        self.assertEqual(_get("/raw/Law"), canonical)

    @unittest.skipUnless(_server_has_new_code(), "requires restarted server (#227/#229)")
    def test_unknown_type_returns_did_you_mean(self):
        from urllib.error import HTTPError
        try:
            d = _get("/raw/Bogus%20Type")
        except HTTPError as e:
            d = json.loads(e.read())
        self.assertIn("did_you_mean", d)
        self.assertIsInstance(d["did_you_mean"], list)


class ValidateRegistriesHTTPTests(unittest.TestCase):
    @unittest.skipUnless(_server_has_new_code(), "requires restarted server (#227/#229)")
    def test_validate_registries_shape(self):
        d = _post("/validate/registries")
        self.assertEqual(d["status"], "validated")
        self.assertIn("warning_count", d)
        self.assertIsInstance(d["warnings"], list)
        for w in d["warnings"]:
            self.assertEqual(set(w.keys()), {"label", "detail"})



# ---------------------------------------------------------------------------
# #254 — server hardening: local-origin gate, path containment, honest statuses
#
# All pure-Python: the handler is driven directly (no live server) except the
# LocalOriginGateHTTPTests class, which binds an ephemeral loopback port so the
# gate is exercised against what urllib really puts on the wire.
# ---------------------------------------------------------------------------
import io
import logging
import threading
import types
from http.server import ThreadingHTTPServer
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request

import mod_state_client


class _StubModState:
    """Minimal ModState stand-in for handler-level tests."""

    def __init__(self, data=None, localization=None):
        self._data = data or {}
        self.localization = localization or {}
        self.mod_parsers = {}
        self.base_parsers = {}
        self.parse_failures = []

    def get_data(self, etype):
        return self._data.get(etype)

    def localize(self, key):
        return self.localization.get(key, key)

    def get_description(self, key):
        return None

    def unlocalize(self, text):
        return [k for k, v in self.localization.items() if text.lower() in str(v).lower()]

    def search_localization(self, query, limit=50):
        return []


class _CapturingHandler(mss.ModStateHandler):
    """A ModStateHandler that never touches a socket: __init__ is bypassed and
    `_respond_json` records instead of writing."""

    def __init__(self, path="/status", headers=None, port=8950, body=None):
        self.path = path
        self.headers = headers if headers is not None else {"Host": f"127.0.0.1:{port}"}
        self.server = types.SimpleNamespace(server_port=port)
        self.responses = []
        self.routed = []

    def _respond_json(self, data, status=200):
        self.responses.append((status, data))

    @property
    def last(self):
        return self.responses[-1]


class LocalRequestRejectionTests(unittest.TestCase):
    """The pure Host/Origin predicate (#254 §1)."""

    def test_accepts_what_curl_urllib_and_requests_send(self):
        for host in ("127.0.0.1:8950", "localhost:8950", "[::1]:8950",
                     "LOCALHOST:8950", "127.0.0.1", "localhost", "[::1]", "::1"):
            with self.subTest(host=host):
                self.assertIsNone(mss._local_request_rejection(host, None, 8950))

    def test_accepts_own_origin(self):
        for origin in ("http://127.0.0.1:8950", "http://localhost:8950",
                       "http://[::1]:8950"):
            with self.subTest(origin=origin):
                self.assertIsNone(
                    mss._local_request_rejection("localhost:8950", origin, 8950))

    def test_rejects_foreign_host_dns_rebinding(self):
        reason = mss._local_request_rejection("evil.example.com:8950", None, 8950)
        self.assertIsNotNone(reason)
        self.assertIn("evil.example.com", reason)

    def test_rejects_host_for_a_different_port(self):
        reason = mss._local_request_rejection("localhost:9999", None, 8950)
        self.assertIn("bind port", reason)

    def test_rejects_missing_host(self):
        self.assertEqual(mss._local_request_rejection(None, None, 8950),
                         "missing Host header")

    def test_rejects_cross_site_origin(self):
        reason = mss._local_request_rejection(
            "localhost:8950", "https://evil.example.com", 8950)
        self.assertIn("Origin", reason)

    def test_rejects_null_origin(self):
        reason = mss._local_request_rejection("localhost:8950", "null", 8950)
        self.assertIn("Origin", reason)

    def test_rejects_origin_on_another_port(self):
        self.assertIsNotNone(
            mss._local_request_rejection("localhost:8950", "http://localhost:3000", 8950))

    def test_port_is_read_from_the_bound_server(self):
        # Same header, different bind port: allowed on 9001, refused on 8950.
        self.assertIsNone(mss._local_request_rejection("localhost:9001", None, 9001))
        self.assertIsNotNone(mss._local_request_rejection("localhost:9001", None, 8950))


class LocalOriginGateHandlerTests(unittest.TestCase):
    """do_GET / do_POST refuse before doing any work (#254 §1)."""

    def test_do_get_rejects_foreign_host_without_routing(self):
        h = _CapturingHandler("/status", headers={"Host": "evil.example.com"})
        with mock.patch.object(mss.ModStateHandler, "route",
                               side_effect=AssertionError("route must not run")):
            with self.assertLogs(mss.logger, level="WARNING") as cap:
                h.do_GET()
        status, body = h.last
        self.assertEqual(status, 403)
        self.assertIn("Forbidden", body["error"])
        self.assertTrue(any("evil.example.com" in line for line in cap.output))

    def test_do_get_allows_loopback_host(self):
        h = _CapturingHandler("/status", headers={"Host": "localhost:8950"})
        with mock.patch.object(mss.ModStateHandler, "route", return_value={"ok": True}):
            h.do_GET()
        self.assertEqual(h.last, (200, {"ok": True}))

    def test_do_post_reload_rejects_cross_site_origin_without_reloading(self):
        h = _CapturingHandler(
            "/reload",
            headers={"Host": "localhost:8950", "Origin": "http://evil.example.com"},
        )
        with mock.patch.object(mss, "_load_mod_state",
                               side_effect=AssertionError("reload must not run")):
            with self.assertLogs(mss.logger, level="WARNING") as cap:
                h.do_POST()
        status, body = h.last
        self.assertEqual(status, 403)
        self.assertIn("Origin", body["error"])
        self.assertTrue(any("evil.example.com" in line for line in cap.output))

    def test_do_post_rejects_foreign_host(self):
        h = _CapturingHandler("/reload", headers={"Host": "attacker.test:8950"})
        with mock.patch.object(mss, "_load_mod_state",
                               side_effect=AssertionError("reload must not run")):
            with self.assertLogs(mss.logger, level="WARNING"):
                h.do_POST()
        self.assertEqual(h.last[0], 403)


def _can_bind_loopback() -> bool:
    import socket
    try:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.close()
        return True
    except OSError:
        return False


class _GateTestHandler(mss.ModStateHandler):
    """Real handler over a real socket, with the data-dependent routing stubbed."""

    def route(self, parts, params):
        return {"ok": True, "parts": parts}

    def log_message(self, *args, **kwargs):
        pass


@unittest.skipUnless(_can_bind_loopback(), "cannot bind a loopback socket here")
class LocalOriginGateHTTPTests(unittest.TestCase):
    """End-to-end on an ephemeral port — proves the gate reads the real bind
    port (never the hardcoded 8950) and that a plain urllib/curl request passes."""

    def setUp(self):
        # The gate logs every rejection at WARNING; keep the deliberate ones
        # out of the test run's console output.
        previous = mss.logger.level
        mss.logger.setLevel(logging.CRITICAL + 1)
        self.addCleanup(mss.logger.setLevel, previous)

    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _GateTestHandler)
        cls.port = cls.httpd.server_port
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def _url(self, path="/status"):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_default_urllib_request_passes(self):
        with urlopen(self._url(), timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            self.assertTrue(json.loads(resp.read())["ok"])

    def test_curl_style_localhost_host_passes(self):
        req = Request(self._url(), headers={"Host": f"localhost:{self.port}"})
        with urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)

    def test_rebound_host_header_is_rejected(self):
        req = Request(self._url(), headers={"Host": "evil.example.com"})
        with self.assertRaises(HTTPError) as ctx:
            urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 403)

    def test_browser_origin_is_rejected(self):
        req = Request(self._url(), headers={"Origin": "https://evil.example.com"})
        with self.assertRaises(HTTPError) as ctx:
            urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 403)
        self.assertIn("error", json.loads(ctx.exception.read()))

    def test_post_reload_from_a_page_is_rejected_before_reloading(self):
        req = Request(
            self._url("/reload"), method="POST", data=b"",
            headers={"Origin": "https://evil.example.com"},
        )
        with mock.patch.object(mss, "_load_mod_state",
                               side_effect=AssertionError("reload must not run")):
            with self.assertRaises(HTTPError) as ctx:
                urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 403)


class EventBalanceFileParamTests(unittest.TestCase):
    """?file= must stay inside the mod tree (#254 §2)."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "events"))
        self.rel = "events/sample_events.txt"
        with open(os.path.join(self.root, self.rel), "w", encoding="utf-8") as f:
            f.write(
                "namespace = sample\n"
                "sample.1 = { type = country_event option = { name = sample.1.a } }\n"
            )
        patcher = mock.patch.object(mss, "mod_path", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_relative_path_inside_the_mod_resolves(self):
        resolved = mss._resolve_mod_relative_path(self.rel)
        self.assertEqual(resolved, os.path.join(os.path.realpath(self.root), self.rel))
        self.assertEqual(mss._event_ids_from_mod_file(self.rel), ["sample.1"])

    def test_absolute_path_is_rejected(self):
        with self.assertRaises(mss.BadRequest) as ctx:
            mss._resolve_mod_relative_path("/etc/passwd")
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("absolute", ctx.exception.payload["error"])

    def test_dotdot_escape_is_rejected(self):
        for attempt in ("../../etc/passwd", "events/../../../etc/passwd", ".."):
            with self.subTest(attempt=attempt):
                with self.assertRaises(mss.BadRequest) as ctx:
                    mss._resolve_mod_relative_path(attempt)
                self.assertEqual(ctx.exception.status, 400)

    def test_dotdot_that_stays_inside_is_allowed(self):
        self.assertEqual(
            mss._resolve_mod_relative_path("events/../" + self.rel),
            os.path.join(os.path.realpath(self.root), self.rel),
        )

    def test_symlink_out_of_the_mod_tree_is_rejected(self):
        target = tempfile.mkdtemp()
        link = os.path.join(self.root, "escape")
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(mss.BadRequest):
            mss._resolve_mod_relative_path("escape/secret.txt")

    def test_embedded_nul_byte_is_400_not_500(self):
        # `?file=x%00y` reaches the handler as a real NUL; os.path.realpath
        # raises ValueError on it, which used to escape as a 500 + traceback.
        with self.assertRaises(mss.BadRequest) as ctx:
            mss._resolve_mod_relative_path("events/foo\x00.txt")
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("NUL", ctx.exception.payload["error"])

    def test_nul_byte_through_the_handler_is_400(self):
        handler = _CapturingHandler("/event-balance?file=events/foo%00.txt")
        stub = _StubModState({"Events": {"sample.1": ("=", {})}})
        with mock.patch.object(mss, "ms", stub):
            with self.assertRaises(mss.BadRequest) as ctx:
                mss.ModStateHandler._event_balance(
                    handler, [], {"file": ["events/foo\x00.txt"]})
        self.assertEqual(ctx.exception.status, 400)

    def test_missing_but_contained_file_is_404(self):
        with self.assertRaises(mss._EndpointError) as ctx:
            mss._event_ids_from_mod_file("events/no_such_file.txt")
        self.assertEqual(ctx.exception.status, 404)

    def test_handler_rejects_traversal_with_400(self):
        handler = _CapturingHandler()
        stub = _StubModState({"Events": {"sample.1": ("=", {})}})
        with mock.patch.object(mss, "ms", stub):
            with self.assertRaises(mss.BadRequest) as ctx:
                mss.ModStateHandler._event_balance(
                    handler, [], {"file": ["../../../etc/passwd"]})
        self.assertEqual(ctx.exception.status, 400)

    def test_issues_handler_rejects_traversal_with_400(self):
        handler = _CapturingHandler()
        stub = _StubModState({"Events": {"sample.1": ("=", {})}})
        with mock.patch.object(mss, "ms", stub):
            with self.assertRaises(mss.BadRequest) as ctx:
                mss.ModStateHandler._event_balance_issues(
                    handler, {"file": ["/etc/passwd"]}, "json")
        self.assertEqual(ctx.exception.status, 400)


class NotFoundVsKeyErrorTests(unittest.TestCase):
    """Only deliberate misses are 404; a real KeyError is a 500 (#254 §3)."""

    def test_notfound_payload_matches_the_pre_change_body(self):
        exc = mss.NotFound("law_nope")
        self.assertEqual(exc.status, 404)
        self.assertEqual(exc.payload["error"], "Not found: 'law_nope'")
        self.assertIn("hint", exc.payload)

    def test_do_get_maps_notfound_to_404(self):
        h = _CapturingHandler("/laws/law_nope")
        with mock.patch.object(mss.ModStateHandler, "route",
                               side_effect=mss.NotFound("law_nope")):
            h.do_GET()
        status, body = h.last
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "Not found: 'law_nope'")

    def test_do_get_maps_a_genuine_keyerror_to_500(self):
        h = _CapturingHandler("/tech-unlocks/x")
        with mock.patch.object(mss.ModStateHandler, "route",
                               side_effect=KeyError("by_type")):
            with self.assertLogs(mss.logger, level="ERROR"):
                h.do_GET()
        status, body = h.last
        self.assertEqual(status, 500)
        self.assertEqual(body["error"], "KeyError: 'by_type'")

    def test_unknown_endpoint_is_still_404(self):
        h = _CapturingHandler("/no-such-endpoint")
        h.do_GET()
        self.assertEqual(h.last[0], 404)

    def test_missing_entity_lookups_raise_notfound(self):
        stub = _StubModState({
            "Laws": {"law_monarchy": ("=", {})},
            "Events": {"ev.1": ("=", {})},
            "Technologies": {"tech_a": ("=", {})},
            "On Actions": {"oa_a": ("=", {})},
        })
        handler = _CapturingHandler()
        with mock.patch.object(mss, "ms", stub):
            for method, args in (
                (mss.ModStateHandler._laws, (["law_nope"],)),
                (mss.ModStateHandler._events, (["ev.nope"], {})),
                (mss.ModStateHandler._tech_tree, (["tech_nope"],)),
                (mss.ModStateHandler._on_actions, (["oa_nope"],)),
            ):
                with self.subTest(method=method.__name__):
                    with self.assertRaises(mss.NotFound):
                        method(handler, *args)

    def test_engine_docs_usage_hint_is_400_not_404(self):
        handler = _CapturingHandler()
        with mock.patch.object(mss, "engine_docs", {"effects": []}):
            with self.assertRaises(mss.BadRequest) as ctx:
                mss.ModStateHandler._engine_docs(handler, ["origin"], {})
            self.assertIn("Usage:", ctx.exception.payload["error"])
            with self.assertRaises(mss.BadRequest):
                mss.ModStateHandler._engine_docs(handler, ["usage"], {})

    def test_unknown_engine_doc_type_is_404(self):
        handler = _CapturingHandler()
        with mock.patch.object(mss, "engine_docs", {"effects": []}):
            with self.assertRaises(mss.NotFound):
                mss.ModStateHandler._engine_docs(handler, ["bogus"], {})


class ErrorBodyStatusTests(unittest.TestCase):
    """`{"error": ...}` bodies no longer come back with HTTP 200 (#254 §4)."""

    def setUp(self):
        self.handler = _CapturingHandler()

    def test_missing_query_param_is_400_and_keeps_the_body_shape(self):
        with mock.patch.object(mss, "ms", _StubModState()):
            with self.assertRaises(mss.BadRequest) as ctx:
                mss.ModStateHandler._search(self.handler, {})
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("error", ctx.exception.payload)
        self.assertEqual(ctx.exception.payload["error"], "Provide ?q=search_term")

    def test_unloaded_collection_is_503(self):
        with mock.patch.object(mss, "ms", _StubModState()):
            for method, args in (
                (mss.ModStateHandler._laws, ([],)),
                (mss.ModStateHandler._events, ([], {})),
                (mss.ModStateHandler._decrees, ([],)),
            ):
                with self.subTest(method=method.__name__):
                    with self.assertRaises(mss._ServiceNotReady) as ctx:
                        method(self.handler, *args)
                    self.assertEqual(ctx.exception.status, 503)
                    self.assertIn("data not loaded", ctx.exception.payload["error"])

    def test_service_not_ready_reaches_the_wire_as_503(self):
        h = _CapturingHandler("/laws")
        with mock.patch.object(mss, "ms", _StubModState()):
            h.do_GET()
        status, body = h.last
        self.assertEqual(status, 503)
        self.assertEqual(body["error"], "Laws data not loaded")

    def test_bad_request_reaches_the_wire_as_400(self):
        h = _CapturingHandler("/search")
        with mock.patch.object(mss, "ms", _StubModState()):
            h.do_GET()
        self.assertEqual(h.last[0], 400)
        self.assertIn("error", h.last[1])

    def test_event_balance_without_a_selector_is_400(self):
        stub = _StubModState({"Events": {"ev.1": ("=", {})}})
        with mock.patch.object(mss, "ms", stub):
            with self.assertRaises(mss.BadRequest):
                mss.ModStateHandler._event_balance(self.handler, [], {})

    def test_logs_diff_without_a_backup_generation_is_404(self):
        info = types.SimpleNamespace(
            family="debug", generation=0, path="/nonexistent/debug.log",
            to_dict=lambda: {"family": "debug"},
        )
        with mock.patch("game_log_reader.list_logs", return_value=[info]):
            with self.assertRaises(mss._EndpointError) as ctx:
                mss.ModStateHandler._logs(self.handler, ["debug", "diff"], {})
        self.assertEqual(ctx.exception.status, 404)
        self.assertIn("to diff against", ctx.exception.payload["error"])

    def test_loc_keys_usage_is_400_and_unknown_type_is_404(self):
        with mock.patch.object(mss, "ms", _StubModState()):
            with self.assertRaises(mss.BadRequest):
                mss.ModStateHandler._loc_keys(self.handler, ["Laws"])
            with self.assertRaises(mss._EndpointError) as ctx:
                mss.ModStateHandler._loc_keys(self.handler, ["Bogus Type", "x"])
        self.assertEqual(ctx.exception.status, 404)
        self.assertIn("known_types", ctx.exception.payload)

    def test_gui_usage_errors_are_400(self):
        with self.assertRaises(mss.BadRequest):
            mss.ModStateHandler._gui(self.handler, [], {})

    def test_modifier_grants_without_a_name_is_400(self):
        with self.assertRaises(mss.BadRequest):
            mss.ModStateHandler._modifier_grants(self.handler, [], {})

    def test_modifier_grants_with_a_malformed_name_is_400(self):
        with self.assertRaises(mss._EndpointError) as ctx:
            mss.ModStateHandler._modifier_grants(self.handler, ["Not A Modifier!"], {})
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("Invalid target name", ctx.exception.payload["error"])
        # The finder's body shape survives the status change.
        self.assertEqual(ctx.exception.payload["grants"], [])
        self.assertEqual(ctx.exception.payload["name"], "Not A Modifier!")


class UnlocalizeFormTests(unittest.TestCase):
    """/help must describe the form the handler implements (#254 §7)."""

    def test_help_documents_the_path_form_and_mentions_q(self):
        entries = mss.ModStateHandler._help(_CapturingHandler())["get"]
        row = next(e for e in entries if e["path"].startswith("/unlocalize/"))
        self.assertEqual(row["path"], "/unlocalize/<text>")
        self.assertIn("?q=", row["desc"])

    def test_help_documents_the_local_only_gate(self):
        help_body = mss.ModStateHandler._help(_CapturingHandler())
        self.assertIn("403", help_body["access"])

    def test_handler_accepts_both_forms(self):
        stub = _StubModState(localization={"law_monarchy": "Monarchy"})
        handler = _CapturingHandler()
        with mock.patch.object(mss, "ms", stub):
            by_path = mss.ModStateHandler._unlocalize(handler, ["Monarchy"], {})
            by_query = mss.ModStateHandler._unlocalize(handler, [], {"q": ["Monarchy"]})
        self.assertEqual(by_path, by_query)
        self.assertEqual(by_path["keys"], ["law_monarchy"])

    def test_no_text_is_400(self):
        handler = _CapturingHandler()
        with mock.patch.object(mss, "ms", _StubModState()):
            with self.assertRaises(mss.BadRequest):
                mss.ModStateHandler._unlocalize(handler, [], {})


class ClientErrorReportingTests(unittest.TestCase):
    """mod_state_client prints the status + body instead of "not running" (#254 §5)."""

    def _http_error(self, code, body):
        return HTTPError(
            "http://127.0.0.1:8950/laws", code, "Service Unavailable",
            {}, io.BytesIO(body),
        )

    def test_http_error_prints_status_and_body(self):
        err = self._http_error(503, b'{"error": "Laws data not loaded"}')
        stderr = io.StringIO()
        with mock.patch.object(mod_state_client, "urlopen", side_effect=err),                 mock.patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit) as ctx:
                mod_state_client.query("laws")
        self.assertEqual(ctx.exception.code, 1)
        out = stderr.getvalue()
        self.assertIn("HTTP 503", out)
        self.assertIn("Laws data not loaded", out)
        self.assertNotIn("not running", out)

    def test_connection_error_keeps_the_not_running_message(self):
        from urllib.error import URLError as _URLError
        stderr = io.StringIO()
        with mock.patch.object(mod_state_client, "urlopen",
                               side_effect=_URLError("Connection refused")),                 mock.patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit) as ctx:
                mod_state_client.query("laws")
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("not running", stderr.getvalue())

    def test_non_json_error_body_is_still_printed(self):
        err = self._http_error(403, b"Forbidden: non-local Host header")
        stderr = io.StringIO()
        with mock.patch.object(mod_state_client, "urlopen", side_effect=err),                 mock.patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit):
                mod_state_client.query("status")
        self.assertIn("non-local Host header", stderr.getvalue())



if __name__ == "__main__":
    unittest.main()
