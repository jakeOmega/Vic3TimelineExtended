# Auto-generated files — ownership map

This file lists every committed mod file whose contents are produced by a generator script. **Do not hand-edit these files.** Edit the generator's input source and re-run the generator instead.

Quick check while exploring: a file is generator-owned if its first 5 lines contain `# AUTO-GENERATED` or `do not edit manually`. To list all marked files:

```bash
git grep -l "AUTO-GENERATED\|do not edit manually" common/ map_data/ localization/
```

## Mod scripting & data

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
| `map_data/state_regions/*.txt` (17 files) | `resources.py` | `deposits_config.json` + vanilla `game/map_data/state_regions/` | After a vanilla map change, update `deposits_config.json` to point old/removed states at successors and re-run. Files do **not** carry the AUTO-GENERATED header — verify by reading `resources.py` before editing. |

## Docs

| File | Owner | Trigger |
|---|---|---|
| `docs/laws.txt`, `docs/technologies.txt`, `docs/buildings.txt`, `docs/goods.txt`, `docs/combat_units.txt` | `mod_state_script.py` | server start + `POST /reload` |
| `docs/vic3_triggers_effects_reference.md`, `docs/vic3_modifier_type_definitions_reference.md` | `engine_docs_render.py` | manual run / server start |
| `docs/triggers_summary.txt`, `docs/effects_summary.txt`, `docs/modifiers_summary.txt`, `docs/event_targets_summary.txt`, `docs/on_actions_summary.txt`, `docs/custom_localization_summary.txt`, `docs/triggers_parsed.txt`, `docs/country_triggers.txt`, `docs/modifier_patterns.md` | `engine_docs_render.py` | manual run / server start |
| `docs/engine_coverage_report.md` | `mod_state_server.py /validate/engine-coverage` | server start + reload |
| `docs/error_log_digest.md` | `game_log_reader.py` | manual run |

## "One-shot generator" outputs (committed; may be hand-edited afterwards)

These are written by scripts that the team runs occasionally to *bootstrap* content. After bootstrap, the committed file is the source of truth and can be hand-edited. Re-running the generator will overwrite hand edits — use with care.

| File | Generator | Notes |
|---|---|---|
| `common/buildings/company_buildings.txt` | `gen_vanilla_company_buildings.py` | |
| `common/production_method_groups/unique_pm_groups.txt` | `gen_vanilla_company_buildings.py` | |
| `common/production_methods/unique_pms.txt` | `gen_vanilla_company_buildings.py` | Note: was hand-edited during the 1.13 migration. If running the generator again, propagate hand edits via the script's templates first. |
| `common/company_types/extra_companies_vanilla_updates.txt` | `gen_vanilla_company_injects.py` AND `gen_vanilla_company_buildings.py` (both write here) | Coordinate runs to avoid one overwriting the other. |
| `localization/english/te_buildings_l_english.yml` | `gen_vanilla_company_buildings.py` | |
| `gfx/interface/icons/character_trait_icons/aptitude_*` (DDS) | `gen_aptitude_icons.py` | |
| `gfx/interface/icons/production_method_icons/*` (DDS) | `gen_pm_icons.py` | |
| `gfx/interface/icons/law_icons/*` (DDS) | `gen_law_icons.py` | |
