"""Journal entry outcomes for the tests (vanilla 1.15).

1.15 replaced a journal entry's complete/on_complete, fail/on_fail,
invalid/on_invalid and on_timeout blocks with `outcome = { ... }` blocks
(<game>/common/journal_entries/journal_entries.md). A test that cut
`on_complete` out of an entry by name finds its outcome here instead, by kind:

    complete  the success outcome: color = "gold_positive" (or the standard completion header)
    fail      the failure outcome: color = "blue_negative" (or the standard failure header)
    invalid   flags = { hidden invalid_outcome }
    timeout   flags = { timeout }

Two layers, for the two ways the tests read script:
- text: `entry_text(file_text, name)`, `outcome_text(entry, kind)` and
  `outcome_part(entry, kind, "trigger" | "effect")` return block bodies, comments
  dropped, so a regex or `in` check reads them as before.
  `old_block(entry, "on_complete")` maps an old block name to its 1.15 place.
- parsed: `outcomes(entry_dict)` and `outcome(entry_dict, kind)` on the dicts
  ParadoxFileParser returns once its (operator, value) pairs are dropped (`plain`
  in test_tax_code_rule.py).

The order of a kind's outcomes is their order in the entry, so `index` picks
among several (an entry with more than one success outcome).
"""

import re

KINDS = ("complete", "fail", "invalid", "timeout")
OLD_BLOCKS = {
    "complete": ("complete", "trigger"),
    "on_complete": ("complete", "effect"),
    "fail": ("fail", "trigger"),
    "on_fail": ("fail", "effect"),
    "invalid": ("invalid", "trigger"),
    "on_invalid": ("invalid", "effect"),
    "on_timeout": ("timeout", "effect"),
}
_COLOR_KIND = {"gold_positive": "complete", "blue_negative": "fail"}
_HEADER_KIND = {"je_standard_completion_header": "complete", "je_standard_failure_header": "fail",
                "JOURNAL_ENTRY_TIMEOUT": "timeout"}


def strip_comments(text):
    """Drop `#` comments outside quoted strings ("#b x#!" is a format, not a comment)."""
    out = []
    for line in text.split("\n"):
        quoted = False
        cut = len(line)
        for i, ch in enumerate(line):
            if ch == '"':
                quoted = not quoted
            elif ch == "#" and not quoted:
                cut = i
                break
        out.append(line[:cut])
    return "\n".join(out)


def _close(text, opening):
    """Index of the brace closing the one at `opening` (comments already dropped)."""
    depth = 0
    quoted = False
    for i in range(opening, len(text)):
        ch = text[i]
        if ch == '"':
            quoted = not quoted
        elif quoted:
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unbalanced braces")


def _direct_blocks(body, key):
    """Bodies of every `key = { ... }` directly inside `body` (not nested deeper)."""
    found = []
    depth = 0
    quoted = False
    i = 0
    pattern = re.compile(r"(?<![\w.:\"])" + re.escape(key) + r"\s*=\s*\{")
    while i < len(body):
        ch = body[i]
        if ch == '"':
            quoted = not quoted
        elif not quoted:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif depth == 0:
                m = pattern.match(body, i)
                if m and (i == 0 or not (body[i - 1].isalnum() or body[i - 1] in "_.:")):
                    opening = m.end() - 1
                    end = _close(body, opening)
                    found.append(body[opening + 1:end])
                    i = end + 1
                    continue
        i += 1
    return found


def entry_text(file_text, name):
    """The body of the top-level entry `name = { ... }` (or `REPLACE:name`), comments dropped."""
    text = strip_comments(file_text.lstrip("﻿"))
    m = re.search(r"^(?:REPLACE:|INJECT:)?" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"entry {name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def field(entry, key):
    """The body of the entry's own `key = { ... }` (not one nested deeper)."""
    blocks = _direct_blocks(entry, key)
    if not blocks:
        raise AssertionError(f"no {key} block")
    return blocks[0]


def _scalar(body, key):
    m = re.search(r"(?m)^\s*" + re.escape(key) + r"\s*=\s*(\"[^\"]*\"|[^\s{}]+)", body)
    return m.group(1).strip('"') if m else None


def text_kind(outcome_body):
    """The kind of one outcome's body text."""
    flags = re.search(r"\bflags\s*=\s*\{([^}]*)\}", outcome_body)
    names = flags.group(1).split() if flags else []
    if "invalid_outcome" in names:
        return "invalid"
    if "timeout" in names:
        return "timeout"
    top = re.sub(r"\{[^{}]*\}", "", outcome_body)
    while re.search(r"\{[^{}]*\}", top):
        top = re.sub(r"\{[^{}]*\}", "", top)
    color = _scalar(top, "color")
    if color in _COLOR_KIND:
        return _COLOR_KIND[color]
    header = _scalar(top, "header")
    if header in _HEADER_KIND:
        return _HEADER_KIND[header]
    raise AssertionError(f"outcome of no known kind: color={color} header={header}")


def outcome_texts(entry):
    """Every outcome body of an entry body, in order."""
    return _direct_blocks(entry, "outcome")


def outcome_text(entry, kind, index=0):
    if kind not in KINDS:
        raise ValueError(kind)
    found = [body for body in outcome_texts(entry) if text_kind(body) == kind]
    if index >= len(found):
        raise AssertionError(f"no {kind} outcome #{index} (the entry has {len(found)})")
    return found[index]


def has_outcome(entry, kind):
    return any(text_kind(body) == kind for body in outcome_texts(entry))


def outcome_part(entry, kind, part, index=0):
    """The body of an outcome's `trigger` or `effect` (or any other direct block)."""
    blocks = _direct_blocks(outcome_text(entry, kind, index), part)
    if not blocks:
        raise AssertionError(f"the {kind} outcome has no {part}")
    return blocks[0]


def old_block(entry, name, index=0):
    """Where an old block's body lives in 1.15: `on_complete` is the success outcome's effect."""
    kind, part = OLD_BLOCKS[name]
    return outcome_part(entry, kind, part, index)


# ---- parsed entries --------------------------------------------------------

def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def parsed_kind(outcome_dict):
    names = _as_list(outcome_dict.get("flags"))
    if "invalid_outcome" in names:
        return "invalid"
    if "timeout" in names:
        return "timeout"
    color = str(outcome_dict.get("color", "")).strip('"')
    if color in _COLOR_KIND:
        return _COLOR_KIND[color]
    header = outcome_dict.get("header")
    if header in _HEADER_KIND:
        return _HEADER_KIND[header]
    raise AssertionError(f"outcome of no known kind: color={color} header={header}")


def outcomes(entry_dict):
    """Every outcome dict of a parsed entry, in order."""
    return _as_list(entry_dict.get("outcome"))


def outcome(entry_dict, kind, index=0):
    found = [o for o in outcomes(entry_dict) if parsed_kind(o) == kind]
    if index >= len(found):
        raise AssertionError(f"no {kind} outcome #{index} (the entry has {len(found)})")
    return found[index]
