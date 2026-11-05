"""Audit `add_modifier` durations that the engine reads as 0 days.

`add_modifier = { name = X days = <script value> }` reads the value as **0
days** when the named script value is written as a block
(`name = { value = 7300 }`) or computed. The Planned Capital decision's option
said "Building the New Capital for 0 days" and "Planned Capital for 0 days"
until its two durations became literals (2026-10-23), while the money beside
them, from another `{ value = N }` value in the same file, was right. No error,
no warning. Every named duration vanilla passes is a bare number
(`normal_modifier_time = 1825` in `vanilla_parsed/common/script_values.json`),
so `name = N` works and `name = { value = N }` does not
(`scripting_best_practices.md` § "Modifier & Cooldown Duration Units").

What is flagged
---------------
A `days`, `months`, `years` or `weeks` key directly inside an `add_modifier`
block, in the mod's `common/` and `events/`, whose value is anything but a
number or the name of a script value written as a bare number (the mod's
`common/script_values/` first, then vanilla's from `vanilla_parsed/`):

* a script value written as a block: `{ value = N }`, or computed;
* a script value written as another name (`a = b`), which vanilla never does;
* an inline block (`days = { value = 30 }`);
* anything else: a name no script value has, a `var:` / `scope:` read.

A scripted effect that passes its own `$X$` to the field
(`ig_approval_effect`'s `days = $DAYS$`) is followed to its callers, and to
theirs when a caller forwards `X = $Y$` from its own parameters; each call's
literal argument is held to the same rule.

A computed duration has no fix in place: branch over a ladder of literals
(`un_propose_add_sponsor_mark`, `te_asat_rebuild_disruption`).

Suppress a deliberate case with a trailing `# REVIEWED YYYY-MM-DD: rationale`
comment on the duration's line or the `add_modifier = {` line, or, for a value
passed through a parameter, on the argument's line or the call's opening line.

Report: docs/engine/modifier_duration_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import json
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from iterator_limit_audit import blank_comments_and_strings
from prev_scope_audit import _parse_reviewed
from script_helper_index import _MERGE_PREFIX_RE

AUDIT_DIRS = ("common", "events")
TIME_KEYS = {"days", "months", "years", "weeks"}
VANILLA_VALUES = os.path.join("vanilla_parsed", "common", "script_values.json")

_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_$][A-Za-z0-9_.:|@$\-]*)\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[^\s{}]+))?"
    r"|(?P<anon>\{)"
)
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PARAM_RE = re.compile(r"\$([A-Za-z0-9_]+)\$")


@dataclass
class Flag:
    file: str
    line: int  # the duration's line, or the argument's
    opener_line: int  # the `add_modifier = {` line, or the call's
    key: str  # days / months / years / weeks, or the argument passed
    value: str  # as written ("{" for a block)
    problem: str  # block / alias / inline_block / not_a_constant
    detail: str  # where the value is defined, or what it is
    modifier: str | None = None  # the modifier's name, when the block names one
    via: str | None = None  # "helper.days" for a value passed through a parameter
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    # helper -> {parameter: the duration key it reaches}, for the report
    params_followed: dict[str, dict[str, str]] = field(default_factory=dict)
    files_audited: int = 0


@dataclass
class _Site:
    """A duration key inside an `add_modifier`."""
    file: str
    line: int
    opener_line: int
    key: str
    value: str
    modifier: str | None
    entity: str | None  # the enclosing scripted effect, in a scripted_effects file
    comments: dict[int, str]


@dataclass
class _Call:
    """A block call to one of the mod's scripted effects."""
    file: str
    line: int
    name: str
    args: dict[str, tuple[str, int]]  # key -> (value, line); value "{" for a block
    entity: str | None
    comments: dict[int, str]


def _line_starts(text: str) -> list[int]:
    return [0] + [m.end() for m in re.finditer(r"\n", text)]


def read_values(mod_path: str) -> dict[str, tuple[str, str]]:
    """name -> (form, where) for every script value: form "number", "block" or
    "alias". The mod's first (the first definition of a name), then vanilla's
    from the committed snapshot."""
    out: dict[str, tuple[str, str]] = {}
    base = os.path.join(mod_path, "common", "script_values")
    if os.path.isdir(base):
        for fname in sorted(os.listdir(base)):
            if not fname.endswith(".txt"):
                continue
            rel = f"common/script_values/{fname}"
            try:
                with open(os.path.join(base, fname), encoding="utf-8-sig", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            clean, _ = blank_comments_and_strings(text)
            starts = _line_starts(clean)
            depth = 0
            for m in _TOKEN_RE.finditer(clean):
                if m.group("close"):
                    depth = max(depth - 1, 0)
                    continue
                if m.group("anon"):
                    depth += 1
                    continue
                if depth == 0:
                    name = _MERGE_PREFIX_RE.sub("", m.group("key"))
                    where = f"{rel}:{bisect_right(starts, m.start())}"
                    value = m.group("value")
                    if m.group("open"):
                        form = "block"
                    elif value is not None and _NUMBER_RE.fullmatch(value):
                        form = "number"
                    else:
                        form = "alias"
                    if not name.startswith("@"):
                        out.setdefault(name, (form, where))
                if m.group("open"):
                    depth += 1
    try:
        with open(os.path.join(mod_path, VANILLA_VALUES), encoding="utf-8") as fh:
            vanilla = json.load(fh)
    except (OSError, ValueError):
        vanilla = {}
    for name, entry in vanilla.items():
        value = entry[1] if isinstance(entry, list) and len(entry) == 2 else None
        if isinstance(value, str):
            form = "number" if _NUMBER_RE.fullmatch(value) else "alias"
        else:
            form = "block"
        out.setdefault(name, (form, "vanilla"))
    return out


def classify(value: str, values: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    """None when the engine reads `value` as a duration, else (problem, detail)."""
    if value == "{":
        return "inline_block", "an inline script value"
    if _NUMBER_RE.fullmatch(value):
        return None
    if _NAME_RE.fullmatch(value):
        form, where = values.get(value, (None, ""))
        if form == "number":
            return None
        if form == "block":
            return "block", f"a script value written as a block ({where})"
        if form == "alias":
            return "alias", f"a script value written as another name ({where})"
        return "not_a_constant", "no script value has this name"
    return "not_a_constant", "not a script value"


def scan_text(text: str, rel: str, effects: set[str]) -> tuple[list[_Site], list[_Call]]:
    """Every duration key inside an `add_modifier`, and every block call to a
    scripted effect named in `effects`, in one file."""
    clean, comments = blank_comments_and_strings(text)
    starts = _line_starts(clean)
    parts = rel.replace("\\", "/").split("/")
    in_effects_file = len(parts) > 2 and parts[0] == "common" and parts[1] == "scripted_effects"

    sites: list[_Site] = []
    calls: list[_Call] = []
    # One frame per open brace: ("add_modifier", state), ("call", _Call) or None.
    stack: list[tuple[str, object] | None] = []
    entity: str | None = None

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                frame = stack.pop()
                if frame and frame[0] == "add_modifier":
                    state = frame[1]
                    for key, value, line in state["times"]:
                        sites.append(_Site(rel, line, state["line"], key, value, state["name"],
                                           entity if in_effects_file else None, comments))
            if not stack:
                entity = None
            continue
        if m.group("anon"):
            stack.append(None)
            continue

        key = m.group("key")
        line = bisect_right(starts, m.start("key"))
        is_open = bool(m.group("open"))
        value = m.group("value")

        if not stack:
            if is_open:
                entity = _MERGE_PREFIX_RE.sub("", key)
                stack.append(None)
            continue

        top = stack[-1]
        if top and top[0] == "add_modifier":
            if key == "name" and value:
                top[1]["name"] = value
            elif key in TIME_KEYS and (is_open or value is not None):
                top[1]["times"].append((key, "{" if is_open else value, line))
        elif top and top[0] == "call" and (is_open or value is not None):
            top[1].args.setdefault(key, ("{" if is_open else value, line))

        if is_open:
            if key == "add_modifier":
                stack.append(("add_modifier", {"line": line, "name": None, "times": []}))
            elif key in effects:
                call = _Call(rel, line, key, {}, entity if in_effects_file else None, comments)
                calls.append(call)
                stack.append(("call", call))
            else:
                stack.append(None)
    return sites, calls


def _mod_effects(mod_path: str) -> set[str]:
    """The names of the mod's scripted effects (depth-0 keys)."""
    names: set[str] = set()
    base = os.path.join(mod_path, "common", "scripted_effects")
    if not os.path.isdir(base):
        return names
    for fname in sorted(os.listdir(base)):
        if not fname.endswith(".txt"):
            continue
        try:
            with open(os.path.join(base, fname), encoding="utf-8-sig", errors="replace") as fh:
                clean, _ = blank_comments_and_strings(fh.read())
        except OSError:
            continue
        depth = 0
        for m in _TOKEN_RE.finditer(clean):
            if m.group("close"):
                depth = max(depth - 1, 0)
            elif m.group("anon"):
                depth += 1
            elif m.group("open"):
                if depth == 0:
                    names.add(_MERGE_PREFIX_RE.sub("", m.group("key")))
                depth += 1
    return names


def check(sites: list[_Site], calls: list[_Call], values: dict[str, tuple[str, str]],
          result: AuditResult) -> None:
    """Flag the direct sites, follow `$X$` durations to their callers, flag those."""
    # helper -> {param: the duration key it ends in}
    follow: dict[str, dict[str, str]] = {}
    for s in sites:
        pm = _PARAM_RE.fullmatch(s.value)
        if pm:
            if s.entity:
                follow.setdefault(s.entity, {}).setdefault(pm.group(1), s.key)
            continue
        if "$" in s.value:
            continue  # a name built from a parameter: nothing to look up
        problem = classify(s.value, values)
        if problem:
            result.flags.append(Flag(
                s.file, s.line, s.opener_line, s.key, s.value, *problem, modifier=s.modifier,
                exemption=_parse_reviewed(s.comments.get(s.line))
                or _parse_reviewed(s.comments.get(s.opener_line)),
            ))

    # A caller that forwards `X = $Y$` from its own parameters passes the duration on.
    changed = True
    while changed:
        changed = False
        for c in calls:
            for arg, key in list(follow.get(c.name, {}).items()):
                value = c.args.get(arg, ("", 0))[0]
                pm = _PARAM_RE.fullmatch(value)
                if pm and c.entity and pm.group(1) not in follow.get(c.entity, {}):
                    follow.setdefault(c.entity, {})[pm.group(1)] = key
                    changed = True

    for c in calls:
        for arg, key in follow.get(c.name, {}).items():
            if arg not in c.args:
                continue  # a missing argument is script_argument_audit's
            value, line = c.args[arg]
            if "$" in value:
                continue
            problem = classify(value, values)
            if problem:
                result.flags.append(Flag(
                    c.file, line, c.line, arg, value, *problem, via=f"{c.name}.{key}",
                    exemption=_parse_reviewed(c.comments.get(line))
                    or _parse_reviewed(c.comments.get(c.line)),
                ))
    result.params_followed = {h: dict(sorted(p.items())) for h, p in sorted(follow.items())}


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    result = AuditResult()
    effects = _mod_effects(mod_path)
    values = read_values(mod_path)
    sites: list[_Site] = []
    calls: list[_Call] = []
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
                rel_p = os.path.relpath(abs_p, mod_path).replace(os.sep, "/")
                try:
                    with open(abs_p, encoding="utf-8-sig", errors="replace") as fh:
                        text = fh.read()
                except OSError:
                    continue
                s, c = scan_text(text, rel_p, effects)
                sites.extend(s)
                calls.extend(c)
                result.files_audited += 1
    check(sites, calls, values, result)
    result.flags.sort(key=lambda f: (f.file, f.line))
    return result


def _describe(f: Flag) -> str:
    what = f"`{f.key} = {f.value}`" if f.value != "{" else f"`{f.key} = {{ ... }}`"
    if f.via:
        helper, key = f.via.split(".")
        return f"passes {what} to `{helper}`, whose `add_modifier` takes it as `{key}`: {f.detail}"
    target = f"`{f.modifier}`" if f.modifier else "a modifier"
    return f"`add_modifier` of {target} takes {what}: {f.detail}"


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Modifier duration audit report",
        "",
        "Auto-generated by `modifier_duration_audit.py` on every",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: an `add_modifier`'s `days` / `months` / `years` / `weeks`",
        "given anything but a number or a script value written as a bare",
        "number. The engine reads a script value written as a block",
        "(`name = { value = 7300 }`), or computed, as **0 days**: the Planned",
        "Capital option said \"for 0 days\" until its durations became",
        "literals. No engine diagnostic. A scripted effect that passes its own",
        "`$X$` to the field is followed to its callers.",
        "",
        "Fix: a constant becomes a bare `name = N` (vanilla's idiom,",
        "`normal_modifier_time = 1825`) or a literal at the call site; a",
        "computed duration becomes a ladder of literals.",
        "",
        "Suppress a deliberate case with a trailing comment on the duration's",
        "line or the `add_modifier = {` line (for a passed value, the argument's",
        "line or the call's): `# REVIEWED YYYY-MM-DD: why`",
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

    out.append("## Parameters Followed")
    out.append("")
    if not result.params_followed:
        out.append("_None._")
    else:
        for helper, params in result.params_followed.items():
            listed = ", ".join(f"`${p}$` (`{k}`)" for p, k in params.items())
            out.append(f"- `{helper}`: {listed}")
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
    out_path = os.path.join(mod_path, "docs", "engine", "modifier_duration_report.md")
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
