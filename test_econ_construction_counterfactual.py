"""The construction-channel counterfactual (#1034, Task 8b): realised points and jobs
per interval between saves, the price ratio a curve shape gives, and the slack path it
implies. Synthetic series with injected cost and sector lookups (no ModState), plus one
CLI run on the committed dataset."""
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.analysis import econ_construction_counterfactual as CF
from scripts.analysis import econ_sim_data as D

REPO = Path(__file__).resolve().parent

# x_raw = (gdppc - 1) / (11 - 1) * 10 = gdppc - 1 on [1, 11], so gdppc 2.0 gives x_raw 1.0.
CURVE = D.CurveConstants(reference=1.0, floor_ratio=1.0, ceiling_ratio=11.0, max_mult=10.0)
MD = SimpleNamespace(numbers=SimpleNamespace(curve=CURVE))
COSTS = {"building_mill": 100.0, "building_hq": None, "building_shop": 400.0}
SECTORS = {"building_mill": "heavy", "building_hq": "other", "building_shop": "services"}
LOOKUPS = {"cost_of": COSTS.get, "sector_of": SECTORS.get}
WORLD = [{"date": "1900.1.1", "gdp": 1.0e9, "population": 1.0e8}]          # world gdppc 10


def _building(levels, staff_a_level=200.0, staffing=None):
    staffing = float(levels) if staffing is None else staffing
    return {"levels": levels, "staffing": staffing, "employees": staff_a_level * staffing,
            "goods_sales": 0.0, "goods_cost": 0.0, "pms": {}}


def _point(date, gdppc, buildings, prior=None, peasants=5000.0, unemployed=1000.0,
           workforce=10000.0, points_weekly=2.0):
    return {
        "date": date,
        "slice": {"population": 2 * workforce, "workforce": workforce, "peasants": peasants,
                  "unemployed": unemployed, "employed": workforce - peasants - unemployed,
                  "buildings_by_type": buildings},
        "owner": {"gdppc": gdppc, "points_weekly": {"government": points_weekly / 2, "private": points_weekly / 2},
                  "variables": {"prior_construction_scaling": prior}},
    }


def _one_interval(gdppc=2.0, prior=1.0, peasants=5000.0, unemployed=1000.0):
    """1000 points (10 mill levels at 100) and 2 jobs a point (200 staff a level)."""
    return {"points": [
        _point("1900.1.1", gdppc, {"building_mill": _building(0)}, prior=prior),
        _point("1910.1.1", gdppc, {"building_mill": _building(10)}, prior=prior,
               peasants=peasants, unemployed=unemployed),
    ]}


class TestCounterfactual(unittest.TestCase):
    def test_linear_reproduces_observed(self):
        series = {"points": [
            _point("1900.1.1", 1.5, {"building_mill": _building(0)}, prior=None),
            _point("1905.1.1", 3.0, {"building_mill": _building(20)}, prior=2.7),     # stale prior, others > 0
            _point("1912.6.1", 7.3, {"building_mill": _building(50)}, prior=4.1),     # others < 0
            _point("1920.1.1", 0.5, {"building_mill": _building(55)}, prior=0.0),     # under the floor
        ]}
        rows = CF.counterfactual(series, MD, "linear", WORLD, **LOOKUPS)
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row.cum_extra_jobs, 0.0)
            self.assertEqual(row.slack_cf_share, row.slack_obs_share)
            self.assertEqual(row.vacancies_cf_share, 0.0)

    def test_cheaper_curve_buys_more_points(self):
        series = _one_interval()
        (iv,) = CF.intervals(series, MD, **LOOKUPS)
        self.assertEqual(iv.points, 1000.0)
        self.assertEqual(iv.jobs_per_point, 2.0)
        self.assertEqual(iv.x_adj_start, 1.0)
        self.assertEqual(iv.others_start, 0.0)
        self.assertEqual(CF.shape_ratio("none", 2.0, 1.0, MD.numbers, None), 2.0)
        (row,) = CF.counterfactual(series, MD, "none", WORLD, **LOOKUPS)
        self.assertEqual(row.cum_extra_jobs, 2000.0)
        self.assertAlmostEqual(row.slack_obs_share, 6000.0 / 10000.0)
        self.assertAlmostEqual(row.slack_cf_share, (6000.0 - 2000.0) / 10000.0)
        self.assertEqual(row.vacancies_cf_share, 0.0)
        summary = CF.summarize("TOY", series, MD, "none", WORLD, **LOOKUPS)
        self.assertAlmostEqual(summary.extra_points_pct, 100.0)

    def test_others_carry_over(self):
        series = _one_interval(gdppc=2.0, prior=2.0)
        (iv,) = CF.intervals(series, MD, **LOOKUPS)
        self.assertAlmostEqual(iv.others_start, 0.5)
        self.assertAlmostEqual(iv.others_end, 0.5)
        self.assertAlmostEqual(CF.x_adj_under("none", 2.0, 2.0, MD.numbers, None), 0.5)
        self.assertAlmostEqual(CF.shape_ratio("none", 2.0, 2.0, MD.numbers, None), 3.0 / 1.5)

    def test_others_cancel_in_the_ratio(self):
        # (1 + x_adj) / (1 + x_adj') reduces to (1 + x_raw) / (1 + x_raw') for any prior.
        for prior in (0.0, 0.4, 1.0, 2.0, 7.5):
            self.assertAlmostEqual(CF.shape_ratio("capped:0.5", 3.0, prior, MD.numbers, None), 3.0 / 1.5)

    def test_slack_floors_and_vacancies_appear(self):
        series = _one_interval(peasants=300.0, unemployed=200.0)
        (row,) = CF.counterfactual(series, MD, "none", WORLD, **LOOKUPS)
        self.assertEqual(row.slack_cf_share, 0.0)
        self.assertAlmostEqual(row.vacancies_cf_share, (2000.0 - 500.0) / 10000.0)
        summary = CF.summarize("TOY", series, MD, "none", WORLD, **LOOKUPS)
        self.assertEqual(summary.first_vacancies, 1910)
        self.assertEqual(summary.first_below_5pct, 1910)

    def test_steeper_curve_cuts_points(self):
        series = _one_interval()
        ratio = CF.shape_ratio("slope:2", 2.0, 1.0, MD.numbers, None)
        self.assertAlmostEqual(ratio, 2.0 / 3.0)
        (row,) = CF.counterfactual(series, MD, "slope:2", WORLD, **LOOKUPS)
        self.assertLess(row.cum_extra_jobs, 0.0)
        self.assertAlmostEqual(row.cum_extra_jobs, 1000.0 * (2.0 / 3.0 - 1.0) * 2.0)
        self.assertGreater(row.slack_cf_share, row.slack_obs_share)

    def test_points_under_a_year_apart_merge(self):
        series = {"points": [
            _point("1900.1.1", 2.0, {"building_mill": _building(0)}, prior=1.0),
            _point("1900.6.1", 2.0, {"building_mill": _building(4)}, prior=1.0),
            _point("1901.6.1", 2.0, {"building_mill": _building(10)}, prior=1.0),
        ]}
        ivs = CF.intervals(series, MD, **LOOKUPS)
        self.assertEqual([(iv.start, iv.end) for iv in ivs], [("1900.1.1", "1901.6.1")])
        self.assertEqual(ivs[0].points, 1000.0)
        rows = CF.counterfactual(series, MD, "none", WORLD, **LOOKUPS)
        self.assertEqual([row.date for row in rows], ["1901.6.1"])

    def test_poor_country_untouched(self):
        for shape in (*CF.DEFAULT_SHAPES, "slope:2", "capped:0"):
            self.assertEqual(CF.shape_ratio(shape, 0.5, 0.0, MD.numbers, 10.0), 1.0, shape)
            self.assertEqual(CF.shape_ratio(shape, 0.5, None, MD.numbers, 10.0), 1.0, shape)
        series = _one_interval(gdppc=0.5, prior=None)
        (iv,) = CF.intervals(series, MD, **LOOKUPS)
        self.assertEqual((iv.others_start, iv.others_end), (0.0, 0.0))
        for shape in CF.DEFAULT_SHAPES:
            (row,) = CF.counterfactual(series, MD, shape, WORLD, **LOOKUPS)
            self.assertEqual(row.cum_extra_jobs, 0.0, shape)


class TestIntervalFigures(unittest.TestCase):
    def test_uncosted_and_demand_bound_types_buy_no_points_or_jobs(self):
        series = {"points": [
            _point("1900.1.1", 2.0, {"building_mill": _building(0), "building_hq": _building(0),
                                     "building_shop": _building(0)}, prior=1.0),
            _point("1910.1.1", 2.0, {"building_mill": _building(10), "building_hq": _building(30),
                                     "building_shop": _building(5)}, prior=1.0),
        ]}
        (iv,) = CF.intervals(series, MD, **LOOKUPS)
        self.assertEqual(iv.points, 1000.0)                 # the mill only; shops are services
        self.assertEqual(iv.gross_jobs, 2000.0)             # the HQ's levels weren't bought with points
        self.assertEqual(iv.uncosted_jobs, 6000.0)
        self.assertEqual(iv.net_jobs_change, 2000.0 + 6000.0)

    def test_staff_a_level_is_at_the_end_point_and_unstaffed_gives_none(self):
        series = {"points": [
            _point("1900.1.1", 2.0, {"building_mill": _building(10, staff_a_level=100.0)}, prior=1.0),
            _point("1910.1.1", 2.0, {"building_mill": _building(20, staff_a_level=300.0, staffing=10.0)},
                   prior=1.0),
        ]}
        (iv,) = CF.intervals(series, MD, **LOOKUPS)
        self.assertEqual(iv.gross_jobs, 10 * 300.0)
        self.assertEqual(iv.net_jobs_change, 3000.0 - 1000.0)
        series["points"][1]["slice"]["buildings_by_type"]["building_mill"] = _building(20, staffing=0.0)
        (iv,) = CF.intervals(series, MD, **LOOKUPS)
        self.assertEqual((iv.gross_jobs, iv.jobs_per_point), (0.0, 0.0))

    def test_points_observed_is_the_mean_rate_over_the_interval(self):
        series = _one_interval()
        series["points"][1]["owner"]["points_weekly"] = {"government": 3.0, "private": 3.0}
        (iv,) = CF.intervals(series, MD, **LOOKUPS)
        self.assertAlmostEqual(iv.points_observed, (2.0 + 6.0) / 2 * 52 * iv.years)

    def test_world_curve_reads_the_interpolated_world(self):
        world = [{"date": "1900.1.1", "gdp": 1.0e8, "population": 1.0e8},       # 1.0 a head
                 {"date": "1920.1.1", "gdp": 3.0e8, "population": 1.0e8}]       # 3.0 a head
        self.assertAlmostEqual(CF.world_gdppc_at(world, "1910.1.1"), 2.0, places=2)
        self.assertIsNone(CF.world_gdppc_at([], "1910.1.1"))
        # gdppc 3.0 against a world of 1.0: x = 3 / 1 on [1, 11] gives x_raw' 2.0.
        self.assertAlmostEqual(CF.shape_ratio("world", 3.0, None, MD.numbers, 1.0), 3.0 / 3.0)
        self.assertAlmostEqual(CF.shape_ratio("world", 3.0, None, MD.numbers, 3.0), 3.0 / 1.0)
        self.assertAlmostEqual(CF.shape_ratio("world", 3.0, None, MD.numbers, None), 3.0 / 1.0)

    def test_unknown_shapes_raise(self):
        for shape in ("cubic", "capped", "slope:x", "flat:2"):
            with self.assertRaises(ValueError, msg=shape):
                CF.shape_ratio(shape, 2.0, 1.0, MD.numbers, None)

    def test_summary_slack_needs_a_point_within_three_years(self):
        series = {"points": [
            _point("1900.1.1", 2.0, {"building_mill": _building(0)}, prior=1.0),
            _point("1916.1.1", 2.0, {"building_mill": _building(10)}, prior=1.0),
            _point("1960.1.1", 2.0, {"building_mill": _building(20)}, prior=1.0),
        ]}
        summary = CF.summarize("TOY", series, MD, "linear", WORLD, **LOOKUPS)
        self.assertAlmostEqual(summary.slack_1917, 0.6)
        self.assertIsNone(summary.slack_1954)
        self.assertIsNone(summary.slack_2045)
        self.assertEqual(summary.vacancies, (0.0, None, None, None, None, None))
        # 2000 extra jobs a 10-level interval under "none" leave 6000 - 4000 = 2000 slack by 1960.
        flooded = CF.summarize("TOY", series, MD, "none", WORLD, **LOOKUPS)
        self.assertAlmostEqual(flooded.slack_1917, 0.4)
        self.assertEqual(flooded.first_below_10pct, None)
        self.assertIsNone(summary.first_below_10pct)
        self.assertIsNone(summary.first_vacancies)


class TestCli(unittest.TestCase):
    def test_cli_runs_on_the_real_dataset(self):
        script = REPO / "scripts" / "analysis" / "econ_construction_counterfactual.py"
        out = subprocess.run([sys.executable, str(script), "--series", "FRA,union,GBR,CHI"],
                             cwd=REPO, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("| FRA | linear |", out.stdout)
        self.assertIn("| FRA | none |", out.stdout)
        self.assertIn("| CHI | none |", out.stdout)

    def test_cli_rejects_an_unknown_shape(self):
        self.assertEqual(CF.main(["--curves", "cubic"]), 2)


if __name__ == "__main__":
    unittest.main()
