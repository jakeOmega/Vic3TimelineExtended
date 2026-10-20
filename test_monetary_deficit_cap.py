"""The bond-finance deficit term's cap and gates, and the dollarised regime pull (#1084).

Owner, 2026-10-20: `te_mon_pressure_deficit` is capped at
`te_mon_deficit_pressure_cap` (1.5pp) before the war doubling, so 3pp at war,
and is 0 for a country that cannot borrow: one that is dollarised (no currency
of its own to inflate) or `in_default` (debt past the credit limit). A
dollarised country's regime pull is to the anchor its expectations are pinned
at (decision K), not to zero, so its core settles near 2 + P/2.

Pinned here:

* the real script values, run through the small interpreter in
  test_banking_external_tools: the cap, the war doubling of the cap, the
  tolerance, the two gates and the guarded read;
* the cap's place in the block (after the coefficient, before the doubling);
* the 52 in te_mon_deficit_annualise_factor, which #1084 settled (weekly
  flows) and which must not be flipped;
* the regime pull by regime, and the fixed point it gives a dollarised country;
* the simulator's port (scripts/analysis/banking_cycle_sim.py) and its
  `pre_deficit_cap` preset;
* the player guide's figures for the cap.
"""
import re
import unittest
from pathlib import Path

from test_banking_external_tools import Script, definitions

ROOT = Path(__file__).resolve().parent
VALUES = 'common/script_values/te_monetary_script_values.txt'
GUIDE = ROOT / 'docs/player_guide/04-banking.md'


def constant(name):
    return float(dict((k, v) for k, _, v in definitions(VALUES)[name])['value'])


class Monetary(Script):
    """The interpreter, reading `has_law_or_variant` from a set of laws."""

    def __init__(self, laws=(), **inputs):
        stubs = dict(te_mon_is_dollarised=False, in_default=False, te_mon_is_metallic=False,
                     te_mon_inflation_anchor=2.0)
        stubs.update(inputs)
        super().__init__(**stubs)
        self.laws = set(laws)

    def check(self, body, mode='AND'):
        laws = [item for item in body if item[0] == 'has_law_or_variant']
        if not laws:
            return super().check(body, mode)
        rest = [item for item in body if item[0] != 'has_law_or_variant']
        answers = [val.removeprefix('law_type:') in self.laws for _, _, val in laws]
        if rest:
            answers.append(super().check(rest, mode))
        if mode == 'NOT':
            return not any(answers)
        return any(answers) if mode == 'OR' else all(answers)


def deficit(pct, **inputs):
    s = Monetary(**inputs)
    if pct is not None:
        s.vars['te_mon_deficit_pct'] = pct
    return s.number('te_mon_pressure_deficit')


class DeficitTerm(unittest.TestCase):
    def setUp(self):
        self.coeff = constant('te_mon_deficit_coeff')
        self.tolerance = constant('te_mon_deficit_tolerance')
        self.cap = constant('te_mon_deficit_pressure_cap')

    def test_the_owner_s_numbers(self):
        self.assertEqual(self.cap, 1.5, 'retuned: edit the player guide, design §9.1 and §21')
        self.assertEqual(self.coeff, 0.3)
        self.assertEqual(self.tolerance, 1)

    def test_below_the_cap_it_is_the_old_term(self):
        for pct in (1.5, 3, 5.5):
            want = self.coeff * (pct - self.tolerance)
            self.assertLess(want, self.cap)
            self.assertAlmostEqual(deficit(pct), want, msg=pct)
            self.assertAlmostEqual(deficit(pct, at_war=True), 2 * want, msg=pct)

    def test_inside_the_tolerance_or_in_surplus_it_is_zero(self):
        for pct in (-20, 0, 0.5, 1):
            self.assertEqual(deficit(pct), 0, pct)
            self.assertEqual(deficit(pct, at_war=True), 0, pct)

    def test_capped_at_one_and_a_half_points(self):
        reach = self.tolerance + self.cap / self.coeff  # 6% of GDP
        self.assertAlmostEqual(reach, 6)
        for pct in (reach, 8, 100, 10_000):
            self.assertAlmostEqual(deficit(pct), self.cap, msg=pct)

    def test_war_doubles_the_cap(self):
        for pct in (6, 15, 567, 10_000):
            self.assertAlmostEqual(deficit(pct, at_war=True), 2 * self.cap, msg=pct)

    def test_no_term_while_dollarised(self):
        for pct in (3, 100, 567):
            self.assertEqual(deficit(pct, te_mon_is_dollarised=True), 0, pct)
            self.assertEqual(deficit(pct, te_mon_is_dollarised=True, at_war=True), 0, pct)

    def test_no_term_in_default(self):
        for pct in (3, 100, 567):
            self.assertEqual(deficit(pct, in_default=True), 0, pct)
            self.assertEqual(deficit(pct, in_default=True, at_war=True), 0, pct)

    def test_no_variable_reads_zero(self):
        self.assertEqual(deficit(None), 0)
        self.assertEqual(deficit(None, at_war=True), 0)

    def test_the_cap_sits_after_the_coefficient_and_before_the_doubling(self):
        (gate,) = [val for key, _, val in definitions(VALUES)['te_mon_pressure_deficit'] if key == 'if']
        keys = [key for key, _, _ in gate]
        self.assertLess(keys.index('multiply'), keys.index('max'))  # a bound on pp, not on % of GDP
        self.assertLess(keys.index('max'), keys.index('if'))        # the war doubling comes after it
        (limit,) = [val for key, _, val in gate if key == 'limit']
        self.assertIn(('in_default', '=', 'no'), limit)
        self.assertIn(('NOT', '=', [('te_mon_is_dollarised', '=', 'yes')]), limit)

    def test_the_annualise_factor_stays_at_52(self):
        # #1084 settled §17 check 12 from saves: the flows are weekly. A country in
        # default reads hundreds legitimately; the cap answers it, not this.
        self.assertEqual(constant('te_mon_deficit_annualise_factor'), 52)


def pull(core, laws=(), **inputs):
    s = Monetary(laws=laws, **inputs)
    s.vars['te_inflation_core'] = core
    return s.number('te_mon_pressure_regime_pull')


class RegimePull(unittest.TestCase):
    def test_by_regime(self):
        for core in (-3, 0, 10, 57):
            self.assertAlmostEqual(pull(core, te_mon_is_metallic=True), -core, msg=core)
            self.assertAlmostEqual(pull(core, te_mon_is_dollarised=True), -(core - 2), msg=core)
            self.assertAlmostEqual(pull(core, laws={'law_decentralized_cryptocurrency'}), -(core + 1), msg=core)
            self.assertEqual(pull(core, laws={'law_fiat_currency'}), 0, core)

    def test_metal_wins_over_dollarisation_and_dollarisation_over_crypto(self):
        both = dict(te_mon_is_metallic=True, te_mon_is_dollarised=True, te_mon_inflation_anchor=0.0)
        self.assertAlmostEqual(pull(10, **both), -10)
        self.assertAlmostEqual(pull(10, laws={'law_decentralized_cryptocurrency'}, te_mon_is_dollarised=True), -8)

    def test_the_dollarised_pull_reads_the_anchor_value(self):
        # te_mon_inflation_anchor, as decision K's pin does, not a literal 2
        self.assertAlmostEqual(pull(10, te_mon_is_dollarised=True, te_mon_inflation_anchor=3.0), -7)

    def test_a_dollarised_country_settles_at_the_anchor_plus_half_its_pressure(self):
        # Step 6: core += speed x (expected + P + pull - core), expectations pinned at the anchor.
        speed = constant('te_mon_core_speed')
        for other in (0, 1.0, 3.0):
            core = 50.0
            for _ in range(600):
                total = other + pull(core, te_mon_is_dollarised=True)
                core += speed * (2 + total - core)
            self.assertAlmostEqual(core, 2 + other / 2, places=6, msg=other)


class Simulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.analysis import banking_cycle_sim as sim
        cls.sim = sim

    def tearDown(self):
        self.sim.TUNE.clear()

    def state(self, pct, war=False, dollarised=False, debt=0.2):
        st = self.sim.State()
        st.deficit_pct, st.at_war, st.dollarised, st.scaled_debt = pct, war, dollarised, debt
        return st

    def test_the_port_matches_the_script(self):
        for pct in (0.5, 3, 6, 100, 567):
            for war in (False, True):
                want = deficit(pct, at_war=war)
                self.assertAlmostEqual(self.sim.deficit_pressure(self.state(pct, war)), want, msg=(pct, war))
                self.assertEqual(self.sim.deficit_pressure(self.state(pct, war, dollarised=True)), 0)
                self.assertEqual(self.sim.deficit_pressure(self.state(pct, war, debt=1.0)), 0)

    def test_pre_deficit_cap_restores_the_uncapped_term_everywhere(self):
        self.sim.TUNE.update(self.sim.PRESETS['pre_deficit_cap'])
        for kw in ({}, {'dollarised': True}, {'debt': 1.5}):
            self.assertAlmostEqual(self.sim.deficit_pressure(self.state(567, **kw)), 0.3 * 566, msg=kw)

    def test_dollarised_pull_and_pin(self):
        sim = self.sim
        cfg = sim.Config(currency='fiat', mode=sim.MODE_PRICE)
        st = sim.State()
        st.dollarised, st.inflation_core, st.inflation, st.inflation_expected = True, 10.0, 10.0, 7.0
        base = sim.pressure_total(cfg, st, 3.0)
        sim.TUNE['dollar_pull'] = 'zero'
        self.assertAlmostEqual(sim.pressure_total(cfg, st, 3.0), base - sim.INFLATION_ANCHOR)
        sim.TUNE.clear()
        import random
        sim.monetary_update_inflation(cfg, st, random.Random(1), 3.0)
        self.assertEqual(st.inflation_expected, sim.INFLATION_ANCHOR)  # decision K


class Guide(unittest.TestCase):
    def test_the_guide_states_the_cap(self):
        text = re.sub(r'\s+', ' ', GUIDE.read_text(encoding='utf-8'))
        cap = constant('te_mon_deficit_pressure_cap')
        self.assertIn(f'A deficit adds at most {cap:g} points of pressure ({2 * cap:g} at war), '
                      'and none in default or once dollarized', text)


if __name__ == '__main__':
    unittest.main()
