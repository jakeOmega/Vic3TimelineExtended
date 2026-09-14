"""Audit for an iterator `limit = { }` that is not the iterator's first child.

`every_*` / `random_*` / `ordered_*` / `any_*` take `limit = { }` as a
**property of the iteration**, not as a sequential statement. Everything in the
block runs (or is counted) only for members that satisfy the limit, no matter
where the `limit` sits::

    every_scope_state = {
        do_a = yes              # <- ALSO gated by the limit below
        limit = { has_building = X }
        do_b = yes
    }

Found 2026-09-12 in `remove_invalid_buildings` (`extra_on_actions.txt`), where
`remove_invalid_company_buildings_effect = yes` preceded an unrelated
space-program `limit`, silently gating a 3,250-line generated company sweep to
states holding a non-capital space program (fixed in #240 by splitting the
iteration in two). Documented in `scripting_best_practices.md` §
"Iterator `limit` Filters the Whole Iteration Regardless of Position".

Why a raw-text scan instead of `paradox_file_parser`
----------------------------------------------------
The parser is structurally unusable for this question. It folds repeated keys
into a list stored at the **first** occurrence of the key, and its tokenizer
discards line numbers and comments outright, so (a) a repeated sibling that
first appears before `limit` would be indistinguishable from one that only
appears after it, (b) dict order alone cannot answer "was this statement written
before the limit", and (c) there would be nothing to hang a
`# REVIEWED YYYY-MM-DD:` suppression comment on. This audit therefore walks the
raw text: comments and string bodies are blanked out (offsets preserved, so line
numbers stay exact), then a single regex streams `key = {`, `key = value` and
`}` in source order while a stack tracks the enclosing blocks. That also handles
several statements sharing one line, which a naive per-line scan would miss.

What is and isn't flagged
-------------------------
Only a **direct** `limit` child of an iterator block counts, and only when some
earlier sibling is an effect. Keys that configure the iteration itself
(`order_by`, `position`, `max`, `weight`, `count`, `percent`, a list
iterator's `variable`/`list`, a container iterator's `tag`/`tags`/scalar
`parent`, …) are order-independent and may legally precede `limit`. `random_list` is not an
iterator (its children are weights) and is excluded.

Note the overlap with `any_limit_audit`: `any_*` counting triggers ignore
`limit` entirely, at any position, so an `any_*` hit here is always also an
`any_limit_audit` hit. `any_*` is kept in scope so this audit stands alone.

Suppress a deliberate case with a trailing `# REVIEWED YYYY-MM-DD: rationale`
comment on either the `limit = {` line or the iterator's opener line.
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

# Iterator families that accept `limit = { }`.
ITERATOR_PREFIXES = ("every_", "random_", "ordered_", "any_")

# Keys that share an iterator prefix but are not iterators (`random_list`'s
# children are weights, never a `limit`). Listed so a future shape change
# can't quietly produce nonsense flags.
NON_ITERATOR_KEYS = {"random_list"}

# Iterator *properties*: order-independent configuration of the iteration
# itself, so they may legally sit before `limit` without gating anything.
ITERATOR_PROPERTY_KEYS = {
    "limit",
    "alternative_limit",
    "order_by",
    "position",
    "max",
    "check_range_bounds",
    "weight",
    "count",
    "percent",
    # List iterators (`every_in_list` and kin) name the list they walk.
    "variable",
    "list",
    # Container iterators (1.13.10+) filter by tag.
    "tag",
    "tags",
}

# Iterator properties only in scalar form. `parent = scope:x` filters a
# container iterator; `parent = { ... }` is a scope change, i.e. an effect.
SCALAR_ITERATOR_PROPERTY_KEYS = {"parent"}

# Directories scanned, relative to the mod root (issue #250).
AUDIT_DIRS = (
    os.path.join("common", "scripted_effects"),
    os.path.join("common", "on_actions"),
    os.path.join("common", "journal_entries"),
    os.path.join("common", "scripted_buttons"),
    "events",
)

_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)

# One pass over the cleaned text: a closing brace, a `key <op> {` opener, a
# `key <op> value` statement, or an unattributed `{` (e.g. `50 = {` inside a
# random_list, whose numeric key the key alternative deliberately skips).
_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)\s*(?:\?=|[!<>=]=|[=<>])\s*(?P<open>\{)?"
    r"|(?P<anon>\{)"
)


@dataclass
class Flag:
    file: str
    line: int  # line of the offending `limit = {`
    iterator: str  # enclosing every_* / random_* / ordered_* / any_* key
    iterator_line: int
    preceding_key: str  # the first effect sibling the limit silently gates
    preceding_line: int
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


def blank_comments_and_strings(text: str) -> tuple[str, dict[int, str]]:
    """Return (clean_text, comments_by_line).

    `clean_text` has the same length as `text` — comment bodies and quoted
    string bodies are replaced by spaces — so match offsets still map to real
    line numbers. `comments_by_line` keeps each line's raw comment text (the
    last one on the line) for `# REVIEWED` lookups.
    """
    out = list(text)
    comments: dict[int, str] = {}
    line = 1
    i = 0
    n = len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            in_string = False
            i += 1
            continue
        if in_string:
            if ch == '"':
                in_string = False
            else:
                out[i] = " "
            i += 1
            continue
        if ch == '"':
            in_string = True
            i += 1
            continue
        if ch == "#":
            end = text.find("\n", i)
            if end < 0:
                end = n
            comments[line] = text[i:end]
            for j in range(i, end):
                out[j] = " "
            i = end
            continue
        i += 1
    return "".join(out), comments


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _line_of(pos: int, starts: list[int]) -> int:
    return bisect_right(starts, pos)


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _is_iterator(name: str | None) -> bool:
    return bool(
        name
        and name not in NON_ITERATOR_KEYS
        and name.startswith(ITERATOR_PREFIXES)
    )


def scan_text(text: str, rel_path: str) -> list[Flag]:
    """Scan one file's raw text; return a flag per misplaced iterator `limit`."""
    flags: list[Flag] = []
    clean, comments = blank_comments_and_strings(text)
    starts = _line_starts(clean)
    # Frames: {"name": str|None, "line": int,
    #          "children": [(key, line, opens_block), ...]}
    stack: list[dict] = []

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
            continue
        if m.group("anon"):
            stack.append({"name": None, "line": _line_of(m.start(), starts),
                          "children": []})
            continue

        key = m.group("key")
        line = _line_of(m.start("key"), starts)
        parent = stack[-1] if stack else None

        if parent is not None:
            if key == "limit" and _is_iterator(parent["name"]):
                prior = next(
                    (c for c in parent["children"]
                     if c[0] not in ITERATOR_PROPERTY_KEYS
                     and not (c[0] in SCALAR_ITERATOR_PROPERTY_KEYS
                              and not c[2])),
                    None,
                )
                if prior is not None:
                    exemption = (
                        _parse_reviewed(comments.get(line))
                        or _parse_reviewed(comments.get(parent["line"]))
                    )
                    flags.append(Flag(
                        file=rel_path,
                        line=line,
                        iterator=parent["name"],
                        iterator_line=parent["line"],
                        preceding_key=prior[0],
                        preceding_line=prior[1],
                        exemption=exemption,
                    ))
            parent["children"].append((key, line, bool(m.group("open"))))

        if m.group("open"):
            stack.append({"name": key, "line": line, "children": []})

    return flags


def scan_file(filepath: str, rel_path: str) -> list[Flag]:
    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    return scan_text(text, rel_path)


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    flags: list[Flag] = []
    files_audited = 0
    for sub in AUDIT_DIRS:
        root_dir = os.path.join(mod_path, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, _dirs, files in os.walk(root_dir):
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                rel_p = os.path.relpath(abs_p, mod_path)
                files_audited += 1
                flags.extend(scan_file(abs_p, rel_p))

    return AuditResult(flags=flags, files_audited=files_audited)


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Iterator `limit` placement audit report",
        "",
        "Auto-generated by `iterator_limit_audit.py` on every `POST /reload`",
        "of the mod state server. Do not hand-edit.",
        "",
        "Flagged: an `every_*` / `random_*` / `ordered_*` / `any_*` block whose",
        "`limit = { }` is preceded by an effect sibling. An iterator's `limit`",
        "filters the whole iteration regardless of where it is written, so the",
        "earlier statement is silently gated by it too — no engine diagnostic.",
        "",
        "Fix: move the `limit` to the top of the block, or split into two",
        "iterations when two child effects need different filters.",
        "",
        "Suppress a deliberate case with a trailing comment on the `limit = {`",
        "line or the iterator's opener line:",
        "`limit = { # REVIEWED YYYY-MM-DD: why`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        by_file: dict[str, list[Flag]] = {}
        for f in unrev:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            out.append(f"### `{fname}`")
            out.append("")
            for f in by_file[fname]:
                out.append(
                    f"- line {f.line}: `limit` inside `{f.iterator}` (opened at "
                    f"line {f.iterator_line}) — silently gates "
                    f"`{f.preceding_key}` at line {f.preceding_line}"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.line}` — `limit` inside `{f.iterator}` after "
                f"`{f.preceding_key}` — **{f.exemption['date']}**: "
                f"{f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    out.append(f"- files audited: {result.files_audited}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "iterator_limit_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    return {
        "files_audited": result.files_audited,
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    print(render_report(result))
    # --strict: CI mode. Exit 1 if any flag lacks a `# REVIEWED ...` exemption.
    if "--strict" in sys.argv:
        raise SystemExit(1 if any(not f.exemption for f in result.flags) else 0)
