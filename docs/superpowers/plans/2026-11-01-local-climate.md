# Local Climate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every land state region a climate record, turn it into a comfort penalty in migration attraction that technology eases to nothing by the end of the game and global warming shifts, remove the mass migration arable land minimum, and show it all on a Local Climate state panel tile.

**Architecture:** A CSV of six climate figures per state region feeds a generator that writes state-scope script values keyed on `state_region`. Hand-written script values turn the record, four technology-carried relief modifiers and the world's warming into four penalty terms. A yearly state pulse applies their sum as one static modifier (`state_migration_pull_add = -1` × the penalty), as Migration Crowding does. A Python mirror of the formula drives an offline calibration test.

**Tech Stack:** Paradox script (script values, scripted effects, on-actions, static modifiers, modifier types, technologies, GUI, loc), Python 3.11/3.12 (generator, calibration, unittest).

**Spec:** `docs/superpowers/specs/2026-11-01-local-climate-design.md`

## Global Constraints

- Work in the sparse worktree `/home/jakef/src/vic3te-local-climate` on `feat/local-climate`. Use the main checkout's venv: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python` and `.venv/bin/ruff`. Never `POST /reload` from a worktree.
- Every new `.txt`/`.gui` starts with exactly one UTF-8 BOM. Brace files use tabs (`scripts/format_paradox_tabs.py`). Loc and guide text are American English.
- Name: "Local Climate" in every player-facing string, never bare "Climate".
- Penalty, never a bonus: `te_climate_penalty` ≥ 0, ≤ `te_climate_penalty_max`; applied as `state_migration_pull_add = -1` × penalty.
- Relief is a sum of carriers, clamped to [0, 1]; each kind reaches 1.0 by era 13 (owner). Historical stages: cold ≈ 0.6, heat ≈ 0.8, water ≈ 0.7 by era 7; disease 1.0 by era 4; modern: cold ≈ 0.8, heat ≈ 0.9, water ≈ 0.85 by era 10.
- A technology keeps one `INJECT`. A second `INJECT` of `modifier` on one technology is unverified; add lines to an existing `INJECT` instead (`git grep -n "^INJECT:<tech> = {" -- common/technology` first).
- `add_modifier`'s `multiplier` is read against ROOT: apply only from a state pulse (`on_yearly_pulse_state`, `on_monthly_pulse_state`), never from `on_game_started` or a country scope.
- Defines: `MASS_MIGRATION_TARGET_MIN_ARABLE_LAND = 0` only. `MASS_MIGRATION_NUM_TARGET_STATES_FOR_NO_PENALTY` and `MASS_MIGRATION_FEW_TARGET_STATES_PENALTY` stay vanilla (owner).
- The Demographics census and base tourism appeal are untouched.
- Per round run the touched tests plus the cheap checks; CI runs the full suite. Tests need the dummy env: `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent` only for modules importing `mod_state_server`.

## Review Focus

1. **A state region with no row** (a region a vanilla patch adds): every generated field falls back to a neutral default, so the penalty is 0 and the tile shows "No climate data". Test: `test_missing_row_is_neutral` (Task 1) and `test_default_record_has_no_penalty` (Task 5).
2. **A save from before the feature, or a newly colonized state**: no `te_climate_penalty_applied` until the monthly first application. The Comfort row must not read a missing variable as 0. Test: `test_comfort_row_waits_for_first_application` (Task 7).
3. **Relief past 1** (carriers summing over 1, or a later law granting relief): clamped. Test: `test_relief_values_clamp` (Task 5).
4. **Warming at or below zero** (the Global Warming rule off, or carbon removal taking the unmasked warming below zero; an aerosol mask floors the felt figure at 0): no term goes negative and the penalty stays in [0, max]. Test: `test_penalty_bounds_under_warming` (Task 5).
5. **A variable removed while the modifier reads it** (`modifier_multiplier_var_audit`): the refresh always sets `te_climate_penalty_applied`, never removes it. Test: `test_refresh_never_removes_the_variable` (Task 6).

---

## PR A: the record and its readings (spec phase 1)

### Task 1: Record schema, validation and generator

**Files:**
- Create: `scripts/generators/data/local_climate.csv` (header plus the anchor rows below)
- Create: `scripts/generators/gen_local_climate.py`
- Create: `common/script_values/local_climate_generated.txt` (generated)
- Test: `test_local_climate.py`

**Interfaces:**
- Produces (Python, `gen_local_climate`): `Row = namedtuple("Row", "state ref_place summer_mean_c summer_humidity winter_mean_c aridity malaria latitude reason")` (numeric fields `int`); `load_rows(path=CSV) -> list[Row]`; `land_regions(repo=REPO) -> set[str]` (every `STATE_X = {` in `map_data/state_regions/*.txt` except `99_seas.txt`); `region_traits(repo=REPO) -> dict[str, set[str]]` (each region's `traits = { … }` from the same files); `validate(rows, regions, traits) -> list[str]`; `render(rows) -> str`; `implausible(rows) -> list[str]`; CLI `python3 scripts/generators/gen_local_climate.py [--check] [--plausibility]`.
- Produces (script, state scope, in the generated file): `te_climate_has_record` (1/0), `te_climate_summer_mean`, `te_climate_summer_humidity`, `te_climate_winter_mean`, `te_climate_aridity`, `te_climate_malaria`, `te_climate_latitude`. Neutral defaults when no row: summer 15, humidity 0, winter 15, aridity 0, malaria 0, latitude 0, has_record 0.

- [ ] **Step 1: Write the failing tests** in `test_local_climate.py`, loading the generator by `importlib` as `test_tourism_heritage.py` does:
  - `test_render_chains_on_state_region`: `render([Row("STATE_GEORGIA","Savannah",28,3,8,0,2,32,"x")])` contains `limit = { state_region = s:STATE_GEORGIA }` under each of the seven value names, and `value = 28` under `te_climate_summer_mean`.
  - `test_missing_row_is_neutral`: each value's final `else` gives the defaults above.
  - `test_validate_ranges`: summer outside −10…45, winter outside −50…30, winter > summer, humidity ∉ 0–3, aridity ∉ 0–2, malaria ∉ 0–2, |latitude| > 90 each yield one error naming the state; a duplicate state yields an error.
  - `test_validate_vanilla_traits`: a region with `state_trait_malaria` and malaria 0 errors; with `state_trait_severe_malaria` and malaria < 2 errors; a region with any trait matching `state_trait_*_desert` and aridity 0 errors. `state_trait_*_desert` comes from `region_traits`.
  - `test_generated_file_is_current`: `render(load_rows())` equals the committed file (strip BOM).
  - `test_generated_file_bom`: the committed file starts with exactly one BOM and the `# AUTO-GENERATED by scripts/generators/gen_local_climate.py — do not edit manually.` header.
- [ ] **Step 2: Run, expect failures** — `.venv/bin/python -m pytest test_local_climate.py -q` → FAIL (module missing).
- [ ] **Step 3: Implement the generator**, modeled on `gen_tourism_heritage.py` (docstring, `REPO`/`CSV`/`OUT` constants, `--check` exits 1 when stale and writes nothing; writes with `encoding="utf-8-sig"`). `--plausibility` prints `implausible(rows)`: |lat| ≥ 55 with winter > 5, |lat| ≤ 15 with winter < 10 and summer < 20 (allowed for highlands, so a report, not an error), humidity 3 with aridity 2. Seed the CSV with the 15 anchor rows Task 5 tests, as below. Field definitions are exactly as spec § 4's table. Task 5's targets were checked by hand against these rows and Task 5's starting constants.

  | state | ref_place | summer_mean_c | summer_humidity | winter_mean_c | aridity | malaria | latitude |
  |---|---|---|---|---|---|---|---|
  | STATE_GEORGIA | Savannah | 28 | 3 | 8 | 0 | 2 | 32 |
  | STATE_WEST_BENGAL | Calcutta | 31 | 3 | 20 | 0 | 2 | 23 |
  | STATE_HOME_COUNTIES | London | 18 | 1 | 5 | 0 | 0 | 51 |
  | STATE_ILE_DE_FRANCE | Paris | 20 | 1 | 4 | 0 | 0 | 49 |
  | STATE_CATALONIA | Barcelona | 25 | 2 | 10 | 0 | 0 | 41 |
  | STATE_LAZIO | Rome | 25 | 2 | 8 | 0 | 2 | 42 |
  | STATE_LOWER_ANDALUSIA | Seville | 28 | 1 | 11 | 0 | 1 | 37 |
  | STATE_SAHARA | Ouargla | 35 | 0 | 11 | 2 | 0 | 31 |
  | STATE_ARIZONA | Tucson | 31 | 1 | 11 | 2 | 0 | 32 |
  | STATE_YAKUTSK | Yakutsk | 19 | 1 | -38 | 0 | 0 | 62 |
  | STATE_MASSACHUSETTS | Boston | 23 | 2 | -2 | 0 | 0 | 42 |
  | STATE_OHIO | Cincinnati | 25 | 2 | 0 | 0 | 1 | 39 |
  | STATE_FLORIDA | Jacksonville | 28 | 3 | 12 | 0 | 2 | 30 |
  | STATE_MIDDLE_EGYPT | Cairo | 28 | 2 | 14 | 0 | 1 | 30 |
  | STATE_MOSCOW | Moscow | 19 | 1 | -7 | 0 | 0 | 56 |

  If a key isn't a region in the mod's `map_data` (STATE_SAHARA's main settled area may sit in another region), use the region that holds the named place and update Task 5's test to match.
- [ ] **Step 4: Run** `python3 scripts/generators/gen_local_climate.py && .venv/bin/python -m pytest test_local_climate.py -q` → PASS.
- [ ] **Step 5: Commit** `test_local_climate.py`, the generator, the CSV and the generated file.

### Task 2: Fill the record for every land region

**Files:**
- Modify: `scripts/generators/data/local_climate.csv`, `common/script_values/local_climate_generated.txt` (regenerated)
- Test: `test_local_climate.py`

- [ ] **Step 1: Add the failing coverage test** `test_every_land_region_has_a_row`: `set(r.state for r in load_rows()) == land_regions()`, and `validate(load_rows(), land_regions(), region_traits()) == []`. Run → FAIL (15 of about 675 rows).
- [ ] **Step 2: Fan out the fill.** Eight subagents, two `map_data/state_regions/` files each (16 land files), each with its own scratch dir `<scratchpad>/climate-<files>/`. Each gets: its region keys; the region names from vanilla's loc (`game/localization/english/map/` state names) and its `city` hub name (`HUB_NAME_<STATE>_city`) to identify the main settled area; the spec § 4 field table verbatim, including the aridity river rule, the dew-point classes and the historical malaria note; the instruction to write `<scratch>/rows.csv` with the CSV's header, one row per region, `reason` a short phrase naming the climate, and `ref_place` the place the figures describe. They return only the path.
- [ ] **Step 3: Merge** the fragments into the CSV (sorted as `map_data` file order, then file order within it), keep the 15 anchor rows Task 1 wrote, regenerate, run the tests, and fix every `validate` error. Read `--plausibility` and correct rows that are wrong rather than unusual (highland tropics are fine).
- [ ] **Step 4: Run** `.venv/bin/python -m pytest test_local_climate.py -q` → PASS.
- [ ] **Step 5: Commit** CSV and generated file: "Local Climate: the record for every land region".

### Task 3: The tile's readings, concept and phase 1 docs

**Files:**
- Modify: `gui/te_state_panel_widgets.gui` (new type `te_state_climate_tile`), `gui/states_panel.gui` (one `state_panel_status_item_small` instance after `### MIGRATION CROWDING`), `common/game_concepts/extra_concepts.txt`, `localization/english/*.yml` (via `organize_loc.py`), `docs/systems/mod_systems/state_and_nation_panels.md`, `docs/systems/mod_systems.md`, `docs/player_guide/08-states.md` (+ PDF)
- Create: `docs/systems/mod_systems/local_climate.md`, `docs/testing/local-climate-playtest.md`, `common/customizable_localization/local_climate_custom_loc.txt` if the words use custom loc
- Test: `test_local_climate.py`

**Interfaces:**
- Consumes: Task 1's script values.
- Produces: concept `concept_local_climate` (texture: a vanilla icon, listed as a placeholder in the system doc); loc keys `TE_STATE_CLIMATE_STATUS` (`"[concept_local_climate]"`), `TE_STATE_CLIMATE_TT`, `TE_STATE_CLIMATE_ROW_SUMMER`, `_ROW_WINTER`, `_ROW_WATER`, `_ROW_MALARIA`, `_NO_DATA`, and per-row hover keys `te_state_climate_summer_tt`, `_winter_tt`, `_water_tt`, `_malaria_tt`; word keys for humidity (Dry, Moderate, Humid, Oppressive), water (Ample, Limited, Scarce) and malaria (None, Seasonal, Endemic).

- [ ] **Step 1: Write failing tests:** `test_tile_instance_reads_the_record` (the instance in `states_panel.gui` uses `te_state_climate_tile`, the type in `te_state_panel_widgets.gui` reads `te_climate_summer_mean`, `te_climate_winter_mean`, `te_climate_aridity`, `te_climate_malaria` and shows `TE_STATE_CLIMATE_NO_DATA` when `te_climate_has_record` is 0); `test_tile_loc_exists` (every key above has English loc; no value contains bare "Climate" outside "Local Climate"). Run → FAIL.
- [ ] **Step 2: Build the tile**, copying the Migration Crowding instance's shape (`te_state_tile_row` rows, `tooltip`, `blockoverride "texture"`). Always visible. Values: `#v [State.MakeScope.ScriptValue('te_climate_summer_mean')|0]°C#!` and the word picked from the class, by state-scope custom loc (`type = state`, as `gm_custom_loc.txt`) or `SelectLocalization` (as the homeland tile). Hover text per spec § 7: what the reading means, and that the figures describe the region's main settled area. The place itself isn't named.
- [ ] **Step 3: Run** `python3 organize_loc.py`, `python3 scripts/analysis/check_gui_lint.py`, `python3 scripts/format_paradox_tabs.py --check gui/te_state_panel_widgets.gui gui/states_panel.gui`, the tests → PASS. Resolve any lint warning on unproven markup by switching to markup a mod `.gui` already uses.
- [ ] **Step 4: Docs.** `local_climate.md` (purpose, the record and its fields, the generator, the tile, placeholders; one `##` per part). Index row in `mod_systems.md`. A tile row in `state_and_nation_panels.md`'s table. One row in `08-states.md`'s state panel table: "Local Climate | Always | Summer and winter temperatures, summer humidity, water and malaria where most of the state's people live." Rebuild the PDF (`.venv/bin/python scripts/build_player_guide.py`) and run `python3 scripts/analysis/check_player_guide_style.py --strict`. The play-test file follows `city-states-playtest.md`'s shape with a "Readings (phase 1)" section: the tile renders on a state, a split state and a sea-adjacent state; no raw keys. Run `test_mod_systems_index.py`.
- [ ] **Step 5: Commit**; then open **PR A** (`--base main`) with a "Player guide" line naming `08-states.md`.

---

## PR B: comfort, relief, warming and the defines (spec phases 2–3)

### Task 4: Relief modifier types and their carriers

**Files:**
- Create: `common/modifier_type_definitions/local_climate_modifier_types.txt`, `common/technology/technologies/te_local_climate_tech_injections.txt`
- Modify: `common/technology/technologies/te_demog_tech_injections.txt` (lines added inside the existing `INJECT:railways`, `INJECT:malaria_prevention`, `INJECT:combustion_engine`), the mod's `era_6.txt`, `era_7.txt`, `era_9.txt`, `era_10.txt`, `era_11.txt`, `era_12.txt`, `era_13.txt` (lines in each carrier's own `modifier` block, adding the block if it has none), `localization/english/te_modifiers_l_english.yml`
- Test: `test_local_climate_comfort.py`

**Interfaces:**
- Produces: `relief_schedule(repo=REPO) -> dict[str, list[tuple[int, str, float]]]` in `scripts/analysis/local_climate_calibration.py` (kind → [(era, technology, amount)]), which Task 5 extends.
- Produces: types `state_climate_heat_relief_add`, `state_climate_cold_relief_add`, `state_climate_water_relief_add`, `state_climate_disease_relief_add`, each `color = good percent = yes decimals = 0 script_only = yes` (the shape of `state_malaria_control_add`), with `<type>` and `<type>_desc` loc.
- The carriers (amounts are the starting schedule; Task 5 may move them within the stage targets):

| Kind | Carriers (era, amount) |
|---|---|
| Cold | `railways` (2) 0.25, `reinforced_concrete` (3) 0.20, `rural_electrification` (6) 0.15, `advanced_structural_engineering` (10) 0.20, `compact_fusion_reactors` (12) 0.10, `programmable_matter` (13) 0.10 |
| Heat | `electrical_generation` (3) 0.10, `personal_appliances` (6) 0.35, `prefabricated_construction` (7) 0.35, `clean_energy_technologies` (9) 0.10, `smart_grids` (11) 0.05, `programmable_matter` (13) 0.05 |
| Water | `combustion_engine` (4) 0.20, `arc_welding` (5) 0.20, `modern_chemical_processes` (6) 0.15, `plastic_mass_production` (7) 0.15, `clean_energy_technologies` (9) 0.15, `fusion_power` (11) 0.10, `programmable_matter` (13) 0.05 |
| Disease | `quinine` (2) 0.50, `malaria_prevention` (4) 0.50 |

- [ ] **Step 1: Write failing tests** in `test_local_climate_comfort.py`: `test_relief_types_registered` (four types, each percent with `script_only = yes`, each with name and `_desc` loc); `test_relief_schedule` (using this task's `relief_schedule()`: cumulative relief at eras 7 and 10 per kind meets the Global Constraints stages within ±0.05, is exactly 1.0 at era 13 for cold, heat and water, and disease is 1.0 at era 4); `test_one_inject_per_technology` (no technology key appears in two `INJECT:` lines across `common/technology/technologies/`); `test_carrier_comments` (each carrier line carries a trailing `#` comment saying why, as `te_demog_tech_injections.txt` does). Run → FAIL.
- [ ] **Step 2: Implement** `relief_schedule(repo=REPO) -> dict[str, list[tuple[int, str, float]]]` in `scripts/analysis/local_climate_calibration.py`. For each `state_climate_<kind>_relief_add = x` it finds the enclosing top-level technology key in `common/technology/technologies/*.txt`, bare or `INJECT:`. It takes the era from the mod's `era = era_N` inside a bare definition, else from `vanilla_parsed/common/technologies.json` (`d[key][1]["era"][1]`).
- [ ] **Step 3: Add the types, the loc and the carriers** per the table. Vanilla technologies without an existing INJECT (`quinine`, `reinforced_concrete`, `electrical_generation`, `arc_welding`) go in the new injections file; check each with `git grep` first. `modern_chemical_processes`, `personal_appliances`, `rural_electrification`, `prefabricated_construction`, `plastic_mass_production` and the later carriers are the mod's own definitions in `era_6.txt` to `era_13.txt`, so their lines go in those definitions. The loc name says what it is ("Cold Relief", "Heat Relief", "Water Supply", "Malaria Relief") and the `_desc` names the term it cuts in [concept_local_climate].
- [ ] **Step 4: Run** the tests, `python3 scripts/format_paradox_tabs.py --check <changed .txt>`, `python3 organize_loc.py --check` → PASS.
- [ ] **Step 5: Commit.**

### Task 5: The comfort formula, warming and the calibration *(reviewed)*

**Files:**
- Create: `common/script_values/local_climate_values.txt`
- Modify: `scripts/analysis/local_climate_calibration.py`
- Test: `test_local_climate_comfort.py`

**Interfaces:**
- Consumes: Task 1's record values, Task 4's types and `relief_schedule`.
- Produces (script, state scope). Constants are bare named values, read by the Python mirror:
  - `te_climate_heat_start = 23` (H0, °C summer mean), `te_climate_humidity_factor = 0.33` (k_hum), `te_climate_heat_weight = 1`, `te_climate_cold_start = 0` (C0, °C winter mean), `te_climate_cold_weight = 0.8`, `te_climate_dry_per_class = 8` (W), `te_climate_malaria_per_class = 2.5` (D), `te_climate_penalty_max = 40`, `te_climate_amp_low_lat = 30`, `te_climate_amp_high_lat = 66.5`, `te_climate_amp_max = 2.5`.
  - `te_climate_amplification`: 1 at |latitude| ≤ 30, rising linearly to 2.5 at |latitude| ≥ 66.5.
  - `te_climate_warming` = `temperature_anomaly_display` × amplification.
  - `te_climate_summer_eff` = summer mean + warming; `te_climate_winter_eff` = winter mean + warming.
  - `te_climate_relief_heat`/`_cold`/`_water`/`_disease` = `modifier:state_climate_<kind>_relief_add`, `min = 0 max = 1`.
  - `te_climate_heat_raw` = max(0, summer_eff − H0) × (1 + k_hum × humidity) × heat_weight; `te_climate_cold_raw` = max(0, C0 − winter_eff) × cold_weight; `te_climate_dry_raw` = W × aridity; `te_climate_disease_raw` = D × malaria.
  - `te_climate_heat_term` = heat_raw × (1 − relief_heat), and likewise `_cold_term`, `_dry_term` (water relief), `_disease_term`.
  - `te_climate_penalty` = sum of the four terms, `max = te_climate_penalty_max`, `min = 0`; 0 when `te_climate_has_record` is 0.
- Produces (Python): `load_constants(path) -> dict[str, float]`; `relief_at(schedule, kind, era) -> float` (cumulative, clamped [0, 1]; era 1 means 1836, no carriers); `amplification(lat, c) -> float`; `terms(row, era, c, schedule, warming=0.0) -> dict[str, float]` (keys `heat`, `cold`, `dry`, `disease`, `penalty`); CLI `python3 scripts/analysis/local_climate_calibration.py [--warming W]` prints the anchor table for eras 1, 4, 7, 10, 13 beside each anchor country's mean penalty over its core regions, hand-listed in the CLI and printed with the table (the United States, Argentina, Brazil, Canada, Australia, Russia, a Caribbean sugar colony, and Elbe for Hamburg). Ownership isn't read from history, so the lists are the country's 1836 heartland.

- [ ] **Step 1: Write the failing tests:**
  - `test_constants_match_script`: `load_constants()` returns the eleven values above, read from the script file.
  - `test_penalty_body_names_every_term`: the squashed body of `te_climate_penalty` adds `te_climate_heat_term`, `_cold_term`, `_dry_term`, `_disease_term`, with `max = te_climate_penalty_max` and `min = 0`. Each `_term` multiplies its `_raw` by (1 − its relief).
  - `test_relief_values_clamp`: each `te_climate_relief_*` body has `min = 0` and `max = 1`.
  - `test_default_record_has_no_penalty`: `terms(<the generator's neutral defaults>, 1, c, s)["penalty"] == 0`.
  - `test_anchor_targets` (penalties as positive points), all at warming 0:

    | Region | Era | Range |
    |---|---|---|
    | STATE_GEORGIA | 1 | 12–16 |
    | STATE_GEORGIA | 7 | 1–4 |
    | STATE_GEORGIA | 10 | ≤ 2 |
    | STATE_WEST_BENGAL | 1 | 20–25, and > Georgia's |
    | STATE_HOME_COUNTIES, STATE_ILE_DE_FRANCE | 1 | ≤ 1 |
    | STATE_CATALONIA | 1 | 1–5 |
    | STATE_LAZIO | 1 | 7–11 |
    | STATE_LAZIO | 4 | ≤ 4 |
    | STATE_LOWER_ANDALUSIA | 1 | heat term < Georgia's heat term |
    | STATE_SAHARA, STATE_ARIZONA | 1 | 24–34 |
    | STATE_SAHARA, STATE_ARIZONA | 10 | ≤ 6 |
    | STATE_YAKUTSK | 1 | 26–34 |
    | STATE_YAKUTSK | 7 | 10–16 |
    | STATE_YAKUTSK | 10 | 4–8 |
    | STATE_MASSACHUSETTS | 1 | ≤ 3, and < Georgia's |
    | STATE_MIDDLE_EGYPT | 1 | < STATE_SAHARA's |

  - `test_end_game_is_free`: every row's penalty at era 13 is 0.
  - `test_penalty_bounds_under_warming`: for warming in (−1, 0, 2, 4), every row at eras 1 and 10 has every term ≥ 0 and a penalty in [0, 40]. Yakutsk's era 1 penalty at warming 3 is below its warming 0 penalty, and Georgia's heat term at warming 3 is above its warming 0 one.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Write `local_climate_values.txt`** (BOM, a header comment citing spec § 5 and § 6) and the Python mirror. Before any number moves, run the CLI and keep its table in the PR body as the calibration evidence (spec § 5.3). If an anchor misses, change constants or carrier amounts, not the targets, and say why in the PR. A row whose figures look wrong goes back through Task 2's fix loop.
- [ ] **Step 4: Run** `.venv/bin/python -m pytest test_local_climate.py test_local_climate_comfort.py -q`, `.venv/bin/ruff check scripts/analysis/local_climate_calibration.py scripts/generators/gen_local_climate.py` → PASS.
- [ ] **Step 5: Commit.**

### Task 6: The modifier, its refresh, the defines and the registries *(reviewed)*

**Files:**
- Create: `common/static_modifiers/local_climate_modifiers.txt`, `common/scripted_effects/local_climate_effects.txt`, `common/on_actions/local_climate_on_actions.txt`
- Modify: `common/defines/extra_defines.txt` (first `NPops` block), `common/script_values/gui_chart_script_values.txt` (`gui_state_hidden_modifier_count`), `gui/states_panel.gui` (both `TimedModifier.GetName` filter lines), `scripts/generators/gen_nation_tab.py` (+ its four outputs), `localization/english/te_modifiers_l_english.yml`
- Test: `test_local_climate_comfort.py`, `test_hidden_state_modifiers.py`, `test_nation_tab.py`

**Interfaces:**
- Consumes: `te_climate_penalty` (Task 5).
- Produces: static modifier `local_climate_discomfort` (`icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds`, `state_migration_pull_add = -1`); state variable `te_climate_penalty_applied`; effect `te_update_local_climate_modifier`; on-actions `local_climate_yearly_on_action` (on `on_yearly_pulse_state`) and `local_climate_first_on_action` (on `on_monthly_pulse_state`, limited to states without the variable); `local_climate_log_on_action` (on `on_yearly_pulse_country`).

- [ ] **Step 1: Write failing tests:**
  - `test_refresh_shape`: the effect's squashed body is, in order: `remove_modifier_if_exists_effect = { MODIFIER = local_climate_discomfort }`, `set_variable = { name = te_climate_penalty_applied value = te_climate_penalty }`, then an `if` on `var:te_climate_penalty_applied > 0` adding `{ name = local_climate_discomfort multiplier = var:te_climate_penalty_applied }`.
  - `test_refresh_never_removes_the_variable`: no `remove_variable = te_climate_penalty_applied` anywhere in `common/`.
  - `test_refresh_sites`: the yearly on-action is listed in an `on_yearly_pulse_state`, and the first-application one in an `on_monthly_pulse_state` with `NOT = { has_variable = te_climate_penalty_applied }`. The effect is called nowhere else (one refresh site plus the first application).
  - `test_defines`: `extra_defines.txt` sets `MASS_MIGRATION_TARGET_MIN_ARABLE_LAND = 0` in an `NPops` block, and sets neither few-states define.
  - `test_modifier_loc`: `local_climate_discomfort` has loc naming [concept_local_climate].
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** The decade log line: once per ten years (a global variable with `days = 3650`, set by the first country to pulse), count every state with `is_mass_migration_target = yes`, and those among them with `arable_land < 10`. Then `debug_log = "TE_LOCAL_CLIMATE mass_migration_targets=<n> under_10_arable=<m>"`. It's informational, not an OK/BROKEN self-check, since zero small targets in a decade proves nothing. Hide `local_climate_discomfort` from the state panel's modifier rows (both filter lines, plus a `has_modifier` term in the count), since the tile shows it. Add `"local_climate_discomfort": "states"` to `NOT_ON_COUNTRY`, run `python3 scripts/generators/gen_nation_tab.py`, and add whatever type-registry line `test_nation_tab.py` names.
- [ ] **Step 4: Run** the three tests, `python3 modifier_multiplier_var_audit.py --strict`, `python3 duplicate_key_audit.py --strict`, `python3 scripts/format_paradox_tabs.py --check <changed>` → PASS.
- [ ] **Step 5: Commit.**

### Task 7: The tile's Comfort row and term hovers

**Files:**
- Modify: `gui/te_state_panel_widgets.gui` (`te_state_climate_tile`), `localization/english/*.yml`
- Test: `test_local_climate_comfort.py`

**Interfaces:**
- Consumes: Task 5's `_raw`, `_term`, `te_climate_relief_*`, `te_climate_warming`; Task 6's variable.
- Produces: script value `te_climate_penalty_shown` (1 when the state has `te_climate_penalty_applied`) in `local_climate_values.txt`; loc `TE_STATE_CLIMATE_ROW_COMFORT`, `te_state_climate_comfort_tt`, `te_state_climate_pending`.

- [ ] **Step 1: Write failing tests:** `test_comfort_row_reads_applied` (the Comfort row's value reads `var:te_climate_penalty_applied` through a script value, red, signed negative); `test_comfort_row_waits_for_first_application` (the row is visible only while `te_climate_penalty_shown` is 1, and `te_state_climate_pending` shows otherwise); `test_term_hovers` (each reading's hover key reads its `_raw`, its relief through `GetValueWithBreakdownFor('state_climate_<kind>_relief_add')`, and its `_term`; the summer and winter hovers read `te_climate_warming`). Run → FAIL.
- [ ] **Step 2: Implement** within the 160 px text column, per `gui_style_guide.md`: "Label: value" rows, detail on hover, no "...". The Comfort hover says the figure updates yearly and is the migration attraction the climate costs.
- [ ] **Step 3: Run** `organize_loc.py`, `check_gui_lint.py`, `long_tooltip_audit.py --strict`, `loc_coverage_audit.py --strict`, `concept_reference_audit.py --strict` (these build ModState from `vanilla_parsed/`, about 7 s each) and the tests → PASS.
- [ ] **Step 4: Commit.**

### Task 8: Docs, guide, play-test list, PR B

**Files:**
- Modify: `docs/systems/mod_systems/local_climate.md`, `docs/systems/mod_systems.md` (the row's `##` list), `docs/player_guide/08-states.md`, `docs/player_guide/15-climate.md`, the PDF, `docs/testing/local-climate-playtest.md`, `docs/vanilla/vanilla_economy_reference.md` § 8.5, `docs/auto_generated_files.md`, `scripts/nightly_audit_select.py`, `docs/superpowers/README.md`

- [ ] **Step 1: System doc:** comfort, relief (the carrier table), warming, the modifier and its refresh sites, the defines, the decade log line, the calibration CLI.
- [ ] **Step 2: Guide.** Add a "Local climate" section in `08-states.md` after Migration crowding, at its depth: what the four terms are, that the technologies ease them (cold early, malaria, water, then air conditioning, all gone by the last era), that warming shifts them, and that mass migrations can now reach small states. Add one line in `15-climate.md` that warming shifts each state's local climate. Rebuild the PDF; run the style lint `--strict` and `build_player_guide.py --check`.
- [ ] **Step 3: Registries.** Add the generated file's row to `auto_generated_files.md` (owner script, CSV input, "one-shot, not a post-load generator; `test_local_climate.py` fails when stale") and to `EXCLUDED_REGISTRY_GLOBS`, then run `test_nightly_audit_select.py`. Fix § 8.5 of the economy reference: market access 0.7, and the arable land floor that the mod removes. Update the specs index row's status.
- [ ] **Step 4: Play-test list**, a "Comfort (phase 2)" section with every item of spec § 9: the tile's Comfort row matches the state's migration attraction breakdown; the US South's net migration against the North's to 1930 in an observer run; a city-state or partial state as a mass migration target (the `TE_LOCAL_CLIMATE` line's `under_10_arable`); no desert target before era 4; destination-country shares to 1914 against a run without comfort.
- [ ] **Step 5: Gate and PR.** Run the touched tests, `ruff check .`, `organize_loc.py --check`, `check_loc_spelling.py --check`, `check_localization_files.py`, `format_paradox_tabs.py --check` on changed brace files, and the `--strict` audits for the touched kinds (`loc_coverage`, `concept_reference`, `modifier_multiplier_var`, `duplicate_key`, `long_tooltip`, `hidden_modifier`, `gui_reference`, `texture_reference`). Then open **PR B** (`--base main`, after PR A merges or retargeted per CLAUDE.md's stacked-PR rule) with the calibration table and a "Player guide" line naming `08-states.md` and `15-climate.md`.

### Task 9: Whole-branch review

- [ ] A fresh reviewer on the most capable model reads PR B's diff against the spec in two parts, script (Tasks 4–6) and docs/GUI (Tasks 3, 7, 8). It gets its own scratch dir and writes findings to a file. Fix rounds are verified by the controller. Don't self-merge: the owner merges.
