# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A large content mod for **Victoria 3** (Paradox Clausewitz engine) that extends the timeline with new eras and systems (banking cycles, global warming, nuclear weapons, cultural hegemony, covert warfare, space race, strategic reserves, post-scarcity, etc.). The repo contains both:

1. **Mod data** — Paradox `.txt` script under `common/`, `events/`, `gui/`, `localization/`, `gfx/`, `map_data/`, plus `descriptor.mod` / `.metadata/`.
2. **Python tooling** — parsers, generators, balance solvers, and a long-running data server used to introspect the parsed mod + base game.

The repo lives in WSL; the engine reads files from a Windows-side mod folder. See **Deployment** below.

## Common commands

### Fresh-machine setup
- `python3 scripts/setup.py` — bootstraps the repo on a new machine: creates `.venv`, installs `requirements.txt`, autodetects (or prompts for) Steam install + Paradox docs folder + deploy target, and writes a gitignored `paths.local.json` consumed by `path_constants.py`. Re-runnable any time paths move.

### Running / using mod data
- **Deploy to the game** (rsync only the engine-required files into the Paradox mod directory):
  - Dry run: `./scripts/deploy.sh`
  - Apply: `./scripts/deploy.sh --apply`
  - Override target: `VIC3_MOD_DEPLOY_TARGET=/path/to/mod ./scripts/deploy.sh --apply`
- **Auto-deploy on edit** runs automatically when VS Code opens this workspace (`.vscode/tasks.json` → `scripts/watch_deploy_on_edit.sh`, uses `inotifywait` with a polling fallback).

### Mod state server (the primary lookup tool)
- Start: `.venv/bin/python mod_state_server.py` (listens on `http://127.0.0.1:8950`, ~60–110s startup). Auto-starts under VS Code. Use the venv Python — system `python3` is missing the `regex` package needed by `ig_feminism` (one of the post-load generators). **Claude has standing approval to start (and restart) the server without asking** — just announce in one short sentence before doing it. The server is the primary lookup tool, so anything that needs it should bring it up rather than work around its absence.
- Status check: `curl http://localhost:8950/status`. Returns engine-doc snapshot timestamps and pattern-catalog counts. **Always verify the server is running before doing game-data lookups.**
- Reload after editing mod files: `curl -X POST http://localhost:8950/reload`. After regenerating engine logs in-game with no mod-file changes: `curl -X POST 'http://localhost:8950/reload?engine_only=true'` (skips the slow ModState rebuild). Neither picks up Python source changes — restart the process for those. The reload response includes a `warnings` array if any audit (`modifier_visibility_audit`, `event_magnitude_audit`, `kill_character_audit`) surfaced actionable findings (`unreviewed > 0` / `hard_fails > 0`); the same warnings appear as `[post-load WARN]` lines in the server log. **Always check the warnings array after a /reload** before claiming a change is clean.
- CLI client: `python mod_state_client.py <command> [args]`.
- Full endpoint list: `docs/python_tools.md`. Highlights:
  - **Entity data**: `/laws`, `/technologies`, `/buildings`, `/production-methods`, `/journal-entries`, `/events`, `/decrees`, `/institutions`, `/script-values`, `/on-actions`, `/treaty-articles`, `/raw/<EntityType>[/<id>]`.
  - **Vocabularies (placeholder → values)**: `/vocabularies` (full map), `/vocabularies/<placeholder>`, plus `/cultures`, `/religions`, `/interest-groups`, `/law-groups`, `/building-groups`, `/pop-types`, `/country-ranks`, `/terrain`, `/discrimination-traits`. Backed by a regex disk fallback so Cultures and Terrain populate even when their files trip the parser.
  - **Modifier patterns**: `/modifier-patterns[?source=catalog|discovered|all]`, `/modifier-patterns/<pattern>` (members + missing vocab values), `/modifier-patterns?expand=<pattern>&<placeholder>=<value>`. Catalog seed at `common/_meta/modifier_patterns.yml`; auto-discovery extends it.
  - **Engine docs**: `/engine-docs/<type>` (effects, triggers, modifiers, event-targets, on-actions, custom-localization). `?group=true` on modifiers uses the §3 pattern catalog. Each entry has an `origin` field (`vanilla` if from the configured `vanilla_snapshot_docs_path`, `mod` if mod-only declared, with `defined_in` for mod entries). Vanilla entries the mod redeclares for cosmetics are tagged `mod_redeclares=true` (origin stays `vanilla` — engine semantics are vanilla's). Filter via `?origin=vanilla|mod`. **`/engine-docs/origin/<name>`** answers "where does this name come from" across all doc types — use it before assuming any modifier is engine-native.
  - **Vanilla snapshot**: the engine-doc data is read from `vanilla_snapshot_docs_path` (typically `~/src/vic3/docs/`), populated by running `script_docs` in the in-game console *without the mod loaded*. To refresh: launch vanilla, type `script_docs` at the console, copy outputs from `vanilla_docs_path` (the live engine docs folder) to `vanilla_snapshot_docs_path`. `/status.vanilla_snapshot` reports staleness (snapshot older than `vanilla_source_repo_path` HEAD commit) and contamination (mod-only `script_only` modifiers in the snapshot — means it was mod-loaded when generated).
  - **Validation**: `/validate/engine-coverage` walks every loaded mod entity and flags `unknown_modifiers` / `suspicious_modifiers` (pattern matched but placeholder not in vocab, with did-you-mean suggestions). Cross-references `error.log` lines as `confirmed_by_engine_log`. `/validate/modifier-visibility` flags modifier values too small to display given the type's `decimals = N` precision (silent "+0%" tooltips); see § "Validation rules that bite if ignored".
  - **Event balance**: `/event-balance/<id>` (or `?ids=` / `?prefix=` / `?file=`) expands each option's `add_modifier` and `add_enactment_modifier` effects and tags every field with its `color` good/bad/neutral plus a player-perspective polarity. `/event-balance/issues` audits the mod for dominated options — `?mode=strict` (default) flags pure-positive vs pure-negative pairs; `?mode=soft&threshold=N` (default 2) catches mixed-vs-mixed dominance on polarity counts. Always run after editing or adding a multi-option event. Append `?format=text` for skimmable output. The audit only sees modifier-field polarity, so verify flags against the source `.txt` — many false positives come from `add_treasury` / `add_momentum` / `change_variable` / `add_radicals` / scope-changes to rivals / scripted effects / `activate_law` / trigger-gated alternatives that the tool can't classify. See `docs/event_creation_guide.md` § Verifying Option Balance for the full list.
  - **Game logs**: `/logs` (index of error/debug/game/gui/etc. with rotated backups), `/logs/<family>?gen=N&q=&file=&source=&category=&since=&dedupe=&dedupe_key=&summary=&raw=&mod_only=&include_external=`, `/logs/<family>/diff?against=N` (what's new since last launch), `/logs/sessions` (cluster mtimes into runs). `include_external` defaults to `false` for `error`/`debug` and drops entries whose only file references are known third-party-mod sources (`statistics_effects.txt` from the Statistics mod). Set `?include_external=true` to see them.
  - **Search / lookup**: `/search?q=`, `/localize/<key>`, `/unlocalize/<text>`, `/references/<key>`, `/modifier-search?q=`, `/unlocked-by/<tech>`, `/technology-effects/<tech>`, `/tech-tree/<tech>`, `/dev-docs/...`.
- **Auto-generated docs** rebuilt on startup and `/reload` (do not hand-edit):
  - From mod data (`mod_state_script.py`): `docs/laws.txt`, `docs/technologies.txt`, `docs/buildings.txt`, `docs/goods.txt`, `docs/combat_units.txt`.
  - From engine docs (`engine_docs_render.py`): `docs/vic3_triggers_effects_reference.md`, `docs/vic3_modifier_type_definitions_reference.md`, `docs/triggers_summary.txt`, `docs/effects_summary.txt`, `docs/modifiers_summary.txt`, `docs/event_targets_summary.txt`, `docs/on_actions_summary.txt`, `docs/custom_localization_summary.txt`, `docs/triggers_parsed.txt`, `docs/country_triggers.txt`, `docs/modifier_patterns.md`.
  - From validation (`/validate/engine-coverage`): `docs/engine_coverage_report.md`.
  - From game logs (`game_log_reader.py`): `docs/error_log_digest.md` (mod-only summary + diff vs `error.1.log`).

### Python utilities (run from repo root)
- Tests for the parser: `python test_paradox_file_parser.py`
- Tab-normalize Paradox files: `python scripts/format_paradox_tabs.py [--check] common/path/to/file.txt ...` — only for brace-based `.txt`; never run on YAML/JSON/Python.
- Sort/clean localization: `python organize_loc.py`
- Localization YAML generation: `python scripts/generators/gen_loc_files.py`
- Production methods: `python pm_costs.py [--dry-run]`, `python scripts/analysis/pm_balance.py --inputs steel:11 --outputs services:1000 --profit 1000`
- Resource deposits from `deposits_config.json`: `python resources.py [--table]`
- Pop balance models: `python scripts/analysis/pop_growth.py [--plot]`, `python pop_needs_curves.py [--table]`
- Ideology attitudes: `python apply_ideologies.py [--dry-run]`
- Event scaffolding (auto-IDs, BOM, loc keys) — see `docs/python_tools.md` for spec format:
  - `python scripts/generators/gen_event.py next-id <namespace> --after N --count K`
  - `python scripts/generators/gen_event.py batch spec.json [--dry-run]`
  - `python scripts/generators/gen_event.py scaffold --namespace ... --title ... --desc ... --options ...`

The scripts that regenerate mod content from configs + vanilla data — `pop_needs_curves.py`, `apply_ideologies.py`, `ig_feminism.py`, `pm_costs.py`, `resources.py`, `gen_pb_principle_unlock_descs.py`, `gen_un_button_descs.py`, `gen_law_consistency.py`, `organize_loc.py`, `event_magnitude_audit.py`, `gen_event_inventory.py` — also auto-run inside `mod_state_server.py` after every full `/reload` (the server logs `[post-load] <name> ok (Xs)`). The current canonical list lives in `POST_LOAD_GENERATORS` in `mod_state_server.py`. Standalone CLIs remain available for manual / dry-run use. Set `VIC3_SKIP_POST_LOAD_GENERATORS=1` to disable the auto-run while iterating on one of those scripts. The auto-run does **not** fire on `/reload?engine_only=true`.

### Dependencies
`.venv/bin/pip install -r requirements.txt`. Core (`requests`, `pyyaml`, `regex`, `numpy`) is required for `mod_state_server.py` plus its post-load generators. The image-generation pipeline (`torch`/`diffusers`/etc.) stays commented out by default. Always run server-touching commands through `.venv/bin/python` so the post-load generators can resolve their deps; `python3` (system) is acceptable for one-off CLI scripts but not for the server.

## Where things live

### Paths
`path_constants.py` is the canonical source for repo and Paradox paths and is imported by nearly every Python tool:
- `mod_path` — this repo
- `base_game_path` — vanilla Victoria 3 install (`/mnt/c/Program Files (x86)/Steam/.../Victoria 3`)
- `mod_deploy_target` — Paradox mod directory rsync writes to
- `vanilla_docs_path` — engine-generated docs (`event_targets.log`, `triggers.log`, `effects.log`, `modifiers.log`, `on_actions.log`, `custom_localization.log`)
- `game_logs_path` — runtime `error.log` / `debug.log`

### Data layout
- `common/` — every Paradox entity type (laws, technologies, buildings, journal_entries, on_actions, scripted_effects, scripted_triggers, scripted_buttons, scripted_progress_bars, scripted_guis, script_values, static_modifiers, modifier_type_definitions, treaty_articles, decrees, decisions, ideologies, interest_groups, …). The `mod_state_server` parses ALL of these from both vanilla and the mod.
- `events/` — event scripts (one file per system: `banking_cycle_events.txt`, `space_race_events.txt`, etc.).
- `gui/` — overridden / extended panels (e.g. `states_panel.gui`, `production_methods.gui`, `building_browser_panel.gui`).
- `localization/english/` — `*_l_english.yml` files.
- `gfx/`, `map_data/` — assets.
- `docs/` — design docs, generated reference files, reading guide in `docs/README.md`. See it before deep diving — many docs are AI-agent-targeted.

## High-level architecture

### How the mod is composed
The mod is a layered set of independent **systems**, most of which follow the same building blocks:

1. **A journal entry** in `common/journal_entries/je_*.txt` that drives the system's UI/state.
2. **A scripted progress bar** (`common/scripted_progress_bars/`) and a set of **scripted buttons** (`common/scripted_buttons/`) for player interaction.
3. **Scripted effects + triggers** (`common/scripted_effects/`, `common/scripted_triggers/`) holding the system's logic, often parameterized with `$GOOD$`/`$TYPE$`/`$RANK$` placeholders (see `docs/scripting_best_practices.md`).
4. **Static modifiers** in `common/static_modifiers/extra_modifiers.txt` representing tunable per-unit effects.
5. **Script values** in `common/script_values/extra_script_values.txt` (and topic-specific files like `tourism.txt`) that compute multipliers consumed by `add_modifier { multiplier = ... }`.
6. **On-actions** in `common/on_actions/` wiring monthly/yearly pulses, election cycles, etc.
7. **Events** in `events/<system>_events.txt` plus a localization YAML in `localization/english/`.
8. **Modifier type definitions** in `common/modifier_type_definitions/` registering any dynamic-pattern modifiers (`building_*`, `goods_*`, `state_building_*`).

### Dynamic modifier pattern (used widely)
A recurring idiom: define a static modifier with unit values (e.g. `state_migration_pull_mult = -0.1`), then in an `on_yearly_pulse_*` re-apply it as `add_modifier = { name = X multiplier = <script_value> }`. The engine multiplies every field by the multiplier each tick. Used by global warming, construction-cost scaling, migration crowding, excess private construction, tourism, and others. State-scoped scaling **must** run from `on_yearly_pulse_state` because the engine evaluates the multiplier in the calling scope chain (law/treaty/building hooks have unreliable scope chains for state-targeted script values). See `docs/mod_systems.md` and `docs/scripting_best_practices.md`.

### Game rules (toggleable systems)
`common/game_rules/` and `descriptor.mod` expose toggles for the major systems (Banking Cycle default ON, Global Warming default ON, World War default OFF). When disabled, the journal entry doesn't appear but related laws/events still provide their non-system effects. See `README.md`.

### Python tooling spine
- `paradox_file_parser.py` — tokenizer + recursive-descent parser for Paradox `.txt` files. Handles `REPLACE:`/`INJECT:` merge directives, BOM, comments, brace nesting. The parser is unit-tested (`test_paradox_file_parser.py`).
- `mod_state.py` — `ModState` class wrapping the parser; loads vanilla + mod data, builds reverse-localization index, exposes `localize`/`unlocalize`/`search_localization`. Bulk Python generators should `from mod_state import ModState` directly rather than going through HTTP.
- `mod_state_server.py` — long-running HTTP service over `ModState` (port 8950). Logs to console (INFO) and `mod_state_server.log` (DEBUG). Events, scripted_effects, scripted_triggers, on_actions are **mod-only**; everything else is mod ∪ vanilla.
- `mod_state_script.py` — regenerates the `docs/*.txt` reference files (also runs on server start/reload).
- `mod_state_client.py` — thin CLI over the server.
- One-shot scaffolders live under `scripts/generators/` (`gen_event.py`, `gen_loc_files.py`, `gen_banking_events.py`, `gen_vanilla_company_buildings.py`, `assimilation_cultures.py`, `add_tech_modifiers.py`, etc.). Image / video pipelines live under `scripts/image_pipeline/` (`gen_image.py`, `gen_pm_icons.py`, `gen_law_icons.py`, `gen_aptitude_icons.py`, `convert_event_image.py`, etc.). Math / CLI tools live under `scripts/analysis/` (`pop_growth.py`, `pm_balance.py`).

## Working in this repo

### Read the docs before scripting
`docs/README.md` is the index. The docs most likely to matter:
- `docs/scripting_best_practices.md` — modifier validation, `days` vs `months` units, scope chain pitfalls, expense scaling, registration of dynamic modifier types, `any_` triggers don't take `limit`, modifier-after-effect read ordering, scripted-trigger/effect catalog. Also: `authority` vs `produced_authority` triggers, the inverse-`country_authority_mult` cost-compensation pattern, and the script-only-modifier-as-cross-system-tag pattern (`country_banking_intervention_max_add`, `country_legislative_override_capacity_add`) for gating events on combinations of laws/techs/decrees while staying visible in player tooltips.
- `docs/event_creation_guide.md` — boilerplate, available videos/icons, IG approval modifiers, `on_yearly_events` wiring, style. Also: AI-weight pitfalls for authority-spending options, and the difference between amenability (IGs willing to talk) vs `country_law_enactment_success_add` / `country_law_enactment_stall_mult` / `add_enactment_phase` (mechanics that actually push a law through).
- `docs/vanilla_economy_reference.md` — concept primer on vanilla Vic3 economy (pops + buy packages, ownership / Investment Pool, market access / MAPI, companies & charters, power-bloc principles, 1.13 naval economy). Read before touching mod content that hooks the vanilla economy if you don't already have the mental model. Carries a "Last verified against vanilla: X" banner — refresh it on every vanilla bump per `docs/vanilla_patch_runbook.md` § 8b.
- `docs/mod_systems.md` — every gameplay system's files and mechanics.
- `docs/journal_entry_systems.md` — the 10+ JE systems in detail.
- `docs/python_tools.md` — full server endpoint list and AI-agent workflow.
- `docs/gui_modding_guide.md` — when touching `gui/`.
- `docs/treaty_articles_reference.md`, `docs/wonder_buildings_reference.md`, `docs/vanilla_company_buildings_reference.md` — patterns for those systems.

### Validation rules that bite if ignored
- The Clausewitz engine **silently ignores invalid modifier names**. Validate via `/modifier-search?q=` or `/engine-docs/modifiers?q=` before introducing one. Known-bad names are listed in `docs/scripting_best_practices.md`.
- **Boolean modifier types must be explicitly declared in `common/modifier_type_definitions/`** — there is no auto-registration from PM use or `modifier:NAME = yes` triggers. Undeclared booleans silently no-op (PMs apply nothing, triggers always evaluate false). `/validate/engine-coverage` now covers booleans (`_bool` / `_boolean` suffix) and `modifier:NAME` trigger references; see `docs/scripting_best_practices.md` § "Boolean Modifier Types Must Be Explicitly Declared" for the country_sr_*_program_bool incident this rule was learned from.
- Dynamic modifier patterns (`building_<name>_throughput_add`, `goods_output_<good>_mult`, `state_building_<name>_max_level_add`, `ship_battle_against_ship_type_<ship>_<accuracy|hull_damage>_<add|mult>`, etc.) require **per-entity registration** in `common/modifier_type_definitions/mod_entity_modifier_types.txt` for any modded building/good/ship type (mod-mechanic knobs go in their own per-system file in the same directory — see `docs/scripting_best_practices.md` § "Where New Registrations Go"). Without registration the modifier silently no-ops. Note that vanilla also only auto-registers *specific axis combinations* per entity (e.g. `ship_type_submarine` gets `_accuracy_*` but NOT `_hull_damage_mult`; `ship_type_dreadnought` gets `_hull_damage_mult` but NOT `_accuracy_mult`) — even when targeting a vanilla type, the specific combo you want may need its own mod-side registration.
- Time units: `short_modifier_time` / `normal_modifier_time` / `long_modifier_time` / `very_long_modifier_time` are in **days**. Always `days = ...`, never `months = ...` (off by 30×).
- `any_*` triggers do NOT accept a `limit = { }` block — siblings only. `limit` is for effect iterators (`every_*`, `random_*`, `ordered_*`).
- `add_modifier` / `remove_modifier` results are not visible inside the same effect block. To recompute a modifier from "base" values, store the prior contribution as a variable and subtract it from the `modifier:X` read. Examples: `prior_pollution_reduction`, `intel_shield_mult`.
- State-scoped script-value updates that traverse `state_region` should be wired to `on_yearly_pulse_state`, not `on_law_activated` / `on_acquired_technology` / treaty entry hooks (broken parent scope chain).
- **Modifier stacking is additive across all sources.** Both `_add` and `_mult` modifiers from different sources (buildings, PMs, traits, laws, events) **sum**, they do not multiply. So a per-building `country_X_mult = -0.02` becomes `-2.0` (200% reduction) when 100 instances of the building exist — pathological. Per-building modifiers in `country_modifiers = { workforce_scaled = { ... } }` blocks must be `_add` with small values, OR use country-scope `_mult` only in places that are applied once (event-applied static modifiers, law modifiers, power-bloc member_modifier). When migrating a removed `_add` modifier, do NOT translate it 1:1 to a `_mult`; either find an `_add` analog or drop the per-building bonus entirely.
- **Top-level entity collisions get silently dropped.** If a mod file declares a top-level key vanilla already owns (`clothes`, a vanilla modifier name, etc.), `debug.log` says `Duplicated key X will not be created` and the mod's whole block is ignored. Use `INJECT:X = { ... }` to extend rather than redeclare. See `docs/scripting_best_practices.md` § "Top-Level Database Collisions".
- **Global variables read by JE `possible` clauses must be initialized in `on_game_started`.** A `possible` block evaluates at game start, before any `on_*_pulse_*` fires. If it reads `global_var:foo` that doesn't exist yet, debug.log shows `Got value of type 'none'` and the JE silently fails to surface. Wire initialization through `on_game_started = { on_actions = { my_init_action } }` (extension form — never `effect = { }`, which clobbers vanilla's body). See `docs/scripting_best_practices.md` § "Global Variable Initialization Timing".
- **Symmetric existence ≠ symmetric activation in the vanilla modifier catalog.** Many vanilla modifiers exist as 0-baseline opt-in *levers* — the modifier is in the catalog, but its default value is 0 and the mechanic only activates when something moves it positive. Example: `state_academics_investment_pool_contribution_add` exists alongside the capitalists/aristocrats counterparts, but academics don't contribute to IP at baseline; the post-scarcity law deliberately moves it up to enable academic IP feed. Treating "modifier exists" as "mechanism is active by default" leads to wrong claims about vanilla. When auditing, check both *existence* and *baseline value*. Cross-reference: `docs/vanilla_economy_reference.md` § 10.2.
- **Modifier values must clear the type's `decimals` rounding threshold.** Each modifier type declares `decimals = N` (and often `percent = yes`) in `common/modifier_type_definitions/`. ~37% of vanilla types are `decimals = 0`; with `percent = yes` (e.g. `country_prestige_mult`) any |value| below 0.005 displays as "+0%" while still applying mechanically — silently invisible. The `modifier_visibility_audit.py` (endpoint `/validate/modifier-visibility`, report `docs/modifier_visibility_report.md` regenerated on `POST /reload`) flags every literal sub-threshold value across `events/*.txt` and `common/**/*.txt`. Two fix paths: (1) bump the value above the threshold (preferred — small-by-design effects probably aren't doing what you intended), or (2) override the modifier type's `decimals` in `common/modifier_type_definitions/`. Suppress an intentional flag with an inline `# REVIEWED YYYY-MM-DD: rationale` comment on the value line.
- **Fast-scaling resources require scaled event effects.** Hardcoded prestige / treasury / bureaucracy / construction deltas in events go invisible at late-game scale (a `multiplier = -20` is 0.012% of 163k prestige). The `event_magnitude_audit.py` (endpoint `/event-magnitude-audit`, report `docs/event_magnitude_report.md` regenerated on `POST /reload`) flags every hardcoded fast-scaling value in `events/*.txt` and recommends the appropriate scaled fix path (mult-based static modifier like `prestige_loss_<tier>`, or `multiplier = sv_<resource>_event_<tier>` script value). Suppress an intentional flag with an inline `# REVIEWED YYYY-MM-DD: rationale` comment on the value line. See `docs/scripting_best_practices.md` § "Audit + library for fast-scaling event effects" for the full registry and tier ladder.
- **Distinguish flat enable costs from metered flows.** Vanilla resource costs come in at least three shapes: (1) **flat enable cost / reservation** — pay a fixed amount that stays reserved while a feature is on, freed when off. Authority is the dominant home for this shape: `consumption_tax_cost` per taxed good (typically 100–500), decrees (100 each for most while the decree is active in a state), state monopolies, IG bolster/suppress (200 each while active), corporate charters above the slot limit (100 each). All are flat-while-on, not metered. (2) **metered flow** — pay continuously in proportion to a runtime quantity (most goods inputs, wages). (3) **one-shot** — pay once at the action (build cost, certain event-applied costs). Mistaking shape (1) for shape (3) ("one-shot decree cost") under-counts ongoing Authority pressure. Mistaking (1) for (2) ("Authority drains with consumption volume") over-couples the cost to runtime activity. When describing or designing a cost, name the shape. Cross-reference: `docs/vanilla_economy_reference.md` § 11.2 and § 12.2.

### Triage workflow for log issues
**Look at `debug.log` first, not `error.log`.** Vic3's `error.log` only contains a small subset of the engine's diagnostic output (mostly script-value type errors). The real signal — `script_parse_error`, `Unknown modifier type`, `Duplicated key`, `inject/replace to a non-existing entry`, `Unknown trigger type`, `Got value of type 'none'`, missing-texture warnings — lives in `debug.log`.

Use the categorized digest:
```bash
curl -s "http://localhost:8950/logs/debug?summary=false&dedupe=true" | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'{e[\"category\"]} | {(e[\"files\"] or [\"?\"])[0]} | {e[\"message\"][:200]}') for e in d['entries']]"
```

Common categories to triage:
- `script_parse_error` — broken token (vanilla rename), unknown modifier (registration missing), unknown trigger (typo or rename).
- `inject_to_missing` — vanilla renamed/removed the INJECT: target. Check `docs/vanilla_patch_runbook.md` § "Known vanilla renames".
- `duplicated_key` — top-level entity collision; convert mod's declaration to `INJECT:`.
- `missing_file` — referenced asset (usually `gfx/event_pictures/*.dds`) doesn't exist; substitute with a thematically similar existing asset or remove the reference.
- `dds_dimensions` — image not multiple of 4; non-blocking visual warning, fixable only by re-exporting the DDS.

Vanilla-file errors (e.g. `headlines_on_actions.txt`, `command_values.txt`) are not the mod's problem — record them in `docs/vanilla_known_bugs.md` and skip.

**Third-party-mod errors slip past `mod_only=true`.** The mod-only filter accepts any entry whose message references a `common/.../*.txt` path, regardless of which mod loaded that file — so log spam from workshop mods loaded alongside this one (Statistics, etc.) looks like our own errors. The `?include_external=` filter on `/logs/<family>` (default `false` for error/debug) drops entries whose only file references are in `EXTERNAL_MOD_SOURCE_FILES` in `game_log_reader.py`. **When a new third-party mod starts emitting noise, extend that set** — and include all paired files, not just the apparent root cause: `jomini_script_system` errors emit one entry referencing both the script-effect file and the on-action call-site, so dropping the entry requires both basenames in the set. Set `?include_external=true` to see what's being filtered.

### System-scope cheat sheet
Where a given modifier or trigger can be used:
- **`mobilization_options/*`** `unit_modifier`: armies only. Don't use `military_formation_fleet_*` or `ship_*` modifiers here.
- **Tech `modifier = { ... }`** (in `common/technology/technologies/`): country-scope. `character_*` modifiers **appear to work in tech scope as of 1.13** — the engine cascades them to every character belonging to the country. Verified empirically: `character_popularity_add` from a tech applies to all of the country's characters. Earlier in development this was a silent no-op, which explains workarounds elsewhere in this codebase. New uses should still verify with a quick in-game test the first time, since not every char-scope modifier may have been wired through. `ship_*` modifiers DO work in tech scope and apply as a country-wide buff to all ships (vanilla `paddle_steamer` uses `ship_hull_damage_mult` / `ship_crew_damage_mult` from a tech `modifier` block; `ship_battle_against_ship_type_*` patterns also work). Use `country_*`, `state_*`, `unit_*`, `building_*`, `ship_*`, `character_*` (verified empirically; verify new ones), or pre-defined country booleans (`country_<feature>_pb_principles_bool`) that are read elsewhere.
- **Power bloc `member_modifier` / `leader_modifier`**: country-scope. `character_*` modifiers cascade to all the country's characters.
- **Static modifiers (`common/static_modifiers/`)**: any scope's modifiers — but the static modifier must be applied at a matching scope (country / state / character).
- **`INJECT:` / `REPLACE:` / `REPLACE_OR_CREATE:` directive prefixes** on entity keys (e.g. `INJECT:building_shipyard = { ... }`) are **engine-native** in Vic3 (Clausewitz). The mod uses them throughout. They merge or replace into the matching vanilla entity at load time. Don't try to "expand" them in tooling.

### Audit and research workflow

When researching mod content (auditing for bugs, inventorying which PMs produce/consume a good, mapping a system across files), a few patterns are reliable and a few are surprisingly broken.

- **Use awk, not `grep -B/-A`, to find which block contains a line.** Paradox brace-nested files (PMs, buildings, laws, etc.) routinely have blocks larger than 40 lines. Running `grep -B40 'goods_output_X' file | grep '^pm_'` reads *across* PM boundaries and mis-attributes — you pick up the previous PM's header for a match deep inside another PM. Use `awk` with a state variable instead:

  ```bash
  awk '/^pm_|^REPLACE:pm_/{cur=$0} /goods_output_X/{print cur}' file | sort -u
  ```

  Track the current block as state, emit it when the marker hits. Reliable regardless of block size. The same pattern works for any header-marker pair: replace the headers with `^building_`, `^law_`, etc. as needed.

- **Verify subagent claims by reading the cited file before acting.** Subagent counts ("91 PMs consume X") are easy to re-verify and usually correct; subagent *attribution* claims ("X is consumed by construction sectors") often aren't, especially when the claim hinged on `grep -B/-A` interpretation or specific line numbers. When a critical finding is on the line of "fix this immediately", do the spot-check first. A few minutes of `Read`/`grep` saves a wrong fix.

- **Engine validation catches naming, not semantics.** `mod_state_server`'s `/validate/engine-coverage` (and `docs/engine_coverage_report.md`) reports unknown/suspicious modifier *names*. It does **not** catch: modifiers whose default value is 0 and need explicit activation; per-building `_mult` modifiers in `workforce_scaled` blocks that go pathological at scale; cost-shape mismatches (treating a flat enable cost as a metered flow). Audits looking for those need to read the code, not just check the coverage report.

- **For Paradox files, `grep -rn "^xxx = "` shows top-level definitions reliably.** The same trick doesn't work inside nested blocks because indented lines lose the anchor. For nested searches, use the awk pattern above.

- **PMs in different groups within a building SUM additively.** When auditing a building's net effect, sum across all active PMs from all groups — they don't cancel or override each other. See `docs/vanilla_economy_reference.md` § 2.

### Recording lessons learned
When you (Claude or future Claude instances) discover something generally applicable — a working trigger syntax, an engine quirk, a refactor pattern, a tool behavior, a validation rule that bites — write it into the appropriate doc in the same session, don't let it die in conversation history. Natural homes:
- Engine syntax, scope rules, modifier validation, scripting gotchas → `docs/scripting_best_practices.md`
- Refactor patterns and the helper inventory → `docs/script_parameterization_audit.md`
- Mod-state-server / tooling behavior → `docs/python_tools.md`
- Cross-cutting workflow notes → this file (`CLAUDE.md`)
- Per-helper context (parameters, scope contract, edge cases) → the helper's own comment header in `common/scripted_*/`.

`docs/` is tracked in the repo, so additions there propagate to fresh clones. The exception is `docs/error_log_digest.md`, which reflects the local game's runtime `error.log` and is gitignored. Don't repeat the same lesson in multiple homes — pick the natural one and link from the others.

Keep additions short — one paragraph or a bullet, not a treatise. The bar is: would the next Claude instance hit the same gotcha or solve the same problem from scratch without this note? If yes, write it down.

### Editing conventions
- Brace-based Paradox files use **tab** indentation. After large edits run `python scripts/format_paradox_tabs.py <files>` (or `--check` in CI-style flows).
- After editing mod files, `POST /reload` to refresh the server's view (the auto-deploy watcher will already have synced files into the Paradox mod folder).
- Localization keys: prefer adding to existing `*_l_english.yml` files and run `python organize_loc.py` to sort and detect unused keys.
- Don't hand-edit auto-generated files. **Always edit the generator's input and re-run the generator.** The idempotent transformers below also auto-run on every mod state server reload (see `POST_LOAD_GENERATORS` and `_run_post_load_generators` in `mod_state_server.py`); manual invocation is still useful for `--dry-run`. Authoritative ownership map (also in `docs/auto_generated_files.md`):
  - `common/ideologies/modified.txt` — owned by `apply_ideologies.py`; input is `ideology_modifications.py` plus vanilla ideology files. Re-run after vanilla updates to pick up new vanilla content (e.g. patches that add new laws or change attitudes).
  - `common/interest_groups/00_*.txt` (8 files) — owned by `ig_feminism.py`.
  - `common/buy_packages/00_buy_packages.txt` — owned by `pop_needs_curves.py`.
  - `common/production_methods/extra_pms.txt` & `unique_pms.txt` cost-comment headers + `commented_vanilla_military_units.txt` — owned by `pm_costs.py`.
  - `map_data/state_regions/*.txt` — owned by `resources.py`; input is `deposits_config.json` plus vanilla `game/map_data/state_regions/`. After a vanilla map change, update `deposits_config.json` to point old/removed states at successors and re-run.
  - `localization/english/te_*_l_english.yml` (~26 category files as of 2026-05; grows with new content families) — owned by `organize_loc.py`; categorises and sorts every key. Add new category prefixes to `categorize_key` (e.g. the `ship_type_*` / `utility_mod_*` rules) when introducing whole new content families, otherwise the keys land in MISCELLANEOUS.
  - `localization/english/te_power_bloc_unlocks_l_english.yml` — *_pb_principles_bool_desc keys are owned by `gen_pb_principle_unlock_descs.py`; short-label keys (without `_desc`) are preserved verbatim and co-located in this file via the `POWER_BLOC_UNLOCKS` rule in `organize_loc.py`. Inputs are `common/power_bloc_principles/extra_power_bloc_principles.txt` (each principle's `possible` clause) and `common/modifier_type_definitions/tech_gate_modifier_types.txt` (the defined unlock booleans).
  - `common/scripted_effects/extra_law_consistency_generated.txt` — owned by `gen_law_consistency.py`. Inputs: every law file (vanilla + mod) for `unlocking_laws`/`disallowing_laws`/`group`/`progressiveness`, plus ideology attitude data (vanilla `common/ideologies/*.txt` + the `modifications` dict in `ideology_modifications.py`). Emits one helper scripted effect per lawgroup that has any law with cross-group constraints, plus the `te_fix_inconsistent_laws` dispatcher (called from `on_law_activated` and `on_monthly_pulse_country` in `extra_on_actions.txt`). When a country has an active law whose `unlocking_laws`/`disallowing_laws` are violated, the helper switches it to the in-group alternative closest by progressiveness, with ideology-attitude similarity as the tiebreak. To rerank lawgroup priority, edit `LAWGROUP_PRIORITY` at the top of the generator. Note: tech-based reversion (e.g. post-scarcity → UBI when bankrupt) lives separately in the hand-written `fix_incompatible_laws` scripted effect — don't fold those cases into the generator.
  - `localization/english/te_un_button_effects_l_english.yml` — `UN_*_EFFECTS` keys are owned by `gen_un_button_descs.py`. The corresponding `UN_*_DESC` keys (hand-written, in te_miscellaneous/te_concepts) reference these via `$..._EFFECTS$` so the volatile mechanical text (modifier values + un_authority deltas) stays auto-synced. Inputs are `common/scripted_buttons/un_buttons.txt` (each button's effect block) and `common/static_modifiers/extra_modifiers.txt` (modifier values). The `UN_BUTTON_EFFECTS` rule in `organize_loc.py` routes the keys to this file. Add a button to `IN_SCOPE_BUTTONS` in the generator to expand coverage.
  - `docs/laws.txt`, `docs/technologies.txt`, `docs/buildings.txt`, `docs/goods.txt`, `docs/combat_units.txt` — owned by `mod_state_script.py`; rebuilt automatically on `POST /reload`.
  - `docs/vic3_*_reference.md`, `docs/triggers_summary.txt`, `docs/effects_summary.txt`, etc. — owned by `engine_docs_render.py`.
  - `docs/engine_coverage_report.md` — owned by `mod_state_server.py /validate/engine-coverage`.
  - `docs/error_log_digest.md` — owned by `game_log_reader.py`.
  - `docs/event_magnitude_report.md` — owned by `event_magnitude_audit.py`; auto-rebuilt by the post-load chain.
  - `docs/modifier_visibility_report.md` — owned by `modifier_visibility_audit.py`; auto-rebuilt by the post-load chain. Inputs are `engine_docs['modifiers']` (decimals + percent annotated by `_union_vanilla_modifier_decimals` / `_union_mod_modifier_types` in `mod_state_server.py`) plus every `.txt` file under `events/` and `common/` (excluding subdirs that don't contain modifier uses: `modifier_type_definitions`, `script_values`, `scripted_triggers`, `pop_needs`, etc.).
  - `docs/event_image_inventory.md` — owned by `gen_event_inventory.py`; auto-rebuilt by the post-load chain. Inventory of every mod event's title/description/flavor/image, used by the custom event-image pipeline.
  - Files produced by `gen_*.py` scripts may or may not be auto-managed. If a file's first 5 lines contain `# AUTO-GENERATED` or `do not edit manually`, treat it as owned. Otherwise, it's a one-shot generator output that's been committed; check the script to decide.
  - Quick check: `git grep -l "AUTO-GENERATED\|do not edit manually" common/ map_data/ localization/`.
- Use `python3` on this system (no `python` alias). The README/CLAUDE.md `python <script>.py` invocations all work as `python3 <script>.py`.

## Deployment topology
- This repo lives on the WSL/Linux side (the configured `mod_path`, e.g. `~/src/Vic3TimelineExtended`).
- The engine reads from the Windows-side mod folder (the configured `mod_deploy_target`, e.g. `/mnt/c/Users/<winuser>/OneDrive/Documents/Paradox Interactive/Victoria 3/mod/Vic3TimelineExtended`).
- `scripts/deploy.sh` rsyncs only `common/`, `events/`, `localization/`, `gui/`, `gfx/`, `map_data/`, `.metadata/`, `descriptor.mod`, `thumbnail.png`. Everything else (Python, docs, tests, `.git`, logs) stays in the repo.
- The auto-deploy watcher runs that rsync continuously while VS Code is open; manual edits via other editors will not auto-deploy.
