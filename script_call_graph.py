"""The mod's script call graph: which event, scripted effect or other entity
runs which scripted effect, and fires which event.

A small layer over `event_context_audit.build_graph`, which already walks every
script file for `trigger_event` sites and scripted-effect calls (with each
call's arguments and block path, and `$EVENT$` ids resolved at each caller).
This module turns that into a forward graph with typed edges, and adds the
graph questions an audit asks: what does this entity reach, which nodes lie on
a cycle, what is the shortest cycle through this edge.

Users: `trigger_event_cycle_audit` (#1012), and `tooltip_walk_variable_audit`
(#918), which asks which scripted effects are reached from somewhere that is
not a tooltip root (an on-action, a journal entry, an event's `immediate`).

Nodes
-----
`Node(kind, name)`. `kind` is `event_context_audit`'s entity kind: `event`,
`scripted_effect`, `on_action`, `journal_entry`, `decision`, `button`, ...
Only events and scripted effects can be entered from script, so only they can
lie on a cycle; every other kind is a root.

Edges
-----
* `call`: the entity's body calls a scripted effect. `params` holds the
  call's depth-1 arguments. A dispatcher call (`helper_$KIND$ = yes`) becomes
  an edge from the caller that names the parameter's value to the effect that
  value picks, with the dispatching helper in `through` (`dispatch = True`).
  So is a bare `$EFFECT$ = yes`, to each effect a caller names; a caller whose
  value is no effect's name (`WHO = scope:x` for a `$WHO$ = { … }` block)
  adds no edge.
* `event`: the entity fires an event, by `trigger_event` (`via`) or an
  on-action's `events` / `random_events` / `first_valid` list. `delayed` is
  True for a `trigger_event` with a `days` / `weeks` / `months` / `years`
  other than a literal 0 (a range reads as its first value; a `$DAYS$` as
  its caller's, and as no delay when some caller passes 0). `id = "ns.2"` is
  `ns.2`. An id passed as a parameter
  (`trigger_event = { id = $EVENT$ }`) is an edge from the **caller that names
  the event**, at the caller's line, with the helper that holds the
  `trigger_event` in `through`. A literal id is an edge from the entity that
  holds the `trigger_event`, at its line, whatever scope parameter surrounds
  it.
* `on_action`: an on-action lists another under `on_actions = { }`.

A definition under a merge directive (`REPLACE:x`, `INJECT:x`, ...) is node
`x` (`event_context_audit.build_graph(strip_directives=True)`).

What the graph does not hold: an effect that makes the engine run other
script at once (`activate_law` runs `on_law_activated` inside the effect, and
`add_journal_entry` the entry's `immediate`), calls from scripted triggers and
script values (neither can fire an event), and anything in a block that is
only described, never run (`map_tooltip`, a journal entry's
`event_outcome_effect_desc`). A `custom_tooltip = { text = … <effects> }`
runs its effects, so those are edges.

Raw text, like the scanner under it: both report file and line, which
`paradox_file_parser` drops.
"""
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Iterable, NamedTuple

EVENT = "event"
EFFECT = "scripted_effect"
ON_ACTION = "on_action"


class Node(NamedTuple):
    kind: str
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Edge:
    src: Node
    dst: Node
    kind: str  # "call", "event" or "on_action"
    file: str  # mod-relative
    line: int
    path: tuple[str, ...] = ()  # block keys from the source's top level to the line
    delayed: bool = False  # event edges: queued, not run inside the caller
    via: str = ""  # event edges: trigger_event | events | random_events | first_valid
    # Where a parameter was resolved at a caller: for an event edge, the
    # helper that holds the `trigger_event`; for a dispatched call, the helpers
    # the name was passed through, the one the source calls first.
    through: tuple[str, ...] = ()
    params: tuple[tuple[str, str], ...] = ()  # call edges: depth-1 arguments
    dispatch: bool = False  # call edges: reached through a `helper_$X$` name

    @property
    def in_option(self) -> bool:
        return "option" in self.path

    @property
    def random(self) -> bool:
        return any(k in ("random", "random_list") for k in self.path)


EdgeFilter = Callable[[Edge], bool]


def runs_at_once(e: Edge) -> bool:
    """The edges the engine follows inside the running effect: every call, and
    every event fired with no delay."""
    return e.kind == "call" or (e.kind == "event" and not e.delayed)


@dataclass
class CallGraph:
    nodes: dict[Node, tuple[str, int]] = field(default_factory=dict)  # -> (file, line); line 0 unknown
    edges: list[Edge] = field(default_factory=list)
    out: dict[Node, list[Edge]] = field(default_factory=dict)

    def add_node(self, node: Node, file: str = "", line: int = 0) -> None:
        if node not in self.nodes or (file and not self.nodes[node][0]):
            self.nodes[node] = (file, line)

    def add_edge(self, edge: Edge) -> None:
        self.add_node(edge.src)
        self.add_node(edge.dst)
        self.edges.append(edge)
        self.out.setdefault(edge.src, []).append(edge)

    def edges_from(self, node: Node, keep: EdgeFilter | None = None) -> list[Edge]:
        return [e for e in self.out.get(node, ()) if keep is None or keep(e)]

    def callees(self, node: Node) -> list[Edge]:
        """The scripted effects `node`'s own body calls."""
        return self.edges_from(node, lambda e: e.kind == "call")

    def reachable(self, start: Node, keep: EdgeFilter | None = None) -> set[Node]:
        """Every node a walk from `start` gets to (not `start` itself, unless a
        cycle returns to it)."""
        seen: set[Node] = set()
        todo = deque([start])
        while todo:
            for e in self.edges_from(todo.popleft(), keep):
                if e.dst not in seen:
                    seen.add(e.dst)
                    todo.append(e.dst)
        return seen

    def components(self, keep: EdgeFilter | None = None) -> dict[Node, int]:
        """{node: component number} for every node on a cycle of kept edges:
        the strongly connected components with more than one node, and single
        nodes with an edge to themselves. Tarjan's algorithm, iterative (the
        mod's longest call chain is deeper than is comfortable to recurse)."""
        index: dict[Node, int] = {}
        low: dict[Node, int] = {}
        on_stack: set[Node] = set()
        stack: list[Node] = []
        out: dict[Node, int] = {}
        count = 0
        n_comp = 0
        for root in sorted(self.nodes):
            if root in index:
                continue
            work: list[tuple[Node, Iterable[Edge]]] = []

            def push(v: Node) -> None:
                nonlocal count
                index[v] = low[v] = count
                count += 1
                stack.append(v)
                on_stack.add(v)
                work.append((v, iter(self.edges_from(v, keep))))

            push(root)
            while work:
                v, it = work[-1]
                advanced = False
                for e in it:
                    w = e.dst
                    if w not in index:
                        push(w)
                        advanced = True
                        break
                    if w in on_stack:
                        low[v] = min(low[v], index[w])
                if advanced:
                    continue
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[v])
                if low[v] == index[v]:
                    comp = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        comp.append(w)
                        if w == v:
                            break
                    if len(comp) > 1 or any(e.dst == v for e in self.edges_from(v, keep)):
                        for w in comp:
                            out[w] = n_comp
                        n_comp += 1
        return out

    def shortest_path(self, src: Node, dst: Node, keep: EdgeFilter | None = None,
                      within: set[Node] | None = None) -> list[Edge] | None:
        """The fewest kept edges from `src` to `dst` (at least one, so
        `src == dst` asks for a cycle), or None. `within` confines the walk."""
        prev: dict[Node, Edge] = {}
        todo = deque([src])
        while todo:
            v = todo.popleft()
            for e in self.edges_from(v, keep):
                w = e.dst
                if within is not None and w not in within:
                    continue
                if w == dst:
                    path = [e]
                    while path[0].src != src:
                        path.insert(0, prev[path[0].src])
                    return path
                if w not in prev and w != src:
                    prev[w] = e
                    todo.append(w)
        return None


_PARAM_RE = re.compile(r"\$(\w+)\$")
_LITERAL_RE = re.compile(r"^[A-Za-z0-9_]*$")


def _name_pattern(name: str) -> re.Pattern:
    literal = _PARAM_RE.split(name)[::2]
    return re.compile("^" + "[A-Za-z0-9_]+".join(re.escape(p) for p in literal) + "$")


def _dispatch_edges(g) -> list[Edge]:
    """Call edges through a parameterised name (`nd_crisis_act_$ACT$ = yes`
    inside `nd_crisis_option`). Each is resolved where the parameter's value is
    written: `nd_crisis_option = { ACT = reject }` in an event option is an
    edge from that event to `nd_crisis_act_reject`, through `nd_crisis_option`,
    so an event reaches only the acts its own options name. A caller that
    forwards the parameter (`ACT = $ACT$`) is followed to its callers. Where
    no caller names an effect (no call site, or no value that is a name), the
    helper gets an edge to every scripted effect the name's pattern fits."""
    names = set(g.effect_file)
    out: list[Edge] = []
    seen: set[tuple] = set()

    def emit(src: Node, target: str, rel: str, ln: int, path, through: tuple[str, ...]) -> bool:
        if target not in names:
            return False
        key = (src, target, rel, ln)
        if key not in seen:
            seen.add(key)
            out.append(Edge(src, Node(EFFECT, target), "call", rel, ln, tuple(path),
                            through=through, dispatch=True))
        return True

    def by_pattern(template: str, holder: str, rel: str, ln: int, path, through) -> bool:
        pattern = _name_pattern(template)
        hit = False
        for n in sorted(names):
            if pattern.match(n):
                hit = emit(Node(EFFECT, holder), n, rel, ln, path, through) or hit
        return hit

    def resolve(template: str, holder: str, rel: str, ln: int, path, through: tuple[str, ...],
                depth: int) -> bool:
        """True when some caller of `holder` gave the name an effect."""
        callers = g.effect_calls.get(holder, []) if holder in names else []
        hit = False
        if depth <= 6:
            for (crel, cln, cpk, _sw, _conds, centity, ckind, cparams) in callers:
                if any(p not in cparams for p in _PARAM_RE.findall(template)):
                    continue  # `helper = yes`: this caller passes no value
                sub = _PARAM_RE.sub(lambda m: cparams[m.group(1)], template)
                if "$" not in sub:
                    hit = emit(Node(ckind, centity), sub, crel, cln, cpk, (holder,) + through) or hit
                elif ckind == EFFECT and _LITERAL_RE.match(_PARAM_RE.sub("", sub) or "_"):
                    hit = resolve(sub, centity, crel, cln, cpk, (holder,) + through, depth + 1) or hit
        # No caller names an effect (none calls it, or none passes a name):
        # every effect the pattern fits, from where the name is written. Not
        # for a bare `$EFFECT$`, which fits every name; its key also holds the
        # `$WHO$ = { … }` scope blocks, so only a caller's value makes it a call.
        if hit or not _PARAM_RE.sub("", template):
            return hit
        return by_pattern(template, holder, rel, ln, path, through)

    for key, calls in g.effect_calls.items():
        if "$" not in key:
            continue
        for (rel, ln, pk, _sw, _conds, entity, _kind, _params) in calls:
            resolve(key, entity, rel, ln, pk, (), 0)
    return out


def _a_caller_fills_zero(g, s, depth: int = 0) -> bool:
    """A `trigger_event = { id = ns.2 days = $DAYS$ }` left in its helper (the
    id is literal, so the site did not move to the callers): undelayed when
    some caller passes 0, or forwards `DAYS = $DAYS$` from a caller that does.
    A site that moved already carries its caller's value."""
    if s.entity_kind != EFFECT or not any("$" in d for d in s.delays) or depth > 6:
        return False
    import event_context_audit as eca

    for (_rel, _ln, _pk, _sw, _conds, entity, kind, params) in g.effect_calls.get(s.entity, []):
        delays = tuple(_PARAM_RE.sub(lambda m: params.get(m.group(1), m.group(0)), d) for d in s.delays)
        if not eca._is_delay(delays):
            return True
        if kind == EFFECT and any("$" in d for d in delays) and _a_caller_fills_zero(
                g, eca.Site(s.event, s.file, s.line, entity, kind, [], [], "", s.via, True,
                            delays=delays), depth + 1):
            return True
    return False


def _add_calls(cg: CallGraph, effect_calls: dict) -> None:
    for callee, calls in effect_calls.items():
        if "$" in callee:
            continue  # a dispatcher call: `_dispatch_edges`
        for (rel, ln, pk, _sw, _conds, entity, kind, params) in calls:
            cg.add_edge(Edge(Node(kind, entity), Node(EFFECT, callee), "call", rel, ln, tuple(pk),
                             params=tuple(sorted(params.items()))))


def calls_only(effect_file: dict[str, str], effect_calls: dict) -> CallGraph:
    """The call edges alone, plain and dispatched, from
    `event_context_audit`'s `effect_calls` ({callee: [call, ...]}, as its
    `scan_file` gives them) and `effect_file` ({effect: file}): what
    `from_event_graph` holds without the events. For a caller that keeps the
    per-file scans between runs (`tooltip_walk_variable_audit`)."""
    from types import SimpleNamespace

    cg = CallGraph()
    for name, rel in effect_file.items():
        cg.add_node(Node(EFFECT, name), rel)
    _add_calls(cg, effect_calls)
    for e in _dispatch_edges(SimpleNamespace(effect_file=effect_file, effect_calls=effect_calls)):
        cg.add_edge(e)
    return cg


def from_event_graph(g) -> CallGraph:
    """Build the forward graph from an `event_context_audit.Graph`."""
    cg = CallGraph()
    for eid, ev in g.events.items():
        cg.add_node(Node(EVENT, eid), ev.file, ev.line)
    for name, rel in g.effect_file.items():
        cg.add_node(Node(EFFECT, name), rel)
    for name, files in g.on_action_files.items():
        cg.add_node(Node(ON_ACTION, name), files[0] if files else "")

    _add_calls(cg, g.effect_calls)

    seen: set[tuple] = set()
    for raw_id, sites in g.sites_by_event.items():
        eid = raw_id.strip('"')  # `id = "ns.2"` is `ns.2`
        for s in sites:
            delayed = s.delayed and not _a_caller_fills_zero(g, s)
            if s.origin and not s.param_event:
                # A literal id inside `$WHO$ = { … }`: one edge, where the
                # `trigger_event` is written, not one per caller.
                file, line, entity = s.origin
                edge = Edge(Node(EFFECT, entity), Node(EVENT, eid), "event", file, line,
                            delayed=delayed, via=s.via)
            else:
                edge = Edge(Node(s.entity_kind, s.entity), Node(EVENT, eid), "event", s.file, s.line,
                            tuple(s.path), delayed=delayed, via=s.via,
                            through=(s.origin[2],) if s.origin else ())
            key = (edge.src, edge.dst, edge.file, edge.line, edge.delayed)
            if key not in seen:
                seen.add(key)
                cg.add_edge(edge)

    for child, parents in g.on_action_parents.items():
        for (parent, ln, rel) in parents:
            cg.add_edge(Edge(Node(ON_ACTION, parent), Node(ON_ACTION, child), "on_action", rel, ln))

    for e in _dispatch_edges(g):
        cg.add_edge(e)
    return cg


def build(mod_path: str, include_console: bool = True) -> CallGraph:
    """The call graph of the mod at `mod_path`. `include_console` keeps the
    `te_debug_*` console harnesses, which `event_context_audit` leaves out."""
    import event_context_audit as eca

    return from_event_graph(eca.build_graph(mod_path, include_console=include_console,
                                            strip_directives=True))
