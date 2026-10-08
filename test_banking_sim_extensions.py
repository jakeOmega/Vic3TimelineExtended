"""Simulator parity with real crash effects, alternate buttons and pool values."""
import copy
import hashlib
import itertools
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.analysis import banking_cycle_sim as S
from test_banking_crash_no_raise import run as run_crash
from test_banking_external_tools import Script, definitions

ROOT = Path(__file__).resolve().parent


class Oracle(Script):
    """Independent existing interpreter with the ce/cw law/JE scope reads."""
    def __init__(self, cfg, state):
        super().__init__()
        self.values.update(definitions('common/script_values/extra_script_values.txt'))
        self.triggers.update(definitions('common/scripted_triggers/market_triggers.txt'))
        self.cfg, self.state = cfg, state
        self.vars.update(finance_cycle_value=state.finance_cycle_value,
                         finance_cycle_momentum=state.finance_cycle_momentum,
                         bubble_pressure=state.bubble_pressure)
        self.inputs.update({
            'modifier:country_banking_intervention_max_add': S.intervention_points(cfg, state),
            '"modifier:country_banking_intervention_max_add"': S.intervention_points(cfg, state),
            'gold_reserves': max(0, state.treasury_balance) * cfg.pool_weekly_income,
            'investment_pool': state.pool_balance * cfg.pool_weekly_income,
            'in_default': state.scaled_debt >= 1,
            'has_healthy_economy': state.scaled_debt <= .6,
            'always': True,
        })

    def check(self, body, mode='AND'):
        rewritten = []
        for key, op, val in body:
            if key == 'has_law':
                name = 'oracle_law'
                self.inputs[name] = val == 'law_type:' + S.ECONOMY_LAWS.get(self.cfg.economy, '')
                rewritten.append((name, '=', 'yes'))
            elif key in ('je:je_banking_cycle', 'has_modifier') or key.startswith('banking_tool_'):
                name = 'oracle_' + key
                if key == 'je:je_banking_cycle':
                    answer = self.check(val)
                elif key == 'has_modifier':
                    answer = val in {S.ALT_TOOL_MODIFIER_NAMES[t] for t in self.state.tools}
                else:
                    answer = self.check(self.triggers[key]) == (val == 'yes')
                self.inputs[name] = answer
                rewritten.append((name, '=', 'yes'))
            elif key == 'scope:banking_crash_origin_country':
                prior = self.vars.get('crash_severity')
                self.vars['crash_severity'] = self.foreign
                self.inputs['oracle_foreign'] = self.check(val)
                if prior is None:
                    self.vars.pop('crash_severity')
                else:
                    self.vars['crash_severity'] = prior
                rewritten.append(('oracle_foreign', '=', 'yes'))
            else:
                rewritten.append((key, op, val))
        return super().check(rewritten, mode)

    def execute(self, body):
        expanded = []
        for key, op, val in body:
            if key == 'random_list':
                entries = []
                for weight, _, effect in val:
                    modifiers = [v for k, _, v in effect if k == 'modifier']
                    amount = float(weight)
                    for modifier in modifiers:
                        amount = self.value(modifier, amount)
                    entries.append((amount, [item for item in effect if item[0] != 'modifier']))
                roll = next(self.rolls) * sum(w for w, _ in entries)
                for weight, effect in entries:
                    if roll < weight:
                        name = 'oracle_roll_' + str(len(self.effects))
                        self.effects[name] = effect
                        expanded.append((name, '=', 'yes'))
                        break
                    roll -= weight
            else:
                expanded.append((key, op, val))
        super().execute(expanded)


class Draws:
    def __init__(self, foreign, *rolls):
        self.foreign, self.rolls = foreign, iter(rolls)

    def choice(self, choices):
        assert self.foreign in choices
        return self.foreign

    def random(self):
        return next(self.rolls)


class Extensions(unittest.TestCase):
    def setUp(self):
        old = dict(S.TUNE)
        S.TUNE.clear()
        self.addCleanup(lambda: (S.TUNE.clear(), S.TUNE.update(old)))

    def test_imported_effect_grid_matches_actual_script_for_all_laws(self):
        for economy, value, momentum, bubble, severity in itertools.product(
                ('market', 'command', 'coop'), (0, 2, 5, 12, 30, 50, 90),
                (-8, -5, -3, 0, 4), (0, 30, 100), (None, 0, 19.9, 20, 40, 60, 80, 100)):
            cfg = S.Config(economy=economy)
            state = S.State(economy=economy, finance_cycle_value=value,
                            finance_cycle_momentum=momentum, bubble_pressure=bubble)
            variables = dict(finance_cycle_value=value, finance_cycle_momentum=momentum,
                             bubble_pressure=bubble, contagion_crash=int(severity is not None),
                             crash_severity=severity or 0)
            laws = (S.ECONOMY_LAWS[economy],) if economy != 'market' else ()
            actual = run_crash('apply_banking_contagion_effects', variables, laws).vars
            S.apply_imported_effects(cfg, state, severity)
            self.assertEqual(state.finance_cycle_value, actual['finance_cycle_value'])
            self.assertEqual(state.finance_cycle_momentum, actual['finance_cycle_momentum'])
            self.assertEqual(state.bubble_pressure, actual['bubble_pressure'])

    def test_imported_chance_severity_and_records(self):
        effect = definitions('common/scripted_effects/banking_cycle_effects.txt')['banking_contagion_crash_check']
        for economy, foreign, bubble in itertools.product(
                ('market', 'command', 'coop'), (10, 30, 50, 70, 90), (0, 40, 100)):
            cfg = S.Config(economy=economy)
            state = S.State(economy=economy, finance_cycle_value=12,
                            finance_cycle_momentum=-6, bubble_pressure=bubble)
            boost = 30 if foreign >= 80 else 20 if foreign >= 60 else 10 if foreign >= 40 else 5
            weight = (bubble + boost) * S.ECONOMY_CRASH_MULT['banking_contagion_chance_economy_mult'][economy]
            probability = weight / (weight + 100)
            oracle = Oracle(cfg, state)
            oracle.foreign = foreign
            oracle.inputs.update(te_mon_has_effective_backstop=False,
                                 **{'modifier:country_banking_crash_chance_mult': 0})
            actual_weight = oracle.value(Script.field(Script.field(Script.field(effect, 'random_list'), '0'), 'modifier'))
            self.assertEqual(weight, actual_weight)
            oracle.rolls = iter((probability - 1e-8, .95))
            oracle.execute(effect)
            self.assertTrue(S.imported_crash(cfg, state, Draws(foreign, probability - 1e-8, .95), 17))
            record = state.imported_crashes[0]
            severity_boost = 20 if foreign >= 80 else 15 if foreign >= 60 else 10 if foreign >= 40 else 5
            expected = min(100, (bubble * S.K.sv('banking_crash_severity_scale_value') + severity_boost)
                           * 2 * S.ECONOMY_CRASH_MULT['banking_contagion_severity_economy_mult'][economy])
            self.assertEqual(record.severity, expected)
            self.assertEqual(record.severity, oracle.vars['crash_severity'])
            self.assertEqual(record.month, 17)
            self.assertEqual(state.crashes, [])
            self.assertIsNone(state.pending_recovery)
            self.assertGreaterEqual(record.value_drop, 0)
            self.assertGreaterEqual(record.momentum_drop, 0)
            self.assertFalse(S.imported_crash(cfg, S.State(economy=economy, bubble_pressure=bubble),
                                             Draws(foreign, probability + 1e-8), 18))

    def test_import_rate_and_separate_summary(self):
        cfg = S.Config(years=100, imported_crash_years=10)
        # Arrival draws alone: annualized expectation 10 per century.
        arrivals = sum(random.Random(i).random() < 1 / 120 for i in range(120000))
        self.assertAlmostEqual(arrivals / 100, 10, delta=1)
        state = S.run_once(S.Config(years=2, imported_crash_years=1 / 12), 42)
        self.assertEqual(len(state.imported_crashes) + len(state.imported_scares), 24)
        summary = S.extension_summary(cfg, [state])
        self.assertEqual(summary['imported_crashes']['per_century'], len(state.imported_crashes))

    def test_alternate_roster_covers_every_registered_button_and_modifier(self):
        je = (ROOT / 'common/journal_entries/je_banking.txt').read_text(encoding='utf-8-sig')
        import re
        buttons = set(re.findall(r'scripted_button = ((?:ce|cw)_\w+)', je))
        modeled = set(S.ALT_TOOL_BUTTONS.values()) | set(S.TRANSFER_BUTTONS)
        modeled |= {b[:3] + 'disable_' + b[3:] for b in S.ALT_TOOL_BUTTONS.values()}
        self.assertEqual(buttons, modeled)
        effects = definitions('common/scripted_effects/banking_policy_effects.txt')
        for tool, button in S.ALT_TOOL_BUTTONS.items():
            effect = effects['banking_effect_' + button]
            je_block = Script.field(effect, 'je:je_banking_cycle')
            modifier = Script.field(Script.field(je_block, 'add_modifier'), 'name')
            self.assertEqual(S.ALT_TOOL_MODIFIER_NAMES[tool], modifier)
            self.assertEqual(S.TOOL_COST[tool], -S.K.modifier(modifier)['country_banking_intervention_max_add'])

    def test_all_alternate_weights_and_holds_match_independent_interpreter(self):
        buttons = definitions('common/scripted_buttons/banking_alt_economy_buttons.txt')
        for economy, value, momentum, bubble in itertools.product(
                ('command', 'coop'), (5, 15, 30, 50, 65, 80, 95), (-4, -1, 0, 4), (0, 30, 55, 80)):
            cfg = S.Config(economy=economy, points=8, pool=True)
            state = S.State(economy=economy, finance_cycle_value=value,
                            finance_cycle_momentum=momentum, bubble_pressure=bubble)
            state.tools = {'ce_allocation', 'ce_target_cut'} if economy == 'command' else {'cw_mutual_aid', 'cw_credit'}
            oracle = Oracle(cfg, state)
            for disable in (False, True):
                scores = S.alternate_scores(cfg, state, disable)
                for tool, got in scores.items():
                    button = S.ALT_TOOL_BUTTONS[tool]
                    if disable:
                        button = button[:3] + 'disable_' + button[3:]
                    expected = oracle.value(Script.field(buttons[button], 'ai_chance'))
                    self.assertEqual(got, expected, (economy, value, momentum, bubble, button))
            for tool, held in S.ai_holds(cfg, state).items():
                self.assertEqual(held, oracle.check(oracle.triggers['banking_ai_hold_' + S.ALT_TOOL_BUTTONS[tool]]))

    def test_economy_damping_is_shared_with_real_script_values(self):
        effects = (ROOT / 'common/scripted_effects/banking_cycle_effects.txt').read_text(encoding='utf-8-sig')
        for name, values in S.ECONOMY_CRASH_MULT.items():
            self.assertIn('multiply = ' + name, effects)
            for economy, multiplier in values.items():
                oracle = Oracle(S.Config(economy=economy), S.State())
                self.assertEqual(multiplier, oracle.number(name))
        market = S.crash_weight(S.Config(), S.State(finance_cycle_value=90, bubble_pressure=70))
        for economy, factor in (('command', .35), ('coop', .65)):
            self.assertAlmostEqual(S.crash_weight(S.Config(economy=economy),
                S.State(economy=economy, finance_cycle_value=90, bubble_pressure=70)), market * factor)

    def test_phases_inertia_and_administered_money(self):
        for economy in ('market', 'command', 'coop'):
            cfg = S.Config(economy=economy)
            state = S.State(economy=economy, finance_cycle_value=90, bubble_pressure=80)
            S.apply_phase_modifiers(cfg, state)
            expected = S.ECONOMY_PHASE_MODIFIERS[economy][S.FRENZY]['country_bubble_pressure_monthly_add']
            self.assertEqual(S.modifier_sum(state, 'country_bubble_pressure_monthly_add'), expected)
            self.assertEqual(state.active_inertia_key is None, economy == 'command')
        state = S.State(inflation=20, inflation_expected=30, stance_gap=-2)
        S.monetary_update(S.Config(economy='command'), state, random.Random(1), 90)
        self.assertEqual((state.policy_rate, state.inflation, state.inflation_expected, state.stance_gap), (3, 0, 0, 0))
        self.assertFalse(S.has_dial(S.Config(economy='command')))
        for economy, expected in (('command', -.5), ('coop', -.25)):
            self.assertEqual(S.law_modifier_sum(S.Config(economy=economy), 'country_banking_random_momentum_mult'), expected)

    def test_held_tools_survive_and_pool_is_observational_for_coop(self):
        cfg = S.Config(economy='coop', points=8, hold_tools=('cw_capital_plan', 'cw_credit'), years=3)
        state = S.run_once(cfg, 123)
        self.assertEqual(state.tools, set(cfg.hold_tools))
        self.assertEqual(sum(state.tool_lifts.values()), 0)
        pool_cfg = copy.copy(cfg)
        pool_cfg.pool = True
        observed = S.run_once(pool_cfg, 123)
        self.assertEqual(state.value_series, observed.value_series)
        self.assertEqual(state.crashes, observed.crashes)
        self.assertEqual(len(observed.pool_series), 36)
        self.assertTrue(all(x >= 0 for x in observed.pool_series))

    def test_pool_income_share_and_floor_match_real_value(self):
        cfg = S.Config(economy='coop', pool=True)
        state = S.State(economy='coop', pool_balance=.01, active_phase=S.PANIC)
        oracle = Oracle(cfg, state)
        oracle.inputs.update(investment_pool_gross_income=1000,
                             **{'modifier:country_weekly_investment_pool_mult': S.modifier_sum(state, 'country_weekly_investment_pool_mult')})
        gain = S.RULES.evaluate(S.RULES.values['investment_pool_banking_cycle_income_add'], S.alternate_read(cfg, state))
        self.assertEqual(gain, oracle.number('investment_pool_banking_cycle_income_add'))
        self.assertGreaterEqual(gain, -10)
        S.advance_pool(cfg, state)
        self.assertGreaterEqual(state.pool_balance, 0)

    def test_command_transfers_conserve_money_and_recalibrate(self):
        cfg = S.Config(economy='command', pool=True)
        state = S.State(economy='command', gdp=1e7, treasury_balance=100, pool_balance=10)
        total = state.treasury_balance + state.pool_balance
        S.transfer_pool(cfg, state, 'ce_invest_pool_inject')
        self.assertEqual(state.pool_balance, 30)  # 0.2% of GDP = 20 income units
        self.assertEqual(state.treasury_balance + state.pool_balance, total)
        S.transfer_pool(cfg, state, 'ce_invest_pool_withdraw')
        S.transfer_pool(cfg, state, 'ce_invest_pool_withdraw')
        self.assertEqual(state.pool_balance, 0)  # second withdrawal capped to pool
        self.assertEqual(state.treasury_balance + state.pool_balance, total)
        self.assertEqual(state.pool_balance_add, -1)
        # At equilibrium, 52 weeks of unchanged income/spending do not drift.
        settled = S.State(economy='command')
        for _ in range(12):
            S.advance_pool(cfg, settled)
        self.assertEqual(settled.pool_balance, 24)

    def test_configuration_rejects_invalid_arms(self):
        for kw in ({'imported_crash_years': -.1}, {'imported_crash_years': .01},
                   {'imported_crash_years': float('nan')}, {'pool_spend_cap': .5},
                   {'economy': 'coop', 'points': 2, 'hold_tools': ('cw_credit',)},
                   {'hold_tools': ('cw_credit',), 'points': 8}):
            with self.assertRaises(ValueError):
                S.Config(**kw)

    def test_default_market_json_is_byte_identical_to_before_extensions(self):
        # Captured from main 028ea9cf, with PYTHONHASHSEED=0 (tool sets sum floats).
        # Keys added to every row since then are dropped before hashing; the
        # sample never opens the Emergency Liquidity Program, so §25 moves nothing
        # else in it.
        added_since_capture = ('eliq_wind_downs_per_century',)
        # Cells added since then are dropped too: the inflation-targeting
        # mandate (#799) adds a mode, and leaves every older cell unchanged.
        modes_added_since_capture = ('inflation',)
        with tempfile.TemporaryDirectory() as temp:
            result = Path(temp) / 'baseline.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/analysis/banking_cycle_sim.py'),
                            '--runs', '2', '--years', '10', '--only', 'fiat',
                            '--points', '0,4,8', '--jobs', '1', '--json', str(result)],
                           env={**os.environ, 'PYTHONHASHSEED': '0'}, check=True,
                           capture_output=True)
            rows = [row for row in json.loads(result.read_text(encoding='utf-8'))
                    if row['mode'] not in modes_added_since_capture]
            for row in rows:
                for key in added_since_capture:
                    row.pop(key)
            self.assertEqual(hashlib.sha256(json.dumps(rows, indent=2).encode()).hexdigest(),
                             'c779b9073eed7929d14b6b59410b8764acd7c87563600d2927dd80a123272336')


if __name__ == '__main__':
    unittest.main()
