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


if __name__ == "__main__":
    unittest.main()
