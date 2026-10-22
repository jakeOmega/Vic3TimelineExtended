"""Deaths by cause (issue #1029): the census's split of last year's deaths, for the Causes of Death sections.

The estimate (method a): each natural cause's deaths at the step's rates over the last count's bands
(demographics_model.cause_deaths_estimate; the generated te_demog_cause_deaths_estimate), scaled to the census's own
deaths from those causes; under Full the deaths the engine added on top count under their causes (owner, 2026-10-22:
te_dg_ot_<c>, the walk's split by the effects' tags), devastation's beside the war dead; childbirth's, the war dead and
the people killed by events as counted (demographics_model.cause_deaths; te_demog_cause_deaths_store). The country sums its states' and keeps the cause
multipliers, Health Care Access and childbirth's rate people- or births-weighted (te_demog_country_census). These run
the script through test_demographics_registry's _Engine against the model.
"""

import dataclasses
import re
import sys
import unittest

import test_demographics_registry as R  # noqa: E402  (its TestCases by attribute only, so they don't run twice here)
from test_demographics_registry import (EFFECTS, GENERATED_EFFECTS, ROOT, _block, _CountryEngine, _engine_for,  # noqa: E402
                                        _text)

sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import gen_demographics as G  # noqa: E402

CONSOLE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"
SLICES = ("inf", "ext", "chr", "work", "mat", "war", "kill")
CAUSE_SHORT = {"infection": "inf", "external": "ext", "chronic": "chr", "work": "work"}
MODEL_KEY = {"inf": "infection", "ext": "external", "chr": "chronic", "work": "work", "mat": "maternal",
             "war": "war", "kill": "kills"}
# a window's deaths on top by cause, people (te_dg_ot_<c>): famine and pollution, a mine's lines, devastation; aid saved some
CAUSES_ON_TOP = {"inf": 900.0, "chr": 400.0, "ext": -150.0, "work": 250.0, "war": 600.0}


def close(case, got, want, rel=1e-6, what=""):
    case.assertLessEqual(abs(got - want), rel * max(abs(want), 1.0), f"{what}: {got} vs {want}")


class TestBandRates(unittest.TestCase):
    """demographics_model.band_cause_rates: the bands of one age group take its rates exactly."""

    def test_a_band_of_one_group_takes_its_rates(self):
        rates = M.band_cause_rates()
        tables = {"infection": P.INFECTION, "external": P.EXTERNAL, "chronic": P.CHRONIC,
                  "work": {"f": P.WORK_BASE, "m": P.WORK_BASE}}
        for b in range(1, P.BANDS - 1):
            (g,) = M.band_groups(b)
            self.assertEqual(P.GROUPS[g][0], 5 * b)
            for cause, table in tables.items():
                for s in "fm":
                    self.assertEqual(rates[cause][s][b], table[s][g], (cause, s, b))

    def test_the_two_open_bands_lie_between_their_groups(self):
        rates = M.band_cause_rates()
        self.assertEqual(M.band_groups(0), [0, 1])
        self.assertEqual([P.GROUPS[g][0] for g in M.band_groups(P.BANDS - 1)], list(range(85, 150, 5)))
        for s in "fm":
            inf = rates["infection"][s][0]
            self.assertLess(P.INFECTION[s][1], inf)
            self.assertLess(inf, P.INFECTION[s][0])
            # most of 85 and over is 85-89: the chronic rate sits near its start, well short of the oldest groups'
            chr_ = rates["chronic"][s][P.BANDS - 1]
            self.assertLess(P.CHRONIC[s][18], chr_)
            self.assertLess(chr_, P.CHRONIC[s][20])

    def test_the_generated_estimate_carries_the_table(self):
        body = _block(_text(GENERATED_EFFECTS), "te_demog_cause_deaths_estimate")
        rates = M.band_cause_rates()
        for cause, short in CAUSE_SHORT.items():
            m = re.search(rf"name = te_dg_ce_{short}\s+value = \{{(.*?)\n\t\}}", body, re.S)
            self.assertIsNotNone(m, short)
            terms = re.findall(r"var:te_dg_b([fm])(\d+)\s+multiply = ([\d.]+)", m.group(1))
            want = {(s, b): G.lit(rates[cause][s][b]) for s in "fm" for b in range(P.BANDS) if rates[cause][s][b]}
            self.assertEqual({(s, int(b)): v for s, b, v in terms}, want, cause)
        self.assertIn("multiply = local_var:te_dg_m_work_f", body)
        self.assertIn("multiply = local_var:te_dg_m_work_m", body)
        self.assertEqual(G.render_effects().count("te_demog_cause_deaths_estimate = {"), 1)


class TestModel(unittest.TestCase):
    RAW = {"infection": 300.0, "external": 40.0, "chronic": 200.0, "work": 10.0}

    def test_the_slices_add_up_to_the_deaths_with_the_war_dead_and_the_killed(self):
        for on_top in (None, {"inf": 30.0, "chr": 12.0, "ext": -4.0, "work": 6.0, "war": 25.0}):
            with self.subTest(on_top=on_top):
                out = M.cause_deaths(self.RAW, deaths=600.0, maternal=20.0, war_dead=50.0, kills=7.0, on_top=on_top,
                                     engine=640.0)
                self.assertAlmostEqual(out["total"], 657.0)
                self.assertAlmostEqual(sum(out[MODEL_KEY[s]] for s in SLICES), out["total"])
                self.assertAlmostEqual(out["fit"], 550.0 / 580.0)
                if on_top is None:
                    # the shares of the four follow the estimate's, and nothing is on top
                    self.assertAlmostEqual(out["infection"] / out["chronic"], 1.5)
                    self.assertEqual(out["war"], 50.0)
                    self.assertEqual(set(out["on_top"].values()), {0.0})

    def test_each_cause_takes_its_own_on_top(self):
        """Owner, 2026-10-22: the window's deaths on top by cause, on the census's count by the window's deaths (580 of
        640 here); war's join the war dead, the rest of the deaths split by the estimate."""
        on_top = {"inf": 64.0, "chr": 32.0, "ext": 0.0, "work": 16.0, "war": 32.0}
        out = M.cause_deaths(self.RAW, deaths=600.0, maternal=20.0, war_dead=50.0, on_top=on_top, engine=640.0)
        k = 580.0 / 640.0
        rest = 580.0 - 144.0 * k
        self.assertAlmostEqual(out["on_top"]["inf"], 64.0 * k)
        self.assertAlmostEqual(out["infection"], rest * 300 / 550 + 64.0 * k)
        self.assertAlmostEqual(out["chronic"], rest * 200 / 550 + 32.0 * k)
        self.assertAlmostEqual(out["external"], rest * 40 / 550)
        self.assertAlmostEqual(out["war"], 50.0 + 32.0 * k)

    def test_the_estimate_is_read_through_the_scales(self):
        """The estimate is at the step's rates, each cause's multiplier scaled by its own on-top share: the rest splits
        by the model's own deaths, the estimate over each scale."""
        scales = {"infection": 2.0, "external": 1.0, "chronic": 1.0, "work": 1.0}
        raw = dict(self.RAW, infection=600.0)
        out = M.cause_deaths(raw, deaths=600.0, maternal=20.0, scales=scales)
        self.assertAlmostEqual(out["infection"] / out["chronic"], 1.5)

    def test_the_scales_add_what_one_scale_did(self):
        """cause_scales: each cause takes its own share of dz on its own deaths; the rest (war's, the census's lag) on all
        four. The four then add E x (1 + dz), as one scale on all did. No estimate or no shares: one scale."""
        shares = {"inf": 0.1, "chr": 0.05, "ext": -0.01, "work": 0.02, "war": 0.1}
        for dz in (0.3, 0.0, -0.2):
            with self.subTest(dz=dz):
                s = M.cause_scales(dz, shares, self.RAW)
                e = sum(self.RAW.values())
                self.assertAlmostEqual(sum(self.RAW[c] * s[c] for c in self.RAW), e * (1 + dz))
                rest = dz - 0.16
                self.assertAlmostEqual(s["infection"], 1 + rest + 0.1 * e / 300)
        self.assertEqual(M.cause_scales(0.3, None, self.RAW), {c: 1.3 for c in self.RAW})
        self.assertEqual(M.cause_scales(0.3, shares, None), {c: 1.3 for c in self.RAW})
        # a cause the model gives under a death can't take its own: they join the rest
        s = M.cause_scales(0.3, shares, dict(self.RAW, work=0.5))
        self.assertAlmostEqual(s["work"], 1 + 0.3 - 0.14)

    def test_the_estimate_matches_the_sweep_away_from_the_open_bands(self):
        """A run's last step: the estimate over last count's bands comes within a few per cent of the sweep's deaths
        (0-4 and 85+ are the only approximate bands), the self-check's 0.9-1.1."""
        for inp in (M.Inputs(sol=8, literacy=0.1, urban_share=0.05),
                    M.Inputs(sol=40, literacy=0.98, urban_share=0.8,
                             techs=frozenset({"medical_degrees", "antibiotics", "modern_vaccines"}))):
            ring = M.seed(inp, 1836, 1e6)
            for year in range(1837, 1897):
                out = M.step(ring, inp, year)
            fit = out["causes"]["fit"]
            self.assertLess(abs(fit - 1), 0.05, fit)
            self.assertAlmostEqual(out["causes"]["total"], out["deaths"], delta=1e-6 * out["deaths"])

    def test_a_replay_has_no_causes(self):
        inp = M.Inputs()
        ring = M.seed(inp, 1836, 1e5)
        qf, qm, mmr = M.group_rates(inp)
        out = M.step(ring, inp, 1837, rates=(qf, qm, mmr, 5.0, M.migrant_profile(inp)))
        self.assertIsNone(out["causes"])


class TestScript(unittest.TestCase):
    """The step's te_dg_dc_* against the model's, from the same ring (TestCohortScript.step_both)."""

    @classmethod
    def setUpClass(cls):
        cls.cohort = R.TestCohortScript()

    def check(self, eng, figures, war=0.0, kills=0.0):
        want = figures["causes"]
        for s in SLICES:
            close(self, eng.vars[f"te_dg_dc_{s}"], want[MODEL_KEY[s]], what=s)
        close(self, eng.vars["te_dg_dc_total"], eng.vars["te_dg_deaths"] + war + kills, what="total")
        close(self, eng.vars["te_dg_dc_fit"], want["fit"], what="fit")
        # the war dead as counted, and under Full devastation's civilians beside them (owner, 2026-10-22)
        close(self, eng.vars["te_dg_dc_war"], war + max(0.0, eng.vars.get("te_dg_dc_war_top", 0.0)), what="war")
        self.assertEqual(eng.vars["te_dg_dc_kill"], kills)

    def test_a_step_without_flows(self):
        eng, _ring, figures, _pop = self.cohort.step_both()
        self.check(eng, figures)
        for c in P.DEATH_CAUSES:
            self.assertEqual(eng.vars[f"te_dg_dc_{c}_top"], 0.0, c)

    def test_a_step_with_war_dead_and_kills(self):
        eng, _ring, figures, _pop = self.cohort.step_both(war_dead=900.0, kills=1500.0, migration=4000.0)
        self.check(eng, figures, war=900.0, kills=1500.0)

    def test_the_script_takes_its_own_flows(self):
        flows = dict(eb=0.0, ed=0.0, crisis=0.0, fjob_share=0.3, migration=0.0, war=400.0, kills=60.0)
        eng, _ring, figures, _pop = self.cohort.step_both(flows=flows)
        self.check(eng, figures, war=400.0, kills=60.0)

    def test_adults_infection_takes_its_factor(self):
        """#1045: with medicine, infection at 15-64 takes te_dg_inf_ad too, in the rates and in the estimate."""
        inp = dataclasses.replace(R.TestCohortScript.INP, mods={P.ACCESS_TYPE: 0.5, P.TREATMENT_TYPE["infection"]: 0.9})
        self.assertLess(M.infection_adult(inp), 0.7)
        eng, _ring, figures, _pop = self.cohort.step_both(inp=inp)
        self.check(eng, figures)

    def test_the_hover_names_the_adults_ages(self):
        """#1045: the state's infection hover names the ages P.INFECTION_ADULT_AGES gives."""
        lo, hi = P.INFECTION_ADULT_AGES
        line = re.search(r'(?m)^ te_demog_st_inf_adult_line:0 "(.*)"$', _text(R.MISC_LOC)).group(1)
        self.assertIn(f"Aged {lo}–{hi - 1},", line)
        self.assertIn("ScriptValue('te_demog_infection_adult')", line)

    def test_deaths_on_top_without_a_split_spread_over_the_causes(self):
        """A first count under Full (no split by cause yet): the deaths on top spread over the four by the estimate, as
        do deaths the game took away; there is no slice of their own."""
        for dz in (0.12, -0.2):
            with self.subTest(dz=dz):
                eng, _ring, figures, _pop = self.cohort.step_both(on_top=(0.05, dz), full=True)
                self.check(eng, figures)
                self.assertNotIn("te_dg_dc_ontop", eng.vars)
                four = sum(eng.vars[f"te_dg_dc_{s}"] for s in ("inf", "ext", "chr", "work"))
                close(self, four, eng.vars["te_dg_deaths"] - eng.vars["te_dg_dc_mat"], what="the four")

    def test_deaths_on_top_count_under_their_causes(self):
        """Owner, 2026-10-22: the walk's split by cause (te_dg_ot_<c>) places each cause's deaths on top on its own
        ages, so the ring matches the model's, and the slices take them, devastation's beside the war dead."""
        eng, ring, figures, pop = self.cohort.step_both(on_top=(0.05, 0.12), full=True, causes=CAUSES_ON_TOP)
        self.cohort.check_step(eng, ring, figures, pop)
        self.check(eng, figures)
        nat = eng.vars["te_dg_deaths"] - eng.vars["te_dg_dc_mat"]
        k = nat / eng.vars["te_dg_ed"]
        for c, v in CAUSES_ON_TOP.items():
            close(self, eng.vars[f"te_dg_dc_{c}_top"], v * k, rel=1e-4, what=f"{c} on top")
            close(self, eng.vars[f"te_dg_dc_{c}_top"], figures["causes"]["on_top"][c], rel=1e-4, what=f"{c} model")
        close(self, eng.vars["te_dg_dc_war"], 600.0 * k, rel=1e-4, what="devastation's civilians")
        # the deaths on top count in their causes' slices, not spread over all four
        flat, _r, flat_figures, _p = self.cohort.step_both(on_top=(0.05, 0.12), full=True)
        self.assertGreater(eng.vars["te_dg_dc_inf"] / eng.vars["te_dg_dc_ext"],
                           flat.vars["te_dg_dc_inf"] / flat.vars["te_dg_dc_ext"])
        # one scale or per cause, the ring adds about the same deaths (the four add E x (1 + dz) at linear order)
        close(self, eng.vars["te_dg_deaths"], flat.vars["te_dg_deaths"], rel=0.02, what="the ring's deaths")

    def test_each_causes_multiplier_takes_its_own_scale(self):
        """te_demog_on_top_scales against demographics_model.cause_scales, from the estimate at the model's rates."""
        eng, ring, figures, pop = self.cohort.step_both(on_top=(0.05, 0.12), full=True, causes=CAUSES_ON_TOP)
        inp = R.TestCohortScript.INP
        cm = M.cause_multipliers(inp)
        wf, wm = M.work_split(inp, cm["work"])
        raw = M.cause_deaths_estimate(*M.band_sums(eng.ring_before), cm, wf, wm, M.infection_adult(inp))
        want = M.cause_scales(0.12, M.on_top_shares(CAUSES_ON_TOP, 30.0 * pop / 1000), raw)
        for c, s in CAUSE_SHORT.items():
            close(self, eng.locals[f"te_dg_sg_{s}"], want[c], rel=1e-3, what=c)
        self.assertGreater(want["infection"], want["external"], "infection takes the famine, accidents the aid")

    def test_a_seed_has_none(self):
        eng = _engine_for(R.TestCohortScript.INP, 1836, 250000.0)
        eng.vars["te_dg_dc_fit"] = 0.97
        eng.call("te_demog_seed")
        for s in SLICES + ("total",):
            self.assertEqual(eng.vars[f"te_dg_dc_{s}"], 0.0, s)
        self.assertNotIn("te_dg_dc_fit", eng.vars)

    def test_the_estimate_reads_last_counts_bands_before_the_sweep(self):
        begin = _block(_text(EFFECTS), "te_demog_step_begin")
        # at the model's rates, before the scales place each cause's deaths on top by it (owner, 2026-10-22)
        self.assertLess(begin.index("te_demog_cause_deaths_estimate = yes"), begin.index("te_demog_on_top_scales = yes"))
        finish = _block(_text(EFFECTS), "te_demog_step_finish")
        self.assertLess(finish.index("te_demog_cause_deaths_store = yes"), finish.index("te_demog_set_scale = yes"))
        self.assertGreater(finish.index("te_demog_cause_deaths_store = yes"),
                           finish.index("set_variable = { name = te_dg_deaths value = local_var:te_dg_deaths }"))


class TestCountryCauses(unittest.TestCase):
    """The country's census sums its states' slices and weights the multipliers, access and childbirth's rate."""

    def census(self, states):
        eng = _CountryEngine(states=states, fixtures={"year": 1900.0, "te_demog_female_work_share": 0.25},
                             triggers={"is_ai": True, "te_demog_cohorts_run": True})
        eng.call("te_demog_country_census")
        return eng.vars

    def states(self):
        a = R.TestCountry.state(4_000_000, 1_600_000, 22, 0.55, rank=1)
        b = R.TestCountry.state(1_000_000, 200_000, 12, 0.2, rank=2)
        for st, k in ((a, 1.0), (b, 3.0)):
            for i, s in enumerate(SLICES):
                st[f"te_dg_dc_{s}"] = k * (i + 1) * 100.0
            st["te_dg_dc_total"] = sum(st[f"te_dg_dc_{s}"] for s in SLICES)
        a.update(te_dg_m_inf=0.5, te_dg_m_ext=0.8, te_dg_m_chr=0.6, te_dg_m_work=1.0, te_dg_m_mat=300.0, te_dg_acc=0.6,
                 te_dg_births=100_000.0)
        b.update(te_dg_m_inf=1.0, te_dg_m_ext=1.2, te_dg_m_chr=1.0, te_dg_m_work=2.0, te_dg_m_mat=600.0, te_dg_acc=0.2,
                 te_dg_births=50_000.0)
        return a, b

    def test_the_slices_are_summed(self):
        v = self.census(list(self.states()))
        for i, s in enumerate(SLICES):
            self.assertAlmostEqual(v[f"te_dg_dc_{s}"], 4 * (i + 1) * 100.0, places=3)
        self.assertAlmostEqual(v["te_dg_dc_total"], sum(v[f"te_dg_dc_{s}"] for s in SLICES), places=3)

    def test_the_rates_are_weighted(self):
        v = self.census(list(self.states()))
        self.assertAlmostEqual(v["te_dg_m_inf"], (4 * 0.5 + 1 * 1.0) / 5, places=4)
        self.assertAlmostEqual(v["te_dg_m_work"], (4 * 1.0 + 1 * 2.0) / 5, places=4)
        self.assertAlmostEqual(v["te_dg_acc"], (4 * 0.6 + 1 * 0.2) / 5, places=4)
        # childbirth's by births
        self.assertAlmostEqual(v["te_dg_m_mat"], (100_000 * 300 + 50_000 * 600) / 150_000, places=3)

    def test_a_state_from_before_the_build_adds_no_slices_and_no_access(self):
        a, b = self.states()
        for s in SLICES + ("total",):
            del b[f"te_dg_dc_{s}"]
        del b["te_dg_acc"]
        v = self.census([a, b])
        self.assertAlmostEqual(v["te_dg_dc_inf"], 100.0, places=3)
        self.assertAlmostEqual(v["te_dg_acc"], 0.6, places=4)

    def test_the_outline_takes_the_stored_multipliers(self):
        census = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertIn("set_local_variable = { name = te_dg_m_inf value = var:te_dg_m_inf }", census)
        self.assertLess(census.index("set_variable = { name = te_dg_m_inf value ="),
                        census.index("set_local_variable = { name = te_dg_m_inf value = var:te_dg_m_inf }"))

    def test_the_adults_infection_factor_is_weighted_and_reaches_the_outline(self):
        """#1045: the country's te_dg_inf_ad is its states' factor by people x their infection multiplier, so the pair
        multiplies to their adults' infection (a state with no medicine stored at 1), and the player's outline reads it:
        with it the outline's adults die less."""
        def outline(trt_a, trt_b):
            a, b = self.states()
            a["te_dg_trt_inf"], b["te_dg_trt_inf"] = trt_a, trt_b
            eng = _CountryEngine(states=[a, b], fixtures={"year": 1900.0, "te_demog_female_work_share": 0.25},
                                 triggers={"is_ai": False, "te_demog_cohorts_run": True})
            eng.call("te_demog_country_census")
            return eng.vars
        w = P.INFECTION_ADULT_MEDICINE
        v = outline(0.9, 0.3)
        fa, fb = 1 - w * 0.6 * 0.9, 1 - w * 0.2 * 0.3
        self.assertAlmostEqual(v["te_dg_inf_ad"], (4 * 0.5 * fa + 1 * 1.0 * fb) / (4 * 0.5 + 1 * 1.0), places=4)
        self.assertAlmostEqual(v["te_dg_m_inf"] * v["te_dg_inf_ad"], (4 * 0.5 * fa + 1 * 1.0 * fb) / 5, places=4)
        plain = outline(0.0, 0.0)
        self.assertAlmostEqual(plain["te_dg_inf_ad"], 1.0, places=6)
        adults = [k for k in v if re.fullmatch(r"te_dg_pj[fm]\d+", k)]
        self.assertTrue(adults, "the outline ran")
        self.assertGreater(sum(v[k] for k in adults), sum(plain[k] for k in adults))
        a, b = self.states()
        del a["te_dg_acc"], b["te_dg_acc"]
        none = _CountryEngine(states=[a, b], fixtures={"year": 1900.0, "te_demog_female_work_share": 0.25},
                              triggers={"is_ai": True, "te_demog_cohorts_run": True})
        none.call("te_demog_country_census")
        self.assertEqual(none.vars["te_dg_inf_ad"], 1.0)


class TestSelfCheck(unittest.TestCase):
    """TE_SELF_CHECK cause_deaths_estimate (the interpreter has no globals or debug_log, so this reads the text)."""

    def test_once_a_game_on_a_degenerate_free_state(self):
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_cause_deaths_selfcheck")
        self.assertIn("NOT = { has_global_variable = te_demog_selfcheck_cause_done }", body)
        self.assertIn("set_global_variable = { name = te_demog_selfcheck_cause_done value = yes }", body)
        self.assertIn("local_var:te_dg_lx_on = 0", body)          # no one in longevity care
        self.assertIn("local_var:te_dg_dc_nat >= 1000", body)     # enough deaths to judge
        self.assertIn("var:te_dg_dc_fit >= 0.9", body)
        self.assertIn("var:te_dg_dc_fit <= 1.1", body)
        self.assertEqual(body.count("TE_SELF_CHECK OK cause_deaths_estimate"), 1)
        self.assertEqual(body.count("TE_SELF_CHECK BROKEN cause_deaths_estimate"), 1)
        # no comparison with an inline value block (it held for every state in game)
        self.assertNotRegex(body, r"[<>]=? \{")
        self.assertIn("te_debug_demog_cause_deaths_selfcheck = yes", _block(_text(EFFECTS), "te_demog_cause_deaths_store"))

    def test_the_playtest_list_names_it(self):
        doc = _text(ROOT / "docs" / "testing" / "demographics-playtest.md")
        self.assertTrue("cause_deaths_estimate" in doc, "the play-test list's Self-checks table names it")


if __name__ == "__main__":
    unittest.main()
