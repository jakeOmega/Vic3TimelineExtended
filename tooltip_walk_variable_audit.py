"""Audit a variable set and then read in one effect body that a tooltip walks (#918).

A scripted GUI's or a journal entry button's `effect`, an event `option` and a
decision's `when_taken` are walked every frame their tooltip shows. The walk
tests each `limit` and evaluates each value against the current state, and
writes nothing. So a body that `set_variable`s a name and later reads it
(`var:X` in a `limit`, a `switch`'s `trigger`, a value, a `prev.` / `scope:`
chain) finds it unset during the walk and logs `Failed to fetch variable`,
`Event target link 'var' returned an unset scope`, `Invalid left side during
comparison 'var'` or `Value of wrong type … 'none'` every frame. The click
works, so nothing shows it until someone hovers the button
(`docs/guides/scripting_best_practices.md` § "Workaround 2" and § "An
Option's Tooltip Walks Its Effects"). Grand Monuments hit it twice:
`gm_com_drop` in `gm_country_refresh` (about 150 lines a burst, 2026-10-07)
and `gm_rebuild_level` as the `trigger` of a 200-case switch reached from the
Rededicate button (about 600 lines a frame, 2026-10-12).

Roots
-----
* every `effect` block in `common/scripted_guis/` and `common/scripted_buttons/`;
* every `option` of an event, its `trigger` and `ai_chance` left out, then
  the event's `after`, walked as the rest of the option's body (an `after`'s
  effects show in every option's preview: scripting_best_practices.md §
  "`every_*` Iterators Enumerate in Tooltip Previews");
* every decision's `when_taken`.

An event's `immediate` is not a root: it runs for real when the event fires,
so what it sets is there when the options' tooltips walk (it counts as code
that keeps a variable set, below).

The walk
--------
From each root the body is walked in order, scripted effects, scripted
triggers and script values inlined, each call's `$PARAM$` arguments
substituted (a forwarded `X = $X$` keeps its first caller's value). Scope is
followed block by block: `scope:x`, `root`, `prev`, an iterator or a scope
link starts a new scope, and `save_scope_as` names the current one (the walk
does run it: § "An Option's Tooltip Walks Its Effects"). A read is flagged when

1. an earlier `set_variable` / `change_variable` of the name (global forms too)
   in the same walk wrote it on the same scope;
2. no guard covers it. A `has_variable = <V>` (or `exists = var:<V>`) in an
   `if` / `else_if` / iterator `limit`, a `trigger_if` limit, or before the
   read in the same `AND`, works two ways:
   * V a *scratch* name, every write of it removed later in its own body on
     a path the write runs on (not in a sibling `if` / `else` branch, a
     `random_list` or `switch` branch, or another option of the event): a
     click-only marker, a staged figure. It cannot be set while a tooltip
     shows, so the guard is false in the walk and the walk skips what it
     guards. Only writes of V's own name count here, not a `$J$` template
     no caller fills in;
   * any other V, a flag a click or a pulse sets and leaves (`gm_com_open`):
     once set, the walk enters what it guards every frame, so the block is
     walked; only a read of V itself behind the guard is safe.
   A guard after the read, or beside it in a `NOT` / `NOR` / `NAND` (which
   reads every child), covers nothing. In an `OR`, a child
   `NOT = { has_variable = x }` covers x in the children after it (the OR
   stops at its first true child), as `nd_taboo_effective_ceiling_value`
   relies on; `variable_guard_audit` reads that shape as sound too. A guard in a scripted trigger the
   `limit` calls counts, and one behind a link (`root = { has_variable = x }`)
   covers `root.var:x`;
3. nothing else keeps the name set (below).

The reads of an `if`'s branches start from what was set before the `if`, so
a set in one branch is not "earlier" for its sibling. `var:X ?= …` is never a
read (false when unset, nothing logged).

"Other code keeps it set"
-------------------------
A variable is left out when some write of it runs without a tooltip root and
nothing later in the same body removes it: those usually exist when the walk
runs (`gm_grandeur`: the country refresh keeps it on every monument state).
Concretely, a write site *keeps* the name when

* it is not inside a root (`option`, a button's `effect`, `when_taken`),
  and, in a scripted effect, the effect is reached through call edges
  (`script_call_graph`) from somewhere that is not a root: an on-action, a
  journal entry, an event's `immediate` or `after`, a law, history; and
* the same body (the scripted effect; an event's or an entity's top-level
  block) does not remove the name later, directly or through an effect it
  calls. `gm_com_drop` was written and removed in one pass of the refresh,
  which the pulse also runs, so it was flagged; an event that sets a name in
  `immediate` and removes it in `after` keeps it for its options.

A write with `$NAME$` in a helper is resolved at each caller that passes the
name (forwards followed); the caller's place decides. A write whose name is a
bare `$X$` no caller fills in is ignored. A name that stays a pattern
(`gm_ig_net_$IG$` with no literal caller) keeps every name it fits.

Blind spots
-----------
* Local variables (`set_local_variable` / `local_var:`): whether the walk
  writes them is unverified, and the mod reads them some fifteen thousand
  times. Not audited.
* Scope identity is by the path written: a write in `scope:x = { … }` read as
  `prev.var:X` from inside an iterator, or a state's `owner` that is the root
  country, reads as another scope (missed, not falsely flagged).
* A `limit` whose truth depends on anything but a `has_variable` of a
  scratch name is taken to pass; every branch of an `if` chain, every
  `random_list` branch and every `switch` case is walked.
* "Removed later in the same body" looks inside one body only: a pulse that
  sets `x` in effect A and removes it in B, which the pulse calls after A,
  reads as keeping `x`. So a button that calls A, reads `x` and calls B is
  not flagged. The same holds for deciding what is scratch.
* A name written to the same object by unrelated code that keeps it is
  enough to clear a read, whatever the scope: a scratch name shared by a
  pulse that keeps it hides a real flag.
* `exists = var:X` is read as a guard, not as a read; whether it logs when X
  is unset is unverified.

Suppression
-----------
Fix the read: compare the values directly (`var:a > some_script_value`), read
a variable that persists between runs, guard the read with `has_variable = X`
(false in the walk, true once the set has run), or put the body behind a
click-only marker (`set_variable = m  if = { limit = { has_variable = m }
remove_variable = m … } }`). Where a read is provably safe, say why on the
read line:

    limit = { var:x > 0 } # REVIEWED 2026-11-12 (tooltip_walk): <why the walk never reaches it unset>

The read line is where the `var:` is written; for a read that arrives as a
`$PARAM$` argument (`SPEC_LEVEL = var:gm_rebuild_level`), the line of the
call that passes it. A tag on a line with no flag is stale and fails
`--strict`. `--root <sgui, event id or decision>` prints one root's walk
flags with their call chains.

Where it runs: CI (`--strict`, through `scripts/run_audits.py`) and the
command line, not the server's reload. A run takes about 25 s cold; the
per-file parse and call scan are kept across runs in one process
(`_PARSE_CACHE`, `_CALL_SCAN_CACHE`), but the walk is most of a warm run, so
a warm one still takes 13 to 15 s, too much for every `POST /reload`.
`regenerate()` is there for the day it joins POST_LOAD_AUDITS: it writes
docs/engine/tooltip_walk_variable_report.md.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import variable_guard_audit as vga
from iterator_limit_audit import blank_comments_and_strings

CHECK = "tooltip_walk"
AUDIT_DIRS = ("common", "events")
REPORT = os.path.join("docs", "engine", "tooltip_walk_variable_report.md")

# Root blocks by directory under common/: a button's `effect`, a decision's
# `when_taken`. Events: every `option`.
ROOT_BLOCKS = {
    "scripted_guis": "effect",
    "scripted_buttons": "effect",
    "decisions": "when_taken",
}
# Keys of an option that are not its effects.
OPTION_SKIP = {"trigger", "ai_chance", "show_as_unavailable", "is_shown", "possible"}

# write key -> variable prefix
WRITE_KEYS = {
    "set_variable": "var", "change_variable": "var",
    "set_global_variable": "global_var", "change_global_variable": "global_var",
}
REMOVE_KEYS = {"remove_variable": "var", "remove_global_variable": "global_var"}
GUARD_KEYS = {"has_variable": "var", "has_global_variable": "global_var"}
SAVE_SCOPE_KEYS = {"save_scope_as", "save_temporary_scope_as"}
# Blocks that only describe effects; nothing in them runs.
DISPLAY_ONLY = {"map_tooltip", "event_outcome_effect_desc", "event_outcome_activated_effect_desc"}
# Scalar keys whose value is a name, never a script value to evaluate.
NAME_KEYS = {"name", "text", "id", "desc", "tooltip", "title", "type", "building", "key",
             "default", "icon", "trigger_desc", "flag", "variable"}
CHAIN_KEYS = ("if", "else_if", "else")
_DIRECTIVE_RE = re.compile(r"^(?:TRY_)?(?:INJECT|REPLACE)(?:_OR_CREATE)?:")
_EVENT_ID_RE = re.compile(r"^[A-Za-z_][\w]*\.\d+$")
_PARAM_RE = re.compile(r"\$(\w+)\$")
_DISPATCH_RE = re.compile(r"^[A-Za-z0-9_$]+$")
_SEG_VAR_RE = re.compile(r"^(var|global_var):([A-Za-z0-9_$\-]+)$", re.I)
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)
_ANY_WRITE_RE = re.compile(r"\b(?:set|change|remove)_(?:global_)?variable\b")

ROOT_SCOPE = "ROOT"
# A scope saved inside `create_container`: the walk creates no container, so
# the scope stays unset and `exists = scope:x` on it is false
# (scripting_best_practices.md § "An Option's Tooltip Walks Its Effects").
UNSET = "<unset>"
CREATE_KEYS = {"create_container"}
GLOBAL_SCOPE = "GLOBAL"
MAX_DEPTH = 40


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class Def:
    kind: str  # "effect" | "trigger" | "value"
    name: str
    file: str
    node: vga.Node


@dataclass
class Root:
    kind: str  # "sgui" | "button" | "option" | "decision"
    label: str  # "gm_rededicate_sgui", "monument_events.17 option 2", ...
    file: str
    line: int
    node: vga.Node
    skip: frozenset = frozenset()
    # An option's tooltip shows the event's `after` too: walked after the option.
    after: vga.Node | None = None


@dataclass
class Site:
    """One place a variable is written or removed, at the line that decides it
    (for a `$NAME$` resolved at a caller, the caller's call line)."""
    prefix: str
    name: str  # concrete, or a pattern if `pattern`
    file: str
    line: int
    body: tuple  # what "the same body" means for a later removal
    background: bool  # runs without a tooltip root
    pattern: re.Pattern | None = None


@dataclass
class Flag:
    file: str
    line: int
    variable: str  # "var:x" / "global_var:x"
    kind: str  # "limit", "switch trigger", "value", "scope"
    set_at: str  # "file:line" of the earlier write
    roots: list[str] = field(default_factory=list)
    chain: list[str] = field(default_factory=list)  # first root's call chain to the read
    via_argument: bool = False  # the read arrives as a `$PARAM$` argument
    exemption: dict | None = None


@dataclass
class StaleTag:
    file: str
    line: int


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    roots: int = 0

    @property
    def failing(self) -> int:
        return sum(1 for f in self.flags if not f.exemption) + len(self.stale_tags)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _strip(name: str) -> str:
    return _DIRECTIVE_RE.sub("", name)


def _files(mod_path: str):
    for sub in AUDIT_DIRS:
        base = os.path.join(mod_path, sub)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs.sort()
            for fname in sorted(files):
                if fname.endswith(".txt"):
                    p = os.path.join(root, fname)
                    yield p, os.path.relpath(p, mod_path).replace(os.sep, "/")


def _subdir(rel: str) -> str:
    parts = rel.split("/")
    if parts[0] == "events":
        return "events"
    return parts[1] if len(parts) > 2 else ""


DEF_DIRS = {"scripted_effects": "effect", "scripted_triggers": "trigger", "script_values": "value"}


# Kept across runs in one process (the server's reloads), so a run reads again
# only what changed: {abs path: ((size, mtime_ns), tree or None)} for the
# parse, and {abs path: ((size, mtime_ns), effect-name token, effect_calls)}
# for event_context_audit's per-file call scan. A tree is read, never written.
_PARSE_CACHE: dict = {}
_CALL_SCAN_CACHE: dict = {}


def _stamp(path: str) -> tuple[int, int] | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_size, st.st_mtime_ns)


class Mod:
    """The parsed files the audit reads, its definitions and roots."""

    def __init__(self, mod_path: str):
        self.mod_path = mod_path
        self.trees: dict[str, vga.Node] = {}
        self.defs: dict[str, dict[str, Def]] = {"effect": {}, "trigger": {}, "value": {}}
        self.roots: list[Root] = []
        self.files: list[tuple[str, str]] = list(_files(mod_path))
        for path, rel in self.files:
            sub = _subdir(rel)
            tree = self._parse(path, sub)
            if tree is None:
                continue
            self.trees[rel] = tree
            if sub in DEF_DIRS:
                kind = DEF_DIRS[sub]
                for child in tree.children:
                    if child[0] != "block" or not child[1].key:
                        continue
                    node = child[1]
                    name = _strip(node.key)
                    # A later REPLACE wins; otherwise the first definition.
                    if name not in self.defs[kind] or node.key.startswith(("REPLACE", "TRY_REPLACE")):
                        self.defs[kind][name] = Def(kind, name, rel, node)
            elif sub in ROOT_BLOCKS:
                want = ROOT_BLOCKS[sub]
                kind = "decision" if sub == "decisions" else ("sgui" if sub == "scripted_guis" else "button")
                for child in tree.children:
                    if child[0] != "block" or not child[1].key:
                        continue
                    for sc in child[1].children:
                        if sc[0] == "block" and sc[1].key == want:
                            self.roots.append(Root(kind, _strip(child[1].key), rel, sc[1].line, sc[1]))
            elif sub == "events":
                for child in tree.children:
                    if child[0] != "block" or not child[1].key or not _EVENT_ID_RE.match(child[1].key):
                        continue
                    n = 0
                    after = next((sc[1] for sc in child[1].children
                                  if sc[0] == "block" and sc[1].key == "after"), None)
                    for sc in child[1].children:
                        if sc[0] == "block" and sc[1].key == "option":
                            n += 1
                            self.roots.append(Root("option", f"{child[1].key} option {n}", rel,
                                                   sc[1].line, sc[1], frozenset(OPTION_SKIP), after))


    @staticmethod
    def _parse(path: str, sub: str) -> vga.Node | None:
        stamp = _stamp(path)
        hit = _PARSE_CACHE.get(path)
        if hit is not None and stamp is not None and hit[0] == stamp:
            return hit[1]
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                text = fh.read()
        except OSError:
            return None
        if sub not in DEF_DIRS and sub not in ROOT_BLOCKS and sub != "events" \
                and not _ANY_WRITE_RE.search(text):
            tree = None  # no write, no def, no root: nothing to read here
        else:
            tree = vga.parse_tree(blank_comments_and_strings(text)[0])
        if stamp is not None:
            _PARSE_CACHE[path] = (stamp, tree)
        return tree

    def _fitting(self, template: str) -> list[Def]:
        """The effects and triggers a parameterised name (`helper_$KIND$`) fits."""
        memo = self.__dict__.setdefault("_fit_defs", {})
        hit = memo.get(template)
        if hit is None:
            literal = _PARAM_RE.split(template)[::2]
            pat = re.compile("^" + "[A-Za-z0-9_]+".join(re.escape(p) for p in literal) + "$")
            hit = memo[template] = [d for kind in ("effect", "trigger")
                                    for n, d in self.defs[kind].items() if pat.match(n)]
        return hit

    def summary(self, d: Def) -> tuple[frozenset, frozenset, frozenset, frozenset]:
        """(reads, writes, guards, scopes): the variable names `d` could read,
        write and test with `has_variable` / `exists`, and the saved scopes it
        names, through what it calls, as written (a name may hold `$PARAM$`s).
        A call through a parameterised name adds `$`, which matches anything."""
        memo = self.__dict__.setdefault("_summary", {})
        key = (d.kind, d.name)
        if key in memo:
            return memo[key]
        memo[key] = (frozenset(),) * 4  # a cycle adds nothing more
        scopes: set[str] = set()
        reads: set[str] = set()
        writes: set[str] = set()
        guards: set[str] = set()
        todo = [d.node]
        while todo:
            node = todo.pop()
            for c in node.children:
                if c[0] == "block":
                    toks = (c[1].key,)
                    todo.append(c[1])
                    if c[1].key in WRITE_KEYS:
                        nm = _name_of(c[1])
                        if nm:
                            writes.add(nm)
                elif c[0] == "scalar":
                    toks = (c[1], c[3])
                    if c[1] in WRITE_KEYS and c[3]:
                        writes.add(c[3])
                    elif c[1] in GUARD_KEYS and c[3]:
                        guards.add(c[3])
                else:
                    toks = (c[1],)
                for t in toks:
                    if not t:
                        continue
                    if "scope:" in t:
                        scopes.update(m.group(1) for m in re.finditer(r"scope:([A-Za-z0-9_$]+)", t))
                    if "var:" in t:
                        names = [m.group(1) for m in re.finditer(r"var:([A-Za-z0-9_$\-]+)", t)]
                        reads.update(names)
                        if c[0] == "scalar" and c[1] == "exists":
                            guards.update(names)
                    if "$" in t:
                        if "var:" not in t:
                            scopes.add("$")
                            if t != toks[0]:
                                # A value: whatever the argument is (a `var:`,
                                # a script value), kept as written.
                                reads.add(t)
                            elif _PARAM_RE.sub("", t) and _DISPATCH_RE.match(t):
                                # `helper_$KIND$`: any effect or trigger the
                                # name's pattern fits.
                                for sub in self._fitting(t):
                                    if sub is not d:
                                        r, w, g, sc = self.summary(sub)
                                        reads |= r
                                        writes |= w
                                        guards |= g
                                        scopes |= sc
                            elif c[0] == "scalar":
                                # `$EFFECT$ = yes`: whatever a caller names.
                                reads.add("$")
                                writes.add("$")
                                guards.add("$")
                            # A `$WHO$ = { … }` block is a scope: its body
                            # is read like any other.
                        continue
                    for kind in ("effect", "trigger", "value"):
                        sub = self.defs[kind].get(t)
                        if sub is not None and sub is not d:
                            r, w, g, sc = self.summary(sub)
                            reads |= r
                            writes |= w
                            guards |= g
                            scopes |= sc
        res = (frozenset(reads), frozenset(writes), frozenset(guards), frozenset(scopes))
        memo[key] = res
        return res


# ---------------------------------------------------------------------------
# Who keeps a variable set
# ---------------------------------------------------------------------------


def _root_context(rel: str, path: tuple[str, ...]) -> bool:
    """True when a site at `path` (block keys below the top-level entity) in
    file `rel` sits inside a tooltip root."""
    sub = _subdir(rel)
    if sub == "events":
        return "option" in path or path[:1] == ("after",)
    want = ROOT_BLOCKS.get(sub)
    return bool(want and path and path[0] == want)


def _body(rel: str, entity: str, path: tuple[str, ...]) -> tuple:
    if _subdir(rel) == "scripted_effects":
        return ("effect", entity)
    return (rel, entity, path[0] if path else "")


class Keepers:
    """Which variable names some code outside a tooltip root keeps set."""

    def __init__(self, mod: Mod):
        import event_context_audit as eca
        import script_call_graph as scg

        # The calls of every script file (event_context_audit's scan, the
        # console harnesses read too), each file's scan kept while it stands.
        names = set(mod.defs["effect"])
        token = hash(frozenset(names))
        effect_calls: dict[str, list] = {}
        for path, rel in mod.files:
            stamp = _stamp(path)
            hit = _CALL_SCAN_CACHE.get(path)
            if hit is None or stamp is None or hit[0] != stamp or hit[1] != token:
                calls = eca.scan_file(path, rel, names, strip_directives=True).effect_calls
                hit = (stamp, token, calls)
                if stamp is not None:
                    _CALL_SCAN_CACHE[path] = hit
            for callee, lst in hit[2].items():
                effect_calls.setdefault(callee, []).extend(lst)
        self.effect_calls = effect_calls
        cg = scg.calls_only({n: d.file for n, d in mod.defs["effect"].items()}, effect_calls)
        self.cg = cg
        self.effects = set(mod.defs["effect"])

        # Effects reached from somewhere that is not a tooltip root.
        starts: list = []
        for e in cg.edges:
            if e.kind != "call" or e.src.kind == scg.EFFECT:
                continue
            file = e.file
            if not _root_context(file, e.path):
                starts.append(e.dst)
        bg: set = set()
        todo = list(starts)
        while todo:
            n = todo.pop()
            if n in bg:
                continue
            bg.add(n)
            todo.extend(x.dst for x in cg.edges_from(n, lambda x: x.kind == "call"))
        self.background_effects = {n.name for n in bg if n.kind == scg.EFFECT}

        self.writes: list[Site] = []
        self.removes: list[Site] = []
        for rel, tree in mod.trees.items():
            for child in tree.children:
                if child[0] == "block" and child[1].key:
                    entity = _strip(child[1].key)
                    self._scan(rel, entity, child[1], ())
        # Mutually exclusive branches per file, as line spans: an `if` chain's
        # branches, `random_list` and `switch` branches, an event's options.
        self._branches: dict[str, list[list[tuple[int, int]]]] = {
            rel: _exclusive_groups(tree, rel) for rel, tree in mod.trees.items()}
        self._removes_by_body: dict[tuple, list[Site]] = {}
        for r in self.removes:
            self._removes_by_body.setdefault(r.body, []).append(r)
        self._writes_by_name: dict[tuple[str, str], list[Site]] = {}
        self._pattern_writes: list[Site] = []
        for w in self.writes:
            if w.pattern is not None:
                self._pattern_writes.append(w)
            else:
                self._writes_by_name.setdefault((w.prefix, w.name), []).append(w)
        self._entity_calls: dict[str, list] = {}
        for e in cg.edges:
            if e.kind == "call" and e.src.kind != scg.EFFECT:
                self._entity_calls.setdefault(e.src.name, []).append(e)
        self._transitive_removes: dict[str, frozenset] | None = None
        self._kept: dict[tuple[str, str], bool] = {}
        self._fits: dict[str, bool] = {}
        self._scratch: dict[tuple[str, str], bool] = {}
        # Every concrete name written somewhere that nothing keeps: the only
        # names a walk can flag. Pattern writes stand for no name of their own.
        self.volatile = frozenset(
            name for (prefix, name) in self._writes_by_name if not self.kept(prefix, name))

    # -- site collection --------------------------------------------------

    def _background(self, rel: str, entity: str, path: tuple[str, ...]) -> bool:
        if _subdir(rel) == "scripted_effects":
            return entity in self.background_effects
        return not _root_context(rel, path)

    def _emit(self, out: list[Site], prefix: str, name: str, rel: str, line: int, entity: str,
              path: tuple[str, ...]) -> None:
        if "$" not in name:
            out.append(Site(prefix, name, rel, line, _body(rel, entity, path),
                            self._background(rel, entity, path)))
            return
        if _subdir(rel) != "scripted_effects":
            return
        resolved = self._resolve(name, entity, 0)
        for (sub, crel, cln, centity, cpath) in resolved:
            out.append(Site(prefix, sub, crel, cln, _body(crel, centity, cpath),
                            self._background(crel, centity, cpath)))
        if not resolved and _PARAM_RE.sub("", name):
            # No caller names it: a pattern over every name it fits.
            literal = _PARAM_RE.split(name)[::2]
            pat = re.compile("^" + "[A-Za-z0-9_]+".join(re.escape(p) for p in literal) + "$")
            out.append(Site(prefix, name, rel, line, _body(rel, entity, path),
                            self._background(rel, entity, path), pat))

    def _resolve(self, template: str, effect: str, depth: int) -> list[tuple]:
        """(name, caller file, caller line, caller entity, caller path) for
        each caller of `effect` that fills `template`'s parameters, forwards
        followed."""
        out: list[tuple] = []
        if depth > 6:
            return out
        for (crel, cln, cpk, _sw, _conds, centity, ckind, cparams) in self.effect_calls.get(effect, []):
            names = _PARAM_RE.findall(template)
            if any(p not in cparams for p in names):
                continue
            sub = _PARAM_RE.sub(lambda m: cparams[m.group(1)], template)
            if "$" not in sub:
                out.append((sub, crel, cln, centity, tuple(cpk)))
            elif ckind == "scripted_effect":
                out.extend(self._resolve(sub, centity, depth + 1))
        return out

    def _scan(self, rel: str, entity: str, node: vga.Node, path: tuple[str, ...]) -> None:
        for child in node.children:
            if child[0] == "scalar":
                _, key, op, value, line = child
                if key in WRITE_KEYS and value:
                    self._emit(self.writes, WRITE_KEYS[key], value, rel, line, entity, path)
                elif key in REMOVE_KEYS and value:
                    self._emit(self.removes, REMOVE_KEYS[key], value, rel, line, entity, path)
            elif child[0] == "block":
                sub = child[1]
                if sub.key in WRITE_KEYS:
                    name = _name_of(sub)
                    if name:
                        self._emit(self.writes, WRITE_KEYS[sub.key], name, rel, sub.line, entity, path)
                if sub.key in DISPLAY_ONLY:
                    continue
                self._scan(rel, entity, sub, path + (sub.key or "",))

    # -- the question -----------------------------------------------------

    def _effect_removes(self, effect: str) -> frozenset:
        """(prefix, name) every removal `effect` makes, through what it calls."""
        if self._transitive_removes is None:
            self._transitive_removes = self._all_removes()
        return self._transitive_removes.get(effect, frozenset())

    def _all_removes(self) -> dict[str, frozenset]:
        """Every effect's removals through its callees, to a fixed point."""
        import script_call_graph as scg

        callees: dict[str, set[str]] = {}
        for e in self.cg.edges:
            if e.kind == "call" and e.src.kind == scg.EFFECT:
                callees.setdefault(e.src.name, set()).add(e.dst.name)
        out: dict[str, set] = {}
        for body, lst in self._removes_by_body.items():
            if body[0] == "effect":
                out.setdefault(body[1], set()).update((r.prefix, r.name) for r in lst)
        changed = True
        while changed:
            changed = False
            for src, dsts in callees.items():
                cur = out.setdefault(src, set())
                before = len(cur)
                for d in dsts:
                    if d in out and d != src:
                        cur |= out[d]
                if len(cur) != before:
                    changed = True
        return {k: frozenset(v) for k, v in out.items()}

    def _exclusive(self, file: str, a: int, b: int) -> bool:
        """Lines `a` and `b` of `file` sit in two branches of which only one
        runs (an `if` and its `else`, two options of one event)."""
        for group in self._branches.get(file, ()):
            ia = next((i for i, (lo, hi) in enumerate(group) if lo <= a <= hi), None)
            if ia is None:
                continue
            ib = next((i for i, (lo, hi) in enumerate(group) if lo <= b <= hi), None)
            if ib is not None and ib != ia:
                return True
        return False

    def _removed_after(self, w: Site) -> bool:
        """The same body removes the name after the write, on a path the
        write runs on: not in a sibling branch, not in another option."""
        var = (w.prefix, w.name)
        for r in self._removes_by_body.get(w.body, []):
            if r.file == w.file and r.line > w.line and (r.prefix, r.name) == var \
                    and not self._exclusive(w.file, w.line, r.line):
                return True
        # A call later in the same body to an effect that removes it.
        import script_call_graph as scg

        if w.body[0] == "effect":
            src = scg.Node(scg.EFFECT, w.body[1])
            edges = self.cg.edges_from(src, lambda x: x.kind == "call")
        else:
            rel, entity, top = w.body
            edges = [x for x in self._entity_calls.get(entity, ())
                     if x.file == rel and (x.path[:1] == (top,) if top else True)]
        for e in edges:
            if e.file == w.file and e.line > w.line and var in self._effect_removes(e.dst.name) \
                    and not self._exclusive(w.file, w.line, e.line):
                return True
        return False

    def fits_volatile(self, template: str) -> bool:
        """Does a name with `$PARAM$`s left in it fit a volatile name?"""
        hit = self._fits.get(template)
        if hit is None:
            if not _PARAM_RE.sub("", template):
                hit = True
            else:
                literal = _PARAM_RE.split(template)[::2]
                pat = re.compile("^" + "[A-Za-z0-9_]+".join(re.escape(p) for p in literal) + "$")
                hit = any(pat.match(x) for x in self.volatile)
            self._fits[template] = hit
        return hit

    def scratch(self, prefix: str, name: str) -> bool:
        """True when every write of the name is removed later in the same body
        (a scratch name, a click-only marker): it cannot be set when a tooltip
        shows, so a guard on it is false in the walk. A flag a click sets and
        leaves is not: once set, the walk enters what it guards every frame."""
        key = (prefix, name)
        hit = self._scratch.get(key)
        if hit is None:
            # The writes of this very name. A `$J$` template no caller fills
            # in (`te_dg_d$J$`) stands for names of its own family; it fits
            # `te_dg_dbg_click` by accident, so it is left out here.
            sites = list(self._writes_by_name.get(key, []))
            hit = bool(sites) and all(self._removed_after(w) for w in sites)
            self._scratch[key] = hit
        return hit

    def kept(self, prefix: str, name: str) -> bool:
        key = (prefix, name)
        if key in self._kept:
            return self._kept[key]
        sites = list(self._writes_by_name.get(key, []))
        sites += [w for w in self._pattern_writes if w.prefix == prefix and w.pattern.match(name)]
        res = any(w.background and not self._removed_after(w) for w in sites)
        self._kept[key] = res
        return res


def _last_line(node: vga.Node) -> int:
    last = node.line
    for c in node.children:
        last = max(last, _last_line(c[1]) if c[0] == "block" else c[-1])
    return last


def _exclusive_groups(tree: vga.Node, rel: str) -> list[list[tuple[int, int]]]:
    """Every set of sibling blocks of which one runs, as (first, last line)
    spans: an `if` / `else_if` / `else` chain, the branches of a `random_list`
    or a `switch`, and an event's options."""
    groups: list[list[tuple[int, int]]] = []

    def visit(node: vga.Node, top: bool) -> None:
        chain: list[tuple[int, int]] = []
        blocks = [c[1] for c in node.children if c[0] == "block"]
        for b in blocks:
            if b.key == "if":
                if len(chain) > 1:
                    groups.append(chain)
                chain = [(b.line, _last_line(b))]
            elif b.key in ("else_if", "else") and chain:
                chain.append((b.line, _last_line(b)))
        if len(chain) > 1:
            groups.append(chain)
        if node.key in ("random_list", "switch"):
            spans = [(b.line, _last_line(b)) for b in blocks]
            if len(spans) > 1:
                groups.append(spans)
        if top and rel.startswith("events/") and node.key and _EVENT_ID_RE.match(node.key):
            spans = [(b.line, _last_line(b)) for b in blocks if b.key == "option"]
            if len(spans) > 1:
                groups.append(spans)
        for b in blocks:
            visit(b, False)

    for c in tree.children:
        if c[0] == "block":
            visit(c[1], True)
    return groups


def _name_of(node: vga.Node) -> str | None:
    for c in node.children:
        if c[0] == "scalar" and c[1] == "name" and c[3]:
            return c[3]
    return None


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------


@dataclass
class _Read:
    file: str
    line: int
    prefix: str
    name: str
    kind: str
    set_at: tuple[str, int]
    chain: tuple[str, ...]
    via_argument: bool


class Walker:
    """One root's ordered walk."""

    def __init__(self, mod: Mod, keepers: Keepers, links: set[str], cache: dict | None = None):
        self.mod = mod
        self.cache = {} if cache is None else cache
        self.keepers = keepers
        self.links = links
        self.reads: list[_Read] = []

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _sub(token, params):
        """(substituted token, origin of the argument that brought a variable
        read in, or None)."""
        if token is None or "$" not in token or not params:
            return token, None
        origin = None

        def rep(m):
            nonlocal origin
            p = params.get(m.group(1))
            if p is None:
                return m.group(0)
            if origin is None and ("var:" in p[0]):
                origin = (p[1], p[2])
            return p[0]

        return _PARAM_RE.sub(rep, token), origin

    def _chain_reads(self, token: str, scopes: tuple[str, ...], aliases: dict) -> list[tuple[str, str, str]]:
        """(prefix, name, scope id) of each variable `token` reads."""
        if not token or ":" not in token:
            return []
        out = []
        cur = scopes[-1]
        idx = len(scopes) - 1
        for seg in token.split("."):
            m = _SEG_VAR_RE.match(seg)
            low = seg.lower()
            if m:
                prefix = m.group(1).lower()
                out.append((prefix, m.group(2), GLOBAL_SCOPE if prefix == "global_var" else cur))
                cur = cur + "/" + seg
            elif low == "root":
                cur = scopes[0]
            elif low == "prev":
                idx -= 1
                cur = scopes[idx] if idx >= 0 else "?prev"
            elif low == "this":
                pass
            elif low.startswith("scope:"):
                cur = aliases.get(seg[6:], "scope:" + seg[6:])
            elif ":" in seg:
                cur = seg  # c:FRA, s:STATE_X, local_var:x, ...: another object
            else:
                cur = cur + "/" + seg
        return out

    def _scope_of(self, key: str, scopes: tuple[str, ...], aliases: dict) -> str:
        cur = scopes[-1]
        idx = len(scopes) - 1
        for seg in key.split("."):
            low = seg.lower()
            if low == "root":
                cur = scopes[0]
            elif low == "prev":
                idx -= 1
                cur = scopes[idx] if idx >= 0 else "?prev"
            elif low == "this":
                pass
            elif low.startswith("scope:"):
                cur = aliases.get(seg[6:], "scope:" + seg[6:])
            elif ":" in seg:
                cur = cur + "/" + seg if low.startswith(("var:", "global_var:")) else seg
            else:
                for p in vga.ITERATOR_PREFIXES:
                    if low.startswith(p):
                        seg = "*" + seg[len(p):]
                        break
                cur = cur + "/" + seg
        return cur

    def _read(self, token, origin, line, file, kind, st) -> None:
        for prefix, name, sid in self._chain_reads(token, st["scopes"], st["aliases"]):
            if "$" in name or self.keepers.kept(prefix, name):
                continue  # other code keeps it set: never flagged
            rfile, rline = origin if origin else (file, line)
            kind = st.get("read_kind") or kind
            r = _Read(rfile, rline, prefix, name, kind, None, st["chain"], origin is not None)
            self._check(r, (sid, prefix, name), st)

    def _check(self, r: _Read, key: tuple, st) -> None:
        """A read flags when this frame wrote the name earlier; otherwise it is
        handed to the caller's frame, which checks it against what it wrote
        before the call. A read behind a guard on its own name is safe."""
        if (key[1], key[2]) in st["guarded"]:
            return
        at = st["sets"].get(key)
        if at is not None:
            r.set_at = at
            self.reads.append(r)
        elif key not in st["removed"] and st["ext"] is not None:
            st["ext"].append((key, r))

    @staticmethod
    def _fork(st) -> dict:
        """A copy of the walk state for a block of its own: guards found inside
        it do not reach past it."""
        new = dict(st)
        new["guarded"] = set(st["guarded"])
        return new

    def _guard(self, key: str, value: str | None, st) -> bool:
        """`has_variable = V` / `exists = var:V`: True when the guard is false
        in the walk (V is a scratch name, or a scope the walk never made).
        Otherwise V may be set, and a read of V behind the guard is safe:
        V joins `st["guarded"]` for the rest of the block."""
        if not value:
            return False
        if key == "exists" and value.startswith("scope:") and "." not in value:
            return st["aliases"].get(value[6:]) == UNSET
        if key in GUARD_KEYS:
            var = (GUARD_KEYS[key], value)
        elif key == "exists":
            reads = self._chain_reads(value, st["scopes"], st["aliases"])
            if not reads:
                return False
            var = (reads[-1][0], reads[-1][1])
        else:
            return False
        if "$" in var[1]:
            return False
        if self.keepers.scratch(*var):
            return True
        if not st.get("no_guard"):
            st["guarded"].add(var)
        return False

    def _call(self, d: Def, params: dict, st, line: int, file: str, ctx: str):
        if d.name in st["stack"] or len(st["stack"]) >= MAX_DEPTH:
            return None
        rkey = ("relevant", d.kind, d.name, ctx, tuple(sorted((k, v[0]) for k, v in params.items())))
        relevant = self.cache.get(rkey)
        reads, writes, guards, named = self.mod.summary(d)
        if relevant is None:
            relevant = self.cache[rkey] = self._relevant(
                reads, writes, guards if ctx != "effect" else (), params)
        if not relevant:
            return None  # it can neither read, write nor test a name nothing keeps
        # The call is walked once for its arguments, scope and the scopes named
        # so far, from an empty frame, across roots (a refresh many options
        # call is walked once). What it reads but did not write itself is
        # checked here against what the caller wrote before the call.
        if any("$" in n for n in named):
            aliases = frozenset(st["aliases"].items())
        else:
            aliases = frozenset((k, v) for k, v in st["aliases"].items() if k in named)
        key = (d.kind, d.name, ctx, tuple(sorted(params.items())), st["scopes"], aliases,
               st.get("read_kind"), bool(st.get("creating")), bool(st.get("no_guard")))
        hit = self.cache.get(key)
        base_chain = st["chain"]
        if hit is None:
            n_reads = len(self.reads)
            before_alias = dict(st["aliases"])
            sub = self._fork(st)
            sub.update(params=params, stack=st["stack"] + (d.name,), chain=(d.name,), file=d.file,
                       sets={}, removed=set(), ext=[], guarded=set())
            if d.kind == "value":
                sub["read_kind"] = "value"
            if ctx == "effect":
                self.effect_body(d.node.children, sub)
                result = None
            else:
                result = self.trigger_and(d.node.children, sub)
            alias_delta = {k: v for k, v in st["aliases"].items() if before_alias.get(k) != v}
            inner = self.reads[n_reads:]
            del self.reads[n_reads:]
            # A scripted trigger's own guards hold for the caller's block too.
            guards = frozenset(sub["guarded"]) if ctx != "effect" else frozenset()
            hit = (inner, sub["ext"], sub["sets"], sub["removed"], alias_delta, result, guards)
            self.cache[key] = hit
        inner, ext, added, removed, alias_delta, result, guards = hit
        # A read inside a script value is reported where the value is named:
        # the one place a guard or a review can go (the value's own lines are
        # shared, and often generated).
        at = (file, line) if d.kind == "value" and st.get("read_kind") != "value" else None
        for r in inner:
            if (r.prefix, r.name) in st["guarded"]:
                continue  # the caller's guard on the name covers the call
            self.reads.append(_Read(*(at or (r.file, r.line)), r.prefix, r.name, r.kind, r.set_at,
                                    base_chain + r.chain, r.via_argument))
        for k, r in ext:
            self._check(_Read(*(at or (r.file, r.line)), r.prefix, r.name, r.kind, None,
                              base_chain + r.chain, r.via_argument), k, st)
        if added or removed:
            new = {k: v for k, v in st["sets"].items() if k not in removed}
            for k, v in added.items():
                new.setdefault(k, v)
            st["sets"] = new
            st["removed"] = (st["removed"] - set(added)) | removed
        st["aliases"].update(alias_delta)
        if guards and not st.get("no_guard"):
            st["guarded"] |= guards
        return result

    def _relevant(self, reads, writes, guards, params) -> bool:
        """Could a call with these static names matter? It does if it may read
        a name some walk could have written (`Keepers.volatile`: a name
        written somewhere that nothing keeps), or write or test one."""
        pool = self.keepers.volatile
        vals = {k: v[0] for k, v in params.items()}
        for n in list(reads) + list(writes) + list(guards):
            if n == "$":
                return True  # a call through a parameterised name: anything
            if "$" in n:
                n = _PARAM_RE.sub(lambda m: vals.get(m.group(1), m.group(0)), n)
            if "$" in n:
                if self.keepers.fits_volatile(n):
                    return True
                continue
            if ":" in n or "." in n:
                # An argument as passed (`global_var:x`, `scope:y.var:z`).
                if any(m.group(1) in pool for m in re.finditer(r"var:([A-Za-z0-9_\-]+)", n)):
                    return True
                continue
            if n in pool:
                return True
            d = self.mod.defs["value"].get(n)
            if d is not None and self._relevant(*self.mod.summary(d)[:3], {}):
                return True
        return False

    def _params_of(self, node: vga.Node, st) -> dict:
        out = {}
        for c in node.children:
            if c[0] == "scalar" and c[3] is not None:
                val = c[3]
                m = re.fullmatch(r"\$(\w+)\$", val)
                if m and m.group(1) in st["params"]:
                    out[c[1]] = st["params"][m.group(1)]  # forwarded: keep the first origin
                else:
                    v, _o = self._sub(val, st["params"])
                    out[c[1]] = (v, st["file"], c[4])
        return out

    def _value_names(self, value, line, st) -> None:
        """A scalar's value that names a script value: walk it for reads."""
        d = self.mod.defs["value"].get(value) if value else None
        if d is not None:
            self._call(d, {}, st, line, st["file"], "trigger")

    # -- effects ----------------------------------------------------------

    def effect_body(self, children, st, skip=frozenset()) -> None:
        chain_base = None
        chain_out: list[dict] = []

        def close_chain():
            nonlocal chain_base, chain_out
            if chain_base is not None:
                merged = dict(chain_base)
                for o in chain_out:
                    merged.update(o)
                st["sets"] = merged
            chain_base, chain_out = None, []

        for child in children:
            if child[0] == "block":
                node = child[1]
                key, _o = self._sub(node.key, st["params"])
                if key in skip:
                    continue
                if key in CHAIN_KEYS:
                    if key == "if" or chain_base is None:
                        close_chain()
                        chain_base = dict(st["sets"])
                    branch = self._fork(st)
                    branch["sets"] = dict(chain_base)
                    self.block_with_limit(node.children, branch)
                    chain_out.append(branch["sets"])
                    if key == "else":
                        close_chain()
                    continue
                close_chain()
                if key == "limit":
                    if self.trigger_and(node.children, st) is False:
                        return
                    continue
                self.effect_block(node, key, st)
            else:
                close_chain()
                if child[0] == "scalar":
                    self.effect_scalar(child, st)
        close_chain()

    def block_with_limit(self, children, st) -> None:
        """A block whose `limit` gates the rest (an `if`, an iterator)."""
        self.effect_body(children, st)

    def effect_scalar(self, child, st) -> None:
        _, rkey, op, rvalue, line = child
        key, korigin = self._sub(rkey, st["params"])
        value, vorigin = self._sub(rvalue, st["params"])
        file = st["file"]
        scope = st["scopes"][-1]
        if key in WRITE_KEYS and value:
            prefix = WRITE_KEYS[key]
            if self.keepers.kept(prefix, value):
                return  # other code keeps it set: no read of it is flagged
            st["sets"].setdefault((GLOBAL_SCOPE if prefix == "global_var" else scope, prefix, value),
                                  (file, line))
            return
        if key in REMOVE_KEYS and value:
            prefix = REMOVE_KEYS[key]
            k = (GLOBAL_SCOPE if prefix == "global_var" else scope, prefix, value)
            st["sets"].pop(k, None)
            st["removed"].add(k)
            return
        if key in SAVE_SCOPE_KEYS and value:
            st["aliases"][value] = UNSET if st.get("creating") else scope
            return
        d = self.mod.defs["effect"].get(key)
        if d is not None:
            if value != "no":
                self._call(d, {}, st, line, file, "effect")
            return
        if key in NAME_KEYS:
            return
        if op != "?=":
            self._read(key, korigin, line, file, "value", st)
        self._read(value, vorigin, line, file, "switch trigger" if key == "trigger" else "value", st)
        self._value_names(value, line, st)

    def effect_block(self, node: vga.Node, key: str, st) -> None:
        file = st["file"]
        if key in DISPLAY_ONLY:
            return
        if key in WRITE_KEYS:
            # The value is read first, then the name written.
            self.effect_body([c for c in node.children if not (c[0] == "scalar" and c[1] == "name")], st)
            name = _name_of(node)
            name, _o = self._sub(name, st["params"])
            if name and not self.keepers.kept(WRITE_KEYS[key], name):
                prefix = WRITE_KEYS[key]
                sid = GLOBAL_SCOPE if prefix == "global_var" else st["scopes"][-1]
                st["sets"].setdefault((sid, prefix, name), (file, node.line))
            return
        d = self.mod.defs["effect"].get(key)
        if d is not None:
            self._call(d, self._params_of(node, st), st, node.line, file, "effect")
            return
        if key in ("switch", "random_list"):
            base = dict(st["sets"])
            outs = []
            for c in node.children:
                if c[0] == "scalar":
                    self.effect_scalar(c, st)
                    base = dict(st["sets"])
                elif c[0] == "block":
                    branch = self._fork(st)
                    branch["sets"] = dict(base)
                    self.effect_body(c[1].children, branch)
                    outs.append(branch["sets"])
            for o in outs:
                st["sets"].update(o)
            return
        if node.op != "?=":
            self._read(node.key, None, node.line, file, "scope", st)
        if key in CREATE_KEYS:
            inner = self._fork(st)
            inner["creating"] = True
            inner["scopes"] = st["scopes"] + ("<created>",)
            self.effect_body(node.children, inner)
            st["sets"], st["removed"] = inner["sets"], inner["removed"]
            return
        if vga._is_scope_change(key, self.links):
            sid = self._scope_of(key, st["scopes"], st["aliases"])
            if sid == UNSET:
                return  # a scope the walk never made: nothing runs in it
            inner = self._fork(st)
            inner["scopes"] = st["scopes"] + (sid,)
            self.effect_body(node.children, inner)
            st["sets"], st["removed"] = inner["sets"], inner["removed"]
            return
        # Any other block (`hidden_effect`, `custom_tooltip`, `while`, a value
        # block): a guard in its own `limit` does not reach past it.
        inner = self._fork(st)
        self.effect_body(node.children, inner)
        st["sets"], st["removed"] = inner["sets"], inner["removed"]

    # -- triggers ---------------------------------------------------------

    def _negated_guards(self, child, st) -> set:
        """The variables a `NOT = { has_variable = x }` (or a `NOR` of such
        guards) tests; empty for any other child."""
        if child[0] != "block" or (child[1].key or "").upper() not in ("NOT", "NOR"):
            return set()
        out = set()
        for c in child[1].children:
            if c[0] != "scalar" or c[2] != "=" or not c[3]:
                return set()
            key, value = c[1], self._sub(c[3], st["params"])[0]
            if key in GUARD_KEYS and "$" not in value:
                out.add((GUARD_KEYS[key], value))
            elif key == "exists":
                reads = self._chain_reads(value, st["scopes"], st["aliases"])
                if not reads:
                    return set()
                out.add((reads[-1][0], reads[-1][1]))
            else:
                return set()
        return out

    def trigger_and(self, children, st, stop=True):
        """Walk a trigger block's children in order. False when the walk knows
        the block is false (a guard on a scratch name), else None.
        `stop`: an AND stops at its first false child."""
        for child in children:
            r = self.trigger_child(child, st)
            if r is False and stop:
                return False
        return None

    def trigger_child(self, child, st):
        file = st["file"]
        if child[0] == "scalar":
            _, rkey, op, rvalue, line = child
            key, korigin = self._sub(rkey, st["params"])
            value, vorigin = self._sub(rvalue, st["params"])
            if op == "=" and self._guard(key, value, st):
                return False
            if op == "=" and st["scopes"][-1] == ROOT_SCOPE and (
                    (key == "is_ai" and value == "yes") or (key == "is_player" and value == "no")):
                return False  # only a player sees a tooltip: an AI-only branch is not walked
            if key in GUARD_KEYS or key == "exists":
                return None
            d = self.mod.defs["trigger"].get(key)
            if d is not None:
                r = self._call(d, {}, st, line, file, "trigger")
                return r if value != "no" else None
            if key in NAME_KEYS:
                return None
            if op != "?=":
                self._read(key, korigin, line, file, "limit", st)
            self._read(value, vorigin, line, file, "limit", st)
            self._value_names(value, line, st)
            return None
        if child[0] != "block":
            return None
        node = child[1]
        key, _o = self._sub(node.key, st["params"])
        if key in DISPLAY_ONLY:
            return None
        upper = (key or "").upper()
        if upper in ("AND", "LIMIT") or key is None:
            return self.trigger_and(node.children, st)
        if upper == "OR":
            # An OR stops at its first true child, so after
            # `NOT = { has_variable = x }` its later children run only when x
            # is set: they may read it (`nd_taboo_effective_ceiling_value`).
            orst = self._fork(st)
            results = []
            for c in node.children:
                results.append(self.trigger_child(c, self._fork(orst)))
                orst["guarded"] |= self._negated_guards(c, orst)
            return False if results and all(r is False for r in results) else None
        if upper in ("NOT", "NOR", "NAND"):
            # A multi-child NOT reads every child: a guard there guards nothing.
            inner = self._fork(st)
            inner["no_guard"] = True
            self.trigger_and(node.children, inner, stop=False)
            return None
        if key in ("trigger_if", "trigger_else_if", "if", "else_if"):
            st = self._fork(st)
            rest = []
            for c in node.children:
                if c[0] == "block" and c[1].key == "limit":
                    if self.trigger_and(c[1].children, st) is False:
                        return None
                else:
                    rest.append(c)
            return self.trigger_and(rest, st)
        d = self.mod.defs["trigger"].get(key)
        if d is not None:
            return self._call(d, self._params_of(node, st), st, node.line, file, "trigger")
        if node.op != "?=":
            self._read(node.key, None, node.line, file, "limit", st)
        if vga._is_scope_change(key, self.links):
            iterator = (key or "").startswith(vga.ITERATOR_PREFIXES)
            # A guard behind a link (`root = { has_variable = x }`) guards
            # the enclosing block's reads (`root.var:x`); one in an iterator
            # tested other objects.
            inner = self._fork(st) if iterator else dict(st)
            inner["scopes"] = st["scopes"] + (self._scope_of(key, st["scopes"], st["aliases"]),)
            r = self.trigger_and(node.children, inner)
            return None if iterator else r
        self.trigger_and(node.children, self._fork(st), stop=False)
        return None

    # -- entry ------------------------------------------------------------

    def can_flag(self, root: Root) -> bool:
        """False when nothing the root reaches writes a name nothing keeps:
        no read in its walk can follow a write, so it needs no walk."""
        node = vga.Node(None, None, root.line)
        node.children = list(root.node.children) + (list(root.after.children) if root.after else [])
        _r, writes, _g, _s = self.mod.summary(Def("root", f"{root.file}:{root.line}", root.file, node))
        pool = self.keepers.volatile
        for n in writes:
            if n == "$" or ("$" in n and self.keepers.fits_volatile(n)) or n in pool:
                return True
        return False

    def walk(self, root: Root) -> None:
        st = {
            "sets": {}, "scopes": (ROOT_SCOPE,), "aliases": {}, "params": {},
            "stack": (), "chain": (), "file": root.file, "removed": set(), "ext": None,
            "guarded": set(),
        }
        children = list(root.node.children)
        if root.after is not None:
            children += root.after.children
        self.effect_body(children, st, root.skip)


# ---------------------------------------------------------------------------
# The audit
# ---------------------------------------------------------------------------


def read_tags(mod_path: str) -> dict[tuple[str, int], dict]:
    """{(file, line): {date, rationale}} for every `(tooltip_walk)` tag."""
    tags: dict[tuple[str, int], dict] = {}
    for path, rel in _files(mod_path):
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        if CHECK not in text:
            continue
        for lineno, raw in enumerate(text.splitlines(), 1):
            if "REVIEWED" not in raw:
                continue
            m = _TAGGED_REVIEWED_RE.search(raw)
            if m and CHECK in re.split(r"[\s,]+", m.group("checks").strip()):
                tags[(rel, lineno)] = {"date": m.group("date"), "rationale": m.group("rationale").strip()}
    return tags


def _root_label(r: Root) -> str:
    return {"sgui": "scripted GUI", "button": "button", "decision": "decision"}.get(r.kind, "") + (
        " " if r.kind != "option" else "") + f"`{r.label}`"


def audit(mod_state=None, mod_path: str | None = None, only_root: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_AUDITS `regenerate(mod_state)` contract. `only_root` walks the
    roots whose label starts with it (an sgui, an event id, a decision)."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    mod = Mod(mod_path)
    keepers = Keepers(mod)
    links = vga.load_scope_links(mod_path)
    result = AuditResult()
    cache: dict = {}
    by_read: dict[tuple[str, int, str, str], Flag] = {}
    for root in mod.roots:
        if only_root and not (root.label == only_root or root.label.startswith(only_root + " ")):
            continue
        result.roots += 1
        w = Walker(mod, keepers, links, cache)
        if not w.can_flag(root):
            continue
        w.walk(root)
        seen: set = set()
        for r in w.reads:
            key = (r.file, r.line, r.prefix, r.name)
            if key in seen:
                continue
            seen.add(key)
            f = by_read.get(key)
            if f is None:
                f = by_read[key] = Flag(r.file, r.line, f"{r.prefix}:{r.name}", r.kind,
                                        f"{r.set_at[0]}:{r.set_at[1]}", chain=list(r.chain),
                                        via_argument=r.via_argument)
            f.roots.append(_root_label(root))
    result.flags = sorted(by_read.values(), key=lambda f: (f.file, f.line, f.variable))

    tags = read_tags(mod_path)
    used: set = set()
    for f in result.flags:
        f.exemption = tags.get((f.file, f.line))
        if f.exemption:
            used.add((f.file, f.line))
    if not only_root:
        result.stale_tags = [StaleTag(file, line) for (file, line) in sorted(tags) if (file, line) not in used]
    return result


def describe(f: Flag) -> str:
    roots = ", ".join(f.roots[:3]) + (f" and {len(f.roots) - 3} more" if len(f.roots) > 3 else "")
    chain = (" through " + " → ".join(f"`{c}`" for c in f.chain)) if f.chain else ""
    arg = " (passed as an argument)" if f.via_argument else ""
    return (f"`{f.variable}` read as a {f.kind}{arg}, written at `{f.set_at}` earlier in the walk of "
            f"{roots}{chain}")


def flag_dict(f: Flag) -> dict:
    return {"file": f.file, "line": f.line, "variable": f.variable, "kind": f.kind, "set_at": f.set_at,
            "roots": f.roots, "chain": f.chain, "via_argument": f.via_argument, "reviewed": f.exemption}


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Tooltip walk variable audit report",
        "",
        "Auto-generated by `tooltip_walk_variable_audit.py` on every `POST /reload`",
        "of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a read of a variable that an earlier `set_variable` in the same",
        "effect body wrote, in a body a tooltip walks (a scripted GUI's or a",
        "button's `effect`, an event option, a decision's `when_taken`). The walk",
        "writes nothing, so the read finds the variable unset and logs every frame",
        "the tooltip shows (#918). Variables some code outside a tooltip keeps set",
        "are left out.",
        "",
        "Fix: compare the values directly, read a variable that persists, guard the",
        "read with `has_variable`, or put the body behind a click-only marker",
        "(`docs/guides/scripting_best_practices.md` § \"An Option's Tooltip Walks",
        "Its Effects\"). Where the read is provably safe, say why on the read line",
        "(for a `$PARAM$` argument, the line of the call that passes it):",
        f"`# REVIEWED YYYY-MM-DD ({CHECK}): why`",
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
        out += ["## Stale tags", "", "Tags on a line with no flag; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` ({CHECK})" for t in result.stale_tags]
        out.append("")
    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        # No line numbers: an edit above the read would churn the report.
        out += [f"- `{f.file}` — `{f.variable}` — **{f.exemption['date']}**: {f.exemption['rationale']}"
                for f in exemp]
        out.append("")
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
    out_path = os.path.join(mod_path, REPORT)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        # Flags without a tag, plus tags on a line with no flag.
        "unreviewed": result.failing,
        "total_flags": len(result.flags),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "stale_tags": len(result.stale_tags),
        "roots": result.roots,
        "path": out_path,
    }


def main(argv: list[str], mod_path: str | None = None) -> int:
    if mod_path is None:
        from path_constants import mod_path
    only = None
    if "--root" in argv:
        i = argv.index("--root")
        if i + 1 >= len(argv):
            raise SystemExit("--root needs a scripted GUI, an event id or a decision")
        only = argv[i + 1]
    res = audit(mod_path=mod_path, only_root=only)
    if only:
        for f in res.flags:
            mark = "reviewed" if f.exemption else "UNREVIEWED"
            print(f"{f.file}:{f.line} [{mark}] {describe(f)}")
        if not res.flags:
            print(f"no flagged read in the walk of {only} ({res.roots} root(s) walked)")
    else:
        print(render_report(res))
    # --strict: CI mode. Exit 1 if any flag lacks its check-tagged
    # `# REVIEWED` comment, or any such tag sits on a line with no flag.
    return 1 if "--strict" in argv and res.failing else 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    raise SystemExit(main(sys.argv[1:]))
