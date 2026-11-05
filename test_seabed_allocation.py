"""The seabed licences' allocation (Global Commons, spec § 2.4, § 8).

Runs the Python model (scripts/analysis/seabed_model.py), which the script
follows step for step, over random worlds: building that fills the room,
demolition, conquest landing between building and recording, annexation,
splits and old saves, with monthly recording, owner-change recording and the
yearly water-filling, under the Open, Regulated and Scramble regimes and the
Antarctic Treaty's Southern bar.

What must hold:
- no basin's records exceed its pool (where nothing is grandfathered);
- every level, built or queued, is licensed after its owner's recording,
  except one its owner queued past its room through the gate's
  under-construction branch, which waits unrecorded while the owner has no
  share left (review H1) and never takes a licence no share paid for;
- a basin over its pool (an old save) never grows;
- a power with no coast in a basin gets a small share there;
- a coastal country without the technology is weighed, and its share waits
  for it: no claims, no room, and the first mover gets only what its weight
  wins against everyone's;
- no licence in use is taken away (entitlement >= holdings), and room is
  never negative after a sharing.

Set SEABED_MODEL_WORLDS (and SEABED_MODEL_YEARS) for a longer run; the spec's
claim was 2,000 worlds of 60 years.
"""
import math
import os
import random
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "analysis"))

import seabed_model as m  # noqa: E402

WORLDS = int(os.environ.get("SEABED_MODEL_WORLDS", "30"))
YEARS = int(os.environ.get("SEABED_MODEL_YEARS", "20"))


def run(world, rng, years, *, regime_schedule=None, check=None, **step):
    """Advance `world` `years` years: twelve months, then the yearly pass."""
    for year in range(years):
        if regime_schedule:
            world.regime = regime_schedule(year)
        for _ in range(12):
            m.step_month(world, rng, **step)
            if check:
                check(world, "month")
        m.yearly_pass(world)
        if check:
            check(world, "pass")


class PoolsHoldTest(unittest.TestCase):
    """No annexation and no splits: nothing is ever recorded against no share,
    so every basin stays within its pool, in every regime, with builders using
    both branches of the gate."""

    def _check(self, world, when):
        for b in m.BASINS:
            self.assertLessEqual(world.basin_records(b), m.POOLS[b], (b, when))
            self.assertLessEqual(world.basin_records(b) + world.basin_unbuilt(b), m.POOLS[b], (b, when))
            self.assertEqual(world.no_share[b], 0, b)
        self.assertEqual(world.stamped_no_share, 0)
        for s in world.states.values():
            if s.coastal and world.alive(s.owner):
                self.assertLessEqual(s.records(), s.levels, f"state {s.sid} holds licences it has no levels for")
        for c in world.countries.values():
            for b in m.BASINS:
                self.assertGreaterEqual(c.unbuilt[b], 0)
            if not c.alive:
                continue
            for b in m.BASINS:
                # a lease's total holds, and its unused claims are part of the lessee's claims
                self.assertLessEqual(c.lease_built[b] + c.lease_unused[b], c.lease_n[b], (c.cid, b, when))
                self.assertGreaterEqual(c.lease_unused[b], 0)
                self.assertLessEqual(c.lease_unused[b], c.unbuilt[b], (c.cid, b, when))
            if when == "month" and m.pending(world, c.cid) > 0:
                # a level waits for a licence only while its owner has no share left
                self.assertEqual(sum(c.unbuilt.values()), 0, f"country {c.cid} leaves a level unlicensed")
            if when == "pass":
                for b in m.BASINS:
                    # the sharing's holdings: a lease's licences count as its lessor's
                    self.assertGreaterEqual(c.sh[b], 0)
                    self.assertGreaterEqual(c.ent[b], c.sh[b], "a licence in use was taken away")

    def _worlds(self, regime, seed, fixed=False):
        for i in range(WORLDS):
            rng = random.Random(seed * 100003 + i)
            world = m.random_world(rng, regime=regime, fixed=fixed)
            run(world, rng, YEARS, check=self._check, annex=0, split=0)

    def test_open(self):
        self._worlds(m.OPEN, 1)

    def test_regulated(self):
        self._worlds(m.REGULATED, 2)

    def test_scramble(self):
        self._worlds(m.SCRAMBLE, 3)

    def test_regime_changes(self):
        for i in range(WORLDS // 2):
            rng = random.Random(4000 + i)
            world = m.random_world(rng)
            run(world, rng, YEARS, regime_schedule=lambda y: (m.OPEN, m.REGULATED, m.SCRAMBLE)[(y // 3) % 3],
                check=self._check, annex=0, split=0)

    def test_fixed_point(self):
        """The engine's 1e-5 truncation, as the script computes."""
        self._worlds(m.REGULATED, 5, fixed=True)

    def test_full_pools(self):
        """Little demolition: the pools fill and builders sit at room 0 with
        construction under way, the review's H1 case, in every regime."""
        for i in range(WORLDS // 2):
            rng = random.Random(6300 + i)
            world = m.random_world(rng, regime=(m.OPEN, m.REGULATED, m.SCRAMBLE)[i % 3])
            run(world, rng, YEARS, check=self._check, annex=0, split=0, demolish=0.002, conquest=0.01)
            self.assertGreater(sum(world.basin_records(b) for b in m.BASINS), 0)

    def test_one_unlicensed_level_at_most(self):
        """Without conquest moving one between owners, a country never has more
        than the one level the gate's second branch let in at room 0."""
        def check(world, when):
            self._check(world, when)
            for c in world.countries.values():
                if c.alive:
                    self.assertLessEqual(m.pending(world, c.cid), 1, c.cid)
        for i in range(WORLDS // 2):
            rng = random.Random(6100 + i)
            world = m.random_world(rng)
            run(world, rng, YEARS, check=check, annex=0, split=0, conquest=0)

    def test_leases(self):
        """Treaty leases start and end at random between claimants, in every
        regime: the pools hold and no lease goes over its total."""
        for i in range(WORLDS):
            rng = random.Random(7700 + i)
            world = m.random_world(rng, regime=(m.OPEN, m.REGULATED, m.SCRAMBLE)[i % 3])
            for _ in range(YEARS):
                for _ in range(12):
                    m.step_leases(world, rng)                 # a treaty enters into force; the month's recording follows
                    m.step_month(world, rng, annex=0, split=0)
                    self._check(world, "month")
                m.yearly_pass(world)
                self._check(world, "pass")

    def test_pools_fill(self):
        """After a sharing with claimants, every pool is fully shared, under
        either regime (an unclaimed reserved half joins the open half): the
        entitlements and the shares waiting for countries without the
        technology."""
        rng = random.Random(6)
        for k in range(40):
            world = m.random_world(rng, regime=m.REGULATED if k % 2 else m.OPEN)
            m.yearly_pass(world)
            for b in m.BASINS:
                if any(c.weight[b] > 0 for c in world.countries.values() if c.alive):
                    self.assertEqual(sum(c.ent[b] + c.wait[b] for c in world.countries.values() if c.alive),
                                     m.POOLS[b], b)


class GrandfatheredTest(unittest.TestCase):
    """What can go over (§ 2.4): old saves, splits, a holder annexed with
    unrecorded levels. The excess is recorded against no share, and a basin
    over its pool never grows."""

    def _never_grows_over_pool(self, world, rng, years, **step):
        """Records never exceed what the last sharing left the basin (its pool,
        or its grandfathered holdings if more), plus anything recorded against
        no share since. A demolished level's licence goes back to a share and
        may be built again, so records can come back up to that ceiling."""
        def ceiling():
            return {b: max(m.POOLS[b], world.basin_records(b) + world.basin_unbuilt(b)) for b in m.BASINS}
        cap = ceiling()
        since = dict(world.no_share)
        for _ in range(years):
            for _ in range(12):
                m.step_month(world, rng, **step)
                for b in m.BASINS:
                    grandfathered = world.no_share[b] - since[b]
                    self.assertLessEqual(world.basin_records(b), cap[b] + grandfathered, f"{b} grew past its ceiling")
                    self.assertLessEqual(world.basin_records(b) + world.basin_unbuilt(b), cap[b] + grandfathered, b)
                for c in world.countries.values():
                    if c.alive and m.pending(world, c.cid) > 0:
                        self.assertEqual(sum(c.unbuilt.values()), 0, f"country {c.cid} leaves a level unlicensed")
            m.yearly_pass(world)
            # grandfathering only through § 2.4's cases: never a stamped state
            self.assertEqual(world.stamped_no_share, 0)
            for b in m.BASINS:
                if world.basin_records(b) > m.POOLS[b]:
                    self.assertEqual(world.basin_unbuilt(b), 0, f"room in {b}, over its pool")
            cap = ceiling()
            since = dict(world.no_share)

    def test_old_save(self):
        for i in range(WORLDS // 2):
            rng = random.Random(7000 + i)
            world = m.random_world(rng, old_save_levels=40)
            levels = {b: sum(s.levels for s in world.states.values() if s.basin == b) for b in m.BASINS}
            for cid in world.countries:
                m.record_country(world, cid)          # the first recording: no shares exist yet
            for b in m.BASINS:
                self.assertEqual(world.basin_records(b), levels[b])
                self.assertEqual(world.no_share[b], levels[b], "an old save's levels take no share")
            self._never_grows_over_pool(world, rng, YEARS // 2, annex=0, split=0)

    def test_annexation_and_splits(self):
        for i in range(WORLDS // 2):
            rng = random.Random(8000 + i)
            world = m.random_world(rng)
            self._never_grows_over_pool(world, rng, YEARS, annex=0.02, split=0.03)

    def test_an_over_pool_basin_gives_no_room(self):
        world = m.World({0: m.Country(0, policy=m.SPONSOR, navy=50), 1: m.Country(1, policy=m.SPONSOR, navy=50)},
                        {0: m.State(0, "arctic", 0, levels=150), 1: m.State(1, "arctic", 1)})
        m.yearly_pass(world)
        self.assertEqual(world.basin_records("arctic"), 150)
        self.assertEqual(world.countries[0].ent["arctic"], 150)      # grandfathered
        self.assertEqual(world.countries[0].unbuilt["arctic"], 0)
        self.assertEqual(world.countries[1].unbuilt["arctic"], 0)    # no room in an over-pool basin
        self.assertGreater(world.countries[1].unbuilt["pacific"], 0)  # but its distant claims stand


class OwnerChangeTest(unittest.TestCase):
    def test_conquest_between_building_and_recording(self):
        """A level finished last month can't cross a border without a licence:
        it is recorded against the stamped holder's share."""
        world = m.World({0: m.Country(0, policy=m.SPONSOR, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                        {0: m.State(0, "pacific", 0), 1: m.State(1, "pacific", 1)})
        m.yearly_pass(world)
        m.record_country(world, 0)
        u0 = world.countries[0].unbuilt["pacific"]
        world.states[0].levels += 3                      # built, not yet recorded
        m.on_state_owner_change(world, world.states[0], 1)
        self.assertEqual(world.states[0].lic["pacific"], 3)
        self.assertEqual(world.countries[0].unbuilt["pacific"], u0 - 3)   # the holder paid
        self.assertEqual(world.states[0].holder, 1)
        self.assertEqual(world.no_share["pacific"], 0)

    def test_without_the_owner_change_recording_the_pool_leaks(self):
        """The control: a full pool, a level built with the holder's last share
        and conquered before its recording. With the owner-change recording the
        holder pays; without it the conqueror, who has no share left, records it
        against none and the basin goes over its pool."""
        def full_world():
            # no navy, so neither has a distant share to fall back on
            world = m.World({0: m.Country(0, policy=m.SPONSOR), 1: m.Country(1, policy=m.SPONSOR)},
                            {0: m.State(0, "arctic", 0), 1: m.State(1, "arctic", 1)})
            m.yearly_pass(world)
            for cid in (0, 1):
                world.states[cid].levels = world.countries[cid].unbuilt["arctic"] - (1 if cid == 0 else 0)
                m.record_country(world, cid)
            world.states[0].levels += 1          # the holder's last licence, built, not yet recorded
            return world

        world = full_world()
        m.on_state_owner_change(world, world.states[0], 1)
        m.record_country(world, 1)
        self.assertEqual(world.basin_records("arctic"), m.POOLS["arctic"])

        world = full_world()
        world.states[0].owner = 1     # the hook left out: nothing restamps the state either
        m.record_country(world, 1)
        self.assertEqual(world.no_share["arctic"], 1)
        # the holder's unused share still stands beside the record taken
        # against none: one more level than the pool, once the holder builds
        self.assertEqual(world.basin_records("arctic") + world.basin_unbuilt("arctic"), m.POOLS["arctic"] + 1)

    def test_annexed_holder_records_against_no_share(self):
        world = m.World({0: m.Country(0, policy=m.SPONSOR, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                        {0: m.State(0, "indian", 0), 1: m.State(1, "indian", 1)})
        m.yearly_pass(world)
        m.record_country(world, 0)
        world.states[0].levels += 2
        world.countries[0].alive = False
        m.on_state_owner_change(world, world.states[0], 1)
        self.assertEqual(world.no_share["indian"], 2)
        self.assertEqual(world.states[0].lic["indian"], 2)


class UnderConstructionBranchTest(unittest.TestCase):
    """Review H1: the gate's second branch (room >= 0 in a state with a level
    under construction) lets one more level in at room 0. Two Arctic claimants
    at 50/50 fill their shares; A keeps a construction going and queues
    another level every month."""

    def _arctic(self, control):
        world = m.World({0: m.Country(0, policy=m.SPONSOR), 1: m.Country(1, policy=m.SPONSOR)},
                        {0: m.State(0, "arctic", 0), 1: m.State(1, "arctic", 1)},
                        shortfall_no_share=control)
        m.yearly_pass(world)
        for cid in (0, 1):
            world.states[cid].levels = world.countries[cid].unbuilt["arctic"]
            m.record_country(world, cid)
        world.states[0].queued = 1          # one level of A's still under construction
        for month in range(24):
            if month and month % 12 == 0:
                m.yearly_pass(world)
            s = world.states[0]
            if m.can_build(world, 0, s):
                s.levels += 1
                s.queued += 1
            for cid in (0, 1):
                m.record_country(world, cid)
        return world

    def test_the_reviews_leak_before_the_fix(self):
        world = self._arctic(control=True)
        self.assertEqual(world.basin_records("arctic"), 124)
        self.assertEqual(world.no_share["arctic"], 24)
        # what seabed_cap now reads as BROKEN, though the ceiling absorbs the 24
        self.assertEqual(world.stamped_no_share, 24)

    def test_the_fix_keeps_the_pool(self):
        world = self._arctic(control=False)
        self.assertEqual(world.basin_records("arctic"), m.POOLS["arctic"])
        self.assertEqual(world.no_share["arctic"], 0)
        self.assertEqual(world.stamped_no_share, 0)
        self.assertEqual(m.pending(world, 0), 1)       # the one level the branch let in waits
        self.assertLess(m.room(world, 0), 0)           # and shuts both branches

    def test_a_waiting_level_takes_a_licence_once_one_frees(self):
        world = self._arctic(control=False)
        world.countries[0].navy = 20                   # A now claims far from home too
        m.yearly_pass(world)                           # and the sharing gives it distant shares
        m.record_country(world, 0)
        self.assertEqual(m.pending(world, 0), 0)       # the waiting level takes one of them
        self.assertEqual(world.basin_records("arctic") - world.states[1].records(), 100 - 50)
        self.assertEqual(world.basin_records("arctic"), m.POOLS["arctic"])
        self.assertEqual(sum(s.distant() for s in world.states.values()), 1)

    def test_random_worlds_leak_without_the_fix(self):
        over = 0
        for i in range(WORLDS // 3):
            rng = random.Random(6200 + i)
            world = m.random_world(rng)
            world.shortfall_no_share = True
            for _ in range(YEARS):
                for _ in range(12):
                    # little demolition, so the pools fill and builders reach room 0
                    m.step_month(world, rng, annex=0, split=0, demolish=0.002, conquest=0.01)
                m.yearly_pass(world)
                over += sum(1 for b in m.BASINS if world.basin_records(b) > m.POOLS[b])
        self.assertGreater(over, 0)


class LicenceChoiceTest(unittest.TestCase):
    def test_local_first_then_the_most_then_swap_back(self):
        c = m.Country(0, policy=m.SPONSOR)
        c.unbuilt.update(pacific=1, atlantic=2, indian=5)
        s = m.State(0, "pacific", 0, levels=3)
        world = m.World({0: c}, {0: s})
        m.record_country(world, 0)
        self.assertEqual(s.lic["pacific"], 1)
        self.assertEqual(s.lic["indian"], 2)            # the basin with the most
        self.assertEqual(s.distant(), 2)
        c.unbuilt["pacific"] = 1                         # a local licence frees up
        m.record_country(world, 0)
        self.assertEqual(s.lic["pacific"], 2)
        self.assertEqual(s.distant(), 1)
        self.assertEqual(c.unbuilt["indian"], 4)         # the distant one went back
        s.levels = 1                                     # demolished: distant licences go back first
        m.record_country(world, 0)
        self.assertEqual(s.lic, {"pacific": 1, "atlantic": 0, "indian": 0, "arctic": 0, "southern": 0})
        self.assertEqual(c.unbuilt["indian"], 5)
        self.assertEqual(c.unbuilt["pacific"], 1)


class WeightTest(unittest.TestCase):
    """§ 2.3's worked examples, and the soft cap."""

    def _country_with(self, navy, coast, policy=m.SPONSOR, **kw):
        """coast: [(basin, ports)] one incorporated coastal state each."""
        c = m.Country(0, navy=navy, policy=policy, **kw)
        states = {i: m.State(i, b, 0, ports=p) for i, (b, p) in enumerate(coast)}
        return m.World({0: c}, states)

    def test_australia_like(self):
        # 5 of 12 coastal states on the Southern Ocean, 8 port levels there, 60 flotillas
        coast = [("southern", 8)] + [("southern", 0)] * 4 + [("indian", 0)] * 7
        w = m.compute_weights(self._country_with(60, coast), 0)
        self.assertAlmostEqual(w["southern"], 10 + 8 + 25)

    def test_great_power_far_and_home(self):
        coast = [("pacific", 15)] + [("pacific", 0)] * 9 + [("atlantic", 0)] * 20
        world = self._country_with(200, coast)
        w = m.compute_weights(world, 0)
        self.assertAlmostEqual(w["southern"], 10)
        self.assertAlmostEqual(w["pacific"], 20 + 15 + 200 * 10 / 30)
        world.countries[0].station = True
        self.assertAlmostEqual(m.compute_weights(world, 0)["southern"], 15)

    def test_policy_factor_and_assertive_navy(self):
        coast = [("pacific", 0)]
        survey = m.compute_weights(self._country_with(100, coast, m.SURVEY), 0)
        unilateral = m.compute_weights(self._country_with(100, coast, m.UNILATERAL), 0)
        self.assertAlmostEqual(survey["pacific"], (2 + 100) * m.POLICY_FACTOR[m.SURVEY])
        self.assertAlmostEqual(unilateral["pacific"], 2 + 200)
        self.assertAlmostEqual(unilateral["atlantic"], 0.05 * 200)
        world = self._country_with(100, coast)
        world.regime = m.SCRAMBLE
        self.assertAlmostEqual(m.compute_weights(world, 0)["pacific"], 2 + 200)

    def test_a_no_coast_power_gets_a_small_share(self):
        """A great power with no Southern coast against three Southern powers."""
        countries = {0: m.Country(0, policy=m.SPONSOR, navy=200)}
        states = {i: m.State(i, "atlantic", 0) for i in range(20)}
        for cid in (1, 2, 3):
            countries[cid] = m.Country(cid, policy=m.SPONSOR, navy=40)
            for j in range(5):
                states[len(states)] = m.State(len(states), "southern", cid, ports=2)
        world = m.World(countries, states)
        m.yearly_pass(world)
        far = world.countries[0].ent["southern"]
        home = [world.countries[cid].ent["southern"] for cid in (1, 2, 3)]
        self.assertGreater(far, 0)
        self.assertLess(far, min(home) / 3)

    def test_unincorporated_coast_counts_half(self):
        # one incorporated and two unincorporated Pacific states, no ports, navy 0
        c = m.Country(0, policy=m.SPONSOR)
        states = {0: m.State(0, "pacific", 0), 1: m.State(1, "pacific", 0, incorporated=False),
                  2: m.State(2, "pacific", 0, incorporated=False)}
        w = m.compute_weights(m.World({0: c}, states), 0)
        self.assertAlmostEqual(w["pacific"], 2 * (1 + m.UNINCORPORATED_COAST * 2))
        self.assertEqual(m.UNINCORPORATED_COAST, 0.5)
        # a basin with only unincorporated coast is home, its ports count in full,
        # and the navy spreads over the coast with those states at half
        c = m.Country(0, policy=m.SPONSOR, navy=30)
        states = {0: m.State(0, "pacific", 0), 1: m.State(1, "atlantic", 0, incorporated=False, ports=3)}
        world = m.World({0: c}, states)
        w = m.compute_weights(world, 0)
        self.assertAlmostEqual(w["atlantic"], 2 * 0.5 + 3 + 30 * 0.5 / 1.5)
        self.assertAlmostEqual(w["pacific"], 2 + 30 * 1 / 1.5)
        self.assertAlmostEqual(w["indian"], 0.05 * 30)

    def test_unincorporated_coast_in_the_readout(self):
        """need_navy converts weight to navy with the same half-counted spread."""
        countries = {0: m.Country(0, policy=m.SPONSOR, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)}
        states = {0: m.State(0, "pacific", 0), 1: m.State(1, "atlantic", 0, incorporated=False),
                  2: m.State(2, "pacific", 1)}
        world = m.World(countries, states)
        m.yearly_pass(world)
        x = m.need_weight(world, "atlantic", 0)
        self.assertIsNotNone(x)
        self.assertEqual(m.need_navy(world, 0, "atlantic"), math.ceil(x / (0.5 / 1.5)))

    def test_barred_countries_hold_only_what_they_held(self):
        countries = {0: m.Country(0, policy=m.SPONSOR, navy=100, barred=True, station=True),
                     1: m.Country(1, policy=m.SPONSOR, navy=20)}
        states = {0: m.State(0, "southern", 0, levels=12), 1: m.State(1, "southern", 1)}
        world = m.World(countries, states)
        m.yearly_pass(world)
        self.assertEqual(world.countries[0].ent["southern"], 12)      # grandfathered
        self.assertEqual(world.countries[0].unbuilt["southern"], 0)
        self.assertEqual(world.countries[1].ent["southern"], m.POOLS["southern"] - 12)
        world.states[0].levels = 0                                     # its levels go
        m.record_country(world, 0)
        m.yearly_pass(world)
        self.assertEqual(world.countries[0].ent["southern"], 0)


class RegulatedTest(unittest.TestCase):
    def test_the_reserved_half_goes_to_eligible_parties(self):
        rng = random.Random(11)
        for _ in range(30):
            world = m.random_world(rng, regime=m.REGULATED)
            for s in world.states.values():
                s.levels = 0
            m.yearly_pass(world)
            for b in m.BASINS:
                part = [c for c in world.countries.values() if c.alive and c.weight[b] > 0]
                if not any(c.eligible for c in part):
                    continue
                not_eligible = [c for c in part if not c.eligible]
                open_half = m.POOLS[b] - m.POOLS[b] // 2
                # with no holdings, the non-eligible share only the open half
                # (+1 each at most from the largest-remainder leftovers)
                self.assertLessEqual(sum(c.ent[b] for c in not_eligible), open_half + len(not_eligible), b)

    def test_a_minor_party_keeps_a_share(self):
        """The anti-goal: early movers must not lock a basin. A minor eligible
        party next to a great power holding most of the open half. On Sponsor
        Contractors the great power's floor may take from the reserved half
        when the Law of the Sea comes into force (the pioneer investors, seabed
        claims spec § 2.2); the floor fades by a quarter a year, so the minor
        party has its reserved half back within three sharings."""
        for policy, sharings in ((m.SURVEY, 1), (m.SPONSOR, 3)):
            countries = {0: m.Country(0, policy=policy, navy=300),
                         1: m.Country(1, policy=m.SPONSOR, navy=2, eligible=True)}
            states = {0: m.State(0, "pacific", 0, levels=0), 1: m.State(1, "pacific", 1)}
            world = m.World(countries, states, regime=m.OPEN)
            m.yearly_pass(world)
            open_minor = world.countries[1].ent["pacific"]
            world.regime = m.REGULATED
            m.yearly_pass(world)
            self.assertGreater(world.countries[1].ent["pacific"], open_minor, policy)
            for _ in range(sharings - 1):
                m.yearly_pass(world)
            self.assertGreaterEqual(world.countries[1].ent["pacific"], m.POOLS["pacific"] // 2, policy)

    def test_a_party_over_its_reserved_share_spills_into_the_open_half(self):
        countries = {cid: m.Country(cid, policy=m.SPONSOR, navy=10, eligible=True) for cid in range(3)}
        countries[3] = m.Country(3, policy=m.SPONSOR, navy=10)
        states = {cid: m.State(cid, "pacific", cid) for cid in range(4)}
        states[0].levels = 120
        world = m.World(countries, states, regime=m.REGULATED)
        m.yearly_pass(world)
        ent = {cid: world.countries[cid].ent["pacific"] for cid in range(4)}
        self.assertEqual(ent[0], 120)
        self.assertEqual(sum(ent.values()), m.POOLS["pacific"])
        # the other two parties still share what is left of the reserved half
        self.assertGreater(ent[1], ent[3])


class WaitingShareTest(unittest.TestCase):
    """Every coastal country is weighed; one without the technology weighs at
    LATENT_FACTOR and its share waits for it (the model's header). The anti-goal
    the claimants-only sharing broke: the first country with the technology was
    handed every pool and could queue it all before a rival caught up."""

    def _world(self, *, first_policy=m.SPONSOR, regime=m.OPEN):
        """0: the first mover; 1: a rival of the same size; 2: an eligible minor.
        All three in the Pacific, and nobody but 0 has the technology."""
        countries = {0: m.Country(0, policy=first_policy, navy=200),
                     1: m.Country(1, policy=m.SPONSOR, navy=200, tech=False),
                     2: m.Country(2, policy=m.SPONSOR, navy=5, tech=False, eligible=True)}
        states, sid = {}, 0
        for owner, n in ((0, 10), (1, 10), (2, 3)):
            for _ in range(n):
                states[sid] = m.State(sid, "pacific", owner, ports=2)
                sid += 1
        return m.World(countries, states, regime=regime)

    def _queue_all_room(self, world, cid):
        """Queue levels in the country's states while the gate lets them in,
        then record, as a builder racing for the pool would."""
        for s in world.owned(cid):
            while m.can_build(world, cid, s):
                s.levels += 1
                s.queued += 1
        m.record_country(world, cid)

    def test_a_lone_first_mover_gets_only_its_weighted_share(self):
        world = self._world()
        m.yearly_pass(world)
        c = world.countries
        w_first = c[0].weight["pacific"]
        w_all = sum(x.weight["pacific"] for x in c.values())
        self.assertAlmostEqual(c[1].weight["pacific"], w_first * m.LATENT_FACTOR)
        self.assertLess(c[0].ent["pacific"], m.POOLS["pacific"])
        self.assertLessEqual(abs(c[0].ent["pacific"] - m.POOLS["pacific"] * w_first / w_all), 1)
        self.assertEqual(sum(x.ent["pacific"] + x.wait["pacific"] for x in c.values()), m.POOLS["pacific"])
        for cid in (1, 2):           # a waiting share is no claim, and nobody's entitlement
            self.assertEqual(c[cid].ent["pacific"], 0)
            self.assertEqual(c[cid].unbuilt["pacific"], 0)
            self.assertGreater(c[cid].wait["pacific"], 0)
        # a distant basin: the first mover's twentieth of a navy is no longer
        # the whole pool, even where nobody has coast, and much less beside a
        # coastal country without the technology
        far = c[0].weight["atlantic"]
        self.assertLessEqual(abs(c[0].ent["atlantic"] - m.POOLS["atlantic"] * far
                                 / sum(x.weight["atlantic"] for x in c.values())), 1)
        before = c[0].ent["atlantic"]
        self.assertLess(before, m.POOLS["atlantic"])
        world.states[100] = m.State(100, "atlantic", 1)
        m.yearly_pass(world)
        self.assertLess(c[0].ent["atlantic"], before)

    def test_the_head_start_is_bounded_by_the_latent_factor(self):
        """Against an equal rival without the technology, the first mover's
        share is 1 / (1 + LATENT_FACTOR) of what the two of them share; once
        the rival has it on the same policy, half."""
        countries = {0: m.Country(0, policy=m.SPONSOR, navy=100),
                     1: m.Country(1, policy=m.SPONSOR, navy=100, tech=False)}
        states = {i: m.State(i, "pacific", i % 2, ports=1) for i in range(10)}
        world = m.World(countries, states)
        m.yearly_pass(world)
        pool = m.POOLS["pacific"]
        self.assertLessEqual(abs(world.countries[0].ent["pacific"] - pool / (1 + m.LATENT_FACTOR)), 1)
        self.assertLessEqual(world.countries[0].ent["pacific"], pool * min(1, 0.5 / m.LATENT_FACTOR) + 1)

    def test_a_lone_first_mover_cannot_lock_the_basin(self):
        """The anti-goal: the first mover queues everything the gate lets it,
        before anyone else has the technology. The rival and the minor still
        share what it couldn't take, as soon as they research it; and under
        the Regulated regime the minor's reserved half waited for it."""
        for regime in (m.OPEN, m.REGULATED):
            world = self._world(regime=regime)
            m.yearly_pass(world)
            first = world.countries[0].ent["pacific"]
            self._queue_all_room(world, 0)
            self.assertEqual(world.basin_records("pacific"), first, regime)
            self.assertLess(first, m.POOLS["pacific"] * 0.9, regime)
            for cid in (1, 2):
                world.countries[cid].tech = True
            m.yearly_pass(world, first_of_year=False)               # the reshare a month later
            ent = {cid: world.countries[cid].ent["pacific"] for cid in world.countries}
            self.assertEqual(ent[0], first, regime)                  # its licences are its own, for good
            self.assertEqual(ent[1] + ent[2], m.POOLS["pacific"] - first, regime)
            self.assertGreater(ent[1], 0, regime)
            self.assertGreater(ent[2], 0, regime)
            if regime == m.REGULATED:
                self.assertGreaterEqual(ent[2], m.POOLS["pacific"] // 2 - first // 2 - 1, regime)

    def test_the_reserved_half_waits_for_an_eligible_party(self):
        """Regulated, the only claimant not eligible: the reserved half no
        longer joins the open half while an eligible party without the
        technology has weight; the claimant shares the open half only."""
        world = self._world(regime=m.REGULATED)
        m.yearly_pass(world)
        open_half = m.POOLS["pacific"] - m.POOLS["pacific"] // 2
        self.assertLessEqual(world.countries[0].ent["pacific"], open_half)
        self.assertGreaterEqual(world.countries[2].wait["pacific"], m.POOLS["pacific"] // 2)

    def test_a_newcomer_turns_its_waiting_share_into_claims(self):
        world = self._world()
        m.yearly_pass(world)
        waiting = world.countries[1].wait["pacific"]
        world.countries[1].tech = True
        world.countries[1].policy = m.SURVEY                         # the factor it waited at
        m.yearly_pass(world, first_of_year=False)
        c = world.countries[1]
        self.assertEqual(c.wait["pacific"], 0)
        self.assertEqual(c.ent["pacific"], c.unbuilt["pacific"])
        self.assertLessEqual(abs(c.ent["pacific"] - waiting), 1)
        self.assertGreater(m.room(world, 1), 0)

    def test_a_holder_without_the_technology_holds_and_waits(self):
        """A conqueror without the technology keeps its licences; its share
        above them waits, and it has no claims."""
        world = self._world()
        world.states[10].levels = 3                                  # in the rival's state
        m.on_state_owner_change(world, world.states[10], 1)          # recorded against no share
        m.yearly_pass(world)
        c = world.countries[1]
        self.assertEqual(c.held["pacific"], 3)
        self.assertEqual(c.ent["pacific"], 3)
        self.assertEqual(c.unbuilt["pacific"], 0)
        self.assertGreater(c.wait["pacific"], 0)

    def test_random_worlds_keep_waiting_shares_out_of_use(self):
        """Over random worlds: a country without the technology never holds a
        claim or room after a sharing, and the pools hold with its share in
        them."""
        rng = random.Random(27)
        for k in range(WORLDS):
            world = m.random_world(rng, regime=(m.OPEN, m.REGULATED, m.SCRAMBLE)[k % 3])

            def check(w, when):
                if when != "pass":
                    return
                for c in w.countries.values():
                    if c.alive and not c.tech:
                        self.assertEqual(sum(c.unbuilt.values()), 0)
                        self.assertLessEqual(m.room(w, c.cid), 0)
                    if c.tech or not c.alive:
                        self.assertEqual(sum(c.wait.values()), 0)
                for b in m.BASINS:
                    self.assertLessEqual(sum(c.ent[b] + c.wait[b] for c in w.countries.values() if c.alive),
                                         max(m.POOLS[b], w.basin_records(b)), b)
            run(world, rng, 6, check=check)


class WaterFillingTest(unittest.TestCase):
    def test_passes_are_bounded_by_the_claimants(self):
        rng = random.Random(12)
        most = 0
        for _ in range(WORLDS):
            world = m.random_world(rng, n_countries=12)
            run(world, rng, 5)
            for b, passes in world.iterations.items():
                part = sum(1 for c in world.countries.values() if c.alive)
                self.assertLessEqual(passes, part + 1, b)
                most = max(most, passes)
        self.assertGreater(most, 1)

    def test_freezing_matches_the_spec(self):
        """Three equal claimants on a pool of 300; one holds 150. It is frozen
        at 150 and the others share the rest."""
        countries = {cid: m.Country(cid, policy=m.SPONSOR, navy=10) for cid in range(3)}
        states = {cid: m.State(cid, "pacific", cid) for cid in range(3)}
        states[0].levels = 150
        world = m.World(countries, states)
        m.yearly_pass(world)
        self.assertEqual([world.countries[c].ent["pacific"] for c in range(3)], [150, 75, 75])
        self.assertEqual(world.countries[0].unbuilt["pacific"], 0)


class FloorTest(unittest.TestCase):
    """Sponsor Contractors' floors (seabed claims spec § 2.2): a Sponsor
    country's claims fade by at most a quarter at the year's first sharing;
    a mid-year sharing honours January's floor; a Scramble voids floors; the
    Antarctic bar leaves a Southern floor at holdings; floors that don't fit
    scale down."""

    def _one_basin_world(self, policy=m.SPONSOR):
        # two claimants on the Pacific; country 0 on `policy`
        w = m.World({0: m.Country(0, policy=policy, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                    {0: m.State(0, "pacific", 0), 1: m.State(1, "pacific", 1)})
        m.yearly_pass(w)
        return w

    def test_sponsor_claims_fade_by_a_quarter_at_most(self):
        w = self._one_basin_world()
        before = w.countries[0].unbuilt["pacific"]            # 150
        w.countries[1].navy = 1000                            # a rival's buildup
        m.yearly_pass(w)
        self.assertGreaterEqual(w.countries[0].unbuilt["pacific"], math.floor(0.75 * before))

    def test_survey_claims_are_fully_re_divided(self):
        w = self._one_basin_world(policy=m.SURVEY)
        w.countries[1].navy = 1000
        m.yearly_pass(w)
        self.assertLess(w.countries[0].unbuilt["pacific"], 10)

    def test_mid_year_sharing_honours_the_stored_floor(self):
        w = self._one_basin_world()
        w.countries[1].navy = 1000
        m.yearly_pass(w)                                      # floor fixed: 112
        kept = w.countries[0].unbuilt["pacific"]
        m.yearly_pass(w, first_of_year=False)
        self.assertEqual(w.countries[0].unbuilt["pacific"], kept)   # no 0.75 x 0.75

    def test_leaving_sponsor_mid_year_drops_the_floor(self):
        w = self._one_basin_world()
        w.countries[1].navy = 1000
        m.yearly_pass(w)
        w.countries[0].policy = m.SURVEY
        m.yearly_pass(w, first_of_year=False)
        self.assertLess(w.countries[0].unbuilt["pacific"], 10)

    def test_scramble_voids_floors(self):
        w = self._one_basin_world()
        w.regime = m.SCRAMBLE
        w.countries[1].navy = 1000
        m.yearly_pass(w)
        self.assertLess(w.countries[0].unbuilt["pacific"], 10)

    def test_barred_southern_floor_is_holdings(self):
        # country 0 has a Southern coast, claims and five levels there; then the bar
        w = m.World({0: m.Country(0, policy=m.SPONSOR, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                    {0: m.State(0, "pacific", 0), 1: m.State(1, "pacific", 1), 2: m.State(2, "southern", 0)})
        m.yearly_pass(w)
        w.states[2].levels = 5
        m.record_country(w, 0)
        self.assertGreater(w.countries[0].unbuilt["southern"], 0)
        w.countries[0].barred = True
        m.yearly_pass(w)
        self.assertEqual(w.countries[0].floor["southern"], 5)
        self.assertEqual(w.countries[0].ent["southern"], 5)
        self.assertEqual(w.countries[0].unbuilt["southern"], 0)

    def test_floors_scale_down_to_fit(self):
        # country 1 holds 280 grandfathered Pacific licences; country 0's floor (112) can't fit beside them
        w = self._one_basin_world()
        w.states[1].levels = 280
        w.states[1].lic["pacific"] = 280
        w.countries[1].unbuilt["pacific"] = 0                  # grandfathered: no claims of its own left
        m.yearly_pass(w)
        ent = {cid: w.countries[cid].ent["pacific"] for cid in (0, 1)}
        held = sum(w.countries[cid].held["pacific"] for cid in (0, 1))
        self.assertLessEqual(sum(ent.values()), max(m.POOLS["pacific"], held))
        self.assertGreaterEqual(ent[1], 280)
        self.assertEqual(ent[0], m.POOLS["pacific"] - 280)

    def test_fit_floors_leaves_holdings_alone(self):
        w = self._one_basin_world()
        w.states[1].levels = 320                               # over the pool on its own
        w.states[1].lic["pacific"] = 320
        m.yearly_pass(w)
        self.assertEqual(w.countries[1].ent["pacific"], 320)
        self.assertEqual(w.countries[0].ent["pacific"], 0)

    def test_a_non_participant_keeps_no_floor(self):
        w = self._one_basin_world()
        m.yearly_pass(w)                                       # a floor is stored from 150 claims
        self.assertGreater(w.countries[0].floor["pacific"], 0)
        w.countries[0].tech = False
        m.yearly_pass(w)
        self.assertEqual(w.countries[0].floor["pacific"], 0)
        self.assertEqual(w.countries[0].unbuilt["pacific"], 0)

    def test_a_holder_without_the_technology_keeps_no_floor(self):
        # still a participant through its licences, but no longer a claimant
        w = self._one_basin_world()
        w.states[0].levels = 4
        m.record_country(w, 0)
        m.yearly_pass(w)
        w.countries[0].tech = False
        m.yearly_pass(w)
        self.assertEqual(w.countries[0].floor["pacific"], 0)
        self.assertEqual(w.countries[0].ent["pacific"], 4)
        self.assertEqual(w.countries[0].unbuilt["pacific"], 0)

    def test_missing_floor_is_no_floor(self):
        w = self._one_basin_world()
        w.countries[0].floor = dict.fromkeys(m.BASINS, 0)      # an old save
        w.countries[1].navy = 1000
        m.yearly_pass(w, first_of_year=False)
        self.assertLess(w.countries[0].unbuilt["pacific"], 10)

    def test_a_lost_state_adds_no_protection(self):
        """Review I3: country 0 holds 100 Pacific licences and claims; its January
        floor protects the claims, not the licences, so losing the mined state
        before a mid-year sharing leaves it at most January's protected part."""
        w = m.World({0: m.Country(0, policy=m.SPONSOR, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                    {0: m.State(0, "pacific", 0), 1: m.State(1, "pacific", 1), 2: m.State(2, "pacific", 0)})
        m.yearly_pass(w)
        w.states[2].levels = 100
        m.record_country(w, 0)
        m.yearly_pass(w)                                      # January: held 100, claims protected
        protected = w.countries[0].floor["pacific"] - w.countries[0].held["pacific"]
        self.assertGreater(protected, 0)
        m.on_state_owner_change(w, w.states[2], 1)
        w.countries[1].navy = 1000
        m.yearly_pass(w, first_of_year=False)
        self.assertEqual(w.countries[0].held["pacific"], 0)
        self.assertLessEqual(w.countries[0].unbuilt["pacific"], protected)

    def test_building_on_claims_mid_year_keeps_the_floor(self):
        w = self._one_basin_world()
        m.yearly_pass(w)                                      # floor 112 from 150 claims
        floor = w.countries[0].floor["pacific"]
        w.states[0].levels = 30
        m.record_country(w, 0)
        w.countries[1].navy = 1000
        m.yearly_pass(w, first_of_year=False)
        self.assertEqual(w.countries[0].ent["pacific"], floor)

    def test_random_worlds_with_mid_year_sharings(self):
        """The pools hold with floors stored in January and honoured by
        mid-year sharings, while countries change policy between them."""
        check = PoolsHoldTest._check
        for i in range(WORLDS // 2):
            rng = random.Random(9100 + i)
            world = m.random_world(rng, regime=(m.OPEN, m.REGULATED, m.SCRAMBLE)[i % 3])
            for year in range(YEARS):
                for month in range(12):
                    m.step_month(world, rng, annex=0, split=0)
                    check(self, world, "month")
                    if month == 6 and rng.random() < 0.5:
                        for c in world.countries.values():
                            if rng.random() < 0.2:
                                c.policy = rng.choice((m.SURVEY, m.SPONSOR, m.UNILATERAL))
                        m.yearly_pass(world, first_of_year=False)
                        check(self, world, "pass")
                m.yearly_pass(world)
                check(self, world, "pass")


class RelinquishTest(unittest.TestCase):
    """Relinquish and Claim Again (seabed claims spec § 2.5)."""

    def _world(self):
        w = m.World({0: m.Country(0, policy=m.SPONSOR, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                    {0: m.State(0, "pacific", 0), 1: m.State(1, "pacific", 1)})
        m.yearly_pass(w)
        w.states[0].levels = 3
        m.record_country(w, 0)
        m.yearly_pass(w)                                        # a floor is stored
        return w

    def test_relinquish_drops_claims_now_and_keeps_licences(self):
        w = self._world()
        self.assertGreater(w.countries[0].unbuilt["pacific"], 0)
        self.assertGreater(w.countries[0].floor["pacific"], 3)
        m.relinquish(w, 0, "pacific")
        self.assertEqual(w.countries[0].unbuilt["pacific"], 0)
        self.assertEqual(w.basin_records("pacific"), 3)
        self.assertEqual(w.countries[0].floor["pacific"], 0)
        self.assertGreater(w.countries[0].unbuilt["atlantic"], 0)      # other basins untouched

    def test_no_weight_until_claim_again(self):
        w = self._world()
        m.relinquish(w, 0, "pacific")
        m.yearly_pass(w)
        self.assertEqual(w.countries[0].weight["pacific"], 0)
        self.assertEqual(w.countries[0].ent["pacific"], w.countries[0].held["pacific"])
        self.assertGreater(w.countries[0].weight["atlantic"], 0)
        m.claim_again(w, 0, "pacific")
        m.yearly_pass(w)
        self.assertGreater(w.countries[0].weight["pacific"], 0)
        self.assertGreater(w.countries[0].unbuilt["pacific"], 0)

    def test_relinquish_licenses_queued_levels_first(self):
        """Review I1: levels queued this month, not yet licensed by the monthly
        recording, take their basin's licences before the claims go."""
        w = self._world()
        w.states[0].levels += 4
        w.states[0].queued += 4
        m.relinquish(w, 0, "pacific")
        m.record_country(w, 0)
        self.assertEqual(m.pending(w, 0), 0)
        self.assertEqual(w.states[0].lic["pacific"], 7)
        self.assertEqual(w.states[0].distant(), 0)
        self.assertEqual(w.countries[0].unbuilt["pacific"], 0)

    def test_the_freed_claims_wait_for_the_next_sharing(self):
        w = self._world()
        rival = w.countries[1].unbuilt["pacific"]
        m.relinquish(w, 0, "pacific")
        m.record_country(w, 1)
        self.assertEqual(w.countries[1].unbuilt["pacific"], rival)
        m.yearly_pass(w)
        self.assertGreater(w.countries[1].unbuilt["pacific"], rival)

    def test_relinquish_never_pays(self):
        """Two copies of a world, driven by generators seeded alike, differ
        only in that one country relinquishes a basin and claims it again
        before the next sharing (January's or a mid-year one): it never ends
        that sharing with more."""
        import copy
        worse = 0
        for i in range(200):
            rng = random.Random(9500 + i)
            world = m.random_world(rng, regime=(m.OPEN, m.REGULATED, m.SCRAMBLE)[i % 3])
            run(world, rng, 1, annex=0, split=0)
            other = copy.deepcopy(world)
            ra, rb = random.Random(i), random.Random(i)
            for _ in range(12):
                m.step_month(world, ra, annex=0, split=0)
                m.step_month(other, rb, annex=0, split=0)
            cid = rng.randrange(len(world.countries))
            b = rng.choice(m.BASINS)
            m.relinquish(world, cid, b)
            m.claim_again(world, cid, b)
            first = i % 2 == 0
            m.yearly_pass(world, first_of_year=first)
            m.yearly_pass(other, first_of_year=first)
            mine, theirs = world.countries[cid], other.countries[cid]
            self.assertLessEqual(mine.ent[b], theirs.ent[b], (i, cid, b))
            self.assertLessEqual(sum(mine.ent.values()), sum(theirs.ent.values()), (i, cid, b))
            worse += mine.ent[b] < theirs.ent[b]
        self.assertGreater(worse, 0)


class LeaseTest(unittest.TestCase):
    """Treaty leases (seabed claims spec § 4): up to N of the lessor's claims
    move at entry into force; each sharing re-divides them and then tops the
    lease back up to N less the licences built on it, from the lessor's own
    claims; those licences count as the lessor's holdings in the sharing, so
    the lessee's own share is untouched; an ended lease's claims return at the
    next sharing and its licences stay the lessee's."""

    def _world(self, lessor_policy=m.SPONSOR, lessor_navy=10):
        # country 0 (lessor) and 1 (lessee), each with one Pacific coastal state; one pass
        w = m.World({0: m.Country(0, policy=lessor_policy, navy=lessor_navy),
                     1: m.Country(1, policy=m.SPONSOR, navy=10)},
                    {0: m.State(0, "pacific", 0), 1: m.State(1, "pacific", 1)})
        m.yearly_pass(w)
        return w

    @staticmethod
    def _build(w, sid, n):
        """n more finished levels in state sid, recorded."""
        w.states[sid].levels += n
        m.record_country(w, w.states[sid].owner)

    def _assert_pool(self, w, b="pacific"):
        self.assertLessEqual(w.basin_records(b) + w.basin_unbuilt(b), m.POOLS[b])
        for c in w.countries.values():
            self.assertGreaterEqual(c.unbuilt[b], 0)
            self.assertGreaterEqual(c.sh[b], 0)

    def test_entry_moves_claims_at_once(self):
        w = self._world()
        before = w.countries[0].unbuilt["pacific"]
        lessee = w.countries[1].unbuilt["pacific"]
        self.assertTrue(m.can_lease(w, 0, 1, "pacific"))
        m.start_lease(w, 0, 1, "pacific", 20)
        self.assertEqual(w.countries[0].unbuilt["pacific"], before - 20)
        self.assertEqual(w.countries[1].lease_unused["pacific"], 20)
        self.assertEqual(w.countries[1].unbuilt["pacific"], lessee + 20)
        self.assertEqual(w.countries[1].lease_src["pacific"], 0)
        self.assertEqual(w.countries[1].lease_n["pacific"], 20)

    def test_own_claims_are_used_first(self):
        w = self._world()
        w.countries[1].unbuilt["pacific"] = 5
        m.start_lease(w, 0, 1, "pacific", 20)
        self._build(w, 1, 7)
        self.assertEqual(w.countries[1].lease_built["pacific"], 2)
        self.assertEqual(w.countries[1].lease_unused["pacific"], 18)
        self.assertEqual(m.own_claims(w.countries[1], "pacific"), 0)

    def test_lessee_share_is_untouched_by_the_lease(self):
        """The lessee builds all its own claims and 10 on the lease; at the next
        sharing its own claims are what they would be had it built only its own,
        with no lease. A lessor this strong is never frozen, so both worlds
        share alike."""
        import copy
        a = self._world(lessor_navy=300)
        b = copy.deepcopy(a)
        own = a.countries[1].unbuilt["pacific"]
        m.start_lease(a, 0, 1, "pacific", 20)
        self._build(a, 1, own + 10)
        self._build(b, 1, own)
        self.assertEqual(a.countries[1].lease_built["pacific"], 10)
        m.yearly_pass(a)
        m.yearly_pass(b)
        self.assertEqual(a.countries[1].ent["pacific"], b.countries[1].ent["pacific"])
        self.assertEqual(m.own_claims(a.countries[1], "pacific"), b.countries[1].unbuilt["pacific"])
        self.assertEqual(a.countries[1].sh["pacific"], own)
        self.assertEqual(a.countries[0].sh["pacific"], 10)
        self.assertEqual(a.countries[1].lease_unused["pacific"], 10)          # topped back up to N - built
        self._assert_pool(a)

    def test_total_never_exceeds_n(self):
        for i in range(50):
            rng = random.Random(7300 + i)
            w = m.random_world(rng, regime=(m.OPEN, m.REGULATED, m.SCRAMBLE)[i % 3])
            for _ in range(8):
                for _ in range(12):
                    m.step_month(w, rng, annex=0.01, split=0)
                    m.step_leases(w, rng, start=0.3, end=0.1)
                    for c in w.countries.values():
                        for b in m.BASINS:
                            self.assertLessEqual(c.lease_built[b] + c.lease_unused[b], c.lease_n[b], (i, c.cid, b))
                m.yearly_pass(w)

    def test_partial_top_up(self):
        # a weak lessor (about 33 Pacific claims a sharing on Survey's ×0.75,
        # under 43 at any factor) and a lease larger than that
        w = self._world(lessor_policy=m.SURVEY, lessor_navy=0)
        w.countries[0].unbuilt["pacific"] = 3
        m.start_lease(w, 0, 1, "pacific", 100)
        self.assertEqual(w.countries[1].lease_unused["pacific"], 3)
        self.assertEqual(w.countries[0].unbuilt["pacific"], 0)
        m.yearly_pass(w)
        share = w.countries[0].ent["pacific"] - w.countries[0].sh["pacific"]
        self.assertLess(share, 100)
        self.assertEqual(w.countries[1].lease_unused["pacific"], share)
        self.assertEqual(w.countries[0].unbuilt["pacific"], 0)
        self._assert_pool(w)

    def test_lessor_annexed(self):
        w = self._world()
        own = w.countries[1].unbuilt["pacific"]
        m.start_lease(w, 0, 1, "pacific", 20)
        self._build(w, 1, own + 5)
        w.countries[0].alive = False                     # annexed by the lessee
        m.on_state_owner_change(w, w.states[0], 1)
        m.yearly_pass(w)
        c = w.countries[1]
        self.assertIsNone(c.lease_src["pacific"])
        self.assertEqual((c.lease_n["pacific"], c.lease_built["pacific"], c.lease_unused["pacific"]), (0, 0, 0))
        self.assertEqual(w.states[1].lic["pacific"], own + 5)   # it keeps what it built
        self.assertGreaterEqual(c.ent["pacific"], own + 5)
        self.assertEqual(c.sh["pacific"], c.held["pacific"])
        self._assert_pool(w)

    def test_destroyed_lease_level(self):
        w = self._world()
        w.countries[1].unbuilt["pacific"] = 0            # every level it builds is on the lease
        m.start_lease(w, 0, 1, "pacific", 20)
        self._build(w, 1, 5)
        self.assertEqual(w.countries[1].lease_built["pacific"], 5)
        w.states[1].levels -= 3                          # demolished
        m.record_country(w, 1)
        self.assertEqual(m.own_claims(w.countries[1], "pacific"), 3)   # the licences come back as its own claims
        m.yearly_pass(w)
        c = w.countries[1]
        self.assertLessEqual(c.lease_built["pacific"], c.held["pacific"])
        self.assertGreaterEqual(c.sh["pacific"], 0)
        self.assertEqual(c.lease_built["pacific"] + c.lease_unused["pacific"], 20)   # the lease has its room back
        self._assert_pool(w)

    def test_ended_lease_returns_unused_at_next_sharing(self):
        w = self._world()
        m.start_lease(w, 0, 1, "pacific", 20)
        m.end_lease(w, 1, "pacific")
        self.assertEqual(w.countries[1].lease_unused["pacific"], 20)          # kept until the sharing
        m.yearly_pass(w)
        for cid in (0, 1):
            c = w.countries[cid]
            self.assertEqual(c.unbuilt["pacific"], c.ent["pacific"] - c.held["pacific"], cid)
        self.assertIsNone(w.countries[1].lease_src["pacific"])
        self.assertEqual(w.countries[1].lease_unused["pacific"], 0)
        self.assertTrue(m.can_lease(w, 0, 1, "pacific"))                    # a new lease may follow
        self._assert_pool(w)

    def test_one_lease_per_basin_per_lessee(self):
        w = self._world()
        m.start_lease(w, 0, 1, "pacific", 20)
        self.assertFalse(m.can_lease(w, 0, 1, "pacific"))
        self.assertTrue(m.can_lease(w, 0, 1, "atlantic"))
        self.assertTrue(m.can_lease(w, 1, 0, "pacific"))

    def test_antarctic_bar_on_both_sides(self):
        w = m.World({0: m.Country(0, policy=m.SPONSOR, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                    {0: m.State(0, "southern", 0), 1: m.State(1, "southern", 1)})
        m.yearly_pass(w)
        self.assertTrue(m.can_lease(w, 0, 1, "southern"))
        w.countries[1].barred = True
        self.assertFalse(m.can_lease(w, 0, 1, "southern"))
        self.assertFalse(m.can_lease(w, 1, 0, "southern"))
        self.assertTrue(m.can_lease(w, 0, 1, "pacific"))

    def test_relinquished_lessee_takes_no_top_up(self):
        w = self._world()
        m.start_lease(w, 0, 1, "pacific", 20)
        m.relinquish(w, 1, "pacific")
        self.assertEqual(w.countries[1].lease_unused["pacific"], 0)
        self.assertEqual(w.countries[1].lease_built["pacific"], 0)          # not booked as built
        m.relinquish(w, 1, "atlantic")
        self.assertFalse(m.can_lease(w, 0, 1, "atlantic"))                   # no new lease into a relinquished basin
        m.yearly_pass(w)
        self.assertEqual(w.countries[1].lease_unused["pacific"], 0)
        self._assert_pool(w)


class SubjectTest(unittest.TestCase):
    """Administer Seabed Claims (seabed claims spec § 5.2): while the pact
    stands, the subject's unused claims pass to its overlord at entry and after
    every sharing, with no total; the licences the overlord builds on them count
    as the subject's holdings at the sharing; nothing pools without the pact,
    and an ended pact's claims return at the next sharing."""

    def _world(self, pact=True, overlord_policy=m.SPONSOR):
        # 0 overlord, 1 its subject, 2 a third party: one Pacific state each
        countries = {0: m.Country(0, policy=overlord_policy, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10),
                     2: m.Country(2, policy=m.SPONSOR, navy=10)}
        countries[1].overlord = 0
        w = m.World(countries, {cid: m.State(cid, "pacific", cid) for cid in range(3)})
        m.yearly_pass(w)
        if pact:
            m.start_pact(w, 0, 1)
        return w

    def test_entry_passes_the_claims_at_once(self):
        w = self._world(pact=False)
        claims = dict(w.countries[1].unbuilt)
        overlord = dict(w.countries[0].unbuilt)
        m.start_pact(w, 0, 1)
        for b in m.BASINS:
            self.assertEqual(w.countries[1].unbuilt[b], 0, b)
            self.assertEqual(w.countries[0].subj_unused[b], claims[b], b)
            self.assertEqual(w.countries[0].unbuilt[b], overlord[b] + claims[b], b)
            self.assertEqual(w.countries[1].pass_unused[b], claims[b], b)

    def test_subject_claims_pass_every_sharing(self):
        w = self._world()
        m.yearly_pass(w)
        sub, over = w.countries[1], w.countries[0]
        for b in m.BASINS:
            self.assertEqual(sub.unbuilt[b], 0, b)
            self.assertGreater(over.subj_unused[b], 0, b)
            self.assertEqual(over.subj_unused[b], sub.ent[b] - sub.sh[b], b)

    def test_no_pooling_without_the_pact(self):
        w = self._world(pact=False)
        m.yearly_pass(w)
        self.assertGreater(w.countries[1].unbuilt["pacific"], 0)
        self.assertEqual(w.countries[0].subj_unused["pacific"], 0)

    def test_overlord_builds_subject_claims_last_and_they_count_as_the_subjects(self):
        w = self._world()
        own = m.own_claims(w.countries[0], "pacific")
        w.states[0].levels += own + 7
        m.record_country(w, 0)
        self.assertEqual(w.countries[1].pass_built["pacific"], 7)
        m.yearly_pass(w)
        self.assertEqual(w.countries[1].sh["pacific"], 7)
        self.assertEqual(w.countries[0].sh["pacific"], own)

    def test_a_pact_never_squeezes_a_third_party(self):
        """Three equal claimants; the overlord builds every claim it has, its
        subject's included, for five years. The third party's share stays a
        third: the subject's weight pays for the licences built on its claims."""
        w = self._world()
        third = w.countries[2].ent["pacific"]
        for _ in range(5):
            w.states[0].levels += w.countries[0].unbuilt["pacific"]
            m.record_country(w, 0)
            m.yearly_pass(w)
            self.assertGreaterEqual(w.countries[2].ent["pacific"], third)

    def test_pact_ends_mid_year(self):
        w = self._world()
        m.yearly_pass(w)
        passed = w.countries[0].subj_unused["pacific"]
        m.end_pact(w, 0, 1)
        self.assertEqual(w.countries[0].subj_unused["pacific"], passed)       # kept until the sharing
        m.yearly_pass(w, first_of_year=False)
        sub, over = w.countries[1], w.countries[0]
        self.assertEqual(over.subj_unused["pacific"], 0)
        self.assertGreater(sub.unbuilt["pacific"], 0)
        self.assertEqual(sub.unbuilt["pacific"], sub.ent["pacific"] - sub.sh["pacific"])

    def test_overlord_floor_excludes_subject_claims(self):
        w = self._world()
        over = w.countries[0]
        own = m.own_claims(over, "pacific")
        self.assertGreater(over.subj_unused["pacific"], 0)
        m.yearly_pass(w)                                                    # January: the floor is set first
        self.assertEqual(over.floor_prot["pacific"], math.floor(m.FLOOR_KEEP * own))

    def test_relinquish_drops_subject_claims_without_building(self):
        w = self._world()
        m.relinquish(w, 0, "pacific")
        self.assertEqual(w.countries[0].subj_unused["pacific"], 0)
        self.assertEqual(w.countries[1].pass_built["pacific"], 0)
        m.yearly_pass(w)
        self.assertEqual(w.countries[0].subj_unused["pacific"], 0)          # none pass into a relinquished basin
        self.assertGreater(w.countries[0].subj_unused["atlantic"], 0)

    def test_random_worlds_with_pacts(self):
        """random_world makes subjects and pacts; pacts start and end at
        random; the pools hold and the counters stay consistent."""
        check = PoolsHoldTest._check
        made = 0
        for i in range(WORLDS):
            rng = random.Random(8800 + i)
            world = m.random_world(rng, regime=(m.OPEN, m.REGULATED, m.SCRAMBLE)[i % 3])
            made += len(world.administer)
            for _ in range(YEARS):
                for _ in range(12):
                    m.step_leases(world, rng)
                    m.step_pacts(world, rng)
                    m.step_month(world, rng, annex=0, split=0)
                    check(self, world, "month")
                    for c in world.countries.values():
                        if c.alive:
                            for b in m.BASINS:
                                self.assertLessEqual(c.lease_unused[b] + c.subj_unused[b], c.unbuilt[b])
                                self.assertGreaterEqual(c.pass_built[b], 0)
                m.yearly_pass(world)
                check(self, world, "pass")
        self.assertGreater(made, 0)


class RatchetTest(unittest.TestCase):
    """Review C2 (the owner's default: switching off and on shouldn't pay).
    Licences built on a lease or on a subject's passed claims go on counting
    against the lessor's or subject's share after the lease or pact ends,
    while both take part; so ending and restarting one never moves their
    cost onto a third party. Three equal claimants, one Pacific state each;
    the builder builds every claim it has, every year."""

    YEARS = 6

    def _world(self):
        cs = {i: m.Country(i, policy=m.SPONSOR, navy=10) for i in range(3)}
        cs[1].overlord = 0
        w = m.World(cs, {i: m.State(i, "pacific", i) for i in range(3)})
        m.yearly_pass(w)
        return w

    def _pact(self, mode):
        w = self._world()
        third, pair = [], []
        for _ in range(self.YEARS):
            if mode != "none" and (0, 1) not in w.administer:
                m.start_pact(w, 0, 1)                  # Administer after the sharing
            if mode == "restart":                      # Return and Administer again before it
                m.end_pact(w, 0, 1)
                m.start_pact(w, 0, 1)
                sub = w.countries[1]
                self.assertEqual(sub.pass_unused["pacific"], w.countries[0].subj_unused["pacific"])
            w.states[0].levels += w.countries[0].unbuilt["pacific"]
            m.record_country(w, 0)
            if mode == "toggle":
                m.end_pact(w, 0, 1)                    # Return Seabed Claims just before the sharing
            m.yearly_pass(w)
            third.append(w.countries[2].ent["pacific"])
            pair.append(w.basin_records("pacific") + w.countries[0].unbuilt["pacific"]
                        + w.countries[1].unbuilt["pacific"] - w.states[2].lic["pacific"])
        return third, pair

    def test_a_toggled_pact_takes_nothing_from_a_third_party(self):
        none, _ = self._pact("none")
        steady, steady_pair = self._pact("steady")
        for mode in ("toggle", "restart"):
            third, pair = self._pact(mode)
            self.assertEqual(third, none, mode)
            self.assertEqual(third, steady, mode)
            for p, q in zip(pair, steady_pair):
                self.assertLessEqual(p, q, mode)

    def _lease(self, toggle):
        cs = {i: m.Country(i, policy=m.SPONSOR, navy=10) for i in range(3)}
        w = m.World(cs, {i: m.State(i, "pacific", i) for i in range(3)})
        m.yearly_pass(w)
        third = []
        for _ in range(self.YEARS):
            if w.countries[1].lease_n["pacific"] == 0 and m.can_lease(w, 0, 1, "pacific"):
                m.start_lease(w, 0, 1, "pacific", 40)
            w.states[1].levels += w.countries[1].unbuilt["pacific"]
            m.record_country(w, 1)
            if toggle:
                m.end_lease(w, 1, "pacific")           # the treaty ends just before the sharing
            m.yearly_pass(w)
            third.append(w.countries[2].ent["pacific"])
        return third

    def test_a_re_signed_lease_takes_nothing_from_a_third_party(self):
        self.assertEqual(self._lease(True), self._lease(False))
        self.assertEqual(self._lease(True), [100] * self.YEARS)

    def test_an_ended_lease_goes_on_counting_against_the_lessor(self):
        cs = {i: m.Country(i, policy=m.SPONSOR, navy=10) for i in range(3)}
        w = m.World(cs, {i: m.State(i, "pacific", i) for i in range(3)})
        m.yearly_pass(w)
        own = w.countries[1].unbuilt["pacific"]
        m.start_lease(w, 0, 1, "pacific", 20)
        w.states[1].levels += own + 20
        m.record_country(w, 1)
        m.end_lease(w, 1, "pacific")
        m.yearly_pass(w)
        c = w.countries[1]
        self.assertEqual(c.lease_src["pacific"], 0)                       # the record stays
        self.assertEqual((c.lease_n["pacific"], c.lease_built["pacific"], c.lease_past["pacific"]), (0, 0, 20))
        self.assertEqual(w.countries[0].sh["pacific"], 20)
        self.assertEqual(c.sh["pacific"], own)
        # a different lessor is refused while the record stands; the same one may lease again
        self.assertFalse(m.can_lease(w, 2, 1, "pacific"))
        self.assertTrue(m.can_lease(w, 0, 1, "pacific"))
        m.start_lease(w, 0, 1, "pacific", 10)
        self.assertEqual((c.lease_n["pacific"], c.lease_built["pacific"], c.lease_past["pacific"]), (10, 0, 20))
        # the lessor gone, the licences are the lessee's own and the record clears
        w.countries[0].alive = False
        m.on_state_owner_change(w, w.states[0], 2)
        m.yearly_pass(w)
        self.assertIsNone(c.lease_src["pacific"])
        self.assertEqual(c.lease_past["pacific"], 0)
        self.assertTrue(m.can_lease(w, 2, 1, "pacific"))

    def test_a_former_subject_goes_on_paying_while_both_take_part(self):
        w = self._world()
        m.start_pact(w, 0, 1)
        w.states[0].levels += w.countries[0].unbuilt["pacific"]
        m.record_country(w, 0)
        built = w.countries[1].pass_built["pacific"]
        self.assertGreater(built, 0)
        m.end_pact(w, 0, 1)
        w.countries[1].overlord = None                 # independent
        m.yearly_pass(w)
        self.assertEqual(w.countries[1].pass_to, 0)
        self.assertEqual(w.countries[1].sh["pacific"], built)
        # a new overlord's pact drops the old record
        w.countries[1].overlord = 2
        m.start_pact(w, 2, 1)
        self.assertEqual(w.countries[1].pass_built["pacific"], 0)
        self.assertEqual(w.countries[1].pass_to, 2)


class FeeTest(unittest.TestCase):
    """The holding fee's base (seabed claims spec § 2.1): licences on levels
    unbuilt at the year's first sharing twice running, and the queued
    licences per basin the pool bar shows."""

    def test_grace_then_fee(self):
        s = m.State(0, "pacific", 0, levels=4, queued=4)
        s.lic["pacific"] = 4
        w = m.World({0: m.Country(0)}, {0: s})
        self.assertEqual(m.fee_base(w, 0), 0)                 # no snapshots
        m.take_snapshots(w)
        self.assertEqual(m.fee_base(w, 0), 0)                 # one January
        m.take_snapshots(w)
        self.assertEqual(m.fee_base(w, 0), 4)                 # two Januaries
        s.queued = 1                                           # three finished
        self.assertEqual(m.fee_base(w, 0), 1)

    def test_no_snapshots_no_fee(self):
        # an old save, or a revolution's winner before its first January
        s = m.State(0, "pacific", 0, levels=9, queued=6)
        s.lic["pacific"] = 9
        w = m.World({0: m.Country(0)}, {0: s})
        self.assertEqual(m.fee_base(w, 0), 0)

    def test_the_years_first_sharing_takes_the_snapshots(self):
        s = m.State(0, "pacific", 0)
        w = m.World({0: m.Country(0, policy=m.SPONSOR, navy=10)}, {0: s})
        m.yearly_pass(w)
        s.levels = s.queued = 3
        m.record_country(w, 0)
        m.yearly_pass(w)
        m.yearly_pass(w, first_of_year=False)                 # a mid-year sharing takes none
        self.assertEqual((s.snap1, s.snap2), (3, 0))
        m.yearly_pass(w)
        self.assertEqual((s.snap1, s.snap2), (3, 3))
        self.assertEqual(m.fee_base(w, 0), 3)

    def test_a_pending_level_pays_nothing(self):
        # five levels, two queued, four licences: the unlicensed level is a queued one
        s = m.State(0, "pacific", 0, levels=5, queued=2)
        s.lic["pacific"] = 4
        s.snap1 = s.snap2 = 2
        w = m.World({0: m.Country(0)}, {0: s})
        self.assertEqual(m.fee_base(w, 0), 1)
        self.assertEqual(m.queued_by_basin(w, 0)["pacific"], 1)

    def test_queued_by_basin(self):
        # an Atlantic state with 5 levels, 2 queued, licences atlantic 3 + arctic 2:
        # the 2 queued count against the distant (Arctic) licences first
        s = m.State(0, "atlantic", 0, levels=5, queued=2)
        s.lic["atlantic"] = 3
        s.lic["arctic"] = 2
        w = m.World({0: m.Country(0)}, {0: s})
        self.assertEqual(m.queued_by_basin(w, 0), {**dict.fromkeys(m.BASINS, 0), "arctic": 2})
        s.queued = 4                                           # then the state's own basin
        self.assertEqual(m.queued_by_basin(w, 0)["atlantic"], 2)
        self.assertEqual(m.queued_by_basin(w, 0)["arctic"], 2)

    def test_queued_by_basin_in_random_worlds(self):
        for i in range(WORLDS // 2):
            rng = random.Random(9700 + i)
            world = m.random_world(rng)

            def check(world, when):
                for cid in world.countries:
                    q = m.queued_by_basin(world, cid)
                    states = [s for s in world.owned(cid) if s.coastal]
                    self.assertEqual(sum(q.values()), sum(m.unbuilt_licences(s) for s in states), cid)
                    for b in m.BASINS:
                        self.assertLessEqual(q[b], sum(s.lic[b] for s in states), (cid, b))
                        self.assertGreaterEqual(q[b], 0)
            run(world, rng, YEARS // 2, check=check, annex=0.02, split=0.03)

    def test_fee_base_bounds_under_conquest(self):
        """Snapshots travel with their state; the base never exceeds the
        licences on the state's unbuilt levels and is never negative."""
        for i in range(WORLDS // 2):
            rng = random.Random(9800 + i)
            world = m.random_world(rng)
            paid = 0

            def check(world, when):
                nonlocal paid
                for s in world.states.values():
                    if not s.coastal:
                        continue
                    base = m.fee_base_state(s)
                    self.assertGreaterEqual(base, 0)
                    self.assertLessEqual(base, max(0, s.records() - s.built), s.sid)
                    self.assertLessEqual(base, s.queued, s.sid)
                    paid += base
            run(world, rng, YEARS, check=check, annex=0.02, split=0.03, complete=0.05)
            self.assertGreater(paid, 0)


class ReadoutTest(unittest.TestCase):
    """The "+1 licence" readout (seabed claims spec § 3.5): the closed form
    against the exact answer from re-running the sharing."""

    def test_closed_form_matches_exact_in_open_worlds(self):
        rng = random.Random(77)
        for _ in range(40):
            w = m.random_world(rng, regime=m.OPEN)
            m.yearly_pass(w)
            for cid, c in w.countries.items():
                for b in m.BASINS:
                    if c.weight[b] <= 0:
                        continue
                    self._check_bound(w, b, cid)

    def _check_bound(self, w, b, cid, lower_bound=True):
        """The closed form ignores largest-remainder rounding, which can hand
        the licence over sooner: the exact need lies between the closed form
        for the entitlement itself and for one more, None reading as no
        amount. So "full" (None) means no licence for certain: the rounding
        may still hand the last one over, at a high weight."""
        exact, closed = m.exact_need_weight(w, b, cid), m.need_weight(w, b, cid)
        if exact is None:
            self.assertIsNone(closed, (cid, b))
            return
        if closed is not None:
            self.assertGreaterEqual(closed - exact, -0.01, (cid, b))
        if not lower_bound:
            return
        lower = m.need_weight(w, b, cid, step=0)
        self.assertIsNotNone(lower, (cid, b))
        self.assertGreaterEqual(exact - lower, -0.01, (cid, b))

    @staticmethod
    def _assumption_holds(w, b, cid):
        """need_weight's assumption at its own answer: no other active
        country falls to its holdings or floor."""
        f = w.final[b]
        x = m.need_weight(w, b, cid)
        me = w.countries[cid]
        me_elig = w.regime == m.REGULATED and me.eligible
        for j in f["active"]:
            if j == cid:
                continue
            c = w.countries[j]
            j_res = w.regime == m.REGULATED and c.eligible and f["wsum_res"] > 0
            if x is None:
                # "full": as our weight grows without bound a rival keeps only
                # a reserved share our weight doesn't reach
                share = f["rem_res"] * c.weight[b] / f["wsum_res"] if j_res and not me_elig else 0.0
            else:
                extra = x + (0 if cid in f["active"] else me.weight[b])
                share = f["rem_open"] * c.weight[b] / (f["wsum_all"] + extra)
                if j_res:
                    share += f["rem_res"] * c.weight[b] / (f["wsum_res"] + (extra if me_elig else 0))
            if share < f["h"][j]:
                return False
        return True

    def test_closed_form_bounds_exact_after_years(self):
        """Holdings, floors and the reserved half, five years in: the closed
        form never understates wherever its assumption holds, and it fails
        rarely. Under the Regulated regime the halves can make it overstate by
        more than one licence, so the lower bound is the Open regime's."""
        rng = random.Random(78)
        checked = skipped = under = 0
        for i in range(30):
            w = m.random_world(rng, regime=(m.OPEN, m.REGULATED)[i % 2])
            run(w, rng, 5, annex=0, split=0)
            for cid, c in w.countries.items():
                for b in m.BASINS:
                    if c.weight[b] <= 0:
                        continue
                    if self._assumption_holds(w, b, cid):
                        checked += 1
                        self._check_bound(w, b, cid, lower_bound=w.regime == m.OPEN)
                        continue
                    # a rival pushed to its holdings or floor: the readout may understate
                    skipped += 1
                    exact, closed = m.exact_need_weight(w, b, cid), m.need_weight(w, b, cid)
                    if closed is not None and (exact is None or closed < exact - 0.01):
                        under += 1
        self.assertGreater(checked, 500)
        self.assertLess(skipped, 0.15 * (checked + skipped))
        self.assertLess(under, 0.01 * (checked + skipped))

    def test_full_basin_reads_none(self):
        # the whole Arctic held by country 0: nothing is left to share
        w = m.World({0: m.Country(0, policy=m.SPONSOR, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                    {0: m.State(0, "arctic", 0, levels=100), 1: m.State(1, "arctic", 1)})
        m.yearly_pass(w)
        self.assertIsNone(m.need_weight(w, "arctic", 1))
        self.assertIsNone(m.exact_need_weight(w, "arctic", 1))
        self.assertIsNone(m.need_navy(w, 1, "arctic"))

    def test_frozen_country_needs_its_holdings_plus_one(self):
        w = m.World({0: m.Country(0, policy=m.SPONSOR, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                    {0: m.State(0, "pacific", 0, levels=200), 1: m.State(1, "pacific", 1)})
        m.yearly_pass(w)
        self.assertEqual(w.countries[0].ent["pacific"], 200)              # frozen at its holdings
        closed, exact = m.need_weight(w, "pacific", 0), m.exact_need_weight(w, "pacific", 0)
        self.assertIsNotNone(exact)
        self.assertGreaterEqual(closed - exact, -0.01)
        self.assertLessEqual(closed - exact, max(0.25 * exact, 1.0))

    def test_navy_conversion(self):
        # home basin, 1 of 2 coastal states there, Sponsor, navy multiplier 1
        c = m.Country(0, policy=m.SPONSOR, navy=10)
        w = m.World({0: c, 1: m.Country(1, policy=m.SPONSOR, navy=40)},
                    {0: m.State(0, "pacific", 0), 1: m.State(1, "atlantic", 0), 2: m.State(2, "pacific", 1)})
        m.yearly_pass(w)
        self.assertEqual(m.need_navy(w, 0, "pacific"), math.ceil(m.need_weight(w, "pacific", 0) / (1.0 * 1 * 1 / 2)))
        self.assertEqual(m.need_navy(w, 0, "indian"), math.ceil(m.need_weight(w, "indian", 0) / (0.05 * 1.0 * 1)))
        c.policy = m.UNILATERAL                                           # the navy counts double
        m.yearly_pass(w)
        self.assertEqual(m.need_navy(w, 0, "indian"), math.ceil(m.need_weight(w, "indian", 0) / (0.05 * 1.0 * 2)))

    def test_no_claim_reads_none(self):
        w = m.World({0: m.Country(0, policy=m.SPONSOR, navy=10, barred=True), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                    {0: m.State(0, "pacific", 0), 1: m.State(1, "pacific", 1)})
        m.yearly_pass(w)
        self.assertIsNone(m.need_navy(w, 0, "southern"))


if __name__ == "__main__":
    unittest.main()
