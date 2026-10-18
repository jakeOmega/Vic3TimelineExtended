"""The construction-channel counterfactual (#1034, Task 8b): realised points and jobs
per interval between saves, the price ratio a curve shape gives, and the slack path it
implies. Synthetic series with injected cost and sector lookups (no ModState), plus one
CLI run on the committed dataset."""
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts.analysis import econ_construction_counterfactual as CF
from scripts.analysis import econ_sim_data as D

REPO = Path(__file__).resolve().parent

# A toy historical curve (the one the observed history was priced under): x_raw =
# (gdppc - 1) / (11 - 1) * 10 = gdppc - 1 on [1, 11], so gdppc 2.0 gives x_raw 1.0. The module
# reads D.HISTORICAL_CURVE when it computes, so setUpModule swaps it for this one.
CURVE = D.CurveConstants(reference=1.0, floor_ratio=1.0, ceiling_ratio=11.0, max_mult=10.0)
# A toy stand-in for the mod's curve with no slack band (#1034's +100% cap): +10 points per 1x
# of reference, capped at +100% from 11x. Slack-band shapes are tested with `slack:`.
CURRENT = D.CurveConstants(reference=1.0, floor_ratio=1.0, ceiling_ratio=11.0, max_mult=1.0)
MD = SimpleNamespace(numbers=SimpleNamespace(curve=CURRENT))
COSTS = {"building_mill": 100.0, "building_hq": None, "building_shop": 400.0}
SECTORS = {"building_mill": "heavy", "building_hq": "other", "building_shop": "services"}
LOOKUPS = {"cost_of": COSTS.get, "sector_of": SECTORS.get}
WORLD = [{"date": "1900.1.1", "gdp": 1.0e9, "population": 1.0e8}]          # world gdppc 10
_HISTORICAL = mock.patch.object(D, "HISTORICAL_CURVE", CURVE)


def setUpModule():
    _HISTORICAL.start()


def tearDownModule():
    _HISTORICAL.stop()


def _building(levels, staff_a_level=200.0, staffing=None):
    staffing = float(levels) if staffing is None else staffing
    return {"levels": levels, "staffing": staffing, "employees": staff_a_level * staffing,
            "goods_sales": 0.0, "goods_cost": 0.0, "pms": {}}


def _point(date, gdppc, buildings, prior=None, peasants=5000.0, unemployed=1000.0,
           workforce=10000.0, points_weekly=2.0, per_state=None):
    point = {
        "date": date,
        "slice": {"population": 2 * workforce, "workforce": workforce, "peasants": peasants,
                  "unemployed": unemployed, "employed": workforce - peasants - unemployed,
                  "buildings_by_type": buildings},
        "owner": {"gdppc": gdppc, "points_weekly": {"government": points_weekly / 2, "private": points_weekly / 2},
                  "variables": {"prior_construction_scaling": prior}},
    }
    if per_state is not None:
        point["per_state"] = per_state
    return point


def _one_interval(gdppc=2.0, prior=1.0, peasants=5000.0, unemployed=1000.0):
    """1000 points (10 mill levels at 100) and 2 jobs a point (200 staff a level)."""
    return {"points": [
        _point("1900.1.1", gdppc, {"building_mill": _building(0)}, prior=prior),
        _point("1910.1.1", gdppc, {"building_mill": _building(10)}, prior=prior,
               peasants=peasants, unemployed=unemployed),
    ]}


def _zero_slack_interval():
    """_one_interval with no peasants or unemployed at either end: 1000 points, 2 jobs a point,
    x_raw 1.0 (gdppc 2.0), others 0 (prior = x_raw)."""
    return {"points": [
        _point("1900.1.1", 2.0, {"building_mill": _building(0)}, prior=1.0, peasants=0.0, unemployed=0.0),
        _point("1910.1.1", 2.0, {"building_mill": _building(10)}, prior=1.0, peasants=0.0, unemployed=0.0),
    ]}


class TestSlackBand(unittest.TestCase):
    def test_slack_shape_is_the_historical_line_with_a_band(self):
        _p, c = CF._shape("slack:0.03:0.15:0.5", CURRENT)
        self.assertEqual(c, D.CurveConstants(1.0, 1.0, 11.0, 10.0, 0.03, 0.15, 0.5))
        _p, c = CF._shape("slack:0.03:0.15", CURRENT)
        self.assertIsNone(c.slack_ease)
        for bad in ("slack:0.15:0.03", "slack:a:b", "slack:0.03", "slack:0.03:0.15:0", "slack:0.03:0.15:0.5:1"):
            with self.assertRaises(ValueError, msg=bad):
                CF._shape(bad, CURRENT)

    def test_a_band_has_a_path_not_a_ratio(self):
        self.assertTrue(CF.has_slack_band("slack:0.03:0.15", CURRENT))
        self.assertFalse(CF.has_slack_band("current", CURRENT))
        with self.assertRaises(ValueError):
            CF.shape_ratio("slack:0.03:0.15", 2.0, None, MD.numbers, None)

    def test_all_slack_applies_none_of_the_line(self):
        # 60% slack throughout, still 40% after the extra jobs: the share stays 0, as `none`.
        series = _one_interval()
        (band,) = CF.counterfactual(series, MD, "slack:0.03:0.15", WORLD, **LOOKUPS)
        (none,) = CF.counterfactual(series, MD, "none", WORLD, **LOOKUPS)
        self.assertAlmostEqual(band.cum_extra_jobs, none.cum_extra_jobs)
        self.assertAlmostEqual(band.cum_extra_jobs, 2000.0)

    def test_no_slack_applies_the_whole_line(self):
        # With no slack and no easing the share is 1 from the first year: the historical curve.
        (row,) = CF.counterfactual(_zero_slack_interval(), MD, "slack:0.03:0.15", WORLD, **LOOKUPS)
        self.assertAlmostEqual(row.cum_extra_jobs, 0.0)

    def test_the_share_eases_up_from_zero(self):
        # Ten yearly steps of 100 points: the share is 1 - 0.5^k in step k, so the step's ratio
        # is (1 + 1) / (1 + 1.0 x share), and each extra point makes 2 jobs.
        (row,) = CF.counterfactual(_zero_slack_interval(), MD, "slack:0.03:0.15:0.5", WORLD, **LOOKUPS)
        expected = sum(100.0 * (2.0 / (2.0 - 0.5 ** k) - 1.0) * 2.0 for k in range(1, 11))
        self.assertAlmostEqual(row.cum_extra_jobs, expected)
        self.assertAlmostEqual(row.vacancies_cf_share, expected / 10000.0)

    def test_share_from_another_series(self):
        # The core has no slack of its own, but the owner country's 60% keeps the share at 0: the core builds
        # as under `none` (the script reads the owner's slack). Priced at its own share it gets the whole line.
        core, owner = _zero_slack_interval(), _one_interval()
        (borrowed,) = CF.counterfactual(core, MD, "slack:0.03:0.15", WORLD, **LOOKUPS, share_from=owner)
        (none,) = CF.counterfactual(core, MD, "none", WORLD, **LOOKUPS)
        (own,) = CF.counterfactual(core, MD, "slack:0.03:0.15", WORLD, **LOOKUPS)
        self.assertAlmostEqual(borrowed.cum_extra_jobs, none.cum_extra_jobs)
        self.assertAlmostEqual(own.cum_extra_jobs, 0.0)
        # a shape with no band ignores it
        (hist,) = CF.counterfactual(core, MD, "historical", WORLD, **LOOKUPS, share_from=owner)
        self.assertEqual(hist.cum_extra_jobs, 0.0)

    def test_share_from_needs_the_same_dates(self):
        other = {"points": [
            _point("1900.1.1", 2.0, {"building_mill": _building(0)}, prior=1.0),
            _point("1911.1.1", 2.0, {"building_mill": _building(10)}, prior=1.0),
        ]}
        with self.assertRaises(ValueError):
            CF.counterfactual(_one_interval(), MD, "slack:0.03:0.15", WORLD, **LOOKUPS, share_from=other)

    def test_others_scale(self):
        # others 1.0 at both ends (prior 2.0 on x_raw 1.0); at half the size the same money
        # buys (1 + 1) / (1 + 0.5) times the points, under the historical curve too.
        series = _one_interval(prior=2.0)
        (row,) = CF.counterfactual(series, MD, "historical", WORLD, **LOOKUPS, others_scale=0.5)
        self.assertAlmostEqual(row.cum_extra_jobs, 1000.0 * (2.0 / 1.5 - 1.0) * 2.0)
        (band,) = CF.counterfactual(series, MD, "slack:0.03:0.15", WORLD, **LOOKUPS, others_scale=0.5)
        self.assertAlmostEqual(band.cum_extra_jobs, 1000.0 * (2.0 * 2.0 / 1.5 - 1.0) * 2.0)
        (same,) = CF.counterfactual(series, MD, "historical", WORLD, **LOOKUPS, others_scale=1.0)
        self.assertEqual(same.cum_extra_jobs, 0.0)


class TestCounterfactual(unittest.TestCase):
    def test_historical_reproduces_observed(self):
        series = {"points": [
            _point("1900.1.1", 1.5, {"building_mill": _building(0)}, prior=None),
            _point("1905.1.1", 3.0, {"building_mill": _building(20)}, prior=2.7),     # stale prior, others > 0
            _point("1912.6.1", 7.3, {"building_mill": _building(50)}, prior=4.1),     # others < 0
            _point("1920.1.1", 0.5, {"building_mill": _building(55)}, prior=0.0),     # under the floor
        ]}
        rows = CF.counterfactual(series, MD, "historical", WORLD, **LOOKUPS)
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row.cum_extra_jobs, 0.0)
            self.assertEqual(row.slack_cf_share, row.slack_obs_share)
            self.assertEqual(row.vacancies_cf_share, 0.0)
        # The mod's curve now is not the one the history ran under: it prices the same
        # money below the historical curve, so it buys more points.
        current = CF.summarize("TOY", series, MD, "current", WORLD, **LOOKUPS)
        self.assertGreater(current.extra_points_pct, 0.0)
        self.assertEqual(CF.summarize("TOY", series, MD, "historical", WORLD, **LOOKUPS).extra_points_pct, 0.0)

    def test_current_is_the_mods_curve(self):
        # Under the +100% cap: 0 at 1, +10 points a 1x of reference, 1.0 from 11 on.
        for shape in ("current", "linear"):
            self.assertEqual(CF.x_under(shape, 25.0, MD.numbers.curve, None), 1.0, shape)
            self.assertAlmostEqual(CF.x_under(shape, 6.0, MD.numbers.curve, None), 0.5, msg=shape)
            self.assertEqual(CF.x_under(shape, 0.5, MD.numbers.curve, None), 0.0, shape)
        # ... priced against the historical baseline, here the toy curve (10.0 at its ceiling).
        self.assertEqual(CF.x_raw_of(25.0), 10.0)
        self.assertAlmostEqual(CF.shape_ratio("current", 25.0, None, MD.numbers, None), 11.0 / 2.0)
        self.assertEqual(CF.shape_ratio("linear", 25.0, None, MD.numbers, None),
                         CF.shape_ratio("current", 25.0, None, MD.numbers, None))
        self.assertEqual(CF.shape_ratio("historical", 25.0, None, MD.numbers, None), 1.0)

    def test_other_shapes_are_built_on_the_historical_constants(self):
        # A capped:2 on the current constants would stay at 1.0, as that line stops there already.
        self.assertEqual(CF.x_under("capped:2", 25.0, MD.numbers.curve, None), 2.0)
        self.assertAlmostEqual(CF.x_under("slope:0.5", 6.0, MD.numbers.curve, None), 2.5)
        self.assertEqual(CF.x_under("none", 25.0, MD.numbers.curve, None), 0.0)

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
        # The script sets prior = x_raw x (1 + others): x_raw 1.0 and prior 2.0 give others 1.0.
        series = _one_interval(gdppc=2.0, prior=2.0)
        (iv,) = CF.intervals(series, MD, **LOOKUPS)
        self.assertAlmostEqual(iv.others_start, 1.0)
        self.assertAlmostEqual(iv.others_end, 1.0)
        # Under the shape the script would set x_raw' x (1 + others): 0 with no curve, 1.0 at half the X.
        self.assertAlmostEqual(CF.x_adj_under("none", 2.0, 2.0, MD.numbers, None), 0.0)
        self.assertAlmostEqual(CF.x_adj_under("capped:0.5", 2.0, 2.0, MD.numbers, None), 0.5 * 2.0)
        # The whole multiplier, (1 + x_raw)(1 + others) = 4 now and 2 with no curve, halves.
        self.assertAlmostEqual(CF.shape_ratio("none", 2.0, 2.0, MD.numbers, None), 2.0)

    def test_others_cancel_in_the_ratio(self):
        # (1 + x_adj + others) / (1 + x_adj' + others) reduces to (1 + x_raw) / (1 + x_raw') for any prior.
        for prior in (0.0, 0.4, 1.0, 2.0, 7.5):
            self.assertAlmostEqual(CF.shape_ratio("capped:0.5", 3.0, prior, MD.numbers, None), 3.0 / 1.5)
            if prior == 0.0:
                continue                # others -1: no cost at all, and the long form divides by 0
            others = CF.others_of(2.0, prior)
            x_adj_new = CF.x_adj_under("capped:0.5", 3.0, prior, MD.numbers, None)
            self.assertAlmostEqual((1.0 + prior + others) / (1.0 + x_adj_new + others), 3.0 / 1.5)

    def test_a_stale_prior_under_the_floor_costs_nothing(self):
        # x_raw 0: the script sets no scaling, so a prior left from an earlier pulse is stale and others is 0.
        self.assertEqual(CF.others_of(0.0, 2.0), 0.0)
        self.assertEqual(CF.x_adj_under("none", 0.5, 2.0, MD.numbers, None), 0.0)
        # The world curve charges a country far above a poor world: the ratio is 1 / (1 + x_raw'), not
        # (1 + the stale prior) / (1 + x_raw').
        x_new = CF.x_under("world", 0.5, MD.numbers.curve, 0.1)
        self.assertGreater(x_new, 0.0)
        self.assertAlmostEqual(CF.shape_ratio("world", 0.5, 2.0, MD.numbers, 0.1), 1.0 / (1.0 + x_new))
        self.assertEqual(CF.shape_ratio("world", 0.5, 2.0, MD.numbers, 0.1),
                         CF.shape_ratio("world", 0.5, None, MD.numbers, 0.1))

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
            if CF.has_slack_band(shape, MD.numbers.curve):
                continue                                    # a path, not a ratio: the loop below covers it
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

    def test_annexed_levels_are_not_counted_as_bought(self):
        # A union series: state 2 is new at the end, with 8 levels of its own. At the end the mill
        # (level-bound, costed) holds 30 of the 50 levels, so 8 x 0.6 = 4.8 of the 20 mill levels
        # gained came with the annexation: points and jobs keep 1 - 4.8 / 20 = 0.76 of their figures.
        union = {"points": [
            _point("1900.1.1", 2.0, {"building_mill": _building(10), "building_hq": _building(0),
                                     "building_shop": _building(0)}, prior=1.0,
                   per_state={"1": [20000, 10000, 5000, 1000, 10]}),
            _point("1910.1.1", 2.0, {"building_mill": _building(30), "building_hq": _building(10),
                                     "building_shop": _building(10)}, prior=1.0,
                   per_state={"1": [20000, 10000, 5000, 1000, 42], "2": [3000, 1500, 900, 100, 8]}),
        ]}
        (iv,) = CF.intervals(union, MD, **LOOKUPS)
        self.assertEqual(iv.annexed_levels, 8.0)
        self.assertAlmostEqual(iv.bought_share, 0.76)
        self.assertAlmostEqual(iv.points, 20 * 100.0 * 0.76)
        self.assertAlmostEqual(iv.gross_jobs, 20 * 200.0 * 0.76)
        self.assertAlmostEqual(iv.jobs_per_point, 2.0)
        self.assertAlmostEqual(iv.points_observed, 2.0 * 52 * iv.years)          # the queues' rate: unscaled
        self.assertEqual(iv.uncosted_jobs, 10 * 200.0)
        (row,) = CF.counterfactual(union, MD, "none", WORLD, **LOOKUPS)
        self.assertAlmostEqual(row.cum_extra_jobs, 20 * 100.0 * 0.76 * (2.0 - 1.0) * 2.0)
        # The same levels with no per-state figures (a fixed state set) are all bought.
        for pt in union["points"]:
            del pt["per_state"]
        (iv,) = CF.intervals(union, MD, **LOOKUPS)
        self.assertEqual((iv.annexed_levels, iv.bought_share, iv.points), (0.0, 1.0, 2000.0))

    def test_an_annexation_larger_than_the_gain_buys_nothing(self):
        union = {"points": [
            _point("1900.1.1", 2.0, {"building_mill": _building(10)}, prior=1.0, per_state={"1": [1, 1, 0, 0, 10]}),
            _point("1910.1.1", 2.0, {"building_mill": _building(12)}, prior=1.0,
                   per_state={"1": [1, 1, 0, 0, 10], "2": [1, 1, 0, 0, 5]}),
        ]}
        (iv,) = CF.intervals(union, MD, **LOOKUPS)
        self.assertEqual((iv.bought_share, iv.points, iv.gross_jobs, iv.jobs_per_point), (0.0, 0.0, 0.0, 0.0))
        (row,) = CF.counterfactual(union, MD, "none", WORLD, **LOOKUPS)
        self.assertEqual(row.cum_extra_jobs, 0.0)

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
        summary = CF.summarize("TOY", series, MD, "historical", WORLD, **LOOKUPS)
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
        for series in ("FRA", "union", "GBR", "CHI"):
            # the historical shape reproduces the observed history, whatever the mod's curve is now
            self.assertIn("| " + series + " | historical | +0% |", out.stdout)
        self.assertIn("| FRA | current |", out.stdout)
        self.assertIn("| FRA | capped:1 |", out.stdout)
        self.assertIn("| FRA | slack:0.03:0.15 |", out.stdout)
        self.assertIn("| FRA | none |", out.stdout)
        self.assertIn("| CHI | none |", out.stdout)

    def test_cli_rejects_an_unknown_shape(self):
        self.assertEqual(CF.main(["--curves", "cubic"]), 2)


if __name__ == "__main__":
    unittest.main()
