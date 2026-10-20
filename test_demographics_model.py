"""The demographics cohort model (scripts/analysis/demographics_model.py).

Pins the model's behaviour to the design's anchors
(docs/superpowers/specs/2026-10-08-demographics-design.md §1, §2.2-§2.4, §3) so a
parameter change that breaks a real-world anchor fails here, before it is generated
into script.
"""

import dataclasses
import math
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402

CARRIERS = DM.load_carriers()


def scenario(**kw):
    """Inputs whose modifier totals come from the game files' carriers for its techs, laws and
    institutions (an incorporated state)."""
    inp = M.Inputs(**kw)
    inp.mods = DM.totals(CARRIERS, inp.techs, inp.laws, inp.institutions)
    return inp

MODERN = frozenset({
    "medical_degrees", "pharmaceuticals", "modern_nursing", "antibiotics", "modern_vaccines",
    "antibiotic_mass_production", "vulcanization", "feminism", "contraceptive_pill", "modern_pharmaceuticals",
    "combustion_engine",
})
EARLY_MEDICINE = frozenset({"medical_degrees", "pharmaceuticals", "modern_nursing", "antibiotics", "vulcanization",
                            "feminism"})

AGRARIAN_1836 = M.Inputs(sol=8, literacy=0.2, urban_share=0.1)
BRITAIN_1836 = scenario(sol=11, literacy=0.35, urban_share=0.3, laws=frozenset({"law_no_womens_rights"}))
FRANCE_1836 = M.Inputs(sol=11, literacy=0.3, urban_share=0.15, means_add=P.FAMILY_LIMITATION_MEANS)
# Ministry of Health levels near each era's top, which technology alone sets (5 by 1950, 6 at era 8).
WEST_1950 = scenario(sol=25, literacy=0.9, urban_share=0.6, techs=EARLY_MEDICINE,
                     laws=frozenset({"law_private_health_insurance", "law_women_in_the_workplace"}),
                     institutions={"institution_health_system": 5, "institution_workplace_safety": 2})
WEST_1990 = scenario(sol=38, literacy=0.98, urban_share=0.75, techs=MODERN,
                     laws=frozenset({"law_public_health_insurance", "law_womens_suffrage",
                                     "law_old_age_pension", "law_dedicated_police"}),
                     institutions={"institution_health_system": 6, "institution_workplace_safety": 4,
                                   "institution_ministry_of_consumer_protection": 3,
                                   # the police law's line is a level of the Ministry of Public Safety (2026-10-16), as
                                   # the harness's West 1990 holds it
                                   "institution_police": 4})
BRITAIN_1900 = scenario(sol=16, literacy=0.75, urban_share=0.6,
                        techs=frozenset({"medical_degrees", "pharmaceuticals", "modern_nursing", "vulcanization",
                                         "feminism"}),
                        laws=frozenset({"law_charitable_health_system"}), institutions={"institution_health_system": 4})
# §2.2's aged row is the West in 1990 itself since Task 7: Women's Suffrage's natural-fertility term takes it to about
# 1.4 children per woman (the case added State-Sponsored Family Planning only to reach 1.3 before that term).
AGED_TODAY = WEST_1990
INDIA_1975 = scenario(sol=9, literacy=0.35, urban_share=0.2,
                      techs=EARLY_MEDICINE | {"modern_vaccines", "contraceptive_pill"},
                      laws=frozenset({"law_charitable_health_system"}))


class TestFertility(unittest.TestCase):
    """§2.3's sketch table: the formula with plausible inputs."""

    def tfr(self, inp):
        _ring, last = M.run_constant(inp, years=200)
        return last["tfr"]

    def test_sketch_cases(self):
        # each with the Late Marriage share the drift gives it (demographics_harness._SCENARIO_PRACTICES) at the fitted
        # cuts (the late-marriage plan, Task 6, 2026-10-12: 0.10 and 0.20, no raise)
        for inp, practices, expected, label in [
            (BRITAIN_1836, {"lm": 1.0}, 4.85, "Britain 1836"),
            (FRANCE_1836, {"lm": 1.0}, 4.3, "France 1836 (Family Limitation)"),
            (BRITAIN_1900, {"lm": 0.75}, 3.45, "Britain 1900"),
            # 2.8 before the women's-rights term; with Women in the Workplace's -0.10 (Task 7) 2.5, nearer the West's
            # 1950 median of 2.31 (Gapminder: Austria 1.87 ... the Netherlands 3.10); 2.35 with Late Marriage at 0.5
            (WEST_1950, {"lm": 0.5}, 2.35, "the West 1950"),
            # 1.6 before Women's Suffrage's natural-fertility term (Task 7), 1.4 with it, 1.35 with Late Marriage
            (WEST_1990, {"lm": 0.45}, 1.35, "the West 1990"),
            (INDIA_1975, {"bs": 0.0}, 5.15, "India 1975"),   # India's held start is 0 since the fit
        ]:
            with self.subTest(label):
                self.assertAlmostEqual(self.tfr(dataclasses.replace(inp, practices=practices)), expected, delta=0.3)

    def test_wealth_term_endpoints(self):
        # 6.0 at SoL 8 and below (owner, 2026-10-10, phase 2 step 4's gate: the model's children per woman sat above
        # Gapminder's almost everywhere at 6.2, and the world multiple at x1.78)
        self.assertAlmostEqual(M.wealth_tfr(0), 6.0)
        self.assertAlmostEqual(M.wealth_tfr(8), 6.0)
        self.assertAlmostEqual(M.wealth_tfr(35), 3.5)
        self.assertAlmostEqual(M.wealth_tfr(60), 3.5)

    def test_asfr_shape_sums_to_one(self):
        self.assertAlmostEqual(sum(M.asfr_shape(r) for r in range(100)), 100000.0)


class TestMeans(unittest.TestCase):
    """The means to plan a family from the fertility types (modifier-types design, stage 2)."""

    def inp(self, literacy=0.5, mods=None, means_add=0.0):
        return M.Inputs(literacy=literacy, mods=dict(mods or {}), means_add=means_add)

    def access(self, literacy):
        return P.MEANS_ACCESS_BASE + (1 - P.MEANS_ACCESS_BASE) * literacy

    def test_no_carrier_is_the_traditional_means(self):
        # Review Focus 1: every 1836 country but France
        self.assertAlmostEqual(M.means(self.inp(0.35)), P.TRADITIONAL_MEANS * self.access(0.35))

    def test_techs_add_in_any_order(self):
        # Review Focus 2: the Pill without vulcanization is the base plus the Pill's own line
        pill_only = DM.totals(CARRIERS, techs={"contraceptive_pill"})
        both = DM.totals(CARRIERS, techs={"vulcanization", "contraceptive_pill"})
        pill = {c.key: c.value for c in CARRIERS if c.type == P.CONTRACEPTION_TYPE}["contraceptive_pill"]
        self.assertAlmostEqual(M.means(self.inp(1.0, pill_only)), P.TRADITIONAL_MEANS + pill)
        self.assertGreater(M.means(self.inp(1.0, both)), M.means(self.inp(1.0, pill_only)))

    def test_the_shift_is_not_scaled_by_literacy(self):
        low = M.means(self.inp(0.0, {P.MEANS_SHIFT_TYPE: 0.1}))
        self.assertAlmostEqual(low, P.TRADITIONAL_MEANS * self.access(0.0) + 0.1)

    def test_static_and_law_shifts_add(self):
        both = M.means(self.inp(0.3, {P.MEANS_SHIFT_TYPE: 0.1}, means_add=P.FAMILY_LIMITATION_MEANS))
        self.assertAlmostEqual(both, min(P.TRADITIONAL_MEANS * self.access(0.3) + 0.1 + P.FAMILY_LIMITATION_MEANS,
                                         P.MEANS_CAP))

    def test_the_tier_is_clamped_before_literacy(self):
        # Review Focus 4: a tier above 1 counts as 1
        self.assertAlmostEqual(M.means(self.inp(0.0, {P.CONTRACEPTION_TYPE: 5.0})), self.access(0.0))

    def test_a_negative_contraception_total_floors_the_tier(self):
        # the tier never goes below 0, as the script's nested block clamps it
        self.assertAlmostEqual(M.means(self.inp(0.0, {P.CONTRACEPTION_TYPE: -1.0, P.MEANS_SHIFT_TYPE: 0.5})), 0.5)

    def test_a_negative_shift_floors_at_zero(self):
        # Review Focus 3: a pronatalist measure never makes the fertility factor exceed 1
        self.assertEqual(M.means(self.inp(0.0, {P.MEANS_SHIFT_TYPE: -2.0})), 0.0)

    def test_cap(self):
        # the natural bound of a share (owner, 2026-10-20; was 0.95)
        self.assertEqual(P.MEANS_CAP, 1.0)
        self.assertEqual(M.means(self.inp(1.0, {P.CONTRACEPTION_TYPE: 1.0, P.MEANS_SHIFT_TYPE: 1.0})), 1.0)
        self.assertAlmostEqual(M.means(self.inp(1.0, {P.CONTRACEPTION_TYPE: 1.0, P.MEANS_SHIFT_TYPE: -0.03})), 0.97)


class TestMortality(unittest.TestCase):
    """§2.4's anchors: infant mortality, life expectancy at birth and at 65."""

    def table(self, inp):
        qf, qm, _ = M.group_rates(inp)
        f, m = M.life_table(qf), M.life_table(qm)
        return {k: (f[k] + m[k]) / 2 for k in f}

    def test_poverty_raises_infection_below_sol_9(self):
        # phase 2 calibration (2026-10-10): x1 at SoL 9 and above, rising to x1.75 at SoL 5 and below (the
        # strength refitted with the census's continuous crowding term counted)
        self.assertEqual(M.poverty_infection(9), 1.0)
        self.assertEqual(M.poverty_infection(15), 1.0)
        self.assertAlmostEqual(M.poverty_infection(7), 1.375)
        self.assertEqual(M.poverty_infection(5), 1.75)
        self.assertEqual(M.poverty_infection(1), 1.75)
        # SoL 8 and 4 share the high-SoL term (x1), so the cause multipliers differ by the poverty term alone
        ratio = (M.cause_multipliers(M.Inputs(sol=4))["infection"] / M.cause_multipliers(M.Inputs(sol=8))["infection"])
        self.assertAlmostEqual(ratio, M.poverty_infection(4) / M.poverty_infection(8))

    def test_crowding_raises_infection_by_its_migration_penalty(self):
        # owner, 2026-10-10: a function of how crowded the state is, not a switch. Infection rises by the same share
        # migration attraction falls (Inputs.crowding: 0.1 x migration_crowding's multiplier), with no ceiling since
        # 2026-10-20 (owner: the old +50% was a guess; Ile-de-France's pull 1.008 doubles its infection)
        def infection(**kw):
            return M.cause_multipliers(M.Inputs(sol=12, literacy=0.3, **kw))["infection"]
        plain = infection()
        self.assertAlmostEqual(infection(crowding=0.038) / plain, 1.038)
        self.assertAlmostEqual(infection(crowding=0.45) / plain, 1.45)
        self.assertAlmostEqual(infection(crowding=1.45) / plain, 2.45)
        self.assertFalse(hasattr(P, "CROWDING_INFECTION_MAX"))
        # the Ministry of Urban Planning works through crowding itself (+10% tolerance a level), not as a gate
        ministry = {"institution_ministry_of_urban_planning": 3}
        self.assertAlmostEqual(infection(crowding=0.1, institutions=ministry), infection(crowding=0.1))

    def test_1836_europe(self):
        t = self.table(BRITAIN_1836)
        self.assertTrue(150 <= t["q0_per_1000"] <= 250, t)
        self.assertTrue(35 <= t["e0"] <= 43, t)
        self.assertTrue(10 <= t["e65"] <= 14, t)

    def test_rich_country_today(self):
        # §2.4's anchor is an infant mortality under 5 per 1,000 today; WEST_1990 (medicine to
        # era 8, Public Health Insurance at level 6, era 8's top) gives about 6; Britain's 1990 was 7.9.
        # Calibrated in the modifier-types stage 1 (demographics_harness.py medicine).
        t = self.table(WEST_1990)
        self.assertLess(t["q0_per_1000"], 8)
        self.assertTrue(72 <= t["e0"] <= 80, t)
        self.assertTrue(17 <= t["e65"] <= 23, t)

    def test_india_1975(self):
        # India in 1975: infant mortality about 130, life expectancy about 50. Medicine reaches
        # only as far as a Charitable Health System at level 1 lets it.
        t = self.table(scenario(sol=9, literacy=0.35, urban_share=0.2, techs=EARLY_MEDICINE | {"modern_vaccines"},
                                laws=frozenset({"law_charitable_health_system"}),
                                institutions={"institution_health_system": 1}))
        self.assertTrue(100 <= t["q0_per_1000"] <= 160, t)
        self.assertTrue(44 <= t["e0"] <= 58, t)

    def test_medicine_without_a_health_system(self):
        # the fast run's case: every medical tech of the late twentieth century, no health law,
        # a poor country. Poor countries with imported medicine in 1980: infant mortality 100-120.
        t = self.table(scenario(sol=10, literacy=0.3, urban_share=0.15, techs=MODERN))
        self.assertTrue(70 <= t["q0_per_1000"] <= 130, t)

    def test_early_public_health_insurance_gap(self):
        # the modifier-types spec's stage-1 gate: a health law before modern medicine, at the same
        # standard of living and literacy, adds at most about 3 years (the old tables gave 8.3)
        early = frozenset({"medical_degrees", "pharmaceuticals", "modern_nursing"})
        with_law = self.table(scenario(sol=12, literacy=0.4, techs=early,
                                       laws=frozenset({"law_public_health_insurance"}),
                                       institutions={"institution_health_system": 3}))
        without = self.table(scenario(sol=12, literacy=0.4, techs=early))
        self.assertTrue(0.5 <= with_law["e0"] - without["e0"] <= 3.0, (with_law, without))

    def test_women_outlive_men_by_a_calibration_gap(self):
        # §3's anchor is about 2 years at e0 35 and 5-7 at e0 75; the starting parameters give
        # about 5 at both. Meeting the anchor is calibration's job (the plan's 'After this
        # plan'); this pins the starting gap so a parameter change that moves it is seen.
        for inp in (BRITAIN_1836, WEST_1990):
            qf, qm, _ = M.group_rates(inp)
            gap = M.life_table(qf)["e0"] - M.life_table(qm)["e0"]
            self.assertTrue(3.0 <= gap <= 6.0, gap)

    def test_no_deaths_lives_at_the_floor_rate_past_150(self):
        # the open last interval (2026-10-20): with no deaths the survivors at 150 live on at the floor rate, one per
        # 100,000 a year, (100000 - 0.5) / 1 more years; finite, and within the script's range
        t = M.life_table([0.0] * len(P.GROUPS))
        self.assertAlmostEqual(t["e0"], 150.0 + 99999.5)
        self.assertAlmostEqual(t["e65"], 85.0 + 99999.5)
        self.assertEqual(M.tail_years(0.0), M.tail_years(P.LT_TAIL_RATE_MIN))
        self.assertEqual(M.tail_years(-5.0), 99999.5)

    def test_the_tail_moves_no_table_before_the_late_game(self):
        # the survivors at 150 of a table before longevity care are a few in ten million: the tail adds under a
        # thousandth of a year to e0 and e65, so the life expectancy any pre-late state shows stays as it was
        for inp in (BRITAIN_1836, WEST_1990):
            for q in M.group_rates(inp)[:2]:
                l150 = M.survivors_at(q, 150)
                self.assertLess(l150, 1e-5)
                with_tail = M.life_table(q)
                with unittest.mock.patch.object(M, "tail_years", lambda rate: 0.0):
                    cut = M.life_table(q)
                self.assertLess(with_tail["e0"] - cut["e0"], 1e-3)
                self.assertLess(with_tail["e65"] - cut["e65"], 1e-3)
                self.assertAlmostEqual(with_tail["e0"] - cut["e0"], l150 * M.tail_years(q[-1]), places=12)

    def test_a_near_immortal_table_lives_for_centuries(self):
        # bodies held young: every group at 40 deaths per 100,000 a year (a rich state's 30-year-olds), the survivors at
        # 150 living on at it. e0 is the closed form, large and finite: 1/q in years, less the half-year
        t = M.life_table([40.0] * len(P.GROUPS))
        q = 40.0 / 100000.0
        self.assertAlmostEqual(t["e0"], (1 - q / 2) / q, delta=1e-9 * t["e0"])
        self.assertTrue(1000 < t["e0"] < 100000 / P.LT_TAIL_RATE_MIN + 150, t["e0"])
        self.assertAlmostEqual(t["e65"], t["e0"], delta=1e-9 * t["e0"])   # a constant rate has no memory

    def test_work_deaths_follow_the_workforce(self):
        before = M.group_rates(scenario(laws=frozenset({"law_no_womens_rights"})))[0]
        after = M.group_rates(scenario(laws=frozenset({"law_women_in_the_workplace"})))[0]
        g = P.group_of(30)
        self.assertGreater(after[g], before[g])


class TestMedicine(unittest.TestCase):
    """The modifier-types design's Decision 1: medicine is 1 - access x treatment; the other
    law, technology and institution terms are 1 + their types' sum, floored."""

    def test_no_carrier_is_exactly_the_base(self):
        # a fresh 1836 state with no medical tech, health law or institution: medicine is 1
        inp = M.Inputs(sol=11, literacy=0.35)
        m = M.cause_multipliers(inp)
        self.assertEqual(m["maternal"], 1.0)
        self.assertEqual(m["work"], 1.0)
        self.assertEqual(m["external"], 1.0)
        self.assertAlmostEqual(m["infection"], M.lerp_sol(11, 1.0, P.SOL_INFECTION_AT_HIGH)
                               * (1 - P.LITERACY_INFECTION_WEIGHT * 0.35))
        self.assertAlmostEqual(m["chronic"], M.lerp_sol(11, 1.0, P.SOL_CHRONIC_AT_HIGH))

    def test_treatment_reaches_only_as_far_as_access(self):
        mods = {P.TREATMENT_TYPE["infection"]: 0.8}
        self.assertAlmostEqual(M.medicine(M.Inputs(mods=mods), "infection"), 1 - P.BASE_ACCESS * 0.8)
        self.assertAlmostEqual(M.medicine(M.Inputs(mods={**mods, P.ACCESS_TYPE: 1.0}), "infection"), 1 - 0.8)

    def test_access_without_treatment_does_nothing(self):
        self.assertEqual(M.medicine(M.Inputs(mods={P.ACCESS_TYPE: 0.6}), "maternal"), 1.0)

    def test_caps_hold(self):
        mods = {P.ACCESS_TYPE: 5.0, P.TREATMENT_TYPE["chronic"]: 5.0}
        self.assertAlmostEqual(M.medicine(M.Inputs(mods=mods), "chronic"), 1 - P.TREATMENT_CAP["chronic"])

    def test_adults_infection_takes_medicine_twice(self):
        """#1045: infection at 15-64 x (1 - weight x access x treatment) more; infants, children and the old, and every
        other cause, keep their rates; with no treatment the factor is 1."""
        self.assertEqual(M.infection_adult(M.Inputs(sol=11, literacy=0.35)), 1.0)
        mods = {P.ACCESS_TYPE: 1.0, P.TREATMENT_TYPE["infection"]: 0.9}
        inp = M.Inputs(sol=40, literacy=0.99, mods=mods)
        adult = M.infection_adult(inp)
        self.assertAlmostEqual(adult, 1 - P.INFECTION_ADULT_MEDICINE * 0.9)
        m = M.cause_multipliers(inp)
        work_f, work_m = M.work_split(inp, m["work"])
        with_f, with_m = M.rates_from_multipliers(m, work_f, work_m, adult)
        plain_f, plain_m = M.rates_from_multipliers(m, work_f, work_m, 1.0)
        lo, hi = P.INFECTION_ADULT_AGES
        for g, (start, _n) in enumerate(P.GROUPS):
            for sx, got, plain in (("f", with_f, plain_f), ("m", with_m, plain_m)):
                cut = (1 - adult) * P.INFECTION[sx][g] * m["infection"] if lo <= start < hi else 0.0
                self.assertAlmostEqual(plain[g] - got[g], cut, places=9, msg=f"{sx} {start}")
        self.assertEqual(M.INFECTION_ADULT_GROUPS, frozenset(range(P.group_of(lo), P.group_of(hi))))
        self.assertEqual(M.INFECTION_ADULT_BANDS, frozenset(range(lo // 5, hi // 5)))

    def test_chronic_treatment_reaches_its_cap_by_era_12(self):
        """Owner, 2026-10-20: chronic treatment to 0.99, reached by technology alone in the last era, as infection's. Eras
        8-11's carriers make 0.70; Genetic Engineering's 0.05 and era 12's two 0.12s take it to the cap, and the
        augmentation laws' flat lines then only cap."""
        t = P.TREATMENT_TYPE["chronic"]
        early = {"modern_pharmaceuticals", "telemedicine", "personalized_medicine"}
        late = early | {"genetic_engineering", "molecular_assemblers", "biological_immortality"}
        self.assertEqual(P.TREATMENT_CAP["chronic"], 0.99)
        self.assertAlmostEqual(DM.totals(CARRIERS, early, (), {})[t], 0.70)
        self.assertAlmostEqual(DM.totals(CARRIERS, late, (), {})[t], P.TREATMENT_CAP["chronic"])
        with_law = DM.totals(CARRIERS, late, {"law_medical_augmentation_only"}, {})
        self.assertAlmostEqual(M.medicine_targets(M.Inputs(mods=with_law))["chronic"], P.TREATMENT_CAP["chronic"])
        # the health bill still counts its three technologies (owner: bills unchanged)
        self.assertEqual(P.HEALTH_TECHS, ("modern_pharmaceuticals", "telemedicine", "personalized_medicine"))

    def test_infection_treatment_reaches_its_cap_by_era_12(self):
        """#1045 (owner, 2026-10-18): the base game's carriers stop at 0.94 by era 7, the rich world of eras 9-10; era 11's
        and 12's lines take infection's treatment to the cap."""
        early = {"medical_degrees", "pharmaceuticals", "modern_nursing", "antibiotics", "modern_vaccines",
                 "antibiotic_mass_production"}
        late = early | {"personalized_medicine", "advanced_nanofabrication"}
        t = P.TREATMENT_TYPE["infection"]
        self.assertAlmostEqual(DM.totals(CARRIERS, early, (), {})[t], 0.94)
        self.assertAlmostEqual(DM.totals(CARRIERS, late, (), {})[t], P.TREATMENT_CAP["infection"])

    def test_plain_terms_are_floored(self):
        # 2026-10-20 (owner): no floor but the natural bound 0, below which a negative rate would add people
        self.assertEqual(P.MORTALITY_MULT_FLOOR, 0.0)
        inp = M.Inputs(mods={"state_work_mortality_mult": -0.9})
        self.assertAlmostEqual(M.plain_multiplier(inp, "work"), 0.1)
        inp = M.Inputs(mods={"state_work_mortality_mult": -1.5})
        self.assertEqual(M.plain_multiplier(inp, "work"), 0.0)
        self.assertEqual(M.cause_multipliers(inp)["work"], 0.0)

    def test_an_unincorporated_state_gets_the_base_access_only(self):
        laws, levels = {"law_public_health_insurance"}, {"institution_health_system": 5}
        techs = {"medical_degrees", "pharmaceuticals", "antibiotics"}
        home = M.Inputs(mods=DM.totals(CARRIERS, techs, laws, levels))
        colony = M.Inputs(mods=DM.totals(CARRIERS, techs, laws, levels, incorporated=False))
        self.assertLess(M.medicine(home, "infection"), M.medicine(colony, "infection"))
        treatment = colony.mods[P.TREATMENT_TYPE["infection"]]
        self.assertAlmostEqual(M.medicine(colony, "infection"), 1 - P.BASE_ACCESS * treatment)


class TestStructure(unittest.TestCase):
    """§2.2's equilibrium table and the demographic dividend."""

    def test_agrarian_reference(self):
        ring, last = M.run_constant(AGRARIAN_1836, years=300)
        s = M.structure(ring)
        self.assertTrue(0.33 <= s["young"] <= 0.43, s)
        self.assertTrue(0.03 <= s["old"] <= 0.07, s)
        self.assertTrue(0.008 <= last["growth"] <= 0.02, last["growth"])

    def test_aged(self):
        # §2.2's aged row (about 1.3 children per woman). The West in 1990 gives about 1.4 with Women's Suffrage's
        # natural-fertility term (phase 2 step 4, Task 7; State-Sponsored Family Planning, which the case added
        # to reach 1.3 before it, would now take it to 1.2). At 1.3-1.4 the stable rate is about
        # ln(0.68) / 30 = -1.3% a year; the sketch's -0.9 to -1.2% came from four bands.
        ring, last = M.run_constant(AGED_TODAY, years=300)
        s = M.structure(ring)
        self.assertTrue(0.09 <= s["young"] <= 0.14, s)
        self.assertTrue(0.28 <= s["old"] <= 0.38, s)
        self.assertTrue(-0.017 <= last["growth"] <= -0.008, last["growth"])

    def test_dividend_window(self):
        ring, _ = M.run_constant(AGRARIAN_1836, years=300)
        start = M.structure(ring)["working"]
        factor = M.fertility(AGRARIAN_1836, 40)["factor"]
        low = M.Inputs(sol=8, literacy=0.2, urban_share=0.1, wealth_tfr=2.2 / factor)
        year = ring.year
        peak = start
        for _ in range(30):
            year += 1
            M.step(ring, low, year)
            peak = max(peak, M.structure(ring)["working"])
        self.assertGreaterEqual(peak - start, 0.08)

    def test_sex_balance(self):
        ring, _ = M.run_constant(BRITAIN_1836, years=200)
        self.assertTrue(90 <= M.structure(ring)["men_per_100_women"] <= 102)


class TestRing(unittest.TestCase):
    """§1: birth cohorts age exactly; the ring wraps; scaling matches the engine."""

    def test_seed_is_steady(self):
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        before = M.structure(ring)
        for year in range(1837, 1857):
            M.step(ring, AGRARIAN_1836, year)
        after = M.structure(ring)
        self.assertLess(abs(after["young"] - before["young"]), 0.015)
        self.assertLess(abs(after["old"] - before["old"]), 0.01)
        self.assertLess(abs(after["men_per_100_women"] - before["men_per_100_women"]), 0.5)

    def test_a_birth_cohort_does_not_spread(self):
        """Extra men born in 1800 stay in one slot for 120 years, then fold into the pool."""
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        twin = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        marked = 1800 % P.RING_YEARS
        ring.m[marked] += 777.0
        for year in range(1837, 1921):
            M.step(ring, AGRARIAN_1836, year)
            M.step(twin, AGRARIAN_1836, year)
        diffs = [a - b for a, b in zip(ring.m, twin.m)]
        self.assertEqual(ring.age_of_slot(marked), 120)
        self.assertGreater(diffs[marked], 0.0)
        self.assertLess(sum(abs(d) for i, d in enumerate(diffs) if i != marked), 1e-6)
        for year in range(1921, 1951):
            M.step(ring, AGRARIAN_1836, year)
            M.step(twin, AGRARIAN_1836, year)
        self.assertEqual(ring.age_of_slot(marked), 0)
        self.assertGreater(ring.pool_m, twin.pool_m)

    def test_scaled_to_engine_population(self):
        ring = M.seed(BRITAIN_1836, 1836, 2_500_000)
        self.assertAlmostEqual(ring.people(), 2_500_000, delta=1)
        M.step(ring, BRITAIN_1836, 1837, engine_pop=2_510_000)
        self.assertAlmostEqual(ring.people(), 2_510_000, delta=1)

    def test_births_minus_deaths_balance(self):
        ring = M.seed(BRITAIN_1836, 1836, 1_000_000)
        before = ring.people()
        out = M.step(ring, BRITAIN_1836, 1837)
        self.assertAlmostEqual(ring.people(), before + out["births"] - out["deaths"], delta=0.01)

    def test_empty_state_steps_without_error(self):
        ring = M.seed(BRITAIN_1836, 1836, 0)
        self.assertEqual(ring.people(), 0)
        M.step(ring, BRITAIN_1836, 1837, engine_pop=0, war_dead=50, kills=10, migration=-200)
        self.assertEqual(ring.people(), 0)
        M.step(ring, BRITAIN_1836, 1838, engine_pop=1000, migration=1000)
        self.assertEqual(ring.people(), 0)   # no class to take arrivals; the script re-seeds instead
        reseeded = M.seed(BRITAIN_1836, 1838, 1000)
        self.assertAlmostEqual(reseeded.people(), 1000, delta=0.01)

    def test_war_dead_are_young_men(self):
        ring = M.seed(BRITAIN_1836, 1836, 1_000_000)
        twin = M.seed(BRITAIN_1836, 1836, 1_000_000)
        M.step(ring, BRITAIN_1836, 1837, war_dead=10_000)
        M.step(twin, BRITAIN_1836, 1837)
        lost_m = sum(t[2] - r[2] for r, t in zip(ring.by_age(), twin.by_age()))
        lost_f = sum(t[1] - r[1] for r, t in zip(ring.by_age(), twin.by_age()))
        self.assertAlmostEqual(lost_m, 9_500, delta=5)
        self.assertAlmostEqual(lost_f, 500, delta=5)
        outside_m = sum(t[2] - r[2] for r, t in zip(ring.by_age(), twin.by_age())
                        if r[0] < 19 or r[0] > 41)
        self.assertLess(abs(outside_m), 1.0)

    def _flow_pair(self, **flow):
        ring = M.seed(BRITAIN_1836, 1836, 1_000_000)
        twin = M.seed(BRITAIN_1836, 1836, 1_000_000)
        M.step(ring, BRITAIN_1836, 1837, **flow)
        M.step(twin, BRITAIN_1836, 1837)
        return ring, twin

    def test_kills_remove_exactly(self):
        ring, twin = self._flow_pair(kills=10_000)
        self.assertAlmostEqual(twin.people() - ring.people(), 10_000, delta=1)

    def test_departures_remove_exactly(self):
        ring, twin = self._flow_pair(migration=-20_000)
        self.assertAlmostEqual(twin.people() - ring.people(), 20_000, delta=1)

    def test_arrivals_add_exactly(self):
        ring, twin = self._flow_pair(migration=20_000)
        self.assertAlmostEqual(ring.people() - twin.people(), 20_000, delta=1)

    def test_migrants_go_where_people_are(self):
        inp = M.Inputs(sol=11, literacy=0.35, urban_share=0.3, crisis=1.0)
        ring = M.seed(BRITAIN_1836, 1836, 1_000_000)
        twin = M.seed(BRITAIN_1836, 1836, 1_000_000)
        M.step(ring, inp, 1837, migration=20_000)
        M.step(twin, inp, 1837)
        gained_old = sum((r[1] + r[2]) - (t[1] + t[2])
                         for r, t in zip(ring.by_age(), twin.by_age()) if r[0] >= 95)
        self.assertLess(gained_old / 20_000, 0.005)

    def test_labour_migrants_are_young_adults(self):
        ring = M.seed(BRITAIN_1836, 1836, 1_000_000)
        twin = M.seed(BRITAIN_1836, 1836, 1_000_000)
        M.step(ring, BRITAIN_1836, 1837, migration=20_000)
        M.step(twin, BRITAIN_1836, 1837)
        gained = {a: (r[1] + r[2]) - (t[1] + t[2]) for r, t in zip(ring.by_age(), twin.by_age()) for a in [r[0]]}
        prime = sum(v for a, v in gained.items() if 18 <= a <= 35)
        self.assertGreater(prime / 20_000, 0.5)


class TestRateTerm(unittest.TestCase):
    """demographics_model.rate_term: the census's births or deaths modifier for one state (phase 2 step 4)."""

    def test_no_other_term_gives_the_model(self):
        m, clamped = M.rate_term(target=80.0, bare=100.0)
        self.assertAlmostEqual(m, -0.2)
        self.assertFalse(clamped)
        self.assertAlmostEqual(100.0 * (1 + m), 80.0)

    def test_pop_level_terms_on_top_add_at_the_bare_curves_weight(self):
        """The engine adds every term (growth probe): with M on, a pop's events are bare x (1 + M + O).
        A pop's own term on top (severe starvation, a workplace line) isn't passed to rate_term: one state-wide M
        can't scale it without moving the other pops' rates, so the state's come to the model's plus bare x O."""
        m, _ = M.rate_term(target=80.0, bare=100.0)
        on_top = 0.3
        self.assertAlmostEqual(100.0 * (1 + m + on_top), 80.0 + 100.0 * on_top)

    def test_state_level_terms_on_top_act_on_the_census_rate(self):
        """Owner, 2026-10-11: a state-level line left on top (pollution, devastation, global warming, an event)
        acts on the census's rate, as its tooltip reads, not on the engine's bare curve. Every pop then gets
        bare x (target / bare) x (1 + O_s): exact per pop, since the line and M are both state-wide."""
        target, o_s = 60.0, 0.3
        m, clamped = M.rate_term(target=target, bare=100.0, on_top=o_s)
        self.assertFalse(clamped)
        for bare_p in (70.0, 30.0):
            self.assertAlmostEqual(bare_p * (1 + m + o_s), bare_p * target / 100.0 * (1 + o_s))
        self.assertAlmostEqual(100.0 * (1 + m + o_s), target * (1 + o_s))

    def test_state_level_terms_on_top_with_absorbed_terms(self):
        absorbed = -0.05 * 100.0
        m, _ = M.rate_term(target=60.0, bare=100.0, absorbed=absorbed, on_top=-0.2)
        self.assertAlmostEqual(100.0 * (1 + m - 0.2) + absorbed, 60.0 * 0.8)

    def test_the_census_applies_the_on_top_family_at_its_rate(self):
        """Owner, 2026-10-11 (the engine-lines plan): a moved on-top line (a family-policy law, a late tech) is
        script-only, so under Full the census applies it: every pop gets bare x (target / bare) x (1 + Q)."""
        m, _ = M.rate_term(target=60.0, bare=100.0, added=0.10)
        self.assertAlmostEqual(100.0 * (1 + m), 60.0 * 1.10)
        m, _ = M.rate_term(target=60.0, bare=100.0, on_top=0.3, added=0.10)
        self.assertAlmostEqual(100.0 * (1 + m + 0.3), 60.0 * (1 + 0.3 + 0.10))

    def test_west_bengal_pollution(self):
        """The fast-mode run's West Bengal, about 1888 (owner's tooltip): the census at about 59% of the bare
        curve and Pollution Impact +32%. Added to the bare curve, the line was +54% of the census's deaths."""
        m_old, _ = M.rate_term(target=59.0, bare=100.0)
        self.assertAlmostEqual(100.0 * (1 + m_old + 0.32) / 59.0 - 1, 0.32 / 0.59)
        m, _ = M.rate_term(target=59.0, bare=100.0, on_top=0.32)
        self.assertAlmostEqual(100.0 * (1 + m + 0.32) / 59.0 - 1, 0.32)

    def test_absorbed_terms_are_netted(self):
        # literacy's -0.1 x a bare-weighted literacy of 0.4: the absorbed sum is -0.1 x 40 over bare 100
        m, _ = M.rate_term(target=80.0, bare=100.0, absorbed=P.LITERACY_BIRTH_PENALTY * 40.0)
        self.assertAlmostEqual(100.0 * (1 + m) + P.LITERACY_BIRTH_PENALTY * 40.0, 80.0)

    def test_the_clamp_keeps_the_state_total_in_the_measured_range(self):
        m, clamped = M.rate_term(target=5.0, bare=100.0, other=0.1)
        self.assertAlmostEqual(m, P.RATE_TOTAL_MIN - 0.1)
        self.assertTrue(clamped)
        m, clamped = M.rate_term(target=600.0, bare=100.0)
        self.assertEqual(m, P.RATE_TERM_MAX)
        self.assertTrue(clamped)

    def test_the_clamp_never_pushes_past_the_terms_on_top(self):
        """A plague event or a decree already past -0.8 in the state read (starvation is per pop, outside it): M may
        not push further down."""
        m, clamped = M.rate_term(target=5.0, bare=100.0, other=-1.2)
        self.assertEqual(m, 0.0)
        self.assertTrue(clamped)

    def test_nobody_gets_no_term(self):
        self.assertEqual(M.rate_term(target=0.0, bare=0.0), (0.0, False))

    def test_the_bounds(self):
        self.assertEqual(P.RATE_TOTAL_MIN, -0.8)   # -0.9 measured, less literacy's -0.1
        self.assertEqual(P.RATE_TERM_MAX, 3.0)     # a guard: linearity holds far above (the 12x fast run)


class TestOnTopScales(unittest.TestCase):
    """The census's ring follows the engine: the step scales its rates by how far the engine ran from the target."""

    def test_scale_is_engine_over_target(self):
        self.assertAlmostEqual(M.on_top_scale(engine=105.0, target=100.0), 0.05)
        self.assertEqual(M.on_top_scale(engine=50.0, target=0.0), 0.0)
        self.assertEqual(M.on_top_scale(engine=1.0, target=100.0), P.ON_TOP_SCALE_MIN)
        self.assertEqual(M.on_top_scale(engine=1000.0, target=100.0), P.ON_TOP_SCALE_MAX)

    def test_scaled_step_gives_back_the_models_own_events(self):
        inp = M.Inputs(sol=9.0, literacy=0.2)
        plain, scaled = M.seed(inp, 1836, 1e6), M.seed(inp, 1836, 1e6)
        a = M.step(plain, inp, 1837)
        b = M.step(scaled, inp, 1837, births_scale=0.1, deaths_scale=0.2)
        self.assertAlmostEqual(b["births"], a["births"] * 1.1, places=6)
        self.assertAlmostEqual(b["births_model"], a["births"], places=6)
        self.assertAlmostEqual(b["deaths_model"], a["deaths"], delta=a["deaths"] * 1e-9)
        self.assertGreater(b["deaths"], a["deaths"] * 1.19)

    def test_no_scale_is_the_old_step(self):
        inp = M.Inputs(sol=9.0, literacy=0.2)
        ring = M.seed(inp, 1836, 1e6)
        out = M.step(ring, inp, 1837)
        self.assertEqual(out["births_model"], out["births"])
        self.assertEqual(out["deaths_model"], out["deaths"])

    def test_life_table_and_tfr_stay_the_models(self):
        inp = M.Inputs(sol=9.0, literacy=0.2)
        a = M.step(M.seed(inp, 1836, 1e6), inp, 1837)
        b = M.step(M.seed(inp, 1836, 1e6), inp, 1837, births_scale=0.3, deaths_scale=0.5)
        self.assertEqual((a["e0"], a["tfr"]), (b["e0"], b["tfr"]))
        self.assertAlmostEqual(b["tfr_shown"], a["tfr"] * 1.3)
        # infant mortality is the life table's too, as the script's te_dg_imr (set before the scales)
        self.assertEqual(a["q0_per_1000"], b["q0_per_1000"])

    # -- the trapezoid (owner, 2026-10-11; #894): a window's events average the engine's rate at its two ends --------

    def test_the_weight_is_the_trapezoids(self):
        self.assertEqual(P.WINDOW_START_WEIGHT, 0.5)

    def test_a_window_takes_the_mean_of_its_two_ends(self):
        """Germany 1897-98: the engine's deaths ran at 100 a month when the window began and at 160 on the step's day
        (a famine's onset). The window books 130, where the snapshot booked 160."""
        self.assertAlmostEqual(M.window_events(end_rate=160.0, start_rate=100.0), 130.0)
        self.assertAlmostEqual(M.window_events(end_rate=100.0, start_rate=160.0), 130.0)

    def test_no_start_rate_is_the_snapshot(self):
        """The first step after a seed, a new state, an old save: no rate stored at the window's start."""
        self.assertEqual(M.window_events(end_rate=160.0, start_rate=None), 160.0)

    def test_the_window_never_expects_fewer_than_no_events(self):
        self.assertEqual(M.window_events(end_rate=0.0, start_rate=-5.0), 0.0)

    def test_crude_rates_of_the_stable_population(self):
        cbr, cdr = M.model_crude_rates(M.Inputs(sol=9.0, literacy=0.2))
        self.assertTrue(20 < cbr < 60 and 15 < cdr < 50, (cbr, cdr))

    def test_starvation_terms_follow_the_engine(self):
        self.assertEqual(M.starvation_terms(0.5), (0.0, 0.0))
        b, d = M.starvation_terms(0.3)   # (0.4 - 0.3) x 2.5 = 0.25 of the mild penalty
        self.assertAlmostEqual(b, -0.7 * 0.25)
        self.assertAlmostEqual(d, 0.6 * 0.25)

    def test_severe_starvation_scales_by_the_starvation_value(self):
        """The famine probe (2026-10-11): the engine applies severe_starvation_penalty x the pop's starvation value,
        clamp((0.4 - food security) x 2.5, 0, 1), as it does starvation_penalty; not in full. 0.5 at the severe
        threshold, 1 at food security 0 and below."""
        for food, sv in ((0.19, 0.525), (0.15, 0.625), (0.1, 0.75), (0.02, 0.95), (0.0, 1.0), (-0.5, 1.0)):
            with self.subTest(food=food):
                b, d = M.starvation_terms(food)
                self.assertAlmostEqual(b, -0.9 * sv)
                self.assertAlmostEqual(d, 1.0 * sv)
                self.assertAlmostEqual(M.starvation_value(food), sv)
        # the mild penalty's own coefficient up to the threshold, severe's from just below it
        self.assertAlmostEqual(M.starvation_terms(0.2)[1], 0.6 * 0.5)
        self.assertAlmostEqual(M.starvation_terms(0.19999)[1], 1.0 * 0.500025)

    def test_the_starvation_value_is_clamped(self):
        self.assertEqual(M.starvation_value(0.4), 0.0)
        self.assertEqual(M.starvation_value(0.9), 0.0)
        self.assertEqual(M.starvation_value(-0.1), P.STARVATION_VALUE_MAX)
        self.assertEqual(P.STARVATION_VALUE_MAX, 1.0)


class TestNaturalFertility(unittest.TestCase):
    """The women's-rights term (phase 2 step 4, Task 7): natural fertility before the means."""

    def test_it_scales_children_per_woman_before_the_means(self):
        base = M.Inputs(sol=9.0, literacy=0.3)
        lower = M.Inputs(sol=9.0, literacy=0.3, mods={P.NATURAL_FERTILITY_TYPE: -0.1})
        a, b = M.fertility(base, 35.0), M.fertility(lower, 35.0)
        self.assertAlmostEqual(b["tfr"], a["tfr"] * 0.9)
        self.assertAlmostEqual(b["natural"], 0.9)
        self.assertEqual((a["means"], a["factor"]), (b["means"], b["factor"]))

    def test_it_is_floored(self):
        inp = M.Inputs(sol=9.0, mods={P.NATURAL_FERTILITY_TYPE: -5.0})
        self.assertEqual(M.fertility(inp, 35.0)["natural"], P.NATURAL_FERTILITY_FLOOR)

    def test_no_womens_rights_is_the_reference(self):
        """Re-centred on No Women's Rights, where 83% of the 1837 world sat, so step 2's fit is unchanged."""
        self.assertEqual(P.NATURAL_FERTILITY_BY_LAW.get("law_no_womens_rights", 0.0), 0.0)


class TestGrowthFactor(unittest.TestCase):
    """d = NRR^(-1/29): the generated script's table spans NRR 0.2 to 4.0 and clamps there."""

    def test_zero_nrr_is_clamped_to_the_table(self):
        self.assertEqual(M.growth_factor(0), M.growth_factor(0.2))
        self.assertEqual(M.growth_factor(-1), M.growth_factor(0.2))

    def test_large_nrr_is_clamped_to_the_table(self):
        self.assertEqual(M.growth_factor(10), M.growth_factor(4.0))

    def test_inside_the_table_it_is_the_power(self):
        self.assertAlmostEqual(M.growth_factor(1.0), 1.0)
        self.assertAlmostEqual(M.growth_factor(2.0), 2.0 ** (-1 / 29))


class TestMigrantProfile(unittest.TestCase):
    def test_each_kinds_weights_sum_to_one(self):
        # migrant_profile combines the three kinds' weights without normalising them.
        for kind, spec in P.MIGRANT_PROFILE.items():
            with self.subTest(kind):
                self.assertEqual(len(spec["weights"]), len(P.MIGRANT_CLASSES))
                self.assertAlmostEqual(sum(spec["weights"]), 1.0)

    def test_women_at_work_is_the_base_plus_the_laws_line(self):
        """Modifier-types stage 3 (2026-10-19): the share was a law table; each women's-rights law now carries the old
        table's figure less the 0.1 base, so every law reads what it did."""
        old_table = {"law_no_womens_rights": 0.1, "law_women_in_the_fields": 0.25, "law_women_own_property": 0.3,
                     "law_women_in_the_workplace": 0.45, "law_womens_suffrage": 0.47, "law_protected_class": 0.48}
        for law, share in old_table.items():
            self.assertAlmostEqual(M.female_work_share(scenario(laws=frozenset({law}))), share, msg=law)
        self.assertEqual(M.female_work_share(M.Inputs()), P.FEMALE_WORK_SHARE_DEFAULT, "no law: the base")
        self.assertEqual(M.female_work_share(M.Inputs(mods={P.FEMALE_WORK_SHARE_TYPE: 2.0})), 1.0, "at most 1")
        self.assertEqual(M.female_work_share(M.Inputs(mods={P.FEMALE_WORK_SHARE_TYPE: -0.5})), 0.0, "at least 0")

    def _family(self, inp):
        """The family kind's weight, read back from the profile's under-15s (only families and refugees bring them)."""
        prof = M.migrant_profile(inp)
        return (prof[(0, "f")] + prof[(0, "m")]) / P.MIGRANT_PROFILE["family"]["weights"][0]

    def test_cheaper_transport_brings_families(self):
        """The transport technologies' line adds to FAMILY_BASE: Paddle Steamer, Railways and the Combustion Engine as
        before, and the aviation techs §2.5 names (owner, 2026-10-19)."""
        base = dict(laws=frozenset({"law_no_womens_rights"}))
        steam = frozenset({"paddle_steamer", "railways", "combustion_engine"})
        air = steam | {"commercial_aviation", "jet_engine_technology"}
        rights = P.FAMILY_RIGHTS_WEIGHT * P.FEMALE_WORK_SHARE_DEFAULT / P.FULL_FEMALE_WORK_SHARE
        self.assertAlmostEqual(self._family(scenario(**base)), P.FAMILY_BASE + rights)
        self.assertAlmostEqual(self._family(scenario(techs=steam, **base)), P.FAMILY_BASE + 0.35 + rights)
        self.assertAlmostEqual(self._family(scenario(techs=air, **base)), P.FAMILY_BASE + 0.45 + rights)


class TestMigrantBooking(unittest.TestCase):
    """The residual's booking keeps the structure plausible (2026-10-12; docs/testing/demographics-migrant-booking-
    2026-10-12.md): a cap on each class and sex with the rest booked flat, and the labour kind's self-correcting split."""

    def setUp(self):
        self.ring = M.seed(BRITAIN_1836, 1836, 1_000_000)
        self.prof = M.migrant_profile(BRITAIN_1836)

    def test_below_the_cap_the_profile_books_as_before(self):
        migration = -0.001 * self.ring.people()
        rates = M.migrant_rates(self.ring, self.prof, migration)
        for (c, sex), rate in rates.items():
            people = (self.ring.class_f if sex == "f" else self.ring.class_m)[c]
            self.assertAlmostEqual(rate, migration * self.prof[(c, sex)] / people, places=12)

    def test_past_the_cap_each_class_stops_and_the_rest_is_flat(self):
        for migration, cap in ((-0.1, P.MIGRANT_CAP_OUT), (0.2, P.MIGRANT_CAP_IN)):
            amount = migration * self.ring.people()
            rates = M.migrant_rates(self.ring, self.prof, amount)
            sums = {(c, s): (self.ring.class_f if s == "f" else self.ring.class_m)[c] for c, s in rates}
            booked = sum(rates[k] * sums[k] for k in rates)
            self.assertAlmostEqual(booked, amount, delta=1e-6 * abs(amount), msg="every migrant is booked")
            want = {k: abs(amount) * self.prof[k] for k in rates}
            flat = sum(w - min(w, cap * sums[k]) for k, w in want.items()) / sum(sums.values())
            self.assertGreater(flat, 0)
            for k, rate in rates.items():
                self.assertAlmostEqual(abs(rate), min(want[k] / sums[k], cap) + flat, places=12, msg=k)
                self.assertEqual(rate > 0, amount > 0, k)
            self.assertAlmostEqual(abs(rates[(2, "m")]), cap + flat, msg="young men stop at the cap")

    def test_an_empty_class_books_its_share_flat(self):
        self.ring.class_m[4] = 0.5
        rates = M.migrant_rates(self.ring, self.prof, 1000.0)
        self.assertEqual(rates[(4, "m")], 0.0)
        others = sum(rates[k] * (self.ring.class_f if k[1] == "f" else self.ring.class_m)[k[0]]
                     for k in rates if k != (4, "m"))
        self.assertAlmostEqual(others, 1000.0, places=6)

    def test_labour_split_balances_where_men_are_few_or_many(self):
        low_start, low_full = P.LABOUR_BALANCE_LOW
        high_start, high_full = P.LABOUR_BALANCE_HIGH
        self.assertEqual(M.labour_balance_weight(low_start, -1), 0.0)
        self.assertEqual(M.labour_balance_weight(low_full, -1), 1.0)
        self.assertEqual(M.labour_balance_weight(80.0, -1), 1.0)
        self.assertEqual(M.labour_balance_weight(80.0, 1), 0.0, "arrivals where men are few keep the jobs' split")
        self.assertAlmostEqual(M.labour_balance_weight((high_start + high_full) / 2, 1), 0.5)
        self.assertEqual(M.labour_balance_weight(130.0, -1), 0.0)
        self.assertEqual(M.labour_balance_weight(None, -1), 0.0)
        self.assertEqual(M.labour_balance_weight(80.0, 0), 0.0)
        few = M.migrant_profile(BRITAIN_1836, 80.0, -1)
        women = sum(v for (c, s), v in few.items() if s == "f" and c == 2)
        men = sum(v for (c, s), v in few.items() if s == "m" and c == 2)
        self.assertAlmostEqual(women, men, msg="young departures half women where men are few")

    def test_sustained_emigration_leaves_a_plausible_structure(self):
        """The bug this fixes: 4% of the people leaving every year for 40 years took the young men to nothing (2 men per
        100 women, Hill Punjab in the 2026-10-12 overnight run); booked now, the state stays near its balance."""
        inp = M.Inputs(sol=8, literacy=0.1, urban_share=0.05, female_job_share=0.02)
        ring = M.seed(inp, 1836, 1_000_000)
        for year in range(1837, 1877):
            M.step(ring, inp, year, engine_pop=ring.people() * 0.985, migration=-0.04 * ring.people())
        figures = M.consequence_figures(ring)
        self.assertGreater(figures["sex_balance"], P.SEX_FEWER_FROM)
        self.assertGreater(figures["term"], -0.25)

    def test_sustained_immigration_stays_under_the_more_men_threshold(self):
        inp = M.Inputs(sol=10, literacy=0.2, urban_share=0.1, female_job_share=0.02)
        ring = M.seed(inp, 1836, 100_000)
        for year in range(1837, 1877):
            M.step(ring, inp, year, engine_pop=ring.people() * 1.09, migration=0.07 * ring.people())
        figures = M.consequence_figures(ring)
        self.assertLess(figures["sex_balance"], P.SEX_MORE_FROM)
        self.assertLess(figures["term"], 0.25)   # the old ceiling, now only a band: migration alone does not push T there


class TestInequality(unittest.TestCase):
    """§4.1: the grouped Gini over wealth bands, and the panel's figure."""

    def test_equal_groups(self):
        self.assertAlmostEqual(M.grouped_gini([(10, 100), (10, 100)]), 0.0)

    def test_one_group_owns_everything(self):
        self.assertGreater(M.grouped_gini([(99, 0.0001), (1, 1000)]), 0.98)

    def test_the_panel_scales_down_the_equality_it_sees(self):
        # owner, 2026-10-10: shown = 1 - X (1 - computed), X fitted to historians' 1836 estimates
        self.assertEqual(P.GINI_SHOWN_EQUALITY, 0.7)
        self.assertAlmostEqual(M.shown_gini(0.0), 0.3)
        self.assertAlmostEqual(M.shown_gini(0.35), 0.545)
        self.assertAlmostEqual(M.shown_gini(1.0), 1.0)
        self.assertAlmostEqual(M.shown_gini(0.95), 0.965, msg="no 0.9 cap")

    def test_wealth_bands_follow_the_income_knots(self):
        # Review Focus 2: each wealth lands in one band; the knots are each band's top. Five levels
        # wide all the way up (2026-10-10, high wealth): the last band, 196 or more, ends at the top level
        cases = {0: 1, 1: 1, 2: 2, 5: 2, 6: 3, 10: 3, 11: 4, 55: 12, 56: 13, 60: 13, 61: 14, 65: 14,
                 66: 15, 99: 21, 100: 21, 101: 22, 195: 40, 196: 41, 200: 41}
        for wealth, band in cases.items():
            self.assertEqual(M.wealth_band(wealth), band, wealth)
        self.assertEqual(P.GINI_BANDS, len(P.GINI_BAND_KNOTS) + 1)
        self.assertEqual(P.GINI_BANDS, 41)
        self.assertEqual(P.GINI_TOP_WEALTH, 200, "the mod's NUM_WEALTH_LEVELS")
        self.assertEqual(P.GINI_INCOME_KNOTS, (*P.GINI_BAND_KNOTS, P.GINI_TOP_WEALTH))

    def test_the_income_stand_in_is_linear_between_knots_and_uncapped(self):
        costs = {w: 100.0 * w * w for w in range(1, P.GINI_TOP_WEALTH + 1)}   # convex, like the packages
        for knot in P.GINI_INCOME_KNOTS:
            self.assertAlmostEqual(M.stand_in_income(knot, costs), costs[knot] / 100, msg=knot)
        self.assertEqual(M.stand_in_income(0, costs), costs[1] / 100, "flat below wealth 1")
        self.assertAlmostEqual(M.stand_in_income(63, costs), (3 * costs[65] + 2 * costs[60]) / 500)
        self.assertGreater(M.stand_in_income(61, costs), M.stand_in_income(60, costs), "no cap at 60")
        self.assertEqual(M.stand_in_income(250, costs), costs[200] / 100, "the top level bounds it")


class TestCausesOfDeath(unittest.TestCase):
    """The Causes of Death plan (2026-10-11): each cause's multiplier is the product of P.CAUSE_FACTORS' factors;
    health-care access and the treatments drift toward their targets at each census step; turmoil raises
    accidents and violence."""

    MODS = {P.ACCESS_TYPE: 0.3, P.TREATMENT_TYPE["infection"]: 0.4, P.TREATMENT_TYPE["maternal"]: 0.35,
            P.TREATMENT_TYPE["chronic"]: 0.1, "state_external_mortality_mult": -0.1,
            "state_work_mortality_mult": 0.1, "state_chronic_mortality_mult": -0.05}

    def test_factors_multiply_to_each_multiplier(self):
        for sol, lit, turm, crowd in ((3, 0.1, 0.0, 0.0), (6.5, 0.2, 0.4, 0.05), (20, 0.5, 1.0, 0.6), (40, 1.0, 0.2, 0.0)):
            inp = M.Inputs(sol=sol, literacy=lit, turmoil=turm, crowding=crowd, mods=dict(self.MODS))
            factors, mult = M.cause_factors(inp), M.cause_multipliers(inp)
            self.assertEqual(list(factors), list(P.CAUSE_FACTORS))
            for cause, fs in factors.items():
                self.assertEqual(tuple(fs), P.CAUSE_FACTORS[cause])
                self.assertAlmostEqual(math.prod(fs.values()), mult[cause], places=12, msg=cause)

    def test_turmoil_raises_accidents_and_violence_only(self):
        calm = M.cause_multipliers(M.Inputs(sol=12, literacy=0.3))
        unrest = M.cause_multipliers(M.Inputs(sol=12, literacy=0.3, turmoil=1.0))
        self.assertAlmostEqual(unrest["external"], calm["external"] * (1 + P.TURMOIL_EXTERNAL_WEIGHT))
        for cause in ("infection", "work", "maternal", "chronic"):
            self.assertEqual(unrest[cause], calm[cause], cause)
        # read as a 0-1 share
        self.assertEqual(M.cause_multipliers(M.Inputs(sol=12, literacy=0.3, turmoil=1.7))["external"],
                         unrest["external"])

    def test_a_seed_starts_medicine_at_its_targets(self):
        inp = M.Inputs(sol=12, literacy=0.3, mods=dict(self.MODS))
        ring = M.seed(inp, 1836, 1e6)
        self.assertEqual(ring.medicine, M.medicine_targets(inp))
        self.assertEqual(M.medicine_drift(None, inp), M.medicine_targets(inp))

    def test_a_seed_ignores_drifted_medicine(self):
        # the script's seed sets medicine at its targets before its rates (te_demog_medicine_at_target, then
        # te_demog_prepare), so a seed given drifted values (a harness reading a save's te_dg_acc) seeds as the script
        # does (review of Tasks 4-5, minor 4)
        inp = M.Inputs(sol=12, literacy=0.3, mods=dict(self.MODS))
        held = dataclasses.replace(inp, medicine={"access": 0.41, "infection": 0.01, "maternal": 0.0, "chronic": 0.0})
        a, b = M.seed(inp, 1836, 1e6), M.seed(held, 1836, 1e6)
        self.assertEqual(b.medicine, M.medicine_targets(inp))
        self.assertEqual((b.f, b.m, b.scale), (a.f, a.m, a.scale))

    def test_medicine_moves_a_share_of_the_gap_each_step(self):
        inp0 = M.Inputs(sol=12, literacy=0.3)
        ring = M.seed(inp0, 1836, 1e6)
        inp1 = M.Inputs(sol=12, literacy=0.3, mods=dict(self.MODS))
        M.step(ring, inp1, 1837)
        r = P.DIFFUSION_BASE
        self.assertAlmostEqual(ring.medicine["access"], P.BASE_ACCESS + r * 0.3)
        self.assertAlmostEqual(ring.medicine["infection"], r * 0.4)
        self.assertAlmostEqual(ring.medicine["maternal"], r * 0.35)
        # the step's rates use the drifted values, not the targets
        drifted = M.cause_multipliers(dataclasses.replace(inp1, medicine=ring.medicine))
        at_target = M.cause_multipliers(inp1)
        self.assertGreater(drifted["infection"], at_target["infection"])

    def test_diffusion_rises_with_its_type_and_is_capped(self):
        self.assertAlmostEqual(M.diffusion(M.Inputs()), P.DIFFUSION_BASE)
        self.assertAlmostEqual(M.diffusion(M.Inputs(mods={P.DIFFUSION_TYPE: 0.3})), P.DIFFUSION_BASE + 0.3)
        self.assertEqual(M.diffusion(M.Inputs(mods={P.DIFFUSION_TYPE: 5.0})), P.DIFFUSION_MAX)

    def test_a_value_near_its_target_takes_it(self):
        inp = M.Inputs(mods={P.ACCESS_TYPE: 0.3})
        target = M.medicine_targets(inp)
        prev = dict(target, access=target["access"] - 0.004 / (1 - P.DIFFUSION_BASE))
        self.assertEqual(M.medicine_drift(prev, inp)["access"], target["access"])
        far = dict(target, access=target["access"] - 0.2)
        self.assertLess(M.medicine_drift(far, inp)["access"], target["access"])

    def test_constant_inputs_keep_the_calibration(self):
        # medicine at its targets from the seed on: run_constant (the anchors' equilibria) is what it was
        inp = M.Inputs(sol=14, literacy=0.4, mods=dict(self.MODS))
        _ring, last = M.run_constant(inp, years=60)
        qf, qm, _mmr = M.group_rates(inp)
        self.assertAlmostEqual(last["e0"], (M.life_table(qf)["e0"] + M.life_table(qm)["e0"]) / 2, places=9)


class TestOnTopSplit(unittest.TestCase):
    """demographics_model.on_top_split (the Causes of Death plan, Task 6, re-planned on #907's window): the window's
    events less the pops' own lines over the same window, each end weighted as window_events weighs the rate."""

    def test_no_start_is_the_snapshot(self):
        events, state, sev = M.on_top_split((1500.0, 400.0, 300.0))
        self.assertEqual(events, 1500.0)
        self.assertAlmostEqual(state, 1100.0)
        self.assertAlmostEqual(sev, 300.0)

    def test_each_part_is_weighted_as_the_rate(self):
        w = P.WINDOW_START_WEIGHT
        events, state, sev = M.on_top_split((1600.0, 600.0, 600.0), start=(1000.0, 100.0, 0.0))
        self.assertAlmostEqual(events, M.window_events(1600.0, 1000.0))
        self.assertAlmostEqual(events - state, w * 100.0 + (1 - w) * 600.0)
        self.assertAlmostEqual(sev, (1 - w) * 600.0, msg="a famine only at the end books (1 - w) of it")

    def test_the_whole_states_part_is_never_below_zero(self):
        self.assertEqual(M.on_top_split((100.0, 300.0, 0.0))[1], 0.0)



class TestPractices(unittest.TestCase):
    """Late Marriage (lm) and Birth Spacing (bs): docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md
    §2-§4; the plan's D5 for the seed."""

    def test_the_terms_multiply_outside_the_means(self):
        inp = M.Inputs(sol=8, literacy=0.2, urban_share=0.1)
        base = M.fertility(inp, 35.0)
        both = M.fertility(dataclasses.replace(inp, practices={"lm": 1.0, "bs": 0.5}), 35.0)
        want = base["tfr"] * (1 - P.PRACTICE_CUT["lm"]) * (1 - P.PRACTICE_CUT["bs"] * 0.5)
        self.assertAlmostEqual(both["tfr"], want, places=9)
        self.assertAlmostEqual(both["lm"], 1 - P.PRACTICE_CUT["lm"])
        self.assertAlmostEqual(both["bs"], 1 - P.PRACTICE_CUT["bs"] * 0.5)
        self.assertEqual(both["means"], base["means"], "the practices act outside the means")

    def test_no_share_is_no_term(self):
        terms = M.fertility(M.Inputs(sol=8), 35.0)
        self.assertEqual((terms["lm"], terms["bs"]), (1.0, 1.0))

    def test_the_start_tables(self):
        for practice, state, region, want in (
                ("lm", "STATE_HOME_COUNTIES", "region_western_europe", 1.0),
                ("lm", "STATE_KOLA", "region_northern_europe", 0.2),
                ("lm", "STATE_GALICIA", "region_southern_europe", 0.9),
                ("lm", "STATE_NEW_CASTILE", "region_southern_europe", 0.6),
                ("lm", "STATE_CAPE_VERDE", "region_southern_europe", 0.0),
                ("lm", "STATE_LAZIO", "region_southern_europe", 0.5),
                ("lm", "STATE_PROVENCE", "region_southern_europe", 1.0),
                ("lm", "STATE_POSEN", "region_eastern_europe", 0.8),
                ("lm", "STATE_MAZOVIA", "region_eastern_europe", 0.4),
                ("lm", "STATE_MOSCOW", "region_russia", 0.0),
                ("lm", "STATE_KANTO", "region_northeast_asia", 0.0),
                ("bs", "STATE_KANTO", "region_northeast_asia", 1.0),
                ("bs", "STATE_RYUKYU_ISLANDS", "region_northeast_asia", 0.0),
                ("bs", "STATE_SEOUL", "region_northeast_asia", P.BS_EAST_ASIA_START),
                ("bs", "STATE_JIANGSU", "region_north_china", P.BS_EAST_ASIA_START),
                ("bs", "STATE_BOMBAY", "region_south_india", P.BS_HELD_START),
                ("bs", "STATE_HOME_COUNTIES", "region_western_europe", 0.0)):
            with self.subTest(practice=practice, state=state):
                self.assertEqual(M.practice_start(practice, state, region), want)

    def test_the_held_groups(self):
        """Owner, 2026-10-11 (plan D13): China, Manchuria and Korea take one Birth Spacing share, India another."""
        for state, region, want in (("STATE_JIANGSU", "region_north_china", "east_asia"),
                                    ("STATE_SEOUL", "region_northeast_asia", "east_asia"),
                                    ("STATE_BOMBAY", "region_south_india", "india"),
                                    ("STATE_KANTO", "region_northeast_asia", None),
                                    ("STATE_MOSCOW", "region_russia", None)):
            self.assertEqual(M.bs_held_group(state, region), want, state)

    def test_the_start_tables_name_only_real_places(self):
        import demographics_regions as R
        table = R.load_table()
        for practice in P.PRACTICES:
            self.assertLessEqual(set(P.PRACTICE_START_REGION[practice]), set(table), practice)
            self.assertLessEqual(set(P.PRACTICE_START_STATE[practice]), set(R.strategic_region_of()), practice)

    def test_late_marriage_target(self):
        # 1836: nothing beyond traditional methods, No Women's Rights, Primogeniture on half-farming land (its Late
        # Marriage line, 0.15, from the game files)
        inp = scenario(literacy=0.4, laws=frozenset({"law_no_womens_rights", "law_primogeniture"}), agrarian_share=0.5,
                       female_job_share=0.2)
        work = P.LM_WOMENS_WORK * 0.2 * 0.1 / P.FULL_FEMALE_WORK_SHARE
        self.assertAlmostEqual(M.practice_target("lm", inp, 0.0), 0.15 * 0.5 + work)
        self.assertEqual(M.practice_target("lm", inp, 1.0), 1.0, "clamped at 1")
        # era 3's pair at literacy 0.75: the means beyond traditional methods are 0.35 x 0.825 = 0.289 (and no
        # impartible inheritance: mods holds no Late Marriage line)
        late = dataclasses.replace(inp, literacy=0.75, female_job_share=0.0, mods={P.CONTRACEPTION_TYPE: 0.35})
        erosion = P.PRACTICE_EROSION_CONTRACEPTION * min(1.0, (0.35 * 0.825 - P.PRACTICE_EROSION_FROM)
                                                         / P.PRACTICE_EROSION_SPAN)
        self.assertAlmostEqual(M.practice_target("lm", late, 1.0), 1 - erosion)
        self.assertAlmostEqual(M.practice_target("lm", dataclasses.replace(late, mods={P.ACCESS_TYPE: 1.0}), 1.0),
                               1.0, msg="health care doesn't erode Late Marriage")

    def test_birth_spacing_target_erodes_with_contraception_and_health_access(self):
        inp = M.Inputs(literacy=0.3, mods={P.ACCESS_TYPE: 0.25})
        self.assertAlmostEqual(M.practice_target("bs", inp, 1.0),
                               1 - P.PRACTICE_EROSION_ACCESS["bs"] * 0.25 / P.PRACTICE_ACCESS_SPAN)
        full = dataclasses.replace(inp, literacy=1.0, mods={P.ACCESS_TYPE: 1.0, P.CONTRACEPTION_TYPE: 0.5})
        self.assertEqual(M.practice_target("bs", full, 1.0), 0.0, "the erosion is at most 1")
        self.assertEqual(M.practice_target("bs", M.Inputs(agrarian_share=1.0, mods={P.LM_FARMS_TYPE: 0.15}), 0.0), 0.0,
                         "nothing builds Birth Spacing up")

    def test_birth_spacing_erodes_with_the_access_medicine_has_reached(self):
        """Since #916 the census's health-care access drifts toward its target (te_dg_acc). Birth Spacing's erosion
        reads that drifted access above the base, not the law's modifier, so it fades as medicine spreads; with no
        drift held (a seed, or a save from before #916) it reads the target, which is the modifier."""
        line = 0.5
        lagging = M.Inputs(mods={P.ACCESS_TYPE: line}, medicine={"access": P.BASE_ACCESS + 0.1,
                                                                 "infection": 0.0, "maternal": 0.0, "chronic": 0.0})
        self.assertAlmostEqual(M.practice_target("bs", lagging, 1.0),
                               1 - P.PRACTICE_EROSION_ACCESS["bs"] * 0.1 / P.PRACTICE_ACCESS_SPAN)
        at_target = dataclasses.replace(lagging, medicine=None)
        self.assertAlmostEqual(M.practice_target("bs", at_target, 1.0),
                               1 - P.PRACTICE_EROSION_ACCESS["bs"] * line / P.PRACTICE_ACCESS_SPAN)

    def test_drift_closes_its_rate_of_the_gap(self):
        self.assertAlmostEqual(M.practice_drift(1.0, 0.45), 1.0 - P.PRACTICE_RATE * 0.55)
        self.assertEqual(M.practice_drift(0.0, 0.0), 0.0)

    def test_a_seed_takes_its_siblings_people_weighted_mean_else_its_eroded_start(self):
        inp = M.Inputs()
        self.assertAlmostEqual(M.practice_seed("lm", inp, 0.0, [(300.0, 0.8), (100.0, 0.4)]), 0.7)
        self.assertEqual(M.practice_seed("lm", inp, 0.4, []), 0.4, "nothing eroded: the start")
        self.assertEqual(M.practice_seed("lm", inp, 0.4, [(0.0, 0.9)]), 0.4, "siblings with no people don't count")
        # review I2: an old save's or a mid-game switch's state seeds at its start less what its conditions eroded
        late = M.Inputs(literacy=1.0, mods={P.CONTRACEPTION_TYPE: 1.0, P.ACCESS_TYPE: 1.0})
        self.assertEqual(M.practice_seed("bs", late, 1.0, []), 0.0, "a 1950 Japan seeds with its spacing gone")
        self.assertAlmostEqual(M.practice_seed("bs", M.Inputs(mods={P.ACCESS_TYPE: 0.25}), 1.0, []),
                               1 - P.PRACTICE_EROSION_ACCESS["bs"] * 0.5)
        drivers = M.Inputs(female_job_share=1.0, laws=frozenset({"law_protected_class"}), agrarian_share=1.0,
                           mods={P.LM_FARMS_TYPE: 0.15, P.FEMALE_WORK_SHARE_TYPE: 0.38})
        self.assertEqual(M.practice_seed("lm", drivers, 0.0, []), 0.0,
                         "the drivers stay out of the seed: Japan's Late Marriage starts at 0 (call 3)")

    def test_a_seed_with_no_sibling_takes_its_regions_copy(self):
        """Stop B, I1 (owner, 2026-10-12): a whole state region changing hands makes a new state object with no sibling;
        its seed takes the region's copy of the shares (te_dg_pr_<P>_r, written at each step), before the eroded
        start. A sibling holding a share still comes first."""
        late = M.Inputs(literacy=1.0, mods={P.CONTRACEPTION_TYPE: 1.0})
        self.assertEqual(M.practice_seed("lm", late, 1.0, [], region=0.85), 0.85, "the region's copy, not 0.3")
        self.assertAlmostEqual(M.practice_seed("lm", late, 1.0, [(100.0, 0.6)], region=0.85), 0.6, msg="sibling first")
        self.assertAlmostEqual(M.practice_seed("lm", late, 1.0, [], region=None), 0.3, msg="nothing: the eroded start")
        self.assertEqual(M.practice_seed("lm", late, 1.0, [], region=0.0), 0.0, "a copy of 0 is a copy")

    def test_marriage_age(self):
        self.assertEqual(M.marriage_age(1.0), 26)
        self.assertEqual(M.marriage_age(0.0), 19)


class TestPhase2Interfaces(unittest.TestCase):
    """Phase 2 step 1 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1): the figures
    the census stores and applies nowhere yet."""

    FARM = dict(sol=8, literacy=0.1, urban_share=0.05, laws=frozenset({"law_no_womens_rights",
                                                                        "law_child_labor_allowed"}))

    def test_the_bands_cover_both_tables(self):
        self.assertEqual(P.BIO_BANDS, tuple(sorted(set(P.CAPACITY) | set(P.HEALTH_NEED))))
        self.assertEqual(M.band_value(P.CAPACITY, 59), 1.0)
        self.assertEqual(M.band_value(P.CAPACITY, 64), P.CAPACITY[60])
        self.assertEqual(M.band_value(P.CAPACITY, 150), P.CAPACITY[85])
        self.assertEqual(M.band_value(P.HEALTH_NEED, 4), 1.0)
        self.assertEqual(M.band_value(P.HEALTH_NEED, 14), 0.5)

    def test_the_working_age_start_follows_the_childrens_rights_law(self):
        """The share is the laws' census line (2026-10-17), read from the game files."""
        for law, share in (("law_child_labor_allowed", 0.3), ("law_restricted_child_labor", 0.1),
                           ("law_compulsory_primary_school", 0.0)):
            inp = scenario(laws=frozenset({law}))
            self.assertEqual([M.start_factor(inp, a) for a in (9, 10, 14, 15)], [0.0, share, share, 1.0], law)
        self.assertEqual(M.child_work_share(M.Inputs()), 0.0, "no law carrying a line: no child at work")
        self.assertEqual(M.child_work_share(M.Inputs(mods={P.CHILD_WORK_TYPE: 1.5})), 1.0, "at most all of them")

    def test_womens_rate_rises_with_the_family_and_the_lower_strata(self):
        none = M.Inputs()
        full = M.Inputs(mods={P.WOMENS_WORK_TYPE: P.WOMENS_WORK_FULL})
        self.assertAlmostEqual(M.women_rate(none), P.WOMEN_BASE)
        self.assertAlmostEqual(M.women_rate(full), P.MEN_RATE)
        self.assertAlmostEqual(M.women_rate(M.Inputs(mods={P.WOMENS_WORK_TYPE: 9.0})), P.MEN_RATE, msg="capped")
        lower = M.Inputs(low_share=0.8)
        self.assertAlmostEqual(M.women_rate(lower), 0.8 * P.WOMEN_LOWER + 0.2 * P.WOMEN_BASE)
        self.assertAlmostEqual(M.women_rate(dataclasses.replace(full, low_share=0.8)), P.MEN_RATE,
                               msg="the floor never lowers a law's rate")

    def test_call_3s_inputs_move_the_rates_and_capacity_within_bounds(self):
        inp = M.Inputs(mods={P.MALE_PARTICIPATION_TYPE: 0.03, P.PARTICIPATION_TYPE: 0.01, P.CAPACITY_TYPE: -0.1})
        rf, rm = M.sex_rates(inp)
        self.assertAlmostEqual(rm, P.MEN_RATE + 0.04)
        self.assertAlmostEqual(rf, P.WOMEN_BASE + 0.01)
        self.assertAlmostEqual(M.capacity_at(inp, 30), 0.9)
        self.assertAlmostEqual(M.capacity_at(inp, 62), P.CAPACITY[60] * 0.9)
        big = M.Inputs(mods={P.MALE_PARTICIPATION_TYPE: 0.5, P.CAPACITY_TYPE: 0.5})
        self.assertEqual(M.sex_rates(big)[1], 1.0)
        self.assertEqual(M.capacity_at(big, 30), 1.0)
        self.assertAlmostEqual(M.capacity_at(big, 82), min(P.CAPACITY[80] * 1.5, 1.0))

    def test_the_working_ages_end_by_the_welfare_law(self):
        self.assertEqual(M.working_ages_end(M.Inputs(), 61.0), (999.0, False, False), "no pension: no end (D10)")
        oap = M.Inputs(laws=frozenset({"law_old_age_pension"}))
        self.assertEqual(M.working_ages_end(oap, 61.0), (65, True, True))
        self.assertEqual(M.working_ages_end(dataclasses.replace(oap, pension_age=70.0), 61.0), (70.0, True, True))
        for law in P.NO_PENSION_AGE_LAWS:
            self.assertEqual(M.working_ages_end(M.Inputs(laws=frozenset({law})), 61.0), (61.0, True, False), law)

    def test_figures_of_a_hand_built_ring(self):
        ring = M.Ring(year=1900)
        for a, f, m in ((5, 100, 100), (12, 50, 50), (30, 200, 200), (66, 40, 30)):
            k = (1900 - a) % M.N
            ring.f[k], ring.m[k] = float(f), float(m)
        ring.pool_f, ring.pool_m = 1.0, 1.0
        inp = scenario(laws=frozenset({"law_child_labor_allowed", "law_old_age_pension"}), low_share=0.5)
        rf = M.women_rate(inp)
        got = M.work_figures(ring, inp, 60.0)
        total = 200 + 100 + 400 + 70 + 2
        wa = 100 + 400                                   # 12-year-olds at 0.3, 30-year-olds; 66 is past 65
        workers = (50 * rf + 50 * 0.92) * 0.3 + (200 * rf + 200 * 0.92) \
            + (40 * rf + 30 * 0.92) * P.CAPACITY[65] * P.AFTER_PENSION_SHARE \
            + (rf + 0.92) * P.CAPACITY[85] * P.AFTER_PENSION_SHARE
        need = 200 * 0.5 + 100 * 0.5 + 400 * 0.8 + 70 * 2.4 + 2 * 4.5
        self.assertAlmostEqual(got["wa_share"], wa / total)
        self.assertAlmostEqual(got["at_work"], workers / wa)
        self.assertAlmostEqual(got["pensioners"], 72 / total)
        self.assertAlmostEqual(got["need"], need / total / P.HEALTH_NEED_1836)
        self.assertAlmostEqual(M.wf_target(got), P.WORKFORCE_SCALE * workers / total)

    def test_with_no_pension_law_the_pool_is_of_working_age(self):
        """D10: with no pension law the working ages have no end, so even the pool (150+) is in them, at capacity's
        last band (te_demog_work_finish's no-pension branch)."""
        ring = M.Ring(year=1900)
        k = (1900 - 30) % M.N
        ring.f[k], ring.m[k] = 200.0, 200.0
        ring.pool_f, ring.pool_m = 1.0, 1.0
        inp = M.Inputs(laws=frozenset({"law_child_labor_allowed"}))
        rf = M.women_rate(inp)
        got = M.work_figures(ring, inp, 60.0)
        self.assertAlmostEqual(got["wa_share"], 1.0)
        self.assertAlmostEqual(got["at_work"], (200 * rf + 200 * 0.92 + (rf + 0.92) * P.CAPACITY[85]) / 402)
        self.assertEqual(got["pensioners"], 0.0)

    def test_the_targets_at_the_starting_values(self):
        """The spec's §1.8 sketch: 1836 farming about 0.25 on the engine's scale, a rich aged state about 0.40."""
        farm = scenario(low_share=0.85, **self.FARM)
        ring, _last = M.run_constant(farm, years=300)
        qf, qm, _ = M.group_rates(farm)
        self.assertAlmostEqual(M.wf_target(M.work_figures(ring, farm, M.old_age(qf, qm))), 0.25, delta=0.02)
        self.assertAlmostEqual(M.old_age(qf, qm), 59.3, delta=1.0)

    def test_the_old_age_threshold_has_fifteen_years_left(self):
        qf, qm, _ = M.group_rates(scenario(**self.FARM))
        for q in (qf, qm):
            age = M.old_age_threshold(q)
            self.assertGreater(age, 50)
            self.assertLess(age, 70)
        flat = [100000.0] * len(P.GROUPS)                 # everyone dies in their first year
        self.assertEqual(M.old_age_threshold(flat), float(P.OLD_AGE_FROM))

    def test_planned_and_unplanned_sum_to_the_children_per_woman(self):
        for kw in (self.FARM, dict(sol=35, literacy=0.95, urban_share=0.8,
                                   techs=frozenset({"vulcanization", "feminism", "contraceptive_pill"}))):
            fert = M.fertility(scenario(**kw), 60.0)
            self.assertAlmostEqual(fert["planned"] + fert["unplanned"], fert["tfr"], places=12)
            self.assertAlmostEqual(fert["unplanned"], fert["tfr"] / fert["factor"] * (1 - fert["means"]), places=12)

    def test_one_schedule_keeps_todays_birth_line(self):
        self.assertIs(P.ASFR_PLANNED_SHAPE, P.ASFR_UNPLANNED_SHAPE)
        for r in (14, 15, 27, 49, 50):
            self.assertEqual(M.slot_births(1234.5, r, r + 3, 4.2, 0.3), 1234.5 * M.asfr_shape(r) / 100000.0 * 4.2)

    def test_two_schedules_split_by_the_planned_share(self):
        other = {15: 10000, 20: 30000, 25: 30000, 30: 20000, 35: 7000, 40: 2500, 45: 500}
        with unittest.mock.patch.object(P, "ASFR_UNPLANNED_SHAPE", other):
            got = M.slot_births(1000.0, 27, 32, 4.0, 0.25)
        want = (P.ASFR_SHAPE_BY_GROUP[25] / 5 * 0.25 + other[30] / 5 * 0.75) * 1000.0 / 100000.0 * 4.0
        self.assertAlmostEqual(got, want)


class TestPhase2Step2(unittest.TestCase):
    """Phase 2 step 2 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §2): the workforce
    term, the pension setting, the two bills and the work deaths' split."""

    def test_the_term_ramps_toward_its_target(self):
        step = P.WF_RAMP_STEP
        self.assertAlmostEqual(M.workforce_term(0.2, 0.0, 0.0), step)
        self.assertAlmostEqual(M.workforce_term(-0.2, 0.0, 0.0), -step)
        self.assertAlmostEqual(M.workforce_term(0.003, 0.0, 0.0), 0.003, msg="within a step it lands")
        self.assertAlmostEqual(M.workforce_term(0.15, 0.30, 0.0), 0.30 - step, msg="from the pair it replaces")

    def test_the_guard_keeps_every_pop_at_its_floor(self):
        """The lowest base (aristocrats' 0.2) + W + the lines on top stays at WF_POP_RATIO_MIN; no cap above."""
        floor = P.WF_POP_RATIO_MIN - P.POP_BASE_RATIO_MIN
        self.assertAlmostEqual(M.workforce_term(-0.5, floor, 0.0), floor)
        self.assertAlmostEqual(M.workforce_term(-0.5, floor, -0.1), floor + 0.1, msg="a negative line on top")
        self.assertAlmostEqual(M.workforce_term(5.0, 4.0, 0.0), 4.0 + P.WF_RAMP_STEP, msg="no cap")
        self.assertEqual(P.POP_BASE_RATIO_MIN, 0.2)

    def test_the_term_nets_only_the_define(self):
        fig = {"wa_share": 0.7, "at_work": 0.5}
        self.assertAlmostEqual(M.workforce_term_target(fig), P.WORKFORCE_SCALE * 0.35 - 0.25)
        self.assertAlmostEqual(M.engine_total(fig, 0.3, 0.05), P.WORKFORCE_SCALE * 0.35 + 0.05 + 0.05)

    def test_fixed_positions_take_their_ages(self):
        for pos in ("early", "standard", "raised"):
            self.assertEqual(M.pension_position_age(pos, 80.0, 90.0), float(P.PENSION_AGE[pos]))

    def test_linked_positions_follow_the_threshold_a_year_a_year_from_65(self):
        self.assertEqual(M.pension_position_age("linked_average", 65.0, 77.0), 66.0)
        self.assertEqual(M.pension_position_age("linked_common", 71.5, 75.0), 70.5, msg="down a year too")
        self.assertEqual(M.pension_position_age("linked_average", 65.0, 62.0), 65.0, msg="the floor")
        self.assertEqual(M.pension_position_age("linked_average", 65.0, None), 65.0, msg="no census: the floor")
        self.assertEqual(M.pension_position_age("linked_average", None, 77.0), 72.0, msg="none yet: at once")
        self.assertEqual(M.pension_position_age("linked_average", 60.0, 77.0), 66.0,
                         msg="from Early: the floor first, then a year (the script's choice, then its drift)")

    def test_the_pension_bill_is_pensioners_times_b(self):
        self.assertAlmostEqual(M.pension_bill_gdp_share(0.2, 5), 0.2 * P.PENSION_B_PER_LEVEL * 5)
        self.assertEqual(M.pension_bill_gdp_share(0.2, 0), 0.0)

    def test_the_health_term(self):
        self.assertAlmostEqual(M.health_term(1.0), 0.0)
        self.assertAlmostEqual(M.health_term(1.5), P.HEALTH_NEED_WEIGHT * 0.5)
        self.assertAlmostEqual(M.health_term(0.9), -P.HEALTH_NEED_WEIGHT * 0.1, msg="a young country: below 0")
        self.assertAlmostEqual(M.health_term(9.0), P.HEALTH_NEED_CAP, msg="the need term's cap")
        self.assertAlmostEqual(M.health_term(1.0, frozenset(P.HEALTH_TECHS) | {"railways"}),
                               P.HEALTH_TECH_STEP * len(P.HEALTH_TECHS))

    def test_work_deaths_split_by_the_census_under_full(self):
        inp = scenario(laws=frozenset({"law_protected_class"}))
        self.assertAlmostEqual(M.work_death_share(inp), P.FULL_FEMALE_WORK_SHARE, msg="the laws' share outside Full")
        full = dataclasses.replace(inp, work_female_share=0.3)
        self.assertEqual(M.work_death_share(full), 0.3)
        f, m = M.work_split(full, 2.0)
        self.assertAlmostEqual(f, 2.0 * 2 * 0.3)
        self.assertAlmostEqual(m, 2.0 * 2 * 0.7)

    def test_the_figures_count_workers_past_the_end_and_the_split(self):
        ring = M.Ring(year=1900)
        for a, f, m in ((30, 100, 100), (70, 40, 30)):
            k = (1900 - a) % M.N
            ring.f[k], ring.m[k] = float(f), float(m)
        inp = M.Inputs(laws=frozenset({"law_old_age_pension"}), low_share=0.5)
        rf, rm = M.sex_rates(inp)
        got = M.work_figures(ring, inp, 60.0)
        past = (40 * rf + 30 * rm) * P.CAPACITY[70] * P.AFTER_PENSION_SHARE
        self.assertAlmostEqual(got["past"], past / 270)
        self.assertAlmostEqual(got["fws_work"], 100 * rf / (100 * rf + 100 * rm), msg="15-64 only")
        self.assertIsNone(M.work_figures(M.Ring(year=1900), inp, 60.0)["fws_work"])


class TestMalariaFactor(unittest.TestCase):
    """Calibration step 3 (the spec's §2.2): infection x (1 + the trait's excess x (1 - the control))."""

    def test_the_factor(self):
        def f(level, control=0.0):
            inp = M.Inputs(sol=7, malaria=level, mods={P.MALARIA_CONTROL_TYPE: control})
            return M.cause_factors(inp)["infection"]["malaria"]
        self.assertEqual(f(0), 1.0)
        self.assertAlmostEqual(f(1), 1 + P.MALARIA_INFECTION[1])
        self.assertAlmostEqual(f(2), 1 + P.MALARIA_INFECTION[2])
        self.assertAlmostEqual(f(2, 0.5), 1 + P.MALARIA_INFECTION[2] / 2)
        self.assertEqual((f(1, 1.0), f(2, 3.0)), (1.0, 1.0), "Malaria Prevention ends it")
        self.assertAlmostEqual(f(1, -1.0), 1 + P.MALARIA_INFECTION[1], msg="the control is 0 to 1")

    def test_the_severe_traits_excess_follows_vanillas_ratio(self):
        self.assertAlmostEqual(P.MALARIA_INFECTION[2], P.MALARIA_INFECTION[1] * P.MALARIA_SEVERE_RATIO, delta=0.005)
        self.assertEqual(P.CAUSE_FACTORS["infection"][-1], "malaria")

    def test_malaria_raises_deaths_and_shortens_life(self):
        e0 = [M.life_table(M.group_rates(M.Inputs(sol=7, literacy=0.05, malaria=level))[0])["e0"] for level in (0, 2)]
        self.assertLess(e0[1], e0[0])


class TestConsequences(unittest.TestCase):
    """Phase 2 step 4 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §4): the pool,
    conscription, the war dead's window, the youth bulge and sex balance."""

    def test_the_pool_is_men_of_twenty_to_thirty_nine(self):
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        rows = ring.by_age()
        self.assertAlmostEqual(ring.fam, sum(m for a, _f, m in rows if 20 <= a <= 39))
        self.assertAlmostEqual(ring.faw, sum(f for a, f, _m in rows if 20 <= a <= 39))
        # the two clocks: the calendar floor and the biological ceiling (equal until phase 3)
        self.assertTrue(M.in_pool(20, 39) and M.in_pool(80, 30))
        self.assertFalse(M.in_pool(19, 19) or M.in_pool(30, 40))

    def test_the_1836_reference_gives_no_term(self):
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        self.assertLess(abs(M.conscription_term(ring.fam, ring.people())), 0.02)

    def test_the_term_falls_as_far_as_the_pool_and_rises_without_limit(self):
        """Owner, 2026-10-16: the +0.25 ceiling is gone; only the -1 floor (no conscripts) remains."""
        self.assertEqual(M.conscription_term(0.0, 1000.0), P.CONSCRIPTION_MIN)
        self.assertAlmostEqual(M.conscription_term(500.0, 1000.0), 500.0 / 1000.0 / P.CONSCRIPTION_REF - 1)
        self.assertGreater(M.conscription_term(500.0, 1000.0), 2.0)
        self.assertAlmostEqual(M.conscription_term(P.CONSCRIPTION_REF * 1.5 * 1000.0, 1000.0), 0.5)
        self.assertAlmostEqual(M.conscription_term(P.CONSCRIPTION_REF * 0.75 * 1000.0, 1000.0), -0.25)
        self.assertEqual(P.CONSCRIPTION_MIN, -1.0)
        self.assertFalse(hasattr(P, "CONSCRIPTION_MAX"))

    def test_war_dead_come_from_the_pools_ages(self):
        """§4.2: a year's war dead leave the cohorts of rate ages 20-39, 95% of them men."""
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        twin = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        M.step(ring, AGRARIAN_1836, 1837, war_dead=5000.0)
        M.step(twin, AGRARIAN_1836, 1837)
        lost = {a: (tf - f, tm - m) for (a, f, m), (_b, tf, tm) in zip(ring.by_age(), twin.by_age())}
        self.assertAlmostEqual(sum(w for w, _m in lost.values()), 5000.0 * (1 - P.WAR_DEAD_MALE_SHARE), places=3)
        self.assertAlmostEqual(sum(m for _w, m in lost.values()), 5000.0 * P.WAR_DEAD_MALE_SHARE, places=3)
        for a, (w, m) in lost.items():
            if not 21 <= a <= 40:                  # ages after the step: rate ages 20-39
                self.assertAlmostEqual(w + m, 0.0, places=6, msg=f"age {a}")
        self.assertGreater(lost[21][1], 0.0)
        self.assertGreater(lost[40][1], 0.0)

    def test_the_youth_bulge(self):
        self.assertEqual(M.youth_bulge(0.16, 0.3), 0.0)
        self.assertEqual(M.youth_bulge(0.25, 0.0), 0.0)
        self.assertEqual(M.youth_bulge(0.24, 0.2), 1.0)
        self.assertAlmostEqual(M.youth_bulge(0.21, 0.1), 0.25)
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        self.assertLess(M.youth_share(ring), P.YOUTH_FROM)

    @unittest.mock.patch.object(P, "SEX_BALANCE_EFFECTS", True)   # judged as if on (held back: the switch)
    def test_the_sex_balance_terms(self):
        self.assertEqual((M.sex_births(None), M.sex_women_add(None), M.sex_fewer_men(None), M.sex_more_men(None)),
                         (1.0, 0.0, 0.0, 0.0))
        for balance in (90.0, 95.0, 100.0, 110.0):
            self.assertEqual((M.sex_births(balance), M.sex_fewer_men(balance), M.sex_more_men(balance)), (1.0, 0.0, 0.0))
        # the Soviet Union of 1959, 82 men per 100 women: births about -9%, women's rate about +0.09 (the design §4.4)
        self.assertAlmostEqual(M.sex_births(82.0), 82.0 / 90.0)
        self.assertLess(abs(M.sex_births(82.0) - 0.91), 0.01)
        self.assertAlmostEqual(M.sex_women_add(82.0), 0.08)
        self.assertEqual(M.sex_births(60.0), P.SEX_BIRTHS_FLOOR)
        self.assertEqual((M.sex_fewer_men(80.0), M.sex_women_add(75.0)), (1.0, P.SEX_WOMEN_RATE))
        self.assertEqual((M.sex_more_men(150.0), M.sex_more_men(170.0)), (1.0, 1.0))
        self.assertAlmostEqual(M.sex_more_men(130.0), 0.5)

    @unittest.mock.patch.object(P, "SEX_BALANCE_EFFECTS", True)   # judged as if on (held back: the switch)
    def test_the_fertility_term_scales_planned_and_unplanned_alike(self):
        inp = dataclasses.replace(BRITAIN_1836, sex_balance=82.0)
        fert, plain = M.fertility(inp, 40.0), M.fertility(BRITAIN_1836, 40.0)
        self.assertAlmostEqual(fert["tfr"], plain["tfr"] * 82.0 / 90.0)
        self.assertAlmostEqual(fert["planned"] + fert["unplanned"], fert["tfr"])
        self.assertAlmostEqual(M.women_rate(inp), M.women_rate(BRITAIN_1836) + 0.08)

    @unittest.mock.patch.object(P, "SEX_BALANCE_EFFECTS", True)   # judged as if on (held back: the switch)
    def test_the_step_reads_the_rings_balance_before_its_sweep(self):
        """A ring short of men has fewer births than the same ring at its own balance."""
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        twin = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        for a in range(20, 60):
            ring.m[(1836 - a) % P.RING_YEARS] *= 0.85
            twin.m[(1836 - a) % P.RING_YEARS] *= 0.85
        balance = M.structure(ring)["men_per_100_women"]
        self.assertLess(balance, P.SEX_FEWER_FROM)
        self.assertGreater(balance / P.SEX_FEWER_FROM, P.SEX_BIRTHS_FLOOR)
        out = M.step(ring, AGRARIAN_1836, 1837)
        self.assertAlmostEqual(out["fertility"]["sex"], balance / P.SEX_FEWER_FROM)
        with unittest.mock.patch.object(M, "sex_births", lambda _b: 1.0):
            plain = M.step(twin, AGRARIAN_1836, 1837)
        self.assertAlmostEqual(out["births"] / plain["births"], balance / P.SEX_FEWER_FROM, places=6)

    def test_a_balanced_ring_keeps_todays_births(self):
        """The 1836 world's balances (91.5-98 in the census's 1836 save) take no term."""
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        self.assertGreater(M.structure(ring)["men_per_100_women"], P.SEX_FEWER_FROM)
        self.assertEqual(M.step(ring, AGRARIAN_1836, 1837)["fertility"]["sex"], 1.0)

    def test_the_three_effects_are_on(self):
        """The migrant booking (2026-10-12) turned on what step 4 held back: conscription, the youth bulge and sex
        balance."""
        self.assertTrue(P.CONSCRIPTION_EFFECTS and P.YOUTH_BULGE_EFFECTS and P.SEX_BALANCE_EFFECTS)

    @unittest.mock.patch.object(P, "SEX_BALANCE_EFFECTS", False)
    def test_held_back_the_sex_balance_effects_are_neutral(self):
        """demographics_params.SEX_BALANCE_EFFECTS off (held back, as step 4 shipped): every sex-balance term is
        neutral, so a ring short of men steps as a balanced one would."""
        for balance in (50.0, 82.0, 150.0):
            self.assertEqual((M.sex_births(balance), M.sex_women_add(balance), M.sex_fewer_men(balance),
                              M.sex_more_men(balance)), (1.0, 0.0, 0.0, 0.0))
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        for a in range(20, 60):
            ring.m[(1836 - a) % P.RING_YEARS] *= 0.85
        self.assertEqual(M.step(ring, AGRARIAN_1836, 1837)["fertility"]["sex"], 1.0)

    def test_conscription_and_the_youth_bulge_apply_past_their_cut_offs(self):
        """T and y are figures the census keeps; none applies while their switches are off (held back, as step 4
        shipped), and when on, none below the cut-offs (the review's Minor 2)."""
        with unittest.mock.patch.object(P, "CONSCRIPTION_EFFECTS", False), \
                unittest.mock.patch.object(P, "YOUTH_BULGE_EFFECTS", False):
            self.assertEqual((M.conscription_applied(-0.5), M.youth_applied(0.8)), (0.0, 0.0))
        with unittest.mock.patch.object(P, "CONSCRIPTION_EFFECTS", True), \
                unittest.mock.patch.object(P, "YOUTH_BULGE_EFFECTS", True):
            self.assertEqual((M.conscription_applied(-0.5), M.youth_applied(0.8)), (-0.5, 0.8))
            self.assertEqual((M.conscription_applied(0.009), M.conscription_applied(-0.009)), (0.0, 0.0))
            self.assertEqual((M.conscription_applied(0.01), M.youth_applied(0.019), M.youth_applied(0.02)),
                             (0.01, 0.0, 0.02))
