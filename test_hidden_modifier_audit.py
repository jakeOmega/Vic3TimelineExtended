"""Unit tests for hidden_modifier_audit (#1213).

Each fixture is a throwaway mod tree: static modifiers (one with effect lines,
one that is only an icon), a vanilla snapshot of loc and modifiers, English
loc and one script file. The crux is when a `custom_tooltip`'s text counts as
rendering the modifier it wraps, what is skipped (lineless modifiers,
`hidden_effect`, a `$PARAM$` text, debug files), and the tagged suppression.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from hidden_modifier_audit import CHECK, REPORT_PATH, audit, main, regenerate

MODIFIERS = """\
te_bonus = {
\ticon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
\tcountry_prestige_add = 5
}
te_other = { country_prestige_add = 1 }
te_marker = {
\ticon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
}
"""


def _write(root: str, rel: str, text: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as fh:
        fh.write(text)


class _Fixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        os.makedirs(os.path.join(self.root, "vanilla_parsed", "common"))
        with open(os.path.join(self.root, "vanilla_parsed", "localization_english.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"VANILLA_TT": "Vanilla text"}, fh)
        with open(os.path.join(self.root, "vanilla_parsed", "common", "modifiers.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"vanilla_bonus": ["=", {"country_prestige_add": ["=", "1"]}],
                       "vanilla_marker": ["=", {"icon": ["=", "x.dds"]}]}, fh)
        _write(self.root, "common/static_modifiers/te_test_modifiers.txt", MODIFIERS)
        self.loc(
            'te_plain_tt:0 "Grants prestige."',
            'te_rendered_tt:0 "Grants: [GetStaticModifier(\'te_bonus\').GetDesc]"',
            'te_other_tt:0 "[GetStaticModifier(\'te_other\').GetDesc]"',
            'te_splice_tt:0 "Intro. $te_rendered_tt$"',
            'te_select_tt:0 "[SelectLocalization( Cond, \'te_rendered_tt\', \'te_plain_tt\' )]"',
        )

    def loc(self, *lines: str) -> None:
        _write(self.root, "localization/english/te_test_l_english.yml",
               "l_english:\n" + "".join(f" {line}\n" for line in lines))

    def script(self, body: str, name: str = "te_test_effects.txt") -> None:
        _write(self.root, f"common/scripted_effects/{name}", body)

    def flags(self):
        return [(f.line, f.text_key, [h.modifier for h in f.hidden]) for f in audit(self.root).flags]


class FlagTests(_Fixture):
    def test_wrapped_add_modifier_with_prose_is_flagged(self):
        self.script("e = {\n"
                    "\tcustom_tooltip = {\n"
                    "\t\ttext = te_plain_tt\n"
                    "\t\tadd_modifier = { name = te_bonus months = 12 }\n"
                    "\t}\n"
                    "}\n")
        r = audit(self.root)
        self.assertEqual([(f.file, f.line, f.text_key) for f in r.flags],
                         [("common/scripted_effects/te_test_effects.txt", 2, "te_plain_tt")])
        self.assertEqual([(h.modifier, h.line) for h in r.flags[0].hidden], [("te_bonus", 4)])
        self.assertEqual(r.failing, 1)

    def test_rendered_modifier_passes_directly_through_splice_and_select(self):
        for key in ("te_rendered_tt", "te_splice_tt", "te_select_tt"):
            with self.subTest(key=key):
                self.script(f"e = {{ custom_tooltip = {{ text = \"{key}\" add_modifier = te_bonus }} }}\n")
                self.assertEqual(self.flags(), [])

    def test_a_different_rendered_modifier_still_hides_this_one(self):
        self.script("e = { custom_tooltip = { text = te_other_tt add_modifier = { name = te_bonus } } }\n")
        self.assertEqual(self.flags(), [(1, "te_other_tt", ["te_bonus"])])

    def test_nested_in_a_scope_change_and_custom_description(self):
        self.script("e = {\n"
                    "\tcustom_description = {\n"
                    "\t\ttext = te_plain_tt\n"
                    "\t\tje:je_x = { if = { limit = { always = yes } add_modifier = { name = vanilla_bonus } } }\n"
                    "\t}\n"
                    "}\n")
        self.assertEqual(self.flags(), [(2, "te_plain_tt", ["vanilla_bonus"])])

    def test_lineless_modifiers_are_not_flagged(self):
        self.script("e = { custom_tooltip = { text = te_plain_tt add_modifier = te_marker"
                    " add_modifier = { name = vanilla_marker } } }\n")
        self.assertEqual(self.flags(), [])

    def test_hidden_effect_is_not_read(self):
        self.script("e = { hidden_effect = { custom_tooltip = { text = te_plain_tt add_modifier = te_bonus } } }\n")
        self.assertEqual(self.flags(), [])

    def test_param_text_is_skipped_and_counted(self):
        self.script("e = { custom_tooltip = { text = $TT$ add_modifier = te_bonus } }\n")
        r = audit(self.root)
        self.assertEqual((r.flags, r.dynamic_skipped), ([], 1))

    def test_param_modifier_needs_some_rendered_modifier(self):
        self.script("e = { custom_tooltip = { text = te_plain_tt add_modifier = { name = $M$ } } }\n"
                    "f = { custom_tooltip = { text = te_other_tt add_modifier = { name = $M$ } } }\n")
        self.assertEqual(self.flags(), [(1, "te_plain_tt", ["$M$"])])

    def test_add_modifier_inside_a_string_or_comment_is_not_counted(self):
        self.script("e = { custom_tooltip = { text = te_plain_tt debug_log = \"add_modifier = te_bonus\" } }\n"
                    "# custom_tooltip = { text = te_plain_tt add_modifier = te_bonus }\n")
        self.assertEqual(self.flags(), [])

    def test_events_are_read_and_debug_files_skipped(self):
        _write(self.root, "events/te_test_events.txt",
               "e.1 = { option = { custom_tooltip = { text = te_plain_tt add_modifier = te_bonus } } }\n")
        self.script("e = { custom_tooltip = { text = te_plain_tt add_modifier = te_bonus } }\n",
                    name="te_debug_effects.txt")
        r = audit(self.root)
        self.assertEqual([f.file for f in r.flags], ["events/te_test_events.txt"])


class SuppressionTests(_Fixture):
    def test_tag_on_the_opening_line_exempts(self):
        self.script(f"e = {{\n\tcustom_tooltip = {{ # REVIEWED 2026-10-27 ({CHECK}): a hidden helper\n"
                    "\t\ttext = te_plain_tt\n\t\tadd_modifier = te_bonus\n\t}\n}\n")
        r = audit(self.root)
        self.assertEqual(r.flags[0].exemption, {"date": "2026-10-27", "rationale": "a hidden helper"})
        self.assertEqual(r.failing, 0)

    def test_tag_on_another_line_is_stale_and_the_flag_stands(self):
        self.script(f"e = {{\n\tcustom_tooltip = {{\n"
                    f"\t\ttext = te_plain_tt # REVIEWED 2026-10-27 ({CHECK}): wrong line\n"
                    "\t\tadd_modifier = te_bonus\n\t}\n}\n")
        r = audit(self.root)
        self.assertIsNone(r.flags[0].exemption)
        self.assertEqual([t.line for t in r.stale_tags], [3])
        self.assertEqual(r.failing, 2)

    def test_tag_on_a_clean_block_is_stale(self):
        self.script(f"e = {{ custom_tooltip = {{ # REVIEWED 2026-10-27 ({CHECK}): was hidden\n"
                    "\ttext = te_rendered_tt add_modifier = te_bonus } }\n")
        r = audit(self.root)
        self.assertEqual(r.flags, [])
        self.assertEqual(len(r.stale_tags), 1)


class CliTests(_Fixture):
    def test_strict_and_regenerate(self):
        self.script("e = { custom_tooltip = { text = te_plain_tt add_modifier = te_bonus } }\n")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["--strict", "--mod-path", self.root]), 1)
        self.assertIn("`te_plain_tt` hides `te_bonus`", out.getvalue())
        with mock.patch("path_constants.mod_path", self.root):
            summary = regenerate(None)
        self.assertEqual((summary["unreviewed"], summary["blocks_checked"]), (1, 1))
        self.assertTrue(os.path.isfile(os.path.join(self.root, REPORT_PATH)))


class RepoTests(unittest.TestCase):
    def test_runs_over_the_mod(self):
        from path_constants import mod_path
        result = audit(mod_path)
        self.assertGreater(result.files_scanned, 100)
        self.assertGreater(result.blocks_checked, 5)

    def test_post_load_roster(self):
        from scripts.analysis.check_post_load_rosters import extract_rosters
        root = os.path.dirname(os.path.abspath(__file__))
        self.assertIn("hidden_modifier_audit", extract_rosters(
            os.path.join(root, "mod_state_server.py"))["POST_LOAD_AUDITS"])


if __name__ == "__main__":
    unittest.main()
