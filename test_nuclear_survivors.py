"""Second-strike survivors against an enemy's arsenal (2026-10-28 rework
spec §3.2): the Python mirror and the script values it mirrors."""

import math
import re
import unittest
from dataclasses import replace
from pathlib import Path

from scripts.analysis.nuclear_incident_rates import Posture, RiskModel
from scripts.analysis.nuclear_survivors import (counterforce_destroyed, counterforce_saved, decapitation_chance,
                                                survivors)

ROOT = Path(__file__).resolve().parent


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


class TestCounterforceScript(unittest.TestCase):
    """A Forces salvo destroys min(exposed, K x landed) x (1 - credit) of the
    victim's warheads (rework spec §6.2). The attacker is scope:nd_sv_enemy."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def destroyed(self, victim):
        return self.model.number("nd_counterforce_destroyed_raw", victim)

    def test_counterforce_matches_mirror(self):
        for landed in (0, 1, 3, 8):
            for survivability in (0, 40, 80):
                for authority, safeguards in ((1, 0), (2, 3), (3, 0), (4, 1)):
                    for icbms, pgm in ((False, False), (True, True)):
                        attacker = Posture(salvo_forces_landed=landed, icbms=icbms, pgm=pgm)
                        victim = Posture(readiness=2, authority=authority, safeguards=safeguards,
                                         survivability=survivability, stockpile=10, enemy=attacker)
                        exposed = self.model.number("nd_exposed_warheads", victim)
                        k = self.model.number("nd_k_ratio", attacker)
                        credit = self.model.number("nd_launch_credit", victim)
                        self.assertTrue(math.isclose(self.destroyed(victim),
                                                     counterforce_destroyed(landed, k, exposed, credit),
                                                     abs_tol=1e-9), victim)
                        self.assertTrue(math.isclose(self.model.number("nd_counterforce_saved_raw", victim),
                                                     counterforce_saved(landed, k, exposed, credit),
                                                     abs_tol=1e-9), victim)

    def test_counterforce_bounded_by_exposed_and_stockpile(self):
        attacker = Posture(salvo_forces_landed=50, icbms=True, pgm=True)
        for stockpile, survivability in ((3, 0), (0, 0), (6, 50)):
            victim = Posture(readiness=3, authority=1, survivability=survivability, stockpile=stockpile, enemy=attacker)
            self.assertLessEqual(self.destroyed(victim), stockpile)
            self.assertLessEqual(self.destroyed(victim), self.model.number("nd_exposed_warheads", victim) + 1e-9)
        hidden = Posture(readiness=3, authority=1, survivability=100, stockpile=10, enemy=attacker)
        self.assertEqual(self.destroyed(hidden), 0)

    def test_saved_share_is_the_credit(self):
        attacker = Posture(salvo_forces_landed=4, icbms=False, pgm=False)
        victim = Posture(readiness=3, authority=3, safeguards=0, survivability=0, stockpile=10, enemy=attacker)
        # Four destroyable, Launch on Warning's 0.6 of them get away first.
        self.assertTrue(math.isclose(self.model.number("nd_counterforce_saved_raw", victim), 2.4))
        self.assertTrue(math.isclose(self.destroyed(victim), 1.6))


class TestDecapitationScript(unittest.TestCase):
    """Chance = max(0, (L - R)/(L + R)) for L warheads on the capital against
    redundancy R (rework spec §6.3)."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def chance(self, landed, redundancy):
        attacker = Posture(salvo_capital_landed=landed, salvo_victim_r=redundancy)
        return self.model.number("nd_decapitation_chance_value", Posture(enemy=attacker))

    def test_chance_matches_mirror(self):
        for landed in (0, 1, 2, 5, 9):
            for redundancy in (1, 1.3, 3.5, 6):
                self.assertTrue(math.isclose(self.chance(landed, redundancy), decapitation_chance(landed, redundancy),
                                             abs_tol=1e-9), (landed, redundancy))

    def test_thirty_warhead_power_needs_seven(self):
        r = self.model.number("nd_redundancy", Posture(stockpile=30, satellite_communications=True, mainframe=False))
        self.assertEqual(self.chance(6, r), 0)
        self.assertGreater(self.chance(7, r), 0)

    def test_three_warhead_state_faces_21_from_two(self):
        r = self.model.number("nd_redundancy", Posture(stockpile=3, satellite_communications=False, mainframe=False))
        self.assertTrue(math.isclose(r, 1.3))
        self.assertTrue(math.isclose(self.chance(2, r), 0.7 / 3.3 * 100))

    def test_believed_redundancy_reads_the_estimate(self):
        p = Posture(stockpile=30, believed_stockpile=10, satellite_communications=False, mainframe=False)
        self.assertTrue(math.isclose(self.model.number("nd_redundancy_believed", p), 2))


class TestSalvoScale(unittest.TestCase):
    """A salvo's UN record, infamy, world relations and taboo knock are a
    single strike's figure times sqrt(warheads landed) (owner, 2026-10-28)."""

    SINGLE = {
        "nd_salvo_un_order_first": "-4",
        "nd_salvo_un_order_answer": "-2",
        "nd_salvo_un_shock": "-3",
        "nd_salvo_dossier_first": "un_dos_points_first_strike",
        "nd_salvo_dossier_answer": "un_dos_points_retaliation",
        "nd_salvo_infamy": "nd_taboo_infamy_strategic",
        "nd_salvo_world_relations": "nd_taboo_world_relations_strategic",
    }

    def test_scaled_values_are_the_single_strike_times_sqrt(self):
        values = (ROOT / "common/script_values/nuclear_deterrence_values.txt").read_text(encoding="utf-8-sig")
        strike = (ROOT / "common/scripted_effects/extra_effects.txt").read_text(encoding="utf-8-sig")
        for name, single in self.SINGLE.items():
            m = re.search(r"(?m)^" + name + r" = \{(.*?)^\}", values, re.S)
            self.assertIsNotNone(m, name)
            body = " ".join(" ".join(line.split("#", 1)[0] for line in m.group(1).splitlines()).split())
            self.assertIn(f"value = {single} multiply = var:nd_salvo_sqrt", body, name)
            # The single strike still uses that figure.
            self.assertIn(single, strike, name)


class TestCalibration(unittest.TestCase):
    """K against the arsenals the AI builds (owner, 2026-10-28: keep K, check
    it here). AI great powers want about 5 to 20 warheads."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def left_after(self, victim):
        return victim.stockpile - self.model.number("nd_counterforce_destroyed_raw", victim)

    def test_one_warhead_cannot_disarm_a_large_arsenal(self):
        attacker = Posture(salvo_forces_landed=1, icbms=True, pgm=True)
        victim = Posture(readiness=3, authority=1, survivability=0, stockpile=20, enemy=attacker)
        self.assertGreaterEqual(self.left_after(victim), 18)

    def test_hardened_great_power_keeps_a_second_strike(self):
        attacker = Posture(salvo_forces_landed=20, icbms=True, pgm=True)
        cap = self.model.number("nd_survivability_cap", Posture())
        victim = Posture(readiness=2, authority=1, survivability=cap, stockpile=20, enemy=attacker)
        self.assertGreaterEqual(self.left_after(victim), 3)

    def test_unhardened_small_arsenal_can_be_disarmed(self):
        attacker = Posture(salvo_forces_landed=3, icbms=True, pgm=True)
        victim = Posture(readiness=3, authority=1, survivability=0, stockpile=5, enemy=attacker)
        self.assertEqual(self.left_after(victim), 0)


if __name__ == "__main__":
    unittest.main()
