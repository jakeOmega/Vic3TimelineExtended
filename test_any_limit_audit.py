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

    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line number and Coverage no file count,
        so the report changes only when the findings do."""
        from any_limit_audit import AuditResult, Flag
        result = AuditResult(flags=[
            Flag("common/scripted_effects/x.txt", 3, "any_scope_state", 2),
            Flag("common/scripted_effects/y.txt", 40, "any_country", 39,
                 exemption={"date": "2026-05-21", "rationale": "deliberate"}),
        ], files_audited=418)
        report = render_report(result)
        self.assertIn(
            "- `common/scripted_effects/y.txt` — `limit` inside `any_country` — "
            "**2026-05-21**: deliberate", report)
        self.assertNotIn("y.txt:40", report)
        self.assertIn("- line 3: `limit` inside `any_scope_state` (opened at line 2)",
                      report)  # unreviewed keeps its lines
        self.assertNotIn("files audited", report)
        self.assertNotIn("418", report)


class AlwaysFalseTests(unittest.TestCase):
    """`always = no` as an any_* body: always false, silently kills its limit."""

    def test_flags_multiline_body(self):
        # The colonial_collapse_effect shape that kept the effect off.
        flags = _scan(
            "colonial_collapse_effect = {\n"
            "\tif = {\n"
            "\t\tlimit = {\n"
            "\t\t\tis_subject = no\n"
            "\t\t\tany_civil_war = {\n"
            "\t\t\t\talways = no\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].kind, "always_false")
        self.assertEqual(flags[0].any_name, "any_civil_war")
        self.assertEqual(flags[0].line, 6)
        self.assertEqual(flags[0].any_line, 5)

    def test_flags_one_line_body(self):
        flags = _scan("t = {\n\tany_scope_state = { always = no }\n}\n")
        self.assertEqual([(f.kind, f.line, f.any_line) for f in flags],
                         [("always_false", 2, 2)])

    def test_flags_always_false_spelling_and_other_conditions(self):
        flags = _scan(
            "any_country = {\n\tis_at_war = yes\n\talways = false\n}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].line, 3)

    def test_flags_under_not(self):
        # Under NOT it is always true instead: just as dead.
        flags = _scan("limit = {\n\tNOT = { any_civil_war = { always = no } }\n}\n")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].any_name, "any_civil_war")

    def test_no_flag_for_bare_always_no(self):
        # A retired potential / possible / limit is deliberate.
        flags = _scan(
            "my_decision = {\n"
            "\tpotential = {\n\t\talways = no\n\t}\n"
            "\tpossible = { always = no }\n"
            "\teffect = { if = { limit = { always = no } } }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_when_not_the_immediate_parent(self):
        flags = _scan(
            "any_scope_state = {\n"
            "\ttrigger_if = {\n\t\tlimit = { is_coastal = yes }\n\t\talways = no\n\t}\n"
            "\tevery_scope_pop = { limit = { always = no } }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_for_always_yes_or_empty_body(self):
        flags = _scan(
            "t = {\n\tany_civil_war = { always = yes }\n\tany_civil_war = { }\n}\n"
        )
        self.assertEqual(flags, [])

    def test_reviewed_on_opener_or_always_line_suppresses(self):
        flags = _scan(
            "any_country = { # REVIEWED 2026-09-26: switched off on purpose\n"
            "\talways = no\n"
            "}\n"
            "any_scope_state = {\n"
            "\talways = no # REVIEWED 2026-09-26: placeholder, see #999\n"
            "}\n"
        )
        self.assertEqual(len(flags), 2)
        self.assertTrue(all(f.exemption for f in flags))
        self.assertEqual(flags[1].exemption["rationale"], "placeholder, see #999")

    def test_report_names_the_kind(self):
        with tempfile.TemporaryDirectory() as td:
            cdir = os.path.join(td, "common", "scripted_effects")
            os.makedirs(cdir)
            with open(os.path.join(cdir, "x.txt"), "w", encoding="utf-8") as fh:
                fh.write("se = {\n\tif = { limit = { any_civil_war = { always = no } } }\n}\n")
            report = render_report(audit(mod_path=td))
            self.assertIn("- line 2: `always = no` inside `any_civil_war` (opened at line 2)",
                          report)
            self.assertIn("- `always = no` flags: 1", report)


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
