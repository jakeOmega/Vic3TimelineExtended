# Solar Colonization Fleets Implementation Plan

> **For agentic workers:** steps use checkbox (`- [ ]`) syntax for tracking. Do the parts in order (6a, 6b, 6c, 6d), each its own branch and PR into `main`; within a part, do the tasks in order, each ending green and committed.

**Goal:** Slice 6 of the solar colonization scope, under Full Colonies only. 6a: Space Command builds fleet strength in five roles; nine fleets per country move between nine locations on real legs, spending propellant (km/s) and supply, refitting to the nation's drive when docked; carriers land marines as garrisons. 6b: hostile fleets fight by posture (Lanchester); colony Defences and integrity; blockades away from Earth; seizure, occupation and its return at the peace; destruction; free colonies taken by force; war support; Survey Colony Defences; the AI's defence. 6c: interdiction in peace; the AI's offence at war; the outer-space convention. 6d: blockading Earth, the ground reserve, ground-to-orbit batteries (and their low-orbit sweeping in peace), orbital fire support in the ground war; Full Colonies becomes the default.

**Architecture:** Three generators. `gen_launch_windows.py` gains every leg between the nine locations (exact windows from Earth, mean-cycle windows home and among the inner four, fixed medians beyond) with months and delta-v per drive. A new post-load regenerator, `scripts/generators/gen_space_fleets.py`, writes every per-slot and per-location block (the nine fleet slots, their readers and the panel rows) from `FLEET_LOCATIONS`, `ROLES` and `gen_launch_windows`' legs. `gen_solar_sites.py` gains the per-world blocks of 6b (integrity, marines, occupation, blockade, ruin) and two table fields. Hand-written files hold what is neither per slot nor per world, and every number lives in a values file.

**Tech stack:** Paradox script (`common/`, `events/`), Victoria 3 GUI, localization YAML, Python 3.11/3.12 `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-26-solar-colonization-fleets-design.md` (§ numbers below are its). Scope: `docs/superpowers/specs/2026-10-25-solar-colonization-contest-scope.md`. When a part is built, add an "As built" section to the design recording where the build departed, as slices 0 to 5 did.

## Global constraints

- **Full Colonies only.** Every new entry point is gated on `sr_colonies_full_enabled = yes`; Races Only and Simple Colonies behave exactly as before until 6d moves the default. Each part's tests include one that every new on-action body, decision, button, building `potential` and diplomatic action reads the gate.
- **Never hand-edit a generated file.** Change the generator and run it (`python3 scripts/generators/<gen>.py`); `test_launch_windows.py`, `test_solar_sites.py` and the new `test_space_fleets.py` fail on stale output. A new regenerator joins `POST_LOAD_REGENERATORS` in `mod_state_server.py`, `CLAUDE.md`'s roster and its count, `docs/guides/python_tools.md`, `docs/auto_generated_files.md` and `scripts/nightly_audit_select.py`'s `EXCLUDED_REGISTRY_GLOBS`; run `python3 scripts/analysis/check_post_load_rosters.py` and `test_nightly_audit_select.py`.
- **Every global variable read is guarded** (`?=` or `has_global_variable`), and every stored country is checked with `exists` and `is_country_alive` before use. **Every `remove_modifier` sits behind its record**, and every static modifier is added at `multiplier =` with the old copy removed first, from **one refresh site** (CLAUDE.md, the dynamic-modifier scaling pattern).
- **A static modifier script adds without a duration gets a `gen_nation_tab.py` registry line** and a rerun (`test_nation_tab.py`): `sr_fleet_upkeep` (6a), `sr_orbital_superiority` (6d).
- **Numbers live in values files**: `common/script_values/sr_fleet_values.txt` (script reads), `common/script_values/sr_fleet_display_values.txt` (the panel only; `test_space_race_layout.py` keeps display values out of read files).
- **Engine-silent traps this design walks near:** a modifier name not registered is silently ignored (validate every new one with `/modifier-search?q=` or `/engine-docs/origin/<name>`, and register any new type in `common/modifier_type_definitions/`); `add_modifier` durations take literals; `change_variable`/`set_variable` render nothing in an option (`custom_tooltip`, `silent_variable_audit`); a scripted effect call passes exactly its `$X$` names, one token each (`script_argument_audit`); a visible event needs an `event_image`.
- **Files.** One UTF-8 BOM on every brace-based `.txt` and `.gui` (generators write it; new hand-written files need it, and only one). Tabs; `python3 scripts/format_paradox_tabs.py --check` on every changed `.txt`. Four docs are CRLF (`journal_entry_systems.md`, `gui_modding_guide.md`, `treaty_articles_reference.md`, `wonder_buildings_reference.md`): edit with `Edit` or bytes, then confirm `grep -c $'\r$'` equals `wc -l`.
- **Loc** in the existing files (`te_journal_entries_l_english.yml` for the panel, `te_events_l_english.yml` for events, the buildings and production methods files for Space Command and the batteries), then `python3 organize_loc.py` and commit everything it moves. `loc_coverage_audit --strict` names a missing key.
- **Python runs on 3.11 in CI**: no PEP 701 f-strings (`grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>`); compare floats with `math.isclose`.
- **Tests** need `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent` without a game. Use `.venv/bin/python`; read results with `grep -E '^(Ran |OK|FAILED)'`.
- **Per task**: its tests, `.venv/bin/ruff check .`, the tab check, and the audits it names, `--strict`. Each part's last task runs everything CI runs (`.github/workflows/ci.yml`'s steps) and the player guide's build and lint.
- **A new GUI file or generated file** fails `test_tax_code_bypass.py` (top-level GUI files in `gui_modding_guide.md`'s table and its count) or `test_nightly_audit_select.py` (every path in `auto_generated_files.md` classified): run both before pushing.

## Review focus

1. **Nothing changes outside Full Colonies** until 6d's default (each part's gate test).
2. **The legs' tables match the generator's physics** and the script's mean-cycle phase matches the generator's (Task A1's tests: the epoch fit, the folding into `[−S/2, S/2)`, the dividend kept positive).
3. **Combat conserves what it should**: each fleet's losses equal the fire allocated to it; screens take losses first; nothing goes negative (Task B3's tests run the step's arithmetic in Python against the generated script's constants).
4. **An occupied world always goes back or moves by cession**; no path leaves it occupied after the peace (Task B6).
5. **The AI can't stall**: every order it gives passes the same checks a player's does, and a fleet it can't bring home is recalled first (Tasks A6, B10, C3).
6. **Nothing counts from an occupied state** (design § 5.1): every read of Space Command, the battlestation, the batteries and the launch site goes through `sr_state_held_by_owner` or `sr_launches_barred` (Tasks A3, B3, D2, D3 each carry a test that scans for a read that skips it).
7. **The owner's calls in the design's § 20.**

## Files

| File | Part | What |
|---|---|---|
| `scripts/generators/gen_launch_windows.py` | 6a | Legs: returns, inner pairs, fixed outer legs, delta-v curves, the report's Fleets section |
| `common/script_values/sr_launch_windows_generated.txt`, `docs/engine/launch_windows_report.md` | 6a | Generated |
| `scripts/generators/gen_space_fleets.py` | 6a–6d | Create: `FLEET_LOCATIONS`, `ROLES`, per-slot and per-location output |
| `common/scripted_effects/sr_fleets_generated.txt`, `common/scripted_triggers/sr_fleets_generated.txt`, `common/script_values/sr_fleets_generated.txt`, `common/script_values/sr_fleets_display_generated.txt`, `common/customizable_localization/sr_fleets_generated_custom_loc.txt`, `gui/journal_entry_widgets/sr_fleets_generated_rows.gui` | 6a–6d | Generated |
| `scripts/generators/gen_solar_sites.py` and its outputs | 6a, 6b | Table fields `propellant` (6a) and `ships` (6b); per-world contact by fleet (6a); integrity, marines, occupation, blockade, ruin (6b) |
| `common/scripted_effects/sr_fleet_effects.txt` | 6a | Create: construction, the home fleet, orders, arrival, docking, refit, supply, repair, marines, the AI's 6a review |
| `common/scripted_triggers/sr_fleet_triggers.txt` | 6a–6d | Create: `sr_fleet_power`, dock, departure and hostility tests |
| `common/script_values/sr_fleet_values.txt`, `common/script_values/sr_fleet_display_values.txt` | 6a–6d | Create: every number; the panel's |
| `common/buildings/sr_space_command.txt`, `common/production_method_groups/sr_space_command_pmgs.txt`, `common/production_methods/sr_space_command_pms.txt` | 6a | Create |
| `common/static_modifiers/space_race_modifiers.txt` | 6a, 6d | `sr_fleet_upkeep`, `sr_orbital_superiority` |
| `common/scripted_effects/sr_site_effects.txt` | 6a, 6b | The global monthly step's order: landings, fleets' arrivals, combat, the worlds' step |
| `common/on_actions/space_race_on_actions.txt` | 6a | The country pulse calls the fleets' month for `sr_fleet_power` countries |
| `common/scripted_guis/sr_fleet_sguis.txt` | 6a–6d | Create: every panel control |
| `gui/journal_entry_widgets/space_race_widget.gui` | 6a, 6b, 6d | Space Command, Fleets, Locations, Colony Defences sections |
| `common/scripted_effects/sr_colony_autonomy_effects.txt`, `common/script_values/sr_colony_autonomy_values.txt` | 6a, 6b | The garrison under Full (6a); the destruction drift term (6b) |
| `common/scripted_effects/sr_fleet_combat_effects.txt` | 6b | Create: the combat step, defences and integrity, blockade, seizure, occupation, destruction, free colonies, war support records |
| `common/script_values/zz_te_war_support_injections.txt` | 6b | Two rows |
| `common/diplomatic_actions/covert_operations.txt` and the covert registry's sites | 6b | Survey Colony Defences, code 17 |
| `common/treaty_articles/124_cede_colony.txt` | 6c | The war goal's infamy against an interdictor |
| UN files named by `test_un_convention_registry.py` | 6c | The convention (op 33, docket item 17, `un_events.42`) |
| `common/script_values/un_dossier_values.txt`, `common/scripted_effects/un_dossier_effects.txt` | 6b | The `un_dos_space` ground |
| `common/buildings/sr_orbital_defense_battery.txt`, its PMG and PMs, `common/modifier_type_definitions/sr_orbital_defense_modifier_types.txt` | 6d | Create the battery; its two script-only state types |
| `common/scripted_effects/te_orbital_debris_effects.txt` | 6d | Low-pool removal in the world's step |
| `common/scripted_effects/sr_earth_orbit_effects.txt` | 6d | Create: the reserve, batteries' fire, the Earth blockade, orbital superiority |
| `common/game_rules/extra_game_rules.txt` | 6d | The default |
| `events/space_race_events.txt` | 6a–6d | `.100`–`.107` |
| `events/te_debug_space_race_events.txt` | 6a–6d | `te_debug_space_race.6` |
| `test_launch_windows.py`, `test_solar_sites.py`, `test_space_race_labels.py`, `test_space_race_layout.py`, `test_nation_tab.py`, `test_covert_op_registry.py`, `test_un_convention_registry.py`, `test_space_race_civil_war.py` | 6a–6d | Extended |
| `test_space_fleets.py` | 6a–6d | Create |
| `docs/testing/solar-colonies-playtest.md` | 6a–6d | A section per part |
| docs and the player guide | 6a–6d | Each part's last task |

---

## Part 6a: the fleet record, Space Command and movement (PR 1)

Branch from `main`. PR title: "Solar colonization slice 6a: fleets, Space Command and movement".

### Task A1: Legs in the launch-window generator

- [ ] **A1.1** `gen_launch_windows.py`: a `Location` table (the nine of the design's § 1.1, each with the body its legs are measured to; `inner` → Venus, `asteroids` → Ceres, `earth` → Earth) and a `LEGS` list of every ordered pair, each tagged `exact` (Earth → X), `cycle` (X → Earth, and the 12 ordered pairs among `inner`, `mars`, `asteroids`, `jupiter`) or `fixed` (the rest).
- [ ] **A1.2** Delta-v for Earth's outbound legs, per drive, by the offsets the transit curves already use: chemical the cheapest transfer plus the premium's extra delta-v; fusion the transfer it takes within its 30 km/s budget; torch and antimatter the brachistochrone's acceleration × time, capped. Emit `sr_leg_dv_<drive>_earth_<loc>` beside the existing `sr_transit_<drive>_<body>` (whose months the Earth legs reuse: `sr_leg_months_<drive>_earth_<loc>` reads them).
- [ ] **A1.3** Departure from a body's system: the loose capture orbit (eccentricity 0.9) the slice 3 capture model arrives in, from the `CAPTURE` table; small bodies depart from rendezvous. Add a helper and unit-test it against a hand calculation for Mars.
- [ ] **A1.4** `cycle` legs: for each pair, the mean synodic period `S` (hundredths of a month) and an epoch `E` fitted to the optimum departure dates over the span (least squares on the phase), then months and delta-v curves by signed offset, averaged over cycles as the premiums are. Emit `sr_leg_phase_<a>_<b>` = `(te_history_month_index * 100 + E) modulo S` with `E` large enough that the dividend is always positive, folded to a signed offset; then `sr_leg_months_<drive>_<a>_<b>` and `sr_leg_dv_<drive>_<a>_<b>` as binary searches on the offset (the premium curves' emitter). Report each pair's worst miss between the mean cycle and the true optimum.
- [ ] **A1.5** `fixed` legs: one median per drive for months and delta-v: `sr_leg_months_<drive>_<a>_<b> = { value = N }`.
- [ ] **A1.6** The rapid response rule (§ 1.2): readers `sr_leg_months_rapid_<drive>_<a>_<b>` that take the next drive's figures, and antimatter's at three quarters rounded up, at least 1.
- [ ] **A1.7** The report: a Fleets section (each pair's kind, cycle, epoch fit and miss, and the curves). Keep the generated values file under about 15,000 lines; print its size in the dry run.
- [ ] **A1.8** `test_launch_windows.py`: every ordered pair and drive has both readers; a better drive is never slower; Earth's outbound months equal today's transit values; the Python reimplementation of `sr_leg_phase` (integer arithmetic, positive dividend, folding) matches the generator's offset for every month of the span; the fixed legs' medians lie within their sampled range. Audits: `script_argument_audit`, `duplicate_key_audit`. Commit: "Launch windows: legs between the nine locations, with delta-v".

### Task A2: The fleets generator and the record

- [ ] **A2.1** `scripts/generators/gen_space_fleets.py` on `gen_solar_sites.py`'s pattern (`HEADER`, one BOM, `--dry-run`, `--check`, `main()`, write only on change), importing `gen_solar_sites.SITES` / `LOCATIONS` and `gen_launch_windows`' locations and legs. Constants: `SLOTS = 9`, `FLEET_LOCATIONS` (`earth` first, then `LOCATIONS`), `ROLES` (key, fire on fleets, fire on defences, endurance, screen, marines a point; the design's § 3 table).
- [ ] **A2.2** Register it (Global constraints) after `gen_solar_sites`.
- [ ] **A2.3** Per slot, generated effects (country scope): `sr_fl_<n>_clear`, `sr_fl_<n>_create_at = { LOC }` (an empty slot at a location, drive the nation's, propellant and supply full), `sr_fl_<n>_add_strength = { ROLE AMOUNT }` (now and full), `sr_fl_<n>_merge_into_<m>` (§ 4's rules), `sr_fl_<n>_detach_to_<m>`. Per slot values: `sr_fl_<n>_strength`, `_strength_full`, `_dv_capacity` (drive capacity × (1 + tender share)), `_endurance` (lowest non-tender role × (1 + 2 × tender share); 36 for tenders alone), `_marine_capacity`, `_fire_fleets`, `_fire_defences`, `_all_rapid`.
- [ ] **A2.4** `common/script_values/sr_fleet_values.txt`: drive capacities (12, 60, 1,000, 5,000), the refit (3 months), endurance attrition (5%), repair (20% at Earth, 10% a Spaceport level), the propellant refill at a non-propellant Spaceport (25%), marines a carrier point (2). Each with a comment naming the design's section.
- [ ] **A2.5** `test_space_fleets.py`: generated files current, one BOM and the header; nine slots each with every effect and value; `ROLES` matches the design's table; every `remove_variable` behind its `has_variable`. Commit: "Space fleets: the generator and the fleet record".

### Task A3: Space Command

- [ ] **A3.1** `common/buildings/sr_space_command.txt`: `building_space_command` (§ 5), unlocked by `space_militarization`, `potential` Full Colonies, `possible` the state has `building_space_program`, government only, expandable, its icon and background copied from an existing military building (a placeholder texture added through `git update-index --cacheinfo` if a new one is wanted; CI checks out without `gfx/`). Decide `bg_military` against `bg_government` by reading what vanilla's `bg_military` does to non-barracks buildings (conscription, the military lens); record the choice in the design's As built.
- [ ] **A3.2** `pmg_space_command_yards` and its four methods (§ 5's table), each gated by its technology (Antimatter Yards also on an owned `building_antimatter_facility`, through the method's `unlocking_` conditions or a `can_be_selected`-style trigger the engine supports; check vanilla's pattern first). Employment per level as the table. Validate every modifier and good name. Each method's loc description states its strength a level a month (design § 5: the rate is not a modifier, since upkeep raises the building's throughput).
- [ ] **A3.3** `sr_state_held_by_owner` (`sr_fleet_triggers.txt`, state scope: its `controller` is its `owner`, on `gm_trophy_values.txt:101`'s `controller =` comparison; design § 5.1). Vanilla keeps buildings working in an occupied state, so this test is the only thing that stops them.
- [ ] **A3.4** `sr_sc_rate` (country value): `every_scope_state` limited to `sr_state_held_by_owner = yes` → `every_scope_building` with `is_building_type = building_space_command`, adding `level × occupancy × rate`, the rate by `has_active_production_method`. Self-check `ship_construction` (§ 18): arm the month a Space Command first reaches half staff in a state its owner controls, log the month after. Play-test row: occupy the state province by province; construction stops when the controller turns, and the row records at how many provinces.
- [ ] **A3.5** The build mix: `sr_sc_mix_<role>` (absent reads the start weights), `sr_sc_month` (country): the month's points shared by weight into the home fleet (`sr_fl_home_slot`, generated: the lowest slot at Earth not in transit or refitting; else the lowest empty slot, created at Earth; else nothing).
- [ ] **A3.6** Upkeep: `sr_fleet_upkeep` (+1% `building_space_command_throughput_add` a unit; register the throughput modifier if it isn't), multiplier = full strength ÷ 10, removed first, refreshed in the fleets' monthly country step only. `gen_nation_tab.py` row, rerun, `test_nation_tab.py`.
- [ ] **A3.7** The AI's cap: `can_build_government` reads `sr_sc_may_build_government` (a player always; an AI below `2 + its colonies`, at most 10, only while `sr_ai_should_participate`, out of default, weekly income positive), counting queued levels as slice 4's base gate does.
- [ ] **A3.8** Tests: the gate; the building's fields; each method's technology; `sr_sc_rate` reads every method and only through `sr_state_held_by_owner`; the mix's weights sum; the cap counts queued levels. Audits: `pm_employment_audit`, `loc_coverage_audit`, `modifier_visibility_audit`. Commit: "Space Command: a building that launches fleet strength".

### Task A4: Movement

- [ ] **A4.1** Generated per slot × destination: `sr_fl_<n>_leg_months_<loc>`, `sr_fl_<n>_leg_dv_<loc>` (the slot's location and drive, or the rapid readers when `_all_rapid`), and the trigger `sr_fl_<n>_may_depart_<loc>` (at a location, not refitting, the leg leaves this month: an Earth leg by `sr_launch_site_departs`'s window rule for chemical and fusion, any month otherwise; propellant covers the delta-v).
- [ ] **A4.2** `sr_fl_<n>_dispatch_<loc>`: spend the delta-v; set `_dest`, `_depart`, `_arrive`; clear `_loc`; add to the destination's inbound record; record `sr_fl_<n>_leg_logged` for the self-check.
- [ ] **A4.3** Arrivals in the global monthly step, after colony fleets and shipments land (`sr_site_effects.txt`'s order) and before the worlds' step: every country in `sr_fleet_powers` lands its fleets whose month has come (`sr_fl_arrivals_country`, generated over slots). Posture as § 6. Contact for every world we hold at the location (`sr_site_contact_<key>` = now). Self-check `fleet_leg` on the first landing.
- [ ] **A4.4** The per-location records (§ 4): rebuilt after arrivals: `sr_loc_present_<loc>`, `sr_loc_strength_<loc>`, the inbound trio, and each country's `sr_fl_at_<loc>`. The `sr_fleet_powers` list: a country joins with its first fleet or Space Command (6d: or battery) and leaves when it has none of them (dead entries dropped, `is_country_alive`); a yearly `every_country` pass (the one place it is used) adds any owner of a Space Command or battery the list missed.
- [ ] **A4.5** The fleets' monthly country step (`sr_fl_month`, from `space_race_on_actions.txt`'s country pulse for `sr_fleet_power` countries): construction (A3.5), then per slot: docked? (`sr_fl_<n>_docked`: at Earth, or at a location where we hold a world with `sr_site_port_<key>` ≥ 1), then refit (start or finish), refill propellant (fully at Earth or at a propellant world's Spaceport; else 25%), supply (refill docked; else −1, attrition at 0), repair (20% at Earth; 10% a Spaceport level, the best at the location), marines (refill at Earth); then the upkeep refresh.
- [ ] **A4.6** Site table field `propellant` (`gen_solar_sites.SITES`, § 2's ten worlds) and the generated `sr_loc_propellant_port_<loc>` (we hold a propellant world with a Spaceport there). `test_solar_sites.py` holds the field's list.
- [ ] **A4.7** A revolution: the winner inherits every slot (variables); `test_space_race_civil_war.py` gains the fleet variables to its inherited list, and the `sr_fleet_powers` entry is repointed in `sr_repair_after_civil_war`.
- [ ] **A4.8** Tests: a dispatch spends exactly the leg's delta-v; an order is refused short of it; a refit blocks departure; the arrival sets the posture; the step's order (landings before the worlds' step); attrition and repair stay within 0 and full. Audits: `container_timed_variable_audit`, `je_immediate_reset_audit`, `prev_scope_audit`, `iterator_limit_audit`. Commit: "Space fleets: orders, legs, docking, refits and supply".

### Task A5: Marines and the garrison under Full Colonies

- [ ] **A5.1** Generated per slot × world (only the worlds at each location): `sr_fl_<n>_land_marines_<key>` and `_embark_<key>`, moving battalions between the fleet and `sr_site_marines_<key>` (global; the holder's), within the fleet's capacity.
- [ ] **A5.2** `sr_site_garrison_at` (slice 5) under Full: set `sr_site_garrison_due_<key>` (365 days) instead of the garrison; the world's monthly step makes the garrison take effect (slice 5's −25 autonomy, ten years, resentment, upkeep) once `sr_site_marines_<key>` ≥ 2, and on the due date's lapse tells a player (`.107`). Under Simple, unchanged. Option text of `.94` gains a Full-only `custom_tooltip` line.
- [ ] **A5.3** A cession or an heir: marines stay if the new holder is the old one's ally, else go home (added to the old holder's home fleet, or lost with no slot). A release loses them.
- [ ] **A5.4** Tests: the due date's both outcomes; the Simple branch untouched; the cession rule. `silent_variable_audit`. Commit: "Space fleets: marines and garrisons".

### Task A6: The AI (building and garrisons)

- [ ] **A6.1** `sr_fl_ai_review` (monthly for AI `sr_fleet_power` countries; yearly for the build decisions): keep the start mix; keep the home fleet at Earth; send a fleet with marines to any world with `sr_site_garrison_due_<key>` and land them on arrival; bring it home after.
- [ ] **A6.2** Tests: the review only issues orders `sr_fl_<n>_may_depart_<loc>` allows. Commit: "Space fleets: the AI builds and garrisons".

### Task A7: The panel

- [ ] **A7.1** Generated rows (`gui/journal_entry_widgets/sr_fleets_generated_rows.gui`): Fleets (one row per slot, § 16) and Locations (one per location); display values in `sr_fleets_display_generated.txt`; custom loc for location names.
- [ ] **A7.2** `space_race_widget.gui`: the Space Command, Fleets and Locations sections (Full only; open by default; client-side flags `sr_panel_space_command_closed`, `sr_panel_fleets_closed`, `sr_panel_locations_closed`), following the Colony Modules section's markup.
- [ ] **A7.3** `common/scripted_guis/sr_fleet_sguis.txt`: the mix steppers (`scope:op` the role), the destination stepper (`sr_fl_dest_pick_<n>`, a country variable per slot, stepping through the other eight), Go, Merge (into the next of ours at the location), Detach, Land, Embark; each `is_valid` the same trigger the effect checks, each hover from a loc key.
- [ ] **A7.4** Loc for every label and hover; `organize_loc.py`. The destination's hover gives the leg's months and delta-v and the window state.
- [ ] **A7.5** `test_space_race_labels.py` and `test_space_race_layout.py` read the new file; `test_tax_code_bypass.py` and `gui_modding_guide.md` if the new GUI file needs a table row; `scripts/analysis/check_gui_lint.py`; `gui_reference_audit --strict`. Commit: "Space fleets: the panel".

### Task A8: Console, self-checks, docs and the guide

- [ ] **A8.1** `te_debug_space_race.6`: log fleets and locations; 100 of each role at Earth; land our fleets; fill propellant and supply; our drive to the next.
- [ ] **A8.2** `docs/testing/solar-colonies-playtest.md`: a 6a section with `ship_construction` and `fleet_leg` rows (when, OK, BROKEN, fallback) and the play-test steps (§ 18's 6a items).
- [ ] **A8.3** Docs: `mod_systems.md` § Space Race (a *Fleets* subsection; the variables and globals tables), `journal_entry_systems.md` (the sections; CRLF), `python_tools.md` and `auto_generated_files.md` (the generator), `scripting_best_practices.md` for anything the build learns. The design gains § 22, As built.
- [ ] **A8.4** Player guide `16-space.md`: a "Fleets" subsection under Colonizing the solar system at the depth of its peers (Space Command, roles, legs and propellant, refits, marines and garrisons), and `17-reference.md` where it lists buildings; rebuild the PDF; `check_player_guide_style.py --strict`.
- [ ] **A8.5** Everything CI runs. Push; open the PR (body: what, the owner's calls still open, the Player guide line, the self-checks). Then 6b.

---

## Part 6b: combat, blockade, seizure and destruction (PR 2)

Branch from `main` after 6a merges. PR title: "Solar colonization slice 6b: combat, blockade, seizure and destruction".

### Task B1: The per-world record

- [ ] **B1.1** `gen_solar_sites.py`: `sr_site_integrity_<key>` (absent 100), `sr_site_occupier_<key>`, `sr_site_blockaded_<key>`, `sr_site_ruined_<key>` (timed 25 years), `sr_site_bombard_<key>` (consecutive months), `sr_site_under_assault_<key>`; each cleared by a release (ruin aside) and by `slice5_vars`'s pattern.
- [ ] **B1.2** Table field `ships` per world, `(bool, bool)` for its two specializations (§ 8): set by reading each specialization's modifier for goods and throughput terms against research terms; hand-check the 68 and record the list in the generator's comment.
- [ ] **B1.3** The sync: an occupied world unmirrors (as a free one does); `sr_site_mult_<a|b>_<key>` gains the blockade factor (0 for a shipping specialization while blockaded).
- [ ] **B1.4** `sr_cf_targetable_<key>` and founding read the ruin; the Solar System display values gain Occupied and Ruined.
- [ ] **B1.5** Tests in `test_solar_sites.py`: every world has each new variable, release clears it, the ruin blocks founding, the factor's placement. Commit: "Solar sites: integrity, occupation, blockade and ruin".

### Task B2: Postures and targets

- [ ] **B2.1** Generated per slot: `sr_fl_<n>_posture` steppers and `sr_fl_<n>_target` (a world at the location, stepping), `_destroy` toggle; the arrival's default posture (A4.3).
- [ ] **B2.2** Panel buttons and scripted GUIs; closing in on a world needs war with its holder, or the world free (§ 9.4); 6b refuses standing off at a location of a country at peace with us (6c lifts that).
- [ ] **B2.3** Tests; commit: "Space fleets: postures and targets".

### Task B3: The combat step

- [ ] **B3.1** `sr_fleet_combat_effects.txt`: `sr_combat_global_monthly`, after arrivals and before the worlds' step, per location: pass 1, each present country's fire on fleets and on defences (its slots there summed, × quality `sr_fleet_quality`), and its engaged hostile strength (§ 7.1's table, `has_war_with`, the free-colony rule); pass 2, each country's losses = the sum over hostile countries engaged of their fire × its share of their targets (`sr_fleet_k` = 0.1). Stored in country variables keyed by location; nested loops over `sr_fleet_powers` only.
- [ ] **B3.2** Losses applied per slot in proportion to the slot's share of the country's strength there, by screening (§ 3) and half destroyed, half damage (generated `sr_fl_<n>_take_losses`).
- [ ] **B3.3** The Orbital Battlestation at Earth (§ 7.5): its strength record on the owner (`sr_battlestation_strength`), full = 25 × level, regaining 10% a month, joined to the owner's Earth forces, all only while its state passes `sr_state_held_by_owner` (§ 5.1): occupied, it neither fights nor recovers. A test holds the read to the trigger.
- [ ] **B3.4** Debris at Earth (`te_debris_add`), the battle notice `.101` (players, once a month per location), the battle's war support record (§ 10).
- [ ] **B3.5** Tests: a Python model of the two passes, run on three cases (one against one, two against one, a three-way) against constants read from the values file, checks the square law's 100-against-50 result and that every fleet's losses equal the fire allocated to it; screens first; no strength below 0. Audits: `iterator_limit_audit`, `prev_scope_audit`, `change_variable_clamp_audit`. Commit: "Space fleets: combat at a location".

### Task B4: Defences and integrity

- [ ] **B4.1** Defences' fire (§ 7.3), joined to the holder's side against fleets closing in on the world; integrity loss from the fire aimed at defences; regain under no assault; +25 on a module landing (slice 4's install). An occupied world's Defences fire for no one (§ 9.2): a liberation fights the occupier's fleets and garrison only.
- [ ] **B4.2** Survey Colony Defences' edge is read here (B9).
- [ ] **B4.3** Tests; commit: "Colony Defences fire, and integrity".

### Task B5: Blockade

- [ ] **B5.1** `sr_site_blockaded_<key>` recomputed each month (not at Earth); emigration's distribution skips it; a shipment landing there is lost; contact isn't recorded; `sr_ebase_refresh` skips its room; the specialization factor.
- [ ] **B5.2** Tests: each effect's site reads the flag. Commit: "Blockades away from Earth".

### Task B6: Seizure, occupation and the peace

- [ ] **B6.1** Seizure (§ 9.1): integrity 0, no hostile fleet stationed, marines above garrison plus militia (`sr_site_militia_<key>`, a battalion a 20,000, at least 1); the marines needed land as the occupier's garrison.
- [ ] **B6.2** The monthly return (§ 9.2): every occupied world whose occupier and holder aren't at war goes back (`.102`); a Cede Colony transfer clears occupation; liberation; a dead holder's occupied world to its heir or its occupier.
- [ ] **B6.3** Self-check is not needed (script sees it); the play-test list carries a peace that returns a world and one that cedes it.
- [ ] **B6.4** Tests: no path leaves a world occupied by a country at peace with its holder after the step; the transfer clears it. Commit: "Seizure, occupation and the return at the peace".

### Task B7: Destruction

- [ ] **B7.1** § 9.3: three consecutive months (`sr_site_bombard_<key>`), the release, the ruin, 20 infamy (`sr_colony_destroy_infamy`, doubled for a convention party once 6c exists: read through a trigger that is `no` until then), `un_dos_space` + 20 through `un_dossier_record` (add the ground in `un_dossier_values.txt`'s header list, its decay and cap, the case strength sum and its tests), +10 autonomy at the destroyer's colonies and `sr_destroyed_colony_until` (ten years) read by a new term in `sr_site_aut_drift_<key>` (+0.2); `.103`.
- [ ] **B7.2** Tests; the drift's terms table in `mod_systems.md`. Commit: "Destroying a colony".

### Task B8: Free colonies by force

- [ ] **B8.1** § 9.4: closing in on a free colony with no war, 10 infamy and `un_dos_space` + 10 when it begins (once per fleet and world), seizure at integrity 0 with marines above militia: holder, autonomy 60, ties cleared; `.104`.
- [ ] **B8.2** Tests; commit: "Free colonies taken by force".

### Task B9: War support and Survey Colony Defences

- [ ] **B9.1** Monthly, in the fleets' step: per country `sr_ws_colonies_net` = Σ the weight (§ 10) of each world it occupies from a holder it is at war with, minus each of its worlds an enemy occupies (`sr_ws_colonies_sum`, generated over the 34 worlds in `gen_solar_sites.py`'s values); and `sr_ws_battle` (timed 30 days, ±0.1 or ±0.25). `zz_te_war_support_injections.txt`: two rows (desc keys in `te_miscellaneous_l_english.yml`) reading the two variables, nothing else, per the file's header.
- [ ] **B9.2** Survey Colony Defences, code 17 (§ 11): `test_covert_op_registry.py`'s row first, then every site it names; the intelligence display (a rival's Defences as a range without it) and the fire edge in B4.
- [ ] **B9.3** Tests; `loc_render_audit`, `script_loc_reference_audit`. Commit: "War support from space, and Survey Colony Defences".

### Task B10: The AI's defence

- [ ] **B10.1** § 14's 6b rules in `sr_fl_ai_review`; the war mix.
- [ ] **B10.2** Tests: orders only through `may_depart`; recall before supply runs out. Commit: "Space fleets: the AI defends".

### Task B11: Panel, notices, console, docs

- [ ] **B11.1** Colony Defences section; Locations' markers; Solar System's Occupied and Ruined; `.100`–`.104` with images and loc.
- [ ] **B11.2** Console options (§ 18's 6b items); play-test rows; docs as A8.3; player guide (combat, blockade, seizure, destruction, the peace) at its peers' depth; the design's As built; everything CI runs; the PR.

---

## Part 6c: interdiction, the AI's offence and the convention (PR 3)

Branch from `main` after 6b merges. PR title: "Solar colonization slice 6c: interdiction in peace, the AI's offence and the outer-space convention".

### Task C1: Interdiction in peace

- [ ] **C1.1** Standing off at a location where a country at peace with us holds a world: allowed; the blockade rule (B5) counts such a fleet; a stationed or standing-off fleet of the target makes it a standoff.
- [ ] **C1.2** The price on the first month of each interdiction (per fleet and target): 5 infamy, `un_dos_space` + 10, `sr_interdiction_target` and `sr_interdiction_recent` (five years) on the interdictor; `.105` to the target.
- [ ] **C1.3** Cede Colony's war goal `infamy` (`124_cede_colony.txt`): an `if` that sets it to 0 when `scope:target_country` has `sr_interdiction_recent` and `var:sr_interdiction_target ?= root` (the play-test row checks the scopes resolve; if they don't, record it and fall back to a half price on the article's AI score).
- [ ] **C1.4** Tests; `treaty_evaluation_scope_audit`. Commit: "Interdiction in peace".

### Task C2: The outer-space convention

- [ ] **C2.1** `test_un_convention_registry.py`: the `CONVENTIONS` row for `colony_protection` (op 33, `un_events.42`, docket item 17, country-scoped, the space race and UN rules, `agenda = True`), then every site its failures name.
- [ ] **C2.2** The docket item raised by `sr_colony_un_on_seizure` (B6.1, B7.1, B8.1 call it), the actor marked; tabling from the chamber by a member with `sr_has_space_colony`; `un_propose_colony_protection_button` for the AI (its `ai_chance` from holding colonies and a rival's seizure or destruction on record).
- [ ] **C2.3** Parties: +2% prestige × E; `sr_colony_convention_party`, now read by the infamy and dossier doubling. The topic's terms text (`je_un_terms_colony_protection`), `test_un_terms_tooltips.py`.
- [ ] **C2.4** Tests; commit: "The Convention on the Settlement of Outer Space".

### Task C3: The AI's offence at war

- [ ] **C3.1** § 14's 6c rules; never destroy, never seize a free colony, never interdict; an interdiction of its colonies counts as a threat for the defence rule (B10), so it stations a fleet there.
- [ ] **C3.2** Tests: the review never orders a leg it can't return from without a dock; no peacetime stand-off at another's colonies. Commit: "Space fleets: the AI attacks at war".

### Task C4: Notices, docs, the guide

- [ ] **C4.1** Console (start an interdiction), play-test rows (Cede Colony's infamy against an interdictor; the convention in the chamber), docs, the player guide (interdiction, the convention), the design's As built, everything CI runs, the PR.

---

## Part 6d: Earth orbit (PR 4)

Branch from `main` after 6c merges. PR title: "Solar colonization slice 6d: Earth orbit, the ground reserve and ground-to-orbit batteries; Full Colonies by default".

### Task D1: The ground reserve

- [ ] **D1.1** `sr_reserve_<role>` (country); `sr_sc_month` adds to the reserve; Launch (`sr_reserve_launch`: the whole reserve into the lowest empty slot at Earth, or merged into the home fleet with none empty); `sr_reserve_auto` (on by default: with no hostile fleet at Earth, the month's construction launches itself, which is 6a's behaviour).
- [ ] **D1.2** Panel (the Space Command section's reserve line, Launch, the toggle), the AI's launch rule. Tests; commit: "Space Command: a ground reserve".

### Task D2: Ground-to-orbit batteries

- [ ] **D2.1** `building_orbital_defense_battery`, levels in any state, Space Militarization, Full Colonies; `pmg_orbital_defense_battery` with Kinetic Interceptors and Ground Lasers (§ 15's table, electricity on the lasers); jobs and inputs at a first guess.
- [ ] **D2.2** The figures as modifiers (design § 15, the owner's suggestion): register `state_orbital_battery_fire_add` (decimals 1) and `state_orbital_debris_sweep_add` (decimals 2, so 0.01 doesn't render as +0) as `script_only = yes` state types in `common/modifier_type_definitions/sr_orbital_defense_modifier_types.txt`, on `barracks_training_modifier_types.txt`'s pattern, with names and `_desc` in `te_modifiers_l_english.yml` ("Fire on Hostile Fleets at Earth", "Low-Orbit Debris Swept in Peace"). Each method's `state_modifiers = { workforce_scaled = { … } }`: Kinetic Interceptors fire 1; Ground Lasers fire 2 and sweep 0.01. One field each, no building-scoped copy (`scripting_best_practices.md`: the game lists a method's state modifiers beside its building ones, so a copy shows twice). `modifier_visibility_audit --strict`.
- [ ] **D2.3** Fire in the Earth battle: `sr_battery_fire` (country value: `every_scope_state` limited to `sr_state_held_by_owner = yes`, adding `modifier:state_orbital_battery_fire_add`, as `barracks_training_values.txt:29` reads its state type), joined to its Earth side's fire; no losses; kinetic debris (0.02 low a point of Kinetic Interceptors' fire).
- [ ] **D2.4** Low-orbit sweeping: `sr_battery_sweep` (the same sum of `modifier:state_orbital_debris_sweep_add`, and 0 while the country is at war). `te_debris_global_monthly` sums every country's sweep (through `sr_fleet_powers`, which a battery's owner joins, not `every_country`) and takes it from the low pool alone, after the existing removal. Self-check `battery_sweep`.
- [ ] **D2.5** Tests: the sweep never touches the high pool; fire and sweep read their state types only through `sr_state_held_by_owner`; each method carries its state modifiers and no building-scoped copy; `test_orbital_debris.py` still passes. Commit: "Ground-to-orbit batteries".

### Task D3: Blockading Earth

- [ ] **D3.1** The B5 rule at Earth: the target's colony fleets, module shipments, settlers and fleet departures from Earth are refused, and none of its colonies records contact; the reserve's Launch still works. `.106` to the target.
- [ ] **D3.2** The launch site occupied (design § 5.1, § 15), Full Colonies only: `sr_launches_barred` (country: `sr_earth_blockaded`, or the Space Program's state fails `sr_state_held_by_owner`) gates every departure path (`sr_cf_launch_month`, `sr_ms_global_month`'s departures, `sr_emig_month`, `sr_fl_<n>_may_depart_<loc>` from Earth) and module fabrication (`sr_mod_month` banks no points); Launch from the reserve reads only the occupation half. A player is told once when the site is lost and when it is back.
- [ ] **D3.3** Tests: each departure path and fabrication read `sr_launches_barred`; Launch reads only the occupation half; under Races Only and Simple Colonies none of it applies. Commit: "Blockading Earth, and an occupied launch site".

### Task D4: Orbital fire support

- [ ] **D4.1** `sr_orbital_superiority` (+10% `unit_offense_mult`, +5% `unit_defense_mult`) at the margin (§ 15), on countries at war, removed first, refreshed in the fleets' monthly step; `gen_nation_tab.py` row.
- [ ] **D4.2** Tests; commit: "Orbital fire support".

### Task D5: The AI, the default, docs

- [ ] **D5.1** § 14's 6d rules (launch, batteries at war, lasers in peace from Cluttered).
- [ ] **D5.2** `space_race_rule`'s default to `space_race_colonies_full`; `test_solar_sites.py`'s rule test; the release notes' entry if the release checklist wants one.
- [ ] **D5.3** Console (fill the reserve; our Earth blockaded by the largest rival), play-test rows, docs, the player guide (Earth orbit, batteries, the default in the rules chapter), the design's As built; move the scope, this design and this plan to `archive/` per `docs/superpowers/README.md` once nothing is left; everything CI runs; the PR.
