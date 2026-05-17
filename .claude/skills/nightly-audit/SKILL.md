---
description: Run today's nightly mod audit interactively in this Claude Code session. Use when the user types /nightly-audit, or when the user asks to "run the audit", "do the nightly", or "trigger today's audit". Generates the per-day prompt via the selector, then has Claude follow that prompt end-to-end. Pairs with the headless scripts/run_nightly_audit.sh that fires from Windows Task Scheduler on logon — both update the same .nightly_last_run marker so they don't double-audit.
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

2. **Read the prompt file in full.** It owns the dedup workflow, focus ranking, auto-fix rule, fast-verify loop, and wrap-up instructions — everything the cloud routine's instructions used to defer to. Don't skip ahead.

3. **Execute the audit per that prompt.** That includes the dedup pass (skim recent `gh issue list` and `docs/audits/nightly/*/` outputs), the per-area checklists in `docs/audits/nightly_checklists/`, the auto-fix cap (5 files / 50 lines across all PRs that night), and the wrap-up (state-bump PR, summary issue/comment as the prompt directs).

4. **On successful completion, update the catch-up marker.** Write today's date so the headless wrapper (`scripts/run_nightly_audit.sh`) won't double-run if Windows Task Scheduler fires next:
   ```bash
   date +%Y-%m-%d > docs/audits/.nightly_last_run
   ```
   Manual re-runs (v2+) still write today's bare date here — the marker exists to gate the *scheduled* wrapper, which doesn't care how many manual passes have happened.
   Don't write the marker if the audit aborted mid-run — leaving it stale lets the next invocation retry.

## Failure handling

If the selector fails, the server is unhealthy, or the audit can't complete (context exhaustion, unrecoverable tool failure): file a GitHub issue with labels `priority:critical` and `nightly-audit:failure`, leave the marker untouched, and exit. Do NOT update `docs/audits/.nightly_coverage.json` — the prompt's selector logic handles re-selection automatically when the state file hasn't moved.

## Plan mode

If this skill is invoked while plan mode is active, the right plan is one line: "run the skill end-to-end." Don't write a multi-section plan — the skill itself owns the workflow and the generated prompt owns the per-night specifics. Do a brief read-only orientation (marker, server status, today's audit dir) if helpful, then call `ExitPlanMode` immediately to request approval.

## Related

- `docs/audits/nightly_audit_README.md` — selector tuning knobs, checklist locations, the local-execution flow.
- `scripts/run_nightly_audit.sh` — the headless catch-up runner (Windows Task Scheduler → wsl.exe). Same marker, different entry point.
- `docs/audits/nightly_checklists/*.md` — per-area audit checklists referenced by the prompt.
