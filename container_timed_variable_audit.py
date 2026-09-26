"""Audit for a timed variable set on a script container, where it never expires.

`set_variable = { name = x days = N }` is accepted in a script container's
scope, and `has_variable = x` is true afterwards, but the engine never counts
the time down there: the save stores the remaining days on the variable, and
on a container that number stays at N for good (on a country it falls). No
error, no warning. Found 2026-09-25 in a 1996 save where every UN resolution
back to No. 1 still carried 1825 days of `un_res_cooldown`, so every topic
that had ever come to a vote (a charter reform, sanctions, peacekeeping, ...)
was on cooldown for good; a mandate's 60-day binding grace `un_mnd_grace`
never ran out either. Vanilla creates no containers, so it has no precedent
either way. Documented in `scripting_best_practices.md` § "Per-Entity State:
Script Containers", rule 15.

What is flagged
---------------
A `set_variable` carrying `days`, `weeks`, `months` or `years` when either

- **its own scope is a container**: the scope it runs in also uses a
  container-only command (`has_tag`, `add_tag`, `remove_tag`, `clear_tags`,
  `destroy_container`, `set_parent`, `clear_parent`, `set_name`,
  `clear_name`), or is a container iterator (`every_container`, ...) or
  `create_container`'s `on_created` block; or
- **its variable is a container variable**: the same name is read or written
  (`has_variable`, `set_variable`, `change_variable`, `remove_variable`,
  `var:<name>`) in a scope that is a container by the rule above, anywhere in
  `common/` or `events/`. This catches the set site that sits in a plainer
  block, like a scripted effect whose container scope is only its caller's.

A scope is an entity's own block or any scope change (iterators, `root` /
`this` / `prev`, any `prefix:value` key such as `scope:x` or `var:x`, and the
engine's scope links), as in `prev_scope_audit`. Every other block (`if`,
`limit`, `hidden_effect`, effect and trigger blocks) belongs to the scope
around it.

Fix: keep a month count instead — `set_variable = { name = x_months value =
<named script value> }`, count it down from a global monthly pulse, and
`remove_variable` it at 0 (`un_resolution_cooldowns_tick`).

Suppress a deliberate case with a trailing `# REVIEWED YYYY-MM-DD: rationale`
comment on the `set_variable` line or on its `days` / `months` / ... line.
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from iterator_limit_audit import blank_comments_and_strings
from prev_scope_audit import _TOKEN_RE, _is_scope_change, _parse_reviewed, load_links

# Directories scanned, relative to the mod root: every scripted surface.
AUDIT_DIRS = ("common", "events")

# Commands that exist only in a script container's scope (engine docs; the
# 1.13.10 digest's script-container additions).
CONTAINER_ONLY_KEYS = {
    "has_tag", "add_tag", "remove_tag", "clear_tags", "destroy_container",
    "set_parent", "clear_parent", "set_name", "clear_name",
}
# Blocks whose inside is a container's scope.
CONTAINER_SCOPE_BLOCKS = re.compile(r"^(?:(?:every|any|random|ordered)_container|on_created)$")

TIME_KEYS = {"days", "weeks", "months", "years"}
# `<key> = <name>` reads or writes the variable <name> in the current scope.
VAR_VALUE_KEYS = {"has_variable", "set_variable", "remove_variable"}
# `<key> = { name = <name> ... }` does the same.
VAR_BLOCK_KEYS = {"set_variable", "change_variable", "clamp_variable", "round_variable"}


@dataclass
class TimedSet:
    name: str
    line: int  # the set_variable line
    time_line: int  # the days / months / ... line
    time_key: str


@dataclass
class _Scope:
    evidence: tuple[str, int] | None = None  # first container-only key seen
    var_refs: list[tuple[str, int]] = field(default_factory=list)
    timed_sets: list[TimedSet] = field(default_factory=list)


@dataclass
class ScanResult:
    """One file's scopes, reduced to what the mod-wide pass needs."""
    rel_path: str
    comments: dict[int, str]
    # (TimedSet, evidence or None) for every timed set in the file.
    timed_sets: list[tuple[TimedSet, tuple[str, int] | None]] = field(default_factory=list)
    # Variable names read or written in a container scope, with their line.
    container_vars: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class Flag:
    file: str
    line: int
    name: str
    time_key: str
    reason: str
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0
    container_var_names: int = 0


def _var_name(token: str | None) -> str | None:
    """`var:x` (or `var:x.owner`) -> `x`; anything else -> None."""
    if not token:
        return None
    head = token.split(".", 1)[0]
    if head.lower().startswith("var:"):
        return head[4:] or None
    return None


def scan_text(text: str, rel_path: str, links: set[str]) -> ScanResult:
    clean, comments = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]

    def line_of(pos: int) -> int:
        return bisect_right(starts, pos)

    scopes: list[_Scope] = []
    # Frames: (key, line, scope index, var-block state or None). A var-block
    # state is [name, TimedSet fields...] collected while inside
    # `set_variable = { ... }` and friends.
    stack: list[tuple[str | None, int, int, dict | None]] = []

    def current() -> _Scope | None:
        return scopes[stack[-1][2]] if stack else None

    def note_var(name: str | None, line: int) -> None:
        scope = current()
        if name and scope is not None:
            scope.var_refs.append((name, line))

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                key, line, scope_idx, vb = stack.pop()
                if vb is not None and vb.get("name"):
                    scope = scopes[scope_idx]
                    scope.var_refs.append((vb["name"], line))
                    if key == "set_variable" and vb.get("time_key"):
                        scope.timed_sets.append(TimedSet(
                            name=vb["name"], line=line,
                            time_line=vb["time_line"], time_key=vb["time_key"],
                        ))
            continue
        if m.group("anon"):
            idx = stack[-1][2] if stack else len(scopes)
            if not stack:
                scopes.append(_Scope())
            stack.append((None, line_of(m.start()), idx, None))
            continue

        key = m.group("key")
        value = m.group("value")
        line = line_of(m.start("key"))

        # Inside a var block: collect its name and any duration.
        vb = stack[-1][3] if stack else None
        if vb is not None:
            if key == "name" and value:
                vb["name"] = value
            elif key in TIME_KEYS and "time_key" not in vb:
                vb["time_key"] = key
                vb["time_line"] = line

        scope = current()
        if scope is not None:
            if key in CONTAINER_ONLY_KEYS and scope.evidence is None:
                scope.evidence = (key, line)
            if key in VAR_VALUE_KEYS and value and not m.group("open"):
                note_var(value, line)
            # A `var:x` read belongs to the scope it is written in, even when
            # it opens a block (`var:x ?= { ... }` is evaluated from outside).
            note_var(_var_name(key), line)
            note_var(_var_name(value), line)

        if m.group("open"):
            if not stack:
                scopes.append(_Scope())
                idx = len(scopes) - 1
            elif _is_scope_change(key, links) or CONTAINER_SCOPE_BLOCKS.match(key):
                scopes.append(_Scope())
                idx = len(scopes) - 1
                if CONTAINER_SCOPE_BLOCKS.match(key):
                    scopes[idx].evidence = (key, line)
            else:
                idx = stack[-1][2]
            state = {} if key in VAR_BLOCK_KEYS else None
            stack.append((key, line, idx, state))

    result = ScanResult(rel_path=rel_path, comments=comments)
    for scope in scopes:
        for ts in scope.timed_sets:
            result.timed_sets.append((ts, scope.evidence))
        if scope.evidence is not None:
            result.container_vars.extend(scope.var_refs)
    return result


def evaluate(scans: list[ScanResult]) -> list[Flag]:
    """Flag the timed sets: in a container scope, or of a container variable."""
    container_vars: dict[str, tuple[str, int]] = {}
    for scan in scans:
        for name, line in scan.container_vars:
            container_vars.setdefault(name, (scan.rel_path, line))

    flags: list[Flag] = []
    for scan in scans:
        for ts, evidence in scan.timed_sets:
            if evidence is not None:
                reason = f"its scope is a container (`{evidence[0]}`, line {evidence[1]})"
            elif ts.name in container_vars:
                where = container_vars[ts.name]
                reason = f"`{ts.name}` is used on a container at `{where[0]}:{where[1]}`"
            else:
                continue
            flags.append(Flag(
                file=scan.rel_path,
                line=ts.line,
                name=ts.name,
                time_key=ts.time_key,
                reason=reason,
                exemption=(
                    _parse_reviewed(scan.comments.get(ts.line))
                    or _parse_reviewed(scan.comments.get(ts.time_line))
                ),
            ))
    return flags


def scan_file(filepath: str, rel_path: str, links: set[str]) -> ScanResult:
    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return ScanResult(rel_path=rel_path, comments={})
    return scan_text(text, rel_path, links)


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    links = load_links(mod_path)
    scans: list[ScanResult] = []
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
                scans.append(scan_file(abs_p, rel_p, links))

    names = {name for scan in scans for name, _ in scan.container_vars}
    return AuditResult(
        flags=evaluate(scans),
        files_audited=len(scans),
        container_var_names=len(names),
    )


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Container timed variable audit report",
        "",
        "Auto-generated by `container_timed_variable_audit.py` on every",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a `set_variable` with `days` / `weeks` / `months` / `years`",
        "in a script container's scope, or of a variable the mod reads or",
        "writes on a container. The engine never expires a timed variable on a",
        "container: `has_variable` stays true for good. No engine diagnostic.",
        "",
        "Fix: store a month count (`value = <named script value>`), count it",
        "down from a global monthly pulse, and `remove_variable` it at 0.",
        "",
        "Suppress a deliberate case with a trailing comment on the",
        "`set_variable` line or its duration line:",
        "`days = 30 # REVIEWED YYYY-MM-DD: why`",
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
                    f"- line {f.line}: `set_variable` of `{f.name}` with "
                    f"`{f.time_key}` — {f.reason}"
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
                f"- `{f.file}:{f.line}` — `{f.name}` (`{f.time_key}`) — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    out.append(f"- files audited: {result.files_audited}")
    out.append(f"- variable names used on containers: {result.container_var_names}")
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
    out_path = os.path.join(mod_path, "docs", "engine", "container_timed_variable_report.md")
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
