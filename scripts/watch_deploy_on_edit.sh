#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_SCRIPT="$REPO_ROOT/scripts/deploy.sh"
LOG_PREFIX='[auto-deploy]'
THROTTLE_MS="${AUTO_DEPLOY_THROTTLE_MS:-1000}"
POLL_INTERVAL="${AUTO_DEPLOY_POLL_INTERVAL:-1}"

log() {
  printf '%s %s\n' "$LOG_PREFIX" "$*"
}

now_ms() {
  date +%s%3N
}

should_ignore() {
  local changed_path="$1"
  local relative_path="${changed_path#"$REPO_ROOT"/}"

  case "$relative_path" in
    .git|.git/*|.venv|.venv/*|generated_images|generated_images/*|__pycache__|__pycache__/*|*.pyc|*.log|*.log.*|*.pid)
      return 0
      ;;
  esac

  case "$relative_path" in
    */__pycache__/*)
      return 0
      ;;
  esac

  return 1
}

run_deploy() {
  local reason="$1"
  local current_ms
  current_ms="$(now_ms)"

  if (( current_ms - LAST_RUN_MS < THROTTLE_MS )); then
    return 0
  fi

  LAST_RUN_MS="$current_ms"
  log "Change detected: $reason"
  if bash "$DEPLOY_SCRIPT" --apply; then
    log 'Deploy finished'
  else
    log 'Deploy failed'
  fi
}

snapshot_signature() {
  find "$REPO_ROOT" \
    \( -path "$REPO_ROOT/.git" -o -path "$REPO_ROOT/.venv" -o -path "$REPO_ROOT/generated_images" -o -name '__pycache__' \) -prune \
    -o -type f ! -name '*.pyc' ! -name '*.log' ! -name '*.pid' -printf '%T@ %p\n' | sort
}

watch_with_inotify() {
  local exclude_regex='(^|/)(\.git|\.venv|generated_images)(/|$)|(^|/)__pycache__(/|$)|\.pyc$|\.log(\..*)?$|\.pid$'

  log "Watching $REPO_ROOT with inotifywait"
  log 'Ready'
  inotifywait -m -r \
    -e close_write,create,delete,move \
    --format '%w%f' \
    --exclude "$exclude_regex" \
    "$REPO_ROOT" | while IFS= read -r changed_path; do
      [[ -n "$changed_path" ]] || continue
      should_ignore "$changed_path" && continue
      run_deploy "${changed_path#"$REPO_ROOT"/}"
    done
}

watch_with_polling() {
  local previous_snapshot
  local current_snapshot
  previous_snapshot="$(snapshot_signature)"

  log "Watching $REPO_ROOT with polling every ${POLL_INTERVAL}s"
  log 'Ready'
  while true; do
    current_snapshot="$(snapshot_signature)"
    if [[ "$current_snapshot" != "$previous_snapshot" ]]; then
      previous_snapshot="$current_snapshot"
      run_deploy 'workspace file change'
    fi
    sleep "$POLL_INTERVAL"
  done
}

if [[ ! -f "$DEPLOY_SCRIPT" ]]; then
  log "Missing deploy script at $DEPLOY_SCRIPT"
  exit 1
fi

LAST_RUN_MS=0

if command -v inotifywait >/dev/null 2>&1; then
  watch_with_inotify
else
  log 'inotifywait not found; falling back to polling'
  watch_with_polling
fi