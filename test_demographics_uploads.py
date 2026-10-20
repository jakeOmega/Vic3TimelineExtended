"""Demographics: uploaded minds (docs/superpowers/specs/2026-10-16-demographics-uploaded-minds-design.md; the owner's calls
of 2026-10-19).

The model (scripts/analysis/demographics_uploads.py, its call sites in demographics_model.step) against the census script
that mirrors it (common/scripted_effects/te_demog_um_effects.txt with te_demog_um_generated_effects.txt), through the
registry test's interpreter: a late step under Full with uploads (the eligible deaths, the uploads, the owner's pool and
free capacity, Living to 100 counting uploads), Mind Backups' restore scaled by longevity care, and the country's year
(endings, capacity, archive and restore, the year's share). Then the model's own transitions, the Nexus's modifiers
against the parameters, the wiring, and the harness scenario.
"""

import dataclasses
import functools
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_uploads as U  # noqa: E402
from test_demographics_late import DC_SLICES, POP, YEAR, _inp, _ring  # noqa: E402
from test_demographics_registry import _CountryEngine, _Engine, _engine_for  # noqa: E402

N = P.RING_YEARS
UM_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_um_effects.txt"
UM_VALUES = ROOT / "common" / "script_values" / "te_demog_um_values.txt"
UM_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_um_modifiers.txt"


class _UmEngine(_Engine):
    """_Engine with an owner: owner = { } runs on the owner's variables, owner = { } and owner ?= { } as triggers test
    them, and owner.var:X reads them; locals are the effect's."""

    def __init__(self, fixtures, owner_vars=None, **kwargs):
        super().__init__(fixtures, **kwargs)
        self.owner_vars = {} if owner_vars is None else owner_vars

    def _on_owner(self, fn, *args):
        saved, self.vars = self.vars, self.owner_vars
        try:
            return fn(*args)
        finally:
            self.vars = saved

    def number(self, tok):
        if tok.startswith("owner."):
            return self._on_owner(self.number, tok[6:])
        return super().number(tok)

    def _test(self, key, op, arg):
        if key == "owner":
            return self._on_owner(self.holds, arg)
        if key == "exists" and arg == "owner":
            return True
        return super()._test(key, op, arg)

    def run(self, items):
        batch = []
        for item in items:
            if item[0] == "owner":
                super().run(batch)
                batch = []
                self._on_owner(self.run, item[2])
            else:
                batch.append(item)
        super().run(batch)


def _engine(ring, inp, pop, owner_vars, full=True, real_multipliers=False, truncate=False):
    """The late test's state (test_demographics_late._engine) with an owner and the rule at Full. The multipliers'
    fixtures take Mind Backups' restore at the ring's E, as the model's step does."""
    prof = M.migrant_profile(inp)
    locals_ = {"te_dg_war": 0.0, "te_dg_kills": 0.0, "te_dg_war_ff": 0.0, "te_dg_war_fm": 0.0, "te_dg_kill": 0.0,
               "te_dg_mig_in": 0.0, "te_dg_mig_out": 0.0}
    for c in range(len(P.MIGRANT_CLASSES)):
        locals_[f"te_dg_pf{c}"], locals_[f"te_dg_pm{c}"] = prof[(c, "f")], prof[(c, "m")]
    stub = {"te_demog_flows": "\n".join(
        [f"set_local_variable = {{ name = {k} value = {v!r} }}" for k, v in locals_.items()]
        + ["te_demog_migrant_rates = yes"])}
    eng = _engine_for(dataclasses.replace(inp, backup_elig=ring.lx_elig or 0.0), YEAR + 1, pop, effects=stub,
                      engine=functools.partial(_UmEngine, owner_vars=owner_vars, truncate=truncate),
                      real_multipliers=real_multipliers)
    eng.trigger_fixtures["te_demog_effects_run"] = full
    for k in range(N):
        if ring.f[k] or ring.m[k]:
            eng.vars[f"te_dg_f{k}"], eng.vars[f"te_dg_m{k}"] = ring.f[k], ring.m[k]
    eng.vars.update(te_dg_pf=ring.pool_f, te_dg_pm=ring.pool_m, te_dg_pa=ring.pool_age, te_dg_scale=ring.scale,
                    te_dg_year=float(YEAR), te_dg_people=ring.total, te_dg_raw=ring.total / ring.scale,
                    te_dg_sex_balance=M.structure(ring)["men_per_100_women"], te_dg_faw=ring.faw, te_dg_fam=ring.fam)
    for c in range(len(P.MIGRANT_CLASSES)):
        eng.vars[f"te_dg_cf{c}"], eng.vars[f"te_dg_cm{c}"] = ring.class_f[c], ring.class_m[c]
    for b, (bf, bm) in enumerate(zip(*M.band_sums(ring))):
        eng.vars[f"te_dg_bf{b}"], eng.vars[f"te_dg_bm{b}"] = bf, bm
    for j in range(P.LX_BANDS):
        if ring.lx_s[j] is not None:
            eng.vars[f"te_dg_s{j}"], eng.vars[f"te_dg_d{j}"] = ring.lx_s[j], ring.lx_d[j]
    for name, value in (("te_dg_lx_ps", ring.lx_ps), ("te_dg_lx_pd", ring.lx_pd), ("te_dg_elig", ring.lx_elig),
                        ("te_dg_cover", ring.lx_cover), ("te_dg_lx_sbar", ring.lx_sbar)):
        if value is not None:
            eng.vars[name] = value
    return eng


def _owner(free=2000.0, phi=0.6, cap=1_000_000.0, f=500.0, m=400.0):
    return {"te_dg_um_cap": cap, "te_dg_um_free": free, "te_dg_um_phi": phi, "te_dg_um_f": f, "te_dg_um_m": m,
            "te_dg_um_af": 0.0, "te_dg_um_am": 0.0}


class TestUploadStepScript(unittest.TestCase):
    """te_demog_step under Full with the owner's capacity against demographics_model.step with Inputs.uploads."""

    def close(self, got, want, rel=1e-8, what=""):
        self.assertLessEqual(abs(got - want), rel * max(abs(want), 1.0), f"{what}: {got} vs {want}")

    def step_both(self, inp, owner, ring=None):
        ring = ring or _ring(inp)
        pop = ring.total * 1.004
        eng = _engine(ring, inp, pop, dict(owner))
        eng.call("te_demog_step")
        um_inp = dataclasses.replace(inp, uploads={"phi": owner["te_dg_um_phi"], "free": owner["te_dg_um_free"]})
        out = M.step(ring, um_inp, YEAR + 1, engine_pop=pop)
        return eng, ring, out

    def check(self, eng, out, owner0):
        self.close(eng.vars["te_dg_deaths"], out["deaths"], 1e-8, "deaths")
        for short, key in DC_SLICES.items():
            self.close(eng.vars[f"te_dg_dc_{short}"], out["causes"][key], 1e-8, f"deaths by cause: {short}")
        um = out["um"]
        self.close(eng.vars["te_dg_um_elig"], um["eligible"], 1e-8, "eligible deaths")
        self.close(eng.vars["te_dg_um_new"], um["uploads"], 1e-8, "uploads")
        self.close(eng.vars["te_dg_um_l100"], um["l100"], 1e-6, "Living to 100 counting uploads")
        own = eng.owner_vars
        self.close(own["te_dg_um_free"], max(0.0, owner0["te_dg_um_free"] - um["uploads"]), 1e-8, "free capacity")
        self.close(own["te_dg_um_f"] - owner0["te_dg_um_f"], um["uploads"] * um["women"], 1e-6, "women's minds")
        self.close(own["te_dg_um_m"] - owner0["te_dg_um_m"], um["uploads"] * (1 - um["women"]), 1e-6, "men's minds")

    def test_a_step_with_free_capacity(self):
        owner = _owner(free=1e9, phi=1.0)
        eng, ring, out = self.step_both(_inp(), dict(owner))
        self.check(eng, out, owner)
        um = out["um"]
        self.assertGreater(um["uploads"], 0.0)
        # everyone the cover reaches uploads: the eligible are cover x the treated's infection and chronic deaths
        self.close(um["uploads"], um["eligible"], 1e-9, "all the eligible")
        self.assertLess(um["eligible"], out["causes"]["infection"] + out["causes"]["chronic"])
        self.assertGreater(um["l100"], out["lx"]["blend"]["l100"], "an upload counts as living")
        # deaths per 1,000 are true deaths: the step's deaths less its uploads
        self.close(eng.vars["te_dg_cdr"], 1000 * (out["deaths"] - um["uploads"]) / eng.vars["te_dg_people"], 1e-6, "cdr")

    def test_the_share_and_the_cap(self):
        """phi of the eligible, never past the free capacity."""
        for owner in (_owner(free=1e9, phi=0.3), _owner(free=50.0, phi=1.0), _owner(free=0.0, phi=0.0)):
            with self.subTest(free=owner["te_dg_um_free"], phi=owner["te_dg_um_phi"]):
                eng, ring, out = self.step_both(_inp(), dict(owner))
                self.check(eng, out, owner)
                self.assertLessEqual(out["um"]["uploads"], owner["te_dg_um_free"] + 1e-9)

    def test_no_capacity_books_nothing(self):
        """An owner whose census left it no capacity (no Nexus, or no Mind Backups): the plain late step, no figures."""
        owner = _owner(cap=0.0, free=0.0)
        inp = _inp()
        ring = _ring(inp)
        eng = _engine(ring, inp, ring.total * 1.004, dict(owner))
        eng.vars["te_dg_um_new"] = 77.0          # a stale figure from before goes
        eng.call("te_demog_step")
        out = M.step(ring, inp, YEAR + 1, engine_pop=ring.total * 1.004)
        self.assertNotIn("um", out)
        for name in ("te_dg_um_new", "te_dg_um_elig", "te_dg_um_l100"):
            self.assertNotIn(name, eng.vars)
        self.assertEqual(eng.owner_vars, owner)
        self.assertAlmostEqual(eng.vars["te_dg_cdr"], 1000 * out["deaths"] / eng.vars["te_dg_people"], places=6)

    def test_outside_full_books_nothing(self):
        owner = _owner(free=1e9, phi=1.0)
        inp = _inp()
        ring = _ring(inp)
        eng = _engine(ring, inp, ring.total * 1.004, dict(owner), full=False)
        eng.call("te_demog_step")
        self.assertNotIn("te_dg_um_new", eng.vars)
        self.assertEqual(eng.owner_vars, owner)

    def test_fixed_point(self):
        """In the engine's five decimals (test_demographics_late.test_fixed_point_births): each product multiplies before
        it divides, so the uploads, the eligible and Living to 100 keep their digits."""
        owner = _owner(free=1e9, phi=0.8)
        inp = _inp()
        ring = _ring(inp)
        eng = _engine(ring, inp, ring.total * 1.004, dict(owner), truncate=True)
        eng.call("te_demog_step")
        out = M.step(ring, dataclasses.replace(inp, uploads={"phi": 0.8, "free": 1e9}), YEAR + 1,
                     engine_pop=ring.total * 1.004)
        for name, want in (("te_dg_um_new", out["um"]["uploads"]), ("te_dg_um_elig", out["um"]["eligible"]),
                           ("te_dg_um_l100", out["um"]["l100"])):
            self.close(eng.vars[name], want, 1e-3, name)

    def test_immortality(self):
        """Under Biological Immortality and the pull few treated bodies die of illness: few uploads."""
        inp = _inp(**{P.AGEING_RATE_TYPE: -1.0, P.REJUVENATION_TYPE: 0.03})
        owner = _owner(free=1e9, phi=1.0)
        eng, ring, out = self.step_both(inp, dict(owner))
        self.check(eng, out, owner)


class TestBackupRestore(unittest.TestCase):
    """Call 2: Mind Backups' restore (P.BACKUP_TYPES) x last step's longevity care E."""

    def test_the_inputs_take_the_restore_at_e(self):
        inp = _inp(**{t: -0.5 for t in P.BACKUP_TYPES.values()}, state_external_mortality_mult=-0.1)
        eng = _engine_for(inp, YEAR + 1, POP)
        eng.vars["te_dg_elig"] = 0.4
        eng.call("te_demog_cause_inputs_store")
        self.assertAlmostEqual(eng.vars["te_dg_in_ext"], -0.1 - 0.5 * 0.4)
        self.assertAlmostEqual(eng.vars["te_dg_in_work"], -0.5 * 0.4)
        e = dataclasses.replace(inp, backup_elig=0.4)
        self.assertAlmostEqual(M.plain_multiplier(e, "external"), 1 - 0.1 - 0.2)
        self.assertAlmostEqual(M.plain_multiplier(e, "work"), 1 - 0.2)

    def test_no_care_no_restore(self):
        """Human Purity (E 0), or a state with no late game (no E): nothing."""
        inp = _inp(**{t: -0.5 for t in P.BACKUP_TYPES.values()})
        eng = _engine_for(inp, YEAR + 1, POP)
        eng.call("te_demog_cause_inputs_store")
        self.assertEqual(eng.vars["te_dg_in_ext"], 0.0)
        self.assertEqual(M.plain_multiplier(inp, "external"), 1.0)

    def test_everyone_in_care_keeps_today(self):
        inp = dataclasses.replace(_inp(**{t: -0.5 for t in P.BACKUP_TYPES.values()}), backup_elig=1.0)
        self.assertAlmostEqual(M.plain_multiplier(inp, "external"), 0.5)
        self.assertAlmostEqual(M.plain_multiplier(inp, "work"), 0.5)

    def test_a_late_step_with_the_restore(self):
        """The step reads last step's E (the ring's), the script the state's stored te_dg_elig: the same deaths."""
        inp = _inp(**{t: -0.5 for t in P.BACKUP_TYPES.values()})
        ring = _ring(inp)
        eng = _engine(ring, inp, ring.total * 1.004, {}, full=False, real_multipliers=True)
        eng.call("te_demog_step")
        out = M.step(ring, inp, YEAR + 1, engine_pop=ring.total * 1.004)
        self.assertAlmostEqual(eng.vars["te_dg_deaths"] / out["deaths"], 1.0, places=8)
        self.assertAlmostEqual(eng.vars["te_dg_m_ext"], M.cause_multipliers(dataclasses.replace(
            inp, backup_elig=0.5, medicine=ring.medicine))["external"], places=8)

    def test_mind_backups_carries_the_restore(self):
        import demographics_modifiers as DM
        carriers = {(c.key, c.type): c.value for c in DM.load_carriers() if c.key == P.UM_TECH}
        for t in P.BACKUP_TYPES.values():
            self.assertEqual(carriers[(P.UM_TECH, t)], -0.5)
        self.assertNotIn((P.UM_TECH, "state_external_mortality_mult"), carriers)
        self.assertNotIn((P.UM_TECH, "state_work_mortality_mult"), carriers)


class _UmCountryEngine(_CountryEngine):
    """_CountryEngine with the owner's technologies and each state's Nexus (its dict's _levels; has_building)."""

    def __init__(self, techs=(), **kwargs):
        super().__init__(**kwargs)
        self.techs = set(techs)

    def number(self, tok):
        if tok == "te_demog_um_state_levels":
            return float(self.vars.get("_levels", 0.0))
        return super().number(tok)

    def _test(self, key, op, arg):
        if key == "has_technology_researched":
            return arg in self.techs
        if key == "has_building":
            assert arg == P.UM_BUILDING, arg
            return self.vars.get("_levels", 0.0) > 0
        return super()._test(key, op, arg)


def _country(pool, states, techs=(P.UM_TECH,), full=True):
    eng = _UmCountryEngine(techs=techs, states=states, fixtures={},
                           triggers={"te_demog_cohorts_run": True, "te_demog_effects_run": full})
    for name in ("f", "m", "af", "am"):
        eng.vars[f"te_dg_um_{name}"] = getattr(pool, name)
    eng.vars["te_dg_um_cap"] = pool.cap
    return eng


class TestCountryYearScript(unittest.TestCase):
    """te_demog_um_country against demographics_uploads.census."""

    def run_both(self, pool, levels, demand, uploaded, people=8e7, deaths=900000.0, techs=(P.UM_TECH,)):
        states = [{"_levels": float(levels) - 1, "te_dg_um_lvo": float(levels) - 1}, {"_levels": 1.0, "te_dg_um_lvo": 0.5},
                  {}]
        eng = _country(pool, states, techs=techs)
        eng.locals.update(te_dg_c_um_new=uploaded, te_dg_c_um_elig=demand, te_dg_c_deaths=deaths, te_dg_c_people=people,
                          te_dg_c_um_l100=0.0, te_dg_c_um_lpm=0.0)
        eng.call("te_demog_um_country")
        want = U.census(dataclasses.replace(pool), levels, P.UM_TECH in techs, demand, uploaded, people)
        for name in ("f", "m", "af", "am", "cap", "free", "phi", "util", "share"):
            self.assertAlmostEqual(eng.vars[f"te_dg_um_{name}"], getattr(want, name), places=6, msg=name)
        self.assertAlmostEqual(eng.vars["te_dg_um_end"], want.ended, places=6)
        self.assertAlmostEqual(eng.vars["te_dg_um_new"], uploaded)
        self.assertAlmostEqual(eng.vars["te_dg_um_dem"], demand)
        if uploaded > 0:
            self.assertAlmostEqual(eng.vars["te_dg_cdr"], 1000 * (deaths - uploaded) / people, places=6)
        else:
            self.assertNotIn("te_dg_cdr", eng.vars, "the census's own figure stands")
        return eng, want

    def test_filling(self):
        pool = U.Pool(f=1.2e6, m=1.0e6, cap=5e6)
        eng, want = self.run_both(pool, 5, demand=900000.0, uploaded=500000.0)
        self.assertGreater(want.phi, 0.9)
        self.assertEqual(want.archived, 0.0)
        # the research cancel: the staffed levels x (1 - utilisation)
        self.assertAlmostEqual(eng.vars["te_dg_um_rmult"], (4 + 0.5) * (1 - want.util), places=6)
        self.assertIn("te_demog_um_research", eng.modifiers)
        self.assertNotIn("te_demog_um_devout", eng.modifiers)

    def test_living_to_100_by_people(self):
        """The country's Living to 100 counting uploads: its late states' by people, a state with none booked at its
        bodies' own."""
        states = [{"te_dg_elig": 1.0, "te_dg_lx_l100": 0.7, "te_dg_um_l100": 0.9, "te_dg_um_new": 10.0, "_pm": 2.0},
                  {"te_dg_elig": 1.0, "te_dg_lx_l100": 0.6, "_pm": 1.0}, {"_pm": 5.0}]
        eng = _country(U.Pool(), states)
        eng.call("te_demog_um_country_init")
        for st in states:
            eng.locals["te_dg_c_s_pm"] = st["_pm"]
            eng._in(st, eng._tree(eng.effects, "te_demog_um_country_add"))
        eng.locals.update(te_dg_c_deaths=100.0, te_dg_c_people=1000.0)
        eng.call("te_demog_um_country")
        self.assertAlmostEqual(eng.vars["te_dg_um_l100"], (0.9 * 2 + 0.6 * 1) / 3)
        self.assertAlmostEqual(eng.vars["te_dg_cdr"], 90.0)

    def test_full_hosts_no_more(self):
        pool = U.Pool(f=2.6e6, m=2.4e6, cap=5e6)
        eng, want = self.run_both(pool, 5, demand=900000.0, uploaded=0.0)
        self.assertAlmostEqual(want.free, want.ended, places=3)   # the endings free a little
        self.assertLess(want.phi, 0.01)

    def test_a_lost_nexus_archives_and_its_return_restores(self):
        pool = U.Pool(f=2.6e6, m=2.4e6, cap=5e6)
        eng, want = self.run_both(pool, 2, demand=900000.0, uploaded=0.0)
        self.assertAlmostEqual(want.active, 2e6, places=3)
        self.assertGreater(want.archived, 2.9e6)
        self.assertEqual(want.free, 0.0)
        back = dataclasses.replace(want)
        eng, again = self.run_both(back, 5, demand=900000.0, uploaded=0.0)
        self.assertLess(again.archived, 1.0)
        self.assertGreater(again.active, 4.99e6)

    def test_no_mind_backups_hosts_nothing(self):
        pool = U.Pool(f=100.0, m=100.0, cap=1e6)
        eng, want = self.run_both(pool, 1, demand=0.0, uploaded=0.0, techs=())
        self.assertEqual(want.cap, 0.0)
        self.assertAlmostEqual(want.active, 0.0)
        self.assertGreater(want.archived, 0.0)

    def test_outside_full_the_pool_stands_and_the_modifiers_go(self):
        pool = U.Pool(f=1e6, m=1e6, cap=5e6)
        eng = _country(pool, [{"_levels": 5.0}], full=False)
        eng.modifiers.update(te_demog_um_research=1.0, te_demog_um_devout=1.0)
        eng.locals.update(te_dg_c_um_new=0.0, te_dg_c_um_elig=0.0, te_dg_c_deaths=1.0, te_dg_c_people=1.0,
                          te_dg_c_um_l100=0.0, te_dg_c_um_lpm=0.0)
        eng.call("te_demog_um_country")
        self.assertEqual(eng.vars["te_dg_um_f"], 1e6)
        self.assertEqual(eng.modifiers, {})

    def test_the_devout_switch(self):
        """Call 8: off by default; on, the Devout lose approval while the minds pass the share."""
        self.assertFalse(P.UM_POLITICS)
        pool = U.Pool(f=1e6, m=1e6, cap=5e6)
        self.assertFalse(U.devout_on(U.census(dataclasses.replace(pool), 5, True, 0.0, 0.0, 8e6)))
        eng = _country(pool, [{"_levels": 5.0}])
        eng.fixtures["te_demog_k_um_politics"] = 1.0
        eng.locals.update(te_dg_c_um_new=0.0, te_dg_c_um_elig=0.0, te_dg_c_deaths=1.0, te_dg_c_people=8e6,
                          te_dg_c_um_l100=0.0, te_dg_c_um_lpm=0.0)
        eng.call("te_demog_um_country")
        self.assertIn("te_demog_um_devout", eng.modifiers)


class TestPoolModel(unittest.TestCase):
    """The country's year in the model (call 5, call 7)."""

    def test_endings_free_capacity_and_archived_minds_never_end(self):
        pool = U.census(U.Pool(f=600.0, m=400.0, af=50.0, am=50.0), 0, True, 0.0, 0.0, 1e4)
        self.assertAlmostEqual(pool.ended, 1000 * P.UM_END_RATE)
        self.assertEqual(pool.cap, 0.0)
        self.assertAlmostEqual(pool.archived, 100.0 + 1000 * (1 - P.UM_END_RATE))

    def test_restored_before_new_uploads(self):
        pool = U.census(U.Pool(af=3e6, am=2e6), 3, True, 1e6, 0.0, 1e8)
        self.assertAlmostEqual(pool.active, 3e6)
        self.assertEqual(pool.free, 0.0)
        self.assertEqual(pool.phi, 0.0)

    def test_a_steps_uploads_take_the_free_capacity(self):
        pool = U.census(U.Pool(), 1, True, 0.0, 0.0, 1e8)
        self.assertEqual((pool.free, pool.phi), (1e6, 1.0))
        U.take_uploads(pool, 600000.0, 0.55)
        self.assertAlmostEqual(pool.f, 330000.0)
        self.assertAlmostEqual(pool.free, 400000.0)


class TestNexus(unittest.TestCase):
    """Call 6's trace: the Nexus's modifiers against the parameters, its research line, the calibration."""

    @staticmethod
    def blocks():
        text = UM_MODIFIERS.read_text(encoding="utf-8-sig")
        out = {}
        for name, body in re.findall(r"^([a-z_]+) = \{(.*?)^\}", text, re.S | re.M):
            out[name] = {k: float(v) for k, v in re.findall(r"^\t([a-z_]+) = (-?[\d.]+)", body, re.M)}
        return out

    def test_the_modifiers_carry_the_parameters(self):
        b = self.blocks()
        lines = U.nexus_lines()
        self.assertEqual(set(lines["out"]), set(P.UM_OUTPUT_FACTORS), "every output the method makes has a factor")
        self.assertEqual(set(lines["in"]), set(P.UM_INPUT_FACTORS), "every input it uses has a factor")
        for good, k in P.UM_OUTPUT_FACTORS.items():
            self.assertEqual(b["te_demog_um_nexus_off"][f"goods_output_{good}_mult"], -1)
            self.assertEqual(b["te_demog_um_nexus_minds"][f"goods_output_{good}_mult"], k)
        for good, k in P.UM_INPUT_FACTORS.items():
            self.assertEqual(b["te_demog_um_nexus_off"][f"goods_input_{good}_mult"], -1)
            self.assertEqual(b["te_demog_um_nexus_minds"][f"goods_input_{good}_mult"], k)
        self.assertEqual(b["te_demog_um_research"], {"country_tech_research_speed_mult": -P.UM_RESEARCH_PER_LEVEL})
        self.assertEqual(b["te_demog_um_devout"], {"interest_group_ig_devout_approval_add": P.UM_DEVOUT_APPROVAL})

    def test_the_research_line_is_the_methods(self):
        text = (ROOT / "common" / "production_methods" / "extra_pms.txt").read_text(encoding="utf-8-sig")
        body = re.search(r"^pm_mind_upload_nexus = \{(.*?)^\}", text, re.S | re.M).group(1)
        self.assertIn(f"country_tech_research_speed_mult = {P.UM_RESEARCH_PER_LEVEL}", body)

    def test_the_mult_axes_are_registered(self):
        """The engine ignores an unregistered goods mult axis (the Strategic Reserve's lesson)."""
        defs = "".join(p.read_text(encoding="utf-8-sig")
                       for p in (ROOT / "common" / "modifier_type_definitions").glob("*.txt"))
        for good in P.UM_OUTPUT_FACTORS:
            self.assertRegex(defs, rf"(?m)^goods_output_{good}_mult = \{{")
        for good in P.UM_INPUT_FACTORS:
            self.assertRegex(defs, rf"(?m)^goods_input_{good}_mult = \{{")

    def test_a_full_level_makes_about_the_calibration(self):
        """A full level, 1,000,000 minds, makes about UM_MIND_OUTPUT a mind a week at base prices, leaning on digital
        assets, and empty it makes nothing."""
        full = U.nexus_output(1.0)
        self.assertLess(abs(full["out_value"] / P.UM_PER_LEVEL - P.UM_MIND_OUTPUT), 0.05 * P.UM_MIND_OUTPUT)
        prices = U.goods_prices()
        da = full["out"]["digital_assets"] * prices["digital_assets"]
        self.assertGreater(da / full["out_value"], 0.7)
        self.assertLess(full["in_value"], 0.3 * full["out_value"])
        self.assertEqual(U.nexus_output(0.0)["out_value"], 0.0)


class TestWiring(unittest.TestCase):
    def test_the_hooks(self):
        text = lambda rel: (ROOT / rel).read_text(encoding="utf-8-sig")  # noqa: E731
        on = text("common/on_actions/te_demog_on_actions.txt")
        self.assertIn("te_demog_um_nexus_refresh = yes", on.split("te_demog_state_yearly_on_action = {")[1].split("\n}")[0])
        eff = text("common/scripted_effects/te_demog_effects.txt")
        finish = eff.split("te_demog_step_finish = {")[1].split("\n}")[0]
        self.assertLess(finish.index("te_demog_cause_deaths_store = yes"), finish.index("te_demog_um_step = yes"))
        self.assertLess(finish.index("te_demog_um_step = yes"), finish.index("te_demog_set_scale = yes"))
        self.assertIn("te_demog_um_clear_state = yes", eff.split("te_demog_seed = {")[1].split("\n}")[0])
        yearly = eff.split("te_demog_country_yearly = {")[1].split("\n}")[0]
        self.assertIn("te_demog_um_clear_outside_full = yes", yearly)
        census = eff.split("te_demog_country_census = {")[1]
        self.assertLess(census.index("te_demog_cause_deaths_country_store = yes"), census.index("te_demog_um_country = yes"))
        lx = text("common/scripted_effects/te_demog_lx_effects.txt")
        self.assertEqual(lx.count("te_demog_um_slot = yes"), 2)
        self.assertIn("te_demog_um_begin = yes", lx)

    def test_the_multiplier_reads_the_states_copy(self):
        """add_modifier's multiplier resolves against ROOT (the state on its pulse), and buildings have no variables:
        the Nexus's modifier reads root.var:, the state's copy, which is never removed."""
        um = UM_EFFECTS.read_text(encoding="utf-8-sig")
        self.assertIn("multiplier = root.var:te_dg_um_util", um)
        self.assertNotIn("remove_variable = te_dg_um_util", um)
        self.assertNotIn("remove_variable = te_dg_um_rmult", um)


class TestScenario(unittest.TestCase):
    """demographics_harness.py uploads: one full Nexus fills and stops; three take longer; the uploads count as living."""

    def test_era11_one_and_three(self):
        one = U.scenario("era11", 5, people=100_000_000, years=10)
        three = U.scenario("era11", 15, people=100_000_000, years=10)
        self.assertGreater(one[0]["uploads"], 0)
        self.assertAlmostEqual(one[-1]["util"], 1.0, places=2)
        self.assertLess(three[-1]["util"], 1.0)
        self.assertLess(one[0]["cdr_true"], one[0]["cdr"])
        self.assertGreater(one[0]["l100_up"], one[0]["l100"])


if __name__ == "__main__":
    unittest.main()
