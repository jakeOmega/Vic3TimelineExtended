"""scripts/analysis/demographics_modifiers.py: carriers from the game files and a state's totals."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402

C = DM.Carrier


class TestTotals(unittest.TestCase):
    CARRIERS = [
        C("technology", "antibiotics", "state_infection_treatment_add", 0.26),
        C("law", "law_child_labor_allowed", "state_work_mortality_mult", 0.1),
        C("law_institution", "law_public_health_insurance", "state_health_care_access_add", 0.12,
          "institution_health_system"),
        C("institution", "institution_ministry_of_consumer_protection", "state_external_mortality_mult", -0.08,
          "institution_ministry_of_consumer_protection"),
    ]
    LEVELS = {"institution_health_system": 3, "institution_ministry_of_consumer_protection": 2}

    def test_nothing_held_is_all_zero(self):
        t = DM.totals(self.CARRIERS)
        self.assertEqual(set(t), set(P.DEMOG_TYPES))
        self.assertEqual(set(t.values()), {0.0})

    def test_techs_and_laws_count_everywhere(self):
        t = DM.totals(self.CARRIERS, techs={"antibiotics"}, laws={"law_child_labor_allowed"}, incorporated=False)
        self.assertAlmostEqual(t["state_infection_treatment_add"], 0.26)
        self.assertAlmostEqual(t["state_work_mortality_mult"], 0.1)

    def test_institution_lines_scale_by_level_in_incorporated_states(self):
        t = DM.totals(self.CARRIERS, laws={"law_public_health_insurance"}, institutions=self.LEVELS)
        self.assertAlmostEqual(t["state_health_care_access_add"], 0.36)
        self.assertAlmostEqual(t["state_external_mortality_mult"], -0.16)

    def test_unincorporated_states_get_no_institution_line(self):
        t = DM.totals(self.CARRIERS, laws={"law_public_health_insurance"}, institutions=self.LEVELS,
                      incorporated=False)
        self.assertEqual(t["state_health_care_access_add"], 0.0)
        self.assertEqual(t["state_external_mortality_mult"], 0.0)

    def test_a_law_institution_line_needs_its_law(self):
        t = DM.totals(self.CARRIERS, institutions=self.LEVELS)
        self.assertEqual(t["state_health_care_access_add"], 0.0)


class TestCarriersInTheGameFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.carriers = DM.load_carriers()

    def test_every_type_has_a_carrier(self):
        carried = {c.type for c in self.carriers}
        for name in P.DEMOG_TYPES:
            self.assertIn(name, carried, name)

    def test_each_type_sits_where_its_design_puts_it(self):
        # access only per Ministry of Health level (incorporated states); treatment on techs, and chronic treatment
        # also as the augmentation laws' flat lines (phase 2 step 4)
        allowed = {P.ACCESS_TYPE: {"law_institution"},
                   **{t: {"technology"} for t in P.TREATMENT_TYPE.values()},
                   P.TREATMENT_TYPE["chronic"]: {"technology", "law"},
                   "state_external_mortality_mult": {"technology", "law", "institution"},
                   "state_work_mortality_mult": {"law", "law_institution"},
                   "state_chronic_mortality_mult": {"law"},
                   P.CONTRACEPTION_TYPE: {"technology"}, P.MEANS_SHIFT_TYPE: {"law"}}
        for c in self.carriers:
            self.assertIn(c.kind, allowed[c.type], c)

    def test_health_laws_carry_access_on_the_health_institution(self):
        access = {c.key: c for c in self.carriers if c.type == P.ACCESS_TYPE}
        self.assertEqual(set(access), {"law_charitable_health_system", "law_private_health_insurance",
                                       "law_public_health_insurance"})
        for c in access.values():
            self.assertEqual(c.institution, "institution_health_system")
        self.assertLess(access["law_charitable_health_system"].value, access["law_private_health_insurance"].value)
        self.assertLess(access["law_private_health_insurance"].value, access["law_public_health_insurance"].value)

    def test_contraception_sits_on_the_four_means_techs(self):
        lines = {c.key: c.value for c in self.carriers if c.type == P.CONTRACEPTION_TYPE}
        self.assertEqual(set(lines), {"vulcanization", "feminism", "contraceptive_pill", "modern_pharmaceuticals"})
        self.assertTrue(all(v > 0 for v in lines.values()), lines)
        # all four together keep the tier at or below 1
        self.assertLessEqual(P.TRADITIONAL_MEANS + sum(lines.values()), 1.0)

    def test_family_planning_law_shifts_the_means(self):
        lines = {c.key: c.value for c in self.carriers if c.type == P.MEANS_SHIFT_TYPE}
        self.assertEqual(lines, {"law_state_sponsored_family_planning": 0.1})

    AUGMENTATION = {"law_medical_augmentation_only", "law_unrestricted_augmentation",
                    "law_regulated_augmentation_market", "law_mandatory_augmentation"}

    def test_every_treatment_carrier_is_a_technology(self):
        """Apart from the augmentation laws' flat chronic treatment (phase 2 step 4, their old mortality lines)."""
        for c in self.carriers:
            if c.type in P.TREATMENT_TYPE.values():
                if c.kind == "law":
                    self.assertEqual(c.type, P.TREATMENT_TYPE["chronic"], c)
                    self.assertIn(c.key, self.AUGMENTATION, c)
                else:
                    self.assertEqual(c.kind, "technology", c)
                self.assertGreater(c.value, 0, c)


RATE_FIELDS = re.compile(r"^state_(birth_rate|mortality|mortality_wealth|\w+_mortality)_mult$")


class TestEngineRateLines(unittest.TestCase):
    """Phase 2 step 4: every birth or mortality line a law, technology or institution carries either nets to
    nothing (absorbed by the census: §8.4, the inverse INJECTs) or belongs to a carrier added on top."""

    @classmethod
    def setUpClass(cls):
        cls.lines = DM.engine_rate_lines()
        cls.vanilla = DM.engine_rate_lines(mod=False)

    def test_every_line_is_absorbed_or_on_top(self):
        # the census's own script-only types (state_work_mortality_mult and the like) are inputs, not engine lines
        live = {k: v for k, v in self.lines.items()
                if abs(v) > 1e-9 and RATE_FIELDS.match(k[3]) and k[3] not in P.DEMOG_TYPES}
        unexpected = sorted(k for k in live if k[1] not in P.ENGINE_LINES_ON_TOP)
        self.assertEqual(unexpected, [], "a birth or mortality line the census neither absorbs nor adds on top")

    def test_the_vanilla_lines_the_census_absorbs_net_to_zero(self):
        for law, block, field in (("law_charitable_health_system", "institution_modifier", "state_mortality_mult"),
                                  ("law_public_health_insurance", "institution_modifier", "state_mortality_mult"),
                                  ("law_private_health_insurance", "institution_modifier", "state_mortality_wealth_mult"),
                                  ("law_child_labor_allowed", "modifier", "state_laborers_mortality_mult"),
                                  ("law_child_labor_allowed", "modifier", "state_machinists_mortality_mult"),
                                  ("law_child_labor_allowed", "modifier", "state_farmers_mortality_mult"),
                                  ("law_child_labor_allowed", "modifier", "state_peasants_mortality_mult"),
                                  ("law_restricted_child_labor", "modifier", "state_laborers_mortality_mult"),
                                  ("law_restricted_child_labor", "modifier", "state_farmers_mortality_mult"),
                                  ("law_restricted_child_labor", "modifier", "state_peasants_mortality_mult")):
            self.assertNotEqual(self.vanilla.get(("law", law, block, field), 0.0), 0.0, msg=(law, field))
            self.assertAlmostEqual(self.lines.get(("law", law, block, field), 0.0), 0.0, msg=(law, field))

    def test_the_on_top_carriers_exist(self):
        carriers = {k[1] for k in self.lines}
        self.assertEqual(sorted(P.ENGINE_LINES_ON_TOP - carriers), [])

    def test_augmentation_moves_to_flat_chronic_treatment(self):
        """The design note's values as totals: flat lines (kind 'law'), not per level (an institution_modifier
        line at +0.10 would give +0.50 at level 5)."""
        chronic = {(c.key, c.kind): c.value for c in DM.load_carriers() if c.type == "state_chronic_treatment_add"}
        self.assertEqual(chronic.get(("law_medical_augmentation_only", "law")), 0.10)
        self.assertEqual(chronic.get(("law_unrestricted_augmentation", "law")), 0.05)
        self.assertEqual(chronic.get(("law_regulated_augmentation_market", "law")), 0.05)
        self.assertEqual(chronic.get(("law_mandatory_augmentation", "law")), 0.05)   # owner, 2026-10-10
        self.assertFalse(any(kind == "law_institution" and "augmentation" in key for key, kind in chronic))
        self.assertEqual(P.TREATMENT_CAP["chronic"], 0.85)


if __name__ == "__main__":
    unittest.main()
