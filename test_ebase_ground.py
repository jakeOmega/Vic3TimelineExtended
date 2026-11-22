"""The Extraplanetary Base's ground types, its shared basket and the month's rules
(docs/superpowers/specs/2026-11-05-extraplanetary-base-ground-types-design.md).

``scripts/generators/ebase_ground.py`` is the reference the generated script must
match: each site's type, each type's mix (§ 6), the basket of the four mining
methods (§ 7), and the month (§ 8.2 to § 8.5) as a Python model.
"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import ebase_ground as eg  # noqa: E402
import gen_solar_sites as gss  # noqa: E402

# § 6.2's table, the figures the loc states: each type's mix, rounded to the whole
# percent, in the goods' order (iron, tech_metals, gold, copper, lead, sulfur, glass).
ROUNDED_MIX = {
    "mixed": (0, 0, 0, 0, 0, 0, 0),
    "metallic": (12, 2, 30, 12, -7, -72, -91),
    "rocky": (26, -3, -51, -17, -17, 7, 36),
    "carbonaceous": (-17, -7, -33, -7, -7, 107, 117),
    "sulfurous": (-16, -11, -37, 5, 5, 320, 26),
    "hydrocarbon": (-25, -15, -50, -20, -20, 80, 249),
    "icy": (0, -5, -40, -10, -10, 61, 81),
}


class GroundTypes(unittest.TestCase):
    """§ 6: a site is its type and its grade, and every type's mix averages to zero
    over the basket, so the grade alone carries how much a site yields."""

    def test_every_place_has_a_type(self):
        self.assertEqual(set(eg.GROUND), {"near_earth"} | {s.key for s in gss.SITES})
        for place, type_ in eg.GROUND.items():
            with self.subTest(place=place):
                self.assertIn(type_, eg.TYPES)

    def test_places_are_near_earth_then_the_sites_in_index_order(self):
        self.assertEqual(eg.PLACES[0], "near_earth")
        self.assertEqual(eg.PLACES[1:], tuple(s.key for s in sorted(gss.SITES, key=lambda s: s.index)))

    def test_each_mix_averages_to_zero(self):
        shares = eg.shares(eg.BASKET)
        for t in eg.TYPES:
            with self.subTest(type=t):
                self.assertLess(abs(sum(shares[g] * eg.mix(t)[g] for g in eg.GOODS)), 1e-12)

    def test_every_derived_grade_is_the_site_s(self):
        shares = eg.shares(eg.BASKET)
        for p in eg.PLACES:
            with self.subTest(place=p):
                derived = sum(shares[g] * eg.score(p, g) for g in eg.GOODS)
                self.assertAlmostEqual(derived, eg.grade(p), delta=1e-12)

    def test_grades_are_the_sites_ebase_grades(self):
        self.assertEqual(eg.grade("near_earth"), 0)
        for s in gss.SITES:
            with self.subTest(site=s.key):
                self.assertAlmostEqual(eg.grade(s.key), s.ebase_grade / 100, delta=1e-12)

    def test_rounded_mixes_match_the_spec(self):
        self.assertEqual(set(ROUNDED_MIX), set(eg.TYPES))
        for t, figures in ROUNDED_MIX.items():
            for g, figure in zip(eg.GOODS, figures):
                with self.subTest(type=t, good=g):
                    self.assertEqual(round(100 * eg.mix(t)[g]), figure)

    def test_base_prices_match_the_goods_files(self):
        import pm_costs  # prices exactly as test_deep_sea_rebalance._Data reads them

        prices = pm_costs.load_goods()
        self.assertEqual(eg.BASE_PRICE, {g: prices[g] for g in eg.GOODS})
        for g in eg.GOODS:
            with self.subTest(good=g):
                self.assertEqual(eg.good_base_price(g), prices[g])

    def test_mixed_is_the_basket(self):
        self.assertEqual(eg.mix("mixed"), {g: 0.0 for g in eg.GOODS})


class Basket(unittest.TestCase):
    """§ 7: the four mining methods share one basket, the same seven goods in the same
    shares of output value at base prices, so a site's mix means the same under each
    and cancels at base prices for every one."""

    MINING = ("pm_regolith_processing", "pm_space_mine", "pm_space_colony_mining", "pm_self_replicating_miners")

    def setUp(self):
        self.methods = eg.base_methods()
        self.mining = eg.mining_methods()

    def test_mining_methods_are_those_within_the_seven_goods(self):
        self.assertEqual(list(self.mining), [pm for pm, m in self.methods.items()
                                             if set(m.outputs) <= set(eg.GOODS)])

    def test_method_goods_are_the_seven_and_the_mining_inputs(self):
        goods = eg.method_goods()
        self.assertEqual(goods[:len(eg.GOODS)], eg.GOODS)
        inputs = {g for m in self.mining.values() for g in m.inputs}
        self.assertEqual(set(goods), set(eg.GOODS) | inputs)
        for g in goods:
            with self.subTest(good=g):
                self.assertGreater(eg.good_base_price(g), 0)

    @staticmethod
    def _value(goods):
        return sum(qty * eg.good_base_price(g) for g, qty in goods.items())

    def test_reads_every_method_of_the_base_group(self):
        for pm in self.MINING:
            with self.subTest(pm=pm):
                self.assertIn(pm, self.mining)
        for pm, m in self.methods.items():
            with self.subTest(pm=pm):
                self.assertTrue(m.outputs)
                self.assertIn("launch_capacity", m.inputs)

    def test_asteroid_mine_is_the_basket(self):
        self.assertEqual(self.methods["pm_space_mine"].outputs, eg.BASKET)

    def test_mining_methods_share_the_basket(self):
        basket = eg.shares(eg.BASKET)
        for pm, m in self.mining.items():
            shares = eg.shares(m.outputs)
            self.assertEqual(set(shares), set(eg.GOODS), pm)
            for g in eg.GOODS:
                with self.subTest(pm=pm, good=g):
                    self.assertAlmostEqual(shares[g], basket[g], delta=0.0001)

    def test_every_type_earns_base_profit_at_base_prices(self):
        for pm, m in self.mining.items():
            base = self._value(m.outputs) - self._value(m.inputs)
            for t in eg.TYPES:
                with self.subTest(pm=pm, type=t):
                    typed = sum(qty * eg.good_base_price(g) * (1 + eg.mix(t)[g])
                                for g, qty in m.outputs.items()) - self._value(m.inputs)
                    self.assertLessEqual(abs(typed - base), 0.001 * abs(base))

    def test_regolith_output_value_is_unchanged(self):
        self.assertAlmostEqual(self._value(self.methods["pm_regolith_processing"].outputs), 16600, delta=0.005)

    def test_regolith_every_type_within_fifty_pence(self):
        """§ 7: with two decimals every type earns £1,600 a level at grade 0 and base
        prices to within £0.50."""
        m = self.methods["pm_regolith_processing"]
        for t in eg.TYPES:
            with self.subTest(type=t):
                typed = sum(qty * eg.good_base_price(g) * (1 + eg.mix(t)[g])
                            for g, qty in m.outputs.items()) - self._value(m.inputs)
                self.assertAlmostEqual(typed, 1600, delta=0.5)


if __name__ == "__main__":
    unittest.main()
