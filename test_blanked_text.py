"""Tests for blanked_text, the blanking the raw-text audits share (#1698).

The regex blanker must give exactly what the per-character loop it replaced
gave (kept here as `_reference`), on hand-made edge cases and on every script
file in the mod; and inside `shared()` a second caller must get the first
one's result without blanking again.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import blanked_text
import iterator_limit_audit
import modifier_multiplier_var_audit
from blanked_text import blank_comments_and_strings, shared

REPO = os.path.dirname(os.path.abspath(__file__))


def _reference(text: str) -> tuple[str, dict[int, str]]:
    """The loop `iterator_limit_audit` used until #1698, verbatim."""
    out = list(text)
    comments: dict[int, str] = {}
    line = 1
    i = 0
    n = len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            in_string = False
            i += 1
            continue
        if in_string:
            if ch == '"':
                in_string = False
            else:
                out[i] = " "
            i += 1
            continue
        if ch == '"':
            in_string = True
            i += 1
            continue
        if ch == "#":
            end = text.find("\n", i)
            if end < 0:
                end = n
            comments[line] = text[i:end]
            for j in range(i, end):
                out[j] = " "
            i = end
            continue
        i += 1
    return "".join(out), comments


EDGE_CASES = [
    "",
    '"',
    '""',
    '"a',
    '"a"',
    "#",
    '#"x"\n"#"',
    'a"b#c\nd"e',
    "\r\n#x\r\n",
    'x = "a" # c\n"\n#z',
    '"abc\n#d"\n"e"f"',
    'é # ü\n"ö"',
    "#a\n#b\n\n#c",
    'a\n"b\n"#c',
    'key = "x" key2 = "y" # REVIEWED 2026-01-01: why\n',
]


class MatchesTheOldLoopTests(unittest.TestCase):
    def test_edge_cases(self):
        for text in EDGE_CASES:
            with self.subTest(text=text):
                clean, comments = blank_comments_and_strings(text)
                self.assertEqual((clean, dict(comments)), _reference(text))
                self.assertEqual(len(clean), len(text))

    def test_every_mod_script_file(self):
        checked = 0
        for top in ("common", "events"):
            for root, _dirs, files in os.walk(os.path.join(REPO, top)):
                for name in files:
                    if not name.endswith(".txt"):
                        continue
                    path = os.path.join(root, name)
                    with open(path, encoding="utf-8-sig", errors="replace") as fh:
                        text = fh.read()
                    clean, comments = blank_comments_and_strings(text)
                    if (clean, dict(comments)) != _reference(text):
                        self.fail(f"{os.path.relpath(path, REPO)} blanks differently")
                    checked += 1
        self.assertGreater(checked, 500)

    def test_the_audits_use_the_shared_one(self):
        self.assertIs(iterator_limit_audit.blank_comments_and_strings,
                      blank_comments_and_strings)
        self.assertIs(modifier_multiplier_var_audit.blank_comments_and_strings,
                      blank_comments_and_strings)


class SharedCacheTests(unittest.TestCase):
    TEXT = 'a = { b = yes } # REVIEWED 2026-01-01: c\nd = "e"\n'

    def test_nothing_is_kept_outside_shared(self):
        blank_comments_and_strings(self.TEXT)
        self.assertEqual(blanked_text.cached_texts(), 0)
        with mock.patch.object(blanked_text, "_blank", wraps=blanked_text._blank) as spy:
            blank_comments_and_strings(self.TEXT)
            blank_comments_and_strings(self.TEXT)
        self.assertEqual(spy.call_count, 2)

    def test_second_caller_gets_the_first_ones_blanking(self):
        with mock.patch.object(blanked_text, "_blank", wraps=blanked_text._blank) as spy:
            with shared():
                first = blank_comments_and_strings(self.TEXT)
                # A different str object with the same text, as a second
                # audit reading the same file gets.
                second = blank_comments_and_strings("".join(list(self.TEXT)))
                self.assertEqual(blanked_text.cached_texts(), 1)
            self.assertEqual(blanked_text.cached_texts(), 0)
        self.assertEqual(spy.call_count, 1)
        self.assertIs(first, second)

    def test_a_changed_text_is_blanked_again(self):
        with shared():
            before = blank_comments_and_strings(self.TEXT)
            after = blank_comments_and_strings(self.TEXT + "# new\n")
        self.assertNotEqual(before, after)
        self.assertEqual(dict(after[1])[3], "# new")

    def test_nested_shared_keeps_the_outer_cache(self):
        with shared():
            blank_comments_and_strings(self.TEXT)
            with shared():
                self.assertEqual(blanked_text.cached_texts(), 1)
            self.assertEqual(blanked_text.cached_texts(), 1)
        self.assertEqual(blanked_text.cached_texts(), 0)

    def test_comments_cannot_be_changed_by_a_caller(self):
        with shared():
            _clean, comments = blank_comments_and_strings(self.TEXT)
            with self.assertRaises(TypeError):
                comments[1] = "# overwritten"  # type: ignore[index]

    def test_the_post_load_chain_shares_one_cache(self):
        import mod_state_server as mss

        seen = []

        def step(mod_state, generators, *, vanilla_files):
            seen.append(blanked_text._cache is not None)

        with mock.patch.object(mss, "_run_generator_chain_steps", side_effect=step):
            mss._run_generator_chain(None, [])
        self.assertEqual(seen, [True])
        self.assertIsNone(blanked_text._cache)


if __name__ == "__main__":
    unittest.main()
