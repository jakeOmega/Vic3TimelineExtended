# Lunar colonization: the Moon as Solar System Colonization's first stage, colonization in era 10 — design

Drafted 2026-10-29 with the owner. It changes the space race as built by the
solar colonization slices 0 to 6
(`2026-10-25-solar-colonization-holders-and-cession-design.md`,
`2026-10-25-solar-colonization-population-and-transit-design.md`,
`2026-10-25-solar-colonization-modules-and-bases-design.md`,
`2026-10-26-solar-colonization-free-colonies-design.md`, and the archived
`archive/specs/2026-10-26-solar-colonization-fleets-design.md`) and the launch
windows of `archive/specs/2026-10-16-global-commons-design.md` § 5. There is no
separate plan: § 13 is the build order.

## 1. The owner's calls (2026-10-29)

1. **The Moon Base milestone is retired.** The Moon becomes a set of six worlds
   inside Solar System Colonization. Founding your first lunar colony takes the
   Moon Base's place in the race, with the first-or-later reward.
2. **Solar System Colonization opens in era 10**, on a new technology. Chemical
   rockets (launch windows, transit, the 15-year horizon) and the cost of each
   colony limit early expansion, not a ladder of technology gates.
3. **The Extraplanetary Base unlocks earlier, in era 10**, with an early method
   that is not very good. Asteroid Mining (era 11) brings today's Asteroid Mine
   method.
4. **New technologies rather than reusing existing ones** in eras 10 to 12, which
   blur together.
5. **Worlds beyond the Moon need the Mars Landing**: a hard gate, under the
   "physical prerequisite" exception to the soft-caps default (`CLAUDE.md`
   § Design defaults).
6. **Lunar colonies can be assaulted** under Full Colonies.
7. **Six lunar worlds.**
8. **Nuclear thermal propulsion only if cheap.** It is: § 9 makes it a second
   off-window premium curve. It adds no drive tier.
9. **No month-long transit to the Moon** (a crewed transfer takes about three
   days). A colony fleet bound for the Moon founds its world in the month it
   leaves (§ 3.3).

Follow-up calls, the same day (PR #1232):

10. **Judge the base on more than its margin.** Profit per point of
    construction and profit per worker (the wage it can pay, and so the richest
    economy that can run it) count too (§ 6).
11. **The lunar tier should cost less than Mars, but more than the first
    draft's 250** (about 40% below Mars's 400), and the later stages may rise
    too (§ 3.2).
12. **More funding levels from the new technologies, and a soft cap.** Funding
    may go past the cap with diminishing returns: the first level above it
    counts as half a level, the next a third, and so on (§ 5.1).

## 2. Intent

After this design:

1. **Era 10 is when colonization starts.** A great or major power that finished
   the Moon Landing researches Cislunar Infrastructure, switches its Space
   Program to the colonization method and settles the Moon first. The Moon is
   cheap, has no launch window, and its fleets land the month they leave.
2. **The Mars Landing race runs beside lunar settlement.** Finishing it opens
   Mars, the asteroids and beyond to that country's colony fleets. From then on
   chemical rockets set the pace: windows, months in transit, and the outer
   system out of reach until fusion.
3. **The race to the Moon keeps its "first".** The first country to found a
   lunar colony gets today's first Moon Base reward, and later countries get the
   later reward when they found their first. The Program row's icon, the Space
   Powers order, the UN count, covert "ahead in space" checks and the Grand
   Monument's lunar moment all keep working, because they read the same record.
4. **Lunar worlds feed the rest of the system.** A lunar propellant colony gives
   off-window launches before Asteroid Mining. A mass driver adds module
   fabrication. Helium-3 helps Fusion Plants. And the Moon's room makes an
   era-10 Extraplanetary Base worth building.
5. **Under Full Colonies the Moon is part of Earth's battleground.** A power
   holding Earth orbit can close in on, blockade, seize or destroy an enemy's
   lunar colony there.

Races Only keeps its rules: the Moon is stage 0, which locks Mars until every
lunar world is claimed.

## 3. The Moon in Solar System Colonization

### 3.1 The six worlds

Six rows join `SITES` in `scripts/generators/gen_solar_sites.py`, at stage 0,
location `earth` (§ 8), launch-window body `None` (never gated, as Mercury), icon
kind `moon`. Founding events `space_race_colony_events.35` to `.40`. The figures
are first guesses for the balance pass (§ 11).

| Key | World | People room (k) | Slots | Base room | Grade | Specialization I | Specialization II | Moon Landing site |
|---|---|---|---|---|---|---|---|---|
| `shackleton` | Shackleton Crater (south pole) | 25 | 2 | 15 | 0 | **Propellant Depot**: propellant depots (§ 3.5), +2% Launch Capacity output | **Polar Outpost**: +0.2 space race progress, +1% research speed | Shackleton Crater |
| `peary` | Peary Crater (north pole) | 15 | 1 | 10 | 0 | **Solar Power**: +10% Orbital Solar Collector throughput | **Polar Observatory**: +2% research speed, +25 innovation cap | — |
| `tranquility` | Tranquility Base (Mare Tranquillitatis) | 20 | 2 | 20 | +5 | **Heritage Site**: +6% cultural pull, +1% prestige, +5% Tourism Industry throughput | **Helium-3 Extraction**: +10% Fusion Plant throughput, +3% Extraplanetary Base throughput | Sea of Tranquility |
| `marius_hills` | Marius Hills (Oceanus Procellarum) | 40 | 3 | 25 | +5 | **Lava Tube City**: +4% cultural pull | **Hardened Installation**: +3% military research speed, +3% influence, −2% military goods cost | Equatorial Plain |
| `daedalus` | Daedalus Crater (far side) | 10 | 1 | 10 | 0 | **Radio Telescope**: +3% research speed, +25 innovation cap | **Deep-Space Relay**: +0.3 space race progress | Far side of the Moon |
| `imbrium` | Mare Imbrium | 25 | 2 | 25 | 0 | **Mass Driver**: +3 module fabrication points a month (`country_sr_module_fabrication_add`), +2% Launch Capacity output | **KREEP Mining**: +5% Extraplanetary Base throughput, +2% Advanced Materials output | — |

Notes:

- Base room is five times the column's since 2026-10-31 (owner): 75, 50, 100,
  125, 50 and 125.
- Every modifier named above is registered today. Shackleton's propellant depots
  need one new script-only boolean, `country_sr_propellant_depots_bool`
  (`common/modifier_type_definitions/`), read by `sr_launch_has_depots`.
- The three Moon Base purposes live on as specializations: scientific in
  Daedalus's Radio Telescope, industrial in Imbrium's Mass Driver, military in
  Marius Hills's Hardened Installation. The save migration (§ 10) uses this
  mapping.
- The lunar total is 135,000 people of room and 105 Extraplanetary Base levels.
  For scale, Valles Marineris alone holds 50,000 and 40 levels, and 16 Psyche
  holds 60 levels.
- **No Spaceport** on a lunar world: fleets dock at Earth, which is the same
  location (§ 8). A lunar world's slots hold Habitats and Defenses.
  `MODULE_TYPES` gains a per-site exclusion.
- **Shipping** (`SHIPPING`, which a blockade stops) is re-derived from the
  modifiers by `test_solar_sites.py`, as for every world.
- **Discoveries:** none in this design. Two are natural later additions (the
  cold traps' comet-water record at Shackleton, an intact lava-tube network at
  Marius Hills).

### 3.2 Stage 0 and the goal

The Moon is **stage 0** (`STAGE_GOALS[0]`, read as
`sr_colonization_goal_stage_0`). Stage 0 leaves stages 1 to 5, the Deep Space
gate's "stage 3" and every save's stage variable unchanged.

The goals rise (owner, call 11). Colonization now opens an era earlier, the new
technologies add funding (§ 5), and the soft cap lets a program fund past it
(§ 5.1), so the same goals would go faster than today's race:

| Stage | Worlds | Goal today | Goal |
|---|---|---|---|
| 0 | The Moon | — | **300** (the Moon Base's; 2/3 of Mars) |
| 1 | Mars and the asteroids | 400 | **450** |
| 2 | Jupiter and Venus | 450 | **525** |
| 3 | Mercury and Saturn | 500 | **600** |
| 4 | Uranus and Neptune | 550 | **700** |
| 5 | The Kuiper Belt | 650 | **800** |

The steps widen with distance: the outer worlds are reached later, with more
funding, at a faster pace. The overview's stage cell reads "Stage: the
Moon" in place of "Stage: 0 of 5". The automatic pick's score
(`SCORE_PER_STAGE` × stage) then favors the Moon, which the AI follows too.
Cede Colony's AI value is `AI_VALUE_BASE` (20) for a lunar world.

Under Races Only, stage 0 locks like any other stage: stage 1 opens for everyone
once all six lunar worlds are claimed. A save already past stage 0 treats the
lunar worlds as an earlier stage's released worlds, which Races Only lets anyone
target today.

### 3.3 Transit: founded the month the fleet leaves

The Moon has no launch window and no transit. Under Simple and Full Colonies a
fleet bound for a lunar world founds it in its launch month, through the path
Races Only uses today (`sr_cf_found_now_<key>`, generated). It never takes a
fleet slot or joins an inbound record, so two countries cannot race fleets in
flight to the same lunar world: whoever launches first takes it, and the world
is no longer a target for anyone else that month.

- `gen_launch_windows.py`: the Moon is a transit-only body, as Mercury, with 0
  months on every drive (a constant, not an orbit). A **module shipment** leaves
  any month and lands at the next monthly step: within the month if the global
  step runs after the country pulse, otherwise the month after.
- **Autonomy:** the distance term (+0.01 a month of transit) is 0, so a lunar
  colony drifts down with the pull of home (−0.25 a month) unless war,
  isolation or a garrison push it up. Lunar colonies stay loyal.
- **Settlers** go as to any world.
- **Under Full Colonies, a blockaded Earth bars every launch, to the Moon
  too** (`sr_launches_barred`, unchanged).

### 3.4 The landing site's discount

The Moon Landing's "Where the Eagle Shall Land" choice (`sr_moon_site_*`) gives
**−25% progress** on the lunar world it names (table in § 3.1), for that country
only, so 225 against 300. Equatorial Plain maps to Marius Hills. Peary and
Imbrium match no landing site. The discount enters the world's
`sr_cf_cost_<key>` (generated) as a factor read from the country's landing
choice. The world's hover and the Target row show the discounted cost. This is a
soft advantage: the world stays open to everyone.

### 3.5 Propellant depots from the Moon

Today `sr_launch_has_depots` is Asteroid Mining (era 11): off-window launches at
the premium. It becomes Asteroid Mining **or** `country_sr_propellant_depots_bool`,
which Shackleton's Propellant Depot carries. A country holding Shackleton on
that specialization can launch outside windows in era 10. It loses this while
Shackleton is blockaded, because the specialization ships.

### 3.6 The first lunar colony

The **first lunar world a country founds with its own fleet** runs today's
`sr_complete_moon_base_effect`:

- it sets `sr_completed_moon_base`;
- it adds `sr_first_moon_base` or `sr_moon_base`;
- it sets the global first and `sr_was_first_moon_base`, with the notice to
  everyone else.

A world received by treaty, inheritance, seizure or a free colony's petition
doesn't count, just as `sr_has_space_colony`'s "real claims" are counted today.
Event `space_race_events.6` (the Moon Base's completion) is rewritten as the
first lunar colony's, and plays after that world's founding event. The
variable's name stays `moon_base` so that every reader below works unchanged
(§ 7).

The Program row's fifth icon reads **Lunar Colony**: lit once you have founded
one, with the flag if you were first; faint while you haven't, or once another
power was first. It is no longer half-lit "under way", since there is no
separate bar.

## 4. Opening colonization in era 10

| | Today | After |
|---|---|---|
| Technology | Directed Energy Weapons (era 11) | **Cislunar Infrastructure** (era 10, § 5) |
| Milestones | Moon Base and Mars Landing | Moon Landing; **beyond the Moon**, the Mars Landing too |
| Space Program method | Solar Colonization: 25,000 Launch Capacity a week | Solar Colonization, unlocked by Cislunar Infrastructure: **10,000** |
| Innovation cost factor | ×8 | **×5** until the Mars Landing, then ×8 |
| Module fabrication, Orbital Assembly | Directed Energy Weapons | Cislunar Infrastructure |

- **`sr_solar_colonization_qualified`** becomes the Moon Landing.
  **`sr_colonization_beyond_moon`** (new) is the Mars Landing. It is checked
  everywhere a world of stage ≥ 1 is eligible:
  - the Target button;
  - the automatic pick's eligibility;
  - Races Only's draw and stage advance (`gen_solar_sites` emits it per world).

  A country given a world beyond the Moon by treaty keeps it and colonizes only
  the Moon until its own Mars Landing. Its panel says why.
- **The JE** (`je_space_race_solar_colonization`): `is_shown_when_inactive` and
  `possible` read the Moon Landing and Cislunar Infrastructure in place of the
  Moon Base, the Mars Landing and Directed Energy Weapons. The colony-holder
  branch is unchanged.
- **The method's bill** (`pm_solar_colonization`): 25,000 was sized for era 11's
  Ablative Rockets (70 Launch Capacity a level). Era 10 has Reusable Rockets
  (50), and every funding level adds 25% to the bill. 10,000 is twice the Mars
  Mission's. Deep Space Exploration (50,000) and Interstellar (100,000) are
  unchanged.
- **The cost factor** (`sr_cost_factor_solar_colonization`) becomes a value:
  5 (the Moon Base's) while the country lacks the Mars Landing, 8 after.
- **Decisions** (`extra_decisions.txt`):
  - Begin Solar Colonization appears while the Space Program runs the Moon
    Mission or the Mars Mission, needs the Moon Landing, and needs worlds left
    that it can reach: stage 0 to 2, or any stage once you hold a colony
    beyond the Moon.
  - Begin Deep Space Exploration needs the Mars Landing in place of the Moon
    Base and the Mars Landing.
- **The Deep Space gate** (a country with no colony needs Deep Space Exploration
  for stage 3 and beyond) counts **colonies beyond the Moon** only. Otherwise an
  easy lunar colony would void it.
- **The Mars Mission method** allows the Mars Landing only, since the Moon Base
  is gone. Each method still includes the ones before it, so the colonization
  method also runs the Mars Landing.

## 5. Technologies

New:

| Technology | Era | Category | Requires | Gives |
|---|---|---|---|---|
| `cislunar_infrastructure` (Cislunar Infrastructure) | 10 | military | `reusable_rocketry` | `pm_solar_colonization`; `pm_sr_fabrication_orbital_assembly`; opens Solar System Colonization; **+2 funding cap** |
| `in_situ_resource_utilization` (In-Situ Resource Utilization) | 10 | military | `reusable_rocketry` | `building_space_mine` with Regolith Processing (§ 6); **+1 funding cap** |
| `nuclear_thermal_propulsion` (Nuclear Thermal Propulsion) | 11 | military | `cislunar_infrastructure` | The smaller off-window premium (§ 9); **+1 funding cap** |

In-Situ Resource Utilization was drafted as a production technology that also
required Additive Manufacturing. It shipped as military, needing Reusable Rocketry
only (PR1): Asteroid Mining, which requires it, is military, and a technology's
prerequisites must share its category (`scripting_best_practices.md` § Same-category
prereq rule).

Changed:

- **Directed Energy Weapons** keeps its funding level, the Laser Broom, Ground
  Lasers, ship and fleet-fire effects. It no longer opens colonization or
  fabrication. Its header comment and the player guide's propulsion table
  ("Directed Energy Weapons (opens colonization)") change with it.
- **Asteroid Mining** requires In-Situ Resource Utilization and Directed Energy
  Weapons, in place of Reusable Rocketry and Directed Energy Weapons. It unlocks
  the Asteroid Mine method (§ 6) and the near-Earth room (§ 6), and keeps
  propellant depots.
- **Reusable Rocketry** no longer gates the Moon Base. Its comment is updated.

Funding cap: today it is 3, plus 1 from each of eleven technologies in eras 7
to 11 and 2 from each of four in era 12, plus 1 from tier V of Advanced
Research. With every space technology a country has 10 by the end of era 10,
14 by the end of era 11 and 22 by the end of era 12. The three new ones add 4
(owner, call 12), so 13 by the end of era 10, 18 by the end of era 11 and 26 by
the end of era 12. The player guide's count changes.

### 5.1 Funding past the cap

The cap becomes soft (owner, call 12). A milestone's funding may go up to **6
levels past the cap**. Each level past it counts for less pace than the one
before: the first for 1/2, the second for 1/3, up to the sixth for 1/7. Every
level still costs in full.

| Levels past the cap | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| This level's pace | +0.25 | +0.17 | +0.13 | +0.10 | +0.08 | +0.07 |
| Effective levels past the cap | 0.50 | 0.83 | 1.08 | 1.28 | 1.45 | 1.59 |

The pace is +0.5 a month per effective level; the 0.5 is the weight of one
level below the cap. The ceiling of 6 is for the script, whose ladder has to
end somewhere. A seventh level would add 1/8 of a level for a full level's
cost, which nobody would buy.

**What is paid in full, and what is reduced:**

- **Paid in full:** a level past the cap still costs 15 innovation a week ×
  the cost factor, and still adds +25% Space Program throughput, which raises
  the Launch Capacity bill.
- **Reduced:** only the pace.

Because throughput isn't reduced, a level past the cap also raises the
program's other workforce-scaled output (module fabrication points, debris
removal) by the full 25%. That is the same price-for-output trade as below the
cap: a full level's Launch Capacity buys a full level's output. The cap only
limits progress.

**Script:**

- `sr_funding_progress` splits in two: `sr_funding_progress`
  (`country_space_race_progress_add = 0.5`) and a new `sr_funding_throughput`
  (`building_space_program_throughput_add = 0.25`).
- `sr_apply_milestone_cost_modifiers_base` gives the first
  `multiplier = sr_funding_<m>_effective`, a new value: the level up to
  `sr_max_funding_level`, plus a six-step ladder for the excess. It gives the
  second `sr_funding_<m>_level`, as now.
- `sr_possible_fund_up` tests `sr_max_funding_level` + 6.
- A save's existing entries pick the split up through the monthly
  `sr_cost_modifiers_missing` repair. Its test is extended to the new modifier.
- A cap that falls below a milestone's level, for example when a power bloc
  principle is lost, leaves the level standing. The excess simply counts past
  the cap.

**Panel:**

- The Funding stepper reads "9 / 7 (+0.8)" past the cap: the level, the cap,
  and the effective levels the excess adds.
- The plus button's tooltip gives the next level's fraction ("+1/3 of a level
  of pace, full cost").
- The pace hover lists funding as below-cap levels and above-cap effective
  levels.

**The AI** stays within the cap in the first build. Observer runs then decide
whether a great power in a contested race, with innovation to spare, should go
one or two levels past it.

Commercial Space Industry is unchanged: after the race, funding adds nothing.

### 5.2 Icons

Each new technology needs an invention icon. Placeholders that copy existing
ones are enough for the first build: `reusable_rocketry.dds` for Cislunar
Infrastructure, `asteroid_mining.dds` for In-Situ Resource Utilization,
`fusion_power.dds` for Nuclear Thermal Propulsion. The icon pipeline can replace
them later. `texture_reference_audit` checks the paths. Icon batch 7 (2026-10-30)
painted all three, and the Moon's colony icon, which had been a copy of Mercury's.

## 6. The Extraplanetary Base from era 10

- **Unlock:** `building_space_mine`'s `unlocking_technologies` becomes
  `in_situ_resource_utilization`.
- **New default method `pm_regolith_processing`** (Regolith Processing). It is
  the first in `pmg_base_building_space_mine` and has no unlocking technology of
  its own. First guess:
  - Inputs, half the Asteroid Mine's: 15 electronic components, 15 radios, 5
    digital access, 60 Launch Capacity. That is £15,000 a week at base prices.
  - Outputs: 175 iron, 95 tech metals and 50 glass, £16,600.
  - Staff: 800 (500 machinists, 250 engineers, 50 academics).

  It is weak on purpose: a foothold that the Moon's room makes worth a few
  levels. Margin is one of three measures (owner, call 10). Profit per
  construction point says what a level repays on the 20,000 it costs. Profit
  per worker is the wage it can pay, and so how rich an economy can still run
  it.

| Method (base prices, goods only) | Profit a level a week | Margin | Per worker (wage it can pay) | Per 1,000 construction |
|---|---|---|---|---|
| Regolith Processing (era 10) | £1,600 | 11% | 2.0 | £80 |
| Asteroid Mine (era 11) | £7,250 | 24% | 7.25 | £363 |
| Mining Colony (era 12) | £37,000 | 33% | 37.0 | £1,850 |
| Deep-Sea Mine (era 11, before its support vessels; 5,000 construction) | £26,300 | 143% | 26.3 | £5,260 |

  A first draft had 1,000 staff, and so 1.2 a worker. That sits in the bottom
  quarter of the era-10 methods' cost comments (their quartiles are 1.4, 1.8 and
  2.5, counting automation tiers), which is too little for the great powers
  that build the base. At 800 staff it pays a little above the era-10
  median, so a rich economy can staff it. Its return on construction stays a fifth of the
  Asteroid Mine's, which is itself the weak investment of era 11 beside the
  Deep-Sea Mine (Global Commons § 1.1). In the per-construction measure,
  Regolith Processing is a toehold, not an investment. That is the intent: the
  reasons to build it are lunar room, the Mining and Resort Colony methods
  ahead, and the Commercial Space Industry once the race is over.
  `pm_costs` rewrites its cost comment on reload.
- **`pm_space_mine`** (the Asteroid Mine) gains
  `unlocking_technologies = { asteroid_mining }`. The Mining Colony and Resort
  Colony methods keep Space Colonization. The era-12 logistics groups are
  unchanged.
- **Room before Asteroid Mining.** The near-Earth asteroids' 10 levels
  (`NEAR_EARTH_ROOM`) need Asteroid Mining. Before it, a country's room is its
  lunar (and any other) colonies' room. Levels past the room work at −50% as
  today. So in era 10, a base without a lunar colony runs a weak method at half
  output: possible (soft cap), rarely worth it.
  `sr_ebase_room_total`'s constant becomes conditional on the technology.
- **Balance constraint:** `test_deep_sea_rebalance.py` compares the base with the
  Deep-Sea Mine era by era. Regolith Processing is era 10, when there is no
  Deep-Sea Mine, so the test must learn the new method and skip the comparison
  for era 10. Every later ordering it holds is unchanged.
- The Commercial Space Industry's "does nothing until you build Extraplanetary
  Bases (Asteroid Mining)" becomes In-Situ Resource Utilization.

## 7. Retiring the Moon Base milestone

Removed:

- `je_space_race_moon_base`, retired the way the mod retires entities:
  - it stays defined, with `is_shown_when_inactive` and `possible` always
    false;
  - an old save's open entry is migrated (§ 10) and removed.
- The purpose event `space_race_events.82` and its `sr_choice_moon_base_*`
  modifiers. The event stays defined for an open copy in an old save, with one
  option that does nothing.
- The Moon Base's row in the mission-profile table, its "first" row (now the
  first lunar colony), its decision prerequisites, and its goal and risk values
  (`sr_moon_base_goal` and its kin, which become dead).
- The Moon Base setback themes (`.14`, `sr_setback_is_crewed_outpost`) move to
  Solar System Colonization while its next fleet is bound for the Moon.

Kept (they read `sr_completed_moon_base`, `sr_was_first_moon_base`,
`sr_global_first_moon_base` or the modifiers, which § 3.6 now sets):

| Reader | File | Change |
|---|---|---|
| Program row and Space Powers | `space_race_display_values.txt`, `space_race_custom_loc.txt` | Label "Lunar Colony"; no "under way" state |
| Achieved count | `space_race_values.txt` (`sr_power_achieved`) | None |
| UN regime count | `un_regime_values.txt` | None |
| Ahead in space | `covert_warfare_triggers.txt` | None |
| Grand Monument lunar moment | `gm_commission_effects.txt` | None (already "lunar colony") |
| Nation tab | `gen_nation_tab.py` output | None |
| `sr_space_race_concluded` | `space_race_triggers.txt` | **Drop** `sr_completed_moon_base`: a power that never founds a lunar colony (all six taken) must still conclude, so that Commercial Space Industry applies |

## 8. Full Colonies: lunar worlds at Earth

The fleets keep nine locations. "Earth and the Moon" is one location, as the
fleets design set it, and the lunar worlds sit there (`location = "earth"`).
`gen_space_fleets` then emits their per-world blocks (world sums, assault,
integrity, seizure, destruction) into Earth's pass automatically. What changes:

1. **Close in at Earth.** At Earth every fleet counts as stationed
   (`sr_fl_gather_at` forces posture 1). A fleet at Earth may now take Close
   in, on a lunar world held by a country at war with it, or on a free lunar
   colony (with its infamy, as elsewhere).
   - The posture button at Earth offers Station and Close in, shown only while
     such a world exists.
   - The target button steps through those worlds.
   - Gathering keeps posture 3 at Earth when its target is a lunar world.
   - A closing-in fleet at Earth is engaged by every hostile fleet there, the
     Orbital Battlestation and the batteries, all of which count as stationed.
     It fires on the stationed and on the world's Defenses.
   - Integrity, Seize and Destroy follow the generic rules. Seizure is
     occupation until the peace, and destroying costs 20 infamy and the rest.
2. **Blockade.** A lunar world is blockaded while its holder's Earth is
   blockaded (`sr_earth_blockaded` in the holder's scope). A blockaded holder
   launches nothing anyway, so the blockade also stops the world's shipping
   specializations and its base room, as at any blockaded world.
3. **Interdiction** is not offered at Earth. At peace, a country's home fleet at
   Earth would face the interdictor, so the rule would rarely bite. This is a
   follow-up if play-tests want it.
4. **The AI at war:**
   - It closes in with its strongest fleet at Earth on the enemy's lunar world
     with the most people and modules, when its fleets at Earth hold orbit
     against that enemy (the enemy's Earth is blockaded by it or an ally).
   - It seizes when its marines outnumber the garrison and militia, and
     otherwise stays stationed.
   - It never destroys, as elsewhere. Its defense is unchanged: the home fleet
     is already at Earth.
5. **Orbital Superiority** counts closing-in fleets at Earth as at Earth.

## 9. Nuclear Thermal Propulsion: a smaller premium

The off-window premium is the rocket equation's extra propellant at a
methane-oxygen engine's exhaust velocity, `exp(extra Δv / 3.7 km/s) − 1`
(`gen_launch_windows.premium_from_extra`). A nuclear thermal engine runs at about
9 km/s (Isp about 900 s), so the same extra Δv costs
`(1 + p)^(3.7 / 9) − 1` of that. Off-window launches stay gated on depots
(§ 3.5); NTP makes them cheaper.

| Mars, months after the window | Chemical premium | NTP premium |
|---|---|---|
| +1 | about +40% | about +15% |
| +2 | about +150% | about +46% |

Implementation, all in `gen_launch_windows.py`:

- a second premium tree, `sr_launch_premium_ntp_<body>`;
- its cached reader, `sr_window_premium_now_ntp_<body>`;
- a country reader, `sr_launch_premium_<body>`, that picks it with the
  technology.

`sr_launch_cost_<body>`, `sr_launch_target_cost_<body>`,
`sr_launch_months_cost_<body>` and the Next Windows display read the country
reader. The report gains the NTP curve.

As built (PR 3a): `sr_launch_premium_<body>` was already the chemical curve,
which the global cache refresh reads in no country's scope, so the country
reader is `sr_window_premium_country_<body>`; the cache holds the NTP curve as
`sr_window_cost_ntp_<body>`. The country reader acts on the technology's
marker, `country_sr_nuclear_thermal_launches_bool` (`sr_launch_has_ntp`), not on
the technology itself, so the tooltip line and the effect share one source.
The tree is computed from the extra Δv at 9 km/s, rounded once, so it can differ from `(1 + p)^(3.7 / 9) − 1` on the stored,
rounded p by under a hundredth. Transit, drives, fleets, yards and
refits are untouched: NTP vehicles fly near-Hohmann transfers, so their transit
is chemical's.

## 10. Save migration

Once, from the global step's migration (`sr_sites_global_monthly`, beside
`sr_sites_initialized`), behind a new `sr_lunar_initialized` flag:

1. **A country with `sr_completed_moon_base`** (it finished the old milestone)
   keeps its reward modifier and variables, and is given one lunar world:
   - the one its purpose maps to (§ 3.1: scientific Daedalus, industrial
     Imbrium, military Marius Hills) on that specialization;
   - with no purpose recorded, Tranquility Base on Heritage Site;
   - if that world is taken, the next free one in table order;
   - with none free, none.

   Countries are taken in order of completion where the save can tell
   (`sr_was_first_moon_base` first), otherwise as `every_country` finds them.
   The world is founded quietly (no founding event, a notice). It does not
   count as a "founded" first lunar colony again.
2. **An open `je_space_race_moon_base`:** its progress moves onto Solar System
   Colonization's bar, up to one lunar goal (300), once that entry runs, and
   the entry is removed. Its funding and approach variables are cleared
   (`sr_cleanup_milestone_variables_effect`).
3. **The colonization prerequisites** (§ 4) apply at once: a country that had
   the Moon Base but not the Mars Landing in an old save colonizes the Moon only
   until it lands on Mars.

`je_immediate_reset_audit` and a revolution's winner: every new record is a
country or global variable, so the winner continues the nation.

## 11. Numbers at a first guess

| Figure | Value | Where |
|---|---|---|
| Stage goals | 300, 450, 525, 600, 700, 800 | `STAGE_GOALS` (§ 3.2) |
| Landing-site discount | −25% | § 3.4 |
| Colonization method's Launch Capacity | 10,000 a week | `pm_solar_colonization` |
| Colonization cost factor | 5 before the Mars Landing, 8 after | `sr_cost_factor_solar_colonization` |
| Funding cap | +2 Cislunar Infrastructure, +1 In-Situ Resource Utilization, +1 Nuclear Thermal Propulsion | § 5 |
| Funding past the cap | up to 6 levels, worth 1/2, 1/3, … 1/7 | § 5.1 |
| Regolith Processing | £1,600 a level, 2.0 a worker | § 6 |
| Lunar people room, base room, grades | § 3.1 | `SITES` |
| NTP exhaust velocity | 9 km/s | § 9 |

A rough era-10 pace check. With every space technology through Cislunar
Infrastructure and In-Situ Resource Utilization, the cap is 13. Pace is the
program (+1), +0.5 a funded level on every running milestone, and +0.2 from
Reusable Rocketry. At funding 8 on colonization alone, on Standard, that is
5.2 a month: a lunar colony (300) every 58 months, 43 at the landing site.
Funding 8 on the Mars Landing as well gives 9.2 a month: a lunar colony every
33 months and Mars (450) every 49. Ambitious is ×1.5.

The cap is rarely what binds. 8 levels on colonization alone cost 600
innovation a week at cost factor 5, and they triple the Space Program's Launch
Capacity bill (+200% throughput, to 30,000 a week). The innovation and Launch
Capacity bills are the real limits, and the soft cap lets a rich program trade
them for pace past the cap. Expect two or three lunar worlds and perhaps one on
Mars for a strong power entering era 11.

## 12. Files touched

- **Generators:**
  - `gen_solar_sites.py`: six rows, stage 0, the exclusions (no Spaceport),
    the beyond-the-Moon gate, the landing discount, `sr_cf_found_now` for the
    Moon, the lunar panel group, the conditional near-Earth room.
  - `gen_launch_windows.py`: the Moon as a 0-month transit-only body; the NTP
    premium.
  - `gen_space_fleets.py`: Close in at Earth, the lunar blockade, the AI.
  - `gen_nation_tab.py`, if a row's label changes.
- **Script:**
  - `je_space_race.txt`: the JE gates; the Moon Base retired.
  - `space_race_triggers.txt`: qualified, concluded, beyond the Moon.
  - `space_race_values.txt`: cost factor, goals.
  - `sr_launch_window_triggers.txt`: depots.
  - `sr_fleet_combat_effects.txt`: gather at Earth.
  - `sr_site_effects.txt`: the migration.
  - `space_race_effects.txt`: first lunar colony.
  - `extra_decisions.txt`: the two decisions.
  - `space_race_colony_events` 35 to 40, and event .6 rewritten.
  - `space_race_modifiers.txt`: twelve specializations.
  - `mod_entity_modifier_types.txt`: the depots boolean.
- **Content:**
  - `era_10.txt`, `era_11.txt`: three technologies.
  - `extra_buildings.txt`: the space mine's unlock.
  - `extra_pms.txt` and `extra_pm_groups.txt`: Regolith Processing.
  - The space race PMs: `pm_solar_colonization` and the fabrication method's
    unlocks and bill.
- **Localization:** six worlds and their events, twelve specializations, three
  technologies, the method, the "Lunar Colony" icon and the stage name. Then
  `organize_loc.py`.
- **Art:**
  - `gfx/interface/icons/space_race_icons/colony_moon.dds`;
  - three invention icons (placeholders, § 5);
  - each founding event's `event_image` (an existing space race image will
    do; `event_image_audit`).
- **Docs:**
  - `docs/systems/mod_systems/space_race.md`, Space Race;
  - `docs/player_guide/16-space.md`, `02-timeline.md`, `17-reference.md` and
    the events appendix, then the PDF;
  - `docs/testing/solar-colonies-playtest.md`;
  - this design's row in `docs/superpowers/README.md`.

## 13. Build order

Three PRs, each green on its own:

1. **Technologies and the base** (§§ 5, 6):
   - the three technologies;
   - the colonization method and fabrication on Cislunar Infrastructure, with
     the bill and the cost factor;
   - the base on In-Situ Resource Utilization with Regolith Processing;
   - the Asteroid Mine on Asteroid Mining, and the conditional near-Earth room.

   Until PR 2 lands, colonization still needs the Moon Base, which Reusable
   Rocketry still offers in era 10.
2. **The Moon** (§§ 3, 4, 7, 10):
   - the six worlds, stage 0, same-month founding, the landing discount and
     lunar depots;
   - the gates (the Moon Landing, beyond the Moon on the Mars Landing);
   - the Moon Base retired, the first lunar colony, the decisions;
   - the migration.
3. **The Moon under fire, and NTP** (§§ 8, 9): Close in at Earth, the lunar
   blockade, the AI; the NTP premium curve.
4. **Funding past the cap** (§ 5.1). Independent of the other three, so it can
   land at any point; the funding levels the new technologies add ride with
   PR 1.

Each PR carries its player guide changes and the rebuilt PDF.

## 14. Tests and checks

- `test_solar_sites.py`: the table against the six new founding events, stage 0,
  no window body, no Spaceport. Its re-derivations cover the rest.
- `test_launch_windows.py`: the committed files fresh, with the Moon's 0 months
  and the NTP curve. A new case: NTP premium = `(1 + p)^(3.7/9) − 1` within
  rounding.
- `test_space_fleets.py`: freshness. A new case: posture 3 survives gathering
  at Earth only for a lunar target.
- `test_deep_sea_rebalance.py`: era 10 skipped, later orderings held.
- Funding past the cap (new, or in `test_space_race_billing.py`):
  - `sr_funding_<m>_effective` equals the level up to the cap, and the
    harmonic sum past it, for each of the six steps;
  - the throughput multiplier stays the raw level;
  - the fund-up ceiling is the cap + 6;
  - the approach-cost equality `test_space_race_approaches.py` holds is
    unchanged.
- Space race tests that count 34 worlds, 7 milestones or the Moon Base JE are
  updated: a sweep with `git grep -n "34\b\|moon_base" -- 'test_*.py'`.
- `je_immediate_reset_audit`, `loc_coverage_audit`, `event_image_audit` and
  `texture_reference_audit` on reload.
- Play-test list (`docs/testing/solar-colonies-playtest.md`):
  - a lunar fleet founds in its launch month;
  - Close in at Earth on a lunar world, then seize and destroy;
  - the migration on a save with a finished and an open Moon Base;
  - an era-10 base with and without lunar room.

## 15. Open questions

1. **Names:** Cislunar Infrastructure, In-Situ Resource Utilization, Regolith
   Processing, and the six worlds' specialization names.
2. **The bill:** 10,000 Launch Capacity, or tie the method's bill to the stage
   the next fleet is bound for (smaller while only the Moon is open)?
3. **Interdiction of lunar worlds** (§ 8.3): leave it out, as proposed?
4. **Lunar Foundries** (Space Colonization's fabrication method) and Imbrium's
   Mass Driver overlap in theme. Rename Lunar Foundries ("Orbital Foundries"),
   or leave both?
5. **The stage goals** (§ 3.2) are a first guess. Is 300 for the Moon (2/3 of
   Mars) the right step, and is the rise for the later stages wanted?
6. **The AI past the cap** (§ 5.1): it stays within the cap until observer runs
   say otherwise.

## 16. As built (2026-10-29)

Built in #1233 (funding past the cap), #1234 (technologies and the base), #1235
(NTP), #1236 (the six lunar worlds), #1237 (the Moon at Earth) and #1238 (the
Moon Base retired, the gates, the migration); #1239 changed the wording.

**Owner's answers to § 15:** the names and the flat 10,000 bill stay;
no interdiction at Earth; Lunar Foundries is renamed Orbital Foundries (text
only); the stage goals stand as drafted; the AI stays within the cap.

**Later owner calls:**

- **Old saves where every colony was already claimed** keep their rewards. No
  completion, Interplanetary Trade Networks or Commercial Space Industry is
  removed, and the Moon opens to them. A country takes it only by choice:
  Resume Solar System Colonization, or Begin Solar Colonization, sets
  `sr_colonization_resumed`, and the entry needs it in such a save.
- **Player-facing text calls a colony site a "site"**, not a "world" (#1239).
  Next Windows, which lists one line per body, says "destination".

**Rulings made in the build:**

- In-Situ Resource Utilization is military and needs only Reusable Rocketry
  (§ 5's note).
- PR2 was split into 2a (the worlds) and 2b (the retirement), and PR3 into 3a
  (NTP) and 3b (the Moon at Earth).
- The Races Only landing discount applies to a chosen Target, not to the
  random draw.
- The six worlds are appended to `SITES` as indices 35 to 40, because indices
  are stored in saves.
- The hand-written world count of 34 became a generated value.
- Under every setting, stages 3 to 5 need Deep Space Exploration or a colony
  beyond the Moon. A lunar colony alone doesn't open them.
- The generic blockade step can never fire at Earth, so a lunar world's
  blockade is § 8.2's Earth rule, in place of the generic step.
- The AI closes in on a lunar world only while no enemy fleet is at Earth (a
  stationed enemy bars the seizure). It picks the target first, then the
  strongest fleet whose marines are enough.
- The Target button charges the free-colony price only while the fleet closes
  in.
- Begin Solar Colonization is shown while a site it reaches is free, after
  the race too (main hid it once the race was over), except to a finished
  program, which sees it only while a lunar site is free.

**Left for the owner:**

- **Lunar garrisons:** Land and Embark aren't offered at Earth, so a lunar
  colony's garrison is its militia.
- **Attackers closing in at Earth** are docked: they repair and refill supply
  and marines every month.
- **Finished without choosing:** once the race is over
  (`sr_all_colonies_complete`, which stays set), a colony holder whose
  colonization program is running and that hasn't chosen to resume for the
  Moon is marked finished the next month and gets Interplanetary Trade
  Networks. That covers a migrated holder whose colonization entry was open in
  an all-claimed save, and one that begins colonization after the race for a
  released site beyond the Moon.
- **The Races Only best cost** ignores the stage 3 to 5 Deep Space gate.
- **The AI past the cap:** it stays within the cap, as answered; revisit
  after observer runs.
- **German and Spanish:** settle a word for "site" before the next
  translation pass.
