"""Audit scripted effect and trigger calls whose arguments don't match the callee (#732).

The engine compiles a parameterized scripted effect or trigger once per call,
from the `$X$` names in its body. Two call shapes fail that compile, and the
call can't be trusted to run:

  * An argument the body never names:
    `Compiling source for <callee> failed for unknown arguments: SETTING`.
    A callee with no `$X$` at all, called with a block, logs
    `Scripted trigger should have no arguments` and
    `PostValidate of trigger '<callee>' returned false` instead.
  * A `$X$` the call doesn't pass: `... failed for missing arguments: X`.
    `helper = yes` and the positional `helper = ROOT` pass nothing.

Both log at every load and nothing else catches them. `st_res_policy_set_by_hand_base`
took an unused `SETTING` from both Strategic Reserve steppers for weeks (64
lines a launch), and the tax code's `te_tax_obl_is_maintenance` dispatcher
then cited it as precedent and shipped kinds 2 and 4 the same way (#731).

What is checked
---------------
Every call in the mod's `common/` and `events/` to a scripted effect or
trigger the mod defines, and to vanilla's when the game files are on disk
(`<base_game_path>/game`; CI and cloud sessions have none and check mod
callees only). Call forms: `helper = { K = v ... }`, `helper = yes|no`, and a
positional `helper = <value>` to a callee that takes parameters.

A dispatcher call whose name holds a parameter, such as
`te_tax_obl_is_maintenance_$KIND$ = { ARG = $ARG$ TARGET = $TARGET$ }`, is
expanded against the literal values the call chain passes for KIND (following
`KIND = $KIND$` forwarding up through the helpers that call it) and every
expansion is checked. A literal expansion that names no helper, in a family
where siblings exist, is flagged too: the engine reports it as an unknown
effect or trigger. When some call in the chain passes a non-literal, every
defined helper the name pattern matches is checked instead.

A name defined both as a scripted effect and as a scripted trigger passes if
the call matches either signature.

Suppression is check-tagged, on the call's line (its opening line for a
multi-line call):

    # REVIEWED 2026-10-05 (script_argument): rationale

A tag that suppresses nothing is stale and fails `--strict`. Without the game
files, a tag on a line that calls a helper outside the index is left alone,
since the vanilla callee can't be checked. The check name is listed in
`event_context_audit.FOREIGN_CHECKS`, which reads every tag inside an event.

Report: docs/engine/script_argument_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import itertools
import os
import re
from dataclasses import dataclass, field

from script_helper_index import (
    _MERGE_PREFIX_RE,
    PARAM_RE,
    Definition,
    blank_comments,
    line_of,
    line_starts,
    load_helpers,
    read_script,
    vanilla_game_dir,
)

CHECK = "script_argument"
AUDIT_DIRS = ("common", "events")
HELPER_DIR_NAMES = {"scripted_effects", "scripted_triggers"}

_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_$][A-Za-z0-9_.:|@$\-]*)\s*(?P<op>\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[^\s{}]+))?"
    r"|(?P<anon>\{)"
)
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)
_FORWARD_RE = re.compile(r"\$([A-Za-z0-9_]+)\$")
_LITERAL_RE = re.compile(r"[A-Za-z0-9_]+")
_BOOL = {"yes", "no"}


@dataclass
class Call:
    file: str
    line: int
    name: str  # as written; a dispatcher's holds `$X$`
    form: str  # "block", "bool" or "scalar"
    args: dict[str, str | None] = field(default_factory=dict)  # None: block value
    value: str | None = None  # the right-hand side of a bool / scalar call
    helper: str | None = None  # enclosing definition, in a helper file


@dataclass
class Flag:
    file: str
    line: int
    call: str  # the name as written
    callee: str
    unknown: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    no_params_block: bool = False  # block call to a callee with no `$X$`
    target_missing: bool = False  # dispatcher expansion that names no helper
    exemption: dict | None = None


@dataclass
class StaleTag:
    file: str
    line: int


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    files_audited: int = 0
    calls_checked: int = 0
    helpers_indexed: int = 0
    vanilla_indexed: bool = False
    # For GET /script-args: the helper index, and every call that reaches
    # each helper (a dispatcher's at each helper it expands to).
    helpers: dict[str, list[Definition]] = field(default_factory=dict, repr=False)
    call_sites: dict[str, list[Call]] = field(default_factory=dict, repr=False)

    @property
    def failing(self) -> int:
        return sum(1 for f in self.flags if not f.exemption) + len(self.stale_tags)


@dataclass
class _FileScan:
    file: str
    calls: list[Call]
    tags: dict[int, dict]
    # line -> names in call position (`x = {`, `x = yes`) that the index
    # doesn't hold; used to spare tags on unverifiable vanilla calls.
    unindexed: dict[int, set[str]]


def _parse_tags(text: str) -> dict[int, dict]:
    tags: dict[int, dict] = {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        if "REVIEWED" not in raw:
            continue
        m = _TAGGED_REVIEWED_RE.search(raw)
        if m and CHECK in re.split(r"[\s,]+", m.group("checks").strip()):
            tags[lineno] = {"date": m.group("date"), "rationale": m.group("rationale").strip()}
    return tags


def scan_text(text: str, rel: str, helpers: dict[str, list[Definition]]) -> _FileScan:
    """Every call in one file: to a known helper, or through a `$X$` name."""
    no_comments, clean = blank_comments(text)
    starts = line_starts(clean)
    parts = rel.replace("\\", "/").split("/")
    in_helper_file = len(parts) > 2 and parts[0] == "common" and parts[1] in HELPER_DIR_NAMES

    calls: list[Call] = []
    unindexed: dict[int, set[str]] = {}
    # One frame per open brace: the Call collecting its arguments, or None.
    stack: list[Call | None] = []
    entity: str | None = None

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
            if not stack:
                entity = None
            continue
        if m.group("anon"):
            stack.append(None)
            continue

        key = m.group("key")
        is_open = bool(m.group("open"))
        value = m.group("value")
        if value is not None and value.startswith('"'):
            # Strings are blanked in `clean`; read the real text back.
            end = no_comments.find('"', m.start("value") + 1)
            value = no_comments[m.start("value"):end + 1 if end >= 0 else m.end("value")]

        if not stack:
            if is_open:
                entity = _MERGE_PREFIX_RE.sub("", key)
                stack.append(None)
            continue

        top = stack[-1]
        if top is not None:
            top.args[key] = None if is_open else value

        call: Call | None = None
        if m.group("op") == "=" and (is_open or value is not None):
            line = line_of(starts, m.start("key"))
            form = "block" if is_open else ("bool" if value in _BOOL else "scalar")
            if "$" in key:
                if form != "scalar":
                    call = Call(rel, line, key, form, value=value,
                                helper=entity if in_helper_file else None)
            elif key in helpers:
                call = Call(rel, line, key, form, value=value,
                            helper=entity if in_helper_file else None)
            elif form != "scalar" and top is None:
                unindexed.setdefault(line, set()).add(key)
            if call is not None:
                calls.append(call)
        if is_open:
            stack.append(call if call is not None and call.form == "block" else None)

    return _FileScan(rel, calls, _parse_tags(text), unindexed)


def _signature_problems(call: Call, d: Definition) -> tuple[list[str], list[str], bool]:
    """(unknown, missing, no_params_block) for one call against one definition.
    An argument key that is itself a `$X$` can't be checked, and hides which
    parameters the call passes, so it skips the missing check."""
    passed = {k for k in call.args if "$" not in k}
    if call.form == "block" and not d.params and call.args:
        return sorted(passed), [], True
    unknown = sorted(passed - d.params)
    missing = [] if len(passed) < len(call.args) else sorted(d.params - passed)
    return unknown, missing, False


def _best_signature(call: Call, defs: list[Definition]) -> tuple[list[str], list[str], bool]:
    """The definition the call fits best: a name that is both an effect and a
    trigger passes if the call matches either."""
    best: tuple | None = None
    for d in defs:
        unknown, missing, no_params = _signature_problems(call, d)
        score = len(unknown) + len(missing) + no_params
        if best is None or score < best[0]:
            best = (score, unknown, missing, no_params)
    return best[1:]


def _check(call: Call, callee: str, defs: list[Definition]) -> Flag | None:
    unknown, missing, no_params = _best_signature(call, defs)
    if not unknown and not missing and not no_params:
        return None
    return Flag(call.file, call.line, call.name, callee, unknown, missing, no_params)


def _param_values(helper: str, param: str, calls_by_name: dict[str, list[Call]],
                  seen: set) -> set[str] | None:
    """The literal values `param` takes at every call of `helper`, following
    `PARAM = $OUTER$` forwarding into the helpers that make those calls. None
    when any call passes something else, or nothing, or no call exists."""
    if (helper, param) in seen:
        return set()
    seen.add((helper, param))
    sites = calls_by_name.get(helper)
    if not sites:
        return None
    out: set[str] = set()
    for c in sites:
        if param not in c.args or c.args[param] is None:
            return None
        v = c.args[param]
        fwd = _FORWARD_RE.fullmatch(v)
        if fwd:
            if not c.helper:
                return None
            sub = _param_values(c.helper, fwd.group(1), calls_by_name, seen)
            if sub is None:
                return None
            out |= sub
        elif _LITERAL_RE.fullmatch(v):
            out.add(v)
        else:
            return None
    return out


def _name_pattern(name: str) -> re.Pattern | None:
    literal = PARAM_RE.split(name)[::2]
    if not "".join(literal).strip("_"):
        return None
    return re.compile("^" + "[A-Za-z0-9_]+".join(re.escape(p) for p in literal) + "$")


def _dispatch_targets(call: Call, helpers, calls_by_name) -> tuple[list[str], bool]:
    """(targets, resolved). Resolved targets are literal expansions; otherwise
    every defined helper the name's pattern matches, bar the dispatcher's own
    definition."""
    params = sorted(set(PARAM_RE.findall(call.name)))
    values: dict[str, list[str]] = {}
    if call.helper:
        for p in params:
            vals = _param_values(call.helper, p, calls_by_name, set())
            if vals is None:
                break
            values[p] = sorted(vals)
    if call.helper and len(values) == len(params):
        targets = []
        for combo in itertools.product(*(values[p] for p in params)):
            sub = dict(zip(params, combo))
            targets.append(PARAM_RE.sub(lambda m: sub[m.group(1)], call.name))
        return targets, True
    pattern = _name_pattern(call.name)
    if pattern is None:
        return [], False
    return sorted(n for n in helpers if pattern.match(n) and n != call.helper), False


def _resolve_dispatchers(calls: list[Call], helpers) -> dict[int, tuple[list[str], bool]]:
    """{id(call): (targets, resolved)} for every dispatcher call.

    Two passes: a dispatcher reached only through another dispatcher (the tax
    bill's `te_tax_dr_relief_$DIR$` reaching `te_tax_dr_relief_0`..`_3`) has
    no literal call site, so the first pass counts dispatcher calls at every
    pattern match, and the second at the targets the first could resolve."""
    direct: dict[str, list[Call]] = {}
    dispatch = [c for c in calls if "$" in c.name]
    for c in calls:
        if "$" not in c.name:
            direct.setdefault(c.name, []).append(c)

    def attribute(targets_of) -> dict[str, list[Call]]:
        out = {k: list(v) for k, v in direct.items()}
        for c in dispatch:
            for t in targets_of(c):
                out.setdefault(t, []).append(c)
        return out

    by_pattern = attribute(lambda c: _dispatch_targets(c, helpers, {})[0])
    first = {id(c): _dispatch_targets(c, helpers, by_pattern) for c in dispatch}
    calls_by_name = attribute(lambda c: first[id(c)][0])
    return {id(c): _dispatch_targets(c, helpers, calls_by_name) for c in dispatch}


def audit(mod_state=None, mod_path: str | None = None,
          vanilla_game: str | None | bool = True) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract. `vanilla_game`:
    True finds the game files (`vanilla_game_dir()`), a path uses that tree,
    and None / False checks mod callees only."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    if vanilla_game is True:
        vanilla_game = vanilla_game_dir()
    vanilla_game = vanilla_game or None

    helpers = load_helpers(mod_path, vanilla_game)
    result = AuditResult(helpers_indexed=len(helpers), vanilla_indexed=vanilla_game is not None,
                         helpers=helpers)

    scans: list[_FileScan] = []
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
                text = read_script(abs_p)
                if text is None:
                    continue
                scans.append(scan_text(text, os.path.relpath(abs_p, mod_path).replace("\\", "/"), helpers))
                result.files_audited += 1

    dispatched = _resolve_dispatchers([c for s in scans for c in s.calls], helpers)

    for s in scans:
        used: set[int] = set()
        for c in s.calls:
            result.calls_checked += 1
            if "$" not in c.name:
                result.call_sites.setdefault(c.name, []).append(c)
                found = [_check(c, c.name, helpers[c.name])]
            else:
                targets, resolved = dispatched[id(c)]
                found = []
                for t in targets:
                    if t in helpers:
                        result.call_sites.setdefault(t, []).append(c)
                        found.append(_check(c, t, helpers[t]))
                    elif resolved:
                        family = _name_pattern(c.name)
                        if family and any(family.match(n) for n in helpers):
                            found.append(Flag(c.file, c.line, c.name, t, target_missing=True))
            for f in found:
                if f is None:
                    continue
                f.exemption = s.tags.get(f.line)
                if f.exemption:
                    used.add(f.line)
                result.flags.append(f)
        for line in sorted(s.tags):
            if line in used:
                continue
            if not result.vanilla_indexed and s.unindexed.get(line):
                continue
            result.stale_tags.append(StaleTag(s.file, line))

    result.flags.sort(key=lambda f: (f.file, f.line, f.callee))
    result.stale_tags.sort(key=lambda t: (t.file, t.line))
    return result


def helper_callers(result: AuditResult, name: str) -> dict | None:
    """GET /script-args/<helper>: the helper's `$X$` names and every call that
    reaches it, with what each passes that the helper never names (`unknown`)
    and what it names that the call doesn't pass (`missing`). None when no
    indexed scripted effect or trigger has that name."""
    defs = result.helpers.get(name)
    if not defs:
        return None
    callers = []
    for c in result.call_sites.get(name, []):
        unknown, missing, _no_params = _best_signature(c, defs)
        callers.append({
            "file": c.file, "line": c.line, "call": c.name, "form": c.form,
            "args": sorted(c.args), "unknown": unknown, "missing": missing,
        })
    return {
        "helper": name,
        "definitions": [
            {"kind": d.kind, "origin": d.origin, "file": d.file, "line": d.line,
             "params": sorted(d.params)}
            for d in defs
        ],
        "params": sorted(set().union(*(d.params for d in defs))),
        "vanilla_indexed": result.vanilla_indexed,
        "callers": callers,
    }


def flag_dict(f: Flag) -> dict:
    return {
        "file": f.file, "line": f.line, "call": f.call, "callee": f.callee,
        "unknown": f.unknown, "missing": f.missing,
        "no_params_block": f.no_params_block, "target_missing": f.target_missing,
        "description": describe(f), "reviewed": f.exemption,
    }


def describe(f: Flag) -> str:
    via = f" → `{f.callee}`" if f.callee != f.call else ""
    head = f"`{f.call}`{via}"
    if f.target_missing:
        return f"{head}: no scripted effect or trigger has this name"
    parts = []
    if f.no_params_block:
        parts.append(f"called with arguments ({', '.join(f.unknown)}) but names no `$X$`")
    elif f.unknown:
        parts.append(f"passes {', '.join(f.unknown)}, which the callee never names")
    if f.missing:
        parts.append(f"doesn't pass {', '.join(f.missing)}, which the callee names")
    return f"{head}: " + "; ".join(parts)


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Script argument audit report",
        "",
        "Auto-generated by `script_argument_audit.py` on every `POST /reload` of",
        "the mod state server. Do not hand-edit.",
        "",
        "Flagged: a call to a scripted effect or trigger that passes an argument",
        "the callee's body never names (`Compiling source for <callee> failed for",
        "unknown arguments`; for a callee with no `$X$`, `should have no",
        "arguments`), or doesn't pass a `$X$` the body names (`failed for missing",
        "arguments`). A dispatcher call (`helper_$KIND$ = { ... }`) is checked",
        "against each helper it can reach. Vanilla callees are checked only when",
        "the game files are on disk.",
        "",
        "Fix: drop the argument at the call, or, where a uniform dispatcher must",
        "pass it, name it in the callee where it never runs",
        "(`trigger_if = { limit = { always = no } $TARGET$ >= $ARG$ }`).",
        "",
        "Suppress a deliberate case on the call's line:",
        "`# REVIEWED YYYY-MM-DD (script_argument): why`",
        "",
        "## Unreviewed flags",
        "",
    ]
    if not unrev:
        out += ["_None._", ""]
    else:
        by_file: dict[str, list[Flag]] = {}
        for f in unrev:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            out += [f"### `{fname}`", ""]
            out += [f"- line {f.line}: {describe(f)}" for f in by_file[fname]]
            out.append("")

    if result.stale_tags:
        out += ["## Stale tags", "", "Tags that suppress nothing; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` ({CHECK})" for t in result.stale_tags]
        out.append("")

    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        # No line number on a reviewed entry: an edit above it would otherwise
        # churn the report.
        out += [
            f"- `{f.file}` — {describe(f)} — **{f.exemption['date']}**: {f.exemption['rationale']}"
            for f in exemp
        ]
        out.append("")

    # Flag counts only: the file, call and helper counts stay on the result
    # (and in the regenerate() summary) but move with unrelated mod content.
    out += [
        "## Coverage",
        "",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        f"- stale tags: {len(result.stale_tags)}",
        "",
    ]
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    out_path = os.path.join(mod_path, "docs", "engine", "script_argument_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        # Flags without a tag, plus tags that suppress nothing.
        "unreviewed": result.failing,
        "total_flags": len(result.flags),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "stale_tags": len(result.stale_tags),
        "files_audited": result.files_audited,
        "calls_checked": result.calls_checked,
        "helpers_indexed": result.helpers_indexed,
        "vanilla_indexed": result.vanilla_indexed,
        "path": out_path,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    res = audit(mod_path=mod_path)
    print(render_report(res))
    if not res.vanilla_indexed:
        print("(no vanilla game files: calls to vanilla helpers were not checked)", file=sys.stderr)
    # --strict: CI mode. Exit 1 if any flag lacks its check-tagged
    # `# REVIEWED` comment, or any such tag suppresses nothing.
    if "--strict" in sys.argv:
        raise SystemExit(1 if res.failing else 0)
