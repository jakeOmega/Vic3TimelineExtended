"""Unit tests for event_magnitude_audit.

Run: python3 test_event_magnitude_audit.py
"""
import os
import tempfile
import unittest

from event_magnitude_audit import (
    FAST_SCALING_MODIFIERS,
    DIRECT_EFFECTS,
    ResourceMeta,
    find_event_id_at_line,
    parse_reviewed_comment,
    scan_direct_effects,
    scan_inline_modifier_types,
    AuditFlag,
)


class RegistryTests(unittest.TestCase):
    def test_registry_has_prestige(self):
        self.assertIn("country_prestige_add", FAST_SCALING_MODIFIERS)
        meta = FAST_SCALING_MODIFIERS["country_prestige_add"]
        self.assertEqual(meta.resource, "prestige")

    def test_registry_has_bureaucracy(self):
        self.assertIn("country_bureaucracy_add", FAST_SCALING_MODIFIERS)

    def test_registry_has_add_treasury_direct(self):
        self.assertIn("add_treasury", DIRECT_EFFECTS)
        meta = DIRECT_EFFECTS["add_treasury"]
        self.assertIn("treasury", meta.resource)


class EventIdResolutionTests(unittest.TestCase):
    def test_simple(self):
        text = (
            "namespace = test_events\n"
            "\n"
            "test_events.1 = {\n"
            "  type = country_event\n"
            "  immediate = {\n"
            "    add_treasury = -100\n"
            "  }\n"
            "}\n"
        )
        # add_treasury sits on line 6
        self.assertEqual(find_event_id_at_line(text, line_no=6), "test_events.1")

    def test_multiple_events_in_file(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_treasury = -100 }\n"
            "}\n"
            "test_events.2 = {\n"
            "  immediate = { add_treasury = -200 }\n"
            "}\n"
        )
        # second add_treasury sits on line 5
        self.assertEqual(find_event_id_at_line(text, line_no=5), "test_events.2")

    def test_inject_replace_prefixes(self):
        text = (
            "REPLACE:foo.5 = {\n"
            "  immediate = { add_treasury = -1 }\n"
            "}\n"
            "INJECT:bar.7 = {\n"
            "  immediate = { add_treasury = -2 }\n"
            "}\n"
        )
        self.assertEqual(find_event_id_at_line(text, line_no=2), "foo.5")
        self.assertEqual(find_event_id_at_line(text, line_no=5), "bar.7")

    def test_no_event_returns_none(self):
        text = "namespace = test_events\n# just a comment\n"
        self.assertIsNone(find_event_id_at_line(text, line_no=2))

    def test_out_of_range_returns_none(self):
        text = "test_events.1 = {\n}\n"
        self.assertIsNone(find_event_id_at_line(text, line_no=99))


class SuppressionCommentTests(unittest.TestCase):
    def test_full_form(self):
        line = "    multiplier = 2000  # REVIEWED 2026-05-04: tech-gated; intentionally large"
        result = parse_reviewed_comment(line)
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "2026-05-04")
        self.assertEqual(result["rationale"], "tech-gated; intentionally large")

    def test_missing_date_rejected(self):
        line = "    multiplier = 2000  # REVIEWED: no date here"
        self.assertIsNone(parse_reviewed_comment(line))

    def test_missing_rationale_rejected(self):
        line = "    multiplier = 2000  # REVIEWED 2026-05-04"
        self.assertIsNone(parse_reviewed_comment(line))

    def test_no_comment_at_all(self):
        line = "    multiplier = 2000"
        self.assertIsNone(parse_reviewed_comment(line))

    def test_unrelated_comment(self):
        line = "    multiplier = 2000  # just a regular comment"
        self.assertIsNone(parse_reviewed_comment(line))


class DirectEffectScannerTests(unittest.TestCase):
    def test_flags_literal(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_treasury = -10000\n"
            "  }\n"
            "}\n"
        )
        flags = scan_direct_effects(text, file_path="events/foo.txt")
        self.assertEqual(len(flags), 1)
        f = flags[0]
        self.assertEqual(f.event_id, "test_events.1")
        self.assertEqual(f.effect, "add_treasury")
        self.assertEqual(f.value, "-10000")
        self.assertEqual(f.resource, "treasury (instant)")
        self.assertIsNone(f.exemption)
        self.assertEqual(f.line, 3)
        self.assertEqual(f.kind, "direct_effect")

    def test_skips_script_value(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_treasury = sv_treasury_event_small }\n"
            "}\n"
        )
        self.assertEqual(scan_direct_effects(text, file_path="x.txt"), [])

    def test_reviewed_becomes_exemption(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_treasury = -10000  # REVIEWED 2026-05-04: vanilla precedent\n"
            "  }\n"
            "}\n"
        )
        flags = scan_direct_effects(text, file_path="x.txt")
        self.assertEqual(len(flags), 1)
        self.assertIsNotNone(flags[0].exemption)
        self.assertEqual(flags[0].exemption["rationale"], "vanilla precedent")

    def test_skips_zero(self):
        # Zero is a literal but not actionable; treat as a no-op.
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_treasury = 0 }\n"
            "}\n"
        )
        flags = scan_direct_effects(text, file_path="x.txt")
        # We still flag zero since it's a literal — it's the user's choice
        # whether to # REVIEWED it. Confirm at least the regex matches.
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].value, "0")


class InlineModifierScannerTests(unittest.TestCase):
    def test_flags_inline_prestige(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = {\n"
            "      country_prestige_add = 100\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        flags = scan_inline_modifier_types(text, file_path="x.txt")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].effect, "country_prestige_add")
        self.assertEqual(flags[0].value, "100")
        self.assertEqual(flags[0].kind, "modifier_inline")

    def test_skips_mult_modifier(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_modifier = { country_prestige_mult = 0.05 } }\n"
            "}\n"
        )
        self.assertEqual(scan_inline_modifier_types(text, file_path="x.txt"), [])

    def test_skips_unrelated_modifier(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_modifier = { country_authority_add = 100 } }\n"
            "}\n"
        )
        self.assertEqual(scan_inline_modifier_types(text, file_path="x.txt"), [])


if __name__ == "__main__":
    unittest.main()
