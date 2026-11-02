# Local Climate

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

Spec: `docs/superpowers/specs/2026-11-01-local-climate-design.md`; plan: `docs/superpowers/plans/2026-11-01-local-climate.md`.

## The Climate Record

- **What:** each land state region's climate where most of its people live, eight figures per region. Every piece of a split region reads the region's record, since the values are keyed on `state_region`.
- **Fields** (`scripts/generators/data/local_climate.csv`; the generated values in brackets):
  - `summer_mean_c`: the warmest month's mean temperature, °C. CSV only since heat v2: the generator checks the hottest day against it and `--plausibility` reads it, but the formula doesn't.
  - `summer_humidity` (`te_climate_summer_humidity`): that month's dew point as a class, 0 dry (under 10 °C), 1 moderate (10–16), 2 humid (16–20), 3 oppressive (over 20); the tile's words are Dry, Moderate, Humid and Sultry. A description only since heat v2, which carries humidity in the heat index.
  - `winter_mean_c` (`te_climate_winter_mean`): the coldest month's mean, °C.
  - `aridity` (`te_climate_aridity`): water for settlement, 0 ample, 1 limited (Köppen BS), 2 scarce (Köppen BW). A great river whose valley holds the main settled area counts as ample, so the Nile valley is 0; a desert whose settled area a lesser river or a large oasis waters is 1 (Lima, Isfahan); a desert of small oases and wells is 2 (Ghardaia). Ruled 2026-11-01 when the eight agents' rows were merged.
  - `malaria` (`te_climate_malaria`): malaria as of 1836, from history rather than vanilla's traits. 0 none, 1 seasonal or local, 2 endemic. Local ague in a region's lowland counts as 1 (the Sologne, the unregulated Rhine plain, the Mälaren basin), as do the Hungarian plain and the Yangtze lowland's vivax.
  - `latitude` (`te_climate_latitude`): signed degrees of the reference place.
  - `hot_day_c` (`te_climate_hot_day`): the hottest day of a typical year, °C: the mean over years of each year's highest daily maximum. The tile's Hot days row.
  - `heat_index` (`te_climate_heat_index`): heat stress on a typical year's worst day: each day's 0.7 × wet-bulb (Stull's formula, from the day's maximum and dew point) + 0.3 × maximum, and the mean over years of each year's highest. The heat term reads it.
  - `heat_source`: where the two heat figures come from: a station (`KSVN:1km`, its code and distance), a station with one figure from the fit (`;fit_hot_day`, `;fit_index`), `fit` or `analog:STATE_X` (whose row it must copy). CSV only.
  - `ref_place` and `reason`: the place the figures describe and a short note on the climate. CSV only, never shown in game.
- **Neutral defaults:** a region with no row (one a vanilla patch adds) reads a hottest day of 20, heat index 0, winter 15 and zero for the rest, which costs no comfort, and `te_climate_has_record` is 0.
- **Generator:** `scripts/generators/gen_local_climate.py` writes `common/script_values/local_climate_generated.txt` (one if-chain on `state_region` per field). `--check` exits 1 when the committed file is stale; `--plausibility` lists rows worth a second look (a warm winter at a high latitude, a cool tropical highland, oppressive humidity with scarce water). Re-run after editing the CSV.
- **Checks** (`test_local_climate.py`): every land region of the mod's `map_data/state_regions/` (not `99_seas.txt`) has exactly one row, in map order; values in range (summer −10…45, winter −50…30, winter ≤ summer; hottest day 10…52 and no cooler than the warmest month; heat index 5…40 and no hotter than the hottest day); `heat_source` in one of its forms (station, station with one fitted figure, `fit`, an analog copying its source's row); vanilla's `state_trait_malaria` needs malaria ≥ 1 and `state_trait_severe_malaria` needs 2; a `state_trait_*_desert` needs aridity ≥ 1, except the regions in `DESERT_TRAIT_EXCEPTIONS`, whose people live by a great river or outside the desert (Aswan, Perth, the Top End): the trait describes the land, the record where people live. Adelaide, on the semi-arid edge, keeps 1. Where vanilla's trait is plainly wrong, the mod takes it away rather than bend the record: Fiji, Tonga and Namaqualand lose Severe Malaria, and Zambezi and Botswana swap it for the mild trait, through `state_trait_config.json`'s `-state_trait_x` entries (owner, 2026-11-01; it also speeds their colonization, which the owner judges too slow).
- **Production:** the 2026-11-01 table was filled by eight subagents from climate normals for each region's main settled area, then validated and spot-checked. Fifteen anchor rows (Georgia, West Bengal, the Home Counties, Île-de-France, Catalonia, Lazio, Lower Andalusia, the Sahara, Arizona, Yakutsk, Massachusetts, Ohio, Florida, Middle Egypt, Moscow) are the calibration's fixed points. Two predate the merge's malaria ruling and stay as calibrated: the Home Counties (London, 0, though Essex and Kent had marsh ague) and Catalonia (Barcelona, 0, though the Ebro delta had malaria).
- **Heat figures** (heat v2, 2026-11-01; spec § 11.2): Wolfram `WeatherData` daily maximum and dew point, 2010–2020, at the first of the six stations nearest the reference place with six years of both (2000–2020 where none had). Better stations replaced the nearest for South Tyrol, Calabria, Piedmont and New York; the Eastern Himalayas take the Himalayas' figures. Where the station is over 150 km away or 300 m above or below the place and misses a least-squares fit on the record's other fields by 2.5 or more, the row takes the fit for that figure: 17 rows for both (`heat_source = fit`) and 5 for one (`KSVN:312km;fit_hot_day`, `;fit_index`; the per-figure rule came with the winter axis, after #1312's review found far stations' hot days such as Kumasi's 39 °C). Mogadishu keeps Wajir's 39.4 °C hot day from 584 km inland, within 2.5 of a fit that can't see the coast. Adelaide and Melbourne keep their stations' high figures, which are real heat waves. The pull is `scripts/analysis/local_climate_heat_pull.wl`, run through the Wolfram tool in batches; a new row takes its station's figures the same way, or the fit.

## Comfort

- **What:** a cut to a state's migration attraction for its climate, in percent (`state_migration_pull_mult`), or a small bonus where a mild winter outweighs the rest (spec § 12). Mass migration attraction is the average of a country's eligible states' attraction, so it reaches mass migration too. Percentages add to the state's others before they multiply its base, and attraction floors at 0.
- **Why percent** (heat v2, owner, 2026-11-01; spec § 11.1): phase 2's points, shared by every state of a hot, poor market, could pin its poorer states at 0 and erase the gaps pops move for. A percentage scales each state's attraction, so the gaps survive in proportion.
- **Formula** (`common/script_values/local_climate_values.txt`, state scope; spec § 11.3), in percent:
  - summer warming = `temperature_anomaly_display` − `te_climate_normals_warming`; winter warming = that × amplification(|latitude|)
  - x = max(0, heat index + 0.8 × summer warming − 26)
  - heat = (4.1 x + 0.36 x²) × (1 − heat relief), so the eighth degree over 26 costs a little over twice the first
  - winter' = winter + winter warming
  - cold (frost) = max(0, 0 − winter') × 0.94 × (1 − cold relief)
  - winter (mildness) = (max(0, 3 − winter') − max(0, min(winter', 15) − 3) × summer share) × 0.6 × (1 − winter relief): a winter like London's in 1836 (3 °C) is neutral, a harsher one costs, a milder one draws, up to 7.2% at 15 °C and over (owner, 2026-11-01)
  - summer share = max(0, 1 − heat before relief / 20): a hot summer cancels a mild winter's draw, so Khartoum or Singapore never out-draw London once air conditioning eases their heat (owner, 2026-11-01, after #1313's review)
  - dry = 16 × water class × (1 − water relief)
  - disease = 5 × malaria class × (1 − disease relief)
  - `te_climate_penalty` = the sum, capped at 80, and 0 for a region with no row. Negative only through the winter term, so never below −7.2; `te_climate_bonus` is its negative part, as a positive percent.
- **Warming:** the record holds today's normals, about 1.1 °C of warming in, so a region reads its record exactly when the world's felt anomaly reaches `te_climate_normals_warming` (1.1). 1836, at anomaly 0, runs 1.1 °C colder on its hot days and 1.1 °C × amplification colder in winter (owner, 2026-11-01).
  - Amplification is 1 up to 30° of latitude, rising in a straight line to 2.5 at 66.5° and beyond. Winters alone take it, since Arctic amplification is a cold-season effect; with it on the hot days Yakutsk's cost rose with warming (spec § 11.3).
  - The heat index rises 0.8 per degree of warming, relative humidity holding about steady.
  - With the Global Warming rule off the anomaly stays 0, and every region keeps its 1836 climate.
  - The felt anomaly is used because an aerosol haze cools the air people live in. It can go negative when carbon removal passes zero.
- **Constants** sit at the head of the values file, and each is a script value: `te_climate_heat_start` (26), `_heat_linear`, `_heat_quadratic`, `_index_per_degree`, `_cold_start`, `_cold_weight`, `_winter_neutral`, `_winter_mild`, `_winter_per_degree`, `_winter_heat_cancel`, `_dry_per_class`, `_malaria_per_class`, `_penalty_max`, `_amp_low_lat`, `_amp_high_lat`, `_amp_max`, `_normals_warming`.
- **Terms stay separate** (`te_climate_<term>_raw`, `te_climate_<term>_term`) all the way to the tile, because each has its own technologies. The `_term`s aren't gated on `te_climate_has_record`, but the tile's rows are, so a no-row region shows none.

## Relief

- **Types** (`common/modifier_type_definitions/local_climate_modifier_types.txt`, `script_only`, percent): `state_climate_heat_relief_add`, `_cold_relief_add`, `_winter_relief_add` (Winter Relief: it closes the gap between a raw winter and a mild one, both ways), `_water_relief_add`, `_disease_relief_add`. `te_climate_relief_<kind>` reads each at state scope and clamps it to 0–1; disease relief also adds the census's `state_malaria_control_add`, which Malaria Prevention carries at 1.
- **Carriers.** Each line carries a `# Local Climate:` comment saying why. A vanilla technology gets one INJECT in `te_local_climate_tech_injections.txt`; a mod technology takes the line in its own era file. `te_demog_tech_injections.txt` stays census-only.

| Technology | Era | Relief |
|---|---|---|
| Quinine | 2 | disease 0.5 |
| Water-tube Boiler | 2 | cold 0.25, winter 0.1 |
| Electrical Generation | 3 | heat 0.1 |
| Reinforced Concrete | 3 | cold 0.2 |
| Malaria Prevention | 4 | disease 1 (Malaria Control) |
| Mechanized Farming | 4 | water 0.2 |
| Arc Welding | 5 | water 0.2 |
| Modern Chemical Processes | 6 | water 0.15 |
| Personal Appliances | 6 | heat 0.35 |
| Rural Electrification | 6 | cold 0.15, winter 0.1 |
| Plastic Mass Production | 7 | water 0.15 |
| Prefabricated Construction | 7 | heat 0.35 |
| Clean Energy Technologies | 9 | heat 0.1, water 0.15 |
| Advanced Structural Engineering | 10 | cold 0.2, winter 0.2 |
| Fusion Power | 11 | water 0.1 |
| Modern Material Science | 11 | winter 0.2 |
| Smart Grids | 11 | heat 0.05 |
| Compact Fusion Reactors | 12 | cold 0.1, winter 0.2 |
| Programmable Matter | 13 | heat 0.05, cold 0.1, winter 0.2, water 0.05 |

- **Schedule** for a country holding every carrier: disease is full from era 4. By era 7, heat is 0.8, cold 0.6 and water 0.7; by era 10, heat 0.9, cold 0.8 and water 0.85. Winter's mildness lasts longer, as the owner asked: 0.2 by era 7, 0.4 by era 10, then 0.6, 0.8 and 1.0 through eras 11–13. Every kind is 1.0 at era 13, so comfort neither costs nor draws at the end of the game.
- **A release without the census** comments out Malaria Prevention's control, leaving disease relief at Quinine's 0.5. Since 1.2.0 the census ships.

## The Modifier and Its Refresh

- **Modifier:** `local_climate_discomfort` (`common/static_modifiers/local_climate_modifiers.txt`), `state_migration_pull_mult = -0.01` (one percent), applied with `multiplier = var:te_climate_penalty_applied`; and `local_climate_amenity`, `state_migration_pull_mult = 0.01`, applied with `multiplier = var:te_climate_bonus_applied` when the total is a bonus. Two fixed-sign modifiers, not a negative multiplier, which no one has seen work (monetary policy's `te_fx_weak`/`_strong` chose the same). Each is plain "Local Climate" in loc, with the concept link in its `_desc`, because the state panel hides it by comparing `TimedModifier.GetName` with `Localize()`.
- **Refresh** (`te_update_local_climate_modifier`, `common/scripted_effects/local_climate_effects.txt`): remove the old copy, store `te_climate_penalty` in `te_climate_penalty_applied` and `te_climate_bonus` in `te_climate_bonus_applied`, then add the cost when the penalty is above 0.5, or else the bonus when that is above 0.5, the tile's gate too (a smaller cut would show as −0%). Neither variable is ever removed.
- **Old saves:** a state carries phase 2's points in `te_climate_penalty_applied` until its yearly refresh, read as percent meanwhile. That errs low almost everywhere (Georgia −15%, against −28%) but high where phase 2's heat overcounted a steady climate (Hawaii about −8%, against −1%). No repair: it lasts at most a year. A state from before the winter axis (§ 12) refreshes within a month: the first application keys on `te_climate_bonus_applied`, which every refresh sets.
- **Sites** (`common/on_actions/local_climate_on_actions.txt`): the yearly refresh, `local_climate_yearly_on_action` on `on_yearly_pulse_state`, the one refresh site; the first application, `local_climate_first_on_action` on `on_monthly_pulse_state`, for states without `te_climate_bonus_applied` (a new game's first month, a save from before § 12, a new state object), since `on_game_started` has no ROOT for the multiplier. A state that changes owner keeps its penalty until its yearly pulse.
- **Hidden** from the state panel's modifier rows (both `TimedModifier.GetName` filter lines in `gui/states_panel.gui`, and `gui_state_hidden_modifier_count`), both modifiers, since the tile shows them; `NOT_ON_COUNTRY` in `scripts/generators/gen_nation_tab.py`.
- **The define:** `MASS_MIGRATION_TARGET_MIN_ARABLE_LAND = 1` in `common/defines/extra_defines.txt`'s first `NPops` block. It is 1, not 0, because the engine rejects 0 at load (`defines.cpp:167 … Must be greater than 0`, the first launch with #1308); every state region has at least 2 arable land, so 1 lets them all in, so city-states and small partial states can be mass migration targets; climate now keeps deserts out early instead. Vanilla's few-target-states penalty (`MASS_MIGRATION_NUM_TARGET_STATES_FOR_NO_PENALTY` 4, `MASS_MIGRATION_FEW_TARGET_STATES_PENALTY` 0.2) is kept (owner, 2026-11-01). `concept_migration_target_desc` is overridden in `localization/english/replace/` without the floor's clause.
- **Log line** (`local_climate_log_on_action` on `on_yearly_pulse_country`; informational, not a self-check): each year the first country to pulse samples the mass migration targets, and each decade `TE_LOCAL_CLIMATE yearly_targets_summed=N under_10_arable=M years=Y date=…` prints the sums. `under_10_arable` above 0 shows the define at work.

## The Local Climate Tile

- **Where:** a `state_panel_status_item_small` in `gui/states_panel.gui` after Migration Crowding, always shown; its contents are the type `te_state_climate_tile` in `gui/te_state_panel_widgets.gui`.
- **Rows** (`te_state_climate_row`: 80 px of label, 76 of value, since "Humidity" and "Seasonal" overrun the standard tile rows): Hot days (°C, the hottest day), Humidity (Dry, Moderate, Humid, Sultry), Winter (°C), Water (Ample, Limited, Scarce), Malaria (None, Seasonal, Endemic). The words come from nested `SelectLocalization` on the class. A region with no row shows `TE_STATE_CLIMATE_NO_DATA` instead.
- **Comfort row:** what the modifiers apply, from the yearly variables, not the live value: the cost in red (`te_climate_penalty_now`) or a mild winter's bonus in green (`te_climate_bonus_now`), in percent. None shows when neither is above 0.5, the refresh's threshold, and Pending until the state's first monthly application (`te_climate_penalty_shown`). Its hover splits it into the five terms, today's, against the total of the last yearly refresh; None has a hover of its own.
- **Hovers:** each reading's hover gives its term before relief (`_raw`), the relief (`te_climate_relief_<kind>`, as a figure; no breakdown of the `script_only` types) and the cost left (`_term`). Hot days and Winter show the climate the formula uses now (`te_climate_hot_day_eff`, `_winter_eff`), and their hovers give today's normal and the warming against it (`te_climate_summer_warming`, `_winter_warming`); Hot days' hover also gives the heat index now (`te_climate_heat_index_eff`), and Winter's gives both the frost cost and winter's mildness as what it draws (`te_climate_winter_draw_raw`, `te_climate_winter_draw`: positive a bonus). Figures the text quotes, the heat threshold and the cap, are spliced from the constants. Humidity's hover gives no cost, since the heat index already holds humidity.
- **Concept:** `concept_local_climate` ("Local Climate"). The name is never bare "Climate", which the global warming panels, the Market panel's Climate tab and the player guide's chapter 15 already use.
- **Placeholder art:** the tile and the concept use vanilla's `gfx/interface/icons/state_trait_icons/tropical_climate.dds`. The final icon should show a thermometer beside a sun and a snowflake, at `gfx/interface/icons/state_status_icons/local_climate.dds`.
- **Loc:** `TE_STATE_CLIMATE_*` and `te_state_climate_*` in `te_miscellaneous_l_english.yml`; the words are `TE_CLIMATE_HUMIDITY_0`–`3`, `TE_CLIMATE_WATER_0`–`2` and `TE_CLIMATE_MALARIA_0`–`2`.
- **Play-test list:** `docs/testing/local-climate-playtest.md`.

## Calibration

- `scripts/analysis/local_climate_calibration.py [--warming W]` mirrors the formula in Python and prints each anchor region's terms and penalty at eras 1, 4, 7, 10 and 13, and each anchor country's mean over its 1836 heartland. W is the world's anomaly; the default 0 is 1836.
- `test_local_climate_comfort.py` pins spec § 11.4's anchor targets on the mirror. It also runs `ScriptValues`, a small interpreter of `local_climate_values.txt`, over every row, era and a range of warming, against the mirror, so the game's arithmetic can't drift from the calibration unseen. An operation the interpreter doesn't know fails the test.
