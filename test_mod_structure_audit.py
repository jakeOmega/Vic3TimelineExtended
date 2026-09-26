"""Unit tests for mod_structure_audit's report rendering.

Run: python3 test_mod_structure_audit.py
"""
import unittest

from mod_structure_audit import AuditResult, Flag, render_report


class RenderReportTests(unittest.TestCase):
    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line numbers, neither its own nor the
        ones its detail cites, and Coverage no file count, so the report
        changes only when the findings do. Unreviewed flags keep their lines."""
        result = AuditResult(
            flags=[
                Flag("collision", "common/laws/b.txt", 30,
                     "Duplicate top-level `law_x = { ... }` in `common/laws/` "
                     "(also at `common/laws/a.txt:5`); engine drops all but one silently."),
                Flag("inject", "common/buildings/c.txt", 44,
                     "`INJECT:building_y` won't merge: mod-only entity defined at "
                     "`common/buildings/d.txt:12`. Edit the definition directly.",
                     exemption={"date": "2026-06-01", "rationale": "load order checked"}),
            ],
            files_audited=366,
        )
        report = render_report(result)
        self.assertIn(
            "- `common/buildings/c.txt` — `INJECT:building_y` won't merge: mod-only entity "
            "defined at `common/buildings/d.txt`. Edit the definition directly. — "
            "**2026-06-01**: load order checked", report)
        self.assertNotIn("c.txt:44", report)
        self.assertNotIn("d.txt:12", report)
        self.assertIn("- `common/laws/b.txt:30` — Duplicate top-level", report)
        self.assertIn("(also at `common/laws/a.txt:5`)", report)
        self.assertNotIn("files audited", report)
        self.assertNotIn("366", report)
        self.assertIn("  - inject: 1", report)


if __name__ == "__main__":
    unittest.main()
