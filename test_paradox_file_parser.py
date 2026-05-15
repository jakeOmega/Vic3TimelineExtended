import io
import json
import os
import sys
import tempfile
import unittest

from mod_state import ModState
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


if __name__ == "__main__":
    unittest.main()
