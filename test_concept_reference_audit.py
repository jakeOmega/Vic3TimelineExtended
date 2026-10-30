"""Unit tests for concept_reference_audit: its loc-line handling and the
`--strict` exit status CI runs it with.

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
    strict_exit_code,
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


class StrictExitCodeTests(unittest.TestCase):
    """`--strict` is the CI mode: fail on any flag with no REVIEWED exemption."""

    def _result(self, *exemptions):
        return AuditResult(flags=[
            ConceptFlag(f"k{i}", "concept_gone", "localization/english/a_l_english.yml", i + 1,
                        exemption=ex)
            for i, ex in enumerate(exemptions)
        ])

    def test_no_flags_passes(self):
        self.assertEqual(strict_exit_code(self._result()), 0)

    def test_one_unreviewed_flag_fails(self):
        self.assertEqual(strict_exit_code(self._result(None)), 1)

    def test_all_reviewed_passes(self):
        reviewed = {"date": "2026-10-30", "rationale": "registered next patch"}
        self.assertEqual(strict_exit_code(self._result(reviewed, reviewed)), 0)

    def test_one_unreviewed_among_reviewed_fails(self):
        reviewed = {"date": "2026-10-30", "rationale": "registered next patch"}
        self.assertEqual(strict_exit_code(self._result(reviewed, None)), 1)

    def test_unregistered_concept_link_fails_and_registering_it_passes(self):
        """End to end through audit(): the #1257 shape, a widget tooltip
        linking a concept `common/game_concepts/` never declared."""
        line = (" je_space_race_widget_mod_mine_tt:0 "
                "\"Needs a [concept_sr_extraplanetary_base].\"")
        concepts = {"concept_x": {}}
        ms = SimpleNamespace(mod_parsers={"Game Concepts": SimpleNamespace(data=concepts)})
        with tempfile.TemporaryDirectory() as td:
            loc_dir = os.path.join(td, "localization", "english")
            os.makedirs(loc_dir)
            path = os.path.join(loc_dir, "a_l_english.yml")

            def run(loc_line):
                with open(path, "w", encoding="utf-8-sig") as fh:
                    fh.write("l_english:\n" + loc_line + "\n")
                return strict_exit_code(audit(ms, mod_path=td))

            self.assertEqual(run(line), 1)
            self.assertEqual(run(line + " # REVIEWED 2026-10-30: registered next patch"), 0)
            concepts["concept_sr_extraplanetary_base"] = {}
            self.assertEqual(run(line), 0)


class RepoTests(unittest.TestCase):
    def test_ci_runs_it_strict(self):
        root = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(root, ".github", "workflows", "ci.yml"), encoding="utf-8") as fh:
            self.assertIn("python3 concept_reference_audit.py --strict", fh.read())


if __name__ == "__main__":
    unittest.main()
