"""Tests for bom_normalizer (issues #148, #255)."""

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

    def test_collapses_a_doubled_bom(self):
        # The engine strips one BOM; a second one becomes part of the first
        # token, so a leading `#` line stops being a comment and every key
        # after it shifts. 2026-10-03: all 323 company buildings were dropped
        # ("Duplicated key = will not be created") by a script that re-added a
        # BOM to text it had decoded without stripping the old one.
        with tempfile.TemporaryDirectory() as td:
            p = self._write(td, "common/buildings/b.txt", BOM + BOM + BOM + b"# c\nb = {}")
            result = normalize_bom(td)
            self.assertEqual(result["files_normalized"], 1)
            with open(p, "rb") as fh:
                self.assertEqual(fh.read(), BOM + b"# c\nb = {}")
            self.assertEqual(normalize_bom(td)["files_normalized"], 0)

    def test_covers_gfx_txt(self):
        with tempfile.TemporaryDirectory() as td:
            self._write(td, "gfx/map/fleet_entities/02_extra.txt", b"e = {}")
            result = normalize_bom(td)
            self.assertEqual(result["files_normalized"], 1)

    def test_covers_gui_files(self):
        # issue #255: `gui/` was out of scope, so three overrides shipped w/o BOM.
        with tempfile.TemporaryDirectory() as td:
            p = self._write(td, "gui/construction_panel.gui", b"widget = {}")
            nested = self._write(
                td, "gui/journal_entry_widgets/sr_widget.gui", b"widget = {}"
            )
            result = normalize_bom(td)
            self.assertEqual(result["files_normalized"], 2)
            self.assertIn("gui/construction_panel.gui", result["normalized_paths"])
            for path in (p, nested):
                with open(path, "rb") as fh:
                    self.assertTrue(fh.read().startswith(BOM))

    def test_gui_scope_is_limited_to_gui_extension(self):
        with tempfile.TemporaryDirectory() as td:
            self._write(td, "gui/notes.txt", b"not script")
            result = normalize_bom(td)
            self.assertEqual(result["files_normalized"], 0)

    def test_missing_scoped_root_is_skipped(self):
        # Sparse checkouts (e.g. no gfx/) must not raise or abort the walk.
        with tempfile.TemporaryDirectory() as td:
            self._write(td, "gui/x.gui", b"widget = {}")
            result = normalize_bom(td)  # no common/, events/, gfx/ on disk
            self.assertEqual(result["files_scanned"], 1)
            self.assertEqual(result["files_normalized"], 1)

    def test_skips_out_of_scope_roots_and_non_txt(self):
        with tempfile.TemporaryDirectory() as td:
            # Out-of-scope root, plus in-scope non-.txt — neither touched.
            self._write(td, "localization/english/x_l_english.yml", b"l_english:")
            self._write(td, "common/foo/data.json", b"{}")
            self._write(td, "common/foo/note.md", b"# note")
            self._write(td, "common/foo/panel.gui", b"widget = {}")
            result = normalize_bom(td)
            self.assertEqual(result["files_normalized"], 0)


class RepoHasNoDoubledBomTests(unittest.TestCase):
    """CI guard: the normalizer only runs on a full /reload, so a doubled BOM
    committed from a branch would otherwise reach the game (it did, 2026-10-03).
    Also covers localization, where the engine reads the file the same way."""

    def test_no_script_or_loc_file_starts_with_two_boms(self):
        repo = os.path.dirname(os.path.abspath(__file__))
        doubled = []
        for root in ("common", "events", "gfx", "gui", "localization"):
            base = os.path.join(repo, root)
            if not os.path.isdir(base):
                continue  # sparse checkout
            for dirpath, _dirs, files in os.walk(base):
                for fname in files:
                    if not fname.endswith((".txt", ".gui", ".yml")):
                        continue
                    path = os.path.join(dirpath, fname)
                    with open(path, "rb") as fh:
                        if fh.read(6) == BOM + BOM:
                            doubled.append(os.path.relpath(path, repo))
        self.assertEqual(doubled, [], "files starting with two UTF-8 BOMs (run bom_normalizer.py)")


if __name__ == "__main__":
    unittest.main()
