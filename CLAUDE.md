# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this repository is

A large content mod for **Victoria 3** (Paradox Clausewitz engine) extending the timeline with new eras and systems (banking cycles, global warming, nuclear weapons, cultural hegemony, covert warfare, space race, strategic reserves, post-scarcity, etc.). Two halves:

1. **Mod data** — Paradox `.txt` script under `common/`, `events/`, `gui/`, `localization/`, `gfx/`, `map_data/`, plus `descriptor.mod` / `.metadata/`.
2. **Python tooling** — parsers, generators, balance solvers, and a long-running data server used to introspect the parsed mod + base game.

The repo lives in WSL; the engine reads files from a Windows-side mod folder (see **Deployment** below).

## Common commands

- **Fresh-machine setup**: `python3 scripts/setup.py` — bootstraps `.venv`, installs `requirements.txt`, autodetects paths, writes a gitignored `paths.local.json`. Re-runnable.
- **Deploy to game**: `./scripts/deploy.sh` (dry run) / `./scripts/deploy.sh --apply`. Auto-deploy runs while VS Code is open (`scripts/watch_deploy_on_edit.sh`).
- **Mod state server** (the primary lookup tool, port 8950, ~60–110s startup):
  - Start: `.venv/bin/python mod_state_server.py` — auto-starts under VS Code. **Claude has standing approval to start/restart it without asking** — announce in one short sentence and bring it up.
  - Status: `curl http://localhost:8950/status`. Always verify before doing game-data lookups.
  - Reload after mod-file edits: `curl -X POST http://localhost:8950/reload` (full, ~90 s) or `?engine_only=true` (skips ModState rebuild after re-launching the game with no mod-file changes). For fast iteration: `?mod_only=true&audits_only=true` (~25 s, reuses cached vanilla parse, skips file-rewriting generators — no working-tree side effects beyond `docs/engine/*_report.md`). Full flag table in `docs/guides/python_tools.md`. The reload response includes a `warnings` array if any post-load audit (`modifier_visibility_audit`, `event_magnitude_audit`, `kill_character_audit`) surfaced findings — **always check it** before claiming a change is clean.
  - Use the **venv Python** for server-touching commands (system `python3` is missing the `regex` package needed by post-load generators). Endpoint inventory: `docs/guides/python_tools.md`.
- **Tests**: `python test_<name>.py` per file (unittest-based, no shared runner). 17+ files cover the parser, post-load generators, server endpoints, balance audits, log readers, engine-docs render.
- **Tab-normalize Paradox files** (after large edits): `python scripts/format_paradox_tabs.py [--check] <files>` — only for brace-based `.txt`; never on YAML/JSON/Python.
- **Sort/clean localization**: `python organize_loc.py`
- **Nightly audit selector**: `python3 scripts/nightly_audit_select.py [--dry-run] [--date YYYY-MM-DD]` — picks a rotating ~2500-line slice of mod content for the scheduled judgement-based audit (covers what procedural audits can't: design intent, balance/coherence, loc tone). Selector + per-area checklists documented in `docs/audits/nightly_audit_README.md`.
- Other one-shot CLIs (event scaffolding, balance solvers, deposit configs, image pipelines) live under `scripts/generators/`, `scripts/analysis/`, `scripts/image_pipeline/`. Most config-driven generators and audits (`pop_needs_curves`, `apply_ideologies`, `ig_feminism`, `pm_costs`, `resources`, `gen_pb_principle_unlock_descs`, `gen_un_button_descs`, `gen_law_consistency`, `organize_loc`, `event_magnitude_audit`, `modifier_visibility_audit`, `kill_character_audit`, `loc_coverage_audit`, `concept_reference_audit`, `gen_event_inventory`) auto-run on `POST /reload` via `POST_LOAD_GENERATORS` in `mod_state_server.py`. Set `VIC3_SKIP_POST_LOAD_GENERATORS=1` to disable while iterating on one of those scripts.

## Where things live

- `path_constants.py` — canonical source for `mod_path`, `base_game_path`, `mod_deploy_target`, `vanilla_docs_path`, `vanilla_snapshot_docs_path`, `game_logs_path`. Imported by nearly every Python tool.
- `common/` — every Paradox entity type. The mod state server parses ALL of these from both vanilla and the mod.
- `events/` — event scripts (one file per system).
- `gui/` — overridden / extended panels.
- `localization/english/` — `*_l_english.yml` files.
- `gfx/`, `map_data/` — assets.
- `docs/` — design docs, generated reference files, reading guide in `docs/README.md`. Most docs are AI-agent-targeted; **read `docs/README.md` before deep-diving** into any system.

## High-level architecture

### Building blocks (the canonical idiom)

The mod is a layered set of independent **systems**, most of which follow the same building blocks:

1. A **journal entry** in `common/journal_entries/je_*.txt` driving the system's UI/state.
2. A **scripted progress bar** + **scripted buttons** for player interaction.
3. **Scripted effects + triggers** holding the system's logic, often parameterized with `$GOOD$`/`$TYPE$`/`$RANK$` placeholders.
4. **Static modifiers** in `common/static_modifiers/extra_modifiers.txt` — tunable per-unit effects.
5. **Script values** computing multipliers consumed by `add_modifier { multiplier = ... }`.
6. **On-actions** wiring monthly/yearly pulses, election cycles, etc.
7. **Events** in `events/<system>_events.txt` plus localization YAML.
8. **Modifier type definitions** in `common/modifier_type_definitions/` registering any dynamic-pattern modifiers.

**Dynamic-modifier scaling pattern**: define a static modifier with unit values, then in an `on_yearly_pulse_*` re-apply it as `add_modifier = { name = X multiplier = <script_value> }`. The engine multiplies every field by the multiplier each tick. State-scoped scaling **must** run from `on_yearly_pulse_state` — law/treaty/building hooks have unreliable scope chains for state-targeted script values. See `docs/systems/mod_systems.md` and `docs/guides/scripting_best_practices.md`.

### Game rules
`common/game_rules/` and `descriptor.mod` expose toggles for the major systems. When disabled, the journal entry doesn't appear but related laws/events still provide their non-system effects. See `README.md`.

### Python tooling spine
- `paradox_file_parser.py` — tokenizer + recursive-descent parser for Paradox `.txt`. Handles `REPLACE:`/`INJECT:` merge directives, BOM, comments, brace nesting. Unit-tested.
- `mod_state.py` — `ModState` class wrapping the parser; loads vanilla + mod data. Bulk Python generators should `from mod_state import ModState` directly rather than going through HTTP.
- `mod_state_server.py` — HTTP service over `ModState` (port 8950). Events, scripted_effects, scripted_triggers, on_actions are **mod-only**; everything else is mod ∪ vanilla.

## Working in this repo

### Read the docs before scripting
Before redesigning, rebalancing, or extending an existing gameplay system, read its section in `docs/systems/mod_systems.md` first — these sections document modifier hooks, threshold tables, button-gate patterns, and architectural conventions specific to that system.

`docs/README.md` is the index. The most-likely-relevant docs:
- `docs/guides/scripting_best_practices.md` — modifier validation, scope rules, `days` vs `months`, dynamic-pattern registration, `any_*` triggers don't take `limit`, modifier stacking gotchas, top-level database collisions, global-variable initialization timing, decimals/visibility, fast-scaling event audits, tech tree authoring, system-scope cheat sheet, audit/research workflow.
- `docs/guides/event_creation_guide.md` — boilerplate, available videos/icons, IG approval modifiers, AI-weight pitfalls, amenability vs enactment-success modifiers, option tradeoff principles.
- `docs/vanilla/CLAUDE.md` — condensed "what you need to know" summary across all vanilla systems. Read first for fast orientation; auto-loads when working in `docs/vanilla/`.
- `docs/vanilla/vanilla_economy_reference.md` — concept primer on vanilla Vic3 economy. Carries a "Last verified against vanilla: X" banner — refresh per `docs/guides/vanilla_patch_runbook.md` § 8b on every vanilla bump.
- `docs/vanilla/vanilla_politics_reference.md` — concept primer on vanilla Vic3 politics (legitimacy, laws, IGs, parties, ideologies, movements, characters, institutions, decrees). Read before touching law-stance, IG-approval, or movement-driven mod content.
- `docs/vanilla/vanilla_states_reference.md` — concept primer on state-level mechanics (incorporation, infrastructure, market access, turmoil, obstinance, devastation, food security, pollution).
- `docs/vanilla/vanilla_technology_reference.md` — concept primer on the tech system (three trees, five eras, innovation/cap, spread, slingshot).
- `docs/vanilla/vanilla_pops_reference.md` — concept primer on the pop / culture / religion / profession layer (acceptance, assimilation, conversion, social hierarchies, qualifications, literacy, dependents, job satisfaction).
- `docs/vanilla/vanilla_colonization_reference.md` — concept primer on colonization (malaria gating, native uprising, Colonial Administration JE, company colonization).
- `docs/vanilla/vanilla_formable_countries_reference.md` — concept primer on formable-country mechanics (minor / major / special unifications); complement to the `add-formable-country` skill.
- `docs/systems/mod_systems.md`, `docs/systems/journal_entry_systems.md` — every gameplay system's files and mechanics.
- `docs/guides/python_tools.md` — full server endpoint list and AI-agent workflow.
- `docs/guides/gui_modding_guide.md`, `docs/vanilla/treaty_articles_reference.md`, `docs/vanilla/wonder_buildings_reference.md`, `docs/vanilla/vanilla_company_buildings_reference.md`.
- **External**: [`Modding-Digests`](https://github.com/Victoria-3-Modding-Co-op/Modding-Digests/) — community-maintained per-vanilla-patch summaries (breaking changes, script-doc diffs, new modifiers/effects/triggers, file-level changes). Local clone at `vic3_modding_digests_path` (`~/src/Modding-Digests` by default), auto-pulled on `mod_state_server` cold start. **First stop** for any "what changed in vanilla 1.x" question — beats manually diffing `~/src/vic3` between version commits.

### Top gotchas (full lists in `docs/guides/scripting_best_practices.md`)
- **The Clausewitz engine silently ignores invalid modifier names and unregistered dynamic patterns.** Validate via `/modifier-search?q=` or `/engine-docs/origin/<name>`. Booleans, building/goods/state-building patterns, and ship axis combos all need explicit registration in `common/modifier_type_definitions/`.
- **Top-level entity collisions get silently dropped** (`Duplicated key X will not be created`). Use `INJECT:X = { ... }` to extend rather than redeclare.
- **`add_modifier`/`remove_modifier` results are not visible inside the same effect block.** To recompute from "base" values, store the prior contribution as a variable and subtract from the `modifier:X` read.
- **`short_modifier_time`/`normal_modifier_time`/`long_modifier_time`/`very_long_modifier_time` are days, not months** (off by 30×). And `any_*` triggers don't accept `limit = { }`.
- **Audits surface findings on every `POST /reload`** (`modifier_visibility_audit`, `event_magnitude_audit`, `kill_character_audit`, `loc_coverage_audit`, `concept_reference_audit`). Suppress an intentional flag with an inline `# REVIEWED YYYY-MM-DD: rationale` comment on the value line (or, for `loc_coverage_audit`, on the entity-opening `<name> = {` line; for `concept_reference_audit`, trailing on the loc value line). Reports under `docs/engine/*_report.md`.
- **The Clausewitz engine emits no warning for missing loc keys.** A mod-introduced static modifier, journal entry, scripted button, etc. without a corresponding `*_l_english.yml` entry shows the raw key in player UI. `loc_coverage_audit` catches this; check `docs/engine/loc_coverage_report.md` after `/reload`.

### Triage workflow for log issues
**Look at `debug.log` first, not `error.log`** — Vic3's `error.log` only contains a small subset of engine diagnostics. Use the `log-triage` skill (`.claude/skills/log-triage/SKILL.md`) — it covers the canonical curl, mod-vs-vanilla decision, third-party-mod filtering (`include_external`), and bulk-fixable noise. Vanilla-file errors (e.g. `headlines_on_actions.txt`) belong in `docs/vanilla/vanilla_known_bugs.md`, not in fixes here.

### Recording lessons learned
When you discover something generally applicable — engine quirk, refactor pattern, tool behavior, validation rule that bites — write it into the appropriate doc in the same session. Don't let it die in conversation history. Natural homes:
- Engine syntax, scope rules, modifier validation, scripting gotchas → `docs/guides/scripting_best_practices.md`
- Refactor patterns / helper inventory → `docs/audits/script_parameterization_audit.md`
- Mod-state-server / tooling behavior → `docs/guides/python_tools.md`
- Cross-cutting workflow notes → this file (`CLAUDE.md`) — keep terse, link out
- Per-helper context → the helper's own comment header in `common/scripted_*/`.

Keep additions short — one paragraph or a bullet, not a treatise. Bar: would the next Claude instance hit the same gotcha or solve the same problem from scratch without this note?

### File issues for mod-state-server capability gaps
The mod state server is the primary introspection tool, but it has blind spots. When you hit one — **the server can't answer a question it structurally should**, or **you fall back to manual `git grep` / file-reading / by-hand cross-referencing or validation for mod work an endpoint could automate** — open a GitHub issue (`gh issue create --label enhancement --label tooling`) proposing the capability, then proceed with the manual workaround for the task at hand. The issue is cheap insurance against the next agent re-doing the same manual sweep. Don't bother filing for one-off curiosities the existing endpoints already cover, or for genuinely engine-side questions the server has no way to know.

Be concrete in the issue: the exact query/validation you needed, the endpoint shape (URL + return JSON) that would answer it, the entity types involved, and the manual fallback you used this time. Issue #128 came exactly from this — a homeland rebalance fell back to raw `git grep` because no endpoint answered "which laws/techs/principles grant modifier X"; the resulting `/modifier-grants/<name>` endpoint now does. Endpoint inventory + AI-agent workflow: `docs/guides/python_tools.md`.

### Editing conventions
- Brace-based Paradox files use **tab** indentation. Run `python scripts/format_paradox_tabs.py <files>` after large edits.
- After editing mod files, `POST /reload` to refresh the server's view (auto-deploy will already have synced files into the Paradox mod folder).
- Localization keys: prefer adding to existing `*_l_english.yml` files, then run `python organize_loc.py`.
- **Never hand-edit auto-generated files.** Always edit the generator's input and re-run. Full ownership map: `docs/auto_generated_files.md`. Quick check while exploring: `git grep -l "AUTO-GENERATED\|do not edit manually" common/ map_data/ localization/`.
- Use `python3` on this system (no `python` alias). README/CLAUDE.md `python <script>.py` invocations all work as `python3`.

### Stacked PRs must target `main`, not the parent feature branch

When opening dependent PRs (PR B builds on PR A's branch), `gh pr create --base <parent-feature-branch>` makes B *merge into the parent branch, not into main*. GitHub does NOT auto-retarget the child when the parent merges — merging B in that state lands its content in the (now-merged-and-deleted) parent branch and silently strands the changes. We've hit this twice (#87-#91, #96-#97). Two safe paths:

1. **Always use `--base main`** even for stacked work. The child's diff against main will include the parent's commits until the parent merges (diff temporarily looks bigger), but the merge target is correct from day one.
2. **Retarget the child's base to main before merging the parent**: `gh pr edit <child> --base main`. Must happen while the child is still open — `gh pr edit --base` rejects closed PRs.

Symptom of the bug: parent PR merges to main, child PRs show `MERGED` in `gh pr view`, but `git log main` doesn't include their commits and the file content on main doesn't reflect the changes. Recovery: push the latest descendant branch as a new ref and open a fresh PR to main (e.g., #98 recovered this session's #96/#97).

### A multi-issue PR needs one `Closes` keyword *per* issue

`Closes #161, #167, #168` auto-closes **only #161** — GitHub binds the closing keyword to the first number; the rest are mere references and stay open after merge. Write `Closes #161. Closes #167. Closes #168.` (or `closes #161, closes #167, …`). Bit us on #174, which silently left #167-172 open (recovered by manual close + a follow-up PR). Verify post-merge with `gh issue list` rather than trusting the PR body.

## Deployment topology
- This repo lives on the WSL/Linux side (`mod_path`, e.g. `~/src/Vic3TimelineExtended`).
- The engine reads from the Windows-side mod folder (`mod_deploy_target`, e.g. `/mnt/c/Users/<winuser>/OneDrive/Documents/Paradox Interactive/Victoria 3/mod/Vic3TimelineExtended`).
- `scripts/deploy.sh` rsyncs only `common/`, `events/`, `localization/`, `gui/`, `gfx/`, `map_data/`, `.metadata/`, `descriptor.mod`, `thumbnail.png`. Everything else (Python, docs, tests, `.git`, logs) stays in the repo.
- The auto-deploy watcher runs the rsync continuously while VS Code is open; manual edits via other editors will not auto-deploy.
