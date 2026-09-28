"""Tests for the principle tier frames (scripts/image_pipeline/gen_principle_tier_frames.py).

Every mod principle must show the frame of its own tier: vanilla ships frames
for tiers I-III only, and a tier-4 or tier-5 principle copied from a tier-3 one
keeps showing "III" with nothing to say so. The tier is the principle's place
in its group's `levels` list.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

MOD_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(MOD_ROOT / "scripts" / "image_pipeline"))

import gen_principle_tier_frames as ptf  # noqa: E402
from generate_icons import rewrite_icon_refs  # noqa: E402


class TierFrameTests(unittest.TestCase):
    def test_every_principle_uses_its_tiers_frame(self):
        tiers = ptf.tiers_by_principle()
        self.assertTrue(any(t == 5 for t in tiers.values()), "no tier-5 principles found")
        targets = {k: ptf.FRAME[t] for k, t in tiers.items()}
        wrong = []
        for path in sorted((MOD_ROOT / "common/power_bloc_principles").glob("*.txt")):
            wrong += rewrite_icon_refs(path, "background", targets, dry_run=True)
        self.assertEqual(sorted(wrong), [],
                         "principles whose background is not their tier's frame: "
                         "run gen_principle_tier_frames.py --wire")

    def test_tier_iv_and_v_frames_are_committed(self):
        folder = MOD_ROOT / ptf.FOLDER
        if not (MOD_ROOT / "gfx").is_dir():
            raise unittest.SkipTest("gfx/ not checked out (sparse worktree)")
        for t in (4, 5):
            self.assertTrue((MOD_ROOT / ptf.FRAME[t]).is_file(), f"{ptf.FRAME[t]} missing from {folder}")

    def test_injected_levels_follow_vanillas_three(self):
        with tempfile.TemporaryDirectory() as d:
            groups = Path(d) / "common/power_bloc_principle_groups"
            groups.mkdir(parents=True)
            (groups / "x.txt").write_text(
                "﻿INJECT:principle_group_a = {\n\tlevels = {\n\t\tprinciple_a_4\n\t\tprinciple_a_5 # tier 5\n\t}\n}\n"
                "principle_group_b = {\n\tlevels = { principle_b_1 principle_b_2 principle_b_3 principle_b_4 principle_b_5 }\n}\n",
                encoding="utf-8")
            self.assertEqual(ptf.tiers_by_principle(Path(d)), {
                "principle_a_4": 4, "principle_a_5": 5,
                "principle_b_1": 1, "principle_b_2": 2, "principle_b_3": 3, "principle_b_4": 4, "principle_b_5": 5,
            })

    def test_inset_sides_continue_four_five_six(self):
        self.assertEqual(len(ptf.INSET[4]), 7)
        self.assertEqual(len(ptf.INSET[5]), 8)


if __name__ == "__main__":
    unittest.main()
