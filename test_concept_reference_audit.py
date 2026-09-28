"""Unit tests for concept_reference_audit's loc-line handling.

The audit reads `# REVIEWED ...` suppressions from the text after a loc
value's closing quote, so the escape-aware split (shared with
ModState.add_localization via mod_state.split_loc_line) must neither cut a
value at an escaped `\"` nor misfile the rest of the text as `trailing`.
"""
import os
import tempfile
import unittest
from types import SimpleNamespace

from concept_reference_audit import (
    AuditResult,
    ConceptFlag,
    _parse_loc_line,
    _parse_reviewed,
    audit,
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


class ConceptFunctionArgumentTests(unittest.TestCase):
    """#438: `Concept()`'s first argument is checked whatever its name."""

    def _audit(self, loc: str) -> AuditResult:
        ms = SimpleNamespace(mod_parsers={
            "Game Concepts": SimpleNamespace(data={"concept_x": {}}),
        })
        with tempfile.TemporaryDirectory() as td:
            loc_dir = os.path.join(td, "localization", "english")
            os.makedirs(loc_dir)
            with open(os.path.join(loc_dir, "a_l_english.yml"), "w", encoding="utf-8-sig") as fh:
                fh.write("l_english:\n" + loc)
            return audit(ms, mod_path=td)

    def test_non_concept_first_argument_flagged(self):
        # The pre-#437 gen_un_button_descs.py output: a modifier name, not a concept.
        result = self._audit(
            " UN_X_EFFECTS:0 \"[Concept('some_modifier_name','$some_modifier_name$')]\"\n"
        )
        self.assertEqual(
            [(f.loc_key, f.concept, f.exemption) for f in result.flags],
            [("UN_X_EFFECTS", "some_modifier_name", None)],
        )

    def test_registered_concept_not_flagged(self):
        result = self._audit(" k:0 \"[Concept('concept_x','X')] and [concept_x]\"\n")
        self.assertEqual(result.flags, [])

    def test_reviewed_comment_still_exempts(self):
        result = self._audit(
            " k:0 \"[Concept('some_modifier_name','x')]\" # REVIEWED 2026-09-27: why\n"
        )
        self.assertEqual(len(result.flags), 1)
        self.assertEqual(result.flags[0].exemption, {"date": "2026-09-27", "rationale": "why"})


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
