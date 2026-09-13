"""Unit tests for scripts/analysis/check_dds_dimensions.py (issue #247).

Uses synthetic 128-byte DDS headers rather than real textures, so the test needs
neither the 1.8 GB gfx/ tree nor an image library.
"""
from __future__ import annotations

import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "analysis"))

from check_dds_dimensions import (  # noqa: E402
    DdsHeaderError,
    load_allowlist,
    main,
    parse_dds_header,
    scan,
)


def make_dds(width: int, height: int, fourcc: bytes = b"DXT5",
             dxgi: int | None = None, header_size: int = 124) -> bytes:
    """Build a minimal but structurally valid DDS header."""
    data = bytearray(128)
    data[0:4] = b"DDS "
    struct.pack_into("<I", data, 4, header_size)
    struct.pack_into("<I", data, 8, 0x000A1007)   # dwFlags (caps|height|width|pixelformat|…)
    struct.pack_into("<I", data, 12, height)
    struct.pack_into("<I", data, 16, width)
    struct.pack_into("<I", data, 76, 32)          # ddspf.dwSize
    struct.pack_into("<I", data, 80, 0x4)         # ddspf.dwFlags = DDPF_FOURCC
    data[84:88] = fourcc
    if fourcc == b"DX10":
        ext = bytearray(20)
        struct.pack_into("<I", ext, 0, dxgi if dxgi is not None else 98)  # BC7_UNORM
        struct.pack_into("<I", ext, 4, 3)         # D3D10_RESOURCE_DIMENSION_TEXTURE2D
        struct.pack_into("<I", ext, 12, 1)        # arraySize
        return bytes(data) + bytes(ext)
    return bytes(data)


class _TempTree:
    def __init__(self, files: dict):
        self.files = files

    def __enter__(self):
        self.dir = tempfile.TemporaryDirectory()
        for name, blob in self.files.items():
            path = os.path.join(self.dir.name, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(blob)
        return self.dir.name

    def __exit__(self, *exc):
        self.dir.cleanup()


class HeaderParsingTests(unittest.TestCase):
    def test_reads_width_and_height(self):
        info = parse_dds_header(make_dds(256, 128))
        self.assertEqual((info["width"], info["height"]), (256, 128))
        self.assertEqual(info["format"], "DXT5")
        self.assertTrue(info["block_compressed"])

    def test_height_and_width_are_not_swapped(self):
        # dwHeight precedes dwWidth in DDS_HEADER — an easy field to transpose.
        info = parse_dds_header(make_dds(250, 256))
        self.assertEqual(info["width"], 250)
        self.assertEqual(info["height"], 256)

    def test_uncompressed_is_not_block_compressed(self):
        info = parse_dds_header(make_dds(250, 250, fourcc=b"\x00\x00\x00\x00"))
        self.assertFalse(info["block_compressed"])

    def test_dx10_bc7_is_block_compressed(self):
        info = parse_dds_header(make_dds(64, 64, fourcc=b"DX10", dxgi=98))
        self.assertTrue(info["block_compressed"])
        self.assertEqual(info["format"], "DX10/BC7")

    def test_dx10_uncompressed_dxgi_is_not_flagged(self):
        info = parse_dds_header(make_dds(63, 63, fourcc=b"DX10", dxgi=28))  # R8G8B8A8_UNORM
        self.assertFalse(info["block_compressed"])

    def test_bad_magic_raises(self):
        blob = bytearray(make_dds(64, 64))
        blob[0:4] = b"NOPE"
        with self.assertRaises(DdsHeaderError):
            parse_dds_header(bytes(blob))

    def test_bad_header_size_raises(self):
        with self.assertRaises(DdsHeaderError):
            parse_dds_header(make_dds(64, 64, header_size=99))

    def test_truncated_file_raises(self):
        with self.assertRaises(DdsHeaderError):
            parse_dds_header(make_dds(64, 64)[:40])


class ScanTests(unittest.TestCase):
    def test_clean_tree_has_no_violations(self):
        with _TempTree({"gfx/ok.dds": make_dds(256, 256)}) as d:
            result = scan([d], repo_root=d, allowlist=set())
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["block_compressed_scanned"], 1)

    def test_odd_dimension_is_flagged(self):
        with _TempTree({"gfx/bad.dds": make_dds(250, 256)}) as d:
            result = scan([d], repo_root=d, allowlist=set())
        self.assertEqual(len(result["violations"]), 1)
        self.assertEqual(result["violations"][0]["path"], "gfx/bad.dds")
        self.assertEqual(result["violations"][0]["width"], 250)

    def test_uncompressed_odd_dimension_is_ignored(self):
        with _TempTree({"gfx/ok.dds": make_dds(250, 133, fourcc=b"\x00\x00\x00\x00")}) as d:
            result = scan([d], repo_root=d, allowlist=set())
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["block_compressed_scanned"], 0)

    def test_unreadable_file_is_reported(self):
        with _TempTree({"gfx/junk.dds": b"not a dds at all"}) as d:
            result = scan([d], repo_root=d, allowlist=set())
        self.assertEqual(len(result["unreadable"]), 1)

    def test_main_exits_nonzero_on_violation(self):
        with _TempTree({"gfx/bad.dds": make_dds(250, 256)}) as d:
            self.assertEqual(main([f"--repo-root={d}", f"--allowlist={d}/none.txt", d]), 1)

    def test_main_exits_zero_on_clean_tree(self):
        with _TempTree({"gfx/ok.dds": make_dds(64, 64)}) as d:
            self.assertEqual(main([f"--repo-root={d}", f"--allowlist={d}/none.txt", d]), 0)


class AllowlistTests(unittest.TestCase):
    def test_shipped_allowlist_holds_the_four_known_offenders(self):
        entries = load_allowlist()
        self.assertEqual(len(entries), 4, entries)
        for name in ("american_google", "japanese_toyota", "korean_samsung", "russian_rosatom"):
            self.assertTrue(
                any(name in entry for entry in entries),
                f"{name} missing from dds_dimension_allowlist.txt",
            )
        for entry in entries:
            self.assertTrue(entry.startswith("gfx/"), entry)

    def test_allowlist_comments_and_blanks_are_ignored(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("# a comment\n\ngfx/a.dds\ngfx/b.dds  # trailing\n")
            path = fh.name
        try:
            self.assertEqual(load_allowlist(path), {"gfx/a.dds", "gfx/b.dds"})
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
