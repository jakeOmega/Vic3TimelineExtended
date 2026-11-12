"""The census's script tests in the engine's fixed point (issue #967).

The script tests run the registry interpreter (test_demographics_registry._Engine) in floats, and floats can't see the
engine's five-decimal cut: values are i64 x 1e-5, so a quotient keeps five decimals, not five significant digits
(docs/guides/scripting_best_practices.md, "Writing a Yearly Per-Age Model in Script"). #964's late births took
TFR / 100000 first, which the engine stores as 0.00001 or 0, and a share under 1 then cut each term to 0; the float
tests matched the model at 1e-8 the whole time. test_demographics_late.py has run the late step in fixed point since.

Each class here is a twin of a float suite (_FixedPointTwin): the same cases, every engine cutting as the game does,
every near-equality at 1e-3 of the value (1e-4 for a small one). Drift inside that is the cut of a case's own inputs;
a disagreement past it is an early divide in the script. The suites are imported as modules, so pytest collects only
the twins from this file.

What the twins found (2026-11-12; docs/systems/mod_systems/demographics.md, "Deaths in fixed point"):
- The sweep's survivors are people x (1 - q / 100000), and q / 100000 keeps five decimals, so a death rate counts only
  its whole deaths per 100,000 (te_demog_age_slot; the late sweep and the pool take the same form). The year's deaths
  come out short by under 1e-5 of the people, about half that on average: 1.45 of 5,892 in TestCohortScript's plain
  step (2.5e-4), where multiplying first (people x q / 100000) leaves 0.03 (6e-6). The shortfall is a share of the
  people, not of the deaths, so it weighs more where deaths are few: with the on-top scale at -0.99 it is 1.3 of the
  58 natural deaths left (2.2%), and that year's deaths are 2.0e-3 short, the one comparison here past 1e-3
  (test_on_top_scales_have_only_their_natural_floor, held to the bound instead). The script is as it was: the change
  would move every recorded census case (test_demographics_golden.py), so it is the owner's to make.
- The life table (te_demog_lt_sex) puts life expectancy at birth 0.017 of 43.3 years high in the seed's case (4e-4):
  a third from the same cut of q, the rest from its survival powers, each multiply cut again. The seed's chain of
  yearly survival (te_demog_seed_slot) leaves its cohorts up to 2.0e-4 off by the same means (women aged 67).
- W's lead multiplies its inputs' cut by up to 12 (TestWorkforceTermFixedPoint): 1.8e-4 on W, no early divide.
Every other comparison of these suites holds at 2e-4.
"""

import unittest
import unittest.mock

import test_demographics_family_census as family_census
import test_demographics_registry as registry
import test_demographics_spread as spread
import test_demographics_wave as wave
import test_demographics_work as work
from test_demographics_registry import _FixedPointTwin

# The sweep's survivors keep five decimals of 1 - q / 100000, so each cohort's deaths are short by under this share of
# its people (the docstring's first finding).
SURVIVOR_CUT = 1e-5


# -- the cohorts: the seed and the step, with flows, war dead and kills --------------------------------------------

class TestCohortScriptFixedPoint(_FixedPointTwin, registry.TestCohortScript):

    def test_on_top_scales_have_only_their_natural_floor(self):
        """The float case's scales of +9 and -0.99, where two of its comparisons don't survive the cut.

        The deaths: -0.99 leaves a hundredth of the natural deaths (58; the year's other 618 are maternal, of ten
        times the births), and the survivors' cut is a share of the people, under SURVIVOR_CUT of 251,000, so it can
        pass REL of the year's 677. The deaths are held to that bound, on the short side only.

        The rate read back: -0.99 is the edge of te_demog_k_on_top_factor_min (1 + dz = 0.01). The window's events are
        stored at five decimals, so events x 1000 / (rate x people) falls a hair under 0.01 and is kept as 0.00999:
        dz is -0.99001, 1 + dz is under the minimum, and the model's rate M aims at stays the last one (30), as in
        test_no_events_keep_the_models_own_rate. The float case reads it back from the step."""
        eng, ring, figures, pop = self.step_both(on_top=(9.0, -0.99), full=True)
        short = figures["deaths"] - eng.vars["te_dg_deaths"]
        self.assertGreaterEqual(short, 0.0)
        self.assertLess(short, SURVIVOR_CUT * pop)
        self.check_step(eng, ring, {**figures, "deaths": eng.vars["te_dg_deaths"]}, pop)
        self.assertEqual(eng.vars["te_dg_bz"], 8.99999)
        self.assertEqual(eng.vars["te_dg_dz"], -0.99001)
        self.close(eng.vars["te_dg_cbr_model"], figures["births_model"] * 1000 / pop, what="cbr_model")
        self.assertEqual(eng.vars["te_dg_cdr_model"], 30.0, "the last step's own rate stays")

    def test_the_survivors_cut_is_under_a_hundred_thousandth_of_the_people(self):
        """The finding's size, in the plain step and with war dead, kills and migrants: the script's deaths are
        short of the model's, by less than SURVIVOR_CUT of the people. A second early divide in the sweep would add
        to the shortfall or change its sign."""
        for flows in (dict(), dict(war_dead=900.0, kills=1500.0, migration=4000.0),
                      dict(war_dead=300.0, kills=200.0, migration=-6000.0)):
            with self.subTest(flows=flows):
                eng, _ring, figures, pop = self.step_both(**flows)
                short = figures["deaths"] - eng.vars["te_dg_deaths"]
                self.assertGreater(short, 0.0)
                self.assertLess(short, SURVIVOR_CUT * pop)


class TestStepWithMeasuresFixedPoint(_FixedPointTwin, family_census.TestStepWithMeasures):
    """The Family Policy measures in the step: maternal deaths per 100,000 births, the sex ratio at birth."""

    COHORT = TestCohortScriptFixedPoint


# -- the rates: the window's events, M and its clamps, the trapezoid's start rates ---------------------------------

class TestRatesScriptFixedPoint(_FixedPointTwin, registry.TestRatesScript):
    pass


class TestWindowEventsFixedPoint(_FixedPointTwin, registry.TestWindowEvents):
    pass


# -- the workforce term and the country census: weighted sums (the Gini bands: registry.TestGiniBands) -------------

class TestWorkforceTermFixedPoint(_FixedPointTwin, work.TestWorkforceTerm):

    def test_the_lead_matches_the_model(self):
        """W's lead is its gap x (0.5 / the pull share - 1), which is 12.4 at 38 births per 1,000, and the gap is
        four stored figures (the pops' base, the target, the lines on top, the game's figure), each cut by under 1e-5
        and the target by 2.5e-5, a product of two: up to 4.5e-5 on the gap and 6e-4 on W, where the float case's
        inputs carry sixteen digits. The largest of its sixty draws is 1.8e-4. Held to 1e-3."""
        with unittest.mock.patch.object(self, "FLOOR", 1e-3):
            super().test_the_lead_matches_the_model()


class TestWorkDeathSplitFixedPoint(_FixedPointTwin, work.TestWorkDeathSplit):
    pass


class TestBillsFixedPoint(_FixedPointTwin, work.TestBills):
    pass


class TestCountryFiguresFixedPoint(_FixedPointTwin, work.TestCountryFigures):
    pass


class TestCountryFixedPoint(_FixedPointTwin, registry.TestCountry):
    pass


# -- the practices, Family Limitation and the event wave's census lines --------------------------------------------

class TestPracticesScriptFixedPoint(_FixedPointTwin, registry.TestPracticesScript):
    pass


class TestPracticeSpreadScriptFixedPoint(_FixedPointTwin, spread.TestPracticeSpreadScript):
    pass


class TestFamilyLimitationScriptFixedPoint(_FixedPointTwin, spread.TestFamilyLimitationScript):
    pass


class TestCulturalHegemonyDriftFixedPoint(_FixedPointTwin, spread.TestCulturalHegemonyDrift):
    pass


class TestOldPastShareFixedPoint(_FixedPointTwin, wave.TestOldPastShare):
    pass


if __name__ == "__main__":
    unittest.main()
