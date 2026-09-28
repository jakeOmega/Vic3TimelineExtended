"""Tests for scripts/analysis/check_goods_label_splices.py."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts" / "analysis"))
import check_goods_label_splices as cgls  # noqa: E402

BOM = "﻿"


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


class SyntheticRepoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        # A mod good and a mod building whose key contains a good's token.
        _write(os.path.join(self.root, "common", "goods", "g.txt"), "widgets = {\n}\n")
        _write(os.path.join(self.root, "common", "buildings", "b.txt"), "building_iron_mine = {\n}\n")
        _write(os.path.join(self.root, "localization", "english", "m_l_english.yml"), BOM + (
            "l_english:\n"
            ' widgets:0 "Widgets"\n'
            ' goods_output_widgets_mult:0 "Building @widgets! Widgets output"\n'
            ' goods_output_widgets_mult_desc:0 "A bonus to @widgets! Widgets"\n'
            ' goods_input_widgets_add:0 "@widgets! $widgets$ input"\n'
            ' building_iron_mine_throughput_add:0 "Iron Mine throughput"\n'
            ' building_group_bg_iron_mining_tax_mult:0 "Iron Mining Tax Income"\n'
        ))
        _write(os.path.join(self.root, "localization", "english", "te_unused_l_english.yml"), BOM + (
            "l_english:\n"
            ' goods_input_widgets_mult:0 "@widgets! Widgets input"\n'
        ))
        _write(os.path.join(self.root, cgls.OVERRIDE_FILE), BOM + (
            "l_english:\n"
            ' iron:0 "Structural Metals"\n'
        ))
        self.snapshot = SimpleNamespace(
            data={"Goods": {"iron": {}, "grain": {}}, "Buildings": {}},
            localization={
                "iron": "Iron",
                "grain": "Grain",
                "goods_input_iron_add": "@iron! Iron input",
                "goods_iron_output_mult": "$iron$ Goods Output",
                "goods_input_grain_add": "@grain! Grain input",
            },
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_spelled_out_labels(self):
        mod_fixes, overrides = cgls.find(self.root, self.snapshot)
        self.assertEqual(
            sorted((key, new) for _p, key, _o, new in mod_fixes),
            [("goods_output_widgets_mult", "Building @widgets! $widgets$ output"),
             ("goods_output_widgets_mult_desc", "A bonus to @widgets! $widgets$")],
        )
        # Only the renamed good's vanilla label; grain is not renamed, and the
        # already-spliced vanilla label needs nothing.
        self.assertEqual(overrides, [("goods_input_iron_add", "@iron! Iron input", "@iron! $iron$ input")])

    def test_fix_then_clean(self):
        cgls.fix(self.root, *cgls.find(self.root, self.snapshot))
        self.assertEqual(cgls.find(self.root, self.snapshot), ([], []))
        with open(os.path.join(self.root, cgls.OVERRIDE_FILE), encoding="utf-8-sig") as fh:
            self.assertIn(' goods_input_iron_add:0 "@iron! $iron$ input"\n', fh.read())


class RepoTests(unittest.TestCase):
    def test_repo_labels_splice_goods_names(self):
        mod_fixes, overrides = cgls.find()
        problems = [f"{k}: {o!r}" for _p, k, o, _n in mod_fixes] + [f"vanilla {k}: {o!r}" for k, o, _n in overrides]
        self.assertEqual(problems, [], "run python3 scripts/analysis/check_goods_label_splices.py --fix")


if __name__ == "__main__":
    unittest.main()
