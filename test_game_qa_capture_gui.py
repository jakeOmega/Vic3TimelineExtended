"""`game_qa/capture_gui.py`: the capture copies of the game's console and error widget, and the view's widgets (#2056).

The game's own files are not in the repo, so the tests use invented ones holding the lines the edits look for, with
decoys beside them (the error widget's inner button has the same `visible` line as its root).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game_qa import capture_gui as cg
from game_qa import gui_preview

CONSOLE = (
    "template editor_text\n{\n\tfontsize = 15\n}\n\n"
    "template ConsoleBackground\n{\n\tusing = clickthrough_blocker\n\n\ttexture = \"bg.dds\"\n"
    "\tmodify_texture = {\n\t\tusing = bg_tiling_pattern\n\t\talpha = 0.065\n\t}\n}\n\n"
    "template console_frame\n{\n\ttexture = \"frame.dds\"\n}\n\n"
    "flowcontainer = {\n\tname = \"console_window\"\n\talwaystransparent = no\n\tscissor = no\n\tlayer = confirmation\n"
    "\tusing = clickthrough_blocker\n\n\tmargin = { 10 10 }\n\n"
    "\tflowcontainer = {\n\t\tdirection = vertical\n\t\tspacing = 4\n\t\tbackground = {\n\t\t\tusing = ConsoleBackground\n"
    "\t\t\tmargin = { 8 8 }\n\t\t}\n\n"
    "\t\tscrollarea = {\n\t\t\tname = \"console_output_scrollarea\"\n\t\t\tsize = { 408 550 }\n\t\t}\n\n"
    "\t\teditbox = {\n\t\t\tbackground = {\n\t\t\t\tusing = ConsoleEditbg\n\t\t\t\tmargin = { 4 0 }\n\t\t\t}\n\n"
    "\t\t\tname = \"console_edit\"\n\t\t\tsize = { 408 40 }\n\t\t}\n\n"
    "\t\tflowcontainer = {\n\t\t\tname = \"toolbars_window\"\n\t\t\tmargin = { 1 10 }\n\t\t}\n\t}\n}\n"
)
ERROR_DEER = (
    "widget = {\n\tname = \"error_deer\"\n\tparentanchor = bottom|hcenter\n\tposition = { 500 -50 }\n"
    "\tvisible = \"[InDebugMode]\"\n\tlayer = layer_error_deer\n\tusing = clickthrough_blocker\n\n"
    "\tflowcontainer = {\n\t\tbutton = {\n\t\t\tsize = { 0 0 }\n\t\t\tvisible = \"[InDebugMode]\"\n\t\t}\n"
    "\t\ttextbox = {\n\t\t\tname = \"debug_current_fps\"\n\t\t\traw_text = \"FPS: [GetCurrentFps|0]\"\n\t\t}\n\t}\n}\n"
)


def edit_line(text: str) -> str:
    """The editbox's block, from its opening to the console_edit name."""
    start = text.index("\t\teditbox = {")
    return text[start:text.index('name = "console_edit"', start)]


class ConsoleTest(unittest.TestCase):
    def test_the_capture_console_draws_nothing_and_keeps_the_edit_line_in_place(self):
        out = cg.capture_console(cg.BOM + CONSOLE.encode()).decode("utf-8-sig")
        self.assertNotIn("clickthrough_blocker", out)
        self.assertIn('name = "console_window"\n\talwaystransparent = yes', out)
        self.assertIn("spacing = 4\n\t\tignoreinvisible = no", out, "hidden children keep their room, or the edit "
                      "line moves off the point click --console presses")
        line = edit_line(out)
        self.assertIn("\t\t\talpha = 0\n", line, "the editbox's own alpha, which its text and caret take")
        self.assertIn("\t\t\t\talpha = 0\n", line, "and its background's")
        self.assertNotIn("alpha = 0.5", out)
        self.assertIn('name = "console_edit"\n\t\t\tsize = { 408 40 }', out, "the edit line itself is untouched")
        self.assertNotIn("alwaystransparent = yes", line, "the edit line still takes the click and the hover")
        self.assertEqual(out.count("{"), out.count("}"))

    def test_the_see_through_console_keeps_its_faint_edit_line(self):
        out = cg.see_through_console(CONSOLE.encode()).decode()
        line = edit_line(out)
        self.assertIn("alpha = 0.5", line)
        self.assertNotIn("\t\t\talpha = 0\n", line)

    def test_bom_and_line_endings_are_kept(self):
        self.assertTrue(cg.capture_console(cg.BOM + CONSOLE.encode()).startswith(cg.BOM))
        self.assertFalse(cg.capture_console(CONSOLE.encode()).startswith(cg.BOM))
        crlf = cg.capture_console(CONSOLE.replace("\n", "\r\n").encode())
        self.assertEqual(crlf.count(b"\r\n"), crlf.count(b"\n"))

    def test_a_moved_line_stops_it(self):
        for old, _new, _count in cg.SEE_THROUGH_EDITS + (cg.HIDDEN_EDIT_LINE,):
            with self.subTest(old=old[:40]):
                with self.assertRaises(cg.CaptureGuiError) as caught:
                    cg.capture_console(CONSOLE.replace(old, "", 1).encode())
                self.assertEqual(caught.exception.code, "capture_gui_changed")


class ErrorDeerTest(unittest.TestCase):
    def test_only_the_root_is_gated_on_the_capture_key(self):
        out = cg.gated_error_deer(ERROR_DEER.encode()).decode()
        root = "\tvisible = \"[And( InDebugMode, Not( GetVariableSystem.Exists( 'te_qa_capture' ) ) )]\"\n"
        self.assertEqual(out.count(root), 1)
        self.assertIn(root + "\tlayer = layer_error_deer", out)
        self.assertIn("\t\t\tvisible = \"[InDebugMode]\"\n", out, "the inner button's line is the decoy, left alone")
        self.assertEqual(out.count("{"), out.count("}"))

    def test_a_moved_root_line_stops_it(self):
        with self.assertRaises(cg.CaptureGuiError):
            cg.gated_error_deer(ERROR_DEER.replace("\tlayer = layer_error_deer\n", "").encode())

    def test_capture_files_reads_both_from_the_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)
            (game / "game" / "gui").mkdir(parents=True)
            (game / cg.CONSOLE_SOURCE).write_bytes(cg.BOM + CONSOLE.encode())
            with self.assertRaises(cg.CaptureGuiError) as caught:
                cg.capture_files(game)
            self.assertEqual(caught.exception.code, "capture_gui_missing")
            (game / cg.ERROR_DEER_SOURCE).write_bytes(ERROR_DEER.encode())
            files = cg.capture_files(game)
            self.assertEqual(sorted(files), [cg.CONSOLE_FILE, cg.ERROR_DEER_FILE])
            self.assertIn(b"te_qa_capture", files[cg.ERROR_DEER_FILE])


class DebugGateTest(unittest.TestCase):
    SOURCE = ("widget = {\n"
              '\tvisible = "[InDebugMode]"\n'
              "\ttext = { visible = [InDebugMode] }\n"
              "\tbox = {\n\t\tvisible = [InDebugMode]\n\t}\n"
              '\tother = {\n\t\tvisible = "[And(InDebugMode, Not(StringIsEmpty(Market.GetModifierDesc)))]" # why\n\t}\n'
              '\traw_text = "InDebugMode"\n'
              '\tvisible = "[IsInDebugModeLike]"\n'
              "}\n")

    def test_every_visible_line_naming_it_needs_the_key_unset_too(self):
        out, changed = cg.gate_debug_lines(self.SOURCE.encode())
        text = out.decode()
        self.assertEqual(changed, 3, "the line holding a whole block is not a visible line, and is left")
        self.assertIn('\tvisible = "[%s]"\n' % cg.GATED_DEBUG, text)
        self.assertIn('\t\tvisible = "[%s]"\n' % cg.GATED_DEBUG, text, "an unquoted one is quoted")
        self.assertIn('\t\tvisible = "[And(%s, Not(StringIsEmpty(Market.GetModifierDesc)))]" # why\n' % cg.GATED_DEBUG,
                      text)
        self.assertIn('\traw_text = "InDebugMode"\n', text)
        self.assertIn('\tvisible = "[IsInDebugModeLike]"\n', text, "a longer name is not the trigger")
        self.assertIn(cg.CAPTURE_KEY, cg.GATED_DEBUG)

    def test_the_bom_and_line_endings_are_kept(self):
        source = cg.BOM + self.SOURCE.replace("\n", "\r\n").encode()
        out, _ = cg.gate_debug_lines(source)
        self.assertTrue(out.startswith(cg.BOM))
        self.assertEqual(out.count(b"\r\n"), source.count(b"\r\n"))

    def test_the_mods_copy_is_gated_where_it_ships_one_and_a_file_with_none_is_left_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, deploy = Path(tmp) / "game_install", Path(tmp) / "deploy"
            (base / "game" / "gui").mkdir(parents=True)
            (deploy / "gui").mkdir(parents=True)
            (base / "game" / "gui" / "journal_entry.gui").write_text('a = {\n\tvisible = "[InDebugMode]"\n}\n')
            (deploy / "gui" / "journal_entry.gui").write_text('mod = {\n\tvisible = "[InDebugMode]"\n}\n')
            (base / "game" / "gui" / "eventwindow.gui").write_text('b = {\n\tvisible = "[InDebugMode]"\n}\n')
            (base / "game" / "gui" / "tooltip.gui").write_text("c = {\n}\n")
            out = cg.debug_gated_files(base, deploy)
            self.assertEqual(sorted(out), ["gui/eventwindow.gui", "gui/journal_entry.gui"])
            self.assertTrue(out["gui/journal_entry.gui"].startswith(b"mod = {"), "the mod's, the build under test")
            self.assertIn(cg.CAPTURE_KEY.encode(), out["gui/eventwindow.gui"])


class ActionTest(unittest.TestCase):
    def test_each_form_and_its_binding(self):
        cases = {
            "set:com_open_window=te_systems_window": "GetVariableSystem.Set( 'com_open_window', 'te_systems_window' )",
            "clear:te_systems_window_wide": "GetVariableSystem.Clear( 'te_systems_window_wide' )",
            "panel:military": "InformationPanelBar.OpenPanel( 'military' )",
            "panel:budget:te_banking": "InformationPanelBar.OpenPanelTab( 'budget', 'te_banking' )",
            "panel:tech_tree:production|military": "InformationPanelBar.OpenPanelTab( 'tech_tree', "
                                                   "'production|military' )",
            "market:te_global_warming": "InformationPanelBar.OpenMarketPanelTab( AccessPlayer.AccessFirstMarket.Self, "
                                        "'te_global_warming' )",
            "close-panel": "InformationPanelBar.ClosePanel",
            "construction": "InformationPanelBar.OpenConstructionPanel( GetPlayer.Self )",
            "construction:ships": "InformationPanelBar.OpenConstructionPanelTab( GetPlayer.Self, 'ships' )",
            "state:capital": "InformationPanelBar.OpenStatePanel( AccessPlayer.AccessCapital )",
            "zoom:capital": "AccessPlayer.AccessCapital.ZoomToCapital",
            "je:je_te_map_room": "InformationPanelBar.OpenJournalEntryPanel( GetPlayerJournalEntry('je_te_map_room')"
                                 ".AccessSelf )",
            "sgui:te_jmap_pick_leading_cause_sgui": "GetScriptedGui('te_jmap_pick_leading_cause_sgui').Execute( "
                                                    "GuiScope.SetRoot( GetPlayer.MakeScope ).End )",
        }
        for text, binding in cases.items():
            with self.subTest(text=text):
                self.assertEqual(cg.parse_action(text).binding, binding)

    def test_anything_else_is_refused(self):
        for text in ("set:a", "set:a=b c", "set:a='x'", "clear:", "panel:", "panel:a:b:c", "market:", "raw:x",
                     "ExecuteConsoleCommand('save')", "set:a=b]", "close-panel:x", "construction:", "construction:a b",
                     "state:FRA", "state:", "zoom:map", "je:", "je:a b", "sgui:x_sgui", "sgui:te_x", "sgui:te_a b_sgui",
                     7, None):
            with self.subTest(text=text):
                with self.assertRaises(cg.CaptureGuiError) as caught:
                    cg.parse_action(text)
                self.assertEqual(caught.exception.code, "bad_action")

    def test_steps(self):
        self.assertEqual(len(cg.parse_steps([["close-panel"], ["panel:budget"]])), 2)
        for steps in ([], "close-panel", [[]], [["close-panel"]] * (cg.MAX_STEPS + 1), [["x"]],
                      [["close-panel"] * (cg.MAX_ACTIONS + 1)], [["close-panel"], "panel:budget"]):
            with self.subTest(steps=steps):
                with self.assertRaises(cg.CaptureGuiError):
                    cg.parse_steps(steps)


class WrapperTest(unittest.TestCase):
    def test_one_widget_a_step_each_running_its_actions_on_create_and_the_token(self):
        steps = cg.parse_steps([["clear:a", "close-panel"], ["set:b=c", "panel:budget:te_banking"]])
        text = cg.view_wrapper_text(steps, 7)
        self.assertEqual(text.count("{"), text.count("}"))
        for i, step in enumerate(steps):
            name = 'name = "%s"' % (cg.VIEW_WIDGET % i)
            self.assertIn(name, text)
            block = text[text.index(name):]
            block = block[:block.index("\n}\n")]
            self.assertIn("trigger_on_create = yes", block)
            for action in step:
                self.assertIn('on_start = "[%s]"' % action.binding, block)
        self.assertNotIn(cg.VIEW_WIDGET % 2, text)
        self.assertEqual(gui_preview.rev_in("Unlocalized text 'te_qa_rev_7' at %s:30" % gui_preview.PREVIEW_FILE), 7)
        self.assertIn('text = "te_qa_rev_7"', text)
        token = text[text.index('name = "%s"' % cg.VIEW_TOKEN_WIDGET):]
        self.assertIn('text = "te_qa_rev_7"', token, "the token sits in a widget of its own, never created")
        self.assertNotIn("on_start", token)


if __name__ == "__main__":
    unittest.main()
