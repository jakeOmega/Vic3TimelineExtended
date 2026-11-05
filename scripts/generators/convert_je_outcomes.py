"""One-shot conversion of the mod's journal entries to vanilla 1.15's outcomes.

Vanilla 1.15 replaced a journal entry's `complete`/`on_complete`,
`fail`/`on_fail`, `invalid`/`on_invalid` and `on_timeout` blocks, the four
`custom_*_header` fields and the `event_outcome_{completed,failed,timeout}_*`
fields with `outcome = { ... }` blocks (`<game>/common/journal_entries/
journal_entries.md`). The old fields log `Unexpected token` and are ignored, so
an unconverted entry never concludes (first 1.15 launch, 2026-11-05). This
script rewrites each entry the way vanilla converted its own, so every mod
entry comes out the same way (docs/audits/vanilla_1_15_prep.md § 3.1):

    complete + on_complete   ->  outcome { header effect_header color = "gold_positive"
                                           conclusion_desc trigger effect event_outcome_* }
    fail + on_fail           ->  the same with the failure headers and "blue_negative"
    invalid + on_invalid     ->  outcome { flags = { hidden invalid_outcome } conclusion_desc trigger effect }
    timeout = N + on_timeout ->  timeout = N stays; outcome { header = JOURNAL_ENTRY_TIMEOUT
                                           effect_header = JOURNAL_ENTRY_ON_TIMEOUT flags = { timeout }
                                           conclusion_desc effect }

Outcomes are written complete, fail, invalid, timeout (vanilla's own order in
all but a handful of its 1.15 entries), where the first old field stood. A
`custom_*_header` becomes the matching outcome's `header`/`effect_header`;
otherwise vanilla's `je_standard_*` keys. Each outcome's `conclusion_desc` is
`<entry>_{complete,fail,invalid,timeout}_conclusion_desc` (vanilla's naming for
its custom ones); the loc is written by hand beside the entry's other keys.

A trigger that can never be true (`always = no`, or an empty block) gives no
outcome, and the effect, headers and event outcome texts that only it could
reach go with it; so does an `on_*` effect with no trigger. The script prints
each such drop, so the loc it leaves without a user can be deleted.

Comments are kept: the comment lines directly above an old field (no blank
line between) move with it, and comments inside a block move with the block.
`REPLACE:`/`INJECT:` entries are skipped: a copy of a vanilla entry is rebuilt
from vanilla 1.15's text, not converted from the 1.14.5 copy.

Run from the repo root; with no arguments it rewrites every file under
common/journal_entries/ that has an old field, in place (one UTF-8 BOM, tabs):

    python3 scripts/generators/convert_je_outcomes.py [--check] [files...]

`--check` writes nothing and exits 1 if a file would change.
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JE_DIR = ROOT / "common" / "journal_entries"

BOM = "﻿"

# The old fields, by the outcome each feeds.
TRIGGER_OF = {"complete": "complete", "fail": "fail", "invalid": "invalid"}
EFFECT_OF = {"on_complete": "complete", "on_fail": "fail", "on_invalid": "invalid", "on_timeout": "timeout"}
HEADER_OF = {
    "custom_completion_header": ("complete", "header"),
    "custom_on_completion_header": ("complete", "effect_header"),
    "custom_failure_header": ("fail", "header"),
    "custom_on_failure_header": ("fail", "effect_header"),
}
EVENT_DESC_OF = {
    "event_outcome_completed_desc": ("complete", "event_outcome_desc"),
    "event_outcome_failed_desc": ("fail", "event_outcome_desc"),
    "event_outcome_timeout_desc": ("timeout", "event_outcome_desc"),
    "event_outcome_completed_effect_desc": ("complete", "event_outcome_effect_desc"),
    "event_outcome_failed_effect_desc": ("fail", "event_outcome_effect_desc"),
    "event_outcome_timeout_effect_desc": ("timeout", "event_outcome_effect_desc"),
}
OLD_FIELDS = set(TRIGGER_OF) | set(EFFECT_OF) | set(HEADER_OF) | set(EVENT_DESC_OF)
# Old fields this script has no mapping for: it stops rather than drop them.
UNSUPPORTED = {
    "on_complete_all_involved", "on_fail_all_involved", "on_invalid_all_involved", "on_timeout_all_involved",
    "event_outcome_invalidated_desc", "event_outcome_invalidated_effect_desc",
}

KINDS = ("complete", "fail", "invalid", "timeout")
STANDARD_HEADERS = {
    "complete": ("je_standard_completion_header", "je_standard_on_completion_header"),
    "fail": ("je_standard_failure_header", "je_standard_on_failure_header"),
    "timeout": ("JOURNAL_ENTRY_TIMEOUT", "JOURNAL_ENTRY_ON_TIMEOUT"),
}
COLOR = {"complete": '"gold_positive"', "fail": '"blue_negative"'}
FLAGS = {"invalid": "{ hidden invalid_outcome }", "timeout": "{ timeout }"}
CONCLUSION_SUFFIX = "_conclusion_desc"

TOKEN = re.compile(r'"[^"\n]*"|[{}]|[<>!?]=|[=<>]|[^\s{}=<>!?"]+')
OPERATORS = {"=", "?=", "<=", ">=", "!=", "<", ">"}


class LayoutError(ValueError):
    """A file laid out in a way the script does not convert safely."""


def conclusion_key(entry, kind):
    return f"{entry}_{kind}{CONCLUSION_SUFFIX}"


def mask(text):
    """`text` with comment and string contents blanked, same length and same newlines.

    Braces, `=` and `#` inside a quoted string or a comment then never count."""
    out = []
    state = "code"
    for ch in text:
        if state == "comment":
            if ch == "\n":
                state = "code"
                out.append(ch)
            else:
                out.append(" ")
        elif state == "string":
            if ch == '"':
                state = "code"
                out.append(ch)
            elif ch == "\n":
                raise LayoutError("a quoted string runs over a line end")
            else:
                out.append("x")
        elif ch == "#":
            state = "comment"
            out.append(" ")
        else:
            if ch == '"':
                state = "string"
            out.append(ch)
    return "".join(out)


@dataclass
class Field:
    key: str
    start: int  # the key's first character
    end: int  # one past the value's last character
    value_start: int
    is_block: bool
    children: list = field(default_factory=list)


def parse(masked):
    """The top-level fields of a masked file, each with its own direct children."""
    tokens = [(m.group(0), m.start(), m.end()) for m in TOKEN.finditer(masked)]
    pos = 0

    def block(depth):
        nonlocal pos
        items = []
        while pos < len(tokens):
            tok, start, end = tokens[pos]
            if tok == "}":
                if depth == 0:
                    raise LayoutError(f"unmatched '}}' at offset {start}")
                pos += 1
                return items, end
            if tok == "{":
                # an anonymous block (a list of blocks): keep its extent only
                pos += 1
                _, close = block(depth + 1)
                items.append(Field("", start, close, start, True))
                continue
            if pos + 1 < len(tokens) and tokens[pos + 1][0] in OPERATORS:
                if pos + 2 >= len(tokens):
                    raise LayoutError(f"{tok}: no value")
                value, vstart, vend = tokens[pos + 2]
                if value == "{":
                    pos += 3
                    children, close = block(depth + 1)
                    items.append(Field(tok, start, close, vstart, True, children))
                else:
                    pos += 3
                    items.append(Field(tok, start, vend, vstart, False))
                continue
            # a bare value in a list (flags = { hidden }, modifiers_while_active = { x })
            items.append(Field(tok, start, end, start, False))
            pos += 1
        if depth != 0:
            raise LayoutError("unclosed '{'")
        return items, len(masked)

    items, _ = block(0)
    return items


def line_start(text, offset):
    return text.rfind("\n", 0, offset) + 1


def line_end(text, offset):
    """One past the newline ending the line that holds `offset - 1` (or the text's end)."""
    at = text.find("\n", offset)
    return len(text) if at < 0 else at + 1


@dataclass
class Piece:
    """One old field as it stands in the file: its leading comment lines and its own lines."""
    field: Field
    comment_start: int  # first line of the comments attached above it
    start: int  # first line of the field
    end: int  # one past its last line's newline

    def text(self, original):
        return original[self.comment_start:self.end]

    def comments(self, original):
        return original[self.comment_start:self.start]

    def own(self, original):
        return original[self.start:self.end]


def locate(original, masked, f):
    start = line_start(original, f.start)
    if masked[start:f.start].strip():
        raise LayoutError(f"{f.key}: shares its line with the field before it")
    end = line_end(original, f.end)
    if masked[f.end:end].strip():
        raise LayoutError(f"{f.key}: shares its line with the field after it")
    comment_start = start
    while comment_start > 0:
        prev = line_start(original, comment_start - 1)
        line = original[prev:comment_start]
        if line.strip().startswith("#") and not masked[prev:comment_start].strip():
            comment_start = prev
        else:
            break
    return Piece(f, comment_start, start, end)


def body_is_never(masked, f):
    """True for `{ always = no }` or `{ }`: a trigger that can never pass."""
    inner = masked[f.value_start + 1:f.end - 1]
    return " ".join(inner.split()) in ("", "always = no")


def indent(text, by="\t"):
    return "".join(by + line if line.strip() else line for line in text.splitlines(keepends=True))


def renamed(original, piece, new_key):
    """The field's own lines, re-keyed and one level deeper."""
    f = piece.field
    own = original[piece.start:f.start] + new_key + original[f.start + len(f.key):piece.end]
    return indent(own)


@dataclass
class EntryResult:
    name: str
    outcomes: list  # kinds written, in order
    dropped: list  # (field key, why)


def convert_entry(original, masked, entry):
    """(start, end, replacement) splices for one entry, and what was done."""
    pieces = {}
    for child in entry.children:
        if child.key in UNSUPPORTED:
            raise LayoutError(f"{entry.key}.{child.key}: no 1.15 mapping in this script")
        if child.key in OLD_FIELDS:
            pieces.setdefault(child.key, []).append(locate(original, masked, child))
    timeout = [c for c in entry.children if c.key == "timeout"]
    if not pieces:
        return [], None
    for key, found in pieces.items():
        if len(found) > 1 and not key.startswith("event_outcome_"):
            raise LayoutError(f"{entry.key}: {key} appears {len(found)} times")

    dropped = []
    live = {}
    for kind in ("complete", "fail", "invalid"):
        trig = pieces.get(kind)
        if trig is None:
            live[kind] = False
        elif body_is_never(masked, trig[0].field):
            live[kind] = False
            dropped.append((kind, "never true" + comment_note(original, trig[0])))
        else:
            live[kind] = True
    live["timeout"] = bool(timeout)

    parts = {kind: {"trigger": None, "effect": None, "header": None, "effect_header": None,
                    "event_outcome_desc": [], "event_outcome_effect_desc": []} for kind in KINDS}
    for key, found in pieces.items():
        if key in TRIGGER_OF:
            kind, slot = TRIGGER_OF[key], "trigger"
        elif key in EFFECT_OF:
            kind, slot = EFFECT_OF[key], "effect"
        elif key in HEADER_OF:
            kind, slot = HEADER_OF[key]
        else:
            kind, slot = EVENT_DESC_OF[key]
        if not live[kind]:
            if key not in TRIGGER_OF:
                dropped.extend((key, f"its {kind} outcome is never reached" + comment_note(original, piece))
                               for piece in found)
            continue
        if isinstance(parts[kind][slot], list):
            parts[kind][slot].extend(found)
        else:
            parts[kind][slot] = found[0]

    name = entry.key
    tab = "\t"
    rendered = []
    written = []
    for kind in KINDS:
        if not live[kind]:
            continue
        p = parts[kind]
        lines = [f"{tab}outcome = {{\n"]
        inner = tab * 2
        if kind != "invalid":
            header, effect_header = STANDARD_HEADERS[kind]
            if p["header"] is not None:
                header = masked_value(original, p["header"].field)
            if p["effect_header"] is not None:
                effect_header = masked_value(original, p["effect_header"].field)
            lines.append(f"{inner}header = {header}\n")
            lines.append(f"{inner}effect_header = {effect_header}\n")
        if kind in COLOR:
            lines.append(f"{inner}color = {COLOR[kind]}\n")
        if kind in FLAGS:
            lines.append(f"{inner}flags = {FLAGS[kind]}\n")
        lines.append(f"{inner}conclusion_desc = {conclusion_key(name, kind)}\n")
        for header_piece in (p["header"], p["effect_header"]):
            if header_piece is not None and header_piece.comments(original):
                lines.append(indent(header_piece.comments(original)))
        if p["trigger"] is not None:
            lines.append(indent(p["trigger"].comments(original)))
            lines.append(renamed(original, p["trigger"], "trigger"))
        if p["effect"] is not None:
            lines.append(indent(p["effect"].comments(original)))
            lines.append(renamed(original, p["effect"], "effect"))
        for slot in ("event_outcome_desc", "event_outcome_effect_desc"):
            for piece in p[slot]:
                lines.append(indent(piece.comments(original)))
                lines.append(renamed(original, piece, slot))
        lines.append(f"{tab}}}\n")
        rendered.append("".join(lines))
        written.append(kind)

    all_pieces = sorted((piece for found in pieces.values() for piece in found), key=lambda p: p.comment_start)
    splices = []
    first = True
    for piece in all_pieces:
        start, end = piece.comment_start, piece.end
        # swallow the blank line after a removed field, so removals leave no gaps
        if original[end:end + 1] == "\n":
            end += 1
        elif original[end:end + 2] == "\t\n":
            end += 2
        replacement = ""
        if first:
            replacement = "\n".join(rendered) + ("\n" if rendered else "")
            first = False
        splices.append((start, end, replacement))
    return splices, EntryResult(name, written, dropped)


def comment_note(original, piece):
    lines = piece.comments(original).count("\n")
    return f"; {lines} comment line(s) above it dropped too" if lines else ""


def masked_value(original, f):
    return original[f.value_start:f.end].strip()


def convert_text(text):
    """(new text, [EntryResult]) for one file's text (BOM and all)."""
    has_bom = text.startswith(BOM)
    body = text[1:] if has_bom else text
    if "\r" in body:
        raise LayoutError("CRLF line endings")
    masked = mask(body)
    results = []
    splices = []
    for entry in parse(masked):
        if not entry.is_block or entry.key.startswith(("REPLACE:", "INJECT:")):
            if entry.is_block and any(c.key in OLD_FIELDS for c in entry.children):
                print(f"skipped {entry.key}: rebuild it from vanilla 1.15, don't convert it", file=sys.stderr)
            continue
        entry_splices, result = convert_entry(body, masked, entry)
        if result is not None:
            splices.extend(entry_splices)
            results.append(result)
    if not splices:
        return text, results
    return BOM + join(body, splices), results


JUNCTION = "\x00"


def join(body, splices):
    """Apply the splices, then tidy the blank lines at each splice point only.

    A removed field took the blank line after it; where it also had one before,
    or stood last in its entry, that leaves a doubled blank line or one before
    the entry's closing brace. Lines away from a splice are left as they were."""
    chunks = []
    prev = 0
    for start, end, replacement in sorted(splices):
        if start < prev:
            raise LayoutError("overlapping fields")
        chunks.extend((body[prev:start], JUNCTION, replacement, JUNCTION))
        prev = end
    chunks.append(body[prev:])
    out = "".join(chunks)
    rules = (
        (re.compile("\n\n(\x00+)\n"), "\n\n\\1"),  # blank, splice, blank: one blank
        (re.compile("\n\n(\x00+)(\t*\\})"), "\n\\1\\2"),  # blank, splice, closing brace: none
    )
    while True:
        new = out
        for pattern, repl in rules:
            new = pattern.sub(repl, new)
        if new == out:
            break
        out = new
    return out.replace(JUNCTION, "")


def default_files():
    return sorted(JE_DIR.glob("*.txt"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 if a file would change")
    args = parser.parse_args(argv)
    files = args.files or default_files()
    changed = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        try:
            new, results = convert_text(text)
        except LayoutError as e:
            print(f"{path}: {e}", file=sys.stderr)
            return 2
        if new == text:
            continue
        changed += 1
        rel = path.relative_to(ROOT) if path.is_absolute() and ROOT in path.parents else path
        for r in results:
            print(f"{rel}: {r.name}: {', '.join(r.outcomes) or 'no outcomes'}")
            for key, why in r.dropped:
                print(f"    dropped {key} ({why})")
        if not args.check:
            path.write_text(new, encoding="utf-8", newline="")
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
