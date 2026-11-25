# Space forces personnel: the design

Drafted 2026-11-24 from the scope (`2026-11-24-space-forces-personnel-scope.md`,
PR #1990), whose decisions and § 10 answers it takes as given. This file
settles the calls the scope's § 11 left open and names every hook, so the
build follows one reference. It is built as **one PR**, not the scope's three
(the owner asked for the system in one PR, 2026-11-24): the pop type and
personnel, the casualties and the assault's toll, and the priority as a
toggle.

## 1. The calls of the scope's § 11

| Call | Decision | Why |
|---|---|---|
| The pop type's name | **Spacers** (`spacers`) | One plural word, as vanilla's types are, and plain in the pops list beside Soldiers and Officers. The building's figure keeps the scope's name, Space Forces Personnel. An owner call (the PR lists it). |
| One type or two | **One** | Halves the definitions and the tables. Officers' politics would matter only if spacers had a political weight of their own, and a few tens of thousands of people don't move a nation's politics. |
| Strata, wages, qualifications | **Lower strata**, `can_always_hire = yes` and no qualifications, as soldiers: a base staffs in any state, as barracks do. Wage weight 2, between soldiers' 1.5 and officers' 5, and a starting quality of life of 8 (soldiers 7). | The scope's lean. |
| `military = yes` | **No** | Its effect isn't recorded. Soldiers and officers are the engine's servicemen through the defines (`SERVICEMEN_POP_TYPE`, `OFFICERS_POP_TYPE`), so a third type marked military could be counted in barracks' or the army's sums the mod doesn't know of. Spacers serve no land unit. |
| The priority's form | **A toggle**: Hulls first (the default) or Marines first, one button in the Space Command row beside Launch and Auto | The owner accepted either for a first build. A per-fleet priority can come later. |
| The assault's toll | `sr_assault_loss_share` **0.5** of the defence the seizure overcomes (the garrison at its holder's crewed share, plus the militia); **the militia take no losses** | The scope's guess. Militia are a colony's people as a figure, not pops. |
| Free the jobs (the scope's § 5.4 step 2) | **Not built.** The kill alone. | It rests on two unread engine facts (§ 9.3 and § 9.4 of the scope). Without it a kill of 1,000 people takes about a quarter of that from the bases' workforce, and the bases rehire the gap, so lost marines come back sooner than a full replacement would. A follow-up once the play-test reads the kill. |

## 2. The pop type and its class

- `common/pop_types/te_spacers.txt`: `spacers`, after vanilla's `soldiers`
  (texture, colour, `start_quality_of_life = 8`, `can_always_hire = yes`,
  `wage_weight = 2`, `paid_private_wage = yes`, `dependent_wage = 0.5`,
  `unemployment = yes`, `ignores_employment_proportionality = yes`, soldiers'
  political engagement and portrait fields). Its icon was a placeholder
  (vanilla's soldiers icon) until painted art was chosen (2026-11-25: a
  cream and orange spacesuit helmet, `pops_icons/spacers.dds`).
- **Its class: a class of its own in each hierarchy**, `te_spacers_class`
  (default hierarchy), `te_spacers_class_edo` and `te_spacers_class_caste`,
  each lower strata with `allowed_professions = { spacers }`, in
  `common/social_classes/te_spacers_classes.txt`. Not an `INJECT` into vanilla's
  `lower_class`: an `INJECT` of a block vanilla already declares adds a second
  block rather than merging (`scripting_best_practices.md`, the ideology read of
  2026-10-04), and whether the engine reads two `allowed_professions` lists is
  unread. A class with one profession has vanilla's precedent (the Edo system's
  `strata_religious`).
- **Politics**: spacers join interest groups by vanilla's general rules
  only (§ 2.1).
- **The mod's tables keyed by pop type** take it where they list every type:
  the Map Room's class maps (selectors 88 and 89), the census generator's pop
  types, the census's war-dead classes and the save series' professions. The
  census does not count spacers among its soldiers (`te_dg_soldiers`, whose
  war-dead share follows the army's dead, and the Armed Forces map), and books
  the kill itself (§ 5.3).
- **Elsewhere**: Internal Resettlement never moves spacers
  (`resettlement_pop_eligible`). The kills that take a stratum, as the colony
  emigration's and resettlement's events do, can take them, as they take
  soldiers; the bases rehire. The tactical nuclear strike halves soldiers and
  officers only, so it spares them.

### 2.1 Armed Forces (owner, 2026-11-24: a minor attraction instead)

Vanilla's Armed Forces draws soldiers and officers by name in its
`pop_weight`; spacers reach it only as any pop does, through an acceptance
term of 25 (12.5 under Professional Army). Adding them needs vanilla's whole
`pop_weight` restated: a `REPLACE` would wipe the mod's female-chance
`INJECT`s into the same interest group, and an `INJECT` of a block vanilla
declares adds a second block. A few tens of thousands of people don't move a
nation's politics, so the build leaves it. The owner agreed ("probably not
worth it") and asked for a minor `interest_group_ig_armed_forces_pop_attraction_mult`
instead: the method's workforce-scaled state modifiers carry +1% a staffed
level. It reaches every pop in the base's state, a garrison town's lean, since
the state and the country are the scopes the game is known to read pop
attraction from; whether pops read it from their workplace is unread.

## 3. The building

`common/buildings/05_zz_te_sr_space_forces_base.txt`, `building_space_forces_base`:
`bg_government`, Space Militarization, `potential` Full Colonies,
`construction_cost_low` (200), government-built only (`can_build_government`
reads `sr_pers_may_build_government`), any state and any number of levels.
One group (`pmg_space_forces_base`), one method (`pm_space_forces_training`):
`level_scaled` `building_employment_spacers_add = 1000`, and
`state_modifiers.workforce_scaled` `state_sr_space_personnel_add = 1000` and
`interest_group_ig_armed_forces_pop_attraction_mult = 0.01` (§ 2.1). No
goods. Workforce-scaled modifiers follow the building's throughput as well as
its staff, so an unincorporated state (−10%), economies of scale or a new
capital (+10%) move a level's personnel too. The modifier type `state_sr_space_personnel_add` joins
`sr_fleet_modifier_types.txt` (script-only, 0 decimals, good).

## 4. Personnel: the values and the month

All in `common/script_values/sr_fleet_values.txt` unless generated.

| Value | Scope | What |
|---|---|---|
| `sr_pers_per_point` | country | 100, 50 with `artificial_intelligence` |
| `sr_pers_per_battalion` | any | 1,000 |
| `sr_pers_capacity` | country | `modifier:state_sr_space_personnel_add` over **every** state, occupied or not; while the migration's grace runs, at least the personnel it found (§ 8) |
| `sr_pers_crews` | country | `sr_pers_per_point` × `sr_fl_strength_full_total` |
| `sr_pers_marines_aboard` | country (generated) | every slot's marines |
| `sr_pers_marines_garrison` | country (generated) | `sr_site_marines_<key>` of every world we hold unoccupied or occupy |
| `sr_pers_in_service` | country | crews + 1,000 × (aboard + garrisons) |
| `sr_pers_share_value` | country | the stored `sr_pers_share` (absent reads 1) |

**The month** (`sr_fl_country_month`): the old-save migration first
(`sr_pers_migrate_once`, § 8), then Space Command's month, the reserve and the
slots' month in the toggle's order, upkeep, the AI's reviews, and
`sr_pers_close` last, which stores `sr_pers_share` = capacity ÷ in service, at
most 1 (1 with nothing in service, and 1 during the grace), and pays the dead
(§ 5.3). The combat pass, in the global step, reads the stored share.

**The gates.** The room is read live at each gate (`sr_pers_room_value`,
capacity − in service, at least 0), not stored, so Launch's click, which runs
outside the month, needs no step of its own and each gate sees what the one
before it spent. A launch (Auto's and Launch's `sr_fl_reserve_in_at`) moves
the share `sr_rs_share` = room ÷ (per point × the reserve), at most 1, of
each role, read once before anything moves, and the reserve keeps the rest;
marines come aboard at the launch and at Earth's monthly refill
(`sr_fl_marines_refill_at`) only up to room ÷ 1,000. A gate only stops
growth: none takes anything away. Launch, its button and Auto all need
`sr_pers_can_crew_launch`: room for a fleet's minimum strength at least, or the
slot a launch makes would be cleared the same month. The AI's launch match
(`sr_earth_reserve_and_ours`) counts only the reserve the room can crew.

**The order.** `sr_pers_marines_first` (a country variable, absent = hulls
first) decides whether `sr_reserve_auto_step` runs before the slots' month
(hulls first: the reserve launches, then the slots refill marines) or after
it. `sr_sc_month` no longer calls the Auto step; `sr_fl_country_month` does, in
the order the toggle sets. The AI sets marines first while at war, hulls
first in peace.

**Short of personnel.** `sr_fleet_readiness` multiplies by the share, so every
fire term that already reads readiness (fleets, Defences, Earth's weight)
reads it. Marines count at the share wherever they are weighed: the closing-in
marines (`sr_cb_mar_<key>`, in `sr_cb_add_target`), a garrison's weight (the
garrison need, at its holder's or occupier's share) and the AI's assault
tests. A seizure spends the marines it lands at their real number:
`sr_site_seize` turns the effective figures it compares back into battalions
by dividing by the seizer's share.

## 5. Casualties

### 5.1 The accruals

`sr_pers_dead_due` (country variable, people) collects them, each at the
loser's share at the time (`sr_pers_note_dead`, reading `local_var:sr_pers_lost`):

| Loss | Site | People |
|---|---|---|
| Battle, the destroyed half | `sr_fl_cut_role` (hand-written) | the fall in full strength × per point |
| Attrition | `sr_fl_month_at`, before `sr_fl_attrition_at` | full strength × 5% × per point |
| A slot cleared below the minimum | `sr_fl_month_at`, before `sr_fl_clear_at` | full strength × per point + marines × 1,000 |
| Marines past the carriers' room at full strength (carriers destroyed) | the trim in `sr_fl_month_at` | that excess × 1,000; those past a damaged carrier's room leave service alive, as damage kills no crew |
| A garrison overrun | `sr_site_occupy` (the holder's defending marines, shared on the Moon and Mars), `sr_site_liberate` (the occupier's) | battalions × 1,000 |
| A colony destroyed | `sr_site_destroy`, before the release (`sr_site_note_destroyed_dead`) | its own battalions × 1,000, to whoever holds it; on the Moon and Mars the holder's others there stay in service |
| The assault's toll | `sr_site_seize` | § 5.2 |

Not deaths: marines home (`sr_fl_take_marines_at` takes them aboard up to the
carriers' room, and the rest leave service, so the trim never sees them),
Transfer, Land and Embark, a cession, an occupation's end, a release by
abandonment or breaking away.

The battle report's dead (`sr_battle_dead`) is what the cuts booked that month
(`local_var:sr_pers_noted`, which `sr_pers_note_people` adds to), so the
Orbital Battlestation's share of the losses and the full-strength floor are
left out.

### 5.2 The assault's toll

`sr_site_assault_toll_<key>` (generated, any scope) = the garrison need × 0.5.
`sr_cb_seizes` needs effective marines above need + toll. `sr_site_seize` pays
need + 1 + toll (at most what was brought), lands what's left after the toll,
and charges the seizer's dead. The AI's assault tests compare marines × share
with need + toll (`sr_site_assault_need_<key>`). The fleet's target hover
doesn't give the price yet (a follow-up); Seize's hover names the toll.

### 5.3 The kill

`sr_pers_kill_step`, in `sr_pers_close`: while the due holds whole hundreds,
the states with bases share them one after another, each taking its share of
the hundreds still to place by its share of the capacity still to share, so
the shares add up to the month's and the last state takes what is left
(rounding each state's share of the whole alone dropped a small due among
three states and doubled it between two). Each kills in steps of
`kill_population_in_state = { value = 100 pop_type = spacers }`, at most its
spacers; the remainder (under 100) is carried, and what no state could pay is
dropped. At most 1,000 steps a month (`sr_pers_kill_max_steps`, the engine's
`while` cap); the rest waits. Each state books what it killed as war dead
(`te_demog_note_war_dead`, the census's `te_dg_war_in`, with
`te_demog_note_kills`' guards). The year's dead go on `sr_pers_killed_year`
for the hover.

## 6. The AI

- **Bases**: `sr_pers_may_build_government`: a player's government always
  may; an AI while the demand × 1.2 (in service, the reserve's crews, the
  carriers' unfilled room × 1,000) is above 1,000 a level built and queued
  (`sr_pers_planned_levels`, through `b:`, which sees a base whose levels are
  all queued), out of default. Levels, not staffed capacity: a level still
  hiring, or emptied by a kill, is already paid for.
- **Pause**: `sr_sc_ai_should_pause` gains the reserve awaiting crews above
  six months' construction with no base queued; `sr_sc_ai_may_resume` waits
  for it to clear.
- **Assault**: § 5.2. **Priority**: § 4.

## 7. The panel and notices

- Space Command: a third row of cells, Personnel (in service of capacity) and
  Crewed (the share, red below 100%), and a button beside Resuming reading
  Hulls or Marines (the order in force; its hover says so), the two taking
  turns as Auto's do.
- The reserve cell and the Launch hover name the points awaiting crews.
- While the share is below 1, a note above the fleet rows says so, rather than
  a Crewed N% on each card: the share is the country's, the same on every
  card.
- The battle report (`.101`) gains the people killed in the month, and the
  occupation notice (`.102`) the marines lost.

## 8. Existing saves

`sr_pers_migrate_once`, once a country (`sr_pers_migrated`), at its first fleets
month: with personnel in service and the ground reserve's crews
(`sr_pers_migrate_need`) above the bases' capacity it creates the base levels
the gap needs, rounded up, in Space Command's state, else the capital
(`extended_timeline_build_specified_building_level`, at most 100), and sets
`sr_pers_grace_until` six months on with `sr_pers_grace_capacity` at that
need, so the share stays 1 and the gates have that much room while the levels
hire.

## 9. Self-checks

`docs/testing/solar-colonies-playtest.md`'s table:

- `pers_pop_type` (scope § 9.1 and 9.5): armed on its country the first month
  it has a base of a level or more, whatever its staff, and read three months
  on: BROKEN with no spacers in the state; re-armed while the base is under
  half staff; else OK when its capacity sum is 0.75 to 1.5 times 1,000 × its
  levels × its staffing (throughput moves it, and the sum lags the live staff a
  tick), BROKEN outside that.
- `pers_kill` (§ 9.2): the first kill of 100 or more in a state, read a day on
  by a hidden event, before the base's weekly hiring most likely refills it: OK
  when the state's spacers fell by at least half the count, BROKEN when they
  didn't.

## 10. Colony modules (the owner, 2026-11-25)

"Spaceport, defenses, black site, training ground, and nuclear command center
should each use 1k spacer jobs/'Personnel' (in addition to Crew)." Built as
follows; the system doc's personnel bullet names every hook.

| Call | Decision | Why |
|---|---|---|
| Which levels count | Every built level of the five (`gen_solar_sites.PERSONNEL_TYPES`) at a colony we hold and no one occupies, 1,000 each (`sr_pers_per_module`), not halved by Artificial Intelligence | A level, not a staffed level, as a damaged hull keeps its crew. An occupied colony's modules serve no one. A battalion isn't halved either. |
| Who is short first | Nobody: the modules join in service, and one share covers fleets, marines and modules | One figure in the Crewed cell explains all three. The modules take theirs when they land, with no gate, as a lost base level does; the gates keep stopping only launches and refills. |
| What a shortfall does | The share multiplies the three facilities' and Defences' staffed levels, and a Spaceport's repair level. Docking and the integrity bonus need only a level | The staffed levels are what every effect already reads, so one factor reaches all of them. |
| Simple Colonies | No personnel: the bases are Full only | |
| Before Space Militarization | The modules wait at a share of 0 under Full; the + button says so, and the AI plans them only with the technology | The base is the building that does the work, a hard gate by the design defaults. A Black Site from a colony's first year now waits for the era 11 technology. |
| Holders with no fleet | `space_race_on_action` stores their share, since only a fleet power runs the fleets' month | Making them fleet powers would also run Space Command's month, whose Orbital Yard points would build hulls with no Space Command. |
| Old saves | `sr_pers_modules_migrate_once`, once a save from the global step | § 8's migration runs per country at its first fleets month, which a holder with no fleet never has; and a save that ran it already needs the modules' levels too. Run per country, it would give a new game's first module holder a free base. |
