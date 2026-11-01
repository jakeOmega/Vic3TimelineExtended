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

    def test_an_amendment_line_counts_while_the_amendment_is_held(self):
        """Undivided Farm Succession's Late Marriage line (2026-10-17): an amendment's modifier, flat, like a law's."""
        lines = [C("amendment", "amendment_undivided_farm_succession", P.LM_FARMS_TYPE, 0.15)]
        self.assertEqual(DM.totals(lines)[P.LM_FARMS_TYPE], 0.0)
        self.assertEqual(DM.totals(lines, laws={"amendment_undivided_farm_succession"})[P.LM_FARMS_TYPE], 0.0,
                         "an amendment is not a law")
        self.assertAlmostEqual(DM.totals(lines, amendments={"amendment_undivided_farm_succession"},
                                         incorporated=False)[P.LM_FARMS_TYPE], 0.15)


class TestCarriersInTheGameFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.carriers = DM.load_carriers()

    def test_every_type_has_a_carrier(self):
        carried = {c.type for c in self.carriers}
        # capacity's only carrier is Pollution Impact's static modifier, which no reader walks
        # (TestWorkforceLinesMoved.BLOCKS pins it), since State Eugenics lost its line (owner, 2026-10-24)
        for name in set(P.DEMOG_TYPES) - {P.CAPACITY_TYPE}:
            self.assertIn(name, carried, name)

    def test_each_type_sits_where_its_design_puts_it(self):
        # access only per Ministry of Health level (incorporated states); treatment on techs, and chronic treatment
        # also as the augmentation laws' flat lines (phase 2 step 4)
        allowed = {P.ACCESS_TYPE: {"law_institution"},
                   **{t: {"technology"} for t in P.TREATMENT_TYPE.values()},
                   P.TREATMENT_TYPE["chronic"]: {"technology", "law"},
                   # the police laws' lines are per level of the Ministry of Public Safety (2026-10-16)
                   "state_external_mortality_mult": {"technology", "law", "law_institution", "institution"},
                   "state_work_mortality_mult": {"law", "law_institution"},
                   # uploaded minds' call 2 (2026-10-19): Mind Backups' restore, x the state's longevity care
                   **{t: {"technology"} for t in P.BACKUP_TYPES.values()},
                   "state_chronic_mortality_mult": {"law"},
                   P.CONTRACEPTION_TYPE: {"technology"}, P.MEANS_SHIFT_TYPE: {"law"},
                   P.NATURAL_FERTILITY_TYPE: {"law"}, P.DIFFUSION_TYPE: {"technology"},
                   # call 3's participation inputs (phase 2 step 1): the criminal-justice laws' flat lines, the
                   # Ministries of Labour per level; Community Service and Mandatory Minimums are amendments (read
                   # since 2026-10-17, when load_carriers took amendments in). No law carries capacity today.
                   P.MALE_PARTICIPATION_TYPE: {"law", "amendment"}, P.PARTICIPATION_TYPE: {"law_institution"},
                   P.CAPACITY_TYPE: {"law"},
                   # calibration step 3: Malaria Prevention's control
                   P.MALARIA_CONTROL_TYPE: {"technology"},
                   # modern safety (2026-10-16): the era 7-9 technologies
                   **{t: {"technology"} for t in P.SAFETY_TYPES.values()},
                   # phase 3, the late game: the ageing ladder and the pull sit on the era 10-12 technologies
                   P.AGEING_RATE_TYPE: {"technology"}, P.REJUVENATION_TYPE: {"technology"},
                   # and who longevity care reaches on the health and augmentation laws (2026-10-17)
                   **{t: {"law"} for t in P.LX_LAW_TYPES},
                   # the laws' other terms (2026-10-17): the childrens'-rights laws' 10-14s at work, the church laws'
                   # weight on Family Limitation, impartible inheritance's Late Marriage (Undivided Farm Succession is
                   # an amendment)
                   P.CHILD_WORK_TYPE: {"law"}, P.FL_LITERACY_TYPE: {"law"}, P.LM_FARMS_TYPE: {"law", "amendment"},
                   # stage 3 (2026-10-19): the migrant profile's transport technologies
                   P.FAMILY_MIGRATION_TYPE: {"technology"}}
        for c in self.carriers:
            self.assertIn(c.kind, allowed[c.type], c)

    def test_ageing_rate_reads_green_because_less_is_better(self):
        """color = good paints a negative value red. The ageing ladder is all negative (a slower pace is the benefit), so
        the type is color = bad, which flips with sign; the rejuvenation pull is positive, so it stays good."""
        text = (ROOT / "common" / "modifier_type_definitions" / "demographics_modifier_types.txt").read_text(
            encoding="utf-8-sig")

        def color(name):
            return re.search(rf"^{name} = \{{[^}}]*?\bcolor = (\w+)", text, re.M).group(1)

        ageing = [c.value for c in self.carriers if c.type == P.AGEING_RATE_TYPE]
        self.assertTrue(ageing and all(v < 0 for v in ageing), ageing)
        self.assertEqual(color(P.AGEING_RATE_TYPE), "bad")
        pull = [c.value for c in self.carriers if c.type == P.REJUVENATION_TYPE]
        self.assertTrue(pull and all(v > 0 for v in pull), pull)
        self.assertEqual(color(P.REJUVENATION_TYPE), "good")

    def test_longevity_care_sits_on_the_health_and_augmentation_laws(self):
        """Late game §4.2 (on the laws since 2026-10-17, so each law's tooltip says what it does): the health laws' cover
        (Private and No Health System none), Mandatory Augmentation's full cover and floor, Unrestricted Augmentation's
        reach, Human Purity's ban, and the market's price falling faster under Private Health Insurance and the
        Regulated Augmentation Market."""
        carried = {}
        for c in self.carriers:
            if c.type in P.LX_LAW_TYPES:
                carried.setdefault(c.type, {})[c.key] = c.value
        self.assertEqual(carried, {
            P.LX_COVER_TYPE: {"law_public_health_insurance": 1.0, "law_charitable_health_system": 0.25,
                              "law_mandatory_augmentation": 1.0},
            P.LX_FLOOR_TYPE: {"law_mandatory_augmentation": 0.9},
            P.LX_REACH_TYPE: {"law_unrestricted_augmentation": 20.0},
            P.LX_BAN_TYPE: {"law_human_purity": 1.0},
            P.LX_PRICE_FALL_TYPE: {"law_private_health_insurance": 1.0, "law_regulated_augmentation_market": 0.5}})

    def test_the_laws_other_census_terms_sit_on_their_laws(self):
        """Each was a has_law lookup until 2026-10-17; now the law carries its value, so its tooltip says what the census
        does with it. A variant carries its parent's (the Millet System and People of the Book, State Religion's)."""
        types = (P.CHILD_WORK_TYPE, P.LM_FARMS_TYPE, P.FL_LITERACY_TYPE)
        carried = {}
        for c in self.carriers:
            if c.type in types:
                carried.setdefault(c.type, {})[c.key] = c.value
        self.assertEqual(carried, {
            P.CHILD_WORK_TYPE: {"law_child_labor_allowed": 0.3, "law_restricted_child_labor": 0.1},
            P.LM_FARMS_TYPE: {"law_primogeniture": 0.15, "amendment_undivided_farm_succession": 0.15},
            P.FL_LITERACY_TYPE: {"law_state_religion": -0.5, "law_millet_system": -0.5, "law_people_of_the_book": -0.5,
                                 "law_total_separation": 0.5, "law_state_atheism": 0.5}})

    def test_the_migrant_profiles_input_sits_on_the_transport_techs(self):
        """Stage 3 (2026-10-19): a technology ladder until then. The transport technologies carry their old figures plus
        the aviation techs §2.5 names (owner, 2026-10-19). The women's-rights laws' share of women at work went on
        2026-10-25: the census's own count of women among its workers took its place, so no law carries a profile
        line."""
        carried = {}
        for c in self.carriers:
            if c.type in P.MIGRANT_PROFILE_TYPES:
                carried.setdefault(c.type, {})[c.key] = c.value
        self.assertEqual(carried, {
            P.FAMILY_MIGRATION_TYPE: {"paddle_steamer": 0.1, "railways": 0.1, "combustion_engine": 0.15,
                                      "commercial_aviation": 0.05, "jet_engine_technology": 0.05}})
        self.assertNotIn("state_female_work_share_add", {c.type for c in DM.load_carriers(
            types=P.DEMOG_TYPES + ("state_female_work_share_add",))})

    def test_late_marriages_two_carriers_never_meet(self):
        """Primogeniture's and Undivided Farm Succession's lines add as modifiers do, where the script's OR counted them
        once: the amendment's allowed laws must leave Primogeniture out, or a country holding both would read 0.30."""
        amendment = DM._u(DM._state(DM.ROOT).get_data("Amendments")["amendment_undivided_farm_succession"])
        allowed = DM._u(amendment.get("allowed_laws"))
        allowed = set(allowed if isinstance(allowed, (list, tuple, set)) else [allowed])
        self.assertTrue(allowed, "the amendment's allowed laws were read")
        self.assertNotIn("law_primogeniture", allowed)

    def test_wealth_concentration_sits_on_the_land_tax_and_economic_laws(self):
        """Spec §4.2's law terms (on the laws since 2026-10-17; not census inputs, so not in P.DEMOG_TYPES). Every
        land-reform law carries its line, a variant at its parent's value, Commercialized Agriculture none."""
        lines = DM.load_carriers(types=P.WC_LAW_TYPES)
        self.assertTrue(all(c.kind == "law" or (c.kind, c.type) == ("amendment", P.WC_INHERITANCE_TYPE) for c in lines),
                        lines)
        carried = {}
        for c in lines:
            carried.setdefault(c.type, {})[c.key] = c.value
        # the inheritance law and its amendments (2026-10-21; #822's has_law lookups until then), from 50: the old
        # targets less 50, Customary Inheritance none
        self.assertEqual(carried[P.WC_INHERITANCE_TYPE], {
            "law_primogeniture": 30.0, "law_free_testation": 10.0, "law_equal_inheritance": -25.0,
            "law_state_universal_heir": -50.0, "law_non_inheritable_usage_rights": -50.0,
            "amendment_estate_duties": -30.0, "amendment_birthright_endowment": -20.0,
            "amendment_perpetual_trusts": 30.0, "amendment_undivided_farm_succession": 10.0})
        self.assertEqual(carried[P.WC_TAX_TYPE], {"law_graduated_taxation": -5.0})
        self.assertEqual(carried[P.WC_ECONOMY_TYPE], {
            "law_laissez_faire": 10.0, "law_extraction_economy": 5.0, "law_interventionism": -5.0,
            "law_guilds_chartered_monopolies": 5.0, "law_freedom_of_contract": 5.0, "law_trust_busting": -5.0,
            "law_regulated_utilities": -5.0})
        # public goods (owner, 2026-10-21): private health care and schooling and strict IP up, public provision down;
        # Terakoya, a variant, at its parent's value (Private Schools); the none, church and open IP laws carry nothing
        self.assertEqual(carried[P.WC_PUBLIC_TYPE], {
            "law_private_health_insurance": 5.0, "law_public_health_insurance": -5.0,
            "law_private_schools": 5.0, "law_terakoya": 5.0, "law_public_schools": -5.0,
            "law_traditional_ip_protection": 5.0, "law_strict_ip_protection": 10.0})
        # slavery (owner, 2026-10-21): property in people; Slavery Banned carries nothing
        self.assertEqual(carried[P.WC_SLAVERY_TYPE], {
            "law_colonial_slavery": 10.0, "law_legacy_slavery": 10.0, "law_debt_slavery": 10.0, "law_slave_trade": 5.0})
        base = {"law_serfdom": 15.0, "law_tenant_farmers": 5.0, "law_peasant_proprietorship": -10.0,
                "law_collectivized_agriculture": -20.0}
        land = carried[P.WC_LAND_TYPE]
        laws = DM._state(DM.ROOT).get_data("Laws")
        group = [k for k, v in laws.items() if DM._u(DM._u(v).get("group")) == "lawgroup_land_reform"]
        self.assertEqual(len(group), 9, group)
        for law in group:
            parent = DM._u(DM._u(laws[law]).get("parent")) or law
            with self.subTest(law=law):
                self.assertEqual(land.get(law), base.get(parent), parent)
        self.assertEqual(set(land), {k for k in group if base.get(DM._u(DM._u(laws[k]).get("parent")) or k)})
        self.assertFalse(set(P.WC_LAW_TYPES) & set(P.DEMOG_TYPES))

    def test_malaria_prevention_alone_controls_malaria(self):
        """Calibration step 3 (the spec's §2.2): the malaria factor ends with Malaria Prevention, not quinine (it protected
        colonists, not the people who lived there), and nothing else carries the control."""
        carried = {c.key: c.value for c in self.carriers if c.type == P.MALARIA_CONTROL_TYPE}
        self.assertEqual(carried, {"malaria_prevention": 1.0})

    def test_modern_safety_sits_on_the_era_7_to_9_technologies(self):
        """Modern safety (owner, 2026-10-16): work safety from building, robots, container ports and office work, 0.90 by
        era 9, and bodies built for the work in era 13 (Self-Directed Evolution, era 13 spec § 7.3), the cap 0.95;
        accidents and violence from planned streets, computer-designed cars and mobile phones, 0.40, and self-driving
        cars in era 11, 0.50."""
        carried = {}
        for c in self.carriers:
            if c.type in P.SAFETY_TYPES.values():
                carried.setdefault(c.type, {})[c.key] = c.value
        self.assertEqual(carried, {
            P.SAFETY_TYPES["work"]: {"prefabricated_construction": 0.15, "robotics": 0.35, "containerization": 0.15,
                                     "knowledge_economy": 0.25, "self_directed_evolution": 0.05},
            P.SAFETY_TYPES["external"]: {"modern_urban_planning": 0.2, "computer_aided_design": 0.1,
                                         "cellular_networks": 0.1, "autonomous_vehicles": 0.1}})
        self.assertLessEqual(max(sum(v.values()) for v in carried.values()), P.SAFETY_MAX)

    def test_policing_and_criminal_justice_lower_deaths_from_violence(self):
        """Accidents and violence (2026-10-16): every police law but No Police lowers the cause a level of the Ministry of
        Public Safety (its institution_modifier, so a law with the Ministry at 0 gives nothing: owner, the review of
        #989), more under a national force; the two progressive criminal-justice laws lower it flat; Penal Labor Camps
        raise work deaths, as Child Labor Allowed does."""
        ext = {(c.kind, c.key): c.value for c in self.carriers if c.type == "state_external_mortality_mult"}
        want = {
            ("law_institution", "law_local_police"): -0.02, ("law_institution", "law_dedicated_police"): -0.03,
            ("law_institution", "law_militarized_police"): -0.03, ("law_institution", "law_private_policing"): -0.02,
            ("law", "law_restorative_justice"): -0.04, ("law", "law_rehabilitation_focused_criminal_justice"): -0.08,
        }
        self.assertEqual({k: v for k, v in ext.items() if k in want}, want)
        police = ("law_no_police", "law_local_police", "law_dedicated_police", "law_militarized_police",
                  "law_private_policing")
        for key in (*police, "law_punishment_focused_criminal_justice", "law_penal_labor_camps"):
            self.assertNotIn(("law", key), ext, "a police law's line is per Ministry level, never flat")
        self.assertNotIn(("institution", "institution_police"), ext, "the Ministry's cut depends on who polices")
        work = {c.key: c.value for c in self.carriers if c.type == "state_work_mortality_mult" and c.kind == "law"}
        self.assertEqual(work["law_penal_labor_camps"], work["law_child_labor_allowed"])
        # the law alone, with no Ministry, gives nothing
        t = DM.totals(self.carriers, laws={"law_dedicated_police"}, institutions={"institution_police": 0})
        self.assertEqual(t["state_external_mortality_mult"], 0.0)
        # a Dedicated Police Force at the Ministry's level 9 under Rehabilitation-Focused criminal justice
        t = DM.totals(self.carriers, laws={"law_dedicated_police", "law_rehabilitation_focused_criminal_justice"},
                      institutions={"institution_police": 9})
        self.assertAlmostEqual(t["state_external_mortality_mult"], -0.35)
        # Private Policing at the same level
        t = DM.totals(self.carriers, laws={"law_private_policing"}, institutions={"institution_police": 9})
        self.assertAlmostEqual(t["state_external_mortality_mult"], -0.18)

    def test_medicine_spreads_from_a_tenth_to_two_fifths(self):
        """The Causes of Death plan: communication and medical-training techs carry the spread of medicine, +0.05 each,
        so a state closes 10% of the gap a year in 1836 and 35% with all five. A party to the World Health
        Organization's convention adds its own +0.05, scaled by the UN's enforcement (40% at an enforcement of 1)."""
        carried = {c.key: c.value for c in self.carriers if c.type == P.DIFFUSION_TYPE}
        self.assertEqual(set(carried), {"electric_telegraph", "modern_nursing", "radio", "world_wide_web",
                                        "telemedicine"})
        self.assertNotIn("intergovernmental_organizations", carried, "the WHO carries that line now")
        t = DM.totals(self.carriers, techs=set(carried))
        self.assertAlmostEqual(P.DIFFUSION_BASE + t[P.DIFFUSION_TYPE], 0.35)
        self.assertAlmostEqual(P.DIFFUSION_BASE + t[P.DIFFUSION_TYPE] + P.WHO_DIFFUSION, 0.4)
        self.assertAlmostEqual(P.DIFFUSION_BASE + DM.totals(self.carriers)[P.DIFFUSION_TYPE], P.DIFFUSION_BASE)

    def test_the_who_convention_carries_its_line(self):
        """The line sits on the convention's static modifier (a static modifier, so load_carriers doesn't walk it), at
        the value the late game's market threshold adds for a party (P.WHO_DIFFUSION)."""
        text = (ROOT / "common" / "static_modifiers" / "extra_modifiers.txt").read_text(encoding="utf-8-sig")
        block = re.search(r"(?ms)^un_pandemic_cooperation_modifier = \{(.*?)^\}", text)
        self.assertIsNotNone(block, "un_pandemic_cooperation_modifier")
        lines = re.findall(rf"(?m)^\t{P.DIFFUSION_TYPE} = ([\d.]+)\s*$", block.group(1))
        self.assertEqual([float(v) for v in lines], [P.WHO_DIFFUSION])

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
    """Owner, 2026-10-11 (docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md): every birth or
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
        self.assertEqual(P.TREATMENT_CAP["chronic"], 0.99)   # owner, 2026-10-20 (was 0.85)
        absorbed = {k[1] for k, (family, v) in self.moved.items()
                    if family == "absorbed" and k[3] == "state_mortality_mult"}
        self.assertTrue(self.AUGMENTATION_LAWS <= absorbed)

    AUGMENTATION_LAWS = {"law_medical_augmentation_only", "law_unrestricted_augmentation",
                         "law_regulated_augmentation_market", "law_mandatory_augmentation"}


class TestWorkforceReaders(unittest.TestCase):
    """Phase 2 step 1 (the design §1.7): the working-adult lines' readers, beside #892's."""

    def test_the_readers_keep_only_the_working_adult_field(self):
        lines = DM.engine_workforce_lines()
        self.assertTrue(lines)
        for (kind, key, block, field), (family, value) in lines.items():
            self.assertEqual(field, P.WORKING_ADULT_FIELD)
            self.assertIn(family, ("womens_work", "replaced"))

    def test_carriers_keep_the_engines_scaling(self):
        by_key = {c.key: c for c in DM.workforce_line_carriers()}
        self.assertEqual(by_key["law_old_age_pension"].kind, "law_institution")
        self.assertEqual(by_key["law_pro_capital_ministry_of_labor"].kind, "law_institution")
        self.assertEqual(by_key["law_womens_suffrage"].kind, "law")
        self.assertEqual(by_key["contraceptive_pill"].kind, "technology")


def _rule_loc():
    """Every English loc value by key, and te_demog_custom_loc.txt's text."""
    loc = {}
    for path in (ROOT / "localization/english").glob("*.yml"):
        for m in re.finditer(r'(?m)^ ([\w.\-]+):\d* "(.*)"\s*$', path.read_text(encoding="utf-8-sig")):
            loc[m.group(1)] = m.group(2)
    return loc, (ROOT / "common/customizable_localization/te_demog_custom_loc.txt").read_text(encoding="utf-8-sig")


class TestCensusOffNames(unittest.TestCase):
    """With the census off, every census-only type's name and description say so (te_demog_custom_loc.txt)."""

    NAME = "[SelectLocalization(GetPlayer.IsValid,'te_demog_census_off_name_ingame','te_demog_census_off_none')]"
    DESC = "[SelectLocalization(GetPlayer.IsValid,'te_demog_census_off_desc_ingame','te_demog_census_off_none')]"

    @classmethod
    def setUpClass(cls):
        types = (ROOT / "common/modifier_type_definitions/demographics_modifier_types.txt").read_text(encoding="utf-8-sig")
        cls.types = re.findall(r"(?m)^(\w+)\s*=\s*\{", types)
        cls.loc, cls.custom = _rule_loc()

    # Types something besides the census reads, so they work with the census off and carry no tag.
    READ_BEYOND_THE_CENSUS = {
        "state_malaria_control_add": "Local Climate's disease relief (te_climate_relief_disease) reads it under every "
                                     "Demographics setting",
    }

    def test_every_census_type_ends_in_the_tag(self):
        self.assertGreater(len(self.types), 40)
        for name in self.types:
            if name in self.READ_BEYOND_THE_CENSUS:
                continue
            self.assertTrue(self.loc.get(name, "").endswith(self.NAME), name)
            self.assertTrue(self.loc.get(name + "_desc", "").endswith(self.DESC), name + "_desc")

    def test_no_other_modifier_carries_the_tag(self):
        """An engine line or a Wealth Concentration term works with the census off, so its name has no tag."""
        tagged = {k for k, v in self.loc.items() if self.NAME in v or self.DESC in v}
        census_only = set(self.types) - set(self.READ_BEYOND_THE_CENSUS)
        self.assertEqual(tagged, census_only | {t + "_desc" for t in census_only})

    def test_malaria_control_works_with_the_census_off(self):
        """Malaria Prevention's Malaria Control also eases Local Climate's malaria cost, census or not, so its
        name and description never say it does nothing."""
        self.assertEqual(self.loc["state_malaria_control_add"], "Malaria Control")
        self.assertIn("[concept_local_climate]", self.loc["state_malaria_control_add_desc"])
        self.assertNotIn("census_off", self.loc["state_malaria_control_add_desc"])

    def test_the_tag_shows_only_while_the_census_doesnt_run(self):
        for entry, key in (("te_demog_census_off_name", "te_demog_census_off_tag"),
                           ("te_demog_census_off_desc", "te_demog_census_off_note")):
            block = re.search(rf"(?ms)^{entry} = \{{(.*?)^\}}", self.custom)
            self.assertIsNotNone(block, entry)
            texts = re.findall(r"trigger = \{ (.*?) \}\s*localization_key = (\w+)", block.group(1))
            self.assertEqual(texts, [("te_demog_cohorts_run = yes", "te_demog_census_off_none"),
                                     ("always = yes", key)], entry)
            self.assertTrue(self.loc[key], key)
        self.assertEqual(self.loc["te_demog_census_off_none"], "")


class TestWorkforceLineNames(unittest.TestCase):
    """Under Full, the two moved Workforce Ratio families' names say what the census does with them instead: the
    replaced family's in a tag after Workforce Ratio, the women's-work family's by reading women's work first (owner,
    2026-10-25)."""

    @classmethod
    def setUpClass(cls):
        cls.loc, cls.custom = _rule_loc()

    def _texts(self, entry):
        block = re.search(rf"(?ms)^{entry} = \{{(.*?)^\}}", self.custom)
        self.assertIsNotNone(block, entry)
        return re.findall(r"trigger = \{ (.*?) \}\s*localization_key = (\w+)", block.group(1))

    def test_these_are_the_two_families(self):
        moved = (ROOT / "common/modifier_type_definitions/demographics_workforce_line_types.txt").read_text(
            encoding="utf-8-sig")
        self.assertEqual(set(re.findall(r"(?m)^(\w+)\s*=\s*\{", moved)),
                         {"state_demog_replaced_ratio_add", "state_demog_womens_work_ratio_add"})

    def test_the_replaced_family_ends_in_its_tag_only_under_full(self):
        self.assertEqual(self.loc["state_demog_replaced_ratio_add"],
                         "$state_working_adult_ratio_add$"
                         "[SelectLocalization(GetPlayer.IsValid,'te_demog_wf_replaced_name_ingame','te_demog_census_off_none')]")
        self.assertEqual(self._texts("te_demog_wf_replaced_name"),
                         [("te_demog_effects_run = yes", "te_demog_wf_replaced_tag"),
                          ("always = yes", "te_demog_census_off_none")])
        # the rendered name is pasted into a quoted tooltip argument (loc_render_audit): no straight apostrophe
        tag = self.loc["te_demog_wf_replaced_tag"]
        self.assertTrue(tag and "'" not in tag)

    def test_the_womens_work_family_reads_womens_work_first_under_full(self):
        self.assertEqual(self.loc["state_demog_womens_work_ratio_add"],
                         "[SelectLocalization(GetPlayer.IsValid,'te_demog_wf_womens_name_ingame','te_demog_wf_plain')]")
        self.assertEqual(self.loc["state_demog_womens_work_ratio_add_desc"],
                         "[SelectLocalization(GetPlayer.IsValid,'te_demog_wf_womens_desc_ingame','te_demog_wf_womens_desc_plain')]")
        self.assertEqual(self._texts("te_demog_wf_womens_name"),
                         [("te_demog_effects_run = yes", "te_demog_wf_womens_full"),
                          ("always = yes", "te_demog_wf_plain")])
        self.assertEqual(self._texts("te_demog_wf_womens_desc"),
                         [("te_demog_effects_run = yes", "te_demog_wf_womens_desc_full"),
                          ("always = yes", "te_demog_wf_womens_desc_plain")])
        full = self.loc["te_demog_wf_womens_full"]
        # "Women's Work" alone since Women's Work Outside the Home went (owner, 2026-10-25)
        self.assertEqual(full, "Women’s Work")
        self.assertNotIn("'", full)  # pasted into a quoted tooltip argument, as above
        self.assertEqual(self.loc["te_demog_wf_plain"], "$state_working_adult_ratio_add$")
        self.assertTrue(self.loc["te_demog_wf_womens_desc_plain"].startswith("$state_working_adult_ratio_add_desc$"))
        self.assertFalse(self.loc["te_demog_wf_womens_desc_full"].startswith("$state_working_adult_ratio_add"))


class TestBirthDeathLineNames(unittest.TestCase):
    """Under Full, the moved birth and death lines' names end in "(Demographics)" (owner, 2026-10-25)."""

    CALL = "[SelectLocalization(GetPlayer.IsValid,'te_demog_line_name_ingame','te_demog_census_off_none')]"

    @classmethod
    def setUpClass(cls):
        cls.loc, cls.custom = _rule_loc()
        cls.types = re.findall(r"(?m)^(\w+)\s*=\s*\{", (
            ROOT / "common/modifier_type_definitions/demographics_engine_line_types.txt").read_text(encoding="utf-8-sig"))

    def test_every_line_type_keeps_its_vanilla_name_and_ends_in_the_tag(self):
        self.assertGreaterEqual(len(self.types), 9)
        for name in self.types:
            self.assertRegex(self.loc[name], rf"^\$state_\w+_mult\${re.escape(self.CALL)}$", name)
        tagged = {k for k, v in self.loc.items() if self.CALL in v}
        self.assertEqual(tagged, set(self.types))

    def test_the_tag_shows_only_under_full(self):
        block = re.search(r"(?ms)^te_demog_line_name = \{(.*?)^\}", self.custom)
        self.assertIsNotNone(block)
        texts = re.findall(r"trigger = \{ (.*?) \}\s*localization_key = (\w+)", block.group(1))
        self.assertEqual(texts, [("te_demog_effects_run = yes", "te_demog_line_tag"),
                                 ("always = yes", "te_demog_census_off_none")])
        self.assertEqual(self.loc["te_demog_line_tag"], " #grey (Demographics)#!")


class TestModifierNamesRenderWithNoPlayer(unittest.TestCase):
    """A modifier type's name and description also render where no player exists: a loading-screen concept tip
    lists a static modifier's lines (vanilla's Pollution Impact shows state_region_pollution_health's), and so does an
    observer's session. `GetPlayer.GetCustom` there logs `Object of type 'country' is not valid for '<entry>'` once per
    frame (about 2,000 lines in 3 seconds on 2026-10-27), so each such name reaches its custom loc through vanilla's
    loading-tip guard, `SelectLocalization(GetPlayer.IsValid, '<x>_ingame', '<plain>')`, and only the `_ingame` key
    calls GetCustom."""

    GUARD = re.compile(r"\[SelectLocalization\(GetPlayer\.IsValid,'(\w+)_ingame','(\w+)'\)\]")

    @classmethod
    def setUpClass(cls):
        cls.loc, _ = _rule_loc()
        cls.types = set()
        for path in (ROOT / "common/modifier_type_definitions").glob("*.txt"):
            cls.types |= set(re.findall(r"(?m)^(\w+)\s*=\s*\{", path.read_text(encoding="utf-8-sig")))

    def test_no_modifier_type_calls_getcustom_on_the_player_unguarded(self):
        self.assertGreater(len(self.types), 100)
        bare = [k for t in self.types for k in (t, t + "_desc") if "GetPlayer.GetCustom(" in self.loc.get(k, "")]
        self.assertEqual(bare, [])

    def test_each_guard_names_its_custom_entry_and_a_plain_fallback(self):
        guarded = {}
        for key, value in self.loc.items():
            for entry, plain in self.GUARD.findall(value):
                guarded[entry] = plain
                self.assertIn(plain, self.loc, key)
        self.assertEqual(set(guarded), {"te_demog_census_off_name", "te_demog_census_off_desc", "te_demog_line_name",
                                        "te_demog_wf_replaced_name", "te_demog_wf_womens_name",
                                        "te_demog_wf_womens_desc"})
        for entry in guarded:
            self.assertEqual(self.loc[entry + "_ingame"], f"[GetPlayer.GetCustom('{entry}')]", entry)


if __name__ == "__main__":
    unittest.main()
