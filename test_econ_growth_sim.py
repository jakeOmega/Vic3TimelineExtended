"""The growth sim (#1034): cost curve shapes, point price, construction purchase,
the yearly step on toy mod data, and the scenarios and calibration code on the
committed dataset."""
import contextlib
import csv
import dataclasses
import io
import json
import math
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from scripts.analysis import econ_growth_sim as G
from scripts.analysis import econ_sim_calibrate as CAL
from scripts.analysis import econ_sim_data as D
from scripts.analysis import econ_sim_scenarios as SC

ROOT = Path(__file__).resolve().parent
C = D.CurveConstants(1.0, 1.0, 100.0, 10.0)


# --------------------------------------------------------------------------
# Toy mod data for the yearly step: literal ladders, no ModState.
# --------------------------------------------------------------------------


def _pm(name, era, employment, crew=0.0, goods_in=0.0, goods_out=0.0, construction_out=0.0):
    return D.PMFigures(name, era, employment, crew, goods_in, goods_out, construction_out)


TOY_START_STAFF = 5000.0                                    # the toy light base PM's staff a level
TOY_BASE_VA = 550.0
TOY_NONE = _pm("toy_none", 0, 0.0)
TOY_LIGHT_BASE = _pm("toy_bakery", 0, TOY_START_STAFF, goods_in=250.0, goods_out=800.0)
TOY_LIGHT_TIER1 = _pm("toy_automated", 1, -1000.0, goods_in=150.0)      # R6: breakeven exactly 0.15


def _toy(light_automation, maintenance=0.0, light_base=(TOY_LIGHT_BASE,)):
    numbers = D.ModNumbers(
        curve=C, cost_tiers={}, retool_mult=10.0, retool_weeks=260, prices={"construction": 1000.0},
        base_project_cap=10.0, base_eos_cap=20.0, project_cap_steps=(), eos_cap_steps=(), tech_era={},
    )
    ladders = {
        "light": D.Ladder("light", "building_toy_light", maintenance, tuple(light_base), (TOY_NONE, *light_automation)),
        "construction": D.Ladder("construction", "building_toy_construction", 0.0,
                                 (_pm("toy_wooden", 0, 6000.0, construction_out=1.0),), (TOY_NONE,)),
    }
    return D.ModData(numbers, ladders, None)


TOY = _toy((TOY_LIGHT_TIER1,))
# A crew-only tier, like pm_ai_managed_fab: its cut cancels the base's per-level staff
# and leaves a fixed crew of 1000 a building. Breakeven 150/5000 = 0.03, under the wage
# floor, so it is taken in the first year (Review Focus 4).
TOY_WITH_CREW_TIER = _toy((_pm("toy_crew_fab", 1, -TOY_START_STAFF, crew=1000.0, goods_in=150.0),))
# Two tiers in one PM group; tier 2 (breakeven 0.10) replaces tier 1, it does not add to it.
TOY_TWO_TIERS = _toy((TOY_LIGHT_TIER1, _pm("toy_robotic", 1, -2000.0, goods_in=200.0)))
# The same tier 2, unlocked only at era 6.
TOY_LATE_TIER2 = _toy((TOY_LIGHT_TIER1, _pm("toy_robotic", 6, -2000.0, goods_in=200.0)))
# The reviewer's case (R25): tier 2 pays against none from 0.225 a week, but against
# tier 1 only from 0.30 (300 more goods for 1000 more jobs).
TOY_DEAR_TIER2 = _toy((TOY_LIGHT_TIER1, _pm("toy_dear_robotic", 1, -2000.0, goods_in=450.0)))


def toy_scenario(**overrides):
    """A 1867-1900 player scenario: one light sector, 1,000 states, wage start 0.05.

    R11: the start is fully staffed (employed_level = the start level-bound jobs), and
    the population defaults to the one whose workforce is exactly the start's people,
    so the first year doesn't reconcile the workforce. Both can be overridden.
    """
    levels = overrides.pop("levels", {"light": 100.0})
    peasants = overrides.pop("peasants", 3e6)
    unemployed = overrides.pop("unemployed", 2e5)
    employed_level = overrides.pop("employed_level", levels.get("light", 0.0) * TOY_START_STAFF)
    employed_demand = overrides.pop("employed_demand", 0.0)
    people = peasants + unemployed + employed_level + employed_demand
    fields = dict(
        name="toy", kind="player", series="", start_year=1867, end_year=1900,
        population=people / G.Params().workforce_share, peasants=peasants, unemployed=unemployed,
        subsistence_capacity=1.5 * peasants,
        employed_level=employed_level, employed_demand=employed_demand,
        gdp=52 * TOY_BASE_VA * levels.get("light", 0.0) * 1.3, points_week=0.0, wage_start=0.05,
        n_states=1000, levels=levels,
        k_emp={"light": 1.0}, k_va={"light": 1.0}, cost_points={"light": 100.0},
        era_points=((1867, 5.0),), land_floor=((1867, 0.0),), welfare=((1867, 0.0),),
        alloc=((1867, {"light": 1.0}),), world_gdppc=(),
        automation_lag_years=0.0, rich_from_year=None, annexations=(),
    )
    fields.update(overrides)
    return SC.Scenario(**fields)


def rec(**kw):
    """A YearRecord with a workforce of 1 and neutral defaults: no slack, fully employed,
    a wage above the floor, a poor country (gdppc 1) in a year before any rich_from_year
    a test sets, money-bound. `jobs_by_sector` follows `jobs_level` unless given."""
    fields = dict(
        year=1900, era=1.0, population=2.0, workforce=1.0, peasants=0.0, unemployed=0.0, employed=1.0,
        jobs_level=1.0, jobs_demand=0.0, vacancies=0.0, wage=0.1, gdp=1.0, gdppc=1.0, x=0.0, spend=0.0,
        points=0.0, money_bound=True, cap_bound=False, labour_bound=False, auto_tiers={"light": 0},
        levels={"light": 1.0},
    )
    fields.update(kw)
    fields.setdefault("jobs_by_sector", {"light": fields["jobs_level"]})
    return G.YearRecord(**fields)


class TestParams(unittest.TestCase):
    def test_defaults(self):
        p = G.Params()
        self.assertEqual((p.curve, p.curve_cap, p.other_construction_mult, p.construction_good_price),
                         ("linear", None, 0.0, 0.93))
        self.assertEqual(p.curve_slope, 1.0)
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

    def test_slope_scales_the_linear_curve(self):          # R34: slope:k is the mod's line at max_mult x k
        self.assertAlmostEqual(G.cost_mult(G.Params(curve_slope=0.5), C, 100), 5.0)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve_slope=0.5), C, 1000), 5.0)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve_slope=0.5), C, 25), 0.5 * 24 / 99 * 10)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve_slope=2.0), C, 100), 20.0)
        self.assertEqual(G.cost_mult(G.Params(curve_slope=0.0), C, 100), 0.0)
        for gdppc in (0.0, 25.0, 100.0):                    # the default leaves the mod's curve alone
            self.assertEqual(G.cost_mult(G.Params(curve_slope=1.0), C, gdppc), G.cost_mult(G.Params(), C, gdppc))

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



class TestScenario(unittest.TestCase):
    def test_era_interpolates_and_holds_flat(self):
        sc = toy_scenario(era_points=((1867, 1.0), (1900, 5.0)))
        self.assertEqual(sc.era_at(1850), 1.0)
        self.assertAlmostEqual(sc.era_at(1880), 1 + 4 * 13 / 33)
        self.assertEqual(sc.era_at(1950), 5.0)

    def test_step_schedules_hold_from_each_point(self):
        sc = toy_scenario(land_floor=((1867, 0.5), (1890, 0.0)), welfare=((1867, 0.0), (1880, 2.0)),
                          alloc=((1867, {"light": 1.0}), (1885, {"light": 0.5, "heavy": 0.5})))
        self.assertEqual([sc.land_floor_at(y) for y in (1860, 1867, 1889, 1890, 1950)], [0.5, 0.5, 0.5, 0.0, 0.0])
        self.assertEqual([sc.welfare_at(y) for y in (1867, 1879, 1880)], [0.0, 0.0, 2.0])
        self.assertEqual(sc.alloc_at(1884), {"light": 1.0})
        self.assertEqual(sc.alloc_at(1885), {"light": 0.5, "heavy": 0.5})

    def test_world_gdppc_is_linear_and_none_without_points(self):
        self.assertIsNone(toy_scenario().world_gdppc_at(1900))
        sc = toy_scenario(world_gdppc=((1900, 2.0), (1910, 4.0)))
        self.assertEqual([sc.world_gdppc_at(y) for y in (1890, 1905, 1920)], [2.0, 3.0, 4.0])

    def test_wage_start_defaults_to_none(self):
        fields = dataclasses.asdict(toy_scenario())
        del fields["wage_start"]
        self.assertIsNone(SC.Scenario(**fields).wage_start)


class TestStep(unittest.TestCase):
    def test_workforce_conserved(self):
        for rec in G.run(toy_scenario(), TOY, G.Params()):
            self.assertAlmostEqual(rec.peasants + rec.unemployed + rec.employed, rec.workforce, delta=1e-6 * rec.workforce)

    def test_no_negative_stocks(self):
        for rec in G.run(toy_scenario(), TOY, G.Params()):
            self.assertTrue(min(rec.peasants, rec.unemployed, rec.employed, rec.wage) >= 0)

    def test_peasant_floor_holds(self):
        sc = toy_scenario(land_floor=((1867, 0.5),), levels={"light": 1e6})
        start = sc.peasants
        self.assertTrue(all(r.peasants >= 0.5 * start - 1e-6 for r in G.run(sc, TOY, G.Params(fill_rate=1.0))))

    def test_wage_at_floor_with_slack(self):
        recs = G.run(toy_scenario(peasants=9e6, levels={"light": 10}), TOY, G.Params(private_invest_share=0, gov_invest_share=0))
        self.assertTrue(all(abs(r.wage - G.Params().wage_floor) < 1e-12 for r in recs))

    def test_wage_rises_when_short_and_respects_margin(self):
        recs = G.run(toy_scenario(population=2e5, peasants=0, levels={"light": 1000}), TOY, G.Params())
        self.assertGreater(recs[-1].wage, recs[0].wage)
        self.assertTrue(all(r.labour_bound for r in recs[1:]))
        # The 0.25 margin: short of labour every year, the wage sits at 0.75 of VA a
        # worker (550 / 5000 a week, x economy of scale on the levels the year began with).
        for prev, r in zip(recs, recs[1:]):
            eos = 0.01 * min(max(prev.levels["light"] / 1000 - 1, 0), 20)
            self.assertAlmostEqual(r.wage, 0.75 * TOY_BASE_VA * (1 + eos) / TOY_START_STAFF)

    def test_margin_stops_a_raise_but_doesnt_cut(self):
        # Start at 1.0 a week, far past 0.75 x 0.11, with no slack and short of labour
        # from the second year: the wage holds rather than dropping to the margin.
        recs = G.run(toy_scenario(population=2e5, peasants=0, unemployed=0, levels={"light": 1000}, wage_start=1.0),
                     TOY, G.Params())
        self.assertTrue(all(r.labour_bound for r in recs[1:]))
        self.assertTrue(all(r.wage == 1.0 for r in recs))

    def test_ai_lags_player(self):
        first = lambda kind: next(r.year for r in G.run(toy_scenario(kind=kind, automation_lag_years=5, wage_start=1.0), TOY, G.Params())
                                  if r.auto_tiers["light"] > 0)
        self.assertEqual(first("ai") - first("player"), 5)

    def test_params_lag_overrides_the_scenario(self):      # R4
        first = next(r.year for r in G.run(toy_scenario(kind="ai", automation_lag_years=5, wage_start=1.0), TOY,
                                           G.Params(automation_lag_years=2)) if r.auto_tiers["light"] > 0)
        self.assertEqual(first, 1869)

    def test_cap_bound_flag(self):
        recs = G.run(toy_scenario(), TOY, G.Params(private_invest_share=0.9, queue_per_state=0.001))
        self.assertTrue(any(r.cap_bound for r in recs))

    def test_extremes_finite(self):                 # Review Focus 4
        for kw in ({"fill_rate": 0}, {"payback_years": 0}, {"curve": "capped", "curve_cap": 0}):
            for r in G.run(toy_scenario(), TOY_WITH_CREW_TIER, G.Params(**kw)):
                self.assertTrue(all(math.isfinite(v) for v in (r.gdp, r.gdppc, r.wage, r.points, r.x)))

    def test_crew_only_tier_staffs_its_crew(self):  # Review Focus 4: 0 per-level staff, a crew a building
        recs = G.run(toy_scenario(), TOY_WITH_CREW_TIER, G.Params())
        self.assertEqual(recs[0].auto_tiers["light"], 1)
        levels_1868 = recs[0].levels["light"]
        self.assertAlmostEqual(recs[1].jobs_by_sector["light"], 1000.0 * levels_1868)     # under 1,000 states: a building a level
        self.assertGreater(recs[1].gdp, 0)

    def test_levers_apply(self):
        base = G.run(toy_scenario(), TOY, G.Params())[-1].levels["light"]
        dear = G.run(toy_scenario(), TOY, G.Params(cost_points_mult=2.0))[-1].levels["light"]
        self.assertLess(dear, base)
        eras = {r.year: r.era for r in G.run(toy_scenario(era_points=((1867, 1.0), (1900, 5.0))), TOY, G.Params(era_shift_years=10))}
        self.assertAlmostEqual(eras[1890], 1 + 4 * 13 / 33)              # era_at(1880)

    def test_run_speed(self):
        t = time.perf_counter(); G.run(toy_scenario(end_year=2050), TOY, G.Params())
        self.assertLess(time.perf_counter() - t, 1.0)

    def test_run_covers_start_to_end_inclusive(self):
        self.assertEqual([r.year for r in G.run(toy_scenario(), TOY, G.Params())], list(range(1867, 1901)))

    # --- return to subsistence (step 12) ------------------------------------

    def _no_growth_no_jobs(self, **kw):
        return G.Params(private_invest_share=0, gov_invest_share=0, g_max=0.0, g_min=0.0, **kw)

    def test_welfare_above_subsistence_premium_keeps_the_unemployed_out(self):
        p = self._no_growth_no_jobs()
        welfare = 1.3 * p.subsistence_income * 1.01
        for r in G.run(toy_scenario(unemployed=1e6, welfare=((1867, welfare),)), TOY, p):
            self.assertAlmostEqual(r.peasants, 3e6)
            self.assertAlmostEqual(r.unemployed, 1e6)

    def test_no_welfare_lets_the_unemployed_return(self):
        p = self._no_growth_no_jobs()
        recs = G.run(toy_scenario(unemployed=1e6, welfare=((1867, 0.0),)), TOY, p)
        self.assertAlmostEqual(recs[0].peasants, 3e6 + p.return_rate * 1e6)
        self.assertAlmostEqual(recs[0].unemployed, (1 - p.return_rate) * 1e6)

    def test_welfare_is_compared_in_base_prices(self):
        # 0.03 nominal clears 1.3 x 0.02; at price level 2 it is 0.015 in base prices, and they return.
        p = self._no_growth_no_jobs(price_level=2.0)
        recs = G.run(toy_scenario(unemployed=1e6, welfare=((1867, 0.03),)), TOY, p)
        self.assertGreater(recs[0].peasants, 3e6)

    def test_returns_stop_at_subsistence_capacity(self):
        p = self._no_growth_no_jobs(return_rate=1.0)
        recs = G.run(toy_scenario(unemployed=1e6, subsistence_capacity=3.4e6), TOY, p)
        self.assertAlmostEqual(recs[-1].peasants, 3.4e6)
        self.assertAlmostEqual(recs[-1].unemployed, 6e5)

    # --- the step's choices -------------------------------------------------

    def test_automation_tiers_replace_each_other(self):
        # A PM group holds alternatives: at tier 2 the staff is base + tier 2 (5000 - 2000),
        # not base + tier 1 + tier 2 (2000).
        recs = G.run(toy_scenario(wage_start=1.0), TOY_TWO_TIERS, G.Params())
        i = next(i for i, r in enumerate(recs) if r.auto_tiers["light"] == 2)
        self.assertAlmostEqual(recs[i + 1].jobs_by_sector["light"], 3000.0 * recs[i].levels["light"])

    def test_retooling_waits_and_adopts_one_tier_a_year(self):
        # Tier 2 unlocks in 1869 and beats tier 1, but tier 1's 260 weeks of retooling run to 1872.
        sc = toy_scenario(wage_start=1.0, era_points=((1867, 5.0), (1869, 6.0)))
        tiers = {r.year: r.auto_tiers["light"] for r in G.run(sc, TOY_LATE_TIER2, G.Params())}
        self.assertEqual((tiers[1867], tiers[1869], tiers[1871], tiers[1872]), (1, 1, 1, 2))

    # --- automation is a best response against the tier in use (R25) -----------

    def test_next_tier_is_judged_against_the_current_one(self):
        # At 0.25 a week tier 1 saves 100 a level and tier 2 only 50: tier 1, never tier 2
        # (tier 2 is past its breakeven against none, 0.225, but not against tier 1, 0.30).
        p = G.Params(wage_floor=0.25, private_invest_share=0, gov_invest_share=0)
        recs = G.run(toy_scenario(wage_start=0.25), TOY_DEAR_TIER2, p)
        self.assertTrue(all(r.wage == 0.25 for r in recs))
        self.assertEqual({r.auto_tiers["light"] for r in recs}, {1})

    def test_a_sector_can_skip_a_tier(self):
        # At 1.0 a week tier 2 saves 1,550 a level against tier 1's 850: straight from none
        # to 2 in the first year, and (the wage held there) never through tier 1.
        recs = G.run(toy_scenario(wage_start=1.0), TOY_DEAR_TIER2, G.Params(wage_floor=1.0))
        self.assertEqual({r.auto_tiers["light"] for r in recs}, {2})

    def test_a_falling_wage_brings_a_sector_down_a_tier(self):
        # Tier 2 at 1.0; the wage then drifts to a floor of 0.25, where tier 1 saves more (below 0.30).
        recs = G.run(toy_scenario(wage_start=1.0), TOY_DEAR_TIER2, G.Params(wage_floor=0.25))
        tiers = [r.auto_tiers["light"] for r in recs]
        self.assertEqual((tiers[0], tiers[-1]), (2, 1))
        down = tiers.index(1)
        self.assertLess(recs[down].wage, 0.30 + 1e-9)

    def test_no_payback_horizon_takes_no_tier(self):
        # payback 0 with no maintenance: a zero gain doesn't clear a zero charge (both tests are strict).
        for wage_start in (0.05, 1.0):                  # below and above the tier's 0.15 breakeven
            recs = G.run(toy_scenario(wage_start=wage_start), TOY, G.Params(payback_years=0))
            self.assertEqual({r.auto_tiers["light"] for r in recs}, {0}, wage_start)

    def test_retooling_charge_comes_off_gdp(self):
        md = _toy((TOY_LIGHT_TIER1,), maintenance=0.1)
        full = G.run(toy_scenario(wage_start=1.0), md, G.Params())
        half = G.run(toy_scenario(wage_start=1.0), md, G.Params(retool_charge_mult=0.5))
        self.assertEqual((full[0].auto_tiers["light"], half[0].auto_tiers["light"]), (1, 1))
        p = G.Params()
        # A year's payment: levels x maintenance x 10 x point price at last year's x x 52, at price level and demand.
        charge = full[0].levels["light"] * 0.1 * 10 * G.point_price(p, 1000.0, full[0].x) * 52 * (1 + p.demand_gdp_ratio)
        self.assertAlmostEqual(half[1].gdp - full[1].gdp, 0.5 * charge, delta=1e-6 * charge)

    def test_automation_sheds_jobs_to_the_unemployed(self):
        # No hiring, growth or returns, so the unemployed move only by what is shed.
        recs = G.run(toy_scenario(wage_start=1.0), TOY, G.Params(fill_rate=0, return_rate=0, g_max=0.0, g_min=0.0))
        self.assertEqual(recs[0].auto_tiers["light"], 1)
        jobs_1868 = (TOY_START_STAFF - 1000.0) * recs[0].levels["light"]
        self.assertAlmostEqual(recs[1].jobs_by_sector["light"], jobs_1868)
        self.assertAlmostEqual(recs[1].unemployed - recs[0].unemployed, 100 * TOY_START_STAFF - jobs_1868)

    def test_annexation_adds_people_and_levels(self):
        event = {"population": 2e6, "peasants": 6e5, "unemployed": 1e5, "levels": {"light": 50.0}}
        recs = G.run(toy_scenario(annexations=((1870, event),)), TOY, G.Params())
        by_year = {r.year: r for r in recs}
        self.assertGreater(by_year[1870].levels["light"] - by_year[1869].levels["light"], 50.0)
        self.assertGreater(by_year[1870].population - by_year[1869].population, 2e6)
        for r in recs:
            self.assertAlmostEqual(r.peasants + r.unemployed + r.employed, r.workforce, delta=1e-6 * r.workforce)

    def test_annexation_adds_subsistence_capacity(self):          # R23
        # No hiring, growth, returns or investment; the event's population brings exactly its
        # own workforce (x 0.5), so the peasants move only by the event and the capacity.
        p = G.Params(fill_rate=0, return_rate=0, g_max=0.0, g_min=0.0, private_invest_share=0, gov_invest_share=0)
        event = {"population": 1.2e6, "peasants": 6e5, "unemployed": 0.0}
        bare = {r.year: r for r in G.run(toy_scenario(subsistence_capacity=3e6, annexations=((1870, event),)), TOY, p)}
        grown_event = dict(event, subsistence_capacity=9e5)
        grown = {r.year: r for r in G.run(toy_scenario(subsistence_capacity=3e6, annexations=((1870, grown_event),)), TOY, p)}
        # Without the event's capacity, the annexed peasants overflow into the unemployed.
        self.assertAlmostEqual(bare[1870].peasants, 3e6)
        self.assertAlmostEqual(bare[1870].unemployed - bare[1869].unemployed, 6e5)
        # With it, they stay peasants, and stay so in later years.
        self.assertAlmostEqual(grown[1870].peasants, 3.6e6)
        self.assertAlmostEqual(grown[1880].peasants, 3.6e6)
        self.assertAlmostEqual(grown[1870].unemployed, grown[1869].unemployed)

    def test_sector_without_cost_points_gets_no_levels(self):      # R14
        recs = G.run(toy_scenario(alloc=((1867, {"light": 0.5, "heavy": 0.5, "services": 0.2}),)), TOY, G.Params())
        self.assertAlmostEqual(recs[0].levels["light"] - 100.0, recs[0].points * 0.5 / 100.0)
        self.assertNotIn("heavy", recs[0].levels)

    def test_mod_side_levers_scale_their_figure(self):
        cap_bound = dict(private_invest_share=0.9, queue_per_state=0.001)
        one = G.run(toy_scenario(), TOY, G.Params(**cap_bound))[0]
        two = G.run(toy_scenario(), TOY, G.Params(project_cap_mult=2.0, **cap_bound))[0]
        self.assertAlmostEqual(two.points, 2 * one.points)
        # Construction jobs follow last year's points a week x workers a point (6000 / 1).
        base = G.run(toy_scenario(points_week=10.0), TOY, G.Params())[0]
        dear = G.run(toy_scenario(points_week=10.0), TOY, G.Params(construction_labour_mult=2.0))[0]
        self.assertEqual((base.jobs_demand, dear.jobs_demand), (60000.0, 120000.0))
        # Economy of scale: 1e5 levels over 1,000 states is past the cap of 20.
        big = toy_scenario(levels={"light": 1e5})
        eos1 = G.run(big, TOY, G.Params())[0].gdp
        eos2 = G.run(big, TOY, G.Params(eos_cap_mult=2.0))[0].gdp
        self.assertAlmostEqual(eos2 / eos1, 1.4 / 1.2)
        # Maintenance: 0.1 goods a level a week at the construction price comes off VA.
        md = _toy((TOY_LIGHT_TIER1,), maintenance=0.1)
        kept = G.run(toy_scenario(), md, G.Params())[0].gdp
        free = G.run(toy_scenario(), md, G.Params(maintenance_mult=0.0))[0].gdp
        self.assertAlmostEqual(free - kept, 100 * 0.1 * 1000 * 0.93 * 52 * 1.3)
        # Late PMs (era 8 and up): their staff scales.
        late = _toy((TOY_LIGHT_TIER1,), light_base=(dataclasses.replace(TOY_LIGHT_BASE, era=8),))
        sc8 = toy_scenario(era_points=((1867, 8.0),))
        self.assertEqual(G.run(sc8, late, G.Params(late_employment_mult=0.5))[0].jobs_by_sector["light"], 100 * 2500.0)


# --------------------------------------------------------------------------
# Diagnostics and the summary row (Task 7)
# --------------------------------------------------------------------------


def _with_sectors(**tier1):
    """TOY plus a ladder for each named sector: `sector=<PMFigures>` gives it that tier 1,
    `sector=None` gives it a ladder with no automation tiers (like infrastructure)."""
    ladders = dict(TOY.ladders)
    for sector, tier in tier1.items():
        automation = (TOY_NONE,) if tier is None else (TOY_NONE, tier)
        ladders[sector] = D.Ladder(sector, "building_toy_" + sector, 0.0, (TOY_LIGHT_BASE,), automation)
    return dataclasses.replace(TOY, ladders=ladders)


# Tier-1 figures for a second sector: breakeven 0.305; a tier that cuts no jobs (no breakeven);
# and a tier whose breakeven is -0.1 (it cuts jobs and adds goods).
HEAVY_DEAR = _pm("toy_heavy_tier", 1, -1000.0, goods_in=305.0)
HEAVY_NO_CUT = _pm("toy_heavy_goods", 1, 0.0, goods_in=100.0)
HEAVY_PAYS_ITSELF = _pm("toy_heavy_cheap", 1, -1000.0, goods_in=100.0, goods_out=200.0)


class TestClassify(unittest.TestCase):
    def test_classify(self):
        sc, p = toy_scenario(rich_from_year=1920), G.Params()
        self.assertEqual(G.classify(rec(year=1950, peasants=0, unemployed=0.005, labour_bound=True), sc, p), "mode1")
        self.assertEqual(G.classify(rec(year=1950, peasants=0.2, wage=p.wage_floor), sc, p), "mode2")
        self.assertEqual(G.classify(rec(year=1900, peasants=0.2, wage=p.wage_floor, gdppc=1.0), sc, p), "ok")
        self.assertEqual(G.classify(rec(year=1950, peasants=0.2, wage=2 * p.wage_floor), sc, p), "mode2")

    def test_a_rich_slack_year_at_a_high_wage_is_mode2(self):          # R34: the wage plays no part
        sc, p = toy_scenario(rich_from_year=1920), G.Params()
        self.assertEqual(G.classify(rec(year=1950, peasants=0.2, wage=100 * p.wage_floor), sc, p), "mode2")
        self.assertEqual(G.classify(rec(year=1950, unemployed=0.2, wage=50.0), sc, p), "mode2")
        # ... and the same year in a country that isn't rich is not.
        self.assertEqual(G.classify(rec(year=1900, peasants=0.2, wage=50.0), sc, p), "ok")

    def test_mode1_needs_labour_to_bind_and_slack_under_the_threshold(self):
        sc, p = toy_scenario(), G.Params()
        self.assertEqual(G.classify(rec(unemployed=0.005, labour_bound=False), sc, p), "ok")
        self.assertEqual(G.classify(rec(unemployed=0.01, labour_bound=True), sc, p), "ok")       # strictly under 1%
        self.assertEqual(G.classify(rec(peasants=0.004, unemployed=0.004, labour_bound=True), sc, p), "mode1")

    def test_mode2_counts_peasants_and_unemployed(self):
        sc, p = toy_scenario(rich_from_year=1920), G.Params()
        self.assertEqual(G.classify(rec(year=1950, peasants=0.06, unemployed=0.06), sc, p), "mode2")
        self.assertEqual(G.classify(rec(year=1950, peasants=0.1), sc, p), "ok")                  # strictly over 10%
        self.assertEqual(G.classify(rec(year=1950, peasants=0.1000001), sc, p), "mode2")

    def test_rich_is_gdp_per_head_or_the_scenarios_year(self):
        p = G.Params()
        no_year = toy_scenario(rich_from_year=None)
        self.assertEqual(G.classify(rec(year=2000, peasants=0.2, gdppc=p.rich_gdppc - 0.01), no_year, p), "ok")
        self.assertEqual(G.classify(rec(year=1900, peasants=0.2, gdppc=p.rich_gdppc), no_year, p), "mode2")
        dated = toy_scenario(rich_from_year=1920)
        self.assertEqual(G.classify(rec(year=1919, peasants=0.2), dated, p), "ok")
        self.assertEqual(G.classify(rec(year=1920, peasants=0.2), dated, p), "mode2")

    def test_no_workforce_is_not_an_error(self):        # Review Focus 4: no ZeroDivisionError
        sc, p = toy_scenario(rich_from_year=1900), G.Params()
        self.assertEqual(G.classify(rec(workforce=0.0, peasants=0.0), sc, p), "ok")

    def test_thresholds_are_parameters(self):
        sc = toy_scenario(rich_from_year=1900)
        r = rec(peasants=0.2)
        self.assertEqual(G.classify(r, sc, G.Params()), "mode2")
        self.assertEqual(G.classify(r, sc, G.Params(mode2_slack=0.25)), "ok")


class TestTakeoff(unittest.TestCase):
    def test_takeoff_and_years_to_10pct(self):
        pct = [60] * 10 + [60 - 2 * i for i in range(1, 26)] + [8] * 5     # whole percents: exact floats
        recs = [rec(year=1900 + i, peasants=s / 100) for i, s in enumerate(pct)]
        self.assertEqual(G.takeoff_year(recs), 1907)                     # 0.60 - 0.54 >= 0.05
        self.assertEqual(G.first_year_below(recs, 0.10, after=1907), 1935)   # strictly below 0.10

    def test_takeoff_is_none_without_a_fall_or_a_later_year(self):
        flat = [rec(year=1900 + i, peasants=0.6) for i in range(30)]
        self.assertIsNone(G.takeoff_year(flat))
        slow = [rec(year=1900 + i, peasants=0.6 - 0.005 * i) for i in range(30)]       # 2.5 points in five years
        self.assertIsNone(G.takeoff_year(slow))
        short = [rec(year=1900 + i, peasants=0.6 - 0.1 * i) for i in range(5)]         # no year has a t+5
        self.assertIsNone(G.takeoff_year(short))
        self.assertIsNone(G.takeoff_year([]))

    def test_takeoff_tolerates_float_slop_at_exactly_five_points(self):
        recs = [rec(year=1900, peasants=0.60), rec(year=1905, peasants=0.55)]
        self.assertLess(0.60 - 0.55, 0.05)                                  # the float difference is just under 0.05
        self.assertEqual(G.takeoff_year(recs), 1900)
        recs = [rec(year=1900, peasants=0.60), rec(year=1905, peasants=0.551)]       # 4.9 points is not a take-off
        self.assertIsNone(G.takeoff_year(recs))

    def test_takeoff_looks_five_years_on_by_year_not_by_position(self):
        gapped = [rec(year=1900, peasants=0.6), rec(year=1903, peasants=0.1), rec(year=1905, peasants=0.5)]
        self.assertEqual(G.takeoff_year(gapped), 1900)

    def test_first_year_below_edges(self):
        recs = [rec(year=1900 + i, peasants=s) for i, s in enumerate((0.04, 0.5, 0.5, 0.04, 0.04))]
        self.assertEqual(G.first_year_below(recs, 0.05), 1900)                 # the first, though it rises again
        self.assertEqual(G.first_year_below(recs, 0.05, after=1901), 1903)     # `after` counts the year itself
        self.assertEqual(G.first_year_below(recs, 0.05, after=1903), 1903)
        self.assertIsNone(G.first_year_below(recs, 0.05, after=1905))
        self.assertIsNone(G.first_year_below(recs, 0.01))
        self.assertIsNone(G.first_year_below([], 0.05))
        self.assertIsNone(G.first_year_below([rec(peasants=0.05)], 0.05))      # strictly below

    def test_no_workforce_is_not_an_error(self):
        self.assertIsNone(G.takeoff_year([rec(year=1900 + i, workforce=0.0, peasants=0.0) for i in range(8)]))
        self.assertEqual(G.first_year_below([rec(workforce=0.0, peasants=0.0)], 0.05), 1900)


class TestTurnYear(unittest.TestCase):
    @staticmethod
    def _years(n=40, start=1870):
        return [(start + i, 0.05 + 0.01 * i) for i in range(n)]

    def test_turn_year_uses_tier_one(self):
        recs = [rec(year=1870 + i, wage=0.05 + 0.01 * i, jobs_level=1.0) for i in range(30)]
        self.assertEqual(G.turn_year(recs, TOY, toy_scenario()), 1870 + 10)   # toy tier-1 breakeven 0.15

    def test_turn_year_needs_sectors_holding_half_the_jobs(self):
        # R5. Light's tier 1 pays at 0.15, heavy's at 0.305. With 40% of the jobs light isn't
        # enough: the turn waits for heavy, whose jobs bring the cumulative share to 100%.
        md = _with_sectors(heavy=HEAVY_DEAR)
        few_light = [rec(year=y, wage=w, jobs_by_sector={"light": 40.0, "heavy": 60.0}) for y, w in self._years()]
        self.assertEqual(G.turn_year(few_light, md, toy_scenario()), 1870 + 26)      # 0.31 >= 0.305; 0.30 is not
        # With 60% of the jobs light is enough on its own.
        most_light = [rec(year=y, wage=w, jobs_by_sector={"light": 60.0, "heavy": 40.0}) for y, w in self._years()]
        self.assertEqual(G.turn_year(most_light, md, toy_scenario()), 1870 + 10)

    def test_exactly_half_the_jobs_is_enough(self):
        md = _with_sectors(heavy=HEAVY_DEAR)
        halves = [rec(year=y, wage=w, jobs_by_sector={"light": 50.0, "heavy": 50.0}) for y, w in self._years()]
        self.assertEqual(G.turn_year(halves, md, toy_scenario()), 1870 + 10)

    def test_each_years_jobs_decide(self):
        # Light holds 30% of the jobs until 1884 and 60% from 1885: the wage passes 0.15 in 1880, the turn is 1885.
        md = _with_sectors(heavy=HEAVY_DEAR)
        recs = []
        for y, w in self._years():
            light = 30.0 if y < 1885 else 60.0
            recs.append(rec(year=y, wage=w, jobs_by_sector={"light": light, "heavy": 100.0 - light}))
        self.assertEqual(G.turn_year(recs, md, toy_scenario()), 1885)

    def test_sectors_without_a_tier_one_or_a_ladder_hold_jobs_but_never_qualify(self):
        md = _with_sectors(infrastructure=None)
        jobs = {"light": 40.0, "infrastructure": 30.0, "other": 30.0}
        recs = [rec(year=1870 + i, wage=100.0, jobs_by_sector=jobs) for i in range(5)]
        self.assertIsNone(G.turn_year(recs, md, toy_scenario()))
        jobs = {"light": 55.0, "infrastructure": 15.0, "other": 30.0}
        recs = [rec(year=1870 + i, wage=100.0, jobs_by_sector=jobs) for i in range(5)]
        self.assertEqual(G.turn_year(recs, md, toy_scenario()), 1870)

    def test_a_tier_that_cuts_no_jobs_never_qualifies(self):
        md = _with_sectors(heavy=HEAVY_NO_CUT)
        self.assertIsNone(D.breakeven(HEAVY_NO_CUT))
        recs = [rec(year=1870 + i, wage=100.0, jobs_by_sector={"heavy": 1.0}) for i in range(5)]
        self.assertIsNone(G.turn_year(recs, md, toy_scenario()))

    def test_a_negative_breakeven_always_qualifies(self):
        md = _with_sectors(heavy=HEAVY_PAYS_ITSELF)
        self.assertLess(D.breakeven(HEAVY_PAYS_ITSELF), 0)
        recs = [rec(year=1870 + i, wage=0.05, jobs_by_sector={"heavy": 1.0}) for i in range(5)]
        self.assertEqual(G.turn_year(recs, md, toy_scenario()), 1870)

    def test_tier_one_is_the_first_tier_a_technology_unlocks(self):
        # R29. An era-0 tier (like farming's pm_tools) has no unlocking technology and is
        # pre-industrial: the turn follows the first tier at era 1 or later, here tier 2
        # (era 3, breakeven 0.20), not tier 1 (era 0, breakeven 0.05) nor tier 3 (era 5, 0.30).
        tools = _pm("toy_tools", 0, -1000.0, goods_in=50.0)
        threshers = _pm("toy_threshers", 3, -1000.0, goods_in=200.0)
        tractors = _pm("toy_tractors", 5, -1000.0, goods_in=300.0)
        md = _toy((tools, threshers, tractors))
        recs = [rec(year=y, wage=w, era=6.0) for y, w in self._years()]        # an era past every tier
        self.assertEqual(G.turn_year(recs, md, toy_scenario()), 1870 + 15)           # 0.20 >= 0.20; 0.19 is not
        # A sector whose only tiers are era 0 has no tier that counts: it never qualifies.
        only_tools = _toy((tools,))
        self.assertIsNone(G.turn_year([rec(year=1870 + i, wage=100.0, era=6.0) for i in range(5)], only_tools, toy_scenario()))
        # An unlocked tier 1 is unchanged (the brief's toy: era 1, breakeven 0.15).
        self.assertEqual(G.turn_year(recs, TOY, toy_scenario()), 1870 + 10)

    def test_a_tier_waits_for_its_technology(self):
        # R30. Tier 1 is unlocked in era 3. The wage is far past its breakeven (0.15) from the
        # start, but the country is in era 2: no turn. Era 2.99 is still short, 3.0 is enough.
        md = _toy((_pm("toy_late_tier", 3, -1000.0, goods_in=150.0),))
        self.assertIsNone(G.turn_year([rec(year=1870 + i, wage=100.0, era=2.0) for i in range(5)], md, toy_scenario()))
        self.assertIsNone(G.turn_year([rec(wage=100.0, era=2.99)], md, toy_scenario()))
        self.assertEqual(G.turn_year([rec(year=1873, wage=100.0, era=3.0)], md, toy_scenario()), 1873)

    def test_the_turn_is_the_first_year_wage_and_era_both_hold(self):
        md = _toy((_pm("toy_late_tier", 3, -1000.0, goods_in=150.0),))           # breakeven 0.15, era 3
        # The wage is past the breakeven from the start; the era arrives at i = 4 (1.0 + 0.5 x 4).
        era_late = [rec(year=1870 + i, wage=1.0, era=1.0 + 0.5 * i) for i in range(12)]
        self.assertEqual(G.turn_year(era_late, md, toy_scenario()), 1870 + 4)
        # The era is there from the start; the wage reaches 0.15 at i = 10.
        wage_late = [rec(year=y, wage=w, era=3.0) for y, w in self._years()]
        self.assertEqual(G.turn_year(wage_late, md, toy_scenario()), 1870 + 10)
        # Both late: the era reaches 3.0 at i = 8 (0.25 a year) and the wage 0.15 at i = 10; the turn is the later.
        both = [rec(year=y, wage=w, era=1.0 + 0.25 * i) for i, (y, w) in enumerate(self._years())]
        self.assertEqual(G.turn_year(both, md, toy_scenario()), 1870 + 10)
        # A slow era (0.1 a year) reaches 3.0 at i = 20, long after the wage passes 0.15.
        slow_era = [rec(year=y, wage=w, era=1.0 + 0.1 * i) for i, (y, w) in enumerate(self._years())]
        self.assertEqual(G.turn_year(slow_era, md, toy_scenario()), 1870 + 20)

    def test_each_sector_waits_for_its_own_technology_and_the_denominator_is_all_jobs(self):
        # Light (breakeven 0.15, era 1) holds 40% of the jobs, heavy (0.10, era 4) 60%. The wage is high
        # throughout. Light alone is under half the jobs, so the turn waits for heavy's era 4.
        late_heavy = _pm("toy_heavy_late", 4, -1000.0, goods_in=100.0)
        md = _with_sectors(heavy=late_heavy)
        jobs = {"light": 40.0, "heavy": 60.0}
        recs = [rec(year=1870 + i, wage=1.0, era=1.0 + 0.5 * i, jobs_by_sector=jobs) for i in range(12)]
        self.assertEqual(G.turn_year(recs, md, toy_scenario()), 1870 + 6)          # era 4.0 at i = 6
        # With light at 60% it is enough from the start, whatever heavy's era.
        recs = [rec(year=1870 + i, wage=1.0, era=1.0 + 0.5 * i, jobs_by_sector={"light": 60.0, "heavy": 40.0}) for i in range(12)]
        self.assertEqual(G.turn_year(recs, md, toy_scenario()), 1870)

    def test_none_when_never_reached_or_without_jobs(self):
        self.assertIsNone(G.turn_year([rec(year=1870 + i, wage=0.14) for i in range(5)], TOY, toy_scenario()))
        self.assertIsNone(G.turn_year([], TOY, toy_scenario()))
        # A year with no level-bound jobs holds half of nothing: it isn't a turn.
        self.assertIsNone(G.turn_year([rec(wage=5.0, jobs_level=0.0)], TOY, toy_scenario()))


class TestSummary(unittest.TestCase):
    ADOPTED = {"light": 1}

    def _flat(self, start=1900, end=2050, **kw):
        return [rec(year=y, **kw) for y in range(start, end + 1)]

    def test_fields(self):
        self.assertEqual([f.name for f in dataclasses.fields(G.Summary)], [
            "setting", "scenario", "turn_year", "adoption_year", "peasants_below_5pct",
            "slack_1950", "slack_2000", "slack_2045", "mode1_years", "mode2_years",
            "money_years", "cap_years", "labour_years", "gdppc_2045",
            "takeoff_year", "takeoff_to_10pct", "takeoff_growth_ratio"])

    def test_counts_modes_and_binding_years_and_reads_the_slack_dates(self):
        sc, p = toy_scenario(rich_from_year=1920, name="the_run"), G.Params()
        recs = self._flat()
        by_year = {r.year: i for i, r in enumerate(recs)}
        for y in range(1930, 1935):                                        # five years of mode 2
            recs[by_year[y]] = rec(year=y, peasants=0.2)
        for y in range(1960, 1963):                                        # three years of mode 1, labour-bound
            recs[by_year[y]] = rec(year=y, unemployed=0.005, labour_bound=True, money_bound=False)
        for y in (1970, 1971):                                             # two years the cap binds
            recs[by_year[y]] = rec(year=y, cap_bound=True, money_bound=False)
        recs[by_year[1950]] = rec(year=1950, peasants=0.2, unemployed=0.05)
        recs[by_year[2000]] = rec(year=2000, peasants=0.04)
        recs[by_year[2045]] = rec(year=2045, unemployed=0.03, gdppc=42.0)
        s = G.summarize(recs, sc, TOY, p, "my_setting")
        self.assertEqual((s.setting, s.scenario), ("my_setting", "the_run"))
        self.assertEqual((s.mode1_years, s.mode2_years), (3, 6))         # the five, and 1950's slack year (rich, any wage: R34)
        self.assertEqual((s.money_years, s.cap_years, s.labour_years), (151 - 5, 2, 3))
        self.assertAlmostEqual(s.slack_1950, 0.25)
        self.assertAlmostEqual(s.slack_2000, 0.04)
        self.assertAlmostEqual(s.slack_2045, 0.03)
        self.assertEqual(s.gdppc_2045, 42.0)

    def test_a_run_that_ends_early_has_no_figure_for_a_later_date(self):
        s = G.summarize(self._flat(1867, 1990), toy_scenario(), TOY, G.Params(), "x")
        self.assertEqual(s.slack_1950, 0.0)
        self.assertIsNone(s.slack_2000)
        self.assertIsNone(s.slack_2045)
        self.assertIsNone(s.gdppc_2045)

    def test_a_run_that_never_reaches_a_threshold_gives_none(self):
        recs = self._flat(peasants=0.6, wage=0.05)
        s = G.summarize(recs, toy_scenario(), TOY, G.Params(), "x", reference=self._flat())
        self.assertIsNone(s.turn_year)
        self.assertIsNone(s.adoption_year)
        self.assertIsNone(s.peasants_below_5pct)
        self.assertIsNone(s.takeoff_year)
        self.assertIsNone(s.takeoff_to_10pct)
        self.assertIsNone(s.takeoff_growth_ratio)

    def test_an_empty_run_summarizes(self):
        s = G.summarize([], toy_scenario(), TOY, G.Params(), "x")
        self.assertEqual((s.mode1_years, s.mode2_years, s.money_years, s.cap_years, s.labour_years), (0, 0, 0, 0, 0))
        self.assertTrue(all(getattr(s, n) is None for n in (
            "turn_year", "adoption_year", "peasants_below_5pct", "slack_1950", "gdppc_2045", "takeoff_year")))

    def test_turn_and_peasants_below_5pct_come_from_the_records(self):
        recs = [rec(year=1870 + i, wage=0.05 + 0.01 * i, peasants=max(0.6 - 0.02 * i, 0.0)) for i in range(40)]
        s = G.summarize(recs, toy_scenario(), TOY, G.Params(), "x")
        self.assertEqual(s.turn_year, 1880)
        self.assertEqual(s.peasants_below_5pct, 1870 + 28)                 # 0.6 - 0.56 = 0.04 < 0.05; 0.06 is not

    def test_adoption_year_is_the_first_adoption_even_if_it_is_undone(self):
        recs = [rec(year=1900 + i, auto_tiers={"light": t, "heavy": 0}) for i, t in enumerate((0, 0, 1, 0, 0))]
        self.assertEqual(G.summarize(recs, toy_scenario(), TOY, G.Params(), "x").adoption_year, 1902)
        recs = [rec(year=1900 + i, auto_tiers={"light": 0, "heavy": h}) for i, h in enumerate((0, 0, 0, 2))]
        self.assertEqual(G.summarize(recs, toy_scenario(), TOY, G.Params(), "x").adoption_year, 1903)

    def test_adoption_year_from_a_real_run(self):
        p = G.Params()
        high = G.summarize(G.run(toy_scenario(wage_start=1.0), TOY, p), toy_scenario(), TOY, p, "x")
        self.assertEqual(high.adoption_year, 1867)
        low = G.summarize(G.run(toy_scenario(), TOY, p), toy_scenario(), TOY, p, "x")     # wage at the floor, under 0.15
        self.assertIsNone(low.adoption_year)

    def test_takeoff_growth_ratio(self):
        pct = [60] * 10 + [60 - 2 * i for i in range(1, 26)] + [8] * 5
        peasants = [s / 100 for s in pct]
        years = [1900 + i for i in range(len(pct))]

        def gdppc_from(rates):                                  # rates[y] is the growth into year y
            out, level = [], 1.0
            for y in years:
                level *= 1.0 + rates.get(y, 0.02)
                out.append(level)
            return out

        # Take-off is 1907: the window is the growth into 1908 .. 1927. 1907's own growth and
        # everything after 1927 are set apart so a misplaced window shows.
        rates = {1907: 0.9, **{y: 0.10 for y in range(1908, 1918)}, **{y: 0.02 for y in range(1918, 1928)}, 1928: 0.5}
        poor = [rec(year=y, peasants=s, gdppc=g) for y, s, g in zip(years, peasants, gdppc_from(rates))]
        rich = [rec(year=y, gdppc=g) for y, g in zip(years, gdppc_from({y: 0.02 for y in years}))]
        sc, p = toy_scenario(), G.Params()
        s = G.summarize(poor, sc, TOY, p, "x", reference=rich)
        self.assertEqual((s.takeoff_year, s.takeoff_to_10pct), (1907, 28))
        self.assertAlmostEqual(s.takeoff_growth_ratio, 3.0)                # (10 x 0.10 + 10 x 0.02) / 20 over 0.02
        self.assertIsNone(G.summarize(poor, sc, TOY, p, "x").takeoff_growth_ratio)             # no reference
        # A reference that ends early is compared over the years both runs have.
        short_rich = [r for r in rich if r.year <= 1917]
        self.assertAlmostEqual(G.summarize(poor, sc, TOY, p, "x", reference=short_rich).takeoff_growth_ratio, 5.0)
        # A reference that does not grow gives no ratio.
        still = [rec(year=y, gdppc=1.0) for y in years]
        self.assertIsNone(G.summarize(poor, sc, TOY, p, "x", reference=still).takeoff_growth_ratio)
        shrinking = [rec(year=y, gdppc=2.0 - 0.01 * i) for i, y in enumerate(years)]
        self.assertIsNone(G.summarize(poor, sc, TOY, p, "x", reference=shrinking).takeoff_growth_ratio)

    def test_no_takeoff_gives_no_ratio_even_with_a_reference(self):
        flat = self._flat(1900, 1950, peasants=0.6)
        s = G.summarize(flat, toy_scenario(), TOY, G.Params(), "x", reference=self._flat(1900, 1950))
        self.assertIsNone(s.takeoff_growth_ratio)

    def test_summarizes_a_real_run(self):
        sc, p = toy_scenario(end_year=2050), G.Params()
        recs = G.run(sc, TOY, p)
        s = G.summarize(recs, sc, TOY, p, "linear")
        self.assertEqual(s.scenario, "toy")
        self.assertLessEqual(s.mode1_years + s.mode2_years, len(recs))
        self.assertEqual((len(recs), s.mode1_years, s.mode2_years), (184, 0, 0))
        # The default toy economy is short of labour from 1870 (money-bound before); with
        # almost all GDP invested through a tiny queue, the cap binds every year instead.
        self.assertEqual((s.money_years, s.cap_years, s.labour_years), (3, 0, 181))
        capped = G.Params(private_invest_share=0.9, queue_per_state=0.001)
        c = G.summarize(G.run(sc, TOY, capped), sc, TOY, capped, "capped")
        self.assertEqual((c.money_years, c.cap_years, c.labour_years), (0, 184, 0))
        self.assertEqual(s.slack_2045, (recs[2045 - 1867].peasants + recs[2045 - 1867].unemployed) / recs[2045 - 1867].workforce)
        self.assertEqual(s.gdppc_2045, recs[2045 - 1867].gdppc)


class TestScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md, cls.ds = D.load_mod_data(), SC.load_dataset()

    def test_scenarios_build_and_run_finite(self):
        for name in SC.SCENARIOS:
            sc = SC.scenario(name, self.ds, self.md)
            self.assertEqual(sc.start_year, 1867, name)
            last = G.run(sc, self.md, G.params_for(name))[-1]
            self.assertTrue(all(math.isfinite(v) for v in (last.gdp, last.wage, last.points, last.peasants)), name)

    def test_start_matches_dataset(self):
        sc = SC.scenario("player_rich", self.ds, self.md)
        first = self.ds["series"]["FRA"]["points"][0]["slice"]
        self.assertAlmostEqual(sc.peasants, first["peasants"], delta=1)
        self.assertAlmostEqual(sc.wage_start, first["wage_per_worker"])

    def test_series_end_where_country_ends(self):     # Review Focus 2
        last_save_year = max(int(p["date"][:4]) for c in self.ds["series"].values() for p in c["points"])
        for name in ("ai_rich", "ai_poor"):
            sc = SC.scenario(name, self.ds, self.md)
            own_last = max(int(p["date"][:4]) for p in self.ds["series"][sc.series]["points"])
            self.assertEqual(sc.end_year, 2050 if own_last == last_save_year else own_last)

    def test_structural_params_shared(self):
        ps = {n: G.params_for(n) for n in SC.SCENARIOS}
        for name in CAL.STRUCTURAL:
            self.assertEqual(len({getattr(p, name) for p in ps.values()}), 1, name)

    def test_calibration_runs_use_the_historical_curve(self):
        # The saves were played under D.HISTORICAL_CURVE; the mod's own curve now differs, and
        # `run` and `sweep` keep using it, but every run `fit`, `starts` and `check` make
        # simulates the history under the old one.
        self.assertNotEqual(self.md.numbers.curve, D.HISTORICAL_CURVE)
        pinned = CAL.historical_md(self.md)
        self.assertEqual(pinned.numbers.curve, D.HISTORICAL_CURVE)
        self.assertIsNot(pinned, self.md)
        self.assertNotEqual(self.md.numbers.curve, D.HISTORICAL_CURVE)          # md itself is untouched
        self.assertEqual(dataclasses.replace(pinned.numbers, curve=self.md.numbers.curve), self.md.numbers)
        seen = []
        real_run = G.run

        def spy(sc, md, p):
            seen.append(md.numbers.curve)
            return real_run(sc, md, p)

        sc = SC.scenario("player_rich", self.ds, self.md)
        with mock.patch.object(G, "run", spy):
            CAL.check(self.ds, self.md)
            checked = len(seen)
            CAL.starts(sc, self.md)
            CAL.fit(sc, self.ds, self.md, G.Params(), ("price_level",), rounds=1)
        self.assertGreaterEqual(checked, 4)                                      # three scenarios and the union
        self.assertGreater(len(seen), checked)
        self.assertEqual(set(seen), {D.HISTORICAL_CURVE})
        # ... while the sim's own entry points take the md they are given, the mod's curve.
        seen.clear()
        with mock.patch.object(G, "run", spy):
            G.run(sc, self.md, G.params_for("player_rich"))
        self.assertEqual(set(seen), {self.md.numbers.curve})

    def test_check_reports_a_miss(self):
        md, ds = self.md, self.ds
        bad = Path(self.enterContext(tempfile.TemporaryDirectory())) / "p.json"
        bad.write_text(json.dumps({"structural": {"price_level": 100.0}, "behaviour": {}}))
        self.assertTrue(CAL.check(ds, md, params_path=bad))

    # --- beyond the brief's five ---------------------------------------------

    def test_start_economy_and_schedules(self):
        rich = SC.scenario("player_rich", self.ds, self.md)
        first = self.ds["series"]["FRA"]["points"][0]
        self.assertAlmostEqual(rich.gdp, first["owner"]["gdppc"] * first["slice"]["population"])
        self.assertAlmostEqual(rich.points_week, sum(first["owner"]["points_weekly"].values()))
        self.assertEqual(rich.subsistence_capacity, 1.5 * rich.peasants)
        self.assertEqual((rich.kind, rich.automation_lag_years, rich.rich_from_year, rich.n_states), ("player", 0.0, 1920, 33))
        self.assertEqual(len(rich.era_points), len(self.ds["series"]["FRA"]["points"]))
        # Employed people split between level-bound and demand-bound sectors; peasants are neither.
        self.assertAlmostEqual(rich.employed_level + rich.employed_demand, first["slice"]["employed"], delta=0.02 * first["slice"]["employed"])
        ai_poor = SC.scenario("ai_poor", self.ds, self.md)
        self.assertEqual((ai_poor.kind, ai_poor.series, ai_poor.rich_from_year, ai_poor.automation_lag_years), ("ai", "CHI", None, 5.0))
        self.assertEqual(ai_poor.land_floor_at(1867), 0.5)              # CHI 1867: serfdom
        self.assertEqual(rich.land_floor_at(1867), 0.0)                 # FRA 1867: peasant proprietorship
        poor = SC.scenario("player_poor", self.ds, self.md)
        self.assertEqual((poor.kind, poor.series, poor.automation_lag_years, poor.rich_from_year), ("player", "CHI", 0.0, None))
        self.assertEqual((poor.era_points, poor.alloc), (rich.era_points, rich.alloc))
        self.assertEqual((poor.peasants, poor.levels, poor.land_floor), (ai_poor.peasants, ai_poor.levels, ai_poor.land_floor))

    def test_every_level_bound_sector_has_a_cost(self):              # R14
        for name in SC.SCENARIOS:
            sc = SC.scenario(name, self.ds, self.md)
            for s in G.LEVEL_BOUND:
                if s != "other":
                    self.assertGreater(sc.cost_points.get(s, 0.0), 0.0, (name, s))

    def test_union_annexations_come_from_new_states(self):
        sc = SC.scenario("player_union", self.ds, self.md)
        pts = self.ds["series"]["union"]["points"]
        self.assertEqual(sc.n_states, len(pts[0]["per_state"]))
        grows = [(a, b) for a, b in zip(pts, pts[1:]) if set(b["per_state"]) - set(a["per_state"])]
        self.assertEqual(len(sc.annexations), len(grows))
        for (year, event), (a, b) in zip(sc.annexations, grows):
            new = set(b["per_state"]) - set(a["per_state"])
            self.assertEqual(year, int(b["date"][:4]))
            self.assertAlmostEqual(event["population"], sum(b["per_state"][s][0] for s in new))
            self.assertAlmostEqual(event["peasants"], sum(b["per_state"][s][2] for s in new))
            self.assertAlmostEqual(event["unemployed"], sum(b["per_state"][s][3] for s in new))
            self.assertAlmostEqual(event["subsistence_capacity"], 1.5 * event["peasants"])     # R23
            self.assertAlmostEqual(sum(event["levels"].values()), sum(b["per_state"][s][4] for s in new))

    def test_alloc_is_the_realised_construction(self):
        def point(date, **levels):
            return {"date": date, "slice": {"buildings_by_type": {b: {"levels": n} for b, n in levels.items()}}}

        buildings = self.md.ms.get_data("Buildings")

        def cost(b):
            return self.md.numbers.cost_tiers[D.val(D.val(buildings[b])["required_construction"])]

        points = [
            point("1900.1.1", building_wheat_farm=10, building_coal_mine=5, building_urban_center=100),
            point("1900.3.1", building_wheat_farm=11, building_coal_mine=5, building_urban_center=100),  # under a year on
            point("1910.1.1", building_wheat_farm=20, building_coal_mine=3, building_urban_center=300,
                  building_tourism_industry=2),
            point("1920.1.1", building_wheat_farm=20, building_coal_mine=13, building_urban_center=300,
                  building_tourism_industry=2),
        ]
        alloc = dict(SC.realised_alloc(points, self.md))
        self.assertEqual(sorted(alloc), [1900.0, 1910.0, 1920.0])
        farm, tourism = 10 * cost("building_wheat_farm"), 2 * cost("building_tourism_industry")
        # Urban centres have no construction cost (they grow by urbanization); lost levels don't count.
        self.assertEqual(set(alloc[1900.0]), {"farming", "services"})
        self.assertAlmostEqual(alloc[1900.0]["farming"], farm / (farm + tourism))
        self.assertAlmostEqual(alloc[1900.0]["services"], tourism / (farm + tourism))
        self.assertEqual(alloc[1910.0], {"mining": 1.0})
        self.assertEqual(alloc[1920.0], alloc[1910.0])              # the last point repeats the last interval

    def test_calibration_is_observed_over_the_ladder(self):
        b = D.base_at(self.md.ladders["light"], 2)
        slice_ = {"buildings_by_type": {
            "building_food_industry": {"levels": 4, "staffing": 2.0, "employees": 12000,
                                       "goods_sales": 2 * (1.5 * b.va + 100), "goods_cost": 200.0},
            "building_railway": {"levels": 3, "staffing": 3.0, "employees": 3000, "goods_sales": 100.0, "goods_cost": 400.0},
            "building_barrack": {"levels": 10, "staffing": 5.0, "employees": 2500, "goods_sales": 0.0, "goods_cost": 50.0},
            "building_subsistence_farms": {"levels": 9, "staffing": 9.0, "employees": 45000, "goods_sales": 9.0, "goods_cost": 0.0},
        }}
        k_emp, k_va = SC.sector_calibration(slice_, self.md, 2)
        self.assertAlmostEqual(k_emp["light"], 6000 / b.employment)
        self.assertAlmostEqual(k_va["light"], 1.5)                  # weekly figures, no / 52
        self.assertEqual(k_va["infrastructure"], 1.0)               # VA -100 a staffed level: no information
        self.assertAlmostEqual(k_emp["infrastructure"], 1000 / D.base_at(self.md.ladders["infrastructure"], 2).employment)
        self.assertEqual((k_emp["other"], k_va["other"]), (500.0, -10.0))     # other: the observed figures themselves
        self.assertNotIn("peasants", k_emp)

    def test_era_is_the_highest_with_half_its_techs(self):
        te = {"a": 1, "b": 1, "c": 2, "d": 2, "e": 3, "f": 3, "g": 3}
        self.assertEqual(SC.era_reached({"a", "c"}, te), 2)
        self.assertEqual(SC.era_reached({"a"}, te), 1)
        self.assertEqual(SC.era_reached({"e", "f", "unknown_tech"}, te), 3)
        self.assertEqual(SC.era_reached(set(), te), 0)

    def test_targets_are_every_point_after_the_start(self):
        sc = SC.scenario("ai_rich", self.ds, self.md)
        pts = self.ds["series"]["GBR"]["points"]
        t = CAL.targets(sc, self.ds)
        self.assertEqual(len(t), len(pts) - 1)
        self.assertEqual(set(t[0]), {"year", "peasant_share", "unemployed_share", "gdppc", "population", "points_week", "wage"})
        self.assertGreater(t[0]["year"], sc.start_year + 1)
        last = pts[-1]
        self.assertAlmostEqual(t[-1]["peasant_share"], last["slice"]["peasants"] / last["slice"]["workforce"])
        self.assertAlmostEqual(t[-1]["points_week"], sum(last["owner"]["points_weekly"].values()))
        self.assertAlmostEqual(t[-1]["wage"], last["slice"]["wage_per_worker"])

    def test_fit_never_raises_the_loss_and_moves_only_named_fields(self):
        sc = SC.scenario("player_rich", self.ds, self.md)
        t = CAL.targets(sc, self.ds)
        p0 = G.Params()
        p1 = CAL.fit(sc, self.ds, self.md, p0, ("price_level", "fill_rate"), rounds=1)
        md = CAL.historical_md(self.md)                             # the curve the fit simulates under
        self.assertLessEqual(CAL.loss(G.run(sc, md, p1), t, p1), CAL.loss(G.run(sc, md, p0), t, p0))
        moved = {f.name for f in dataclasses.fields(G.Params) if getattr(p1, f.name) != getattr(p0, f.name)}
        self.assertLessEqual(moved, {"price_level", "fill_rate"})
        self.assertEqual(p0, G.Params())                            # p0 untouched


class TestCalibration(unittest.TestCase):
    T0 = {"year": 1900.0, "peasant_share": 0.4, "unemployed_share": 0.1, "gdppc": 2.0, "population": 10.0,
          "points_week": 10.0, "wage": 1.0}

    def _recs(self):
        return [rec(year=1900, workforce=1.0, peasants=0.4, unemployed=0.1, population=10.0, gdppc=2.0, points=52 * 10.0, wage=0.5),
                rec(year=1901, workforce=1.0, peasants=0.2, unemployed=0.3, population=20.0, gdppc=8.0, points=52 * 40.0, wage=1.0)]

    def test_loss_is_zero_on_matching_records(self):
        # The sim's wage is in base prices: 0.5 x price level 2 is the observed 1.0.
        self.assertAlmostEqual(CAL.loss(self._recs(), [self.T0], G.Params(price_level=2.0)), 0.0)

    def test_loss_interpolates_to_the_target_year(self):
        mid = {"year": 1900.5, "peasant_share": 0.3, "unemployed_share": 0.2, "gdppc": 5.0, "population": 15.0,
               "points_week": 25.0, "wage": 1.5}
        self.assertAlmostEqual(CAL.loss(self._recs(), [mid], G.Params(price_level=2.0)), 0.0)

    def test_loss_weights_each_term_once(self):
        off = dict(self.T0, peasant_share=0.5, gdppc=2.0 * math.e)
        self.assertAlmostEqual(CAL.loss(self._recs(), [off], G.Params(price_level=2.0)), 0.1 ** 2 + 1.0)

    def test_loss_stays_finite_on_a_collapsed_economy(self):
        collapsed = [rec(year=1900, gdppc=-1.0, points=0.0)]
        self.assertTrue(math.isfinite(CAL.loss(collapsed, [self.T0], G.Params())))

    def test_params_for_layers_structural_then_behaviour(self):
        path = Path(self.enterContext(tempfile.TemporaryDirectory())) / "p.json"
        path.write_text(json.dumps({"structural": {"fill_rate": 0.3, "price_level": 2.0},
                                    "behaviour": {"player_rich": {"private_invest_share": 0.2},
                                                  "ai_rich": {"automation_lag_years": 3.0}}}))
        rich = G.params_for("player_rich", path)
        self.assertEqual((rich.fill_rate, rich.price_level, rich.private_invest_share), (0.3, 2.0, 0.2))
        self.assertEqual(G.params_for("player_poor", path).private_invest_share, 0.2)
        self.assertEqual(G.params_for("player_union", path).private_invest_share, 0.2)
        self.assertEqual(G.params_for("ai_rich", path).automation_lag_years, 3.0)
        ai_poor = G.params_for("ai_poor", path)                     # no behaviour entry: the defaults
        self.assertEqual((ai_poor.fill_rate, ai_poor.private_invest_share, ai_poor.automation_lag_years),
                         (0.3, G.Params().private_invest_share, None))
        path.write_text(json.dumps({"structural": {"no_such_param": 1.0}, "behaviour": {}}))
        with self.assertRaises(KeyError):
            G.params_for("player_rich", path)


class TestParsing(unittest.TestCase):
    def test_parse_sets_rejects_unknown(self):
        with self.assertRaises(SystemExit) as cm:
            G.parse_sets(["no_such_param=1"])
        self.assertIn("fill_rate", str(cm.exception))             # names the valid ones

    def test_parse_sets_coerces(self):
        self.assertEqual(G.parse_sets(["fill_rate=0.3", "curve=log"]), {"fill_rate": 0.3, "curve": "log"})

    def test_parse_sets_coerces_every_field_to_its_type(self):
        for f in dataclasses.fields(G.Params):
            text = "log" if f.name == "curve" else "2"
            value = G.parse_sets([f.name + "=" + text])[f.name]
            self.assertEqual(value, text if f.name == "curve" else 2.0, f.name)
            self.assertIsInstance(dataclasses.replace(G.Params(), **{f.name: value}), G.Params)

    def test_parse_sets_optional_fields_take_none(self):
        self.assertEqual(G.parse_sets(["curve_cap=none", "automation_lag_years=None"]),
                         {"curve_cap": None, "automation_lag_years": None})
        self.assertEqual(G.parse_sets(["curve_cap=3"]), {"curve_cap": 3.0})

    def test_parse_sets_rejects_malformed_items(self):
        for bad in ("fill_rate", "=3", "fill_rate=abc", "fill_rate=", "fill_rate=nan", "curve=cubic", "curve_cap=x"):
            with self.assertRaises(SystemExit, msg=bad):
                G.parse_sets([bad])
        with self.assertRaises(SystemExit):                       # a number that is not optional
            G.parse_sets(["fill_rate=none"])

    def test_parse_sets_later_item_wins(self):
        self.assertEqual(G.parse_sets(["fill_rate=0.3", "fill_rate=0.4"]), {"fill_rate": 0.4})

    def test_parse_curve(self):
        self.assertEqual(G.parse_curve("capped:3"), {"curve": "capped", "curve_cap": 3.0})
        self.assertEqual(G.parse_curve("log"), {"curve": "log"})
        self.assertEqual(G.parse_curve("linear"), {"curve": "linear"})
        self.assertEqual(G.parse_curve("world"), {"curve": "world"})
        self.assertEqual(G.parse_curve("none"), {"curve": "none"})
        self.assertEqual(G.parse_curve("slope:0.5"), {"curve": "linear", "curve_slope": 0.5})

    def test_parse_curve_slope_gives_the_curve_params_a_half_line(self):
        p = dataclasses.replace(G.Params(), **G.parse_curve("slope:0.5"))
        self.assertAlmostEqual(G.cost_mult(p, C, 100), 5.0)

    def test_parse_curve_rejects_bad_specs(self):
        for bad in ("cubic", "", "capped", "capped:", "capped:x", "slope", "slope:x", "log:2", "capped:nan", "slope:inf",
                    "capped:-1", "slope:-0.5"):
            with self.assertRaises(SystemExit, msg=bad):
                G.parse_curve(bad)
        with self.assertRaises(SystemExit) as cm:
            G.parse_curve("capped")
        self.assertIn("capped", str(cm.exception))


class TestSweep(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md, cls.ds = D.load_mod_data(), SC.load_dataset()

    def _expected(self, name, spec, sets=None):
        """What a sweep row should be: built by hand, the same way, from the pieces."""
        def params(scenario):
            p = dataclasses.replace(G.params_for(scenario), **(sets or {}))
            return dataclasses.replace(p, **G.parse_curve(spec))
        rich = SC.scenario("player_rich", self.ds, self.md)
        reference = G.run(rich, self.md, params("player_rich"))
        sc = SC.scenario(name, self.ds, self.md)
        p = params(name)
        return G.summarize(G.run(sc, self.md, p), sc, self.md, p, spec, reference=reference)

    def test_sweep_is_curve_by_scenario(self):
        rows = G.sweep(["linear", "none"], ["player_rich", "ai_poor"], self.md, self.ds, {})
        self.assertEqual([(r.setting, r.scenario) for r in rows],
                         [("linear", "player_rich"), ("linear", "ai_poor"), ("none", "player_rich"), ("none", "ai_poor")])

    def test_rows_use_the_fitted_params_and_the_rich_players_reference_under_the_same_curve(self):
        rows = G.sweep(["capped:1", "none"], ["ai_poor"], self.md, self.ds, {})
        self.assertEqual(rows, [self._expected("ai_poor", "capped:1"), self._expected("ai_poor", "none")])

    def test_sets_apply_before_the_curve(self):
        sets = {"fill_rate": 0.9, "curve_cap": 7.0}            # the sweep's capped:1 wins over a set cap
        rows = G.sweep(["capped:1"], ["player_rich"], self.md, self.ds, sets)
        self.assertEqual(rows, [self._expected("player_rich", "capped:1", sets)])
        self.assertNotEqual(rows, G.sweep(["capped:1"], ["player_rich"], self.md, self.ds, {}))

    def test_slope_and_capped_specs_run(self):
        rows = G.sweep(["slope:0.5", "capped:3"], ["player_rich"], self.md, self.ds, {})
        self.assertEqual([r.setting for r in rows], ["slope:0.5", "capped:3"])

    def test_player_rich_is_its_own_reference(self):
        row, = G.sweep(["linear"], ["player_rich"], self.md, self.ds, {})
        if row.takeoff_growth_ratio is not None:
            self.assertAlmostEqual(row.takeoff_growth_ratio, 1.0)

    def test_unknown_scenario_or_curve_exits(self):
        with self.assertRaises(SystemExit):
            G.sweep(["linear"], ["nowhere"], self.md, self.ds, {})
        with self.assertRaises(SystemExit):
            G.sweep(["cubic"], ["player_rich"], self.md, self.ds, {})

    def test_a_sweep_sets_the_curve_itself(self):
        with self.assertRaises(SystemExit):
            G.sweep(["linear"], ["player_rich"], self.md, self.ds, {"curve": "log"})


class TestRenderTable(unittest.TestCase):
    def _row(self, **kw):
        fields = dict(setting="linear", scenario="player_rich", turn_year=1900, adoption_year=1910,
                      peasants_below_5pct=1950, slack_1950=0.123, slack_2000=0.04, slack_2045=0.0,
                      mode1_years=3, mode2_years=20, money_years=100, cap_years=30, labour_years=21,
                      gdppc_2045=12.34, takeoff_year=1880, takeoff_to_10pct=35, takeoff_growth_ratio=3.456)
        fields.update(kw)
        return G.Summary(**fields)

    def test_columns_and_a_row(self):
        lines = G.render_table([self._row()]).splitlines()
        header = [c.strip() for c in lines[0].strip("|").split("|")]
        self.assertEqual(header[:5], ["Setting", "Type", "Turn year", "Adoption year", "Peasants < 5%"])
        self.assertEqual(len(header), 12)
        self.assertTrue(set(lines[1].replace("|", "")) <= set("-: "))
        cells = [c.strip() for c in lines[2].strip("|").split("|")]
        self.assertEqual(len(cells), 12)
        self.assertEqual(cells[:5], ["linear", "player_rich", "1900", "1910", "1950"])
        self.assertEqual(cells[5], "12.3% / 4.0% / 0.0%")
        self.assertEqual(cells[6], "3 / 20")
        self.assertEqual(cells[7], "100 / 30 / 21")
        self.assertEqual(cells[8], "12.3")
        self.assertEqual(cells[9:], ["1880", "35", "3.46"])
        self.assertTrue(lines[2].startswith("| linear |"))

    def test_none_shows_as_a_dash(self):
        row = self._row(turn_year=None, adoption_year=None, peasants_below_5pct=None, slack_1950=None, slack_2000=None,
                        slack_2045=None, gdppc_2045=None, takeoff_year=None, takeoff_to_10pct=None,
                        takeoff_growth_ratio=None)
        cells = [c.strip() for c in G.render_table([row]).splitlines()[2].strip("|").split("|")]
        self.assertEqual(cells[2:5], ["—", "—", "—"])
        self.assertEqual(cells[5], "— / — / —")
        self.assertEqual(cells[8:], ["—", "—", "—", "—"])
        part = [c.strip() for c in G.render_table([self._row(slack_2000=None)]).splitlines()[2].strip("|").split("|")]
        self.assertEqual(part[5], "12.3% / — / 0.0%")

    def test_zero_is_not_a_dash(self):
        cells = [c.strip() for c in G.render_table([self._row(takeoff_to_10pct=0, mode1_years=0)]).splitlines()[2].strip("|").split("|")]
        self.assertEqual((cells[6], cells[10]), ("0 / 20", "0"))

    def test_no_rows_is_a_header_only(self):
        self.assertEqual(len(G.render_table([]).splitlines()), 2)


class TestCli(unittest.TestCase):
    def _main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = G.main(list(argv))
        return code, out.getvalue()

    def test_cli_run_and_sweep(self):
        out = subprocess.run([sys.executable, "scripts/analysis/econ_growth_sim.py", "sweep",
                              "--scenarios", "player_rich", "--curves", "linear,none"],
                             capture_output=True, text=True, cwd=ROOT, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("| linear |", out.stdout)
        self.assertIn("| none |", out.stdout)

    def test_cli_run_prints_a_summary_and_writes_the_csv(self):
        path = Path(self.enterContext(tempfile.TemporaryDirectory())) / "run.csv"
        code, out = self._main("run", "--scenario", "player_rich", "--end", "1900", "--curve", "slope:0.5",
                               "--set", "fill_rate=0.3", "--csv", str(path))
        self.assertEqual(code, 0)
        self.assertIn("| slope:0.5 | player_rich |", out)
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual([int(r["year"]) for r in rows], list(range(1867, 1901)))
        for name in ("era", "population", "peasants", "unemployed", "wage", "gdp", "gdppc", "x", "points", "mode",
                     "peasant_share", "slack_share", "money_bound", "cap_bound", "labour_bound"):
            self.assertIn(name, rows[0], name)
        self.assertTrue(any(k.startswith("levels_") for k in rows[0]))
        self.assertTrue(any(k.startswith("tier_") for k in rows[0]))
        self.assertTrue(all(math.isfinite(float(r["gdppc"])) for r in rows))

    def test_cli_run_matches_the_library(self):
        path = Path(self.enterContext(tempfile.TemporaryDirectory())) / "run.csv"
        self._main("run", "--scenario", "ai_poor", "--end", "1950", "--curve", "capped:3", "--set", "fill_rate=0.3",
                   "--csv", str(path))
        md = D.load_mod_data()
        sc = dataclasses.replace(SC.scenario("ai_poor", SC.load_dataset(), md), end_year=1950)
        p = dataclasses.replace(G.params_for("ai_poor"), fill_rate=0.3, **G.parse_curve("capped:3"))
        records = G.run(sc, md, p)
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), len(records))
        self.assertAlmostEqual(float(rows[-1]["gdppc"]), records[-1].gdppc, places=6)
        self.assertAlmostEqual(float(rows[-1]["x"]), records[-1].x, places=6)

    def test_cli_run_without_a_csv_writes_nothing_and_prints_a_trace(self):
        code, out = self._main("run", "--scenario", "player_rich", "--end", "1900")
        self.assertEqual(code, 0)
        self.assertIn("| linear | player_rich |", out)

    def test_cli_sweep_prints_a_row_per_curve_and_scenario(self):
        code, out = self._main("sweep", "--scenarios", "player_rich,ai_poor", "--curves", "linear,slope:0.5,capped:3")
        self.assertEqual(code, 0)
        rows = [line for line in out.splitlines() if line.startswith("| ") and "Setting" not in line]
        self.assertEqual(len(rows), 6)
        self.assertIn("| slope:0.5 | ai_poor |", out)

    def test_cli_rejects_bad_input(self):
        for argv in (["run", "--scenario", "nowhere"], ["run"], ["run", "--scenario", "player_rich", "--set", "bogus=1"],
                     ["run", "--scenario", "player_rich", "--curve", "capped"],
                     ["run", "--scenario", "player_rich", "--set", "curve=capped"],
                     ["run", "--scenario", "player_rich", "--end", "1800"],
                     ["sweep", "--curves", "cubic"], ["sweep", "--scenarios", "nowhere"], ["sweep", "--curves", ""],
                     ["sweep", "--set", "curve=capped"], []):
            with self.assertRaises(SystemExit, msg=argv), contextlib.redirect_stderr(io.StringIO()):
                G.main(argv)


if __name__ == "__main__":
    unittest.main()
