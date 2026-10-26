"""Game-independent fixtures for GUI cross-reference extraction and severity."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import gui_reference_audit as audit
import loc_coverage_audit as loc


class GuiReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'mod'
        self.root.mkdir()
        self.write('common/scripted_guis/test.txt', '''good = {
 saved_scopes = { op }
 is_shown = { always = yes }
 is_valid = { scope:op = 1 }
}''')
        self.write('common/script_values/test.txt', 'scalar = 1\nblock = { value = 2 }\n')
        self.write('common/customizable_localization/test.txt', 'custom = { text = { localization_key = LABEL } }')
        self.write('common/static_modifiers/test.txt', 'bonus = { prestige = 1 }')
        self.write('localization/english/test.yml', 'l_english:\n LABEL:0 "Hello"\n')

    def write(self, rel, text, base=None, bom=False):
        path = (base or self.root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8-sig' if bom else 'utf-8')
        return path

    def gui(self, text, bom=True):
        return self.write('gui/test.gui', text, bom=bom)

    def run_audit(self, vanilla=None):
        return audit.audit(self.root, vanilla or self.root / 'missing')

    def errors(self, result):
        return [(f.kind, f.name) for f in result.flags if f.severity == 'error']

    def test_all_reference_categories_and_scalar_values(self):
        self.gui('''widget = {
 text = "LABEL"
 tooltip = "[Localize('LABEL')]"
 datacontext = "[GetScriptedGui('good')]"
 value = "[Scope.ScriptValue('scalar')]"
 other = "[Scope.ScriptValue('block')]"
 custom = "[Scope.GetCustom('custom')]"
 bonus = "[GetStaticModifier('bonus')]"
 onclick = "[GetScriptedGui('good').Execute(GuiScope.AddScope('op', MakeScopeValue('1')).End)]"
}''')
        result = self.run_audit()
        self.assertEqual([], self.errors(result))
        for kind in audit.CALLS:
            self.assertTrue(result.references['gui/test.gui'][kind])
            self.assertTrue(all(r['resolved'] for r in result.references['gui/test.gui'][kind]))
        self.assertEqual(5, result.references['gui/test.gui']['script_values'][0]['line'])

    def test_comments_and_quoted_hashes_braces(self):
        self.gui('''# GetScriptedGui('missing') { visible = yes
widget = { text = "[Localize('LABEL')] # { } \\"quoted\\""
 # }
 raw_text = "Literal { # }"
}''')
        self.assertEqual([], self.errors(self.run_audit()))

    def test_bom_structure_and_inline_duplicate_visible(self):
        self.gui('widget = { visible = yes visible = no }\n}', bom=False)
        self.assertEqual({'bom', 'braces', 'duplicate_visible'}, {k for k, _ in self.errors(self.run_audit())})
        self.gui('widget = { visible = yes widget = { visible = no } }')
        self.assertEqual([], self.errors(self.run_audit()))
        self.gui('widget = {')
        self.assertIn(('braces', '{'), self.errors(self.run_audit()))

    def test_mod_scripted_gui_typo_always_errors(self):
        self.gui('widget = { onclick = "[GetScriptedGui(\'typo\')]" }')
        self.assertIn(('scripted_guis', 'typo'), self.errors(self.run_audit()))

    def test_unavailable_vanilla_warns_and_live_vanilla_errors(self):
        self.gui('''widget = { text = "MISSING"
 value = "[Scope.ScriptValue('missing')]"
 custom = "[Scope.GetCustom('missing')]"
 bonus = "[GetStaticModifier('missing')]"
}''')
        result = self.run_audit()
        self.assertEqual([('custom_loc', 'missing')], self.errors(result))
        self.assertEqual(4, len(result.flags))
        vanilla = self.root.parent / 'vanilla'
        for directory in audit.DIRS.values():
            (vanilla / 'game/common' / directory).mkdir(parents=True)
        (vanilla / 'game/localization/english').mkdir(parents=True)
        self.assertEqual(4, self.run_audit(vanilla).errors)

    def test_snapshot_localization_and_script_values(self):
        self.write('vanilla_parsed/localization_english.json', json.dumps({'VANILLA': 'Text'}))
        self.write('vanilla_parsed/common/script_values.json', json.dumps({'vanilla_value': 1}))
        self.gui('''widget = { text = "VANILLA" tooltip = "TYPO"
 value = "[Scope.ScriptValue('vanilla_value')]"
 other = "[Scope.ScriptValue('typo')]"
}''')
        self.assertEqual({('loc_keys', 'TYPO'), ('script_values', 'typo')}, set(self.errors(self.run_audit())))

    def test_scripted_constant_is_not_a_script_value(self):
        self.write('vanilla_parsed/common/script_values.json', json.dumps({}))
        self.write('common/script_values/consts.txt', '@only_const = 3\nreal_value = { value = @only_const }\n')
        self.gui('''widget = {
 value = "[Scope.ScriptValue('only_const')]"
 other = "[Scope.ScriptValue('real_value')]"
}''')
        self.assertEqual([('script_values', 'only_const')], self.errors(self.run_audit()))

    def test_defined_names_merge_directives(self):
        # #1180: only the *_OR_CREATE directives define the entry they name.
        text = """INJECT:a = { x = 1 }
REPLACE:b = { x = 1 }
TRY_INJECT:c = { x = 1 }
TRY_REPLACE:d = { x = 1 }
INJECT_OR_CREATE:e = { x = 1 }
REPLACE_OR_CREATE:f = { x = 1 }
@g = 1
h = 1
i = { nested = 1 }
# commented = 1
"""
        self.assertEqual({'e', 'f', 'h', 'i'}, audit.defined_names(text))

    def test_inject_or_replace_with_no_base_does_not_resolve(self):
        # Every kind: an INJECT:/TRY_REPLACE: name resolves only through a
        # definition of its own, mod or vanilla; *_OR_CREATE: names define.
        vanilla = self.root.parent / 'vanilla'
        calls = {'script_values': "Scope.ScriptValue('{}')", 'static_modifiers': "GetStaticModifier('{}')",
                 'scripted_guis': "GetScriptedGui('{}')", 'custom_loc': "Scope.GetCustom('{}')"}
        names = ('inject_only', 'try_replace_only', 'created', 'recreated', 'vanilla_base', 'mod_base')
        for kind, directory in audit.DIRS.items():
            self.write(f'common/{directory}/directives.txt', """INJECT:inject_only = { x = 1 }
TRY_REPLACE:try_replace_only = { x = 1 }
INJECT_OR_CREATE:created = { x = 1 }
REPLACE_OR_CREATE:recreated = { x = 1 }
INJECT:vanilla_base = { x = 1 }
REPLACE:mod_base = { x = 1 }
""")
            self.write(f'common/{directory}/base.txt', 'mod_base = { x = 1 }\n')
            self.write(f'game/common/{directory}/vanilla.txt', 'vanilla_base = { x = 1 }\n', base=vanilla)
        self.gui('widget = {\n' + ''.join(
            f' p{n} = "[{calls[kind].format(name)}]"\n'
            for n, (kind, name) in enumerate((k, nm) for k in calls for nm in names)) + '}')
        refs = self.run_audit(vanilla).references['gui/test.gui']
        for kind in calls:
            resolved = {r['name']: r['resolved'] for r in refs[kind]}
            self.assertEqual({'inject_only': False, 'try_replace_only': False, 'created': True,
                              'recreated': True, 'vanilla_base': True, 'mod_base': True},
                             resolved, kind)
        errors = self.errors(self.run_audit(vanilla))
        for kind in calls:
            self.assertIn((kind, 'inject_only'), errors)
            self.assertIn((kind, 'try_replace_only'), errors)

    def test_inject_of_a_snapshot_name_resolves_offline(self):
        # No game install: an INJECT: of a vanilla script value or static
        # modifier still resolves through the committed snapshot.
        self.write('vanilla_parsed/common/script_values.json', json.dumps({'vanilla_sv': 1}))
        self.write('vanilla_parsed/common/modifiers.json', json.dumps({'vanilla_mod': 1}))
        self.write('common/script_values/inject.txt', 'INJECT:vanilla_sv = { add = 1 }\nINJECT:gone_sv = { add = 1 }\n')
        self.write('common/static_modifiers/inject.txt', 'INJECT:vanilla_mod = { x = 1 }\nREPLACE:gone_mod = { x = 1 }\n')
        self.gui('''widget = {
 a = "[Scope.ScriptValue('vanilla_sv')]"
 b = "[Scope.ScriptValue('gone_sv')]"
 c = "[GetStaticModifier('vanilla_mod')]"
 d = "[GetStaticModifier('gone_mod')]"
}''')
        self.assertEqual({('script_values', 'gone_sv'), ('static_modifiers', 'gone_mod')},
                         set(self.errors(self.run_audit())))

    def test_saved_scope_not_hidden_by_unrelated_sgui(self):
        self.write('common/scripted_guis/other.txt', 'other = { saved_scopes = { typo } }')
        self.gui('''widget = {
 datacontext = "[GetScriptedGui('other')]"
 onclick = "[GetScriptedGui('good').Execute(GuiScope.AddScope('typo', Scope.MakeScope).End)]"
}''')
        self.assertIn(('saved_scopes', 'typo'), self.errors(self.run_audit()))

    def test_two_receivers_in_one_expression_validate_separately(self):
        self.write('common/scripted_guis/other.txt', 'other = { saved_scopes = { typo } }')
        self.gui("""widget = {
 text = "[Concatenate(GetScriptedGui('good').ExecuteTooltip(GuiScope.AddScope('typo', MakeScopeValue('(CFixedPoint)1')).End), GetScriptedGui('other').ExecuteTooltip(GuiScope.AddScope('typo', Scope.MakeScope).End))]"
}""")
        flags = [f for f in self.run_audit().flags if f.kind == 'saved_scopes']
        self.assertEqual(1, len(flags))
        self.assertIn('good', flags[0].detail)

    def test_progress_bar_coverage_runs_on_explicit_fields(self):
        self.write('common/scripted_progress_bars/bar.txt', 'bar = {\n name = LABEL\n desc = MISSING\n}\n')
        ms = SimpleNamespace(base_parsers={}, mod_parsers={
            'Scripted Progress Bars': SimpleNamespace(data={'bar': ('=', {'name': ('=', 'LABEL'), 'desc': ('=', 'MISSING')})})
        }, has_localization=lambda key: key == 'LABEL')
        result = loc.audit(ms, str(self.root))
        self.assertEqual(['MISSING'], result.flags[0].missing_keys)

    def test_dynamic_scope_binding_is_explicit_warning(self):
        self.gui('widget = { onclick = "[ScriptedGui.Execute(GuiScope.AddScope(\'op\', Scope.MakeScope).End)]" }')
        self.assertEqual([], self.errors(self.run_audit()))
        self.assertEqual('saved_scopes', self.run_audit().flags[0].kind)

    def test_is_shown_is_brace_aware_not_is_valid(self):
        self.gui('widget = {}')
        self.assertFalse(any(f.kind == 'is_shown_scope' for f in self.run_audit().flags))
        self.write('common/scripted_guis/shown.txt', '''shown = {
 saved_scopes = { op }
 is_shown = { if = { limit = { scope:op = 1 } always = yes } }
}''')
        flags = [f for f in self.run_audit().flags if f.kind == 'is_shown_scope']
        self.assertEqual(['shown'], [f.name for f in flags])
        self.assertEqual('warn', flags[0].severity)

    def test_mount_requires_name_in_exact_file_and_not_nested_control(self):
        self.gui('types = { type Good = widget {} }\nwidget = { name = "root" widget = { name = "nested" } }')
        self.write('gui/elsewhere.gui', 'widget = { name = "elsewhere" }', bom=True)
        je = 'common/journal_entries/test.txt'
        for name in ['Good', 'root']:
            self.write(je, f'entry = {{ widget = {{ gui = "gui/test.gui" name = "{name}" }} }}')
            self.assertEqual([], self.errors(self.run_audit()))
        for name in ['nested', 'elsewhere', 'typo']:
            self.write(je, f'entry = {{ widget = {{ gui = "gui/test.gui" name = "{name}" }} }}')
            self.assertIn(('mount', name), self.errors(self.run_audit()))
        self.write(je, 'entry = { widget = { gui = "gui/no.gui" name = "root" } }')
        self.assertIn(('mount', 'gui/no.gui'), self.errors(self.run_audit()))

    def test_inherited_vanilla_custom_loc_warns_offline_and_errors_with_vanilla(self):
        self.gui('''widget = { custom = "[Law.GetCountry.GetCustom('enactment_phase_1')]"
 typo = "[Law.GetCountry.GetCustom('enactment_phase_9')]"
}''')
        result = self.run_audit()
        self.assertEqual([('custom_loc', 'enactment_phase_9')], self.errors(result))
        self.assertEqual(2, len(result.flags))
        vanilla = self.root.parent / 'vanilla'
        (vanilla / 'game/common/customizable_localization').mkdir(parents=True)
        self.assertIn(('custom_loc', 'enactment_phase_1'), self.errors(self.run_audit(vanilla)))

    def test_missing_types_warn_offline_error_with_vanilla(self):
        self.gui('types = { type Local = widget {} }\nLocal = {}\nTypo = {}')
        self.assertEqual([], self.errors(self.run_audit()))
        vanilla = self.root.parent / 'game'
        (vanilla / 'gui').mkdir(parents=True)
        self.assertIn(('gui_types', 'Typo'), self.errors(self.run_audit(vanilla)))

    def test_cli_no_writes_strict_status_and_regenerate(self):
        self.gui('widget = { onclick = "[GetScriptedGui(\'bad\')]" }')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, audit.main(['--strict', '--mod-path', str(self.root), '--vanilla-path', str(self.root / 'absent')]))
            self.assertEqual(0, audit.main(['--mod-path', str(self.root), '--vanilla-path', str(self.root / 'absent')]))
        self.assertFalse((self.root / 'docs').exists())
        with patch('path_constants.mod_path', str(self.root)):
            summary = audit.regenerate(None)
        self.assertEqual(1, summary['unreviewed'])
        self.assertTrue((self.root / 'docs/engine/gui_reference_report.md').exists())

    def test_progress_bar_explicit_keys(self):
        self.assertEqual([('TITLE', True, 'name'), ('DETAIL', True, 'desc')],
                         loc._REQUIREMENTS['Scripted Progress Bars']('bar', {'name': ('=', '"TITLE"'), 'desc': ('=', 'DETAIL')}))
        self.assertEqual('common/scripted_progress_bars', loc._DIR_MAP['Scripted Progress Bars'])


if __name__ == '__main__':
    unittest.main()
