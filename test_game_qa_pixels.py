"""Tests for game_qa.pixels: reading the helper's own screenshots."""

import unittest

from game_qa import pixels, win_helper


def image(width, height, colour, patch=None):
    """An RGB picture of one colour, with `patch` ((left, top, right, bottom), colour) painted over it."""
    rows = []
    for y in range(height):
        for x in range(width):
            inside = patch and patch[0][0] <= x < patch[0][2] and patch[0][1] <= y < patch[0][3]
            rows.append(bytes(patch[1] if inside else colour))
    return width, height, b"".join(rows)


class PixelsTest(unittest.TestCase):
    def test_what_the_helper_encodes_is_read_back(self):
        width, height, rgb = image(7, 5, (10, 20, 30), (((2, 1, 4, 3)), (200, 100, 50)))
        self.assertEqual(pixels.decode_png(win_helper.encode_png(width, height, rgb)), (width, height, rgb))

    def test_what_is_not_one_of_its_pngs_is_refused(self):
        good = win_helper.encode_png(2, 2, bytes(12))
        for data in (b"", b"GIF89a", good[:20], good.replace(b"IDAT", b"IDAX")):
            with self.subTest(data=data[:12]), self.assertRaises(pixels.PixelsError):
                pixels.decode_png(data)

    def test_a_region_is_cut_by_fractions(self):
        whole = image(10, 10, (0, 0, 0), ((8, 0, 10, 10), (9, 9, 9)))
        width, height, rgb = pixels.region(whole, (0.8, 0.0, 1.0, 0.5))
        self.assertEqual((width, height), (2, 5))
        self.assertEqual(set(rgb), {9})
        with self.assertRaises(pixels.PixelsError):
            pixels.region((1, 1, bytes(3)), (0.87, 0.06, 0.99, 0.80))

    def test_changed_is_the_share_of_pixels_that_differ(self):
        plain = image(10, 10, (30, 30, 30))
        self.assertEqual(pixels.changed(plain, plain), 0.0)
        self.assertEqual(pixels.changed(plain, image(10, 10, (40, 40, 40))), 0.0)     # within the tolerance
        self.assertAlmostEqual(pixels.changed(plain, image(10, 10, (30, 30, 30), ((0, 0, 5, 2), (200, 30, 30)))), 0.1)
        self.assertEqual(pixels.changed(plain, image(10, 9, (30, 30, 30))), 1.0)


class ScaledUpTest(unittest.TestCase):
    """`profiler-roots`' crop (#1701): each pixel repeated, nothing made up."""

    def test_each_pixel_becomes_a_square_of_itself(self):
        rgb = bytes([1, 2, 3, 4, 5, 6,
                     7, 8, 9, 10, 11, 12])          # 2 x 2: (1,2,3) (4,5,6) / (7,8,9) (10,11,12)
        width, height, out = pixels.scaled_up((2, 2, rgb), 3)
        self.assertEqual((width, height), (6, 6))
        for y in range(6):
            for x in range(6):
                source = ((y // 3) * 2 + x // 3) * 3
                with self.subTest(x=x, y=y):
                    self.assertEqual(out[(y * 6 + x) * 3:(y * 6 + x) * 3 + 3], rgb[source:source + 3])

    def test_a_factor_of_one_is_the_image_itself(self):
        picture = image(5, 3, (10, 20, 30), ((1, 1, 3, 2), (200, 100, 50)))
        self.assertEqual(pixels.scaled_up(picture, 1), picture)

    def test_a_bad_factor_or_image_is_refused(self):
        for factor in (0, -1, 1.5, True, "2"):
            with self.subTest(factor=factor), self.assertRaises(pixels.PixelsError):
                pixels.scaled_up((1, 1, bytes(3)), factor)
        with self.assertRaises(pixels.PixelsError):
            pixels.scaled_up((2, 2, bytes(11)), 2)

    def test_the_crop_is_written_as_the_helper_writes_its_shots(self):
        picture = image(4, 3, (10, 20, 30), ((0, 0, 2, 1), (90, 80, 70)))
        self.assertEqual(pixels.decode_png(pixels.encode_png(picture)), picture)


if __name__ == "__main__":
    unittest.main()
