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
| `TE_SELF_CHECK OK/BROKEN site_receiver_entry: …` | once a game, 70 days after a country without the Moon Base and Mars Landing received a colony | it holds Solar System Colonization and the colony | it has no entry (the engine did not activate its inactive copy, or `add_journal_entry` failed for one with no record; the add skips a copy since #1416) or lost the colony | put a received colony's modifiers on the country instead of the entry for a country that cannot hold the entry (the entry's declarations would need a country copy) |

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
| `TE_SELF_CHECK OK/BROKEN emigration_batch before=… after=… sent=…` | once a game, the first month a country sends settlers | the states taken from lost at least 90% of what was sent between them (colony people design § 6.3: every state gives in proportion to its people) | they lost less: the strata filter removed fewer people than asked, or `state_population` reads the change only on the next tick, as it does after `kill_population_percent_in_state` (scripting_best_practices § "`state_population` Doesn't Fall Until the Next Tick"); then read a state's people a month on | if the states' people fall by the batches |

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
9. **Crews and AGI.** Crews read one per 5,000 people; with Artificial General Intelligence they read AGI. *Superseded by § Colony people limit modules (#1954 Part B).*
10. **The AI's settlers.** In an observer run under Simple Colonies, a top-three space power holding colonies sets
    Emigration to Steady within a year; its colonies' people grow. *Superseded by § Colony people limit modules (#1954 Part B).*

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
| `TE_SELF_CHECK OK/BROKEN ebase_mix country=… read=… want=… buildings=…` | once a game, the month after a country under Simple or Full Colonies first has an Extraplanetary Base with a Tech-Critical Metals mix of 1.5% or more either way (ground types design § 5.3), read before that month's refresh strips anything, on a mix at least two days old; a month later again while some base buildings match and some don't (one no refresh has reached yet) | every base building's `modifier:goods_output_tech_metals_mult` is the base's mix, `var:sr_ebase_mix_tech_metals` / 100 (`want`), within 0.001 (OK: `buildings` counts them; BROKEN: none matches, `buildings` counts them, `read` is one's figure): `sr_ebase_mix_tech_metals_bonus` / `_penalty`, added to the building at `multiplier = root.var:sr_ebase_mix_tech_metals_units`, reach its output | `read` 0: the unit modifiers never reach the building (`add_modifier` on a building, or the multiplier through `root.var:`); another figure: the multiplier or another line is off | for 0, apply the mix as `goods_output_<good>_mult` on the base's state instead (it reaches only the state's producers of the good), or set the multiplier from a local read in country scope; for another figure, read the building's output tooltip |

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
5. **Upkeep.** Superseded by § The colonies' costs as Launch Capacity (2026-11-25): Colony Modules is on the Space
   Program building, as Launch Capacity input, not on the entry as throughput.
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
10. **Discovery boons** (2026-11-25; `docs/systems/space_race_discoveries.md` § "Choice rewards: site boons"). Under Full Colonies, holding Titan with one staffed Research Station and one staffed Materials Foundry, fire `space_race_discovery_events.4` from the console (`event space_race_discovery_events.4` after giving the country `sr_discovery_titan_chemistry_pending`): each option's tooltip reads "+100% to ... at Titan. It belongs to the colony, whoever holds it." with the module's name and Titan spliced, and no modifier line. Take the second: within a month the entry's Materials Foundry line doubles (one level reads as two), and Titan's page shows "An Impact-Born Chemical Laboratory: +100%" under Materials Foundry, its hover the option's tooltip, and nothing under Research Station. Cede Titan: the new holder's page shows the line and its Foundry line doubles. Under Races Only the same option's tooltip shows its old modifier (+2% advanced materials output) and the entry holds it. A boosted Habitat (Olympus Mons, second option) shows twice the Habitat share in its hover and twice the room in Settlers.

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
5. **Free colonies.** Supply a free colony: the Space Program's Launch Capacity input shows Free Colony Supply (300 Launch
   Capacity a week; § The colonies' costs as Launch Capacity) and the entry Free Colony Trade, the colony's people grow again, and our ties climb 2 a month. At 100 (option g, then a month) "<World>
   Asks to Join Us": welcome it and it is ours again at autonomy 20, with its people and modules.
6. **A dead holder.** `annex <TAG>` an AI holder whose capital region nobody can take a colony for: a world with 1,000
   people or more reads Free, not Unclaimed.
7. **Colony life.** Our first colony to reach 5,000 people gets "The First Child of <World>", three years after our
   first colony reached 1,000 at the soonest, and no later colony does. Strikes and dome breaches come rarely, at colonies of 10,000 and 5,000 people, and never within ten years of
   the last one (`sr_life_cooldown`). A dome breach names the people lost, and Settlers shows the colony smaller.
8. **The AI.** In an observer run, AI space powers answer the demand with charters, supply up to two free colonies,
   and welcome a colony that asks to join.
9. **Covert operations.** Incite Colonial Autonomy and Sabotage Colony appear in the diplomatic actions against a
   country holding a colony under Simple Colonies, and not under Races Only; once established, the target's colonies'
   autonomy climbs (Incite) or its largest colony loses people (Sabotage).
10. **Old saves.** A save from before this change keeps its Space Race setting; its colonies start at autonomy 0.
11. **Revoking a charter** (owner, 2026-11-23). Grant a colony of 1,000 people or more a charter (option b, then the
    demand), then open its page: Revoke shows beside Abandon while the Status tile reads Charter (or Both), and not
    otherwise; a colony we hold occupied greys it out. Revoke asks first ("Revoke the Charter of <World>?", the world
    named, the budget-hearing picture). Keep it changes nothing. Revoke it: the Status tile reads Ruled (or Garrison),
    the world's specialization line in the entry's modifiers goes back to its full size, its autonomy reads 99, every
    other colony of ours with 1,000 people or more is 10 higher, `debug.log` has `TE_SR_AUTONOMY <world>: charter
    revoked, autonomy 99.0`, and the next month brings no "<World> Demands Self-Government" (the five-year cooldown
    started again). A colony of ours that was at 90 or more reads Free the next month.
12. **A push to 100 frees a colony** (2026-11-23). With option b on a colony below 100, run Incite Colonial Autonomy
    against its holder at full priority, or revoke a second charter while one colony stands at 99: the colony reads
    Free the month after it reaches 100, though the month's settling would have taken it back to 99.

## Fleets, Space Command, combat and seizure (slice 6, parts 6a and 6b)

Design: `docs/superpowers/archive/specs/2026-10-26-solar-colonization-fleets-design.md` (§ 22 records what was built and where
it departs). Everything here needs the Space Race rule at Full Colonies; under Simple Colonies and Races Only none of
it shows. The console is `event te_debug_space_race.6` (log our fleets and every location's forces; 100 strength of
each role at Earth; land our fleets now; fill propellant and supply; our fleets' drive one up; our first colony's
integrity to 0; this month's combat now; occupy our first colony by our strongest enemy, or return it; start an
interdiction; fill the reserve; an enemy fleet at Earth). Grep `debug.log` for `TE_SELF_CHECK`, then `TE_SR_FLEET`, `TE_SR_LOC` and `TE_SR_COMBAT`.

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN ship_construction country=… rate=…` | once a game, a month after a Space Command first runs at half staff or more in a state its owner controls | `sr_sc_rate`, the sum of `modifier:state_sr_ship_construction_add` over the states its owner controls, reads above 0: a production method's workforce-scaled `state_modifiers` reach the state | it reads 0 | compute the rate in script, level × occupancy × the method's rate by `has_active_production_method`, and state the rates in the methods' descriptions |
| `TE_SELF_CHECK OK/BROKEN fleet_upkeep_line country=… units=… robotics_mult=… telephones_mult=… software_mult=… want=…` | once a game, the month after a Space Command first carries the upkeep with units above 0 (Space Race UI pass design § 10) | the building's Robotics, Wired Telecommunication Gear and Software input multipliers are each 9 × its units: the newly registered mults reach the building (that they multiply the unscaled line is item 2's tooltip read) | one reads 0 (unregistered, or not on the building) or another figure (other lines reach that input) | for 0, check the `goods_input_<good>_mult` with `/modifier-search`; for another figure, read the building's input tooltip and compare the six goods' lines |
| `TE_SELF_CHECK OK/BROKEN fleet_leg location=… drive=… leg=… flown=…` | OK once a game, on the first fleet that lands on an 8th, 15th or 22nd having flown its whole leg (never an old save's converted fleet or the console's landing); BROKEN once, if any fleet lands four ticks (a month) or more late. A dead mid-month clock leaves fleets at most three ticks late, so only `fleet_clock` shows the mid-month ticks run | `flown` equals `leg`, in ticks of the fleets' clock (four a month): the quarters `docs/engine/launch_windows_report.md` gives that leg and drive | the clock missed an arrival | read `fleet_clock`; land fleets from the country pulse as well |
| `TE_SELF_CHECK OK/BROKEN fleet_clock last_quarter=…` | once a game each way, on a 1st when last month's clock was queued on a power (`sr_fl_clock_power`, the same country, not a revolution's winner) that lived through the month (2026-11-25 design § 1.6) | `last_quarter` is 3: the 22nd's hidden tick event (`space_race_events.120`-`.122`, queued with `days = 7/14/21` on one fleet power) fired; it is noted before the rules are read, so a rule switched off and on again doesn't count | the 22nd never ran on a power still alive | queue the three ticks on every fleet power (`sr_fl_clock_queue`); the guard in `sr_fl_tick_step` keeps each tick once |
| `TE_SELF_CHECK OK/BROKEN fleet_battle location=… steps=… ended=…` (OK) / `… fire=… strength=…` (BROKEN) | once a game each way (2026-11-25 design § 2.10) | a battle settled within its tick: a unit broke or was destroyed inside the ceiling of 60 steps (`sr_bt_max_steps`; an even fight takes about 14) | the ceiling was reached with units still paired whose fire is at least half their strength: the steps didn't settle a real fight | raise `sr_bt_k` (0.05) or `sr_bt_max_steps`; `test_space_fleet_battle.py` runs the loop in fixed point |
| `TE_SELF_CHECK OK/BROKEN xfer_step_scope … slot=… role=… [amount=…]` | once a game, the first − or + clicked in a fleet's Transfer popup | the step code, the third chained `AddScope` (`scope:step`, after `op` and `pick`), reached `sr_fleet_xfer_step_sgui`; `slot` is the fleet's slot, `role` the row's code (1 warships … 6 marines), `amount` the figure after the click | no step code matched: the third scope didn't arrive, and the amount didn't move. **No line at all** after a click means `op` or `pick` didn't arrive (no case of `sr_fl_by_op` or `sr_fl_xfer_step_at` matched) or the button never ran | for BROKEN, pass two scopes: `pick` = role × 100 + step code, decoded in `sr_fl_xfer_step_at`; for no line, check the button's `enabled` and the Into buttons, which use `op` and `pick` too |

**What checks itself, and what needs a hand.**

- **Logged with no input:** start a game at Full Colonies and grep `error.log` and `debug.log` for the new files
  (`sr_fleet*`, `sr_fleets_generated*`, `space_race_events.txt`, `covert_operations.txt`): script errors in them show at
  load. `ship_construction` logs by itself once any country has run a Space Command at half staff for a month: an AI
  space power in an observer run, or you. Its first form fired on 2026-10-31 and printed nothing (its `rate=` read
  `THIS.MakeScope.ScriptValue`, which `debug_log` drops the line for); the fixed line's marker is
  `sr_sc_checked_v2`, so a save that already ran the old one checks again.
- **Logged after one action:**
  - `fleet_leg` logs on the first fleet that lands, so send one (AI fleets seldom leave Earth outside a war).
  - `fleet_clock` logs on the second 1st after the first fleet power appears: any Full Colonies game with a Space Command.
  - `fleet_battle` logs on the first battle: console options o and b at Earth, then i.
    **Seen OK 2026-11-25** (harness session on a copy of the owner's June 2043 save, build `1e902f0d4` as a side
    mod): a setup put 100 warships of Aceh and 50 of the Aceh White Army, at war, at Mars and ran `sr_battle_at`.
    `TE_SELF_CHECK OK fleet_battle location=3 steps=11 ended=1`; the White Army broke at 23.96 and stayed (no dock in
    reach), Aceh kept 89.57; neither AI switched to Avoid (no Space Command). The same fleets placed without a battle
    were fought by the July 1 monthly step with the same figures, and the July 7 hidden tick advanced
    `sr_fl_tick_now` to month × 4 + 1. Not seen: the pace escape and an AI with a Space Command choosing Avoid, a
    player's Engage / Avoid button, a broken fleet's retreat to a dock, the batteries' weekly fire.
  - `TE_SR_FLEET` and `TE_SR_LOC` are console option a's.
  - `TE_SR_COMBAT` lines log every occupation, liberation, seizure and destruction as it happens.
- **Set up by hand and read by eye:** steps 1 to 22 below. Console option b gives a fleet, h and i force an assault
  and a month's combat, and j an occupation, which shortens most of them.

1. **The rule.** Under Simple Colonies, no Space Command building, no Space Command, Fleets or Colony Defences
   sections, no Survey Colony Defences operation, and `.94`'s Send a garrison works as slice 5 built it. Switch to Full.
2. **Space Command.** Research Space Militarization: Space Command can be built by the government, and only in a state
   with a Space Program. Its four methods (Orbital Shipyards, Fusion Yards, Torch Yards, Antimatter Yards) each show
   "Fleet Strength Built a Month" scaled by staffing. Staffed, the panel's Space Command section reads the strength
   built last month and the levels; the home fleet appears at Earth in Fleets; `ship_construction` logs OK.
3. **The build mix.** Each role's button steps 0, 1, 2, 3, 0; the next month's construction follows the weights
   (option a's per-role figures, or the strength hover).
4. **Upkeep.** As the fleets grow, Space Command's input tooltip shows Fleet Upkeep on its six maintenance goods,
   +900% for every 10 strength at full, and the section's Upkeep figure matches (the UI pass section, PR 7, has the
   detail). The methods' other inputs don't change.
5. **Orders.** Pick a destination in the Fleet Destination popup (its rows give each trip's weeks and propellant;
   the PR 3 section below), then Go: Go is disabled with the reason when the leg can't leave or the propellant is short (a chemical fleet
   at Earth outside Mars's window, for instance). In transit the card reads "Lands in N weeks"; on landing
   `fleet_leg` logs OK and the ticks flown match the quarters `docs/engine/launch_windows_report.md` gives.
   **The clock (2026-11-25 design § 1).** Send a torch or antimatter fleet on the 3rd of a month: its weeks count down
   by one on the 8th, 15th, 22nd and 1st, and it lands on the tick the popup's weeks said, counted from the 1st it was
   sent after (not a whole month later). Two fleets of different drives sent to the same place on the same day land on
   different ticks.
6. **Docking and refits.** A fleet back at Earth refills propellant and supply, repairs 20% of its damage a month, and
   refits to a newer drive (Refit shows three months). A fleet at our colony with a Spaceport repairs 10% a level, and
   refills propellant by 25% a month only on a world that makes it (Utopia Planitia, Ceres, Europa, Ganymede, Callisto,
   Titan, Enceladus, Rhea, Triton, Pluto). Away from a dock, supply counts down; at zero the fleet loses 5% a month.
7. **Transfer, marines.** Move all of one fleet into another at its location, then part of one into a new fleet, in
   the Transfer popup (the PR 4 section below, which took in Merge and Detach). At Earth the
   carriers fill with marines (2 battalions a point of carrier strength); Land opens a list of our colonies there and
   its Land puts them at the one picked (Colony Defences shows them), Embark takes them back.
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
12. **Battles (2026-11-25 design § 2).** Console option o (the strongest enemy puts a fleet at Earth) and b
    (100 strength of each role at Earth), then option i (a week's battles): the battle settles at once, not over
    months. Both fleets lose by the square law until one has lost half of what it brought and breaks; one that
    breaks flies to the nearest dock other than where it is (Earth, or a Spaceport of its owner's): broken at
    Earth with a Spaceport in reach it leaves Earth, and with none it stays (2026-11-25 design § 5.2).
    "Battle Over <location>" reports our losses, theirs and what's left, at most once a week; the location's status
    reads Battle; screens (warships, rapid response) take the losses before carriers and tenders. At Earth, any
    Orbital Battlestation fights for its owner (25 strength a level), never breaks, and regains 10% a month; the
    batteries fire a quarter of their month's figure each week; a battle there adds debris (Orbit section).
    **Engage / Avoid.** Set a fleet to Avoid and send it to an enemy location held by a slower enemy fleet that
    engages: it lands on Station (not Stand off) and nobody fights; set it to Stand off and it is caught the next
    week (it blockades, so it is tied). Send it against a faster one: it is caught. Send it where the enemy holds a
    colony with a fleet set to Avoid: our fleet, if it engages, catches theirs (tied to its colony). The button shows
    on the card in flight and where the posture line does, and in the Fleets window always; without a Space Command
    it is grayed with the reason. An AI fleet sets its own: it avoids a fight it would lose by strength × fire.
    **Stances (§ 5.1).** The card's button reads the stance in force and a click sets the next (Avoid, Hit and Run,
    Engage, Fight to the Last); "Fight to the Last" fits the 168-wide button, and in flight "Lands in N weeks"
    still fits beside it with the track at 96. The Fleets window's page shows four buttons two to a line, the one in force lit. A Hit and Run fleet against
    an equal Engage one breaks at about 73 of 100 while the other holds; a Fight to the Last fleet never breaks
    (no retreat, destroyed if it loses). **Friends (§ 5.3).** Two AIs at war with one enemy, each weaker alone but
    stronger together, both engage. **Forecast (§ 5.4).** Fleet Destination has a Battle column (popup 884 wide):
    blank where no enemy is, else Clear win / Costly win / Defeat / Rout in green, yellow, gold, red; its hover gives
    ours with this fleet and theirs and the winner's loss. An enemy fleet bound for our colony (.100) or Earth
    (.111) adds Space Command's forecast to the alert, or "We have no fleet there" with none.
13. **Postures and blockade.** Stand off at an enemy's colony with no enemy fleet holding orbit: its row in their
    Colony Defences, and our Locations row, read Blockaded / Blockading; their settlers and modules stop arriving,
    a mining or shipping specialization's modifier goes to nothing while an observatory's keeps running, and its
    Extraplanetary Base room drops out.
14. **Assault and seizure.** Close in on an enemy's colony (the target button opens Fleet Target, the PR 3 section
    below; its hover gives the target's Defences as a range, exact with Survey Colony Defences): its Defences fire
    back and its integrity falls; at 0, with more marines than its garrison and militia, "<World> Occupied" to both
    sides. It gives its holder nothing, shows Occupied with the occupier's flag, and the war-support breakdown shows
    "Colonies occupied in space". At the peace it returns ("<World> Returned"), unless a Cede Colony article took it.
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
   defensive pact), holds a colony: the Interdict posture button can be clicked, and its hover names the price (the
   posture buttons are in the PR 3 section below). Where only allies or enemies hold colonies, Interdict is greyed.
   While interdicting, Fleet Target lets us target only the worlds of countries we may interdict.
2. **The price.** Entering Interdict: our infamy +5, our UN record's "Hostile acts in space" +10, once for that fleet
   and that country (targeting another country's world pays again; staying put pays nothing more).
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
   0 and the home fleet grows each month, as before (Auto-launch: On). Switch Auto-launch off: the Reserve grows a month at a time,
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

1. **The overview cells (`te_banking_ov_cell`, hovers through `sr_colony_overview_sgui`'s `ExecuteTooltip`: new).** Under Simple Colonies: Colonies reads Loyal with "N of 34 held"; push a colony to autonomy 50 (`event te_debug_space_race.2` or wait) and it reads the colony's name in red, "wants self-rule", then "+N more want it" with a second; its hover lists them by name. Modules reads "N queued", or Queue empty (red once the fabrication stock is full). Next Window reads "in N months", "Open now", "Any month" with a torch drive, or "No site left". Under Full Colonies a Defense cell joins them: Calm, then, with an enemy fleet standing off a colony, Blockaded and the colony's name, its hover listing every threatened colony and an inbound hostile fleet's landing.
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
   bloc, or change the principle): the level stays and the figure reads "N / N−1 (+0.5)" at once. The pace follows
   within a few days, since the entry declares the bonus from the live cap (#1404, which retired the monthly
   recalculation through `sr_cost_funding_cap`): that entry's Funding Progress Bonus drops by 0.25 (the top level now
   counts as half a level). The other way, research a cap technology while funded at 9 with a cap of 7: "9 / 7 (+0.8)"
   reads "9 / 8 (+0.5)" at once, and within a week the bonus rises from +3.92 to +4.25. For those days the pace
   hover's Funding line (live values) and its "Added each month" breakdown (the modifier) can disagree by that much;
   after them they agree. If they still disagree a week later, the declaration isn't reading the cap.
6. **The AI.** In an observer run, no AI's stepper shows "(+…)": the AI stops at the cap. One left past it by a falling
   cap funds down to the cap within a few weeks.
7. **An old save.** Retired with #1404: vanilla 1.15 loads no save from before the split (#1407), and each entry
   declares both modifiers. The old-save strip went too (#1429); nothing to check.

## Lunar colonization, build 1: technologies and the era-10 base (2026-10-29)

The first build of `docs/superpowers/specs/2026-10-29-lunar-colonization-design.md` (§§ 5, 6): three technologies, the colonization method and Orbital Assembly on Cislunar Infrastructure, the Extraplanetary Base on In-Situ Resource Utilization with Regolith Processing. Colonization still needs the Moon Base and the Mars Landing until the second build. No self-check: the one engine question (item 6) shows in the game's own behaviour.

1. **The tree.** Cislunar Infrastructure (era 10, military) follows Reusable Rocketry; In-Situ Resource Utilization (era 10, military) follows Reusable Rocketry; Nuclear Thermal Propulsion (era 11, military) follows Cislunar Infrastructure; Asteroid Mining now follows In-Situ Resource Utilization and Directed Energy Weapons. Each shows its space race funding cap line (+2, +1, +1) and a placeholder icon (Reusable Rocketry's, Asteroid Mining's, Fusion Power's).
2. **The method.** With Cislunar Infrastructure, the Space Program's Solar Colonization method and Module Fabrication's Orbital Assembly unlock; Solar Colonization reads 10,000 Launch Capacity a week at full staff. Begin Solar Colonization shows with Cislunar Infrastructure and is still possible only after the Moon Base and the Mars Landing.
3. **Switching early by hand.** Before the Moon Base and the Mars Landing, switch the method in the building panel: the bill rises from 5,000 to 10,000, the Moon Base and the Mars Landing keep running (the method carries the Mars Mission's), and Solar System Colonization does not start. This is the intended intermediate state (a method has no `possible`), not a bug. Watch an AI too: the method group picks the most productive method, so an AI with Cislunar Infrastructure and no Moon Base may switch on its own and pay 10,000 a week for nothing. The second build ends this, since the method then opens colonization itself.
4. **The cost factor.** Solar System Colonization's Space Program Cost reads ×8 for a country with the Mars Landing (15 innovation × 8 a funding level); a country holding a colony by treaty without the Mars Landing pays ×5, and its cost re-posts when its Mars Landing completes.
5. **The era-10 base.** With In-Situ Resource Utilization, an Extraplanetary Base can be built and starts on Regolith Processing (15 Electronic Components, 15 Wireless Telecommunication Gear, 5 Digital Access and 60 Launch Capacity for 175 Structural Metals, 95 Tech-Critical Metals and 50 Glass and Plastics a level); the Asteroid Mine method waits for Asteroid Mining. Under Simple or Full Colonies, the Modules view reads room 0 until Asteroid Mining or a colony, and a level built then works at −75%; Asteroid Mining adds the near-Earth 10. AI governments and private investors don't build a base with no room.
6. **Retired at vanilla 1.15** (the repair went with the migration; saves from 1.14.5 don't carry over). ~~**An old save (`te_repair_lunar_technologies`).** Load a save from before this build in which a country runs Solar Colonization or Orbital Assembly on Directed Energy Weapons, and one holds Asteroid Mining. In the first month, `debug.log` has a `TE_LUNAR_TECH_REPAIR` line for each, and they hold Cislunar Infrastructure and In-Situ Resource Utilization. Before that month ends, watch the colonizing country's Space Program: if the engine moved it off Solar Colonization at the load (its technology unresearched for a moment), its colonization entry fails (the program lost), and a colonizer with no colony yet loses its progress toward its first colony with the entry's `on_fail`. Fallback for that: switch back by hand after the first month (the AI through Begin Solar Colonization); nothing in script runs before the first monthly pulse.~~
7. **Orbital Foundries.** Space Colonization's fabrication method reads Orbital Foundries in the method group, the Colony Modules section's fabrication tooltip and the method's own description.
8. **Art (icon batch 7).** The three technologies show their own icons in the tree: Cislunar Infrastructure an orbital station with a lander docked, In-Situ Resource Utilization a tracked regolith processor, Nuclear Thermal Propulsion a reactor engine. None repeats Reusable Rocketry's, Asteroid Mining's or Fusion Power's.

## Lunar colonization, build 2a: six lunar worlds at stage 0 (2026-10-29)

The second build of `docs/superpowers/specs/2026-10-29-lunar-colonization-design.md` (§§ 3, 4, 8): the Moon's six worlds as stage 0 (Shackleton Crater, Peary Crater, Tranquility Base, Marius Hills, Daedalus Crater, Mare Imbrium), founded the month a fleet leaves, the Moon Landing site's discount and Shackleton's Propellant Depot. Colonization still needs the Moon Base and the Mars Landing, and the Moon Base still runs, until build 2b. The console is `event te_debug_space_race.2` and `.3` as above.

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK lunar_stage0_draw world=<key> …` | once a game, the first lunar world the Races Only draw founds | the stage-0 draw found the Moon in play and founded a lunar world the month the bar filled | `TE_SELF_CHECK BROKEN lunar_stage0_draw held=… best_cost=…` (once a game): under Races Only with no target, a full bar was held three months at stage 0 with a lunar world free, so the Moon is missing from `sr_launch_best_cost` or `sr_launch_ungated_departs` read false, and Mars stays locked for everyone | read `best_cost`: above 0, `sr_window_moon_in_play` is false (check its `sr_colonization_stage >= 0` arm); at 0, give the lunar draw branches no departs test at all |
| `TE_SELF_CHECK OK/BROKEN propellant_depots_bool …` | OK once a game, once a Shackleton holder read the boolean yes and a country that lost the world (ceded, released or taken by an heir) read no; BROKEN once, on a mismatch two months running (read every month for every country, so a holder whose programme has finished counts) | Shackleton's Propellant Depot on the colonization entry reaches the country as `modifier:country_sr_propellant_depots_bool`, and leaves it with the world. Its ×0-under-blockade case comes with build 3b's lunar blockade (its section below) | `record=yes boolean=no`: the INJECT of the entry's generated declarations (`common/journal_entries/sr_sites_generated.txt`, 1.15 scaling modifiers) didn't merge, or the entry's boolean doesn't reach the country; `record=no boolean=yes`: the boolean outlived the world | use `sr_depots_by_record = yes` in place of the modifier in `sr_launch_has_depots` (`sr_launch_window_triggers.txt`) |
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

Build 2b of `docs/superpowers/specs/2026-10-29-lunar-colonization-design.md` (§§ 4, 7): Solar System Colonization opens on the Moon Landing with Cislunar Infrastructure, and each world beyond the Moon needs the Mars Landing; a country's first lunar colony takes the Moon Base's place in the race; the Moon Base milestone is retired. Lunar blockades are build 3b's (its section below). Its old-save half (the migration, the carry, `.109` and the console's `event te_debug_space_race.8`) and the `lunar_migration` self-check went with vanilla 1.15, which loads no save from 1.14.x (#1407).

1. **The Moon on the Moon Landing.** In a new game, with the Moon Landing and Cislunar Infrastructure but not the Mars Landing: Begin Solar Colonization appears from the Moon Mission and is possible; the journal never shows a Moon Base. Colonization founds only lunar worlds, under Races Only too (the draw has no world beyond the Moon). Under Simple or Full, hover Target on a world of Mars: it is grayed with "The site is on the Moon, or we have completed the Mars Landing". Once the Moon is full, the bar fills and holds, and Next Window's third line reads "no Mars Landing" (design § 4: the panel says why). After the Mars Landing the button works, the line reads the stage again, and under Races Only stage 1 draws.
2. **The first lunar colony.** Found a lunar world: its colony event (`space_race_colony_events.35` to `.40`) fires, then Foothold on Another World (`space_race_events.6`) a day later, with one option and the Lunar Colony reward (First Lunar Colony for the race's first); other countries get the notice that we founded a colony on the Moon (`.20`), and the Program row's Lunar Colony icon lights, with the first mark for the race's first (no half-lit state before). Its reward shows on the colonization entry's reward hover, the first's and the later one's. A second lunar colony fires no `.6`. Check the innovation cost hover: the founding reposts no cost.
3. **Begin Deep Space for a lunar-only holder.** Under Races Only, a country with the Mars Landing and Space Colonization researched that holds only lunar worlds at stage 3 is offered Begin Deep Space Exploration; one holding a colony beyond the Moon is not, and colonizes on Solar Colonization. Under Simple or Full, with every world of stages 1 and 2 claimed and a lunar world still free, the same country is offered it too (a free lunar world needs no Deep Space). And under Races Only past stage 2 with a lunar world free, a country without Deep Space that takes Begin Solar Colonization sees its entry open and found on the Moon (review I1).
4. **Retired at vanilla 1.15** (the old-save half went with the migration; saves from 1.14.5 don't carry over). ~~**An old save's Moon Bases.** Load a save from before this build in which one country finished the Moon Base first as a scientific outpost, a second later as an industrial facility, a third with no purpose chosen, and a fourth has it open with progress. After the first month: the first holds Daedalus Crater (Daedalus Radio Telescope), the second Mare Imbrium (Imbrium Mass Driver), the third Tranquility Base (Tranquility Heritage Site); a military installation would hold Marius Hills (Marius Hills Hardened Installation). A world already taken gives way to the first free lunar world in table order. Each player among them gets The Moon Base Becomes a Colony (`.109`) naming its world, once even when item 5's notice applies too (one `.109` with both texts); no colony event (`.35` to `.40`) and no `.6` plays, and each keeps its Moon Base reward. `debug.log`: `TE_SELF_CHECK OK lunar_migration migrated=3`. The fourth's Moon Base leaves the journal and the carry line logs its progress; once its colonization runs, its next month's launch step adds that much to the bar (at most 300), and its cost hover shows one colonization cost, not two.~~
5. **A race over with the Moon free keeps everything; the Moon by choice.** In a game where every site has been claimed, with a player holding Interplanetary Trade Networks and drawing Commercial Space Industry and an AI that never colonized but runs the Interstellar Mission, free a lunar world again (a holder dead without an heir, or `event te_debug_space_race.2`'s release option on a country whose first colony is lunar). The next month: nothing is removed (the player keeps both, and its colonization reads finished). No program starts on its own: the AI's entry stays closed and its dividend stays (the entry's `possible` names the choice). Resume Solar System Colonization shows in the decisions panel; take it: the colonization bar, funding stepper, approach buttons and Target work again, the innovation cost hover bills the program, and Commercial Space Industry is gone the next month while it runs. Once the lunar world is claimed again the program stops within a month: Interplanetary Trade Networks is still there once, not twice, and Commercial Space Industry returns. An AI that takes Resume (it weighs it 100 while it takes part in the race, out of default and with a positive fixed income) loses its dividend while it runs: note how many do. Then switch a finished player to the Moon Mission: Begin Solar Colonization shows in place of Resume, and taking it runs the bar the same month (review R1). In a game whose race isn't over, the entry's `possible` hover shows no choice line: it sits in a `trigger_if` on `sr_race_over_moon_free`, and the hiding is unseen in game so far.
6. **Retired at vanilla 1.15** (the old-save half went with the migration; saves from 1.14.5 don't carry over). ~~**The Purpose of the Base left open.** In an old save with that event (`.82`) waiting, it shows one option, Settle the Moon instead., and changes nothing. The country's Moon Base was running, so its progress is carried as item 4's fourth country's is.~~
7. **Retired at vanilla 1.15** (the old-save half went with the migration; saves from 1.14.5 don't carry over). ~~**The console.** `event te_debug_space_race.8`: option b on a country with no lunar world gives it Daedalus Crater (or the next free world) next month, with `.109`; option c on a country running colonization logs `OK lunar_migration carried=120` next month, again on a rerun (it clears the carry's records), and its next launch month adds 120.~~

## Lunar colonization, build 3b: the Moon under fire at Earth (2026-10-29)

Design § 8 of `docs/superpowers/specs/2026-10-29-lunar-colonization-design.md`, Full Colonies only: Close in at Earth on a lunar world, its blockade while the holder's Earth is blockaded, no interdiction at Earth, and the AI's lunar offence. Before this build no lunar world could be blockaded: the generic blockade step needs an enemy standing off, and nobody stands off at Earth. No new self-check: everything here is script arithmetic on records the console logs (`event te_debug_space_race.6`, option a; `TE_SR_COMBAT` lines for seizures and destructions). A setup: two countries at war, one holding a lunar colony (found one with `event te_debug_space_race.2` or `.3`), the other with a fleet at Earth (option b) with assault carriers.

1. **The Earth posture options.** As the attacker, at war with a lunar colony's holder: the fleet row at Earth shows the posture and target buttons, and only then (at peace, or with no hostile lunar colony, they are hidden). The posture buttons offer Station and Close in only (Stand off and Interdict greyed, "not at Earth"), their hovers in the Earth text; Fleet Target lets us target the hostile lunar colonies only. A free lunar colony is offered too, and closing in on it costs its 10 infamy once.
2. **Close in, then seize.** Close in on the enemy's lunar colony: its Defenses fire on our fleet (losses in the battle report), and every enemy fleet at Earth, its Orbital Battlestation and its batteries fire on it too. Integrity falls (to skip the wait, option h from the holder's seat sets its first colony's integrity to 0). With the holder's fleets and battlestation gone from Earth and more marines than its garrison and militia, the colony is occupied the next month (`.102` to both sides) and goes back at the peace. While a fleet of the holder is stationed at Earth, or its battlestation stands, nothing is seized.
3. **Close in, then destroy.** Toggle Destroy on a closing-in fleet: three months with more fire than the colony's Defenses, and no enemy fleet stationed at Earth, destroy it (`.103`, 20 infamy, ruined for 25 years). A fleet that can no longer close in (peace, the colony taken) goes back to Station, not Stand off.
4. **The lunar blockade.** As the holder, with no fleet of ours at Earth and an enemy fleet there (option o): Earth's Locations row reads Earth Blockaded, and from the next month our lunar colonies read Blockaded in the Defenses view, their settlers and module shipments stop, their shipping specializations (Shackleton's Propellant Depot, Peary's Solar Power, Tranquility Base's two, Imbrium's two) give nothing, their Extraplanetary Base room drops out, and research ones keep running. Holding Shackleton with its depot, this is also the `propellant_depots_bool` self-check's blockaded path (build 2a's table above): the premium lines in Next Windows go, and the line should read OK once a blockaded holder read the boolean no. Launch the reserve: the blockade of Earth and of the Moon lifts together the month after. Our battlestation and batteries fire but don't lift it.
5. **No interdiction at Earth.** At peace with a lunar colony's holder, a fleet at Earth shows no posture or target buttons, and the posture buttons anywhere else still offer Interdict only where a non-ally holds a colony.
6. **The AI's lunar offence.** As a lunar holder at war with an AI fleet power, with no fleet of ours at Earth (option o gives the AI one): within a month or two the AI's strongest fleet at Earth closes in on our lunar colony with the most people and modules, if its marines outnumber our garrison and militia (otherwise it stays stationed), and never toggles Destroy. Launch the reserve: with a fleet of ours at Earth the AI's fleet goes back to Station the next month. With two enemies at war with the AI, one of them with a fleet at Earth, the AI doesn't close in on the other's lunar colony (it couldn't seize it). In an observer run, note whether AI wars produce lunar occupations at all.
7. **Orbital Superiority while closing in.** At war, with our fleets at Earth outmatching the enemy's, the Orbital Superiority modifier keeps its strength when one of those fleets closes in on a lunar colony.
8. **The AI's Moon while its fleets are away.** In an observer run or at war with an AI that holds a lunar colony: when its offence or defence has sent every fleet of its own away from Earth, and an enemy fleet reaches Earth, does it lose the Moon? Its defence has no Earth arm (it never comes home for a lunar colony), and only Auto's reserve or its reserve rule puts a fleet back up. Record how often an AI loses a lunar colony this way; an Earth arm in its defence is the fix if it does.
9. **A free lunar colony's price.** At peace, with a free colony on the Moon: the home fleet's Target button picks it for nothing (its hover has no price line). Close in's hover then shows the price, and the click charges it once; while closing in, the Target hover's last line names the price, and targeting another free colony charges it again.

## Lunar colonization, build 3a: Nuclear Thermal Propulsion's premium (2026-10-29)

Design § 9 of `docs/superpowers/specs/2026-10-29-lunar-colonization-design.md`: a second off-window premium curve, the same extra delta-v at 9 km/s, which a country with Nuclear Thermal Propulsion pays (`sr_window_premium_country_<body>`). No new self-check: `window_gate_paid` (`docs/testing/global-commons-playtest.md`) now logs the country's own premium, cached and by date, so an NTP launch that reads the chemical curve shows as a mismatch or a `spent` above goal × (1 + the NTP figure). Reference: `docs/engine/launch_windows_report.md`, the NTP columns.

1. **The tooltip.** Nuclear Thermal Propulsion shows "Smaller Premium for Off-Window Launches" under its funding cap line, with its explanation on hover, and its description ends on the smaller premium.
2. **An NTP country's off-window cost.** For a country running Solar System Colonization, research Asteroid Mining and Nuclear Thermal Propulsion from the console. The month after a Mars window closes (offset +2; the windows are in the global commons list's Reference line), Mission Control's Next Windows reads Mars at about +16%, where a country with Asteroid Mining alone reads about +43%; the month after, about +46% against +150%. Its "costs N months" is goal × that ÷ pace. `event te_debug_launch_windows.1` option b: the `TE_LAUNCH_WINDOWS mars` line's `premium` and `premium_by_date` are both the NTP figure, and `our_cost` is it too while the approach would launch.
3. **Cheaper, not possible.** A country with Nuclear Thermal Propulsion but not Asteroid Mining still waits for windows: Next Windows reads "In N months" with no premium.
4. **The launch.** Under Standard at a fast pace, the NTP country launches off-window in more months than the chemical one (the report's off-window rule on Mars, NTP columns), and its first such launch logs `TE_SELF_CHECK OK window_gate_paid` with `premium_cached` = `premium_date` = the NTP figure.

## Colony management (2026-10-30)

Design: `docs/superpowers/specs/2026-10-30-colony-management-design.md` (the owner's play-test notes on the Colonies section). Simple and Full Colonies. The `unit_` field the Training Ground puts on the journal entry reaching the army is what vanilla's `modifiers_while_active` already do (the Caucasus war entries' `unit_offense_*`), and item 6 looks at it. Grep `debug.log` for `TE_SR_MODULES` for a colony's own builds. The follow-up (#1258) made the slot and drive technologies markers, which two self-checks read:

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN drive_marker country=… level=…` | once a game, a month after a country running colonization first has Fusion Power | Fusion Power's `country_sr_drive_fusion_bool` (a script-only boolean) reaches the country and `sr_drive_level` reads 1 or more | the country reads no fusion drive: `modifier:` does not read a technology's script-only boolean, so every drive is lost | drop `script_only = yes` from the three drive types, as Nuclear Thermal Propulsion's boolean is declared; failing that, read `has_technology_researched` again in `sr_drive_level`, `sr_launch_has_fusion` and `sr_launch_has_antimatter`, keeping the markers for the tooltips |
| `TE_SELF_CHECK OK/BROKEN habitat_marker country=… modifier=… seen=…` | once a game, a month after a country holding a colony first has one of the five Habitat room technologies | the technology's `country_sr_habitat_room_add` reaches the country (`modifier` 0.1 or more) and its first colony's `sr_site_hab_share_now_<key>` reads it through the holder's scope (`seen`, the share less 0.5, at least it; more where the world keeps a better share from an earlier holder) | `modifier` 0: the technology's script-only share does not reach the country; `seen` below it: the scope switch (`global_var:sr_site_holder_<key> = { add = modifier:… }`) reads nothing | `modifier` 0: as `drive_marker`'s fallback, drop `script_only = yes`; `seen` short: read the holder's five technologies in `sr_site_hab_share_now_<key>` (`gen_solar_sites.render_population_values`), keeping the marker for the tooltips |


1. **Drift colors.** In the Autonomy view a colony whose autonomy is rising shows its drift in red, one falling in green; the hover's terms the same way, and its last line says where the colony settles.
2. **Settling.** A colony with a hover reading "settles near 30%" moves toward 30 from either side over the following years, and a chartered colony settles near 0 instead of drifting back up.
3. **Next Windows.** On chemical rockets, with stage-4 and stage-5 worlds unclaimed and targetable: the Uranus, Neptune and Kuiper Belt rows are absent, and the line under the table counts them. Each row's transit matches `docs/engine/launch_windows_report.md` for the month; with a fusion drive the Window column reads Any month, and with Asteroid Mining a closed window reads the premium and the months. The Staged in Orbit hover lists the same destinations.
4. **Slots and the price past them.** Queue modules at a 2-slot colony until its Slots reads 3/2 (red): the hover's next price reads 300; the module past the slots leaves fabrication's stock 200 lower when it is built, the next 300 lower. Five past the slots, the + buttons grey out with the room line crossed. With Advanced Nanofabrication the colony reads one more slot. *Superseded by § Colony people limit modules (#1954 Part B).*
5. **Facilities.** Build one of each at a fully crewed colony: the entry shows Off-World Research Stations, Cultural Centers, Resorts, Black Sites, Training Grounds and Materials Foundries at multiplier 1; the colony's Bases rises by 50 with a Mining Complex; Module Fabrication's rate rises by 4 with an Orbital Yard (and Space Command's month by 0.5 under Full Colonies); the nuclear Command Reliability target rises by 4 with a Nuclear Command Center; the colony's drift hover shows −0.15 for its Administration. Blockade the colony: the Mining Complex, Yard, Resort and Foundry stop, the rest keep running.
6. **The Training Ground reaches the army.** With Off-World Training Grounds on the entry, a battalion's experience gain in the military panel's breakdown includes it. If it doesn't, stop declaring `sr_module_train` on the entry and add it to the country instead, at `multiplier = sr_mod_units_train` on the colony month (`sr_mod_month`), removing the old copy first.
7. **A colony's own modules.** A colony at autonomy 50 with 30,000 people shows Building climbing by 1.5 a month; at 100% it gains a module (`TE_SR_MODULES <key> built a module of its own`), Building restarts at 0, and a specialization level shows in its modifiers at once. A colony with no slot or specialization level left holds at 100%.
8. **A colony's page.** Click a colony's name, or the arrow beside it (which shows on the list, not the page): only that colony shows, with People, Modules, Autonomy and (Full) Defenses one under another, each heading with its control on the right (Settlers and the priority button, Clear, Abandon), the figures in tiles two to a row with an icon each, and the fifteen modules one to a line with their full names (a site's specializations by name) and nothing cut short. Hover a tile: its breakdown, as the list's figure gave. Back returns to the list, and so does any view button. Every button on the page works as it does in the list. Nothing on the panel is underlined but a word inside a tooltip.
9. **The AI.** In an observer run, an AI outside the top three that holds a colony sets Emigration to Steady with a positive income, queues a module a year, and answers a self-government demand with a charter; it lets a colony go only after losing its Space Program. Cede Colony: asking an AI for its empty lunar outpost shows about −60 for the colony in the acceptance breakdown, and for a large built-up colony −200.
10. **Solar System's second line.** Under Simple Colonies, each site in Solar System shows the module icon with its slots as ours (its size's plus our Colony Module Slots) and the Extraplanetary Base icon with its room and grade ("300 (+30%)" at 16 Psyche); each hover says what it means, and the base hover's Base Grade is a link to its concept, as in the Mining Complex's hover and a colony's Bases hover. Under Races Only the line is gone. *Superseded by § Colony people limit modules (#1954 Part B).*
11. **The technologies' tooltips.** Nuclear Thermal Propulsion, Orbital Manufacturing, Advanced Nanofabrication, Space Colonization and Molecular Assemblers each list +1 Colony Module Slots, and each adds a slot at every colony we hold (the Modules view's Slots, the page's Slots tile). Fusion Power lists Fusion Drive for Colony Fleets, Muon-Catalyzed Fusion Reactors Fusion Torch for Colony Fleets and Antimatter Production Antimatter Drive for Colony Fleets, and Next Windows' transit falls with each as before. *Superseded by § Colony people limit modules (#1954 Part B).*
12. **The race to the Moon.** Hover Solar System Colonization's reward in the milestone grid: the race to the Moon is named as the old Moon Base milestone's prize and the one race among the sites; a lunar site's hover in Solar System points to it.

## Extraplanetary Bases: −75% past the room and a flat crew (2026-10-31)

Owner, 2026-10-31: a level past all of a country's room works at −75% (`gen_solar_sites.OVERFLOW_GRADE`, −50% before), and the base's four base methods hire a flat crew in `unscaled` (800 on Regolith Processing, 1,000 on the others) with `building_job_attractiveness_mult = 5`, as the `pm_ai_managed_*` crews. That an `unscaled` crew counts once a building and that goods still follow every level is what that prototype's self-checks read (`ai-managed-flat-staff-playtest.md`); no new self-check.

1. **Past the room.** Under Simple or Full Colonies, with room for 10 (Asteroid Mining, no colony) and 20 levels, the Extraplanetary Base Room modifier reads −37.5% Extraplanetary Base throughput, and the Modules view's room hover and Base Grade's concept −75% past the room.
2. **The crew.** A base of 20 levels or more on the Asteroid Mine shows about 500 machinists, 400 engineers and 100 academics, and no more after another level. Its output is the method's per level × its levels (× throughput), as the output tooltip lists, once the crew is in.
3. **The crew fills.** A month or two after a base is built or grows, its staff reads at or near the crew; if many bases sit well below it, look for a state short of engineers before raising the attractiveness.

## Extraplanetary Base ground types: the Bases view (2026-11-21)

Design: `docs/superpowers/specs/2026-11-05-extraplanetary-base-ground-types-design.md` § 9.1. Simple or Full
Colonies, In-Situ Resource Utilization, a few colonies held and a base of 50 levels or more. The view's figures
are the refresh's: give a new base a month before reading them.

1. **The look.** The Colonies switch shows five buttons on one line, People to Bases, none clipped. Bases shows the
   checkbox and "Assign for the most profit"; the levels rows (with the checkbox off, "Unassigned levels" too); the
   move lines; "Output a Week, Before Other
   Modifiers" with Now and If prices hold, each a profit on the right and seven goods icons under it; then, with
   Asteroid Mining, the near-Earth asteroids' box; then each colony's box: its name, its ground type and grade on
   the first line, "levels / room", − and + and "£… a level" on the second, seven goods on the third. Nothing
   overlaps or runs past the panel's edge, and "Near-Earth Asteroids" is not cut off.
2. **`|K` in the totals.** The totals' goods read at most five characters ("12.3K", "1.23M"). If the game prints
   six ("123.4K"), the cell cuts them off: widen `te_sr_eb_good_cell` by narrowing its icon, or print the totals
   with `|0` on two lines.
3. **The checkbox.** The mod's first `checkbutton`: it draws ticked with the checkbox on, at 24 × 24, and a click
   unticks it (`sr_ebase_auto_sgui`), the second row turning to "At our assignments". Its hover gives the rule.
4. **− and +.** With the checkbox off, a click on a colony's + raises its assignment by 5 and "→ N" appears beside
   its levels; a right-click raises it by 25, and − lowers it the same ways. The tax workbench's steppers right-click a
   scripted GUI the same way (`onrightclick` with an `op` scope, on a button greyed by another op's `IsValid`): if a
   right-click does nothing here, compare them, and failing that give each box ±25 buttons of its own. A right-click
   on a greyed + changes nothing, the checkbox included (the effect sets nothing unless the target changes). A
   click with the checkbox on unticks it first.
5. **The move lines.** With the checkbox on and a move under way (raise one good's price until a site of another
   type earns more): "Moving since <year>, up to N a month", "From <site> to <site>", and "<site> earns N% more a
   level", or "<site> loses money a level". With nothing moving: "Levels stay where they are" and why. With the
   checkbox off: "Levels to move to our assignments: N" and "Months to go: about M, at up to P a month"; at the
   assignments, "no levels left to move".
   Once a move has ended, "Last move: <year> to <year>" and its sites. The lines give years, not months.
6. **A colony that doesn't serve us.** A blockaded colony stays listed, its box reading "Blockaded: N working
   elsewhere until freed" in red; an occupied one reads "Occupied:" and is still listed. A blockaded colony that
   held no levels shows no such line.
7. **The hovers.** The view button's hover, and each good's hover in a box, name the method most of our levels run.
   The totals heading's hover ends with our country's breakdown of Extraplanetary Base throughput, and says its
   Extraplanetary Base Room line is the grade, already in the figures: with no other throughput, Now's goods match
   the base buildings' output added up. If the breakdown prints nothing or raw text, drop it from
   `je_space_race_widget_eb_totals_tt`.
8. **Frame time.** With Bases open on a large country's save holding about 20 colonies, the panel's frame time is
   about that of People (the wall clock of `docs/audits/late_game_performance.md`, "Reading the wall clock"). Most
   figures are stored variables, but each box's + reads `sr_ebase_queued_levels` for its validity, and the levels
   rows and the unassigned line read `sr_ebase_levels` and `sr_ebase_queued_levels`: each a walk over the
   country's states and buildings, up to 41 boxes a frame (final review S2). If it is slower, have the + buttons'
   `enabled` read a free count (queued less assigned) that the refresh and each click store, and keep the live
   check in `is_valid` for the hover and the effect's clamp; a level queued between updates then leaves + greyed
   until the next one.
9. **The switch row when Bases appears.** Open the Colonies tab before In-Situ Resource Utilization, with four view
   buttons, and research it with the tab open: the Bases button appears at the right end of the row and nothing
   runs past the panel's edge. The row sits in a fixed 476 slot, its buttons from the left (style rule 8: a centred
   row is placed once, at its first width).

## Taking a module down (2026-10-31)

Owner, 2026-10-31: on a colony's page each module has a minus button that takes one level down over 12 months
(`sr_mod_dismantle_months`), one level at a time a world (`sr_colony_dismantle_sgui`; the record is the holder's
`sr_md_type_<key>` and `sr_md_left_<key>`, the work `sr_md_month_<key>` from `sr_mod_month`). It rests on nothing new
the engine has to prove (a variable counted down by the entry's pulse, the generated level write the landing already
uses), so no self-check. Console: `event te_debug_space_race.4`, option *Finish every module level we are taking down
now*; `TE_SR_MODULES <key>: a module level of type N dismantled` in `debug.log`.

1. **A level comes down.** Under Simple or Full Colonies, with a Research Station at level 2 on a colony, open the
   colony's page and press its minus button. A red line under its name reads *Coming down, months left: 12*, one less
   each month; the button greys on every other module of that colony (*Nothing else is being taken down*). Twelve
   months on the level reads 1, Slots one fewer, and Research Station's entry modifier its new size the same month.
2. **Stop it.** Press the minus button again on the module coming down: the line goes, the level stays.
3. **The founding specialization.** Its minus button is greyed at level 1 (*the outpost itself*); at level 2 it takes
   it to 1. The other specialization goes to 0, and its modifier leaves the entry.
4. **A Habitat.** With the colony's people above the room one Habitat fewer would leave, its minus button is greyed.
   With room to spare, start it: settlers stop at the smaller room (the colony's emigration weight falls), growth
   stops there, and when it comes down no one is lost.
5. **Under fire (Full Colonies).** While an enemy fleet blockades the colony, the months left stand still; when the
   colony is occupied or ceded, the line goes and the level stands. Taken back, it has the level.
6. **Lunar worlds.** A Moon colony's page shows no Spaceport row's minus button.

## A colony's page: its own icons (icon batch 8, 2026-10-31)

Thirteen tiles and module rows on a colony's page had vanilla or borrowed placeholders (`space_race_gui_icons.md` §
A colony's page has the table). No script reads them.

1. **The tiles (34 px).** Open a colony's page under Full Colonies: Crews shows a colonist in an orange suit with a
   wrench; Modules Crewed the silver module with a people mark; Autonomy the Habitat's dome flying a teal flag; the
   Autonomy section's Status the dome with a red wax seal; Defenses a grey gun turret on rock; Integrity the dome
   with a crack down it; the Defenses section's Status the dome with a radar dish. Each reads at its size, the crack
   included.
2. **The module rows (24 px).** Habitat a blue dome over lit windows, Spaceport a gold lander on an orange-ringed pad,
   Research Station a silver observatory with a brass telescope, Cultural Center two gold theater masks, Training
   Ground a marine in sand-tan leaping, Nuclear Command Center a blast door with a yellow radiation sign, Defenses the
   turret. None is a speck or reads as something else.

## The owner's UI pass: quick changes (2026-10-31)

No post-setback cooldown, self-government at 50, the grade beside Bases, the queue in its own box, Solar System lower
(`docs/systems/mod_systems/space_race.md` § Key Mechanics, § Colony modules and Extraplanetary Base room).

1. **No Shielded state.** Force an Ambitious failure (`event te_debug_space_race.1`, option j, on a milestone set to
   Ambitious) and answer it: the overview keeps reading Ambitious with its risk, never "Shielded", and the next month
   rolls as usual. The console's "Clear the setback cooldown" option is gone.
2. **Retired at vanilla 1.15** (the strip went with the migration; saves from 1.14.5 don't carry over). ~~**An old
   save from inside a cooldown.** Load a save taken while a milestone read Shielded: within a month the overview reads
   its approach again (until then a Safe or Standard one may read Ambitious), and `sr_failure_cooldown` is gone from
   the country.~~
3. **Self-government at 50.** A colony whose autonomy reaches 50 fires `space_race_events.94` (Demands
   Self-Government), and the overview's Colonies cell names it in red from 50.
4. **The grade beside Bases.** The Colonies section's Modules view: each colony's Bases reads its room and grade,
   "160 (+5%)", the minus a true minus at the outer moons; a colony's page shows both in the Base Room tile. Nothing
   elides.
5. **The queue's box.** Queue two modules: under the base room, a "Queue (2)" heading, then a darker box with "Next
   module in N mo" and the two places, and a gap before the colonies' rows. Fill all eight shipment slots with stock
   in hand: it reads "slots full". With no fabrication method and too little in stock: "stopped", in red; with the stock covering the head, it still reads "in 1 mo" and the module is built. The months match the stock, the
   rate and the head's price (100, more past the colony's slots).
6. **Superseded by the tabs (PR 8).** Solar System is now its own tab, above How Solar Colonization Works: the tabs'
   section below.

## The owner's UI pass: tabs (PR 8, 2026-10-31)

Solar System Colonization's four tabs (UI pass design § 11; `docs/systems/mod_systems/space_race.md` § Tabs).
**Fallback** if the tab row misbehaves in one host: drop the wrappers' `visible`, which brings back the one long panel.

1. **The default.** A new session opens Solar System Colonization on Mission Control: the approach, funding, setbacks,
   Next Windows and Rivals, with the overview above the tab row. The Mission Control button is greyed.
2. **Each tab.** Fleets shows Colony Fleets, and under Full Colonies Space Command and Space Fleets; Colonies shows
   Colonies; Solar System shows Solar System and How Solar Colonization Works. Each tab's button greys while it is
   shown; the labels read in full.
3. **Remembered.** Pick Colonies, close the journal and reopen it: still on Colonies. The same in the Timeline Extended
   window's Space Race tab, which shares the choice.
4. **Both hosts.** The tab row and every tab draw in the journal entry and in the Timeline Extended window.
5. **Other milestones.** The Mars Landing and the rest keep their one panel, with no tab row.
6. **The window's Mission Control.** In the Timeline Extended window's Space Race tab, Mission Control shows no Orbital
   Debris row (the window's empty `sr_debris` override reaches it one container deeper now); the journal's does.
7. **The guide's screenshot.** Retake `docs/player_guide/images/solar_system_colonization_tab.png` on the Mission
   Control tab, with the tab row in view, and check its caption in `16-space.md`.

## The owner's UI pass: the Base Room cell (PR 5, 2026-10-31)

The colonization overview's Base Room cell and the refresh when a base is built (UI pass design § 8;
`docs/systems/mod_systems/space_race.md` § Colony modules and Extraplanetary Base room).

1. **The cell.** With In-Situ Resource Utilization, the overview's third row shows Base Room: our Extraplanetary Base
   levels against our room ("120 / 400"), and under it the site the next level goes to (since the ground types
   build; see "Extraplanetary Base ground types: the controls", item 8, below). Without the technology the row is gone.
2. **Queued levels.** Queue 20 levels: the cell reads "120 +20 / 400" at once (owner, 2026-11-04; it had read "120 / 400"
   with the queue left out), the hover counts them, the Modules view gains "Extraplanetary Base levels
   queued +20", and by the next month (or the day after a level finishes) the next site moves to the one those
   levels would leave (counting them, not only the built ones). Queue past all of our room: the figure turns red
   and reads "next at −75%" at once, and with nothing built and 80 queued against room for 75, "0 +80 / 75" in red. Nothing elides; with room of
   10,000 or more (Mining Complexes) or 1,000 levels queued, the cell shows their sum instead ("12000 / 14335").
3. **On completion.** When a queued level finishes, the cell's average and its next site change the next day, not at the
   next month. If nothing changes until the month turns, `on_building_built` / `on_building_expanded` never reached
   `te_on_building_*` (unverified, `scripting_best_practices.md`); fallback: drop the hook, the monthly pulse stays.
4. **A batch stacks nothing.** Let several levels finish on one day (queue them in several states at once) and compare
   the country's Extraplanetary Base Room modifier before and after: one copy, at the new average, not two.
5. **No stutter.** With the panel open and many states holding bases, scrolling the overview stays smooth (the levels,
   queue and room are read live, each a loop over our buildings). Fallback if it stutters: read copies the refresh
   stores.
## The owner's UI pass: the popup and the colony target (PR 2, 2026-10-31)

The mod's first centred popup (`te_ui_popup` in `gui/te_widget_library.gui`, the `te_popups` root in `gui/te_popups.gui`)
and the colony target popup it carries (`docs/systems/mod_systems/space_race.md` § Popups; UI pass design §§ 3, 5).
**Fallback** if the popup layer misbehaves: draw `te_sr_target_popup_body` inline in Colony Fleets, under the row that
opened it.

1. **It opens over both hosts.** Colony Fleets' Choose (Change once there is a target) opens Colony Target in the middle
   of the screen, the rest dimmed, over the journal panel and over the Timeline Extended window's Space Race tab.
2. **It closes three ways.** Escape closes the popup and leaves the journal panel or the Timeline Extended window open
   behind it; a click outside the popup closes it; so does its close button. Reopen it each time.
3. **The rows read.** With the popup open from either host, every listed site shows its slots, base room and grade,
   holder, inbound fleets and launch window (slots, room and fleets under Simple and Full Colonies; "Any month" at the
   Moon and Mercury; "Open now", "In N months", or with
   depots "+N% now, N mo" elsewhere), with figures, not raw keys or zeros. The count reads "N of 40 sites can be
   targeted"; Show all lists all 40.
4. **Target and Clear.** Target on a site closes the popup; Colony Fleets names the site, with Change and Clear, and
   Solar System's row reads Our target. Reopened with Change, the popup shows that site's button as Clear. Both
   clicks run once (the choice, then the close, on one button). A site beyond the Moon before the Mars Landing is
   greyed, its hover naming the Mars Landing.
5. **Solar System is a list to read.** Its rows have no button; the row ends after the inbound fleets.
6. **The entry closing under it** (hard to reach on purpose; note it if seen). With the popup open while the
   colonization entry goes away, the popup says "Solar System Colonization isn't running." instead of an empty frame.
7. **The screen behind takes nothing.** The shell carries `filter_mouse = left|right|wheel`, as vanilla's windows do.
   With the popup open, the wheel and a right-click outside its body neither scroll the journal panel nor move the
   map; a left-click there closes the popup.
8. **The launcher.** The Timeline Extended launcher (`layer = top`) draws over the dim. Note whether it still opens the
   window while the popup is up; that's acceptable either way.
9. **A long window figure fits.** With depots and a closed window, a site's window reads "+N% now, N mo" in full,
   months included, not cut off with an ellipsis.
10. **The people room** (the owner, 2026-11-22). Under Simple or Full Colonies, the line under each site's name starts
    with the population icon and its people room before Habitats ("25,000" at Shackleton, "50,000" at Valles
    Marineris, in full, not elided), then the Habitat cap; its hover gives our Habitat share as a percent, not 0%.
    With Space Colonization the figures read 50% higher (37,500 and 75,000), and with Terraforming too, double
    ("100,000" at Valles Marineris, still in full). Solar System's own rows have no such cell.

## The owner's UI pass: the Earth alert (PR 6, 2026-10-31)

Hostile fleets bound for Earth (UI pass design § 9; `docs/systems/mod_systems/space_race.md` § Earth orbit): the
quiet feed notice `sr_earth_hostile_notice`, the loud `space_race_events.111`, and the overview's Hostile Fleet cell,
all under Full Colonies. **Fallback** if the feed notice doesn't show: a popup in `.106`'s shape for the quiet case
too.

1. **The quiet notice.** At war with a fleet power, with a stronger fleet of ours at Earth, watch one of its fleets set
   out for Earth: one notice in the feed, "A Hostile Fleet Is Bound for Earth", naming the country, not a popup and
   not every month after. Its color is the feed's bad one.
2. **The loud notice.** With no fleet of ours at Earth and Earth not blockaded (or ours weaker than theirs there plus
   what is coming), a hostile fleet setting out for Earth brings the popup Earth Is Threatened, once, with the
   country's name, the months to its landing and both strengths as figures, not zeros. No feed notice for that fleet.
   **Not when already blockaded:** with Earth blockaded, their fleets flying home bring feed notices, not popups.
3. **Loud later in the leg.** With a quiet notice heard, take our fleet away from Earth while theirs is on the way:
   the popup comes the next month, once.
4. **A war declared mid-flight.** A country's fleet already on its way to Earth (coming home, say) when it declares
   war on us: the notice comes the next month.
5. **Two loud fleets in one month.** Two hostile fleets that would each tip the balance set out the same month: one
   popup, naming one fleet's country, and a feed notice for the other fleet; no second popup the month after. With
   one of them heard quietly before (item 3's setup), the popup names the other, the one we hadn't heard of.
6. **The cell.** While a hostile fleet is on its way, the overview's third row shows Hostile Fleet, "Earth in N mo"
   and "theirs vs ours" (theirs at Earth and on the way); red in the loud case. The hover has a line a country, its name, fleets, strength
   and first landing, with the figures not zeros (they're read in that country's scope). Gone once they land or the
   war ends, and absent under Races Only and Simple Colonies.
7. **Two powers' notices.** Fleets of two different powers set out for Earth the same month, each quiet: the two feed
   notices name different countries (each saves its owner before it posts; unverified that a notice keeps it).
8. **No stutter at war.** At war with several fleet powers, scrolling the overview stays smooth (the cell walks their
   nine slots each frame). Fallback: read copies the step stores.

## The owner's UI pass: fleet upkeep and Space Command (PR 7, 2026-10-31)

The maintenance line and no fleet orders without a Space Command (UI pass design § 10;
`docs/systems/mod_systems/space_race.md` § Upkeep). Self-check `fleet_upkeep_line` above.

1. **The line.** Any Space Command's input tooltip lists 20 Electronic Components, 20 Wired and 20 Wireless
   Telecommunication Gear, 10 Software, 20 Industrial Robotics and 40 Chemicals at full staff, under every yard method,
   and the same at one level as at four. With no fleet, nothing more.
2. **The upkeep.** With a fleet of 100 strength at full (10 units), each of the six reads +9,000% on the building
   (Fleet Upkeep), and the panel's Upkeep reads +9000%. At full staff Industrial Robotics reads 1,820 a week (20 ×
   91): the unscaled line takes the multiplier. Launch Capacity, Advanced Materials and electricity show no Fleet Upkeep
   line. Switching the yards to Orbital Shipyards changes none of the six.
3. **No Space Command.** Demolish Space Command with a fleet at Earth: Space Fleets' red note shows; Go, the posture
   button and the target button are greyed, each saying why; a refit under way stops counting down and resumes when a
   Space Command is built again; a damaged fleet isn't repaired, but its supply and propellant refill. A fleet in
   flight lands. An AI at war without one sends no fleets.
4. **Occupation.** With Space Command's state occupied, the same as 3. (Unasked: the occupied building still pays its
   line and the upkeep while its staff work.)
5. **Two Space Commands.** A nation runs one since "Pausing Space Command" below: annexing or forming a country that
   holds a second one dismantles the smaller within a month (item 5 there), and the one kept carries the whole Fleet
   Upkeep (at 10 units, +9,000%).

## Pausing Space Command (2026-10-31)

Pause and Resume, the AI's fiscal pause, one Space Command a nation and half fire without one
(`docs/systems/mod_systems/space_race.md` § *Fleets, Space Command and combat*: the Pause, One Space Command a nation
and No Space Command bullets). All under Full Colonies. No self-check line: each rests on a read below.

1. **Pause.** (Since 2026-11-25 Paused is one of Construction's three modes; "Space Command's Construction table"
   below.) With a Space Command running Fusion Yards and a fleet, choose Paused: it is drawn selected, Built a
   month reads Paused at once, and the building's modifiers list Construction Paused. At the next monthly step
   nothing is built: Fleet strength at full doesn't rise, nor the Reserve with Auto-launch off. A fleet still takes Go,
   posture and target orders, Launch still sends a reserve up, and with Auto-launch on a reserve built before the pause
   still launches itself. Choose Full: it is drawn selected, Built a month reads Resuming, the inputs stay cut, and the
   next step builds nothing; then Construction Paused comes off, and the step after builds the full month's figure
   again. Choosing Paused before the step cancels the resume: still paused after the step.
2. **The inputs' tooltip read (unverified engine fact).** Paused, the building's input tooltip shows Launch Capacity
   and Advanced Materials at 0, each with a −100% Construction Paused line, while the six maintenance goods keep
   their lines and Fleet Upkeep. **Fallback** if a −100% sum doesn't zero an input (it shows a small figure, or
   the building still buys it in the market panel): fold the method's own +100% into the cut, as the uploaded minds'
   Nexus does (`te_demog_um_nexus_good`: the multiplier × (1 + the building's other bonuses on that good)).
3. **Below −100%.** Run Torch or Antimatter Yards under Green Building Codes (the Global Warming entry's
   `green_building_codes_modifier`, −2.5% electricity on every building) and pause: electricity sums to −102.5%. It
   should read 0, not a negative figure, and the building shouldn't sell electricity or show a negative input.
   That is the only other source on the three goods that reaches a Space Command (`/modifier-grants`: the others sit
   on Deep-Sea Mines, the Nexus and grid stations). **Fallback** if it goes negative: the cut at −1 minus the
   building's other bonuses on the good, read as `prev.modifier:goods_input_electricity_mult` at the apply.
4. **The AI's pause (observer).** In an observer run past 2000 with AI fleet powers, find one in default or in
   deficit at peace: its Space Command carries Construction Paused (the building's modifiers), and its reserve and
   fleets stop growing. It resumes no sooner than six months later, and only once out of default with a surplus, or
   at war. An AI in deficit at war keeps building. Watch that a budget near zero doesn't flip it every month.
5. **One Space Command a nation.** Annex or form a country with a Space Command while you hold one: within a month
   the one with fewer levels is dismantled, and the feed says "Space Command Dismantled", naming its state and the
   one kept (the state names, not blanks). With the same levels, the one in your market capital stays. Two removed
   the same month bring two notices, each naming its own state (each saves its state before it posts; unverified that
   a notice keeps it). The month a building is dismantled may build that month from both (the modifier sum can lag a
   day): note it if Built a month jumps once.
   **At the source** (review of #1287, I2): move the market capital (its Space Program follows) and open the build
   menu there: Space Command is refused, its hover reading "We have no other Space Command: a nation runs one, so
   expand the one we have, or demolish it first". The old one, now outside the Space Program's state, still expands.
   Demolish it, and the new capital can build one. **The AI (observer):** an AI that annexes a Space Command with more
   levels than its own keeps the annexed one and expands it there, up to its cap; Space Command shouldn't keep
   appearing and vanishing in its capital.
6. **Half fire.** At war, fight a battle at a location with a Space Command and note a month's losses on both sides
   (the battle report). Demolish Space Command, or have its state occupied, and fight a comparable month: our fleets
   deal about half the losses, take the same, and Space Fleets' note and the orders' hover say they fight at half
   strength. At Earth, Orbital Superiority falls by about half the margin, and an inbound hostile fleet that our
   fleet's full strength would hold now brings the Earth Is Threatened popup. That popup and the overview's Hostile
   Fleet hover still print ours at full strength, and add "Without a Space Command our fleets fight at half
   strength." The battlestation and the batteries fire as before.
7. **No month built for free (review of #1287, I1).** A month is built in one lump at the country's monthly step,
   so Resume waits for the step, and that step builds nothing. Pause the day after a step (Built a month just
   changed) and Resume the day before the next: that step builds nothing, Construction Paused comes off after it,
   and only the step after builds. Pausing mid-month bills the days since the last step for nothing, at most a
   month's inputs. **The owner's alternative** (zero waste, a slower crisis pause): both a pause and a resume wait
   for the step.

## Space Command's Construction table: orders, the mix and the three modes (2026-11-25)

The build mix's five buttons and the Pause button became a table and three modes
(`docs/systems/mod_systems/space_race.md` § *Fleets, Space Command and combat*: the Orders and the modes bullet).
All under Full Colonies, with a Space Command building at a known rate (Built a month). No self-check line: every
engine fact it rests on is in use elsewhere in the panel (two chained scopes on a scripted GUI: the module buttons;
`click_modifiers`: the Transfer popup; the selected-tab look: the Strategic Reserve's policies). Console option n of
`event te_debug_space_race.6` fills the reserve, to tell built hulls from launched ones.

**Seen in game 2026-11-25** (PR #2063; `game_qa` on a copy of the owner's USA save of June 2043, the branch in a
variant mod, runs `20261125T215243Z`, `20261125T220413Z` and `20261125T221607Z`; 3840 x 2160, scale 1.5; shots in
`/mnt/d/vic3te-data/sr-orders-2026-11-25/shots/`). Steps 1, 2 and 3's plain clicks, as written, with the hovers of
an order's +, a weight's + at 3 (greyed, "Its weight is below 3" crossed) and the mode in force. Steps 4, 5, 7 and
8 with the month run from a setup (`sr_sc_month = yes`), not by passing days: from Paused, Full read Resuming and
the first step built nothing; orders of 30 Warships and 15 Siege at 17.8331 a month came down 2 to 1 (18.11127
and 9.05564, then 6.22254 and 3.11128, Months to build them 2, then 1) and the fourth step moved both whole (Siege
in the reserve exactly 15, neither order's variable left) with the rest to the mix; Orders Only with nothing on
order built nothing at the next step and read Idle with Construction Paused on the building; an order placed
while idle read Resuming, and withdrawn, Idle again; one hull ordered then built 1.0 and idled. Under the game's
own monthly pulse the resume was seen to take effect (Resuming to building between 3 and 9 July). No line in
`error.log` named the new script or panel. **Not seen:** shift-click and ctrl-click (the harness holds no key; the
form is the Transfer popup's), an order built and launched under the game's own pulse, step 6 by hand
(`OrdersRunTest` runs it) and step 9. Two of the runs ended in a crash while days passed, both in the engine's
random lock as the harness's date read met a running tick (#1963, with the folders): the harness's, not the
panel's, and the reason the month was run from a setup.

1. **The layout.** Under the six cells: Launch, Auto-launch: On and Crews first: Hulls in one row, none cut short;
   the Construction heading; Full (drawn selected), Orders Only and Paused; then the table, its five heads each over
   its column and the rows not wider than the cells above; then Hulls on order: 0. Nothing ends in "...", and the −,
   + and cross buttons sit level with their figures. A click on Auto-launch and on Crews first changes its value in
   place, the row not moving.
2. **The mix.** − and + step a weight by one, between 0 and 3: at 3 the + is greyed ("Its weight is below 3",
   crossed), at 0 the −. The share beside each weight follows at once and the five sum to 100%, give or take a point of
   rounding. With every weight at
   0, Warships reads 100% and the month's construction is all warships.
3. **An order's clicks.** On one role: a click on + adds 1, shift-click 10, ctrl-click 100; the same three on − take
   them off, stopping at 0; the cross withdraws the order. − and the cross are greyed with no order ("It has hulls on
   order", crossed). Hulls on order follows the sum.
4. **Orders first, in Full.** With a rate of R a month, order fewer than R hulls of a role with weight 0 (Siege, say):
   after the next step the Reserve column (Auto-launch off) shows them, the order is back to 0, and the rest of the
   month went to the mix's roles. Then order more than R, of two roles, one twice the other: each month the two
   orders come down in that proportion, Months to build them reads the sum over R rounded up, nothing goes to the
   mix's other roles, and both reach 0 in the same month.
5. **Orders Only.** With an order under way, choose Orders Only: nothing changes until the order is filled. The step
   that fills it leaves Built a month reading Idle, the building's modifiers list Construction Paused, and the
   yards buy no Launch Capacity, Advanced Materials or electricity. Place an order: Built a month reads Resuming; the
   next step builds nothing, the one after builds. Withdraw that order before the step: back to Idle.
6. **No month lost to rearranging.** In Orders Only with the yards building, withdraw the only order and place
   another the same day: Built a month keeps its figure (not Idle), and the next step builds the new order in full.
7. **Switching modes.** With an order under way, Full to Orders Only and back while the yards build: no Resuming, no
   missed month. With nothing on order, Full to Orders Only: Built a month keeps its figure until the month turns,
   then reads Idle, that month building nothing. From Paused, Orders Only with nothing on order reads Idle at once
   and stays cut (the hover says the yards stay idle until an order); with an order it reads Resuming.
8. **An order always finishes.** Order 5 of one role at a rate that is not round (Built a month 2.5 or so, from a
   yard short of staff): within three months Hulls on order reads 0, and `sr_sc_order_<role>` is unset in the
   console (`has_variable`). In Orders Only the yards then read Idle.
9. **The AI (observer).** An AI fleet power's table is not ours to see, but its reserve and fleets grow in its mix
   as before (warships, carriers and tenders in peace). Tag over to one mid-game: its mode reads Full, or Paused
   under its fiscal pause, and Hulls on order 0.

## The owner's UI pass: Transfer (PR 4, 2026-10-31)

A fleet's Transfer popup, which took in Merge and Detach (UI pass design § 6; `docs/systems/mod_systems/space_race.md`
§ Popups, Transfer). Full Colonies. Self-check `xfer_step_scope` above. **Fallback** if the − and + keys don't reach the
scripted GUI: one scripted GUI per step size, as the construction market has.

1. **It opens.** A fleet at a location with another fleet of ours there, or a free slot and some strength, has
   Transfer in its orders line; it opens Transfer in the middle of the screen, from the journal panel and from the
   Timeline Extended window. Each role and the marines start at half, rounded; Into has New fleet greyed as already
   chosen (or, with all nine slots full, the first fleet there). The row's figures read, not zeros or raw keys.
2. **The keys, on a scripted GUI's button** (the construction market's, there on a GUI-local value): on a role of a
   few hundred (`event te_debug_space_race.6`, "Add 100 strength of each role", adds 100 a use), a click on + adds 1,
   Shift+click 10, Ctrl+click 100, and Alt+click 1,000, which stops at all of it; a right-click sets all of it. On −,
   the same down, and a right-click sets none. Each click moves the figure once. Note whether Shift, Ctrl and Alt need
   the button's hover first.
3. **The three-scope call.** The first click logs `TE_SELF_CHECK OK xfer_step_scope` with the popup's slot, the row's
   role code and the new amount. BROKEN means the third scope didn't arrive; no line at all means the first two didn't,
   or the button never ran (the table says which fallback).
4. **Held to what is there.** Set warships to all, then let a battle cut them (or `event te_debug_space_race.6`'s
   combat now) with the popup open: the amount reads the new strength, never more, and Transfer moves no more than
   that.
5. **Into another fleet.** With two fleets at one location, Into lists the other by its drive and strength
   ("Fusion 12", as its Fleets row), and choosing it greys it; a fleet elsewhere has no button, and a line of Into with
   none hides. Other fleet reads that fleet's figures with the amounts added. Transfer moves them; the other fleet
   keeps its posture, and with ships joining takes the slower drive, the later refit and the lower share of propellant
   and supply. All of every row into it: the first fleet is gone and the second holds both, as Merge did. Two fleets
   with the same drive and strength read alike (a known limit).
6. **A damaged role keeps its ratio.** Damage a fleet (a battle), then move half its warships into a new fleet: in
   each fleet's strength hover, the warships' now over full is the old fleet's ratio, and the two fleets' warships add
   up to the old figures, now and at full. A fleet closing in or interdicting splits off a new fleet at Stand off
   (it has no target).
7. **The refusals.** Transfer greys, with the reason on hover: everything at 0; all of a fleet into a new fleet (it
   would keep nothing); the other fleet destroyed before the click (a battle, or `event te_debug_space_race.6`'s
   "Run this month's combat now" with a stronger enemy there: its Into button goes, and Transfer says the fleet it goes
   into isn't here); into a fleet already past its own carriers' room, the room line, and the marines' + says why.
   With every ship chosen, the marines row shows all of them and its − and + grey.
8. **The marines follow the carriers' room** (owner, 2026-11-24). On a fleet of 199 warships, 99 assault carriers,
   99 tenders and 199 marines (1 past its room), choose 5 of each role into a new fleet: the marines read 10 whatever
   was chosen, Stays 189, Other fleet 10, Transfer is clickable, and the marines' − and + grey, each with its reason.
   Move more carriers and the marines move with them; with room to spare both ways, − and + step within it and a
   right-click sets the fewest or the most the room allows. A fleet already past its carriers' room (carriers lost in
   battle) can still move marines out.
9. **The fleet gone.** With the popup open, let a battle destroy the fleet (a stronger enemy fleet there, then
   `event te_debug_space_race.6`'s "Run this month's combat now"; the popup's dim covers every other window, so the
   fleet can't be sent away from under it): the popup says "This fleet has left, or is gone." and nothing in it acts.
   Transfer closes the popup.
10. **No Space Command.** Transfer still works without one (Merge and Detach did); the owner may want it gated.

## The owner's UI pass: the fleet popups and posture buttons (PR 3, 2026-10-31)

Fleet Destination, Fleet Target and the posture buttons on a fleet's row (UI pass design §§ 4, 7;
`docs/systems/mod_systems/space_race.md` § Fleets, Orders), under Full Colonies. Both popups use PR 2's shell; its
items above (layer, Escape, click outside, mouse filter) apply to them too. **Fallback** if a body shows the wrong
slot: one body, read from a country variable the opening click sets (design § 3's rejected route; mind the same-click
gotcha).

1. **Nine bodies switch with the slot.** With three fleets at different locations, open each one's destination button
   in turn: the popup names that fleet's location, strength, propellant and supply, and lists every location but its
   own. The same from the Timeline Extended window's Space Race tab (Fleets tab): identical rows and figures.
2. **The rows read.** Each row has the trip's months and propellant to a tenth, red where the fleet carries less (the
   hover says so); from Earth a window reading "Open now" or "In N months", blank from anywhere else and blank for a
   fleet at a torch or antimatter pace (Compact Fusion Reactors, Antimatter Production; a fleet of rapid response hulls
   alone runs one drive ahead, so on the fusion drive it reads blank too, and a chemical or fusion fleet still shows
   the window); our colonies there, and the enemy's strength there and on its way (0 at peace). No raw keys, nothing
   cut off with an ellipsis.
3. **Choosing, then Go.** Choose on a row closes the popup, and the fleet's destination button names the location;
   reopened, that row reads Chosen. Go then works as before, and stays greyed where the propellant is short. Both of
   Choose's clicks run once (the choice, then the close).
4. **Why it can't leave.** A refitting fleet's popup says it is refitting; with Earth blockaded, a fleet at Earth's
   says the launches are barred; with no Space Command in a state we control, it says so (before a refit). Each can
   still choose.
5. **A fleet gone under the popup.** With the popup open, let the month tick on a fleet that loses its last battle
   (`event te_debug_space_race.6`'s "Run this month's combat now"): the popup reads "This fleet has left, or is gone." and has no buttons.
6. **The posture buttons.** Away from Earth, a fleet's row shows Station, Stand off, Close in and Interdict on their
   own line under its orders, the one in force lit (not greyed). Each other one sets its posture on one click; a
   greyed one's hover gives the reason (no hostile site here; no site of a country at peace with us; never at Earth).
   Hovering the lit one says what the fleet does in that posture. No hover is cut off or overflows the screen (the
   longest, Interdict's and Close in's at Earth, are about 490 characters).
7. **A posture's price is charged once.** Close in on a free colony: 10 infamy and the UN record once; click Station
   and Close in again on the same site: nothing more. With no target and a free colony the first hostile site here,
   Close in's hover lists the free colony's price before the click, and the click charges it. Interdict a country's site: 5 infamy once; Station, then
   Interdict the same country: charged again (a new interdiction).
8. **At Earth.** With an enemy's lunar colony, the posture line shows at Earth: Station and Close in can be chosen,
   Stand off and Interdict greyed with "not at Earth". With none, no posture line at Earth.
9. **Fleet Target.** The target button opens the sites at the fleet's location with their holders (flag, Ours, Free,
   Occupied, Unclaimed). Target on a hostile site closes the popup and the row's target names it; reopened, it reads
   Targeted. Closing in, targeting a free colony charges its price; interdicting, a new country's site charges the
   interdiction's. A site the posture can't take is greyed with the reason.
10. **No stutter.** Opening and closing either popup, and scrolling Fleet Target at Jupiter (six sites), stays smooth:
    the target popup holds 360 rows, 9 slots × 40 worlds, all but a few hidden. Fallback if it stutters: one body per
    location, the slot read from a country variable. Scroll Space Fleets with nine fleets at locations too: each row
    now asks four posture buttons' `IsValid` (36 a frame for nine fleets), where the step button asked one. Fallback
    if that stutters: the four buttons' state from one display value a fleet, set monthly and on each order.
11. **The two buttons' gates (#1298).** The destination and target buttons grey on `sr_fleet_pick_sgui` and
    `sr_fleet_target_sgui`, which lost their effects (never run) in #1298. No precedent: vanilla never calls
    `IsValidTooltip`, and every other effect-less scripted GUI is read only through `IsValid`. Hover a greyed
    target button (no hostile site at the fleet's location, or no Space Command in a state we control): it opens
    with the failed reason, crossed ("A site here is held by a country at war with us…" or "We have a Space Command
    in a state we control…"), then the target. Hover an enabled one: the same lines ticked. The destination button
    can't grey (its orders line shows only at a location, the gate's one condition), so its hover must open with the
    ticked "The fleet is at a location, not in transit", then the leg; the leg alone is a fail. A missing line or a
    raw key means `IsValidTooltip` renders nothing for a scripted GUI with no `effect`. Fallback: give each gate
    `effect = { custom_tooltip = sr_fl_not_at_location_tt }` (the target gate: `sr_fl_no_target_tt`), a text-only
    effect that changes nothing.

## Colony politics need 1,000 people (2026-11-12)

Owner's decision, issue #1620: autonomy builds, and a colony demands self-government or breaks away, only with
`sr_free_colony_minimum` (1,000) people (`sr_site_peopled_<key>`, `docs/systems/mod_systems/space_race.md`).

1. **An empty outpost through a war.** Found an outpost far out (Kuiper Belt or Saturn) and send no settlers, then go to
   war for a few years. Its autonomy stays at 0, its drift reads 0 and its hover opens with "With fewer than 1,000
   people it makes no demands" and ends "settles near 0%". No "<World> Demands Self-Government", no break-away, and
   the overview's Colonies cell reads Loyal. Incite Colonial Autonomy can't be launched against a country holding only
   such outposts (greyed: "Target must hold a colony of at least 1,000 people").
2. **The thousandth settler.** With the outpost our first colony, set its autonomy to 80 (`event te_debug_space_race.5`) while it has fewer than
   1,000 people: the next months it falls (1% a month), with no demand. Send settlers until it passes 1,000: from that
   month its drift takes its terms again, the hover's note goes, and at 50 or more the demand comes the next month.
3. **A dip under the minimum.** A colony just over 1,000 that Sabotage Colony takes under it keeps its autonomy,
   falling 1% a month; nothing resets it, and Sabotage adds no autonomy while it is under.

## Space Fleets as cards, and the banner (2026-11-14)

Owner's review of 2026-11-14: each fleet in Space Fleets is a card (`te_sr_fleet_row`), with a picture at the head of
the section (`te_sr_fleet_banner`). Nothing here was seen in game before it merged; `docs/systems/space_race_gui_icons.md`
lists the art. Needs Full Colonies and at least two fleets (`event te_debug_space_race.6`).

1. **The card.** Each fleet sits in its own framed box, 480 wide, with a gap between cards. The head reads, left to
   right: the gold emblem in its inset, the fleet's number (I to IX), where it is, its drive (or Refit and its
   months), and the roll-up arrow at the right edge. Nothing overlaps and no label ends in "...".
2. **Ships by role.** Five cells: Warships, Rapid, Siege, Carriers, Tenders, each with its icon, its count beside it
   and its word beneath. A role the fleet has none of shows its icon faint and a 0. Hovering any cell gives the
   fleet's ships, each role of its full number. The icons are painted (the silver warship, a steel-blue dart, a bronze
   gunship behind one big gun, a grey carrier with three orange bays, an orange tank): can the five be told apart at
   24 px, lit and faint?
3. **The bars.** Strength, km/s, Supply and Marines, each a caption, a bar and "now/full" under it. A fleet fresh from
   Earth has four full bars; one back from a battle or a long leg shows the bars part empty, and the figures agree
   with the hover on a role cell (propellant of capacity, supply of months). A fleet with no carriers shows Marines
   0/0 and an empty bar.
4. **Rolling up.** The arrow rolls the card up to its head, which then also shows the strength figure (ships on
   hover) left of a roll-down arrow; the roll-down arrow brings the body back. Each card rolls on its own; the other
   cards don't move sideways. The state resets when the game is restarted (it is client-side).
5. **In transit.** Send a fleet: its head reads "→ <location>", and under it a bar fills as the months pass, a small
   ship riding the bar's end, with "Lands in N months." beside it. The ship marker is not clipped at either end of
   the bar. The orders and posture lines are gone until it lands; the ships and bars still show unless rolled up.
6. **Orders and posture.** Go, Transfer, Land and Embark each carry their sign left of the word, in one line that
   fits the card. The four posture buttons show their icon over their word, a teal world each time: inside a blue
   shield (Station), inside a white ring (Stand off), under four closing arrows (Close in), behind a red-and-white
   barrier (Interdict); the one in force is lit, icon included. Seize shows the flag; with the order set to destroy,
   the burst and Destroy. The orders' signs are still cream line drawings: do they sit acceptably beside the
   painted icons at 16 px?
7. **The banner.** A picture 480 × 110 sits under the Space Fleets header, above the cards. Each is painted at the
   slot's own shape (960 × 220), so it should fill the slot with nothing squashed, tiled or cut off. It is the
   chemical-drive picture at first (dark rocket warships on orange flames over the night-side Earth), and changes once
   Fusion Power (three dark ships on blue-white ring engines), Compact Fusion Reactors (silver ships on white exhaust,
   Jupiter small at the right) and antimatter drives (dark ships on violet beams, a ringed planet ahead) are ours, the
   same step as Colony Fleets' Drive line. The exhaust's color says the drive: orange, blue, white, violet. Is each
   still sharp at that size, with its ships clear of the slot's edges?
8. **A card's world.** Left of where a fleet is, the head shows that location's world at 24 px: Earth Orbit the
   Earth in its gold ring, Mars the red planet, and so on out to the Kuiper Belt's dwarf planet. A fleet in
   transit shows the world it is bound for. Exactly one shows at a time.

## Space Command's cells, the Locations strip and the colony fleets' track (2026-11-14)

The same review. Space Command's four readings are overview cells, Locations is a strip, and each colony fleet in
flight has a track.

1. **Space Command.** Four boxes, two to a row, each with its icon in an inset: Built a month (Space Command's
   building), Fleet strength (the warship), Upkeep (the colonist with a wrench) and Reserve (the lander on its pad).
   Each keeps the hover its row had. Pause: Built a month reads Paused in the same box, with the paused hover, and
   nothing moves. Under them Launch, Auto and Pause as before; then the build mix, five buttons with a role's sign
   over "Warship 1" and so on, in one line that fits. A click still steps the weight 0 to 3.
2. **Locations.** One strip, 476 wide: a narrow column of three small icons (the gold shield, the steel shield, the
   warship; hover each for Ours, Others, Inbound), then nine columns, Earth Orbit to the Kuiper Belt, each under
   its world's icon (the name on hover). Down a column: our strength, the strongest other power's flag, every other
   power's strength, the inbound "count·months", and a status icon. The three caption icons sit level with their
   lines. The flag sits centred in its column; a column with no other power there shows no flag and a 0.
3. **Statuses.** With a fleet standing off an enemy's colonies, that column's foot shows the Stand off icon, the
   world in its ring (hover: Blockading); as the one blockaded, the same icon on a red disc (Blockaded). A battle
   month shows a burst on the red disc; interdiction the world behind its barrier, plain for ours and on the red
   disc against us. Earth's column shows the Earth hovers.
4. **Colony fleets.** Each fleet in flight in Colony Fleets shows, between its world and its landing, a short bar
   with the ship on it, filling from launch to landing. A lunar fleet lands the month it leaves and never shows. A
   fleet launched before this build has its departure month stored already, so its bar is right from the first
   month. The world's name and "in N months (year)" both still fit.

## Module storage, Moon modules and the Next Module hover (2026-11-15)

From a game where eight Hellas Planitia modules held every shipment slot for a Mars window and stopped the Moon's
queue behind them. The console is `event te_debug_space_race.4` as above.

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN module_storage country=… storage=… cap=…` | once a game, a month after a Space Program first runs a Module Storage method at half staff or more | the method's workforce-scaled `country_sr_module_storage_add` reaches its country (`storage` up to 1000 or 3000 by staffing, `cap` 500 + a year of fabrication + that) | `storage=0`: the group's country modifier doesn't reach the country (`module_fabrication`'s check covers the same route for fabrication) | read the method and the program's occupancy in script (`sr_mod_storage_runs`) and add the storage in `sr_mod_fab_storage` |

1. **Module Storage.** The Space Program shows a fourth group, Module Storage, on No Module Storage. Component Depot
   (Cislunar Infrastructure) and Orbital Depot (Space Colonization) list +1,000 and +3,000 Colony Module Storage and
   their goods. The Fabrication row's hover lists the stock: Base 500, a year's fabrication at this month's rate,
   and Module Storage, adding up to the cap it names. With the stock full, the month's points don't raise it.
2. **A cap that falls.** With a full stock above 500, switch Module Storage back to None: the stock keeps its points
   (it is not cut), and fabrication adds nothing until the stock is below the new cap.
3. **Past the slots.** At a colony four past its slots, with only the base stock, the + button greys out with "Our
   module stock can hold its price" crossed; with an Orbital Depot it allows up to eight past, the Slots hover giving
   the price (up to 900) and the stock's cap. Queue one, then switch storage off: when it reaches the top the stock
   still fills to its price (the Next Module hover counts down) and it is built. *Superseded by § Colony people limit modules (#1954 Part B).*
4. **The Moon needs no slot.** *Since 2026-11-23 Mars modules wait in the queue, not in slots (§ Modules built only
   once they can go): fill the slots with modules in flight instead, to Saturn on chemical drives.* With all eight
   shipment slots taken by modules for Mars, queue a Mining Complex at a
   lunar colony behind a Mars module. Next month the lunar module jumps to the top of the queue and is installed
   that month (the level rises, Shipments stays 8 / 0); the Mars module waits behind it. With the stock below the
   lunar module's price it stays where it is. A blockaded or occupied lunar colony's module takes a slot instead
   (*since 2026-11-23 it waits in the queue, On Hold*).
5. **The hover by state.** The Next Module line reads "shipping full" with every slot taken, and its hover gives
   the waiting and in-flight counts, the months until the first can leave (Mars: the months to its window) and
   the first lands, and, with a Moon module behind the head, the Moon note (with Earth blockaded, "Earth is
   blockaded" instead; *since 2026-11-23 a blockaded Earth reads On Hold*). In a window's last month a module still waiting reads about a cycle less 2 months. While
   fabricating, the hover gives the price, stock, rate and months; when stopped, the reason: launch site lost, or no
   fabrication. "1 month" reads singular.

## Module goods and the AI's fabrication budget (2026-11-20)

The owner's resizing of Module Fabrication and Module Storage: no Advanced Materials on the era 10 methods, new
inputs on all of them, and each later method dearer a week but about 10% cheaper a point. No self-check: the AI's
budget reads `fixed_income` and the programme's throughput as the mission budget does.

1. **The goods.** With Cislunar Infrastructure and no Advanced Material Fabricator in the market, Orbital Assembly
   lists 1,300 Launch Capacity, 400 Electronic Components, 300 Industrial Robotics and 300 Wireless Telecommunication
   Gear, and Component Depot 1,000 Electricity, 250 Electronic Components and 125 Industrial Robotics; neither shows
   an Advanced Materials shortage. Orbital Foundries, Fusion Shipyards and Orbital Depot list Advanced Materials
   (15, 20 and 3) with the rest. The building's expenses rise by about 340,000, 732,000 and 1,368,000 a week at
   full staff on the three fabrication methods.
2. **The AI's method.** In a save with AI colony holders that have queued modules, read their Space Programs
   (`scripts/analysis/save_world_report.py buildings --type building_space_program`) a year after the review: one
   with Compact Fusion Reactors and weekly fixed income well over 27M runs Fusion Shipyards; one with it and
   income under about 15M runs Orbital Assembly (or its cheapest method), not Fusion Shipyards. Funding raises the
   line with the throughput.

## Extraplanetary Base ground types: the controls (2026-11-21)

The checkbox, the − and + buttons, the totals and the move notice (ground types design § 8.3, § 8.4, § 9.1, § 9.4;
`sr_colony_sguis.txt`, `sr_ebase_generated.txt`). No self-check: each rests on effects the mod already uses, and
`test_ebase_assignment.py` runs the generated script against the model (`ebase_ground.py`). Open the Colonies section's
Bases view with In-Situ Resource Utilization and a base of a hundred or more levels.

1. **A hover writes nothing.** Hover the checkbox and a site's − and + for ten seconds each: `debug.log` and
   `error.log` gain no `Failed to fetch variable`, `Value of wrong type` or `Event target link 'var' returned an unset
   scope` line from `sr_ebase_generated.txt` or `sr_colony_sguis.txt`, and the game doesn't stutter. Each hover says
   what the click does, and with the checkbox on, − and + add that Assign for the most profit goes off first.
2. **Switching the checkbox off and on.** With the checkbox on, click it: every site's assignment reads the levels it
   has now (a blockaded site's, the levels it is owed), and nothing moves the next month. Click it again: the
   assignments go, and the next month moves up to the pace from the site that earns least a level.
3. **− and +.** With the checkbox off, − on a site lowers its assignment by 5 (a right-click by 25, if the view binds
   it), and the levels above it move at the pace to a site below its assignment. + is greyed while every built and
   queued level is assigned, with that reason crossed; with levels queued it adds up to them and up to the site's
   room. A click with the checkbox on switches it off first.
4. **The totals at once.** A click changes the totals' second row the same moment, without waiting for the month:
   "At our assignments" with the checkbox off, "If prices hold" on. "Now" is the base's goods a week before other
   modifiers: one Asteroid Mine level at 16 Psyche reads about 363 Structural Metals.
5. **Toggling gains nothing.** Switch the checkbox off and on again twice in one month: that month moves no more
   levels than the pace (review focus 5).
6. **The move notice.** A base of 150 levels at 16 Psyche with Glass and Plastics 50% dear (§ 10 stage 3, the console
   can set the price): the feed notice "Extraplanetary Base Levels Moving" arrives in the second month of the move,
   once it has carried 8 levels (5% of 150), naming 16 Psyche, Ceres and Glass and Plastics, with the pace. No
   second notice while the move runs, none within a year of the last, none with the checkbox off and none for a
   move between two sites of one type. Weeks later, after the move has ended, the notice in the feed still names
   the same sites and good.
7. **A click's cost.** On a late save with a large base, a click on − or + doesn't hitch: the forecast behind the
   totals (up to 41 passes over the 41 places) runs once on the click, from the figures the last refresh stored.
8. **The Base Room cell names the next place.** The overview's Base Room cell's last line names the site the next
   level goes to (queued levels counted) in the overview's short names: "Ceres", "Near-Earth", "Valles Marineris"
   without "...". With built and queued levels at or past the room it reads "next at -75%" the moment levels are
   queued, before any refresh. The hover's second paragraph gives that site's Ground Type, Base Grade and profit a
   level a week, both concept links working, or past the room the −75% line; neither shows a raw key (the two
   `AddLocalizationIf` sub-keys). A click on − or + that changes where the next level goes changes the line at once.
9. **The room modifiers' descriptions.** Hover Extraplanetary Base Room in the Nation tab's modifiers: the
   description says the levels work at their sites' Base Grade where the Bases view puts them, not "the richest
   first".
10. **Switching off during a blockade.** With 150 levels at 16 Psyche, Ceres and Io and the checkbox on, blockade
    Psyche until its levels work elsewhere, then click − on Io: + at Ceres stays usable (the cuts the refresh stored,
    `sr_eb_switch_cut_<k>`), the unassigned row reads the 5 levels − freed, and the boxes' arrows show where the
    levels will sit once Psyche is freed. Lift the blockade: the levels come back to Psyche, every site reads its
    assignment with no arrow left, and "At our assignments: no levels left to move".
11. **Ticked back on mid-month.** With the checkbox off and a site that earns well more than another, tick it on
    after the first of the month: the move area reads "Levels start moving next month", not "No site with room
    earns ...", and the move starts on the first. The no-gain line, when it shows, wraps to two lines inside the
    column. Ticking either way ends a running move: it shows as the last move, never as the checkbox's.
12. **A country handed to the AI.** Switch the checkbox off, then `play` another country for a month: the first
    country's checkbox is back on (its levels move for the most profit again), and switching back finds it on.

## Extraplanetary Base ground types: the month and the readings (2026-11-21)

Where the levels work and what they make (ground types design §§ 2, 5, 8, 9.2, 9.6; `sr_ebase_generated.txt`,
`ebase_ground.py`). `test_ebase_assignment.py` runs the generated month against the model offline; these are what only
the game shows. Use a save under Full Colonies with In-Situ Resource Utilization, Asteroid Mining and two or three
colonies of different types (16 Psyche and Ceres are the design's example).

1. **The acceptance test (§ 2).** From the UI alone, with no console: say where your levels work, what the base makes
   of each good, and why it last moved. Note anything you had to guess.
2. **Two layers multiply.** With a base whose levels all work one site, its building's output tooltip for one good reads
   the method's figure × (1 + the Extraplanetary Base Room throughput) × (1 + that good's Extraplanetary Base Ground
   line), and the building shows the site's type's mix (at 16 Psyche alone: Glass and Plastics −91%). If the two add
   instead, profit at base prices is off a site's grade times its mix, and `ebase_mix` can't see it.
3. **A glut.** Let one good fall well below base price (or set it from the console) with a base of 150 levels or more:
   the checkbox moves levels one way at the pace and stops while the gap is still inside the margin. Watch two or
   three years for a move back. The model moves back once if a price closes only a tenth of its gap a month, so a
   back-and-forth here says the game's prices answer slower than assumed: note the price path.
4. **A blockade and its return.** Blockade a colony that holds levels: within a month they work elsewhere (or past the
   room), its box says why, its assignment is kept, and no notice of a move is posted. Lift it: they come back the
   next refresh, at once, not at the pace.
5. **The pace.** A base of 150 levels moves 4 a month. Build a level mid-month: the day-after refresh places it and
   moves nothing more that month.
6. **The logistics cuts.** On a base with Tethered Launch and Fusion Tugs at base prices, profit a level at a grade-0
   site reads about £21,650 on the Asteroid Mine (£7,250 without them), and a move needs about £1,083 a level more.
7. **Tick time.** On a late save with many AI bases, the first of the month is no slower than before this build
   (the wall clock of `docs/audits/late_game_performance.md`, "Reading the wall clock", against the same save on
   `main`).
8. **Solar System's line.** Under each site's name, "300 (+30%) Metallic" at 16 Psyche and "200 (+15%) Carbonaceous" at Ceres, and the resort room, fit without "...",
   in Solar System and in the colony target popup. The base room's hover gives its type's seven figures, each good
   named, no raw `$key$`.
9. **The Help page.** How Solar Colonization Works shows its Extraplanetary Bases topic under Simple and Full Colonies
   only, with a line per ground type and the checkbox's rule.

## The Resort Colony, a building of its own (#1948, 2026-11-21)

The Resort Colony method left the Extraplanetary Base for `building_space_resort`, whose levels work their own room
(20 in Earth orbit, each colony's `RESORTS` figure, 20 a staffed Off-World Resort level; each was half that until
the owner doubled them, 2026-11-28) best draw first, −75% past it. No self-check: the fill, the refresh and the building's throughput type are the base's, which work.

1. **It appears and is held to the room.** With Space Colonization, the Resort Colony is in the build list, and the
   base's production methods no longer list the Resort Colony. Under Simple or Full Colonies an AI government and
   private investors stop at the room (built and queued); your government builds past it.
2. **The draw.** Holding Tranquility Base with its room filled, the building's throughput breakdown shows Resort
   Colony Room at the average draw (+30% with 60 levels in Tranquility's 40 and Earth orbit's 20: +20%). One level
   past all of the room pulls it toward −75%. The overview's Resort Room cell reads built and queued against room,
   red past it, and "next at" the next level's draw.
3. **The module.** Before Space Colonization the Off-World Resort's + button is grayed with "We have Space
   Colonization". After it, a staffed level raises the colony's resort room by 20 within a month, on its page's
   Resort Room tile and in the overview.
4. **An old save.** A base still on the Resort Colony method (if a pre-#1948 save is at hand): note which method the
   engine gives it, and that the log names nothing about the missing method. *Answered in part (owner, 2026-11-26):
   the base swaps to another method of its group on the next weekly tick. Still open: which method it gets, and
   whether the log names it.*
5. **Solar System's line, with the room doubled** (2026-11-28). Under Valles Marineris, Hellas Planitia and Utopia
   Planitia the resort cell reads "100 (+25%)", "100 (+5%)" and "100 (+0%)" without "...", in Solar System and in the
   colony target popup; the slots cell before it, narrowed to one digit to make the room, still shows its Habitat cap
   (1 to 4) whole.

## The Resort Colony free of its state (#1953, 2026-11-22)

`sr_resort_state_refresh`, on each state's monthly pulse, takes the state's share of a Resort Colony's Tourism and Fine
Art output multipliers (the state's read less its owner's) back off the building as Off-World Hotels. Scope:
`docs/superpowers/specs/2026-11-22-colony-people-and-off-world-tourism-scope.md` § 2.

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN resort_state building=… state=… country=… share=… own=…` | once a game, at the monthly refresh of the first state whose last cancel was 40% or more either way, whose owner's own Tourism line is 30% or more either way (such as Multicultural with Guaranteed Liberties, or a secret police law), and whose share has moved 5 points or less since; read before the refresh strips the cancel (a month old) | `own`, the building's Tourism read less the state's plus last month's share, is −0.05 to +0.25 (0, or a company's +0.2): the state's read carries the country's lines, the building's read carries the state's, and Off-World Hotels reaches the building at its multiplier | `own` near `share` / 100: the cancel never reached the building. Near `country`: the state's read leaves the country's lines out, so the share double-counts them. Near minus `share` / 100: the building's read leaves the state's lines out, so read the output tooltip by hand (item 1) | the first: apply the pair from `every_scope_building = { limit = { is_building_type = building_space_resort } … }` in place of `b:building_space_resort`, as `sr_eb_apply_mix` does. The second: take the share as the state's read alone. The third: if the building's output tooltip still lists the state's lines, the engine applies them though the read leaves them out, and the cancel works; if it doesn't, the state's lines never reached the resort and the cancel must go |

1. **A big airport.** A Resort Colony in a state with a large Airport on its Airport or Spaceport method, at a world with its
   room free. The building's Tourism output breakdown lists the state's lines (Tourism Output, the Airport) and one
   Off-World Hotels line that takes their sum off, within a month of building it, so its Tourism comes to the
   method's line × throughput × (1 + the country's lines). The Tourism Industry in the same state keeps every line. The
   building's throughput still lists the Spaceport's +1% a staffed level.
2. **A polluted state.** A Resort Colony in a heavily polluted state (or one in turmoil) whose Tourism Industry makes
   no Tourism. The resort's Tourism is at par: the same as an identical Resort Colony in a clean state with no
   Airport. If it is far above par, the engine clamps the state's sum at −100% before it adds the building's line:
   cap the bonus at 100 units in `sr_resort_state_good` (scope § 2, "The clamp").
3. **Studios.** A Resort Colony in the state of a Sony Pictures Studios, Netflix Animation Studios, Nintendo
   Development Center or Universal Studios Hollywood: its Art and Entertainment breakdown shows the studio's line and
   an Off-World Hotels line that cancels it.

## Colony people limit modules (#1954 Part B, 2026-11-22)

Slots are gone: a colony takes as many modules as its people can crew, a crew being 10,000 people (5,000 with
Artificial General Intelligence), and only Habitats have a cap, past which each costs more with no top. Five
technologies add 10 points of Habitat room each. Settlers are an amount that halves and doubles, drawn from every
state by its people, and each takes 3 Launch Capacity that the Space Program buys. An Administration costs 25
authority a staffed level. Design: `docs/superpowers/specs/2026-11-22-colony-people-limit-modules-design.md`
(§ 13 for the engine questions). The self-checks are `emigration_batch` (§ Targets, colony fleets and settlers) and
`habitat_marker` (§ Colony management), both reworded for this design; read them a week after the first month.

Console: `event te_debug_space_race.3` (g fills our colonies to half their room, e sets settlers to 2,000 a month and
sends them) and `event te_debug_space_race.4` (b fills the stock, c queues one of each module, e lands them).

1. **Crews at a large colony.** A colony of 45,000 people with eight crewed levels: the Modules view's Crews reads
   7/4 (needed / available) in red, its hover says what a short crew costs and how to get more, and every crewed module runs at
   (4 + 1) ÷ 8, 62.5%, in the specialization's multiplier on the entry. The People view's Crews reads 7/4 in
   red, and the overview shows a Crews cell, "1 short". With Artificial General Intelligence the same
   colony reads 7/9, not red, and the cell goes.
1a. **The People view's Crews color** (owner, 2026-11-23). Crews used / available, colored by the crews left once
   the queue and every shipment land: at a colony of 50,000 people (5 crews) with five crewed levels (4 used) it
   reads 4/5 in green; queue one crewed module and it turns yellow, still 4/5, the moment the + button's crew
   line reads "No crew to spare"; queue a second and it turns red, still 4/5. Queuing a Habitat changes nothing.
   When the modules land the figure follows: 5/5 yellow, then 6/5 red.
2. **The + button's crew line.** At that colony the + button on a facility shows "No crew to spare" in red and
   still lets us queue; at a fully crewed colony with one crew to spare it reads "Needs a crew: this colony's people
   have one to spare", and after one more crewed module is queued it reads short; on a Habitat the line is absent.
   Under Full Colonies the colony's Defenses fire at its staffing: at half strength at 50%.
3. **The Habitat cap and its price.** At a 2-cap world with two Habitats, the Modules view's Habitats reads 2/2; the
   hover gives the people each holds, its share of the starting room (50% without the technologies, 100% with
   all five) and the next price, 200, then 300 for the one after. Once the next price passes the module stock's cap
   (the Fabrication hover) the Habitat's + button greys out with the price line crossed; with an Orbital Depot it
   goes on.
4. **Room from the technologies.** Research Nuclear Thermal Propulsion with a colony held: its tooltip lists
   +10% Habitat Room, and within a month each Habitat at our colonies holds 60% of the starting room (the colony's
   room rises by a tenth of its base a Habitat). Cede the colony to a country without it: its room doesn't fall.
5. **The settler bill at two amounts.** Set settlers to 4,000 a month (step 4): the People view's "Sent last month"
   reads 4,000 and "Launch Capacity a week" 2,769. The Space Program's Launch Capacity input breakdown has a Settler
   Launches line that adds about that much at full staff, and the same with modules built (the throughput term: if
   the line is off by the throughput, drop the throughput from `sr_emig_bill_divisor`). Step up to 32,000: the
   line grows eightfold. Set settlers Off: the line is gone within two months, also after the entry ends.
6. **Settlers from several states.** A country of three states, 4 million, 2 million and 100,000 people, at 32,000 a
   month: "Sent last month" reads 32,000 every month, and over a year the states lose about 256,000, 128,000 and
   6,000 (the census's emigrants by state), each within 500 of that, the small state a batch every few months. Strata: in the largest state, middle and lower pops each fall, spread over the
   state's pops, not one pop emptied (`kill_population_in_state` by stratum). A country of 1 million at 32,000 a
   month sends 10,000 (the 1% cap).
7. **An Administration's authority.** Build one at a fully crewed colony: the country's authority breakdown lists
   Off-World Administrations at 25 more authority cost; a second staffed level makes it 50; understaffed at 50%,
   25 for the two. An AI builds one only with 50 authority to spare.
8. **The two room modules at one world.** At a Mars colony with a Habitat and a Terraforming level, the colony's room
   is the base × (1 + share × Habitats + terraformed share). The Habitat comes down only while the people fit
   the room without it.
9. **The pick.** With no target set, Colony Fleets' destination prefers a 4-cap world over an otherwise equal
   2-cap one; the target line's hover gives the cap and the people and crews it holds at the cap at our share.
10. **The AI's settlers.** In an observer run a colony-holding AI with a positive income steps its settlers up while
    fabrication's 5% leaves room, and never past its colonies' free room; in default it sets them Off.

## Colony room from Space Colonization and Terraforming (2026-11-22)

No new self-check: the base room factor reads `country_sr_colony_room_add` through the holder's scope as
`habitat_marker` already checks for the Habitat share.

1. **Space Colonization.** Research it with a colony held: its tooltip lists +50% Space Colony Room, and within a month
   the People view's room at a world with no Habitats is 1.5 times the table's (Valles Marineris 75,000), each
   Habitat's people in the Modules view's hover half again as many, and Solar System's people at the cap for a
   world we don't hold the same.
2. **Terraforming.** Research it next: the room is double the table's (100,000 at Valles Marineris before any
   Habitat), and a Terraforming level's 4% a year is of that doubled room.
3. **A cession.** Cede the colony to a country with neither technology: its room doesn't fall the next month.

## Modules built only once they can go (2026-11-23)

The owner's rule (`sr_mq_head_ready`, `sr_mq_promote_ready`): a module for a world with launch windows is built
once its window is at most `sr_mod_build_lead_months` (1) off, so none waits for a window in a shipment slot, and
the first module further down the queue that can go, and that the stock covers, is built ahead of one that can't.
No self-check: every input is a variable or a script value the Next Module hover already shows. The console is
`event te_debug_space_race.4`.

1. **Mercury ahead of Mars.** Under Simple or Full Colonies, with chemical drives, a Mars window over a year off,
   and colonies at Mars and Mercury, queue a Mars module, then a Mercury module, with the stock covering both
   (option b). Next month the Mercury module is built (Shipments 1 / 0, then 0 / 1 once it leaves); the Mars
   module stays first in the queue, unbuilt. Next Module reads "in N mo", N the months until a month before the window, and its hover
   is Waiting for Its Window, with the price and the stock.
2. **The window comes.** Advance to a month before the Mars window: the Mars module is built (Shipments 1 / 0),
   leaves with the window, and Next Module moves to the following entry. With six or more Mars modules queued and
   the stock full, two are built each month from then until the window's second month, six in all, and the rest
   wait for the next window in the queue, not in a slot.
3. **The queue's order.** Queue Mars, Ceres, Mars, Mercury with neither window near: only Mercury is built, and the
   queue then reads Mars, Ceres, Mars in that order.
4. **An unpaid module doesn't jump.** With the stock below 100, queue Mars (window far) then Mercury: nothing is
   built until the stock reaches 100, then Mercury is.
5. **On hold.** Blockade Earth (Full Colonies): nothing is built, Next Module reads "on hold" in red and its hover
   says Earth is blockaded; the stock still fills. Lift it: building resumes. With only a Moon colony blockaded,
   its module waits first in the queue ("on hold", the Moon line) while a Mercury module behind it is built.
6. **Late game.** With a fusion torch or antimatter drive, every module is built in queue order as before: no
   window holds any.
7. **An older save.** Load a save with Mars modules waiting in slots: they leave at their window as before, and
   new Mars modules stay in the queue.

## The Colonies window and the system map (2026-11-23)

The owner's two asks: a colony opens in a window of its own (`te_sr_colony_popup`, `te_popup` = `sr_colony`), and
the Solar System tab opens on a map (`te_sr_system_map`). Both were drawn in the running game on the owner's
2031 save through `game_qa gui-show` (the map, the list under a picked location, the window's content on three
colonies), and the window was also shot in its popup host with its keys set by a probe widget. No click was
made then: the harness clicked only the engine's tool windows. **Clicked on 2026-11-24** (a copy of the owner's save
of December 2032, 20 colonies; the HUD may be clicked since that day, `game-qa` skill): the parts of steps 1, 2,
3, 6, 7 and 8 marked *seen* below. The rest is still for a hand. No self-check:
nothing here is script. **Fallback** if the window misbehaves: the page drawn inline under the Colonies list
again (`te_sr_colony_pages` in `te_sr_sec_colonies`, shown on `sr_colony_focus`).

1. **A base opens its window.** *(Seen 2026-11-24: a colony's name opened Our Colonies on it over a dimmed screen, with no scrollbar at 2160p and scale 1.5, and the close button closed it and left the tab as it was. Not tried: the arrow, Escape, a click outside.)* Under Simple or Full Colonies, on the Colonies tab (journal entry and the
   Timeline Extended window), click a colony's name, then another colony's arrow: each opens Our Colonies on that
   colony, over a dimmed screen, with no scrollbar on a 1080p screen at scale 1 for a world without Terraforming.
   Escape, the close button and a click outside each close it and leave the panel behind as it was.
2. **The list in the window.** *(Seen 2026-11-24: twenty colonies in the tab's order, the one shown greyed; clicking Valles Marineris changed the page and kept the window. Not tried: a name's hover.)* Every colony we hold is on a button at the left, in the Colonies tab's order; the
   one shown is greyed. Click another: the page changes, the window stays. A name's hover is the site's
   specializations with their effects, as in the Colonies list (it reads the player's country, which the popup
   gives itself).
3. **The page works.** *(Seen 2026-11-24: + on Spaceport queued one, the row reading "0 +1" and the overview's Modules "12 queued" from 11. Not tried: the other controls.)* In the window, change a colony's settler priority, queue a module with +, dismantle one
   with −, assign an Extraplanetary Base level with the Bases + (In-Situ Resource Utilization), press Revoke on a
   chartered colony and cancel the question: each acts as it did on the old page, and each greyed button gives its
   reason on hover.
4. **A colony lost under the window.** Open the window on our first colony (Shackleton Crater, if we hold it),
   close it, run `event te_debug_space_race.2` and give that colony away (option c), then open the window from
   another colony: the first is gone from the list. The line "This colony is no longer ours. Choose another from
   the list." takes a page's place only when a colony is lost while the window is on it, which the console can't
   do from under a popup; note it if it is ever seen.
5. **Races Only.** Under Races Only the colonies' names are plain text with no arrow, and nothing opens.
6. **The map reads.** *(Seen 2026-11-24: the Sun, nine icons with their names on two lines by turns, none cut; gold markers for ours, rings for unclaimed, the dashed ring on our target; the key under it. No other power's flag or inbound dart was on that save.)* On the Solar System tab the map shows the Sun, nine icons on their orbits with their
   names on two lines by turns (none cut, none overlapping), and a marker a site: gold for ours, a flag for
   another power's, a ring for unclaimed, a gold ring round our target, a small dart on a site a colony fleet is
   flying to. The key under the map names them. A flag here is small (20 × 13): say if it can't be told apart.
7. **A location filters the list.** *(Seen 2026-11-24: clicking Mars framed its icon, the list showed Mars's five sites alone and the button read All locations. Not tried: clicking it again, a marker that isn't ours.)* Click a location's icon or name: its icon is framed, the list below shows
   that location's sites alone, every one, the count line reads "One location's sites shown" and the button
   reads All locations. Click the same location again, or All locations: the usual list returns, with Show all
   as before. Click a marker that isn't ours: the same, for its location.
8. **Our marker opens the window.** *(Seen 2026-11-24: a gold marker under the Moon opened Our Colonies on Shackleton Crater. Not tried: the list's arrow, the target popup.)* Click a gold marker: Our Colonies opens on that colony. The same from the
   arrow beside "Ours" in the list. The colony target popup's list shows no arrow.
9. **Another country's panel** (National Info, Space Race tab): the map and the window are the player's own;
   another country's column shows neither, as before.

## Marines and Defenses shared on the Moon and Mars (2026-11-24)

The owner's rule (`space_race.md`, *Shared worlds*): a holder's marines at any of its colonies on the Moon or Mars
defend each of them, its Defenses there fire for each in full and add half their hardness, the fire falls with
the attacked colony's integrity and is split over every colony of the holder's there under attack, and Land and
Embark work on the Moon. No self-check: the one comparison it adds (`sr_site_shares`, two holders through
`global_var:… ?= { global_var:… ?= this }`) is built of reads the panel already shows, and the Defenses view and
the target hover show the shared figures. Full Colonies throughout; the console is `event te_debug_space_race.6`.

1. **Land on the Moon.** Hold two lunar colonies and keep a fleet with marines at Earth: Land is enabled, its
   popup lists both, and the marines land at the one picked, and the Defenses view's Marines shows the same figure on both rows. Embark
   takes them back aboard. Next month the fleet has refilled at Earth (the known gap: Land again and the Moon's
   marines keep growing; a garrison cost is to come).
2. **A shared garrison.** With two battalions landed at one lunar colony, answer an autonomy demand at the other
   with Send a garrison: the garrison takes effect the next month, with no fleet sent.
3. **The seizure.** As an enemy holding Earth orbit, close in on our undefended lunar colony while our marines
   stand at the other: the target hover's marines are ours from both, Seize waits for more than those and the
   militia, and once it lands our marines at the other colony are gone too (its Defenses view row reads 0).
4. **Shared Defenses on Mars.** Hold two Mars colonies, four Defenses levels at one and none at the other, and
   close in on the undefended one with a siege fleet: the battle report counts losses to Defenses, and its
   integrity falls by about 10 × the fleet's fire on defenses ÷ 150 a month (hardness 50 + 50 × 4 × 0.5), not ÷ 50.
5. **Two attacks at once.** Close in on both Mars colonies with two fleets of the same strength: each loses about
   half what one fleet alone loses to the Defenses.
6. **An occupied colony shares nothing.** Once one Mars colony is occupied, the other's Defenses view shows only its
   own marines, and the occupied one's Defenses fire for no one.
7. **The AI.** An AI with a lunar colony that orders a garrison lands two battalions from a fleet at Earth within a
   month; an AI fleet coming home to Earth with no lunar garrison due keeps its marines aboard.

## Marines: Land and Embark pick the colony and the amount (2026-11-24)

Mercury and Venus share a fleet location, and Land put every marine aboard at Venus whenever we held both, while
Embark took from Venus first (the owner, 2026-11-24). Land and Embark now open a Marines popup listing our colonies at
the fleet's location, with an amount (`space_race.md`, *Marines*). No self-check: every button passes two scopes
(`op`, and `pick` a world or a step code), as the target popup's Target and the colony module buttons do; the
amount's keys are Transfer's `click_modifiers` with no third scope (Transfer's own, three scopes, are still
unproven: `xfer_step_scope`). Full Colonies; the console is `event te_debug_space_race.6`.

1. **The label.** Choose Mercury & Venus in Fleet Destination: the fleet card's button reads "Merc./Venus", and
   "→ Merc./Venus" in flight, neither cut off. The popup's Where column shows "Merc./Venus" in full.
2. **Land opens it.** Hold Mercury and Venus, with a fleet carrying marines at their location: Land on the card
   opens Marines with "Marines aboard" (aboard / the carriers' room), "Marines to move" at every marine aboard, and a
   row each for Mercury and Venus with our marines at each.
3. **Split them.** Click − on the amount (Shift, Ctrl and Alt take 10, 100 and 1,000; right-click none; + adds,
   right-click the most): it moves and stops at none and at the most. Set it to half, Land on Mercury: half the
   marines go there, the popup stays open, and Land on Venus puts down up to the amount of the rest. The card's
   Marines bar falls by each.
4. **Embark from one.** Close it, then Embark on the card: the amount starts at the room aboard. Embark on
   Venus's row takes up to the amount of ours there, no more than the carriers hold; Mercury's stay. Embark greys,
   with its reason, on a colony with none of ours, and once the carriers are full.
5. **Due.** Answer a demand for self-government at Mercury with a garrison: its row reads Due (yellow), and the
   hover says two battalions within a year. Land two there: the garrison takes effect the next month.
6. **Only ours, not occupied.** An enemy occupies one of our colonies at a location: its row is gone. A free
   colony or another power's has no row.
7. **A fleet that is gone.** Leave Marines open, unpaused, while the fleet is destroyed in battle: the popup reads
   "This fleet has left, or is gone."
8. **The AI.** An AI with a garrison due still lands every marine aboard at that colony (it never sees the popup).

## Space forces personnel (2026-11-24)

Design: `docs/superpowers/specs/2026-11-24-space-forces-personnel-design.md` (the scope, PR #1990, beside it). Full
Colonies. Spacers are the mod's first pop type, so the first two rows ask whether the engine takes one at all. The
console's `event te_debug_space_race.6` option n fills the reserve (100 of each role: 50,000 personnel at 100 a
point), o puts an enemy fleet at Earth.

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN pers_pop_type country=… spacers=… occupancy=… personnel=… want=…` | once a game, three months after a country first has a Space Forces Base of a level or more (whatever its staff; later while the base is under half staff) | the base's state holds Spacers and its `state_sr_space_personnel_add` is 0.75 to 1.5 times 1,000 × the base's levels × its occupancy (throughput moves it: −10% unincorporated, +10% a new capital, economies of scale) | `spacers=0`: the pop type, or its social class (`te_spacers_classes.txt`, one per hierarchy), doesn't load or doesn't hire (also look for a pop-type or social-class error in `error.log`); `personnel` off `want`: the method's workforce-scaled state modifier doesn't reach the state as the batteries' does | for the pop type, put Spacers in vanilla's lower class by a full restatement of `lower_class` (and the caste and Edo classes) rather than classes of their own; for the figure, compute capacity in script, level × occupancy × 1,000 by `is_building_type`, as `ship_construction`'s fallback does |
| `TE_SELF_CHECK OK/BROKEN pers_kill country=… spacers_before=… killed=… spacers_day_on=…` | once a game, a day after the first state kills a hundred or more Spacers (`space_race_events.140`) | the state's Spacers fell by at least half the count: `kill_population_in_state` with `pop_type = spacers` takes the mod's pop type | they fell by less. A weekly hire falling in that day can refill a small kill (about one game in seven), so a BROKEN with the base's staff up since wants a second game before the fallback | kill by `every_scope_pop = { limit = { is_pop_type = spacers } }` with `kill_population_percent` scaled to the count |
| `TE_SR_PERS migrate country=… in_service=… grace_until_month=…` | once a country, its first fleets month, only when an old save's fleets need more personnel than its bases give | (a record, not a check) the levels the migration built, in Space Command's state or the capital | | |
| `TE_SR_PERS migrate_modules country=… need=… grace_until_month=…` | once a save, its first month under Full Colonies after the colony modules took personnel (2026-11-25), for each country holding a Spaceport, Defenses, Black Site, Training Ground or Nuclear Command Center whose need tops its bases' capacity | (a record, not a check) the levels it built beyond those built and queued, in Space Command's state or the capital | | |

1. **The building.** With Cislunar Infrastructure under Full Colonies, the build menu offers Space Forces Base in any
   state, as a government building only. Its method's tooltip shows 1,000 Spacers a level and +1,000 Space Forces
   Personnel. A level hires Spacers (the state's pops list shows them, with the placeholder soldiers icon), and the
   Map Room's Classes row has Spacers' two maps.
2. **The cells.** Space Command's Personnel cell reads in service of capacity (the base's 1,000 a staffed level);
   its hover gives crews, marines aboard, marines landed and the year's dead. Crewed reads 100% while capacity
   covers what's in service.
3. **The launch gate.** With one staffed base level (1,000 personnel) and no fleets, fill the reserve (option n, 500
   points): Launch sends up 10 points, 2% of each role, and the rest waits. The Reserve hover names the
   points awaiting crews. With no room, Launch greys with its reason, and Auto launches nothing.
4. **Marines.** At Earth, a fleet with empty carrier room takes on marines only as far as personnel are spare (a
   battalion for each 1,000). Click Hulls (it reads Marines) and fill the reserve again: next month the marines
   fill before the reserve goes up.
5. **Short of personnel.** Demolish the base level: Crewed falls below 100%, Space Fleets shows the note, and the
   battle report's losses dealt read lower by the share.
6. **The dead.** Lose ships in a battle: the battle report names the people killed, and the base's state's
   Spacers fall by about that many (whole hundreds) at the month's end. The census's War Dead map counts them.
7. **The toll.** Seize an enemy colony with marines to spare: the marines aboard fall by the garrison need plus
   half again, the landed garrison is the need plus one, and the occupation notice names the dead.
8. **An old save.** Load a save from before this change with fleets: in the first month Space Forces Base levels
   appear in Space Command's state (`TE_SR_PERS migrate`), and Crewed reads 100% for six months while they hire.
9. **The AI.** In an observer run, AI fleet powers build Space Forces Bases (the census or the Map Room's Spacers
   map shows where), and none pauses Space Command for crews while it has a base level queued.
10. **Colony modules take personnel** (the owner, 2026-11-25). Under Full Colonies, with a colony and one staffed
    base level, hover a Black Site's + button: the personnel line says 1,000 are spare; queue two and the next
    hover says none are spare. Once one lands, the Personnel cell's in service rises by 1,000 and its hover names
    the module levels. With two landed and the one level, Crewed reads about 50% and the Nation tab's Off-World
    Black Sites reads +1 intelligence capacity, two levels at half.
11. **A holder with no fleet.** In a country with a colony, a Training Ground and no Space Forces Base or Space
    Command, Crewed reads 0% a month after it lands and Off-World Training Grounds is gone from the Nation tab; build
    a base level and both come back as it hires.
12. **Spaceport repairs.** With a damaged fleet docked at a colony Spaceport and Crewed at 50%, the fleet repairs
    about 5% of its damage a month a level instead of 10%, and still refills and refits.
13. **An old save's modules.** Load a save from before 2026-11-25 with colony Black Sites or Defenses: in the first
    month base levels appear (`TE_SR_PERS migrate_modules`) and Crewed holds at 100% for six months.
14. **The Research Station.** A staffed Research Station shows Off-World Research Stations on the Nation tab with
    +25 innovation cap and no research speed; the cap in the innovation tooltip rises by 25.
15. **A base before fleets.** With Cislunar Infrastructure and without Space Militarization, build a Space Forces
    Base and an Orbital Yard: Space Command's Built a month stays 0 and the reserve stays empty. With Space
    Militarization and still no Space Command it stays 0; once a Space Command level stands in a state we control,
    Built a month adds the yards' 0.5 a staffed level. A Black Site queued at the same time is staffed once the
    base hires.

## A giant planet's moons share an Orbital Yard, not their Defenses (2026-11-25)

The owner: "all Jupiter's moons, Saturn's moons, etc. should count as the same place - i.e. you can build modules on
Europa with an Orbital Yard on Io. This should not be the case for defenses, though." (`space_race.md`, *Colony
modules*: *Shipments*; `gen_solar_sites.yard_mates`). No self-check: the reach is the generated
`sr_site_yard_builds_<key>`, read by the build loop the section below already checks. What only the game shows is the
hovers. The console is `event te_debug_space_race.4` (modules).

1. **Across the moons.** Hold Io with a staffed Orbital Yard level and Europa with none, and queue a module for
   Europa: the next module reads "in N mo", its hover is *Built at an Orbital Yard*, and at the pulse it is installed
   at once, with no shipment and no wait for Jupiter's window. Titan's yard builds for Rhea the same way; Ceres's
   doesn't build for Vesta, nor Pluto-Charon's for Eris.
2. **The hovers.** Europa's Yard cell names Jupiter's six moons and says the moons' Defenses and marines stay apart;
   Saturn's, Uranus's and Neptune's moons name theirs; Ceres's reads "this colony", Valles Marineris's Mars and
   Shackleton's the Moon. The Yard column's header gives the whole rule, and the Defenses hover says each moon of a
   giant planet is defended by its own. None shows a raw `$je_space_race_widget_mod_yard_tt_…$` key (the hovers are
   spliced from three fragments). The yard's queue button names the reach too.
3. **Defenses stay apart.** Under Full Colonies, with Defenses and marines at Io and none at Europa, close in on
   Europa: Io's Defenses don't fire for it, and Io's marines don't count toward Europa's garrison (the target
   hover's Defenses and marines are Europa's alone).
4. **The yard's moon lost.** Occupy Io: Europa's next module ships from Earth again (it waits for a slot and the
   window).

## Orbital Yards build on their world; Cultural Centers draw guests; Training Grounds train marines (2026-11-24)

Three facility changes the owner asked for together (`space_race.md`, *Colony modules*: *Shipments*, *Facilities*,
*Resort Colony room*; *Seizure, occupation, destruction*). No self-check: none rests on an engine behaviour nobody has
seen. The build loop is script logic (`test_solar_sites.py`), the draw a script value the fill already multiplies, and
the marines' weight a script value in two comparisons. Simple or Full Colonies; the marine rows need Full. The console
is `event te_debug_space_race.4` (modules) and `.6` (marines).

1. **A yard builds for its world.** Hold Ceres with an Orbital Yard level and queue two modules there, first in the
   queue: the next module reads "in N mo" and its hover is *Built at an Orbital Yard*. At the next month's pulse both
   are built and installed at once (the Ceres levels rise, the Shipments count doesn't), each for 100 points from the
   stock. Queued behind a Mars module whose window is months off, they are built ahead of it the same way (the row
   shows the Mars module's *Waiting for Its Window* until then: the queue reorders only at the pulse).
2. **On top of the four.** With a stock of 1,000 or more, queue four modules for Mercury, then three for a colony
   whose world has our yard: all seven are built in one month (four into shipment slots, three installed at once).
   Queue the yard's three first instead: the same seven.
3. **A shared world.** A yard at Valles Marineris builds for our Olympus Mons too (the Moon's six sites the same);
   since 2026-11-25 one at Europa builds for our Ganymede too (the next section).
4. **A blockade.** Blockade Earth: Mercury's modules wait ("on hold"), the yard world's are still built from the
   stock, except the Moon's (its colonies are blockaded while Earth is). Lose the launch site under Full Colonies:
   Mercury's read "stopped", and the yard world's are built while the stock lasts (the month adds no points). A
   hostile fleet blockading the yard's own world stops it: that
   world's modules go back to shipping (they wait for a slot and the window), and so do they when the yard's colony
   is occupied.
5. **No yard, no change.** Dismantle the yard (its level comes down after a year): the world's next module ships
   again.
6. **Cultural Center draw.** At Valles Marineris (+25% Resort Draw), build a Cultural Center: its Solar System line
   and its page's Resort Room tile read +26% once the level is staffed, +27% with two. With Resort Colony levels
   filling Valles Marineris's room, Resort Colony Room's average and the overview's next-level draw rise by about
   the same share. A colony short of crews adds its staffing share (a level at half staffing reads +25.5, shown +26
   or +25).
7. **Training Grounds weigh marines.** With full crews and five staffed Training Ground levels (+25%), close in on
   an enemy colony with an untrained garrison of 4 and militia 1: the need is 5 and the toll 2.5, so the seizure
   needs more than 7.5. Six of our battalions (7.5 weighed) aren't enough, seven (8.75) seize it: 6.8 battalions are
   spent, 2,000 Spacers die (the toll over our weight) and 4.8 battalions land. Untrained, it takes eight, and 2,500
   die. The other way, give the defender the five levels (need 6, toll 3): our untrained nine battalions don't take
   it, ten do.
8. **The AI.** An AI with Training Grounds closes in with fewer battalions than one without, against the same
   garrison; one facing a trained garrison waits for more.

## Module queue alerts on the top bar (2026-11-25)

Two alerts, `sr_module_queue_empty` and `sr_module_stock_full` (`common/alert_types/te_space_race_alerts.txt`), the
mod's first. The console is `event te_debug_space_race.4`: option b fills the stock to its cap, option c queues one of
each module at our first colony.

1. **The file loads.** Under Simple or Full Colonies, holding a colony, with Orbital Assembly running and nothing
   queued, a green round alert with vanilla's hammer shows, "No Colony Modules Queued". Its hover gives the month's
   points and the stock against its cap, and the hint names the Modules view of the Colonies section in Solar System
   Colonization. If no alert shows at all, the engine did not read a mod file in `common/alert_types/` beside
   vanilla's `00_alert_types.txt`: the fallback is a copy of vanilla's file under the same name with the two alerts
   added, which then has to follow every vanilla patch.
2. **The stock full.** Option b: the green alert gives way to a yellow one with vanilla's crate, "Colony Module Stock
   Full", whose hover gives the cap and the points lost each month. The overview's Modules cell reads a red "Queue
   empty" at the same time.
3. **Queueing ends both.** Option c, or one module queued by hand: whichever alert showed goes at once.
4. **The click** opens the Journal.
5. **The switches.** The game's alert settings list "Colony Module Queue Empty" and "Colony Module Stock Full";
   switching one off hides it.
6. **Neither shows** with No Module Fabrication and no Orbital Yard or Mass Driver, with no colony held, or under
   Races Only. The text shows no raw key and no stray `[`, and "Colony Module" in the name and the description opens
   the concept on hover.

## The Fleets window (2026-11-25)

The owner's ask: "space fleets [should] have their own 'details' type popout window, like bases/colonies have now"
(`te_sr_fleet_popup`, up on the client-side `sr_fleet_focus`; `mod_systems/space_race.md`, "The Fleets window").
**Seen and clicked on 2026-11-25** in a `game_qa` session on a copy of the owner's save of June 2043 (the United
States under Full Colonies, two fleets at Earth), with three test fleets added by a setup (one damaged at Mars, one
in flight to Jupiter, one fresh at Earth); 3840 × 2160 at scale 1.5: the parts marked *seen* below. Two more
sessions, each launched on the files as they then stood (the last after the review's fixes), logged no line naming
them in `error.log`; a fourth, for the banner the owner then asked for, the same. The rest is for a hand. No self-check: nothing here changes what script does. **Fallback** if the window misbehaves under a
picker: put the window on `te_popup` like the Colonies window (`sr_fleet`), and have each picker's close and choice
set `te_popup` back to it.

1. **A card opens the window.** *(Seen: the arrow on fleet I's card, on the Fleets tab of the Timeline Extended
   window's side panel, opened Our Fleets on Fleet I over a dimmed screen, with no scrollbar. Not tried: the journal
   entry's own card, a rolled-up card's arrow.)* Each fleet's card has vanilla's go-to arrow left of the button that
   rolls it up; its hover says what opens. Rolled up, the card still shows the arrow, and its strength is not cut
   ("9999/9999" fits).
2. **The list.** *(Seen: six fleets in slot order with number, world, place and strength, the one shown greyed;
   a click on IX changed the page and kept the window; "→ Jupiter" with Jupiter's icon for the fleet in flight.)*
   A row's hover is the fleet's ships, each role of its full number.
3. **The page reads.** *(Seen, on a fleet at Mars, one at Earth and one in flight: the fleet banner across the
   top at its full size, a different picture for each of four fleets on four drives (the owner's antimatter fleets,
   and test fleets set to torch, fusion and chemical), each matching its Drive tile; Ships as six tiles with each
   role now of full, Condition's four bars and four tiles, Orders with a caption a line, Locations under it; in
   flight the track under the head and "In flight. It takes orders once it lands." for the orders; at Earth no
   Posture or Target line. Hovers seen: a role's tile, Fire on Fleets, Fire on Defenses, Dock, Repair a Month,
   the km/s bar, the trip's line white and red. Not
   seen: a refit in the Drive tile, a target with intelligence, the two notes above the page.)* The Mars
   fleet's Dock read "None here" with 0% repair, the Earth fleets' "Earth" with 20%.
4. **The trip.** *(Seen: "Months: 2, propellant: 1273.0 km/s" under Saturn, the figure red for a fleet carrying
   22 km/s, and Go greyed; for the owner's fleet I, which carries 6,316, the figure white and Go lit.)*
5. **A picker opens over the window and comes back to it.** *(Seen: the destination button opened Fleet Destination
   over the dimmed window, whose own close button was gone; Choose on Saturn closed the picker and the window read
   Saturn; Transfer opened Transfer, and its Transfer made fleet III of half of IX, the list reading 6 / 9 at once;
   Land opened Marines, and a click outside it closed Marines alone. Not tried: the target picker (no hostile site
   on that save), and **Escape with a picker up**, which should close the picker alone and, pressed again, the
   window: the window's close button is hidden under a picker on the assumption that a hidden button takes no
   shortcut. If Escape closes both at once, or the window first, say so.)*
6. **Orders act.** *(Seen: Station on a fleet standing off set its posture, `sr_disp_fl_7_posture` 2 then 1, the
   lit choice moving. Not tried: Go, Seize / Destroy, Close in, Interdict.)* Every greyed button gives its reason on
   hover, as on the card.
7. **Closing.** *(Seen: the close button closed the window and left the tab behind as it was. Not tried: Escape,
   a click outside with no picker up.)*
8. **A fleet lost under the window.** Transfer all of the fleet shown into another fleet: the page gives way to
   "This fleet is gone. Choose another from the list.", and its row leaves the list. With no fleet left at all
   (the console: clear every slot with the window open) the window reads "We have no fleets. A Space Command builds
   the first at Earth." over an empty list.
9. **Another country's panel** (National Info, Space Race tab) shows no fleets and no arrow, as before.

## The colonies' costs as Launch Capacity (2026-11-25)

Module upkeep, free colony supply, colonial garrisons, a strike settlement and dome breach repairs are each a flat
Launch Capacity a week, on the Space Program building, and no longer its throughput nor a share of its base
(`docs/systems/mod_systems/space_race.md` § *The colonies' costs*). Simple or Full Colonies. No self-check line: a good's
input mult added to a building at runtime was seen working (Space Command's old upkeep), and how a building's input sums
its throughput and its mults can't be read from script, only from the tooltip (items 1 and 2).

1. **The line.** Holding colonies with 12 module levels past each one's first, the Space Program's Launch Capacity input
   tooltip shows Colony Modules, adding 1,200 Launch Capacity a week at full staff: its +% is 1,200 ÷ (the methods'
   listed Launch Capacity × (1 + the programme's throughput)), +12% on Solar Colonization alone, unfunded. The Modules
   view's Upkeep row reads 1,200. **Fallback** if the line is missing: the multiplier didn't reach the building through
   the local variable; carry it as `root.var:`, as the settlers' bill does.
2. **Neither funding nor the mission raises it.** Note the Launch Capacity the line adds, then fund the running
   milestone one level up: a month later the line's +% has fallen and the Launch Capacity it adds is the same. Switch
   the mission (Solar Colonization to Deep Space Exploration): the +% falls to about a fifth and the Launch Capacity is
   the same. **Fallback** if funding raised it: the engine doesn't multiply a runtime input mult by throughput, so drop
   `sr_program_throughput_factor` from `sr_emig_bill_divisor`, which Settler Launches shares (item 8 shows it too).
3. **No output.** With fabrication running, queue modules: Colony Module Fabrication per Month doesn't rise as levels land
   (until 2026-11-25 each level raised it 1%), nor do the programme's innovation, prestige and pace.
4. **Garrison, supply.** Garrison a colony (`.94`): Colonial Garrisons joins the line at 200 Launch Capacity a week.
   Supply a free colony: Free Colony Supply at 300. The tooltips of both choices and the Autonomy view's hovers say so.
5. **The strike and the breach.** Fire `space_race_events.96` and meet the demands: next month Colony Strike Settlement
   (500 a week) is on the line, and stays 36 months (`sr_strike_settlement_months` counts down in the console's
   variables). `.97`'s Rebuild at once: Dome Breach Repairs, 1,000 a week, 12 months.
6. **A rebuilt programme.** Demolish the Space Program and build it again: within a month the lines are back.
7. **The AI.** In an observer run, an AI colony power's mission matches its budget: no program stepped down by a bill
   the budget didn't see (every `sr_ai_mission_bill_*` adds `sr_ccost_lc_now`).
8. **The settlers.** With settlers and modules both billed, Settler Launches and Colony Modules sit on the same input
   and the People view's Launch Capacity a week matches what Settler Launches adds.

## A colony held by force (2026-11-25)

Under Full Colonies a colony at 100 autonomy is held by our marines there, losing battalions each month, and declares
itself free only when they fall short; on the Moon and Mars every colony of ours held there declares together
(`docs/systems/mod_systems/space_race.md` § *A colony held by force*). The engine facts it rests on each have a use in
the mod already (`law_stance` in interest group scope in `zz_te_party_join_weights.txt`, an interest group modifier at
a multiplier in `un_regime_effects.txt`, `add_radicals` with `interest_group = scope:` in
`amendment_petition_events.txt`), so there is no self-check line. The console is `event te_debug_space_race.5`, option
i (our first colony's autonomy to 100).

1. **The hold.** A colony of 1,000 people or more, two marine battalions landed there, at war (so its terms reach
   1 or more), then option i: next month its autonomy reads 100, its row in the Autonomy view reads Held, the page
   "Held: N months", and "<World> Rises Against Us" (`.114`) arrives. Its hover gives our marines, the need and
   the loss a month.
2. **The losses.** Month by month the colony's marines (the Defenses view) fall by the hover's loss. In the interest
   group panel, each group that disapproves of Colonial Exploitation shows Colonies Held by Force at −2 approval, a
   strongly disapproving one −4, and its radicals rise as battalions are lost. Change the Free Speech law: the figure
   becomes −3 under Protected Speech, −1.5 under Censorship, −1 under Outlawed Dissent.
3. **The overrun.** Let the marines run below the need: the colony declares itself free, "<World> Declares Itself
   Free" with the overrun description, and the option's hover gives the battalions lost.
4. **A world rising together.** Two Mars colonies held by force, then embark most of the marines: both declare in the
   same month, "Our Martian Colonies Break Away", the joint council's flavor, and a colony of ours on Mars still under
   100 keeps its marines.
5. **Let it go.** At `.114`, option b: the colony is free, ties 50, and its marines are aboard our first fleet at Earth
   (or leave service with none there).
6. **The hold ends.** Make peace with the colony's terms back under 1: within a few months its autonomy falls under
   100, the row reads its charter or garrison again, and Colonies Held by Force leaves the interest groups a month later.
7. **No militia for us.** A seizure of a colony held by force needs more than half again its marines alone, not its
   militia too (`sr_site_garrison_need_<key>`).
8. **The AI.** In an observer run with Full Colonies and an AI colony at war, an AI fleet lands marines at a colony it
   holds by force once the hold has under a year left.
9. **Simple Colonies.** Option i under Simple Colonies: next month the colony declares itself free, no hold.


## Colonies Held counts worlds (2026-11-25)

Fix for #2054: the overview's Colonies cell, Colonies Held above the Colonies list and the count over the Colonies
window's list read `sr_disp_colonies_held`, which summed a value for each of a world's two specializations, so a world
whose modules had raised both counted twice ("41 of 40 held"). It now adds 1 for each world where either is held.
Simple or Full Colonies, with Colony Modules.

1. **Both specializations raised.** On a colony with one specialization at level 1 or more, raise the other with a
   module until both read a level. Colonies Held, the overview's Colonies cell and the Colonies window's count do not
   move, and read the number of colonies in the list: `read sr_disp_colonies_held` equals the rows shown, and never
   passes `sr_sites_world_count` (40).

## The AI queues a Mining Complex when its base room is full (#1952, 2026-11-27)

Fix for #1952: the AI's module plan (`sr_mod_ai_plan_<key>`) queued a Mining Complex only while the country's built
Extraplanetary Base levels exceeded its room, which building never brings about: an AI government's and every
investor's base stop at the room, queued levels counted (`sr_ebase_has_room`). It now asks for one once the room is
full, queued levels counted, as the Off-World Resort's line does (#1948). Simple or Full Colonies, with Colony Modules.

1. **AI colony holders grow their room.** In an observer run past In-Situ Resource Utilization, take an AI that
   holds a colony and whose bases fill its room (as that country, `read sr_ebase_queued_levels` at or above
   `read sr_ebase_room_total`). At its next yearly review it queues a Mining Complex instead of a Research Station,
   once the colony's crews can run it. Once the complex is staffed, the room has risen by 50 a level
   (`sr_mod_mine_room`) and the AI builds bases into it. Count the AI's modules by type against an earlier run:
   more Mining Complexes and fewer Research Stations where the room was full, and no change where it was not.
