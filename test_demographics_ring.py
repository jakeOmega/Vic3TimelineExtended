"""The ring's 300 years and the pyramid's rows past 85 (issue #1075).

Part 1: the census keeps 85 and over as its last band, and the pyramid splits it into rows (demographics_params.OLD_ROWS)
where the people past 100 are 1% of the people or more (te_demog_old_rows_close, te_demog_old_rows_show; the model's
old_rows, old_rows_shown, lx_bio_old_rows), on states, countries and the biological pyramid.

Part 2: the ring holds ages 0-299 (demographics_params.RING_YEARS), and a census taken on the 150-year ring (a save from
before the change: its state has no te_dg_ring) is re-filed at its next step (te_demog_ring_migrate, against its twin
demographics_model.ring_migrate): each cohort keeps its age, the late game's birth bands go with their slots, and the
pool goes to its mean age with its treated share and deficit (owner, 2026-10-20).
"""

import math
import random
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
from test_demographics_late import YEAR as LATE_YEAR  # noqa: E402
from test_demographics_late import _engine as _late_engine  # noqa: E402
from test_demographics_late import _inp as _late_inp  # noqa: E402
from test_demographics_late import _ring as _late_ring  # noqa: E402
from test_demographics_registry import (  # noqa: E402
    DISPLAY_VALUES, EFFECTS, LX_GEN_EFFECTS, VALUES, _block, _CountryEngine, _Engine, _engine_for, _raw_blocks, _text)

GENERATED_EFFECTS_FILE = ROOT / "common" / "scripted_effects" / "te_demog_generated_effects.txt"
GUI = ROOT / "gui" / "te_demographics_widgets.gui"
LOC = ROOT / "localization" / "english"
N = P.RING_YEARS
ROWS = len(P.OLD_ROWS)
LAST = P.BANDS - 1

OLD, W = M.OLD_RING_YEARS, P.LX_BAND_WIDTH
OLD_BANDS = OLD // W


def _old_census(year, seed, pool_age=165.4, treated=True, pool=True, band_of_age=None):
    """A census as a 150-year ring holds it at the count of `year`: (the script's variables, the model's Ring).
    band_of_age: an age whose old birth band is sure to hold a treated share."""
    rnd = random.Random(seed)
    ring = M.Ring(year=year)
    ring.scale = 1.37
    v = {"te_dg_year": float(year), "te_dg_scale": ring.scale}
    for k in range(OLD):
        if rnd.random() < 0.15:
            continue                          # a slot nobody holds has no variable
        f, m = round(rnd.uniform(1, 9000), 3), round(rnd.uniform(1, 9000), 3)
        ring.f[k], ring.m[k] = f, m
        v[f"te_dg_f{k}"], v[f"te_dg_m{k}"] = f, m
    if treated:
        for j in range(OLD_BANDS):
            if rnd.random() < 0.3:
                continue
            s, d = round(rnd.uniform(0.05, 0.9), 4), round(rnd.uniform(1, 80), 3)
            ring.lx_s[j], ring.lx_d[j] = s, d
            v[f"te_dg_s{j}"], v[f"te_dg_d{j}"] = s, d
        if band_of_age is not None:
            j = ((year - band_of_age) % OLD) // W
            ring.lx_s[j], ring.lx_d[j] = 0.3, 21.5
            v[f"te_dg_s{j}"], v[f"te_dg_d{j}"] = 0.3, 21.5
    pf, pm = (round(rnd.uniform(100, 50000), 3), round(rnd.uniform(100, 50000), 3)) if pool else (0.0, 0.0)
    ring.pool_f, ring.pool_m, ring.pool_age = pf, pm, pool_age
    v.update(te_dg_pf=pf, te_dg_pm=pm, te_dg_pa=pool_age)
    if treated and pool:
        ring.lx_ps, ring.lx_pd = 0.62, 118.25
        v.update(te_dg_lx_ps=0.62, te_dg_lx_pd=118.25)
    for c in range(len(P.MIGRANT_CLASSES)):
        cf, cm = round(rnd.uniform(1000, 90000), 3), round(rnd.uniform(1000, 90000), 3)
        ring.class_f[c], ring.class_m[c] = cf, cm
        v[f"te_dg_cf{c}"], v[f"te_dg_cm{c}"] = cf, cm
    return v, ring


def _migrated(v, truncate=False):
    eng = _Engine({}, truncate=truncate)
    eng.vars.update(v)
    eng.call("te_demog_ring_check")
    return eng


class TestRingYears(unittest.TestCase):
    def test_the_ring_reaches_past_any_age_a_player_meets(self):
        """Someone born in 1836 is 264 in 2100: the ring holds them (issue #1075)."""
        self.assertEqual(P.RING_YEARS, 300)
        self.assertGreater(P.RING_YEARS, 2100 - 1836)
        self.assertEqual(P.LX_BANDS * P.LX_BAND_WIDTH, P.RING_YEARS)
        self.assertEqual(P.MIGRANT_CLASSES[-1][1], P.RING_YEARS)

    def test_the_hand_written_ring_literals_are_the_rings(self):
        """The script's own 300s, 299s and 298s are RING_YEARS, its last age and the last age that flows."""
        n = P.RING_YEARS
        values = _text(VALUES)
        self.assertIn(f"modulo = {n}", _block(values, "te_demog_open_slot"))
        effects = _text(EFFECTS)
        self.assertIn(f"set_variable = {{ name = te_dg_pa value = {n} }}", _block(effects, "te_demog_seed"))
        self.assertIn(f"set_variable = {{ name = te_dg_ring value = {n} }}", _block(effects, "te_demog_seed"))
        self.assertIn(f"limit = {{ local_var:te_dg_age <= {n - 2} }}", _block(effects, "te_demog_accumulate_slot"))
        self.assertIn(f"limit = {{ local_var:te_dg_age = {n} }}", _block(effects, "te_demog_slot"))
        self.assertIn(f"multiply = {n} }}", _block(effects, "te_demog_fold_slot"))
        self.assertEqual(_block(effects, "te_demog_work_pool_part").count(f"te_dg_wa_end <= {n} }}"), 2)
        migrate = _block(effects, "te_demog_ring_migrate")
        self.assertIn(f"set_variable = {{ name = te_dg_ring value = {n} }}", migrate)
        self.assertIn(f"modulo = {OLD} }}", migrate)
        # no hand-written 150, 149 or 148 left in the census's code outside the migration and the life tables, which
        # close at 150 (GROUPS)
        for name in ("te_demog_seed", "te_demog_seed_slot", "te_demog_accumulate_slot", "te_demog_slot",
                     "te_demog_age_slot", "te_demog_fold_slot", "te_demog_work_pool_part", "te_demog_work_part"):
            code = "\n".join(line.split("#")[0] for line in _block(effects, name).splitlines())
            self.assertIsNone(re.search(r"\b(14[89]|150)\b", code), name)

    def test_every_step_checks_the_ring_first(self):
        effects = _text(EFFECTS)
        code = [line.strip() for line in _block(effects, "te_demog_step_begin").splitlines()
                if line.strip() and not line.strip().startswith("#")]
        self.assertEqual(code[0], "te_demog_ring_check = yes")


class TestRingMigration(unittest.TestCase):
    """te_demog_ring_migrate against demographics_model.ring_migrate."""

    def _check(self, year, seed, **kw):
        v, ring = _old_census(year, seed, **kw)
        ages = {(year - k) % OLD: (ring.f[k], ring.m[k]) for k in range(OLD) if ring.f[k]}
        M.ring_migrate(ring)
        eng = _migrated(v)
        got = eng.vars
        self.assertEqual(got["te_dg_ring"], P.RING_YEARS)
        for k in range(P.RING_YEARS):
            for s, side in (("f", ring.f), ("m", ring.m)):
                if side[k]:
                    self.assertAlmostEqual(got[f"te_dg_{s}{k}"], side[k], places=6, msg=(year, k, s))
                else:
                    self.assertNotIn(f"te_dg_{s}{k}", got, (year, k, s))
        # each cohort kept its age on the new ring
        for k in range(P.RING_YEARS):
            if f"te_dg_f{k}" in got:
                age = (year - k) % P.RING_YEARS
                if age in ages:
                    self.assertAlmostEqual(got[f"te_dg_f{k}"], ages[age][0], places=6, msg=(year, age))
        for j in range(P.LX_BANDS):
            for name, side in ((f"te_dg_s{j}", ring.lx_s), (f"te_dg_d{j}", ring.lx_d)):
                if side[j] is None:
                    self.assertNotIn(name, got, (year, name))
                else:
                    self.assertAlmostEqual(got[name], side[j], places=7, msg=(year, name))
        self.assertAlmostEqual(got["te_dg_pf"], ring.pool_f, places=6)
        self.assertAlmostEqual(got["te_dg_pm"], ring.pool_m, places=6)
        self.assertAlmostEqual(got["te_dg_pa"], ring.pool_age, places=6)
        for name, want in (("te_dg_lx_ps", ring.lx_ps), ("te_dg_lx_pd", ring.lx_pd)):
            if want is None:
                self.assertNotIn(name, got)
            else:
                self.assertAlmostEqual(got[name], want, places=7)
        for c in range(len(P.MIGRANT_CLASSES)):
            self.assertAlmostEqual(got[f"te_dg_cf{c}"], ring.class_f[c], places=5, msg=c)
            self.assertAlmostEqual(got[f"te_dg_cm{c}"], ring.class_m[c], places=5, msg=c)
        return eng, ring

    def test_a_year_in_the_rings_first_half(self):
        # 1937 mod 300 = 137: the slots above the open slot (37) move up 150
        self.assertLess(1937 % P.RING_YEARS, OLD)
        self._check(1937, 1)

    def test_a_year_in_the_rings_second_half(self):
        # 2057 mod 300 = 257: the open slot (107) and those below it move up 150
        self.assertGreaterEqual(2057 % P.RING_YEARS, OLD)
        self._check(2057, 2)

    def test_the_pool_goes_to_its_mean_age(self):
        """Franche-Comte's 9.4M at a mean age of 165 all become 165 (the owner's simple rule)."""
        for year in (1937, 2057):
            v, ring = _old_census(year, 3, pool_age=164.6)
            pool_f, pool_m = ring.pool_f, ring.pool_m
            eng = _migrated(v)
            k = (year - 165) % P.RING_YEARS
            self.assertAlmostEqual(eng.vars[f"te_dg_f{k}"], pool_f, places=6)
            self.assertAlmostEqual(eng.vars[f"te_dg_m{k}"], pool_m, places=6)
            self.assertEqual((eng.vars["te_dg_pf"], eng.vars["te_dg_pm"], eng.vars["te_dg_pa"]),
                             (0.0, 0.0, float(P.RING_YEARS)))
            self.assertNotIn("te_dg_lx_ps", eng.vars)
            # its band takes its treated share and deficit (no cohort under 150 shares a band with 165)
            j = k // W
            self.assertAlmostEqual(eng.vars[f"te_dg_s{j}"], 0.62, places=7)
            self.assertAlmostEqual(eng.vars[f"te_dg_d{j}"], 118.25, places=6)

    def test_a_young_pool_merges_into_its_band(self):
        """A pool of mean age 151 lands in a band with the cohorts aged 147-149: the band's share and deficit are the
        two's by people."""
        for year in (1937, 2057):
            v, ring = _old_census(year, 4, pool_age=150.8, band_of_age=149)
            k = (year - 151) % P.RING_YEARS
            j = k // W
            # the band holds the cohorts aged 149 and 148 beside 150-152
            self.assertTrue({(year - x) % P.RING_YEARS for x in (148, 149)} <= set(range(W * j, W * j + W)))
            eng, ring = self._check(year, 4, pool_age=150.8, band_of_age=149)
            self.assertNotAlmostEqual(eng.vars[f"te_dg_s{j}"], 0.62, places=3)
            self.assertNotAlmostEqual(eng.vars[f"te_dg_s{j}"], 0.3, places=3)

    def test_a_pool_past_the_ring_stays(self):
        for year in (1937, 2057):
            eng, ring = self._check(year, 5, pool_age=312.0)
            self.assertGreater(eng.vars["te_dg_pf"], 0)
            self.assertEqual(eng.vars["te_dg_pa"], 312.0)
            self.assertIn("te_dg_lx_ps", eng.vars)

    def test_no_pool_and_no_late_game(self):
        for year in (1937, 2057):
            eng, _ring = self._check(year, 6, treated=False, pool=False)
            self.assertFalse(any(re.fullmatch(r"te_dg_[sd]\d+", n) for n in eng.vars))

    def test_the_new_ring_is_a_300_year_census_of_the_same_people(self):
        """A seed on the 300-year ring folded back onto 150 slots comes back unchanged: the re-filing is the ring's own
        layout for every age under 150 (the model's seed's ages past 150 hold under a millionth of a person, and are
        left out)."""
        inp = M.Inputs(sol=20, literacy=0.6, urban_share=0.4)
        for year in (1937, 2057):
            new = M.seed(inp, year, 2_000_000.0)
            for a in range(OLD, P.RING_YEARS):
                k = (year - a) % P.RING_YEARS
                self.assertLess(new.f[k] + new.m[k], 1e-6, a)
                new.f[k] = new.m[k] = 0.0
            old = M.Ring(year=year, scale=new.scale)
            for a in range(OLD):
                old.f[(year - a) % OLD] = new.f[(year - a) % P.RING_YEARS]
                old.m[(year - a) % OLD] = new.m[(year - a) % P.RING_YEARS]
            old.class_f, old.class_m = list(new.class_f), list(new.class_m)
            M.ring_migrate(old)
            self.assertEqual(old.f, new.f)
            self.assertEqual(old.m, new.m)

    def test_fixed_point(self):
        """Under the engine's five decimals the re-filing stays within the range and close to the model."""
        for year in (1937, 2057):
            v, ring = _old_census(year, 7, pool_age=150.8)
            M.ring_migrate(ring)
            eng = _migrated(v, truncate=True)
            for j in range(P.LX_BANDS):
                if ring.lx_s[j] is not None:
                    self.assertTrue(math.isclose(eng.vars[f"te_dg_s{j}"], ring.lx_s[j], abs_tol=1e-4), j)
                    self.assertTrue(math.isclose(eng.vars[f"te_dg_d{j}"], ring.lx_d[j], rel_tol=1e-4), j)

    def test_a_late_census_re_filed_then_stepped_matches_the_model(self):
        """End to end: a late-game census on the 150-year ring, its pool at 160 and treated, re-filed by its own next
        step (te_demog_step_begin's te_demog_ring_check) and stepped, against ring_migrate then step in the model."""
        import copy
        import test_demographics_late as L
        inp = _late_inp()
        new = _late_ring(inp)
        y = new.year
        for a in range(OLD, N):
            new.f[(y - a) % N] = new.m[(y - a) % N] = 0.0
        old = M.Ring(year=y, scale=new.scale)
        for a in range(OLD):
            old.f[(y - a) % OLD], old.m[(y - a) % OLD] = new.f[(y - a) % N], new.m[(y - a) % N]
        for j in range(OLD_BANDS):
            top = W * j + W - 1
            old.lx_s[j] = new.lx_s[((y - (y - top) % OLD) % N) // W]
            old.lx_d[j] = new.lx_d[((y - (y - top) % OLD) % N) // W]
        old.pool_f, old.pool_m, old.pool_age, old.lx_ps, old.lx_pd = 3000.0, 2000.0, 160.4, 0.7, 95.0
        old.lx_elig, old.lx_cover, old.lx_sbar = new.lx_elig, new.lx_cover, new.lx_sbar
        old.class_f, old.class_m, old.fam, old.faw = list(new.class_f), list(new.class_m), new.fam, new.faw
        old.fws_work, old.medicine, old.total = new.fws_work, new.medicine, new.total
        ring = M.ring_migrate(copy.deepcopy(old))
        self.assertEqual(ring.pool_f, 0.0)
        pop = ring.people() * 1.004
        eng = _late_engine(ring, inp, pop)
        # the script's census as the save holds it: the old ring, its pool and class sums, and no te_dg_ring
        for name in [n for n in eng.vars if re.fullmatch(r"te_dg_([fmsd])\d+", n)]:
            del eng.vars[name]
        for k in range(OLD):
            if old.f[k] or old.m[k]:
                eng.vars[f"te_dg_f{k}"], eng.vars[f"te_dg_m{k}"] = old.f[k], old.m[k]
        for j in range(OLD_BANDS):
            if old.lx_s[j] is not None:
                eng.vars[f"te_dg_s{j}"], eng.vars[f"te_dg_d{j}"] = old.lx_s[j], old.lx_d[j]
        for c in range(len(P.MIGRANT_CLASSES)):
            eng.vars[f"te_dg_cf{c}"], eng.vars[f"te_dg_cm{c}"] = old.class_f[c], old.class_m[c]
        eng.vars.update(te_dg_pf=old.pool_f, te_dg_pm=old.pool_m, te_dg_pa=old.pool_age, te_dg_lx_ps=old.lx_ps,
                        te_dg_lx_pd=old.lx_pd)
        del eng.vars["te_dg_ring"]
        eng.call("te_demog_step")
        self.assertEqual(eng.vars["te_dg_ring"], P.RING_YEARS)
        out = M.step(ring, inp, y + 1, engine_pop=pop)
        L.TestLateGameScript("test_a_late_step_matches_the_model").check(eng, ring, out)

    def test_a_census_on_the_new_ring_is_left_alone(self):
        v, _ring = _old_census(2057, 8)
        v["te_dg_ring"] = float(P.RING_YEARS)
        eng = _migrated(v)
        self.assertEqual(eng.vars, v)



# ---- Part 1: the pyramid's rows past 85 ----------------------------------------------------------------------------

class TestOldRowsModel(unittest.TestCase):
    def test_the_rows(self):
        self.assertEqual(P.OLD_ROWS, (85, 100, 125, 150, 200, 250, 300))
        self.assertEqual(P.OLD_ROW_WIDTHS, (15, 25, 25, 50, 50, 50, 5))
        self.assertEqual(P.OLD_ROW_DRAW, (0.33333, 0.2, 0.2, 0.1, 0.1, 0.1, 1.0))
        self.assertEqual(P.OLD_ROW_GATE, 0.01)

    def test_past_each_start(self):
        rows = [(90, 10.0, 5.0), (100, 1.0, 2.0), (149, 3.0, 4.0), (150, 7.0, 0.0), (299, 1.0, 1.0), (300, 2.0, 2.0)]
        of, om = M.old_rows(rows)
        self.assertEqual(of, [0.0, 14.0, 13.0, 10.0, 3.0, 3.0, 2.0])
        self.assertEqual(om, [0.0, 9.0, 7.0, 3.0, 3.0, 3.0, 2.0])

    def test_shown_only_past_the_gate(self):
        """An 1836-2000 pyramid ends at 85+: people past 100 under 1% of the people show no rows."""
        of, om = [0.0, 4.0, 1.0, 0.0, 0.0, 0.0, 0.0], [0.0, 4.9, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.assertEqual(M.old_rows_shown(300.0, 200.0, of, om, 1000.0), (0, None))
        top, rows = M.old_rows_shown(300.0, 200.0, of, om, 890.0)
        self.assertEqual(top, 1)
        self.assertEqual(rows[0], (296.0, 195.1))
        self.assertEqual(rows[1], (4.0, 4.9))      # 100 and over: everyone older in the top row
        self.assertEqual(rows[2:], [(0.0, 0.0)] * (ROWS - 2))

    def test_the_top_row_takes_everyone_older(self):
        of = [0.0, 50.0, 40.0, 30.0, 4.0, 1.0, 0.0]
        om = [0.0, 40.0, 30.0, 20.0, 3.0, 0.0, 0.0]
        top, rows = M.old_rows_shown(100.0, 80.0, of, om, 1000.0)
        self.assertEqual(top, 3)                  # 150 and over: 50 of 1,000; 200 and over 7, under the gate
        self.assertEqual(rows[:4], [(50.0, 40.0), (10.0, 10.0), (10.0, 10.0), (30.0, 20.0)])
        self.assertEqual(rows[4:], [(0.0, 0.0)] * 3)

    def test_the_scale_takes_the_rows_drawn(self):
        bf, bm = [10.0] * P.BANDS, [12.0] * P.BANDS
        bf[LAST] = 900.0
        self.assertEqual(M.pyramid_scale(bf, bm), 900.0)
        shown = (2, [(90.0, 60.0), (200.0, 100.0), (500.0, 10.0)] + [(0.0, 0.0)] * 4)
        self.assertAlmostEqual(M.pyramid_scale(bf, bm, shown), 100.0)        # 125+: 500 per five of its 25 years


def _long_lived(seed=1):
    """A late-game state where many live past 85: cohorts at 92 to 270 on the late tests' ring, most of each in longevity
    care with a body of about 60, and a pool past 300."""
    inp = _late_inp()
    ring = _late_ring(inp, seed=seed)
    unit = ring.total / ring.scale
    for age, share in ((92, 0.02), (110, 0.03), (118, 0.02), (130, 0.03), (170, 0.04), (220, 0.03), (270, 0.02)):
        k = (LATE_YEAR - age) % N
        ring.f[k] += share * unit * 0.55
        ring.m[k] += share * unit * 0.45
        ring.lx_s[k // W], ring.lx_d[k // W] = 0.8, age - 60.0
    ring.pool_age = N + 3.5
    M._refresh_denominators(ring)
    ring.total = ring.people()
    return inp, ring


class TestOldRowsScript(unittest.TestCase):
    """te_demog_old_rows_close and _show, and the biological pyramid's, run by the census against the model."""

    def close(self, got, want, rel=1e-8, what=""):
        self.assertLessEqual(abs(got - want), rel * max(abs(want), 1.0), f"{what}: {got} vs {want}")

    def _kept(self, eng, ring, rows):
        """The model's [(age, women, men)] for the slots the script kept (it drops a cohort under half a person)."""
        return [(a, f, m) for a, f, m in rows if a == N or f"te_dg_f{(ring.year - a) % N}" in eng.vars]

    def _shown(self, eng, prefix, band, people):
        of = [0.0] + [eng.vars.get(f"{prefix}f{i}", 0.0) for i in range(1, ROWS)]
        om = [0.0] + [eng.vars.get(f"{prefix}m{i}", 0.0) for i in range(1, ROWS)]
        return M.old_rows_shown(eng.vars[f"{band}f{LAST}"], eng.vars[f"{band}m{LAST}"], of, om, people)

    def _check_shown(self, eng, top_var, px, want):
        top, rows = want
        if top == 0:
            self.assertNotIn(top_var, eng.vars)
            self.assertFalse(any(n.startswith(px) for n in eng.vars), px)
            return
        self.assertEqual(eng.vars[top_var], top)
        for i, (f, m) in enumerate(rows):
            self.close(eng.vars[f"{px}f{i}"], f, 1e-6, f"{px}f{i}")
            self.close(eng.vars[f"{px}m{i}"], m, 1e-6, f"{px}m{i}")

    def _bands(self, eng, prefix):
        return ([eng.vars[f"{prefix}f{b}"] for b in range(P.BANDS)], [eng.vars[f"{prefix}m{b}"] for b in range(P.BANDS)])

    def test_an_ordinary_census_ends_at_85(self):
        """A seed and a step of an 1836 farm state: no row shows, and the scale is the bands' as before."""
        inp = M.Inputs(sol=8, literacy=0.1, urban_share=0.05)
        eng = _engine_for(inp, 1836, 250000.0, effects={"te_demog_flows": "te_demog_no_flows = yes"})
        eng.call("te_demog_seed")
        self.assertNotIn("te_dg_pyr_top", eng.vars)
        self.assertFalse(any(re.fullmatch(r"te_dg_px[fm]\d", n) for n in eng.vars))
        self.close(eng.vars["te_dg_pyr_max"], M.pyramid_scale(*self._bands(eng, "te_dg_b")), 1e-9, "scale")
        for i in range(2, ROWS):
            self.assertNotIn(f"te_dg_of{i}", eng.vars, i)

    def test_a_long_lived_state_splits_its_pyramid(self):
        inp, ring = _long_lived()
        pop = ring.total * 1.004
        eng = _late_engine(ring, inp, pop)
        eng.call("te_demog_step")
        M.step(ring, inp, LATE_YEAR + 1, engine_pop=pop)
        # the people past each start, the model's over the cohorts the script kept
        of, om = M.old_rows(self._kept(eng, ring, ring.by_age()))
        for i in range(1, ROWS):
            if of[i] + om[i] > 0:
                self.close(eng.vars[f"te_dg_of{i}"], of[i], 1e-7, f"women past {P.OLD_ROWS[i]}")
                self.close(eng.vars[f"te_dg_om{i}"], om[i], 1e-7, f"men past {P.OLD_ROWS[i]}")
            else:
                self.assertNotIn(f"te_dg_of{i}", eng.vars, i)
        # the rows shown from those, and the 85+ band they split
        cal = self._shown(eng, "te_dg_o", "te_dg_b", pop)
        self.assertGreaterEqual(cal[0], 3, "rows past 150 show")
        self._check_shown(eng, "te_dg_pyr_top", "te_dg_px", cal)
        self.close(sum(f + m for f, m in cal[1]), eng.vars[f"te_dg_bf{LAST}"] + eng.vars[f"te_dg_bm{LAST}"], 1e-7,
                   "the rows hold 85 and over")
        # the biological pyramid's, its treated parts at their biological ages
        bio = M.lx_bio_old_rows(ring)
        kept_bio = M.old_rows(self._bio_parts(eng, ring))
        for i in range(1, ROWS):
            want_f, want_m = kept_bio[0][i], kept_bio[1][i]
            if want_f + want_m > 0.5:
                self.assertLess(abs(eng.vars[f"te_dg_bof{i}"] - want_f), 1e-6 * want_f + 1e-6, i)
                self.assertLess(abs(eng.vars[f"te_dg_bom{i}"] - want_m), 1e-6 * want_m + 1e-6, i)
            self.assertLessEqual(want_f, bio[0][i] + 1e-6)
        bshown = self._shown(eng, "te_dg_bo", "te_dg_bb", pop)
        self._check_shown(eng, "te_dg_bpyr_top", "te_dg_bpx", bshown)
        self.assertLess(bshown[0], cal[0], "the treated are younger by body")
        # the scale over both views as drawn
        scale = max(M.pyramid_scale(*self._bands(eng, "te_dg_b"), cal),
                    M.pyramid_scale(*self._bands(eng, "te_dg_bb"), bshown))
        self.close(eng.vars["te_dg_pyr_max"], scale, 1e-6, "scale")
        self.assertLess(scale, eng.vars[f"te_dg_bf{LAST}"], "the split rows are drawn per five years of age")

    def _bio_parts(self, eng, ring):
        """The model's biological parts (lx_bio_old_rows') for the slots the script kept."""
        out = []
        for a, f, m in self._kept(eng, ring, ring.by_age()):
            if a == N:
                sh, bio = (ring.lx_ps or 0.0), ring.pool_age - (ring.lx_pd or 0.0)
            else:
                sh, bio = ring.lx_slot.get((ring.year - a) % N, (0.0, a))
            out.append((a, f - f * sh, m - m * sh))
            if sh > 0:
                out.append((bio, f * sh, m * sh))
        return out

    def test_fixed_point(self):
        inp, ring = _long_lived(seed=2)
        pop = ring.total * 1.004
        eng = _late_engine(ring, inp, pop, truncate=True)
        eng.call("te_demog_step")
        self.assertGreaterEqual(eng.vars["te_dg_pyr_top"], 3)
        rows = [eng.vars[f"te_dg_px{s}{i}"] for i in range(ROWS) for s in "fm"]
        self.assertTrue(all(x >= 0 for x in rows))
        self.assertLess(abs(sum(rows) - eng.vars[f"te_dg_bf{LAST}"] - eng.vars[f"te_dg_bm{LAST}"]), 0.01)

    def test_the_country_sums_its_states_rows(self):
        """te_demog_add_bands_to_root's rows into the country's, and its own rows shown."""
        blocks = _raw_blocks([GENERATED_EFFECTS_FILE])
        states = []
        for k, (o1, o3) in enumerate(((800.0, 300.0), (200.0, 0.0), (0.0, 0.0))):
            s = {f"te_dg_b{x}{b}": 1000.0 for b in range(P.BANDS) for x in "fm"}
            if o1:
                s.update(te_dg_of1=o1, te_dg_om1=o1 / 2)
            if o3:
                s.update(te_dg_of3=o3, te_dg_om3=0.0)
            states.append(s)
        body = (blocks["te_demog_reset_country_bands"] + "\nevery_scope_state = { te_demog_add_bands_to_root = yes }\n"
                + blocks["te_demog_country_old_rows_store"]
                + "\nset_local_variable = { name = te_dg_or_people value = 36000 }\n"
                + "te_demog_old_rows_show = { CUM = te_dg_co BAND = te_dg_cb PX = te_dg_px TOP = te_dg_pyr_top }")
        eng = _CountryEngine(states=states, fixtures={}, effects={"te_test": body})
        eng.call("te_test")
        self.assertEqual((eng.vars["te_dg_cof1"], eng.vars["te_dg_com1"]), (1000.0, 500.0))
        self.assertEqual((eng.vars["te_dg_cof3"], eng.vars["te_dg_com3"]), (300.0, 0.0))
        self.assertNotIn("te_dg_cof2", eng.vars)
        # 150 and over: 300 of 36,000, under 1%; 100 and over 1,500, past it
        self.assertEqual(eng.vars["te_dg_pyr_top"], 1)
        self.assertEqual((eng.vars["te_dg_pxf0"], eng.vars["te_dg_pxm0"]), (2000.0, 2500.0))
        self.assertEqual((eng.vars["te_dg_pxf1"], eng.vars["te_dg_pxm1"]), (1000.0, 500.0))
        self.assertEqual(eng.vars["te_dg_pxf3"], 0.0)

    def test_the_rows_go_when_the_gate_closes(self):
        eng = _Engine({})
        eng.vars.update({f"te_dg_b{x}{b}": 1000.0 for b in range(P.BANDS) for x in "fm"})
        eng.vars.update(te_dg_of1=200.0, te_dg_om1=100.0, te_dg_pyr_top=1.0,
                        **{f"te_dg_px{s}{i}": 1.0 for i in range(ROWS) for s in "fm"})
        eng.locals["te_dg_or_people"] = 36000.0
        eng.run(_parse("te_demog_old_rows_show = { CUM = te_dg_o BAND = te_dg_b PX = te_dg_px TOP = te_dg_pyr_top }"))
        self.assertNotIn("te_dg_pyr_top", eng.vars)
        self.assertFalse(any(n.startswith("te_dg_px") for n in eng.vars))


def _parse(text):
    from test_demographics_registry import _parse_script
    return _parse_script(text)


class TestOldRowsWiring(unittest.TestCase):
    def test_the_sweep_marks_the_row_starts(self):
        """The hand-written last band (17) runs on to the first row start past 85-99 (100), then the generated marks."""
        body = _block(_text(EFFECTS), "te_demog_age_boundaries")
        self.assertIn(f"limit = {{ local_var:te_dg_band < {LAST} }}", body)
        self.assertIn(f"limit = {{ local_var:te_dg_band >= {LAST} }}", body)
        self.assertIn(f"set_local_variable = {{ name = te_dg_next_band value = {P.OLD_ROWS[1]} }}", body)
        self.assertIn("te_demog_old_row_mark = yes", body)
        self.assertIn("te_demog_old_rows_close = yes", _block(_text(EFFECTS), "te_demog_close_accumulators"))

    def test_the_scales_read_every_row(self):
        values = _text(DISPLAY_VALUES)
        for name in ("te_demog_pyramid_max", "te_demog_state_pyramid_max"):
            body = _block(values, name)
            for i, d in enumerate(P.OLD_ROW_DRAW):
                for s in "fm":
                    want = (f"min = var:te_dg_px{s}{i}" if d == 1
                            else f"min = {{ value = var:te_dg_px{s}{i} multiply = {d:g} }}")
                    self.assertIn(want, body, (name, i, s))
        lx = _text(LX_GEN_EFFECTS)
        for name in ("te_demog_lx_bio_bands_store", "te_demog_lx_country_bio_store"):
            body = _block(lx, name)
            self.assertIn("te_demog_old_rows_show = {", body, name)
            for i in range(ROWS):
                for s in "fm":
                    self.assertIn(f"var:te_dg_bpx{s}{i}", body, (name, i, s))
        for name in ("te_demog_lx_bio_bands_clear", "te_demog_lx_country_bio_store"):
            self.assertIn("remove_variable = te_dg_bpyr_top", _block(lx, name), name)

    def test_the_gui_draws_each_view_split_where_the_census_says(self):
        gui = GUI.read_text(encoding="utf-8-sig")
        loc = "".join(f.read_text(encoding="utf-8-sig") for f in LOC.glob("*_l_english.yml"))
        views = (("GetPlayer.MakeScope", "te_demog_pyr_split_sgui", "te_dg_px", "te_dg_pyr_top", "te_demog_pyr_old_tt"),
                 ("GetPlayer.MakeScope", "te_demog_lx_bio_pyr_split_sgui", "te_dg_bpx", "te_dg_bpyr_top",
                  "te_demog_pyr_bio_old_tt"),
                 ("State.MakeScope", "te_demog_state_pyr_split_sgui", "te_dg_px", "te_dg_pyr_top", "te_demog_st_pyr_old_tt"),
                 ("State.MakeScope", "te_demog_lx_state_bio_pyr_split_sgui", "te_dg_bpx", "te_dg_bpyr_top",
                  "te_demog_st_pyr_bio_old_tt"))
        for scope, sgui, px, top, tt in views:
            gate = f"GetScriptedGui('{sgui}').IsShown( GuiScope.SetRoot( {scope} ).End )"
            self.assertEqual(gui.count(f'visible = "[{gate}]"'), 1, sgui)
            self.assertEqual(gui.count(f'visible = "[Not( {gate} )]"'), 1, f"{sgui}: the 85+ row hides")
            split = gui[gui.index(f'visible = "[{gate}]"'):]
            split = split[:split.index(f'visible = "[Not( {gate} )]"')]
            for i, d in enumerate(P.OLD_ROW_DRAW):
                for s in "fm":
                    var = f"{scope}.Var('{px}{s}{i}').GetValue"
                    want = var if d == 1 else f"Multiply_CFixedPoint( {var}, '(CFixedPoint){d:g}' )"
                    self.assertIn(want, split, (sgui, i, s))
                    self.assertIn(f" {tt}_{i}:0 ", loc, (tt, i))
                if 0 < i:
                    self.assertIn(f"GreaterThanOrEqualTo_CFixedPoint( {scope}.Var('{top}').GetValue, "
                                  f"'(CFixedPoint){i}' )", split, (sgui, i))
                if 0 < i < ROWS - 1:
                    self.assertIn(f" {tt}_open_{i}:0 ", loc, (tt, i))
        for i in range(1, ROWS - 1):
            self.assertIn(f' te_demog_pyr_row_{i}:0 "{P.OLD_ROWS[i]}–{P.OLD_ROWS[i + 1] - 1}"', loc)
            self.assertIn(f' te_demog_pyr_row_open_{i}:0 "{P.OLD_ROWS[i]}+"', loc)


if __name__ == "__main__":
    unittest.main()
