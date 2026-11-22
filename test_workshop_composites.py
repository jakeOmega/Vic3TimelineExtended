"""Tests for the Workshop composites (scripts/image_pipeline/workshop_composites.py).

The counts are checked against the figures the published Workshop screenshots give
(workshop_screenshot_specs.py), so a stale figure fails here instead of on the store page
(the laws image said 165 for a week: a count that skipped `law_post-scarcity`). The render
test draws every image with gray stand-in pictures and Pillow's own font, so it needs neither
gfx/ (CI checks out without it) nor the game.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

MOD_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(MOD_ROOT / "scripts" / "image_pipeline"))

try:
    from PIL import Image, ImageFont

    ImageFont.load_default(size=12)  # Pillow 10.1+ with FreeType
    HAVE_PIL = True
except (ImportError, TypeError, OSError):
    HAVE_PIL = False

if HAVE_PIL:
    import workshop_composites as wc
    import workshop_screenshot_specs as specs


@unittest.skipUnless(HAVE_PIL, "needs Pillow 10.1+")
class CountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.counts = wc.mod_counts(MOD_ROOT)

    def test_published_figures_match_the_files(self):
        c = self.counts
        laws = specs.SPECS["09_laws"]
        self.assertEqual(laws["title"], f"{c['laws']} New Laws")
        self.assertEqual(laws["subtitle"], f"and {c['law_groups']} new law groups")
        tech = specs.SPECS["10_technology"]["stats"][0]
        self.assertEqual(tech["big"], f"{c['techs']} new technologies")
        eras = sorted(c["techs_by_era"])
        self.assertEqual(tech["lines"][0], f"in eras {wc.ROMAN[eras[0]]} to {wc.ROMAN[eras[-1]]},")

    def test_every_era_has_a_row(self):
        self.assertEqual(set(wc.ERAS), set(self.counts["techs_by_era"]))
        self.assertEqual(sum(self.counts["techs_by_era"].values()), self.counts["techs"])

    def test_counts_find_something_of_each(self):
        for key in ("techs", "laws", "law_groups", "events", "wonders", "megaprojects", "pictures"):
            self.assertGreater(self.counts[key], 0, key)

    def test_a_key_may_hold_a_hyphen(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "laws.txt"
            f.write_text("law_post-scarcity = {\n\tgroup = lawgroup_welfare\n}\n"
                         "INJECT:law_x = {\n}\n# commented = {\n", encoding="utf-8")
            self.assertEqual(list(wc._entries("*.txt", Path(tmp))), ["law_post-scarcity"])

    def test_the_system_images_hold_every_system(self):
        held = [s for a, b in wc.SYSTEM_IMAGES for s in wc.SYSTEMS[a:b]]
        self.assertEqual(held, wc.SYSTEMS)


@unittest.skipUnless(HAVE_PIL, "needs Pillow 10.1+")
class RenderTests(unittest.TestCase):
    def test_every_image_draws(self):
        counts = wc.mod_counts(MOD_ROOT)
        gray = Image.new("RGB", (1020, 500), (120, 120, 120))
        saved = wc.pic, wc.ws.FONT_DIR
        wc.pic = lambda key: gray
        wc.ws.FONT_DIR = None  # Pillow's default font
        try:
            for name, (_builder, desc) in wc.BUILDERS.items():
                for stem, img in wc.render(name, counts):
                    with self.subTest(image=stem):
                        if desc:
                            self.assertEqual(img.width, wc.DW)  # twice the 630 px Steam shows
                        else:
                            self.assertGreater(img.width, 1800)
                        self.assertGreater(img.height, 100)
        finally:
            wc.pic, wc.ws.FONT_DIR = saved


if __name__ == "__main__":
    unittest.main()
