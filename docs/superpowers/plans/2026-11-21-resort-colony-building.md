# The Resort Colony building: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the Resort Colony method off the Extraplanetary Base into a new building, `building_space_resort`, with its own room and draw at each world, and make the Off-World Resort module feed that room.

**Architecture:** A twin of the base-room code. `gen_solar_sites.py` gets a `RESORTS` table and writes the resort room values, the best-draw-first fill and the per-site display values. Hand-written script adds the building, its method, the refresh with its modifier pair, the build gates and the day-after hook. The space race widget gets an overview cell, Modules-view rows and site figures.

**Tech Stack:** Paradox script (Victoria 3 1.15), Python 3.11/3.12 generators and unittest/pytest tests.

**Spec:** `docs/superpowers/specs/2026-11-21-resort-colony-building-design.md`

**Worktree:** `/home/jakef/src/te-worktrees/resort-colony`, branch `feature/resort-colony-building`, base `a2aebeba4`. Never `POST /reload` from here. Run Python with `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python` (written `$PY` below).

## Global Constraints

- Building key `building_space_resort`, loc "Resort Colony"; method key stays `pm_space_colony_vacation`, loc "Luxury Resorts".
- Method inputs a level (workforce-scaled): Electronic Components 15, Wireless Telecommunication Gear (`radios`) 30, Digital Access 10, Advanced Materials 0.5, Launch Capacity 480, Wine 50, Luxury Furniture 30, Fruit 30. Outputs: Fine Art 300, Tourism 900. Inputs £108,000, profit £42,000 at base prices.
- Room: Earth orbit `ORBIT_RESORT_ROOM = 10` at draw 0, for every country with `space_colonization`. Each serving world's `resort_room` is its `room` (10 to 50, 945 in all), plus `sr_mod_resort_room = 10` per staffed Off-World Resort level, floored. Past the room `RESORT_OVERFLOW_DRAW = -75`.
- Draws (percent): Tranquility +30; Olympus Mons, Valles Marineris +25; Shackleton, Marius Hills, Venus, Iapetus, Enceladus +15; Imbrium, Peary, Vesta, Callisto, Titan +10; Hellas, Ceres, Rhea, Mimas +5; Daedalus, Utopia, Arcadia, Psyche, Europa, Ganymede, Miranda 0; Mercury, Pallas, Io, Amalthea, Triton −5; Hygiea, Pluto −10; Himalia, Titania, Oberon, Ariel −15; Proteus, Haumea −25; Eris, Makemake −30; Sedna −35.
- Fill order: `(-draw, 1, index)`, Earth orbit at `(0, 0, 0)`.
- Under Races Only (`sr_colonies_contested_enabled` false): unlimited, no modifier.
- Off-World Resort: a hook (no `sr_module_resort` modifier), queued only with `space_colonization`. AI line: `sr_resort_queued_levels >= sr_resort_room_total`.
- Throughput carried to the resort, each a `building_space_resort_throughput_add` line equal to the base's: `sr_commercial_space_dividend` (0.05), `te_orbital_debris` (−0.002), `pm_spaceport`'s state modifier (0.01).
- Tabs in Paradox files; `.txt`, `.gui` and loc `.yml` files start with exactly one UTF-8 BOM. Never hand-edit generated files: edit `gen_solar_sites.py` and rerun it.
- Commit by path, never `git add -A` / `-a`. Each commit ends with the attribution lines from the session's system reminder.

## Review Focus

1. **A country with no colony.** It gets Earth orbit's 10 levels at 0, and an 11th level drags the average toward −75%: `sr_resort_room_total` adds 10 under `space_colonization` alone (Task 1 test).
2. **A blockaded or occupied colony.** Its resort room leaves the total and the fill, through `site_serves`, as base room does (Task 1 test).
3. **The Space Race rule switched to Races Only mid-game.** The next refresh removes both modifiers and adds neither (Task 3 test: removal before the contested-rule `if`).
4. **Several levels finishing on one day.** One hook event fires, not one per level: the pending marker (Task 3 test).
5. **A module queued before Space Colonization.** Queueing refuses it with its reason line. A level already standing in an old save adds room once the technology arrives (Task 4 test: the queue trigger and the GUI reason).

---

### Task 1: The sites table, room values and fill (generator)

**Files:**
- Modify: `scripts/generators/gen_solar_sites.py` (constants near `NEAR_EARTH_ROOM` ~l.358; `Site` properties ~l.92; `ebase_tiers()` ~l.474; `render_module_values()` ~l.1917-1925; the per-site block ~l.1987-1991; the fill writer ~l.2389-2440; `render_display()` ~l.3657)
- Generated (rerun, don't edit): `common/script_values/sr_sites_generated.txt`, `common/scripted_effects/sr_sites_generated.txt`, `common/script_values/sr_sites_display_generated.txt`
- Modify: `common/script_values/sr_colony_module_values.txt` (beside `sr_mod_mine_room` l.120 and `sr_ebase_levels` l.190)
- Test: `test_resort_colony.py` (new; helpers `_raw`, `_strip`, `_block` imported from `test_solar_sites`)

**Interfaces:**
- Produces (Python): `RESORTS: dict[str, tuple[int, int]]` (key → (room, draw)), `Site.resort_room -> int`, `Site.resort_draw -> int`, `ORBIT_RESORT_ROOM = 10`, `RESORT_TECH = "space_colonization"`, `RESORT_OVERFLOW_DRAW = -75`, `resort_tiers() -> list[Site | None]`.
- Produces (script): `sr_resort_room_total` (country value), `sr_site_resort_room_<key>` (any-scope value), `sr_resort_fill` (effect: reads `local_var:sr_rs_left`, writes `local_var:sr_rs_sum`), `sr_resort_next_fill` (effect: sets `var:sr_resort_next_draw`, reads `sr_resort_queued_levels`), `sr_disp_site_resort_room_<key>`, `sr_mod_resort_room = { value = 10 }`, `sr_resort_levels`, `sr_resort_queued_levels`.

- [ ] **Step 1: Write the failing tests** in `test_resort_colony.py`, class `ResortTableTest` and `ResortRoomTest`:
  - `test_every_site_has_a_resort_row`: `set(gss.RESORTS) == {s.key for s in gss.SITES}`.
  - `test_room_is_the_worlds_room_for_now`: for every site, `site.resort_room == site.room`; `sum(...) == 945`.
  - `test_draws_are_the_designs`: a dict literal of the 40 draws from Global Constraints equals `{s.key: s.resort_draw for s in gss.SITES}`; every draw `% 5 == 0` and in `[-35, 30]`.
  - `test_constants`: `ORBIT_RESORT_ROOM == 10`, `RESORT_TECH == "space_colonization"`, `RESORT_OVERFLOW_DRAW == -75`.
  - `test_tiers_best_draw_first`: `resort_tiers()[0].key == "tranquility"`, `resort_tiers()[-1].key == "sedna"`, `None` appears once, before every site with draw 0, and after every site with draw > 0.
  - `test_room_total`: in `_strip(_raw("common","script_values","sr_sites_generated.txt"))`, block `sr_resort_room_total` contains `if = { limit = { has_technology_researched = space_colonization } add = 10 }`, and for each site `f"{gss.site_serves(s)} }} add = sr_site_resort_room_{k} }}"`.
  - `test_site_room`: block `sr_site_resort_room_<k>` contains `value = <resort_room>` and `add = { value = sr_site_resort_staffed_<k> multiply = sr_mod_resort_room floor = yes }`.
  - `test_fill_and_next_fill`: blocks `sr_resort_fill` and `sr_resort_next_fill` exist in the generated effects; `sr_resort_fill` has one `max = sr_site_resort_room_<k>` per site and `max = 10` once, and multiplies by `-75` past all of it; `sr_resort_next_fill` sets `sr_resort_next_draw`.
  - `test_hand_values`: `sr_colony_module_values.txt` has `sr_mod_resort_room = { value = 10 }`, and `sr_resort_levels` / `sr_resort_queued_levels` count `building_space_resort` (`add = level`, `add = level_after_queued_constructions`).
  - `test_display`: the generated display file has `sr_disp_site_resort_room_<k> = { value = sr_site_resort_room_<k> }` for every site.

- [ ] **Step 2: Run and see them fail.** `$PY -m pytest test_resort_colony.py -q`. Expected: fail on `AttributeError: ... RESORTS`.

- [ ] **Step 3: Implement in `gen_solar_sites.py`.**
  - `RESORTS` beside `SHIPPING`, one line per site, `(room, draw)`, with a comment citing spec § 6.2. `Site.resort_room` / `Site.resort_draw` read it, as `Site.ships` reads `SHIPPING`.
  - `resort_tiers()` mirrors `ebase_tiers()`.
  - The room total, the per-site value (its staffed term uses `sr_site_resort_staffed_{k}`, which `render_module_values` already writes for every generic facility), the fill and the next fill mirror the base's. Use the local variables `sr_rs_left`, `sr_rs_take`, `sr_rs_sum` and `sr_rs_next_left`, and comments that name spec § 6.
  - `sr_disp_site_resort_room_{k}` goes beside `sr_disp_site_ebase_room_{k}`.
  - Add `sr_mod_resort_room`, `sr_resort_levels` and `sr_resort_queued_levels` to `sr_colony_module_values.txt` by hand, beside their base twins.

- [ ] **Step 4: Regenerate and pass.** Run `$PY scripts/generators/gen_solar_sites.py`, then `$PY -m pytest test_resort_colony.py test_solar_sites.py -q`. Expected: all pass. `test_solar_sites`' `GeneratedFilesTest` holds the files equal to the generator.

- [ ] **Step 5: Commit** `scripts/generators/gen_solar_sites.py`, the three generated files, `sr_colony_module_values.txt` and `test_resort_colony.py`: "Resort Colony room: sites table, room values and fill (#1948)".

### Task 2: The building, its method and the lists that name buildings

**Files:**
- Modify: `common/buildings/extra_buildings.txt` (new `REPLACE_OR_CREATE:building_space_resort` straight after `building_space_mine`, l.416-447)
- Modify: `common/production_method_groups/extra_pm_groups.txt:1096-1107` (drop `pm_space_colony_vacation`; new `REPLACE_OR_CREATE:pmg_base_building_space_resort` after it, holding only `pm_space_colony_vacation`)
- Modify: `common/production_methods/extra_pms.txt:17774-17812` (the new inputs; the note at ~17632 "five base methods" → "four"; a comment above the method naming the building)
- Modify: `common/company_types/extra_companies_flavored.txt:3953-3958` (Axiom Space: add `building_space_resort` to `building_types`)
- Modify: `common/scripted_triggers/misc_triggers.txt` (`is_privately_expandable_building_type`, after `building_space_mine` l.160), `common/scripted_triggers/te_orbital_debris_triggers.txt` (`te_debris_uses_orbit`, l.28)
- Modify: `test_building_list_order.py:42` (`TAIL_BUILDINGS`), `test_maintenance_tiers.py:235` (intensive list)
- Modify loc: `localization/english/te_buildings_l_english.yml` (beside `building_space_mine` l.542), `localization/english/te_production_methods_l_english.yml` (l.2257 → "Luxury Resorts"; `pmg_base_building_space_resort` beside l.2500)
- Test: `test_resort_colony.py` (class `ResortBuildingTest`)

**Interfaces:**
- Consumes: `sr_resort_may_build_government`, `sr_resort_may_build_private` (Task 3 writes them; this task's building references them, so Tasks 2 and 3 land in one commit pair before any reload).
- Produces: `building_space_resort`, `pmg_base_building_space_resort`.

- [ ] **Step 1: Write the failing tests:**
  - `test_building_shape`: the block `REPLACE_OR_CREATE:building_space_resort` has `bg_exotic`, `space_colonization`, the groups `pmg_base_building_space_resort`, `pmg_launch_to_orbit_building_space_mine`, `pmg_transport_in_space_building_space_mine` and `pmg_maintenance_intensive`, `construction_cost_space_mine`, `owner ?= { sr_resort_may_build_government = yes }` and `owner ?= { sr_resort_may_build_private = yes }`.
  - `test_base_group_is_the_four_mining_methods`: `pmg_base_building_space_mine` lists exactly `pm_regolith_processing, pm_space_mine, pm_space_colony_mining, pm_self_replicating_miners`; `pmg_base_building_space_resort` lists exactly `pm_space_colony_vacation`.
  - `test_method_figures`: parse `pm_space_colony_vacation`'s `goods_input_*_add` and `goods_output_*_add` against the base prices (vanilla `vanilla_parsed/common/goods.json` and the mod's `common/goods/*.txt`). Inputs sum to 108000, outputs to 150000; Advanced Materials is 0.5; no input good is `local`, except `digital_access`; there is no `services` input.
  - `test_axiom_lists_the_resort`: Axiom Space's `building_types` holds `building_space_resort` and `building_space_mine`.
  - `test_lists_name_the_resort`: `is_privately_expandable_building_type` and `te_debris_uses_orbit` name `building_space_resort`.

- [ ] **Step 2: Run them; they fail.** `$PY -m pytest test_resort_colony.py -q -k ResortBuildingTest`.

- [ ] **Step 3: Implement.**
  - The building copies the base's block, except for the technology, the base group, the gates and a comment pointing at the spec.
  - Method inputs as in Global Constraints. Keep the crew and `required_input_goods`. The `# Price:` comment lines are rewritten by `pm_costs` (`$PY pm_costs.py`): run it, and commit its output for this method only.
  - Loc: `building_space_resort:0 "Resort Colony"`, `pmg_base_building_space_resort:0 "Base Building Space Resort"` (the pattern of l.2500), and `pm_space_colony_vacation:0 "Luxury Resorts"`. Add `building_space_resort_throughput_add` and `_desc` in Task 3.

- [ ] **Step 4: Pass.** `$PY -m pytest test_resort_colony.py test_building_list_order.py test_maintenance_tiers.py test_deep_sea_rebalance.py -q`. Expected: pass, apart from the gates' existence, which Task 3 makes true (the shape test only reads text).

- [ ] **Step 5: Commit** the files above: "Resort Colony: a building of its own, off the Extraplanetary Base (#1948)".

### Task 3: The refresh, its modifiers, the gates and the hook (review this task)

**Files:**
- Modify: `common/scripted_effects/sr_colony_module_effects.txt` (after `sr_ebase_hook_fire`, ~l.488: `sr_resort_refresh`, `sr_resort_hook_fire`)
- Modify: `common/scripted_triggers/sr_colony_module_triggers.txt` (after `sr_ebase_may_build_private`, ~l.105)
- Modify: `common/static_modifiers/space_race_modifiers.txt` (after `sr_ebase_room_penalty` l.415: the pair; `sr_commercial_space_dividend` l.425-428: second line)
- Modify: `common/static_modifiers/te_orbital_debris_modifiers.txt` (the file holding `te_orbital_debris`, l.28-36), `common/production_methods/extra_pms.txt:11608-11617` (`pm_spaceport` state modifier)
- Modify: `common/modifier_type_definitions/mod_entity_modifier_types.txt` (after `building_space_mine_throughput_add` l.923)
- Modify: `common/on_actions/space_race_on_actions.txt:16-22` (monthly), `common/on_actions/extra_on_actions.txt:733-750` (built / expanded)
- Modify: `events/space_race_events.txt` (new hidden `space_race_events.112` after `.110`, l.5437-5449)
- Modify: `scripts/generators/gen_nation_tab.py:164-165` (`"sr_resort_room_*"` beside `"sr_ebase_room_*"`), then rerun it
- Modify: `test_space_race_dividend.py:143-146` (the modifier's keys now include `building_space_resort_throughput_add`, equal to the base's line)
- Loc: `te_miscellaneous_l_english.yml` (`sr_resort_room_bonus`, `sr_resort_room_penalty`, `sr_resort_room_full_tt` beside l.6790-6792), `te_concepts_l_english.yml` (`sr_resort_room_bonus_desc`, `_penalty_desc` beside l.2752; `sr_commercial_space_dividend_desc` names both buildings), `te_buildings_l_english.yml` (`building_space_resort_throughput_add`, `_desc`)
- Test: `test_resort_colony.py` (class `ResortRefreshTest`)

**Interfaces:**
- Consumes: `sr_resort_fill`, `sr_resort_next_fill`, `sr_resort_room_total`, `sr_resort_levels`, `sr_resort_queued_levels` (Task 1).
- Produces: `sr_resort_refresh`, `sr_resort_hook_fire`, `var:sr_resort_draw`, `var:sr_resort_units`, `var:sr_resort_next_draw`, `sr_resort_has_room`, `sr_resort_may_build_government`, `sr_resort_may_build_private`, `sr_resort_room_bonus`, `sr_resort_room_penalty`, `building_space_resort_throughput_add`, `space_race_events.112`.

- [ ] **Step 1: Write the failing tests:**
  - `test_refresh_removes_first_and_averages`: in `sr_resort_refresh`, both `remove_modifier` lines come before any `add_modifier`, `sr_colonies_contested_enabled = yes` comes after both removals, and the block calls `sr_resort_fill = yes` and `sr_resort_next_fill = yes` and divides `local_var:sr_rs_sum` by the levels.
  - `test_modifier_pair`: `sr_resort_room_bonus` has `building_space_resort_throughput_add = 0.01` and `_penalty` has `-0.01`; the type is defined in `mod_entity_modifier_types.txt`.
  - `test_gates`: `sr_resort_has_room` has `NOT = { sr_colonies_contested_enabled = yes }` and `sr_resort_queued_levels < sr_resort_room_total`; `_government` has `is_ai = no`; `_private` has no `is_ai`.
  - `test_monthly_and_hook`: `space_race_on_actions.txt` calls `sr_resort_refresh = yes` under `has_technology_researched = space_colonization`; both on-actions in `extra_on_actions.txt` call `sr_resort_hook_fire = yes` for `is_building_type = building_space_resort`. `sr_resort_hook_fire` sets `sr_resort_hook_pending` with `days = 2` only when unset and fires `space_race_events.112` with `days = 1`. The event is hidden, removes the marker and calls `sr_resort_refresh`.
  - `test_carry_over_lines`: `sr_commercial_space_dividend`, `te_orbital_debris` and `pm_spaceport` each carry `building_space_resort_throughput_add` equal to their `building_space_mine_throughput_add`.
  - `test_no_mining_bonus_reaches_the_resort`: no `sr_colony_*`, `sr_discovery_*`, `sr_mars_robotic_precursor` or `sr_extraplanetary_commercial` modifier names `building_space_resort_throughput_add`.

- [ ] **Step 2: Run; they fail.**

- [ ] **Step 3: Implement** each as the twin of its base counterpart (spec § 6.3, § 6.4, § 8).
  - The event's `trigger` is `has_technology_researched = space_colonization`, with a `# REVIEWED 2026-11-21 (delayed_trigger):` comment in the words of `.110`'s.
  - `sr_resort_room_full_tt` says the levels, built and queued, are within our room: 10 in Earth orbit and each colony's.
  - Update `test_space_race_dividend.py`'s `test_modifier_only_pays_throughput` to the two keys plus `icon`, and assert that the two values are equal.

- [ ] **Step 4: Pass.** Run `$PY scripts/generators/gen_nation_tab.py`, then `$PY -m pytest test_resort_colony.py test_space_race_dividend.py test_nation_tab.py test_solar_sites.py test_orbital_debris.py -q`, then `$PY scripts/run_audits.py --strict` (or `scripts/preflight.py --quick`). Expected: pass; no new `modifier_field_audit`, `delayed_event_trigger_audit`, `loc_coverage_audit` or `script_argument_audit` finding.

- [ ] **Step 5: Commit**: "Resort Colony room: the refresh, its modifiers, gates and hook (#1948)".

### Task 4: The Off-World Resort module as the room's hook

**Files:**
- Modify: `scripts/generators/gen_solar_sites.py` (`FACILITIES` l.290: `Facility("resort", ..., True, False)`; `render_module_triggers()` l.2506-2517: for `t == "resort"` add `has_technology_researched = space_colonization`; `_module_ai()` l.2153-2159: `("resort", "sr_resort_queued_levels >= sr_resort_room_total")` after `"mine"`), then rerun it
- Generated (rerun): `common/journal_entries/sr_sites_generated.txt` (the `sr_module_resort` declaration goes), `common/scripted_triggers/sr_sites_generated.txt`, `common/scripted_effects/sr_sites_generated.txt`
- Modify: `common/static_modifiers/space_race_modifiers.txt:283-286` (delete `sr_module_resort`)
- Modify: `common/scripted_guis/sr_colony_sguis.txt:268-284` (an `scope:op = 10` `trigger_if` with `custom_tooltip = { text = sr_mod_req_resort_tech_tt has_technology_researched = space_colonization }`)
- Loc: delete `sr_module_resort` and `sr_module_resort_desc` (`te_concepts_l_english.yml:2809-2810`). Rewrite `je_space_race_widget_mod_resort_tt` (`te_journal_entries_l_english.yml:1742`) and `sr_mod_queue_resort_tt` (`te_miscellaneous_l_english.yml:6936`) to "+10 Resort Colony room at the colony a staffed level". Add `sr_mod_req_resort_tech_tt:0 "We have [GetTechnology('space_colonization').GetName]"` beside `sr_mod_req_terra_tech_tt` (l.6949).
- i18n: drop the removed keys' rows from `i18n/{german,spanish,russian}/tm/te_concepts.json`, as `i18n/README.md` says for removed keys.
- Test: `test_resort_colony.py` (class `ResortModuleTest`)

**Interfaces:**
- Consumes: `sr_resort_queued_levels`, `sr_resort_room_total` (Task 1), `sr_site_resort_staffed_<key>` (already generated).

- [ ] **Step 1: Write the failing tests:**
  - `test_facility_is_a_hook`: `gss.FACILITY["resort"].modifier is False` and `.ships is True`; the generated entry file has no `sr_module_resort`; `space_race_modifiers.txt` has no `sr_module_resort =`.
  - `test_queue_needs_the_technology`: every `sr_mod_can_queue_resort_<k>` block holds `has_technology_researched = space_colonization`, and no other facility's does.
  - `test_reason_line`: `sr_colony_sguis.txt` has `scope:op = 10` with `sr_mod_req_resort_tech_tt`, and the loc key exists.
  - `test_ai_plans_a_resort_when_room_is_full`: every `sr_mod_ai_plan_<k>` holds `sr_resort_queued_levels >= sr_resort_room_total` within the branch that queues `resort`, after the `mine` branch.
  - `test_no_three_percent_text`: neither rewritten loc key contains `+3%`.

- [ ] **Step 2: Run; they fail.**

- [ ] **Step 3: Implement** as listed under Files. Rerun `$PY scripts/generators/gen_solar_sites.py`.

- [ ] **Step 4: Pass.** `$PY -m pytest test_resort_colony.py test_solar_sites.py test_space_race_labels.py test_nation_tab.py -q`, plus `$PY organize_loc.py --check` and `$PY scripts/run_audits.py --strict`.

- [ ] **Step 5: Commit**: "Off-World Resort: room for Resort Colony levels, with Space Colonization (#1948)".

### Task 5: What the player sees

**Files:**
- Modify: `common/script_values/space_race_display_values.txt` (after `sr_disp_ebase_shown` l.1360: the twins `sr_disp_resort_levels`, `_room`, `_draw`, `_queued`, `_next_draw` with the live `-75` past the room, `_past`, `_total`, `_split`, `_shown` on `space_colonization`)
- Modify: `gui/journal_entry_widgets/space_race_widget.gui`:
  - the overview row at ~9598-9660: a Resort Room `te_banking_ov_cell` after Base Room's; the row's `visible` ORs in `sr_disp_resort_shown`; its icon is `building_tourism_industry.dds` until the building's own icon exists;
  - the Modules view summary at ~3898-3920: two rows, twins of the base's, using `je_space_race_widget_resort_*`;
  - the colony row at ~1775-1817: a "Resorts" widget beside "Bases", with blocks `module_resorts_tooltip`, `module_resorts` and `module_draw`. If the row has no width left, put the figures in the colony page's tiles only (~2436-2457) and say so in the PR;
  - the colony page at ~2436-2457: a Resort Room tile;
  - the Solar System line at ~4400-4420: a second icon and textbox with block `site_resorts`.
- Modify: `scripts/generators/gen_solar_sites.py` (`render_gui()` overrides beside `module_bases` ~l.4013-4018 and `site_bases` l.3960: `module_resorts` = `[sr_disp_site_resort_room_<k>|0]`, `module_draw` = `({_signed(draw)}%)`, `module_resorts_tooltip` = `tooltip = "je_space_race_widget_resorts_tt"`, `site_resorts` = `#v <resort_room>#! (<draw>%)`), then rerun it
- Modify: `common/game_concepts/extra_concepts.txt:109` (`concept_sr_resort_draw = {}` after `concept_sr_base_grade`)
- Loc: `te_journal_entries_l_english.yml` (`je_space_race_widget_ovc_resort_cap` "Resort Room", `_fig`, `_fig_plus`, `_tt`, `_word`, `_word_past`, `_word_split`, `_word_split_past`; `je_space_race_widget_resort_label` "Resort Colony levels / room", `_figure`, `_queued_label`, `_queued_figure`, `_tt`; `je_space_race_widget_modules_col_resorts` "Resorts"; `je_space_race_widget_page_resorts` "Resort Room"; `je_space_race_widget_resorts_tt`), `te_miscellaneous_l_english.yml` (`concept_sr_resort_draw:0 "Resort Draw"`), `te_concepts_l_english.yml` (`concept_sr_resort_draw_desc`). Each is the twin of its `ebase` key, in `docs/guides/loc_style_guide.md`'s style.
- Test: `test_resort_colony.py` (class `ResortPanelTest`)

- [ ] **Step 1: Write the failing tests:**
  - `test_display_values`: the nine `sr_disp_resort_*` values exist. `sr_disp_resort_next_draw` sets `-75` when `sr_resort_queued_levels >= sr_resort_room_total`, and `sr_disp_resort_shown` reads `space_colonization`.
  - `test_overview_cell`: the widget holds a `te_banking_ov_cell` with `tooltip = "je_space_race_widget_ovc_resort_tt"`, and the row's `visible` names `sr_disp_resort_shown`.
  - `test_generated_overrides`: for every site, the generated rows file has `module_resorts`, `module_draw` with the signed draw, and `site_resorts`.
  - `test_concept`: `concept_sr_resort_draw` is defined and has both loc keys.

- [ ] **Step 2: Run; they fail.**

- [ ] **Step 3: Implement.** Mirror the base's markup. Keep `gui_style_guide.md`'s widths and the `te_sr_fontsize_row` style. Every new `.gui` loc key must exist.

- [ ] **Step 4: Pass.** `$PY -m pytest test_resort_colony.py test_solar_sites.py test_space_race_labels.py -q`, `$PY scripts/analysis/check_gui_lint.py`, `$PY gui_reference_audit.py --strict`, `$PY organize_loc.py --check`.

- [ ] **Step 5: Commit**: "Resort Colony room in the space race panel (#1948)".

### Task 6: The guide, the docs, the snapshot and the gate

**Files:**
- Modify: `docs/player_guide/02-timeline.md:336-348`: drop the Resort Colony from the base's paragraph, and give the Resort Colony a sentence of its own after it (Space Colonization, room, draw, pointer to 16).
- Modify: `docs/player_guide/16-space.md`:
  - l.225: an overview row for Resort Room;
  - l.253: the Modules view adds resort room and draw;
  - l.757: the Off-World Resort row becomes "+10 Resort Colony room at the colony (needs Space Colonization)";
  - l.790: Solar System gives resort room and draw;
  - after the Extraplanetary Base room section (l.886-905): a "Resort Colony room" subsection with the tiers, the −75%, Resort Draw as a hover term, and a short table of draws grouped as the base grade table is.
- Rebuild: `$PY scripts/build_player_guide.py`; commit the PDF with the chapters.
- Modify: `docs/systems/mod_systems/space_race.md` (the Colony modules section: the Off-World Resort in the facility list as a hook; a "Resort Colony room" bullet after "Extraplanetary Base room"), `docs/testing/solar-colonies-playtest.md` (spec § 12's four items), and the spec (§ 6.1/6.2: "a `RESORTS` table read through `Site` properties" in place of "a column in `SITES`").
- Regenerate: `$PY scripts/snapshot_balance.py` (`docs/data/balance_snapshot.json`), and any generator a check names (for example `te_cred_monopoly_ladder_generated.txt`'s).

- [ ] **Step 1: Write the guide and docs edits.** Then run `$PY scripts/build_player_guide.py` and the guide's lint (`docs/player_guide/STYLE.md` names it).
- [ ] **Step 2: Run the gate.** `$PY scripts/preflight.py --changed`, then `$PY scripts/preflight.py --quick`. Expected: green; read and fix any failure.
- [ ] **Step 3: Commit** the guide, PDF, docs, snapshot and regenerated files: "Resort Colony: player guide, docs and play-test list (#1948)".

### Task 7: The icon, the review, the PR and the follow-ups

- [ ] **Step 1: The icon.** Make candidates with the off-repo tooling (`reference_icon_offrepo_tools.md`: `~/flux_runs/tools`; check `nvidia-smi` first). Send the owner a review sheet with my pick in a gold box. Commit the pick as `gfx/interface/icons/building_icons/building_space_resort.dds` and point the building and the overview cell at it. If the GPU is busy, ship the Tourism Industry icon and say so in the PR.
- [ ] **Step 2: Whole-branch review**, in two parts (script, then docs and GUI), by fresh reviewers. Verify each finding before fixing it.
- [ ] **Step 3: Open the PR** against `main`, while the review runs. The body says:
  - `Closes #1948`;
  - a Player guide line naming 02 and 16;
  - an "Intended balance" section: £42,000 a level, the draws, the room, the Earth-orbit 10;
  - the ground-types overlap, and which files merge by hand.
- [ ] **Step 4: File the follow-ups:**
  - merging the two room fills once both PRs are in (owner's call 5);
  - the dormant Mining Complex AI line (`sr_ebase_levels > sr_ebase_room_total`);
  - the Airport's tourism bonus against the draw (spec § 8).
  Give each its evidence. Labels: `enhancement`, plus `tooling` where it applies.
