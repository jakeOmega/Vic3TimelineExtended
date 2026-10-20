"""Wealth Concentration's remaining shocks, the r > g term and the Inequality effect (owner, 2026-10-19;
docs/superpowers/specs/2026-10-08-demographics-design.md §4.2, §7).

The shocks and r > g run whatever the Demographics rule (Wealth Concentration is the Inheritance system's, #822); the
Inequality effect runs under Full only. The script runs through test_demographics_registry's interpreter."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from test_demographics_registry import (  # noqa: E402  (helpers and paths only: no TestCase)
    APPLIED, DEMOG_ON_ACTIONS, EFFECTS, VALUES, WEALTH_EFFECTS, _block, _CountryEngine, _parse_script, _text)

INEQ_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_inequality_modifiers.txt"
WIDGETS = ROOT / "gui" / "te_demographics_widgets.gui"
NATION_TAB = ROOT / "scripts" / "generators" / "gen_nation_tab.py"
MISC_LOC = ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml"
TARGET_FIXTURES = {"te_inh_law_amendment_target": 75.0, "te_demog_wc_land_term": 4.0,
                   "te_demog_wc_tax_term": -5.0, "te_demog_wc_econ_term": 5.0}


def _scored(wc):
    """A state te_demog_wc_national can weigh: a score, its walk's levels, people and Gini."""
    return {"te_dg_wc": float(wc), "te_dg_wc_target": 50.0, "te_dg_lv_own": 10.0, "te_dg_lv_self": 0.0,
            "te_dg_lv_ctry": 0.0, "te_dg_lv_priv": 30.0, "te_dg_bureaucrats": 0.0, "te_dg_walk_pop": 1e6,
            "te_dg_gini": 0.5}


def _loc_keys():
    return set(re.findall(r"(?m)^ (\w+):\d* ", _text(MISC_LOC)))


# -- W2: ownership shocks ---------------------------------------------------------------------------------------------

class TestOwnershipShock(unittest.TestCase):
    """A state's state-owned share of capital moving 10 points or more in a year jumps its score half a point a point,
    at most 10: privatisation up, nationalisation down."""

    @staticmethod
    def state(wc=50.0, priv=60.0, self_=20.0, ctry=20.0, sown=None, pop=1e6, prev=1e6):
        s = {"te_dg_wc": wc, "te_dg_lv_priv": priv, "te_dg_lv_self": self_, "te_dg_lv_ctry": ctry,
             "te_dg_walk_pop": pop, "te_dg_walk_pop_prev": prev}
        if sown is not None:
            s["te_dg_wc_sown"] = sown
        return s

    def year(self, state, target=None):
        # target None: the state's own score, so the drift adds nothing and only the shock moves it
        # truncate: the engine's fixed point, where 0.3 - 0.2 is 0.1 exactly
        eng = _CountryEngine(states=[state], fixtures={"te_demog_wc_target": state["te_dg_wc"] if target is None
                                                       else target, "devastation": 0.0}, truncate=True)
        eng._in(state, _parse_script("te_demog_wc_state_yearly = yes"))
        return state

    def test_the_first_year_only_stores_the_share(self):
        s = self.year(self.state())
        self.assertEqual(s["te_dg_wc"], 50.0)
        self.assertAlmostEqual(s["te_dg_wc_sown"], 0.2)

    def test_half_a_point_a_point_capped_at_ten(self):
        # last year's share, this year's state-owned levels of 100 -> the jump
        for sown, ctry, jump in ((0.2, 32.0, -6.0),    # nationalised 12 points
                                 (0.2, 30.0, -5.0),    # exactly 10 points: it counts
                                 (0.2, 29.0, 0.0),     # 9 points: drift, no shock
                                 (0.2, 60.0, -10.0),   # 40 points: the cap
                                 (0.5, 20.0, 10.0),    # privatised 30 points: +15, capped
                                 (0.34, 20.0, 7.0)):   # privatised 14 points
            with self.subTest(sown=sown, ctry=ctry):
                s = self.year(self.state(priv=80.0 - ctry, ctry=ctry, sown=sown))
                self.assertAlmostEqual(s["te_dg_wc"], 50.0 + jump)
                self.assertAlmostEqual(s["te_dg_wc_sown"], ctry / 100.0)

    def test_the_score_stays_in_range(self):
        s = self.year(self.state(wc=96.0, ctry=0.0, priv=80.0, sown=0.5))
        self.assertEqual(s["te_dg_wc"], 100.0)
        s = self.year(self.state(wc=4.0, ctry=60.0, priv=20.0, sown=0.1))
        self.assertEqual(s["te_dg_wc"], 0.0)

    def test_no_shock_when_the_people_moved_a_quarter(self):
        for pop, prev, shocked in ((1.26e6, 1e6, False), (0.74e6, 1e6, False), (1.25e6, 1e6, True),
                                   (0.75e6, 1e6, True)):
            with self.subTest(pop=pop):
                s = self.year(self.state(ctry=40.0, priv=40.0, sown=0.2, pop=pop, prev=prev))
                self.assertEqual(s["te_dg_wc"], 40.0 if shocked else 50.0)
                self.assertAlmostEqual(s["te_dg_wc_sown"], 0.4, msg="the share is stored either way")

    def test_no_shock_without_last_years_people(self):
        s = self.state(ctry=40.0, priv=40.0, sown=0.2)
        del s["te_dg_walk_pop_prev"]
        self.assertEqual(self.year(s)["te_dg_wc"], 50.0)

    def test_under_twenty_capital_levels_no_shock_and_no_share(self):
        s = self.year(self.state(priv=5.0, self_=4.0, ctry=10.0, sown=0.0))   # 19 levels, 53% state-owned
        self.assertEqual(s["te_dg_wc"], 50.0)
        self.assertNotIn("te_dg_wc_sown", s)
        s = self.year(self.state(priv=5.0, self_=5.0, ctry=10.0, sown=0.0))   # 20 levels: in
        self.assertEqual(s["te_dg_wc"], 40.0)

    def test_a_state_the_walk_has_not_reached_is_left_alone(self):
        s = {"te_dg_wc": 50.0}
        self.year(s)
        self.assertEqual(s, {"te_dg_wc": 50.0, "te_dg_wc_target": 50.0})

    def test_the_shock_adds_to_the_drift(self):
        s = self.year(self.state(ctry=40.0, priv=40.0, sown=0.2), target=60.0)
        self.assertAlmostEqual(s["te_dg_wc"], 50.0 + 0.3 - 10.0)

    def test_a_change_of_owner_clears_the_share(self):
        s = self.state(sown=0.2)
        eng = _CountryEngine(states=[s], fixtures={})
        eng._in(s, _parse_script("te_demog_wc_owner_change = yes"))
        self.assertNotIn("te_dg_wc_sown", s)
        on_actions = _text(DEMOG_ON_ACTIONS)
        self.assertIn("te_demog_wc_owner_change_on_action", _block(on_actions, "on_state_owner_change"))
        self.assertIn("te_demog_wc_owner_change = yes", _block(on_actions, "te_demog_wc_owner_change_on_action"))

    def test_wired_into_the_state_year_before_the_clamp(self):
        body = _block(_text(WEALTH_EFFECTS), "te_demog_wc_state_yearly")
        self.assertLess(body.index("te_demog_wc_ownership_shock = yes"), body.index("clamp_variable"))
        self.assertIn("te_demog_wc_capital_levels", _block(_text(VALUES), "te_demog_wc_state_owned_share"),
                      "the ownership term's capital filter")


# -- W1: the financial boom -------------------------------------------------------------------------------------------

class TestBoomShock(unittest.TestCase):
    def month(self, states, country, running=True, boom=False, frenzy=False):
        eng = _CountryEngine(states=states, effects=APPLIED, fixtures=TARGET_FIXTURES,
                             triggers={"te_banking_cycle_running": running, "banking_cycle_is_boom": boom,
                                       "banking_cycle_is_frenzy": frenzy})
        eng.vars.update(country)
        eng.call("te_demog_wc_boom_check")
        return eng.vars

    def test_frenzy_raises_every_score_once_a_cycle(self):
        states = [_scored(50.0), _scored(98.0), {}]
        v = self.month(states, {}, frenzy=True)
        self.assertEqual([s.get("te_dg_wc") for s in states], [55.0, 100.0, None])
        self.assertEqual(v["te_dg_wc_boom"], 1)
        self.assertIn("applied", v, "the national figure and its modifiers follow")
        # the next months of the same frenzy: nothing
        v = self.month(states, v, frenzy=True)
        self.assertEqual(states[0]["te_dg_wc"], 55.0)
        # back to Boom: still the same cycle
        v = self.month(states, v, boom=True)
        self.assertIn("te_dg_wc_boom", v)
        v = self.month(states, v, frenzy=True)
        self.assertEqual(states[0]["te_dg_wc"], 55.0)
        # below Boom (a crash lowers the cycle to 40 or less): re-armed, and the next frenzy shocks again
        v = self.month(states, v)
        self.assertNotIn("te_dg_wc_boom", v)
        v = self.month(states, v, frenzy=True)
        self.assertEqual(states[0]["te_dg_wc"], 60.0)

    def test_nothing_without_a_running_cycle(self):
        states = [{"te_dg_wc": 50.0}]
        v = self.month(states, {}, running=False, frenzy=True)
        self.assertEqual(states[0]["te_dg_wc"], 50.0)
        self.assertNotIn("te_dg_wc_boom", v)

    def test_hooked_monthly_whatever_the_rule(self):
        body = _block(_text(DEMOG_ON_ACTIONS), "te_demog_country_monthly_on_action")
        self.assertIn("te_demog_wc_boom_check = yes", body)
        self.assertIn("te_demog_wc_shock = { AMOUNT = 5 }", _block(_text(WEALTH_EFFECTS), "te_demog_wc_boom_check"))


# -- W3: land reform --------------------------------------------------------------------------------------------------

class TestLandReform(unittest.TestCase):
    NATIONAL = {"te_demog_wc_national": "set_variable = { name = refreshed value = 1 }"}

    def month(self, states, last, now):
        eng = _CountryEngine(states=states, effects=self.NATIONAL, fixtures={"te_demog_wc_land_code": float(now)})
        if last is not None:
            eng.vars["te_dg_wc_land"] = float(last)
        eng.call("te_demog_wc_land_reform_check")
        return eng.vars

    def test_reform_from_serfdom_or_tenancy(self):
        # codes: 1 Serfdom, 2 Tenant Farmers, 3 Commercialized Agriculture, 4 Peasant Proprietorship, 5 Collectivized
        for last, now, reform in ((1, 4, True), (1, 5, True), (2, 4, True), (2, 5, True), (3, 4, False),
                                  (3, 5, False), (1, 3, False), (2, 1, False), (4, 5, False), (5, 4, False),
                                  (None, 4, False), (4, 4, False)):
            with self.subTest(last=last, now=now):
                states = [{"te_dg_wc": 60.0, "te_dg_agr_share": 0.7}, {"te_dg_wc": 60.0, "te_dg_agr_share": 0.1},
                          {"te_dg_wc": 60.0}, {"te_dg_agr_share": 0.9}]
                v = self.month(states, last, now)
                want = [53.0, 59.0] if reform else [60.0, 60.0]
                self.assertAlmostEqual(states[0]["te_dg_wc"], want[0])
                self.assertAlmostEqual(states[1]["te_dg_wc"], want[1])
                self.assertEqual(states[2]["te_dg_wc"], 60.0, "no agrarian share: left alone")
                self.assertNotIn("te_dg_wc", states[3], "no score: none made")
                self.assertEqual("refreshed" in v, reform)
                self.assertEqual(v["te_dg_wc_land"], float(now), "this month's law is kept for the next")

    def test_clamped(self):
        states = [{"te_dg_wc": 4.0, "te_dg_agr_share": 0.9}]
        self.month(states, 1, 5)
        self.assertEqual(states[0]["te_dg_wc"], 0.0)

    def test_the_codes_follow_the_parents(self):
        body = _block(_text(VALUES), "te_demog_wc_land_code")
        for code, law in ((1, "law_serfdom"), (2, "law_tenant_farmers"), (3, "law_commercialized_agriculture"),
                          (4, "law_peasant_proprietorship"), (5, "law_collectivized_agriculture")):
            self.assertRegex(body, rf"has_law_or_variant = law_type:{law} \}}\s*value = {code}\b")
        self.assertNotIn("has_law ", body, "variants take their parent's role through has_law_or_variant")

    def test_hooked_monthly(self):
        self.assertIn("te_demog_wc_land_reform_check = yes",
                      _block(_text(DEMOG_ON_ACTIONS), "te_demog_country_monthly_on_action"))


# -- S1: r > g --------------------------------------------------------------------------------------------------------

class TestReturnOnCapital(unittest.TestCase):
    def year(self, country, gdp, running=True, truncate=False):
        eng = _CountryEngine(fixtures={"te_mon_gdp_current": float(gdp)},
                             triggers={"te_banking_cycle_running": running}, truncate=truncate)
        eng.vars.update(country)
        eng.call("te_demog_wc_growth_update")
        return eng.vars

    def test_growth_averages_over_about_five_years(self):
        v = self.year({"te_policy_rate": 4.0}, 1000.0)
        self.assertEqual(v["te_dg_wc_gdp"], 1000.0)
        self.assertNotIn("te_dg_wc_g", v, "no growth before a second year")
        self.assertNotIn("te_dg_wc_rg", v)
        v = self.year(v, 1030.0)
        self.assertAlmostEqual(v["te_dg_wc_g"], 3.0)
        self.assertAlmostEqual(v["te_dg_wc_rg"], 2.0, msg="2 x (4 - 3)")
        v = self.year(v, 1030.0 * 1.08)
        self.assertAlmostEqual(v["te_dg_wc_g"], 3.0 + 0.2 * (8.0 - 3.0))
        self.assertAlmostEqual(v["te_dg_wc_rg"], 0.0)

    def test_a_years_growth_counts_ten_at_most(self):
        v = self.year({"te_dg_wc_gdp": 1000.0, "te_dg_wc_g": 2.0, "te_policy_rate": 4.0}, 1500.0)
        self.assertAlmostEqual(v["te_dg_wc_g"], 2.0 + 0.2 * 8.0, msg="a conquest's +50% counts +10")
        v = self.year({"te_dg_wc_gdp": 1000.0, "te_dg_wc_g": 2.0, "te_policy_rate": 4.0}, 500.0)
        self.assertAlmostEqual(v["te_dg_wc_g"], 2.0 - 0.2 * 12.0)

    def test_the_real_rate_and_the_cap(self):
        for rate, inflation, g, term in ((4.0, None, 1.0, 5.0), (4.0, 0.5, 1.0, 5.0), (5.0, 3.0, 1.0, 2.0),
                                         (10.0, 22.0, 3.0, -5.0), (3.0, 0.0, 4.0, -2.0)):
            with self.subTest(rate=rate, inflation=inflation):
                country = {"te_dg_wc_gdp": 1000.0, "te_dg_wc_g": g, "te_policy_rate": rate}
                if inflation is not None:
                    country["te_inflation"] = inflation
                v = self.year(country, 1000.0 * (1 + g / 100))
                self.assertAlmostEqual(v["te_dg_wc_r"], rate - (inflation or 0.0))
                self.assertAlmostEqual(v["te_dg_wc_rg"], term)

    def test_zero_until_the_cycle_runs(self):
        v = self.year({"te_dg_wc_gdp": 1000.0, "te_dg_wc_g": 2.0, "te_policy_rate": 4.0, "te_dg_wc_rg": 3.0}, 1020.0,
                      running=False)
        self.assertNotIn("te_dg_wc_rg", v)
        self.assertAlmostEqual(v["te_dg_wc_g"], 2.0, msg="the average is kept warm")
        self.assertAlmostEqual(v["te_dg_wc_r"], 4.0)
        eng = _CountryEngine(fixtures={})
        self.assertEqual(eng.value("te_demog_wc_rg_term"), 0.0)
        eng.vars["te_dg_wc_rg"] = -3.5
        self.assertEqual(eng.value("te_demog_wc_rg_term"), -3.5)

    def test_a_late_game_gdp_fits_the_fixed_point(self):
        v = self.year({"te_dg_wc_gdp": 7.0e11, "te_dg_wc_g": 2.0, "te_policy_rate": 4.0}, 7.21e11, truncate=True)
        self.assertAlmostEqual(v["te_dg_wc_g"], 2.0 + 0.2 * (3.0 - 2.0), places=4)

    def test_the_target_takes_the_seventh_term(self):
        state = {"te_dg_lv_priv": 30.0, "te_dg_lv_self": 10.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": 0.5}
        for rg, want in ((0.0, 89.0), (5.0, 94.0), (-5.0, 84.0)):
            eng = _CountryEngine(states=[state], fixtures={"te_inh_law_amendment_target": 80.0,
                                                           "te_demog_wc_land_term": 6.0, "te_demog_wc_tax_term": -5.0,
                                                           "te_demog_wc_econ_term": 0.0})
            if rg:
                eng.vars["te_dg_wc_rg"] = rg
            self.assertAlmostEqual(eng.value_in(state, "te_demog_wc_target"), want)

    def test_the_national_refresh_stores_the_bar_and_the_seven_add_up(self):
        a = _scored(60.0)
        eng = _CountryEngine(states=[a], effects=APPLIED, fixtures=TARGET_FIXTURES)
        eng.vars["te_dg_wc_rg"] = 3.0
        eng.call("te_demog_wc_national")
        v = eng.vars
        self.assertEqual(v["te_dg_wc_t_rg"], 3.0)
        bars = sum(v[f"te_dg_wc_t_{t}"] for t in ("law", "land", "own", "ineq", "tax", "econ", "rg"))
        self.assertAlmostEqual(v["te_dg_wc_target"], 50 + bars)

    def test_hooked_before_the_yearly_refresh(self):
        body = _block(_text(DEMOG_ON_ACTIONS), "te_demog_country_yearly_on_action")
        self.assertLess(body.index("te_demog_wc_growth_update = yes"), body.index("te_demog_country_yearly = yes"))
        self.assertIn("te_demog_wc_national = yes", _block(_text(EFFECTS), "te_demog_country_yearly"))

    def test_both_panels_show_the_term(self):
        widgets = _text(WIDGETS)
        self.assertIn("GetPlayer.MakeScope.ScriptValue('te_demog_wc_rg_term')", widgets)
        self.assertIn("State.GetOwner.MakeScope.ScriptValue('te_demog_wc_rg_term')", widgets)
        keys = _loc_keys()
        for key in ("te_demog_wc_t_rg", "te_demog_wc_t_rg_tt", "te_demog_st_wc_t_rg_tt"):
            self.assertIn(key, keys)


# -- S3: the Inequality effect ----------------------------------------------------------------------------------------

class TestInequality(unittest.TestCase):
    def refresh(self, gini, full=True, had=None):
        eng = _CountryEngine(fixtures={}, triggers={"te_demog_effects_run": full}, truncate=True)
        if gini is not None:
            eng.vars["te_dg_gini"] = gini
        if had is not None:
            eng.modifiers["te_demog_census_inequality"] = had
            eng.vars["te_dg_ineq"] = had
        eng.call("te_demog_inequality_refresh")
        return eng

    def test_from_045_to_the_cap_at_065(self):
        # at or under 0.452 the multiplier is 0.01 or less, and no modifier is applied
        for gini, mult in ((0.30, None), (0.45, None), (0.452, None), (0.50, 0.25), (0.55, 0.5), (0.65, 1.0),
                           (0.80, 1.0)):
            with self.subTest(gini=gini):
                eng = self.refresh(gini, had=0.4)
                got = eng.modifiers.get("te_demog_census_inequality")
                if mult is None:
                    self.assertIsNone(got)
                else:
                    self.assertAlmostEqual(got, mult, places=5)
                    self.assertAlmostEqual(eng.vars["te_dg_ineq"], mult, places=5)

    def test_outside_full_it_goes(self):
        eng = self.refresh(0.7, full=False, had=0.4)
        self.assertEqual(eng.modifiers, {})
        self.assertNotIn("te_dg_ineq", eng.vars)
        self.assertEqual(self.refresh(None, had=0.4).modifiers, {}, "no Gini yet: nothing")

    def test_one_refresh_site_on_the_state_pulse(self):
        sites = [p.name for p in (ROOT / "common").rglob("*.txt")
                 if "add_modifier = { name = te_demog_census_inequality" in p.read_text(encoding="utf-8-sig")]
        self.assertEqual(sites, ["te_demog_wealth_effects.txt"])
        self.assertIn("te_demog_inequality_refresh = yes", _block(_text(EFFECTS), "te_demog_state_yearly"))

    def test_the_modifier(self):
        body = _block(_text(INEQ_MODIFIERS), "te_demog_census_inequality")
        self.assertIn("state_radicals_from_political_movements_mult = 0.1", body)
        self.assertIn("te_demog_census_inequality", _loc_keys())
        self.assertIn("te_demog_census_inequality_desc", _loc_keys())
        self.assertIn('"te_demog_census_*": "states"', _text(NATION_TAB), "the Nation tab's family places it")


if __name__ == "__main__":
    unittest.main()
