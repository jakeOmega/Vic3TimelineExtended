#!/usr/bin/env bash
# scripts/deploy.sh — copy game-required files from the WSL working copy
# to the Windows-side Paradox mod folder.
#
# Usage:
#   ./scripts/deploy.sh            # dry-run (prints what would change)
#   ./scripts/deploy.sh --apply    # actually syncs
#
# The source is this repo; the destination is the Paradox mod folder on the
# Windows side (reached from WSL via /mnt/c/...). Only files the Clausewitz
# engine actually needs are copied; Python tools, docs, tests, logs, and the
# .git directory stay behind.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Resolve the deploy target. Order: env var override → path_constants.py
# (which itself reads paths.local.json → env vars → autodetect). path_constants
# only uses stdlib so system python3 works even without .venv.
if [[ -n "${VIC3_MOD_DEPLOY_TARGET:-}" ]]; then
  DEST="$VIC3_MOD_DEPLOY_TARGET"
else
  DEST="$(python3 -c "import sys; sys.path.insert(0, '$REPO_ROOT'); from path_constants import mod_deploy_target; print(mod_deploy_target)" 2>/dev/null || true)"
fi

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then APPLY=1; fi

RSYNC_FLAGS=(
  -rtv                  # recursive, preserve times, verbose (omit -a: no perms/owner on /mnt/c)
  --delete
  --prune-empty-dirs
  --no-perms
  --no-owner
  --no-group
)
[[ "$APPLY" -eq 0 ]] && RSYNC_FLAGS+=(--dry-run)

# Include only game-required top-level entries; exclude everything else.
# Trailing /*** means "this directory and everything under it".
INCLUDES=(
  --include=/common
  --include=/common/***
  --include=/events
  --include=/events/***
  --include=/localization
  --include=/localization/***
  --include=/gui
  --include=/gui/***
  --include=/gfx
  --include=/gfx/***
  --include=/map_data
  --include=/map_data/***
  --include=/.metadata
  --include=/.metadata/***
  --include=/descriptor.mod
  --include=/thumbnail.png
  --exclude=/*
  --exclude=*.pyc
  --exclude=__pycache__/
  --exclude=.DS_Store
)

if [[ -z "$DEST" ]]; then
  echo "No deploy target configured."
  echo "Run python3 scripts/setup.py to configure paths, or set VIC3_MOD_DEPLOY_TARGET."
  exit 1
fi
if [[ ! -d "$DEST" ]]; then
  echo "Deploy target does not exist: $DEST"
  echo "Create it first, or re-run python3 scripts/setup.py."
  exit 1
fi

rsync "${RSYNC_FLAGS[@]}" "${INCLUDES[@]}" "$REPO_ROOT/" "$DEST/"

if [[ "$APPLY" -eq 0 ]]; then
  echo
  echo "DRY RUN. Re-run with --apply to copy files."
fi
