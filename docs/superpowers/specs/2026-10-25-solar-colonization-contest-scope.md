# Solar System Colonization: contested colonies, population and bases — scope

Drafted 2026-10-25 from the owner's brief: colonies can be contested, captured or
destroyed; colonies hold people taken from Earth; colonies can be built up with
modules; space fleets and marines; anything else that fits. This is a scoping
document, a menu with a recommended build order, not yet a design. Nothing is
built. The owner's calls are in § 9. Read `docs/systems/mod_systems.md` § Space
Race and `docs/player_guide/16-space.md` § Colonizing the solar system first; this
document assumes both.

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

What follows from that:

1. **A site can never change hands.** No effect anywhere moves a colony.
2. **Annexing the holder deletes its colonies for everyone.** The dead country's
   journal entry and its modifiers go; the global flags stay. The worlds stay
   claimed by no one for the rest of the game. So conquering a holder outright
   today doesn't keep its colonies alive at all; it removes them from the game.
   Conquering part of it changes nothing, and once a colony is held the
   programme ignores rank too.
3. **A colony has no state of its own.** No population, no buildings, no defence:
   nothing to grow, nothing to attack.
4. Revolutions are handled: the winner inherits `<modifier>_held` and
   `sr_colony_count`, and `sr_repair_after_civil_war` rebuilds the modifiers.

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
| A hostile act in space short of war, with UN consequences | The anti-satellite strike (`common/diplomatic_actions/te_asat_strike_action.txt`, dossier ground `un_dos_asat`, the moratorium `un_events.41`) |
| A covert operation against a rival programme | `covert_space_espionage_action`, one of 15 operations on the `covert_op_start = { TYPE = … }` pattern (`common/diplomatic_actions/covert_operations.txt:2086`) |
| Building room that comes from an abstract holding, as a soft cap | Seabed licences gating the Deep-Sea Mine (`te_seabed_gate`, `building_ocean_mine`'s `possible`) |
| Departures to a body only in its window | Launch windows: `sr_launch_site_departs = { BODY = … }`, `sr_window_open_<body>`, the three propulsion steps (`common/scripted_triggers/sr_launch_window_triggers.txt`) |
| A custom war goal with an `on_enforced` effect | `te_colonial_reconquest` (`common/war_goal_types/te_colonial_reconquest.txt`) |
| Space military already in the tech tree | Space Militarization (era 11, Orbital Bombardment units), Orbital Weapon Platforms (era 12, the Orbital Battlestation, five levels of combat bonuses), Directed Energy Weapons, Muon-Catalyzed Fusion Reactors. The UN outer-space regime already bars a battlestation (`un_regime_effects.txt:253`) |
| Per-site code from one table | `gen_launch_windows.py`, `gen_seabed_basins.py` (post-load regenerators) |
| Programme levels instead of per-item buttons | The Colonial Empire's programmes at levels 0–3, stepped by an AI review (`mod_systems.md` § Colonial Programmes) |

## 3. Engine facts

**What the scope rests on:**

- **Colonies stay abstract**: records and modifiers, not map states. Hidden
  off-map states would need provinces in `map_data`, would show on the map and
  would draw AI invasions; for 34 sites that isn't worth it. Rejected.
- **Fleets and armies can't leave the map.** Space forces have to be numbers in
  script, not formations.
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
  `vanilla_war_reference.md` § 13) if occupied colonies are to count in a war.
- Which modifier, if any, can add a weekly Launch Capacity input to the Space
  Program for module upkeep; failing that, upkeep is money under Programme Costs.

## 4. Foundation: a site record that names its holder

Everything below needs this, and it fixes the annexation hole on its own.

- **Per-site state lives in global variables keyed by site, with the holder as a
  pointer:** `sr_site_holder_<site>` (a country), `sr_site_spec_<site>` (1 or 2,
  the chosen specialization) and `sr_site_status_<site>` (held, occupied,
  derelict, ruined, independent). Later slices add population, modules and
  integrity beside them. A transfer then repoints one variable; whatever the site
  holds stays with the site.
- **The journal entry's modifiers become a projection of the record.** One sync
  effect per site puts the specialization on the holder's entry and takes it off
  everyone else's. `<modifier>_held` stays as the revolution-proof mirror.
- **Generate the 34 sites from one table** (body, stage, event, the two
  specializations, the discovery seed), as the launch windows are. Today's
  `sr_establish_colony_effect` and `sr_check_colony_stage_effect` become generator
  output, and the table is what the transfer articles, the panel and the tests
  read.
- **Old saves migrate themselves**: each specialization names its site, so the
  `<modifier>_held` variables say who holds what. A monthly pass builds the holder
  record wherever it is missing.
- **A dead holder** (recommendation, D1): its colonies pass to whoever owns its
  last capital's state region (recorded yearly on the holder), and become
  derelict if that country runs no space programme or the region has no owner. A
  derelict site is claimed by the next fleet that can reach it, at a discount,
  whatever the current stage.
- **A revolution's winner** repoints the holder records in the existing
  `te_civil_war_on_won` hook when the original tag dies.
- **Panel:** a Solar System section listing every site with its holder's flag,
  next to Our Colonies.

## 5. Contest

### 5.1 Cede colonies by treaty (small, proven)

One directed treaty article per body group (Mars, the Asteroid Belt, Venus,
Mercury, Jupiter, Saturn, Uranus, Neptune, the Kuiper Belt: nine), with
`quantity` as the number of colonies ceded there, `can_be_enforced` and
`giftable`, as the seabed lease is built. It gives three things at once:

- a **sale**, paired with a Money Transfer the other way;
- a **gift** to an ally or a subject;
- a **war goal**, through enforcement: beat a holder on Earth and take its Mars
  colonies in the peace. That answers "they get it forever, even if you conquer
  them".

A cession is permanent, not a lease. Population and modules go with the site.
The article can't let the giver pick which sites go, so either the receiver picks
in a follow-up event (recommended, D4) or a fixed rule picks them.

### 5.2 Space power: one national strength, projected through launch windows

- **One number per country, not fleets at bodies.** Its sources: a new
  government building (working name Space Command, unlocked by Space
  Militarization) whose levels and production methods (chemical, fusion,
  antimatter drives) set most of it, employing officers, engineers and servicemen
  and consuming Launch Capacity and Advanced Materials; the Orbital Battlestation's
  levels; the techs above. A colony's defence module counts only for that colony.
- **Projection goes by launch window.** An expedition to a body leaves in that
  body's window, or at the premium with Asteroid Mining, or any month with
  Muon-Catalyzed Fusion Reactors, the colony fleets' own three steps. It arrives
  after a transit time, and the strength it carries is tied up until it returns.
  That gives the space war geography (Jupiter is far, Mars opens every 26 months)
  with no stationing to manage. Per-body fleets would be more geography and much
  more micromanagement; not for a first version (D8).
- It also counts as power projection for prestige.

### 5.3 War in space: blockade, seize, destroy

At war with a holder (D5: or also in peace, as an act like the anti-satellite
strike, with infamy and a UN dossier), an expedition that reaches a body besieges
the enemy colonies there. Each month its strength is compared with the colony's
defence; the colony's integrity falls while it is outmatched, and the holder
resupplies or reinforces only in the body's own windows, which is what makes the
outer worlds hard to hold and hard to take. At zero integrity the attacker
chooses:

- **Blockade:** the colony's specialization goes dark for its holder while the
  siege lasts.
- **Seize:** needs marines (D9: a capacity of the Space Command's production
  method, or a real land unit type). The colony is occupied.
- **Destroy:** the colony and its people are lost; the site is ruined for some
  years, then claimable again. Infamy and a UN item.

**Occupation or conquest (D6).** Recommended, as on Earth: an occupied colony
gives its specialization to no one, counts for the occupier's war support, and
goes back at the peace unless a Cede article for its body is enforced. Then 5.1
stays the only way a colony changes hands in war, and 5.3 is how you make the
enemy sign it.

### 5.4 Covert operations

New operations on the existing pattern: Sabotage Colony (integrity, deaths),
Incite Colonial Autonomy (feeds 5.5), Survey Colony Defences (intelligence, as
slice 7's network intelligence does). Each is small because the framework is
there.

### 5.5 Colonies that leave on their own

With population (§ 6), each colony gains an autonomy figure that rises with its
people, its distance (stage), months without resupply, and its holder's wars and
repression laws. At a threshold, an event: grant a charter (keep it, at a cost),
garrison it, or let it go. An independent colony has no holder and gives no one
its specialization; its former holder can win it back by treaty or force, and a
rival can recognise it and take it as a protected holding. A weak holder can then
lose a colony through neglect, without any war (D14).

### 5.6 Abandonment

A button to abandon a colony (its upkeep stops): the site becomes derelict, and
the first fleet that reaches it reclaims it.

## 6. Population

- **Each colony keeps a head count**, `sr_site_pop_<site>`. It rises with
  emigration from Earth and slow growth in habitats, and falls with sieges,
  disasters and events.
- **Emigration is a national programme at levels 0–3, not a button per colony**:
  each month a batch per level leaves the state that holds the Space Program
  (`kill_population_in_state`) and is shared among the colonies with room. Two
  choices for who leaves (D10): by stratum, or the profession the colony's
  specialization works with (academics to a research site, engineers to a mining
  one), which makes emigration cost qualified people rather than just heads.
  Launch Capacity use rises with the level.
- **Population scales the specialization**: re-applied with a multiplier from the
  head count, on a soft curve (for instance half at founding, full at 100,000,
  half again at a million; D11). A colony nobody lives in is a flag on a rock; a
  populous one is worth defending.
- **The scale stays small beside Earth.** 34 colonies at a million each is a
  rounding error for a great power of the 2080s, so the cost is Launch Capacity
  and the qualified people, not the head count.
- A destroyed colony's people die. An evacuation option brings them back with
  `create_pop` in the capital.
- Optional: the Demographics census counts emigrants as an exit.

## 7. Modules

Two shapes (D12):

- **(a) Specialization levels.** Each colony's chosen specialization gets levels 1
  to 3, bought with money and Launch Capacity; the level becomes part of its
  multiplier. The 68 modifiers that exist already do the work.
- **(b) Generic modules,** a few per site: Habitat (room and growth for people),
  Defences (siege resistance), Spaceport (resupply and expeditions from it leave
  outside windows to its neighbours; possibly the propellant depots the launch
  windows already describe). Extraction and research don't need modules of their
  own: that is what specializations do.

Recommended: (a) plus the three generic modules. A module ships in its body's
launch window and is built over months. Upkeep is weekly, under Programme Costs.

**Tie the Extraplanetary Base to colonies (D13).** Colonies matter in a war only
if they matter in the economy. The seabed pattern would give each colony with a
mining specialization some Extraplanetary Base room, with a steep throughput
penalty past it (a soft cap, per the design defaults). That changes the Global
Commons balance between Extraplanetary Bases and Deep-Sea Mines
(`2026-10-16-global-commons-design.md` § 1), so it needs the owner's call.

## 8. Recommended build order

Each slice plays on its own and ships its own AI weights, tests and player guide
section.

| Slice | What | Size |
|---|---|---|
| 0 | Foundation (§ 4): holder records, the site generator, migration, the dead-holder rule, the Solar System list | Medium |
| 1 | Cede articles (§ 5.1): sale, gift, war goal | Small to medium |
| 2 | Population and emigration (§ 6), specializations scaled by people | Medium |
| 3 | Modules (§ 7), upkeep, and the Extraplanetary Base tie if D13 says yes | Medium |
| 4 | Space Command and expeditions (§ 5.2) | Large |
| 5 | Sieges, seizure, destruction, occupation at the peace, infamy and UN hooks (§ 5.3) | Large |
| 6 | Covert operations, autonomy and independence, abandonment, colony life events (§§ 5.4–5.6) | Medium |

Slices 0 and 1 already answer the brief's first point. Slices 4 and 5 are the
largest and the riskiest: the AI has to judge a war it can't see on the map, and
the end of a war has to settle every occupied colony.

Other ideas, not in the order: colony events (the first birth on Mars, a strike,
a dome breach); a Mars terraforming megaproject lasting decades; extending the UN
outer-space convention to forbid seizing colonies, with violations on the dossier;
colonies held jointly by a power bloc; Resort Colony tourism drawing on the
colonies held.

## 9. Decisions for the owner

- **D1** A dead holder's colonies: to the owner of its last capital (recommended),
  to whoever annexed most of it, or all derelict.
- **D2** Interplanetary Trade Networks once colonies can change hands: kept by
  everyone who held a colony when the 34th was claimed, or held only while
  holding one.
- **D3** Transfer unit: one article per body group with a quantity (nine,
  recommended), or one per site (34).
- **D4** Who picks the ceded sites: the receiver in an event (recommended), or a
  fixed rule.
- **D5** Space operations only in a war with the holder, or also in peace as an
  act like the anti-satellite strike.
- **D6** An occupied colony goes back at the peace unless ceded (recommended), or
  a capture is final.
- **D7** Destroying a colony: allowed? Its price in infamy, UN standing and years
  ruined.
- **D8** Space strength: one national figure projected through launch windows
  (recommended), or fleets stationed at bodies.
- **D9** Marines: a capacity of the Space Command (recommended), or a land unit
  type that has to exist in the army.
- **D10** Who emigrates: by stratum, or the profession the colony works with.
- **D11** How population scales a specialization, and what an empty colony gives.
- **D12** Modules: specialization levels plus three generic modules
  (recommended), or a full catalogue.
- **D13** Extraplanetary Base room from colonies: yes, changing the Global
  Commons balance, or no.
- **D14** Can colonies break away, and what does an independent colony become?
- **D15** Game rule: under the Space Race rule, or a separate Contested Space rule
  (on or off by default).
