"""reframe_event_image.py: the two edits that move a picture's subject into
the half of the event window the player sees. The picture tests need Pillow,
which CI's venv may not install, so they skip without it."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "image_pipeline"))

import contact_sheet  # noqa: E402
import reframe_event_image as reframe  # noqa: E402

try:
    from PIL import Image
except ImportError:  # pragma: no cover - CI without Pillow
    Image = None


class ShiftLimit(unittest.TestCase):
    def test_the_reflected_fill_stays_under_the_text_panel(self):
        # The fill starts at 1 - shift of the width; the panel at PANEL_LEFT.
        self.assertGreater(1 - reframe.MAX_SHIFT, contact_sheet.PANEL_LEFT)


@unittest.skipIf(Image is None, "Pillow is not installed")
class Edits(unittest.TestCase):
    def picture(self):
        """100 x 10, black, with a white column at x = 50 and a red one at x = 90."""
        im = Image.new("RGB", (100, 10), "black")
        for y in range(10):
            im.putpixel((50, y), (255, 255, 255))
            im.putpixel((90, y), (255, 0, 0))
        return im

    def test_mirror_moves_the_right_to_the_left(self):
        out = reframe.mirror(self.picture())
        self.assertEqual(out.size, (100, 10))
        self.assertEqual(out.getpixel((49, 5)), (255, 255, 255))
        self.assertEqual(out.getpixel((9, 5)), (255, 0, 0))

    def test_shift_moves_the_subject_left_and_keeps_the_size(self):
        out = reframe.shift_left(self.picture(), 0.2)
        self.assertEqual(out.size, (100, 10))
        self.assertEqual(out.getpixel((30, 5)), (255, 255, 255))
        self.assertEqual(out.getpixel((50, 5)), (0, 0, 0))
        self.assertEqual(out.getpixel((70, 5)), (255, 0, 0))

    def test_shift_fills_the_right_with_the_edge_reflected(self):
        # The source's last 20 columns (80..99, red at 90) are mirrored into
        # the output's last 20, so the red column lands at 80 + (99 - 90).
        out = reframe.shift_left(self.picture(), 0.2)
        self.assertEqual(out.getpixel((89, 5)), (255, 0, 0))
        self.assertEqual(out.getpixel((95, 5)), (0, 0, 0))

    def test_shift_is_capped(self):
        with self.assertRaises(ValueError):
            reframe.shift_left(self.picture(), reframe.MAX_SHIFT + 0.01)
        with self.assertRaises(ValueError):
            reframe.shift_left(self.picture(), 0)

    def test_mirror_runs_before_shift(self):
        out = reframe.reframe(self.picture(), do_mirror=True, shift=0.05)
        # Mirrored, red is at 9; shifted left by 5, at 4.
        self.assertEqual(out.getpixel((4, 5)), (255, 0, 0))


if __name__ == "__main__":
    unittest.main()
