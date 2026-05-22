"""Unit tests for loc_render_audit (issue #134).

Covers the pure check_value detector, loc-line parsing + REVIEWED suppression,
an end-to-end tempdir run with mixed clean/bad/suppressed values, and a
vanilla-clean calibration (the bracket-tag check must be 0 on vanilla loc).
"""
from __future__ import annotations

import os
import tempfile
import unittest

from loc_render_audit import (
    audit,
    check_value,
    render_report,
    _parse_loc_line,
    _parse_reviewed,
)

VANILLA_GAME = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game"


class CheckValueTests(unittest.TestCase):
    def test_flags_bold_open_and_close(self):
        issues = check_value("Hello [b]world[/b]")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0][0], "bracket_tag")
        self.assertIn("[b]", issues[0][1])
        self.assertIn("[/b]", issues[0][1])

    def test_flags_italic_and_underline(self):
        self.assertTrue(check_value("[i]x[/i]"))
        self.assertTrue(check_value("[u]x[/u]"))

    def test_flags_arbitrary_closing_tag(self):
        issues = check_value("text [/color] more")
        self.assertEqual(issues[0][0], "bracket_tag")
        self.assertIn("[/color]", issues[0][1])

    def test_clean_accessor_chain_not_flagged(self):
        self.assertEqual(check_value("[SCOPE.GetName] did a thing"), [])

    def test_clean_concept_link_not_flagged(self):
        self.assertEqual(check_value("see [concept_legitimacy] for detail"), [])

    def test_valid_format_codes_not_flagged(self):
        # The correct #b …#! style must never be flagged.
        self.assertEqual(check_value("gained #b 5#! points"), [])

    def test_unbalanced_hash_not_flagged(self):
        # The unbalanced-#…#! check was dropped (2341 vanilla false positives);
        # such values must pass cleanly now.
        self.assertEqual(check_value("#R unclosed red text"), [])
        self.assertEqual(check_value("trailing reset only #!"), [])


class ParseLineTests(unittest.TestCase):
    def test_extracts_key_value_trailing(self):
        parsed = _parse_loc_line(' my_key:0 "the [b]value[/b]" # REVIEWED 2026-05-21: ok\n')
        self.assertIsNotNone(parsed)
        key, value, trailing = parsed
        self.assertEqual(key, "my_key")
        self.assertEqual(value, "the [b]value[/b]")
        self.assertIn("REVIEWED", trailing)

    def test_value_with_internal_quotes_kept_whole(self):
        key, value, _ = _parse_loc_line('k:0 "the \\"Iron\\" man [b]x[/b]"\n')
        self.assertIn("[b]", value)
        self.assertIn("Iron", value)

    def test_header_and_comment_lines_skipped(self):
        self.assertIsNone(_parse_loc_line("l_english:\n"))
        self.assertIsNone(_parse_loc_line("# a comment\n"))
        self.assertIsNone(_parse_loc_line("\n"))

    def test_reviewed_comment_parsed(self):
        rev = _parse_reviewed("# REVIEWED 2026-05-21: deliberate literal markup")
        self.assertEqual(rev["date"], "2026-05-21")
        self.assertIn("deliberate", rev["rationale"])
        self.assertIsNone(_parse_reviewed("# just a normal comment"))


class EndToEndTests(unittest.TestCase):
    def _write(self, td, body):
        loc_dir = os.path.join(td, "localization", "english")
        os.makedirs(loc_dir)
        with open(os.path.join(loc_dir, "test_l_english.yml"), "w",
                  encoding="utf-8") as fh:
            fh.write(body)

    def test_clean_loc_zero_flags(self):
        with tempfile.TemporaryDirectory() as td:
            self._write(td, 'l_english:\n clean_key:0 "#b bold#! and [concept_x]"\n')
            result = audit(mod_path=td)
            self.assertEqual(len(result.flags), 0)
            self.assertEqual(result.loc_files_scanned, 1)
            self.assertEqual(result.values_checked, 1)

    def test_partitions_suppressed_and_unreviewed(self):
        with tempfile.TemporaryDirectory() as td:
            self._write(
                td,
                'l_english:\n'
                ' bad_key:0 "this is [b]wrong[/b]"\n'
                ' ok_key:0 "also [i]wrong[/i]" # REVIEWED 2026-05-21: intentional demo\n'
                ' good_key:0 "this #b is fine#!"\n',
            )
            result = audit(mod_path=td)
            unrev = [f for f in result.flags if not f.exemption]
            exemp = [f for f in result.flags if f.exemption]
            self.assertEqual(len(unrev), 1)
            self.assertEqual(unrev[0].loc_key, "bad_key")
            self.assertEqual(len(exemp), 1)
            self.assertEqual(exemp[0].loc_key, "ok_key")
            self.assertEqual(exemp[0].exemption["date"], "2026-05-21")

    def test_report_renders(self):
        with tempfile.TemporaryDirectory() as td:
            self._write(td, 'l_english:\n bad:0 "[b]x[/b]"\n')
            report = render_report(audit(mod_path=td))
            self.assertIn("Localization render audit report", report)
            self.assertIn("Bracket formatting tags", report)


@unittest.skipUnless(os.path.isdir(VANILLA_GAME), "vanilla install not found")
class VanillaCleanTests(unittest.TestCase):
    def test_vanilla_loc_has_no_bracket_flags(self):
        # The bracket-tag check is designed to be vanilla-clean; any hit would
        # mean the regex over-matches a legitimate accessor/concept form.
        result = audit(mod_path=VANILLA_GAME)
        self.assertEqual(
            len(result.flags), 0,
            f"unexpected bracket-tag flags in vanilla loc: "
            f"{[(f.file, f.line, f.detail) for f in result.flags[:5]]}",
        )


if __name__ == "__main__":
    unittest.main()
