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

## Routine setup

The routine's **Instructions** field is canonical at [`scripts/nightly_audit_routine_instructions.md`](../../scripts/nightly_audit_routine_instructions.md) — paste the file contents (everything below the leading HTML comment + `---`) verbatim into the Anthropic Routines UI. The UI does not auto-pull; re-paste whenever that file changes.

The instructions are deliberately thin: `source ./scripts/cloud_setup.sh` to bootstrap the sandbox (shallow-sparse-clones vanilla into `../vic3`, clones `Modding-Digests`, sets `VIC3_*` env vars, creates `.venv`, starts `mod_state_server` and waits for `/status`), then `python3 scripts/nightly_audit_select.py` to generate `docs/audits/nightly/<date>/prompt.md`, then read and follow that file. The per-night prompt — not the routine instructions — owns the dedup, focus-ranking, auto-fix, fast-verify, and wrap-up workflow. Bootstrap failure and selector failure both route to the same "open a `priority:critical` issue, don't touch the state file" failure path.

Without `cloud_setup.sh`, the audit Claude has no `/modifier-search`, `/engine-docs/origin/*`, or `/reload?mod_only=true&audits_only=true` to query and regresses to raw file reads — exactly the failure mode this setup exists to prevent.

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

## Routines sandbox notes

Pre-filled from what's true after `scripts/cloud_setup.sh` runs. **The first deployment should confirm these and overwrite anything that's wrong:**

- **Working directory at routine start**: assumed to be the repo root (the routine instructions `source ./scripts/cloud_setup.sh` from there).
- **`gh` CLI availability**: not required for bootstrap — `cloud_setup.sh` clones the private `jakeOmega/vic3` via native `git clone`, which the Routines GitHub proxy authenticates transparently. `gh` is still useful during the audit phase for `gh issue list` / `gh issue create`; install it from the routine's setup script if you want those convenience calls, otherwise the audit will fall back to `curl https://api.github.com/...`.
- **`/status` precondition**: as of issue #93's fix, `mod_state_server` returns HTTP 503 from `/status` when `base_game_path/game/common` is missing or near-empty. The bootstrap's existing `curl -sf` readiness gate catches this without further script changes — bootstrap fails loud after the 180 s ceiling instead of running the audit blind.
- **Python version**: `python3` with the standard packages from `requirements.txt` (the bootstrap creates `.venv` and `pip install`s). Server-side code requires the `regex` package; the system `python3` alone is insufficient.
- **Date access**: assumed `datetime.date.today()` returns local-date — confirm in first run; if the sandbox is UTC and you straddle midnight, prompts/state files may land under the "wrong" date.
- **Git identity**: TBD on first run (`git config user.name && git config user.email`). The audit's PRs / commits will show whatever the sandbox is configured with.
- **Branch push capability**: TBD on first run (auto-fix PRs and the state-bump PR both need to push a feature branch).
- **Auto-merge availability**: TBD per repo settings. If disabled, state-bump-only PRs stay open until merged manually.
- **Server availability**: after `scripts/cloud_setup.sh`, `mod_state_server` is running on `http://localhost:8950`. Use `?mod_only=true&audits_only=true` on `/reload` for fast verify cycles (~25 s vs ~90 s for an unflagged reload; no working-tree side effects beyond `docs/engine/*_report.md`).

Edit this section as the first deployment fills in the TBDs.

## What this audit does NOT do

- It does not duplicate the post-load procedural audits (`modifier_visibility_audit`, `event_magnitude_audit`, `kill_character_audit`, `loc_coverage_audit`, `concept_reference_audit`, `localization_accessor_audit`, `mod_structure_audit`). Those run on every `POST /reload` and cover bugs that have a procedural signature.
- It does not audit the Python tooling. The tooling has its own unittest coverage. Exception: if a generator visibly breaks while the audit is running, file an issue for it — don't fix it as part of the audit.
- It does not auto-fix anything that requires understanding designer intent. Those become issues.

## Schedule

Set via the Anthropic Routines UI; the selector is execution-agnostic. Reasonable starting cadence: nightly at the user's local off-hours. Lower the cadence (e.g. every 2 nights) if coverage builds too fast for the user to triage outputs.
