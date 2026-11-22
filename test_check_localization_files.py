"""Unit tests for scripts/analysis/check_localization_files.py (issue #247).

The loc loader fails silently on a missing BOM, a missing `l_english:` header, or
a key defined twice, so these are exactly the cases CI has to catch. Quote marks
are checked because the repo's own loc tools misread a bare inner quote.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "analysis"))

from check_localization_files import (  # noqa: E402
    check_file,
    check_replace_shadows,
    check_tm_file,
    escape_quoted_splices,
    iter_loc_files,
    iter_tm_files,
    main,
    unescaped_quoted_splices,
)

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
            os.makedirs(os.path.dirname(path), exist_ok=True)
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

    def test_header_follows_the_file_name_language(self):
        text = BOM + 'l_german:\n TE_ALPHA:0 "Alpha"\n'
        self.assertEqual(_check(text, name="te_test_l_german.yml"), [])

    def test_english_header_in_a_german_file_is_flagged(self):
        problems = _check(GOOD, name="te_test_l_german.yml")
        self.assertEqual(len(problems), 1)
        self.assertIn("expected 'l_german:'", problems[0])

    def test_name_without_language_suffix_is_flagged(self):
        problems = _check(GOOD, name="te_test.yml")
        self.assertEqual(len(problems), 1)
        self.assertIn("_l_<language>.yml", problems[0])


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


class QuoteTests(unittest.TestCase):
    """The game reads a value to the line's last quote; the repo's loc tools
    (split_loc_line) stop at the first bare one, so literal quotes are `\\"`."""

    def test_escaped_quotes_in_pairs_pass(self):
        text = BOM + 'l_english:\n TE_ALPHA:0 "\\"Go,\\" he said. \\"Now.\\""\n'
        self.assertEqual(_check(text), [])

    def test_bare_inner_quote_is_flagged(self):
        text = BOM + 'l_english:\n TE_ALPHA:0 "A "Held" row"\n'
        problems = _check(text)
        self.assertEqual(len(problems), 1)
        self.assertIn(":2:", problems[0])
        self.assertIn("bare", problems[0])

    def test_bare_quote_before_a_format_code_is_flagged(self):
        # Parses as an empty value plus a "comment" that is really the text.
        text = BOM + 'l_english:\n TE_ALPHA:0 ""#bold I accuse#! them.""\n'
        self.assertEqual(len(_check(text)), 1)

    def test_trailing_comment_after_the_value_is_allowed(self):
        text = BOM + 'l_english:\n TE_ALPHA:0 "Alpha" # REVIEWED 2026-10-03: checked\n'
        self.assertEqual(_check(text), [])

    def test_quote_in_a_trailing_comment_is_flagged(self):
        # The game would read the comment up to its quote as part of the value.
        text = BOM + 'l_english:\n TE_ALPHA:0 "Alpha" # REVIEWED 2026-10-03: "quoted"\n'
        self.assertEqual(len(_check(text)), 1)

    def test_unpaired_escaped_quote_is_flagged(self):
        text = BOM + 'l_english:\n TE_ALPHA:0 "\\"Opened and never closed."\n'
        problems = _check(text)
        self.assertEqual(len(problems), 1)
        self.assertIn("unpaired", problems[0])

    def test_escaped_backslash_before_a_quote_is_not_an_escaped_quote(self):
        text = BOM + 'l_english:\n TE_ALPHA:0 "C:\\\\"\n'
        self.assertEqual(_check(text), [])


class VersionSpaceTests(unittest.TestCase):
    """`KEY:0 "value"`: the version digit is followed by a space. `KEY:0"value"`
    is a typo (an editor dropping the trailing space); neither vanilla nor the
    mod writes it. `KEY:"value"` with no digit is the mod's own older form and
    renders in game (the banking buttons), so it stays allowed."""

    def test_version_digit_glued_to_the_quote_is_flagged(self):
        text = BOM + 'l_english:\n TE_ALPHA:0"Alpha"\n'
        problems = _check(text)
        self.assertEqual(len(problems), 1)
        self.assertIn(":2:", problems[0])
        self.assertIn("TE_ALPHA", problems[0])
        self.assertIn("space", problems[0])

    def test_no_version_and_no_space_is_allowed(self):
        text = BOM + 'l_english:\n TE_ALPHA:"Alpha"\n TE_BETA: "Beta"\n'
        self.assertEqual(_check(text), [])


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
        paths = iter_loc_files([repo_loc])
        for path in paths:
            problems.extend(check_file(path))
        problems.extend(check_replace_shadows(paths))
        self.assertEqual(problems, [], "\n".join(problems))


class ReplaceShadowTests(unittest.TestCase):
    """Check 10: a key a `replace/` file overrides, defined again in an
    ordinary file of the same language (#1406's goods_output_fertilizer_mult)."""

    def _problems(self, files: dict) -> list[str]:
        with _TempLoc(files) as d:
            return check_replace_shadows(iter_loc_files([d]))

    def test_key_in_replace_and_an_ordinary_file_is_flagged_on_the_ordinary_copy(self):
        problems = self._problems({
            "english/replace/te_override_l_english.yml": BOM + 'l_english:\n TE_ALPHA:0 "A"\n',
            "english/te_misc_l_english.yml": BOM + 'l_english:\n TE_BETA:0 "B"\n TE_ALPHA:0 "A"\n',
        })
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("te_misc_l_english.yml:3: 'TE_ALPHA'", problems[0])
        self.assertIn("te_override_l_english.yml:2", problems[0])

    def test_keys_only_in_replace_or_only_outside_pass(self):
        self.assertEqual(self._problems({
            "english/replace/te_override_l_english.yml": BOM + 'l_english:\n TE_ALPHA:0 "A"\n',
            "english/te_misc_l_english.yml": BOM + 'l_english:\n TE_BETA:0 "B"\n',
        }), [])

    def test_another_languages_replace_folder_does_not_count(self):
        self.assertEqual(self._problems({
            "german/replace/te_override_l_german.yml": BOM + 'l_german:\n TE_ALPHA:0 "A"\n',
            "english/te_misc_l_english.yml": BOM + 'l_english:\n TE_ALPHA:0 "A"\n',
        }), [])

    def test_any_folder_layout_counts_by_the_file_names_language(self):
        problems = self._problems({
            "replace/te_override_l_english.yml": BOM + 'l_english:\n TE_ALPHA:0 "A"\n',
            "english/sub/te_misc_l_english.yml": BOM + 'l_english:\n TE_ALPHA:0 "A"\n',
        })
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("te_misc_l_english.yml:2: 'TE_ALPHA'", problems[0])

    def test_main_fails_on_a_shadowed_key(self):
        with _TempLoc({
            "english/replace/te_override_l_english.yml": BOM + 'l_english:\n TE_ALPHA:0 "A"\n',
            "english/te_misc_l_english.yml": BOM + 'l_english:\n TE_ALPHA:0 "A"\n',
        }) as d:
            self.assertEqual(main([d]), 1)



class QuoteEscapingTests(unittest.TestCase):
    """Check 9: from 1.15 a `$key$` inside a loc function's quoted argument
    needs the `q` flag; the game logs "missing required quote-escaping"."""

    def test_unescaped_concept_display_splice_is_flagged(self):
        text = BOM + "l_english:\n TE_ALPHA:0 \"[Concept('concept_pop','$concept_pops$')] grow\"\n"
        problems = _check(text)
        self.assertEqual(len(problems), 1)
        self.assertIn(":2:", problems[0])
        self.assertIn("`$concept_pops$`", problems[0])
        self.assertIn("quote-escaping", problems[0])

    def test_escaped_splices_pass(self):
        text = (BOM + "l_english:\n TE_ALPHA:0 \"[Concept('concept_pop','$concept_pops|q$')]\"\n"
                " TE_BETA:0 \"[ConcatIfNeitherEmpty('$VALUE|%0q$', '\\n')]\"\n")
        self.assertEqual(_check(text), [])

    def test_splices_outside_quoted_arguments_pass(self):
        # Top level, and a prose apostrophe outside brackets that must not pair
        # with an argument's quote.
        text = BOM + "l_english:\n TE_ALPHA:0 \"It's $concept_pops$ and [GetPlayer.GetName]'s $X$\"\n"
        self.assertEqual(_check(text), [])

    def test_other_functions_and_flagged_splices_are_flagged(self):
        problems = _check(BOM + "l_english:\n TE_ALPHA:0 \"#tooltip:[GetRawTextTooltipTag('$DESC$')] [ConcatIfNeitherEmpty('$VALUE|v$', '\\n')]\"\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("`$DESC$`, `$VALUE|v$`", problems[0])

    def test_escape_appends_q_to_existing_flags(self):
        self.assertEqual(
            escape_quoted_splices("[Concept('c','$a$')] $b$ [F('$x|v$', '$y|q$')]"),
            ("[Concept('c','$a|q$')] $b$ [F('$x|vq$', '$y|q$')]", 2))
        self.assertEqual(unescaped_quoted_splices("[A('[concept_x] $k$')] '$p$'"), ["$k$"])

    def test_translation_memory_fields_are_checked(self):
        records = {
            "TE_ALPHA": {"en": "[Concept('concept_pop','$concept_pops|q$')]",
                         "de": "[Concept('concept_pop','$concept_pops$')]"},
            "TE_ALPHA_GEN": {"base": "TE_ALPHA", "en": "x", "de": "y"},
        }
        with tempfile.TemporaryDirectory() as d:
            tm = os.path.join(d, "german", "tm")
            os.makedirs(tm)
            path = os.path.join(tm, "te_test.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(records, fh)
            self.assertEqual(iter_tm_files([d]), [path])
            problems = check_tm_file(path)
            self.assertEqual(main([d]), 1)
        self.assertEqual(len(problems), 1)
        self.assertIn("TE_ALPHA.de", problems[0])

    def test_repo_translation_memories_are_escaped(self):
        repo_i18n = os.path.join(os.path.dirname(os.path.abspath(__file__)), "i18n")
        problems = []
        for path in iter_tm_files([repo_i18n]):
            problems.extend(check_tm_file(path))
        self.assertEqual(problems, [], "\n".join(problems))


class SplitValueTests(unittest.TestCase):
    """A value written with a raw newline (a script's "\\n" instead of the
    two characters) leaves `key:0 "first part` on one line and the rest on the
    next. The game reads neither line as the value, and organize_loc keeps the
    first line as the whole value and drops the rest, after which nothing
    else flags it."""

    def test_a_value_with_no_closing_quote_is_flagged(self):
        problems = _check(BOM + 'l_english:\n TE_ALPHA:0 "first part\nsecond part"\n TE_BETA:0 "Beta"\n')
        self.assertTrue(any(":2:" in p and "no closing quote" in p and "TE_ALPHA" in p for p in problems), problems)
        self.assertTrue(any(":3:" in p and "not a key line" in p for p in problems), problems)

    def test_a_key_without_a_version_digit_is_a_key_line(self):
        self.assertEqual(_check(BOM + 'l_english:\n TE_ALPHA:"Alpha"\n'), [])

    def test_blank_and_comment_lines_are_not_stray(self):
        self.assertEqual(_check(BOM + 'l_english:\n\n # a section\n TE_ALPHA:0 "Alpha"\n'), [])


if __name__ == "__main__":
    unittest.main()
