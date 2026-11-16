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
variable has no *initialising* `set_variable` (of the same kind) anywhere in
`common/` or `events/`, nor in vanilla's `common/` (the `vanilla_parsed/`
snapshot). A set initialises unless it can only run when the variable is
already set:

* it sits in a block whose `limit` has `has_variable = X` as its own child or
  under an `AND`, or reads `var:X` there (`var:X >= 6`: false when X is unset);
* with nothing but `if` / `else_if` / `while` and other blocks that stay on
  the same object between that limit and the set. Behind a scope change
  (`scope:other = { set_variable = … }`, an iterator) a `var` guard no longer
  speaks of the object being set; global and local guards hold at any depth.

A set written in a scripted effect with the name in a parameter (`set_variable
= { name = $OUT$ … }`) initialises the name each caller passes (`te_set_sqrt =
{ … OUT = my_var }`), through helpers that pass it on.

What is not judged
------------------
* Whether the set runs *before* the change. A variable set at an object's
  creation and changed in its monthly pulse is the mod's ordinary shape, and
  only the name is matched: one initialising set anywhere clears every change
  of that name.
* A change whose name is all parameter (`name = $COUNTER$`): counted
  (`AuditResult.unjudged`, in `regenerate()`'s summary), not judged. A name
  that is part parameter (`sr_$KEY$_stock`) is matched against the sets as a
  pattern, either way round.
* A variable only vanilla's *events* set: the snapshot has no events, so such a
  change is flagged and takes the comment below.

Suppress an intended one with a trailing
`# REVIEWED YYYY-MM-DD (variable_init): rationale` on the `change_variable`
line. A tagged comment on a line with no flag is stale and fails `--strict`.

A raw-text scan with `variable_guard_audit`'s tree, for its reasons: the parser
keeps neither line numbers nor comments. About five seconds: only the files
that write a variable are parsed (some 40% of the text), and another only when
it holds the name of a variable that would otherwise be flagged.
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
    "has `has_variable = X` or reads `var:X`, on the same object. The reset after a batch, `if = { limit = { "
    "var:x >= 6 } set_variable = { name = x value = 0 } }`, is the usual one.\n\n"
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

# A variable read at the head of a limit's own line (`this.` is the current
# scope); `scope:x.var:y` reads another object's and is not a guard.
_HEAD_READ_RE = re.compile(r"^(?:this\.)?(var|global_var|local_var):([A-Za-z0-9_$\-]+)$", re.I)
_PARAM_RE = re.compile(r"\$[A-Za-z0-9_]+\$")
_ANY_WRITE_RE = re.compile(r"\b(?:set|change)_(?:global_|local_)?variable\b")

# A name with a `$PARAM$` in it is matched as a pattern only when this many
# characters of it are literal: `$KEY$` or `$PX$f0` would match every name.
MIN_LITERAL = 4

# How many rounds a parameter name is followed through helpers that pass it on
# (`a = { OUT = $X$ }` inside `b`, called with `X = name`).
MAX_PASSES = 6


@dataclass
class Flag:
    file: str
    line: int  # the `change_variable` line
    effect: str  # change_variable / change_global_variable / change_local_variable
    kind: str  # var / global_var / local_var
    name: str
    # Where the variable is set, each behind a guard of its own name.
    guarded_sets: list[tuple[str, int]] = field(default_factory=list)
    exemption: dict | None = None

    @property
    def message(self) -> str:
        setter = "set_" + self.effect[len("change_"):]
        guard = "has_" + self.effect[len("change_"):]
        head = f"`{self.effect}` of `{self.name}`: "
        if not self.guarded_sets:
            return head + f"no `{setter}` of it in the mod or in vanilla's `common/`"
        shown = ", ".join(f"`{f}:{ln}`" for f, ln in self.guarded_sets[:3])
        more = len(self.guarded_sets) - 3
        if more > 0:
            shown += f" and {more} more"
        return (head + f"every `{setter}` of it sits behind a `{guard}` check or a `{self.kind}:` read of it "
                f"({shown}), so nothing sets it first")


@dataclass
class AuditResult(_AuditResult):
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0
    judged: int = 0  # change sites matched against the sets
    unjudged: int = 0  # change sites whose name is all parameter


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


def _written_name(child: tuple) -> str | None:
    """The variable a set or change statement names: `set_variable = x`, or
    the block's `name = x`. A quoted name was blanked and is not read."""
    if child[0] == "scalar":
        value = child[3]
    else:
        value = next((c[3] for c in child[1].children if c[0] == "scalar" and c[1] == "name"), None)
    if not value or value.startswith('"'):
        return None
    return value


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
                m = _HEAD_READ_RE.match(key)
            elif child[0] == "block":
                sub = child[1]
                if (sub.key or "").upper() == "AND":
                    read(sub)
                    continue
                m = _HEAD_READ_RE.match(sub.key or "")
            else:
                continue
            if m:
                guards.add((m.group(1).lower(), m.group(2)))

    for child in node.children:
        if child[0] == "block" and child[1].key == "limit":
            read(child[1])
    return guards


class _Scan:
    """What the parsed files write: every set with whether it is guarded,
    every call that passes arguments, and every change."""

    def __init__(self, links: set[str]):
        self.links = links
        # (kind, name, guarded, file, line, owner): `owner` is the scripted
        # effect the statement is written in, if any.
        self.sets: list[tuple[str, str, bool, str, int, str | None]] = []
        # (callee, {argument: value}, guards at the call, file, line, owner).
        # Any block with an upper-case argument (`OUT = my_var`, as the mod
        # writes them), so scripted triggers too; only a callee that sets a
        # name in a parameter is ever looked up.
        self.calls: list[tuple[str, dict[str, str], frozenset, str, int, str | None]] = []
        self.changes: list[tuple[str, int, str, str, str]] = []  # file, line, effect, kind, name

    def add(self, f: _File) -> None:
        if f.rel.startswith(SCRIPTED_EFFECTS_DIR):
            for child in f.tree.children:
                if child[0] == "block":
                    self.walk(child[1], frozenset(), f.rel, child[1].key)
        else:
            self.walk(f.tree, frozenset(), f.rel, None)

    def walk(self, node: Node, guards: frozenset, rel: str, owner: str | None) -> None:
        for child in node.children:
            if child[0] == "bare":
                continue
            key = child[1] if child[0] == "scalar" else child[1].key
            line = child[4] if child[0] == "scalar" else child[1].line
            if key in SET_KEYS:
                name = _written_name(child)
                if name:
                    kind = SET_KEYS[key]
                    self.sets.append((kind, name, (kind, name) in guards, rel, line, owner))
            elif key in CHANGE_KEYS:
                name = _written_name(child)
                if name:
                    self.changes.append((rel, line, key, CHANGE_KEYS[key], name))
            if child[0] != "block":
                continue
            sub = child[1]
            if key:
                args = {c[1]: c[3] for c in sub.children
                        if c[0] == "scalar" and c[3] and c[1].isupper()}
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


def substitute(template: str, args: dict[str, str]) -> str:
    """`template` with each `$P$` the call passes filled in. A parameter the
    call leaves out, or passes as a quoted string, stays."""
    def fill(m: re.Match) -> str:
        value = args.get(m.group(0)[1:-1])
        return m.group(0) if value is None or value.startswith('"') else value
    return _PARAM_RE.sub(fill, template)


def resolve_sets(scan: _Scan) -> tuple[set[tuple[str, str]], dict[tuple[str, str], list[tuple[str, int]]]]:
    """(the initialised names, the guarded sets by name). A set a scripted
    effect makes of a name in a parameter is credited to the name each caller
    passes, through helpers that pass it on."""
    initialised: set[tuple[str, str]] = set()
    guarded: dict[tuple[str, str], list[tuple[str, int]]] = {}
    # scripted effect -> {(kind, name with $PARAM$)} it sets unguarded.
    templates: dict[str, set[tuple[str, str]]] = {}
    for kind, name, is_guarded, rel, line, owner in scan.sets:
        if is_guarded:
            guarded.setdefault((kind, name), []).append((rel, line))
            continue
        initialised.add((kind, name))
        if owner and "$" in name:
            templates.setdefault(owner, set()).add((kind, name))
    for _ in range(MAX_PASSES):
        grew = False
        for callee, args, guards, rel, line, owner in scan.calls:
            for kind, template in tuple(templates.get(callee, ())):
                name = substitute(template, args)
                if name == template:
                    continue  # the call passes none of its parameters
                if (kind, name) in guards:
                    guarded.setdefault((kind, name), []).append((rel, line))
                    continue
                initialised.add((kind, name))
                if owner and "$" in name and (kind, name) not in templates.setdefault(owner, set()):
                    templates[owner].add((kind, name))
                    grew = True
        if not grew:
            break
    return initialised, guarded


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


def _uninitialised(scan: _Scan, initialised: set[tuple[str, str]]) -> set[tuple[str, str]]:
    """The changed (kind, name)s no initialising set matches. A name that is
    all parameter is not among them: it is not judged."""
    exact = {kind: set() for kind in SET_KEYS.values()}
    skeletons = {kind: set() for kind in SET_KEYS.values()}
    patterns = {kind: [] for kind in SET_KEYS.values()}
    for kind, name in initialised:
        if "$" not in name:
            exact[kind].add(name)
        elif len(literal_part(name)) >= MIN_LITERAL:
            skeletons[kind].add(skeleton(name))
            patterns[kind].append(_pattern(name))

    def is_initialised(kind: str, name: str) -> bool:
        if "$" not in name:
            return name in exact[kind] or any(p.fullmatch(name) for p in patterns[kind])
        if skeleton(name) in skeletons[kind]:
            return True
        mine = _pattern(name)
        return any(mine.fullmatch(n) for n in exact[kind])

    changed = {(kind, name) for _rel, _line, _effect, kind, name in scan.changes
               if "$" not in name or len(literal_part(name)) >= MIN_LITERAL}
    return {(kind, name) for kind, name in changed if not is_initialised(kind, name)}


def judge(texts: dict[str, str], *, links: set[str] | None = None,
          vanilla: set[tuple[str, str]] | None = None) -> AuditResult:
    """Audit `texts` ({relative path: file text}) as one mod."""
    links = links or set()
    result = AuditResult(files_audited=len(texts))

    pending = dict(texts)
    files: list[_File] = []
    scan = _Scan(links)

    def load(rels: list[str]) -> None:
        for rel in rels:
            clean, comments = blank_comments_and_strings(pending.pop(rel))
            files.append(_File(rel, parse_tree(clean), comments))
            scan.add(files[-1])

    # Most of the mod's text writes no variable, and parsing is most of the
    # cost. Such a file can still initialise one, by passing its name to a
    # scripted effect that sets it, so it is parsed only when it holds the
    # name of a variable that would otherwise be flagged (and every scripted
    # effect file then, for a helper that only passes the name on).
    load([rel for rel in sorted(pending) if _ANY_WRITE_RE.search(pending[rel])])
    while True:
        mod_sets, guarded_sets = resolve_sets(scan)
        missing = _uninitialised(scan, mod_sets | (vanilla or set()))
        needles = {max(skeleton(name).split("\0"), key=len) for _kind, name in missing}
        batch = [rel for rel in sorted(pending)
                 if rel.startswith(SCRIPTED_EFFECTS_DIR) or any(n in pending[rel] for n in needles)]
        if not needles or not batch:
            break
        load(batch)

    comments = {f.rel: f.comments for f in files}
    used: set[tuple[str, int]] = set()
    for rel, line, effect, kind, name in scan.changes:
        if "$" in name and len(literal_part(name)) < MIN_LITERAL:
            result.unjudged += 1
            continue
        result.judged += 1
        if (kind, name) not in missing:
            continue
        exemption = parse_reviewed(comments[rel].get(line), (CHECK,))
        if exemption is not None:
            used.add((rel, line))
        result.flags.append(Flag(rel, line, effect, kind, name,
                                 sorted(guarded_sets.get((kind, name), [])), exemption))
    result.flags.sort(key=lambda f: (f.file, f.line))

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
