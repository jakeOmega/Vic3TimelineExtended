"""The Timeline Extended window's full-screen frame, te_fullscreen_block_window
(spec docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 4.1).

Vanilla's fullscreen_block_window (gui/block_windows.gui), as 1.14 and 1.15 have it:
- a 100% x 100% widget, a clickthrough_blocker, laid out from the screen's
  origin: its own 78 px top filler (the top bar's art, which the real top bar
  draws over) and its content vbox at margin_top = 100, margin_left = 50,
  block "content_margin_right" (45);
- a _show state that ducks the world's sound (snapshot mute_world_80) and a
  0.2 s _hide fade;
- the header: block "window_header_name"; block "back_button_fullscreen"
  around back_button_large, onclick InformationPanelBar.OpenPreviousPanel,
  input_action "back"; close_button_large outside any block, onclick
  InformationPanelBar.ClosePanel, shortcut "close_window";
- then block "fixed_top", block "entire_content_area" around a
  fullscreen_scrollarea (block "scrollarea_content", a horizontal scroll bar
  as needed), block "fixed_bottom".

Its Close does nothing for a scripted widget, which isn't a vanilla panel,
so the mod's copy is generated from the committed fixture by
scripts/generators/gen_te_systems_window.py with three changes: the type's
name, and Back and Close clearing com_open_window as the narrow frame's do.
A vanilla patch that changes the type: replace the fixture, rerun the
generator.
"""
import difflib
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scripts.generators import gen_te_systems_window as gen  # noqa: E402

CLEAR = "onclick = \"[GetVariableSystem.Clear('com_open_window')]\""


def _type(text, name):
    m = re.search(rf"^\ttype {name} = widget \{{$", text, re.M)
    assert m, f"no type {name}"
    return text[m.start():gen._block_end(text, m.end() - 1, name) + 1]


class FrameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vanilla = _type(gen.VANILLA_FRAMES.read_text(encoding="utf-8-sig"), "fullscreen_block_window")
        cls.ours = _type((ROOT / "gui" / "te_systems_window_generated.gui").read_text(encoding="utf-8-sig"),
                         "te_fullscreen_block_window")

    def test_it_is_vanillas_but_for_the_name_back_and_close(self):
        """Line for line, but that a line of vanilla's holding only tabs is empty in ours: the generated file passes
        the tab check (scripts/format_paradox_tabs.py; test_te_systems_window.py holds it to that)."""
        self.assertTrue(any(ln and not ln.strip() for ln in self.vanilla.splitlines()), "vanilla has no such line now")
        vanilla = [ln if ln.strip() else "" for ln in self.vanilla.splitlines()]
        diff = [ln for ln in difflib.unified_diff(vanilla, self.ours.splitlines(), lineterm="", n=0)
                if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
        self.assertEqual(sorted(ln[0] + ln[1:].strip() for ln in diff), sorted([
            "-type fullscreen_block_window = widget {",
            "+type te_fullscreen_block_window = widget {",
            '-onclick = "[InformationPanelBar.OpenPreviousPanel]"',
            f"+{CLEAR}",
            '-onclick = "[InformationPanelBar.ClosePanel]"',
            f"+{CLEAR}",
        ]))

    def test_back_and_close_close_the_window(self):
        back = self.ours[self.ours.index('block "back_button_fullscreen"'):]
        back = back[:back.index("close_button_large")]
        self.assertIn(CLEAR, back)
        self.assertIn('input_action = "back"', back)
        close = self.ours[self.ours.index("close_button_large = {"):]
        close = close[:close.index('block "fixed_top"')]
        self.assertIn(CLEAR, close)
        self.assertIn('shortcut = "close_window"', close)    # Escape closes it
        self.assertNotIn("InformationPanelBar", self.ours)

    def test_it_has_the_blocks_the_window_fills(self):
        for block in ("window_header_name", "fixed_top", "entire_content_area", "fixed_bottom",
                      "content_margin_right", "back_button_fullscreen"):
            self.assertIn(f'block "{block}"', self.ours)
        self.assertIn("fullscreen_scrollarea = {}", self.ours)

    def _frame_of(self, text):
        """fullscreen_frame() on `text` in place of the fixture, without its four comment lines."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "block_windows.gui"
            path.write_text(text, encoding="utf-8")
            with mock.patch.object(gen, "VANILLA_FRAMES", path):
                return [ln for ln in gen.fullscreen_frame() if not ln.startswith("###")]

    def test_a_brace_in_a_comment_or_a_string_is_not_counted(self):
        """The scan for the type's end skips comments and quoted strings: a `}` in either used to end the type
        early, or a `{` to run it on into the next (#1338)."""
        fixture = gen.VANILLA_FRAMES.read_text(encoding="utf-8-sig")
        opener = "\ttype fullscreen_block_window = widget {\n"
        self.assertEqual(fixture.count(opener), 1)
        plain = self._frame_of(fixture)
        for line in ("\t\t# the next type starts at its }", "\t\t# an opener, { left open",
                     '\t\ttooltip = "a } in a string, with a \\" before a second }"', '\t\ttooltip = "#bold {#!"'):
            with self.subTest(line=line):
                self.assertEqual(self._frame_of(fixture.replace(opener, opener + line + "\n")),
                                 [plain[0], line[1:], *plain[1:]])

    def test_a_type_that_never_closes_says_so(self):
        """It raised TypeError, from slicing to None (#1338)."""
        fixture = gen.VANILLA_FRAMES.read_text(encoding="utf-8-sig")
        start = fixture.index("\ttype fullscreen_block_window = widget {")
        cut = fixture[:fixture.index('block "fixed_top"', start)]
        with self.assertRaisesRegex(ValueError, r"block_windows\.gui: fullscreen_block_window is never closed"):
            self._frame_of(cut)

    def test_the_fixture_is_the_installed_file(self):
        base = os.environ.get("VIC3_BASE_GAME")
        if base is None:
            try:
                import path_constants
                base = path_constants.base_game_path
            except Exception:
                base = None
        game = Path(base) / "game" / "gui" / "block_windows.gui" if base else None
        if game is None or not game.is_file():
            self.skipTest("no Victoria 3 install")
        self.assertEqual(gen.VANILLA_FRAMES.read_bytes(), game.read_bytes(),
                         "vanilla changed: replace the fixture and run scripts/generators/gen_te_systems_window.py")


if __name__ == "__main__":
    unittest.main()
