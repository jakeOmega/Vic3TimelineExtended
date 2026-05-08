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
if useful, and assign the constant via `_resolve(...)` further down.
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


def _resolve(key: str, env_var: Optional[str] = None) -> str:
    """Return the resolved value for `key`, or raise RuntimeError."""
    if env_var:
        v = os.environ.get(env_var)
        if v:
            return v
    if key in _LOCAL_CFG and _LOCAL_CFG[key]:
        return _LOCAL_CFG[key]
    auto = _autodetect().get(key)
    if auto:
        return auto
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

# Engine docs (script_docs output): two sources, used together for vanilla-vs-mod
# disambiguation. The runtime path is whatever the user last wrote there by typing
# `script_docs` in the in-game console — it could be vanilla-loaded OR mod-loaded
# depending on context. The repo-mirror path is a vanilla-only snapshot; treat it
# as the authoritative baseline. See docs/guides/python_tools.md.
vanilla_snapshot_docs_path = _resolve("vanilla_snapshot_docs_path", "VIC3_VANILLA_DOCS_SNAPSHOT")
vanilla_source_repo_path = _resolve("vanilla_source_repo_path", "VIC3_VANILLA_REPO")
vanilla_docs_path = _resolve("vanilla_docs_path", "VIC3_VANILLA_DOCS_RUNTIME")
mod_loaded_docs_path = vanilla_docs_path  # alias; same path, clearer intent

game_logs_path = _resolve("game_logs_path", "VIC3_GAME_LOGS")
