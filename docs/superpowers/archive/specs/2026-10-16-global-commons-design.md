# The Global Commons: seabed licences, launch windows and orbital debris — design

Drafted 2026-10-16 from a reviewed outside brainstorm (two proposals: a "Global Commons"
seabed and polar partition, and a "Cislunar logistics" space layer). The owner agreed which
parts to keep, in the review conversation; § Decisions lists them. The owner's three pillars
for the system: fun, realism and balance. Read `docs/systems/mod_systems.md` § Space Race and
`docs/player_guide/10-united-nations.md` § UN conventions and agencies before planning; this
document assumes both.

## Intent

The seabed, the polar regions and Earth orbit are commons that no one owns. The late game has
none of the politics that commons bring:

1. **The Deep-Sea Mine is uncapped.** `building_ocean_mine` (`common/buildings/extra_buildings.txt:970`)
   has `has_max_level = no` and needs only `is_coastal = yes`. Any coastal state can build it
   without limit, so the seabed is never scarce, nobody contests it, and the mine undercuts the
   placed land deposits of the fourteen new mines.
2. **Propulsion technology doesn't change how the space race plays.** Reusable rockets, the Space
   Elevator and fusion drives add progress and output, but a 1960s chemical rocket and a fusion
   torch reach Mars on the same schedule.
3. **Orbit has no shared cost.** Nothing a power does in orbit harms anyone else's use of it.

This design caps the seabed in five ocean basins that powers claim shares of, under rules the
UN's Law of the Sea can regulate. It makes the planets reachable only in their real launch
windows until fusion drives free them, and adds an orbital debris index that anti-satellite
weapons drive up and remediation drives down.

## Decisions (owner, 2026-10-16)

- **Keep the seabed caps.** Basin licences cap the Deep-Sea Mine through the existing
  slot-building pattern (the Solar Power Receiver's).
- **Make the Deep-Sea Mine better now that it is capped**, strictly better than asteroid mining
  (the Extraplanetary Base) until era 12's Space Elevator and compact fusion drives (§ 1).
- **The "Seize Seabed Claims" war goal waits for a later phase** (§ 10).
- **Launch windows: yes, from tables computed ahead of time by date** (§ 5).
- **Debris needs guardrails.** A cascade slows programs and never halts them. Debris clears over
  decades (low orbits in years). Strikes count toward the UN censure case. **Plus cleanup
  efforts whose cost falls with technology and Launch Capacity.** With compact fusion drives and
  a Space Elevator, cleanup should be cheap and easy (§ 6).
- **Dropped:**
  - the weekly transit queue, deep-space commerce raiding and contested colonies;
  - the three constellation tracks and weekly reconstitution clicks;
  - a Helium-3 good;
  - Mars relieving Migration Crowding;
  - Titan hydrocarbons for Earth's market;
  - the Extraplanetary Base rework into "zone receiving complexes";
  - +300 innovation-cap rewards.

Second round (owner, 2026-10-16, on the PR):

- **Soft caps, not eligibility gates.** "For stuff like this I'd generally lean towards soft
  caps," such as a very large penalty for powers with no far-southern coastline in place of a
  ban. So any coastal power can claim in any basin, at a steep weight penalty where it has no
  coast (§ 2.3). Where such a licence can be used: third round.
- **No micromanagement while waiting for a window.** The mental model is supplies put in orbit
  while the window is awaited. Progress made while a colonization bar waits is staged in orbit
  and spent when the window opens, so lowering funding while waiting gains nothing (§ 5.2). The
  Mars Landing's arrival-season gate is dropped, which leaves one waiting rule.

Third round (owner, 2026-10-16, on the PR):

- **Conquest carries the licences.** "Could we just say you conquered the licenses too?" Yes.
  Licences are recorded on the state the mine stands in and change hands with it (§ 2.4).
- **National licences: the owner is unsure.** § 2.4 now proposes local licences first, with a
  long-haul penalty on a distant one. § 11 #1 sets out the options.
- **Soft windows with more technology**, "to ease people into it." Asteroid Mining unlocks
  launches outside a window at the premium the extra propellant costs (§ 5.2a).
- **"Avoid", not "never".** Rewarding a toggle is to be avoided, but there are times it is worth
  it for other reasons. `CLAUDE.md`'s design default now says so.

Fourth round (owner, 2026-10-16, on the PR):

- **Licences: option (a), local first and distant at a penalty**, "Awesome!" (§ 2.4).
- **No cap on the off-window premium.** "Given that it is calculated, should we not cap it?" The
  computed premium is the price. A launch outside a window happens when the months it saves
  outweigh the months its extra progress costs, weighted by the approach (§ 5.2a).

Where this document says "compact fusion drives" it means the era 12 technology
`compact_fusion_reactors`, shown in game as **Muon-Catalyzed Fusion Reactors**.

## Goals

- A Deep-Sea Mine level is a licence: scarce, worth claiming and worth more than an
  Extraplanetary Base level until era 12's propulsion arrives.
- Built levels are never taken away. A shrinking entitlement only stops new construction.
- Soft caps: every coastal power can claim in every basin, and geography sets the size of its
  share, not whether it may have one.
- Minor coastal countries keep a share when the Law of the Sea regulates the seabed (the real
  UNCLOS "parallel system": half of each basin is reserved for developing parties).
- Defecting from the Law of the Sea is a real choice with a real price (the US has never
  ratified UNCLOS, and in 2025 moved to license seabed mining under its own law).
- Chemical propulsion means waiting for a window; fusion drives end the waiting. The tables
  match the real sky.
- Orbital debris is a commons problem: everyone pays for anyone's anti-satellite strike, and
  anyone can pay to clean up.
- AI and players run under the same rules, without `is_ai` branches in the mechanics.

## Non-goals

- New map provinces, Antarctic states or resource depletion.
- Space combat, fleets in space, or a transit queue a player watches.
- New goods (no Helium-3).
- Changing what Solar System Colonization's 34 worlds give, or how colonies are claimed, beyond
  when the next one can be founded (§ 5).
- Rebalancing land mines.

## Anti-goals (would make this a failure even if it technically works)

- An AI anti-satellite war ends the space race for a player who isn't fighting it.
- A licence cut removes or downsizes a building a player paid for.
- Early movers lock a basin forever. Licences are first come, first served (that is the race),
  but the reserved half and the regime rules must leave minors a way in.
- The seabed panel asks for five decisions a year. Policy is national, and basins are readouts.
- A full space-race bar sits waiting for a window with no explanation of why or for how long.
- Waiting rewards fiddling: a player who cuts funding while a bar waits for its window, and
  restores it afterwards, must come out no better off than one who left it alone.

## Engine facts this rests on

- **The slot-building pattern works for players, the AI and private investment.** The Solar
  Power Receiver's `possible` (`common/buildings/extra_buildings.txt:1853`) reads a country
  modifier for its slots, and `solar_receiver_slots_remaining`
  (`common/script_values/extra_script_values.txt:2598`) subtracts built and queued levels
  (`level_after_queued_constructions`). The AI's builder respects `possible`, so the caps bind
  the AI with no AI code.
- **No effect removes building levels** (`docs/guides/scripting_best_practices.md` § Building
  Lifecycle Effect Gotchas).
  Shrinking means remove-and-rebuild. That resets methods, lays off staff and, for a privately
  owned building, does unrecorded things to its shares. The Deep-Sea Mine is privately owned,
  so this design never shrinks one.
- **No trigger reads a coastal state's ocean.** `is_coastal` only says yes or no. But every
  coastal land state in the mod's `map_data/state_regions/` has a `naval_exit_id` naming one of
  the 105 sea regions in `map_data/state_regions/99_seas.txt` (372 coastal states, 85 sea regions
  in use). A generator can map state → sea region → basin offline (§ 2.1).
- **`on_state_owner_change` gives only the state, under its new owner**, with no scope for the
  previous one (`scripting_best_practices.md`, the `on_state_owner_change` bullet under § `any_state`
  from State Scope Iterates Owner's States). The Strategic
  Reserve stamps the holder on the state ahead of time for that reason (`st_res_hub_holder`).
  **Whether a state keeps its variables across the change is unverified**; Grand Monuments rests
  on it too. § 2.4 depends on it and ships a self-check.
- **A production method can be gated only by technology, law, principle, identity or another
  method**, never by a trigger (`scripting_best_practices.md` § Locking Production Methods). So
  per-basin yields can't be separate methods, and the era-12 logistics methods (§ 1.2) gate on
  technology, not on owning a Space Elevator.
- **`goods_input_launch_capacity_mult` is not registered.** The mod registers
  `goods_input_launch_capacity_add`, `goods_output_launch_capacity_add` and
  `goods_output_launch_capacity_mult` (`common/modifier_type_definitions/mod_entity_modifier_types.txt:98`,
  `:103`, `:542`), not the input mult. A method using it would silently do nothing until it is
  registered.
- **`navy_size`** (country → value, flotillas) and **`naval_combat_power`** are value
  accessors (`docs/engine/event_targets_summary.txt`).
- **Dates are comparable.** `game_date >= 2033.3.1` is a trigger (`common/journal_entries/te_vanilla_opium.txt:36`),
  and `te_history_month_index` (`common/script_values/te_history_values.txt:26`) is a monotonic
  month counter (year × 12 + month).
- **Space race pace and risk run through two country modifiers**, `country_space_race_progress_mult`
  and `country_space_race_risk_mult`. Pace is floored at 0.5 a month and risk is clamped to
  1–50% (`common/script_values/space_race_values.txt:83`, `:213`). A debris penalty through
  them can slow programs but never halt them.
- **Colonies are founded by `sr_establish_colony_effect`** (`common/scripted_effects/space_race_effects.txt:801`):
  a `random_list` with a `trigger` per site. The bar-fill check in `je_space_race.txt` subtracts
  the goal and keeps the overflow. A site can drop out of the draw by adding a condition to its
  `trigger`.
- **Strike actions are diplomatic actions** (`common/diplomatic_actions/nuke.txt`), with AI
  weights. An anti-satellite strike can follow the same pattern.
- **A custom war goal must reuse an engine `kind` and needs a play type to start a war over**
  (`scripting_best_practices.md` § War Goal Types; the mod's `te_un_mandate_restore_state` and
  `te_reunify_country`). That is why the war goal waits.

## 1. Deep-Sea Mine vs Extraplanetary Base (phase 1)

### 1.1 The Deep-Sea Mine, strictly better until era 12

Today, per level at base prices (`common/production_methods/extra_pms.txt:15545`, `:15659`):

| | Deep-Sea Mine, Abyssal Plain Mining (era 11) | Extraplanetary Base, Asteroid Mining (era 11) |
|---|---|---|
| Construction | 5,000 | 20,000 |
| Employment | 2,000 | 1,000 |
| Tech-Critical Metals | 100 | 250 |
| Output value / input cost | 28,200 / 22,000 | 37,250 / 30,000 (24,000 of it Launch Capacity) |
| Profit | 6,200 (28%) | 7,250 (24%) |

The Deep-Sea Mine is cheaper to build but worse per level and per worker. Uncapped, cheap
levels were its whole case. Capped, each level must be worth claiming. Proposed `pm_ocean_mine`
(first estimate):

| | Today | Proposed |
|---|---|---|
| Employment | 1,000 machinists, 800 engineers, 200 academics | 500 machinists, 400 engineers, 100 academics |
| Structural Metals (iron) | 20 | 260 |
| Tech-Critical Metals | 100 | 260 |
| Conductive and Base Metals (lead) | 260 | 150 |
| Gold | 40 | 50 |
| Chemical and Industrial Minerals (sulfur) | 100 | 50 |
| Inputs | 22,000 | unchanged |
| Profit | 6,200 (28%) | 22,700 (103%) |

The mix follows real polymetallic nodules: mostly manganese (a structural metal), then nickel and
cobalt (tech-critical) and copper (conductive), with gold and sulfur from vent sulfides. Every
output is at least the Extraplanetary Base's, inputs are lower, the workforce is the same and
construction is a quarter of the cost, so it is strictly better on every axis but scale. The
margin sits below the late land tech-metal mines (~150–170%, `pm_smart_miners_building_tech_metals_mine`).

`pm_advanced_ocean_mine` (Advanced Nanofabrication, era 12) stays twice the base method's output
on today's inputs: 89,400 output, 25,500 input, profit 63,900. `pm_automated_ocean_mine`
(Artificial General Intelligence, era 12) keeps that output at 10 workers on today's inputs
(30,300), profit 59,100. Construction stays 5,000 (`construction_cost_mega_high`), so a licence
stays the binding limit, not the price.

### 1.2 The era-12 flip: Extraplanetary Base logistics

Asteroid mining is a launch-cost business: 80–86% of the Extraplanetary Base's input bill is
Launch Capacity. The two propulsion tracks (§ 5.1) each cut it through a new secondary method
group on `building_space_mine`. Both groups are needed, because a production method group
holds one choice:

| Group | Default | Upgrade | Gate | Effect |
|---|---|---|---|---|
| Launch to orbit | Chemical Launch | Tethered Launch | `space_elevator` (era 12) | `goods_input_launch_capacity_mult = -0.3` |
| Transport in space | Chemical Tugs | Fusion Tugs | `compact_fusion_reactors` (era 12) | `goods_input_launch_capacity_mult = -0.3` |

Register `goods_input_launch_capacity_mult` in `mod_entity_modifier_types.txt` first. Per level
at base prices, against the Deep-Sea Mine's era-12 profit of 63,900:

| Extraplanetary Base method | Neither upgrade | One | Both |
|---|---|---|---|
| Space Colony Mining (Space Colonization) | 37,000 | 65,800 (≈ parity) | 94,600 (1.5×) |
| Asteroid Mining base method | 7,250 | 14,450 | 21,650 |

So the Extraplanetary Base overtakes per level only with Space Colonization and both
propulsion technologies, and it is the route with no cap. The Deep-Sea Mine stays the better
return on construction all game (5,000 against 20,000), so licences stay worth holding.
The Space Elevator's own Launch Capacity output already lowers the price in its market, which
is the building's reward for the country that builds one.

### 1.3 Seabed output at full build-out

The map holds 3,574 levels of tech-critical mine deposits: Nickel and Cobalt 1,250, Lithium 978,
Rare Earth Metals 800, Platinum Group Metals 546, at up to ~500–600 Tech-Critical Metals a level
with their late methods. That is roughly 1.8–2.1 million a week if all were built. The pools in
§ 2.2 total 1,000 levels: 260,000 a week at the base method (≈ 13% of the land potential), twice
that with Advanced Nanofabrication. (The review conversation guessed that 1,100 levels would far
exceed demand. The deposit totals say they don't.)

## 2. Seabed basins and licences (phase 1)

### 2.1 Basins

Five basins: **Pacific**, **Atlantic**, **Indian**, **Arctic** and **Southern**. Each coastal
state belongs to exactly one, the basin of its naval exit's sea region. A state's basin decides
where its owner's claim weight comes from (§ 2.3), and which licence its mines use first
(§ 2.4). It doesn't bar a mine from another basin's licence, which works at a long-haul penalty
(§ 2.4). Real contracts reach across oceans: Germany, Belgium, France and the UK hold
International Seabed Authority contracts in the Pacific's Clarion-Clipperton Zone.

- A generator, `scripts/generators/gen_seabed_basins.py`, reads `naval_exit_id` from
  `map_data/state_regions/*.txt` and a hand-written table of the 105 sea regions → basin. It
  writes `common/scripted_effects/te_seabed_basins_generated.txt` with the effect
  `te_seabed_set_state_basin` (an `if` chain on `state_region = s:STATE_X` that sets the state
  variable `te_seabed_basin` = 1…5). It runs in `POST_LOAD_REGENERATORS`, and its test fails on a
  coastal state left unmapped.
- The table puts the Mediterranean, Black Sea, Baltic, North Sea, Caribbean and Gulf of Mexico in
  the Atlantic; the Red Sea, Persian Gulf and Arabian Sea in the Indian; the Sea of Japan, East
  and South China Seas in the Pacific. Arctic: Barents, Kara, Laptev, East Siberian, Chukchi,
  Beaufort, Greenland and Norwegian Seas, the Northwest Passage, Baffin Bay, Davis Strait and Hudson
  Bay. Southern: Patagonian Sea, Patagonian Channels, Cape of Good Hope, Great Australian Bight and
  Tasman Sea. The builder checks each borderline case against the map.
- The yearly allocation pass sets the variable on any coastal state without it, since conquest
  and splits make new state scopes. Nothing evaluated often reads the basin: the building gate
  (§ 2.6) doesn't.

### 2.2 Pools

Fixed, in Deep-Sea Mine levels (first estimate): **Pacific 300**, **Atlantic 250**,
**Indian 200**, **Southern 150**, **Arctic 100**. These are global script values, so
tuning is one edit. The Pacific is largest because the Clarion-Clipperton Zone is the richest
nodule field. The Arctic is smallest because its real prize is oil and gas, which this system
doesn't touch. Pools don't grow with technology (§ 11).

### 2.3 Claim weight

Yearly, for each coastal country with Abyssal Plain Mining, in every basin:

```
a basin it borders (it owns an incorporated coastal state there):
  coast  = 2 × its incorporated coastal states in the basin
  ports  = levels of building_port in those states
  navy   = navy_size × (its coastal states in this basin ÷ all its coastal states)
  weight = (coast + ports + navy) × policy factor (§ 2.5)

a basin it doesn't border:
  weight = 0.05 × navy_size × policy factor
```

Fleets don't sit in a basin in any way script can read, so national navy size is spread over
the country's coastline. An Antarctic research station adds +5 Southern weight whether or not
the country borders the Southern basin (phase 2, § 4).

**A soft cap, not a gate.** A power can claim far from home, but it brings no coast or ports
and a twentieth of its navy, so its share there is small. Take an Australia-like country with 5
of its 12 coastal states on the Southern Ocean, 8 port levels there and 60 flotillas: 10 + 8 +
25 = 43. A great power with 200 flotillas and no southern coast gets 10, or 15 with a station.
At home in its own Pacific (10 of 30 coastal states, 15 port levels), the same great power gets
20 + 15 + 67 = 102. So a far basin is worth about a tenth of a home one to it. All of these are
first estimates.

### 2.4 Licences: shares, records and room

**A licence belongs to a level, not to a country** (owner, 2026-10-16: "you conquered the licences
too"). Licences are recorded on the state the mine stands in, so they change hands with it. Three
pieces of state:

- **State records.** A state with Deep-Sea Mine levels carries `te_seabed_lic_<basin>`, the number
  of its levels holding a licence from each basin (usually only its own). It also carries
  `te_seabed_holder`, its owner when last recorded. The Strategic Reserve's holder stamp
  (`st_res_hub_holder`) is the pattern.
- **Unbuilt shares.** Each country carries `te_seabed_unbuilt_<basin>`: the licences it is entitled
  to in that basin and hasn't used.
- **Room**, read live: the country's unbuilt shares, summed, minus the levels in its states not
  yet recorded (built or queued). This is a copy of `solar_receiver_slots_remaining` over those
  variables. It is one national number, so the building gate (§ 2.6) reads no basin.

**Recording, monthly**, from the monthly country pulse over the owner's states:
- A level not yet recorded takes a licence from the owner's unbuilt share, from the state's own
  basin if any is left, otherwise from the basin with the most. That share goes down by one.
- A distant licence is swapped for a local one as soon as the owner has local share to spare, so
  nothing needs managing.
- Levels that went (downsized, destroyed) give their licences back to the owner's shares, distant
  ones first.
- Each pass re-stamps `te_seabed_holder` on the state.

**Recording on a change of owner.** `on_state_owner_change` gives script only the state, under its
new owner (§ Engine facts). So it first records any levels not yet recorded against the stamped
holder's shares; a level finished last month can't cross a border without a licence. If the
holder no longer exists (annexed whole), they are recorded against no share. Then the records
stay where they are: the new owner holds those licences from now on, and its own unbuilt shares
are untouched.

**Sharing, yearly**, from the country pulse after the weights:

1. Each country's **held** licences in a basin are the records in its states.
2. **Share each pool by water-filling**, with held licences as each country's built levels:
   1. Start with every claimant active and `remaining = pool`.
   2. Each active country's entitlement is `remaining × weight ÷ Σ active weights`.
   3. A country holding at least that many (grandfathered, or after a conquest) is frozen at what
      it holds. It leaves the active set, and its holdings come off `remaining`. Repeat from
      step ii.
   Repeat until no country is newly frozen, which takes at most one pass per claimant: use a
   `while` (`common/scripted_effects/decolonization.txt:271` shows one), not a fixed count. A
   model of this section needed up to 9 passes in randomized worlds. Entitlements are whole
   licences, rounded down, and the leftovers go out by largest remainder so each pool is fully
   shared.
3. **Store** each unbuilt share as entitlement − held.

**Why the pools hold.** Records are made only out of unbuilt shares and move only with their
states. Between passes, a basin's records therefore never exceed the entitlements shared out of
its pool. A frozen country keeps everything it holds, so no licence in use is ever taken away. A
model of this section ran 2,000 random worlds for 60 years each, with building, conquest and
demolition every month, and conquest landing between building and recording. No basin rose
above its pool and no level was left without a licence. Without the owner-change recording, the
same model leaked: 319 basin-years over pool. Under the regulated regime (§ 3) each pool splits in
two, and step 2 runs once per half.

**What can still go over.** Three kinds of levels are recorded where they stand, against no share:
- an old save's levels;
- levels a state brings with it when a split creates it;
- unrecorded levels whose holder was annexed whole.

The water-filling then freezes whoever holds them (grandfathered). Only these can leave a basin
over its pool, and no one gets new room there until it is back under. The third is at most a
month's building.

**The engine fact underneath:** a state keeps its variables when it changes owner. Grand Monuments
relies on the same fact (`docs/superpowers/archive/specs/2026-09-27-grand-monument-rework-design.md`, in-game
check 3), and it is still unverified here. Ship with the self-check `seabed_licence_follows_state`
(§ 8). If it fails, keep the records in global variables per coastal state region (the generator of
§ 2.1 can emit them), with the holder stamp beside them.

**Which licence a level uses** (owner, 2026-10-16: option (a) of § 11 #1):
- Its own basin's first.
- A level on a distant licence (another basin's, because its own basin's share is used up) works
  at −25% throughput, **Long-Haul Seabed Operations**. This is a unit state modifier,
  `building_ocean_mine_throughput_add = -0.25`, applied from `on_yearly_pulse_state` with the
  state's share of distant-licence levels as its multiplier. That is the state pulse, as
  state-scoped scaling requires, and its one refresh site.
- `building_<type>_throughput_add` works at state scope: the mining-region state traits use it
  (`common/state_traits/te_mining_traits.txt`).
- The gate's tooltip says which licence the next level would take, and the penalty if it is
  distant.

### 2.5 Seabed policy

One national policy, not one per basin, changed from the panel (§ 2.7). Influence is held while
the policy stands, as covert operations and UN tabling hold it:

| Policy | Influence in use | Policy factor | Notes |
|---|---|---|---|
| Scientific Survey (default) | none | ×0.25 | |
| Sponsor Contractors | 50 | ×1 | The lawful route under the Law of the Sea. |
| Unilateral Licensing | 150 | ×1, navy ×2 | Defection while the Law of the Sea regulates the seabed (§ 3.3). Otherwise an assertive claim: −10 relations a year with each other Unilateral claimant sharing a basin. |

### 2.6 The building gate

`building_ocean_mine` keeps `is_coastal = yes` and adds, with the game rule on, that the owner
has room. A custom tooltip, as `building_solar_receiver_slots_tt` does, gives:
- the room and the unbuilt share in each basin;
- which licence the next level here would take: local, or distant at −25% (§ 2.4).

The gate itself reads no basin. With the rule off, the building is unchanged.

### 2.7 Display

- **State Panel tile** on coastal states once the owner has Abyssal Plain Mining, beside the
  Solar Collector and Antimatter Facility tiles (`gui/states_panel.gui`): "Seabed licences:
  34 / 40", plus "6 distant" when some are. Hover for the state's own records, each basin's
  licences held and unbuilt, the world's total against each pool, and the weight breakdown.
- **Seabed section** on a Timeline Extended window tab (UN or Economy, builder's call): the
  policy buttons and a row per basin where the country has weight, home or distant, with its
  share, plus the regime (§ 3). Explanations collapsed per `docs/guides/gui_style_guide.md`.

### 2.8 AI

Building needs no AI code (the engine's builder obeys `possible`). Policy is chosen yearly by a
score in one script-values table, as global warming's is (`common/script_values/global_warming_ai_values.txt`):

- **Sponsor Contractors** when that policy would give it at least one licence and Tech-Critical
  Metals sell above base price in its market.
- **Unilateral Licensing** weighted by rank, so mostly great and major powers. More likely with
  low UN standing, a rivalry with a fellow claimant, or a Tech-Critical Metals price above 1.25×
  base. Exemplary UN standing carries a large negative weight, not a ban.
- **Scientific Survey** otherwise.

### 2.9 Game rule and old saves

The rule is `global_commons_rule`, with `global_commons_enabled` (default) and
`global_commons_disabled`. Disabled, the Deep-Sea Mine is uncapped as today, and §§ 3–4 don't
appear. Launch windows and debris (§§ 5–6) belong to the space race and follow `space_race_rule`.
In an old save, the first recording gives every built Deep-Sea Mine level a licence from the
basin it stands in, against no share, and the water-filling grandfathers it. A country over its
share starts with zero room. Where a basin's old levels already exceed its pool, no one else gets
room there until levels go.

## 3. The Law of the Sea governs the seabed (phase 1b)

### 3.1 No new convention

The UN already has the Convention on the Law of the Sea (ITLOS) (`10-united-nations.md:766`;
`un_agency_itlos`). The real convention's Part XI governs the seabed beyond national
jurisdiction, so the seabed terms are added to ITLOS's terms, with no new vote. They sleep until
any country researches Abyssal Plain Mining, and the convention's hover shows them.

### 3.2 Regimes

One global regime, held in a global variable and shown in the Seabed section:

| Regime | When | Allocation |
|---|---|---|
| Open | ITLOS not in force, or the UN rule off | Each pool by weight among all claimants. |
| Regulated | ITLOS in force | Half of each pool, the **reserved half**, by weight among parties whose GDP per head is below the members' average (the World Development Fund's yardstick). The **open half** by weight among all claimants. |
| Scramble | Two or more great powers on Unilateral Licensing while Regulated | The whole pool by weight among all claimants, navy ×2 for everyone. Returns to Regulated two years after fewer than two great powers remain on Unilateral Licensing. |

### 3.3 Under the Regulated regime

- **Royalties.** A party pays, each week, 4% of its Deep-Sea Mine levels' base output value
  (≈ 1,800 a level at the proposed base method). The money goes to the World Development Fund
  where the Fund stands, otherwise to the UN budget. The real draft Mining Code proposes ad
  valorem royalties of a few percent. Dividends can't be taxed directly. Bill it the way UN dues
  are billed.
- **Unilateral Licensing by a party** costs 10 infamy once, 5 standing and 10 case strength
  ("binding resolution refused", `10-united-nations.md` § Grounds for UN censure). It drops the
  country from the reserved half and pays no royalties. Going back to Sponsor Contractors
  restores party status after a 5-year cooldown.
- **Non-parties** (refused ratification, or outside the UN) claim in the open half only and pay
  no royalties. Unilateral Licensing costs them nothing extra beyond § 2.5's relations.

## 4. The Antarctic Treaty (phase 2)

- **Antarctic research station.** A decision for any country with Space Exploration (era 7; the
  real treaty dates from 1959, after the International Geophysical Year). There is no rank or
  coastline gate: the upkeep is the limit, and about thirty countries run real stations. It
  brings a small research modifier (+2% research speed, +25 innovation cap) for a weekly upkeep
  (billed as the mod's other standing programs are; builder's call), and +5 Southern weight
  (§ 2.3).
- **Antarctic Treaty**, a new UN convention, raised on the docket by a country's first station.
  Terms:
  - Parties hold **no Southern licences**: their Southern entitlement is 0, and levels built
    before ratification are grandfathered.
  - Parties with a station gain +3% research speed.
  - The treaty counts +0.25 toward each party's UN Authority Target (Policy pillar).
  - The real Madrid Protocol's mining ban is the point of the convention, so there is no
    separate vote for it.
- **Denunciation** costs 10 infamy, 5 standing and 10 case strength, and takes the country out
  of the treaty. When two or more great powers are out and holding
  Southern licences, the treaty lapses and the Southern basin opens to all.
- With the UN rule off, there is no treaty, and the Southern basin is Open once anyone researches
  Abyssal Plain Mining.

## 5. Launch windows and two-track propulsion (phase 3)

### 5.1 Two tracks

Getting off Earth and moving between planets are separate problems:

| Track | Chemical (default) | Better |
|---|---|---|
| Launch to orbit (cost) | Aerospace Industry rockets | Reusable Rocketry (era 10, already +progress), Space Elevator (era 12) |
| Transport in space (timing) | Hohmann transfers in launch windows | Asteroid Mining (era 11): outside a window at a premium; compact fusion drives (era 12): no windows |

The launch-to-orbit track works through Launch Capacity's price and the Extraplanetary Base
methods (§ 1.2). The transport track works through windows.

### 5.2 What the windows gate

Only **Solar System Colonization** waits for windows. A site can be drawn only while its
destination's window is open: add the window condition to each site's `trigger` in
`sr_establish_colony_effect`.

**Supplies wait in orbit (owner, 2026-10-16).** While no site in the stage has an open window,
the program keeps building: the hardware, habitats and propellant for the next colony fleets go
up and are staged in orbit. In script, nothing new is needed for most of this:

- **The bar keeps filling past the goal, with no cap.** The bar-fill check already keeps the
  overflow (`je_space_race.txt`, "preserve overflow"). Each full goal of staged progress is one
  colony fleet ready to go.
- **When a window opens, the fleets depart.** One colony is founded each month the window is
  open, as long as staged progress covers a goal. A three-month window sends up to three; what's
  left waits for the next window.
- **Staged progress survives a stage change.** If the stage's last sites go to rivals, the fleets
  carry on to the next stage, since the overflow already survives a stage change. Progress still
  staged when the last of the 34 worlds is claimed is lost, as an unfinished bar is today.
- **Setbacks hit only the fleet being readied.** A setback takes its share (×0.75 or ×0.85 and
  the flat amount) of at most one goal, never of the whole stage: loss = share ×
  min(progress, goal). Without this cap, a big staged bank would make every setback ruinous, and
  the player would have a reason to cut funding while waiting.
- **Nothing to manage.** Funding and approach keep running and keep buying progress that will be
  used, so lowering them while waiting only delays the fleets that follow. The bill is the
  hardware being built.

**Not gated:**

- The Moon, which is always reachable.
- The Mars Landing. The arrival-season gate in this spec's first draft is dropped, to leave one
  waiting rule.
- The Deep-Space Probe (its target is chosen after it starts) and the Interstellar Probe.
- Mercury, whose 4-month synodic cycle leaves it nearly always reachable. In reality Mercury needs
  gravity assists rather than windows.

### 5.2a Three steps of propulsion

The owner's ruling (2026-10-16): make the softer version available with more technology, to ease
players into it. The three steps:

| Step | Technology | Launches |
|---|---|---|
| Chemical | Directed Energy Weapons opens colonization (era 11) | In a window only |
| Propellant depots | Asteroid Mining (era 11) | In a window, free. Outside one, at the computed premium, when it saves time (below) |
| Fusion drives | Muon-Catalyzed Fusion Reactors (era 12) | Any month, free |

Asteroid Mining requires Directed Energy Weapons, so it always comes second. It fits the step
historically: water and ore mined in space refill propellant depots in orbit, and the margin they
give is what makes an off-window transfer affordable.

**The premium is the propellant an off-window transfer needs.** The generator's prototype finds,
for each departure date, the minimum Δv over all transfer times. It uses a Lambert solver on the
§ 5.3 orbital elements, departure from low Earth orbit and capture into a loose orbit at the
target. The premium is the rocket equation's extra mass,
`exp(extra Δv ÷ 3.7 km/s) − 1`, at a methane-oxygen engine's exhaust velocity. The minimum for
Mars comes out at 4.45 km/s; the real figure is about 3.6 km/s to depart plus 0.9 km/s to
capture. Premiums by months from a window's optimum (2033–34 cycles):

| Months from the optimum | −6 | −5 | −4 | −3 | −2 | −1 to +1 (window) | +2 | +3 | +4 | +5 | +6 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Mars | +193% | +109% | +64% | +35% | +17% | free | +35% | +51% | +60% | +87% | +183% |
| Venus | +80% | +59% | +40% | +24% | +13% | free | +63% | +149% | +276% | +485% | +864% |
| Jupiter | > +1,000% | > +1,000% | > +1,000% | +925% | +214% | free | +75% | +424% | > +1,000% | > +1,000% | > +1,000% |

**No cap: the computed premium is the price** (owner, 2026-10-16: "given that it is calculated,
should we not cap it?"). The previous draft closed months above +100%. A cap is unnecessary, because
what kept the automatic launch from wasting progress was never the price, but when to pay it.
Paying +400% when the next free window is three months away throws progress away, whatever the
physics allows. So the rule launches outside a window only when that gains time:

- Launching now brings this colony forward by *m*, the months until the stage's next free
  window, the soonest among its unclaimed sites.
- It sets every later colony back by goal × premium ÷ pace months, the extra progress spent at
  the program's monthly pace (`sr_progress`, the panel's figure).
- The approach the program already has decides the trade, with no new control:

| Approach | Launches outside a window when |
|---|---|
| Safe | Never; it waits for the window |
| Standard | goal × premium ÷ pace ≤ *m*: it saves at least as many months as it costs |
| Ambitious | goal × premium ÷ pace ≤ 2*m*: it values the colony now twice as much, in a race for first claims |

**The launch rule.** Each month:
1. Take the stage's cheapest site that passes the approach's test.
2. When staged progress covers goal × (1 + premium), the colony is founded and that much progress
   is spent.

That is still one colony a month. Inside a window the premium is zero, so steps 1 and 2 of the
propulsion ladder behave alike there.

What the rule does on Mars (goal 400; the prototype's premiums; 3 months of the 26 are the window
itself):

| Pace | Standard launches | Ambitious launches |
|---|---|---|
| 5 a month | in the window only (3 months in 26) | also 2–3 months after it (5 in 26) |
| 10 a month | 2–3 months after (5 in 26) | 2–5 months after (7 in 26) |
| 20 a month | 2–5 months after (7 in 26) | 2–6 months after (8 in 26) |
| 40 a month | 2–6 months after (8 in 26) | also 2–3 months before (10 in 26) |

It launches mostly just after a window closes, when the next one is two years away: a program
that missed the window by two months pays +35% rather than waiting two years. It almost never
launches just before a window, since waiting is cheap then. A faster program launches off-window
more often, as its extra progress costs it less time. Expensive months never pass the test at any
plausible pace. The generator stores premiums only up to +100,000%, a ceiling for the script's
number range that no test can reach (it would need a pace above 16,000 a month).

Holding `compact_fusion_reactors` removes every window and premium, for that country only. Fleets
then depart as soon as they are ready, as colonies are founded today.

### 5.3 Computing the windows

`scripts/generators/gen_launch_windows.py` reads Keplerian mean elements and finds, for each
destination, the departure dates of minimum-energy transfers. A departure date *d* is optimal when
the target's true longitude at *d + T* equals Earth's at *d* + 180°, where *T* is half the period
of the transfer ellipse from Earth's radius at *d* to the target's at arrival. Elements:

- Planets: JPL "Approximate Positions of the Planets" (Standish), Table 1, valid 1800–2050 and
  good enough to 2136 for a month's precision.
- Asteroids and Kuiper Belt objects: JPL Small-Body Database osculating elements, two-body.

The window is the optimum's calendar month ±1 (three months). The generator writes, from 1900 to
the game's `END_DATE` (2136.1.1), month-index ranges against `te_history_month_index`:

- `common/scripted_triggers/sr_launch_windows_generated.txt`: `sr_window_open_<body>`.
- `common/script_values/sr_launch_windows_generated.txt`:
  - `sr_window_months_to_next_<body>`, an `if` chain read only by tooltips;
  - `sr_launch_offset_<body>`, the signed months from the nearest optimum, one branch per cycle;
  - `sr_launch_premium_<body>`, a lookup of § 5.2a's premium by that offset. The generator
    averages the Lambert curve over all cycles, reports how far individual cycles stray, and
    stores premiums up to +100,000% (§ 5.2a).

A global monthly pulse caches each body's open/closed state and premium in global variables, so
country pulses and site triggers read one variable each. Window bodies:

- Mars: 26-month cycle, about 111 windows to 2136.
- Venus: 19 months.
- The five asteroid sites: about 15–17 months.
- Jupiter: 13 months.
- Saturn: 12.4 months.
- Uranus, Neptune and the Kuiper Belt: about 12 months.

**The method matches history.** A prototype of the generator, using planets only, put every Mars
launch since 1964 inside its computed window:

| Mission | Launched | Computed optimum | Window |
|---|---|---|---|
| Mariner 4 | 1964-11-28 | 1964-11-23 | 1964.10–1964.12 |
| Mariner 9, Mars 2 and 3 | 1971-05-30 | 1971-06-06 | 1971.05–1971.07 |
| Viking 1 and 2 | 1975-08-20 | 1975-09-13 | 1975.08–1975.10 |
| Mars Global Surveyor, Pathfinder | 1996-11-07 | 1996-12-01 | 1996.11–1997.01 |
| Spirit, Opportunity, Mars Express | 2003-06-10 | 2003-06-24 | 2003.05–2003.07 |
| MRO | 2005-08-12 | 2005-08-16 | 2005.07–2005.09 |
| Phoenix | 2007-08-04 | 2007-09-19 | 2007.08–2007.10 |
| Curiosity | 2011-11-26 | 2011-11-19 | 2011.10–2011.12 |
| MAVEN, Mangalyaan | 2013-11-05 | 2013-12-22 | 2013.11–2014.01 |
| ExoMars TGO | 2016-03-14 | 2016-02-08 | 2016.01–2016.03 |
| InSight | 2018-05-05 | 2018-05-18 | 2018.04–2018.06 |
| Perseverance, Tianwen-1, Hope | 2020-07-30 | 2020-07-30 | 2020.06–2020.08 |

Venus (Venera 7 and 9, the Pioneer Venus multiprobe, Vega, Venus Express) and Jupiter (Pioneer 10
and 11, the Voyagers, Juno) launches all fall within four weeks of their computed optima too.
Mars windows in era 11 (about 2030–2060), for scale. Arrival is for the colony event's text only
("the fleet reached Mars in November"); nothing waits on it:

| Window | Arrival | | Window | Arrival |
|---|---|---|---|---|
| 2030.12–2031.02 | 2031.09 | | 2045.12–2046.02 | 2046.09 |
| 2033.03–2033.05 | 2033.11 | | 2048.01–2048.03 | 2048.10 |
| 2035.06–2035.08 | 2036.04 | | 2050.05–2050.07 | 2051.02 |
| 2037.07–2037.09 | 2038.06 | | 2052.07–2052.09 | 2053.05 |
| 2039.08–2039.10 | 2040.07 | | 2054.08–2054.10 | 2055.06 |
| 2041.09–2041.11 | 2042.07 | | 2056.09–2056.11 | 2057.07 |
| 2043.10–2043.12 | 2044.08 | | 2058.10–2058.12 | 2059.08 |

### 5.4 Display and AI

- While a full bar waits, the overview's approach row reads **Staged in orbit: 1.4 fleets**, the
  staged progress in goals. Hover it for each candidate destination's months to its next window,
  that the fleets depart one a month while a window is open, and that compact fusion drives
  remove launch windows.
- Mission Control gains a **Next windows** line listing the stage's destinations with the months
  to each. After Asteroid Mining, each also shows today's premium when it is open, as in "Ceres:
  +35% now, window in 4 months". It also says whether the approach would launch there now, with
  the months it would save against the months it would cost.
- AI: no change. It keeps funding, and staged progress means waiting costs it only time.

## 6. Orbital debris (phase 4)

### 6.1 The index

Two global variables, because real debris splits by altitude:

| Pool | Decay | Real basis |
|---|---|---|
| `orbital_debris_low` | 1.5% a month (half-life ≈ 4 years) | Below ~600 km, drag clears debris in years (most of Kosmos 1408's fragments, 2021, re-entered within three years). |
| `orbital_debris_high` | 0.05% a month (half-life ≈ 115 years) | Higher orbits keep it for a century (Fengyun-1C, 2007, at 865 km). |

The **index** is low + high, capped at 100. Sources:

- Each running Space Program adds +0.01 low a month. Background traffic settles near 4 points
  with six programs.
- Each anti-satellite strike adds +6 low and +6 high (§ 6.3).
- **Kessler cascade:** at index ≥ 75, collisions add +0.2 high a month on their own until removal
  outpaces them.

A global monthly pulse updates the pools. Tiers, for text only: Clear (< 25), Cluttered (25–49),
Hazardous (50–74), Kessler Cascade (75+).

### 6.2 What debris does

One unit static modifier, `te_orbital_debris`, applied from the monthly country pulse (its one
refresh site) with `multiplier` = the index. It goes to every country that uses orbit: a Space
Program, any orbital megaproject or an Extraplanetary Base.

| Per index point | At 50 | At 100 |
|---|---|---|
| `country_space_race_risk_mult` +0.01 | +50% setback risk | +100% (risk still clamps at 50%) |
| `country_space_race_progress_mult` −0.003 | −15% pace | −30% pace (floor 0.5 a month) |
| Throughput −0.002 on `building_space_mine`, `building_solar_collector`, `building_orbital_battlestation`, `building_space_elevator` | −10% | −20% |

At Hazardous and above, a Space Elevator owner rolls each month (index × 0.02%, so 1.5% at 75)
for a **ribbon strike** event: −50% elevator throughput for six months, or pay to repair it in
two.

Nothing halts. The space race can't stop, pace has a floor, and every penalty clears as debris
does.

### 6.3 The anti-satellite strike

A diplomatic action, `te_asat_strike_action`, on the `nuke.txt` pattern:

- **Needs:** at war with the target, Guided Missiles (era 7; the Soviet and US tests of
  1968–1985 were era 7–8), the striker's own Space Program, and a target with a Space Program
  or an orbital megaproject. Not used against this target in the past 12 months.
- **The target** gets `te_orbital_network_disrupted` for 12 months: −10% unit offense and defense,
  −20% space race progress, −25% orbital megaproject throughput. Orbital Battlestations halve it,
  and a Space Program on the Mars Mission method or higher shortens it to 6 months
  (reconstitution is automatic, with no clicks).
- **The striker** pays 5 infamy, a new case-strength ground "Destructive anti-satellite strike:
  15" (`10-united-nations.md` § Grounds for UN censure), −30 relations with every other country
  that uses orbit, and the debris it shares with everyone.
- **Non-kinetic interference stays the existing covert operation Communications Disruption**,
  unchanged.
- **AI:** low base weight. The weight is zero unless the enemy's orbital investment (Space Program
  tier plus orbital megaproject levels) exceeds the AI's own, and near zero at index ≥ 50 unless
  the AI is losing the war. These are AI weights, not rules: a player faces only the action's own
  requirements.

### 6.4 Cleanup

A new secondary method group on `building_space_program`, `pmg_space_program_debris_removal`.
Each method carries a registered country modifier, `country_orbital_debris_removal_add`
(workforce-scaled, in the method's `country_modifiers`), and a little prestige:

| Method | Gate | Launch Capacity a week | Removal a month | Launch Capacity per point removed |
|---|---|---|---|---|
| None (default) | | 0 | 0 | |
| Active Debris Removal | Reusable Rocketry (era 10) | 300 | 0.05 | ≈ 26,000 |
| Laser Broom | Directed Energy Weapons (era 11) | 300 (+ electricity) | 0.15 | ≈ 8,700 |
| Fusion Sweepers | compact fusion drives (era 12) | 150 | 0.5 | ≈ 1,300 |

- **The Space Elevator doubles removal**: each fully staffed level adds +10% to
  `country_orbital_debris_removal_mult`, up to +100%. Its own Launch Capacity output also makes
  every method cheaper in its market. With fusion drives and an elevator, one program clears 30
  points in about 2.5 years. With early active removal, a cascade is beyond any one country.
- The global monthly pulse sums every country's removal and takes it from the high pool first
  (real removal missions target large, long-lived objects).
- **Prestige for cleaners**, +1% per 0.1 removal a month, makes cleanup more than charity.
  Everyone benefits from a cleaner's work, which is the commons dilemma.
- **AI:** turns removal on when the index is ≥ 25 and it uses orbit, more readily at ≥ 50, and
  picks the best method it has.

### 6.5 The UN

- The anti-satellite case ground (§ 6.3).
- A docket situation, "A destructive anti-satellite strike", raises a new convention, the
  **Moratorium on Destructive Anti-Satellite Tests** (the UN General Assembly's 2022 resolution
  77/41). Terms:
  - a party's strike costs double infamy and twice the case strength;
  - parties gain prestige;
  - parties with a removal method count toward the Delivery pillar, as aid delivered does.

## 7. Cross-system effects

- **Seabed ↔ asteroids.** Capping the seabed is what gives the asteroid route its value: a
  landlocked power can buy its way around the Pacific's naval powers in era 12.
- **Debris ↔ Solar Collector, Battlestation and Space Elevator.** The megaprojects that most
  use orbit are hit hardest, which gives their owners reason to clean.
- **Existing events.** Space race event `.31` (Orbital Debris Concerns) can read the index
  (more likely, and named by tier, at Cluttered and above). Optional.

## 8. Tests, docs, in-game checks

- **Tests:**
  - `test_seabed_basins.py`: every coastal state maps to a basin, and the generated file is
    current.
  - `test_launch_windows.py`:
    - the historical launch table in § 5.3 stays inside its windows;
    - each premium curve's minimum falls in its window's middle month;
    - § 5.2a's Mars table comes out of the break-even rule;
    - the generated files are current.
  - `test_deep_sea_rebalance.py`: per-level base-price profit of the Deep-Sea Mine ≥ the
    Extraplanetary Base's for every method pair without the two logistics upgrades, and less
    with both (§ 1.2's table).
  - `test_seabed_allocation.py`: a Python model of § 2.4 (records, unbuilt shares, monthly and
    owner-change recording, water-filling), run over randomized worlds with building, conquest
    and demolition. No basin's records exceed its pool, every level stays licensed, a basin over
    its pool (old saves) never grows, and a power with no coast in a basin gets a small share
    there. The scratch model behind § 2.4's claims is the starting point. The script's numbers
    follow the model, as the demographics census's do.
- **Audits:**
  - `loc_coverage_audit` for every new key.
  - `modifier_visibility_audit`.
  - `je_immediate_reset_audit`: the seabed state lives in country and global variables, so a
    revolution's winner keeps its entitlements and policy.
- **Docs:**
  - `docs/systems/mod_systems.md`: new Global Commons section; Space Race § Key Mechanics for
    windows and debris.
  - `docs/auto_generated_files.md` and the post-load rosters for the two generators.
  - Player guide chapters: 02 (Deep-Sea Mine row), 10 (ITLOS terms, Antarctic Treaty, the
    moratorium, the new case ground), 16 (windows, debris, cleanup, the anti-satellite strike),
    17 (reference).
- **Self-checks** (`TE_SELF_CHECK`, pattern in `CLAUDE.md`):
  - `seabed_cap`: each basin's recorded licences ≤ its pool, and every Deep-Sea Mine level is
    recorded, once a year after the first allocation.
  - `seabed_licence_follows_state`: the first time a state with recorded licences changes owner,
    OK when its `te_seabed_lic_*` and holder stamp read back inside `on_state_owner_change` and a
    month later; BROKEN otherwise. Fallback: § 2.4's per-region global records.
  - `window_gate`: no colony founded while its body's window is closed.
- **Play-test list:**
  - the State Panel tile;
  - a Deep-Sea Mine level on a distant licence, its long-haul penalty, and the swap to a local
    licence once one frees up;
  - a conquered state's licences arriving with it;
  - fleets staged in orbit departing when the window opens, and a setback while fleets are
    staged;
  - an off-window launch after Asteroid Mining;
  - a ribbon strike;
  - a Kessler cascade cleared by Fusion Sweepers.

## 9. Phasing

| Phase | Contents | Depends on |
|---|---|---|
| 1 | § 1 (rebalance and the Extraplanetary Base logistics methods), § 2 (basins, pools, weights, entitlements, policy, gate, tile, AI) with the Open regime only | — |
| 1b | § 3 (ITLOS seabed terms, Regulated and Scramble regimes, royalties) | 1, UN rule |
| 2 | § 4 (stations, Antarctic Treaty) | 1b |
| 3 | § 5 (launch windows, staging in orbit, off-window launches after Asteroid Mining) | — (independent of 1) |
| 4 | § 6 (debris index, effects, anti-satellite strike, cleanup methods, the UN moratorium) | — |

Phases 3 and 4 can run in parallel with phase 1.

## 10. Out of scope (later)

- **"Seize Seabed Claims" war goal** (owner: later phase). A custom goal on an existing `kind`
  (`humiliation` is the likely carrier) whose `on_enforced` moves part of the loser's
  entitlement to the winner, plus a `dp_` play type.
- A nuclear-thermal propulsion tier between chemical and fusion, which would widen windows to
  half of each cycle.
- Pools that grow with world technology.
- Basin yield flavor (per-basin output modifiers need one registered type per good).
- A non-kinetic satellite-jamming covert operation separate from Communications Disruption.

## 11. My calls, for the owner to check

1. **Where a licence can be used: decided** (owner, 2026-10-16: option (a), local first and
   distant at a penalty, § 2.4). Still to tune:
   - the long-haul penalty (−25% throughput);
   - the distant-basin claim penalty of § 2.3 (a twentieth of the navy, no coast or ports, +5
     for an Antarctic station).
2. **Pools are fixed** (1,000 levels in all). Growth with technology is listed as later work.
3. **The Deep-Sea Mine's numbers** (§ 1.1): ~103% margin at the base method and ~250% with
   Advanced Nanofabrication. These are high, but each level is a scarce licence. Alternatively,
   raise the era-12 inputs to bring it near the land mines' ~170%. That would move the
   era-12 parity point in § 1.2.
4. **The logistics methods gate on technology, not on owning a Space Elevator.** Methods can't be
   gated by a building. The elevator's owner is rewarded through Launch Capacity prices and
   debris removal.
5. **Staged fleets depart one a month** while a window is open, with no cap on what can be
   staged. The alternative, every ready fleet leaving in the window's first month, is quicker
   but fires several colony events at once.
6. **Off-window launches** (§ 5.2a). The owner asked for them to unlock with more technology,
   and for no cap. Still to check:
   - Asteroid Mining as the middle step.
   - The break-even test's weights: Standard launches when it saves at least as many months as
     it costs, Ambitious when it saves at least half as many. Safe never launches off-window.
   - A methane-oxygen exhaust velocity (3.7 km/s) in the premium. A hydrogen-oxygen one (4.4)
     would make every premium a sixth to a fifth smaller.
7. **Royalties of 4% of output value**, to the World Development Fund.
8. **The anti-satellite strike starts at Guided Missiles (era 7)**, as history did, rather than
   at Space Militarization (era 11).
