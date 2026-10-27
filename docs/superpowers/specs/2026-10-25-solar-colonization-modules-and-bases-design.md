# Solar System Colonization, slice 4: colony modules and Extraplanetary Bases from colonies — design

Drafted 2026-10-25. Slice 4 of the scope in
`docs/superpowers/archive/specs/2026-10-25-solar-colonization-contest-scope.md` (§ 10), whose § Decisions and
§ 11 record the owner's calls (D18, M1 among them); this design assumes them and
the records of slices 0 to 3 (`2026-10-25-solar-colonization-holders-and-cession-design.md`,
`2026-10-25-solar-colonization-population-and-transit-design.md`). It gives
every colony modules, with the two specializations as modules, and makes
Extraplanetary Base room come from colonies (scope §§ 8.1, 8.2). There is no
separate plan: § 14 is the build order.

## Decisions (owner, 2026-10-25, for this slice)

- **Modules are built by a production method group on the Space Program.**
  Its methods take goods and give a script-only country modifier, module
  fabrication points a month, and queued modules are built at that rate. (The
  owner's suggestion, preferred over a per-order bill.)
- **All three generic modules ship now**: Habitat works; Defences and the
  Spaceport are placeholders, buildable, with their work to come with the
  fleets (slice 6).
- **Near-Earth room**: every country has room for 10 Extraplanetary Base levels
  at an ordinary grade, and colonies add their own. The AI must understand not
  to build past the room.
- **The penalty falls only on the levels past the room**: one country modifier
  set to the average over all levels, so a level 20 base with room for 10, at
  −50% past the room, works at −25%.

## Intent

After this slice, under Simple Colonies and Full Colonies:

1. **A colony is built up with modules.** Its two specializations are modules
   with levels: a world shares four specialization levels between them (D18),
   so one at 4, both at 2, or 1 and 3; the founding choice is level 1. A
   specialization's modifier is the one that exists, times its level.
2. **Three generic modules** share a world's slots from the site table (Mars
   four, Mimas one): **Habitat** (+50% of the world's room for people a level),
   **Defences** and **Spaceport** (placeholders).
3. **Modules need crews.** Every level past the first, Habitats aside, needs a
   crew of 5,000 people. An understaffed colony runs its modules at the share
   its crews can man. Artificial General Intelligence needs no crews.
4. **Modules are fabricated at Earth and shipped.** The Space Program's Module
   Fabrication method gives points a month; the national queue takes them one
   module at a time, first in first out; a finished module waits for its body's
   launch window (or leaves any month with a torch) and is installed when it
   lands.
5. **Extraplanetary Bases draw on colonies' room.** Each world's room holds
   tens of base levels at its own grade (16 Psyche +30%, the outer moons worse);
   levels fill the best room first; past all of it, a level works at −50%.

Races only is unchanged: one specialization at level 1, no modules, bases
unlimited.

## Non-goals

What Defences and the Spaceport will do (slice 6: the fleets' combat,
resupply, repair and propellant); blockades stopping deliveries or dropping a
site's base room (slice 6); dismantling a module; free colonies, autonomy and
colony events (slice 5).

## Engine facts

**Rests on:**

- A production method's `country_modifiers = { workforce_scaled = { … } }`
  reaches its country and is read as `modifier:<type>` (the debris removal
  methods, `te_orbital_debris_pms.txt`, `te_debris_removal_selfcheck`).
- `activate_production_method = { building_type = building_space_program production_method = … }`
  in country scope (`te_debris_activate_best_removal`).
- A building's `can_build_government` and `can_build_private` are state-scope
  triggers that read `owner` (vanilla `building_opium_plantation`), and the
  AI's builder obeys them as it obeys `possible` (Global Commons design,
  engine facts: the slot-building pattern).
- A country's levels of a building type, built and queued, in a script value:
  `every_scope_state = { every_scope_building = { … add = level } }` with
  `level_after_queued_constructions` for the queued ones
  (`solar_receiver_slots_remaining`, read by the Solar Power Receiver's
  `possible`).
- A throughput modifier is linear: total throughput is one plus the sum of the
  adds, so the average of per-level grades over all levels gives each level's
  output exactly (the owner's −25% example).
- A static modifier on the journal entry at `multiplier = <script value>`, the
  script value reading only global variables, so it evaluates alike in the
  entry's scope and the country's.

**Unverified, each with a self-check (§ 12):**

- That a secondary method group's workforce-scaled modifier on the Space
  Program reaches its country (the debris removal self-check reads the same,
  for another type).
- That `has_modifier` sees a modifier an `add_modifier` placed earlier in the
  same effect. Today's code assumes it in places and avoids relying on it in
  others (slices 2-3 design § 15); the first sync that re-adds a specialization logs it.

## 1. The site table

`gen_solar_sites.SITES` gains three fields per world:

| Field | What | Range |
|---|---|---|
| `slots` | generic module slots (Habitat, Defences, Spaceport share them) | 1 (Himalia, Amalthea, Mimas, Miranda, Proteus and the four smallest dwarf planets) to 4 (Valles Marineris, Hellas and Utopia Planitia) |
| `ebase_room` | Extraplanetary Base levels the world's room holds | 10 to 60 (16 Psyche); 760 in all |
| `ebase_grade` | the throughput a level in its room gets, in percent | +30 (16 Psyche) to −45 (Sedna) |

The grades follow scope § 8.2: the metal asteroids rich and close (Psyche
+30, Vesta +20, Ceres +15), the Martian sites good (+10), Jupiter's big moons
ordinary (0), Venus and Saturn's moons poor (−10 to −20), Uranus, Neptune and
the Kuiper Belt worse (−25 to −45). First guesses, to tune in play (M1).

## 2. The module record

Global variables per world, beside the record of slices 0 to 3:

| Variable | Holds | Absent |
|---|---|---|
| `sr_site_lvl_a_<key>`, `sr_site_lvl_b_<key>` | the specialization's level (the event's first and second option) | the founding choice reads 1, the other 0 |
| `sr_site_hab_<key>`, `sr_site_def_<key>`, `sr_site_port_<key>` | the generic modules' levels | 0 |

So a save from before this slice reads its founding choice at level 1 with no
migration. The record is the world's: a cession or an heir takes it, a
release clears it.

**Caps** (generated): the two specializations together at most four
(`SPEC_BUDGET`), the three generic modules together at most the world's
`slots`. A queued or shipping module counts against its cap, so a landing
never overflows one (a cession aside: § 7).

## 3. What a module does

- **A specialization** shows its modifier at `multiplier = sr_site_mult_<a|b>_<key>`,
  its level times the colony's staffing (§ 4). The sync (`sr_site_mirror_on_<key>`)
  shows each specialization whose level is at least 1, through
  `sr_site_show_modifier_at = { MODIFIER MULT }`: the `_held` record as today,
  and on the entry, when the multiplier applied (the country's
  `<modifier>_mult`) differs from the one wanted, the old copy removed and the
  new one added. The test is the variable, not `has_modifier` (§ 12), so a
  second sync in the same effect never re-adds. Under races only the
  multiplier is 1.
- **A Habitat** adds 50% of the world's base room a level (`sr_site_room_<key>`
  becomes a value), so more people, so more crews.
- **Defences and Spaceport** take a slot, need a crew and cost upkeep, and do
  nothing yet. Their tooltips say what they will do with the fleets.

## 4. Crews and staffing

`sr_site_crews_<key>` (slice 2) counts the crews a colony's people make, one a
5,000. Its modules need `levels − 1` of them, where `levels` counts both
specializations, Defences and Spaceport (Habitats need none: they house the
crews). The colony's **staffing** is 1 when it has the crews, under
Artificial General Intelligence (the holder's technology), or under races
only; otherwise `(crews + 1) / levels`: a colony with four levels and no
crews runs each at a quarter, the founding outpost's worth. Staffing scales
the specializations' multipliers; it never touches a Habitat's room, so an
understaffed colony can't shrink its own room and lose its people.

## 5. Fabrication

**The method group** `pmg_space_program_module_fabrication`, a third group on
`building_space_program` beside the missions and debris removal,
`ai_selection = most_productive` as the debris group has. No method employs
anyone: they ride on the mission's workforce, as debris removal does.

| Method | Technology | Launch Capacity/wk | Advanced Materials/wk | Points a month |
|---|---|---|---|---|
| None (default) | — | — | — | 0 |
| Orbital Assembly | Directed Energy Weapons | 1,500 | 10 | 5 |
| Lunar Foundries | Space Colonization | 2,000 | 15 | 12 |
| Fusion Shipyards | Muon-Catalyzed Fusion Reactors | 2,000 | 10 | 25 |

The points are `country_sr_module_fabrication_add` (a new script-only type,
workforce-scaled, so a half-staffed programme fabricates at half the rate).
Every module costs 100 points.

**The month** (the entry's pulse, simple and full, for a country with the
entry): the month's points go into `sr_fab_stock`, kept up to 200 so a stall
(no free shipment, nothing queued) loses nothing short of that. Then, up to
twice a month, while the stock holds 100 and a shipment slot is free, the
queue's first entry is built: it leaves the queue and fills a shipment slot.
An entry for a world the country no longer holds is dropped unbuilt.

**The queue** is the holder's, one for the nation, first in first out
(owner, 2026-10-25): twenty places, `sr_mq_<n>_site` (a world's index) and
`sr_mq_<n>_type` (the module's code), filled from place 1 without gaps. A row's
+ adds an entry at the end; removing one (its button in the queue's list, a
colony's clear button, or the world leaving the country) moves every later
entry up. A count per world and module type, `sr_mq_<type>_<key>` (types `a`,
`b`, `hab`, `def`, `port`), follows the queue for the caps and the panel:
added to on each new entry and recounted after every removal and monthly. A
colony that leaves its holder takes nothing of it (the next holder starts with
none), as the emigration priority doesn't follow either.

## 6. Shipments

Eight slots per country (`sr_ms_<n>_site`, `_type`, `_arrive`;
`sr_ms_count`), filled by fabrication and emptied by landing. From the global
monthly step, for every country with a shipment, before the worlds' step:

- **A shipment waiting at Earth** (no `_arrive`) leaves when its body can be
  reached at no premium (`sr_mod_departs_<key>`: the window open, or a torch or
  antimatter drive; Mercury always) and gets `_arrive` = now plus the
  country's `sr_transit_months_<body>`. Off-window launches at a premium are
  the colonization bar's, which modules don't spend.
- **A shipment whose month has come lands**: the module is installed if the
  world is still claimed and its cap has room, whoever holds it now; otherwise
  it is lost. Then the world syncs.

## 7. Cession, heirs, release, revolutions

- A world's modules go with it. The old holder's queue for it is cleared by the
  unmirror; its shipments already made land and are installed for the new
  holder (they are at the world), unless the new holder filled the cap first.
- A release clears the levels with the rest of the record.
- A revolution's winner inherits the queue, stock and slots (variables) and
  the `_mult` records; the entry's immediate puts the specializations back at
  their multipliers (§ 3, `sr_sync_colony_modifier_base` gains `MULT`).
- **Cede Colony's AI value** gains 5 a module level past the first.

## 8. Upkeep

`sr_module_upkeep` on the entry, at multiplier = the module levels past
the first at the colonies the country holds: +1% Space Program throughput a
level, its Launch Capacity bill (owner: upkeep is an input multiplier on the
building doing the work). Refreshed with the entry's other two modifiers
(`sr_emig_refresh_modifiers`, once per effect).

## 9. Extraplanetary Bases from colonies

Under simple and full, monthly from the country pulse, for every country with
Asteroid Mining (`sr_ebase_refresh`, the one refresh site):

1. Its built levels, `sr_ebase_levels`.
2. **Filling, best room first**: the room tiers in descending grade (ties in
   table order), the near-Earth room (10 levels at 0) among the grade-0 tiers,
   each colony's tier counting only while the country holds it. Each tier takes
   `min(levels left, its room)` at its grade; whatever is left takes −50%.
3. The average, `sum ÷ levels`, as one of two unit country modifiers:
   `sr_ebase_room_bonus` (+1% Extraplanetary Base throughput) or
   `sr_ebase_room_penalty` (−1%), at multiplier = the average's size in
   percent. Both removed first.
4. `sr_ebase_room` (levels of room in all) stored for the build gate.

**The AI** (owner: it must understand not to build past the room):
`building_space_mine` gains `can_build_private` (no private investor builds
past the room, in anyone's country) and `can_build_government` (an AI
government doesn't; a player's can, at the penalty), both reading built and
queued levels against `sr_ebase_room`, and both always true under races only.
A level past the room adds half a level's output for a full level's 20,000
construction, so the AI loses nothing worth having.

**Balance against the Deep-Sea Mine** (scope § 8.2): at the best grade (+30%)
the era-11 base earns 9,425 a level against the mine's 26,300, and costs four
times the construction. `test_deep_sea_rebalance.py` holds the era-11 ordering
with the best grade added.

## 10. AI for modules

Each January, from the entry's pulse, for an AI holding a colony under
simple and full (`sr_mod_ai_review`):

- **The method**: the best fabrication method it has while it is among the
  space race's top three (`sr_ai_should_participate`), out of default, with a
  positive weekly income and something to queue; None otherwise.
- **The queue**: each colony it holds with nothing queued or shipping gets one
  module: a Habitat when its people fill three quarters of its room and a slot
  is free; else the next level of its founding specialization (then the
  other), when the budget has room and its crews (or AGI) can run it. Never
  Defences or a Spaceport while they are placeholders.

## 11. The panel: Colony Modules

A new section after Settlers, simple and full only (open by default; the flag
`sr_panel_modules_closed`):

- **Fabrication**: the points a month and the method; the stock; the queue's
  length; shipments waiting and in flight; the upkeep.
- **Extraplanetary Bases**: built levels against room, and the throughput the
  room gives.
- **One row per held colony** (generated): its icon and name, its staffing,
  then a button per module type showing the level and what is queued
  ("2+1"); a click queues one more (`sr_colony_module_sgui`, `scope:site` and
  `scope:op` the type), and the row's last button clears the colony's queue.
  Tooltips name the module and what a level does.

## 12. Self-checks and the play-test list

Added to `docs/testing/solar-colonies-playtest.md`:

- **`module_fabrication`**: the first month a staffed Space Program runs a
  fabrication method: OK when `modifier:country_sr_module_fabrication_add` is
  above 0, BROKEN otherwise (the method's modifier never reaches the country).
- **`modifier_seen_same_effect`**: the first time a world's sync re-adds a
  specialization (the first month after loading a save with colonies, or the
  first module landing), right after the add: OK when the entry's
  `has_modifier` sees it, BROKEN otherwise. Settles the question for the whole
  mod.

The play-test list adds what script can't see: the Colony Modules section,
the method group in the Space Program's panel, a module's effect on the
specialization's line in the entry's modifiers, and the AI's Extraplanetary
Base construction stopping at the room.

**Console** (`te_debug_space_race.4`): log every colony's modules; fill our
stock; queue one of each at our first colony; land our shipments now.

## 13. My calls, for the owner to check

1. **Every module costs 100 points**, the methods give 5, 12 and 25 a month:
   a module every 20, 8 or 4 months at full staff. First guesses.
2. **First in first out** (settled by the owner on the PR, 2026-10-25, in place
   of a round-robin over colonies): the queue builds in the order modules were
   added, and a player moves one up by removing what is ahead of it.
3. **Habitats need no crew** and staffing never shrinks room.
4. **Understaffing scales the modules' effect** rather than idling a module.
5. **No dismantling**: the founding specialization stays at least level 1, so
   "one at level 4" is the founding one.
6. **Modules leave only at no premium**: in the window, or any month with a
   torch or antimatter drive.
7. **A landing installs for whoever holds the world**, and is lost on a world
   released or full.
8. **Upkeep +1% Space Program throughput a level past the first.**
9. **The AI can't build Extraplanetary Base levels past the room**, a player can.
10. **Defences and Spaceport are buildable now**, with no effect until the
    fleets; the AI doesn't build them.

## 14. Build order

1. The site table's fields; the record, levels, staffing and multipliers; the
   mirror at multipliers; release; the entry backstop with `MULT`.
2. The method group, methods, modifier type; the queue, fabrication,
   shipments and landing; upkeep; the AI.
3. Extraplanetary Base room: the refresh, the two modifiers, the build gates.
4. The panel, scripted GUI, loc, console.
5. Tests, docs, the player guide, the play-test list.

## 15. As built (2026-10-25)

Where the build departs from the sections above, and why:

- **The upkeep modifier is `sr_module_upkeep`**, not `sr_colony_modules_upkeep`
  (§ 8): every `sr_colony_*` static modifier is a specialization, and the
  tests and the Nation tab registry read the family as one.
- **Fabrication follows the Space Program's throughput** (§ 5): a method's
  workforce-scaled country modifier scales with it, as debris removal does, so
  funding (and the modules' own upkeep) raises the points with the bill.
- **The backstop is a helper of its own**, `sr_sync_colony_spec_base = { MODIFIER MULT }`
  (§ 7): the discovery outcomes keep `sr_sync_colony_modifier_base`, which has
  no multiplier, and the 68 specialization calls moved from
  `space_race_effects.txt` to the generated `sr_sites_sync_entry_specs`.
- **The founding dispatcher records the multiplier** (§ 3): the event's grant
  adds the specialization unscaled, so `sr_site_choose_<modifier>` sets
  `<modifier>_mult` to 1 before the world's sync, which then adds nothing.
- **The AI's method needs its technology** (§ 10): a holder given a colony may
  lack Directed Energy Weapons, so with none of the three technologies it
  switches nothing on.
- **The panel's column heads are short** ("I", "II", "Hab", "Port", "Def",
  "Crew"): a cell is 52 wide (`test_space_race_labels.py`), and the heads'
  tooltips name the modules.
- **The console is a new event**, `te_debug_space_race.4`.
- **The queue is first in first out** (owner, 2026-10-25, on the PR), not the
  round-robin over colonies of § 5's first draft: twenty places in order, a
  list in the panel with a remove button per entry (`sr_colony_module_queue_sgui`),
  the per-world counts kept for the caps. No reordering control: a move-up
  button would need markup no mod panel has used yet.
