"""Audit for a `change_variable` on a variable that nothing ever sets first.

`change_variable` does not create a variable. On one that is not set it does
nothing and logs `change_variable effect [ Variable not of the 'value' scope
type. Type: empty ]`, every time it runs, so a counter that is only ever
changed never counts. The UN's cease-fire order kept its unbooked debit that
way (#1818): the month added one to `un_cf_debit_months`, and the only
`set_variable` of it was the reset after a booking, behind `has_variable =
un_cf_debit_months`. The debit was never booked in any game, and the only sign
was four log lines a month while an order was being fought.

What is flagged
---------------
A `change_variable`, `change_global_variable` or `change_local_variable` whose
variable has no *initialising* `set_variable` of that exact name and kind
anywhere in `common/` or `events/`, nor in vanilla's `common/` (the
`vanilla_parsed/` snapshot). A set initialises unless:

* it can only run when the variable is already set. It sits in a block whose
  `limit` has `has_variable = X` or `exists = var:X` as its own child or under
  an `AND`, or reads `var:X` there on either side of a comparison (`var:X >=
  6`: false when X is unset), with nothing but `if` / `else_if` / `while` and
  other blocks that stay on the same object between that limit and the set.
  Behind a scope change (`scope:other = { set_variable = … }`, an iterator) a
  `var` guard no longer speaks of the object being set; global and local
  guards hold at any depth;
* it is the flag form, `set_variable = x` or a block with no `value`. That
  stores a boolean, and whether `change_variable` can count on one is unknown
  (nothing in the mod relies on it), so it is not taken as a start.

Names in a scripted effect's parameter are followed to the callers, both ways.
A `set_variable = { name = $OUT$ … }` initialises the name each caller passes
(`te_set_sqrt = { … OUT = my_var }`), and a `change_variable = { name =
$COUNTER$ … }` is judged for each name a caller passes, through helpers that
pass the name on (`wrap = { helper = { OUT = $OUT$ } }`). A name a call passes
to such a change is flagged at the call.

What is not judged
------------------
* Whether the set runs *before* the change, or on the same object. A variable
  set at an object's creation and changed in its monthly pulse is the mod's
  ordinary shape, and only the name is matched: one initialising set anywhere
  clears every change of that name.
* A guard the audit cannot see in the set's own body. Only a `limit` is read.
  A reset whose guard is held by the helper's caller, sits inside a scripted
  trigger, an event's `trigger`, a button's `possible` or a `random_list`
  entry's `trigger`, is the `else` of `NOT = { has_variable = X }`, or reaches
  the object through a saved scope (`scope:me = { … }`) counts as a start.
* What a set stores. `set_variable = { name = x value = scope:y }` counts,
  whatever `scope:y` holds.
* `clamp_variable` and `round_variable`, which presumably fail the same way on
  an unset variable (not read from a log yet).
* A change whose name carries a parameter and that no caller resolves (the
  helper is never called with a plain name, or only through a call whose own
  name is a parameter). If the name is all parameter it is counted
  (`AuditResult.unjudged`); if part of it is literal (`sr_$KEY$_stock`) it is
  matched against the sets as a pattern.

What is flagged that may be sound (none in the mod today)
---------------------------------------------------------
* A variable only vanilla's *events* set: the snapshot has no events.
* A variable set only by a helper that is itself called through a name in a
  parameter (`sr_$KIND$_seed = { … }`): that call cannot be followed, so the
  name it sets is not credited.
Each takes the comment below.

Suppress an intended one with a trailing
`# REVIEWED YYYY-MM-DD (variable_init): rationale` on the flagged line: the
`change_variable` line, or the line of the call that passes the name. A tagged
comment on a line with no flag is stale and fails `--strict`.

A raw-text scan with `variable_guard_audit`'s tree, for its reasons: the parser
keeps neither line numbers nor comments. About six seconds: only the files
that write a variable are parsed (some 40% of the text), and another only when
it calls a scripted effect that sets or changes a name it is passed.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from audit_common import AuditResult as _AuditResult
from audit_common import StaleTag, cli_main, parse_reviewed, render_report as _standard_report, write_text
from blanked_text import blank_comments_and_strings
from variable_guard_audit import Node, _is_scope_change, load_scope_links, parse_tree

CHECK = "variable_init"
TITLE = "change_variable initialisation audit report"
REPORT_PATH = os.path.join("docs", "engine", "change_variable_init_report.md")
INTRO = (
    "A set does not count when it can only run with the variable already set: it sits in a block whose `limit` "
    "has `has_variable = X`, `exists = var:X` or a read of `var:X`, on the same object. The reset after a batch, "
    "`if = { limit = { var:x >= 6 } set_variable = { name = x value = 0 } }`, is the usual one. Nor does the flag "
    "form, `set_variable = x`, which stores no number. Only a `limit` in the set's own body is read: a guard held "
    "by a helper's caller, or inside a scripted trigger or an event's `trigger`, is not seen.\n\n"
    "Fix: set the variable where its owner begins (`set_variable = { name = x value = 0 }`), or just before the "
    "change: `if = { limit = { NOT = { has_variable = x } } set_variable = { name = x value = 0 } }`."
)

# Directories scanned, relative to the mod root: every scripted surface.
AUDIT_DIRS = ("common", "events")
SCRIPTED_EFFECTS_DIR = "common/scripted_effects/"
VANILLA_COMMON = os.path.join("vanilla_parsed", "common")

# effect -> the prefix its variable is read with (the kind).
SET_KEYS = {
    "set_variable": "var",
    "set_global_variable": "global_var",
    "set_local_variable": "local_var",
}
CHANGE_KEYS = {
    "change_variable": "var",
    "change_global_variable": "global_var",
    "change_local_variable": "local_var",
}
GUARD_KEYS = {
    "has_variable": "var",
    "has_global_variable": "global_var",
    "has_local_variable": "local_var",
}
_WRITE_KEYS = tuple(SET_KEYS) + tuple(CHANGE_KEYS)

# A variable read standing alone on one side of a limit's own line (`this.` is
# the current scope); `scope:x.var:y` reads another object's and is no guard.
_HEAD_READ_RE = re.compile(r"^(?:this\.)?(var|global_var|local_var):([A-Za-z0-9_$\-]+)$", re.I)
_PARAM_RE = re.compile(r"\$([A-Za-z0-9_]+)\$")
# A quoted variable name, `name = "x"` or `set_variable = "x"`. Strings are
# blanked before the scan, so these are unquoted first, length kept.
_QUOTED_NAME_RE = re.compile(
    r'(\b(?:name|(?:set|change)_(?:global_|local_)?variable)\s*=\s*)"([A-Za-z0-9_.:$\-]+)"')

# A change name that carries a `$PARAM$` and that no caller resolves is matched
# as a pattern only when this many characters of it are literal: `$KEY$` or
# `$PX$f0` would match every name.
MIN_LITERAL = 4

# A parameter name is followed through helpers that pass it on until nothing
# new is found; this only bounds a loop that should never get near it.
MAX_PASSES = 100


@dataclass
class Flag:
    file: str
    line: int  # the `change_variable` line, or the call that passes the name
    effect: str  # change_variable / change_global_variable / change_local_variable
    kind: str  # var / global_var / local_var
    name: str
    # Where the variable is set, each behind a guard of its own name.
    guarded_sets: list[tuple[str, int]] = field(default_factory=list)
    # Where it is set in the flag form only.
    flag_sets: list[tuple[str, int]] = field(default_factory=list)
    # For a name passed to a helper: (file, line, name as written) of the
    # helper's change.
    via: tuple[str, int, str] | None = None
    exemption: dict | None = None

    @property
    def message(self) -> str:
        setter = "set_" + self.effect[len("change_"):]
        guard = "has_" + self.effect[len("change_"):]
        if self.via:
            head = (f"passes `{self.name}` to the `{self.effect}` of `{self.via[2]}` at "
                    f"`{self.via[0]}:{self.via[1]}`: ")
        else:
            head = f"`{self.effect}` of `{self.name}`: "

        def shown(sites: list[tuple[str, int]]) -> str:
            text = ", ".join(f"`{f}:{ln}`" for f, ln in sites[:3])
            return text + (f" and {len(sites) - 3} more" if len(sites) > 3 else "")

        if self.guarded_sets:
            return (head + f"every `{setter}` of it sits behind a `{guard}` check or a `{self.kind}:` read of it "
                    f"({shown(self.guarded_sets)}), so nothing sets it first")
        if self.flag_sets:
            return (head + f"its only `{setter}` is the flag form ({shown(self.flag_sets)}), which stores no "
                    "number")
        return head + f"no `{setter}` of it in the mod or in vanilla's `common/`"


@dataclass
class AuditResult(_AuditResult):
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0
    judged: int = 0  # change sites matched against the sets
    unjudged: int = 0  # change sites whose name is all parameter and no caller resolves


@dataclass
class _File:
    rel: str
    tree: Node
    comments: dict


def literal_part(name: str) -> str:
    return _PARAM_RE.sub("", name)


def skeleton(name: str) -> str:
    """The name with each `$PARAM$` as one wildcard."""
    return _PARAM_RE.sub("\0", name)


def _pattern(name: str) -> re.Pattern:
    return re.compile(".+".join(re.escape(part) for part in skeleton(name).split("\0")))


def unquote_names(text: str) -> str:
    """`text` with each quoted variable name's quotes turned to spaces, so the
    name survives the blanking of strings. Offsets and lines are unchanged."""
    # Written as the formatter leaves it; the cheap test spares the other
    # files the pattern.
    if 'name = "' not in text and 'variable = "' not in text:
        return text
    return _QUOTED_NAME_RE.sub(lambda m: f"{m.group(1)} {m.group(2)} ", text)


def writes_a_variable(text: str) -> bool:
    """Whether the text names a set or a change at all (comments included)."""
    return any(key in text for key in _WRITE_KEYS)


def _written_name(child: tuple) -> str | None:
    """The variable a set or change statement names: `set_variable = x`, or
    the block's `name = x`."""
    if child[0] == "scalar":
        value = child[3]
    else:
        value = next((c[3] for c in child[1].children if c[0] == "scalar" and c[1] == "name"), None)
    if not value or value.startswith('"'):
        return None
    return value


def _stores_a_value(child: tuple) -> bool:
    """False for the flag form of a set: `set_variable = x`, or a block with
    no `value` (a bare flag, or one with only a duration)."""
    if child[0] == "scalar":
        return False
    return any(
        (c[0] == "scalar" and c[1] == "value") or (c[0] == "block" and c[1].key == "value")
        for c in child[1].children
    )


def limit_guards(node: Node) -> set[tuple[str, str]]:
    """The variables a block's `limit` proves set for the block's body."""
    guards: set[tuple[str, str]] = set()

    def read(block: Node) -> None:
        for child in block.children:
            if child[0] == "scalar":
                _, key, op, value, _line = child
                kind = GUARD_KEYS.get(key)
                if kind and op == "=" and value:
                    guards.add((kind, value))
                    continue
                # `var:x >= 6`, `5 < var:x`, `exists = var:x`: each is false
                # (or an error) while x is unset.
                sides = (key, value or "")
            elif child[0] == "block":
                sub = child[1]
                if (sub.key or "").upper() == "AND":
                    read(sub)
                    continue
                sides = (sub.key or "",)
            else:
                continue
            for side in sides:
                m = _HEAD_READ_RE.match(side)
                if m:
                    guards.add((m.group(1).lower(), m.group(2)))

    for child in node.children:
        if child[0] == "block" and child[1].key == "limit":
            read(child[1])
    return guards


class _Scan:
    """What the parsed files write: every set with whether it is guarded,
    every call that passes arguments, and every change."""

    def __init__(self, links: set[str], odd_params: frozenset[str] = frozenset()):
        self.links = links
        # Parameter names that are not all upper case, so not caught by the
        # cheap test below. The mod has none.
        self.odd_params = odd_params
        # (kind, name, guarded, file, line, owner, stores a value): `owner` is
        # the scripted effect the statement is written in, if any.
        self.sets: list[tuple[str, str, bool, str, int, str | None, bool]] = []
        # (callee, {argument: value}, guards at the call, file, line, owner).
        # Any block with an upper-case argument (`OUT = my_var`, as the mod
        # writes them), so scripted triggers too; only a callee that sets or
        # changes a name in a parameter is ever looked up.
        self.calls: list[tuple[str, dict[str, str], frozenset, str, int, str | None]] = []
        # (file, line, effect, kind, name, owner)
        self.changes: list[tuple[str, int, str, str, str, str | None]] = []

    def add(self, f: _File) -> None:
        if f.rel.startswith(SCRIPTED_EFFECTS_DIR):
            for child in f.tree.children:
                if child[0] == "block":
                    self.walk(child[1], frozenset(), f.rel, child[1].key)
        else:
            self.walk(f.tree, frozenset(), f.rel, None)

    def walk(self, node: Node, guards: frozenset, rel: str, owner: str | None) -> None:
        odd = self.odd_params
        for child in node.children:
            if child[0] == "bare":
                continue
            key = child[1] if child[0] == "scalar" else child[1].key
            line = child[4] if child[0] == "scalar" else child[1].line
            if key in SET_KEYS:
                name = _written_name(child)
                if name:
                    kind = SET_KEYS[key]
                    self.sets.append((kind, name, (kind, name) in guards, rel, line, owner,
                                      _stores_a_value(child)))
            elif key in CHANGE_KEYS:
                name = _written_name(child)
                if name:
                    self.changes.append((rel, line, key, CHANGE_KEYS[key], name, owner))
            if child[0] != "block":
                continue
            sub = child[1]
            if key:
                args = {c[1]: c[3] for c in sub.children
                        if c[0] == "scalar" and c[3] and (c[1].isupper() or c[1] in odd)}
                if args:
                    self.calls.append((key, args, guards, rel, line, owner))
            inner = guards
            if inner and _is_scope_change(key, self.links):
                # Another object: an outer `var` guard says nothing about it.
                inner = frozenset(g for g in inner if g[0] != "var")
            own = limit_guards(sub)
            if own:
                inner = inner | own
            self.walk(sub, inner, rel, owner)


def substitute(template: str, args: dict[str, str]) -> tuple[str, bool]:
    """(`template` with each `$P$` the call passes filled in, whether the call
    passes any of them). A parameter the call leaves out, or passes as a quoted
    string, stays. A helper that passes a name on under the same parameter
    (`OUT = $OUT$`) gives the template back unchanged, and has still passed it."""
    passed = False

    def fill(m: re.Match) -> str:
        nonlocal passed
        value = args.get(m.group(1))
        if value is None or value.startswith('"'):
            return m.group(0)
        passed = True
        return value

    return _PARAM_RE.sub(fill, template), passed


@dataclass
class _Resolved:
    # Names with a set that stores a value and is not behind a guard of its
    # own name; a name still carrying a `$PARAM$` is a helper's, unresolved.
    initialised: set[tuple[str, str]] = field(default_factory=set)
    guarded: dict[tuple[str, str], list[tuple[str, int]]] = field(default_factory=dict)
    flag_form: dict[tuple[str, str], list[tuple[str, int]]] = field(default_factory=dict)
    # A plain name a call passes to a helper's change:
    # (kind, name) -> {(call file, call line): (change file, line, effect, name as written)}
    reached: dict[tuple[str, str], dict[tuple[str, int], tuple[str, int, str, str]]] = field(default_factory=dict)
    # The parameter-named change sites some caller resolved to a plain name.
    resolved_changes: set[tuple[str, int]] = field(default_factory=set)
    # Scripted effects that set or change a name they are passed.
    helpers: set[str] = field(default_factory=set)


def resolve(scan: _Scan) -> _Resolved:
    """Credit every set and change a scripted effect makes of a name in a
    parameter to the name each caller passes, through helpers that pass it on."""
    out = _Resolved()
    # scripted effect -> {(kind, name with $PARAM$)} it sets unguarded.
    set_templates: dict[str, set[tuple[str, str]]] = {}
    # scripted effect -> {(kind, name with $PARAM$, where the change is written)}.
    change_templates: dict[str, set[tuple[str, str, tuple[str, int, str, str]]]] = {}
    for kind, name, is_guarded, rel, line, owner, stores in scan.sets:
        if is_guarded:
            out.guarded.setdefault((kind, name), []).append((rel, line))
        elif not stores:
            out.flag_form.setdefault((kind, name), []).append((rel, line))
        else:
            out.initialised.add((kind, name))
            if owner and "$" in name:
                set_templates.setdefault(owner, set()).add((kind, name))
    for rel, line, effect, kind, name, owner in scan.changes:
        if owner and "$" in name:
            change_templates.setdefault(owner, set()).add((kind, name, (rel, line, effect, name)))

    # Only a call of an effect that holds a template is ever read.
    calls_of: dict[str, list] = {}
    for call in scan.calls:
        calls_of.setdefault(call[0], []).append(call)
    for _ in range(MAX_PASSES):
        grew = False
        callees = [name for name in calls_of if name in set_templates or name in change_templates]
        for callee, args, guards, rel, line, owner in (call for name in callees for call in calls_of[name]):
            for kind, template in tuple(set_templates.get(callee, ())):
                name, passed = substitute(template, args)
                if not passed:
                    continue
                if (kind, name) in guards:
                    out.guarded.setdefault((kind, name), []).append((rel, line))
                    continue
                out.initialised.add((kind, name))
                if owner and "$" in name and (kind, name) not in set_templates.setdefault(owner, set()):
                    set_templates[owner].add((kind, name))
                    grew = True
            for kind, template, origin in tuple(change_templates.get(callee, ())):
                name, passed = substitute(template, args)
                if not passed:
                    continue
                if "$" not in name:
                    out.reached.setdefault((kind, name), {}).setdefault((rel, line), origin)
                    out.resolved_changes.add(origin[:2])
                elif owner and (kind, name, origin) not in change_templates.setdefault(owner, set()):
                    change_templates[owner].add((kind, name, origin))
                    grew = True
        if not grew:
            break
    out.helpers = {name for name, found in set_templates.items() if found}
    out.helpers |= {name for name, found in change_templates.items() if found}
    return out


def vanilla_sets(mod_path: str) -> set[tuple[str, str]]:
    """Every (kind, name) a `set_variable` in vanilla's `common/` names, from
    the committed snapshot. Guards are not read: a vanilla variable is
    vanilla's to initialise."""
    found: set[tuple[str, str]] = set()
    base = os.path.join(mod_path, VANILLA_COMMON)
    if not os.path.isdir(base):
        return found

    def names(value):
        # A parser tuple is an operator-first array, and a repeated key a list.
        if isinstance(value, list):
            for item in value:
                yield from names(item)
        elif isinstance(value, dict):
            yield from names(value.get("name"))
        elif isinstance(value, str) and value not in ("=", "?="):
            yield value

    def walk(value) -> None:
        if isinstance(value, dict):
            for key, sub in value.items():
                kind = SET_KEYS.get(key)
                if kind:
                    found.update((kind, n) for n in names(sub))
                walk(sub)
        elif isinstance(value, list):
            for sub in value:
                walk(sub)

    for fname in sorted(os.listdir(base)):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(base, fname), encoding="utf-8") as fh:
                walk(json.load(fh))
        except (OSError, ValueError):
            continue
    return found


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _script_files(mod_path: str):
    for top in AUDIT_DIRS:
        base = os.path.join(mod_path, top)
        for dirpath, dirs, names in os.walk(base):
            dirs.sort()
            for fname in sorted(names):
                if fname.endswith(".txt"):
                    path = os.path.join(dirpath, fname)
                    yield path, os.path.relpath(path, mod_path).replace(os.sep, "/")


def judge(texts: dict[str, str], *, links: set[str] | None = None,
          vanilla: set[tuple[str, str]] | None = None) -> AuditResult:
    """Audit `texts` ({relative path: file text}) as one mod."""
    links = links or set()
    result = AuditResult(files_audited=len(texts))

    pending = {rel: unquote_names(text) for rel, text in texts.items()}
    odd_params = frozenset(
        p for rel, text in pending.items() if rel.startswith(SCRIPTED_EFFECTS_DIR) and "$" in text
        for p in _PARAM_RE.findall(text) if not p.isupper()
    )
    files: list[_File] = []
    scan = _Scan(links, odd_params)

    def load(rels: list[str]) -> None:
        for rel in rels:
            clean, comments = blank_comments_and_strings(pending.pop(rel))
            files.append(_File(rel, parse_tree(clean), comments))
            scan.add(files[-1])

    # Most of the mod's text writes no variable, and parsing is most of the
    # cost. Such a file matters only when it calls a scripted effect that sets
    # or changes a name it is passed, which its words tell without parsing it;
    # a helper found that way can bring in callers of its own.
    load([rel for rel in sorted(pending) if writes_a_variable(pending[rel])])
    words: dict[str, set[str]] = {}
    known: set[str] = set()
    while True:
        found = resolve(scan)
        new = found.helpers - known
        known |= new
        if not new or not pending:
            break
        for rel in pending:
            if rel not in words:
                words[rel] = set(pending[rel].split())
        batch = [rel for rel in sorted(pending) if not new.isdisjoint(words[rel])]
        if not batch:
            break
        load(batch)

    # A plain name is cleared by a set of exactly that name. A set whose name
    # still carries a parameter says nothing about a plain name: as a pattern,
    # `te_dg_m$S$` would clear every variable that starts `te_dg_m`.
    exact = {kind: set() for kind in SET_KEYS.values()}
    skeletons = {kind: set() for kind in SET_KEYS.values()}
    for kind, name in found.initialised | (vanilla or set()):
        if "$" not in name:
            exact[kind].add(name)
        elif len(literal_part(name)) >= MIN_LITERAL:
            skeletons[kind].add(skeleton(name))

    def pattern_initialised(kind: str, name: str) -> bool:
        """For a change name that carries a parameter no caller resolved: a set
        written with the same parameters, or any plain set name it could be."""
        if skeleton(name) in skeletons[kind]:
            return True
        mine = _pattern(name)
        return any(mine.fullmatch(n) for n in exact[kind])

    comments = {f.rel: f.comments for f in files}
    used: set[tuple[str, int]] = set()

    def flag(rel: str, line: int, effect: str, kind: str, name: str, via=None) -> None:
        exemption = parse_reviewed(comments[rel].get(line), (CHECK,))
        if exemption is not None:
            used.add((rel, line))
        result.flags.append(Flag(
            rel, line, effect, kind, name,
            sorted(found.guarded.get((kind, name), [])),
            sorted(found.flag_form.get((kind, name), [])),
            via, exemption,
        ))

    for rel, line, effect, kind, name, _owner in scan.changes:
        if "$" not in name:
            result.judged += 1
            if name not in exact[kind]:
                flag(rel, line, effect, kind, name)
        elif (rel, line) in found.resolved_changes:
            result.judged += 1  # each name a caller passes is judged below
        elif len(literal_part(name)) >= MIN_LITERAL:
            result.judged += 1
            if not pattern_initialised(kind, name):
                flag(rel, line, effect, kind, name)
        else:
            result.unjudged += 1
    for (kind, name), calls in found.reached.items():
        if name in exact[kind]:
            continue
        for (rel, line), (origin_rel, origin_line, effect, written) in calls.items():
            flag(rel, line, effect, kind, name, via=(origin_rel, origin_line, written))
    result.flags.sort(key=lambda f: (f.file, f.line, f.name))

    for rel in sorted(pending):
        if CHECK in pending[rel]:
            comments[rel] = blank_comments_and_strings(pending[rel])[1]
    for rel in sorted(comments):
        for line, comment in comments[rel].items():
            hit = parse_reviewed(comment, (CHECK,))
            if hit is not None and hit["tag"] == CHECK and (rel, line) not in used:
                result.stale.append(StaleTag(rel, line, CHECK))
    return result


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (a file scan) but kept for the POST_LOAD_AUDITS
    `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    texts = {rel: _read(path) for path, rel in _script_files(mod_path)}
    return judge(texts, links=load_scope_links(mod_path), vanilla=vanilla_sets(mod_path))


def render_report(result: AuditResult) -> str:
    # Flag counts only: how many changes were judged moves with unrelated mod
    # content, so it stays on the result and in regenerate()'s summary.
    return _standard_report(result, TITLE, audit="change_variable_init_audit", intro=INTRO)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    write_text(out_path, render_report(result))
    return {
        "unreviewed": len(result.failing),
        "total_flags": len(result.flags),
        "exempted": len(result.exemptions),
        "stale_tags": len(result.stale),
        "judged": result.judged,
        "unjudged": result.unjudged,
        "files_audited": result.files_audited,
        "path": out_path,
    }


def main(argv=None) -> int:
    """Print the report; `--strict` (CI) exits 1 on an unreviewed flag or a
    stale tag."""
    from path_constants import mod_path

    def add_arguments(parser):
        parser.add_argument("--write", action="store_true", help="also write the report")

    def run(args):
        result = audit(mod_path=mod_path)
        if args.write:
            write_text(os.path.join(mod_path, REPORT_PATH), render_report(result))
        return result

    return cli_main(run, lambda result, args: render_report(result), argv=argv,
                    description=__doc__.splitlines()[0], add_arguments=add_arguments,
                    strict_help="exit 1 on an unreviewed flag or a stale tag (CI mode)")


if __name__ == "__main__":
    raise SystemExit(main())
