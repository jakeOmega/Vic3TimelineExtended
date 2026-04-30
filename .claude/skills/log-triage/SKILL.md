---
description: Triage Victoria 3 game logs (debug.log first, then error.log) in this mod repo. Read logs via the mod_state_server /logs API, categorize issues, distinguish mod from vanilla problems, fix mod-related ones, and append non-obvious lessons learned. Use whenever investigating crashes, in-game bugs, missing content, modifier no-ops, journal entries that don't surface, or after a game session ends.
---

# Log triage skill

## When to use

- User reports an in-game bug, crash, or modded content not appearing.
- A modifier, journal entry, decree, or event doesn't behave as expected.
- After re-launching the game with mod changes — diff the new debug.log against the prior session.
- User asks "what's broken in the logs?" or "did my edit break anything?".

## Pre-flight

```bash
curl -s http://localhost:8950/status
```

If that fails, the mod state server isn't running. Start it yourself with `.venv/bin/python mod_state_server.py` via Bash `run_in_background: true` (use the venv Python — system `python3` is missing the `regex` package). Warmup is ~60–110s; poll `curl -s http://localhost:8950/status` until it returns before continuing. Don't fall back to grepping log files by hand; the categorization, mod-only filtering, and dedupe live in the server.

After mod-file edits: `curl -X POST http://localhost:8950/reload`. After only re-launching the game with no mod-file changes: `curl -X POST 'http://localhost:8950/reload?engine_only=true'` (skips the slow ModState rebuild).

**`/logs/*` reads runtime logs, not parse-time output.** A fix that resolves a `script_parse_error` won't disappear from `/logs/debug` until the **game is re-launched** and writes a new `debug.log`. `/validate/engine-coverage` reports go clean immediately on `POST /reload`, but log entries are stale until the user runs the game. Don't chase phantom failures by re-fixing what's already fixed — confirm via `/validate/engine-coverage` (immediate) and `/logs/debug/diff?against=1` (after next launch).

## Canonical first command

Always start with `debug.log`, never `error.log` — Vic3's `error.log` only carries a small subset of engine diagnostics (mostly script-value type errors); the actionable signal lives in `debug.log`.

```bash
curl -s "http://localhost:8950/logs/debug?summary=false&dedupe=true" | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'{e[\"category\"]} | {(e[\"files\"] or [\"?\"])[0]} | {e[\"message\"][:200]}') for e in d['entries']]"
```

Output: one line per deduped entry — `category | first-referenced-file | message-truncated-to-200-chars`.

`mod_only` defaults to true for `debug`/`error` families, so this is already filtered to mod-relevant entries. For a histogram of categories instead of entries, use `?summary=true`.

## Log layout

- On disk: `/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/logs/` (Windows: `C:\Users\jakef\OneDrive\Documents\Paradox Interactive\Victoria 3\logs`).
- Families served by `/logs/<family>`: `error`, `debug`, `game`, `gui`, `graphics`, `event_scopes`, `dedicated_server`.
- Generations: `?gen=0` is current, `?gen=1` is the newest backup (= the prior launch).
- `/logs/debug/diff?against=1` — what's new since the previous game session. Run this after a fix to confirm the entries are gone.
- `/logs/sessions` — clusters file mtimes into runs; useful to scope triage to "this session only".

Useful `/logs/<family>` query params: `q=` (substring), `file=` (glob on referenced file path), `category=` (exact filter), `since=HH:MM:SS`, `dedupe_key=message+file|message|category|exact`, `mod_only=true|false`.

## Triage workflow

1. Run the canonical command above.
2. For each entry, decide **mod vs vanilla**:
   - Look at the path in `files`. If it doesn't exist under this repo, it's a vanilla file → record it in `docs/vanilla_known_bugs.md` if it's not already there, then skip.
   - If it does exist, it's a mod issue → fix it.
3. Group mod entries by category and tackle each batch — cheaper to fix related entries together than ping-pong between unrelated bugs.
4. After fixes: `POST /reload`, re-launch game, then `/logs/debug/diff?against=1` to confirm the fixed entries are gone.

## Category playbook

`game_log_reader.py:31-56` is the source of truth for category names. Common ones and first-look fix paths:

| Category | What it usually means | Where to look |
|---|---|---|
| `script_parse_error` | Typo, vanilla rename, unregistered modifier, or unknown trigger | `docs/vanilla_patch_runbook.md` § Known vanilla renames; `/modifier-search?q=` to validate names |
| `inject_to_missing` | Vanilla renamed/removed an `INJECT:` target | Same runbook |
| `duplicated_key` | Top-level entity collision (mod redeclares a vanilla key) | Convert mod's declaration to `INJECT:`. `docs/scripting_best_practices.md` § Top-Level Database Collisions |
| `inconsistent_trigger_scope` / `inconsistent_effect_scope` | Wrong scope for the trigger or effect | `/engine-docs/triggers`, `/engine-docs/effects`; `docs/scripting_best_practices.md` § scope chain |
| `missing_file` | Asset (often `gfx/event_pictures/*.dds`) not found | Substitute thematically-similar existing asset, or remove the reference |
| `missing_texture_for_entity` | Entity references a DDS that doesn't exist | Same |
| `dds_dimensions` | DDS not a multiple of 4 | Visual-only warning; usually skip unless re-exporting |
| `vfs_mount` | Filesystem/mount issue | Usually environmental, not a mod bug |
| `gui_parse_error` / `gui_widget_error` | GUI script error | `docs/gui_modding_guide.md` |
| `gamedatabase_other`, `localization`, `ai`, `other` | Fallback buckets | Case-by-case |

For **"modifier silently no-ops"** reports that don't show in logs at all: the engine ignores invalid modifier names without logging. Validate via `/modifier-search?q=` and check `common/modifier_type_definitions/extra_modifier_types.txt` for missing per-entity registration of dynamic patterns (`building_*`, `goods_*`, `state_building_*`, `ship_battle_against_ship_type_*`).

## Where lessons live

When you discover something worth recording, route by topic — write it in exactly one place:

- **Engine syntax, scope rule, modifier validation, scripting gotcha** → `docs/scripting_best_practices.md`
- **Log-triage workflow, category interpretation, tooling quirk** → this skill's "Lessons learned" section below
- **One-off vanilla bug** → `docs/vanilla_known_bugs.md`
- **Refactor pattern / helper inventory** → `docs/script_parameterization_audit.md`
- **Per-helper context** → that helper's own header comment

This mirrors `CLAUDE.md` § "Recording lessons learned" — don't duplicate across homes.

## End-of-turn requirement

Before ending your turn on a log-triage task, ask: did I learn something a future Claude instance would hit again? If yes, route per the decision tree above. If it belongs here, append a dated bullet to "Lessons learned" below (`- YYYY-MM-DD: …`). One paragraph max — if it's longer, it probably belongs in a doc, not the skill.

The bar is: would the next Claude rediscover this from scratch? If yes, write it down. If it's already obvious from the code or covered in the playbook above, don't.

## Lessons learned

Workflow- and tooling-level lessons accrue here. Engine/scripting lessons go to `docs/scripting_best_practices.md` instead.

- 2026-04-29: `debug.log` is the primary signal; `error.log` only surfaces a small subset (mostly script-value type errors). Always start with the canonical debug.log curl above. Source: `CLAUDE.md` § "Triage workflow for log issues".
- 2026-04-29: `category=other` entries with `source=jomini_effect_impl.cpp:454` and a message body that's a plain English phrase (e.g. "Election Campaign Started", "Conservative Party Created", "Revolutionary Coalition Disbanded") are **intentional vanilla `debug_log = "..."` calls** in `common/on_actions/00_code_on_actions.txt`, not bugs. They dominate `mod_only=true` triage results during election cycles because the categorizer can't distinguish them from real errors. Recognize and skip; don't dig into vanilla source for them.
