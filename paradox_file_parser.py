import re
import codecs
import json
import copy
import logging


logger = logging.getLogger(__name__)

INDENT_SIZE = 4
# Every operator the engine accepts between a key and its value. `!=`
# (not equal), `?=` (scope exists and ...) and `==` all occur in vanilla and
# mod script; an operator missing here makes parse_object reject the key.
conditional_tokens = ["=", "<", ">", "<=", ">=", "!=", "?=", "=="]
directive_prefixes = ("INJECT:", "REPLACE:", "REPLACE_OR_CREATE:")


class ParadoxFileParser:
    def __init__(self):
        self.data = {}

    def tokenize(self, text):
        # Typed-literal forms: rgb{ R G B }, hsv{ H S V }, hsv360{ H S V },
        # hex{ ... } are color literals in vanilla. Tokenized as ONE token
        # so parse_object doesn't mis-read the body as key/value pairs.
        # @[ident] is a script-time substitution expression (occupation_values.txt).
        # Allowing optional whitespace between the keyword and `{` matches
        # `hsv360 \t{ ... }` forms seen in some flag definitions.
        # Operator class covers !=, ?= and == as well as = < > <= >= — `!` and
        # `?` belong to no other token class, so before they were listed here
        # they were silently dropped and `x != 0` tokenized as `x = 0`.
        token_pattern = (
            r'(?:rgb|hsv360|hsv|hex)\s*\{[^}]*\}'
            r'|@\[[^\]]+\]'
            r'|\{|\}|\s*[!?><=]+\s*|"[^"]*"|[\w\-\.:\|/$@]+'
        )
        text = "\n".join(self._strip_comment(line) for line in text.split("\n"))
        tokens = re.findall(token_pattern, text.strip())
        return [t.strip() for t in tokens]

    @staticmethod
    def _strip_comment(line):
        """Drop a `# ...` comment from one line, but not a `#` that sits
        inside a quoted string (`desc = "Cost: #N 5 #!"`). Fast path when no
        quote precedes the first `#`. A line whose quote is never closed
        falls back to cutting at the first `#`, which is the old split() rule.
        """
        hash_pos = line.find("#")
        if hash_pos == -1:
            return line
        if '"' not in line[:hash_pos]:
            return line[:hash_pos]
        in_string = False
        for i, ch in enumerate(line):
            if ch == '"':
                in_string = not in_string
            elif ch == "#" and not in_string:
                return line[:i]
        if in_string:
            return line[:hash_pos]
        return line

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
        """A `{ ... }` block is a dictionary if a conditional (=, >=, etc.)
        appears at the OUTER depth — not inside a nested object.

        Old behavior: any conditional anywhere inside counted, which
        misclassified `{ { x = 1 } { x = 2 } }` (a list of anonymous
        objects) as a dict and broke parse_object. Now lists of objects
        route through parse_list instead.
        """
        value_tokens = self.extract_tokens_within_braces(tokens)
        depth = 0
        for tok in value_tokens:
            if tok == "{":
                depth += 1
                continue
            if tok == "}":
                depth -= 1
                continue
            if depth == 0 and tok in conditional_tokens:
                return True
        return False

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
        """Walk top-level tokens of a list value. Bare `{ ... }` items
        recurse into parse_object so list-of-anonymous-objects shapes
        (vanilla ship_name_definitions, terrain textures, treaty articles_to_create)
        produce a list of dicts rather than raising.
        """
        result = []
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            if tok == "{":
                # Find matching close brace, then recurse on the inner block.
                depth = 1
                j = i + 1
                while j < n and depth > 0:
                    if tokens[j] == "{":
                        depth += 1
                    elif tokens[j] == "}":
                        depth -= 1
                    j += 1
                # tokens[i:j] is the brace-delimited block including both braces.
                nested, _ = self.parse_object(tokens[i:j])
                result.append(nested)
                i = j
            else:
                result.append(tok)
                i += 1
        return result

    def parse_simple_value(self, tokens):
        return tokens[0], tokens[1:]

    def parse_object(self, tokens):
        """Parse `{ key op value ... }` starting at the opening brace.

        Returns `{key: (op, value)}` when every key is unique. When any key
        repeats — `add_modifier = ...` chains, script-value `add`/`multiply`
        steps, `random_list` branches, a trigger listing several `has_law` —
        returns a list of single-key dicts, one per entry in source order, so
        each entry keeps its OWN operator (`gdp > 1000` next to two
        `has_law = ...` stays `>`) and identical duplicates survive
        (`add = 5 add = 5 add = 3` is three entries). `_normalize_data`
        later folds that list into `{key: [(op, v), ...]}`.
        """
        first_token, tokens = self.next_token(tokens)
        if first_token != "{":
            raise ValueError(
                f"Expected '{first_token}' to be '{{' when parsing object, got '{first_token}'"
            )
        entries = []
        seen = set()
        has_repeat = False
        while True:
            token, tokens = self.next_token(tokens)
            if token is None or token == "}":
                if has_repeat:
                    return [{key: (op, value)} for key, op, value in entries], tokens
                return {key: (op, value) for key, op, value in entries}, tokens
            key = token
            symbol, tokens = self.next_token(tokens)
            if symbol not in conditional_tokens:
                raise ValueError(
                    f"Expected a valid symbol after key in object, got: '{symbol}' after '{key}'"
                )
            value, tokens = self.parse_value(tokens)
            if key in seen:
                has_repeat = True
            seen.add(key)
            entries.append((key, symbol, value))

    def parse_file(self, file_path, apply_directives=True):
        # Update self.data with the parsed content
        with codecs.open(file_path, "r", "utf-8-sig") as f:
            text = f.read()
        tokens = self.tokenize("{" + text + "}")
        try:
            parsed = self.parse_object(tokens)[0]
            parsed = self._collapse_top_level_duplicates(parsed, file_path)
            if apply_directives:
                self.merge_data(parsed)
            else:
                self.data.update(parsed)
                self.data = self._normalize_data(self.data)
        except Exception as e:
            print(f"Error parsing file: {file_path}")
            raise e

    def _collapse_top_level_duplicates(self, parsed, file_path):
        """Fold the list of single-key dicts that parse_object returns for a
        file whose top level repeats a key back into a plain dict.

        Duplicates fold in file order with the rules merge_data applies when
        a later FILE repeats a key: an `INJECT:x` duplicate injects into the
        earlier copy (lossless — how the engine applies successive INJECT
        blocks, e.g. the phase-1/phase-2 blocks per company in
        common/company_types/extra_companies_vanilla_updates.txt), while a
        plain or `REPLACE:` duplicate replaces the earlier copy — last wins,
        which is what the apply_directives=False branch always did through
        sequential dict.update. Replaced keys are logged as a warning because
        a definition was discarded (the engine logs `Duplicated key X will
        not be created` for such a file and may keep the first copy instead;
        either way the file should be fixed); folded INJECT keys at debug
        level. Previously the apply_directives=True branch passed the list to
        merge_data and the resulting AttributeError dropped the whole file.
        """
        if not isinstance(parsed, list):
            return parsed
        merged = {}
        replaced = []
        injected = []
        for item in parsed:
            for raw_key, value in item.items():
                if raw_key in merged:
                    directive, _ = self._split_directive(raw_key)
                    if directive == "INJECT":
                        merged[raw_key] = self._inject_value(merged[raw_key], value)
                        if raw_key not in injected:
                            injected.append(raw_key)
                        continue
                    if raw_key not in replaced:
                        replaced.append(raw_key)
                merged[raw_key] = value
        if injected:
            logger.debug(
                "%s: repeated INJECT: key(s) folded in file order: %s",
                file_path,
                ", ".join(injected),
            )
        if replaced:
            logger.warning(
                "%s: top-level key(s) defined more than once: %s "
                "(keeping the last definition of each)",
                file_path,
                ", ".join(replaced),
            )
        return merged

    def merge_data(self, new_data):
        # Merge new data into existing self.data, with new_data taking precedence
        for raw_key, raw_value in new_data.items():
            directive, key = self._split_directive(raw_key)
            if directive in ("REPLACE", "REPLACE_OR_CREATE"):
                self.data[key] = raw_value
            elif directive == "INJECT":
                if key in self.data:
                    self.data[key] = self._inject_value(self.data[key], raw_value)
                else:
                    self.data[key] = raw_value
            else:
                self.data[key] = raw_value
        self.data = self._normalize_data(self.data)

    def _split_directive(self, key):
        for prefix in directive_prefixes:
            if key.startswith(prefix):
                return prefix[:-1], key[len(prefix) :]
        return None, key

    def _inject_value(self, base_value, injected_value):
        if isinstance(base_value, tuple) and isinstance(injected_value, tuple):
            base_operator = base_value[0]
            base_right = base_value[1]
            base_tail = base_value[2:] if len(base_value) > 2 else ()
            injected_right = injected_value[1]
            merged_right = self._inject_value(base_right, injected_right)
            return (base_operator, merged_right, *base_tail)

        if isinstance(base_value, dict) and isinstance(injected_value, dict):
            merged = copy.deepcopy(base_value)
            for raw_key, injected_child in injected_value.items():
                directive, key = self._split_directive(raw_key)
                if directive in ("REPLACE", "REPLACE_OR_CREATE"):
                    merged[key] = injected_child
                elif directive == "INJECT":
                    if key in merged:
                        merged[key] = self._inject_value(merged[key], injected_child)
                    else:
                        merged[key] = injected_child
                else:
                    if key in merged:
                        merged[key] = self._inject_value(merged[key], injected_child)
                    else:
                        merged[key] = injected_child
            return merged

        if isinstance(base_value, list) and isinstance(injected_value, list):
            merged = list(base_value)
            for item in injected_value:
                if not any(item == existing for existing in merged):
                    merged.append(item)
            return merged
        if isinstance(base_value, list) and isinstance(injected_value, dict):
            merged = list(base_value)
            for raw_key, injected_child in injected_value.items():
                directive, key = self._split_directive(raw_key)
                matched_index = None
                for index, item in enumerate(merged):
                    if isinstance(item, dict) and key in item:
                        matched_index = index
                        break
                if matched_index is None:
                    merged.append({key: injected_child})
                    continue

                existing_value = merged[matched_index][key]
                if directive in ("REPLACE", "REPLACE_OR_CREATE"):
                    merged[matched_index][key] = injected_child
                elif directive == "INJECT":
                    merged[matched_index][key] = self._inject_value(
                        existing_value, injected_child
                    )
                else:
                    merged[matched_index][key] = self._inject_value(
                        existing_value, injected_child
                    )
            return merged
        base_number = self._try_parse_number(base_value)
        injected_number = self._try_parse_number(injected_value)
        if base_number is not None and injected_number is not None:
            summed = base_number + injected_number
            return str(summed)

        return injected_value

    def _normalize_data(self, data):
        if isinstance(data, dict):
            normalized = {}
            for key, value in data.items():
                normalized[key] = self._normalize_data(value)
            return normalized
        if isinstance(data, list):
            if all(
                isinstance(item, dict) and len(item) == 1 for item in data
            ):
                merged = {}
                for item in data:
                    key = next(iter(item))
                    value = self._normalize_data(item[key])
                    if key in merged:
                        existing = merged[key]
                        if isinstance(existing, list):
                            existing.append(value)
                        else:
                            merged[key] = [existing, value]
                    else:
                        merged[key] = value
                return merged
            return [self._normalize_data(item) for item in data]
        if isinstance(data, tuple) and len(data) >= 2:
            operator = data[0]
            right_value = self._normalize_data(data[1])
            if len(data) > 2:
                return (operator, right_value, *data[2:])
            return (operator, right_value)
        return data

    def _try_parse_number(self, value):
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return float(value) if "." in value or "e" in value.lower() else int(value)
            except ValueError:
                return None
        return None

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
