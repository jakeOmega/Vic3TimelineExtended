r"""CI sanity check for the mod's localization YAML files.

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
  5. no bare `"` inside a value or in a trailing comment. The game reads a
     value to the line's last quote, so it shows one as a quote mark (vanilla
     English has ~1,800), but `mod_state.split_loc_line`, which every loc tool
     here uses, stops at it: the translation harness, the audits and the
     deploy-time language build all see the value cut short, and the build
     splices the English tail back in after the translated half. Write a
     literal quote as `\"`.
  6. every `\"` in a value is paired, or the line shows a dangling quote mark
  7. every value closes on its own line, and every other line is blank, a
     comment or the header. A value written with a raw newline (a script's
     "\n" where the file needs the two characters `\n`) leaves
     `key:0 "first part` on one line and the rest on the next: the game reads
     neither as the value, and organize_loc keeps the first line as the whole
     value and drops the rest, after which no other check sees it.
  8. a version digit is followed by a space before the quote (`key:0 "`).
     `key:0"value"` is a typo neither vanilla nor the mod writes (an editor
     that drops a trailing space produces it). `key:"value"`, with no digit,
     is the mod's own older form and renders in game, so it passes.
  9. every `$key$` splice inside a single-quoted argument of a loc data
     function (`[Concept('concept_pop','$concept_pops$')]`,
     `ConcatIfNeitherEmpty('$X$', …)`, `GetRawTextTooltipTag('$X$')`) carries
     the `q` format flag: `$concept_pops|q$`, or `q` after any flags it already
     has (`$VALUE|%0q$`). From 1.15 the game logs "missing required
     quote-escaping" for every one without it (pdx_data_localize.cpp), and
     vanilla 1.15 escapes all ~9,950 of its own. A `'` counts as a delimiter
     only inside `[...]`, so a prose apostrophe never pairs with one.

 10. no key a `replace/` file overrides is also defined in an ordinary loc file
     of the same language. The `replace/` copy wins, so the other one is dead
     text that a later edit can change to no effect; organize_loc never reads
     `replace/` for keys, so it can't merge the two. 1.15 left one such pair
     (`goods_output_fertilizer_mult`, #1406), after the migration had cleaned
     up `goods_output_fine_art_mult` by hand.

Check 9 also runs over the translation memories (`i18n/<language>/tm/**/*.json`,
every field of every record), since the deploy swaps their text in: an
unescaped translation would bring the error back in that language's game.

Pass a directory to check other trees too, e.g. the deploy-time language copies
`scripts/generators/gen_non_english_loc.py` stages under `build/localization/`.

Usage:
    python3 scripts/analysis/check_localization_files.py [paths...]

With no arguments it scans `localization/` and `i18n/` under the repo root.
Exits 1 and prints one `file:line: message` per problem; exits 0 when clean.
"""

from __future__ import annotations

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from mod_state import split_loc_line  # noqa: E402

BOM = b"\xef\xbb\xbf"

# `KEY:0 "value"` / `KEY: "value"` — the key is the leading token before the colon.
_KEY_RE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\s*\d*\s*"')

# `KEY:0"value"`: a version digit glued to the quote (check 8).
_VERSION_NO_SPACE_RE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d+"')

# The loader takes a file's language from its `_l_<language>.yml` suffix.
_LANGUAGE_SUFFIX_RE = re.compile(r"_l_([a-z_]+)\.yml$")

# An escaped quote whose backslash is not itself escaped.
_ESCAPED_QUOTE_RE = re.compile(r'(?<!\\)(?:\\\\)*\\"')

# A `$key$` / `$key|flags$` splice (check 9).
_SPLICE_RE = re.compile(r"\$([^$\s|]+)(?:\|([^$\s]*))?\$")


def quoted_arg_splices(value: str) -> list[tuple[int, int, str, str]]:
    """(start, end, key, flags) of every splice inside a single-quoted
    argument of a `[...]` data expression in one loc value.

    A `'` is a string delimiter only while a `[` is open; outside brackets it
    is an apostrophe. Inside a quoted argument brackets are text, so
    `'[concept_x]'` neither opens nor closes an expression. An argument left
    unclosed at the end of the value is ignored."""
    out: list[tuple[int, int, str, str]] = []
    depth = 0
    start = -1
    for i, ch in enumerate(value):
        if start >= 0:
            if ch == "'":
                for m in _SPLICE_RE.finditer(value, start, i):
                    out.append((m.start(), m.end(), m.group(1), m.group(2) or ""))
                start = -1
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        elif ch == "'" and depth:
            start = i + 1
    return out


def unescaped_quoted_splices(value: str) -> list[str]:
    """The quoted-argument splices of one loc value that lack the `q` flag."""
    return [
        value[start:end]
        for start, end, _key, flags in quoted_arg_splices(value)
        if "q" not in flags
    ]


def escape_quoted_splices(value: str) -> tuple[str, int]:
    """`value` with `q` added to every quoted-argument splice that lacks it
    (`$x$` -> `$x|q$`, `$x|v$` -> `$x|vq$`, as vanilla 1.15 writes them),
    and how many it changed."""
    parts: list[str] = []
    last = changed = 0
    for start, end, key, flags in quoted_arg_splices(value):
        if "q" in flags:
            continue
        parts.append(value[last:start])
        parts.append(f"${key}|{flags}q$")
        last = end
        changed += 1
    parts.append(value[last:])
    return "".join(parts), changed


def _quote_escaping_problem(where: str, key: str, splices: list[str]) -> str:
    listed = ", ".join(f"`{s}`" for s in splices)
    return (
        f"{where}: {listed} in '{key}' sits inside a quoted argument of a loc "
        f"function and needs quote-escaping: add `q` to its flags (`$x|q$`, "
        f"`$x|vq$`); the game logs \"missing required quote-escaping\" otherwise"
    )


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
        if _VERSION_NO_SPACE_RE.match(line):
            problems.append(
                f"{rel}:{index}: '{key}' has no space between its version digit and the quote: "
                f"write `{key}:0 \"…\"`"
            )
        if key in seen:
            problems.append(
                f"{rel}:{index}: duplicate key '{key}' "
                f"(first defined at line {seen[key]})"
            )
        else:
            seen[key] = index

    for index, line in enumerate(lines, start=1):
        parsed = split_loc_line(line)
        if parsed is None:
            stripped = line.strip()
            key_line = _KEY_RE.match(line)
            if key_line and f"{key_line.group(1)}:" != expected_header:
                problems.append(
                    f"{rel}:{index}: the value of '{key_line.group(1)}' has no closing quote on its "
                    f"line: a newline written into the value? Write it as `\\n`"
                )
            elif stripped and not stripped.startswith("#") and not re.match(r"^l_[a-z_]+:$", stripped):
                problems.append(
                    f"{rel}:{index}: not a key line, a comment or the header: the rest of a "
                    f"value split across lines?"
                )
            continue
        key, value, trailing = parsed
        # A comment follows the value only if no quote does: `""#bold x#!""`
        # parses as an empty value and a "comment" that is really the text.
        rest = trailing.strip()
        if '"' in rest or (rest and not rest.startswith("#")):
            problems.append(
                f"{rel}:{index}: bare `\"` inside the value of '{key}' (or in a "
                f"trailing comment): the game reads to the line's last quote, the "
                f"repo's loc tools (translation, audits, the language build) stop "
                f"at this one; write a literal quote as `\\\"`"
            )
        elif len(_ESCAPED_QUOTE_RE.findall(value)) % 2:
            problems.append(
                f"{rel}:{index}: unpaired `\\\"` in '{key}': the game shows a "
                f"dangling quote mark"
            )
        unescaped = unescaped_quoted_splices(value)
        if unescaped:
            problems.append(_quote_escaping_problem(f"{rel}:{index}", key, unescaped))

    return problems


def _file_keys(path: str) -> dict[str, int]:
    """Each key a loc file defines, with the line it is first defined on."""
    keys: dict[str, int] = {}
    try:
        with open(path, encoding="utf-8-sig") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return keys  # check_file reports the file itself
    for index, line in enumerate(lines, start=1):
        match = _KEY_RE.match(line)
        if match and not re.match(r"^l_[a-z_]+$", match.group(1)):
            keys.setdefault(match.group(1), index)
    return keys


def check_replace_shadows(paths: list[str]) -> list[str]:
    """Check 10: a key both a `replace/` file and an ordinary file of the same
    language define. Reported on the ordinary copy, the one to delete. The
    language is the file name's `_l_<language>` suffix, as the game reads it,
    so any folder layout counts."""
    overrides: dict[tuple[str, str], tuple[str, int]] = {}
    ordinary: list[tuple[str, str]] = []
    for path in paths:
        suffix = _LANGUAGE_SUFFIX_RE.search(os.path.basename(path))
        if suffix is None:
            continue  # check_file reports the name
        language = suffix.group(1)
        if "replace" in os.path.normpath(path).split(os.sep):
            for key, line in _file_keys(path).items():
                overrides.setdefault((language, key), (path, line))
        else:
            ordinary.append((language, path))
    problems: list[str] = []
    for language, path in ordinary:
        for key, line in _file_keys(path).items():
            hit = overrides.get((language, key))
            if hit:
                problems.append(
                    f"{os.path.relpath(path, REPO_ROOT)}:{line}: '{key}' is also defined in "
                    f"{os.path.relpath(hit[0], REPO_ROOT)}:{hit[1]}, whose copy wins; "
                    f"delete this one"
                )
    return problems


def iter_tm_files(roots: list[str]) -> list[str]:
    """The translation memories (`.json` files in a `tm` folder) under roots."""
    found: list[str] = []
    for root in roots:
        if os.path.isdir(root):
            for dirpath, _dirnames, filenames in os.walk(root):
                parts = os.path.normpath(dirpath).split(os.sep)
                if "tm" in parts:
                    found.extend(
                        os.path.join(dirpath, name) for name in filenames if name.endswith(".json")
                    )
        elif root.endswith(".json") and "tm" in os.path.normpath(root).split(os.sep):
            found.append(root)
    return sorted(set(found))


def check_tm_file(path: str) -> list[str]:
    """Check 9 over one translation memory: every text field of every record
    (`en` and the translation; `base` names a key, not text)."""
    rel = os.path.relpath(path, REPO_ROOT)
    try:
        with open(path, encoding="utf-8") as fh:
            records = json.load(fh)
    except (OSError, ValueError) as exc:
        return [f"{rel}:1: not a readable translation memory ({exc})"]
    problems: list[str] = []
    for key, record in records.items():
        if not isinstance(record, dict):
            continue
        for field, text in record.items():
            if field == "base" or not isinstance(text, str):
                continue
            unescaped = unescaped_quoted_splices(text)
            if unescaped:
                problems.append(_quote_escaping_problem(f"{rel}: {key}.{field}", key, unescaped))
    return problems


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    roots = args or [os.path.join(REPO_ROOT, "localization"), os.path.join(REPO_ROOT, "i18n")]

    files = iter_loc_files(roots)
    tm_files = iter_tm_files(roots)
    if not files and not tm_files:
        print(f"No .yml files found under: {', '.join(roots)}", file=sys.stderr)
        return 1

    problems: list[str] = []
    for path in files:
        problems.extend(check_file(path))
    problems.extend(check_replace_shadows(files))
    for path in tm_files:
        problems.extend(check_tm_file(path))

    for problem in problems:
        print(problem, file=sys.stderr)

    tm_note = f" and {len(tm_files)} translation memor{'y' if len(tm_files) == 1 else 'ies'}" if tm_files else ""
    print(f"Checked {len(files)} localization file(s){tm_note}; {len(problems)} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
