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


# The megaproject display bug (2026-10-01): a state pulse re-applied each
# construction site's progress modifier with `this.var:`, which inside
# every_scope_building is the building. Buildings hold no variables, so the read
# returned 'none' and the engine scaled the modifier by 1 (a constant "+100%").
SPACE_ELEVATOR_BUGGY = """space_elevator_on_action = {
\teffect = {
\t\tif = {
\t\t\tlimit = { has_building = building_space_elevator_construction_site }
\t\t\tspace_elevator_construction = yes
\t\t\tevery_scope_building = {
\t\t\t\tlimit = { is_building_type = building_space_elevator_construction_site }
\t\t\t\tremove_modifier = space_elevator_progress
\t\t\t\tadd_modifier = {
\t\t\t\t\tname = space_elevator_progress
\t\t\t\t\tmultiplier = this.var:space_elevator_progress_var
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
"""


class BuildingScopeTests(unittest.TestCase):
    def test_reproduces_megaproject_progress_bug(self):
        flags = _scan(SPACE_ELEVATOR_BUGGY)
        self.assertEqual(len(flags), 1)
        f = flags[0]
        self.assertEqual(f.check, "building_scope")
        self.assertEqual(f.variable, "space_elevator_progress_var")
        self.assertEqual(f.multiplier, "this.var:space_elevator_progress_var")
        self.assertEqual(f.modifier_name, "space_elevator_progress")
        self.assertEqual(f.block, "space_elevator_on_action")
        self.assertEqual(f.add_line, 11)
        self.assertEqual(f.scope_block, "every_scope_building")
        self.assertEqual(f.scope_line, 6)

    def test_root_var_is_clean(self):
        fixed = SPACE_ELEVATOR_BUGGY.replace("this.var:", "root.var:")
        self.assertEqual(_scan(fixed), [])

    def test_bare_var_in_building_scope_is_flagged(self):
        flags = _scan(SPACE_ELEVATOR_BUGGY.replace("this.var:", "var:"))
        self.assertEqual([f.multiplier for f in flags],
                         ["var:space_elevator_progress_var"])

    def test_timed_modifier_is_still_flagged(self):
        flags = _scan(
            "se = {\n"
            "\trandom_scope_building = {\n"
            "\t\tadd_modifier = { name = m multiplier = var:x days = 30 }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual([f.check for f in flags], ["building_scope"])

    def test_b_link_opens_a_building_scope(self):
        flags = _scan(
            "se = {\n"
            "\tb:building_university = { add_modifier = { name = m multiplier = var:x } }\n"
            "}\n"
        )
        self.assertEqual([f.scope_block for f in flags], ["b:building_university"])

    def test_control_flow_between_iterator_and_modifier_is_transparent(self):
        flags = _scan(
            "se = {\n"
            "\tevery_scope_building = {\n"
            "\t\tif = { limit = { level > 1 }\n"
            "\t\t\trandom_list = { 10 = { add_modifier = { name = m multiplier = var:x } } }\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)

    def test_scope_change_inside_the_iterator_ends_the_building_scope(self):
        # `owner` / `state` leave the building, and they hold variables.
        for link in ("owner", "state"):
            text = (
                "se = {\n"
                "\tevery_scope_building = {\n"
                f"\t\t{link} = {{ add_modifier = {{ name = m multiplier = var:x }} }}\n"
                "\t}\n"
                "}\n"
            )
            self.assertEqual(_scan(text), [], link)

    def test_modifier_outside_any_building_scope_is_clean(self):
        self.assertEqual(_scan(
            "se = {\n"
            "\tevery_scope_state = { add_modifier = { name = m multiplier = var:x } }\n"
            "}\n"
        ), [])

    def test_reviewed_on_multiplier_line_suppresses(self):
        flags = _scan(SPACE_ELEVATOR_BUGGY.replace(
            "progress_var\n", "progress_var # REVIEWED 2026-10-01: probe\n"))
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].exemption["rationale"], "probe")

    def test_report_names_the_building_scope(self):
        from modifier_multiplier_var_audit import AuditResult
        report = render_report(AuditResult(flags=_scan(SPACE_ELEVATOR_BUGGY)))
        self.assertIn("inside `every_scope_building` (line 6)", report)
        self.assertIn("root.var:space_elevator_progress_var", report)


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

    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line numbers but names its block,
        modifier and variable, and Coverage prints no file count, so the report
        changes only when the findings do."""
        from modifier_multiplier_var_audit import AuditResult, Flag
        result = AuditResult(flags=[
            Flag("common/scripted_effects/y.txt", 120, 131, "_boost", "var:_boost",
                 "boost_mod", "te_apply_boost", 110,
                 exemption={"date": "2026-06-02", "rationale": "timed elsewhere"}),
            Flag("common/scripted_effects/z.txt", 60, 64, "_rate", "var:_rate",
                 "rate_mod", "te_apply_rate", 55),
        ], files_audited=201)
        report = render_report(result)
        self.assertIn(
            "- `common/scripted_effects/y.txt` — `te_apply_boost`: `boost_mod` with "
            "`multiplier = var:_boost`, `_boost` removed — **2026-06-02**: "
            "timed elsewhere", report)
        for gone in ("y.txt:120", "line 131", "files audited", "201"):
            self.assertNotIn(gone, report)
        # The unreviewed entry keeps its lines.
        self.assertIn("- `te_apply_rate` (line 55): `rate_mod` applied at line 60", report)
        self.assertIn("is removed at line 64", report)


if __name__ == "__main__":
    unittest.main()
