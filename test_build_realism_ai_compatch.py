"""Tests for the Realism AI compatibility-patch builder's text helpers.

The build itself needs the Realism AI mod installed and checks its own
output (scripts/generators/build_realism_ai_compatch.py); these cover the
pieces that run without it: comment-aware block scanning and the INJECT-style
modifier merge used for the two laws.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts" / "generators"))

import build_realism_ai_compatch as b  # noqa: E402


class BlockScanTests(unittest.TestCase):
    def test_braces_in_comments_and_strings_are_ignored(self):
        text = (
            'a = { # {{ not a brace\n'
            '\tname = "}{"\n'
            '}\n'
            'REPLACE_OR_CREATE:b = {\n'
            '\tnested = { x = 1 }\n'
            '}\n'
        )
        keys = [k for k, _s, _o, _c in b.blocks_at_depth(text)]
        self.assertEqual(keys, ["a", "REPLACE_OR_CREATE:b"])

    def test_depth_one_blocks(self):
        body = "{\n\tmodifier = {\n\t\tx = 1\n\t}\n\tpossible = { y = 2 }\n}"
        keys = [k for k, _s, _o, _c in b.blocks_at_depth(body, depth_target=1)]
        self.assertEqual(keys, ["modifier", "possible"])

    def test_split_directive(self):
        self.assertEqual(b.split_directive("TRY_INJECT:law_x"), ("TRY_INJECT", "law_x"))
        self.assertEqual(b.split_directive("law_x"), ("", "law_x"))


class ModifierMergeTests(unittest.TestCase):
    BODY = (
        "{\n"
        "\tgroup = lawgroup_citizenship\n"
        "\tmodifier = {\n"
        "\t\tcountry_authority_add = 200\n"
        "\t\t# a comment line\n"
        "\t\tcountry_cultural_pull_mult = -0.15\n"
        "\t}\n"
        "\tcan_impose = { always = no }\n"
        "}"
    )

    def test_sums_existing_and_appends_new(self):
        merged = b._merge_into_modifier(
            self.BODY,
            [("country_authority_add", "200"), ("state_birth_rate_mult", "0.05")],
            "test",
        )
        self.assertIn("country_authority_add = 400 # Realism AI adds 200", merged)
        self.assertIn("\t\tstate_birth_rate_mult = 0.05 # Realism AI\n\t}", merged)
        self.assertIn("country_cultural_pull_mult = -0.15", merged)
        self.assertIn("can_impose = { always = no }", merged)

    def test_float_sums_are_exact_enough(self):
        merged = b._merge_into_modifier(self.BODY, [("country_cultural_pull_mult", "0.05")], "test")
        self.assertIn("country_cultural_pull_mult = -0.1 # Realism AI adds 0.05", merged)

    def test_nested_modifier_lines_are_refused(self):
        body = "{\n\tmodifier = {\n\t\tworkforce_scaled = { x = 1 }\n\t}\n}"
        with self.assertRaises(b.BuildError):
            b._merge_into_modifier(body, [("x", "1")], "test")

    def test_two_modifier_blocks_are_refused(self):
        body = "{\n\tmodifier = { a = 1 }\n\tmodifier = { b = 1 }\n}"
        with self.assertRaises(b.BuildError):
            b._merge_into_modifier(body, [("a", "1")], "test")


if __name__ == "__main__":
    unittest.main()
