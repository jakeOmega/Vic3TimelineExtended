"""Parse-time audit: duplicate scalar keys within a single modifier-family block.

The Clausewitz engine silently accepts a repeated `<key> = <value>` inside one
block. Its own `Duplicated key X will not be created` warning fires only on
**top-level entity** collisions, never on duplicate keys *inside* a block. For a
modifier block that means:

  * duplicate boolean `= yes` / identical-value scalar → inert noise (last-wins
    picks the same value), but pure clutter and a sign of a non-idempotent
    generator (issue #191 doubled 35+ unlock bools this way);
  * duplicate scalar with **differing** values → silently last-wins, dropping the
    other value (issue #190: conflicting `traded_quantity`).

This audit walks mod `.txt` files and flags duplicate **scalar-valued** keys
(`= <number>` / `= yes` / `= no`) inside the modifier-family container blocks
listed in `_MODIFIER_BLOCK_KEYS`. It deliberately does **not** look inside
script-value math blocks (`add = { multiply = … multiply = … }`) or effect
blocks, where a repeated key is a legitimate *sequential* operation, not a
map collision — that distinction is what keeps the false-positive rate at zero
(empirically verified against the full mod; see issue #192).

Severity: identical repeated value → `warn` (inert); differing value → `error`
(a real last-wins data loss). Both feed the `unreviewed` count so either fires
the POST /reload warnings array.

Suppress an intentional repeat with a same-line comment on the duplicate:
`# REVIEWED YYYY-MM-DD: rationale`.

Sibling of `modifier_visibility_audit.py`; registered in `POST_LOAD_AUDITS`.
"""

import os
import re
from dataclasses import dataclass, field


# Block-opener keys whose bodies are modifier *maps* (duplicate scalar key =
# bug). An explicit set — NOT suffix matching — so effect blocks like
# `add_modifier` / `remove_modifier` (which end in `_modifier` but are
# statements, not containers) are never tracked. Script-value math blocks
# (`add`, `multiply`, …) and list/AI-weight containers are intentionally absent.
_MODIFIER_BLOCK_KEYS = frozenset({
    "modifier",            # static_modifiers, laws, techs, buildings, AI-weight modifiers
    "member_modifier",     # power bloc principles
    "power_bloc_modifier",
    "institution_modifier",
    "country_modifiers",   # PM country_modifiers blocks
    "building_modifiers",  # PM building_modifiers blocks
    "state_modifiers",
    "character_modifier",
    "unit_modifier",
    # modifier-scaling wrappers (live inside the containers above)
    "workforce_scaled",
    "level_scaled",
    "throughput_scaled",
    "unscaled",
})


@dataclass
class DuplicateKeyFlag:
    file: str
    line: int           # line of the 2nd-or-later occurrence
    key: str
    value: str          # value at this occurrence
    first_line: int     # line of the first occurrence in the same block
    first_value: str
    block_key: str      # the enclosing modifier-family block opener
    severity: str       # "error" (differing value) | "warn" (identical value)
    exemption: dict | None = None  # {date, rationale} when REVIEWED


@dataclass
class AuditResult:
    flags: list[DuplicateKeyFlag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


# A line that is *exactly* a scalar assignment: `key = <number|yes|no>` with an
# optional trailing comment and nothing else. The strict `$` anchor guarantees
# the RHS is a bare scalar (never a `{` block, never multi-value), so we only
# ever compare map-style scalar fields.
_SCALAR_LINE_RE = re.compile(
    r"^[ \t]*(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
    r"(?P<value>-?\d+(?:\.\d+)?|yes|no)"
    r"(?:\s*(?P<comment>#.*))?\s*$"
)

# `key = {` — captures the opener key for a block.
_BLOCK_OPEN_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{")

_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


@dataclass
class _Frame:
    block_key: str
    tracked: bool
    seen: dict = field(default_factory=dict)  # scalar key -> (first_line, first_value)


def _brace_events(nocomment: str):
    """Yield ('open', opener_key|None) / ('close', None) in source order.

    Handles multiple braces on one line (`a = { b = {`) and out-of-order
    close-then-open (`} c = {`) by walking character positions.
    """
    opener_at = {}
    for m in _BLOCK_OPEN_RE.finditer(nocomment):
        opener_at[m.end() - 1] = m.group("key")  # position of the '{'
    for idx, ch in enumerate(nocomment):
        if ch == "{":
            yield "open", opener_at.get(idx)
        elif ch == "}":
            yield "close", None


def _scan_file(file_path: str, rel_path: str) -> tuple[list[DuplicateKeyFlag], int]:
    """Scan one file. Returns (flags, tracked_scalar_lines_seen)."""
    try:
        with open(file_path, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return [], 0
    return scan_text(text, rel_path)


def scan_text(text: str, rel_path: str) -> tuple[list[DuplicateKeyFlag], int]:
    """Scan raw text for duplicate scalar keys in modifier-family blocks.

    Returns (flags, tracked_scalar_lines_seen). Exposed for unit tests.
    """
    flags: list[DuplicateKeyFlag] = []
    tracked_hits = 0
    stack = [_Frame(block_key="<root>", tracked=False)]

    for i, line in enumerate(text.splitlines(), start=1):
        sm = _SCALAR_LINE_RE.match(line)
        if sm:
            # Pure scalar assignment line — never contains braces, so it cannot
            # change block depth. Record / flag against the current frame.
            frame = stack[-1]
            if frame.tracked:
                tracked_hits += 1
                key = sm.group("key")
                value = sm.group("value")
                if key in frame.seen:
                    first_line, first_value = frame.seen[key]
                    severity = "warn" if value == first_value else "error"
                    flags.append(DuplicateKeyFlag(
                        file=rel_path,
                        line=i,
                        key=key,
                        value=value,
                        first_line=first_line,
                        first_value=first_value,
                        block_key=frame.block_key,
                        severity=severity,
                        exemption=_parse_reviewed(sm.group("comment")),
                    ))
                else:
                    frame.seen[key] = (i, value)
            continue

        nocomment = line.split("#", 1)[0]
        for kind, opener in _brace_events(nocomment):
            if kind == "open":
                stack.append(_Frame(
                    block_key=opener or "<anon>",
                    tracked=(opener in _MODIFIER_BLOCK_KEYS),
                ))
            elif len(stack) > 1:
                stack.pop()

    return flags, tracked_hits


def _iter_scan_files(mod_path: str):
    """Yield (abs_path, rel_path) for every mod .txt under events/ and common/."""
    for base in ("events", "common"):
        base_dir = os.path.join(mod_path, base)
        if not os.path.isdir(base_dir):
            continue
        for root, _dirs, files in os.walk(base_dir):
            for fname in sorted(files):
                if fname.endswith(".txt"):
                    abs_p = os.path.join(root, fname)
                    yield abs_p, os.path.relpath(abs_p, mod_path)


def audit(ms=None, mod_path: str | None = None) -> AuditResult:
    """Walk events/ + common/ for duplicate scalar keys in modifier-family blocks."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    flags: list[DuplicateKeyFlag] = []
    files_audited = 0
    tracked_hits = 0
    for abs_p, rel_p in _iter_scan_files(mod_path):
        f, hits = _scan_file(abs_p, rel_p)
        flags.extend(f)
        tracked_hits += hits
        files_audited += 1

    return AuditResult(
        flags=flags,
        coverage={
            "files_audited": files_audited,
            "tracked_modifier_scalar_lines": tracked_hits,
        },
    )


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    errors = [f for f in unrev if f.severity == "error"]
    warns = [f for f in unrev if f.severity == "warn"]

    out = [
        "# Duplicate-key-within-block audit report",
        "",
        "Auto-generated by `duplicate_key_audit.py` on every `POST /reload` of the",
        "mod state server. Do not hand-edit.",
        "",
        "Flagged: a scalar key (`= <number>` / `= yes` / `= no`) that appears more",
        "than once inside the **same** modifier-family block. The engine accepts",
        "this silently and applies last-wins (or, for `_add`, stacks).",
        "",
        "- **error** — the repeated values *differ*, so one value is silently lost.",
        "- **warn** — the repeated values are identical: inert clutter (often a",
        "  non-idempotent generator, see #191).",
        "",
        "Scope: only the modifier-family container blocks in `_MODIFIER_BLOCK_KEYS`",
        "(`modifier`, `member_modifier`, `workforce_scaled`, …). Script-value math",
        "blocks (`add = { multiply … multiply … }`) and effect blocks are excluded",
        "— a repeated key there is a legitimate sequential operation, not a map",
        "collision.",
        "",
        "Suppress an intentional repeat with a same-line comment on the duplicate:",
        "`# REVIEWED YYYY-MM-DD: rationale`",
        "",
        f"## Errors — differing values, silent data loss ({len(errors)})",
        "",
    ]
    if not errors:
        out.append("_None._")
        out.append("")
    else:
        for f in errors:
            out.append(
                f"- `{f.file}:{f.line}` — `{f.key} = {f.value}` duplicates "
                f"`{f.key} = {f.first_value}` at line {f.first_line} "
                f"(inside `{f.block_key}` block); last-wins keeps `{f.value}`."
            )
        out.append("")

    out.append(f"## Warnings — identical repeats, inert clutter ({len(warns)})")
    out.append("")
    if not warns:
        out.append("_None._")
        out.append("")
    else:
        by_file: dict[str, list[DuplicateKeyFlag]] = {}
        for f in warns:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            for f in by_file[fname]:
                out.append(
                    f"- `{f.file}:{f.line}` — `{f.key} = {f.value}` repeats line "
                    f"{f.first_line} (inside `{f.block_key}` block)."
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
                f"- `{f.file}:{f.line}` — `{f.key} = {f.value}` "
                f"(dup of line {f.first_line}) — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    for k, v in result.coverage.items():
        out.append(f"- {k}: {v}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)} (errors: {len(errors)}, warns: {len(warns)})")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_GENERATORS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "duplicate_key_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    unrev = [f for f in result.flags if not f.exemption]
    errors = sum(1 for f in unrev if f.severity == "error")
    warns = sum(1 for f in unrev if f.severity == "warn")
    return {
        "files_audited": result.coverage.get("files_audited", 0),
        "total_flags": len(result.flags),
        # `unreviewed` is in _POST_LOAD_WARN_KEYS, so any nonzero value fires the
        # reload warnings array. Carry the full unsuppressed count (errors + warns).
        "unreviewed": len(unrev),
        "errors": errors,
        "warns": warns,
        "exempted": len(result.flags) - len(unrev),
    }


if __name__ == "__main__":
    import json
    res = audit()
    print(render_report(res))
    print(json.dumps({
        "total": len(res.flags),
        "errors": sum(1 for f in res.flags if f.severity == "error" and not f.exemption),
        "warns": sum(1 for f in res.flags if f.severity == "warn" and not f.exemption),
    }))
