"""The demographics cohort model (scripts/analysis/demographics_model.py).

Pins the model's behaviour to the design's anchors
(docs/superpowers/specs/2026-10-08-demographics-design.md §1, §2.2-§2.4, §3) so a
parameter change that breaks a real-world anchor fails here, before it is generated
into script.
"""

import sys
import unittest
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
                                   "institution_ministry_of_consumer_protection": 3})
BRITAIN_1900 = scenario(sol=16, literacy=0.75, urban_share=0.6,
                        techs=frozenset({"medical_degrees", "pharmaceuticals", "modern_nursing", "vulcanization",
                                         "feminism"}),
                        laws=frozenset({"law_charitable_health_system"}), institutions={"institution_health_system": 4})
AGED_TODAY = scenario(sol=38, literacy=0.98, urban_share=0.75, techs=MODERN,
                      laws=frozenset({"law_public_health_insurance", "law_womens_suffrage", "law_old_age_pension",
                                      "law_dedicated_police", "law_state_sponsored_family_planning"}),
                      institutions={"institution_health_system": 6, "institution_workplace_safety": 4,
                                    "institution_ministry_of_consumer_protection": 3})
INDIA_1975 = scenario(sol=9, literacy=0.35, urban_share=0.2,
                      techs=EARLY_MEDICINE | {"modern_vaccines", "contraceptive_pill"},
                      laws=frozenset({"law_charitable_health_system"}))


class TestFertility(unittest.TestCase):
    """§2.3's sketch table: the formula with plausible inputs."""

    def tfr(self, inp):
        _ring, last = M.run_constant(inp, years=200)
        return last["tfr"]

    def test_sketch_cases(self):
        for inp, expected, label in [
            (BRITAIN_1836, 5.5, "Britain 1836"),
            (FRANCE_1836, 4.9, "France 1836 (Family Limitation)"),
            (BRITAIN_1900, 3.85, "Britain 1900"),
            (WEST_1950, 2.8, "the West 1950"),
            (WEST_1990, 1.6, "the West 1990"),
            (INDIA_1975, 5.3, "India 1975"),
        ]:
            with self.subTest(label):
                self.assertAlmostEqual(self.tfr(inp), expected, delta=0.3)

    def test_wealth_term_endpoints(self):
        self.assertAlmostEqual(M.wealth_tfr(0), 6.2)
        self.assertAlmostEqual(M.wealth_tfr(8), 6.2)
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
        self.assertEqual(M.means(self.inp(1.0, {P.CONTRACEPTION_TYPE: 1.0, P.MEANS_SHIFT_TYPE: 1.0})), P.MEANS_CAP)


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
        # migration attraction falls (Inputs.crowding: 0.1 x migration_crowding's multiplier), at most +50%
        def infection(**kw):
            return M.cause_multipliers(M.Inputs(sol=12, literacy=0.3, **kw))["infection"]
        plain = infection()
        self.assertAlmostEqual(infection(crowding=0.038) / plain, 1.038)
        self.assertAlmostEqual(infection(crowding=0.45) / plain, 1.45)
        self.assertAlmostEqual(infection(crowding=1.45) / plain, 1 + P.CROWDING_INFECTION_MAX)
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

    def test_no_deaths_lives_to_the_end_of_the_ring(self):
        self.assertAlmostEqual(M.life_table([0.0] * len(P.GROUPS))["e0"], 150.0)

    def test_work_deaths_follow_the_workforce(self):
        before = M.group_rates(M.Inputs(laws=frozenset({"law_no_womens_rights"})))[0]
        after = M.group_rates(M.Inputs(laws=frozenset({"law_women_in_the_workplace"})))[0]
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

    def test_plain_terms_are_floored(self):
        inp = M.Inputs(mods={"state_work_mortality_mult": -0.9})
        self.assertEqual(M.plain_multiplier(inp, "work"), P.MORTALITY_MULT_FLOOR)
        self.assertEqual(M.cause_multipliers(inp)["work"], P.MORTALITY_MULT_FLOOR)

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
        # §2.2's aged row (about 1.3 children per woman). The West in 1990 alone now gives about 1.6, as
        # history did (stage 2's fit), so the case adds State-Sponsored Family Planning. At 1.3 the stable
        # rate is about ln(0.65) / 30 = -1.4% a year; the sketch's -0.9 to -1.2% came from four bands.
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

    def test_terms_on_top_add_at_the_bare_curves_weight(self):
        """The engine adds every term (growth probe): with M on, a pop's events are bare x (1 + M + O).
        The state's then come to the model's plus bare x O."""
        m, _ = M.rate_term(target=80.0, bare=100.0)
        on_top = 0.3
        self.assertAlmostEqual(100.0 * (1 + m + on_top), 80.0 + 100.0 * on_top)

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
        """A famine or a plague already past -0.8: M may not push further down."""
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

    def test_crude_rates_of_the_stable_population(self):
        cbr, cdr = M.model_crude_rates(M.Inputs(sol=9.0, literacy=0.2))
        self.assertTrue(20 < cbr < 60 and 15 < cdr < 50, (cbr, cdr))

    def test_starvation_terms_follow_the_engine(self):
        self.assertEqual(M.starvation_terms(0.5), (0.0, 0.0))
        self.assertEqual(M.starvation_terms(0.1), (-0.9, 1.0))
        b, d = M.starvation_terms(0.3)   # (0.4 - 0.3) x 2.5 = 0.25 of the mild penalty
        self.assertAlmostEqual(b, -0.7 * 0.25)
        self.assertAlmostEqual(d, 0.6 * 0.25)


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
