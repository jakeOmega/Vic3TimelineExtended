"""Unit tests for concept_reference_audit's loc-line handling.

The audit reads `# REVIEWED ...` suppressions from the text after a loc
value's closing quote, so the escape-aware split (shared with
ModState.add_localization via mod_state.split_loc_line) must neither cut a
value at an escaped `\"` nor misfile the rest of the text as `trailing`.
"""
import unittest

from concept_reference_audit import _parse_loc_line, _parse_reviewed


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


if __name__ == "__main__":
    unittest.main()
