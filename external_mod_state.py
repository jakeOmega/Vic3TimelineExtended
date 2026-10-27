"""The merged result of loading another mod beside this one (#1184).

`GET /external-mod-overlap/state?path=<mod root>` on mod_state_server, and
`/state/<EntityType>[/<key>]` under it. `build()` returns a `LayeredState`:
a copy of the server's ModState in which every key the other mod's
`common/` defines holds what the engine ends up with when both mods load,
plus, per key, how that value came about.

The load order is external_mod_overlap's model, not a second one: for each
key, `scenario_loads()` gives every definition (vanilla's, ours, theirs) in
load order under each combination of the unknowns, `simulate()` says what
each one does (created, dropped_duplicate, redefined, replaced, injected,
skipped), and this module replays those steps with the parsed values,
merging an INJECT the way ModState does (`ParadoxFileParser.merge_data`, so a
script value appends its steps). With the probed settings that is one ASCII
file order with vanilla's files interleaved, bare definitions first (which
one wins per folder is BARE_DUPLICATE_RULES), then the directives in the
order `order_for_reading()` gives them. Nothing here restates the order, so
a change to the model's settings or readings carries through.

Where an unknown changes a key's value (a file both mods ship: which one the
playset loads later; a folder whose bare-duplicate rule BARE_DUPLICATE_RULES
doesn't record), the key's status is `undetermined`, its entry lists
every candidate, and the layered state holds the first scenario's value,
which `state_holds` names: the other mod loaded later, and the first bare
definition winning.

Scope:
- Only keys the other mod defines are recomputed, plus keys in a file of
  ours or vanilla's at a path the other mod also ships (that file is
  replaced whole). Every other key keeps the server's own value, so `/raw`
  and the layered state differ only where the other mod reaches.
- Entity types the server parses only. Events, on_actions, defines,
  history, gui and localization aren't layered; `not_layered` says why for
  each folder the other mod has. The report's event, on_action, define, loc
  and gui sections cover those.
- Vanilla's definitions come from the game files when installed (with file
  names), else from the server's parsed vanilla (one definition per key, read
  first, as external_mod_overlap's snapshot fallback has it). The server keeps
  no vanilla for scripted effects, triggers, GUIs and progress bars; without
  the game, vanilla is taken as absent there (`vanilla_source: unavailable`).
  Without the game files the snapshot names vanilla's files but not their
  keys: a file of theirs at a vanilla path is listed in
  `replaced_vanilla_files`, and vanilla's keys keep the server's value with
  a `caveat`.
- A file that doesn't parse is listed in `parse_failures`, and a key with a
  definition in it keeps the server's value (status `parse_failed`). So does
  a key one file repeats (`repeated_in_file`: two bare copies, or a repeated
  directive beside another one on the key), since the parser keeps one body
  per key and file. INJECTs alone fold in order and REPLACEs alone keep the
  last, as the engine applies them.
- A folder the other mod has that isn't layered gives its reason on the
  per-type and per-key routes too, not only in `not_layered`.
"""
from __future__ import annotations

import copy
import json
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

import external_mod_overlap as emo
from external_mod_overlap import OURS, THEIRS, VANILLA, Op
from mod_state import VANILLA_COMMON_DIRS, parser_for
from paradox_file_parser import INJECT_DIRECTIVES, REPLACE_DIRECTIVES

# Folder kinds (external_mod_overlap.rule_for) whose keys merge as one
# database entry each; the others aren't layered.
_LAYERED_KINDS = frozenset({"database", "script_values", "unknown"})
_NOT_LAYERED_REASON = {
    "defines": "per-key values, not entries: see the report's `defines`",
    "on_actions": "an on_action's event lists add up across files and ModState keeps one "
                  "file's hook: see `additive_hooks` and `on_action_conflicts`",
    "additive": "history blocks are effects that all run; the server doesn't parse them",
    "wrapper": "entries sit inside a wrapper block both mods repeat; the server doesn't "
               "parse this folder",
}
# A status per recomputed key, against the model's load of this mod without
# the other one.
STATUSES = ("changed", "added", "removed", "undetermined", "parse_failed", "repeated_in_file",
            "unchanged", "not_created")
# simulate()'s effects, by what replaying one does to the value.
_SETS_VALUE = frozenset({"created", "redefined", "replaced"})
_NO_VALUE_CHANGE = frozenset({"dropped_duplicate", "skipped_no_entry", "error_no_entry"})
# Status lists longer than this are cut in the summary (the per-type
# endpoint lists every key).
_SUMMARY_LIST_CAP = 200
_ABSENT = object()
# A directive one file may repeat with nothing else on the key: the parser's
# one body (INJECTs folded in order, the last REPLACE) is the engine's result.
_FOLDABLE = INJECT_DIRECTIVES | REPLACE_DIRECTIVES
_REPLACED_VANILLA_CAVEAT = (
    "Without the game files, vanilla's file names come from the snapshot manifest, which "
    "records no keys per file: a file of theirs at a vanilla file's path replaces it whole, "
    "but which of vanilla's keys go with it isn't known, so they keep the server's value.")
_SCOPE = (
    "Only the keys the other mod defines, and keys in a file of ours or vanilla's at a path it "
    "also ships, are recomputed; every other key is the server's own value (/raw). Events, "
    "on_actions, defines, history, gui and localization aren't layered. " + _REPLACED_VANILLA_CAVEAT
    + " A key one file repeats (two bare copies, or a repeated directive beside another one on "
    "the key) is `repeated_in_file` and keeps the server's value: the parser keeps one body per "
    "key and file.")
_STATE_HOLDS = {
    "later_mod": "theirs",
    "bare_duplicate": emo.FIRST_WINS,
    "note": "Where an unknown changes a key's value (status undetermined), the layered "
            "state holds the first scenario's: the other mod loaded later for a file both "
            "ship, and the first bare definition winning in a folder whose rule isn't "
            "recorded. The key's entry lists every candidate.",
}


def to_json(obj):
    """Parsed Paradox data (tuples) as JSON-ready lists, as /raw serves it."""
    if isinstance(obj, (tuple, list)):
        return [to_json(item) for item in obj]
    if isinstance(obj, dict):
        return {k: to_json(v) for k, v in obj.items()}
    return obj


def _fingerprint(value) -> str:
    """A comparable form of a value (or _ABSENT)."""
    if value is _ABSENT:
        return "<absent>"
    return json.dumps(to_json(value), sort_keys=True, ensure_ascii=False)


def parse_values(path: str, entity_type: str) -> tuple[Optional[dict], Optional[str]]:
    """({raw key: value}, None) for one script file, directives left on the
    keys (ModState.parse_mod_file), or (None, the error)."""
    parser = parser_for(entity_type)
    try:
        parser.parse_file(path, apply_directives=False)
    except Exception as exc:  # noqa: BLE001 - a foreign mod's file can hold anything
        return None, f"{type(exc).__name__}: {exc}"
    return parser.data, None


@dataclass
class KeyResult:
    entity_type: str
    db: str
    key: str
    status: str
    in_state: object                      # the value the layered state holds, or _ABSENT
    server: object                        # ms's value, or _ABSENT
    server_matches_model: Optional[bool]  # ms's value is the model's load without them
    without_them: list                    # the model's values for this mod alone
    definitions: list                     # [{side, file, line, directive}]
    load: list                            # the first scenario's simulated load
    in_vanilla: Optional[bool]
    depends_on: list = field(default_factory=list)
    candidates: list = field(default_factory=list)   # undetermined: one row per scenario
    state_holds: Optional[dict] = None
    failures: list = field(default_factory=list)
    caveat: Optional[str] = None

    def as_dict(self) -> dict:
        out = {
            "type": self.entity_type,
            "id": self.key,
            "layered": True,
            "status": self.status,
            "present": self.in_state is not _ABSENT,
            "value": None if self.in_state is _ABSENT else to_json(self.in_state),
            "server_present": self.server is not _ABSENT,
            "server_value": None if self.server is _ABSENT else to_json(self.server),
            "server_matches_model": self.server_matches_model,
            "in_vanilla": self.in_vanilla,
            "definitions": self.definitions,
            "load": self.load,
        }
        if self.server_matches_model is False:
            # The server's own merge (vanilla first, the last bare definition
            # kept) differs from the probed load order for this key even
            # without the other mod.
            out["model_without_them"] = [
                None if v is _ABSENT else to_json(v) for v in self.without_them]
        if self.status == "undetermined":
            out["depends_on"] = self.depends_on
            out["state_holds"] = self.state_holds
            out["candidates"] = self.candidates
        if self.failures:
            out["parse_failures" if self.status == "parse_failed" else "problems"] = self.failures
        if self.caveat:
            out["caveat"] = self.caveat
        return out

    def row(self) -> dict:
        out = {"key": self.key, "status": self.status}
        if self.status == "undetermined":
            out["depends_on"] = self.depends_on
        if self.server_matches_model is False:
            out["server_matches_model"] = False
        return out


@dataclass
class TypeLayer:
    entity_type: str
    db: str
    vanilla_source: str
    rule: dict
    server_holds_vanilla: bool = True
    keys: dict = field(default_factory=dict)    # key -> KeyResult
    # Without the game files: vanilla files theirs replaces by path, whose
    # keys the snapshot doesn't record.
    replaced_vanilla_files: list = field(default_factory=list)

    def summary(self) -> dict:
        out = {"entity_type": self.entity_type, "dir": f"common/{self.db}",
               "vanilla_source": self.vanilla_source, "rule": self.rule,
               "keys_layered": len(self.keys), "by_status": {}}
        if not self.server_holds_vanilla:
            out["server_holds_vanilla"] = False
            out["note"] = ("the server parses no vanilla for this type, so server_value lacks "
                           "vanilla's definitions and server_matches_model leaves them out too")
        if self.replaced_vanilla_files:
            out["replaced_vanilla_files"] = self.replaced_vanilla_files
            out["replaced_vanilla_note"] = _REPLACED_VANILLA_CAVEAT
        by: dict = {}
        for kr in self.keys.values():
            by.setdefault(kr.status, []).append(kr.key)
        out["by_status"] = {s: len(by[s]) for s in STATUSES if s in by}
        for status in STATUSES:
            if status in ("unchanged", "not_created") or status not in by:
                continue
            keys = sorted(by[status])
            out[status] = keys[:_SUMMARY_LIST_CAP]
            if len(keys) > _SUMMARY_LIST_CAP:
                out[f"{status}_truncated"] = len(keys) - _SUMMARY_LIST_CAP
        differs = sorted(k for k, kr in self.keys.items() if kr.server_matches_model is False)
        if differs:
            out["server_differs_from_model"] = differs[:_SUMMARY_LIST_CAP]
        return out


@dataclass
class LayeredState:
    """The server's ModState with another mod layered in (`mod_state`), and
    how each recomputed key came about (`types`)."""
    mod_state: object
    path: str
    mod_name: Optional[str]
    types: dict                          # entity type -> TypeLayer
    not_layered: list
    parse_failures: list
    scan_warnings: list
    built_in_s: float = 0.0
    # Server entity types whose folder the other mod has but that aren't
    # layered: {entity type: {dir, reason}}.
    not_layered_types: dict = field(default_factory=dict)

    def summary(self) -> dict:
        by: dict = {}
        differs = 0
        replaced = [{"entity_type": et, "file": f, "note": _REPLACED_VANILLA_CAVEAT}
                    for et in sorted(self.types) for f in self.types[et].replaced_vanilla_files]
        for layer in self.types.values():
            for kr in layer.keys.values():
                by[kr.status] = by.get(kr.status, 0) + 1
                differs += kr.server_matches_model is False
        return {
            "mod_name": self.mod_name,
            "path": self.path,
            "built_in_s": round(self.built_in_s, 2),
            "model": {
                "file_order": list(emo.file_orders()),
                "load_reading": list(emo.load_readings()),
                "see": emo.LOAD_ORDER_DOC,
            },
            "state_holds": _STATE_HOLDS,
            "scope": _SCOPE,
            "summary": {
                "entity_types_layered": len(self.types),
                "keys_layered": sum(len(t.keys) for t in self.types.values()),
                "by_status": {s: by[s] for s in STATUSES if s in by},
                "server_differs_from_model": differs,
                "not_layered": len(self.not_layered),
                "replaced_vanilla_files": len(replaced),
                "parse_failures": len(self.parse_failures),
                "scan_warnings": len(self.scan_warnings),
            },
            "entity_types": [self.types[et].summary() for et in sorted(self.types)],
            "not_layered": self.not_layered,
            "replaced_vanilla_files": replaced,
            "parse_failures": self.parse_failures,
        }

    def _not_layered(self, et: str) -> Optional[str]:
        row = self.not_layered_types.get(et)
        return f"{row['dir']} isn't layered: {row['reason']}" if row else None

    def entity_type(self, et: str) -> dict:
        layer = self.types.get(et)
        if layer is None:
            return {"entity_type": et, "layered": False,
                    "reason": self._not_layered(et)
                    or "the other mod defines nothing the server parses as this type",
                    "keys": []}
        return {**layer.summary(), "layered": True,
                "keys": [layer.keys[k].row() for k in sorted(layer.keys)]}

    def entity(self, et: str, key: str) -> Optional[dict]:
        """A key's merged entry, or None when neither the layered state nor
        the server has it."""
        layer = self.types.get(et)
        if layer is not None and key in layer.keys:
            return layer.keys[key].as_dict()
        data = self.mod_state.get_data(et) or {}
        unlayered = self._not_layered(et)
        if unlayered:
            # The other mod may define this key; the layered state can't say.
            return {"type": et, "id": key, "layered": False, "reason": unlayered,
                    "present": key in data,
                    "value": to_json(data[key]) if key in data else None}
        if key not in data:
            return None
        out = {"type": et, "id": key, "layered": False,
               "reason": "the other mod doesn't define it or replace its file: the server's "
                         "own value",
               "present": True, "value": to_json(data[key])}
        base = self.mod_state.base_parsers.get(et)
        if layer is not None and layer.replaced_vanilla_files and base and key in base.data:
            out["caveat"] = _REPLACED_VANILLA_CAVEAT
            out["replaced_vanilla_files"] = layer.replaced_vanilla_files
        return out


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------

class _Values:
    """Parsed values per definition file, read once per build (vanilla's are
    kept on the VanillaIndex, across builds)."""

    def __init__(self, et: str, db: str, roots: dict, vanilla, failures: list):
        self.et, self.db, self.roots, self.vanilla, self.failures = et, db, roots, vanilla, failures
        self._files: dict = {}

    def _abs(self, side: str, path: str) -> Optional[str]:
        if side == VANILLA:
            return self.vanilla.game_file(self.db, path)
        return os.path.join(self.roots[side], "common", *self.db.split("/"), *path.split("/"))

    def _ref(self, side: str, path: str) -> str:
        return f"{'game/' if side == VANILLA else ''}common/{self.db}/{path}"

    def file(self, side: str, path: str) -> Optional[dict]:
        k = (side, path)
        if k in self._files:
            return self._files[k]
        full = self._abs(side, path)
        cache = self.vanilla.parsed_files if side == VANILLA else None
        if cache is not None and full in cache:
            data, err = cache[full]
        else:
            data, err = parse_values(full, self.et) if full else (None, "no game files")
            if cache is not None:
                cache[full] = (data, err)
        if err:
            self.failures.append({"side": side, "file": self._ref(side, path), "error": err})
        self._files[k] = data
        return data


def _ref(db: str, op: Op) -> Optional[str]:
    if not op.path:
        return None
    return f"{'game/' if op.side == VANILLA else ''}common/{db}/{op.path}"


def _replay(et: str, key: str, ordered: list, bare_rule: str, value_of) -> tuple:
    """(final value or _ABSENT, trace) for one scenario's load."""
    _surviving, trace = emo.simulate(ordered, bare_rule)
    parser = parser_for(et)
    for op, step in zip(ordered, trace):
        effect = step["effect"]
        if effect in _SETS_VALUE:
            parser.data.pop(key, None)
            parser.merge_data({key: copy.deepcopy(value_of(op))})
        elif effect == "injected":
            parser.merge_data({f"INJECT:{key}": copy.deepcopy(value_of(op))})
        elif effect not in _NO_VALUE_CHANGE:
            raise ValueError(f"simulate() effect {effect!r} has no replay rule")
    return parser.data.get(key, _ABSENT), trace


def _layer_key(et, db, key, rule, o_ops, t_ops, v_arg, o_files, t_files, value_of,
               server_value, in_vanilla, server_holds_vanilla=True) -> KeyResult:
    def load_refs(trace):
        return [{"side": s["side"], "file": _ref(db, Op(s["side"], s["path"], s["line"])),
                 "line": s["line"] or None, "directive": s["directive"], "effect": s["effect"]}
                for s in trace]

    dims, loads = emo.scenario_loads(o_ops, t_ops, v_arg, rule.bare_duplicate, o_files, t_files)
    names = list(dims)
    results, values, traces = {}, {}, {}
    for combo, ordered, bare in loads:
        value, trace = _replay(et, key, ordered, bare, value_of)
        results[combo], values[combo], traces[combo] = _fingerprint(value), value, trace
    without = _outcomes(et, key, o_ops, v_arg, rule, o_files, value_of)
    # The server's own view to compare with: it keeps no vanilla for some
    # types (scripted effects, triggers), so leave vanilla out there too.
    server_view = without if server_holds_vanilla or not v_arg else _outcomes(
        et, key, o_ops, False, rule, o_files, value_of)

    first = loads[0][0]
    in_state = values[first]
    outcomes = set(results.values())
    depends_on, candidates, state_holds = [], [], None
    if len(outcomes) > 1:
        status = "undetermined"
        depends_on = emo.deciding_unknowns(dims, results)
        rows = {}
        for combo, _ordered, _bare in loads:
            sc = tuple(v for n, v in zip(names, combo) if n in depends_on)
            if sc in rows:
                continue
            value = values[combo]
            rows[sc] = {"scenario": dict(zip(depends_on, sc)),
                        "present": value is not _ABSENT,
                        "value": None if value is _ABSENT else to_json(value),
                        "load": load_refs(traces[combo])}
        candidates = list(rows.values())
        state_holds = dict(zip(depends_on, (v for n, v in zip(names, first) if n in depends_on)))
    else:
        merged = results[first]
        if merged in without:
            status = "not_created" if in_state is _ABSENT else "unchanged"
        elif in_state is _ABSENT:
            status = "removed"
        elif all(v is _ABSENT for v in without.values()):
            status = "added"
        else:
            status = "changed"
    defs = _definitions(db, [*(v_arg or []), *o_ops, *t_ops])
    return KeyResult(
        entity_type=et, db=db, key=key, status=status, in_state=in_state, server=server_value,
        server_matches_model=_fingerprint(server_value) in server_view,
        without_them=list(without.values()), definitions=defs,
        load=load_refs(traces[first]), in_vanilla=in_vanilla, depends_on=depends_on,
        candidates=candidates, state_holds=state_holds)


def _definitions(db: str, ops: list) -> list:
    """Every definition of a key, in ASCII file order."""
    return [{"side": op.side, "file": _ref(db, op), "line": op.line or None,
             "directive": op.directive}
            for op in emo.sort_ops(ops, "ascii", vanilla_first=False)]


def _outcomes(et, key, o_ops, v_arg, rule, o_files, value_of) -> dict:
    """{fingerprint: value} for the model's load of this mod alone."""
    _dims, loads = emo.scenario_loads(o_ops, [], v_arg, rule.bare_duplicate, o_files, [])
    out = {}
    for _combo, ordered, bare in loads:
        value, _trace = _replay(et, key, ordered, bare, value_of)
        out.setdefault(_fingerprint(value), value)
    return out


_REPEATED_ERROR = (
    "this file defines the key more than once (two bare copies, or a repeated directive beside "
    "another one on the key). The engine keeps the first bare copy and applies each directive "
    "in turn, but the parser keeps one body per key and file, so the layered value can't be "
    "built from it: the key keeps the server's value")


def _file_ops(side: str, db: str, key: str, defs) -> tuple[list, list]:
    """([(Op, raw key)], problems) for one side's definitions of `key`,
    `defs` being (path, line, directive) in file order. One Op per raw key
    per file. The parser folds a file's repeated INJECTs into one body, in
    order, and keeps the last of repeated REPLACEs; when the file holds no
    other definition of the key that is the engine's result too. Any other
    repeat is a problem (_REPEATED_ERROR): a bare copy the engine keeps first
    and the parser last, or directives whose order one body loses."""
    by_file: dict = {}
    for path, line, directive in defs:
        by_file.setdefault(path, []).append((line, directive))
    ops, problems = [], []
    for path, rows in by_file.items():
        counts = Counter(d for _line, d in rows)
        for d, n in counts.items():
            if n > 1 and not (len(counts) == 1 and d in _FOLDABLE):
                problems.append({"side": side, "file": _ref(db, Op(side, path, 0)),
                                 "lines": [ln for ln, dd in rows if dd == d], "directive": d,
                                 "error": _REPEATED_ERROR})
        seen = set()
        for line, d in rows:
            if d not in seen:
                seen.add(d)
                ops.append((Op(side, path, line, d), f"{d}:{key}" if d else key))
    return ops, problems


def _layer_db(ms, et: str, db: str, rule, ours_root: str, o_files: list, theirs_root: str,
              t_files: list, vanilla, failures: list, warnings: list) -> TypeLayer:
    t_scan = emo._scan_db(theirs_root, db, t_files, warnings, THEIRS)
    o_scan = emo._scan_db(ours_root, db, o_files, warnings, OURS)
    src = vanilla.source(db)
    # The server parses vanilla for these types only (mod_state.VANILLA_COMMON_DIRS).
    server_holds_vanilla = et in VANILLA_COMMON_DIRS
    server_has_vanilla = bool(ms.base_parsers.get(et) and ms.base_parsers[et].data)
    vanilla_source = src or "unavailable"
    t_cf = {p.casefold() for p in t_files}
    keys = set(t_scan.entries)
    # A file of ours or vanilla's at a path theirs ships is replaced whole.
    keys |= {k for k, lst in o_scan.entries.items() if any(p.casefold() in t_cf for p, _ in lst)}
    v_scan = vanilla.scan(db)
    replaced = []
    if v_scan is None:
        # No game files: the snapshot names vanilla's files but not their keys.
        snap = {p.casefold(): p for p in (vanilla.snapshot_files(db) or [])}
        replaced = sorted(f"game/common/{db}/{snap[p.casefold()]}" for p in t_files
                          if p.casefold() in snap)
    keys |= {k for k, lst in (v_scan or {}).items() if any(p.casefold() in t_cf for p, _ in lst)}

    values = _Values(et, db, {OURS: ours_root, THEIRS: theirs_root}, vanilla, failures)
    server_data = ms.get_data(et) or {}
    base_data = ms.base_parsers[et].data if server_has_vanilla else {}
    layer = TypeLayer(et, db, vanilla_source, rule.as_dict(), server_holds_vanilla,
                      replaced_vanilla_files=replaced)
    for key in sorted(keys):
        v = vanilla.ops(db, key)
        v_ops, v_prob = _file_ops(VANILLA, db, key, [(op.path, op.line, op.directive)
                                                     for op in v]) if v else ([], [])
        o_ops, o_prob = _file_ops(OURS, db, key, [(p, e.line, e.directive)
                                                  for p, e in o_scan.entries.get(key, [])])
        t_ops, t_prob = _file_ops(THEIRS, db, key, [(p, e.line, e.directive)
                                                    for p, e in t_scan.entries.get(key, [])])
        raw_keys = {op: raw for op, raw in (*v_ops, *o_ops, *t_ops)}

        def value_of(op, _raw=raw_keys, _key=key):
            if op.side == VANILLA and op.path is None:
                return base_data.get(_key)
            data = values.file(op.side, op.path)
            return data.get(_raw[op]) if data else None

        # A definition whose value can't be read: the key keeps the server's.
        key_failures = []
        for op in raw_keys:
            if op.side == VANILLA and op.path is None:
                ok = _key_in(base_data, key)
            else:
                data = values.file(op.side, op.path)
                ok = data is not None and raw_keys[op] in data
            if not ok:
                key_failures.append({"side": op.side, "file": _ref(db, op), "line": op.line or None,
                                     "error": "the definition's value couldn't be read"})
        server_value = server_data.get(key, _ABSENT)
        in_vanilla = None if v is None else bool(v)
        problems = [*v_prob, *o_prob, *t_prob]
        if key_failures or problems:
            layer.keys[key] = KeyResult(
                entity_type=et, db=db, key=key,
                status="parse_failed" if key_failures else "repeated_in_file",
                in_state=server_value, server=server_value, server_matches_model=None,
                without_them=[], definitions=_definitions(db, list(raw_keys)), load=[],
                in_vanilla=in_vanilla, failures=key_failures or problems)
            continue
        # Vanilla unknown (no game files, no server vanilla for this type):
        # taken as absent, as /raw shows the type.
        v_arg = [op for op, _ in v_ops] if v else False
        kr = _layer_key(
            et, db, key, rule, [op for op, _ in o_ops], [op for op, _ in t_ops], v_arg,
            o_scan.files, t_scan.files, value_of, server_value, in_vanilla, server_holds_vanilla)
        if replaced and v and any(op.path is None for op in v):
            kr.caveat = _REPLACED_VANILLA_CAVEAT
        layer.keys[key] = kr
    return layer


def _key_in(data: dict, key: str) -> bool:
    return isinstance(data, dict) and key in data


def build(ms, theirs_root: str, ours_root: str, vanilla=None) -> LayeredState:
    """Layer the mod at `theirs_root` onto `ms` (the server's ModState,
    loaded from `ours_root`). `vanilla`: an external_mod_overlap.VanillaIndex
    (default: the game files, else the snapshot). `ms` is not changed."""
    t0 = time.monotonic()
    if vanilla is None:
        vanilla = emo.VanillaIndex.default()
    elif isinstance(vanilla, dict):
        vanilla = emo.VanillaIndex(keys=vanilla)
    their_files = emo._their_files(theirs_root)
    t_common = emo._common_files(theirs_root)
    o_common = emo._common_files(ours_root, git_fallback=True)
    failures: list = []
    warnings: list = []
    not_layered: list = []
    not_layered_types: dict = {}
    types: dict = {}

    def skip(dir_: str, reason: str, et: Optional[str]) -> None:
        not_layered.append({"dir": dir_, "reason": reason})
        if et and et in ms.mod_parsers:
            not_layered_types[et] = {"dir": dir_, "reason": reason}

    for db in sorted(t_common):
        rule = emo.rule_for(db)
        et = emo.SERVER_TYPES.get(db)
        if rule.kind not in _LAYERED_KINDS:
            skip(f"common/{db}", _NOT_LAYERED_REASON[rule.kind], et)
            continue
        if et is None or et not in ms.mod_parsers:
            skip(f"common/{db}", "the server doesn't parse this folder", None)
            continue
        if not any(p.endswith(".txt") for p in t_common[db]):
            continue
        types[et] = _layer_db(ms, et, db, rule, ours_root, o_common.get(db, []), theirs_root,
                              t_common[db], vanilla, failures, warnings)
    for top, reason, et in (
        ("events/", "a duplicated event id keeps the copy read first, and which of two mods' "
                    "copies that is is unknown: see `event_id_collisions`", "Events"),
        ("localization/", "two loc files of one kind give no known winner: see `loc_collisions`",
         None),
        ("gui/", "see `path_collisions` and `gui_type_collisions`", None),
    ):
        if any(p.startswith(top) for p in their_files):
            skip(top.rstrip("/"), reason, et)

    layered = copy.copy(ms)
    layered.mod_parsers = dict(ms.mod_parsers)
    layered.parse_failures = [*ms.parse_failures, *({**f, "source": f["side"]} for f in failures)]
    layered._reverse_loc = None
    for et, layer in types.items():
        parser = parser_for(et)
        parser.data = dict(ms.mod_parsers[et].data)
        for key, kr in layer.keys.items():
            if kr.in_state is _ABSENT:
                parser.data.pop(key, None)
            else:
                parser.data[key] = kr.in_state
        layered.mod_parsers[et] = parser
    return LayeredState(mod_state=layered, path=theirs_root, mod_name=emo.read_mod_name(theirs_root),
                        types=types, not_layered=not_layered, parse_failures=failures,
                        scan_warnings=warnings, built_in_s=time.monotonic() - t0,
                        not_layered_types=not_layered_types)
