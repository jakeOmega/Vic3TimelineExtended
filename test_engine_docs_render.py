"""Tests for engine_docs_render — both unit tests for individual renderers
and an integration test for the `render_all` driver that writes every
reference file into a tempdir.
"""
import os
import re
import tempfile
import unittest

from engine_docs_render import (
    _compact_desc,
    _is_regional_iterator,
    _primary_scope,
    render_country_triggers,
    render_modifier_patterns,
    render_modifiers_reference,
    render_summary_event_targets,
    render_summary_modifiers,
    render_summary_on_actions,
    render_summary_triggers_effects,
    render_triggers_effects_reference,
    render_triggers_parsed,
    render_all,
)


class CompactDescTests(unittest.TestCase):
    def test_truncates_at_first_sentence(self):
        s = "First sentence. Second sentence still there."
        self.assertEqual(_compact_desc(s), "First sentence.")

    def test_cuts_inline_usage_example(self):
        s = "Some description some_modifier = value here for example"
        result = _compact_desc(s)
        self.assertNotIn("=", result)

    def test_long_text_is_truncated(self):
        s = "x" * 500
        result = _compact_desc(s, max_len=100)
        self.assertLessEqual(len(result), 100)
        self.assertTrue(result.endswith("..."))

    def test_empty_input(self):
        self.assertEqual(_compact_desc(""), "")


class RegionalIteratorTests(unittest.TestCase):
    def test_matches_regional_patterns(self):
        self.assertTrue(_is_regional_iterator("any_country_in_europe"))
        self.assertTrue(_is_regional_iterator("every_state_in_americas"))
        self.assertTrue(_is_regional_iterator("random_strategic_region_in_india"))

    def test_does_not_match_plain_iterators(self):
        self.assertFalse(_is_regional_iterator("any_country"))
        self.assertFalse(_is_regional_iterator("every_state"))
        self.assertFalse(_is_regional_iterator("any_scope_country"))


class PrimaryScopeTests(unittest.TestCase):
    def test_known_scope_mapped_to_label(self):
        self.assertEqual(_primary_scope("country"), "Country")
        self.assertEqual(_primary_scope("interest_group"), "Interest Group")
        self.assertEqual(_primary_scope("political_movement"), "Political Movement")

    def test_unknown_scope_falls_back_to_titlecase(self):
        self.assertEqual(_primary_scope("some_new_scope"), "Some New Scope")

    def test_none_or_empty_is_global(self):
        self.assertEqual(_primary_scope(None), "Global / Logic")
        self.assertEqual(_primary_scope(""), "Global / Logic")
        self.assertEqual(_primary_scope("none"), "Global / Logic")
        self.assertEqual(_primary_scope([]), "Global / Logic")

    def test_list_input_uses_first_element(self):
        self.assertEqual(_primary_scope(["country", "state"]), "Country")


class TriggersEffectsRenderTests(unittest.TestCase):
    def test_renders_with_iterator_family_and_scope_sections(self):
        triggers = [
            {"name": "any_scope_state", "description": "Iterate states.",
             "scopes": ["country"], "targets": ["state"]},
            {"name": "is_at_war", "description": "Country is at war.",
             "scopes": ["country"], "targets": []},
        ]
        effects = [
            {"name": "every_scope_state", "description": "Iterate states.",
             "scopes": ["country"], "targets": ["state"]},
            {"name": "add_modifier", "description": "Add a modifier.",
             "scopes": ["country", "state"], "targets": []},
        ]
        out = render_triggers_effects_reference(triggers, effects)
        self.assertIn("# Victoria 3", out)
        # Iterator family should appear once with both prefixes.
        self.assertIn("`any/every_scope_state`", out)
        # Plain triggers and effects should appear under per-scope sections.
        self.assertIn("`is_at_war`", out)
        self.assertIn("`add_modifier`", out)
        # Header should mention the source files.
        self.assertIn("Auto-generated from", out.splitlines()[0])

    def test_filters_regional_iterators(self):
        triggers = [
            {"name": "any_country_in_europe", "description": "Regional iter.",
             "scopes": ["none"], "targets": ["country"]},
            {"name": "any_country", "description": "Plain iter.",
             "scopes": ["none"], "targets": ["country"]},
        ]
        out = render_triggers_effects_reference(triggers, [])
        self.assertNotIn("`any/every_country_in_europe`", out)
        self.assertNotIn("any_country_in_europe", out)


class ModifiersRenderTests(unittest.TestCase):
    def test_groups_pattern_members_when_index_provided(self):
        modifiers = [
            {"name": "goods_output_grain_add", "mask": "goods", "display_name": "Grain", "description": "Grain out."},
            {"name": "goods_output_iron_add", "mask": "goods", "display_name": "Iron", "description": "Iron out."},
            {"name": "country_authority_add", "mask": "country", "display_name": "Auth", "description": "Auth."},
        ]
        pattern_index = {
            "goods_output_{good}_add": {
                "grain": modifiers[0],
                "iron": modifiers[1],
            }
        }
        out = render_modifiers_reference(modifiers, pattern_index)
        self.assertIn("## Dynamic Patterns", out)
        self.assertIn("`goods_output_{good}_add`", out)
        # Members listed compactly:
        self.assertIn("`goods_output_grain_add`", out)
        self.assertIn("`goods_output_iron_add`", out)
        # Modifiers covered by pattern do NOT also appear in the per-mask list:
        # only the un-grouped country_authority_add should appear there.
        by_mask_section = out.split("## By Mask", 1)[1]
        self.assertIn("`country_authority_add`", by_mask_section)
        self.assertNotIn("`goods_output_grain_add`", by_mask_section)

    def test_no_pattern_index_lists_everything_under_mask(self):
        modifiers = [
            {"name": "country_authority_add", "mask": "country", "display_name": "", "description": "Auth."},
        ]
        out = render_modifiers_reference(modifiers, None)
        self.assertNotIn("## Dynamic Patterns", out)
        self.assertIn("country_authority_add", out)


class ModifierPatternsRenderTests(unittest.TestCase):
    def test_lists_catalog_and_discovered_with_missing(self):
        catalog = [
            {
                "pattern": "goods_output_{good}_add",
                "placeholder": "good",
                "vocab": "good",
                "notes": "Per-good output additive.",
            }
        ]
        pattern_index = {
            "goods_output_{good}_add": {
                "grain": {"name": "goods_output_grain_add", "mask": "goods"},
            }
        }
        discovered = [
            {
                "pattern": "country_{poptype}_strength_mult",
                "placeholder": "poptype",
                "vocab": "poptype",
                "members": ["clergy", "aristo"],
            }
        ]
        vocabularies = {"good": ["grain", "iron", "wheat"], "poptype": ["clergy", "aristo"]}
        out = render_modifier_patterns(catalog, pattern_index, discovered, vocabularies)
        self.assertIn("## Catalog (1 patterns)", out)
        self.assertIn("Per-good output additive.", out)
        # Missing values list (vocab minus present members):
        self.assertIn("Missing values:", out)
        self.assertIn("`iron`", out)
        self.assertIn("`wheat`", out)
        # Discovered section appears with member preview:
        self.assertIn("## Discovered (not yet in catalog)", out)
        self.assertIn("country_{poptype}_strength_mult", out)


class SummaryRenderTests(unittest.TestCase):
    def test_triggers_effects_summary_pipe_format(self):
        entries = [
            {"name": "is_at_war", "scopes": ["country"], "description": "True if at war."},
        ]
        out = render_summary_triggers_effects(entries)
        self.assertIn("country|is_at_war|True if at war.", out)

    def test_modifiers_summary_pipe_format(self):
        entries = [
            {"name": "country_authority_add", "mask": "country", "description": "Adds authority."},
        ]
        out = render_summary_modifiers(entries)
        self.assertIn("country|country_authority_add|Adds authority.", out)

    def test_event_targets_summary(self):
        entries = [
            {"name": "controller", "input_scopes": ["state"], "output_scopes": ["country"], "description": "scope to controller"},
        ]
        out = render_summary_event_targets(entries)
        self.assertIn("state|controller|country|scope to controller", out)

    def test_on_actions_summary(self):
        entries = [
            {"name": "on_yearly_pulse_country", "scopes": ["country"], "from_code": True},
        ]
        out = render_summary_on_actions(entries)
        self.assertIn("on_yearly_pulse_country|country|from_code=yes", out)

    def test_country_triggers_filter(self):
        entries = [
            {"name": "country_thing", "scopes": ["country"], "description": "Country trigger."},
            {"name": "state_thing", "scopes": ["state"], "description": "State trigger."},
        ]
        out = render_country_triggers(entries)
        self.assertIn("country_thing", out)
        self.assertNotIn("state_thing", out)

    def test_triggers_parsed_full_form(self):
        entries = [
            {"name": "test_trigger", "scopes": ["country"], "targets": ["state"],
             "description": "Detailed description here."},
        ]
        out = render_triggers_parsed(entries)
        self.assertIn("## test_trigger", out)
        self.assertIn("Scopes: country", out)
        self.assertIn("Targets: state", out)
        self.assertIn("Detailed description here.", out)


class RenderAllIntegrationTests(unittest.TestCase):
    """Drives the full pipeline end-to-end with synthetic engine_docs."""

    def setUp(self):
        self.engine_docs = {
            "triggers": [
                {"name": "is_at_war", "scopes": ["country"], "targets": [], "description": "At war."},
                {"name": "any_scope_state", "scopes": ["country"], "targets": ["state"],
                 "description": "Iter states."},
            ],
            "effects": [
                {"name": "add_modifier", "scopes": ["country"], "targets": [], "description": "Add."},
                {"name": "every_scope_state", "scopes": ["country"], "targets": ["state"],
                 "description": "Iter."},
            ],
            "modifiers": [
                {"name": "country_authority_add", "mask": "country", "display_name": "Auth", "description": "Auth."},
                {"name": "goods_output_grain_add", "mask": "goods", "display_name": "Grain", "description": "Grain."},
            ],
            "event-targets": [
                {"name": "controller", "input_scopes": ["state"], "output_scopes": ["country"],
                 "scopes": ["state"], "description": "Controller."},
            ],
            "on-actions": [
                {"name": "on_yearly_pulse_country", "from_code": True, "scopes": ["country"]},
            ],
            "custom-localization": [
                {"name": "GetCountryName", "scopes": ["country"], "random_valid": False, "loc_entries": ["x"]},
            ],
        }
        self.pattern_catalog = [
            {"pattern": "goods_output_{good}_add", "placeholder": "good", "vocab": "good",
             "notes": "Per-good output additive."},
        ]
        self.pattern_index = {
            "goods_output_{good}_add": {"grain": self.engine_docs["modifiers"][1]}
        }
        self.vocabularies = {"good": ["grain", "iron"]}

    def test_writes_all_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = render_all(
                self.engine_docs,
                tmp,
                pattern_catalog=self.pattern_catalog,
                pattern_index=self.pattern_index,
                discovered_patterns=[],
                vocabularies=self.vocabularies,
            )
            files = sorted(os.listdir(tmp))
        expected = {
            "vic3_triggers_effects_reference.md",
            "vic3_modifier_type_definitions_reference.md",
            "triggers_summary.txt",
            "effects_summary.txt",
            "modifiers_summary.txt",
            "event_targets_summary.txt",
            "on_actions_summary.txt",
            "custom_localization_summary.txt",
            "country_triggers.txt",
            "triggers_parsed.txt",
            "modifier_patterns.md",
        }
        self.assertEqual(set(files), expected)
        # All written sizes positive
        for size in written.values():
            self.assertGreater(size, 0)

    def test_files_carry_auto_generated_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_all(
                self.engine_docs,
                tmp,
                pattern_catalog=self.pattern_catalog,
                pattern_index=self.pattern_index,
                vocabularies=self.vocabularies,
            )
            for fname in os.listdir(tmp):
                with open(os.path.join(tmp, fname), "r", encoding="utf-8") as f:
                    head = f.read(400)
                self.assertTrue(
                    "Auto-generated" in head,
                    f"{fname} missing auto-generated header",
                )

    def test_modifier_patterns_omitted_when_no_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_all(self.engine_docs, tmp)  # no catalog → no patterns MD
            self.assertNotIn("modifier_patterns.md", os.listdir(tmp))


if __name__ == "__main__":
    unittest.main()
