"""Unit tests for iterator_limit_audit (issue #250).

The crux is discrimination: flag a `limit` only when an *effect* sibling was
written before it inside the same iterator block. Iterator configuration keys
(`order_by`, `max`, …), non-iterators, nested blocks and comments must not
produce flags.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from iterator_limit_audit import audit, render_report, scan_text


def _scan(text: str):
    return scan_text(text, "test.txt")


class DetectionTests(unittest.TestCase):
    def test_flags_effect_before_limit(self):
        flags = _scan(
            "se = {\n"
            "\tevery_scope_state = {\n"
            "\t\tdo_a = yes\n"
            "\t\tlimit = { has_building = X }\n"
            "\t\tdo_b = yes\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].iterator, "every_scope_state")
        self.assertEqual(flags[0].line, 4)
        self.assertEqual(flags[0].preceding_key, "do_a")
        self.assertEqual(flags[0].preceding_line, 3)

    def test_reproduces_remove_invalid_buildings_bug(self):
        # The historical case (#240): a generated company sweep written before
        # an unrelated space-program limit, silently gated by it.
        flags = _scan(
            "remove_invalid_buildings = {\n"
            "\teffect = {\n"
            "\t\tevery_scope_state = {\n"
            "\t\t\tremove_invalid_company_buildings_effect = yes\n"
            "\t\t\tlimit = {\n"
            "\t\t\t\tAND = {\n"
            "\t\t\t\t\tNOT = { owner.market_capital = THIS }\n"
            "\t\t\t\t\thas_building = building_space_program\n"
            "\t\t\t\t}\n"
            "\t\t\t}\n"
            "\t\t\tremove_building = building_space_program\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].preceding_key,
                         "remove_invalid_company_buildings_effect")
        self.assertEqual(flags[0].line, 5)

    def test_no_flag_when_limit_is_first(self):
        flags = _scan(
            "every_scope_state = {\n"
            "\tlimit = { is_incorporated = yes }\n"
            "\tadd_modifier = x\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_for_iterator_property_before_limit(self):
        # order_by / max / position configure the iteration; they do not gate
        # anything, so they may legally precede the limit.
        flags = _scan(
            "ordered_scope_state = {\n"
            "\torder_by = population\n"
            "\tmax = 3\n"
            "\tlimit = { is_incorporated = yes }\n"
            "\tadd_modifier = x\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_flags_every_random_ordered_and_any(self):
        for name in ("every_scope_state", "random_scope_state",
                     "ordered_scope_state", "any_scope_state"):
            with self.subTest(iterator=name):
                flags = _scan(
                    f"{name} = {{\n"
                    "\tdo_a = yes\n"
                    "\tlimit = { x = yes }\n"
                    "}\n"
                )
                self.assertEqual(len(flags), 1)
                self.assertEqual(flags[0].iterator, name)

    def test_no_flag_for_non_iterator_lookalikes(self):
        flags = _scan(
            "random_list = {\n"
            "\t50 = { do_a = yes }\n"
            "\t50 = { do_b = yes }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_limit_attributed_to_immediate_parent_only(self):
        # The inner limit belongs to the inner iterator, which has no effect
        # sibling before it -> no flag, even though the outer block does.
        flags = _scan(
            "every_scope_country = {\n"
            "\tdo_a = yes\n"
            "\tevery_scope_state = {\n"
            "\t\tlimit = { is_incorporated = yes }\n"
            "\t\tdo_b = yes\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_flags_inner_iterator_when_it_has_an_effect_first(self):
        flags = _scan(
            "every_scope_country = {\n"
            "\tlimit = { is_at_war = yes }\n"
            "\tevery_scope_state = {\n"
            "\t\tdo_b = yes\n"
            "\t\tlimit = { is_incorporated = yes }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].iterator, "every_scope_state")
        self.assertEqual(flags[0].line, 5)

    def test_limit_inside_if_within_iterator_is_not_the_iterator_limit(self):
        flags = _scan(
            "every_scope_state = {\n"
            "\tdo_a = yes\n"
            "\tif = {\n"
            "\t\tlimit = { is_coastal = yes }\n"
            "\t\tdo_b = yes\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_handles_several_statements_on_one_line(self):
        # A per-line scan would miss this; the statement stream does not.
        flags = _scan("every_scope_state = { do_a = yes limit = { x = yes } }\n")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].preceding_key, "do_a")

    def test_ignores_commented_out_statements(self):
        flags = _scan(
            "every_scope_state = {\n"
            "\t# do_a = yes\n"
            "\tlimit = { x = yes }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_ignores_statements_inside_string_literals(self):
        # The quoted body must not register a `limit` child or unbalance the
        # brace stack: exactly one flag, on the real limit at line 3.
        flags = _scan(
            "every_scope_state = {\n"
            '\tcustom_tooltip = "limit = { y = yes }"\n'
            "\tlimit = { x = yes }\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].line, 3)
        self.assertEqual(flags[0].preceding_key, "custom_tooltip")


class SuppressionTests(unittest.TestCase):
    def test_reviewed_on_limit_line_suppresses(self):
        flags = _scan(
            "every_scope_state = {\n"
            "\tdo_a = yes\n"
            "\tlimit = { x = yes } # REVIEWED 2026-09-13: both effects are gated\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertIsNotNone(flags[0].exemption)
        self.assertEqual(flags[0].exemption["date"], "2026-09-13")

    def test_reviewed_on_iterator_opener_line_suppresses(self):
        flags = _scan(
            "every_scope_state = { # REVIEWED 2026-09-13: deliberate\n"
            "\tdo_a = yes\n"
            "\tlimit = { x = yes }\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertIsNotNone(flags[0].exemption)
        self.assertEqual(flags[0].exemption["rationale"], "deliberate")


class AuditAndReportTests(unittest.TestCase):
    def test_walks_audit_dirs_and_renders_report(self):
        with tempfile.TemporaryDirectory() as td:
            eff_dir = os.path.join(td, "common", "scripted_effects")
            os.makedirs(eff_dir)
            with open(os.path.join(eff_dir, "x.txt"), "w", encoding="utf-8") as fh:
                fh.write(
                    "se = {\n\tevery_scope_state = {\n\t\tdo_a = yes\n"
                    "\t\tlimit = { x = yes }\n\t}\n}\n"
                )
            # Outside the audited directory set -> not scanned.
            other = os.path.join(td, "common", "scripted_triggers")
            os.makedirs(other)
            with open(os.path.join(other, "y.txt"), "w", encoding="utf-8") as fh:
                fh.write(
                    "st = {\n\tevery_scope_state = {\n\t\tdo_a = yes\n"
                    "\t\tlimit = { x = yes }\n\t}\n}\n"
                )

            result = audit(mod_path=td)
            self.assertEqual(result.files_audited, 1)
            self.assertEqual(len(result.flags), 1)

            report = render_report(result)
            self.assertIn("Iterator `limit` placement audit report", report)
            self.assertIn("every_scope_state", report)
            self.assertIn("- unreviewed: 1", report)

    def test_report_reports_none_when_clean(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "events"))
            report = render_report(audit(mod_path=td))
            self.assertIn("_None._", report)
            self.assertIn("- total flags: 0", report)


if __name__ == "__main__":
    unittest.main()
