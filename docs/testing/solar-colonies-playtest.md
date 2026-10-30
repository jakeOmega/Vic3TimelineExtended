# Solar colonies play-test checklist

What the next play-test of the colony record (slices 0 and 1 of the solar colonization scope:
`docs/superpowers/specs/2026-10-25-solar-colonization-holders-and-cession-design.md`) should look at. In-game checks
don't gate the merge (CLAUDE.md, "In-game checks"): where the build rests on an engine fact nobody has verified, it
ships the preferred version with a `TE_SELF_CHECK OK|BROKEN <name>` line in `debug.log` and names its fallback below.
Grep `debug.log` for `TE_SELF_CHECK` first, then for `TE_SR_SITES` (the record's own lines).

The console is `event te_debug_space_race.2` (log every world's record, claim the first free world, give our first
colony away as Cede Colony would, release our first colony, run the monthly step). `event te_debug_space_race.1`
still reaches the milestones.

## Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK site_dead_holder <world>: …` | once a game, the first month a world's holder is no longer alive | which guard caught the dead holder: `exists` on the stored country, or `is_country_alive = no` on a stored country that still exists. Either is fine; record which | `TE_SELF_CHECK BROKEN site_dead_holder <world>: the heir did not take it`: the transfer to the capital region's owner left the dead holder on the record | if neither guard catches it (the world stays on a dead holder, no line), store the holder's tag as well and compare tags (`c:<TAG>` and `exists`) |
| `TE_SELF_CHECK OK/BROKEN site_receiver_entry: …` | once a game, 70 days after a country without the Moon Base and Mars Landing received a colony | it holds Solar System Colonization and the colony | it has no entry (`add_journal_entry` or the widened `possible` failed) or lost the colony | put a received colony's modifiers on the country instead of the entry for a country that cannot hold the entry (`sr_site_show_modifier` would need a country branch) |

## The record

1. **Founding.** Found a colony (`event te_debug_space_race.1` to the colonization entry, or the console's claim). The
   founding event fires as before; after choosing, `event te_debug_space_race.2` option a logs the world as held by us.
   Our Colonies and the colony count read as they did.
2. **Solar System.** Open Solar System Colonization: the Solar System section, closed by default, lists every world
   under eight locations. A world we hold reads "Ours", a rival's shows its flag (its name on hover), an unclaimed one
   "Unclaimed". Check the flags draw and that no row ends in "...".
3. **A dead holder.** Find an AI holding a colony (`te_debug_space_race.2` option a), then `annex <TAG>` it from the
   console. Within a month its worlds show the new holder, the annexer of its capital, and a player heir gets "Heirs
   to a Fallen Programme". The heir's entry opens if it had none, and the colony's specialization modifier is on it.
4. **No heir.** Release a colony (option r): the world reads "Unclaimed" and is drawn again by the next fleet whose
   window is open, even from a later stage.
5. **Revolutions.** A holder whose revolutionaries win: its worlds are the winner's on the day of the win (not a month
   later), and the winner's Our Colonies lists them.
6. **Old saves.** Load a save from before this change in which a colony holder had been annexed. After 45 days its
   worlds read "Unclaimed" (`TE_SR_SITES released <world>` in `debug.log`). Every other world keeps its holder.
7. **A holder without the milestones.** Give a colony (option c) to a great power that has not landed on Mars: its
   Solar System Colonization opens, reads Idle, bills nothing and shows the colony in Our Colonies.

## Cede Colony and the rule (slice 1)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN cede_colony_input: …` | once a game, the first Cede Colony that enters into force | the article's input building type named a world the source held, and the world moved | no world matched: `input_building_type` did not read back, or `scope:input = bt:<type>` / `?= bt:<type>` does not compare building types | one article per body group with a `quantity` and the receiver picking the worlds in an event, as the seabed lease (scope § 6.1's fallback) |

1. **The rule.** The setup screen's Space Race rule offers Full Colonies (the default since slice 6d), Simple
   Colonies, Races Only and Disabled. Under each of the first three every space race entry appears as before; under
   Disabled none does.
2. **The designer.** Under Simple Colonies, open a treaty with a country that holds a colony: Cede Colony lists that
   country's colonies by name and icon ("Valles Marineris Colony"), and only those. The list, the picked colony under
   it, the draft row and the signed treaty's row are the mod's own widgets (vanilla shows a building type only for a
   company monopoly): check each shows the colony's name and icon. Under Races Only the article does not appear.
   The first build crashed the game here (2026-10-30): its list read `ArticleDraft.GetValidBuildingTypes`, which
   needs a company. The list is now `te_sr_cede_site_list_treaty`, generated, keyed on the article's source
   (`ArticleDraft.GetFirstOrSource`); the owner opened it without a crash and it looked right the same day. Still to
   see: no `This data is likely not a container` in that launch's `debug.log`; picking a colony turns the Add button
   green; a colony the treaty already carries is still listed, and Add should refuse it a second time (`usage_limit`);
   and what the article button's options count (`TreatyDraft.GetNumAvailableInputOptions`) shows for Cede Colony. A
   list that reads "None" for a holder, or names the other side's colonies, means the source is the wrong country,
   which logs nothing; only an accessor that fails to resolve logs, as `FetchData failed` naming `sr_cede_held_`.
3. **The building types appear nowhere else**: not in the build menu, the production overview, the encyclopedia, a
   company's or an industry charter's list. If one does, note where.
4. **A sale.** Cede one of our colonies for a Money Transfer to an AI great power: it accepts when the money is large
   enough, the colony moves on ratification, both sides get "A Colony Changes Hands", and the receiver's Our Colonies
   and Solar System list show it.
5. **A swap**: one colony each way in one treaty moves both.
6. **A war goal.** In a diplomatic play against a colony holder, add Cede Colony as a war goal (maneuvers 5, infamy
   10). Enforced in the peace, the colony moves. This crashed the game in the first build too: check that the picker
   (`te_sr_cede_site_list_war`) opens with no `This data is likely not a container` in `debug.log`, that it lists the
   colonies of the country the goal is pressed against (`WarGoalDraft.GetTarget`) and only those, and that picking one
   turns the war goal's Add button green (its own gate, `ArticleDraft.CanAddWarGoal`).
7. **The AI.** In an observer run past the first colonies, an AI holding a colony with no space programme (an heir's)
   offers it; AI powers in the race ask for colonies; neither spams the treaty screen.

## Targets, colony fleets and settlers (slices 2 and 3)

Design: `docs/superpowers/specs/2026-10-25-solar-colonization-population-and-transit-design.md`. The console is
`event te_debug_space_race.3` (log our fleets, the fleets bound for each world and every colony's people; send a fleet
now; land every fleet now; emigration on High and this month's settlers now; fill our colonies to half their room).
Grep `debug.log` for `TE_SR_FLEETS` and `TE_SR_SETTLERS` after option a.

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK colony_fleet_arrival world=<index> flown=<months> …` | once a game, the first fleet that lands in its arrival month | the global step landed it in its month; `flown` should be the transit `docs/engine/launch_windows_report.md` gives its body and drive for its departure month | `TE_SELF_CHECK BROKEN colony_fleet_arrival … late=<months>`: a fleet landed two or more months after its month, so the step missed it | land fleets from the entry's monthly pulse as well, for the country's own slots |
| `TE_SELF_CHECK OK/BROKEN emigration_batch before=… after=… sent=…` | once a game, the first month a country sends settlers | the Space Program's state lost at least 90% of what was sent | it lost less: the strata filter removed fewer people than asked, or `state_population` reads the change only later | if the state's population falls by the batch a month later instead, read the change at the next month's step; if the filter falls short, take the batch without `strata` |

1. **Targets, under every setting.** With a programme running, open the Solar System list: unclaimed worlds the
   programme can reach show Target. Under Races Only only the current stage's worlds (and any released one) do. Pick
   one: its row reads "Our target", Colony Fleets names it, and the next fleet goes there when its window opens, even
   if another world's window is open first. Clear goes back to the draw.
2. **A fleet travels (Simple or Full Colonies).** Found a programme and let a fleet leave for Mars: the world stays
   Unclaimed, Colony Fleets lists the fleet with its world and landing (about 9 months by chemical rocket), and the
   Mars row shows "1·9". On its landing month the founding event fires and the world reads "Ours".
3. **Drives.** With Fusion Power the same trip in a window takes about 3 months; with Muon-Catalyzed Fusion Reactors
   about 1, any month. The Drive line in Colony Fleets names the drive.
4. **A race to a world.** Send a fleet to a world an AI's fleet is already bound for (its row shows the count): if
   theirs lands first, ours founds another free world of the same planet ("Another Flag Already Flies"), or, at an
   asteroid, is lost ("A Fleet With Nowhere to Land").
5. **The automatic pick.** Leave the target unset: the programme sends fleets to near, cheap worlds first and does not
   send a chemical fleet to Uranus (16 years). The AI's fleets do the same.
6. **The stages.** Under Simple or Full, a fleet can leave for Saturn while Mars is still free (with Deep Space
   Exploration or a colony held); the stage line shows the innermost stage with a free world.
7. **Settlers.** Under Simple or Full, the Settlers section lists our colonies with people / room. Set Emigration to
   Low: next month the colonies gain 500 people between them, the Space Program's Launch Capacity bill rises by about
   5%, and the census of its state shows the emigrants. Set Mars High and Venus Closed: Mars takes most of them, Venus
   none.
8. **The bonus.** Option g (half the room): People off Earth reads the sum, and Off-World Population is on Solar System
   Colonization at the multiplier its tooltip shows.
9. **Crews and AGI.** Crews read one per 5,000 people; with Artificial General Intelligence they read AGI.
10. **The AI's settlers.** In an observer run under Simple Colonies, a top-three space power holding colonies sets
    Emigration to Steady within a year; its colonies' people grow.

## From the 2026-10-25 log triage

- **Load.** `error.log` at launch carries no `Database type building_sr_site_<world> has missing texture`: each site
  building has the Monuments' panel `background` since 2026-10-25 (34 lines a launch before).

## Colony modules and Extraplanetary Base room (slice 4)

Design: `docs/superpowers/specs/2026-10-25-solar-colonization-modules-and-bases-design.md`. The console is
`event te_debug_space_race.4` (log every colony's modules and caps; fill our fabrication stock; queue one of each
module at our first colony and fabricate now; land our shipments now; recompute our Extraplanetary Base room). Grep
`debug.log` for `TE_SR_MODULES` after option a.

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN module_fabrication country=… points=…` | once a game, a month after a Space Program first runs a fabrication method at half staff or more | the method's `country_sr_module_fabrication_add` reaches its country | the country has no points: the secondary group's workforce-scaled country modifier does not reach it | give the points from script instead: `sr_mod_fab_rate` reads which method the Space Program runs (`sr_mod_fabrication_runs`) and its occupancy |
| `TE_SELF_CHECK OK/BROKEN modifier_seen_same_effect <modifier>` | once a game, the first time a world's sync re-adds a specialization at its multiplier (the first month after loading a save with colonies, or the first module landing) | `has_modifier` sees a modifier an `add_modifier` placed earlier in the same effect | it doesn't yet: every refresh must stay once per effect (the mod's code already assumes so) | none needed for this slice: `sr_site_show_modifier_at` tests its `_mult` record, not `has_modifier`; record the answer in `scripting_best_practices.md` |

1. **The method group.** Under Simple Colonies, the Space Program's panel shows a third group, Module Fabrication,
   starting on No Module Fabrication. Orbital Assembly (Cislunar Infrastructure) shows +5 Colony Module Fabrication per
   Month, and the Colony Modules section's first row reads 5.0 at full staff.
2. **Queueing.** Each colony we hold has a row: its Crew share, then the first and second specialization, Habitat,
   Port and Def. A level's tooltip names what it gives. + adds one to the end of the queue ("+1" beside the level, and
   a new last line in the Queue list with the world and the module); the button greys out at four specialization
   levels, the colony's slots or 20 entries, counting what is queued. A queue line's button removes it and the lines
   below move up; a row's clear button removes all of that colony's lines. From the second line on, the arrow swaps
   a line with the one above it, and Alt+Click on it moves the line to the top, the others moving down a place; the
   first line has no arrow, its space kept, so the remove buttons stay in one column, and the "+N" beside each level
   stays the same after a move. Fabrication builds the top line first.
3. **A module's journey.** With 100 points in stock (option b), a queued module fills a shipment (Shipments 1 / 0),
   leaves in its world's window (1 / 0 becomes 0 / 1) and lands after the transit its drive buys (option e lands it
   now). A specialization level doubles that specialization's line in the entry's modifiers; a Habitat raises the
   colony's room in Settlers.
4. **Staffing.** A colony with no people and its founding specialization at level 3 reads 33%, and the specialization
   gives one level's worth; with Artificial General Intelligence it reads 100% and gives three.
5. **Upkeep.** The entry's Colony Modules modifier adds +1% Space Program throughput for each level past each
   colony's first, and the Space Program's Launch Capacity bill follows.
6. **Extraplanetary Base room.** A country with no colony and 20 Extraplanetary Base levels shows Extraplanetary Base
   Room at -25% throughput in the building's breakdown; one holding 16 Psyche and 20 levels shows +30%. Under Races
   Only neither shows.
7. **The AI's bases.** In an observer run under Simple Colonies, AI countries without colonies stop building
   Extraplanetary Base levels at 10 (none queued past it), and private investors in a player's country stop at the
   player's room; the player can still build past it.
8. **The AI's modules.** AI space powers holding colonies switch Module Fabrication on once a year when they queue a
   module, queue Habitats and specialization levels, never Spaceports or Defences, and switch it off with nothing
   queued.
9. **Cession.** A colony ceded with modules keeps them; a module on its way when it was ceded lands for the new holder.

## Autonomy, free colonies, abandonment and colony life (slice 5)

Design: `docs/superpowers/specs/2026-10-26-solar-colonization-free-colonies-design.md`. Simple Colonies is now the
Space Race rule's default. The console is `event te_debug_space_race.5` (log every world's autonomy, freedom and ties;
set our first colony's autonomy to 80; let our first colony go; supply every free colony; full ties with every free
colony we supply; ask whether to abandon our first colony). Grep `debug.log` for `TE_SR_AUTONOMY` after option a, and
for `TE_SR_SITES <world> is a free colony`.

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN colony_evacuation before=… after=… sent=… match=…->… left=…` | once a game, the first time a player brings a colony's people home (Abandon, then Bring them home) | `create_pop` made the evacuees in the capital (or, if it holds Promethean pops, the most populous state without them) as the placeholder culture `promethean`, and `change_pop_religion` / `change_pop_culture` turned them into the capital's largest pop's religion and culture: that state's people of that culture and religion (`match`) grew by at least 90% of them and `left` is 0 | `match` grew less, or `left` is above 0. The state's own growth (`before`/`after`) tells them apart: no growth means `create_pop` made fewer or none at run time, or `state_population` reads the change only later; growth without `match` means a conversion failed or lands only later (`left` above 0: the culture; `left` 0: the religion, or loops that didn't see the new pops) | if the pops show the right culture and religion a few days later, nothing to do; if a conversion fails, the evacuees stay Promethean or atheist: convert them by a different route, or drop the batches; if `create_pop` fails, the evacuees are lost, as a release always lost them: drop the batches and say so in Bring them home's tooltip |

1. **The section.** Under Simple Colonies, Solar System Colonization shows Colony Autonomy below Colony Modules: one
   row per colony we hold, with its autonomy, its drift a month (the drift's terms on hover), Ruled / Charter /
   Garrison / Both, and Abandon; then Free Colonies. Check no label ends in "...".
2. **The demand.** Option b, then wait a month: "<World> Demands Self-Government" names the world. A charter drops
   autonomy by 30, the row reads Charter, and the specialization's line in the entry's modifiers shrinks to 80%; a
   garrison drops it by 25, the row reads Garrison and the entry shows Colonial Garrisons (+2% Space Program
   throughput); letting it go frees it.
3. **Breaking away.** Set a colony's autonomy to 100 with Incite Colonial Autonomy or by waiting at war: the next
   month it reads Free in the Solar System list, its specialization leaves our entry, and a player holder gets
   "<World> Declares Itself Free".
4. **Abandoning.** Abandon (or option h) asks first. Bring them home releases the world (Unclaimed in Solar System)
   and logs `colony_evacuation`; the capital's population rises by the colony's people, in whole thousands, as its
   largest pop's culture and religion (no Promethean pops in its pop list; a capital that already had some sends them to
   the most populous state without any). Leave them to govern themselves makes it
   Free, with our ties at 50. An outpost of fewer than 1,000 people offers only Close
   the outpost.
5. **Free colonies.** Supply a free colony: the entry shows Free Colony Supply (+3% Space Program throughput) and Free
   Colony Trade, the colony's people grow again, and our ties climb 2 a month. At 100 (option g, then a month) "<World>
   Asks to Join Us": welcome it and it is ours again at autonomy 20, with its people and modules.
6. **A dead holder.** `annex <TAG>` an AI holder whose capital region nobody can take a colony for: a world with 1,000
   people or more reads Free, not Unclaimed.
7. **Colony life.** Our first colony to reach 2,000 people gets "The First Child of <World>", and no later colony
   does. Strikes and dome breaches come rarely, at colonies of 10,000 and 5,000 people, and never within ten years of
   the last one (`sr_life_cooldown`). A dome breach names the people lost, and Settlers shows the colony smaller.
8. **The AI.** In an observer run, AI space powers answer the demand with charters, supply up to two free colonies,
   and welcome a colony that asks to join.
9. **Covert operations.** Incite Colonial Autonomy and Sabotage Colony appear in the diplomatic actions against a
   country holding a colony under Simple Colonies, and not under Races Only; once established, the target's colonies'
   autonomy climbs (Incite) or its largest colony loses people (Sabotage).
10. **Old saves.** A save from before this change keeps its Space Race setting; its colonies start at autonomy 0.

## Fleets, Space Command, combat and seizure (slice 6, parts 6a and 6b)

Design: `docs/superpowers/archive/specs/2026-10-26-solar-colonization-fleets-design.md` (§ 22 records what was built and where
it departs). Everything here needs the Space Race rule at Full Colonies; under Simple Colonies and Races Only none of
it shows. The console is `event te_debug_space_race.6` (log our fleets and every location's forces; 100 strength of
each role at Earth; land our fleets now; fill propellant and supply; our fleets' drive one up; our first colony's
integrity to 0; this month's combat now; occupy our first colony by our strongest enemy, or return it; the two upkeep
probes). Grep `debug.log` for `TE_SELF_CHECK`, then `TE_SR_FLEET`, `TE_SR_LOC`, `TE_SR_COMBAT` and `TE_SR_PROBE`.

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN ship_construction country=… rate=…` | once a game, a month after a Space Command first runs at half staff or more in a state its owner controls | `sr_sc_rate`, the sum of `modifier:state_sr_ship_construction_add` over the states its owner controls, reads above 0: a production method's workforce-scaled `state_modifiers` reach the state | it reads 0 | compute the rate in script, level × occupancy × the method's rate by `has_active_production_method`, and state the rates in the methods' descriptions |
| `TE_SELF_CHECK OK/BROKEN fleet_leg location=… drive=… leg=… flown=…` | OK once a game, on the first fleet that lands in its month; BROKEN once, if any fleet lands two or more months late | `flown` equals `leg`, the months `docs/engine/launch_windows_report.md` gives that leg and drive | the global monthly step missed an arrival | land fleets from the country pulse as well |
| `TE_SR_PROBE upkeep_inputs candidate=… before=… after=…` | console options k and l, fourteen days apart | see the probe below | | |

**What checks itself, and what needs a hand.**

- **Logged with no input:** start a game at Full Colonies and grep `error.log` and `debug.log` for the new files
  (`sr_fleet*`, `sr_fleets_generated*`, `space_race_events.txt`, `covert_operations.txt`): script errors in them show at
  load. `ship_construction` logs by itself once any country has run a Space Command at half staff for a month: an AI
  space power in an observer run, or you.
- **Logged after one action:**
  - `fleet_leg` logs on the first fleet that lands, so send one (AI fleets seldom leave Earth outside a war).
  - The probe needs console options k and l, and a read of the input tooltip.
  - `TE_SR_FLEET` and `TE_SR_LOC` are console option a's.
  - `TE_SR_COMBAT` lines log every occupation, liberation, seizure and destruction as it happens.
- **Set up by hand and read by eye:** steps 1 to 22 below. Console option b gives a fleet, h and i force an assault
  and a month's combat, and j an occupation, which shortens most of them.

**The upkeep probe (open call, owner).** The fleets' upkeep ships as `sr_fleet_upkeep_goods`, the three good-specific
input multipliers (Launch Capacity, Advanced Materials, electricity), which the mod already uses. The design prefers
`sr_fleet_upkeep`, the generic `building_goods_input_mult`, which follows any change to the methods, but the owner
recalls trouble with it. With a Space Command (or, before one, a Space Program) built: option k, wait fourteen days,
read the Space Command's input tooltip and the two `TE_SR_PROBE` lines (the market's Launch Capacity buy orders before
and after; a jump of about half the building's bill means the candidate worked). Then option l and the same. If the
generic one raises every input, switch `sr_fl_upkeep_apply` to `sr_fleet_upkeep` and record the answer in
`docs/guides/scripting_best_practices.md`.

1. **The rule.** Under Simple Colonies, no Space Command building, no Space Command, Fleets or Colony Defences
   sections, no Survey Colony Defences operation, and `.94`'s Send a garrison works as slice 5 built it. Switch to Full.
2. **Space Command.** Research Space Militarization: Space Command can be built by the government, and only in a state
   with a Space Program. Its four methods (Orbital Shipyards, Fusion Yards, Torch Yards, Antimatter Yards) each show
   "Fleet Strength Built a Month" scaled by staffing. Staffed, the panel's Space Command section reads the strength
   built last month and the levels; the home fleet appears at Earth in Fleets; `ship_construction` logs OK.
3. **The build mix.** Each role's button steps 0, 1, 2, 3, 0; the next month's construction follows the weights
   (option a's per-role figures, or the strength hover).
4. **Upkeep.** As the fleets grow, Space Command's input tooltip shows Fleet Upkeep, +1% for every 10 strength at
   full, and the section's Upkeep figure matches. Nothing else's inputs change.
5. **Orders.** Pick a destination (the button steps through the other eight; its hover gives the leg's months and
   km/s), then Go: Go is disabled with the reason when the leg can't leave or the propellant is short (a chemical fleet
   at Earth outside Mars's window, for instance). In transit the row reads "→ Mars" and its landing month; on landing
   `fleet_leg` logs OK and the months flown match `docs/engine/launch_windows_report.md`.
6. **Docking and refits.** A fleet back at Earth refills propellant and supply, repairs 20% of its damage a month, and
   refits to a newer drive (Refit shows three months). A fleet at our colony with a Spaceport repairs 10% a level, and
   refills propellant by 25% a month only on a world that makes it (Utopia Planitia, Ceres, Europa, Ganymede, Callisto,
   Titan, Enceladus, Rhea, Triton, Pluto). Away from a dock, supply counts down; at zero the fleet loses 5% a month.
7. **Merge, detach, marines.** Merge two fleets at one location; detach half of one into a free slot. At Earth the
   carriers fill with marines (2 battalions a point of carrier strength); Land puts them at our colony there (Colony
   Defences shows them), Embark takes them back.
8. **Garrisons under Full.** Answer a demand for self-government (`.94`, option b of `te_debug_space_race.5`) with a
   garrison: nothing changes until a fleet lands 2 battalions there within a year, then the garrison takes effect as in
   slice 5. Without one, "Garrison for <World> Never Came" after a year.
9. **The location records.** Locations lists the nine locations with our strength, the strongest other power's flag
   and everyone else's strength, the inbound fleets ("count·months", highlighted when ours lands first). Compare
   option a's `TE_SR_LOC` lines.
10. **The AI.** In an observer run with Full Colonies: AI space powers in the top three build Space Command (a few
    levels, never in default or with a negative income), garrison their colonies under Full, and bring fleets home
    short of supply or propellant.
11. **A hostile fleet's alert.** An AI at war with us sends a fleet to a location where we hold a colony (or, from a
    second player's seat, send one): we get "Hostile Fleet Bound for <location>" with the months to its landing.
12. **Combat.** Two fleets at war at one location, both Station: each month both lose strength by the square law
    (losses = 0.1 × the other side's fire, fire = strength × role factor × quality; 100 against 50 ends near 87 left).
    "Battle Over <location>" reports our losses, theirs and what's left, at most once a month; the location's status
    reads Battle; screens (warships, rapid response) take the losses before carriers and tenders. At Earth, any
    Orbital Battlestation fights for its owner (25 strength a level) and regains 10% a month; a battle there adds
    debris (Orbit section).
13. **Postures and blockade.** Stand off at an enemy's colony with no enemy fleet holding orbit: its row in their
    Colony Defences, and our Locations row, read Blockaded / Blockading; their settlers and modules stop arriving,
    a mining or shipping specialization's modifier goes to nothing while an observatory's keeps running, and its
    Extraplanetary Base room drops out.
14. **Assault and seizure.** Close in on an enemy's colony (the target button steps through hostile worlds; its hover
    gives the target's Defences as a range, exact with Survey Colony Defences): its Defences fire back and its
    integrity falls; at 0, with more marines than its garrison and militia, "<World> Occupied" to both sides. It
    gives its holder nothing, shows Occupied with the occupier's flag, and the war-support breakdown shows "Colonies
    occupied in space". At the peace it returns ("<World> Returned"), unless a Cede Colony article took it.
15. **Liberation.** The holder closing in with more marines than the occupier's garrison frees it ("Liberated").
16. **Destruction.** Toggle To destroy and close in for three months with no enemy fleet stationed: "<World>
    Destroyed", the destroyer's infamy +20, its UN record's "Hostile acts in space" +20, its own colonies +10
    autonomy and a ten-year drift term; the world reads Ruined and no colony fleet can target it for 25 years.
17. **Free colonies by force.** Close in on a free colony, no war needed: 10 infamy at once; at integrity 0 with marines
    above its militia it is ours at autonomy 60, and its suppliers are told.
18. **War support.** In a war with battles in space, the breakdown shows "Battles in space" (±0.1, ±0.25 in a rout)
    for thirty days after each battle month.
19. **Survey Colony Defences.** Against a colony holder at Full: once established, our fleets' target hover shows the
    target world's Defences, integrity and marines exactly, and our fire on its defences is higher (compare option
    i's `TE_SR_COMBAT` figures with and without).
20. **Occupied states (§ 5.1).** Occupy, province by province, a state holding a Space Command or the Orbital
    Battlestation: note the month construction stops and the battlestation stops fighting, and that both resume when
    the state is retaken.
21. **Revolutions.** A fleet power whose revolutionaries win: the winner has its fleets the same day, and a world the
    old government occupied stays occupied by the winner.
22. **Panel.** Every new section opens and closes and no label ends in "...". The fleet row's orders line fits on
    one line; a full nine-slot Fleets section and the Locations list stay readable.

## Interdiction, the AI's offence and the outer-space convention (slice 6, part 6c)

Design: the fleets design's §§ 12–14 (§ 23 records what was built and where it departs). Full Colonies, as for 6a and
6b. Console option m of `event te_debug_space_race.6` starts an interdiction with our first fleet that may make one.
No new self-check: the script sees everything here, and the two engine questions (the war goal's scopes, the AI's
choices) are read by eye. `TE_SR_COMBAT interdiction begun …` lines log each interdiction, one for each side.

1. **The Interdict posture.** A fleet at a location where a country at peace with us, and not our ally (no alliance or
   defensive pact), holds a colony: the posture button steps Station → Stand off → Close in (only with a hostile world
   there) → Interdict → Station, and its hover names the price when Interdict is next. Where only allies or enemies
   hold colonies, Interdict is skipped. The target button, while interdicting, steps through the worlds of countries
   we may interdict.
2. **The price.** Entering Interdict: our infamy +5, our UN record's "Hostile acts in space" +10, once for that fleet
   and that country (stepping the target to another country's world pays again; staying put pays nothing more).
3. **The blockade.** With none of the target's fleets there, from the next month its colonies at that location read
   Interdicted in its Colony Defences and Locations, and ours reads Interdicting; settlers and modules stop arriving,
   a mining specialization stops, an observatory keeps running, and its Extraplanetary Base room drops out (as step 13
   of 6a/6b). Its other colonies elsewhere are untouched, and a third country's colonies at the same location too.
4. **The standoff.** The target stations or stands off a fleet there: the blockade lifts the next month, and nobody
   fires (no battle report, no losses).
5. **The target's notice.** From the target's seat (a second player, since the AI never interdicts): "Our Colonies
   at <location> Interdicted", naming the interdictor.
6. **Cede Colony's war goal against an interdictor (engine read).** As the target, within five years: start a play
   against the interdictor with Cede Colony as a war goal. The war goal's infamy reads 0, with the line "They
   interdicted our colonies in peace". The same war goal against anyone else, or against the interdictor after five
   years, costs its 10. If it reads 10 against the interdictor, the war goal's `infamy` block doesn't see
   `scope:target_country` or `root` as vanilla's Money Transfer reads them: record it, and fall back to halving the
   article's AI score instead (plan C1.3).
7. **The interdiction's end.** Declare war on the target: the fleet stands off and blockades it as an enemy. Or sign
   an alliance or defensive pact with it, or let the world change hands: the fleet stands off and Interdicted clears.
8. **The AI answers an interdiction.** Interdict an AI's colonies: within a few months it sends a fleet there (if one
   can reach it within six months) and stations it, and the blockade turns into a standoff.
9. **The AI attacks at war.** In an observer run, or at war with an AI fleet power that outmatches us somewhere within
   a year's flight: once a month at most it sends one docked fleet to the nearest location with an enemy colony where
   it is at least 1.5 times the enemy's fleets and Defences there. On arrival it closes in on the colony with the most
   people and modules (if its marines exceed the garrison and militia) or stands off and blockades. It never toggles
   Destroy, never attacks a free colony and never picks Interdict. It brings the fleet home when short of supply or
   propellant, or when the enemy's fleets there outmatch it.
10. **The convention in the chamber.** At Full Colonies, with the UN founded and a colony held somewhere, the chamber's
    Table a Resolution list shows "Convention on the Settlement of Outer Space" (under Simple Colonies or Races Only the
    row is hidden); a member holding a colony may table it; its hover gives the terms. After a seizure or destruction
    the docket offers it ("A Convention on the Settlement of Outer Space", with the cause line naming who did it) to
    a member holding a colony, never the actor. Carried, the overview's COPUOS lights, parties carry "Outer Space
    Settlement Convention" (+2% prestige × enforcement), and a party's Destroy price tooltip and free-colony price
    read 40 and 20 infamy (twice the 20 and 10). Refusing it in the proposer event leaves "Refused the Outer Space
    Settlement Convention".
11. **Art.** The convention's topic icon in the session strip is COPUOS's domed moon rock under the scroll, and COPUOS's
    agency icon the domed moon rock alone, each its own file (icon batch 6).

## Earth orbit: the ground reserve, batteries, Earth's blockade and fire support (slice 6, part 6d)

Design: the fleets design's §§ 5.1, 14 and 15 (§ 24 records what was built and where it departs). Full Colonies,
which is now the Space Race rule's default for a new game; a save keeps its own setting. Console options of
`event te_debug_space_race.6`: n fills our ground reserve (100 of each role), o has the strongest country at war with
us put a fleet of 100 of each role at Earth (with none of ours there, a blockade).

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN battery_sweep sweep=… low_before=… low_after=… high_before=… high_after=…` | once a game, a month after a country at peace first runs Ground Lasers at half staff or more in a state it controls | the world's debris step took a sweep, the low pool fell by all of it (or to 0) and the high pool didn't move | the low pool fell by less, the high pool moved, or (`sweep=0`) nothing was swept: the method's state modifier doesn't reach the state | compute the sweep in script, level × occupancy × 0.01 by `has_active_production_method`, as `ship_construction`'s fallback does |

1. **The reserve.** With a Space Command running and no enemy fleet at Earth, Space Command's Reserve row stays near
   0 and the home fleet grows each month, as before (Auto: on). Switch Auto off: the Reserve grows a month at a time,
   its hover gives the roles, and the home fleet stops growing. Launch puts it all up as one fleet at Earth, with
   full propellant, supply and marines. The upkeep figure counts the reserve too.
2. **The reserve against a blockade.** At war, console option o (our fleets away from Earth): the Locations row for
   Earth reads Blockaded, Space Command shows the red note, and "Earth Orbit Blockaded" arrives naming the enemy.
   Auto holds the reserve on the ground. Launch still works: the new fleet fights at Earth the next month and the
   blockade lifts while it survives. An AI blockaded this way launches once its reserve and its fleets at Earth match
   the enemy's there.
3. **What a blockade stops.** While Earth reads Blockaded: no colony fleet leaves (a full bar waits), module
   shipments wait at Earth, settlers stop, Go on a fleet at Earth is greyed with "Nothing leaves Earth", and our
   colonies' autonomy counts months without contact (no fleet arrival or module landing renews it). Modules are still
   fabricated, and a fleet already away can still move between other locations.
4. **Batteries.** Build a Ground-to-Orbit Battery (Space Militarization) in a few states. Its method's tooltip and the
   state's modifiers show "Fire on Hostile Fleets at Earth" (and with Ground Lasers "Low-Orbit Debris Swept in Peace",
   +0.01 a level, not +0). With an enemy fleet at Earth the battle report comes each month and the enemy loses about
   0.1 × the batteries' fire a month; the batteries lose nothing and don't lift a blockade. Kinetic Interceptors raise
   the low debris pool a little (0.02 a point fired); Ground Lasers don't.
5. **Sweeping.** At peace with Ground Lasers running, the Orbit row's low pool falls each month by 0.01 a level beyond
   its decay and the high pool is untouched; at war the sweep stops. The `battery_sweep` line above reads OK.
6. **Orbital superiority.** At war with our fleets at Earth and the enemy's weaker there (or absent): our country's
   modifiers list "Orbital Superiority" and a land battle's offense and defense breakdowns show it, up to +10% and +5%
   at a margin of 1 (our strength there twice the enemy's, or 10 above none). It goes at the peace, or when the enemy
   outmatches us at Earth.
7. **Occupied states** (design § 5.1). Occupy, province by province, the state of our Space Program, then a battery's:
   note the month each stops (every launch, module fabrication, the reserve's Launch; the batteries' fire and sweep)
   and that each resumes when the state is retaken. "Our Launch Site Is Occupied" arrives once, and "Our Launch Site
   Is Ours Again" when it is back. Record at how many provinces `controller` turned, as for Space Command (6a/6b's
   step 20).
8. **The AI's batteries.** In an observer run: an AI builds batteries only while at war with a country that has
   fleets, up to five levels, and switches to Ground Lasers at war or once debris is Cluttered when it has Directed
   Energy Weapons. Whether the building's own AI then keeps the method it was given is a watch item.
9. **The default.** A new game's setup screen shows Full Colonies selected for the Space Race rule, its description
   naming fleets, blockades of Earth and batteries. A save from before keeps its setting.

## The colonization panel after the GUI audit (2026-10-27)

The colonization sections' share of the GUI and localization audit (`docs/audits/gui_audit/space_seabed.md`, SPC-1 to SPC-19). No self-check: everything here is display and fails visibly (a blank, a raw key, a row in the wrong view). The race-wide items and the `sr_powers_list` self-check are in `docs/testing/space-race-playtest.md` under the same date.

1. **The overview cells (`te_banking_ov_cell`, hovers through `sr_colony_overview_sgui`'s `ExecuteTooltip`: new).** Under Simple Colonies: Colonies reads Loyal with "N of 34 held"; push a colony to autonomy 75 (`event te_debug_space_race.2` or wait) and it reads the colony's name in red, "wants self-rule", then "+N more want it" with a second; its hover lists them by name. Modules reads "N queued", or Queue empty (red once the fabrication stock is full). Next Window reads "in N months", "Open now", "Any month" with a torch drive, or "No site left". Under Full Colonies a Defense cell joins them: Calm, then, with an enemy fleet standing off a colony, Blockaded and the colony's name, its hover listing every threatened colony and an inbound hostile fleet's landing.
2. **The Colonies view switch (`GetVariableSystem.Set` / `HasValue` on `sr_colony_view`).** People is the default; each button shows its view's figures above the rows and its columns on each row's second line, the active button greyed. Defenses shows only under Full Colonies; an occupied colony appears there, with its occupier, and in no other view. Under Races Only, the switch is gone and each row is the icon and name.
3. **A colony's name hover (`AddLocalizationIf` of whole keys, each with its `GetStaticModifier(...).GetDesc`).** Lists the specializations we hold there at their levels, nothing for one we don't, and no stray blank lines.
4. **A colony's drift hover (`AddLocalizationIf` chains with `te_tt_newline`).** The total, the pull of home, its people, its distance by our drive; the no-contact, charter, garrison, war and destroyed-colony lines only when they apply, each with its figure. The total matches the row's Drift figure.
5. **Solar System's filter.** Open by default; it lists the worlds our next fleet can go to, ours and any a fleet is bound for, under their locations, with the count line above (`SelectLocalization` of keys rooted on `GetPlayer`). Show all lists all 34 and reads Show fewer. A world's name hover gives its stage and location, both specializations' effects, the transit by our drive and, while windows apply, its next window.
6. **Colony Fleets.** Our target reads the world with Clear beside it (Clear works, then reads Next fleet: chosen at launch, its hover the program's pick); the Drive row names the drive, its label a concept link.
7. **Greyed buttons (SPC-1, the generated rows).** Hover a greyed Target (the program not running, or a world it can't take), a module + with the queue full, the slots used or the specialization not chosen (each condition its own line), Abandon with a request pending, a fleet's Go while refitting: each shows the failing requirement with a cross, then what the button does. The fleet destination and target buttons keep their leg and intelligence hovers below the reason.
8. **Space Fleets and Locations.** The section reads Space Fleets; Space Command's row reads Fleet strength; Locations' inbound column wears the warship (icon batch 7: a dark grey armed spacecraft, legible at 16 px?), Solar System's the colonization rocket. The overview's Defense cell shows the warship too, and the Modules cell a silver habitat module.
9. **How Solar Colonization Works.** Collapsed at the foot of Solar System Colonization, seven subsections; the live sections open on their rows, with no paragraph of rules above them.

## A world's specializations on hover (2026-10-28)

The Solar System world hovers listed both specializations' effects in one run, so a player couldn't tell which belonged to which. Each now has its name in bold with its effects indented beneath it (`#indent_newline:3`, vanilla's form, new to the mod's own localization). No self-check: it is display and fails visibly.

1. **Two labeled blocks.** Hover 4 Vesta in the Solar System list: "It offers two specializations:", then Vesta Mining Operations with Advanced Materials output and Extraplanetary Base throughput indented under it, then Vesta Science Outpost with research speed and space race progress under it. The transit line and the window line after them are back at the margin. If the effects are not indented, or the indent runs on into the transit line, write each block as a bold name, `\n`, then the `GetDesc` with no indent (the UN terms' form).

## Funding past the cap (lunar colonization design § 5.1, 2026-10-29)

A milestone's funding may go six levels past the cap, each worth less pace than the one before (1/2 of a level, then
1/3, down to 1/7); every level still costs in full and adds its full +25% Space Program throughput. The pace and the
throughput are two modifiers on the entry now, `sr_funding_progress` and `sr_funding_throughput`. No self-check: the
engine's modifier sum can't single out one source, and the panel shows the result. `event te_debug_space_race.1`
reaches a milestone.

1. **The stepper.** Fund a running milestone to the cap: the figure reads as before ("7 / 7"). Press + once more: it
   reads "8 / 7 (+0.5)", then "9 / 7 (+0.8)", and at six past the cap "13 / 7 (+1.6)" with + greyed. Nothing ends in
   "..." (the cell is 140 wide now) and the minus and plus buttons sit beside the figure.
2. **The plus button's tooltip.** At the cap it ends with "Past the cap: +1/2 of a level of pace, at full cost"; one
   level past, "+1/3"; at five past, "+1/7". Below the cap that line is absent. At six past, the button is greyed and
   its first line reads "Funding is not yet six levels past the cap" with a cross.
3. **The pace.** Hover the headline's "+N/mo": the Funding line reads "N levels within the cap, X effective levels past
   it", summed over the running milestones. In the "Added each month" breakdown the Funding Progress Bonus of an entry
   funded at 9 with a cap of 7 is +3.9 (7.83 × 0.5), not +4.5, and the added progress rises by 0.25 and then 0.17 for the first
   two levels past the cap.
4. **The throughput.** The Space Program's throughput breakdown shows Funding Throughput Bonus at the full +25% a level,
   past the cap too (+225% at 9), and the Launch Capacity bill rises with it.
5. **A cap that moves.** Fund a milestone to the cap with Advanced Research tier V, then lose the principle (leave the
   bloc, or change the principle): the level stays and the figure reads "N / N−1 (+0.5)" at once. The pace follows at
   the next monthly pulse, which sees the cap differ from the one the costs were computed with (`sr_cost_funding_cap`)
   and recalculates: that entry's Funding Progress Bonus drops by 0.25 (the top level now counts as half a level). The
   other way, research a cap technology while funded at 9 with a cap of 7: "9 / 7 (+0.8)" reads "9 / 8 (+0.5)" at
   once, and within a month the bonus rises from +3.92 to +4.25. Until that pulse the pace hover's
   Funding line (live values) and its "Added each month" breakdown (the modifier) can disagree by that much; after it
   they agree. If they still disagree a month later, `sr_cost_funding_cap` isn't being compared or set.
6. **The AI.** In an observer run, no AI's stepper shows "(+…)": the AI stops at the cap. One left past it by a falling
   cap funds down to the cap within a few weeks.
7. **An old save.** Load a save from before the split with a running milestone: within a month its entry carries both
   Funding Progress Bonus and Funding Throughput Bonus, and the Space Program's throughput is what it was before the
   update.

## Lunar colonization, build 1: technologies and the era-10 base (2026-10-29)

The first build of `docs/superpowers/specs/2026-10-29-lunar-colonization-design.md` (§§ 5, 6): three technologies, the colonization method and Orbital Assembly on Cislunar Infrastructure, the Extraplanetary Base on In-Situ Resource Utilization with Regolith Processing. Colonization still needs the Moon Base and the Mars Landing until the second build. No self-check: the one engine question (item 6) shows in the game's own behaviour.

1. **The tree.** Cislunar Infrastructure (era 10, military) follows Reusable Rocketry; In-Situ Resource Utilization (era 10, military) follows Reusable Rocketry; Nuclear Thermal Propulsion (era 11, military) follows Cislunar Infrastructure; Asteroid Mining now follows In-Situ Resource Utilization and Directed Energy Weapons. Each shows its space race funding cap line (+2, +1, +1) and a placeholder icon (Reusable Rocketry's, Asteroid Mining's, Fusion Power's).
2. **The method.** With Cislunar Infrastructure, the Space Program's Solar Colonization method and Module Fabrication's Orbital Assembly unlock; Solar Colonization reads 10,000 Launch Capacity a week at full staff. Begin Solar Colonization shows with Cislunar Infrastructure and is still possible only after the Moon Base and the Mars Landing.
3. **Switching early by hand.** Before the Moon Base and the Mars Landing, switch the method in the building panel: the bill rises from 5,000 to 10,000, the Moon Base and the Mars Landing keep running (the method carries the Mars Mission's), and Solar System Colonization does not start. This is the intended intermediate state (a method has no `possible`), not a bug. Watch an AI too: the method group picks the most productive method, so an AI with Cislunar Infrastructure and no Moon Base may switch on its own and pay 10,000 a week for nothing. The second build ends this, since the method then opens colonization itself.
4. **The cost factor.** Solar System Colonization's Space Program Cost reads ×8 for a country with the Mars Landing (15 innovation × 8 a funding level); a country holding a colony by treaty without the Mars Landing pays ×5, and its cost re-posts when its Mars Landing completes.
5. **The era-10 base.** With In-Situ Resource Utilization, an Extraplanetary Base can be built and starts on Regolith Processing (15 Electronic Components, 15 Wireless Telecommunication Gear, 5 Digital Access and 60 Launch Capacity for 175 Structural Metals, 95 Tech-Critical Metals and 50 Glass and Plastics a level); the Asteroid Mine method waits for Asteroid Mining. Under Simple or Full Colonies, the Modules view reads room 0 until Asteroid Mining or a colony, and a level built then works at −50%; Asteroid Mining adds the near-Earth 10. AI governments and private investors don't build a base with no room.
6. **An old save (`te_repair_lunar_technologies`).** Load a save from before this build in which a country runs Solar Colonization or Orbital Assembly on Directed Energy Weapons, and one holds Asteroid Mining. In the first month, `debug.log` has a `TE_LUNAR_TECH_REPAIR` line for each, and they hold Cislunar Infrastructure and In-Situ Resource Utilization. Before that month ends, watch the colonizing country's Space Program: if the engine moved it off Solar Colonization at the load (its technology unresearched for a moment), its colonization entry fails (the program lost), and a colonizer with no colony yet loses its progress toward its first colony with the entry's `on_fail`. Fallback for that: switch back by hand after the first month (the AI through Begin Solar Colonization); nothing in script runs before the first monthly pulse.
7. **Orbital Foundries.** Space Colonization's fabrication method reads Orbital Foundries in the method group, the Colony Modules section's fabrication tooltip and the method's own description.
8. **Art (icon batch 7).** The three technologies show their own icons in the tree: Cislunar Infrastructure an orbital station with a lander docked, In-Situ Resource Utilization a tracked regolith processor, Nuclear Thermal Propulsion a reactor engine. None repeats Reusable Rocketry's, Asteroid Mining's or Fusion Power's.

## Lunar colonization, build 2a: six lunar worlds at stage 0 (2026-10-29)

The second build of `docs/superpowers/specs/2026-10-29-lunar-colonization-design.md` (§§ 3, 4, 8): the Moon's six worlds as stage 0 (Shackleton Crater, Peary Crater, Tranquility Base, Marius Hills, Daedalus Crater, Mare Imbrium), founded the month a fleet leaves, the Moon Landing site's discount and Shackleton's Propellant Depot. Colonization still needs the Moon Base and the Mars Landing, and the Moon Base still runs, until build 2b. The console is `event te_debug_space_race.2` and `.3` as above.

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK lunar_stage0_draw world=<key> …` | once a game, the first lunar world the Races Only draw founds | the stage-0 draw found the Moon in play and founded a lunar world the month the bar filled | `TE_SELF_CHECK BROKEN lunar_stage0_draw held=… best_cost=…` (once a game): under Races Only with no target, a full bar was held three months at stage 0 with a lunar world free, so the Moon is missing from `sr_launch_best_cost` or `sr_launch_ungated_departs` read false, and Mars stays locked for everyone | read `best_cost`: above 0, `sr_window_moon_in_play` is false (check its `sr_colonization_stage >= 0` arm); at 0, give the lunar draw branches no departs test at all |
| `TE_SELF_CHECK OK/BROKEN propellant_depots_bool …` | OK once a game, once a Shackleton holder read the boolean yes and a country that lost the world (ceded, released or taken by an heir) read no; BROKEN once, on a mismatch two launch months running | Shackleton's Propellant Depot on the colonization entry reaches the country as `modifier:country_sr_propellant_depots_bool`, and leaves it with the world. Its ×0-under-blockade case comes with build 3b's lunar blockade (its section below) | `record=yes boolean=no`: the entry's boolean doesn't reach the country; `record=no boolean=yes`: the boolean outlived the world | use `sr_depots_by_record = yes` in place of the modifier in `sr_launch_has_depots` (`sr_launch_window_triggers.txt`) |
| `TE_SELF_CHECK BROKEN lunar_double_claim <key> …` | never, if all is well: a lunar world founded while it already had a holder | (no OK line) | two countries founded the same lunar world in one month: the dispatch's same-month founding doesn't see the first claim | test `sr_cf_targetable_<key>` again inside `sr_cf_found_now_<key>` and send the second fleet's progress back |

1. **The Moon first.** Start Solar System Colonization in a new game: the overview reads "Stage: the Moon", Next Window reads Open now over "the Moon" (build 2b; the Moon needs no window), and the Solar System list shows the six lunar worlds under The Moon at the top. Hover one: Stage 0: The Moon, its two specializations, and that a fleet bound there founds its colony the month it leaves. The Worlds pie and Colonies Held count 40.
2. **Founded the month it leaves (every setting).** Fill the bar under Races Only, then under Simple or Full: the colony is founded that month, its event (`space_race_colony_events.35` to `.40`) fires, and under Simple or Full Colony Fleets shows no fleet in flight for it. With six fleets already in flight to other worlds, a lunar fleet still leaves.
3. **Races Only steps on.** Under Races Only, once all six lunar worlds are claimed, the stage reads 1 and Mars and the asteroids draw. An old Races Only save already past stage 1 draws lunar worlds first, since they are released and need no window (accepted, design § 3.2).
4. **The landing discount.** In a game whose Moon Landing chose Shackleton Crater, target Shackleton Crater under Simple or Full: the bar's goal reads 225 (300 less 25%), the world's hover says the discount is ours, and a rival pays 300. Under Races Only the bar still reads the stage's 300, but the targeted colony is founded once progress reaches 225: the bar takes a target's own goal only under Simple and Full, a display gap left as it was (a released earlier-stage target already founded below the bar). Without Target the draw pays 300.
5. **Two AIs, one lunar world, one month.** In an observer run under Simple Colonies, watch for two AI powers whose bars fill in the same month with one lunar world left: one founds it, the other's fleet does not (no `lunar_double_claim` line, and only one founding event). Note what the second did with its progress.
6. **Shackleton's depots.** Hold Shackleton Crater with the Propellant Depot and no Asteroid Mining: Next Windows shows today's premium for closed destinations and a fleet can leave off-window. Give the colony away (Cede Colony, or `event te_debug_space_race.2`, which gives our first colony away as Cede Colony would): the premium lines go. The `propellant_depots_bool` line should be OK by then. A blockade can't switch the depots off in this build (item 7).
7. **Superseded by build 3b.** The lunar blockade, Close in at Earth and the AI's lunar offence are build 3b's (its section below). No enemy can interdict at Earth.
8. **No Spaceport.** In the Modules view, a lunar colony's Spaceport cell reads "-" with a hover saying why, and has no button; its slots take Habitats and Defenses.
9. **An old Simple or Full save.** Load a save from before this build with the stage past 1: at the first monthly step (`sr_sites_recompute_stage`) the stage drops to 0, since the Moon's worlds are unclaimed. The overview reads "Stage: the Moon" mid-game and the automatic pick favors the Moon (its score, 100, beats every outer world), but a fleet can still be sent anywhere a Target reaches, and a Target pays its own world's goal. Consistent with the design; note how it reads to a player.
10. **The Mass Driver fabricates.** Hold Mare Imbrium with the Mass Driver under Simple or Full and No Module Fabrication: the stock grows 3 points a month (times the specialization's level and the colony's staffing), and queued modules are built. The `module_fabrication` self-check skips that country, since its points need no method.
11. **Races Only, lunar colonies but no Deep Space.** A country holding only lunar worlds, without Deep Space Exploration, reaches stage 3: its bar fills and is held every month (the stage 3 to 5 draws need Deep Space or a colony beyond the Moon), and it founds nothing more. Intended (design § 4); an AI in this state is waiting for Begin Deep Space Exploration, which from build 2b it is offered: only a colony beyond the Moon hides it (build 2b's item 3).
12. **The Moon's icon (icon batch 7).** The Solar System list's lunar rows and Cede Colony's picker show a mid-grey Moon with dark seas, evenly lit, not Mercury's half-lit grey-brown planet.

## Lunar colonization, build 2b: the Moon Base retired (2026-10-29)

Build 2b of `docs/superpowers/specs/2026-10-29-lunar-colonization-design.md` (§§ 4, 7): Solar System Colonization opens on the Moon Landing with Cislunar Infrastructure, and each world beyond the Moon needs the Mars Landing; a country's first lunar colony takes the Moon Base's place in the race; the Moon Base milestone is retired, and an old save's Moon Base becomes a lunar colony. Lunar blockades are build 3b's (its section below). The console is `event te_debug_space_race.8`: option a runs the migration's check again, b pretends we finished a scientific Moon Base and holds no lunar world (the migration runs again next month), c pretends an old Moon Base is open with 120 progress (next month's pulse carries it).

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK lunar_migration migrated=<n>` | once a game, the first monthly step of an old save (`sr_lunar_migrate`, behind `sr_lunar_initialized`) | every country that finished the old Moon Base holds a lunar world, or none was free; `n` > 0, so a new game, which migrates no one, logs nothing | `TE_SELF_CHECK BROKEN lunar_migration country=… migrated=…`: a country that finished the Moon Base holds no lunar world while one is free, so `sr_lunar_migrate_country`'s chain gave it none | empty `LUNAR_MIGRATION` and `LUNAR_MIGRATION_NO_PURPOSE` in `gen_solar_sites.py`, so every country takes the first free lunar world in table order with its first specialization |
| `TE_SELF_CHECK OK lunar_migration carried=<p> banked=<b>` | once a game, the first open Moon Base the monthly country pulse carries (`sr_lunar_carry_moon_base`) | the open entry's progress (at most 300) is banked for Solar System Colonization before the inactive cleanup clears it; `banked` is what the next launch month adds | `TE_SELF_CHECK BROKEN lunar_migration still open: …` (once a game, from the retired entry's own pulse, `sr_lunar_carry_lingering_check`): two months after the carry the retired entry is still active, so its `possible = { always = no }` didn't deactivate it. It moves nothing (its pulse runs only while `sr_active_moon_base`, which the carry removes), but it shows in the journal | make the retired entry fail at once (`fail = { always = yes }`, its `on_fail` emptied so no programme-loss report plays); the carry runs before the cleanup either way |

1. **The Moon on the Moon Landing.** In a new game, with the Moon Landing and Cislunar Infrastructure but not the Mars Landing: Begin Solar Colonization appears from the Moon Mission and is possible; the journal never shows a Moon Base. Colonization founds only lunar worlds, under Races Only too (the draw has no world beyond the Moon). Under Simple or Full, hover Target on a world of Mars: it is grayed with "The site is on the Moon, or we have completed the Mars Landing". Once the Moon is full, the bar fills and holds, and Next Window's third line reads "no Mars Landing" (design § 4: the panel says why). After the Mars Landing the button works, the line reads the stage again, and under Races Only stage 1 draws.
2. **The first lunar colony.** Found a lunar world: its colony event (`space_race_colony_events.35` to `.40`) fires, then Foothold on Another World (`space_race_events.6`) a day later, with one option and the Lunar Colony reward (First Lunar Colony for the race's first); other countries get the notice that we founded a colony on the Moon (`.20`), and the Program row's Lunar Colony icon lights, with the first mark for the race's first (no half-lit state before). Its reward shows on the colonization entry's reward hover, the first's and the later one's. A second lunar colony fires no `.6`. Check the innovation cost hover: the founding reposts no cost.
3. **Begin Deep Space for a lunar-only holder.** Under Races Only, a country with the Mars Landing and Space Colonization researched that holds only lunar worlds at stage 3 is offered Begin Deep Space Exploration; one holding a colony beyond the Moon is not, and colonizes on Solar Colonization. Under Simple or Full, with every world of stages 1 and 2 claimed and a lunar world still free, the same country is offered it too (a free lunar world needs no Deep Space). And under Races Only past stage 2 with a lunar world free, a country without Deep Space that takes Begin Solar Colonization sees its entry open and found on the Moon (review I1).
4. **An old save's Moon Bases.** Load a save from before this build in which one country finished the Moon Base first as a scientific outpost, a second later as an industrial facility, a third with no purpose chosen, and a fourth has it open with progress. After the first month: the first holds Daedalus Crater (Daedalus Radio Telescope), the second Mare Imbrium (Imbrium Mass Driver), the third Tranquility Base (Tranquility Heritage Site); a military installation would hold Marius Hills (Marius Hills Hardened Installation). A world already taken gives way to the first free lunar world in table order. Each player among them gets The Moon Base Becomes a Colony (`.109`) naming its world, once even when item 5's notice applies too (one `.109` with both texts); no colony event (`.35` to `.40`) and no `.6` plays, and each keeps its Moon Base reward. `debug.log`: `TE_SELF_CHECK OK lunar_migration migrated=3`. The fourth's Moon Base leaves the journal and the carry line logs its progress; once its colonization runs, its next month's launch step adds that much to the bar (at most 300), and its cost hover shows one colonization cost, not two.
5. **An all-claimed old save keeps everything; the Moon by choice.** Load a save from before build 2a (34 worlds, all claimed) with a player holding Interplanetary Trade Networks and drawing Commercial Space Industry, and an AI that never colonized but runs the Interstellar Mission. After the first month: nothing is removed (the player keeps both, and its colonization reads finished), and it gets The Moon Is Open (`.109`), naming the decision. No program starts on its own: the AI's entry stays closed and its dividend stays (the entry's `possible` names the choice). Resume Solar System Colonization shows in the decisions panel; take it: the colonization bar, funding stepper, approach buttons and Target work again, the innovation cost hover bills the program, and Commercial Space Industry is gone the next month while it runs. Under Simple or Full the stage reads the Moon (build 2a's item 9); under Races Only it stays at 5 and the draw takes the lunar worlds as released ones (build 2a's item 3). Once all six lunar worlds are claimed the program stops within a month: Interplanetary Trade Networks is still there once, not twice, and Commercial Space Industry returns. An AI that takes Resume (it weighs it 100 while it takes part in the race, out of default and with a positive fixed income) loses its dividend while it runs: note how many do. Then switch a finished player to the Moon Mission: Begin Solar Colonization shows in place of Resume, and taking it runs the bar the same month (review R1). In a game whose race isn't over, the entry's `possible` hover shows no choice line: it sits in a `trigger_if` on `sr_race_over_moon_free`, and the hiding is unseen in game so far.
6. **The Purpose of the Base left open.** In an old save with that event (`.82`) waiting, it shows one option, Settle the Moon instead., and changes nothing. The country's Moon Base was running, so its progress is carried as item 4's fourth country's is.
7. **The console.** `event te_debug_space_race.8`: option b on a country with no lunar world gives it Daedalus Crater (or the next free world) next month, with `.109`; option c on a country running colonization logs `OK lunar_migration carried=120` next month, again on a rerun (it clears the carry's records), and its next launch month adds 120.

## Lunar colonization, build 3b: the Moon under fire at Earth (2026-10-29)

Design § 8 of `docs/superpowers/specs/2026-10-29-lunar-colonization-design.md`, Full Colonies only: Close in at Earth on a lunar world, its blockade while the holder's Earth is blockaded, no interdiction at Earth, and the AI's lunar offence. Before this build no lunar world could be blockaded: the generic blockade step needs an enemy standing off, and nobody stands off at Earth. No new self-check: everything here is script arithmetic on records the console logs (`event te_debug_space_race.6`, option a; `TE_SR_COMBAT` lines for seizures and destructions). A setup: two countries at war, one holding a lunar colony (found one with `event te_debug_space_race.2` or `.3`), the other with a fleet at Earth (option b) with assault carriers.

1. **The Earth posture options.** As the attacker, at war with a lunar colony's holder: the fleet row at Earth shows the posture and target buttons, and only then (at peace, or with no hostile lunar colony, they are hidden). The posture button steps Station → Close in → Station; its hover is the Earth text; the target button steps through the hostile lunar colonies only. A free lunar colony is offered too, and closing in on it costs its 10 infamy once.
2. **Close in, then seize.** Close in on the enemy's lunar colony: its Defenses fire on our fleet (losses in the battle report), and every enemy fleet at Earth, its Orbital Battlestation and its batteries fire on it too. Integrity falls (to skip the wait, option h from the holder's seat sets its first colony's integrity to 0). With the holder's fleets and battlestation gone from Earth and more marines than its garrison and militia, the colony is occupied the next month (`.102` to both sides) and goes back at the peace. While a fleet of the holder is stationed at Earth, or its battlestation stands, nothing is seized.
3. **Close in, then destroy.** Toggle Destroy on a closing-in fleet: three months with more fire than the colony's Defenses, and no enemy fleet stationed at Earth, destroy it (`.103`, 20 infamy, ruined for 25 years). A fleet that can no longer close in (peace, the colony taken) goes back to Station, not Stand off.
4. **The lunar blockade.** As the holder, with no fleet of ours at Earth and an enemy fleet there (option o): Earth's Locations row reads Earth Blockaded, and from the next month our lunar colonies read Blockaded in the Defenses view, their settlers and module shipments stop, their shipping specializations (Shackleton's Propellant Depot, Peary's Solar Power, Tranquility Base's two, Imbrium's two) give nothing, their Extraplanetary Base room drops out, and research ones keep running. Holding Shackleton with its depot, this is also the `propellant_depots_bool` self-check's blockaded path (build 2a's table above): the premium lines in Next Windows go, and the line should read OK once a blockaded holder read the boolean no. Launch the reserve: the blockade of Earth and of the Moon lifts together the month after. Our battlestation and batteries fire but don't lift it.
5. **No interdiction at Earth.** At peace with a lunar colony's holder, a fleet at Earth shows no posture or target buttons, and the posture button anywhere else still offers Interdict only where a non-ally holds a colony.
6. **The AI's lunar offence.** As a lunar holder at war with an AI fleet power, with no fleet of ours at Earth (option o gives the AI one): within a month or two the AI's strongest fleet at Earth closes in on our lunar colony with the most people and modules, if its marines outnumber our garrison and militia (otherwise it stays stationed), and never toggles Destroy. Launch the reserve: with a fleet of ours at Earth the AI's fleet goes back to Station the next month. With two enemies at war with the AI, one of them with a fleet at Earth, the AI doesn't close in on the other's lunar colony (it couldn't seize it). In an observer run, note whether AI wars produce lunar occupations at all.
7. **Orbital Superiority while closing in.** At war, with our fleets at Earth outmatching the enemy's, the Orbital Superiority modifier keeps its strength when one of those fleets closes in on a lunar colony.
8. **The AI's Moon while its fleets are away.** In an observer run or at war with an AI that holds a lunar colony: when its offence or defence has sent every fleet of its own away from Earth, and an enemy fleet reaches Earth, does it lose the Moon? Its defence has no Earth arm (it never comes home for a lunar colony), and only Auto's reserve or its reserve rule puts a fleet back up. Record how often an AI loses a lunar colony this way; an Earth arm in its defence is the fix if it does.
9. **A free lunar colony's price.** At peace, with a free colony on the Moon: the home fleet's Target button picks it for nothing (its hover has no price line). Stepping the posture to Close in then shows the price in the posture hover and charges it once; while closing in, the Target hover's last line names the price, and stepping to another free colony charges it again.

## Lunar colonization, build 3a: Nuclear Thermal Propulsion's premium (2026-10-29)

Design § 9 of `docs/superpowers/specs/2026-10-29-lunar-colonization-design.md`: a second off-window premium curve, the same extra delta-v at 9 km/s, which a country with Nuclear Thermal Propulsion pays (`sr_window_premium_country_<body>`). No new self-check: `window_gate_paid` (`docs/testing/global-commons-playtest.md`) now logs the country's own premium, cached and by date, so an NTP launch that reads the chemical curve shows as a mismatch or a `spent` above goal × (1 + the NTP figure). Reference: `docs/engine/launch_windows_report.md`, the NTP columns.

1. **The tooltip.** Nuclear Thermal Propulsion shows "Smaller Premium for Off-Window Launches" under its funding cap line, with its explanation on hover, and its description ends on the smaller premium.
2. **An NTP country's off-window cost.** For a country running Solar System Colonization, research Asteroid Mining and Nuclear Thermal Propulsion from the console. The month after a Mars window closes (offset +2; the windows are in the global commons list's Reference line), Mission Control's Next Windows reads Mars at about +16%, where a country with Asteroid Mining alone reads about +43%; the month after, about +46% against +150%. Its "costs N months" is goal × that ÷ pace. `event te_debug_launch_windows.1` option b: the `TE_LAUNCH_WINDOWS mars` line's `premium` and `premium_by_date` are both the NTP figure, and `our_cost` is it too while the approach would launch.
3. **Cheaper, not possible.** A country with Nuclear Thermal Propulsion but not Asteroid Mining still waits for windows: Next Windows reads "In N months" with no premium.
4. **The launch.** Under Standard at a fast pace, the NTP country launches off-window in more months than the chemical one (the report's off-window rule on Mars, NTP columns), and its first such launch logs `TE_SELF_CHECK OK window_gate_paid` with `premium_cached` = `premium_date` = the NTP figure.

## Colony management (2026-10-30)

Design: `docs/superpowers/specs/2026-10-30-colony-management-design.md` (the owner's play-test notes on the Colonies section). Simple and Full Colonies. No new self-check: the one engine fact the build leans on, a `unit_` field in a modifier on a journal entry reaching the army, is what vanilla's `modifiers_while_active` already do (the Caucasus war entries' `unit_offense_*`), and item 6 looks at it. Grep `debug.log` for `TE_SR_MODULES` for a colony's own builds.

1. **Drift colors.** In the Autonomy view a colony whose autonomy is rising shows its drift in red, one falling in green; the hover's terms the same way, and its last line says where the colony settles.
2. **Settling.** A colony with a hover reading "settles near 30%" moves toward 30 from either side over the following years, and a chartered colony settles near 0 instead of drifting back up.
3. **Next Windows.** On chemical rockets, with stage-4 and stage-5 worlds unclaimed and targetable: the Uranus, Neptune and Kuiper Belt rows are absent, and the line under the table counts them. Each row's transit matches `docs/engine/launch_windows_report.md` for the month; with a fusion drive the Window column reads Any month, and with Asteroid Mining a closed window reads the premium and the months. The Staged in Orbit hover lists the same destinations.
4. **Slots and the price past them.** Queue modules at a 2-slot colony until its Slots reads 3/2 (red): the hover's next price reads 300; the module past the slots leaves fabrication's stock 200 lower when it is built, the next 300 lower. Five past the slots, the + buttons grey out with the room line crossed. With Advanced Nanofabrication the colony reads one more slot.
5. **Facilities.** Build one of each at a fully crewed colony: the entry shows Off-World Research Stations, Cultural Centers, Resorts, Black Sites, Training Grounds and Materials Foundries at multiplier 1; the colony's Bases rises by 10 with a Mining Complex; Module Fabrication's rate rises by 4 with an Orbital Yard (and Space Command's month by 0.5 under Full Colonies); the nuclear Command Reliability target rises by 4 with a Nuclear Command Center; the colony's drift hover shows −0.15 for its Administration. Blockade the colony: the Mining Complex, Yard, Resort and Foundry stop, the rest keep running.
6. **The Training Ground reaches the army.** With Off-World Training Grounds on the entry, a battalion's experience gain in the military panel's breakdown includes it. If it doesn't, move `sr_module_train` from the entry to the country, refreshed and removed by `sr_mod_refresh_facilities`.
7. **A colony's own modules.** A colony at autonomy 50 with 30,000 people shows Building climbing by 1.5 a month; at 100% it gains a module (`TE_SR_MODULES <key> built a module of its own`), Building restarts at 0, and a specialization level shows in its modifiers at once. A colony with no slot or specialization level left holds at 100%.
8. **A colony's page.** Click a colony's name: only that colony shows, with People, Modules, Autonomy and (Full) Defenses one under another, each with its heads; Back returns to the list, and so does any view button. Every button on the page works as it does in the list.
9. **The AI.** In an observer run, an AI outside the top three that holds a colony sets Emigration to Steady with a positive income, queues a module a year, and answers a self-government demand with a charter; it lets a colony go only after losing its Space Program. Cede Colony: asking an AI for its empty lunar outpost shows about −60 for the colony in the acceptance breakdown, and for a large built-up colony −200.
