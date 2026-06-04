"""Tests for duplicate_key_audit.py (issue #192).

Pins the two things that make this audit useful instead of noisy:
  1. it flags duplicate scalar keys inside modifier-family blocks
     (identical → warn, differing → error), and
  2. it does NOT flag script-value math blocks (`add = { multiply … multiply … }`)
     or block-valued repeats — the false-positive trap the allowlist guards.

Run: python3 test_duplicate_key_audit.py
"""

import unittest

import duplicate_key_audit as dk


def _flags(text):
    flags, _ = dk.scan_text(text, "test.txt")
    return flags


class DetectionTests(unittest.TestCase):
    def test_identical_value_dup_is_warn(self):
        text = (
            "some_tech = {\n"
            "\tmodifier = {\n"
            "\t\tfoo_bool = yes\n"
            "\t\tfoo_bool = yes\n"
            "\t}\n"
            "}\n"
        )
        flags = _flags(text)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].key, "foo_bool")
        self.assertEqual(flags[0].severity, "warn")
        self.assertEqual(flags[0].line, 4)
        self.assertEqual(flags[0].first_line, 3)
        self.assertEqual(flags[0].block_key, "modifier")

    def test_differing_value_dup_is_error(self):
        text = (
            "some_good = {\n"
            "\tmodifier = {\n"
            "\t\tcountry_x_add = 10\n"
            "\t\tcountry_x_add = 20\n"
            "\t}\n"
            "}\n"
        )
        flags = _flags(text)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].severity, "error")
        self.assertEqual(flags[0].value, "20")
        self.assertEqual(flags[0].first_value, "10")

    def test_dup_in_scaling_wrapper_inside_modifier(self):
        text = (
            "pm_x = {\n"
            "\tbuilding_modifiers = {\n"
            "\t\tworkforce_scaled = {\n"
            "\t\t\tgoods_input_lead_add = 10\n"
            "\t\t\tgoods_input_lead_add = 20\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        flags = _flags(text)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].severity, "error")
        self.assertEqual(flags[0].block_key, "workforce_scaled")


class NoFalsePositiveTests(unittest.TestCase):
    def test_script_value_add_block_not_flagged(self):
        # Sequential math: repeated multiply/divide are legitimate, not a collision.
        text = (
            "some_sv = {\n"
            "\tvalue = 100\n"
            "\tadd = {\n"
            "\t\tvalue = 5\n"
            "\t\tmultiply = 0.5\n"
            "\t\tmultiply = 0.25\n"
            "\t\tdivide = 1000\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(_flags(text), [])

    def test_block_valued_repeats_not_flagged(self):
        # Two `modifier = {` children in an ai_chance, and two add_modifier
        # statements — block-valued keys, never tracked as scalar dups.
        text = (
            "evt.1 = {\n"
            "\tai_chance = {\n"
            "\t\tbase = 1\n"
            "\t\tmodifier = { trigger = { x = yes } add = 2 }\n"
            "\t\tmodifier = { trigger = { y = yes } add = 3 }\n"
            "\t}\n"
            "\timmediate = {\n"
            "\t\tadd_modifier = { name = a }\n"
            "\t\tadd_modifier = { name = b }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(_flags(text), [])

    def test_same_key_in_sibling_blocks_not_flagged(self):
        # Each block has its own key namespace; `value = N` once per block is fine.
        text = (
            "x = {\n"
            "\tmodifier = { country_a_add = 1 }\n"
            "\tmodifier = { country_a_add = 1 }\n"
            "}\n"
        )
        self.assertEqual(_flags(text), [])

    def test_non_modifier_block_not_tracked(self):
        # A repeated scalar in a plain (non-allowlisted) block is left alone —
        # could be a legitimate sequential effect.
        text = (
            "x = {\n"
            "\teffect = {\n"
            "\t\tadd_innovation = 5\n"
            "\t\tadd_innovation = 3\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(_flags(text), [])


class SuppressionTests(unittest.TestCase):
    def test_reviewed_comment_marks_exemption(self):
        text = (
            "x = {\n"
            "\tmodifier = {\n"
            "\t\tfoo_add = 1\n"
            "\t\tfoo_add = 2  # REVIEWED 2026-06-04: intentional stacking, verified\n"
            "\t}\n"
            "}\n"
        )
        flags = _flags(text)
        self.assertEqual(len(flags), 1)
        self.assertIsNotNone(flags[0].exemption)
        self.assertEqual(flags[0].exemption["date"], "2026-06-04")


if __name__ == "__main__":
    unittest.main()
