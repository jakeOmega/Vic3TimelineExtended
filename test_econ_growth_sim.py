"""Cost curve shapes, point price and construction purchase for the growth sim (#1034)."""
import dataclasses
import math
import unittest

from scripts.analysis import econ_growth_sim as G
from scripts.analysis import econ_sim_data as D

C = D.CurveConstants(1.0, 1.0, 100.0, 10.0)


class TestParams(unittest.TestCase):
    def test_defaults(self):
        p = G.Params()
        self.assertEqual((p.curve, p.curve_cap, p.other_construction_mult, p.construction_good_price),
                         ("linear", None, 0.0, 0.93))
        self.assertEqual((p.private_invest_share, p.gov_invest_share, p.queue_per_state), (0.13, 0.05, 1.0))
        self.assertEqual((p.fill_rate, p.wage_floor, p.wage_step, p.wage_decay), (0.5, 0.05, 1.0, 0.2))
        self.assertEqual((p.vacancy_target, p.slack_target, p.subsistence_income, p.payback_years), (0.02, 0.03, 0.02, 10.0))
        self.assertEqual((p.price_level, p.services_jobs_per_gdp, p.demand_gdp_ratio), (1.0, 0.0, 0.3))
        self.assertEqual((p.g_max, p.g_min, p.g_slope, p.workforce_share), (0.025, -0.005, 0.004, 0.5))
        self.assertEqual((p.mode1_slack, p.mode2_slack, p.rich_gdppc, p.labour_bind_vacancy), (0.01, 0.10, 5.0, 0.05))

    def test_later_task_fields_exist(self):             # R4: Task 6 and Task 8 read these
        p = G.Params()
        self.assertEqual(p.return_rate, 0.1)
        self.assertIsNone(p.automation_lag_years)

    def test_mod_side_levers_are_neutral(self):
        p = G.Params()
        for name in ("cost_points_mult", "project_cap_mult", "construction_labour_mult", "late_employment_mult",
                     "eos_cap_mult", "maintenance_mult", "retool_charge_mult"):
            self.assertEqual(getattr(p, name), 1.0, name)
        self.assertEqual(p.era_shift_years, 0.0)

    def test_every_field_can_be_overridden_by_name(self):
        base = G.Params()
        for f in dataclasses.fields(G.Params):
            value = "capped" if f.name == "curve" else 0.5
            self.assertEqual(getattr(dataclasses.replace(base, **{f.name: value}), f.name), value, f.name)

    def test_curves_roster(self):
        self.assertEqual(G.CURVES, ("linear", "capped", "log", "sqrt", "world", "none"))


class TestCurve(unittest.TestCase):
    def test_linear(self):
        p = G.Params()
        for gdppc, x in ((0, 0), (1, 0), (25, 24 / 99 * 10), (100, 10), (1000, 10)):
            self.assertAlmostEqual(G.cost_mult(p, C, gdppc), x)

    def test_shapes(self):
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="log"), C, 10), 5.0)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="sqrt"), C, 25.75), 5.0)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="capped", curve_cap=3), C, 100), 3.0)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="capped", curve_cap=3), C, 25), 24 / 99 * 10)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="world"), C, 10, world_gdppc=5), 10 / 99)
        self.assertEqual(G.cost_mult(G.Params(curve="none"), C, 50), 0.0)

    def test_extremes_finite(self):                 # Review Focus 4
        for kw in ({"curve": "capped", "curve_cap": 0}, {"curve": "log"}, {"curve": "world"}):
            for gdppc in (0.0, 1e-12, 1e9):
                self.assertTrue(math.isfinite(G.cost_mult(G.Params(**kw), C, gdppc, world_gdppc=0.0)))

    def test_every_shape_is_finite_monotone_and_bounded(self):
        grid = [0.0, 1e-12, 0.5, 1.0, 1.5, 3.0, 25.0, 99.0, 100.0, 250.0, 1e9]
        for curve in G.CURVES:
            p = G.Params(curve=curve, curve_cap=4.0)
            xs = [G.cost_mult(p, C, g, world_gdppc=2.0) for g in grid]
            self.assertTrue(all(math.isfinite(x) for x in xs), curve)
            self.assertEqual(xs, sorted(xs), curve)
            self.assertGreaterEqual(min(xs), 0.0, curve)
            self.assertLessEqual(max(xs), 4.0 if curve == "capped" else C.max_mult, curve)

    def test_curves_agree_at_the_ends(self):
        for curve in ("linear", "log", "sqrt"):
            p = G.Params(curve=curve)
            self.assertEqual(G.cost_mult(p, C, 1.0), 0.0, curve)
            self.assertAlmostEqual(G.cost_mult(p, C, 100.0), 10.0, msg=curve)

    def test_cap_above_the_line_changes_nothing(self):     # capped keeps the line's slope; the cap only clamps
        p = G.Params(curve="capped", curve_cap=50.0)
        for gdppc in (0.0, 25.0, 100.0, 1000.0):
            self.assertAlmostEqual(G.cost_mult(p, C, gdppc), G.cost_mult(G.Params(), C, gdppc))

    def test_negative_gdp_per_capita_costs_nothing(self):
        for curve in ("linear", "log", "sqrt"):
            self.assertEqual(G.cost_mult(G.Params(curve=curve), C, -3.0), 0.0, curve)

    def test_world_without_a_world_figure_is_zero(self):
        p = G.Params(curve="world")
        self.assertEqual(G.cost_mult(p, C, 50.0), 0.0)
        self.assertEqual(G.cost_mult(p, C, 50.0, world_gdppc=None), 0.0)
        self.assertEqual(G.cost_mult(p, C, 50.0, world_gdppc=0.0), 0.0)

    def test_world_uses_the_ratio_against_the_ceiling_ratio(self):
        c = D.CurveConstants(10.0, 1.0, 100.0, 10.0)        # reference 10 changes nothing for the world curve
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="world"), c, 20.0, world_gdppc=10.0), 10 / 99)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="world"), c, 1000.0, world_gdppc=10.0), 10.0)

    def test_reference_scales_the_thresholds(self):
        c = D.CurveConstants(50.0, 1.0, 100.0, 10.0)
        self.assertEqual(G.cost_mult(G.Params(), c, 50.0), 0.0)
        self.assertAlmostEqual(G.cost_mult(G.Params(), c, 5000.0), 10.0)

    def test_capped_without_a_cap_is_an_error(self):
        with self.assertRaises(ValueError):
            G.cost_mult(G.Params(curve="capped"), C, 50.0)

    def test_unknown_curve_is_an_error(self):
        with self.assertRaises(ValueError):
            G.cost_mult(G.Params(curve="cubic"), C, 50.0)

    def test_degenerate_span_is_a_step(self):
        c = D.CurveConstants(1.0, 5.0, 5.0, 10.0)           # floor == ceiling
        for curve in ("linear", "log", "sqrt"):
            p = G.Params(curve=curve)
            self.assertEqual(G.cost_mult(p, c, 4.9), 0.0, curve)
            self.assertEqual(G.cost_mult(p, c, 5.0), 10.0, curve)

    def test_log_with_a_zero_floor_is_an_error(self):
        with self.assertRaises(ValueError):
            G.cost_mult(G.Params(curve="log"), D.CurveConstants(1.0, 0.0, 100.0, 10.0), 5.0)


class TestPointPrice(unittest.TestCase):
    def test_point_price_matches_saves(self):       # spec 4.1: FRA 1917 GBP 1,584; EUN 1998 GBP 4,925
        self.assertAlmostEqual(G.point_price(G.Params(construction_good_price=0.95), 1000, 0.666), 1582.7, places=1)
        self.assertAlmostEqual(G.point_price(G.Params(construction_good_price=0.91), 1000, 4.409), 4922.2, places=1)

    def test_other_construction_mult_scales_the_price(self):
        base = G.point_price(G.Params(), 1000, 2.0)
        self.assertAlmostEqual(G.point_price(G.Params(other_construction_mult=0.5), 1000, 2.0), base * 1.5)

    def test_free_construction_good_is_a_zero_price(self):
        self.assertEqual(G.point_price(G.Params(construction_good_price=0.0), 1000, 2.0), 0.0)


class TestPointsBought(unittest.TestCase):
    def test_cap_binds(self):
        self.assertEqual(G.points_bought(1e9, 1000, 5000), (5000, True))
        self.assertEqual(G.points_bought(1e6, 1000, 5000), (1000, False))

    def test_exactly_at_the_cap_is_not_cap_bound(self):
        self.assertEqual(G.points_bought(5e6, 1000, 5000), (5000, False))

    def test_zero_price_buys_up_to_the_cap(self):   # Review Focus 4: no ZeroDivisionError
        self.assertEqual(G.points_bought(1.0, 0.0, 5000), (5000, True))
        self.assertEqual(G.points_bought(0.0, 0.0, 5000), (0.0, False))

    def test_nothing_to_spend_or_no_capacity(self):
        self.assertEqual(G.points_bought(0.0, 1000, 5000), (0.0, False))
        self.assertEqual(G.points_bought(-5.0, 1000, 5000), (0.0, False))
        self.assertEqual(G.points_bought(1e9, 1000, 0.0), (0.0, True))


if __name__ == "__main__":
    unittest.main()
