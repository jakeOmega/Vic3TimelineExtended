"""CI sanity check for the mod's localization YAML files.

The Clausewitz loc loader is silently unforgiving: a file without the UTF-8 BOM,
or whose first line is not `l_<language>:` for the language its name ends in, is
dropped whole (every key in it renders as its raw key in-game), and a key defined
twice inside one file silently keeps only the last definition. None of that produces a log line, so it is exactly the
class of breakage CI should catch.

Checks, per `localization/**/*.yml`:
  1. the file starts with a UTF-8 BOM (EF BB BF)
  2. the bytes decode as UTF-8
  3. the name ends in `_l_<language>.yml` and the first non-blank, non-comment
     line is the matching `l_<language>:` (so `x_l_german.yml` needs `l_german:`)
  4. no localization key is defined twice within the same file

Pass a directory to check other trees too, e.g. the deploy-time language copies
`scripts/generators/gen_non_english_loc.py` stages under `build/localization/`.

Usage:
    python3 scripts/analysis/check_localization_files.py [paths...]

With no arguments it scans `localization/` under the repo root. Exits 1 and
prints one `file:line: message` per problem; exits 0 when clean.
"""

from __future__ import annotations

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BOM = b"\xef\xbb\xbf"

# `KEY:0 "value"` / `KEY: "value"` — the key is the leading token before the colon.
_KEY_RE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\s*\d*\s*"')

# The loader takes a file's language from its `_l_<language>.yml` suffix.
_LANGUAGE_SUFFIX_RE = re.compile(r"_l_([a-z_]+)\.yml$")


def iter_loc_files(roots: list[str]) -> list[str]:
    """Expand directories to their `.yml` files; pass through explicit files."""
    found: list[str] = []
    for root in roots:
        if os.path.isdir(root):
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in sorted(filenames):
                    if name.endswith(".yml"):
                        found.append(os.path.join(dirpath, name))
        elif root.endswith(".yml"):
            found.append(root)
    return sorted(set(found))


def check_file(path: str) -> list[str]:
    """Return a list of `file:line: message` problems for one loc file."""
    problems: list[str] = []
    rel = os.path.relpath(path, REPO_ROOT)

    with open(path, "rb") as fh:
        raw = fh.read()

    if not raw.startswith(BOM):
        problems.append(
            f"{rel}:1: missing UTF-8 BOM — the game drops the whole file "
            f"(run bom_normalizer.py)"
        )

    body = raw[len(BOM):] if raw.startswith(BOM) else raw
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        problems.append(f"{rel}:1: not valid UTF-8 ({exc})")
        return problems

    lines = text.splitlines()

    suffix = _LANGUAGE_SUFFIX_RE.search(os.path.basename(path))
    if suffix is None:
        problems.append(
            f"{rel}:1: name does not end in `_l_<language>.yml` — the game "
            f"reads a loc file's language from that suffix"
        )
    expected_header = f"l_{suffix.group(1) if suffix else 'english'}:"

    header_line = None
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        header_line = (index, stripped)
        break

    if header_line is None:
        problems.append(f"{rel}:1: file has no content (expected `{expected_header}`)")
    elif header_line[1] != expected_header:
        problems.append(
            f"{rel}:{header_line[0]}: first non-blank line is "
            f"{header_line[1]!r}, expected {expected_header!r}"
        )

    seen: dict[str, int] = {}
    for index, line in enumerate(lines, start=1):
        match = _KEY_RE.match(line)
        if not match:
            continue
        key = match.group(1)
        if f"{key}:" == expected_header:
            continue
        if key in seen:
            problems.append(
                f"{rel}:{index}: duplicate key '{key}' "
                f"(first defined at line {seen[key]})"
            )
        else:
            seen[key] = index

    return problems


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    roots = args or [os.path.join(REPO_ROOT, "localization")]

    files = iter_loc_files(roots)
    if not files:
        print(f"No .yml files found under: {', '.join(roots)}", file=sys.stderr)
        return 1

    problems: list[str] = []
    for path in files:
        problems.extend(check_file(path))

    for problem in problems:
        print(problem, file=sys.stderr)

    print(f"Checked {len(files)} localization file(s); {len(problems)} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
