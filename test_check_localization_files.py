"""Unit tests for scripts/analysis/check_localization_files.py (issue #247).

The loc loader fails silently on a missing BOM, a missing `l_english:` header, or
a key defined twice, so these are exactly the cases CI has to catch.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "analysis"))

from check_localization_files import check_file, iter_loc_files, main  # noqa: E402

BOM = "﻿"
GOOD = BOM + 'l_english:\n TE_ALPHA:0 "Alpha"\n TE_BETA:0 "Beta"\n'


class _TempLoc:
    """Write one or more loc files into a throwaway directory."""

    def __init__(self, files: dict):
        self.files = files

    def __enter__(self):
        self.dir = tempfile.TemporaryDirectory()
        for name, text in self.files.items():
            path = os.path.join(self.dir.name, name)
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
        return self.dir.name

    def __exit__(self, *exc):
        self.dir.cleanup()


def _check(text: str, name: str = "te_test_l_english.yml"):
    with _TempLoc({name: text}) as d:
        return check_file(os.path.join(d, name))


class CleanFileTests(unittest.TestCase):
    def test_well_formed_file_has_no_problems(self):
        self.assertEqual(_check(GOOD), [])

    def test_leading_comments_before_header_are_allowed(self):
        text = BOM + '# a comment\n\nl_english:\n TE_ALPHA:0 "Alpha"\n'
        self.assertEqual(_check(text), [])

    def test_same_key_in_two_different_files_is_not_a_duplicate(self):
        files = {
            "a_l_english.yml": BOM + 'l_english:\n TE_ALPHA:0 "A"\n',
            "b_l_english.yml": BOM + 'l_english:\n TE_ALPHA:0 "B"\n',
        }
        with _TempLoc(files) as d:
            problems = []
            for path in iter_loc_files([d]):
                problems.extend(check_file(path))
        self.assertEqual(problems, [])


class BomTests(unittest.TestCase):
    def test_missing_bom_is_flagged(self):
        problems = _check(GOOD[1:])
        self.assertEqual(len(problems), 1)
        self.assertIn("missing UTF-8 BOM", problems[0])
        self.assertIn(":1:", problems[0])

    def test_invalid_utf8_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "te_bad_l_english.yml")
            with open(path, "wb") as fh:
                fh.write(b"\xef\xbb\xbfl_english:\n TE_A:0 \"\xff\xfe\"\n")
            problems = check_file(path)
        self.assertEqual(len(problems), 1)
        self.assertIn("not valid UTF-8", problems[0])


class HeaderTests(unittest.TestCase):
    def test_wrong_header_is_flagged_with_its_line(self):
        text = BOM + '\n\nl_french:\n TE_ALPHA:0 "Alpha"\n'
        problems = _check(text)
        self.assertEqual(len(problems), 1)
        self.assertIn("expected 'l_english:'", problems[0])
        self.assertIn(":3:", problems[0])

    def test_empty_file_is_flagged(self):
        problems = _check(BOM + "\n\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("no content", problems[0])


class DuplicateKeyTests(unittest.TestCase):
    def test_duplicate_key_reports_both_lines(self):
        text = BOM + 'l_english:\n TE_ALPHA:0 "One"\n TE_BETA:0 "B"\n TE_ALPHA:0 "Two"\n'
        problems = _check(text)
        self.assertEqual(len(problems), 1)
        self.assertIn("duplicate key 'TE_ALPHA'", problems[0])
        self.assertIn(":4:", problems[0])
        self.assertIn("line 2", problems[0])

    def test_duplicate_inside_a_comment_is_ignored(self):
        text = BOM + 'l_english:\n TE_ALPHA:0 "One"\n# TE_ALPHA:0 "One"\n'
        self.assertEqual(_check(text), [])

    def test_version_suffix_variants_count_as_the_same_key(self):
        text = BOM + 'l_english:\n TE_ALPHA:0 "One"\n TE_ALPHA:1 "Two"\n'
        problems = _check(text)
        self.assertEqual(len(problems), 1)
        self.assertIn("duplicate key 'TE_ALPHA'", problems[0])


class MainTests(unittest.TestCase):
    def test_main_returns_zero_on_clean_tree(self):
        with _TempLoc({"te_ok_l_english.yml": GOOD}) as d:
            self.assertEqual(main([d]), 0)

    def test_main_returns_one_on_problem(self):
        with _TempLoc({"te_bad_l_english.yml": GOOD[1:]}) as d:
            self.assertEqual(main([d]), 1)

    def test_main_returns_one_when_nothing_found(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main([d]), 1)

    def test_repo_localization_tree_is_clean(self):
        """The committed loc tree must satisfy the check CI runs."""
        repo_loc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "localization")
        problems = []
        for path in iter_loc_files([repo_loc]):
            problems.extend(check_file(path))
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
