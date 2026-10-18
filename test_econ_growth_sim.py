"""The growth sim (#1034): cost curve shapes, point price, construction purchase,
and the yearly step on toy mod data."""
import dataclasses
import math
import time
import unittest

from scripts.analysis import econ_growth_sim as G
from scripts.analysis import econ_sim_data as D
from scripts.analysis import econ_sim_scenarios as SC

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


if __name__ == "__main__":
    unittest.main()
