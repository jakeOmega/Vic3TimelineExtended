"""Unit tests for the modifier pattern catalog + auto-discovery (§3) and the
mod-vs-engine modifier classifier (§4) in mod_state_server.

These tests don't require a running server. They exercise the pure helpers
directly, monkey-patching module globals where the tested function reads from
them.
"""
import os
import tempfile
import unittest

import mod_state_server as srv


def _engine_entry(name, mask="country", description=""):
    return {"name": name, "mask": mask, "display_name": "", "description": description}


class CompilePatternTests(unittest.TestCase):
    def test_basic_split(self):
        self.assertEqual(
            srv._compile_pattern("goods_output_{good}_add"),
            ("goods_output_", "good", "_add"),
        )

    def test_suffix_only(self):
        self.assertEqual(
            srv._compile_pattern("{good}_mult"),
            ("", "good", "_mult"),
        )

    def test_prefix_only(self):
        self.assertEqual(
            srv._compile_pattern("country_institution_impact_{institution}"),
            ("country_institution_impact_", "institution", ""),
        )

    def test_no_placeholder_returns_none(self):
        self.assertIsNone(srv._compile_pattern("no_placeholder_here"))


class MatchPatternTests(unittest.TestCase):
    def test_match_in_middle(self):
        captured = srv._match_pattern("goods_output_grain_add", "goods_output_", "_add")
        self.assertEqual(captured, "grain")

    def test_no_match_wrong_prefix(self):
        self.assertIsNone(srv._match_pattern("country_grain_add", "goods_output_", "_add"))

    def test_no_match_wrong_suffix(self):
        self.assertIsNone(srv._match_pattern("goods_output_grain_mult", "goods_output_", "_add"))

    def test_empty_capture_rejected(self):
        # Captured value cannot be empty.
        self.assertIsNone(srv._match_pattern("goods_output__add", "goods_output_", "_add"))


class VocabStripPrefixTests(unittest.TestCase):
    def test_building_ids_emit_both_forms(self):
        # Force the disk fallback to return a known set, then confirm vocab
        # values include both `building_textile_mills` and `textile_mills`
        # so catalog matching against modifier names works either way.
        original = srv._vocab_disk_cache.copy()
        srv._vocab_disk_cache.clear()
        srv._vocab_disk_cache["building"] = ["building_textile_mills", "building_solar_collector"]
        try:
            # ms is None at module import time before _load_mod_state runs;
            # _vocabulary_values falls through to the cache.
            srv.ms = None
            values = srv._vocabulary_values("building")
        finally:
            srv._vocab_disk_cache.clear()
            srv._vocab_disk_cache.update(original)
        self.assertIn("building_textile_mills", values)
        self.assertIn("textile_mills", values)
        self.assertIn("solar_collector", values)


class BuildPatternIndexesTests(unittest.TestCase):
    def test_catalog_match_with_vocab(self):
        catalog = [
            {
                "pattern": "goods_output_{good}_add",
                "placeholder": "good",
                "vocab": "good",
            }
        ]
        engine = [
            _engine_entry("goods_output_grain_add"),
            _engine_entry("goods_output_iron_add"),
            _engine_entry("country_authority_add"),  # unrelated; should not match
        ]
        vocabularies = {"good": ["grain", "iron", "wheat"]}
        index, m_to_p, discovered = srv._build_pattern_indexes(engine, catalog, vocabularies)
        self.assertIn("goods_output_{good}_add", index)
        self.assertEqual(set(index["goods_output_{good}_add"].keys()), {"grain", "iron"})
        self.assertEqual(m_to_p["goods_output_grain_add"][0], "goods_output_{good}_add")
        self.assertEqual(m_to_p["goods_output_grain_add"][2], "catalog")
        # `country_authority_add` does not match the pattern, stays unmatched.
        self.assertNotIn("country_authority_add", m_to_p)

    def test_catalog_rejects_value_not_in_vocab(self):
        catalog = [
            {
                "pattern": "goods_output_{good}_add",
                "placeholder": "good",
                "vocab": "good",
            }
        ]
        engine = [_engine_entry("goods_output_madeup_add")]
        vocabularies = {"good": ["grain", "iron"]}
        index, _m_to_p, _disc = srv._build_pattern_indexes(engine, catalog, vocabularies)
        # `madeup` is not in the vocab so the catalog pass should not register it.
        self.assertNotIn("madeup", index.get("goods_output_{good}_add", {}))

    def test_discovery_below_threshold_is_skipped(self):
        # Two members sharing a derived pattern is below DISCOVERY_MIN_MEMBERS=3
        # so it should NOT be auto-promoted.
        engine = [
            _engine_entry("country_foo_add"),
            _engine_entry("country_bar_add"),
        ]
        vocabularies = {"poptype": ["foo", "bar"]}
        index, m_to_p, discovered = srv._build_pattern_indexes(engine, [], vocabularies)
        self.assertEqual(discovered, [])

    def test_discovery_at_threshold_creates_pattern(self):
        engine = [
            _engine_entry("country_foo_add"),
            _engine_entry("country_bar_add"),
            _engine_entry("country_baz_add"),
        ]
        vocabularies = {"poptype": ["foo", "bar", "baz"]}
        index, m_to_p, discovered = srv._build_pattern_indexes(engine, [], vocabularies)
        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered[0]["pattern"], "country_{poptype}_add")
        self.assertEqual(set(discovered[0]["members"]), {"foo", "bar", "baz"})

    def test_discovery_skips_short_vocab_values(self):
        # Vocab values shorter than 3 chars are excluded so we don't collapse
        # `country_X_Y_add` into `country_{x}_Y_add` for every short XX.
        engine = [
            _engine_entry("country_a_add"),
            _engine_entry("country_b_add"),
            _engine_entry("country_c_add"),
        ]
        vocabularies = {"poptype": ["a", "b", "c"]}
        _idx, _m, discovered = srv._build_pattern_indexes(engine, [], vocabularies)
        self.assertEqual(discovered, [])


class _DefinitionsOnly:
    """The ModState surface `_classify_modifier_name` reads: the modifier type
    definitions, vanilla's and the mod's."""

    def __init__(self, modifier_types):
        self._types = modifier_types

    def get_data(self, entity_type):
        return self._types if entity_type == "Modifier Types" else {}


class ClassifyModifierNameTests(unittest.TestCase):
    def setUp(self):
        # A name is valid only when a definition registers it (#391). The
        # definitions come from the loaded ModState; `modifiers_set` is every
        # name the caller knows of, the engine-docs dump included.
        self.modifiers_set = {"country_authority_add", "country_listed_only_add"}
        # pattern_pairs shape: (pattern_str, prefix, suffix, vocab_set, placeholder)
        self.pattern_pairs = [
            (
                "goods_output_{good}_add",
                "goods_output_",
                "_add",
                {"grain", "iron"},
                "good",
            )
        ]
        self._saved_ms = srv.ms
        srv.ms = _DefinitionsOnly({"country_authority_add": {}, "goods_output_iron_add": {}})
        # Reset modifier_to_pattern so leftover state from prior tests doesn't leak.
        self._saved_mtp = srv.modifier_to_pattern
        srv.modifier_to_pattern = {}

    def tearDown(self):
        srv.modifier_to_pattern = self._saved_mtp
        srv.ms = self._saved_ms

    def test_engine_set_classification(self):
        status, info = srv._classify_modifier_name(
            "country_authority_add", self.modifiers_set, self.pattern_pairs
        )
        self.assertEqual(status, "engine")

    def test_name_only_the_engine_docs_list_is_unknown(self):
        # `modifiers.log` lists every name the engine could register; a dump
        # older than the game also lists names a patch removed.
        status, info = srv._classify_modifier_name(
            "country_listed_only_add", self.modifiers_set, self.pattern_pairs
        )
        self.assertEqual(status, "unknown")
        self.assertEqual(info, {"listed_in_engine_docs": True})

    def test_registered_pattern_instance_is_engine(self):
        status, info = srv._classify_modifier_name(
            "goods_output_iron_add", self.modifiers_set, self.pattern_pairs
        )
        self.assertEqual((status, info), ("engine", {}))

    def test_pattern_runtime_match_needs_a_definition(self):
        # `goods_output_grain_add` matches the pattern AND `grain` is in the
        # vocab, but no definition registers it: the engine ignores it, so the
        # classifier reports it with the pattern it would belong to.
        status, info = srv._classify_modifier_name(
            "goods_output_grain_add", self.modifiers_set, self.pattern_pairs
        )
        self.assertEqual(status, "unknown")
        self.assertEqual(info["pattern"], "goods_output_{good}_add")
        self.assertEqual(info["value"], "grain")
        self.assertIs(info["unregistered_pattern_instance"], True)
        self.assertNotIn("listed_in_engine_docs", info)

    def test_suspicious_classification(self):
        # `goods_output_grane_add` matches the pattern shape but `grane` is not
        # in the vocab — likely typo, status "suspicious".
        status, info = srv._classify_modifier_name(
            "goods_output_grane_add", self.modifiers_set, self.pattern_pairs
        )
        self.assertEqual(status, "suspicious")
        self.assertIn("grain", info["vocab_did_you_mean"])

    def test_unknown_classification(self):
        status, info = srv._classify_modifier_name(
            "totally_made_up_modifier_add", self.modifiers_set, self.pattern_pairs
        )
        self.assertEqual(status, "unknown")
        self.assertEqual(info, {})

    def test_modifier_to_pattern_short_circuit(self):
        srv.modifier_to_pattern["country_authority_add"] = (
            "country_{whatever}_add",
            "authority",
            "catalog",
        )
        # A definition registers the name, so engine wins (modifier_to_pattern
        # is the second-priority lookup).
        status, _ = srv._classify_modifier_name(
            "country_authority_add", self.modifiers_set, self.pattern_pairs
        )
        self.assertEqual(status, "engine")

        # A name with no definition that the engine docs file under a pattern
        # is still unregistered; the cached lookup supplies the pattern.
        srv.modifier_to_pattern["custom_modifier_add"] = (
            "custom_{x}_add", "modifier", "catalog",
        )
        status, info = srv._classify_modifier_name(
            "custom_modifier_add", self.modifiers_set | {"custom_modifier_add"}, self.pattern_pairs
        )
        self.assertEqual(status, "unknown")
        self.assertEqual(info["pattern"], "custom_{x}_add")
        self.assertIs(info["unregistered_pattern_instance"], True)
        self.assertIs(info["listed_in_engine_docs"], True)

    def test_nothing_is_registered_without_a_mod_state(self):
        srv.ms = None
        status, _ = srv._classify_modifier_name(
            "country_authority_add", self.modifiers_set, self.pattern_pairs
        )
        self.assertEqual(status, "unknown")


class DidYouMeanTests(unittest.TestCase):
    def test_substring_match_ranks_first(self):
        result = srv._did_you_mean("grain", {"grain", "iron", "tools"})
        self.assertEqual(result[0], "grain")

    def test_partial_match(self):
        result = srv._did_you_mean("grane", {"grain", "iron"})
        self.assertIn("grain", result)

    def test_empty_vocab(self):
        self.assertEqual(srv._did_you_mean("anything", set()), [])

    def test_limit(self):
        vocab = {f"item_{i}" for i in range(20)}
        self.assertLessEqual(len(srv._did_you_mean("item", vocab, limit=3)), 3)


class DiskVocabularyScanTests(unittest.TestCase):
    def test_extracts_top_level_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "00_test.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    "north_german = {\n"
                    "    color = rgb { 62 77 100 }\n"
                    "    religion = protestant\n"
                    "}\n"
                    "anglo_saxon= {\n"
                    "    color = rgb { 100 100 200 }\n"
                    "}\n"
                )
            keys = srv._disk_vocabulary_scan([tmp])
        self.assertIn("north_german", keys)
        self.assertIn("anglo_saxon", keys)

    def test_skips_indented_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "00_test.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    "outer = {\n"
                    "    inner = {\n"
                    "        x = 1\n"
                    "    }\n"
                    "}\n"
                )
            keys = srv._disk_vocabulary_scan([tmp])
        self.assertEqual(keys, ["outer"])

    def test_missing_dir_returns_empty(self):
        self.assertEqual(srv._disk_vocabulary_scan(["/nonexistent/dir"]), [])


if __name__ == "__main__":
    unittest.main()
