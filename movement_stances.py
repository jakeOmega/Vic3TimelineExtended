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
Vanilla script switches three more from outside the movement files
(EXTERNAL_SWITCHES); test_movement_stances fails when the mod, or vanilla
where the game is installed, gains another.

Why it matters: a law a movement backs gets that movement's support as
enactment success, and under the Direct Democracy and Free Federation
amendments a law no movement backs pays a flat -10% success (#841; they
used to block it outright with `country_must_have_movement_to_enact_laws_bool`).

Two readings of "backs", both reported:
- `unbacked_laws` (the absolute reading, #838's): no movement rates the law
  `approve` or better.
- `never_backed_laws` (the comparative reading): no movement rates the law
  above any other law of its group, so whatever law is in force, no
  movement prefers this one. The engine most likely means this
  (`PoliticalMovement.EndorsesEnactingLaw`; the defines' "comparative
  stance"; scripting_best_practices.md on the movement bool), so a movement
  content with the current law backs nothing. `current=<law>` gives the
  comparative reading from one law in force.

The functions take merged {name: parsed body} dicts (`ModState.get_data`), so
the server endpoints (`/movements`, `/movement-stances`) and the CLI share
them:

    python3 movement_stances.py --movements
    python3 movement_stances.py --lawgroup lawgroup_rules_of_war [--current law_x]
    python3 movement_stances.py --law law_total_war
    python3 movement_stances.py --gaps
    python3 movement_stances.py --standing

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
    "Technologies": "technology/technologies",
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

# Core-ideology switches vanilla script makes from outside the movement files,
# {movement: (ideology, ...)}; the movement bodies' own switches are read from
# the data. Verified against 1.15.0.
EXTERNAL_SWITCHES = {
    # events/russia_events/ip5_communism_events.txt:390 and :619 (1.15 dropped
    # communism.txt's switch of movement_communist to the vanguardist movement)
    "movement_socialist": ("ideology_revolutionary_socialist_movement", "ideology_state_socialist_movement"),
    # events/japan_events/ep2_meiji_restoration.txt:91
    "movement_tokugawa_loyalist": ("ideology_tokugawa_loyalist_movement_2",),
    # common/scripted_effects/00_victoria_ep2_scripted_effects.txt:2696
    "movement_meiji_restorationist": ("ideology_meiji_restorationist_movement_daijoi",),
}


def _items(body):
    """(key, value) pairs of a parsed block, a repeated key's list expanded."""
    if not isinstance(body, dict):
        return
    for k, v in body.items():
        for item in v if isinstance(v, list) else [v]:
            yield k, _unwrap(item)


def _walk(body, key: str, negated: bool = False):
    """Yield (value, negated) for every `key = value` anywhere under `body`.
    `negated` is true under an odd number of NOT / NOR / NAND."""
    for k, v in _items(body):
        if k == key:
            yield v, negated
        elif isinstance(v, dict):
            yield from _walk(v, key, negated != (k in _NEGATIONS))


def tech_gate(trigger) -> list[str]:
    """Technologies a `creation_trigger` names with `has_technology_researched`
    outside a NOT / NOR / NAND. An OR's alternatives are listed alike."""
    out: list[str] = []
    for tech, negated in _walk(trigger, "has_technology_researched"):
        if isinstance(tech, str) and not negated and tech not in out:
            out.append(tech)
    return out


def movement_ideologies(body, name: str | None = None) -> list[tuple[str, str]]:
    """[(ideology, via)]: the declared `ideology` (via "ideology") first, then
    every `set_core_ideology` target in the movement's own body, then those
    EXTERNAL_SWITCHES lists for `name` (both via "set_core_ideology")."""
    out: list[tuple[str, str]] = []
    declared = _unwrap(body.get("ideology")) if isinstance(body, dict) else None
    if isinstance(declared, str):
        out.append((declared, "ideology"))
    seen = {i for i, _ in out}
    switches = [i for i, _neg in _walk(body, "set_core_ideology")]
    switches += list(EXTERNAL_SWITCHES.get(name, ()))
    for ideology in switches:
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
    held = movement_ideologies(body, name)
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
    value = block.get(parent_of.get(law, law))
    if isinstance(value, list) and value:
        value = value[-1]  # a repeated line: the engine keeps the last
    value = _unwrap(value)
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
        for ideology, via in movement_ideologies(_unwrap(movements[name]), name):
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

    Over the enactable laws (carriers left out): `unbacked_laws` lists those
    no movement rates `approve` or better, `never_backed_laws` those no
    movement rates above any other law of the group (see the module
    docstring). With `current` (a law of the group), each row also carries
    `backs`, the enactable laws it rates above `current`, and
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
    never_backed = [law for law in enactable if not any(
        _rank(row["stances"][law]) > _rank(row["stances"][other])
        for row in rows for other in enactable if other != law)]
    if current is not None:
        for row in rows:
            floor = _rank(row["stances"][current])
            row["backs"] = [law for law in enactable
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
        "never_backed_laws": never_backed,
    }
    if current is not None:
        out["mode"] = "comparative"
        out["current"] = current
    return out


def stance_gaps(movements: dict, ideologies: dict, laws: dict, carriers=frozenset(),
                vanilla_lawgroups=None) -> dict:
    """Law groups no movement holds a stance on, and per group the enactable
    laws no movement backs, in both readings (lawgroup_stances).

    {"lawgroups_without_stance": [{lawgroup, origin, laws}],
     "unbacked_laws": [{lawgroup, origin, laws}],
     "never_backed_laws": [{lawgroup, origin, laws}]}

    `origin` is the law group's: "vanilla" when `vanilla_lawgroups` holds it,
    else "mod" (omitted when `vanilla_lawgroups` is None). A vanilla group
    can hold laws the mod adds.
    """
    groups: dict = {}
    for law, g in law_groups(laws).items():
        groups.setdefault(g, []).append(law)
    no_stance: list[dict] = []
    unbacked: list[dict] = []
    never_backed: list[dict] = []
    for g in sorted(groups):
        result = lawgroup_stances(g, movements, ideologies, laws, carriers)
        row = {"lawgroup": g}
        if vanilla_lawgroups is not None:
            row["origin"] = "vanilla" if g in vanilla_lawgroups else "mod"
        if not result["movements"]:
            no_stance.append({**row, "laws": result["laws"]})
            continue
        if result["unbacked_laws"]:
            unbacked.append({**row, "laws": result["unbacked_laws"]})
        if result["never_backed_laws"]:
            never_backed.append({**row, "laws": result["never_backed_laws"]})
    return {"lawgroups_without_stance": no_stance, "unbacked_laws": unbacked,
            "never_backed_laws": never_backed}


# ---------------------------------------------------------------------------
# Standing grievances (#1832): a stance on a law no government can leave
# ---------------------------------------------------------------------------
# A movement's target activism takes MOVEMENT_RADICALISM_FROM_ACTIVE_LAW_STANCE
# (vanilla's -0.05) x the stance x its active_law_radicalism_multiplier from
# each law in force. So a disapproved law that a country holds from 1836, while
# nothing the movement rates higher can be enacted, is activism no government
# can answer. The rule (test_movement_stance_guard.py): a movement may
# disapprove of a law a country can hold from 1836 only if it rates higher a
# law of the same group that a country can enact within GRACE_ERAS (one) of
# the era in which the movement can first exist. The resolution is an era
# (about 25 years); the grace is the owner's (2026-11-15).
#
# How each side is read:
# - When a movement can first exist: the technologies its `creation_trigger`
#   names (a block's conditions all hold, so the latest; an OR's alternatives,
#   the earliest). Anything else (laws, cultures, scripted triggers) is read as
#   true from 1836 and a negation as never delaying, so an unread condition
#   can only make the movement earlier and the guard err toward a flag. A
#   movement that switches ideology (`set_core_ideology`) holds the new one
#   from its own first era.
# - When a law can first be enacted: its `unlocking_technologies` (any of),
#   one of its `unlocking_laws` (any of, each at its own first era), and the
#   technology and law conditions of its `can_enact` and `is_visible`.
#   `always = no` there means never. A `trigger_if` is an exception for the
#   countries its limit picks (vanilla's British India, Congress Poland) and
#   doesn't delay anyone else. Any other condition (a tag, subject status, a
#   government type, a scripted trigger) is one the guard can't place in
#   time: the answer is "unread", and a row whose only answers in time are
#   unread is not counted as answered.
# - A law a country can hold from 1836: one whose first era is 1, or one the
#   history's GLOBAL every_country block activates (`seeded`).
# - An answer: another law of the group the ideology rates higher, not a
#   carrier, not barred by a law the one in force needs (Unregulated
#   Donations needs a voting law, which bars No Campaign Finance Laws).

_ERA_NEVER = None
# How many eras after the movement's first an answer may open and still count
# (the owner, 2026-11-15: "grace").
GRACE_ERAS = 1
_SCOPE_FREE_KEYS = frozenset({"AND", "hidden_trigger", "custom_tooltip", "limit"})


def technology_eras(technologies: dict) -> dict:
    """{technology: era number} from `era = era_N`."""
    out: dict = {}
    for name, raw in technologies.items():
        body = _unwrap(raw)
        era = _unwrap(body.get("era")) if isinstance(body, dict) else None
        if isinstance(era, str) and era.startswith("era_"):
            out[_entity_name(name)] = int(era.split("_", 1)[1])
    return out


def _entity_name(key: str) -> str:
    return key.rsplit(":", 1)[-1]


def _as_names(raw) -> list:
    """A field's value as a flat list of names (`x`, `{ x y }`, repeated keys)."""
    value = _unwrap(raw)
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    out: list = []
    if isinstance(value, (list, tuple)):
        for item in value:
            out.extend(_as_names(item))
    return [x for x in out if isinstance(x, str)]


class _EraReader:
    """Earliest era a trigger can hold. `strict` reads it as a law's gate
    (unknown conditions are recorded in `unread`, a negation too); otherwise
    as a movement's creation_trigger (only technologies count)."""

    def __init__(self, eras: dict, law_era=None, strict: bool = True):
        self.eras, self.law_era, self.strict = eras, law_era, strict
        self.unread: set = set()
        self.unknown_techs: set = set()

    def _tech(self, tech: str) -> int:
        if tech not in self.eras:
            self.unknown_techs.add(tech)
            return 99
        return self.eras[tech]

    def era(self, body, any_of: bool = False):
        """None means never."""
        values: list = []
        for key, value in _items(body):
            if key == "has_technology_researched" and isinstance(value, str):
                values.append(self._tech(value))
            elif key == "always" and isinstance(value, str):
                values.append(_ERA_NEVER if value == "no" else 1)
            elif key in ("has_law", "has_law_or_variant") and isinstance(value, str) and value.startswith("law_type:"):
                if self.strict and self.law_era is not None:
                    values.append(self.law_era(value.split(":", 1)[1]))
                else:
                    values.append(1)
            elif key == "text":
                continue  # custom_tooltip's loc key
            elif key in _NEGATIONS:
                if self.strict:
                    self.unread.add(key)
                values.append(1)
            elif key in ("trigger_if", "trigger_else", "trigger_else_if"):
                values.append(1)
            elif key == "OR" and isinstance(value, dict):
                values.append(self.era(value, any_of=True))
            elif isinstance(value, dict):
                if self.strict and key not in _SCOPE_FREE_KEYS:
                    self.unread.add(key)
                values.append(self.era(value))
            else:
                if self.strict:
                    self.unread.add(key)
                values.append(1)
        if not values:
            return 1
        known = [v for v in values if v is not _ERA_NEVER]
        if any_of:
            return min(known) if known else _ERA_NEVER
        return _ERA_NEVER if len(known) < len(values) else max(known)


def movement_first_era(body, eras: dict) -> tuple[int, set]:
    """(the first era a movement can exist in, technologies the era table lacks)."""
    trigger = _unwrap(body.get("creation_trigger")) if isinstance(body, dict) else None
    reader = _EraReader(eras, strict=False)
    era = reader.era(trigger) if isinstance(trigger, dict) else 1
    return (1 if era is _ERA_NEVER else era), reader.unknown_techs


def law_gates(laws: dict, eras: dict) -> tuple[dict, set]:
    """({law: {"group", "era" (None = never), "unread" (sorted), "needs", "barred_by"}},
    technologies the era table lacks)."""
    bodies = {name: _unwrap(raw) for name, raw in laws.items()}
    bodies = {n: b for n, b in bodies.items() if isinstance(b, dict) and isinstance(_unwrap(b.get("group")), str)}
    memo: dict = {}
    unknown: set = set()

    def gate(law: str, stack: tuple = ()) -> dict:
        if law in memo:
            return memo[law]
        if law not in bodies or law in stack:
            return {"era": _ERA_NEVER if law in stack else 1, "unread": []}
        body = bodies[law]
        techs = _as_names(body.get("unlocking_technologies"))
        unread: set = set()
        reader = _EraReader(eras, law_era=lambda x: gate(x, stack + (law,))["era"])
        era = min(reader._tech(t) for t in techs) if techs else 1
        needs = _as_names(body.get("unlocking_laws"))
        if needs:
            options = [(gate(x, stack + (law,)), x) for x in needs]
            clean = [g["era"] for g, _ in options if g["era"] is not _ERA_NEVER and not g["unread"]]
            any_era = [g["era"] for g, _ in options if g["era"] is not _ERA_NEVER]
            if clean:
                era = max(era, min(clean))
            elif any_era:
                era = max(era, min(any_era))
                unread.add("unlocking_laws")
            else:
                era = _ERA_NEVER
        for key in ("can_enact", "is_visible"):
            trigger = _unwrap(body.get(key))
            if isinstance(trigger, dict) and era is not _ERA_NEVER:
                cond = reader.era(trigger)
                era = _ERA_NEVER if cond is _ERA_NEVER else max(era, cond)
        unread |= {f"{k}" for k in reader.unread}
        unknown.update(reader.unknown_techs)
        out = {
            "group": _unwrap(body.get("group")),
            "era": era,
            "unread": sorted(unread),
            "needs": needs,
            "barred_by": _as_names(body.get("disallowing_laws")),
        }
        if not stack:
            memo[law] = out
        return out

    return {law: gate(law) for law in sorted(bodies)}, unknown


def standing_grievances(movements: dict, ideologies: dict, laws: dict, technologies: dict,
                        carriers=frozenset(), seeded=frozenset(), open_gates=frozenset(),
                        grace: int = GRACE_ERAS) -> dict:
    """Every (movement, ideology, law it disapproves of that a country can hold
    from 1836), with the laws it rates higher and its verdict (see the section
    comment above):

    {"rows": [{movement, ideology, via, first_era, law, group, stance,
               answers: [{law, stance, era, unread}], verdict}],
     "unknown_technologies": [...]}

    `verdict` is "answered" (an answer opens by `first_era` + `grace` with
    nothing unread, or its unread conditions are in `open_gates`), "unread" (every
    answer in time has a condition the guard can't place) or "standing" (no
    answer opens in time)."""
    eras = technology_eras(technologies)
    gates, unknown = law_gates(laws, eras)
    parent_of = law_parents(laws)
    members: dict = {}
    for law, g in gates.items():
        members.setdefault(g["group"], []).append(law)
    holdable = {law for law, g in gates.items()
                if law not in carriers and (law in seeded or g["era"] == 1)}
    rows: list = []
    for name in sorted(movements):
        body = _unwrap(movements[name])
        if not isinstance(body, dict):
            continue
        first_era, missing = movement_first_era(body, eras)
        unknown |= missing
        for ideology, via in movement_ideologies(body, name):
            ideology_body = _unwrap(ideologies.get(ideology))
            if not isinstance(ideology_body, dict):
                continue
            for group, laws_of_group in sorted(members.items()):
                block = _unwrap(ideology_body.get(group))
                if isinstance(block, list) and block:
                    block = _unwrap(block[-1])
                if not isinstance(block, dict):
                    continue
                ranks = {law: _rank(_stance(block, law, parent_of)[0]) for law in laws_of_group}
                for law in laws_of_group:
                    if law not in holdable or ranks[law] >= 0:
                        continue
                    needs = set(gates[law]["needs"])
                    answers = [
                        {"law": other, "stance": ranks[other], "era": gates[other]["era"],
                         "unread": [] if other in open_gates else gates[other]["unread"]}
                        for other in laws_of_group
                        if other != law and other not in carriers and ranks[other] > ranks[law]
                        and gates[other]["era"] is not _ERA_NEVER
                        and not (needs and needs <= set(gates[other]["barred_by"]))
                    ]
                    in_time = [a for a in answers if a["era"] <= first_era + grace]
                    verdict = ("answered" if any(not a["unread"] for a in in_time)
                               else "unread" if in_time else "standing")
                    rows.append({
                        "movement": name, "ideology": ideology, "via": via, "first_era": first_era,
                        "law": law, "group": group, "stance": ranks[law], "answers": answers,
                        "verdict": verdict,
                    })
    return {"rows": rows, "unknown_technologies": sorted(unknown)}


VERDICT_RANK = {"answered": 0, "unread": 1, "standing": 2}


def new_grievances(merged: dict, vanilla: dict) -> list:
    """Rows of `merged` (standing_grievances on the mod's data) whose verdict is
    worse than vanilla's own data gives the same (movement, ideology, law), a
    row vanilla lacks counting as answered there: what the mod made, leaving
    vanilla's design to vanilla."""
    base = {(r["movement"], r["ideology"], r["law"]): VERDICT_RANK[r["verdict"]] for r in vanilla["rows"]}
    return [r for r in merged["rows"]
            if VERDICT_RANK[r["verdict"]] > base.get((r["movement"], r["ideology"], r["law"]), 0)]


def history_seeded_laws(mod_path: str) -> set:
    """Laws common/history/extra_history.txt's GLOBAL every_country block
    activates, its conditional lines included (the 1836 baseline of the mod's
    law groups)."""
    import re

    path = os.path.join(mod_path, "common", "history", "extra_history.txt")
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    m = re.search(r"(?m)^\tevery_country\s*=\s*\{", text)
    if not m:
        return set()
    depth, i = 1, m.end()
    while depth and i < len(text):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return set(re.findall(r"activate_law\s*=\s*law_type:(law_\w+)", text[m.end():i]))


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
    what.add_argument("--standing", action="store_true",
                      help="movements' stances on laws no government can leave (#1832): every row the mod "
                           "makes worse than vanilla, then vanilla's own")
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
    elif args.standing:
        def run(data, carriers_, seeded):
            return standing_grievances(data.get("Political Movements") or {}, data.get("Ideologies") or {},
                                       data.get("Laws") or {}, data.get("Technologies") or {},
                                       carriers_, seeded)
        merged = run({et: ms.get_data(et) or {} for et in ENTITY_TYPES}, carriers,
                     history_seeded_laws(args.mod_path))
        base = run(vanilla, frozenset(), frozenset())
        out = {"made_by_the_mod": new_grievances(merged, base),
               "vanilla": [r for r in base["rows"] if r["verdict"] != "answered"],
               "unknown_technologies": merged["unknown_technologies"]}
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
