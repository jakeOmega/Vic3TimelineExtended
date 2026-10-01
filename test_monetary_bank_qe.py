"""The mandate bank's own asset purchases at the rate floor (design doc §0.12).

A bank that runs its mandate (delegated, AI or independent) buys assets itself
once its rate is on the floor and headline inflation is under the anchor:
`te_mon_pressure_bank_qe = min(cap, per_pp x (anchor - headline))`. It exists
because Central Bank Independence forbids monetisation, and at the floor both
mandates ask for less than the floor allows, so an independent country in
deflation had only OMO's flat +1.0 to climb out on.

Four things are pinned here:

* the real script value, run through the small interpreter in
  test_banking_external_tools: zero while the gate is shut or prices are at
  target, linear under it, capped;
* the gate itself (`te_mon_bank_buys_assets`): the four conditions the design
  gives it, and the term's place in `te_mon_pressure_total`;
* the simulator's port (scripts/analysis/banking_cycle_sim.py) against the same
  numbers, and against the regimes that must not get it (metal, a manual dial,
  no national bank, a rate above the floor);
* the figures the in-game tooltips state in words ("half a point", "two and a
  half"), which nothing else reads back from the constants;
* the Price Pressure tooltip's asset-purchases line: the displayed figure is OMO
  plus the bank's term, and neither goes through the modifier channel that
  Inflation Anchoring nets against.
"""
import re
import unittest
from pathlib import Path

from test_banking_external_tools import Script, definitions

ROOT = Path(__file__).resolve().parent
LOC = ROOT / 'localization/english/te_miscellaneous_l_english.yml'


def term(headline, buys=True, anchor=2):
    """`te_mon_pressure_bank_qe` on the real script, with the gate and anchor stubbed."""
    s = Script(te_mon_bank_buys_assets=buys, te_mon_inflation_anchor=anchor)
    s.vars['te_inflation'] = headline
    return s.number('te_mon_pressure_bank_qe')


def constants():
    values = definitions('common/script_values/te_monetary_script_values.txt')
    return (float(dict((k, v) for k, _, v in values['te_mon_bank_qe_per_pp'])['value']),
            float(dict((k, v) for k, _, v in values['te_mon_bank_qe_cap'])['value']))


class ScriptValue(unittest.TestCase):
    def test_zero_when_the_bank_is_not_buying(self):
        for headline in (-9, -3, 0, 5):
            self.assertEqual(term(headline, buys=False), 0, headline)

    def test_zero_at_or_above_the_anchor(self):
        for headline in (2, 2.5, 8, 40):
            self.assertEqual(term(headline), 0, headline)

    def test_scales_with_the_shortfall_until_the_cap(self):
        per_pp, cap = constants()
        for headline in (1, 0, -1, -2.5):
            self.assertAlmostEqual(term(headline), per_pp * (2 - headline), msg=headline)
            self.assertLess(per_pp * (2 - headline), cap)

    def test_capped(self):
        _, cap = constants()
        for headline in (-3, -6.6, -10):
            self.assertEqual(term(headline), cap, headline)

    def test_cap_is_reached_five_points_under_target(self):
        per_pp, cap = constants()
        self.assertAlmostEqual(per_pp * 5, cap)

    def test_anchor_is_the_mandates_own(self):
        # Metal anchors on 0 and never reaches this gate, but the value must read
        # the anchor rather than a literal 2.
        self.assertAlmostEqual(term(-1, anchor=0), 0.5)

    def test_missing_headline_is_guarded(self):
        s = Script(te_mon_bank_buys_assets=True, te_mon_inflation_anchor=2)
        self.assertEqual(s.number('te_mon_pressure_bank_qe'), 0)


def find(body, key):
    return [(op, val) for k, op, val in body if k == key]


class Gate(unittest.TestCase):
    def setUp(self):
        self.gate = definitions('common/scripted_triggers/te_monetary_triggers.txt')['te_mon_bank_buys_assets']

    def test_has_the_four_conditions(self):
        self.assertIn(('=', 'yes'), find(self.gate, 'te_mon_has_dial'))
        self.assertIn(('=', 'yes'), find(self.gate, 'te_mon_mandate_binds'))
        self.assertIn(('=', 'yes'), find(self.gate, 'te_mon_policy_rate_at_floor'))
        (_, either), = find(self.gate, 'OR')
        laws = sorted(val for _, _, val in either)
        self.assertEqual(laws, ['law_type:law_digital_currency', 'law_type:law_fiat_currency'])

    def test_is_part_of_the_pressure_sum(self):
        total = definitions('common/script_values/te_monetary_script_values.txt')['te_mon_pressure_total']
        self.assertIn(('=', 'te_mon_pressure_bank_qe'), find(total, 'add'))
        self.assertIn(('=', 'te_mon_pressure_qe'), find(total, 'add'))  # beside OMO, not instead of it

    def test_reads_last_months_headline_not_core(self):
        body = definitions('common/script_values/te_monetary_script_values.txt')['te_mon_pressure_bank_qe']
        text = repr(body)
        self.assertIn('var:te_inflation', text)
        self.assertNotIn('te_inflation_core', text)  # hidden state, ruling P7


class PurchaseDisplay(unittest.TestCase):
    """te_mon_purchase_pressure_display, and the tooltip that prints it."""

    def display(self, omo, buys, headline=-5):
        s = Script(te_mon_bank_buys_assets=buys, te_mon_inflation_anchor=2)
        s.vars['te_inflation'] = headline
        if omo:
            s.tools.add('omo')
        return s.number('te_mon_purchase_pressure_display')

    def test_is_omo_plus_the_banks_own_purchases(self):
        _, cap = constants()
        self.assertEqual(self.display(omo=False, buys=False), 0)
        self.assertEqual(self.display(omo=True, buys=False), 1.0)
        self.assertEqual(self.display(omo=False, buys=True), cap)
        self.assertEqual(self.display(omo=True, buys=True), cap + 1.0)

    def test_neither_term_goes_through_the_anchored_modifier_channel(self):
        values = definitions('common/script_values/te_monetary_script_values.txt')
        for name in ('te_mon_pressure_modifiers', 'te_mon_pressure_anchoring',
                     'te_mon_other_pressure_display', 'te_mon_wage_pressure_display'):
            text = repr(values[name])
            self.assertNotIn('te_mon_pressure_qe', text, name)
            self.assertNotIn('te_mon_pressure_bank_qe', text, name)
            self.assertNotIn('te_mon_purchase_pressure_display', text, name)

    def test_the_tooltip_prints_it_and_says_anchoring_does_not_absorb_it(self):
        text = TooltipNumbers.loc(self, 'banking_dash_mon_pressure_tt')
        self.assertIn("ScriptValue('te_mon_purchase_pressure_display')", text)
        self.assertIn('Anchoring does not absorb it', text)
        # ...and the modifier breakdown it sits beside is still there.
        self.assertIn("GetValueWithBreakdownFor('country_inflation_pressure_add')", text)


class SimulatorPort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.analysis import banking_cycle_sim as sim
        cls.sim = sim
        sim.TUNE.clear()

    def state(self, cfg, headline, rate=None):
        sim = self.sim
        lo, _ = sim.target_bounds(cfg, sim.State(), 3.0)
        return sim.State(policy_rate=lo if rate is None else rate, inflation=headline)

    def config(self, currency='digital', fin_law='law_central_bank_independence',
               mode=None, national_bank=True):
        sim = self.sim
        return sim.Config(currency=currency, fin_law=fin_law, national_bank=national_bank,
                          mode=sim.MODE_PRICE if mode is None else mode)

    def test_matches_the_script_value(self):
        for currency in ('fiat', 'digital'):
            cfg = self.config(currency)
            for headline in (-10, -6.6, -3, -2.5, -1, 0, 1.5, 2, 6):
                got = self.sim.bank_qe_pressure(cfg, self.state(cfg, headline), 3.0)
                self.assertAlmostEqual(got, term(headline), msg=(currency, headline))

    def test_the_floor_is_the_regimes_own(self):
        digital = self.config('digital')
        fiat = self.config('fiat')
        # Digital's floor is -3, fiat's is 0: a rate of -1 is on fiat's floor only
        # as a bank that can still cut, and 0 is not on digital's.
        self.assertGreater(self.sim.bank_qe_pressure(digital, self.state(digital, -4), 3.0), 0)
        self.assertEqual(self.sim.bank_qe_pressure(digital, self.state(digital, -4, rate=0.0), 3.0), 0)
        self.assertGreater(self.sim.bank_qe_pressure(fiat, self.state(fiat, -4, rate=0.0), 3.0), 0)
        self.assertEqual(self.sim.bank_qe_pressure(fiat, self.state(fiat, -4, rate=0.5), 3.0), 0)

    def test_every_mandate_run_bank_gets_it(self):
        sim = self.sim
        cbi = self.config(mode=sim.MODE_NOTHING)  # independence runs the mandate whatever the player does
        delegated = self.config(fin_law='law_universal_banking_light_prudence', mode=sim.MODE_GROWTH)
        for cfg in (cbi, delegated):
            self.assertGreater(sim.bank_qe_pressure(cfg, self.state(cfg, -5), 3.0), 0, cfg.fin_law)

    def test_a_manual_dial_does_not(self):
        sim = self.sim
        cfg = self.config(fin_law='law_universal_banking_light_prudence', mode=sim.MODE_NOTHING)
        self.assertEqual(sim.bank_qe_pressure(cfg, self.state(cfg, -5), 3.0), 0)

    def test_metal_and_a_missing_bank_do_not(self):
        sim = self.sim
        for currency in ('gold', 'commodity'):
            cfg = self.config(currency)
            self.assertEqual(sim.bank_qe_pressure(cfg, self.state(cfg, -5), 3.0), 0, currency)
        cfg = self.config('digital', national_bank=False)
        self.assertEqual(sim.bank_qe_pressure(cfg, self.state(cfg, -5), 3.0), 0)

    def test_enters_the_pressure_sum(self):
        sim = self.sim
        cfg = self.config()
        st = self.state(cfg, -5)
        on = sim.pressure_total(cfg, st, 3.0)
        sim.TUNE['bank_qe'] = 0.0
        try:
            off = sim.pressure_total(cfg, st, 3.0)
        finally:
            sim.TUNE.clear()
        self.assertAlmostEqual(on - off, constants()[1])

    def test_a_deflation_that_stalled_now_recovers(self):
        """The reported trap: independent, Digital Currency, rate on -3, headline -6.6."""
        import random
        sim = self.sim

        def years_to_zero(tune):
            sim.TUNE.clear()
            sim.TUNE.update(tune)
            cfg = sim.Config(currency='digital', mode=sim.MODE_PRICE, points=8,
                             fin_law='law_central_bank_independence', wage_pressure=0.9, bank_level=9)
            st = sim.State(policy_rate=-3.0, policy_rate_target=-3.0, inflation=-6.6,
                           inflation_core=-4.2, inflation_expected=-4.9, neutral_rate=3.0,
                           basket_index=0.92, basket_avg=1.0)
            st.basket_seeded = True
            rng = random.Random(1)
            for month in range(1, 121):
                st.neutral_walk = st.neutral_error = st.inflation_noise = st.growth_term = 0.0
                st.deficit_pct = 0.0
                sim.monetary_update(cfg, st, rng, 0)
                if st.inflation >= 0:
                    return month / 12
            return None

        try:
            # Without Open-Market Operations the old model fell to the -10 clamp for good.
            before = years_to_zero({'bank_qe': 0.0})
            after = years_to_zero({})
        finally:
            sim.TUNE.clear()
        self.assertIsNone(before)
        self.assertIsNotNone(after)
        self.assertLess(after, 8)


class TooltipNumbers(unittest.TestCase):
    """The tooltips state the figures in words, so a retune has to edit them."""

    def loc(self, key):
        match = re.search(rf'^ {key}:0 "(.*)"$', LOC.read_text(encoding='utf-8-sig'), re.M)
        self.assertIsNotNone(match, key)
        return match.group(1)

    def test_mandate_tooltip_states_the_slope_and_the_cap(self):
        per_pp, cap = constants()
        text = self.loc('banking_dash_mon_mandate_tt')
        self.assertEqual(per_pp, 0.5, 'retuned: edit the tooltip, the player guide and §0.12')
        self.assertEqual(cap, 2.5, 'retuned: edit the tooltip, the player guide and §0.12')
        self.assertIn('half a point', text)
        self.assertIn('two and a half', text)

    def test_delegation_tooltip_says_independence_cannot_print(self):
        text = self.loc('banking_dash_mon_delegation_tt')
        self.assertIn('print for the treasury', text)
        self.assertIn('buys assets on its own account', text)


if __name__ == '__main__':
    unittest.main()
