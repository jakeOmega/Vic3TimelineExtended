# Documentation Reference

This folder contains reference documents for Victoria 3 modding and this mod's content. **AI agents should read only the docs relevant to their current task.**

Files marked `[auto-gen]` are regenerated automatically and should not be hand-edited — see `auto_generated_files.md` for the canonical generator → output map.

## Layout

```
docs/
├── README.md                 (this file)
├── auto_generated_files.md   (generator → output ownership map)
├── guides/                   (curated authoring guides — read first)
├── systems/                  (mod-system writeups)
├── vanilla/                  (hand-curated vanilla-game references)
├── engine/                   (auto-generated engine dumps + audit reports)
├── audits/                   (active audits + living trackers)
├── data/                     (machine-readable inputs / baselines)
├── archive/                  (deferred / completed / orphaned reference)
└── superpowers/plans/        (multi-step implementation plans from /writing-plans)
```

## Mod Authoring Guides — `guides/`

| File | Contents | Read When... |
|------|----------|--------------|
| [`guides/scripting_best_practices.md`](guides/scripting_best_practices.md) | Modifier validation, scope chains, time units, expense scaling, scripted triggers/effects catalog, fast-scaling event-effect rules | Scripting modifiers, effects, debugging, or checking for reusable helpers |
| [`guides/event_creation_guide.md`](guides/event_creation_guide.md) | Event boilerplate, videos, icons, style guide, IG reactions, AI-weight pitfalls, amenability vs. enactment mechanics | Writing or modifying events |
| [`guides/gui_modding_guide.md`](guides/gui_modding_guide.md) | Widget types, layout, data binding, scripted GUIs, standalone panels, tooltips, format specifiers, GetVariableSystem | Creating or modifying GUI panels |
| [`guides/python_tools.md`](guides/python_tools.md) | All Python scripts, mod state server API, every endpoint, AI-agent workflow | Using Python tools or the mod state server |
| [`guides/vanilla_patch_runbook.md`](guides/vanilla_patch_runbook.md) | Step-by-step process for absorbing a new vanilla patch into the mod | Updating the mod after a vanilla version bump |
| [`guides/quick_reference_ids.md`](guides/quick_reference_ids.md) | Vanilla law / IG / pop / strata IDs, script values, modifier durations | Looking up game IDs or script-value names quickly |

## Mod Systems — `systems/`

| File | Contents | Read When... |
|------|----------|--------------|
| [`systems/mod_systems.md`](systems/mod_systems.md) | All key mod systems: banking cycle, global warming, construction scaling, migration crowding, nuclear, colonial collapse, wonders, etc. | Understanding or modifying a mod system |
| [`systems/journal_entry_systems.md`](systems/journal_entry_systems.md) | All 10+ custom journal-entry systems in detail | Working on or debugging a journal entry system |
| [`systems/strategic_reserve_system.md`](systems/strategic_reserve_system.md) | Architecture and file layout of the Strategic Reserve journal-entry system | Adding goods to the SR; touching the SR JE / Hub building |

## Vanilla & Patch References — `vanilla/`

The directory has its own [`vanilla/CLAUDE.md`](vanilla/CLAUDE.md) — a condensed "what you need to know" summary that auto-loads when working in `docs/vanilla/`. Read that first for fast orientation; the per-system docs below are the deep dives.

**External companion**: the [Modding-Digests](https://github.com/Victoria-3-Modding-Co-op/Modding-Digests/) repo (cloned to `vic3_modding_digests_path`, auto-pulled on server cold start) holds upstream-maintained per-patch breaking-change + script-doc diffs. The reference docs here cover *what is*; the digests cover *what changed* version-by-version. First stop for "what broke in vanilla 1.x" questions.

| File | Contents | Read When... |
|------|----------|--------------|
| [`vanilla/vanilla_economy_reference.md`](vanilla/vanilla_economy_reference.md) | Concept primer on vanilla Vic3 economy (pops, ownership / IP, markets / MAPI, companies, power blocs, naval economy) | Need shared context on the base-game economy before touching mod content that hooks it |
| [`vanilla/vanilla_war_reference.md`](vanilla/vanilla_war_reference.md) | Concept primer on vanilla Vic3 war systems (formations, units, commanders, mobilization, supply, war support, capitulation) | Need shared context on the base-game war layer before touching anti-war / wartime / mobilization-related mod content |
| [`vanilla/vanilla_diplomacy_reference.md`](vanilla/vanilla_diplomacy_reference.md) | Concept primer on vanilla Vic3 diplomacy (rank, prestige, relations, attitudes, interests, infamy, actions, treaties, subjects, power blocs) | Need shared context on the base-game diplomatic layer before touching mod content that hooks ranks / infamy / plays / subjects / power blocs |
| [`vanilla/vanilla_politics_reference.md`](vanilla/vanilla_politics_reference.md) | Concept primer on vanilla Vic3 politics (legitimacy, laws, IGs, parties, ideologies, movements, characters, institutions, decrees) | Need shared context on the base-game political layer before touching mod content that hooks laws / IG approval / movements / characters / institutions |
| [`vanilla/vanilla_states_reference.md`](vanilla/vanilla_states_reference.md) | Concept primer on vanilla Vic3 states (incorporation, infrastructure, market access, capital, turmoil, obstinance, devastation, food security, pollution, hubs, split states) | Touching state-level mechanics: incorporation cost, infrastructure / market-access modifiers, turmoil/obstinance penalties, food-security or pollution effects |
| [`vanilla/vanilla_technology_reference.md`](vanilla/vanilla_technology_reference.md) | Concept primer on vanilla Vic3 technology (three trees, five eras, innovation generation and cap, technology spread, slingshot strategy) | Adding mod technologies; reasoning about era-cost penalties or spread; refreshing tech-balance baselines |
| [`vanilla/vanilla_pops_reference.md`](vanilla/vanilla_pops_reference.md) | Concept primer on vanilla Vic3 pops (definition, culture/religion/acceptance, assimilation, conversion, the 15 professions, social hierarchies, qualifications, literacy, education access, workforce/dependents, job satisfaction) | Touching pop-side mechanics not covered by economy/politics: assimilation/conversion, social-hierarchy partitions, qualifications gating |
| [`vanilla/vanilla_colonization_reference.md`](vanilla/vanilla_colonization_reference.md) | Concept primer on vanilla Vic3 colonization (gating, malaria, growth, native uprising, Colonial Administration JE, company colonization) | Touching colonization mechanics, colonial-admin JEs, native uprisings, or Civilizing Mission tech-gated content |
| [`vanilla/vanilla_formable_countries_reference.md`](vanilla/vanilla_formable_countries_reference.md) | Concept primer on vanilla Vic3 formable countries (minor / major unification, candidacy, leadership plays, unification plays, special unifications) | Touching formable-country mechanics; complement to the `add-formable-country` skill |
| [`vanilla/vanilla_known_bugs.md`](vanilla/vanilla_known_bugs.md) | Vanilla bugs the mod *cannot* fix; debug.log noise to ignore | Triaging log entries; deciding whether an issue is mod-side |
| [`vanilla/vanilla_company_buildings_reference.md`](vanilla/vanilla_company_buildings_reference.md) | System architecture + all implemented vanilla company buildings | Implementing company buildings for vanilla companies |
| [`vanilla/treaty_articles_reference.md`](vanilla/treaty_articles_reference.md) | Treaty article engine constraints + all implemented article designs | Implementing new treaty articles |
| [`vanilla/wonder_buildings_reference.md`](vanilla/wonder_buildings_reference.md) | Two-phase construction pattern + all implemented wonder designs | Implementing new wonder / megastructure buildings |
| [`vanilla/modding-reference.md`](vanilla/modding-reference.md) | Compressed Clausewitz engine reference (data types, scope rules, file formats) | Wider engine context not covered by the trigger/effect references |

## Engine Reference & Auto-Generated Dumps — `engine/`

All files in this directory are `[auto-gen]` — regenerated on `POST /reload` (see `auto_generated_files.md`).

### Mod data dumps

| File | Contents |
|------|----------|
| [`engine/buildings.txt`](engine/buildings.txt) | All buildings with their PM groups and PMs in tree format |
| [`engine/combat_units.txt`](engine/combat_units.txt) | All combat unit types with unlocking technologies |
| [`engine/goods.txt`](engine/goods.txt) | All tradeable goods (one per line) |
| [`engine/laws.txt`](engine/laws.txt) | All law groups and laws with unlock techs |
| [`engine/technologies.txt`](engine/technologies.txt) | All technologies by era with prerequisites and descriptions |

### Engine references (triggers, effects, modifiers)

| File | Contents |
|------|----------|
| [`engine/vic3_triggers_effects_reference.md`](engine/vic3_triggers_effects_reference.md) | Full compressed reference: 84 iterator families, 820 triggers, 337 effects |
| [`engine/vic3_modifier_type_definitions_reference.md`](engine/vic3_modifier_type_definitions_reference.md) | All ~2,300 modifier type keys from vanilla |
| [`engine/triggers_summary.txt`](engine/triggers_summary.txt) | Compact pipe-delimited trigger index (scope \| name \| description) |
| [`engine/effects_summary.txt`](engine/effects_summary.txt) | Compact pipe-delimited effect index (scope \| name \| description) |
| [`engine/modifiers_summary.txt`](engine/modifiers_summary.txt) | Compact pipe-delimited modifier index |
| [`engine/triggers_parsed.txt`](engine/triggers_parsed.txt) | Fully parsed triggers with syntax examples and comparison operators |
| [`engine/country_triggers.txt`](engine/country_triggers.txt) | Country-scope triggers only, with descriptions |
| [`engine/event_targets_summary.txt`](engine/event_targets_summary.txt) | Engine event-target accessors |
| [`engine/on_actions_summary.txt`](engine/on_actions_summary.txt) | Vanilla `on_action` hooks |
| [`engine/custom_localization_summary.txt`](engine/custom_localization_summary.txt) | Custom localization function documentation |
| [`engine/modifier_patterns.md`](engine/modifier_patterns.md) | Auto-discovered modifier patterns (`building_*`, `goods_*`, `state_building_*`, …) with placeholders |

### Vanilla annotated dumps (gitignored)

| File | Contents |
|------|----------|
| [`engine/commented_vanilla_pms.txt`](engine/commented_vanilla_pms.txt) | Vanilla production methods with input/output cost annotations |
| [`engine/commented_vanilla_military_units.txt`](engine/commented_vanilla_military_units.txt) | Vanilla `combat_unit_type` definitions, annotated |

### Audit + validation reports

| File | Contents |
|------|----------|
| [`engine/engine_coverage_report.md`](engine/engine_coverage_report.md) | Output of `/validate/engine-coverage` — unknown / suspicious modifier flags |
| [`engine/modifier_visibility_report.md`](engine/modifier_visibility_report.md) | Modifier values too small to display given the type's `decimals = N` |
| [`engine/kill_character_audit.md`](engine/kill_character_audit.md) | `kill_character` calls audited for void6 / exists guards |
| [`engine/event_magnitude_report.md`](engine/event_magnitude_report.md) | Hardcoded fast-scaling event effects flagged by the magnitude audit |
| [`engine/event_image_inventory.md`](engine/event_image_inventory.md) | Every mod event with title, description, flavor, and current image path |
| [`engine/loc_render_report.md`](engine/loc_render_report.md) | Bracket-style formatting tags (`[b]`, `[/i]`, …) in loc values — render-breaking, cause log-spam lag |
| [`engine/any_limit_report.md`](engine/any_limit_report.md) | `limit = { }` placed as an immediate child of an `any_*` trigger (silently ignored → meaning flip) |
| [`engine/error_log_digest.md`](engine/error_log_digest.md) | Mod-only summary of `error.log` + diff vs. `error.1.log` (gitignored) |

## Audits & Living Trackers — `audits/`

| File | Contents | Read When... |
|------|----------|--------------|
| [`audits/open_issues.md`](audits/open_issues.md) | Living tracker of known mod bugs / followups not yet ticketed elsewhere | Looking for the current to-do queue; before starting unrelated work |
| [`audits/mod_known_noise.md`](audits/mod_known_noise.md) | Mod-side cosmetic log entries filtered from triage but tracked in `open_issues.md` | Triaging logs; auditing what's swept under the rug |
| [`audits/combat_unit_balance_review.md`](audits/combat_unit_balance_review.md) | Era-by-era combat-unit balance audit | Tuning unit stats or adding new units |
| [`audits/concept_usage_audit.md`](audits/concept_usage_audit.md) | Semantic audit of every `[concept_X]` / `[Concept(...)]` loc reference: which link the right meaning vs a homonym (e.g. "genetic screening" → naval screening). Full inventory + misuse/borderline findings. Regen via `scripts/analysis/concept_usage_inventory.py` + `render_concept_usage_audit.py` | Adding concept links to loc; checking a common-word concept isn't misused. Complements `concept_reference_audit.py` (which only checks a ref *exists*) |
| [`audits/pm_building_balance_review.md`](audits/pm_building_balance_review.md) | Per-building production-method balance audit | Tuning a PM's input/output ratios or unlocking conditions |
| [`audits/mod_only_tech_modifier_baseline.md`](audits/mod_only_tech_modifier_baseline.md) | User-supplied baseline targets for mod-only tech modifiers | Re-tuning tech modifier targets or refreshing the audit anchor |
| [`audits/script_parameterization_audit.md`](audits/script_parameterization_audit.md) | Catalog of helper scripted_effects / scripted_triggers and the parameterization pattern used | Considering whether to introduce a new helper vs. inlining |
| [`audits/steam_workshop_description.md`](audits/steam_workshop_description.md) | Draft Steam Workshop description maintained per release | Updating the Workshop listing copy |

## Machine-Readable Data — `data/`

| File | Contents | Read When... |
|------|----------|--------------|
| [`data/balance_snapshot.json`](data/balance_snapshot.json) | JSON dump of mod balance state for vanilla-bump comparisons (`scripts/snapshot_balance.py`) | Bumping vanilla; diffing balance against a previous snapshot |
| [`data/tech_modifier_baseline.json`](data/tech_modifier_baseline.json) | Vanilla tech modifier baseline cache (per-modifier min/median/max) | Refresh after vanilla bumps via `tech_balance_audit.py --refresh-baseline` |
| [`data/tech_modifier_pattern_baseline.json`](data/tech_modifier_pattern_baseline.json) | Vanilla pattern-grouped baseline (e.g. `building_*_throughput_add` median) | Same audit cache, parametric-pattern half |
| [`data/tech_modifier_pattern_overrides.yml`](data/tech_modifier_pattern_overrides.yml) | Hand overrides for parametric pattern medians | When a pattern's vanilla median needs a designer adjustment |
| [`data/tech_modifier_polarity.yml`](data/tech_modifier_polarity.yml) | Override registry for tech-modifier polarity classification | When the heuristic mis-labels a modifier's polarity |

## Archive — `archive/`

Reference material kept for historical or design-rationale purposes. Not actively maintained; check git history for the surrounding work.

| File | Why it's here |
|------|---------------|
| [`archive/political_lobbies_design.md`](archive/political_lobbies_design.md) | DEFERRED — implementation reverted after a new-game crash; design + engine findings preserved for re-attempt |
| [`archive/dynamic_country_naming_feasibility.md`](archive/dynamic_country_naming_feasibility.md) | Feasibility study; not implemented |
| [`archive/decolonization_review.md`](archive/decolonization_review.md) | Audit + redesign work shipped — preserved as design rationale |
| [`archive/future_journal_entry_ideas.md`](archive/future_journal_entry_ideas.md) | MVP shipped; expansion ideas for social-movement JEs |
| [`archive/event_inspiration.md`](archive/event_inspiration.md) | Historical economic / financial crises as event seeds |

## Auto-Generation Registry

[`auto_generated_files.md`](auto_generated_files.md) — canonical map of generator scripts → output files (mod data, docs, GFX). Read before hand-editing anything.

## Session Plans

| Path | Contents |
|------|----------|
| `superpowers/plans/` | Multi-step implementation plans authored by Claude Code via `/writing-plans`. Each plan is self-contained and dated. |

## Engine-Generated Logs (outside the repo)

These files are generated by running `script_docs` in the in-game console **without the mod loaded**, then copied to `~/src/vic3/docs/` (the vanilla snapshot path used by `mod_state_server`'s engine-doc loader). The compressed `.md` references in `engine/` are produced from these logs — read the raw `.log` files only when cross-referencing.

| File | Contents |
|------|----------|
| `event_targets.log` | All scope-to-scope accessors and value properties |
| `triggers.log` | Engine-canonical trigger documentation (raw source for `engine/vic3_triggers_effects_reference.md`) |
| `effects.log` | Engine-canonical effect documentation |
| `modifiers.log` | Engine-canonical modifier documentation (raw source for `engine/vic3_modifier_type_definitions_reference.md`) |
| `on_actions.log` | Engine-canonical on_actions documentation |
| `custom_localization.log` | Custom localization function documentation |
