# Solar System Colonization, slice 6: fleets, combat and Earth orbit — design

Drafted 2026-10-26 from an interview with the owner. Slice 6 of the scope in
`2026-10-25-solar-colonization-contest-scope.md` (§ 10, "the fleets phase":
§ 5 and §§ 6.2–6.3), whose § Decisions and § 11 record the owner's earlier
calls; the interview's answers are below and in the scope's § 11 (fifth
round). This design assumes the records of slices 0 to 5
(`2026-10-25-solar-colonization-holders-and-cession-design.md`,
`2026-10-25-solar-colonization-population-and-transit-design.md`,
`2026-10-25-solar-colonization-modules-and-bases-design.md`,
`2026-10-26-solar-colonization-free-colonies-design.md`). The plan is
`../plans/2026-10-26-solar-colonization-fleets.md`: four parts, each its own
PR.

Everything here is under **Full Colonies** only (`sr_colonies_full_enabled`).
Races only and Simple Colonies are unchanged.

## Decisions (owner, 2026-10-26, interview)

- **One design for the whole phase, in four parts**, each its own PR: **6a**
  the fleet record, ship roles, Space Command and movement; **6b** combat,
  postures, blockade away from Earth, seizure, destruction, the peace, war
  support; **6c** interdiction in peace, the AI's offence, the outer-space
  convention; **6d** Earth orbit: blockading Earth, a ground reserve,
  ground-to-orbit batteries, orbital fire support in the ground war. (The scope
  had three parts; 6d is new, from the owner's answer on Earth orbit.)
- **Ship roles, not drive classes.** A drive is a national unlock, not a hull
  type. A fleet flies on the nation's best drive once it has **docked** at
  Earth or at one of our Spaceports since that drive arrived: an automatic
  refit of about three months. A fleet deployed at Saturn keeps its old drive
  until it calls at a port, so a rival's new drive opens a window, not an
  instant change. (The owner asked what scrapping old hulls would buy: under
  the square law, old hulls still add fighting strength and absorb losses, so
  the answer was little; tracking strength per drive would mostly make players
  sort fleets by hull age.)
- **Five roles**: warships, assault carriers, tenders, **siege ships** (good
  against colony defences, poor against fleets) and **rapid response** ships
  (fly one drive ahead, weak in combat).
- **Legs between locations**: Earth's outbound legs keep their exact tables.
  Returns to Earth, and legs among the inner locations (Mercury and Venus,
  Mars, the Asteroid Belt, Jupiter), get windows from their mean synodic cycle,
  with delta-v and transit curves by month. Legs touching Saturn or beyond
  (other than to and from Earth) are fixed medians. "Include it only where it
  matters most" (owner).
- **Propellant in km/s**, from the generator's tables, refilled at Earth or at
  one of our Spaceports.
- **Earth and the Moon**: no blockade of Earth in 6a to 6c; fleets fight there
  and add orbital debris. In 6d an uncontested blockade at Earth stops the
  target's launches, and the side holding Earth orbit gets fire support in
  the ground war. **A blockade must not be able to hold a power for a whole
  war** (owner: two ships in orbit must not beat thirty built one at a time):
  new hulls wait in a **ground reserve** and launch together, and
  **ground-to-orbit batteries** (an extension of the anti-satellite strike)
  fire on any enemy fleet at Earth every month. With Directed Energy
  Weapons, the batteries' lasers also **clear low-orbit debris in peace**
  (owner's addition).
- **War support**: both occupied colonies and battles count, kept small: a
  colony is a rounding error beside a city on Earth. Per occupied colony
  0.1 to 0.25 a beat, rising as colonies grow (owner: "0.1 up to 0.25
  depending on the era, as space industry and colony populations rise").
- **The AI defends and attacks at war, and never interdicts in peace.**
- **Space Command** is a new government building, built where the Space
  Program stands.
- **Marines are the garrison** under Full Colonies: slice 5's "Garrison it"
  answer stations marines a fleet must land within a year, and marines at a
  colony defend it against seizure. Simple Colonies keeps slice 5's political
  garrison.
- **Full Colonies becomes the default when 6d ships.**
- **The outer-space convention** comes about as the anti-satellite Moratorium
  did, a docket item raised by the first seizure or destruction, and **can
  also be tabled** by a member that holds a colony, a player from the
  chamber or the AI by its button.
- **A free colony seized is ours at once**: closing in on one needs no war
  (there is no one to make peace with) but costs infamy and a UN dossier item.
- **Occupied states** (owner, after the interview): nothing is built, launched
  or fired from a state its owner doesn't control. Space Command, the
  ground-to-orbit batteries and the Orbital Battlestation in an occupied state
  count for no one: not their owner, and not the occupier, whose gain is the
  denial (§ 5.1). Vanilla keeps buildings working under occupation
  (`vanilla_war_reference.md` § Occupation), so the script must test it.

Kept from the scope (§ Decisions, § 11): fleets are records with a location
and a timer; nine slots; capacity and current; no interception in transit;
Lanchester's square law until a play-test; Earth and the Moon one location
and a battleground; warships screen carriers and tenders (F10); tenders pool
supply and propellant (F11); the panel picks what Space Command builds (F9).

## Intent

After each part, under Full Colonies:

- **6a.** A power with Space Militarization builds **Space Command** in its
  Space Program's state. Its levels and methods set how much fleet strength it
  launches a month, shared among five roles by a build mix the player sets.
  New strength joins the home fleet at Earth. The player keeps up to **nine
  fleets** and orders each to any of the nine locations. A fleet spends
  **propellant** (km/s) on each leg and **supply** each month away from a
  port, refits to the nation's best drive when it docks, and is repaired,
  refuelled and resupplied at Earth or a Spaceport. Assault carriers carry
  **marines**, which garrison our colonies (slice 5's garrison answer, now
  done by fleets). The panel lists fleets, Space Command and every location's
  forces. The AI builds Space Command and lands its garrisons. Nothing fights
  yet.
- **6b.** Hostile fleets at a location **fight each month** (Lanchester), by
  **posture**: station, stand off, close in. Colony **Defences** fire on fleets
  closing in, and a colony has an **integrity** they protect. An uncontested
  stand-off **blockades** the enemy's colonies at a location (not at Earth).
  Closing in grinds integrity down; at zero, with enough marines, the colony
  is **occupied**, and it goes back at the peace unless a Cede Colony article
  for it is enforced. A colony can instead be **destroyed**, which is quicker
  and costs infamy, a UN item and the destroyer's own colonies' loyalty. A
  free colony can be seized. Occupied colonies and battles move **war
  support**. **Survey Colony Defences** joins the covert operations. The AI
  defends its colonies.
- **6c.** Fleets may **interdict in peace**: standing off at a rival's colonies
  blockades them without a shot, at a price in infamy and UN standing, and
  gives the target a casus belli. The **AI attacks at war**. The UN can
  adopt an **outer-space convention** against seizing and destroying colonies.
- **6d.** **Earth can be blockaded**: an uncontested enemy fleet at Earth stops
  our launches. New hulls wait in a **ground reserve** and launch together, and
  **ground-to-orbit batteries** fire on enemy fleets at Earth (and, with
  lasers, sweep low-orbit debris in peace). Holding Earth orbit gives **fire
  support** in the war on the ground. **Full Colonies becomes the default.**

## Non-goals

Interception in transit (scope § 5.4). Fleets of a power bloc, or Spaceports
that serve allies (ours only, for now). Free colonies with fleets of their
own, their diplomacy, the UN as their guarantor (scope § 6.5's later items).
The AI interdicting in peace, destroying colonies or seizing free colonies.
Combat between countries that are not at war (an interdiction meeting a
stationed fleet is a standoff, not a battle). Emigration by culture, the Mars
terraforming megaproject, colonies held by a power bloc (scope § 10's other
ideas).

## Engine facts

**Rests on:**

- Everything slices 0 to 5 rest on: the global record keyed by world, the
  sync, the global monthly step and its order (landings before the worlds'
  step), `$PARAM$` substitution in variable names, a static modifier at
  `multiplier =` removed first, one refresh site per modifier, scripted GUIs
  with `scope:site` and `scope:op`, timed global and country variables.
- `modulo` in a script value (`te_construction_market_pulse_values.txt:19`),
  kept on positive integers: C++'s `%` keeps the dividend's sign, so the
  generator adds a positive epoch term.
- `has_war_with = <country>` (country scope; `docs/engine/triggers_parsed.txt`),
  with a stored country as its target.
- War support's last term, `INJECT:war_support_from_journal_entries`
  (`common/script_values/zz_te_war_support_injections.txt`): root the
  country, `scope:war` the war, one `add = { value desc }` per row, no
  `every_country` and no randomness.
- A production method's `state_modifiers = { workforce_scaled = { … } }` on a
  script-only state type, read in state scope as `modifier:<type>` (the
  barracks training methods' `state_reserve_battalions_add`,
  `barracks_training_values.txt:29`); a `script_only` type still renders in
  tooltips (`scripting_best_practices.md`).
- `add_modifier` in building scope, from `every_scope_building`, at
  `multiplier = root.var:<x>` (`resettlement_refresh_destination_readout`,
  `resettlement_effects.txt:495`, confirmed in game 2026-09-27; the Orbital
  Battlestation's progress, `extra_on_actions.txt:3091`); and
  `building_goods_input_mult`, the building-masked multiplier on a building's
  goods consumed (`docs/engine/modifiers_summary.txt`; vanilla's
  `mobilized_battalion_consumption` sets it to 1 on a mobilized barracks).
- A government building whose `can_build_government` reads the country, so the
  AI builds no further than a script value allows (slice 4's
  `sr_ebase_may_build_government`).
- A treaty article's war goal `infamy` is a script value with `add = { desc value }`
  (`common/treaty_articles/124_cede_colony.txt:170`).
- `te_debris_add = { LOW HIGH }` (`te_orbital_debris_effects.txt:54`).
- A state's `controller` link, compared to a country (`controller = scope:x`,
  `gm_trophy_values.txt:101`). Buildings in an occupied state go on working
  and supplying their market in vanilla (`vanilla_war_reference.md`
  § Occupation), so every count in § 5.1 tests the controller itself.
- The covert framework's registry (`test_covert_op_registry.py`; Incite
  Colonial Autonomy is code 15, Sabotage Colony 16) and the UN convention
  registry (`test_un_convention_registry.py`, which names the sixty-odd sites
  a convention needs; the Moratorium is op 32, docket item 16, `un_events.41`).

**Unverified, each with a self-check or a play-test row (§ 18):**

- That Space Command's methods' state modifier reaches its state and reads
  above 0 once staffed (`ship_construction`).
- **That `building_goods_input_mult` on a building raises its input goods**
  (the owner recalls trouble with it), against the good-specific multipliers
  known to work: the `upkeep_inputs` probe, run before the upkeep is written
  (§ 5, § 18).
- That a fleet lands in the month its leg's table gives (`fleet_leg`, on
  `colony_fleet_arrival`'s pattern).
- That a war goal's `infamy` block sees `scope:target_country` and `root` in a
  treaty article's war goal, so Cede Colony can cost nothing against an
  interdictor (a play-test row: the war goal's infamy reads 0).
- That the war-support breakdown shows the new rows by their `desc` (a
  play-test row).
- When a partly occupied state's `controller` turns to the occupier (at half
  its provinces, as war-goal control counts it, or only at all of them): a
  play-test row occupies a Space Command state province by province and notes
  the month construction stops.

## 1. Locations and legs

### 1.1 The nine locations

| Code | Key | Name | Legs measured to | Worlds |
|---|---|---|---|---|
| 1 | `earth` | Earth and the Moon | Earth | none (the Moon Base is a milestone, not a world) |
| 2 | `inner` | Mercury and Venus | Venus | Mercury, Venus Cloud Habitat |
| 3 | `mars` | Mars | Mars | five |
| 4 | `asteroids` | the Asteroid Belt | Ceres | five |
| 5 | `jupiter` | the Jupiter system | Jupiter | six |
| 6 | `saturn` | the Saturn system | Saturn | five |
| 7 | `uranus` | the Uranus system | Uranus | four |
| 8 | `neptune` | the Neptune system | Neptune | two |
| 9 | `kuiper` | the Kuiper Belt | Pluto's orbit (`kuiper`) | five |

`gen_solar_sites.LOCATIONS` (the panel's eight) gains `earth` first in a new
`FLEET_LOCATIONS`. A fleet at a location acts on every world there. Each
multi-body location is measured to one body: Mercury is reached on Venus's
legs and the four smaller asteroids on Ceres's. Colony fleets and module
shipments keep their per-body tables (slices 3 and 4).

### 1.2 Legs

A **leg** is a trip between two locations by one drive. For every ordered pair
and drive, the generator gives its **months** and its **delta-v** (km/s):

| Leg | Departure | Curves |
|---|---|---|
| Earth → any location | today's exact windows (`sr_window_*`, the body's) | months: today's `sr_transit_<drive>_<body>`; delta-v: new, by the same offset |
| any location → Earth | the pair's mean synodic cycle | months and delta-v by signed months from the cycle's optimum |
| among Mercury and Venus, Mars, the Belt and Jupiter (12 ordered pairs) | the pair's mean synodic cycle | months and delta-v by signed months from the optimum |
| every other pair (Jupiter → Saturn, Mars → Uranus, Saturn → Neptune, …) | any month | one fixed figure each: the median over the span |

- **Delta-v by drive.** Chemical: the cheapest transfer plus the premium's
  extra delta-v at that offset (the same Lambert solutions the premiums come
  from; `extra = 3.7 × ln(1 + premium)` for Earth's legs). Fusion: the
  delta-v of the transfer it takes, within its 30 km/s budget. Torch and
  antimatter: the brachistochrone's, acceleration × time, at most its cap.
  Departure from a planet's or moon's system starts in the loose capture
  orbit a fleet arrives in (eccentricity 0.9, slice 3's capture), not in
  low orbit.
- **A mean-cycle window in script.** `sr_leg_phase_<a>_<b>` =
  `(te_history_month_index × 100 + E) modulo S`, with `S` the pair's synodic
  period in hundredths of a month and `E` a positive epoch term the generator
  fits to the span's optimum dates; the signed offset is the phase in months,
  folded into `[−S/2, S/2)`. For eccentric pairs (Mars and the Belt) a mean
  cycle can miss the true window by a month or so; the report says by how much.
- **Rapid response.** A fleet of rapid response hulls alone flies one drive
  ahead (chemical hulls on fusion's legs and so on; antimatter hulls at three
  quarters of antimatter's months, rounded up, at least 1) and spends that
  drive's delta-v from that drive's capacity (§ 2).
- **Size.** About 7,000 more lines in `sr_launch_windows_generated.txt`
  (today 7,009). No monthly cache: a leg is read when a fleet departs and when
  the panel draws a fleet's row.
- **The report** (`docs/engine/launch_windows_report.md`) gains a Fleets
  section: every pair's cycle, its fitted epoch against the true optimum
  dates, and its curves.

## 2. Drives, refits and propellant

| Drive (`sr_drive_level`) | Capacity (km/s) | So, with no Spaceport on the way |
|---|---|---|
| 0 Chemical | 12 | a round trip to Mars (about 9) or Venus; one way to Jupiter (8), Saturn (8.5) or the Belt (10.5) |
| 1 Fusion | 60 | a round trip to Jupiter in a window (two legs within 30 each) |
| 2 Fusion torch | 1,000 | two to four legs (250 to 400 each) |
| 3 Antimatter | 5,000 | three to six legs |

- **A fleet records its own drive**, `sr_fl_<n>_drive`, the nation's best when
  it was built or last refitted. **Docked** means at Earth, or at a location
  where we hold a colony with a Spaceport. A docked fleet whose drive is below
  the nation's starts a **refit**: three months (`sr_fl_<n>_refit_until`), in
  which it can't depart (it can still fight), then it flies on the nation's
  drive of that day.
- **Propellant**, `sr_fl_<n>_dv` (km/s), against its capacity (§ 3, tenders).
  A leg needs the fleet's propellant to cover its delta-v; otherwise the order
  is refused, and the panel says how short it is. Docked, a fleet refills each
  month: fully at Earth and at a Spaceport on a **propellant world** (a new
  site-table field: water or volatiles to crack: Utopia Planitia, Ceres,
  Europa, Ganymede, Callisto, Titan, Enceladus, Rhea, Triton, Pluto-Charon),
  and a quarter of its capacity at any other Spaceport (propellant shipped up
  from Earth). So a chemical fleet reaches Jupiter, and comes home only if we
  hold a Spaceport there: a Spaceport on Europa is worth fighting over.

## 3. Ship roles

| Role | Fire on fleets | Fire on defences | Endurance (months) | Other | Screen? |
|---|---|---|---|---|---|
| Warship | 1.0 | 1.0 | 18 | | screens |
| Rapid response | 0.5 | 0.5 | 12 | an all-rapid fleet flies one drive ahead | screens |
| Siege ship | 0.5 | 2.0 | 18 | | screened |
| Assault carrier | 0.25 | 0.25 | 12 | 2 marine battalions a point of strength | screened |
| Tender | 0.1 | 0.1 | 36 | pools supply and propellant | screened |

What a fleet can do follows from what it holds:

- **Pace**: the fleet's drive (§ 2), or one ahead if it holds rapid response
  hulls alone.
- **Propellant capacity**: the drive's capacity × (1 + the tenders' share of the
  fleet's strength).
- **Endurance**: the lowest endurance among its other roles × (1 + 2 × the
  tenders' share); a fleet of tenders alone, 36. A third tenders turns 12
  months into 20.
- **Marines**: 2 battalions a point of carrier strength.
- **Screening** (F10): a fleet's losses fall on its screens (warships, rapid
  response) in proportion to their strength until they are gone; only then on
  the screened roles. So carriers survive a fight their warships win.

## 4. The fleet record

Per country, nine slots `n` = 1 to 9 (generated per slot), all country
variables, so a revolution's winner inherits them (and a dead country's are
gone):

| Variable | Holds |
|---|---|
| `sr_fl_<n>_loc` | the location's code; absent = an empty slot |
| `sr_fl_<n>_dest`, `_arrive`, `_depart` | in transit: the destination, the arrival and departure months |
| `sr_fl_<n>_<role>`, `sr_fl_<n>_<role>_full` | strength now and at full, per role (`war`, `rapid`, `siege`, `carrier`, `tender`) |
| `sr_fl_<n>_dv` | propellant left, km/s |
| `sr_fl_<n>_supply` | months of supply left |
| `sr_fl_<n>_marines` | marine battalions aboard |
| `sr_fl_<n>_drive`, `_refit_until` | its drive, and a refit's end |
| `sr_fl_<n>_posture`, `_target` (6b) | 1 station, 2 stand off, 3 close in; the world it closes in on |
| `sr_fl_<n>_destroy` (6b) | closing in to destroy, not to seize |

- **Strength** is built by Space Command (§ 5), lost in battle, and repaired
  when docked: at Earth 20% of the gap a month, at a Spaceport 10% a level.
  A battle's losses are half destroyed (strength now and at full both fall)
  and half damage (strength now falls; repair brings it back).
- **Supply** counts down a month away from a dock and refills when docked. At
  zero the fleet loses 5% of its strength a month.
- **Marines** refill at Earth only, to capacity within the month; they land at
  our colonies (§ 9.6) and are spent in a seizure.
- **Merge and detach.** At the same location, a fleet merges into another of
  ours (every number added; the drive the lower; propellant and supply the
  lower share of their capacities) or detaches half of each role into an empty
  slot.
- **Global records per location**, rebuilt by the global step monthly and on
  every arrival and departure: `sr_loc_present_<loc>` (fleets there),
  `sr_loc_strength_<loc>` (their strength), `sr_loc_inbound_<loc>`,
  `_inbound_first_<loc>` and `_inbound_by_<loc>` (as slice 3's per-world
  inbound record). A country with a fleet at a location carries
  `sr_fl_at_<loc>` (its summed strength there), so combat reads one number per
  country and location. A global variable list, `sr_fleet_powers`, holds every
  country with a fleet, a Space Command or (6d) a battery, so the monthly steps
  never walk `every_country`.

## 5. Space Command

`building_space_command`: a government building (`bg_military`, unless its
handling of barracks gets in the way, then `bg_government`), unlocked by
Space Militarization, `potential` Full Colonies, `possible` the state holds a
Space Program, expandable, `can_build_private` no.

| Method (`pmg_space_command_yards`) | Technology | Strength a level a month | Inputs a level a week | Employs a level |
|---|---|---|---|---|
| Orbital Shipyards | Space Militarization | 0.5 | Launch Capacity 500, Advanced Materials 10 | 500 officers, 2,000 engineers, 2,500 machinists |
| Fusion Yards | Fusion Power | 1.0 | Launch Capacity 600, Advanced Materials 15 | same |
| Torch Yards | Muon-Catalyzed Fusion Reactors | 1.5 | Launch Capacity 600, Advanced Materials 15, electricity 200 | same |
| Antimatter Yards | Antimatter Production and an Antimatter Containment Facility | 2.0 | Launch Capacity 700, Advanced Materials 20, electricity 400 | same |

- **Construction is a modifier the player can read**, as the batteries'
  figures are (§ 15). Each method carries its rate as a script-only,
  workforce-scaled state modifier in its `state_modifiers`,
  `state_sr_ship_construction_add` ("Fleet Strength Built a Month"), so the
  method's tooltip shows what a level builds and staffing is in the number.
  `sr_sc_rate` (country value) sums `modifier:state_sr_ship_construction_add`
  over the states that pass `sr_state_held_by_owner` (§ 5.1). This works only
  because the upkeep below scales inputs, not throughput: a workforce-scaled
  modifier follows throughput (slice 4's fabrication does), so an upkeep on
  throughput would feed the fleet's size back into its own construction.
- **The build mix** (F9, panel orders): five weights 0 to 3,
  `sr_sc_mix_<role>`, warships 2, carriers 1, tenders 1, siege and rapid 0 to
  start. The month's construction is shared by weight and added to the **home
  fleet**: the lowest slot at Earth, not in transit or refitting (a new slot
  at Earth when there is none; nothing is built with all nine slots away from
  Earth). New strength comes at full, with the nation's drive; joining a fleet
  on an older drive it takes that fleet's drive until the fleet refits.
- **Upkeep scales Space Command's inputs** (the house rule: upkeep is an
  input multiplier on the building that does the work; owner, on the PR: the
  inputs, not throughput). `sr_fleet_upkeep`, a static modifier
  (`building_goods_input_mult` +1% a unit), sits on the Space Command building
  itself, at multiplier = `root.var:sr_fleet_upkeep_units` (full strength in
  service ÷ 10, set on the country first). The fleets' monthly country step
  refreshes it, removed first, its one refresh site. It can't be a country
  modifier: `building_goods_input_mult` is building-masked, so on the country
  it would raise the inputs of every building the country owns. So a fleet of
  300 makes Space Command consume 30% more goods, and builds no faster for it.
  The building's panel shows the line. `gen_nation_tab.py` lists it under
  `NOT_ON_COUNTRY`.
- **`building_goods_input_mult` is checked first, and has a fallback.** The
  owner recalls trouble with it in this mod before (nothing in the repo
  records what), while the good-specific multipliers are known to work. So 6a
  opens with a probe (§ 18) that puts each candidate on a building at a large
  multiplier and reads the result. The preferred one,
  `building_goods_input_mult`, covers every input with one line and follows
  any change to the methods. The fallback, `sr_fleet_upkeep_goods`, carries
  `goods_input_launch_capacity_mult`, `goods_input_advanced_materials_mult`
  and `goods_input_electricity_mult` at +1% each. All three are registered by
  the mod (`mod_entity_modifier_types.txt:599`, `:558`, `:528`), and a test
  keeps the list in step with the methods' input goods. Either way it sits on
  the building, never the country: the good-specific types are building-masked
  too, and on the country would raise every building's use of those goods.
  The answer goes into `scripting_best_practices.md`, so the next system
  needn't ask.
- **The Orbital Battlestation** fights at Earth (6b, § 7.5).

### 5.1 Occupied states

One trigger, `sr_state_held_by_owner` (state scope: its `controller` is its
owner), gates every Earth building this design counts:

| Building | Part | In a state its owner doesn't control |
|---|---|---|
| Space Command | 6a | adds nothing to `sr_sc_rate`: no strength is built there |
| The Orbital Battlestation | 6b | doesn't fight at Earth for its owner, and doesn't regain strength |
| Ground-to-orbit batteries | 6d | don't fire, and their lasers don't sweep |
| The Space Program (the launch site) | 6d | its owner launches nothing (§ 15: colony fleets, module shipments, settlers, fleets from Earth and the reserve) and fabricates no modules |

The occupier gets nothing from them. The yards, batteries and launch site are
staffed by the owner's people and fed by its market, and vanilla gives an
occupier no building's output. What the occupier gains is that its enemy has
lost them, which also gives a land war a way to shut down a space programme.
They work again the month the state is back under its owner's control.

The space race's own milestones (`je_space_race_*`) are unchanged: they read
the Space Program as before. Stopping those under occupation would be a
change to the race, not to the fleets.

## 6. Orders and movement (6a)

- **An order** (the fleet's row, § 16): pick a destination, then Go.
  Allowed when the fleet is at a location, not refitting, the leg departs this
  month, and its propellant covers the leg's delta-v. A leg from Earth leaves in
  the body's window as colony fleets do, or outside it for the extra delta-v.
  A chemical fleet may simply not have it. A torch or antimatter leg leaves any
  month. A mean-cycle leg leaves any month, at the delta-v its offset gives.
- **The dispatch** spends the delta-v, sets `_dest`, `_depart` and `_arrive`
  (now + the leg's months), clears `_loc` and posture, adds the fleet to the
  destination's inbound record and, under 6b, alerts players who hold a
  colony there and are at war with the fleet's owner (`.100`).
- **In transit** a fleet can be neither attacked nor recalled, and spends no
  supply (it carries its own for the trip).
- **Arrival**, from the global monthly step before combat and before the
  worlds' step: `_loc` = `_dest`, posture Station where we hold a colony there
  and Stand off elsewhere, the location's records rebuilt. A fleet that lands
  where we hold a colony counts as **contact** for its autonomy (slice 5's
  `sr_site_contact_<key>`), for every world we hold there.
- **The AI** orders fleets through the same effects (§ 14).

## 7. Combat at a location (6b)

### 7.1 Who fights

Each month, at each location, every fleet fights every **hostile** fleet it is
**engaged** with. Hostile: their owners are at war with each other
(`has_war_with`); and a fleet closing in on a free colony is hostile to that
colony's Defences alone (§ 9.5). Engaged, by posture:

| Posture | Engages |
|---|---|
| Station (the default where we hold a colony) | every hostile fleet at the location |
| Stand off (blockade) | hostile fleets that stand off or are stationed; out of the defences' reach |
| Close in (assault) | hostile fleets that close in or are stationed, and the defences of the world it targets |

At Earth there are no colonies: every hostile fleet there engages every other,
whatever its posture, and the Orbital Battlestation fights for its owner.

### 7.2 Lanchester's square law

Each side's **losses are in proportion to the other side's fire**: a month,
fleet A loses `k × B's fire`, with `k` = 0.1 and fire the sum of each role's
strength times its factor (§ 3) times the owner's **quality** (1, +25% each
for Directed Energy Weapons, Orbital Weapon Platforms and Antimatter
Production). That is the square law: fighting strength goes as the square of
numbers, so concentration pays (100 against 50 ends with about 87 left). The
scope's wording, losses in proportion to the other's strength *squared*,
would be a different law; this design uses the standard one.

With more than two countries at a location, each fleet's fire is shared among
the hostile forces it engages in proportion to their strength, and each
country's losses are the sum of the fire it receives. Losses spread over the
roles by screening (§ 3), half destroyed and half damage (§ 4).

### 7.3 Defences and integrity

- **Defences** (slice 4's placeholder module): a world's Defences fire on the
  hostile fleets closing in on it, 15 strength a level at factor 1.5 (+25% with
  Orbital Weapon Platforms), scaled by its integrity.
- **Integrity**, `sr_site_integrity_<key>` (global, 0 to 100, absent reads 100):
  the colony's hull, domes and power. The fire closing-in fleets aim at the
  world's Defences (their fire on defences, shared with the stationed fleets
  they also engage) lowers it by `100 × fire ÷ hardness` a month, with
  hardness = 50 + 50 a Defences level. A world under no assault regains 5 a
  month, 10 with a Spaceport, and 25 when a module lands.
- So two Defences hold a fleet of 100 warships for more than a year (6.7 a
  month at first, while the Defences' fire wears the fleet down), and 50 siege
  ships with it halve that. First guesses (§ 20).

### 7.4 After the month's fighting

- **Notices** (players, once a month at most per location): `.101`, a battle
  report (who fought, the losses on each side, integrity).
- **Debris**: at Earth, every point of strength lost adds 0.05 to the low pool
  and 0.02 to the high (`te_debris_add`), so a battle of 100 points' losses
  adds about what an anti-satellite strike does.
- **War support** (§ 10).

### 7.5 The Orbital Battlestation

At Earth only: its owner's battlestation fights in every battle there as 25
warship strength a level (five levels at most, Orbital Weapon Platforms'
building), losing strength as a fleet does and regaining 10% of full a month.
It never moves and is never destroyed: its losses take nothing from the
building. In a state its owner doesn't control it neither fights nor recovers
(§ 5.1).

## 8. Blockade (6b; at Earth from 6d)

A world is **blockaded** (`sr_site_blockaded_<key>`, recomputed each month)
when a fleet hostile to its holder stands off at its location and no fleet of
its holder is stationed or standing off there. Then, for that world:

- **No settlers** land (emigration treats it as Closed).
- **Module shipments** landing there are lost.
- **No contact**: fleets and shipments of its holder don't reach it, so the
  autonomy clock runs (slice 5).
- **Mined output stops**: its Extraplanetary Base room drops out of its
  holder's room (slice 4's `sr_ebase_refresh` skips it), and its
  **goods-shipping specializations** run at nothing. A new site-table field
  says which of a world's two specializations ship goods to Earth (mining,
  industrial, volatiles, propellant, extraction and the like), through a
  blockade factor in `sr_site_mult_<a|b>_<key>` as the charter's share works
  (slice 5). Research is radioed home: science and observatory
  specializations keep running, so a blockade hurts mining and logistics
  colonies, not observatories.

Fleets and colony fleets in transit are never intercepted. A colony fleet
founding a free world at a blockaded location founds it.

## 9. Seizure, occupation and destruction (6b)

### 9.1 Seizure

A fleet closing in on a world brings its integrity down (§ 7.3). At zero, if
no hostile fleet is stationed at the location and the fleet's marines exceed
the world's **garrison** (its holder's marines there, § 9.6) plus its
**militia** (a battalion a 20,000 people, at least one), the world is
**occupied**: the marines needed land as the occupier's garrison, and the rest
stay aboard.

### 9.2 Occupation

- `sr_site_occupier_<key>` (global): the occupier. An occupied world gives its
  modifiers to no one (the sync unmirrors it, as it does a free colony), its
  Extraplanetary Base room counts for no one, its people stay, nothing is
  founded or shipped there, and it counts in the war's war support (§ 10).
  Its Defences fire for no one, as an occupied state's buildings work for no
  one (§ 5.1): the occupier holds it with its garrison, and a liberation
  fights the occupier's fleets and garrison, not the world's own guns.
- **It goes back at the peace**: each month the global step returns every
  occupied world whose occupier and holder are no longer at war (the record
  cleared, the world synced, both told, `.102`). A Cede Colony article for it
  enforced in the peace moves the holder first, which clears the occupation, so
  the world stays where it is. Cession is still the one way a war moves a
  colony; occupation is how you make the enemy sign it.
- **Liberation**: the holder (or an ally at war with the occupier) closing in
  with more marines than the occupier's garrison, at integrity 0, frees it.
- A dead holder's occupied world passes to its heir (slice 0) occupied, or, if
  there is no heir, to its occupier.

### 9.3 Destruction

A fleet closing in **to destroy** (`sr_fl_<n>_destroy`) needs no marines:
three consecutive months closing in with no hostile fleet left stationed at
the location and its fire on defences above the Defences' fire. Then:

- the colony and its people are lost, its modules and its record cleared, as a
  release; the world is **ruined** for 25 years (`sr_site_ruined_<key>`, timed),
  in which no fleet can found it (`sr_cf_targetable_<key>` and founding read it);
- the destroyer pays **20 infamy** (doubled for a convention party, § 13), 20
  on the UN dossier's new ground `un_dos_space` ("hostile acts in space": one
  record for every act in this design, weighted per act, beside
  `un_dos_asat`), and its own colonies resent it: +10 autonomy at once at
  each, and a new drift term, +0.2 a month for ten years
  (`sr_destroyed_colony_until`), joins slice 5's table (the scope's
  "destruction of other colonies");
- both sides are told (`.103`).

Destruction is quicker than seizure (three months against an integrity grind),
as the owner wants: "it is easier to throw something fast at a colony than to
land marines on it".

### 9.4 Free colonies by force

Closing in on a **free colony** needs no war: the fleet's owner is hostile to
the free colony itself, and only its own Defences fire back (its suppliers do
not defend it). Starting costs **10 infamy** and 10 on `un_dos_space`. At
integrity 0 with marines above its militia, it is **ours at once**: holder
us, at autonomy 60, every country's ties to it cleared (slice 5's
`sr_site_clear_ties_<key>`), its suppliers told (`.104`). Destroying a free
colony is allowed on the same terms as § 9.3.

### 9.5 Hostility for free colonies

So that § 7.1 needs one rule: a fleet closing in on a free colony is hostile to
that colony's Defences and to nobody else.

### 9.6 Marines as garrisons

- **Landing and embarking**: a fleet at a location where we hold a colony
  lands marines there (`sr_site_marines_<key>`, global, the holder's) or takes
  them back aboard. The marines stay with the world through a cession or an
  heir only if the new holder is their owner's ally; otherwise they come home
  to Earth (they are added to the home fleet).
- **Slice 5's garrison under Full Colonies**: "Garrison it" (`.94`) sets
  `sr_site_garrison_due_<key>` (one year). The garrison takes effect (slice 5's
  −25 autonomy, its ten years, its resentment and its upkeep) when two
  battalions or more stand at the world, and lapses unanswered after the year
  (a player is told). Under Simple Colonies the garrison is as slice 5 built
  it.
- **Marines defend**: every battalion at a world raises what a seizure needs.

## 10. War support (6b)

Two rows in `INJECT:war_support_from_journal_entries`, each reading one country
variable the fleets' step refreshes monthly (the injection file's rules: no
iteration, no randomness):

- **Space colonies occupied**: for each world we occupy from an enemy in this
  war, +w a beat, and for each of ours an enemy occupies, −w;
  w = 0.1 + 0.15 × min(1, the world's people ÷ 75,000). So an outpost counts
  0.1 and a grown colony 0.25: the owner's "0.1 up to 0.25 as colony
  populations rise". The sum is the country's, not the war's: a country in two
  wars counts it in each (whether `scope:war` reaches a script value the
  injection calls is unverified, and two wars at once in space are rare).
- **Space battles**: a month in which we fought, +0.1 a beat for thirty days
  if the enemy lost the larger share of its strength, −0.1 if we did; ±0.25 if a
  side's fleet there was destroyed. A timed country variable carries it.

For scale, vanilla's own per-beat terms run from −5 (fully occupied) to about
+2.

## 11. Survey Colony Defences (6b)

Covert operation code 17, on the registry's pattern: intelligence axis,
moderate tier, needs Full Colonies and a target holding a colony. Each month
established:

- **Intelligence**: our panel shows the target's colonies' Defences, integrity
  and garrison exactly (without it, a rival's Defences read as a range and its
  garrison as unknown);
- **An edge**: our fleets' fire on the target's defences is +20% × the
  operation's multiplier (1 to 3.2, `covert_op_effect_mult`).

No modifier on the target.

## 12. Interdiction in peace (6c)

The owner's decision, on the model of the 1962 quarantine of Cuba:

- **A fleet may move to, and stand off at, a location where a country we are
  not at war with holds colonies.** That is an **interdiction**: its colonies
  there are blockaded (§ 8) while no fleet of its own stands there.
- **An interdiction that meets the target's stationed or standing-off fleet is
  a standoff**: no blockade, no shot. The first shot is a war: closing in,
  fighting and seizure all need one (`has_war_with`).
- **The price**, when an interdiction begins (a fleet stands off at a location
  of a country at peace with us that holds a world there): 5 infamy, 10 on
  `un_dos_space`, and the target's casus belli:
  `sr_interdiction_target` (the country) and `sr_interdiction_recent` (five
  years) on the interdictor, which Cede Colony's war goal reads to cost **no
  infamy** against it.
- The target is told (`.105`), and the panel's location row says so.
- **The AI never interdicts** (owner); it answers an interdiction by stationing
  a fleet there (§ 14).

## 13. The outer-space convention (6c)

A new UN convention, the **Convention on the Settlement of Outer Space**
(`colony_protection`, op 33, `un_events.42`, docket item 17, country-scoped,
the space race rule and the UN rule):

- **Raised** by the first seizure or destruction of a colony (as the Moratorium
  is by a strike: `sr_colony_un_on_seizure` leaves `un_dkt_colony_pending` for
  two years and marks the actor, which may not table it), and **tabled** by a
  member holding a colony (owner): a player from the chamber, the AI from a new
  `un_propose_colony_protection_button`.
- **Parties**: +2% prestige (× the enforcement multiplier); a party that seizes
  or destroys a colony, or seizes a free colony, pays twice the infamy and the
  case (`sr_colony_convention_party`, read by §§ 9.3–9.4 and 6b's seizure).
  It forbids nothing.
- `test_un_convention_registry.py`'s `CONVENTIONS` row first: its failures name
  every site still missing.

## 14. The AI

A monthly review per AI country with a fleet or a Space Command
(`sr_fl_ai_review`), stepped as the Colonial Empire's programmes are:

- **6a: building.** Space Command up to `2 + its colonies` levels (at most 10)
  for a top-three space power (`sr_ai_should_participate`), out of default, with
  a positive weekly income, through `can_build_government`'s cap. The mix
  stays at its start. The home fleet stays at Earth, except to land a due
  garrison (§ 9.6): a fleet with marines goes to the world and lands them.
- **6b: defence.** Each location where it holds colonies and a hostile fleet
  is present or inbound gets its strongest available fleet, stationed, if that
  fleet reaches it before the first hostile arrival or within six months.
  It recalls a fleet whose supply is under three months or whose propellant
  won't cover the leg home, and refits when docked. At war it switches the mix
  to warships 3, siege 1, carriers 1, tenders 1.
- **6c: offence at war.** A fleet that outmatches, 1.5 times over, the
  enemy's fleets at a location within twelve months' leg, with the propellant
  for the leg home or a dock of ours there, closes in on the enemy world of
  most value there (people and module levels). It closes in to seize when its
  marines suffice, else it stands off (a blockade). It never destroys a
  colony, never seizes a free one, and never interdicts in peace. A fleet
  interdicting its colonies counts as a threat for the 6b rule, so it
  stations a fleet there and turns the blockade into a standoff (§ 12).
- **6d** (§ 15): it launches its reserve when the reserve and its fleets at
  Earth match the enemy there (at once when no enemy is there), builds
  batteries at war with a fleet-holding enemy, and runs Ground Lasers in peace
  once debris is Cluttered.

## 15. Earth orbit (6d)

- **The ground reserve.** From 6d, Space Command's construction goes to
  `sr_reserve_<role>` on the ground, not to the home fleet. **Launch** (a
  button; the AI by § 14) puts the whole reserve into orbit as one fleet in an
  empty slot at Earth, any month, blockade or not. A blockade must face what
  we built at full strength, not one month's worth at a time. With no hostile
  fleet at Earth, construction may launch itself each month (a toggle,
  `sr_reserve_auto`, on by default), so a player at peace sees 6a's behaviour.
- **Ground-to-orbit batteries**, `building_orbital_defense_battery` (an
  extension of the anti-satellite strike), levels in any state we control,
  unlocked by Space Militarization, under Full Colonies:

  | Method | Technology | Each level a month |
  |---|---|---|
  | Kinetic Interceptors | Space Militarization | 1 point of fire on hostile fleets at Earth; each point fired adds 0.02 low debris |
  | Ground Lasers | Directed Energy Weapons (electricity input) | 2 points of fire, no debris; **in peace**, clears 0.01 from the low pool |

  Batteries fire in the Earth battle (§ 7.1) and take no losses.
- **The figures are modifiers the player can read** (owner, on the PR). Each
  method carries its fire, and Ground Lasers its sweep, as script-only,
  workforce-scaled **state** modifiers in its `state_modifiers`:
  `state_orbital_battery_fire_add` ("Fire on Hostile Fleets at Earth") and
  `state_orbital_debris_sweep_add` ("Low-Orbit Debris Swept in Peace"). So the
  method's tooltip and the state's modifiers show what a level does (a
  `script_only` type still renders in tooltips,
  `scripting_best_practices.md`), and staffing is in the number already. The
  script decides when they count: `sr_battery_fire` and `sr_battery_sweep`
  (country values) sum `modifier:state_…` over the states that pass
  `sr_state_held_by_owner` (§ 5.1), the sweep only while the country is at war
  with no one. That is the barracks training methods' pattern
  (`state_reserve_battalions_add`, read in `barracks_training_values.txt:29`).
  One field each, no building-scoped copy, which the game would list a second
  time.
- **Low-orbit sweeping** (owner's addition). Ground-based lasers that ablate
  small debris until it de-orbits are a real proposal for low orbit (NASA's
  ORION study of the 1990s and later laser-broom studies), and can't reach the
  debris high above. So Ground Lasers clear only the **low pool**, and only in
  peace: every country's `sr_battery_sweep` is summed in
  `te_debris_global_monthly` and taken from the low pool alone. A state
  modifier summed in script, not a country modifier like the Space Program's
  removal methods: a method's country modifier would still reach its owner
  from an occupied state (§ 5.1) and couldn't switch off in war. Ten levels
  clear 0.1 a month, beside Laser Broom's 0.15 from the Space Program and the
  low pool's own 1.5% decay: a help against everyday clutter, no cure for a
  Kessler cascade, which lives in the high pool.
- **Blockading Earth**: § 8's rule at Earth. A hostile fleet standing off at
  Earth with no fleet of the target there blockades the target: no colony
  fleet, module shipment, settler or fleet leaves Earth (Launch from the
  reserve still can), and none of its colonies has contact.
- **The launch site occupied** (§ 5.1): while its Space Program's state isn't
  under its control, a country launches nothing at all. No colony fleet,
  module shipment, settler, fleet departure from Earth or reserve launch, and
  no module fabrication. Unlike a blockade in orbit, no Launch breaks it: the
  state has to be retaken. Every departure trigger reads one test,
  `sr_launches_barred` (blockaded at Earth, or the launch site occupied).
- **Orbital fire support**: at war, a country whose fleets at Earth outmatch
  the hostile fleets there (or face none while it has some) gets
  `sr_orbital_superiority` (+10% unit offense, +5% unit defense) at
  multiplier = the margin, `min(1, (ours − theirs) ÷ max(theirs, 10))`,
  refreshed monthly from the country pulse. It stands beside the
  anti-satellite strike's −10%.
- **The default**: `space_race_rule`'s default becomes
  `space_race_colonies_full`. A save keeps its own setting.

## 16. The panel

All under Full Colonies, in the solar colonization widget, each section
collapsible with its client-side flag:

- **Space Command** (6a): construction a month and its levels; the build mix,
  five buttons each stepping its weight 0 → 3; the upkeep; from 6d the reserve
  by role, Launch and the auto-launch toggle.
- **Fleets** (6a): one row per slot (generated): location (or the destination
  and months left), strength now / full with the roles on hover, drive (and a
  refit's months), propellant now / capacity, supply, marines; then the
  destination button (it steps through the other eight locations; its hover
  gives the leg's months and delta-v and whether it departs now), Go, Merge,
  Detach, Land and Embark marines. From 6b: the posture button (Station → Stand
  off → Close in), the target world button (stepping through the location's
  worlds) and Destroy.
- **Locations** (6a): one row per location: our strength there, others' (the
  strongest power's flag; its strength exact, since fleets in space are seen),
  the inbound count·months as on the Solar System rows; from 6b, Battle,
  Blockaded or Interdicted.
- **Colony Defences** (6b): one row per colony we hold: Defences, integrity,
  marines, and its status (Blockaded, Under assault, Occupied, with the
  occupier's flag).
- The Solar System rows (slice 0) read **Occupied** and **Ruined** (two more
  `sr_disp_site_<key>` values).

The rows are generated; `test_space_race_labels.py` and
`test_space_race_layout.py` read them, as they do slice 4's.

## 17. Notices

Each a player event with an image (`event_image_audit`), its world or
location named through generated custom loc on a country variable, its
options' records in `custom_tooltip`s (`silent_variable_audit`):

| Event | Part | To | When |
|---|---|---|---|
| `space_race_events.100` | 6b | a holder at war with the fleet's owner | a hostile fleet departs for a location where it holds a colony (the arrival date) |
| `.101` | 6b | each side | a battle at a location, at most once a month |
| `.102` | 6b | holder and occupier | a world occupied; returned at the peace; liberated |
| `.103` | 6b | holder and destroyer | a world destroyed |
| `.104` | 6b | the seizer and the free colony's suppliers | a free colony seized |
| `.105` | 6c | the target | an interdiction begins |
| `.106` | 6d | the target | Earth blockaded |
| `.107` | 6a | the holder | a garrison lapsed unanswered (§ 9.6) |

## 18. Self-checks, the play-test list and the console

Added to `docs/testing/solar-colonies-playtest.md`:

- **`ship_construction`** (6a): a month after a Space Command first runs at half
  staff or more in a state its owner controls: OK when `sr_sc_rate` is above
  0, BROKEN otherwise (fallback: compute the rate in script, level ×
  occupancy × the method's rate by `has_active_production_method`, and state
  it in the methods' descriptions).
- **`fleet_leg`** (6a): the first fleet that lands logs its leg, its drive, the
  months flown against the table; BROKEN if it landed two or more months late
  (fallback: land fleets from the country pulse as well).
- **The `upkeep_inputs` probe** (6a, before the upkeep is written): a console
  option puts one candidate (`sr_fleet_upkeep`, then in a second run
  `sr_fleet_upkeep_goods`) at multiplier 50 (+50% inputs) on our Space
  Command, or on our Space Program before one is built (it buys Launch
  Capacity too). It logs the market's Launch Capacity buy orders
  (`market_goods_buy_orders`) and, through a follow-up event fourteen days
  later, logs them again and removes the modifier: `TE_SR_PROBE upkeep_inputs
  <candidate> before=… after=…`. The owner reads the building's input
  tooltip (the definitive read; the market is the cross-check) and records
  which works. Not a once-a-game self-check: the building's goods use can't be
  read from script, and the market's buy orders move with every other buyer,
  so only a large, deliberate jump reads clearly.
- **`battery_sweep`** (6d): the first month the world's step takes a sweep:
  logs the low pool before and after and the sum of `sr_battery_sweep`; BROKEN
  if the low pool fell by less than the sum (beyond its decay) or the high pool
  moved.

Play-test rows: every section and button; the destination's hover figures
against the report; a refit; a battle's losses against the square law; a
blockade's effects (settlers, shipments, base room, a mining specialization
at nothing, an observatory still running); seizure and the return at the peace;
destruction and the ruin; the war-support breakdown's two rows; Cede Colony's
war goal at 0 infamy against an interdictor; the convention in the chamber;
the reserve breaking a blockade; batteries firing; orbital superiority in a land
battle's breakdown; occupied states (§ 5.1): occupy, province by province, a
state holding Space Command, a battery, the battlestation or the Space Program,
and note the month each stops (construction, fire, the Earth battle, every
launch) and that each resumes when the state is retaken.

**Console**: `te_debug_space_race.6`, its options grown part by part: log our
fleets and every location's forces; give us 100 strength of each role at
Earth; land our fleets now; fill propellant and supply; set our drive to the
next; (6b) set a world's integrity to 0, run the month's combat now, occupy or
return a world; (6c) start an interdiction; (6d) fill the reserve, blockade
our Earth by the largest rival.

## 19. What the scope changes

- § 5.1's ship classes by drive generation give way to **roles with a refit on
  docking** (§§ 2–3).
- § 5.4's "losses in proportion to the other's strength squared" is
  restated as the square law proper (§ 7.2).
- § 10's three parts become four: 6d is Earth orbit.
- § 9: Full becomes the default when 6d ships, not 6c.

## 20. My calls, for the owner to check

1. **Drive capacities** 12, 60, 1,000 and 5,000 km/s; a refit of three months.
2. **The roles' figures** (§ 3), and **screens first** for losses.
3. **Lanchester's k = 0.1 a month**, quality +25% a technology.
4. **Space Command's rates** 0.5 to 2 strength a level a month; 5,000 jobs a
   level; upkeep +1% of its input goods a 10 points of fleet.
5. **Integrity**: hardness 50 + 50 a Defences level; regains 5 a month.
6. **Seizure needs integrity 0 and marines above garrison and militia**; a
   battalion of militia a 20,000 people.
7. **Destruction**: three months, 20 infamy, 25 years ruined, +10 autonomy
   and +0.2 a month for ten years at the destroyer's colonies.
8. **Free colonies**: 10 infamy to begin, autonomy 60 when seized.
9. **War support**: the occupation row's weight by the world's people (0.1 to
   0.25 at 75,000), summed per country rather than per war; battles ±0.1,
   ±0.25 for a fleet destroyed.
10. **Interdiction**: 5 infamy, dossier 10, Cede Colony free of infamy against
    the interdictor for five years.
11. **Mercury reached on Venus's legs**, the four smaller asteroids on Ceres's.
12. **Spaceports serve their holder only**; marines land only at our colonies.
13. **Ground Lasers clear 0.01 low debris a level a month, in peace only.**
14. **Orbital superiority +10% offense, +5% defense**, at the margin.
15. **The AI never destroys colonies or seizes free ones** (beyond the owner's
    "never interdicts").
16. **One dossier ground for space**, `un_dos_space`, rather than one per act:
    the dossier keeps one record a kind of wrong (six today).
17. **Occupied buildings count for no one, the occupier included** (§ 5.1),
    and **an occupied launch site stops every launch and module fabrication**
    (§ 15), under Full Colonies. The owner's note named the new buildings;
    the launch site is my extension of it, the same rule applied to the
    building every launch leaves from. An occupied colony's Defences likewise
    fire for no one (§ 9.2).
18. **Space Command's rate and the batteries' figures are state modifiers the
    script sums** (§§ 5, 15, the owner's suggestions on the PR), and **the
    fleet's upkeep is a modifier on the Space Command building that raises its
    input goods** (`building_goods_input_mult` if the probe shows it works,
    else the three good-specific multipliers), so a bigger fleet costs more
    and builds no faster.

## 21. Build order

The plan, `../plans/2026-10-26-solar-colonization-fleets.md`: four parts,
6a to 6d, each a PR that plays on its own and ships its AI, tests, docs,
player guide section and play-test rows.
