"""The Extraplanetary Base's ground types: the reference the generated script matches.

Design: ``docs/superpowers/specs/2026-11-05-extraplanetary-base-ground-types-design.md``
(§ n below means that document's). Plan:
``docs/superpowers/plans/2026-11-21-extraplanetary-base-ground-types.md``.

A site is its ground type and its grade (§ 6). Each type has one mix: a level's
output of each of the basket's seven goods against the method's output at grade 0,
as a signed fraction. Each mix is normalized so that its mean over the basket,
weighted by value at base prices, is exactly zero; a site's grade is then exactly
its value-weighted mean score, and at base prices every type earns a level's base
profit (§ 6.1).

It also holds the month (§ 8.2 to § 8.5) as a Python model, ``month()`` and the
functions beside it: the reference the generated script must match, rule for rule.

This module holds no game data of its own beyond the design's constants. The
grades come from ``gen_solar_sites.SITES``; the base methods and the prices of
goods outside the seven are read from the mod's files on first use. Nothing here
reads a file at import.
"""

from __future__ import annotations

import functools
import math
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen_solar_sites as gss  # noqa: E402

# --- § 6 and § 7: goods, types, the basket -----------------------------------------

# The basket's seven goods, in this order everywhere (plan, Global Constraints):
# Structural Metals, Tech-Critical Metals, Gold, Conductive Metals, Base Metals,
# Chemical and Industrial Minerals, Glass and Plastics.
GOODS: tuple[str, ...] = ("iron", "tech_metals", "gold", "copper", "lead", "sulfur", "glass")

# Their base prices (the goods files' `cost`; test_ebase_ground holds them in step).
BASE_PRICE: dict[str, int] = {
    "iron": 40, "tech_metals": 80, "gold": 100, "copper": 40, "lead": 40, "sulfur": 50, "glass": 40,
}

# The seven ground types (§ 6.2), in this order everywhere. Mixed is the reference:
# the basket as it comes.
TYPES: tuple[str, ...] = ("mixed", "metallic", "rocky", "carbonaceous", "sulfurous", "hydrocarbon", "icy")

# Each type's composition, a factor of the basket before normalization, in GOODS order
# (§ 6.1: a rounded version of the average of the first draft's rows for its sites).
# mix() normalizes it to a value-weighted mean of exactly zero.
_COMPOSITION_ROWS: dict[str, tuple[float, ...]] = {
    "mixed": (1, 1, 1, 1, 1, 1, 1),
    "metallic": (1.2, 1.1, 1.4, 1.2, 1.0, 0.3, 0.1),
    "rocky": (1.3, 1.0, 0.5, 0.85, 0.85, 1.1, 1.4),
    "carbonaceous": (0.8, 0.9, 0.65, 0.9, 0.9, 2.0, 2.1),
    "sulfurous": (0.8, 0.85, 0.6, 1.0, 1.0, 4.0, 1.2),
    "hydrocarbon": (0.75, 0.85, 0.5, 0.8, 0.8, 1.8, 3.5),
    "icy": (1.0, 0.95, 0.6, 0.9, 0.9, 1.6, 1.8),
}
COMPOSITION: dict[str, dict[str, float]] = {
    t: dict(zip(GOODS, map(float, row), strict=True)) for t, row in _COMPOSITION_ROWS.items()
}

# Each place's ground type (§ 6.3). `near_earth` is the near-Earth asteroids, the one
# place that is no colony (room 10 at grade 0 with Asteroid Mining).
_SITES_BY_TYPE: dict[str, tuple[str, ...]] = {
    "mixed": ("near_earth",),
    "metallic": ("psyche",),
    "rocky": ("vesta", "valles_marineris", "olympus_mons", "hellas_planitia", "mercury", "tranquility",
              "marius_hills", "daedalus", "imbrium"),
    "carbonaceous": ("ceres", "pallas", "hygiea", "himalia", "callisto", "enceladus"),
    "sulfurous": ("amalthea", "io", "europa", "venus"),
    "hydrocarbon": ("titan", "iapetus", "pluto", "makemake", "sedna"),
    "icy": ("utopia_planitia", "arcadia_planitia", "shackleton", "peary", "ganymede", "rhea", "mimas",
            "titania", "oberon", "miranda", "ariel", "triton", "proteus", "eris", "haumea"),
}
GROUND: dict[str, str] = {place: t for t, places in _SITES_BY_TYPE.items() for place in places}

# The 41 places: the near-Earth asteroids (index 0), then the 40 sites in Site.index
# order (1 to 40). A place's position here is its index in the script.
NEAR_EARTH = "near_earth"
PLACES: tuple[str, ...] = (NEAR_EARTH, *(s.key for s in sorted(gss.SITES, key=lambda s: s.index)))

# The basket (§ 7): the Asteroid Mine's outputs a level. The four mining methods share
# its value shares; Regolith Processing's, the Mining Colony's and Self-Replicating
# Miners' are it scaled.
BASKET: dict[str, float] = {
    "iron": 250, "tech_metals": 175, "gold": 50, "copper": 95, "lead": 10, "sulfur": 25, "glass": 70,
}

# Levels past all of the room work at this grade and count as Mixed (§ 8.6).
OVERFLOW_GRADE: float = gss.OVERFLOW_GRADE / 100

_SITE_GRADE: dict[str, float] = {s.key: s.ebase_grade / 100 for s in gss.SITES}


def shares(outputs: dict[str, float]) -> dict[str, float]:
    """Each good's share of the outputs' value at base prices (fractions summing to 1).
    Goods outside the seven are priced from the goods files."""
    values = {g: qty * good_base_price(g) for g, qty in outputs.items()}
    total = sum(values.values())
    return {g: v / total for g, v in values.items()}


def mix(type_: str) -> dict[str, float]:
    """The type's mix (§ 6.1): a level's output of each good against the method's at
    grade 0, a signed fraction. The composition divided by its value-weighted mean over
    the basket, less one, so the mix's own value-weighted mean is exactly zero."""
    composition = COMPOSITION[type_]
    basket = shares(BASKET)
    mean = sum(basket[g] * composition[g] for g in GOODS)
    return {g: composition[g] / mean - 1 for g in GOODS}


def grade(place: str) -> float:
    """The place's grade as a fraction (§ 4): the throughput its levels work at.
    The near-Earth asteroids are 0."""
    return 0.0 if place == NEAR_EARTH else _SITE_GRADE[place]


def score(place: str, good: str) -> float:
    """A level's output of `good` at `place` against the method's at grade 0 (§ 6.1):
    (1 + grade)(1 + mix) - 1."""
    return (1 + grade(place)) * (1 + mix(GROUND[place])[good]) - 1


# --- Prices -----------------------------------------------------------------------

_PRICES: dict[str, float] | None = None


def good_base_price(good: str) -> float:
    """A good's base price: BASE_PRICE for the seven, the goods files for any other
    (the mining methods' inputs), read once on first use, as pm_costs prices the cost
    comments."""
    if good in BASE_PRICE:
        return BASE_PRICE[good]
    global _PRICES
    if _PRICES is None:
        import pm_costs

        _PRICES = pm_costs.load_goods()
    return _PRICES[good]


# --- The base methods (Task 2) ----------------------------------------------------

BASE_GROUP = "pmg_base_building_space_mine"


class MethodGoods(NamedTuple):
    """A method's goods a level at grade 0: its `workforce_scaled` lines."""

    outputs: dict[str, float]
    inputs: dict[str, float]


def _unwrap(value):
    while isinstance(value, tuple) and len(value) == 2:
        value = value[1]
    return value


def _parse_dir(*parts: str) -> dict:
    from paradox_file_parser import ParadoxFileParser

    parser = ParadoxFileParser()
    for path in sorted((ROOT.joinpath(*parts)).glob("*.txt")):
        parser.parse_file(str(path))
    return {key: _unwrap(value) for key, value in parser.data.items()}


def _goods_lines(block: dict, direction: str) -> dict[str, float]:
    prefix, suffix = f"goods_{direction}_", "_add"
    return {key[len(prefix):-len(suffix)]: float(_unwrap(v)) for key, v in block.items()
            if key.startswith(prefix) and key.endswith(suffix)}


@functools.lru_cache(maxsize=1)
def _read_base_methods() -> tuple[tuple[str, MethodGoods], ...]:
    groups = _parse_dir("common", "production_method_groups")
    pms = _parse_dir("common", "production_methods")
    listed = _unwrap(groups[BASE_GROUP]["production_methods"])
    listed = listed if isinstance(listed, list) else [listed]
    out = []
    for pm in map(str, listed):
        block = _unwrap(_unwrap(pms[pm])["building_modifiers"])
        block = _unwrap(block["workforce_scaled"])
        out.append((pm, MethodGoods(_goods_lines(block, "output"), _goods_lines(block, "input"))))
    return tuple(out)


def base_methods() -> dict[str, MethodGoods]:
    """Every method of the Extraplanetary Base's base group (BASE_GROUP), in the group's
    order, with its `workforce_scaled` goods a level, read from the mod's production
    method files on first use. Never a hard-coded list."""
    return {pm: MethodGoods(dict(m.outputs), dict(m.inputs)) for pm, m in _read_base_methods()}


def mining_methods() -> dict[str, MethodGoods]:
    """The base methods whose outputs are all within GOODS, in the group's order: the
    ones the basket, the mix and the month count. Methods with goods outside the seven
    are left out."""
    return {pm: m for pm, m in base_methods().items() if set(m.outputs) <= set(GOODS)}


def method_goods() -> tuple[str, ...]:
    """Every good any mining method makes or uses, GOODS first and then the inputs in
    the order the methods name them: each needs a price (§ 8.3)."""
    seen = list(GOODS)
    for m in mining_methods().values():
        for g in (*m.outputs, *m.inputs):
            if g not in seen:
                seen.append(g)
    return tuple(seen)


# --- The month (Task 4): § 8.2 to § 8.5 as a model --------------------------------
#
# The reference the generated script follows rule for rule. A country's record is a
# BaseState; month() runs § 8.2's steps 1 to 5 on it and returns the next one. Each
# rule is written once, below, in a function named for it:
#
# - the orders (§ 8.2 steps 3 to 5, § 8.3, § 8.4): where new levels go (_give_steps)
#   and where levels leave first (_take_steps), by profit with the checkbox on and by
#   grade with it off, ties by PLACES order; taking runs the same order backward;
# - displacement (step 2), return (step 3), levels gained or lost (step 4), the paced
#   moves (step 5) and the pair a move takes (_checkbox_pair, _manual_pair);
# - the pace (§ 8.5), the checkbox and the buttons (§ 8.4), the forecast (§ 9.1) and
#   the mix (§ 5.2).
#
# Places a mapping leaves out have no room, don't serve, aren't held and earn 0.

PACE_MONTHS = 48  # § 8.5: a quarter of the base a year
MARGIN = 0.05  # § 8.3: a move must gain 5% of the yardstick a level
NOTICE_SHARE = 0.05  # § 9.4: the notice waits until a move has carried 5% of the levels
STEPS = (5, 25)  # § 8.4: a click's levels, and a right-click's


@dataclass
class BaseState:
    """A country's record (§ 8.1), all of it country variables in the script.

    at: levels working at each place now (sr_eb_at_<k>).
    target: levels the player wants there, read only with the checkbox off
        (sr_eb_target_<k>).
    away: levels moved out because a site we hold stopped serving us (blockaded or
        occupied), owed back when it serves again (sr_eb_away_<k>).
    over: levels past all of the room, at -75% and counted as Mixed (sr_eb_over).
    manual: the checkbox is off (sr_eb_manual). Unset, the default, means on.
    placed: the first placement is made (sr_eb_placed).
    moves: the month's paced moves, (from, to, levels) a pass, in order; the record
        the move line and the notice read (§ 9.1, § 9.4). Not stored as is.
    """

    at: dict[str, int] = field(default_factory=dict)
    target: dict[str, int] = field(default_factory=dict)
    away: dict[str, int] = field(default_factory=dict)
    over: int = 0
    manual: bool = False
    placed: bool = False
    moves: tuple[tuple[str, str, int], ...] = ()

    def copy(self) -> BaseState:
        return replace(self, at=dict(self.at), target=dict(self.target), away=dict(self.away))

    @property
    def levels(self) -> int:
        return sum(self.at.values()) + self.over


# --- Prices and profit (§ 8.3) ---

def margin_terms(type_: str) -> dict[str, dict[str, float]]:
    """For each mining method, a level's signed £ a week of each good at grade 0 and
    base prices on ground of `type_`: outputs out × price × (1 + mix), inputs
    -(in × price). The constants the generator bakes into sr_eb_margin_<type>."""
    mix_t = mix(type_)
    terms = {}
    for pm, m in mining_methods().items():
        row: dict[str, float] = {}
        for g, qty in m.outputs.items():
            row[g] = row.get(g, 0.0) + qty * good_base_price(g) * (1 + mix_t[g])
        for g, qty in m.inputs.items():
            row[g] = row.get(g, 0.0) - qty * good_base_price(g)
        terms[pm] = row
    return terms


def margin(type_: str, method_shares: dict[str, float], price_rel: dict[str, float]) -> float:
    """A level's profit a week at grade 0 on ground of `type_` (§ 8.3's bracket):
    Σ_m f(m) × Σ_g term(m, g) × (1 + price_rel(g)). `method_shares` is f(m), the share
    of our mining levels on each mining method; `price_rel` the signed premium of each
    good on our market, inputs included (0 = base price)."""
    terms = margin_terms(type_)
    unknown = set(method_shares) - set(terms)
    if unknown:
        raise ValueError(f"not mining methods of {BASE_GROUP}: {sorted(unknown)}")
    return sum(f * sum(v * (1 + price_rel.get(g, 0.0)) for g, v in terms[pm].items())
               for pm, f in method_shares.items())


def profit_a_level(place: str, method_shares: dict[str, float], price_rel: dict[str, float]) -> float:
    """§ 8.3: a level's profit a week at `place`, (1 + G) × its type's margin."""
    return (1 + grade(place)) * margin(GROUND[place], method_shares, price_rel)


def profits(method_shares: dict[str, float], price_rel: dict[str, float]) -> dict[str, float]:
    """profit_a_level at every place."""
    return {p: profit_a_level(p, method_shares, price_rel) for p in PLACES}


def yardstick(method_shares: dict[str, float]) -> float:
    """§ 8.3: our methods' profit a level at grade 0 and base prices, weighted by their
    levels (£7,250 for an Asteroid Mine). Fixed, so the rule behaves the same when
    profits are small or negative."""
    return margin("mixed", method_shares, {})


def pace(levels: int) -> int:
    """§ 8.5: ceil(L / 48) levels a month, at least 1."""
    return max(1, math.ceil(levels / PACE_MONTHS))


# --- The orders ---

def _index(place: str) -> int:
    return PLACES.index(place)


def by_grade() -> list[str]:
    """Every place best grade first, ties by PLACES order (the near-Earth asteroids
    first among grade 0): today's fill order, gen_solar_sites.ebase_tiers()."""
    return sorted(PLACES, key=lambda p: (-grade(p), _index(p)))


def _by_profit(profit: dict[str, float]) -> list[str]:
    """Every place by profit a level, best first, ties by PLACES order."""
    return sorted(PLACES, key=lambda p: (-profit.get(p, 0.0), _index(p)))


def _give_steps(state: BaseState, room_now: dict[str, int], profit: dict[str, float]) -> list[tuple[str, int]]:
    """§ 8.2 step 4: where levels without a place go, as (place, fill up to) steps.
    Checkbox on: the best place with free room by profit a level while it makes money,
    then by grade. Off: places below their target first, best grade first, up to the
    target; then by grade."""
    if state.manual:
        first = [(p, min(state.target.get(p, 0), room_now[p])) for p in by_grade()
                 if state.target.get(p, 0) > state.at.get(p, 0)]
    else:
        first = [(p, room_now[p]) for p in _by_profit(profit) if profit.get(p, 0.0) > 0]
    return first + [(p, room_now[p]) for p in by_grade()]


def _take_steps(state: BaseState, profit: dict[str, float]) -> list[tuple[str, int]]:
    """§ 8.2 steps 3 and 4: where levels leave first, as (place, down to) steps: the
    place the next move would take from (step 5), the give order run backward.
    Checkbox on: the worst place by profit a level first. Off: places above their
    target first, worst grade first, down to the target; then worst grade first."""
    if state.manual:
        worst = list(reversed(by_grade()))
        return [(p, state.target.get(p, 0)) for p in worst] + [(p, 0) for p in worst]
    return [(p, 0) for p in reversed(_by_profit(profit))]


def _place(at: dict[str, int], levels: int, steps: Iterable[tuple[str, int]]) -> int:
    """Put `levels` into `at` along `steps`; returns what is left past all of them."""
    for p, cap in steps:
        take = min(levels, cap - at.get(p, 0))
        if take > 0:
            at[p] = at.get(p, 0) + take
            levels -= take
    return levels


def _take(at: dict[str, int], levels: int, steps: Iterable[tuple[str, int]], exclude=()) -> int:
    """Take up to `levels` out of `at` along `steps`, never from `exclude`; returns how
    many it took."""
    taken = 0
    for p, floor in steps:
        if p in exclude:
            continue
        take = min(levels - taken, at.get(p, 0) - floor)
        if take > 0:
            at[p] -= take
            taken += take
    return taken


# --- The paced move (§ 8.2 step 5, § 8.3, § 8.4) ---

def _checkbox_pair(state: BaseState, room_now: dict[str, int], profit: dict[str, float],
                   yard: float) -> tuple[str, str, int] | None:
    """§ 8.3: from the place in use that earns least a level to the place with free
    room that earns most, while the gap is at least MARGIN of the yardstick, and
    never to a place that loses money. The worst in use and the best with room are
    the only pair to test: if they don't clear the margin, no pair does."""
    in_use = [p for p in PLACES if state.at.get(p, 0) > 0]
    free = [p for p in PLACES if room_now[p] > state.at.get(p, 0)]
    if not in_use or not free:
        return None
    src = min(in_use, key=lambda p: (profit.get(p, 0.0), -_index(p)))
    dst = max(free, key=lambda p: (profit.get(p, 0.0), -_index(p)))
    gap = profit.get(dst, 0.0) - profit.get(src, 0.0)
    if src == dst or profit.get(dst, 0.0) <= 0 or gap <= 0 or gap < MARGIN * yard:
        return None
    return src, dst, min(state.at[src], room_now[dst] - state.at.get(dst, 0))


def _manual_pair(state: BaseState, room_now: dict[str, int]) -> tuple[str, str, int] | None:
    """§ 8.2 step 5 with the checkbox off: from a place above its target (worst grade
    first) to one below it with free room (best grade first). A level no target calls
    for stays where it works."""
    tgt = state.target
    src = next((p for p in reversed(by_grade()) if state.at.get(p, 0) > tgt.get(p, 0)), None)
    dst = next((p for p in by_grade()
                if state.at.get(p, 0) < min(tgt.get(p, 0), room_now[p])), None)
    if src is None or dst is None:
        return None
    return src, dst, min(state.at[src] - tgt.get(src, 0), min(tgt[dst], room_now[dst]) - state.at.get(dst, 0))


def _moves(state: BaseState, room_now: dict[str, int], profit: dict[str, float], yard: float,
           budget: int | None) -> tuple[tuple[str, str, int], ...]:
    """Move pass after pass, each one pair moving min(pace left, the source's excess,
    the destination's free room), until `budget` levels have moved (None: no pace) or
    no pair qualifies. Each pass empties its source or fills its destination for good,
    so the passes number at most len(PLACES), plus one the pace cuts short."""
    moves = []
    left = math.inf if budget is None else budget
    while left > 0:
        pair = _manual_pair(state, room_now) if state.manual else _checkbox_pair(state, room_now, profit, yard)
        if pair is None:
            break
        src, dst, n = pair
        n = int(min(n, left))
        state.at[src] -= n
        state.at[dst] = state.at.get(dst, 0) + n
        left -= n
        moves.append((src, dst, n))
        if len(moves) > len(PLACES) + 1:
            raise RuntimeError("move passes ran past their bound")
    return tuple(moves)


def _room_now(room: dict[str, int], serves: dict[str, bool] | None) -> dict[str, int]:
    """§ 8.2 step 1: each place's room that serves us this run, 0 otherwise."""
    return {p: room.get(p, 0) if serves is None or serves.get(p, False) else 0 for p in PLACES}


def _clean(at: dict[str, int]) -> dict[str, int]:
    return {p: n for p, n in at.items() if n}


# --- The month (§ 8.2) ---

def month(state: BaseState, *, room: dict[str, int], serves: dict[str, bool], built: int,
          profit: dict[str, float], yard: float, held: dict[str, bool] | None = None) -> BaseState:
    """§ 8.2's steps 1 to 5 on `state`, returning the next state.

    room: each place's room (its levels' room and its staffed Mining Complexes').
    serves: whether each place serves us this run (`site_serves`: held, not blockaded,
        not occupied; the near-Earth asteroids with Asteroid Mining).
    held: whether we hold each place. A place held that doesn't serve is blockaded or
        occupied: its levels go into `away` and come back. A place not held is lost for
        good (ceded, captured, abandoned): it loses its at, target and away. Omitted,
        exactly the places that serve are held.
    built: L, the built levels.
    profit: each place's profit a level this month (profit_a_level); yard: the
        yardstick (yardstick()). Read only with the checkbox on.
    """
    s = state.copy()
    held = serves if held is None else held
    room_now = _room_now(room, serves)  # Step 1

    # Step 2, displacement, at once: where `at` exceeds the room, the excess leaves and
    # is placed as new levels are (step 4). A site held that stopped serving puts it in
    # `away`; room that shrank while the site serves (a Mining Complex unstaffed) does
    # not. A site lost for good loses its at, target and away. The levels past the room
    # join them: room that opens takes them at once, in step 4.
    pool = s.over
    for p in PLACES:
        if not held.get(p, False):
            pool += s.at.pop(p, 0)
            s.target.pop(p, None)
            s.away.pop(p, None)
            continue
        excess = s.at.get(p, 0) - room_now[p]
        if excess > 0:
            s.at[p] -= excess
            pool += excess
            if not serves.get(p, False):
                s.away[p] = s.away.get(p, 0) + excess

    # Step 3, return, at once: a site that serves us again takes back up to its `away`
    # (as far as its room allows), from the levels without a place first, then from
    # where the next move would take levels from (step 5). Its debt is then settled.
    # Sites return best grade first; none takes from another returning this month.
    returned: set[str] = set()
    for p in by_grade():
        if not serves.get(p, False) or p not in s.away:
            continue
        owed = min(s.away.pop(p), room_now[p] - s.at.get(p, 0))
        if owed > 0:
            from_pool = min(owed, pool)
            pool -= from_pool
            got = from_pool + _take(s.at, owed - from_pool, _take_steps(s, profit), exclude=returned | {p})
            s.at[p] = s.at.get(p, 0) + got
        returned.add(p)

    # Step 4, levels gained or lost: L against the levels on record. New levels join
    # the pool; lost levels come off the pool first (the levels past the room, and
    # those displaced this month), then from where the next move would take from.
    # The pool then goes where new levels go (_give_steps); what fits nowhere is past
    # the room.
    have = sum(s.at.values()) + pool
    if built > have:
        pool += built - have
    elif built < have:
        lose = have - built
        cut = min(lose, pool)
        pool -= cut
        _take(s.at, lose - cut, _take_steps(s, profit))
    s.over = _place(s.at, pool, _give_steps(s, room_now, profit))

    # Step 5, moves, paced (§ 8.5): up to the month's pace in levels move. A country's
    # first placement (§ 8.8) is the whole of its first month: it places all its levels
    # at once by the rule in force, and moves nothing.
    s.moves = _moves(s, room_now, profit, yard, pace(built)) if state.placed else ()
    s.placed = state.placed or built > 0
    s.at = _clean(s.at)
    return s


def forecast(state: BaseState, *, room: dict[str, int], profit: dict[str, float], yard: float,
             serves: dict[str, bool] | None = None) -> BaseState:
    """§ 9.1's second row: step 5's rule in force run from where the levels are to where
    it stops, with no pace. With the checkbox on, "If prices hold" (§ 8.3's rule at
    these prices); with it off, "At our assignments" (the targets, as far as levels
    and room allow). `serves` omitted, every place in `room` serves. Its moves are the
    passes it took."""
    s = state.copy()
    s.moves = _moves(s, _room_now(room, serves), profit, yard, None)
    s.at = _clean(s.at)
    return s


def next_place(state: BaseState, *, room: dict[str, int], serves: dict[str, bool], queued: int,
               profit: dict[str, float]) -> str | None:
    """§ 9.3: where the next level goes once the queued levels are placed, by the rule
    in force; None past all of the room."""
    at = dict(state.at)
    steps = _give_steps(state, _room_now(room, serves), profit)
    if _place(at, queued, steps):
        return None
    probe = dict(at)
    if _place(probe, 1, steps):
        return None
    return next(p for p in PLACES if probe.get(p, 0) > at.get(p, 0))


# --- The checkbox and the buttons (§ 8.4) ---

def set_checkbox(state: BaseState, on: bool) -> BaseState:
    """§ 8.4. Off: every place's target is set to the levels on record there, its `at`
    and its `away`, so nothing moves until the player changes one (a blockaded site's
    levels, back, meet their own target). On: the targets are dropped, and the
    checkbox's moves start from where the levels are. Neither moves a level."""
    s = state.copy()
    if on:
        s.manual, s.target = False, {}
    elif not s.manual:
        s.manual = True
        s.target = _clean({p: s.at.get(p, 0) + s.away.get(p, 0) for p in PLACES})
    return s


def assign(state: BaseState, place: str, step: int, *, room: dict[str, int], built: int, queued: int) -> BaseState:
    """§ 8.4's - and + buttons: change `place`'s target by `step` levels. A click while
    the checkbox is on switches it off first. Minus stops at 0. Plus stops at the
    place's room and at the unassigned levels (built and queued less the targets), and
    does nothing without one. Never moves a level."""
    s = set_checkbox(state, on=False)
    now = s.target.get(place, 0)
    if step < 0:
        new = max(0, now + step)
    else:
        unassigned = built + queued - sum(s.target.values())
        new = now + max(0, min(step, room.get(place, 0) - now, unassigned))
    s.target[place] = new
    s.target = _clean(s.target)
    return s


# --- The modifiers (§ 5.2) ---

def mix_now(state: BaseState) -> tuple[float, dict[str, float]]:
    """§ 5.2: T, the average grade over the levels, and D(g), the base's mix: its
    places' types' mixes weighted by levels × (1 + grade). Levels past the room count
    at OVERFLOW_GRADE and as Mixed. Fractions; no levels, all zero."""
    levels = state.levels
    if levels == 0:
        return 0.0, {g: 0.0 for g in GOODS}
    t = (sum(n * grade(p) for p, n in state.at.items()) + state.over * OVERFLOW_GRADE) / levels
    weight = sum(n * (1 + grade(p)) for p, n in state.at.items()) + state.over * (1 + OVERFLOW_GRADE)
    d = {}
    for g in GOODS:
        made = sum(n * (1 + grade(p)) * (1 + mix(GROUND[p])[g]) for p, n in state.at.items())
        d[g] = (made + state.over * (1 + OVERFLOW_GRADE)) / weight - 1
    return t, d
