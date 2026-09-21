"""Idempotency regression tests for scripts/generators/add_tech_modifiers.py (issue #191).

The generator splices unlock-bool modifiers into tech `modifier = { }` blocks. Before
the #191 fix it appended unconditionally, so a second run doubled every modifier (the
engine's `Duplicated key` warning only catches top-level entity collisions, never
duplicate keys inside a block). These tests pin the "already present → skip" guard,
including the partial-overlap case (some bools present, one genuinely new).

Two further destructive behaviours are pinned here as well:

* Step 1 used to regenerate `tech_gate_modifier_types.txt` from scratch with
  `open(..., 'w')`, deleting every hand-maintained definition it had no table entry for
  — notably the `country_sr_*_program_bool` space-program block, without which the space
  race silently never activates. It now merges in only what is missing.
* Step 6 only checked for pre-existing loc keys in the single file it appends to, so the
  ~104 keys that had since migrated to other `localization/english/*.yml` files were
  re-appended on every run. The check is now cross-file.

The end-to-end test builds a throwaway mod tree and asserts a second full run is
byte-for-byte a no-op — the unit-level form of "running it on a clean checkout leaves
`git status` clean". Nothing here touches the real tree or needs Victoria 3 installed.

Run: .venv/bin/python test_add_tech_modifiers.py
"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts' / 'generators'))
import add_tech_modifiers as atm  # noqa: E402


def _read(path):
    with open(path, encoding='utf-8-sig') as f:
        return f.read()


def _read_bytes(path):
    with open(path, 'rb') as f:
        return f.read()


class _TmpFileMixin(unittest.TestCase):
    def _write(self, text, bom=False):
        fd, path = tempfile.mkstemp(suffix='.txt')
        os.close(fd)
        with open(path, 'w', encoding='utf-8-sig' if bom else 'utf-8') as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path

    def _tmpdir(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return d.name


class FilterNewModifiersTests(unittest.TestCase):
    def test_returns_only_absent_preserving_order(self):
        body = "\n\t\talpha_bool = yes\n\t\tbeta_bool = yes\n"
        self.assertEqual(atm._filter_new_modifiers(body, ['alpha_bool', 'gamma_bool']), ['gamma_bool'])
        self.assertEqual(atm._filter_new_modifiers(body, ['gamma_bool', 'alpha_bool', 'delta_bool']),
                         ['gamma_bool', 'delta_bool'])

    def test_all_present_returns_empty(self):
        body = "\n\t\talpha_bool = yes\n\t\tbeta_bool = yes\n"
        self.assertEqual(atm._filter_new_modifiers(body, ['alpha_bool', 'beta_bool']), [])

    def test_no_substring_false_match(self):
        # `foo_bool` must NOT be considered present just because `foo_bool_extra` is.
        body = "\n\t\tcountry_foo_bool_extra = yes\n\t\tfoo_bool_v2 = yes\n"
        self.assertEqual(atm._filter_new_modifiers(body, ['foo_bool']), ['foo_bool'])


class TechFileTests(_TmpFileMixin):
    TECH = (
        "my_tech = {\n"
        "\tera = era_6\n"
        "\tmodifier = {\n"
        "\t\tcountry_x_add = 5\n"
        "\t}\n"
        "}\n"
    )

    def test_second_run_is_a_noop(self):
        path = self._write(self.TECH)
        mmap = {'my_tech': ['foo_bool', 'bar_bool']}
        self.assertTrue(atm.add_modifiers_to_tech_file(path, mmap))   # 1st run mutates
        self.assertFalse(atm.add_modifiers_to_tech_file(path, mmap))  # 2nd run no-op
        out = _read(path)
        self.assertEqual(out.count('foo_bool = yes'), 1)
        self.assertEqual(out.count('bar_bool = yes'), 1)
        self.assertEqual(out.count('country_x_add = 5'), 1)  # pre-existing content untouched

    def test_partial_overlap_adds_only_the_new_one(self):
        text = (
            "my_tech = {\n"
            "\tmodifier = {\n"
            "\t\tfoo_bool = yes\n"
            "\t}\n"
            "}\n"
        )
        path = self._write(text)
        # foo_bool already present; run adds [foo_bool, baz_bool] — only baz_bool should land.
        self.assertTrue(atm.add_modifiers_to_tech_file(path, {'my_tech': ['foo_bool', 'baz_bool']}))
        out = _read(path)
        self.assertEqual(out.count('foo_bool = yes'), 1)  # not duplicated
        self.assertEqual(out.count('baz_bool = yes'), 1)  # newly added


class InjectTests(_TmpFileMixin):
    def test_existing_inject_partial_overlap_and_idempotent(self):
        text = (
            "INJECT:vanilla_tech = {\n"
            "\tmodifier = {\n"
            "\t\texisting_bool = yes\n"
            "\t}\n"
            "}\n"
        )
        path = self._write(text)
        atm.add_inject_entries_to_modified(path, {'vanilla_tech': ['existing_bool', 'new_bool']})
        out = _read(path)
        self.assertEqual(out.count('existing_bool = yes'), 1)  # not doubled
        self.assertEqual(out.count('new_bool = yes'), 1)       # added
        # second run: nothing new
        atm.add_inject_entries_to_modified(path, {'vanilla_tech': ['existing_bool', 'new_bool']})
        out2 = _read(path)
        self.assertEqual(out2.count('new_bool = yes'), 1)
        self.assertEqual(out2.count('existing_bool = yes'), 1)

    def test_new_inject_created_once(self):
        path = self._write("# modified.txt header\n")
        atm.add_inject_entries_to_modified(path, {'brand_new_tech': ['a_bool']})
        out = _read(path)
        self.assertEqual(out.count('INJECT:brand_new_tech'), 1)
        self.assertEqual(out.count('a_bool = yes'), 1)
        # second run must NOT create a duplicate INJECT block nor double the bool
        atm.add_inject_entries_to_modified(path, {'brand_new_tech': ['a_bool']})
        out2 = _read(path)
        self.assertEqual(out2.count('INJECT:brand_new_tech'), 1)
        self.assertEqual(out2.count('a_bool = yes'), 1)


class ModifierTypeMergeTests(_TmpFileMixin):
    """Step 1 must merge, never regenerate (the space-program regression)."""

    # Shape of the real hand-maintained block the old `open(..., 'w')` deleted every run.
    HAND_BLOCK = (
        '# Space Program building PM unlock modifiers\n'
        '# REQUIRED: without these the space race silently never activates.\n'
        'country_sr_earth_orbit_program_bool = {\n\tcolor = good\n\tboolean = yes\n}\n'
        'country_sr_moon_mission_program_bool = {\n\tcolor = good\n\tboolean = yes\n}\n\n'
    )

    def _fixture(self, omit=()):
        """A type file holding the hand block plus every expected definition but `omit`."""
        parts = ['# Boolean modifiers for technology-gated features.\n\n', self.HAND_BLOCK]
        for header, names in atm.expected_modifier_definitions():
            parts.append(header + '\n')
            parts.extend(atm._definition_block(n) for n in names if n not in omit)
        return self._write(''.join(parts), bom=True)

    def test_complete_file_is_not_rewritten_at_all(self):
        path = self._fixture()
        before = _read_bytes(path)
        self.assertFalse(atm.merge_modifier_type_definitions(path))
        self.assertEqual(_read_bytes(path), before)  # not even a BOM/whitespace round-trip

    def test_hand_maintained_block_survives_a_merge(self):
        principles = atm.expected_modifier_definitions()[0][1]
        missing = principles[0]
        path = self._fixture(omit={missing})

        self.assertTrue(atm.merge_modifier_type_definitions(path))
        out = _read(path)

        # The whole point of the merge rewrite: unrelated definitions are never pruned.
        self.assertIn('country_sr_earth_orbit_program_bool = {', out)
        self.assertIn('country_sr_moon_mission_program_bool = {', out)
        self.assertIn('# Space Program building PM unlock modifiers', out)
        # ...and the missing one landed, exactly once.
        self.assertEqual(out.count(f'{missing} = {{'), 1)

    def test_missing_definition_lands_in_its_own_section(self):
        principles = atm.expected_modifier_definitions()[0][1]
        missing = principles[-1]
        path = self._fixture(omit={missing})
        atm.merge_modifier_type_definitions(path)
        out = _read(path)

        pb_header = out.index(atm.PRINCIPLE_SECTION_HEADER)
        button_header = out.index(atm.BUTTON_SECTION_HEADER)
        self.assertTrue(pb_header < out.index(f'{missing} = {{') < button_header)

    def test_button_definition_lands_after_the_button_header(self):
        buttons = atm.expected_modifier_definitions()[1][1]
        missing = buttons[0]
        path = self._fixture(omit={missing})
        atm.merge_modifier_type_definitions(path)
        out = _read(path)
        self.assertGreater(out.index(f'{missing} = {{'), out.index(atm.BUTTON_SECTION_HEADER))

    def test_merge_is_idempotent(self):
        principles = atm.expected_modifier_definitions()[0][1]
        path = self._fixture(omit={principles[0], principles[3]})
        self.assertTrue(atm.merge_modifier_type_definitions(path))
        after_first = _read_bytes(path)
        self.assertFalse(atm.merge_modifier_type_definitions(path))
        self.assertEqual(_read_bytes(path), after_first)

    def test_creates_file_with_header_when_absent(self):
        path = os.path.join(self._tmpdir(), 'tech_gate_modifier_types.txt')
        self.assertTrue(atm.merge_modifier_type_definitions(path))
        out = _read(path)
        self.assertIn('HAND-MAINTAINED', out)
        for _, names in atm.expected_modifier_definitions():
            for name in names:
                self.assertEqual(out.count(f'{name} = {{'), 1)
        self.assertFalse(atm.merge_modifier_type_definitions(path))


class LocalizationTests(_TmpFileMixin):
    def test_pb_principle_desc_keys_are_never_emitted(self):
        """gen_pb_principle_unlock_descs.py owns those; two owners = duplicate_key_audit."""
        loc = atm.generate_localization()
        self.assertNotIn('_pb_principles_bool_desc', loc)
        self.assertIn('_pb_principles_bool:0', loc)  # the short label is still ours

    def test_existing_keys_are_read_from_every_yml_in_the_folder(self):
        root = self._tmpdir()
        loc_dir = os.path.join(root, 'localization', 'english')
        os.makedirs(loc_dir)
        for name, key in (('a_l_english.yml', 'alpha_bool'), ('b_l_english.yml', 'beta_bool')):
            with open(os.path.join(loc_dir, name), 'w', encoding='utf-8-sig') as f:
                f.write(f'l_english:\n {key}:0 "x"\n')
        keys = atm.existing_localization_keys(root)
        self.assertIn('alpha_bool', keys)
        self.assertIn('beta_bool', keys)

    def test_missing_localization_folder_is_tolerated(self):
        self.assertEqual(atm.existing_localization_keys(self._tmpdir()), set())


def _build_mod_tree(root):
    """A throwaway mod tree wired exactly like the real one, from the live tables."""
    def write(rel, text):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8-sig') as f:
            f.write(text)

    mod_techs = sorted(
        (set(atm.PRINCIPLE_TECH_MODIFIERS) | set(atm.BUTTON_TECH_MODIFIERS)) - atm.VANILLA_TECHS
    )
    write('common/technology/technologies/era_6.txt', ''.join(
        f'{tech} = {{\n\tera = era_6\n\tcategory = production\n'
        f'\tmodifier = {{\n\t\tcountry_pre_existing_add = 5\n\t}}\n}}\n\n'
        for tech in mod_techs
    ))
    write('common/technology/technologies/modified.txt', '# modified.txt\n')

    # One `possible` clause per principle tech, in the pre-conversion form.
    write('common/power_bloc_principles/extra_power_bloc_principles.txt', ''.join(
        f'principle_{tech}_1 = {{\n\tpossible = {{\n'
        f'\t\thas_technology_researched = {tech}\n\t}}\n}}\n\n'
        for tech in sorted(atm.PRINCIPLE_TECH_MODIFIERS)
    ))

    by_file = {}
    for rel_path, button, tech, _ in atm.BUTTON_SPECIFIC_MAP:
        by_file.setdefault(rel_path, []).append((button, tech))
    for rel_path, buttons in by_file.items():
        write(rel_path, ''.join(
            f'{button} = {{\n\tvisible = {{\n'
            f'\t\thas_technology_researched = {tech}\n\t}}\n}}\n\n'
            for button, tech in buttons
        ))

    write('common/modifier_type_definitions/tech_gate_modifier_types.txt',
          '# Boolean modifiers for technology-gated features.\n\n'
          + ModifierTypeMergeTests.HAND_BLOCK)
    write('localization/english/te_modifiers_l_english.yml',
          'l_english:\n some_unrelated_key:0 "x"\n')


def _snapshot(root):
    return {
        os.path.relpath(os.path.join(dirpath, name), root): _read_bytes(os.path.join(dirpath, name))
        for dirpath, _, names in os.walk(root)
        for name in names
    }


class EndToEndIdempotencyTests(_TmpFileMixin):
    """`main()` twice over must be a byte-level no-op the second time."""

    def _run(self, root):
        with redirect_stdout(io.StringIO()):
            atm.main(root)

    def test_second_full_run_changes_nothing(self):
        root = self._tmpdir()
        _build_mod_tree(root)

        self._run(root)
        after_first = _snapshot(root)
        self._run(root)
        after_second = _snapshot(root)

        self.assertEqual(sorted(after_first), sorted(after_second))
        for rel in after_first:
            self.assertEqual(after_first[rel], after_second[rel], f'{rel} changed on the 2nd run')

    def test_first_run_actually_did_the_work(self):
        """Guards against the no-op above passing because main() does nothing at all."""
        root = self._tmpdir()
        _build_mod_tree(root)
        self._run(root)

        types_file = _read(os.path.join(
            root, 'common/modifier_type_definitions/tech_gate_modifier_types.txt'))
        self.assertIn('country_sr_earth_orbit_program_bool = {', types_file)  # hand block kept
        for _, names in atm.expected_modifier_definitions():
            for name in names:
                self.assertEqual(types_file.count(f'{name} = {{'), 1)

        principles = _read(os.path.join(
            root, 'common/power_bloc_principles/extra_power_bloc_principles.txt'))
        self.assertNotIn('has_technology_researched', principles)

        era = _read(os.path.join(root, 'common/technology/technologies/era_6.txt'))
        for tech in sorted(set(atm.PRINCIPLE_TECH_MODIFIERS) - atm.VANILLA_TECHS):
            bool_name = atm.PRINCIPLE_TECH_MODIFIERS[tech][0]
            self.assertEqual(era.count(f'{bool_name} = yes'), 1, bool_name)
        # pre-existing modifier content survived the splice, once per tech
        mod_techs = (
            set(atm.PRINCIPLE_TECH_MODIFIERS) | set(atm.BUTTON_TECH_MODIFIERS)
        ) - atm.VANILLA_TECHS
        self.assertEqual(era.count('country_pre_existing_add = 5'), len(mod_techs))

        modified = _read(os.path.join(root, 'common/technology/technologies/modified.txt'))
        for tech in sorted(atm.VANILLA_TECHS):
            self.assertEqual(modified.count(f'INJECT:{tech}'), 1)

    def test_localization_key_living_in_another_file_is_not_re_added(self):
        root = self._tmpdir()
        _build_mod_tree(root)
        loc_dir = os.path.join(root, 'localization', 'english')

        # The real-world case: the key migrated to a topical file years ago.
        migrated = atm.expected_modifier_definitions()[0][1][0]
        with open(os.path.join(loc_dir, 'te_power_bloc_unlocks_l_english.yml'),
                  'w', encoding='utf-8-sig') as f:
            f.write(f'l_english:\n {migrated}:0 "Enables [GetTechnology(\'x\').GetName]"\n')

        self._run(root)
        te_modifiers = _read(os.path.join(loc_dir, 'te_modifiers_l_english.yml'))
        self.assertNotIn(f' {migrated}:0', te_modifiers)


if __name__ == '__main__':
    unittest.main()
