#!/usr/bin/env python3
"""What is guaranteed whenever an event fires, for whoever writes its text.

    python3 scripts/analysis/event_guarantees.py modern_election_events.11
    python3 scripts/analysis/event_guarantees.py modern_election_events      # the whole chain
    python3 scripts/analysis/event_guarantees.py augmentation_events --json  # the same, as data
    python3 scripts/analysis/event_guarantees.py --tech social_media         # one technology
    python3 scripts/analysis/event_guarantees.py --trigger has_augmentation_tech
    python3 scripts/analysis/event_guarantees.py --check-doc                 # the per-chain rows

A text may show only what must be true whenever it is shown
(docs/guides/loc_style_guide.md, "Detail that cannot be wrong"). This prints,
per event, what its own `trigger` requires and what the gates outside it add.

The event's own trigger:

* the technologies it requires, each with its era;
* every technology that follows from them: their prerequisites, recursively,
  and (owner's rule, 2026-11-09) every technology more than two eras behind
  the latest one required. A tech cannot require one from another category,
  so the prerequisites alone miss the obvious (social media does not require
  the telephone), but technology spread makes anything three eras back as
  good as certain;
* the technologies it requires to be ABSENT;
* the rest of its top-level lines, as written.

The gates outside it (#1622), each labeled by where it came from:

* `law X unlocks at`: for `is_enacting_law` / `has_law = law_type:X`, the
  law's `unlocking_technologies` (all of them) and `unlocking_laws` (one of
  them, each read the same way). A law in force (`has_law`) was enacted with
  them unless the country began the game with it or an effect handed it over.
* `scripted trigger X tests`: a scripted trigger the trigger calls, opened one
  level, with any law inside it.
* `journal entry Y requires`, for `has_journal_entry = Y` in the trigger: the
  entry's activation tests, as below.
* under `fired by`, one entry per route that reaches the event:
  - `journal entry Y requires`: the entry's `is_shown_when_inactive` and
    `possible` (it activates when both hold), and the tests around every
    `add_journal_entry` of it, which skips both. Read when the entry
    activated, so only its technology is carried into the totals.
  - `pool weight tests`: a `random_list` draw whose base weight is 0 can only
    be drawn through an `add` in its `modifier`, so the tests around the adds
    are requirements, one of them at least. `! weight added outside that
    gate` marks an add that lacks a technology another add tests.
  - `tests at the dispatch`: every `if` limit, `random_list` trigger and
    outcome trigger between the firing entity and the `trigger_event`.
  - `sent by`: an event that sends this one. Nothing of the sender's own
    technology carries over; only the tests at the dispatch do.
  - an on-action's own `trigger`, and the on-actions that call it.
  - a scripted effect is followed to everything that calls it, and one that
    is handed the event as an argument (`helper = { EVENT = ns.4 }`) is read
    with the call's arguments filled in.
  - `not followed`: a decision, a button, a treaty or anything else the tool
    does not open, a scripted effect nothing calls, a dispatch it could not
    find. A scope change on the way (`random_country = { ... }`) is followed:
    the route keeps only the tests made after it, in the receiver's scope.

A guarantee from outside holds only if EVERY route gives it. The `from
outside` line is that intersection, and it is nothing as soon as one route is
not followed or nothing is found that fires the event. `in all` adds the
event's own trigger. Only technology is totalled: a law or a variable tested
when a journal entry activated or an event was sent can have changed since.

A requirement inside an `OR` is listed as "one of"; what every alternative
has in common (shared prerequisites, a lowest era) is still guaranteed. An
option's own `trigger`, and a `triggered_desc`'s, add to it for that text:
they are listed under `only for` when they test a technology or a law.

`--check-doc` reads docs/guides/event_text_guarantees.md and reports every
technology a row's Guaranteed column names that no event of the row's chains
is guaranteed, and every `tech (era N)` whose era is wrong. It is a reading
aid, not a gate: the rows are prose.

Technologies, laws and journal entries come from the mod's files and the
committed vanilla_parsed/ snapshot; scripted triggers, effects and on-actions
from the mod's files only (the snapshot has none of vanilla's). The dispatch
graph is event_context_audit.build_graph, the one behind the server's
/event-dispatch. Needs no game and no server.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

import event_context_audit as eca  # noqa: E402
import faith_scene_audit as fsa  # noqa: E402
from faith_scene_audit import Node, parse_script  # noqa: E402

ERAS_BEHIND = 3
"""A tech this many eras behind a required one, or more, is assumed researched."""
TRIGGER_DEPTH = 1
"""How many levels of scripted trigger are opened (#1622: one)."""
LAW_DEPTH = 3
"""How far `unlocking_laws` is followed from one law to the laws that unlock it."""
MAX_ROUTES = 40
"""Calls of one scripted effect read before the rest are reported as not followed."""
GUARANTEES_DOC = os.path.join("docs", "guides", "event_text_guarantees.md")

_TECH_DEF = re.compile(r"^(?:(?:INJECT|REPLACE|TRY_INJECT|REPLACE_OR_CREATE|INJECT_OR_CREATE):)?([\w\-]+)\s*=\s*\{", re.M)
_ERA = re.compile(r"\bera\s*=\s*era_(\d+)")
_UNLOCKING = re.compile(r"unlocking_technologies\s*=\s*\{([^}]*)\}")
_COMMENT = re.compile(r"#[^\n]*")
_PREFIX = re.compile(r"^(?:INJECT|REPLACE|TRY_INJECT|REPLACE_OR_CREATE|INJECT_OR_CREATE):")
_APPENDING = ("INJECT:", "TRY_INJECT:", "INJECT_OR_CREATE:")
_ADD_ENTRY = re.compile(r"\badd_journal_entry\s*=\s*\{[^{}]*?\btype\s*=\s*([\w\-]+)", re.S)
_LAW_TESTS = {"is_enacting_law": "being enacted", "has_law": "in force", "has_law_or_variant": "in force"}
_SAME_SCOPE_WRAPPERS = ("custom_tooltip", "custom_description", "hidden_trigger")
_WRAPPER_FIELDS = ("text", "subject", "object", "value")
# Journal entry hooks that run once for each involved country (1.15): the receiver is not the
# country whose `possible` activated the entry.
_INVOLVED_HOOKS = frozenset({"effect_all_involved", "immediate_all_involved",
                             "on_become_involved_after_activation", "on_no_longer_involved"})
_KIND_TEXT = {
    "journal_entry": "journal entry", "on_action": "on-action", "scripted_effect": "scripted effect",
    "event": "event", "button": "scripted button", "treaty": "treaty article",
    "diplomatic_action": "diplomatic action", "history": "history file",
}


def block_end(text: str, open_brace: int) -> int:
    """Index just past the brace matching the one at `open_brace`."""
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def load_technologies(repo_root=REPO_ROOT) -> dict:
    """{tech: {"era": int | None, "requires": [tech, ...]}} for vanilla and the mod."""
    techs = {}
    snapshot = os.path.join(repo_root, "vanilla_parsed", "common", "technologies.json")
    if os.path.exists(snapshot):
        with open(snapshot, encoding="utf-8") as fh:
            for name, (_, body) in json.load(fh).items():
                era = body.get("era", [None, ""])[1]
                requires = body.get("unlocking_technologies", [None, []])[1]
                names = list(requires) if isinstance(requires, dict) else [
                    r if isinstance(r, str) else r[1] for r in (requires or [])
                ]
                techs[name] = {
                    "era": int(era.split("_")[1]) if era.startswith("era_") else None,
                    "requires": [n for n in names if isinstance(n, str)],
                }
    for path in sorted(glob.glob(os.path.join(repo_root, "common", "technology", "technologies", "*.txt"))):
        with open(path, encoding="utf-8-sig") as fh:
            text = _COMMENT.sub("", fh.read())
        for match in _TECH_DEF.finditer(text):
            body = text[match.end() - 1: block_end(text, match.end() - 1)]
            entry = techs.setdefault(match.group(1), {"era": None, "requires": []})
            era = _ERA.search(body)
            if era:
                entry["era"] = int(era.group(1))
            unlocking = _UNLOCKING.search(body)
            if unlocking:
                for name in unlocking.group(1).split():
                    if name not in entry["requires"]:
                        entry["requires"].append(name)
    return techs


def prerequisites(tech: str, techs: dict) -> set:
    """Every technology `tech` requires, recursively (not `tech` itself)."""
    seen, stack = set(), list(techs.get(tech, {}).get("requires", []))
    while stack:
        name = stack.pop()
        if name not in seen:
            seen.add(name)
            stack.extend(techs.get(name, {}).get("requires", []))
    return seen


def assumed(required: list, techs: dict) -> tuple:
    """(prerequisites of the required techs, the era at or before which every
    tech is assumed, or None)."""
    closure = set()
    for tech in required:
        closure |= prerequisites(tech, techs)
    eras = [techs[t]["era"] for t in required if techs.get(t, {}).get("era")]
    return closure - set(required), _cutoff(max(eras) if eras else None)


def _cutoff(era):
    """The era at or before which every technology is assumed, given one of `era`."""
    return era - ERAS_BEHIND if era and era - ERAS_BEHIND >= 1 else None


def find_events(selector: str, repo_root=REPO_ROOT) -> list:
    """[(event id, file, body)] for an event id or a whole namespace."""
    namespace = selector.rsplit(".", 1)[0] if re.search(r"\.\d+$", selector) else selector
    pattern = re.compile(r"^(%s\.\d+)\s*=\s*\{" % re.escape(namespace), re.M)
    found = []
    for path in sorted(glob.glob(os.path.join(repo_root, "events", "**", "*.txt"), recursive=True)):
        with open(path, encoding="utf-8-sig") as fh:
            text = _COMMENT.sub("", fh.read())
        for match in pattern.finditer(text):
            if selector != namespace and match.group(1) != selector:
                continue
            body = text[match.end() - 1: block_end(text, match.end() - 1)]
            found.append((match.group(1), os.path.relpath(path, repo_root).replace("\\", "/"), body))
    found.sort(key=lambda e: int(e[0].rsplit(".", 1)[1]))
    return found


# ---------------------------------------------------------------------------
# What a set of tests guarantees
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Gate:
    """What is true when a set of tests has passed.

    `techs` holds each researched technology with its prerequisites. `era`
    says that some technology of that era or later is researched, which an
    `OR` of two era 9 technologies still guarantees though it names neither.
    `statements` are the other tests, as written."""
    techs: frozenset = frozenset()
    era: int | None = None
    absent: frozenset = frozenset()
    statements: tuple = ()

    def both(self, other: Gate) -> Gate:
        """This and `other` together."""
        eras = [e for e in (self.era, other.era) if e]
        statements = self.statements + tuple(s for s in other.statements if s not in self.statements)
        return Gate(self.techs | other.techs, max(eras) if eras else None, self.absent | other.absent, statements)

    def either(self, other: Gate) -> Gate:
        """One of this and `other`, the reader not knowing which: what both give."""
        era = min(self.era, other.era) if self.era and other.era else None
        statements = tuple(s for s in self.statements if s in other.statements)
        return Gate(self.techs & other.techs, era, self.absent & other.absent, statements)

    def technology(self) -> Gate:
        """The part that stays true: a technology is never lost."""
        return Gate(self.techs, self.era)

    def __bool__(self) -> bool:
        return bool(self.techs or self.era or self.absent or self.statements)


NOTHING = Gate()


def _either_of(gates: list) -> Gate:
    if not gates:
        return NOTHING
    out = gates[0]
    for gate in gates[1:]:
        out = out.either(gate)
    return out


@dataclass
class Reading:
    """One trigger block: what it shows the writer, and the Gate it amounts to."""
    required: list = field(default_factory=list)
    absent: list = field(default_factory=list)
    one_of: list = field(default_factory=list)        # [[tech, ...], ...], one list per OR
    one_of_gates: list = field(default_factory=list)  # what each OR guarantees whichever holds
    other: list = field(default_factory=list)
    sources: list = field(default_factory=list)       # labeled lines: laws, scripted triggers, pools
    gate: Gate = NOTHING

    def add(self, more: Reading) -> None:
        self.required += more.required
        self.absent += more.absent
        self.one_of += more.one_of
        self.one_of_gates += more.one_of_gates
        self.other += more.other
        self.sources += more.sources
        self.gate = self.gate.both(more.gate)

    def state(self, text: str) -> None:
        self.other.append(text)
        self.gate = self.gate.both(Gate(statements=(text,)))


@dataclass
class Route:
    """One way the event is reached."""
    kind: str        # journal_entry | on_action | event | repeat | scope | not_followed
    name: str
    where: str       # file:line of the dispatch, or of the outermost call
    head: str
    gate: Gate = NOTHING
    followed: bool = True
    lines: list = field(default_factory=list)   # [(label, text)]
    via: list = field(default_factory=list)     # scripted effects passed through, nearest the event first
    count: int = 1
    switch: str | None = None                   # the scope change between the origin and the event, if any


def render(node: Node) -> str:
    """A script node back as one line of script."""
    if node.children is not None:
        inner = " ".join(render(child) for child in node.children)
        head = f"{node.key} {node.op} " if node.key else ""
        return f"{head}{{ {inner} }}" if inner else f"{head}{{ }}"
    if not node.op:
        return node.key
    value = node.value or ""
    return f"{node.key} {node.op} " + (f'"{value}"' if " " in value or not value else value)


def _split_prefix(key: str) -> tuple:
    match = _PREFIX.match(key)
    return (match.group(0), key[match.end():]) if match else ("", key)


def _number(text) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _dispatches(node: Node, event_id: str) -> bool:
    """Whether a node fires the event: a `trigger_event`, an entry of an
    on-action's list, or the event passed to a scripted effect as an argument."""
    if node.key == "trigger_event":
        return node.value == event_id or any(c.key == "id" and c.value == event_id for c in node.children or [])
    return node.children is None and event_id in (node.key, node.value)


def _block(node: Node, key: str) -> list:
    """The lines of every `key = { ... }` directly inside `node`."""
    return [line for child in node.children or [] if child.key == key and child.children is not None
            for line in child.children]


def _is_pair(entry) -> bool:
    return isinstance(entry, list) and len(entry) == 2 and isinstance(entry[0], str) and entry[0] in fsa._OPERATORS


def _json_nodes(body: dict) -> list:
    """A vanilla_parsed block (`{key: [op, value]}`, a repeated key as a list
    of such pairs) as script nodes. The order of repeated keys among the
    others is not kept; nothing here depends on it."""
    nodes = []
    for key, entry in body.items():
        for op, value in ([entry] if _is_pair(entry) else entry):
            if isinstance(value, dict):
                nodes.append(Node(key, op, None, _json_nodes(value), 0))
            elif isinstance(value, list):
                nodes.append(Node(key, op, None, [Node(str(item), "", None, None, 0) for item in value], 0))
            else:
                nodes.append(Node(key, op, str(value).strip('"'), None, 0))
    return nodes


def _snapshot(repo_root: str, name: str) -> dict:
    """One file of the tree's committed vanilla snapshot, or {} without one."""
    path = os.path.join(repo_root, "vanilla_parsed", "common", name)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_laws(repo_root=REPO_ROOT) -> dict:
    """{law: {"technologies": [...], "laws": [...], "parent": law | None}} for
    vanilla and the mod. An INJECTed list adds to the law's own
    (scripting_best_practices.md, "List fields append")."""
    laws = {}
    for name, (_, body) in _snapshot(repo_root, "laws.json").items():
        laws[name] = {
            "technologies": [t for t in body.get("unlocking_technologies", [None, []])[1] if isinstance(t, str)],
            "laws": [t for t in body.get("unlocking_laws", [None, []])[1] if isinstance(t, str)],
            "parent": body.get("parent", [None, None])[1],
        }
    for path in sorted(glob.glob(os.path.join(repo_root, "common", "laws", "*.txt"))):
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            nodes = parse_script(fh.read())
        for node in nodes:
            if node.children is None:
                continue
            prefix, name = _split_prefix(node.key)
            if prefix not in _APPENDING or name not in laws:
                laws[name] = {"technologies": [], "laws": [], "parent": None}
            entry = laws[name]
            for key, into in (("unlocking_technologies", "technologies"), ("unlocking_laws", "laws")):
                for item in _block(node, key):
                    if item.key and item.key not in entry[into]:
                        entry[into].append(item.key)
            for child in node.children:
                if child.key == "parent" and child.value:
                    entry["parent"] = child.value
    return laws


# ---------------------------------------------------------------------------
# The mod's script, read on demand
# ---------------------------------------------------------------------------


class Script:
    """The mod's script under one root: its laws, scripted triggers, journal
    entries and dispatch graph, each loaded the first time it is asked for.

    `follow=False` reads an event's own trigger only, as the tool did before
    #1622: no law, no scripted trigger, no route."""

    def __init__(self, repo_root=REPO_ROOT, techs: dict | None = None, follow: bool = True):
        self.root = repo_root
        self.techs = load_technologies(repo_root) if techs is None else techs
        self.follow = follow
        self._files: dict = {}
        self._effect_routes: dict = {}
        self._cycles = 0

    # ---- sources ----------------------------------------------------------

    @cached_property
    def laws(self) -> dict:
        return load_laws(self.root) if self.follow else {}

    @cached_property
    def triggers(self) -> dict:
        if not self.follow:
            return {}
        found = fsa._definitions(Path(self.root), "scripted_triggers")
        return {_split_prefix(name)[1]: body for name, body in found.items()}

    @cached_property
    def graph(self) -> eca.Graph:
        return eca.build_graph(self.root)

    @cached_property
    def journal_entries(self) -> dict:
        """{entry: [(prefix, lines)]} for the mod's definitions."""
        found: dict = {}
        for path in sorted(glob.glob(os.path.join(self.root, "common", "journal_entries", "*.txt"))):
            for node in self.nodes(os.path.relpath(path, self.root).replace("\\", "/")):
                if node.children is not None and node.key:
                    prefix, name = _split_prefix(node.key)
                    found.setdefault(name, []).append((prefix, node))
        return found

    @cached_property
    def entry_adds(self) -> dict:
        """{entry: [(file, line)]} for every `add_journal_entry` outside the
        console benches, which add entries no player's game does."""
        found: dict = {}
        for base in ("common", "events"):
            for path in sorted(glob.glob(os.path.join(self.root, base, "**", "*.txt"), recursive=True)):
                if os.path.basename(path).startswith("te_debug_"):
                    continue
                with open(path, encoding="utf-8-sig", errors="replace") as fh:
                    text = eca._strip_comments(fh.read())
                rel = os.path.relpath(path, self.root).replace("\\", "/")
                for match in _ADD_ENTRY.finditer(text):
                    found.setdefault(match.group(1), []).append((rel, text.count("\n", 0, match.start()) + 1))
        return found

    def nodes(self, rel: str) -> list:
        if rel not in self._files:
            try:
                with open(os.path.join(self.root, rel), encoding="utf-8-sig", errors="replace") as fh:
                    self._files[rel] = parse_script(fh.read())
            except OSError:
                self._files[rel] = []
        return self._files[rel]

    # ---- technology -------------------------------------------------------

    def with_era(self, name: str) -> str:
        era = self.techs.get(name, {}).get("era")
        return f"{name} (era {era})" if era else f"{name} (unknown technology)"

    def tech_gate(self, name: str) -> Gate:
        info = self.techs.get(name)
        if not info:
            return Gate(techs=frozenset({name}))
        return Gate(frozenset({name}) | prerequisites(name, self.techs), info["era"])

    def leading(self, techs) -> list:
        """The technologies of a set that are no other member's prerequisite,
        latest era first."""
        behind = set()
        for name in techs:
            behind |= prerequisites(name, self.techs)
        return sorted(set(techs) - behind, key=lambda t: (-(self.techs.get(t, {}).get("era") or 0), t))

    def gives(self, gate: Gate) -> str:
        """A Gate's technology in words, or ''."""
        parts = []
        lead = self.leading(gate.techs)
        if lead:
            parts.append(", ".join(self.with_era(t) for t in lead)
                         + (" and what they require" if len(gate.techs) > len(lead) else ""))
        named = max((self.techs.get(t, {}).get("era") or 0 for t in gate.techs), default=0)
        cutoff = _cutoff(gate.era)
        if cutoff and gate.era > named:
            parts.append(f"a technology of era {gate.era} or later")
        if cutoff:
            parts.append(f"every technology of era {cutoff} or earlier")
        return "; ".join(parts)

    # ---- laws -------------------------------------------------------------

    def law_gate(self, name: str, seen: frozenset = frozenset()) -> Gate:
        """The technology a law's enactment needed: all of its unlocking
        technologies, and what every one of its unlocking laws needed."""
        law = self.laws.get(name)
        if not law:
            return NOTHING
        gate = NOTHING
        for tech in law["technologies"]:
            gate = gate.both(self.tech_gate(tech))
        if law["laws"] and len(seen) < LAW_DEPTH:
            # A law that unlocks itself in a circle adds nothing the others lack.
            others = [self.law_gate(other, seen | {name}) for other in law["laws"] if other not in seen and other != name]
            gate = gate.both(_either_of(others))
        return gate.technology()

    def law_source(self, name: str, mode: str) -> dict:
        law = self.laws.get(name)
        label = f"law {name} unlocks at" if mode == "being enacted" else f"law {name} (in force) unlocks at"
        source = {"kind": "law", "name": name, "mode": mode, "label": label, "technologies": [], "laws": []}
        if not law:
            source["text"] = "not found in the mod's laws or the snapshot: nothing is taken from it"
            return source
        source["technologies"], source["laws"] = list(law["technologies"]), list(law["laws"])
        parts = [", ".join(self.with_era(t) for t in law["technologies"]) or "no technology"]
        if law["laws"]:
            one = len(law["laws"]) == 1
            parts.append(("the law " if one else "one of the laws ") + ", ".join(law["laws"]))
            behind = self.gives(_either_of([self.law_gate(other, frozenset({name})) for other in law["laws"]]))
            if behind:
                parts.append(("that law needs " if one else "each of those laws needs ") + behind)
        text = "; ".join(parts)
        if mode == "in force" and (law["technologies"] or law["laws"]):
            text += " (unless the country began the game with the law or an effect gave it)"
        source["text"] = text
        return source

    def law_variants(self, name: str) -> list:
        return [name] + sorted(other for other, law in self.laws.items() if law["parent"] == name)

    # ---- trigger blocks ---------------------------------------------------

    def read_block(self, nodes: list, depth: int = 0, seen: frozenset = frozenset()) -> Reading:
        """A trigger block's lines, read together in the scope they are written in."""
        reading = Reading()
        for node in nodes:
            self._read_node(node, reading, depth, seen)
        return reading

    def _read_node(self, node: Node, reading: Reading, depth: int, seen: frozenset) -> None:
        key, kids, value = node.key, node.children, node.value
        plain = node.op in ("=", "?=", "==")
        if key == "has_technology_researched" and value and plain:
            reading.required.append(value)
            reading.gate = reading.gate.both(self.tech_gate(value))
        elif key in ("NOT", "NOR") and kids is not None:
            names = [k.value for k in kids if k.key == "has_technology_researched" and k.value]
            reading.absent += names
            reading.gate = reading.gate.both(Gate(absent=frozenset(names)))
            if len(names) != len(kids):
                reading.state(render(node))
        elif key == "AND" and kids is not None:
            for kid in kids:
                self._read_node(kid, reading, depth, seen)
        elif key in _SAME_SCOPE_WRAPPERS and kids is not None:
            for kid in kids:
                if kid.key not in _WRAPPER_FIELDS:
                    self._read_node(kid, reading, depth, seen)
        elif key == "OR" and kids is not None:
            self._read_or(node, reading, depth, seen)
        elif key in _LAW_TESTS and value and value.startswith("law_type:") and plain and self.follow:
            law, mode = value[len("law_type:"):], _LAW_TESTS[key]
            names = self.law_variants(law) if key == "has_law_or_variant" else [law]
            reading.sources += [self.law_source(name, mode) for name in names]
            reading.state(render(node))
            reading.gate = reading.gate.both(_either_of([self.law_gate(name) for name in names]))
        elif key == "has_journal_entry" and value and plain and self.follow:
            lines, gate = self.entry_reading(value)
            reading.sources += [{"kind": "journal_entry", "name": value, "label": label, "text": text}
                                for label, text in lines]
            reading.state(render(node))
            reading.gate = reading.gate.both(gate)
        elif key in self.triggers and key not in seen and depth < TRIGGER_DEPTH and (value == "yes" or kids is not None):
            body = self.triggers[key]
            if kids is not None:
                body = fsa._substitute(body, {k.key: k.value for k in kids if k.value is not None})
            inner = self.read_block(body, depth + 1, seen | {key})
            reading.sources.append({
                "kind": "scripted_trigger", "name": key, "label": f"scripted trigger {key} tests",
                "text": self.line(inner) or "nothing", "adds": bool(inner.gate.techs or inner.gate.era or inner.gate.absent),
            })
            reading.sources += inner.sources
            reading.state(render(node))
            reading.gate = reading.gate.both(Gate(inner.gate.techs, inner.gate.era, inner.gate.absent))
        else:
            reading.state(render(node))

    def _read_or(self, node: Node, reading: Reading, depth: int, seen: frozenset) -> None:
        alternatives = [self.read_block([kid], depth, seen) for kid in node.children]
        gate = _either_of([alt.gate for alt in alternatives])
        names = [name for alt in alternatives for name in alt.required + [n for group in alt.one_of for n in group]]
        if names:
            reading.one_of.append(names)
            reading.one_of_gates.append(gate)
        for alt in alternatives:
            reading.sources += alt.sources
        reading.state(render(node))
        reading.gate = reading.gate.both(Gate(gate.techs, gate.era, gate.absent))

    def line(self, reading: Reading, width: int = 110) -> str:
        """A Reading on one line."""
        parts = []
        parts += [self.with_era(t) for t in dict.fromkeys(reading.required)]
        parts += [f"NOT {t}" for t in dict.fromkeys(reading.absent)]
        for names in reading.one_of:
            parts.append("one of " + ", ".join(self.with_era(t) for t in dict.fromkeys(names)))
        for statement in dict.fromkeys(reading.other):
            if statement == "always = yes":
                continue
            if reading.one_of and statement.startswith("OR = {") and "has_technology_researched" in statement:
                continue
            parts.append(statement if len(statement) <= width else statement[:width - 3] + "...")
        return "; ".join(parts)

    def source_lines(self, reading: Reading, only_adding: bool = False) -> list:
        """[(label, text)] for the laws and scripted triggers a Reading opened."""
        seen, lines = set(), []
        for source in reading.sources:
            if only_adding and source["kind"] == "scripted_trigger" and not source.get("adds"):
                continue
            pair = (source["label"], source["text"])
            if pair not in seen:
                seen.add(pair)
                lines.append(pair)
        return lines

    # ---- the tests between an entity and a dispatch -------------------------

    def locate(self, rel: str, line: int, match, entity: str | None = None) -> list | None:
        """The chain of nodes from a top-level entity of `rel` down to the
        deepest node on `line` that `match` accepts."""
        for top in self.nodes(rel):
            if top.children is None or top.line > line or (entity is not None and top.key != entity):
                continue
            chain = self._descend(top, line, match, [])
            if chain:
                return chain
        return None

    def _descend(self, node: Node, line: int, match, trail: list) -> list | None:
        trail = trail + [node]
        for child in node.children or []:
            if child.line > line:
                break
            found = self._descend(child, line, match, trail)
            if found:
                return found
        return trail if node.line == line and len(trail) > 1 and match(node) else None

    def chain_reading(self, chain: list, site_switches=None, helper: Node | None = None,
                      event_id: str | None = None, depth: int = 0) -> tuple:
        """(what the tests between the entity and the dispatch guarantee about
        the receiver, the scope change on the way or None).

        A test above a scope change (`random_country = { ... }`) is about
        someone else, so reading starts again there; the limit of the scope
        change itself is the receiver's. `helper` is a scripted effect the
        chain ends in a call of, which fires the event it is handed as an
        argument: its own tests are read with the arguments filled in."""
        reading, switch, switches = Reading(), None, 0
        for index in range(1, len(chain) - 1):
            parent, node = chain[index - 1], chain[index]
            key = node.key
            if key in self.graph.effect_file:
                helper = node  # the event is an argument of this call: what follows is inside the effect
                break
            if key in ("if", "else_if", "while"):
                if key == "else_if":
                    self._state_failed_siblings(parent, node, reading)
                reading.add(self.read_block(_block(node, "limit")))
            elif key == "else":
                self._state_failed_siblings(parent, node, reading)
            elif parent.key == "random_list" and _number(key) is not None:
                reading.add(self.read_block(_block(node, "trigger")))
                if _number(key) == 0:
                    reading.add(self.pool(node))
            elif key == "outcome":
                reading.add(self.read_block(_block(node, "trigger")))
            elif key and (eca._is_switch(key) or key in _INVOLVED_HOOKS):
                reading, switch, switches = Reading(), key, switches + 1
                reading.add(self.read_block(_block(node, "limit")))
        if helper is not None:
            inside = self._through_helper(helper, event_id, depth) if event_id else None
            if inside is None:
                # Unread: the graph still says whether the effect changes scope before it fires the event.
                if site_switches is not None and len(site_switches) > switches:
                    reading, switch = Reading(), f"{site_switches[-1]}, inside scripted effect {helper.key}"
            elif inside[1]:
                reading, switch = inside[0], f"{inside[1]}, inside scripted effect {helper.key}"
            else:
                reading.add(inside[0])
        return reading, switch

    def effect_node(self, name: str) -> Node | None:
        rel = self.graph.effect_file.get(name)
        for top in self.nodes(rel) if rel else []:
            if top.children is not None and _split_prefix(top.key)[1] == name:
                return top
        return None

    def _through_helper(self, call: Node, event_id: str, depth: int) -> tuple | None:
        """(Reading, scope change or None) for a scripted effect that fires
        the event from its arguments (`helper = { EVENT = ns.4 }`), read with
        the call's arguments filled in. None when the event is not found in
        it. An effect that fires it from several places gives what all of
        them test."""
        top = self.effect_node(call.key)
        if top is None or depth >= 4:
            return None
        args = {kid.key: kid.value for kid in call.children or [] if kid.value is not None}
        body = Node(call.key, "=", None, fsa._substitute(top.children, args), top.line)
        chains: list = []
        self._collect(body, lambda node: _dispatches(node, event_id), [], chains)
        if not chains:
            return None
        found = [self.chain_reading(chain, None, None, event_id, depth + 1) for chain in chains]
        if len(found) == 1:
            return found[0]
        gate = _either_of([reading.gate for reading, _ in found])
        merged = Reading(gate=Gate(gate.techs, gate.era, gate.absent))
        merged.state(f"{call.key} fires it from {len(found)} places: only what all of them test is kept")
        return merged, next((switch for _, switch in found if switch), None)

    def _collect(self, node: Node, match, trail: list, into: list) -> None:
        """Every chain from `node` down to a deepest node `match` accepts."""
        trail = trail + [node]
        before = len(into)
        for child in node.children or []:
            self._collect(child, match, trail, into)
        if len(into) == before and len(trail) > 1 and match(node):
            into.append(trail)

    @staticmethod
    def _state_failed_siblings(parent: Node, node: Node, reading: Reading) -> None:
        """An `else` runs when the `if` and every `else_if` above it failed."""
        index = next(i for i, child in enumerate(parent.children) if child is node)
        failed = []
        while index > 0 and parent.children[index - 1].key in ("if", "else_if"):
            index -= 1
            limit = _block(parent.children[index], "limit")
            if limit:
                failed.append(("NOT" if len(limit) == 1 else "NAND") + " = { " + " ".join(render(n) for n in limit) + " }")
            if parent.children[index].key == "if":
                break
        for statement in reversed(failed):
            reading.state(statement)

    def pool(self, entry: Node) -> Reading:
        """A `random_list` draw of base weight 0: it is drawn only when an
        `add` in its `modifier` runs, so the tests around the adds are
        requirements, one set of them at least."""
        adds, unread = [], []

        def walk(nodes: list, tests: list) -> None:
            tests = tests + [line for node in nodes if node.key == "trigger" and node.children is not None
                             for line in node.children]
            for node in nodes:
                if node.key in ("trigger", "limit", "desc"):
                    continue
                if node.key == "add":
                    amount = _number(node.value) if node.children is None else None
                    if amount is None or amount > 0:
                        adds.append((tests, node))
                elif node.key in ("if", "else_if"):
                    walk([child for child in node.children or [] if child.key != "limit"], tests + _block(node, "limit"))
                elif node.key == "else":
                    walk(node.children or [], tests)
                else:
                    unread.append(node.key)

        for child in entry.children or []:
            if child.key == "modifier" and child.children is not None:
                walk(child.children, [])
        reading = Reading()
        if unread:
            reading.sources.append({
                "kind": "pool", "label": "pool weight", "followed": False,
                "text": "base weight 0, but its modifier uses " + ", ".join(sorted(set(unread)))
                        + ", which the tool does not read: nothing is taken from it"})
            return reading
        if not adds:
            reading.sources.append({"kind": "pool", "label": "pool weight",
                                    "text": "base weight 0 and nothing adds to it: never drawn"})
            return reading
        branches = [self.read_block(tests) for tests, _ in adds]
        texts = []
        for branch in branches:
            text = self.line(branch) or "no test at all"
            if text not in texts:
                texts.append(text)
        reading.sources.append({
            "kind": "pool", "label": "pool weight tests",
            "text": texts[0] if len(texts) == 1 else "one of [ " + " ] or [ ".join(texts) + " ]"})
        for branch in branches:
            reading.sources += [s for s in branch.sources if s["kind"] != "scripted_trigger" or s.get("adds")]
        named = [name for branch in branches for name in branch.required]
        for branch, (_, add) in zip(branches, adds):
            missing = sorted({name for name in named if name not in branch.gate.techs})
            if missing:
                amount = add.value if add.children is None else "a computed amount"
                reading.sources.append({
                    "kind": "pool_flag", "label": "! weight added outside that gate",
                    "text": f"+{amount} on line {add.line} does not test {', '.join(missing)}: "
                            + (self.line(branch) or "no test at all")})
        gate = _either_of([branch.gate for branch in branches])
        reading.gate = Gate(gate.techs, gate.era, gate.absent)
        return reading

    # ---- journal entries and on-actions -------------------------------------

    def entry_reading(self, entity: str) -> tuple:
        """([(label, text)], Gate) for a journal entry: what its activation
        tested. A technology is all that is kept: the rest was true then."""
        name = _split_prefix(entity)[1]
        mine = self.journal_entries.get(name, [])
        blocks = [node for _, node in mine]
        if not mine or all(prefix in _APPENDING for prefix, _ in mine):
            vanilla = _snapshot(self.root, "journal_entries.json").get(name)
            if vanilla:
                blocks.append(Node(name, "=", None, _json_nodes(vanilla[1]), 0))
        tests = [line for block in blocks for key in ("is_shown_when_inactive", "possible") for line in _block(block, key)]
        lines, gates = [], []
        if tests:
            reading = self.read_block(tests)
            lines.append((f"journal entry {name} requires", (self.line(reading) or "nothing") + " (when it activated)"))
            lines += self.source_lines(reading)
            gates.append(reading.gate)
        elif blocks:
            lines.append((f"journal entry {name}", "has no `possible` and no `is_shown_when_inactive`: only an effect adds it"))
        else:
            lines.append((f"journal entry {name}", "is not in the mod's files or the snapshot"))
        for rel, line in self.entry_adds.get(name, []):
            chain = self.locate(rel, line, lambda node: node.key == "add_journal_entry")
            reading = self.chain_reading(chain)[0] if chain else Reading()
            lines.append(("also added by effect", f"{rel}:{line}, which skips both: "
                          + (self.line(reading) or "no test the tool can read")))
            lines += self.source_lines(reading, only_adding=True)
            gates.append(reading.gate)
        return lines, _either_of(gates).technology()

    def on_action_reading(self, top: Node, name: str) -> tuple:
        """([(label, text)], Gate) for the on-action block a dispatch sits in."""
        lines = []
        reading = self.read_block(_block(top, "trigger"))
        if reading.gate or reading.other:
            lines.append((f"on-action {name} requires", self.line(reading)))
            lines += self.source_lines(reading)
        parents = sorted({parent for parent, _, _ in self.graph.on_action_parents.get(name, [])})
        if parents:
            lines.append(("called from", "on-action " + ", ".join(parents) + " (its trigger is not read)"))
        return lines, reading.gate

    # ---- routes -----------------------------------------------------------

    def routes(self, event_id: str) -> list:
        """Every way the event is reached, like routes merged."""
        found = []
        for site in self.graph.sites_by_event.get(event_id, []):
            found += self._routes_from(site.file, site.line, site.entity, site.entity_kind,
                                       ("event", event_id), site.switches, frozenset(), site.via)
        merged: dict = {}
        for route in found:
            if route.kind == "event" and route.name == event_id and not route.switch:
                # The event sending itself to the same country again: whatever held the first time still does.
                route.kind = "repeat"
                route.head = (f"sent by: itself ({route.where}), to the same country: a repeat, "
                              "which adds nothing and takes nothing away")
            key = (route.kind, route.name, route.head.replace(route.where, ""), route.gate,
                   tuple(route.lines), tuple(re.sub(r":\d+\)", ")", step) for step in route.via))
            if key in merged:
                merged[key].count += 1
            else:
                merged[key] = route
        return list(merged.values())

    def _routes_from(self, rel, line, entity, kind, target, switches, stack, via="trigger_event") -> list:
        """The routes through one dispatch of the event, or one call of a
        scripted effect that leads to it, at rel:line inside `entity`."""
        where = f"{rel}:{line}"
        kind_text = _KIND_TEXT.get(kind, kind.replace("_", " "))
        name = _split_prefix(entity)[1]
        helper = None
        if target[0] == "event":
            chain = self.locate(rel, line, lambda n: _dispatches(n, target[1]), entity)
            if chain is None:  # the event is fired inside a scripted effect that this line calls with arguments
                chain = self.locate(rel, line, lambda n: n.key in self.graph.effect_file, entity)
                helper = chain[-1] if chain else None
        else:
            chain = self.locate(rel, line, lambda n: n.key == target[1], entity)
        if chain is None:
            return [Route("not_followed", name, where, followed=False,
                          head=f"not followed: {kind_text} {name} ({where}): the tool could not find the dispatch there")]
        local, switch = self.chain_reading(chain, switches, helper, target[1] if target[0] == "event" else None)
        lines = []
        if self.line(local):
            label = "tests at the dispatch" if target[0] == "event" else f"tests where {target[1]} is called"
            lines.append((label, self.line(local)))
        lines += [pair for pair in self.source_lines(local, only_adding=True) if pair not in lines]
        gate = local.gate.technology()
        if kind == "event":
            into = f", into {switch}" if switch else ""
            return [Route("event", name, where, gate=gate, lines=lines, switch=switch,
                          head=f"sent by: {name} ({where}){into}: nothing of the sender's own technology carries over")]
        if switch:
            return [Route("scope", name, where, gate=gate, lines=lines, switch=switch,
                          head=f"{kind_text} {name} ({where}) fires it in another scope ({switch}): "
                               f"what {name} requires is its own country's, not the receiver's")]
        if kind == "journal_entry":
            more, entry_gate = self.entry_reading(entity)
            return [Route("journal_entry", name, where, gate=gate.both(entry_gate), lines=lines + more,
                          head=f"journal entry {name} ({where})")]
        if kind == "on_action":
            more, action_gate = self.on_action_reading(chain[0], name)
            pool = "" if via == "trigger_event" else f", {via}"
            return [Route("on_action", name, where, gate=gate.both(action_gate.technology()), lines=lines + more,
                          head=f"on-action {name} ({where}{pool})")]
        if kind == "scripted_effect":
            step = f"scripted effect {name} ({where})"
            return [Route(r.kind, r.name, r.where, r.head, gate.both(r.gate), r.followed, lines + r.lines,
                          [step] + r.via, switch=r.switch)
                    for r in self._effect_callers(entity, stack)]
        return [Route("not_followed", name, where, followed=False,
                      head=f"not followed: {kind_text} {name} ({where}): the tool does not open a {kind_text}")]

    def _effect_callers(self, effect: str, stack: frozenset) -> list:
        """The routes into a scripted effect, one or more per call of it."""
        if effect in self._effect_routes:
            return self._effect_routes[effect]
        calls = self.graph.effect_calls.get(effect, [])
        if not calls:
            return [Route("not_followed", effect, "", followed=False,
                          head=f"not followed: nothing the tool can find calls scripted effect {effect}")]
        cycles, routes = self._cycles, []
        for index, (rel, line, _path, switches, _conds, entity, kind, _params) in enumerate(calls):
            if len(routes) >= MAX_ROUTES:
                routes.append(Route("not_followed", effect, "", followed=False,
                                    head=f"not followed: {len(calls) - index} more call(s) of scripted effect {effect}"))
                break
            if entity == effect or entity in stack:
                self._cycles += 1  # a call from inside the loop adds nothing its other callers lack
                continue
            routes += self._routes_from(rel, line, entity, kind, ("call", effect), switches, stack | {effect})
        if not routes:
            routes = [Route("not_followed", effect, "", followed=False,
                            head=f"not followed: scripted effect {effect} is only called from a loop it is part of")]
        if cycles == self._cycles:  # a list cut short by a loop is right for this stack only
            self._effect_routes[effect] = routes
        return routes


# ---------------------------------------------------------------------------
# One event
# ---------------------------------------------------------------------------


def _event_lines(body: str) -> list:
    nodes = parse_script(body)
    return nodes[0].children or [] if nodes and not nodes[0].key and nodes[0].children is not None else nodes


def read_trigger(body: str, script: Script | None = None) -> dict:
    """The event's own `trigger`: required, forbidden and one-of technologies,
    its other top-level statements, and with a `script` the laws and scripted
    triggers it names (`sources`) and the Gate it all amounts to."""
    script = script or Script(REPO_ROOT, techs={}, follow=False)
    trigger = [node for node in _event_lines(body) if node.key == "trigger" and node.children is not None]
    reading = script.read_block(trigger[0].children) if trigger else Reading()
    return {"required": reading.required, "absent": reading.absent, "one_of": reading.one_of,
            "one_of_gates": reading.one_of_gates, "other": reading.other, "has_trigger": bool(trigger),
            "sources": reading.sources, "gate": reading.gate, "reading": reading}


def _variants(lines: list) -> list:
    """[(part, loc key, trigger lines)] for every text shown under a test of
    its own: a `triggered_desc`, an option."""
    found = []

    def walk(nodes: list, part: str) -> None:
        for node in nodes:
            if node.key == "triggered_desc" and node.children is not None:
                key = next((c.value for c in node.children if c.key == "desc" and c.value), None)
                found.append((part, key, _block(node, "trigger")))
            if node.children:
                walk(node.children, part)

    for node in lines:
        if node.key in ("title", "desc", "flavor") and node.children is not None:
            walk(node.children, node.key)
        elif node.key == "option" and node.children is not None:
            name = next((c.value for c in node.children if c.key == "name" and c.value), None)
            if name is None:
                name = next((t.value for c in node.children if c.key == "name" and c.children
                             for t in c.children if t.key == "text" and t.value), None)
            found.append(("option", name, _block(node, "trigger")))
    return found


def _technology_json(script: Script, gate: Gate) -> dict:
    return {
        "technologies": sorted(gate.techs, key=lambda t: (script.techs.get(t, {}).get("era") or 0, t)),
        "era": gate.era,
        "assume_through_era": _cutoff(gate.era),
    }


def analyze(event_id: str, path: str, body: str, script: Script) -> dict:
    """Everything the tool knows about one event, as plain data (`--json`)."""
    trigger = read_trigger(body, script)
    reading = trigger["reading"]
    closure, cutoff = assumed(reading.required, script.techs)
    out = {
        "event": event_id,
        "file": path,
        "trigger": {
            "present": trigger["has_trigger"],
            "required": reading.required,
            "prerequisites": sorted(closure, key=lambda t: (script.techs.get(t, {}).get("era") or 0, t)),
            "assume_through_era": cutoff,
            "absent": reading.absent,
            "one_of": [{"technologies": names, "whichever": _technology_json(script, gate)}
                       for names, gate in zip(reading.one_of, reading.one_of_gates)],
            "other": reading.other,
            "sources": reading.sources,
        },
    }
    if not script.follow:
        return out
    routes = script.routes(event_id)
    out["routes"] = [{
        "kind": route.kind, "name": route.name, "where": route.where, "head": route.head,
        "followed": route.followed, "count": route.count, "via": route.via,
        "lines": [{"label": label, "text": text} for label, text in route.lines],
        **_technology_json(script, route.gate),
    } for route in routes]
    unfollowed = [route.head for route in routes if not route.followed]
    first = [route.gate for route in routes if route.kind != "repeat"]
    outside = _either_of(first) if first and not unfollowed else NOTHING
    out["outside"] = {"routes": len(first), "not_followed": unfollowed, **_technology_json(script, outside)}
    total = reading.gate.both(outside)
    out["variants"] = []
    for part, key, tests in _variants(_event_lines(body)):
        own = script.read_block(tests)
        gate = own.gate
        if gate.techs - total.techs or (_cutoff(gate.era) or 0) > (_cutoff(total.era) or 0) or gate.absent - total.absent:
            out["variants"].append({"part": part, "key": key, "tests": script.line(own),
                                    "sources": own.sources, **_technology_json(script, gate)})
    out["guaranteed"] = {**_technology_json(script, total), "leading": script.leading(total.techs),
                         "absent": sorted(total.absent)}
    return out


def _shown(statement: str) -> str:
    return statement if len(statement) <= 150 else statement[:147] + "..."


def render_event(data: dict, script: Script) -> str:
    """One event's analysis as the text the CLI prints."""
    lines = [f"{data['event']}  ({data['file']})"]
    trigger = data["trigger"]
    if not trigger["present"]:
        lines.append("  no trigger of its own: everything depends on what fires it")
    elif trigger["required"]:
        lines.append("  requires:      " + ", ".join(script.with_era(t) for t in trigger["required"]))
        if trigger["prerequisites"]:
            lines.append("  so also has:   " + ", ".join(trigger["prerequisites"]))
        if trigger["assume_through_era"]:
            lines.append(f"  and may assume every technology of era {trigger['assume_through_era']} or earlier")
    else:
        lines.append("  requires no technology of its own" if "routes" in data
                     else "  requires no technology: assume none, whatever the subject suggests")
    if trigger["absent"]:
        lines.append("  must NOT have: " + ", ".join(script.with_era(t) for t in trigger["absent"]))
    for group in trigger["one_of"]:
        common = script.gives(Gate(frozenset(group["whichever"]["technologies"]), group["whichever"]["era"]))
        lines.append("  one of:        " + ", ".join(script.with_era(t) for t in group["technologies"])
                     + "  (guarantees none of them" + (f"; whichever it is: {common})" if common else ")"))
    for statement in trigger["other"]:
        lines.append("  also:          " + _shown(statement))
    for label, text in _unique((s["label"], s["text"]) for s in trigger["sources"]):
        lines.append(f"  {label}: {text}")
    if "routes" not in data:
        return "\n".join(lines)
    grouped: dict = {}
    for variant in data["variants"]:
        grouped.setdefault(variant["tests"], []).append(variant)
    for tests, variants in grouped.items():
        names = ", ".join(f"{v['key'] or 'an unnamed text'} ({v['part']})" for v in variants)
        lines.append(f"  only for {names}: {_shown(tests)}")
        for label, text in _unique((s["label"], s["text"]) for s in variants[0]["sources"]):
            lines.append(f"      {label}: {text}")
        lines.append("      gives: " + script.gives(Gate(frozenset(variants[0]["technologies"]), variants[0]["era"])))
    lines.append("  fired by:" if data["routes"] else "  fired by:      nothing the tool can find")
    for route in data["routes"]:
        more = f"  (and {route['count'] - 1} more like it)" if route["count"] > 1 else ""
        lines.append(f"    - {route['head']}{more}")
        for step in route["via"]:
            lines.append(f"        through {step}")
        for label, text in _unique((line["label"], line["text"]) for line in route["lines"]):
            lines.append(f"        {label}: {text}")
        gives = script.gives(Gate(frozenset(route["technologies"]), route["era"]))
        if route["followed"] and route["kind"] != "repeat":
            lines.append("        gives: " + (gives or "no technology"))
    outside = data["outside"]
    if not outside["routes"] and not outside["not_followed"]:
        lines.append("  from outside:  nothing is guaranteed: a console command, a vanilla script or a dispatch "
                     "the tool cannot see may fire it")
    elif outside["not_followed"]:
        lines.append(f"  from outside:  nothing is guaranteed: {len(outside['not_followed'])} of "
                     f"{outside['routes']} route(s) not followed")
    else:
        gives = script.gives(Gate(frozenset(outside["technologies"]), outside["era"]))
        every = "its one route gives" if outside["routes"] == 1 else f"all {outside['routes']} routes give"
        lines.append(f"  from outside:  {every} " + (gives or "no technology"))
    total = data["guaranteed"]
    gives = script.gives(Gate(frozenset(total["technologies"]), total["era"]))
    lines.append("  in all:        " + (gives or "no technology: assume none, whatever the subject suggests"))
    return "\n".join(lines)


def _unique(pairs) -> list:
    seen, out = set(), []
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    return out


def describe(event_id, path, body, techs, script: Script | None = None) -> str:
    """The text for one event. Without a `script`, its own trigger only."""
    script = script or Script(REPO_ROOT, techs=techs, follow=False)
    return render_event(analyze(event_id, path, body, script), script)


# ---------------------------------------------------------------------------
# The per-chain rows of event_text_guarantees.md
# ---------------------------------------------------------------------------

_BACKTICKED = re.compile(r"`([^`]+)`")
_ERA_CLAIM = re.compile(r"`([\w\-]+)`\s*\((?:[^()]*?,\s*)?era (\d+)")


def check_doc(text: str, script: Script, analyses) -> list:
    """Findings for the per-chain table: `analyses(namespace)` returns the
    chain's analyzed events. A technology a row's Guaranteed column names
    should be guaranteed to at least one event of the chains its Where column
    names, and a `tech (era N)` anywhere should carry the technology's era."""
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        for name, era in _ERA_CLAIM.findall(line):
            actual = script.techs.get(name, {}).get("era")
            if actual and actual != int(era):
                findings.append(f"line {number}: `{name}` is given as era {era}; it is era {actual}")
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 5 or cells[0] or set(cells[1]) <= set("-: ") or cells[1] == "Where":
            continue
        chains = []
        for token in _BACKTICKED.findall(cells[1]):
            name = token.split(".")[0] if re.fullmatch(r"[\w\-]+(?:\.\d+)?", token) else None
            if name and name not in chains and analyses(name):
                chains.append(name)
        if not chains:
            continue
        events = [event for chain in chains for event in analyses(chain)]
        for name in dict.fromkeys(_BACKTICKED.findall(cells[2])):
            if name not in script.techs:
                continue
            era = script.techs[name]["era"]
            if not any(_event_has(event, name, era) for event in events):
                findings.append(
                    f"line {number}: {', '.join(chains)}: the row guarantees `{name}`"
                    + (f" (era {era})" if era else "") + ", which the tool finds guaranteed to none of the "
                    f"{len(events)} event(s). Read the gate again, or it is one the tool does not follow.")
    return findings


def _event_has(event: dict, name: str, era) -> bool:
    """Whether one analyzed event is guaranteed `name`, in all or in one text."""
    for part in [event.get("guaranteed", {})] + event.get("variants", []):
        if name in part.get("technologies", []):
            return True
        through = part.get("assume_through_era")
        if through and era and era <= through:
            return True
    return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("selector", nargs="?", help="An event id (`ns.12`) or a namespace.")
    parser.add_argument("--tech", help="Show one technology's era and prerequisites instead.")
    parser.add_argument("--trigger", help="Show what one scripted trigger guarantees instead.")
    parser.add_argument("--json", action="store_true", help="Print the events' analysis as JSON.")
    parser.add_argument("--own", action="store_true", help="Read the event's own trigger only (no laws, no routes).")
    parser.add_argument("--check-doc", nargs="?", const=GUARANTEES_DOC, metavar="FILE",
                        help=f"Compare the per-chain rows of FILE (default {GUARANTEES_DOC}) with what the tool finds.")
    args = parser.parse_args(argv)

    script = Script(REPO_ROOT, follow=not args.own)
    techs = script.techs
    if args.tech:
        if args.tech not in techs:
            print(f"No technology named {args.tech}.", file=sys.stderr)
            return 1
        closure, cutoff = assumed([args.tech], techs)
        print(f"{args.tech}: era {techs[args.tech]['era']}")
        print("  requires, recursively: " + (", ".join(sorted(closure)) or "nothing"))
        if cutoff:
            print(f"  an event gated on it may assume every technology of era {cutoff} or earlier")
        return 0
    if args.trigger:
        if args.trigger not in script.triggers:
            print(f"No scripted trigger named {args.trigger} in common/scripted_triggers/.", file=sys.stderr)
            return 1
        reading = script.read_block(script.triggers[args.trigger], depth=1, seen=frozenset({args.trigger}))
        print(f"scripted trigger {args.trigger} tests: {script.line(reading, width=150) or 'nothing'}")
        for label, text in script.source_lines(reading):
            print(f"  {label}: {text}")
        print("  so, where it holds: " + (script.gives(reading.gate) or "no technology"))
        return 0
    if args.check_doc:
        cache: dict = {}
        known = {event_id.rsplit(".", 1)[0] for event_id in script.graph.events}

        def analyses(namespace: str) -> list:
            if namespace not in known:
                return []
            if namespace not in cache:
                cache[namespace] = [analyze(*event, script) for event in find_events(namespace)]
            return cache[namespace]

        with open(os.path.join(REPO_ROOT, args.check_doc), encoding="utf-8") as fh:
            findings = check_doc(fh.read(), script, analyses)
        print("\n".join(findings) if findings else f"{args.check_doc}: no row names a technology the tool cannot find.")
        if findings:
            print(f"\n{len(findings)} to read in {args.check_doc}. The rows are prose and this is a reading aid: "
                  "a finding is a row to check against the script, not a failure.")
        return 0
    if not args.selector:
        parser.error("give an event id, a namespace, --tech, --trigger or --check-doc")
    events = find_events(args.selector)
    if not events:
        print(f"No event matches {args.selector}.", file=sys.stderr)
        return 1
    data = [analyze(*event, script) for event in events]
    if args.json:
        json.dump(data, sys.stdout, indent=1)
        print()
    else:
        print("\n\n".join(render_event(event, script) for event in data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
