"""Which political movements hold a stance on a law, and which would back it (#838).

A movement takes its stance on laws from its ideology. The movement declares
`ideology = ideology_x`, and that ideology's `lawgroup_*` blocks rate each law
`strongly_approve` ... `strongly_disapprove`. Two rules from
`ideology_lawgroup_audit` carry over: a law the block leaves out is neutral,
and a variant (`parent = law_x`) takes its parent's stance. A movement can
also switch its core ideology while it lives (`set_core_ideology = ideology_y`
in its own body: seven vanilla movements do, the modernizer stepping from
`_1` to `_2`, the cultural minority through `_2` to `_4`, the fascist to
integralist), so each ideology it can switch to counts as one it can hold.
A `set_core_ideology` in some other file (a scripted effect) is not seen.

Why it matters: the Direct Democracy and Free Federation amendments carry
`country_must_have_movement_to_enact_laws_bool`, so under them a law passes
only with a movement behind it. A law no movement rates `approve` or better
can then never be enacted.

The functions take merged {name: parsed body} dicts (`ModState.get_data`), so
the server endpoints (`/movements`, `/movement-stances`) and the CLI share
them:

    python3 movement_stances.py --movements
    python3 movement_stances.py --lawgroup lawgroup_rules_of_war [--current law_x]
    python3 movement_stances.py --law law_total_war
    python3 movement_stances.py --gaps

The CLI builds a small ModState on the committed `vanilla_parsed/` snapshot,
so it needs no game install.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from ideology_lawgroup_audit import _unwrap, carrier_laws, law_groups, law_parents

ENTITY_TYPES = {
    "Political Movements": "political_movements",
    "Ideologies": "ideologies",
    "Laws": "laws",
    "Law Groups": "law_groups",
}

# Stance -> rank. A movement backs a law it rates BACKING_RANK or better.
STANCE_RANK = {
    "strongly_disapprove": -2,
    "disapprove": -1,
    "neutral": 0,
    "approve": 1,
    "strongly_approve": 2,
}
BACKING_RANK = 1
_NEGATIONS = frozenset({"NOT", "NOR", "NAND"})


def _items(body):
    """(key, value) pairs of a parsed block, a repeated key's list expanded."""
    if not isinstance(body, dict):
        return
    for k, v in body.items():
        for item in v if isinstance(v, list) else [v]:
            yield k, _unwrap(item)


def _walk(body, key: str, negated: bool = False):
    """Yield (value, negated) for every `key = value` anywhere under `body`.
    `negated` is true under NOT / NOR / NAND."""
    for k, v in _items(body):
        if k == key:
            yield v, negated
        elif isinstance(v, dict):
            yield from _walk(v, key, negated or k in _NEGATIONS)


def tech_gate(trigger) -> list[str]:
    """Technologies a `creation_trigger` names with `has_technology_researched`
    outside a NOT / NOR / NAND. An OR's alternatives are listed alike."""
    out: list[str] = []
    for tech, negated in _walk(trigger, "has_technology_researched"):
        if isinstance(tech, str) and not negated and tech not in out:
            out.append(tech)
    return out


def movement_ideologies(body) -> list[tuple[str, str]]:
    """[(ideology, via)]: the declared `ideology` (via "ideology") first, then
    every `set_core_ideology` target in the movement's own body (via
    "set_core_ideology")."""
    out: list[tuple[str, str]] = []
    declared = _unwrap(body.get("ideology")) if isinstance(body, dict) else None
    if isinstance(declared, str):
        out.append((declared, "ideology"))
    seen = {i for i, _ in out}
    for ideology, _neg in _walk(body, "set_core_ideology"):
        if isinstance(ideology, str) and ideology not in seen:
            seen.add(ideology)
            out.append((ideology, "set_core_ideology"))
    return out


def movement_summary(name: str, raw, ideologies: dict | None = None) -> dict:
    """One movement's catalog row:
    {name, category, ideology, alternate_ideologies, creation_trigger_keys,
     tech_gate[, unknown_ideologies]}."""
    body = _unwrap(raw)
    body = body if isinstance(body, dict) else {}
    held = movement_ideologies(body)
    trigger = _unwrap(body.get("creation_trigger"))
    row = {
        "name": name,
        "category": _unwrap(body.get("category")),
        "ideology": next((i for i, via in held if via == "ideology"), None),
        "alternate_ideologies": [i for i, via in held if via == "set_core_ideology"],
        "creation_trigger_keys": list(trigger) if isinstance(trigger, dict) else [],
        "tech_gate": tech_gate(trigger),
    }
    if ideologies is not None:
        unknown = [i for i, _ in held if i not in ideologies]
        if unknown:
            row["unknown_ideologies"] = unknown
    return row


def movement_catalog(movements: dict, ideologies: dict | None = None) -> list[dict]:
    """`movement_summary` for every movement, sorted by name."""
    return [movement_summary(n, movements[n], ideologies) for n in sorted(movements)]


def _stance(block: dict, law: str, parent_of: dict) -> tuple[str, bool]:
    """(stance, explicit) of one law in a lawgroup block. A variant reads its
    parent's line; a law the block leaves out is neutral (explicit False)."""
    value = _unwrap(block.get(parent_of.get(law, law)))
    if isinstance(value, str):
        return value, True
    return "neutral", False


def _rank(stance: str) -> int:
    return STANCE_RANK.get(stance, 0)


def lawgroup_members(laws: dict, lawgroup: str) -> list[str]:
    return sorted(law for law, g in law_groups(laws).items() if g == lawgroup)


def movement_rows(lawgroup: str, members: list[str], movements: dict, ideologies: dict,
                  parent_of: dict) -> list[dict]:
    """One row per (movement, ideology it can hold) whose ideology has a
    block for `lawgroup`."""
    rows: list[dict] = []
    for name in sorted(movements):
        mv = movement_summary(name, movements[name])
        for ideology, via in movement_ideologies(_unwrap(movements[name])):
            ideology_body = _unwrap(ideologies.get(ideology))
            block = _unwrap(ideology_body.get(lawgroup)) if isinstance(ideology_body, dict) else None
            if not isinstance(block, dict):
                continue
            stances: dict = {}
            implicit: list[str] = []
            for law in members:
                stance, explicit = _stance(block, law, parent_of)
                stances[law] = stance
                if not explicit:
                    implicit.append(law)
            row = {
                "movement": name,
                "category": mv["category"],
                "ideology": ideology,
                "via": via,
                "tech_gate": mv["tech_gate"],
                "stances": stances,
            }
            if implicit:
                row["implicit_neutral"] = implicit
            rows.append(row)
    return rows


def lawgroup_stances(lawgroup: str, movements: dict, ideologies: dict, laws: dict,
                     carriers=frozenset(), current: str | None = None) -> dict | None:
    """Every movement's stance on every law of `lawgroup`, or None when no law
    belongs to it.

    `unbacked_laws` lists the enactable laws (carriers left out) that no
    movement rates `approve` or better. With `current` (a law of the group),
    each row also carries `backs`, the laws it rates above `current`, and
    `unbacked_laws` lists the laws no movement rates above it instead.
    """
    members = lawgroup_members(laws, lawgroup)
    if not members:
        return None
    if current is not None and current not in members:
        raise ValueError(f"{current} is not a law of {lawgroup}")
    parent_of = law_parents(laws)
    rows = movement_rows(lawgroup, members, movements, ideologies, parent_of)
    enactable = [law for law in members if law not in carriers]
    if current is not None:
        for row in rows:
            floor = _rank(row["stances"][current])
            row["backs"] = [law for law in members
                            if law != current and _rank(row["stances"][law]) > floor]
        unbacked = [law for law in enactable if law != current
                    and not any(law in row["backs"] for row in rows)]
    else:
        unbacked = [law for law in enactable
                    if not any(_rank(row["stances"][law]) >= BACKING_RANK for row in rows)]
    out = {
        "lawgroup": lawgroup,
        "laws": members,
        "variants": {law: parent_of[law] for law in members if law in parent_of},
        "carriers": [law for law in members if law in carriers],
        "movements": rows,
        "unbacked_laws": unbacked,
    }
    if current is not None:
        out["mode"] = "comparative"
        out["current"] = current
    return out


def stance_gaps(movements: dict, ideologies: dict, laws: dict, carriers=frozenset(),
                vanilla_lawgroups=None) -> dict:
    """Law groups no movement holds a stance on, and per group the enactable
    laws no movement rates `approve` or better.

    {"lawgroups_without_stance": [{lawgroup, origin, laws}],
     "unbacked_laws": [{lawgroup, origin, laws}]}

    `origin` is "vanilla" when `vanilla_lawgroups` holds the group, else "mod"
    (omitted when `vanilla_lawgroups` is None).
    """
    groups: dict = {}
    for law, g in law_groups(laws).items():
        groups.setdefault(g, []).append(law)
    no_stance: list[dict] = []
    unbacked: list[dict] = []
    for g in sorted(groups):
        result = lawgroup_stances(g, movements, ideologies, laws, carriers)
        row = {"lawgroup": g}
        if vanilla_lawgroups is not None:
            row["origin"] = "vanilla" if g in vanilla_lawgroups else "mod"
        if not result["movements"]:
            no_stance.append({**row, "laws": result["laws"]})
        elif result["unbacked_laws"]:
            unbacked.append({**row, "laws": result["unbacked_laws"]})
    return {"lawgroups_without_stance": no_stance, "unbacked_laws": unbacked}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def load_state(mod_path: str):
    """A ModState of ENTITY_TYPES on the committed vanilla_parsed/ snapshot."""
    import vanilla_parsed
    from mod_state import ModState

    snap = vanilla_parsed.load(os.path.join(mod_path, "vanilla_parsed"))
    base = {et: "" for et in ENTITY_TYPES}
    mod = {et: os.path.join(mod_path, "common", d) for et, d in ENTITY_TYPES.items()}
    return ModState(base, mod, vanilla_data=snap.data), snap.data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--movements", action="store_true", help="list every movement")
    what.add_argument("--lawgroup", help="stances on one law group")
    what.add_argument("--law", help="stances on the group of one law")
    what.add_argument("--gaps", action="store_true",
                      help="law groups no movement rates, and laws no movement backs")
    ap.add_argument("--current", help="with --lawgroup/--law: compare against this law")
    ap.add_argument("--mod-path", default=None)
    args = ap.parse_args(argv)

    if args.mod_path is None:
        from path_constants import mod_path as default_mod_path
        args.mod_path = default_mod_path
    ms, vanilla = load_state(args.mod_path)
    movements = ms.get_data("Political Movements") or {}
    ideologies = ms.get_data("Ideologies") or {}
    laws = ms.get_data("Laws") or {}
    carriers = carrier_laws(args.mod_path)
    if args.movements:
        out = movement_catalog(movements, ideologies)
    elif args.gaps:
        out = stance_gaps(movements, ideologies, laws, carriers,
                          set(vanilla.get("Law Groups") or {}))
    else:
        group = args.lawgroup or law_groups(laws).get(args.law)
        if group is None:
            print(f"unknown law: {args.law}", file=sys.stderr)
            return 2
        try:
            out = lawgroup_stances(group, movements, ideologies, laws, carriers, args.current)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 2
        if out is None:
            print(f"no law belongs to {group}", file=sys.stderr)
            return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
