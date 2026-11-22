#!/usr/bin/env python3
"""Regenerate `localization_accessor_vanilla_extras.py` from vanilla's loc.

The engine reads vanilla's loc, so an `accessor 'X' is not valid on type 'T'`
flag the localization accessor audit raises against it is a gap in the audit's
catalog. This tool sorts each gap into one of two kinds:

* **Terminal**: no vanilla chain goes on past the accessor. It is a name or a
  number, and it is folded into the extras as `"value"`.
* **Chained further**: some vanilla chain has another step after it, so it
  returns an object. It is NOT folded. Folding it as `"value"` would clear the
  flag by switching the check off for the rest of every chain through it (#348:
  153 accessors went in that way). Give it its real return type by hand in
  `_BUILTIN_ACCESSORS_BY_TYPE` in `localization_accessor_audit.py`, then run
  this again: the accessors behind it surface once it is typed.

Vanilla's loc comes from the game install (`game/localization/english/`), or
from the committed `vanilla_parsed/` snapshot when there is none; the output
says which. A flag listed in the audit's `KNOWN_VANILLA_FLAGS` is vanilla's own
mistake and is left alone. With the engine's data types at hand (the
Modding-Digests checkout's `docs/data_types_*.txt`, found through
`path_constants`, or `--data-types DIR`), each new accessor is printed with
what the engine says it returns.

Besides folding, a run drops every extras entry the hand table now defines
(the hand-typed pair wins anyway) and every `--drop TYPE.ACCESSOR`, then lists
the folded accessors that vanilla chains further through all the same.
`--prune` also drops every entry no chain in vanilla's loc calls: the fold
only ever adds, so an accessor an older vanilla used stays after vanilla stops
using it, and nothing then backs its typing. The report lists each pruned
entry the mod's own loc still calls, which the audit flags from then on.

Re-run after every vanilla patch (runbook § 4). `--dry-run` reports and writes
nothing. Exit code 1 when a chained-further accessor is waiting for its type,
or a folded one that vanilla chains through is neither typed nor explained in
the audit's `BLIND_UNDETERMINED`. A chained-further gap that table explains is
folded as `"value"` and listed, so a fold from an empty extras file settles.

Usage: python3 scripts/generators/fold_vanilla_loc_accessors.py [--dry-run]
           [--source auto|install|snapshot] [--data-types DIR]
           [--drop TYPE.ACCESSOR ...] [--prune]
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import localization_accessor_audit as audit_mod  # noqa: E402
import path_constants  # noqa: E402

EXTRAS = REPO / "localization_accessor_vanilla_extras.py"
ENGINE_DOCS = REPO / "docs" / "engine"
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")

HEADER = '''\
# Auto-extracted from vanilla loc. Do not hand-edit; regenerate via
# scripts/generators/fold_vanilla_loc_accessors.py.
# Every accessor here returns "value": a name or a number that no vanilla chain
# goes on past. An accessor vanilla chains further through returns an object and
# is typed by hand in _BUILTIN_ACCESSORS_BY_TYPE in localization_accessor_audit.py;
# the generator reports those and leaves them out.

'''

# The audit's types that are not the snake-cased name of one engine data type.
# `country` also stands for a script scope (ROOT, THIS, a journal entry's
# target), and three of the audit's types cover several engine ones.
ENGINE_TYPES: dict[str, tuple[str, ...]] = {
    "scope_object": ("TopScope", "Scope"),
    "country": ("Country", "Scope"),
    "law": ("Law", "LawType"),
    "market_goods": ("Goods", "MarketGoods", "StateGoods"),
    "treaty_article": ("Article",),
    "regional_objective": ("AIRegionalObjective",),
    "strategic_region": ("StrategicRegion", "GeographicRegion"),
    "meta_player": ("Player",),
}


# ---------------------------------------------------------------------------
# Vanilla's loc
# ---------------------------------------------------------------------------

def load_vanilla_lines(source: str = "auto") -> tuple[list, str]:
    """`(vanilla's loc lines, where they came from)`. `auto` reads the game
    install when there is one and the committed snapshot otherwise."""
    loc_dir = None
    if source in ("auto", "install"):
        try:
            loc_dir = os.path.join(path_constants.base_game_path, "game", "localization", "english")
        except RuntimeError:
            loc_dir = None
        if loc_dir and os.path.isdir(loc_dir):
            # Every file the engine reads, subfolders included (english/frontend/,
            # english/map/, ...), as the snapshot holds them: the audit's own
            # reader takes one folder and would miss some 2,400 keys.
            from mod_state import iter_loc_files
            lines = []
            for path in iter_loc_files(loc_dir):
                rel = os.path.relpath(path, loc_dir).replace(os.sep, "/")
                lines += [audit_mod.LocLine(rel, ll.line, ll.key, ll.value, ll.comment)
                          for ll in audit_mod.read_loc_file(path)]
            return lines, f"the game install ({loc_dir})"
        if source == "install":
            raise SystemExit(f"no vanilla loc at {loc_dir or 'base_game_path (not configured)'}")
    snapshot = audit_mod.load_vanilla_snapshot_loc()
    if snapshot is None:
        raise SystemExit("no game install and no vanilla_parsed/ snapshot to read vanilla's loc from")
    loc, version = snapshot
    return audit_mod.lines_from_dict(loc), f"the vanilla_parsed/ snapshot ({version}; no game install)"


# ---------------------------------------------------------------------------
# The engine's data types (optional)
# ---------------------------------------------------------------------------

def load_data_types(docs_dir: str | None) -> dict[str, dict[str, list[tuple[str, str]]]] | None:
    """`{engine type: {accessor: [(definition kind, return type)]}}` from the
    engine's `data_types_*.txt` dump under `docs_dir`; None when there is none."""
    if not docs_dir:
        return None
    paths = sorted(glob.glob(os.path.join(docs_dir, "data_types_*.txt")))
    if not paths:
        return None
    types: dict[str, dict[str, list[tuple[str, str]]]] = {}
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        for block in text.split("-----------------------"):
            lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
            if not lines or "." not in lines[0].split("(")[0]:
                continue
            typ, accessor = lines[0].split("(")[0].strip().split(".", 1)
            kind = ret = ""
            for line in lines[1:]:
                if line.startswith("Definition type:"):
                    kind = line.split(":", 1)[1].strip()
                elif line.startswith("Return type:"):
                    ret = line.split(":", 1)[1].strip()
            types.setdefault(typ, {}).setdefault(accessor, []).append((kind, ret))
    return types


def default_data_types_dir() -> str | None:
    for name in ("vanilla_snapshot_docs_path", "vanilla_snapshot_docs_path_default"):
        try:
            path = getattr(path_constants, name)
        except (RuntimeError, AttributeError):
            path = None
        if path and glob.glob(os.path.join(path, "data_types_*.txt")):
            return path
    return None


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def engine_says(data_types: dict | None, typ: str, accessor: str) -> str:
    """What the data types say `typ.accessor` returns, for the report: a promote
    returns an object, a function a name or a number."""
    if data_types is None:
        return ""
    engine_types = ENGINE_TYPES.get(typ) or tuple(
        name for name in data_types if _normalize(name) == _normalize(typ))
    found = []
    for engine_type in engine_types:
        entries = data_types.get(engine_type, {}).get(accessor, [])
        promote = [ret for kind, ret in entries if kind == "Promote"]
        if promote:
            found.append(f"{engine_type}.{accessor} is a promote to {promote[0]}")
        elif entries:
            returns = [ret for _, ret in entries if ret and ret != "[unregistered]"]
            found.append(f"{engine_type}.{accessor} is a function"
                         + (f" returning {returns[0]}" if returns else ""))
    if found:
        return "data types: " + "; ".join(found)
    tried = ", ".join(engine_types) or f"no engine type matches `{typ}`"
    return f"data types: no such accessor ({tried}), so vanilla's text may be dead"


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------

@dataclass
class Gap:
    """An accessor vanilla calls on a type that the catalog doesn't list."""
    type: str
    accessor: str
    key: str            # a loc key that calls it
    chain: str
    continuations: list[str] = field(default_factory=list)  # step names seen after it

    @property
    def name(self) -> str:
        return f"{self.type}.{self.accessor}"


@dataclass
class FoldPlan:
    extras: dict[str, dict[str, str]]          # the table to write
    terminal: list[Gap] = field(default_factory=list)   # folded as "value"
    chained: list[Gap] = field(default_factory=list)    # to be typed by hand
    # chained further, but BLIND_UNDETERMINED says nothing tells what it returns:
    # folded as "value" all the same, so a fold from empty extras still settles
    undetermined: list[Gap] = field(default_factory=list)
    shadowed: list[str] = field(default_factory=list)   # dropped: the hand table has them
    dropped: list[str] = field(default_factory=list)    # dropped by --drop
    pruned: list[str] = field(default_factory=list)     # dropped by --prune: vanilla never calls them
    known: int = 0                                      # flags in KNOWN_VANILLA_FLAGS
    residual: list = field(default_factory=list)        # flags that name no accessor
    blind: list = field(default_factory=list)           # folded pairs vanilla chains past
    flags: int = 0                                      # vanilla flags before the fold
    explained: dict = field(default_factory=dict)       # the BLIND_UNDETERMINED in use

    @property
    def untyped_blind(self) -> list:
        return [p for p in self.blind if (p.type, p.accessor) not in self.explained]

    @property
    def changed(self) -> bool:
        return bool(self.terminal or self.undetermined or self.shadowed or self.dropped
                    or self.pruned)

    @property
    def needs_hand_typing(self) -> bool:
        return bool(self.chained or self.untyped_blind)


def plan_fold(
    lines: list,
    hand: dict[str, dict[str, str]],
    extras: dict[str, dict[str, str]],
    *,
    engine_docs_dir: str = "",
    known_flags: dict | None = None,
    undetermined: dict | None = None,
    drop: tuple[str, ...] = (),
    prune: bool = False,
) -> FoldPlan:
    """What a fold of vanilla's `lines` would do to `extras`, given the
    hand-typed table `hand`. Writes nothing. `known_flags` and `undetermined`
    default to the audit's `KNOWN_VANILLA_FLAGS` and `BLIND_UNDETERMINED`; a
    chained-further gap the latter explains is folded as `"value"`, since
    nothing says what else to type it. `prune` drops every extras entry no
    chain in `lines` calls (see called_pairs)."""
    known_flags = audit_mod.KNOWN_VANILLA_FLAGS if known_flags is None else known_flags
    if undetermined is None:
        undetermined = audit_mod.BLIND_UNDETERMINED
    plan = FoldPlan(extras={}, explained=undetermined)
    for typ, accessors in extras.items():
        for accessor, ret in accessors.items():
            name = f"{typ}.{accessor}"
            if accessor in hand.get(typ, {}):
                plan.shadowed.append(name)
            elif name in drop:
                plan.dropped.append(name)
            else:
                plan.extras.setdefault(typ, {})[accessor] = ret
    unknown = sorted(set(drop) - set(plan.dropped))
    if unknown:
        raise SystemExit(f"--drop: not in the extras (or already hand-typed): {', '.join(unknown)}")

    catalog = audit_mod._load_engine_catalog(
        engine_docs_dir, audit_mod.merge_folded(hand, plan.extras))
    result = audit_mod.audit_lines(lines, catalog)
    gaps: dict[tuple[str, str], Gap] = {}
    is_chained: set[tuple[str, str]] = set()
    for flag in result.flags:
        if flag.exemption:
            continue
        plan.flags += 1
        if (flag.key, flag.chain) in known_flags:
            plan.known += 1
            continue
        chain = audit_mod.extract_chains(f"[{flag.chain}]")[0]
        bad = next((s for s in audit_mod.walk_chain(chain, flag.context, catalog)
                    if s.returns is None), None)
        if bad is None or not _IDENT_RE.fullmatch(bad.name):
            # A denied scope, a typo that glues two steps together: no accessor
            # to add. It stays a flag until someone lists it as known.
            plan.residual.append(flag)
            continue
        pair = (bad.receiver, bad.name)
        gap = gaps.setdefault(pair, Gap(bad.receiver, bad.name, flag.key, flag.chain))
        if not bad.last:
            is_chained.add(pair)
            nxt = audit_mod._step_name(chain.steps[bad.index + 1])
            if nxt not in gap.continuations:
                gap.continuations.append(nxt)
    for pair, gap in sorted(gaps.items()):
        if pair in is_chained and pair in undetermined:
            plan.undetermined.append(gap)
            plan.extras.setdefault(gap.type, {})[gap.accessor] = "value"
        elif pair in is_chained:
            plan.chained.append(gap)
        else:
            plan.terminal.append(gap)
            plan.extras.setdefault(gap.type, {})[gap.accessor] = "value"

    catalog = audit_mod._load_engine_catalog(
        engine_docs_dir, audit_mod.merge_folded(hand, plan.extras))
    if prune:
        called = called_pairs(lines, catalog)
        for typ in sorted(plan.extras):
            for accessor in sorted(plan.extras[typ]):
                if (typ, accessor) not in called:
                    plan.pruned.append(f"{typ}.{accessor}")
                    del plan.extras[typ][accessor]
        plan.extras = {typ: accs for typ, accs in plan.extras.items() if accs}
        catalog = audit_mod._load_engine_catalog(
            engine_docs_dir, audit_mod.merge_folded(hand, plan.extras))
    plan.blind = [p for p in audit_mod.find_blind_pairs(lines, catalog, hand_typed=hand)
                  if not p.hand_typed]
    return plan


def called_pairs(lines: list, catalog: dict[str, dict[str, str]]) -> set[tuple[str, str]]:
    """Every `(type, accessor)` some chain in `lines` calls, as far as
    `catalog` lets the audit follow the chain. Every extras entry is `value`,
    so the walk stops at one: dropping an entry never hides another."""
    called: set[tuple[str, str]] = set()
    for ll in lines:
        if "[" not in ll.value:
            continue
        ctx = audit_mod.classify_context(ll.key)
        for chain in audit_mod.extract_chains(ll.value):
            for step in audit_mod.walk_chain(chain, ctx, catalog):
                called.add((step.receiver, step.name))
    return called


def mod_calls(pruned: list[str], mod_loc_dir: str | None = None) -> dict[str, str]:
    """`{"type.accessor": an example loc key}` for each pruned entry the mod's
    own English loc still calls: the audit flags those once they are pruned.
    Empty when there is no mod loc to read."""
    if not pruned:
        return {}
    loc_dir = mod_loc_dir or str(REPO / "localization" / "english")
    if not os.path.isdir(loc_dir):
        return {}
    wanted = {tuple(name.split(".", 1)) for name in pruned}
    catalog = audit_mod._load_engine_catalog(str(ENGINE_DOCS), audit_mod._BUILTIN_ACCESSORS_BY_TYPE)
    found: dict[str, str] = {}
    for ll in audit_mod.read_all_loc(loc_dir):
        if "[" not in ll.value:
            continue
        ctx = audit_mod.classify_context(ll.key)
        for chain in audit_mod.extract_chains(ll.value):
            for step in audit_mod.walk_chain(chain, ctx, catalog):
                if (step.receiver, step.name) in wanted:
                    found.setdefault(f"{step.receiver}.{step.name}", ll.key)
    return dict(sorted(found.items()))


def render_extras(extras: dict[str, dict[str, str]]) -> str:
    lines = [HEADER + "VANILLA_EXTRACTED_ACCESSORS = {"]
    for typ in sorted(extras):
        if not extras[typ]:
            continue
        lines.append(f'    "{typ}": {{')
        lines += [f'        "{acc}": "{ret}",' for acc, ret in sorted(extras[typ].items())]
        lines.append("    },")
    lines.append("}\n")
    return "\n".join(lines)


def render_plan(plan: FoldPlan, source: str, data_types: dict | None, *, dry_run: bool,
                mod_uses: dict[str, str] | None = None) -> str:
    out = [f"vanilla loc: {source}"]
    out.append("data types: " + ("read" if data_types is not None else
                                 "none found (set vic3_modding_digests_path or pass --data-types "
                                 "to see what the engine says each accessor returns)"))
    out.append(f"vanilla flags: {plan.flags} ({plan.known} known vanilla mistakes, "
               f"{len(plan.residual)} unexplained)")
    verb = "would fold" if dry_run else "folded"
    out.append("")
    out.append(f"Terminal, {verb} as \"value\": {len(plan.terminal)}")
    for gap in plan.terminal:
        says = engine_says(data_types, gap.type, gap.accessor)
        out.append(f"  + {gap.name}" + (f"   [{says}]" if says else ""))
    out.append("")
    out.append(f"Chained further in vanilla, NOT folded: {len(plan.chained)}"
               + (" (type these by hand in _BUILTIN_ACCESSORS_BY_TYPE, then run again)"
                  if plan.chained else ""))
    for gap in plan.chained:
        says = engine_says(data_types, gap.type, gap.accessor)
        out.append(f"  ! {gap.name}, then {', '.join(gap.continuations)}"
                   f"   e.g. {gap.key}: [{gap.chain}]" + (f"   [{says}]" if says else ""))
    if plan.undetermined:
        out.append("")
        out.append(f"Chained further, {verb} as \"value\" because BLIND_UNDETERMINED "
                   f"explains them: {len(plan.undetermined)}")
        for gap in plan.undetermined:
            out.append(f"  ~ {gap.name}, then {', '.join(gap.continuations)}")
    if plan.shadowed or plan.dropped or plan.pruned:
        out.append("")
        out.append(f"Dropped from the extras: {len(plan.shadowed)} the hand table defines, "
                   f"{len(plan.dropped)} by --drop, {len(plan.pruned)} by --prune "
                   "(vanilla's loc never calls them)")
        for name in plan.shadowed + plan.dropped + plan.pruned:
            out.append(f"  - {name}")
    if mod_uses:
        out.append("")
        out.append(f"Pruned, but the mod's loc still calls them (the audit flags these now): "
                   f"{len(mod_uses)}")
        for name, key in mod_uses.items():
            out.append(f"  ! {name}   e.g. {key}")
    if plan.residual:
        out.append("")
        out.append("Flags that name no accessor to add (a vanilla typo belongs in "
                   "KNOWN_VANILLA_FLAGS):")
        for flag in plan.residual:
            out.append(f"  {flag.key} | {flag.chain} | {flag.reason}")
    out.append("")
    out.append(f"Folded accessors vanilla chains further through: {len(plan.blind)} "
               f"({len(plan.untyped_blind)} to be typed, the rest explained in BLIND_UNDETERMINED)")
    for pair in plan.blind:
        why = plan.explained.get((pair.type, pair.accessor))
        says = engine_says(data_types, pair.type, pair.accessor)
        out.append(f"  {'~' if why else '!'} {pair.name}, then {', '.join(pair.continuations)}"
                   + (f"   [{says}]" if says and not why else ""))
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="See the module docstring for the two kinds of gap and the exit code.")
    parser.add_argument("--dry-run", action="store_true", help="report and write nothing")
    parser.add_argument("--source", choices=("auto", "install", "snapshot"), default="auto",
                        help="vanilla's loc: the game install, the vanilla_parsed/ snapshot, or "
                             "(default) the install when there is one")
    parser.add_argument("--data-types", metavar="DIR", default=None,
                        help="a folder holding the engine's data_types_*.txt (default: the "
                             "Modding-Digests docs path_constants resolves)")
    parser.add_argument("--drop", metavar="TYPE.ACCESSOR", action="append", default=[],
                        help="remove this entry from the extras (repeatable): one the fold "
                             "added through a wrong type upstream")
    parser.add_argument("--prune", action="store_true",
                        help="also remove every entry no chain in vanilla's loc calls")
    args = parser.parse_args(argv)

    lines, source = load_vanilla_lines(args.source)
    data_types = load_data_types(args.data_types or default_data_types_dir())
    plan = plan_fold(
        lines, audit_mod.HAND_TYPED_ACCESSORS, audit_mod.VANILLA_EXTRACTED_ACCESSORS,
        engine_docs_dir=str(ENGINE_DOCS), drop=tuple(args.drop), prune=args.prune)
    print(render_plan(plan, source, data_types, dry_run=args.dry_run,
                      mod_uses=mod_calls(plan.pruned)))

    if args.dry_run:
        print("\ndry run: nothing written")
    elif plan.changed:
        EXTRAS.write_text(render_extras(plan.extras), encoding="utf-8")
        print(f"\nrewrote {EXTRAS.name}")
    else:
        print(f"\n{EXTRAS.name} is up to date")
    return 1 if plan.needs_hand_typing else 0


if __name__ == "__main__":
    raise SystemExit(main())
