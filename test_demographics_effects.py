"""The demographic effects' curves and sizes (docs/superpowers/specs/2026-10-22-demographic-effects-impact-design.md):
scripts/analysis/demographics_effects.py, the Python twin the harness's readouts and the size tests read."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts" / "analysis"))

import demographics_effects as DE  # noqa: E402


class TestCurves(unittest.TestCase):
    """The spec's § The curve table, point by point."""

    def test_extended(self):
        self.assertEqual(DE.extended(0.5), 0.5)
        self.assertEqual(DE.extended(1), 1)
        self.assertEqual(DE.extended(2), 1.5)
        self.assertEqual(DE.extended(-1), 0)
        self.assertEqual(DE.extended(5, cap=2), 2)

    def test_wealth_concentration(self):
        for score, high, low in ((80, 1, 0), (90, 4 / 3, 0), (100, 5 / 3, 0), (20, 0, 1), (10, 0, 7 / 6),
                                 (0, 0, 4 / 3), (50, 0, 0)):
            self.assertAlmostEqual(DE.wc_high(score), high, msg=score)
            self.assertAlmostEqual(DE.wc_low(score), low, msg=score)

    def test_primacy(self):
        for p, s in ((0.25, 0), (0.5, 1), (0.6, 1.2), (0.8, 1.6), (1.0, 2)):
            self.assertAlmostEqual(DE.primacy(p), s, msg=p)

    def test_metro(self):
        for share, up in ((40, 0), (60, 1), (80, 1.5), (95, 1.875)):
            self.assertAlmostEqual(DE.metro_up(share), up, msg=share)
        self.assertAlmostEqual(DE.metro_down(5), 1)
        self.assertAlmostEqual(DE.metro_down(0), 1, msg="the dispersed side has nothing beyond its floor")
        self.assertAlmostEqual(DE.metro_down(12.5), 0.5)

    def test_sex(self):
        for b, more in ((110, 0), (130, 1), (150, 1.5), (170, 2), (200, 2)):
            self.assertAlmostEqual(DE.more_men(b), more, msg=b)
        for b, fewer in ((90, 0), (80, 1), (70, 1.5), (60, 2), (40, 2)):
            self.assertAlmostEqual(DE.fewer_men(b), fewer, msg=b)

    def test_youth(self):
        self.assertAlmostEqual(DE.youth(0.24, 0.2), 1)
        self.assertAlmostEqual(DE.youth(0.30, 0.2), 1.5)
        self.assertAlmostEqual(DE.youth(0.36, 1.0), 2, msg="2 x 3, capped")
        self.assertEqual(DE.youth(0.17, 0.5), 0)

    def test_inequality(self):
        for g, m in ((0.45, 0), (0.65, 1), (0.70, 1.25), (0.80, 2.25), (1.0, 4.25)):
            self.assertAlmostEqual(DE.inequality(g), m, msg=g)

    def test_caps(self):
        self.assertEqual(DE.primacy(1.0), 2)
        self.assertEqual(DE.more_men(400), 2)
        self.assertEqual(DE.fewer_men(0), 2)
        self.assertEqual(DE.youth(1.0, 1.0), 2)

    def test_old_curves(self):
        self.assertAlmostEqual(DE.wc_high_old(80), 0.6)
        self.assertAlmostEqual(DE.wc_low_old(0), 1)
        self.assertAlmostEqual(DE.primacy_old(0.6), 1)
        self.assertAlmostEqual(DE.primacy_old(0.9), 1)
        self.assertAlmostEqual(DE.metro_up_old(80), 1)
        self.assertAlmostEqual(DE.more_men_old(150), 1)
        self.assertAlmostEqual(DE.fewer_men_old(60), 1)
        self.assertAlmostEqual(DE.youth_old(0.36, 1.0), 1)
        self.assertAlmostEqual(DE.inequality_old(0.8), 1.75)

    def test_none_is_zero(self):
        for name, (old, new) in DE.CONDITIONS.items():
            self.assertEqual(new(None), 0, name)
            self.assertEqual(old(None), 0, name)
        self.assertEqual(DE.youth(None, 0.2), 0)
        self.assertEqual(DE.youth_old(0.3, None), 0)


class TestSizes(unittest.TestCase):
    """The modifiers' fields at 1x, from the spec's tables (the build's size tests pin script to these)."""

    def test_the_spec_sizes(self):
        self.assertEqual(DE.SIZES["inh_great_fortunes"], {
            "country_aristocrats_pol_str_mult": 0.2, "country_capitalists_pol_str_mult": 0.2,
            "country_bubble_pressure_monthly_add": 0.3})
        self.assertEqual(DE.SIZES["inh_dispersed_property"], {
            "state_political_strength_from_wealth_mult": -0.1, "state_pop_qualifications_mult": 0.1,
            "state_education_access_add": 0.1, "state_radicals_from_political_movements_mult": -0.1})
        self.assertNotIn("state_aristocrats_investment_pool_efficiency_mult", DE.SIZES["inh_dispersed_property"])

    def test_every_modifier(self):
        self.assertEqual(set(DE.SIZES), {
            "inh_great_fortunes", "inh_dispersed_wealth", "inh_concentrated_property", "inh_dispersed_property",
            "inh_land_hunger", "te_demog_census_inequality", "te_demog_primate_city", "te_demog_provincial_neglect",
            "te_demog_mt_metropolis", "te_demog_mt_crowding", "te_demog_mt_dispersed", "te_demog_census_youth_bulge",
            "te_demog_census_fewer_men", "te_demog_census_more_men"})

    def test_the_bubble_line_is_symmetric(self):
        self.assertEqual(DE.BUBBLE_GREAT, -DE.BUBBLE_DISPERSED)
        self.assertEqual(DE.SIZES["inh_dispersed_wealth"]["country_bubble_pressure_monthly_add"], DE.BUBBLE_DISPERSED)


if __name__ == "__main__":
    unittest.main()
