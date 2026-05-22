# Python Tools & Mod State Server

Reference for all Python utility scripts and the background data server.

## Path Constants

`path_constants.py` — Defines `mod_path`, `base_game_path`, `doc_path`. Imported by nearly all other scripts.

## Auto-run on server reload

`mod_state_server.py` runs a chain of idempotent transformers after every full ModState load (server startup and `POST /reload`). The canonical rosters are `POST_LOAD_REGENERATORS` (the 10 file-rewriting generators) and `POST_LOAD_AUDITS` (the 7 read-only audits) in `mod_state_server.py`; the default reload runs `POST_LOAD_GENERATORS = POST_LOAD_REGENERATORS + POST_LOAD_AUDITS`. Each entry must expose `regenerate(mod_state=None)` and finish in well under a second. Failures are logged with `[post-load] <name> FAILED` and skipped — they don't block startup. `POST /reload?engine_only=true` bypasses `_load_mod_state` and so skips these; `POST /reload?audits_only=true` runs only `POST_LOAD_AUDITS` (no working-tree side effects beyond `docs/engine/*_report.md`).

**Audit warnings**: when a generator's return dict contains `unreviewed > 0` or `hard_fails > 0`, the runner logs `[post-load WARN] <label> surfaced issues: <key>=<n>` at WARNING level and adds an entry to the `/reload` response's `warnings` array — caller sees regressions in the same response, no log-scraping required. Add new actionable counter names to `_POST_LOAD_WARN_KEYS` in `mod_state_server.py` if a new audit invents one.

| Module | Output |
|---|---|
| `pop_needs_curves` | `common/buy_packages/00_buy_packages.txt` |
| `apply_ideologies` | `common/ideologies/modified.txt` |
| `ig_feminism` | `common/interest_groups/00_*.txt` |
| `pm_costs` | cost-comment headers in `common/production_methods/extra_pms.txt` & `unique_pms.txt`; `docs/engine/commented_vanilla_pms.txt`; `docs/engine/commented_vanilla_military_units.txt` |
| `resources` | `map_data/state_regions/*.txt` |
| `gen_pb_principle_unlock_descs` | `*_pb_principles_bool_desc` keys in `localization/english/te_power_bloc_unlocks_l_english.yml` |
| `gen_un_button_descs` | `localization/english/te_un_button_effects_l_english.yml` |
| `gen_law_consistency` | `common/scripted_effects/extra_law_consistency_generated.txt` |
| `organize_loc` | `localization/english/te_*_l_english.yml` (~26 category files) |
| `event_magnitude_audit` | `docs/engine/event_magnitude_report.md` |
| `modifier_visibility_audit` | `docs/engine/modifier_visibility_report.md` |
| `kill_character_audit` | `docs/engine/kill_character_audit.md` |
| `loc_coverage_audit` | `docs/engine/loc_coverage_report.md` |
| `mod_structure_audit` | `docs/engine/mod_structure_report.md` — flags brace-balance failures, silent-INJECT failures (INJECTs targeting mod-only or REPLACEd entities), and within-namespace top-level collisions. Subdirs that merge by design (`on_actions/`, `defines/`, `history/`) are excluded from collision detection. |
| `gen_event_inventory` | `docs/engine/event_image_inventory.md` |

**Opt-out:** Set `VIC3_SKIP_POST_LOAD_GENERATORS=1` in the server's environment to skip the entire post-load batch (useful while iterating on one of these scripts).

**Watcher safety:** The deploy watcher (`scripts/watch_deploy_on_edit.sh`) only rsyncs to the Paradox mod folder; it does **not** call `/reload`. So a generator writing into `common/` or `map_data/` triggers exactly one extra rsync after the reload completes, never an infinite loop. **Do not wire `/reload` into the watcher.**

Every module retains its standalone CLI entrypoint (with `--dry-run` flags where applicable); auto-run uses a quiet code path that suppresses the verbose progress output.

### Adding a new post-load generator

Three rules — break any of them and the integration fails silently or deadlocks at startup:

1. **Module lives at the repo root.** `POST_LOAD_GENERATORS` calls `importlib.import_module(<bare_name>)`, which only resolves modules on `sys.path`. Generators in `scripts/generators/` don't qualify. If you have one there and want it auto-run, move it (`git mv`) to the repo root.
2. **Expose `def regenerate(mod_state=None)`.** The post-load chain passes the live `ModState` instance. Read entity data via `mod_state.get_data("Events")` / `mod_state.localize(...)` / `mod_state.mod_parsers[...]` — never via HTTP loopback to `localhost:8950`. The server isn't accepting requests yet during startup, so a `urlopen('http://localhost:8950/...')` call inside post-load will block until timeout. (`gen_event_inventory.py` originally hit the HTTP endpoint and could not have been auto-run as-shipped — refactoring it to take `mod_state` was the unblocker.)
3. **Standalone fallback uses `mod_state_script` for the path dicts.** When `mod_state is None`, instantiate `ModState(base_game_paths, mod_paths)` — those dicts are defined in `mod_state_script.py` and `mod_state_server.py`, **not** in `path_constants.py` (which only has `mod_path` / `base_game_path` scalars). Importing from `mod_state_script` keeps the standalone path cycle-free; importing from `mod_state_server` would re-enter the server module.

After adding the module + appending to `POST_LOAD_GENERATORS`, validate without disrupting a running server: run `.venv/bin/python <your_module>.py` (the standalone path) and confirm the output file is rewritten. The integration test (`[post-load] <name> ok` line) only fires on a fresh server start — pick that up on the next natural restart rather than killing the running PID for a check.

**Edits to an existing post-load generator don't take effect on `/reload`.** Python caches the module on first import; `POST /reload` re-runs the chain but each entry is the version that was imported at server startup. Symptom: a fix to `pm_costs.py` works when invoked directly (`.venv/bin/python pm_costs.py`) but `/reload` still produces the broken output. Restart the server to pick up the edit.

### Generator idempotency around hand-edited loc

When a post-load generator regenerates a loc value via regex substitution (e.g. `pm_costs.py` rewriting the `Cost at current market prices: …` suffix in every `combat_unit_type_*_desc`), a hand-edit that tags the term with `[concept_X]` or `[Concept('X', '…')]` will silently break the regex's anchor — the generator's "replace existing" path stops matching, falls back to "append fresh," and the file accumulates a duplicate suffix on every reload. No parser warning fires; the only catch is visual inspection of the loc value or a `grep -c` after a few reloads.

Defensive pattern: make the regex match BOTH the legacy untagged form and the tagged form (`(?:market prices|\[Concept\('concept_market_price', 'market prices'\)\])`) and emit the tagged form on write. The same applies to any generator that anchors on display-name substrings of registered concepts.

## Core Infrastructure

| Script | Purpose | Run |
|--------|---------|-----|
| `paradox_file_parser.py` | Parses Paradox `.txt` files into Python dicts. Handles tokenization, brace nesting, `REPLACE:` / `INJECT:` merge directives, and diff detection. | Library (import) |
| `test_paradox_file_parser.py` | 12 unit tests for the parser. | `python test_paradox_file_parser.py` |
| `test_event_balance.py` | 53 unit tests for the `/event-balance` helpers (polarity arithmetic, modifier color lookup, static-modifier resolution, option-body walker, `add_enactment_modifier` expansion, change_variable parsing, file id extraction, text rendering, strict and soft dominance helpers). | `python -m unittest test_event_balance` |
| `mod_state.py` | `ModState` class wrapping the parser. Loads all entity types and localization. Provides `localize()`, `unlocalize()`, `search_localization()`, `build_reverse_localization()`. | Library (import) |
| `mod_state_server.py` | Persistent HTTP server (port 8950) serving parsed mod data as JSON. See **Mod State Server** section. | `.venv/bin/python mod_state_server.py` |
| `mod_state_client.py` | CLI client for the mod state server. | `python mod_state_client.py <command> [args]` |
| `mod_state_script.py` | Generates text reference docs (`docs/engine/laws.txt`, `docs/engine/technologies.txt`, `docs/engine/buildings.txt`, `docs/engine/goods.txt`, `docs/engine/combat_units.txt`) from parsed mod state. This is also called automatically when the mod state server starts or reloads. | `python mod_state_script.py` |

## Formatting & Maintenance

| Script | Purpose | Run |
|--------|---------|-----|
| `scripts/format_paradox_tabs.py` | Normalizes leading tab indentation for brace-based Paradox `.txt` files by recalculating indentation from brace depth. Useful after large manual or AI edits when nested blocks are syntactically correct but hard to read. | `python scripts/format_paradox_tabs.py common/journal_entries/je_strategic_reserve.txt` |

### Paradox Tab Formatter

Use `scripts/format_paradox_tabs.py` on brace-based Paradox script files such as files under `common/`, `events/`, or similar `.txt` data directories when indentation has drifted.

```bash
# Format files in place
python scripts/format_paradox_tabs.py common/journal_entries/je_strategic_reserve.txt common/scripted_effects/st_res_effects.txt

# Check whether files would change without rewriting them
python scripts/format_paradox_tabs.py --check common/journal_entries/je_strategic_reserve.txt common/scripted_effects/st_res_effects.txt
```

Notes:
- The formatter is intended for brace-based Paradox `.txt` files only.
- It strips existing leading whitespace and reapplies tabs from inferred brace depth.
- It ignores braces inside quoted strings and ignores trailing `#` comments while computing indentation.
- Do not use it on YAML, JSON, or Python files.

## Localization & Code Generation

| Script | Purpose | Run |
|--------|---------|-----|
| `organize_loc.py` | Sorts localization keys alphabetically, detects unused keys, finds implicit keys. **Auto-runs on every server reload.** When introducing a new content family, add its prefix to `categorize_key` (e.g. `ship_type_*` → `SHIP_TYPES`) so its keys don't fall into MISCELLANEOUS. **4+ token gotcha:** the fallback rule is `re.match(r"^[a-zA-Z_]+$", key) and len(key.split("_")) < 4 → CONCEPTS, else MISCELLANEOUS`. A bare `state_trait_bushveld_complex` (4 tokens) lands in MISCELLANEOUS while its `_desc` lands in CONCEPTS — splitting the family across two files. Any new prefix whose base key has 4+ tokens needs an explicit `startswith` rule even if you're "fine with MISCELLANEOUS." | `python organize_loc.py` |
| `gen_ministry_events.py` | Generates `events/ministry_law_events.txt` (ministry law events). | `python gen_ministry_events.py` |
| `scripts/generators/gen_loc_files.py` | Generates localization YAML for `extra_law_events` and `ministry_law_events`. | `python scripts/generators/gen_loc_files.py` |
| `scripts/generators/gen_event.py` | Event scaffolding tool. Generates boilerplate event definitions + loc entries from compact JSON specs or CLI args. Handles ID allocation, BOM encoding, and triggered_desc chains. Three subcommands: `next-id`, `batch`, `scaffold`. | See **Event Scaffolding** section below. |

## Production Method Tools

| Script | Purpose | Run |
|--------|---------|-----|
| `pm_costs.py` | Annotates PM files with cost/revenue comments. **Auto-runs on every server reload.** | `python pm_costs.py` (supports `--dry-run`) |
| `scripts/analysis/pm_balance.py` | Newton-Raphson solver for PM input amounts. | `python scripts/analysis/pm_balance.py --inputs steel:11 --outputs services:1000 --profit 1000` |
| `apply_ideologies.py` | Applies ideology attitude modifications from `ideology_modifications.py`. **Auto-runs on every server reload.** | `python apply_ideologies.py` (supports `--dry-run`) |

## Balance & Analysis

| Script | Purpose | Run |
|--------|---------|-----|
| `scripts/analysis/pop_growth.py` | Pop growth model (birthrate, mortality vs SoL). | `python scripts/analysis/pop_growth.py` (text table), `--plot` for chart |
| `pop_needs_curves.py` | Pop needs curve definitions and buy_packages generator. **Auto-runs on every server reload.** | `python pop_needs_curves.py` (generate), `--table` for display only |

## Content Generation

| Script | Purpose | Run |
|--------|---------|-----|
| `resources.py` | Injects resource deposits into state region files from `deposits_config.json`. **Auto-runs on every server reload.** | `python resources.py` (`--table` for dry run) |
| `ig_feminism.py` | Adjusts female leader/commander probability in IG files. **Auto-runs on every server reload.** | `python ig_feminism.py` |
| `scripts/image_pipeline/event_image_prompts.py` | Maps all mod events to image/video assets. Defines AI image generation prompts. Used by `generate_event_images.py`. | Library (import) |
| `scripts/image_pipeline/generate_event_images.py` | 3-phase pipeline: generate AI images (FLUX.1-schnell), convert to DDS, create event videos. | `python scripts/image_pipeline/generate_event_images.py --phase generate` |

## Event Scaffolding (`gen_event.py`)

Generates boilerplate-free Paradox event definitions and localization entries from compact JSON specs. Handles auto-ID allocation (scans existing event files), UTF-8 BOM encoding, triggered_desc chains, default option inheritance, and section headers.

### Subcommands

```bash
# Find next available IDs in a namespace
python gen_event.py next-id space_race_events --after 600 --count 5

# Generate events from a JSON spec (preview first)
python gen_event.py batch my_spec.json --dry-run
python gen_event.py batch my_spec.json

# Quick single-event scaffold
python gen_event.py scaffold --namespace my_events --title "Title" --desc "Desc" --options "Opt A" "Opt B" --dry-run
```

### JSON Spec Format

```json
{
    "namespace": "my_events",
    "output_file": "events/my_file.txt",
    "append": false,
    "header_comment": "MY EVENTS SECTION",
    "auto_id_start": 0,
    "defaults": {
        "type": "country_event",
        "icon": "gfx/interface/icons/event_icons/event_default.dds",
        "duration": 3,
        "options": [
            {"name_ref": "shared.option.key", "default": true, "ai_weight": 5}
        ]
    },
    "events": [
        {
            "id": 1,
            "comment": "Short description",
            "section_comment": "SECTION DIVIDER",
            "title": "My Event Title",
            "desc": "Simple description.",
            "flavor": "Flavor text.",
            "image": "my_image",
            "options": [
                {"name": "Option text", "default": true, "ai_weight": 5, "effects": "add_prestige = 10"}
            ]
        }
    ]
}
```

### Key Field Patterns

| Field | New loc key | Reference existing key |
|-------|-------------|----------------------|
| Title | `"title": "text"` → `ns.ID.t` | `"title_ref": "existing.key"` |
| Desc (simple) | `"desc": "text"` → `ns.ID.d` | — |
| Desc (triggered) | `"desc": [{"text": "new", "key": "ns.ID.d.1"}]` | `"desc": ["ref.key"]` or `[{"ref": "key"}]` |
| Flavor | `"flavor": "text"` → `ns.ID.f` | `"flavor_ref": "existing.key"` |
| Option name | `"name": "text"` → `ns.ID.a` | `"name_ref": "existing.key"` |

Hidden events: set `"hidden": true` — generates minimal structure (type + hidden + trigger + immediate only).

### Workflow

1. Write a compact JSON spec (10-15 lines per event vs 60+ lines of Paradox script)
2. `python gen_event.py batch spec.json --dry-run` to preview
3. `python gen_event.py batch spec.json` to write files
4. `python organize_loc.py` to sort the appended loc keys
5. Edit the generated `.txt` to add event-specific effects to options

---

## Mod State Server (Background Data Service)

The mod-state server (`mod_state_server.py`) parses **all vanilla AND mod data** (laws, technologies, buildings, interest groups, goods, ideologies, combat units, events, journal entries, institutions, production methods, decisions, decrees, script values, scripted effects/triggers, on-actions, treaty articles, and more) **once** on startup, then serves it over a local HTTP API. It also parses engine documentation files (effects, triggers, modifiers, event targets, on-actions, custom localization) and loads developer reference `.md` files from the base game. This is the **preferred way for AI agents to look up game data**.

> **IMPORTANT:** The server indexes BOTH vanilla base game data AND mod data, merged together for most entity types. Events, scripted effects, scripted triggers, and on-actions are **mod-only** (they load only from the mod directory, not vanilla).

> **Logging:** The server logs to both console (INFO level) and `mod_state_server.log` (DEBUG level) in the mod root directory. Check the log file for detailed error diagnostics.

### Auto-Generated Documentation

On startup and on `/reload`, the server automatically generates the following documentation files in `docs/`:
- `laws.txt` — All law groups and laws with unlock technologies
- `technologies.txt` — All technologies by era with prerequisites and descriptions
- `buildings.txt` — All buildings with PM groups, PMs, and pollution data
- `goods.txt` — All tradeable goods
- `combat_units.txt` — All combat unit types with unlocking technologies

These files should NOT be manually edited — they are regenerated from parsed game data.

### Starting the Server

The server **auto-starts when the VS Code workspace opens** via a VS Code task in `.vscode/tasks.json`. It runs in a background terminal labeled "Mod State Server".

To start manually (use the venv Python so the post-load generators resolve their deps):
```bash
.venv/bin/python mod_state_server.py
```
Loads in ~60–110 seconds, then listens on `http://127.0.0.1:8950`.

### Checking If the Server Is Running
```powershell
Invoke-RestMethod http://localhost:8950/status
```

> **AI agent rule:** ALWAYS check if the server is running at the START of any session that involves looking up game data.

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/status` | GET | Server status, loaded entity types, loc key count |
| `/entity-types` | GET | List of entity type names |
| `/keys/<EntityType>` | GET | All entity IDs + localized names for a type |
| `/raw/<EntityType>` | GET | Full raw parsed data for a type |
| `/raw/<EntityType>/<id>` | GET | Raw parsed data for one entity |
| `/loc-keys/<EntityType>/<id>` | GET | Resolve the stable family of loc keys an entity exposes (name/desc/...). Seeded set in `LOC_KEY_FAMILIES` (treaty articles, decisions, JEs, decrees, diplo actions/plays, laws, country formations, modifiers, institutions). |
| `/localize/<key>` | GET | Game key → display text |
| `/unlocalize/<text>` | GET | Display text → matching game key(s) |
| `/search?q=<query>` | GET | Search entity IDs, names, and localization |
| `/laws` | GET | All laws grouped by law group |
| `/laws/<law_id>` | GET | Detailed law data — includes resolved `name` and `description` (the `<law_id>_desc` loc; the field intent / ethnocentrism ordering lives in the description, not the `progressiveness` number). `/decrees/<id>` and `/institutions/<id>` likewise expose `description`. |
| `/technologies` | GET | All technologies grouped by era |
| `/technologies?era=<n>` | GET | Technologies for a single era |
| `/technologies/<tech_id>` | GET | Detailed technology data |
| `/buildings` | GET | All buildings with PM group count |
| `/buildings?detail=true` | GET | All buildings with full PM group/PM detail |
| `/buildings/<building_id>` | GET | Detailed building data |
| `/buildings/pm-map` | GET | Compact building→PM group→PM mapping for generators |
| `/goods` | GET | All tradeable goods |
| `/combat-units` | GET | Combat units grouped by unit group |
| `/ideologies` | GET | All ideologies |
| `/ideologies/<id>` | GET | Ideology detail |
| `/events` | GET | All mod events with type, image/video, icon |
| `/events/<event_id>` | GET | Event detail with options and raw data |
| `/events?image=<name>` | GET | Filter events by image/video filename |
| `/events?type=<type>` | GET | Filter events by type (country_event, etc.) |
| `/event-balance/<event_id>` | GET | Annotate option effects with modifier polarity. For each `add_modifier` / `add_enactment_modifier`, looks up the static modifier and tags every numeric field with its `color` (good/bad/neutral) and player-perspective `polarity` (positive/negative/neutral). Walks `if`/`random_list`/scope-iterator/scope-change blocks. |
| `/event-balance?ids=a,b,c` | GET | Annotate a comma-separated list of events |
| `/event-balance?prefix=<ns>` | GET | Annotate every event whose id starts with `<ns>` (e.g. `banking_cycle_events`) |
| `/event-balance?file=events/foo.txt` | GET | Annotate every event declared in a file |
| `/event-balance/issues[?prefix=&file=]` | GET | **Strict-mode audit** (default). Flags events with at least one option pure-positive on modifiers AND another pure-negative. |
| `/event-balance/issues?mode=soft&threshold=N` | GET | **Soft-mode audit**. Flags pairwise polarity-count dominance — one option has ≥ as many positive modifier fields AND ≤ as many negatives as another, with combined gap ≥ `threshold` (default 2). Catches mixed-vs-mixed dominance the strict check misses. |
| `/event-balance/...?format=text` | GET | Render the result as a plain-text report instead of JSON |
| `/event-balance/issues?...&include_reviewed=true` | GET | Surface the `reviewed` exemption list in the JSON. Events with a `# REVIEWED YYYY-MM-DD: rationale` comment on the event header line (or in the contiguous comment block directly above it) are moved out of `flagged` into `reviewed_count` / `reviewed`. The text renderer always shows the reviewed count in the header line (e.g. `flagged 0 (4 reviewed)`). Use this when an option-dominance shape is intentional — typically because the "dominated" option's compensation lives in post-completion rewards or other effects the audit can't see. |

**Audit limitations** (verify each flag against source before editing): the audit only sees `add_modifier` / `add_enactment_modifier` field polarity. It does NOT classify `add_treasury`, `add_radicals` / `add_loyalists`, `add_momentum`, `change_variable`, `change_relations`, `change_infamy`, `set_ideology`, `set_variable`-driven choice routing, scripted-effect calls, `activate_law`, or `add_modifier` applied via scope changes to *other* actors. It also counts modifier *fields*, not `days = …` durations or value magnitudes. See `docs/guides/event_creation_guide.md` § Verifying Option Balance for the full list.
| `/institutions` | GET | All institutions with unlock tech |
| `/institutions/<id>` | GET | Institution detail with modifiers |
| `/production-methods` | GET | All production methods |
| `/production-methods/<pm_id>` | GET | PM detail with building/country/state modifiers |
| `/production-methods?building=<id>` | GET | All PMs for a building, grouped by PM group |
| `/journal-entries` | GET | All journal entries with group |
| `/journal-entries/<je_id>` | GET | Journal entry detail |
| `/treaty-articles` | GET | All treaty articles |
| `/treaty-articles/<id>` | GET | Treaty article detail |
| `/treaty-articles/<id>/loc-keys` | GET | Treaty article's loc-key family (name / desc / article_short_desc / effects_desc) |
| `/diplomatic-actions` | GET | All diplomatic action types — the `type =` vocabulary that feeds `has_diplomatic_pact = { who type }`. Each entry carries `category` (general/subject_relation/power_bloc), `groups`, `is_subject_relation`, `is_two_sided_pact`, `subject_type`. |
| `/diplomatic-actions/<id>` | GET | Detail with full `pact` block and `raw` AST |
| `/decisions` | GET | All decisions |
| `/decisions/<id>` | GET | Decision detail |
| `/script-values` | GET | All script value IDs |
| `/script-values/<id>` | GET | Script value raw data |
| `/scripted-effects` | GET | All scripted-effect IDs, each with its `parameters` (`$X$` placeholders) |
| `/scripted-effects/<id>` | GET | Scripted-effect detail: `parameters`, `callers` (every call site — events, on_actions, journal entries, other helpers, **and vanilla** — with `file`/`line`/`origin` and parsed args), `raw`. The caller index is a brace-aware file scan (the parser drops file/line); built lazily on first request (~25s) and cached until the next `/reload`. **First stop before changing a parameterized helper's signature** — enumerates every caller and the args each passes. |
| `/scripted-triggers` | GET | All scripted-trigger IDs with `parameters` |
| `/scripted-triggers/<id>` | GET | Scripted-trigger detail (same shape as `/scripted-effects/<id>`) |
| `/decrees` | GET | All decrees |
| `/decrees/<id>` | GET | Decree detail with modifiers |
| `/principles` | GET | All Power Bloc principle IDs |
| `/principles/<id>` | GET | Principle detail: resolved `name`/`description`, `group_id`/`group_name`/`group_levels` (reverse-looked-up from Principle Groups), and `modifier_blocks` (each present `member_modifier`/`institution_modifier`/`power_bloc_modifier`/… bag as `{block, modifiers}`). `Principles`, `Principle Groups`, and `Amendments` are now first-class entity types — `/keys/Principles`, `/raw/Principles/<id>`, `/filter`, `/references` all work too. |
| `/amendments` | GET | All amendment IDs |
| `/amendments/<id>` | GET | Amendment detail: `name`/`description`, `parent` law, `allowed_laws`, and `modifiers`. |
| `/diff/<EntityType>/<id>` | GET | **Mod-vs-vanilla field-level diff** — what the mod actually changes for an entity vs the vanilla baseline (merge-directive aware; ModState holds both parses). Returns `{in_vanilla, added, removed, changed}` with flattened dotted keys (`modifier.state_homeland_creation_threshold_add`); `changed[key]` is `{vanilla, mod}`. `in_vanilla: false` ⇒ the whole entity is `added`. `?format=text` gives a `difflib` unified diff over a Paradox-ish render of the two blocks. **Use for any `REPLACE:`/`INJECT:` override audit or vanilla version bump** instead of hand-diffing against `~/src/vic3`. |
| `/on-actions` | GET | All on-action IDs (mod-only) |
| `/on-actions/<id>` | GET | On-action raw data |
| `/gui/render-sites/<loc_key>` | GET | Every GUI file:line (mod + vanilla) that references `<loc_key>` via a known loc attribute (`text` / `tooltip` / `raw_text` / ...). Mechanical scan; one curl replaces a multi-grep over both GUI trees. |
| `/gui/render-paths/<EntityType>?field=<role>` | GET | Every GUI file:line that renders `<field>` of `<EntityType>` via `[<DataType>.GetX]`. Resolves EntityType → DataType via `ENTITY_TYPE_TO_DATATYPE`, field role → method names via `FIELD_TO_METHODS`. Fields: `name` / `desc` / `icon` / `tooltip`. |
| `/reload` | POST | Re-parse all files from disk + run post-load chain (regenerators + audits). Flags compose; see table below. |

##### `/reload` flag table

| Query | Cost | Working-tree side effects | What it skips | When to use |
|---|---|---|---|---|
| (none) | ~30–60 s | regenerator output under `common/`, `localization/english/`, `events/` + audit reports under `docs/engine/` | nothing | Normal "I edited mod files, re-run everything" reload. |
| `?engine_only=true` | <1 s | none | the entire ModState rebuild (only re-reads engine-doc snapshots) | After re-launching the game with no mod-file edits, when you only want freshly-typed `script_docs` output to be picked up. |
| `?audits_only=true` | ~80 s | audit reports under `docs/engine/*_report.md` only | the 10 file-rewriting `POST_LOAD_REGENERATORS` | When you want a clean re-check of audit warnings without regenerators reshuffling your diff. Time-savings are modest — the parse dominates. The real win is the clean diff. |
| `?mod_only=true` | ~25 s | regenerator output (as above) | the vanilla parse + vanilla loc re-read (uses cached snapshot from the previous full load) + the engine-docs / dev-refs reload | When you've only edited mod files and want a quick reload. Vanilla cache is opt-in — if you bump vanilla, run an unflagged `/reload` to refresh it. |
| `?mod_only=true&audits_only=true` | ~25 s | audit reports under `docs/engine/*_report.md` only | both regenerators *and* the vanilla re-read | **The fast-verify path used by the nightly audit.** Safe to call after every batch of fixes. |

#### `/raw/<EntityType>[/<id>]` Response Shape

The path takes a **display type name** (URL-encoded with `%20`, e.g. `/raw/Ship%20Types/ship_type_nuclear_submarine`, `/raw/Ship%20Modifications/ship_mod_*`) — not the Python class name. `/entity-types` lists the valid values; `/raw/<unknown>` returns `{"error": "Not found: '<X>'"}`.

The body wraps **every parsed node** as `[<operator>, <value>]` (operator is usually `=`, occasionally `>` / `<` / `?=` etc. for trigger comparisons). So a single-entity fetch is a list, not a dict, and every field one level down is also a wrapped list. To read a leaf field like `modifier.ship_visibility_add` from `/raw/Ship%20Types/<id>`:

```python
import requests
d = requests.get("http://localhost:8950/raw/Ship%20Types/ship_type_nuclear_submarine").json()
val = d[1]['modifier'][1]['ship_visibility_add'][1]   # → '3'
```

Note `d[1]` (skip the leading operator), then dict access, then `[1]` again at each level. Values come back as **strings**, not numbers — cast with `float()` / `int()` if doing math. For surveys across many entities, prefer the structured endpoints (`/laws`, `/production-methods`, etc.) or import `mod_state` directly — `/raw/` is best when you need every field including triggers and AI-weight blocks that the structured endpoints flatten.

#### Analytical Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/references/<key>` | GET | Find all entities referencing a given key |
| `/tech-tree/<tech_id>` | GET | Full prerequisite chain + unlocks |
| `/modifier-search?q=<pattern>` | GET | Find modifier field names matching pattern |
| `/modifier-grants/<name>?scope=both&limit=200` | GET | **Reverse modifier-grant lookup** — every entity that *grants* modifier `<name>` (the inverse of `/engine-docs/usage`, which only finds effect/trigger call sites). Scans Laws, Technologies, Power Bloc Principles, Amendments, Decrees, Buildings, and Static Modifiers by file (the parser drops file/line, so this is a direct file scan). Returns `{entity_type, entity_id, origin, file, line, value, block}` per grant site. `scope=mod\|vanilla\|both` (default `both`); `block` is the modifier bag the grant lives in (`modifier`, `member_modifier`, `institution_modifier`, `tax_modifier_high`, `direct` for static modifiers, …). **First stop for any modifier rebalance** ("which laws/techs/principles grant X, and at what value?"). Note: under `scope=both` a value the mod INJECTs into a vanilla entity appears twice (vanilla + mod patch) for the same `entity_id`; `origin` disambiguates — use `scope=mod` for the mod's effective additions only. |
| `/unlocked-by/<tech_id>` | GET | All laws, buildings, PMs, units unlocked by a tech (each entry now carries a `type` field — required by the universal `?annotate=` post-processor; see below). |
| `/tech-unlocks` | GET | Bulk inverted index: every mod-side tech mapped to the entities that depend on it (`Buildings`, `Combat Unit Types`, `Decrees`, `Laws`, `Mobilization Options`, `Parties`, `PMs`, `Ship Modifications`, `Ship Types`). Per-tech shape is `{by_type: {<EntityType>: [{type,id,file,source}]}, summary: {<EntityType>: count}, n_total: int}`. Filters: `?source=mod\|vanilla\|all` (default `mod`), `?era=era_6` / `?eras=era_6,era_7` to filter by source-tech era, `?summary=true` drops `by_type` lists, `?refresh=true` rebuilds the cache. Combine with `?annotate=` for inline strength signals (e.g. PM `flag` / `margin_pct` via the `balance` annotator). Cached on first call after each `/reload`. **Clausewitz merge-directive prefixes (`INJECT:foo`, `REPLACE:foo`, `REPLACE_OR_CREATE:foo`) are stripped before indexing**, so an entity declared as `REPLACE_OR_CREATE:building_synthetics_plant_rubber` correctly attributes to its underlying `building_synthetics_plant_rubber` id. |
| `/tech-unlocks/<tech_id>` | GET | Single-tech entry from the inverted index — same shape as one value of `/tech-unlocks`. |
| `/annotators` | GET | List every registered annotator with its `name`, `entity_type`, `fields`, and `description`. Use to discover what `?annotate=<name>` values are valid against entity-listing endpoints. Today: `balance` for `PMs`. New annotators register at server startup by importing their owning module. |
| `/filter/<EntityType>?field=<name>&value=<val>` | GET | Filter entities by field value |
| `/unlocalized` | GET | Find all entities missing localization keys. `?type=Modifiers` filters to one type. `?mod_only=false` includes vanilla. Returns structured JSON with `total_entities_with_missing_loc`, `total_missing_keys`, and `by_type` breakdown. Supported types: Modifiers, Technologies, Buildings, Building Groups, Laws, Institutions, Decrees, Events, PMs, PM Groups, Modifier Types, and more (24 total). |

##### Annotator post-processor (`?annotate=<name>[,<name>...]` or `?annotate=all`)

Wired centrally into `route()`. Walks the response tree, finds every dict
that carries both a `type` field and an `id` field, and merges fields
from the requested annotators into each match. Unknown annotator names
are silently skipped, so `?annotate=all` is a forward-compatible "give
me everything that applies" idiom.

- Default request (no `?annotate=`) is a pure pass-through: zero
  overhead.
- All entity-listing endpoints participate — `/laws`, `/buildings`,
  `/technologies`, `/production-methods`, `/raw/<type>/<id>`,
  `/references/<key>`, `/tech-tree/<id>`, `/unlocked-by/<id>`,
  `/tech-unlocks`, `/keys/<EntityType>`, etc. Future entity-list
  endpoints just need to set `type=<EntityType>` on their entries.
- Adding a new annotator is import-time only: write a
  `<thing>_balance_lib.py` that calls `annotators.register(...)`, import
  it once in `mod_state_server.py`, and `?annotate=<name>` works
  everywhere immediately. No endpoint changes required.

Today's registered annotator: `balance` for `PMs` — adds
`flag` (`HIGH-PROFIT` / `DEEP-LOSS` / `THROUGHPUT` / `HIGH-WAGE` /
`LOW-WAGE` / `OK` / `NO-COSTS`), `margin_pct`, `wage_be`. Computed
from the auto-generated cost-comment block in PM bodies via
`pm_balance_lib.build_pm_balance_map`.

#### Technology & Engine Research Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/technology-effects/<tech_id>` | GET | ALL effects of a technology: direct modifiers, unlocked PMs (with modifier details), buildings, combat units, laws, institutions, decisions, journal entries, diplomatic actions, company types, mobilization options, and dependent technologies |
| `/engine-docs` | GET | List available engine doc types with entry counts |
| `/engine-docs/<type>` | GET | List all entries of a type (effects, triggers, modifiers, event-targets, on-actions, custom-localization) |
| `/engine-docs/<type>?q=<search>` | GET | Search entries by name or description |
| `/engine-docs/<type>?scope=<scope>` | GET | Filter by scope (e.g. `?scope=building`, `?scope=country`) |
| `/engine-docs/<type>?mask=<mask>` | GET | Filter modifiers by mask |
| `/engine-docs/<type>?group=true` | GET | Group similar modifiers by pattern (e.g. `building_{name}_throughput_add`) |
| `/engine-docs/<type>?limit=<n>` | GET | Limit results (default 500) |
| `/engine-docs/<type>?origin=vanilla\|mod` | GET | Filter by origin tag (modifiers + custom-localization only) |
| `/engine-docs/origin/<name>` | GET | Disambiguation lookup: returns the origin (`vanilla` or `mod`) of a modifier / trigger / effect / event_target / on_action / custom_localization name across all doc types **plus the full schema** (description, example, scopes, traits, reads, targets). Use before assuming a name is engine-native — the recurring "is this engine-recognized or mod-declared?" question. Also use as a one-curl trigger-schema lookup: "does `is_in_geographic_region` exist, what scope, what syntax?". Vanilla entries the mod cosmetically redeclares are tagged `mod_redeclares=true` while origin stays `vanilla` (engine semantics are vanilla's). Mod-only entries include `defined_in`. |
| `/engine-docs/usage/<name>` | GET | Real-world call sites of `<name>` from vanilla `common/`. Returns file:line + 4-line snippets per hit (params `limit`, `before`, `after`, `include_defs`). Use when the engine docs don't cover an identifier (post-1.13.5 `triggers.log` is missing names like `has_treaty_defensive_pact_with`, `has_treaty_alliance_with`) or when you want canonical argument shapes from real script. Default filter excludes column-0 definitions and `trigger_localization/` label cross-references. ~6s per query on WSL+NTFS. |
| `/engine-docs/loc-functions[/<name>]` | GET | Index of loc-rendering data-system functions (`GetStaticModifier`, `GetValueWithBreakdownFor`, `GetNameNoFormatting`, `Concept`, `AddTextIf`, `sCharacter`, …) discovered by scanning vanilla `localization/english/` + `gui/` for `[...]` expressions. List form returns 8.8k tokens sorted by count; single-entry form returns up to 8 example expressions with file:line. Params: `q`, `kind` (function / method / scope / accessor), `min_count`, `limit`, `include_examples`. Use when researching the canonical loc idiom for a feature — answers "is there a function to render the effect list of a static modifier?" in one curl instead of grepping the loc tree. Lazy-built on first request (~3s), cached for the server lifetime. |
| `/dev-docs` | GET | List all developer reference .md files from base game, grouped by directory |
| `/dev-docs/<directory>` | GET | Get developer reference doc(s) for a directory (e.g. `production_methods`, `buildings`, `journal_entries`) |
| `/dev-docs/<dir>/<file>` | GET | Get a specific .md file by path |
| `/dev-docs?q=<search>` | GET | Search across all developer reference docs |

#### Validation & Mod Hygiene Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/validate/engine-coverage` | GET | Walk every loaded mod entity, cross-reference modifier-shaped keys against (vanilla engine docs ∪ mod-side `common/modifier_type_definitions/`) and the modifier-pattern catalog. Suffixes covered: `_add`, `_mult`, `_max_level(s)`, `_set`, `_bool`, `_boolean`. Also walks `modifier:NAME = yes` trigger references (used in JE `possible` clauses, scripted_triggers, etc.) and validates the NAME side through the same classifier — catches the country_sr_*_program_bool class of regression where an undeclared boolean silently no-ops. Names defined as Script Values are pre-filtered (they end in `_mult`/`_add` but appear in `multiplier =` / `limit = { X > 0 }`, not as modifier reads). Pop Needs and Script Values entity types are skipped entirely. Returns full `unknown_modifiers` and `suspicious_modifiers` lists. **For a healthy mod, the expected result is `0 unknown / 0 suspicious`** — anything non-zero is real signal (typo, missing pattern registration, or vanilla rename). Unit + integration tests at `test_engine_coverage_validator.py` freeze the boolean-coverage paths against future regressions. |
| `/validate/engine-coverage?summary=true` | GET | Same, but return only the `summary` counts and metadata (no entity lists). |
| `/validate/engine-coverage?filter=vanilla_breakages` | GET | Now redundant — mod-defined modifier types are folded in by default. Kept for back-compat; behaves as a no-op. |
| `/validate/engine-coverage?refresh=true` | GET | Force re-run of the validation (default: cached after each `/reload`). |
| `/validate/modifier-visibility` | GET | Flag modifier values too small to display given the modifier type's `decimals = N` (and `percent = yes/no`) precision — e.g. `country_prestige_mult = 0.005` renders as "+0%" because the type is `decimals=0 percent=yes`. The modifier still applies mechanically, only the tooltip rounds to 0. Returns `{summary, flagged: [{file, line, modifier, value, decimals, percent, min_visible}, ...]}`. Suppress an intentional sub-threshold value with a same-line `# REVIEWED YYYY-MM-DD: rationale` comment. Report mirror: `docs/engine/modifier_visibility_report.md`. |
| `/validate/modifier-visibility?include_reviewed=true` | GET | Also include the reviewed-exemptions list in the response (default: counts only). |
| `/validate/modifier-visibility?summary=true` | GET | Counts only — no per-flag details. |
| `/duplicate-images` | GET | Flag images reused across entities of types where vanilla holds "one image per entity": Buildings (`icon`), Goods (`texture`), Decrees (`texture`), Technologies (`texture`), Interest Groups (`texture`), Laws (`icon`). Permissive types (Events, Journal Entries, Production Methods, Ideologies, Combat Units) are intentionally not scanned — vanilla shares images across many of those by design. Groups by **content hash** (md5 of the resolved `.dds` file, mod overlay first then vanilla), so two entities pointing at different filenames whose files have identical bytes still cluster — catches the case where a placeholder file was duplicated under N names. Each cluster carries `kind: "path"` (single shared filename) or `kind: "content"` (multiple distinct filenames, identical bytes). Defaults to mod-only mode: clusters with no mod-side entities are suppressed. Allowlist at `common/_meta/duplicate_image_allowlist.yml`, keyed by lowercase entity-type slug. Each entry uses either `image: <path>` (single, for path dupes) or `images: [<path>, …]` (multiple, for content dupes) plus the exact `entities:` list that may share — adding a new entity or a new identical-content file re-flags the cluster, forcing a fresh review. Query params: `?include_vanilla=true`, `?include_allowlisted=true`, `?type=Buildings` (repeatable / comma-separated), `?format=text`. Tests: `test_duplicate_images.py` (unit, fake ModState; injects a fake hasher so content-dup tests don't need real .dds files) plus an env-gated `VanillaSanityTest` (set `VIC3_RUN_VANILLA_TESTS=1`) that asserts each strict type stays under 10 vanilla-only flags. |
| `/auto-generated` | GET | Return the file → generator-script ownership map. Helps tools and devs answer "is this file safe to hand-edit?" Mirrors `docs/auto_generated_files.md` in machine-readable form. |

### Query Examples (PowerShell)
```powershell
# List all laws
Invoke-RestMethod http://localhost:8950/laws

# Get detailed info for a specific law
Invoke-RestMethod http://localhost:8950/laws/law_monarchy

# Localize a game key
Invoke-RestMethod http://localhost:8950/localize/law_monarchy

# Reverse-localize
Invoke-RestMethod http://localhost:8950/unlocalize/Monarchy

# Search across all entities
Invoke-RestMethod "http://localhost:8950/search?q=nuclear"

# Deep JSON output
(Invoke-RestMethod http://localhost:8950/laws) | ConvertTo-Json -Depth 10

# Find references to a technology
(Invoke-RestMethod "http://localhost:8950/references/infrastructural_concrete") | ConvertTo-Json -Depth 5

# Filter entities
(Invoke-RestMethod "http://localhost:8950/filter/Technologies?field=era&value=era_5") | ConvertTo-Json -Depth 5

# List all mod events with space images
(Invoke-RestMethod "http://localhost:8950/events?image=space") | ConvertTo-Json -Depth 3

# Get all PMs for a building
(Invoke-RestMethod "http://localhost:8950/production-methods?building=building_government_administration") | ConvertTo-Json -Depth 4

# List journal entries
(Invoke-RestMethod "http://localhost:8950/journal-entries") | ConvertTo-Json -Depth 3

# Get institution detail with modifiers
(Invoke-RestMethod "http://localhost:8950/institutions/institution_social_security") | ConvertTo-Json -Depth 3

# Get ALL effects of a technology (modifiers, unlocked PMs/buildings/units/laws, dependents)
(Invoke-RestMethod "http://localhost:8950/technology-effects/nuclear_energy") | ConvertTo-Json -Depth 5

# Search engine docs for effects related to modifiers
Invoke-RestMethod "http://localhost:8950/engine-docs/effects?q=add_modifier&limit=10"

# Find all building-scope event targets
Invoke-RestMethod "http://localhost:8950/engine-docs/event-targets?scope=building"

# Group similar modifiers by pattern
Invoke-RestMethod "http://localhost:8950/engine-docs/modifiers?q=throughput&group=true"

# Get the developer reference template for production methods
(Invoke-RestMethod "http://localhost:8950/dev-docs/production_methods").content

# Search developer reference docs for a specific field
(Invoke-RestMethod "http://localhost:8950/dev-docs?q=unlocking_laws") | ConvertTo-Json -Depth 3
```

### Query Examples (Python Client)
```powershell
python mod_state_client.py status
python mod_state_client.py laws law_monarchy
python mod_state_client.py localize law_monarchy
python mod_state_client.py search nuclear
python mod_state_client.py references law_anarchy
python mod_state_client.py tech-tree nuclear_energy
python mod_state_client.py modifier-search goods_output
```

### AI Agent Workflow

1. **Check server:** Verify with `Invoke-RestMethod http://localhost:8950/status`. If down, start in a background terminal.
2. **Localize / unlocalize:** `/unlocalize/Monarchy` → `law_monarchy`, `/localize/law_monarchy` → "Monarchy".
3. **Search first:** When unsure of exact IDs, use `/search?q=...`.
4. **Prefer structured endpoints** (`/laws`, `/technologies`, `/buildings`) over `/raw`.
5. **Use `/raw` for full data** when you need every field (triggers, effects, modifiers, AI weights).
6. **After editing mod files:** `POST /reload` to pick up changes without restarting. Note: `/reload` re-parses data files, NOT Python code. To pick up Python code changes, restart the server process.
7. **Entity types use display names with spaces** (e.g. "PM Groups"). URL-encode as `%20`.
8. **Validate modifier names** with `/modifier-search?q=<substring>` or `/engine-docs/modifiers?q=<substring>` before using them.
9. **Cross-reference** with `/references/<key>` to find all entities using a given key.
10. **Tech dependencies:** `/tech-tree/<tech_id>` for prerequisites, `/technology-effects/<tech_id>` for comprehensive effects.
11. **Look up triggers/effects by scope:** `/engine-docs/effects?scope=country`, `/engine-docs/triggers?scope=building`.
12. **Developer reference templates:** `/dev-docs/production_methods`, `/dev-docs/buildings`, etc. for official game developer documentation of entity file structures.
13. **Hit a capability gap? File an issue.** If the server can't answer a question it structurally should, or you find yourself falling back to manual `git grep` / file-reading / by-hand cross-referencing or validation that an endpoint could automate, open a GitHub issue (`gh issue create --label enhancement --label tooling`) proposing the endpoint — including the exact query you needed, the desired URL + return JSON, and the manual fallback you used — then proceed with the workaround for now. This is how `/modifier-grants/<name>` (#128) came to be: a homeland rebalance fell back to raw grep because nothing answered "which laws/techs/principles grant modifier X". See CLAUDE.md § "File issues for mod-state-server capability gaps".

### Direct Import for Python Generators

For Python scripts that need bulk data (e.g., iterating over all 254 buildings), **import `mod_state` directly** instead of making HTTP calls. The HTTP server can become unstable under rapid sequential requests.

```python
from mod_state import ModState
from path_constants import base_game_path, mod_path

# Only load the entity types you need
ENTITY_PATHS_BASE = {
    "Buildings": base_game_path + r"\game\common\buildings",
    "PM Groups": base_game_path + r"\game\common\production_method_groups",
}
ENTITY_PATHS_MOD = {
    "Buildings": mod_path + r"\common\buildings",
    "PM Groups": mod_path + r"\common\production_method_groups",
}

ms = ModState(ENTITY_PATHS_BASE, ENTITY_PATHS_MOD)
buildings = ms.get_data("Buildings")  # dict of id -> parsed entity
```

Helper functions for navigating parsed data:
```python
def get_entity_data(entity_tuple):
    """Extract inner data dict from ('=', {...}) entity tuple."""
    if isinstance(entity_tuple, tuple) and len(entity_tuple) >= 2:
        data = entity_tuple[1]
    else:
        data = entity_tuple
    if isinstance(data, list):
        flat = {}
        for item in data:
            if isinstance(item, dict):
                flat.update(item)
        return flat
    return data

def get_field(data, key, default=None):
    """Get value from entity data, unwrapping ('=', value) tuples."""
    val = data.get(key) if isinstance(data, dict) else None
    if val is None:
        return default
    if isinstance(val, tuple) and len(val) >= 2:
        return val[1]
    return val
```

These helpers are defined in `mod_state_server.py` but are simple enough to copy into generator scripts. See `gen_building_transfer.py` for a complete example.

> **Rule of thumb:** Use HTTP for quick interactive lookups (1–10 queries). Use direct `ModState` import for batch operations (iterating entire entity types).

### Gotchas when writing tooling that walks `common/`

Three things that have bitten audit scripts and the inverted-index walker
in this repo. Worth knowing before writing a new walker.

**1. Strip Clausewitz merge-directive prefixes before matching IDs.** The
mod uses `INJECT:foo`, `REPLACE:foo`, and `REPLACE_OR_CREATE:foo`
extensively (~250 entities across the unlock-source dirs alone). A
naïve identifier regex like `[A-Za-z_][A-Za-z0-9_]*` won't match
`REPLACE_OR_CREATE:building_synthetics_plant_rubber` and that entity
silently falls out of the walk — its `unlocking_technologies` (and any
other field) goes uncounted. The engine resolves directive-prefixed
keys to the underlying entity, so tooling should too. Reference
implementation: `tech_unlocks_lib.iter_top_level_blocks` (`tech_unlocks_lib.py`).
Test: `test_tech_unlocks_lib.test_clausewitz_merge_directive_prefixes`.

**2. `ms.mod_parsers` keys are space-separated, not directory-named.**
`production_methods/` → `"PMs"`, `combat_unit_types/` → `"Combat Unit Types"`,
`mobilization_options/` → `"Mobilization Options"`, `ship_types/` →
`"Ship Types"`, etc. (See `base_game_paths` / `mod_paths` at the top of
`mod_state_server.py` for the full list.) When registering an
annotator, tagging entries with `type=<EntityType>`, or calling
`ms.get_data(<EntityType>)`, use these exact keys — the post-processor
matches strings, so `"ProductionMethods"` silently mismatches `"PMs"`
with no error.

**3. Cost comments are stripped by `paradox_file_parser`.** PMs ship
with auto-generated cost summaries (`# Total input cost: ...`,
`# Profit margin: ...`, `# Wage breakeven: ...`) emitted by
`pm_costs.py`, but the parser tokenizer drops comments at load time.
Tooling that needs cost data — including the `balance` annotator's
`compute()` — must re-read PM files directly off disk rather than
going through `ms.get_data("PMs")`. `pm_balance_lib.build_pm_balance_map`
is the canonical implementation; reuse it via the annotator registry
rather than re-parsing comments.
