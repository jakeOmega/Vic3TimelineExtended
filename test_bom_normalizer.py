"""Tests for bom_normalizer (issue #148)."""

import os
import tempfile
import unittest

from bom_normalizer import BOM, normalize_bom


class NormalizeBomTests(unittest.TestCase):
    def _write(self, root, rel, data: bytes):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def test_prepends_bom_to_scoped_txt_without_one(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._write(td, "common/foo/bar.txt", b"x = { y = 1 }")
            result = normalize_bom(td)
            self.assertEqual(result["files_normalized"], 1)
            self.assertIn("common/foo/bar.txt", result["normalized_paths"])
            with open(p, "rb") as fh:
                self.assertTrue(fh.read().startswith(BOM))

    def test_idempotent_leaves_bommed_file_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            self._write(td, "events/e.txt", BOM + b"namespace = e")
            result = normalize_bom(td)
            self.assertEqual(result["files_normalized"], 0)

    def test_does_not_double_bom(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._write(td, "events/e.txt", b"namespace = e")
            normalize_bom(td)
            normalize_bom(td)  # second pass must not add a second BOM
            with open(p, "rb") as fh:
                data = fh.read()
            self.assertTrue(data.startswith(BOM))
            self.assertFalse(data[3:].startswith(BOM))

    def test_covers_gfx_txt(self):
        with tempfile.TemporaryDirectory() as td:
            self._write(td, "gfx/map/fleet_entities/02_extra.txt", b"e = {}")
            result = normalize_bom(td)
            self.assertEqual(result["files_normalized"], 1)

    def test_skips_out_of_scope_roots_and_non_txt(self):
        with tempfile.TemporaryDirectory() as td:
            # Out-of-scope root, plus in-scope non-.txt — neither touched.
            self._write(td, "localization/english/x_l_english.yml", b"l_english:")
            self._write(td, "common/foo/data.json", b"{}")
            self._write(td, "common/foo/note.md", b"# note")
            result = normalize_bom(td)
            self.assertEqual(result["files_normalized"], 0)


if __name__ == "__main__":
    unittest.main()
