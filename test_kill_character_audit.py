"""Unit tests for kill_character_audit's report rendering.

Run: python3 test_kill_character_audit.py
"""
import unittest

from kill_character_audit import AuditFlag, render_report


class RenderReportTests(unittest.TestCase):
    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line number and the header no file
        count, so the report changes only when the findings do. Hard fails keep
        their lines."""
        flags = [
            AuditFlag(file="events/a.txt", line=10, event_id="a.1", target_scope="spy",
                      has_void6=False, has_exists_guard=False, reason="no guard"),
            AuditFlag(file="events/b.txt", line=90, event_id="b.4", target_scope="heir",
                      has_void6=False, has_exists_guard=False, reason="no guard",
                      exemption={"date": "2026-05-01", "rationale": "vanilla character"}),
        ]
        report = render_report(flags, files_audited=52)
        self.assertIn(
            "- `events/b.txt` — event `b.4` — target `scope:heir` — "
            "2026-05-01: vanilla character", report)
        self.assertNotIn("b.txt:90", report)
        self.assertIn("- `events/a.txt:10` — event `a.1`", report)
        self.assertNotIn("Files audited", report)
        self.assertNotIn("52", report)
        self.assertIn("Reviewed exemptions: **1**.", report)


if __name__ == "__main__":
    unittest.main()
