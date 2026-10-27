# Solar System Colonization: contested colonies, population and bases — scope

Drafted 2026-10-25 from the owner's brief: colonies can be contested, captured or
destroyed; colonies hold people taken from Earth; colonies can be built up with
modules; space fleets and marines; anything else that fits. Revised the same day
through three rounds of the owner's answers (§ Decisions). This is a scoping
document, a menu with a build order, not yet a design. Slices 0 and 1 are built
(`docs/superpowers/specs/2026-10-25-solar-colonization-holders-and-cession-design.md`), slices 2 and
3 (`docs/superpowers/specs/2026-10-25-solar-colonization-population-and-transit-design.md`), slice
4 (`docs/superpowers/specs/2026-10-25-solar-colonization-modules-and-bases-design.md`), and slice 5
(`docs/superpowers/specs/2026-10-26-solar-colonization-free-colonies-design.md`). Slice 6, the
fleets phase, is designed in four parts, 6a to 6d
(`2026-10-26-solar-colonization-fleets-design.md`, with its plan
`../plans/2026-10-26-solar-colonization-fleets.md`), from the fifth round of
§ 11. Read `docs/systems/mod_systems.md` § Space Race and
`docs/player_guide/16-space.md` § Colonizing the solar system first; this
document assumes both.

## Decisions (owner, 2026-10-25)

**Holding and contest**

- **A dead holder's colonies pass to the owner of its last capital**, for the
  first version, under every setting but off (races only included). Later they
  may become **free colonies** by default, perhaps under the UN (§ 6.5).
- **Cession by treaty, one article per body at least**; better, one article that
  picks the colony, if hidden per-site building types can serve as its input
  (§ 6.1). Otherwise the receiver picks the ceded sites.
- **An occupied colony goes back at the peace unless a cession is enforced**, as
  occupied land does (§ 6.3).
- **A blockade needs only to beat the enemy's mobile forces, not the colony's
  defences.** The blockader stands off, out of the defences' reach, close enough
  to intercept anything coming or going (§ 6.2).
- **Interdiction in peace: yes** (§ 6.2).
- **Destroying a colony is allowed**, at a price in infamy, UN standing and years
  ruined, and later in the autonomy of the destroyer's own colonies. It is easier
  than capture: it is easier to throw something fast at a colony than to land
  marines on it (§ 6.3).
- **Free colonies wait and trade, at first** (§ 6.5).
- **Covert operations, colonies breaking away, abandonment and an outer-space
  convention against seizure are in** (§§ 6.4–6.6).
- **Interplanetary Trade Networks** is replaced, or given to every colony holder
  (D2, open between the two).

**Fleets**

- **Fleets are objects, not one national score**: numbers, a location and a
  timer. A fleet is at a location or in transit with an arrival date. Combat
  happens only at a location; nothing is intercepted in transit, at least for
  now. A phase of its own (§ 5).
- **About nine fleets per country**, enough for one per location: Earth with the
  Moon, Mercury with Venus, Mars, the Asteroid Belt, Jupiter, Saturn, Uranus,
  Neptune and the Kuiper Belt (§ 5.1).
- **Fleet numbers come in pairs, capacity and current**: a fleet is refuelled and
  resupplied (§ 5.1). The owner's first idea for composition: a handful of ship
  types or tiers, each with a known delta-v cap, supply and marines, and
  strength tracked per type; the fleet's delta-v and supply are the minimum
  across its types, its marines the sum.
- **Transfer times are real** (§ 5.3), with fusion drives in eras 11 and
  especially 12 (very high specific impulse, decent thrust) making travel quick.
  **Antimatter is a drive step of its own**, perhaps with antimatter-capable fleet
  power gated by the antimatter megaproject, the Antimatter Containment Facility.
- **Combat follows Lanchester's square law**, at least until a play-test (§ 5.4).
- **Earth and the Moon (the Moon Base) are one location and a battleground**,
  and battles there add to the orbital debris index (§ 5.4).

**Colonization**

- **Colony fleets travel too and claim on arrival.** If a fleet's site is taken
  before it arrives, it takes another free site at the same body; with none, the
  investment is lost (§ 5.6). Sending a colony to Uranus by chemical rocket when
  fusion torches are ten years off may be foolish.
- **Transfer times are the lock**, not the five stages, under simple and full
  (§ 5.6).
- **A colony fleet targets its destination**; today's random draw from the stage
  goes (§ 5.6).

**Population and modules**

- **Population is crews for modules** (§ 7). With Artificial General Intelligence
  (era 12, the production tree's last technology), modules need no crews at all.
  If an era 13 capstone comes, it can take that role.
- **Emigration has priorities**: a player building up Mars shouldn't see most of
  their people go to Venus (§ 7).
- **Who emigrates**: by stratum or by profession, either is fine. Colonies are
  melting pots; emigration policies by culture (only accepted pops, or exiling
  unaccepted ones) can be explored later (§ 7).
- **A specialization is probably just a module type** (§ 8.1).
- **Upkeep is input multipliers** on the building that does the work, as the mod
  has done before (§ 8.1).
- **Extraplanetary Bases are tied to colonies**, with huge total room. Powers
  fight over a site because it is good, or to deny it, almost never because
  space is tapped out. The Deep-Sea Mine stays the cheaper build, which is most
  of what keeps the Global Commons balance (§ 8.2).

**The rule**

- **Four levels of the Space Race rule**: off, races only (today's system),
  simple colonies, full colonies. **Full is the default** once the system is
  ready (§ 9).

## 1. What a colony is today

A colony is three records, and none of them names who holds it:

- **The claim** is a global flag, `sr_colony_<site> = yes`, set by
  `sr_establish_colony_effect` (`common/scripted_effects/space_race_effects.txt:832`,
  about 390 hand-written lines for the 34 sites). Stage advancement
  (`sr_check_colony_stage_effect`, `:1221`), the global count
  (`sr_total_global_colonies`) and completion read only these flags.
- **The holder's side** is `sr_colony_count` on the country and, for the
  specialization chosen in the site's event (`space_race_colony_events.1`–`.34`), a
  static modifier on `je:je_space_race_solar_colonization` plus
  `<modifier>_held` on the country (`sr_grant_colony_modifier`, `:1829`).
- **Its value** is that one modifier: +2% to +4% research speed, +0.1 to +0.4 space
  race progress, +5% Extraplanetary Base throughput and the like
  (`common/static_modifiers/space_race_modifiers.txt:464` on). Small each, worth
  something across ten colonies. Interplanetary Trade Networks follows once all 34
  are claimed.

So a site can never change hands; annexing its holder removes it from the game
(the journal entry and its modifiers go, the flag stays); and a colony has no
population, buildings or defence of its own. Revolutions are handled: the winner
inherits `<modifier>_held` and `sr_colony_count`, and `sr_repair_after_civil_war`
rebuilds the modifiers. A colony fleet founds its colony the month it departs, at
a random free site of the current stage.

Only the top three AI powers make space progress (the rank gate in
`docs/player_guide/16-space.md` § Joining the space race), so few AI countries
ever hold colonies. Every mechanic below needs AI weights of its own, or it only
ever happens to the AI and never by it.

## 2. What we can build on

| Need | Precedent in this repo |
|---|---|
| Move an abstract commons asset between countries, as a sale, a gift or a war goal | The five seabed lease articles, `common/treaty_articles/122_seabed_lease.txt`: one directed article per basin, `quantity` input, `can_be_enforced` + `giftable`. Its header: "Enforceable, so a war's winner can impose one: this is the earlier design's Seize Seabed Claims war goal." `test_seabed_leases.py` holds them alike |
| A treaty article that picks one item of a type | Vanilla `acquire_monopoly_for_company`: `required_inputs = { company building_type }`, a `building_type_valid_trigger`, and `usage_limit = once_per_side_with_same_inputs`, so one treaty can carry the article several times with different inputs |
| A stored country that may have died | `banking_rescue_donor_exists` (`common/scripted_triggers/banking_debt_triggers.txt:67`): `exists = var:x` plus `is_country_alive = yes` |
| Remove people in batches and count them | Internal Resettlement's deaths in transit, `kill_population_in_state` with `pop_type` / `strata` filters (`common/scripted_effects/resettlement_effects.txt:253`; the value is a constant). `create_pop` (state scope) brings people back |
| Transfer times and delta-v to each body | `scripts/generators/gen_launch_windows.py` computes every body's Hohmann time of flight and solves Lambert's problem for the delta-v of transfers between 0.25 and 2.6 times it (`TOF_RANGE`); today it emits only the windows and the off-window premiums |
| Departures to a body only in its window | Launch windows: `sr_launch_site_departs = { BODY = … }`, `sr_window_open_<body>`, the three propulsion steps (`common/scripted_triggers/sr_launch_window_triggers.txt`) |
| Upkeep as an input multiplier | Funding levels raise the Space Program's throughput (and so its Launch Capacity bill); the era-12 logistics methods use `goods_input_launch_capacity_mult` (`common/production_methods/te_global_commons_logistics_pms.txt:36`, registered in `mod_entity_modifier_types.txt:599`) |
| A hostile act in space short of war, with UN consequences | The anti-satellite strike (`common/diplomatic_actions/te_asat_strike_action.txt`, dossier ground `un_dos_asat`, the moratorium `un_events.41`) |
| A covert operation against a rival programme | `covert_space_espionage_action`, one of 15 operations on the `covert_op_start = { TYPE = … }` pattern (`common/diplomatic_actions/covert_operations.txt:2086`) |
| Building room that comes from an abstract holding, as a soft cap | Seabed licences gating the Deep-Sea Mine (`te_seabed_gate`, `building_ocean_mine`'s `possible`) |
| A custom war goal with an `on_enforced` effect | `te_colonial_reconquest` (`common/war_goal_types/te_colonial_reconquest.txt`) |
| Space military already in the tech tree | Space Militarization (era 11, Orbital Bombardment units), Orbital Weapon Platforms (era 12, the Orbital Battlestation, five levels of combat bonuses), Directed Energy Weapons, Fusion Power, Muon-Catalyzed Fusion Reactors, Antimatter Production (the Antimatter Containment Facility megaproject and the Antimatter Engine). The UN outer-space regime already bars a battlestation (`un_regime_effects.txt:253`) |
| A shared cost of fighting in orbit | The orbital debris index (`te_orbital_debris_effects.txt`), which anti-satellite strikes raise |
| Per-site code from one table | `gen_launch_windows.py`, `gen_seabed_basins.py` (post-load regenerators) |
| Programme levels instead of per-item buttons | The Colonial Empire's programmes at levels 0–3, stepped by an AI review (`mod_systems.md` § Colonial Programmes) |

## 3. Engine facts

**What the scope rests on:**

- **Colonies stay abstract**: records and modifiers, not map states. Hidden
  off-map states would need provinces in `map_data`, would show on the map and
  would draw AI invasions; for 34 sites that isn't worth it. Rejected.
- **The engine's fleets and armies can't leave the map**, so space fleets are
  records in script (§ 5), not formations.
- `kill_population_in_state` takes a constant, so emigration goes in fixed
  batches (resettlement does the same).
- Treaty articles run `on_entry_into_force`, take a `quantity` or a
  `building_type`, and with `can_be_enforced` become war goals with no war goal
  type of our own.
- `has_game_rule` tests a setting's flags, and one setting can carry several
  (§ 9).

**To verify (a self-check each, per the house rule):**

- A global variable holding a country after that country is annexed: does
  `exists` fail, or does `is_country_alive` have to catch it? Guard with both, as
  banking does, and log `TE_SELF_CHECK` on the first dead holder.
- **Hidden building types as a treaty input** (§ 6.1). Vanilla's only
  `building_type_valid_trigger` is `always = yes`, so it is unproven what scopes
  the trigger sees (the building type, the source country). Also: whether a
  building type that can never be built is still offered by the treaty designer;
  what it must declare (a building group, a production method group); whether it
  shows in other lists (the production overview, the encyclopedia); and which of
  the mod's audits need to skip it.
- How a script event can move war support (`add_war_support_change` is listed in
  `vanilla_war_reference.md` § 13) if occupied colonies and space battles are to
  count in a war.
- How far a scripted GUI can go for fleet orders (pick a fleet, pick a location,
  confirm) before it needs a generated widget per fleet slot.
- Later, not now: whether `kill_population_in_state` takes a culture filter, for
  emigration policies by culture (§ 7).

## 4. Foundation: a site record that names its holder

Everything else needs this, and it fixes the annexation hole on its own.

- **Per-site state lives in global variables keyed by site, with the holder as a
  pointer:** `sr_site_holder_<site>` (a country), `sr_site_spec_<site>` (the
  specialization chosen at founding) and `sr_site_status_<site>` (held,
  occupied, blockaded, derelict, ruined, free). Later slices add population,
  modules and integrity beside them. A transfer then repoints one variable;
  whatever the site holds stays with the site.
- **The journal entry's modifiers become a projection of the record.** One sync
  effect per site puts the colony's modifiers on the holder's entry and takes
  them off everyone else's. `<modifier>_held` stays as the revolution-proof
  mirror.
- **Generate the 34 sites from one table** (body, location, event, the two
  specializations, the discovery seed, and later room, mining quality and module
  slots), as the launch windows are. Today's `sr_establish_colony_effect` and
  `sr_check_colony_stage_effect` become generator output, and the table is what
  the cession article, the panel and the tests read.
- **Old saves migrate themselves**: each specialization names its site, so the
  `<modifier>_held` variables say who holds what. A monthly pass builds the holder
  record wherever it is missing.
- **A dead holder's colonies pass to whoever owns its last capital's state
  region** (recorded yearly on the holder), under every setting but off. With no
  owner there, or none running a programme, the site becomes derelict: the next
  fleet that can reach it claims it, at a discount. Free colonies (§ 6.5) can
  replace this default later.
- **A revolution's winner** repoints the holder records in the existing
  `te_civil_war_on_won` hook when the original tag dies.
- **Interplanetary Trade Networks** is replaced, or granted to every colony
  holder rather than only to those holding one when the last site was claimed
  (D2).
- **Panel:** a Solar System section listing every site with its holder's flag,
  next to Our Colonies. Under simple and full it is also where a colony fleet's
  destination is picked (§ 5.6).

## 5. Fleets (a phase of its own)

### 5.1 What a fleet is

A fleet is a record on its country: its ships by class, a few pooled stores, a
location and, in transit, a destination and an arrival date.

- **Nine slots per country** (`sr_fleet_<n>_*`, generated per slot), one for each
  location, so a power can keep a fleet everywhere it has interests. The panel
  shows one row per fleet. A slot is empty, at a location, or in transit.
- **Locations** are the owner's nine: Earth with the Moon (home, and the Moon
  Base), Mercury with Venus, Mars, the Asteroid Belt, Jupiter, Saturn, Uranus,
  Neptune and the Kuiper Belt. A fleet at a location can act on any site there.
  Departures still follow the window of the body a fleet heads for (Venus, or one
  asteroid, has its own).
- **Ship classes**, a handful (six to eight), each with fixed figures in a table:
  - its drive generation (chemical, fusion, fusion torch, antimatter), which sets
    its **delta-v capacity**;
  - its role: a **warship** (combat strength), an **assault carrier** (marines
    per point of strength) or, optionally, a **tender** (supply and propellant
    for the others);
  - its **supply endurance**, the months it lasts away from a friendly port.
- **What a fleet records**, each as capacity and current where it can run down:
  - **strength per class**, current and full (damage is the gap);
  - **propellant**, the delta-v it has left against what its classes allow;
  - **supply**, the months it has left against its endurance;
  - **marines**, current and capacity.
- **What the fleet can do follows from its classes**, as the owner proposed:
  - its delta-v capacity is the **minimum** over the classes it holds: the
    slowest ship sets the pace, so a fleet mixing chemical hulls with torches
    travels like a chemical fleet, which is the reason to retire old hulls;
  - its endurance is the **minimum** over its classes, unless it carries tenders,
    whose stores top up the others;
  - its marines are the **sum**;
  - its combat strength is the sum of each class's strength times its combat
    factor.
- **How the numbers move:**
  - **Strength** is built at Earth by Space Command (below), lost in battle, and
    repaired at Earth or at a friendly Spaceport (§ 8.1) over months.
  - **Propellant** is spent on each transfer, the delta-v that transfer needs
    (§ 5.3), and refilled at Earth or at a Spaceport; a Spaceport at a
    volatile-rich site (Ceres, Europa) that makes propellant is worth fighting
    over.
  - **Supply** runs down each month away from Earth or a friendly Spaceport and
    refills there; at zero, the fleet loses strength.
  - **Marines** are spent on a seizure (they become the occupied colony's
    garrison) and replenished at Earth.
- **Space Command** (working name; a government building unlocked by Space
  Militarization) builds strength at Earth. Its levels set how much it launches a
  year, its methods which drive generation, each gated by its technology:
  Fusion Power, Muon-Catalyzed Fusion Reactors, and Antimatter Production with
  the Antimatter Containment Facility built (the owner's suggestion). Which role
  it builds is F9. It employs officers, engineers and servicemen, and its upkeep
  is its inputs (Launch Capacity, Advanced Materials, fuel). The Orbital
  Battlestation adds strength at Earth only.
- **Merging and splitting** fleets at the same location moves numbers between
  slots.

### 5.2 Movement

An order sends a fleet to another location. Chemical fleets leave in the
destination body's launch window, or outside it at the premium with Asteroid
Mining; torch fleets leave any month, as today's rule for Muon-Catalyzed Fusion
Reactors. While in transit a fleet can be neither attacked nor recalled, and the
destination's holders see it coming (an alert with the arrival date), which is
the time they have to reinforce.

### 5.3 Real transit times, bought with delta-v

Minimum-energy (Hohmann) transfers take about 4 months to Mercury, 5 to Venus, 8
to 9 to Mars, 15 to Ceres, 2.7 years to Jupiter, 6 to Saturn, 16 to Uranus, 31
to Neptune and 45 to Pluto. Those are the chemical era's times, unchanged.

| Drive | Technology | Travel |
|---|---|---|
| Chemical | (the Space Program's start) | Hohmann transfers in launch windows, a little faster at a premium (Asteroid Mining) |
| Fusion | Fusion Power (era 11, military) | Very high specific impulse, modest thrust: well under Hohmann times, windows still matter for the far worlds |
| Fusion torch | Muon-Catalyzed Fusion Reactors (era 12, military) | Very high specific impulse and decent thrust: near-straight-line trips, months to the outer planets, no windows |
| Antimatter | Antimatter Production (era 12, military), with the Antimatter Containment Facility | Faster still |

For chemical and the slower fusion transfers, the generator's Lambert solver
already tabulates delta-v against time of flight by departure date, and can emit
the transit time each drive's delta-v buys per body and month. Its grid stops at
a quarter of the Hohmann time, so torch and antimatter transfers use the
brachistochrone instead (accelerate to the midpoint, decelerate the rest: time
from the distance on the departure date, which the generator's ephemerides give,
and the drive's acceleration, capped by its delta-v).

So chemical fleets fight only in the inner system and the outer colonies are
defended by distance until fusion. Propulsion decides space war and the
colonization of the outer worlds, and delta-v is the number on a fleet that
means something.

### 5.4 Combat at a location

Each month, at each location, the hostile forces there fight: fleets in the
same posture band (§ 6.2) and, for fleets that close in, the colonies'
defences. Losses follow Lanchester's square law (each side's losses in
proportion to the other's strength squared, so concentration pays), spread over
the classes by strength, until a play-test says otherwise. Whether warships
screen carriers and tenders, as vanilla's naval screening does, is F10. No
interception in transit. Battles at Earth and the Moon add to the orbital debris
index, so fighting at home has a cost everyone shares.

### 5.5 AI

A monthly review per space power, as the Colonial Empire's programmes are
stepped: keep a fleet at each location where it holds a colony under threat; at
war, send its strongest fleet against the enemy location where it outmatches the
defence and the transit is short; recall a fleet low on supply or propellant.
The AI is the largest risk in this phase: it has to judge a war it can't see on
the map.

### 5.6 Colony fleets travel too

Under simple and full colonies:

- **A colony fleet picks its destination.** The player chooses the site from the
  Solar System list; the AI scores sites by quality, distance and rivals en
  route. Today's random draw from the stage goes. Whether races only keeps the
  draw is D19.
- **It claims its site on arrival, not on departure.** It leaves with the transit
  time its drive buys (§ 5.3). The first fleet to arrive takes the site; a later
  one takes another free site at the same body, and with none, its investment is
  lost. A chemical fleet to Uranus can be overtaken by a torch launched a decade
  later.
- **Transfer times are the lock.** The five stages stop being locks: the outer
  worlds gate themselves by distance. Races only keeps the stages and instant
  founding.
- **What is in transit is visible**: the panel lists our fleets en route with
  their arrival dates, and rivals' fleets bound for a site we want.
- The transit tables are the same ones warships need, so colony transit is built
  first (slice 3 in § 10) and the fleets phase reuses them.

## 6. Contest

### 6.1 Cession by treaty

**Preferred: one Cede Colony article that picks the site.** One directed article,
`required_inputs = { building_type }`, with one hidden building type per site
(never buildable) standing for the colony, and a `building_type_valid_trigger`
offering only the sites the source holds. `once_per_side_with_same_inputs` lets
a treaty cede several colonies. It is `can_be_enforced` and `giftable`, as the
seabed lease is, so it gives a **sale** (paired with a Money Transfer the other
way), a **gift** to an ally or a subject, and a **war goal**: beat a holder on
Earth and take the colony you want in the peace. It rests on the engine checks
in § 3.

**Fallback: one article per body** (nine), with `quantity` as the number ceded
there, and the receiver picking which in a follow-up event.

Either way a cession is permanent, and population and modules go with the site.

### 6.2 Postures at a location, and blockade

A fleet at a location holds one of three postures:

- **Station** (the default where we hold a colony): defends our colonies there,
  fights any enemy fleet at the location.
- **Stand off** (blockade): stays out of the colonies' defences' reach and fights
  only enemy fleets standing off or stationed there. Once no enemy fleet
  contests it, it intercepts everything going to or from the enemy colonies at
  the location: emigrants, module deliveries, resupply, and mined output shipped
  to Earth (so a blockaded mining colony's Extraplanetary Base room stops
  counting for its holder, § 8.2). Research data is radioed home and can't be
  intercepted, so a science colony keeps its specialization; a blockade hurts
  mining and logistics colonies, not observatories.
- **Close in** (assault): enters the defences' reach, fights fleets and
  defences together, and wears down the colony's integrity (§ 6.3).

**Interdiction in peace** (owner's decision): movement and standing off are
allowed in peace, on the model of the Cuban quarantine of 1962. It costs infamy,
it is a UN dossier item as the anti-satellite strike is, and it gives the target
a casus belli. No shot is fired in peace; closing in, combat between fleets,
seizure and destruction need a war. An interdiction that meets the target's
stationed fleet is a standoff, and the first shot is a declaration of war.

### 6.3 Seizure, occupation and destruction

- **Seize.** A fleet closing in on a colony whose defences it outmatches brings
  the colony's integrity down month by month. The holder can resupply or
  reinforce only through the body's windows (until fusion), which is what makes
  the outer worlds hard to hold and hard to take. At zero integrity, with enough
  marines, the colony is **occupied**: it gives its modifiers to no one, its
  occupier's marines garrison it, it counts for the occupier's war support, and
  it goes back at the peace unless a Cede Colony article for it is enforced.
  Cession stays the one way a colony changes hands in war; occupation is how you
  make the enemy sign it.
- **Destroy.** Easier than seizure: no marines, and it needs only to outmatch the
  defences for a few months of bombardment, not to grind integrity to zero.
  The colony and its people are lost, and the site is ruined for years before it
  can be claimed again. The price: infamy, a UN item, and, once autonomy exists
  (§ 6.5), a rise in the autonomy of the destroyer's own colonies.

### 6.4 Covert operations

New operations on the existing pattern: Sabotage Colony (integrity, deaths),
Incite Colonial Autonomy (feeds § 6.5), Survey Colony Defences (intelligence, as
the covert slice 7's network intelligence does). Each is small because the
framework is there.

### 6.5 Free colonies, and colonies that leave on their own

A **free colony** is a site with people and no holder. It gives no one its
modifiers. Each colony gains an autonomy figure that rises with its people, its
distance, the months it goes without resupply, and its holder's wars,
repression and destruction of other colonies; at a threshold an event lets its
holder grant a charter (keep it, at a cost), garrison it, or let it go free.

**First version (owner's lean): free colonies wait and trade.** A free colony
trades with powers that send it supply, which pays both sides and pulls it
closer to its trading partner; it can be reclaimed by force. Diplomacy (a treaty
it accepts when its autonomy is low and relations are high), taking sides, and
growing into an actor of its own come later, as does the UN as its guarantor
(seizing a free colony a dossier item) and free colonies as the default for a
dead holder's.

### 6.6 Abandonment, and the outer-space convention

A holder can abandon a colony (its upkeep stops; its people come home or stay as
a free colony). The UN's outer-space convention can be extended to forbid
seizing and destroying colonies, with violations on the dossier.

## 7. Population

- **Each colony keeps a head count**, `sr_site_pop_<site>`. It rises with
  emigration from Earth and slow growth in its habitats, and falls with sieges,
  disasters and events.
- **Emigration is one national programme with per-colony priorities.** The
  programme's level (0–3) sets how many leave each month, in batches, from the
  state that holds the Space Program (`kill_population_in_state`); its upkeep is
  an input multiplier on the Space Program. Each colony has a priority (closed,
  low, normal, high; new colonies start at normal), and each month's emigrants
  are shared by priority times free room. A player building up Mars sets Mars
  high and Venus low, and never has to touch the rest. The AI sets priorities in
  its review.
- **Who leaves**: by stratum to start (the owner is fine with stratum or
  profession). Colonies are melting pots and keep no culture. Emigration policies
  by culture, such as sending only accepted pops or exiling unaccepted ones, can
  come later (the culture filter check in § 3).
- **People are crews.** Every module and specialization level above the first
  needs people to run, as a building needs employees. A founded colony is an
  automated outpost that runs its first module with a skeleton crew; everything
  past that is limited by its population. A Habitat module raises the room for
  people. So the chain is Habitat, then people, then modules, then output, and
  each step is worth defending.
- **Artificial General Intelligence removes the crew requirement entirely**
  (`artificial_intelligence`, era 12, production; an era 13 capstone can take
  that role if one comes). Modules then run without people and only the site's
  slots limit them. People still matter: the nation's off-world population gives
  a small prestige and cultural pull bonus, and it is what autonomy (§ 6.5)
  grows from.
- **The scale stays small beside Earth.** 34 colonies at a million each is a
  rounding error for a great power of the 2080s, so the cost is Launch Capacity
  and the people taken, not the head count.
- A destroyed colony's people die. An evacuation option brings them back with
  `create_pop` in the capital.
- Optional: the Demographics census counts emigrants as an exit.

## 8. Modules and mining

### 8.1 Modules

- **A specialization is a module type** (the owner's lean). Each site offers its
  two specializations as site-specific modules, with levels 1 to 3, whose
  modifiers are the 68 that exist, times the level. The founding event installs
  the chosen one at level 1, as an automated outpost. Whether the other can be
  built later, or the founding choice excludes it, is D18.
- **Three generic modules**, with slots per site from the site table (Mars more,
  Mimas fewer): **Habitat** (room and growth for people), **Defences** (what a
  closing fleet must beat), **Spaceport** (repairs, refuels and resupplies our
  fleets at the location, so a stand-off there costs no supply; resupplies the
  colony outside windows; makes propellant at a volatile-rich site; a candidate
  for the propellant depots the launch windows already describe).
- A module ships in its body's launch window and is built over months; a
  blockade stops the delivery.
- **Upkeep is an input multiplier** on the building doing the work (owner): the
  Space Program for colony modules, Space Command for fleets, as funding already
  raises the Space Program's Launch Capacity bill.

### 8.2 Extraplanetary Bases from colonies

Extraplanetary Base room comes from colonies, as Deep-Sea Mine room comes from
seabed licences, with a steep throughput penalty past the room rather than a ban
(the design defaults' soft cap).

- **The room is huge.** Each site's room, from the site table, is set so that the
  34 together are many times what every power could plausibly build, and even
  one good colony covers a great power's build-out. Space is never tapped out.
- **What differs is quality**: output per level, or per Launch Capacity, by
  site. A metal asteroid such as 16 Psyche is rich and close; Ceres, Vesta and
  the Martian sites are good; the outer moons are poor for shipping metal to
  Earth but can carry volatiles (helium-3 for the Fusion Plant specializations).
  A holder's bases fill the room of its best sites first, so a new poor colony
  adds room without diluting the bases already running, and taking a rival's
  Psyche colony lowers their average and raises ours.
- **Implementation sketch**: one country modifier on Extraplanetary Base
  throughput, re-applied monthly from the quality of the levels actually built,
  best room first; a blockaded or occupied site's room drops out. A single
  refresh site, per the house rule.
- **The Global Commons balance** (`2026-10-16-global-commons-design.md` § 1)
  rests mostly on the Deep-Sea Mine being much cheaper to build (owner), so the
  quality grades are unlikely to break the era-12 flip; a check of the two
  buildings' output per construction point at the grades settles it. Under races
  only (§ 9), bases stay unlimited as today.

## 9. The game rule: four levels of the Space Race rule

None of this makes sense without the space race, so it is a setting of the
existing `space_race_rule` (`common/game_rules/extra_game_rules.txt:140`), not a
rule of its own. The line between simple and full is fleets:

| Setting | What it has |
|---|---|
| Off | No space race (today's `space_race_disabled`) |
| Races only | Solar System Colonization as today: first come, first served, instant founding at a random site of the stage, the stages, colonies never change hands by treaty or war, Extraplanetary Bases unlimited. The holder record exists underneath, and the dead-holder rule applies |
| Simple colonies | Races only, plus cession by treaty (sale, gift, war goal), population, emigration and crews, modules, Extraplanetary Bases from colonies, colony fleets that pick their site and travel, distance in place of the stages, covert operations, free colonies and abandonment. Colonies change hands only at the peace table, or by agreement |
| Full colonies | Simple, plus fleets: movement, postures, blockade, interdiction in peace, sieges, seizure and destruction. **The default** once the system is ready |

**How it reads in script.** `has_game_rule` tests a setting's flags, and a
setting can carry several (today's off setting carries four). So every setting
but off keeps `flag = space_race_enabled`, and the 61 existing
`has_game_rule = space_race_enabled` checks in 22 files keep working untouched.
Simple and full add `flag = sr_colonies_contested`, full adds
`flag = sr_colonies_full`, and new script reads those through scripted gates
(`sr_colonies_contested_enabled`, `sr_colonies_full_enabled`), as Demographics
reads its three-level rule.

**Saves and the default.** A save records its setting by name. Keeping the name
`space_race_enabled` for races only means a save from before the change keeps
today's colonies, which is the Global Commons precedent ("a save from before it
keeps the uncapped mine"). While the system is built, the default stays races
only, so a half-built slice never reaches a new game: simple becomes the
default when slice 5 ships, full when the fleets phase's last part (6d,
Earth orbit) does (owner, 2026-10-26).

Two balances follow: Extraplanetary Bases unlimited (races only) and from
colonies (simple, full). Both need checking, and the guide has to describe both.

## 10. Build order

Each slice plays on its own and ships its own AI weights, tests and player guide
section.

| Slice | What | Size |
|---|---|---|
| 0 | Foundation (§ 4): holder records, the site generator, migration, the dead-holder rule, the Solar System list, Interplanetary Trade Networks (D2). Every setting but off | Medium |
| 1 | The four-level rule (§ 9) and the Cede Colony article (§ 6.1), starting with the hidden-building-type check; the per-body fallback if it fails | Small to medium |
| 2 | Population, emigration with priorities, crews and AGI (§ 7) | Medium |
| 3 | Transit tables in the launch-window generator (§ 5.3); colony fleets that pick their site, travel and claim on arrival; distance in place of the stages (§ 5.6) | Medium |
| 4 | Modules with specializations as modules (§ 8.1) and Extraplanetary Bases from colonies (§ 8.2) | Medium to large (the balance) |
| 5 | Covert operations, free colonies (waiting and trade), autonomy, abandonment, colony life events (§§ 6.4–6.6). Simple becomes the default | Medium |
| 6 | **The fleets phase** (§ 5, §§ 6.2–6.3; designed in `2026-10-26-solar-colonization-fleets-design.md`): 6a the fleet record, ship roles, Space Command and movement on legs between the nine locations; 6b combat at locations, postures, blockade away from Earth, seizure and destruction, settlement at the peace, war support, the AI's defence; 6c interdiction in peace, the AI's offence, the outer-space convention; 6d Earth orbit (blockading Earth, the ground reserve, ground-to-orbit batteries, fire support in the ground war). Full becomes the default with 6d | Large, the riskiest |

Slices 0 and 1 already let a war on Earth take colonies. Slice 6 is a phase of
its own, and its parts can ship as separate PRs.

Other ideas, not in the order: colony events (the first birth on Mars, a strike,
a dome breach); a Mars terraforming megaproject lasting decades; colonies held
jointly by a power bloc; Resort Colony tourism drawing on the colonies held.

## 11. Open calls

Fourth round (owner, 2026-10-25), now settled:

- **D2** Either way; the networks were a capstone for a race that ended, and
  colonies that are fought over, destroyed and refounded need one less. Slices 0
  and 1 keep today's grant (every holder once all 34 are claimed, including one
  that gains a colony by cession later); replacing it can come with a later
  slice.
- **D18** Specialization slots: a site has a fixed budget of specialization
  levels (four, say) to share between its two specializations: one at level 4,
  both at 2, or 1 and 3.
- **D19** Races only lets players pick their site too.
- **F9** Panel orders, leaning; a production method per role is acceptable.
- **F10** Warships screen carriers and tenders; a stance that lets a fleet drop
  the screen can come later, as the postures do.
- **F11** Tenders pool supply and propellant for the fleet.
- **M1** Set the grades and the room at a first guess and tune them in
  play-tests.
- **Marines as garrisons** give fleets another job: moving marines between
  colonies to garrison them.

Nothing is open that blocks slices 0 and 1. Their design:
`docs/superpowers/specs/2026-10-25-solar-colonization-holders-and-cession-design.md`.

Fifth round (owner, 2026-10-26, the fleets interview), now settled; the
design is `2026-10-26-solar-colonization-fleets-design.md`:

- **Four parts**, 6a to 6d, one design and one plan, each part its own PR.
- **Ship roles, not drive classes** (replacing § 5.1's classes by drive
  generation): a drive is a national unlock, and a fleet takes it in a refit
  when it next docks at Earth or one of our Spaceports. Old hulls are not worth
  scrapping under the square law, so tracking them per drive would mostly be
  bookkeeping.
- **Five roles**: warships, assault carriers, tenders, siege ships (strong
  against colony defences) and rapid response ships (a drive ahead, weak in
  combat).
- **Legs**: exact windows from Earth; mean-cycle windows home and among
  Mercury and Venus, Mars, the Belt and Jupiter; fixed medians beyond.
  "Include it only where it matters most."
- **Propellant in km/s** from the generator's tables.
- **Earth orbit is a part of its own (6d)**: no blockade at Earth before it.
  Then a blockade stops launches and holding orbit supports the ground war,
  and so that a small blockade can't hold a power for a whole war, new hulls
  wait in a ground reserve and launch together, and ground-to-orbit batteries
  fire on fleets at Earth (with lasers, sweeping low-orbit debris in peace).
- **War support** from occupied colonies (0.1 to 0.25 a beat, growing with the
  colony) and from battles, both kept small beside the war on Earth.
- **The AI** defends and attacks at war; it never interdicts in peace.
- **Space Command** is a building, where the Space Program stands.
- **Marines are the garrison** under Full Colonies.
- **Full becomes the default with 6d.**
- **The outer-space convention** follows the Moratorium, and members holding a
  colony can also table it.
- **A free colony seized is ours at once.**
