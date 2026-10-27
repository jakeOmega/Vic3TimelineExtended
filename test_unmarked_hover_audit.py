"""Unit tests for unmarked_hover_audit (#1213).

Each fixture is a throwaway mod tree: a vanilla loc snapshot, English loc, a
scripted GUI file (for the mod's own names) and one `.gui` file. The crux is
what carries a tooltip (a widget's own, a row type's `blockoverride`, a
`tooltipwidget`), which textboxes are its text, what counts as marked, what
is left out as vanilla's or a control's, and where a flag and its tag go.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from unmarked_hover_audit import CHECK, REPORT_PATH, audit, main, regenerate

ROW_TYPE = """\
types t {
\ttype te_row = flowcontainer {
\t\tblock "row_tooltip" {}
\t\ttextbox = {
\t\t\tblock "label_format" {
\t\t\t\t%s
\t\t\t}
\t\t\tblock "row_label" {}
\t\t}
\t}
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
        os.makedirs(os.path.join(self.root, "vanilla_parsed"))
        with open(os.path.join(self.root, "vanilla_parsed", "localization_english.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"VANILLA_TT": "Vanilla hover", "VANILLA_LABEL": "Locked"}, fh)
        _write(self.root, "common/scripted_guis/te_test_sguis.txt", "te_x_sgui = { scope = country }\n")
        _write(self.root, "localization/english/te_test_l_english.yml", "l_english:\n" + "".join(
            f" {line}\n" for line in (
                'te_tt:0 "A hover"',
                'te_label:0 "Label"',
                'te_value:0 "12"',
                'te_marked:0 "#tooltippable Label#!"',
                'te_inline:0 "See #tooltippable;tooltip:te_tt this#!"',
                'te_splice:0 "$te_marked$"',
            )))

    def gui(self, body: str, name: str = "te_test.gui") -> None:
        _write(self.root, f"gui/{name}", body)

    def flags(self):
        return [(f.line, f.hover) for f in audit(self.root).flags]


class DirectHoverTests(_Fixture):
    def test_widget_tooltip_over_unmarked_text_is_flagged(self):
        self.gui('flowcontainer = {\n'
                 '\ttooltip = "te_tt"\n'
                 '\ttextbox = { text = "te_label" }\n'
                 '\ttextbox = { text = "te_value" }\n'
                 '}\n')
        r = audit(self.root)
        self.assertEqual([(f.file, f.line, f.labels) for f in r.flags],
                         [("gui/te_test.gui", 2, ["te_label", "te_value"])])
        self.assertEqual(r.failing, 1)

    def test_one_marked_textbox_is_enough(self):
        self.gui('flowcontainer = {\n'
                 '\ttooltip = "te_tt"\n'
                 '\ttextbox = { text = "te_label" default_format = "#tooltippable" }\n'
                 '\ttextbox = { text = "te_value" }\n'
                 '}\n')
        self.assertEqual(self.flags(), [])

    def test_mark_in_the_loc_counts_inline_and_through_a_splice(self):
        for key in ("te_marked", "te_inline", "te_splice"):
            with self.subTest(key=key):
                self.gui(f'widget = {{ tooltip = "te_tt" textbox = {{ text = "{key}" }} }}\n')
                self.assertEqual(self.flags(), [])

    def test_textbox_carrying_its_own_tooltip(self):
        self.gui('textbox = { text = "te_value" tooltip = "[GetScriptedGui(\'te_x_sgui\').ExecuteTooltip( GuiScope.End )]" }\n')
        self.assertEqual(self.flags(), [(1, "textbox")])

    def test_buttons_and_onclick_controls_are_not_judged(self):
        self.gui('button = { tooltip = "te_tt" textbox = { text = "te_label" } }\n'
                 'widget = { tooltip = "te_tt" onclick = "[X]" textbox = { text = "te_label" } }\n'
                 'types t { type te_btn = button_standard { } }\n'
                 'te_btn = { tooltip = "te_tt" textbox = { text = "te_label" } }\n')
        self.assertEqual(self.flags(), [])

    def test_text_inside_a_nested_hover_is_that_hovers(self):
        self.gui('widget = {\n'
                 '\ttooltip = "te_tt"\n'
                 '\ttextbox = { text = "te_label" tooltip = "te_tt" default_format = "#tooltippable" }\n'
                 '}\n')
        self.assertEqual(self.flags(), [])

    def test_vanilla_tooltip_or_vanilla_text_is_left_out(self):
        self.gui('widget = { tooltip = "VANILLA_TT" textbox = { text = "te_label" } }\n'
                 'widget = { tooltip = "te_tt" textbox = { text = "VANILLA_LABEL" } }\n')
        r = audit(self.root)
        self.assertEqual((r.flags, r.vanilla_skipped), ([], 2))

    def test_tooltipwidget_with_mod_content(self):
        self.gui('widget = {\n'
                 '\ttooltipwidget = { textbox = { text = "te_tt" } }\n'
                 '\ttextbox = { text = "te_label" }\n'
                 '}\n'
                 'widget = {\n'
                 '\ttooltipwidget = { textbox = { text = "VANILLA_TT" } }\n'
                 '\ttextbox = { text = "te_label" }\n'
                 '}\n')
        self.assertEqual(self.flags(), [(2, "widget")])

    def test_debug_gui_is_skipped(self):
        self.gui('widget = { tooltip = "te_tt" textbox = { text = "te_label" } }\n', name="te_debug_x.gui")
        self.gui('widget = { }\n')
        self.assertEqual(self.flags(), [])


def _instance(extra: str = "") -> str:
    return ('te_row = {\n'
            '\tblockoverride "row_tooltip" { tooltip = "te_tt" }\n'
            '\tblockoverride "row_label" { text = "te_label" }\n'
            f'{extra}'
            '}\n')


class RowTypeTests(_Fixture):
    def instance(self, extra: str = "") -> str:
        return _instance(extra)

    def test_unmarked_row_type_is_flagged_once_at_the_type(self):
        self.gui(ROW_TYPE % "" + self.instance() + self.instance())
        r = audit(self.root)
        self.assertEqual([(f.line, f.hover) for f in r.flags], [(2, "type te_row")])
        self.assertEqual(r.flags[0].instances, ["gui/te_test.gui:13", "gui/te_test.gui:17"])

    def test_label_format_block_marks_every_instance(self):
        self.gui(ROW_TYPE % 'default_format = "#tooltippable"' + self.instance())
        self.assertEqual(self.flags(), [])

    def test_overriding_the_format_away_on_a_hovered_row_is_flagged(self):
        self.gui(ROW_TYPE % 'default_format = "#tooltippable"'
                 + self.instance('\tblockoverride "label_format" {}\n'))
        self.assertEqual(self.flags(), [(2, "type te_row")])

    def test_row_without_a_tooltip_is_not_a_hover(self):
        self.gui(ROW_TYPE % "" + 'te_row = { blockoverride "row_label" { text = "te_label" } }\n')
        self.assertEqual(self.flags(), [])

    def test_tooltip_on_the_instance_lands_on_the_type(self):
        self.gui(ROW_TYPE % "" + 'te_row = {\n\ttooltip = "te_tt"\n'
                 '\tblockoverride "row_label" { text = "te_label" }\n}\n')
        self.assertEqual(self.flags(), [(2, "type te_row")])


class SuppressionTests(_Fixture):
    def test_tag_on_the_tooltip_line(self):
        self.gui('widget = {\n'
                 f'\ttooltip = "te_tt" # REVIEWED 2026-10-27 ({CHECK}): the icon says it\n'
                 '\ttextbox = { text = "te_label" }\n'
                 '}\n')
        r = audit(self.root)
        self.assertEqual(r.flags[0].exemption, {"date": "2026-10-27", "rationale": "the icon says it"})
        self.assertEqual(r.failing, 0)

    def test_tag_on_the_type_line_for_a_row_type(self):
        body = (ROW_TYPE % "").replace(
            "type te_row = flowcontainer {",
            f"type te_row = flowcontainer {{ # REVIEWED 2026-10-27 ({CHECK}): rows read as a table")
        self.gui(body + _instance())
        r = audit(self.root)
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.failing, 0)

    def test_stale_tag_fails(self):
        self.gui('widget = {\n'
                 f'\ttooltip = "te_tt" # REVIEWED 2026-10-27 ({CHECK}): was unmarked\n'
                 '\ttextbox = { text = "te_marked" }\n'
                 '}\n')
        r = audit(self.root)
        self.assertEqual([(t.file, t.line) for t in r.stale_tags], [("gui/te_test.gui", 2)])
        self.assertEqual(r.failing, 1)


class CliTests(_Fixture):
    def test_strict_and_regenerate(self):
        self.gui('widget = { tooltip = "te_tt" textbox = { text = "te_label" } }\n')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["--strict", "--mod-path", self.root]), 1)
        self.assertIn("text `te_label`", out.getvalue())
        with mock.patch("path_constants.mod_path", self.root):
            summary = regenerate(None)
        self.assertEqual(summary["unreviewed"], 1)
        self.assertTrue(os.path.isfile(os.path.join(self.root, REPORT_PATH)))


class RepoTests(unittest.TestCase):
    def test_runs_over_the_mod(self):
        from path_constants import mod_path
        result = audit(mod_path)
        self.assertGreater(result.files_scanned, 20)
        self.assertGreater(result.hovers_checked, 100)

    def test_post_load_roster(self):
        from scripts.analysis.check_post_load_rosters import extract_rosters
        root = os.path.dirname(os.path.abspath(__file__))
        self.assertIn("unmarked_hover_audit", extract_rosters(
            os.path.join(root, "mod_state_server.py"))["POST_LOAD_AUDITS"])


if __name__ == "__main__":
    unittest.main()
