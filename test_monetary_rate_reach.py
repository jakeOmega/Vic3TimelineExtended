"""The dial's reach above 20% (#1084, owner 2026-10-20).

Three changes let a fiat or digital bank win back an inflation past about 20%,
which at a 25% ceiling and a flat third of a point a month it could not:

* `te_mon_target_max` is `te_mon_target_ceiling_free` (60) for fiat, digital
  and a suspended gold standard; a convertible gold standard keeps
  `te_mon_target_ceiling_gold` (15), and commodity money its band;
* a month's drift is max(te_mon_drift_step, a sixth of the distance), both
  scaled by `te_mon_drift_speed_factor`, so digital currency stays twice as
  fast at every distance; an emergency cut raises only the least step. The
  distance counted is at most |headline - anchor| (`te_mon_inflation_gap_abs`,
  PR #1086's review), so a target set far past where the rate should go buys
  nothing a click could game: with inflation on target the drift is flat;
* `te_mon_pressure_stance` reads its own clamp, -2..+10, while the banking
  cycle's channel keeps the shared -2..+4 (the 2026-09-22 ruling).

Pinned here on the real script (the small interpreter in
test_banking_external_tools), against the simulator's port, and in the
tooltips and the player guide that state the figures.
"""
import re
import unittest
from pathlib import Path

from test_banking_external_tools import Script, definitions
from test_monetary_bank_qe import Monetary as QeMonetary

ROOT = Path(__file__).resolve().parent
VALUES = 'common/script_values/te_monetary_script_values.txt'
LOC = ROOT / 'localization/english/te_miscellaneous_l_english.yml'
GUIDE = ROOT / 'docs/player_guide/04-banking.md'
FLAT = 0.3333


def constant(name):
    return float(dict((k, v) for k, _, v in definitions(VALUES)[name])['value'])


def ceiling(**inputs):
    stubs = dict(te_mon_is_on_gold=False, te_mon_has_narrow_dial=False)
    stubs.update(inputs)
    s = Script(**stubs)
    s.vars['te_mon_commodity_centre'] = 3
    return s.number('te_mon_target_max')


class Ceiling(unittest.TestCase):
    def test_the_owner_s_numbers(self):
        self.assertEqual(constant('te_mon_target_ceiling_free'), 60)
        self.assertEqual(constant('te_mon_target_ceiling_gold'), 15)

    def test_fiat_digital_and_suspended_gold_reach_sixty(self):
        # Fiat and digital are the fall-through, and so is a gold standard whose
        # convertibility is suspended (te_mon_is_on_gold is false while it lasts).
        self.assertEqual(ceiling(), 60)

    def test_gold_keeps_fifteen(self):
        self.assertEqual(ceiling(te_mon_is_on_gold=True), 15)

    def test_commodity_money_keeps_its_band(self):
        self.assertEqual(ceiling(te_mon_has_narrow_dial=True), 3 + constant('te_mon_commodity_band_margin_up'))

    def test_the_floors_are_unchanged(self):
        for floor_add, want in ((0.0, 0), (-0.03, -3)):
            s = Script(te_mon_peg_is_defending=False, te_mon_has_narrow_dial=False, te_mon_is_on_gold=False,
                       **{'modifier:country_policy_rate_floor_add': floor_add})
            self.assertAlmostEqual(s.number('te_mon_target_min'), want)


class Drift:
    """te_monetary_drift_rate_toward on the real step values, at a given speed.

    `inflation` is last month's headline, which caps the distance the step
    counts (|headline - anchor|, anchor 2). The default, 50, is far enough off
    that the cap does not bind for any gap below 48; None leaves no headline.
    """

    def __init__(self, speed=1.0, emergency=False, inflation=50.0):
        harness = QeMonetary(te_mon_bank_can_buy_assets=False)
        for stub in ('te_mon_drift_step', 'te_mon_drift_step_threshold', 'te_mon_drift_step_down',
                     'te_mon_drift_step_down_threshold_neg'):
            harness.inputs.pop(stub)
        harness.inputs.update(te_mon_drift_speed_factor=speed, te_mon_emergency_cuts=emergency,
                              te_mon_inflation_anchor=2.0)
        if inflation is not None:
            harness.vars['te_inflation'] = inflation
        self.harness = harness

    def step(self, rate, target):
        h = self.harness
        h.vars.update(te_policy_rate=rate, te_policy_rate_target=target)
        h.effect('te_monetary_drift_policy_rate')
        return h.vars['te_policy_rate']

    def path(self, rate, target, months):
        out = []
        for _ in range(months):
            rate = self.step(rate, target)
            out.append(rate)
        return out


class DriftFormula(unittest.TestCase):
    def test_a_sixth_of_the_distance_far_out(self):
        for gap in (12, 24, 35):
            self.assertAlmostEqual(Drift().step(25, 25 + gap) - 25, gap / 6, places=4, msg=gap)
            self.assertAlmostEqual(25 - Drift().step(25, 25 - gap), gap / 6, places=4, msg=gap)

    def test_a_third_of_a_point_close_in(self):
        for gap in (0.5, 1, 1.5, 2):
            self.assertAlmostEqual(Drift().step(5, 5 + gap) - 5, FLAT, places=4, msg=gap)
            self.assertAlmostEqual(5 - Drift().step(5, 5 - gap), FLAT, places=4, msg=gap)

    def test_a_one_point_move_still_takes_three_months(self):
        for got, want in zip(Drift().path(3, 4, 3), (3 + FLAT, 3 + 2 * FLAT, 4)):
            self.assertAlmostEqual(got, want, places=6)

    def test_digital_is_twice_as_fast_at_every_distance(self):
        for gap in (1.5, 3, 12, 30):
            fiat = Drift().step(10, 10 + gap) - 10
            digital = Drift(speed=2).step(10, 10 + gap) - 10
            self.assertAlmostEqual(digital, 2 * fiat, places=4, msg=gap)

    def test_an_emergency_cut_raises_only_the_least_step(self):
        factor = constant('te_mon_emergency_cut_factor')
        self.assertAlmostEqual(5 - Drift(emergency=True).step(5, 3), factor * FLAT, places=4)
        self.assertAlmostEqual(25 - Drift(emergency=True).step(25, 1), 24 / 6, places=4)
        self.assertAlmostEqual(Drift(emergency=True).step(5, 6.5) - 5, FLAT, places=4)  # hikes keep the ordinary step

    def test_it_never_steps_past_the_target(self):
        for speed in (1, 2, 7, 12):
            for rate, target in ((0, 60), (60, 0), (25, 27), (4, 3.5)):
                path = Drift(speed=speed).path(rate, target, 400)
                self.assertTrue(all(min(rate, target) - 1e-9 <= r <= max(rate, target) + 1e-9 for r in path))
                self.assertAlmostEqual(path[-1], target)

    def test_twenty_five_points_in_about_a_year_and_a_half(self):
        months = Drift().path(25, 50, 120)
        first_within = next(m for m, r in enumerate(months, 1) if r >= 50 - 2.5)
        self.assertLessEqual(first_within, 14)  # a flat third of a point took 68 months to get there
        self.assertEqual(months[-1], 50)

    def test_the_distance_counted_is_at_most_how_far_inflation_is_from_target(self):
        # 5 points of inflation off target: a sixth of 5, however far the target.
        for target in (12, 30, 60):
            self.assertAlmostEqual(Drift(inflation=7).step(5, target) - 5, 5 / 6, places=4, msg=target)
            self.assertAlmostEqual(5 - Drift(inflation=-3).step(5 + target, 5) + target, 5 / 6, places=4)
        # Digital doubles the capped step too.
        self.assertAlmostEqual(Drift(speed=2, inflation=7).step(5, 60) - 5, 2 * 5 / 6, places=4)

    def test_with_inflation_on_target_the_drift_is_flat(self):
        for inflation in (2.0, 2.2, 1.5, None):
            for rate, target in ((5, 14), (5, 60), (40, 15), (25, 0)):
                moved = abs(Drift(inflation=inflation).step(rate, target) - rate)
                self.assertAlmostEqual(moved, FLAT, places=4, msg=(inflation, rate, target))

    def test_overshooting_the_target_buys_nothing_with_inflation_on_target(self):
        # The review's exploit: shift-click to 60 for a pulse, then back. Each month
        # the gamer takes whichever target lands the rate nearest 14 without passing it.
        def months(gamed, inflation):
            drift, rate, n = Drift(inflation=inflation), 5.0, 0
            while abs(rate - 14) > 1e-6 and n < 200:
                options = (14, 20, 30, 45, 60) if gamed else (14,)
                landed = [drift.step(rate, t) for t in options]
                rate = min((r for r in landed if r <= 14 + 1e-9), key=lambda r: 14 - r)
                n += 1
            return n
        self.assertEqual(months(True, 2.0), months(False, 2.0))
        self.assertEqual(months(False, 2.0), 27)  # 9 points at a third of a point
        # far off target the bank is meant to move fast, honest or not
        self.assertLessEqual(months(False, 36.0), 16)

    def test_the_step_values_are_only_read_inside_the_drift(self):
        # They read the scratch variable te_mon_work, so nothing may render them.
        shown = LOC.read_text(encoding='utf-8-sig') + ''.join(
            p.read_text(encoding='utf-8-sig') for p in (ROOT / 'gui').rglob('*.gui'))
        for name in ('te_mon_drift_step_up_now', 'te_mon_drift_step_down_now', 'te_mon_drift_gap_down'):
            self.assertNotIn(name, shown)
        for name in ('te_mon_drift_step_up_now', 'te_mon_drift_step_down_now'):
            body = definitions(VALUES)[name]
            self.assertIn(('max', '=', 'var:te_mon_work' if 'up' in name else 'te_mon_drift_gap_down'), body)
            # the inflation cap bounds the distance, ahead of the divide
            self.assertEqual(body[1], ('max', '=', 'te_mon_inflation_gap_abs'), name)
            self.assertEqual(body[2][0], 'divide', name)


def stance(gap):
    s = Script()
    if gap is not None:
        s.vars['te_mon_stance_gap'] = gap
    return s.number('te_mon_pressure_stance'), s.number('te_mon_stance_gap_clamped')


class StanceClamp(unittest.TestCase):
    def test_the_inflation_term_reaches_ten_points_of_gap(self):
        coeff = constant('te_mon_stance_pressure_coeff')
        self.assertEqual(constant('te_mon_pressure_stance_clamp_tight'), 10)
        for gap in (0, 2, 4, 6.5, 10):
            self.assertAlmostEqual(stance(gap)[0], -coeff * gap, msg=gap)
        self.assertAlmostEqual(stance(10)[0], -4.0)

    def test_the_loose_side_is_the_shared_one(self):
        coeff = constant('te_mon_stance_pressure_coeff')
        loose = constant('te_mon_stance_gap_clamp_loose')
        for gap in (-2, -5, -10):
            self.assertAlmostEqual(stance(gap)[0], -coeff * max(loose, gap), msg=gap)

    def test_the_cycle_keeps_its_own_clamp(self):
        self.assertEqual(constant('te_mon_stance_gap_clamp_tight'), 4)
        self.assertEqual(constant('te_mon_stance_gap_clamp_loose'), -2)
        for gap, want in ((10, 4), (6, 4), (3, 3), (-10, -2)):
            self.assertEqual(stance(gap)[1], want, gap)
        values = definitions(VALUES)
        for name in ('te_mon_stance_momentum_add', 'te_mon_stance_bubble_add'):
            self.assertEqual(values[name][0], ('value', '=', 'te_mon_stance_gap_clamped'), name)

    def test_guarded(self):
        self.assertEqual(stance(None), (0, 0))


class Simulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.analysis import banking_cycle_sim as sim
        cls.sim = sim

    def tearDown(self):
        self.sim.TUNE.clear()

    def test_ceilings(self):
        sim = self.sim
        for currency, want in (('fiat', 60), ('digital', 60), ('gold', 15)):
            self.assertEqual(sim.target_bounds(sim.Config(currency=currency), sim.State(), 3.0)[1], want)
        sim.TUNE.update(sim.PRESETS['pre_rate_reach'])
        self.assertEqual(sim.target_bounds(sim.Config(currency='fiat'), sim.State(), 3.0)[1], 25)

    def test_drift_matches_the_script(self):
        sim = self.sim
        for currency, speed in (('fiat', 1), ('digital', 2)):
            cfg = sim.Config(currency=currency, mode=sim.MODE_NOTHING)
            for inflation in (2.0, 7.0, 50.0):
                for rate, target in ((25, 50), (50, 25), (3, 4), (5, 4.5), (0, 60), (40, 2)):
                    got = sim.drift_toward(cfg, sim.State(inflation=inflation), rate, target)
                    want = Drift(speed=speed, inflation=inflation).step(rate, target)
                    self.assertAlmostEqual(got, want, places=3, msg=(currency, inflation, rate, target))

    def trap(self, tune=None, runs=24):
        """China's 2048 state (core 36, expected 32, rate and target 25), 30 years."""
        sim = self.sim
        sim.TUNE.clear()
        sim.TUNE.update(tune or {})
        original = sim.monetary_update

        def seeded(cfg, st, rng, year):
            if not getattr(st, '_trap', False):
                st._trap = True
                st.inflation_core = st.inflation = 36.0
                st.inflation_expected = 32.0
                st.policy_rate = st.policy_rate_target = st.virtual_rate = st.virtual_target = 25.0
                st.stance_gap, st.inflation_band, st.inflation_band_applied = -10.0, 5, 5
            original(cfg, st, rng, year)
        sim.monetary_update = seeded
        try:
            cfg = sim.Config(currency='fiat', mode=sim.MODE_PRICE, points=0, years=30, wage_pressure=1.1,
                             fin_law='law_universal_banking_light_prudence', deficit_mean=1.5)
            series = [sim.run_once(cfg, seed).inflation_series for seed in range(5000, 5000 + runs)]
        finally:
            sim.monetary_update = original
            sim.TUNE.clear()
        reached = sum(max(s) >= 50 for s in series)
        under10 = sorted(next((m / 12 for m, x in enumerate(s) if x < 10), 99) for s in series)
        return reached, under10[len(under10) // 2]

    def test_the_trap_escape_holds(self):
        reached, median = self.trap()
        self.assertEqual(reached, 0)
        self.assertLess(median, 18)
        # and it is #1084's dial that does it: the old one runs most of them into hyperinflation
        reached_before, _ = self.trap(self.sim.PRESETS['pre_rate_reach'])
        self.assertGreater(reached_before, 12)

    def test_stance_clamps(self):
        sim = self.sim
        for gap in (-10, -3, 0, 4, 7, 10):
            st = sim.State(stance_gap=gap)
            self.assertAlmostEqual(sim.clamped_gap_pressure(st), max(-2, min(10, gap)))
            self.assertAlmostEqual(sim.clamped_gap(st), max(-2, min(4, gap)))

    def test_pre_rate_reach_restores_the_flat_drift_and_the_shared_clamp(self):
        sim = self.sim
        sim.TUNE.update(sim.PRESETS['pre_rate_reach'])
        cfg = sim.Config(currency='fiat', mode=sim.MODE_NOTHING)
        self.assertAlmostEqual(sim.drift_toward(cfg, sim.State(), 25, 50), 25 + FLAT)
        self.assertAlmostEqual(sim.clamped_gap_pressure(sim.State(stance_gap=10)), 4)


class Text(unittest.TestCase):
    def loc(self, key):
        match = re.search(rf'^ {key}:0 "(.*)"$', LOC.read_text(encoding='utf-8-sig'), re.M)
        self.assertIsNotNone(match, key)
        return match.group(1)

    def test_tooltips_read_the_share_and_the_least_step(self):
        # The Policy Rate row no longer repeats the drift (GUI audit BNK-9,
        # 2026-10-27): the Target row beside it reads it, and the rate's row
        # points there.
        self.assertIn('$banking_dash_mon_target_label$', self.loc('banking_dash_mon_rate_tt'))
        self.assertNotIn('te_mon_drift_gap_share_pct', self.loc('banking_dash_mon_rate_tt'))
        self.assertIn("ScriptValue('te_mon_emergency_cut_factor')", self.loc('banking_dash_mon_target_tt'))
        for key in ('banking_dash_mon_target_tt', 'banking_dash_ro_rate_source_mandate'):
            text = self.loc(key)
            self.assertIn("ScriptValue('te_mon_drift_gap_share_pct')|0]%#!", text, key)
            self.assertIn("ScriptValue('te_mon_drift_step')|2]#! of a point", text, key)
            self.assertIn('never less than', text, key)

    def test_the_share_value_is_a_sixth_times_the_speed(self):
        for speed in (1, 2):
            s = Script(te_mon_drift_speed_factor=speed)
            self.assertAlmostEqual(s.number('te_mon_drift_gap_share_pct'), 100 / 6 * speed)

    def test_the_target_tooltip_reads_the_ceiling(self):
        self.assertIn("ScriptValue('te_mon_target_max')|1]%#!", self.loc('banking_dash_mon_target_tt'))

    def test_the_guide_states_the_ranges_and_the_drift(self):
        text = GUIDE.read_text(encoding='utf-8')
        top = int(constant('te_mon_target_ceiling_free'))
        self.assertIn(f'| 0% to {top}% |', text)
        self.assertIn(f'| −3% to {top}% |', text)
        self.assertIn(f'| 0% to {int(constant("te_mon_target_ceiling_gold"))}% |', text)
        self.assertNotIn('to 25% |', text)
        flat = re.sub(r'\s+', ' ', text)
        self.assertIn('a sixth of the distance', flat)


if __name__ == '__main__':
    unittest.main()
