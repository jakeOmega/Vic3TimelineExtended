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
        self.assertIn("add = owner.modifier:country_fertility_means_add", body)
        self.assertLess(body.index("country_fertility_means_add"), body.index("max = "))

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
