"""Tests for the Workshop screenshot annotator (scripts/image_pipeline/workshop_screenshots.py).

The specs are checked as data (no Pillow needed). The render test draws a
synthetic screenshot with Pillow's own font, so it needs neither the game's
fonts nor the original screenshots, and skips where Pillow is missing.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

MOD_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(MOD_ROOT / "scripts" / "image_pipeline"))

import workshop_screenshot_specs as specs  # noqa: E402

try:
    from PIL import Image, ImageFont

    ImageFont.load_default(size=12)  # Pillow 10.1+ with FreeType
    HAVE_PIL = True
except (ImportError, TypeError, OSError):
    HAVE_PIL = False


class SpecTests(unittest.TestCase):
    def test_every_spec_is_well_formed(self):
        problems = [f"{name}: {p}" for name, spec in specs.SPECS.items() for p in specs.validate(spec)]
        self.assertEqual(problems, [])

    def test_validate_catches_mistakes(self):
        bad = dict(src="x.png", title="T", colum=600,
                   callouts=[dict(box=(10, 10, 5, 50), pt=(1, 1), title="A", to="left")])
        found = " | ".join(specs.validate(bad))
        for expected in ("unknown key 'colum'", "exactly one of 'box' or 'pt'",
                         "is not (x0, y0, x1, y1)", "to 'left'", "no 'column' or 'column_region'"):
            self.assertIn(expected, found)

    def test_no_future_years_in_the_text(self):
        # Owner, 2026-11-06: no dates for the speculative eras.
        import re
        for name, spec in specs.SPECS.items():
            texts = [spec["title"], spec.get("subtitle", "")]
            texts += [co.get(k, "") for co in spec.get("callouts", []) for k in ("title", "body")]
            texts += [st.get("big", "") for st in spec.get("stats", [])]
            texts += [line for st in spec.get("stats", []) for line in st.get("lines", [])]
            for t in texts:
                self.assertIsNone(re.search(r"\b2[0-9]{3}\b", t), f"{name}: a future year in {t!r}")


@unittest.skipUnless(HAVE_PIL, "Pillow 10.1+ with FreeType not installed")
class RenderTests(unittest.TestCase):
    def setUp(self):
        import workshop_screenshots as ws
        self.ws = ws
        ws.FONT_DIR = None  # Pillow's default font: no game install needed

    def test_callouts_number_top_to_bottom(self):
        cos = [dict(box=(0, 500, 10, 510)), dict(pt=(300, 20)), dict(box=(50, 20, 60, 30))]
        order = [co.get("box", co.get("pt")) for co in self.ws.reading_order(cos)]
        self.assertEqual(order, [(50, 20, 60, 30), (300, 20), (0, 500, 10, 510)])

    def test_render_and_export(self):
        shot = Image.new("RGB", (900, 600), (60, 70, 80))
        spec = dict(
            src="synthetic.png", title="Test System", subtitle="a one-line pitch", u=0.8, column=400,
            callouts=[
                dict(box=(20, 300, 400, 380), title="Lower", body="Second by position"),
                dict(box=(20, 40, 400, 120), title="Upper", body="First by position"),
                dict(pt=(700, 500), at=(500, 300), w=300, title="Placed", body="With an arrow"),
            ],
            stats=[dict(at=(500, 40), w=300, big="123 things", lines=["and more"])],
        )
        self.assertEqual(specs.validate(spec), [])
        img = self.ws.render(spec, shot)
        self.assertEqual(img.width, 900 + 400)
        self.assertGreater(img.height, 600)  # the header sits above the shot
        with tempfile.TemporaryDirectory() as d:
            q, size = self.ws.export(img, Path(d) / "out.jpg")
            self.assertLess(size, self.ws.SIZE_LIMIT)


if __name__ == "__main__":
    unittest.main()
