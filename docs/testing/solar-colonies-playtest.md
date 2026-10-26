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

1. **The rule.** The setup screen's Space Race rule offers Full Colonies, Simple Colonies, Races Only (the default) and
   Disabled. Under each of the first three every space race entry appears as before; under Disabled none does.
2. **The designer.** Under Simple Colonies, open a treaty with a country that holds a colony: Cede Colony lists that
   country's colonies by name and icon ("Valles Marineris Colony"), and only those. The list, the picked colony under
   it, the draft row and the signed treaty's row are the mod's own widgets (vanilla shows a building type only for a
   company monopoly): check each shows the colony's name and icon. Under Races Only the article does not appear.
3. **The building types appear nowhere else**: not in the build menu, the production overview, the encyclopedia, a
   company's or an industry charter's list. If one does, note where.
4. **A sale.** Cede one of our colonies for a Money Transfer to an AI great power: it accepts when the money is large
   enough, the colony moves on ratification, both sides get "A Colony Changes Hands", and the receiver's Our Colonies
   and Solar System list show it.
5. **A swap**: one colony each way in one treaty moves both.
6. **A war goal.** In a diplomatic play against a colony holder, add Cede Colony as a war goal (maneuvers 5, infamy
   10). Enforced in the peace, the colony moves.
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
   starting on No Module Fabrication. Orbital Assembly (Directed Energy Weapons) shows +5 Colony Module Fabrication per
   Month, and the Colony Modules section's first row reads 5.0 at full staff.
2. **Queueing.** Each colony we hold has a row: its Crew share, then the first and second specialization, Habitat,
   Port and Def. A level's tooltip names what it gives. + adds one to the end of the queue ("+1" beside the level, and
   a new last line in the Queue list with the world and the module); the button greys out at four specialization
   levels, the colony's slots or 20 entries, counting what is queued. A queue line's button removes it and the lines
   below move up; a row's clear button removes all of that colony's lines. Fabrication builds the top line first.
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
| `TE_SELF_CHECK OK/BROKEN colony_evacuation before=… after=… sent=…` | once a game, the first time a player brings a colony's people home (Abandon, then Bring them home) | `create_pop` with the capital's largest pop's culture and religion made the evacuees in the capital: it grew by at least 90% of them | it grew less: `create_pop` made fewer or none at run time, or `state_population` reads the change only later | if the state grows a month later, nothing to do; if `create_pop` fails, the evacuees are lost, as a release always lost them: drop the batches and say so in Bring them home's tooltip |

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
   and logs `colony_evacuation`; the capital's population rises by the colony's people, in whole thousands. Leave them
   to govern themselves makes it Free, with our ties at 50. An outpost of fewer than 1,000 people offers only Close
   the outpost.
5. **Free colonies.** Supply a free colony: the entry shows Free Colony Supply (+3% Space Program throughput) and Free
   Colony Trade, the colony's people grow again, and our ties climb 2 a month. At 100 (option g, then a month) "<World>
   Asks to Join Us": welcome it and it is ours again at autonomy 20, with its people and modules.
6. **A dead holder.** `annex <TAG>` an AI holder whose capital region nobody can take a colony for: a world with 1,000
   people or more reads Free, not Unclaimed.
7. **Colony life.** A colony that reaches 2,000 people gets "The First Child of <World>"; strikes and dome breaches
   come at random at colonies of 10,000 and 5,000 people. A dome breach names the people lost, and Settlers shows the
   colony smaller.
8. **The AI.** In an observer run, AI space powers answer the demand with charters, supply up to two free colonies,
   and welcome a colony that asks to join.
9. **Covert operations.** Incite Colonial Autonomy and Sabotage Colony appear in the diplomatic actions against a
   country holding a colony under Simple Colonies, and not under Races Only; once established, the target's colonies'
   autonomy climbs (Incite) or its largest colony loses people (Sabotage).
10. **Old saves.** A save from before this change keeps its Space Race setting; its colonies start at autonomy 0.
