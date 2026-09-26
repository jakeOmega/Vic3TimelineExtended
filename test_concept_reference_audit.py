"""Unit tests for concept_reference_audit's loc-line handling.

The audit reads `# REVIEWED ...` suppressions from the text after a loc
value's closing quote, so the escape-aware split (shared with
ModState.add_localization via mod_state.split_loc_line) must neither cut a
value at an escaped `\"` nor misfile the rest of the text as `trailing`.
"""
import unittest

from concept_reference_audit import (
    AuditResult,
    ConceptFlag,
    _parse_loc_line,
    _parse_reviewed,
    render_report,
)


class ParseLocLineTests(unittest.TestCase):
    def test_escaped_quote_keeps_value_whole_and_trailing_comment(self):
        line = (
            r' k:0 "He said \"go\" [Concept(' + "'concept_x','x')]"
            r'" # REVIEWED 2026-05-09: rationale' + "\n"
        )
        parsed = _parse_loc_line(line)
        self.assertIsNotNone(parsed)
        key, value, trailing = parsed
        self.assertEqual(key, "k")
        self.assertEqual(value, r'He said \"go\" [Concept(' + "'concept_x','x')]")
        self.assertEqual(
            _parse_reviewed(trailing),
            {"date": "2026-05-09", "rationale": "rationale"},
        )

    def test_plain_line_without_comment_has_empty_trailing(self):
        self.assertEqual(_parse_loc_line(' k:1 "[concept_y]"\n'), ("k", "[concept_y]", ""))

    def test_header_comment_and_malformed_lines_are_skipped(self):
        for line in ("l_english:\n", "# c\n", " # indented: c\n", " k:0 bare\n", r' k:0 "open \"' + "\n", "\n"):
            self.assertIsNone(_parse_loc_line(line), repr(line))


class RenderReportTests(unittest.TestCase):
    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line number and Coverage no scan counts,
        so the report changes only when the findings do."""
        result = AuditResult(
            flags=[
                ConceptFlag("k_bad", "concept_gone", "localization/english/a_l_english.yml", 7),
                ConceptFlag("k_ok", "concept_later", "localization/english/b_l_english.yml", 12,
                            exemption={"date": "2026-05-09", "rationale": "added next patch"}),
            ],
            loc_files_scanned=178, refs_checked=2939, registered_concepts=718,
        )
        report = render_report(result)
        self.assertIn(
            "- `localization/english/b_l_english.yml` — `k_ok` references "
            "`concept_later` — **2026-05-09**: added next patch", report)
        self.assertNotIn("b_l_english.yml:12", report)
        self.assertIn("`localization/english/a_l_english.yml:7`", report)  # unreviewed
        for gone in ("loc files scanned", "concept references checked",
                     "registered concepts", "178", "2939", "718"):
            self.assertNotIn(gone, report)
        self.assertIn("- total flags: 2", report)


if __name__ == "__main__":
    unittest.main()
