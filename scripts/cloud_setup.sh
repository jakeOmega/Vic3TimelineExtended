#!/usr/bin/env bash
# Bootstraps a cloud sandbox (Claude Code Routine env) for running the
# nightly audit against a live mod_state_server. Idempotent — every step
# guards on prior state so warm-started sandboxes don't redo expensive work.
#
# What it does, in order:
#   1. Sparse-shallow-clone the private vanilla repo (jakeOmega/vic3) into
#      ../vic3. Only game/common, game/localization/english, game/gui,
#      game/map_data are fetched (~150 MB instead of 2 GB).
#   2. Shallow-clone the public Modding-Digests repo into ~/Modding-Digests.
#      mod_state_server uses its highest-version /docs as the engine-doc
#      snapshot (modifier-search, /engine-docs/origin/, etc.).
#   3. Create throwaway dirs for the path_constants.py entries that are
#      irrelevant in the cloud (mod_deploy_target, vanilla_docs_path,
#      game_logs_path) so import doesn't raise.
#   4. Export VIC3_* env vars so path_constants.py resolves cleanly without
#      a paths.local.json.
#   5. Create .venv and install requirements.txt if missing.
#   6. Start mod_state_server in the background and wait for /status.
#
# Re-running is safe: each step short-circuits when its target already
# exists / is up. On failure to start the server within 180 s, the script
# dumps the server log and exits non-zero so the routine fails loudly
# instead of running the audit blind.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

vanilla_dir="$(cd .. && pwd)/vic3"
digests_dir="${HOME}/Modding-Digests"

log() { printf '[cloud_setup] %s\n' "$*"; }

# ---------------------------------------------------------------------------
# 1. Vanilla repo (private — requires gh auth)
# ---------------------------------------------------------------------------
if [ -d "${vanilla_dir}/.git" ]; then
  log "vanilla repo already present at ${vanilla_dir}; skipping clone"
else
  log "cloning jakeOmega/vic3 -> ${vanilla_dir} (sparse, depth=1)"
  # `gh repo clone` forwards flags after `--` to git. `--sparse` initializes
  # an empty sparse-checkout (cone mode) so only the toplevel is materialized
  # before we explicitly opt in to the dirs we want via `sparse-checkout set`.
  gh repo clone jakeOmega/vic3 "${vanilla_dir}" -- --depth=1 --sparse
  git -C "${vanilla_dir}" sparse-checkout set \
    game/common \
    game/localization/english \
    game/gui \
    game/map_data
  log "vanilla sparse checkout ready ($(du -sh "${vanilla_dir}/game" 2>/dev/null | cut -f1) materialized)"
fi

# ---------------------------------------------------------------------------
# 2. Modding-Digests (public — for engine-docs / modifier search)
# ---------------------------------------------------------------------------
if [ -d "${digests_dir}/.git" ]; then
  log "Modding-Digests already present at ${digests_dir}; skipping clone"
else
  log "cloning Modding-Digests -> ${digests_dir}"
  git clone --depth=1 https://github.com/Victoria-3-Modding-Co-op/Modding-Digests.git "${digests_dir}"
fi

# ---------------------------------------------------------------------------
# 3. Dummy paths for path_constants.py's mandatory-but-cloud-irrelevant entries
# ---------------------------------------------------------------------------
mkdir -p /tmp/vic3_deploy_target /tmp/vic3_docs_runtime /tmp/vic3_logs

# ---------------------------------------------------------------------------
# 4. Env vars consumed by path_constants.py (env > paths.local.json > autodetect)
# ---------------------------------------------------------------------------
export VIC3_BASE_GAME="${vanilla_dir}"
export VIC3_VANILLA_REPO="${vanilla_dir}"
export VIC3_MODDING_DIGESTS_REPO="${digests_dir}"
export VIC3_MOD_DEPLOY_TARGET="/tmp/vic3_deploy_target"
export VIC3_VANILLA_DOCS_RUNTIME="/tmp/vic3_docs_runtime"
export VIC3_GAME_LOGS="/tmp/vic3_logs"

# ---------------------------------------------------------------------------
# 5. Venv + deps (requires the regex package for post-load generators)
# ---------------------------------------------------------------------------
if [ ! -x ".venv/bin/python" ]; then
  log "creating .venv and installing requirements.txt"
  python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -r requirements.txt
fi

# ---------------------------------------------------------------------------
# 6. Start mod_state_server (background) + wait for readiness
# ---------------------------------------------------------------------------
if curl -sf http://localhost:8950/status >/dev/null 2>&1; then
  log "mod_state_server already responding on :8950; skipping start"
else
  log "starting mod_state_server (will take ~60–110 s to warm up)"
  nohup .venv/bin/python mod_state_server.py >/tmp/mod_state_server.log 2>&1 &
  disown || true

  deadline=$((SECONDS + 180))
  until curl -sf http://localhost:8950/status >/dev/null 2>&1; do
    if [ $SECONDS -ge $deadline ]; then
      log "ERROR: server did not become ready within 180 s"
      log "---- /tmp/mod_state_server.log tail ----"
      tail -n 80 /tmp/mod_state_server.log || true
      exit 1
    fi
    sleep 3
  done
  log "mod_state_server is ready"
fi

log "bootstrap complete"
