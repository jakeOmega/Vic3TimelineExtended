"""Which loc accessors vanilla calls on a data type, and in which rendering
contexts (#1246), for `GET /loc-accessors/<Type>` and the CLI below.

`/engine-docs/<type>` covers effects, triggers, modifiers, event targets,
on-actions and custom localization, but nothing says which accessors loc and GUI
chain on a `PoliticalLobby`, an `InterestGroup` or a `Country`. Naming lobbies
in the covert exposure events (#1245) needed "does vanilla ever call
`GetMembersDesc` in event text?" and answered it with two hand-written greps.

Every `[...]` chain in vanilla English loc, and in vanilla `.gui` files when the
game is installed, is walked with `localization_accessor_audit`'s own tables:
`resolve_first_step` types the first step (a magic scope of the key's context, a
global constructor such as `PoliticalLobby('x')`), and the audit's catalog types
each later step. Each step after the first is counted under the type its
receiver resolved to, so `SCOPE.sPoliticalLobby('x').GetMembersDesc` counts
`sPoliticalLobby` on `scope_object` and `GetMembersDesc` on `political_lobby`.
Calls nested in a step's arguments (`GetTruceDate(TARGET_COUNTRY.Self)`) are
walked as chains of their own.

A step is counted only while its receiver's type is known. After an accessor the
catalog types as `value` (a name, a number, and also whatever the catalog never
modelled, such as `GetTargetCountry`) or doesn't list, the rest of the chain
can't be attributed; `coverage.unattributed_steps` counts those.

Each use carries the context of the loc key that holds it: the audit's own
(`events`, `journal_entries`, `war_goals`, `treaty_articles` and the three
diplomatic-action ones), the keys the audit leaves `permissive` split by shape
(`notification` for `notification_*`, `ui` for ALL-CAPS GUI strings, `other`),
and `gui` for a `.gui` file.

`returns` is the catalog's type for the accessor, `null` when the catalog
doesn't list it, which is the case `localization_accessor_audit` flags on this
type. `scope_accessor` is the saved-scope accessor on `SCOPE` that yields the
type, as the audit's catalog lists it (`SCOPE.gsInterestGroup`, not the
nonexistent `sInterestGroup`), the one vanilla uses most.

    python3 loc_accessor_usage.py PoliticalLobby [--context events] [--examples 5]
    python3 loc_accessor_usage.py            # every type with its use count
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field

import localization_accessor_audit as audit
import vanilla_parsed

# Steps whose receiver is one of these can't be attributed to a data type.
_UNTYPED = frozenset({"value", "unknown"})
# `SCOPE.<accessor>` forms that build a saved-scope object: `sCountry`,
# `gsInterestGroup`. `GetInterestGroup` and the like read an existing one.
_SCOPE_ACCESSOR_RE = re.compile(r"^g?s[A-Z]")
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")
_EXAMPLES_PER_CONTEXT = 3
DEFAULT_EXAMPLES = 3
MAX_EXAMPLES = 25


# ---------------------------------------------------------------------------
# Contexts
# ---------------------------------------------------------------------------

def usage_context(key: str, diplo_keys: set[str]) -> tuple[str, str]:
    """(context the audit resolves `key`'s first step in, the label to report).

    The audit leaves most of vanilla `permissive`, so that bucket is split by
    key shape for the label only; the resolving context stays `permissive`.
    """
    ctx = audit.classify_context(key, diplo_action_keys=diplo_keys)
    if ctx != "permissive":
        return ctx, ctx
    if key.startswith("notification_"):
        return ctx, "notification"
    if re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
        return ctx, "ui"
    return ctx, "other"


# ---------------------------------------------------------------------------
# Walking a chain
# ---------------------------------------------------------------------------

def _call_args(step: str) -> list[str]:
    """Top-level arguments of a `Func(a, b)` step, split at depth-0 commas
    outside quotes."""
    if not audit._FUNC_CALL_RE.match(step):
        return []
    body = step[step.index("(") + 1: step.rindex(")")]
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    in_quote = False
    for ch in body:
        if ch == "'":
            in_quote = not in_quote
        elif not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                out.append("".join(buf).strip())
                buf = []
                continue
        buf.append(ch)
    out.append("".join(buf).strip())
    return [a for a in out if a]


def _arg_chain(arg: str) -> list[str] | None:
    """The steps of an argument that is itself an accessor chain; `None` for a
    string, a number, a `$X$` substitution or anything else."""
    steps = audit._split_chain(audit._strip_format_modifier(arg))
    if not steps or not _IDENT_RE.fullmatch(audit._step_name(steps[0])):
        return None
    return steps


def _first_step_type(first: str, context: str, aliases: dict[str, str]) -> str:
    """`audit.resolve_first_step`, plus a bare CamelCase data type that names a
    catalog type (`StateGoods` for `state_goods`) the audit has no constructor
    for. An ALL-CAPS name is a magic scope, never a data type."""
    typ = audit.resolve_first_step(first, context)
    if typ == "unknown" and first[:1].isupper() and not first.isupper():
        return aliases.get(_normalize(first), "unknown")
    return typ


def typed_steps(steps: list[str], context: str, catalog: dict[str, dict[str, str]],
                aliases: dict[str, str]):
    """Yield `(receiver_type, accessor_name, attributed)` for every step after a
    chain's first, nested argument chains included. `attributed` is false when
    the receiver's type was lost, with the receiver type "unknown"."""
    first = audit._step_name(steps[0])
    current = _first_step_type(first, context, aliases)
    for i, step in enumerate(steps):
        for arg in _call_args(step):
            nested = _arg_chain(arg)
            if nested:
                yield from typed_steps(nested, context, catalog, aliases)
        if i == 0:
            continue
        name = audit._step_name(step)
        if current in _UNTYPED:
            yield "unknown", name, False
            continue
        yield current, name, True
        nxt = catalog.get(current, {}).get(name)
        current = nxt if nxt and "," not in nxt else "unknown"


# ---------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------

@dataclass
class Use:
    count: int = 0
    contexts: Counter = field(default_factory=Counter)
    # context -> [{source, expression}], at most _EXAMPLES_PER_CONTEXT each
    examples: dict[str, list[dict]] = field(default_factory=dict)


@dataclass
class Index:
    types: dict[str, dict[str, Use]] = field(default_factory=dict)
    coverage: dict = field(default_factory=dict)


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def display_name(typ: str) -> str:
    """`political_lobby` -> `PoliticalLobby`, as vanilla spells the data type."""
    return "".join(p.capitalize() for p in typ.split("_"))


def _type_aliases(catalog: dict[str, dict[str, str]]) -> dict[str, str]:
    return {_normalize(t): t for t in catalog if t not in _UNTYPED}


def _record(index: Index, typ: str, accessor: str, label: str, source: str,
            expression: str) -> None:
    use = index.types.setdefault(typ, {}).setdefault(accessor, Use())
    use.count += 1
    use.contexts[label] += 1
    shown = use.examples.setdefault(label, [])
    if len(shown) < _EXAMPLES_PER_CONTEXT and not any(e["expression"] == expression for e in shown):
        shown.append({"source": source, "expression": expression})


def _scan_text(index: Index, text: str, resolve_ctx: str, label: str, source: str,
               catalog: dict, aliases: dict[str, str]) -> None:
    for chain in audit.extract_chains(text):
        index.coverage["chains"] += 1
        expression = f"[{chain.raw}]"
        for typ, name, attributed in typed_steps(chain.steps, resolve_ctx, catalog, aliases):
            if not attributed:
                index.coverage["unattributed_steps"] += 1
                continue
            index.coverage["attributed_steps"] += 1
            _record(index, typ, name, label, source, expression)


def _gui_files(gui_dirs: list[str]):
    for root in gui_dirs:
        if not os.path.isdir(root):
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs.sort()
            for fname in sorted(files):
                if fname.endswith(".gui"):
                    yield os.path.join(dirpath, fname), root


def build_index(loc: dict[str, str], catalog: dict[str, dict[str, str]], *,
                diplo_keys: set[str] | None = None,
                gui_dirs: list[str] | None = None) -> Index:
    """Index every chain in `loc` ({key: value}) and in the `.gui` files under
    `gui_dirs`."""
    diplo_keys = diplo_keys or set()
    aliases = _type_aliases(catalog)
    index = Index(coverage={
        "loc_keys": len(loc), "gui_files": 0, "chains": 0,
        "attributed_steps": 0, "unattributed_steps": 0,
    })
    for key, value in loc.items():
        if "[" not in value:
            continue
        resolve_ctx, label = usage_context(key, diplo_keys)
        _scan_text(index, value, resolve_ctx, label, key, catalog, aliases)
    for path, root in _gui_files(gui_dirs or []):
        index.coverage["gui_files"] += 1
        rel = os.path.relpath(path, os.path.dirname(root)).replace(os.sep, "/")
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                for line_no, line in enumerate(f, start=1):
                    if "[" not in line or line.lstrip().startswith("#"):
                        continue
                    _scan_text(index, line, "permissive", "gui", f"{rel}:{line_no}",
                               catalog, aliases)
        except OSError:
            continue
    index.coverage["gui_scanned"] = index.coverage["gui_files"] > 0
    return index


# ---------------------------------------------------------------------------
# Reading vanilla
# ---------------------------------------------------------------------------

def load_snapshot_loc(snapshot_dir: str = vanilla_parsed.DEFAULT_DIR) -> dict[str, str]:
    """Vanilla English loc from the committed snapshot, without decoding its
    entity files."""
    manifest = vanilla_parsed.read_manifest(snapshot_dir)
    if manifest is None:
        raise FileNotFoundError(f"no vanilla snapshot at {snapshot_dir}")
    with open(os.path.join(snapshot_dir, manifest["localization"]["file"]),
              encoding="utf-8") as f:
        return json.load(f)


def load_catalog(engine_docs_dir: str) -> dict[str, dict[str, str]]:
    """The audit's `{type: {accessor: return type}}` catalog."""
    return audit._load_engine_catalog(engine_docs_dir)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def _public_types(index: Index) -> list[str]:
    return [t for t in index.types if t not in _UNTYPED]


def resolve_type(index: Index, catalog: dict[str, dict[str, str]], query: str) -> str | None:
    """`PoliticalLobby`, `political_lobby` and `politicallobby` all name the
    catalog type `political_lobby`; `None` when neither the catalog nor the
    index has it."""
    wanted = _normalize(query)
    if not wanted:
        return None
    for typ in sorted({*catalog, *_public_types(index)} - _UNTYPED):
        if _normalize(typ) == wanted:
            return typ
    return None


def suggest(index: Index, catalog: dict[str, dict[str, str]], query: str) -> list[str]:
    shown = {_normalize(t): display_name(t) for t in {*catalog, *_public_types(index)} - _UNTYPED}
    close = difflib.get_close_matches(_normalize(query), list(shown), n=5, cutoff=0.6)
    return [shown[c] for c in close]


def contexts_seen(index: Index) -> list[str]:
    seen: set[str] = set()
    for accessors in index.types.values():
        for use in accessors.values():
            seen.update(use.contexts)
    return sorted(seen)


def list_types(index: Index) -> dict:
    """Every type with the accessors vanilla chains on it."""
    rows = []
    for typ in _public_types(index):
        accessors = index.types[typ]
        rows.append({
            "type": typ,
            "name": display_name(typ),
            "accessors": len(accessors),
            "uses": sum(u.count for u in accessors.values()),
        })
    rows.sort(key=lambda r: (-r["uses"], r["type"]))
    return {"coverage": dict(index.coverage), "contexts": contexts_seen(index), "types": rows}


def _scope_accessors(index: Index, catalog: dict[str, dict[str, str]], typ: str) -> list[dict]:
    seen = index.types.get("scope_object", {})
    rows = [
        {"name": f"SCOPE.{acc}", "uses": seen[acc].count if acc in seen else 0}
        for acc, ret in catalog.get("scope_object", {}).items()
        if ret == typ and _SCOPE_ACCESSOR_RE.match(acc)
    ]
    rows.sort(key=lambda r: (-r["uses"], r["name"]))
    return rows


def _pick_examples(use: Use, contexts: list[str], limit: int) -> list[dict]:
    """Up to `limit` examples, one per context in turn so a rare context isn't
    crowded out by a common one."""
    picked: list[dict] = []
    for round_ in range(_EXAMPLES_PER_CONTEXT):
        for ctx in contexts:
            shown = use.examples.get(ctx, [])
            if round_ < len(shown) and len(picked) < limit:
                picked.append({"context": ctx, **shown[round_]})
    return picked


def lookup(index: Index, catalog: dict[str, dict[str, str]], query: str, *,
           context: str | None = None, examples: int = DEFAULT_EXAMPLES,
           min_uses: int = 1) -> dict | None:
    """The accessors vanilla chains on the type `query` names, or `None` for an
    unknown type. `context` keeps only uses in that context; `min_uses` drops
    rarer accessors."""
    typ = resolve_type(index, catalog, query)
    if typ is None:
        return None
    rows = []
    for acc, use in index.types.get(typ, {}).items():
        counts = Counter({context: use.contexts[context]}) if context else use.contexts
        if context and not counts[context]:
            continue
        uses = sum(counts.values())
        if uses < min_uses:
            continue
        ordered = [c for c, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
        rows.append({
            "name": acc,
            "uses": uses,
            "contexts": {c: counts[c] for c in ordered},
            "returns": catalog.get(typ, {}).get(acc),
            "examples": _pick_examples(use, ordered, examples),
        })
    rows.sort(key=lambda r: (-r["uses"], r["name"]))
    scope = _scope_accessors(index, catalog, typ)
    return {
        "type": typ,
        "name": display_name(typ),
        "context": context,
        "scope_accessor": scope[0]["name"] if scope else None,
        "scope_accessors": scope,
        "uses": sum(r["uses"] for r in rows),
        "accessors": rows,
        "gui_scanned": bool(index.coverage.get("gui_scanned")),
        "coverage": dict(index.coverage),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("type", nargs="?", help="data type, e.g. PoliticalLobby or political_lobby")
    parser.add_argument("--context", help="only uses in this context (events, notification, gui, …)")
    parser.add_argument("--examples", type=int, default=DEFAULT_EXAMPLES)
    parser.add_argument("--min-uses", type=int, default=1)
    args = parser.parse_args()

    from path_constants import mod_path
    catalog = load_catalog(os.path.join(mod_path, "docs", "engine"))
    gui_dirs: list[str] = []
    try:
        from path_constants import base_game_path
        gui_dirs.append(os.path.join(base_game_path, "game", "gui"))
    except RuntimeError:
        pass
    index = build_index(load_snapshot_loc(), catalog, gui_dirs=gui_dirs)
    if not args.type:
        print(json.dumps(list_types(index), indent=2))
        return 0
    out = lookup(index, catalog, args.type, context=args.context,
                 examples=min(max(args.examples, 0), MAX_EXAMPLES), min_uses=args.min_uses)
    if out is None:
        print(f"unknown type {args.type!r}; did you mean {suggest(index, catalog, args.type)}")
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
