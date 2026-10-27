"""Unit tests for long_tooltip_audit (#1213).

Each fixture is a throwaway mod tree: a vanilla loc snapshot, English loc and
one or two `.gui` files. The crux is the rendered length (splices expanded,
`[...]` and icons one character, format codes none), which references count
(`text`, `tooltip`, `Localize`, `SelectLocalization`), what counts as a How
section, and the tagged suppression, stale tags included.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from long_tooltip_audit import (
    CHECK, REPORT_PATH, THRESHOLD, audit, main, regenerate, rendered_length, rendered_text,
)

LONG = "x" * (THRESHOLD + 1)


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
        os.makedirs(os.path.join(self.root, "vanilla_parsed"))
        with open(os.path.join(self.root, "vanilla_parsed", "localization_english.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"VANILLA_WORD": "Grain", "VANILLA_LONG": LONG}, fh)

    def loc(self, *lines: str, name: str = "te_test_l_english.yml", folder: str = "") -> None:
        rel = os.path.join("localization", "english", folder, name)
        _write(self.root, rel, "l_english:\n" + "".join(f" {line}\n" for line in lines))

    def gui(self, body: str, name: str = "te_test.gui") -> None:
        _write(self.root, f"gui/{name}", body)

    def keys(self, result=None):
        result = result or audit(self.root)
        return [f.key for f in result.flags]


class RenderedLengthTests(unittest.TestCase):
    def lookup(self, key):
        return {"inner": "abc", "loop": "$loop$"}.get(key)

    def test_plain_text_and_newline(self):
        self.assertEqual(rendered_length("ab\\ncd", self.lookup), 5)

    def test_splice_is_expanded_and_unknown_param_is_one(self):
        self.assertEqual(rendered_length("$inner$ $VALUE$", self.lookup), 5)

    def test_brackets_and_icons_count_one_each(self):
        self.assertEqual(rendered_length("[GetPlayer.GetName] @oil! x", self.lookup), 5)
        self.assertEqual(rendered_length("[Select( [A], 'b' )]", self.lookup), 1)

    def test_format_codes_count_none(self):
        self.assertEqual(rendered_length("#b Bold#! #tooltippable;tooltip:[x],k Word#!", self.lookup),
                         len("Bold Word"))

    def test_escaped_quote_is_one(self):
        self.assertEqual(rendered_text('say \\"hi\\"', self.lookup), 'say "hi"')

    def test_recursive_splice_terminates(self):
        self.assertLess(rendered_length("$loop$", self.lookup), 20)


class FlagTests(_Fixture):
    def test_long_tooltip_is_flagged_with_file_and_length(self):
        self.loc(f'te_long_tt:0 "{LONG}"', 'te_short_tt:0 "short"')
        self.gui('widget = {\n\ttooltip = "te_long_tt"\n\ttextbox = { text = "te_short_tt" }\n}\n')
        r = audit(self.root)
        self.assertEqual([(f.key, f.length, f.gui_files) for f in r.flags],
                         [("te_long_tt", THRESHOLD + 1, ["gui/te_test.gui"])])
        self.assertEqual(r.flags[0].loc_line, 2)
        self.assertEqual(r.failing, 1)

    def test_at_threshold_passes(self):
        self.loc(f'te_tt:0 "{"x" * THRESHOLD}"')
        self.gui('widget = { tooltip = "te_tt" }\n')
        self.assertEqual(self.keys(), [])

    def test_threshold_argument(self):
        self.loc('te_tt:0 "0123456789"')
        self.gui('widget = { tooltip = "te_tt" }\n')
        self.assertEqual(self.keys(audit(self.root, threshold=5)), ["te_tt"])

    def test_splice_counts_toward_length(self):
        self.loc('te_tt:0 "Intro: $VANILLA_LONG$"')
        self.gui('widget = { tooltip = "te_tt" }\n')
        self.assertEqual(self.keys(), ["te_tt"])

    def test_localize_and_select_localization_arguments_count(self):
        self.loc(f'te_a:0 "{LONG}"', f'te_b:0 "{LONG}"', f'te_c:0 "{LONG}"')
        self.gui('widget = {\n'
                 '\ttooltip = "[Localize(\'te_a\')]"\n'
                 '\ttext = "[SelectLocalization( GetScriptedGui(\'te_x\').IsShown( GuiScope.End ), \'te_b\', \'te_c\' )]"\n'
                 '}\n')
        self.assertEqual(self.keys(), ["te_a", "te_b", "te_c"])

    def test_vanilla_key_and_unreferenced_key_are_not_flagged(self):
        self.loc(f'te_unused_here:0 "{LONG}"')
        self.gui('widget = { tooltip = "VANILLA_LONG" }\n')
        self.assertEqual(self.keys(), [])

    def test_debug_gui_is_skipped(self):
        self.loc(f'te_tt:0 "{LONG}"')
        self.gui('widget = { tooltip = "te_tt" }\n', name="te_debug_panel.gui")
        self.gui('widget = { }\n')
        self.assertEqual(self.keys(), [])

    def test_te_unused_is_not_read_and_replace_wins(self):
        self.loc(f'te_tt:0 "{LONG}"', name="te_unused_l_english.yml")
        self.loc('te_r:0 "short"')
        self.loc(f'te_r:0 "{LONG}"', name="override_l_english.yml", folder="replace")
        self.gui('widget = { tooltip = "te_tt" tooltip = "te_r" }\n')
        self.assertEqual(self.keys(), ["te_r"])


class HowSectionTests(_Fixture):
    def setUp(self):
        super().setUp()
        self.loc(f'te_rule:0 "{LONG}"', f'te_tax_how_rule:0 "{LONG}"')

    def test_how_toggle_excludes(self):
        self.gui('flowcontainer = {\n'
                 '\tvisible = "[GetVariableSystem.Exists(\'te_x_how_open\')]"\n'
                 '\ttextbox = { text = "te_rule" }\n'
                 '}\n')
        self.assertEqual(self.keys(), [])

    def test_the_show_more_arrow_is_not_a_how_section(self):
        self.gui('widget = {\n'
                 '\tvisible = "[Not(GetVariableSystem.Exists(\'te_x_how_open\'))]"\n'
                 '\ttooltip = "te_rule"\n'
                 '}\n')
        self.assertEqual(self.keys(), ["te_rule"])

    def test_how_or_help_named_type_excludes(self):
        self.gui('types t {\n'
                 '\ttype te_x_help_topic = flowcontainer { textbox = { text = "te_rule" } }\n'
                 '}\n')
        self.assertEqual(self.keys(), [])

    def test_how_named_key_is_excluded_anywhere(self):
        self.gui('widget = { tooltip = "te_tax_how_rule" }\n')
        self.assertEqual(self.keys(), [])

    def test_a_key_also_used_live_is_flagged(self):
        self.gui('types t {\n'
                 '\ttype te_x_sec_how = flowcontainer { textbox = { text = "te_rule" } }\n'
                 '}\n'
                 'widget = { tooltip = "te_rule" }\n')
        self.assertEqual(self.keys(), ["te_rule"])


class SuppressionTests(_Fixture):
    def test_tag_on_the_loc_line_exempts(self):
        self.loc(f'te_tt:0 "{LONG}" # REVIEWED 2026-10-27 ({CHECK}): a reference card')
        self.gui('widget = { tooltip = "te_tt" }\n')
        r = audit(self.root)
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.flags[0].exemption, {"date": "2026-10-27", "rationale": "a reference card"})
        self.assertEqual(r.failing, 0)

    def test_stale_tag_fails(self):
        self.loc(f'te_tt:0 "short" # REVIEWED 2026-10-27 ({CHECK}): was long')
        self.gui('widget = { tooltip = "te_tt" }\n')
        r = audit(self.root)
        self.assertEqual([(t.key, t.line) for t in r.stale_tags], [("te_tt", 2)])
        self.assertEqual(r.failing, 1)

    def test_tag_for_another_check_does_not_exempt(self):
        self.loc(f'te_tt:0 "{LONG}" # REVIEWED 2026-10-27 (loc_script_value): other')
        self.gui('widget = { tooltip = "te_tt" }\n')
        r = audit(self.root)
        self.assertIsNone(r.flags[0].exemption)
        self.assertEqual(r.stale_tags, [])

    def test_tag_on_an_overridden_copy_is_stale(self):
        self.loc(f'te_tt:0 "{LONG}" # REVIEWED 2026-10-27 ({CHECK}): first copy', name="a_l_english.yml")
        self.loc(f'te_tt:0 "{LONG}"', name="b_l_english.yml")
        self.gui('widget = { tooltip = "te_tt" }\n')
        r = audit(self.root)
        self.assertIsNone(r.flags[0].exemption)
        self.assertEqual(len(r.stale_tags), 1)


class CliTests(_Fixture):
    def test_strict_exit_codes_and_report(self):
        self.loc(f'te_tt:0 "{LONG}"')
        self.gui('widget = { tooltip = "te_tt" }\n')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["--strict", "--mod-path", self.root]), 1)
        self.assertIn("`te_tt`", out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--mod-path", self.root]), 0)
            self.assertEqual(main(["--strict", "--mod-path", self.root, "--threshold", "999"]), 0)

    def test_regenerate_writes_the_report(self):
        self.loc(f'te_tt:0 "{LONG}"')
        self.gui('widget = { tooltip = "te_tt" }\n')
        with mock.patch("path_constants.mod_path", self.root):
            summary = regenerate(None)
        self.assertEqual((summary["unreviewed"], summary["total_flags"]), (1, 1))
        with open(os.path.join(self.root, REPORT_PATH), encoding="utf-8") as fh:
            self.assertIn("| 501 | `te_tt` |", fh.read())

    def test_missing_snapshot_raises(self):
        os.remove(os.path.join(self.root, "vanilla_parsed", "localization_english.json"))
        self.loc('te_tt:0 "x"')
        self.gui('widget = { tooltip = "te_tt" }\n')
        with self.assertRaises(FileNotFoundError):
            audit(self.root)


class RepoTests(unittest.TestCase):
    def test_runs_over_the_mod(self):
        from path_constants import mod_path
        result = audit(mod_path)
        self.assertGreater(result.gui_files_scanned, 20)
        self.assertGreater(result.keys_measured, 1000)

    def test_post_load_roster(self):
        from scripts.analysis.check_post_load_rosters import extract_rosters
        root = os.path.dirname(os.path.abspath(__file__))
        self.assertIn("long_tooltip_audit", extract_rosters(
            os.path.join(root, "mod_state_server.py"))["POST_LOAD_AUDITS"])


if __name__ == "__main__":
    unittest.main()
