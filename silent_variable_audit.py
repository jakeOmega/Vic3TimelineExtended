"""Parse-time audit: event options that change a number the player can see,
without saying so.

`change_variable` and `set_variable` render nothing in an option's tooltip.
When the variable they write is one the UI displays — a journal entry's
"Command reliability", a panel's "Credibility" — the player sees the number
move after the click but was never told the option would move it. The engine
says nothing about this; the only symptom is an option whose tooltip reads as
"costs money and does nothing". `nuclear_incident.40` ("A Routine Mishap")
shipped that way: its "fix the procedure" option paid a 60-day expense for +3
command reliability, and showed only the expense.

Rule: flag an option of a visible mod event when its effects — descending into
`if` / `else` / `random_list` / scope switches and into the mod's scripted
effects (with `$PARAM$` substituted) — write a *displayed* variable outside a
tooltip. A write is covered when it sits inside `custom_tooltip = { text = …
<effects> }` / `custom_description`, inside `hidden_effect`, or in a block
(or under a block) that carries its own `custom_tooltip` line.

A variable is *displayed* when the mod's localization or GUI reads it:
`Var('x')` / `GetVariable('x')` (scope variables), `GetGlobalVariable('x')`
(global variables), or `ScriptValue('sv')` where the named script value reads
`var:x` / `global_var:x`, through any script values it names in turn.

Known blind spots — it is a ranking heuristic, not a verdict:
- **Any sibling `custom_tooltip` counts as cover**, even one that describes
  something else. `nuclear_incident.10.e` had "more pressure, more danger"
  beside a silent credibility +5 and passed. Space-race options pair
  `SR_PROGRESS_ADD_5_TT` with the write it describes, which is the case the
  lenient rule exists for.
- **Displayed means mod loc or GUI.** A variable shown only through a
  customizable localization, a progress bar or a `HasVariable` toggle is not
  tracked.
- **Options only.** `immediate`, `after`, buttons and decisions are out of
  scope: an event's `immediate` is not shown as a choice, and buttons have
  their own tooltip conventions.
- **Mod events only**, plain `<id> = {` definitions; console-only
  `te_debug_*` harness files are skipped, as are `hidden = yes` events.

Suppression is check-tagged, on its own line anywhere inside the option:

    # REVIEWED 2026-09-25 (silent_variable): the JE tooltip explains this drift

An untagged `# REVIEWED YYYY-MM-DD:` comment elsewhere in the event is read by
other audits and does not count here. A tag on an option that is no longer
flagged is stale and fails `--strict` until it is removed.

Report: docs/engine/silent_variable_report.md. Registered in POST_LOAD_AUDITS.
"""

import glob
import os
import re
from dataclasses import dataclass, field

from paradox_file_parser import ParadoxFileParser

CHECK = "silent_variable"

_DEF_RE = re.compile(r"^[ \t]*([a-z_][a-z0-9_]*\.\d+)[ \t]*=[ \t]*\{", re.M)
_HIDDEN_RE = re.compile(r"^[ \t]*hidden[ \t]*=[ \t]*yes\b", re.M)
_OPTION_RE = re.compile(r"(?<![\w.:])option[ \t]*=[ \t]*\{")
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$",
    re.M,
)
_CONSOLE_FILE_RE = re.compile(r"^te_debug_")

# What the UI reads.
_SCOPE_VAR_READ_RE = re.compile(r"(?:\bVar|\bGetVariable)\(\s*['\"](\w+)['\"]")
_GLOBAL_VAR_READ_RE = re.compile(r"\bGetGlobalVariable\(\s*['\"](\w+)['\"]")
_SCRIPT_VALUE_READ_RE = re.compile(r"ScriptValue\(\s*['\"](\w+)['\"]")
# What a script value reads. `global_var:x` must not also count as `var:x`.
_SV_SCOPE_VAR_RE = re.compile(r"(?<!\w)var:(\w+)")
_SV_GLOBAL_VAR_RE = re.compile(r"(?<!\w)global_var:(\w+)")

_WRITE_KEYS = {
    "change_variable": "scope",
    "set_variable": "scope",
    "change_global_variable": "global",
    "set_global_variable": "global",
}
# Blocks whose inner effects are described by their own text.
_TOOLTIP_KEYS = {"custom_tooltip", "custom_description"}
# Blocks that are not shown, not executed, or not effects.
_SKIP_KEYS = {
    "hidden_effect", "show_as_tooltip", "trigger", "limit", "ai_chance",
    "modifier", "name", "trigger_event",
}


def _pairs(obj):
    """(key, value) pairs of a parsed block: a dict when its keys are unique,
    a list of single-key dicts when a key repeats."""
    if isinstance(obj, dict):
        yield from obj.items()
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                yield from item.items()


def _val(v):
    return v[1] if isinstance(v, tuple) else v


def _subst(s, params: dict[str, str]):
    if not isinstance(s, str) or "$" not in s:
        return s
    for k, v in params.items():
        s = s.replace(f"${k}$", v)
    return s


def _parse_text(parser: ParadoxFileParser, text: str):
    return parser.parse_object(parser.tokenize("{" + text + "}"))[0]


@dataclass
class Write:
    variable: str
    kind: str  # "scope" | "global"
    via: str | None  # the scripted effect the write sits in, if any


@dataclass
class OptionFlag:
    event_id: str
    option: str
    file: str
    line: int
    writes: list[Write]
    exemption: dict | None = None


@dataclass
class StaleTag:
    event_id: str
    option: str
    file: str
    line: int


@dataclass
class AuditResult:
    flags: list[OptionFlag] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)

    @property
    def failing(self) -> int:
        return sum(1 for f in self.flags if not f.exemption) + len(self.stale_tags)


# ---------------------------------------------------------------------------
# What the UI displays
# ---------------------------------------------------------------------------

def _read_all(paths) -> str:
    chunks = []
    for p in paths:
        try:
            with open(p, encoding="utf-8-sig", errors="replace") as fh:
                chunks.append(fh.read())
        except OSError:
            continue
    return "\n".join(chunks)


def _load_blocks(parser, paths, unparsed: list[str]) -> dict:
    out = {}
    for p in paths:
        try:
            with open(p, encoding="utf-8-sig", errors="replace") as fh:
                tree = _parse_text(parser, fh.read())
        except Exception:  # noqa: BLE001 — a file the parser rejects is reported, not fatal
            unparsed.append(p)
            continue
        for k, v in _pairs(tree):
            out.setdefault(k, _val(v))
    return out


def displayed_variables(mod_path: str, parser: ParadoxFileParser, unparsed: list[str]):
    """Return (scope_vars, global_vars) that mod loc or GUI displays."""
    shown = _read_all(
        sorted(glob.glob(os.path.join(mod_path, "localization", "**", "*.yml"), recursive=True))
        + sorted(glob.glob(os.path.join(mod_path, "gui", "**", "*.gui"), recursive=True))
    )
    scope_vars = set(_SCOPE_VAR_READ_RE.findall(shown))
    global_vars = set(_GLOBAL_VAR_READ_RE.findall(shown))
    sv_refs = set(_SCRIPT_VALUE_READ_RE.findall(shown))

    svs = _load_blocks(
        parser,
        sorted(glob.glob(os.path.join(mod_path, "common", "script_values", "*.txt"))),
        unparsed,
    )
    memo: dict[str, tuple[set, set]] = {}

    def resolve(name: str, stack: frozenset) -> tuple[set, set]:
        if name in memo:
            return memo[name]
        if name in stack or name not in svs:
            return set(), set()
        sv_scope: set[str] = set()
        sv_global: set[str] = set()
        inner = stack | {name}

        def scan(s: str):
            sv_scope.update(_SV_SCOPE_VAR_RE.findall(s))
            sv_global.update(_SV_GLOBAL_VAR_RE.findall(s))
            if s in svs and s != name:
                a, b = resolve(s, inner)
                sv_scope.update(a)
                sv_global.update(b)

        def walk(o):
            if isinstance(o, str):
                scan(o)
            elif isinstance(o, tuple):
                walk(o[1])
            else:
                for k, v in _pairs(o):
                    scan(k)
                    walk(v)

        walk(svs[name])
        memo[name] = (sv_scope, sv_global)
        return memo[name]

    for ref in sv_refs:
        a, b = resolve(ref, frozenset())
        scope_vars |= a
        global_vars |= b
    return scope_vars, global_vars


# ---------------------------------------------------------------------------
# What an option writes
# ---------------------------------------------------------------------------

class _Walker:
    def __init__(self, effects: dict):
        self.effects = effects

    def silent_writes(self, block) -> list[Write]:
        out: list[Write] = []
        self._walk(block, False, {}, (), None, out)
        return out

    def _walk(self, block, covered, params, stack, via, out):
        items = list(_pairs(block))
        cov = covered or any(k in _TOOLTIP_KEYS for k, _ in items)
        for key, raw in items:
            body = _val(raw)
            if key in _TOOLTIP_KEYS or key in _SKIP_KEYS:
                continue
            kind = _WRITE_KEYS.get(key)
            if kind:
                if not cov:
                    name = self._write_name(body, params)
                    if name and "$" not in name:
                        out.append(Write(name, kind, via))
                continue
            called = _subst(key, params)
            if called in self.effects and called not in stack:
                call_params = {}
                for pk, pv in _pairs(body) if isinstance(body, (dict, list)) else ():
                    pv = _val(pv)
                    if isinstance(pv, str):
                        call_params[pk] = _subst(pv, params)
                self._walk(self.effects[called], cov, call_params, stack + (called,),
                           via or called, out)
                continue
            if isinstance(body, (dict, list)):
                self._walk(body, cov, params, stack, via, out)

    @staticmethod
    def _write_name(body, params):
        if isinstance(body, str):
            return _subst(body, params)
        for k, v in _pairs(body):
            if k == "name":
                return _subst(_val(v), params)
        return None


def _match_block(text: str, brace_pos: int) -> int:
    """Index just past the `}` matching the `{` at brace_pos. Comments are
    already blanked by the caller, so braces inside them do not count."""
    depth = 0
    for i in range(brace_pos, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def _blank_comments(text: str) -> str:
    """Replace every `# …` comment (outside a quoted string) with spaces, so
    offsets and line numbers still line up with the original text."""
    out = []
    for line in text.split("\n"):
        in_str = False
        cut = len(line)
        for i, ch in enumerate(line):
            if ch == '"':
                in_str = not in_str
            elif ch == "#" and not in_str:
                cut = i
                break
        out.append(line[:cut] + " " * (len(line) - cut))
    return "\n".join(out)


def _top_level_options(code: str, start: int, end: int):
    """(offset of `option`, offset of its `{`, end offset) for each option
    directly inside the event block code[start:end]."""
    depth = 0
    i = start
    while i < end:
        c = code[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 1 and c == "o":
            m = _OPTION_RE.match(code, i)
            if m and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] in "_.:")):
                brace = m.end() - 1
                close = _match_block(code, brace)
                yield i, brace, close
                i = close
                continue
        i += 1


def _option_name(parsed) -> str:
    for k, v in _pairs(parsed):
        if k == "name":
            body = _val(v)
            if isinstance(body, str):
                return body
            for kk, vv in _pairs(body):
                if kk == "text":
                    return _val(vv)
    return "?"


def audit(mod_path: str) -> AuditResult:
    parser = ParadoxFileParser()
    unparsed: list[str] = []
    scope_vars, global_vars = displayed_variables(mod_path, parser, unparsed)
    effects = _load_blocks(
        parser,
        sorted(glob.glob(os.path.join(mod_path, "common", "scripted_effects", "*.txt"))),
        unparsed,
    )
    walker = _Walker(effects)

    flags: list[OptionFlag] = []
    stale: list[StaleTag] = []
    options_seen = 0
    events_seen = 0
    events_dir = os.path.join(mod_path, "events")
    for path in sorted(glob.glob(os.path.join(events_dir, "**", "*.txt"), recursive=True)):
        if _CONSOLE_FILE_RE.match(os.path.basename(path)):
            continue
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        code = _blank_comments(text)
        for m in _DEF_RE.finditer(code):
            eid = m.group(1)
            brace = code.index("{", m.start())
            end = _match_block(code, brace)
            if _HIDDEN_RE.search(code, brace, end):
                continue
            events_seen += 1
            for opt_start, opt_brace, opt_end in _top_level_options(code, brace, end):
                options_seen += 1
                try:
                    parsed = parser.parse_object(parser.tokenize(code[opt_brace:opt_end]))[0]
                except Exception:  # noqa: BLE001
                    unparsed.append(f"{path}:{eid}")
                    continue
                name = _option_name(parsed)
                line = text.count("\n", 0, opt_start) + 1
                tag = None
                for rm in _TAGGED_REVIEWED_RE.finditer(text, opt_brace, opt_end):
                    checks = {c.strip() for c in rm.group("checks").split(",")}
                    if CHECK in checks:
                        tag = {"date": rm.group("date"), "rationale": rm.group("rationale")}
                        break
                writes = [
                    w for w in walker.silent_writes(parsed)
                    if (w.variable in scope_vars if w.kind == "scope" else w.variable in global_vars)
                ]
                if writes:
                    seen = set()
                    uniq = []
                    for w in writes:
                        if (w.variable, w.via) not in seen:
                            seen.add((w.variable, w.via))
                            uniq.append(w)
                    flags.append(OptionFlag(eid, name, path, line, uniq, tag))
                elif tag:
                    stale.append(StaleTag(eid, name, path, line))

    flags.sort(key=lambda f: (f.file, f.line))
    stale.sort(key=lambda s: (s.file, s.line))
    return AuditResult(
        flags=flags,
        stale_tags=stale,
        coverage={
            "events_scanned": events_seen,
            "options_scanned": options_seen,
            "displayed_scope_variables": len(scope_vars),
            "displayed_global_variables": len(global_vars),
            "unparsed": unparsed,
        },
    )


def render_report(result: AuditResult, mod_path: str = "") -> str:
    unreviewed = [f for f in result.flags if not f.exemption]
    exempted = [f for f in result.flags if f.exemption]
    cov = result.coverage

    def _loc(file: str, line: int) -> str:
        rel = os.path.relpath(file, mod_path) if mod_path else file
        return f"{rel}:{line}"

    def _writes(f: OptionFlag) -> str:
        parts = []
        for w in f.writes:
            label = f"`{w.variable}`" if w.kind == "scope" else f"global `{w.variable}`"
            parts.append(f"{label} (via `{w.via}`)" if w.via else label)
        return ", ".join(parts)

    out: list[str] = []
    out.append("# Silent Variable Report")
    out.append("")
    out.append(
        "Options of visible mod events that change a variable the UI displays "
        "without any tooltip saying so. `change_variable` / `set_variable` "
        "render nothing, so the player sees the number move after the click "
        "but was never told. Wrap the write in `custom_tooltip = { text = <key> "
        "<effects> }` naming the change."
    )
    out.append("")
    out.append(f"- Events scanned: **{cov.get('events_scanned', 0)}**")
    out.append(f"- Options scanned: **{cov.get('options_scanned', 0)}**")
    out.append(
        f"- Displayed variables: **{cov.get('displayed_scope_variables', 0)}** scope, "
        f"**{cov.get('displayed_global_variables', 0)}** global"
    )
    out.append(f"- Silent writes (unreviewed): **{len(unreviewed)}**")
    out.append(f"- Silent writes (REVIEWED-suppressed): **{len(exempted)}**")
    out.append(f"- Stale `({CHECK})` tags: **{len(result.stale_tags)}**")
    if cov.get("unparsed"):
        out.append(f"- Skipped (parser rejected): **{len(cov['unparsed'])}**")
    out.append("")

    if unreviewed:
        out.append("## Unreviewed")
        out.append("")
        for f in unreviewed:
            out.append(f"- `{f.event_id}` option `{f.option}` — {_loc(f.file, f.line)} — {_writes(f)}")
        out.append("")
        out.append(
            "Wrap each write in `custom_tooltip = { text = <key> … }` naming the "
            "change, or add `# REVIEWED YYYY-MM-DD (silent_variable): rationale` "
            "on its own line inside the option."
        )
        out.append("")
    else:
        out.append("No unreviewed silent writes. ✅")
        out.append("")

    if result.stale_tags:
        out.append("## Stale tags")
        out.append("")
        for s in result.stale_tags:
            out.append(f"- `{s.event_id}` option `{s.option}` — {_loc(s.file, s.line)}")
        out.append("")

    if exempted:
        out.append("## REVIEWED-suppressed")
        out.append("")
        for f in exempted:
            ex = f.exemption or {}
            out.append(
                f"- `{f.event_id}` option `{f.option}` — {_loc(f.file, f.line)} — {_writes(f)} "
                f"(REVIEWED {ex.get('date', '?')}: {ex.get('rationale', '')})"
            )
        out.append("")

    if cov.get("unparsed"):
        out.append("## Skipped")
        out.append("")
        for p in cov["unparsed"]:
            out.append(f"- {os.path.relpath(p, mod_path) if mod_path and os.path.isabs(p) else p}")
        out.append("")

    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_GENERATORS entry point. Writes the silent-variable report.

    File-based (events, scripted effects, script values, loc and GUI are read
    from disk), so `mod_state` is accepted for protocol compatibility but unused.
    """
    from path_constants import mod_path

    result = audit(mod_path)
    out_path = os.path.join(mod_path, "docs", "engine", "silent_variable_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result, mod_path))
    return {
        # Flags without a tag, plus tags that suppress nothing.
        "unreviewed": result.failing,
        "stale_tags": len(result.stale_tags),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "options_scanned": result.coverage.get("options_scanned", 0),
        "path": out_path,
    }


if __name__ == "__main__":
    import sys

    from path_constants import mod_path as _mp

    res = audit(_mp)
    print(render_report(res, _mp))
    # --strict: CI mode. Exit 1 if any flag lacks a `(silent_variable)` tag or
    # any such tag suppresses nothing.
    if "--strict" in sys.argv:
        raise SystemExit(1 if res.failing else 0)
