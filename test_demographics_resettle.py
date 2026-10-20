"""Internal Resettlement's known moves in the census and the US frontier's 1836 seed (2026-10-19).

The master spec (docs/superpowers/specs/2026-10-08-demographics-design.md) §2.5 "Known kills" and §2.6. The script
(te_demog_resettle_effects.txt, the generated te_demog_resettle_generated_effects.txt and their call sites) is run
through test_demographics_registry's interpreter against scripts/analysis/demographics_resettle.py:
- each programme's profile (the owner's calls) and the walk's counters by class and sex;
- a step with known moves: arrivals and departures booked by their profiles, the transit dead as known kills by the
  profile, the residual holding only the rest, the counters taken and removed;
- a state with no counters steps exactly as before (test_demographics_golden holds the rest);
- the frontier's seed: men per woman by the 1840 census's age groups, the people kept, the mark taken off at the
  pulse's re-seed.

Run: python3 -m unittest test_demographics_resettle -v
"""

import dataclasses
import re
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import demographics_model as M  # noqa: E402
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_resettle as RS  # noqa: E402
import gen_demographics_resettle as RSG  # noqa: E402
from test_demographics_registry import (  # noqa: E402  (helpers only: no TestCase)
    EFFECTS, RESETTLE_EFFECTS, _block, _engine_for, _parse_script, _text)

RESETTLEMENT = ROOT / "common" / "scripted_effects" / "resettlement_effects.txt"
HISTORY = ROOT / "common" / "history" / "extra_history.txt"
RS_VALUES = ROOT / "common" / "script_values" / "te_demog_resettle_generated_values.txt"
REGISTRY = ROOT / "test_resettlement_programme_registry.py"
INP = M.Inputs(sol=12, literacy=0.3, urban_share=0.15, techs=frozenset({"railways"}),
               laws=frozenset({"law_women_in_the_fields"}))
INP.mods = DM.totals(DM.load_carriers(), INP.techs, INP.laws, INP.institutions)
YEAR, POP = 1850, 200000.0


def squash(text):
    return re.sub(r"\s+", " ", re.sub(r"#[^\n]*", "", text)).strip()


def _counter_vars(counters):
    """The script's state variables for a Counters (te_dg_rs_*)."""
    out = {}
    for side, amounts in (("i", counters.inn), ("o", counters.out)):
        for key, v in amounts.items():
            out[RSG._name(side, key)] = v
    for name, v in (("te_dg_rs_in", counters.moved_in), ("te_dg_rs_out", counters.moved_out),
                    ("te_dg_rs_dead", counters.dead)):
        if v:
            out[name] = v
    return out


class TestProfiles(unittest.TestCase):
    """Each programme's movers (owner, 2026-10-19), as demographics_params.RESETTLE_PROFILES gives them."""

    def shares(self, programme, lf=0.3):
        return RS.programme_shares(programme, lf)

    def by_sex(self, sh, s):
        return sum(v for (_c, sex), v in sh.items() if sex == s)

    def test_every_programme_is_in_the_registry_order(self):
        text = _text(REGISTRY)
        rows = re.findall(r'Programme\("(\w+)", (\d+),', text)
        self.assertEqual(tuple(k for k, _c in sorted(rows, key=lambda r: int(r[1]))), P.RESETTLE_PROGRAMMES)
        self.assertEqual(set(P.RESETTLE_PROFILES), set(P.RESETTLE_PROGRAMMES))

    def test_shares_sum_to_one(self):
        for programme in P.RESETTLE_PROGRAMMES:
            for lf in (0.1, 0.35, 0.6):
                with self.subTest(programme=programme, lf=lf):
                    self.assertAlmostEqual(sum(self.shares(programme, lf).values()), 1.0, places=12)

    def test_families_are_the_family_kind(self):
        for programme in ("land_grants", "organized_colonization"):
            sh = self.shares(programme)
            for c, w in enumerate(P.MIGRANT_PROFILE["family"]["weights"]):
                self.assertAlmostEqual(sh.get((c, "f"), 0.0), w / 2, msg=programme)
                self.assertAlmostEqual(sh.get((c, "m"), 0.0), w / 2, msg=programme)

    def test_military_colonies_half_labour_at_eighty_percent_men(self):
        sh = self.shares("military_colonies")
        lab, fam = P.MIGRANT_PROFILE["labour"]["weights"], P.MIGRANT_PROFILE["family"]["weights"]
        for c in range(len(P.MIGRANT_CLASSES)):
            self.assertAlmostEqual(sh.get((c, "m"), 0.0), 0.5 * lab[c] * 0.8 + 0.5 * fam[c] * 0.5)
            self.assertAlmostEqual(sh.get((c, "f"), 0.0), 0.5 * lab[c] * 0.2 + 0.5 * fam[c] * 0.5)
        self.assertAlmostEqual(self.by_sex(sh, "m"), 0.65)

    def test_penal_transportation(self):
        """Mostly 15-35 (12% at 15-17, 78% at 18-35, 10% at 36-59: the controller's proposal, unconfirmed), 85% men:
        Australia's convicts, a fifth under 20."""
        sh = self.shares("penal_transportation")
        self.assertAlmostEqual(self.by_sex(sh, "m"), 0.85)
        for c, w in ((1, 0.12), (2, 0.78), (3, 0.10)):
            self.assertAlmostEqual(sh[(c, "f")] + sh[(c, "m")], w)
        self.assertNotIn((0, "f"), sh)
        self.assertNotIn((4, "m"), sh)

    def test_special_settlements_are_the_refugee_kind(self):
        sh = self.shares("special_settlements")
        for c, w in enumerate(P.MIGRANT_PROFILE["refugee"]["weights"]):
            self.assertAlmostEqual(sh[(c, "f")], w / 2)

    def test_development_program_sixty_families_forty_labour_by_the_jobs(self):
        for lf in (0.1, 0.45):
            sh = self.shares("development_program", lf)
            lab = P.MIGRANT_PROFILE["labour"]["weights"]
            fam = P.MIGRANT_PROFILE["family"]["weights"]
            for c in range(len(P.MIGRANT_CLASSES)):
                self.assertAlmostEqual(sh.get((c, "f"), 0.0), 0.6 * fam[c] / 2 + 0.4 * lab[c] * lf)
        # the labour share follows the destination's jobs as the residual's labour kind does (before its balance ramp)
        for fjob, fws in ((0.0, 0.1), (0.4, 0.25), (0.9, 0.48)):
            rights = fws / P.FULL_FEMALE_WORK_SHARE
            want = M.clamp(P.LABOUR_FEMALE_SHARE_MIN + fjob * rights
                           * (P.LABOUR_FEMALE_SHARE_MAX - P.LABOUR_FEMALE_SHARE_MIN),
                           P.LABOUR_FEMALE_SHARE_MIN, P.LABOUR_FEMALE_SHARE_MAX)
            self.assertAlmostEqual(RS.labour_female_share(fjob, fws), want)
        # and the script's value reads the same (te_demog_rs_labour_f, at the destination)
        eng = _engine_for(dataclasses.replace(INP, female_job_share=0.4), YEAR, POP)
        eng.vars["te_dg_fjob_share"] = 0.4
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_rs_labour_f")),
                               RS.labour_female_share(0.4, M.female_work_share(INP)))
        del eng.vars["te_dg_fjob_share"]
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_rs_labour_f")), P.LABOUR_FEMALE_SHARE_MIN)

    def test_rustication_is_ages_15_to_24_evenly(self):
        sh = self.shares("rustication")
        self.assertEqual(sh, {("youth", "f"): 0.5, ("youth", "m"): 0.5})
        self.assertEqual(P.RESETTLE_KINDS["youth"]["ages"], (15, 24))

    def test_managed_retreat_doubles_the_old(self):
        sh = self.shares("managed_retreat")
        ref = P.MIGRANT_PROFILE["refugee"]["weights"]
        total = sum(ref) + ref[-1]
        self.assertAlmostEqual(sh[(4, "f")] + sh[(4, "m")], 2 * ref[-1] / total)
        self.assertAlmostEqual(sh[(0, "f")] + sh[(0, "m")], ref[0] / total)


class TestWalkCounters(unittest.TestCase):
    """te_demog_rs_add (generated) books a month's movers as demographics_resettle.book does."""

    def test_add_matches_the_model(self):
        for code, programme in enumerate(P.RESETTLE_PROGRAMMES):
            for side, model_side in (("i", "in"), ("o", "out")):
                with self.subTest(programme=programme, side=side):
                    eng = _engine_for(INP, YEAR, POP)
                    eng.locals.update(te_dg_rs_code=float(code), te_dg_rs_amt=1700.0, te_dg_rs_lf=0.37)
                    eng.run(_parse_script(f"te_demog_rs_add = {{ SIDE = {side} }}"))
                    eng.run(_parse_script(f"te_demog_rs_add = {{ SIDE = {side} }}"))   # a second take adds on
                    c = RS.Counters()
                    RS.book(c, programme, 1700.0, model_side, 0.37)
                    RS.book(c, programme, 1700.0, model_side, 0.37)
                    want = c.inn if model_side == "in" else c.out
                    got = {k: v for k, v in eng.vars.items() if k.startswith(f"te_dg_rs_{side}_")}
                    self.assertEqual(set(got), {RSG._name(side, k) for k in want})
                    for key, v in want.items():
                        self.assertAlmostEqual(got[RSG._name(side, key)], v, delta=0.05, msg=key)

    def test_the_walk_books_both_ends_while_the_census_runs(self):
        take = squash(_block(_text(RESETTLEMENT), "resettlement_take_from_source"))
        self.assertIn("set_local_variable = { name = rs_moved_now value = 0 }", take)
        self.assertIn("change_local_variable = { name = rs_moved_now add = local_var:rs_move }", take)
        # after the move, then the consequences (which book the dead)
        self.assertLess(take.index("move_partial_pop"), take.index("rs_moved_now add"))
        self.assertLess(take.index("te_demog_rs_note_move = yes"), take.index("resettlement_source_consequences = yes"))
        dead = squash(_block(_text(RESETTLEMENT), "resettlement_source_consequences"))
        self.assertLess(dead.index("rs_death_carry subtract = local_var:rs_dead_people"),
                        dead.index("te_demog_rs_note_dead = yes"))
        note = squash(_block(_text(RESETTLE_EFFECTS), "te_demog_rs_note_move"))
        self.assertIn("te_demog_cohorts_run = yes", note)
        self.assertEqual(note.count("te_demog_has_census = yes"), 2, "each end only with a census")
        self.assertIn("te_demog_rs_add = { SIDE = o }", note)
        self.assertIn("scope:rs_destination = { if = { limit = { te_demog_has_census = yes } te_demog_rs_add = { SIDE = i }",
                      note)

    def test_the_events_kills_are_known_kills(self):
        """Review M4: Hard Winter's and the settlements' famine's dead reach the census as kills, not emigrants."""
        events = squash(_text(ROOT / "events" / "resettlement_events.txt"))
        for value, kill in (("1000", "kill_population_in_state = { value = 1000 strata = lower }"),
                            # the famine can't kill more farmers than the state holds (re-review)
                            ("{ value = 5000 max = resettlement_state_farmers }",
                             "kill_population_in_state = { value = 5000 pop_type = farmers }")):
            self.assertIn(f"hidden_effect = {{ te_demog_note_kills = {{ VALUE = {value} }} }} {kill}", events)

    def test_the_transit_dead_are_known_kills(self):
        """The 2026-10-09 gap: they reached the census through te_demog_note_kills, the strikes' path."""
        dead = squash(_block(_text(RESETTLE_EFFECTS), "te_demog_rs_note_dead"))
        self.assertIn("te_demog_note_kills = { VALUE = local_var:rs_dead_people }", dead)
        self.assertIn("te_demog_rs_total = { NAME = te_dg_rs_dead }", dead)
        self.assertLess(dead.index("te_demog_note_kills"), dead.index("te_demog_rs_add"))


class TestStepWithKnownMoves(unittest.TestCase):
    """te_demog_step with the script's own te_demog_flows and a state's counters, against demographics_resettle.step."""

    def setUp(self):
        self.ring = M.seed(INP, YEAR, POP)

    def run_both(self, counters, rest=3000.0, kills=0.0, eb=5000.0, ed=4200.0, fjob=0.3):
        ring = self.ring
        inp = dataclasses.replace(INP, female_job_share=fjob)
        residual = rest + counters.moved_in - counters.moved_out
        # what the engine did: the change holds the moves, the transit dead and the other kills
        pop = ring.total + eb - ed - kills - counters.dead + residual
        eng = _engine_for(inp, YEAR + 1, pop)
        eng.fixtures.update({"te_demog_crisis": 0.0,
                             "te_demog_family_transport": inp.mods.get(P.FAMILY_MIGRATION_TYPE, 0.0)})
        for k in range(P.RING_YEARS):
            if ring.f[k] or ring.m[k]:
                eng.vars[f"te_dg_f{k}"], eng.vars[f"te_dg_m{k}"] = ring.f[k] * ring.scale, ring.m[k] * ring.scale
        balance = M.structure(ring)["men_per_100_women"]
        eng.vars.update(te_dg_pf=ring.pool_f, te_dg_pm=ring.pool_m, te_dg_pa=ring.pool_age, te_dg_scale=1.0,
                        te_dg_year=YEAR, te_dg_people=ring.total, te_dg_raw=ring.total, te_dg_sex_balance=balance,
                        te_dg_faw=ring.faw, te_dg_fam=ring.fam, te_dg_pop_last=ring.total, te_dg_eb=eb, te_dg_ed=ed,
                        te_dg_fjob_share=fjob)
        for c in range(len(P.MIGRANT_CLASSES)):
            eng.vars[f"te_dg_cf{c}"], eng.vars[f"te_dg_cm{c}"] = ring.class_f[c], ring.class_m[c]
        for b, (bf, bm) in enumerate(zip(*M.band_sums(ring))):
            eng.vars[f"te_dg_bf{b}"], eng.vars[f"te_dg_bm{b}"] = bf, bm
        all_kills = kills + counters.dead
        if all_kills:
            eng.vars["te_dg_kills_in"] = all_kills
        eng.vars.update(_counter_vars(counters))
        eng.call("te_demog_step")
        model = M.Ring(**{f.name: getattr(ring, f.name) for f in dataclasses.fields(M.Ring)})
        model.f, model.m = list(ring.f), list(ring.m)
        model.class_f, model.class_m = list(ring.class_f), list(ring.class_m)
        inp = dataclasses.replace(inp, crisis=0.0)
        figures, rest_banded, net = RS.step(model, inp, YEAR + 1, counters, engine_pop=pop, kills=all_kills,
                                            residual=residual)
        return eng, model, figures, rest_banded, net

    def check(self, eng, model, rel=2e-6):
        raw = model.pool_f + model.pool_m
        for k in range(P.RING_YEARS):
            a = model.age_of_slot(k)
            if f"te_dg_f{k}" not in eng.vars:
                # the script drops a cohort under half a person; the model keeps it
                self.assertTrue(model.f[k] < 0.5 and model.m[k] < 0.5, a)
                continue
            raw += model.f[k] + model.m[k]
            for s, got, want in (("f", eng.vars[f"te_dg_f{k}"], model.f[k]), ("m", eng.vars[f"te_dg_m{k}"], model.m[k])):
                self.assertLessEqual(abs(got - want), rel * max(abs(want), 1.0), f"{s} aged {a}: {got} vs {want}")
        self.assertLessEqual(abs(eng.vars["te_dg_scale"] - model.total / raw), rel, "the scale")
        for name in RSG.counter_names():
            self.assertNotIn(name, eng.vars, "the step takes and removes the counters")

    def test_no_counters_is_the_plain_step(self):
        eng, model, _f, rest, net = self.run_both(RS.Counters())
        self.check(eng, model)
        self.assertAlmostEqual(eng.vars["te_dg_net_migration"], net)
        self.assertNotIn("te_dg_rs_net", eng.vars)

    def test_land_grants_arrivals_by_the_family_profile(self):
        c = RS.Counters()
        RS.book(c, "land_grants", 9000.0, "in")
        eng, model, _f, rest, net = self.run_both(c, rest=2500.0)
        self.check(eng, model)
        self.assertAlmostEqual(rest, 2500.0)
        # the known net is kept apart for the offline re-walk (demographics_rebook.booked_residual)
        self.assertAlmostEqual(eng.vars["te_dg_rs_net"], 9000.0, places=3)
        import demographics_rebook as RB
        self.assertAlmostEqual(RB.booked_residual(eng.vars), 2500.0, places=3)
        self.assertAlmostEqual(eng.vars["te_dg_net_migration"], 2500.0 + 9000.0, places=3)
        self.assertAlmostEqual(eng.vars["te_dg_mig_raw"], 2500.0 + 9000.0, places=3)

    def test_arrivals_bypass_the_residuals_cap(self):
        """A known move is a count: 30,000 men aged 18-35 into 200,000 people pass the 5% cap."""
        c = RS.Counters()
        RS.book(c, "penal_transportation", 30000.0, "in")
        before = RS.men_per_100(self.ring, 18, 35)
        eng, model, *_ = self.run_both(c, rest=0.0)
        self.check(eng, model)
        self.assertGreater(RS.men_per_100(model, 19, 36), before + 20)

    def test_penal_departures_and_their_dead_leave_by_the_profile(self):
        c = RS.Counters()
        RS.book(c, "penal_transportation", 6000.0, "out")
        RS.book(c, "penal_transportation", 300.0, "out", dead=True)
        eng, model, figures, rest, net = self.run_both(c, rest=-1500.0, kills=200.0)
        self.check(eng, model)
        self.assertAlmostEqual(rest, -1500.0)
        self.assertAlmostEqual(eng.vars["te_dg_net_migration"], -1500.0 - 6000.0, places=3)
        # every kill is counted as killed (the Causes of Death slice); only the others come from every age
        self.assertAlmostEqual(eng.vars["te_dg_dc_kill"], 500.0, places=3)
        self.assertAlmostEqual(figures["causes"]["kills"], 500.0, places=6)

    def test_rustication_by_single_years_15_to_24(self):
        c = RS.Counters()
        RS.book(c, "rustication", 8000.0, "out")
        RS.book(c, "rustication", 100.0, "out", dead=True)
        plain = M.Ring(**{f.name: getattr(self.ring, f.name) for f in dataclasses.fields(M.Ring)})
        plain.f, plain.m = list(self.ring.f), list(self.ring.m)
        eng, model, *_ = self.run_both(c, rest=0.0)
        self.check(eng, model)
        # ages 16-25 after the step (rate ages 15-24) lost people beside the plain step's; 15 and 26 did not
        M.step(plain, dataclasses.replace(INP, female_job_share=0.3, crisis=0.0), YEAR + 1)
        for a, lost in ((15, False), (16, True), (25, True), (26, False)):
            k = (YEAR + 1 - a) % P.RING_YEARS
            ratio = model.f[k] / plain.f[k]
            self.assertTrue((ratio < 0.99) if lost else (ratio > 0.995), (a, ratio))

    def test_development_program_and_managed_retreat(self):
        c = RS.Counters()
        RS.book(c, "development_program", 7000.0, "in", RS.labour_female_share(0.3, M.female_work_share(INP)))
        RS.book(c, "managed_retreat", 2000.0, "in")
        eng, model, *_ = self.run_both(c, rest=-900.0)
        self.check(eng, model)

    def test_a_frontier_filling_fast_keeps_its_census(self):
        """The census has no size test any more (owner, 2026-10-20), so a frontier that grows by more than a quarter
        in a year by resettlement steps like any other state, and the known moves still skip the residual's caps (the
        step's te_demog_rs_take; TestStepWithKnownMoves). The value the old test subtracted had no other reader."""
        census = squash(_block(_text(EFFECTS), "te_demog_state_census"))
        for gone in ("te_demog_rs_known_change", "te_dg_over", "te_dg_under"):
            self.assertNotIn(gone, census)
        self.assertNotIn("te_demog_rs_known_change", _text(RS_VALUES))
        self.assertIn("te_demog_rs_take = yes", _block(_text(EFFECTS), "te_demog_flows"))

    def test_a_seed_clears_the_counters(self):
        c = RS.Counters()
        RS.book(c, "land_grants", 900.0, "in")
        eng = _engine_for(INP, YEAR, POP)
        eng.vars.update(_counter_vars(c))
        eng.vars["te_dg_rs_net"] = 900.0
        eng.call("te_demog_seed")
        for name in RSG.counter_names() + ["te_dg_rs_net"]:
            self.assertNotIn(name, eng.vars)

    def test_the_census_gates_the_counters(self):
        for name in ("te_demog_rs_note_move", "te_demog_rs_note_dead"):
            self.assertIn("te_demog_cohorts_run = yes", squash(_block(_text(RESETTLE_EFFECTS), name)), name)

    def test_the_self_check_compares_the_rest_with_the_arrivals(self):
        """One-sided (review, 2026-10-20): BROKEN only when the rest is below -0.25 x the arrivals, so a continued
        save's partial-year counters and the engine's own immigration (both positive) read OK."""
        body = squash(_block(_text(RESETTLE_EFFECTS), "te_demog_rs_selfcheck"))
        self.assertIn("TE_SELF_CHECK OK resettle_moves_booked", body)
        self.assertIn("TE_SELF_CHECK BROKEN resettle_moves_booked", body)
        self.assertIn("set_local_variable = { name = te_dg_rs_chk_floor value = { value = local_var:te_dg_rs_in "
                      "multiply = -0.25 } }", body)
        self.assertIn("limit = { local_var:te_dg_mig >= local_var:te_dg_rs_chk_floor }", body)
        self.assertLess(body.index("TE_SELF_CHECK OK"), body.index("TE_SELF_CHECK BROKEN"))
        self.assertIn("NOT = { has_global_variable = te_demog_rs_selfcheck_done }", body)
        flows = squash(_block(_text(EFFECTS), "te_demog_flows"))
        self.assertLess(flows.index("te_demog_rs_take = yes"), flows.index("name = te_dg_kill value"))
        self.assertLess(flows.index("set_variable = { name = te_dg_mig_raw"), flows.index("te_demog_rs_selfcheck = yes"))


class TestFrontierSeed(unittest.TestCase):
    """§2.6: the US frontier starts young and male (owner, 2026-10-19: history data)."""

    def seed_both(self, region, reseed=False):
        eng = _engine_for(INP, 1836, POP, place=(region, None))
        eng.vars["te_dg_frontier"] = 1.0
        if reseed:
            eng.vars["te_dg_reseed"] = 1.0
        eng.call("te_demog_seed")
        with unittest.mock.patch.object(M, "growth_factor", lambda nrr: eng.locals["te_dg_d"]):
            ring = RS.frontier_seed(INP, 1836, POP, region)
        return eng, ring

    def test_the_seed_matches_the_model(self):
        eng, ring = self.seed_both("STATE_WISCONSIN")
        for a, f, m in ring.by_age()[:-1]:
            k = (1836 - a) % P.RING_YEARS
            if f"te_dg_f{k}" not in eng.vars:
                continue
            self.assertAlmostEqual(eng.vars[f"te_dg_f{k}"], f, delta=1e-4 * max(f, 1), msg=a)
            self.assertAlmostEqual(eng.vars[f"te_dg_m{k}"], m, delta=1e-4 * max(m, 1), msg=a)
        for c in range(len(P.MIGRANT_CLASSES)):
            self.assertAlmostEqual(eng.vars[f"te_dg_cm{c}"], ring.class_m[c], delta=1e-4 * ring.class_m[c])

    def test_men_per_woman_by_age_group_and_the_people_kept(self):
        for region, row in P.FRONTIER_1836.items():
            with self.subTest(region=region):
                ring = RS.frontier_seed(INP, 1836, POP, region)
                self.assertAlmostEqual(ring.people(), POP, places=3)
                for (lo, hi), ratio in row["ratios"].items():
                    self.assertAlmostEqual(RS.men_per_100(ring, lo, min(hi, 149)), 100 * ratio, places=6)
                plain = M.seed(INP, 1836, POP)
                self.assertAlmostEqual(RS.men_per_100(ring, 0, 14), RS.men_per_100(plain, 0, 14), places=6)

    def test_the_figures_are_the_censuss(self):
        """Wisconsin Territory's settlers aged 20-29: 6,328 men and 2,713 women (233 per 100); its 1836 pops are 78%
        settlers and the rest near even, so the state starts at 190 (the exact mixture, review 2026-10-20)."""
        r, s = 6328 / 2713, 28004 / 36004
        mixed = (s * r / (1 + r) + (1 - s) / 2) / (s / (1 + r) + (1 - s) / 2)
        self.assertAlmostEqual(P.FRONTIER_1836["STATE_WISCONSIN"]["ratios"][(20, 29)], mixed)
        self.assertAlmostEqual(mixed, 1.903, places=3)
        # the mixture: settlers' men and women over everyone's, at one to one for the rest
        men, women = s * r / (1 + r), s / (1 + r)
        self.assertAlmostEqual(P.frontier_mix(r, s), (men + (1 - s) / 2) / (women + (1 - s) / 2))
        self.assertAlmostEqual(P.frontier_mix(r, 1.0), r)
        self.assertAlmostEqual(P.frontier_mix(r, 0.0), 1.0)
        self.assertEqual(set(P.FRONTIER_1836), set(P.FRONTIER_1840_WHITE))
        self.assertEqual(set(P.FRONTIER_1836), {"STATE_MICHIGAN", "STATE_INDIANA", "STATE_ILLINOIS", "STATE_MISSOURI",
                                                "STATE_ARKANSAS", "STATE_IOWA", "STATE_WISCONSIN", "STATE_MISSISSIPPI",
                                                "STATE_ALABAMA", "STATE_LOUISIANA", "STATE_FLORIDA"})

    def test_the_old_southwest_and_florida(self):
        """Added 2026-10-20 (owner): every state the US holds in 1836 whose 1840 free white men per 100 women aged 15-49
        were 110 or more. Their rows sum, with the under-15s the seed leaves alone, to each state's official white total
        (Gibson and Jung, Table A-21); the settlers are dixie of every religion and Louisiana's cajun."""
        under_15 = {"STATE_MISSISSIPPI": (19542 + 14164 + 11475, 18235 + 13328 + 10919),
                    "STATE_ALABAMA": (36611 + 28215 + 22819, 33917 + 26804 + 21786),
                    "STATE_LOUISIANA": (13835 + 10736 + 7848, 13718 + 10395 + 7760),
                    "STATE_FLORIDA": (2455 + 1947 + 1520, 2241 + 1761 + 1448)}
        official = {"STATE_MISSISSIPPI": 179074, "STATE_ALABAMA": 335185, "STATE_LOUISIANA": 158457,
                    "STATE_FLORIDA": 27943}
        ratio_15_49 = {"STATE_MISSISSIPPI": 131.6, "STATE_ALABAMA": 116.2, "STATE_LOUISIANA": 155.7,
                       "STATE_FLORIDA": 177.3}
        for region, total in official.items():
            with self.subTest(region=region):
                rows = P.FRONTIER_1840_WHITE[region]
                self.assertEqual(sum(m + f for m, f in rows.values()) + sum(under_15[region]), total)
                m = sum(rows[a][0] for a in ((15, 19), (20, 29), (30, 39), (40, 49)))
                f = sum(rows[a][1] for a in ((15, 19), (20, 29), (30, 39), (40, 49)))
                self.assertAlmostEqual(100 * m / f, ratio_15_49[region], places=1)
                self.assertGreaterEqual(100 * m / f, 110)
        self.assertAlmostEqual(P.FRONTIER_SETTLER_SHARE["STATE_LOUISIANA"], (35992 + 118392 + 200) / 294684)
        self.assertAlmostEqual(P.FRONTIER_SETTLER_SHARE["STATE_MISSISSIPPI"], 172804 / 260804)
        # Mississippi's settlers aged 20-29, 20,084 men and 14,464 women, mixed with a third of its people enslaved
        r, s = 20084 / 14464, 172804 / 260804
        self.assertAlmostEqual(P.FRONTIER_1836["STATE_MISSISSIPPI"]["ratios"][(20, 29)], P.frontier_mix(r, s))

    def test_an_unlisted_region_seeds_as_before(self):
        eng = _engine_for(INP, 1836, POP, place=("STATE_OHIO", None))
        eng.vars["te_dg_frontier"] = 1.0
        eng.call("te_demog_seed")
        plain = _engine_for(INP, 1836, POP, place=("STATE_OHIO", None))
        plain.call("te_demog_seed")
        for k, v in plain.vars.items():
            self.assertAlmostEqual(eng.vars[k], v, msg=k)

    def test_the_pulse_reseed_takes_the_mark_off(self):
        eng, _ring = self.seed_both("STATE_MICHIGAN")
        self.assertIn("te_dg_frontier", eng.vars, "the game start's seed keeps it for the first pulse's")
        eng, _ring = self.seed_both("STATE_MICHIGAN", reseed=True)
        self.assertNotIn("te_dg_frontier", eng.vars)

    def test_history_marks_the_us_states(self):
        text = squash(_text(HISTORY))
        self.assertIn("c:USA ?= { every_scope_state = { limit = { te_demog_frontier_listed > 0 } "
                      "set_variable = te_dg_frontier } }", text)
        listed = squash(_block(_text(RS_VALUES), "te_demog_frontier_listed"))
        for region in P.FRONTIER_1836:
            self.assertIn(f"state_region = s:{region}", listed)
        start = squash(_block(_text(EFFECTS), "te_demog_country_game_start"))
        self.assertIn("remove_variable = te_dg_frontier", start)


if __name__ == "__main__":
    unittest.main()
