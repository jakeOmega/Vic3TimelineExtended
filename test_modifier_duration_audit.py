"""Unit tests for modifier_duration_audit.

`add_modifier`'s `days` reads a script value written as a block, or computed,
as 0 days: the Planned Capital option said "for 0 days" on both its modifiers.
A literal or a script value written as a bare number (vanilla's
`normal_modifier_time = 1825`) is read right and must not flag. A scripted
effect that passes its own `$DAYS$` to the field is followed to its callers.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import modifier_duration_audit
from modifier_duration_audit import AuditResult, Flag, audit, render_report

VALUES = (
    "bare_days = 1825\n"
    "block_days = { value = 7300 }\n"
    "computed_days = {\n"
    "\tvalue = normal_modifier_time\n"
    "\tmultiply = pace_mult\n"
    "}\n"
    "alias_days = bare_days\n"
)


_ROOTS: list[str] = []


def tearDownModule():
    for root in _ROOTS:
        shutil.rmtree(root, ignore_errors=True)


def _mod(files: dict[str, str], vanilla: dict | None = None) -> str:
    """A throwaway mod tree; `vanilla` stands in for the script_values snapshot."""
    root = tempfile.mkdtemp()
    _ROOTS.append(root)
    files = {"common/script_values/v.txt": VALUES, **files}
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write(text)
    snapshot = os.path.join(root, "vanilla_parsed", "common")
    os.makedirs(snapshot)
    with open(os.path.join(snapshot, "script_values.json"), "w", encoding="utf-8") as fh:
        json.dump(vanilla if vanilla is not None else {
            "normal_modifier_time": ["=", "1825"],
            "vanilla_block": ["=", {"value": ["=", "3"]}],
        }, fh)
    return root


def _flags(event_body: str, **extra) -> list[Flag]:
    files = {"events/e.txt": "e.1 = {\n\timmediate = {\n" + event_body + "\t}\n}\n", **extra}
    return audit(mod_path=_mod(files)).flags


class DirectSiteTests(unittest.TestCase):
    def test_reproduces_planned_capital_bug(self):
        flags = _flags("\t\tadd_modifier = {\n\t\t\tname = te_demog_pc_works\n\t\t\tdays = block_days\n\t\t}\n")
        self.assertEqual([(f.line, f.opener_line, f.key, f.value, f.problem, f.modifier) for f in flags],
                         [(5, 3, "days", "block_days", "block", "te_demog_pc_works")])
        self.assertIn("common/script_values/v.txt:2", flags[0].detail)

    def test_computed_value_flags(self):
        flags = _flags("\t\tadd_modifier = { name = x days = computed_days is_decaying = yes }\n")
        self.assertEqual([(f.value, f.problem) for f in flags], [("computed_days", "block")])

    def test_months_and_years_flag_too(self):
        flags = _flags("\t\tadd_modifier = { name = x months = block_days }\n"
                       "\t\tadd_modifier = { name = y years = block_days }\n")
        self.assertEqual([f.key for f in flags], ["months", "years"])

    def test_literals_and_bare_values_pass(self):
        flags = _flags("\t\tadd_modifier = { name = a days = 1825 }\n"
                       "\t\tadd_modifier = { name = b months = -1 }\n"
                       "\t\tadd_modifier = { name = c days = bare_days }\n"
                       "\t\tadd_modifier = { name = d days = normal_modifier_time }\n"
                       "\t\tadd_modifier = { name = e }\n")
        self.assertEqual(flags, [])

    def test_vanilla_block_flags(self):
        flags = _flags("\t\tadd_modifier = { name = x days = vanilla_block }\n")
        self.assertEqual([(f.problem, "vanilla" in f.detail) for f in flags], [("block", True)])

    def test_alias_inline_block_unknown_name_and_variable_flag(self):
        flags = _flags("\t\tadd_modifier = { name = a days = alias_days }\n"
                       "\t\tadd_modifier = { name = b days = { value = 30 } }\n"
                       "\t\tadd_modifier = { name = c days = no_such_value }\n"
                       "\t\tadd_modifier = { name = d days = var:left }\n")
        self.assertEqual([(f.modifier, f.problem) for f in flags],
                         [("a", "alias"), ("b", "inline_block"), ("c", "not_a_constant"),
                          ("d", "not_a_constant")])

    def test_a_mod_definition_shadows_vanilla(self):
        files = {"common/script_values/z.txt": "normal_modifier_time = { value = 1825 }\n"}
        flags = _flags("\t\tadd_modifier = { name = x days = normal_modifier_time }\n", **files)
        self.assertEqual([f.problem for f in flags], ["block"])

    def test_only_add_modifier_is_checked(self):
        flags = _flags("\t\tset_variable = { name = x value = 1 days = block_days }\n"
                       "\t\tadd_modifier = { name = y multiplier = block_days }\n")
        self.assertEqual(flags, [])

    def test_comments_are_ignored(self):
        flags = _flags("\t\t# add_modifier = { name = x days = block_days }\n"
                       "\t\tadd_modifier = { name = y days = 30 } # days = block_days\n")
        self.assertEqual(flags, [])


HELPER = (
    "# Scope: country\n"
    "approval = {\n"
    "\tevery_interest_group = {\n"
    "\t\tadd_modifier = { name = $MODIFIER$ days = $DAYS$ is_decaying = yes }\n"
    "\t}\n"
    "}\n"
    "forwarder = {\n"
    "\tapproval = { MODIFIER = m DAYS = $LENGTH$ }\n"
    "}\n"
)


class PassThroughTests(unittest.TestCase):
    def test_a_parameter_is_followed_to_its_callers(self):
        files = {"common/scripted_effects/h.txt": HELPER}
        flags = _flags("\t\tapproval = { MODIFIER = m DAYS = block_days }\n"
                       "\t\tapproval = { MODIFIER = m DAYS = normal_modifier_time }\n"
                       "\t\tapproval = {\n\t\t\tMODIFIER = m\n\t\t\tDAYS = 30\n\t\t}\n", **files)
        self.assertEqual([(f.line, f.opener_line, f.key, f.value, f.via) for f in flags],
                         [(3, 3, "DAYS", "block_days", "approval.days")])

    def test_a_forwarded_parameter_is_followed_again(self):
        files = {"common/scripted_effects/h.txt": HELPER}
        flags = _flags("\t\tforwarder = {\n\t\t\tLENGTH = computed_days\n\t\t}\n", **files)
        self.assertEqual([(f.line, f.opener_line, f.key, f.via) for f in flags],
                         [(4, 3, "LENGTH", "forwarder.days")])

    def test_the_followed_parameters_are_reported(self):
        result = audit(mod_path=_mod({"common/scripted_effects/h.txt": HELPER}))
        self.assertEqual(result.params_followed, {"approval": {"DAYS": "days"}, "forwarder": {"LENGTH": "days"}})
        self.assertIn("- `approval`: `$DAYS$` (`days`)", render_report(result))


class SuppressionTests(unittest.TestCase):
    def test_reviewed_on_the_duration_line(self):
        flags = _flags("\t\tadd_modifier = {\n\t\t\tname = x\n"
                       "\t\t\tdays = block_days # REVIEWED 2026-10-23: test\n\t\t}\n")
        self.assertEqual(flags[0].exemption, {"date": "2026-10-23", "rationale": "test"})

    def test_reviewed_on_the_opener_line(self):
        flags = _flags("\t\tadd_modifier = { name = x days = block_days } # REVIEWED 2026-10-23: test\n")
        self.assertIsNotNone(flags[0].exemption)

    def test_reviewed_on_the_call_line(self):
        files = {"common/scripted_effects/h.txt": HELPER}
        flags = _flags("\t\tapproval = { MODIFIER = m DAYS = block_days } # REVIEWED 2026-10-23: test\n", **files)
        self.assertIsNotNone(flags[0].exemption)

    def test_plain_comment_is_not_an_exemption(self):
        flags = _flags("\t\tadd_modifier = { name = x days = block_days } # five years\n")
        self.assertIsNone(flags[0].exemption)


class ReportTests(unittest.TestCase):
    def test_regenerate_writes_report_and_counts(self):
        root = _mod({"events/e.txt": "e.1 = {\n\timmediate = {\n"
                                      "\t\tadd_modifier = { name = x days = block_days }\n"
                                      "\t\tadd_modifier = { name = y days = block_days } # REVIEWED 2026-10-23: test\n"
                                      "\t}\n}\n"})
        with mock.patch("path_constants.mod_path", root):
            summary = modifier_duration_audit.regenerate()
        self.assertEqual({k: summary[k] for k in ("total_flags", "unreviewed", "exempted")},
                         {"total_flags": 2, "unreviewed": 1, "exempted": 1})
        with open(os.path.join(root, "docs", "engine", "modifier_duration_report.md"), encoding="utf-8") as fh:
            report = fh.read()
        self.assertIn("- line 3: `add_modifier` of `x` takes `days = block_days`", report)
        self.assertIn("**2026-10-23**: test", report)

    def test_empty_report_says_none(self):
        report = render_report(AuditResult())
        self.assertEqual(report.count("_None._"), 3)
        self.assertIn("- total flags: 0", report)


class RepoTests(unittest.TestCase):
    def test_the_mod_has_no_unreviewed_flag(self):
        from path_constants import mod_path
        unrev = [f for f in audit(mod_path=mod_path).flags if not f.exemption]
        self.assertEqual(unrev, [])

    def test_post_load_roster_and_ci(self):
        from scripts.analysis.check_post_load_rosters import extract_rosters
        root = os.path.dirname(os.path.abspath(__file__))
        self.assertIn("modifier_duration_audit", extract_rosters(
            os.path.join(root, "mod_state_server.py"))["POST_LOAD_AUDITS"])
        with open(os.path.join(root, ".github", "workflows", "ci.yml"), encoding="utf-8") as fh:
            self.assertIn("python3 modifier_duration_audit.py --strict", fh.read())


if __name__ == "__main__":
    unittest.main()
