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
                   P.CONTRACEPTION_TYPE: {"technology"}, P.MEANS_SHIFT_TYPE: {"law"},
                   P.NATURAL_FERTILITY_TYPE: {"law"}}
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

    def test_womens_rights_carry_the_natural_fertility_term(self):
        lines = {c.key: c.value for c in DM.load_carriers() if c.type == P.NATURAL_FERTILITY_TYPE}
        self.assertEqual(lines, {k: v for k, v in P.NATURAL_FERTILITY_BY_LAW.items() if v})

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


# Phase 2 step 4, owner amendment (2026-10-10): nothing changes outside Full. The census cancels the lines it absorbs
# through its own term M, under Full only, and edits no carrier. These are the 26 lines Tasks 6 and 8 had cancelled
# or deleted, at their values on main (origin/main 079d67da, compared line by line with engine_rate_lines).
RESTORED = {
    ("institution", "institution_ministry_of_consumer_protection", "modifier", "state_mortality_mult"): -0.01,
    ("law", "law_charitable_health_system", "institution_modifier", "state_mortality_mult"): -0.03,
    ("law", "law_public_health_insurance", "institution_modifier", "state_mortality_mult"): -0.05,
    ("law", "law_private_health_insurance", "institution_modifier", "state_mortality_wealth_mult"): -0.002,
    ("law", "law_child_labor_allowed", "modifier", "state_farmers_mortality_mult"): 0.05,
    ("law", "law_child_labor_allowed", "modifier", "state_laborers_mortality_mult"): 0.05,
    ("law", "law_child_labor_allowed", "modifier", "state_machinists_mortality_mult"): 0.05,
    ("law", "law_child_labor_allowed", "modifier", "state_peasants_mortality_mult"): 0.05,
    ("law", "law_restricted_child_labor", "modifier", "state_farmers_mortality_mult"): 0.02,
    ("law", "law_restricted_child_labor", "modifier", "state_laborers_mortality_mult"): 0.02,
    ("law", "law_restricted_child_labor", "modifier", "state_peasants_mortality_mult"): 0.02,
    ("law", "law_no_womens_rights", "modifier", "state_birth_rate_mult"): 0.05,
    ("law", "law_women_in_the_fields", "modifier", "state_birth_rate_mult"): -0.1,
    ("law", "law_women_in_the_workplace", "modifier", "state_birth_rate_mult"): -0.05,
    ("law", "law_womens_suffrage", "modifier", "state_birth_rate_mult"): -0.05,
    ("law", "law_protected_class", "modifier", "state_birth_rate_mult"): -0.1,
    ("law", "law_state_sponsored_family_planning", "modifier", "state_birth_rate_mult"): -0.05,
    ("law", "law_unrestricted_augmentation", "modifier", "state_mortality_mult"): -0.05,
    ("law", "law_medical_augmentation_only", "institution_modifier", "state_mortality_mult"): -0.02,
    ("law", "law_regulated_augmentation_market", "institution_modifier", "state_mortality_mult"): -0.02,
    ("law", "law_mandatory_augmentation", "institution_modifier", "state_mortality_mult"): -0.02,
    ("technology", "modern_vaccines", "modifier", "state_birth_rate_mult"): 0.05,
    ("technology", "modern_vaccines", "modifier", "state_mortality_mult"): -0.05,
    ("technology", "antibiotic_mass_production", "modifier", "state_birth_rate_mult"): 0.05,
    ("technology", "antibiotic_mass_production", "modifier", "state_mortality_mult"): -0.05,
    ("technology", "contraceptive_pill", "modifier", "state_birth_rate_mult"): -0.1,
}


class TestEngineRateLines(unittest.TestCase):
    """Owner, 2026-10-11 (docs/superpowers/plans/2026-10-11-demographics-engine-lines-script-only.md): every birth or
    mortality line a law, technology or institution carried now sits on a script-only type, in the absorbed family
    (the census models it under Full) or the on-top family (the census applies it at its rate). Vanilla's are moved by
    an INJECT that cancels the field and carries the type (te_demog_engine_line_injections.txt), the mod's in place."""

    INJECTIONS = ROOT / "common" / "laws" / "te_demog_engine_line_injections.txt"

    @classmethod
    def setUpClass(cls):
        cls.lines = DM.engine_rate_lines()
        cls.vanilla = DM.engine_rate_lines(mod=False)
        cls.moved = DM.engine_lines()
        cls.carriers = DM.line_carriers()

    def live(self):
        return {k: v for k, v in self.lines.items() if abs(v) > 1e-9 and DM.is_engine_rate_field(k[3])}

    def test_the_lines_tasks_6_and_8_took_off_sit_on_their_types(self):
        """The lines amendment A restored (2026-10-10) now sit on their types at the same values."""
        for k, v in RESTORED.items():
            self.assertAlmostEqual(self.moved[k][1], v, msg=k)

    def test_every_vanilla_line_is_cancelled_and_carried(self):
        """Each vanilla birth or mortality line nets to 0 (the tooltip drops it) and its type carries vanilla's value."""
        for k, v in self.vanilla.items():
            if DM.is_engine_rate_field(k[3]) and abs(v) > 1e-9:
                self.assertAlmostEqual(self.lines.get(k, 0.0), 0.0, msg=k)
                self.assertAlmostEqual(self.moved[k][1], v, msg=k)

    def test_no_census_input_file_sets_an_engine_rate_line_on_a_carrier(self):
        """The census's own files among the laws, technologies and institutions carry its inputs only, except the
        injection file, whose engine fields only cancel vanilla's."""
        carriers = [ROOT / "common" / d for d in ("laws", "technology", "institutions")]
        for path in sorted(p for d in carriers for p in d.rglob("te_demog_*.txt")):
            if path == self.INJECTIONS:
                continue
            code = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
            fields = {f for f in re.findall(r"\b(state_\w+_mult)\s*=", code) if DM.is_engine_rate_field(f)}
            self.assertEqual(fields, set(), path.name)

    def test_the_census_types_are_not_engine_rate_fields(self):
        for t in P.DEMOG_TYPES:
            self.assertFalse(DM.is_engine_rate_field(t), t)
        for f in ("state_birth_rate_mult", "state_mortality_mult", "state_laborers_mortality_mult",
                  "state_mortality_wealth_mult"):
            self.assertTrue(DM.is_engine_rate_field(f), f)

    def test_the_families_match_the_on_top_lists(self):
        """A line's family is written on its carrier; P's on-top lists must agree with the files."""
        for (kind, key, block, field), (family, v) in self.moved.items():
            on_top = key in P.ENGINE_LINES_ON_TOP or field in P.ENGINE_FIELDS_ON_TOP
            self.assertEqual(family, "ontop" if on_top else "absorbed", (kind, key, block, field))

    def test_line_carriers_keep_the_engines_scaling(self):
        """A law's institution_modifier line is per level of the law's institution and an institution's own line per
        its level, both in incorporated states only (kinds law_institution and institution); every other line is flat."""
        got = {(c.kind, c.key, c.type): (c.value, c.institution) for c in self.carriers}
        health = "institution_health_system"
        absorbed_d = "state_demog_absorbed_mortality_mult"
        self.assertEqual(got[("law_institution", "law_charitable_health_system", absorbed_d)], (-0.03, health))
        self.assertEqual(got[("law_institution", "law_public_health_insurance", absorbed_d)], (-0.05, health))
        self.assertEqual(got[("law_institution", "law_private_health_insurance", "state_demog_ontop_mortality_wealth_mult")],
                         (-0.002, health))
        consumer = "institution_ministry_of_consumer_protection"
        self.assertEqual(got[("institution", consumer, absorbed_d)], (-0.01, consumer))
        self.assertEqual(got[("law_institution", "law_regulated_augmentation_market", absorbed_d)], (-0.02, consumer))
        self.assertEqual(got[("law", "law_unrestricted_augmentation", absorbed_d)], (-0.05, None))
        self.assertEqual(got[("law", "law_child_labor_allowed", "state_demog_absorbed_laborers_mortality_mult")], (0.05, None))
        self.assertEqual(got[("technology", "contraceptive_pill", "state_demog_absorbed_birth_rate_mult")], (-0.1, None))
        self.assertEqual(len(got), len(self.carriers), "one carrier per line")

    def test_every_restored_line_but_wealth_mortality_is_absorbed(self):
        """Owner, 2026-10-10 and 2026-10-11: Private Health Insurance's wealth line is on top (the census applies it at
        its rate under Full, floored: P.WEALTH_LINE_FLOOR); every other restored line is absorbed."""
        for k in RESTORED:
            self.assertEqual(self.moved[k][0], "ontop" if k[3] == "state_mortality_wealth_mult" else "absorbed", k)
        self.assertIn("state_mortality_wealth_mult", P.ENGINE_FIELDS_ON_TOP)

    def test_the_on_top_carriers_keep_their_lines(self):
        """Each carrier the census adds on top still carries an on-top line: one listed with no line left would be a
        stale entry (#881 took three LGBTQ+ Rights laws' lines away)."""
        on_top = {k[1] for k, (family, v) in self.moved.items() if family == "ontop"}
        self.assertEqual(sorted(P.ENGINE_LINES_ON_TOP - on_top), [])

    def test_the_natural_fertility_sizes_follow_the_owners_rule(self):
        """Owner call (d), 2026-10-10: each women's-rights law's natural fertility is its own birth line re-centred on
        No Women's Rights (its +0.05 is the reference), so a vanilla patch that moves a line moves the term with it.
        Women Own Property has no line (0 - 0.05); Protected Class's is the mod's own -0.10."""
        ref = self.vanilla[("law", "law_no_womens_rights", "modifier", "state_birth_rate_mult")]
        want = {law: self.moved.get(("law", law, "modifier", "state_birth_rate_mult"), (None, 0.0))[1] - ref
                for law in ("law_no_womens_rights", "law_women_in_the_fields", "law_women_own_property",
                            "law_women_in_the_workplace", "law_womens_suffrage", "law_protected_class")}
        self.assertAlmostEqual(want["law_protected_class"], -0.15)
        carried = {c.key: c.value for c in DM.load_carriers() if c.type == P.NATURAL_FERTILITY_TYPE}
        for law, value in want.items():
            self.assertAlmostEqual(carried.get(law, 0.0), value, msg=law)
            self.assertAlmostEqual(P.NATURAL_FERTILITY_BY_LAW.get(law, 0.0), value, msg=law)

    def test_line_totals_take_a_countrys_flat_lines(self):
        lines = {("law", "law_a", "modifier", "state_birth_rate_mult"): 0.05,
                 ("law", "law_b", "modifier", "state_birth_rate_mult"): -0.1,
                 ("technology", "tech_a", "modifier", "state_mortality_mult"): -0.05,
                 ("law", "law_a", "institution_modifier", "state_mortality_mult"): 0.5}   # per level: left out
        self.assertEqual(DM.engine_line_totals(lines, laws={"law_a"}, techs={"tech_a"}),
                         {"state_birth_rate_mult": 0.05, "state_mortality_mult": -0.05})

    def test_womens_rights_birth_lines_are_absorbed(self):
        """Vanilla's women's-rights birth lines (and Protected Class's) sit in the absorbed family: under Full the
        census's natural-fertility term (Task 7 of the 2026-10-10 plan) carries their effect."""
        for law in ("law_no_womens_rights", "law_women_in_the_fields", "law_women_in_the_workplace",
                    "law_womens_suffrage", "law_protected_class"):
            family, value = self.moved[("law", law, "modifier", "state_birth_rate_mult")]
            self.assertEqual(family, "absorbed", law)
            self.assertNotIn(law, P.ENGINE_LINES_ON_TOP)

    def test_augmentation_carries_flat_chronic_treatment_beside_its_mortality_lines(self):
        """The design note's values as totals: flat lines (kind 'law'), not per level (an institution_modifier
        line at +0.10 would give +0.50 at level 5). The laws' own mortality lines are absorbed."""
        chronic = {(c.key, c.kind): c.value for c in DM.load_carriers() if c.type == "state_chronic_treatment_add"}
        self.assertEqual(chronic.get(("law_medical_augmentation_only", "law")), 0.10)
        self.assertEqual(chronic.get(("law_unrestricted_augmentation", "law")), 0.05)
        self.assertEqual(chronic.get(("law_regulated_augmentation_market", "law")), 0.05)
        self.assertEqual(chronic.get(("law_mandatory_augmentation", "law")), 0.05)   # owner, 2026-10-10
        self.assertFalse(any(kind == "law_institution" and "augmentation" in key for key, kind in chronic))
        self.assertEqual(P.TREATMENT_CAP["chronic"], 0.85)
        absorbed = {k[1] for k, (family, v) in self.moved.items()
                    if family == "absorbed" and k[3] == "state_mortality_mult"}
        self.assertTrue(self.AUGMENTATION_LAWS <= absorbed)

    AUGMENTATION_LAWS = {"law_medical_augmentation_only", "law_unrestricted_augmentation",
                         "law_regulated_augmentation_market", "law_mandatory_augmentation"}


if __name__ == "__main__":
    unittest.main()
