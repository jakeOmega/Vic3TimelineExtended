"""Demographics phase 2 step 3b: the census reads the Family Policy measures and laws
(docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §3.2, §3.5, §3.7, §5).

The six measure types' reads in the script against their twins in demographics_model (test_demographics_registry's
interpreter), a census step with measures on against the model's step, the family laws' births lines moved to the
absorbed family (the pair re-applies the same totals outside Full), and the harness's `measures` command against §5's
bands. With no measure on, test_demographics_golden holds every census number where it was.
"""

import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path

import test_demographics_registry as R
from test_demographics_registry import (GENERATED_EFFECTS, GENERATED_VALUES, ROOT, _Engine, _block, _engine_for,
                                        _raw_blocks, _text)

sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
import demographics_harness as H  # noqa: E402
import demographics_model as M  # noqa: E402
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402

LAWS_FILE = ROOT / "common" / "laws" / "extra_laws.txt"
VALUES = ROOT / "common" / "script_values" / "te_demog_values.txt"
MS_VALUES = ROOT / "common" / "script_values" / "te_demog_measure_values.txt"
MS_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_measure_modifiers.txt"
PN, PC = P.PRO_NATALIST_LAW, "law_population_control_measures"


def _fixtures(**types):
    """The six types' reads (0 unless given) and the two owner reads, as an engine's fixtures."""
    out = {f"modifier:{t}": 0.0 for t in P.MEASURE_TYPES}
    for short, value in types.items():
        out[f"modifier:{getattr(P, short)}"] = value
    return out


class TestPolicyTerm(unittest.TestCase):
    """te_demog_tfr_policy (generated) against demographics_model.policy_term: the desired type, and Birth Limit's part
    relieved by the Rural Exemption's type x the agrarian share."""

    def test_script_matches_the_model(self):
        for desired in (-1.5, -0.75, -0.3, 0.0, 0.05, 0.24):
            for relief in (0.0, 0.5, 1.5):
                for part in (0.0, -0.3, -0.45):
                    for agr in (None, 0.0, 0.62, 1.0):
                        mods = {P.DESIRED_TYPE: desired, P.BIRTH_LIMIT_RELIEF_TYPE: relief}
                        inp = M.Inputs(mods=mods, birth_limit=part, agrarian_share=agr or 0.0)
                        eng = _Engine({**_fixtures(DESIRED_TYPE=desired, BIRTH_LIMIT_RELIEF_TYPE=relief),
                                       "te_demog_ms_birth_limit_part": part})
                        if agr is not None:
                            eng.vars["te_dg_agr_share"] = agr
                        with self.subTest(desired=desired, relief=relief, part=part, agr=agr):
                            got = eng.value(eng._tree(eng.values, "te_demog_tfr_policy"))
                            self.assertAlmostEqual(got, M.policy_term(inp), places=9)

    def test_the_exemption_halves_birth_limit_on_farms(self):
        """§3.4: the Rural Exemption halves Birth Limit by the state's agrarian share."""
        lines = DM.measure_lines()
        for setting in ("birth_limit", "birth_limit_one"):
            part = lines[setting][P.DESIRED_TYPE]
            relief = lines["rural_exemption"][P.BIRTH_LIMIT_RELIEF_TYPE]
            inp = M.Inputs(mods={P.DESIRED_TYPE: part, P.BIRTH_LIMIT_RELIEF_TYPE: relief}, birth_limit=part,
                           agrarian_share=1.0)
            self.assertAlmostEqual(M.policy_term(inp), 1 + part / 2, msg=setting)
            self.assertAlmostEqual(M.policy_term(dataclasses.replace(inp, agrarian_share=0.0)), 1 + part)

    def test_birth_limits_part_is_the_owners_modifier(self):
        """te_demog_ms_birth_limit_part reads the owner's Birth Limit modifier, at its constants (pinned to the
        modifiers by test_demographics_measures)."""
        body = _block(_text(MS_VALUES), "te_demog_ms_birth_limit_part")
        self.assertIn("owner = { has_modifier = te_demog_ms_birth_limit }", body)
        self.assertIn("value = te_demog_ms_desired_birth_limit\n", body + "\n")
        self.assertIn("owner = { has_modifier = te_demog_ms_birth_limit_one }", body)
        self.assertIn("value = te_demog_ms_desired_birth_limit_one", body)
        # the owner's read stays inside the relief's branch: no state outside Population Control reads the owner for it
        policy = _block(_text(GENERATED_VALUES), "te_demog_tfr_policy")
        self.assertLess(policy.index(f"modifier:{P.BIRTH_LIMIT_RELIEF_TYPE} > 0"),
                        policy.index("te_demog_ms_birth_limit_part"))


class TestDesiredAndUrban(unittest.TestCase):
    """te_demog_desired and te_demog_tfr_urban (hand-written) against demographics_model.fertility's desired and
    urban_term: Family Housing's relief, the policy term, the floor and the cap."""

    def _desired(self, inp, e0):
        eng = _Engine({**_fixtures(), "te_demog_ms_birth_limit_part": inp.birth_limit,
                       **{f"modifier:{t}": inp.mods.get(t, 0.0) for t in P.MEASURE_TYPES}})
        eng.vars.update(te_dg_lit=inp.literacy, te_dg_e0=e0, te_dg_urban_share=inp.urban_share,
                        te_dg_agr_share=inp.agrarian_share)
        return eng

    def test_script_matches_the_model(self):
        for lit, urban, e0 in ((0.1, 0.05, 32.0), (0.98, 0.8, 79.0), (0.6, 0.3, 55.0)):
            for desired in (-0.95, -0.45, 0.0, 0.24, 2.0):
                for housing in (0.0, 0.5, 1.4):
                    mods = {P.DESIRED_TYPE: desired, P.URBAN_RELIEF_TYPE: housing}
                    inp = M.Inputs(literacy=lit, urban_share=urban, mods=mods)
                    want = M.fertility(inp, e0)
                    eng = self._desired(inp, e0)
                    with self.subTest(lit=lit, urban=urban, desired=desired, housing=housing):
                        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_tfr_urban")), want["urban"],
                                               places=9)
                        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_desired")), want["desired"],
                                               places=9)
                        self.assertGreaterEqual(want["desired"], P.DESIRED_FLOOR)
                        self.assertLessEqual(want["desired"], P.DESIRED_CAP)

    def test_family_housing_cancels_half_the_urban_term(self):
        inp = M.Inputs(urban_share=0.8, mods={P.URBAN_RELIEF_TYPE: DM.measure_lines()["family_housing"][
            P.URBAN_RELIEF_TYPE]})
        self.assertAlmostEqual(1 - M.urban_term(inp), (1 - M.urban_term(M.Inputs(urban_share=0.8))) / 2)

    def test_the_hand_written_values_read_the_generated_terms(self):
        values = _text(VALUES)
        desired = _block(values, "te_demog_desired")
        for line in ("multiply = te_demog_tfr_policy", "min = te_demog_k_desired_floor",
                     "max = te_demog_k_desired_cap"):
            self.assertIn(line, desired)
        self.assertIn("multiply = te_demog_urban_left_stored", _block(values, "te_demog_tfr_urban"))


class TestTooltipsShowWhatTheStepUsed(unittest.TestCase):
    """The children-per-woman tooltips show the policy term and urban life as the step stored them (te_dg_policy,
    te_dg_urban_left; te_demog_natural_shown's pattern): a measure switched on between steps moves the live reads, not
    the figures shown beside te_dg_tfr, until the next step."""

    def test_a_measure_between_steps_shows_at_the_next_step(self):
        inp = dataclasses.replace(R.TestCohortScript.INP, mods={**R.TestCohortScript.INP.mods})
        eng = _engine_for(inp, 1836, 250000.0)
        eng.call("te_demog_seed")
        self.assertEqual(eng.vars["te_dg_policy"], 1.0)
        self.assertEqual(eng.vars["te_dg_urban_left"], 1.0)
        shown = {n: eng.value(eng._tree(eng.values, n)) for n in ("te_demog_tfr_policy_shown", "te_demog_tfr_urban")}
        # Child Allowance and Family Housing go on in June
        eng.fixtures[f"modifier:{P.DESIRED_TYPE}"] = 0.19
        eng.fixtures[f"modifier:{P.URBAN_RELIEF_TYPE}"] = 0.5
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_tfr_policy")), 1.19)
        for name, value in shown.items():
            self.assertEqual(eng.value(eng._tree(eng.values, name)), value, name)
        # the next census stores them, and the figure follows
        eng.call("te_demog_prepare")
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_tfr_policy_shown")), 1.19)
        want = M.urban_term(dataclasses.replace(inp, mods={**inp.mods, P.URBAN_RELIEF_TYPE: 0.5}))
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_tfr_urban")), want, places=9)

    def test_the_tooltips_read_the_stored_terms(self):
        loc = _text(ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml")
        self.assertNotIn("ScriptValue('te_demog_tfr_policy')", loc)
        self.assertEqual(loc.count("ScriptValue('te_demog_tfr_policy_shown')"), 2)
        self.assertIn("multiply = te_demog_urban_left_stored", _block(_text(VALUES), "te_demog_tfr_urban"))


class TestMeansLiteracy(unittest.TestCase):
    """te_demog_means (generated) with Sex Education's literacy against demographics_model.means."""

    def test_script_matches_the_model(self):
        for lit in (0.0, 0.35, 0.9, 1.0):
            for extra in (0.0, 0.2, 0.5):
                for contra in (0.0, 0.45):
                    inp = M.Inputs(literacy=lit, mods={P.CONTRACEPTION_TYPE: contra, P.MEANS_LITERACY_TYPE: extra})
                    eng = _Engine({f"modifier:{P.CONTRACEPTION_TYPE}": contra, f"modifier:{P.MEANS_SHIFT_TYPE}": 0.0,
                                   **_fixtures(MEANS_LITERACY_TYPE=extra)})
                    eng.vars["te_dg_lit"] = lit
                    with self.subTest(lit=lit, extra=extra, contra=contra):
                        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_means")), M.means(inp),
                                               places=9)

    def test_sex_education_raises_the_means_where_literacy_is_low(self):
        extra = DM.measure_lines()["sex_education"][P.MEANS_LITERACY_TYPE]
        low = M.Inputs(literacy=0.3, mods={P.CONTRACEPTION_TYPE: 0.45})
        self.assertGreater(M.means(dataclasses.replace(low, mods={**low.mods, P.MEANS_LITERACY_TYPE: extra})),
                           M.means(low))
        full = M.Inputs(literacy=1.0, mods={P.CONTRACEPTION_TYPE: 0.45})
        self.assertEqual(M.means(dataclasses.replace(full, mods={**full.mods, P.MEANS_LITERACY_TYPE: extra})),
                         M.means(full))


class TestMaternal(unittest.TestCase):
    """Restricted Contraception's maternal deaths: the maternal cause's "laws" factor, on the step's stored input."""

    def test_the_stored_input_and_the_factor_match_the_model(self):
        for line in (0.0, 0.25, -0.9):
            inp = M.Inputs(mods={P.MATERNAL_TYPE: line})
            eng = _Engine(R._mod_fixtures(inp))   # every read the store makes (calibration step 3's malaria too)
            eng.vars.update(te_dg_sol=8.0, te_dg_lit=0.0)
            eng.call("te_demog_cause_inputs_store")
            self.assertAlmostEqual(eng.vars["te_dg_in_mat"], line)
            factors = M.cause_factors(inp)["maternal"]
            self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_f_maternal_laws")), factors["laws"])
            self.assertEqual(factors["laws"], max(P.MORTALITY_MULT_FLOOR, 1 + line))

    def test_restricted_contraception_raises_maternal_deaths_by_a_quarter(self):
        line = DM.measure_lines()["restricted_contraception"][P.MATERNAL_TYPE]
        base = M.group_rates(M.Inputs())[2]
        self.assertAlmostEqual(M.group_rates(M.Inputs(mods={P.MATERNAL_TYPE: line}))[2], base * 1.25)


class TestNewbornSplit(unittest.TestCase):
    """te_demog_newborn_split (generated) against demographics_model.newborn_split: the constants unless prenatal
    sexing and a positive sex-ratio type move it."""

    def test_script_matches_the_model(self):
        for tech in (False, True):
            for srb in (0.0, 5.0, 10.0, -3.0):
                inp = M.Inputs(techs=frozenset({P.PRENATAL_SEXING_TECH} if tech else ()), mods={P.SRB_TYPE: srb})
                eng = _Engine({"te_demog_srb_add": max(0.0, srb) if tech else 0.0})
                eng.call("te_demog_newborn_split")
                girls, boys = M.newborn_split(inp)
                with self.subTest(tech=tech, srb=srb):
                    self.assertAlmostEqual(eng.locals["te_dg_nb_f"], girls, places=6)
                    self.assertAlmostEqual(eng.locals["te_dg_nb_m"], boys, places=6)
                    if not tech or srb <= 0:
                        # exactly the constants: 100 x 100,000 / 205 is 48780.49, not the constant's 48780
                        self.assertEqual((girls, boys), (P.FEMALE_BIRTH_PER_100K, P.MALE_BIRTH_PER_100K))

    def test_birth_limit_sets_110_and_115_boys(self):
        lines = DM.measure_lines()
        for setting, boys_per_100 in (("birth_limit", 110), ("birth_limit_one", 115)):
            inp = M.Inputs(techs=frozenset({P.PRENATAL_SEXING_TECH}), mods={P.SRB_TYPE: lines[setting][P.SRB_TYPE]})
            girls, boys = M.newborn_split(inp)
            self.assertAlmostEqual(100 * boys / girls, boys_per_100, places=6)

    def test_the_gate_reads_the_owners_technology(self):
        body = _block(_text(GENERATED_VALUES), "te_demog_srb_add")
        self.assertIn(f"owner = {{ has_technology_researched = {P.PRENATAL_SEXING_TECH} }}", body)
        self.assertIn(f"modifier:{P.SRB_TYPE}", body)
        self.assertIn(f"\n{P.PRENATAL_SEXING_TECH} = {{", "\n" + _text(
            ROOT / "common" / "technology" / "technologies" / "era_8.txt"))

    def test_only_the_steps_newborns_take_it(self):
        """The step's two newborn splits read the locals; the seed (the stable structure) keeps the constants."""
        effects = _raw_blocks([ROOT / "common" / "scripted_effects" / "te_demog_effects.txt"])
        self.assertIn("te_demog_newborn_split = yes", effects["te_demog_step_run"])
        for name in ("te_demog_fold_slot", "te_demog_step_finish"):
            self.assertIn("local_var:te_dg_nb_f", effects[name], name)
            self.assertNotIn("te_demog_k_female_births_per_100k", effects[name], name)
        self.assertIn("te_demog_k_female_births_per_100k", effects["te_demog_seed_slot"])


class TestStepWithMeasures(unittest.TestCase):
    """A census step with measures on, the script against demographics_model.step (TestCohortScript's step_both and
    check_step): desired fertility's policy term, Family Housing, the means (the model's, a fixture here),
    Restricted Contraception's maternal deaths and Birth Limit's sex ratio at birth with prenatal sexing."""

    def setUp(self):
        self.cohort = R.TestCohortScript("test_seed_rates_match_the_model")   # its helpers, not its tests
        self.YEAR, self.POP = self.cohort.YEAR, self.cohort.POP

    def _inp(self, **mods):
        base = self.cohort.INP
        base = dataclasses.replace(base, techs=base.techs | {P.PRENATAL_SEXING_TECH})
        return dataclasses.replace(base, mods={**base.mods, **mods})

    def test_a_pro_natalist_package_steps_as_the_model(self):
        inp = self._inp(**{P.DESIRED_TYPE: 0.24, P.URBAN_RELIEF_TYPE: 0.5, P.MATERNAL_TYPE: 0.25,
                           P.MEANS_SHIFT_TYPE: -0.2})
        eng, ring, figures, pop = self.cohort.step_both(inp=inp)
        self.cohort.check_step(eng, ring, figures, pop)
        self.cohort.close(eng.vars["te_dg_tfr"], figures["tfr"], what="TFR")
        self.cohort.close(eng.vars["te_dg_desired"], figures["fertility"]["desired"], what="desired")
        self.assertGreater(figures["fertility"]["policy"], 1)

    def test_birth_limit_with_the_exemption_steps_as_the_model(self):
        inp = dataclasses.replace(self._inp(**{P.DESIRED_TYPE: -0.55, P.BIRTH_LIMIT_RELIEF_TYPE: 0.5,
                                               P.SRB_TYPE: 10.0}), birth_limit=-0.45, agrarian_share=0.6)

        def engine(fixtures, **kw):
            eng = _Engine(fixtures, **kw)
            eng.vars["te_dg_agr_share"] = inp.agrarian_share   # the walk's, which the Rural Exemption reads
            return eng

        eng, ring, figures, pop = self.cohort.step_both(inp=inp, engine=engine)
        self.cohort.check_step(eng, ring, figures, pop)
        self.cohort.close(eng.vars["te_dg_desired"], figures["fertility"]["desired"], what="desired")
        self.assertAlmostEqual(figures["fertility"]["policy"], 1 - 0.55 + 0.45 * 0.5 * 0.6)
        # the newborns' split moved: 115 boys to 100 girls
        open_k = (self.YEAR + 1) % P.RING_YEARS
        self.cohort.close(eng.vars[f"te_dg_m{open_k}"] / eng.vars[f"te_dg_f{open_k}"], 1.15, rel=1e-6, what="SRB")

    def test_planned_births_take_desired_fertility_and_unplanned_dont(self):
        """§1.6: planned = wealth x natural x means x desired, unplanned = wealth x natural x (1 - means): a measure on
        desired family size moves only the planned part."""
        got = {}
        for name, inp in (("off", self._inp()), ("on", self._inp(**{P.DESIRED_TYPE: 0.24}))):
            eng = _engine_for(inp, self.YEAR, self.POP)
            eng.call("te_demog_seed")
            got[name] = (eng.value(eng._tree(eng.values, "te_demog_tfr_planned")),
                         eng.value(eng._tree(eng.values, "te_demog_tfr_unplanned")))
            fert = M.fertility(inp, eng.vars["te_dg_e0"])
            self.cohort.close(got[name][0], fert["planned"], rel=1e-6, what=f"planned ({name})")
            self.cohort.close(got[name][1], fert["unplanned"], rel=1e-6, what=f"unplanned ({name})")
        self.assertGreater(got["on"][0], got["off"][0])
        self.cohort.close(got["on"][1], got["off"][1], rel=1e-9, what="unplanned unchanged")


class TestFamilyLawsUnderFull(unittest.TestCase):
    """§3.2: Pro-Natalist Policy's and Population Control Measures' births lines move to the absorbed family (M cancels
    them under Full), so outside Full the moved lines' pair re-applies the same totals; Pro-Natalist Policy gains its
    own desired-fertility line; Communal Child-Rearing stays on top."""

    OLD_BIRTHS = {PN: 0.1, PC: -0.1}

    @classmethod
    def setUpClass(cls):
        cls.lines = DM.line_carriers()

    def _refresh(self, law, full):
        sums = DM.totals(self.lines, laws={law}, types=tuple(P.ENGINE_LINE_TYPES.values()))
        eng = _Engine({f"modifier:{n}": v for n, v in sums.items()},
                      triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": full})
        if full:
            eng.vars.update(te_dg_mb=-0.3, te_dg_md=-0.3, te_dg_q_b=0.0, te_dg_q_d=0.0)
        eng.call("te_demog_lines_refresh")
        return eng, sums

    def test_outside_full_the_pair_applies_the_same_births_total(self):
        for law, births in self.OLD_BIRTHS.items():
            eng, sums = self._refresh(law, full=False)
            pair = {k: v for k, v in eng.modifiers.items() if k.startswith("te_demog_line_births_")}
            self.assertEqual(pair, {f"te_demog_line_births_{'up' if births > 0 else 'down'}": abs(births)}, law)
            self.assertAlmostEqual(eng.vars["te_dg_ln_births"], births, msg=law)
            # now on the absorbed family, none on top
            self.assertAlmostEqual(sums["state_demog_absorbed_birth_rate_mult"], births, msg=law)
            self.assertAlmostEqual(sums["state_demog_ontop_birth_rate_mult"], 0.0, msg=law)

    def test_under_full_the_census_term_leaves_them_off(self):
        for law in self.OLD_BIRTHS:
            eng, _ = self._refresh(law, full=True)
            self.assertFalse(any(k.startswith("te_demog_line_births_") for k in eng.modifiers), law)

    def test_the_on_top_list_keeps_communal_child_rearing_only(self):
        self.assertNotIn(PN, P.ENGINE_LINES_ON_TOP)
        self.assertNotIn(PC, P.ENGINE_LINES_ON_TOP)
        self.assertIn("law_communal_child_rearing", P.ENGINE_LINES_ON_TOP)
        sums = DM.totals(self.lines, laws={"law_communal_child_rearing"}, types=tuple(P.ENGINE_LINE_TYPES.values()))
        self.assertAlmostEqual(sums["state_demog_ontop_birth_rate_mult"], -0.2)

    def test_pro_natalist_policy_carries_its_desired_line(self):
        carriers = DM.load_carriers(types=P.DEMOG_TYPES + P.MEASURE_TYPES)
        got = DM.totals(carriers, laws={PN}, types=P.DEMOG_TYPES + P.MEASURE_TYPES)
        self.assertAlmostEqual(got[P.DESIRED_TYPE], 0.05)
        for law in ("law_traditional_family_structure", PC, "law_state_sponsored_family_planning",
                    "law_communal_child_rearing"):
            self.assertEqual(DM.totals(carriers, laws={law}, types=P.MEASURE_TYPES)[P.DESIRED_TYPE], 0.0, law)

    def test_a_release_comments_the_laws_census_line_and_keeps_its_births_line(self):
        """The release script comments every line setting a type of demographics_modifier_types.txt and keeps every
        state_demog_ line (test_release_census_inputs): so Pro-Natalist Policy ships its births line on the pair and
        loses only its desired-fertility line, and keeps its other lines."""
        types = _text(ROOT / "common" / "modifier_type_definitions" / "demographics_modifier_types.txt")
        self.assertIn(f"{P.DESIRED_TYPE} = {{", types)
        body = _block(_text(LAWS_FILE), PN)
        self.assertIn(f"{P.DESIRED_TYPE} = 0.05", body)
        self.assertIn("state_demog_absorbed_birth_rate_mult = 0.10", body)
        self.assertIn("state_welfare_payments_mult = 0.10", body)
        self.assertIn("state_demog_absorbed_birth_rate_mult = -0.1", _block(_text(LAWS_FILE), PC))


class TestHarnessMeasures(unittest.TestCase):
    """demographics_harness.py measures: §5's bands at the fitted sizes."""

    @classmethod
    def setUpClass(cls):
        cls.rows = H.measure_rows()
        cls.shares = H.money_shares()

    def test_the_full_pro_natalist_package_lands_in_its_band(self):
        self.assertTrue(self.rows["rich"])
        for r in self.rows["rich"]:
            with self.subTest(r["label"]):
                self.assertTrue(H.RICH_TFR[0] <= r["base"] <= H.RICH_TFR[1], r["base"])
                self.assertTrue(H.PACKAGE_BAND[0] <= r["package"] <= H.PACKAGE_BAND[1], r["package"])

    def test_each_single_measure_stays_under_its_cap(self):
        for r in self.rows["rich"]:
            for m, (d, coercive) in r["singles"].items():
                if not coercive:
                    self.assertLess(d, H.SINGLE_MAX, f"{r['label']}: {m}")
            # the direction each aims at
            self.assertGreater(r["singles"]["child_allowance"][0], 0)
            self.assertLess(r["singles"]["later_longer_fewer"][0], 0)
            self.assertLess(r["singles"]["birth_limit_one"][0], r["singles"]["birth_limit"][0])

    def test_the_packages_upkeep_is_its_share_of_revenue(self):
        for r in self.rows["rich"]:
            cost = H.package_upkeep(self.shares, H.PRONATAL_PACKAGE, r["young"], r["urban"], 0.0)
            share = cost / H.REVENUE_SHARE_OF_GDP
            self.assertTrue(H.UPKEEP_BAND[0] <= share <= H.UPKEEP_BAND[1], f"{r['label']}: {share:.3%}")

    def test_the_money_shares_are_the_scripts(self):
        self.assertEqual(self.shares, {"child_allowance": 0.005, "family_housing": 0.0025, "parental_leave": 0.003,
                                       "free_contraception": 0.001})

    def test_the_budget_reader(self):
        save = "\n".join([
            "SAV0100", "meta_data={", "}", "country_manager={", "\tdatabase={", "1={", '\tdefinition="AAA"',
            "\tbudget={", "\t\tweekly_income={ 0 10 0 0 0 0 0 500 0 0 0 0 0 0 0 0 }", "\t}", "\tgdp={",
            "\t\tsample_rate=28", "\t\tchannels={", "0={", "\t\t\t\tindex=2", "\t\t\t\tvalues={ 100 2600 9 }",
            "\t\t\t}\t\t}", "\t}", "}", "2={", '\tdefinition="BBB"', "\tbudget={",
            "\t\tweekly_income={ 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 }", "\t}", "\tgdp={", "\t\tchannels={", "0={",
            "\t\t\t\tindex=1", "\t\t\t\tvalues={ 52 }", "\t\t\t}\t\t}", "\t}", "}", "\t}", "}", "states={", "}", ""])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "slice.v3"
            path.write_text(save, encoding="utf-8")
            got = H.budget_shares(str(path))
        # slot 7 (the investment pool's share of construction) is left out; the GDP is the latest sample (index - 1)
        self.assertEqual([(t, g) for t, g, _s in got], [("AAA", 2600.0), ("BBB", 52.0)])
        self.assertAlmostEqual(got[0][2], 10 * 52 / 2600)
        self.assertAlmostEqual(got[1][2], 1.0)

    def test_the_command_runs_and_passes(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = H.main(["measures"])
        self.assertEqual(code, 0, buf.getvalue())
        self.assertIn("package", buf.getvalue())


class TestGeneratedReads(unittest.TestCase):
    def test_every_measure_type_is_read_in_state_scope(self):
        text = _text(GENERATED_VALUES) + _text(GENERATED_EFFECTS)
        for name in P.MEASURE_TYPES:
            self.assertIn(f"modifier:{name}", text, name)
            self.assertNotIn(f"owner.modifier:{name}", text, name)

    def test_the_measures_file_is_the_harness_source(self):
        """Each measure's census types come from its modifier, the source the harness reads."""
        mods = _raw_blocks([MS_MODIFIERS])
        lines = DM.measure_lines()
        self.assertEqual(set(lines), {n[len("te_demog_ms_"):] for n in mods if not n.endswith("_cost")})


if __name__ == "__main__":
    unittest.main()
