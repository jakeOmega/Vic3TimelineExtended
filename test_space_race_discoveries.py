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
        # The world's record (colony record design § 3): global variables.
        self.globals = {}
        self.events = []
        self.rolls = []
        self.chances = []
        self.enabled = True
        self.colony = True

    def matches(self, conditions):
        for key, arg in occurrences(conditions):
            if key == 'has_variable':
                result = arg in self.variables
            elif key == 'has_global_variable':
                result = arg in self.globals
            elif key == 'NOT':
                result = not self.matches(arg)
            elif key in ('has_game_rule', 'sr_space_race_on'):
                # The Space Race rule, read through its gate (sr_site_triggers.txt).
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
            elif key == 'set_global_variable':
                self.globals[value(arg, 'name')] = value(arg, 'value')
            elif key == 'remove_global_variable':
                self.globals.pop(arg, None)
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
        # The world's record keeps the find for whoever holds Europa later.
        self.assertIn('sr_site_disc_europa_life_pending', state.globals)
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
        # The draw is generated from the site table (gen_solar_sites.py).
        text = (ROOT / 'common/scripted_effects/sr_sites_generated.txt').read_text('utf-8-sig')
        text = text[text.index('sr_establish_colony_effect = {'):text.index('sr_check_colony_stage_effect = {')]
        for key, site in SITES.items():
            with self.subTest(discovery=key):
                marker = f'sr_seed_colony_discovery = {{ DISCOVERY = {key} }}'
                claim = f'set_global_variable = {{ name = sr_colony_{site} value = yes }}'
                # Once in its own stage's draw and once in each later stage's,
                # which also draws released worlds (colony record design § 6):
                # every seed follows its own world's claim.
                self.assertEqual(text.count(marker), text.count(claim))
                self.assertGreater(text.count(marker), 0)
                for found in re.finditer(re.escape(marker), text):
                    start = text.rfind(claim, 0, found.start())
                    self.assertGreater(start, 0)
                    between = text[start:found.start()]
                    self.assertNotIn('trigger_event', between)
                    self.assertNotIn('random_list', between)
                    self.assertLess(found.start(), text.index('trigger_event', start))

    def test_twenty_deliveries_have_complete_choices_art_and_declarations(self):
        # Under races only, the entry declares each outcome while its holder's
        # <modifier>_held is set (1.15 scaling modifiers, #1404): a revolution's
        # winner inherits the variable, so no repair puts the modifier back. Under
        # simple and full colonies the outcome is its world's boon (BoonTests).
        declared = set(re.findall(
            r'modifier = (sr_discovery_\w+)\s*value = \{\s*value = 0\s*if = \{\s*limit = \{ has_variable = \1_held '
            r'NOT = \{ sr_colonies_contested_enabled = yes \} \}\s*add = 1\s*\}',
            (ROOT / 'common/journal_entries/sr_sites_generated.txt').read_text('utf-8-sig')))
        self.assertEqual(len(declared), 40)
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
                chosen = [key for key in option if key.startswith('sr_site_choose_')]
                self.assertEqual(len(chosen), 1)
                self.assertEqual(value(option, chosen[0]), 'yes')
                mod = chosen[0][len('sr_site_choose_'):]
                self.assertIn(mod, self.modifiers)
                self.assertIn(mod, declared)
                self.assertIn(mod, loc_keys)
                self.assertIn(f'{mod}_tt', loc_keys)
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
        self.assertNotIn('sr_sync_colony_discovery_modifiers', effects)
        self.assertNotIn('sr_sync_colony_discovery_modifiers', (ROOT / 'common/scripted_effects/space_race_discovery_effects.txt').read_text('utf-8-sig'))
        monthly = repr(self.effects['sr_monthly_colony_discoveries'])
        self.assertNotIn('sr_solar_colonization_running', monthly)
        self.assertNotIn('sr_ai_should_participate', monthly)
        self.assertNotIn('sr_completed_solar_colonization', monthly)


def _block(text, name):
    """The body of `name = { ... }` (its first definition at a line start)."""
    match = re.search(rf'(?m)^\s*{re.escape(name)} = \{{', text)
    assert match, name
    depth, start = 1, match.end()
    for i in range(start, len(text)):
        depth += {'{': 1, '}': -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i]
    raise AssertionError(name)


class BoonTests(unittest.TestCase):
    """A discovery's option is its world's boon under simple and full colonies
    (the owner, 2026-11-25): +100% to one module's effect at that world
    (gen_solar_sites.DISCOVERY_BOONS)."""

    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts' / 'generators'))
        import gen_solar_sites
        cls.gss = gen_solar_sites
        cls.values = (ROOT / 'common/script_values/sr_sites_generated.txt').read_text('utf-8-sig')
        cls.display = (ROOT / 'common/script_values/sr_sites_display_generated.txt').read_text('utf-8-sig')
        cls.rows = (ROOT / 'gui/journal_entry_widgets/sr_sites_generated_rows.gui').read_text('utf-8-sig')
        cls.widget = (ROOT / 'gui/journal_entry_widgets/space_race_widget.gui').read_text('utf-8-sig')
        loc = ''.join(p.read_text('utf-8-sig') for p in (ROOT / 'localization/english').glob('*.yml'))
        cls.loc = dict(re.findall(r'(?m)^ ([\w.]+):\d* "(.*)"$', loc))

    def test_every_discovery_names_a_module_its_world_takes(self):
        gss = self.gss
        seeded = {d for s in gss.SITES for d in s.discoveries}
        self.assertEqual(set(gss.DISCOVERY_BOONS), seeded)
        self.assertEqual(set(gss.DISCOVERY_BOONS), set(SITES))
        for site in gss.SITES:
            for d in site.discoveries:
                with self.subTest(discovery=d):
                    a, b = gss.DISCOVERY_BOONS[d]
                    # The first option studies the find; the second puts it to use.
                    self.assertEqual(a, 'lab')
                    self.assertNotEqual(b, 'lab')
                    for t in (a, b):
                        self.assertIn(t, gss.BOON_TYPES)
                        self.assertIn(t, gss.generic_types(site))
        # Not the Administration (its staffed levels are its bill), nor the
        # modules other generators read.
        self.assertFalse({'admin', 'def', 'port'} & set(gss.BOON_TYPES))
        self.assertEqual(gss.BOON_BONUS, 1)
        self.assertRegex(self.values, rf'(?m)^sr_site_boon_bonus = \{{ value = {gss.BOON_BONUS} \}}')

    def test_the_boon_reads_the_world_s_record(self):
        gss = self.gss
        for site in gss.SITES:
            k = site.key
            for t, sources in gss.site_boons(site).items():
                with self.subTest(site=k, type=t):
                    boon = _block(self.values, f'sr_site_boon_{t}_{k}')
                    self.assertIn('value = 1', boon)
                    found = re.findall(r'global_var:sr_site_disc_(\w+) = (\d) \} add = sr_site_boon_bonus', boon)
                    self.assertEqual(found, [(d, str(o)) for d, o in sources])
                    if t == 'hab':
                        self.assertIn(f'sr_site_hab_share_eff_{k} = {{ value = sr_site_hab_share_value_{k} '
                                      f'multiply = sr_site_boon_hab_{k} }}', self.values)
                    else:
                        self.assertIn(f'sr_site_{t}_eff_{k} = {{ value = sr_site_{t}_staffed_{k} '
                                      f'multiply = sr_site_boon_{t}_{k} }}', self.values)
            # No boon value where no discovery here can name the type.
            for t in set(gss.BOON_TYPES) - set(gss.site_boons(site)):
                self.assertNotIn(f'sr_site_boon_{t}_{k} =', self.values)

    def test_every_effect_reads_the_effective_levels(self):
        gss = self.gss
        for f in gss.FACILITIES:
            units = _block(self.values, f'sr_mod_units_{f.key}')
            for site in gss.SITES:
                if f.key not in gss.generic_types(site):
                    continue
                with self.subTest(facility=f.key, site=site.key):
                    self.assertIn(f'add = {gss.eff_value(site, f.key)} }}', units)
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(gss.eff_value(site, 'mine'), _block(self.values, f'sr_site_ebase_room_{k}'))
                self.assertIn(gss.eff_value(site, 'resort'), _block(self.values, f'sr_site_resort_room_{k}'))
                self.assertIn(gss.eff_value(site, 'culture'), _block(self.values, f'sr_site_resort_draw_{k}'))
                for name in (f'sr_site_room_{k}', f'sr_md_room_less_hab_{k}'):
                    self.assertIn(f'multiply = {gss.hab_share_eff(site)}', _block(self.values, name))
                if gss.terraformable(site):
                    self.assertIn(f'value = {gss.eff_value(site, "terra")}', _block(self.values, f'sr_site_terra_rate_{k}'))
        # The Administration's units are its authority bill: never boosted.
        self.assertNotIn('sr_site_admin_eff_', self.values)

    def test_the_tooltips_name_the_module_and_the_world(self):
        gss = self.gss
        pct = f'+{gss.BOON_BONUS:.0%}'
        for site in gss.SITES:
            for d in site.discoveries:
                for m, t in zip(gss.discovery_modifiers(d), gss.DISCOVERY_BOONS[d]):
                    with self.subTest(outcome=m):
                        text = self.loc[f'{m}_tt']
                        self.assertTrue(text.startswith(f'#G {pct}#! to '))
                        self.assertIn(f'$je_space_race_widget_mod_name_{t}$', text)
                        self.assertIn(f'$sr_site_name_{site.key}$', text)
                with self.subTest(page_line=d):
                    eid = gss_event(d)
                    self.assertEqual(self.loc[f'je_space_race_widget_mod_boon_{d}'],
                                     f'${eid}.t$: #G {pct}#!')

    def test_the_colony_page_shows_each_boon(self):
        gss = self.gss
        start = self.widget.index('type te_sr_page_mod_row = flowcontainer {')
        row = self.widget[start:self.widget.index('\ttype ', start + 1)]
        self.assertIn('block "row_boons" {\n\t\t\t\tvisible = no\n\t\t\t}', row)
        for t in gss.BOON_TYPES:
            with self.subTest(type=t):
                self.assertIn(f'blockoverride "row_boons" {{\n\t\t\t\t\t\tblock "mod_{t}_boons" {{\n'
                              '\t\t\t\t\t\t\tvisible = no', self.widget)
        for site in gss.SITES:
            for d in site.discoveries:
                for option, (m, t) in enumerate(zip(gss.discovery_modifiers(d), gss.DISCOVERY_BOONS[d]), start=1):
                    with self.subTest(outcome=m):
                        shown = (f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue("
                                 f"'sr_disp_site_disc_{d}'), '(CFixedPoint){option}' )")
                        line = (f'visible = "[{shown}]"', f'text = "je_space_race_widget_mod_boon_{d}"',
                                f'tooltip = "{m}_tt"')
                        self.assertTrue(all(part in self.rows for part in line))
                        self.assertRegex(self.rows, rf'blockoverride "mod_{t}_boons" \{{[^}}]*{re.escape(shown)}')
                self.assertIn(f'sr_disp_site_disc_{d} = {{', self.display)


def gss_event(discovery):
    effects = (ROOT / 'common/scripted_effects/space_race_discovery_effects.txt').read_text('utf-8-sig')
    return re.search(rf'DISCOVERY = {discovery} EVENT = (\S+)', effects).group(1)


if __name__ == '__main__':
    unittest.main()
