"""Keys where ModState's merge and the engine's load order disagree (#1191).

    python3 load_order_audit.py [--strict]

ModState (the parsed mod + vanilla data every tool and audit reads) merges
same-named entries its own way (`ModState.load_files_from_directory`,
`ParadoxFileParser.merge_data`): vanilla first, then the mod's files in name
order, in one pass. A bare key or a REPLACE overwrites what is there, an
INJECT merges into it, and an INJECT or REPLACE of a key nothing defined
creates it.

The engine reads something else (docs/guides/scripting_best_practices.md
§ Load Order (probed 2026-10-26)): vanilla's and the mod's files form one
name-ordered list, the first bare definition of a key wins (a script value:
the last), and the directives apply afterwards in phases. Where the two give
a key different values, `/raw`, `/laws` and every audit built on ModState
reason about a definition the game never loads.

This audit lists those keys. It holds no load-order model of its own: for
each key it takes the definitions `external_mod_overlap`'s scanner finds,
`scenario_loads()` puts them in the engine's order under each reading the
model still allows, `simulate()` says what each one does, and
`external_mod_state._replay()` applies those steps to the parsed values. The
result is compared with the value ModState holds. A change to the model's
settings (`KNOWN_*`, `BARE_DUPLICATE_RULES`) carries through.

Each key the mod defines lands in one group:

- agrees (not listed), with a count of bare copies whose bodies are
  identical (`identical`: the value is the same whichever the engine keeps);
- `difference`: every reading gives the same value and ModState holds
  another. The row names the LOAD_ORDER_MODEL entries that decide it (found
  by flipping one at a time: the bare-duplicate rule, the directive phases,
  vanilla's files read first) and their status. `--strict` fails on these;
- `model_unsure`: the value depends on something the model doesn't know (a
  folder whose bare-duplicate rule isn't recorded, where the TRY_ forms
  apply) or rests on a rule nobody read in game (the order of two plain
  REPLACEs of one key, a directive in the same file as a bare definition of
  its key). Listed apart, never as fact;
- `undetermined`: without the game files. The `vanilla_parsed/` snapshot
  stores vanilla's keys merged, with no file per key; only the manifest
  names vanilla's files. So vanilla's entry is taken as one bare definition
  and each vanilla file of the folder is tried as the one that holds it.
  When the answers differ (a mod bare copy whose file sorts between
  vanilla's files, or a vanilla file the mod replaces by path) the key is
  reported here, never as clean and never as a difference;
- `not_compared`: a file that defines the key twice (the parser keeps one
  body per key and file), or a definition whose value couldn't be read.

With the game installed (`path_constants.base_game_path`) vanilla's files
are read instead: every key then has its vanilla file, nothing is
undetermined for lack of one, vanilla keys in a file the mod replaces by
path are checked, and vanilla's own repeated keys are listed
(`vanilla_only`). The report says which mode it ran in.

Not covered: events, on_actions (their lists add up), defines, history, and
the `common/` folders ModState doesn't parse. Scripted effects, triggers,
GUIs and progress bars have no vanilla in ModState or the snapshot, so
without the game files only the mod's own definitions are compared there.
Where ModState and the model agree nothing is listed, though both may rest
on the same unprobed rule: an INJECT below its mod-only target in one file
merges in both (`mod_structure_audit` flags those).

There is no suppression comment: a difference is fixed in the script (name
the directive: `REPLACE:` to override, `INJECT:` to extend, one bare
definition per key) or by making ModState's merge follow the engine.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

import external_mod_overlap as emo
import external_mod_state as ems
from external_mod_overlap import OURS, VANILLA, Op
from mod_state import VANILLA_COMMON_DIRS

REPORT_PATH = os.path.join("docs", "engine", "load_order_report.md")

DIFFERENCE = "difference"
MODEL_UNSURE = "model_unsure"
UNDETERMINED = "undetermined"
NOT_COMPARED = "not_compared"
VANILLA_ONLY = "vanilla_only"
IDENTICAL = "identical"
KINDS = (DIFFERENCE, MODEL_UNSURE, UNDETERMINED, NOT_COMPARED, VANILLA_ONLY, IDENTICAL)

SNAPSHOT_MODE = "snapshot"
GAME_MODE = "game files"

# How sure a LOAD_ORDER_MODEL status is, weakest last. A difference resting on
# anything past `documented` is reported as model_unsure.
_STATUS_ORDER = ("probed", "documented", "unprobed", "unknown")
_SURE = frozenset({"probed", "documented"})

# The unknowns scenario_loads() simulates that are the model's own.
_MODEL_UNKNOWNS = ("file_order", "bare_duplicate", "load_reading", "or_create_phase", "try_phase")

_EFFECT_TEXT = {
    "created": "creates the entry",
    "dropped_duplicate": "dropped, the key already exists",
    "redefined": "read later, takes the key's place",
    "replaced": "replaces the entry",
    "injected": "added to the entry",
    "error_no_entry": "no entry to act on (the engine logs the non-existing-entry error)",
    "skipped_no_entry": "no entry, skipped",
}
# What the model takes as given without a read in game (the guide's "Not
# probed" list). A difference on a key of one of these shapes is model_unsure.
_UNPROBED_ORDER = ("the order of two plain REPLACEs, or two *_OR_CREATEs, of one key is taken as "
                   "file order")
_UNPROBED_SAME_FILE = ("a directive in the same file as a bare definition of its key is taken to "
                       "apply (one INJECT there was seen not to)")
_FACT_RE = re.compile(r"\bfacts? \d+(?:-\d+)?")
_FIELD_CAP = 8
# The mod's files, and vanilla's when the game is installed, as last scanned
# (external_mod_overlap._scan_file), so a reload re-scans only what changed:
# the scan is most of a run.
_SCAN_CACHE: dict = {}
# scenario_loads()'s name for an unknown -> the LOAD_ORDER_MODEL entry that records it.
_UNKNOWN_ENTRY = {"file_order": "file_order", "bare_duplicate": "bare_duplicate_other",
                  "load_reading": "directive_phases", "or_create_phase": "or_create_with_bare",
                  "try_phase": "try_phase"}


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class Guess:
    """Where vanilla's definitions of a key are taken to be."""
    vanilla: object            # scenario_loads()'s `vanilla`: a list of Ops, or False
    when: str = ""             # the guess as a clause ("" when vanilla's files are known)
    replaced: bool = False     # vanilla's copy is in a file the mod replaces by path


@dataclass
class Case:
    """One way the unknowns can fall for a key, and what the engine then reads."""
    when: str                  # the vanilla guess, as a clause ("" when nothing is guessed)
    replaced: bool
    scenario: dict             # every unknown scenario_loads() names, with this case's value
    ordered: list              # the definitions in the engine's order
    bare_rule: str
    value: object              # the engine's value, or ems._ABSENT
    fingerprint: str
    trace: list                # simulate()'s


@dataclass
class Row:
    kind: str
    entity_type: str
    db: str
    key: str
    definitions: list = field(default_factory=list)   # [{side, file, line, directive}]
    mod_state: str = ""        # what ModState holds, in words
    engine: str = ""           # what the engine reads, in words (the first case)
    load: list = field(default_factory=list)          # the first case's load, one line per step
    fields: list = field(default_factory=list)        # top-level fields that differ
    decided_by: list = field(default_factory=list)    # [{entry, status, facts}]
    depends_on: list = field(default_factory=list)    # model unknowns that change the value
    cases: list = field(default_factory=list)         # [{when, agrees, engine, load}]
    note: str = ""


@dataclass
class AuditResult:
    mode: str = SNAPSHOT_MODE
    rows: list = field(default_factory=list)
    keys_checked: int = 0      # keys replayed (a lone bare definition vanilla lacks is skipped)
    keys_defined: int = 0
    not_covered: list = field(default_factory=list)   # [(folder, reason)]
    unparsed: list = field(default_factory=list)      # mod folders ModState doesn't parse
    # Snapshot mode: vanilla files the mod replaces by path, whose keys nothing lists.
    replaced_vanilla_files: list = field(default_factory=list)
    no_vanilla: list = field(default_factory=list)    # folders checked without vanilla's keys
    scan_warnings: list = field(default_factory=list)
    parse_failures: list = field(default_factory=list)

    def of(self, kind: str) -> list:
        return [r for r in self.rows if r.kind == kind]

    def summary(self) -> dict:
        out = {"mode": self.mode, "keys_defined": self.keys_defined,
               "keys_checked": self.keys_checked,
               # The server's warning key: differences are what a reload should flag.
               "unreviewed": len(self.of(DIFFERENCE))}
        for kind in KINDS[1:]:
            out[kind] = len(self.of(kind))
        return out


# ---------------------------------------------------------------------------
# One key
# ---------------------------------------------------------------------------

def _ref(db: str, op: Op, line: bool = True) -> str:
    """A definition as the report names it."""
    if op.path is None:
        return "vanilla's entry"
    text = ems._ref(db, op)
    return f"`{text}:{op.line}`" if line and op.line else f"`{text}`"


def _steps(db: str, case: Case, line: bool = True, guessed_vanilla: bool = False) -> list:
    """The engine's load of one case, one line per definition, in the order applied."""
    out = []
    for op, step in zip(case.ordered, case.trace):
        ref = ("vanilla's entry" if guessed_vanilla and op.side == VANILLA
               else _ref(db, op, line))
        out.append(f"{ref} ({op.directive or 'bare'}): {_EFFECT_TEXT[step['effect']]}")
    return out


def _engine_text(db: str, case: Case, line: bool = True, guessed_vanilla: bool = False) -> str:
    if case.value is ems._ABSENT:
        return "no entry"
    surviving, _trace = emo.simulate(case.ordered, case.bare_rule)
    kept = [op for op in case.ordered if op in surviving]

    def ref(op):
        return "vanilla's entry" if guessed_vanilla and op.side == VANILLA else _ref(db, op, line)

    if len(kept) == 1:
        return _the(ref(kept[0]))
    return f"{ref(kept[0])} with the INJECT at " + ", ".join(ref(op) for op in kept[1:])


def _the(ref: str) -> str:
    """`the definition at <file>`, or `vanilla's entry` as it stands."""
    return f"the definition at {ref}" if ref.startswith("`") else ref


def _holder_text(db: str, fingerprint: str, ops: list, value_of) -> str:
    """What a value is, by the definitions whose own body equals it."""
    if fingerprint == ems._fingerprint(ems._ABSENT):
        return "no entry"
    same = [op for op in ops if ems._fingerprint(value_of(op)) == fingerprint]
    if same:
        rest = ", ".join(_ref(db, op) for op in same[1:])
        return _the(_ref(db, same[0])) + (f" (identical: {rest})" if rest else "")
    return "a merge of several definitions"


def _differing_fields(a, b) -> list:
    """The top-level fields two entries differ in, or [] when either isn't a block."""
    def block(v):
        return v[1] if isinstance(v, tuple) and len(v) > 1 and isinstance(v[1], dict) else None
    da, db_ = block(a), block(b)
    if da is None or db_ is None:
        return []
    return sorted(k for k in set(da) | set(db_)
                  if ems._fingerprint(da.get(k, ems._ABSENT)) != ems._fingerprint(db_.get(k, ems._ABSENT)))


def _position_text(vfile: str, op_paths: list, total: int, count: int) -> str:
    """Where a guessed vanilla file sorts among the files that define the key."""
    order = emo.file_orders()[0]

    def rank(p):
        return (emo.name_key(p, order), p)

    paths = sorted(set(op_paths), key=rank)
    before = sum(1 for p in paths if rank(p) < rank(vfile))
    if before == 0:
        where = f"that sorts before `{paths[0]}`"
    elif before == len(paths):
        where = f"that sorts after `{paths[-1]}`"
    else:
        where = f"that sorts between `{paths[before - 1]}` and `{paths[before]}`"
    return f"vanilla defines it in a file {where} ({count} of vanilla's {total} files)"


def _vanilla_guesses(vfiles: list, op_paths: list, mod_files_cf: set) -> list:
    """Snapshot mode: one Guess for each way vanilla's file can sort against
    the mod files that define the key, each standing on one vanilla file of
    that kind. A vanilla file at a path the mod ships is a guess of its own:
    the mod's file replaces it, and vanilla's definition with it."""
    orders = emo.file_orders()
    groups: dict = {}
    for vf in vfiles:
        if vf.casefold() in mod_files_cf:
            cls = ("replaced", vf)
        else:
            cls = tuple((emo.name_key(p, o), p) < (emo.name_key(vf, o), vf)
                        for o in orders for p in op_paths)
        groups.setdefault(cls, []).append(vf)
    out = []
    for cls, files in groups.items():
        replaced = bool(cls) and cls[0] == "replaced"
        if replaced:
            when = (f"vanilla defines it in `{files[0]}`, a path the mod also ships, so "
                    "vanilla's file isn't read")
        elif len(groups) == 1:
            when = "vanilla defines it"
        else:
            when = _position_text(files[0], op_paths, len(vfiles), len(files))
        out.append(Guess([Op(VANILLA, files[0], 0)], when, replaced))
    return out


def _cases(et, key, rule, o_ops, guesses, o_files, value_of) -> tuple:
    """(cases, deciding): every case for one key (each vanilla guess x each
    scenario of the model's unknowns) and the model unknowns whose value
    alone changes some case's result."""
    cases, deciding = [], set()
    for guess in guesses:
        dims, loads = emo.scenario_loads(o_ops, [], guess.vanilla, rule.bare_duplicate, o_files, [])
        names = list(dims)
        results = {}
        for combo, ordered, bare in loads:
            value, trace = ems._replay(et, key, ordered, bare, value_of)
            results[combo] = ems._fingerprint(value)
            cases.append(Case(when=guess.when, replaced=guess.replaced,
                              scenario=dict(zip(names, combo)), ordered=ordered, bare_rule=bare,
                              value=value, fingerprint=results[combo], trace=trace))
        deciding |= set(emo.deciding_unknowns(dims, results))
    return cases, [n for n in _MODEL_UNKNOWNS if n in deciding]


def _status(entry: str, db: str) -> str:
    if entry == "bare_duplicate":
        return emo.bare_rule_status(db)
    return emo.LOAD_ORDER_MODEL[entry]["status"]


def _decided_by(et, key, db, rule, case: Case, value_of) -> list:
    """The LOAD_ORDER_MODEL entries the engine's value for this key rests on,
    found by taking each one back to what ModState does and seeing whether the
    value moves: the other bare-duplicate rule; one name-ordered pass in place
    of the deferred directive phases; vanilla's files read first. An INJECT or
    REPLACE that finds no entry, and a vanilla file the mod replaces by path,
    are read off the case itself."""
    ops = list(case.ordered)
    order = case.scenario["file_order"]

    def value(ordered, bare):
        return ems._fingerprint(ems._replay(et, key, ordered, bare, value_of)[0])

    entries = []
    if case.bare_rule in (emo.FIRST_WINS, emo.LAST_WINS):
        other = emo.LAST_WINS if case.bare_rule == emo.FIRST_WINS else emo.FIRST_WINS
        if value(ops, other) != case.fingerprint:
            entries.append(rule.source)
    one_pass = emo.order_for_reading(ops, order, "interleaved")
    one_pass_value = value(one_pass, case.bare_rule)
    if one_pass_value != case.fingerprint:
        at = {id(op): i for i, op in enumerate(one_pass)}
        directives = [op for op in one_pass if op.directive]
        bare = [op for op in one_pass if op.directive is None]
        # A directive read, by name, before a bare definition it applies after.
        if directives and bare and at[id(directives[0])] < at[id(bare[-1])]:
            entries.append("directives_deferred")
        if [op for op in ops if op.directive] != directives:
            entries.append("directive_phases")
    if value(emo.order_for_reading(ops, order, "vanilla_first"), case.bare_rule) != one_pass_value:
        entries.append("interleaving")
    if any(step["effect"] == "error_no_entry" for step in case.trace):
        entries.append("directives")
    if case.replaced:
        entries.append("same_path")
    return [{"entry": e, "status": _status(e, db),
             "facts": ", ".join(_FACT_RE.findall(emo.LOAD_ORDER_MODEL[e]["see"]))}
            for e in dict.fromkeys(entries)]


def _unprobed(ops: list) -> list:
    """The unprobed rules the model's answer for these definitions rests on."""
    out = []
    plain = sum(1 for o in ops if o.directive == "REPLACE")
    creating = sum(1 for o in ops if o.directive in emo.OR_CREATE_DIRECTIVES)
    if plain > 1 or creating > 1:
        out.append(_UNPROBED_ORDER)
    bare_files = {(o.side, o.path) for o in ops if o.directive is None and o.path}
    if any(o.directive and (o.side, o.path) in bare_files for o in ops):
        out.append(_UNPROBED_SAME_FILE)
    return out


def _weakest(statuses) -> str:
    return max(statuses, key=_STATUS_ORDER.index, default="probed")


def _check_key(et, db, key, rule, o_ops, v_ops, guesses, o_files, value_of, server_value,
               *, guessed, mod_involved, no_server_vanilla) -> Optional[Row]:
    """The row for one key whose definitions all read, or None when ModState
    and the engine agree and the key's bare copies aren't identical."""
    all_ops = [*v_ops, *o_ops]
    defs = ems._definitions(db, all_ops)
    cases, deciding = _cases(et, key, rule, o_ops, guesses, o_files, value_of)
    held = ems._fingerprint(server_value)
    values = {c.fingerprint for c in cases}
    if values == {held}:
        bare = [op for op in all_ops if op.directive is None]
        if len(bare) > 1 and len({ems._fingerprint(value_of(op)) for op in bare}) == 1:
            return Row(IDENTICAL, et, db, key, definitions=defs)
        return None

    row = Row(DIFFERENCE, et, db, key, definitions=defs,
              mod_state=_holder_text(db, held, all_ops, value_of))
    if no_server_vanilla:
        row.note = ("ModState holds no vanilla for this type, so its value lacks vanilla's "
                    "definitions whatever the load order.")

    def case_rows(label):
        seen, out = set(), []
        for c in cases:
            text = label(c)
            if text not in seen:
                seen.add(text)
                out.append({"when": text, "agrees": c.fingerprint == held,
                            "engine": _engine_text(db, c, guessed_vanilla=guessed),
                            "load": _steps(db, c, guessed_vanilla=guessed)})
        return out

    if deciding:
        row.kind, row.depends_on = MODEL_UNSURE, deciding
        several = len({c.when for c in cases}) > 1
        row.cases = case_rows(lambda c: "; ".join(
            [*([c.when] if several else []), *(f"{n} is {c.scenario[n]}" for n in deciding)]))
        return row
    if held in values:
        row.kind = UNDETERMINED
        row.cases = case_rows(lambda c: c.when)
        return row

    # ModState differs in every case (and, but for a vanilla file nobody can
    # name here, from one and the same engine value).
    first = cases[0]
    row.engine = _engine_text(db, first, guessed_vanilla=guessed)
    row.load = _steps(db, first, guessed_vanilla=guessed)
    row.fields = _differing_fields(server_value, first.value)
    row.decided_by = _decided_by(et, key, db, rule, first, value_of)
    if len(values) > 1:
        row.cases = case_rows(lambda c: c.when)
    unprobed = _unprobed(all_ops)
    if unprobed:
        row.kind = MODEL_UNSURE
        row.note = " ".join(filter(None, [
            row.note, "Rests on a rule not read in game: " + "; ".join(unprobed) + "."]))
    elif _weakest(d["status"] for d in row.decided_by) not in _SURE:
        row.kind = MODEL_UNSURE
    elif not mod_involved:
        row.kind = VANILLA_ONLY
    return row


# ---------------------------------------------------------------------------
# The whole mod
# ---------------------------------------------------------------------------

def _check_db(ms, et: str, db: str, rule, mod_path: str, o_files: list, vanilla,
              result: AuditResult) -> None:
    o_scan = emo._scan_db(mod_path, db, o_files, result.scan_warnings, OURS,
                          cache=_SCAN_CACHE)
    server_holds_vanilla = et in VANILLA_COMMON_DIRS
    v_scan = vanilla.scan(db)               # None without the game files
    if vanilla.source(db) is None and not server_holds_vanilla:
        # Scripted effects, triggers, GUIs, progress bars: the snapshot holds
        # no vanilla for them, as ModState doesn't. Vanilla is left out.
        result.no_vanilla.append(f"common/{db}")
    vfiles = vanilla.snapshot_files(db) or []
    o_cf = {p.casefold() for p in o_scan.files}
    # Without the game files nothing lists the keys of a vanilla file the mod
    # replaces by path; only the ones the mod defines elsewhere get checked.
    result.replaced_vanilla_files += sorted(f"common/{db}/{vf}" for vf in vfiles
                                            if vf.casefold() in o_cf)
    values = ems._Values(et, db, {OURS: mod_path}, vanilla, result.parse_failures)
    server_data = ms.get_data(et) or {}
    base = ms.base_parsers.get(et)
    base_data = base.data if base is not None and isinstance(base.data, dict) else {}

    keys = set(o_scan.entries)
    result.keys_defined += len(keys)
    if v_scan is not None and server_holds_vanilla:
        # With the game files: vanilla keys in a file the mod replaces by
        # path, and keys vanilla's own files define more than once.
        keys |= {k for k, lst in v_scan.items()
                 if len(lst) > 1 or any(e.directive for _p, e in lst)
                 or any(p.casefold() in o_cf for p, _e in lst)}

    for key in sorted(keys):
        v = vanilla.ops(db, key)
        if v is None:
            # The index has no vanilla for this folder: go by ModState's own.
            v = [Op(VANILLA, None, 0)] if key in base_data else False
        mod_defs = [(p, e.line, e.directive) for p, e in o_scan.entries.get(key, [])]
        if v is False and len(mod_defs) == 1 and mod_defs[0][2] is None:
            continue            # one bare definition, nothing to merge with
        result.keys_checked += 1
        v_ops, v_prob = ems._file_ops(VANILLA, db, key, [(op.path, op.line, op.directive)
                                                         for op in v]) if v else ([], [])
        o_ops, o_prob = ems._file_ops(OURS, db, key, mod_defs)
        raw_keys = dict((*v_ops, *o_ops))
        # The snapshot's vanilla: one merged entry, its file unknown.
        merged_vanilla = any(op.side == VANILLA and op.path is None for op in raw_keys)

        def value_of(op, _raw=raw_keys, _key=key):
            if op.side == VANILLA and (op.path is None or op not in _raw):
                return base_data.get(_key)
            data = values.file(op.side, op.path)
            return data.get(_raw[op]) if data else None

        unread = []
        for op in raw_keys:
            if op.side == VANILLA and op.path is None:
                ok = key in base_data
            else:
                data = values.file(op.side, op.path)
                ok = data is not None and raw_keys[op] in data
            if not ok:
                unread.append(f"{_ref(db, op)}: the definition's value couldn't be read")
        repeats = [f"`{p['file']}` defines it {len(p['lines'])} times "
                   f"({p['directive'] or 'bare'}, lines {', '.join(map(str, p['lines']))})"
                   for p in (*v_prob, *o_prob)]
        if unread or repeats:
            note = "; ".join(unread or repeats)
            if not unread:
                note += (". The engine keeps a file's first bare copy and applies each directive "
                         "in turn; the parser keeps one body per key and file, so the values "
                         "can't be replayed")
            result.rows.append(Row(NOT_COMPARED, et, db, key,
                                   definitions=ems._definitions(db, list(raw_keys)), note=note))
            continue

        mod_ops = [op for op, _ in o_ops]
        vanilla_ops = [op for op, _ in v_ops]
        replaced = any(op.path and op.path.casefold() in o_cf for op in vanilla_ops)
        if not v:
            guesses = [Guess(False)]
        elif merged_vanilla and vfiles:
            guesses = _vanilla_guesses(vfiles, [op.path for op in mod_ops], o_cf)
        else:
            # The game files' own definitions; or a merged entry with no file
            # list to guess from, which sort_ops() reads first.
            guesses = [Guess(vanilla_ops, replaced=replaced)]
        row = _check_key(
            et, db, key, rule, mod_ops, vanilla_ops, guesses, o_scan.files, value_of,
            server_data.get(key, ems._ABSENT), guessed=merged_vanilla,
            mod_involved=bool(mod_ops) or replaced,
            no_server_vanilla=bool(v) and not server_holds_vanilla)
        if row is not None:
            result.rows.append(row)


def default_vanilla(mod_path: str) -> emo.VanillaIndex:
    """Vanilla for a command-line run, whose ModState comes from `mod_path`'s
    snapshot (load_state): the game files when installed and the snapshot
    matches them, else the snapshot alone."""
    snap = os.path.join(mod_path, "vanilla_parsed")
    game = None
    try:
        import path_constants
        import vanilla_parsed
        root = path_constants.base_game_path
        if (os.path.isdir(os.path.join(root, "game", "common"))
                and vanilla_parsed.check(snap, root).fresh):
            game = os.path.join(root, "game", "common")
    except Exception:  # noqa: BLE001 - no install configured
        game = None
    return emo.VanillaIndex(game_common=game, snapshot_dir=snap, scan_cache=_SCAN_CACHE)


def _server_vanilla() -> Optional[emo.VanillaIndex]:
    """Vanilla as the running server's ModState has it, or None outside a
    server (which runs as `__main__`). Its `_overlap_vanilla_index()` picks
    the game files when the server's vanilla matches them and the snapshot
    otherwise; the index returned here reads the same source, through this
    module's scan cache, so a reload doesn't scan vanilla's files again."""
    fn = getattr(sys.modules.get("__main__"), "_overlap_vanilla_index", None)
    try:
        index = fn() if callable(fn) else None
    except Exception:  # noqa: BLE001 - fall back to default_vanilla
        return None
    if index is None:
        return None
    return emo.VanillaIndex(game_common=index.game_common, snapshot_dir=index.snapshot_dir,
                            scan_cache=_SCAN_CACHE)


def load_state(mod_path: str, snapshot_dir: Optional[str] = None):
    """The ModState a server on this checkout would serve without the game:
    vanilla from the `vanilla_parsed/` snapshot, the mod from `mod_path`."""
    import vanilla_parsed
    from mod_state import ModState, entity_paths

    base, mod = entity_paths(os.path.join(mod_path, "_no_game_"), mod_path)
    snap = vanilla_parsed.load(snapshot_dir or os.path.join(mod_path, "vanilla_parsed"))
    return ModState(base, mod, vanilla_data=snap.data)


_NOT_COVERED_REASON = {
    "defines": "per-key values, not entries",
    "on_actions": "an on_action's event lists add up across files, and ModState keeps one file's",
    "additive": "history blocks are effects that all run; ModState doesn't parse them",
    "wrapper": "entries sit inside a wrapper block every file repeats; ModState doesn't parse it",
}


def audit(mod_state=None, mod_path: Optional[str] = None,
          vanilla: Optional[emo.VanillaIndex] = None) -> AuditResult:
    """Compare every key the mod defines in a folder ModState parses.
    `mod_state` defaults to one built from the snapshot (load_state), and
    `vanilla` to default_vanilla(): pass the two together, so that the
    vanilla the engine side reads is the vanilla ModState was loaded from."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    if vanilla is None:
        vanilla = default_vanilla(mod_path)
    if mod_state is None:
        mod_state = load_state(mod_path)
    result = AuditResult(mode=GAME_MODE if vanilla.game_common else SNAPSHOT_MODE)
    o_common = emo._common_files(mod_path, git_fallback=True)
    dbs = set(o_common)
    if vanilla.game_common:
        dbs |= {db for et, db in VANILLA_COMMON_DIRS.items() if et in mod_state.mod_parsers}
    unparsed, not_covered = [], {}
    for db in sorted(dbs):
        rule = emo.rule_for(db)
        et = emo.SERVER_TYPES.get(db)
        if rule.kind not in ems._LAYERED_KINDS:
            folder = "history" if rule.kind == "additive" else db
            not_covered[f"common/{folder}"] = _NOT_COVERED_REASON[rule.kind]
        elif et is None or et not in mod_state.mod_parsers:
            if any(p.endswith(".txt") for p in o_common.get(db, [])):
                unparsed.append(f"common/{db}")
        else:
            _check_db(mod_state, et, db, rule, mod_path, o_common.get(db, []), vanilla, result)
    result.not_covered = sorted(not_covered.items())
    result.unparsed = unparsed
    result.rows.sort(key=lambda r: (KINDS.index(r.kind), r.db, r.key))
    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _defs_text(row: Row, line: bool = True) -> str:
    out = []
    for d in row.definitions:
        if not d["file"]:
            out.append("vanilla (its file isn't in the snapshot)")
            continue
        ref = f"{d['file']}:{d['line']}" if line and d["line"] else d["file"]
        out.append(f"`{ref}` ({d['directive'] or 'bare'})")
    return "; ".join(out)


def _decided_text(row: Row) -> str:
    if not row.decided_by:
        return ("not identified: no single LOAD_ORDER_MODEL entry moves the value. ModState may "
                "not have read one of these files (it skips names that start with `_`)")
    return "; ".join(f"`{d['entry']}` ({d['status']}{', ' + d['facts'] if d['facts'] else ''})"
                     for d in row.decided_by)


def _row_lines(row: Row) -> list:
    out = [f"### `common/{row.db}` `{row.key}`", "",
           f"- Definitions: {_defs_text(row)}",
           f"- ModState holds: {row.mod_state}"]
    if row.engine:
        out.append(f"- The engine reads: {row.engine}")
        out += [f"  - {step}" for step in row.load]
    if row.fields:
        shown = ", ".join(f"`{f}`" for f in row.fields[:_FIELD_CAP])
        more = len(row.fields) - _FIELD_CAP
        out.append(f"- Fields that differ: {shown}" + (f" and {more} more" if more > 0 else ""))
    if row.depends_on:
        out.append("- Depends on: " + ", ".join(
            f"`{n}` (LOAD_ORDER_MODEL entry `{_UNKNOWN_ENTRY[n]}`)" for n in row.depends_on))
    else:
        out.append(f"- Decided by: {_decided_text(row)}")
    for case in row.cases:
        verdict = "agrees with ModState" if case["agrees"] else "differs"
        out.append(f"- If {case['when']}: the engine reads {case['engine']} ({verdict})")
        out += [f"  - {step}" for step in case["load"]]
    if row.note:
        out.append(f"- Note: {row.note}")
    out.append("")
    return out


def _strip_lines(step: str) -> str:
    return re.sub(r"(\.txt):\d+`", r"\1`", step)


def _undetermined_lines(rows: list) -> list:
    """Keys grouped by what they wait on: one block per folder, set of
    definitions and set of cases, without line numbers (an edit above a key
    would otherwise churn the report)."""
    groups: dict = {}
    for row in rows:
        merged: dict = {}       # cases with one result read as one
        for c in row.cases:
            merged.setdefault((c["agrees"], tuple(_strip_lines(s) for s in c["load"])),
                              []).append(c["when"])
        cases = tuple((tuple(whens), agrees, load) for (agrees, load), whens in merged.items())
        groups.setdefault((row.db, _defs_text(row, line=False), cases), []).append(row.key)
    out = []
    for (db, defs, cases), keys in sorted(groups.items(), key=lambda g: (g[0][0], sorted(g[1])[0])):
        out += [f"### `common/{db}`: {len(keys)} key{'s' if len(keys) != 1 else ''}", "",
                f"- Definitions: {defs}"]
        for whens, agrees, load in cases:
            verdict = "agrees with ModState" if agrees else "**differs**"
            steps = "; ".join(load) if load else "nothing defines the key"
            out.append(f"- If {', or '.join(whens)}: {verdict}. The engine's load: {steps}.")
        out += ["- Keys: " + ", ".join(f"`{k}`" for k in sorted(keys)), ""]
    return out


def _section(out: list, title: str, intro: list, rows: list, render=None) -> None:
    out += [f"## {title}", "", *intro, *([""] if intro else [])]
    if not rows:
        out += ["_None._", ""]
        return
    if render is not None:
        out += render(rows)
        return
    for row in rows:
        out += _row_lines(row)


def render_report(result: AuditResult) -> str:
    game = result.mode == GAME_MODE
    out = [
        "# Load order audit report",
        "",
        "Auto-generated by `load_order_audit.py` on every `POST /reload` of the mod",
        "state server. Do not hand-edit.",
        "",
        "Keys where the value ModState holds differs from what the engine loads, as",
        "`external_mod_overlap.simulate()` replays the probed load order",
        f"({emo.LOAD_ORDER_DOC}).",
        "ModState reads vanilla first and then the mod's files in one pass, a later",
        "bare key overwriting an earlier one. The engine reads vanilla's and the",
        "mod's files as one name-ordered list, keeps the first bare definition of a",
        "key (the last, for a script value) and applies the directives afterwards",
        "in phases. Every tool built on ModState sees ModState's value (#1191).",
        "",
        f"**Mode: {result.mode}.** " + (
            "Vanilla's definitions were read from the installed game, each with its file."
            if game else
            "No game install: vanilla's keys come from the `vanilla_parsed/` snapshot, which "
            "records no file per key, and vanilla's file names from its manifest. A key whose "
            "answer turns on which vanilla file defines it is under *Undetermined without the "
            "game files*; a reload on a machine with the game decides those."),
        "",
        "| Group | Keys |",
        "|---|---|",
        f"| Differences (ModState holds a value the engine doesn't load) | {len(result.of(DIFFERENCE))} |",
        f"| Model unsure | {len(result.of(MODEL_UNSURE))} |",
        f"| Undetermined without the game files | {len(result.of(UNDETERMINED))} |",
        f"| Not compared | {len(result.of(NOT_COMPARED))} |",
        "| Vanilla's own files | "
        f"{len(result.of(VANILLA_ONLY)) if game else 'not checked'} |",
        f"| Identical bare copies (no difference) | {len(result.of(IDENTICAL))} |",
        "",
        "The LOAD_ORDER_MODEL entries (`external_mod_overlap.py`) a row cites, with",
        "their status:",
        "",
        "| Entry | Status | Where |",
        "|---|---|---|",
    ]
    for entry in ("interleaving", "bare_duplicate", "bare_duplicate_script_values",
                  "bare_duplicate_other", "directives", "directives_deferred", "directive_phases",
                  "or_create_with_bare", "try_phase", "same_path"):
        m = emo.LOAD_ORDER_MODEL[entry]
        status = m["status"]
        if entry == "bare_duplicate":
            status = ("probed in " + ", ".join(f"`{d}`" for d in sorted(emo.BARE_DUPLICATE_PROBED))
                      + "; documented in the other folders")
        out.append(f"| `{entry}` | {status} | {m['see']} |")
    out.append("")
    _section(out, "Differences", [
        "Every reading the model allows gives the same value, and ModState holds",
        "another. In game the engine's value is the one that applies. Fix the",
        "script (one bare definition per key; `REPLACE:` to override, `INJECT:` to",
        "extend) or make ModState's merge follow the engine. `--strict` fails on",
        "these.",
    ], result.of(DIFFERENCE))
    _section(out, "Model unsure", [
        "The value depends on something the load-order model doesn't know, or rests",
        "on a rule nobody has read in game. Not a finding until a probe settles it.",
    ], result.of(MODEL_UNSURE))
    _section(out, "Undetermined without the game files", [
        "ModState agrees with the engine if vanilla defines the key in one file and",
        "differs if it is in another, and the snapshot doesn't say which. Neither",
        "clean nor a finding.",
    ], result.of(UNDETERMINED), _undetermined_lines)
    _section(out, "Not compared", [], result.of(NOT_COMPARED), lambda rows: [
        *(f"- `common/{r.db}` `{r.key}`: {r.note}." for r in rows), ""])
    if game:
        _section(out, "Vanilla's own files", [
            "Keys the mod doesn't define that vanilla's files define more than once,",
            "where ModState's vanilla value differs from the engine's.",
        ], result.of(VANILLA_ONLY))
    else:
        out += ["## Vanilla's own files", "", "_Not checked: needs the game files._", ""]

    def same_lines(rows):
        by_db: dict = {}
        for r in rows:
            by_db.setdefault(r.db, []).append(r.key)
        return [*(f"- `common/{db}` ({len(keys)}): " + ", ".join(f"`{k}`" for k in sorted(keys))
                  for db, keys in sorted(by_db.items())), ""]

    _section(out, "Identical bare copies", [
        "Keys with more than one bare definition whose bodies are identical: the",
        "value is the same whichever copy the engine keeps. Where the mod's copy",
        "restates vanilla's, it is dead script in a first-wins folder.",
    ], result.of(IDENTICAL), same_lines)
    out += ["## Not covered", ""]
    if result.no_vanilla:
        out.append("- Checked among the mod's own files only, since neither ModState nor the "
                   "snapshot holds vanilla's keys there (with the game files a mod copy of a "
                   "vanilla key is checked too): "
                   + ", ".join(f"`{d}`" for d in sorted(result.no_vanilla)) + ".")
    if result.replaced_vanilla_files:
        out.append("- Vanilla keys in a file the mod replaces by path ("
                   + ", ".join(f"`{f}`" for f in result.replaced_vanilla_files)
                   + "): one the mod's file leaves out is gone in game while ModState keeps it. "
                   "The snapshot can't list a vanilla file's keys, so only those the mod defines "
                   "are checked; with the game files all of them are.")
    out.append("- `events/`: a duplicated event id keeps the copy read first, in an order of its "
               "own (fact 6).")
    for folder, reason in result.not_covered:
        out.append(f"- `{folder}`: {reason}.")
    if result.unparsed:
        out.append("- Folders ModState doesn't parse: "
                   + ", ".join(f"`{d}`" for d in result.unparsed) + ".")
    out.append("")
    if result.scan_warnings or result.parse_failures:
        out += ["## Files that didn't read cleanly", ""]
        for w in result.scan_warnings:
            out.append(f"- `{w['file']}`: {w['warning']}")
        for f in result.parse_failures:
            out.append(f"- `{f['file']}`: {f['error']}")
        out.append("")
    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path,
                   vanilla=_server_vanilla() if mod_state is not None else None)
    out_path = os.path.join(mod_path, REPORT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_report(result))
    return result.summary()


def main(argv=None, mod_path: Optional[str] = None) -> int:
    """Print the report. With `--strict` (CI), exit 1 on any difference."""
    argv = sys.argv[1:] if argv is None else argv
    result = audit(mod_path=mod_path)
    print(render_report(result))
    if "--strict" in argv:
        return 1 if result.of(DIFFERENCE) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
