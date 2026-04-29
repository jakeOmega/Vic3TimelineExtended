# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A large content mod for **Victoria 3** (Paradox Clausewitz engine) that extends the timeline with new eras and systems (banking cycles, global warming, nuclear weapons, cultural hegemony, covert warfare, space race, strategic reserves, post-scarcity, etc.). The repo contains both:

1. **Mod data** — Paradox `.txt` script under `common/`, `events/`, `gui/`, `localization/`, `gfx/`, `map_data/`, plus `descriptor.mod` / `.metadata/`.
2. **Python tooling** — parsers, generators, balance solvers, and a long-running data server used to introspect the parsed mod + base game.

The repo lives in WSL; the engine reads files from a Windows-side mod folder. See **Deployment** below.

## Common commands

### Running / using mod data
- **Deploy to the game** (rsync only the engine-required files into the Paradox mod directory):
  - Dry run: `./scripts/deploy.sh`
  - Apply: `./scripts/deploy.sh --apply`
  - Override target: `VIC3_MOD_DEPLOY_TARGET=/path/to/mod ./scripts/deploy.sh --apply`
- **Auto-deploy on edit** runs automatically when VS Code opens this workspace (`.vscode/tasks.json` → `scripts/watch_deploy_on_edit.sh`, uses `inotifywait` with a polling fallback).

### Mod state server (the primary lookup tool)
- Start: `python mod_state_server.py` (listens on `http://127.0.0.1:8950`, ~50s startup). Auto-starts under VS Code.
- Status check: `curl http://localhost:8950/status`. Returns engine-doc snapshot timestamps and pattern-catalog counts. **Always verify the server is running before doing game-data lookups.**
- Reload after editing mod files: `curl -X POST http://localhost:8950/reload`. After regenerating engine logs in-game with no mod-file changes: `curl -X POST 'http://localhost:8950/reload?engine_only=true'` (skips the slow ModState rebuild). Neither picks up Python source changes — restart the process for those.
- CLI client: `python mod_state_client.py <command> [args]`.
- Full endpoint list: `docs/python_tools.md`. Highlights:
  - **Entity data**: `/laws`, `/technologies`, `/buildings`, `/production-methods`, `/journal-entries`, `/events`, `/decrees`, `/institutions`, `/script-values`, `/on-actions`, `/treaty-articles`, `/raw/<EntityType>[/<id>]`.
  - **Vocabularies (placeholder → values)**: `/vocabularies` (full map), `/vocabularies/<placeholder>`, plus `/cultures`, `/religions`, `/interest-groups`, `/law-groups`, `/building-groups`, `/pop-types`, `/country-ranks`, `/terrain`, `/discrimination-traits`. Backed by a regex disk fallback so Cultures and Terrain populate even when their files trip the parser.
  - **Modifier patterns**: `/modifier-patterns[?source=catalog|discovered|all]`, `/modifier-patterns/<pattern>` (members + missing vocab values), `/modifier-patterns?expand=<pattern>&<placeholder>=<value>`. Catalog seed at `common/_meta/modifier_patterns.yml`; auto-discovery extends it.
  - **Engine docs**: `/engine-docs/<type>` (effects, triggers, modifiers, event-targets, on-actions, custom-localization). `?group=true` on modifiers uses the §3 pattern catalog.
  - **Validation**: `/validate/engine-coverage` walks every loaded mod entity and flags `unknown_modifiers` / `suspicious_modifiers` (pattern matched but placeholder not in vocab, with did-you-mean suggestions). Cross-references `error.log` lines as `confirmed_by_engine_log`.
  - **Event balance**: `/event-balance/<id>` (or `?ids=` / `?prefix=` / `?file=`) expands each option's `add_modifier` and `add_enactment_modifier` effects and tags every field with its `color` good/bad/neutral plus a player-perspective polarity. `/event-balance/issues` audits the mod for dominated options — `?mode=strict` (default) flags pure-positive vs pure-negative pairs; `?mode=soft&threshold=N` (default 2) catches mixed-vs-mixed dominance on polarity counts. Always run after editing or adding a multi-option event. Append `?format=text` for skimmable output. The audit only sees modifier-field polarity, so verify flags against the source `.txt` — many false positives come from `add_treasury` / `add_momentum` / `change_variable` / `add_radicals` / scope-changes to rivals / scripted effects / `activate_law` / trigger-gated alternatives that the tool can't classify. See `docs/event_creation_guide.md` § Verifying Option Balance for the full list.
  - **Game logs**: `/logs` (index of error/debug/game/gui/etc. with rotated backups), `/logs/<family>?gen=N&q=&file=&source=&category=&since=&dedupe=&dedupe_key=&summary=&raw=&mod_only=`, `/logs/<family>/diff?against=N` (what's new since last launch), `/logs/sessions` (cluster mtimes into runs).
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
- Localization YAML generation: `python gen_loc_files.py`
- Production methods: `python pm_costs.py [--dry-run]`, `python pm_balance.py --inputs steel:11 --outputs services:1000 --profit 1000`
- Resource deposits from `deposits_config.json`: `python resources.py [--table]`
- Pop balance models: `python pop_growth.py [--plot]`, `python pop_needs_curves.py [--table]`
- Ideology attitudes: `python apply_ideologies.py [--dry-run]`
- Event scaffolding (auto-IDs, BOM, loc keys) — see `docs/python_tools.md` for spec format:
  - `python gen_event.py next-id <namespace> --after N --count K`
  - `python gen_event.py batch spec.json [--dry-run]`
  - `python gen_event.py scaffold --namespace ... --title ... --desc ... --options ...`

### Dependencies
`pip install -r requirements.txt` (only `requests` is required for the core tooling; the image-generation pipeline pulls in `torch`/`diffusers`/etc. and is commented out by default).

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
- Generators (`gen_event.py`, `gen_loc_files.py`, `gen_pm_icons.py`, `gen_law_icons.py`, `gen_aptitude_icons.py`, `gen_vanilla_company_buildings.py`, `gen_banking_events.py`, etc.) consume parsed `ModState` data and emit Paradox `.txt` / YAML / DDS.

## Working in this repo

### Read the docs before scripting
`docs/README.md` is the index. The docs most likely to matter:
- `docs/scripting_best_practices.md` — modifier validation, `days` vs `months` units, scope chain pitfalls, expense scaling, registration of dynamic modifier types, `any_` triggers don't take `limit`, modifier-after-effect read ordering, scripted-trigger/effect catalog. Also: `authority` vs `produced_authority` triggers, the inverse-`country_authority_mult` cost-compensation pattern, and the script-only-modifier-as-cross-system-tag pattern (`country_banking_intervention_max_add`, `country_legislative_override_capacity_add`) for gating events on combinations of laws/techs/decrees while staying visible in player tooltips.
- `docs/event_creation_guide.md` — boilerplate, available videos/icons, IG approval modifiers, `on_yearly_events` wiring, style. Also: AI-weight pitfalls for authority-spending options, and the difference between amenability (IGs willing to talk) vs `country_law_enactment_success_add` / `country_law_enactment_stall_mult` / `add_enactment_phase` (mechanics that actually push a law through).
- `docs/mod_systems.md` — every gameplay system's files and mechanics.
- `docs/journal_entry_systems.md` — the 10+ JE systems in detail.
- `docs/python_tools.md` — full server endpoint list and AI-agent workflow.
- `docs/gui_modding_guide.md` — when touching `gui/`.
- `docs/treaty_articles_reference.md`, `docs/wonder_buildings_reference.md`, `docs/vanilla_company_buildings_reference.md` — patterns for those systems.

### Validation rules that bite if ignored
- The Clausewitz engine **silently ignores invalid modifier names**. Validate via `/modifier-search?q=` or `/engine-docs/modifiers?q=` before introducing one. Known-bad names are listed in `docs/scripting_best_practices.md`.
- Dynamic modifier patterns (`building_<name>_throughput_add`, `goods_output_<good>_mult`, `state_building_<name>_max_level_add`, `ship_battle_against_ship_type_<ship>_<accuracy|hull_damage>_<add|mult>`, etc.) require **per-entity registration** in `common/modifier_type_definitions/extra_modifier_types.txt` for any modded building/good/ship type. Without registration the modifier silently no-ops. Note that vanilla also only auto-registers *specific axis combinations* per entity (e.g. `ship_type_submarine` gets `_accuracy_*` but NOT `_hull_damage_mult`; `ship_type_dreadnought` gets `_hull_damage_mult` but NOT `_accuracy_mult`) — even when targeting a vanilla type, the specific combo you want may need its own mod-side registration.
- Time units: `short_modifier_time` / `normal_modifier_time` / `long_modifier_time` / `very_long_modifier_time` are in **days**. Always `days = ...`, never `months = ...` (off by 30×).
- `any_*` triggers do NOT accept a `limit = { }` block — siblings only. `limit` is for effect iterators (`every_*`, `random_*`, `ordered_*`).
- `add_modifier` / `remove_modifier` results are not visible inside the same effect block. To recompute a modifier from "base" values, store the prior contribution as a variable and subtract it from the `modifier:X` read. Examples: `prior_pollution_reduction`, `intel_shield_mult`.
- State-scoped script-value updates that traverse `state_region` should be wired to `on_yearly_pulse_state`, not `on_law_activated` / `on_acquired_technology` / treaty entry hooks (broken parent scope chain).
- **Modifier stacking is additive across all sources.** Both `_add` and `_mult` modifiers from different sources (buildings, PMs, traits, laws, events) **sum**, they do not multiply. So a per-building `country_X_mult = -0.02` becomes `-2.0` (200% reduction) when 100 instances of the building exist — pathological. Per-building modifiers in `country_modifiers = { workforce_scaled = { ... } }` blocks must be `_add` with small values, OR use country-scope `_mult` only in places that are applied once (event-applied static modifiers, law modifiers, power-bloc member_modifier). When migrating a removed `_add` modifier, do NOT translate it 1:1 to a `_mult`; either find an `_add` analog or drop the per-building bonus entirely.
- **Top-level entity collisions get silently dropped.** If a mod file declares a top-level key vanilla already owns (`clothes`, a vanilla modifier name, etc.), `debug.log` says `Duplicated key X will not be created` and the mod's whole block is ignored. Use `INJECT:X = { ... }` to extend rather than redeclare. See `docs/scripting_best_practices.md` § "Top-Level Database Collisions".
- **Global variables read by JE `possible` clauses must be initialized in `on_game_started`.** A `possible` block evaluates at game start, before any `on_*_pulse_*` fires. If it reads `global_var:foo` that doesn't exist yet, debug.log shows `Got value of type 'none'` and the JE silently fails to surface. Wire initialization through `on_game_started = { on_actions = { my_init_action } }` (extension form — never `effect = { }`, which clobbers vanilla's body). See `docs/scripting_best_practices.md` § "Global Variable Initialization Timing".

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

### System-scope cheat sheet
Where a given modifier or trigger can be used:
- **`mobilization_options/*`** `unit_modifier`: armies only. Don't use `military_formation_fleet_*` or `ship_*` modifiers here.
- **Tech `modifier = { ... }`** (in `common/technology/technologies/`): country-scope. `character_*` modifiers do NOT apply here — they only work in scopes that target a character (character traits, character-applied static modifiers, etc.). `ship_*` modifiers DO work in tech scope and apply as a country-wide buff to all ships (vanilla `paddle_steamer` uses `ship_hull_damage_mult` / `ship_crew_damage_mult` from a tech `modifier` block; `ship_battle_against_ship_type_*` patterns also work). Use `country_*`, `state_*`, `unit_*`, `building_*`, `ship_*`, or pre-defined country booleans (`country_<feature>_pb_principles_bool`) that are read elsewhere.
- **Power bloc `member_modifier` / `leader_modifier`**: country-scope. `character_*` modifiers cascade to all the country's characters.
- **Static modifiers (`common/static_modifiers/`)**: any scope's modifiers — but the static modifier must be applied at a matching scope (country / state / character).
- **`INJECT:` / `REPLACE:` / `REPLACE_OR_CREATE:` directive prefixes** on entity keys (e.g. `INJECT:building_shipyard = { ... }`) are **engine-native** in Vic3 (Clausewitz). The mod uses them throughout. They merge or replace into the matching vanilla entity at load time. Don't try to "expand" them in tooling.

### Recording lessons learned
When you (Claude or future Claude instances) discover something generally applicable — a working trigger syntax, an engine quirk, a refactor pattern, a tool behavior, a validation rule that bites — write it into the appropriate doc in the same session, don't let it die in conversation history. Natural homes:
- Engine syntax, scope rules, modifier validation, scripting gotchas → `docs/scripting_best_practices.md`
- Refactor patterns and the helper inventory → `docs/script_parameterization_audit.md`
- Mod-state-server / tooling behavior → `docs/python_tools.md`
- Cross-cutting workflow notes → this file (`CLAUDE.md`)
- Per-helper context (parameters, scope contract, edge cases) → the helper's own comment header in `common/scripted_*/`. These propagate across clones.

Note that `docs/` is gitignored (see `.gitignore`), so doc edits help the current local environment but don't propagate. For lessons that need to survive a fresh clone, either commit them to `CLAUDE.md` or to the helper's own file header. Don't repeat in both places — pick the natural home and link.

Keep additions short — one paragraph or a bullet, not a treatise. The bar is: would the next Claude instance hit the same gotcha or solve the same problem from scratch without this note? If yes, write it down.

### Editing conventions
- Brace-based Paradox files use **tab** indentation. After large edits run `python scripts/format_paradox_tabs.py <files>` (or `--check` in CI-style flows).
- After editing mod files, `POST /reload` to refresh the server's view (the auto-deploy watcher will already have synced files into the Paradox mod folder).
- Localization keys: prefer adding to existing `*_l_english.yml` files and run `python organize_loc.py` to sort and detect unused keys.
- Don't hand-edit auto-generated files. **Always edit the generator's input and re-run the generator.** Authoritative ownership map (also in `docs/auto_generated_files.md`):
  - `common/ideologies/modified.txt` — owned by `apply_ideologies.py`; input is `ideology_modifications.py` plus vanilla ideology files. Re-run after vanilla updates to pick up new vanilla content (e.g. patches that add new laws or change attitudes).
  - `common/interest_groups/00_*.txt` (8 files) — owned by `ig_feminism.py`.
  - `common/buy_packages/00_buy_packages.txt` — owned by `pop_needs_curves.py`.
  - `map_data/state_regions/*.txt` — owned by `resources.py`; input is `deposits_config.json` plus vanilla `game/map_data/state_regions/`. After a vanilla map change, update `deposits_config.json` to point old/removed states at successors and re-run.
  - `docs/laws.txt`, `docs/technologies.txt`, `docs/buildings.txt`, `docs/goods.txt`, `docs/combat_units.txt` — owned by `mod_state_script.py`; rebuilt automatically on `POST /reload`.
  - `docs/vic3_*_reference.md`, `docs/triggers_summary.txt`, `docs/effects_summary.txt`, etc. — owned by `engine_docs_render.py`.
  - `docs/engine_coverage_report.md` — owned by `mod_state_server.py /validate/engine-coverage`.
  - `docs/error_log_digest.md` — owned by `game_log_reader.py`.
  - Files produced by `gen_*.py` scripts may or may not be auto-managed. If a file's first 5 lines contain `# AUTO-GENERATED` or `do not edit manually`, treat it as owned. Otherwise, it's a one-shot generator output that's been committed; check the script to decide.
  - Quick check: `git grep -l "AUTO-GENERATED\|do not edit manually" common/ map_data/ localization/`.
- Use `python3` on this system (no `python` alias). The README/CLAUDE.md `python <script>.py` invocations all work as `python3 <script>.py`.

## Deployment topology
- This repo is on the WSL/Linux side (`/home/jakef/src/Vic3TimelineExtended`).
- The engine reads from the Windows-side mod folder (`/mnt/c/Users/jakef/.../Victoria 3/mod/Vic3TimelineExtended`).
- `scripts/deploy.sh` rsyncs only `common/`, `events/`, `localization/`, `gui/`, `gfx/`, `map_data/`, `.metadata/`, `descriptor.mod`, `thumbnail.png`. Everything else (Python, docs, tests, `.git`, logs) stays in the repo.
- The auto-deploy watcher runs that rsync continuously while VS Code is open; manual edits via other editors will not auto-deploy.
