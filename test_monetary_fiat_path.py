"""The road from a gold peg to fiat money (2026-10-05).

Three changes, each pinned on the real script through test_banking_external_tools'
small interpreter:

* A DEEP SLUMP DRAINS PEG CONFIDENCE. te_mon_peg_in_deep_slump (a Downturn or a
  Panic while the stance the bank reads is Tight or Very Tight) takes
  te_mon_peg_slump_drain off confidence a month in step 10, whatever the vault
  holds, and holds the recovery (test_peg_confidence_recovery pins the hold).
  The months-to-crisis table in monetary_policy_design.md §12.3 is checked here
  against the shipped constants, and the simulator's port against the script.
* THE SUSPENSION ENDS IN A QUESTION. Step 10 stops te_peg_suspended_months at 1
  and sends te_peg.3 once; only its options take the counter to 0 — resume at
  confidence 50, or Fiat Money where the law's own gates allow it.
* THE AI'S CURRENCY WEIGHTS. Gold weighs nothing once fiat is on offer; fiat
  weighs more while suspended, in deflation and in later eras; cooperative
  ownership joins the national bank's economic-system branch.
"""
import math
import re
import unittest

from test_banking_external_tools import ROOT, Script, definitions, parse_body

EFFECTS = 'common/scripted_effects/te_monetary_effects.txt'
TRIGGERS = 'common/scripted_triggers/te_monetary_triggers.txt'
MARKET_TRIGGERS = 'common/scripted_triggers/market_triggers.txt'
EVENTS = 'events/te_peg_events.txt'
LAWS = 'common/laws/extra_laws.txt'


class World(Script):
    """Script, with the monetary and cycle triggers loaded, laws and techs held
    as sets, and trigger_event recorded rather than refused."""

    def __init__(self, laws=(), techs=(), **inputs):
        super().__init__(**inputs)
        self.events = []
        self.laws, self.techs = set(laws), set(techs)
        raw = definitions(TRIGGERS)
        raw.update(definitions(MARKET_TRIGGERS))
        self.triggers.update({k: self.rw(v) for k, v in raw.items()})

    def rw(self, body):
        """has_law / has_technology_researched -> boolean inputs the interpreter reads."""
        out = []
        for key, op, val in body:
            if key == 'has_law':
                name = val.removeprefix('law_type:')
                self.inputs[f'__law_{name}'] = name in self.laws
                out.append((f'__law_{name}', '=', 'yes'))
            elif key == 'has_technology_researched':
                self.inputs[f'__tech_{val}'] = val in self.techs
                out.append((f'__tech_{val}', '=', 'yes'))
            elif isinstance(val, list):
                out.append((key, op, self.rw(val)))
            else:
                out.append((key, op, val))
        return out

    def weight(self, body):
        return self.value(self.rw(body))

    def execute(self, body):
        for key, _, val in body:
            if key == 'trigger_event':
                self.events.append(self.field(val, 'id'))
        super().execute([item for item in body if item[0] != 'trigger_event'])


def gold_update():
    return definitions(EFFECTS)['te_monetary_update_gold']


def find(body, predicate):
    """Depth-first: the first (index, list) whose item satisfies predicate."""
    for i, item in enumerate(body):
        if predicate(item):
            return i, body
        if isinstance(item[2], list):
            found = find(item[2], predicate)
            if found is not None:
                return found
    return None


def limit_has(item, key, val='yes'):
    return (isinstance(item[2], list) and item[0] in ('if', 'else_if')
            and (key, '=', val) in Script.field(item[2], 'limit'))


class DeepSlumpTrigger(unittest.TestCase):
    def slump(self, **vars_):
        s = World()
        s.vars.update(vars_)
        return s.check([('te_mon_peg_in_deep_slump', '=', 'yes')])

    def test_downturn_or_panic_with_a_tight_stance(self):
        for cycle in (5, 9.9, 10, 24.9):
            for band in (4, 5):
                self.assertTrue(self.slump(finance_cycle_value=cycle, te_mon_stance_band=band),
                                (cycle, band))

    def test_not_out_of_the_recession_bands(self):
        for cycle in (25, 39, 50, 90):
            self.assertFalse(self.slump(finance_cycle_value=cycle, te_mon_stance_band=5), cycle)

    def test_not_without_a_tight_stance(self):
        # Deflation alone is not enough: metallic prices rest near the band.
        for band in (1, 2, 3):
            self.assertFalse(self.slump(finance_cycle_value=10, te_mon_stance_band=band,
                                        te_inflation_band=1), band)

    def test_guarded(self):
        self.assertFalse(self.slump())
        self.assertFalse(self.slump(finance_cycle_value=10))
        self.assertFalse(self.slump(te_mon_stance_band=5))


class SlumpDrain(unittest.TestCase):
    def test_step_10_subtracts_the_drain_when_the_slump_holds(self):
        found = find(gold_update(), lambda item: limit_has(item, 'te_mon_peg_in_deep_slump'))
        self.assertIsNotNone(found)
        i, body = found
        self.assertEqual(body[i][0], 'if')
        writes = [val for key, _, val in body[i][2] if key == 'change_variable']
        self.assertEqual(writes, [[('name', '=', 'te_peg_confidence'),
                                   ('subtract', '=', 'te_mon_peg_slump_drain')]])

    def test_the_drain_comes_before_the_crisis_test(self):
        body = gold_update()
        _, branch = find(body, lambda item: limit_has(item, 'te_mon_peg_in_deep_slump'))
        keys = [key for key, _, _ in branch]
        crisis = next(i for i, (key, _, val) in enumerate(branch)
                      if key == 'if' and ('trigger_event', '=', [('id', '=', 'te_peg.1')]) in val)
        drain = next(i for i, item in enumerate(branch)
                     if limit_has(item, 'te_mon_peg_in_deep_slump'))
        self.assertLess(drain, crisis, keys)

    def test_months_to_the_crisis_threshold(self):
        """§12.3's table: a sustained deep slump, heal held, from 100 / 70 / 50."""
        s = World()
        drain = s.number('te_mon_peg_slump_drain')
        threshold = s.number('te_mon_peg_crisis_threshold')
        self.assertEqual(drain, 3)
        expected = {100: 27, 70: 17, 50: 10}
        for start, months in expected.items():
            confidence, n = start, 0
            while confidence > threshold:
                confidence -= drain
                n += 1
            self.assertEqual(n, months, start)
            self.assertEqual(n, math.ceil((start - threshold) / drain))
        # Inside the owner's 1.5-3 years from a trusted peg.
        self.assertTrue(18 <= expected[100] <= 36)

    def test_simulator_port_matches(self):
        from scripts.analysis import banking_cycle_sim as sim
        from scripts.analysis.banking_cycle_sim import Config, State, monetary_update_gold
        saved = dict(sim.TUNE)
        sim.TUNE.clear()
        self.addCleanup(lambda: (sim.TUNE.clear(), sim.TUNE.update(saved)))
        state = State(policy_rate=3.3, bank_gold=1e6, bank_gold_seeded=True,
                      peg_confidence=80, finance_cycle_value=15, stance_band=4)
        monetary_update_gold(Config(currency='gold'), state, 3)
        self.assertEqual(state.peg_confidence, 77)  # -3, and no +1 heal
        state = State(policy_rate=3.3, bank_gold=1e6, bank_gold_seeded=True,
                      peg_confidence=80, finance_cycle_value=15, stance_band=3)
        monetary_update_gold(Config(currency='gold'), state, 3)
        self.assertEqual(state.peg_confidence, 81)


class SuspensionClock(unittest.TestCase):
    """The clock at the foot of step 10: count down to 1, then ask once."""

    def setUp(self):
        body = gold_update()
        i = next(i for i, item in enumerate(body)
                 if item[0] == 'if' and ('var:te_peg_suspended_months', '>', '1')
                 in Script.field(item[2], 'limit'))
        self.clock = body[i:i + 2]
        self.assertEqual(self.clock[1][0], 'else_if')

    def tick(self, s, months=1):
        for _ in range(months):
            s.execute(self.clock)

    def test_counts_down_to_one_and_asks_once(self):
        s = World()
        s.vars['te_peg_suspended_months'] = 60
        self.tick(s, 59)
        self.assertEqual(s.vars['te_peg_suspended_months'], 1)  # the last month
        self.assertEqual(s.events, [])
        self.tick(s)                                             # month 60 asks
        self.assertEqual(s.vars['te_peg_suspended_months'], 1)
        self.assertEqual(s.events, ['te_peg.3'])
        self.assertIn('te_peg_resume_asked', s.vars)
        self.tick(s, 6)
        self.assertEqual(s.vars['te_peg_suspended_months'], 1)  # still suspended
        self.assertEqual(s.events, ['te_peg.3'])                 # not asked twice

    def test_a_lost_question_is_asked_again(self):
        s = World()
        s.vars.update(te_peg_suspended_months=1)
        self.tick(s)
        del s.vars['te_peg_resume_asked']  # the 120 days ran out unanswered
        self.tick(s)
        self.assertEqual(s.events, ['te_peg.3', 'te_peg.3'])

    def test_no_suspension_no_question(self):
        s = World()
        s.vars['te_peg_suspended_months'] = 0
        self.tick(s, 3)
        self.assertEqual(s.events, [])
        self.assertEqual(s.vars['te_peg_suspended_months'], 0)

    def test_the_old_auto_resume_is_gone(self):
        # Nothing in step 10 writes confidence 50 any more; te_peg.3 does.
        found = find(gold_update(), lambda item: item[0] == 'set_variable'
                     and ('value', '=', 'te_mon_peg_devalue_confidence') in item[2])
        self.assertIsNone(found)


class SuspensionEndEvent(unittest.TestCase):
    def setUp(self):
        self.event = definitions(EVENTS)['te_peg.3']
        self.options = [val for key, _, val in self.event if key == 'option']

    def option(self, name):
        return next(o for o in self.options if ('name', '=', name) in o)

    def test_shape(self):
        keys = [key for key, _, _ in self.event]
        self.assertNotIn('trigger', keys)  # te_peg.1's rule: step 10 is the gate
        self.assertIn('cancellation_trigger', keys)
        self.assertIn('event_image', keys)
        self.assertEqual(len(self.options), 2)

    def test_resume_is_the_default_and_restarts_at_fifty(self):
        a = self.option('te_peg.3.a')
        self.assertIn(('default_option', '=', 'yes'), a)
        s = World()
        s.vars.update(te_peg_suspended_months=1, te_peg_confidence=12, te_peg_resume_asked=1)
        s.execute(Script.field(a, 'hidden_effect'))
        self.assertEqual(s.vars['te_peg_suspended_months'], 0)
        self.assertEqual(s.vars['te_peg_confidence'], 50)
        self.assertNotIn('te_peg_resume_asked', s.vars)

    def test_fiat_needs_the_laws_own_gates_and_shows_greyed(self):
        b = self.option('te_peg.3.b')
        self.assertIn(('show_as_unavailable', '=', [('always', '=', 'yes')]), b)
        self.assertIn(('activate_law', '=', 'law_type:law_fiat_currency'), b)
        trigger = Script.field(b, 'trigger')
        cases = {
            (('law_national_bank',), ('keynesian_economics',), False): True,
            ((), ('keynesian_economics',), False): False,
            (('law_national_bank',), (), False): False,
            (('law_national_bank',), ('keynesian_economics',), True): False,
        }
        for (laws, techs, dollarised), allowed in cases.items():
            s = World(laws=laws, techs=techs)
            if dollarised:
                s.vars['te_mon_dollarised'] = 1
            self.assertEqual(s.check(s.rw(trigger)), allowed, (laws, techs, dollarised))

    def test_fiat_ends_the_clock_and_the_lost_gold_bonus(self):
        b = self.option('te_peg.3.b')
        s = World()
        s.vars.update(te_peg_suspended_months=1, te_peg_resume_asked=1)
        s.execute(Script.field(b, 'hidden_effect'))
        self.assertEqual(s.vars['te_peg_suspended_months'], 0)
        self.assertNotIn('te_peg_resume_asked', s.vars)
        removes = [val for key, _, val in b if key == 'if'
                   and ('remove_modifier', '=', 'te_mon_peg_credibility_lost') in val]
        self.assertTrue(removes)

    def test_every_option_explains_itself(self):
        # silent_variable: the writes are hidden, so each option says what it does.
        for option in self.options:
            self.assertIn('custom_tooltip', [key for key, _, _ in option])


def block(text, name, start=0):
    """The inside of the first `name = { ... }` at or after start."""
    i = re.compile(r'(?m)^\s*' + re.escape(name) + r'\s*=\s*\{').search(text, start)
    assert i, name
    depth = 0
    for j in range(i.end() - 1, len(text)):
        depth += {'{': 1, '}': -1}.get(text[j], 0)
        if depth == 0:
            return text[i.end():j], i.end()
    raise AssertionError(name)


def law_weight(law):
    """A law's ai_enact_weight_modifier, parsed alone: the law files' bare lists
    (unlocking_technologies) are beyond the interpreter's key = value parser."""
    text = (ROOT / LAWS).read_text(encoding='utf-8-sig')
    _, at = block(text, law)
    inner, _ = block(text, 'ai_enact_weight_modifier', at)
    return parse_body(inner)


class CurrencyWeights(unittest.TestCase):
    def setUp(self):
        self.gold = law_weight('law_gold_standard')
        self.fiat = law_weight('law_fiat_currency')
        self.bank = law_weight('law_national_bank')

    def test_gold_weighs_nothing_once_fiat_is_on_offer(self):
        cases = {
            ((), ()): 100,
            (('law_national_bank',), ()): 100,
            ((), ('keynesian_economics',)): 100,
            (('law_national_bank',), ('keynesian_economics',)): 0,
            (('law_fiat_currency',), ()): 0,
            (('law_digital_currency',), ()): 0,
        }
        for (laws, techs), weight in cases.items():
            self.assertEqual(World(laws=laws, techs=techs).weight(self.gold), weight, (laws, techs))

    def test_fiat_rises_while_suspended_in_deflation_and_by_era(self):
        self.assertEqual(World().weight(self.fiat), 200)
        s = World()
        s.vars['te_peg_suspended_months'] = 12
        self.assertEqual(s.weight(self.fiat), 500)
        s = World()
        s.vars['te_inflation_band'] = 1
        self.assertEqual(s.weight(self.fiat), 400)
        s.vars['te_inflation_band'] = 2
        self.assertEqual(s.weight(self.fiat), 200)
        eras = ('television_broadcasting', 'containerization', 'globalization')
        for n in range(1, 4):
            self.assertEqual(World(techs=eras[:n]).weight(self.fiat), 200 + 100 * n)
        s = World(techs=eras)
        s.vars.update(te_peg_suspended_months=12, te_inflation_band=1)
        self.assertEqual(s.weight(self.fiat), 1000)

    def test_cooperative_ownership_joins_the_banks_economic_systems(self):
        # A minor, out of debt, in no power bloc: 600 base, +400 for the
        # economic systems that presuppose someone managing credit.
        def bank_weight(law):
            s = World(laws=(law,), scaled_debt=0, country_rank=1)
            s.inputs['rank_value:major_power'] = 3
            return s.weight([item for item in self.bank
                             if not (item[0] == 'if' and any(
                                 k == 'power_bloc' for k, _, _ in Script.field(item[2], 'limit')))])
        for law in ('law_interventionism', 'law_laissez_faire', 'law_command_economy',
                    'law_cooperative_ownership'):
            self.assertEqual(bank_weight(law), 1000, law)
        self.assertEqual(bank_weight('law_agrarianism'), 600)


if __name__ == '__main__':
    unittest.main()
