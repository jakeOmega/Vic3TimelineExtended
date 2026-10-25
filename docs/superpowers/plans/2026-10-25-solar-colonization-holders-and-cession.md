# Solar Colonization Holders and Cession Implementation Plan

> **For agentic workers:** steps use checkbox (`- [ ]`) syntax for tracking. Do the tasks in order; each ends green and committed.

**Goal:** Slices 0 and 1 of the solar colonization scope. Every world gets a holder record that the holder's variables and journal entry mirror; a dead holder's colonies pass to whoever owns its last capital; the panel lists the solar system; the Space Race rule gets four settings; and under simple and full colonies, the Cede Colony treaty article moves a named colony by sale, gift or war.

**Architecture:** One site table in `scripts/generators/gen_solar_sites.py` (a post-load regenerator) writes every per-site block: the founding draw, the sync, transfer, release, migration, the choice dispatcher, the dead-holder step, Cede Colony's filter and apply, the panel snapshot, 34 hidden site building types and a custom loc. Hand-written files hold what is not per site: the monthly global step's wiring, the heir choice, the rule gates, the article, the notices, the console. The global record (`sr_site_holder_<key>`, `sr_site_spec_<key>`, …) is the truth; `<modifier>_held` and the entry modifiers are its projection.

**Tech stack:** Paradox script (`common/`, `events/`), Victoria 3 GUI, localization YAML, Python 3.11/3.12 `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-25-solar-colonization-holders-and-cession-design.md`. Scope: `docs/superpowers/specs/2026-10-25-solar-colonization-contest-scope.md`.

## Global constraints

- **Never hand-edit a generated file.** Change `gen_solar_sites.py` and run `python3 scripts/generators/gen_solar_sites.py`; `test_solar_sites.py` fails on a stale output.
- **Every global variable read is guarded**: `global_var:x ?=` or `has_global_variable = x` first. `test_launch_windows.py`'s `test_global_variable_reads_are_guarded` already enforces this for the draw; `test_solar_sites.py` extends it to every generated file.
- **Every `remove_modifier` sits behind its `has_modifier`** (`test_the_monthly_sync_removes_only_what_is_there`), and every stored country is guarded with `exists` and `is_country_alive` before use.
- **Files.** One UTF-8 BOM on every brace-based `.txt` and `.gui` (the generator writes it; new hand-written files need it). Tabs for indentation; `python3 scripts/format_paradox_tabs.py --check` on every changed `.txt`. Three docs are CRLF here: `journal_entry_systems.md`, `treaty_articles_reference.md`, `gui_modding_guide.md`: edit with `Edit` or bytes, then confirm `grep -c $'\r$'` equals `wc -l`.
- **Loc**: new keys in the existing files (`te_journal_entries_l_english.yml` for the panel, `te_events_l_english.yml` for events, `te_game_rules_l_english.yml` for the rule, a treaty articles file for the article and the site building types), then `python3 organize_loc.py` and commit whatever it moves. A literal `"` inside a value is `\"`.
- **Python runs on 3.11 in CI**: no PEP 701 f-strings (`grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>`).
- **Tests** need `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent` without a game. Use `.venv/bin/python`; read results with `grep -E '^(Ran |OK|FAILED)'`.
- **Per task**: its tests, `ruff check .`, the tab check, and the audits named in the task. Task 10 runs everything CI runs.
- **No behaviour change under races only beyond the design's**: the dead-holder rule, released worlds, the Solar System list, the widened entry conditions.

## Review focus

1. **The projection can't drift.** The sync removes a site from its old mirror before it adds it to the new holder, recounts both, and runs monthly for all 34 sites (Task 2).
2. **Under races only, founding is unchanged** apart from the holder write and the released worlds' branches (Task 1's byte-equivalence step, then Task 2's and 3's diffs of the generator).
3. **No bare `has_game_rule = space_race_enabled` survives outside `sr_space_race_on`** (Task 7's test).
4. **Cede Colony moves only a colony the source still holds**, whichever input the AI picked (Task 8's filter and apply).
5. **The owner's calls in the design's § 16.**

## Files

| File | Task | What |
|---|---|---|
| `scripts/generators/gen_solar_sites.py` | 1–8 | Create: the site table and every per-site output |
| `common/scripted_effects/sr_sites_generated.txt` | 1–8 | Generated |
| `common/scripted_triggers/sr_sites_generated.txt` | 2–8 | Generated |
| `common/script_values/sr_sites_generated.txt` | 2–8 | Generated |
| `common/buildings/sr_site_buildings_generated.txt` | 8 | Generated |
| `common/customizable_localization/sr_sites_generated_custom_loc.txt` | 4 | Generated |
| `common/scripted_effects/space_race_effects.txt` | 1, 2, 4 | The draw and stage check move out; `sr_grant_colony_modifier` dispatches; `sr_repair_after_civil_war` repoints |
| `common/scripted_effects/space_race_discovery_effects.txt` | 2 | The pending flag goes global too |
| `common/scripted_effects/sr_site_effects.txt` | 2–8 | Create: the monthly step's body, heir choice, notices, transfer base |
| `common/scripted_triggers/sr_site_triggers.txt` | 2, 4, 7 | Create: `sr_site_can_hold`, the rule gates |
| `common/scripted_triggers/space_race_triggers.txt` | 3 | `sr_solar_colonization_qualified`, joined to `sr_solar_colonization_running` |
| `common/on_actions/sr_sites_on_actions.txt` | 2 | Create: the global monthly step |
| `common/on_actions/space_race_on_actions.txt` | 2 | The country pulse's gate widens |
| `common/journal_entries/je_space_race.txt` | 3 | The entry's conditions; `on_fail`'s report |
| `gui/journal_entry_widgets/space_race_widget.gui` | 5 | The Solar System section |
| `common/game_rules/extra_game_rules.txt` | 7 | Four settings |
| 22 files with `has_game_rule = space_race_enabled` | 7 | → `sr_space_race_on = yes` |
| `common/building_groups/sr_site_groups.txt` | 8 | Create: `bg_sr_colony_sites` |
| `common/treaty_articles/123_cede_colony.txt` | 8 | Create: `te_cede_colony` |
| `events/space_race_events.txt` | 4, 8 | `.91`, `.90` |
| `events/te_debug_space_race_events.txt` | 6 | `te_debug_space_race.2` |
| `test_solar_sites.py` | 1–8 | Create |
| `test_launch_windows.py` | 1, 3 | Reads the draw from the generated file; the stage test admits earlier stages |
| `mod_state_server.py` | 1 | `gen_solar_sites` in `POST_LOAD_REGENERATORS`, after `gen_launch_windows` |
| `CLAUDE.md`, `docs/guides/python_tools.md`, `docs/auto_generated_files.md`, `scripts/nightly_audit_select.py` | 1 | The new regenerator and its outputs |
| `docs/testing/solar-colonies-playtest.md` | 6 | Create |
| docs and the player guide | 9 | See Task 9 |

## Task 1: The site table, and the draw reproduced

- [ ] **1.1** Read the 34 sites out of today's script with a one-off script (not committed): from `sr_establish_colony_effect` each site's key, stage, `BODY` and `DISCOVERY` (if any) and event id; from `events/space_race_colony_events.txt` each event's two `sr_grant_colony_modifier` modifiers in option order and its image; from `space_race_discovery_effects.txt` each discovery's event and its `_a` / `_b` outcomes. Add the location (the owner's nine) and the icon kind (the `colony_<kind>.dds` each Our Colonies row uses) by hand. Write `SITES` and `DISCOVERIES` into `gen_solar_sites.py` as literal tuples.
- [ ] **1.2** Write the generator on `gen_launch_windows.py`'s pattern: `HEADER`, one BOM, `--dry-run` and `--check`, a `main()` the server calls, outputs written only when they change. Its only output for now: `common/scripted_effects/sr_sites_generated.txt` with `sr_establish_colony_effect` and `sr_check_colony_stage_effect`, emitted from the table.
- [ ] **1.3** Delete the two effects from `space_race_effects.txt`, leaving a comment where they were that names the generated file. Confirm the generated bodies equal the deleted ones apart from indentation of the header comment (diff them).
- [ ] **1.4** `test_launch_windows.py`: read `sr_establish_colony_effect` from the generated file.
- [ ] **1.5** `test_solar_sites.py`: generated files current, one BOM and the header; the table matches the colony events, `gen_launch_windows.BODIES` and the discovery seeds (re-derived from the files, as 1.1 did).
- [ ] **1.6** Register `gen_solar_sites` in `POST_LOAD_REGENERATORS` after `gen_launch_windows`; add it to `CLAUDE.md`'s regenerator list (and its count of regenerators), `python_tools.md`'s table, `auto_generated_files.md`, and classify the output paths in `scripts/nightly_audit_select.py` (`EXCLUDED_REGISTRY_GLOBS`). Run `python3 scripts/analysis/check_post_load_rosters.py` and `test_nightly_audit_select.py`.
- [ ] **1.7** Tests: `test_solar_sites.py`, `test_launch_windows.py`, `test_space_race_*.py`, `test_nightly_audit_select.py`, `test_reload_post_load.py` (skips without a server). Commit: "Solar sites: one table generates the colony draw".

## Task 2: The record, the dispatcher and the sync

- [ ] **2.1** Generator, the draw: after each site's `set_global_variable = { name = sr_colony_<key> value = yes }`, add `set_global_variable = { name = sr_site_holder_<key> value = root }` and `sr_site_sync_<key> = yes`.
- [ ] **2.2** Generator, the dispatcher: for each of the 68 specializations, `sr_site_choose_<modifier> = { set_global_variable = { name = sr_site_spec_<key> value = 1|2 } sr_site_sync_<key> = yes }`; for each of the 40 discovery outcomes, `sr_site_choose_<modifier> = { set_global_variable = { name = sr_site_disc_<d> value = 1|2 } if has_global_variable sr_site_disc_<d>_pending → remove_global_variable … sr_site_sync_<key> = yes }`.
- [ ] **2.3** `sr_grant_colony_modifier` (`space_race_effects.txt:1829`) gains `sr_site_choose_$MODIFIER$ = yes` after its two lines. `script_argument_audit --strict` must stay clean (the dispatcher takes no arguments).
- [ ] **2.4** `sr_seed_colony_discovery` sets `sr_site_disc_$DISCOVERY$_pending` (global) beside the country's pending flag; `sr_finish_colony_discovery` removes it if set.
- [ ] **2.5** Generator, the sync, per site (design § 4):

  ```
  sr_site_sync_<key> = {
  	# 1. The old mirror loses the site.
  	if = {
  		limit = {
  			has_global_variable = sr_site_mirror_<key>
  			NOT = { global_var:sr_site_mirror_<key> ?= global_var:sr_site_holder_<key> }
  		}
  		global_var:sr_site_mirror_<key> ?= {
  			if = {
  				limit = { is_country_alive = yes }
  				sr_site_unmirror_<key> = yes
  				set_variable = { name = sr_colony_count value = sr_sites_held_count }
  			}
  		}
  		remove_global_variable = sr_site_mirror_<key>
  	}
  	# 2. The holder gains it.
  	if = {
  		limit = { global_var:sr_site_holder_<key> ?= { is_country_alive = yes } }
  		global_var:sr_site_holder_<key> = {
  			sr_site_mirror_on_<key> = yes
  			set_variable = { name = sr_colony_count value = sr_sites_held_count }
  		}
  		set_global_variable = { name = sr_site_mirror_<key> value = global_var:sr_site_holder_<key> }
  	}
  }
  ```

  `sr_site_unmirror_<key>` / `sr_site_mirror_on_<key>` (country scope) write and remove the `_held` variables, `sr_discovery_<d>_done` and `_pending`, and the entry modifiers behind `je:je_space_race_solar_colonization ?=` and `has_modifier`.
- [ ] **2.6** Generator, `common/script_values/sr_sites_generated.txt`: `sr_sites_held_count` (country scope, one `if = { limit = { global_var:sr_site_holder_<key> ?= this } add = 1 }` per site).
- [ ] **2.7** `sr_site_effects.txt`: `sr_sites_global_monthly` (no ROOT) calls the generated `sr_sites_monthly`, which for now syncs all 34. `sr_sites_on_actions.txt`: `on_monthly_pulse = { on_actions = { sr_sites_on_action } }`, `sr_sites_on_action` gated on the space race (today `has_game_rule = space_race_enabled`; Task 7 swaps the gate).
- [ ] **2.8** `space_race_on_actions.txt`: the sync gate becomes `OR = { sr_space_race_participant = yes sr_has_space_colony = yes }`.
- [ ] **2.9** Tests: every site has a sync, mirror and unmirror naming exactly its modifiers and discoveries; every modifier `sr_grant_colony_modifier` receives has a dispatcher; the draw writes the holder after the claim; every `remove_modifier` and `remove_variable` in the generated files is behind its test. Audits: `script_argument_audit`, `empty_effect_audit`, `silent_variable_audit` (a hidden write is fine; the dispatcher runs inside options that already show the modifier), `container_timed_variable_audit`, `prev_scope_audit`, `duplicate_key_audit`, all `--strict`. Commit: "Solar sites: a holder record the colony modifiers mirror".

## Task 3: Old saves, released worlds and the entry

- [ ] **3.1** Generator: `sr_sites_migrate_country` (country scope): for each of the 108 modifiers, `if = { limit = { has_variable = <m>_held } sr_site_choose_<m> = yes }`, and for a specialization also set the holder to ROOT when the site has none; for each discovery, `sr_discovery_<d>_pending` → the global pending flag.
- [ ] **3.2** `sr_sites_global_monthly`: on the first run (`NOT = { has_global_variable = sr_sites_initialized }`), `every_country = { limit = { sr_has_space_colony = yes } sr_sites_migrate_country = yes }`, then `sr_sites_initialized` and `sr_sites_grace` (`days = 45`).
- [ ] **3.3** Generator: `sr_site_adopt_or_release_<key>` in the monthly step: a claimed site with no holder adopts a living country carrying either specialization's `_held` (`random_country` with that limit); once `sr_sites_grace` is gone, a claimed site still without holder or carrier is released (`sr_site_release_<key>`: remove claim, holder and mirror after unmirroring, log `TE_SR_SITES released <key>`).
- [ ] **3.4** Generator, the draw: each stage's `random_list` also lists every earlier stage's worlds, each with its own claim test and window trigger. `sr_any_site_unclaimed` (generated trigger: any `NOT = { has_global_variable = sr_colony_<key> }`).
- [ ] **3.5** `space_race_triggers.txt`: `sr_solar_colonization_qualified = { has_variable = sr_completed_moon_base has_variable = sr_completed_mars_landing }`, added to `sr_solar_colonization_running`.
- [ ] **3.6** `je_space_race.txt`, the entry (design § 8): `is_shown_when_inactive` and `possible` gain the colony branch; the colonizing branch takes the two milestones and `sr_any_site_unclaimed`; the monthly pulse's progress branch adds `sr_solar_colonization_qualified = yes`; `on_fail` calls `sr_report_program_loss` only if qualified.
- [ ] **3.7** Tests: `test_launch_windows.py`'s `test_each_stage_holds_its_bodies_sites` admits earlier stages' worlds (and still requires each stage's own); `test_solar_sites.py` checks the migration names all 108 modifiers and the entry's two branches; `test_space_race_civil_war.py` passes unchanged. Audits: `je_immediate_reset_audit`, `iterator_limit_audit`, `any_limit_audit`, `--strict`. Commit: "Solar sites: old saves migrate, released worlds rejoin the draw".

## Task 4: The dead holder and revolutions

- [ ] **4.1** `sr_site_triggers.txt`: `sr_site_can_hold = { is_country_alive = yes NOT = { is_country_type = decentralized } }`.
- [ ] **4.2** Generator, the monthly step per site: record the capital (`global_var:sr_site_holder_<key> ?= { if = { limit = { is_country_alive = yes exists = capital } … set_global_variable = { name = sr_site_region_<key> value = capital.state_region } } }`, as nuclear custody records `nd_ar_capital_region`); then the dead-holder branch: holder set and not alive → `sr_site_choose_heir = { … }` saves `scope:sr_site_heir` from `s:` region's `ordered_scope_state` (`order_by = state_population`, `limit = { owner = { sr_site_can_hold = yes } }`), then transfer (`sr_site_transfer_<key>`) or release. The first such case logs `TE_SELF_CHECK OK site_dead_holder` with which guard caught it; a dead holder still on the site a month later logs BROKEN.
- [ ] **4.3** Generator, `sr_site_transfer_<key>` (any scope, reads `scope:sr_site_new_holder` and optional `scope:sr_site_old_holder`): repoint, sync, `add_journal_entry` for a new holder without the entry, set `sr_site_notice_index` and fire the right notice for players, mark the receiver for the `site_receiver_entry` check (Task 6), refresh players' snapshots.
- [ ] **4.4** Generator, the custom loc: `sr_site_notice_name` with one `text` per site (`trigger = { var:sr_site_notice_index = N }`, `localization_key = sr_site_name_<key>`). Loc: `sr_site_name_<key>` for the 34 worlds.
- [ ] **4.5** `events/space_race_events.txt`: `.91` (design § 12), players only, one option, the Valles Marineris image.
- [ ] **4.6** `space_race_effects.txt`, `sr_repair_after_civil_war`: `sr_sites_repoint_loser = yes` (generated: for each site, if the rebels won and `global_var:sr_site_holder_<key> ?= scope:te_cw_loser`, the holder becomes ROOT and the site syncs).
- [ ] **4.7** Tests: every site has the capital record, the dead-holder branch and the repoint; the heir trigger excludes decentralized countries; `.91` has an image and loc. Audits: `event_image_audit`, `event_context_audit`, `loc_coverage_audit`, `orphaned_event_audit`, `--strict`. Commit: "Solar sites: a dead holder's colonies pass to its capital's owner".

## Task 5: The Solar System section

- [ ] **5.1** Generator: `sr_sites_refresh_snapshot` (country scope): per site, `sr_ss_cap_<key>` = the holder's capital state when the holder has one, removed otherwise; `sr_disp_site_<key>` (0 unclaimed, 1 ours, 2 another's with a capital, 3 another's without).
- [ ] **5.2** Call it monthly for players from `sr_sites_global_monthly` (`every_country = { limit = { is_player = yes } … }`) and from each transfer.
- [ ] **5.3** `space_race_widget.gui`: the section after Our Colonies (design § 9): header with `sr_panel_solar_system_closed`, nine location subheadings, 34 rows written by a one-off script from the table (not committed), each row's outer `visible` on `sr_disp_site_<key>` and inner `datacontext` on `sr_ss_cap_<key>`. Closed by default: the flag's sense is "open" (`sr_panel_solar_system_open`), so a fresh client shows it closed.
- [ ] **5.4** Loc: the header, the nine subheadings, "Ours", "Unclaimed", "Another power", the row name keys (`sr_site_name_<key>` from Task 4).
- [ ] **5.5** `python3 scripts/analysis/check_gui_lint.py` (no errors), `gui_reference_audit --strict`, `loc_render_audit --strict`. Test: the 34 rows match the table, in location order. Commit: "Solar sites: the panel lists the solar system".

## Task 6: The console, self-checks and the play-test list

- [ ] **6.1** `te_debug_space_race.2` (design § 13): six options, each a call to an existing or generated effect, with `TE_SR_SITES` log lines for the record dump.
- [ ] **6.2** The `site_receiver_entry` check: a transfer to a country that isn't `sr_solar_colonization_qualified` sets `sr_site_receiver_check` (`days = 70`) on it; the monthly country pulse, when it finds the timer's last month, logs OK if `has_journal_entry = je_space_race_solar_colonization` and the site's specialization modifier is on it, BROKEN otherwise. Once a game (`sr_site_receiver_checked` global).
- [ ] **6.3** `docs/testing/solar-colonies-playtest.md`: the Self-checks table (`site_dead_holder`, `site_receiver_entry`, `cede_colony_input`), each with its fallback, and the visual checks of the design's § 13.
- [ ] **6.4** Audits: `orphaned_event_audit` (the console event carries the review comment the other debug events do), `event_image_audit`. Commit: "Solar sites: console, self-checks, play-test list".

## Task 7: Four settings of the Space Race rule

- [ ] **7.1** `extra_game_rules.txt`: `space_race_colonies_full`, `space_race_colonies_simple`, `space_race_enabled`, `space_race_disabled` (that order on the setup screen), one flag each named after the setting; the off setting keeps its PM flags; `default = space_race_enabled`.
- [ ] **7.2** `sr_site_triggers.txt`: `sr_space_race_on` (`OR` of the three), `sr_colonies_contested_enabled` (simple or full), `sr_colonies_full_enabled`.
- [ ] **7.3** Replace every `has_game_rule = space_race_enabled` outside the gate with `sr_space_race_on = yes` (a sed over the 22 files; re-read each diff: a `NOT = { has_game_rule = space_race_enabled }` becomes `NOT = { sr_space_race_on = yes }`). Check `.gui` files too.
- [ ] **7.4** Loc: the two new settings' names and descriptions; Races Only's name and description replace "Enabled"'s; each description says what the setting adds.
- [ ] **7.5** Test: no `has_game_rule = space_race_enabled` anywhere but `sr_space_race_on`; the four settings, the default and the kept name. Run the whole suite here: the rule is read in 22 files. Commit: "Space Race rule: off, races only, simple and full colonies".

## Task 8: Cede Colony

- [ ] **8.1** `common/building_groups/sr_site_groups.txt`: `bg_sr_colony_sites`, shown nowhere (copy the fields of an existing hidden group; `is_shown_in_outliner = no`).
- [ ] **8.2** Generator, `common/buildings/sr_site_buildings_generated.txt`: 34 `building_sr_site_<key>` (design § 11.1). If the engine requires a production method group, add one shared marker group and method in a hand-written file with no modifiers, and confirm `pm_employment_audit --strict` and `prestige_good_roster_audit --strict` pass (exempt them in the audits if needed, with the reason).
- [ ] **8.3** Generator: `sr_cede_site_input_valid` (trigger, `root` the source): `OR` over the sites of `AND = { scope:input = bt:building_sr_site_<key> global_var:sr_site_holder_<key> ?= root }`. `sr_cede_colony_apply` (effect): per site, if `scope:article_options.input_building_type ?= bt:building_sr_site_<key>` and the holder is still `scope:sr_cede_source`, save `scope:sr_site_new_holder`, transfer, set `sr_cede_matched`; after the sites, the `cede_colony_input` self-check (OK if matched, BROKEN if not). `sr_cede_ai_input_value` (value, `scope:article.input_building_type`): 20 + 5 × stage.
- [ ] **8.4** `common/treaty_articles/123_cede_colony.txt`: the article (design § 11.2), including the `ai` and `wargoal` blocks. `python3 treaty_evaluation_scope_audit.py --strict` and `python3 treaty_leverage_side_audit.py --strict`.
- [ ] **8.5** `events/space_race_events.txt`: `.90` (design § 12), with a triggered description for treaty and for peace (`sr_site_notice_cause`).
- [ ] **8.6** Loc: the article's name, description, effects description and short description; the 34 building types' names ("$sr_site_name_<key>$ Colony") and descriptions; the AI's score descriptions; `.90`.
- [ ] **8.7** Tests: the article's flags, usage limit, input and the filter's call; every site in the filter and the apply; the building types all `potential = { always = no }` with loc. Audits: `loc_coverage_audit`, `loc_render_audit`, `script_loc_reference_audit`, `duplicate_key_audit`, `--strict`. Commit: "Cede Colony: a treaty article that moves a named colony".

## Task 9: Docs and the player guide

- [ ] **9.1** `docs/systems/mod_systems.md` § Space Race: the site record and its projection, the monthly step, the dead-holder rule, released worlds, the rule's settings, Cede Colony; the variables table (`sr_site_*`).
- [ ] **9.2** `docs/systems/journal_entry_systems.md` (CRLF): the entry's new conditions and the Solar System section.
- [ ] **9.3** `docs/vanilla/treaty_articles_reference.md` (CRLF): Cede Colony, with the hidden building types as the engine constraint it rests on.
- [ ] **9.4** Player guide: `16-space.md` § Colonizing the solar system (who holds a colony, a holder that is annexed, released worlds, the Solar System list, Cede Colony under simple and full, the AI); `01-introduction.md` § Game rules (the Space Race rule's four settings; recount the rules if the count changes); `09-diplomacy.md` where it lists the mod's treaty articles. Match the depth of the text around it (`CLAUDE.md` § Keep the player guide current). `python3 scripts/analysis/check_player_guide_style.py --strict`, then `.venv/bin/python scripts/build_player_guide.py` (needs `requirements-docs.txt`) and commit chapter and PDF together; `scripts/build_player_guide.py --check`.
- [ ] **9.5** `docs/guides/scripting_best_practices.md`: one paragraph on the rule gate (why not a second flag), and one on hidden building types as a treaty input, marked unverified until the self-check reports.
- [ ] **9.6** `docs/superpowers/README.md`: the design's and plan's rows. Commit: "Solar sites: docs and player guide".

## Task 10: Verify, push, PR

- [ ] **10.1** Everything CI runs (`.github/workflows/ci.yml`), each step's exact command: `compileall`, the unittest suite, `ruff check .`, `format_paradox_tabs.py --check`, `check_localization_files.py`, `organize_loc.py --check`, `check_post_load_rosters.py`, the player guide's style lint and `--check`, the thirty audits in their exit-code mode, `check_gui_lint.py`.
- [ ] **10.2** Re-read the whole diff for: a global read without a guard; a stored country used without `is_country_alive`; a generated file edited by hand; a BOM missing or doubled; CRLF docs flipped.
- [ ] **10.3** Push `claude/solar-colonization-scope-cvx3t3` and open the PR against `main`: summary, the owner's calls (design § 16), the self-checks and play-test list, and the "Player guide" line naming the chapters updated.
