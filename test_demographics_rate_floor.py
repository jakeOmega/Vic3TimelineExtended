"""The census's births and deaths terms down to the engine's own floor (owner, 2026-10-20).

The floor of the state read with the census's term in it went from -0.8 to -1, the engine's own per-pop floor; M lost its
+3 ceiling and the step's scales their -0.9 and +4. This file holds what the change added that the registry's
interpreter can't run as it stands, and the checks the change rests on:
- the self-check rate_below_measured (te_demog_rate_effects.txt), which reads globals and writes debug_log lines;
- the late game's wealth slope at a state total near -0.95: its bound is fitted to this refresh's census rate and reads
  no M, so the richest pop stays at the treated's rate whatever M was;
- the walk's per-pop death multiplier with the state's wealth line x the pop's wealth, as the engine applies it (probe
  P6), and the two places that read the walk beside the line: the window's start rate and the Causes of Death split;
- the loc that named the mod's clamps as the game's limits;
- the calendar estimate of deaths by cause, which a late-game state skips (its own count replaces it).
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_harness as H  # noqa: E402
import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import test_demographics_registry as R  # noqa: E402  (a module: its TestCases aren't collected here)
from test_demographics_registry import (  # noqa: E402  (helpers only: no TestCase)
    EFFECTS, GENERATED_VALUES, MISC_LOC, RATE_EFFECTS, _block, _Engine, _find, _OwnerEngine, _raw_blocks, _text)

CHECK = ("te_demog_rbm_selfcheck_flows", "te_demog_rbm_selfcheck_arm")
REAL = _raw_blocks([RATE_EFFECTS])


class _CheckEngine(_Engine):
    """_Engine with the self-check's own effects (the registry stubs them) and what they need: has_global_variable reads
    the globals set here, set_global_variable sets one, debug_log keeps its text."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for name in CHECK:
            self.effects[name] = REAL[name]
        self.globals, self.logs = set(), []

    def _test(self, key, op, arg):
        if key == "has_global_variable":
            return arg in self.globals
        return super()._test(key, op, arg)

    @staticmethod
    def _join_logs(items):
        """The interpreter's parser splits a quoted string at its spaces: a debug_log's words come back as one text."""
        out, i = [], 0
        while i < len(items):
            key, op, arg = items[i]
            i += 1
            if key == "debug_log" and isinstance(arg, str) and not (len(arg) > 1 and arg.endswith('"')):
                parts = [arg]
                while i < len(items):
                    k, o, a = items[i]
                    i += 1
                    parts.append(f"{k}{o}{a}" if o else k)
                    if parts[-1].endswith('"'):
                        break
                arg = " ".join(parts)
            out.append((key, op, arg))
        return out

    def run(self, items):
        segment = []
        for item in self._join_logs(items):
            key, _, arg = item
            if key not in ("set_global_variable", "debug_log"):
                segment.append(item)
                continue
            super().run(segment)
            segment = []
            if key == "set_global_variable":
                self.globals.add(arg if isinstance(arg, str) else _find(arg, "name"))
            else:
                self.logs.append(arg)
        super().run(segment)


class TestRateBelowMeasured(unittest.TestCase):
    """te_demog_rbm_selfcheck_flows and _arm. A late state of a million people at the bare curve's lowest (100 deaths a
    month per 100,000, so its bare deaths are 1e8 in the walk's units): the window just measured ran at the old floor (a
    fifth of the bare curve), the new one starts at 0.04 of it, a total of -0.96."""

    POP = 1_000_000.0
    ED0 = 100.0 * POP

    def engine(self):
        eng = _CheckEngine({"state_population": self.POP}, triggers={"te_demog_effects_run": True})
        eng.locals.update(te_dg_war=0.0, te_dg_kills=0.0, te_dg_rk_on=0.0)
        return eng

    def arm(self, eng, mult_end=0.2, mult_start=0.2, mig=10.0, new=0.04):
        """Step N: the flows' candidate from a window at mult_start .. mult_end of the bare curve, then the refresh's
        new start rate (new x the bare curve, per head) and the arm."""
        eng.locals.update(te_dg_w_ed0=self.ED0, te_dg_w_ed=mult_end * self.ED0, te_dg_mig=mig)
        eng.vars["te_dg_sr_d"] = mult_start * self.ED0 / self.POP
        eng.call("te_demog_rbm_selfcheck_flows")
        eng.vars["te_dg_sr_d"] = new * self.ED0 / self.POP
        eng.locals["te_dg_rate_sr"] = 1.0
        eng.call("te_demog_rbm_selfcheck_arm")

    def read(self, eng, mig, mult_end=0.04, start=0.04):
        """Step N+1: the window at start .. mult_end of the bare curve, the residual `mig` against the walk's expected
        deaths at its linear line (te_dg_ed, which holds the census's wealth line per pop since 2026-10-20)."""
        ed = (start + mult_end) / 2 * self.ED0 * 12 / 1e5
        eng.vars.update(te_dg_ed=ed)
        eng.locals.update(te_dg_w_ed0=self.ED0, te_dg_w_ed=mult_end * self.ED0, te_dg_mig=mig)
        eng.call("te_demog_rbm_selfcheck_flows")
        return ed

    def verdict(self, eng):
        lines = [x for x in eng.logs if "rate_below_measured" in x]
        self.assertEqual(len(lines), 1, eng.logs)
        return lines[0].split()[1]

    def test_it_arms_on_a_drop_from_the_measured_range(self):
        eng = self.engine()
        self.arm(eng)
        self.assertAlmostEqual(eng.vars["te_dg_rbm_s1"], 0.04)
        self.assertEqual(eng.vars["te_dg_rbm_r0"], 10.0)
        # a month of the old rate less the new one, in deaths: (0.2 - 0.04) x 1e8 / 1e5
        self.assertAlmostEqual(eng.vars["te_dg_rbm_lag"], 160.0)

    def test_ok_when_the_year_runs_on_the_line(self):
        """The engine linear to -1: the residual is the engine's own migration, 10, well inside half the expected
        deaths."""
        eng = self.engine()
        self.arm(eng)
        self.read(eng, mig=10.0)
        self.assertEqual(self.verdict(eng), "OK")
        self.assertIn("te_demog_rbm_selfcheck_done", eng.globals)
        for name in ("te_dg_rbm_r0", "te_dg_rbm_s1", "te_dg_rbm_lag", "te_dg_rbm_r", "te_dg_rbm_gap"):
            self.assertNotIn(name, eng.vars, name)

    def test_broken_when_the_engine_stops_at_minus_0_9(self):
        """Had the engine held each pop at -0.9, the window's deaths would be a tenth of the bare curve: 720 more than
        the 480 the walk expects at -0.96, which the residual shows with the sign turned."""
        eng = self.engine()
        self.arm(eng)
        gap = 0.1 * self.ED0 * 12 / 1e5 - 0.04 * self.ED0 * 12 / 1e5
        self.read(eng, mig=10.0 - gap)
        self.assertEqual(self.verdict(eng), "BROKEN")

    def test_the_first_month_may_run_at_the_old_rate(self):
        """Q7: a change of rate shows within a month, so the low side takes a month of the old rate on top."""
        eng = self.engine()
        self.arm(eng)
        self.read(eng, mig=-0.5 * 480 - 150.0)
        self.assertEqual(self.verdict(eng), "OK")
        eng = self.engine()
        self.arm(eng)
        self.read(eng, mig=-0.5 * 480 - 170.0)
        self.assertEqual(self.verdict(eng), "BROKEN")

    def test_a_stop_at_minus_0_9_never_reads_ok(self):
        """The review of #1082: the OK band's low side takes a month of the old rate on top of half the deaths, so after a
        big drop (an old window at 0.55 of the bare curve, a late medical leap) a stop at -0.9 would have read OK. The
        arm now asks the deficit such a stop leaves to clear that low side by the baseline's quarter of the deaths: every
        armed state reads BROKEN under a stop at -0.9, even with that quarter of migration the other way."""
        armed = {}
        for old in (0.2, 0.3, 0.4, 0.55, 0.8):
            with self.subTest(old=old):
                eng = self.engine()
                self.arm(eng, mult_end=old, mult_start=old)
                armed[old] = "te_dg_rbm_s1" in eng.vars
                if armed[old]:
                    gap = 0.1 * self.ED0 * 12 / 1e5 - 0.04 * self.ED0 * 12 / 1e5
                    self.read(eng, mig=0.25 * 480 - gap)
                    self.assertEqual(self.verdict(eng), "BROKEN")
                else:
                    self.assertNotIn("te_dg_rbm_r0", eng.vars)
        self.assertEqual(armed, {0.2: True, 0.3: True, 0.4: False, 0.55: False, 0.8: False})

    def test_above_the_band_is_migration_not_a_verdict(self):
        """A stop at -0.9 only adds deaths, so it pushes the residual down. A residual above half the deaths is migration
        the baseline missed: no line, the arm goes, and the once-a-game flag stays unspent for a later state."""
        eng = self.engine()
        self.arm(eng)
        self.read(eng, mig=0.5 * 480 + 1.0)
        self.assertEqual(eng.logs, [])
        self.assertNotIn("te_demog_rbm_selfcheck_done", eng.globals)
        for name in ("te_dg_rbm_s1", "te_dg_rbm_r0", "te_dg_rbm_lag"):
            self.assertNotIn(name, eng.vars, name)

    def test_the_console_replay_does_nothing_here(self):
        """te_debug_demog.1's option a replays a step through te_demog_flows with no walk: the hook reads no walk local,
        spends no flag and keeps an armed state's arm for its real step."""
        eng = self.engine()
        self.arm(eng)
        armed = {k: eng.vars[k] for k in ("te_dg_rbm_s1", "te_dg_rbm_r0", "te_dg_rbm_lag")}
        for name in ("te_dg_w_ed0", "te_dg_w_ed"):
            eng.locals.pop(name)
        eng.vars["te_dg_ed"] = 480.0
        eng.locals["te_dg_mig"] = -5000.0
        eng.call("te_demog_rbm_selfcheck_flows")
        self.assertEqual(eng.logs, [])
        self.assertNotIn("te_demog_rbm_selfcheck_done", eng.globals)
        self.assertEqual({k: eng.vars[k] for k in armed}, armed)

    def test_no_arm_where_the_baseline_is_loud(self):
        """A residual over a quarter of the new window's deaths (120 here) is migration that could hide a bend."""
        eng = self.engine()
        self.arm(eng, mig=121.0)
        self.assertNotIn("te_dg_rbm_s1", eng.vars)
        self.assertNotIn("te_dg_rbm_r0", eng.vars)

    def test_no_arm_where_the_baseline_was_below_the_measured_range(self):
        """A baseline taken below -0.9 would already hold a bend, if there were one: no candidate."""
        for kw in (dict(mult_end=0.09), dict(mult_start=0.09)):
            with self.subTest(**kw):
                eng = self.engine()
                self.arm(eng, **kw)
                self.assertNotIn("te_dg_rbm_r0", eng.vars)
                self.assertNotIn("te_dg_rbm_s1", eng.vars)

    def test_no_arm_above_minus_0_95_or_with_few_deaths(self):
        """At -0.94 a stop at -0.9 would add less than the deaths' half the check reads; under 100 deaths a year a few
        people's moves decide it."""
        eng = self.engine()
        self.arm(eng, new=0.06)
        self.assertNotIn("te_dg_rbm_s1", eng.vars)
        self.assertNotIn("te_dg_rbm_r0", eng.vars)
        eng = self.engine()
        eng.fixtures["state_population"] = 1000.0
        self.POP, saved = 1000.0, self.POP
        try:
            self.ED0, saved_ed0 = 100.0 * 1000.0, self.ED0
            self.arm(eng, mig=0.0)
            self.assertNotIn("te_dg_rbm_s1", eng.vars)
        finally:
            self.POP, self.ED0 = saved, saved_ed0

    def test_no_verdict_if_the_window_ended_higher(self):
        """The window's end back above -0.95: no line, the arm goes, and a later state can arm."""
        eng = self.engine()
        self.arm(eng)
        self.read(eng, mig=0.0, mult_end=0.08)
        self.assertEqual(eng.logs, [])
        self.assertNotIn("te_demog_rbm_selfcheck_done", eng.globals)
        self.assertNotIn("te_dg_rbm_s1", eng.vars)

    def test_war_kills_or_moves_end_the_arm(self):
        for name in ("te_dg_war", "te_dg_kills", "te_dg_rk_on"):
            with self.subTest(name=name):
                eng = self.engine()
                self.arm(eng)
                eng.locals[name] = 1.0
                self.read(eng, mig=0.0)
                self.assertEqual(eng.logs, [])
                self.assertNotIn("te_dg_rbm_s1", eng.vars)
                self.assertNotIn("te_dg_rbm_r0", eng.vars, "nor a new candidate")

    def test_once_a_game(self):
        eng = self.engine()
        self.arm(eng)
        eng.globals.add("te_demog_rbm_selfcheck_done")
        self.read(eng, mig=0.0)
        self.assertEqual(eng.logs, [])
        self.assertNotIn("te_dg_rbm_s1", eng.vars)
        eng = self.engine()
        eng.globals.add("te_demog_rbm_selfcheck_done")
        self.arm(eng)
        self.assertNotIn("te_dg_rbm_r0", eng.vars)

    def test_a_refresh_that_stores_no_start_drops_the_candidate(self):
        """A refresh that stored no start rate (a seed's, a walk under one person): the candidate goes, so a later
        refresh can't arm on a stale baseline."""
        eng = self.engine()
        eng.locals.update(te_dg_w_ed0=self.ED0, te_dg_w_ed=0.2 * self.ED0, te_dg_mig=0.0)
        eng.call("te_demog_rbm_selfcheck_flows")
        self.assertIn("te_dg_rbm_r0", eng.vars)
        eng.locals["te_dg_rate_sr"] = 0.0
        eng.call("te_demog_rbm_selfcheck_arm")
        self.assertNotIn("te_dg_rbm_r0", eng.vars)

    def test_the_hooks_sit_where_the_figures_are(self):
        """The flows' hook runs after the residual takes Internal Resettlement's known moves out and before the noise
        band zeroes a small one; the arm is the refresh's last statement, after it stores the next window's start."""
        flows = _block(_text(EFFECTS), "te_demog_flows")
        hook = flows.index("te_demog_rbm_selfcheck_flows = yes")
        self.assertLess(flows.index("te_demog_rs_selfcheck = yes"), hook)
        self.assertLess(hook, flows.index("te_dg_noise"))
        refresh = _block(_text(RATE_EFFECTS), "te_demog_rates_refresh")
        self.assertTrue(refresh.rstrip().rstrip("}").rstrip().endswith("te_demog_rbm_selfcheck_arm = yes"))
        flows_check = _block(_text(RATE_EFFECTS), "te_demog_rbm_selfcheck_flows")
        self.assertEqual(flows_check.count("NOT = { has_global_variable = te_demog_rbm_selfcheck_done }"), 2)
        self.assertIn("TE_SELF_CHECK OK rate_below_measured", flows_check)
        self.assertIn("TE_SELF_CHECK BROKEN rate_below_measured", flows_check)
        self.assertIn("NOT = { te_demog_clock_on = yes }", flows_check)


class TestTheWealthSlopeAtTheFloor(unittest.TestCase):
    """Step 2's check (2026-10-20): with the floor at -1 a late state's deaths total can sit near -0.95, and the census's
    wealth slope (Census: Deaths by Wealth) takes a rich pop lower still. The slope's bound holds the richest pop at the
    treated's rate on the census's rate, so it is fitted to this refresh's target over the bare curve (te_dg_rate_tb)
    and reads no M: the refresh's own new term, the old one and has_modifier all leave it alone."""

    POP = 1_000_000.0
    ED0 = 8.0 * POP * 100 / 12           # the bare deaths: 8 per 1,000 a year
    CDR = 0.385                          # the census's: a total of about -0.95 with the +0.04 line on top
    READ = 0.04

    def refresh(self, slope, prior=0.0, mbar=0.6, rho=0.1, wbar=40.0, wtop=150.0, wealth_read=0.0):
        families = {f"modifier:{n}": 0.0 for n in P.ENGINE_LINE_TYPES.values()}
        eng = _Engine({"state_population": self.POP, "modifier:state_birth_rate_mult": 0.05,
                       "modifier:state_mortality_mult": self.READ + prior,
                       "modifier:state_mortality_wealth_mult": wealth_read, **families},
                      triggers={"te_demog_effects_run": True, "te_demog_cohorts_run": True})
        if prior:
            eng.modifiers["te_demog_census_deaths_down"] = -prior
            eng.vars["te_dg_md"] = prior
        eng.locals.update(te_dg_w_eb0=475e6, te_dg_w_ed0=self.ED0, te_dg_w_ebr=0.0, te_dg_w_edr=0.0, te_dg_w_eb=475e6,
                          te_dg_w_ed=self.ED0 * (1 + self.READ + prior) + wealth_read * wbar * self.ED0,
                          te_dg_w_eb0m=475e6, te_dg_w_ed0m=self.ED0,
                          te_dg_w_sev=0.0, te_dg_w_sevd=0.0, te_dg_w_edw=wbar * self.ED0, te_dg_w_wtop=wtop)
        eng.vars.update(te_dg_stepped=1.0, te_dg_cbr_model=10.0, te_dg_cdr_model=self.CDR, te_dg_lx_slope=slope,
                        te_dg_lx_mbar=mbar, te_dg_lx_rho=rho)
        eng.call("te_demog_rates_refresh")
        return eng

    def test_the_richest_pop_stays_at_the_treated_rate(self):
        tb = self.CDR * self.POP * 100 / 12 / self.ED0
        for slope in (-0.004, -0.02):
            with self.subTest(slope=slope):
                eng = self.refresh(slope)
                md, w = eng.vars["te_dg_md"], eng.vars["te_dg_w"]
                self.assertEqual(eng.vars["te_dg_rate_clamped"], 0, "the floor doesn't bind")
                mean = 1 + self.READ + md + w * 40.0
                self.assertAlmostEqual(mean, tb * (1 + self.READ), places=5)
                self.assertLess(mean - 1, -0.94, "the total sits near -0.95")
                held = M.lx_wealth_term(slope, 0.6, 0.1, 40.0, 150.0)
                richest = 1 + self.READ + md + w * 150.0
                self.assertAlmostEqual(richest, tb * (1 + self.READ + held * 110.0), places=5)
                self.assertGreaterEqual(richest, tb * (0.1 / 0.6 + self.READ) - 1e-6)
                self.assertGreater(richest, 0, "the richest pop's deaths don't floor at 0")

    def test_the_bound_reads_no_m(self):
        """Last step's M in the read and on its modifier (-0.5 or +0.3): the same slope, the same wealth line, the same
        new M; only the read's other part decides."""
        base = self.refresh(-0.02)
        for prior in (-0.5, 0.3):
            with self.subTest(prior=prior):
                eng = self.refresh(-0.02, prior=prior)
                self.assertAlmostEqual(eng.locals["te_dg_rate_slope"], base.locals["te_dg_rate_slope"], places=9)
                self.assertAlmostEqual(eng.vars["te_dg_w"], base.vars["te_dg_w"], places=9)
                self.assertAlmostEqual(eng.vars["te_dg_md"], base.vars["te_dg_md"], places=9)
                self.assertAlmostEqual(eng.locals["te_dg_rate_new_d"], eng.vars["te_dg_md"], places=9)


class TestTheWalkAppliesTheWealthLine(unittest.TestCase):
    """2026-10-20: te_demog_pop_death_mult adds the state's state_mortality_wealth_mult x the pop's wealth, inside the
    per-pop floor at 0, as the engine does (probe P6: proportional to each pop's own wealth). Under Full the read is the
    census's pair (Private Health Insurance's line at the census's rate and the late slope), so the window's deaths, dz
    and the residual now see the deaths the line takes away; before, they ran high by |the line| x the mean wealth."""

    D = H.G.read_defines()

    def multiplier(self, read, wealth_read, wealth, food=0.8):
        text = _block(_text(GENERATED_VALUES), "te_demog_pop_death_mult")
        reads = dict.fromkeys(re.findall(r"(?:state|workplace)\.modifier:\w+", text), 0.0)
        reads.update({"state.modifier:state_mortality_mult": read,
                      "state.modifier:state_mortality_wealth_mult": wealth_read})
        lo, hi = P.FOOD_SECURITY_SEVERE_STARVATION_THRESHOLD, P.FOOD_SECURITY_STARVATION_THRESHOLD
        eng = _OwnerEngine({"literacy_rate": 0.9, "food_security": food, "wealth": wealth, **reads}, pop_type="clerks",
                           triggers={"is_in_severe_starvation": food < lo, "is_in_mild_starvation": lo <= food < hi,
                                     "is_employed": False, "is_homeland_of_country_cultures": True})
        return eng.value(eng._tree(eng.values, "te_demog_pop_death_mult"))

    def test_the_line_scales_by_the_pops_wealth(self):
        self.assertAlmostEqual(self.multiplier(-0.9, 0.0, 60.0), 0.1, places=5)
        self.assertAlmostEqual(self.multiplier(-0.9, -0.001, 60.0), 0.04, places=5)
        self.assertAlmostEqual(self.multiplier(0.0, -0.002, 99.0), 1 - 0.198, places=5)
        # past the floor the pop's deaths are 0, never negative
        self.assertEqual(self.multiplier(-0.9, -0.002, 99.0), 0.0)

    def test_predict_and_the_walk_agree(self):
        """predict (demographics_harness.predict_state) gives each pop bare x max(0, 1 + M + the lines on top + its own
        + the wealth line x its wealth), the line at the census's rate. The walk's multiplier on the same read gives the
        same deaths, a late rate where the floor is near."""
        for cdr, line, wealth in ((1.0, -0.004, 50.0), (30.0, -0.002, 80.0), (0.4, -0.005, 99.0)):
            with self.subTest(cdr=cdr, line=line, wealth=wealth):
                pop = H.Pop(1e6, 30.0, 0.9, 0.8, wealth=wealth)
                out = H.predict_state([pop], cbr=10.0, cdr=cdr, d=self.D, on_top_d=0.04, wealth=line)
                bare_d = 1e6 * H.G.monthly_mortality(30.0, self.D) * 12
                wealth_read = max(line, P.WEALTH_LINE_FLOOR) * (cdr / 1000 * 1e6) / bare_d
                mult = self.multiplier(out["m_d"] + 0.04, wealth_read, wealth)
                self.assertAlmostEqual(out["deaths"], bare_d * mult, delta=out["deaths"] * 1e-4 + 1e-3)

    def test_the_split_keeps_the_line_in_the_whole_state(self):
        """The census's wealth line is the census's own: M nets it, so the Causes of Death split counts it in the whole
        state's part, with that M, not as a line on some of its people."""
        eng = _Engine({"state_population": 1e6, "modifier:state_mortality_mult": -0.5,
                       "modifier:state_mortality_wealth_mult": -0.002},
                      triggers={"te_demog_effects_run": True})
        ed0, edw = 100.0 * 1e6, 100.0 * 1e6 * 40.0
        w_ed = ed0 * 0.5 + (-0.002) * edw            # every pop unfloored, no line of its own
        eng.locals.update(te_dg_w_ed0=ed0, te_dg_w_edr=0.0, te_dg_w_ed=w_ed, te_dg_w_edw=edw, te_dg_w_sevd=0.0,
                          te_dg_w_sev=0.0, te_dg_w_pop=1e6)
        eng.vars.update(te_dg_ed=w_ed * 12 / 1e5)
        eng.call("te_demog_on_top_split")
        self.assertAlmostEqual(eng.vars["te_dg_ed_state"], eng.vars["te_dg_ed"], places=3)
        self.assertEqual(eng.vars["te_dg_ed_sev"], 0.0)

    def test_the_start_rate_swaps_in_the_new_line(self):
        """The window that starts at the refresh runs on its new te_dg_w: the start rate takes the walk's line in force
        off the bare deaths x wealth it reaches and puts the new one on, as it does for M."""
        case = TestTheWealthSlopeAtTheFloor()
        old_line = -0.0001
        eng = case.refresh(-0.004, wealth_read=old_line)
        md, w = eng.vars["te_dg_md"], eng.vars["te_dg_w"]
        ed0, edw = case.ED0, 40.0 * case.ED0
        walk_ed = ed0 * (1 + case.READ) + old_line * edw
        want = (md * ed0 + walk_ed + (w - old_line) * edw) / case.POP
        self.assertAlmostEqual(eng.vars["te_dg_sr_d"], want, places=4)
        # the start's own lines leave the line out: none of the pops has a line of its own here
        self.assertAlmostEqual(eng.vars["te_dg_sp_d"], 0.0, places=4)


    def test_fast_mode_swaps_in_the_new_line(self):
        """Fast mode's term is (K - 1) x the walk's average with the census's new terms in it: the walk's average holds
        the wealth line in force, so the census's new te_dg_w goes in for it, on the bare deaths x wealth it reaches, as
        the start rate takes it (the review of #1082)."""
        eng = R.TestFastMode()._eng_full()
        old_line, ed0 = -0.0001, 430e3
        eng.fixtures["modifier:state_mortality_wealth_mult"] = old_line
        eng.locals["te_dg_w_edw"] = 40.0 * ed0
        R.TestFastMode()._both(eng, eb=1.05 * 475e3, eb0=475e3, ed=(0.98 + old_line * 40.0) * ed0, ed0=ed0)
        md, w = eng.vars["te_dg_md"], eng.vars["te_dg_w"]
        self.assertEqual(w, 0.0)   # no line under Full here: the census applies none
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], 3 * (0.98 + md), places=5)


class TestTheTextIsTrue(unittest.TestCase):
    """The hover named the mod's clamps as the game's limits ("can't fall below a fifth of its base", "can't rise past
    four times its base"). The cap is gone; the floor is the engine's own, and its text says what binds it."""

    def test_the_loc(self):
        loc = _text(MISC_LOC)
        for gone in ("te_demog_st_ontop_end_cap:", "te_demog_st_ontop_end_rest:"):
            self.assertNotIn(gone, loc)
        floor = re.search(r'^ te_demog_st_ontop_end_floor:0 "(.*)"$', loc, re.M).group(1)
        for false in ("a fifth", "four times", "can't fall"):
            self.assertNotIn(false, floor)
        self.assertIn("base death rate was left to take off", floor)
        measured = re.search(r'^ te_demog_st_ontop_tt_measured:0 "(.*)"$', loc, re.M).group(1)
        self.assertIn("'te_demog_st_ontop_end_floor', 'te_demog_st_ontop_end' )", measured)
        self.assertIn("'te_demog_st_ontop_end_floor_phi', 'te_demog_st_ontop_end_phi' )", measured)

    def test_the_private_insurance_note(self):
        """Private Health Insurance's wealth line can take the richest pops' deaths to 0; the walk leaves them out but
        the split takes off their unfloored share, so the hover says so under that law (owner, 2026-10-20)."""
        loc = _text(MISC_LOC)
        get = {k: v for k, v in re.findall(r'(?m)^ (\w+):\d* "(.*)"$', loc)}
        self.assertIn("te_demog_state_phi_note_sgui", get["te_demog_st_ontop_tt_measured"])
        for key, base in (("te_demog_st_ontop_end_phi", "te_demog_st_ontop_end"),
                          ("te_demog_st_ontop_end_floor_phi", "te_demog_st_ontop_end_floor")):
            self.assertEqual(get[key], f"${base}$\\n$te_demog_st_ontop_phi$")
        note = get["te_demog_st_ontop_phi"]
        self.assertIn("$law_private_health_insurance$", note)
        self.assertIn("stop dying altogether", note)
        for row in ("Other effects on some of its people", "Effects on the whole state"):   # the rows the hover prints
            self.assertIn(row, note)
            self.assertIn(row, get["te_demog_st_ontop_tt_measured"])
        self.assertTrue(note.startswith("#lore") and note.endswith("#!"))
        sgui = " ".join(_block(_text(ROOT / "common" / "scripted_guis" / "te_demog_sguis.txt"),
                               "te_demog_state_phi_note_sgui").split())
        self.assertIn("scope = state", sgui)
        self.assertIn("te_demog_effects_run = yes owner ?= { has_law = law_type:law_private_health_insurance }", sgui)

    def test_no_script_names_the_old_limits(self):
        for path in (RATE_EFFECTS, EFFECTS, ROOT / "common" / "script_values" / "te_demog_generated_values.txt"):
            text = _text(path)
            for gone in ("te_demog_k_rate_total_min", "te_demog_k_rate_term_max", "te_demog_k_on_top_scale_max"):
                self.assertNotIn(gone, text, (path.name, gone))

    def test_a_late_state_skips_the_calendar_estimate(self):
        """The late sweep's own count replaces the calendar estimate (te_demog_lx_cause_deaths), whose calendar ages
        put an immortal state's deaths dozens of times too high: with no ceiling on dz it could pass the fixed point."""
        begin = _block(_text(EFFECTS), "te_demog_step_begin")
        self.assertRegex(begin, r"if = \{\s*limit = \{ local_var:te_dg_lx_on = 0 \}\s*te_demog_cause_deaths_estimate = yes\s*\}")


if __name__ == "__main__":
    unittest.main()
