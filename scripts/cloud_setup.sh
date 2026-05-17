#!/usr/bin/env bash
# Bootstraps a cloud sandbox (Claude Code Routine env) for running the
# nightly audit against a live mod_state_server. Idempotent — every step
# guards on prior state so warm-started sandboxes don't redo expensive work.
#
# What it does, in order:
#   1. Sparse-shallow-clone the private vanilla repo (jakeOmega/vic3) into
#      ../vic3. Only game/common, game/localization/english, game/gui,
#      game/map_data are fetched (~150 MB instead of 2 GB). Auth in the
#      Routines sandbox requires `GH_TOKEN` in the routine's Environment
#      Variables — the proxy that auto-authenticates the routine's primary
#      repo does NOT cover cross-repo private clones (see issue #99). In
#      local dev, the script falls back to whatever credentials git is
#      already configured with.
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
# instead of running the audit blind. An ERR trap (below) does the same
# for any other non-zero exit — needed because when the script is `source`d
# from a parent shell whose errexit state differs, `set -e` alone has been
# observed to miss command-not-found failures (see issue #93).

set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

vanilla_dir="$(cd .. && pwd)/vic3"
digests_dir="${HOME}/Modding-Digests"

log() { printf '[cloud_setup] %s\n' "$*"; }

trap 'rc=$?; log "ERROR: bootstrap failed at line $LINENO (exit $rc)"; \
      if [ -f /tmp/mod_state_server.log ]; then \
        log "---- /tmp/mod_state_server.log tail ----"; \
        tail -n 60 /tmp/mod_state_server.log; \
      fi; \
      exit $rc' ERR

# ---------------------------------------------------------------------------
# 1. Vanilla repo (private — needs GH_TOKEN in routines; local git creds otherwise)
# ---------------------------------------------------------------------------
# Auth resolution: prefer GH_TOKEN (or GITHUB_TOKEN) embedded in the URL.
# The Routines GitHub proxy doesn't auto-authenticate cross-repo private
# clones — only the routine's primary repo — so a token is required in the
# sandbox (set it in the routine's Environment Variables UI; see issue #99).
# In local dev, leaving the token unset falls back to whatever credentials
# git already has configured.
vanilla_remote_token="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [ -n "${vanilla_remote_token}" ]; then
  vanilla_remote_url="https://x-access-token:${vanilla_remote_token}@github.com/jakeOmega/vic3.git"
  vanilla_auth_source="GH_TOKEN/GITHUB_TOKEN env"
else
  vanilla_remote_url="https://github.com/jakeOmega/vic3.git"
  vanilla_auth_source="ambient git credentials (no GH_TOKEN/GITHUB_TOKEN env)"
fi

# Preflight: cheap auth probe before the (slower) clone. Fails fast with an
# actionable message if the token is missing or wrong, so the routine log
# doesn't bury the cause under git's terse "could not read Username" line.
if [ ! -d "${vanilla_dir}/.git" ]; then
  log "preflight: probing jakeOmega/vic3 auth via ${vanilla_auth_source}"
  if ! GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code "${vanilla_remote_url}" HEAD >/dev/null 2>&1; then
    log "ERROR: cannot reach jakeOmega/vic3 — auth probe failed."
    log "  Auth source tried: ${vanilla_auth_source}"
    if [ -z "${vanilla_remote_token}" ]; then
      log "  Fix: set GH_TOKEN in the routine's Environment Variables UI to a"
      log "  GitHub personal access token with repo:read scope on jakeOmega/vic3."
      log "  The Routines GitHub proxy only auto-authenticates the routine's"
      log "  primary repo, not cross-repo private clones (issue #99)."
    else
      log "  Fix: verify the GH_TOKEN/GITHUB_TOKEN has repo:read scope on"
      log "  jakeOmega/vic3 and is not expired."
    fi
    exit 1
  fi
fi

if [ -d "${vanilla_dir}/.git" ]; then
  log "vanilla repo already present at ${vanilla_dir}; skipping clone"
else
  log "cloning jakeOmega/vic3 -> ${vanilla_dir} (sparse, depth=1)"
  # `--sparse` initializes cone mode so only the toplevel is materialized
  # before we explicitly opt in to the dirs we want via `sparse-checkout set`.
  GIT_TERMINAL_PROMPT=0 git clone --depth=1 --filter=blob:none --sparse \
      "${vanilla_remote_url}" "${vanilla_dir}"
  git -C "${vanilla_dir}" sparse-checkout set \
    game/common \
    game/localization/english \
    game/gui \
    game/map_data

  # Hard-fail if the clone silently no-op'd. Guards against variants the
  # preflight can't catch — sparse-checkout regression, post-clone disk
  # issue, etc.
  if [ ! -d "${vanilla_dir}/game/common" ] \
     || [ -z "$(ls -A "${vanilla_dir}/game/common" 2>/dev/null)" ]; then
    log "ERROR: vanilla clone did not materialize at ${vanilla_dir}/game/common"
    log "---- ${vanilla_dir} listing ----"
    ls -la "${vanilla_dir}" 2>/dev/null || true
    ls -la "${vanilla_dir}/game" 2>/dev/null || true
    exit 1
  fi
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
