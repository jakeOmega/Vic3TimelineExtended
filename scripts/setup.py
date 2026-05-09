#!/usr/bin/env python3
"""One-shot bootstrap for Vic3TimelineExtended on a fresh machine.

Run with system python3 (no venv yet). Pure stdlib.

What it does:
  1. Detects platform (WSL is the supported primary; Linux/Windows fall through to prompts).
  2. Creates .venv/ if missing and pip-installs requirements.txt.
  3. Auto-detects every per-machine path it can (Steam install via Steam's
     libraryfolders.vdf, Paradox docs folder via Windows username + standard layouts).
  4. Prompts for each path with the detected value as the default. Existing
     values from paths.local.json are also loaded as defaults if re-running.
  5. Validates the vanilla docs snapshot at vanilla_snapshot_docs_path. Prints
     the manual `script_docs` workflow if it's missing — does NOT auto-copy.
  6. Writes paths.local.json at the repo root.
  7. Smoke-tests the deploy with `scripts/deploy.sh` (dry-run).
  8. Prints next steps.

Re-runnable. Can be invoked any time paths move.

Usage:
    python3 scripts/setup.py            # interactive
    python3 scripts/setup.py --no-venv  # skip venv creation/install (paths only)
    python3 scripts/setup.py --yes      # accept all detected defaults non-interactively
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# This script lives at scripts/setup.py — repo root is one level up.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import _path_detect  # noqa: E402

PATHS_LOCAL = REPO_ROOT / "paths.local.json"
VENV_DIR = REPO_ROOT / ".venv"
REQUIREMENTS = REPO_ROOT / "requirements.txt"

# Each entry: (key, prompt label, env_var, optional, validator)
# validator: function(str) -> bool indicating whether the path looks plausible.
PATH_SPECS = [
    (
        "base_game_path",
        "Vic3 install (Steam library / steamapps/common/Victoria 3)",
        "VIC3_BASE_GAME",
        False,
        lambda p: (Path(p) / "game" / "common").exists(),
    ),
    (
        "mod_deploy_target",
        "Mod deploy target (where the engine reads the mod from)",
        "VIC3_MOD_DEPLOY_TARGET",
        False,
        # Mod target may not exist yet — we offer to mkdir below.
        lambda p: True,
    ),
    (
        "vanilla_snapshot_docs_path",
        "Vanilla script_docs snapshot (authoritative engine docs baseline)",
        "VIC3_VANILLA_DOCS_SNAPSHOT",
        True,
        lambda p: (Path(p) / "modifiers.log").exists() or (Path(p) / "triggers.log").exists(),
    ),
    (
        "vanilla_source_repo_path",
        "Vanilla source mirror (HEAD commit date used as 'current vanilla version')",
        "VIC3_VANILLA_REPO",
        True,
        lambda p: Path(p).exists(),
    ),
    (
        "vanilla_docs_path",
        "Vanilla docs runtime path (where in-game `script_docs` writes)",
        "VIC3_VANILLA_DOCS_RUNTIME",
        True,
        lambda p: Path(p).exists(),
    ),
    (
        "game_logs_path",
        "Game logs directory (Vic3's runtime error.log / debug.log)",
        "VIC3_GAME_LOGS",
        True,
        lambda p: Path(p).exists(),
    ),
    (
        "vic3_modding_digests_path",
        "Modding-Digests local clone (per-vanilla-patch modder change digests; auto-cloned on first server start)",
        "VIC3_MODDING_DIGESTS_REPO",
        True,
        # Path may not exist yet — server clones it on first start.
        lambda p: True,
    ),
]


def banner(msg: str) -> None:
    print(f"\n=== {msg} ===")


def info(msg: str) -> None:
    print(f"  {msg}")


def warn(msg: str) -> None:
    print(f"  ! {msg}")


def err(msg: str) -> None:
    print(f"  ✗ {msg}", file=sys.stderr)


def prompt_default(label: str, default: str | None, accept_all: bool) -> str:
    if accept_all and default:
        print(f"  {label}\n    {default} [auto-accepted]")
        return default
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            response = input(f"  {label}{suffix}\n    > ").strip()
        except EOFError:
            print()
            if default:
                return default
            raise SystemExit("Setup needs interactive input. Re-run without --yes or pipe input.")
        if response:
            return response
        if default:
            return default
        warn("Value is required. Try again.")


def ensure_venv(skip: bool) -> None:
    if skip:
        info("Skipping venv creation (--no-venv).")
        return
    banner("Python virtual environment")
    if VENV_DIR.exists():
        info(f".venv already exists at {VENV_DIR}; reusing it.")
    else:
        info(f"Creating .venv at {VENV_DIR}...")
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            err("venv creation failed.")
            raise SystemExit(1)
    pip = VENV_DIR / "bin" / "pip"
    if not pip.exists():
        # Windows-style venv layout (defensive)
        pip = VENV_DIR / "Scripts" / "pip.exe"
    if not pip.exists():
        err(f"Could not find pip in {VENV_DIR}. Setup cannot install dependencies.")
        raise SystemExit(1)
    info(f"Installing requirements: {pip} install -r requirements.txt")
    result = subprocess.run(
        [str(pip), "install", "-r", str(REQUIREMENTS)],
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        err("pip install failed. You can re-run setup after fixing the issue.")
        raise SystemExit(1)


def gather_paths(accept_all: bool) -> dict[str, str]:
    banner("Path configuration")

    existing: dict = {}
    if PATHS_LOCAL.exists():
        try:
            existing = json.loads(PATHS_LOCAL.read_text())
            info(f"Loaded existing values from {PATHS_LOCAL.name}.")
        except json.JSONDecodeError as exc:
            warn(f"{PATHS_LOCAL.name} is not valid JSON ({exc}); ignoring it.")

    detected = _path_detect.detect_all()
    if _path_detect.is_wsl():
        info("WSL detected — autodetection enabled.")
    else:
        info("Non-WSL platform — autodetection limited; you'll be prompted for most paths.")

    resolved: dict[str, str] = {}
    for key, label, env_var, optional, validator in PATH_SPECS:
        # Prefer existing config; else env var; else autodetected.
        default = (
            existing.get(key)
            or os.environ.get(env_var)
            or detected.get(key)
        )
        value = prompt_default(label, default, accept_all)
        if not validator(value):
            if optional:
                warn(f"{key}: {value} doesn't look populated yet (validator failed). Recording anyway.")
            else:
                warn(f"{key}: {value} failed validation but is required. Saving as-is; some tools may break.")
        resolved[key] = value

    # Offer to mkdir the deploy target if missing.
    mod_target = Path(resolved["mod_deploy_target"])
    if not mod_target.exists():
        if accept_all or input(f"  Mod deploy target does not exist. Create {mod_target}? [Y/n] ").strip().lower() in ("", "y", "yes"):
            try:
                mod_target.mkdir(parents=True, exist_ok=True)
                info(f"Created {mod_target}.")
            except OSError as exc:
                warn(f"Could not create {mod_target}: {exc}")

    return resolved


def write_local_config(resolved: dict[str, str]) -> None:
    banner("Writing paths.local.json")
    PATHS_LOCAL.write_text(json.dumps(resolved, indent=4) + "\n")
    info(f"Wrote {PATHS_LOCAL}.")


def check_vanilla_snapshot(resolved: dict[str, str]) -> None:
    banner("Vanilla docs snapshot")
    snapshot = Path(resolved["vanilla_snapshot_docs_path"])
    runtime = Path(resolved["vanilla_docs_path"])
    expected_logs = ["modifiers.log", "triggers.log", "effects.log",
                     "event_targets.log", "on_actions.log", "custom_localization.log"]
    have = [log for log in expected_logs if (snapshot / log).exists()]
    missing = [log for log in expected_logs if log not in have]
    if not missing:
        info(f"Snapshot at {snapshot} looks complete ({len(have)}/{len(expected_logs)} logs).")
        return
    warn(f"Snapshot at {snapshot} is missing: {', '.join(missing)}")
    print()
    print("  To populate the snapshot:")
    print("    1. Launch Victoria 3 with NO mods enabled.")
    print("    2. Open the in-game console (`` ` ``) and type:  script_docs")
    print(f"    3. Copy the resulting *.log files from")
    print(f"       {runtime}")
    print(f"       to")
    print(f"       {snapshot}")
    print("  This is needed by mod_state_server.py to disambiguate vanilla vs mod.")


def smoke_test_deploy() -> None:
    banner("Smoke-testing deploy.sh (dry run)")
    deploy = REPO_ROOT / "scripts" / "deploy.sh"
    if not deploy.exists():
        warn(f"{deploy} not found; skipping smoke test.")
        return
    if not shutil.which("rsync"):
        warn("rsync not on PATH; deploy will fail until installed (apt install rsync).")
        return
    result = subprocess.run(
        ["bash", str(deploy)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        info("Dry-run deploy succeeded.")
    else:
        warn("Dry-run deploy failed:")
        for line in (result.stdout + result.stderr).splitlines()[:20]:
            print(f"      {line}")


def print_next_steps() -> None:
    banner("Next steps")
    print("  Start the mod state server (long-running, used by tooling):")
    print("    .venv/bin/python mod_state_server.py")
    print("  Then in another shell:")
    print("    curl http://localhost:8950/status")
    print("  Apply a deploy (writes to mod_deploy_target):")
    print("    ./scripts/deploy.sh --apply")
    print("  Re-run this setup any time paths move:")
    print("    python3 scripts/setup.py")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--no-venv", action="store_true",
                        help="Skip venv creation and pip install (configure paths only).")
    parser.add_argument("--yes", action="store_true",
                        help="Accept all detected defaults non-interactively.")
    args = parser.parse_args()

    print(f"Vic3TimelineExtended setup. Repo: {REPO_ROOT}")
    ensure_venv(skip=args.no_venv)
    resolved = gather_paths(accept_all=args.yes)
    write_local_config(resolved)
    check_vanilla_snapshot(resolved)
    smoke_test_deploy()
    print_next_steps()
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
