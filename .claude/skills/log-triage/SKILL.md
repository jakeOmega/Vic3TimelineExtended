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
curl -s "http://localhost:8950/logs/debug?summary=false&dedupe=true&mod_only=unknown&vanilla_bugs=hide&mod_noise=hide" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Total: {len(d[\"entries\"])}'); [print(f'{e[\"category\"]} | {e[\"source\"]} | {(e[\"files\"] or [\"?\"])[0]} | {e[\"message\"][:200]}') for e in d['entries']]"
```

Output: a `Total: N` line, then one line per deduped entry — `category | cpp_source:line | first-referenced-file | message-truncated-to-200-chars`.

Three things this command does that matter:

- **`vanilla_bugs=hide` and `mod_noise=hide`** apply the parsed registries (`docs/vanilla/vanilla_known_bugs.md`, `docs/audits/mod_known_noise.md`), so previously-categorized vanilla bugs and tracked low-priority mod noise drop out of the first view. The per-entry mod-vs-vanilla decision-tree should focus on genuinely-new entries — if you're re-discovering something the registry already covers, you're doing the registry's job by hand. Audit what's currently swept away with `?vanilla_bugs=show&mod_noise=show` (default behavior) or scope to one bucket with `?vanilla_bugs=only` / `?mod_noise=only`.
- **`mod_only=unknown`** is the recommended triage mode. The default `mod_only=true` for debug/error filters out *every* entry whose message body contains no script path — including engine errors fired from vanilla cpp source (e.g. `pdx_data_factory.cpp` "Could not find data system function ...") that are actually caused by mod content. `unknown` keeps mod-path entries AND uncategorized empty-files entries, dropping only entries positively tagged as registered vanilla. Switch to `mod_only=true` if you want the strict "has a script path" view, or `mod_only=false` for everything-including-known-vanilla.
- **The `source` field** (cpp file:line, e.g. `jomini_scriptvalue.cpp:1659`) is what you anchor on when registering engine noise into `vanilla_known_bugs.md` § "Engine noise (source-anchored)" — printing it default avoids a second curl just to look up the source token.

For a histogram of categories instead of entries, use `?summary=true`.

## Log layout

- On disk: `/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/logs/` (Windows: `C:\Users\jakef\OneDrive\Documents\Paradox Interactive\Victoria 3\logs`).
- Families served by `/logs/<family>`: `error`, `debug`, `game`, `gui`, `graphics`, `event_scopes`, `dedicated_server`.
- Generations: `?gen=0` is current, `?gen=1` is the newest backup (= the prior launch).
- `/logs/debug/diff?against=1` — what's new since the previous game session. Run this after a fix to confirm the entries are gone.
- `/logs/sessions` — clusters file mtimes into runs; useful to scope triage to "this session only".

Useful `/logs/<family>` query params: `q=` (substring), `file=` (glob on referenced file path), `category=` (exact filter), `since=HH:MM:SS`, `dedupe_key=message+file|message|category|exact`, `mod_only=true|false|unknown`, `vanilla_bugs=hide|only|show`, `mod_noise=hide|only|show`, `include_external=true|false`.

## Triage workflow

1. Run the canonical command above.
2. **Bulk-fix routine noise first.** Some categories are non-actionable per-entry but trivially fixable in bulk. Doing them up front shortens the actionable list and saves the next session from re-triaging the same noise. See "Bulk-fixable noise" below.
3. For each remaining entry, decide **mod vs vanilla**:
   - Look at the path in `files`. If it doesn't exist under this repo, it's a vanilla file → record it in `docs/vanilla/vanilla_known_bugs.md` if it's not already there, then skip.
   - If it does exist, it's a mod issue → fix it.
4. Group mod entries by category and tackle each batch — cheaper to fix related entries together than ping-pong between unrelated bugs.
5. After fixes: `POST /reload`, re-launch game, then `/logs/debug/diff?against=1` to confirm the fixed entries are gone.

## Bulk-fixable noise

These produce a lot of triage entries that look like errors but are mechanical to fix in bulk. Fix them at the start of the session, before per-entry triage, so they don't crowd the actionable list.

### Missing UTF-8 BOM (`should be in utf8-bom encoding`)

The Clausewitz engine warns once per Paradox `.txt` that lacks the leading `\xef\xbb\xbf` byte sequence. Files still load (the warning literally says "will try to use it anyways"), but every missing-BOM file is one extra triage line forever.

Fix in one pass:

```bash
python3 <<'EOF'
import os
BOM = b'\xef\xbb\xbf'
fixed = []
for r in ['common', 'events']:
    for dp, _, files in os.walk(r):
        for f in files:
            if not f.endswith('.txt'):
                continue
            p = os.path.join(dp, f)
            with open(p, 'rb') as fh:
                data = fh.read()
            if not data.startswith(BOM):
                with open(p, 'wb') as fh:
                    fh.write(BOM + data)
                fixed.append(p)
print(f'Prepended BOM to {len(fixed)} files')
EOF
```

**Before doing the bulk write, check whether any of the files are auto-generated.** Per `CLAUDE.md` § "Don't hand-edit auto-generated files," the auto-gen list lives in `POST_LOAD_GENERATORS` in `mod_state_server.py` and the ownership map in `docs/auto_generated_files.md`. If a generator writes its outputs without BOM (e.g. `ig_feminism.py` previously used `encoding="utf-8"`), the next `POST /reload` regenerates them and the warning comes back. Fix the generator's write call to `encoding="utf-8-sig"` *first*, then run the bulk fix. **Restart the server (`pkill -f mod_state_server.py` then re-start)** after editing a generator — `/reload` doesn't pick up Python source changes.

YAML/JSON/Python files use a different convention; only target `.txt` under Paradox-script roots. Don't write BOMs to `descriptor.mod`, `.metadata/`, or other files outside `common/` and `events/` without verifying they need one.

### `dds_dimensions` warnings

DDS textures whose width/height aren't multiples of 4 produce one warning per file. Fixing requires re-exporting the DDS through an image pipeline (BC1/BC3 block-compressed needs multiple-of-4 dimensions). Not bulk-fixable from text editing — leave them in the noise pile unless the user asks to re-export.

### Vanilla `00_code_on_actions.txt:7362: <Phrase> Created`

Intentional vanilla `debug_log = "..."` calls that fire every election/movement cycle. Always skip; they aren't fixable.

## Category playbook

`game_log_reader.py:31-56` is the source of truth for category names. Common ones and first-look fix paths:

| Category | What it usually means | Where to look |
|---|---|---|
| `script_parse_error` | Typo, vanilla rename, unregistered modifier, or unknown trigger | `docs/guides/vanilla_patch_runbook.md` § Known vanilla renames; `/modifier-search?q=` to validate names |
| `inject_to_missing` | Vanilla renamed/removed an `INJECT:` target | Same runbook |
| `duplicated_key` | Top-level entity collision (mod redeclares a vanilla key) | Convert mod's declaration to `INJECT:`. `docs/guides/scripting_best_practices.md` § Top-Level Database Collisions |
| `inconsistent_trigger_scope` / `inconsistent_effect_scope` | Wrong scope for the trigger or effect | `/engine-docs/triggers`, `/engine-docs/effects`; `docs/guides/scripting_best_practices.md` § scope chain |
| `missing_file` | Asset (often `gfx/event_pictures/*.dds`) not found | Substitute thematically-similar existing asset, or remove the reference |
| `missing_texture_for_entity` | Entity references a DDS that doesn't exist | Same |
| `dds_dimensions` | DDS not a multiple of 4 | Visual-only warning; usually skip unless re-exporting |
| `other` with `should be in utf8-bom encoding` | Mod `.txt` file lacks the leading `\xef\xbb\xbf` BOM | Bulk-fix at session start — see "Bulk-fixable noise" below |
| `vfs_mount` | Filesystem/mount issue | Usually environmental, not a mod bug |
| `gui_parse_error` / `gui_widget_error` | GUI script error | `docs/guides/gui_modding_guide.md` |
| `gamedatabase_other`, `localization`, `ai`, `other` | Fallback buckets | Case-by-case |

For **"modifier silently no-ops"** reports that don't show in logs at all: the engine ignores invalid modifier names without logging. Validate via `/modifier-search?q=` and check `common/modifier_type_definitions/mod_entity_modifier_types.txt` for missing per-entity registration of dynamic patterns (`building_*`, `goods_*`, `state_building_*`, `ship_battle_against_ship_type_*`).

## Where lessons live

When you discover something worth recording, route by topic — write it in exactly one place:

- **Engine syntax, scope rule, modifier validation, scripting gotcha** → `docs/guides/scripting_best_practices.md`
- **Log-triage workflow, category interpretation, tooling quirk** → this skill's "Lessons learned" section below
- **One-off vanilla bug** → `docs/vanilla/vanilla_known_bugs.md`
- **Refactor pattern / helper inventory** → `docs/audits/script_parameterization_audit.md`
- **Per-helper context** → that helper's own header comment

This mirrors `CLAUDE.md` § "Recording lessons learned" — don't duplicate across homes.

## End-of-turn requirement

Before ending your turn on a log-triage task, ask: did I learn something a future Claude instance would hit again? If yes, route per the decision tree above. If it belongs here, append a dated bullet to "Lessons learned" below (`- YYYY-MM-DD: …`). One paragraph max — if it's longer, it probably belongs in a doc, not the skill.

The bar is: would the next Claude rediscover this from scratch? If yes, write it down. If it's already obvious from the code or covered in the playbook above, don't.

## Lessons learned

Workflow- and tooling-level lessons accrue here. Engine/scripting lessons go to `docs/guides/scripting_best_practices.md` instead.

- 2026-04-29: `debug.log` is the primary signal; `error.log` only surfaces a small subset (mostly script-value type errors). Always start with the canonical debug.log curl above. Source: `CLAUDE.md` § "Triage workflow for log issues".
- 2026-04-29: `category=other` entries with `source=jomini_effect_impl.cpp:454` and a message body that's a plain English phrase (e.g. "Election Campaign Started", "Conservative Party Created", "Revolutionary Coalition Disbanded") are **intentional vanilla `debug_log = "..."` calls** in `common/on_actions/00_code_on_actions.txt`, not bugs. They dominate `mod_only=true` triage results during election cycles because the categorizer can't distinguish them from real errors. Recognize and skip; don't dig into vanilla source for them.
- 2026-05-02: A referenced file path that exists in **neither** this mod (`ls <path>` from repo root) **nor** vanilla (`/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/<path>`) is almost always a **third-party Steam Workshop mod**. Locate it with `find /mnt/c/Program Files\ \(x86\)/Steam/steamapps/workshop/content/529340 -name <basename>` and identify via `<workshop>/<id>/.metadata/metadata.json`'s `name` field. The `mod_only=true` filter can't distinguish workshop mods from this mod, so they leak through. Not our problem — skip without recording in `vanilla_known_bugs.md`. Recent example: `GDPGR_scripted_effects.txt` and `events/gdp_events.txt` Div/0 entries trace to "GDP Growth Rate Improved" v1.2.2 (workshop id 3255320685).
- 2026-05-05: **Use `?vanilla_bugs=hide` (or `=only` to inspect what's tagged) on every `/logs/*` call.** `docs/vanilla/vanilla_known_bugs.md` is now a parsed registry — entries with `### \`path/to/file.txt[:line]\`` headings, an optional fenced code block whose lines become signature substrings, and a body whose backticked path references extend the heading's basenames. Multiple distinct error variants per bug should all go inside the same code block (`tag_vanilla_bugs` matches if ANY signature substring appears in the message, normalized for `:NNN` line refs). Avoid `<X>` placeholders in signatures — they're matched literally and won't hit real messages with quoted values. The `## Expected mod-override noise` section uses the same parser to register the `replace/*.yml` warnings as known by-design noise.
- 2026-05-05: **For comprehensive vanilla-bug discovery, aggregate across all `error*.log` and `debug*.log` generations, not just current.log.** Bugs that only fire under specific conditions (certain country exists / specific JE active / particular UI panel open) often appear in older generations but not current. Pattern: `for path in sorted(glob.glob(os.path.join(game_logs_path, 'error*.log'))): if 'Manfred' not in path and 'pickle' not in path: all_entries.extend(parse_log(path))`. Then `tag_vanilla_bugs(...)` and group by basename — the high-volume basenames are the registration targets. Took error-log tagging from 22% → 86% in one session.
- 2026-05-05: **`add_loyalists` and `add_radicals` share the same `*_radicals` script values.** Vanilla `event_values.txt` only defines `small_radicals = 0.02 / medium_radicals = 0.05 / large_radicals = 0.1`. There are NO `*_loyalists` script values — vanilla event code uses the radicals values for both effects (`acceptance_events.txt` calls `add_loyalists = { value = large_radicals }`). Mod usages of `value = small_loyalists` will silently fail (`Failed to find a valid event target link`) — replace with the matching `*_radicals` value, not a literal. Note: this triple-fires per occurrence — `Failed to find a valid event target link 'small_loyalists'` + `Badly read script value small_loyalists` + `add_loyalists effect [ The 'value' field must be set ]` — recognize as one bug, not three.
- 2026-05-06: **A single `script_parse_error` typically chains downstream `inconsistent_effect_scope` / "Unknown trigger type" / "Unknown effect" entries in the same file.** The parser loses block boundaries after the first failure and mis-attributes valid sibling triggers/effects as unknown. Fix the upstream parse error first, then re-check — the cascade usually disappears on its own. Don't independently chase the downstream entries; they're symptoms, not root causes. Recent example: `country_prestige >= 100` (script value used as trigger) at extra_decisions.txt:160 cascaded into "Unknown effect add_authority" at :164 and "Unknown effect set_country_flag" at :169 — all three were one bug. Same shape with `radical_fraction >= 0.10` (block trigger called as scalar) cascading into "Unknown trigger type: add" at the next line.
- 2026-05-06: **Crashes that ONLY happen on new-game start (load-from-save is fine) implicate `common/history/`.** New-game start runs every `common/history/*` file; load-from-save bypasses them entirely. When a crash is gated specifically on new-game and not on load, the suspect is whatever changed in `common/history/` — not the broader entity definitions, scripted effects, events, or modifier types (those load on both paths). Bisect by removing recently-touched history files first. **Parse-clean ≠ runtime-safe**: the engine can crash inside the C++ effect-execution path (e.g. `create_political_lobby`) without flushing a script_parse_error or any actionable log line — `debug.log` may stop mid-load with only benign notices like `should be in utf8-bom encoding` against the file. Don't trust silence in logs as innocence; the load-vs-new-game differential is faster than further log analysis. Recent example: a single domestic-lobby (`category = foreign`) seed in `common/history/lobbies/01_extended_lobbies.txt` crashed new games; logs showed only the BOM warning, no script error.
- 2026-05-09: **The canonical `mod_only=true` filter hides errors whose `files` field never resolves to a mod path, even when a mod loc string is the cause.** Unregistered concept refs (`[concept_X]` with no `common/game_concepts/` entry) fire `Could not find data system function 'concept_X'` from `pdx_data_factory.cpp` — vanilla source, no mod file in the message body — at hundreds of times per render, causing UI lag. The canonical curl returned `Total: 0` while the underlying file had 600+ such lines. **For a thorough sweep, use `?mod_only=unknown` instead of the default `?mod_only=true`** — it keeps mod-path entries AND uncategorized empty-files entries, dropping only entries positively tagged as registered vanilla bugs. The unregistered-concept failure mode itself is now caught at parse time by `concept_reference_audit` (`docs/engine/concept_reference_report.md`), which scans every loc YAML for `[concept_X]` / `[Concept('concept_X', ...)]` references and flags any not declared in `common/game_concepts/`. Engine-fact write-up of the concept-registration requirement lives in `docs/guides/scripting_best_practices.md` § Game Concept Hyperlinks.
- 2026-05-10: **`vanilla_known_bugs.md` entries can parse, persist, and still match nothing if the heading isn't shaped `### \`anchor\` — title`.** A free-text heading like `### Vanilla journal_entries — ...` survives parse but never tags real log entries; only a backtick-quoted anchor at the front (file path, file path + line refs, or cpp source token) gets indexed. Full reload's `warnings` array does NOT flag this — it only catches the related "no file path or source anchor — would match every log entry" case (which fires when the signature block has no script path *and* there's no `- source:` line). The "parses but matches nothing" failure is silent; verify by running the canonical curl after each batch and confirming the entries you expected to swallow are actually gone.
- 2026-05-10: **`POST /reload?engine_only=true` re-parses the bug registry but skips audits.** Useful for fast iteration when adding `vanilla_known_bugs.md` entries (~1s instead of ~77s). But you have to run a full `POST /reload` once at the end to surface the parser's rejection warnings — `engine_only` returns `warnings: []` even when entries were rejected.
- 2026-05-11: **Two registry-heading parse gotchas, both surface as `'X' has no file path or source anchor — rejected` warnings:**
  - **Line-ref format:** the `_PATH_REF_RE` regex (`game_log_reader.py:327`) accepts `\`path.txt:N\`` and `\`path.txt:N, N, N\`` (single colon, then comma-separated numbers), but NOT `\`path.txt:N, :N, :N\`` (repeated colons). The repeated-colon form fails the whole anchor capture, leaving `file_basenames` empty even though the path is right there. Format multi-line headings as `### \`events/foo.txt:112, 205, 206, 210\`` not `### \`events/foo.txt:112, :205, :206, :210\``.
  - **Title-as-signature:** the parser ALSO treats the text after ` — ` in the heading (`_TITLE_AFTER_DASH_RE`) as a signature line. If that title text *looks* like an engine error message (e.g. `Undefined event target 'X'`), the parser captures it, fails its anchor check, and rejects the whole entry. Keep titles paraphrased ("unbound option-branch scope") rather than verbatim engine-error keywords.
- 2026-05-14: **`debug.log` rotates aggressively — capture the canonical triage output to a file before drilling in.** Vic3 caps each debug.log at 524 KB, then rolls 0..5; a 5-launch session (or any session with high-volume mod-side spam) can scroll your initial gen=0 findings entirely out of all six retained files. Pattern: run the canonical curl, drill into one entry, return for the next entry — by then the user may have re-launched the game and gen=0 is a fresh 5 KB file. Earlier findings (line numbers, repeat counts) are still valid against the mod files themselves (those haven't changed), but the API view of them is gone. Solution: `curl -s "http://localhost:8950/logs/debug?..." > /tmp/debug_triage.json` early; re-query with `python3 -c "import json; ..." < /tmp/debug_triage.json`. The /tmp file survives the rotation. Same pattern for `error.log`. The `summary=true` view is small enough to keep in conversation but the full deduped entry list is not — save it.
