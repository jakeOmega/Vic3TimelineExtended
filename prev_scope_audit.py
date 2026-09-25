"""Audit for a `prev` that can only mean a scope the script names two lines up.

`prev` is the scope before the **most recent** scope change, and entering
`root = { }`, `scope:x = { }` or `c:TAG = { }` is a scope change like any
other. So in::

    every_power_bloc_member = {
        root = {
            power_bloc ?= {
                add_leverage = { target = prev value = 3 }   # prev = root
            }
        }
    }

`prev` is not the member being iterated — it is `root`, because
`power_bloc ?= { }` was entered from `root = { }`. The engine logs nothing:
`prev` is a valid country, and the effect lands on the wrong one once per
iteration. Found 2026-09-25 in `un_vote.2`, which gave a power-bloc leader
"<bloc> gains 3 Leverage in <itself>" twenty times over when its resolution
carried. Documented in `scripting_best_practices.md` § "`prev` Is One Scope
Change Back".

What is flagged
---------------
A `prev` (as a value, a block key, or the head of a `prev.x` chain) whose
enclosing scope changes, innermost first, are ``B`` then ``A`` then at least one
more, where ``A`` names its scope outright — `root` / `ROOT`, or any
`prefix:value` form (`scope:x`, `c:TAG`, `var:x`, `global_var:x`, …). There,
`prev` *is* ``A``: the author could have written ``A``'s name, having just
written it, and a `prev` there almost always means a scope further out —
usually the iterator the whole thing sits in. A `prev` directly inside ``A``
(``A`` innermost) is the ordinary, correct use and is not flagged; nor is a
chain with nothing outside ``A`` (the entity's own top-level block does not
count), where there is no further-out scope to confuse it with.

Scope changes are iterators (`every_` / `random_` / `ordered_` / `any_`,
not `random_list`), `root` / `ROOT` / `this` / `prev`, any key with a `:` or
`.` in it, and the engine's scope links (`event_targets.log`, via
`docs/engine/event_targets_summary.txt`: `owner`, `capital`, `power_bloc`, …).
Every other block — `if`, `limit`, `hidden_effect`, and effect or trigger
blocks such as `add_leverage = { }` — is transparent.

Fix: save the scope you mean (`save_temporary_scope_as = member`) and name it
(`target = scope:member`), which also survives later edits to the nesting.

Suppress a deliberate case with a trailing `# REVIEWED YYYY-MM-DD: rationale`
comment on the `prev` line or on ``A``'s opener line.
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from iterator_limit_audit import blank_comments_and_strings

# Directories scanned, relative to the mod root: every scripted surface.
AUDIT_DIRS = ("common", "events")

# Scope-link catalog, generated from the engine's event_targets.log.
EVENT_TARGETS = os.path.join("docs", "engine", "event_targets_summary.txt")

ITERATOR_PREFIXES = ("every_", "random_", "ordered_", "any_")
NON_ITERATOR_KEYS = {"random_list"}
SELF_REFERENCES = {"root", "this", "prev"}

_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)

# One pass over the cleaned text: a closing brace, a `key <op> {` opener, a
# `key <op> value` statement, or an unattributed `{` (e.g. `50 = {` inside a
# random_list, whose numeric key the key alternative deliberately skips).
_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[A-Za-z_][A-Za-z0-9_.:@$\-]*))?"
    r"|(?P<anon>\{)"
)


@dataclass
class Flag:
    file: str
    line: int  # line of the `prev`
    named: str  # the named scope `prev` resolves to (A)
    named_line: int
    inner: str  # the scope change entered from it (B)
    outer: str  # the nearest scope change outside A
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


def load_links(mod_path: str) -> set[str]:
    """Scope-link names from the event-targets catalog; empty if it is absent
    (the audit then recognises iterators and named scopes only)."""
    path = os.path.join(mod_path, EVENT_TARGETS)
    links: set[str] = set()
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or "|" not in line:
                    continue
                name = line.split("|")[1].strip()
                if name:
                    links.add(name)
    except OSError:
        pass
    return links


def _is_prev(token: str | None) -> bool:
    if not token:
        return False
    head = token.split(".", 1)[0]
    return head.lower() == "prev"


def _is_named(key: str) -> bool:
    """A scope named outright: `root`, or any `prefix:value` form."""
    head = key.split(".", 1)[0]
    return head.lower() == "root" or ":" in head


def _is_scope_change(key: str, links: set[str]) -> bool:
    if key in NON_ITERATOR_KEYS:
        return False
    if key.startswith(ITERATOR_PREFIXES):
        return True
    if key.lower() in SELF_REFERENCES:
        return True
    if ":" in key or "." in key:
        return True
    return key in links


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def scan_text(text: str, rel_path: str, links: set[str]) -> list[Flag]:
    flags: list[Flag] = []
    clean, comments = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]

    def line_of(pos: int) -> int:
        return bisect_right(starts, pos)

    # Frames: (key or None, line, is_scope_change). The entity's own
    # top-level block is never a scope change.
    stack: list[tuple[str | None, int, bool]] = []

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
            continue
        if m.group("anon"):
            stack.append((None, line_of(m.start()), False))
            continue

        key = m.group("key")
        line = line_of(m.start("key"))

        if _is_prev(key) or _is_prev(m.group("value")):
            chain = [(k, ln) for k, ln, sc in stack if sc]
            if len(chain) >= 3 and _is_named(chain[-2][0]):
                named, named_line = chain[-2]
                flags.append(Flag(
                    file=rel_path,
                    line=line,
                    named=named,
                    named_line=named_line,
                    inner=chain[-1][0],
                    outer=chain[-3][0],
                    exemption=(
                        _parse_reviewed(comments.get(line))
                        or _parse_reviewed(comments.get(named_line))
                    ),
                ))

        if m.group("open"):
            is_scope = bool(stack) and _is_scope_change(key, links)
            stack.append((key, line, is_scope))

    return flags


def scan_file(filepath: str, rel_path: str, links: set[str]) -> list[Flag]:
    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    return scan_text(text, rel_path, links)


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    links = load_links(mod_path)
    flags: list[Flag] = []
    files_audited = 0
    for sub in AUDIT_DIRS:
        root_dir = os.path.join(mod_path, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, dirs, files in os.walk(root_dir):
            dirs.sort()
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                rel_p = os.path.relpath(abs_p, mod_path)
                files_audited += 1
                flags.extend(scan_file(abs_p, rel_p, links))

    return AuditResult(flags=flags, files_audited=files_audited)


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# `prev` scope audit report",
        "",
        "Auto-generated by `prev_scope_audit.py` on every `POST /reload` of the",
        "mod state server. Do not hand-edit.",
        "",
        "Flagged: a `prev` inside a scope change that was itself entered from a",
        "scope the script names outright (`root`, `scope:x`, `c:TAG`, …), inside",
        "some further scope. `prev` is the scope before the most recent scope",
        "change, so there it is that named scope — not the iterator or outer",
        "scope it almost always is meant to be. No engine diagnostic.",
        "",
        "Fix: save the scope you mean (`save_temporary_scope_as = x`) and name",
        "it (`scope:x`).",
        "",
        "Suppress a deliberate case with a trailing comment on the `prev` line",
        "or on the named scope's opener line:",
        "`target = prev # REVIEWED YYYY-MM-DD: why`",
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
                    f"- line {f.line}: `prev` inside `{f.inner}`, entered from "
                    f"`{f.named}` (line {f.named_line}) inside `{f.outer}` — "
                    f"it resolves to `{f.named}`, not to `{f.outer}`'s scope"
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
                f"- `{f.file}:{f.line}` — `prev` = `{f.named}` inside "
                f"`{f.inner}` — **{f.exemption['date']}**: "
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
    out_path = os.path.join(mod_path, "docs", "engine", "prev_scope_report.md")
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
