"""Unit tests for scripts/analysis/strata_social_axis_audit.

Run: python3 test_strata_social_axis_audit.py
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "scripts" / "analysis"))

import strata_social_axis_audit as audit_mod


def _write_event_file(tmp: Path, name: str, body: str) -> None:
    events_dir = tmp / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    (events_dir / name).write_text(body, encoding="utf-8")


PROGRESSIVE_MIRROR_OPTION = """\
\toption = {
\t\tname = test.1.a
\t\tadd_radicals = { value = small_radicals strata = upper }
\t\tadd_loyalists = { value = small_radicals strata = lower }
\t}
"""

REGRESSIVE_MIRROR_OPTION = """\
\toption = {
\t\tname = test.1.b
\t\tadd_loyalists = { value = small_radicals strata = upper }
\t\tadd_radicals = { value = small_radicals strata = lower }
\t}
"""

PARTIAL_PROGRESSIVE_OPTION = """\
\toption = {
\t\tname = test.2.a
\t\tadd_radicals = { value = small_radicals strata = upper }
\t}
"""

PARTIAL_REGRESSIVE_OPTION = """\
\toption = {
\t\tname = test.2.b
\t\tadd_loyalists = { value = small_radicals strata = upper }
\t}
"""

ECONOMIC_SINGLE_STRATA_OPTION = """\
\toption = {
\t\tname = bank.1.a
\t\tadd_radicals = { value = small_radicals strata = upper }
\t}
"""

NO_STRATA_OPTION = """\
\toption = {
\t\tname = quiet.1.a
\t\tadd_modifier = { name = some_modifier days = normal_modifier_time }
\t}
"""


def _event(event_id: str, *options: str) -> str:
    return (
        f"{event_id} = {{\n"
        + "\ttype = country_event\n"
        + "\tplacement = root\n"
        + "".join(options)
        + "}\n"
    )


class Tier1WithinOptionMirrorTests(unittest.TestCase):
    def test_progressive_mirror_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _write_event_file(
                tmp, "test_events.txt",
                _event("test.1", PROGRESSIVE_MIRROR_OPTION),
            )
            result = audit_mod.audit(tmp)
            self.assertEqual(len(result.tier1), 1)
            self.assertEqual(result.tier1[0].event_id, "test.1")
            self.assertEqual(result.tier1[0].option_name, "test.1.a")
            self.assertIn("upper-radicals", result.tier1[0].shape)
            self.assertIn("lower-loyalists", result.tier1[0].shape)
            self.assertEqual(len(result.tier2), 0)

    def test_regressive_mirror_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _write_event_file(
                tmp, "test_events.txt",
                _event("test.1", REGRESSIVE_MIRROR_OPTION),
            )
            result = audit_mod.audit(tmp)
            self.assertEqual(len(result.tier1), 1)
            self.assertIn("upper-loyalists", result.tier1[0].shape)
            self.assertIn("lower-radicals", result.tier1[0].shape)

    def test_partial_strata_not_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _write_event_file(
                tmp, "test_events.txt",
                _event("test.1", PARTIAL_PROGRESSIVE_OPTION),
            )
            result = audit_mod.audit(tmp)
            self.assertEqual(len(result.tier1), 0)
            self.assertEqual(len(result.tier2), 0)

    def test_pure_economic_event_not_flagged(self):
        """An economic-axis event with a single-direction strata reaction
        (e.g. upper-radicals on a bank-failure event) should NOT trip the
        audit. The bug-class is the mirrored shape, not strata-reactions
        in general."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _write_event_file(
                tmp, "bank_events.txt",
                _event("bank.1", ECONOMIC_SINGLE_STRATA_OPTION),
            )
            result = audit_mod.audit(tmp)
            self.assertEqual(len(result.tier1), 0)
            self.assertEqual(len(result.tier2), 0)


class Tier2CrossOptionFlipTests(unittest.TestCase):
    def test_cross_option_flip_flagged(self):
        """One partial-progressive option + one partial-regressive option →
        Tier 2 fires."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _write_event_file(
                tmp, "test_events.txt",
                _event(
                    "test.2",
                    PARTIAL_PROGRESSIVE_OPTION,
                    PARTIAL_REGRESSIVE_OPTION,
                ),
            )
            result = audit_mod.audit(tmp)
            self.assertEqual(len(result.tier1), 0)
            self.assertEqual(len(result.tier2), 1)
            self.assertEqual(result.tier2[0].event_id, "test.2")

    def test_tier1_event_suppresses_tier2(self):
        """An event whose options are within-option mirrors gets listed at
        Tier 1; Tier 2 doesn't double-list it."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _write_event_file(
                tmp, "test_events.txt",
                _event(
                    "test.3",
                    PROGRESSIVE_MIRROR_OPTION,
                    REGRESSIVE_MIRROR_OPTION,
                ),
            )
            result = audit_mod.audit(tmp)
            self.assertEqual(len(result.tier1), 2)
            self.assertEqual(len(result.tier2), 0)


class ExceptionsDocTests(unittest.TestCase):
    def test_exempted_event_moves_to_exempted_bucket(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _write_event_file(
                tmp, "bank_events.txt",
                _event("bank.12", PROGRESSIVE_MIRROR_OPTION),
            )
            audits_dir = tmp / "docs" / "audits"
            audits_dir.mkdir(parents=True)
            (audits_dir / "strata_social_axis_exceptions.md").write_text(
                "# Strata exceptions\n\n"
                "- `bank.12` — Bank failure wipes upper-strata bondholder equity "
                "in a way no lower-strata pop is exposed to. The strata reaction "
                "here is incidence of an economic shock, not a social-progressivism proxy.\n",
                encoding="utf-8",
            )
            result = audit_mod.audit(tmp)
            self.assertEqual(len(result.tier1), 0, "exempted event must not be in unexempted bucket")
            self.assertEqual(len(result.exempted_tier1), 1)
            self.assertEqual(result.exempted_tier1[0].event_id, "bank.12")

    def test_load_exceptions_parses_bullet_entries(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            audits_dir = tmp / "docs" / "audits"
            audits_dir.mkdir(parents=True)
            (audits_dir / "strata_social_axis_exceptions.md").write_text(
                "# header\n\n"
                "- `event.1` — context.\n"
                "* `event.2` — context with asterisk bullet.\n"
                "  - `event.3` — indented bullet.\n"
                "- not_an_event_id — no backticks; skip.\n"
                "- `event.4`\n"  # no rationale, but parser still grabs the id
                "Regular line — no bullet, skip.\n",
                encoding="utf-8",
            )
            exempt = audit_mod.load_exceptions(tmp)
            self.assertEqual(exempt, {"event.1", "event.2", "event.3", "event.4"})


class CommentAndStringRobustnessTests(unittest.TestCase):
    def test_comments_with_braces_dont_break_parsing(self):
        body = (
            "# this { confuses } naive parsers\n"
            + _event("test.4", PROGRESSIVE_MIRROR_OPTION)
        )
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _write_event_file(tmp, "test_events.txt", body)
            result = audit_mod.audit(tmp)
            self.assertEqual(len(result.tier1), 1)
            self.assertEqual(result.tier1[0].event_id, "test.4")

    def test_replace_or_inject_prefix_handled(self):
        body = (
            "INJECT:test.5 = {\n"
            "\ttype = country_event\n"
            + PROGRESSIVE_MIRROR_OPTION
            + "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _write_event_file(tmp, "test_events.txt", body)
            result = audit_mod.audit(tmp)
            self.assertEqual(len(result.tier1), 1)
            self.assertEqual(result.tier1[0].event_id, "test.5")


class ReportRenderTests(unittest.TestCase):
    def test_empty_result_renders_none_sections(self):
        result = audit_mod.AuditResult(files_audited=5)
        rendered = audit_mod.render_report(result)
        self.assertIn("# Strata vs social-axis audit report", rendered)
        self.assertIn("Tier 1 — within-option mirrors (0)", rendered)
        self.assertIn("_None._", rendered)
        self.assertIn("files audited: 5", rendered)

    def test_flag_appears_in_report(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _write_event_file(
                tmp, "test_events.txt",
                _event("test.6", PROGRESSIVE_MIRROR_OPTION),
            )
            result = audit_mod.audit(tmp)
            rendered = audit_mod.render_report(result)
            self.assertIn("`test.6`", rendered)
            # The fixture's option name is hardcoded as test.1.a regardless of event id;
            # we just need to confirm the option appears in the report.
            self.assertIn("test.1.a", rendered)
            self.assertIn("upper-radicals + lower-loyalists", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
