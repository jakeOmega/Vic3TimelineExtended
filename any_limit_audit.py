"""Audit for `limit = { }` placed as an immediate child of an `any_*` trigger.

`any_*` counting triggers (`any_scope_state`, `any_scope_character`,
`any_neighbouring_country`, …) **do not accept a `limit = { }` block** — unlike
their `every_*` / `random_*` / `ordered_*` iterator cousins, which do. When
someone writes

    any_scope_state = {
        limit = { <filter> }   # SILENTLY IGNORED
        <conditions>
    }

(a natural carry-over from the iterator syntax), the engine ignores the `limit`
and evaluates the trigger against **all** members instead of the filtered
subset — flipping the trigger's meaning with no engine diagnostic. Documented in
CLAUDE.md gotchas + `scripting_best_practices.md`; this audit catches it
structurally.

Detection is a brace-aware line scan (mirroring `mod_structure_audit`) over
`common/` and `events/`. The key correctness rule: a `limit = {` is flagged only
when its **immediate** enclosing block is an `any_*` block. A `limit` nested one
level deeper inside a legitimate `every_*` / `random_*` / `ordered_*` /
`trigger_if` block within the `any_*` is fine and must NOT be flagged — that's
why the scan tracks the full opener stack and checks the stack top, not merely
"is there an `any_*` ancestor." `count` / `percent` children of `any_*` are also
valid; only `limit` is the bug.

Suppress a rare legitimate case with a trailing comment on the `any_*` opener
line: `any_scope_state = { # REVIEWED YYYY-MM-DD: rationale`.
"""
import os
import re
from dataclasses import dataclass, field


@dataclass
class Flag:
    file: str
    line: int  # line of the offending `limit = {`
    any_name: str  # the enclosing any_* trigger
    any_line: int  # line of the any_* opener
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


_OPENER_RE = re.compile(r"^\s*([A-Za-z_][\w]*)\s*=\s*\{")
_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)


def _split_comment(line: str) -> tuple[str, str | None]:
    idx = line.find("#")
    if idx < 0:
        return line, None
    return line[:idx], line[idx:]


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def scan_file(filepath: str, rel_path: str) -> list[Flag]:
    """Brace-aware scan of one file; return flags for any `limit = {` whose
    immediate enclosing block is an `any_*` trigger."""
    flags: list[Flag] = []
    # Stack of opener frames: {"name": str|None, "line": int, "comment": str|None}.
    # None name == an anonymous nesting level (extra `{` on a line we couldn't
    # attribute to a leading `name = {`).
    stack: list[dict] = []
    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return flags

    for line_num, raw in enumerate(lines, 1):
        content, comment = _split_comment(raw.rstrip("\n"))
        opens = content.count("{")
        closes = content.count("}")
        net = opens - closes
        m = _OPENER_RE.match(content)

        def _maybe_flag(name):
            if name != "limit":
                return
            parent = stack[-1] if stack else None
            if parent and parent["name"] and parent["name"].startswith("any_"):
                flags.append(Flag(
                    file=rel_path,
                    line=line_num,
                    any_name=parent["name"],
                    any_line=parent["line"],
                    exemption=_parse_reviewed(parent["comment"]),
                ))

        if net >= 1 and m:
            # A block opens here and stays open (possibly with extra nesting).
            _maybe_flag(m.group(1))
            stack.append({"name": m.group(1), "line": line_num, "comment": comment})
            for _ in range(net - 1):
                stack.append({"name": None, "line": line_num, "comment": None})
        elif net >= 1:
            for _ in range(net):
                stack.append({"name": None, "line": line_num, "comment": None})
        elif net == 0 and m and opens >= 1:
            # Balanced inline block: `name = { ... }` opens and closes here.
            _maybe_flag(m.group(1))
        elif net < 0:
            for _ in range(-net):
                if stack:
                    stack.pop()

    return flags


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    flags: list[Flag] = []
    files_audited = 0
    for sub in ("common", "events"):
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
        "# `any_*` limit audit report",
        "",
        "Auto-generated by `any_limit_audit.py` on every full `POST /reload`",
        "of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a `limit = { }` block placed as an immediate child of an",
        "`any_*` counting trigger. `any_*` triggers ignore `limit` (unlike",
        "`every_*` / `random_*` / `ordered_*`), so the filter is silently",
        "dropped and the trigger evaluates against all members — a meaning flip",
        "with no engine diagnostic.",
        "",
        "Fix: move the `limit` conditions up as direct conditions of the",
        "`any_*` block (they are ANDed there), or restructure the logic.",
        "",
        "Suppress a rare legitimate case with a trailing comment on the",
        "`any_*` opener line: `any_scope_state = { # REVIEWED YYYY-MM-DD: why`",
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
                    f"- line {f.line}: `limit` inside `{f.any_name}` "
                    f"(opened at line {f.any_line})"
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
                f"- `{f.file}:{f.line}` — `limit` inside `{f.any_name}` — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
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
    """POST_LOAD_GENERATORS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "any_limit_report.md")
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
