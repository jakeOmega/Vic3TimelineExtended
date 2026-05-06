# Documentation Reference

This folder contains reference documents for Victoria 3 modding and this mod's content. **AI agents should read only the docs relevant to their current task.**

Files marked `[auto-gen]` are regenerated automatically and should not be hand-edited — see `auto_generated_files.md` for the canonical generator → output map.

## Mod Game Data `[auto-gen]`

| File | Contents | Read When... |
|------|----------|--------------|
| `buildings.txt` | All buildings with their PM groups and PMs in tree format | Working on buildings, production methods, or PM costs |
| `combat_units.txt` | All combat unit types with unlocking technologies | Working on military units or combat balance |
| `goods.txt` | All tradeable goods (one per line) | Checking goods names for PM inputs/outputs or trade |
| `laws.txt` | All law groups and laws with unlock techs | Working on laws, political systems, or legal prerequisites |
| `technologies.txt` | All technologies by era with prerequisites and descriptions | Working on tech trees, unlock conditions, or era gating |

## Engine Reference (Triggers, Effects, Modifiers) `[auto-gen]`

| File | Contents | Read When... |
|------|----------|--------------|
| `vic3_triggers_effects_reference.md` | Full compressed reference: 84 iterator families, 820 triggers, 337 effects | Looking up a trigger/effect name, scope, or syntax |
| `vic3_modifier_type_definitions_reference.md` | All ~2,300 modifier type keys from vanilla | Validating modifier names, finding correct modifier for a scope |
| `triggers_summary.txt` | Compact pipe-delimited trigger index (scope \| name \| description) | Quick trigger lookup by scope |
| `effects_summary.txt` | Compact pipe-delimited effect index (scope \| name \| description) | Quick effect lookup by scope |
| `modifiers_summary.txt` | Compact pipe-delimited modifier index | Quick modifier lookup |
| `triggers_parsed.txt` | Fully parsed triggers with syntax examples and comparison operators | Detailed trigger documentation with examples |
| `country_triggers.txt` | Country-scope triggers only, with descriptions | Working specifically in country scope |
| `event_targets_summary.txt` | Engine event-target accessors (e.g. `controller`, `level`, `training_rate`) | Looking up a property usable in script values / trigger comparisons |
| `on_actions_summary.txt` | Vanilla `on_action` hooks | Wiring custom logic to engine pulses or game events |
| `custom_localization_summary.txt` | Custom localization function documentation | Writing dynamic localization expressions |
| `modifier_patterns.md` | Auto-discovered modifier patterns (`building_*`, `goods_*`, `state_building_*`, …) with placeholders | Adding a dynamic modifier; verifying placeholder vocabulary |

## Mod Authoring Guides

| File | Contents | Read When... |
|------|----------|--------------|
| `event_creation_guide.md` | Event boilerplate, videos, icons, style guide, IG reactions, AI-weight pitfalls, amenability vs. enactment mechanics | Writing or modifying events |
| `scripting_best_practices.md` | Modifier validation, scope chains, time units, expense scaling, scripted triggers/effects catalog, fast-scaling event-effect rules | Scripting modifiers, effects, debugging, or checking for reusable helpers |
| `mod_systems.md` | All key mod systems: banking cycle, global warming, construction scaling, migration crowding, nuclear, colonial collapse, wonders, etc. | Understanding or modifying a mod system |
| `journal_entry_systems.md` | All 10+ custom journal-entry systems in detail | Working on or debugging a journal entry system |
| `python_tools.md` | All Python scripts, mod state server API, every endpoint, AI-agent workflow | Using Python tools or the mod state server |
| `gui_modding_guide.md` | Widget types, layout, data binding, scripted GUIs, standalone panels, tooltips, format specifiers, GetVariableSystem | Creating or modifying GUI panels |
| `modding-reference.md` | Compressed Clausewitz engine reference (data types, scope rules, file formats) | Wider engine context not covered by the trigger/effect references |
| `quick_reference_ids.md` | Vanilla law / IG / pop / strata IDs, script values, modifier durations | Looking up game IDs or script-value names quickly |

## Vanilla & Patch References

| File | Contents | Read When... |
|------|----------|--------------|
| `vanilla_economy_reference.md` | Concept primer on vanilla Vic3 economy (pops, ownership / IP, markets / MAPI, companies, power blocs, naval economy) | Need shared context on the base-game economy before touching mod content that hooks it |
| `vanilla_war_reference.md` | Concept primer on vanilla Vic3 war systems (formations, units, commanders, mobilization, supply, war support, capitulation) | Need shared context on the base-game war layer before touching anti-war / wartime / mobilization-related mod content |
| `vanilla_diplomacy_reference.md` | Concept primer on vanilla Vic3 diplomacy (rank, prestige, relations, attitudes, interests, infamy, actions, treaties, subjects, power blocs) | Need shared context on the base-game diplomatic layer before touching mod content that hooks ranks / infamy / plays / subjects / power blocs |
| `vanilla_patch_runbook.md` | Step-by-step process for absorbing a new vanilla patch into the mod | Updating the mod after a vanilla version bump |
| `vanilla_known_bugs.md` | Vanilla bugs the mod *cannot* fix; debug.log noise to ignore | Triaging log entries; deciding whether an issue is mod-side |
| `vanilla_company_buildings_reference.md` | System architecture + all implemented vanilla company buildings | Implementing company buildings for vanilla companies |
| `treaty_articles_reference.md` | Treaty article engine constraints + all implemented article designs | Implementing new treaty articles |
| `wonder_buildings_reference.md` | Two-phase construction pattern + all implemented wonder designs | Implementing new wonder / megastructure buildings |
| `commented_vanilla_pms.txt` | Vanilla production methods with input/output cost annotations | Copying a vanilla PM as a starting template; checking PM cost shape |
| `commented_vanilla_military_units.txt` | Vanilla `combat_unit_type` definitions, annotated | Copying a vanilla unit as a starting template |

## System Designs (Implemented)

| File | Contents | Read When... |
|------|----------|--------------|
| `decolonization_review.md` | Post-implementation review of decolonization mechanics + path-dependent legacies | Modifying or extending decolonization; understanding the design intent |
| `strategic_reserve_system.md` | Architecture and file layout of the Strategic Reserve journal-entry system | Adding goods to the SR; touching the SR JE / Hub building |
| `political_lobbies_design.md` | Design proposals for 15 political lobby types (2 implemented, 13 planned) | Implementing new political lobbies; tracking what's already shipped |

## Audits & Reviews

| File | Contents | Read When... |
|------|----------|--------------|
| `combat_unit_balance_review.md` | Era-by-era combat-unit balance audit | Tuning unit stats or adding new units |
| `pm_building_balance_review.md` | Per-building production-method balance audit | Tuning a PM's input/output ratios or unlocking conditions |
| `tech_tree_balance_review.md` | Tech-tree balance review for eras 6–9 | Adding or rebalancing late-era technologies |
| `script_parameterization_audit.md` | Catalog of helper scripted_effects / scripted_triggers and the parameterization pattern used | Considering whether to introduce a new helper vs. inlining |
| `open_issues.md` | Living tracker of known mod bugs / followups not yet ticketed elsewhere | Looking for the current to-do queue; before starting unrelated work |
| `engine_coverage_report.md` `[auto-gen]` | Output of `/validate/engine-coverage` — unknown / suspicious modifier-name flags + did-you-mean suggestions | After editing modifiers or before merging; cross-reference against `error.log` lines |
| `error_log_digest.md` `[auto-gen, gitignored]` | Mod-only summary of `error.log` + diff vs. `error.1.log` | Triaging a recent crash / parse error |
| `event_magnitude_report.md` `[auto-gen]` | Hardcoded fast-scaling event effects (prestige / treasury / bureaucracy / construction) flagged by the magnitude audit | After editing or adding multi-option events; before merging |
| `balance_snapshot.json` `[auto-gen, manual run]` | JSON dump of mod balance state for vanilla-bump comparisons (`scripts/snapshot_balance.py`) | Bumping vanilla; diffing balance against a previous snapshot |

## Image Pipeline

| File | Contents | Read When... |
|------|----------|--------------|
| `event_image_inventory.md` `[auto-gen]` | Every mod event with title, description, flavor, and current image path | Driving custom event-image generation |

## Future Work / Inspiration

| File | Contents | Read When... |
|------|----------|--------------|
| `future_journal_entry_ideas.md` | Planned expansion for social-movement JEs (additional events, toggle buttons, cross-JE interactions) | Expanding the 8 social-movement journal entries |
| `event_inspiration.md` | Historical economic / financial crises as event seeds | Drafting new flavor events; looking for seed material |
| `dynamic_country_naming_feasibility.md` | Feasibility study for "another country of the same culture exists" dynamic naming | Implementing dynamic country names for splits (Korea, Germany, Vietnam, …) |

## Auto-generation Registry

| File | Contents | Read When... |
|------|----------|--------------|
| `auto_generated_files.md` | Canonical map of generator scripts → output files (mod data, docs, GFX) | Finding the input source of an auto-rebuilt file; before hand-editing anything |

## Session Plans

| Path | Contents |
|------|----------|
| `superpowers/plans/` | Multi-step implementation plans authored by Claude Code via `/writing-plans`. Each plan is self-contained and dated. |

## Engine-Generated Logs (outside the repo)

These files are generated by running `script_docs` in the in-game console **without the mod loaded**, then copied to `~/src/vic3/docs/` (the vanilla snapshot path used by `mod_state_server`'s engine-doc loader). The compressed `.md` references in this folder are produced from these logs — read the raw `.log` files only when cross-referencing.

| File | Contents | Read When... |
|------|----------|--------------|
| `event_targets.log` | All scope-to-scope accessors and value properties | Verifying a property not in `event_targets_summary.txt` |
| `triggers.log` | Engine-canonical trigger documentation (raw source for `vic3_triggers_effects_reference.md`) | Cross-referencing trigger syntax |
| `effects.log` | Engine-canonical effect documentation | Cross-referencing effect syntax |
| `modifiers.log` | Engine-canonical modifier documentation (raw source for `vic3_modifier_type_definitions_reference.md`) | Cross-referencing modifier definitions |
| `on_actions.log` | Engine-canonical on_actions documentation | Looking up vanilla on_action hooks |
| `custom_localization.log` | Custom localization function documentation | Writing dynamic localization expressions |
