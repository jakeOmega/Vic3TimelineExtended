"""Integration tests for the annotator registry endpoints.

Requires the mod state server running on http://127.0.0.1:8950. Tests
self-skip when it isn't up, mirroring the pattern in
`test_reload_post_load.py` / `test_engine_coverage_validator.py`.

Run:
    .venv/bin/python -m unittest test_annotator_endpoints -v
"""
from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.parse
import urllib.request


SERVER = "http://127.0.0.1:8950"


def _server_running() -> bool:
    try:
        with urllib.request.urlopen(f"{SERVER}/status", timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def _get(path: str) -> dict:
    url = f"{SERVER}{path}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


@unittest.skipUnless(_server_running(), f"server not running at {SERVER}")
class AnnotatorEndpointTests(unittest.TestCase):
    """Hits the live server. Each test is self-contained — no test-state leaks."""

    # ---- /annotators -----------------------------------------------------

    def test_annotators_lists_balance(self) -> None:
        data = _get("/annotators")
        self.assertIn("annotators", data)
        names = [(a["name"], a["entity_type"]) for a in data["annotators"]]
        self.assertIn(("balance", "PMs"), names)
        # Field set should be stable.
        balance = next(a for a in data["annotators"]
                       if a["name"] == "balance" and a["entity_type"] == "PMs")
        for f in ("flag", "margin_pct", "wage_be"):
            self.assertIn(f, balance["fields"])

    # ---- /tech-unlocks ---------------------------------------------------

    def test_tech_unlocks_summary_returns_dict(self) -> None:
        data = _get("/tech-unlocks?summary=true")
        self.assertIsInstance(data, dict)
        # At least one mod-side tech should be in the index — the tree has
        # several. Check the bombing_aircraft case from the design plan.
        self.assertIn("bombing_aircraft", data)
        rec = data["bombing_aircraft"]
        # `summary=true` means by_type lists are dropped.
        self.assertNotIn("by_type", rec)
        self.assertGreater(rec["n_total"], 0)

    def test_tech_unlocks_single_tech_full_shape(self) -> None:
        rec = _get("/tech-unlocks/modern_tools")
        self.assertGreater(rec["n_total"], 0)
        self.assertIn("PMs", rec["by_type"])
        # Every entry should carry type + id + file + source — the index
        # contract.
        for e in rec["by_type"]["PMs"]:
            self.assertEqual(e["type"], "PMs")
            self.assertIn("id", e)
            self.assertIn("file", e)
            self.assertIn("source", e)

    def test_tech_unlocks_with_balance_annotation(self) -> None:
        rec = _get("/tech-unlocks/modern_tools?annotate=balance")
        pm_entries = rec["by_type"].get("PMs", [])
        self.assertGreater(len(pm_entries), 0)
        # Each PM should have picked up the annotator fields.
        for e in pm_entries:
            self.assertIn("flag", e)
            # Flags belong to the documented set.
            self.assertIn(e["flag"], (
                "OK", "HIGH-PROFIT", "DEEP-LOSS", "HIGH-WAGE", "LOW-WAGE",
                "THROUGHPUT", "NO-COSTS",
            ))

    def test_tech_unlocks_unknown_annotator_silently_skips(self) -> None:
        rec = _get("/tech-unlocks/modern_tools?annotate=does-not-exist")
        # Shape unchanged; no annotator fields injected.
        for e in rec["by_type"].get("PMs", []):
            self.assertNotIn("flag", e)

    # ---- /unlocked-by/<tech> -------------------------------------------

    def test_unlocked_by_includes_type_field_by_default(self) -> None:
        # Backward compat sanity: every entry should now carry `type`,
        # which is the universal contract addition.
        rec = _get("/unlocked-by/modern_tools")
        for etype, entries in rec.items():
            for e in entries:
                self.assertEqual(e["type"], etype)

    def test_unlocked_by_with_annotate_balance(self) -> None:
        rec = _get("/unlocked-by/modern_tools?annotate=balance")
        pm_entries = rec.get("PMs", [])
        self.assertGreater(len(pm_entries), 0)
        for e in pm_entries:
            self.assertIn("flag", e)

    # ---- universal wire-up -----------------------------------------------

    def test_universal_wireup_production_methods(self) -> None:
        # Validates §4 of the design — annotation is wired into every
        # entity-list endpoint, not just /tech-unlocks.
        data = _get("/production-methods?annotate=balance")
        # Entries are a list at the top level for /production-methods.
        self.assertIsInstance(data, list)
        # Find a PM that has cost comments — pm_dragline_excavators_coal_mine
        # should have a flag. Sample the first 50 to keep the test cheap.
        sampled = [e for e in data[:50] if e.get("type") == "PMs"]
        self.assertGreater(len(sampled), 0)
        annotated = [e for e in sampled if "flag" in e]
        # At least *some* of the first 50 PMs should be annotated. Allowing
        # for NO-COSTS PMs which still get a `flag` field.
        self.assertGreater(len(annotated), 0)

    def test_universal_wireup_no_op_on_unrelated_endpoint(self) -> None:
        # /laws has no `balance` annotator registered for the Laws type, so
        # ?annotate=balance is a no-op. Response shape stays normal.
        data = _get("/laws?annotate=balance")
        # /laws returns a dict-of-groups shape; just sanity-check it's there
        # and no flag field leaked into law entries.
        self.assertIsInstance(data, dict)
        for group in data.values():
            for law in group.get("laws", []):
                self.assertNotIn("flag", law)
                # And every law entry now carries `type=Laws`.
                self.assertEqual(law.get("type"), "Laws")

    # ---- backward-compat sanity -----------------------------------------

    def test_no_annotate_param_response_minus_type_unchanged(self) -> None:
        # Response shape without ?annotate= is unchanged except for the
        # additive `type` field on entity entries (the only schema addition
        # in this PR's non-annotated path).
        data = _get("/laws")
        self.assertIsInstance(data, dict)
        # Each law entry should carry the new `type` field but no annotator
        # fields.
        sampled = []
        for group in data.values():
            sampled.extend(group.get("laws", [])[:2])
            if len(sampled) >= 4:
                break
        self.assertGreater(len(sampled), 0)
        for law in sampled:
            self.assertEqual(law.get("type"), "Laws")
            self.assertIn("id", law)
            self.assertNotIn("flag", law)


if __name__ == "__main__":
    unittest.main()
