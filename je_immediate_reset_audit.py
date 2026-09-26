"""Audit for a journal entry's `immediate` that resets state it should keep.

A journal entry's `immediate` does not run once per game. It runs whenever a
record of the entry starts:

- **re-activation** — an entry with `can_deactivate = yes` whose `possible`
  failed and later holds again;
- **revolution, inherited** — every entry a victorious revolution inherits
  (`can_revolution_inherit` unset or `yes`) is a new record, and its
  `immediate` runs again *after* the loser's variables are merged in;
- **revolution, not inherited** — with `can_revolution_inherit = no` the
  winner gets a fresh inactive record, which activates while `possible`
  holds and runs `immediate` then, also after the merge.

So an unguarded `set_variable = { name = x value = 0 }` there silently
resets whatever the player had built up in `x`. The engine logs nothing.
Found in the German-revolution saves of 2026-09-25: `je_banking_cycle` reset
`finance_cycle_value` from 6.6 (a deep panic) to 50, `je_civil_rights` wiped
its path counters, `je_space_race_<m>` resets its milestone's funding, and
`je_nuclear_program` once deleted a whole arsenal on re-activation.
Documented in `scripting_best_practices.md`: the "`immediate` runs again on
every activation" bullet and § "What a Civil War's Winner Inherits".

What is flagged
---------------
In every mod journal entry's `immediate` and `immediate_all_involved`
(including a mod `INJECT:` / `REPLACE:` of a vanilla entry; vanilla itself
is not scanned): a write that is not idempotent on existing state —
`set_variable` to anything but `yes`, `change_variable`, `remove_variable`,
`clear_variable_list`, `clear_variable_map`, and their `_global_` forms. A
timed set (`days = N`) re-arms its timer, so it counts even with no value.

The walk follows `if` / `else` / `random_list` / `while` / `custom_tooltip` /
`hidden_effect` / scope changes, and the mod's scripted effects (with
`$PARAM$` substituted), so a reset inside a helper the `immediate` calls is
reported at the helper's line, with the call chain. It skips what does not
run as an effect: `limit`, `trigger`, `show_as_tooltip`, `ai_chance`,
`modifier`, `trigger_event`.

Not flagged:

- **Guarded writes.** The write can only run while its variable is missing:
  an enclosing `limit` (of an `if`, `else_if`, `while` or iterator) has
  `NOT = { has_variable = x }` as a top-level condition, or `has_variable = x`
  inside a `NOR`; or the write is in the `else` / `else_if` of an `if` whose
  whole limit is `has_variable = x`. A multi-child `NOT` is not read as a
  guard. A **positive** `has_variable = x` is not a guard either: "remove it
  if it is there" still destroys what is there. Globals use
  `has_global_variable`, lists `has_variable_list`, maps `has_variable_map`.
  Guards match by name only; the guard's scope and the write's are not
  compared.
- **Flag sets.** `set_variable = x` and `value = yes` can only ever write
  `yes`, so running one again loses nothing.

Listed in the report, not failing:

- **Progress-bar inputs** (`progress_bar`). A variable the entry's
  `current_value` reads with `var:`, directly or through the script values it
  names. The goal is frozen at activation as `current_value +
  goal_add_value`, so carrying the old progress into a new record inflates
  the goal and the bar reads negative when it next wraps: resetting it is
  the documented rule. On an inheritable entry it still costs the player the
  progress, which the listing lets a reader weigh.
- **Pulse refreshes** (`pulse_refresh`). A write inside a scripted effect,
  called with the same parameters, that some mod journal entry's
  `on_weekly_pulse` / `on_monthly_pulse` / `on_yearly_pulse` runs *every
  time it fires* — reached with no `if`, `while`, `random`, iterator or
  `limit` on the way. Running it once more at activation does what the next
  pulse does anyway: display caches and status codes
  (`colonial_empire_refresh_display`, `sr_set_milestone_status_base`). An
  accumulator the pulse also ticks gets one extra tick. A refresh the pulse
  runs only conditionally is not proven, and needs a REVIEWED comment.
- **Guarded by another variable** (`other_guard`, a warning). The write
  runs only while a *different* variable is missing — a group initialised
  behind one sentinel (`NOT = { has_variable = ch_total }` around the sets
  of `ch_art`, `ch_sol`, ...). It resets only if the sentinel was removed
  while the variable was kept.

Each finding names its entry, the entry's `can_revolution_inherit` (`yes`,
`no`, or unset, which the engine treats as `yes`; `transferable = yes`
blocks inheritance whatever it says) and its `can_deactivate` (unset means
`no`), so the report can be read by path.

Fix: create the variable only if it is missing —
`if = { limit = { NOT = { has_variable = x } } set_variable = { ... } }`.
Keep a reset only when the old value is wrong for the new record, e.g. a
tracker of a modifier the new record does not have, and say so.

Suppress a deliberate reset with a trailing `# REVIEWED YYYY-MM-DD: rationale`
comment on any line of the write (`set_variable = {` through its closing
brace); on the opener line of the innermost `if` / `else_if` / `else` /
`random_list` / `random` around it; or on any call line on the way to it —
the `immediate`'s own `some_effect = yes` covers everything that effect
does. A comment inside a shared scripted effect covers every entry that
reaches it. Iterator opener lines are not read: `iterator_limit_audit`
reads `# REVIEWED` there. There is no stale-comment check, as in
`container_timed_variable_audit`: the untagged comment is shared with other
line-anchored audits, so one this audit no longer needs may be another's.

Blind spots: events fired from `immediate` (`trigger_event`) are not
followed; `set_bar_progress` is not a write here — the saves show an
inherited entry keeps the loser's scripted-bar values; a vanilla scripted
effect is opaque; a pulse on an on_action (rather than on a journal entry)
does not make a refresh.

Report: docs/engine/je_immediate_reset_report.md. Registered in
POST_LOAD_AUDITS; `--strict` fails on an unreviewed `unguarded` flag.
"""
import glob
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from iterator_limit_audit import blank_comments_and_strings
from prev_scope_audit import _is_scope_change, _parse_reviewed, load_links

JE_DIR = os.path.join("common", "journal_entries")
EFFECTS_DIR = os.path.join("common", "scripted_effects")
SCRIPT_VALUES_DIR = os.path.join("common", "script_values")
REPORT = os.path.join("docs", "engine", "je_immediate_reset_report.md")

IMMEDIATE_KEYS = ("immediate", "immediate_all_involved")
PULSE_KEYS = ("on_weekly_pulse", "on_monthly_pulse", "on_yearly_pulse")
MERGE_PREFIXES = ("INJECT:", "REPLACE:", "TRY_INJECT:", "TRY_REPLACE:",
                  "INJECT_OR_CREATE:", "REPLACE_OR_CREATE:")

# Write key -> namespace. The namespace picks the trigger that guards it.
WRITE_KEYS = {
    "set_variable": "scope",
    "change_variable": "scope",
    "remove_variable": "scope",
    "clear_variable_list": "list",
    "clear_variable_map": "map",
    "set_global_variable": "global",
    "change_global_variable": "global",
    "remove_global_variable": "global",
    "clear_global_variable_list": "global_list",
    "clear_global_variable_map": "global_map",
}
SET_KEYS = {"set_variable", "set_global_variable"}
# The trigger that says "this variable exists", per namespace.
EXISTS_TRIGGERS = {
    "has_variable": "scope",
    "has_global_variable": "global",
    "has_variable_list": "list",
    "has_global_variable_list": "global_list",
    "has_variable_map": "map",
    "has_global_variable_map": "global_map",
}
TIME_KEYS = {"days", "weeks", "months", "years"}
# Blocks that do not run as effects.
SKIP_KEYS = {
    "limit", "trigger", "show_as_tooltip", "ai_chance", "modifier",
    "trigger_event", "weight", "chance",
}
# Blocks whose opener line may carry a suppression for the writes inside.
SUPPRESS_BLOCKS = {"if", "else_if", "else", "random_list", "random"}
# Blocks whose body does not run every time their parent does.
_CONDITIONAL_BLOCKS = {"if", "else_if", "else", "while", "random", "random_list", "switch"}
_ITERATOR_PREFIXES = ("every_", "random_", "ordered_", "any_")

# Categories. Only UNGUARDED fails --strict.
UNGUARDED = "unguarded"
BAR = "progress_bar"
REFRESH = "pulse_refresh"
OTHER_GUARD = "other_guard"

_TOKEN_RE = re.compile(r'"[^"\n]*"|\{|\}|\?=|[<>!=]=|[<>=]|[^\s{}<>=!?"]+')
_OPS = {"=", "?=", "<", ">", "<=", ">=", "!=", "=="}
_VAR_READ_RE = re.compile(r"(?<![\w:])var:(\w+)")
_PARAM_RE = re.compile(r"\$(\w+)\$")


# ---------------------------------------------------------------------------
# A line-aware tree
# ---------------------------------------------------------------------------

@dataclass
class Node:
    key: str | None
    line: int
    value: str | None = None
    children: list["Node"] | None = None
    end_line: int = 0


@dataclass
class SourceFile:
    rel_path: str
    nodes: list[Node]
    comments: dict[int, str]


def parse_text(text: str) -> tuple[list[Node], dict[int, str]]:
    """Parse Paradox script into Nodes that keep their line numbers. Comments
    and string bodies are blanked first (offsets unchanged), so a brace in
    either does not count and each comment stays on its line."""
    clean, comments = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]
    toks = [(m.group(0), bisect_right(starts, m.start())) for m in _TOKEN_RE.finditer(clean)]
    pos = 0

    def block() -> list[Node]:
        nonlocal pos
        out: list[Node] = []
        while pos < len(toks):
            tok, line = toks[pos]
            if tok == "}":
                return out
            pos += 1
            if tok in _OPS:  # a stray operator
                continue
            if tok == "{":
                node = Node(None, line, children=block())
                node.end_line = toks[pos][1] if pos < len(toks) else line
                pos += 1
                out.append(node)
                continue
            if pos < len(toks) and toks[pos][0] in _OPS:
                pos += 1
                nxt = toks[pos][0] if pos < len(toks) else "}"
                if nxt == "{":
                    pos += 1
                    node = Node(tok, line, children=block())
                    node.end_line = toks[pos][1] if pos < len(toks) else line
                    pos += 1
                    out.append(node)
                elif nxt != "}":
                    out.append(Node(tok, line, value=nxt, end_line=toks[pos][1]))
                    pos += 1
                else:
                    out.append(Node(tok, line, value="", end_line=line))
            else:
                out.append(Node(None, line, value=tok, end_line=line))
        return out

    nodes: list[Node] = []
    while pos < len(toks):
        nodes.extend(block())
        pos += 1  # an unmatched top-level `}`
    return nodes, comments


def load_file(path: str, rel_path: str) -> SourceFile:
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return SourceFile(rel_path, [], {})
    nodes, comments = parse_text(text)
    return SourceFile(rel_path, nodes, comments)


def _child(node: Node, key: str) -> Node | None:
    for c in node.children or ():
        if c.key == key:
            return c
    return None


def _subst(s: str | None, params: dict[str, str]) -> str | None:
    if not s or "$" not in s:
        return s
    return _PARAM_RE.sub(lambda m: params.get(m.group(1), m.group(0)), s)


def _strings(node: Node):
    """Every key and scalar value under a node."""
    if node.key:
        yield node.key
    if node.value:
        yield node.value
    for c in node.children or ():
        yield from _strings(c)


# ---------------------------------------------------------------------------
# Journal entries
# ---------------------------------------------------------------------------

@dataclass
class JournalEntry:
    name: str
    file: str
    line: int
    mode: str  # "" or the merge prefix, e.g. "INJECT"
    inherit: str  # "yes" | "no" | "unset"
    transferable: bool
    deactivate: str  # "yes" | "no" | "unset"
    node: Node

    @property
    def inherits(self) -> bool:
        return self.inherit != "no" and not self.transferable

    def describe(self) -> str:
        inherit = {"unset": "unset (= yes)"}.get(self.inherit, self.inherit)
        if self.transferable:
            inherit += ", but `transferable = yes` blocks it"
        deact = {"unset": "unset (= no)"}.get(self.deactivate, self.deactivate)
        mode = f"; a mod `{self.mode}:` of a vanilla entry" if self.mode else ""
        return f"can_revolution_inherit: {inherit}; can_deactivate: {deact}{mode}"


def journal_entries(files: list[SourceFile]) -> list[JournalEntry]:
    out: list[JournalEntry] = []
    for sf in files:
        for node in sf.nodes:
            if not node.key or node.children is None:
                continue
            name, mode = node.key, ""
            for prefix in MERGE_PREFIXES:
                if name.startswith(prefix):
                    name, mode = name[len(prefix):], prefix[:-1]
                    break

            def scalar(key: str, node=node) -> str:
                c = _child(node, key)
                return c.value.lower() if c is not None and c.value else "unset"

            out.append(JournalEntry(
                name=name, file=sf.rel_path, line=node.line, mode=mode,
                inherit=scalar("can_revolution_inherit"),
                transferable=scalar("transferable") == "yes",
                deactivate=scalar("can_deactivate"),
                node=node,
            ))
    return out


def bar_variables(je: JournalEntry, script_values: dict[str, Node]) -> set[str]:
    """Variables the entry's `current_value` reads with `var:`, directly or
    through the script values it names, transitively."""
    cv = _child(je.node, "current_value")
    if cv is None:
        return set()
    found: set[str] = set()
    seen: set[str] = set()
    todo: list[Node] = [cv]
    while todo:
        node = todo.pop()
        for s in _strings(node):
            found.update(_VAR_READ_RE.findall(s))
            if s in script_values and s not in seen:
                seen.add(s)
                todo.append(script_values[s])
    return found


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Call:
    effect: str
    file: str
    line: int


@dataclass(frozen=True)
class Guard:
    namespace: str
    name: str
    file: str
    line: int


@dataclass(frozen=True)
class _Ctx:
    file: str
    params: tuple = ()
    chain: tuple = ()  # Calls, outermost first
    guards: tuple = ()  # Guards: variables known to be missing here
    tested: frozenset = frozenset()  # (namespace, name) tested positively
    suppress_line: tuple | None = None  # (file, line) of the innermost SUPPRESS_BLOCKS opener
    scopes: tuple = ()  # scope-change keys, outermost first
    refresh: str | None = None  # the every-pulse effect this runs inside

    @property
    def param_dict(self) -> dict[str, str]:
        return dict(self.params)


@dataclass
class Write:
    key: str
    name: str
    value: str | None
    timed: bool
    file: str
    line: int
    end_line: int
    ctx: _Ctx

    @property
    def namespace(self) -> str:
        return WRITE_KEYS[self.key]


def _is_conditional(node: Node, key: str | None) -> bool:
    """A block whose body does not run every time its parent does."""
    if key is None:
        return True  # an anonymous block, e.g. a random_list weight
    if key in _CONDITIONAL_BLOCKS or key in SKIP_KEYS or key.startswith(_ITERATOR_PREFIXES):
        return True
    return _child(node, "limit") is not None


def _limit_tests(limit: Node | None, params: dict[str, str]):
    """Read a `limit`: (missing, present, lone_present).

    missing      {(ns, name)} the body can only run without: a top-level
                 single-child `NOT = { has_variable = x }`, or a
                 `has_variable = x` inside a top-level `NOR`.
    present      {(ns, name)} tested positively anywhere in it.
    lone_present (ns, name) when the whole limit is one `has_variable = x`,
                 so a following `else` runs only while x is missing.
    """
    missing: set[tuple[str, str]] = set()
    present: set[tuple[str, str]] = set()
    if limit is None or not limit.children:
        return missing, present, None

    def exists_test(n: Node):
        ns = EXISTS_TRIGGERS.get(n.key or "")
        if ns and n.value:
            return ns, _subst(n.value, params)
        return None

    def conjuncts(children: list[Node]):
        for c in children:
            if c.key == "AND" and c.children is not None:
                yield from conjuncts(c.children)
            else:
                yield c

    def positives(n: Node):
        t = exists_test(n)
        if t:
            present.add(t)
        if n.key not in ("NOT", "NOR"):
            for c in n.children or ():
                positives(c)

    items = list(conjuncts(limit.children))
    for c in items:
        positives(c)
        if c.key == "NOT" and c.children is not None and len(c.children) == 1:
            t = exists_test(c.children[0])
            if t:
                missing.add(t)
        elif c.key == "NOR" and c.children is not None:
            for cc in c.children:
                t = exists_test(cc)
                if t:
                    missing.add(t)
    lone = exists_test(items[0]) if len(items) == 1 else None
    return missing, present, lone


class _Walker:
    def __init__(self, effects: dict[str, tuple[str, Node]], links: set[str]):
        self.effects = effects
        self.links = links

    @staticmethod
    def _call_params(call: Node, params: dict[str, str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for c in call.children or ():
            if c.key and c.value is not None:
                out[c.key] = _subst(c.value, params)
        return out

    def calls_every_pulse(self, node: Node, params: dict[str, str]) -> set[tuple]:
        """Every (effect, params) that runs each time `node` runs: called
        under it, transitively, with no conditional block on the way."""
        out: set[tuple] = set()

        def visit(n: Node, p: dict[str, str], stack: tuple):
            for c in n.children or ():
                key = _subst(c.key, p)
                if key in self.effects and key not in stack:
                    cp = self._call_params(c, p)
                    sig = (key, tuple(sorted(cp.items())))
                    if sig not in out:
                        out.add(sig)
                        visit(self.effects[key][1], cp, stack + (key,))
                    continue
                if c.children is not None and not _is_conditional(c, key):
                    visit(c, p, stack)

        visit(node, params, ())
        return out

    def writes(self, block: Node, ctx: _Ctx, refreshes: set[tuple]) -> list[Write]:
        out: list[Write] = []
        self._walk(block.children or [], ctx, refreshes, out)
        return out

    def _walk(self, children: list[Node], ctx: _Ctx, refreshes: set[tuple], out: list[Write]):
        params = ctx.param_dict
        # The `lone_present` of each limit so far in an if / else_if chain.
        chain: list = []
        for c in children:
            key = _subst(c.key, params) if c.key else None
            if key not in ("else_if", "else"):
                chain = []
            if key is None:
                if c.children is not None:  # an anonymous block
                    self._walk(c.children, ctx, refreshes, out)
                continue
            if key in WRITE_KEYS:
                w = self._write(c, key, ctx)
                if w is not None:
                    out.append(w)
                continue
            if key in SKIP_KEYS:
                continue
            if key in self.effects and not any(call.effect == key for call in ctx.chain):
                cp = self._call_params(c, params)
                efile, enode = self.effects[key]
                sig = (key, tuple(sorted(cp.items())))
                inner = _Ctx(
                    file=efile,
                    params=tuple(sorted(cp.items())),
                    chain=ctx.chain + (Call(key, ctx.file, c.line),),
                    guards=ctx.guards,
                    tested=ctx.tested,
                    suppress_line=ctx.suppress_line,
                    scopes=ctx.scopes,
                    refresh=ctx.refresh or (key if sig in refreshes else None),
                )
                self._walk(enode.children or [], inner, refreshes, out)
                continue
            if c.children is None:
                continue

            limit = _child(c, "limit")
            missing, present, lone = _limit_tests(limit, params)
            if key in ("else_if", "else"):
                missing |= {t for t in chain if t is not None}
            if key in ("if", "else_if"):
                chain.append(lone)
            guard_line = (limit or c).line
            guards = ctx.guards + tuple(
                Guard(ns, name, ctx.file, guard_line) for ns, name in sorted(missing))
            scopes = ctx.scopes + ((key,) if _is_scope_change(key, self.links) else ())
            inner = _Ctx(
                file=ctx.file,
                params=ctx.params,
                chain=ctx.chain,
                guards=guards,
                tested=ctx.tested | present,
                suppress_line=(ctx.file, c.line) if key in SUPPRESS_BLOCKS else ctx.suppress_line,
                scopes=scopes,
                refresh=ctx.refresh,
            )
            self._walk(c.children, inner, refreshes, out)

    @staticmethod
    def _write(node: Node, key: str, ctx: _Ctx) -> Write | None:
        params = ctx.param_dict
        value = None
        timed = False
        if node.children is None:
            name = _subst(node.value, params)
        else:
            name = None
            for c in node.children:
                if c.key == "name":
                    name = _subst(c.value, params)
                elif c.key == "value":
                    value = _subst(c.value, params) if c.children is None else "{ ... }"
                elif c.key in TIME_KEYS:
                    timed = True
        if key in SET_KEYS and value is None:
            value = "yes"  # `set_variable = x` is `value = yes`
        if not name or "$" in name:
            return None
        return Write(key, name, value, timed, ctx.file, node.line,
                     node.end_line or node.line, ctx)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

@dataclass
class Flag:
    je: str
    je_file: str
    je_setting: str
    inherits: bool
    category: str
    file: str
    line: int
    key: str  # set_variable, change_variable, ...
    name: str
    value: str | None
    via: list[str]  # the call chain, outermost first: "`effect` (file:line)"
    scopes: list[str]
    detail: str
    exemption: dict | None = None
    refresh: str | None = None  # the every-pulse effect, for pulse_refresh

    @property
    def where(self) -> str:
        return f"{self.file}:{self.line}"

    def describe(self) -> str:
        what = f"`{self.key}` `{self.name}`"
        if self.key in SET_KEYS and self.value is not None:
            what += f" = `{self.value}`"
        via = f" via {' -> '.join(self.via)}" if self.via else ""
        scope = f" in `{' > '.join(self.scopes)}`" if self.scopes else ""
        extra = f" — {self.detail}" if self.detail else ""
        return f"{what} at `{self.where}`{via}{scope}{extra}"


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)  # every category
    entries: list[JournalEntry] = field(default_factory=list)
    files_audited: int = 0

    def of(self, category: str) -> list[Flag]:
        return [f for f in self.flags if f.category == category]

    @property
    def unreviewed(self) -> list[Flag]:
        return [f for f in self.flags if f.category == UNGUARDED and not f.exemption]

    @property
    def exempted(self) -> list[Flag]:
        return [f for f in self.flags if f.category == UNGUARDED and f.exemption]


def _exemption(w: Write, comments: dict[str, dict[int, str]]) -> dict | None:
    lines = [(w.file, ln) for ln in range(w.line, w.end_line + 1)]
    if w.ctx.suppress_line:
        lines.append(w.ctx.suppress_line)
    lines.extend((call.file, call.line) for call in reversed(w.ctx.chain))  # nearest first
    for f, ln in lines:
        ex = _parse_reviewed(comments.get(f, {}).get(ln))
        if ex:
            return ex
    return None


def _classify(w: Write, bars: set[str]) -> tuple[str, str]:
    """(category, detail) for a write that is neither guarded nor a flag."""
    if w.namespace == "scope" and w.name in bars:
        return BAR, "the entry's `current_value` reads it"
    if w.ctx.refresh:
        return REFRESH, f"`{w.ctx.refresh}` also runs on every pulse of a journal entry"
    other = [g for g in w.ctx.guards if g.name != w.name]
    if other:
        g = other[-1]
        return OTHER_GUARD, f"runs only while `{g.name}` is missing (`{g.file}:{g.line}`)"
    notes = []
    if (w.namespace, w.name) in w.ctx.tested:
        notes.append(f"only a positive existence test of `{w.name}` encloses it, "
                     "so it destroys what is there")
    if w.timed:
        notes.append("a timed set re-arms its timer")
    return UNGUARDED, "; ".join(notes)


def evaluate(je_files: list[SourceFile], effect_files: list[SourceFile],
             sv_files: list[SourceFile], links: set[str]) -> AuditResult:
    effects: dict[str, tuple[str, Node]] = {}
    for sf in effect_files:
        for node in sf.nodes:
            if node.key and node.children is not None:
                effects.setdefault(node.key, (sf.rel_path, node))
    script_values: dict[str, Node] = {}
    for sf in sv_files:
        for node in sf.nodes:
            if node.key:
                script_values.setdefault(node.key, node)
    comments = {sf.rel_path: sf.comments for sf in je_files + effect_files}

    walker = _Walker(effects, links)
    result = AuditResult(files_audited=len(je_files), entries=journal_entries(je_files))

    # Effects some mod entry's pulse runs every time it fires.
    refreshes: set[tuple] = set()
    for je in result.entries:
        for pk in PULSE_KEYS:
            pulse = _child(je.node, pk)
            if pulse is not None:
                refreshes |= walker.calls_every_pulse(pulse, {})

    for je in result.entries:
        bars = bar_variables(je, script_values)
        seen: set[tuple] = set()
        for ik in IMMEDIATE_KEYS:
            block = _child(je.node, ik)
            if block is None or block.children is None:
                continue
            for w in walker.writes(block, _Ctx(file=je.file), refreshes):
                if w.key in SET_KEYS and w.value == "yes" and not w.timed:
                    continue  # a flag: idempotent
                if any(g.namespace == w.namespace and g.name == w.name for g in w.ctx.guards):
                    continue  # guarded
                if (w.file, w.line, w.name) in seen:
                    continue
                seen.add((w.file, w.line, w.name))
                category, detail = _classify(w, bars)
                result.flags.append(Flag(
                    je=je.name, je_file=je.file, je_setting=je.describe(),
                    inherits=je.inherits, category=category,
                    file=w.file, line=w.line, key=w.key, name=w.name, value=w.value,
                    via=[f"`{c.effect}` ({c.file}:{c.line})" for c in w.ctx.chain],
                    scopes=list(w.ctx.scopes), detail=detail,
                    exemption=_exemption(w, comments),
                    refresh=w.ctx.refresh if category == REFRESH else None,
                ))
    return result


def _load_dir(mod_path: str, rel_dir: str) -> list[SourceFile]:
    return [
        load_file(p, os.path.relpath(p, mod_path))
        for p in sorted(glob.glob(os.path.join(mod_path, rel_dir, "*.txt")))
    ]


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    return evaluate(
        _load_dir(mod_path, JE_DIR),
        _load_dir(mod_path, EFFECTS_DIR),
        _load_dir(mod_path, SCRIPT_VALUES_DIR),
        load_links(mod_path),
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _by_entry(flags: list[Flag], out: list[str]) -> None:
    if not flags:
        out.extend(["_None._", ""])
        return
    groups: dict[tuple, list[Flag]] = {}
    for f in flags:
        groups.setdefault((f.je_file, f.je, f.je_setting), []).append(f)
    for je_file, je, setting in sorted(groups):
        out.extend([f"### `{je}` (`{je_file}`)", "", setting, ""])
        for f in groups[(je_file, je, setting)]:
            out.append(f"- {f.describe()}")
        out.append("")


def _flat(flags: list[Flag], out: list[str]) -> None:
    if not flags:
        out.extend(["_None._", ""])
        return
    # One line per entry and variable: its first write, and how many more.
    groups: dict[tuple, list[Flag]] = {}
    for f in sorted(flags, key=lambda f: (f.je_file, f.je, f.file, f.line, f.name)):
        groups.setdefault((f.je_file, f.je, f.name), []).append(f)
    for fs in groups.values():
        f = fs[0]
        inherited = "inherited" if f.inherits else "not inherited"
        more = f" (+{len(fs) - 1} more writes)" if len(fs) > 1 else ""
        out.append(f"- `{f.je}` ({inherited}): {f.describe()}{more}")
    out.append("")


def _exemption_summary(flags: list[Flag], out: list[str]) -> None:
    """One line per entry and REVIEWED comment: a comment on a call line or
    a shared `if` can cover dozens of writes."""
    if not flags:
        out.extend(["_None._", ""])
        return
    groups: dict[tuple, list[Flag]] = {}
    for f in flags:
        key = (f.je_file, f.je, f.je_setting, f.exemption["date"], f.exemption["rationale"])
        groups.setdefault(key, []).append(f)
    by_entry: dict[tuple, list[tuple]] = {}
    for key in groups:
        by_entry.setdefault(key[:3], []).append(key)
    for je_file, je, setting in sorted(by_entry):
        out.extend([f"### `{je}` (`{je_file}`)", "", setting, ""])
        for key in by_entry[(je_file, je, setting)]:
            fs = groups[key]
            if len(fs) == 1:
                out.append(f"- {fs[0].describe()} — **{key[3]}**: {key[4]}")
                continue
            names = list(dict.fromkeys(f.name for f in fs))
            shown = ", ".join(f"`{n}`" for n in names[:6])
            more = f", +{len(names) - 6} more" if len(names) > 6 else ""
            out.append(f"- {len(fs)} writes of {shown}{more}, first at `{fs[0].where}` "
                       f"— **{key[3]}**: {key[4]}")
        out.append("")


def _refresh_summary(flags: list[Flag], out: list[str]) -> None:
    if not flags:
        out.extend(["_None._", ""])
        return
    groups: dict[tuple, list[str]] = {}
    for f in flags:
        names = groups.setdefault((f.je_file, f.je, f.inherits, f.refresh), [])
        if f.name not in names:
            names.append(f.name)
    for (_, je, inherits, effect), names in sorted(groups.items()):
        inherited = "inherited" if inherits else "not inherited"
        shown = ", ".join(f"`{n}`" for n in names[:6])
        more = f", +{len(names) - 6} more" if len(names) > 6 else ""
        out.append(f"- `{je}` ({inherited}): `{effect}` — {len(names)} variables: {shown}{more}")
    out.append("")


def render_report(result: AuditResult) -> str:
    unrev = result.unreviewed
    exemp = result.exempted
    out = [
        "# Journal-entry immediate reset audit report",
        "",
        "Auto-generated by `je_immediate_reset_audit.py` on every",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "A journal entry's `immediate` runs again whenever a record of it",
        "starts: on a re-activation (`can_deactivate = yes`), on every entry a",
        "revolution's winner inherits, and on the fresh record a",
        "`can_revolution_inherit = no` entry gets — the last two after the",
        "loser's variables are merged in. Flagged: a write there that is not",
        "idempotent (`set_variable` to anything but `yes`, `change_variable`,",
        "`remove_variable`, a list or map clear), reached from the `immediate`",
        "directly or through the mod's scripted effects, and not guarded by",
        "`NOT = { has_variable = <that variable> }`. It silently resets what",
        "the player built up. No engine diagnostic.",
        "",
        "Fix: create the variable only if it is missing. Suppress a deliberate",
        "reset with a trailing `# REVIEWED YYYY-MM-DD: why` on the write, on",
        "the innermost `if` / `else_if` / `else` / `random_list` / `random`",
        "line around it, or on a call line leading to it.",
        "",
        "## Unreviewed Flags",
        "",
    ]
    _by_entry(unrev, out)
    out.extend(["## Reviewed Exemptions", ""])
    _exemption_summary(exemp, out)

    out.extend([
        "## Not Failing",
        "",
        "### Progress-bar inputs",
        "",
        "The entry's `current_value` reads these. Its goal is frozen at",
        "activation as `current_value + goal_add_value`, so they are reset on",
        "purpose (`scripting_best_practices.md`, \"`immediate` runs again on",
        "every activation\"). On an inherited entry the reset still costs the",
        "player the progress made.",
        "",
    ])
    _flat(result.of(BAR), out)
    out.extend([
        "### Pulse refreshes",
        "",
        "Written inside a scripted effect that a journal entry's pulse runs,",
        "with the same parameters, every time it fires: a recomputation, not a",
        "reset. One line per entry and outermost refresh effect.",
        "",
    ])
    _refresh_summary(result.of(REFRESH), out)
    out.extend([
        "### Guarded by another variable (warnings)",
        "",
        "Written only while a different variable is missing — a group",
        "initialised behind one sentinel. It resets only if the sentinel was",
        "removed while this variable was kept.",
        "",
    ])
    _flat(result.of(OTHER_GUARD), out)

    with_immediate = sum(
        1 for je in result.entries if any(_child(je.node, k) for k in IMMEDIATE_KEYS))
    out.extend([
        "## Coverage",
        "",
        f"- journal-entry files audited: {result.files_audited}",
        f"- journal entries: {len(result.entries)} ({with_immediate} with an `immediate`)",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        f"- progress-bar inputs: {len(result.of(BAR))}",
        f"- pulse refreshes: {len(result.of(REFRESH))}",
        f"- guarded by another variable: {len(result.of(OTHER_GUARD))}",
        "",
    ])
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    out_path = os.path.join(mod_path, REPORT)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        "files_audited": result.files_audited,
        "unreviewed": len(result.unreviewed),
        "exempted": len(result.exempted),
        "progress_bar_inputs": len(result.of(BAR)),
        "pulse_refreshes": len(result.of(REFRESH)),
        "other_guard_warnings": len(result.of(OTHER_GUARD)),
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    print(render_report(result))
    # --strict: CI mode. Exit 1 if any unguarded write lacks a `# REVIEWED ...`.
    if "--strict" in sys.argv:
        raise SystemExit(1 if result.unreviewed else 0)
