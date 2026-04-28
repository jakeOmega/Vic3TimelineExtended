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
- `docs/scripting_best_practices.md` — modifier validation, `days` vs `months` units, scope chain pitfalls, expense scaling, registration of dynamic modifier types, `any_` triggers don't take `limit`, modifier-after-effect read ordering, scripted-trigger/effect catalog.
- `docs/event_creation_guide.md` — boilerplate, available videos/icons, IG approval modifiers, `on_yearly_events` wiring, style.
- `docs/mod_systems.md` — every gameplay system's files and mechanics.
- `docs/journal_entry_systems.md` — the 10+ JE systems in detail.
- `docs/python_tools.md` — full server endpoint list and AI-agent workflow.
- `docs/gui_modding_guide.md` — when touching `gui/`.
- `docs/treaty_articles_reference.md`, `docs/wonder_buildings_reference.md`, `docs/vanilla_company_buildings_reference.md` — patterns for those systems.

### Validation rules that bite if ignored
- The Clausewitz engine **silently ignores invalid modifier names**. Validate via `/modifier-search?q=` or `/engine-docs/modifiers?q=` before introducing one. Known-bad names are listed in `docs/scripting_best_practices.md`.
- Dynamic modifier patterns (`building_<name>_throughput_add`, `goods_output_<good>_mult`, `state_building_<name>_max_level_add`, etc.) require **per-entity registration** in `common/modifier_type_definitions/extra_modifier_types.txt` for any modded building/good. Without registration the modifier silently no-ops.
- Time units: `short_modifier_time` / `normal_modifier_time` / `long_modifier_time` / `very_long_modifier_time` are in **days**. Always `days = ...`, never `months = ...` (off by 30×).
- `any_*` triggers do NOT accept a `limit = { }` block — siblings only. `limit` is for effect iterators (`every_*`, `random_*`, `ordered_*`).
- `add_modifier` / `remove_modifier` results are not visible inside the same effect block. To recompute a modifier from "base" values, store the prior contribution as a variable and subtract it from the `modifier:X` read. Examples: `prior_pollution_reduction`, `intel_shield_mult`.
- State-scoped script-value updates that traverse `state_region` should be wired to `on_yearly_pulse_state`, not `on_law_activated` / `on_acquired_technology` / treaty entry hooks (broken parent scope chain).

### Editing conventions
- Brace-based Paradox files use **tab** indentation. After large edits run `python scripts/format_paradox_tabs.py <files>` (or `--check` in CI-style flows).
- After editing mod files, `POST /reload` to refresh the server's view (the auto-deploy watcher will already have synced files into the Paradox mod folder).
- Localization keys: prefer adding to existing `*_l_english.yml` files and run `python organize_loc.py` to sort and detect unused keys.
- Don't hand-edit auto-generated files: `docs/laws.txt`, `docs/technologies.txt`, `docs/buildings.txt`, `docs/goods.txt`, `docs/combat_units.txt`, and anything produced by `gen_*.py` (re-run the generator).

## Deployment topology
- This repo is on the WSL/Linux side (`/home/jakef/src/Vic3TimelineExtended`).
- The engine reads from the Windows-side mod folder (`/mnt/c/Users/jakef/.../Victoria 3/mod/Vic3TimelineExtended`).
- `scripts/deploy.sh` rsyncs only `common/`, `events/`, `localization/`, `gui/`, `gfx/`, `map_data/`, `.metadata/`, `descriptor.mod`, `thumbnail.png`. Everything else (Python, docs, tests, `.git`, logs) stays in the repo.
- The auto-deploy watcher runs that rsync continuously while VS Code is open; manual edits via other editors will not auto-deploy.
