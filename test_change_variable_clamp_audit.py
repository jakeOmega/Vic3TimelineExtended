"""Unit tests for change_variable_clamp_audit.

A `min` or `max` directly inside `change_variable` (or its global / local
twins) flags: vanilla never writes it, and the mod wrote `max = 0` ten times
meaning a floor. A `min` / `max` nested in a script-value block inside the
change, and `clamp_variable`'s own bounds, must not flag.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

import change_variable_clamp_audit
from change_variable_clamp_audit import AuditResult, Flag, audit, render_report, scan_text


def _flags(text: str):
    return scan_text(text, "f.txt")


class DetectionTests(unittest.TestCase):
    def test_reproduces_nuclear_setback_bug(self):
        # nuclear_weapon_events.19.a before the fix: one-line blocks.
        flags = _flags(
            "option = {\n"
            "\tcustom_tooltip = {\n"
            "\t\ttext = NW_PROGRESS_SUBTRACT_15_TT\n"
            "\t\tchange_variable = { name = nuclear_weapon_program_progress subtract = 15 }\n"
            "\t\tchange_variable = { name = nuclear_weapon_program_progress max = 0 }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(
            [(f.line, f.opener_line, f.effect, f.bound, f.value, f.name) for f in flags],
            [(5, 5, "change_variable", "max", "0", "nuclear_weapon_program_progress")],
        )

    def test_reproduces_election_worst_phase_bug(self):
        # covert_op_election_confidence_effect: the change sits in a scope change.
        flags = _flags(
            "if = {\n"
            "\tlimit = { covert_op_is_fully_operational = yes }\n"
            "\tROOT = { change_variable = { name = iw_election_worst_phase max = 3 } }\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.name, f.value) for f in flags],
                         [(3, "iw_election_worst_phase", "3")])

    def test_multi_line_block_flags_the_bound_line(self):
        flags = _flags(
            "e = {\n"
            "\tchange_variable = {\n"
            "\t\tname = x\n"
            "\t\tadd = 5\n"
            "\t\tmin = var:x_floor\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.opener_line, f.bound, f.value) for f in flags],
                         [(5, 2, "min", "var:x_floor")])

    def test_global_and_local_twins_flag(self):
        flags = _flags(
            "e = {\n"
            "\tchange_global_variable = { name = g max = 10 }\n"
            "\tchange_local_variable = { name = l min = 1 }\n"
            "}\n"
        )
        self.assertEqual([(f.effect, f.bound) for f in flags],
                         [("change_global_variable", "max"), ("change_local_variable", "min")])

    def test_block_valued_bound_flags(self):
        flags = _flags("e = { change_variable = { name = x max = { value = y } } }\n")
        self.assertEqual([(f.bound, f.value) for f in flags], [("max", "{")])

    def test_both_bounds_flag_separately(self):
        flags = _flags("e = { change_variable = { name = x min = 0 max = 5 } }\n")
        self.assertEqual([f.bound for f in flags], ["min", "max"])

    def test_script_value_clamp_nested_in_the_change_does_not_flag(self):
        self.assertEqual(_flags(
            "e = {\n"
            "\tchange_variable = {\n"
            "\t\tname = x\n"
            "\t\tadd = { value = y max = 3 min = 0 }\n"
            "\t}\n"
            "}\n"
        ), [])

    def test_clamp_variable_and_other_blocks_do_not_flag(self):
        self.assertEqual(_flags(
            "e = {\n"
            "\tclamp_variable = { name = x max = 120 min = 0 }\n"
            "\tclamp_global_variable = { name = g max = 1 min = 0 }\n"
            "\tset_variable = { name = x value = { value = y min = 0 } }\n"
            "\tchange_variable = { name = x add = 1 }\n"
            "}\n"
            "sv = { value = 3 max = 1 min = 0 }\n"
        ), [])

    def test_comments_and_strings_are_ignored(self):
        self.assertEqual(_flags(
            "e = {\n"
            "\t# change_variable = { name = x max = 0 }\n"
            "\tchange_variable = { name = x add = 1 } # max = 0\n"
            "\tcustom_tooltip = \"change_variable = { name = x max = 0 }\"\n"
            "}\n"
        ), [])

    def test_unnamed_change_still_flags(self):
        flags = _flags("e = { change_variable = { max = 0 } }\n")
        self.assertEqual([(f.name, f.bound) for f in flags], [(None, "max")])


class ExemptionTests(unittest.TestCase):
    TEXT = (
        "e = {{\n"
        "\tchange_variable = {{ name = s max = 0 }}{on_one_line}\n"
        "\tchange_variable = {{{on_opener}\n"
        "\t\tname = u\n"
        "\t\tmin = 2{on_bound}\n"
        "\t}}\n"
        "}}\n"
    )
    NOTE = " # REVIEWED 2026-09-26: a test"

    def test_unreviewed(self):
        flags = _flags(self.TEXT.format(on_one_line="", on_opener="", on_bound=""))
        self.assertEqual([f.exemption for f in flags], [None, None])

    def test_reviewed_on_bound_line(self):
        flags = _flags(self.TEXT.format(on_one_line=self.NOTE, on_opener="", on_bound=self.NOTE))
        self.assertEqual([f.exemption["rationale"] for f in flags], ["a test", "a test"])

    def test_reviewed_on_opener_line(self):
        flags = _flags(self.TEXT.format(on_one_line="", on_opener=self.NOTE, on_bound=""))
        self.assertEqual([f.name for f in flags if f.exemption], ["u"])

    def test_plain_comment_is_not_an_exemption(self):
        flags = _flags(self.TEXT.format(on_one_line=" # floor at 0", on_opener="", on_bound=""))
        self.assertIsNone(flags[0].exemption)


class AuditTests(unittest.TestCase):
    def _tree(self, tmp):
        os.makedirs(os.path.join(tmp, "common", "scripted_effects"))
        os.makedirs(os.path.join(tmp, "events"))
        os.makedirs(os.path.join(tmp, "gui"))
        with open(os.path.join(tmp, "common", "scripted_effects", "a.txt"), "w", encoding="utf-8-sig") as fh:
            fh.write("a = { change_variable = { name = k max = 0 } }\n")
        with open(os.path.join(tmp, "events", "b.txt"), "w", encoding="utf-8") as fh:
            fh.write("b.1 = { immediate = { clamp_variable = { name = k2 max = 3 min = 0 } } }\n")
        # Outside the audited dirs: never read.
        with open(os.path.join(tmp, "gui", "c.txt"), "w", encoding="utf-8") as fh:
            fh.write("c = { change_variable = { name = k3 max = 0 } }\n")

    def test_audit_walks_common_and_events_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._tree(tmp)
            result = audit(mod_path=tmp)
            self.assertEqual(result.files_audited, 2)
            self.assertEqual([(f.file, f.name) for f in result.flags],
                             [(os.path.join("common", "scripted_effects", "a.txt"), "k")])
            report = render_report(result)
            self.assertIn("- line 1: `change_variable` of `k` carries `max = 0`", report)
            self.assertIn("- unreviewed: 1", report)

    def test_regenerate_writes_report_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._tree(tmp)
            with mock.patch("path_constants.mod_path", tmp):
                summary = change_variable_clamp_audit.regenerate()
            self.assertEqual(summary, {
                "files_audited": 2, "total_flags": 1, "unreviewed": 1, "exempted": 0,
            })
            with open(os.path.join(tmp, "docs", "engine", "change_variable_clamp_report.md"),
                      encoding="utf-8") as fh:
                self.assertIn("carries `max = 0`", fh.read())

    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line number and Coverage no file count,
        so the report changes only when the findings do."""
        result = AuditResult(flags=[
            Flag("common/scripted_effects/a.txt", 7, 7, "change_variable", "max", "0", "k"),
            Flag("common/scripted_effects/b.txt", 70, 68, "change_variable", "min", "2", "cool",
                 exemption={"date": "2026-09-26", "rationale": "floor on purpose"}),
        ], files_audited=490)
        report = render_report(result)
        self.assertIn(
            "- `common/scripted_effects/b.txt` — `change_variable` of `cool` carries "
            "`min = 2` — **2026-09-26**: floor on purpose", report)
        self.assertNotIn("b.txt:70", report)
        self.assertIn("- line 7: `change_variable` of `k`", report)  # unreviewed
        for gone in ("files audited", "490"):
            self.assertNotIn(gone, report)

    def test_empty_report_says_none(self):
        report = render_report(AuditResult())
        self.assertEqual(report.count("_None._"), 2)
        self.assertIn("- total flags: 0", report)


if __name__ == "__main__":
    unittest.main()
