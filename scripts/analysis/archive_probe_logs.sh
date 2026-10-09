#!/usr/bin/env bash
# Keep every debug.log generation (and every Nth autosave) while a long probe runs.
#
#   scripts/analysis/archive_probe_logs.sh OUT_DIR [SAVE_EVERY]
#
# debug.log rolls over at 512 KB and the game keeps five old generations, so a
# probe that logs for game-years loses its first lines. Every 5 seconds this copies
# each debug.N.log whose modification time changed (a rotation just wrote it) and,
# every 60 seconds, the live debug.log. The copies overlap; the probe's reader
# (demographics_growth_probe.py) reads identical lines once. With SAVE_EVERY > 0 it
# also copies every SAVE_EVERY-th new autosave.v3 (plain-text ones are ~250 MB).
# Stop it with Ctrl-C (or kill); it never deletes anything.
set -euo pipefail

OUT="${1:?usage: archive_probe_logs.sh OUT_DIR [SAVE_EVERY]}"
SAVE_EVERY="${2:-0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOGS="$(python3 -c "import sys; sys.path.insert(0, '$REPO_ROOT'); import path_constants; print(path_constants.game_logs_path)")"
SAVES="$(dirname "$LOGS")/save games"
mkdir -p "$OUT/logs" "$OUT/saves"
declare -A seen
saves_seen=0
last_live=0
# an autosave already on disk belongs to an earlier game: skip it
[[ -f "$SAVES/autosave.v3" ]] && seen[autosave]="$(stat -c %Y "$SAVES/autosave.v3")"
echo "archiving $LOGS -> $OUT (autosave every ${SAVE_EVERY:-0})"
while true; do
  for f in "$LOGS"/debug.[1-5].log; do
    [[ -f "$f" ]] || continue
    stamp="$(stat -c %Y-%s "$f")"
    if [[ "${seen[$f]:-}" != "$stamp" ]]; then
      seen[$f]="$stamp"
      cp "$f" "$OUT/logs/$(basename "$f" .log).$(date +%s%N).log"
    fi
  done
  now="$(date +%s)"
  if (( now - last_live >= 60 )) && [[ -f "$LOGS/debug.log" ]]; then
    cp "$LOGS/debug.log" "$OUT/logs/debug.live.$(date +%s%N).log"
    last_live="$now"
  fi
  if (( SAVE_EVERY > 0 )) && [[ -f "$SAVES/autosave.v3" ]]; then
    stamp="$(stat -c %Y "$SAVES/autosave.v3")"
    if [[ "${seen[autosave]:-}" != "$stamp" ]]; then
      seen[autosave]="$stamp"
      saves_seen=$((saves_seen + 1))
      if (( (saves_seen - 1) % SAVE_EVERY == 0 )); then
        sleep 5   # let the game finish writing it
        cp "$SAVES/autosave.v3" "$OUT/saves/autosave.$(date +%s).v3"
      fi
    fi
  fi
  sleep 5
done
