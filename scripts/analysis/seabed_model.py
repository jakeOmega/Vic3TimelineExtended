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
  te_seabed_policy (1 Survey, 2 Sponsor, 3 Unilateral), te_seabed_floor_<basin>
  (the share a sharing may not go below, fixed at the year's first sharing),
  te_seabed_relinq_<basin> (1 = relinquished: weight 0 there until Claim Again),
  te_seabed_lease_src_<basin> (the lessor of its lease there, a country) with
  te_seabed_lease_n_<basin>, _built_<basin> and _unused_<basin>, and
  te_seabed_sh_<basin> (its holdings as the sharing counts them),
  te_seabed_subj_unused_<basin> (claims its subjects passed it, unused) and, on
  a subject, te_seabed_pass_built_<basin> / te_seabed_pass_unused_<basin> (the
  licences its overlord built on its passed claims / those still unused).
- Global: te_seabed_regime (1 Open, 2 Regulated, 3 Scramble).

COUNTRIES WITHOUT THE TECHNOLOGY WAIT FOR THEIR SHARE (the owner, 2026-10-27).
Claim weight is relative, so a sharing among claimants alone handed the first
country with Abyssal Plain Mining every pool in full, distant basins
included, and whatever it queued before a rival caught up was its licences
for good. So every sharing weighs every coastal country. One without the
technology weighs at LATENT_FACTOR (te_seabed_latent_factor) in place of its
policy factor, and its entitlement above its holdings waits for it
(te_seabed_wait_<basin>): it is no claim, so no level, lease or pact can use
it, and the country's claims stay 0 until it researches the technology, when
the next sharing gives it claims by weight. A coastal country with no other
part in the sharing (no technology, no licences) only waits
(te_seabed_waits): it is weighed and shared, records nothing and holds no
claims. A
participant without the technology (a holder) is weighed the same way and
keeps no claims either. The first mover's head start is now bounded: its
share is what its weight wins against everyone's, at most 1 / LATENT_FACTOR
times its share once all have the technology on the same policy.

THE HOLDING FEE (seabed claims spec § 2.1). At the year's first sharing every
coastal state keeps its count of licences on unbuilt levels, and the one
before (te_seabed_unb_snap1, te_seabed_unb_snap2; te_seabed_take_snapshots).
A state's fee base is the smallest of the count now and the two snapshots, so
a level pays only once it was already unbuilt at the year's first sharing
before last; te_seabed_fee_base sums it over a country's coastal states. The
snapshots are state variables, so they pass with the state, and a state
without them (an old save, a split) pays nothing until it has two.

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

A LEVEL THE OWNER QUEUED PAST ITS ROOM STAYS UNRECORDED (review H1). The gate
has the Solar Power Receiver's second branch: a state with a level under
construction passes at room 0, so construction under way is not halted by its
own queued level. That branch can't tell re-checking a queued level from
queueing one more, so at room 0 it lets one extra level in. Recorded against
no share, such a level would leave room at 0 and the branch open, and the
basin would grow by a level a month for as long as a construction ran (the
review's 124 Arctic records against a pool of 100 in 24 months). So the
shortfall of a recording by the state's own stamped owner is left unrecorded
("pending"): room stays below 0, both branches shut, and the level is recorded
when a share pays for it. Only the three cases of § 2.4 are recorded against no
share: an old save's first recording or a split's new state (no stamp), and a
holder gone by the time its state changes hands (annexed whole). A holder that
exists but can't pay leaves the level pending with the new owner.

SPONSOR CONTRACTORS' FLOORS (seabed claims spec § 2.2). At the year's first
sharing (the one that finds te_seabed_pass_year below the current year:
January, or the first mid-year sharing of a year with no January pass),
te_seabed_set_floors stores on each claimant on Sponsor Contractors, outside a
Scramble, a floor per basin: its holdings plus three quarters of its claims
going into the sharing, rounded down (its Southern floor is its holdings where
the Antarctic Treaty bars it), and beside it the protected claims alone
(te_seabed_fprot_<basin>). Every sharing in the year then freezes a country at
max(held, min(floor, held + protected claims)) instead of held
(te_seabed_fit_floors): building on claims mid-year keeps January's floor, and a
licence lost mid-year (conquest, demolition) doesn't come back as a protected
claim (review I3). A mid-year sharing honours the stored figures without
recomputing them, so protection never compounds within a year, and treats it as 0 for a country no longer on Sponsor or no
longer a claimant, or in a Scramble. Where the frozen amounts exceed what the
basin can share (its pool, or its holdings if more), every protected part is
scaled down by one factor, rounding down, and holdings are never touched. A
floor may spill into a Regulated pool's reserved half, as a frozen holding does
(the convention's pioneer investors); it fades by a quarter a year, so the half
refills.

LEASES (seabed claims spec § 4). A Lease <Basin> Seabed Claims treaty article
(common/treaty_articles/122_seabed_lease.txt) leases N of the lessor's claims
in one basin to the lessee; N is the lease's total, the licences built on it
plus its unused claims. At entry into force (te_seabed_lease_start) up to N of
the lessor's own claims move at once. Leased claims are part of the lessee's
claims (unbuilt), kept apart by its counters, and a level it records takes
its own claims first (te_seabed_lease_consume, at the end of
te_seabed_record_country). A lease stands at a sharing while its article is in
force and both sides are claimants (in the Southern Ocean, neither barred by
the Antarctic Treaty). For the sharing, a standing lease's licences count as
the lessor's holdings, not the lessee's (te_seabed_lease_shift_held, writing
te_seabed_sh_<basin>), so the lessee's own share is untouched and the lessor's
share pays for them. The sharing re-divides every claim, leased ones
included; then te_seabed_settle_leases tops each standing lease back up to N
less its licences, from the lessor's own claims, as far as they go. Only own
claims can be leased, and no floor protects leased claims: a lessee's floor,
and its lessor's, count only own claims.

AN ENDED LEASE GOES ON CHARGING ITS LESSOR (review C2; the owner's default
that switching off and on shouldn't pay). When the article ends, its unused
claims return through the next sharing, but the licences built on it go on
counting as the lessor's holdings (te_seabed_lease_past_<basin>) for as long
as both countries take part in the sharing: they were the lessor's claims.
Were they the lessee's own from then on, the lessee would freeze above its
weight and a third party would pay, at every end and re-signing. The record
clears only when one side stops taking part (gone, or no coast and no
licences). While it stands the lessee can lease that basin's claims again
from the same lessor only (te_seabed_can_lease).

SUBJECTS (seabed claims spec § 5.2). Administer Seabed Claims
(common/diplomatic_actions/te_seabed_administer_claims.txt), an overlord's
pact with a direct subject, is a lease with no total that keeps the same two
counters, on the subject. At entry and after every sharing
(te_seabed_pass_subject_claims) the subject's own claims in every basin pass
to the overlord, which records them after its own claims and before leased
ones. At the sharing the licences the overlord built on them count as the
subject's holdings, after its lease's, so the subject's weight pays for them
once: without that the pair would take a third party's share year by year.
The subject's counters name the overlord they are charged to
(te_seabed_pass_to), and go on charging it after the pact ends, for as long
as both take part, as an ended lease does; only a pact with another overlord
starts them afresh. Ended, the unused passed claims return through the next
sharing.

UNINCORPORATED COAST (seabed claims spec § 5.1) counts at half
(te_seabed_uninc_coast) in the coast term and the navy's spread; its ports
count in full, and a basin with only unincorporated coast is home.

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
A reserved half that no active country is eligible for joins the open half
(review L1), so each pool is always fully shared; an eligible party without
the technology is active, so the reserved half waits with it.
"""

from __future__ import annotations

import copy
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
LATENT_FACTOR = 0.25                 # te_seabed_latent_factor: a coastal country without the technology, in place of its policy factor
COAST_WEIGHT = 2
DISTANT_NAVY_SHARE = 0.05
STATION_WEIGHT = 5
ASSERTIVE_NAVY_MULT = 2
FLOOR_KEEP = 0.75                    # te_seabed_floor_keep: Sponsor keeps at least this much of its claims
FEE_RATE = 0.02                      # te_seabed_fee_rate: the holding fee, of a level's base output value a week
READOUT_FULL_BELOW = 0.01            # te_seabed_readout: a half with less than this left for us reads "full"
UNINCORPORATED_COAST = 0.5           # te_seabed_uninc_coast: an unincorporated coastal state's coast weight


def fx(x: float) -> float:
    """The engine keeps values in units of 1e-5, truncated toward zero."""
    return math.trunc(x * 100000) / 100000


@dataclass
class Country:
    cid: int
    alive: bool = True
    tech: bool = True                # has_technology_researched = abyssal_plain_mining
    policy: int = SURVEY
    navy: float = 0.0                # naval power projection ÷ te_seabed_power_projection_scale
    eligible: bool = False           # te_seabed_reserved_half_eligible (hook)
    barred: bool = False             # te_seabed_southern_barred (hook)
    station: bool = False            # has_variable = te_antarctic_station
    unbuilt: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))
    held: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))
    ent: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))
    wait: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))      # te_seabed_wait_<basin>: no technology, share above holdings
    weight: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0.0))
    floor: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))   # te_seabed_floor_<basin>; 0 = none
    relinquished: dict = field(default_factory=lambda: dict.fromkeys(BASINS, False))   # te_seabed_relinq_<basin>
    floor_prot: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))  # te_seabed_fprot_<basin>: the claims part
    # Its treaty lease per basin, as the lessee (te_seabed_lease_src_<basin> etc.)
    lease_src: dict = field(default_factory=lambda: dict.fromkeys(BASINS, None))    # the lessor
    lease_n: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))         # its total
    lease_built: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))     # licences built on it
    lease_unused: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))    # its unused claims, in unbuilt
    lease_past: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))      # built on ended leases from lease_src
    sh: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))              # te_seabed_sh_<basin>
    overlord: int | None = None      # its direct overlord (is_direct_subject_of)
    subj_unused: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))     # passed it by subjects, in unbuilt
    pass_built: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))      # as a subject: built on by its overlord
    pass_unused: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))     # as a subject: at its overlord, unused
    pass_to: int | None = None       # te_seabed_pass_to: the overlord its two counters are charged to


@dataclass
class State:
    sid: int
    basin: str | None                # te_seabed_basin; None = landlocked
    owner: int
    incorporated: bool = True
    ports: int = 0                   # building_port levels
    levels: int = 0                  # Deep-Sea Mine level_after_queued_constructions
    queued: int = 0                  # of which under construction (is_under_construction)
    lic: dict = field(default_factory=lambda: dict.fromkeys(BASINS, 0))
    holder: int | None = None        # te_seabed_holder
    snap1: int = 0                   # te_seabed_unb_snap1: licences on unbuilt levels, the year's first sharing
    snap2: int = 0                   # te_seabed_unb_snap2: the same, a year before

    @property
    def coastal(self) -> bool:
        return self.basin is not None

    @property
    def built(self) -> int:          # the Deep-Sea Mine's level
        return self.levels - self.queued

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
    # The review's control: True restores the pre-fix rule (an owner's own
    # shortfall recorded against no share), which leaks through the gate's
    # second branch.
    shortfall_no_share: bool = False
    # te_seabed_cap_stamped_noshare: levels a monthly recording put against
    # no share in a state that carried a stamp. Legitimately always 0 (a
    # stamped owner's shortfall waits; another country's stamp means the
    # owner-change hook didn't run), so seabed_cap logs BROKEN above 0: the
    # signature of the H1 leak, which the no-share counter otherwise absorbs.
    stamped_no_share: int = 0
    iterations: dict = field(default_factory=dict)   # water-filling passes, last sharing, per basin
    # The last sharing's final round, per basin, for the readout: rem_res,
    # rem_open, wsum_res, wsum_all (the te_seabed_*_<basin> globals), the
    # active set, frozen_at (cid -> what it was frozen at), frozen_res (the
    # reserved-half part of it), h (every participant's max(held, floor)) and
    # the participants.
    final: dict = field(default_factory=dict)
    leases_ended: set = field(default_factory=set)   # (lessee, basin): its article ended; settled at the next sharing
    administer: set = field(default_factory=set)     # (overlord, subject): the te_seabed_administer_claims pact

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


def pending(world: World, cid) -> int:
    """Levels in the country's coastal states with no licence (te_seabed_unrecorded_total
    after its recording): what it queued past its room."""
    return sum(unrecorded(s) for s in world.owned(cid) if s.coastal)


def gate_open(r: int, s: State) -> bool:
    """te_seabed_gate's two branches for a state, given its owner's room r:
    room > 0, or room >= 0 in a state with a level under construction."""
    return r > 0 or (s.queued > 0 and r >= 0)


def can_build(world: World, cid, s: State) -> bool:
    """building_ocean_mine possible, with the rule on (te_seabed_gate)."""
    c = world.countries[cid]
    return s.coastal and c.tech and s.owner == cid and gate_open(room(world, cid), s)


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


def state_record_new(world: World, s: State, payer, *, pend: bool = False, monthly: bool = False) -> int:
    """te_seabed_state_record_new: each level without a record takes a licence
    from the payer's unbuilt share, the state's own basin first, then the
    basin with the most. Levels the payer can't cover stay unrecorded when
    `pend` (local te_sb_pend: the payer is the state's own stamped owner, or a
    holder that exists), else are recorded in the state's own basin against no
    share (grandfathered, § 2.4 "What can still go over"). Returns the count
    not covered."""
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
    if n > 0 and not pend:
        s.lic[s.basin] += n
        world.no_share[s.basin] += n
        if monthly and s.holder is not None:
            world.stamped_no_share += n
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
        own = s.holder == cid and not world.shortfall_no_share
        state_record_new(world, s, cid, pend=own, monthly=True)
        state_swap_local(world, s)
    for s in states:
        s.holder = cid
    lease_consume(world, cid)


def on_state_owner_change(world: World, s: State, new_owner) -> None:
    """te_seabed_on_state_owner_change (on_state_owner_change, ROOT = the state
    under its new owner): unrecorded levels are recorded against the stamped
    holder's shares; against no share if the state has no stamp or the holder
    no longer exists, and left pending (for the new owner's share) if the
    holder exists but can't pay. Then the records stay on the state and the new
    owner holds them; its own shares are untouched."""
    if s.coastal:
        payer = s.holder if s.holder is not None and world.alive(s.holder) else None
        state_record_new(world, s, payer, pend=payer is not None and not world.shortfall_no_share)
    s.owner = new_owner
    s.holder = new_owner


# ---------------------------------------------------------------------------
# The holding fee's base (seabed claims spec § 2.1) and queued licences
# ---------------------------------------------------------------------------

def unbuilt_licences(s: State) -> int:
    """te_seabed_state_unbuilt_lic: licences on the state's queued levels.
    Built levels are licensed first (a level is recorded when queued), so a
    shortfall falls on queued levels, and licences above the levels (a
    demolition not yet recorded) are on none."""
    return max(0, min(s.queued, s.records() - s.built))


def take_snapshots(world: World) -> None:
    """te_seabed_take_snapshots (the year's first sharing, after recording):
    every coastal state keeps its last two counts of licences on unbuilt
    levels. A split's new state starts at 0 and 0."""
    for s in world.states.values():
        if s.coastal:
            s.snap2 = s.snap1
            s.snap1 = unbuilt_licences(s)


def fee_base_state(s: State) -> int:
    """te_seabed_state_fee_base: licences on levels that were already unbuilt
    at the last two first-sharings of a year, assuming levels finish in the
    order they were queued: a grace of 12 to 24 months."""
    return max(0, min(unbuilt_licences(s), s.snap1, s.snap2))


def fee_base(world: World, cid) -> int:
    """te_seabed_fee_base: fee_base_state over the country's coastal states."""
    return sum(fee_base_state(s) for s in world.owned(cid) if s.coastal)


def queued_by_basin(world: World, cid) -> dict:
    """te_seabed_queued_<basin>, written by the monthly recording: the
    licences the country's queued levels hold, by basin. A state's queued
    licences count against its distant licences first (basin order), then
    its own basin's: a level takes a distant licence only once the local
    share is gone, so distant ones are normally the newest."""
    q = dict.fromkeys(BASINS, 0)
    for s in world.owned(cid):
        if not s.coastal:
            continue
        n = unbuilt_licences(s)
        for b in _distant_order(s) + [s.basin]:
            k = min(n, s.lic[b])
            q[b] += k
            n -= k
            if n == 0:
                break
    return q


# ---------------------------------------------------------------------------
# The yearly pass (te_seabed_yearly_pass)
# ---------------------------------------------------------------------------

def is_claimant(world: World, cid) -> bool:
    """te_seabed_is_claimant: Abyssal Plain Mining and a coastal state."""
    c = world.countries[cid]
    return c.alive and c.tech and any(s.coastal for s in world.owned(cid))


def takes_part(world: World, cid) -> bool:
    """te_seabed_takes_part (the sharing's te_seabed_part): alive, and a
    claimant or a holder of licences or levels."""
    return world.alive(cid) and (is_claimant(world, cid)
                                 or any(s.records() > 0 or s.levels > 0 for s in world.owned(cid)))


def waits(world: World, cid) -> bool:
    """te_seabed_waits: a coastal country with no other part in the sharing
    (no Abyssal Plain Mining, no licences). It is weighed and its share waits
    for it, but it records nothing and holds no claims."""
    return (world.alive(cid) and not takes_part(world, cid)
            and any(s.coastal for s in world.owned(cid)))


def _coast(s: State) -> float:
    """te_seabed_weight_tally's count for a coastal state: 1, or
    UNINCORPORATED_COAST unincorporated."""
    return 1 if s.incorporated else UNINCORPORATED_COAST


def compute_weights(world: World, cid) -> dict:
    """te_seabed_compute_weights (§ 2.3, spec § 5.1). Home basin: (2 × coastal
    states + port levels + navy × its share of coastal states) × policy factor,
    unincorporated states counting UNINCORPORATED_COAST in both counts;
    distant: 0.05 × navy × policy factor, LATENT_FACTOR in its place for a
    country without the technology (te_seabed_claim_factor). Unilateral
    Licensing or the Scramble doubles the navy. +5 Southern with an Antarctic
    station; Southern 0 for a country the Antarctic Treaty bars."""
    c = world.countries[cid]
    v = world.v
    home = [s for s in world.owned(cid) if s.coastal]
    total = sum(_coast(s) for s in home)
    navy = c.navy * (ASSERTIVE_NAVY_MULT if (c.policy == UNILATERAL or world.regime == SCRAMBLE) else 1)
    factor = POLICY_FACTOR[c.policy] if c.tech else LATENT_FACTOR
    w = {}
    for b in BASINS:
        n = sum(_coast(s) for s in home if s.basin == b)
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
    for b in BASINS:
        if c.relinquished[b]:
            w[b] = 0
    return w


def relinquish(world: World, cid, b: str) -> None:
    """te_seabed_relinquish (the basin's Relinquish button, seabed claims spec
    § 2.5): the country's claims in basin b go at once, its floor there with
    them, and its weight there is 0 at every sharing until it claims again.
    Licences on its levels stay. It never sets te_seabed_reshare: the freed
    claims wait for the next sharing something else brings about. It records
    the country first, so levels queued since the monthly recording take their
    licences before the claims go."""
    record_country(world, cid)       # levels queued since the last recording keep their licences (review I1)
    c = world.countries[cid]
    c.unbuilt[b] = 0
    c.lease_unused[b] = 0            # leased and subject-passed claims go too, without counting as built
    c.subj_unused[b] = 0
    for sub in world.countries.values():
        if sub.pass_to == cid:
            sub.pass_unused[b] = 0
    c.floor[b] = 0
    c.floor_prot[b] = 0
    c.relinquished[b] = True


def claim_again(world: World, cid, b: str) -> None:
    """te_seabed_claim_again: the country claims basin b again from the next
    sharing; nothing comes back before it."""
    world.countries[cid].relinquished[b] = False


def share_basin(world: World, b: str, part: list) -> dict:
    """te_seabed_share_basin (§ 2.4 step 2, § 3.2): water-fill pool b among the
    participants `part` (claimants and holders), held licences as each one's
    built levels, raised to its floor (fit_floors). Returns {cid: entitlement}."""
    v = world.v
    pool = POOLS[b]
    countries = world.countries
    h = fit_floors(world, b, part)
    w = {cid: countries[cid].weight[b] for cid in part}
    elig = {cid: world.regime == REGULATED and countries[cid].eligible for cid in part}
    rem_res = pool // 2 if world.regime == REGULATED else 0          # te_seabed_rem_res_<b>
    rem_open = pool - rem_res                                        # te_seabed_rem_open_<b>
    active = set(part)                                               # te_seabed_act_<b>
    frozen_h = 0
    frozen_res = {}                                                  # te_seabed_dr_<b>: its reserved-half debit

    def fold_unclaimed():
        """te_seabed_share_fold_unclaimed: a reserved half no active country
        is eligible for joins the open half (review L1); a waiting party is
        active."""
        nonlocal rem_res, rem_open
        if rem_res > 0 and not any(elig[i] and w[i] > 0 for i in active):
            rem_open = v(rem_open + rem_res)
            rem_res = 0.0

    def tentative(cid):
        wr = sum(w[i] for i in active if elig[i])                    # te_seabed_wsum_res_<b>
        wa = sum(w[i] for i in active)                               # te_seabed_wsum_all_<b>
        er = v(v(rem_res * w[cid]) / wr) if elig[cid] and wr > 0 else 0.0
        eo = v(v(rem_open * w[cid]) / wa) if wa > 0 else 0.0
        return er, er + eo

    passes = 0
    while True:
        passes += 1
        fold_unclaimed()
        tent = {cid: tentative(cid) for cid in active}
        newly = [cid for cid in sorted(active) if h[cid] >= tent[cid][1]]
        if not newly:
            break
        for cid in newly:
            er, e = tent[cid]
            dr = v(v(h[cid] * er) / e) if e > 0 else 0.0
            frozen_res[cid] = dr
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
    fold_unclaimed()
    world.final[b] = {
        "rem_res": rem_res, "rem_open": rem_open,
        "wsum_res": sum(w[i] for i in active if elig[i]), "wsum_all": sum(w[i] for i in active),
        "active": set(active), "frozen_at": {cid: h[cid] for cid in part if cid not in active},
        "frozen_res": dict(frozen_res), "h": dict(h), "part": list(part),
    }
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


def need_weight(world: World, b: str, cid, step: int = 1) -> float | None:
    """te_seabed_readout (seabed claims spec § 3.5): about how much more claim
    weight the country needs in basin b for one more licence, from the last
    sharing's final round. With R licences left to the active set and W its
    weight, a country of weight w and tentative share e = R·w/W needs, for a
    target t, d = t - e more: Δw = d·W / (R - e - d), which for a country
    sharing one half is (t·W - R·w) / (R - t). An active country's target is
    its entitlement + 1; a frozen one's what it was frozen at + 1, with its
    holdings put back in the halves they came off and its weight back in the
    active set. An eligible party under the Regulated regime takes the smaller
    Δw of its two halves (both rise, so the true need is a little less). None
    where no half has a licence left for it ("full"), or the country has no
    weight here.

    It is a sufficient figure, not a lottery: the sharing's largest-remainder
    rounding may hand the licence over sooner, so the exact need lies between
    this form for the entitlement itself (step=0) and for one more (Open
    regime; under the Regulated regime the halves can make it overstate by
    more). "Full" means no licence for certain; the rounding may still hand
    the last one over, at a high weight. A half with less than
    READOUT_FULL_BELOW of a licence left for us reads "full", which the
    engine's fixed point needs too. It assumes
    no rival is pushed down to its holdings or floor by our growth, and under
    the Regulated regime that no frozen party is eligible (its holdings come
    off the halves by shares our weight moves); where either fails it can
    understate (test_seabed_allocation's ReadoutTest counts how rarely)."""
    f = world.final.get(b)
    c = world.countries[cid]
    if f is None or cid not in f["part"] or c.weight[b] <= 0:
        return None
    w = c.weight[b]
    elig = world.regime == REGULATED and c.eligible
    r_res, r_open, w_res, w_all = f["rem_res"], f["rem_open"], f["wsum_res"], f["wsum_all"]
    if cid in f["active"]:
        t = c.ent[b] + step
    else:
        fa = f["frozen_at"][cid]
        dr = f["frozen_res"].get(cid, 0.0)
        t = fa + step
        r_res += dr
        r_open += fa - dr
        w_all += w
        if elig:
            w_res += w
    halves = [(r_open, w_all)]
    if elig and r_res > 0 and w_res > 0:
        halves.append((r_res, w_res))
    shares = [R * w / W for R, W in halves]
    d = max(0.0, t - sum(shares))
    best = None
    for (R, W), e in zip(halves, shares):
        if R - e - d > READOUT_FULL_BELOW:       # at 0 the licence is never certain: "full"
            x = d * W / (R - e - d)
            best = x if best is None else min(best, x)
    return best


def need_navy(world: World, cid, b: str) -> int | None:
    """te_seabed_need_navy_<basin>: need_weight in units of navy (Country.navy,
    the scaled power projection; the panel shows it × the scale,
    te_seabed_power_projection_scale, as raw naval power projection). At home
    the navy counts in proportion to the country's coastal states there
    (factor × navy multiplier × n_b ÷ N, unincorporated ones at half); far away at DISTANT_NAVY_SHARE
    (0.05 × factor × navy multiplier). Rounded up; None passes through."""
    x = need_weight(world, b, cid)
    if x is None:
        return None
    c = world.countries[cid]
    factor = POLICY_FACTOR[c.policy] if c.tech else LATENT_FACTOR      # te_seabed_claim_factor
    mult = ASSERTIVE_NAVY_MULT if (c.policy == UNILATERAL or world.regime == SCRAMBLE) else 1
    home = [s for s in world.owned(cid) if s.coastal]
    n = sum(_coast(s) for s in home if s.basin == b)
    per = factor * mult * n / sum(_coast(s) for s in home) if n > 0 else DISTANT_NAVY_SHARE * factor * mult
    return math.ceil(x / per)


def exact_need_weight(world: World, b: str, cid, *, tol: float = 0.01, cap: float = 1e6) -> float | None:
    """Test reference for need_weight: the least extra weight, to within
    `tol`, at which re-running the last sharing of basin b on a copy gives the
    country one licence more; None if no weight up to `cap` does."""
    f = world.final.get(b)
    c = world.countries[cid]
    if f is None or cid not in f["part"] or c.weight[b] <= 0:
        return None
    target = c.ent[b] + 1
    sim = copy.deepcopy(world)
    base = c.weight[b]

    def gets(x):
        sim.countries[cid].weight[b] = base + x
        return share_basin(sim, b, f["part"])[cid] >= target

    hi = 1.0
    while not gets(hi):
        hi *= 2
        if hi > cap:
            return None
    lo = 0.0
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if gets(mid):
            hi = mid
        else:
            lo = mid
    return hi


def floor_in_force(world: World, c: Country, b: str) -> int:
    """The stored floor a sharing honours (te_seabed_fit_floors' read): 0 off
    Sponsor Contractors, in a Scramble, for a country that is no longer a
    claimant, and in the Southern Ocean for a country the Antarctic Treaty
    bars."""
    if c.policy != SPONSOR or world.regime == SCRAMBLE or not is_claimant(world, c.cid):
        return 0
    if b == "southern" and c.barred:
        return 0
    return c.floor[b]


def set_floors(world: World, cid) -> None:
    """te_seabed_set_floors (the year's first sharing, after recording and
    held, before weights): on Sponsor Contractors, outside a Scramble, a
    claimant's floor in each basin is its holdings (sh) plus FLOOR_KEEP of its
    own claims going into the sharing, rounded down; its Southern floor is its
    holdings where the Antarctic Treaty bars it. Otherwise no floor."""
    c = world.countries[cid]
    if c.policy != SPONSOR or world.regime == SCRAMBLE or not is_claimant(world, cid):
        c.floor = dict.fromkeys(BASINS, 0)
        c.floor_prot = dict.fromkeys(BASINS, 0)
        return
    for b in BASINS:
        keep = 0 if (b == "southern" and c.barred) else math.floor(FLOOR_KEEP * own_claims(c, b))
        c.floor[b] = c.sh[b] + keep
        c.floor_prot[b] = keep


def fit_floors(world: World, b: str, part: list) -> dict:
    """te_seabed_fit_floors (te_seabed_fz_<basin>): what each participant is
    frozen at, max(held, min(floor, held + protected claims)), held being its
    holdings as the sharing counts them (sh, after the leases' shift). Where those
    exceed what the basin can share (its pool, or its holdings if more), every
    protected part is scaled down by one factor, rounding down; holdings are
    never touched."""
    countries = world.countries
    held = {cid: countries[cid].sh[b] for cid in part}

    def protected(cid):
        c = countries[cid]
        f = floor_in_force(world, c, b)
        return max(0, min(f, held[cid] + c.floor_prot[b]) - held[cid]) if f > 0 else 0
    prot = {cid: protected(cid) for cid in part}
    room_left = max(POOLS[b], sum(held.values())) - sum(held.values())
    total = sum(prot.values())
    if total > room_left:
        prot = {cid: p * room_left // total for cid, p in prot.items()}
    return {cid: held[cid] + prot[cid] for cid in part}


# ---------------------------------------------------------------------------
# Treaty leases (seabed claims spec § 4)
# ---------------------------------------------------------------------------

def own_claims(c: Country, b: str) -> int:
    """te_seabed_own_claims: the country's claims in basin b less those it
    holds by lease or its subjects passed it; only these can be leased out,
    passed on or protected by a floor."""
    return max(0, c.unbuilt[b] - c.lease_unused[b] - c.subj_unused[b])


def can_lease(world: World, src, dst, b: str) -> bool:
    """te_seabed_can_lease (the article's possible): two different claimants;
    the lessor has own claims in basin b; the lessee has no lease standing
    there, nor a record from another lessor (an ended lease still charging it),
    and has not relinquished it; in the Southern Ocean, neither side barred by
    the Antarctic Treaty."""
    s, d = world.countries[src], world.countries[dst]
    if src == dst or not (is_claimant(world, src) and is_claimant(world, dst)):
        return False
    if b == "southern" and (s.barred or d.barred):
        return False
    return (own_claims(s, b) > 0 and d.lease_n[b] == 0 and d.lease_src[b] in (None, src)
            and not d.relinquished[b])


def start_lease(world: World, src, dst, b: str, n: int) -> None:
    """te_seabed_lease_start (the article's on_entry_into_force): up to n of
    the lessor's own claims in basin b move to the lessee at once. A record of
    an ended lease from the same lessor carries on; one from another lessor
    (only an enforced lease can get past te_seabed_can_lease) is dropped, its
    licences the lessee's own."""
    s, d = world.countries[src], world.countries[dst]
    if d.lease_src[b] not in (None, src):
        _clear_lease(d, b)
    k = min(n, own_claims(s, b))
    s.unbuilt[b] -= k
    d.unbuilt[b] += k
    d.lease_src[b], d.lease_n[b], d.lease_built[b], d.lease_unused[b] = src, n, 0, k


def end_lease(world: World, dst, b: str) -> None:
    """The article ends (broken, renegotiated away, a party gone): nothing
    moves until the next sharing, which finds it no longer in force."""
    world.leases_ended.add((dst, b))


def lease_consume(world: World, cid) -> None:
    """te_seabed_lease_consume (the end of te_seabed_record_country): what the
    recording took from the country's claims comes off its own claims first,
    then off those its subjects passed it (booked in id order on each subject
    whose counters charge it as built on its claims), and only then off its
    leased ones, which become
    licences built on the lease."""
    c = world.countries[cid]
    for b in BASINS:
        left = max(0, c.unbuilt[b])
        new = min(c.lease_unused[b], left)
        c.lease_built[b] += c.lease_unused[b] - new
        c.lease_unused[b] = new
        new_subj = min(c.subj_unused[b], left - new)
        used = c.subj_unused[b] - new_subj
        c.subj_unused[b] = new_subj
        for sub in sorted(world.countries.values(), key=lambda x: x.cid):
            if used == 0:
                break
            if sub.pass_to == cid and sub.pass_unused[b] > 0:
                k = min(used, sub.pass_unused[b])
                sub.pass_unused[b] -= k
                sub.pass_built[b] += k
                used -= k


def lease_stands(world: World, dst, b: str) -> bool:
    """A lease stands at a sharing while its article is in force and both
    sides are claimants; in the Southern Ocean, while neither is barred."""
    d = world.countries[dst]
    src = d.lease_src[b]
    if src is None or d.lease_n[b] == 0 or (dst, b) in world.leases_ended:
        return False
    if not (is_claimant(world, dst) and is_claimant(world, src)):
        return False
    return not (b == "southern" and (d.barred or world.countries[src].barred))


def lease_charged(world: World, dst, b: str) -> bool:
    """A lease's licences, standing or ended, count as its lessor's while both
    countries take part in the sharing."""
    src = world.countries[dst].lease_src[b]
    return src is not None and takes_part(world, dst) and takes_part(world, src)


def pact_charged(world: World, sub) -> bool:
    """A subject's counters charge their overlord while both take part."""
    o = world.countries[sub].pass_to
    return o is not None and takes_part(world, sub) and takes_part(world, o)


def share_held(world: World, cid, b: str) -> int:
    """te_seabed_sh_<basin> (te_seabed_lease_shift_held, after held): the
    holdings the sharing counts. A lease's licences, standing or ended,
    capped at the lessee's holdings, count as its lessor's instead of the
    lessee's, and a pact's as the subject's instead of the overlord's, while
    both sides take part (lease_charged, pact_charged)."""
    c = world.countries[cid]
    sh = c.held[b] - sum(_outflows(world, cid, b).values())
    for d in world.countries.values():
        if d.cid != cid:
            sh += _outflows(world, d.cid, b).get(cid, 0)
    return sh


def _outflows(world: World, cid, b: str) -> dict:
    """The part of a country's holdings in basin b that the sharing counts as
    others': its lease's licences first (built on it and on ended leases from
    the same lessor), then those it built on each subject's passed claims,
    subjects in id order, each capped at what is left of its holdings.
    {country: licences}."""
    c = world.countries[cid]
    left = c.held[b]
    out = {}
    if lease_charged(world, cid, b):
        k = min(c.lease_built[b] + c.lease_past[b], left)
        out[c.lease_src[b]] = k
        left -= k
    for sub in sorted(world.countries.values(), key=lambda x: x.cid):
        if sub.pass_to == cid and pact_charged(world, sub.cid):
            k = min(sub.pass_built[b], left)
            out[sub.cid] = out.get(sub.cid, 0) + k
            left -= k
    return out


def _clear_lease(c: Country, b: str) -> None:
    c.lease_src[b] = None
    c.lease_n[b] = c.lease_built[b] = c.lease_unused[b] = c.lease_past[b] = 0


def settle_leases(world: World) -> None:
    """te_seabed_settle_leases (after the five sharings). A record whose two
    sides no longer both take part is cleared: its licences are the lessee's
    own from now on. One whose lease has ended keeps charging the lessor with
    what was built on it (te_seabed_lease_past_<basin>), and clears once that
    is nothing. A standing one counts at most the lessee's holdings as built
    on it (a demolished level gives the lease its room back) and, unless the
    lessee has relinquished the basin, is topped back up to its total less its
    licences, from the lessor's own claims, as far as they go."""
    for d in sorted(world.countries.values(), key=lambda c: c.cid):
        for b in BASINS:
            if d.lease_src[b] is None:
                continue
            if not lease_charged(world, d.cid, b):
                _clear_lease(d, b)
                continue
            d.lease_built[b] = min(d.lease_built[b], d.held[b])
            d.lease_past[b] = min(d.lease_past[b], d.held[b] - d.lease_built[b])
            if not lease_stands(world, d.cid, b):
                d.lease_past[b] += d.lease_built[b]
                d.lease_n[b] = d.lease_built[b] = d.lease_unused[b] = 0
                if d.lease_past[b] == 0:
                    _clear_lease(d, b)
                continue
            if d.relinquished[b]:
                continue
            s = world.countries[d.lease_src[b]]
            k = max(0, min(d.lease_n[b] - d.lease_built[b] - d.lease_unused[b], own_claims(s, b)))
            s.unbuilt[b] -= k
            d.unbuilt[b] += k
            d.lease_unused[b] += k
    world.leases_ended.clear()


# ---------------------------------------------------------------------------
# Subjects: Administer Seabed Claims (seabed claims spec § 5.2)
# ---------------------------------------------------------------------------

def pact_stands(world: World, o, sub, b: str) -> bool:
    """The pact stands in basin b while the overlord keeps it, the country is
    still its direct subject and both are claimants; in the Southern Ocean,
    while neither is barred by the Antarctic Treaty."""
    s = world.countries[sub]
    if (o, sub) not in world.administer or s.overlord != o:
        return False
    if not (is_claimant(world, o) and is_claimant(world, sub)):
        return False
    return not (b == "southern" and (s.barred or world.countries[o].barred))


def _charge_to(s: Country, o) -> None:
    """te_seabed_pass_to: the subject's counters charge overlord o; a record
    charging another overlord is dropped (its licences are that overlord's
    own)."""
    if s.pass_to not in (None, o):
        s.pass_built = dict.fromkeys(BASINS, 0)
        s.pass_unused = dict.fromkeys(BASINS, 0)
    s.pass_to = o


def pass_claims(world: World, o, sub) -> None:
    """One pact's pass: the subject's own claims in every basin where the pact
    stands go to the overlord, unless the overlord relinquished the basin."""
    s, ov = world.countries[sub], world.countries[o]
    _charge_to(s, o)
    for b in BASINS:
        if ov.relinquished[b] or not pact_stands(world, o, sub, b):
            continue
        k = own_claims(s, b)
        s.unbuilt[b] -= k
        s.pass_unused[b] += k
        ov.unbuilt[b] += k
        ov.subj_unused[b] += k


def start_pact(world: World, o, sub) -> None:
    """te_seabed_administer_claims' start: counters charging another overlord
    are dropped (the licences it built are its own); this overlord's carry on
    (review C2: ending and taking the pact again must not orphan them). The
    subject's claims pass at once."""
    s = world.countries[sub]
    _charge_to(s, o)
    world.administer.add((o, sub))
    pass_claims(world, o, sub)


def end_pact(world: World, o, sub) -> None:
    """The overlord ends the pact, or it breaks: nothing moves until the next
    sharing, which re-divides the passed claims."""
    world.administer.discard((o, sub))


def pass_subject_claims(world: World) -> None:
    """te_seabed_pass_subject_claims (after te_seabed_settle_leases): a
    record whose two sides no longer both take part is cleared (its licences
    are the overlord's own); otherwise at most the overlord's holdings count
    as built on the subject's claims, pact or no pact. Where a pact stands, the
    subject's claims pass again."""
    for s in sorted(world.countries.values(), key=lambda x: x.cid):
        if s.pass_to is None:
            continue
        if not pact_charged(world, s.cid):
            s.pass_built = dict.fromkeys(BASINS, 0)
            s.pass_unused = dict.fromkeys(BASINS, 0)
            s.pass_to = None
            continue
        for b in BASINS:
            s.pass_built[b] = min(s.pass_built[b], world.countries[s.pass_to].held[b])
    for o, sub in sorted(world.administer):
        if world.countries[sub].overlord == o:
            pass_claims(world, o, sub)


def yearly_pass(world: World, *, first_of_year: bool = True) -> None:
    """te_seabed_yearly_pass: (1) state basins (the generator's table, fixed in
    the model); (2) te_seabed_un_update_regime (the caller sets world.regime);
    (3) every participant records, and at the year's first sharing every
    coastal state takes its fee snapshots (te_seabed_take_snapshots); (4) held,
    the leases' shift (te_seabed_lease_shift_held), and at the year's first
    sharing the floors (te_seabed_set_floors); (5) weights; (6) sharing; (7)
    unbuilt = entitlement - sh for a claimant, and for a country without the
    technology its waiting share (entitlement - sh) and no claims; every
    country that takes no part loses any stale share and floor; (8)
    te_seabed_settle_leases, then te_seabed_pass_subject_claims. The coastal
    countries that only wait (te_seabed_waits) are weighed in (5) and shared
    in (6), and nothing else."""
    holders = {s.owner for s in world.states.values() if s.records() > 0 or s.levels > 0}
    part = sorted(cid for cid in world.countries
                  if world.alive(cid) and (is_claimant(world, cid) or cid in holders))
    waiting = sorted(cid for cid in world.countries if cid not in part and waits(world, cid))
    for cid in part:
        record_country(world, cid)
    if first_of_year:
        take_snapshots(world)
    for cid in part:
        c = world.countries[cid]
        for b in BASINS:
            c.held[b] = sum(s.lic[b] for s in world.owned(cid))
    for cid in part:                 # te_seabed_lease_shift_held
        c = world.countries[cid]
        for b in BASINS:
            c.sh[b] = share_held(world, cid, b)
    for cid in part:
        c = world.countries[cid]
        if first_of_year:
            set_floors(world, cid)
        c.weight = compute_weights(world, cid)
    for cid in waiting:              # te_seabed_wait_weights: holds nothing, protected by nothing
        c = world.countries[cid]
        c.held = dict.fromkeys(BASINS, 0)
        c.sh = dict.fromkeys(BASINS, 0)
        c.floor = dict.fromkeys(BASINS, 0)
        c.floor_prot = dict.fromkeys(BASINS, 0)
        c.weight = compute_weights(world, cid)
    for b in BASINS:
        ent = share_basin(world, b, [cid for cid in part + waiting
                                     if world.countries[cid].weight[b] > 0 or world.countries[cid].sh[b] > 0])
        for cid in part + waiting:
            c = world.countries[cid]
            e = ent.get(cid, 0)
            if c.tech:
                c.ent[b] = e
                c.wait[b] = 0
            else:                    # its share waits for the technology: no claims
                c.ent[b] = min(e, c.sh[b])
                c.wait[b] = e - c.ent[b]
            c.unbuilt[b] = c.ent[b] - c.sh[b]
            c.lease_unused[b] = 0    # the sharing re-divides leased and passed claims too
            c.subj_unused[b] = 0
            c.pass_unused[b] = 0
    for cid, c in world.countries.items():
        if cid not in part and cid not in waiting:
            c.wait = dict.fromkeys(BASINS, 0)
            c.weight = dict.fromkeys(BASINS, 0.0)
            c.unbuilt = dict.fromkeys(BASINS, 0)
            c.held = dict.fromkeys(BASINS, 0)
            c.sh = dict.fromkeys(BASINS, 0)
            c.ent = dict.fromkeys(BASINS, 0)
            c.floor = dict.fromkeys(BASINS, 0)
            c.floor_prot = dict.fromkeys(BASINS, 0)
            c.subj_unused = dict.fromkeys(BASINS, 0)
            c.pass_unused = dict.fromkeys(BASINS, 0)
    settle_leases(world)
    pass_subject_claims(world)


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
    world = World(countries, states, regime=regime, fixed=fixed)
    # a fifth of the countries are subjects (no chains), half of them under the pact
    for cid in countries:
        if rng.random() < 0.2 and not any(c.overlord == cid for c in countries.values()):
            lords = [o for o in countries if o != cid and countries[o].overlord is None]
            if lords:
                countries[cid].overlord = rng.choice(lords)
                if rng.random() < 0.5:
                    world.administer.add((countries[cid].overlord, cid))
    return world


def step_month(world: World, rng: random.Random, *, conquest=0.08, demolish=0.05,
               annex=0.004, split=0.01, complete=0.5, cancel=0.02) -> None:
    """One month: building, which queues a level wherever the gate is open
    (both branches, so a builder queues one more in a state already under
    construction at room 0, as the AI and private investment do), construction
    finishing or being cancelled, demolition of finished levels, a conquest
    landing between building and recording (its construction cancelled before
    the hook, after it, or not at all), the odd annexation and split, then each
    country's monthly recording in random order."""
    alive = [cid for cid in world.countries if world.alive(cid)]
    for cid in alive:
        if not world.countries[cid].tech:
            continue
        coastal = [s for s in world.owned(cid) if s.coastal]
        free = room(world, cid)
        for _ in range(rng.randrange(4)):
            options = [s for s in coastal if gate_open(free, s)]
            if not options:
                break
            s = rng.choice(options)
            s.levels += 1
            s.queued += 1
            free -= 1
    for s in world.states.values():
        for _ in range(s.queued):
            if rng.random() < complete:
                s.queued -= 1
            elif rng.random() < cancel:
                s.queued -= 1
                s.levels -= 1
        built = s.levels - s.queued
        if built > 0 and rng.random() < demolish:
            s.levels -= rng.randint(1, built)

    def change_owner(s, new_owner):
        when = rng.random()
        if when < 1 / 3:                     # construction cancelled before the hook
            s.levels -= s.queued
            s.queued = 0
        on_state_owner_change(world, s, new_owner)
        if 1 / 3 <= when < 2 / 3:            # ...or after it
            s.levels -= s.queued
            s.queued = 0

    for s in list(world.states.values()):
        if rng.random() < conquest:
            others = [cid for cid in alive if cid != s.owner]
            if others:
                change_owner(s, rng.choice(others))
    if rng.random() < annex and len(alive) > 2:
        loser, winner = rng.sample(alive, 2)
        # Whether the loser still exists when its last states' hooks fire is
        # unread, so the model takes both orders.
        dies_first = rng.random() < 0.5
        if dies_first:
            world.countries[loser].alive = False
        for s in world.owned(loser):
            change_owner(s, winner)
        world.countries[loser].alive = False
    if rng.random() < split:
        coastal = [s for s in world.states.values() if s.coastal and s.levels > s.queued]
        if coastal:
            parent = rng.choice(coastal)
            new_id = max(world.states) + 1
            # a split makes a new state scope with no variables; it brings
            # some finished levels with it (the records stay with the parent
            # and come back to its owner at the next recording)
            moved = rng.randint(0, parent.levels - parent.queued)
            parent.levels -= moved
            world.states[new_id] = State(new_id, parent.basin, rng.choice(alive), levels=moved)
    order = list(alive)
    rng.shuffle(order)
    for cid in order:
        if world.alive(cid):
            record_country(world, cid)


def step_pacts(world: World, rng: random.Random, *, start=0.03, end=0.03) -> None:
    """Administer Seabed Claims for the random worlds: with probability `start`
    a subject without the pact gets it, with `end` a pact ends."""
    if rng.random() < start:
        subs = [c.cid for c in world.countries.values() if c.alive and c.overlord is not None
                and world.alive(c.overlord) and (c.overlord, c.cid) not in world.administer]
        if subs:
            sub = rng.choice(subs)
            start_pact(world, world.countries[sub].overlord, sub)
    if rng.random() < end and world.administer:
        end_pact(world, *rng.choice(sorted(world.administer)))


def step_leases(world: World, rng: random.Random, *, start=0.05, end=0.03) -> None:
    """Treaty leases for the random worlds, after the month's recording: with
    probability `start` two claimants try a lease of a random size in a random
    basin (the article's possible), and with `end` a standing lease ends."""
    if rng.random() < start:
        claimants = [cid for cid in world.countries if is_claimant(world, cid)]
        if len(claimants) >= 2:
            src, dst = rng.sample(claimants, 2)
            b = rng.choice(BASINS)
            if can_lease(world, src, dst, b):
                start_lease(world, src, dst, b, rng.randint(1, own_claims(world.countries[src], b)))
    if rng.random() < end:
        leases = [(c.cid, b) for c in world.countries.values() if c.alive for b in BASINS
                  if c.lease_src[b] is not None and (c.cid, b) not in world.leases_ended]
        if leases:
            end_lease(world, *rng.choice(leases))
