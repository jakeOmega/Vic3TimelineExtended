# Nightly mod audit

A scheduled Claude Code Routine that audits a small rotating slice of mod content for things the procedural audits (modifier visibility, magnitude, kill_character, loc coverage, concept refs, accessor chains, mod_structure) can't catch — design intent, mod-convention adherence, balance / coherence vs peers, localization tone. Coverage spreads across the repo over time.

## How it works

Each run:

1. **Selector** (`scripts/nightly_audit_select.py`) walks `common/`, `events/`, `gui/`, `localization/english/`, `map_data/`, `gfx/`; excludes auto-generated files; scores each remaining file by `days_since_last_audit + recency_boost + jitter`; iteratively greedy-picks under a 2500-line / 15-file budget, applying a per-new-doc penalty after the seed pick so picks cluster by shared docs (minimizes the auditor's pre-reading list). Large files are sliced to ≤600 lines, picking the contiguous range with least overlap to prior coverage.
2. The selector writes:
   - `docs/audits/nightly/<date>/prompt.md` — the audit prompt with doc-reading list, targets, checklists, focus ranking, auto-fix rule, wrap-up instructions.
   - `docs/audits/nightly/<date>/targets.json` — machine-readable manifest.
3. **Claude reads the prompt** and audits the targets against the per-area checklists under `docs/audits/nightly_checklists/`.
4. **Findings**: each finding is either fixed via PR (if "no more effort than filing an issue") or filed as a GitHub issue. Cap: 5 files / 50 lines changed per night across all auto-fix PRs.
5. **State**: `docs/audits/.nightly_coverage.json` is updated and committed via PR (never direct-pushed to `main`). On nights with auto-fix PRs the state bump rides in the first PR; on nights without it goes in a `nightly-audit(YYYY-MM-DD): state bump` PR set to auto-merge.
6. **Failure**: if the audit can't complete (context exhaustion, tool failure), Claude opens a `priority:critical` `nightly-audit:failure` issue and leaves the state file untouched so the next run re-selects the same targets.

## Components

| Path | Purpose |
|---|---|
| `scripts/nightly_audit_select.py` | Target selector, prompt generator. Stdlib only. |
| `docs/audits/.nightly_coverage.json` | Per-file audit state. Committed. |
| `docs/audits/nightly_checklists/*.md` | 8 per-area checklists (events, journal_entries, laws_and_politics, production_methods_and_buildings, technologies, localization, gui, scripted_effects_and_triggers). |
| `docs/audits/nightly/<date>/prompt.md` | Generated per run — the audit prompt. |
| `docs/audits/nightly/<date>/targets.json` | Generated per run — machine-readable target list. |
| `docs/audits/nightly/<date>/report.md` | Optional summary. Off by default; enable with `--report`. |

## Execution model

Local-only as of issues #93/#99/#100 — the Anthropic Routines proxy is hard-scoped to one repo per session and cannot reach private `jakeOmega/vic3` for the vanilla clone, with no safe in-sandbox workaround (env vars and setup scripts are both public, the OAuth token lives on a parent-process file descriptor not reachable from a subshell). The cloud routine was retired; the audit now runs against the user's local `mod_state_server` (which already has vanilla on disk via `path_constants.base_game_path`).

Two entry points share the same per-day catch-up gate (`docs/audits/.nightly_last_run`):

1. **`/nightly-audit` slash command** — runs the audit in your current Claude Code session. Defined at `.claude/skills/nightly-audit/SKILL.md`. Use this for on-demand runs or to manually catch up. Invokes the selector, then has Claude read and follow the generated prompt directly.

2. **`scripts/run_nightly_audit.sh`** — headless wrapper. Verifies the server, runs the selector, pipes today's prompt into `claude --print --permission-mode auto`, writes the date marker on success. Idempotent — `--force` re-runs even if today's marker is already set.

The headless wrapper is fired by a Windows Scheduled Task (registered via `scripts/install_nightly_audit_task.ps1`) that triggers **at every logon AND daily at 04:00**. The script's date-marker gate dedups, so booting at 11 AM, 4 PM, and 9 PM only runs the audit once — and a missed 04:00 because the machine was off still gets caught up at the next logon.

### One-time setup

From a Windows PowerShell session in the repo (no admin needed):

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\install_nightly_audit_task.ps1
```

Auto-detects your default WSL distro; pass `-WslDistro <name>`, `-RepoPathInWsl <path>`, `-DailyTime HH:MM`, or `-TaskName <string>` to override. Re-runnable — overwrites any existing task with the same name. The task runs as your current user so the WSL identity (and `claude` CLI auth) match interactive use.

Prereqs:
- `mod_state_server` running on `:8950` at audit time. It auto-starts under VS Code; if you don't keep VS Code open continuously, either add it to startup, run it as a separate scheduled task, or accept the audit will be skipped (the wrapper exits clean and the marker stays stale, so the next invocation retries).
- `claude` CLI on `$PATH` for the WSL user. Confirm via `wsl -- bash -lc 'which claude'`.

### Failure handling

If the wrapper aborts (server unhealthy, selector errors, `claude --print` non-zero exit), the marker is NOT updated — the next trigger retries. Stderr from each run lands in `docs/audits/nightly/logs/<date>.log`. The audit prompt itself owns the "file a `priority:critical` `nightly-audit:failure` issue" rule for in-audit failures.

## Invoking manually

```bash
# Selection preview without writing files
python3 scripts/nightly_audit_select.py --dry-run

# Specific date
python3 scripts/nightly_audit_select.py --dry-run --date 2026-05-22

# Real run that writes prompt.md + targets.json
python3 scripts/nightly_audit_select.py

# With optional report
python3 scripts/nightly_audit_select.py --report

# Custom output directory (for testing)
python3 scripts/nightly_audit_select.py --out-dir /tmp/audit-test
```

## Tuning knobs

At the top of `scripts/nightly_audit_select.py`:

| Constant | Default | Purpose |
|---|---|---|
| `LINE_BUDGET` | 2500 | Total mod-content lines per night. Raise for deeper coverage / lower for tighter focus. |
| `FILE_CAP` | 15 | Max files per night. |
| `SLICE_CAP` | 600 | Max lines per file slice. Larger slice = fewer files per night. |
| `RECENT_FINDINGS_CAP` | 3 | Cap on `recent_findings` for the recency boost. |
| `DECAY_DAYS` | 90 | After this many days, `recent_findings` decays by half. |
| `NEW_DOC_PENALTY` | 5.0 | Per-new-doc penalty when greedy-picking later files (each new doc the candidate would add to the auditor's reading list costs this many days of staleness equivalent). Higher = tighter clustering by doc affinity; lower = recency dominates. |

Add to or remove from `EXCLUDED_REGISTRY_GLOBS` when a generator starts/stops wholly-regenerating a file.
Add to or remove from `INTENTIONALLY_NOT_EXCLUDED` when a file's relationship to its generator changes (partially-managed vs hand-authored vs out-of-scope).

## Per-area checklists

Each checklist is short and specific — 6 to 10 bullets tied to a doc reference, a memory entry, or a vanilla mechanic. The current set is a first draft. The selector picks the matching checklist based on the file path.

### Checklist tuning

After **2–4 weeks** of nightly runs, review the issues + PRs the audit produced and ask, per bullet:

- Did this catch real things?
- Did it produce ignored noise (issues closed without action, PRs that the user reverted or rewrote)?
- Did the audit find things consistently that aren't on the checklist? Add them.
- Are there bullets that never fire? Cut them.

This tuning is manual, not scheduled. The checklists are deliberately first-draft — they'll get sharper once you have real data in hand. Cut, rewrite, or add accordingly. Don't try to make them comprehensive; keep them short enough to read.

## Registry drift

Every selector run diffs `docs/auto_generated_files.md` against `EXCLUDED_REGISTRY_GLOBS` and `INTENTIONALLY_NOT_EXCLUDED`. If a registry entry isn't covered by either list (or vice versa), the prompt grows a `## Registry drift` section listing the deltas, and night Claude is instructed to investigate as part of the audit.

This means the agent's narrowing decision ("which registry entries are wholly-regenerated vs partially-managed") gets re-validated continuously, without requiring scheduled manual review.

## Local execution notes

- **`/status` precondition** (from issue #93's fix, still useful): `mod_state_server` returns HTTP 503 from `/status` when `base_game_path/game/common` is missing or near-empty. The headless wrapper's `curl -sf` health check catches this and aborts loud rather than running against missing vanilla.
- **`claude --print` permission mode**: the wrapper uses `--permission-mode auto` so the audit runs unattended. Avoid `--dangerously-skip-permissions` unless you really mean it.
- **Catch-up marker**: `docs/audits/.nightly_last_run` is a one-line file holding the YYYY-MM-DD of the last successful run. Both entry points update it; both gate on it. The wrapper exits 0 (not error) when today's marker is already set — that's the "missed schedule but already caught up" case.
- **Per-run log**: `docs/audits/nightly/logs/<date>.log` captures the headless run's stdout + stderr. Tail it if you want to see what the unattended Claude did.

## What this audit does NOT do

- It does not duplicate the post-load procedural audits (`modifier_visibility_audit`, `event_magnitude_audit`, `kill_character_audit`, `loc_coverage_audit`, `concept_reference_audit`, `localization_accessor_audit`, `mod_structure_audit`). Those run on every `POST /reload` and cover bugs that have a procedural signature.
- It does not audit the Python tooling. The tooling has its own unittest coverage. Exception: if a generator visibly breaks while the audit is running, file an issue for it — don't fix it as part of the audit.
- It does not auto-fix anything that requires understanding designer intent. Those become issues.

## Schedule

Set via Windows Task Scheduler (see "Execution model" above for the one-time install). Default: every logon + daily at 04:00, dedup'd by the date marker. Adjust `-DailyTime HH:MM` when re-running `install_nightly_audit_task.ps1` if you want a different fixed slot. Lower the cadence (every 2 nights, weekly) by editing the catch-up gate in `scripts/run_nightly_audit.sh` to compare against `today - N days`.
