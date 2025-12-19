# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 23:22:15 2023

@author: jakef
"""

import re
from os import walk

from ideology_modifications import modifications
from path_constants import base_game_path, mod_path


def parse_file(file_path):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    entries = {}
    stack = []
    key = None
    value = ""

    for line in content.split("\n"):
        if line.strip() == "":
            continue
        if (
            "{" in line and "}" in line
        ):  # Handle the case where the opening and closing braces are on the same line
            value += line + "\n"
        elif "{" in line:
            if key is None:
                key = line.split("=", 1)[0].strip()
                value = "{\n"
            else:
                value += line + "\n"
            stack.append("{")
        elif "}" in line:
            stack.pop()
            value += line + "\n"
        else:
            value += line + "\n"

        if key is not None and len(stack) == 0:
            entries[key] = value
            key = None
            value = ""

    return entries


def _is_append_only(original_entry: str, sub_entries_mods: dict) -> bool:
    """Return True if modifications only add brand-new top-level sub-entries.

    If we touch (edit/extend) an already-existing sub-entry, we must REPLACE.
    """

    # Any modification that targets an existing "<sub_key> = {" block is not append-only.
    for sub_key in sub_entries_mods.keys():
        if f"{sub_key} = {{" in original_entry:
            return False
    return True


def _replacement_reasons(original_entry: str, sub_entries_mods: dict) -> list[str]:
    """Return a list of sub_keys that already exist (thus forcing REPLACE)."""

    reasons = []
    for sub_key in sub_entries_mods.keys():
        if f"{sub_key} = {{" in original_entry:
            reasons.append(sub_key)
    return reasons


def modify_entries(entries, modifications):
    """Apply `modifications` to parsed ideology entries.

    Returns a dict mapping ideology key -> (keyword, new_entry_text, replace_reasons).
    """

    result = {}

    for key, sub_entries in modifications.items():
        if key not in entries:
            continue

        original_entry = entries[key]
        entry = original_entry

        for sub_key, lines in sub_entries.items():
            if sub_key + " = {" in entry:
                # Modify existing lines within the sub-entry or add new lines
                for line in lines:
                    line_key, line_value = line
                    line_pattern = f"\t\t{re.escape(line_key)} = .*"
                    new_line = f"\t\t{line_key} = {line_value}"
                    if re.search(line_pattern, entry):
                        entry = re.sub(line_pattern, new_line, entry)
                    else:
                        entry = entry.replace(
                            f"{sub_key} = {{", f"{sub_key} = {{\n{new_line}", 1
                        )
            else:
                # Add a new sub-entry before the first line that starts with "lawgroup_"
                new_value = "\n".join([f"\t\t{line[0]} = {line[1]}" for line in lines])
                new_sub_entry = f"\t{sub_key} = {{\n{new_value}\n\t}}"
                pattern = re.compile(r"(\n\tlawgroup_)", re.DOTALL)
                entry = pattern.sub("\n" + new_sub_entry + r"\1", entry, 1)

        replace_reasons = _replacement_reasons(original_entry, sub_entries)
        keyword = "INJECT" if len(replace_reasons) == 0 else "REPLACE"
        result[key] = (keyword, entry, replace_reasons)

    return result


def update_law_reqs(entries):
    # entries can be either {key: value} or {key: (keyword, new_entry_text, replace_reasons)}
    for key in list(entries.keys()):
        val = entries[key]

        if isinstance(val, tuple):
            if len(val) == 3:
                keyword, entry, reasons = val
            else:
                keyword, entry = val
                reasons = []
        else:
            keyword, entry, reasons = None, val, []

        entry = entry.replace(
            "has_law = law_type:law_womens_suffrage",
            "AND = { has_law = law_type:law_protected_class has_law = law_type:law_full_equality_and_protection }",
        )

        if keyword is not None:
            entries[key] = (keyword, entry, reasons)
        else:
            entries[key] = entry

    return entries


def _extract_block(entry_body: str, block_key: str) -> str | None:
    """Extract a top-level Paradox block like '\t<block_key> = { ... \t}' from an ideology body."""

    # Find the first occurrence of a top-level "\t<block_key>" and then balance braces.
    needle = f"\t{block_key} = {{"
    start = entry_body.find(needle)
    if start == -1:
        return None

    i = start
    brace_depth = 0
    started = False
    while i < len(entry_body):
        ch = entry_body[i]
        if ch == "{":
            brace_depth += 1
            started = True
        elif ch == "}":
            brace_depth -= 1
            if started and brace_depth == 0:
                # include through end-of-line after the closing brace
                end = entry_body.find("\n", i)
                if end == -1:
                    end = len(entry_body)
                else:
                    end = end + 1
                return entry_body[start:end]
        i += 1

    return None


def write_to_file(file_path, entries):
    with open(file_path, "w", encoding="utf-8-sig") as f:
        for key, value in entries.items():
            if isinstance(value, tuple):
                if len(value) == 3:
                    keyword, body, reasons = value
                else:
                    keyword, body = value
                    reasons = []

                if keyword == "REPLACE" and reasons:
                    # Paradox-style comment
                    f.write(
                        f"# Forced REPLACE due to existing section(s): {', '.join(reasons[:3])}\n"
                    )

                if keyword == "INJECT":
                    # Only output the new lawgroup_* blocks that were added.
                    # These are the sub-entries present in `modifications[key]`.
                    inject_body = "{\n"
                    for sub_key in modifications.get(key, {}).keys():
                        block = _extract_block(body, sub_key)
                        if block:
                            inject_body += block
                    inject_body += "}\n"
                    f.write(f"INJECT:{key} = {inject_body}\n")
                else:
                    f.write(f"{keyword}:{key} = {body}\n")
            else:
                # Fallback: previous behavior
                f.write(f"{key} = {value}\n")


entries = {}
filenames = next(
    walk(base_game_path + r"\game\common\ideologies"),
    (None, None, []),
)[2]
for file in filenames:
    print("Parsing: ", file)
    new_entries = parse_file(base_game_path + r"\game\common\ideologies\\" + file)
    print("Found ", len(new_entries.keys()), " new entries")
    entries.update(new_entries)


modified_entries = modify_entries(entries, modifications)
modified_entries = update_law_reqs(modified_entries)
write_to_file(
    mod_path + r"\common\ideologies\modified.txt",
    modified_entries,
)
