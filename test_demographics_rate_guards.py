"""The census's guards (#1476, 2026-11-06).

The first 1.15 observer game reached 1923 with East Bengal at some 9e15 people. Sindh, at 1.2 billion and still in range,
showed the failure mode: crowding of 91 drove infection past every age's death cap, the life table collapsed, the model's
death rate turned negative, and the deaths term sat at its floor, so the engine killed nobody there. Three guards, each at
a bound no sane state of the 2020, 1940 and 1926 saves reached, and at the runaway tripwire's bound for the same sign:

1. Out of range, the census clears its terms (te_demog_census_out_of_range in te_demog_rates_refresh): its people's sum
   below 0 or over 500 million, life expectancy under 5, a model rate below 0, and since 2026-11-19 (owner) known kills
   of a third or more of its people in the step's window (25 warheads on Sankt-Peterburg in 1977 put its births term at
   the ceiling). The engine's own rates run, as under Display only. The census then seeds again in place of that step
   (TestTheKillsGuard).
2. Crowding's infection factor stops at a pull of 5 (te_demog_f_infection_crowding).
3. Births' term stops at +10 (te_demog_rate_ceiling).

These tests run the real script through the registry's interpreter and hold it to its Python twin
(demographics_model.census_out_of_range, rate_term's ceiling, cause_factors), and check that a guarded state still trips
the tripwire, whose figures date the onset.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
from test_demographics_registry import (  # noqa: E402  (helpers only: no TestCase)
    CONSOLE_EFFECTS, GENERATED_VALUES, RATE_EFFECTS, TRIGGERS, _block, _ConsoleEngine, _Engine, _text)
from test_demographics_runaway_check import SANE, SINDH  # noqa: E402
import test_demographics_registry as R  # noqa: E402  (TestRatesScript's pulse, by the module: no second collection)

CHECK = "te_debug_demog_runaway_selfcheck"
POP = 1_000_000.0
EB0, ED0 = 475.0 * POP, 430.0 * POP     # the walk's bare births and deaths, a month x 100,000
# the census's own figures at a sane step: Jiangxi's (test_demographics_runaway_check.SANE)
IN_RANGE = {"te_dg_walk_pop": POP, "te_dg_e0": 40.0}


def _refresh_engine(full=True, stepped=1.0, cbr=38.0, cdr=31.0, eb0=EB0, ed0=ED0, census=None, console=False,
                    pop=POP, kill_share=None):
    """A state at its census under Full, as TestRatesScript sets it up, with the census's own figures (`census`);
    kill_share: the census's local te_dg_kill_share (None: te_demog_state_census set none)."""
    families = {f"modifier:{name}": 0.0 for name in P.ENGINE_LINE_TYPES.values()}
    cls = _ConsoleEngine if console else _Engine
    eng = cls({"state_population": pop, "modifier:state_birth_rate_mult": 0.0, "modifier:state_mortality_mult": 0.0,
               **families}, triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": True})
    eng.locals.update(te_dg_w_eb0=eb0, te_dg_w_ed0=ed0, te_dg_w_ebr=0.0, te_dg_w_edr=0.0, te_dg_w_eb=eb0,
                      te_dg_w_ed=ed0, te_dg_w_eb0m=eb0, te_dg_w_ed0m=ed0, te_dg_w_sev=0.0, te_dg_w_sevd=0.0)
    eng.vars.update(te_dg_stepped=stepped, te_dg_cbr_model=cbr, te_dg_cdr_model=cdr)
    eng.vars.update(IN_RANGE if census is None else census)
    if kill_share is not None:
        eng.locals["te_dg_kill_share"] = kill_share
    return eng


def _terms_in_force(eng):
    """Last step's terms, as a state holds them going into this one."""
    eng.modifiers.update(te_demog_census_births_down=0.3, te_demog_census_deaths_down=1.0)
    eng.vars.update(te_dg_mb=-0.3, te_dg_md=-1.0, te_dg_tb_b=0.6, te_dg_tb_d=0.2, te_dg_os_b=0.0, te_dg_os_d=0.0,
                    te_dg_q_b=0.0, te_dg_q_d=0.0, te_dg_w=0.0, te_dg_rate_clamp_d=1.0, te_dg_rate_clamped=1.0,
                    te_dg_rep_b=0.0, te_dg_rep_d=0.0, te_dg_sr_b=400.0, te_dg_sr_d=10.0)


TERM_VARS = ("te_dg_mb", "te_dg_md", "te_dg_tb_b", "te_dg_tb_d", "te_dg_os_b", "te_dg_os_d", "te_dg_q_b", "te_dg_q_d",
             "te_dg_w", "te_dg_rate_clamp_d", "te_dg_rate_clamped", "te_dg_sr_b", "te_dg_sr_d")


class TestTheModelsTwin(unittest.TestCase):
    def test_the_bounds(self):
        """Each guard sits past the sane extremes of three saves (the largest state 128 million, life expectancy 26 or
        more, crowding 1.64 at most, a births term 4.05 at most) and at the tripwire's bound for the same sign."""
        self.assertEqual(P.RATE_GUARD_PEOPLE_MAX, 500_000_000)
        self.assertGreater(P.RATE_GUARD_PEOPLE_MAX, 3 * 128e6)
        # below the first sum that wraps at the script's fixed-point limit: a seed's people x 100,000
        self.assertLess(P.RATE_GUARD_PEOPLE_MAX * 100_000, 9.2e13)
        self.assertEqual(P.RATE_GUARD_E0_MIN, 5.0)
        self.assertEqual(P.CROWDING_INFECTION_PULL_MAX, 5.0)
        self.assertGreater(P.CROWDING_INFECTION_PULL_MAX, 1.64 * 3)
        self.assertEqual(P.RATE_BIRTHS_CEILING, 10.0)
        self.assertGreater(P.RATE_BIRTHS_CEILING, 4.05 * 2)
        # the fourth guard (owner, 2026-11-19): a third of the people killed in one step's window
        self.assertEqual(P.RATE_GUARD_KILLS_SHARE, 1 / 3)

    def test_out_of_range(self):
        for args, why in (((POP, 40.0, 38.0, 31.0), 0), ((-5.7e13, 0.5, 38.0, 31.0), 1), ((1.19e9, 0.5, 0.0, -473.6), 1),
                          ((5e8, 40.0, 38.0, 31.0), 0), ((5e8 + 1, 40.0, 38.0, 31.0), 1), ((POP, 4.99, 38.0, 31.0), 2),
                          ((POP, 5.0, 38.0, 31.0), 0), ((POP, 40.0, -0.1, 31.0), 3), ((POP, 40.0, 38.0, -0.1), 3),
                          ((POP, 0.5, 38.0, -473.6), 2), ((None, None, None, None), 0),
                          # the fourth guard: known kills over the people at the last count, a third or more, above 1 too
                          ((POP, 40.0, 38.0, 31.0, 0.34), 4), ((POP, 40.0, 38.0, 31.0, 1 / 3), 4),
                          ((POP, 40.0, 38.0, 31.0, 0.33), 0), ((POP, 40.0, 38.0, 31.0, 2.53), 4),
                          ((POP, 40.0, 38.0, 31.0, 0.0), 0), ((POP, 40.0, 38.0, 31.0, None), 0),
                          ((POP, 0.5, 38.0, 31.0, 0.9), 2), ((POP, 40.0, -0.1, 31.0, 0.9), 3),
                          ((None, None, None, None, 0.5), 4)):
            with self.subTest(args=args):
                self.assertEqual(M.census_out_of_range(*args), why)

    def test_the_kill_share(self):
        """Sankt-Peterburg's 1977 salvo against its 1976 count: about 3.7 million booked (#1917's fix) is 0.93 of its
        people, the 10 million booked before it 2.5; both past the bound. No kills noted, no share."""
        people_1976 = 3_995_846.0
        self.assertAlmostEqual(M.kill_share(3.7e6, people_1976), 0.926, places=3)
        self.assertAlmostEqual(M.kill_share(10e6, people_1976), 2.503, places=3)
        self.assertIsNone(M.kill_share(None, people_1976))
        self.assertEqual(M.kill_share(500.0, 0.0), 500.0, "the people at least 1")
        for kills in (3.7e6, 10e6):
            self.assertEqual(M.census_out_of_range(197_774.0, 40.0, 38.0, 31.0, M.kill_share(kills, people_1976)), 4)

    def test_the_births_ceiling(self):
        """No ceiling for a figure in range; a target computed from nonsense stops at +10."""
        m, clamped = M.rate_term(target=380.0, bare=100.0, ceiling=P.RATE_BIRTHS_CEILING)
        self.assertAlmostEqual(m, 2.8)
        self.assertFalse(clamped)
        m, clamped = M.rate_term(target=5000.0, bare=100.0, ceiling=P.RATE_BIRTHS_CEILING)
        self.assertEqual((m, clamped), (P.RATE_BIRTHS_CEILING, True))
        self.assertAlmostEqual(M.rate_term(target=5000.0, bare=100.0)[0], 49.0, msg="deaths keep no ceiling")

    def test_crowding_stops_at_its_cap(self):
        def factor(crowding):
            return M.cause_factors(M.Inputs(crowding=crowding))["infection"]["crowding"]
        self.assertAlmostEqual(factor(1.64), 2.64)
        self.assertAlmostEqual(factor(5.0), 6.0)
        self.assertAlmostEqual(factor(91.343), 6.0)

    def test_the_cap_keeps_the_rings_adults_alive(self):
        """Sindh's 91 killed every age group at 55-100% a year, so the ring emptied; at the cap a poor state's infants
        all die but its adults die at 4-5% a year, so the ring keeps people to model, and guard 1 hands the state to
        the engine (life expectancy 0.5)."""
        qf, _, _ = M.group_rates(M.Inputs(sol=8.0, literacy=0.3, crowding=91.343))
        adults = [q for (start, _), q in zip(P.GROUPS, qf) if 20 <= start < 45]
        self.assertTrue(all(q < 10_000 for q in adults), adults)
        self.assertLess(M.life_table(qf)["e0"], P.RATE_GUARD_E0_MIN)

    def test_the_harness_takes_the_ceiling(self):
        text = _text(ROOT / "scripts" / "analysis" / "demographics_harness.py")
        self.assertIn("ceiling=P.RATE_BIRTHS_CEILING", text)


class TestTheCrowdingCapScript(unittest.TestCase):
    def test_the_generated_factor(self):
        body = _block(_text(GENERATED_VALUES), "te_demog_f_infection_crowding")
        self.assertRegex(body, r"value = var:te_dg_in_crowd max = 5 multiply = 1 add = 1")

    def test_script_matches_the_model(self):
        for crowding in (0.0, 0.5, 1.64, 5.0, 91.343):
            with self.subTest(crowding=crowding):
                eng = _Engine({})
                eng.vars["te_dg_in_crowd"] = crowding
                got = eng.value(eng._tree(eng.values, "te_demog_f_infection_crowding"))
                want = M.cause_factors(M.Inputs(crowding=crowding))["infection"]["crowding"]
                self.assertAlmostEqual(got, want)

    def test_the_input_stays_as_read(self):
        """The tripwire's sign 6 reads the input itself, so a capped state still shows its crowding."""
        walk = _text(ROOT / "common" / "scripted_effects" / "te_demog_generated_effects.txt")
        self.assertNotRegex(walk, r"name = te_dg_in_crowd value = \{[^}]*max")
        self.assertIn("te_demog_k_crowding_pull_max", _block(_text(CONSOLE_EFFECTS), CHECK))


class TestTheGuardInTheRefresh(unittest.TestCase):
    def refresh(self, prior=True, **kw):
        eng = _refresh_engine(**kw)
        if prior:
            _terms_in_force(eng)
        eng.call("te_demog_rates_refresh")
        return eng

    def assert_cleared(self, eng, why):
        self.assertEqual(eng.vars.get("te_dg_rate_guard"), why)
        self.assertEqual(eng.modifiers, {}, "no census term in force")
        for name in TERM_VARS:
            self.assertNotIn(name, eng.vars, name)
        self.assertEqual((eng.locals["te_dg_rate_new_b"], eng.locals["te_dg_rate_new_d"]), (0.0, 0.0),
                         "fast mode, next in the clock step, sees no term")
        # the moved lines' pairs come back at the state's next monthly refresh, as under Display only
        self.assertTrue(eng.holds(eng._tree(eng.triggers, "te_demog_lines_apply")))

    def test_a_sane_state_keeps_its_terms(self):
        eng = self.refresh(prior=False)
        self.assertNotIn("te_dg_rate_guard", eng.vars)
        self.assertIn("te_dg_mb", eng.vars)
        self.assertIn("te_dg_md", eng.vars)
        mb, _ = M.rate_term(38.0 * POP * 100 / 12, EB0, ceiling=P.RATE_BIRTHS_CEILING)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertFalse(eng.holds(eng._tree(eng.triggers, "te_demog_lines_apply")))

    def test_sindhs_collapsed_life_table(self):
        """The 1923 save's figures: life expectancy 0.5 and a model death rate of -474 per 1,000. The deaths term went to
        its floor (the engine killed nobody); now the terms clear, and the engine's own rates run."""
        eng = self.refresh(cbr=0.0, cdr=-473.61, census={"te_dg_walk_pop": 20e6, "te_dg_e0": 0.5})
        self.assert_cleared(eng, 2)

    def test_a_wrapped_sum(self):
        """East Bengal: the walk's people read below 0, and its bare sums with them. The refresh used to skip a walk
        under the bare minimum and leave last step's terms in force; now they come off."""
        eng = self.refresh(eb0=-2.7e13, ed0=-2.4e13, census={"te_dg_walk_pop": -5.7e13, "te_dg_e0": 0.5})
        self.assert_cleared(eng, 1)

    def test_half_a_billion(self):
        eng = self.refresh(census={"te_dg_walk_pop": 5e8 + 1, "te_dg_e0": 40.0})
        self.assert_cleared(eng, 1)
        eng = self.refresh(census={"te_dg_walk_pop": 5e8, "te_dg_e0": 40.0})
        self.assertNotIn("te_dg_rate_guard", eng.vars)
        self.assertIn("te_dg_mb", eng.vars)

    def test_a_model_rate_below_zero(self):
        for kw in ({"cdr": -0.5}, {"cbr": -0.5}):
            with self.subTest(**kw):
                self.assert_cleared(self.refresh(**kw), 3)

    def test_the_first_bound_that_holds(self):
        eng = self.refresh(cdr=-473.61, census={"te_dg_walk_pop": 1.19e9, "te_dg_e0": 0.5})
        self.assert_cleared(eng, 1)

    def test_a_seed_out_of_range_clears_too(self):
        """A seed leaves in-range terms as they were; out of range they come off as at a step."""
        eng = _refresh_engine(stepped=0.0, census={"te_dg_walk_pop": POP, "te_dg_e0": 0.5})
        del eng.vars["te_dg_cbr_model"], eng.vars["te_dg_cdr_model"]
        _terms_in_force(eng)
        eng.call("te_demog_rates_refresh")
        self.assert_cleared(eng, 2)
        eng = _refresh_engine(stepped=0.0)
        del eng.vars["te_dg_cbr_model"], eng.vars["te_dg_cdr_model"]
        _terms_in_force(eng)
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_dg_rate_guard", eng.vars)
        self.assertEqual(eng.vars["te_dg_md"], -1.0, "a seed in range leaves the terms as they are")

    def test_a_missing_figure_says_nothing(self):
        eng = _refresh_engine(census={})
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_dg_rate_guard", eng.vars)
        self.assertIn("te_dg_mb", eng.vars)

    def test_the_census_takes_over_again_once_back_in_range(self):
        eng = self.refresh(census={"te_dg_walk_pop": POP, "te_dg_e0": 0.5})
        self.assertEqual(eng.vars["te_dg_rate_guard"], 2)
        eng.vars["te_dg_e0"] = 30.0
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_dg_rate_guard", eng.vars)
        self.assertIn("te_dg_mb", eng.vars)
        self.assertTrue(eng.modifiers)

    def test_outside_full_the_verdict_goes(self):
        eng = _refresh_engine(full=False, census={"te_dg_walk_pop": POP, "te_dg_e0": 0.5})
        eng.vars["te_dg_rate_guard"] = 2.0
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_dg_rate_guard", eng.vars)

    def test_known_kills_of_a_third(self):
        """The fourth guard (owner, 2026-11-19): a third or more of the people at the last count killed in the step's
        window, a share above 1 included; the local te_demog_state_census sets for it."""
        for share in (1 / 3, 0.5, 0.95, 2.5):
            with self.subTest(share=share):
                self.assert_cleared(self.refresh(kill_share=share), 4)
        for share in (0.0, 0.2, 0.33):
            with self.subTest(share=share):
                eng = self.refresh(prior=False, kill_share=share)
                self.assertNotIn("te_dg_rate_guard", eng.vars)
                self.assertIn("te_dg_mb", eng.vars)

    def test_the_kills_guard_comes_last(self):
        eng = self.refresh(kill_share=0.9, census={"te_dg_walk_pop": POP, "te_dg_e0": 0.5})
        self.assert_cleared(eng, 2)
        self.assert_cleared(self.refresh(kill_share=0.9, cdr=-0.5), 3)

    def test_a_seed_with_the_kills_clears_too(self):
        """The census's seed in place of the struck step removes the model's rates, so without the guard the refresh
        would leave last year's terms in force; with it they come off."""
        eng = _refresh_engine(stepped=0.0, kill_share=0.9)
        del eng.vars["te_dg_cbr_model"], eng.vars["te_dg_cdr_model"]
        _terms_in_force(eng)
        eng.call("te_demog_rates_refresh")
        self.assert_cleared(eng, 4)

    def test_the_clear_drops_the_verdict(self):
        body = _block(_text(RATE_EFFECTS), "te_demog_rates_clear")
        self.assertIn("remove_variable = te_dg_rate_guard", body)

    def test_the_bounds_are_the_twins(self):
        """The trigger's bounds are the constants the model reads, and every figure is read only where the state holds
        it."""
        text = _text(TRIGGERS)
        for name in ("te_demog_census_people_out_of_range", "te_demog_census_e0_out_of_range",
                     "te_demog_census_rates_out_of_range"):
            body = _block(text, name)
            read = set(re.findall(r"var:(\w+)", body))
            self.assertTrue(read, name)
            self.assertEqual(read - set(re.findall(r"has_variable = (\w+)", body)), set(), name)
        # the fourth reads the census's local, only where te_demog_state_census set it
        body = _block(text, "te_demog_census_kills_out_of_range")
        self.assertEqual(set(re.findall(r"local_var:(\w+)", body)), {"te_dg_kill_share"})
        self.assertIn("has_local_variable = te_dg_kill_share", body)
        self.assertNotIn("var:te_dg_", body.replace("local_var:", ""))
        self.assertIn("te_demog_k_rate_guard_kills_share", body)
        self.assertIn("te_demog_census_kills_out_of_range = yes", _block(text, "te_demog_census_out_of_range"))
        values = _text(GENERATED_VALUES)
        self.assertIn("te_demog_k_rate_guard_kills_share = { value = 0.33333 }", values)
        self.assertIn(f"te_demog_k_rate_guard_people = {{ value = {P.RATE_GUARD_PEOPLE_MAX} }}", values)
        self.assertIn("te_demog_k_rate_guard_e0 = { value = 5 }", values)
        self.assertIn("te_demog_k_rate_births_ceiling = { value = 10 }", values)
        self.assertIn("te_demog_k_crowding_pull_max = { value = 5 }", values)


class TestTheBirthsCeiling(unittest.TestCase):
    def test_a_nonsense_target_stops_at_ten(self):
        """A model birth rate of 300 per 1,000 on the curves' lowest: target / bare 31, which no figure in range
        reaches. Deaths, at a model rate of 300 too, keep no ceiling."""
        eng = _refresh_engine(cbr=300.0, cdr=300.0, eb0=80.0 * POP, ed0=100.0 * POP)
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.vars["te_dg_mb"], P.RATE_BIRTHS_CEILING)
        self.assertEqual(eng.vars["te_dg_rate_clamped"], 1)
        self.assertAlmostEqual(eng.modifiers["te_demog_census_births_up"], P.RATE_BIRTHS_CEILING)
        md, _ = M.rate_term(300.0 * POP * 100 / 12, 100.0 * POP)
        self.assertGreater(md, P.RATE_BIRTHS_CEILING)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=4)
        self.assertEqual(eng.vars["te_dg_rate_clamp_d"], 0, "the deaths floor didn't bite")

    def test_the_largest_sane_term_is_untouched(self):
        """Turkmenia's +4.05 (2020): the target / bare that gives it on a plain state."""
        cbr = (1 + 4.053) * EB0 * 12 / 100 / POP
        eng = _refresh_engine(cbr=cbr)
        eng.call("te_demog_rates_refresh")
        self.assertAlmostEqual(eng.vars["te_dg_mb"], 4.053, places=4)
        self.assertEqual(eng.vars["te_dg_rate_clamped"], 0)

    def test_births_only(self):
        body = _block(_text(RATE_EFFECTS), "te_demog_rates_refresh")
        self.assertEqual(body.count("te_demog_rate_ceiling = yes"), 1)
        births = body.index("set_variable = { name = te_dg_mb ")
        self.assertLess(body.index("te_demog_rate_ceiling = yes"), births)
        self.assertLess(body.index("te_demog_rate_clamp = yes"), body.index("te_demog_rate_ceiling = yes"))


class TestTheTripwireSeesAGuardedState(unittest.TestCase):
    def tripwire(self, state, **kw):
        eng = _ConsoleEngine({}, triggers={"te_demog_effects_run": True})
        eng.effects["debug_log_scopes"] = ""
        eng.vars.update(state)
        eng.locals["te_dg_prov_step"] = kw.get("prov_step", 0.0)
        eng.call(CHECK)
        return eng, [text for text, _ in eng.logs if "demog_runaway" in text]

    @staticmethod
    def guarded(state, guard):
        """The state as the refresh leaves it when the guard held: no terms, and the verdict."""
        out = {k: v for k, v in state.items() if k not in TERM_VARS}
        out["te_dg_rate_guard"] = float(guard)
        return out

    def test_sindh_at_its_size(self):
        eng, lines = self.tripwire(self.guarded(SINDH, 1))
        self.assertEqual(eng.vars["te_dg_chk_runaway"], 2)
        self.assertEqual(eng.vars["te_dg_chk_runaway_year"], 1922.0)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("TE_SELF_CHECK BROKEN demog_runaway why="))
        self.assertIn("guard=[THIS.Var('te_dg_rate_guard')", lines[0])
        self.assertNotIn("te_dg_mb", lines[0], "the terms are gone")

    def test_sindhs_rates_in_a_state_of_twenty_million(self):
        state = {**self.guarded(SINDH, 2), "te_dg_walk_pop": 20e6, "te_dg_walk_pop_prev": 19e6}
        eng, lines = self.tripwire(state)
        self.assertEqual(eng.vars["te_dg_chk_runaway"], 4)
        self.assertEqual(len(lines), 1)

    def test_only_the_guard(self):
        """A model rate below 0 in a state that shows no other sign: why 8."""
        eng, lines = self.tripwire(self.guarded(SANE, 3))
        self.assertEqual(eng.vars["te_dg_chk_runaway"], 8)
        self.assertEqual(len(lines), 1)
        # a small state's short life table too: its rates say nothing on their own, but the guard held
        small = {**self.guarded(SANE, 2), "te_dg_walk_pop": 9_000.0, "te_dg_walk_pop_prev": 9_100.0, "te_dg_e0": 0.5}
        eng, lines = self.tripwire(small)
        self.assertEqual(eng.vars["te_dg_chk_runaway"], 8)

    def test_the_kills_guard_alone_is_quiet(self):
        """The fourth guard answers a strike, not a model gone wrong: alone it logs nothing and sets no code, so the
        state's one line stays for a runaway later (the guards' own why 8 is guards 1 to 3)."""
        eng, lines = self.tripwire(self.guarded(SANE, 4))
        self.assertEqual(lines, [])
        self.assertNotIn("te_dg_chk_runaway", eng.vars)
        # a small state's too
        eng, lines = self.tripwire({**self.guarded(SANE, 4), "te_dg_walk_pop": 9_000.0, "te_dg_walk_pop_prev": 9_100.0})
        self.assertEqual(lines, [])

    def test_the_kills_guard_with_another_sign_prints_its_code(self):
        state = {**self.guarded(SANE, 4), "te_dg_e0": 0.5}
        eng, lines = self.tripwire(state)
        self.assertEqual(eng.vars["te_dg_chk_runaway"], 4)
        self.assertEqual(len(lines), 1)
        self.assertIn("guard=[THIS.Var('te_dg_rate_guard')", lines[0])
        self.assertEqual(eng.logs[0][1]["te_dg_rate_guard"], 4.0)
        self.assertIn("4 known kills of a third or more of its people in the step's window", lines[0])

    def test_an_unguarded_state_keeps_its_line(self):
        eng, lines = self.tripwire({**SANE, "te_dg_rate_clamp_d": 1.0})
        self.assertEqual(eng.vars["te_dg_chk_runaway"], 5)
        self.assertNotIn("guard=", lines[0])
        self.assertIn("te_dg_mb", lines[0])

    def test_the_births_term_at_its_ceiling(self):
        eng, _ = self.tripwire({**SANE, "te_dg_mb": P.RATE_BIRTHS_CEILING})
        self.assertEqual(eng.vars["te_dg_chk_runaway"], 7)
        eng, lines = self.tripwire({**SANE, "te_dg_mb": P.RATE_BIRTHS_CEILING - 0.01})
        self.assertEqual(lines, [])

    def test_the_guards_and_the_tripwire_share_their_bounds(self):
        body = _block(_text(CONSOLE_EFFECTS), CHECK)
        for name in ("te_demog_k_rate_guard_people", "te_demog_k_rate_guard_e0", "te_demog_k_crowding_pull_max",
                     "te_demog_k_rate_births_ceiling"):
            self.assertIn(name, body)
        self.assertNotIn("500000000", body)


class TestEndToEnd(unittest.TestCase):
    def test_sindh_through_the_refresh_and_the_tripwire(self):
        """Sindh's census at 20 million (its rates, not its size): the refresh clears the terms, and the tripwire, next
        at the census, logs the onset with the guard's code."""
        census = {k: v for k, v in SINDH.items() if k not in TERM_VARS}
        census.update(te_dg_walk_pop=20e6, te_dg_walk_pop_prev=19e6)
        eng = _refresh_engine(cbr=0.0, cdr=-473.61, census=census, console=True, pop=20e6)
        eng.effects["debug_log_scopes"] = ""
        _terms_in_force(eng)
        eng.locals["te_dg_prov_step"] = 0.0
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.vars["te_dg_rate_guard"], 2)
        self.assertEqual(eng.modifiers, {})
        eng.call(CHECK)
        lines = [text for text, _ in eng.logs if "demog_runaway" in text]
        self.assertEqual(len(lines), 1)
        self.assertEqual(eng.vars["te_dg_chk_runaway"], 4)
        self.assertIn("guard=", lines[0])


# the census pulse with its seed and step stubbed: which ran (test_demographics_territory's STUBS)
CENSUS_STUBS = {"te_demog_seed": "set_variable = { name = did value = 1 }",
                "te_demog_step": "set_variable = { name = did value = 2 }"}


class TestTheKillsGuard(unittest.TestCase):
    """The fourth guard (owner, 2026-11-19) and the census's seed in place of the struck step (the lead session's
    addition, separate from the guard): 25 warheads on Sankt-Peterburg in 1977 left 197,774 of 3,995,846 people, and
    the step counted the year's births and deaths from the people before the kills over the survivors (840 births and
    6,369 deaths per 1,000), which put the births term at its ceiling and poisoned the next years' target and scales."""

    def census(self, kills=None, year=1837.0, last=1836.0, pop_last=1000.0, pop=1000.0, rule=True, full=True):
        """te_demog_state_census for a state counted in `last` at pop_last people, with `kills` noted since (None:
        te_dg_kills_in unset); the seed and step stubbed. rule: the census runs (Full or Display only); full: Full."""
        eng = _Engine({"year": year, "state_population": pop, "te_demog_state_provinces": 10.0},
                      triggers={"te_demog_cohorts_run": rule, "te_demog_effects_run": full and rule},
                      effects=CENSUS_STUBS)
        eng.vars.update(te_dg_year=last, te_dg_raw=900.0, te_dg_pop_last=pop_last, te_dg_provinces=10.0)
        if kills is not None:
            eng.vars["te_dg_kills_in"] = kills
        eng.call("te_demog_state_census")
        return eng

    def test_the_share_is_the_models(self):
        for kills, pop_last in ((3.7e6, 3_995_846.0), (10e6, 3_995_846.0), (300.0, 1000.0), (0.0, 1000.0),
                                (50.0, 0.0)):
            with self.subTest(kills=kills, pop_last=pop_last):
                eng = _Engine({})
                eng.vars.update(te_dg_kills_in=kills, te_dg_pop_last=pop_last)
                eng.call("te_demog_kill_share_store")
                self.assertAlmostEqual(eng.locals["te_dg_kill_share"], M.kill_share(kills, pop_last), places=9)
        eng = _Engine({})
        eng.vars["te_dg_pop_last"] = 1000.0
        eng.call("te_demog_kill_share_store")
        self.assertNotIn("te_dg_kill_share", eng.locals, "no kills noted, no share")

    def test_a_third_seeds_in_place_of_the_step(self):
        for kills, did in ((333.34, 1), (900.0, 1), (2500.0, 1), (333.0, 2), (100.0, 2), (0.0, 2), (None, 2)):
            with self.subTest(kills=kills):
                eng = self.census(kills=kills)
                self.assertEqual(eng.vars["did"], did)
                # left for the refresh, straight after the census in the same effect; 0 without kills
                self.assertAlmostEqual(eng.locals["te_dg_kill_share"], (kills or 0.0) / 1000.0)

    def test_only_a_census_a_year_on_reads_the_kills(self):
        """A second pulse in the same year does nothing, and its kills wait for the next step's window; a census gap
        seeds anyway, and its kills say nothing about a step."""
        eng = self.census(kills=900.0, year=1836.0)
        self.assertNotIn("did", eng.vars)
        self.assertEqual(eng.locals["te_dg_kill_share"], 0.0)
        self.assertEqual(eng.vars["te_dg_kills_in"], 900.0)
        eng = self.census(kills=900.0, last=1834.0)
        self.assertEqual(eng.vars["did"], 1)
        self.assertEqual(eng.locals["te_dg_kill_share"], 0.0)

    def test_each_census_starts_its_own_share(self):
        """A pulse is its own effect in game, so a local can't carry over; the census still sets it 0 first, so a seed
        or a second pulse after a struck census reads none, whatever ran before it."""
        eng = _Engine({"year": 1837.0, "state_population": 1000.0, "te_demog_state_provinces": 10.0},
                      triggers={"te_demog_cohorts_run": True}, effects=CENSUS_STUBS)
        eng.vars.update(te_dg_year=1837.0, te_dg_raw=900.0, te_dg_pop_last=1000.0, te_dg_provinces=10.0)
        eng.locals["te_dg_kill_share"] = 0.9
        eng.call("te_demog_state_census")
        self.assertEqual(eng.locals["te_dg_kill_share"], 0.0)
        self.assertNotIn("did", eng.vars)

    def test_wherever_the_census_runs(self):
        """The seed is the census's own (Full and Display only alike); only the refresh's guard is Full's. Disabled: no
        census."""
        self.assertEqual(self.census(kills=900.0).vars["did"], 1)
        self.assertEqual(self.census(kills=900.0, full=False).vars["did"], 1, "Display only")
        eng = self.census(kills=900.0, rule=False)
        self.assertNotIn("did", eng.vars)

    def test_the_census_keeps_no_size_test(self):
        """The owner's 2026-10-20 rule stands: known kills are not a move, and the share is read in its own effect."""
        body = re.sub(r"#[^\n]*", "", _block(_text(R.EFFECTS), "te_demog_state_census"))
        self.assertIn("te_demog_kill_share_store = yes", body)
        self.assertIn("te_demog_census_kills_out_of_range = yes", body)
        self.assertNotIn("te_dg_pop_last", body)
        self.assertNotIn("te_dg_kills_in", body)

    # -- through the yearly pulse (TestRatesScript's, its walks stubbed) --------------------------------------------------

    def pulse(self):
        eng = R.TestRatesScript._pulse(self)
        eng.call("te_demog_state_yearly")            # 1836: no census, a seed
        eng.fixtures["year"] = 1837.0
        eng.call("te_demog_state_yearly")            # 1837: a step, and M
        self.assertEqual(eng.vars["te_dg_stepped"], 1)
        self.assertIn("te_dg_mb", eng.vars)
        self.assertTrue(self.census_mods(eng))
        return eng

    @staticmethod
    def census_mods(eng):
        return {k: v for k, v in eng.modifiers.items()
                if k.startswith(("te_demog_census_births", "te_demog_census_deaths", "te_demog_census_wealth"))}

    def test_a_struck_state_through_the_pulse(self):
        """1838: kills of 0.9 (and of 2.5, a salvo booked against a stale state_population) of the people at the 1837
        count. The census seeds at the people left in place of its step (no model rates, no scales, no start rate),
        the refresh clears its terms (te_dg_rate_guard 4, no Census: Births or Census: Deaths), and in 1839 the
        census steps from the seed and sets its terms again."""
        for share in (0.9, 2.5):
            with self.subTest(share=share):
                eng = self.pulse()
                eng.vars["te_dg_kills_in"] = share * eng.vars["te_dg_pop_last"]
                eng.fixtures["year"] = 1838.0
                eng.call("te_demog_state_yearly")
                self.assertEqual(eng.vars["te_dg_rate_guard"], 4)
                self.assertEqual(eng.vars["te_dg_stepped"], 0, "a seed, not a step")
                self.assertEqual(eng.vars["te_dg_year"], 1838.0)
                self.assertNotIn("te_dg_kills_in", eng.vars)
                for name in ("te_dg_cbr_model", "te_dg_cdr_model", "te_dg_sr_b", "te_dg_sr_d", *TERM_VARS):
                    self.assertNotIn(name, eng.vars, name)
                self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))
                self.assertEqual(self.census_mods(eng), {})
                self.assertEqual((eng.locals["te_dg_rate_new_b"], eng.locals["te_dg_rate_new_d"]), (0.0, 0.0))
                eng.fixtures["year"] = 1839.0
                eng.call("te_demog_state_yearly")
                self.assertNotIn("te_dg_rate_guard", eng.vars)
                self.assertEqual(eng.vars["te_dg_stepped"], 1)
                self.assertIn("te_dg_mb", eng.vars)
                self.assertTrue(self.census_mods(eng))

    def test_fewer_kills_step_as_before(self):
        eng = self.pulse()
        eng.vars["te_dg_kills_in"] = 0.3 * eng.vars["te_dg_pop_last"]
        eng.fixtures["year"] = 1838.0
        eng.call("te_demog_state_yearly")
        self.assertNotIn("te_dg_rate_guard", eng.vars)
        self.assertEqual(eng.vars["te_dg_stepped"], 1)
        self.assertIn("te_dg_mb", eng.vars)


if __name__ == "__main__":
    unittest.main()
