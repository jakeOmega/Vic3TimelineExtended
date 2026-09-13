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

Only `mod_path` and `doc_path` are computed at import. Every per-machine
path resolves lazily on first attribute access (PEP 562 module `__getattr__`)
and is cached afterwards, so importing this module never needs a Victoria 3
install; a tool that actually reads an unresolvable path gets the same
RuntimeError as before, with a clear pointer to `python3 scripts/setup.py`.
`from path_constants import base_game_path` works unchanged (PEP 562 covers
`from`-imports), and resolution happens at that import.

Adding a new path constant: pick an env var name (VIC3_*), register it in
`_LAZY_SPECS` below, and extend the autodetect logic in scripts/_path_detect.py
if useful. For external resources that not every contributor will have
configured (e.g. optional reference checkouts), mark it optional so `_resolve`
returns None on failure instead of raising.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

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

# Every other constant resolves lazily, on first attribute access (PEP 562
# module `__getattr__` below), and is then cached in this module's globals.
# That keeps `import path_constants` — and therefore every mod-only audit CLI
# and most of the test suite — working on a machine with no Victoria 3 install:
# only the tools that actually read a game path pay the RuntimeError.
#
# `_LAZY_SPECS[name] = (paths.local.json key, env var, optional)`; `optional`
# constants return None instead of raising when unresolved.
#
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
#
# `vic3_modding_digests_path` is the optional per-vanilla-patch modder change
# digest checkout (https://github.com/Victoria-3-Modding-Co-op/Modding-Digests).
# Auto-pulled on cold start by mod_state_server.py when set; None when unconfigured.
_LAZY_SPECS: dict[str, tuple[str, str, bool]] = {
    "base_game_path": ("base_game_path", "VIC3_BASE_GAME", False),
    "mod_deploy_target": ("mod_deploy_target", "VIC3_MOD_DEPLOY_TARGET", False),
    "vanilla_snapshot_docs_path": (
        "vanilla_snapshot_docs_path",
        "VIC3_VANILLA_DOCS_SNAPSHOT",
        True,
    ),
    "vanilla_source_repo_path": ("vanilla_source_repo_path", "VIC3_VANILLA_REPO", False),
    "vanilla_docs_path": ("vanilla_docs_path", "VIC3_VANILLA_DOCS_RUNTIME", False),
    "game_logs_path": ("game_logs_path", "VIC3_GAME_LOGS", False),
    "vic3_modding_digests_path": (
        "vic3_modding_digests_path",
        "VIC3_MODDING_DIGESTS_REPO",
        True,
    ),
}

# Aliases: same value, clearer intent at the call site.
_LAZY_ALIASES: dict[str, str] = {"mod_loaded_docs_path": "vanilla_docs_path"}

if TYPE_CHECKING:  # pragma: no cover — declarations for type checkers/IDEs only.
    base_game_path: str
    mod_deploy_target: str
    vanilla_snapshot_docs_path: Optional[str]
    vanilla_source_repo_path: str
    vanilla_docs_path: str
    mod_loaded_docs_path: str
    game_logs_path: str
    vic3_modding_digests_path: Optional[str]
    vanilla_snapshot_docs_path_default: Optional[str]


def _lazy(name: str):
    """Resolve `name` on first use and cache it in this module's globals.

    Used by the module-level `__getattr__` and by module-internal code, which
    cannot rely on `__getattr__` (PEP 562 only covers attribute access on the
    module object, not bare global lookups inside functions)."""
    if name in globals():
        return globals()[name]
    if name in _LAZY_SPECS:
        key, env_var, optional = _LAZY_SPECS[name]
        value = _resolve(key, env_var, optional=optional)
    elif name in _LAZY_ALIASES:
        value = _lazy(_LAZY_ALIASES[name])
    elif name in _LAZY_DERIVED:
        value = _LAZY_DERIVED[name]()
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


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
    digests_root = _lazy("vic3_modding_digests_path")
    if not digests_root:
        return None
    root = Path(digests_root)
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
_LAZY_DERIVED: dict[str, Callable[[], Optional[str]]] = {
    "vanilla_snapshot_docs_path_default": _derive_digest_docs_path,
}


# Exported names, derived from the tables above so they cannot drift. `__all__`
# matters here: `from path_constants import *` bypasses `__getattr__` unless the
# lazy constants are named, in which case CPython getattr()s each entry (and so
# resolves every one of them).
__all__ = ["mod_path", "doc_path", *_LAZY_SPECS, *_LAZY_ALIASES, *_LAZY_DERIVED]


def __getattr__(name: str):
    """PEP 562 hook: resolve per-machine paths on first access, then cache.

    Keeps `from path_constants import base_game_path` working exactly as
    before — including the RuntimeError + `python3 scripts/setup.py` hint when
    the path cannot be resolved — while leaving the import itself cheap and
    game-install-free."""
    return _lazy(name)


def __dir__() -> list:
    return sorted(
        set(globals()) | set(_LAZY_SPECS) | set(_LAZY_ALIASES) | set(_LAZY_DERIVED)
    )
