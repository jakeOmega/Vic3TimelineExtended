"""game_defines: the engine defines merged leaf by leaf (#1879), and
`vanilla_parsed.vanilla_define`, which tests use to pin a vanilla define
without a game install."""
import os
import tempfile
import unittest

import game_defines as gd
import vanilla_parsed

TEXT = """
@scale = 0.5
NAI = {
	GATE = 0.1 # If we don't have at least this fraction ...
	NAME = "ai_strategy_default"
	STEPS = { 10 50 100 }
	ENABLED = yes
}
NPops = {
	A = 1
}
NPops = {
	B = @scale
	A = 3
}
"""


class ReaderTests(unittest.TestCase):
    def test_leaves_are_tokens_as_written(self):
        out = gd.parse_text(TEXT)
        self.assertEqual(out["NAI"], {"GATE": "0.1", "NAME": '"ai_strategy_default"',
                                      "STEPS": ["10", "50", "100"], "ENABLED": "yes"})
        self.assertEqual(out["@scale"], "0.5")

    def test_a_namespace_opened_twice_keeps_both_blocks(self):
        self.assertEqual(gd.parse_text(TEXT)["NPops"], {"A": "3", "B": "@scale"})

    def test_files_merge_leaf_by_leaf_in_name_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in (("00_defines.txt", TEXT), ("zz_mod.txt", "NAI = { GATE = 0.02 }\n"),
                               ("jomini/00_tooltips.txt", "NTooltips = { DELAY = 0.5 }\n")):
                path = os.path.join(tmp, name)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8-sig") as f:
                    f.write(text)
            self.assertEqual(list(gd.parse_files(tmp)), ["00_defines.txt", "jomini/00_tooltips.txt", "zz_mod.txt"])
            merged = gd.parse_dir(tmp)
        self.assertEqual(merged["NAI"]["GATE"], "0.02")
        self.assertEqual(merged["NAI"]["ENABLED"], "yes")
        self.assertEqual(merged["NTooltips"], {"DELAY": "0.5"})
        self.assertEqual(gd.leaf_count(merged), 7)
        self.assertEqual(gd.parse_dir(os.path.join(tmp, "gone")), {})


class CommittedSnapshotTests(unittest.TestCase):
    """Vanilla's defines as the repo carries them."""

    def test_vanilla_define_reads_the_snapshot(self):
        self.assertEqual(vanilla_parsed.vanilla_define("NAI", "CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS"), "0.1")
        self.assertEqual(vanilla_parsed.vanilla_define("NAI", "DEFAULT_STRATEGY_STRING"), '"ai_strategy_default"')
        self.assertIsInstance(vanilla_parsed.vanilla_define("NEconomy", "COMPANY_INFLUENCE_LEVEL_STEPS"), list)
        with self.assertRaises(KeyError):
            vanilla_parsed.vanilla_define("NAI", "NO_SUCH_DEFINE")

    def test_both_npops_blocks_are_kept(self):
        # Vanilla 1.15's 00_defines.txt opens NPops twice; ModState's merge would keep one.
        defines = vanilla_parsed.load_defines()
        self.assertGreater(len(defines["NPops"]), 100)
        self.assertGreater(gd.leaf_count(defines), 3000)
        info = vanilla_parsed.read_manifest(vanilla_parsed.DEFAULT_DIR)["defines"]
        self.assertEqual(info["leaves"], gd.leaf_count(defines))


if __name__ == "__main__":
    unittest.main()
