"""scripts/generators/gen_demographics.py: the committed script is a fresh generation, and its shape."""

import re
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts"))

import gen_demographics as gen  # noqa: E402
import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_regions as R  # noqa: E402
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

    def test_no_law_term_is_generated(self):
        """Since 2026-10-17 the laws carry their census and Wealth Concentration terms as modifier lines, so the
        generated values read modifier:, never has_law (the land term is hand-written in te_demog_values.txt;
        test_demographics_modifiers pins the lines on the laws)."""
        self.assertNotIn("te_demog_wc_land_term = {", self.values)
        for name, typ in (("te_demog_child_work", P.CHILD_WORK_TYPE), ("te_demog_pr_target_lm", P.LM_FARMS_TYPE),
                          # stage 3 (2026-10-19): the migrant profile's women at work and families' transport
                          ("te_demog_female_work_share", P.FEMALE_WORK_SHARE_TYPE),
                          ("te_demog_family_transport", P.FAMILY_MIGRATION_TYPE)):
            body = self.values.split(f"{name} = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertIn(f"modifier:{typ}", body, name)
            self.assertNotIn("has_law", body, name)
            self.assertNotIn("has_technology_researched", body, name)
        body = self.values.split("te_demog_female_work_share = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn(f"value = {gen.lit(P.FEMALE_WORK_SHARE_DEFAULT)}", body, "the base the laws' lines add to")

    def test_means_read_the_modifier(self):
        body = self.values.split("te_demog_means = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn(f"add = modifier:{P.MEANS_SHIFT_TYPE}", body)
        self.assertNotIn("owner.modifier:", body)
        # the cap after the shift: 1, a share's natural bound (owner, 2026-10-20; was 0.95)
        self.assertEqual(P.MEANS_CAP, 1.0)
        cap = re.findall(r"max = (\S+)", body.split(f"add = modifier:{P.MEANS_SHIFT_TYPE}", 1)[1])
        self.assertEqual(cap, [gen.lit(P.MEANS_CAP)])

    def test_every_cause_has_a_multiplier(self):
        for cause in gen.CAUSES:
            self.assertIn(f"te_demog_mult_{cause} = {{", self.values)

    def test_enter_class_trees_on_the_rate_age_class(self):
        body = self.effects.split("te_demog_enter_class = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("local_var:te_dg_acls <=", body)
        self.assertNotIn("te_dg_cls", body)
        self.assertNotIn("te_dg_mig_add_", body)
        for sex in "fm":
            # each class sets its gain and loss from the booking's rate (te_demog_migrant_rates, 2026-10-12)
            for kind in ("gain", "frac"):
                self.assertEqual(body.count(f"name = te_dg_mig_{kind}_{sex} value = {{ value = local_var:te_dg_mr_{sex}"),
                                 len(P.MIGRANT_CLASSES))
            self.assertEqual(body.count("add = local_var:te_dg_mig_flat"), 4 * len(P.MIGRANT_CLASSES))

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
        # every body the causes' figures come from: each factor, the medicine targets and the spread's rate (values),
        # and te_demog_cause_inputs_store (effects), which reads the plain types for the factors (review of Tasks 4-5)
        names = [f"te_demog_f_{cause}_{f}" for cause, factors in P.CAUSE_FACTORS.items() for f in factors]
        names += [f"te_demog_f_{cause}_medicine_target" for cause in P.MEDICINE_CAUSES]
        names += ["te_demog_access_target", "te_demog_medical_diffusion"]
        names += [f"te_demog_treatment_target_{cause}" for cause in P.MEDICINE_CAUSES]
        bodies = {name: self._value(name) for name in names}
        bodies["te_demog_cause_inputs_store"] = self.effects.split("te_demog_cause_inputs_store = {", 1)[1].split(
            "\n}\n", 1)[0]
        bodies.update({f"te_demog_mult_{cause}": self._cause(cause) for cause in gen.CAUSES})
        for name, body in bodies.items():
            with self.subTest(name):
                self.assertNotIn("has_technology_researched", body)
                self.assertNotIn("has_law", body)
                self.assertNotIn("institution = institution_health_system", body)
                self.assertNotIn("institution = institution_workplace_safety", body)
                self.assertNotIn("owner", body)

    def _value(self, name):
        return self.values.split(f"\n{name} = {{", 1)[1].split("\n}\n", 1)[0]

    def test_each_multiplier_is_the_product_of_its_factors(self):
        for cause, factors in P.CAUSE_FACTORS.items():
            lines = [line.strip() for line in self._cause(cause).strip().splitlines()]
            want = [f"value = te_demog_f_{cause}_{factors[0]}"]
            want += [f"multiply = te_demog_f_{cause}_{f}" for f in factors[1:]]
            if cause == "maternal":
                want.append(f"multiply = {P.MATERNAL_PER_100K_BIRTHS}")
            self.assertEqual(lines, want, cause)

    def test_factors_read_only_what_the_step_stored(self):
        # the hover multiplies to the row between steps only if no factor reads a live modifier, turmoil or crowding
        for cause, factors in P.CAUSE_FACTORS.items():
            for f in factors:
                body = self._value(f"te_demog_f_{cause}_{f}")
                with self.subTest(cause=cause, factor=f):
                    self.assertNotIn("modifier:", body)
                    self.assertNotIn("has_modifier", body)
                    self.assertIsNone(re.search(r"(?<![\w:])turmoil\b", body))
                    self.assertRegex(body, r"var:te_dg_(acc|trt_\w+|in_\w+)\b")
                    # the walk's te_dg_sol and te_dg_lit change at a walk without a step; the step's copies don't
                    self.assertIsNone(re.search(r"var:te_dg_(sol|lit)\b", body))

    def test_the_targets_read_the_types(self):
        self.assertIn(f"value = modifier:{P.ACCESS_TYPE}", self._value("te_demog_access_target"))
        self.assertIn(f"value = modifier:{P.DIFFUSION_TYPE}", self._value("te_demog_medical_diffusion"))
        for cause in P.MEDICINE_CAUSES:
            self.assertIn(f"value = modifier:{P.TREATMENT_TYPE[cause]}",
                          self._value(f"te_demog_treatment_target_{cause}"))

    def test_the_inputs_store_reads_each_plain_type(self):
        body = self.effects.split("te_demog_cause_inputs_store = {", 1)[1].split("\n}\n", 1)[0]
        for cause, types in P.MORTALITY_TYPES.items():
            for t in types:
                self.assertIn(f"add = modifier:{t}", body)
            self.assertIn(f"name = te_dg_in_{P.CAUSE_SHORT[cause]}", body)
        self.assertIn("value = turmoil", body)
        self.assertIn("var:migration_crowding_mult_applied", body)

    def test_every_type_is_read_in_state_scope(self):
        # medicine's types in the targets (values); the plain ones in te_demog_cause_inputs_store (effects), which
        # stores them for the factors (the Causes of Death plan)
        both = self.values + self.effects
        for name in P.DEMOG_MORTALITY_TYPES + (P.DIFFUSION_TYPE,):
            self.assertIn(f"modifier:{name}", both, name)
            self.assertNotIn(f"owner.modifier:{name}", both, name)

    def test_the_walk_sums_severe_starvation_under_full(self):
        """The Causes of Death section's split (Task 6): one Full-only severe-starvation test per pop, beside the walk's
        other Full-only sums. Its people count unconditionally; its deaths' severe term only where the engine doesn't
        floor the pop, and the term is the very ladder te_demog_pop_death_mult holds."""
        init = self.effects.split("te_demog_absorbed_walk_init = {", 1)[1].split("\n}\n", 1)[0]
        pop = self.effects.split("te_demog_absorbed_walk_pop = {", 1)[1].split("\n}\n", 1)[0]
        before_guard = init.split("te_demog_effects_run = yes", 1)[0]
        for name in ("te_dg_w_sev", "te_dg_w_sevd"):
            self.assertIn(f"set_local_variable = {{ name = {name} value = 0 }}", before_guard)
        guarded = pop.split("local_var:te_dg_w_rep > 0", 1)[1]
        self.assertEqual(pop.count("is_in_severe_starvation = yes"), 1)
        severe = guarded.split("is_in_severe_starvation = yes", 1)[1]
        self.assertIn("change_local_variable = { name = te_dg_w_sev add = total_size }", severe)
        floored = severe.split("local_var:te_dg_p_md > 0", 1)
        self.assertEqual(len(floored), 2, "the deaths sit inside the engine's floor test")
        self.assertNotIn("te_dg_w_sevd", floored[0])
        ladder = self.values.split("te_demog_pop_death_mult = {", 1)[1].split("\n}\n", 1)[0]
        ladder = ladder.split("limit = { is_in_severe_starvation = yes }", 1)[1].split("else_if = {\n\t\tlimit = { is_in_mild", 1)[0]
        want = [line.strip() for line in ladder.strip().splitlines() if line.strip() != "}"]
        got = [line.strip() for line in floored[1].split("value = 0", 1)[1].strip().splitlines()][:len(want)]
        self.assertEqual(got, want)
        self.assertNotIn("te_demog_pop_severe", self.values + self.effects, "no new per-pop script value")

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

    def test_normalize_bands_covers_bands_classes_and_pool_sums(self):
        body = self.effects.split("te_demog_normalize_bands = {", 1)[1].split("\n}\n", 1)[0]
        names = [f"te_dg_b{s}{b}" for b in range(P.BANDS) for s in "fm"]
        names += [f"te_dg_c{s}{c}" for c in range(len(P.MIGRANT_CLASSES)) for s in "fm"]
        names += ["te_dg_faw", "te_dg_fam"]   # the pool's sums (phase 2 step 4), which replaced the 18-40 sums
        for name in names:
            self.assertEqual(body.count(f"change_variable = {{ name = {name} multiply = local_var:te_dg_norm_e5 }}"), 1, name)
            self.assertEqual(body.count(f"change_variable = {{ name = {name} divide = 100000 }}"), 1, name)
        self.assertEqual(body.count("change_variable"), 2 * len(names))

    def test_maternal_comment_says_it_is_a_rate(self):
        head = self.values.split("te_demog_mult_maternal = {", 1)[0].rsplit("\n\n", 1)[-1]
        self.assertIn("maternal deaths per 100,000 births", head)

    def test_phase2_constants_match_the_params(self):
        for name, value in (("on_top_scale_min", P.ON_TOP_SCALE_MIN), ("on_top_factor_min", P.ON_TOP_FACTOR_MIN),
                            ("rate_total_floor", P.RATE_TOTAL_FLOOR), ("rate_bare_min", P.RATE_BARE_MIN),
                            ("window_start_weight", P.WINDOW_START_WEIGHT)):
            self.assertIn(f"te_demog_k_{name} = {{ value = {gen.lit(value)} }}", self.values, name)
        # owner, 2026-10-20: the scales and M have no ceiling, and the floor is the engine's own
        for gone in ("on_top_scale_max", "rate_term_max", "rate_total_min"):
            self.assertNotIn(f"te_demog_k_{gone} ", self.values, gone)

    def test_the_absorbed_terms_follow_the_engine(self):
        """Owner amendment A and B (2026-10-10): literacy's penalty from literacy_penalty, mild starvation's in the
        engine's steps and severe starvation's left out."""
        pop_b = self.values.split("te_demog_pop_absorbed_births = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn(f"value = literacy_rate\n\tmultiply = {gen.lit(P.LITERACY_BIRTH_PENALTY)}", pop_b)
        self.assertIn("is_in_severe_starvation = no", pop_b)
        self.assertNotIn("-0.9", pop_b)
        # the laws', techs' and institutions' lines are script-only (the engine-lines plan, 2026-10-11): no state or
        # class ladder is generated any more
        for gone in ("te_demog_absorbed_births = {", "te_demog_absorbed_deaths = {", "te_demog_absorbed_laborers_deaths = {"):
            self.assertNotIn(gone, self.values)


    def test_the_practices_values(self):
        """Late Marriage and Birth Spacing (the late-marriage plan, Task 7): the start ladders, erosions, seeds,
        targets and terms."""
        for p in P.PRACTICES:
            start = self.values.split(f"te_demog_pr_start_{p} = {{", 1)[1].split("\n}\n", 1)[0]
            # the state regions come after the strategic regions, so they win
            if "region = sr:" in start and "state_region = s:" in start:
                self.assertLess(start.rindex("region = sr:"), start.index("state_region = s:"))
            term = self.values.split(f"te_demog_pr_term_{p} = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertIn(f"limit = {{ has_variable = te_dg_pr_{p} }}", term)
            self.assertIn(f"multiply = {gen.lit(P.PRACTICE_CUT[p])}", term)
            self.assertIn(f"te_demog_pr_target_{p} = {{", self.values)
            seed = self.values.split(f"te_demog_pr_seed_{p} = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertIn(f"value = te_demog_pr_erosion_{p}", seed)
            self.assertIn(f"multiply = te_demog_pr_start_{p}", seed)
            self.assertIn(f"value = te_demog_pr_seed_{p}", self.values.split(f"te_demog_pr_target_{p} = {{", 1)[1])
            self.assertIn(f"multiply = te_demog_pr_term_{p}", self.values.split("te_demog_pr_terms = {", 1)[1])
        lm = self.values.split("te_demog_pr_target_lm = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn(f"add = {{ value = var:te_dg_agr_share multiply = modifier:{P.LM_FARMS_TYPE} }}", lm)
        erosion_lm = self.values.split("te_demog_pr_erosion_lm = {", 1)[1].split("\n}\n", 1)[0]
        self.assertNotIn("te_dg_acc", erosion_lm, "health care erodes Birth Spacing only")
        erosion_bs = self.values.split("te_demog_pr_erosion_bs = {", 1)[1].split("\n}\n", 1)[0]
        # the access medicine has reached above the base (#916's drifted te_dg_acc), not the law's modifier
        self.assertIn("value = var:te_dg_acc subtract = te_demog_k_base_access", erosion_bs)
        self.assertNotIn(f"modifier:{P.ACCESS_TYPE}", erosion_bs)
        self.assertIn(f"te_demog_k_practice_rate = {{ value = {gen.lit(P.PRACTICE_RATE)} }}", self.values)

    def test_late_marriages_inheritance_reads_the_states_line(self):
        """Stop B, M1 read the inheritance conditions inside an owner = { } block, since te_inh_has_undivided_farms
        reads a country link. Since 2026-10-17 Primogeniture and Undivided Farm Succession carry a state type, which
        reaches the state from the country: the target reads it in state scope, with no owner link and no law test."""
        target = self.values.split("te_demog_pr_target_lm = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn(f"multiply = modifier:{P.LM_FARMS_TYPE}", target)
        for gone in ("owner", "has_law", "te_inh_has_undivided_farms"):
            self.assertNotIn(gone, target)

    def test_the_start_ladders_give_every_state_its_start(self):
        """Each ladder, read in order as the engine reads it (a later if wins), gives every land state region the
        start demographics_model.practice_start gives it, with the entries that change nothing left out."""
        import demographics_model as M
        import demographics_regions as R
        for p in P.PRACTICES:
            ladder = self.values.split(f"te_demog_pr_start_{p} = {{", 1)[1].split("\n}\n", 1)[0]
            blocks = []
            for line in ladder.splitlines():
                line = line.strip()
                named = re.fullmatch(r"(?:region = sr:|state_region = s:)(\w+)", line)
                value = re.fullmatch(r"value = ([\d.]+)", line)
                if line == "if = {":
                    blocks.append([set(), None])
                elif named:
                    blocks[-1][0].add(named.group(1))
                elif blocks and value:
                    blocks[-1][1] = float(value.group(1))
            for state, region in R.strategic_region_of().items():
                got = 0.0
                for names, v in blocks:
                    if state in names or region in names:
                        got = v
                self.assertAlmostEqual(got, M.practice_start(p, state, region), msg=f"{p} {state}")

    def test_the_practice_loops_call_every_practice(self):
        for name in ("seed", "step", "country_init", "country_add", "country_store"):
            body = self.effects.split(f"te_demog_practices_{name} = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertEqual(re.findall(rf"te_demog_practice_{name} = \{{ P = (\w+) \}}", body), list(P.PRACTICES))

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
        self.assertIn("is_in_severe_starvation = yes }", self.birth)
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

    def test_severe_starvation_scales_with_food_security(self):
        """The famine probe (2026-10-11): the engine applies severe_starvation_penalty x the pop's starvation value,
        clamp((0.4 - food security) x 2.5, 0, 1), as it does the mild penalty, not in full. The walk reads it in 0.05
        steps from the severe threshold down to 0, at each step's middle (the probe's table)."""
        buckets = gen._starvation_buckets(severe=True)
        self.assertEqual([round(lo, 2) for lo, _ in buckets], [0.15, 0.1, 0.05, 0.0])
        self.assertEqual([round(s, 4) for _, s in buckets], [0.5625, 0.6875, 0.8125, 0.9375])
        self.assertTrue(all(0 < s <= P.STARVATION_VALUE_MAX for _, s in buckets))
        severe = gen.static_modifier(ROOT, "severe_starvation_penalty")
        self.assertEqual(severe, {"state_birth_rate_mult": P.STARVATION_SEVERE["births"],
                                  "state_mortality_mult": P.STARVATION_SEVERE["deaths"]})
        for body, want in ((self.birth, ["-0.50625", "-0.61875", "-0.73125", "-0.84375"]),
                           (self.death, ["0.5625", "0.6875", "0.8125", "0.9375"])):
            branch = body.split("limit = { is_in_severe_starvation = yes }", 1)[1].split("is_in_mild_starvation", 1)[0]
            self.assertEqual(re.findall(r"food_security >= ([0-9.]+)", branch), ["0.15", "0.1", "0.05"])
            self.assertEqual(re.findall(r"add = (-?[0-9.]+)", branch), want)
            self.assertIn(f"else = {{ add = {want[-1]} }}", branch)
            self.assertNotRegex(branch, r"add = -?(0\.9|1)\s")   # never flat
    def test_working_conditions_reach_the_mods_construction_sector(self):
        """REPLACE:bg_construction re-parents construction under heavy industry, so its laborers read heavy industry's
        group keys, which carry its working_conditions (0.1), as well as their own group's."""
        laborers = self.death.split("is_pop_type = laborers }", 1)[1].split("is_pop_type = machinists }", 1)[0]
        heavy = re.search(r"limit = \{ workplace = \{ OR = \{ is_building_group = bg_heavy_industry ([^}]*)\} \} \}"
                          r"(.*?)\n\t*\}", laborers, re.S)
        self.assertIsNotNone(heavy)
        self.assertIn("is_building_group = bg_construction", heavy.group(1))
        self.assertIn("add = workplace.modifier:building_group_bg_heavy_industry_laborers_mortality_mult", heavy.group(2))
        mining = re.search(r"limit = \{ workplace = \{ (?:OR = \{ )?is_building_group = bg_mining\b.*?\n(.*?)\n\t*\}", laborers, re.S)
        self.assertIn("add = workplace.modifier:building_group_bg_mining_laborers_mortality_mult", mining.group(1))

    def test_every_working_conditions_row_is_read_not_added(self):
        """The self-check working_conditions_read (2026-10-17): a mine's read of its laborers' key holds the table's
        0.1, scaled by the building's building_working_conditions_mult (the growth probe's 1949 capital read 0 under
        Workplace Safety at five). So the walk reads each row through its workplace's group key and adds no constant:
        until then it added the table on top and counted working conditions twice."""
        rows = gen.static_modifier(ROOT, "working_conditions")
        self.assertEqual(len(rows), 31)
        for key in rows:
            group, ptype = re.fullmatch(r"building_group_(bg_\w+?)_(laborers|machinists|engineers|slaves)_mortality_mult",
                                        key).groups()
            branch = self.death.split(f"is_pop_type = {ptype} }}", 1)[1].split("is_pop_type = ", 1)[0]
            gate = re.search(rf"limit = \{{ workplace = \{{ (?:OR = \{{ )?is_building_group = {group}\b.*?\n(.*?)\n\t*\}}",
                             branch, re.S)
            self.assertIsNotNone(gate, key)
            self.assertIn(f"add = workplace.modifier:{key}", gate.group(1), key)
        # no literal in any workplace group's gate: every line there is a read
        gates = re.findall(r"limit = \{ workplace = \{ [^\n]*\n(.*?)\n\t*\}", self.death, re.S)
        self.assertGreater(len(gates), 30)
        for body in gates:
            self.assertNotRegex(body, r"add = -?[0-9.]+\s*$")
            self.assertNotRegex(body, r"add = -?[0-9.]+\n")

    def test_the_self_check_reads_the_tables_mining_line(self):
        """working_conditions_read's expected read is the table's bg_mining laborers line at the building's scale."""
        values = (ROOT / "common" / "script_values" / "te_debug_demog_values.txt").read_text(encoding="utf-8-sig")
        table = gen.static_modifier(ROOT, "working_conditions")["building_group_bg_mining_laborers_mortality_mult"]
        self.assertIn(f"te_debug_demog_wc_table_mining_laborers = {{ value = {gen.lit(table)} }}", values)
        self.assertIn("te_debug_demog_wc_mine_read = { value = modifier:building_group_bg_mining_laborers_mortality_mult }",
                      values)
        scale = values.split("te_debug_demog_wc_mine_scale = {", 1)[1].split("\n}", 1)[0]
        self.assertIn("add = modifier:building_working_conditions_mult", scale)
        self.assertIn("min = 0", scale)

    def test_class_and_workplace_reads(self):
        laborers = self.death.split("is_pop_type = laborers }", 1)[1].split("is_pop_type = machinists }", 1)[0]
        self.assertIn("add = state.modifier:state_laborers_mortality_mult", laborers)       # child labor laws
        self.assertIn("add = workplace.modifier:building_laborers_mortality_mult", laborers)  # production methods
        self.assertIn("exists = workplace", laborers)
        self.assertNotIn("state_mortality_turmoil_mult", self.death)   # scaling unknown, measured about 0
        # the wealth line x the pop's own wealth (probe P6; 2026-10-20), once, inside the floor at 0
        line = "add = { value = state.modifier:state_mortality_wealth_mult multiply = wealth }"
        self.assertEqual(self.death.count("state_mortality_wealth_mult"), 1)
        self.assertIn(line, self.death)
        self.assertLess(self.death.index(line), self.death.rindex("min = 0"))


class TestPhase2Generated(unittest.TestCase):
    """Phase 2 step 1 (the interfaces plan, Task 3)."""

    @classmethod
    def setUpClass(cls):
        cls.effects = gen.render_effects()
        cls.values = gen.render_values(ROOT)

    def test_the_birth_line_is_todays_while_the_schedules_are_one(self):
        body = re.search(r"^te_demog_slot_births = \{\n(.*?)^\}", self.effects, re.M | re.S).group(1)
        self.assertIn("value = { value = local_var:te_dg_f multiply = local_var:te_dg_asfr divide = 100000 "
                      "multiply = local_var:te_dg_tfr }", body)
        self.assertNotIn("te_dg_asfr_un", self.effects)

    def test_two_schedules_write_two_terms(self):
        other = {15: 10000, 20: 30000, 25: 30000, 30: 20000, 35: 7000, 40: 2500, 45: 500}
        with unittest.mock.patch.object(P, "ASFR_UNPLANNED_SHAPE", other):
            text = gen.render_effects()
        self.assertIn("te_dg_asfr_un", text)
        self.assertIn("multiply = local_var:te_dg_sh_pl", text)

    def test_the_bands_are_the_tables(self):
        for a in P.BIO_BANDS:
            self.assertIn(f"value = {{ value = {gen.lit(M.band_value(P.CAPACITY, a))} multiply = local_var:te_dg_wk_capm "
                          "max = 1 }", self.effects)
        self.assertRegex(self.effects, r"te_demog_enter_cal_band = \{")
        self.assertRegex(self.effects, r"te_demog_enter_bio_band = \{")

    def test_the_life_table_ends_with_the_threshold(self):
        lt = re.search(r"^te_demog_life_table = \{\n(.*?)^\}", self.effects, re.M | re.S).group(1)
        self.assertTrue(lt.rstrip().endswith("te_demog_old_age_pass = yes"))
        for start, _w in P.GROUPS:
            stored = f"name = te_dg_oal{start}f" in lt
            self.assertEqual(stored, start >= P.OLD_AGE_FROM, start)

    def test_the_constants(self):
        self.assertNotIn("te_demog_k_workforce_scale", self.values, "the rates are in the game's units (2026-10-20)")
        for name, v in (("men_rate", P.MEN_RATE), ("rate_max", P.RATE_MAX),
                        ("pension_age_standard", P.PENSION_AGE["standard"]),
                        ("health_need_1836", P.HEALTH_NEED_1836)):
            self.assertIn(f"te_demog_k_{name} = {{ value = {gen.lit(v)} }}", self.values)


class TestCalibrationStep3Generated(unittest.TestCase):
    """Calibration step 3 (docs/superpowers/archive/specs/2026-10-12-demographics-calibration-step3-design.md; owner calls 1-2,
    2026-10-12): the country-scope absorbed lines and the malaria factor's inputs."""

    @classmethod
    def setUpClass(cls):
        out = gen.plan_outputs()
        cls.values, cls.effects = out[gen.VALUES], out[gen.EFFECTS]

    def _value(self, name):
        return self.values.split(f"\n{name} = {{", 1)[1].split("\n}\n", 1)[0]

    def test_the_absorbed_deaths_add_the_owners_read_where_the_walk_reads_the_workplaces(self):
        absorbed = self._value("te_demog_pop_country_absorbed_deaths")
        walk = self._value("te_demog_pop_country_line_walk_read")
        death = self._value("te_demog_pop_death_mult")
        for group in P.COUNTRY_ABSORBED_GROUPS:
            key = f"building_group_{group}_mortality_mult"
            self.assertIn(f"add = owner.modifier:{key}", absorbed)
            self.assertIn(f"add = workplace.modifier:{key}", walk)
            gate = absorbed.split(f"add = owner.modifier:{key}", 1)[0].rsplit("limit = ", 1)[1]
            self.assertIn(gate.strip(), death, "the same workplace gate the walk adds the key under")
        self.assertEqual(absorbed.replace("owner.", "workplace."), walk, "one gate, two readers")
        self.assertIn("add = te_demog_pop_country_absorbed_deaths", self._value("te_demog_pop_absorbed_deaths"))
        self.assertNotIn("te_demog_pop_country_absorbed_deaths", self._value("te_demog_pop_absorbed_births"))

    def test_the_listed_malaria_regions_are_the_maps(self):
        listed, pending = {}, []
        for line in self._value("te_demog_malaria_level_listed").splitlines():
            m = re.search(r"state_region = s:(STATE_\w+)", line)
            if m:
                pending.append(m.group(1))
            m = re.search(r"^\t\tadd = (\d)$", line)
            if m:
                listed.update(dict.fromkeys(pending, int(m.group(1))))
                pending = []
        self.assertEqual(listed, R.malaria_levels())
        self.assertEqual(sum(1 for v in listed.values() if v == 2), 26)

    def test_the_level_reads_the_trait_and_the_store_its_control(self):
        level = self._value("te_demog_malaria_level")
        for trait in P.MALARIA_TRAITS:
            self.assertIn(f"has_state_trait = {trait}", level)
        self.assertNotIn("owner", level)
        self.assertNotIn("te_demog_malaria_level_listed", level, "the fallback is off (P.MALARIA_READS_REGION_LIST)")
        store = self.effects.split("te_demog_cause_inputs_store = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("set_variable = { name = te_dg_in_mal value = te_demog_malaria_level }", store)
        self.assertIn(f"value = modifier:{P.MALARIA_CONTROL_TYPE} min = 0 max = 1", store)

    def test_the_famine_reserves_fallback_reads_the_subsistence_farm(self):
        """famine_reserves_absorbed's fallback for an owner's read of 0: the farm's own read, on subsistence farms only
        (no company owns one, so no building-scope line is absorbed with it)."""
        with unittest.mock.patch.object(P, "COUNTRY_ABSORBED_FROM_FARM", True):
            values = gen.plan_outputs()[gen.VALUES]
        body = values.split("\nte_demog_pop_country_absorbed_deaths = {", 1)[1].split("\n}\n", 1)[0]
        self.assertNotIn("owner.", body)
        self.assertIn("limit = { workplace = { is_building_group = bg_subsistence_agriculture } }", body)
        self.assertIn("add = workplace.modifier:building_group_bg_agriculture_mortality_mult", body)
        self.assertNotIn("bg_staple_crops", body)

    def test_the_fallback_reads_the_list(self):
        with unittest.mock.patch.object(P, "MALARIA_READS_REGION_LIST", True):
            values = gen.plan_outputs()[gen.VALUES]
        level = values.split("\nte_demog_malaria_level = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("value = te_demog_malaria_level_listed", level)
        self.assertNotIn("has_state_trait", level)


if __name__ == "__main__":
    unittest.main()
