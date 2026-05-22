"""Unit tests for any_limit_audit (issue #135).

The crux is discrimination: flag `limit` only when its *immediate* parent is an
`any_*` block, never when it sits inside a legitimate nested iterator
(`every_*` / `trigger_if` / …) that itself lives inside an `any_*`.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from any_limit_audit import audit, scan_file, render_report

VANILLA_GAME = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game"


def _scan(text: str):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(text)
        path = fh.name
    try:
        return scan_file(path, "test.txt")
    finally:
        os.unlink(path)


class DetectionTests(unittest.TestCase):
    def test_flags_limit_immediate_child_of_any(self):
        flags = _scan(
            "se = {\n"
            "\tany_scope_state = {\n"
            "\t\tlimit = { is_incorporated = yes }\n"
            "\t\tis_coastal = yes\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].any_name, "any_scope_state")
        self.assertEqual(flags[0].line, 3)

    def test_flags_multiline_limit_block(self):
        flags = _scan(
            "any_scope_character = {\n"
            "\tlimit = {\n"
            "\t\tis_ruler = yes\n"
            "\t}\n"
            "\thas_role = general\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].any_name, "any_scope_character")

    def test_no_flag_for_every_iterator(self):
        # every_* legitimately takes limit.
        flags = _scan(
            "every_scope_state = {\n"
            "\tlimit = { is_incorporated = yes }\n"
            "\tadd_modifier = x\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_for_limit_nested_in_every_inside_any(self):
        # The critical discrimination case: limit's immediate parent is the
        # every_* iterator, not the any_* — must NOT flag.
        flags = _scan(
            "any_scope_country = {\n"
            "\tevery_scope_state = {\n"
            "\t\tlimit = { is_incorporated = yes }\n"
            "\t}\n"
            "\tis_at_war = yes\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_for_limit_in_trigger_if_inside_any(self):
        flags = _scan(
            "any_scope_state = {\n"
            "\ttrigger_if = {\n"
            "\t\tlimit = { is_coastal = yes }\n"
            "\t\tpopulation > 1000\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_for_count_or_percent_children(self):
        flags = _scan(
            "any_scope_state = {\n"
            "\tcount = 3\n"
            "\tpercent = 0.5\n"
            "\tis_coastal = yes\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_nested_any_inside_any_both_discriminated(self):
        # Inner limit's immediate parent is any_scope_pop (also any_*) -> flag.
        flags = _scan(
            "any_scope_state = {\n"
            "\tany_scope_pop = {\n"
            "\t\tlimit = { is_employed = yes }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].any_name, "any_scope_pop")


class SuppressionTests(unittest.TestCase):
    def test_reviewed_on_any_opener_line_suppresses(self):
        flags = _scan(
            "any_scope_state = { # REVIEWED 2026-05-21: deliberate, see note\n"
            "\tlimit = { is_incorporated = yes }\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertIsNotNone(flags[0].exemption)
        self.assertEqual(flags[0].exemption["date"], "2026-05-21")


class ReportTests(unittest.TestCase):
    def test_report_partitions_and_renders(self):
        with tempfile.TemporaryDirectory() as td:
            cdir = os.path.join(td, "common", "scripted_effects")
            os.makedirs(cdir)
            with open(os.path.join(cdir, "x.txt"), "w", encoding="utf-8") as fh:
                fh.write(
                    "se = {\n\tany_scope_state = {\n\t\tlimit = { x = yes }\n\t}\n}\n"
                )
            result = audit(mod_path=td)
            self.assertEqual(len(result.flags), 1)
            report = render_report(result)
            self.assertIn("any_*` limit audit report", report)
            self.assertIn("any_scope_state", report)


@unittest.skipUnless(os.path.isdir(VANILLA_GAME), "vanilla install not found")
class VanillaCleanTests(unittest.TestCase):
    def test_vanilla_has_no_flags(self):
        # Vanilla uses any_*/limit extensively but never the buggy form; a hit
        # would mean the immediate-parent discrimination is broken.
        result = audit(mod_path=VANILLA_GAME)
        self.assertEqual(
            len(result.flags), 0,
            f"unexpected flags in vanilla: "
            f"{[(f.file, f.line, f.any_name) for f in result.flags[:5]]}",
        )


if __name__ == "__main__":
    unittest.main()
