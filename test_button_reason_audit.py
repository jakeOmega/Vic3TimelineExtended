"""Unit tests for button_reason_audit (#1213).

Each fixture is a throwaway mod tree: scripted GUIs, scripted triggers, a
script value, scripted buttons, English loc and one `.gui` file. The crux for
`missing_reason` is where a button's tooltip can come from (its own, a
blockoverride's instance, a type's instances) and what counts as a reason;
for `raw_condition`, what prints raw (variable and script value tests, a
scripted trigger that reaches one), what covers it, and which blocks are
read. Both checks' tags and stale tags are covered.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from button_reason_audit import REPORT_PATH, audit, main, parse_script, regenerate

SGUIS = """\
te_go_sgui = {
\tscope = country
\tis_valid = {
\t\thas_technology_researched = te_tech
\t}
\teffect = { }
}
te_free_sgui = {
\tscope = country
\teffect = { }
}
te_always_sgui = {
\tscope = country
\tis_valid = { always = yes }
}
te_raw_sgui = {
\tscope = country
\tis_valid = {
\t\tvar:te_points > 2
\t\tcustom_tooltip = { text = te_req_tt var:te_other > 0 }
\t\tte_raw_trigger = yes
\t\tte_clean_trigger = yes
\t\ttrigger_if = {
\t\t\tlimit = { has_variable = te_flag }
\t\t\tte_sv >= 3
\t\t}
\t}
}
te_unrendered_sgui = {
\tscope = country
\tis_valid = { has_variable = te_flag }
}
"""

TRIGGERS = """\
te_raw_trigger = {
\tte_inner_trigger = yes
}
te_inner_trigger = {
\thas_global_variable = te_started
}
te_clean_trigger = {
\tcustom_tooltip = { text = te_req_tt has_variable = te_flag }
}
"""

BUTTONS = """\
te_button = {
\tname = te_button
\tpossible = {
\t\thas_variable = te_flag
\t\tNOT = { exists = var:te_target }
\t}
}
te_clean_button = {
\tname = te_clean_button
\tpossible = { custom_tooltip = { text = te_req_tt has_variable = te_flag } }
}
"""

GO = "GetScriptedGui('te_go_sgui')"
SCOPE = "GuiScope.SetRoot( GetPlayer.MakeScope ).End"


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
        _write(self.root, "common/scripted_guis/te_test_sguis.txt", SGUIS)
        _write(self.root, "common/scripted_triggers/te_test_triggers.txt", TRIGGERS)
        _write(self.root, "common/script_values/te_test_values.txt", "te_sv = { value = 1 }\n")
        _write(self.root, "common/scripted_buttons/te_test_buttons.txt", BUTTONS)
        _write(self.root, "localization/english/te_test_l_english.yml", "l_english:\n"
               ' te_req_tt:0 "A requirement"\n'
               ' te_plain_tt:0 "Does a thing"\n'
               f' te_reason_tt:0 "[{GO}.IsValidTooltip( {SCOPE} )]"\n')

    def gui(self, body: str, name: str = "te_test.gui") -> None:
        _write(self.root, f"gui/{name}", body)

    def missing(self):
        return [(f.line, f.owner) for f in audit(self.root).flags if f.check == "missing_reason"]

    def raw(self):
        return [(f.file, f.line, f.owner, f.detail) for f in audit(self.root).flags
                if f.check == "raw_condition"]


class ParseTests(unittest.TestCase):
    def test_operators_and_lines(self):
        stmts = parse_script("a = {\n\tvar:x >= 3\n\tb != c\n}\n")
        self.assertEqual([(s.key, s.op, s.value, s.line) for s in stmts[0].children],
                         [("var:x", ">=", "3", 2), ("b", "!=", "c", 3)])


class MissingReasonTests(_Fixture):
    def test_execute_tooltip_only_is_flagged(self):
        self.gui('button = {\n'
                 f'\tenabled = "[{GO}.IsValid( {SCOPE} )]"\n'
                 f'\ttooltip = "[{GO}.ExecuteTooltip( {SCOPE} )]"\n'
                 '}\n')
        r = audit(self.root)
        self.assertEqual([(f.file, f.line, f.owner) for f in r.flags if f.check == "missing_reason"],
                         [("gui/te_test.gui", 2, "te_go_sgui")])

    def test_is_valid_tooltip_gives_the_reason_directly_or_through_loc(self):
        for tooltip in (f"[Concatenate( {GO}.IsValidTooltip( {SCOPE} ), Localize('te_plain_tt') )]",
                        "te_reason_tt"):
            with self.subTest(tooltip=tooltip):
                self.gui(f'button = {{ enabled = "[{GO}.IsValid( {SCOPE} )]" tooltip = "{tooltip}" }}\n')
                self.assertEqual(self.missing(), [])

    def test_a_tooltip_branching_on_is_valid_gives_its_own_reason(self):
        self.gui(f'button = {{ enabled = "[{GO}.IsValid( {SCOPE} )]" '
                 f'tooltip = "[SelectLocalization( {GO}.IsValid( {SCOPE} ), \'te_plain_tt\', \'te_req_tt\' )]" }}\n')
        self.assertEqual(self.missing(), [])

    def test_no_is_valid_or_always_yes_never_greys(self):
        self.gui('button = { enabled = "[GetScriptedGui(\'te_free_sgui\').IsValid( GuiScope.End )]" }\n'
                 'button = { enabled = "[GetScriptedGui(\'te_always_sgui\').IsValid( GuiScope.End )]" }\n')
        self.assertEqual(self.missing(), [])

    def test_no_tooltip_at_all_is_flagged(self):
        self.gui(f'button = {{ enabled = "[{GO}.IsValid( {SCOPE} )]" }}\n')
        self.assertEqual(self.missing(), [(1, "te_go_sgui")])

    def test_datacontext_names_the_scripted_gui(self):
        self.gui('button = {\n'
                 '\tdatacontext = "[GetScriptedGui(\'te_free_sgui\')]"\n'
                 '\tenabled = "[ScriptedGui.IsValid( GuiScope.End )]"\n'
                 '}\n'
                 'button = {\n'
                 f'\tdatacontext = "[{GO}]"\n'
                 '\tenabled = "[ScriptedGui.IsValid( GuiScope.End )]"\n'
                 '}\n')
        self.assertEqual(self.missing(), [(7, "te_go_sgui")])

    def test_enabled_in_a_blockoverride_reads_the_instance(self):
        self.gui('te_row = {\n'
                 f'\tblockoverride "go" {{ enabled = "[{GO}.IsValid( {SCOPE} )]" }}\n'
                 '\tblockoverride "go_tooltip" { tooltip = "te_reason_tt" }\n'
                 '}\n'
                 'te_row = {\n'
                 f'\tblockoverride "go" {{ enabled = "[{GO}.IsValid( {SCOPE} )]" }}\n'
                 '\tblockoverride "go_tooltip" { tooltip = "te_plain_tt" }\n'
                 '}\n')
        self.assertEqual(self.missing(), [(6, "te_go_sgui")])

    def test_enabled_in_a_type_is_judged_per_instance(self):
        self.gui('types t {\n'
                 '\ttype te_choice = button {\n'
                 '\t\tblock "context" {}\n'
                 '\t\tenabled = "[ScriptedGui.IsValid( GuiScope.End )]"\n'
                 '\t\tblock "tip" {}\n'
                 '\t}\n'
                 '}\n'
                 f'te_choice = {{ blockoverride "context" {{ datacontext = "[{GO}]" }} '
                 'blockoverride "tip" { tooltip = "te_reason_tt" } }\n'
                 f'te_choice = {{ blockoverride "context" {{ datacontext = "[{GO}]" }} '
                 'blockoverride "tip" { tooltip = "te_plain_tt" } }\n'
                 'te_choice = { blockoverride "context" { datacontext = "[GetScriptedGui(\'te_free_sgui\')]" } '
                 'blockoverride "tip" { tooltip = "te_plain_tt" } }\n')
        r = audit(self.root)
        flags = [f for f in r.flags if f.check == "missing_reason"]
        self.assertEqual([(f.line, f.owner) for f in flags], [(4, "te_go_sgui")])
        self.assertIn("in 1 instance(s): `gui/te_test.gui:9`", flags[0].detail)

    def test_vanilla_is_valid_and_debug_files_are_not_read(self):
        self.gui('button = { enabled = "[IsValid( GetPlayer.ToggleSomething )]" }\n')
        self.gui(f'button = {{ enabled = "[{GO}.IsValid( {SCOPE} )]" }}\n', name="te_debug_x.gui")
        self.assertEqual(self.missing(), [])


class RawConditionTests(_Fixture):
    def setUp(self):
        super().setUp()
        self.gui(f'button = {{ tooltip = "[GetScriptedGui(\'te_raw_sgui\').IsValidTooltip( {SCOPE} )]" }}\n')

    def test_raw_tests_in_a_rendered_is_valid(self):
        rows = [r for r in self.raw() if r[2] == "te_raw_sgui is_valid"]
        self.assertEqual(len(rows), 1)
        file, line, _owner, detail = rows[0]
        self.assertEqual((file, line), ("common/scripted_guis/te_test_sguis.txt", 18))
        self.assertIn("line 19: `var:te_points > 2`", detail)
        self.assertIn("line 21: `te_raw_trigger = yes` reaches `has_global_variable = te_started`", detail)
        self.assertIn("line 25: `te_sv >= 3`", detail)
        # Covered: the custom_tooltip, the clean trigger, the trigger_if's limit.
        self.assertNotIn("te_other", detail)
        self.assertNotIn("te_clean_trigger", detail)
        self.assertNotIn("te_flag", detail)

    def test_unrendered_scripted_gui_is_not_read(self):
        self.assertFalse(any(r[2].startswith("te_unrendered_sgui") for r in self.raw()))

    def test_datacontext_in_a_file_using_scripted_gui_is_valid_tooltip_renders(self):
        self.gui('widget = {\n'
                 '\tdatacontext = "[GetScriptedGui(\'te_unrendered_sgui\')]"\n'
                 '\tbutton = { tooltip = "[ScriptedGui.IsValidTooltip( GuiScope.End )]" }\n'
                 '}\n', name="te_other.gui")
        self.assertTrue(any(r[2] == "te_unrendered_sgui is_valid" for r in self.raw()))

    def test_scripted_button_possible(self):
        rows = {r[2]: r for r in self.raw()}
        self.assertIn("te_button possible", rows)
        self.assertIn("`has_variable = te_flag`", rows["te_button possible"][3])
        self.assertIn("`exists = var:te_target`", rows["te_button possible"][3])
        self.assertNotIn("te_clean_button possible", rows)

    def test_a_scripted_button_only_the_ai_sees_is_not_read(self):
        # `is_ai = yes` at the top of `visible` (an AND) hides the button from
        # every player; nested in an OR it does not.
        _write(self.root, "common/scripted_buttons/te_test_buttons.txt", BUTTONS + """\
te_ai_button = {
\tvisible = {
\t\tis_ai = yes
\t\thas_variable = te_flag
\t}
\tpossible = { has_variable = te_flag }
}
te_either_button = {
\tvisible = {
\t\tOR = { is_ai = yes has_variable = te_flag }
\t}
\tpossible = { has_variable = te_flag }
}
""")
        r = audit(self.root)
        owners = {f.owner for f in r.flags if f.check == "raw_condition"}
        self.assertNotIn("te_ai_button possible", owners)
        self.assertIn("te_either_button possible", owners)
        self.assertIn("te_button possible", owners)
        self.assertEqual(r.ai_only_skipped, 1)


class SuppressionTests(_Fixture):
    def test_missing_reason_tag_on_the_enabled_line(self):
        self.gui('button = {\n'
                 f'\tenabled = "[{GO}.IsValid( {SCOPE} )]" # REVIEWED 2026-10-27 (missing_reason): obvious\n'
                 '}\n')
        r = audit(self.root)
        flags = [f for f in r.flags if f.check == "missing_reason"]
        self.assertEqual(flags[0].exemption, {"date": "2026-10-27", "rationale": "obvious"})

    def test_raw_condition_tag_on_the_block_line_and_stale_tags(self):
        _write(self.root, "common/scripted_buttons/te_test_buttons.txt", BUTTONS.replace(
            "\tpossible = {\n\t\thas_variable",
            "\tpossible = { # REVIEWED 2026-10-27 (raw_condition): debug only\n\t\thas_variable").replace(
            "\tname = te_clean_button\n",
            "\tname = te_clean_button # REVIEWED 2026-10-27 (raw_condition): nothing here\n"))
        self.gui('widget = { }\n')
        r = audit(self.root)
        button = [f for f in r.flags if f.owner == "te_button possible"][0]
        self.assertEqual(button.exemption["rationale"], "debug only")
        self.assertEqual([(t.check, t.line) for t in r.stale_tags], [("raw_condition", 9)])

    def test_a_tag_for_the_other_check_is_stale(self):
        self.gui('button = {\n'
                 f'\tenabled = "[{GO}.IsValid( {SCOPE} )]" # REVIEWED 2026-10-27 (raw_condition): wrong check\n'
                 '}\n')
        r = audit(self.root)
        self.assertIsNone([f for f in r.flags if f.check == "missing_reason"][0].exemption)
        self.assertEqual([(t.check, t.file) for t in r.stale_tags], [("raw_condition", "gui/te_test.gui")])


class CliTests(_Fixture):
    def test_strict_and_regenerate(self):
        self.gui(f'button = {{ enabled = "[{GO}.IsValid( {SCOPE} )]" }}\n')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["--strict", "--mod-path", self.root]), 1)
        self.assertIn("`te_go_sgui`", out.getvalue())
        with mock.patch("path_constants.mod_path", self.root):
            summary = regenerate(None)
        self.assertEqual((summary["missing_reason"], summary["raw_condition"]), (1, 1))
        self.assertTrue(os.path.isfile(os.path.join(self.root, REPORT_PATH)))


class RepoTests(unittest.TestCase):
    def test_runs_over_the_mod(self):
        from path_constants import mod_path
        result = audit(mod_path)
        self.assertGreater(result.buttons_checked, 100)
        self.assertGreater(result.blocks_checked, 50)

    def test_post_load_roster(self):
        from scripts.analysis.check_post_load_rosters import extract_rosters
        root = os.path.dirname(os.path.abspath(__file__))
        self.assertIn("button_reason_audit", extract_rosters(
            os.path.join(root, "mod_state_server.py"))["POST_LOAD_AUDITS"])


if __name__ == "__main__":
    unittest.main()
