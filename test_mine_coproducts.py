"""The co-product mines (#1419): each of gen_mine_coproducts.MINES runs its own copy of
its family's equipment groups, with the family's good split across several goods by
value, and the copies are current, value-neutral and wired like their templates."""

import os
import re
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import gen_mine_coproducts as gen  # noqa: E402
import pm_costs  # noqa: E402
import pm_emissions  # noqa: E402

u = gen.unwrap


def workforce(method):
    return u(u(u(method).get("building_modifiers", {})).get("workforce_scaled", {})) or {}


def goods(method, kind):
    """{good: Decimal quantity} of the method's workforce-scaled inputs or outputs."""
    result = {}
    for key, value in workforce(method).items():
        match = re.fullmatch(rf"goods_{kind}_(\w+)_add", key)
        if match:
            result[match[1]] = Decimal(u(value))
    return result


def as_list(value):
    value = u(value)
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


class MineCoproductsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = gen.load_state(ROOT)
        cls.methods = cls.state.mod_parsers["PMs"].data
        cls.groups = cls.state.mod_parsers["PM Groups"].data
        cls.buildings = cls.state.mod_parsers["Buildings"].data
        cls.prices = pm_costs.goods_from_parsed(cls.state.mod_parsers["Goods"].data)
        cls.plans = gen.plan_clones(cls.state, ROOT)

    def test_generation_is_current(self):
        self.assertEqual(gen.regenerate(self.state, root=ROOT, dry_run=True), [],
                         "run python3 scripts/generators/gen_mine_coproducts.py, then gen_carbon_capture_pms.py")

    def test_shares_are_whole_and_led_by_the_largest(self):
        for mine in gen.MINES:
            with self.subTest(mine=mine.building):
                shares = [Decimal(share) for _, share in mine.shares]
                self.assertEqual(sum(shares), 1)
                self.assertEqual(shares[0], max(shares))
                self.assertTrue(all(share > 0 for share in shares))
                self.assertEqual(len({good for good, _ in mine.shares}), len(mine.shares))
                for good, _ in mine.shares:
                    self.assertIn(good, self.prices)

    def test_copies_keep_their_templates_value_inputs_and_gates(self):
        for mine, template_good, mapping, _groups in self.plans:
            for template, name in mapping.items():
                original, copy = self.methods[template], self.methods[name]
                with self.subTest(method=name):
                    netted = pm_emissions.netted_fuel(template, original)
                    inputs = goods(original, "input")
                    for fuel, burn in netted.items():
                        inputs[fuel] = inputs.get(fuel, 0) + burn
                    self.assertEqual(goods(copy, "input"), inputs)
                    gross = goods(original, "output").get(template_good, Decimal(0)) + netted.get(template_good, 0)
                    value = gross * self.prices[template_good]
                    copied = sum(q * self.prices[g] for g, q in goods(copy, "output").items())
                    # rounding: under half a tenth of each good's price per line
                    tolerance = sum(Decimal("0.05") * self.prices[g] for g, _ in mine.shares)
                    self.assertLessEqual(abs(copied - value), tolerance)
                    self.assertLessEqual(set(goods(copy, "output")), {g for g, _ in mine.shares})
                    for key in ("unlocking_technologies", "disallowing_laws", "unlocking_laws", "texture"):
                        self.assertEqual(as_list(u(copy).get(key)), as_list(u(original).get(key)), key)
                    level = u(u(u(original).get("building_modifiers", {})).get("level_scaled", {}))
                    copied_level = u(u(u(copy).get("building_modifiers", {})).get("level_scaled", {}))
                    self.assertEqual(copied_level, level)
                    gate = [mapping.get(pm, pm) for pm in as_list(u(original).get("unlocking_production_methods"))]
                    self.assertEqual(as_list(u(copy).get("unlocking_production_methods")), gate)

    def test_each_mine_splits_its_output_as_configured(self):
        for mine, _good, mapping, _groups in self.plans:
            totals = {}
            for name in mapping.values():
                for good, quantity in goods(self.methods[name], "output").items():
                    totals[good] = totals.get(good, 0) + quantity * self.prices[good]
            whole = sum(totals.values())
            with self.subTest(mine=mine.building):
                for good, share in mine.shares:
                    self.assertAlmostEqual(float(totals.get(good, 0) / whole), float(share), delta=0.005)

    def test_copies_burn_what_their_templates_burn(self):
        factors, scale = gen.emission_factors(ROOT)
        for _mine, _good, mapping, _groups in self.plans:
            for template, name in mapping.items():
                original = self.methods[template]
                expected = pm_emissions.recipe_emissions(original, factors, scale,
                                                         pm_emissions.netted_fuel(template, original))
                state = u(u(u(self.methods[name]).get("state_modifiers", {})).get("workforce_scaled", {})) or {}
                line = state.get(pm_emissions.STATE_MODIFIER)
                with self.subTest(method=name):
                    self.assertEqual(Decimal(u(line)) if line else Decimal(0), expected)

    def test_buildings_run_their_copies_and_no_template(self):
        for mine, _good, mapping, template_groups in self.plans:
            listed = as_list(u(self.buildings[mine.building])["production_method_groups"])
            with self.subTest(mine=mine.building):
                for template, copy in template_groups.items():
                    self.assertIn(copy, listed)
                    self.assertNotIn(template, listed)
                    for pm in as_list(u(self.groups[copy])["production_methods"]):
                        # a copy, or a shared method that makes nothing
                        self.assertTrue(pm in mapping.values() or not goods(self.methods[pm], "output"), pm)
                        self.assertNotIn(pm, mapping)
                    for key in ("texture", "ai_selection"):
                        self.assertEqual(u(u(self.groups[copy]).get(key)), u(u(self.groups[template]).get(key)))

    def test_shared_methods_unlock_on_the_copies_too(self):
        for mine, _good, mapping, template_groups in self.plans:
            for group in as_list(u(self.buildings[mine.building])["production_method_groups"]):
                if group in template_groups.values() or group.startswith("pmg_carbon_capture_"):
                    continue
                for pm in as_list(u(self.groups[group])["production_methods"]):
                    gate = as_list(u(self.methods[pm]).get("unlocking_production_methods"))
                    for template in gate:
                        if template in mapping:
                            with self.subTest(mine=mine.building, method=pm, template=template):
                                self.assertIn(mapping[template], gate)

    def test_copies_are_named_after_their_templates(self):
        text = (ROOT / gen.LOC).read_text(encoding="utf-8-sig")
        for _mine, _good, mapping, template_groups in self.plans:
            for template, name in [*mapping.items(), *template_groups.items()]:
                with self.subTest(name=name):
                    self.assertRegex(text, rf'(?m)^ {re.escape(name)}:0 "\${re.escape(template)}\$"$')

    def test_the_tech_metals_family_is_only_a_template(self):
        # All four tech metals mines run copies, so no building runs the family's
        # output groups; they stay defined as the copies' source.
        for group in gen.CLONED_GROUPS:
            name = f"pmg_{group}_building_tech_metals_mine"
            self.assertIn(name, self.groups)
            for building, value in self.buildings.items():
                with self.subTest(building=building, group=name):
                    self.assertNotIn(name, as_list(u(value).get("production_method_groups")))

    def test_generated_files_have_one_bom(self):
        for relative in (gen.METHODS, gen.GROUPS):
            data = (ROOT / relative).read_bytes()
            with self.subTest(path=str(relative)):
                self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(data[3:].startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    os.chdir(ROOT)
    unittest.main()
