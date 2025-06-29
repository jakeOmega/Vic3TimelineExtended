import re
import codecs
import json
import copy


INDENT_SIZE = 4
conditional_tokens = ["=", "<", ">", "<=", ">="]


class ParadoxFileParser:
    def __init__(self):
        self.data = {}

    def tokenize(self, text):
        token_pattern = r'hsv\{\s*\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s*\}|\{|\}|\s*[><=]+\s*|"[^"]*"|[\w\-\.:\|/]+'
        text = "\n".join(
            [
                line.split("#")[0]
                for line in text.split("\n")
                if not line.startswith("#")
            ]
        )
        tokens = re.findall(token_pattern, text.strip())
        return [t.strip() for t in tokens]

    def calculate_depths(self, tokens):
        """
        Calculates and assigns a depth level to each token.
        Depth increments inside each '{' and decrements upon each '}'.
        """
        depths = []
        current_depth = 0

        for token in tokens:
            if token == "}":
                current_depth -= 1
            depths.append(current_depth)
            if token == "{":
                current_depth += 1

        return depths

    def extract_tokens_within_braces(self, tokens):
        extracted_tokens = []
        extraction_started = False
        depths = self.calculate_depths(tokens)
        for token, depth in zip(tokens, depths):
            if depth == 0 and token == "{":
                extraction_started = True
                continue
            if extraction_started:
                if depth == 0 and token == "}":
                    break
                extracted_tokens.append(token)

        return extracted_tokens

    def is_value_simple(self, tokens):
        return tokens[0] != "{"

    def is_value_dictionary(self, tokens):
        value_tokens = self.extract_tokens_within_braces(tokens)
        return any([t in conditional_tokens for t in value_tokens])

    def next_token(self, tokens):
        if len(tokens) == 0:
            return None, []
        else:
            return tokens[0], tokens[1:]

    def parse_value(self, tokens):
        if self.is_value_simple(tokens):
            return self.parse_simple_value(tokens)
        elif self.is_value_dictionary(tokens):
            return self.parse_object(tokens)
        else:
            list_tokens = self.extract_tokens_within_braces(tokens)
            return self.parse_list(list_tokens), tokens[len(list_tokens) + 2 :]

    def parse_list(self, tokens):
        return tokens

    def parse_simple_value(self, tokens):
        return tokens[0], tokens[1:]

    def _listify(self, obj):
        obj_list = []
        for key, value in obj.items():
            operator = value[0]
            if isinstance(value[1], list):
                for item in value[1]:
                    obj_list.append({key: (operator, item)})
            else:
                obj_list.append({key: (operator, value[1])})
        return obj_list

    def parse_object(self, tokens):
        first_token, tokens = self.next_token(tokens)
        if first_token != "{":
            raise ValueError(
                f"Expected '{first_token}' to be '{{' when parsing object, got '{first_token}'"
            )
        obj = {}
        list_flag = False
        while True:
            token, tokens = self.next_token(tokens)
            if token is None or token == "}":
                if list_flag:
                    obj = self._listify(obj)
                return obj, tokens
            else:
                key = token
                symbol, tokens = self.next_token(tokens)
                if (
                    symbol not in conditional_tokens
                ):  # Extend this list to support more symbols
                    raise ValueError(
                        f"Expected a valid symbol after key in object, got: '{symbol}' after '{key}'"
                    )
                value, tokens = self.parse_value(tokens)
                if key in obj.keys() and obj[key] != (symbol, value):
                    if not list_flag:
                        for all_key in obj.keys():
                            obj[all_key] = (symbol, [obj[all_key][1]])
                        list_flag = True
                    obj[key][1].append(value)
                else:
                    if list_flag:
                        obj[key] = (symbol, [value])
                    else:
                        obj[key] = (symbol, value)

    def parse_file(self, file_path):
        # Update self.data with the parsed content
        with codecs.open(file_path, "r", "utf-8-sig") as f:
            text = f.read()
        tokens = self.tokenize("{" + text + "}")
        try:
            self.merge_data(self.parse_object(tokens)[0])
        except Exception as e:
            print(f"Error parsing file: {file_path}")
            raise e

    def merge_data(self, new_data):
        # Merge new data into existing self.data, with new_data taking precedence
        self.data.update(new_data)

    def detect_modifications(self, base_parser):
        return self._compare_dicts(self.data, base_parser.data)

    def _compare_dicts(self, mod_dict, base_dict):
        changes = {}
        for key, mod_value in mod_dict.items():
            if key not in base_dict:
                changes[key] = {"change_type": "added", "change_value": mod_value}
            elif mod_value != base_dict[key]:
                if isinstance(mod_value, tuple) and isinstance(base_dict[key], tuple):
                    if isinstance(mod_value[1], dict) and isinstance(
                        base_dict[key][1], dict
                    ):
                        changes_in_nested_dict = self._compare_dicts(
                            mod_value[1], base_dict[key][1]
                        )
                        if changes_in_nested_dict:
                            changes[key] = {
                                "change_type": "modified",
                                "change_value": (mod_value[0], changes_in_nested_dict),
                            }
                    elif isinstance(mod_value[1], list) and isinstance(
                        base_dict[key][1], list
                    ):
                        changes_in_list = self._compare_lists(
                            mod_value[1], base_dict[key][1]
                        )
                        if changes_in_list:
                            changes[key] = {
                                "change_type": "modified",
                                "change_value": (mod_value[0], changes_in_list),
                            }
                    else:
                        changes[key] = {
                            "change_type": "modified",
                            "change_value": mod_value,
                        }
                else:
                    changes[key] = {
                        "change_type": "modified",
                        "change_value": mod_value,
                    }

        for key in base_dict:
            if key not in mod_dict:
                changes[key] = {
                    "change_type": "removed",
                    "change_value": base_dict[key],
                }

        return changes

    def _compare_lists(self, mod_list, base_list):
        list_changes = []
        added_items = [
            item
            for item in mod_list
            if not any(item == base_item for base_item in base_list)
        ]
        removed_items = [
            item
            for item in base_list
            if not any(item == mod_item for mod_item in mod_list)
        ]

        for item in added_items:
            list_changes.append({"change_type": "added", "change_value:": item})

        for item in removed_items:
            list_changes.append({"change_type": "removed", "change_value:": item})

        return list_changes if list_changes else None

    def save_changes_to_json(self, base_parser, file_path):
        changes = self.detect_modifications(base_parser)
        with open(file_path, "w") as json_file:
            json.dump(changes, json_file, indent=4)

    def set_data_from_changes_json(self, base_parser, changes_file_path):
        with open(changes_file_path, "r") as json_file:
            changes = json.load(json_file)
        data = copy.deepcopy(base_parser.data)
        self.data = self._apply_changes(data, changes)

    def _apply_changes(self, data, changes):
        changed_data = copy.deepcopy(data)
        for key, value in changes.items():
            change_type, change_value = value["change_type"], value["change_value"]
            if change_type == "added":
                operator, right_value = change_value[0], change_value[1]
                changed_data[key] = (operator, self._format_from_json(right_value))
            elif change_type == "removed" and key in changed_data:
                del changed_data[key]
            elif change_type == "modified":
                operator, right_value = change_value[0], change_value[1]
                if len(changed_data[key]) > 2:
                    original_value = changed_data[key][1:]
                else:
                    _, original_value = changed_data[key]
                if isinstance(right_value, dict) and isinstance(original_value, dict):
                    changed_data[key] = (
                        operator,
                        self._apply_changes(original_value, right_value),
                    )
                elif isinstance(right_value, list) and isinstance(original_value, list):
                    changed_data[key] = (
                        operator,
                        self._merge_lists(original_value, right_value),
                    )
                else:
                    changed_data[key] = (operator, self._format_from_json(right_value))
            else:
                raise ValueError(f"Invalid change type: {change_type}")

        return changed_data

    def _is_conditional_tuple(self, value):
        """json doesn't support tuples, so this checks for the tuples format as well"""
        if len(value) == 2 and value[0] in conditional_tokens:
            return True
        else:
            return False

    def _format_from_json(self, json_value):
        if isinstance(json_value, dict):
            result = {}
            for key, value in json_value.items():
                if self._is_conditional_tuple(value):
                    operator, right_value = value[0], value[1]
                    result[key] = (operator, self._format_from_json(right_value))
                elif isinstance(value, list):
                    result[key] = [self._format_from_json(item) for item in value]
                else:
                    result[key] = self.format_data_to_string(value)
            return result
        elif self._is_conditional_tuple(json_value):
            return (json_value[0], self._format_from_json(json_value[1]))
        elif isinstance(json_value, list):
            return [self._format_from_json(item) for item in json_value]
        else:
            return json_value

    def _merge_lists(self, base_list, changes):
        for change_type, item in changes:
            if change_type == "added":
                base_list.append(item)
            elif change_type == "removed" and item in base_list:
                base_list.remove(item)
        return base_list

    def __repr__(self):
        return self.format_data_to_string(self.data)

    def format_data_to_string(self, data, indent=0):
        # Convert self.data into the game's file format and write to file_path
        line_prefix = " " * indent
        if isinstance(data, list):
            return "\n".join(
                [self.format_data_to_string(item, indent) for item in data]
            )
        elif isinstance(data, dict):
            lines = []
            for key, value in data.items():
                done = False
                while not done:
                    if isinstance(value, tuple):
                        symbol, actual_value = value[0], value[1]
                        value = value[2:]
                        if isinstance(actual_value, dict) or isinstance(
                            actual_value, list
                        ):
                            lines.append(f"{line_prefix}{key} {symbol} {{")
                            lines.append(
                                self.format_data_to_string(
                                    actual_value, indent + INDENT_SIZE
                                )
                            )
                            lines.append(line_prefix + "}")
                        else:
                            lines.append(f"{line_prefix}{key} {symbol} {actual_value}")
                        if len(value) == 0:
                            done = True
                    else:
                        if isinstance(value, list):
                            for item in value:
                                lines.append(
                                    f"{line_prefix}{key} = "
                                    + self.format_data_to_string(
                                        item, indent + INDENT_SIZE
                                    )
                                )
                        else:
                            lines.append(f"{line_prefix}{key} = {value}")
                        done = True

            return "\n".join(lines)
        else:
            return line_prefix + str(data)

    def write_file(self, file_path, base_parser):
        modified_data = self._get_modified_data(self.data, base_parser)
        formatted_data = self.format_data_to_string(modified_data)
        with open(file_path, "w") as file:
            file.write(formatted_data)

    def _get_modified_data(self, mod_data, base_parser):
        changes = self.detect_modifications(base_parser)
        modified_data = {}
        for key in changes:
            modified_data[key] = mod_data[key]
        return modified_data


# Example usage
# parser = ParadoxFileParser()
# parser.parse_file(
#    "F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\production_methods\extra_pms.txt"
# )

# print(parser.format_dict_to_string(parser.data))
