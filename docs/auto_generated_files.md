# Auto-generated files — ownership map

This file lists every committed mod file whose contents are produced by a generator script. **Do not hand-edit these files.** Edit the generator's input source and re-run the generator instead.

Quick check while exploring: a file is generator-owned if its first 5 lines contain `# AUTO-GENERATED` or `do not edit manually`. To list all marked files:

```bash
git grep -l "AUTO-GENERATED\|do not edit manually" common/ map_data/ localization/
```

## Mod scripting & data

The scripts in this section auto-run inside `mod_state_server.py` after every full `/reload` (see `POST_LOAD_GENERATORS` and `_run_post_load_generators`). Manual invocation remains useful for `--dry-run` or when iterating on the script itself; set `VIC3_SKIP_POST_LOAD_GENERATORS=1` to disable the auto-run.

| File / glob | Owner script | Input | Notes |
|---|---|---|---|
| `common/ideologies/modified.txt` | `apply_ideologies.py` | `ideology_modifications.py` + vanilla `common/ideologies/*.txt` | Re-run after vanilla updates to pull in new vanilla laws/attitudes (e.g. 1.13 added `law_social_monarchy`). The python file holds the *delta* the mod imposes; vanilla files are the baseline. |
| `common/interest_groups/00_armed_forces.txt` | `ig_feminism.py` | mod state | Same pattern for `00_devout`, `00_industrialists`, `00_intelligentsia`, `00_landowners`, `00_petty_bourgeoisie`, `00_rural_folk`, `00_trade_unions`. |
| `common/interest_groups/00_devout.txt` | `ig_feminism.py` | mod state | (see armed_forces) |
| `common/interest_groups/00_industrialists.txt` | `ig_feminism.py` | mod state | (see armed_forces) |
| `common/interest_groups/00_intelligentsia.txt` | `ig_feminism.py` | mod state | (see armed_forces) |
| `common/interest_groups/00_landowners.txt` | `ig_feminism.py` | mod state | (see armed_forces) |
| `common/interest_groups/00_petty_bourgeoisie.txt` | `ig_feminism.py` | mod state | (see armed_forces) |
| `common/interest_groups/00_rural_folk.txt` | `ig_feminism.py` | mod state | (see armed_forces) |
| `common/interest_groups/00_trade_unions.txt` | `ig_feminism.py` | mod state | (see armed_forces) |
| `common/buy_packages/00_buy_packages.txt` | `pop_needs_curves.py` | mod state | |
| `common/production_methods/extra_pms.txt` & `unique_pms.txt` (cost-comment headers only); `common/combat_unit_types/extra_combat_units.txt` & `common/mobilization_options/extra_mobilization_options.txt` (cost-comment headers in `upkeep_modifier` blocks); `docs/engine/commented_vanilla_pms.txt`; `docs/engine/commented_vanilla_military_units.txt`; `common/script_values/auto_combat_unit_market_costs.txt`; `localization/english/te_combat_units_l_english.yml` (per-unit `Cost at base prices: …` integer + `Cost at current market prices: …` SV reference appended to each `combat_unit_type_*_desc`) | `pm_costs.py` | `common/goods/*.txt` + PM files + `extra_combat_units.txt` itself | Replaces existing comment anchors in the `workforce_scaled` and `upkeep_modifier` blocks; idempotent across runs. The `docs/engine/commented_vanilla_*` reference dumps are gitignored. The auto SV file holds one `value_combat_unit_market_cost_<unit>` per non-INJECT mod combat unit, computing total upkeep at current prices via `(1 + market.mg:<good>.market_goods_pricier) × <base_contribution>`. The loc updater warns (and skips) any `_desc` missing the canonical `Cost at base prices: #N @money!N #!` suffix. |
| `map_data/state_regions/*.txt` (17 files) | `resources.py` | `deposits_config.json` + vanilla `game/map_data/state_regions/` | After a vanilla map change, update `deposits_config.json` to point old/removed states at successors and re-run. Files do **not** carry the AUTO-GENERATED header — verify by reading `resources.py` before editing. |
| `localization/english/te_*_l_english.yml` (~26 category files as of 2026-05; grows with new content families) | `organize_loc.py` | every other `*_l_english.yml` under `localization/english/` | Categorises and sorts every key. When you introduce a brand-new content family (new key prefix), add a `startswith` rule in `categorize_key` and a category in `CATEGORIES` — otherwise its keys silently land in MISCELLANEOUS and any pre-existing dedicated file gets dropped on next run. **`te_buildings_l_english.yml` is also written by `gen_vanilla_company_buildings.py`** (one-shot, see § "One-shot generator outputs" below); the auto-run order matters — run organize_loc.py *after* gen_vanilla_company_buildings.py to fold the appended keys into their final category file. The mod_state_server post-load chain handles this automatically. |
| `localization/english/te_power_bloc_unlocks_l_english.yml` (`*_pb_principles_bool_desc` keys only) | `gen_pb_principle_unlock_descs.py` | `common/power_bloc_principles/extra_power_bloc_principles.txt` (each principle's `possible` clause) + `common/modifier_type_definitions/tech_gate_modifier_types.txt` (the defined unlock booleans) | Generates one description per `country_*_pb_principles_bool` modifier naming the tier(s) and group(s) it unlocks. Runs **before** organize_loc.py so the new keys flow into the canonical file. The generator preserves the short-label `*_pb_principles_bool` keys (without `_desc`) verbatim — those are co-located here by the `POWER_BLOC_UNLOCKS` rule in `categorize_key`. Orphaned bools (defined but no principle requires them) and undefined bools (referenced by a principle but missing from `tech_gate_modifier_types.txt`) are logged as warnings. |
| `common/geographic_regions/te_formable_regions_generated.txt` | `scripts/generators/gen_formable_regions.py` | vanilla `common/strategic_regions/*.txt` + inline config in the script | Holds explicit-state-list `geographic_region_united_{europe,africa,north_america,earth}` for the EUN/AFU/UNA/UNE formables. Vic3's formable code only reads `state_regions = {...}` (not `strategic_regions = {...}`) when expanding required states. **Manual rerun only** — not in the post-load chain; rerun after vanilla strategic-region rebalances. Fails loudly if a configured strategic region disappears, which is the prompt to update its inline config. |

## Docs

All generator-produced docs files live under `docs/engine/`. Manually-curated audit reports under `docs/audits/` (e.g. `mod_only_tech_modifier_baseline.md`) are bootstrapped by `tech_balance_audit.py` and then hand-edited; see "One-shot generator outputs" for that pattern.

| File | Owner | Trigger |
|---|---|---|
| `docs/engine/laws.txt`, `docs/engine/technologies.txt`, `docs/engine/buildings.txt`, `docs/engine/goods.txt`, `docs/engine/combat_units.txt` | `mod_state_script.py` | server start + `POST /reload` |
| `docs/engine/vic3_triggers_effects_reference.md`, `docs/engine/vic3_modifier_type_definitions_reference.md` | `engine_docs_render.py` | manual run / server start |
| `docs/engine/triggers_summary.txt`, `docs/engine/effects_summary.txt`, `docs/engine/modifiers_summary.txt`, `docs/engine/event_targets_summary.txt`, `docs/engine/on_actions_summary.txt`, `docs/engine/custom_localization_summary.txt`, `docs/engine/triggers_parsed.txt`, `docs/engine/country_triggers.txt`, `docs/engine/modifier_patterns.md` | `engine_docs_render.py` | manual run / server start |
| `docs/engine/engine_coverage_report.md` | `mod_state_server.py /validate/engine-coverage` | server start + reload |
| `docs/engine/error_log_digest.md` | `game_log_reader.py` | manual run |
| `docs/engine/event_magnitude_report.md` | `event_magnitude_audit.py` | server start + `POST /reload` (post-load chain) |
| `docs/engine/modifier_visibility_report.md` | `modifier_visibility_audit.py` | server start + `POST /reload` (post-load chain). Flags modifier values too small to display given the type's `decimals = N` precision. |
| `docs/engine/kill_character_audit.md` | `kill_character_audit.py` | server start + `POST /reload` (post-load chain) |
| `docs/engine/localization_accessor_report.md` | `localization_accessor_audit.py` | server start + `POST /reload` (post-load chain). Flags `[X.Y.Z]` accessor chains in loc YAML that the engine would silently drop (e.g. `[SCOPE.GetTargetCountry.GetName]` outside of contexts where it resolves). Catalog seeded from vanilla loc; supplement in `localization_accessor_vanilla_extras.py`. |
| `docs/engine/event_image_inventory.md` | `gen_event_inventory.py` | server start + `POST /reload` (post-load chain). Inventory of all mod events used to drive custom event-image generation. |
| `docs/audits/mod_only_tech_modifier_baseline.md` | `scripts/analysis/tech_balance_audit.py --refresh-baseline` | manual run; row-level `target_typical_value` cells are then hand-edited |
| `docs/data/tech_modifier_baseline.json`, `docs/data/tech_modifier_pattern_baseline.json` | `scripts/analysis/tech_modifier_baseline.py` | refreshed via `tech_balance_audit.py --refresh-baseline` |
| `docs/data/balance_snapshot.json` | `scripts/snapshot_balance.py` | manual run; snapshot before vanilla bumps |

## "One-shot generator" outputs (committed; may be hand-edited afterwards)

These are written by scripts that the team runs occasionally to *bootstrap* content. After bootstrap, the committed file is the source of truth and can be hand-edited. Re-running the generator will overwrite hand edits — use with care.

| File | Generator | Notes |
|---|---|---|
| `common/buildings/company_buildings.txt` | `scripts/generators/gen_vanilla_company_buildings.py` | |
| `common/production_method_groups/unique_pm_groups.txt` | `scripts/generators/gen_vanilla_company_buildings.py` | |
| `common/production_methods/unique_pms.txt` | `scripts/generators/gen_vanilla_company_buildings.py` | Note: was hand-edited during the 1.13 migration. If running the generator again, propagate hand edits via the script's templates first. |
| `common/company_types/extra_companies_vanilla_updates.txt` | `scripts/generators/gen_vanilla_company_injects.py` AND `scripts/generators/gen_vanilla_company_buildings.py` (both write here) | Coordinate runs to avoid one overwriting the other. |
| `localization/english/te_buildings_l_english.yml` | `scripts/generators/gen_vanilla_company_buildings.py` | Appended to by the company generator before being re-categorized by organize_loc.py — see note in the post-load table above. |
| `localization/english/extra_law_events_l_english.yml`, `ministry_law_events_l_english.yml` | `scripts/generators/gen_loc_files.py` | Bootstrap dumps of event localization. After bootstrap these are hand-edited freely; do not re-run without merging hand changes first. |
| `gfx/interface/icons/character_trait_icons/aptitude_*` (DDS) | `scripts/image_pipeline/gen_aptitude_icons.py` | |
| `gfx/interface/icons/production_method_icons/*` (DDS) | `scripts/image_pipeline/gen_pm_icons.py` | |
| `gfx/interface/icons/law_icons/*` (DDS) | `scripts/image_pipeline/gen_law_icons.py` | |
