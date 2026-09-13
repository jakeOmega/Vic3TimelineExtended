"""CI sanity check for the mod's localization YAML files.

The Clausewitz loc loader is silently unforgiving: a file without the UTF-8 BOM,
or whose first line is not `l_english:`, is dropped whole (every key in it renders
as its raw key in-game), and a key defined twice inside one file silently keeps
only the last definition. None of that produces a log line, so it is exactly the
class of breakage CI should catch.

Checks, per `localization/**/*.yml`:
  1. the file starts with a UTF-8 BOM (EF BB BF)
  2. the bytes decode as UTF-8
  3. the first non-blank, non-comment line is `l_english:`
  4. no localization key is defined twice within the same file

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

    header_line = None
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        header_line = (index, stripped)
        break

    if header_line is None:
        problems.append(f"{rel}:1: file has no content (expected `l_english:`)")
    elif header_line[1] != "l_english:":
        problems.append(
            f"{rel}:{header_line[0]}: first non-blank line is "
            f"{header_line[1]!r}, expected 'l_english:'"
        )

    seen: dict[str, int] = {}
    for index, line in enumerate(lines, start=1):
        match = _KEY_RE.match(line)
        if not match:
            continue
        key = match.group(1)
        if key == "l_english":
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
