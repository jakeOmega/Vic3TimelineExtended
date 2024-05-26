import unittest
from paradox_file_parser import ParadoxFileParser
import json


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

    def test_dummy(self):
        d1 = {"key1": ("=", "value1")}
        d2 = {"key1": ("=", "value1")}
        comparison = d1 == d2
        assert comparison


if __name__ == "__main__":
    unittest.main()
