#!/usr/bin/env python3

from __future__ import annotations

import argparse
import difflib
from pathlib import Path


def _code_portion(line: str) -> str:
    in_string = False
    escaped = False
    result: list[str] = []

    for char in line:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            result.append(" ")
            continue

        if char == '"':
            in_string = True
            result.append(" ")
            continue

        if char == "#":
            break

        result.append(char)

    return "".join(result)


def _leading_closers(text: str) -> int:
    index = 0
    while index < len(text) and text[index] == "}":
        index += 1
    return index


def format_text(text: str) -> str:
    lines = text.splitlines()
    formatted_lines: list[str] = []
    depth = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted_lines.append("")
            continue

        code = _code_portion(stripped)
        indent_depth = max(depth - _leading_closers(code.lstrip()), 0)
        formatted_lines.append(f"{'\t' * indent_depth}{stripped}")

        open_count = code.count("{")
        close_count = code.count("}")
        depth = max(depth + open_count - close_count, 0)

    formatted = "\n".join(formatted_lines)
    if text.endswith("\n"):
        formatted += "\n"
    return formatted


def iter_target_files(paths: list[str]) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []

    for raw_path in paths:
        path = Path(raw_path)
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            ordered.append(resolved)

    return ordered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize tab indentation for brace-based Paradox script files.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Files to format in place.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report files that would change without modifying them.",
    )
    args = parser.parse_args()

    changed_files: list[Path] = []

    for path in iter_target_files(args.paths):
        original = path.read_text(encoding="utf-8")
        formatted = format_text(original)

        if formatted == original:
            continue

        changed_files.append(path)

        if args.check:
            diff = difflib.unified_diff(
                original.splitlines(),
                formatted.splitlines(),
                fromfile=str(path),
                tofile=str(path),
                lineterm="",
            )
            for line in diff:
                print(line)
            continue

        path.write_text(formatted, encoding="utf-8")
        print(path)

    if args.check and changed_files:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())