"""Tests for the nightly-audit per-run-delta state reconstruction.

State used to live in one committed aggregate that every run mutated; two
unmerged nightly PRs editing it conflicted on merge (#202/#204). It now lives as
`frozen baseline + replay(per-run findings.json deltas)`. These tests pin the
reconstruction contract: fold reproduces a delta-free baseline exactly, applies
deltas in date order, never double-counts a run already folded into the baseline,
skips runs missing a findings.json, and stays equivalent to a direct
`update_state` replay (the property that keeps decay/recency scoring unchanged).
"""

import json
import sys
import tempfile
import unittest
from datetime import date as Date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import nightly_audit_state_update as nas


class FoldStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.baseline = self.root / "baseline.json"
        self.nightly = self.root / "nightly"
        self.nightly.mkdir()
        self.cache = self.root / "cache.json"
        # Redirect module constants at the temp sandbox; restore on teardown.
        self._orig = (nas.BASELINE_FILE, nas.NIGHTLY_DIR, nas.CACHE_FILE)
        nas.BASELINE_FILE = self.baseline
        nas.NIGHTLY_DIR = self.nightly
        nas.CACHE_FILE = self.cache
        self.addCleanup(self._restore)

    def _restore(self):
        nas.BASELINE_FILE, nas.NIGHTLY_DIR, nas.CACHE_FILE = self._orig

    def _write_baseline(self, as_of, files):
        with open(self.baseline, "w") as f:
            json.dump({"version": 1, "as_of": as_of, "files": files}, f)

    def _write_run(self, label, date, targets, findings, *, with_findings=True):
        d = self.nightly / label
        d.mkdir()
        with open(d / "targets.json", "w") as f:
            json.dump({"date": date, "run_label": label, "targets": targets}, f)
        if with_findings:
            with open(d / "findings.json", "w") as f:
                json.dump(findings, f)

    # ----- baseline passthrough --------------------------------------------

    def test_no_deltas_returns_baseline(self):
        files = {"common/a.txt": {"audit_count": 3, "last_audited": "2026-01-01", "recent_findings": 0}}
        self._write_baseline("2026-06-05", files)
        folded = nas.fold_state()
        self.assertEqual(folded["files"], files)

    def test_baseline_is_not_mutated_by_fold(self):
        """fold must work on copies — re-folding yields the same result."""
        files = {"common/a.txt": {"audit_count": 1, "last_audited": "2026-06-04", "recent_findings": 0}}
        self._write_baseline("2026-06-05", files)
        self._write_run("2026-06-06", "2026-06-06",
                        [{"path": "common/a.txt", "line_range": None}], {"common/a.txt": 0})
        first = nas.fold_state()
        second = nas.fold_state()
        self.assertEqual(first["files"], second["files"])
        # baseline file on disk is unchanged
        on_disk = json.load(open(self.baseline))["files"]
        self.assertEqual(on_disk["common/a.txt"]["audit_count"], 1)

    # ----- delta application ------------------------------------------------

    def test_delta_bumps_count_and_stamps_date(self):
        self._write_baseline("2026-06-05", {})
        self._write_run("2026-06-06", "2026-06-06",
                        [{"path": "common/a.txt", "line_range": [1, 600]}], {"common/a.txt": 2})
        folded = nas.fold_state()["files"]["common/a.txt"]
        self.assertEqual(folded["audit_count"], 1)
        self.assertEqual(folded["last_audited"], "2026-06-06")
        self.assertEqual(folded["recent_findings"], 2)
        self.assertEqual(folded["partial_coverage"], [[1, 600]])

    def test_two_runs_same_file_accumulate(self):
        """A file audited by two post-baseline runs lands at the higher count —
        this is the case a line-based merge of the old aggregate got wrong."""
        self._write_baseline("2026-06-05", {"common/a.txt": {"audit_count": 8, "last_audited": "2026-06-05", "recent_findings": 0}})
        self._write_run("2026-06-06", "2026-06-06",
                        [{"path": "common/a.txt", "line_range": None}], {"common/a.txt": 0})
        self._write_run("2026-06-07", "2026-06-07",
                        [{"path": "common/a.txt", "line_range": None}], {"common/a.txt": 0})
        folded = nas.fold_state()["files"]["common/a.txt"]
        self.assertEqual(folded["audit_count"], 10)
        self.assertEqual(folded["last_audited"], "2026-06-07")

    # ----- double-count guards ---------------------------------------------

    def test_as_of_guard_skips_delta_at_or_before_baseline(self):
        """A findings.json dated on/before the baseline's as_of is already baked
        into the baseline — folding it again would double-count."""
        self._write_baseline("2026-06-05", {"common/a.txt": {"audit_count": 1, "last_audited": "2026-06-05", "recent_findings": 0}})
        # date == as_of -> skipped
        self._write_run("2026-06-05", "2026-06-05",
                        [{"path": "common/a.txt", "line_range": None}], {"common/a.txt": 0})
        folded = nas.fold_state()["files"]["common/a.txt"]
        self.assertEqual(folded["audit_count"], 1, "delta at as_of must not re-apply")

    def test_run_without_findings_json_is_skipped(self):
        """Historical runs (targets.json only, no findings.json) are already in
        the baseline and must not be folded."""
        self._write_baseline("2026-06-05", {})
        self._write_run("2026-06-06", "2026-06-06",
                        [{"path": "common/a.txt", "line_range": None}], {}, with_findings=False)
        self.assertEqual(nas.fold_state()["files"], {})

    # ----- ordering ---------------------------------------------------------

    def test_replay_is_date_ordered(self):
        """last_audited must reflect the latest date regardless of dir-iteration
        order on the filesystem."""
        self._write_baseline("2026-06-05", {})
        # Write the later date first to make sure sorting (not write order) wins.
        self._write_run("2026-06-09", "2026-06-09",
                        [{"path": "common/a.txt", "line_range": None}], {"common/a.txt": 1})
        self._write_run("2026-06-07", "2026-06-07",
                        [{"path": "common/a.txt", "line_range": None}], {"common/a.txt": 3})
        folded = nas.fold_state()["files"]["common/a.txt"]
        self.assertEqual(folded["audit_count"], 2)
        self.assertEqual(folded["last_audited"], "2026-06-09")
        self.assertEqual(folded["recent_findings"], 1)  # the 2026-06-09 run's value

    # ----- equivalence to direct update_state replay ------------------------

    def test_fold_equals_sequential_update_state(self):
        """The whole point: folding deltas == replaying update_state by hand, so
        the recency/decay scoring is identical to the old write-time path."""
        base_files = {"common/old.txt": {"audit_count": 1, "last_audited": "2026-01-01", "recent_findings": 2}}
        self._write_baseline("2026-06-05", base_files)
        runs = [
            ("2026-06-06", [{"path": "common/a.txt", "line_range": [1, 600]}], {"common/a.txt": 1}),
            ("2026-06-07", [{"path": "common/b.txt", "line_range": None}], {"common/b.txt": 0}),
        ]
        for date, targets, findings in runs:
            self._write_run(date, date, targets, findings)
        folded = nas.fold_state()["files"]

        # Independent manual replay.
        manual = {"common/old.txt": dict(base_files["common/old.txt"])}
        state = {"version": 1, "files": manual}
        for date, targets, findings in runs:
            nas.update_state(state, {"date": date, "targets": targets}, findings, Date.fromisoformat(date))
        self.assertEqual(folded, state["files"])

    # ----- helper main() integration ---------------------------------------

    def test_main_writes_findings_and_cache(self):
        self._write_baseline("2026-06-05", {})
        d = self.nightly / "2026-06-06"
        d.mkdir()
        targets = [{"path": "common/a.txt", "line_range": None, "lines": 100}]
        with open(d / "targets.json", "w") as f:
            json.dump({"date": "2026-06-06", "run_label": "2026-06-06", "targets": targets}, f)
        findings_in = d / "in.json"
        json.dump({"common/a.txt": 4}, open(findings_in, "w"))

        rc = nas.main([
            "--targets-json", str(d / "targets.json"),
            "--findings-json", str(findings_in),
            "--state-file", str(self.cache),  # default is import-time CACHE_FILE; redirect it
            "--date", "2026-06-06",
        ])
        self.assertEqual(rc, 0)
        # findings.json written next to targets.json
        written = json.load(open(d / "findings.json"))
        self.assertEqual(written, {"common/a.txt": 4})
        # cache refreshed and reflects the fold
        cache = json.load(open(self.cache))
        self.assertEqual(cache["files"]["common/a.txt"]["recent_findings"], 4)
        self.assertEqual(cache["files"]["common/a.txt"]["audit_count"], 1)


if __name__ == "__main__":
    unittest.main()
