"""convert_company_icon.fit_to_square copies a logo onto its square canvas as
it is (#246).

It pasted the logo with itself as the mask, which on an empty canvas squares
every soft edge's alpha and darkens its color toward black: a pixel of
(200, 100, 50, 128) came out (100, 50, 25, 64).
"""

import os
import sys
import unittest

MOD_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MOD_ROOT, "scripts", "image_pipeline"))

try:
    from PIL import Image

    import convert_company_icon as cci
except ImportError:  # CI installs no Pillow
    cci = None


@unittest.skipIf(cci is None, "Pillow is not installed")
class FitToSquareTests(unittest.TestCase):
    HALF = (200, 100, 50, 128)

    def test_a_half_alpha_pixel_keeps_its_color_and_alpha(self):
        src = Image.new("RGBA", (cci.ICON_SIZE, cci.ICON_SIZE), self.HALF)
        out = cci.fit_to_square(src)
        self.assertEqual(out.size, (cci.ICON_SIZE, cci.ICON_SIZE))
        self.assertEqual(out.getpixel((cci.ICON_SIZE // 2, cci.ICON_SIZE // 2)), self.HALF)

    def test_a_banner_is_centered_unscaled_on_a_transparent_canvas(self):
        size = cci.ICON_SIZE
        src = Image.new("RGBA", (size, size // 2), self.HALF)
        out = cci.fit_to_square(src)
        top = size // 4
        self.assertEqual(out.getpixel((size // 2, size // 2)), self.HALF)
        self.assertEqual(out.getpixel((0, top)), self.HALF)
        self.assertEqual(out.getpixel((size // 2, top - 1))[3], 0)
        self.assertEqual(out.getpixel((size // 2, top + size // 2))[3], 0)


if __name__ == "__main__":
    unittest.main()
