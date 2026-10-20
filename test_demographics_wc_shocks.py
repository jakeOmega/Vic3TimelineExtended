"""Wealth Concentration's remaining shocks, the r > g term and the Inequality effect (owner, 2026-10-19;
docs/superpowers/specs/2026-10-08-demographics-design.md §4.2, §7).

The shocks and r > g run whatever the Demographics rule (Wealth Concentration is the Inheritance system's, #822); the
Inequality effect runs under Full only. The script runs through test_demographics_registry's interpreter."""

import math
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from test_demographics_registry import (  # noqa: E402  (helpers and paths only: no TestCase)
    APPLIED, DEMOG_ON_ACTIONS, EFFECTS, INH_EFFECTS, VALUES, WEALTH_EFFECTS, _block, _CountryEngine, _find,
    _parse_script, _raw_blocks, _text)

INEQ_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_inequality_modifiers.txt"
WIDGETS = ROOT / "gui" / "te_demographics_widgets.gui"
NATION_TAB = ROOT / "scripts" / "generators" / "gen_nation_tab.py"
MISC_LOC = ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml"
MARKET_TRIGGERS = ROOT / "common" / "scripted_triggers" / "market_triggers.txt"
TERRITORY_VALUES = ROOT / "common" / "script_values" / "te_demog_territory_values.txt"
INFLATION_EVENTS = ROOT / "events" / "te_inflation_events.txt"
EVENTS_LOC = ROOT / "localization" / "english" / "te_events_l_english.yml"
CONCEPTS_LOC = ROOT / "localization" / "english" / "te_concepts_l_english.yml"
TARGET_FIXTURES = {"te_inh_law_amendment_target": 75.0, "te_demog_wc_land_term": 4.0,
                   "te_demog_wc_tax_term": -5.0, "te_demog_wc_econ_term": 5.0}


def _scored(wc):
    """A state te_demog_wc_national can weigh: a score, its walk's levels, people and Gini."""
    return {"te_dg_wc": float(wc), "te_dg_wc_target": 50.0, "te_dg_lv_own": 10.0, "te_dg_lv_self": 0.0,
            "te_dg_lv_ctry": 0.0, "te_dg_lv_priv": 30.0, "te_dg_bureaucrats": 0.0, "te_dg_walk_pop": 1e6,
            "te_dg_gini": 0.5}


def _loc_keys():
    return set(re.findall(r"(?m)^ (\w+):\d* ", _text(MISC_LOC)))


def _loc():
    return dict(re.findall(r'(?m)^ (\w+):\d* "(.*)"$', _text(MISC_LOC)))


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

    def test_a_move_of_people_skips_nothing(self):
        """Capital levels don't move with people, so a migration jump makes no share change spurious (owner,
        2026-10-20): the census's old re-seed rule (a move of more than a quarter in the year) is gone here too."""
        for pop in (5.74e6, 1.26e6, 0.74e6, 0.3e6, 1e6):
            with self.subTest(pop=pop):
                s = self.year(self.state(ctry=40.0, priv=40.0, sown=0.2, pop=pop, prev=1e6))
                self.assertEqual(s["te_dg_wc"], 40.0)
                self.assertAlmostEqual(s["te_dg_wc_sown"], 0.4)
        self.assertNotIn("te_dg_walk_pop", _block(_text(WEALTH_EFFECTS), "te_demog_wc_ownership_shock"))

    def test_last_years_people_are_not_needed(self):
        s = self.state(ctry=40.0, priv=40.0, sown=0.2)
        del s["te_dg_walk_pop_prev"]
        self.assertEqual(self.year(s)["te_dg_wc"], 40.0)

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

    def test_a_crash_value_re_arms_it(self):
        """The banking triggers themselves on the cycle's value: Frenzy from 88, Boom from 75. A crash lowers the cycle
        to 40 or less once its option lands (banking_crash_lower_cycle_to)."""
        states = [_scored(50.0)]
        country = {}
        for value, score, marked in ((90.0, 55.0, True),    # Frenzy: +5
                                     (95.0, 55.0, True),    # still Frenzy: nothing
                                     (80.0, 55.0, True),    # Boom: still this cycle
                                     (90.0, 55.0, True),    # back to Frenzy from Boom: nothing
                                     (40.0, 55.0, False),   # the crash's ceiling: re-armed
                                     (74.0, 55.0, False),
                                     (88.0, 60.0, True)):   # the next Frenzy: +5
            eng = _CountryEngine(states=states, effects=APPLIED, fixtures=TARGET_FIXTURES,
                                 triggers={"te_banking_cycle_running": True})
            eng.triggers.update(_raw_blocks([MARKET_TRIGGERS]))
            eng.vars.update(country)
            eng.vars["finance_cycle_value"] = value
            eng.call("te_demog_wc_boom_check")
            country = eng.vars
            with self.subTest(value=value):
                self.assertEqual(states[0]["te_dg_wc"], score)
                self.assertEqual("te_dg_wc_boom" in country, marked)

    def test_nothing_without_a_running_cycle(self):
        states = [{"te_dg_wc": 50.0}]
        v = self.month(states, {}, running=False, frenzy=True)
        self.assertEqual(states[0]["te_dg_wc"], 50.0)
        self.assertNotIn("te_dg_wc_boom", v)

    def test_hooked_monthly_whatever_the_rule(self):
        body = _block(_text(DEMOG_ON_ACTIONS), "te_demog_country_monthly_on_action")
        self.assertIn("te_demog_wc_boom_check = yes", body)
        self.assertIn("te_demog_wc_shock = { AMOUNT = 5 }", _block(_text(WEALTH_EFFECTS), "te_demog_wc_boom_check"))


# -- Money: the hyperinflation crisis (owner, 2026-10-20) --------------------------------------------------------------

class TestHyperinflationShock(unittest.TestCase):
    """§4.2's Money bullet: bond fortunes vanish. -5 to every state when te_inflation.1 fires (its immediate, so riding
    it out takes it again each time the crisis returns after its cooldown) and -5 more on a currency reform, whatever
    the Demographics rule."""

    @staticmethod
    def event():
        return _parse_script(_block(_text(INFLATION_EVENTS), "te_inflation.1"))

    def options(self):
        return [v for k, _, v in self.event() if k == "option"]

    @staticmethod
    def run_body(body, states):
        eng = _CountryEngine(states=states, effects=APPLIED, fixtures=TARGET_FIXTURES)
        eng.run(body)
        return eng.vars

    def test_minus_five_when_the_crisis_fires(self):
        states = [_scored(50.0), _scored(3.0), {}]
        v = self.run_body(_find(self.event(), "immediate"), states)
        self.assertEqual([s.get("te_dg_wc") for s in states], [45.0, 0.0, None])
        self.assertIn("applied", v, "the national figure and its modifiers follow")

    def test_five_more_on_a_currency_reform_only(self):
        reform, dollarise, ride = self.options()
        self.assertEqual([_find(o, "name") for o in (reform, dollarise, ride)],
                         ["te_inflation.1.a", "te_inflation.1.b", "te_inflation.1.c"])
        blocks = [v for k, _, v in reform if k == "custom_tooltip" and isinstance(v, list)]
        self.assertEqual(len(blocks), 1, "the reform's shock sits in a tooltip that says so")
        self.assertEqual(_find(blocks[0], "text"), "te_inflation.1.a.wc.tt")
        states = [_scored(45.0)]
        self.run_body([item for item in blocks[0] if item[0] != "text"], states)
        self.assertEqual(states[0]["te_dg_wc"], 40.0)
        for option in (dollarise, ride):
            self.assertNotIn("te_demog_wc_shock", repr(option))

    def test_the_crisis_is_the_one_site(self):
        sites = [p.name for p in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").rglob("*.txt"))
                 if "te_inflation" in p.name or "te_monetary" in p.name
                 if "te_demog_wc_shock" in p.read_text(encoding="utf-8-sig")]
        self.assertEqual(sites, ["te_inflation_events.txt"])
        body = _block(_text(INFLATION_EVENTS), "te_inflation.1")
        self.assertEqual(body.count("te_demog_wc_shock = { AMOUNT = -5 }"), 2)
        self.assertNotIn("te_demog_effects_run", body, "every Demographics rule")

    def test_each_options_tooltip_says_so(self):
        loc = dict(re.findall(r'(?m)^ ([\w.]+):\d* "(.*)"$', _text(EVENTS_LOC) + "\n" + _text(MISC_LOC)))
        self.assertIn("[concept_inheritance_concentration] fell by #v 5#! when the crisis broke",
                      loc["te_inflation_wc_fired"])
        for key in ("te_inflation.1.a.wc.tt", "te_inflation.1.b.tt", "te_inflation.1.c.tt"):
            self.assertIn("$te_inflation_wc_fired$", loc[key], key)
        self.assertIn("#v 5#! more", loc["te_inflation.1.a.wc.tt"])
        self.assertIn("#v 5#! again", loc["te_inflation.1.c.tt"])
        for path, key in ((CONCEPTS_LOC, "concept_inheritance_concentration_desc"), (MISC_LOC, "te_demog_how_wc")):
            self.assertIn("a hyperinflation crisis", dict(re.findall(r'(?m)^ (\w+):\d* "(.*)"$', _text(path)))[key])


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

    def test_a_won_revolution_takes_the_old_governments_law(self):
        """The rebels store their own law through the war and a winner's variables take precedence, so the repair gives
        the winner the loser's role; the next month compares it with the rebels' law."""
        repair = _block(_text(INH_EFFECTS), "inh_repair_after_civil_war")
        call = repair.index("te_demog_wc_civil_war_inherit = yes")
        guard = repair.rfind("if = {", 0, call)
        self.assertIn("var:te_cw_rebels_won = 1", repair[guard:call])
        self.assertLess(call, repair.index("te_demog_wc_national = yes"))
        # the old government's Serfdom against the rebels' Peasant Proprietorship
        states = [{"te_dg_wc": 60.0, "te_dg_agr_share": 0.5}]
        self.month(states, 1, 4)
        self.assertEqual(states[0]["te_dg_wc"], 55.0)

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

def _lp(r):
    """A year's growth in log points: 100 x ln of its GDP ratio (te_demog_wc_log_growth)."""
    return 100.0 * math.log(r)


class TestReturnOnCapital(unittest.TestCase):
    def year(self, country, gdp, running=True, truncate=False, states=5, engine=False):
        """te_demog_wc_growth_update at the yearly pulse, the country holding `states` states (te_demog_wc_state_count).
        engine=True returns the engine (its locals hold the year's sample, te_dg_wc_g_year, when one was taken)."""
        eng = _CountryEngine(fixtures={"te_mon_gdp_current": float(gdp), "te_demog_wc_state_count": float(states)},
                             triggers={"te_banking_cycle_running": running}, truncate=truncate)
        eng.vars.update(country)
        eng.call("te_demog_wc_growth_update")
        return eng if engine else eng.vars

    def test_growth_averages_over_about_five_years(self):
        v = self.year({"te_policy_rate": 4.0}, 1000.0)
        self.assertEqual(v["te_dg_wc_gdp"], 1000.0)
        self.assertNotIn("te_dg_wc_g", v, "no growth before a second year")
        self.assertNotIn("te_dg_wc_rg", v)
        v = self.year(v, 1030.0)
        g = _lp(1.03)
        self.assertAlmostEqual(v["te_dg_wc_g"], g, places=3)
        self.assertAlmostEqual(v["te_dg_wc_rg"], 2 * (4.0 - g), places=3)
        v = self.year(v, 1030.0 * 1.08)
        self.assertAlmostEqual(v["te_dg_wc_g"], g + 0.2 * (_lp(1.08) - g), places=3)

    def test_growth_is_in_log_points(self):
        """The average takes 100 x ln of each year's GDP ratio (owner, 2026-10-20), as it came, however large: a real
        boom past 10% counts in full, with no clamp."""
        for ratio in (1.5, 0.5, 1.05, 0.95, 2.0):
            with self.subTest(ratio=ratio):
                v = self.year({"te_dg_wc_gdp": 1000.0, "te_dg_wc_states": 5.0, "te_dg_wc_g": 2.0,
                               "te_policy_rate": 4.0}, 1000.0 * ratio)
                self.assertAlmostEqual(v["te_dg_wc_g"], 2.0 + 0.2 * (_lp(ratio) - 2.0), places=3)
        self.assertNotIn("min = -10", _block(_text(WEALTH_EFFECTS), "te_demog_wc_growth_update"))

    def test_a_five_percent_year_reads_4_88(self):
        for last in (1000.0, 7.0e11):
            with self.subTest(last=last):
                eng = self.year({"te_dg_wc_gdp": last, "te_dg_wc_states": 5.0}, last * 1.05, truncate=True,
                                engine=True)
                self.assertEqual(round(eng.locals["te_dg_wc_g_year"], 2), 4.88)
                self.assertEqual(round(eng.vars["te_dg_wc_g"], 2), 4.88, "the first sample is the average")

    def test_a_fall_and_its_recovery_cancel(self):
        """-50% and then +100% back to the same GDP: the two samples net about 0 (in percent they were -50 and +100,
        which averaged up)."""
        eng = self.year({"te_dg_wc_gdp": 1000.0, "te_dg_wc_states": 5.0}, 500.0, truncate=True, engine=True)
        fall = eng.locals["te_dg_wc_g_year"]
        eng = self.year(eng.vars, 1000.0, truncate=True, engine=True)
        rise = eng.locals["te_dg_wc_g_year"]
        self.assertAlmostEqual(fall, -_lp(2.0), delta=0.001)
        self.assertAlmostEqual(fall + rise, 0.0, delta=0.001)

    def test_the_series_against_the_logarithm(self):
        """te_demog_wc_log_growth (ln r = 2 atanh z to z^9, z = (r - 1) / (r + 1)) under the fixed point against
        math.log, for r from 0.1 to 10 and GDP from 1,000 to the late game's 7 x 10^11: within 0.0002 log points from
        0.5 to 2, 0.25% from 0.2 to 5, 2.5% from 0.1 to 10, and rising with r throughout."""
        eng = _CountryEngine(fixtures={}, truncate=True)
        for last in (1000.0, 1.234e6, 7.0e11):
            prev = None
            for i in range(0, 201):
                r = 0.1 * 10 ** (i / 100)
                now = round(last * r, 5)
                eng.vars = eng.root_vars = {"te_dg_wc_gdp": last}
                eng.locals = {"te_dg_wc_gdp_now": now}
                eng.call("te_demog_wc_log_growth")
                got, want = eng.locals["te_dg_wc_g_year"], _lp(now / last)
                if 0.5 <= r <= 2.0:
                    self.assertAlmostEqual(got, want, delta=0.0002, msg=(last, r))
                elif 0.2 <= r <= 5.0:
                    self.assertLessEqual(abs(got - want), 0.0025 * abs(want), (last, r))
                else:
                    self.assertLessEqual(abs(got - want), 0.025 * abs(want), (last, r))
                if prev is not None:
                    self.assertGreater(got, prev, (last, r))
                prev = got

    def test_a_change_of_territory_samples_unless_the_gdp_jumped(self):
        """In a year the country gained or lost states the sample is taken unless the GDP moved more than a tenth
        (the ratio under 0.9 or over 1.1, owner 2026-10-20): then the jump is the territory's, so the year takes no
        sample and the GDP is re-based. A colony's year counts; a conquest's jump doesn't."""
        for states in (6, 4):
            for ratio, sampled in ((1.05, True), (0.95, True), (1.1, True), (0.9, True), (1.3, False),
                                   (0.85, False), (1.11, False)):
                with self.subTest(states=states, ratio=ratio):
                    start = {"te_dg_wc_gdp": 1000.0, "te_dg_wc_states": 5.0, "te_dg_wc_g": 2.0,
                             "te_policy_rate": 4.0}
                    v = self.year(dict(start), 1000.0 * ratio, states=states)
                    want = 2.0 + 0.2 * (_lp(ratio) - 2.0) if sampled else 2.0
                    self.assertAlmostEqual(v["te_dg_wc_g"], want, places=3)
                    self.assertAlmostEqual(v["te_dg_wc_gdp"], 1000.0 * ratio, msg="re-based either way")
                    self.assertEqual(v["te_dg_wc_states"], float(states))
                    self.assertAlmostEqual(v["te_dg_wc_rg"], max(-5.0, min(5.0, 2 * (4.0 - v["te_dg_wc_g"]))), places=5)
        # the year after a skipped jump: growth on the new territory
        v = self.year({"te_dg_wc_gdp": 1000.0, "te_dg_wc_states": 5.0, "te_dg_wc_g": 2.0, "te_policy_rate": 4.0},
                      1500.0, states=6)
        v = self.year(v, 1500.0 * 1.07, states=6)
        self.assertAlmostEqual(v["te_dg_wc_g"], 2.0 + 0.2 * (_lp(1.07) - 2.0), places=3)

    def test_an_old_saves_first_year_reads_as_a_change(self):
        """A save from before the state count holds a GDP and no count: that year is treated as a change of territory,
        so it samples unless the GDP jumped, and stores both."""
        v = self.year({"te_dg_wc_gdp": 1000.0, "te_dg_wc_g": 2.0, "te_policy_rate": 4.0}, 1030.0)
        self.assertAlmostEqual(v["te_dg_wc_g"], 2.0 + 0.2 * (_lp(1.03) - 2.0), places=3)
        self.assertEqual((v["te_dg_wc_gdp"], v["te_dg_wc_states"]), (1030.0, 5.0))
        v = self.year({"te_dg_wc_gdp": 1000.0, "te_dg_wc_g": 2.0, "te_policy_rate": 4.0}, 1300.0)
        self.assertAlmostEqual(v["te_dg_wc_g"], 2.0)

    def test_a_gdp_of_zero_or_below_takes_no_sample(self):
        """A GDP of 0 or below, this year's or last, has no meaningful ratio (its sample would be about -357): no
        sample, and the GDP is re-based, on the same territory too."""
        for last, now in ((1000.0, 0.0), (1000.0, -5.0), (0.0, 1000.0), (-5.0, 1000.0)):
            with self.subTest(last=last, now=now):
                v = self.year({"te_dg_wc_gdp": last, "te_dg_wc_states": 5.0, "te_dg_wc_g": 2.0,
                               "te_policy_rate": 4.0}, now)
                self.assertEqual(v["te_dg_wc_g"], 2.0)
                self.assertEqual(v["te_dg_wc_gdp"], now)

    def test_the_territory_guard_never_shares_a_not_with_its_read(self):
        """scripting_best_practices.md: a multi-child NOT reads every child, so the stored count is read only inside
        an if on has_variable (the local te_dg_wc_same)."""
        body = re.sub(r"\s+", " ", re.sub(r"#[^\n]*", "", _block(_text(WEALTH_EFFECTS), "te_demog_wc_growth_update")))
        self.assertNotIn("NOT = {", body)
        self.assertIn("if = { limit = { has_variable = te_dg_wc_states } if = { limit = { var:te_dg_wc_states = "
                      "local_var:te_dg_wc_states_now }", body)

    def test_the_hover_shows_a_compound_annual_rate(self):
        """te_demog_wc_g_shown = 100 x (e^(g/100) - 1) for the hovers, by series, under the fixed point: within 0.003
        points of math.exp for |g| up to 100 and 0.1% up to 230. A halving's average reads -50 and a doubling's
        +100; 0 with no average."""
        eng = _CountryEngine(fixtures={}, truncate=True)
        for i in range(-460, 461):
            g = i / 2
            eng.vars = eng.root_vars = {"te_dg_wc_g": g}
            got, want = eng.value("te_demog_wc_g_shown"), 100.0 * (math.exp(g / 100) - 1)
            if abs(g) <= 100:
                self.assertAlmostEqual(got, want, delta=0.003, msg=g)
            else:
                self.assertLessEqual(abs(got - want), 0.001 * abs(want), g)
        for g, shown in ((_lp(0.5), -50.0), (_lp(2.0), 100.0), (_lp(1.05), 5.0)):
            eng.vars = eng.root_vars = {"te_dg_wc_g": g}
            self.assertAlmostEqual(eng.value("te_demog_wc_g_shown"), shown, delta=0.001)
        eng.vars = eng.root_vars = {}
        self.assertEqual(eng.value("te_demog_wc_g_shown"), 0.0)

    def test_the_state_count_iterates_the_countrys_states(self):
        body = re.sub(r"\s+", " ", _block(_text(TERRITORY_VALUES), "te_demog_wc_state_count")).strip()
        self.assertEqual(body, "value = 0 every_scope_state = { add = 1 }")

    def test_the_real_rate_and_the_cap(self):
        for rate, inflation, g, term in ((4.0, None, 1.0, 5.0), (4.0, 0.5, 1.0, 5.0), (5.0, 3.0, 1.0, 2.0),
                                         (10.0, 22.0, 3.0, -5.0), (3.0, 0.0, 4.0, -2.0)):
            with self.subTest(rate=rate, inflation=inflation):
                country = {"te_dg_wc_gdp": 1000.0, "te_dg_wc_states": 5.0, "te_dg_wc_g": g, "te_policy_rate": rate}
                if inflation is not None:
                    country["te_inflation"] = inflation
                # a year of g log points, so the average stays at g
                v = self.year(country, 1000.0 * math.exp(g / 100))
                self.assertAlmostEqual(v["te_dg_wc_r"], rate - (inflation or 0.0))
                self.assertAlmostEqual(v["te_dg_wc_rg"], term, places=3)

    def test_zero_until_the_cycle_runs(self):
        v = self.year({"te_dg_wc_gdp": 1000.0, "te_dg_wc_states": 5.0, "te_dg_wc_g": 2.0, "te_policy_rate": 4.0,
                       "te_dg_wc_rg": 3.0}, 1040.0, running=False)
        self.assertNotIn("te_dg_wc_rg", v)
        self.assertAlmostEqual(v["te_dg_wc_g"], 2.0 + 0.2 * (_lp(1.04) - 2.0), places=3, msg="the average is kept warm")
        self.assertAlmostEqual(v["te_dg_wc_r"], 4.0)
        eng = _CountryEngine(fixtures={})
        self.assertEqual(eng.value("te_demog_wc_rg_term"), 0.0)
        eng.vars["te_dg_wc_rg"] = -3.5
        self.assertEqual(eng.value("te_demog_wc_rg_term"), -3.5)

    def test_no_policy_rate_no_term(self):
        v = self.year({"te_dg_wc_gdp": 1000.0, "te_dg_wc_states": 5.0, "te_dg_wc_g": 2.0}, 1040.0)
        self.assertNotIn("te_dg_wc_r", v)
        self.assertNotIn("te_dg_wc_rg", v, "a running cycle with no rate yet adds nothing")
        self.assertAlmostEqual(v["te_dg_wc_g"], 2.0 + 0.2 * (_lp(1.04) - 2.0), places=3,
                               msg="the average still moves")

    def test_the_hover_gives_figures_only_while_the_term_is_in_force(self):
        eng = _CountryEngine(fixtures={})
        self.assertEqual(eng.value("te_demog_wc_rg_on"), 0.0)
        eng.vars["te_dg_wc_rg"] = 0.0
        self.assertEqual(eng.value("te_demog_wc_rg_on"), 1.0)
        loc = _loc()
        for key, scope, figures in (("te_demog_wc_t_rg_tt", "GetPlayer", "te_demog_wc_t_rg_figures"),
                                    ("te_demog_st_wc_t_rg_tt", "State.GetOwner", "te_demog_st_wc_t_rg_figures")):
            self.assertNotIn("te_dg_wc_r'", loc[key], "the figures sit in the named key")
            self.assertIn(f"{scope}.MakeScope.ScriptValue('te_demog_wc_rg_on')", loc[key])
            self.assertIn(f"'{figures}', 'te_demog_wc_t_rg_off'", loc[key])
            # the growth average as a compound annual rate (te_demog_wc_g_shown), not its log points
            self.assertIn(f"{scope}.MakeScope.ScriptValue('te_demog_wc_g_shown')|1]%", loc[figures])
            self.assertNotIn("te_dg_wc_g'", loc[figures])
        self.assertNotIn("[", loc["te_demog_wc_t_rg_off"].replace("[concept_banking_cycle]", ""))

    def test_a_won_revolution_continues_the_nations_growth(self):
        body = _block(_text(WEALTH_EFFECTS), "te_demog_wc_civil_war_inherit")
        for name in ("te_dg_wc_land", "te_dg_wc_gdp", "te_dg_wc_g", "te_dg_wc_states"):
            self.assertIn(f"set_variable = {{ name = {name} value = scope:te_cw_loser.var:{name} }}", body)
        # the GDP's state count goes with it: copied with the GDP, or removed when the loser held none (an old save)
        gdp = body.index("name = te_dg_wc_gdp value")
        self.assertLess(gdp, body.index("name = te_dg_wc_states value"))
        self.assertLess(body.index("name = te_dg_wc_states value"), body.index("remove_variable = te_dg_wc_states"))

    def test_a_late_game_gdp_fits_the_fixed_point(self):
        v = self.year({"te_dg_wc_gdp": 7.0e11, "te_dg_wc_states": 5.0, "te_dg_wc_g": 2.0, "te_policy_rate": 4.0},
                      7.21e11, truncate=True)
        self.assertAlmostEqual(v["te_dg_wc_g"], 2.0 + 0.2 * (_lp(1.03) - 2.0), places=4)

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

    def test_from_045_on_with_no_cap(self):
        """The same slope past 0.65 (owner, 2026-10-20: the cap at 1 went): +27.5% at a Gini of 1."""
        # at or under 0.452 the multiplier is 0.01 or less, and no modifier is applied
        for gini, mult in ((0.30, None), (0.45, None), (0.452, None), (0.50, 0.25), (0.55, 0.5), (0.65, 1.0),
                           (0.80, 1.75), (1.0, 2.75)):
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

    def test_the_help_and_the_state_hover_name_seven_terms(self):
        loc = _loc()
        self.assertIn("50 plus seven terms", loc["te_demog_how_wc"])
        for key in ("te_demog_how_wc", "te_demog_st_wc_tt"):
            self.assertIn("the return on capital against growth", loc[key], key)
        for shock in ("land reform", "banking frenzy", "state-owned share", "hyperinflation crisis"):
            self.assertIn(shock, loc["te_demog_how_wc"])

    def test_one_refresh_site_on_the_state_pulse(self):
        sites = [p.name for p in (ROOT / "common").rglob("*.txt")
                 if "add_modifier = { name = te_demog_census_inequality" in p.read_text(encoding="utf-8-sig")]
        self.assertEqual(sites, ["te_demog_wealth_effects.txt"])
        self.assertIn("te_demog_inequality_refresh = yes", _block(_text(EFFECTS), "te_demog_state_yearly"))

    def test_no_max_on_the_multiplier(self):
        body = _block(_text(WEALTH_EFFECTS), "te_demog_inequality_refresh")
        self.assertIn("value = { value = var:te_dg_gini subtract = 0.45 multiply = 5 min = 0 } }", body)
        self.assertNotIn("max =", body)
        self.assertNotIn("up to 10%", _loc()["te_demog_census_inequality_desc"])

    def test_the_modifier(self):
        body = _block(_text(INEQ_MODIFIERS), "te_demog_census_inequality")
        self.assertIn("state_radicals_from_political_movements_mult = 0.1", body)
        self.assertIn("te_demog_census_inequality", _loc_keys())
        self.assertIn("te_demog_census_inequality_desc", _loc_keys())
        self.assertIn('"te_demog_census_*": "states"', _text(NATION_TAB), "the Nation tab's family places it")


if __name__ == "__main__":
    unittest.main()
