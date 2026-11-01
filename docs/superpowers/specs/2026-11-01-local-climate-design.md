# Local Climate: a climate record per state, and comfort as migration attraction

Date: 2026-11-01. Owner request, reached in conversation: remove the arable land
minimum for mass migration targets, and in its place represent how climate
shaped where people chose to live. Coasts held denser populations than equally
fertile interiors because their temperatures were milder, and the US South
stayed thinner than its land suggests until air conditioning. Each state gets a
small climate record (a handful of numbers) that feeds a comfort score, comfort
feeds migration attraction, technology eases each kind of discomfort at its own
time, and global warming moves the record. Calls the owner did not make are
marked *(designer's call)*; the builder may revisit those with a stated reason.

## 1. Why

- **The arable land minimum is a poor guard, and it shuts out small places.**
  `MASS_MIGRATION_TARGET_MIN_ARABLE_LAND = 10` (vanilla `NPops`) keeps a state
  below 10 arable land from ever being a mass migration target. That excludes
  city-states, treaty ports and partial states, whose share of a region's arable
  land is small: Hamburg's two provinces of Elbe hold about 5 of the region's
  30. It also stops guarding late in the game, because the mod's technologies
  multiply arable land several times over and most marginal land clears 10
  (owner).
- **Removing it opens deserts and mountains** unless something else says where
  people want to live. That something should be climate.
- **Climate drew people historically**, and nothing in the base game or the mod
  says so today. Vanilla's desert traits cut farming, construction and
  infrastructure but not migration, and vanilla's malaria traits sit only on
  Africa, Indonesia and the Pacific islands, so the US South carries no
  disease mark.
- **Base appeal is not the score to reuse.** The conversation started from
  "rebrand or split base tourism appeal into comfort". Base appeal is a
  tourist's score: it rates Wyoming 90 and Alaska 80 for Yellowstone and the
  glaciers, exactly the places people did not settle. Comfort needs its own
  numbers.

## 2. Goals, non-goals, anti-goals

**Goals**

1. Every land state region has a climate record: summer heat, summer
   humidity, winter cold, aridity, malaria, latitude.
2. The record produces a comfort penalty in migration attraction, so harsh
   climates draw fewer migrants, both within a market and as mass migration
   targets (the owner's reading: mass migration attraction is mostly ordinary
   migration attraction).
3. Technology eases each part of the penalty on its own schedule: cold early,
   disease and water in between, heat late (air conditioning).
4. Global warming shifts the record's temperatures, so hot places get less
   comfortable and cold ones more.
5. The state panel shows the record and what it costs the state, following the
   mod's state panel tiles (Homeland Dynamics, Migration Crowding, the tourism
   card).
6. The arable land minimum for mass migration targets goes, along with the
   penalty for countries with few target states (the owner's original lean was
   to set it to 1).

**Non-goals (v1)**

- Agriculture reading the climate record. This is v2 (owner): it overlaps
  vanilla's desert and soil traits and the mod's arable land technologies.
- Any change to base tourism appeal. Comfort does not feed tourism. If a later
  version ties sun and beach tourism to the record, the climate part of base
  appeal has to come out first, or it counts twice.
- The Demographics census reading the record's malaria. The census keeps its
  own malaria factor from vanilla's traits *(designer's call)*: switching it is
  a recalibration of a fitted system, and it belongs with v2. Until then the
  Local Climate tile can mark Georgia malarial while the census does not.
- Air conditioning as electricity demand ("tech or something", owner). v1
  makes it a technology effect; making hot states consume power for cooling
  is a v2 candidate for the power grid system.
- AI work. Migration is the engine's; the carriers are ordinary technologies.
- A game rule *(designer's call)*: the define change cannot follow a rule, so
  turning comfort off would leave the floor gone and nothing in its place.
  Migration Crowding has no rule either.

**Anti-goals**: what would make this a failure even if it works

- **Climate as an eligibility gate.** No state is barred from anything by its
  climate. It is a penalty in attraction, per the mod's soft-caps default.
- **Scenic wilderness as a magnet.** This is why base appeal is not reused.
- **Swamping jobs and wages.** A booming hot state still draws people (Gulf
  oil towns, 20th-century Houston). Comfort shifts the balance and must not
  overrule the economy.
- **Double counting** with Migration Crowding (density) or with the census's
  malaria deaths.
- **Micromanagement.** There is nothing to toggle, no building to manage and no
  decision to take.

## 3. What exists today (facts this rests on)

- **Migration attraction's scale** (vanilla `NPops`): +2 per point of average
  standard of living, up to +30 from available jobs, up to +10 from
  subsistence jobs, down to −50 from unemployment. A state receives
  intra-market migration only above 1.25 × the market's average attraction
  (`MIGRATION_PULL_HIGH_THRESHOLD`). A pop in a mass migration moves only to a
  state that beats home by 10 (`MASS_MIGRATION_MIN_DIFFERENCE_IN_MIGRATION_ATTRACTION_TO_MOVE`).
- **The mass migration target defines** (vanilla `NPops`; the mod overrides
  none): `MASS_MIGRATION_TARGET_MIN_ARABLE_LAND = 10` is a hard filter on each
  state. `MASS_MIGRATION_NUM_TARGET_STATES_FOR_NO_PENALTY = 4` and
  `MASS_MIGRATION_FEW_TARGET_STATES_PENALTY = 0.2` cut a country's target score
  by 20% for each eligible state below 4, so one eligible state keeps 40%.
  Each country's piece of a split region is its own state, and a piece gets a
  share of the region's arable land
  (`docs/vanilla/vanilla_states_reference.md` § 1.2).
- **Precedent: Migration Crowding** (`docs/systems/mod_systems/pops_and_migration.md`):
  a state modifier (`migration_crowding`, `state_migration_pull_mult`)
  re-applied from `on_yearly_pulse_state` with a script-value multiplier, its
  own state panel tile, no game rule. Local Climate follows the same shape.
- **Precedent: per-region tables.** `base_tourism_appeal_value`
  (`common/script_values/tourism.txt`) is a `state_region = s:X` if-chain over
  671 regions, each with a one-line reason. `gen_tourism_heritage.py` turns a
  CSV in `scripts/generators/data/` into a generated script value keyed the
  same way, with a staleness test.
- **Global warming's temperature** is world-wide, not per state:
  `temperature_anomaly_display` is the felt anomaly (warming less the aerosol
  mask), `gw_unmasked_temperature` the warming emissions caused
  (`docs/systems/mod_systems/global_warming.md`).
- **Malaria in the mod today**: the Demographics census multiplies infection
  deaths in states with vanilla's malaria traits, and `malaria_prevention`
  (vanilla, era 4) carries `state_malaria_control_add = 1` for it
  (`te_demog_tech_injections.txt`). `quinine` (era 2) carries nothing for the
  census, because it protected colonists rather than the people who lived
  there.
- **No mod content mentions air conditioning.** Era 6 has `personal_appliances`
  and `rural_electrification`; era 7 has `prefabricated_construction` and
  `modern_urban_planning`.

## 4. The climate record

**Keyed on the state region** (`state_region = s:X`), like base appeal. Every
piece of a split region therefore has the region's climate. Sea regions
(`map_data/state_regions/99_seas.txt`) get no row. A state with no row reads as
neutral: no penalty, and the tile says "no climate data".

**Fields.** Real-world units, so a reader can check a row against climate
normals *(designer's call)*:

| Field | Meaning | Example: Georgia |
|---|---|---|
| `summer_mean_c` | Warmest month's mean temperature, °C, integer | 28 |
| `summer_humidity` | The warmest month's mean dew point as a class: 0 dry (under 10 °C), 1 moderate (10–16), 2 humid (16–20), 3 oppressive (over 20). A dry-summer Mediterranean climate is 0 or 1 | 3 |
| `winter_mean_c` | Coldest month's mean temperature, °C, integer | 8 |
| `aridity` | Water: 0 humid, 1 semi-arid (Köppen BS), 2 arid (Köppen BW) | 0 |
| `malaria` | Malaria as of 1836: 0 none, 1 seasonal or local, 2 endemic | 2 |
| `latitude` | Signed degrees of the reference place, integer | 32 |
| `ref_place` | The place the figures describe (CSV only) | Savannah |
| `reason` | One line, as base appeal's comments (CSV only) | Hot, humid coastal lowland, endemic malaria |

- **Heat is the warmest month's mean, read with its dew point** *(designer's
  call)*. The builder check found that a daily maximum read with a Köppen
  humidity class ranks Seville (36 °C maximum, dry summer) worse than Savannah
  (33 °C, oppressive). That is the wrong way round for comfort, and no choice
  of constants fixes it. With the mean and the dew point, Savannah (28, class
  3) reads worse than Seville (28, class 1), and Kolkata (31, class 3) worse
  than both.
- **Aridity is its own field** *(designer's call)*. Dry heat is easier to bear
  than humid heat, so a desert's comfort term alone is moderate, yet the
  floor's job was to keep deserts out. What keeps people out of a desert is
  water, and dams, irrigation and later desalination fixed that (the Sun Belt
  needed both air conditioning and water projects).

- **The figures describe where the people are:** the region's largest city or
  main settled area, not its geographic center. A coastal city's milder
  temperatures are why a coast scores better, so the coast needs no field of
  its own *(designer's call)*.
- **Malaria is historical, not vanilla's traits.** In 1836 it was endemic in
  the US South, much of Italy, the Balkans, the Low Countries' coasts and
  England's fens. The row must at least agree with vanilla where vanilla has a
  trait: `state_trait_malaria` means 1 or more, `state_trait_severe_malaria`
  means 2. A test checks this.
- **Latitude is cheap and factual.** Phase 3 needs it for the strength of
  warming, and v2 agriculture will probably want it.

**Source and production.** One CSV,
`scripts/generators/data/local_climate.csv`, about 760 rows. It is filled by
subagents in bulk, each with its own scratch directory and a slice of regions,
from climate normals they know for each region's reference place. The owner
prefers subscription subagents to paid API calls for bulk work. A generator,
`scripts/generators/gen_local_climate.py`, writes
`common/script_values/local_climate_generated.txt`: one state-scope script
value per numeric field (`te_climate_summer_mean`, `te_climate_summer_humidity`,
`te_climate_winter_mean`, `te_climate_aridity`, `te_climate_malaria`,
`te_climate_latitude`), each an if-chain on `state_region`. It runs yearly and from the panel, so the chain's
length doesn't matter. `--check` mode and a staleness test, as
`gen_tourism_heritage.py` has.

**Validation**, in the test: every land region of the mod's
`map_data/state_regions/` has exactly one row; values sit in range (summer
−10…45, winter −50…30, summer ≥ winter); humidity, aridity and malaria are in
their classes; the vanilla malaria traits agree; every region with one of
vanilla's desert traits (`state_trait_sahara_desert` and the like) has aridity
2. A plausibility pass also flags
rows whose latitude and temperatures disagree badly (a 60° region with a
30 °C winter), for a person to look at.

## 5. Comfort

**Shape.** Comfort is a penalty, never a bonus *(designer's call)*: a mild
climate costs nothing, and a harsh one costs migration attraction. Only
differences matter inside a market, since a state needs 1.25 × the market's
average, so penalizing harsh places is the same as favoring mild ones there.
Across countries, a penalty keeps a desert from being picked without inflating
anyone's attraction.

```
heat     = max(0, summer − H0) × (1 + k_hum × summer_humidity) × (1 − heat_relief)
cold     = max(0, C0 − winter) × (1 − cold_relief)
dry      = W × aridity × (1 − water_relief)
disease  = D × malaria × (1 − disease_relief)
penalty  = min(P_max, w_heat × heat + w_cold × cold + dry + disease)
```

- `summer` and `winter` are the record's figures plus warming (phase 3).
- `H0` (the summer mean where heat starts to cost), `C0` (the winter mean where
  cold starts to cost), `k_hum`, `W`, `D`, the weights and `P_max` are tuning
  constants at the head of the script values file. The builder sets them by
  the calibration in § 5.3.
- The four terms stay separate all the way to the panel, because each has its
  own fixes and the player needs to see which one is costing them.

### 5.1 How it is applied

- **`state_migration_pull_add`, not `_mult`** *(designer's call)*. A penalty
  in attraction points reads as "this climate is worth N points of standard of
  living to a migrant" (2 points of attraction per point of standard of
  living). A multiplier would also scale with the economy, and on a state
  whose attraction is negative (heavy unemployment) a negative multiplier
  would move it toward zero, turning the penalty into a bonus.
- **One static modifier**, `local_climate_discomfort`
  (`state_migration_pull_add = -1`), applied with `multiplier = <penalty>`.
  The penalty is never negative, so no signed multiplier is needed.
- **Dynamic-modifier pattern**: a state on-action on `on_yearly_pulse_state`
  calls `te_update_local_climate_modifier`, which removes the old copy
  (`remove_modifier_if_exists_effect`) and adds the new one, as
  `migration_crowding_on_action` does. Its single refresh site is that pulse,
  plus a seed for every state at game start, so 1836 has it from the first
  day (the builder picks the start hook the mod already uses for state
  seeding). A newly researched relief shows within a year. A state carrying
  the modifier from before a revolution keeps it until its next pulse, which
  is fine.
- The refresh stores the penalty it applied
  (`var:te_climate_penalty_applied`), so the panel can show what is in force,
  as Migration Crowding stores `migration_crowding_mult_applied`.

### 5.2 Relief from technology

Four new modifier types, registered in `common/modifier_type_definitions/`,
percent-styled, 0–1, with names and descriptions in loc:
`state_climate_heat_relief_add`, `state_climate_cold_relief_add`,
`state_climate_water_relief_add` and `state_climate_disease_relief_add`. The script values read each with
`modifier:<type>` and clamp it to its cap. They are modifiers rather than
`has_technology` checks so that the engine's breakdown names every source on
hover, and so that a law, building or event can grant relief later.

Carriers are `INJECT:`s on existing technologies, as
`te_demog_tech_injections.txt` does. A new technology is added only if no
existing one fits. The schedule (owner: cold is addressable earlier):

| Relief | When | Candidate carriers | Cap |
|---|---|---|---|
| Cold | Eras 1–3 mostly, a little later | `railways` (era 2, coal by rail heats homes), an era 3 building technology for central heating, `rural_electrification` (era 6) | About 0.6: the far north stays thin today, from short summers and isolation as much as cold |
| Disease | Eras 2 and 4 | `quinine` (era 2), about half. Migrants arrive without immunity, like the colonists it protected. `malaria_prevention` (era 4), the rest | 1.0 |
| Heat | Era 3 a little, eras 6–7 mostly | `electrical_generation` (era 3, electric fans), `personal_appliances` (era 6, window units), an era 7 construction technology (central air in new housing) | About 0.8: outdoor heat remains |
| Water | Eras 4–6 (dams, irrigation, pumped supply), era 7 or later (desalination) | No technology named for water was found in vanilla or the mod. The builder picks engineering and chemistry carriers in those eras, or adds one | About 0.7: a desert city stays dearer to supply |

The builder confirms each carrier by reading the technology tree
(`common/technology/technologies/`, vanilla's and the mod's `era_*.txt`) and
may swap one for a better fit. The candidates are named here only to fix the
eras. `state_climate_disease_relief_add` is separate from the census's
`state_malaria_control_add`, so quinine can help migrants without changing
the census (§ 2).

### 5.3 Calibration (before any number is final)

Per the mod's evidence-based tuning rule, the builder produces a table before
fixing constants. For a set of anchor regions it shows the penalty in 1836, at
era 4 and at era 7, beside the same states' standard-of-living and jobs terms
from an observer save. Suggested anchors: Georgia, Louisiana, Massachusetts,
Ohio, Arizona, California, Florida; Île-de-France, Lazio, Andalusia; Moscow,
Yakutia; Egypt's Nile valley, the Sahara, Arabia; Bengal, the Deccan; coastal
and interior Brazil; Quebec.

Targets, in attraction points (1 SoL = 2 attraction), for the builder to
confirm against that table:

- A mild maritime or coastal Mediterranean climate (London, Lazio): 0. A hot,
  dry-summer interior (Andalusia at Seville): a small heat cost, well under
  Georgia's.
- Georgia in 1836: about −12 to −16 (6–8 SoL). With malaria and heat eased by
  era 7: about −3.
- Bengal in 1836: about −20 to −25, worse than Georgia, as its climate is.
  Its density comes from history and rice, which comfort doesn't undo:
  comfort moves the margin of migration, not the pops the game starts with.
- The Sahara or the Arabian interior before relief: about −30, most of it the
  dry term. Arizona: about −30 in 1836, about −5 once air conditioning and
  water projects arrive. Yakutia before relief: about −30, and about −15
  after.
- `P_max` around −40, so climate alone never outweighs a full jobs bonus plus
  a good standard of living.

**A country column too.** A country's mass migration attraction is "largely
based on the average migration attraction of eligible states" (vanilla's
`concept_mass_migration_pull_desc`). Removing the floor makes every
incorporated, well-connected state eligible, so comfort moves which
*country* a mass migration picks, not just which state. The table shows each
anchor country's average with and without comfort: the United States (its
South in the average), Argentina, Brazil, Canada, Australia, Russia, a
city-state.

**A known consequence.** Hot-to-hot mass migrations of the period, such as
Indians to Mauritius, Natal and the Caribbean or Chinese to Malaya, weaken,
because temperate target countries win the average. A state modifier can't
tell a migrant from a hot homeland apart from any other, so acclimatization
isn't representable. `P_max` and the jobs term are what keep those flows
alive; the calibration table should show they survive at a reduced size.

What should come out: the US North keeps drawing more migrants than the South
until the mid-20th century, and the Sun Belt gains after air conditioning.
Deserts are not picked as mass migration targets early on. Coasts outdraw
interiors of similar wealth. The owner's standard is verisimilitude, not an
exact fit.

### 5.4 The defines

In an `NPops = { }` block of `common/defines/extra_defines.txt`, shipped in the
same PR as comfort and never before it:

```
MASS_MIGRATION_TARGET_MIN_ARABLE_LAND = 0
MASS_MIGRATION_NUM_TARGET_STATES_FOR_NO_PENALTY = 1
```

The same PR fixes `docs/vanilla/vanilla_economy_reference.md` § 8.5. It says a
mass migration target needs 30% market access, but the define
(`MASS_MIGRATION_STATE_MIN_MARKET_ACCESS`) is 0.7 in 1.13.9 and in the
installed game. It also describes the arable land floor, which the mod now
removes.

## 6. Global warming (phase 3)

- `summer` and `winter` in § 5 become the record's figures plus
  `temperature_anomaly_display × amplification(latitude)`. The felt anomaly is
  used because an aerosol haze cools the air people live in *(designer's
  call)*.
- Amplification rises with latitude: about 1 in the tropics and about 2.5
  above the Arctic Circle, as observed warming runs. The builder picks a
  simple curve and states it.
- Warming then raises the heat term and lowers the cold term, so Siberia gains
  and the Gulf loses. The panel's hover shows the shift.
- This is one term in two script values plus a hover line. The builder may
  ship it in phase 2's PR *(designer's call)*.

## 7. The state panel

A **Local Climate** tile in the state panel's status grid, built as a type in
`gui/te_state_panel_widgets.gui` with an instance in `gui/states_panel.gui`,
like the Migration Crowding tile. It follows `docs/guides/gui_style_guide.md`:
a brief label and value per row, the detail on hover, the parts of a total as
signed rows.

- **Phase 1 (readings):** Summer (°C, with the humidity word), Winter (°C),
  Water (Humid, Semi-arid or Arid), Malaria (None, Seasonal or Endemic). Each
  row's hover says what the reading means and that the figures describe the
  region's main settled area. The reference place is not named in game
  *(designer's call)*: naming it would take about 675 generated place-name
  keys and their translations, and vanilla's hub names (Georgia's city hub is
  Macon, not Savannah) would name a different place from the one measured.
- **Phase 2 (comfort):** a Comfort row, the migration attraction the climate
  costs (red), and each reading row's hover adds its term: the raw penalty,
  the relief in force with its sources
  (`GetValueWithBreakdownFor('state_climate_heat_relief_add')` and so on),
  and the result.
- **Phase 3:** the summer and winter hovers add the warming shift.
- The tile's name is a concept, `concept_local_climate`, with a `_desc` that
  explains the record and comfort.
- **Naming** *(designer's call)*: "Local Climate", never bare "Climate", which
  already names the global warming panels, the Market panel's Climate tab and
  the player guide's chapter 15.
- Layout inside the 260 px tile (rows, bars or plain values) is the builder's,
  within the style guide. Placeholder icons are fine, listed as the style guide
  asks.

## 8. Phases

1. **The record and its readings.** CSV, generator, generated script values,
   tests, the tile's three reading rows, the concept, the system doc. No
   gameplay effect.
2. **Comfort.** The penalty script values and constants, the static modifier
   and its yearly refresh and start seed, the four relief types and their
   carriers, the calibration table, the defines, the Comfort row and the term
   hovers, the player guide section, the economy reference fix.
3. **Global warming.** Amplification, the shifted temperatures, the hover
   lines, a line in player guide chapter 15. It may fold into phase 2.

v2, separately: agriculture from the record; the census's malaria from the
record; air conditioning as electricity demand; climate in tourism.

## 9. House plumbing (constraints, not discoveries)

- `docs/systems/mod_systems/local_climate.md`, with a row in
  `docs/systems/mod_systems.md` (`test_mod_systems_index.py`), and a row in
  `state_and_nation_panels.md`'s tile table.
- The generated file goes in `docs/auto_generated_files.md` and in
  `scripts/nightly_audit_select.py`'s `EXCLUDED_REGISTRY_GLOBS`, with the CSV
  under `INTENTIONALLY_NOT_EXCLUDED` (`test_nightly_audit_select`).
- `local_climate_discomfort` is a permanent state modifier and needs a
  `NOT_ON_COUNTRY` line in `scripts/generators/gen_nation_tab.py`. The four
  relief types are carried by technologies, so they need type-registry lines
  (`TYPE_ROWS` or `NOT_A_ROW`). Rerun the generator; `test_nation_tab.py`
  names what is missing.
- Loc for the modifier, the three types, the concept and every tile key, then
  `organize_loc.py`. `loc_coverage_audit` and `concept_reference_audit` run in
  CI.
- Player guide (`docs/player_guide/08-states.md`): a Local climate section
  beside Migration crowding at its depth, with a line in chapter 15 in
  phase 3. Rebuild the PDF.
- A play-test list, `docs/testing/local-climate-playtest.md`: the tile
  renders; in an observer run, the US South's net migration until 1930 is
  below the North's; a city-state or a partial state is picked as a mass
  migration target once the define changes (`is_mass_migration_target` on a
  state with under 10 arable land); no desert is a mass migration target
  before era 4; the destination countries' shares of mass migrations to 1914,
  against an observer run without comfort. Where an engine fact is unverified, a once-a-game
  `TE_SELF_CHECK` line per the house pattern: for example, the count of mass
  migration targets under 10 arable land, logged ten years in.
- The UTF-8 BOM on every new `.txt` and `.gui`, tabs in brace files
  (`format_paradox_tabs.py`), and an entry in `docs/superpowers/README.md`.

## 10. Left to the builder

The tuning constants (by § 5.3); the final carrier technologies (by § 5.2's
eras); the amplification curve; the tile's layout; the start hook for the
seed; the CSV's production split across subagents; icons.
