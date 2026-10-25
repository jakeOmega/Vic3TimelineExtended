# Solar System Colonization, slices 2 and 3: colony population and colony fleets that travel — design

Drafted 2026-10-25. Slices 2 and 3 of the scope in
`2026-10-25-solar-colonization-contest-scope.md` (§ 10), whose § Decisions and
§ 11 record the owner's calls; this design assumes them and the colony record
of slices 0 and 1 (`2026-10-25-solar-colonization-holders-and-cession-design.md`).
Slice 2 gives every colony a head count, an emigration programme with
per-colony priorities, crews and Artificial General Intelligence (scope § 7).
Slice 3 gives the launch-window generator transit tables for four drives, and
makes a colony fleet pick its world, travel and claim it on arrival, with
distance in place of the five stages (scope §§ 5.3, 5.6). There is no separate
plan: § 14 is the build order.

## Intent

After these two slices:

1. **Every world can be targeted** (all settings but off; the owner's D19). The
   Solar System list has a Target button on each world the programme may
   claim; without a target, the programme picks as before (races only) or by
   score (simple and full).
2. **Under simple and full, a colony fleet travels.** It leaves with the transit
   time its drive buys, from 4 months to Mercury by chemical rocket to 45 years
   to the Kuiper Belt, and claims its world when it arrives, not when it
   leaves. A world taken before it arrives sends it to another free world of
   the same body; with none, the investment is lost. The five stages stop
   being locks: distance is the lock.
3. **Four drives** (chemical, fusion, fusion torch, antimatter) set the transit
   time, from tables the launch-window generator computes from the same
   ephemerides and Lambert solver as the windows.
4. **Under simple and full, colonies hold people.** Each world has a head count
   that grows slowly up to its room and rises with emigration from Earth: one
   national programme (Off, Low, Steady, High) taking people from the Space
   Program's state, shared out by each colony's priority (Closed, Low, Normal,
   High) times its free room. People are crews: each colony shows how many
   module levels its people can run, which slice 4's modules will need;
   Artificial General Intelligence removes the need. The nation's off-world
   population gives a small prestige and cultural pull bonus.

## Non-goals

Modules, Habitat room, Extraplanetary Bases from colonies (slice 4); free
colonies, autonomy, abandonment, colony life events (slice 5); warfleets,
blockades, sieges, destruction and evacuation (slice 6). Emigrants are not in
transit: they count on arrival the month they leave, until blockades can
intercept them (slice 6). Emigration policies by culture are later (scope § 7).
Races only keeps the stages and instant founding; it gains only the Target
button.

## Engine facts

**Rests on:**

- `kill_population_in_state = { value = N strata = S }` with a constant N, in a
  `while = { count = local_var:x }` loop (`resettlement_effects.txt:306`).
- `state_population` reads as a script value in state scope
  (`colonial_empire_values.txt:1768`).
- `random_scope_building` with `is_building_type` in country scope, and a
  building's `state` link (`te_aipm_selfcheck_on_actions.txt:43`).
- A scripted GUI receives a number through `AddScope('x', MakeScopeValue(...))`
  and reads it as `scope:x = N` (`space_race_sguis.txt`, `scope:op`).
- `$PARAM$` substitution in variable names (`sr_discovery_$DISCOVERY$_pending`).
- Local variables are visible in the scripted effects a block calls
  (`sr_cede_matched`, set in `sr_cede_colony_apply`'s branches, read by
  `sr_cede_colony_self_check`).
- A static modifier on the journal entry at `multiplier =`, removed first
  (`sr_funding_progress`, the dynamic-modifier scaling pattern in `CLAUDE.md`).
- A modifier that raises a building type's throughput raises its input bill:
  funding's `building_space_program_throughput_add` (scope § 2, "Upkeep as an
  input multiplier").
- People removed by script and not booked as known kills are read by the
  Demographics census as emigrants (`te_demog_note_kills`'s header), which is
  what they are: the census counts emigrants as an exit without any change.

**Unverified, each with a self-check (§ 12):**

- That `kill_population_in_state` with a `strata` filter removes the whole batch
  from a capital state (it should: the state holds millions), and how soon the
  state's population reads the change.
- That a fleet's arrival month, set at departure from the cached transit table,
  is the month it is processed (the global step's order against the countries'
  pulses).

## 1. Drives

A country's drive is the best of four, `sr_drive_level` (country value):

| Level | Drive | Needs | Departures |
|---|---|---|---|
| 0 | Chemical | (the Space Program) | In a window; outside one at the premium with Asteroid Mining, when the approach's test passes (unchanged) |
| 1 | Fusion | `fusion_power` (era 11, military) | As chemical: windows still matter |
| 2 | Fusion torch | `compact_fusion_reactors` (Muon-Catalyzed Fusion Reactors, era 12) | Any month (today's "fusion drives" rule, unchanged) |
| 3 | Antimatter | `antimatter_production` and an Antimatter Containment Facility (`building_antimatter_facility`) | Any month |

The window rule's `sr_launch_has_fusion` gains the antimatter drive, so the two
fastest drives both leave any month. That is the one change under races only
besides the Target button; antimatter without the torch is a rare pairing
(different prerequisites in era 12).

## 2. Transit tables (the launch-window generator)

`gen_launch_windows.py` computes, for every window body and for Mercury, the
transit months each drive buys, from the ephemerides and Lambert solver it
already has:

- **Chemical**: the body's Hohmann time, the median of its windows' transfer
  times over the span: 4 months to Mercury, 5 to Venus, 9 to Mars, 13 to 18 to
  the asteroids, 33 to Jupiter, 73 to Saturn, 192 to Uranus, 369 to Neptune,
  611 to the Kuiper Belt. The scope's "chemical era's times, unchanged". An
  off-window departure pays its premium in propellant and flies the same
  transfer.
- **Fusion**: the shortest time of flight whose delta-v (departure from a
  parking orbit plus capture, as the premium's) is within a budget of
  30 km/s, from a Lambert grid down to a twentieth of the Hohmann time; by
  signed months from the optimum, averaged over the 16 sampled cycles as the
  premium is, and never above chemical. In a window: 2 to 3 months to Mars,
  7 to 9 to Jupiter, 16 to 18 to Saturn, about 3 years to Uranus, 5 to Neptune,
  11 to 25 to the Kuiper Belt; off-window it falls back towards chemical. Windows still
  matter for the far worlds.
- **Fusion torch**: a brachistochrone (accelerate to the midpoint, decelerate
  the rest) at 0.01 g with a 400 km/s delta-v cap (coasting at half of it when
  the cap binds), over the distance from Earth at departure to the body at
  arrival, by offset: about 1 month to Mars, 2 to Jupiter, 4 to Saturn, 6 to
  Uranus, 9 to Neptune, 12 to the Kuiper Belt. "Months to the outer planets."
- **Antimatter**: the same at 0.03 g and 2,000 km/s: 1 to 4 months anywhere.

Every figure is rounded to whole months, at least 1. Mercury, never gated, has
one figure per drive (its mean over every month). The generated
`sr_transit_<drive>_<body>` read `sr_launch_offset_<body>` (a binary search, as
the premium is); the monthly window cache stores this month's
(`sr_window_transit_<drive>_<body>`), and the country reader
`sr_transit_months_<body>` picks its drive's. The report
(`docs/engine/launch_windows_report.md`) gets a transit section: every body,
drive and offset.

## 3. Targets (all settings but off)

- **The record**: `sr_cf_target` on the country, a world's index in the site
  table; absent means automatic.
- **Targetable** (`sr_cf_targetable_<key>`, generated, country scope): the world
  is unclaimed and
  - races only: its stage is at most the current stage (the draw's own
    candidates: the stage's worlds and any released world of an earlier one);
  - simple and full: its stage is at most 2, or the country has Deep Space
    Exploration (`country_sr_deep_space_exploration_program_bool`), or holds a
    colony: today's outer-system rule, read per world instead of per stage.
- **The panel**: each Solar System row of a world we may target has a Target
  button while our programme runs (`sr_solar_colonization_running`); our
  target's row reads Our Target and its button clears it. A new Colony Fleets
  section names the destination: our target, or Automatic.
- **A target lost** (claimed by a rival before we launch) is cleared at the next
  launch month and the programme goes back to automatic; the panel shows it.

## 4. Launching

`sr_launch_month` (the entry's monthly pulse, unchanged entry point) branches on
the rule.

**Races only.** With a valid target whose body can depart (`sr_launch_target_cost_<body>`
below the never value) and staged progress covering its cost, the target is
founded at once (`sr_site_found_now_<key>`, the draw's branch body with the
window gate check), and the rest of the launch is today's: spend, the charter,
the stage check. Without a target, today's random draw.

**Simple and full** (`sr_cf_launch_month`):

1. A free fleet slot is needed (six, § 6); with none, the bar waits.
2. **Target mode**: the target departs and progress covers its cost → dispatch.
3. **Automatic**: among the worlds that are targetable, can depart now and are
   affordable, the best score (§ 7) within a 15-year horizon → dispatch.
4. **Dispatch** (`sr_cf_dispatch_<key>`): spend the world's cost (its stage's goal
   × (1 + its body's premium)), fill the slot (world, departure month, arrival
   month = now + `sr_transit_months_<body>`), run the window gate self-check for
   the body, and add the fleet to the world's inbound record (§ 8).

At most one fleet a month, as today. A world's cost uses its own stage's goal
(400 to 650): the outer worlds cost more as well as taking longer.

**A targeted departure outside a window** (`sr_launch_target_departs_paid`): the
approach's test against the target body's own wait, k × its months to its
window, not the stage's soonest window: the programme has chosen where to go.

## 5. Arrival

The global monthly step (`sr_sites_global_monthly`) first lands every fleet
whose arrival month has come (`sr_cf_arrivals_country` on every country with a
fleet in flight), then runs the per-world step as before. A fleet arriving at:

- **its world, unclaimed**: founds it (`sr_site_found_<key>`, the founder as
  `this`): claim, holder, sync, discovery seeds, the founding event; then the
  entry opens if it has none, the first-colony charter, the stage recompute (§ 9),
  every player's Solar System snapshot;
- **its world, taken**: founds the first unclaimed world of the same body
  (Mars's five, Jupiter's six, Saturn's five, Uranus's four, Neptune's two, the
  Kuiper Belt's five), and a player gets `space_race_events.92`, diverted;
- **its body full**: the fleet is lost, and a player gets `.92`, lost.

Two fleets arriving the same month: the first processed takes the world.

## 6. Fleet slots

Six per country (`sr_cf_<n>_site`, `_depart`, `_arrive`; `sr_cf_in_flight`
counts them). A revolution's winner inherits them with the other variables, so
its fleets fly on; a dead country's are gone. A programme that stops (its
method off, its rank lost) keeps its fleets in flight: they were paid for.

## 7. The automatic pick (simple and full)

Per world, `sr_cf_score_<key>` (generated, country scope):

    100 − 10 × stage − transit months ÷ 2 − 40 × premium − 10 × fleets inbound
        − 60 if another country's fleet arrives there first

Eligible: targetable, departs now (cost below never), cost covered by staged
progress, arrival within 180 months. The highest score is dispatched, the
earlier world in table order on a tie. So a chemical programme takes Mars and
the asteroids, then Jupiter, and waits for fusion before Uranus (192 months by
chemical), as the owner's "sending a colony to Uranus by chemical rocket when
fusion torches are ten years off may be foolish" wants. The AI and a player who
set no target pick alike; a player can target past the horizon by hand.

## 8. In transit, visible

- **Inbound record** (global, per world): `sr_site_inbound_<key>` (fleets on
  their way), `sr_site_inbound_first_<key>` (the earliest arrival month) and
  `sr_site_inbound_by_<key>` (its country). Added to at dispatch, rebuilt from
  every country's slots by the global monthly step after arrivals, so a fleet
  that landed, or a country that died, drops out within a month.
- **Panel**: Colony Fleets lists our six slots (the world, the drive's transit,
  arrival year and months left); the Solar System rows of unclaimed worlds show
  the fleets on their way, with the first's arrival and whether it is ours.

## 9. The stage under simple and full

The stages stop being locks, but the global stage still names how far out the
free worlds are. After each founding, and monthly, `sr_sites_recompute_stage`
sets it to the lowest stage with an unclaimed world, and sets
`sr_all_colonies_complete` once none is left (worlds can now be claimed out of
order, so today's step-by-one stage check would stall). Races only keeps today's
stage check. Its readers:

- `sr_solar_colonization_goal`: with a target under simple and full, the
  target's stage goal; otherwise the global stage's, as today.
- `sr_window_body_in_play_<body>` (generated): under simple and full a body is in
  play while it has an unclaimed world, whatever the stage.
- The entry's `possible` and the two mission decisions read
  `sr_colonization_inner_open` (races only: stage at most 2, as today; simple and
  full: an unclaimed world of stage 1 or 2), in place of their stage tests.

## 10. Population (simple and full)

### 10.1 The record

| Variable | Holds | Written by |
|---|---|---|
| `sr_site_pop_<key>` (global) | the colony's people | emigration, growth; cleared by a release |
| `sr_emig_level` (country) | the programme: 0 Off, 1 Low, 2 Steady, 3 High | the panel, the AI |
| `sr_emig_prio_<key>` (country) | the holder's priority for the colony: 0 Closed, 1 Low, 2 Normal (absent), 3 High | the panel; cleared when the colony leaves it |

The people live on the world's record, so a cession or an heir takes them with
it; the priority is the holder's, so a new holder starts at Normal. A founded
colony starts at 0, an automated outpost. A released world loses its people
(slice 5's free colonies will keep them).

### 10.2 Room and growth

Each world's **room** comes from the site table (`room`, in thousands): 10,000
(Himalia, Amalthea, Mimas, Miranda, Proteus, Eris, Makemake, Haumea, Sedna) to
50,000 (Valles Marineris, Hellas and Utopia Planitia), 810,000 in all. Slice 4's
Habitat module adds to it. **Growth** is 0.2% a month (about 2.4% a year) up to
the room, from the global monthly step.

### 10.3 Emigration

Monthly, from the entry's pulse, for a country with the programme on, a Space
Program and a held colony with free room:

- **How many**: Low 500 a month, Steady 1,000, High 2,000, in batches of 500
  (250 middle strata and 250 lower, `kill_population_in_state`, from the Space
  Program's state), never more than the colonies' free room.
- **Where**: each held colony's share is its weight over the sum, weight =
  priority weight (Closed 0, Low 1, Normal 2, High 4) × free room. So a player
  building up Mars sets Mars High and Venus Low and touches nothing else, and a
  full colony takes no one.
- **Upkeep**: `sr_emigration_programme` on the entry, at multiplier = the level:
  `building_space_program_throughput_add` +5% a level, the Space Program's
  Launch Capacity bill (funding's precedent, +25% a level).
- **The census**: the people taken read as emigrants in the Demographics
  census, which is what they are.

### 10.4 Crews and AGI

People are crews. Each colony's **crews**, `sr_site_crews_<key>`, are the module
levels above the first its people can run, one per 5,000 people. Until slice 4
there are no modules to crew: the colony runs its specialization as an
automated outpost, and the panel shows the crews it could field. With
`artificial_intelligence` (Artificial General Intelligence, era 12), modules
need no crews at all and the panel says so; slice 4 reads both.

### 10.5 The off-world population

`sr_offworld_population` on the entry: +1% prestige and +2% cultural pull per
100,000 of the nation's people off Earth, at most ten times (+10%, +20%: about
Interplanetary Trade Networks' size, for a million people). Re-applied monthly
from the entry's pulse (its one refresh site), removed first.

### 10.6 AI

Each January, from the entry's pulse: Off in default or with no held colony
with room; Steady when it is among the space race's top three
(`sr_ai_should_participate`) and its weekly income is positive; Low otherwise.
Priorities stay Normal: the weights by free room already fill the emptiest
colonies first.

### 10.7 The panel: Settlers

A new section after Our Colonies, simple and full only: the programme with − and
+ (its emigrants a month and the Space Program's state), the off-world
population and its bonus, crews or AGI, then one row per held colony: its icon
and name, people and room, crews, and its priority (click to step Closed → Low
→ Normal → High).

## 11. Notices

`space_race_events.92` (players): a colony fleet arrived to find its world taken
(diverted, naming the world it founded instead, or lost). The founding itself
is the world's own event, as today.

## 12. Self-checks and the play-test list

Added to `docs/testing/solar-colonies-playtest.md`:

- **`colony_fleet_arrival`**: the first fleet that lands logs its world, its
  departure and arrival months and the months it flew against the transit the
  table gives; BROKEN if a slot's arrival month is more than a month past
  (a fleet the step missed).
- **`emigration_batch`**: the first month's emigration logs the Space Program
  state's population before and after its batches; OK when it fell by at least
  90% of what was sent, BROKEN otherwise.

The play-test list adds what script can't see: the Target button and the
Settlers and Colony Fleets sections in the panel; the drive's effect on a
dispatch's arrival; the census's emigrant line in the Space Program's state.

**Console** (`te_debug_space_race.2` gains options): log our fleets and every
world's inbound record; land our fleets now; set the emigration programme to
High and run a month; log every colony's people.

## 13. My calls, for the owner to check

1. **Fusion's budget is 30 km/s, the torch 0.01 g and 400 km/s, antimatter 0.03 g
   and 2,000 km/s.** First guesses that give the scope's shapes (windows still
   matter with fusion; months to the outer planets with the torch); tune in
   play.
2. **Chemical transit is the body's median Hohmann time whatever the month**: an
   off-window launch pays for its departure, not for a faster trip.
3. **Antimatter leaves any month under every setting**, as the torch does.
4. **A world's colony cost follows its own stage** under simple and full (400 to
   650): the outer worlds cost more as well as taking longer.
5. **The automatic pick's horizon is 15 years**, for players and the AI alike; a
   player can target past it.
6. **Six fleet slots**; with all in flight the bar waits.
7. **A diverted fleet takes another world of the same launch-window body**: on
   Mars, Jupiter, Saturn, Uranus, Neptune and the Kuiper Belt there are others;
   at each asteroid, Venus and Mercury there are none, and the fleet is lost.
8. **Emigrants travel instantly** until blockades exist to stop them (slice 6).
9. **Emigrants are half middle, half lower strata.**
10. **Until slice 4, crews are shown, not used**: the specialization stays at
    level 1, the automated outpost, so no modifier changes with people. The
    off-world bonus is slice 2's payoff.
11. **A released world loses its people** until free colonies exist (slice 5).
12. **The AI keeps every priority at Normal.**
13. **Room totals 810,000**, before slice 4's Habitats; the bonus caps at a
    million people, so it needs Habitats to reach.

## 14. Build order

1. Transit tables and drives in `gen_launch_windows.py`; the cache; the report;
   `test_launch_windows.py`.
2. The site table's `room`; generated founding (`sr_site_found_<key>`,
   `sr_site_found_now_<key>`), targetability, costs, scores, dispatch, arrival,
   inbound record, the stage recompute; the hand-written launch, slots, arrival
   loop, notices; `test_solar_sites.py`.
3. Population: the record, growth, emigration, crews, the bonus, the AI.
4. The panel: the Solar System rows move into a generated file
   (`gui/journal_entry_widgets/sr_sites_generated_rows.gui`) with the Target
   button and the inbound marker; Colony Fleets and Settlers; scripted GUIs.
5. Docs, the player guide, the play-test list, CI's checks.

## 15. As built (2026-10-25)

Where the build departs from the sections above, and why:

- **The Solar System rows are generated now** (`te_sr_solar_system_rows` in
  `gui/journal_entry_widgets/sr_sites_generated_rows.gui`, with the Settlers rows
  and the Colony Fleets slot rows): every row gained the Target button and the
  inbound marker, and the generator already holds the table they follow.
  `test_solar_sites.py` reads them there; `test_space_race_labels.py` and
  `test_space_race_layout.py` read both files.
- **The inbound marker reads "count·months"** (§ 8): the fleets on their way and
  the months until the first lands, in a brighter color when the first is ours. A
  rival's name would need a capital snapshot per world, as the holder's flag has,
  and the row has no room for a second flag.
- **A target can be cleared while the programme is idle**; choosing one needs it
  running (`sr_colony_target_sgui`).
- **Fusion's Lambert grid runs from 0.05 to 2.6 times the Hohmann time**, 48
  points refined by bisection, and every drive's departure is on the 15th of its
  month. A better drive is never slower than the one before it.
- **The automatic pick tests the goal alone before the window** (`sr_cf_eligible_<key>`),
  so a month whose bar covers no world skips the 34 departure checks.
- **The Off-World Population modifier waits for 1,000 people**
  (`sr_offworld_bonus_minimum`), so a colony's first batch doesn't post a modifier
  worth a hundredth of a percent.
- **The console is a new event**, `te_debug_space_race.3`, rather than more options
  on `.2`.
- **The automatic pick's −60 counts every fleet on its way** (§ 7), ours
  included: `sr_cf_beaten_<key>` reads the world's inbound record, which holds
  every country's fleets. A second fleet of ours to a world one of ours already
  reaches first would arrive to find it taken.
- **Emigration shares run in passes** (§ 10.3, `sr_emig_distribute`). A colony
  capped at its free room passes the rest on, and the next pass shares what is
  left among the colonies with room, so every settler sent lands; the month never
  sends more than the open colonies' room. One pass capped shares and dropped the
  excess, so people left Earth and landed nowhere when the room ran short.
- **The entry's modifiers refresh once per effect.** `sr_emig_set_level` doesn't
  refresh them; its callers do (the Settlers button, and the entry's pulse after
  the AI's review), because whether `has_modifier` sees an `add_modifier` made
  earlier in the same effect is unverified, and a second refresh could stack a
  copy.
- **Number range.** The weights (priority × free room, people) and the capital
  state's population stay far inside the script's 64-bit fixed point
  (`scripting_best_practices.md`, units of 1e-5, a ceiling near 9×10^13);
  `sr_launch_window_values.txt`'s "about two million" is that file's own,
  stricter budget.
