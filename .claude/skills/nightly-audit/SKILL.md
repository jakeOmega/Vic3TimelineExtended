---
description: Run a judgment-based mod audit interactively in this Claude Code session — either today's full nightly slice OR a user-scoped targeted slice. Triggers on /nightly-audit, generic phrasings ("run the audit", "do the nightly", "trigger today's audit"), AND area-targeted phrasings like "audit event localization", "audit the laws", "audit journal entries tonight", "review the GUI files", "deep pass on UN events" — any "audit/review <area or file pattern>" request where the area maps to one of the selector's known areas (events, gui, journal_entries, laws_and_politics, localization, production_methods_and_buildings, scripted_effects_and_triggers, technologies) or to a `common/`/`events/`/`gui/`/`localization/` file pattern. The selector translates the scope into flags; bare invocations get today's rotation slice. Generates the per-day prompt via the selector, then has Claude follow that prompt end-to-end. Pairs with the headless scripts/run_nightly_audit.sh that fires from Windows Task Scheduler on logon — both update the same .nightly_last_run marker so they don't double-audit.
---

# Run today's nightly mod audit

## When to use

- User types `/nightly-audit`.
- User asks to "run the audit", "trigger the audit", "do today's audit", or similar.
- Catch-up from a missed cloud-routine run (the old cloud Routine bootstrap was retired after issues #93/#99/#100 — proxy was hard-scoped to one repo per session and couldn't reach private vanilla).

If you're being asked something audit-adjacent that isn't an actual run (e.g. "what did last night's audit find?"), don't invoke this skill — read the relevant file directly.

## Pre-flight

```bash
curl -sf http://localhost:8950/status | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('status')=='running', d"
```

`-sf` fails the curl on non-2xx — which is what af0d6a7 uses to signal a degraded server (HTTP 503 + `{"status":"degraded","ready":false,...}` when `base_game_path/game/common` is missing or empty). The healthy response is `{"status":"running",...}` — there is no `ready: true` field, so don't assert one. A successful 200 + `status=running` is the signal to proceed.

If the curl fails or status isn't `running`, start the server yourself per CLAUDE.md (`.venv/bin/python mod_state_server.py` via Bash `run_in_background: true`, then poll `/status` until it returns 200 — warmup ~60–110 s). Don't proceed against a missing or degraded server — vanilla cross-references silently no-op and the audit's coverage collapses without warning.

## Steps

1. **Generate today's prompt.** Run the selector exactly once with `--allow-rerun`:
   ```bash
   python3 scripts/nightly_audit_select.py --allow-rerun
   ```
   It prints the path of the generated prompt and writes that file plus `targets.json`. Read the path from the selector's stdout — don't guess it.

   `--allow-rerun` is a no-op on the first invocation of the day (writes to `docs/audits/nightly/YYYY-MM-DD/`). On subsequent same-day invocations, when that dir already exists, it writes to `docs/audits/nightly/YYYY-MM-DD-v2/`, then `-v3/`, etc. — preserving prior runs' prompts/targets/reports. The wrap-up section of the prompt automatically uses the versioned label (e.g. `nightly-audit/2026-05-17-v2-<slug>`) for branch and PR titles so v2's PR doesn't collide with v1's.

   Scheduled runs via `scripts/run_nightly_audit.sh` deliberately do *not* pass this flag — the marker-gate keeps them at one run per day.

   **Targeted runs.** If the user's `/nightly-audit` message includes a scope (an area name, a file pattern, a directory, "only X tonight", etc.), translate it into selector flags and append them. Valid areas: `events`, `gui`, `journal_entries`, `laws_and_politics`, `localization`, `production_methods_and_buildings`, `scripted_effects_and_triggers`, `technologies`. Globs match the repo-relative path via `fnmatch`. Examples:

   | User says | You run |
   |---|---|
   | `/nightly-audit` (bare) | `python3 scripts/nightly_audit_select.py --allow-rerun` |
   | "audit event localization", `/nightly-audit event loc` | `python3 scripts/nightly_audit_select.py --allow-rerun --areas localization --include '*event*'` |
   | "audit only journal entries tonight" | `python3 scripts/nightly_audit_select.py --allow-rerun --areas journal_entries` |
   | "deep pass on UN events, 1000 lines max" | `python3 scripts/nightly_audit_select.py --allow-rerun --include 'events/un_*.txt' --budget 1000` |
   | "skip the gfx and gui stuff tonight" | `python3 scripts/nightly_audit_select.py --allow-rerun --exclude 'gfx/*' --exclude 'gui/*'` |

   Targeted runs write to `docs/audits/nightly/YYYY-MM-DD-<slug>/` (slug derived from filters), distinct from the bare `YYYY-MM-DD/` of a full nightly. The selector exits 2 with a clear error if an area name is misspelled or the filter combination is empty — fix the flags and re-run rather than falling back to an unfiltered audit silently.

2. **Read the prompt file in full.** It owns the dedup workflow, focus ranking, auto-fix rule, fast-verify loop, and wrap-up instructions — everything the cloud routine's instructions used to defer to. Don't skip ahead.

3. **Execute the audit per that prompt.** That includes the dedup pass (skim recent `gh issue list` and `docs/audits/nightly/*/` outputs), the per-area checklists in `docs/audits/nightly_checklists/`, the auto-fix cap (5 files / 50 lines across all PRs that night), and the wrap-up (state-bump PR, summary issue/comment as the prompt directs).

4. **On successful completion, conditionally update the catch-up marker.** Check the run's `targets.json` first:
   ```bash
   python3 -c "import json,sys; d=json.load(open('docs/audits/nightly/<run-label>/targets.json')); sys.exit(0 if d.get('skip_nightly_marker') else 1)" \
     && echo "targeted run — marker left untouched so tonight's full audit can still fire" \
     || date +%Y-%m-%d > docs/audits/.nightly_last_run
   ```
   - **Full runs** (`skip_nightly_marker: false`): write today's date so the headless wrapper (`scripts/run_nightly_audit.sh`) won't double-run if Windows Task Scheduler fires next. Manual re-runs (v2+) still write today's bare date — the marker exists to gate the *scheduled* wrapper.
   - **Targeted runs** (`skip_nightly_marker: true`): skip the marker write. The targeted slice doesn't satisfy the full nightly's coverage promise; per-file aging still happens (the wrap-up writes the run's `findings.json`), which naturally deprioritizes those files in the next full run.
   - Don't write the marker if the audit aborted mid-run — leaving it stale lets the next invocation retry.

## Failure handling

If the selector fails, the server is unhealthy, or the audit can't complete (context exhaustion, unrecoverable tool failure): file a GitHub issue with labels `priority:critical` and `nightly-audit:failure`, leave the marker untouched, and exit. Do NOT write the run's `findings.json` — with no delta recorded, the selector re-selects the same targets next run.

## State updates

State lives as a frozen baseline (`docs/audits/.nightly_coverage_baseline.json`) plus one committed `findings.json` delta per run; the aggregate `docs/audits/.nightly_coverage.json` is a **git-ignored derived cache**, rebuilt by replaying deltas. Record a run's results only via `scripts/nightly_audit_state_update.py` (it writes the dated `findings.json` and refreshes the cache); the per-night prompt's wrap-up shows the exact invocation. **Never** hand-edit state, and **never commit** the `.nightly_coverage.json` cache — committing it reintroduces the one-shared-file merge-conflict surface this design removed (#202/#204). Commit only your run's `docs/audits/nightly/<run-label>/` dir (`prompt.md`, `targets.json`, `findings.json`).

## Plan mode

If this skill is invoked while plan mode is active, the right plan is one line: "run the skill end-to-end." Don't write a multi-section plan — the skill itself owns the workflow and the generated prompt owns the per-night specifics. Do a brief read-only orientation (marker, server status, today's audit dir) if helpful, then call `ExitPlanMode` immediately to request approval.

## Related

- `docs/audits/nightly_audit_README.md` — selector tuning knobs, checklist locations, the local-execution flow.
- `scripts/run_nightly_audit.sh` — the headless catch-up runner (Windows Task Scheduler → wsl.exe). Same marker, different entry point.
- `docs/audits/nightly_checklists/*.md` — per-area audit checklists referenced by the prompt.
