"""scripts/analysis/demographics_ontop.py and the widened gate: calibration step 3's harness
(docs/superpowers/archive/specs/2026-10-12-demographics-calibration-step3-design.md §3; owner calls 1-3, 2026-10-12)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_ontop as O  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_practices as DP  # noqa: E402
import demographics_regions as R  # noqa: E402


def _fit(sid, tag, deaths, base=6.0, people=1e7):
    return DP.FitState(sid, "", tag, people, True, base, 0.4, 30.0, deaths, 0.0, 0.0, None)


class TestProjection(unittest.TestCase):
    # step year, group, peace, reasons, births, deaths, people, migration, tag, state id
    ROWS = [
        [1840, "India", True, [], 42.0, 30.0, 1000.0, 0.0, "BIC", "1"],
        [1840, "Africa", True, [], 45.0, 36.0, 1000.0, 0.0, "ASH", "2"],
        [1840, "W/N/C/S Europe", True, [], 38.0, 26.0, 1000.0, 0.0, "GBR", "3"],
        [1840, "Africa", False, ["war"], 45.0, 90.0, 1000.0, 0.0, "ASH", "2"],   # not peacetime
    ]
    # the 1841 save closes the 1840 step: India's own lines -25% of its window deaths (the trait), Britain's +5%
    # (working conditions), with 2% severe starvation; Africa holds no split (Display only)
    SPLITS = {1841: {"1": {"te_dg_ed": 100.0, "te_dg_ed_state": 125.0, "te_dg_ed_sev": 0.0},
                     "3": {"te_dg_ed": 100.0, "te_dg_ed_state": 93.0, "te_dg_ed_sev": 2.0}}}
    PRACTICE = (1.0, 0.0, 0.0, 0.0, 0.0)

    def states(self, africa_deaths=300.0):
        return {1837: [_fit("1", "BIC", 300.0), _fit("2", "ASH", africa_deaths), _fit("3", "GBR", 300.0)]}

    def test_before_is_the_measured_rate(self):
        today = self.states()
        proj = O.project(self.ROWS, self.SPLITS, today, today, *self.PRACTICE, absorb=False)
        for label, want in (("India", 12.0), ("Africa", 9.0), ("W/N/C/S Europe", 12.0)):
            self.assertAlmostEqual(proj["groups"][label][1], want, places=9, msg=label)
            self.assertAlmostEqual(proj["groups"][label][0], want, places=9, msg=label)

    def test_call_1_absorbs_only_the_net_negative_own_lines(self):
        """India's -25% leaves its deaths (30 / 0.75 = the deaths without the trait's 7.5); Britain's +5% stays on top,
        unchanged; a state-year with no split is unchanged."""
        today = self.states()
        proj = O.project(self.ROWS, self.SPLITS, today, today, *self.PRACTICE)
        self.assertAlmostEqual(proj["groups"]["India"][1], 42.0 - 30.0 * 1.25, places=9)
        self.assertAlmostEqual(proj["groups"]["W/N/C/S Europe"][1], 12.0, places=9)
        self.assertAlmostEqual(proj["groups"]["Africa"][1], 9.0, places=9)
        self.assertAlmostEqual(proj["parts"]["India"]["own_neg"], -7.5, places=9)
        self.assertAlmostEqual(proj["parts"]["W/N/C/S Europe"]["own_pos"], 1.3, places=9)

    def test_the_malaria_factor_scales_the_census_rate_not_the_own_lines(self):
        today, point = self.states(), self.states(africa_deaths=330.0)
        proj = O.project(self.ROWS, self.SPLITS, today, point, *self.PRACTICE)
        self.assertAlmostEqual(proj["groups"]["Africa"][1], 45.0 - 36.0 * 1.1, places=9)
        # Britain's census part (26 less its 1.3 own and 0.52 severe) would scale; its ratio is 1 here
        self.assertAlmostEqual(proj["groups"]["W/N/C/S Europe"][1], 12.0, places=9)
        self.assertAlmostEqual(proj["world"][0], (12.0 + 9.0 + 12.0) / 3, places=9)

    def test_fit_g_takes_the_smallest_g_inside_the_band(self):
        today = self.states()
        by_g = {0.0: today, 0.05: self.states(africa_deaths=315.0), 0.1: self.states(africa_deaths=330.0)}
        # Africa +9.0, then 45 - 36 x 1.05 = +7.2: inside +3 to +8 at 0.05
        self.assertEqual(O.fit_g(self.ROWS, self.SPLITS, today, by_g, self.PRACTICE), 0.05)
        self.assertIsNone(O.fit_g(self.ROWS, self.SPLITS, today, by_g, self.PRACTICE, top=3.0))

    def test_the_severe_excess_follows_the_ratio(self):
        self.assertEqual(O.malaria_infection(0.08), {1: 0.08, 2: round(0.08 * P.MALARIA_SEVERE_RATIO, 2)})

    def test_splits_from_extract_alls_json(self):
        with tempfile.TemporaryDirectory() as d:
            for date in ("1841.1.1", "1841.6.1"):
                (Path(d) / f"{date}.json").write_text(json.dumps(
                    {"date": date, "states": {"1": {"vars": {"te_dg_ed": 100.0, "te_dg_ed_state": 125.0}}}}),
                    encoding="utf-8")
            got = O.read_splits(sorted(Path(d).glob("*.json")))
        self.assertEqual(set(got), {1841}, "1 January saves only")
        self.assertEqual(O.split_of(got, 1840, "1"), (-0.25, 0.0))
        self.assertEqual(O.split_of(got, 1840, "2"), (0.0, 0.0))


class TestWidenedGate(unittest.TestCase):
    def test_half_the_spread_at_least_half_a_point(self):
        w = R.widening({"China": 1.14, "W/N/C/S Europe": 0.08})
        self.assertAlmostEqual(w["China"], 0.57)
        self.assertEqual(w["W/N/C/S Europe"], 0.5)
        self.assertEqual(set(R.widening()), set(R.TWO_RUN_SPREAD))

    def test_the_spread_is_measured_from_two_runs(self):
        a = [[1840, "China", True, [], 40.0, 34.0, 1000.0, 0.0, "CHI", "1"]]
        b = [[1840, "China", True, [], 40.0, 35.5, 1000.0, 0.0, "CHI", "1"]]
        self.assertAlmostEqual(O.two_run_spread(a, b)["China"], 1.5)

    def test_the_gate_judges_the_widened_band(self):
        proj = {"groups": {"W/N/C/S Europe": (11.07, 7.6)}, "world": (8.75, 7.5), "tags": {}}
        self.assertEqual(DP.region_gate(proj, widen=R.widening()), [])
        fails = DP.region_gate(dict(proj, groups={"W/N/C/S Europe": (11.07, 7.4)}), widen=R.widening())
        self.assertEqual(fails, ["W/N/C/S Europe: +7.40 per 1,000 (history +8 to +10, widened +7.50 to +10.50)"])
        self.assertEqual(len(DP.region_gate(proj)), 1, "history's bands without widen")


if __name__ == "__main__":
    unittest.main()
