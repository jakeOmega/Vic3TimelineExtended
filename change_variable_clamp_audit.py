"""Audit for `min =` / `max =` inside `change_variable`, where the direction is a guess.

The engine docs list `min` and `max` among `change_variable`'s operations but
say nothing about which way they clamp, and vanilla never uses them there. In
a script value, `max = N` caps the running total and `min = N` floors it
(`scripting_best_practices.md` § "Repeated `min` / `max` in a script value
are sequential clamps"), so `change_variable = { name = x max = 0 }` most
likely caps `x` at 0. Ten mod sites wrote it meaning a floor (found
2026-09-26): the nuclear programme's development setbacks (`max = 0` after a
subtraction, which would wipe the progress), Election Interference's "worst
phase reached" (`max = 3` from a start of 0, which keeps it at 0 so the
penalty never applied) and the Intelligence Sharing shield (`max = 0` on a
boost that has to be positive to count). No error, no warning either way.

Vanilla shows two forms whose direction nobody has to guess:

- `clamp_variable = { name = x max = 120 min = 0 }`: `min` is the floor and
  `max` the ceiling. Every vanilla site (8) passes both bounds, so pass both.
- an explicit `if = { limit = { var:x < 0 } set_variable = { name = x value = 0 } }`.

What is flagged
---------------
A `min` or `max` key directly inside a `change_variable`,
`change_global_variable` or `change_local_variable` block. A `min` / `max`
nested deeper (a script-value block such as `add = { value = y max = 3 }`)
is a script-value clamp and is not flagged.

Suppress a deliberate case with a trailing `# REVIEWED YYYY-MM-DD: rationale`
comment on the flagged `min` / `max` line or on the `change_variable = {`
line (the same line for the one-line form).
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from iterator_limit_audit import blank_comments_and_strings
from prev_scope_audit import _TOKEN_RE, _parse_reviewed

# Directories scanned, relative to the mod root: every scripted surface.
AUDIT_DIRS = ("common", "events")

CHANGE_KEYS = {"change_variable", "change_global_variable", "change_local_variable"}
BOUND_KEYS = {"min", "max"}

# The bound's right-hand side, for the report (`_TOKEN_RE`'s value group
# skips numbers, so read it off the raw text).
_BOUND_VALUE_RE = re.compile(r"\s*(?:\?=|[!<>=]=|[=<>])\s*([^\s{}#]+|\{)")


@dataclass
class Flag:
    file: str
    line: int  # the `min` / `max` line
    opener_line: int  # the `change_variable = {` line
    effect: str  # change_variable / change_global_variable / change_local_variable
    bound: str  # "min" or "max"
    value: str  # the bound's right-hand side ("{" for a block)
    name: str | None  # the variable, when the block names one
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


def scan_text(text: str, rel_path: str) -> list[Flag]:
    clean, comments = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]

    def line_of(pos: int) -> int:
        return bisect_right(starts, pos)

    # Frames: (key or None, line, state). `state` is a dict for a change_*
    # block (its variable name and bound hits), else None.
    stack: list[tuple[str | None, int, dict | None]] = []
    flags: list[Flag] = []

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                key, opener_line, state = stack.pop()
                if state is not None:
                    for bound, line, value in state["bounds"]:
                        flags.append(Flag(
                            file=rel_path,
                            line=line,
                            opener_line=opener_line,
                            effect=key,
                            bound=bound,
                            value=value,
                            name=state["name"],
                            exemption=(
                                _parse_reviewed(comments.get(line))
                                or _parse_reviewed(comments.get(opener_line))
                            ),
                        ))
            continue
        if m.group("anon"):
            stack.append((None, line_of(m.start()), None))
            continue

        key = m.group("key")
        line = line_of(m.start("key"))
        state = stack[-1][2] if stack else None
        if state is not None:
            if key == "name" and m.group("value"):
                state["name"] = m.group("value")
            elif key in BOUND_KEYS:
                vm = _BOUND_VALUE_RE.match(clean, m.end("key"))
                state["bounds"].append((key, line, vm.group(1) if vm else "?"))

        if m.group("open"):
            new_state = {"name": None, "bounds": []} if key in CHANGE_KEYS else None
            stack.append((key, line, new_state))

    flags.sort(key=lambda f: f.line)
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

    result = AuditResult()
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
                result.flags.extend(scan_file(abs_p, rel_p))
                result.files_audited += 1
    return result


def _describe(f: Flag) -> str:
    target = f"`{f.name}`" if f.name else "an unnamed variable"
    return f"`{f.effect}` of {target} carries `{f.bound} = {f.value}`"


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# change_variable clamp audit report",
        "",
        "Auto-generated by `change_variable_clamp_audit.py` on every",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a `min =` or `max =` directly inside `change_variable`,",
        "`change_global_variable` or `change_local_variable`. Vanilla never",
        "does this, and the direction is easy to get backwards: in a script",
        "value `max = N` caps and `min = N` floors, so `max = 0` written as",
        "\"no lower than 0\" most likely caps the variable at 0 instead. No",
        "engine diagnostic.",
        "",
        "Fix: `clamp_variable = { name = x max = <ceiling> min = <floor> }`,",
        "with both bounds as every vanilla site passes them, or an explicit",
        "`if = { limit = { var:x < N } set_variable = { name = x value = N } }`.",
        "",
        "Suppress a deliberate case with a trailing comment on the `min` /",
        "`max` line or on the `change_variable = {` line:",
        "`max = 3 # REVIEWED YYYY-MM-DD: why`",
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
                out.append(f"- line {f.line}: {_describe(f)}")
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
                f"- `{f.file}` — {_describe(f)} — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    # Flag counts only: the file count stays on the result (and in the
    # regenerate() summary) but moves with unrelated mod content.
    out.append("## Coverage")
    out.append("")
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
    out_path = os.path.join(mod_path, "docs", "engine", "change_variable_clamp_report.md")
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
