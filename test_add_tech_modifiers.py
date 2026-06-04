"""Idempotency regression tests for scripts/generators/add_tech_modifiers.py (issue #191).

The generator splices unlock-bool modifiers into tech `modifier = { }` blocks. Before
the #191 fix it appended unconditionally, so a second run doubled every modifier (the
engine's `Duplicated key` warning only catches top-level entity collisions, never
duplicate keys inside a block). These tests pin the "already present → skip" guard,
including the partial-overlap case (some bools present, one genuinely new).

Run: .venv/bin/python test_add_tech_modifiers.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts' / 'generators'))
import add_tech_modifiers as atm  # noqa: E402


def _read(path):
    with open(path, encoding='utf-8-sig') as f:
        return f.read()


class _TmpFileMixin(unittest.TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix='.txt')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path


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


if __name__ == '__main__':
    unittest.main()
