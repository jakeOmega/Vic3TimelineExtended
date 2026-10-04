"""Rare colony discoveries: ownership, one-shot seeding, delays and reward repair.

These exercise the parsed scripts' state transitions with deterministic rolls;
they do not substitute for an engine play-test.
"""
from pathlib import Path
import re
import subprocess
import unittest

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
SITES = {
    'europa_life': 'europa', 'europa_vents': 'europa',
    'enceladus_life': 'enceladus', 'titan_chemistry': 'titan',
    'hellas_fossils': 'hellas_planitia', 'olympus_tubes': 'olympus_mons',
    'utopia_glacier': 'utopia_planitia', 'arcadia_brines': 'arcadia_planitia',
    'ceres_reservoir': 'ceres', 'vesta_impactor': 'vesta',
    'psyche_metal': 'psyche', 'pallas_water': 'pallas', 'venus_waves': 'venus',
    'mercury_archive': 'mercury', 'io_roof': 'io',
    'ganymede_layers': 'ganymede', 'callisto_archive': 'callisto',
    'titania_ocean': 'titania', 'triton_jet': 'triton', 'pluto_antifreeze': 'pluto',
}


def load(path):
    parser = ParadoxFileParser()
    parser.parse_file(ROOT / path)
    return parser.data


def value(node, key):
    return node[key][1]


def occurrences(node):
    for key, entries in node.items():
        for entry in entries if isinstance(entries, list) else [entries]:
            yield key, entry[1]


class ScriptState:
    """Small strict executor for just the effects and triggers under test.

    Timers are explicit state so tests can expire them independently. Every
    unsupported command fails instead of silently approximating engine behavior.
    """
    def __init__(self, definitions):
        self.definitions = definitions
        self.variables = {}
        self.events = []
        self.rolls = []
        self.chances = []
        self.enabled = True
        self.colony = True

    def matches(self, conditions):
        for key, arg in occurrences(conditions):
            if key == 'has_variable':
                result = arg in self.variables
            elif key == 'NOT':
                result = not self.matches(arg)
            elif key == 'has_game_rule':
                result = self.enabled
            elif key == 'sr_has_space_colony':
                result = self.colony
            else:
                raise AssertionError(f'Unsupported trigger: {key}')
            if not result:
                return False
        return True

    def call(self, name, **params):
        def expand(obj):
            if isinstance(obj, str):
                for key, arg in params.items():
                    obj = obj.replace(f'${key}$', str(arg))
                return obj
            if isinstance(obj, dict):
                return {expand(k): expand(v) for k, v in obj.items()}
            if isinstance(obj, tuple):
                return tuple(expand(v) for v in obj)
            if isinstance(obj, list):
                return [expand(v) for v in obj]
            raise AssertionError(type(obj))
        self.execute(expand(self.definitions[name][1]))

    def execute(self, body):
        for key, arg in occurrences(body):
            if key in ('limit', 'chance'):
                continue
            if key == 'if':
                if self.matches(value(arg, 'limit')):
                    self.execute(arg)
            elif key == 'random':
                self.chances.append(int(value(arg, 'chance')))
                if self.rolls.pop(0):
                    self.execute(arg)
            elif key == 'set_variable':
                self.variables[value(arg, 'name')] = (
                    value(arg, 'value'), value(arg, 'days') if 'days' in arg else None)
            elif key == 'remove_variable':
                self.variables.pop(arg, None)
            elif key == 'trigger_event':
                self.events.append(value(arg, 'id'))
            elif key == 'hidden_effect':
                self.execute(arg)
            elif key in self.definitions:
                self.call(key, **{k: v for k, v in occurrences(arg)})
            else:
                raise AssertionError(f'Unsupported effect: {key}')


class DiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = load('common/scripted_effects/space_race_discovery_effects.txt')
        cls.events = load('events/space_race_discovery_events.txt')
        cls.modifiers = load('common/static_modifiers/space_race_discovery_modifiers.txt')
        # CI intentionally omits gfx/ from its sparse checkout. Validate asset
        # references against Git's index, without requiring texture downloads.
        cls.pictures = set(subprocess.check_output(
            ['git', 'ls-files', '--', 'gfx/event_pictures/*.dds'],
            cwd=ROOT, text=True).splitlines())

    def state(self):
        return ScriptState(self.effects)

    def test_failed_founding_roll_is_never_retried(self):
        state = self.state()
        state.rolls = [False]
        state.call('sr_seed_colony_discovery', DISCOVERY='europa_life')
        self.assertIn('sr_discovery_europa_life_rolled', state.variables)
        self.assertNotIn('sr_discovery_europa_life_pending', state.variables)
        state.call('sr_seed_colony_discovery', DISCOVERY='europa_life')
        self.assertEqual(state.chances, [10])

    def test_successful_seed_surveys_once_and_preserves_elapsed_timer(self):
        state = self.state()
        state.rolls = [True]
        state.call('sr_seed_colony_discovery', DISCOVERY='europa_life')
        self.assertEqual(state.variables['sr_discovery_europa_life_survey'], ('yes', '365'))
        state.variables['sr_discovery_europa_life_survey'] = ('yes', '20')
        state.call('sr_seed_colony_discovery', DISCOVERY='europa_life')
        self.assertEqual(state.variables['sr_discovery_europa_life_survey'], ('yes', '20'))
        self.assertEqual(state.chances, [10])

    def test_survey_and_cooldown_block_the_monthly_roll(self):
        for timer in ('sr_discovery_europa_life_survey', 'sr_discovery_cooldown'):
            with self.subTest(timer=timer):
                state = self.state()
                state.variables = {'sr_discovery_europa_life_pending': ('yes', None),
                                   timer: ('yes', '20')}
                state.call('sr_monthly_colony_discoveries')
                self.assertEqual(state.chances, [])
                self.assertEqual(state.events, [])

    def test_success_reserves_spacing_and_keeps_other_candidates_pending(self):
        state = self.state()
        state.variables = {f'sr_discovery_{key}_pending': ('yes', None) for key in SITES}
        state.rolls = [True]
        state.call('sr_monthly_colony_discoveries')
        self.assertEqual(state.chances, [1])
        self.assertEqual(state.events, ['space_race_discovery_events.1'])
        self.assertEqual(state.variables['sr_discovery_cooldown'], ('yes', '180'))
        immediate = value(self.events['space_race_discovery_events.1'][1], 'immediate')
        state.execute(immediate)
        self.assertNotIn('sr_discovery_europa_life_pending', state.variables)
        self.assertIn('sr_discovery_europa_life_done', state.variables)
        self.assertIn('sr_discovery_europa_vents_pending', state.variables)
        del state.variables['sr_discovery_cooldown']
        state.rolls = [True]
        state.call('sr_monthly_colony_discoveries')
        self.assertEqual(state.events[-1], 'space_race_discovery_events.2')
        self.assertEqual(state.chances, [1, 2])

    def test_failed_monthly_roll_preserves_the_pending_discovery(self):
        state = self.state()
        state.variables['sr_discovery_europa_life_pending'] = ('yes', None)
        state.rolls = [False, True]
        state.call('sr_monthly_colony_discoveries')
        self.assertIn('sr_discovery_europa_life_pending', state.variables)
        self.assertNotIn('sr_discovery_cooldown', state.variables)
        state.call('sr_monthly_colony_discoveries')
        self.assertEqual(state.events, ['space_race_discovery_events.1'])

    def test_done_discovery_never_rolls_even_if_pending_was_restored(self):
        state = self.state()
        state.variables = {'sr_discovery_europa_life_pending': ('yes', None),
                           'sr_discovery_europa_life_done': ('yes', None)}
        state.call('sr_monthly_colony_discoveries')
        self.assertEqual(state.chances, [])

    def test_game_rule_and_colony_ownership_gate_delivery(self):
        for attribute in ('enabled', 'colony'):
            state = self.state()
            state.variables['sr_discovery_europa_life_pending'] = ('yes', None)
            setattr(state, attribute, False)
            state.call('sr_monthly_colony_discoveries')
            self.assertEqual(state.chances, [])

    def test_every_seed_belongs_to_its_actual_claim(self):
        text = (ROOT / 'common/scripted_effects/space_race_effects.txt').read_text('utf-8-sig')
        for key, site in SITES.items():
            with self.subTest(discovery=key):
                marker = f'sr_seed_colony_discovery = {{ DISCOVERY = {key} }}'
                self.assertEqual(text.count(marker), 1)
                claim = f'set_global_variable = {{ name = sr_colony_{site} value = yes }}'
                start = text.rfind(claim, 0, text.index(marker))
                self.assertGreater(start, 0)
                between = text[start:text.index(marker)]
                self.assertNotIn('trigger_event', between)
                self.assertNotIn('random_list', between)
                self.assertLess(text.index(marker), text.index('trigger_event', start))

    def test_twenty_deliveries_have_complete_choices_art_and_reward_repairs(self):
        sync = self.effects['sr_sync_colony_discovery_modifiers'][1]
        repaired = {value(arg, 'MODIFIER') for key, arg in occurrences(sync)
                    if key == 'sr_sync_colony_modifier_base'}
        all_loc = ''.join(p.read_text('utf-8-sig') for p in
                          (ROOT / 'localization/english').glob('*.yml'))
        loc_keys = set(re.findall(r'^ ([\w.]+):', all_loc, re.M))
        monthly = self.effects['sr_monthly_colony_discoveries'][1]
        dispatches = [arg for key, arg in occurrences(value(monthly, 'if'))
                      if key == 'sr_roll_colony_discovery']
        self.assertEqual(len(dispatches), 20)
        self.assertEqual(len(self.events) - 1, 20)  # namespace is metadata
        self.assertEqual(len(self.modifiers), 40)
        for dispatch in dispatches:
            eid = value(dispatch, 'EVENT')
            key = value(dispatch, 'DISCOVERY')
            self.assertIn(key, SITES)
            self.assertEqual(value(dispatch, 'CHANCE'),
                             '1' if key in ('europa_life', 'enceladus_life', 'hellas_fossils') else '2')
            event = self.events[eid][1]
            self.assertEqual(value(event, 'type'), 'country_event')
            texture = value(value(event, 'event_image'), 'texture').strip('"')
            self.assertIn(texture, self.pictures)
            for field in ('title', 'desc', 'flavor'):
                self.assertIn(value(event, field), loc_keys)
            options = event['option']
            self.assertEqual(len(options), 2)
            self.assertEqual(value(options[0][1], 'default_option'), 'yes')
            for _, option in options:
                self.assertIn(value(option, 'name'), loc_keys)
                mod = value(value(option, 'sr_grant_colony_modifier'), 'MODIFIER')
                self.assertIn(mod, self.modifiers)
                self.assertIn(mod, repaired)
                self.assertIn(mod, loc_keys)
            trigger = value(event, 'trigger')
            state = self.state()
            state.variables[f'sr_discovery_{key}_pending'] = ('yes', None)
            self.assertTrue(state.matches(trigger))
            state.variables[f'sr_discovery_{key}_done'] = ('yes', None)
            self.assertFalse(state.matches(trigger))

    def test_monthly_and_entry_sync_hooks_are_wired(self):
        actions = (ROOT / 'common/on_actions/space_race_on_actions.txt').read_text('utf-8-sig')
        effects = (ROOT / 'common/scripted_effects/space_race_effects.txt').read_text('utf-8-sig')
        self.assertEqual(actions.count('sr_monthly_colony_discoveries = yes'), 1)
        self.assertIn('sr_sync_colony_discovery_modifiers = yes', effects)
        monthly = repr(self.effects['sr_monthly_colony_discoveries'])
        self.assertNotIn('sr_solar_colonization_running', monthly)
        self.assertNotIn('sr_ai_should_participate', monthly)
        self.assertNotIn('sr_completed_solar_colonization', monthly)


if __name__ == '__main__':
    unittest.main()
