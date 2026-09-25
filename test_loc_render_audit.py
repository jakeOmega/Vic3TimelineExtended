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
    check_quoted_expansion,
    check_quoted_name,
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


class CheckQuotedExpansionTests(unittest.TestCase):
    """The UN button defect: `[Concept('…','$un_peacekeeping_contributor_modifier$')]`
    expanded a concept link into the quoted argument and broke the parse."""

    LOC = {
        "linked_name": "[concept_un_peacekeeping] Contributor",
        "apostrophe_name": "Women's Integration",
        "plain_name": "Arms Control Participant",
    }

    def _issues(self, value):
        return [i for i, _d in check_quoted_expansion(value, self.LOC)]

    def test_bracket_in_expansion_flagged(self):
        self.assertEqual(
            self._issues("Applies [Concept('concept_x','$linked_name$')]"),
            ["quoted_arg_expansion"])

    def test_apostrophe_in_expansion_flagged(self):
        self.assertEqual(
            self._issues("[Concept('concept_x', '$apostrophe_name$')]"),
            ["quoted_arg_expansion"])

    def test_plain_expansion_not_flagged(self):
        self.assertEqual(self._issues("[Concept('concept_x','$plain_name$')]"), [])

    def test_top_level_reference_not_flagged(self):
        # Outside a data expression the expansion renders normally.
        self.assertEqual(self._issues("Applies $linked_name$ (+5%)"), [])

    def test_unknown_reference_not_flagged(self):
        # Runtime parameters ($VALUE$ etc.) are not loc keys.
        self.assertEqual(self._issues("[Concept('concept_x','$VALUE$')]"), [])

    def test_prose_apostrophes_do_not_pair_into_arguments(self):
        value = "It's [Concept('concept_x','$plain_name$')] and it's $linked_name$"
        self.assertEqual(self._issues(value), [])


class CheckQuotedNameTests(unittest.TestCase):
    """The "Women's Integration" defect: vanilla's add-modifier tooltip pastes
    the modifier name into `GetRawTextTooltipTag('…')`."""

    def _flagged(self, value, loc=None):
        return bool(check_quoted_name(value, loc or {}))

    def test_straight_apostrophe_flagged(self):
        self.assertTrue(self._flagged("Women's Integration"))

    def test_typographic_apostrophe_not_flagged(self):
        self.assertFalse(self._flagged("Women\u2019s Integration"))

    def test_quotes_inside_data_expressions_not_flagged(self):
        self.assertFalse(self._flagged(
            "[Concept('concept_power_bloc_leader', 'Bloc Leader')] Forbade Union"))
        self.assertFalse(self._flagged(
            "Enables [GetTechnology('x').GetName] principles"))

    def test_apostrophe_reached_through_reference_flagged(self):
        self.assertTrue(self._flagged("$base$ Bonus", {"base": "Victor's Peace"}))


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

    def test_quoted_name_only_checks_modifier_and_modifier_type_names(self):
        with tempfile.TemporaryDirectory() as td:
            self._write(
                td,
                'l_english:\n'
                ' my_static_mod:0 "Women\'s Integration"\n'
                ' my_mod_type_add:0 "Soldiers\' [concept_x]"\n'
                ' my_reviewed_mod:0 "Victor\'s Peace" # REVIEWED 2026-09-25: demo\n'
                ' my_event_title:0 "The People\'s Choice"\n',
            )
            for rel, body in (
                ("common/static_modifiers/m.txt",
                 "my_static_mod = {\n}\nmy_reviewed_mod = {\n}\n"),
                ("common/modifier_type_definitions/t.txt", "my_mod_type_add = {\n}\n"),
            ):
                os.makedirs(os.path.dirname(os.path.join(td, rel)), exist_ok=True)
                with open(os.path.join(td, rel), "w", encoding="utf-8") as fh:
                    fh.write(body)
            result = audit(mod_path=td)
        got = sorted((f.loc_key, f.issue, bool(f.exemption)) for f in result.flags)
        self.assertEqual(got, [
            ("my_mod_type_add", "quoted_name_apostrophe", False),
            ("my_reviewed_mod", "quoted_name_apostrophe", True),
            ("my_static_mod", "quoted_name_apostrophe", False),
        ])

    def test_quoted_expansion_resolves_across_files(self):
        with tempfile.TemporaryDirectory() as td:
            self._write(td, 'l_english:\n uses:0 "[Concept(\'concept_x\',\'$linked$\')]"\n')
            with open(os.path.join(td, "localization", "english", "other_l_english.yml"),
                      "w", encoding="utf-8") as fh:
                fh.write('l_english:\n linked:0 "[concept_y] Contributor"\n')
            result = audit(mod_path=td)
        self.assertEqual([(f.loc_key, f.issue) for f in result.flags],
                         [("uses", "quoted_arg_expansion")])

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
        tag_flags = [f for f in result.flags if f.issue == "bracket_tag"]
        self.assertEqual(
            len(tag_flags), 0,
            f"unexpected bracket-tag flags in vanilla loc: "
            f"{[(f.file, f.line, f.detail) for f in tag_flags[:5]]}",
        )

    def test_vanilla_english_loc_has_no_nested_bracket_flags(self):
        # Zero nested-bracket values across all 102k vanilla *English* loc
        # values, which is what establishes the rule. The non-English vanilla
        # files are NOT clean — e.g. `content_104_l_japanese.yml:436` writes
        # `[[Concept(…)]]` where the English line writes `[Concept(…)]` — so
        # those are translator typos in vanilla, not an escaping convention.
        # This mod ships English only, so scope the assertion to match.
        result = audit(mod_path=VANILLA_GAME)
        nested = [
            f for f in result.flags
            if f.issue == "nested_brackets"
            and os.path.normpath(f.file).startswith(
                os.path.join("localization", "english")
            )
        ]
        self.assertEqual(
            len(nested), 0,
            f"unexpected nested-bracket flags in vanilla English loc: "
            f"{[(f.file, f.line, f.detail) for f in nested[:5]]}",
        )


if __name__ == "__main__":
    unittest.main()
