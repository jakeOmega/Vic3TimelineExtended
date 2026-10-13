"""Demographics phase 3, the late game (docs/superpowers/specs/2026-10-11-demographics-late-game-design.md).

The model's late-game section (scripts/analysis/demographics_model.py) against the census script that mirrors it
(common/scripted_effects/te_demog_lx_effects.txt with te_demog_lx_generated_effects.txt), through the registry test's
interpreter: a state's late step from the same ring on both sides, every slot, the pool, the bands' treated shares and
deficits, eligibility and cover, the life tables, the work figures and the conscription pool. And the model's own
behaviour against the design (§1.2-§1.5, §4.2): selection, ageing, the pull, joining, a ban, the seed.
"""

import dataclasses
import random
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
from test_demographics_registry import (  # noqa: E402
    EFFECTS, LX_EFFECTS, WORK_EFFECTS, _block, _CountryEngine, _Engine, _engine_for, _raw_blocks, _text)

N = P.RING_YEARS
YEAR, POP = 2100, 250000.0
# a state with an ageing carrier and the pull, Public Health Insurance (the public route), people at three wealth bands
BASE = M.Inputs(sol=30, literacy=0.95, urban_share=0.7, techs=frozenset({"medical_degrees"}),
                laws=frozenset({"law_protected_class", "law_public_health_insurance"}),
                wealth_bands={6: 30000.0, 10: 50000.0, 15: 20000.0}, lx_w=55.0)
LATE = {P.AGEING_RATE_TYPE: -0.25, P.REJUVENATION_TYPE: 0.0, P.ACCESS_TYPE: 0.3, P.DIFFUSION_TYPE: 0.2,
        "state_chronic_treatment_add": 0.4, "state_infection_treatment_add": 0.5}


def _inp(**mods):
    inp = dataclasses.replace(BASE)
    inp.mods = {**LATE, **mods}
    return inp


def _ring(inp, seed=1, pool=(30.0, 20.0), late=True):
    """A ring from the model's seed, with each adult band at a random treated share and deficit, a treated pool, and the
    state's eligibility and cover part-way (late=False: the model's seed as it is)."""
    ring = M.seed(inp, YEAR, POP)
    ring.f = [x * ring.scale / 1.02 for x in ring.f]
    ring.m = [x * ring.scale / 1.02 for x in ring.m]
    ring.scale = 1.02
    ring.f[(YEAR + 1) % N], ring.m[(YEAR + 1) % N] = 40.0, 25.0      # aged 149 now, folds at the step
    ring.f[(YEAR + 2) % N], ring.m[(YEAR + 2) % N] = 30.0, 20.0
    ring.pool_f, ring.pool_m, ring.pool_age = pool[0], pool[1], 152.5
    # the script holds no cohort under half a person (te_demog_age_slot drops it): neither does this ring
    for k in range(N):
        if ring.f[k] * ring.scale + ring.m[k] * ring.scale < 0.5:
            ring.f[k] = ring.m[k] = 0.0
    if late:
        rnd = random.Random(seed)
        for j in range(P.LX_BANDS):
            if ring.lx_s[j] is not None:
                ring.lx_s[j] = rnd.uniform(0.2, 0.9)
                ring.lx_d[j] = rnd.uniform(0.0, 12.0)
        ring.lx_ps, ring.lx_pd = 0.6, 40.0
        ring.lx_elig, ring.lx_cover, ring.lx_sbar = 0.5, 0.8, 0.55
    M._refresh_denominators(ring)
    ring.total = ring.people()
    return ring


def _engine(ring, inp, pop, war_dead=0.0, kills=0.0, migration=0.0):
    """The script's state with the ring's variables, its flows stubbed from the model's own formulas (the registry's
    TestCohortScript.step_both)."""
    prof = M.migrant_profile(inp)
    locals_ = {"te_dg_war_ff": min(0.5, war_dead * (1 - P.WAR_DEAD_MALE_SHARE) / ring.faw),
               "te_dg_war_fm": min(0.5, war_dead * P.WAR_DEAD_MALE_SHARE / ring.fam),
               "te_dg_kill": min(0.9, kills / ring.total),
               "te_dg_mig_in": max(migration, 0.0), "te_dg_mig_out": max(-migration, 0.0)}
    for c in range(len(P.MIGRANT_CLASSES)):
        locals_[f"te_dg_pf{c}"], locals_[f"te_dg_pm{c}"] = prof[(c, "f")], prof[(c, "m")]
    # te_demog_enter_class now reads the booking rates generated from the same profile and class sums.
    stub = {"te_demog_flows": "\n".join(
        [f"set_local_variable = {{ name = {k} value = {v!r} }}" for k, v in locals_.items()]
        + ["te_demog_migrant_rates = yes"])}
    eng = _engine_for(inp, YEAR + 1, pop, effects=stub)
    for k in range(N):
        if ring.f[k] or ring.m[k]:
            eng.vars[f"te_dg_f{k}"], eng.vars[f"te_dg_m{k}"] = ring.f[k], ring.m[k]
    eng.vars.update(te_dg_pf=ring.pool_f, te_dg_pm=ring.pool_m, te_dg_pa=ring.pool_age, te_dg_scale=ring.scale,
                    te_dg_year=float(YEAR), te_dg_people=ring.total, te_dg_raw=ring.total / ring.scale,
                    te_dg_sex_balance=M.structure(ring)["men_per_100_women"], te_dg_faw=ring.faw, te_dg_fam=ring.fam)
    for c in range(len(P.MIGRANT_CLASSES)):
        eng.vars[f"te_dg_cf{c}"], eng.vars[f"te_dg_cm{c}"] = ring.class_f[c], ring.class_m[c]
    for j in range(P.LX_BANDS):
        if ring.lx_s[j] is not None:
            eng.vars[f"te_dg_s{j}"], eng.vars[f"te_dg_d{j}"] = ring.lx_s[j], ring.lx_d[j]
    for name, value in (("te_dg_lx_ps", ring.lx_ps), ("te_dg_lx_pd", ring.lx_pd), ("te_dg_elig", ring.lx_elig),
                        ("te_dg_cover", ring.lx_cover), ("te_dg_lx_sbar", ring.lx_sbar)):
        if value is not None:
            eng.vars[name] = value
    return eng


class TestLateGameScript(unittest.TestCase):
    """te_demog_step with the late sweep against demographics_model.step's late path."""

    def close(self, got, want, rel=1e-8, what=""):
        self.assertLessEqual(abs(got - want), rel * max(abs(want), 1.0), f"{what}: {got} vs {want}")

    def step_both(self, inp, ring=None, **flows):
        ring = ring or _ring(inp)
        pop = ring.total * 1.004
        eng = _engine(ring, inp, pop, **flows)
        eng.call("te_demog_step")
        out = M.step(ring, inp, YEAR + 1, engine_pop=pop, war_dead=flows.get("war_dead", 0.0),
                     kills=flows.get("kills", 0.0), migration=flows.get("migration", 0.0))
        return eng, ring, out

    def check(self, eng, ring, out, rel=1e-8):
        self.close(eng.vars["te_dg_births"], out["births"], rel, "births")
        self.close(eng.vars["te_dg_deaths"], out["deaths"], rel, "deaths")
        for k in range(N):
            if f"te_dg_f{k}" not in eng.vars:
                self.assertTrue(ring.f[k] < 0.5 and ring.m[k] < 0.5, f"slot {k} dropped with people")
                continue
            self.close(eng.vars[f"te_dg_f{k}"], ring.f[k], rel, f"women in slot {k}")
            self.close(eng.vars[f"te_dg_m{k}"], ring.m[k], rel, f"men in slot {k}")
        self.close(eng.vars["te_dg_pf"], ring.pool_f, rel, "pool women")
        self.close(eng.vars["te_dg_pm"], ring.pool_m, rel, "pool men")
        self.close(eng.vars["te_dg_pa"], ring.pool_age, rel, "pool age")
        for j in range(P.LX_BANDS):
            if ring.lx_s[j] is None:
                self.assertNotIn(f"te_dg_s{j}", eng.vars, f"band {j}'s share")
                self.assertNotIn(f"te_dg_d{j}", eng.vars, f"band {j}'s deficit")
                continue
            self.close(eng.vars[f"te_dg_s{j}"], ring.lx_s[j], rel, f"band {j}'s share")
            self.close(eng.vars[f"te_dg_d{j}"], ring.lx_d[j], rel, f"band {j}'s deficit")
        if ring.lx_ps is None:
            self.assertNotIn("te_dg_lx_ps", eng.vars)
        else:
            self.close(eng.vars["te_dg_lx_ps"], ring.lx_ps, rel, "pool's share")
            self.close(eng.vars["te_dg_lx_pd"], ring.lx_pd, rel, "pool's deficit")
        self.close(eng.vars["te_dg_mab"], out["mab"], 1e-8, "the mean age at childbirth")
        if out["lx"].get("b50"):
            self.close(eng.vars["te_dg_lx_b50"], out["lx"]["b50"], 1e-8, "births to women of 50 and over")
        else:
            self.assertNotIn("te_dg_lx_b50", eng.vars)
        lx = out["lx"]
        for name, want in (("te_dg_elig", lx["elig"]), ("te_dg_cover", lx["cover"]), ("te_dg_lx_sbar", lx["sbar"]),
                           ("te_dg_age_rate", lx["rr"]), ("te_dg_lx_pub", lx["pub"]),
                           ("te_dg_e0", lx["blend"]["e0"]), ("te_dg_e0f", lx["blend"]["e0_f"]),
                           ("te_dg_e65", lx["blend"]["e65"]), ("te_dg_old_age", lx["blend"]["old_age"]),
                           ("te_dg_old_age_c", lx["untreated"]["old_age"]), ("te_dg_lx_l100", lx["blend"]["l100"]),
                           ("te_dg_lx_l100t", lx["treated"]["l100"]), ("te_dg_lx_l100u", lx["untreated"]["l100"]),
                           ("te_dg_lx_rho", lx["rho"]), ("te_dg_lx_slope", lx["slope"]), ("te_dg_lx_mbar", lx["mbar"])):
            self.close(eng.vars[name], want, 1e-6, name)
        # the biological pyramid's moves from the calendar one (the script's bands leave out the cohorts it dropped, each
        # under half a person: TestCohortScript checks the calendar bands)
        bio_f, bio_m = lx["bio_bands"]
        cal_f, cal_m = [0.0] * P.BANDS, [0.0] * P.BANDS
        for a, f, m in ring.by_age():
            cal_f[M.lx_band_of(a)] += f
            cal_m[M.lx_band_of(a)] += m
        for b in range(P.BANDS):
            for s, bio, cal in (("f", bio_f, cal_f), ("m", bio_m, cal_m)):
                got = eng.vars[f"te_dg_bb{s}{b}"] - eng.vars[f"te_dg_b{s}{b}"]
                self.assertLess(abs(got - (bio[b] - cal[b])), 1.0, f"biological band {b} ({s}): {got} vs {bio[b] - cal[b]}")
                self.assertGreaterEqual(eng.vars["te_dg_pyr_max"], eng.vars[f"te_dg_bb{s}{b}"])
        # the mean ages: the model keeps the cohorts the script drops under half a person
        self.close(eng.vars["te_dg_lx_age"], lx["mean_age"], 1e-5, "mean age")
        self.close(eng.vars["te_dg_lx_bio"], lx["mean_bio"], 1e-5, "mean biological age")
        # the conscription pool's sums, before the new scale (the script's raw total leaves out the cohorts it dropped)
        self.close(eng.vars["te_dg_fam"] / eng.vars["te_dg_scale"], ring.fam / ring.scale, 1e-8, "the pool's men")
        self.close(eng.vars["te_dg_faw"] / eng.vars["te_dg_scale"], ring.faw / ring.scale, 1e-8, "the pool's women")

    def work(self, eng, ring, inp):
        qf, qm, _ = M.group_rates(dataclasses.replace(inp, medicine=ring.medicine))
        want = M.work_figures(ring, inp, M.old_age(qf, qm))
        for name in ("wa_share", "at_work", "pensioners", "need"):
            self.close(eng.vars[f"te_dg_{name}"], want[name], 1e-5, name)

    def test_a_late_step_matches_the_model(self):
        inp = _inp()
        eng, ring, out = self.step_both(inp)
        self.check(eng, ring, out)
        self.work(eng, ring, inp)
        self.assertGreater(out["lx"]["treated"]["l100"], out["lx"]["untreated"]["l100"])

    def test_immortality_with_the_pull(self):
        inp = _inp(**{P.AGEING_RATE_TYPE: -1.0, P.REJUVENATION_TYPE: 0.03})
        eng, ring, out = self.step_both(inp)
        self.check(eng, ring, out)
        self.work(eng, ring, inp)

    def test_artificial_wombs(self):
        """Ectogenesis (§3.5): a share of planned births from women and men alike, with no maternal death."""
        inp = dataclasses.replace(_inp(), ecto_levels=3.0)
        ring = _ring(inp)
        ring.births = 4000.0
        eng = _engine(ring, inp, ring.total * 1.004)
        eng.vars["te_dg_births"] = 4000.0
        eng.call("te_demog_step")
        out = M.step(ring, inp, YEAR + 1, engine_pop=ring.total * 1.004)
        self.assertAlmostEqual(out["lx"]["ecto"], 0.75)
        self.check(eng, ring, out)

    def test_immortal_women_bear_children_past_50(self):
        """Unplanned births follow the body (§3.1): treated women of calendar 50 and over with young bodies bear some."""
        inp = _inp(**{P.AGEING_RATE_TYPE: -1.0, P.REJUVENATION_TYPE: 0.03})
        ring = _ring(inp)
        for j in range(P.LX_BANDS):
            if ring.lx_s[j] is not None and (YEAR - P.LX_BAND_WIDTH * j - 4) % N >= 60:   # bands of 60 and over
                ring.lx_d[j] = 30.0
        eng, ring, out = self.step_both(inp, ring=ring)
        self.check(eng, ring, out)
        self.assertGreater(out["lx"]["b50"], 0.0)

    def test_with_war_kills_and_migrants(self):
        inp = _inp()
        for flows in (dict(war_dead=900.0, kills=1500.0, migration=4000.0),
                      dict(war_dead=500.0, migration=-3000.0)):
            eng, ring, out = self.step_both(inp, **flows)
            self.check(eng, ring, out)

    def test_eligibility_falling_and_rising(self):
        """Cover falls with eligibility (a ban: Human Purity) and returns before anyone new joins (§1.2)."""
        banned = dataclasses.replace(_inp(), laws=BASE.laws | {P.LX_BAN_LAW})
        eng, ring, out = self.step_both(banned)
        self.check(eng, ring, out)
        self.assertLess(out["lx"]["cover"], 0.8)
        self.assertEqual(out["lx"]["phi"], 0.0)
        rich = dataclasses.replace(_inp(), wealth_bands={30: 100000.0}, lx_w=20.0)
        eng, ring, out = self.step_both(rich)
        self.check(eng, ring, out)
        self.assertEqual(out["lx"]["cover"], 1.0)
        self.assertGreater(out["lx"]["phi"], 0.0)

    def test_the_first_late_step(self):
        """A state whose owner has just researched the first carrier: no bands, eligibility from 0."""
        inp = _inp()
        ring = _ring(inp, late=False)
        ring.lx_s, ring.lx_d = [None] * P.LX_BANDS, [None] * P.LX_BANDS
        ring.lx_ps = ring.lx_pd = ring.lx_elig = ring.lx_cover = ring.lx_sbar = None
        eng, ring, out = self.step_both(inp, ring=ring)
        self.check(eng, ring, out)
        self.assertGreater(sum(1 for s in ring.lx_s if s), 15)   # the adult bands with people

    def test_mandatory_and_unrestricted(self):
        for law in (P.LX_MANDATORY_LAW, P.LX_UNRESTRICTED_LAW):
            inp = dataclasses.replace(_inp(), laws=BASE.laws | {law})
            eng, ring, out = self.step_both(inp)
            self.check(eng, ring, out)

    def test_the_seed(self):
        """A seed once ageing is slowed (§1.2): its adults survive with the treated at the rate's steady biological age,
        and each band starts at E and its steady deficit."""
        inp = _inp(**{P.AGEING_RATE_TYPE: -0.5})
        eng = _engine_for(inp, YEAR, POP)
        eng.call("te_demog_seed")
        # the script reads the growth factor from a table of growth_factor; the model takes the same d
        with unittest.mock.patch.object(M, "growth_factor", lambda nrr: eng.locals["te_dg_d"]):
            ring = M.seed(inp, YEAR, POP)
        plain = M.seed(_inp(**{P.AGEING_RATE_TYPE: 0.0}), YEAR, POP)
        for a, f, m in ring.by_age()[:-1]:
            k = (YEAR - a) % N
            if f"te_dg_f{k}" not in eng.vars:
                self.assertLess(f + m, 1e-5 * POP, f"age {a} left empty")
                continue
            self.close(eng.vars[f"te_dg_f{k}"], f, 1e-4, f"women aged {a}")
            self.close(eng.vars[f"te_dg_m{k}"], m, 1e-4, f"men aged {a}")
        old_share = sum(f + m for a, f, m in ring.by_age()[:-1] if a >= 80) / POP
        self.assertGreater(old_share, sum(f + m for a, f, m in plain.by_age()[:-1] if a >= 80) / POP,
                           "the treated live longer, so the seed holds more old people")
        target, pub = M.lx_targets(inp)
        self.close(eng.vars["te_dg_elig"], target, 1e-9, "eligibility")
        self.assertEqual(eng.vars["te_dg_cover"], 1)
        for j in range(P.LX_BANDS):
            if ring.lx_s[j] is None:
                self.assertNotIn(f"te_dg_s{j}", eng.vars)
            else:
                self.close(eng.vars[f"te_dg_s{j}"], ring.lx_s[j], 1e-9, f"band {j}")
                self.close(eng.vars[f"te_dg_d{j}"], ring.lx_d[j], 1e-9, f"band {j}'s deficit")

    def test_no_carrier_takes_the_plain_sweep(self):
        """Before the first carrier nothing of the late game runs: no variable, the plain sweep."""
        inp = _inp(**{P.AGEING_RATE_TYPE: 0.0})
        ring = _ring(inp, late=False)
        eng, ring, out = self.step_both(inp, ring=ring)
        self.assertEqual(out["lx"], {})
        for name in ("te_dg_elig", "te_dg_cover", "te_dg_s5", "te_dg_lx_l100", "te_dg_old_age_c"):
            self.assertNotIn(name, eng.vars)


class TestLateGameModel(unittest.TestCase):
    """The model against the design's rules."""

    def run_years(self, inp, years, ring=None):
        ring = ring or M.seed(inp, YEAR, 1_000_000)
        out = None
        for y in range(ring.year + 1, ring.year + 1 + years):
            out = M.step(ring, inp, y)
        return ring, out

    def test_selection_raises_the_treated_share_with_age(self):
        """The untreated die faster, so the old become more treated (§1.2's step 2)."""
        inp = _inp(**{P.AGEING_RATE_TYPE: -0.25})
        inp = dataclasses.replace(inp, wealth_bands={6: 1.0}, lx_w=200.0)   # half the public route, no market
        ring, _out = self.run_years(inp, 40)
        young = ring.lx_s[M.lx_band((ring.year - 32) % N)]
        old = ring.lx_s[M.lx_band((ring.year - 87) % N)]
        self.assertGreater(old, young)

    def test_a_ban_keeps_the_bodies_age(self):
        """Losing care: bodies keep their deficit and age at 1 from where they are (call 9), no snap back."""
        inp = _inp(**{P.AGEING_RATE_TYPE: -1.0, P.REJUVENATION_TYPE: 0.03})
        ring, _ = self.run_years(inp, 30)
        j = M.lx_band((ring.year - 70) % N)
        before = ring.lx_d[j]
        banned = dataclasses.replace(inp, laws=inp.laws | {P.LX_BAN_LAW})
        ring, out = self.run_years(banned, 5, ring)
        self.assertLess(out["lx"]["cover"], 1.0)
        self.assertGreater(ring.lx_d[j], before * 0.9)

    def test_immortality_holds_the_body(self):
        """r = 0 with the pull: a treated band's biological age falls toward 35 and stays (§1.4)."""
        inp = _inp(**{P.AGEING_RATE_TYPE: -1.0, P.REJUVENATION_TYPE: 0.03})
        inp = dataclasses.replace(inp, wealth_bands={40: 1.0}, lx_w=0.0)
        ring, out = self.run_years(inp, 60)
        j = M.lx_band((ring.year - 102) % N)
        self.assertLess(102 - ring.lx_d[j], 60)
        self.assertGreater(out["lx"]["treated"]["l100"], 2 * out["lx"]["untreated"]["l100"])
        self.assertGreaterEqual(out["lx"]["blend"]["old_age"], P.LX_OLD_AGE_NONE)

    def test_inert_before_the_carrier(self):
        """No carrier: the late path never runs and the step is the census's as before."""
        inp = _inp(**{P.AGEING_RATE_TYPE: 0.0})
        ring, out = self.run_years(inp, 3)
        self.assertEqual(out["lx"], {})
        self.assertIsNone(ring.lx_elig)

    def test_access_routes(self):
        """§4.2's table: the public route by the health law's cover; the market by wealth against the threshold."""
        inp = dataclasses.replace(_inp(), wealth_bands={2: 50.0, 21: 50.0}, lx_w=80.0)
        acc = M.medicine_targets(inp)["access"]
        target, pub = M.lx_targets(inp)
        self.assertAlmostEqual(pub, acc)
        self.assertAlmostEqual(target, 0.5 * acc + 0.5 * max(acc, M.lx_market(P.LX_BAND_WEALTH[21], 80.0)))
        private = dataclasses.replace(inp, laws=frozenset({"law_private_health_insurance"}))
        self.assertEqual(M.lx_targets(private)[1], 0.0)
        self.assertEqual(M.lx_targets(dataclasses.replace(inp, laws=inp.laws | {P.LX_BAN_LAW})), (0.0, 0.0))
        self.assertGreaterEqual(M.lx_targets(dataclasses.replace(inp, laws=inp.laws | {P.LX_MANDATORY_LAW}))[0],
                                P.LX_MANDATORY_FLOOR)
        self.assertGreater(M.lx_targets(dataclasses.replace(inp, laws=inp.laws | {P.LX_UNRESTRICTED_LAW}))[0],
                           M.lx_targets(private)[0])

    def test_the_market_threshold_falls(self):
        self.assertEqual(M.lx_market_next(None), P.LX_MARKET_START)
        self.assertEqual(M.lx_market_next(80.0), 80.0 - P.LX_MARKET_FALL)
        self.assertEqual(M.lx_market_next(80.0, laws={"law_private_health_insurance"}), 78.0)
        self.assertEqual(M.lx_market_next(P.LX_MARKET_FLOOR), P.LX_MARKET_FLOOR)


class TestWealthSlope(unittest.TestCase):
    """Rich pops really die less (§4.3, call 14): the slope of each wealth band's multiplier against wealth, on the census's
    own Deaths by Wealth pair, M netting what it moves so the state's total stays the census's."""

    POP = 1_000_000.0

    ED0 = 8.0 * 1_000_000 * 100 / 12          # the bare deaths: 8 per 1,000 a year (the census's target: 4)

    def refresh(self, slope, mbar, rho, edw, wtop, line=0.0):
        ed0 = self.ED0
        eng = _Engine({"state_population": self.POP, "modifier:state_birth_rate_mult": 0.05,
                       "modifier:state_mortality_mult": 0.04,
                       **{f"modifier:{n}": 0.0 for n in P.ENGINE_LINE_TYPES.values()},
                       "modifier:state_demog_ontop_mortality_wealth_mult": line},
                      triggers={"te_demog_effects_run": True, "te_demog_cohorts_run": True})
        eng.locals.update(te_dg_w_eb0=475e6, te_dg_w_ed0=ed0, te_dg_w_ebr=0.0, te_dg_w_edr=0.0, te_dg_w_eb=475e6,
                          te_dg_w_ed=ed0, te_dg_w_eb0m=475e6, te_dg_w_ed0m=ed0, te_dg_w_sev=0.0, te_dg_w_sevd=0.0,
                          te_dg_w_edw=edw, te_dg_w_wtop=wtop)
        eng.vars.update(te_dg_stepped=1.0, te_dg_cbr_model=10.0, te_dg_cdr_model=4.0, te_dg_lx_slope=slope,
                        te_dg_lx_mbar=mbar, te_dg_lx_rho=rho)
        eng.call("te_demog_rates_refresh")
        return eng, ed0

    def test_the_slope_nets_out_and_the_richest_are_held(self):
        ed0, wbar = self.ED0, 40.0
        for slope, wtop in ((-0.004, 120.0), (-0.02, 150.0)):
            eng, ed0 = self.refresh(slope, 0.6, 0.1, wbar * ed0, wtop)
            target = 4.0 * self.POP * 100 / 12
            tb = target / ed0
            held = M.lx_wealth_term(slope, 0.6, 0.1, wbar, wtop)
            md, _ = M.rate_term(target, ed0, absorbed=held * tb * wbar * ed0, other=0.04, on_top=0.04)
            self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
            self.assertAlmostEqual(eng.vars["te_dg_w"], (P.WEALTH_LINE_FLOOR * 0 + held) * tb, places=6)
            # the richest pop's rate on the census's: 1 + slope x (its wealth - the mean), at least the treated's
            self.assertGreaterEqual(1 + held * (wtop - wbar), 0.1 / 0.6 - 1e-9)
            # the state's total stays the census's: the bare curves x (1 + M + wealth x W), summed, is the target
            total = ed0 * (1 + eng.vars["te_dg_md"] + 0.04) + eng.vars["te_dg_w"] * wbar * ed0
            self.assertAlmostEqual(total, target * 1.04, delta=target * 1e-4)
        self.assertLess(M.lx_wealth_term(-0.02, 0.6, 0.1, wbar, 150.0), 0)
        self.assertGreater(M.lx_wealth_term(-0.02, 0.6, 0.1, wbar, 150.0), -0.02, "the hold binds")

    def test_no_late_game_no_slope(self):
        eng = _Engine({"state_population": self.POP, "modifier:state_birth_rate_mult": 0.05,
                       "modifier:state_mortality_mult": 0.04, **{f"modifier:{n}": 0.0 for n in P.ENGINE_LINE_TYPES.values()}},
                      triggers={"te_demog_effects_run": True, "te_demog_cohorts_run": True})
        eng.locals.update(te_dg_w_eb0=475e6, te_dg_w_ed0=430e6, te_dg_w_ebr=0.0, te_dg_w_edr=0.0, te_dg_w_eb=475e6,
                          te_dg_w_ed=430e6, te_dg_w_eb0m=475e6, te_dg_w_ed0m=430e6, te_dg_w_sev=0.0, te_dg_w_sevd=0.0)
        eng.vars.update(te_dg_stepped=1.0, te_dg_cbr_model=10.0, te_dg_cdr_model=4.0)
        eng.call("te_demog_rates_refresh")
        self.assertAlmostEqual(eng.vars["te_dg_w"], P.WEALTH_LINE_FLOOR * 0, places=9)

    def test_the_model_slope(self):
        """A rich minority within reach: its multiplier is rho's share lower, so the slope is negative."""
        inp = dataclasses.replace(_inp(), laws=frozenset({"law_private_health_insurance"}),
                                  wealth_bands={2: 800.0, 30: 200.0}, lx_w=100.0)
        slope, mbar = M.lx_wealth_slope(inp, 0.2, 0.25)
        self.assertLess(slope, 0)
        self.assertAlmostEqual(mbar, 0.8 * 1 + 0.2 * 0.25)
        self.assertEqual(M.lx_wealth_slope(dataclasses.replace(inp, laws=inp.laws | {P.LX_BAN_LAW}), 0.2, 0.25),
                         (0.0, 1.0))


class TestGapPolitics(unittest.TestCase):
    """§4.4, call 15: built behind demographics_params.LONGEVITY_POLITICS, off until a play-test sizes it."""

    def test_off_applies_nothing(self):
        self.assertFalse(P.LONGEVITY_POLITICS)
        eng = _Engine({}, triggers={"te_demog_effects_run": True})
        eng.vars.update(te_dg_lx_l100t=0.8, te_dg_lx_l100u=0.3)
        eng.modifiers["te_demog_lx_gap_labor"] = 0.4      # a game that had it on: it goes
        eng.call("te_demog_lx_politics_refresh")
        self.assertEqual(eng.modifiers, {})

    def test_on_applies_the_gap(self):
        eng = _Engine({"te_demog_k_lx_politics": 1.0}, triggers={"te_demog_effects_run": True})
        eng.vars.update(te_dg_lx_l100t=0.8, te_dg_lx_l100u=0.3)
        eng.call("te_demog_lx_politics_refresh")
        self.assertAlmostEqual(eng.modifiers["te_demog_lx_gap_labor"], 0.5)
        eng.trigger_fixtures["te_demog_effects_run"] = False
        eng.call("te_demog_lx_politics_refresh")
        self.assertEqual(eng.modifiers, {}, "outside Full nothing")

    def test_the_sizes(self):
        mods = _raw_blocks([ROOT / "common" / "static_modifiers" / "te_demog_lx_modifiers.txt"])
        self.assertIn(f"interest_group_ig_trade_unions_approval_add = {P.LX_POLITICS_APPROVAL}", mods["te_demog_lx_gap_politics"])
        self.assertIn(f"interest_group_ig_rural_folk_approval_add = {P.LX_POLITICS_APPROVAL}", mods["te_demog_lx_gap_politics"])
        self.assertIn(f"state_pop_support_movement_labor_mult = {P.LX_POLITICS_LABOR}", mods["te_demog_lx_gap_labor"])


class TestLateGameHarness(unittest.TestCase):
    """demographics_harness.py lategame (demographics_late.py): the band model against the per-cohort truth (§1.3) and the
    design's bands."""

    @classmethod
    def setUpClass(cls):
        import demographics_late as L
        cls.L = L
        cls.carriers, cls.lines = L._carriers()
        cls.start = L.start_ring(L.scenarios_base(cls.carriers, cls.lines))

    def test_the_bands_track_the_truth(self):
        """§1.3, call 8: a share and a deficit per band tracks the per-cohort truth (here within 0.1 per 1,000)."""
        for techs, share in ((self.L.ERA12, 0.2), (self.L.ERA11, 0.5)):
            inp = self.L._share_inputs(self.carriers, self.lines, techs, share)
            d_band, x_band = self.L.band_model(inp, share, self.start, years=30)
            d_truth, x_truth = self.L.truth(inp, share, self.start, years=30)
            self.assertLess(abs(d_band - d_truth), 0.1, (share, d_band, d_truth))
            self.assertLess(abs(x_band / x_truth - 1), 0.01, (share, x_band, x_truth))

    def test_the_command_meets_its_bands(self):
        import argparse
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = self.L.main(argparse.Namespace(years=60))
        self.assertEqual(code, 0, out.getvalue())


class TestLateGameCountry(unittest.TestCase):
    """The country's late figures (people-weighted), the health bill's longevity-care term (§5.2), Linked to Common
    Longevity on the untreated's threshold (§2.2), the AI's push from the gap, and the market threshold (§4.2)."""

    def test_people_weighted(self):
        states = [dict(te_dg_people=2_000_000.0, te_dg_elig=0.8, te_dg_lx_pub=0.6, te_dg_lx_l100=0.5,
                       te_dg_lx_l100t=0.7, te_dg_lx_l100u=0.2, te_dg_old_age_c=80.0, te_dg_lx_age=50.0, te_dg_lx_bio=40.0),
                  dict(te_dg_people=1_000_000.0, te_dg_elig=0.2, te_dg_lx_pub=0.1, te_dg_lx_l100=0.3,
                       te_dg_lx_l100t=0.6, te_dg_lx_l100u=0.1, te_dg_old_age_c=74.0, te_dg_lx_age=40.0, te_dg_lx_bio=38.0),
                  dict(te_dg_people=5_000_000.0)]                    # before the late game: left out
        for s in states:
            for b in range(P.BANDS):
                s[f"te_dg_bf{b}"], s[f"te_dg_bm{b}"] = 100.0, 90.0
        states[0].update({f"te_dg_bb{x}{b}": 150.0 for b in range(P.BANDS) for x in "fm"})
        blocks = _raw_blocks([LX_EFFECTS])
        body = (blocks["te_demog_lx_country_init"]
                + "\nevery_scope_state = { set_local_variable = { name = te_dg_c_s_pm value = { value = var:te_dg_people"
                " divide = 1000000 } } te_demog_lx_country_add = yes }\n" + blocks["te_demog_lx_country_store"]
                + "\nte_demog_lx_country_bio_store = yes")
        eng = _CountryEngine(states=states, fixtures={}, effects={"te_test": body})
        eng.vars["te_dg_pyr_max"] = 0.0
        eng.call("te_test")
        self.assertAlmostEqual(eng.vars["te_dg_elig"], (0.8 * 2 + 0.2) / 3, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_lx_l100t"], (0.7 * 2 + 0.6) / 3, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_old_age_c"], (80 * 2 + 74) / 3, places=4)
        self.assertAlmostEqual(eng.vars["te_dg_lx_bio"], (40 * 2 + 38) / 3, places=4)
        # the biological pyramid: the late state's own bands, the others' calendar ones
        self.assertAlmostEqual(eng.vars["te_dg_cbbf3"], 150.0 + 100.0 + 100.0)
        self.assertAlmostEqual(eng.vars["te_dg_pyr_max"], 350.0)

    def test_no_late_state_no_figures(self):
        blocks = _raw_blocks([LX_EFFECTS])
        body = blocks["te_demog_lx_country_init"] + "\n" + blocks["te_demog_lx_country_store"]
        eng = _CountryEngine(states=[], fixtures={}, effects={"te_test": body})
        eng.vars.update(te_dg_elig=0.5, te_dg_lx_l100=0.4, te_dg_lx_l100t=0.5, te_dg_lx_l100u=0.3)
        eng.call("te_test")
        self.assertNotIn("te_dg_elig", eng.vars)
        self.assertNotIn("te_dg_lx_l100", eng.vars)

    def test_the_health_bill_pays_for_public_longevity_care(self):
        fixtures = {"gdp": 52_000_000.0, '"institution_investment_level(institution_social_security)"': 5.0,
                    "te_demog_health_tech_term": 0.15, "income": 300_000.0}
        eng = _Engine(fixtures, triggers={"te_demog_effects_run": True, "te_demog_has_pension_law": False})
        eng.vars.update(te_dg_need=1.2, te_dg_lx_pub=0.9, te_dg_elig=0.6)
        eng.call("te_demog_bills_refresh")
        want = M.health_term(1.2, frozenset(P.HEALTH_TECHS), lx_public=0.9, lx_elig=0.6)
        self.assertAlmostEqual(eng.vars["te_dg_health_term"], want, places=5)
        self.assertAlmostEqual(want, P.HEALTH_NEED_WEIGHT * 0.2 + 0.15 + 0.6 * P.LX_PUBLIC_HEALTH_WEIGHT)

    def test_linked_to_common_follows_the_untreated(self):
        eng = _Engine({"te_demog_ms_now": 2100.0}, triggers={"te_demog_effects_run": True,
                                                             "te_demog_has_pension_law": True})
        eng.vars.update(te_dg_old_age=130.0, te_dg_old_age_c=88.0, te_dg_pension_age=80.0,
                        te_dg_pension_pos=float(P.PENSION_POSITION_ID["linked_common"]))
        target = eng.value(eng._tree(eng.values, "te_demog_pension_link_target"))
        self.assertEqual(target, M.pension_position_age("linked_common", None, 88.0))
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_pension_link_target_average")), 125.0)
        eng.call("te_demog_pension_link_drift")
        self.assertEqual(eng.vars["te_dg_pension_age"], 81.0)
        del eng.vars["te_dg_old_age_c"]           # before anyone is treated: the two follow one table
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_pension_link_target")), 125.0)

    def _ai(self, gap, **vars_):
        fixtures = {"te_demog_ms_now": 2100.0, "te_demog_pension_bill_share": 0.1, "scaled_debt": 0.0,
                    "te_demog_country_unemployment": 0.02}
        eng = _Engine(fixtures, triggers={"te_demog_effects_run": True, "te_demog_has_pension_law": True, "is_ai": True,
                                          "in_default": False})
        eng.vars.update(te_dg_old_age=90.0, te_dg_pension_age=65.0, te_dg_lx_l100t=0.5 + gap, te_dg_lx_l100u=0.5,
                        **vars_)
        eng.call("te_demog_pension_ai")
        return eng

    def test_a_wide_gap_picks_linked_to_common(self):
        self.assertEqual(self._ai(0.3).vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["linked_common"])
        self.assertNotIn("te_dg_pension_pos", self._ai(0.15).vars)
        common = dict(te_dg_pension_pos=float(P.PENSION_POSITION_ID["linked_common"]), te_dg_pension_since=2080.0)
        self.assertEqual(self._ai(0.15, **common).vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["linked_common"])
        self.assertEqual(self._ai(0.05, **common).vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["standard"])

    def test_the_market_threshold(self):
        eng = _Engine({"te_demog_lx_country_carrier": 1.0, "te_demog_lx_market_diffusion": 0.2,
                       "te_demog_lx_market_laws": 2.0}, triggers={})
        eng.call("te_demog_lx_market_step")
        self.assertEqual(eng.vars["te_dg_lx_w"], P.LX_MARKET_START)
        eng.call("te_demog_lx_market_step")
        self.assertAlmostEqual(eng.vars["te_dg_lx_w"],
                               M.lx_market_next(float(P.LX_MARKET_START), {"law_private_health_insurance"}, 0.2))
        eng.fixtures["te_demog_lx_country_carrier"] = 0.0
        eng.vars["te_dg_lx_w"] = 10.0
        eng.call("te_demog_lx_market_step")
        self.assertEqual(eng.vars["te_dg_lx_w"], 10.0, "it falls only once the country has a carrier")

    def test_the_wiring(self):
        yearly = _block(_text(EFFECTS), "te_demog_country_yearly")
        self.assertIn("te_demog_lx_market_step = yes", yearly)
        census = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertLess(census.index("te_demog_lx_country_store = yes"), census.index("te_demog_work_country_store = yes"),
                        "the health bill reads the country's late figures")
        begin = _block(_text(EFFECTS), "te_demog_step_begin")
        self.assertLess(begin.index("te_demog_prepare = yes"), begin.index("te_demog_lx_begin = yes"))
        self.assertLess(begin.index("te_demog_lx_begin = yes"), begin.index("te_demog_on_top_scales = yes"),
                        "the age groups' own rates before the step's scales")
        self.assertIn("te_demog_pension_link_target_average", _block(_text(WORK_EFFECTS), "te_demog_pension_ai"))


if __name__ == "__main__":
    unittest.main()
