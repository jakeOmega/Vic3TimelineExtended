# Solar System Colonization: contested colonies, population and bases — scope

Drafted 2026-10-25 from the owner's brief: colonies can be contested, captured or
destroyed; colonies hold people taken from Earth; colonies can be built up with
modules; space fleets and marines; anything else that fits. Revised the same day
with the owner's first answers (§ Decisions). This is a scoping document, a menu
with a build order, not yet a design. Nothing is built. The calls still open are
in § 11. Read `docs/systems/mod_systems.md` § Space Race and
`docs/player_guide/16-space.md` § Colonizing the solar system first; this
document assumes both.

## Decisions (owner, 2026-10-25)

- **A dead holder's colonies pass to the owner of its last capital**, for the
  first version. Later they may become **free colonies** by default (perhaps
  under the UN), which can be brought into the fold by force, diplomacy or trade
  (§ 6.5).
- **An occupied colony goes back at the peace unless a cession is enforced**, as
  occupied land does (§ 6.3).
- **Fleets are objects, not one national score**: a handful of numbers
  (strength, delta-v, fuel, ship types, whatever proves useful), a location and a
  timer. A fleet is either at a celestial body or in transit with an arrival
  date. Combat happens only at a body; nothing is intercepted in transit, at
  least for now. Large enough to be a phase of its own (§ 5).
- **A blockade needs only to beat the enemy's mobile forces, not the colony's
  defences.** The blockader stands off, out of the defences' reach, close enough
  to intercept anything coming or going (§ 6.2).
- **Emigration has priorities**: a player building up Mars shouldn't see most of
  their people go to Venus (§ 7).
- **Extraplanetary Bases are tied to colonies** (no more unlimited bases), but
  the total extraction space offers is huge. Powers fight over a site because it
  is good (much output per Launch Capacity), or to deny it to a rival, almost
  never because space is tapped out (§ 8.2).
- **Covert operations, colonies breaking away, abandonment and an outer-space
  convention against seizure are in** (§§ 6.4–6.6).
- **Space operations outside a war:** the owner leans yes, undecided (D5,
  § 6.2 has a proposal).
- **The game rule is a three-way choice, off / simple / full** (§ 9).

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
rebuilds the modifiers. A colony fleet founds its colony the month it departs; no
travel time is modelled.

Only the top three AI powers make space progress (the rank gate in
`docs/player_guide/16-space.md` § Joining the space race), so few AI countries
ever hold colonies. Every mechanic below needs AI weights of its own, or it only
ever happens to the AI and never by it.

## 2. What we can build on

| Need | Precedent in this repo |
|---|---|
| Move an abstract commons asset between countries, as a sale, a gift or a war goal | The five seabed lease articles, `common/treaty_articles/122_seabed_lease.txt`: one directed article per basin, `quantity` input, `can_be_enforced` + `giftable`. Its header: "Enforceable, so a war's winner can impose one: this is the earlier design's Seize Seabed Claims war goal." `test_seabed_leases.py` holds them alike |
| A stored country that may have died | `banking_rescue_donor_exists` (`common/scripted_triggers/banking_debt_triggers.txt:67`): `exists = var:x` plus `is_country_alive = yes` |
| Remove people in batches and count them | Internal Resettlement's deaths in transit, `kill_population_in_state` with `pop_type` / `strata` filters (`common/scripted_effects/resettlement_effects.txt:253`; the value is a constant). `create_pop` (state scope) brings people back |
| Transfer times and delta-v to each body | `scripts/generators/gen_launch_windows.py` computes every body's Hohmann time of flight and solves Lambert's problem for the delta-v of transfers between 0.25 and 2.6 times it (`TOF_RANGE`); today it emits only the windows and the off-window premiums |
| Departures to a body only in its window | Launch windows: `sr_launch_site_departs = { BODY = … }`, `sr_window_open_<body>`, the three propulsion steps (`common/scripted_triggers/sr_launch_window_triggers.txt`) |
| A hostile act in space short of war, with UN consequences | The anti-satellite strike (`common/diplomatic_actions/te_asat_strike_action.txt`, dossier ground `un_dos_asat`, the moratorium `un_events.41`) |
| A covert operation against a rival programme | `covert_space_espionage_action`, one of 15 operations on the `covert_op_start = { TYPE = … }` pattern (`common/diplomatic_actions/covert_operations.txt:2086`) |
| Building room that comes from an abstract holding, as a soft cap | Seabed licences gating the Deep-Sea Mine (`te_seabed_gate`, `building_ocean_mine`'s `possible`) |
| A custom war goal with an `on_enforced` effect | `te_colonial_reconquest` (`common/war_goal_types/te_colonial_reconquest.txt`) |
| Space military already in the tech tree | Space Militarization (era 11, Orbital Bombardment units), Orbital Weapon Platforms (era 12, the Orbital Battlestation, five levels of combat bonuses), Directed Energy Weapons, Muon-Catalyzed Fusion Reactors. The UN outer-space regime already bars a battlestation (`un_regime_effects.txt:253`) |
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
- Treaty articles run `on_entry_into_force`, take a `quantity`, and with
  `can_be_enforced` become war goals with no war goal type of our own.

**To verify (a self-check each, per the house rule):**

- A global variable holding a country after that country is annexed: does
  `exists` fail, or does `is_country_alive` have to catch it? Guard with both, as
  banking does, and log `TE_SELF_CHECK` on the first dead holder.
- Whether `kill_population_in_state` takes a culture filter, if we want to record
  who emigrated.
- How a script event can move war support (`add_war_support_change` is listed in
  `vanilla_war_reference.md` § 13) if occupied colonies and space battles are to
  count in a war.
- Which modifier, if any, can add a weekly Launch Capacity input to the Space
  Program for module and fleet upkeep; failing that, upkeep is money under
  Programme Costs.
- How far a scripted GUI can go for fleet orders (pick a fleet, pick a body,
  confirm) before it needs a generated widget per fleet slot.

## 4. Foundation: a site record that names its holder

Everything else needs this, and it fixes the annexation hole on its own.

- **Per-site state lives in global variables keyed by site, with the holder as a
  pointer:** `sr_site_holder_<site>` (a country), `sr_site_spec_<site>` (1 or 2,
  the chosen specialization) and `sr_site_status_<site>` (held, occupied,
  blockaded, derelict, ruined, free). Later slices add population, modules and
  integrity beside them. A transfer then repoints one variable; whatever the site
  holds stays with the site.
- **The journal entry's modifiers become a projection of the record.** One sync
  effect per site puts the specialization on the holder's entry and takes it off
  everyone else's. `<modifier>_held` stays as the revolution-proof mirror.
- **Generate the 34 sites from one table** (body, stage, event, the two
  specializations, the discovery seed, and later room, mining quality and module
  slots), as the launch windows are. Today's `sr_establish_colony_effect` and
  `sr_check_colony_stage_effect` become generator output, and the table is what
  the cession articles, the panel and the tests read.
- **Old saves migrate themselves**: each specialization names its site, so the
  `<modifier>_held` variables say who holds what. A monthly pass builds the holder
  record wherever it is missing.
- **A dead holder's colonies pass to whoever owns its last capital's state
  region** (recorded yearly on the holder). With no owner there, or none running
  a programme, the site becomes derelict: the next fleet that can reach it
  claims it, at a discount, whatever the current stage. Free colonies (§ 6.5)
  can replace this default later.
- **A revolution's winner** repoints the holder records in the existing
  `te_civil_war_on_won` hook when the original tag dies.
- **Panel:** a Solar System section listing every site with its holder's flag,
  next to Our Colonies.

## 5. Fleets (a phase of its own)

### 5.1 What a fleet is

A fleet is a record on its country: a few numbers, a location and a timer.

- **Fixed slots, a handful per country** (`sr_fleet_<n>_*`, n = 1 to 4, say), so
  the panel shows one row per fleet and the code for each slot is generated. A
  slot is empty, at a body, or in transit.
- **The numbers** (F2), a first cut:
  - **Strength** of its warships, what it fights with;
  - **Marines**, what it takes a colony with (§ 6.3);
  - **Delta-v**, the budget its drives allow, which buys transit speed (§ 5.3);
  - **Supply**, months it can stay away from a friendly spaceport before
    strength starts to fall; topped up at Earth or at a Spaceport module (§ 8).
  Ship types, if they come, are mixes of these (a tanker raises supply, a troop
  carrier marines), not separate combat rules.
- **Locations** are bodies, not sites: Earth orbit (home), and the window bodies
  the generator already lists (Mars, Venus, each asteroid, the Jupiter, Saturn,
  Uranus and Neptune systems, the Kuiper Belt) plus Mercury. A fleet at Jupiter
  can act on any of the six Jupiter sites.
- **Fleets are built at Earth** by a government building (working name Space
  Command, unlocked by Space Militarization): its levels set how much strength
  and how many marines it can put into orbit a year, and its production methods
  (chemical, fusion and antimatter drives) the delta-v of what it launches. It
  employs officers, engineers and servicemen and consumes Launch Capacity and
  Advanced Materials. The Orbital Battlestation adds strength at Earth orbit
  only. Merging and splitting fleets at the same body is a matter of moving
  numbers between slots.

### 5.2 Movement

An order sends a fleet from its body to another. It leaves in that body's launch
window, or outside it at the premium with Asteroid Mining, or any month with
Muon-Catalyzed Fusion Reactors, the colony fleets' own three steps. While it is
in transit it can be neither attacked nor recalled, and the destination's holder
sees it coming (an alert with the arrival date), which is the time it has to
reinforce.

### 5.3 Transit time from delta-v

Minimum-energy (Hohmann) transfers take about 4 months to Mercury, 5 to Venus, 8
to 9 to Mars, 15 to Ceres, 2.7 years to Jupiter, 6 to Saturn, 16 to Uranus, 31
to Neptune and 45 to Pluto. A fleet with delta-v to spare takes a faster, costlier
transfer: the generator's Lambert solver already tabulates delta-v against time
of flight, and can emit, per body, the transit time a given delta-v buys.
Chemical fleets then fight only in the inner system; the outer colonies are
defended by distance until fusion drives cut Jupiter to months. That makes
propulsion tech decide space war, as it should, and makes delta-v the number
that means something. The Lambert grid stops at a quarter of the Hohmann time,
so fusion-era transfers need it widened or a straight-line (brachistochrone)
approximation (F3).

### 5.4 Combat at a body

Each month, at each body, the hostile forces there fight: fleets in the same
posture band (§ 6.2) and, for fleets that close in, the colonies' defences.
Losses follow strength on a simple rule (Lanchester's square law is the usual
model of ranged combat: each side's losses in proportion to the other's strength
squared, so concentration pays). No interception in transit. Battles in Earth
orbit add to the orbital debris index (F6), so fighting at home has a cost
everyone shares.

### 5.5 AI

A monthly review per space power, as the Colonial Empire's programmes are
stepped: keep a fleet at each body where it holds a colony under threat; at war,
send its strongest fleet against the enemy body where it outmatches the defence
and the transit is short; recall a fleet low on supply. The AI is the largest
risk in this phase: it has to judge a war it can't see on the map.

## 6. Contest

### 6.1 Cession by treaty

One directed treaty article per body group (Mars, the Asteroid Belt, Venus,
Mercury, Jupiter, Saturn, Uranus, Neptune, the Kuiper Belt: nine), with
`quantity` as the number of colonies ceded there, `can_be_enforced` and
`giftable`, as the seabed lease is built. It gives a **sale** (paired with a
Money Transfer the other way), a **gift** to an ally or a subject, and a **war
goal**, through enforcement: beat a holder on Earth and take its Mars colonies in
the peace. A cession is permanent. Population and modules go with the site. The
article can't let the giver pick which sites go, so the receiver picks in a
follow-up event (recommended, D4) or a fixed rule does.

### 6.2 Postures at a body, and blockade

A fleet at a body holds one of three postures:

- **Station** (the default at a body where we hold a colony): defends our
  colonies there, fights any enemy fleet at the body.
- **Stand off** (blockade): stays out of the colonies' defences' reach and fights
  only enemy fleets standing off or stationed there. Once no enemy fleet
  contests it, it intercepts everything going to or from the enemy colonies at
  the body: emigrants, module deliveries, resupply, and mined output shipped to
  Earth (so a blockaded mining colony's Extraplanetary Base room stops counting
  for its holder, § 8.2). Research data is radioed home and can't be
  intercepted, so a science colony keeps its specialization; a blockade hurts
  mining and logistics colonies, not observatories.
- **Close in** (assault): enters the defences' reach, fights fleets and
  defences together, and wears down the colony's integrity (§ 6.3).

**Outside a war (D5), proposed:** movement and standing off are allowed in
peace, as an **interdiction** (the Cuban quarantine of 1962 is the model): infamy,
a UN dossier item like the anti-satellite strike, and a casus belli for the
target. No shot is fired in peace; closing in, combat between fleets, seizure and
destruction need a war. A peaceful interdiction that meets the target's
stationed fleet is a standoff, and the first shot is a declaration of war.

### 6.3 Seizure, occupation and destruction

A fleet closing in on a colony whose defences it outmatches brings the colony's
integrity down month by month; the holder can resupply or reinforce only through
the body's windows, which is what makes the outer worlds hard to hold and hard to
take. At zero integrity the attacker chooses:

- **Seize**, with enough marines: the colony is **occupied**. It gives its
  specialization to no one, counts for the occupier's war support, and goes back
  at the peace unless a cession article for its body is enforced (owner's
  decision). Cession stays the one way a colony changes hands in war; occupation
  is how you make the enemy sign it.
- **Destroy**: the colony and its people are lost, the site is ruined for some
  years, then claimable again. Infamy and a UN item (D7).

### 6.4 Covert operations

New operations on the existing pattern: Sabotage Colony (integrity, deaths),
Incite Colonial Autonomy (feeds § 6.5), Survey Colony Defences (intelligence, as
the covert slice 7's network intelligence does). Each is small because the
framework is there.

### 6.5 Free colonies, and colonies that leave on their own

A **free colony** is a site with people and no holder. It gives no one its
specialization. With population (§ 7), each colony gains an autonomy figure that
rises with its people, its distance, the months it goes without resupply, and its
holder's wars and repression; at a threshold an event lets its holder grant a
charter (keep it, at a cost), garrison it, or let it go free. A free colony can
be brought into the fold: by force (seize it), by diplomacy (a treaty it accepts
when its autonomy is low and relations high) or by trade (a standing trade link
that pays both sides and pulls it closer). The UN can be its guarantor: under the
outer-space convention, seizing a free colony is a dossier item. Later, a dead
holder's colonies can become free by default instead of passing to the capital's
owner.

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
  state that holds the Space Program (`kill_population_in_state`); Launch
  Capacity use rises with the level. Each colony has a priority (closed, low,
  normal, high; new colonies start at normal), and each month's emigrants are
  shared by priority times free room. A player building up Mars sets Mars high
  and Venus low, and never has to touch the rest. The AI sets priorities in its
  review.
- **Who leaves** (D10): by stratum, or the profession the colony needs
  (academics to a research site, engineers to a mining one), which makes
  emigration cost qualified people rather than just heads.
- **What people do** (P1). Three shapes, and they can combine:
  - **Crews** (recommended as the core): every module and specialization level
    above the first needs people to run, as a building needs employees. A
    founded colony is an automated outpost that runs its first specialization
    level with a skeleton crew; everything past that is limited by its
    population. A Habitat module raises the room for people. So the chain is
    Habitat, then people, then modules, then output, and each step is worth
    defending.
  - **Scaling**: the specialization's modifier grows with the head count on a
    soft curve. Simpler, but it double-counts with crews; pick one.
  - **Intrinsic**: the nation's off-world population as a whole gives a small
    prestige and cultural pull bonus, and is what autonomy (§ 6.5) and
    independence grow from.
- **The scale stays small beside Earth.** 34 colonies at a million each is a
  rounding error for a great power of the 2080s, so the cost is Launch Capacity
  and the qualified people, not the head count.
- A destroyed colony's people die. An evacuation option brings them back with
  `create_pop` in the capital.
- Optional: the Demographics census counts emigrants as an exit.

## 8. Modules and mining

### 8.1 Modules

- **Specialization levels**: each colony's chosen specialization gets levels 1 to
  3, bought with money and Launch Capacity; the level becomes part of its
  multiplier. The 68 modifiers that exist already do the work.
- **Three generic modules**, with slots per site from the site table (Mars more,
  Mimas fewer): **Habitat** (room and growth for people), **Defences** (siege
  resistance, what a closing fleet must beat), **Spaceport** (resupplies our
  fleets at the body, so a stand-off there costs no supply; resupply of the
  colony outside windows; a candidate for the propellant depots the launch
  windows already describe).
- A module ships in its body's launch window and is built over months; a
  blockade stops the delivery. Upkeep is weekly, under Programme Costs.

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
- This changes the Global Commons balance between the Extraplanetary Base and
  the Deep-Sea Mine (`2026-10-16-global-commons-design.md` § 1): the quality
  grades have to be set so that the era-12 flip still happens. Under the rule's
  off setting (§ 9), bases stay unlimited as today.

## 9. The game rule: off, simple, full

A proposed split, with the line between simple and full at fleets:

| Setting | What it has |
|---|---|
| Off | Solar System Colonization as today: first come, first served, colonies never change hands, Extraplanetary Bases unlimited. The holder record exists underneath, and the dead-holder rule applies (D16) |
| Simple | Off, plus cession by treaty (sale, gift, war goal), population and emigration, modules, Extraplanetary Bases from colonies, covert operations, free colonies and abandonment. Colonies change hands only at the peace table, or by agreement |
| Full | Simple, plus fleets: movement, postures, blockade, interdiction in peace, sieges, seizure and destruction |

Two balances follow: Extraplanetary Bases unlimited (off) and from colonies
(simple, full). Both need checking, and the guide has to describe both.

## 10. Build order

Each slice plays on its own and ships its own AI weights, tests and player guide
section.

| Slice | What | Size |
|---|---|---|
| 0 | Foundation (§ 4): holder records, the site generator, migration, the dead-holder rule, the Solar System list. All settings | Medium |
| 1 | The game rule (§ 9) and cession articles (§ 6.1) | Small to medium |
| 2 | Population, emigration with priorities, crews (§ 7) | Medium |
| 3 | Modules (§ 8.1) and Extraplanetary Bases from colonies (§ 8.2) | Medium to large (the balance) |
| 4 | Covert operations, free colonies, autonomy, abandonment, colony life events (§§ 6.4–6.6) | Medium |
| 5 | **The fleets phase** (§ 5, § 6.2–6.3): 5a the fleet record, Space Command and movement with transit by delta-v; 5b combat at bodies, postures, blockade, seizure and destruction, settlement at the peace; 5c interdiction in peace, the AI | Large, the riskiest |

Slices 0 and 1 already let a war on Earth take colonies. Slice 5 is a phase of
its own, as the owner expects, and its parts can ship as separate PRs.

Other ideas, not in the order: colony events (the first birth on Mars, a strike,
a dome breach); a Mars terraforming megaproject lasting decades; colonies held
jointly by a power bloc; Resort Colony tourism drawing on the colonies held;
colony fleets that found their colony on arrival rather than on departure (F4).

## 11. Open calls

Answered calls are in § Decisions. Still open:

- **D2** Interplanetary Trade Networks once colonies can change hands: kept by
  everyone who held a colony when the 34th was claimed, or held only while
  holding one.
- **D3** Cession unit: one article per body group with a quantity (nine,
  recommended), or one per site (34).
- **D4** Who picks the ceded sites: the receiver in an event (recommended), or a
  fixed rule.
- **D5** Space operations in peace: the interdiction of § 6.2 (movement and
  stand-off only, with infamy, a UN item and a casus belli), or none.
- **D7** Destroying a colony: allowed? Its price in infamy, UN standing and years
  ruined.
- **D10** Who emigrates: by stratum, or the profession the colony needs.
- **D11** If population scales specializations: the curve, and what an empty
  colony gives.
- **D14** What a free colony can do: only wait to be brought back, or trade,
  take sides, and grow into an actor of its own.
- **D16** Does the dead-holder rule apply under the off setting too (it fixes
  colonies vanishing), or is off exactly today?
- **D17** The rule's default setting.
- **F1** How many fleet slots per country.
- **F2** A fleet's numbers: strength, marines, delta-v and supply, or fewer; ship
  types or none.
- **F3** Transit times: real (from the generator, 16 years to Uranus by chemical
  rocket), or compressed for play.
- **F4** Colony fleets: keep founding on departure, or found on arrival like
  fleets.
- **F5** The combat rule: Lanchester's square law, or something flatter.
- **F6** Earth orbit as a battleground that adds to the debris index, or home
  only.
- **P1** What people do: crews (recommended), scaling, intrinsic, or a mix.
- **M1** The site quality grades and the room scale; the Global Commons flip
  must survive them.
