"""The Timeline Extended window's full-screen frame, te_fullscreen_block_window
(spec docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 4.1).

Vanilla's fullscreen_block_window (gui/block_windows.gui), as 1.14 has it:
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
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scripts.generators import gen_te_systems_window as gen  # noqa: E402

CLEAR = "onclick = \"[GetVariableSystem.Clear('com_open_window')]\""


def _type(text, name):
    m = re.search(rf"^\ttype {name} = widget \{{$", text, re.M)
    assert m, f"no type {name}"
    depth = 0
    for i in range(m.end() - 1, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[m.start():i + 1]
    raise AssertionError("unclosed")


class FrameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vanilla = _type(gen.VANILLA_FRAMES.read_text(encoding="utf-8-sig"), "fullscreen_block_window")
        cls.ours = _type((ROOT / "gui" / "te_systems_window_generated.gui").read_text(encoding="utf-8-sig"),
                         "te_fullscreen_block_window")

    def test_it_is_vanillas_but_for_the_name_back_and_close(self):
        diff = [ln for ln in difflib.unified_diff(self.vanilla.splitlines(), self.ours.splitlines(), lineterm="", n=0)
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
