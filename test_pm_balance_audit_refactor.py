"""Golden-output stability test for scripts/analysis/pm_balance_audit.py.

Snapshot lives at tests/golden/pm_balance_audit.txt. The audit script's
stdout (run against the real `common/production_methods/`) must match the
snapshot byte-for-byte.

If a real PM file change causes a legitimate output diff, regenerate the
golden via:
    .venv/bin/python scripts/analysis/pm_balance_audit.py > tests/golden/pm_balance_audit.txt

Run:
    .venv/bin/python -m unittest test_pm_balance_audit_refactor -v
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
GOLDEN = REPO / "tests" / "golden" / "pm_balance_audit.txt"
AUDIT = REPO / "scripts" / "analysis" / "pm_balance_audit.py"


class PmBalanceAuditOutputTests(unittest.TestCase):
    def test_audit_output_matches_golden(self) -> None:
        if not GOLDEN.exists():
            self.skipTest(f"golden file missing: {GOLDEN}")
        result = subprocess.run(
            [sys.executable, str(AUDIT)],
            capture_output=True,
            text=True,
            cwd=REPO,
            check=True,
        )
        actual = result.stdout
        expected = GOLDEN.read_text()
        if actual != expected:
            # Helpful diff hint; full diff would be huge so just first divergence.
            for i, (a, b) in enumerate(zip(actual.splitlines(),
                                           expected.splitlines())):
                if a != b:
                    self.fail(
                        f"Output diverges at line {i+1}:\n"
                        f"  actual:   {a!r}\n"
                        f"  expected: {b!r}\n"
                        f"Regenerate via: .venv/bin/python {AUDIT} > {GOLDEN}"
                    )
            self.fail("Output length differs from golden — regenerate snapshot.")
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
