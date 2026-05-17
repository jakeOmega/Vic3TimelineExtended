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
curl -s http://localhost:8950/status
```

The server must return `ready: true` (added in af0d6a7). If it isn't running, start it yourself per CLAUDE.md (`.venv/bin/python mod_state_server.py` via Bash `run_in_background: true`, then poll `/status` until ready — warmup ~60–110 s). Don't proceed against a missing or degraded server — vanilla cross-references silently no-op and the audit's coverage collapses without warning.

## Steps

1. **Generate today's prompt.** Run the selector exactly once:
   ```bash
   python3 scripts/nightly_audit_select.py
   ```
   It prints the path of the generated prompt (something like `docs/audits/nightly/YYYY-MM-DD/prompt.md`) and writes that file plus `targets.json`. Read the path from the selector's stdout — don't guess it.

2. **Read the prompt file in full.** It owns the dedup workflow, focus ranking, auto-fix rule, fast-verify loop, and wrap-up instructions — everything the cloud routine's instructions used to defer to. Don't skip ahead.

3. **Execute the audit per that prompt.** That includes the dedup pass (skim recent `gh issue list` and `docs/audits/nightly/*/` outputs), the per-area checklists in `docs/audits/nightly_checklists/`, the auto-fix cap (5 files / 50 lines across all PRs that night), and the wrap-up (state-bump PR, summary issue/comment as the prompt directs).

4. **On successful completion, update the catch-up marker.** Write today's date so the headless wrapper (`scripts/run_nightly_audit.sh`) won't double-run if Windows Task Scheduler fires next:
   ```bash
   date +%Y-%m-%d > docs/audits/.nightly_last_run
   ```
   Don't write the marker if the audit aborted mid-run — leaving it stale lets the next invocation retry.

## Failure handling

If the selector fails, the server is unhealthy, or the audit can't complete (context exhaustion, unrecoverable tool failure): file a GitHub issue with labels `priority:critical` and `nightly-audit:failure`, leave the marker untouched, and exit. Do NOT update `docs/audits/.nightly_coverage.json` — the prompt's selector logic handles re-selection automatically when the state file hasn't moved.

## Related

- `docs/audits/nightly_audit_README.md` — selector tuning knobs, checklist locations, the local-execution flow.
- `scripts/run_nightly_audit.sh` — the headless catch-up runner (Windows Task Scheduler → wsl.exe). Same marker, different entry point.
- `docs/audits/nightly_checklists/*.md` — per-area audit checklists referenced by the prompt.
