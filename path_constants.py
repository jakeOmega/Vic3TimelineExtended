"""Resolved per-machine paths for the Vic3TimelineExtended mod tooling.

Every Python tool in this repo imports its absolute paths from this module.
The values come from one of three sources, tried in order:

  1. Environment variables (VIC3_BASE_GAME, VIC3_MOD_DEPLOY_TARGET, ...).
     One-off overrides win over the persistent config — handy for testing
     against a different Vic3 install or temporary deploy target.
  2. paths.local.json at the repo root (gitignored). This is what
     `python3 scripts/setup.py` writes after detecting/prompting; it's
     the persistent per-machine answer.
  3. Auto-detection helpers in scripts/_path_detect.py — only useful on
     WSL with a default Steam install.

If none of the three resolve a required path, importing this module raises
RuntimeError with a clear pointer to `python3 scripts/setup.py`.

Adding a new path constant: pick an env var name (VIC3_*), add it to
DEFAULT_KEYS below, extend the autodetect logic in scripts/_path_detect.py
if useful, and assign the constant via `_resolve(...)` further down. For
external resources that not every contributor will have configured (e.g.
optional reference checkouts), pass `optional=True` so `_resolve` returns
None on failure instead of raising at import time.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent
_LOCAL = _REPO_ROOT / "paths.local.json"

# Make the detection helpers importable without requiring scripts/ to be a package.
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import _path_detect  # noqa: E402

_SETUP_HINT = "Run python3 scripts/setup.py to configure machine paths."


def _load_local() -> dict:
    if _LOCAL.exists():
        try:
            return json.loads(_LOCAL.read_text())
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"paths.local.json at {_LOCAL} is not valid JSON: {exc}. {_SETUP_HINT}"
            ) from exc
    return {}


_LOCAL_CFG = _load_local()
_AUTODETECTED: Optional[dict] = None


def _autodetect() -> dict:
    global _AUTODETECTED
    if _AUTODETECTED is None:
        _AUTODETECTED = _path_detect.detect_all()
    return _AUTODETECTED


def _resolve(key: str, env_var: Optional[str] = None, optional: bool = False) -> Optional[str]:
    """Return the resolved value for `key`. Raises RuntimeError unless `optional=True`,
    in which case unresolved keys return None."""
    if env_var:
        v = os.environ.get(env_var)
        if v:
            return v
    if key in _LOCAL_CFG and _LOCAL_CFG[key]:
        return _LOCAL_CFG[key]
    auto = _autodetect().get(key)
    if auto:
        return auto
    if optional:
        return None
    raise RuntimeError(
        f"Could not resolve path '{key}'. "
        f"Set it in {_LOCAL.name}"
        + (f" or via ${env_var}" if env_var else "")
        + f". {_SETUP_HINT}"
    )


# Repo root and docs are always derivable — never need user config.
mod_path = str(_REPO_ROOT)
doc_path = str(_REPO_ROOT / "docs")

# Per-machine paths. Order matches the previous (hand-written) file's order.
base_game_path = _resolve("base_game_path", "VIC3_BASE_GAME")
mod_deploy_target = _resolve("mod_deploy_target", "VIC3_MOD_DEPLOY_TARGET")

# Engine docs (script_docs output): the runtime path is whatever the user last
# wrote there by typing `script_docs` in the in-game console — it could be
# vanilla-loaded OR mod-loaded depending on context. The repo-mirror snapshot
# path (vanilla-only) is preferred as the authoritative baseline when present.
# As of vanilla 1.13.5 the engine-doc logs are no longer shipped under vic3/docs/
# (the upstream owner moved them to the Modding-Digests repo); a derived
# `vanilla_snapshot_docs_path_default` resolves them from the highest-version
# digest checkout on disk. The order consumers should follow: configured
# `vanilla_snapshot_docs_path` (if set and exists) → `vanilla_snapshot_docs_path_default`
# → `mod_loaded_docs_path`. See docs/guides/python_tools.md and
# docs/guides/vanilla_patch_runbook.md § 0.
vanilla_snapshot_docs_path = _resolve(
    "vanilla_snapshot_docs_path", "VIC3_VANILLA_DOCS_SNAPSHOT", optional=True
)
vanilla_source_repo_path = _resolve("vanilla_source_repo_path", "VIC3_VANILLA_REPO")
vanilla_docs_path = _resolve("vanilla_docs_path", "VIC3_VANILLA_DOCS_RUNTIME")
mod_loaded_docs_path = vanilla_docs_path  # alias; same path, clearer intent

game_logs_path = _resolve("game_logs_path", "VIC3_GAME_LOGS")

# Optional: per-vanilla-patch modder change digests
# (https://github.com/Victoria-3-Modding-Co-op/Modding-Digests). Auto-pulled
# on cold start by mod_state_server.py when set. None when unconfigured.
vic3_modding_digests_path: Optional[str] = _resolve(
    "vic3_modding_digests_path", "VIC3_MODDING_DIGESTS_REPO", optional=True
)


def _semver_key(name: str) -> tuple:
    """Sort key for digest version dirs (e.g. '1.13.4' → (1, 13, 4))."""
    parts = []
    for piece in name.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            return ()
    return tuple(parts)


def _derive_digest_docs_path() -> Optional[str]:
    """Find <vic3_modding_digests_path>/<latest-version>/docs containing the
    expected engine-doc logs. Returns None if no usable directory exists."""
    if not vic3_modding_digests_path:
        return None
    root = Path(vic3_modding_digests_path)
    if not root.is_dir():
        return None
    candidates = []
    for child in root.iterdir():
        key = _semver_key(child.name)
        if not key:
            continue
        docs = child / "docs"
        if (docs / "modifiers.log").is_file():
            candidates.append((key, str(docs)))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


# Derived: latest engine-doc snapshot from Modding-Digests. Consumers should
# fall back to this when `vanilla_snapshot_docs_path` is unset or missing.
vanilla_snapshot_docs_path_default: Optional[str] = _derive_digest_docs_path()
