#!/usr/bin/env bash
# Catch-up runner for the nightly mod audit. Replaces the cloud Routine
# bootstrap (deprecated after issues #93/#99/#100 — the Routines proxy is
# hard-scoped to one repo per session and can't reach private vanilla).
#
# Designed for Windows Task Scheduler logon-trigger: if today's audit
# hasn't happened yet, run it now. If it already ran today, exit clean.
# Safe to invoke from cron, scheduled tasks, the /nightly-audit skill, or
# manually whenever — the date marker dedups.
#
# Flow:
#   1. Compare today's date vs docs/audits/.nightly_last_run.
#   2. If today > last_run (or --force), proceed; else exit 0.
#   3. Ensure mod_state_server is healthy (verify /status, abort with
#      actionable error if not — does NOT auto-start; that's VS Code's job).
#   4. Run scripts/nightly_audit_select.py to generate today's prompt.
#   5. Pipe the prompt into `claude --print --permission-mode auto` so the
#      audit runs headlessly. Output streams to a per-run log.
#   6. On success, write today's date to the marker.
#
# Local Claude Code CLI auth is required for step 5 (uses your normal
# user-level credentials). The script does not handle auth itself.

set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

marker_file="docs/audits/.nightly_last_run"
log_dir="docs/audits/nightly/logs"
today="$(date +%Y-%m-%d)"
force=0

for arg in "$@"; do
    case "$arg" in
        --force) force=1 ;;
        -h|--help)
            cat <<EOF
Usage: $0 [--force]

Runs the nightly mod audit if it hasn't run today. Default: catch-up
mode — exits 0 if today's audit already ran. --force runs unconditionally
(used by the /nightly-audit slash command).
EOF
            exit 0
            ;;
        *)
            printf 'Unknown arg: %s\n' "$arg" >&2
            exit 2
            ;;
    esac
done

log() { printf '[run_nightly_audit %s] %s\n' "$(date -Iseconds)" "$*"; }

# ---- 1-2. Catch-up gate -----------------------------------------------------
last_run=""
[ -f "$marker_file" ] && last_run="$(cat "$marker_file" 2>/dev/null | tr -d '[:space:]' || true)"

if [ "$force" -eq 0 ] && [ "$last_run" = "$today" ]; then
    log "audit already ran today ($today); exiting (use --force to re-run)"
    exit 0
fi

if [ "$force" -eq 1 ]; then
    log "forced run requested; last_run=${last_run:-<never>}"
else
    log "today=$today, last_run=${last_run:-<never>} — proceeding"
fi

# ---- 3. Server health -------------------------------------------------------
if ! curl -sf http://localhost:8950/status >/dev/null 2>&1; then
    log "ERROR: mod_state_server is not responding on :8950"
    log "  Start it manually:  .venv/bin/python mod_state_server.py"
    log "  Or open VS Code in this repo — it auto-starts."
    log "  Aborting so the audit doesn't run against missing vanilla data."
    exit 1
fi
log "mod_state_server is healthy"

# ---- 4. Generate today's prompt ---------------------------------------------
log "running scripts/nightly_audit_select.py"
selector_out="$(python3 scripts/nightly_audit_select.py)"
printf '%s\n' "$selector_out"

# Selector prints the prompt path on stdout; pluck it.
prompt_path="$(printf '%s\n' "$selector_out" | grep -oE 'docs/audits/nightly/[0-9-]+/prompt\.md' | tail -n 1 || true)"
if [ -z "$prompt_path" ] || [ ! -f "$prompt_path" ]; then
    log "ERROR: selector ran but no prompt path detected in its output"
    exit 1
fi
log "prompt ready at $prompt_path"

# ---- 5. Run audit via claude --print ----------------------------------------
mkdir -p "$log_dir"
audit_log="$log_dir/${today}.log"
log "invoking claude --print (audit output streams to $audit_log)"

# --permission-mode auto: accept tool calls without prompting (we're headless).
# Stdin = the prompt; --print runs to completion and exits.
if ! claude --print --permission-mode auto < "$prompt_path" >"$audit_log" 2>&1; then
    rc=$?
    log "ERROR: claude --print exited $rc (see $audit_log)"
    exit $rc
fi
log "audit completed; output in $audit_log"

# ---- 6. Update marker -------------------------------------------------------
mkdir -p "$(dirname "$marker_file")"
printf '%s\n' "$today" > "$marker_file"
log "wrote marker: $marker_file = $today"
