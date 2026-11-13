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

Second check, `always_false`: `always = no` (or `always = false`) as an
immediate child of an `any_*` block. The iterator is true only when some
element matches its body, and `always = no` matches nothing, so the trigger is
false for every scope, and the `limit` or `trigger` holding it can never pass
(under a `NOT` it is always true instead). It is not "there is no X": write
`NOT = { any_X = { } }` for that. `colonial_collapse_effect` carried
`any_civil_war = { always = no }` for six months and never ran. A bare
`always = no` (a `potential` or `possible` retired on purpose) is not an
`any_*` body and is never flagged. This check reads tokens, not lines, so a
one-line `any_X = { always = no }` is caught too. Suppress with the same
trailing `# REVIEWED` comment, on the `any_*` opener line or on the
`always = no` line.

Third check, `filter_count`: a `filter = { }` child of an `any_*` block with
neither `percent` nor `count = all` beside it. The engine takes `filter` only
with one of those, and anything else fails at load ("Filter should only be
used if a percent or count = all is specified", then "PostValidate of
trigger 'any_X' returned false"): `filter` names the set a share or "all" is
measured against, and a plain count has no such set. Write the condition into
the body for a count, or turn the count into a share. The United Nations of
Earth's supermajority shipped `filter` with `count >= <value>` (2026-11-12).
Suppress with the same trailing `# REVIEWED` comment, on the `any_*` opener
line or on the `filter = {` line.
"""
import os
import re
from dataclasses import dataclass, field

from audit_common import AuditResult as _AuditResult
from audit_common import cli_main, parse_reviewed, write_text


@dataclass
class Flag:
    file: str
    line: int  # line of the offending `limit = {` / `always = no`
    any_name: str  # the enclosing any_* trigger
    any_line: int  # line of the any_* opener
    exemption: dict | None = None
    kind: str = "limit"  # "limit" or "always_false"


# What each flag kind is called in the report.
_KIND_LABEL = {
    "limit": "`limit`",
    "always_false": "`always = no`",
    "filter_count": "`filter` without `percent` or `count = all`",
}


@dataclass
class AuditResult(_AuditResult):
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


_OPENER_RE = re.compile(r"^\s*([A-Za-z_][\w]*)\s*=\s*\{")


def _split_comment(line: str) -> tuple[str, str | None]:
    idx = line.find("#")
    if idx < 0:
        return line, None
    return line[:idx], line[idx:]


_TOKEN_RE = re.compile(r"[{}]|\?=|[<>!=]=?|[^\s{}<>!=?]+")
_FALSE_VALUES = {"no", "false"}


def _scan_always_false(lines: list[str], rel_path: str) -> list[Flag]:
    """Token scan: flag `always = no|false` whose immediate enclosing block
    is an `any_*` trigger. Tokens rather than lines, so a one-line
    `any_X = { always = no }` is seen too."""
    toks: list[tuple[str, int, str | None]] = []  # (token, line, line comment)
    for line_num, raw in enumerate(lines, 1):
        content, comment = _split_comment(raw.rstrip("\n"))
        for tok in _TOKEN_RE.findall(content):
            toks.append((tok, line_num, comment))

    flags: list[Flag] = []
    stack: list[dict] = []
    for i, (tok, line_num, comment) in enumerate(toks):
        if tok == "{":
            name = None
            opener_line, opener_comment = line_num, comment
            if i >= 2 and toks[i - 1][0] in ("=", "?="):
                name, opener_line, opener_comment = toks[i - 2]
            stack.append({"name": name, "line": opener_line, "comment": opener_comment})
        elif tok == "}":
            if stack:
                stack.pop()
        elif (
            tok == "always"
            and i + 2 < len(toks)
            and toks[i + 1][0] == "="
            and toks[i + 2][0].lower() in _FALSE_VALUES
        ):
            parent = stack[-1] if stack else None
            if parent and parent["name"] and parent["name"].startswith("any_"):
                exemption = parse_reviewed(parent["comment"]) or parse_reviewed(comment)
                flags.append(Flag(
                    file=rel_path,
                    line=line_num,
                    any_name=parent["name"],
                    any_line=parent["line"],
                    exemption=exemption,
                    kind="always_false",
                ))
    return flags


_COMPARE_OPS = {"=", "?=", ">", ">=", "<", "<=", "!="}


def _scan_filter_count(lines: list[str], rel_path: str) -> list[Flag]:
    """Token scan: flag a `filter = {` whose immediate enclosing block is an
    `any_*` trigger that has neither a `percent` comparison nor `count = all`
    as a direct child (anywhere in the block, before or after the filter)."""
    toks: list[tuple[str, int, str | None]] = []  # (token, line, line comment)
    for line_num, raw in enumerate(lines, 1):
        content, comment = _split_comment(raw.rstrip("\n"))
        for tok in _TOKEN_RE.findall(content):
            toks.append((tok, line_num, comment))

    flags: list[Flag] = []
    stack: list[dict] = []
    for i, (tok, line_num, comment) in enumerate(toks):
        parent = stack[-1] if stack else None
        in_any = bool(parent and parent["name"] and parent["name"].startswith("any_"))
        if tok == "{":
            name = None
            opener_line, opener_comment = line_num, comment
            if i >= 2 and toks[i - 1][0] in ("=", "?="):
                name, opener_line, opener_comment = toks[i - 2]
            if in_any and name == "filter" and parent["filter"] is None:
                parent["filter"] = (opener_line, opener_comment)
            stack.append({"name": name, "line": opener_line, "comment": opener_comment,
                          "filter": None, "share": False})
        elif tok == "}":
            if not stack:
                continue
            frame = stack.pop()
            if frame["filter"] is not None and not frame["share"]:
                f_line, f_comment = frame["filter"]
                flags.append(Flag(
                    file=rel_path,
                    line=f_line,
                    any_name=frame["name"],
                    any_line=frame["line"],
                    exemption=parse_reviewed(frame["comment"]) or parse_reviewed(f_comment),
                    kind="filter_count",
                ))
        elif in_any and i + 1 < len(toks):
            op = toks[i + 1][0]
            if tok == "percent" and op in _COMPARE_OPS:
                parent["share"] = True
            elif (tok == "count" and op == "=" and i + 2 < len(toks)
                    and toks[i + 2][0] == "all"):
                parent["share"] = True
    return flags


def scan_file(filepath: str, rel_path: str) -> list[Flag]:
    """Brace-aware scan of one file; return flags for any `limit = {` whose
    immediate enclosing block is an `any_*` trigger, and for any
    `always = no` in the same position (`_scan_always_false`)."""
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
                    exemption=parse_reviewed(parent["comment"]),
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

    flags.extend(_scan_always_false(lines, rel_path))
    flags.extend(_scan_filter_count(lines, rel_path))
    flags.sort(key=lambda f: f.line)
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
    unrev = result.unreviewed
    exemp = result.exemptions

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
        "Also flagged: `always = no` (or `always = false`) as an immediate",
        "child of an `any_*` trigger. No element matches it, so the trigger is",
        "false for every scope and the block holding it can never pass. For",
        "\"there is no X\" write `NOT = { any_X = { } }`. A bare `always = no`",
        "outside an `any_*` (a retired `potential`) is not flagged.",
        "",
        "Also flagged: a `filter = { }` child of an `any_*` trigger with",
        "neither `percent` nor `count = all` beside it. The engine takes",
        "`filter` only with one of those and refuses the trigger at load",
        "(\"Filter should only be used if a percent or count = all is",
        "specified\"). For a count, write the condition into the body; for",
        "\"all but N\", use a `percent` share.",
        "",
        "Suppress a rare legitimate case with a trailing comment on the",
        "`any_*` opener line: `any_scope_state = { # REVIEWED YYYY-MM-DD: why`",
        "(for `always = no` or `filter`, the comment may also sit on that line).",
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
                    f"- line {f.line}: {_KIND_LABEL[f.kind]} inside `{f.any_name}` "
                    f"(opened at line {f.any_line})"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        # No line number on a reviewed entry: an edit above it would
        # otherwise churn the report.
        for f in exemp:
            out.append(
                f"- `{f.file}` — {_KIND_LABEL[f.kind]} inside `{f.any_name}` — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    # Flag counts only: `files_audited` stays on the result (and in the
    # regenerate() summary) but moves with every new file.
    out.append("## Coverage")
    out.append("")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- `always = no` flags: {sum(1 for f in result.flags if f.kind == 'always_false')}")
    out.append(f"- `filter` flags: {sum(1 for f in result.flags if f.kind == 'filter_count')}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_GENERATORS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    write_text(os.path.join(mod_path, "docs", "engine", "any_limit_report.md"), report)
    unrev = len(result.unreviewed)
    exemp = len(result.exemptions)
    return {
        "files_audited": result.files_audited,
        "total_flags": len(result.flags),
        "always_false_flags": sum(1 for f in result.flags if f.kind == "always_false"),
        "filter_count_flags": sum(1 for f in result.flags if f.kind == "filter_count"),
        "unreviewed": unrev,
        "exempted": exemp,
    }


def main(argv=None) -> int:
    """Print the report; `--strict` (CI) exits 1 if any flag lacks a
    `# REVIEWED ...` exemption."""
    from path_constants import mod_path
    return cli_main(lambda args: audit(mod_path=mod_path), lambda result, args: render_report(result),
                    argv=argv, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    raise SystemExit(main())
