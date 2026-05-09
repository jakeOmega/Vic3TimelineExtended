"""Path auto-detection helpers shared by path_constants.py and scripts/setup.py.

Pure stdlib — usable from system python3 before the venv exists.

The functions here are best-effort. Each returns a string path on success,
None on failure (so callers can fall through to prompts or env vars).
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional


VIC3_STEAM_APP_ID = "529340"


def is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def windows_username() -> Optional[str]:
    """Return the Windows-side username when running under WSL, else None."""
    if not is_wsl():
        return None
    try:
        out = subprocess.run(
            ["cmd.exe", "/c", "echo %USERNAME%"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    name = out.stdout.strip().strip("\r")
    return name or None


def wsl_path_from_windows(win_path: str) -> str:
    """Convert C:\\Foo\\Bar (or C:/Foo/Bar) into /mnt/c/Foo/Bar."""
    p = win_path.replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if not m:
        return win_path
    drive, rest = m.group(1).lower(), m.group(2)
    return f"/mnt/{drive}/{rest}"


def _read_libraryfolders_vdf(vdf_path: Path) -> list[str]:
    """Parse a Steam libraryfolders.vdf and return library root paths.

    Format is roughly:
        "libraryfolders" {
            "0" { "path" "C:\\\\Program Files (x86)\\\\Steam" "apps" { "529340" "..." } }
            "1" { "path" "D:\\\\SteamLibrary" "apps" { ... } }
        }

    We only care about the path values that contain Vic3 (app id 529340).
    """
    if not vdf_path.exists():
        return []
    try:
        text = vdf_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    libraries: list[tuple[str, str]] = []  # (path, apps_block)
    for m in re.finditer(
        r'"path"\s*"([^"]+)".*?"apps"\s*\{(.*?)\}',
        text, re.DOTALL,
    ):
        libraries.append((m.group(1).replace("\\\\", "\\"), m.group(2)))
    return [path for path, apps in libraries if VIC3_STEAM_APP_ID in apps]


def find_vic3_install() -> Optional[str]:
    """Locate the Vic3 install root via Steam's libraryfolders.vdf.

    Returns a path that should contain `game/`, `dlc/`, etc. — i.e. the
    `steamapps/common/Victoria 3` folder. WSL-only fast path; on other
    platforms returns None.
    """
    if not is_wsl():
        return None
    candidate_vdfs = [
        Path("/mnt/c/Program Files (x86)/Steam/config/libraryfolders.vdf"),
        Path("/mnt/c/Program Files/Steam/config/libraryfolders.vdf"),
    ]
    for vdf in candidate_vdfs:
        for lib_root_win in _read_libraryfolders_vdf(vdf):
            lib_root = wsl_path_from_windows(lib_root_win)
            install = Path(lib_root) / "steamapps" / "common" / "Victoria 3"
            if install.exists():
                return str(install)
    # Fallback: the default install location, even without VDF parsing
    default = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3")
    if default.exists():
        return str(default)
    return None


def find_paradox_docs(winuser: Optional[str] = None) -> Optional[str]:
    """Locate the Victoria 3 Paradox documents folder. WSL-only.

    Tries OneDrive-redirected first (the common modern default), then
    plain Documents. Validates by checking for the `mod/`, `logs/`, or
    `settings.txt` markers Vic3 creates.
    """
    if not is_wsl():
        return None
    if winuser is None:
        winuser = windows_username()
    if not winuser:
        return None
    suffix = "Documents/Paradox Interactive/Victoria 3"
    candidates = [
        Path(f"/mnt/c/Users/{winuser}/OneDrive/{suffix}"),
        Path(f"/mnt/c/Users/{winuser}/{suffix}"),
    ]
    for cand in candidates:
        if cand.exists() and any(
            (cand / marker).exists()
            for marker in ("mod", "logs", "settings.txt")
        ):
            return str(cand)
    # No marker found — return the OneDrive guess if it exists at all,
    # or the plain Documents guess. Caller will prompt to confirm.
    for cand in candidates:
        if cand.exists():
            return str(cand)
    return None


def detect_all() -> dict[str, Optional[str]]:
    """Run every detector and return a dict of best-effort defaults."""
    repo_root = str(Path(__file__).resolve().parents[1])
    home = Path(os.path.expanduser("~"))
    vic3_install = find_vic3_install()
    paradox_docs = find_paradox_docs()
    return {
        "mod_path": repo_root,
        "base_game_path": vic3_install,
        "mod_deploy_target": (
            f"{paradox_docs}/mod/Vic3TimelineExtended" if paradox_docs else None
        ),
        "vanilla_source_repo_path": str(home / "src" / "vic3"),
        "vanilla_snapshot_docs_path": str(home / "src" / "vic3" / "docs"),
        "vic3_modding_digests_path": str(home / "src" / "Modding-Digests"),
        "vanilla_docs_path": (
            f"{paradox_docs}/docs" if paradox_docs else None
        ),
        "game_logs_path": (
            f"{paradox_docs}/logs" if paradox_docs else None
        ),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(detect_all(), indent=2))
