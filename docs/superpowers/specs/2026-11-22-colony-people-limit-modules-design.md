# Colony people limit modules: design

Part B of the scope merged in #1954
(`2026-11-22-colony-people-and-off-world-tourism-scope.md` §§ 3–5), from the
owner's answers there (§ 5) and on this design's first outline (2026-11-22).
Part A, the Resort Colony free of its state, was built in #1957.

Read first: the scope's § 3 (what it found and why), `space_race.md` §§ Colony
population, Colony modules and Extraplanetary Base room, Autonomy; the colony
management design (`2026-10-30-colony-management-design.md`) § 4.2 (where
autonomy settles) and § 5 (slots).

## 1. Intent

A colony's people, not its slots, decide how much it can run. Today slots run
out before crews do, and from era 12 Artificial Intelligence waives crews
entirely, so people give prestige, autonomy pressure and militia and little
else. The owner wants people to be the limit: more people run more modules,
holding a large colony costs something, and settlers are bounded only by the
people a country has and the Launch Capacity it can buy ("If you have the
population and the launch capacity, I don't really see what limit there is in
moving people to your new colonies").

**Goals**

- Crews limit modules, at every era. The Habitat is the one capped module.
- Settlers are an open-ended amount, paid in Launch Capacity, drawn from the
  whole country.
- A large colony presses for autonomy hard enough that Administrations, a
  charter, a garrison or letting it go are each a real choice, and
  Administrations cost authority.
- A player can see, everywhere it matters, how many crews a colony needs and
  has, and what the next module will do to them.

**Non-goals**

- No limit on how many of one module a world holds (owner, call 4: "We may
  add limits later, but let's see how it does without first"). § 8 tabulates
  what that allows, for the play-test.
- A world's own Extraplanetary Base and Resort Colony room stays automated: a
  colony with no people is still a working mine.
- No repair of saves started before this lands (as for #1950).

**Anti-goals** (would make it a failure even if it works)

- A reward for switching settlers off and on, or for timing them to launch
  windows. Settlers leave monthly whatever the windows, as today.
- A bill that quietly grows with something else: the settler bill must follow
  the settlers, not the Space Program's other throughput (§ 6.2).
- A colony that loses people because its holder changed: a cession or a
  break-away must not shrink the Habitats it was built with (§ 4.4).

## 2. Approaches

**The settler bill.** The owner chose Launch Capacity per settler on the Space
Program (call 5). The engine drops a goods `_add` applied by `add_modifier`
(`scripting_best_practices.md` § "Goods I/O modifiers: PM-applied vs
runtime-applied"), so the bill can't be its own input line.

1. **A `_mult` on the building's whole Launch Capacity input**, sized each
   month so it adds the settlers' Launch Capacity: the mod's runtime-scaling
   pattern (Strategic Reserve, uploaded minds). **Chosen.** An understaffed
   programme pays a little less, which the owner accepted: "You cannot
   (easily) reduce employment at a Space Program".
2. Keep today's +5% throughput a level. Rejected in the scope: throughput
   also raises the programme's innovation, prestige, fabrication points and
   Module Storage, so an open-ended rate would be a reward. The owner
   confirmed that bonus goes.
3. A production method group of settler amounts. Rejected: methods are a
   fixed list, which is a fixed top.

**Where settlers come from.** The owner pointed to the Settlement Authority's
walk (call 6). The engine has no effect that takes part of one pop off the
map. `move_partial_pop` only moves people to another state, and the only ways
to remove people are `kill_population_in_state` and its kin, which take a
fixed number from a state or country by stratum or pop type.

1. **Every state gives the same share of its people**, removed there by
   stratum, each state's fraction carried to the next month until it makes a
   batch. **Chosen** (owner, 2026-11-22). It reads only `state_population`,
   so it needs no count of a state's pops, and the draw is spread over the
   whole country.
2. Walk the states largest first, as the Authority does, taking at most 2% of
   a stratum a month from each and stopping once the month is filled. Its
   first draft here. Rejected (owner): at large amounts the draw lands on one
   or two states (32,000 a month from a 4-million state is about 10% of its
   people a year), and it counts each source's pops.
3. Run the Authority's walk as it is, moving each pop's 2% to the Space
   Program's state, then remove the same number there. It keeps the per-pop
   cap exactly, but moves everyone twice, counts every source's pops each
   month (what made the 17-second tick, `late_game_performance.md` § "The
   USA of 1977"), and removes whichever of the launch state's pops the kill
   picks, so that state's mix drifts.

   What the colony programme keeps from the Authority is its census booking
   (§ 6.3).

**Habitat room from the technologies.** One script-only country modifier,
+0.1 Habitat room share a technology, read through the holder as
`country_sr_colony_growth_add` is. It replaces `country_sr_colony_slots_add`
on the same five technologies, so their tooltips show the new reward. No
alternative was worth sketching.

## 3. Decided (owner, 2026-11-22)

From the scope's § 5 and this design's outline:

1. The slot technologies give more people per Habitat: +10 points of the
   world's base room each, 50% to 100% with all five.
2. Artificial Intelligence halves the crew a level needs.
3. A colony short of crews runs every crewed module at the same share.
4. A crew is 10,000 people. No concentration limit for now.
5. Settlers cost Launch Capacity on the Space Program, the same price for
   every world: about 3 a settler, so 2,000 a month costs what High does now
   ("Fine"). The +15% throughput bonus goes ("that's intended").
6. Settlers come from the country's states, half middle strata and half
   lower: every state gives the same share of its people, at most 1% of the
   country's people a month (owner, on the builder check, 2026-11-22).
7. Past the Habitat cap, no limit, at the rising price; the stock rule stays.
8. An Administration costs authority, **about 25 a level** (owner).
9. The automatic destination pick weighs the Habitat cap.
10. The AI's settlers share fabrication's 5% of weekly income (owner, on the
    builder check): together they never pass it, so its space spending stays
    within the mission's 10% plus that 5%.

## 4. The rule

### 4.1 Slots go

Any module may be queued at any colony at the flat price,
`sr_module_points` (100). Every slot test leaves the queue triggers, the
landing's install, the AI plan, a colony's own builds and the panel. What
limits a colony is:

- **Crews.** Staffing stays (crews + 1) ÷ crewed levels, at most 1, where
  crewed levels are the specializations, Defences, Spaceport and the eleven
  facilities, and the +1 is the founding specialization's level, which runs
  without a crew. The staffed levels of a colony therefore sum to crews + 1
  however many are built, so a module past the crews adds nothing in total and
  thins the rest. That is the soft cap; there is no other penalty.
- **The specializations' budget** of four levels between the two, as now.
- **Terraforming's** three levels, as now.
- **The Habitat cap** (§ 4.3).
- **Fabrication and shipping**, as now: 20 queue places, eight shipment slots
  (the Moon needs none), two modules a month at most.

### 4.2 Crews

- `CREW_PER_LEVEL` becomes 10,000. A holder with `artificial_intelligence`
  needs 5,000 (`sr_site_crew_per_level_<key>`, read through the holder, so a
  cession changes it with the holder). Races Only still needs none.
- The waiver goes everywhere it is read: staffing, the AI plan's crew test,
  the panel's AGI text (`sr_disp_agi`, `je_space_race_widget_settlers_agi`).
- A free colony has no holder and counts at 10,000.

### 4.3 The Habitat cap

- The table's `slots` (1 to 4) becomes the world's **Habitat cap**,
  `sr_site_hab_cap_<key>`, a constant: no technology changes it.
- Past the cap the n-th Habitat costs `sr_module_points` × (1 + n), with no
  top (today's `SLOTS_PAST_MAX` goes). Habitats built and on their way, every
  shipper's, set the price, as slots do now (`sr_mod_generic_cost_<key>`
  becomes the Habitat's price; every other module costs the flat price).
- **The stock rule stays for Habitats**: one is queued past the cap only while
  its price fits in the module stock (`sr_mod_next_cost_<key> <=
  sr_mod_fab_stock_cap`). So Module Storage and fabrication set the reach:

| Country | Stock | Furthest Habitat past the cap |
|---|---|---|
| No storage, 5 points a month | 560 | 4th |
| Component Depot, 12.5 a month | 1,650 | 15th |
| Orbital Depot, 25 a month | 3,800 | 37th |

- The fill rule stays: a Habitat queued while the stock was larger is still
  built (`sr_mod_fab_stock_fill_cap`).
- A Habitat landing always installs (no cap to be lost against). A module of
  any other type installs while its own cap has room (specializations,
  Terraforming), or always.

### 4.4 Habitat room

- A Habitat adds `sr_site_hab_share_<key>` of the world's base room:
  0.5 plus the holder's `country_sr_habitat_room_add` (§ 5).
- **The world keeps the best share it has had.** The share is a global record,
  set in the world's monthly step to the larger of itself and the holder's
  share, and cleared on release. A cession to a holder with fewer technologies,
  a break-away and an heir keep the room the Habitats were built with. Without
  this, growth's `max = sr_site_room_held_<key>` would cut a freed colony's
  people to the smaller room the next month (my call).
- Terraforming's share adds to it as now. The dismantle guard
  (`sr_md_room_less_hab_<key>`) takes one Habitat's share off the same figure.

People a world holds at its cap, every world built out:

| Habitat share | People, all 40 worlds | Crews at 10,000 | Crews with AI |
|---|---|---|---|
| 50% (no technology) | 2.15 million | 209 | 429 |
| 100% (all five) | 3.36 million | 332 | 671 |
| 100%, Terraforming finished on its nine worlds | 4.50 million | 446 | 899 |

| World | Base room | Cap | People at cap, 100% | Crews | With AI |
|---|---|---|---|---|---|
| Valles Marineris, Hellas Planitia, Utopia Planitia | 50,000 | 4 | 250,000 (400,000 terraformed) | 25 | 50 |
| Olympus Mons, Arcadia Planitia, Ceres, Ganymede, Callisto, Titan, Marius Hills | 40,000 | 3 | 160,000 (280,000 terraformed, all but Ceres and Marius Hills) | 16 | 32 |
| Europa | 30,000 | 3 | 120,000 | 12 | 24 |
| Mercury | 25,000 | 3 | 100,000 | 10 | 20 |
| Venus Cloud Habitat | 30,000 | 2 | 90,000 (180,000 terraformed) | 9 | 18 |
| Vesta, Shackleton, Mare Imbrium | 25,000 | 2 | 75,000 | 7 | 15 |
| Psyche, Pallas, Enceladus, Rhea, Titania, Oberon, Triton, Pluto, Tranquility Base | 20,000 | 2 | 60,000 | 6 | 12 |
| Hygiea, Io, Iapetus, Ariel | 15,000 | 2 | 45,000 | 4 | 9 |
| Peary Crater | 15,000 | 1 | 30,000 | 3 | 6 |
| The ten 10,000 worlds (Himalia, Sedna, …) | 10,000 | 1 | 20,000 | 2 | 4 |

## 5. The five technologies

Nuclear Thermal Propulsion, Orbital Manufacturing, Advanced Nanofabrication,
Space Colonization and Molecular Assemblers each carry
`country_sr_habitat_room_add = 0.1` (script-only,
`space_race_modifier_types.txt`, shown as a percentage: "+10% Habitat room")
in place of `country_sr_colony_slots_add = 1`. `02-timeline.md` describes them.

## 6. Settlers

### 6.1 The amount

- `sr_emig_level` stays, as the step: 0 Off, and step n sends
  500 × 2^(n − 1) a month, so 1, 2 and 3 are today's Low, Steady and High and
  a running game keeps its setting. The panel shows the number, not a name.
- − halves (500 to Off); + doubles. **No fixed top**: + is valid while this
  month's amount is below the open colonies' free room
  (`sr_emig_open_room_total`), since a doubling past it sends no one more. Its
  hover says so (my call).
- Each month sends the amount, never more than the free room or 1% of the
  country's people (§ 6.3), in batches of 500 (250 middle strata, 250 lower).
- **Distribution is unchanged**: priority × free room, in passes, so every
  settler sent lands.
- **None leave** while launches are barred, under Races Only, or with no
  Space Program, as now.

### 6.2 The bill

- **3 Launch Capacity a settler** (`sr_emig_lc_per_settler`), the same for
  every world. A week's bill is last month's settlers × 3 × 12 ÷ 52:

| Settlers a month | Launch Capacity a week | At the base price (200) |
|---|---|---|
| 500 | 346 | £69,000 |
| 2,000 (today's High; it costs 1,500 and more now) | 1,385 | £277,000 |
| 8,000 | 5,538 | £1.1 million |
| 32,000 | 22,154 | £4.4 million |
| 128,000 | 88,615 | £17.7 million |

  The price of Launch Capacity rises as the programme buys more, which is the
  brake the owner named.
- **The mechanism**: a building modifier `sr_settler_launches`,
  `goods_input_launch_capacity_mult = 0.01`, on the Space Program at
  `sr_emig_bill_units` = 100 × the week's bill ÷ (the building's Launch
  Capacity at full staff × (1 + the country's
  `building_space_program_throughput_add`)).
  - *The building's Launch Capacity at full staff* (`sr_emig_lc_base`) is the
    sum of its active methods' lines, read with `has_active_production_method`:
    the mission (Earth Orbit 500, Moon 1,500, Mars 5,000, Solar Colonization
    10,000, Deep Space 50,000, Interstellar 100,000), debris removal (300, 300,
    150), fabrication (1,300, 2,600, 4,800) and the Orbital Depot (450). The
    Space Program is one level (`expandable = no`). A test holds the figures
    to the methods' files.
  - *Dividing out the throughput* keeps the bill on the settlers: module
    upkeep (+1% a level past each colony's first) and free colony supply
    (+3% a colony) raise the programme's throughput, and with 300 modules
    that is +300%, which would otherwise quadruple the settler bill.
    State-scope throughput (devastation, riots) is not divided out.
- **One refresh site**, `sr_emig_bill_refresh`, after `sr_emig_month` in the
  same pulse: remove, then add at `root.var:sr_emig_bill_units` through
  `every_scope_building`, the ground-types pattern (`sr_eb_apply_mix`), and
  skip the add at 0. `sr_emigration_programme` (the throughput) is removed
  from the entry and its static modifier deleted.
- The goods axis `goods_input_launch_capacity_mult` must be registered if it
  isn't (`modifier_field_audit` says).

### 6.3 Where they come from

Every state gives the same share of its people (owner, 2026-11-22). Each
month, once the month's settlers are known (the amount, never more than the
open colonies' free room):

1. **The share.** `sr_emig_share` = the month's settlers ÷ the country's
   people (the sum of its states' `state_population`), at most
   `sr_emig_people_cap` (1%): a country can't send more than 1% of its people
   in a month, however high the amount is set. Above that the month sends 1%,
   and the panel says so.
2. **Each state's due**: `sr_emig_due` (a state variable) = the share ×
   `state_population` + the state's carry (`sr_emig_carry`, what it owed
   and didn't give before). One pass over the country's states, reading only
   `state_population`, so no count of a state's pops.
3. **The take**, a second pass with `ordered_scope_state` by `var:sr_emig_due`,
   largest first: each state gives its whole batches of 500 (`floor(due ÷
   500)`) while the month has settlers left to find, and keeps the rest as its
   carry. A state the month runs out before keeps its whole due, so it comes
   earlier next month. Over a few months every state gives its share; a small
   state gives a batch every few months.
4. **The removal**, in each state that gives: `while = { count = <batches> }`
   of `kill_population_in_state = { value = 250 strata = middle }` and
   `{ value = 250 strata = lower }` (the effect takes a constant).
5. **Sent** is the batches taken × 500, the figure the distribution, the bill
   and the panel read. It never passes the month's settlers, and averages
   them over a few months, within a batch a state.

Every state the country owns is a source, the Space Program's included (my
call). The Settlement Authority's 2% budget is not shared: at the share's
size (32,000 a month in a country of 100 million is 0.03%) it never binds,
and the 1% cap holds the extreme. The carry is a state variable, so a state
that changes hands takes its small debt with it; harmless.

**The census books settlers as known moves out, by a profile** (the scope's
§ 3.5: the programme reuses the Authority's census booking). Left unbooked,
they would fall to the census's residual, which gives at most 3% of an age
class and sex a year (`te_demog_k_migrant_cap_out`) and spreads the rest flat
over every age; large draws pass that cap. Each source state with a census
books its take as `te_demog_rs_note_move` books a source's: the source side
only (`te_dg_rs_out`, `te_dg_rs_o_*`), there being no destination on the map,
by Organized Colonization's profile (`RESETTLE_PROFILES`: families), so the
census's step takes them off the residual as a count. The booking takes a
profile code where it now reads `scope:rs_destination.var:rs_programme`.

**Self-check** `emigration_batch` reads the sum of the falls across the
states taken from against 90% of the sent, once a game, as it reads one state
today.

**Engine question** (play-test): whether `kill_population_in_state` with a
stratum spreads the take over the state's pops of that stratum in proportion
to their size. If it takes from one pop first, the per-pop share is uneven,
but the state's total holds.

### 6.4 How long and how much

Filling a world from empty, settlers at the rate shown and growth at 0.2% a
month (Valles Marineris on High priority alone):

| Settlers a month | Valles Marineris to 250,000 | Launch Capacity spent | At the base price |
|---|---|---|---|
| 2,000 | 9 years | 670,000 | £134 million |
| 8,000 | 2.5 years | 720,000 | £144 million |

Every world to 3.36 million at 32,000 a month takes about 8 years and 9
million Launch Capacity (£1.8 billion at the base price), against a module's
£24 to £30 million.

## 7. Autonomy and the Administration

### 7.1 Where colonies settle

At peace and ungarrisoned, pressure = −0.25 + 0.05 per 10,000 people + 0.01
per transit month (at most +0.5) − 0.15 per staffed Administration level
(− 0.4 chartered), and autonomy
settles at 100 × the pressure; at 100 the colony breaks away, at 50 it
demands terms (colony management design § 4.2). With settlers arriving there
is contact, so the no-contact term is 0. Transit at chemical drives (Mars 9
months, Jupiter 33, Saturn and out past the cap); faster drives move a column
left.

Where autonomy settles with no Administration (100 or more breaks away):

| People | Moon | Mars | Jupiter | Saturn and out |
|---|---|---|---|---|
| 10,000 | 0 | 0 | 13 | 30 |
| 50,000 | 0 | 9 | 33 | 50 |
| 100,000 | 25 | 34 | 58 | 75 |
| 160,000 | 55 | 64 | 88 | breaks away |
| 250,000 | breaks away | breaks away | breaks away | breaks away |
| 400,000 (terraformed) | breaks away | breaks away | breaks away | breaks away |

Administrations to settle below the demand (50), and below 25:

| People | Moon | Mars | Jupiter | Saturn and out | Chartered, Mars |
|---|---|---|---|---|---|
| 100,000 | 0, 1 | 0, 1 | 1, 3 | 2, 4 | 0, 0 |
| 160,000 | 1, 3 | 1, 3 | 3, 5 | 4, 6 | 0, 0 |
| 250,000 | 4, 6 | 4, 6 | 6, 8 | 7, 9 | 2, 4 |
| 400,000 | 9, 11 | 9, 11 | 11, 13 | 12, 14 | 7, 9 |

So Valles Marineris at its cap holds with four Administrations of its 25
crews (100 authority), or six to keep it quiet (150), or a charter and two.
That is the tension the owner wants (scope § 3.6): autonomy, not the Habitat
cap, is the practical limit on a large colony. With Artificial Intelligence
the Administrations are the same number of a doubled crew count.

### 7.2 Authority

- A new entry modifier, `sr_module_admin`, with
  `country_authority_cost_add = 25` (owner: "about 25 a level"; a positive
  cost, never a negative add), declared on the colonization entry at
  `sr_mod_units_admin` (the staffed levels, summed over the colonies that
  serve THIS) while above 0, beside the five facility modifiers
  (`sr_sites_generated.txt`, generated). The Administration stays a hook on
  autonomy; the modifier only bills it.
- An understaffed Administration costs and does its share.
- For scale: a company charter and a monopoly cost 100 each (vanilla
  defines).

## 8. Module effects at many crews

Each facility gives its effect per staffed level with no ceiling (the Nuclear
Command Center's +12 aside). Today's ceiling is 13 crewed levels at the
largest world and 444 in the whole table. Below, "one world" is every crew
of Valles Marineris at its cap in one type (25, 50 with AI), and "every
world" is every crew in the table at 100% Habitat room (332, 671 with AI):
the ceiling, which only a country holding all forty worlds could reach.

| Module | A staffed level | One world | With AI | Every world | With AI |
|---|---|---|---|---|---|
| Mining Complex | +50 base room there | +1,250 | +2,500 | +16,600 | +33,550 |
| Off-World Resort | +10 Resort Colony room there | +250 | +500 | +3,320 | +6,710 |
| Research Station | +2% research speed | +50% | +100% | +664% | +1,342% |
| Cultural Center | +3% cultural pull, +1% prestige | +75%, +25% | +150%, +50% | +996%, +332% | +2,013%, +671% |
| Black Site | +1 intelligence capacity, +3% covert efficiency | +25, +75% | +50, +150% | +332, +996% | +671, +2,013% |
| Training Ground | +4% army experience gain | +100% | +200% | +1,328% | +2,684% |
| Materials Foundry | +3% Advanced Materials output | +75% | +150% | +996% | +2,013% |
| Orbital Yard | +4 fabrication points a month, +0.5 Space Command strength | +100, +12.5 | +200, +25 | +1,328, +166 | +2,684, +336 |
| Nuclear Command Center | +4 reliability target, at most +12 | +12 | +12 | +12 | +12 |
| Administration | −0.15 autonomy there, 25 authority | | | | |

Reference figures: the table's own base room is 4,325 and its resort room 955;
fabrication is 5 to 25 points a month.

**What holds them**, without a limit on concentration (owner, call 4):
settlers' price and time (§ 6.4), autonomy (§ 7), fabrication (two modules a
month at most, each £24–30 million) and shipping. The play-test watches the
two room modules first: the ground-types checkbox moves levels to the site
that earns most, so cheap room at the best site would empty the others
(scope § 3.7). Research Stations come next. A limit, if one is needed, is a
later PR.

## 9. The AI

- **Modules** (`sr_mod_ai_plan_<key>`): "slot modules only within the world's
  slots" becomes:
  - a Habitat only within the cap, once people fill three quarters of the
    room (it never pays past the cap);
  - a specialization level or a facility only while crews ≥ crewed levels
    (one to spare), Artificial Intelligence no longer exempt;
  - an Administration also only while `authority >=
    sr_mod_ai_admin_authority` (50, twice its cost; my call).
  The order and the other tests stay. This also ends the loop #1950 left (an
  Off-World Resort a year in place of Research Stations): it stops at the
  crews.
- **Settlers** (`sr_emig_ai_review`, yearly, after the fabrication method is
  picked): Off in the same cases as now. Otherwise they share fabrication's
  budget (owner, on the builder check): the largest step whose bill at
  today's Launch Capacity price fits in `sr_mod_ai_fab_share` (5%) of weekly
  `fixed_income` less the chosen method's bill, never past the open room; at
  least step 1 for an AI that tends colonies with a positive weekly income,
  and step 1 for any other. Today settlers sit in the mission budget's bill
  as throughput (`sr_ai_program_throughput_unfunded`, `ai.md` § Space Program
  Mission Budget); that term goes with the throughput. Priorities stay
  Normal.
- **A colony's own builds** (`sr_site_self_build_<key>`): a Habitat within
  the cap at three quarters full, then its specialization levels and a
  Research Station or Cultural Center only within its crews, as the AI plan.
- **Storage**: the AI stays on No Module Storage (it never queues past the
  cap).
- **The automatic destination pick** (`sr_cf_score_<key>`, population and
  transit design § 7): + 1 a 10,000 people the world holds at its cap at our
  share (`SCORE_PER_CREW_ROOM`). Valles Marineris gains 25 and Himalia 2, on a
  score that loses 10 a stage and half a transit month, so a large world beats
  a near small one but not a near large one (Marius Hills, 116, before Valles
  Marineris, 110; my call).

## 10. The panel

The owner's requirement: a player must see when crews limit a colony and what
to do about it. Each piece below names where it goes; the cell widths are the
builder's, measured by `test_space_race_labels.py`.

**Modules view, a colony's box.** The header line's Staffing and Slots cells
become Crews and Habitats:

```
[x] Valles Marineris
  Crews 7/5  75%   Habitats 2/4   Bases 200 +10%
  Res  2 +1 [+]  Min  1    [+]  Hab  2    [+]  Port 0 [+]  Def  0 [+]
  Mine 3    [+]  Yard 0    [+]  Lab  2 +1 [+]  Arts 0 [+]  Tour 0 [+]
  Spy  0    [+]  Camp 0    [+]  Nuke 0    [+]  Mat  0 [+]  Gov  1 [+]
```

- *Crews needed / available*: crewed levels less the founding one, and the
  people's crews; red when needed is more; the share beside it. Its hover:

```
Crews at Valles Marineris
Its 8 crewed module levels need 7 crews: the founding specialization
runs without one. Its 52,000 people make 5, one for every 10,000
(5,000 with Artificial Intelligence).
Every crewed module runs at 75%: 6 crews for 8 levels.
2 crewed modules are queued or on their way: 20,000 more people.
More crews: send more settlers, set this colony's priority to High,
or build a Habitat for room.
```

- *Habitats built / cap*: red past the cap. Its hover: the cap comes from the
  world's size; a Habitat holds 30,000 people here (60% of the base room,
  with one of the five technologies); the next costs 100 points, and past the
  cap the n-th costs (1 + n) × 100, queued only while the module stock holds
  its price (stock 1,650 now).
- The level field takes two digits.

**The + button** gains a line for a crewed type, the scope's two cases:

```
Needs a crew: 2 to spare after this one
No crew to spare: every crewed module here would run at 67% (75% now)
```

and for a Habitat, its price and "past the cap: the 2nd past costs 300".
`sr_mod_req_slot_room_tt` and `sr_mod_queue_past_slots_tt` go.

**A colony's page.** The Slots tile becomes Habitats (built / cap) and the
Crews tile reads needed / available with the share; the module rows are
unchanged.

**People view.**

```
Settlers a month   4,000  [-][+]      sent last month 4,000
                   2,769 Launch Capacity a week
People off Earth   612,000            Off-World Population +6
Valles Marineris   52,000 / 110,000   Crews 5, 7 needed   High
Olympus Mons       31,000 / 64,000    Crews 3             Normal
```

- The programme line: the amount, − and +, sent last month and the week's
  bill; its hover where they come from (every state the same share of its
  people, at most 1% of the country's a month, half middle strata and half
  lower) and the price.
- Each colony: crews, and "N needed" in red when short; the hover adds the
  people the queued crewed modules will need.

**Overview.** A cell "Understaffed N" (red above 0), its hover the colonies
and their shares. Where it fits among the overview's cells is the builder's.

**Choosing a destination** (owner): the Habitat cap goes where a fleet's
destination is picked.

- *Solar System*, each world's row, beside its Target button:
  `Habitats 4 · 250,000 · 25 crews`, at our share and our crew size. The
  second line's slots figure (`site_slots`, `sr_disp_ss_slots_<key>`) goes.
  `test_a_site_s_second_line_fits_the_row` and its first-line twin hold the
  widths.
- *Colony Fleets*, the destination line: the same three figures after the
  world's name.

**How it Works and the concepts**: the colony modules topic, the crews concept
and the Habitat's text rewritten around people: crews are the limit, the cap
is the Habitat's alone, the technologies make Habitats roomier, AI halves the
crew.

## 11. What else reads people

| Reader | Today | At the new sizes | Change |
|---|---|---|---|
| Off-World Population (+1% prestige, +2% pull a 100,000) | at most 10 units (1 million) | reachable by a big programme | none: the cap stays (my call) |
| Militia (a battalion a 20,000) | 2 at a full Mars plain | 12 at Valles Marineris | none: a larger colony is harder to seize |
| War support's weight (full at 75,000) | most colonies below it | big colonies at it | none |
| A colony's own builds (autonomy × people, at most 5 a month) | rarely at the cap | at the cap from 50,000 people at autonomy 100 | none; within crews and the cap (§ 9) |
| Cede Colony's AI value (1 a 1,000 people, at most 170 in all) | under the cap | big colonies at it | none |
| Free colony trade (a 20,000 over suppliers, at most 5) | | at the cap sooner | none |
| Dome breach (a tenth of the people) | 5,000 at a Mars plain | 25,000 | none: the flavor scales |
| Evacuation (`create_pop` in 1,000s) | up to 50 batches | up to 400 | none: one event |
| The census | settlers from one state | from several, each counted there (§ 6.3) | none |

## 12. What goes

`country_sr_colony_slots_add` (its type and its five grants),
`sr_site_slots_<key>`, `sr_site_slots_max_<key>`, `SLOTS_PAST_MAX`,
`sr_mod_slots_used_<key>` (a Habitat count replaces it), `sr_mod_scope_slot_room`,
`sr_mod_scope_past_slots` (a Habitat-only form replaces it),
`sr_disp_ss_slots_<key>`, the Slots cell and its hover, `sr_emigration_programme`
and its declaration, the AI crew waiver, `sr_disp_agi`. The guide's Slots text.
Old saves are not repaired; a running game keeps its modules, and its
settler level (§ 6.1).

## 13. Engine questions, self-checks and the play-test

| Question | How it is checked | Fallback |
|---|---|---|
| A runtime `goods_input_launch_capacity_mult` on the Space Program scales its whole Launch Capacity input, every method's line | The axis already works on a building at runtime (`sr_space_command_paused`, −1, on the Space Command); play-test: the Space Program's input before and after raising settlers | none needed if it holds; else a settlers' building of its own (back to the owner) |
| The building's throughput multiplies that input as it does the lines | Play-test, the same reading with modules built | drop the throughput term |
| `kill_population_in_state` by stratum spreads over the state's pops | Play-test: a large state's pops before and after | none: the state's total holds either way |
| Several states' falls add up to what was sent | Self-check `emigration_batch`, the falls summed across the states taken from | as today's |

`docs/testing/solar-colonies-playtest.md` gains a section: crews at a large
colony (the Crews cell, the + line, a module past the crews), the Habitat cap
and its price, the settler bill at two amounts, settlers from several states,
an Administration's authority, and the two room modules at one world.

## 14. Tests

- `test_solar_sites.py`: no slot test left in any queue trigger or install;
  the Habitat's price and stock rule; the crew per level and its AI half; the
  Habitat share, its record and its five grants; the AI plan's crew and
  authority tests; the destination score's new term.
- A settler bill test: `sr_emig_lc_base` sums every Space Program method's
  Launch Capacity line as its file states it, and the units for a known case.
- The draw, in a Python twin of the two passes: the share and its 1% cap,
  each state's due and carry, the take never past the month's settlers, and
  over a run of months every state giving its share within a batch.
- The census booking: a settler take books the source side only, by
  Organized Colonization's profile (`test_demographics_resettle.py` or its
  kin).
- The AI's settlers within fabrication's 5% (`test_ai_space_mission_budget.py`
  loses the settler throughput term).
- `test_authority_cost_modifiers.py` covers `sr_module_admin` already.
- `test_nation_tab.py`: `sr_settler_launches` is a building modifier
  (`NOT_ON_COUNTRY`); `sr_module_admin` is declared on the entry.
- The label width tests for the new cells and the Solar System figures.

## 15. Player guide

`16-space.md`: Colony settlers (the amount, the bill, where they come from),
Colony modules (crews, the Habitat cap and price, no slots), Autonomy (the
Administration's authority, a line on large colonies), and any figure that
names slots. `02-timeline.md`: the five technologies. `17-reference.md` and
the appendices if they list slots. The PDF rebuilt.

## 16. Build stages

One PR, in three stages, each committed and tested on its own:

1. **The rule**: slots out, the Habitat cap and price, the Habitat share and
   its record, the five technologies, crews at 10,000 and the AI half, the
   Administration's authority, the AI plan and a colony's own builds, the
   destination score.
2. **Settlers**: the amount, the bill and its refresh, the draw and its
   census booking, the AI's settlers, the self-check.
3. **The panel and the guide**: § 10, the concepts and How it Works, the
   play-test list, `16-space.md` and `02-timeline.md`, the PDF.

## 17. Left to the builder

Names of new values and loc keys; cell widths and where the Understaffed cell
sits; the hover wording (to `loc_style_guide.md`); how the country's people
are summed for the share (a pass over its states or a country trigger); the
order of the three stages' commits.

**Calls made in this design, for the owner to check**: dividing the
throughput out of the bill
(§ 6.2); + valid while the amount is below the open room (§ 6.1); the world
keeping its best Habitat share (§ 4.4); every owned state a source (§ 6.3);
the AI's authority margin of 50 (§ 9); the destination score's weight (§ 9);
the Off-World Population cap kept (§ 11); the Settlement Authority's budget
not shared (§ 6.3); settlers booked in the census by Organized Colonization's
profile (§ 6.3).
