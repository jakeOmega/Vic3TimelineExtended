# Space forces personnel: crews and marines drawn from a building, and killed with them: scope

Drafted 2026-11-24 from the owner's request. This is a scoping document: what to
build, in what order, and the calls the owner has to make. It is not yet a
design, and it has no implementation plan. Later sessions write both.

**Status (2026-11-24):** scope only. The open calls in § 10 are unanswered.
Each has a recommendation.

Read first: `docs/systems/mod_systems/space_race.md` § Fleets, Space Command and
combat; the fleets design
(`docs/superpowers/archive/specs/2026-10-26-solar-colonization-fleets-design.md`)
§§ 3 to 5, 9.6 and 15; and the Space Race UI pass design
(`2026-10-31-space-race-ui-pass-design.md`) § 10, for the fleets' upkeep.

## The request (owner, 2026-11-24)

> Right now, marines and fleets in space are free once built. I think we should
> make them be limited by a new government building that employs soldiers and
> officers and adds a new script-only modifier type, with marines using a fair
> bit of manpower and fleets not that much. Ideally, when ships are destroyed or
> marines lost, a proportional amount of people employed in these buildings
> should die.

Read as four requirements:

- **R1.** A new government building that employs soldiers and officers.
- **R2.** A new script-only modifier type the building grants, which is the
  capacity.
- **R3.** Fleets and marines draw on that capacity: marines a lot, ships a
  little.
- **R4.** Ships destroyed and marines lost kill a matching number of the
  building's staff.

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
  so is a fleet launched from the reserve. A battalion lost in a seizure is
  back the next month.

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
is 1,200). The mod's Military Base (`bg_government`, 200 soldiers and 50
officers a level) shows that soldiers and officers work in a government
building.

## 2. The proposal in brief

A new government building, the **Space Forces Base**, employs 900 soldiers
and 100 officers a level and grants **Space Forces Personnel**, 1,000 a level,
workforce-scaled. A point of fleet strength needs 100 personnel, and a marine
battalion 1,000. Hulls leave the ground reserve and marines come aboard only
as far as personnel allow. A fleet whose personnel fall short later, because a
base's state is occupied or a base loses staff, fights at the share it can
crew. Ships destroyed and marines lost take as many people out of the bases'
jobs, and the same number of soldiers and officers die in those states. The
census books them as war dead.

## 3. The building (R1, R2)

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
  `level_scaled` 900 soldiers and 100 officers; `state_modifiers.workforce_scaled`
  `state_sr_space_personnel_add = 1000`. **No goods inputs**: like the Naval
  Administration, its cost is its wages and the people it takes out of the
  workforce (open call 10).
- **The modifier type** `state_sr_space_personnel_add` in
  `sr_fleet_modifier_types.txt`: `script_only = yes`, `decimals = 0`, `color =
  good`, named "Space Forces Personnel". It is a state type, as
  `state_sr_ship_construction_add` is, so the sum can skip occupied states
  (§ 4.5) and the casualties can be split by state (§ 5.4).
- **Capacity**, a country value `sr_pers_capacity`, sums
  `modifier:state_sr_space_personnel_add` over the states that pass
  `sr_state_held_by_owner`, as `sr_sc_rate_buildings` does.
- **Never grant the type from a country-level source.** A state's `modifier:state_*`
  read includes the country's modifiers (`scripting_best_practices.md` §
  Reading Pops, Buildings and Wars for a Yearly Model), so a law or technology
  that carried it on the country would be counted once for every state. A
  later boost to personnel goes on the method, or is a separate country type.
- **File and art**: `common/buildings/05_zz_te_sr_space_forces_base.txt`, so it
  sorts after Space Command (`test_building_list_order.py`), a building icon
  and a method icon.

## 4. What draws on it (R3)

### 4.1 The rates

| What | Personnel | Value |
|---|---|---|
| A point of fleet strength, at full, any role | 100 | `sr_pers_per_point` |
| A marine battalion, aboard or in a garrison | 1,000 | `sr_pers_per_battalion` |

A battalion is a vanilla battalion's manpower. A point of carrier strength
holds 2 battalions, so its marines need 2,000 people against the hull's own
100: marines are where the people go, as the request asks.

What that means at the starting build mix (warships 2, carriers 1, tenders 1,
so a quarter of the strength is carriers), with every carrier full:

| Fleet | Crews | Marines | Personnel | Base levels |
|---|---|---|---|---|
| 30 points | 3,000 | 15 battalions, 15,000 | 18,000 | 18 |
| 100 points | 10,000 | 50 battalions, 50,000 | 60,000 | 60 |
| 100 points, warships only | 10,000 | none | 10,000 | 10 |
| Two garrisons ("Garrison it" needs 2 battalions) | | 4,000 | 4,000 | 4 |
| Seizing a colony of 200,000 (10 militia battalions, so 11 land) | | 11,000 | 11,000 | 11 |

Sixty levels of a 1,000-job building is a great power's army-sized
commitment, in the range of a vanilla army of 60 battalions. A 100-point fleet
already costs about 760,000 a week in goods, so the people are a second,
smaller check, and the larger part of it falls on the carriers.

### 4.2 In service and headroom

- **In service** = 100 × the full strength of every slot + 1,000 × the marines
  aboard every slot and in every garrison we hold, or hold as occupier
  (`sr_site_marines_<key>`). Full strength, not current, since a damaged hull
  keeps its crew.
- **The ground reserve needs no crew until it launches**: its hulls are on the
  ground, waiting.
- **Headroom** = capacity − in service.

### 4.3 The gates

1. **Launching.** Auto and Launch move at most headroom ÷ 100 points from the
   reserve, shared by the build mix. The rest waits, shown as awaiting crews.
   Space Command keeps building into the reserve, so no progress is lost
   while crews are short, and the bill buys real hulls. A player who doesn't
   want to pay for hulls nobody can crew pauses Space Command, which already
   exists.
2. **Marines** refill at Earth, and at a launch, to the lesser of the
   carriers' room and headroom ÷ 1,000.
3. **Hulls first, then marines.** The country month already runs the reserve's
   Auto (`sr_sc_month`) before the slots' month refills marines
   (`sr_fl_each_slot`), so new hulls take the headroom first. A player who
   wants the marines first turns Auto off (open call 3).

### 4.4 Short of personnel

When in service exceeds capacity (a base's state occupied, levels demolished
or lost with a state, or staffing short), the **crewed share** `sr_pers_ratio` = capacity ÷ in service, at
most 1, applies to everything in service:

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

Bases in a state their owner doesn't control add nothing, by the rule
(`sr_state_held_by_owner`) that already applies to Space Command, the batteries and
the Orbital Battlestation (fleets design § 5.1). A land war against the
bases' states thins the crews of every fleet in orbit, which is a new lever
for the side without fleets (open call 5).

## 5. Casualties (R4)

### 5.1 How many die

- **Ships:** 100 × the strength destroyed (the fall in full strength) × the
  crewed share at the time. Uncrewed hulls have nobody aboard.
- **Damage kills nobody.** The damaged half is repaired with its crew (open
  call 6).
- **Marines:** 1,000 × the battalions lost × the crewed share: carriers lost
  with marines aboard (the trim), a slot cleared, a garrison overrun, a colony
  destroyed with its garrison.
- **Not deaths:** marines coming home, a transfer, a cession, a slot emptied
  by a transfer. A dead country's fleets have nobody left to kill.
- **Seizing costs the attacker nothing today**: the landing force is placed,
  not fought. This scope doesn't add assault casualties (open call 6).

### 5.2 One accrual per loss, one kill site

Each loss site in § 1.2 adds the people to a country variable on the loser,
`sr_pers_dead_due`. The owner's next fleets country step pays it out, the one
site that kills. A garrison overrun adds to the defender, read before
`sr_site_occupy` overwrites the record. `sr_fl_cut_role` is hand-written and
called by the generated `sr_fl_take_losses_at`. The attrition and the clear
are generated by `gen_space_fleets.py`, so the hooks go in the generator.

### 5.3 The engine's limit: no kill by workplace

- The kill effects (`kill_population_in_state`,
  `kill_population_percent_in_state`, and the country's `kill_population`) take
  a pop type, strata, culture or religion, never a building. `kill_crew` is a
  ship-scope effect for vanilla's navy. Pop scope has no kill.
- `kill_population_in_state` takes a constant, so a count is killed in steps
  (Internal Resettlement kills its transit dead 100 at a time in a `while`,
  carrying the fraction: `resettlement_effects.txt`). Whether
  `kill_population_percent_in_state`'s `percent` takes a script value is
  unverified.
- **A pop's people include its dependents**: its workforce is about a quarter
  to three tenths of it (`scripting_best_practices.md` § Reading Pops,
  Buildings and Wars, "The working-adult ratio"). Killing 1,000 people from the
  base's soldiers takes about 270 of its employees, not 1,000.

So "kill 1,000 soldiers in that state" would fall on every soldier there (the
army's barracks, the Military Base and conscription centers included), at a
split the engine chooses, and would take about a quarter of that from the
base's jobs.

### 5.4 The mechanism: move them out of the jobs, then kill

For each state holding bases, in proportion to its share of the capacity:

1. **Free the jobs.** `every_scope_pop` limited to
   `pop_employment_building = building_space_forces_base`, soldiers then
   officers, `move_partial_pop = { state = <this state> population = <the
   pop's share ÷ its workforce share> }`. The base loses exactly as many
   employees as died, and they stay in the state, unemployed.
2. **Kill the count.** `kill_population_in_state = { value = 100 pop_type =
   soldiers }` in a `while`, and the same for officers, at the method's 90 and
   10, with the remainder carried per country, so a small loss is killed once
   the losses add up to 100.

The base's jobs fall by exactly the dead, and so does the state's population.
Which soldier pop's people die is still the engine's choice, so a base sharing
a state with a large army takes about its share of the deaths. The survivors
of the moved group are unemployed soldiers in the same state, the first
anyone hires back. The capacity falls with the jobs and comes back as the
base rehires, at most a tenth of its jobs a week
(`scripting_best_practices.md` § A New Building Hires a Tenth of a Level's
Jobs a Week). That is the "losses take time to replace" vanilla's barracks
have: a 60-level base back from 10,000 dead in about two weeks, a 5-level one
from 5,000 in ten.

Fallbacks, if the move does not do what step 1 expects (§ 9):

- **Kill only.** Step 2 alone. Simpler, but the capacity barely falls, so lost
  marines are back the next month as today, minus the people.
- **A training debt.** Step 2, plus a script figure that removes the dead from
  capacity and drains at a tenth of the bases' jobs a week. Exact, with no
  engine question, but it imitates hiring instead of using it.

### 5.5 The census and the notices

- **War dead, not known kills.** `te_demog_note_kills` books every age and both
  sexes. Soldiers are the war dead's profile, 95% men of conscription age,
  which the census keeps in `te_dg_war_in` on the state. A small helper,
  `te_demog_note_war_dead = { VALUE = … }`, adds to it with the same guards
  (the census running, the state counted).
- **Notices.** The battle report (`.101`) gains "N of our space forces were
  killed"; the occupation notice (`.102`) names the garrison's battalions and
  people. The personnel hover (§ 7) shows the year's dead.

## 6. The AI

- **Builds bases** through `can_build_government` and a new
  `sr_pers_may_build_government`: while in service, plus the reserve awaiting
  crews and the carriers' unfilled room, exceeds capacity plus the levels
  queued, plus a margin of a fifth. `ai_value` as Space Command's, more at war.
- **Pauses Space Command** (`sr_sc_ai_should_pause` gains a term) when the
  reserve awaiting crews passes six months' construction and no base is
  queued.
- **Its assault test** (`sr_fl_ai_assault_at`, `sr_fl_ai_lunar_assault`)
  compares marines at the crewed share with the garrison's need, so it doesn't
  attack with marines it can't man.

## 7. The panel and the guide

- **Space Command section:** a Personnel figure, in service over capacity,
  either a fifth overview cell or in the reserve cell, depending on the
  width. Its hover lists crews, marines aboard and in garrisons, the reserve
  awaiting crews, the bases' levels and staffing, and the year's dead.
- **The reserve cell** shows how many points are awaiting crews; the Launch and
  Auto hovers say how many points go up.
- **A fleet's card** shows "Crewed N%" in its head while the share is below 1.
- **The building's tooltip** shows Space Forces Personnel from the method, as
  Space Command's shows Fleet Strength Built a Month.
- **Player guide:** `16-space.md` § Space Command (the base and the rates, with
  a row beside Space Command), § Battles in space (crews die), § Blockade,
  seizure and destruction (a lost garrison's dead), § Holding Earth orbit (the
  reserve awaiting crews); `17-reference.md`'s Space fleets and Ground reserve
  rows. Rebuild the PDF.

## 8. Existing saves

A save with fleets and no base would wake with a crewed share of 0: every
fleet firing nothing. Recommended: a one-time migration at the first fleets
step after the update (a flag on the country). For each fleet power it creates
the base levels its personnel in service need, rounded up and government
owned, in Space Command's state, else the capital. The crewed share is held at
1 for six months (`sr_pers_grace_until`) while those levels hire, which takes
about ten weeks at a tenth a week. The nuclear delivery build's migration of
fielded legs is the precedent.

## 9. Engine facts to check

Each gets a once-a-game `TE_SELF_CHECK` line and a row in
`docs/testing/solar-colonies-playtest.md`:

1. **`move_partial_pop` into the pop's own state** frees the jobs and keeps the
   people there, unemployed (`pers_move_out`: the base's employees a week on).
   If it fails, use the fallbacks in § 5.4.
2. **The kill's count**: the state's population a week on is lower by the dead
   (`state_population` lags a tick: § `state_population` Doesn't Fall Until the
   Next Tick).
3. **The capacity sum** equals staffed jobs ÷ jobs × 1,000 a level, with no
   country-level copy in it (`pers_capacity_sum`).
4. **Soldiers and officers hire into the base at this size.** The Military
   Base shows that they do at 250 a level.
5. **Whether `kill_population_percent_in_state` takes a script value.** If it
   does, the loops in step 2 go.

## 10. Open calls for the owner

1. **The name.** Space Forces Base (recommended), Space Forces Garrison or
   Space Corps Barracks.
2. **The rates.** 100 personnel a point and 1,000 a battalion (recommended).
   Should Artificial Intelligence halve ship crews, as it halves colony crews?
   Recommended: yes for ships, and marines unchanged.
3. **Who goes first when headroom is short.** Hulls first, then marines
   (recommended: it is the order the month already runs, and Auto off puts
   marines first), or marines first.
4. **Short of personnel.** The crewed share on fire and on marines' weight
   (recommended), or marines past capacity stood down, with no deaths.
5. **Occupied states.** Their bases count for no one (recommended, the rule
   every space building follows), or they still count because the people are
   in orbit.
6. **Who dies.** Only the destroyed half (recommended), or a share of the
   damaged half too; and whether a seizure should kill part of the landing
   force (recommended: not in this work).
7. **The kill mechanism.** Move out, then kill (recommended), kill only, or
   the training debt (§ 5.4).
8. **Existing saves.** Create the levels and a six-month grace (recommended),
   the grace alone, or nothing.
9. **The goods upkeep.** Unchanged (recommended); revisit after a balance pass
   reads the bases' wages against it.
10. **The building's inputs.** None (recommended, as the Naval
    Administration), or Small Arms and Ammunition as the Military Base takes.

## 11. Build order

Two PRs, so the capacity half can ship even if the kill needs a second try:

1. **Personnel.** The building, method and modifier type; capacity, in
   service, headroom and the crewed share; the launch and marine gates; the
   shortfall in combat and the AI's assault test; the AI's bases and pause;
   the migration; the panel; the guide; self-checks 3 and 4. Values in
   `sr_fleet_values.txt`; any per-slot reads in `gen_space_fleets.py`.
2. **Casualties.** The accruals at each loss site (hand-written and
   generated), the monthly kill, the census's war dead helper, the notices,
   self-checks 1, 2 and 5, the guide's battle and seizure lines.

## 12. Not changed

Space Command's staff, methods and goods upkeep; the Orbital Battlestation and
the ground-to-orbit batteries, which have staff of their own; colony crews and
militia; vanilla's army and navy; Simple Colonies and Races Only, where none of
this runs. A rule switched off mid-game leaves the bases standing with their
staff, as it leaves Space Command.
