"""Scenario tests execute the new script values/effects with bounded engine inputs.

This is deliberately a small interpreter, not an engine emulator: unknown syntax
fails. Treasury/modifier writes can be deferred to test same-block visibility;
variable writes are immediate, as required by the monetary system's accounting.
"""
import math
import operator
import re
import unittest
from pathlib import Path

from mod_state import split_loc_line
from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
TOOLS = ('restrict_inflows', 'sterilize_inflows', 'foreign_borrowing_limits',
         'fx_surrender', 'emergency_import_financing')


def parse_body(source):
    tokens = iter(ParadoxFileParser().tokenize(source))

    def body():
        result = []
        for key in tokens:
            if key == '}':
                return result
            op = next(tokens)
            value = next(tokens)
            result.append((key, op, body() if value == '{' else value.strip('"')))
        return result
    return body()


def definitions(path):
    return {key: value for key, _, value in parse_body((ROOT / path).read_text(encoding='utf-8-sig'))}


class Script:
    def __init__(self, *, cash=10000, deferred=False, **inputs):
        self.values = definitions('common/script_values/banking_external_values.txt')
        for file in ('te_monetary_script_values', 'te_monetary_fx_script_values'):
            self.values.update(definitions(f'common/script_values/{file}.txt'))
        self.triggers = definitions('common/scripted_triggers/banking_policy_triggers.txt')
        self.effects = definitions('common/scripted_effects/banking_external_effects.txt')
        self.effects.update(definitions('common/scripted_effects/banking_policy_effects.txt'))
        self.vars = {}
        self.tools = set()
        self.inputs = dict(gdp=1e6, gold_reserves=cash, export_reliance=.2,
                           te_mon_full_system=True, banking_is_market_economy=True,
                           journal=True, bank=True, dial=True, gold=True, crisis=True,
                           at_war=False, controls_locked=False, points=10)
        self.inputs.update(inputs)
        self.deferred = deferred
        self.cash_delta = 0
        self.pending_removals = set()
        self.shown = []

    def number(self, value):
        if isinstance(value, list):
            return self.value(value)
        if value.startswith('var:'):
            return self.vars[value[4:]]  # Fail on unguarded missing-variable reads.
        if value in self.inputs:
            return self.inputs[value]
        if value in self.values:
            return self.value(self.values[value])
        return float(value)

    def value(self, body, initial=0):
        n = initial
        matched = False
        for key, _, val in body:
            if key in ('if', 'else_if', 'else'):
                condition = key == 'else' or self.check(self.field(val, 'limit'))
                if (key == 'if' or not matched) and condition:
                    n = self.value([item for item in val if item[0] != 'limit'], n)
                    matched = True
                elif key == 'if':
                    matched = False
            elif key == 'desc':
                continue
            else:
                x = self.number(val)
                operations = {'value': lambda: x, 'add': lambda: n+x,
                              'subtract': lambda: n-x, 'multiply': lambda: n*x,
                              'divide': lambda: n/x, 'min': lambda: max(n, x),
                              'max': lambda: min(n, x)}
                n = operations[key]()
        return n

    @staticmethod
    def field(body, name):
        return next(val for key, _, val in body if key == name)

    def check(self, body, mode='AND'):
        answers = []
        for key, op, val in body:
            if key == 'text':
                continue
            if key in ('OR', 'AND', 'NOT'):
                answer = self.check(val, key)
            elif key == 'custom_tooltip' or key == 'market':
                answer = self.check(val)
            elif key == 'has_variable':
                answer = val in self.vars
            elif key == 'exists':
                answer = val == 'market'
            elif key == 'has_journal_entry':
                answer = self.inputs['journal']
            elif key == 'has_law_or_variant':
                assert val == 'law_type:law_national_bank', val
                answer = self.inputs['bank']
            elif key == 'market_exports_reliance':
                _, comp, rhs = val[0]
                answer = self.compare(self.inputs['export_reliance'], comp, self.number(rhs))
            elif key.startswith('banking_tool_') and key.endswith('_active'):
                answer = (key[len('banking_tool_'):-len('_active')] in self.tools) == (val == 'yes')
            elif key in ('te_mon_has_gold_flows', 'te_mon_has_dial', 'te_mon_in_financial_crisis',
                         'is_at_war', 'modifier:country_banking_lock_capital_controls_bool'):
                name = dict(te_mon_has_gold_flows='gold', te_mon_has_dial='dial',
                            te_mon_in_financial_crisis='crisis', is_at_war='at_war',
                            **{'modifier:country_banking_lock_capital_controls_bool': 'controls_locked'})[key]
                answer = self.inputs[name] == (val == 'yes')
            elif key == 'modifier:country_banking_intervention_max_add':
                answer = self.compare(self.inputs['points'], op, self.number(val))
            elif key in self.triggers:
                answer = self.check(self.triggers[key]) == (val == 'yes')
            elif key in self.inputs and isinstance(self.inputs[key], bool):
                answer = self.inputs[key] == (val == 'yes')
            else:
                answer = self.compare(self.number(key), op, self.number(val))
            answers.append(answer)
            # Guarded var reads and scoped conditions short circuit.
            if mode == 'AND' and not answer:
                return False
            if mode == 'OR' and answer:
                return True
        return not any(answers) if mode == 'NOT' else (any(answers) if mode == 'OR' else all(answers))

    @staticmethod
    def compare(a, op, b):
        return {'=': operator.eq, '>': operator.gt, '<': operator.lt,
                '>=': operator.ge, '<=': operator.le}[op](a, b)

    def effect(self, name):
        self.execute(self.effects[name])
        self.inputs['gold_reserves'] += self.cash_delta
        self.cash_delta = 0
        self.tools.difference_update(self.pending_removals)
        self.pending_removals.clear()

    def execute(self, body):
        matched = False
        for key, _, val in body:
            if key in ('if', 'else_if', 'else'):
                condition = key == 'else' or self.check(self.field(val, 'limit'))
                if (key == 'if' or not matched) and condition:
                    self.execute([x for x in val if x[0] != 'limit'])
                    matched = True
                elif key == 'if':
                    matched = False
            elif key == 'set_variable':
                self.vars[self.field(val, 'name')] = self.number(self.field(val, 'value'))
            elif key == 'change_variable':
                name = self.field(val, 'name')
                self.vars[name] = self.value([x for x in val if x[0] != 'name'], self.vars[name])
            elif key == 'clamp_variable':
                name = self.field(val, 'name')
                self.vars[name] = max(self.number(self.field(val, 'min')),
                                      min(self.number(self.field(val, 'max')), self.vars[name]))
            elif key == 'remove_variable':
                self.vars.pop(val, None)
            elif key == 'add_treasury':
                delta = self.number(val)
                if self.deferred:
                    self.cash_delta += delta
                else:
                    self.inputs['gold_reserves'] += delta
            elif key == 'je:je_banking_cycle':
                self.execute(val)
            elif key == 'remove_modifier':
                tool = val.removeprefix('banking_')
                if self.deferred:
                    self.pending_removals.add(tool)
                else:
                    self.tools.discard(tool)
            elif key == 'add_modifier':
                self.tools.add(self.field(val, 'name').removeprefix('banking_'))
            elif key == 'te_history_record_banking_marker':
                continue
            elif key == 'custom_tooltip':
                # Records the line the tooltip would draw; a block still runs.
                if isinstance(val, list):
                    self.shown.append(self.field(val, 'text'))
                    self.execute([x for x in val if x[0] != 'text'])
                else:
                    self.shown.append(val)
            elif key in self.effects:
                self.execute(self.effects[key])
            else:
                raise AssertionError(f'Unsupported effect {key}')


class ExternalPolicyScenarios(unittest.TestCase):
    def test_no_monetary_tools_in_simplified_mode(self):
        s = Script(te_mon_full_system=False)
        for tool in TOOLS:
            self.assertFalse(s.check(s.triggers['banking_possible_cb_'+tool]))

    def test_regime_and_law_gates(self):
        s = Script(gold=False, dial=False)
        for tool in ('sterilize_inflows', 'fx_surrender', 'restrict_inflows'):
            self.assertFalse(s.check(s.triggers['banking_possible_cb_'+tool]))
        s = Script(controls_locked=True)
        for tool in ('restrict_inflows', 'fx_surrender'):
            self.assertFalse(s.check(s.triggers['banking_external_eligible_'+tool]))
        s.inputs['at_war'] = True
        self.assertTrue(s.check(s.triggers['banking_external_eligible_restrict_inflows']))

    def test_funded_sterilization_only_offsets_positive_pressure(self):
        s = Script()
        s.effect('banking_effect_cb_sterilize_inflows')
        s.vars.update(te_gold_flow_pct=4, te_gold_flow=100)
        self.assertAlmostEqual(s.number('te_mon_pressure_gold_flow'), .5)
        s.vars.update(te_gold_flow_pct=-4, te_gold_flow=-100)
        self.assertAlmostEqual(s.number('te_mon_pressure_gold_flow'), -2)
        s.inputs['gold_reserves'] = 0
        s.effect('banking_external_monthly_update')
        self.assertNotIn('sterilize_inflows', s.tools)
        s.vars.update(te_gold_flow_pct=4, te_gold_flow=100)
        self.assertAlmostEqual(s.number('te_mon_pressure_gold_flow'), 2)

    def test_protection_matures_and_repeal_does_not_instantly_restore_risk(self):
        s = Script()
        s.tools.add('foreign_borrowing_limits')
        s.vars['te_fx_index'] = 80
        baseline = s.number('te_mon_premium_fx')
        for _ in range(24):
            s.effect('banking_external_monthly_update')
        self.assertAlmostEqual(s.number('te_mon_premium_fx'), baseline/2, places=4)
        s.effect('banking_effect_cb_disable_foreign_borrowing_limits')
        self.assertAlmostEqual(s.number('te_mon_premium_fx'), baseline/2, places=4)
        for _ in range(24):
            s.effect('banking_external_monthly_update')
        self.assertAlmostEqual(s.number('te_mon_premium_fx'), baseline)

    def test_purchase_conserves_cash_and_never_creates_hot_money(self):
        for cash, room, exports in ((100, 10000, .4), (10000, 100, .4), (10000, 10000, 0)):
            s = Script(cash=cash, export_reliance=exports)
            s.tools.add('fx_surrender')
            s.vars.update(te_bank_gold=200000-room, te_gold_hot_money=3000)
            initial = s.inputs['gold_reserves']+s.vars['te_bank_gold']
            s.effect('banking_external_purchase_reserves')
            self.assertEqual(initial, s.inputs['gold_reserves']+s.vars['te_bank_gold'])
            self.assertGreaterEqual(s.inputs['gold_reserves'], 0)
            self.assertLessEqual(s.vars['te_bank_gold'], 200000)
            self.assertEqual(s.vars['te_gold_hot_money'], 3000)
            if exports == 0:
                self.assertEqual(s.inputs['gold_reserves'], cash)

    def test_combined_monthly_bills_never_overdraw_even_with_deferred_treasury(self):
        for deferred in (False, True):
            for cash in (0, 99, 100, 550, 600, 1000):
                s = Script(cash=cash, deferred=deferred)
                s.tools.update(('sterilize_inflows', 'emergency_import_financing'))
                s.effect('banking_external_monthly_update')
                self.assertGreaterEqual(s.inputs['gold_reserves'], 0)
                if cash < 600:
                    self.assertNotIn('emergency_import_financing', s.tools)

    def test_import_cost_escalates_caps_and_cannot_be_reset_by_toggling(self):
        s = Script(cash=1e6)
        s.tools.add('emergency_import_financing')
        for _ in range(30):
            s.effect('banking_external_monthly_update')
        self.assertEqual(s.number('banking_external_import_cost'), 1000)
        s.effect('banking_effect_cb_disable_emergency_import_financing')
        s.effect('banking_effect_cb_emergency_import_financing')
        self.assertEqual(s.number('banking_external_import_cost'), 1000)
        s.inputs['crisis'] = False
        s.effect('banking_external_monthly_update')
        self.assertNotIn('emergency_import_financing', s.tools)
        for _ in range(12):
            s.effect('banking_external_monthly_update')
        self.assertEqual(s.number('banking_external_import_cost'), 500)

    def test_regime_loss_cleans_up_gold_tools(self):
        s = Script(gold=False)
        s.tools.update(('sterilize_inflows', 'fx_surrender'))
        s.effect('banking_external_monthly_update')
        self.assertFalse(s.tools)

    def test_flow_restriction_halves_inflows_but_does_not_trap_exiting_gold(self):
        from scripts.analysis.banking_cycle_sim import Config, State, monetary_update_gold
        cfg = Config(currency='gold', points=6)
        for gap in (2, -2, 0):
            plain = State(policy_rate=3+gap, bank_gold=1e6, bank_gold_seeded=True,
                          gold_hot_money=100000)
            restricted = State(policy_rate=3+gap, bank_gold=1e6, bank_gold_seeded=True,
                               gold_hot_money=100000, tools={'restrict_inflows'})
            monetary_update_gold(cfg, plain, 3)
            monetary_update_gold(cfg, restricted, 3)
            expected = plain.gold_flow/2 if gap > 0 else plain.gold_flow
            self.assertAlmostEqual(restricted.gold_flow, expected)
            self.assertAlmostEqual(restricted.gold_hot_money,
                                   100000+restricted.gold_flow)

    def test_new_flow_tools_are_unavailable_in_simplified_simulations(self):
        from scripts.analysis.banking_cycle_sim import Config, State, tool_possible
        cfg = Config(currency='gold', points=6, simplified=True)
        for tool in ('restrict_inflows', 'sterilize_inflows'):
            self.assertFalse(tool_possible(cfg, State(), tool))

    def test_existing_stocks_survive_monthly_initialization(self):
        s = Script()
        s.vars.update(banking_external_fx_protection=.4, banking_external_import_months=10)
        s.tools.add('foreign_borrowing_limits')
        s.effect('banking_external_monthly_update')
        self.assertGreater(s.vars['banking_external_fx_protection'], .4)
        self.assertEqual(s.vars['banking_external_import_months'], 9)

    def test_export_credit_and_all_new_rows_are_in_external_category(self):
        gui = (ROOT/'gui/journal_entry_widgets/banking_dashboard_widget.gui').read_text(encoding='utf-8-sig')
        external = gui.split('### External & Currency', 1)[1].split('### Crisis Response', 1)[0]
        for tool in (*TOOLS, 'export_credit_facility'):
            self.assertIn("banking_dash_enable_cb_"+tool, external)
        self.assertNotIn('banking_dash_enable_cb_export_credit_facility',
                         gui.split('### Directed Credit', 1)[1].split('### External & Currency', 1)[0])


def english_loc():
    loc = {}
    for path in sorted((ROOT/'localization/english').glob('*.yml')):
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            parsed = split_loc_line(line)
            if parsed:
                loc[parsed[0]] = parsed[1]
    return loc


def tooltip_keys(effects, body):
    """Every custom_tooltip key an effect body can draw, in any branch, through helpers."""
    keys = []
    for key, _, val in body:
        if key == 'custom_tooltip':
            keys.append(next(v for k, _, v in val if k == 'text') if isinstance(val, list) else val)
        elif isinstance(val, list):
            keys += tooltip_keys(effects, val)
        elif key in effects and val == 'yes':
            keys += tooltip_keys(effects, effects[key])
    return keys


# The tools whose monthly pulse does work their modifier does not carry, and the
# not-a-modifier lines each effect draws (see the header of
# common/scripted_effects/banking_policy_effects.txt).
NONMOD_LINES = {
    'banking_effect_cb_open_market_ops': ('banking_nonmod_open_market_ops_tt',),
    'banking_effect_cb_capital_controls_outflow': ('banking_nonmod_capital_controls_tt',
                                                   'banking_nonmod_capital_controls_fatigue_tt',
                                                   'banking_nonmod_war_end_lift_tt'),
    'banking_effect_cb_disable_capital_controls_outflow': ('banking_nonmod_capital_controls_off_tt',),
    'banking_effect_cb_restrict_inflows': ('banking_nonmod_restrict_inflows_tt',
                                           'banking_nonmod_war_end_lift_tt'),
    'banking_effect_cb_sterilize_inflows': ('banking_nonmod_sterilize_inflows_tt',),
    'banking_effect_cb_foreign_borrowing_limits': ('banking_nonmod_foreign_borrowing_limits_tt',),
    'banking_effect_cb_disable_foreign_borrowing_limits': ('banking_nonmod_foreign_borrowing_limits_off_tt',),
    'banking_effect_cb_fx_surrender': ('banking_nonmod_fx_surrender_tt', 'banking_nonmod_war_end_lift_tt'),
    'banking_effect_cb_emergency_import_financing': ('banking_nonmod_emergency_import_financing_tt',),
    'banking_effect_cb_disable_emergency_import_financing': ('banking_nonmod_emergency_import_financing_off_tt',),
}
# The dashboard row tooltip splices the same lines under its modifier list.
# Capital controls' fatigue lines stay out: the row's own lore line says it,
# with the live count.
ROW_LINES = {
    'open_market_ops': ('banking_nonmod_open_market_ops_tt',),
    'capital_controls_outflow': ('banking_nonmod_capital_controls_tt',),
    'restrict_inflows': ('banking_nonmod_restrict_inflows_tt',),
    'sterilize_inflows': ('banking_nonmod_sterilize_inflows_tt',),
    'foreign_borrowing_limits': ('banking_nonmod_foreign_borrowing_limits_tt',
                                 'banking_nonmod_foreign_borrowing_limits_off_tt'),
    'fx_surrender': ('banking_nonmod_fx_surrender_tt',),
    'emergency_import_financing': ('banking_nonmod_emergency_import_financing_tt',
                                   'banking_nonmod_emergency_import_financing_off_tt'),
}
LABELS = ('banking_nonmod_monthly_label', 'banking_nonmod_lifted_label', 'banking_nonmod_war_end_label')


class NonModifierTooltipTest(unittest.TestCase):
    """The work a tool does outside its modifier is named, marked, and true to the script."""

    @classmethod
    def setUpClass(cls):
        cls.script = Script()
        cls.loc = english_loc()

    def text(self, key):
        return re.sub(r'\$(\w+)\$', lambda m: self.text(m.group(1)) if m.group(1) in self.loc else m.group(0),
                      self.loc[key])

    def test_each_effect_draws_its_lines(self):
        for effect, keys in NONMOD_LINES.items():
            drawn = tooltip_keys(self.script.effects, self.script.effects[effect])
            for key in keys:
                with self.subTest(effect=effect, key=key):
                    self.assertIn(key, drawn)

    def test_every_line_opens_with_a_label(self):
        for label in LABELS:
            self.assertRegex(self.loc[label], r'^#title [^#]+:#!$')
        for key in {k for keys in NONMOD_LINES.values() for k in keys}:
            with self.subTest(key=key):
                self.assertRegex(self.loc[key], r'^\$(%s)\$ ' % '|'.join(LABELS))

    def test_dashboard_rows_splice_the_lines_under_the_modifier(self):
        for tool, keys in ROW_LINES.items():
            row = self.loc['banking_dash_tt_cb_' + tool]
            for key in keys:
                with self.subTest(tool=tool, key=key):
                    self.assertIn('$%s$' % key, row)
                    self.assertGreater(row.index('$%s$' % key), row.index('.GetDesc]'))

    def test_war_end_line_shows_exactly_when_peace_would_lift_the_tool(self):
        for tool in ('restrict_inflows', 'fx_surrender'):
            for at_war, locked in ((True, True), (True, False), (False, False)):
                with self.subTest(tool=tool, at_war=at_war, locked=locked):
                    s = Script(at_war=at_war, controls_locked=locked)
                    s.effect('banking_effect_cb_' + tool)
                    self.assertEqual('banking_nonmod_war_end_lift_tt' in s.shown, at_war and locked)
            s = Script(at_war=True, controls_locked=True)
            s.effect('banking_effect_cb_' + tool)
            s.effect('banking_external_monthly_update')
            self.assertIn(tool, s.tools)
            s.inputs['at_war'] = False
            s.effect('banking_external_monthly_update')
            self.assertNotIn(tool, s.tools)

    def test_capital_controls_cleanup_spares_exactly_the_unlocked_laws(self):
        # Outflow Controls' peace-time lift names laws rather than reading the
        # lock, so the war-end line is right only while the two lists agree.
        laws = (ROOT/'common/laws/extra_laws.txt').read_text(encoding='utf-8-sig')
        unlocked = {name for name, body in re.findall(r'(?ms)^(law_\w+) = \{\n(.*?)^\}', laws)
                    if 'group = lawgroup_financial_regulation' in body
                    and 'country_banking_lock_capital_controls_bool = yes' not in body}
        cleanup = (ROOT/'common/scripted_effects/banking_cycle_effects.txt').read_text(encoding='utf-8-sig')
        block = cleanup.split('banking_cycle_cleanup_capital_controls = {', 1)[1].split('\n}', 1)[0]
        self.assertEqual(set(re.findall(r'has_law = law_type:(law_\w+)', block)), unlocked)

    def test_figures_match_the_script_values(self):
        v, t, s = self.script.number, self.text, self.script

        self.assertEqual(v('te_mon_qe_pressure'), 1)
        self.assertIn('#v 1#! percentage point', t('banking_nonmod_open_market_ops_tt'))

        self.assertEqual(v('te_mon_controls_damp_value'), .25)
        self.assertIn('#b quarter#!', t('banking_nonmod_capital_controls_tt'))
        per_step, steps = v('te_mon_controls_months_per_step'), v('te_mon_controls_months_max') / v('te_mon_controls_months_per_step')
        self.assertIn('every #v %d#! months, up to #v %d#!' % (per_step, steps), t('banking_nonmod_capital_controls_fatigue_tt'))
        self.assertEqual(v('te_mon_controls_decay'), 3)
        self.assertIn('#v 3#! months a month, three times', t('banking_nonmod_capital_controls_off_tt'))

        self.assertEqual(v('banking_external_inflow_factor'), .5)
        self.assertIn('#b halved#!', t('banking_nonmod_restrict_inflows_tt'))

        self.assertEqual(1 - v('banking_external_sterilized_factor'), .75)
        self.assertIn('#b three quarters#!', t('banking_nonmod_sterilize_inflows_tt'))
        self.assertIn('#v %.2f%%#!' % (100 * v('banking_external_sterilization_share')),
                      t('banking_nonmod_sterilize_inflows_tt'))

        step, cap = v('banking_external_fx_protection_step'), v('banking_external_fx_protection_cap')
        months = math.ceil(cap / step - 1e-9)
        for key in ('banking_nonmod_foreign_borrowing_limits_tt', 'banking_nonmod_foreign_borrowing_limits_off_tt'):
            self.assertIn('about #v %d%%#!' % round(100 * step), t(key))
        self.assertIn('up to #v %g%%#! after #v %d#! months' % (100 * cap, months),
                      t('banking_nonmod_foreign_borrowing_limits_tt'))

        self.assertIn('up to #v %.2f%%#! of annual GDP' % (100 * v('banking_external_surrender_share')),
                      t('banking_nonmod_fx_surrender_tt'))

        gdp, fatigue_cap = s.inputs['gdp'], v('banking_external_import_fatigue_cap')
        costs = []
        for months_funded in (0, fatigue_cap):
            s.vars['banking_external_import_months'] = months_funded
            costs.append(100 * v('banking_external_import_cost') / gdp)
        del s.vars['banking_external_import_months']
        self.assertIn('costs #v %.2f%%#! of annual GDP from the treasury, rising to #v %.2f%%#! after #v %d#! funded months'
                      % (*costs, fatigue_cap), t('banking_nonmod_emergency_import_financing_tt'))

        holiday = s.effects['banking_effect_cb_bank_holiday']
        cooldown = next(val for key, _, val in holiday
                        if key == 'custom_tooltip' and ('text', '=', 'banking_bank_holiday_cooldown_set_tt') in val)
        days = s.field(s.field(cooldown, 'set_variable'), 'days')
        self.assertIn('#v %d#! years' % (int(days) // 365), t('banking_bank_holiday_cooldown_set_tt'))


if __name__ == '__main__':
    unittest.main()
