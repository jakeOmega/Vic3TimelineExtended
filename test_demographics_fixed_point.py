"""The census's script tests in the engine's fixed point (issue #967).

The script tests run the registry interpreter (test_demographics_registry._Engine) in floats, and floats can't see the
engine's five-decimal cut: values are i64 x 1e-5, so a quotient keeps five decimals, not five significant digits
(docs/guides/scripting_best_practices.md, "Writing a Yearly Per-Age Model in Script"). #964's late births took
TFR / 100000 first, which the engine stores as 0.00001 or 0, and a share under 1 then cut each term to 0; the float
tests matched the model at 1e-8 the whole time. test_demographics_late.py has run the late step in fixed point since.

Each class here is a twin of a float suite (_FixedPointTwin): the same cases, every engine cutting as the game does,
every near-equality at five units of the last decimal (or 1e-5 of a figure past 5). A suite that needs more says why
where it is twinned. A disagreement past the tolerance is an early divide in the script, a fixture on a threshold's
edge, or the cut multiplied by the case's own arithmetic. The suites are imported as modules, so pytest collects only
the twins from this file.

What the twins found (2026-11-12; docs/systems/mod_systems/demographics.md, "Deaths in fixed point"), and what became
of it:
- The sweep's survivors were people x (1 - q / 100000), and q / 100000 keeps five decimals, so a death rate counted only
  its whole deaths per 100,000 and a year's deaths came out short by up to 1e-5 of the people: 1.45 of 5,892 in
  TestCohortScript's plain step (2.5e-4), 2.2% of the natural deaths where the on-top scale left 58. Fixed: the people
  x the rate first and divide = 100000 last (te_demog_age_slot, the pool, the late sweep, the seed's decrement). The
  plain step's deaths are now 0.03 short (6e-6) and its cohorts within 3e-6 of the model's.
- The seed's growth power was a chain, growth factor^age x the factor once an age, cut at each multiply: at 0.98556 it
  was 5.8e-4 low by age 67 and 1.17e-3 by 103. The survivors' cut ran the other way in the same chain, so the ring
  netted 2.0e-4 low at women aged 67 and 5.0e-4 at 103. Fixed: the power is kept at radix 100,000 (te_demog_seed_slot).
  The seed's ring is now within 4.5e-5 of the model's at every age with a person in it.
- The life table (te_demog_lt_sex) puts life expectancy at birth 0.017 of 43.3 years high in the seed's case (4e-4):
  a third from the cut of q, the rest from its survival powers, each multiply cut again, over a small q. Not changed:
  it keeps a survival probability by design, and the figure it moves is shown to one decimal.
- W's lead is its gap x (0.5 / the pull share - 1): 12 at 38 births per 1,000, 41 at 12, 83 at 6, 499 at 1 and 4,999
  with none, and one unit of the gap's last decimal moves W by that many (TestWorkforceTermFixedPoint). The pull share
  keeps two digits at 1 birth per 1,000 (0.00099 for 0.0009995), which makes that lead 1% larger. No early divide.
"""

import random
import unittest

import test_demographics_cause_deaths as cause_deaths
import test_demographics_family_census as family_census
import test_demographics_registry as registry
import test_demographics_spread as spread
import test_demographics_wave as wave
import test_demographics_work as work
from test_demographics_registry import _Engine, _FixedPointTwin

M, P = work.M, work.P   # demographics_model and demographics_params, on the path the suites set
UNIT = _FixedPointTwin.UNIT



class _CohortTwin(_FixedPointTwin):
    """The twin of a suite that seeds or steps the ring and compares its cohorts, births, deaths or life table.

    REL: a cohort leaves a step as its people x the ring's scale, less its dead, its killed and its migrants, and each
    of those is the cohort x a share kept to five decimals (the scale, the kills', the war's, its class's migrants'
    and the flat rate): five units of the cohort at most, over the part of it that stays, which at the oldest ages
    under the heaviest emigration here is a fifth. Children per woman is a product of five stored factors and the
    births carry it (3e-5). Since #967's fix the death rates themselves cost nothing: a step with no flows is within
    3e-6 at every age, and the seed within 4.5e-5.
    FLOOR is ten units: a cohort of under one person (0.03 at age 105) comes through a dozen cuts.
    LIFE_TABLE: the figures the life table gives, which is not rewritten (the module's docstring): life expectancy
    and the net reproduction rate both 4e-4 high. They keep #967's 1e-3, which is room for that and not a bound."""

    REL = 5 * UNIT / 0.2
    FLOOR = 10 * UNIT
    LIFE_TABLE = frozenset({"e0 women", "e0 men", "e0", "e65", "NRR"})
    LIFE_TABLE_REL = 1e-3

    def close(self, got, want, *args, **kw):
        what = kw.get("what", args[1] if len(args) > 1 else "")
        if what in self.LIFE_TABLE:
            self.assertLessEqual(abs(got - want), self.LIFE_TABLE_REL * abs(want), f"{what}: {got} vs {want}")
        else:
            super().close(got, want, *args, **kw)


# -- the cohorts: the seed and the step, with flows, war dead and kills --------------------------------------------

class TestCohortScriptFixedPoint(_CohortTwin, registry.TestCohortScript):

    def test_on_top_scales_have_only_their_natural_floor(self):
        """The float case's scales of +9 and -0.99, of which -0.99 is the edge of te_demog_k_on_top_factor_min
        (1 + dz = 0.01). The window's events are stored at five decimals, so events x 1000 / (rate x people) falls a
        hair under 0.01 and is kept as 0.00999: dz is -0.99001, 1 + dz is under the minimum, and the model's rate M
        aims at stays the last one (30), as in test_no_events_keep_the_models_own_rate. The float case reads it back
        from the step. The births' +9 comes out as 8.99999 by the same cut. The step itself is the float case's:
        its 677 deaths (58 of them natural, a hundredth of the year's) are 1.7e-4 short, the scale's own last
        decimal."""
        eng, ring, figures, pop = self.step_both(on_top=(9.0, -0.99), full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual(eng.vars["te_dg_bz"], 8.99999)
        self.assertEqual(eng.vars["te_dg_dz"], -0.99001)
        self.close(eng.vars["te_dg_cbr_model"], figures["births_model"] * 1000 / pop, what="cbr_model")
        self.assertEqual(eng.vars["te_dg_cdr_model"], 30.0, "the last step's own rate stays")

    def test_the_death_rates_keep_their_decimals(self):
        """#967's fix, held: the sweep takes the people x the rate first, so with nothing but births and deaths in
        the year every cohort of a person or more is within one unit per unit of the model's and the year's deaths
        within two (they were 2.5e-4 short while a rate counted only its whole deaths per 100,000). The seed's ring
        is within five at every age since its growth power kept its decimals (it was 5.0e-4 low at 103). What is left
        there is the cause multipliers' own fifth decimal, which a cohort's survival carries once for each unit of its
        cumulative hazard: 4.5e-5 at women aged 100, the last age with a person in it."""
        eng, ring, figures, _pop = self.step_both()
        self.assertLessEqual(abs(eng.vars["te_dg_deaths"] - figures["deaths"]), 2 * UNIT * figures["deaths"])
        for k in range(P.RING_YEARS):
            age = ring.age_of_slot(k)
            # not the newborns, who carry children per woman's cut, nor the two cohorts step_both plants at the ring's
            # end, most of whom die: the scale's cut is a share of those who began the year
            for sex, people in (("f", ring.f[k]), ("m", ring.m[k])):
                if people >= 1.0 and 0 < age < P.RING_YEARS - 2:
                    self.assertLessEqual(abs(eng.vars[f"te_dg_{sex}{k}"] - people), UNIT * people, f"{sex} aged {age}")
        eng, ring = self.seed_both()
        for age, women, men in ring.by_age()[:-1]:
            k = (self.YEAR - age) % P.RING_YEARS
            for sex, people in (("f", women), ("m", men)):
                if people >= 1.0:
                    self.assertLessEqual(abs(eng.vars[f"te_dg_{sex}{k}"] - people),
                                         max(5 * UNIT * people, self.FLOOR), f"the seed's {sex} aged {age}")


class TestStepWithMeasuresFixedPoint(_CohortTwin, family_census.TestStepWithMeasures):
    """The Family Policy measures in the step: maternal deaths per 100,000 births, the sex ratio at birth."""

    COHORT = TestCohortScriptFixedPoint


class TestCauseDeathsScriptFixedPoint(_CohortTwin, cause_deaths.TestScript):
    """The step's deaths by cause against the model's, from the same ring."""

    COHORT = TestCohortScriptFixedPoint


class TestCausesInTheStepFixedPoint(_FixedPointTwin, registry.TestCausesInTheStep):

    def life_expectancy_close(self, got, want):
        """The one figure here that comes off the life table (_CohortTwin.LIFE_TABLE): each age group's person-years
        are (1 - p^n) / q, n cuts over a small q. 41.771 for 41.755 here (3.8e-4). The multipliers and the stored
        inputs beside it stay at the mixin's tolerance."""
        self.assertLessEqual(abs(got - want), _CohortTwin.LIFE_TABLE_REL * want)


# -- fast mode: the census's terms at K times the rates ------------------------------------------------------------

class TestFastModeFixedPoint(_FixedPointTwin, registry.TestFastMode):
    """Every case here runs at K = 4, where the fast term is F = (K - 1) x the census's quotient T / B x (1 + what is
    on top). The quotient's cut therefore counts K - 1 times in F and once more in M, and the cases compare their
    sum, 1 + M + F + the rest, with the model's: K units, and up to four more from the two products' and the two
    stores' own cuts. 5.6 units at most here (1.82320 for 1.82326)."""

    K = 4
    FLOOR = (K + 4) * UNIT


# -- the workforce term ---------------------------------------------------------------------------------------------

class TestWorkforceTermFixedPoint(_FixedPointTwin, work.TestWorkforceTerm):

    FREE_DRAWS = 20   # for each birth rate, cases whose lead no cap holds

    @staticmethod
    def _stored(draw):
        """A case as the game holds it: every figure at five decimals, so the cut moves nothing on the way in."""
        return tuple(round(x, 5) for x in draw[:-1]) + (draw[-1],)

    def _free_draws(self):
        """Cases with the game's figure so near its aim that the lead stands inside its cap, at each birth rate: of
        the float case's sixty draws a cap holds all but one."""
        rng = random.Random(967)
        for cbr in self.LEAD_RATES:
            made = 0
            while made < self.FREE_DRAWS:
                wa, at = round(rng.uniform(0.4, 0.8), 5), round(rng.uniform(0.21, 0.77), 5)
                w, extra = rng.uniform(-0.2, 0.3), rng.uniform(-0.2, 0.1)
                wbase = rng.uniform(0.22, 0.3)
                gap = rng.uniform(-0.9, 0.9) * P.WF_LEAD_CAP / self._multiplier(cbr)
                engine = wbase + work._target(wa, at) + extra - gap
                if 0.05 <= engine <= 0.95:   # the script takes no lead from a figure of 0.01 or less
                    made += 1
                    yield wa, at, w, extra, wbase, engine, cbr

    @staticmethod
    def _multiplier(cbr, share_cut=0.0):
        return P.WF_LEAD_HALF / max(M.workforce_pull_share(cbr) - share_cut, P.WF_PULL_SHARE_MIN) - 1

    def _lead_cuts(self, wa, at, w, extra, wbase, engine, cbr):
        """(the pull share's cut, W's cut, whether a cap holds the lead on both sides) for a stored case.

        The pull share is (b^2 / 6 - b / 2 + 1) x b, b the births per head: b^2 is cut once, the sixth of it once
        more, and the product with b once, so under (1 + 1.2 b) units.
        The lead before its caps is the gap x (0.5 / share - 1). On stored inputs the gap's one cut is the target's
        product, working ages x share at work: under a unit, times the multiplier at the share's low end. The
        multiplier's own error is that low end less the true one, plus its quotient's cut, times the gap. The
        product is cut once more, and W adds the target's cut and its own store's.
        Each cap (0.2 either way, the ceiling on a lead up, the guard under W) moves W no further than the lead moved.
        Where the model's lead is past a cap by more than the lead's cut, the script's is past it too and W is the
        cap's own figure on both sides."""
        target = work._target(wa, at)
        gap = wbase + target + extra - engine
        share_cut = (1 + 1.2 * min(max(cbr / 1000.0, 0.0), P.WF_PULL_B_MAX)) * UNIT
        mult, mult_hi = self._multiplier(cbr), self._multiplier(cbr, share_cut)
        lead_cut = mult_hi * UNIT + abs(gap) * (mult_hi - mult + UNIT) + UNIT
        lead = M.workforce_lead(target, extra, wbase, engine, cbr)
        want = M.workforce_term(target, extra, lead)
        past_a_cap = abs(gap * mult - lead) + (want - (target + lead))
        return share_cut, lead_cut + 2 * UNIT, past_a_cap >= lead_cut

    def test_the_lead_matches_the_model(self):
        """The float case's sixty draws and FREE_DRAWS more at each birth rate, each as the game stores it.

        Where a cap holds the lead, W is at the mixin's tolerance. Where none does, W carries the gap's last decimal
        times 0.5 / the pull share - 1 (the docstring's fourth finding), so it is held to that draw's own bound
        (_lead_cuts): up to 2e-4 at 38 births per 1,000, 6e-4 at 12, 1.2e-3 at 6, 7e-3 at 1 and 0.05 with none,
        where the lead of a gap under 0.00004 is all the comparison has. The pull share is held to its own cut, a
        unit or so, at every draw. On the float case's unrounded inputs the gap takes four more cuts, which is how
        its one free draw came out 1.8e-4 off at 38."""
        free = dict.fromkeys(self.LEAD_RATES, 0)
        draws = [(self._stored(d), "the float case's") for d in self._lead_draws()]
        draws += [(self._stored(d), "free") for d in self._free_draws()]
        for draw, kind in draws:
            cbr = draw[-1]
            eng, want = self._lead_run(*draw)
            share_cut, w_cut, held = self._lead_cuts(*draw)
            self.assertLessEqual(abs(eng.value("te_demog_wf_pull_share") - M.workforce_pull_share(cbr)), share_cut,
                                 (kind, draw))
            if held:
                self.assertAlmostEqual(eng.vars["te_dg_mw"], want, places=4, msg=(kind, draw))
            else:
                free[cbr] += 1
                self.assertLessEqual(abs(eng.vars["te_dg_mw"] - want), w_cut, (kind, draw))
        for cbr, count in free.items():
            self.assertGreaterEqual(count, self.FREE_DRAWS // 2, f"too few free leads at {cbr} births per 1,000")


# -- every other suite that runs the interpreter, at the mixin's tolerance -----------------------------------------
# The window and the rates refresh (M, its clamps, the trapezoid's start rates, the split on top), the country census
# and its weighted sums (the Gini bands have their own truncated cases: registry.TestGiniBands), the walk's lines, the
# practices, Family Limitation, the wave. A suite of text checks alone has nothing to twin.

PLAIN = {
    registry: """TestAbsorbedScript TestCauseFactorsScript TestCausesDisplay TestConsequencesScript TestCountry TestFlows
        TestInheritanceBalance TestLinesScript TestMeansScript TestMedicalOutreach TestMedicineDriftScript
        TestNaturalFertilityScript TestOldAgeScript TestOnTopClampSide TestOnTopSplitScript TestPensionAge
        TestPopMultiplierScript TestPracticesScript TestRatesScript TestSlotBirthsScript TestStateGini TestTrend
        TestWealth TestWealthSizes TestWealthStateModifiers TestWindowEvents TestWorkWalk TestWorkforceLinesScript""",
    work: """TestBills TestCountryFigures TestPensionAi TestPensionSetting TestWorkDeathSplit TestWorkTermSelfChecks
        TestWorkforceRow""",
    family_census: """TestDesiredAndUrban TestFamilyLawsUnderFull TestMaternal TestMeansLiteracy TestNewbornSplit
        TestPolicyTerm TestTooltipsShowWhatTheStepUsed""",
    spread: "TestCulturalHegemonyDrift TestFamilyLimitationScript TestPracticeSpreadScript",
    wave: "TestOldPastShare",
}

for _module, _names in PLAIN.items():
    for _name in _names.split():
        globals()[f"{_name}FixedPoint"] = type(f"{_name}FixedPoint", (_FixedPointTwin, getattr(_module, _name)),
                                               {"__module__": __name__})


# -- the mixin itself -----------------------------------------------------------------------------------------------

class TestTheTwinMixin(unittest.TestCase):

    def _run(self, case):
        result = unittest.TestResult()
        case.run(result)
        self.assertEqual((result.failures, result.errors), ([], []))
        return case

    def test_an_engine_built_in_setup_or_setupclass_cuts_too(self):
        """A float suite that builds its engine before the test body (setUp, setUpClass) still gets a fixed-point
        twin, and the float suite beside it stays in floats."""
        class Float(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                cls.once = _Engine({})

            def setUp(self):
                self.before = _Engine({})

            def runTest(self):
                self.seen = (self.once.truncate, self.before.truncate, _Engine({}).truncate)

        class Twin(_FixedPointTwin, Float):
            pass

        for cls, want in ((Twin, (True, True, True)), (Float, (False, False, False))):
            case, result = cls(), unittest.TestResult()
            unittest.TestSuite([case]).run(result)      # a suite runs setUpClass, as a runner does
            self.assertEqual((result.failures, result.errors), ([], []))
            self.assertEqual(case.seen, want, cls.__name__)
        self.assertFalse(_Engine.FIXED_POINT, "the twin leaves the float suites in floats")

    def test_a_failing_twin_leaves_floats_behind_it(self):
        class Float(unittest.TestCase):
            def runTest(self):
                raise AssertionError("fails")

        class Twin(_FixedPointTwin, Float):
            pass

        result = unittest.TestResult()
        Twin().run(result)
        self.assertEqual(len(result.failures), 1)
        self.assertFalse(_Engine.FIXED_POINT)

    def test_the_tolerance_is_five_units_or_a_hundred_thousandth(self):
        class Float(unittest.TestCase):
            def runTest(self):
                self.assertAlmostEqual(0.30004, 0.3, places=9)        # four units
                self.assertAlmostEqual(7000.06, 7000.0, places=9)     # under 1e-5 of 7,000
                with self.assertRaises(AssertionError):
                    self.assertAlmostEqual(0.30006, 0.3, places=9)    # six units
                with self.assertRaises(AssertionError):
                    self.assertAlmostEqual(7000.08, 7000.0, places=9)
                self.assertAlmostEqual(0.5, 0.52, delta=0.05)         # the float case's own looser tolerance stands

        class Twin(_FixedPointTwin, Float):
            pass

        self._run(Twin())


if __name__ == "__main__":
    unittest.main()
