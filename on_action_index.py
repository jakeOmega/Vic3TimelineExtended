"""On-actions as the engine reads them, for GET /on-actions and GET
/on-action-callers (#333).

The engine merges every declaration of an on-action: the `events` and
`on_actions` lists add up across files, and an `effect` block overwrites, the
later file's replacing the earlier one (external_mod_overlap.LOAD_ORDER_MODEL
["on_actions"], a documented claim, not a probed one). ModState's "On Actions"
store keeps one block per name, the last one parsed, so it shows one of the
thirty-odd files that declare `on_monthly_pulse_country` and hides the rest.

`scan` therefore reads `common/on_actions` file by file, with the scanner
external_mod_overlap already uses for another mod's hooks (`_scan_db`), and
keeps every declaration with its file and line. `entry` gives one on-action's
declarations (`sources`), the lists the recorded rules let it merge, the
fields more than one declaration sets that do not add up
(`fields_set_more_than_once`), and the on-actions that list it (`fired_by`).

What it does not assert:

- `random_events` set by more than one declaration is not merged: each
  declaration is its own pool with its own `chance_to_happen`, and how the
  engine combines them is not recorded. `merged.random_events` is then None.
- A declaration under a directive (`REPLACE:on_x`) is not merged with the
  others: no rule for a directive on an on-action is recorded. `merged` is
  then None.
- The chaining fields `first_valid`, `first_valid_on_action`,
  `random_on_actions` and `fallback` are named in a source's `fields` but not
  expanded (the mod uses none).

Load order is the probed one (LOAD_ORDER_MODEL["interleaving"]): vanilla's and
the mod's files make one list ordered by file name, vanilla not first. A
vanilla file a mod file of the same path replaces is not read.

Vanilla's on-actions are read only where the game is installed: they are not
in `vanilla_parsed/`. Without them `origin` reads "mod (vanilla not indexed)"
and `vanilla_indexed` is false, so a hook's merged view is the mod's half.

`callers` is the inverse: the on-actions that reach a scripted effect, an
event or another on-action, through any chain of scripted effects and events,
from event_context_audit's dispatch graph (mod script only). It follows
on-actions, scripted effects and events; every other entity the graph knows
calls the target (a journal entry's pulse, a button, a decision, ...) is
listed in `not_followed`, so an empty `callers` is not read as "nothing runs
this". An effect a caller passes by name (`helper = { EFFECT = name }`, run
as `$EFFECT$ = yes` inside the helper) is followed through the helper, and
listed in `passed_as_parameter` either way. A row is the shortest route from
its on-action call site, not the only one: `guards_complete` is false, with
`other_routes`, when a link on it has another call site or another way down.
"""
from __future__ import annotations

import os
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Optional

import external_mod_overlap as ext

DB = "on_actions"
MOD, VANILLA = "mod", "vanilla"
NOT_INDEXED = "mod (vanilla not indexed)"
VANILLA_NOTE = (
    "Only this mod's declarations are indexed: vanilla's common/on_actions is read from "
    "the game files, which this machine does not have, and is not in vanilla_parsed/. "
    "Whatever vanilla declares for this name is missing from sources and merged."
)
_RULES = ext.LOAD_ORDER_MODEL["on_actions"]
RULE_OVERWRITES = "overwrites: the later file's block replaces the earlier one"
RULE_UNKNOWN = "unknown: not recorded whether this field adds up across declarations"
RULE_DIRECTIVE = ("unknown: a declaration carries a directive, and how a directive on an "
                  "on-action combines with the other declarations is not recorded")
RANDOM_EVENTS_NOTE = (
    "random_events is set by more than one declaration. Each is its own pool with its own "
    "chance_to_happen (read them in sources); how the engine combines them is not recorded, "
    "so no single pool is given here."
)
DIRECTIVE_NOTE = (
    "A declaration carries a directive (directive_declarations). No rule for a directive on "
    "an on-action is recorded, so the declarations are not merged: read sources."
)
# The weight `random_events = { 100 = 0 }` gives to firing nothing.
NO_EVENT = "0"


@dataclass
class Declaration:
    """One `name = { ... }` block of an on-action, in one file."""
    name: str
    rel: str                  # the file's path within common/on_actions: what load order compares
    file: str                 # `common/on_actions/x.txt`, or `game/common/on_actions/x.txt`
    line: int
    origin: str               # MOD | VANILLA
    directive: Optional[str]
    fields: list = field(default_factory=list)        # [(field, line)] at depth 1, in order
    on_actions: list = field(default_factory=list)
    events: list = field(default_factory=list)
    # {event id, or NO_EVENT: weight}; a repeated id's weights are added.
    random_events: dict = field(default_factory=dict)
    chance_to_happen: Optional[object] = None

    def field_names(self) -> list:
        return [name for name, _line in self.fields]

    def as_source(self) -> dict:
        out = {"file": self.file, "line": self.line, "origin": self.origin}
        if self.directive:
            out["directive"] = self.directive
        out.update({
            "on_actions": list(self.on_actions),
            "events": list(self.events),
            "random_events": dict(self.random_events),
            "fields": self.field_names(),
        })
        if self.chance_to_happen is not None:
            out["chance_to_happen"] = self.chance_to_happen
        return out


def block_items(value: Optional[str]) -> tuple[list, list]:
    """(bare tokens, [(key, value)]) at depth 1 of a `{ ... }` block given as
    its tokens joined by spaces (scan_script's form). A pair whose value is a
    block has value None; a value that is not a block gives nothing."""
    tokens = ext._TOKEN_RE.findall(value or "")
    bare: list = []
    pairs: list = []
    if not tokens or tokens[0] != "{":
        return bare, pairs
    i, n = 1, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "}":
            break
        if tok == "{" or (i + 2 < n and tokens[i + 1] in ext._OPERATORS and tokens[i + 2] == "{"):
            # A nested block, anonymous or keyed (`delay = { days = 5 }`): skip it whole.
            start = i if tok == "{" else i + 2
            depth, j = 0, start
            while j < n:
                if tokens[j] == "{":
                    depth += 1
                elif tokens[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if tok != "{":
                pairs.append((tok, None))
            i = j + 1
        elif i + 2 < n and tokens[i + 1] in ext._OPERATORS:
            pairs.append((tok, tokens[i + 2]))
            i += 3
        else:
            bare.append(tok.strip('"'))
            i += 1
    return bare, pairs


def _number(text: str):
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def _declaration(name: str, rel: str, file: str, origin: str, entry) -> Declaration:
    decl = Declaration(name, rel, file, entry.line, origin, entry.directive)
    for raw_key, line, value in entry.children:
        key = ext.split_directive(raw_key)[1]
        decl.fields.append((key, line))
        bare, pairs = block_items(value)
        if key == "on_actions":
            decl.on_actions.extend(bare)
        elif key == "events":
            decl.events.extend(bare)
        elif key == "random_events":
            for weight, event in pairs:
                if weight == "chance_to_happen":
                    decl.chance_to_happen = None if event is None else _number(event)
                elif event is not None and isinstance(_number(weight), (int, float)):
                    event = event.strip('"')
                    decl.random_events[event] = decl.random_events.get(event, 0) + _number(weight)
    return decl


def _load_order_key(order: str):
    """One list ordered by file name, vanilla's files and the mod's together
    (ext.sort_ops with vanilla_first=False), then by line."""
    def key(decl: Declaration):
        return (ext.name_key(decl.rel, order), decl.rel, decl.origin != VANILLA, decl.line)
    return key


@dataclass
class Index:
    declarations: dict = field(default_factory=dict)   # name -> [Declaration], in load order
    vanilla_indexed: bool = False
    warnings: list = field(default_factory=list)       # [{"file", "warning"}] from the scan
    # Vanilla files a mod file of the same path replaces: not read.
    shadowed_vanilla_files: list = field(default_factory=list)

    def names(self, origin: Optional[str] = None) -> list:
        return [name for name, decls in self.declarations.items()
                if origin is None or any(d.origin == origin for d in decls)]

    def origin_of(self, name: str) -> str:
        origins = {d.origin for d in self.declarations.get(name, [])}
        if not self.vanilla_indexed:
            return NOT_INDEXED
        if origins == {MOD, VANILLA}:
            return "mod+vanilla"
        return VANILLA if origins == {VANILLA} else MOD

    def warnings_for(self, files) -> list:
        files = set(files)
        return [w for w in self.warnings if w["file"] in files]

    def fired_by(self, name: str) -> list:
        """Every declaration whose `on_actions` list names `name`."""
        return [
            {"on_action": parent, "file": d.file, "line": d.line, "origin": d.origin}
            for parent, decls in self.declarations.items()
            for d in decls if name in d.on_actions
        ]

    def fields_set_more_than_once(self, name: str) -> list:
        """The fields more than one declaration of `name` sets that do not add
        up: `effect` (the later file's wins, by the documented rule) and every
        field with no recorded rule (`trigger`, `random_events`, ...). With a
        directive among the declarations no field has a recorded rule."""
        decls = self.declarations.get(name, [])
        under_directive = any(d.directive for d in decls)
        setters: dict = {}
        for d in decls:
            for fname, line in d.fields:
                setters.setdefault(fname, []).append((d, line))
        out = []
        for fname, lst in setters.items():
            if len({(d.file, d.line) for d, _l in lst}) < 2:
                continue
            if fname in ext.ADDITIVE_ON_ACTION_FIELDS and not under_directive:
                continue
            row = {
                "field": fname,
                "declarations": [{"file": d.file, "line": line, "origin": d.origin}
                                 for d, line in lst],
                "rule": RULE_UNKNOWN,
                "winner": None,
            }
            if under_directive:
                row["rule"] = RULE_DIRECTIVE
            elif fname in ext.OVERWRITING_ON_ACTION_FIELDS:
                last = set()
                for order in ext.file_orders():
                    d, line = max(lst, key=lambda pair, order=order: (
                        _load_order_key(order)(pair[0]), pair[1]))
                    last.add((d.file, line))
                row["rule"] = RULE_OVERWRITES
                # How sure the rule is ("documented": a repo doc says so, not
                # read in game), and where it is written.
                row["rule_status"] = _RULES["status"]
                row["rule_see"] = f"external_mod_overlap.LOAD_ORDER_MODEL['on_actions']; {_RULES['see']}"
                # More than one answer: the file-name order decides, and it isn't known.
                if len(last) == 1:
                    row["winner"] = dict(zip(("file", "line"), next(iter(last))))
            out.append(row)
        return out

    def merged(self, name: str) -> tuple[Optional[dict], dict]:
        """(the merged lists, or None when a directive leaves no recorded
        rule; the notes that go beside them)."""
        decls = self.declarations.get(name, [])
        notes: dict = {}
        directives = [d for d in decls if d.directive]
        if directives:
            notes["merged_note"] = DIRECTIVE_NOTE
            notes["directive_declarations"] = [
                {"file": d.file, "line": d.line, "directive": d.directive, "rule": RULE_DIRECTIVE}
                for d in directives]
            return None, notes
        merged: dict = {
            "on_actions": [n for d in decls for n in d.on_actions],
            "events": [e for d in decls for e in d.events],
        }
        pools = [d for d in decls if "random_events" in d.field_names()]
        if len(pools) > 1:
            merged["random_events"] = None
            merged["random_events_note"] = RANDOM_EVENTS_NOTE
        else:
            merged["random_events"] = dict(pools[0].random_events) if pools else {}
            if pools and pools[0].chance_to_happen is not None:
                merged["chance_to_happen"] = pools[0].chance_to_happen
        return merged, notes

    def entry(self, name: str) -> Optional[dict]:
        decls = self.declarations.get(name)
        if not decls:
            return None
        merged, notes = self.merged(name)
        out = {
            "type": "On Actions",
            "id": name,
            "origin": self.origin_of(name),
            "vanilla_indexed": self.vanilla_indexed,
            "declarations": len(decls),
            "sources": [d.as_source() for d in decls],
            "merged": merged,
            **notes,
            "fields_set_more_than_once": self.fields_set_more_than_once(name),
            "fired_by": self.fired_by(name),
        }
        if not self.vanilla_indexed:
            out["note"] = VANILLA_NOTE
        if self.shadowed_vanilla_files:
            same_path = ext.LOAD_ORDER_MODEL["same_path"]
            out["shadowed_vanilla_files"] = {
                "files": list(self.shadowed_vanilla_files),
                "rule": "a mod file at a vanilla file's path replaces vanilla's whole file, "
                        "so these are not read",
                # "documented": a repo doc says so; not read in game.
                "rule_status": same_path["status"],
                "rule_see": f"external_mod_overlap.LOAD_ORDER_MODEL['same_path']; {same_path['see']}",
            }
        warnings = self.warnings_for(d.file for d in decls)
        if warnings:
            out["warnings"] = warnings
        return out

    def listing(self) -> list:
        """The on-actions a mod file declares, as GET /on-actions lists them.
        A row whose file the scan warned about carries the warning: an
        unclosed brace there can swallow the on-actions after it."""
        rows = []
        for name, decls in self.declarations.items():
            if not any(d.origin == MOD for d in decls):
                continue
            files = sorted({d.file for d in decls})
            row = {"type": "On Actions", "id": name, "declarations": len(decls), "files": files}
            warnings = self.warnings_for(files)
            if warnings:
                row["warnings"] = warnings
            rows.append(row)
        return rows


def _scan_side(root: str, origin: str, label: str, index: Index, skip=()) -> bool:
    """Add every declaration under `<root>/common/on_actions` to `index`,
    leaving out the files in `skip`; False when the folder isn't there."""
    base = os.path.join(root, "common", DB)
    if not os.path.isdir(base):
        return False
    warnings: list = []
    files = [rel for rel in ext.list_files(base) if rel not in skip]
    scan = ext._scan_db(root, DB, files, warnings, origin, block_cap=None)
    for w in warnings:
        index.warnings.append({"file": label + w["file"], "warning": w["warning"]})
    for name, lst in scan.entries.items():
        for rel, entry in lst:
            index.declarations.setdefault(name, []).append(
                _declaration(name, rel, f"{label}common/{DB}/{rel}", origin, entry))
    return True


def scan(mod_root: str, vanilla_game_dir: Optional[str] = None) -> Index:
    """Every on-action declaration of the mod at `mod_root` and, where
    `vanilla_game_dir` (the install's `game/` folder) exists, of vanilla, in
    load order. Reads the files on each call (about 40 ms for the mod's 74)."""
    index = Index()
    _scan_side(mod_root, MOD, "", index)
    if vanilla_game_dir:
        mod_base = os.path.join(mod_root, "common", DB)
        mod_files = ext.list_files(mod_base) if os.path.isdir(mod_base) else []
        vanilla_base = os.path.join(vanilla_game_dir, "common", DB)
        shadowed = [rel for rel in (ext.list_files(vanilla_base) if os.path.isdir(vanilla_base) else [])
                    if any(ext.same_path(rel, m) for m in mod_files)]
        index.vanilla_indexed = _scan_side(vanilla_game_dir, VANILLA, "game/", index, shadowed)
        index.shadowed_vanilla_files = [f"game/common/{DB}/{rel}" for rel in shadowed]
    order = ext.file_orders()[0]
    for decls in index.declarations.values():
        decls.sort(key=_load_order_key(order))
    return index


# ---------------------------------------------------------------------------
# The inverse: which on-actions run this
# ---------------------------------------------------------------------------

# The caller kinds the walk goes through; an on-action ends a chain. Every
# other kind of entity that calls into the chain goes to `not_followed`.
FOLLOWED = ("scripted_effect", "event")
CALLERS_NOTE = (
    "Mod script only: vanilla's on-actions, events and scripted effects are not scanned. "
    "callers are the on-actions that reach the target through scripted effects and events "
    "(an event's immediate, after or option: the hop's path says which). Entities of any "
    "other kind that call the target or a link of such a chain (a journal entry's pulse, a "
    "scripted button, a decision, ...) are not followed: they are in not_followed, so read "
    "count together with not_followed_count. A row is the shortest route from that on-action "
    "call site, not the only one: where guards_complete is false, a link on it has another "
    "call site or another way down to the target (other_routes), whose guards may differ."
)


def _hop(kind: str, entity: str, rel: str, line: int, path, guards: str, via: str) -> dict:
    return {"in": entity, "kind": kind, "file": rel, "line": line, "path": list(path),
            "guards": guards.strip(), "via": via}


def _passed_effects(graph) -> dict:
    """{scripted effect: [(helper, param, call, run sites)]} for every call
    that passes the effect's name as an argument (`helper = { EFFECT = name }`).
    The run sites are the `$EFFECT$ = yes` / `$EFFECT$ = { }` sites inside the
    helper: with some, the effect runs wherever the helper is called that way.
    Kept on the graph, which is built once per request."""
    cached = getattr(graph, "_passed_effects", None)
    if cached is None:
        cached = {}
        for helper, calls in graph.effect_calls.items():
            if helper not in graph.effect_file:
                continue
            for call in calls:
                for param, value in call[7].items():
                    if value in graph.effect_file:
                        runs = [c for c in graph.effect_calls.get(f"${param}$", [])
                                if c[5] == helper and c[6] == "scripted_effect"]
                        cached.setdefault(value, []).append((helper, param, call, runs))
        graph._passed_effects = cached
    return cached


def _incoming(graph, kind: str, name: str):
    """Every site that reaches the node `(kind, name)`, as (hop, inner): the
    caller's hop, and the hops between it and the node that are not links of
    their own. `inner` is empty for a plain call. For an effect a caller
    passes by name to a helper, the caller's hop is its call of the helper
    (`passes`) and `inner` is the helper's `$PARAM$ = yes` site."""
    if kind == "scripted_effect":
        for rel, line, path, _sw, conds, entity, caller_kind, _params in graph.effect_calls.get(name, []):
            yield _hop(caller_kind, entity, rel, line, path, conds, "effect"), []
        for helper, param, call, runs in _passed_effects(graph).get(name, []):
            if not runs:
                continue
            rel, line, path, _sw, conds, entity, caller_kind, _params = call
            outer = _hop(caller_kind, entity, rel, line, path, conds, "effect")
            outer["passes"] = {"to": helper, "param": param}
            r_rel, r_line, r_path, _s, r_conds, _e, _k, _p = runs[0]
            inner = _hop("scripted_effect", helper, r_rel, r_line, r_path, r_conds, "parameter")
            inner["param"] = param
            if len(runs) > 1:
                inner["other_sites"] = len(runs) - 1
            yield outer, [inner]
    elif kind == "event":
        for site in graph.sites_by_event.get(name, []):
            yield _hop(site.entity_kind, site.entity, site.file, site.line, site.path,
                       site.conds, site.via), []
    elif kind == "on_action":
        for parent, line, rel in graph.on_action_parents.get(name, []):
            yield _hop("on_action", parent, rel, line, ["on_actions"], "", "on_actions"), []


def _roots(graph, name: str) -> list:
    """The on-actions nothing in the mod lists that chain down to `name`
    through `on_actions` lists; `name` itself when nothing lists it."""
    roots, seen, todo = set(), {name}, [name]
    while todo:
        current = todo.pop()
        parents = {p for p, _line, _file in graph.on_action_parents.get(current, [])}
        if not parents:
            roots.add(current)
        for parent in parents - seen:
            seen.add(parent)
            todo.append(parent)
    return sorted(roots)


def _walk(graph, start: list):
    """Walk backwards from the `start` nodes through scripted effects and
    events. Returns (chains ending at an on-action, chains ending at an entity
    of a kind not followed, the direct callers of a start node that nothing
    outside the walk reaches, and `calls`: for each link, the nodes of the
    walk it calls). A chain is a list of hops, the outermost first; a hop is
    one call site: the entity it sits in (`in`, `kind`), where (`file`,
    `line`, `path`), its `guards`, how it calls the next link (`via`), and
    `other_sites`, the number of further call sites of that link in the same
    entity (given when there are some; their guards can differ).

    Each link is visited once, so a chain is the shortest route from its
    first call site to the target, not the only one: `calls` says which links
    have another way down."""
    found, not_followed = [], []
    seen = set(start)
    todo = deque((node, []) for node in start)
    calls: dict = {}        # followed caller -> the nodes it calls
    entered = set()         # nodes an on-action or a not-followed entity calls
    while todo:
        node, chain = todo.popleft()
        by_caller: dict = {}
        for hop, inner in _incoming(graph, *node):
            if hop["kind"] == "on_action":
                entered.add(node)
                found.append([hop] + inner + chain)   # every on-action call site is a row
            else:
                by_caller.setdefault((hop["kind"], hop["in"]), []).append((hop, inner))
        for (caller_kind, caller), hops in by_caller.items():
            hop, inner = dict(hops[0][0]), hops[0][1]
            if len(hops) > 1:
                hop["other_sites"] = len(hops) - 1
            if caller_kind in FOLLOWED:
                calls.setdefault((caller_kind, caller), set()).add(node)
                if (caller_kind, caller) not in seen:
                    seen.add((caller_kind, caller))
                    todo.append(((caller_kind, caller), [hop] + inner + chain))
            else:
                entered.add(node)
                not_followed.append([hop] + inner + chain)
    # A link is reached when something enters it, or a reached link calls it.
    reached, spread = set(entered), deque(entered)
    while spread:
        for callee in calls.get(spread.popleft(), ()):
            if callee not in reached:
                reached.add(callee)
                spread.append(callee)
    # What calls the target but hangs from nothing: a console harness event,
    # dead code, a loop with no way in.
    unreached = sorted(
        {caller for caller, callees in calls.items()
         if caller not in reached and caller not in start and callees & set(start)})
    return found, not_followed, [{"kind": kind, "id": name} for kind, name in unreached], calls


def _other_routes(chain: list, start: list, calls: dict) -> list:
    """Why a row's guards are not the whole condition: each link of `chain`
    that calls the next one from more than one site (`other_sites`), or that
    reaches the target through another link as well (`also_through`)."""
    out = []
    for i, hop in enumerate(chain):
        row = {}
        if hop.get("other_sites"):
            row["other_sites"] = hop["other_sites"]
        if i and hop["via"] != "parameter":
            # The node this link calls: the next link, or the target itself.
            # A helper's `$PARAM$` site is part of the hop before it, not a link.
            later = [h for h in chain[i + 1:] if h["via"] != "parameter"]
            nxt = {(later[0]["kind"], later[0]["in"])} if later else set(start)
            also = sorted(name for _kind, name in calls.get((hop["kind"], hop["in"]), set()) - nxt)
            if also:
                row["also_through"] = also
        if row:
            out.append({"in": hop["in"], **row})
    return out


def callers(mod_root: str, target: str, code_on_actions=None) -> Optional[dict]:
    """The on-actions that reach scripted effect `target`, event `target` or
    on-action `target`, or None when the mod has no such effect, event or
    on-action. `kind` names which it is (joined by `+` when one name is more
    than one). `code_on_actions` is the set of on-actions the engine fires
    from code (the engine docs' `from_code`), when the caller has it.

    Builds event_context_audit's graph on each call (several seconds for the
    whole mod), as /event-dispatch does."""
    import event_context_audit as eca

    graph = eca.build_graph(mod_root, include_console=True)
    start = []
    if target in graph.effect_file:
        start.append(("scripted_effect", target))
    if target in graph.events or target in graph.sites_by_event:
        start.append(("event", target))
    if target in graph.on_action_files:
        start.append(("on_action", target))
    if not start:
        return None
    found, skipped, unreached, calls = _walk(graph, start)

    rows, seen = [], set()
    for chain in sorted(found, key=lambda c: (c[0]["file"], c[0]["line"], c[0]["in"])):
        first = chain[0]
        through = [hop["in"] for hop in chain[1:]]
        sig = (first["in"], first["file"], first["line"], tuple(through), first["via"])
        if sig in seen:
            continue
        seen.add(sig)
        roots = _roots(graph, first["in"])
        other_routes = _other_routes(chain, start, calls)
        rows.append({
            "on_action": first["in"], "file": first["file"], "line": first["line"],
            "via": first["via"], "through": through,
            # One entry per hop, the on-action's own call first: an empty
            # string is a hop with no enclosing limit or trigger.
            "guards": [hop["guards"] for hop in chain],
            # False: this is the shortest route from the on-action's call, and
            # a link on it has another call site or another way down to the
            # target (other_routes), under guards this row does not show.
            "guards_complete": not other_routes,
            "other_routes": other_routes,
            # The route runs through an event option: someone has to pick it.
            "through_option": any(hop["kind"] == "event" and "option" in hop["path"]
                                  for hop in chain),
            "hops": chain,
            "roots": roots,
            "engine_hooks": (None if code_on_actions is None
                             else [r for r in roots if r in code_on_actions]),
        })

    grouped: dict = {}
    for chain in skipped:
        first = chain[0]
        key = (first["kind"], first["in"], tuple(hop["in"] for hop in chain[1:]))
        row = grouped.setdefault(key, {
            "kind": first["kind"], "id": first["in"], "file": first["file"],
            "line": first["line"], "path": first["path"], "sites": 0,
            "through": [hop["in"] for hop in chain[1:]],
        })
        row["sites"] += 1 + first.get("other_sites", 0)
    not_followed = sorted(grouped.values(), key=lambda r: (r["kind"], r["id"], r["through"]))
    kinds = Counter(row["kind"] for row in not_followed)

    passed = [
        {"to": helper, "param": param, "in": call[5], "kind": call[6], "file": call[0],
         "line": call[1], "followed": bool(runs)}
        for helper, param, call, runs in _passed_effects(graph).get(target, [])
    ] if ("scripted_effect", target) in start else []

    one_route = sum(not r["guards_complete"] for r in rows)
    if rows:
        summary = f"{len({r['on_action'] for r in rows})} on-action(s) reach it"
        if one_route:
            summary += (f"; {one_route} of {len(rows)} rows show one route of several "
                        "(guards_complete false)")
    else:
        summary = "no on-action reaches it"
    if not_followed:
        summary += ("; also called from " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
                    + " (not_followed), which this does not trace to a pulse")
    elif not rows:
        if unreached:
            summary += ": only entities nothing in the mod's script reaches call it (unreached)"
        elif passed:
            first = passed[0]
            summary += (f": its name is passed as a parameter to {first['to']} at "
                        f"{first['file']}:{first['line']} (passed_as_parameter), which runs it "
                        "in a way this did not follow")
        else:
            summary += ": nothing in the mod's script calls it"
    return {
        "target": target,
        "kind": "+".join(kind for kind, _name in start),
        "origin": NOT_INDEXED,
        "note": CALLERS_NOTE,
        "summary": summary,
        "count": len(rows),
        "on_actions": sorted({r["on_action"] for r in rows}),
        "callers": rows,
        "not_followed_count": len(not_followed),
        "not_followed_kinds": dict(sorted(kinds.items())),
        "not_followed": not_followed,
        "unreached": unreached,
        "passed_as_parameter": passed,
    }
