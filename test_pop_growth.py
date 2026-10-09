"""scripts/analysis/pop_growth.py reads the mod's growth defines (#demographics Task 1)."""

import dataclasses
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import pop_growth as G  # noqa: E402


class TestDefines(unittest.TestCase):
    def setUp(self):
        self.d = G.read_defines()

    def test_reads_the_file(self):
        self.assertEqual(self.d.max_birthrate, 0.00475)
        self.assertEqual(self.d.min_birthrate, 0.00080)
        self.assertEqual(self.d.max_mortality, 0.00600)
        self.assertEqual(self.d.min_mortality, 0.00100)
        self.assertEqual((self.d.equilibrium_sol, self.d.transition_sol, self.d.max_sol, self.d.stable_sol),
                         (4, 11, 18, 35))

    def test_curve_endpoints(self):
        self.assertAlmostEqual(G.monthly_birthrate(0, self.d), 0.00475)
        self.assertAlmostEqual(G.monthly_birthrate(11, self.d), 0.00475)
        self.assertAlmostEqual(G.monthly_birthrate(35, self.d), 0.00080)
        self.assertAlmostEqual(G.monthly_birthrate(50, self.d), 0.00080)
        self.assertAlmostEqual(G.monthly_mortality(0, self.d), 0.00600)
        self.assertAlmostEqual(G.monthly_mortality(35, self.d), 0.00100)
        self.assertAlmostEqual(G.monthly_mortality(4, self.d), G.monthly_birthrate(4, self.d))
        self.assertAlmostEqual(G.monthly_birthrate(0, self.d, malnourishment=True), 0.00475 * 0.6)

    def test_yearly_api_unchanged(self):
        self.assertAlmostEqual(G.calculate_birthrate(35), 0.00080 * 12)

    def test_stable_sol_shrinks(self):
        # spec Context: absent modifiers a state at SoL 35 shrinks by 0.24% a year
        self.assertAlmostEqual(G.calculate_growth_rate(35), -0.0024, places=6)

    def test_derived_values_follow_the_define_formulas_off_default(self):
        # With transition_birthrate_mult != 1 the pre-transition slope is the defines file's
        # (birthrate_at_transition - rate_at_equilibrium) / pop_growth_transition_sol, not zero-based.
        d = dataclasses.replace(self.d, transition_birthrate_mult=1.5)
        at_transition = d.max_birthrate * 1.5
        rate_at_eq = d.equilibrium_sol * ((at_transition - d.max_birthrate) / d.transition_sol) + d.max_birthrate
        pre_slope = (at_transition - rate_at_eq) / d.transition_sol
        for sol in (4, 7, 11):
            self.assertAlmostEqual(G.monthly_birthrate(sol, d), pre_slope * sol + d.max_birthrate)
        self.assertAlmostEqual(G.monthly_mortality(d.equilibrium_sol, d), rate_at_eq)
