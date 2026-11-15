"""A common-currency adopter's core inflation is pulled toward its leader's (owner, 2026-11-15).

An adopter keeps its own inflation (§15A.1, ruling G1), but traded goods in one
money sell at one price, so `te_mon_pressure_regime_pull` gains a fourth branch:
-te_mon_union_price_pull x (own core - the leader's core), reading
`te_mon_anchor_core`, step 1c's copy of the anchor's `te_inflation_core`.

Pinned here:

* the branch, through the small interpreter in test_banking_external_tools: its
  sign both ways, the guard on the copy, that only an adopter gets it, and that
  the branches above it win;
* the fixed point with expectations at the leader's core: leader + P / 2;
* the reason the pull is 1 and not 0.5: under the leader's rate the stance term
  hands an adopter back 0.4 of each point it runs hot, so with no pull it has no
  fixed point at all, and with 1 the gap settles near its own pressure;
* the seed and the step 1c copy, and that the copy stays hidden state.
"""
import re
import unittest
from pathlib import Path

from test_banking_external_tools import definitions
from test_monetary_deficit_cap import Monetary, constant

ROOT = Path(__file__).resolve().parent
ARRANGEMENT_EFFECTS = ROOT / 'common/scripted_effects/te_monetary_arrangement_effects.txt'


def interpreter(**inputs):
    """One interpreter for a loop: building one parses five script files."""
    inputs.setdefault('te_mon_is_union_adopter', True)
    return Monetary(laws={'law_fiat_currency'}, **inputs)


def pull(core, leader=None, s=None, **inputs):
    s = s or interpreter(**inputs)
    s.vars['te_inflation_core'] = core
    if leader is not None:
        s.vars['te_mon_anchor_core'] = leader
    return s.number('te_mon_pressure_regime_pull')


class Branch(unittest.TestCase):
    def test_the_owner_s_number(self):
        self.assertEqual(constant('te_mon_union_price_pull'), 1,
                         'retuned: edit the comment above te_mon_union_price_pull and the design doc §0.15')

    def test_it_closes_on_the_leader_s_core_both_ways(self):
        k = constant('te_mon_union_price_pull')
        for core, leader in ((6, 2), (2, 6), (-1, 2), (2, 2), (40, 3.5)):
            self.assertAlmostEqual(pull(core, leader), -k * (core - leader), msg=(core, leader))

    def test_no_copy_no_pull(self):
        self.assertEqual(pull(8), 0)

    def test_only_an_adopter(self):
        for core in (0, 6, 30):
            self.assertEqual(pull(core, 2, te_mon_is_union_adopter=False), 0, core)

    def test_the_branches_above_win(self):
        # An adopter joins on fiat money, not dollarized (te_mon_union_regime_fits); one
        # dollarized since takes the dollarized pull, since that money is what circulates.
        self.assertAlmostEqual(pull(10, 4, te_mon_is_metallic=True), -10)
        self.assertAlmostEqual(pull(10, 4, te_mon_is_dollarised=True), -8)

    def test_it_is_the_last_branch(self):
        body = definitions('common/script_values/te_monetary_script_values.txt')['te_mon_pressure_regime_pull']
        branches = [val for key, _, val in body if key in ('if', 'else_if')]
        (limit,) = [val for key, _, val in branches[-1] if key == 'limit']
        self.assertIn(('te_mon_is_union_adopter', '=', 'yes'), limit)
        self.assertIn(('has_variable', '=', 'te_mon_anchor_core'), limit)


class FixedPoint(unittest.TestCase):
    def test_with_expectations_at_the_leader_s_core_it_settles_halfway(self):
        # Step 6: core += speed x (expected + P + pull - core). With half the basket
        # traded at one price, half the gap the domestic sum would open is what is left.
        speed = constant('te_mon_core_speed')
        s = interpreter()
        for leader in (2.0, 3.5):
            for other in (-1.0, 0.0, 1.0, 3.0):
                core = 20.0
                for _ in range(600):
                    core += speed * (leader + other + pull(core, leader, s=s) - core)
                self.assertAlmostEqual(core, leader + other / 2, places=6, msg=(leader, other))


class UnderTheLeadersRate(unittest.TestCase):
    """Step 6 with the stance term in the loop, which is what an adopter actually faces.

    The leader sits at core 2 and its neutral stance, so its rate is r* + 2 and an
    adopter with the same r* has a stance gap of 2 - its own headline (step 8: rate
    - headline - r*; no cost-push here, so headline = core). Expectations blend
    toward the leader's target with the imported credibility c, de-anchoring over
    te_mon_deanchor_span (te_mon_expectation_target), at a non-CBI alpha of 1/24.
    The stance and the pull are the script's own values, through the interpreter.
    """

    LEADER = 2.0

    def gap(self, c, other, adopter=True, months=1500):
        speed = constant('te_mon_core_speed')
        span = constant('te_mon_deanchor_span')
        core = expected = self.LEADER
        stance_gap = 0.0
        s = interpreter(te_mon_is_union_adopter=adopter)
        for _ in range(months):
            s.vars.update(te_inflation_core=core, te_mon_anchor_core=self.LEADER,
                          te_mon_stance_gap=stance_gap)  # step 6 reads last month's gap
            total = other + s.number('te_mon_pressure_stance') + s.number('te_mon_pressure_regime_pull')
            c_eff = c * max(0.0, 1 - abs(core - self.LEADER) / span)
            expected += (core * (1 - c_eff) + self.LEADER * c_eff - expected) / 24
            core += speed * (expected + total - core)
            stance_gap = self.LEADER - core
        return core - self.LEADER

    def test_without_the_pull_there_is_no_fixed_point(self):
        # 0.56 is 0.8 x an independent bank's 0.7: the best credibility an adopter imports.
        self.assertGreater(self.gap(0.56, 1.0, adopter=False), 30)

    def test_with_it_the_gap_settles_near_the_country_s_own_pressure(self):
        for c in (0.25, 0.56):
            for other in (0.5, 1.0, 2.0):
                gap = self.gap(c, other)
                self.assertGreater(gap, 0.4 * other, msg=(c, other))  # its inflation is still its own
                self.assertLess(gap, 1.3 * other, msg=(c, other))


class TheCopy(unittest.TestCase):
    def setUp(self):
        self.text = re.sub(r'#[^\n]*', '', ARRANGEMENT_EFFECTS.read_text(encoding='utf-8-sig'))

    def test_seeded_behind_has_variable(self):
        self.assertRegex(self.text, r'NOT = \{ has_variable = te_mon_anchor_core \} \}\s*'
                                    r'set_variable = \{ name = te_mon_anchor_core value = 2 \}')

    def test_copied_in_step_1c_from_the_anchor_s_core(self):
        start = self.text.index('te_monetary_update_anchor = {')
        body = self.text[start:self.text.index('te_mon_emergency_controls_months', start)]
        self.assertRegex(body, r'scope:te_mon_anchor_now = \{ has_variable = te_inflation_core \}')
        self.assertIn('set_variable = { name = te_mon_anchor_core '
                      'value = scope:te_mon_anchor_now.var:te_inflation_core }', body)

    def test_hidden(self):
        # The leader's core is hidden state (ruling P7): no tooltip, loc string or panel shows it.
        for folder, pattern in (('localization/english', '*.yml'), ('gui', '*.gui')):
            for path in (ROOT / folder).rglob(pattern):
                self.assertNotIn('te_mon_anchor_core', path.read_text(encoding='utf-8-sig'), path)


if __name__ == '__main__':
    unittest.main()
