"""Unit tests for modifier_visibility_audit's report rendering.

Run: python3 test_modifier_visibility_audit.py
"""
import unittest

from modifier_visibility_audit import AuditResult, VisibilityFlag, render_report


def _flag(line: int, exemption: dict | None = None) -> VisibilityFlag:
    return VisibilityFlag(
        file="common/static_modifiers/extra_modifiers.txt", line=line,
        modifier="state_construction_mult", value="-0.0001", value_float=-0.0001,
        decimals=0, percent=True, min_visible=0.005, exemption=exemption,
    )


class RenderReportTests(unittest.TestCase):
    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line number and Coverage no file or
        registry counts, so the report changes only when the findings do."""
        result = AuditResult(
            flags=[
                _flag(12),
                _flag(371, {"date": "2026-05-06", "rationale": "multiplied by a big number"}),
            ],
            coverage={"files_audited": 320, "modifiers_in_registry_with_decimals": 2738,
                      "registry_hits": 7610},
        )
        report = render_report(result)
        self.assertIn(
            "- `common/static_modifiers/extra_modifiers.txt` — "
            "`state_construction_mult = -0.0001` (displays as +0%) — "
            "**2026-05-06**: multiplied by a big number", report)
        self.assertNotIn("extra_modifiers.txt:371", report)
        self.assertIn("`common/static_modifiers/extra_modifiers.txt:12`", report)  # unreviewed
        for gone in ("files_audited", "modifiers_in_registry_with_decimals",
                     "registry_hits", "2738", "7610"):
            self.assertNotIn(gone, report)
        self.assertIn("- total flags: 2", report)
        self.assertIn("- exempted: 1", report)


if __name__ == "__main__":
    unittest.main()
