# CLAUDE.md

Guidance for Claude Code working in this repository. This file holds what every task needs. Rules for one kind of file live in `.claude/rules/` and load when you open a matching file; the table under **Rules by area** lists them, so read the one for your task if it has not loaded.

## What this repository is

A large content mod for **Victoria 3** (Paradox Clausewitz engine) extending the timeline with new eras and systems (banking cycles, global warming, nuclear weapons, cultural hegemony, covert warfare, space race, strategic reserves, post-scarcity, etc.). Two halves:

1. **Mod data** — Paradox `.txt` script under `common/`, `events/`, `gui/`, `localization/`, `gfx/`, `map_data/`, plus the `.metadata/` folder (Vic3 reads `.metadata/metadata.json`, not a `descriptor.mod`).
2. **Python tooling** — parsers, generators, balance solvers, about forty audits, and a long-running data server used to introspect the parsed mod + base game.

The repo lives in WSL; the engine reads files from a Windows-side mod folder (see **Deployment topology**).

## The three commands to know

- **Before you push: `.venv/bin/python scripts/preflight.py`.** It runs every check of CI's main job, with CI's dummy game paths, and says how to fix what fails. `--quick` leaves out the test suite (about 80 s; the full run is about 8 minutes). `--changed` runs only what your diff can reach, for the loop while you work. `--list` shows the checks. CI runs this same script, so a green preflight is a green main job.
- **Before you write an effect, trigger or modifier you have not used in this mod: `python3 scripts/lessons.py <name>`.** The guides hold several hundred engine lessons; this lists the sections that mention the name, and `--show N` prints one.
- **When an audit flags your change: read what `scripts/run_audits.py` printed.** It gives what the flag means and the comment that suppresses an intended one. All the audits, what each catches and where each comment goes: `docs/guides/audits.md` (generated from `audit_registry.py`).

## Rules by area

| Working on | Read | Loads when you open |
|---|---|---|
| Script: `common/`, `events/` | `.claude/rules/script.md` (the engine gotchas, the dynamic-modifier pattern) | a file under `common/` or `events/` |
| Localization | `.claude/rules/localization.md` | a file under `localization/` or `i18n/` |
| GUI | `.claude/rules/gui.md`, then `docs/guides/gui_style_guide.md` | a file under `gui/` |
| Python tooling, tests | `.claude/rules/python.md` | a `.py` file |
| Docs, the player guide | `.claude/rules/docs.md` | a file under `docs/` |
| Vanilla references | `docs/vanilla/CLAUDE.md` | a file under `docs/vanilla/` |
| Branches, stacked PRs, worktrees, multi-agent waves, play-testing unmerged work | `docs/guides/git_workflow.md` | never on its own: read it before any of these |
| Game logs | the `log-triage` skill | on request |

## Common commands

- **Fresh-machine setup**: `python3 scripts/setup.py` — bootstraps `.venv`, installs `requirements.txt`, autodetects paths, writes a gitignored `paths.local.json`. Re-runnable. In a game-less cloud container, `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-docs.txt` (a minute or two, no Victoria 3 needed) is enough to run the whole suite and to rebuild the player guide PDF; the system `python3` lacks `numpy`, `pytest` and `ruff`. There is no `python` alias: use `python3` or `.venv/bin/python`.
- **Tests**: `.venv/bin/python -m pytest -n auto test_*.py` runs the suite in parallel, as CI does (about 450 files, 12,500 tests, 6–7 minutes on four cores); `.venv/bin/python -m pytest test_<name>.py -q` runs one file. No game install is needed: `conftest.py` supplies dummy paths. More in `.claude/rules/python.md` and `docs/guides/python_tools.md` § "Running the suite".
- **Mod state server** (the primary lookup tool, port 8950, ~30 s startup):
  - Start: `.venv/bin/python mod_state_server.py` — auto-starts under VS Code. **Claude has standing approval to start/restart it without asking** — announce in one short sentence and bring it up. A cold start runs the 19 regenerators on the working tree, like a full `/reload`: start on a clean tree or with `VIC3_SKIP_POST_LOAD_GENERATORS=1`, then `git status` and stage or revert everything they wrote as one unit. A half-committed `organize_loc` move silently drops keys (#613, #617).
  - Status: `curl http://localhost:8950/status`. Always verify before doing game-data lookups.
  - Reload after mod-file edits: `curl -X POST http://localhost:8950/reload` (full, ~30 s), or `?mod_only=true&audits_only=true` for fast iteration (~13 s, no working-tree side effects beyond `docs/engine/*_report.md`). **Always read the response's `warnings` array** before claiming a change is clean: every reload audit feeds it, and so does a step that crashed. `generators_wrote_files`, `reparsed_after_generators` and `parse_failures` are there too. Flag table and endpoint inventory: `docs/guides/python_tools.md`.
  - With no game install the server serves vanilla from the committed `vanilla_parsed/` snapshot and skips the regenerators that read raw vanilla files. After a vanilla patch or any parser edit, rebuild the snapshot on the machine with the game: `python3 vanilla_parsed.py build` (`check` says whether it's needed). Details: `docs/guides/python_tools.md` § "Vanilla data source".
- **Deploy to game**: `./scripts/deploy.sh` (dry run) / `./scripts/deploy.sh --apply`. Auto-deploy runs while VS Code is open (`scripts/watch_deploy_on_edit.sh`).
- **Player guide**: `.venv/bin/python scripts/build_player_guide.py` rebuilds the PDF (pandoc + Typst, deterministic); commit chapter and PDF together. See **Keep the player guide current**.
- **Nightly audit**: the `nightly-audit` skill, or `python3 scripts/nightly_audit_select.py [--dry-run]`; documented in `docs/audits/nightly_audit_README.md`.
- **Cutting a release**: `docs/guides/release_checklist.md`. From 1.2.0 a release ships `main` as it stands, the Demographics census included (owner, 2026-10-26); `scripts/release/comment_out_census_inputs.py` is only for a release cut without it, on a `release/<version>` branch never merged back. Tag the commit you upload and publish its GitHub release the same day (1.1.9 went untagged for a week).
- **CI** (`.github/workflows/ci.yml`, Python 3.11 + 3.12, on every PR and on pushes to `main`): `scripts/preflight.py`'s five groups, one step each, plus a separate texture-dimension job that needs `gfx/`. Nothing in it needs a Victoria 3 install. Reproduce a failed step with `.venv/bin/python scripts/preflight.py --only <group or check id>`.
- Other one-shot CLIs (event scaffolding, balance solvers, deposit configs, image pipelines) live under `scripts/generators/`, `scripts/analysis/`, `scripts/image_pipeline/`. The config-driven generators and the audits run on every `POST /reload` (`POST_LOAD_REGENERATORS` and `POST_LOAD_AUDITS` in `mod_state_server.py`; rosters in `docs/guides/python_tools.md` and `docs/auto_generated_files.md`). Set `VIC3_SKIP_POST_LOAD_GENERATORS=1` to disable them while iterating on one.

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

**Dynamic-modifier scaling pattern**: a static modifier with unit values, re-applied from a yearly or monthly pulse as `add_modifier = { name = X multiplier = <script_value> }` after removing the old copy, from exactly one refresh site, and from a *state* pulse when the modifier is state-scoped. The reasons and the traps are in `.claude/rules/script.md` and `docs/systems/mod_systems/dynamic_modifier_pattern.md`.

### Game rules
`common/game_rules/extra_game_rules.txt` exposes toggles for the major systems. When disabled, the journal entry doesn't appear but related laws/events still provide their non-system effects. See `README.md`.

### Python tooling spine
- `paradox_file_parser.py` — tokenizer + recursive-descent parser for Paradox `.txt`. Handles `REPLACE:`/`INJECT:` merge directives, BOM, comments, brace nesting. Unit-tested.
- `mod_state.py` — `ModState` class wrapping the parser; loads vanilla + mod data. Bulk Python generators should `from mod_state import ModState` directly rather than going through HTTP.
- `mod_state_server.py` — HTTP service over `ModState` (port 8950). Events, scripted_effects, scripted_triggers, on_actions are **mod-only**; everything else is mod ∪ vanilla.
- `vanilla_parsed.py` — builds, loads and freshness-checks `vanilla_parsed/`, the committed JSON parse of vanilla. The vanilla entity-type list is `mod_state.VANILLA_COMMON_DIRS`.
- `audit_registry.py` — the one table of the audits; `scripts/run_audits.py`, `scripts/preflight.py`, CI and `docs/guides/audits.md` all read it.

## Working in this repo

### Read the docs before scripting
Before redesigning, rebalancing, or extending an existing gameplay system, read its file in `docs/systems/mod_systems/` first (one file per system; the index, `docs/systems/mod_systems.md`, lists them and every `##` section) — these files document modifier hooks, threshold tables, button-gate patterns, and architectural conventions specific to that system. A new system gets its own file and an index row.

`docs/README.md` is the index of everything else. The ones most often needed:
- `docs/guides/scripting_best_practices.md` — the engine's rules and quirks, several hundred sections. Search it with `scripts/lessons.py`.
- `docs/guides/event_creation_guide.md` — event boilerplate, images, IG approval modifiers, AI-weight pitfalls, option tradeoff principles, tone.
- `docs/guides/gui_style_guide.md` and `docs/guides/gui_modding_guide.md` — what a panel should be, and how to build one.
- `docs/guides/python_tools.md` — every server endpoint and tool, and the AI-agent workflow.
- `docs/vanilla/CLAUDE.md` — a condensed summary of the vanilla systems, with the concept primers (economy, politics, states, technology, pops, colonization, formables) beside it. Read the primer before touching mod content built on that vanilla system.
- **External**: [`Modding-Digests`](https://github.com/Victoria-3-Modding-Co-op/Modding-Digests/) — community per-patch summaries of vanilla changes. Local clone at `vic3_modding_digests_path` (`~/src/Modding-Digests` by default), auto-pulled on a server cold start. **First stop** for any "what changed in vanilla 1.x" question.

### Top gotchas

The engine accepts almost anything without a word. One line each here; the full text, with the evidence and the audit that catches each, is `.claude/rules/script.md`.

- Invalid modifier names and unregistered dynamic patterns are **silently ignored**. Validate with `/modifier-search?q=` or `/engine-docs/origin/<name>`.
- A second top-level entity with the same name is **silently dropped**. Extend with `INJECT:X = { ... }`.
- A **missing loc key logs nothing**; the player sees the raw key.
- `add_modifier` / `remove_modifier` results are not visible inside the same effect block.
- The `*_modifier_time` values are **days**, not months, and `any_*` triggers take no `limit = { }`.
- `add_modifier`'s `days` / `months` takes a literal or a bare `name = N` script value, never a `{ value = N }` or computed one (it reads as 0).
- A same-name `add_modifier` **stacks**: remove the old copy before re-adding.
- A modifier that takes authority is a positive `country_authority_cost_add`, never a negative `country_authority_add`.
- `country_treaty_leverage_generation_add` generates leverage *against* the country whose block carries it.
- Power bloc principle tiers **replace** the tier below; each restates everything.
- A visible event needs an `event_image`, or it draws a magenta blob with no log line.
- `change_variable` / `set_variable` show nothing in an option's tooltip; say it in a `custom_tooltip`.
- A scripted effect or trigger call passes exactly the `$X$` names its callee uses, each a single token.
- A revolution's winner inherits the loser's variables but no modifiers and no lists: **the winner continues the nation**, so mirror such state in variables.
- A rule-gated journal entry must also end when its game rule is switched off mid-game.
- A company's prestige good needs a roster building that makes its base good; every amendment needs a scripted way in; an ideology's lawgroup block names every law in its group.
- Before telling the user a vanilla value is engine-hardcoded or missing, scan `vanilla_parsed/common/*.json` by the *effect's* name.

### Keep the player guide current (check before every PR)
`docs/player_guide/` is what players read to learn the mod, so it must match the script. **Before opening any PR, ask whether it changes anything a player sees or decides**: a law, building, modifier value, button, event option, threshold, AI behaviour a player plans around, or an in-game name. If it does, update the chapter that covers it (and `17-reference.md` or an appendix if they list it) in the same PR, rebuild the PDF and commit chapter and PDF together; CI fails on a stale PDF. Every PR body says which it is: a "Player guide" line naming the chapters updated, or why none needed it ("no player-facing change", or "below the guide's level of detail"). Style and the lint: `docs/player_guide/STYLE.md`.

**Current means accurate, not exhaustive: match the depth of what's already there.** The duty is that nothing in the guide goes wrong and a player can find the things they plan around, not that each PR writes up the system it touched. Fix a figure the guide states, rename what was renamed, and give a new building, production method, good, company or law a table row, a list entry or a sentence where its peers already sit. A subsection of its own is for a system the player works through (a journal entry, a panel, buttons, a chain of event choices), not for one building or law. Leave out what tooltips already show: per-method input tables, staffing figures, every modifier a law grants, every option of a one-off event. If the guide doesn't give a figure, changing it needs no guide edit. Pharmaceutical Industries, the biotechnology companies and Penal Labor Camps were each written up at many times the length of their peers and had to be cut back.

### Design defaults for gameplay systems (owner, 2026-10-16)

- **Soft caps, not eligibility gates.** Where a rule decides who may take part (a rank, a coastline, a region), prefer a steep penalty that leaves everyone a way in over a ban. Physical prerequisites, such as the technology or the building that does the work, can stay hard gates.
- **Avoid micromanagement.** By default, a wait or a limit shouldn't reward switching a setting off and back on: keep progress made while blocked for when the block lifts, rather than losing it or billing for nothing. It's a default, not a law. A toggle can be worth having for other reasons.

Worked examples: distant seabed claims and off-window launches (soft caps), and launch-window staging (no micromanagement), in `docs/superpowers/archive/specs/2026-10-16-global-commons-design.md` §§ 2.3, 5.2, 5.2a.

### In-game checks: self-checks and the play-test list (owner, 2026-10-12)

In-game checks don't gate a merge. A PR lands on the offline gate (CI, the audits, the tests) and adds what only the game can show to a play-test list, `docs/testing/demographics-playtest.md` for Demographics; the play-test before a release works through it. Where a build rests on an engine fact nobody has verified, ship the preferred version with a once-a-game `debug_log` line, `TE_SELF_CHECK OK|BROKEN <name>` with the numbers (pattern: `te_debug_demog_pr_selfcheck_start` / `te_debug_demog.5`), and name the fallback in the list's Self-checks table. Exclude degenerate inputs so OK can't be a false pass, and read a week after the change, since a modifier sum can lag a day.

### Triage workflow for log issues
**Look at `debug.log` first, not `error.log`** — Vic3's `error.log` only contains a small subset of engine diagnostics. Use the `log-triage` skill (`.claude/skills/log-triage/SKILL.md`) — it covers the canonical curl, mod-vs-vanilla decision, third-party-mod filtering (`include_external`), and bulk-fixable noise. Vanilla-file errors (e.g. `headlines_on_actions.txt`) belong in `docs/vanilla/vanilla_known_bugs.md`, not in fixes here. A vanilla bug the mod does patch, because it hurts play, starts its file with `# VANILLA FIX:`, gets a test against `vanilla_parsed/` that fails once vanilla fixes it, and a row in `vanilla_known_bugs.md` § "Vanilla bugs the mod fixes" (runbook § 6c).

### Editing conventions
- **Never hand-edit auto-generated files.** Edit the generator's input and re-run. Ownership map: `docs/auto_generated_files.md`. Quick check: `git grep -l "AUTO-GENERATED\|do not edit manually" common/ map_data/ localization/ docs/guides/`.
- Loc and player-guide text are American English; after adding loc keys run `python3 organize_loc.py` and commit everything it changes.
- Brace-based Paradox files use tabs; `.txt`, `.gui` and loc `.yml` files start with exactly one UTF-8 BOM.
- PRs target `main`, even stacked ones, and a multi-issue PR needs one `Closes` keyword per issue. The rest of the branch and PR practice, with what went wrong each time, is `docs/guides/git_workflow.md`.

### Recording lessons learned
When you discover something generally applicable — engine quirk, refactor pattern, tool behavior, validation rule that bites — write it into the appropriate doc in the same session. Don't let it die in conversation history. Natural homes:
- Engine syntax, scope rules, modifier validation, scripting gotchas → a new `##` section in `docs/guides/scripting_best_practices.md` whose heading states the rule (that is what `scripts/lessons.py` searches). One that has bitten more than once also gets a bullet in `.claude/rules/script.md`.
- Refactor patterns / helper inventory → `docs/audits/script_parameterization_audit.md`
- Mod-state-server / tooling behavior → `docs/guides/python_tools.md`
- Branch, merge and PR practice → `docs/guides/git_workflow.md`
- Rules for one kind of file → that area's file in `.claude/rules/`
- Per-helper context → the helper's own comment header in `common/scripted_*/`.

**Keep this file short.** It loads in every session, so a line here costs every task. It takes a rule only when the rule applies whatever the task; anything else goes in one of the homes above, with at most a line here pointing at it. A lesson that can be checked by machine is better as a preflight check or an audit than as a sentence anywhere.

Keep additions short — one paragraph or a bullet, not a treatise. Bar: would the next Claude instance hit the same gotcha or solve the same problem from scratch without this note?

### File issues for mod-state-server capability gaps
The mod state server is the primary introspection tool, but it has blind spots. When you hit one — **the server can't answer a question it structurally should**, or **you fall back to manual `git grep` / file-reading / by-hand cross-referencing or validation for mod work an endpoint could automate** — open a GitHub issue (labels `enhancement` and `tooling`) proposing the capability, then proceed with the manual workaround for the task at hand. The issue is cheap insurance against the next agent re-doing the same manual sweep. Don't bother filing for one-off curiosities the existing endpoints already cover, or for genuinely engine-side questions the server has no way to know.

Be concrete in the issue: the exact query/validation you needed, the endpoint shape (URL + return JSON) that would answer it, the entity types involved, and the manual fallback you used this time. Issue #128 came exactly from this — a homeland rebalance fell back to raw `git grep` because no endpoint answered "which laws/techs/principles grant modifier X"; the resulting `/modifier-grants/<name>` endpoint now does.

## Deployment topology
- This repo lives on the WSL/Linux side (`mod_path`, e.g. `~/src/Vic3TimelineExtended`).
- The engine reads from the Windows-side mod folder (`mod_deploy_target`, e.g. `/mnt/c/Users/<winuser>/OneDrive/Documents/Paradox Interactive/Victoria 3/mod/Vic3TimelineExtended`).
- `scripts/deploy.sh` rsyncs only `common/`, `events/`, `localization/`, `gui/`, `gfx/`, `map_data/`, `.metadata/` (plus `thumbnail.png`). Everything else (Python, docs, tests, `.git`, logs) stays in the repo.
- The ten non-English languages ship English copies generated at deploy time, with German and Spanish translations swapped in from `i18n/<language>/tm/`. Never commit a non-English loc folder. Details: `.claude/rules/localization.md` and `i18n/README.md`.
- The auto-deploy watcher runs the rsync continuously while VS Code is open; manual edits via other editors will not auto-deploy.
