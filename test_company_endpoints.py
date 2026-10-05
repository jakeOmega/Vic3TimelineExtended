"""Company comparison and reverse roster lookup (#667), without a game install."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from mod_state import ModState
import mod_state_server as mss
import vanilla_parsed


VANILLA = """
company_generic = {
    flavored_company = no
    building_types = { building_a building_b }
    extension_building_types = { building_c }
    prosperity_modifier = { throughput = 0.1 }
    possible_prestige_goods = { prestige_good_a }
    attainable = {
        has_technology_researched = tech_a
        OR = { has_technology_researched = tech_b has_technology_researched = tech_c }
    }
}
company_flavored = {
    flavored_company = yes
    building_types = { building_b }
    prosperity_modifier = { throughput = 0.2 state_building_b_max_level_add = 1 }
}
company_replaced = {
    flavored_company = no
    building_types = { building_a }
    prosperity_modifier = { old_effect = 0.5 }
}
company_noop = { flavored_company = no building_types = { building_c } }
"""
MOD = """
INJECT:company_generic = {
    building_types = { building_d }
    prosperity_modifier = { wages = -0.1 state_building_d_max_level_add = 1 }
}
REPLACE:company_replaced = {
    flavored_company = yes
    building_types = { building_d }
    extension_building_types = { building_a building_d }
    prosperity_modifier = { new_effect = 0.3 state_building_a_max_level_add = 2 }
}
INJECT:company_noop = { flavored_company = no }
company_new = {
    flavored_company = no
    building_types = { building_a building_c building_d }
    prosperity_modifier = { input = -0.2 output = 0.1 }
}
"""


class CompanyEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mod = self.root / 'mod'
        self.base = self.root / 'game'
        for root in (self.mod, self.base):
            (root / 'common/company_types').mkdir(parents=True)
        self.vanilla_file = self.base / 'common/company_types/00.txt'
        self.vanilla_file.write_text(VANILLA, encoding='utf-8')
        self.mod_file = self.mod / 'common/company_types/patch.txt'
        self.mod_file.write_text(MOD, encoding='utf-8')
        self.base_dirs = {'Company Types': str(self.vanilla_file.parent)}
        self.mod_dirs = {'Company Types': str(self.mod_file.parent)}
        self.state = ModState(self.base_dirs, self.mod_dirs)
        self.state.localization = {'company_generic': 'Generic Company', 'building_a': 'Building A'}
        # No production methods or other unrelated data are needed for lookup.
        self.state.mod_parsers['Buildings'] = mss.ParadoxFileParser()
        self.state.mod_parsers['Buildings'].data = {
            'building_' + c: ('=', {}) for c in 'abcde'
        }
        for name, value in {
            'ms': self.state, 'mod_path': str(self.mod), 'base_game_path': str(self.base),
            'mod_paths': self.mod_dirs, 'base_game_paths': self.base_dirs,
            '_vanilla_source': {'kind': 'game_files'}, '_company_catalog_cache': None,
        }.items():
            patch = mock.patch.object(mss, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        self.handler = object.__new__(mss.ModStateHandler)

    def request(self, path):
        self.handler.path = path
        self.handler._local_request_ok = mock.Mock(return_value=True)
        self.handler._respond_json = mock.Mock()
        self.handler.do_GET()
        args = self.handler._respond_json.call_args.args
        return (args[1] if len(args) > 1 else 200), args[0]

    def rows(self, query=''):
        status, body = self.request('/companies' + query)
        self.assertEqual(status, 200)
        self.assertEqual(body['count'], len(body['companies']))
        # Exercise JSON serialization, including unwrapped modifier values.
        json.dumps(body)
        return {c['id']: c for c in body['companies']}

    def test_merged_fields_and_flagship_separation(self):
        before = copy.deepcopy(self.state.get_data('Company Types'))
        rows = self.rows()
        self.assertEqual(list(rows), sorted(rows))
        generic = rows['company_generic']
        self.assertEqual(generic['name'], 'Generic Company')
        self.assertFalse(generic['flavored'])
        self.assertEqual(generic['building_types'], ['building_a', 'building_b', 'building_d'])
        self.assertEqual(generic['extension_building_types'], ['building_c'])
        self.assertEqual((generic['roster_size'], generic['extension_count']), (3, 1))
        self.assertEqual(generic['prosperity_modifier'], {'throughput': '0.1', 'wages': '-0.1'})
        self.assertEqual(generic['flagship'], {'state_building_d_max_level_add': '1'})
        self.assertEqual(generic['effect_count'], 2)
        self.assertEqual(generic['possible_prestige_goods'], ['prestige_good_a'])
        self.assertEqual(generic['attainable_techs'], ['tech_a', 'tech_b', 'tech_c'])
        replacement = rows['company_replaced']
        self.assertEqual(replacement['building_types'], ['building_d'])
        self.assertEqual(replacement['prosperity_modifier'], {'new_effect': '0.3'})
        self.assertEqual(before, self.state.get_data('Company Types'))

    def test_source_filters_include_injects_replacements_and_noop_patches(self):
        mod = self.rows('?source=mod')
        self.assertEqual(set(mod), {'company_generic', 'company_new', 'company_replaced', 'company_noop'})
        self.assertEqual(set(self.rows('?source=vanilla')), {'company_flavored'})
        self.assertEqual(set(self.rows('?source=mod&flavored=yes')), {'company_replaced'})
        self.assertEqual(set(self.rows('?source=all&flavored=no')),
                         {'company_generic', 'company_new', 'company_noop'})
        self.assertEqual(mod['company_generic']['source_files'], [
            {'source': 'mod', 'file': 'common/company_types/patch.txt'},
            {'source': 'vanilla', 'file': 'common/company_types/00.txt'},
        ])

    def test_stats_use_filtered_rows_and_exclude_flagship_effects(self):
        status, body = self.request('/companies')
        self.assertEqual(status, 200)
        self.assertEqual(body['stats']['no'], {
            'count': 3, 'roster_size_median': 3, 'roster_size_max': 3, 'effect_count_median': 2,
        })
        self.assertEqual(body['stats']['yes']['effect_count_median'], 1)
        _, filtered = self.request('/companies?flavored=yes&source=mod')
        self.assertEqual(filtered['stats']['yes']['roster_size_median'], 1)
        self.assertEqual(filtered['stats']['no'], {
            'count': 0, 'roster_size_median': None, 'roster_size_max': None, 'effect_count_median': None,
        })

    def test_reverse_lookup_uses_merged_rosters_and_independent_memberships(self):
        status, body = self.request('/building-companies/building_a')
        self.assertEqual(status, 200)
        self.assertEqual(body['building'], {'type': 'Buildings', 'id': 'building_a', 'name': 'Building A'})
        self.assertEqual(body['roster'], ['company_generic', 'company_new'])
        self.assertEqual(body['extension'], ['company_replaced'])
        _, both = self.request('/building-companies/building_d')
        self.assertEqual(both['roster'], ['company_generic', 'company_new', 'company_replaced'])
        self.assertEqual(both['extension'], ['company_replaced'])
        _, uncovered = self.request('/building-companies/building_e')
        self.assertEqual((uncovered['roster'], uncovered['extension']), ([], []))

    def test_bad_filters_paths_and_unknown_buildings(self):
        for path, expected in (
            ('/companies?flavored=maybe', 400), ('/companies?flavored=', 200),
            ('/companies?source=both', 400), ('/companies/anything', 404),
            ('/building-companies', 400), ('/building-companies/unknown', 404),
            ('/building-companies/building_a/extra', 404),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], expected)

    def test_unloaded_data_returns_503_but_loaded_empty_collection_is_valid(self):
        with mock.patch.object(mss, 'ms', None):
            self.assertEqual(self.request('/companies')[0], 503)
            self.assertEqual(self.request('/building-companies/building_a')[0], 503)
        self.state.mod_parsers.pop('Company Types')
        self.assertEqual(self.request('/companies')[0], 503)
        self.assertEqual(self.request('/building-companies/building_a')[0], 503)
        self.state.mod_parsers['Company Types'] = mss.ParadoxFileParser()
        self.assertEqual(self.rows(), {})
        self.assertEqual(self.request('/building-companies/building_a')[1]['roster'], [])

    def test_response_mutation_cannot_poison_catalog_or_parsed_state(self):
        rows = self.rows()
        rows['company_generic']['building_types'].clear()
        rows['company_generic']['prosperity_modifier']['throughput'] = 1000
        fresh = self.rows()['company_generic']
        self.assertEqual(fresh['roster_size'], len(fresh['building_types']))
        self.assertEqual(fresh['prosperity_modifier']['throughput'], '0.1')

    def test_reload_after_generator_writes_invalidates_catalog(self):
        self.rows()
        self.mod_file.write_text(MOD.replace('building_d', 'building_e'), encoding='utf-8')
        with mock.patch.object(mss, '_VANILLA_LOC_CACHE', {}):
            self.assertIsNone(mss._reparse_mod_after_writes(self.state))
        self.assertIsNone(mss._company_catalog_cache)
        self.assertIn('building_e', self.rows()['company_generic']['building_types'])
        self.assertNotIn('company_generic', self.request('/building-companies/building_d')[1]['roster'])

    def test_snapshot_source_uses_backing_json_even_if_raw_vanilla_is_present(self):
        with mock.patch.object(mss, '_vanilla_source', {'kind': 'vanilla_parsed'}):
            rows = self.rows()
        self.assertEqual(rows['company_flavored']['source_files'], [
            {'source': 'vanilla', 'file': 'vanilla_parsed/common/company_types.json'},
        ])
        self.assertEqual(rows['company_generic']['source'], 'mod')

    def test_committed_snapshot_and_real_mod_company_patches(self):
        repo = Path(__file__).resolve().parent
        vanilla = {}
        for label, filename in (('Company Types', 'company_types'), ('Buildings', 'buildings')):
            vanilla[label] = vanilla_parsed.decode(json.loads(
                (repo / 'vanilla_parsed/common' / (filename + '.json')).read_text(encoding='utf-8')))
        mod_dirs = {label: str(repo / 'common' / directory)
                    for label, directory in (('Company Types', 'company_types'), ('Buildings', 'buildings'))}
        state = ModState(dict.fromkeys(vanilla, '/nonexistent'), mod_dirs, vanilla_data=vanilla)
        with mock.patch.multiple(mss, ms=state, mod_path=str(repo), mod_paths=mod_dirs,
                                 _vanilla_source={'kind': 'vanilla_parsed'}):
            rows = self.rows('?flavored=no')
            biotech = rows['company_basic_biotechnology']
            self.assertEqual(biotech['source'], 'mod')
            self.assertEqual(biotech['effect_count'], 2)
            self.assertTrue(biotech['flagship'])
            for bid in biotech['building_types']:
                self.assertIn('company_basic_biotechnology', self.request('/building-companies/' + bid)[1]['roster'])


if __name__ == '__main__':
    unittest.main()
