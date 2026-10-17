"""A Python model of the seabed licences (Global Commons, spec §§ 2.3-2.4, 2.9, 3.2).

The script in common/scripted_effects/te_global_commons_seabed_effects.txt
follows this model step for step; each function names the effect it stands
for, and the effects name it back. test_seabed_allocation.py runs it over
random worlds (building, conquest between building and recording,
demolition, annexation, splits, old saves) and checks the pools hold.

THE STATE (as the script keeps it)
- State: te_seabed_basin (1..5), te_seabed_lic_<basin> (licences recorded on
  its Deep-Sea Mine levels, per basin), te_seabed_holder (owner when last
  recorded).
- Country: te_seabed_unbuilt_<basin> (U: entitled and unused),
  te_seabed_held_<basin> (records in its states, refreshed yearly),
  te_seabed_w_<basin> (claim weight), te_seabed_ent_<basin> (entitlement),
  te_seabed_policy (1 Survey, 2 Sponsor, 3 Unilateral).
- Global: te_seabed_regime (1 Open, 2 Regulated, 3 Scramble).

ONE DEPARTURE FROM THE SPEC'S WORDING (decided by the builder): a level is
recorded as soon as it is QUEUED, not when it is finished. The spec's room
already counts queued levels against the share (§ 2.4, "built or queued"),
so recording them is the same accounting one step earlier. It closes the one
leak the spec's version has: a yearly sharing that shrinks an entitlement
while levels are under construction would otherwise leave those levels to
finish with no share, and they would push their basin over its pool. With
queued levels recorded, the water-filling sees them as held and never
shares below them. A cancelled construction gives its licence back at the
next recording, like a demolished level.

HOW THE REGULATED REGIME SPLITS A POOL (decided by the builder; § 3.2 says
"step 2 runs once per half"). Each pool is a reserved half (rounded down)
and an open half. Both halves are water-filled TOGETHER, in one loop: a
country's tentative entitlement is its reserved-half share (if eligible)
plus its open-half share, and it is frozen when its holdings reach that sum.
A frozen country's holdings come off the two halves in proportion to its two
tentative shares (all of them off the open half when it has no reserved
share). A half driven below zero by grandfathered holdings takes the deficit
from the other half, so the basin as a whole never shares out more than its
pool. Licences carry no half: a record is a record. This keeps the invariant
(Σ entitlements = the pool, or the frozen holdings if they exceed it) with
no attribution to store, and a party that holds more than its reserved
share spills into the open half instead of starving the other parties.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

BASINS = ("pacific", "atlantic", "indian", "arctic", "southern")   # 1..5, gen_seabed_basins.BASINS
# te_seabed_pool_<basin> (te_global_commons_seabed_values.txt)
POOLS = {"pacific": 300, "atlantic": 250, "indian": 200, "arctic": 100, "southern": 150}
OPEN, REGULATED, SCRAMBLE = 1, 2, 3
SURVEY, SPONSOR, UNILATERAL = 1, 2, 3

# te_seabed_policy_factor_* / te_seabed_coast_weight / te_seabed_distant_navy_share /
# te_seabed_station_weight / te_seabed_navy_assertive_mult
POLICY_FACTOR = {SURVEY: 0.25, SPONSOR: 1.0, UNILATERAL: 1.0}
COAST_WEIGHT = 2
DISTANT_NAVY_SHARE = 0.05
STATION_WEIGHT = 5
ASSERTIVE_NAVY_MULT = 2


def fx(x: float) -> float:
    """The engine keeps values in units of 1e-5, truncated toward zero."""
    return math.trunc(x * 100000) / 100000


@dataclass
class Country:
    cid: int
    alive: bool = True
    tech: bool = True                # has_technology_researched = abyssal_plain_mining
    policy: int = SURVEY
    navy: float = 0.0                # navy_size
    eligible: bool = False           # te_seabed_reserved_half_eligible (hook)
    barred: bool = False             # te_seabed_southern_barred (hook)
    station: bool = False            # has_variable = te_antarctic_station
    unbuilt: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))
    held: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))
    ent: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))
    weight: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0.0))


@dataclass
class State:
    sid: int
    basin: str | None                # te_seabed_basin; None = landlocked
    owner: int
    incorporated: bool = True
    ports: int = 0                   # building_port levels
    levels: int = 0                  # Deep-Sea Mine level_after_queued_constructions
    lic: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))
    holder: int | None = None        # te_seabed_holder

    @property
    def coastal(self) -> bool:
        return self.basin is not None

    def records(self) -> int:        # te_seabed_state_records
        return sum(self.lic.values())

    def distant(self) -> int:        # te_seabed_state_distant_records
        return sum(v for b, v in self.lic.items() if b != self.basin)


@dataclass
class World:
    countries: dict
    states: dict
    regime: int = OPEN
    fixed: bool = False              # emulate the engine's 1e-5 truncation
    no_share: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))  # te_seabed_noshare_<b>
    iterations: dict = field(default_factory=dict)   # water-filling passes, last sharing, per basin

    def owned(self, cid):
        return [s for s in self.states.values() if s.owner == cid]

    def alive(self, cid) -> bool:
        c = self.countries.get(cid)
        return c is not None and c.alive

    def basin_records(self, b) -> int:
        return sum(s.lic[b] for s in self.states.values())

    def basin_unbuilt(self, b) -> int:
        return sum(c.unbuilt[b] for c in self.countries.values() if c.alive)

    def v(self, x: float) -> float:
        return fx(x) if self.fixed else x


# ---------------------------------------------------------------------------
# Room (te_seabed_room) and the gate (building_ocean_mine's possible)
# ---------------------------------------------------------------------------

def unrecorded(s: State) -> int:
    """te_seabed_state_unrecorded: levels (built or queued) without a record."""
    return max(0, s.levels - s.records())


def room(world: World, cid) -> int:
    """te_seabed_room: unbuilt shares, summed, less the levels not yet recorded."""
    c = world.countries[cid]
    return sum(c.unbuilt.values()) - sum(unrecorded(s) for s in world.owned(cid) if s.coastal)


def can_build(world: World, cid, s: State) -> bool:
    """building_ocean_mine possible, with the rule on (te_seabed_gate)."""
    c = world.countries[cid]
    return s.coastal and c.tech and s.owner == cid and room(world, cid) > 0


# ---------------------------------------------------------------------------
# Recording (te_seabed_record_country and its state steps)
# ---------------------------------------------------------------------------

def _distant_order(s: State):
    return [b for b in BASINS if b != s.basin]


def state_return_excess(world: World, s: State) -> None:
    """te_seabed_state_return_excess: licences above the state's levels go back
    to its owner's shares, distant ones first (basin order), then local."""
    excess = s.records() - s.levels
    if excess <= 0:
        return
    owner = world.countries[s.owner]
    for b in _distant_order(s) + [s.basin]:
        k = min(excess, s.lic[b])
        s.lic[b] -= k
        owner.unbuilt[b] += k
        excess -= k
        if excess == 0:
            return


def _argmax_unbuilt(c: Country):
    """te_seabed_take_most (with te_seabed_unbuilt_max): the basin with the most unbuilt share,
    the first in basin order on a tie; None when all are 0."""
    best = None
    for b in BASINS:
        if c.unbuilt[b] > 0 and (best is None or c.unbuilt[b] > c.unbuilt[best]):
            best = b
    return best


def state_record_new(world: World, s: State, payer) -> int:
    """te_seabed_state_record_new: each level without a record takes a licence
    from the payer's unbuilt share, the state's own basin first, then the
    basin with the most. Levels the payer can't cover (no payer, or no share
    left) are recorded in the state's own basin against no share
    (grandfathered, § 2.4 "What can still go over"). Returns that count."""
    n = s.levels - s.records()
    if n <= 0:
        return 0
    c = world.countries[payer] if payer is not None and world.alive(payer) else None
    if c is not None:
        k = min(n, c.unbuilt[s.basin])
        c.unbuilt[s.basin] -= k
        s.lic[s.basin] += k
        n -= k
        while n > 0:
            b = _argmax_unbuilt(c)
            if b is None:
                break
            k = min(n, c.unbuilt[b])
            c.unbuilt[b] -= k
            s.lic[b] += k
            n -= k
    if n > 0:
        s.lic[s.basin] += n
        world.no_share[s.basin] += n
    return n


def state_swap_local(world: World, s: State) -> None:
    """te_seabed_state_swap_local: distant licences swap for local ones while
    the owner has local share to spare. Basin totals don't move: the local
    basin turns unbuilt into a record, the distant one a record into unbuilt."""
    owner = world.countries[s.owner]
    k = min(s.distant(), owner.unbuilt[s.basin])
    for b in _distant_order(s):
        if k == 0:
            return
        m = min(k, s.lic[b])
        s.lic[b] -= m
        s.lic[s.basin] += m
        owner.unbuilt[s.basin] -= m
        owner.unbuilt[b] += m
        k -= m


def record_country(world: World, cid) -> None:
    """te_seabed_record_country (monthly country pulse, and the yearly pass's
    first step): returns first over every coastal state, then new levels and
    swaps, then the holder stamp on every coastal state."""
    states = [s for s in world.owned(cid) if s.coastal]
    for s in states:
        state_return_excess(world, s)
    for s in states:
        state_record_new(world, s, cid)
        state_swap_local(world, s)
    for s in states:
        s.holder = cid


def on_state_owner_change(world: World, s: State, new_owner) -> None:
    """te_seabed_on_state_owner_change (on_state_owner_change, ROOT = the state
    under its new owner): unrecorded levels are recorded against the stamped
    holder's shares (none if it no longer exists), then the records stay on the
    state and the new owner holds them; its own shares are untouched."""
    if s.coastal:
        state_record_new(world, s, s.holder)
    s.owner = new_owner
    s.holder = new_owner


# ---------------------------------------------------------------------------
# The yearly pass (te_seabed_yearly_pass)
# ---------------------------------------------------------------------------

def is_claimant(world: World, cid) -> bool:
    """te_seabed_is_claimant: Abyssal Plain Mining and a coastal state."""
    c = world.countries[cid]
    return c.alive and c.tech and any(s.coastal for s in world.owned(cid))


def compute_weights(world: World, cid) -> dict:
    """te_seabed_compute_weights (§ 2.3). Home basin: (2 × incorporated coastal
    states + port levels + navy × its share of coastal states) × policy factor;
    distant: 0.05 × navy × policy factor. Unilateral Licensing or the Scramble
    doubles the navy. +5 Southern with an Antarctic station; Southern 0 for a
    country the Antarctic Treaty bars."""
    c = world.countries[cid]
    v = world.v
    home = [s for s in world.owned(cid) if s.coastal and s.incorporated]
    total = len(home)
    navy = c.navy * (ASSERTIVE_NAVY_MULT if (c.policy == UNILATERAL or world.regime == SCRAMBLE) else 1)
    factor = POLICY_FACTOR[c.policy]
    w = {}
    for b in BASINS:
        n = sum(1 for s in home if s.basin == b)
        if n > 0:
            ports = sum(s.ports for s in home if s.basin == b)
            raw = COAST_WEIGHT * n + ports + v(v(navy * n) / total)
        else:
            raw = v(DISTANT_NAVY_SHARE * navy)
        w[b] = v(raw * factor)
    if c.station:
        w["southern"] += STATION_WEIGHT
    if c.barred:
        w["southern"] = 0
    return w


def share_basin(world: World, b: str, part: list) -> dict:
    """te_seabed_share_basin (§ 2.4 step 2, § 3.2): water-fill pool b among the
    participants `part` (claimants and holders), held licences as each one's
    built levels. Returns {cid: entitlement}."""
    v = world.v
    pool = POOLS[b]
    countries = world.countries
    h = {cid: countries[cid].held[b] for cid in part}
    w = {cid: countries[cid].weight[b] for cid in part}
    elig = {cid: world.regime == REGULATED and countries[cid].eligible for cid in part}
    rem_res = pool // 2 if world.regime == REGULATED else 0          # te_seabed_rem_res_<b>
    rem_open = pool - rem_res                                        # te_seabed_rem_open_<b>
    active = set(part)                                               # te_seabed_act_<b>
    frozen_h = 0

    def tentative(cid):
        wr = sum(w[i] for i in active if elig[i])                    # te_seabed_wsum_res_<b>
        wa = sum(w[i] for i in active)                               # te_seabed_wsum_all_<b>
        er = v(v(rem_res * w[cid]) / wr) if elig[cid] and wr > 0 else 0.0
        eo = v(v(rem_open * w[cid]) / wa) if wa > 0 else 0.0
        return er, er + eo

    passes = 0
    while True:
        passes += 1
        tent = {cid: tentative(cid) for cid in active}
        newly = [cid for cid in sorted(active) if h[cid] >= tent[cid][1]]
        if not newly:
            break
        for cid in newly:
            er, e = tent[cid]
            dr = v(v(h[cid] * er) / e) if e > 0 else 0.0
            rem_res = v(rem_res - dr)
            rem_open = v(rem_open - (h[cid] - dr))
            frozen_h += h[cid]
            active.discard(cid)
        if rem_res < 0:
            rem_open = v(rem_open + rem_res)
            rem_res = 0.0
        if rem_open < 0:
            rem_res = max(0.0, v(rem_res + rem_open))
            rem_open = 0.0

    world.iterations[b] = passes
    ent = {cid: h[cid] for cid in part if cid not in active}
    total = max(0, pool - frozen_h)                                  # te_seabed_left_<b> before the floors
    frac = {}
    for cid in active:
        e = tentative(cid)[1]
        ent[cid] = math.floor(e)
        frac[cid] = e - ent[cid]
    left = total - sum(ent[cid] for cid in active)
    # Largest remainder; the engine's ordered_country breaks ties its own way,
    # the model by country id.
    order = sorted(active, key=lambda cid: (-frac[cid], cid))
    i = 0
    while left > 0 and i < len(order):
        ent[order[i]] += 1
        left -= 1
        i += 1
    # Truncation can leave the floors one over the total: take it back from
    # the smallest remainders that stay at or above their holdings.
    for cid in reversed(order):
        if left >= 0:
            break
        if ent[cid] > h[cid]:
            ent[cid] -= 1
            left += 1
    return ent


def yearly_pass(world: World) -> None:
    """te_seabed_yearly_pass: (1) state basins (the generator's table, fixed in
    the model); (2) te_seabed_un_update_regime (the caller sets world.regime);
    (3) every participant records; (4) held; (5) weights; (6) sharing;
    (7) unbuilt = entitlement - held, and every country that takes no part
    loses any stale share."""
    holders = {s.owner for s in world.states.values() if s.records() > 0 or s.levels > 0}
    part = sorted(cid for cid in world.countries
                  if world.alive(cid) and (is_claimant(world, cid) or cid in holders))
    for cid in part:
        record_country(world, cid)
    for cid in part:
        c = world.countries[cid]
        for b in BASINS:
            c.held[b] = sum(s.lic[b] for s in world.owned(cid))
        c.weight = compute_weights(world, cid) if is_claimant(world, cid) else dict.fromkeys(BASINS, 0.0)
    for b in BASINS:
        ent = share_basin(world, b, [cid for cid in part
                                     if world.countries[cid].weight[b] > 0 or world.countries[cid].held[b] > 0])
        for cid in part:
            c = world.countries[cid]
            c.ent[b] = ent.get(cid, 0)
            c.unbuilt[b] = c.ent[b] - c.held[b]
    for cid, c in world.countries.items():
        if cid not in part:
            c.unbuilt = dict.fromkeys(BASINS, 0)
            c.held = dict.fromkeys(BASINS, 0)
            c.ent = dict.fromkeys(BASINS, 0)


# ---------------------------------------------------------------------------
# Random worlds
# ---------------------------------------------------------------------------

def random_world(rng: random.Random, *, n_countries=8, n_states=48, regime=OPEN,
                 old_save_levels=0, fixed=False) -> World:
    countries = {}
    for cid in range(n_countries):
        countries[cid] = Country(
            cid,
            tech=rng.random() < 0.8,
            policy=rng.choice((SURVEY, SPONSOR, SPONSOR, UNILATERAL)),
            navy=rng.choice((0, 5, 20, 60, 150, 300)),
            eligible=rng.random() < 0.4,
            barred=rng.random() < 0.2,
            station=rng.random() < 0.2,
        )
    states = {}
    for sid in range(n_states):
        basin = rng.choice(BASINS + BASINS[:3] + (None,))           # more Pacific/Atlantic/Indian coast
        states[sid] = State(sid, basin, owner=rng.randrange(n_countries),
                            incorporated=rng.random() < 0.85, ports=rng.choice((0, 0, 1, 3, 8)))
        if old_save_levels and basin is not None and rng.random() < 0.5:
            states[sid].levels = rng.randrange(old_save_levels)
    return World(countries, states, regime=regime, fixed=fixed)


def step_month(world: World, rng: random.Random, *, conquest=0.08, demolish=0.05,
               annex=0.004, split=0.01) -> None:
    """One month: building (each country fills some of its room), demolition,
    a conquest landing between building and recording, the odd annexation and
    split, then each country's monthly recording in random order."""
    alive = [cid for cid in world.countries if world.alive(cid)]
    for cid in alive:
        if not world.countries[cid].tech:
            continue
        coastal = [s for s in world.owned(cid) if s.coastal]
        free = room(world, cid)
        for _ in range(rng.randrange(4)):
            if coastal and free > 0:          # the gate: room > 0 (can_build)
                rng.choice(coastal).levels += 1
                free -= 1
    for s in list(world.states.values()):
        if s.levels > 0 and rng.random() < demolish:
            s.levels -= rng.randint(1, s.levels)
    for s in list(world.states.values()):
        if rng.random() < conquest:
            others = [cid for cid in alive if cid != s.owner]
            if others:
                on_state_owner_change(world, s, rng.choice(others))
    if rng.random() < annex and len(alive) > 2:
        loser, winner = rng.sample(alive, 2)
        # Whether the loser still exists when its last states' hooks fire is
        # unread, so the model takes both orders.
        dies_first = rng.random() < 0.5
        if dies_first:
            world.countries[loser].alive = False
        for s in world.owned(loser):
            on_state_owner_change(world, s, winner)
        world.countries[loser].alive = False
    if rng.random() < split:
        coastal = [s for s in world.states.values() if s.coastal and s.levels > 0]
        if coastal:
            parent = rng.choice(coastal)
            new_id = max(world.states) + 1
            # a split makes a new state scope with no variables; it brings
            # some levels with it (the records stay with the parent and come
            # back to its owner at the next recording)
            moved = rng.randint(0, parent.levels)
            parent.levels -= moved
            world.states[new_id] = State(new_id, parent.basin, rng.choice(alive), levels=moved)
    order = list(alive)
    rng.shuffle(order)
    for cid in order:
        if world.alive(cid):
            record_country(world, cid)
