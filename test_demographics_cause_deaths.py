"""Deaths by cause (issue #1029): the census's split of last year's deaths, for the Causes of Death sections.

The estimate (method a): each natural cause's deaths at the step's rates over the last count's bands
(demographics_model.cause_deaths_estimate; the generated te_demog_cause_deaths_estimate), scaled to the census's own
deaths from those causes; childbirth's, the deaths added on top, the war dead and the people killed by events as counted
(demographics_model.cause_deaths; te_demog_cause_deaths_store). The country sums its states' and keeps the cause
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
SLICES = ("inf", "ext", "chr", "work", "mat", "ontop", "war", "kill")
CAUSE_SHORT = {"infection": "inf", "external": "ext", "chronic": "chr", "work": "work"}
MODEL_KEY = {"inf": "infection", "ext": "external", "chr": "chronic", "work": "work", "mat": "maternal",
             "ontop": "on_top", "war": "war", "kill": "kills"}


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
    def test_the_slices_add_up_to_the_deaths_with_the_war_dead_and_the_killed(self):
        raw = {"infection": 300.0, "external": 40.0, "chronic": 200.0, "work": 10.0}
        for dz in (0.0, 0.25, -0.3):
            with self.subTest(dz=dz):
                out = M.cause_deaths(raw, deaths=600.0, maternal=20.0, deaths_scale=dz, war_dead=50.0, kills=7.0)
                self.assertAlmostEqual(out["total"], 657.0)
                self.assertAlmostEqual(sum(out[MODEL_KEY[s]] for s in SLICES), out["total"])
                # the shares of the four follow the estimate's
                self.assertAlmostEqual(out["infection"] / out["chronic"], 1.5)
                self.assertEqual(out["on_top"] > 0, dz > 0)
                if dz > 0:
                    self.assertAlmostEqual(out["on_top"], 580.0 * dz / (1 + dz))
                self.assertAlmostEqual(out["fit"], 550.0 / 580.0)

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
        self.assertEqual(eng.vars["te_dg_dc_war"], war)
        self.assertEqual(eng.vars["te_dg_dc_kill"], kills)

    def test_a_step_without_flows(self):
        eng, _ring, figures, _pop = self.cohort.step_both()
        self.check(eng, figures)
        self.assertEqual(eng.vars["te_dg_dc_ontop"], 0.0)

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

    def test_deaths_added_on_top_are_their_own_slice(self):
        eng, _ring, figures, _pop = self.cohort.step_both(on_top=(0.05, 0.12), full=True)
        self.check(eng, figures)
        nat = eng.vars["te_dg_deaths"] - eng.vars["te_dg_dc_mat"]
        close(self, eng.vars["te_dg_dc_ontop"], nat * 0.12 / 1.12, rel=1e-4, what="on top")

    def test_deaths_taken_away_show_no_slice(self):
        """Below 0 the game took deaths away: the four causes share all the census's deaths but childbirth's."""
        eng, _ring, figures, _pop = self.cohort.step_both(on_top=(0.0, -0.2), full=True)
        self.check(eng, figures)
        self.assertEqual(eng.vars["te_dg_dc_ontop"], 0.0)
        four = sum(eng.vars[f"te_dg_dc_{s}"] for s in ("inf", "ext", "chr", "work"))
        close(self, four, eng.vars["te_dg_deaths"] - eng.vars["te_dg_dc_mat"], what="the four")

    def test_a_seed_has_none(self):
        eng = _engine_for(R.TestCohortScript.INP, 1836, 250000.0)
        eng.vars["te_dg_dc_fit"] = 0.97
        eng.call("te_demog_seed")
        for s in SLICES + ("total",):
            self.assertEqual(eng.vars[f"te_dg_dc_{s}"], 0.0, s)
        self.assertNotIn("te_dg_dc_fit", eng.vars)

    def test_the_estimate_reads_last_counts_bands_before_the_sweep(self):
        begin = _block(_text(EFFECTS), "te_demog_step_begin")
        self.assertGreater(begin.index("te_demog_cause_deaths_estimate = yes"), begin.index("te_demog_on_top_scales = yes"))
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
