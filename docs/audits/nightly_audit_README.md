# Nightly mod audit

A scheduled Claude Code Routine that audits a small rotating slice of mod content for things the procedural audits (modifier visibility, magnitude, kill_character, loc coverage, concept refs, accessor chains, mod_structure) can't catch — design intent, mod-convention adherence, balance / coherence vs peers, localization tone. Coverage spreads across the repo over time.

## How it works

Each run:

1. **Selector** (`scripts/nightly_audit_select.py`) walks `common/`, `events/`, `gui/`, `localization/english/`, `map_data/`, `gfx/`; excludes auto-generated files; scores each remaining file by `days_since_last_audit + recency_boost + jitter`; greedy-picks under a 2500-line / 8-file budget. Large files are sliced to ≤600 lines, picking the contiguous range with least overlap to prior coverage.
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

## Routine setup

The routine's **Instructions** field should be approximately:

> Run `python3 scripts/nightly_audit_select.py`, then read and follow `docs/audits/nightly/$(date +%Y-%m-%d)/prompt.md` end-to-end. Take the dedup, focus-ranking, auto-fix, and wrap-up steps literally. If you cannot complete the audit, follow the prompt's "Failure handling" section before exiting.

Keep the file-based prompt approach (don't inline checklist content into the Routine Instructions field) — this preserves an audit trail per night and lets you edit checklists without touching the routine config.

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
| `FILE_CAP` | 8 | Max files per night. |
| `SLICE_CAP` | 600 | Max lines per file slice. Larger slice = fewer files per night. |
| `RECENT_FINDINGS_CAP` | 3 | Cap on `recent_findings` for the recency boost. |
| `DECAY_DAYS` | 90 | After this many days, `recent_findings` decays by half. |

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

## Routines sandbox notes

> **To be filled in after running a one-off probing routine.** The first deployment should answer these so future sessions can rely on them:
>
> - **Working directory at routine start** — affects path assumptions in the selector.
> - **`gh` CLI availability** — if not present, document the GitHub API-via-curl fallback that works with the connection's auth (issue creation: `gh issue create` → `curl -X POST https://api.github.com/repos/<owner>/<repo>/issues …`; PR creation: `gh pr create` → corresponding API call).
> - **Python version** — confirm stdlib-only constraints are met.
> - **Date access** — confirm `datetime.date.today()` returns the expected date in the sandbox's TZ.
> - **Git identity** — what author shows on commits/PRs the audit creates.
> - **Branch push capability** — confirm pushing a feature branch works (the audit needs this for auto-fix and state-bump PRs).
> - **Auto-merge availability** — if the repo doesn't have auto-merge enabled, state-bump-only PRs stay open until manually merged. Note here whether that's the current state.

Once probed, edit this section with the answers; the audit prompt's wrap-up logic relies on knowing the answers, especially around PR creation.

## What this audit does NOT do

- It does not duplicate the post-load procedural audits (`modifier_visibility_audit`, `event_magnitude_audit`, `kill_character_audit`, `loc_coverage_audit`, `concept_reference_audit`, `localization_accessor_audit`, `mod_structure_audit`). Those run on every `POST /reload` and cover bugs that have a procedural signature.
- It does not audit the Python tooling. The tooling has its own unittest coverage. Exception: if a generator visibly breaks while the audit is running, file an issue for it — don't fix it as part of the audit.
- It does not auto-fix anything that requires understanding designer intent. Those become issues.

## Schedule

Set via the Anthropic Routines UI; the selector is execution-agnostic. Reasonable starting cadence: nightly at the user's local off-hours. Lower the cadence (e.g. every 2 nights) if coverage builds too fast for the user to triage outputs.
