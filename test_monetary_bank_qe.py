"""The mandate bank's own asset purchases at the rate floor (design doc §0.12).

A bank that runs its mandate (delegated, AI or independent) under fiat or
digital money keeps a VIRTUAL rate beside its real one: where it would put the
rate if the floor were not there. Above the floor the two are the same; under
it the real rate sits on the floor and the bank buys assets in proportion to
the gap, `te_mon_pressure_bank_qe = min(cap, per_pp x (floor - virtual rate))`.
The virtual rate drifts at the real rate's speeds, so the purchases never
switch on or off in one step, and they are gone by the month the real rate
leaves the floor. Price stability may only take the virtual rate under the
floor while prices are under target; growth always may.

Pinned here:

* the real script value and the two triggers, run through the small
  interpreter in test_banking_external_tools;
* the three effects the virtual rate lives in (step 1d's settle, step 2c's
  virtual target and step 3's drift), executed on the real script, and a
  month-by-month run of the three that checks the purchases move no faster
  than the drift and are gone before the real rate rises;
* the simulator's port (scripts/analysis/banking_cycle_sim.py) against the same
  numbers, the regimes that must not get it, the reported deflation trap and
  the pre_bank_qe preset;
* the figures the in-game tooltips state in words ("one point", "two and a
  half"), which nothing else reads back from the constants;
* the Asset Purchases row: its figure is OMO plus the bank's term, neither goes
  through the modifier channel that Inflation Anchoring nets against (so the
  Price Pressure row cannot print them), and the row is wired in under the
  anchoring row.
"""
import re
import unittest
from pathlib import Path

from test_banking_external_tools import Script, definitions, parse_body

ROOT = Path(__file__).resolve().parent
LOC = ROOT / 'localization/english/te_miscellaneous_l_english.yml'
EFFECTS = 'common/scripted_effects/te_monetary_effects.txt'
TRIGGERS = 'common/scripted_triggers/te_monetary_triggers.txt'
VALUES = 'common/script_values/te_monetary_script_values.txt'

DIGITAL_FLOOR, FIAT_FLOOR = -3.0, 0.0
DIGITAL_STEP = 0.6667  # te_mon_drift_step under law_digital_currency's +100% speed


def constants():
    values = definitions(VALUES)
    return (float(dict((k, v) for k, _, v in values['te_mon_bank_qe_per_pp'])['value']),
            float(dict((k, v) for k, _, v in values['te_mon_bank_qe_cap'])['value']))


def past_the_cap(floor=DIGITAL_FLOOR):
    """A virtual rate well past the depth at which the purchases reach their cap."""
    per_pp, cap = constants()
    return floor - 2 * cap / per_pp


def term(virtual, floor=DIGITAL_FLOOR, can=True):
    """`te_mon_pressure_bank_qe` on the real script, with the gate and floor stubbed."""
    s = Script(te_mon_bank_can_buy_assets=can, te_mon_target_min=floor)
    s.vars['te_mon_virtual_rate'] = virtual
    return s.number('te_mon_pressure_bank_qe')


class Monetary(Script):
    """The interpreter, with the monetary effects and two things they need.

    `round = yes` inside a value block, and calls to a parameterised effect
    (`te_monetary_drift_rate_toward = { RATE = x TARGET = y }`), which are
    expanded the way the engine does: by substituting $RATE$ and $TARGET$ into
    the effect's text before it is read.
    """

    def __init__(self, floor=DIGITAL_FLOOR, step=DIGITAL_STEP, **inputs):
        stubs = dict(
            te_mon_target_min=floor, te_mon_target_max=25.0,
            te_mon_drift_step=step, te_mon_drift_step_threshold=step + 0.0067,
            te_mon_drift_step_down=step, te_mon_drift_step_down_threshold_neg=-(step + 0.0067),
            te_mon_bank_can_buy_assets=True, te_mon_bank_may_go_under_floor=True)
        stubs.update(inputs)
        super().__init__(**stubs)
        self.source = (ROOT / EFFECTS).read_text(encoding='utf-8-sig')
        self.effects.update(definitions(EFFECTS))
        self.triggers['te_mon_policy_rate_at_floor'] = definitions(TRIGGERS)['te_mon_policy_rate_at_floor']
        self.vars.update(te_mon_work=0, te_mon_work2=0)

    def seat(self, rate, target, virtual_rate=None, virtual_target=None):
        self.vars.update(te_policy_rate=rate, te_policy_rate_target=target,
                         te_mon_virtual_rate=rate if virtual_rate is None else virtual_rate,
                         te_mon_virtual_target=target if virtual_target is None else virtual_target)
        return self

    def value(self, body, initial=0):
        if any(key == 'round' for key, _, _ in body):
            rest = [item for item in body if item[0] != 'round']
            return float(round(super().value(rest, initial)))
        return super().value(body, initial)

    def execute(self, body):
        # Expand each parameterised call into an effect of its own and hand the
        # base interpreter the whole block, so if / else_if / else chains hold.
        expanded = []
        for key, op, val in body:
            if (key in self.effects and isinstance(val, list) and val
                    and all(k.isupper() for k, _, _ in val)):
                text = re.search(rf'^{key} = \{{\n(.*?)^\}}', self.source, re.M | re.S).group(1)
                for name, _, arg in val:
                    text = text.replace(f'${name}$', arg)
                call = f'{key}({",".join(arg for _, _, arg in val)})'
                self.effects[call] = parse_body(text)
                expanded.append((call, '=', 'yes'))
            else:
                expanded.append((key, op, val))
        super().execute(expanded)

    def month(self, work):
        """Steps 1d, 2c, 2b and 3 of one pulse, with the mandate formula's answer given."""
        self.effect('te_monetary_settle_virtual_rate')
        self.vars['te_mon_work'] = work
        self.effect('te_monetary_update_virtual_target')
        self.effect('te_monetary_clamp_target')
        self.effect('te_monetary_drift_policy_rate')
        return self.number('te_mon_pressure_bank_qe'), self.vars['te_policy_rate']


class ScriptValue(unittest.TestCase):
    def test_zero_when_the_bank_cannot_buy(self):
        for virtual in (-6, -4, -3, 2):
            self.assertEqual(term(virtual, can=False), 0, virtual)

    def test_zero_at_or_above_the_floor(self):
        for floor, virtual in ((DIGITAL_FLOOR, -3), (DIGITAL_FLOOR, 1), (FIAT_FLOOR, 0), (FIAT_FLOOR, 4)):
            self.assertEqual(term(virtual, floor), 0, (floor, virtual))

    def test_scales_with_the_depth_under_the_floor_until_the_cap(self):
        per_pp, cap = constants()
        for floor in (DIGITAL_FLOOR, FIAT_FLOOR):
            for depth in (0.33, 1, 2, 2.4):
                self.assertAlmostEqual(term(floor - depth, floor), per_pp * depth, msg=(floor, depth))
                self.assertLess(per_pp * depth, cap)

    def test_capped(self):
        per_pp, cap = constants()
        for beyond in (0, 0.5, 7):
            virtual = DIGITAL_FLOOR - cap / per_pp - beyond
            self.assertEqual(term(virtual), cap, virtual)

    def test_the_virtual_target_stops_where_the_cap_is_reached(self):
        per_pp, cap = constants()
        s = Script()
        self.assertAlmostEqual(s.number('te_mon_virtual_depth_max'), cap / per_pp)
        self.assertAlmostEqual(term(DIGITAL_FLOOR - cap / per_pp), cap)

    def test_the_virtual_target_floor_follows_the_mandate(self):
        per_pp, cap = constants()
        for may, want in ((True, DIGITAL_FLOOR - cap / per_pp), (False, DIGITAL_FLOOR)):
            s = Script(te_mon_bank_may_go_under_floor=may, te_mon_target_min=DIGITAL_FLOOR)
            self.assertAlmostEqual(s.number('te_mon_virtual_target_min'), want, msg=may)

    def test_missing_virtual_rate_is_guarded(self):
        s = Script(te_mon_bank_can_buy_assets=True, te_mon_target_min=DIGITAL_FLOOR)
        self.assertEqual(s.number('te_mon_pressure_bank_qe'), 0)

    def test_reads_the_virtual_rate_not_inflation(self):
        text = repr(definitions(VALUES)['te_mon_pressure_bank_qe'])
        self.assertIn('var:te_mon_virtual_rate', text)
        self.assertIn('te_mon_target_min', text)
        self.assertNotIn('te_inflation', text)  # neither core (hidden, ruling P7) nor headline


def find(body, key):
    return [(op, val) for k, op, val in body if k == key]


class Gates(unittest.TestCase):
    def test_who_can_buy_has_the_three_conditions_and_no_floor_test(self):
        gate = definitions(TRIGGERS)['te_mon_bank_can_buy_assets']
        self.assertIn(('=', 'yes'), find(gate, 'te_mon_has_dial'))
        self.assertIn(('=', 'yes'), find(gate, 'te_mon_mandate_binds'))
        self.assertEqual(find(gate, 'te_mon_policy_rate_at_floor'), [])
        (_, either), = find(gate, 'OR')
        laws = sorted(val for _, _, val in either)
        self.assertEqual(laws, ['law_type:law_digital_currency', 'law_type:law_fiat_currency'])

    def may(self, mandate, headline, can=True):
        s = Script(te_mon_bank_can_buy_assets=can, te_mon_inflation_anchor=2)
        s.triggers['te_mon_bank_may_go_under_floor'] = definitions(TRIGGERS)['te_mon_bank_may_go_under_floor']
        s.vars['te_mon_mandate'] = mandate
        if headline is not None:
            s.vars['te_inflation'] = headline
        return s.check([('te_mon_bank_may_go_under_floor', '=', 'yes')])

    def test_price_stability_goes_under_the_floor_only_with_prices_under_target(self):
        for headline in (-6.6, 0, 1.9):
            self.assertTrue(self.may(1, headline), headline)
        for headline in (2, 2.5, 8):
            self.assertFalse(self.may(1, headline), headline)
        self.assertFalse(self.may(1, None))  # no headline yet

    def test_growth_goes_under_the_floor_with_prices_on_target_too(self):
        for headline in (-6.6, 1.9, 2, 5, None):
            self.assertTrue(self.may(2, headline), headline)

    def test_neither_mandate_without_a_bank_that_can_buy(self):
        for mandate in (1, 2):
            self.assertFalse(self.may(mandate, -5, can=False), mandate)

    def test_is_part_of_the_pressure_sum(self):
        total = definitions(VALUES)['te_mon_pressure_total']
        self.assertIn(('=', 'te_mon_pressure_bank_qe'), find(total, 'add'))
        self.assertIn(('=', 'te_mon_pressure_qe'), find(total, 'add'))  # beside OMO, not instead of it

    def test_the_monthly_update_settles_the_virtual_rate_before_the_dial(self):
        update = repr(definitions(EFFECTS)['te_monetary_monthly_update'])
        self.assertLess(update.index("'te_monetary_settle_virtual_rate'"),
                        update.index("'te_monetary_update_target'"))

    def test_a_save_without_the_virtual_pair_is_seeded_from_the_real_one(self):
        init = repr(definitions(EFFECTS)['te_monetary_init_variables'])
        self.assertIn("('name', '=', 'te_mon_virtual_target'), ('value', '=', 'var:te_policy_rate_target')", init)
        self.assertIn("('name', '=', 'te_mon_virtual_rate'), ('value', '=', 'var:te_policy_rate')", init)


class Effects(unittest.TestCase):
    """The three effects the virtual rate lives in, on the real script."""

    def test_settle_resets_the_virtual_pair_unless_the_bank_is_buying(self):
        # Buying: real pair on the floor, virtual pair under it. Kept.
        s = Monetary().seat(-3, -3, -4.33, -5)
        s.effect('te_monetary_settle_virtual_rate')
        self.assertEqual((s.vars['te_mon_virtual_rate'], s.vars['te_mon_virtual_target']), (-4.33, -5))
        # The player took the dial back: reset, so nothing stale comes back with delegation.
        s = Monetary(te_mon_bank_can_buy_assets=False).seat(-3, -3, -4.33, -5)
        s.effect('te_monetary_settle_virtual_rate')
        self.assertEqual((s.vars['te_mon_virtual_rate'], s.vars['te_mon_virtual_target']), (-3, -3))
        # Off the floor (a debug sequence wrote the real rate): the real pair wins.
        s = Monetary().seat(5, 5, -4.33, -5)
        s.effect('te_monetary_settle_virtual_rate')
        self.assertEqual((s.vars['te_mon_virtual_rate'], s.vars['te_mon_virtual_target']), (5, 5))
        # A virtual pair that is not under the real one carries nothing.
        s = Monetary().seat(-3, -3, -2, -1)
        s.effect('te_monetary_settle_virtual_rate')
        self.assertEqual((s.vars['te_mon_virtual_rate'], s.vars['te_mon_virtual_target']), (-3, -3))

    def test_virtual_target_keeps_the_hysteresis_and_rounding(self):
        s = Monetary().seat(-3, -3, -3, -4)
        for work, want in ((-4.6, -4), (-3.4, -4), (-4.8, -5), (-2.2, -2)):
            s.vars['te_mon_work'] = work
            s.effect('te_monetary_update_virtual_target')
            self.assertEqual(s.vars['te_mon_virtual_target'], want, work)
            self.assertEqual(s.vars['te_policy_rate_target'], want, work)  # step 2b then holds it at the floor

    def test_virtual_target_stops_at_the_depth_or_at_the_floor(self):
        per_pp, cap = constants()
        s = Monetary().seat(-3, -3)
        s.vars['te_mon_work'] = -12  # what price stability asks for at -6.6%
        s.effect('te_monetary_update_virtual_target')
        self.assertAlmostEqual(s.vars['te_mon_virtual_target'], DIGITAL_FLOOR - cap / per_pp)
        s.effect('te_monetary_clamp_target')
        self.assertEqual(s.vars['te_policy_rate_target'], DIGITAL_FLOOR)
        s = Monetary(te_mon_bank_may_go_under_floor=False).seat(-3, -3, -3, -5)
        s.vars['te_mon_work'] = -12
        s.effect('te_monetary_update_virtual_target')
        self.assertEqual(s.vars['te_mon_virtual_target'], DIGITAL_FLOOR)

    def test_drift_holds_the_real_rate_on_the_floor_while_the_virtual_one_carries_on(self):
        s = Monetary().seat(-3, -3, -3, -5)
        s.effect('te_monetary_drift_policy_rate')
        self.assertAlmostEqual(s.vars['te_mon_virtual_rate'], -3 - DIGITAL_STEP)
        self.assertEqual(s.vars['te_policy_rate'], DIGITAL_FLOOR)

    def test_drift_above_the_floor_is_the_ordinary_drift(self):
        for rate, target in ((4, 1), (1, 4), (-1.5, -3), (2, 2.3)):
            virtual = Monetary().seat(rate, target)
            virtual.effect('te_monetary_drift_policy_rate')
            manual = Monetary(te_mon_bank_can_buy_assets=False).seat(rate, target)
            manual.effect('te_monetary_drift_policy_rate')
            self.assertAlmostEqual(virtual.vars['te_policy_rate'], manual.vars['te_policy_rate'],
                                   msg=(rate, target))

    def test_a_year_down_and_back_moves_the_purchases_a_drift_step_at_a_time(self):
        per_pp, cap = constants()
        s = Monetary().seat(-3, -3)
        path = [-12] * 8 + [-4.8] * 4 + [-1.0] * 10  # the mandate asks deep, then less, then off the floor
        prev, seen = 0.0, []
        for work in path:
            bought, rate = s.month(work)
            self.assertLessEqual(abs(bought - prev), per_pp * DIGITAL_STEP + 1e-6, work)
            if rate > DIGITAL_FLOOR + 0.01:
                self.assertEqual(bought, 0, 'the purchases are gone before the rate rises')
            seen.append(bought)
            prev = bought
        self.assertEqual(max(seen), cap)
        self.assertGreater(s.vars['te_policy_rate'], DIGITAL_FLOOR)

    def test_price_stability_at_target_winds_the_purchases_down_rather_than_stopping(self):
        per_pp, cap = constants()
        deepest = DIGITAL_FLOOR - cap / per_pp
        s = Monetary().seat(-3, -3, deepest, deepest)
        s.inputs['te_mon_bank_may_go_under_floor'] = False  # prices back at target
        bought = [s.month(-12)[0] for _ in range(int(cap / (per_pp * DIGITAL_STEP)) + 2)]
        self.assertGreater(bought[0], 0)
        self.assertAlmostEqual(cap - bought[0], per_pp * DIGITAL_STEP, places=3)
        self.assertEqual(bought[-1], 0)


class SimulatorPort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.analysis import banking_cycle_sim as sim
        cls.sim = sim
        sim.TUNE.clear()

    def config(self, currency='digital', fin_law='law_central_bank_independence',
               mode=None, national_bank=True):
        sim = self.sim
        return sim.Config(currency=currency, fin_law=fin_law, national_bank=national_bank,
                          mode=sim.MODE_PRICE if mode is None else mode)

    def state(self, cfg, virtual, headline=-5.0):
        lo, _ = self.sim.target_bounds(cfg, self.sim.State(), 3.0)
        return self.sim.State(policy_rate=max(lo, virtual), policy_rate_target=lo,
                              virtual_rate=virtual, virtual_target=virtual, inflation=headline)

    def test_matches_the_script_value(self):
        for currency, floor in (('fiat', FIAT_FLOOR), ('digital', DIGITAL_FLOOR)):
            cfg = self.config(currency)
            for depth in (-1, 0, 0.5, 1.7, 2.5, 4, 9):
                got = self.sim.bank_qe_pressure(cfg, self.state(cfg, floor - depth), 3.0)
                self.assertAlmostEqual(got, term(floor - depth, floor), msg=(currency, depth))

    def test_every_mandate_run_bank_can_buy(self):
        sim = self.sim
        cbi = self.config(mode=sim.MODE_NOTHING)  # independence runs the mandate whatever the player does
        delegated = self.config(fin_law='law_universal_banking_light_prudence', mode=sim.MODE_GROWTH)
        for cfg in (cbi, delegated):
            self.assertTrue(sim.bank_can_buy_assets(cfg, sim.State()), cfg.fin_law)
            self.assertGreater(sim.bank_qe_pressure(cfg, self.state(cfg, -6), 3.0), 0, cfg.fin_law)

    def test_a_manual_dial_metal_and_a_missing_bank_cannot(self):
        sim = self.sim
        manual = self.config(fin_law='law_universal_banking_light_prudence', mode=sim.MODE_NOTHING)
        for cfg in (manual, self.config('gold'), self.config('commodity'),
                    self.config('digital', national_bank=False)):
            self.assertFalse(sim.bank_can_buy_assets(cfg, sim.State()), (cfg.currency, cfg.mode))
            self.assertEqual(sim.bank_qe_pressure(cfg, self.state(cfg, -6), 3.0), 0)

    def test_the_mandate_condition_matches_the_trigger(self):
        sim = self.sim
        price = self.config()
        growth = self.config(mode=sim.MODE_GROWTH)
        for headline, want_price in ((-6.6, True), (1.9, True), (2.0, False), (5.0, False)):
            st = sim.State(inflation=headline)
            self.assertEqual(sim.bank_may_go_under_floor(price, st), want_price, headline)
            self.assertTrue(sim.bank_may_go_under_floor(growth, st), headline)

    def test_enters_the_pressure_sum(self):
        sim = self.sim
        cfg = self.config()
        st = self.state(cfg, past_the_cap())
        on = sim.pressure_total(cfg, st, 3.0)
        sim.TUNE['bank_qe'] = 0.0
        try:
            off = sim.pressure_total(cfg, st, 3.0)
        finally:
            sim.TUNE.clear()
        self.assertAlmostEqual(on - off, constants()[1])

    def trap(self, tune, mode=None, fin_law='law_central_bank_independence', months=120):
        """The reported trap: Digital Currency, rate on -3, headline -6.6, no noise."""
        import random
        sim = self.sim
        sim.TUNE.clear()
        sim.TUNE.update(tune)
        cfg = sim.Config(currency='digital', mode=sim.MODE_PRICE if mode is None else mode, points=8,
                         fin_law=fin_law, wage_pressure=0.9, bank_level=9)
        st = sim.State(policy_rate=-3.0, policy_rate_target=-3.0, inflation=-6.6,
                       inflation_core=-4.2, inflation_expected=-4.9, neutral_rate=3.0,
                       basket_index=0.92, basket_avg=1.0)
        st.basket_seeded = True
        rng = random.Random(1)
        rows = []
        try:
            for _ in range(months):
                st.neutral_walk = st.neutral_error = st.inflation_noise = st.growth_term = 0.0
                st.deficit_pct = 0.0
                sim.monetary_update(cfg, st, rng, 0)
                rows.append((st.inflation, st.policy_rate, st.virtual_rate,
                             sim.bank_qe_pressure(cfg, st, 3.0)))
        finally:
            sim.TUNE.clear()
        return rows

    def test_a_deflation_that_stalled_now_recovers(self):
        def years_to_zero(rows):
            return next((month / 12 for month, row in enumerate(rows, 1) if row[0] >= 0), None)
        # Without Open-Market Operations the old model fell to the -10 clamp for good.
        self.assertIsNone(years_to_zero(self.trap({'bank_qe': 0.0})))
        after = years_to_zero(self.trap({}))
        self.assertIsNotNone(after)
        self.assertLess(after, 8)

    def test_in_the_trap_the_purchases_never_jump_and_end_before_the_rate_rises(self):
        per_pp, cap = constants()
        rows = self.trap({})
        bought = [row[3] for row in rows]
        self.assertGreater(max(bought), 0)
        self.assertLessEqual(max(bought), cap)
        for before, after in zip(bought, bought[1:]):
            self.assertLessEqual(abs(after - before), per_pp * DIGITAL_STEP + 1e-6)
        lifted = [row for row in rows if row[1] > DIGITAL_FLOOR + 0.01]
        self.assertTrue(lifted)
        self.assertEqual(lifted[0][3], 0)

    def test_pre_bank_qe_keeps_the_virtual_rate_on_the_real_one(self):
        for _, rate, virtual, bought in self.trap({'bank_qe': 0.0}, months=60):
            self.assertEqual((virtual, bought), (rate, 0))

    def test_the_currency_loop_imports_what_it_is_seeded_with(self):
        from scripts.analysis import banking_deflation_trap as trap
        loop = trap.CurrencyLoop(125.3, -2.6)
        self.assertAlmostEqual((loop.avg - loop.index) * 0.15, -2.6)

    def test_the_simulator_imports_nothing_unless_asked(self):
        self.assertEqual(self.sim.fx_imported(self.config(), self.sim.State(), 3.0), 0.0)

    def test_the_playtest_leaves_the_clamp_with_the_shipped_cap(self):
        """§0.12 "The cap": Panic, a strong currency, headline on -10%. The old cap held it there."""
        from scripts.analysis import banking_deflation_trap as trap
        shipped = [trap.playtest(seed, months=24)['off_clamp'] for seed in range(6)]
        previous = [trap.playtest(seed, months=24, cap=trap.PREVIOUS_CAP)['off_clamp'] for seed in range(6)]
        self.assertTrue(all(month is not None and month <= 12 for month in shipped), shipped)
        self.assertGreaterEqual(sum(month is None for month in previous), 4, previous)

    def test_a_manual_dial_is_unchanged(self):
        sim = self.sim
        manual = dict(mode=sim.MODE_NOTHING, fin_law='law_universal_banking_light_prudence')
        self.assertEqual(self.trap({}, **manual), self.trap({'bank_qe': 0.0}, **manual))


class PurchaseDisplay(unittest.TestCase):
    """The Asset Purchases row, and the display values it prints."""

    WIDGET = ROOT / 'gui/journal_entry_widgets/banking_dashboard_widget.gui'

    def display(self, omo, buys, name='te_mon_purchase_pressure_display'):
        s = Script(te_mon_bank_can_buy_assets=buys, te_mon_target_min=DIGITAL_FLOOR)
        s.vars['te_mon_virtual_rate'] = past_the_cap()
        if omo:
            s.tools.add('omo')
        return s.number(name)

    def test_is_omo_plus_the_banks_own_purchases(self):
        _, cap = constants()
        self.assertEqual(self.display(omo=False, buys=False), 0)
        self.assertEqual(self.display(omo=True, buys=False), 1.0)
        self.assertEqual(self.display(omo=False, buys=True), cap)
        self.assertEqual(self.display(omo=True, buys=True), cap + 1.0)

    def test_the_two_halves_the_tooltip_lists_add_up_to_the_row(self):
        _, cap = constants()
        omo = self.display(True, True, name='te_mon_omo_pressure_display')
        bank = self.display(True, True, name='te_mon_bank_purchase_display')
        self.assertEqual((omo, bank), (1.0, cap))
        self.assertEqual(omo + bank, self.display(True, True))

    def test_neither_term_goes_through_the_anchored_modifier_channel(self):
        values = definitions(VALUES)
        for name in ('te_mon_pressure_modifiers', 'te_mon_pressure_anchoring',
                     'te_mon_other_pressure_display', 'te_mon_wage_pressure_display'):
            text = repr(values[name])
            for purchase in ('te_mon_pressure_qe', 'te_mon_pressure_bank_qe',
                             'te_mon_purchase_pressure_display', 'te_mon_omo_pressure_display',
                             'te_mon_bank_purchase_display'):
                self.assertNotIn(purchase, text, (name, purchase))

    def test_the_row_is_shown_only_while_something_is_bought(self):
        # Text, not definitions(): the interpreter's parser stops after the first entry of this file.
        text = (ROOT / 'common/scripted_guis/te_monetary_sguis.txt').read_text(encoding='utf-8-sig')
        block = re.search(r'^banking_mon_has_purchases = \{\n(.*?)^\}', text, re.M | re.S)
        self.assertIsNotNone(block)
        self.assertIn('is_shown = { te_mon_purchase_pressure_display > 0 }', block.group(1))

    def test_the_row_is_wired_and_sits_between_anchoring_and_monetising(self):
        text = self.WIDGET.read_text(encoding='utf-8-sig')
        for needle in ("GetScriptedGui('banking_mon_has_purchases').IsShown(",
                       'tooltip = "banking_dash_mon_purchases_tt"',
                       'text = "banking_dash_mon_purchases_label"',
                       'text = "banking_dash_mon_purchases_value"'):
            self.assertEqual(text.count(needle), 1, needle)
        anchoring = text.index('banking_dash_mon_anchoring_tt')
        purchases = text.index('banking_dash_mon_purchases_tt')
        monetise = text.index('banking_dash_mon_monetise_tt')
        self.assertLess(anchoring, purchases)  # the anchoring row's comment says "the two rows above"
        self.assertLess(purchases, monetise)

    def test_the_row_text_prints_the_display_values_and_says_anchoring_does_not_absorb_them(self):
        loc = TooltipNumbers.loc
        # A game concept like every other label in the block, so it renders as a concept link.
        self.assertEqual(loc(self, 'banking_dash_mon_purchases_label'),
                         "[Concept('concept_banking_asset_purchases','Asset Purchases')]")
        concepts = (ROOT / 'common/game_concepts/extra_concepts.txt').read_text(encoding='utf-8-sig')
        self.assertIn('\nconcept_banking_asset_purchases = {}\n', concepts)
        self.assertEqual(loc(self, 'concept_banking_asset_purchases'), 'Asset Purchases')
        desc = (ROOT / 'localization/english/te_concepts_l_english.yml').read_text(encoding='utf-8-sig')
        self.assertIn(' concept_banking_asset_purchases_desc:0 "', desc)
        self.assertIn("ScriptValue('te_mon_purchase_pressure_display')",
                      loc(self, 'banking_dash_mon_purchases_value'))
        tip = loc(self, 'banking_dash_mon_purchases_tt')
        self.assertIn("ScriptValue('te_mon_omo_pressure_display')", tip)
        self.assertIn("ScriptValue('te_mon_bank_purchase_display')", tip)
        self.assertIn('Inflation Anchoring does not absorb it', tip)

    def test_the_tooltip_names_the_virtual_rate_only_while_the_bank_buys(self):
        tip = TooltipNumbers.loc(self, 'banking_dash_mon_purchases_tt')
        self.assertIn("GetCustom('te_mon_virtual_rate_note')", tip)
        text = (ROOT / 'common/customizable_localization/banking_dash_custom_loc.txt').read_text(encoding='utf-8-sig')
        block = re.search(r'^te_mon_virtual_rate_note = \{\n(.*?)^\}', text, re.M | re.S).group(1)
        self.assertIn('trigger = { te_mon_bank_purchase_display > 0 }', block)
        self.assertLess(block.index('banking_dash_mon_purchases_virtual\n'),
                        block.index('banking_dash_mon_purchases_virtual_none'))
        self.assertIn("Var('te_mon_virtual_rate')", TooltipNumbers.loc(self, 'banking_dash_mon_purchases_virtual'))
        self.assertEqual(TooltipNumbers.loc(self, 'banking_dash_mon_purchases_virtual_none'), '')

    def test_price_pressure_keeps_its_modifier_breakdown_and_points_at_the_row(self):
        tip = TooltipNumbers.loc(self, 'banking_dash_mon_pressure_tt')
        self.assertIn("GetValueWithBreakdownFor('country_inflation_pressure_add')", tip)
        self.assertNotIn('te_mon_purchase_pressure_display', tip)  # the row's figure stays modifiers only
        self.assertIn('a row of their own', tip)


class DelegationHint(unittest.TestCase):
    """Ruling N1: a manual dial gets no purchases, and the Delegation tooltip says so when it matters."""

    def test_the_hint_closes_the_tooltips_first_paragraph(self):
        tip = TooltipNumbers.loc(self, 'banking_dash_mon_delegation_tt')
        call = "[JournalEntry.GetCountry.GetCustom('te_mon_delegation_purchase_hint')]"
        self.assertEqual(tip.count(call), 1)
        self.assertLess(tip.index(call), tip.index('$TOOLTIP_DELIMITER$'))

    def test_it_shows_only_for_a_manual_fiat_or_digital_dial_on_its_floor_with_prices_falling(self):
        text = (ROOT / 'common/customizable_localization/banking_dash_custom_loc.txt').read_text(encoding='utf-8-sig')
        block = re.search(r'^te_mon_delegation_purchase_hint = \{\n(.*?)^\}', text, re.M | re.S).group(1)
        trigger = re.search(r'trigger = \{(.*?)\n\t\t\}', block, re.S).group(1)
        for line in ('te_mon_has_dial = yes', 'te_mon_mandate_binds = no',
                     'has_law_or_variant = law_type:law_fiat_currency',
                     'has_law_or_variant = law_type:law_digital_currency',
                     'te_mon_policy_rate_at_floor = yes', 'var:te_inflation < 0'):
            self.assertIn(line, trigger)
        self.assertLess(block.index('banking_dash_mon_delegation_purchase_hint\n'),
                        block.index('banking_dash_mon_delegation_purchase_hint_none'))

    def test_the_hint_names_the_condition_rather_than_promising_purchases(self):
        hint = TooltipNumbers.loc(self, 'banking_dash_mon_delegation_purchase_hint')
        self.assertTrue(hint.startswith(' Your rate is on its floor and prices are falling'))
        self.assertIn('whenever its rule asked for a lower rate than the floor allows', hint)
        self.assertNotIn('\\n', hint)
        self.assertEqual(TooltipNumbers.loc(self, 'banking_dash_mon_delegation_purchase_hint_none'), '')


class TooltipNumbers(unittest.TestCase):
    """The tooltips state the figures in words, so a retune has to edit them."""

    def loc(self, key):
        match = re.search(rf'^ {key}:0 "(.*)"$', LOC.read_text(encoding='utf-8-sig'), re.M)
        self.assertIsNotNone(match, key)
        return match.group(1)

    def test_mandate_tooltip_states_the_slope_the_cap_and_each_mandates_rule(self):
        per_pp, cap = constants()
        text = self.loc('banking_dash_mon_mandate_tt')
        self.assertEqual(per_pp, 1.0, 'retuned: edit the tooltip, the player guide and §0.12')
        self.assertEqual(cap, 5.0, 'retuned: edit the tooltip, the player guide and §0.12')
        self.assertIn('#b one point#! of upward pressure on prices for every point it would have cut below the floor', text)
        self.assertIn('at most #b five#!', text)
        self.assertIn('$banking_dash_mon_mandate_price$ buys only while prices are under its target', text)
        self.assertIn('$banking_dash_mon_mandate_growth$ also buys through a slump with prices on target', text)

    def test_delegation_tooltip_says_independence_cannot_print(self):
        text = self.loc('banking_dash_mon_delegation_tt')
        self.assertIn('print for the treasury', text)
        self.assertIn('buys assets on its own account', text)


if __name__ == '__main__':
    unittest.main()
