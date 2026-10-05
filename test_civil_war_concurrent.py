"""Exercise #476's concurrent endings against the shared Paradox script.

The runner implements only the variable/scope operations these helpers use;
it does not simulate engine hook timing. Tests supply both possible end-hook
pairs and the save-confirmed merge rule (winner's own variables take priority).
"""

import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent


def entries(body):
    for part in body if isinstance(body, list) else [body]:
        for key, (operator, value) in part.items():
            yield key, operator, value


class Country:
    def __init__(self):
        self.variables = {}
        self.modifiers = set()
        self.alive = True


class EndingScript:
    """A strict runner for the shared helpers, with downstream repairs observed."""

    def __init__(self):
        parser = ParadoxFileParser()
        self.effects = {}
        for path in (
            'common/scripted_effects/te_civil_war_effects.txt',
            'common/scripted_effects/civil_rights_effects.txt',
            'common/scripted_effects/agricultural_diffusion_effects.txt',
        ):
            body = parser.parse_object(parser.tokenize('{' + (ROOT / path).read_text(encoding='utf-8-sig') + '}'))[0]
            self.effects.update({name: value for name, _, value in entries(body)})
        self.countries = [Country() for _ in range(5)]
        self.globals = {}
        self.scopes = {}
        self.calls = []
        self.root = None

    def reference(self, name, country):
        if name.lower() == 'root':
            return self.root
        if name.lower() == 'this':
            return country
        prefix, key = name.split(':', 1)
        return {'var': country.variables, 'global_var': self.globals, 'scope': self.scopes}[prefix].get(key)

    def condition(self, body, country):
        def check(key, operator, value):
            if key == 'OR':
                return any(self.condition({k: (op, v)}, country) for k, op, v in entries(value))
            if key == 'NOT':
                return not self.condition(value, country)
            if key == 'has_variable':
                return value in country.variables
            if key == 'has_global_variable':
                return value in self.globals
            if key == 'has_modifier':
                return value in country.modifiers
            if key == 'exists':
                return self.reference(value, country) is not None
            if key == 'is_country_alive':
                return country.alive == (value == 'yes')
            if key == 'is_country_type':
                return value == 'recognized'
            actual = self.reference(key, country)
            if isinstance(value, (dict, list)):
                return actual is not None and self.condition(value, actual)
            expected = self.reference(value, country) if ':' in value or value.lower() in ('root', 'this') else value
            return actual is not None and actual == expected
        return all(check(*entry) for entry in entries(body))

    def run(self, body, country):
        matched = False
        for key, operator, value in entries(body):
            if key in ('if', 'else_if', 'else'):
                if key == 'if':
                    matched = False
                content = list(entries(value))
                gate = next((v for k, _, v in content if k == 'limit'), {})
                allowed = key == 'else' or self.condition(gate, country)
                if not matched and allowed:
                    self.run(value, country)
                    matched = True
            elif key in ('limit', 'debug_log'):
                continue
            elif key in ('set_variable', 'set_global_variable'):
                fields = {k: v for k, _, v in entries(value)}
                stored = fields['value']
                if ':' in stored or stored.lower() in ('root', 'this'):
                    stored = self.reference(stored, country)
                target = self.globals if key == 'set_global_variable' else country.variables
                target[fields['name']] = stored
            elif key == 'save_scope_as':
                self.scopes[value] = country
            elif key == 'remove_variable':
                del country.variables[value]
            elif key == 'remove_global_variable':
                del self.globals[value]
            elif key == 'every_country':
                gate = next(v for k, _, v in entries(value) if k == 'limit')
                for other in self.countries:
                    if other.alive and self.condition(gate, other):
                        self.run(value, other)
            elif ':' in key:
                other = self.reference(key, country)
                if other is not None:
                    self.run(value, other)
                elif operator != '?=':
                    raise AssertionError(f'Missing required scope {key}')
            elif key.startswith('te_civil_war_'):
                self.run(self.effects[key], country)
            elif key in ('cr_rebuild_after_civil_war', 'cr_drop_rebel_run_state',
                         'agdiff_backfill_diffusion_for_country', 'agdiff_restore_first_mover_prestige',
                         'agdiff_repoint_first_country'):
                # Observe downstream choices, rather than emulating their systems.
                self.calls.append(key)
            else:
                raise AssertionError(f'Unsupported effect {key}')

    def effect(self, name, winner):
        self.root = winner
        self.run(self.effects[name], winner)

    def merge(self, winner, loser, kind='1', reported_origin=None, rebel=None):
        for key, value in loser.variables.items():
            winner.variables.setdefault(key, value)
        loser.alive = False
        self.globals = {'te_cw_ending_origin': reported_origin or loser,
                        'te_cw_ending_rebel': rebel or winner, 'te_cw_ending_kind': kind}
        self.scopes.clear()
        self.calls.clear()
        self.effect('te_civil_war_resolve_sides', winner)


class ConcurrentEndingsTest(unittest.TestCase):
    def setUp(self):
        self.script = EndingScript()
        self.original, self.first, self.second, self.other, self.third = self.script.countries
        self.original.variables['te_cw_role'] = '1'
        for rebel in (self.first, self.second, self.third):
            rebel.variables.update(te_cw_origin=self.original, te_cw_role='2')
        self.other.variables['te_cw_origin'] = self.other

    def first_wins(self):
        s = self.script
        s.merge(self.first, self.original)
        self.assertEqual(self.first.variables['te_cw_rebels_won'], '1')
        s.effect('te_civil_war_repoint_uprisings', self.first)
        self.assertIs(self.second.variables['te_cw_origin'], self.first)
        self.assertIs(self.third.variables['te_cw_origin'], self.first)
        self.assertIs(self.other.variables['te_cw_origin'], self.other)
        s.effect('te_civil_war_clear', self.first)
        self.assertNotIn('te_cw_origin', self.first.variables)
        self.assertNotIn('te_cw_role', self.first.variables)
        self.assertNotIn('te_cw_government_won', self.first.variables)
        self.assertEqual(s.globals, {})

    def test_second_revolution_loses_with_either_engine_pair(self):
        self.first_wins()
        for origin in (self.original, self.first):
            with self.subTest(stale_pair=origin is self.original):
                s = self.script
                s.merge(self.first, self.second, reported_origin=origin, rebel=self.second)
                self.assertEqual(self.first.variables['te_cw_rebels_won'], '0')
                self.assertEqual(self.first.variables['te_cw_government_won'], '1')
                self.assertIs(s.scopes['te_cw_loser'], self.second)
                s.effect('cr_repair_after_civil_war', self.first)
                self.assertEqual(s.calls, ['cr_drop_rebel_run_state'])
                s.effect('te_civil_war_repoint_uprisings', self.first)
                self.assertIs(self.third.variables['te_cw_origin'], self.first)
                s.effect('te_civil_war_clear', self.first)

    def test_second_revolution_wins_and_uses_continuing_governments_bank(self):
        self.first_wins()
        s = self.script
        self.first.variables['te_mon_policy_rate'] = '4'
        s.merge(self.second, self.first, reported_origin=self.original)
        self.assertEqual(self.second.variables['te_cw_rebels_won'], '1')
        self.assertEqual(self.second.variables['te_cw_government_won'], '0')
        self.assertIs(s.scopes['te_cw_loser'], self.first)
        self.assertEqual(s.scopes['te_cw_loser'].variables['te_mon_policy_rate'], '4')
        s.effect('te_civil_war_repoint_uprisings', self.second)
        self.assertIs(self.third.variables['te_cw_origin'], self.second)

    def test_government_beats_secession_after_revolution(self):
        self.first_wins()
        self.script.merge(self.first, self.second, kind='2', reported_origin=self.original, rebel=self.second)
        self.script.effect('cr_repair_after_civil_war', self.first)
        self.assertEqual(self.script.calls, ['cr_drop_rebel_run_state'])
        self.assertEqual(self.first.variables['te_cw_rebels_won'], '0')

    def test_secession_finishes_first_then_government_beats_revolution(self):
        # on_secession_end cleared the surviving seceder's role; the first
        # victory's clear also removed the government's role.
        self.first.variables.clear()
        self.original.variables.clear()
        self.script.merge(self.original, self.second, reported_origin=self.original, rebel=self.second)
        self.script.effect('cr_repair_after_civil_war', self.original)
        self.assertEqual(self.script.calls, ['cr_drop_rebel_run_state'])

    def test_single_war_government_wins(self):
        self.script.merge(self.original, self.first, reported_origin=self.original, rebel=self.first)
        self.assertEqual(self.original.variables['te_cw_rebels_won'], '0')
        self.assertEqual(self.original.variables['te_cw_government_won'], '1')
        self.assertIs(self.script.scopes['te_cw_loser'], self.first)

    def test_single_war_rebel_without_pointer_falls_back_to_pair(self):
        self.first.variables.pop('te_cw_origin')
        self.script.merge(self.first, self.original)
        self.assertEqual(self.first.variables['te_cw_rebels_won'], '1')
        self.assertIs(self.script.scopes['te_cw_loser'], self.original)

    def test_legacy_ending_without_pair_uses_origin(self):
        self.script.effect('te_civil_war_resolve_sides', self.first)
        self.assertEqual(self.first.variables['te_cw_rebels_won'], '1')
        self.assertIs(self.script.scopes['te_cw_loser'], self.original)

    def test_legacy_government_without_pair_keeps_its_repair(self):
        self.original.variables['te_cw_origin'] = self.original
        self.script.effect('te_civil_war_resolve_sides', self.original)
        self.assertEqual(self.original.variables['te_cw_government_won'], '1')
        self.script.effect('cr_repair_after_civil_war', self.original)
        self.assertEqual(self.script.calls, ['cr_drop_rebel_run_state'])

    def test_rebel_with_unresolvable_pointer_uses_pair(self):
        self.first.variables['te_cw_origin'] = None
        self.script.merge(self.first, self.original)
        self.assertIs(self.script.scopes['te_cw_loser'], self.original)

    def test_seceder_with_role_already_cleared_is_not_a_new_regime(self):
        self.first.variables.clear()
        self.script.globals = {'te_cw_ending_origin': self.original,
                               'te_cw_ending_rebel': self.first, 'te_cw_ending_kind': '2'}
        self.script.effect('te_civil_war_resolve_sides', self.first)
        self.assertEqual(self.first.variables['te_cw_rebels_won'], '0')
        self.assertEqual(self.first.variables['te_cw_government_won'], '0')
        self.script.effect('te_civil_war_repoint_uprisings', self.first)
        self.assertIs(self.second.variables['te_cw_origin'], self.original)

    def test_unearned_first_mover_record_cannot_survive_to_later_revolution(self):
        self.second.variables['agdiff_first_mover_month'] = '100'
        self.script.merge(self.original, self.second, reported_origin=self.original, rebel=self.second)
        self.script.effect('agdiff_repair_after_civil_war', self.original)
        self.assertNotIn('agdiff_first_mover_month', self.original.variables)
        self.script.effect('te_civil_war_clear', self.original)
        self.script.merge(self.first, self.original)
        self.assertNotIn('agdiff_first_mover_month', self.first.variables)

    def test_government_keeps_its_own_first_mover_reward_record(self):
        self.original.variables['agdiff_first_mover_month'] = '100'
        self.original.modifiers.add('agdiff_first_mover_prestige')
        self.script.merge(self.original, self.second, reported_origin=self.original, rebel=self.second)
        self.script.effect('agdiff_repair_after_civil_war', self.original)
        self.assertEqual(self.original.variables['agdiff_first_mover_month'], '100')

    def test_rebel_winner_keeps_first_mover_record_for_restore(self):
        self.original.variables['agdiff_first_mover_month'] = '100'
        self.script.merge(self.first, self.original)
        self.script.effect('agdiff_repair_after_civil_war', self.first)
        self.assertEqual(self.first.variables['agdiff_first_mover_month'], '100')
        self.assertIn('agdiff_restore_first_mover_prestige', self.script.calls)

    def test_independent_seceder_keeps_its_first_mover_record(self):
        self.first.variables['agdiff_first_mover_month'] = '100'
        self.script.globals = {'te_cw_ending_origin': self.original,
                               'te_cw_ending_rebel': self.first, 'te_cw_ending_kind': '2'}
        self.script.effect('te_civil_war_resolve_sides', self.first)
        self.script.effect('agdiff_repair_after_civil_war', self.first)
        self.assertEqual(self.first.variables['agdiff_first_mover_month'], '100')
        self.assertNotIn('agdiff_restore_first_mover_prestige', self.script.calls)

    def test_repoint_runs_after_repairs_and_before_cleanup(self):
        text = (ROOT / 'common/on_actions/te_civil_war_on_actions.txt').read_text(encoding='utf-8-sig')
        won = text[text.index('te_civil_war_on_won = {'):]
        self.assertLess(won.index('te_monetary_repair_after_civil_war = yes'),
                        won.index('te_civil_war_repoint_uprisings = yes'))
        self.assertLess(won.index('te_civil_war_repoint_uprisings = yes'), won.index('te_civil_war_clear = yes'))


if __name__ == '__main__':
    unittest.main()
