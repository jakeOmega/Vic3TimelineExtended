"""Unit tests for modifier_multiplier_var_audit (issue #250).

The crux is the pairing rule: a *permanent* `add_modifier` whose `multiplier`
reads `var:X`, followed later in the same top-level block by
`remove_variable = X`. Timed modifiers, removals that precede the modifier,
removals in another block, and the "different branch, modifier already dropped"
clean-up shape must all stay quiet.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from modifier_multiplier_var_audit import audit, render_report, scan_text

# The historical bug (#240): update_intel_sharing_defense applied a permanent
# shield modifier scaled by var:_best_boost and then removed that variable.
INTEL_SHARING_BUGGY = """update_intel_sharing_defense = {
\tset_variable = { name = _best_boost value = 0 }
\tevery_scope_country = {
\t\tlimit = { has_intel_sharing = yes }
\t\tset_variable = { name = _cand value = 1 }
\t}
\tif = {
\t\tlimit = { has_modifier = intelligence_sharing_defense_shield_modifier }
\t\tremove_modifier = intelligence_sharing_defense_shield_modifier
\t}
\tif = {
\t\tlimit = { var:_best_boost > 0 }
\t\tadd_modifier = {
\t\t\tname = intelligence_sharing_defense_shield_modifier
\t\t\tmultiplier = var:_best_boost
\t\t}
\t}
\tremove_variable = _own_def
\tremove_variable = _best_boost
}
"""


def _scan(text: str):
    return scan_text(text, "test.txt")


class DetectionTests(unittest.TestCase):
    def test_reproduces_intel_sharing_bug(self):
        flags = _scan(INTEL_SHARING_BUGGY)
        self.assertEqual(len(flags), 1)
        f = flags[0]
        self.assertEqual(f.variable, "_best_boost")
        self.assertEqual(f.multiplier, "var:_best_boost")
        self.assertEqual(f.modifier_name,
                         "intelligence_sharing_defense_shield_modifier")
        self.assertEqual(f.block, "update_intel_sharing_defense")
        self.assertEqual(f.add_line, 15)
        self.assertEqual(f.remove_line, 19)

    def test_no_flag_when_modifier_is_timed(self):
        for duration in ("days = 365", "months = 12", "years = 1"):
            with self.subTest(duration=duration):
                flags = _scan(
                    "se = {\n"
                    "\tadd_modifier = {\n"
                    "\t\tname = m\n"
                    "\t\tmultiplier = var:x\n"
                    f"\t\t{duration}\n"
                    "\t}\n"
                    "\tremove_variable = x\n"
                    "}\n"
                )
                self.assertEqual(flags, [])

    def test_no_flag_when_variable_is_not_removed(self):
        flags = _scan(
            "se = {\n"
            "\tadd_modifier = { name = m multiplier = var:x }\n"
            "\tset_variable = { name = x value = 2 }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_when_removal_precedes_the_modifier(self):
        flags = _scan(
            "se = {\n"
            "\tremove_variable = x\n"
            "\tset_variable = { name = x value = 2 }\n"
            "\tadd_modifier = { name = m multiplier = var:x }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_for_a_different_variable_name(self):
        flags = _scan(
            "se = {\n"
            "\tadd_modifier = { name = m multiplier = var:keep_me }\n"
            "\tremove_variable = scratch\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_across_two_top_level_blocks(self):
        flags = _scan(
            "se_a = {\n"
            "\tadd_modifier = { name = m multiplier = var:x }\n"
            "}\n"
            "se_b = {\n"
            "\tremove_variable = x\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_flags_scope_prefixed_multipliers(self):
        for token in ("var:x", "owner.var:x", "root.var:x", "scope:target.var:x"):
            with self.subTest(multiplier=token):
                flags = _scan(
                    "se = {\n"
                    f"\tadd_modifier = {{ name = m multiplier = {token} }}\n"
                    "\tremove_variable = x\n"
                    "}\n"
                )
                self.assertEqual(len(flags), 1)
                self.assertEqual(flags[0].multiplier, token)
                self.assertEqual(flags[0].variable, "x")

    def test_local_var_pairs_only_with_remove_local_variable(self):
        flags = _scan(
            "se = {\n"
            "\tadd_modifier = { name = m multiplier = local_var:x }\n"
            "\tremove_variable = x\n"
            "}\n"
        )
        self.assertEqual(flags, [])

        flags = _scan(
            "se = {\n"
            "\tadd_modifier = { name = m multiplier = local_var:x }\n"
            "\tremove_local_variable = x\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].variable, "x")

    def test_reproduces_per_site_modifier_shape(self):
        # The variable is removed after the iteration that applied the
        # permanent modifier — still a live multiplier reading a dead variable.
        flags = _scan(
            "te_construction_market_apply_per_site_modifier = {\n"
            "\tremove_variable = te_cm_capacity_mult\n"
            "\tevery_scope_building = {\n"
            "\t\tlimit = { is_building_type = site }\n"
            "\t\tremove_modifier = cap_mod\n"
            "\t\towner = { set_variable = { name = te_cm_capacity_mult value = 1 } }\n"
            "\t\tadd_modifier = {\n"
            "\t\t\tname = cap_mod\n"
            "\t\t\tmultiplier = owner.var:te_cm_capacity_mult\n"
            "\t\t}\n"
            "\t}\n"
            "\tremove_variable = te_cm_capacity_mult\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].remove_line, 12)


class BranchTests(unittest.TestCase):
    CLEANUP_ELSE = (
        "se = {\n"
        "\tif = {\n"
        "\t\tlimit = { has_pact = yes }\n"
        "\t\tset_variable = { name = shield_mult value = 1 }\n"
        "\t\tadd_modifier = { name = shield multiplier = var:shield_mult }\n"
        "\t}\n"
        "\telse = {\n"
        "{REMOVE_MODIFIER}"
        "\t\tremove_variable = shield_mult\n"
        "\t}\n"
        "}\n"
    )

    def test_else_branch_that_drops_the_modifier_first_is_clean(self):
        flags = _scan(self.CLEANUP_ELSE.replace(
            "{REMOVE_MODIFIER}", "\t\tremove_modifier = shield\n"))
        self.assertEqual(flags, [])

    def test_else_branch_that_leaves_the_modifier_up_is_flagged(self):
        # Without the remove_modifier, a shield applied on an earlier call is
        # still live when this branch deletes its backing variable.
        flags = _scan(self.CLEANUP_ELSE.replace("{REMOVE_MODIFIER}", ""))
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].variable, "shield_mult")

    def test_sibling_if_blocks_are_not_treated_as_exclusive(self):
        flags = _scan(
            "se = {\n"
            "\tif = {\n"
            "\t\tlimit = { a = yes }\n"
            "\t\tadd_modifier = { name = m multiplier = var:x }\n"
            "\t}\n"
            "\tif = {\n"
            "\t\tlimit = { b = yes }\n"
            "\t\tremove_variable = x\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)

    def test_separate_event_options_are_exclusive(self):
        flags = _scan(
            "my_event.1 = {\n"
            "\toption = {\n"
            "\t\tname = a\n"
            "\t\tadd_modifier = { name = m multiplier = var:x }\n"
            "\t}\n"
            "\toption = {\n"
            "\t\tname = b\n"
            "\t\tremove_modifier = m\n"
            "\t\tremove_variable = x\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(flags, [])


class SuppressionTests(unittest.TestCase):
    def test_reviewed_on_remove_line_suppresses(self):
        flags = _scan(
            "se = {\n"
            "\tadd_modifier = { name = m multiplier = var:x }\n"
            "\tremove_variable = x # REVIEWED 2026-09-13: modifier is re-applied first\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertIsNotNone(flags[0].exemption)
        self.assertEqual(flags[0].exemption["date"], "2026-09-13")

    def test_reviewed_on_multiplier_line_suppresses(self):
        flags = _scan(
            "se = {\n"
            "\tadd_modifier = {\n"
            "\t\tname = m\n"
            "\t\tmultiplier = var:x # REVIEWED 2026-09-13: deliberate\n"
            "\t}\n"
            "\tremove_variable = x\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].exemption["rationale"], "deliberate")


class AuditAndReportTests(unittest.TestCase):
    def test_walks_audit_dirs_and_renders_report(self):
        with tempfile.TemporaryDirectory() as td:
            eff_dir = os.path.join(td, "common", "scripted_effects")
            os.makedirs(eff_dir)
            with open(os.path.join(eff_dir, "x.txt"), "w", encoding="utf-8") as fh:
                fh.write(INTEL_SHARING_BUGGY)
            other = os.path.join(td, "common", "scripted_triggers")
            os.makedirs(other)
            with open(os.path.join(other, "y.txt"), "w", encoding="utf-8") as fh:
                fh.write(INTEL_SHARING_BUGGY)

            result = audit(mod_path=td)
            self.assertEqual(result.files_audited, 1)
            self.assertEqual(len(result.flags), 1)

            report = render_report(result)
            self.assertIn("multiplier-variable persistence audit report", report)
            self.assertIn("_best_boost", report)
            self.assertIn("- unreviewed: 1", report)

    def test_report_reports_none_when_clean(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "events"))
            report = render_report(audit(mod_path=td))
            self.assertIn("_None._", report)
            self.assertIn("- total flags: 0", report)


if __name__ == "__main__":
    unittest.main()
