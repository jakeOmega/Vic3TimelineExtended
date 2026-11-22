"""The contact sheet's --window preview: the event window's proportions, and
what its text panel leaves clear. The numbers come from a screenshot; these
tests keep the preview and the written rule (docs/guides/event_creation_guide.md,
event_image_prompts.py) telling the same story. Rendering needs Pillow, which
CI's venv does not install, so that test skips without it."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "image_pipeline"))

import contact_sheet  # noqa: E402


class WindowGeometry(unittest.TestCase):
    def test_frame_is_wider_than_the_picture(self):
        # 1700 x 1200 pictures are stretched to the frame, so the frame's
        # proportions, not the picture's, are what a reviewer must see.
        w, h = contact_sheet.window_thumb_size(1120)
        self.assertEqual((w, h), contact_sheet.WINDOW_FRAME)
        self.assertGreater(w / h, 1700 / 1200)

    def test_about_half_the_picture_is_clear(self):
        self.assertEqual(contact_sheet.clear_width(1000), 512)
        self.assertTrue(0.45 <= contact_sheet.PANEL_LEFT <= 0.55)

    def test_the_guide_states_the_same_split(self):
        guide = (ROOT / "docs" / "guides" / "event_creation_guide.md").read_text(encoding="utf-8")
        m = re.search(r"left (\d+)% of the picture", guide)
        self.assertIsNotNone(m, "event_creation_guide.md no longer gives the clear share")
        self.assertEqual(int(m.group(1)), round(contact_sheet.PANEL_LEFT * 100))


class WindowRender(unittest.TestCase):
    def test_panel_darkens_the_right_and_leaves_the_left(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")
        out = contact_sheet.as_in_window(Image.new("RGB", (1700, 1200), "white"), width=400)
        self.assertEqual(out.size, contact_sheet.window_thumb_size(400))
        edge = contact_sheet.clear_width(400)
        self.assertEqual(out.getpixel((edge - 10, 50)), (255, 255, 255))
        self.assertLess(max(out.getpixel((edge + 10, 50))), 80)
        self.assertLess(max(out.getpixel((399, 50))), 80)


if __name__ == "__main__":
    unittest.main()
