# Wonder Buildings Plan — Late-Game Megastructures

## Reference: The Space Elevator Pattern

All wonder buildings follow the two-building construction pattern established by the Space Elevator:

1. **Construction Site Building** (`building_X_construction_site`)
   - `buildable = yes`, `expandable = no`, single-level
   - `building_group = bg_government` (government-funded, no private investment)
   - Uses `required_construction = construction_cost_medium` (vanilla = 400 construction points, so it goes up fast via normal construction queue)
   - PM group with 3–4 PMs at different speeds: paused / slow / medium / fast
   - Construction PMs consume enormous quantities of goods and employ large workforces
   - Each month, `on_monthly_pulse_state` runs a scripted effect that increments a progress variable based on `(occupancy / 12) × speed_multiplier`
   - At progress ≥ 1.0: removes site, creates/upgrades the completed building
   - A `building_total_X_progress` modifier type is used for the visual progress display

2. **Completed Wonder Building** (`building_X`)
   - `buildable = no`, `expandable = no`
   - `building_group = bg_private_infrastructure` or `bg_space`
   - `ownership_type = self`
   - Created exclusively by the scripted effect (never by the player directly)
   - Can be upgraded by rebuilding the construction site (up to some max level)
   - Produces extraordinary quantities of a key good and/or provides powerful modifiers

### Key Design Constants (from Space Elevator)

| Parameter | Space Elevator Value | Notes |
|---|---|---|
| Construction PM speeds | 0.25× / 0.5× / 1× | = ~4 yr / ~2 yr / ~1 yr at full occupancy |
| Max level | 20 | Via repeated construction site rebuilds |
| Employment (construction) | 100,000 (50k eng + 50k acad) | Massive mobilization |
| Employment (operational) | 10,000/level (5k eng + 5k acad) | Still substantial |
| Construction cost (fast) | ~£290M/month goods input | Ruins your economy if you're not ready |
| Operational profit | ~£179M/level/month | Enormous payoff — the whole point |
| Key produced good | launch_capacity (1M/level @ £200) | Creates downstream demand chain |

### Goods Prices Reference (mod)

| Good | Price | Good | Price |
|---|---|---|---|
| electricity | £30 | electronic_components | £80 |
| steel | £50 | telephones | £70 |
| radios | £80 | advanced_materials | £4,000 |
| launch_capacity | £200 | digital_access | £60 |
| consumer_appliances | £60 | robotics | £120 |
| fertilizer (chemicals) | £30 | engines | £60 |
| glass (plastics) | £40 | tools | £40 |
| explosives | £50 | oil | £40 |
| automobiles | £100 | digital_assets (software) | £80 |
| lead (cond. metals) | £50 | iron (struct. metals) | £40 |
| tech_metals | £80 | coal (energy minerals) | £30 |

---

## Wonder 1: Solar Collector Array

**Fantasy:** The ultimate clean energy source. Massive orbital solar collectors beam power down to receivers on the ground, producing electricity so cheap it approaches free.

### Technology
- **Unlocked by:** `space_based_solar_power` (era 12, prereq: `quantum_communications`)
- **Current state of this tech:** Unlocks `pm_base_building_space_power` on renewable power plants (input: 100 launch_capacity + electronics/steel/telephones/advanced_materials → output: 9,000 electricity). This PM will be **removed** from renewable power plants and replaced by the wonder.

### Building Design

**Construction Site: `building_solar_collector_construction_site`**
- `building_group = bg_government`
- `unlocking_technologies = { space_based_solar_power }`
- **Location:** Any state, unrestricted, since the receivers are the new building.
- **Max level:** 10 (each level = one more collector array in orbit)

| Speed | Duration | Key Inputs/month | Employment |
|---|---|---|---|
| Paused | — | 5 advanced_materials (maintenance) | 25k eng + 25k acad |
| Slow | ~4yr | 500 advanced_materials, 40,000 launch_capacity, 5,000 electronic_components, 2,000 steel | 25k eng + 25k acad |
| Medium | ~2yr | 1,000 advanced_materials, 80,000 launch_capacity, 10,000 electronic_components, 4,000 steel | 25k eng + 25k acad |
| Fast | ~1yr | 2,000 advanced_materials, 160,000 launch_capacity, 20,000 electronic_components, 8,000 steel | 25k eng + 25k acad |

**Rationale for inputs:** Orbital solar collectors are physically simpler than a space elevator (no tether) but still require massive amounts of launch_capacity to get the collector panels to orbit, plus advanced_materials for the panels and electronic_components for the power transmission system.

### Hub + Receivers Architecture

Electricity is a local good in Victoria 3 — it cannot be produced in one place and consumed in another. The Solar Collector Array uses a **three-building system:**

1. **Construction Site** (`building_solar_collector_construction_site`) — builds and launches orbital collector arrays
2. **Completed Hub** (`building_solar_collector`) — represents the orbital infrastructure. Produces no electricity itself. Each level allows 10 additional receivers to be built.
3. **Receiver** (`building_solar_receiver`) — cheap, buildable ground stations that convert beamed power into electricity. Each produces 200,000 electricity per level.

**Completed Hub: `building_solar_collector`**
- `building_group = bg_government` (infrastructure project, not a commercial enterprise)
- **Does not produce electricity.** Instead, each level enables 10 `building_solar_receiver` buildings.
- Consumes maintenance goods to keep the orbital arrays operational.

| Per Level | Input | Output |
|---|---|---|
| advanced_materials | 200 (£800k) | — |
| electronic_components | 500 (£40k) | — |
| launch_capacity | 2,000 (£400k) | — |
| steel | 200 (£10k) | — |
| digital_access | 500 (£30k) | — |
| Employment | 2,000 eng + 2,000 acad | — |
| **Total input** | ~£1.28M/level | (pure maintenance cost) |

**Receiver: `building_solar_receiver`**
- `building_group = bg_private_infrastructure` (commercial electricity production)
- `buildable = yes`, `expandable = yes`
- `required_construction = construction_cost_medium` (cheap to build, like the construction site)
- **Possible condition:** State must have enough solar collector capacity (hub level × 10 ≥ total receivers)

| Per Level | Input | Output |
|---|---|---|
| electronic_components | 20 (£1.6k) | — |
| steel | 10 (£500) | — |
| **electricity** | — | **200,000 (£6M)** |
| Employment | 500 eng + 500 machinists | — |
| **Total input** | ~£2.1k | — |
| **Total output** | £6M | — |
| **Profit** | ~£6M/level | — |

At 10 hub levels with 100 receivers total: 20,000,000 electricity output across all states with receivers. The low maintenance input means electricity approaches near-free once the orbital collectors are in place.

### Interaction with Existing Space Power PM
Remove `pm_base_building_space_power` from renewable power plants entirely. The solar collector wonder replaces and supersedes it. Players who researched `space_based_solar_power` now build the wonder instead of switching a PM. This is a cleaner design — the old PM was already absurdly profitable for a simple PM switch.

---

## Wonder 2: Orbital Battlestation

**Fantasy:** A weapons platform in orbit that provides military dominance to whoever controls it. "The high ground" made literal.

### Technology
- **Unlocked by:** `orbital_weapon_platforms` (era 12, prereqs: `space_militarization` + `asteroid_mining`)
- **Current state of this tech:** Provides +0.5 nuke attack/defense, +200 barracks max. No buildings currently tied to it.

### Building Design

**Construction Site: `building_orbital_battlestation_construction_site`**
- `building_group = bg_government`
- `unlocking_technologies = { orbital_weapon_platforms }`
- **Location:** Unrestricted.
- **Max level:** 5 TOTAL (not per state, global limit)

| Speed | Duration | Key Inputs/month | Employment |
|---|---|---|---|
| Paused | — | 5 advanced_materials | 20k eng + 20k officers + 10k acad |
| Slow | ~4yr | 3,000 advanced_materials, 30,000 launch_capacity, 3,000 electronic_components, 5,000 steel, 2,000 explosives | 20k eng + 20k officers + 10k acad |
| Medium | ~2yr | 6,000 advanced_materials, 60,000 launch_capacity, 6,000 electronic_components, 10,000 steel, 4,000 explosives | 20k eng + 20k officers + 10k acad |
| Fast | ~1yr | 12,000 advanced_materials, 120,000 launch_capacity, 12,000 electronic_components, 20,000 steel, 8,000 explosives | 20k eng + 20k officers + 10k acad |

**Rationale:** Military orbital platforms are heavy, armored, and weapon-laden. They need explosives for ordnance, more steel for armor, and lots of launch_capacity. Officers are part of the construction workforce (military oversight).

**Completed: `building_orbital_battlestation`**
- `building_group = bg_military`

| Per Level | Input | Output / Effect |
|---|---|---|
| advanced_materials | 300 (£1.2M) | — |
| electronic_components | 500 (£40k) | — |
| launch_capacity | 5,000 (£1M) | — |
| explosives | 500 (£25k) | — |
| steel | 300 (£15k) | — |
| Employment | 2,000 eng + 3,000 officers + 1,000 acad | — |
| **Total input** | ~£2.28M/level | — |
| **Country modifiers (per level):** | | |
| `unit_offense_mult` | +0.05 per level | — |
| `unit_defense_mult` | +0.05 per level | — |
| `unit_morale_recovery_mult` | +0.05 per level | — |
| `country_nuclear_weapon_defense_chance_add` | +0.10 per level | — |
| `unit_blockade_mult` | +0.10 per level | — |
| `unit_morale_damage_mult` | +0.05 per level | — |

At 5 levels: +25% offense, +25% defense, +25% morale recovery, +50% nuke defense, +50% blockade efficiency, +25% morale damage. This is a **massive** military bonus that costs roughly £11.4M/month in goods to maintain. The country modifiers should be applied via the wonder building's PM `country_modifier` block, not via `add_modifier`.

**Design notes:**
- This does NOT produce a tradeable good (unlike the space elevator/solar collector). It provides country-wide military buffs.
- The modifiers in the `orbital_weapon_platforms` tech should be **reduced** since the battlestation building now provides the main military payoff (the tech modifier was a placeholder).
- Very expensive to build AND maintain → balanced against enormous military benefit.
- At max level (5), the +25% offense/defense makes your armies dramatically stronger. This is comparable to having a full-tier technology advantage in weapons tech.

---

## Wonder 3: Antimatter Containment Facility

**Fantasy:** Antimatter is the densest energy storage medium physically possible. A single gram has the energy of 21.5 kilotons of TNT. A containment facility for industrial-scale antimatter production enables revolutionary propulsion, weapons, and energy applications.

### Technology
- **Unlocked by:** `antimatter_production` (era 12, prereqs: `fusion_power` + `quantum_communications`)
- **Current state of this tech:** Provides +0.25 aerospace throughput, +60 naval base max, +100% formation movement speed. No buildings tied to it.

### Brainstorming — What Does Antimatter Do Mechanically?

Antimatter is useful for three things:
1. **Propulsion** — antimatter rockets make interplanetary travel trivial. This means faster military formation movement, better convoys, enhanced naval projection.
2. **Weapons** — antimatter warheads are even more devastating than nuclear weapons. This provides nuke attack bonuses and conventional military throughput.
3. **Energy** — antimatter annihilation is the most efficient energy conversion process possible. But fusion already fills the "cheap power" niche, and the solar collector does too.

**Recommendation:** Focus on **military and logistical applications**. Antimatter as a good (like launch_capacity) that feeds military buildings and formations.

### No New Good
Antimatter will NOT be a tradeable good (new goods are computationally expensive). Instead, the antimatter facility follows a similar pattern to the Solar Collector Array: each level enables a number of downstream buildings or provides scaling country modifiers for military applications.

### Building Design

**Construction Site: `building_antimatter_facility_construction_site`**
- `building_group = bg_government`
- `unlocking_technologies = { antimatter_production }`
- **Location:** Any state with electricity level ≥ 10 (antimatter production requires enormous power)
- **Max level:** 10

| Speed | Duration | Key Inputs/month | Employment |
|---|---|---|---|
| Paused | — | 5 advanced_materials | 25k eng + 25k acad |
| Slow | ~4yr | 5,000 advanced_materials, 10,000 electronic_components, 50,000 electricity, 5,000 steel | 25k eng + 25k acad |
| Medium | ~2yr | 10,000 / 20,000 / 100,000 / 10,000 (2×) | 25k eng + 25k acad |
| Fast | ~1yr | 20,000 / 40,000 / 200,000 / 20,000 (4×) | 25k eng + 25k acad |

**Rationale:** Antimatter production is fundamentally an energy-conversion process — you smash particles together at enormous energy cost to produce tiny amounts of antimatter. Hence the huge electricity input.

**Completed: `building_antimatter_facility`**
- `building_group = bg_space` (or new `bg_advanced_military`)
- `ownership = self`

| Per Level | Input | Output |
|---|---|---|
| electricity | 50,000 (£1.5M) | — |
| advanced_materials | 200 (£800k) | — |
| electronic_components | 500 (£40k) | — |
| steel | 200 (£10k) | — |
| **antimatter** | — | **500 (£250k)** |
| Employment | 3,000 eng + 3,000 acad | — |
| **Total input** | ~£2.35M | — |
| **Total output** | £250k | — |

**Wait, this loses money!** Yes — deliberately. Antimatter production is **staggeringly** energy-intensive and inherently unprofitable. You produce antimatter because you need it for military applications and interstellar travel, not because it makes money. This mirrors how real militaries spend vast sums producing materials with no direct commercial value.

**But the game needs the building to not bankrupt itself.** The building should either:
- (A) Be `ownership = self` government-funded (like a government building) with subsidies built in, OR
- (B) Also produce a commercial byproduct (advanced_materials from the supercollider waste, research speed bonus) that offsets costs, OR
- (C) Have country_modifier bonuses baked in (like the battlestation) that justify the expense

**Recommendation: Approach C** — The antimatter facility provides country-wide military modifiers (formation speed, naval projection, weapons potency) that justify its operating cost, AND produces the `antimatter` good consumed by military PMs and the interstellar ship.

**Revised outputs:**

| Per Level | Input | Output / Effect |
|---|---|---|
| electricity | 50,000 (£1.5M) | — |
| advanced_materials | 200 (£800k) | — |
| electronic_components | 300 (£24k) | — |
| **antimatter** | — | **500 (£250k)** |
| Country modifiers: | | |
| `military_formation_movement_speed_mult` | +0.10 per level | — |
| `country_convoys_capacity_mult` | +0.05 per level | — |
| Employment | 3,000 eng + 3,000 acad | — |
| **Net operating cost** | ~£2.07M/level | (offset by military value + antimatter for downstream uses) |

The `antimatter_production` tech modifiers remain unchanged — these techs are deliberately chosen as wonder hooks because they are currently underpowered for endgame. The building adds on top of the tech bonuses.

### Downstream Uses of Antimatter
- **Military buildings (future):** Each facility level could enable downstream military installations (like the solar receiver pattern) providing combat bonuses.
- **Interstellar Colony Ship (Wonder 5):** Requires antimatter facility at a minimum level as a build prerequisite.
- **Potential new combat unit type:** Antimatter strike craft.

---

## Wonder 4: Mind Upload Nexus

**Fantasy:** True digital immortality. Consciousness can be copied and uploaded to digital substrate, granting a form of immortality. The societal implications are staggering.

### Technology
- **Unlocked by:** `mind_backups` (era 12, prereqs: `biological_immortality` + `neural_lace`)
- **Current state of this tech:** Provides +10 economy_of_scale cap, +50 max weekly construction progress, -5% mortality, +10000 character health.
- **Note:** User mentioned "mind_uploading" but the mod has `mind_backups`. We'll use `mind_backups` as the prerequisite.

### What Does Mind Uploading Do Mechanically?

This is the most philosophically interesting wonder. Possible mechanical effects:
1. **Effective immortality** → massive reduction in mortality, character health
2. **Knowledge preservation** → tech research speed, innovation
3. **Population dynamics** → uploaded minds don't die but do they reproduce? Do they count as pops?
4. **Labour force transformation** → uploaded minds can work virtually (digital services, software, research)
5. **Societal upheaval** → massive radicals from those who oppose it, loyalists from those who embrace it
6. **IG reactions** — devout HATE this (it's blasphemy), intelligentsia LOVE it, trade unions fear job displacement

Since we can't actually create digital pops or fundamentally change the pop system, the mechanical translation should focus on:
- **Research and innovation boost** (uploaded minds contribute to intellectual output)
- **Mortality reduction** (biological backups available)
- **Service/software throughput** (digital labor)
- **Massive IG polarization** (this is the most socially disruptive technology imaginable)

### Building Design

**Construction Site: `building_mind_upload_nexus_construction_site`**
- `building_group = bg_government`
- `unlocking_technologies = { mind_backups }`
- **Location:** Any state with a university at level ≥ 5 (intellectual infrastructure requirement)
- **Max level:** 5 (each nexus is a continent-scale data center for human consciousness)

| Speed | Duration | Key Inputs/month | Employment |
|---|---|---|---|
| Paused | — | 5 advanced_materials | 30k eng + 30k acad |
| Slow | ~4yr | 3,000 advanced_materials, 10,000 electronic_components, 5,000 digital_access, 20,000 electricity | 30k eng + 30k acad |
| Medium | ~2yr | 2× slow | 30k eng + 30k acad |
| Fast | ~1yr | 4× slow | 30k eng + 30k acad |

**Completed: `building_mind_upload_nexus`**
- `building_group = bg_private_infrastructure`
- `ownership = self`

| Per Level | Input | Output / Effect |
|---|---|---|
| electricity | 30,000 (£900k) | — |
| electronic_components | 1,000 (£80k) | — |
| digital_access | 2,000 (£120k) | — |
| advanced_materials | 100 (£400k) | — |
| **digital_assets (software)** | — | **5,000 (£400k)** |
| **services** | — | **5,000 (£200k)** |
| Country modifiers: | | |
| `country_tech_research_speed_mult` | +0.05 per level | — |
| `country_weekly_innovation_mult` | +0.10 per level | — |
| `state_mortality_mult` | -0.02 per level | — |
| `character_health_add` | +500 per level | — |
| Employment | 3,000 eng + 5,000 acad + 2,000 clerks | — |
| **Net operating cost** | ~£900k/level (offset by digital_assets + services output) | — |

At 5 levels: +25% tech speed, +50% innovation, -10% mortality, +2500 character health. The research/innovation boost is the primary reason to build this. The mortality reduction stacks with `biological_immortality` tech (-20%) for a total of -30% mortality.

**Design notes:**
- The output goods (software, services) keep it from being a pure money sink.
- The big output is intellectual: tech speed + innovation. This accelerates the endgame tech race.
- Character health bonus means rulers and generals effectively cannot die of natural causes.
- The `mind_backups` tech modifiers should be reduced since the building provides the main effects.
- Consider an event chain: "First Uploaded Mind" one-time event when the first nexus completes. Massive IG reactions.

**Design revision:** Focus on massive services and software output representing the digital labor of uploaded minds. Drop mortality reduction (would stack below 0% with existing techs), innovation (cheap by endgame), and character health (already covered by `mind_backups` tech). Keep the tech research speed buff as the sole country modifier; the main value of this wonder is the enormous goods output.

---

## Wonder 5: Interstellar Colony Ship (The Ark)

**Fantasy:** The ultimate expression of human ambition — an interstellar colony ship that will carry civilization to another star. This is the "one more turn" endgame goal.

### Technology
- **Unlocked by:** `space_colonization` (era 12, prereqs: `biohacking_and_human_augmentation` + `lab-grown_food`)
- **Additional requirement:** Should also require `antimatter_production` and `space_elevator` techs. Must have a `building_space_elevator` at level ≥ 5 in the state (launches from the elevator). These would be `possible` conditions on the construction site, not tech unlocks.

### What Does an Interstellar Ship Do Mechanically?

This is a **prestige project** — the ultimate victory lap. It doesn't "do" something practical for your economy. Instead:
1. **Enormous prestige** — completing an interstellar ship is the greatest achievement in human history
2. **Population emigration** — colonists leave for the new world (population cost)
3. **National unity** — the shared endeavor transcends class and faction
4. **Technology showcase** — research speed from having the most advanced engineering project ever
5. **Global event** — every country in the world should get a notification

### Building Design

**Construction Site: `building_interstellar_ship_construction_site`**
- `building_group = bg_government`
- `unlocking_technologies = { space_colonization }`
- **Possible conditions:** Must also have `antimatter_production` and `space_elevator` techs. Must have a `building_space_elevator` at level ≥ 5 in the state (launches from the elevator).
- **Location:** Same state as a space elevator (equatorial)
- **Max level:** 1 (there is only one Ark)
- **Special:** This should be the single most expensive project in the game. Construction takes 5–10 years even at fast speed.

| Speed | Duration | Key Inputs/month | Employment |
|---|---|---|---|
| Paused | — | 10 advanced_materials | 50k eng + 50k acad |
| Slow | ~10yr | 10,000 advanced_materials, 200,000 launch_capacity, 10,000 electronic_components, 10,000 steel, 5,000 digital_access, 50,000 electricity | 50k eng + 50k acad |
| Medium | ~5yr | 2× slow | 50k eng + 50k acad |
| Fast | ~2.5yr | 4× slow | 50k eng + 50k acad |

**Note:** The fast speed is slower than other wonders (0.4× instead of 1×, i.e., ~2.5 years). This is the apex project.

**Completion Effect (not a completed building):**
Unlike other wonders, the Ark doesn't become an operational building. Upon completion:
1. **One-time prestige burst:** Massive permanent modifier (+100 prestige? Or a scaling prestige add)
2. **Country modifier:** Permanent `interstellar_ark_launched` modifier providing +50% prestige, +25% influence, +25% tech research speed, +20 legitimacy
3. **Population cost:** Lose 500,000 or 1,000,000 pops from the state (the colonists). Use `kill_population_in_state` or `change_pop_population` effects.
4. **Global notification:** Every country gets a notification that the Ark has launched
5. **Loyalists:** Massive loyalists gain across all strata (national pride)
6. **Event:** A special one-time event commemorating the launch

### Alternative: Operational Colony Ship Building
If we want it to be more than a one-shot:
- The completed building could represent the "Colony Ship Program" producing a new good `colony_ship_capacity` that provides prestige and a permanent country modifier scaling with level.
- But this feel less dramatic. **Recommendation: One-shot with massive permanent rewards.** The journey IS the reward — the 5-10 years of building it gives the player a long-term goal, and the completion is a narrative climax.

---

## Implementation Priorities

| Priority | Wonder | Complexity | Key New Content |
|---|---|---|---|
| 1 | **Solar Collector Array** | High | Three-building system (site + hub + receivers), remove old PM |
| 2 | **Orbital Battlestation** | Medium | New building pair, country military modifiers |
| 3 | **Antimatter Containment Facility** | Medium | New building pair, military modifiers (no new good) |
| 4 | **Mind Upload Nexus** | Medium | New building pair, massive services/software output |
| 5 | **Interstellar Colony Ship** | High | Unique completion mechanics, population effects, global events |

### Shared Infrastructure Needed

1. **Scripted effects pattern:** Template `wonder_construction` effect per building (copy space_elevator_construction, parameterize)
2. **On-action wiring:** Each wonder gets an on_action in `on_monthly_pulse_state`
3. **Progress modifier types:** One `building_total_X_progress` per wonder in `extra_modifier_types.txt`
4. **Static modifiers:** Progress display modifiers (like `space_elevator_progress`)
5. **Building groups:** May need `bg_orbital` or similar for the space-based wonders
6. **Localization:** Each wonder needs ~30-50 loc keys (building names, PM names, tooltips, progress bar)
7. **Tech modifier rebalancing:** Not planned — the selected techs are currently underpowered for endgame. The wonders add on top of existing tech modifiers.

### Summary Table

| Wonder | Tech | Max Lvl | Key Input | Key Output | Main Benefit |
|---|---|---|---|---|---|
| Solar Collector | space_based_solar_power | 10 | launch_capacity, advanced_materials | 200k electricity/receiver | Cheapest power (via receivers) |
| Orbital Battlestation | orbital_weapon_platforms | 5 | launch_capacity, steel, explosives | military modifiers | +5%/lvl off/def/morale |
| Antimatter Facility | antimatter_production | 10 | electricity (massive), advanced_materials | military modifiers | Movement speed + convoy capacity |
| Mind Upload Nexus | mind_backups | 5 | electricity, electronics, digital_access | massive software + services | +5%/lvl tech speed + digital labor |
| Interstellar Ark | space_colonization | 1 | everything (launch, adv_mat, electricity) | (completion event) | Prestige, victory lap |

---

## FAQ

1. **Should wonders be limited to one per country?** No. The cost is the limiting factor, not a hard cap. Only the Ark should be unique (one per world, first to complete wins).

2. **Should wonders have maintenance concepts?** No. Goods consumption in the operational PM IS the maintenance.

3. **Should there be events tied to each wonder?** Would add flavor but not strictly necessary. Can be added later.

4. **AI behavior:** The AI needs to know when to build these. High `ai_value` on the PM modifier types and appropriate `ai_weight` on the tech. The pricetag means only Great Powers will realistically build them.

5. **Antimatter as a good vs. just modifiers:** No new good — too computationally expensive. Use hub+downstream or pure modifier pattern instead.

6. **Tech rebalancing scope:** No rebalancing planned. The selected techs are deliberately underpowered and the wonders add on top.