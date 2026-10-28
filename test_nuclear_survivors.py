"""Second-strike survivors against an enemy's arsenal (2026-10-28 rework
spec §3.2): the Python mirror and the script values it mirrors."""

import math
import unittest
from dataclasses import replace

from scripts.analysis.nuclear_incident_rates import Posture, RiskModel
from scripts.analysis.nuclear_survivors import survivors


class TestSurvivorsFormula(unittest.TestCase):
    def test_formula_cases(self):
        # Half of ten exposed, an enemy of three: three destroyed.
        self.assertEqual(survivors(10, 50, 1.0, 0, 1.0, 3), 7)
        # All ten exposed, the enemy could destroy 40: Launch on Warning's
        # credit of 0.6 gets six away first.
        self.assertTrue(math.isclose(survivors(10, 0, 1.0, 0.6, 2.0, 20), 6))
        self.assertEqual(survivors(0, 80, 1.0, 0, 1, 5), 0)

    def test_readiness_factor_scales_survivability(self):
        self.assertTrue(math.isclose(survivors(10, 50, 0.5, 0, 1.0, 20), 2.5))


class TestSurvivorsScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def test_launch_credit(self):
        credit = {(a, s): self.model.number("nd_launch_credit", Posture(authority=a, safeguards=s))
                  for a in (1, 2, 3, 4) for s in (0, 3)}
        self.assertEqual(credit[1, 0], 0)
        self.assertEqual(credit[4, 0], 0)
        self.assertTrue(math.isclose(credit[2, 0], 0.25))
        self.assertTrue(math.isclose(credit[2, 3], 0.10))
        self.assertTrue(math.isclose(credit[3, 0], 0.6))
        self.assertTrue(math.isclose(credit[3, 3], 0.45))

    def test_exchange_ratio(self):
        k = self.model.number
        self.assertEqual(k("nd_k_ratio", Posture(icbms=False, pgm=False)), 1)
        self.assertEqual(k("nd_k_ratio", Posture(icbms=True, pgm=False)), 1.5)
        self.assertEqual(k("nd_k_ratio", Posture(icbms=True, pgm=True)), 2)

    def test_redundancy(self):
        r = self.model.number("nd_redundancy", Posture(stockpile=30, satellite_communications=True, mainframe=False))
        self.assertTrue(math.isclose(r, 6))

    def test_mirror_matches_script(self):
        enemy = Posture(believed_stockpile=12, icbms=True, pgm=False)
        for p in (Posture(readiness=3, authority=1, safeguards=0, survivability=40, stockpile=10, enemy=enemy),
                  Posture(readiness=1, authority=3, safeguards=2, survivability=70, stockpile=6, enemy=enemy),
                  Posture(readiness=2, authority=2, safeguards=3, survivability=10, stockpile=20,
                          enemy=replace(enemy, believed_stockpile=2))):
            factor = self.model.number("nd_effective_survivability", p) / p.survivability
            expected = survivors(p.stockpile, p.survivability, factor, self.model.number("nd_launch_credit", p),
                                 self.model.number("nd_k_ratio", p.enemy), p.enemy.believed_stockpile)
            self.assertTrue(math.isclose(self.model.number("nd_survivors_vs_saved", p), expected), p)

    def test_variants(self):
        enemy = Posture(believed_stockpile=40, icbms=True, pgm=True)
        p = Posture(readiness=0, authority=3, safeguards=0, survivability=60, stockpile=10, enemy=enemy)
        heightened = replace(p, readiness=2)
        self.assertTrue(math.isclose(self.model.number("nd_survivors_r2_vs_saved", p),
                                     self.model.number("nd_survivors_vs_saved", heightened)))
        bare = replace(heightened, authority=1)
        self.assertTrue(math.isclose(self.model.number("nd_survivors_bare_r2_vs_saved", p),
                                     self.model.number("nd_survivors_vs_saved", bare)))
        ceiling = replace(bare, survivability=self.model.number("nd_survivability_cap", p))
        self.assertTrue(math.isclose(self.model.number("nd_survivors_ceiling_bare_r2_vs_saved", p),
                                     self.model.number("nd_survivors_vs_saved", ceiling)))


if __name__ == "__main__":
    unittest.main()
