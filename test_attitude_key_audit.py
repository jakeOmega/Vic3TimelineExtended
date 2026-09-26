"""Unit tests for attitude_key_audit's report rendering.

Run: python3 test_attitude_key_audit.py
"""
import unittest

from attitude_key_audit import AttitudeFlag, AuditResult, render_report


class RenderReportTests(unittest.TestCase):
    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line number and Coverage no file or
        reference count (the engine's catalog size stays), so the report
        changes only when the findings do."""
        result = AuditResult(
            flags=[
                AttitudeFlag("common/ai_strategies/a.txt", 8, "friendly"),
                AttitudeFlag("common/ai_strategies/b.txt", 61, "hostile",
                             exemption={"date": "2026-06-05", "rationale": "legacy alias"}),
            ],
            files_scanned=418, refs_checked=215,
        )
        report = render_report(result)
        self.assertIn(
            "- `common/ai_strategies/b.txt` — `attitude = hostile` — "
            "**2026-06-05**: legacy alias", report)
        self.assertNotIn("b.txt:61", report)
        self.assertIn("- `common/ai_strategies/a.txt:8`", report)  # unreviewed
        for gone in ("script files scanned", "attitude references checked", "418", "215"):
            self.assertNotIn(gone, report)
        self.assertIn("- valid catalog keys: 15", report)


if __name__ == "__main__":
    unittest.main()
