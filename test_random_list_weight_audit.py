"""Unit tests for random_list_weight_audit (#1573).

The crux is discrimination: `trigger` under a `random_list` branch's
`modifier` is rejected by the engine; the same block under `ai_chance`, under
`random = { }` or as a branch's own `trigger` is valid.
"""
from __future__ import annotations

import unittest

from random_list_weight_audit import audit, scan_text


class DetectionTests(unittest.TestCase):
    def test_flags_trigger_in_a_branch_modifier(self):
        flags = scan_text(
            "e = {\n"
            "\trandom_list = {\n"
            "\t\t30 = {\n"
            "\t\t\tmodifier = {\n"
            "\t\t\t\ttrigger = { exists = scope:x }\n"
            "\t\t\t\tadd = 15\n"
            "\t\t\t}\n"
            "\t\t\tadd_loyalists = { value = 1 }\n"
            "\t\t}\n"
            "\t\t70 = { }\n"
            "\t}\n"
            "}\n",
            "t.txt",
        )
        self.assertEqual([(f.line, f.branch, f.branch_line) for f in flags], [(5, "30", 3)])

    def test_flags_a_one_line_block(self):
        flags = scan_text("random_list = { 10 = { modifier = { trigger = { always = yes } add = 5 } } }",
                          "t.txt")
        self.assertEqual(len(flags), 1)

    def test_if_limit_form_is_clean(self):
        self.assertEqual(scan_text(
            "random_list = {\n"
            "\t30 = {\n"
            "\t\tmodifier = {\n"
            "\t\t\tif = { limit = { exists = scope:x } add = 15 }\n"
            "\t\t}\n"
            "\t}\n"
            "}\n",
            "t.txt",
        ), [])

    def test_ai_chance_form_is_clean(self):
        self.assertEqual(scan_text(
            "option = {\n"
            "\tai_chance = {\n"
            "\t\tbase = 1\n"
            "\t\tmodifier = { trigger = { is_at_war = yes } add = 2 }\n"
            "\t}\n"
            "}\n",
            "t.txt",
        ), [])

    def test_random_chance_form_is_clean(self):
        # `random = { modifier = { } }` requires its trigger.
        self.assertEqual(scan_text(
            "random = { chance = 10 modifier = { trigger = { always = yes } add = 5 } }",
            "t.txt",
        ), [])

    def test_a_branch_trigger_is_clean(self):
        self.assertEqual(scan_text(
            "random_list = { 10 = { trigger = { is_at_war = yes } } 90 = { } }",
            "t.txt",
        ), [])

    def test_ai_chance_inside_a_branch_is_clean(self):
        # A modifier two levels under the branch is not the branch's weight.
        self.assertEqual(scan_text(
            "random_list = { 10 = { if = { limit = { always = yes } modifier = { trigger = { } } } } }",
            "t.txt",
        ), [])

    def test_comments_are_ignored(self):
        self.assertEqual(scan_text(
            "random_list = { 10 = { modifier = { # trigger = {\n add = 1 } } }",
            "t.txt",
        ), [])


class ModTests(unittest.TestCase):
    def test_the_mod_is_clean(self):
        result = audit()
        self.assertGreater(result.files_audited, 100)
        self.assertEqual(
            [f"{f.file}:{f.line}" for f in result.flags], [],
            "write `modifier = { if = { limit = { ... } add = N } }` in a random_list branch",
        )


if __name__ == "__main__":
    unittest.main()
