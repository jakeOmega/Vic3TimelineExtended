"""On-actions as the engine reads them, for GET /on-actions and GET
/on-action-callers (#333).

The engine merges every declaration of an on-action: the `events` and
`on_actions` lists add up across files, and an `effect` block overwrites, the
later file's replacing the earlier one (external_mod_overlap.LOAD_ORDER_MODEL
["on_actions"]; docs/guides/scripting_best_practices.md § "Extending Vanilla
On-Actions Safely"). ModState's "On Actions" store keeps one block per name,
the last one parsed, so it shows one of the thirty-odd files that declare
`on_monthly_pulse_country` and hides the rest.

`scan` therefore reads `common/on_actions` file by file, with the scanner
external_mod_overlap already uses for another mod's hooks (`_scan_db`), and
keeps every declaration with its file and line. `entry` gives one on-action's
declarations (`sources`), their merged lists, the fields more than one
declaration sets that do not add up (`fields_set_more_than_once`), and the
on-actions that list it (`fired_by`). The chaining fields `first_valid`,
`first_valid_on_action`, `random_on_actions` and `fallback` are named in a
source's `fields` but not expanded (the mod uses none).

Vanilla's on-actions are read only where the game is installed: they are not
in `vanilla_parsed/`. Without them `origin` reads "mod (vanilla not indexed)"
and `vanilla_indexed` is false, so a hook's merged view is the mod's half.

`callers` is the inverse: the on-actions that run a scripted effect, fire an
event or list another on-action, through any chain of scripted effects, from
event_context_audit's dispatch graph (mod script only).
"""
from __future__ import annotations

import os
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
CALLERS_NOTE = (
    "Mod script only: vanilla's on-actions and scripted effects are not scanned. A caller "
    "is an on-action whose own block, or a scripted effect it reaches, names the target; "
    "an event fired from another event's option is /event-dispatch's question."
)
RULE_OVERWRITES = "overwrites: the later file's block replaces the earlier one"
RULE_UNKNOWN = "unknown: not recorded whether this field adds up across declarations"
# The weight `random_events = { 100 = 0 }` gives to firing nothing.
NO_EVENT = "0"


@dataclass
class Declaration:
    """One `name = { ... }` block of an on-action, in one file."""
    name: str
    file: str                 # `common/on_actions/x.txt`, or `game/common/on_actions/x.txt`
    line: int
    origin: str               # MOD | VANILLA
    directive: Optional[str]
    fields: list = field(default_factory=list)        # [(field, line)] at depth 1, in order
    on_actions: list = field(default_factory=list)
    events: list = field(default_factory=list)
    random_events: dict = field(default_factory=dict)  # {event id, or NO_EVENT: weight}
    chance_to_happen: Optional[str] = None

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


def _declaration(name: str, file: str, origin: str, entry) -> Declaration:
    decl = Declaration(name, file, entry.line, origin, entry.directive)
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
                    decl.chance_to_happen = event
                elif event is not None and isinstance(_number(weight), (int, float)):
                    event = event.strip('"')
                    decl.random_events[event] = decl.random_events.get(event, 0) + _number(weight)
    return decl


def _load_order_key(order: str):
    def key(decl: Declaration):
        return (decl.origin != VANILLA, ext.name_key(decl.file, order), decl.file, decl.line)
    return key


@dataclass
class Index:
    declarations: dict = field(default_factory=dict)   # name -> [Declaration], in load order
    vanilla_indexed: bool = False
    warnings: list = field(default_factory=list)

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

    def fired_by(self, name: str) -> list:
        """Every declaration whose `on_actions` list names `name`."""
        return [
            {"on_action": parent, "file": d.file, "line": d.line, "origin": d.origin}
            for parent, decls in self.declarations.items()
            for d in decls if name in d.on_actions
        ]

    def fields_set_more_than_once(self, name: str) -> list:
        """The fields more than one declaration of `name` sets that do not add
        up: `effect` (the later file's wins) and every field with no recorded
        rule (`trigger`, `random_events`, ...)."""
        decls = self.declarations.get(name, [])
        setters: dict = {}
        for d in decls:
            for fname, line in d.fields:
                setters.setdefault(fname, []).append((d, line))
        out = []
        for fname, lst in setters.items():
            if fname in ext.ADDITIVE_ON_ACTION_FIELDS or len({(d.file, d.line) for d, _l in lst}) < 2:
                continue
            row = {
                "field": fname,
                "declarations": [{"file": d.file, "line": line, "origin": d.origin}
                                 for d, line in lst],
            }
            if fname in ext.OVERWRITING_ON_ACTION_FIELDS:
                last = set()
                for order in ext.file_orders():
                    d, line = max(lst, key=lambda pair, order=order: (
                        _load_order_key(order)(pair[0]), pair[1]))
                    last.add((d.file, line))
                row["rule"] = RULE_OVERWRITES
                # More than one answer: the file-name order decides, and it isn't known.
                row["winner"] = (dict(zip(("file", "line"), next(iter(last))))
                                 if len(last) == 1 else None)
            else:
                row["rule"] = RULE_UNKNOWN
                row["winner"] = None
            out.append(row)
        return out

    def entry(self, name: str) -> Optional[dict]:
        decls = self.declarations.get(name)
        if not decls:
            return None
        merged_random: dict = {}
        for d in decls:
            for event, weight in d.random_events.items():
                merged_random[event] = merged_random.get(event, 0) + weight
        out = {
            "type": "On Actions",
            "id": name,
            "origin": self.origin_of(name),
            "vanilla_indexed": self.vanilla_indexed,
            "declarations": len(decls),
            "sources": [d.as_source() for d in decls],
            "merged": {
                "on_actions": [n for d in decls for n in d.on_actions],
                "events": [e for d in decls for e in d.events],
                "random_events": merged_random,
            },
            "fields_set_more_than_once": self.fields_set_more_than_once(name),
            "fired_by": self.fired_by(name),
        }
        if not self.vanilla_indexed:
            out["note"] = VANILLA_NOTE
        return out

    def listing(self) -> list:
        """The on-actions a mod file declares, as GET /on-actions lists them."""
        return [
            {"type": "On Actions", "id": name, "declarations": len(decls),
             "files": sorted({d.file for d in decls})}
            for name, decls in self.declarations.items()
            if any(d.origin == MOD for d in decls)
        ]


def _scan_side(root: str, origin: str, label: str, index: Index) -> bool:
    """Add every declaration under `<root>/common/on_actions` to `index`;
    False when the folder isn't there."""
    base = os.path.join(root, "common", DB)
    if not os.path.isdir(base):
        return False
    warnings: list = []
    scan = ext._scan_db(root, DB, ext.list_files(base), warnings, origin, block_cap=None)
    for w in warnings:
        index.warnings.append({"file": label + w["file"], "warning": w["warning"]})
    for name, lst in scan.entries.items():
        for rel, entry in lst:
            index.declarations.setdefault(name, []).append(
                _declaration(name, f"{label}common/{DB}/{rel}", origin, entry))
    return True


def scan(mod_root: str, vanilla_game_dir: Optional[str] = None) -> Index:
    """Every on-action declaration of the mod at `mod_root` and, where
    `vanilla_game_dir` (the install's `game/` folder) exists, of vanilla.
    Reads the files on each call (about 40 ms for the mod's 74)."""
    index = Index()
    if vanilla_game_dir:
        index.vanilla_indexed = _scan_side(vanilla_game_dir, VANILLA, "game/", index)
    _scan_side(mod_root, MOD, "", index)
    order = ext.file_orders()[0]
    for decls in index.declarations.values():
        decls.sort(key=_load_order_key(order))
    return index


# ---------------------------------------------------------------------------
# The inverse: which on-actions run this
# ---------------------------------------------------------------------------

def _hooks(graph, name: str) -> list:
    """The on-actions with no parent that chain down to `name` through
    `on_actions` lists (the engine's hooks, normally); `name` itself when
    nothing lists it."""
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


def _effect_callers(graph, effect: str) -> list:
    """(on_action, file, line, guards, path, through) for every on-action
    that reaches scripted effect `effect`; `through` lists the scripted
    effects between the on-action's call and `effect`, outermost first."""
    out, seen, todo = [], {effect}, [(effect, [])]
    while todo:
        current, through = todo.pop(0)
        for rel, line, path, _switches, conds, entity, kind, _params in graph.effect_calls.get(current, []):
            if kind == "on_action":
                out.append((entity, rel, line, conds.strip(), list(path), through))
            elif kind == "scripted_effect" and entity not in seen:
                seen.add(entity)
                todo.append((entity, [entity] + through))
    return out


def callers(mod_root: str, target: str) -> Optional[dict]:
    """The on-actions that run scripted effect `target`, fire event `target`
    or list on-action `target`, or None when the mod has no such effect,
    event or on-action. `kind` names which it is (joined by `+` when one name
    is more than one). Builds event_context_audit's graph on each call (a
    second or more)."""
    import event_context_audit as eca

    graph = eca.build_graph(mod_root, include_console=True)
    kinds: list = []
    found: list = []
    if target in graph.effect_file:
        kinds.append("scripted_effect")
        found += [(oa, rel, line, guards, path, through, "effect")
                  for oa, rel, line, guards, path, through in _effect_callers(graph, target)]
    if target in graph.events or target in graph.sites_by_event:
        kinds.append("event")
        for site in graph.sites_by_event.get(target, []):
            if site.entity_kind == "on_action":
                found.append((site.entity, site.file, site.line, site.conds.strip(),
                              list(site.path), [], site.via))
            elif site.entity_kind == "scripted_effect":
                # The event is fired inside a scripted effect: its on-action callers.
                for oa, rel, line, guards, path, through in _effect_callers(graph, site.entity):
                    found.append((oa, rel, line, guards, path, through + [site.entity],
                                  site.via))
    if target in graph.on_action_files:
        kinds.append("on_action")
        found += [(parent, rel, line, "", ["on_actions"], [], "on_actions")
                  for parent, line, rel in graph.on_action_parents.get(target, [])]
    if not kinds:
        return None
    rows, seen = [], set()
    for oa, rel, line, guards, path, through, via in sorted(found, key=lambda r: (r[1], r[2], r[0])):
        sig = (oa, rel, line, tuple(through), via)
        if sig in seen:
            continue
        seen.add(sig)
        rows.append({
            "on_action": oa, "file": rel, "line": line, "via": via, "through": through,
            "path": path, "guards": guards, "hooks": _hooks(graph, oa),
        })
    return {
        "target": target,
        "kind": "+".join(kinds),
        "origin": NOT_INDEXED,
        "note": CALLERS_NOTE,
        "count": len(rows),
        "on_actions": sorted({r["on_action"] for r in rows}),
        "callers": rows,
    }
