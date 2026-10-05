"""Peg confidence's monthly recovery (ruling Q10, revised 2026-09-27).

Three things are pinned here, all run on the real script through the small
interpreter in test_banking_external_tools:

* the recovery is banded — +3 under 40 (Doubted), +2 under 70 (Watched), +1
  above (Trusted) — for a gold peg and a treaty peg alike;
* borrowed gold blocks a gold peg's recovery only while it is LEAVING, at a gap
  of 0 or under. A peg-defence bank parks a tenth or three over the world rate
  (ruling Q5), so while any hot money at all blocked it, every AI on gold and
  every delegated player bank stayed frozen wherever the last crisis left it;
* an almost-empty vault's +2 is capped at the healthy heal, so it never
  recovers faster than a healthy vault (+1 from 70);
* a deep slump holds the recovery, as overvaluation does (2026-10-05; the
  drain itself is pinned in test_monetary_fiat_path).

The simulator's port (scripts/analysis/banking_cycle_sim.py) is checked against
the same cases.
"""
import unittest

from test_banking_external_tools import Script, definitions


def find_heal_branch(body):
    """The else_if that follows step 10's `te_mon_peg_under_pressure = yes` if."""
    for i, (key, _, val) in enumerate(body):
        if not isinstance(val, list):
            continue
        if key == 'if' and ('te_mon_peg_under_pressure', '=', 'yes') in Script.field(val, 'limit'):
            assert body[i + 1][0] == 'else_if', body[i + 1][0]
            return body[i + 1][2]
        found = find_heal_branch(val)
        if found is not None:
            return found
    return None


def peg_script(**inputs):
    defaults = dict(te_mon_fx_is_overvalued=False, te_mon_is_swap_recipient=False,
                    te_mon_union_gets_cooperation=False, te_mon_capital_controls_in_force=False,
                    te_mon_peg_in_deep_slump=False)
    s = Script(**{**defaults, **inputs})
    s.values.update(definitions('common/script_values/te_monetary_union_script_values.txt'))
    s.effects.update(definitions('common/scripted_effects/te_monetary_arrangement_effects.txt'))
    return s


class BandedRecovery(unittest.TestCase):
    def test_heal_follows_the_dashboard_bands(self):
        s = peg_script()
        for confidence, heal in ((0, 3), (20, 3), (39.9, 3), (40, 2), (69.9, 2),
                                 (70, 1), (100, 1)):
            s.vars['te_peg_confidence'] = confidence
            self.assertEqual(s.number('te_mon_peg_confidence_heal'), heal, confidence)

    def test_heal_is_guarded_against_a_missing_variable(self):
        self.assertEqual(peg_script().number('te_mon_peg_confidence_heal'), 1)

    def test_treaty_peg_heals_by_band(self):
        for start, end in ((30, 33), (50, 52), (80, 81), (99.5, 100)):
            s = peg_script()
            s.vars.update(te_peg_confidence=start, te_peg_crisis_cooldown=5)
            s.effect('te_monetary_update_anchor_peg')
            self.assertEqual(s.vars['te_peg_confidence'], end, start)

    def test_treaty_peg_still_holds_while_overvalued(self):
        s = peg_script(te_mon_fx_is_overvalued=True)
        s.vars.update(te_peg_confidence=50, te_peg_crisis_cooldown=5,
                      te_mon_overvaluation=5)
        s.effect('te_monetary_update_anchor_peg')
        self.assertEqual(s.vars['te_peg_confidence'], 50)


class GoldPegHealCondition(unittest.TestCase):
    def setUp(self):
        body = definitions('common/scripted_effects/te_monetary_effects.txt')['te_monetary_update_gold']
        self.branch = find_heal_branch(body)
        self.assertIsNotNone(self.branch)

    def heals(self, gap, hot, overvalued=False, slump=False):
        s = peg_script(te_mon_fx_is_overvalued=overvalued, te_mon_peg_in_deep_slump=slump)
        s.vars.update(te_gold_flow_gap=gap, te_gold_hot_money=hot)
        return s.check(Script.field(self.branch, 'limit'))

    def test_hot_money_at_a_positive_gap_does_not_block_the_heal(self):
        # Peg defence parked 0.3 over the world rate, vault full of borrowed gold.
        self.assertTrue(self.heals(gap=0.3, hot=5000))

    def test_hot_money_leaving_at_the_floor_still_holds_it(self):
        self.assertFalse(self.heals(gap=0, hot=5000))

    def test_rate_at_the_world_rate_with_no_hot_money_heals(self):
        self.assertTrue(self.heals(gap=0, hot=0))

    def test_rate_under_the_world_rate_holds_it(self):
        self.assertFalse(self.heals(gap=-0.5, hot=0))

    def test_overvaluation_holds_it(self):
        self.assertFalse(self.heals(gap=0.3, hot=0, overvalued=True))

    def test_a_deep_slump_holds_it(self):
        # Peg defence parked a little over the world rate, vault healthy: it
        # would heal, but not while the slump it is prolonging lasts.
        self.assertTrue(self.heals(gap=0.3, hot=0))
        self.assertFalse(self.heals(gap=0.3, hot=0, slump=True))

    def test_the_branch_adds_the_banded_heal(self):
        adds = [val for key, _, val in self.branch if key == 'change_variable']
        self.assertEqual(adds, [[('name', '=', 'te_peg_confidence'),
                                 ('add', '=', 'te_mon_peg_confidence_heal')]])


class LowVaultRecovery(unittest.TestCase):
    """Under pressure the positive term is +2, capped at the healthy heal, so an
    almost-empty vault never recovers faster than a healthy one (+1 from 70)."""

    def move(self, confidence):
        s = peg_script(scaled_debt=0.2)
        s.vars.update(te_peg_confidence=confidence, te_gold_flow_gap=0, te_gold_hot_money=0)
        return s.number('te_mon_peg_confidence_move')

    def test_capped_at_the_healthy_heal(self):
        for confidence, move in ((10, 2), (39, 2), (50, 2), (69, 2), (70, 1), (95, 1)):
            self.assertEqual(self.move(confidence), move, confidence)

    def test_never_faster_than_a_healthy_vault(self):
        s = peg_script()
        for confidence in range(0, 101, 5):
            s.vars['te_peg_confidence'] = confidence
            self.assertLessEqual(self.move(confidence), s.number('te_mon_peg_confidence_heal'))


class SimulatorPort(unittest.TestCase):
    def step(self, *, gap, hot, confidence, bank_gold=1e6):
        from scripts.analysis.banking_cycle_sim import Config, State, monetary_update_gold
        state = State(policy_rate=3 + gap, bank_gold=bank_gold, bank_gold_seeded=True,
                      gold_hot_money=hot, peg_confidence=confidence)
        monetary_update_gold(Config(currency='gold'), state, 3)
        return state.peg_confidence

    def test_sim_heals_by_band_through_borrowed_gold_at_a_positive_gap(self):
        self.assertEqual(self.step(gap=0.3, hot=100000, confidence=30), 33)
        self.assertEqual(self.step(gap=0.3, hot=100000, confidence=50), 52)
        self.assertEqual(self.step(gap=0.3, hot=100000, confidence=80), 81)

    def test_sim_holds_while_borrowed_gold_leaves(self):
        self.assertEqual(self.step(gap=0, hot=100000, confidence=50), 50)

    def test_sim_caps_the_low_vault_term(self):
        # 1e5 against a limit of 0.2 x 1e7: a twentieth, under pressure.
        self.assertEqual(self.step(gap=0, hot=0, confidence=50, bank_gold=1e5), 52)
        self.assertEqual(self.step(gap=0, hot=0, confidence=80, bank_gold=1e5), 81)


if __name__ == '__main__':
    unittest.main()
