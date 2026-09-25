# Python Tools & Mod State Server

Reference for all Python utility scripts and the background data server.

## Path Constants

`path_constants.py` — Defines `mod_path`, `base_game_path`, `doc_path`. Imported by nearly all other scripts.

Only `mod_path` and `doc_path` are computed at import; every per-machine path (`base_game_path`, `mod_deploy_target`, `vanilla_*`, `game_logs_path`, `vic3_modding_digests_path`, the `mod_loaded_docs_path` alias and the derived `vanilla_snapshot_docs_path_default`) resolves lazily on first attribute access through a PEP 562 module `__getattr__`, then caches. `from path_constants import base_game_path` behaves exactly as before — same `RuntimeError` + `python3 scripts/setup.py` hint when unresolvable, just raised at the importing module rather than at `path_constants` import. Practical effect: mod-only tools (`duplicate_key_audit`, `any_limit_audit`, `loc_render_audit`, `kill_character_audit`, …) and most of the test suite run on a machine with no Victoria 3 install. Add a new constant by registering it in `_LAZY_SPECS`, not by assigning it at module scope. When writing a CLI that needs vanilla only for one subcommand, import that constant inside the branch (see `effect_trigger_validity_audit.py`'s `bootstrap`) so the common path stays install-free. One caveat: `hasattr(path_constants, 'base_game_path')` and `getattr(path_constants, 'base_game_path', fallback)` raise the setup `RuntimeError` on an unresolved path instead of returning `False`/the default — both only swallow `AttributeError` — so probe with `'base_game_path' in vars(path_constants)` or catch `RuntimeError`.

## Auto-run on server reload

`mod_state_server.py` runs a chain of idempotent transformers after every full ModState load (server startup and `POST /reload`). The canonical rosters are `POST_LOAD_REGENERATORS` (the 12 file-rewriting generators) and `POST_LOAD_AUDITS` (the 16 read-only audits) in `mod_state_server.py`; the default reload runs `POST_LOAD_GENERATORS = POST_LOAD_REGENERATORS + POST_LOAD_AUDITS`. Each entry must expose `regenerate(mod_state=None)` and finish in well under a second. Failures are logged with `[post-load] <name> FAILED`, recorded in the reload response's `warnings` array, and skipped — they don't block startup. `POST /reload?engine_only=true` bypasses `_load_mod_state` and so skips these; `POST /reload?audits_only=true` runs only `POST_LOAD_AUDITS` (no working-tree side effects beyond `docs/engine/*_report.md`).

**Audit warnings**: when a generator's return dict contains `unreviewed > 0` or `hard_fails > 0`, the runner logs `[post-load WARN] <label> surfaced issues: <key>=<n>` at WARNING level and adds an entry to the `/reload` response's `warnings` array — caller sees regressions in the same response, no log-scraping required. Add new actionable counter names to `_POST_LOAD_WARN_KEYS` in `mod_state_server.py` if a new audit invents one.

**Crash warnings**: a step that *fails* (ImportError, an exception inside `regenerate()`, no `regenerate` attribute) also lands in `warnings`, as `{label, module, error, traceback_tail}` — before, it was logged and dropped, so `POST /reload` answered `{"status": "reloaded"}` while a whole audit had silently not run. `POST /reload?engine_only=true` reports its two steps (`engine_docs`, `engine_coverage_validation`) the same way. So `warnings` entries come in two shapes: findings carry `counts`/`summary`, crashes carry `error`/`traceback_tail`.

**Writers run after the parse**: the file-rewriting regenerators write to disk without updating the in-memory parse. The runner content-hashes the mod's tracked `.txt`/`.yml` under `common/`, `events/`, `localization/` before and after that half of the chain; if anything actually changed, it re-parses the mod side **once** (`ms.reload_mod` + loc re-layer) before running `POST_LOAD_AUDITS`, so the audits — and `/raw`, `/localize` — see the regenerated content in the same reload. Content hashing (not mtime) is deliberate: several generators rewrite their output unconditionally, and a stat-only check would re-parse on every reload. The response reports `generators_wrote_files: [<mod-relative paths>]` plus `reparsed_after_generators: <bool>`; if that bool is `false`, the re-parse failed (see the `post_load_reparse` warning) and a second `/reload` is needed.

#### `POST_LOAD_REGENERATORS` — file-rewriting generators (in run order)

| Module | Output |
|---|---|
| `pop_needs_curves` | `common/buy_packages/00_buy_packages.txt` |
| `apply_ideologies` | `common/ideologies/modified.txt` |
| `ig_feminism` | `common/interest_groups/00_*.txt` |
| `pm_costs` | cost-comment headers in `common/production_methods/extra_pms.txt` & `unique_pms.txt` and in the `upkeep_modifier` blocks of `common/combat_unit_types/extra_combat_units.txt` & `common/mobilization_options/extra_mobilization_options.txt`; `common/script_values/auto_combat_unit_market_costs.txt`; the `Cost at …` suffixes in `localization/english/te_combat_units_l_english.yml`; `docs/engine/commented_vanilla_pms.txt`; `docs/engine/commented_vanilla_military_units.txt` |
| `resources` | `map_data/state_regions/*.txt` |
| `gen_pb_principle_unlock_descs` | `*_pb_principles_bool_desc` keys in `localization/english/te_power_bloc_unlocks_l_english.yml` |
| `gen_un_button_descs` | `localization/english/te_un_button_effects_l_english.yml` |
| `gen_law_consistency` | `common/scripted_effects/extra_law_consistency_generated.txt` |
| `gen_company_building_cleanup` | `common/scripted_effects/company_building_cleanup_effects.txt` — one `remove_building` guard per company building plus `remove_disbanded_company_buildings_effect`. The only roster entry that lives under `scripts/generators/`; it is imported by dotted path (`scripts.generators.gen_company_building_cleanup`), see § "Adding a new post-load generator". |
| `organize_loc` | `localization/english/te_*_l_english.yml` (29 category files) |
| `gen_event_inventory` | `docs/engine/event_image_inventory.md` |
| `bom_normalizer` | **Runs last.** Prepends the UTF-8 BOM to any mod `.txt` under `common/`, `events/`, `gfx/` and any `.gui` under `gui/` that lacks one, so the engine stops warning `should be in utf8-bom encoding`. Writes no new files; only rewrites files missing the BOM, so a clean tree stays clean. |

#### `POST_LOAD_AUDITS` — read-only audits (in run order)

Every row writes only its report under `docs/engine/`, so `?audits_only=true` leaves the rest of the working tree untouched.

| Module | Output |
|---|---|
| `event_magnitude_audit` | `docs/engine/event_magnitude_report.md` — hardcoded fast-scaling resource deltas in event effects. Also exposed live at `/event-magnitude-audit`. |
| `modifier_visibility_audit` | `docs/engine/modifier_visibility_report.md` — modifier values too small to display given the type's `decimals = N` / `percent` precision. Also exposed live at `/validate/modifier-visibility`. |
| `kill_character_audit` | `docs/engine/kill_character_audit.md` — `kill_character` call sites audited for void6 / `exists` guards. |
| `loc_coverage_audit` | `docs/engine/loc_coverage_report.md` — mod-introduced entities (modifiers, JEs, scripted buttons, treaty articles, …) with no `*_l_english.yml` key, which the engine renders as the raw key with no warning. Suppress on the entity-opening `<name> = {` line. |
| `concept_reference_audit` | `docs/engine/concept_reference_report.md` — `[concept_X]` / `[Concept('concept_X', …)]` loc references to concepts not declared in `common/game_concepts/`. Each unresolved ref logs three error lines *per render* and stalls the panel showing it. Suppress trailing on the loc value line. |
| `localization_accessor_audit` | `docs/engine/localization_accessor_report.md` — `[X.Y.Z]` accessor chains in loc YAML the engine would silently resolve to the empty string. Catalog seeded from vanilla loc; supplement in `localization_accessor_vanilla_extras.py`. |
| `mod_structure_audit` | `docs/engine/mod_structure_report.md` — flags brace-balance failures, silent-INJECT failures (INJECTs targeting mod-only or REPLACEd entities), and within-namespace top-level collisions. Subdirs that merge by design (`on_actions/`, `defines/`, `history/`) are excluded from collision detection. |
| `loc_render_audit` | `docs/engine/loc_render_report.md` — four checks. `bracket_tag`: bracket-style formatting tags (`[b]`, `[/i]`, …) in loc values. Vic3 has no such tags; the engine treats `[b]` as a failing data-system-function and floods the log, causing in-game lag. `nested_brackets` (added 2026-09-20): a `[` opened inside an unclosed `[...]`, e.g. `[SelectLocalization( [GetScriptedGui(…)], …)]` — the loc parser does not nest, the whole value fails to parse, and the widget pointing at the key logs `Failed parsing localized text`; single-quoted runs are skipped. Both are vanilla- and mod-clean, so they are pure regression guards. `quoted_arg_expansion` (added 2026-09-25): a `$key$` inside a single-quoted data-function argument whose mod loc value contains `[` or `'`, which breaks the string literal (the UN button effects' `Concept('…','$un_peacekeeping_contributor_modifier$')`). `quoted_name_apostrophe` (added 2026-09-25): a straight `'` in the rendered name of a mod static modifier or modifier type, which vanilla's add-modifier tooltip pastes into `GetRawTextTooltipTag('…')` ("Women's Integration"). Both read `common/static_modifiers/` and `common/modifier_type_definitions/` plus mod loc directly, so `--strict` still needs no game install. (An `#…#!` balance check was scoped out — 2341 vanilla false positives; Vic3 splits formatting across concatenated loc fragments.) |
| `any_limit_audit` | `docs/engine/any_limit_report.md` — flags `limit = { }` placed as an immediate child of an `any_*` counting trigger (silently ignored by the engine → meaning flip). Discriminates correctly: a `limit` inside a nested `every_*`/`trigger_if` within the `any_*` is legitimate and not flagged. |
| `iterator_limit_audit` | `docs/engine/iterator_limit_report.md` — flags an `every_*`/`random_*`/`ordered_*`/`any_*` block whose `limit = { }` is written after an effect sibling. An iterator's `limit` filters the whole iteration regardless of position, so the earlier effect is silently gated too (issue #250). Iteration properties may precede `limit` without a flag: `order_by`/`max`/`count`/…, a list iterator's `variable`/`list`, and a container iterator's `tag`/`tags`/scalar `parent`. Raw-text scan: the parser folds repeated keys to the first occurrence and drops line numbers, so source order is not recoverable from it. |
| `modifier_multiplier_var_audit` | `docs/engine/modifier_multiplier_var_report.md` — flags a permanent `add_modifier = { … multiplier = var:X }` (no `days`/`months`/`years`) followed later in the same top-level block by `remove_variable = X`. The engine re-evaluates the stored multiplier on later ticks, so the removed variable reads `'none'` (issue #250). Quiet for the clean-up shape where an exclusive branch drops the modifier first. |
| `pm_employment_audit` | `docs/engine/pm_employment_report.md` — for each building, enumerates the *valid* PM combinations (one per group, honoring `unlocking_production_methods`) and flags any profession whose employment total goes negative in some combination. Catches automation/refinement PMs whose negative `building_employment_*_add` exceeds the lowest base PM's employment (e.g. a 0-employment base + a strong automation reduction). Buckets by scaling context; ignores tech/principle gating (late-game reachable). Mod-relevant flags warn; all-vanilla combos are informational only. |
| `orphaned_event_audit` | `docs/engine/orphaned_event_report.md` — `is_triggered_only = yes` events that no `trigger_event` or dispatch list ever references. The engine only reports `Event X is orphaned` at runtime game-start (issue #147). |
| `effect_trigger_validity_audit` | `docs/engine/effect_trigger_validity_report.md` — effect/trigger keywords absent from the frozen catalog at `docs/engine/effect_trigger_valid_keys.txt` (and `funcname(...)` call-syntax). The engine only reports `Unknown effect X` at game-load (issue #146). Scans every directory in `SCAN_ROOTS` — events, the scripted helpers, on-actions, and the script-bearing `common/` entity dirs (#288/#295) — with each `ScanRoot` declaring its file format's entity-schema fields (`extra_valid`) and the blocks to skip (`skip_blocks`, the static-modifier containers `modifier_visibility_audit` owns). Flags in call form (`x = yes` / `x = { … }`) are reported as `unresolved-helper-call` and also served by `GET /scripted-helpers/unresolved`. The catalog itself is a one-shot bootstrap, **not** regenerated per reload — refresh it on a vanilla bump with `effect_trigger_validity_audit.py bootstrap`, which harvests from the same roots. |
| `duplicate_key_audit` | `docs/engine/duplicate_key_report.md` — repeated scalar keys *inside* one block (e.g. a modifier bag). Vic3's own `Duplicated key X will not be created` warning only fires for top-level entity collisions; a duplicate inside a block silently last-wins (issues #190, #191). |
| `attitude_key_audit` | `docs/engine/attitude_key_report.md` — `attitude = <bareword>` values outside the engine's fixed 15-key catalog. An unknown key never matches, so the AI weight or refusal gate keyed on it is dead code, with no parse-time warning. |
| `event_image_audit` | `docs/engine/event_image_report.md` — visible events declaring no `event_image` and no alternate art (`gui_window` / `left_icon` / `right_icon`). The default event window has no fallback art, so these render the engine's magenta missing-texture placeholder, with no log line of any kind. All of vanilla has one such event (`test.120`). Issue #353. |
| `treaty_leverage_side_audit` | `docs/engine/treaty_leverage_side_report.md` — a directed treaty article whose `country_treaty_leverage_generation_add` sits in the same side's modifier block as the side named by `maintenance_paid_by`. The modifier generates leverage *against* its carrier, so the beneficiary (who pays the upkeep) must not also hold it. Engine-silent when inverted — valid modifier, valid block, influence just flows the wrong way. Vanilla's six leverage-bearing articles all conform. |
| `event_context_audit` | `docs/engine/event_context_report.md` — events whose text does not match the context they fire in. Builds a dispatch graph of every mod event (each `trigger_event` / on-action `events` list, through scripted effects — including `$EVENT$`-parameterised helpers — immediates and on-action chains, with each site's scope switches and enclosing `limit`/`trigger` guards) and flags three heuristic classes for a human read: **`system_ungated`** — title/description talks about a mod system (spies, bank runs, a space programme, a nuclear standoff, the UN, …) but the event reads none of that system's state and not every dispatch site is gated on it (the class PR #418 fixed by hand); **`unchosen_self_action`** — the text says the *recipient* did something ("our information campaign") though it can arrive from a pulse, a journal-entry tick or another country's option; **`imputed_foreign_action`** — the event picks another country itself, says it acted, and lands relations/modifiers/follow-ups on it. Suppression is **check-tagged** and goes anywhere inside the event block (conventionally its own line) — `# REVIEWED YYYY-MM-DD (<check>): rationale`, or `(all)` — because an opening-line comment is already read by `orphaned_event_audit`, `loc_coverage_audit` and `event_image_audit`. Console-only `te_debug_*` events are skipped. M_NEW2 #2/#3 in `docs/audits/open_issues.md`. |


**Offline exit-code mode (what CI runs).** Eleven of these audits are pure file scans — they never build a `ModState`, so they run with nothing but the dummy `VIC3_*` paths and are wired into `.github/workflows/ci.yml`. Each prints its report to stdout and signals findings through its exit status:

| Command | Exits 1 when |
|---|---|
| `python3 duplicate_key_audit.py --strict` | an unexempted **`error`**-severity flag exists (a repeated key with a *differing* value). `warn`-severity identical repeats (`add = 5 add = 5`) are reported but do **not** fail: the engine runs both on purpose, and the ones in the tree come from non-idempotent generators re-emitting a line (#191). |
| `python3 any_limit_audit.py --strict` | any unexempted flag exists |
| `python3 loc_render_audit.py --strict` | any unexempted flag exists |
| `python3 orphaned_event_audit.py --strict` | any unexempted flag exists |
| `python3 iterator_limit_audit.py --strict` | any unexempted flag exists |
| `python3 modifier_multiplier_var_audit.py --strict` | any unexempted flag exists |
| `python3 kill_character_audit.py --check` | any unexempted flag exists (`--check`, not `--strict`) |
| `python3 attitude_key_audit.py` | any unexempted flag exists — **no flag at all**; `main()` returns the exit code natively, so passing `--strict` does nothing |
| `python3 event_image_audit.py --strict` | any unexempted flag exists |
| `python3 treaty_leverage_side_audit.py --strict` | any unexempted flag exists |
| `python3 event_context_audit.py --strict` | any flag without a check-tagged `# REVIEWED YYYY-MM-DD (<check>): …` comment inside the event, or any such comment that suppresses nothing (stale — the check no longer fires there — or a misspelled check name) |

"Unexempted" always means "without an inline `# REVIEWED YYYY-MM-DD: rationale` comment in the suppression position that audit documents". The other eight audits stay out of CI. Six need a live `ModState` (vanilla data, loc index). Two do not and run fine with CI's dummy `VIC3_*` paths — handy from a sparse worktree: `python3 effect_trigger_validity_audit.py` (**always exits 0** — read the `Flags (unreviewed)` line, e.g. `| grep -iE 'unreviewed|unresolved'`) and `python3 localization_accessor_audit.py --report` (exits 1 when `unreviewed > 0`). Run standalone, the thirteen offline audit CLIs (the eleven in CI plus these two) print to stdout and leave `docs/engine/` alone — only the post-load chain writes the reports.

CI's other two game-independent checkers are `scripts/analysis/check_localization_files.py` (loc BOM / `l_english:` header / duplicate keys) and `scripts/analysis/check_dds_dimensions.py` (block-compressed textures need both dimensions divisible by 4; known offenders in `scripts/analysis/dds_dimension_allowlist.txt`). Note that the latter's **stale-allowlist check runs only on the default full-`gfx/` sweep** — pass a path and the scan narrows, so an allowlist entry outside it is unvisited rather than dead. `scan()` takes `check_stale`, and `main()` sets it from "were any positional roots given", so a clean partial scan can't exit 1 on entries it never looked at.

**Opt-out:** Set `VIC3_SKIP_POST_LOAD_GENERATORS=1` in the server's environment to skip the entire post-load batch (useful while iterating on one of these scripts).

**Watcher safety:** The deploy watcher (`scripts/watch_deploy_on_edit.sh`) only rsyncs to the Paradox mod folder; it does **not** call `/reload`. So a generator writing into `common/` or `map_data/` triggers exactly one extra rsync after the reload completes, never an infinite loop. **Do not wire `/reload` into the watcher.**

Every module retains its standalone CLI entrypoint (with `--dry-run` flags where applicable); auto-run uses a quiet code path that suppresses the verbose progress output.

### Adding a new post-load generator

Three rules — break any of them and the integration fails silently or deadlocks at startup:

1. **The roster entry's second element is the import path.** `POST_LOAD_GENERATORS` calls `importlib.import_module(<path>)`, so a repo-root module is registered by its bare name (`("pm_costs", "pm_costs")`) and one under `scripts/generators/` by its dotted path (`("gen_company_building_cleanup", "scripts.generators.gen_company_building_cleanup")`) — the repo root is on `sys.path`, and `scripts/` / `scripts/generators/` resolve as **PEP 420 namespace packages** — neither carries an `__init__.py` (`find scripts -name __init__.py` is empty) and on Python 3 none is needed. Prefer the repo root for new generators, but a `scripts/generators/` module does qualify; just register the dotted path, not the bare name.
2. **Expose `def regenerate(mod_state=None)`.** The post-load chain passes the live `ModState` instance. Read entity data via `mod_state.get_data("Events")` / `mod_state.localize(...)` / `mod_state.mod_parsers[...]` — never via HTTP loopback to `localhost:8950`. The server isn't accepting requests yet during startup, so a `urlopen('http://localhost:8950/...')` call inside post-load will block until timeout. (`gen_event_inventory.py` originally hit the HTTP endpoint and could not have been auto-run as-shipped — refactoring it to take `mod_state` was the unblocker.)
3. **Standalone fallback uses `mod_state_script` for the path dicts.** When `mod_state is None`, instantiate `ModState(base_game_paths, mod_paths)` — those dicts are defined in `mod_state_script.py` and `mod_state_server.py`, **not** in `path_constants.py` (which only has `mod_path` / `base_game_path` scalars). Importing from `mod_state_script` keeps the standalone path cycle-free; importing from `mod_state_server` would re-enter the server module.

After adding the module + appending to `POST_LOAD_GENERATORS`, validate without disrupting a running server: run `.venv/bin/python <your_module>.py` (the standalone path) and confirm the output file is rewritten. The integration test (`[post-load] <name> ok` line) only fires on a fresh server start — pick that up on the next natural restart rather than killing the running PID for a check.

**Edits to an existing post-load generator don't take effect on `/reload`.** Python caches the module on first import; `POST /reload` re-runs the chain but each entry is the version that was imported at server startup. Symptom: a fix to `pm_costs.py` works when invoked directly (`.venv/bin/python pm_costs.py`) but `/reload` still produces the broken output. Restart the server to pick up the edit. The same thing happens when a long-running server predates merged audit changes. If its `/status` `uptime_seconds` goes back before the latest `git log` touching a `POST_LOAD_*` module, `/reload` rewrites `docs/engine/*_report.md` with the old code. On 2026-09-14 a 14-hour-old server reverted `effect_trigger_validity_report.md` to its pre-#298 scan roots. Check uptime before you trust a report diff.

### Generator idempotency around hand-edited loc

When a post-load generator regenerates a loc value via regex substitution (e.g. `pm_costs.py` rewriting the `Cost at current market prices: …` suffix in every `combat_unit_type_*_desc`), a hand-edit that tags the term with `[concept_X]` or `[Concept('X', '…')]` will silently break the regex's anchor — the generator's "replace existing" path stops matching, falls back to "append fresh," and the file accumulates a duplicate suffix on every reload. No parser warning fires; the only catch is visual inspection of the loc value or a `grep -c` after a few reloads.

Defensive pattern: make the regex match BOTH the legacy untagged form and the tagged form (`(?:market prices|\[Concept\('concept_market_price', 'market prices'\)\])`) and emit the tagged form on write. The same applies to any generator that anchors on display-name substrings of registered concepts.

## Core Infrastructure

| Script | Purpose | Run |
|--------|---------|-----|
| `paradox_file_parser.py` | Parses Paradox `.txt` files into Python dicts. Handles tokenization, brace nesting, `REPLACE:` / `INJECT:` merge directives, and diff detection. AST shape: `{key: (op, value)}`; a key repeated inside a block becomes `{key: [(op, value), ...]}` in source order, every entry keeping its own operator (`=`, `<`, `>`, `<=`, `>=`, `!=`, `?=`, `==`) and identical duplicates kept (`add = 5 add = 5` is two entries — the engine runs both). A file that repeats a *top-level* key folds the copies the way later files fold onto earlier ones: `INJECT:x` injects into the earlier copy, a plain or `REPLACE:` copy replaces it (last wins) and logs a warning on the `paradox_file_parser` logger. | Library (import) |
| `test_paradox_file_parser.py` | 40 unit tests for the parser (tokenizer, operators, repeated keys, directives, duplicate top-level keys, loc-line parsing). | `python test_paradox_file_parser.py` |
| `test_event_balance.py` | 53 unit tests for the `/event-balance` helpers (polarity arithmetic, modifier color lookup, static-modifier resolution, option-body walker, `add_enactment_modifier` expansion, change_variable parsing, file id extraction, text rendering, strict and soft dominance helpers). | `python -m unittest test_event_balance` |
| `mod_state.py` | `ModState` class wrapping the parser. Loads all entity types and localization. Provides `localize()`, `unlocalize()`, `search_localization()`, `build_reverse_localization()`. Module-level `parse_loc_line()` / `iter_loc_lines()` are the single loc-line rule (escape-aware — a value containing `\"` reads back whole, backslashes kept verbatim; the `l_english:` header, comment lines and unquoted lines are skipped) shared with the server's `_parse_loc_lines`. | Library (import) |
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

### Python lint gate (`ruff`)

`ruff.toml` at the repo root enables the pyflakes (`F`) rules only — undefined
names, duplicate defs / dict keys, imports shadowed by loop variables, unused
imports and locals, f-strings with no placeholders. Style and import-order rules
(`E` / `I` / `UP` / …) are deliberately **not** selected; turning them on would
rewrite every file for no correctness gain.

```bash
ruff check .                 # must print "All checks passed!"
ruff check --fix .           # apply the safe fixes (unused imports, f-strings)
ruff check --unsafe-fixes .  # preview the rest; review each before applying
```

Notes:
- `ruff` is in `requirements.txt` under the "Dev / CI" block as `ruff>=0.5,<1`.
  CI installs one **pinned** version instead (see the "Lint (ruff, pyflakes rules)"
  step in `.github/workflows/ci.yml`) so a ruff release can't redden a commit that
  changed nothing; bump the pin deliberately after running `ruff check .` locally
  on the new version.
- `ruff.toml` uses `extend-exclude`, not `exclude` — `exclude` *replaces* ruff's
  built-in defaults (`.git`, `__pycache__`, `build/`, `dist/`, …), which is almost
  never what you want.
- Keep the tree clean: a new finding in a file you touch is a review blocker.
- Suppress a deliberate unused import (side-effect import, re-export, availability
  probe) with `# noqa: F401` **plus** a reason comment — ruff rejects a malformed
  directive like `# noqa: local import` and warns about it. If there is no finding
  to suppress (a function-local import for an optional dependency, say), drop the
  `# noqa:` prefix and write a plain comment.
- Names only referenced in string annotations under `from __future__ import
  annotations` still need a real binding: import them in an `if TYPE_CHECKING:`
  block, which clears ruff's F821 and lets static checkers resolve the name. It
  does **not** help `typing.get_type_hints()` — `TYPE_CHECKING` is `False` at
  runtime, so the import never executes and `get_type_hints()` still raises
  `NameError` on that annotation. Only a real runtime import fixes that.

## Localization & Code Generation

| Script | Purpose | Run |
|--------|---------|-----|
| `organize_loc.py` | Sorts localization keys alphabetically, detects unused keys, finds implicit keys. **Auto-runs on every server reload.** When introducing a new content family, add its prefix to `categorize_key` (e.g. `ship_type_*` → `SHIP_TYPES`) so its keys don't fall into MISCELLANEOUS. **Substring rules match inside words — check for an accidental hit before adding one.** `categorize_key`'s DIPLOMACY rule is a plain `s in key` over `["diplo", "_subject_", "_proposal_"]`, and until 2026-09-20 it also carried a bare `"pact"`, so every key containing **im*pact*** was filed into `te_diplomacy_l_english.yml` — `banking_dash_mon_stance_impact_line` sat alone there while its 237 `banking_dash_*` siblings lived in MISCELLANEOUS. The rule is now `re.search(r"(^|_)pacts?(_|$)", key)`. Prefer a token-anchored regex over a bare substring for any word that is also a common English infix. Symptom: a key whose siblings all live elsewhere; hand-moving it does nothing, because the next reload puts it back — fix `categorize_key`. **4+ token gotcha:** the fallback rule is `re.match(r"^[a-zA-Z_]+$", key) and len(key.split("_")) < 4 → CONCEPTS, else MISCELLANEOUS`. A bare `state_trait_bushveld_complex` (4 tokens) lands in MISCELLANEOUS while its `_desc` lands in CONCEPTS — splitting the family across two files. Any new prefix whose base key has 4+ tokens needs an explicit `startswith` rule even if you're "fine with MISCELLANEOUS." **`te_events_l_english.yml` is not a flat sort:** it is grouped into `#` / `# <NAMESPACE>` / `#` sections ordered by the *uppercased* event namespace (so `TEMPERATURE_ANOMALY_0` precedes `TE_DEBUG_UN`, because `M` sorts before `_`), with `OTHER_EVENT_KEYS` last. Hand-inserting an event key at its plain alphabetical position lands it in the wrong section and the next run relocates it, turning a small edit into a large diff — insert the whole `# <NAMESPACE>` block in namespace order instead. **UNUSED is a heuristic — `git grep -w` a key before deleting it from `te_unused_l_english.yml`.** A key counts as used if its name appears as a token in any non-loc `.txt`/`.yml`/`.gui`, via the implicit finders, or transitively from a used loc value as `$key$`, `@key!`, `[X.GetKey…]`, or a single-quoted argument inside a `[...]` expression (`SelectLocalization( …, 'key', … )`, `AddLocalizationIf( …, 'key' )` — `find_quoted_loc_args`), or as an embedded tooltip's key (`#tooltip:[X.GetTooltipTag],key`, `#tooltip:key`). Before those last two rules, widget row/tooltip keys reached only through `SelectLocalization`, and hover tooltips such as `nuke_success_final_chance_breakdown_tt`, were filed as unused although they render; any other indirect reference can still be missed. A key **built in script from a parameter** is one (`custom_tooltip_no_bullet = je_$NAME$`): pass the whole key as its own parameter (`KEY = je_un_res_why_yes_grounds`) so the token appears in the `.txt`, as the UN chamber's reason and position lines do. | `python organize_loc.py` |
| `scripts/generators/gen_loc_files.py` | One-shot bootstrap: dumps localization YAML for `extra_law_events` and `ministry_law_events` from literals in the script. Its two output files no longer exist as such — `organize_loc.py` has since folded their keys into the `te_*_l_english.yml` category files, so re-running it would resurrect two stale duplicates. Treat as historical. | `python3 scripts/generators/gen_loc_files.py` |
| `scripts/generators/gen_banking_events.py` | One-shot scaffolder for banking-cycle events 21–45 plus their modifiers, dispatch entries and loc. **`main()` refuses to run without `--force`** (prints a `RERUN_REFUSAL` to stderr, exits 1, writes nothing): it *appends* to live mod files rather than rewriting them, everything it emitted has been hand-edited since, and it is in neither `POST_LOAD_GENERATORS` nor `docs/auto_generated_files.md` — a re-run would duplicate ~25 events on top of the edited originals. Its embedded modifier strings are kept in step with `extra_modifiers.txt` by hand so the file is not a source of stale values; that does not make it safe to run. | `python3 scripts/generators/gen_banking_events.py` (refuses) |
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
| `scripts/analysis/check_save_history_order.py` | Reads a `.v3` save and reports whether each country's `te_hist` history store is in chronological order — the order the history charts draw. Unpacks the save's binary `gamestate` directly; no game needed beyond the file. Exits 1 on an out-of-order store. | `python3 scripts/analysis/check_save_history_order.py` (newest save), `<save.v3>`, or `--all` |
| `pop_needs_curves.py` | Pop needs curve definitions and buy_packages generator. **Auto-runs on every server reload.** | `python pop_needs_curves.py` (generate), `--table` for display only |

## Content Generation

| Script | Purpose | Run |
|--------|---------|-----|
| `resources.py` | Injects resource deposits into state region files from `deposits_config.json`. **Auto-runs on every server reload.** | `python resources.py` (`--table` for dry run) |
| `ig_feminism.py` | Adjusts female leader/commander probability in IG files. **Auto-runs on every server reload.** | `python ig_feminism.py` |
| `scripts/image_pipeline/event_image_prompts.py` | Maps all mod events to image/video assets. Defines AI image generation prompts. Used by `generate_event_images.py`. | Library (import) |
| `scripts/image_pipeline/generate_event_images.py` | 3-phase pipeline: generate AI images (FLUX.1-schnell), convert to DDS, create event videos. | `python scripts/image_pipeline/generate_event_images.py --phase generate` |

## Event Scaffolding (`scripts/generators/gen_event.py`)

Generates boilerplate-free Paradox event definitions and localization entries from compact JSON specs. Handles auto-ID allocation (scans existing event files), UTF-8 BOM encoding, triggered_desc chains, default option inheritance, and section headers.

### Subcommands

```bash
# Find next available IDs in a namespace
python3 scripts/generators/gen_event.py next-id space_race_events --after 600 --count 5

# Generate events from a JSON spec (preview first)
python3 scripts/generators/gen_event.py batch my_spec.json --dry-run
python3 scripts/generators/gen_event.py batch my_spec.json

# Quick single-event scaffold
python3 scripts/generators/gen_event.py scaffold --namespace my_events --title "Title" --desc "Desc" --options "Opt A" "Opt B" --dry-run
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
2. `python3 scripts/generators/gen_event.py batch spec.json --dry-run` to preview
3. `python3 scripts/generators/gen_event.py batch spec.json` to write files
4. `python organize_loc.py` to sort the appended loc keys
5. Edit the generated `.txt` to add event-specific effects to options

---

## Mod State Server (Background Data Service)

The mod-state server (`mod_state_server.py`) parses **all vanilla AND mod data** (laws, technologies, buildings, interest groups, goods, ideologies, combat units, events, journal entries, institutions, production methods, decisions, decrees, script values, scripted effects/triggers, on-actions, treaty articles, and more) **once** on startup, then serves it over a local HTTP API. It also parses engine documentation files (effects, triggers, modifiers, event targets, on-actions, custom localization) and loads developer reference `.md` files from the base game. This is the **preferred way for AI agents to look up game data**.

> **IMPORTANT:** The server indexes BOTH vanilla base game data AND mod data, merged together for most entity types. Events, scripted effects, scripted triggers, and on-actions are **mod-only** (they load only from the mod directory, not vanilla).

> **Localization** is read like the engine reads it, recursing into subdirectories (`mod_state.iter_loc_files`). Vanilla keeps about 2,400 keys in `english/map/` (every `STATE_*` name), `interest_groups/`, `character/`, `historical/` and `frontend/`. Before 2026-09 these were silently missing, and `/localize/STATE_X` returned the raw key. The one exception is `replace/`: it is skipped by the recursive read and loaded last (the mod's `localization/english/replace/`) so its keys override.

> **Logging:** The server logs to both console (INFO level) and `mod_state_server.log` (DEBUG level) in the mod root directory. Check the log file for detailed error diagnostics.

### Auto-Generated Documentation

On startup and on `/reload`, the server automatically generates the following documentation files in `docs/engine/` (via `mod_state_script.py`):
- `docs/engine/laws.txt` — All law groups and laws with unlock technologies
- `docs/engine/technologies.txt` — All technologies by era with prerequisites and descriptions
- `docs/engine/buildings.txt` — All buildings with PM groups, PMs, and pollution data
- `docs/engine/goods.txt` — All tradeable goods
- `docs/engine/combat_units.txt` — All combat unit types with unlocking technologies

These files should NOT be manually edited — they are regenerated from parsed game data.

### Starting the Server

The server **auto-starts when the VS Code workspace opens** via a VS Code task in `.vscode/tasks.json`. It runs in a background terminal labeled "Mod State Server".

To start manually (use the venv Python so the post-load generators resolve their deps):
```bash
.venv/bin/python mod_state_server.py
```
Loads in ~30 seconds (measured in a cloud container; ~60–110 s before the parser went linear-time in 2026-09), then listens on `http://127.0.0.1:8950`.

**Reload-checking a worktree branch without touching the main checkout.** `mod_path` comes from the imported module's own location and the PID file lives in that checkout, so a second server started *from a worktree* on another port parses and regenerates that worktree only. `PORT` is a module constant with no CLI flag, so set it before `main()`:
```bash
cd <worktree> && cp <main checkout>/paths.local.json .   # gitignored; the worktree has none
<main checkout>/.venv/bin/python -c "import sys; sys.argv=['mod_state_server.py']; import mod_state_server as m; m.PORT=8951; m.main()"
curl -X POST http://127.0.0.1:8951/reload                 # read `warnings` as usual
kill $(cat mod_state_server.pid) && git checkout -- docs/engine/   # the audits rewrote their reports
```
Stop it by its PID file, not `pkill -f "m.PORT=8951"`: that pattern also matches the shell running the `pkill`, which kills your own command. Used to reload-check each branch of the #428–#430 wave (#441–#444) while the main server kept serving `main`.

### Vanilla data source: `vanilla_parsed/` or the game files

ModState's vanilla half — every entity type in `mod_state.VANILLA_COMMON_DIRS` (the one list; the server's `base_game_paths` derives from it) plus the English loc dict — can come from two places:

- **`vanilla_parsed/`** — the committed parse, written by `vanilla_parsed.py build`. One JSON file per entity type under `common/`, `localization_english.json`, and `manifest.json` (game version, parser fingerprint, per-type counts, size + sha256 of every source file). Loads in about a second, reads no game file, and needs **no game install**, so a cloud session or CI gets the full vanilla view: every entity endpoint, `/diff`, `/localize`, and every audit that reads parsed vanilla.
- **The game files** under `<base_game_path>/game` — parsed on every full load, as before.

`VIC3_VANILLA_SOURCE` picks between them. `auto` (the default) uses `vanilla_parsed/` when it is fresh. With the game files on disk and the snapshot stale, it parses the files and warns. With no game files, it loads the snapshot even when stale and warns. It does the same when the game files are a known **older** vanilla than the snapshot, for example an out-of-date vanilla git clone as `base_game_path` in a cloud session (`/status` `vanilla_source.game_files_outdated`). Those files are then also kept away from the raw-vanilla generators below. `game_files` always parses; `vanilla_parsed` always loads the snapshot. "Fresh" means all of the following match:

- the snapshot format version;
- the parser fingerprint: a hash of `paradox_file_parser.py` and the ModState file-walk and loc-read functions, so **any edit there, comments included, stales the snapshot**;
- the entity-type table;
- when the game files are present, the live `rawVersion` and the source-file inventory (path + size).

`/status` reports it all under `vanilla_source` (`kind`, `reason`, `freshness`, `game_files_present`, `warnings`). A stale snapshot adds a `{label: "vanilla_source", detail}` entry to every `POST /reload` `warnings` until the next full load.

**Rebuild on the machine with the game** after every vanilla patch (runbook § 4) and after any change to the parser:

```bash
python3 vanilla_parsed.py check            # fast; exit 1 + reasons when stale
python3 vanilla_parsed.py check --full     # hash every source file (catches same-size edits)
python3 vanilla_parsed.py build            # rewrite vanilla_parsed/ (a no-op when nothing changed)
python3 vanilla_parsed.py info             # one-line summary of the committed snapshot
```

`build --game-root <dir>` builds from any tree with the `game/...` layout, e.g. the vanilla git clone. It reads the version from the clone's HEAD subject, or you can pass `--game-version`. The output is byte-identical wherever it is built, because files load in sorted name order (`mod_state.iter_script_files`). A vanilla bump therefore shows up in `git diff vanilla_parsed/` as a line-level diff of the parsed data. `check --no-game` checks against the code only.

**Without game files, some things still need them.** The snapshot holds parsed data only. With no `<base_game_path>/game/common` on disk (e.g. `VIC3_BASE_GAME=/nonexistent`):

- **Skipped (reported).** With no game files, or outdated ones, the post-load chain skips `VANILLA_FILE_REGENERATORS` (`pop_needs_curves`, `apply_ideologies`, `ig_feminism`, `pm_costs`, `resources`, `gen_law_consistency`) and `generate_docs`, because they read raw vanilla text. The reload reports them in one `vanilla_files_missing` warning. Their committed outputs are left alone rather than regenerated blind. Run blind, `apply_ideologies` would empty `common/ideologies/modified.txt`.
- **Vanilla side empty.** These return mod-only results: `/engine-docs/usage`, the vanilla callers in `/scripted-effects|triggers/<id>`, the vanilla side of `/modifier-grants`, `/engine-docs/loc-functions`, `/gui/render-*`, `/dev-docs`, `/tech-unlocks?source=vanilla`, `/duplicate-images`' vanilla hashes, and the `/validate/*?old_ref=` migration helpers. All of them scan raw files.

Engine docs (`effects.log` & co.) are separate from all this and still come from Modding-Digests (`vic3_modding_digests_path`).

### Checking If the Server Is Running
```powershell
Invoke-RestMethod http://localhost:8950/status
```

> **AI agent rule:** ALWAYS check if the server is running at the START of any session that involves looking up game data.

### HTTP status codes and access (#254 / PR #270)

Two behaviours changed in PR #270 that any script or agent talking to this server needs to know.

**1. Local-origin gate — every route, every method, 403 on failure.** `do_GET` / `do_POST` run the gate *before* any routing or reload work, so a rejected request costs nothing. A request is refused with **403** when:

- there is no `Host` header, or its hostname isn't `127.0.0.1` / `localhost` / `[::1]` (bracketed or bare; the port-less spelling is accepted);
- the `Host` port doesn't match the **actual bound port** (read from the live socket, not the hardcoded `8950`); or
- it carries an `Origin` that isn't `http://127.0.0.1:<port>` / `http://localhost:<port>` / `http://[::1]:<port>` — `Origin: null` (sandboxed iframe, `file://` page) is refused too.

This blocks a page in the user's browser from driving the server (CSRF / DNS rebinding). **Normal use is unaffected**: `curl`, `curl -f`, `urllib`, `requests` and PowerShell's `Invoke-RestMethod` all send a conforming `Host` and no `Origin`. Every rejection logs at WARNING with the offending header. The predicate is `_local_request_rejection(host, origin, port)` — a pure function, unit-tested without a server.

**2. Error bodies now carry honest statuses.** Endpoints used to answer `{"error": …}` at HTTP **200**, so `curl -f` readiness probes passed on failure and a client couldn't branch on the status. 49 such returns were converted. The exception classes in `mod_state_server.py` are `NotFound` (404), `BadRequest` (400), `DataNotLoaded` (503, a `_ServiceNotReady`); a bare `KeyError` escaping a handler is now a genuine **500** (a server bug) rather than a 404.

| Old → new | Routes / condition |
|---|---|
| **200 → 403** | Every route, any method, when the `Host`/`Origin` gate rejects the request. |
| **200 → 503** | `"<X> data not loaded"` on `/laws`, `/principles`, `/amendments`, `/technologies`, `/buildings`, `/goods`, `/combat-units`, `/ideologies`, `/events`, `/institutions`, `/journal-entries`, `/diplomatic-actions`, `/treaty-articles`, `/decisions`, `/script-values`, `/decrees`, `/on-actions`, `/production-methods`, `/scripted-effects`, `/scripted-triggers`, `/tech-tree/<id>`, `/technology-effects/<id>`, `/event-balance`, `/event-balance/issues`. Also `/production-methods?building=<id>` (`"Required data not loaded"`), `/validate/engine-coverage` (`"Mod state or engine docs not loaded"`), and `/engine-docs/usage/<name>` when the vanilla `common/` dir is missing. Body is unchanged apart from an added `hint` — but **`curl -f` now fails on these**, which is the point. |
| **200 → 400** | Missing or malformed input: `/localize` (no key) · `/unlocalize` (no text) · `/search`, `/modifier-search` (no `?q`) · `/references` (no key) · `/tech-tree`, `/unlocked-by`, `/technology-effects` (no id) · `/diff` (missing type/id) · `/filter` (no type, or no `?field`) · `/loc-keys` (fewer than 2 segments) · `/gui` (no sub-endpoint) · `/gui/render-sites` (no key) · `/gui/render-paths` (no type, or unknown `?field`) · `/modifier-grants` (no name, or malformed) · `/modifier-patterns?expand=` (pattern without a placeholder, or missing the placeholder value) · `/event-balance` (no id / `?ids` / `?prefix` / `?file`). |
| **404 → 400** | `/engine-docs/origin` and `/engine-docs/usage` called with no `<name>` — the usage hint used to ride on a `KeyError`. |
| **200 → 404** | `/logs/<family>/diff` when the `?against=` generation doesn't exist · `/loc-keys/<UnknownType>/<id>` · `/gui/render-paths/<UnmappedEntityType>`. |
| **404 → 500** | A genuine `KeyError` inside a handler (a server bug, not a missing entity). All 500 bodies are now `{"error": "<ExceptionType>: <msg>"}`. |
| **200 → 500** | `/engine-docs/usage/<name>` when the vanilla scan itself fails (timeout / scan error). |

**`/event-balance?file=` is contained to the mod tree.** `_resolve_mod_relative_path()` rejects absolute paths, `\` / `X:` prefixes, `..` escapes and symlinks pointing outside `mod_path` with **400** (a `..` that stays inside is fine); a path that resolves inside the tree but names a missing file is **404**, and an unparseable file is **400**. The other path-shaped params are pure dict lookups against pre-indexed data and were audited as safe: `/dev-docs/<path>`, `/engine-docs/<type>`, `/logs/<family>`, `/raw/<Type>/<id>`.

**`/unlocalize` takes both forms.** `/unlocalize/<text>` (path segment) and `/unlocalize?q=<text>` both work — use the query form for text containing slashes or awkward spacing. `/help` now advertises the path form and mentions `?q=`, and carries an `access` line describing the 403 gate.

**`mod_state_client.py` prints error bodies.** `query()` catches `HTTPError` *before* `URLError` (HTTPError subclasses it, so order matters), prints `HTTP <code> <reason>` plus the pretty-printed JSON body to stderr, and exits 1. A real connection failure still gives the "server is not running" message.

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/status` | GET | Server status, loaded entity types, loc key count, `parse_failure_count` + `parse_failures` (files ModState skipped because they failed to parse — `{file, error, source}`, capped at 20; non-zero means those entities are missing from every endpoint), `last_reload` (previous reload's flags + `warnings`, and — when that reload's regenerators rewrote anything — `generators_wrote_files` + `reparsed_after_generators`) |
| `/entity-types` | GET | List of entity type names |
| `/help` | GET | Self-describing index of the server's GET and POST endpoints, emitted from the handler itself. Use it as the live cross-check when this table looks stale. |
| `/keys/<EntityType>` | GET | All entity IDs + localized names for a type |
| `/raw/<EntityType>` | GET | Full raw parsed data for a type |
| `/raw/<EntityType>/<id>` | GET | Raw parsed data for one entity |
| `/loc-keys/<EntityType>/<id>` | GET | Resolve the stable family of loc keys an entity exposes (name/desc/...). Seeded set in `LOC_KEY_FAMILIES` (treaty articles, decisions, JEs, decrees, diplo actions/plays, laws, country formations, modifiers, institutions). |
| `/localize/<key>` | GET | Game key → display text |
| `/unlocalize/<text>` | GET | Display text → matching game key(s). `?q=<text>` works too — prefer it when the text contains slashes. |
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
| `/scripted-effects/<id>` | GET | Scripted-effect detail: `parameters`, `callers` (every call site — events, on_actions, journal entries, other helpers, **and vanilla** — with `file`/`line`/`origin` and parsed args), `raw`. The caller index is a brace-aware file scan (the parser drops file/line), cached until the next `/reload` and **warmed in a background thread after every load**, so a request normally hits a hot cache; `/status`' `call_index_ready` says whether it's built yet, and a request that races the warm blocks on that in-flight scan rather than starting a second one (#296). The vanilla half of the scan — the bulk of the cost, and immutable while the process lives — is built once per process and reused, so only the mod tree is re-walked per reload and the warm after a reload is a fraction of the cold one (#293, #296). **First stop before changing a parameterized helper's signature** — enumerates every caller and the args each passes. |
| `/scripted-triggers` | GET | All scripted-trigger IDs with `parameters` |
| `/scripted-triggers/<id>` | GET | Scripted-trigger detail (same shape as `/scripted-effects/<id>`) |
| `/scripted-helpers/unresolved` | GET | The inverse of that caller index: call sites whose **callee is missing** — every `name = yes` / `name = { … }` in the mod naming a scripted effect/trigger that neither vanilla nor the mod defines, so the engine silently ignores the line (#288). Returns `{count, include_reviewed, unresolved_helper_calls: [{name, file, line, kind, snippet, reviewed}]}`. Backed by `effect_trigger_validity_audit`, so it sees every directory in `SCAN_ROOTS`, not just the ones the parser indexes. `?include_reviewed=true` keeps sites suppressed with an inline `# REVIEWED …` comment. Run it after deleting or renaming a helper. |
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
| `/reload` | POST | Re-parse all files from disk + run post-load chain (regenerators + audits). Response: `status`, `startup_seconds`, `mode`, plus `warnings` / `generators_wrote_files` + `reparsed_after_generators` / `parse_failures` when non-empty — **always check them** before calling a change clean. Flags compose; see table below. |

##### `/reload` flag table

Timings are order-of-magnitude and move with the machine; the ordering is the part that matters. The Cost column was measured on a WSL+NTFS checkout **before the parser went linear-time (2026-09)**, when the parse dominated every mode. Since then the whole ModState parse (vanilla files + mod) takes a few seconds: 3.9 s in a cloud container, where a server start is ~30 s and `?mod_only=true&audits_only=true` ~13 s. The post-load chain is now the bulk of a reload. No flag combination is ever slower than an unflagged reload — `audits_only` only drops the regenerators, `mod_only` also drops the vanilla re-read.

| Query | Cost | Working-tree side effects | What it skips | When to use |
|---|---|---|---|---|
| (none) | ~60–90 s | regenerator output under `common/`, `localization/english/`, `events/` + audit reports under `docs/engine/` | nothing | Normal "I edited mod files, re-run everything" reload. |
| `?engine_only=true` | <1 s | none | the entire ModState rebuild (only re-reads engine-doc snapshots) | After re-launching the game with no mod-file edits, when you only want freshly-typed `script_docs` output to be picked up. |
| `?audits_only=true` | ~60–90 s | audit reports under `docs/engine/*_report.md` only | the 12 file-rewriting `POST_LOAD_REGENERATORS` | When you want a clean re-check of audit warnings without regenerators reshuffling your diff. Time-savings are modest — the parse dominates. The real win is the clean diff. |
| `?mod_only=true` | ~25 s | regenerator output (as above) | the vanilla parse + vanilla loc re-read (uses cached snapshot from the previous full load) + the engine-docs / dev-refs reload | When you've only edited mod files and want a quick reload. Vanilla cache is opt-in — if you bump vanilla, run an unflagged `/reload` to refresh it. |
| `?mod_only=true&audits_only=true` | ~25 s | audit reports under `docs/engine/*_report.md` only | both regenerators *and* the vanilla re-read | **The fast-verify path used by the nightly audit.** Safe to call after every batch of fixes. |

> **Caveat — editing modifier-type schemas:** if your edit changed a `decimals` / `percent` / `script_only` field in `common/modifier_type_definitions/`, the fast paths above do **not** rebuild the modifier-decimals registry that `modifier_visibility_audit` reads (`_union_mod_modifier_types`). It keeps the pre-edit value and emits false "displays as +0" flags. Restart the server (`mod_state_server.py --replace`) or run an unflagged full `/reload` to refresh it. (A plain re-launch without `--replace` is refused while the old PID is alive.)
>
> The same staleness hits a **newly added** modifier type: after a fast reload, `/engine-docs/modifiers?q=<name>` still returns 0 entries for it, which looks exactly like a registration that failed to parse. It is not. Confirm the registration with `/search?q=<name>` (it comes back under the `Modifier Types` entity type, with its loc name) and the grants with `/modifier-grants/<name>`; both read the freshly parsed ModState. Only reach for a restart if you actually need the engine-docs view.

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
- The post-processor **mutates entry dicts in place**. A handler that
  serves entries out of a module-level cache must return copies of the
  entry dicts, not just of the lists holding them — otherwise one
  annotated request stamps its fields onto every later response
  (`/tech-unlocks` leaked `flag` this way until `_copy_unlocks_record`
  started copying entries).
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
| `/validate/vanilla-surface-diff?old_ref=<git-ref>` | GET | Patch-migration helper (#228). Diff entity-key *surfaces* between the vanilla clone at `old_ref` and the **live install**: modifier_type_definitions, defines, laws, law_groups, institutions, technologies, harvest_condition_types. Returns `{added, removed, removed_and_used_by_mod:[{name, category, mod_files, re_registered_by_mod?}], summary}`. The `removed_and_used_by_mod` join is the payoff — it surfaces vanilla renames/deregistrations the mod still references (the two 1.13.9 breakage classes). `re_registered_by_mod` marks names the mod re-declares in its own `modifier_type_definitions/` (safe, not a fire). |
| `/validate/gui-at-risk?old_ref=<git-ref>` | GET | Patch-migration helper (#228). Enumerate mod `gui/*.gui` overrides (and wholesale same-path `common/` overrides) whose vanilla counterpart changed `old_ref`→live. Returns `{gui_at_risk:[{rel, changed, last_vanilla_commit}], common_overrides_at_risk, summary}`. Uses `git diff` net-difference with clone HEAD as the live proxy (verified byte-identical to the live install). |
| `/validate/loc-override-drift?old_ref=<git-ref>` | GET | Patch-migration helper (#228). Report which of the ~72 vanilla loc keys the mod shadows had their *vanilla* string change `old_ref`→live. Returns `{shadowed_key_count, drifted:[{key, old, new}], summary}`. Cheap to know (last migration: 0 drifted), expensive by hand. |
| `/duplicate-images` | GET | Flag images reused across entities of types where vanilla holds "one image per entity": Buildings (`icon`), Goods (`texture`), Decrees (`texture`), Technologies (`texture`), Interest Groups (`texture`), Laws (`icon`). Permissive types (Events, Journal Entries, Production Methods, Ideologies, Combat Units) are intentionally not scanned — vanilla shares images across many of those by design. Groups by **content hash** (md5 of the resolved `.dds` file, mod overlay first then vanilla), so two entities pointing at different filenames whose files have identical bytes still cluster — catches the case where a placeholder file was duplicated under N names. Each cluster carries `kind: "path"` (single shared filename) or `kind: "content"` (multiple distinct filenames, identical bytes). Defaults to mod-only mode: clusters with no mod-side entities are suppressed. Allowlist at `common/_meta/duplicate_image_allowlist.yml`, keyed by lowercase entity-type slug. Each entry uses either `image: <path>` (single, for path dupes) or `images: [<path>, …]` (multiple, for content dupes) plus the exact `entities:` list that may share — adding a new entity or a new identical-content file re-flags the cluster, forcing a fresh review. Query params: `?include_vanilla=true`, `?include_allowlisted=true`, `?type=Buildings` (repeatable / comma-separated), `?format=text`. Tests: `test_duplicate_images.py` (unit, fake ModState; injects a fake hasher so content-dup tests don't need real .dds files) plus an env-gated `VanillaSanityTest` (set `VIC3_RUN_VANILLA_TESTS=1`) that asserts each strict type stays under 10 vanilla-only flags. |
| `/auto-generated` | GET | Return the file → generator-script ownership map. Helps tools and devs answer "is this file safe to hand-edit?" Mirrors `docs/auto_generated_files.md` in machine-readable form. |
| `/event-magnitude-audit` | GET | Live run of the `event_magnitude_audit` post-load audit: hardcoded fast-scaling resource deltas in event effects. Returns `{flags: [{file, line, event_id, kind, effect, value, resource, fix_hint, exemption}], coverage}`. Filters: `?resource=<substring>`, `?event_id=<id>`, `?show_reviewed=true` (include `# REVIEWED` exemptions), `?format=text` (the markdown report instead of JSON). Report mirror: `docs/engine/event_magnitude_report.md`. |
| `/event-dispatch/<event_id>` | GET | Who fires a mod event: every `trigger_event` / on-action list site, resolved through scripted effects (including `$EVENT$`/`$WHO$`-parameterised helpers), immediates and on-action chains. Returns `{event_id, defined_in, hidden, chosen_by_recipient, reason, gated_systems, sites: [{file, line, entity, entity_kind, via, path, scope_switches, in_option, guards, chosen, reason}]}`. Reads the tree from disk on each call (~1 s), so it reflects edits without a `/reload`. 400 without an id, 404 for an unknown one. |
| `/event-context-audit` | GET | Live run of `event_context_audit`: `{flags: [{check, event_id, file, line, detail, evidence, dispatch, exemption}], coverage, stale_tags}`. Filters: `?check=system_ungated\|unchosen_self_action\|imputed_foreign_action` (400 on anything else), `?event_id=<id>`, `?show_reviewed=true`, `?format=text`. Report mirror: `docs/engine/event_context_report.md`. |
| `POST /validate/registries` | POST | Re-validate `docs/vanilla/vanilla_known_bugs.md` + `docs/audits/mod_known_noise.md` (anchor resolution, tracked-issue cross-references) **without** a reload — milliseconds. Returns `{status, warning_count, warnings}`, the same warning shapes `/reload` folds into its own `warnings`. Use after editing either registry. |

#### Vocabulary & Modifier-Pattern Endpoints

A *vocabulary* is the set of values a `{placeholder}` in a dynamic modifier pattern can take (e.g. `{good}` → every Goods id). The pattern catalog and `/validate/engine-coverage` both read these; the endpoints below expose them directly, which is the fastest way to answer "what are the legal values of X?" without `/keys/<EntityType>` + manual prefix-stripping.

| Endpoint | Method | Description |
|---|---|---|
| `/vocabularies` | GET | Every placeholder → `{entity_type, count, values}`. Placeholders: `good`, `building`, `bg`, `ig`, `poptype`, `culture`, `religion`, `law`, `law_group`, `tech`, `combat_unit`, `combat_unit_group`, `institution`, `terrain`, `country_rank`, `ideology`, `discrimination_trait`. |
| `/vocabularies/<placeholder>` | GET | One placeholder: `{placeholder, entity_type, count, values}`. Values are the *pattern-facing* forms — redundant entity prefixes (`building_`, `ig_`, `law_`, …) are stripped, so they slot straight into a modifier name. Unknown placeholder → 404. |
| `/building-groups`, `/country-ranks`, `/cultures`, `/discrimination-traits`, `/interest-groups`, `/law-groups`, `/pop-types`, `/religions`, `/terrain` | GET | Convenience wrappers over the matching vocabulary: `{placeholder, entity_type, count, entries: [{id, name}]}`. Same values as `/vocabularies/<placeholder>`, plus the localized display name per entry. |
| `/modifier-patterns` | GET | The dynamic-modifier pattern catalog: `{count, patterns: [{pattern, source, placeholder, vocab, members, vocab_size, missing_count}]}`. `source` is `catalog` (hand-registered) or `discovered` (inferred from the engine docs). `missing_count` = vocabulary values with no engine-doc member — the registration gap that makes a modifier silently no-op. |
| `/modifier-patterns?source=catalog\|discovered\|all` | GET | Filter by `source` (default `all`). |
| `/modifier-patterns/<pattern>` | GET | One pattern (URL-encode the braces): `{pattern, source, placeholder, vocab, notes, members: [{value, name, display_name, mask}], missing, missing_count}`. |
| `/modifier-patterns?expand=<pattern>&<placeholder>=<value>` | GET | Instantiate a pattern for one value: `{pattern, placeholder, value, concrete_name, exists_in_engine_docs, engine_doc_entry}`. **The one-curl answer to "is `building_<X>_throughput_add` a real modifier for this building?"** |

#### Game-Log Endpoints

Read Victoria 3's own logs (`game_logs_path`) through the server instead of opening them by hand — the reader clusters launch sessions, tags known vanilla bugs and registered mod noise, and filters to mod-authored script paths. The `log-triage` skill (`.claude/skills/log-triage/SKILL.md`) is the canonical workflow; this table is the route reference.

| Endpoint | Method | Description |
|---|---|---|
| `/logs` | GET | Index of available log families (`debug`, `error`, `game`, …) with their backup generations and mtimes. |
| `/logs/sessions` | GET | Cluster the log files into game-launch sessions, newest first. |
| `/logs/<family>` | GET | Parsed entries for the newest generation of that family. `?gen=N` reads backup generation N. |
| `/logs/<family>?summary=true` | GET | Category histogram + top repeated entries instead of the entry list. |
| `/logs/<family>/diff[?against=N]` | GET | Entries present in the current generation but not in generation `N` — "what's new since the last launch". |
| `/logs/<family>?q=&file=&source=&category=&since=` | GET | Filter entries by message substring, referenced script file, emitting source, category, or timestamp. |
| `/logs/<family>?dedupe=&dedupe_key=&limit=&offset=&raw=` | GET | Collapse repeats, page the result, or return unparsed lines. |
| `/logs/<family>?mod_only=true\|false\|unknown` | GET | `true` (default for `debug`/`error`) keeps only entries naming a mod script path; `false` keeps everything; `unknown` keeps everything not registered as a vanilla bug or vanilla noise — the mode that surfaces engine errors emitted from vanilla C++ with no mod path attached but caused by mod content. |
| `/logs/<family>?vanilla_bugs=show\|hide\|only` | GET | Tag (default) / drop / keep-only entries matching `docs/vanilla/vanilla_known_bugs.md`. Tagged entries carry `vanilla_bug_ref: {title, section, kind}`. |
| `/logs/<family>?mod_noise=show\|hide\|only` | GET | Same, against `docs/audits/mod_known_noise.md` (mod-side cosmetic entries, cross-linked to `docs/audits/open_issues.md`). `?vanilla_bugs=hide&mod_noise=hide` is the fully-clean triage view. |
| `/logs/<family>?include_external=true` | GET | Keep entries whose script paths belong to *other* installed mods (dropped by default). |

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
6. **After editing mod files:** `POST /reload` to pick up changes without restarting. Note: `/reload` re-parses data files, NOT Python code. To pick up Python code changes, restart the server process. **This is worse than "the change doesn't take" when the Python you edited is a *regenerator's input*.** `/reload` runs the regenerators from the modules it imported at startup, so after editing e.g. `ideology_modifications.py` and running `apply_ideologies.py` by hand, the next `/reload` rewrites `common/ideologies/modified.txt` from the **stale** dict and silently reverts your edit — `generators_wrote_files` lists the file, `warnings` is empty, and `git status` quietly loses it. Restart the server first, then reload; or re-run the standalone generator after the reload and don't reload again until you have restarted.
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

These helpers are defined in `mod_state_server.py` but are simple enough to copy into generator scripts. `scripts/generators/gen_vanilla_company_buildings.py` is a worked example of the direct-`ModState` pattern.

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
