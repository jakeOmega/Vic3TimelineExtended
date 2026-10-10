"""scripts/analysis/demographics_modifiers.py: carriers from the game files and a state's totals."""

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
        # access only per Ministry of Health level (incorporated states); treatment only on techs
        allowed = {P.ACCESS_TYPE: {"law_institution"},
                   **{t: {"technology"} for t in P.TREATMENT_TYPE.values()},
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

    def test_contraception_sits_on_the_three_means_techs(self):
        lines = {c.key: c.value for c in self.carriers if c.type == P.CONTRACEPTION_TYPE}
        self.assertEqual(set(lines), {"vulcanization", "contraceptive_pill", "modern_pharmaceuticals"})
        self.assertTrue(all(v > 0 for v in lines.values()), lines)
        # all three together keep the tier at or below 1
        self.assertLessEqual(P.TRADITIONAL_MEANS + sum(lines.values()), 1.0)

    def test_family_planning_law_shifts_the_means(self):
        lines = {c.key: c.value for c in self.carriers if c.type == P.MEANS_SHIFT_TYPE}
        self.assertEqual(lines, {"law_state_sponsored_family_planning": 0.1})

    def test_every_treatment_carrier_is_a_technology(self):
        for c in self.carriers:
            if c.type in P.TREATMENT_TYPE.values():
                self.assertEqual(c.kind, "technology", c)
                self.assertGreater(c.value, 0, c)


if __name__ == "__main__":
    unittest.main()
