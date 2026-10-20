# Grand Monuments: size in records, construction sites, level-1 monuments — Implementation Plan A

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A monument's size lives in its records, a player builds a construction site and dedicates it, and every finished monument is a level-1 building that nothing rebuilds. World wealth is Plan B (`2026-10-18-grand-monument-sites-plan-b.md`); here every level counts one grandeur, so nothing a player sees changes in size.

**Architecture:** Two PRs. **A1** (Tasks 1-2) moves every size reader and writer to records while the building still stands full height, so the rebuilds that still run are harmless and nothing reads 1 when the building drops to level 1. **A2** (Tasks 3-10) adds the site type, makes the finished type level 1, migrates old saves, and deletes the rebuild, freeze, split-piece and level-arithmetic machinery; it can't be split, because once the building is level 1 the upkeep and merge arithmetic must be replaced in the same change. Structural work (create, remove, demote, swap, migrate) runs in hidden events, never in the refresh that tooltips walk.

**Tech Stack:** Paradox Clausewitz script (Victoria 3 1.14.5), `.gui`, customizable localization, Python `unittest` structural pins (`test_grand_monument_registry.py`, `test_grand_monument_trophies.py`, `test_grand_monuments_layout.py`, `test_grand_monument_archaeology.py`, plus `test_maintenance_tiers.py`, `test_te_systems_window.py`, `test_hidden_state_modifiers.py`).

**Spec:** `docs/superpowers/archive/specs/2026-10-18-grand-monument-sites-and-world-wealth-design.md`. **Code maps** (every name below with its file:line at 823dc25c): `docs/superpowers/archive/plans/2026-10-18-gm-sites-inventory/` — A (levels, rebuilds, freeze, building, seeding, `.1`), B (shadows, merges, split pieces, repair), C (grandeur readers, opportunities, vanity, upkeep, world GDP), D (GUI, tests, docs, engine facts). Read the one your task names before starting.

## Global Constraints

- **Finished type** `building_grand_monument` (key kept, so old saves' buildings are already it): `buildable = no`, `expandable = no`, `downsizeable = no`, no `unlocking_technologies`, keeps `possible` (the game rule) and both PM groups; always level 1. Script creates `buildable = no` buildings (vanilla's Manila cathedral ruins, inventory D §4).
- **The building group's per-level effects shrink** (my call, for the owner's check): `bg_grand_monuments` gives 10 urbanization and uses 1 infrastructure a level, so a level-1 finished monument gives one level's worth. Accepted; nothing restores them.
- **Site type** `building_grand_monument_site` (not `…_construction_site`: `te_construction_market_site` exists): one per state, `required_construction = construction_cost_grand_monument` (1000), `expandable = yes`, `downsizeable = yes`, group `bg_grand_monuments`, no upkeep, no dedication effects, no grandeur counted anywhere.
- **Records.** Primary, on the state: `gm_levels`, `gm_start_grandeur`, `gm_age`. Beside, on its container: `gm_tr_levels`, `gm_tr_start_grandeur`, `gm_tr_age`. Site, on the state: `gm_site_counted` (levels counted), `gm_site_grandeur` (starting grandeur so far). A missing start grandeur reads as the levels (old saves, trophies, digs).
- **Plan A's rate is 1:** every counted level adds 1 starting grandeur.
- **Grandeur** = starting grandeur + age. **Ageing** = starting grandeur × 2 ÷ 1200 a month (`multiply = 2 divide = 1200`), ×0.5 under Mothballed.
- **Levels count cost, grandeur counts meaning** (spec §3.6): Rededicate's money (500 × levels), upkeep and a site's construction read levels; effects, sums, IG nets, tourism, contests, anniversaries, trophy value and every taking share read grandeur.
- **Upkeep:** 0.1 construction a recorded level a week (today's `pm_maintenance`), ×1.5 Open, 0 Mothballed, ×1 otherwise; nothing under `pm_no_maintenance`. Never edit `pm_maintenance` (shared by ~74 types).
- **One method switch per building per tick.** An existing building changes method only by `activate_production_method`; never call `create_building` on a state that has the type (the engine keeps the larger level). A created finished building gets `activate_production_methods` and a `gm_restore_pm` fallback.
- **The refresh writes nothing structural.** `gm_country_refresh` and the state loops only trigger hidden events (`monument_events.29`, `.31`, and the new `.32`).
- A variable backing a `multiplier` is zeroed, never removed. No timed variable on a container. `gm_rebuilding` (one day) guards every `create_building` / `remove_building` of either type, so `.1` ignores it.
- Tabs in brace files; exactly one UTF-8 BOM; loc into existing `*_l_english.yml`, then `organize_loc.py`; Python 3.11-compatible tests; run the registry test with `python3 -m unittest test_grand_monument_registry`, never as a script (a mid-file `unittest.main()` skips half of it).
- The branch stacks on #1055 (`feat/gm-dedicate-button`); each PR is `--base main`. Every PR body carries a Player guide line.

## Review Focus

1. **Grandeur unchanged by the migration.** A save from before this plan: every state's `gm_state_grandeur`, the country's `gm_sum_standing` and each trophy's `gm_tr_grandeur` read the same after `.32` as before. Pinned in Task 6 (`MigrationTests.test_totals_survive`: the migration writes `gm_levels` from the old `building − secondaries` arithmetic before it removes the building, and logs both sums in `TE_SELF_CHECK monument_migrated`).
2. **Dedicating a site where a grander monument stands.** The Arc de Triomphe stays the state's monument, the new column stands beside it, and the building ends on the Arc's method with one switch a tick. Pinned in Task 4 (`SiteDedicationTests.test_beside_a_grander_one`: the answer demotes and sets `gm_newcomer`; the swap back runs only from `.29` after `gm_state_newcomer_settled`).
3. **An old undedicated monument with levels still queued.** Nothing removes it while `is_under_construction`; it becomes a site once construction stops, at its level. Pinned in Task 6 (`MigrationTests.test_waits_for_construction`).
4. **A finished building that vanishes with its records standing** (a nuclear strike, an unread engine path) is put back at level 1 on its dedication within a month; Pull Down and a whole taking clear the records first, so they are never put back. Pinned in Task 5 (`LostBuildingTests`).
5. **A tooltip walk never restructures.** No `create_building`, `remove_building`, `create_container`, `destroy_container`, `activate_production_method` or `gm_state_demote_primary` inside `gm_country_refresh` or anything it calls. Pinned in Task 10 (`WalkedRefreshTests.test_refresh_writes_nothing_structural`, a call-graph scan).

---

## PR A1: size lives in records

### Task 1: Records and the values that read them (no behaviour change)

**Files:** `common/script_values/gm_values.txt`, `gm_monument_values.txt`, `gm_trophy_values.txt`, `gm_commission_values.txt`; `common/scripted_effects/gm_effects.txt`, `gm_monument_effects.txt`, `gm_trophy_effects.txt`; tests: `test_grand_monument_registry.py` (`LevelsApartTests`, `AgeTests`, `AgeingTests`, `CONTAINER_RECORDS`), `test_grand_monument_trophies.py`. Map: inventory A §1, C §1.

**Interfaces — Produces** (all 0 when there is no monument):
- `gm_state_primary_levels` (state): `var:gm_levels` when set; else today's `gm_state_level − gm_state_secondary_levels`, min 1 (an undedicated monument, until Task 6 makes it a site).
- `gm_state_primary_start` (state): `var:gm_start_grandeur` when set, else `gm_state_primary_levels`.
- `gm_mon_start` (container): `var:gm_tr_start_grandeur` when set, else `gm_mon_levels`.
- `gm_state_primary_grandeur` = `gm_state_primary_start` + `gm_state_primary_age`; `gm_mon_grandeur` = `gm_mon_start` + `gm_mon_age`; `gm_state_grandeur` unchanged in shape.
- `gm_state_age_step` = `gm_state_primary_start` × 2 ÷ 1200 × `gm_policy_factor_age`; `gm_mon_age_step` = `gm_mon_start` × 2 ÷ 1200, ×0.5 Mothballed.
- `CONTAINER_RECORDS` gains `gm_levels → gm_tr_levels` and `gm_start_grandeur → gm_tr_start_grandeur`.

- [ ] Write `LevelsApartTests.test_only_named_readers_read_the_building`: across `common/` and `events/`, `gm_state_level` and `b:building_grand_monument.level` appear only in `gm_state_primary_levels`' undedicated branch, the rebuild bodies inventory A §2 lists (until Task 5 deletes them) and the debug event. Run it: FAIL.
- [ ] Write `AgeTests.test_ageing_reads_starting_grandeur` (both steps read `gm_state_primary_start` / `gm_mon_start`, never `_levels`) and `test_start_grandeur_falls_back_to_levels` (the two fallbacks above). FAIL.
- [ ] Repoint every reader inventory A §1 marks *changes*: trophy shares (`gm_state_tr_levels`, `_age`, `_value`, `_whole`, `_levels_left`, `gm_mon_tr_*`) carry a start-grandeur share alongside the level share (`gm_state_tr_start`, `gm_mon_tr_start` = start × levels taken ÷ levels); `gm_state_tr_value` = ceil((start taken + age taken) ÷ 2); `gm_state_rededicate_cost` reads `gm_state_primary_levels`; the ceremony level; the eight loc keys and `monument_trophy_events.1.d` (inventory A §1) read `gm_state_primary_levels` or the new start value as their sentence means.
- [ ] `gm_state_demote_primary`, `gm_state_raise_secondary`, `gm_tr_copy_from_state` and `gm_state_tr_take_records_from_moving` carry both new pairs (they iterate `CONTAINER_RECORDS`'s twins). `gm_clear_state` removes `gm_start_grandeur`.
- [ ] Run the four GM test files: OK. Commit.

### Task 2: Writers keep the records (rebuilds still run)

**Files:** `gm_effects.txt` (`gm_state_dedicate`, `gm_state_rededicate`), `gm_trophy_effects.txt` (taking, return, `gm_state_tr_receive`), `gm_monument_effects.txt` (promotion, Pull Down beside, swap), `gm_archaeology_effects.txt` (placing), `gm_landmark_effects.txt`, `gm_commission_effects.txt` (`gm_state_gift_grandeur`); tests `TakingTests`, `ReturnToAStateWithAMonumentTests`, `RededicateAgeTests`, `LandmarkTests`, archaeology `PlacingTests`. Map: inventory A §2, C §3.

**Interfaces — Consumes:** Task 1's values and record names.

- [ ] Write `RecordWriterTests`, one test each: dedication writes `gm_start_grandeur` = `gm_levels`; a piece taken subtracts its level, start and age shares from the primary's records (or the container's); a return adds them back (beside: kept on its container); Rededicate halves `gm_levels` (rounded up), `gm_start_grandeur` and `gm_age`; promotion moves the container's three records onto the state; a dig placed or a trophy home writes `gm_tr_start_grandeur` / `gm_start_grandeur` = its levels (spec §3.6: 1836 rate); a landmark writes `gm_levels` = `gm_start_grandeur` = `$LEVEL$`. FAIL.
- [ ] Implement each in the effect that already changes that monument; the rebuild call beside it stays until Task 5.
- [ ] Run the four GM test files and `scripts/analysis/check_gui_lint.py`, `script_argument_audit.py --strict`, `loc_coverage_audit.py --strict`: OK. Commit; open PR A1 (`--base main`; Player guide: "no player-facing change").

## PR A2: construction sites and level-1 monuments

### Task 3: The site building and its tracker

**Files:** Create `common/buildings/grand_monument_site.txt`; modify `common/buildings/grand_monuments.txt`, `common/production_method_groups/grand_monument_pmgs.txt`, `common/production_methods/grand_monument_pms.txt`, `common/scripted_triggers/gm_monument_triggers.txt`, `monument_triggers.txt`, `common/script_values/gm_values.txt`, `gm_monument_values.txt`, `common/on_actions/monument_events_on_actions.txt`, `events/monument_events.txt` (`.1`), `localization/english/te_buildings_l_english.yml`; tests `test_maintenance_tiers.py` (read the new file), new `SiteBuildingTests`. Map: inventory A §4, §6; D §4.

**Interfaces — Produces:**
- `pmg_grand_monument_site` / `pm_grand_monument_site` (one PM, nothing in or out; whatever `test_maintenance_tiers` asks for a no-upkeep building).
- `gm_state_site_level` (state): the site's level, 0 with none. `gm_state_has_site` (trigger).
- `gm_state_can_build_site` (trigger, the site's `can_build_government`/`can_build_private`, each reason a custom tooltip): not contested; no ceremony, unveiling, naming, restore or gift pending; `gm_state_monument_count < 6`. Open while `gm_rebuilding`.
- `gm_state_monument_count` counts a site as one.
- `gm_state_count_site_levels` (effect, state, real execution only): new site levels above `gm_site_counted` add one each to `gm_site_grandeur` and `gm_site_counted`, and in hard times run today's vanity backlash once per level; fewer levels than counted scale `gm_site_grandeur` by new ÷ old and set `gm_site_counted`. Run from `gm_state_monthly` and at the start of every dedication.

- [ ] Write `SiteBuildingTests`: the finished type's four flags (Global Constraints) and no `ai_value` or `required_construction` cost read; the site's fields above, its `ai_value` (moved verbatim from the finished type, −25 a monument via `gm_state_monument_count`); the state pulse's gate includes `has_building = building_grand_monument_site`; `.1` sends a site level to `.20` and the AI's site ceremony check, and ignores both types under `gm_rebuilding`; vanity is no longer in `.1`; `gm_state_count_site_levels` is called from `gm_state_monthly` and nowhere inside the refresh. FAIL.
- [ ] Write `SiteConstructionTests`: everything that queues or reads monument construction names the site, since the finished type can no longer be built: `gm_com_queue_levels` and `gm_com_ai_queue` (`start_building_construction = building_grand_monument_site`, the AI queueing `gm_com_levels_to_go`, not the whole target), `gm_com_pick_build_state` (a state with a site, else one where `gm_state_can_build_site` holds), `gm_com_monument_under_construction`, `gm_com_can_raise`, and every `is_under_construction` read inventory A trip 11 lists. FAIL.
- [ ] Implement. `building_grand_monument_site` loc: name "Grand Monument (Under Construction)" (`te_buildings_l_english.yml`), description: what's built here becomes a monument once dedicated. Finished type's desc drops "Its level is its grandeur".
- [ ] Run the four GM files + `test_maintenance_tiers`: OK. Commit.

### Task 4: Dedication from the site, and Rededicate

**Files:** `events/monument_events.txt` (`.2`), `common/scripted_effects/gm_effects.txt`, `gm_monument_effects.txt`, `gm_signature_effects.txt`, `gm_commission_effects.txt`, `common/scripted_guis/gm_sguis.txt`, `gm_monument_sguis.txt`, `common/scripted_triggers/monument_triggers.txt`, loc; tests `DedicateButtonTests`, new `SiteDedicationTests`, `RededicateTests`. Map: inventory A §3, D §1.

**Interfaces — Consumes:** Task 3. **Produces:**
- `gm_ceremony_mode` (state variable, set by the press, removed by the answer): `flag:site` or `flag:rededicate`. `.2`'s trigger becomes: mode site with a site standing, or mode rededicate with a finished primary; `NOT gm_seen` goes.
- `gm_state_awaits_dedication` (trigger): a site of level ≥ 1. The Dedicate sgui's validity: that, the site not under construction, no `gm_ceremony_pending`, `gm_restore_pm` or `gm_rebuilding`.
- `gm_state_finish_site` (effect, inside `gm_state_dedicate` when mode is site, given the PM key): `gm_state_count_site_levels`; a finished primary standing → `gm_state_demote_primary`, `gm_newcomer`; write `gm_levels` = `gm_site_counted`, `gm_start_grandeur` = `gm_site_grandeur`, `gm_age` = 0; set `gm_rebuilding`; `remove_building = building_grand_monument_site`; no finished building → `create_building { building = building_grand_monument level = 1 activate_production_methods = { pm_monument_$KEY$ } }` and `gm_restore_pm` = the dedication; one standing → its one `activate_production_method`; remove `gm_site_*`.
- `gm_state_apply_rededicate` (effect, the answer in mode rededicate): pays `gm_state_rededicate_cost`, halves the three records, supporters' ledger −0.5 × grandeur, keeps the landmark look and size, clears name and dedication records the way `gm_clear_state = { KEEP_LANDMARK = yes }` does without touching size, switches the method once.

- [ ] Write `SiteDedicationTests`: the ceremony's options reach `gm_state_finish_site` in mode site; "Let it stand as it is, for now" exists only in mode site; mode rededicate has "Keep it as it is" (cancel: nothing paid, nothing changed), the default on timeout, AI weight 0; `test_beside_a_grander_one` (Review Focus 2); the AI's ceremony for a site opens once its site is not under construction and level ≥ 1 (#1055's rule, moved), from `.1` and the refresh's catch-up. `RededicateTests`: the press only starts the ceremony; the answer pays and halves; `monument_events.17`, the AI (`gm_effects.txt` AI contest path) and beside (`gm_mon_order_choice` → swap first) all go through the press. `DedicateButtonTests` updated to the site reads. FAIL.
- [ ] Implement; keep `gm_newcomer`, `gm_state_newcomer_settled`, `gm_state_settle_newcomer` and `.29`'s settle branch as the one-day separator between the two switches.
- [ ] Run the four GM files: OK. Commit.

### Task 5: Records replace rebuilds

**Files:** `gm_trophy_effects.txt`, `gm_monument_effects.txt`, `gm_effects.txt`, `gm_archaeology_effects.txt`, `gm_landmark_effects.txt`, `gm_commission_effects.txt`, `common/script_values/*gm*`, `common/scripted_triggers/gm_*`, `events/monument_events.txt`, `events/te_debug_monuments_events.txt`; tests per inventory D §2 "Delete" and "Rewrite". Map: inventory A §2-§3, §5.

**Interfaces — Produces:** `gm_state_put_back_building` (effect, hidden event only): `gm_rebuilding`, `create_building` level 1 on the primary's dedication with the `gm_restore_pm` fallback.

- [ ] Write `NoRebuildTests.test_no_monument_rebuild`: no `te_construction_market_build_specified_level` call names either monument type outside Task 6's migration; no `max = 200`; none of `gm_state_tr_add_levels`, `gm_state_tr_shrink_by`, `gm_rebuild_level`, `gm_rebuild_asked`, `gm_tr_return_queued`, `gm_tr_return_relations`, `gm_monument_rebuild_self_check`, `gm_state_record_frozen_levels`, `gm_state_has_new_levels`, `gm_state_found_beside`, `gm_state_has_copied_dedication`, `gm_state_reset_copied_dedication` exists. `LostBuildingTests` (Review Focus 4): `gm_state_monthly`'s no-building branch with records standing triggers the hidden event that runs `gm_state_put_back_building`; Pull Down and `gm_state_tr_remove_whole` clear records or promote first. FAIL.
- [ ] A piece taken, a return, a dig placed, Pull Down beside, a whole taking with a monument beside (promotion: the container's records rise, the building stays and switches once), and a landmark seeded change records only; the finished building is created only where none stands and removed only where the last monument goes. Landmarks: `create_building` level 1. The "one rebuild a state a day" waits go with their rebuilds; `gm_rebuilding` stays as the create/remove guard. The copied-dedication path (#1055's `gm_state_return_to_undedicated` and the panel-pick branch of `gm_state_first_sight`) goes: a finished building is always created dedicated, and its method locks.
- [ ] Delete the tests inventory D lists under "Delete" (keep `ContestTests.test_ladder_reaches_200`: other systems use the ladder); rewrite the "Rewrite" ones to the records.
- [ ] Run the four GM files: OK. Commit.

### Task 6: Old saves

**Files:** `events/monument_events.txt` (new hidden state event `.32`), `gm_effects.txt` (refresh state loop detection), `gm_monument_effects.txt`; tests new `MigrationTests`; `docs/testing/` (Task 10). Map: spec §3.5, inventory A trip 9, B §5.

**Interfaces — Produces:** `gm_migrated` (state variable, 1); `gm_state_needs_migration` (trigger): a finished building, no `gm_migrated`, not `gm_rebuilding`; `gm_state_migrate` (effect, `.32` only).

- [ ] Write `MigrationTests`: the refresh only triggers `.32`; `.32` waits while the building `is_under_construction` (`test_waits_for_construction`); a dedicated monument gets `gm_levels` from the old arithmetic if missing, then the building goes to level 1 on its method (`gm_state_put_back_building` after `remove_building`); an undedicated one (or one with a ceremony open: `gm_ceremony_pending` and `gm_ceremony_level` cleared) becomes a site at its level through the ladder (`SPEC_TYPE = building_grand_monument_site`), `gm_site_counted` = `gm_site_grandeur` = that level, and the largest monument beside rises to primary if any; seeded landmarks set `gm_migrated`; `test_totals_survive` (Review Focus 1); the merge, revolt and lost-building checks wait for `gm_migrated`; `TE_SELF_CHECK monument_migrated` logs `gm_sum_standing` before and after. FAIL.
- [ ] Implement; the one-off `gm_short_repair_monthly` goes (spec §3.5: a frozen monument migrates at its `gm_levels`).
- [ ] Run the four GM files and `test_old_save_repairs.py`: OK. Commit.

### Task 7: Merges and revolts

**Files:** `gm_monument_effects.txt`, `gm_monument_triggers.txt`, `gm_monument_values.txt`, `gm_effects.txt`, `events/monument_events.txt` (`.1`, `.29`, `.31`), the split-piece GUI and loc (inventory B §2); tests `MergeShadowTests` (rewrite), delete `SplitPieceTests`, `SplitPieceLineTests`, `ShortRepairTests`. Map: inventory B (all of it).

**Interfaces — Produces:**
- Shadows carry records only: `gm_state_write_shadow` writes the three records (and a site's two) with no level arithmetic, for a dedicated primary and for a site. The writer-count test allows `gm_shadow_monthly`, `gm_state_raise_orphan` and the site writer.
- `gm_state_merge_pending` (trigger): an orphan shadow in the region, and here a finished building with no records, one above level 1, or a site above `gm_site_counted`.
- Settling an orphan: beside the surviving primary, or as primary if none (creating the finished building at level 1 if none stands); a finished building left above level 1 is put back to 1 (`remove_building` + `gm_state_put_back_building`, one switch). A site orphan's grandeur so far joins the surviving site's; site levels nothing explains count one each (Plan B: at the current rate).
- **Revolt rule, in this order:** an unrecorded finished building with an orphan in its region is adopted; one with none is removed (hidden event): the monument stays with the part that keeps its records (spec §3.7).

- [ ] Write the rewritten `MergeShadowTests` (records-only shadow, the two orphan outcomes, put back to 1, the revolt rule's order, `TE_SELF_CHECK monument_merge_level1`: what a merge left the surviving finished building's level and method at, read once a game). FAIL.
- [ ] Implement; delete everything inventory B marks GO (split pieces, the repair, `gm_state_unexplained_levels`, `gm_state_levels_short`, `gm_state_shadow_levels`, `gm_state_split_short`, `gm_sh_rejoin`, …) and their callers' branches (inventory B §5); `gm_mon_repair_origin` uses `gm_tr_repair_places`' most-populous rule. Keep `gm_repair_after_civil_war`.
- [ ] Run the four GM files: OK. Commit.

### Task 8: Upkeep from recorded levels

**Files:** `common/static_modifiers/gm_modifiers.txt`, `gm_effects.txt` (`gm_state_monthly`, `gm_remove_local_modifiers`), `gm_values.txt`, `common/scripted_effects/gm_policy_effects.txt` (text); tests new `UpkeepTests`. Map: inventory C §5.

**Interfaces — Produces:** static modifier `gm_upkeep` (`goods_input_construction_mult = 1`, the invisible icon); `gm_state_upkeep_mult` (state) = (`gm_state_primary_levels` + `gm_state_secondary_levels`) × (1.5 Open, 0 Mothballed, 1 otherwise) − 1, written each month into a state variable that backs the multiplier.

- [ ] Write `UpkeepTests`: `gm_state_monthly` is the one refresh site, applying `gm_upkeep` on the finished building with that multiplier; `gm_policy_upkeep_open` / `_mothballed` are no longer added (their definitions stay and are still removed, for old saves); the maintenance PM group is untouched. FAIL.
- [ ] Implement, following `scripting_best_practices.md` on building-scoped multipliers from a state pulse (the reserve hub's `local_var` shape is the alternative, inventory C §5). Run the four GM files + `test_nation_tab` (`gm_*` is covered by `NOT_ON_COUNTRY`): OK. Commit.

### Task 9: Panels and loc

**Files:** `gui/te_state_panel_widgets.gui`, `gui/journal_entry_widgets/grand_monuments_widget.gui`, `gui/gm_trophy_widgets.gui`, `common/script_values/gm_values.txt` (status, counts, displays), `common/customizable_localization/gm_custom_loc.txt`, loc; tests `StateCardTests`, layout `StateCardTest`, `OrderTest`, `FlagTest`, `AgeingPanelTests`, `test_te_systems_window.py`. Map: inventory D §1.

**Interfaces — Produces:** `gm_state_disp_site` (state: 1 with a site); the card's gate opens for a monument or a site; a site block on the card (levels built, grandeur so far, under construction or not, the Dedicate button as a type instance); Awaiting Dedication lists sites; the overview's Undedicated cell counts sites, relabelled "Being Built"; the Finished line names levels and age for every finished monument; How Grand Monuments Work describes sites, dedication and records. `gm_entry_unlocked`, the entry's `is_shown_when_inactive` and `gm_country_refresh`'s `add_journal_entry` also hold for a country whose only Grand Monument building is a site, so the Dedicate list is reachable.

- [ ] Update the layout and card tests for the block, the cell and the lists. FAIL. Implement. Run `check_gui_lint.py`, `gui_reference_audit.py --strict`, `loc_coverage_audit.py --strict`, `concept_reference_audit`, the four GM files, `test_te_systems_window`, `test_hidden_state_modifiers`: OK. Commit.

### Task 10: Docs, guide, play-test list, final gate

**Files:** `docs/systems/mod_systems.md` (§ Grand Monuments and lines 224, 2090; inventory D §3), `docs/player_guide/02-timeline.md`, `08-states.md` and the PDF, `docs/testing/grand-monuments-ageing-playtest.md`, `grand-monuments-multiple-playtest.md`, the spec (§4: `create_building` takes `activate_production_methods` and makes `buildable = no` buildings, both now in use), `docs/guides/scripting_best_practices.md` if a lesson came up; test `WalkedRefreshTests`.

- [ ] Write `WalkedRefreshTests.test_refresh_writes_nothing_structural` (Review Focus 5). Run: OK, or fix what it finds.
- [ ] Docs: the sentences inventory D §3 lists, at the guide's existing depth. Play-test list: site build and pause, Dedicate on a site, dedicating beside a grander monument, the finished building at level 1 on its method, old-save migration (grandeur unchanged, an undedicated one becomes a site), a lost building put back, a merge, a revolt's part, upkeep Open/Mothballed; self-checks `monument_migrated`, `monument_created_on_dedication` (a month after creation the method reads back; BROKEN means the `gm_restore_pm` fallback did the work), `monument_merge_level1`. Remove the split-piece, repair and rebuild self-check rows.
- [ ] Final gate: the four GM files and the peripheral tests (inventory D §2), `check_gui_lint`, every `--strict` audit CI runs, `organize_loc --check`, `check_localization_files`, `check_post_load_rosters`, `format_paradox_tabs --check` on changed `.txt`, ruff, the guide's style lint and `build_player_guide.py --check`, one BOM on every changed file. Commit; open PR A2 (`--base main`; Player guide: chapters 02 and 08).
