import io
import os
import sys
import tempfile
import unittest

from mod_state import ModState, parse_loc_line, split_loc_line
from paradox_file_parser import ParadoxFileParser


class ParadoxFileParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = ParadoxFileParser()

    def test_tokenize(self):
        text = """
        # This is a comment
        key = value
        { nested_key = nested_value }
        """
        tokens = self.parser.tokenize(text)
        expected_tokens = [
            "key",
            "=",
            "value",
            "{",
            "nested_key",
            "=",
            "nested_value",
            "}",
        ]
        self.assertEqual(tokens, expected_tokens)

    def test_calculate_depths(self):
        tokens = [
            "{",
            "key",
            "=",
            "value",
            "{",
            "nested_key",
            "=",
            "nested_value",
            "}",
            "}",
        ]
        depths = self.parser.calculate_depths(tokens)
        expected_depths = [0, 1, 1, 1, 1, 2, 2, 2, 1, 0]
        self.assertEqual(depths, expected_depths)

    def test_extract_tokens_within_braces(self):
        tokens = [
            "{",
            "key",
            "=",
            "value",
            "{",
            "nested_key",
            "=",
            "nested_value",
            "}",
            "}",
        ]
        extracted_tokens = self.parser.extract_tokens_within_braces(tokens)
        expected_tokens = [
            "key",
            "=",
            "value",
            "{",
            "nested_key",
            "=",
            "nested_value",
            "}",
        ]
        self.assertEqual(extracted_tokens, expected_tokens)

    def test_is_value_simple(self):
        tokens = ["key", "=", "value"]
        is_simple = self.parser.is_value_simple(tokens)
        self.assertTrue(is_simple)

    def test_is_value_dictionary(self):
        tokens = ["key", "=", "{", "nested_key", "=", "nested_value", "}"]
        is_dictionary = self.parser.is_value_dictionary(tokens)
        self.assertTrue(is_dictionary)

    def test_parse_value_dictionary(self):
        tokens = ["{", "nested_key", "=", "nested_value", "}"]
        value, remaining_tokens = self.parser.parse_value(tokens)
        expected_value = {"nested_key": ("=", "nested_value")}
        expected_remaining_tokens = []
        self.assertEqual(value, expected_value)
        self.assertEqual(remaining_tokens, expected_remaining_tokens)

    def test_parse_value_nested_dictionary(self):
        tokens = ["{", "nested_key", "=", "{", "key", "=", "value", "}", "}"]
        value, remaining_tokens = self.parser.parse_value(tokens)
        expected_value = {"nested_key": ("=", {"key": ("=", "value")})}
        expected_remaining_tokens = []
        self.assertEqual(value, expected_value)
        self.assertEqual(remaining_tokens, expected_remaining_tokens)

    def test_format_data_to_string_with_list(self):
        data = ["value1", "value2", "value3"]
        expected_output = "value1\nvalue2\nvalue3"
        output = self.parser.format_data_to_string(data)
        self.assertEqual(output, expected_output)

    def test_format_data_to_string_with_dict(self):
        data = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }
        expected_output = "key1 = value1\nkey2 = value2\nkey3 = value3"
        output = self.parser.format_data_to_string(data)
        self.assertEqual(output, expected_output)

    def test_format_data_to_string_with_nested_dict(self):
        data = {
            "key1": (
                "=",
                {
                    "nested_key1": ("=", "nested_value1"),
                    "nested_key2": (">", "nested_value2"),
                },
            )
        }
        expected_output = "key1 = {\n    nested_key1 = nested_value1\n    nested_key2 > nested_value2\n}"
        output = self.parser.format_data_to_string(data)
        self.assertEqual(output, expected_output)

    def test_format_data_to_string_complex(self):
        data = {
            "if": (
                "=",
                {
                    "limit": (
                        "=",
                        {
                            "scope:interest_group": (
                                "=",
                                [
                                    {
                                        "is_interest_group_type": (
                                            "=",
                                            "ig_petty_bourgeoisie",
                                        )
                                    },
                                    {
                                        "is_interest_group_type": (
                                            "=",
                                            "ig_armed_forces",
                                        )
                                    },
                                ],
                            )
                        },
                    ),
                    "add": ("=", "50"),
                },
            )
        }
        expected_output = "if = {\n    limit = {\n        scope:interest_group = {\n            is_interest_group_type = ig_petty_bourgeoisie\n            is_interest_group_type = ig_armed_forces\n        }\n    }\n    add = 50\n}"
        output = self.parser.format_data_to_string(data)
        self.assertEqual(output, expected_output)

    # -----------------------------------------------------------------
    # Vanilla-syntax constructs the parser previously rejected, leading to
    # whole files being silently skipped on load. Added when fixing the
    # post-restart parse-warnings sweep (May 2026).
    # -----------------------------------------------------------------
    def test_tokenize_rgb_color_literal(self):
        """`rgb{ 62 77 100 }` in cultures/00_cultures.txt is one token."""
        text = "color = rgb{ 62 77 100 }"
        tokens = self.parser.tokenize(text)
        self.assertEqual(tokens, ["color", "=", "rgb{ 62 77 100 }"])

    def test_tokenize_hsv_color_literal_still_works(self):
        """Regression: existing hsv/hsv360 support must not break."""
        text = "color = hsv360{ 20 80 80 }"
        tokens = self.parser.tokenize(text)
        self.assertEqual(tokens, ["color", "=", "hsv360{ 20 80 80 }"])

    def test_tokenize_at_substitution_expression(self):
        """`@[hazardous_terrain_factor]` in script_values is one token.
        Without this the parser drops the brackets and mis-tokenizes the
        expression as two separate tokens, breaking object-key alignment.
        """
        text = "multiply = @[hazardous_terrain_factor]"
        tokens = self.parser.tokenize(text)
        self.assertEqual(tokens, ["multiply", "=", "@[hazardous_terrain_factor]"])

    def test_tokenize_top_level_at_constant_unchanged(self):
        """Regression: `@max_battles = 4` (no brackets) keeps working."""
        text = "@max_battles = 4"
        tokens = self.parser.tokenize(text)
        self.assertEqual(tokens, ["@max_battles", "=", "4"])

    def test_is_value_dictionary_ignores_nested_conditionals(self):
        """A value is a *dict* only if a conditional appears at depth 0
        relative to the outer braces. A list of anonymous objects
        (`{ { x = 1 } { x = 2 } }`) has conditionals only at depth 1+
        and must classify as a list, not a dict."""
        tokens_dict = ["{", "key", "=", "value", "}"]
        tokens_list_of_anon = ["{", "{", "x", "=", "1", "}", "{", "x", "=", "2", "}", "}"]
        self.assertTrue(self.parser.is_value_dictionary(tokens_dict))
        self.assertFalse(self.parser.is_value_dictionary(tokens_list_of_anon))

    def test_parse_value_anonymous_objects_in_list(self):
        """`{ { type = custom_text } { type = name_list } }` -> list of two dicts.
        This is the vanilla ship_name_definitions / decisions / terrain shape
        that previously made the parser raise."""
        tokens = ["{", "{", "type", "=", "custom_text", "}",
                       "{", "type", "=", "name_list", "}", "}"]
        value, remaining = self.parser.parse_value(tokens)
        self.assertEqual(value, [
            {"type": ("=", "custom_text")},
            {"type": ("=", "name_list")},
        ])
        self.assertEqual(remaining, [])

    def test_parse_value_simple_list_still_works(self):
        """Regression: a list of scalar tokens stays a list of strings."""
        tokens = ["{", "general", "}"]
        value, remaining = self.parser.parse_value(tokens)
        self.assertEqual(value, ["general"])

    def test_parse_value_mixed_anonymous_object_and_dict_value(self):
        """Real vanilla shape: `properties = { { type = X name_list = { Y Z } } }`
        — nested object containing both a scalar key and a list-valued key."""
        tokens = ["{",
                  "{",
                    "type", "=", "name_list",
                    "name_list", "=", "{", "Y", "Z", "}",
                  "}",
                  "}"]
        value, remaining = self.parser.parse_value(tokens)
        self.assertEqual(value, [
            {"type": ("=", "name_list"), "name_list": ("=", ["Y", "Z"])},
        ])

    def test_missing_mod_override_directory_is_silent(self):
        """Registering an entity type in mod_paths without an on-disk override
        is a legitimate pattern — it reserves the slot so future mod content
        can override vanilla. As long as the base game directory exists,
        ModState must NOT print a warning for the absent mod-side dir."""
        with tempfile.TemporaryDirectory() as tmp:
            base_root = os.path.join(tmp, "base")
            mod_root = os.path.join(tmp, "mod")
            os.makedirs(os.path.join(base_root, "cultures"))
            # Write a minimal valid culture so the parser has something to read.
            with open(os.path.join(base_root, "cultures", "00_a.txt"), "w") as f:
                f.write("test_culture = {\n\tcolor = rgb{ 1 2 3 }\n}\n")
            # mod dir for the same entity type intentionally does NOT exist.
            base_dirs = {"Cultures": os.path.join(base_root, "cultures")}
            mod_dirs  = {"Cultures": os.path.join(mod_root,  "cultures")}

            buf = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = buf
            try:
                ms = ModState(base_dirs, mod_dirs)
            finally:
                sys.stdout = old_stdout
            output = buf.getvalue()
            self.assertNotIn(
                "Mod directory not found", output,
                f"Spurious warning printed: {output!r}",
            )
            self.assertIn("test_culture", ms.mod_parsers["Cultures"].data)

    def test_dummy(self):
        d1 = {"key1": ("=", "value1")}
        d2 = {"key1": ("=", "value1")}
        comparison = d1 == d2
        assert comparison


def _collect_operators(node, found=None):
    """Every operator token in a parsed tree (tuples are (op, value))."""
    if found is None:
        found = set()
    if isinstance(node, tuple) and len(node) >= 2:
        found.add(node[0])
        _collect_operators(node[1], found)
    elif isinstance(node, dict):
        for value in node.values():
            _collect_operators(value, found)
    elif isinstance(node, list):
        for item in node:
            _collect_operators(item, found)
    return found


class ParserSemanticsTests(unittest.TestCase):
    """Issue #241: comparison operators, repeated keys, duplicate top-level
    keys, `#` inside strings, and escape-aware localization values."""

    REPO = os.path.dirname(os.path.abspath(__file__))

    def setUp(self):
        self.parser = ParadoxFileParser()

    def _parse_block(self, text):
        return self.parser.parse_object(self.parser.tokenize("{" + text + "}"))[0]

    def _normalized_block(self, text):
        return self.parser._normalize_data(self._parse_block(text))

    # -- operators ----------------------------------------------------------
    def test_tokenize_keeps_not_equal_exists_and_double_equal_operators(self):
        """`!` and `?` used to belong to no token class and were dropped, so
        `x != 0` tokenized as `x = 0`."""
        tokens = self.parser.tokenize("x != 0\npower_bloc ?= { a = b }\ny == z\nw<=1")
        self.assertEqual(tokens, [
            "x", "!=", "0",
            "power_bloc", "?=", "{", "a", "=", "b", "}",
            "y", "==", "z",
            "w", "<=", "1",
        ])

    def test_parse_object_preserves_comparison_operators(self):
        obj = self._parse_block("x != 0 power_bloc ?= { a = b } y == z gdp >= 5")
        self.assertEqual(obj, {
            "x": ("!=", "0"),
            "power_bloc": ("?=", {"a": ("=", "b")}),
            "y": ("==", "z"),
            "gdp": (">=", "5"),
        })

    def test_real_mod_files_keep_comparison_operators(self):
        """The mod sites named in #241: `!= 0` in script_values/modified.txt,
        `!= this` in treaty_articles, `power_bloc ?= {` in extra_laws."""
        cases = {
            "common/script_values/modified.txt": "!=",
            "common/treaty_articles/extra_treaty_articles.txt": "!=",
            "common/laws/extra_laws.txt": "?=",
        }
        for rel, op in cases.items():
            path = os.path.join(self.REPO, rel)
            if not os.path.isfile(path):
                self.skipTest(f"{rel} not present")
            parser = ParadoxFileParser()
            parser.parse_file(path, apply_directives=False)
            self.assertIn(op, _collect_operators(parser.data), rel)

    # -- repeated keys --------------------------------------------------------
    def test_repeated_keys_keep_each_siblings_operator(self):
        """List conversion used to rewrite every earlier sibling's operator
        with the current key's: `gdp > 1000` became `gdp = 1000`."""
        obj = self._parse_block("gdp > 1000 has_law = law_type:a has_law = law_type:b")
        self.assertEqual(obj, [
            {"gdp": (">", "1000")},
            {"has_law": ("=", "law_type:a")},
            {"has_law": ("=", "law_type:b")},
        ])
        self.assertEqual(self.parser._normalize_data(obj), {
            "gdp": (">", "1000"),
            "has_law": [("=", "law_type:a"), ("=", "law_type:b")],
        })

    def test_repeated_key_with_mixed_operators_keeps_each_entry_operator(self):
        self.assertEqual(
            self._normalized_block("x > 1 x < 5 x != 3"),
            {"x": [(">", "1"), ("<", "5"), ("!=", "3")]},
        )

    def test_identical_duplicates_are_appended_not_collapsed(self):
        """`add = 5 add = 5 add = 3` is three script-value steps, not two."""
        obj = self._parse_block("add = 5 add = 5 add = 3")
        self.assertEqual(obj, [
            {"add": ("=", "5")}, {"add": ("=", "5")}, {"add": ("=", "3")},
        ])
        self.assertEqual(
            self.parser._normalize_data(obj),
            {"add": [("=", "5"), ("=", "5"), ("=", "3")]},
        )

    def test_identical_duplicate_blocks_and_late_duplicates_are_kept(self):
        self.assertEqual(
            self._normalized_block("add_modifier = { name = a } add_modifier = { name = a }"),
            {"add_modifier": [("=", {"name": ("=", "a")}), ("=", {"name": ("=", "a")})]},
        )
        # A duplicate that only appears after another key already repeated.
        self.assertEqual(
            self._normalized_block("a = 1 a = 2 b = 3 b = 3"),
            {"a": [("=", "1"), ("=", "2")], "b": [("=", "3"), ("=", "3")]},
        )

    def test_unique_keys_still_parse_to_a_dict(self):
        self.assertEqual(self._parse_block("a = 1 b > 2"), {"a": ("=", "1"), "b": (">", "2")})

    # -- comments -------------------------------------------------------------
    def test_tokenize_hash_inside_string_is_not_a_comment(self):
        tokens = self.parser.tokenize('desc = "Cost: #N 5 #!" # a real comment\nnext = 1')
        self.assertEqual(tokens, ["desc", "=", '"Cost: #N 5 #!"', "next", "=", "1"])

    def test_tokenize_unterminated_quote_still_cuts_at_hash(self):
        """Fallback for a line whose quote never closes: the old split() rule."""
        self.assertEqual(self.parser._strip_comment('x = "oops # not'), 'x = "oops ')
        self.assertEqual(self.parser._strip_comment("x = 1 # c"), "x = 1 ")
        self.assertEqual(self.parser._strip_comment("# whole line"), "")

    # -- files ----------------------------------------------------------------
    def _write(self, tmp, name, text):
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_parse_file_duplicate_top_level_key_last_wins_and_warns(self):
        """parse_file(apply_directives=True) used to hand the list to
        merge_data and drop the whole file with AttributeError."""
        text = "a = { x = 1 }\nb = { y = 1 }\na = { x = 2 }\n"
        for apply_directives in (True, False):
            with self.subTest(apply_directives=apply_directives):
                with tempfile.TemporaryDirectory() as tmp:
                    path = self._write(tmp, "dup.txt", text)
                    parser = ParadoxFileParser()
                    with self.assertLogs("paradox_file_parser", level="WARNING") as logs:
                        parser.parse_file(path, apply_directives=apply_directives)
                    self.assertEqual(parser.data, {
                        "a": ("=", {"x": ("=", "2")}),
                        "b": ("=", {"y": ("=", "1")}),
                    })
                    self.assertEqual(len(logs.output), 1)
                    self.assertIn("dup.txt", logs.output[0])
                    self.assertIn("more than once: a (", logs.output[0])

    def test_parse_file_without_duplicates_does_not_warn(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "ok.txt", "a = { x = 1 }\nb = { y = 1 }\n")
            with self.assertNoLogs("paradox_file_parser", level="WARNING"):
                ParadoxFileParser().parse_file(path)

    def test_parse_file_repeated_inject_blocks_fold_in_order(self):
        """extra_companies_vanilla_updates.txt injects each company twice
        (phase 1 / phase 2). Both blocks must survive, as if in two files."""
        mod_text = (
            "INJECT:c = { building_types = { a } }\n"
            "INJECT:c = { building_types = { b } bonus = { x = 1 } }\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            mod_path = self._write(tmp, "mod.txt", mod_text)
            base_path = self._write(tmp, "base.txt", "c = { building_types = { v } }\n")
            # Mod path (ModState.parse_mod_file): directives kept, value folded.
            mod = ParadoxFileParser()
            with self.assertNoLogs("paradox_file_parser", level="WARNING"):
                mod.parse_file(mod_path, apply_directives=False)
            self.assertEqual(mod.data, {"INJECT:c": ("=", {
                "building_types": ("=", ["a", "b"]),
                "bonus": ("=", {"x": ("=", "1")}),
            })})
            # Directive path: folded block injects into the earlier definition.
            full = ParadoxFileParser()
            full.parse_file(base_path)
            full.parse_file(mod_path)
            self.assertEqual(full.data, {"c": ("=", {
                "building_types": ("=", ["v", "a", "b"]),
                "bonus": ("=", {"x": ("=", "1")}),
            })})

    def test_merge_data_applies_directives_from_a_mod_file(self):
        """ModState flow: vanilla via parse_file(), mod via parse_mod_file
        (apply_directives=False) then merge_data() with INJECT:/REPLACE:."""
        vanilla = "law_a = { x = 1 tags = { p } }\nlaw_b = { y = 1 }\n"
        mod = (
            "INJECT:law_a = { z = 3 tags = { q } }\n"
            "REPLACE:law_b = { y = 2 }\n"
            "law_c = { w > 1 w < 9 }\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            parser = ParadoxFileParser()
            parser.parse_file(self._write(tmp, "vanilla.txt", vanilla))
            mod_parser = ParadoxFileParser()
            mod_parser.parse_file(self._write(tmp, "mod.txt", mod), apply_directives=False)
            parser.merge_data(mod_parser.data)
        self.assertEqual(parser.data, {
            "law_a": ("=", {"x": ("=", "1"), "tags": ("=", ["p", "q"]), "z": ("=", "3")}),
            "law_b": ("=", {"y": ("=", "2")}),
            "law_c": ("=", {"w": [(">", "1"), ("<", "9")]}),
        })

    # -- localization ---------------------------------------------------------
    def test_parse_loc_line_reads_escaped_quotes_whole(self):
        """The old rule cut at the second `"`, so a value with `\"` read back
        as a lone backslash (augmentation_events.* in te_events_l_english.yml)."""
        line = r' augmentation_events.4.d:0 "Leaders say humanity is \"playing God\" and demand limits."'
        self.assertEqual(
            parse_loc_line(line),
            ("augmentation_events.4.d", r'Leaders say humanity is \"playing God\" and demand limits.'),
        )
        self.assertEqual(parse_loc_line(r' k:1 "\"a,\" b said.\n\n\"c\"" # "not this"'),
                         ("k", r'\"a,\" b said.\n\n\"c\"'))

    def test_parse_loc_line_plain_and_versioned_keys(self):
        self.assertEqual(parse_loc_line(' key:0 "value"  # trailing'), ("key", "value"))
        self.assertEqual(parse_loc_line('key: "value"'), ("key", "value"))
        self.assertEqual(parse_loc_line(' key:0 "  padded  "'), ("key", "padded"))
        self.assertEqual(parse_loc_line(' key:0 ""'), ("key", ""))

    def test_parse_loc_line_skips_header_comments_and_unquoted_lines(self):
        for line in (
            "l_english:",
            "﻿l_english:",
            " # section: notes",
            "# plain: comment",
            "",
            "   ",
            " key_without_value:0",
            " key_without_value:0 bare",
            ' two words: "x"',
            r' unterminated:0 "never closes \"',
        ):
            self.assertIsNone(parse_loc_line(line), repr(line))

    def test_split_loc_line_returns_raw_value_and_trailing_comment(self):
        """concept_reference_audit reads `# REVIEWED` suppressions from the
        text after the closing quote; an escaped quote must not end it early."""
        line = r' k:0 "He said \"go\"" # REVIEWED 2026-05-09: rationale' + "\n"
        self.assertEqual(
            split_loc_line(line),
            ("k", r'He said \"go\"', " # REVIEWED 2026-05-09: rationale"),
        )
        self.assertEqual(split_loc_line(' k:0 " padded "'), ("k", " padded ", ""))
        self.assertIsNone(split_loc_line("l_english:"))

    def test_add_localization_reads_subdirectories_but_not_replace(self):
        # Vanilla keeps state names in english/map/, IG names in
        # english/interest_groups/, ... — the engine reads those, so ModState
        # must too. `replace/` is the override layer callers load last.
        with tempfile.TemporaryDirectory() as tmp:
            files = {
                "a_l_english.yml": ' top:0 "Top"\n shared:0 "from a"\n',
                "map/states_l_english.yml": ' STATE_X:0 "State X"\n',
                "map/deeper/more_l_english.yml": ' deep:0 "Deep"\n',
                "z_l_english.yml": ' shared:0 "from z"\n',
                "replace/r_l_english.yml": ' top:0 "Replaced"\n',
                "map/notes.txt": ' not_loc:0 "ignored"\n',
            }
            for rel, body in files.items():
                path = os.path.join(tmp, *rel.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write("l_english:\n" + body)
            ms = ModState({}, {})
            ms.add_localization(tmp)
            self.assertEqual(ms.localization, {
                "top": "Top", "shared": "from z", "STATE_X": "State X", "deep": "Deep",
            })
            ms.add_localization(os.path.join(tmp, "replace"))
            self.assertEqual(ms.localization["top"], "Replaced")

    def test_add_localization_end_to_end(self):
        text = (
            "﻿l_english:\n"
            " # SECTION: one\n"
            ' plain:0 "Hello"\n'
            r' quoted:0 "She said \"go.\""' "\n"
            "# comment line\n"
            ' spaced: "  trimmed "\n"'
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "x_l_english.yml"), "w", encoding="utf-8") as f:
                f.write(text)
            ms = ModState({}, {})
            ms.add_localization(tmp)
        self.assertEqual(ms.localization, {
            "plain": "Hello",
            "quoted": r'She said \"go.\"',
            "spaced": "trimmed",
        })


if __name__ == "__main__":
    unittest.main()
