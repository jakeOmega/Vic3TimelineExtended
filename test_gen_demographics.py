"""scripts/generators/gen_demographics.py: the committed script is a fresh generation, and its shape."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts"))

import gen_demographics as gen  # noqa: E402
import demographics_params as P  # noqa: E402
from format_paradox_tabs import format_text  # noqa: E402


class TestGenerated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = gen.plan_outputs()
        cls.effects = cls.outputs[gen.EFFECTS]
        cls.values = cls.outputs[gen.VALUES]

    def test_committed_outputs_are_current(self):
        for rel, text in self.outputs.items():
            self.assertEqual((ROOT / rel).read_text(encoding="utf-8-sig"), text, str(rel))

    def test_committed_bytes_are_current(self):
        # regenerate() compares bytes, so this also pins the one UTF-8 BOM the text comparison above strips.
        result = gen.regenerate(dry_run=True)
        self.assertFalse(result["changed"], result["changed_files"])

    def test_tabs_already_formatted(self):
        for rel, text in self.outputs.items():
            self.assertEqual(format_text(text), text, str(rel))

    def test_five_decimals_at_most(self):
        for rel, text in self.outputs.items():
            self.assertIsNone(re.search(r"\d\.\d{6,}", text), str(rel))

    def test_sweeps_visit_every_slot_twice_in_descending_order(self):
        for name, p1, p2 in (("te_demog_sweep", "te_demog_slot_p1", "te_demog_slot_p2"),
                             ("te_demog_seed_sweep", "te_demog_seed_p1", "te_demog_seed_p2")):
            body = self.effects.split(f"{name} = {{", 1)[1].split("\n}\n", 1)[0]
            calls = re.findall(r"(te_demog_\w+_p[12]) = \{ S = (\d+) \}", body)
            expected = [(p1, str(k)) for k in range(P.RING_YEARS - 1, -1, -1)]
            expected += [(p2, str(k)) for k in range(P.RING_YEARS - 1, -1, -1)]
            self.assertEqual(calls, expected, name)

    def test_one_leaf_per_age_group(self):
        body = self.effects.split("te_demog_enter_group = {", 1)[1].split("\n}\n", 1)[0]
        self.assertEqual(body.count("name = te_dg_next_group"), len(P.GROUPS))

    def test_life_table_calls_pass_both_arguments(self):
        calls = re.findall(r"te_demog_lt_group = \{ (.*?) \}", self.effects)
        self.assertEqual(len(calls), len(P.GROUPS))
        for call in calls:
            self.assertRegex(call, r"^N = \d FERTILE = (yes|no)$")

    def test_engine_curves_match_the_defines(self):
        self.assertIn("te_demog_pop_engine_births = {", self.values)
        self.assertIn("value = 475", self.values)      # 0.00475 a month x 100,000
        self.assertIn("value = 80", self.values)       # 0.00080 at SoL 35+

    def test_land_tenure_variants_take_their_parents_value(self):
        values = gen.land_tenure_values(ROOT)
        self.assertEqual(len(values), 9)
        self.assertEqual(values["law_manorialism"], values["law_serfdom"])
        self.assertEqual(values["law_latifundias"], values["law_tenant_farmers"])
        self.assertEqual(values["law_expanded_latifundias"], values["law_tenant_farmers"])
        self.assertEqual(values["law_homesteading"], values["law_peasant_proprietorship"])

    def test_means_read_the_modifier(self):
        body = self.values.split("te_demog_means = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn(f"add = modifier:{P.MEANS_SHIFT_TYPE}", body)
        self.assertNotIn("owner.modifier:", body)
        self.assertLess(body.index(P.MEANS_SHIFT_TYPE), body.index("max = 0.95"))

    def test_every_cause_has_a_multiplier(self):
        for cause in gen.CAUSES:
            self.assertIn(f"te_demog_mult_{cause} = {{", self.values)

    def test_enter_class_trees_on_the_rate_age_class(self):
        body = self.effects.split("te_demog_enter_class = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("local_var:te_dg_acls <=", body)
        self.assertNotIn("te_dg_cls", body)
        self.assertNotIn("te_dg_mig_add_", body)
        for sex in "fm":
            self.assertEqual(body.count(f"name = te_dg_mig_gain_{sex}\n"), len(P.MIGRANT_CLASSES))
            self.assertEqual(body.count(f"name = te_dg_mig_frac_{sex}\n"), len(P.MIGRANT_CLASSES))

    def _cause(self, cause):
        return self.values.split(f"te_demog_mult_{cause} = {{", 1)[1].split("\n}\n", 1)[0]

    def test_means_read_the_types_not_techs_or_laws(self):
        body = self.values.split("te_demog_means = {", 1)[1].split("\n}\n", 1)[0]
        self.assertNotIn("has_technology_researched", body)
        self.assertNotIn("has_law", body)
        # the tier is clamped inside its own block, before literacy multiplies it
        tier = body.split("value = {", 1)[1].split("}", 1)[0]
        self.assertIn(f"value = modifier:{P.CONTRACEPTION_TYPE}", tier)
        self.assertIn(f"add = {gen.lit(P.TRADITIONAL_MEANS)}", tier)
        self.assertIn("min = 0", tier)
        self.assertIn("max = 1", tier)
        self.assertLess(body.index("multiply = { value = var:te_dg_lit"), body.index(f"modifier:{P.MEANS_SHIFT_TYPE}"))

    def test_causes_read_the_types_not_the_owners_techs_or_laws(self):
        for cause in gen.CAUSES:
            body = self._cause(cause)
            self.assertNotIn("has_technology_researched", body, cause)
            self.assertNotIn("has_law", body, cause)
            self.assertNotIn("institution = institution_health_system", body, cause)
            self.assertNotIn("institution = institution_workplace_safety", body, cause)

    def test_medicine_reads_access_and_the_causes_treatment(self):
        for cause in P.MEDICINE_CAUSES:
            body = self._cause(cause)
            self.assertIn(f"value = modifier:{P.ACCESS_TYPE}", body, cause)
            self.assertIn(f"value = modifier:{P.TREATMENT_TYPE[cause]}", body, cause)
        for cause in set(gen.CAUSES) - set(P.MEDICINE_CAUSES):
            self.assertNotIn(P.ACCESS_TYPE, self._cause(cause), cause)

    def test_every_type_is_read_in_state_scope(self):
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertIn(f"modifier:{name}", self.values, name)
            self.assertNotIn(f"owner.modifier:{name}", self.values, name)

    def test_replay_values_are_one_sequential_block(self):
        self.assertNotIn("te_demog_dbg_unit", self.values)
        share = "multiply = var:te_dg_scale multiply = 1000 divide = { value = var:te_dg_people min = 1 }"
        for s in "fm":
            for k in range(P.RING_YEARS):
                self.assertIn(f"te_demog_dbg_{s}{k} = {{ value = 0 if = {{ limit = {{ has_variable = te_dg_{s}{k} }} "
                              f"value = var:te_dg_{s}{k} {share} }} }}", self.values)
            self.assertIn(f"te_demog_dbg_pool_{s} = {{ value = 0 if = {{ limit = {{ has_variable = te_dg_p{s} }} "
                          f"value = var:te_dg_p{s} {share} }} }}", self.values)

    def test_normalize_slots_touches_every_slot_in_two_steps(self):
        body = self.effects.split("te_demog_normalize_slots = {", 1)[1].split("\n}\n", 1)[0]
        for s in "fm":
            for k in range(P.RING_YEARS):
                name = f"te_dg_{s}{k}"
                self.assertIn(f"limit = {{ has_variable = {name} }}", body)
                self.assertEqual(body.count(f"change_variable = {{ name = {name} multiply = local_var:te_dg_norm_e5 }}"), 1)
                self.assertEqual(body.count(f"change_variable = {{ name = {name} divide = 100000 }}"), 1)
                self.assertLess(body.index(f"name = {name} multiply"), body.index(f"name = {name} divide"))

    def test_normalize_bands_covers_bands_classes_and_war_sums(self):
        body = self.effects.split("te_demog_normalize_bands = {", 1)[1].split("\n}\n", 1)[0]
        names = [f"te_dg_b{s}{b}" for b in range(P.BANDS) for s in "fm"]
        names += [f"te_dg_c{s}{c}" for c in range(len(P.MIGRANT_CLASSES)) for s in "fm"]
        names += ["te_dg_f1840", "te_dg_m1840"]
        for name in names:
            self.assertEqual(body.count(f"change_variable = {{ name = {name} multiply = local_var:te_dg_norm_e5 }}"), 1, name)
            self.assertEqual(body.count(f"change_variable = {{ name = {name} divide = 100000 }}"), 1, name)
        self.assertEqual(body.count("change_variable"), 2 * len(names))

    def test_maternal_comment_says_it_is_a_rate(self):
        head = self.values.split("te_demog_mult_maternal = {", 1)[0].rsplit("\n\n", 1)[-1]
        self.assertIn("maternal deaths per 100,000 births", head)

    def test_phase2_constants_match_the_params(self):
        for name, value in (("on_top_scale_min", P.ON_TOP_SCALE_MIN), ("on_top_scale_max", P.ON_TOP_SCALE_MAX),
                            ("rate_total_min", P.RATE_TOTAL_MIN),
                            ("rate_term_max", P.RATE_TERM_MAX),
                            ("literacy_birth_penalty", P.LITERACY_BIRTH_PENALTY)):
            self.assertIn(f"te_demog_k_{name} = {{ value = {gen.lit(value)} }}", self.values, name)


class TestEngineRateTerms(unittest.TestCase):
    """The expected births and deaths the migration residual is measured against: each pop's curves x the
    engine's own multiplier for it (docs/testing/demographics-growth-probe-results-2026-10-09.md)."""

    @classmethod
    def setUpClass(cls):
        values = gen.plan_outputs()[gen.VALUES]
        cls.birth = values.split("te_demog_pop_birth_mult = {", 1)[1].split("\n}\n", 1)[0]
        cls.death = values.split("te_demog_pop_death_mult = {", 1)[1].split("\n}\n", 1)[0]
        cls.registered = gen.registered_modifier_types(ROOT)

    def test_only_registered_modifier_types_are_read(self):
        """An unregistered key (modifiers.log lists ~1,100 mortality keys, 72 are registered) reads as 'none'
        on every pop: the growth probe's v3 and v4 runs flooded debug.log that way."""
        for body in (self.birth, self.death):
            read = set(re.findall(r"modifier:(\w+)", body))
            self.assertTrue(read)
            self.assertEqual(sorted(read - self.registered), [])

    def test_births_take_the_literacy_penalty_and_starvation(self):
        literacy = gen.static_modifier(ROOT, "literacy_penalty")["state_birth_rate_mult"]
        self.assertEqual(literacy, -0.1)   # the mod's REPLACE:literacy_penalty, as vanilla's
        self.assertIn(f"add = {{ value = literacy_rate multiply = {gen.lit(literacy)} }}", self.birth)
        self.assertIn("add = state.modifier:state_birth_rate_mult", self.birth)
        self.assertRegex(self.birth, r"is_in_severe_starvation = yes \}\s*add = -0\.9")
        self.assertNotIn("malnourishment", self.birth)   # the mod's own static modifier; nothing applies it

    def test_each_multiplier_is_floored_per_pop(self):
        for body in (self.birth, self.death):
            self.assertTrue(body.rstrip().endswith("min = 0"))

    def test_mild_starvation_scales_with_food_security(self):
        """starvation_penalty x (0.4 - food security) x 2.5, at most 0.5 (vanilla's comment), read in 0.05 steps."""
        buckets = gen._starvation_buckets()
        self.assertEqual([round(lo, 2) for lo, _ in buckets], [0.35, 0.3, 0.25, 0.2])
        self.assertEqual([round(s, 4) for _, s in buckets], [0.0625, 0.1875, 0.3125, 0.4375])
        mild = gen.static_modifier(ROOT, "starvation_penalty")
        self.assertIn(f"food_security >= 0.35 }} add = {gen.lit(mild['state_mortality_mult'] * 0.0625)} }}", self.death)

    def test_working_conditions_reach_the_mods_construction_sector(self):
        """REPLACE:bg_construction re-parents construction under heavy industry, so its laborers take heavy
        industry's working_conditions (0.1) as well as their own group's reads."""
        laborers = self.death.split("is_pop_type = laborers }", 1)[1].split("is_pop_type = machinists }", 1)[0]
        heavy = re.search(r"limit = \{ workplace = \{ OR = \{ is_building_group = bg_heavy_industry ([^}]*)\} \} \}"
                          r"(.*?)\n\t*\}", laborers, re.S)
        self.assertIsNotNone(heavy)
        self.assertIn("is_building_group = bg_construction", heavy.group(1))
        self.assertIn("add = 0.1", heavy.group(2))
        mining = re.search(r"limit = \{ workplace = \{ (?:OR = \{ )?is_building_group = bg_mining\b.*?\n(.*?)\n\t*\}", laborers, re.S)
        self.assertIn("add = 0.1", mining.group(1))

    def test_every_working_conditions_row_is_applied(self):
        rows = gen.static_modifier(ROOT, "working_conditions")
        self.assertEqual(len(rows), 31)
        for key, value in rows.items():
            group, ptype = re.fullmatch(r"building_group_(bg_\w+?)_(laborers|machinists|engineers|slaves)_mortality_mult",
                                        key).groups()
            branch = self.death.split(f"is_pop_type = {ptype} }}", 1)[1].split("is_pop_type = ", 1)[0]
            gate = re.search(rf"limit = \{{ workplace = \{{ (?:OR = \{{ )?is_building_group = {group}\b.*?\n(.*?)\n\t*\}}",
                             branch, re.S)
            self.assertIsNotNone(gate, key)
            self.assertIn(f"add = {gen.lit(value)}", gate.group(1), key)

    def test_class_and_workplace_reads(self):
        laborers = self.death.split("is_pop_type = laborers }", 1)[1].split("is_pop_type = machinists }", 1)[0]
        self.assertIn("add = state.modifier:state_laborers_mortality_mult", laborers)       # child labor laws
        self.assertIn("add = workplace.modifier:building_laborers_mortality_mult", laborers)  # production methods
        self.assertIn("exists = workplace", laborers)
        self.assertNotIn("state_mortality_turmoil_mult", self.death)   # scaling unknown, measured about 0
        self.assertNotIn("state_mortality_wealth_mult", self.death)
