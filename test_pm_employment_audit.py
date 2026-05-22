"""Unit tests for pm_employment_audit.

Run: python3 test_pm_employment_audit.py
"""
import os
import tempfile
import unittest

from pm_employment_audit import (
    audit,
    render_report,
    _parse_reviewed,
    _pm_employment,
    AuditResult,
)


class FakeMS:
    """Minimal stand-in for ModState. The audit only calls `get_data`."""

    def __init__(self, buildings: dict, pm_groups: dict, pms: dict):
        self._data = {"Buildings": buildings, "PM Groups": pm_groups, "PMs": pms}

    def get_data(self, entity_type):
        return self._data.get(entity_type)


def _emp(scaling: str, **profs) -> dict:
    """Build a PM body with employment adds in one scaling block."""
    return {"building_modifiers": {scaling: {f"building_employment_{p}_add": str(v)
                                             for p, v in profs.items()}}}


def _write(tmp: str, rel: str, content: str):
    path = os.path.join(tmp, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _scaffold(tmp: str, mod_buildings: dict | None = None, mod_pms: dict | None = None):
    """Write opening-line stubs so the named entities count as mod-defined.
    Values are an optional trailing comment (e.g. '# REVIEWED ...')."""
    def block(entries: dict) -> str:
        out = []
        for name, comment in entries.items():
            c = f" {comment}" if comment else ""
            out.append(f"{name} = {{{c}\n}}\n")
        return "".join(out)
    if mod_buildings:
        _write(tmp, "common/buildings/test.txt", block(mod_buildings))
    if mod_pms:
        _write(tmp, "common/production_methods/test.txt", block(mod_pms))


# ---------------------------------------------------------------------------
class ParseReviewedTests(unittest.TestCase):
    def test_match(self):
        self.assertEqual(
            _parse_reviewed("# REVIEWED 2026-05-22: intentional, base >= 4000"),
            {"date": "2026-05-22", "rationale": "intentional, base >= 4000"},
        )

    def test_no_match(self):
        self.assertIsNone(_parse_reviewed("# just a comment"))
        self.assertIsNone(_parse_reviewed(None))


class EmploymentExtractTests(unittest.TestCase):
    def test_buckets_and_professions(self):
        body = {"building_modifiers": {
            "level_scaled": {"building_employment_laborers_add": "-3500",
                             "building_employment_machinists_add": "1000"},
            "workforce_scaled": {"building_employment_farmers_add": "500",
                                 "goods_output_sugar_add": "30"},
        }}
        emp = _pm_employment(body)
        self.assertEqual(emp["level_scaled"]["laborers"], -3500.0)
        self.assertEqual(emp["level_scaled"]["machinists"], 1000.0)
        self.assertEqual(emp["workforce_scaled"]["farmers"], 500.0)
        self.assertNotIn("goods_output_sugar", emp["workforce_scaled"])

    def test_empty_for_no_building_modifiers(self):
        self.assertEqual(_pm_employment({"state_modifiers": {}}), {})


# ---------------------------------------------------------------------------
class AuditTests(unittest.TestCase):
    def _run(self, buildings, pmgs, pms, tmp):
        ms = FakeMS(buildings, pmgs, pms)
        return audit(ms, mod_path=tmp)

    def test_basic_negative_flagged(self):
        buildings = {"B": {"production_method_groups": ["g_base", "g_auto"]}}
        pmgs = {"g_base": {"production_methods": ["pm_base"]},
                "g_auto": {"production_methods": ["pm_auto"]}}
        pms = {"pm_base": _emp("level_scaled", laborers=1000),
               "pm_auto": _emp("level_scaled", laborers=-3500)}
        with tempfile.TemporaryDirectory() as tmp:
            _scaffold(tmp, mod_pms={"pm_auto": None})
            res = self._run(buildings, pmgs, pms, tmp)
        self.assertEqual(len(res.flags), 1)
        f = res.flags[0]
        self.assertEqual(f.profession, "laborers")
        self.assertEqual(f.scaling, "level_scaled")
        self.assertEqual(f.total, -2500.0)
        self.assertTrue(f.mod_relevant)
        self.assertIsNone(f.exemption)

    def test_offset_not_flagged(self):
        buildings = {"B": {"production_method_groups": ["g_base", "g_auto"]}}
        pmgs = {"g_base": {"production_methods": ["pm_base"]},
                "g_auto": {"production_methods": ["pm_auto"]}}
        pms = {"pm_base": _emp("level_scaled", laborers=4000),
               "pm_auto": _emp("level_scaled", laborers=-3500)}
        with tempfile.TemporaryDirectory() as tmp:
            _scaffold(tmp, mod_pms={"pm_auto": None})
            res = self._run(buildings, pmgs, pms, tmp)
        self.assertEqual(res.flags, [])

    def test_dead_pm_gating_excluded(self):
        # pm_trans_dead's -3500 is unreachable in this building (its unlock
        # references a PM that isn't here), so no combo can select it.
        buildings = {"B": {"production_method_groups": ["g_base", "g_trans"]}}
        pmgs = {"g_base": {"production_methods": ["pm_base"]},
                "g_trans": {"production_methods": ["pm_trans_dead", "pm_trans_ok"]}}
        pms = {
            "pm_base": _emp("level_scaled", laborers=1000),
            "pm_trans_dead": {**_emp("level_scaled", laborers=-3500),
                              "unlocking_production_methods": ["pm_some_mine"]},
            "pm_trans_ok": _emp("level_scaled", laborers=0),
        }
        with tempfile.TemporaryDirectory() as tmp:
            _scaffold(tmp, mod_pms={"pm_trans_dead": None})
            res = self._run(buildings, pmgs, pms, tmp)
        self.assertEqual(res.flags, [])

    def test_cross_group_dependency_excludes_low_base_combo(self):
        # pm_auto only unlocks alongside pm_high, so the (pm_low, pm_auto)
        # combo that would go negative is invalid.
        buildings = {"B": {"production_method_groups": ["g_base", "g_auto"]}}
        pmgs = {"g_base": {"production_methods": ["pm_low", "pm_high"]},
                "g_auto": {"production_methods": ["pm_auto"]}}
        pms = {
            "pm_low": _emp("level_scaled", laborers=1000),
            "pm_high": _emp("level_scaled", laborers=5000),
            "pm_auto": {**_emp("level_scaled", laborers=-3500),
                        "unlocking_production_methods": ["pm_high"]},
        }
        with tempfile.TemporaryDirectory() as tmp:
            _scaffold(tmp, mod_pms={"pm_auto": None})
            res = self._run(buildings, pmgs, pms, tmp)
        self.assertEqual(res.flags, [])

    def test_reviewed_suppression(self):
        buildings = {"B": {"production_method_groups": ["g_base", "g_auto"]}}
        pmgs = {"g_base": {"production_methods": ["pm_base"]},
                "g_auto": {"production_methods": ["pm_auto"]}}
        pms = {"pm_base": _emp("level_scaled", laborers=1000),
               "pm_auto": _emp("level_scaled", laborers=-3500)}
        with tempfile.TemporaryDirectory() as tmp:
            _scaffold(tmp, mod_pms={"pm_auto": "# REVIEWED 2026-05-22: deliberate"})
            res = self._run(buildings, pmgs, pms, tmp)
        self.assertEqual(len(res.flags), 1)
        self.assertEqual(res.flags[0].exemption,
                         {"date": "2026-05-22", "rationale": "deliberate"})

    def test_vanilla_only_not_mod_relevant(self):
        buildings = {"B": {"production_method_groups": ["g_base", "g_auto"]}}
        pmgs = {"g_base": {"production_methods": ["pm_base"]},
                "g_auto": {"production_methods": ["pm_auto"]}}
        pms = {"pm_base": _emp("level_scaled", laborers=1000),
               "pm_auto": _emp("level_scaled", laborers=-3500)}
        with tempfile.TemporaryDirectory() as tmp:
            # nothing scaffolded → all participants vanilla
            res = self._run(buildings, pmgs, pms, tmp)
        self.assertEqual(len(res.flags), 1)
        self.assertFalse(res.flags[0].mod_relevant)

    def test_buckets_dont_cross_offset(self):
        # workforce +5000 must NOT cancel a level_scaled -3500.
        buildings = {"B": {"production_method_groups": ["g_base", "g_auto"]}}
        pmgs = {"g_base": {"production_methods": ["pm_base"]},
                "g_auto": {"production_methods": ["pm_auto"]}}
        pms = {"pm_base": _emp("workforce_scaled", laborers=5000),
               "pm_auto": _emp("level_scaled", laborers=-3500)}
        with tempfile.TemporaryDirectory() as tmp:
            _scaffold(tmp, mod_pms={"pm_auto": None})
            res = self._run(buildings, pmgs, pms, tmp)
        self.assertEqual(len(res.flags), 1)
        self.assertEqual(res.flags[0].scaling, "level_scaled")
        self.assertEqual(res.flags[0].total, -3500.0)


# ---------------------------------------------------------------------------
class RenderTests(unittest.TestCase):
    def test_empty(self):
        out = render_report(AuditResult(flags=[], coverage={}))
        self.assertIn("## Unreviewed Flags", out)
        self.assertIn("_None._", out)

    def test_populated(self):
        buildings = {"B": {"production_method_groups": ["g_base", "g_auto"]}}
        pmgs = {"g_base": {"production_methods": ["pm_base"]},
                "g_auto": {"production_methods": ["pm_auto"]}}
        pms = {"pm_base": _emp("level_scaled", laborers=1000),
               "pm_auto": _emp("level_scaled", laborers=-3500)}
        with tempfile.TemporaryDirectory() as tmp:
            _scaffold(tmp, mod_pms={"pm_auto": None})
            res = audit(FakeMS(buildings, pmgs, pms), mod_path=tmp)
        out = render_report(res)
        self.assertIn("`B`", out)
        self.assertIn("laborers", out)
        self.assertIn("-2500", out)


if __name__ == "__main__":
    unittest.main()
