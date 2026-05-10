"""Unit tests for scripts/generators/gen_prestige_icons.py.

Pure unit — no live game files, no server. Run:
    python3 -m unittest test_gen_prestige_icons -v
"""
from __future__ import annotations

import sys
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts" / "image_pipeline"))

import gen_prestige_icons as gen


SAMPLE_PRESTIGE_FILE = '''\
prestige_good_alpha = {
\tbase_good = alpha_good
\tprestige_bonus = 0.1
\ttexture = "gfx/interface/icons/goods_icons/alpha_good.dds"
}

prestige_good_beta = {
\tbase_good = beta_good
\tprestige_bonus = 0.1
\ttexture = "gfx/interface/icons/goods_icons/beta_good.dds"
}

prestige_good_unfindable = {
\tbase_good = ghost_good
\tprestige_bonus = 0.1
\ttexture = "gfx/interface/icons/goods_icons/ghost_good.dds"
}
'''


def _write_test_dds(path: Path, w: int = 64, h: int = 64) -> None:
    """Write a small synthetic uncompressed RGBA DDS using the same encoder
    we're testing the output of. Not great for source-file fidelity tests, but
    it's what Pillow can read on this machine without Wand/ImageMagick."""
    rng = np.random.default_rng(seed=42)
    arr = rng.integers(0, 256, size=(h, w, 4), dtype=np.uint8)
    arr[..., 3] = 255  # opaque
    img = Image.fromarray(arr, "RGBA")
    gen.write_dds_rgba(img, path)


class DdsHeaderTests(unittest.TestCase):
    def test_header_round_trips_via_pillow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.dds"
            _write_test_dds(p, w=32, h=24)
            self.assertTrue(p.is_file())
            self.assertEqual(p.stat().st_size, 128 + 32 * 24 * 4)
            with Image.open(p) as img:
                self.assertEqual(img.size, (32, 24))
                self.assertEqual(img.mode, "RGBA")

    def test_header_pixel_format_matches_vanilla(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.dds"
            _write_test_dds(p, w=8, h=8)
            with open(p, "rb") as f:
                head = f.read(128)
            self.assertEqual(head[:4], b"DDS ")
            (pf_size,) = struct.unpack_from("<I", head, 76)
            (pf_flags,) = struct.unpack_from("<I", head, 80)
            (rgb_bits,) = struct.unpack_from("<I", head, 88)
            (r_mask,) = struct.unpack_from("<I", head, 92)
            (g_mask,) = struct.unpack_from("<I", head, 96)
            (b_mask,) = struct.unpack_from("<I", head, 100)
            (a_mask,) = struct.unpack_from("<I", head, 104)
            self.assertEqual(pf_size, 32)
            self.assertEqual(pf_flags, 0x41)  # alphapixels|rgb
            self.assertEqual(rgb_bits, 32)
            self.assertEqual((r_mask, g_mask, b_mask, a_mask),
                             (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000))


class TextureRewriteTests(unittest.TestCase):
    def test_strips_prestige_prefix_from_prior_runs(self) -> None:
        text = (
            'prestige_good_x = {\n'
            '\ttexture = "gfx/interface/icons/goods_icons/prestige/foo.dds"\n'
            '}\n'
        )
        rewrites, sources = gen.parse_textures(text)
        self.assertEqual(len(rewrites), 1)
        self.assertEqual(rewrites[0].old_path,
                         "gfx/interface/icons/goods_icons/prestige/foo.dds")
        self.assertEqual(rewrites[0].new_path,
                         "gfx/interface/icons/goods_icons/prestige/foo.dds")
        # Source map points at the un-prefixed source.
        self.assertEqual(sources, {"gfx/interface/icons/goods_icons/foo.dds": "foo.dds"})

    def test_idempotent_rewrite(self) -> None:
        text = (
            'prestige_good_x = {\n'
            '\ttexture = "gfx/interface/icons/goods_icons/prestige/foo.dds"\n'
            '}\n'
        )
        rewrites, _ = gen.parse_textures(text)
        out = gen.rewrite_textures(text, rewrites)
        self.assertEqual(out, text)


class RunPipelineTests(unittest.TestCase):
    def test_full_pipeline_generates_outputs_and_rewrites_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            mod_gfx = tdp / "gfx" / "interface" / "icons" / "goods_icons"
            mod_gfx.mkdir(parents=True)
            _write_test_dds(mod_gfx / "alpha_good.dds", w=32, h=32)
            _write_test_dds(mod_gfx / "beta_good.dds", w=64, h=48)
            # Note: ghost_good.dds intentionally absent → goes to missing_sources.

            prestige_file = tdp / "extra_prestige_goods.txt"
            prestige_file.write_text(SAMPLE_PRESTIGE_FILE, encoding="utf-8")
            output_dir = mod_gfx / "prestige"

            with mock.patch.object(gen, "PRESTIGE_FILE", prestige_file), \
                 mock.patch.object(gen, "OUTPUT_DIR", output_dir), \
                 mock.patch.object(gen, "SOURCE_DIRS", (mod_gfx,)):
                summary = gen.run()

            self.assertEqual(summary.generated, 2)
            self.assertEqual(summary.skipped_existing, 0)
            self.assertEqual(summary.missing_sources,
                             ["gfx/interface/icons/goods_icons/ghost_good.dds"])
            self.assertTrue(summary.rewrote_file)

            self.assertTrue((output_dir / "alpha_good.dds").is_file())
            self.assertTrue((output_dir / "beta_good.dds").is_file())
            self.assertFalse((output_dir / "ghost_good.dds").exists())

            with Image.open(output_dir / "alpha_good.dds") as alpha:
                self.assertEqual(alpha.size, (32, 32))
                self.assertEqual(alpha.mode, "RGBA")

            txt = prestige_file.read_text(encoding="utf-8")
            self.assertIn("prestige/alpha_good.dds", txt)
            self.assertIn("prestige/beta_good.dds", txt)
            # Ghost entry's texture line is left untouched.
            self.assertIn("prestige/ghost_good.dds", txt)

    def test_idempotent_second_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            mod_gfx = tdp / "gfx" / "interface" / "icons" / "goods_icons"
            mod_gfx.mkdir(parents=True)
            _write_test_dds(mod_gfx / "alpha_good.dds", w=16, h=16)
            _write_test_dds(mod_gfx / "beta_good.dds", w=16, h=16)
            prestige_file = tdp / "extra_prestige_goods.txt"
            prestige_file.write_text(SAMPLE_PRESTIGE_FILE, encoding="utf-8")
            output_dir = mod_gfx / "prestige"

            with mock.patch.object(gen, "PRESTIGE_FILE", prestige_file), \
                 mock.patch.object(gen, "OUTPUT_DIR", output_dir), \
                 mock.patch.object(gen, "SOURCE_DIRS", (mod_gfx,)):
                first = gen.run()
                second = gen.run()

            self.assertEqual(second.generated, 0)
            self.assertEqual(second.skipped_existing, 2)
            self.assertFalse(second.rewrote_file)
            self.assertEqual(first.generated, 2)

    def test_force_overwrites_existing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            mod_gfx = tdp / "gfx" / "interface" / "icons" / "goods_icons"
            mod_gfx.mkdir(parents=True)
            _write_test_dds(mod_gfx / "alpha_good.dds", w=16, h=16)
            _write_test_dds(mod_gfx / "beta_good.dds", w=16, h=16)
            prestige_file = tdp / "extra_prestige_goods.txt"
            prestige_file.write_text(SAMPLE_PRESTIGE_FILE, encoding="utf-8")
            output_dir = mod_gfx / "prestige"

            with mock.patch.object(gen, "PRESTIGE_FILE", prestige_file), \
                 mock.patch.object(gen, "OUTPUT_DIR", output_dir), \
                 mock.patch.object(gen, "SOURCE_DIRS", (mod_gfx,)):
                gen.run()
                forced = gen.run(force=True)

            self.assertEqual(forced.generated, 2)
            self.assertEqual(forced.skipped_existing, 0)


if __name__ == "__main__":
    unittest.main()
