# Space forces personnel: crews and marines drawn from a building, and killed with them: scope

Drafted 2026-11-24 from the owner's request. This is a scoping document: what to
build, in what order, and the calls the owner settled. It is not yet a design,
and it has no implementation plan. Later sessions write both.

**Status (2026-11-24):** scope, with the owner's answers to all ten open calls
the same day (§ 10). One answer changes the request: the base employs a new
pop type of its own instead of soldiers and officers, so a kill by pop type
reaches only its people (§ 3.2, § 5.3). The design can start; § 11 lists what
it has to settle.

Read first: `docs/systems/mod_systems/space_race.md` § Fleets, Space Command and
combat; the fleets design
(`docs/superpowers/archive/specs/2026-10-26-solar-colonization-fleets-design.md`)
§§ 3 to 5, 9 and 15; and the Space Race UI pass design
(`2026-10-31-space-race-ui-pass-design.md`) § 10, for the fleets' upkeep.

## The request (owner, 2026-11-24)

> Right now, marines and fleets in space are free once built. I think we should
> make them be limited by a new government building that employs soldiers and
> officers and adds a new script-only modifier type, with marines using a fair
> bit of manpower and fleets not that much. Ideally, when ships are destroyed or
> marines lost, a proportional amount of people employed in these buildings
> should die.

Read as four requirements, R1 as the owner's answer to call 7 changed it:

- **R1.** A new government building whose staff are a new pop type that
  nothing else employs (originally: soldiers and officers).
- **R2.** A new script-only modifier type the building grants, which is the
  capacity.
- **R3.** Fleets and marines draw on that capacity: marines a lot, ships a
  little.
- **R4.** Ships destroyed and marines lost, and marines killed taking a
  colony, kill a matching number of the building's staff.

## Decisions (owner, 2026-11-24)

- **The Space Forces Base**, 1,000 personnel a level.
- **100 personnel a point of fleet strength, 1,000 a marine battalion.**
  Artificial Intelligence halves ship crews, as it halves colony crews; marines
  are unchanged.
- **Hulls against marines: a player-set priority is the goal.** "A toggle in
  the UI or a priority marker for fleets (similar to the base priority for
  migrants) should be the goal. Either is okay as a short term thing if this
  ends up being complex." The migrants' priority is the colonies' settler
  priority, which steps Normal, High, Closed and Low (`sr_colony_priority_sgui`).
- **Short of personnel: the crewed share** scales fleet fire and marines'
  weight.
- **Occupied states still count.** The people are already in orbit. This
  departs, for personnel alone, from the rule every other space building
  follows (fleets design § 5.1).
- **Who dies: the destroyed half, and assault losses.** Damage kills nobody; a
  seizure now kills part of the landing force, a new step in the combat model.
- **The kill: a new pop type** for the bases' staff, the owner's suggestion.
- **Existing saves:** a one-time migration creates the levels each fleet power
  needs, with six months' grace.
- **The goods upkeep stays as it is** for now.
- **The base takes no goods**: its wages are its cost.

## 1. Today

### 1.1 What a fleet costs once built

- **Hulls.** Space Command builds fleet strength into the ground reserve each
  month (`sr_sc_month` → `sr_reserve_build`), and the reserve goes up to the
  home fleet while Auto is on (`sr_reserve_auto_step`) or all at once on Launch
  (`sr_fl_reserve_in_at`). Space Command's staff (500 officers, 2,000 engineers
  and 2,500 machinists a level) are shipyard workers. They build the ships, and
  nobody crews them.
- **Upkeep is goods only.** The building's maintenance line is multiplied by
  +900% for every 10 points of full strength, with the reserve included:
  7,560 a week a point (UI pass design § 10). That is the only running cost a
  fleet has.
- **Marines cost nothing at all.** A docked fleet at Earth is refilled to its
  carriers' room every month (`sr_fl_month_at` sets `sr_fl_<n>_marines` to
  `sr_fl_<n>_marine_capacity`, 2 battalions a point of carrier strength), and
  so is a fleet launched from the reserve. A seizure lands one battalion more
  than the garrison and militia (`sr_site_seize`), and those marines become
  the new garrison: none die.

### 1.2 Where ships and marines are lost

| Loss | Script | What happens to the record |
|---|---|---|
| Battle, the destroyed half | `sr_fl_cut_role` (`sr_fleet_effects.txt`), from `sr_fl_take_losses_at` | Strength now and at full both fall |
| Battle, the damaged half | the same | Strength now falls; repair brings it back |
| Attrition, out of supply | `sr_fl_attrition_at` (generated) | 5% of now and full a month |
| A slot below the minimum strength | `sr_fl_clear_at`, from `sr_fl_month_at` | The slot and the marines aboard are gone |
| Marines past the carriers' room | the trim at the end of `sr_fl_month_at` | The excess is gone (carriers lost in battle) |
| A garrison overrun | `sr_site_occupy`, `sr_site_liberate` | `sr_site_marines_<key>` is overwritten with the attacker's landed marines |
| A colony destroyed | `sr_site_destroy` → `sr_site_release_<key>` | Its garrison is removed |
| Other releases (abandonment, breaking away, a dead holder) | `sr_site_release_<key>` | Not yet traced per path: some may send marines home first |
| Not losses | `sr_site_end_occupation`, `sr_site_transfer_marines`, Transfer, a slot emptied by a transfer | The marines or hulls move. Nobody dies |

### 1.3 Vanilla's model: the Naval Administration

The base game already does what the request describes, for sailors. A Naval
Administration level employs 900 soldiers and 100 officers and grants
`country_sailors_max_add` 1,000, workforce-scaled (`pm_simple_sailor_recruitment`),
and ships draw their crews from that pool (a Dreadnought's `ship_crew_max_add`
is 1,200).

## 2. The proposal in brief

A new government building, the **Space Forces Base**, employs 1,000 people a
level of a new pop type and grants **Space Forces Personnel**, 1,000 a level,
workforce-scaled. A point of fleet strength needs 100 personnel, 50 with
Artificial Intelligence, and a marine battalion needs 1,000. Hulls leave the
ground reserve and marines come aboard only as far as personnel allow, in the
order the player sets. A fleet whose personnel later fall short fights at the
share it can crew. Ships destroyed, marines lost, and marines killed taking a
colony kill as many of the new pop type in the bases' states, and the census
books them as war dead.

## 3. The building and its people (R1, R2)

### 3.1 The building

- **`building_space_forces_base`**, `bg_government` for the reason Space Command
  gives (`05_zz_te_sr_space_command.txt`'s header: `bg_military` is the parent
  of the army and navy groups and has no building of its own). Unlocked by
  Space Militarization, `potential` Full Colonies (`sr_colonies_full_enabled`),
  government-built only. **Any state, any number of levels**: unlike Space
  Command there is no one-per-nation rule and no site rule.
- **Construction cost: low.** It is a barracks, not a shipyard. Vanilla's Naval
  Administration is `construction_cost_very_low`; Space Command is
  `very_high`.
- **One method group with one method to start**, "Space Forces Training":
  `level_scaled` 1,000 jobs of the new pop type (§ 3.2);
  `state_modifiers.workforce_scaled` `state_sr_space_personnel_add = 1000`. No
  goods inputs: its cost is its wages and the people it takes out of the
  workforce, as the Naval Administration's is.
- **The modifier type** `state_sr_space_personnel_add` in
  `sr_fleet_modifier_types.txt`: `script_only = yes`, `decimals = 0`, `color =
  good`, named "Space Forces Personnel". A state type, as
  `state_sr_ship_construction_add` is, so the kill can be split by state
  (§ 5.4).
- **Capacity**, a country value `sr_pers_capacity`, sums
  `modifier:state_sr_space_personnel_add` over **every** state the country
  owns, occupied or not (the owner's answer), unlike `sr_sc_rate_buildings`,
  which skips states failing `sr_state_held_by_owner`.
- **Never grant the type from a country-level source.** A state's `modifier:state_*`
  read includes the country's modifiers (`scripting_best_practices.md` §
  Reading Pops, Buildings and Wars for a Yearly Model), so a law or technology
  that carried it on the country would be counted once for every state. A
  later boost to personnel goes on the method, or is a separate country type.
- **File and art**: `common/buildings/05_zz_te_sr_space_forces_base.txt`, so it
  sorts after Space Command (`test_building_list_order.py`), a building icon
  and a method icon.

### 3.2 The new pop type

The base's staff are a pop type nothing else employs, so
`kill_population_in_state = { pop_type = <it> … }` reaches only them (§ 5.3).
It is the mod's first pop type (`common/pop_types/` holds none today, against
vanilla's fifteen), so it carries most of this work's risk and most of its
files. What it needs:

- **The definition**, after vanilla's `soldiers` (`vanilla_parsed/common/pop_types.json`):
  strata, `texture` and `color`, `wage_weight`, `dependent_wage`,
  `unemployment`, `can_always_hire`, `political_engagement_*`, the portrait
  fields, and whether it is `military = yes`, whose effect isn't recorded in
  the repo.
- **Who becomes one**: its qualifications, and so which pops the base can
  hire from.
- **Its needs and politics**: the strata's needs; the interest groups that
  draw it (Armed Forces first; the guide's introduction says Armed Forces
  counts each state's Soldiers and Officers).
- **The mod's pop-type tables**: the census (`demographics_params.py`, among
  them `DEATH_CAUSE_WAR_CLASSES`, and `gen_demographics.py`'s class and
  workplace terms), the journal map mode classes (`gen_journal_map_classes.py`
  and its siblings), and anything else keyed by pop type, found by a sweep in
  the design.
- **Its name, loc, icon and concept.**

One type or two (an enlisted type and an officer type, as vanilla splits
soldiers from officers) is the design's call (§ 11). Two keep the split's
politics and cost twice the definitions; either way the kill stays exact,
since neither type works anywhere else.

## 4. What draws on it (R3)

### 4.1 The rates

| What | Personnel | Value |
|---|---|---|
| A point of fleet strength, at full, any role | 100; 50 with Artificial Intelligence | `sr_pers_per_point` |
| A marine battalion, aboard or in a garrison | 1,000 | `sr_pers_per_battalion` |

A battalion is a vanilla battalion's manpower. A point of carrier strength
holds 2 battalions, so its marines need 2,000 people against the hull's own
100: marines are where the people go, as the request asks.

What that means at the starting build mix (warships 2, carriers 1, tenders 1,
so a quarter of the strength is carriers), with every carrier full and before
Artificial Intelligence:

| Fleet | Crews | Marines | Personnel | Base levels |
|---|---|---|---|---|
| 30 points | 3,000 | 15 battalions, 15,000 | 18,000 | 18 |
| 100 points | 10,000 | 50 battalions, 50,000 | 60,000 | 60 |
| 100 points, warships only | 10,000 | none | 10,000 | 10 |
| Two garrisons ("Garrison it" needs 2 battalions) | | 4,000 | 4,000 | 4 |
| Seizing a colony of 200,000 (10 militia battalions, no garrison): 11 land and 5 die (§ 5.2) | | 16 battalions, 16,000 | 16,000 | 16 |

Sixty levels of a 1,000-job building is a great power's army-sized
commitment, in the range of a vanilla army of 60 battalions. A 100-point fleet
already costs about 760,000 a week in goods, so the people are a second,
smaller check, and the larger part of it falls on the carriers.

### 4.2 In service and headroom

- **In service** = the crew per point × the full strength of every slot +
  1,000 × the marines aboard every slot and in every garrison we hold, or hold
  as occupier (`sr_site_marines_<key>`). Full strength, not current, since a
  damaged hull keeps its crew.
- **The ground reserve needs no crew until it launches**: its hulls are on the
  ground, waiting.
- **Headroom** = capacity − in service.

### 4.3 The gates

1. **Launching.** Auto and Launch move at most headroom ÷ the crew per point
   from the reserve, shared by the build mix. The rest waits, shown as
   awaiting crews. Space Command keeps building into the reserve, so no
   progress is lost while crews are short, and the bill buys real hulls. A
   player who doesn't want to pay for hulls nobody can crew pauses Space
   Command, which already exists.
2. **Marines** refill at Earth, and at a launch, to the lesser of the
   carriers' room and headroom ÷ 1,000.
3. **The order is the player's** (owner). The goal is a control in the panel:
   a toggle between hulls first and marines first, or a priority on each fleet
   that steps as the settlers' does (Normal, High, Closed, Low), with the
   reserve's launch taking a place in the same order. The first build can ship
   a fixed order. Hulls first is the cheaper one, since the country month
   already runs the reserve's Auto (`sr_sc_month`) before the slots' month
   refills marines (`sr_fl_each_slot`), and Auto off then puts marines
   first.

### 4.4 Short of personnel

When in service exceeds capacity (levels demolished or lost with a state, or
staffing short), the **crewed share** `sr_pers_ratio` = capacity ÷ in service, at most 1, applies to
everything in service:

- a fleet's fire on fleets and on Defences is multiplied by it, beside
  `sr_fleet_readiness` and `sr_fleet_quality`;
- marines count at that share wherever they are counted: a seizure's
  `sr_cb_mar_<key>`, a garrison's weight in `sr_site_garrison_need_<key>`, the
  AI's assault test.

This is the soft cap in place of a gate (the owner's default, 2026-10-16):
nothing is taken away, and everything works less well until the bases catch
up. A country with no base at all has a share of 0, which is why existing
saves need § 8.

### 4.5 Occupied states

**Bases in an occupied state still count** (owner): the people they supply
are in orbit. A land war doesn't thin an enemy's crews, though it can still
stop Space Command, the batteries and the launch site, which keep the fleets
design's § 5.1 rule. The bases' people in an occupied state can still die (§ 5.4), since
they are the owner's pops wherever the front is.

## 5. Casualties (R4)

### 5.1 How many die

- **Ships:** the crew per point × the strength destroyed (the fall in full
  strength) × the crewed share at the time. Uncrewed hulls have nobody
  aboard.
- **Damage kills nobody.** The damaged half is repaired with its crew.
- **Marines:** 1,000 × the battalions lost × the crewed share: carriers lost
  with marines aboard (the trim), a slot cleared, a garrison overrun, a colony
  destroyed with its garrison, and the assault's dead (§ 5.2).
- **Not deaths:** marines coming home, a transfer, a cession, a slot emptied
  by a transfer. A dead country's fleets have nobody left to kill.

### 5.2 Assault losses (new)

A seizure today lands the garrison need plus one battalion, and none die. With
this work the defence costs the attacker marines too:

- **The attacker's dead** are a share of the defence it overcomes: the
  garrison's battalions plus the militia's, × `sr_assault_loss_share`. A first
  guess is 0.5, so taking a colony held by 2 marine battalions and 10 militia
  costs 6 battalions, 6,000 people.
- **They come off the closing-in fleets' marines first**, the largest first.
  The landing still needs the garrison need plus one after them, so
  `sr_cb_seizes` and the AI's assault tests (`sr_fl_ai_assault_at`,
  `sr_fl_ai_lunar_assault`) read need + 1 + the losses, and a fleet that
  can't pay both waits, as one short of marines waits today.
- **The defenders' marines die** as § 5.1 counts them. The militia are colony
  people, a figure and not pops; whether a seizure takes some of them is not
  in this scope.
- **A liberation and a free colony's seizure** pay the same toll against
  what holds them.

### 5.3 Why a pop type: no kill by workplace

- The kill effects (`kill_population_in_state`,
  `kill_population_percent_in_state`, and the country's `kill_population`) take
  a pop type, strata, culture or religion, never a building. `kill_crew` is a
  ship-scope effect for vanilla's navy. Pop scope has no kill.
- So with soldiers and officers as staff, a kill would fall on every soldier in
  the state, the army's barracks included, at a split the engine chooses. With
  a type that only the base employs, it falls on the base's people and
  nobody else's.
- `kill_population_in_state` takes a constant, so a count is killed in steps
  (Internal Resettlement kills its transit dead 100 at a time in a `while`,
  carrying the fraction: `resettlement_effects.txt`). Whether
  `kill_population_percent_in_state`'s `percent` takes a script value is
  unverified.
- **A pop's people include its dependents**: its workforce is about a quarter
  to three tenths of it (`scripting_best_practices.md` § Reading Pops,
  Buildings and Wars, "The working-adult ratio"). Killing 1,000 people of the
  type takes about 270 of the base's employees, not 1,000. That is true of
  any pop type.

### 5.4 The kill

`sr_pers_dead_due` (country) collects the people at each loss site in § 1.2
and the assault in § 5.2; the fleets' country step pays it out, the one site
that kills. A garrison overrun charges the defender, read before
`sr_site_occupy` overwrites the record. `sr_fl_cut_role` is hand-written; the
attrition and the clear are generated by `gen_space_fleets.py`, so their hooks
go in the generator.

In each state holding bases, by its share of the capacity:

1. **Kill the count.** `kill_population_in_state = { value = 100 pop_type =
   <the type> }` in a `while`, with the remainder carried per country, so a
   small loss is killed once the losses add up to 100. Exact, and only the
   base's people.
2. **Free the jobs as well** (recommended for the design). Before the kill,
   `move_partial_pop` takes the dead's number of workers out of the base's
   pops (their share ÷ the pop's workforce share) into unemployment in the
   same state. The base's jobs then fall by the full number of dead, not a
   quarter of it, and the capacity comes back as the base rehires, at most a
   tenth of its jobs a week (`scripting_best_practices.md` § A New Building
   Hires a Tenth of a Level's Jobs a Week). That is the "losses take time to
   replace" vanilla's barracks have: a 60-level base back from 10,000 dead in
   about two weeks, a 5-level one from 5,000 in ten. Without it the bases
   refill a quarter of the gap at once, and lost marines are back sooner.

### 5.5 The census and the notices

- **War dead, not known kills.** `te_demog_note_kills` books every age and both
  sexes. The war dead's profile is 95% men of conscription age, which the
  census keeps in `te_dg_war_in` on the state. A small helper,
  `te_demog_note_war_dead = { VALUE = … }`, adds to it with the same guards
  (the census running, the state counted), and the new type joins
  `DEATH_CAUSE_WAR_CLASSES`.
- **Notices.** The battle report (`.101`) gains "N of our space forces were
  killed"; the occupation notice (`.102`) names the battalions lost on both
  sides and their people. The personnel hover (§ 7) shows the year's dead.

## 6. The AI

- **Builds bases** through `can_build_government` and a new
  `sr_pers_may_build_government`: while in service, plus the reserve awaiting
  crews and the carriers' unfilled room, exceeds capacity plus the levels
  queued, plus a margin of a fifth. `ai_value` as Space Command's, more at war.
- **Pauses Space Command** (`sr_sc_ai_should_pause` gains a term) when the
  reserve awaiting crews passes six months' construction and no base is
  queued.
- **Its assault test** compares marines at the crewed share with the need plus
  the assault's dead (§ 5.2), so it doesn't attack with marines it can't man
  or can't spare.
- **Its priority**, once § 4.3's control exists: marines first at war while it
  plans an assault, hulls first otherwise.

## 7. The panel and the guide

- **Space Command section:** a Personnel figure, in service over capacity,
  either a fifth overview cell or in the reserve cell, depending on the
  width. Its hover lists crews, marines aboard and in garrisons, the reserve
  awaiting crews, the bases' levels and staffing, and the year's dead.
- **The reserve cell** shows how many points are awaiting crews; the Launch and
  Auto hovers say how many points go up.
- **A fleet's card** shows "Crewed N%" in its head while the share is below 1,
  and later its priority (§ 4.3).
- **The building's tooltip** shows Space Forces Personnel from the method, as
  Space Command's shows Fleet Strength Built a Month.
- **The fleet's target hover** gives a seizure's price in marines, the need
  plus the assault's dead.
- **Player guide:** `16-space.md` § Space Command (the base, its people and
  the rates, with a row beside Space Command), § Battles in space (crews die),
  § Blockade, seizure and destruction (the assault's dead, a lost garrison's
  dead), § Holding Earth orbit (the reserve awaiting crews);
  `17-reference.md`'s Space fleets and Ground reserve rows; the new pop type
  where the guide names pop types (the introduction's Armed Forces line).
  Rebuild the PDF.

## 8. Existing saves (owner: create the levels, with grace)

A save with fleets and no base would wake with a crewed share of 0: every
fleet firing nothing. A one-time migration at the first fleets step after the
update (a flag on the country) creates, for each fleet power, the base levels
its personnel in service need, rounded up and government owned, in Space
Command's state, else the capital. The crewed share is held at 1 for six
months (`sr_pers_grace_until`) while those levels hire the new type, which
takes about ten weeks at a tenth a week. The nuclear delivery build's
migration of fielded legs is the precedent.

## 9. Engine facts to check

Each gets a once-a-game `TE_SELF_CHECK` line and a row in
`docs/testing/solar-colonies-playtest.md`:

1. **A mod pop type works**: it loads, the base hires it, it shows in the
   state's pops and the building's staff (`pers_pop_type`). The mod has never
   added one.
2. **The kill reaches it**: `kill_population_in_state` with the new
   `pop_type` lowers the type's people in the state by the count, a week on
   (`state_population` lags a tick: § `state_population` Doesn't Fall Until
   the Next Tick).
3. **What an unemployed member of the type becomes**: whether people the base
   lays off or § 5.4's move frees keep the type (and so are still the kill's
   target) or turn into another.
4. **`move_partial_pop` into the pop's own state** frees the jobs and keeps the
   people there (`pers_move_out`). If it fails, the kill alone still works.
5. **The capacity sum** equals staffed jobs ÷ jobs × 1,000 a level, with no
   country-level copy in it (`pers_capacity_sum`).
6. **Whether `kill_population_percent_in_state` takes a script value.** If it
   does, the loops go.

## 10. The open calls, answered (owner, 2026-11-24)

Each line gives the answer, and the recommendation where the owner chose
otherwise.

1. **The name: Space Forces Base.**
2. **The rates: 100 personnel a point and 1,000 a battalion**, with
   Artificial Intelligence halving ship crews and marines unchanged.
3. **Who goes first: the player's choice**, a panel toggle or a per-fleet
   priority like the settlers' (the recommendation was hulls first, fixed).
   Either fixed order is fine for a first build if the control is complex.
4. **Short of personnel: the crewed share** on fire and on marines' weight.
5. **Occupied states: their bases still count** (the recommendation was that
   they count for no one, as every other space building's).
6. **Who dies: the destroyed half, plus assault losses** (the recommendation
   was the destroyed half alone).
7. **The kill mechanism: a new pop type**, the owner's suggestion (the
   recommendation had been to move soldiers and officers out of the jobs, then
   kill).
8. **Existing saves: create the levels and a six-month grace.**
9. **The goods upkeep: unchanged**, to revisit after a balance pass reads the
   bases' wages against it.
10. **The building's inputs: none**, wages only.

## 11. For the design

Calls the scope leaves to the design, with my lean where I have one:

- **The pop type's name**, and **one type or two** (lean: one, which halves the
  definitions and the tables; two if the officers' politics matter).
- **Its strata, wages and qualifications** (lean: soldiers' lower strata and
  `can_always_hire`, so a base staffs anywhere, as barracks do), and whether
  it is `military = yes`.
- **The priority's form**: a toggle, or a priority per fleet with the reserve
  in the same order.
- **The assault's toll**: `sr_assault_loss_share` (0.5 to start) and whether
  the militia take losses.
- **Whether to free the jobs** with the move in § 5.4 (lean: yes, if the
  engine check passes).

## 12. Build order

Three PRs, so the risky parts land separately:

1. **The pop type and personnel.** The pop type and every table it joins; the
   building, method and modifier type; capacity, in service, headroom and the
   crewed share; the launch and marine gates in a fixed order (hulls first);
   the shortfall in combat; the AI's bases and pause; the migration; the
   panel; the guide; self-checks 1 and 5. Values in `sr_fleet_values.txt`; any
   per-slot reads in `gen_space_fleets.py`.
2. **Casualties and assault losses.** The accruals at each loss site
   (hand-written and generated), the assault's toll in the seizure and the AI's
   tests, the monthly kill, the census's war dead helper, the notices,
   self-checks 2, 3, 4 and 6, the guide's battle and seizure lines.
3. **The priority.** The toggle or the per-fleet priority, the AI's use of
   it, the panel and the guide.

## 13. Not changed

Space Command's staff, methods and goods upkeep; the fleets design's § 5.1
occupation rule for Space Command, the batteries, the Orbital Battlestation and the launch site;
the Battlestation and batteries' own staff; colony crews and militia (bar
the militia question in § 11); vanilla's army and navy; Simple Colonies and Races
Only, where none of this runs. A rule switched off mid-game leaves the bases
standing with their staff, as it leaves Space Command.
