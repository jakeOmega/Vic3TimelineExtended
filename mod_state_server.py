"""
Mod State Server - persistent HTTP API for querying parsed mod/vanilla data.

Start:  python mod_state_server.py            # normal start (skips if already running)
        python mod_state_server.py --replace   # kill existing instance, take over port

Query:  Invoke-RestMethod http://localhost:8950/status
        Invoke-RestMethod http://localhost:8950/laws
        python mod_state_client.py laws

Logs:   mod_state_server.log (rotated each startup, previous kept as .log.1)
"""

import importlib
import json
import logging
import logging.handlers
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs, unquote
from urllib.request import urlopen
from urllib.error import URLError

from mod_state import ModState
from paradox_file_parser import ParadoxFileParser
from path_constants import (
    base_game_path,
    doc_path,
    mod_path,
    vanilla_docs_path,
    vanilla_snapshot_docs_path,
    vanilla_snapshot_docs_path_default,
    vanilla_source_repo_path,
    mod_loaded_docs_path,
    game_logs_path,
    vic3_modding_digests_path,
)

# Annotator registry — importing pm_balance_lib triggers registration of the
# `balance` annotator for production methods. Keep this import grouped with
# other annotator-owning libraries; new ones get added by importing them
# here so their registrations happen before any request runs.
import annotators
import pm_balance_lib  # noqa: F401 — imported for its annotator side effect
import tech_unlocks_lib

PORT = 8950
PID_FILE = os.path.join(mod_path, "mod_state_server.pid")

# ---------------------------------------------------------------------------
# Logging setup  (log rotates each startup; keeps 1 backup)
# ---------------------------------------------------------------------------
LOG_FILE = os.path.join(mod_path, "mod_state_server.log")

logger = logging.getLogger("mod_state_server")
logger.setLevel(logging.DEBUG)

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

_file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, mode="a", maxBytes=0, backupCount=2, encoding="utf-8",
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))

logger.addHandler(_console_handler)
logger.addHandler(_file_handler)

_server_start_time: float = 0.0  # set in main()

# ---------------------------------------------------------------------------
# Path configuration (mirrors mod_state_script.py)
#
# Use forward slashes everywhere; path_constants exposes Linux-rooted paths,
# and the win-style backslash trick from the pre-WSL repo no longer works.
# ---------------------------------------------------------------------------
_BASE_COMMON = os.path.join(base_game_path, "game", "common")
_MOD_COMMON = os.path.join(mod_path, "common")

base_game_paths = {
    "Building Groups": os.path.join(_BASE_COMMON, "building_groups"),
    "Buildings": os.path.join(_BASE_COMMON, "buildings"),
    "Technologies": os.path.join(_BASE_COMMON, "technology", "technologies"),
    "PM Groups": os.path.join(_BASE_COMMON, "production_method_groups"),
    "PMs": os.path.join(_BASE_COMMON, "production_methods"),
    "Ideologies": os.path.join(_BASE_COMMON, "ideologies"),
    "Battle Conditions": os.path.join(_BASE_COMMON, "battle_conditions"),
    "Buy Packages": os.path.join(_BASE_COMMON, "buy_packages"),
    "Character Interactions": os.path.join(_BASE_COMMON, "character_interactions"),
    "Character Traits": os.path.join(_BASE_COMMON, "character_traits"),
    "Combat Unit Groups": os.path.join(_BASE_COMMON, "combat_unit_groups"),
    "Combat Unit Types": os.path.join(_BASE_COMMON, "combat_unit_types"),
    "Company Types": os.path.join(_BASE_COMMON, "company_types"),
    "Diplomatic Actions": os.path.join(_BASE_COMMON, "diplomatic_actions"),
    "Diplomatic Plays": os.path.join(_BASE_COMMON, "diplomatic_plays"),
    "Goods": os.path.join(_BASE_COMMON, "goods"),
    "Institutions": os.path.join(_BASE_COMMON, "institutions"),
    "Interest Groups": os.path.join(_BASE_COMMON, "interest_groups"),
    "Law Groups": os.path.join(_BASE_COMMON, "law_groups"),
    "Laws": os.path.join(_BASE_COMMON, "laws"),
    "Mobilization Option Groups": os.path.join(_BASE_COMMON, "mobilization_option_groups"),
    "Mobilization Options": os.path.join(_BASE_COMMON, "mobilization_options"),
    "Modifier Types": os.path.join(_BASE_COMMON, "modifier_type_definitions"),
    "Modifiers": os.path.join(_BASE_COMMON, "static_modifiers"),
    "Pop Needs": os.path.join(_BASE_COMMON, "pop_needs"),
    "Subject Types": os.path.join(_BASE_COMMON, "subject_types"),
    "Script Values": os.path.join(_BASE_COMMON, "script_values"),
    "Scripted Buttons": os.path.join(_BASE_COMMON, "scripted_buttons"),
    "Ship Types": os.path.join(_BASE_COMMON, "ship_types"),
    "Ship Groups": os.path.join(_BASE_COMMON, "ship_groups"),
    "Ship Modifications": os.path.join(_BASE_COMMON, "ship_modifications"),
    "Ship Modification Slots": os.path.join(_BASE_COMMON, "ship_modification_slots"),
    "Ship Name Definitions": os.path.join(_BASE_COMMON, "ship_name_definitions"),
    "Journal Entries": os.path.join(_BASE_COMMON, "journal_entries"),
    "Journal Entry Groups": os.path.join(_BASE_COMMON, "journal_entry_groups"),
    "Decisions": os.path.join(_BASE_COMMON, "decisions"),
    "Treaty Articles": os.path.join(_BASE_COMMON, "treaty_articles"),
    "Religions": os.path.join(_BASE_COMMON, "religions"),
    "Decrees": os.path.join(_BASE_COMMON, "decrees"),
    # Vocabularies the engine needs but the loader didn't include before:
    "Cultures": os.path.join(_BASE_COMMON, "cultures"),
    "Country Ranks": os.path.join(_BASE_COMMON, "country_ranks"),
    "Discrimination Traits": os.path.join(_BASE_COMMON, "discrimination_traits"),
    "Pop Types": os.path.join(_BASE_COMMON, "pop_types"),
    "Terrains": os.path.join(_BASE_COMMON, "terrain"),
    "Game Concepts": os.path.join(_BASE_COMMON, "game_concepts"),
}

mod_paths = {
    "Building Groups": os.path.join(_MOD_COMMON, "building_groups"),
    "Buildings": os.path.join(_MOD_COMMON, "buildings"),
    "Technologies": os.path.join(_MOD_COMMON, "technology", "technologies"),
    "PM Groups": os.path.join(_MOD_COMMON, "production_method_groups"),
    "PMs": os.path.join(_MOD_COMMON, "production_methods"),
    "Ideologies": os.path.join(_MOD_COMMON, "ideologies"),
    "Battle Conditions": os.path.join(_MOD_COMMON, "battle_conditions"),
    "Buy Packages": os.path.join(_MOD_COMMON, "buy_packages"),
    "Character Interactions": os.path.join(_MOD_COMMON, "character_interactions"),
    "Character Traits": os.path.join(_MOD_COMMON, "character_traits"),
    "Combat Unit Groups": os.path.join(_MOD_COMMON, "combat_unit_groups"),
    "Combat Unit Types": os.path.join(_MOD_COMMON, "combat_unit_types"),
    "Company Types": os.path.join(_MOD_COMMON, "company_types"),
    "Diplomatic Actions": os.path.join(_MOD_COMMON, "diplomatic_actions"),
    "Diplomatic Plays": os.path.join(_MOD_COMMON, "diplomatic_plays"),
    "Goods": os.path.join(_MOD_COMMON, "goods"),
    "Institutions": os.path.join(_MOD_COMMON, "institutions"),
    "Interest Groups": os.path.join(_MOD_COMMON, "interest_groups"),
    "Laws": os.path.join(_MOD_COMMON, "laws"),
    "Law Groups": os.path.join(_MOD_COMMON, "law_groups"),
    "Mobilization Option Groups": os.path.join(_MOD_COMMON, "mobilization_option_groups"),
    "Mobilization Options": os.path.join(_MOD_COMMON, "mobilization_options"),
    "Modifier Types": os.path.join(_MOD_COMMON, "modifier_type_definitions"),
    "Modifiers": os.path.join(_MOD_COMMON, "static_modifiers"),
    "Pop Needs": os.path.join(_MOD_COMMON, "pop_needs"),
    "Subject Types": os.path.join(_MOD_COMMON, "subject_types"),
    "Script Values": os.path.join(_MOD_COMMON, "script_values"),
    "Scripted Effects": os.path.join(_MOD_COMMON, "scripted_effects"),
    "Scripted Triggers": os.path.join(_MOD_COMMON, "scripted_triggers"),
    "Scripted Buttons": os.path.join(_MOD_COMMON, "scripted_buttons"),
    "Ship Types": os.path.join(_MOD_COMMON, "ship_types"),
    "Ship Groups": os.path.join(_MOD_COMMON, "ship_groups"),
    "Ship Modifications": os.path.join(_MOD_COMMON, "ship_modifications"),
    "Ship Modification Slots": os.path.join(_MOD_COMMON, "ship_modification_slots"),
    "Ship Name Definitions": os.path.join(_MOD_COMMON, "ship_name_definitions"),
    "Journal Entries": os.path.join(_MOD_COMMON, "journal_entries"),
    "Journal Entry Groups": os.path.join(_MOD_COMMON, "journal_entry_groups"),
    "Decisions": os.path.join(_MOD_COMMON, "decisions"),
    "On Actions": os.path.join(_MOD_COMMON, "on_actions"),
    "Treaty Articles": os.path.join(_MOD_COMMON, "treaty_articles"),
    "Religions": os.path.join(_MOD_COMMON, "religions"),
    "Decrees": os.path.join(_MOD_COMMON, "decrees"),
    "Events": os.path.join(mod_path, "events"),
    # Mod-side counterparts of the new vocabularies (most are vanilla-only, but
    # listed so the mod can override them in future).
    "Cultures": os.path.join(_MOD_COMMON, "cultures"),
    "Country Ranks": os.path.join(_MOD_COMMON, "country_ranks"),
    "Discrimination Traits": os.path.join(_MOD_COMMON, "discrimination_traits"),
    "Pop Types": os.path.join(_MOD_COMMON, "pop_types"),
    "Terrains": os.path.join(_MOD_COMMON, "terrain"),
    "Game Concepts": os.path.join(_MOD_COMMON, "game_concepts"),
}

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
ms: ModState = None  # type: ignore[assignment]
startup_elapsed: float = 0.0
engine_docs: dict = {}  # Parsed engine documentation (effects, triggers, etc.)
dev_reference_docs: dict = {}  # .md files from base game common/ dirs


# ---------------------------------------------------------------------------
# Instance management  (duplicate detection, PID file, port probing)
# ---------------------------------------------------------------------------
def _probe_existing_server(timeout: float = 3.0) -> dict | None:
    """Try to reach an existing server on PORT.  Returns status dict or None."""
    try:
        resp = urlopen(f"http://127.0.0.1:{PORT}/status", timeout=timeout)
        return json.loads(resp.read())
    except Exception:
        return None


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def _write_pid_file():
    """Write our PID to the PID file."""
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger.warning(f"Could not write PID file: {e}")


def _read_pid_file() -> int | None:
    """Read PID from PID file.  Returns None if missing or invalid."""
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _cleanup_pid_file():
    """Remove PID file on exit."""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception:
        pass


def _kill_existing_server() -> bool:
    """Attempt to kill an existing server process.  Returns True if killed."""
    pid = _read_pid_file()
    if pid and pid != os.getpid() and _is_pid_alive(pid):
        logger.info(f"Killing existing server (PID {pid})…")
        try:
            if sys.platform == "win32":
                import subprocess
                subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                               capture_output=True, timeout=10)
            else:
                os.kill(pid, signal.SIGTERM)
            # Wait up to 5s for it to die
            for _ in range(50):
                if not _is_pid_alive(pid):
                    break
                time.sleep(0.1)
            else:
                logger.warning(f"PID {pid} did not die after 5s")
                return False
            logger.info(f"Killed existing server (PID {pid})")
            return True
        except Exception as e:
            logger.warning(f"Failed to kill PID {pid}: {e}")
    return False


def _check_port_available() -> bool:
    """Check if the port is available for binding.

    Sets SO_REUSEADDR to mirror what HTTPServer does at bind time, so a
    lingering TIME_WAIT socket from a just-killed server doesn't make us
    return False when the real bind would succeed.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", PORT))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _ensure_single_instance(replace: bool = False) -> bool:
    """Ensure only one server instance runs.

    If replace=True, kills any existing instance.
    Returns True if we should proceed to start, False if we should exit.
    """
    existing = _probe_existing_server()
    if existing:
        pid = _read_pid_file()
        pid_info = f" (PID {pid})" if pid else ""
        if replace:
            logger.info(f"--replace: taking over from existing server{pid_info}")
            _kill_existing_server()
            # Wait for port to become available
            for i in range(50):
                if _check_port_available():
                    break
                time.sleep(0.1)
            else:
                logger.error("Port still occupied after killing existing server")
                return False
            return True
        else:
            logger.info(
                f"Server already running{pid_info} "
                f"(up {existing.get('startup_seconds', '?')}s load, "
                f"{existing.get('localization_keys', '?')} loc keys). "
                f"Use --replace to take over."
            )
            print(f"\nServer already running on http://127.0.0.1:{PORT}{pid_info}.")
            print("Use --replace to kill the existing instance and start a new one.")
            return False

    # No server responding — check for stale PID file
    stale_pid = _read_pid_file()
    if stale_pid:
        if _is_pid_alive(stale_pid):
            # Process exists but not responding on port — might be loading
            logger.info(
                f"PID {stale_pid} is alive but not responding on port {PORT} "
                f"(may still be loading). Waiting up to 90s…"
            )
            for i in range(90):
                time.sleep(1)
                resp = _probe_existing_server(timeout=2.0)
                if resp:
                    logger.info(f"Existing server came up after {i+1}s wait")
                    print(f"\nExisting server (PID {stale_pid}) finished loading after {i+1}s.")
                    return False
                if not _is_pid_alive(stale_pid):
                    logger.info(f"PID {stale_pid} died while waiting")
                    break
            else:
                if replace:
                    logger.info(f"Timed out waiting; killing PID {stale_pid}")
                    _kill_existing_server()
                else:
                    logger.warning(
                        f"PID {stale_pid} still alive but unresponsive after 90s. "
                        f"Use --replace to force."
                    )
                    return False
        else:
            logger.debug(f"Removing stale PID file (PID {stale_pid} not running)")

    # Check port isn't held by something else entirely
    if not _check_port_available():
        logger.error(
            f"Port {PORT} is in use by another process (not our server). "
            f"Free the port or change PORT in mod_state_server.py."
        )
        return False

    return True


# ---------------------------------------------------------------------------
# Engine docs parser
# ---------------------------------------------------------------------------
# Two possible sources for the script_docs output:
# - vanilla_snapshot_docs_path: authoritative vanilla-only snapshot, written by
#   running `script_docs` in the in-game console without the mod loaded.
# - mod_loaded_docs_path: the runtime path; whatever the user last wrote there
#   (could be vanilla- OR mod-loaded depending on context).
# We prefer the vanilla snapshot when available so we can confidently tag every
# parsed entry's origin. If the snapshot is missing we fall back to runtime and
# tag entries `unknown` (we re-tag mod-source-derived entries below in any case).
ENGINE_DOCS_DIR = vanilla_docs_path  # legacy default; superseded by _engine_docs_source()


def _has_engine_logs(path: Optional[str]) -> bool:
    return bool(
        path
        and os.path.isdir(path)
        and any(
            os.path.isfile(os.path.join(path, f))
            for f in ("modifiers.log", "effects.log", "triggers.log")
        )
    )


_USAGE_TARGET_RE_CACHE: dict[str, re.Pattern] = {}


def _engine_docs_find_usage(
    target: str,
    *,
    limit: int = 5,
    include_defs: bool = False,
    context_before: int = 1,
    context_after: int = 3,
) -> dict:
    """Scan vanilla `common/` for real-world call sites of `target` (a trigger,
    effect, or modifier name). Returns context-bracketed snippets with file:line.

    Default filter excludes column-0 `target = {` (definition) and matches inside
    `common/trigger_localization/` (engine-side display-label cross-references,
    not script calls). Set `include_defs=true` to disable filtering.

    Backend: ripgrep when available (fast, ~1-2s across vanilla); Python
    `os.walk` otherwise. Either way the result is capped at `limit`.
    """
    if not target or not re.match(r"^[a-z][a-z0-9_]*$", target):
        return {
            "name": target,
            "error": "Invalid target name (expected snake_case identifier).",
            "uses": [],
        }

    if not os.path.isdir(_BASE_COMMON):
        return {
            "name": target,
            "error": f"Vanilla common dir not found: {_BASE_COMMON}",
            "uses": [],
        }

    # Cache the per-target regex used to filter "call-site" lines from "match
    # within a longer identifier". A call site has the identifier as a whole
    # word followed by whitespace and an operator (= < > <= >= !=) or `{`.
    pat = _USAGE_TARGET_RE_CACHE.get(target)
    if pat is None:
        pat = re.compile(
            r"(^|[^A-Za-z0-9_])" + re.escape(target) + r"\s*(=|<|>|!=|<=|>=|\{)"
        )
        _USAGE_TARGET_RE_CACHE[target] = pat

    # Prefer system grep (always available, ~5-10x faster than Python walk on
    # WSL+NTFS). Fall back to ripgrep, then Python walk.
    raw_matches: list[tuple[str, int, str]] = []  # (relpath, line_no, line)
    grep_path = shutil.which("grep")
    rg_path = shutil.which("rg")
    backend = "python"
    try:
        if grep_path or rg_path:
            if grep_path:
                cmd = [
                    grep_path, "-rn", "-w",
                    "--include=*.txt",
                    "--exclude-dir=trigger_localization",
                    target, _BASE_COMMON,
                ]
                backend = "grep"
            else:
                cmd = [
                    rg_path, "-n", "-w", "-t", "txt",
                    "--max-count", "30",
                    "--no-heading", "--no-messages",
                    target, _BASE_COMMON,
                ]
                backend = "ripgrep"
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            for raw in proc.stdout.splitlines():
                # Format: "<absolute_path>:<line_no>:<line>"
                head, _, rest = raw.partition(":")
                line_no_str, _, line = rest.partition(":")
                try:
                    line_no = int(line_no_str)
                except ValueError:
                    continue
                rel = os.path.relpath(head, _BASE_COMMON)
                raw_matches.append((rel, line_no, line))
        else:
            for root, _dirs, files in os.walk(_BASE_COMMON):
                for fname in files:
                    if not fname.endswith(".txt"):
                        continue
                    path = os.path.join(root, fname)
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            for i, line in enumerate(f, start=1):
                                if target in line:
                                    rel = os.path.relpath(path, _BASE_COMMON)
                                    raw_matches.append((rel, i, line.rstrip("\n")))
                    except OSError:
                        continue
    except subprocess.TimeoutExpired:
        return {
            "name": target,
            "error": "Timed out scanning vanilla common/. Try a more specific name.",
            "uses": [],
        }
    except Exception as e:
        return {
            "name": target,
            "error": f"Scan failed: {e}",
            "uses": [],
        }

    # Filter to call sites (not definitions or label cross-references).
    filtered: list[tuple[str, int, str]] = []
    for rel, line_no, line in raw_matches:
        if not include_defs:
            if rel.startswith("trigger_localization" + os.sep):
                # Engine-side trigger-localization cross-references — not calls.
                continue
            if line.lstrip() != line and (line.lstrip().startswith(target + " ")
                                          or line.lstrip().startswith(target + "=")):
                # Indented call site — good.
                pass
            elif line.startswith(target):
                # Column-0 line starting with the name is almost always a definition.
                # Filter unless include_defs is set.
                continue
        if not pat.search(line):
            continue
        filtered.append((rel, line_no, line))
        if len(filtered) >= limit * 4:  # surface a few extras pre-dedupe-by-file
            break

    # Diversify across files: prefer first hit per file before repeating one file.
    by_file: dict[str, list[tuple[int, str]]] = {}
    for rel, line_no, line in filtered:
        by_file.setdefault(rel, []).append((line_no, line))
    diversified: list[tuple[str, int, str]] = []
    while len(diversified) < limit and any(by_file.values()):
        for rel in list(by_file.keys()):
            if not by_file[rel]:
                continue
            line_no, line = by_file[rel].pop(0)
            diversified.append((rel, line_no, line))
            if len(diversified) >= limit:
                break

    # Read context around each chosen match.
    uses = []
    for rel, line_no, line in diversified:
        abs_path = os.path.join(_BASE_COMMON, rel)
        snippet_lines: list[str] = []
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            start = max(1, line_no - context_before)
            end = min(len(all_lines), line_no + context_after)
            for i in range(start, end + 1):
                marker = ">" if i == line_no else " "
                snippet_lines.append(f"{marker} {i:5}: {all_lines[i - 1].rstrip()}")
        except OSError:
            snippet_lines = [f"  {line_no}: {line.rstrip()}"]
        uses.append({
            "file": rel,
            "line": line_no,
            "snippet": "\n".join(snippet_lines),
        })

    return {
        "name": target,
        "total_call_sites_scanned": len(filtered),
        "returned": len(uses),
        "backend": backend,
        "uses": uses,
    }


def _engine_docs_source() -> tuple[str, str]:
    """Return (chosen_directory, source_label).

    Preference order:
      1. `vanilla_snapshot` — operator-configured `vanilla_snapshot_docs_path`
         (e.g. populated by running `script_docs` in vanilla without the mod).
      2. `digest_snapshot` — derived `vanilla_snapshot_docs_path_default` from
         the highest-version Modding-Digests checkout on disk. Used when the
         operator doesn't maintain a local snapshot (the common case post-1.13.5,
         where vanilla no longer ships engine-doc logs).
      3. `mod_loaded` — runtime fallback; may contain mod-declared entries, so
         origin tagging is `unknown` and downstream code re-tags from mod-source.
    """
    if _has_engine_logs(vanilla_snapshot_docs_path):
        return vanilla_snapshot_docs_path, "vanilla_snapshot"
    if _has_engine_logs(vanilla_snapshot_docs_path_default):
        return vanilla_snapshot_docs_path_default, "digest_snapshot"
    return mod_loaded_docs_path, "mod_loaded"


def _load_vanilla_repo_head_info() -> dict:
    """Return {sha, sha_short, date_iso, date_unix} for the HEAD commit of the
    vanilla source mirror, or {} if not a git repo / not available."""
    repo = vanilla_source_repo_path
    if not os.path.isdir(os.path.join(repo, ".git")):
        return {}
    try:
        result = subprocess.run(
            ["git", "-C", repo, "log", "-1", "--format=%H %ct %ai"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        parts = result.stdout.strip().split(maxsplit=2)
        if len(parts) >= 3:
            sha, ct, ai = parts
            return {
                "sha": sha,
                "sha_short": sha[:8],
                "date_unix": int(ct),
                "date_iso": ai,
            }
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        logger.warning(f"Failed to read vanilla repo HEAD: {e}")
    return {}

def _parse_effects_triggers_log(filepath: str) -> list[dict]:
    """Parse effects.log / triggers.log format:
    ## name
    description prose lines...
    name = usage_example                # code-like, opens with the entry name
    Traits: <, <=, =, !=, >, >=         # value-comparison operators (optional)
    Reads gamestate for all scopes.     # gamestate-read note (optional)
    **Supported Scopes**: scope1, scope2
    **Supported Targets**: target1, target2

    Returns dicts with: name, description (prose only), example, traits, reads,
    scopes, targets.
    """
    entries = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Failed to read engine doc {filepath}: {e}")
        return entries

    current = None
    for line in lines:
        line = line.rstrip("\n").rstrip()  # engine docs end lines with "  " (md hard break)
        if line.startswith("## "):
            if current:
                current["description"] = current["description"].strip()
                entries.append(current)
            current = {
                "name": line[3:].strip(),
                "description": "",
                "example": "",
                "traits": "",
                "reads": "",
                "scopes": [],
                "targets": [],
            }
        elif current:
            if line.startswith("**Supported Scopes**:"):
                scopes_text = line.split(":", 1)[1].strip()
                current["scopes"] = [s.strip() for s in scopes_text.split(",") if s.strip()]
            elif line.startswith("**Supported Targets**:"):
                targets_text = line.split(":", 1)[1].strip()
                current["targets"] = [t.strip() for t in targets_text.split(",") if t.strip()]
            elif line.startswith("Traits:"):
                current["traits"] = line.split(":", 1)[1].strip()
            elif line.startswith("Reads gamestate") or line.startswith("Reads nothing"):
                current["reads"] = line.strip()
            elif (
                not current["example"]
                and current["name"]
                and line
                and (
                    line.startswith(current["name"] + " ")
                    or line.startswith(current["name"] + "=")
                    or line.startswith(current["name"] + ">")
                    or line.startswith(current["name"] + "<")
                    or line == current["name"]
                )
            ):
                # First code-like usage line wins. Format examples:
                #   active_lens = lens
                #   global_country_ranking > 42
                #   amendment_stance = {  (multi-line example follows in description)
                current["example"] = line.strip()
            else:
                current["description"] += line + "\n"
    if current:
        current["description"] = current["description"].strip()
        entries.append(current)
    return entries


_MODIFIER_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*:$")


def _parse_modifiers_log(filepath: str) -> list[dict]:
    """Parse modifiers.log format:
    modifier_name:
      Mask: mask_type
      Name: Display Name
      Description: ...
        (continuation lines, possibly bullet-prose, may follow at column 0)
    """
    entries = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Failed to read engine doc {filepath}: {e}")
        return entries

    current = None
    in_description = False
    for line in lines:
        stripped = line.rstrip("\n")
        if stripped.startswith("---"):
            continue

        # Modifier name = a snake_case identifier ending with ':' at column 0.
        # Any other line at column 0 (prose ending with ':' etc.) is treated as
        # continuation of the previous Description.
        if stripped and not stripped[0].isspace() and _MODIFIER_NAME_RE.match(stripped):
            if current:
                current["description"] = current["description"].rstrip()
                entries.append(current)
            current = {
                "name": stripped[:-1],
                "mask": "",
                "display_name": "",
                "description": "",
            }
            in_description = False
        elif current and stripped.startswith("  "):
            kv = stripped.strip()
            if kv.startswith("Mask:"):
                current["mask"] = kv.split(":", 1)[1].strip()
                in_description = False
            elif kv.startswith("Name:"):
                current["display_name"] = kv.split(":", 1)[1].strip()
                in_description = False
            elif kv.startswith("Description:"):
                current["description"] = kv.split(":", 1)[1].strip()
                in_description = True
            elif in_description:
                # Indented continuation (rare) — append to description.
                current["description"] += " " + kv
        elif current and in_description:
            # Unindented continuation (modifiers.log emits the long-form
            # description at column 0). Append, preserving paragraph breaks.
            if stripped.strip():
                if current["description"]:
                    current["description"] += "\n" + stripped
                else:
                    current["description"] = stripped
            else:
                current["description"] += "\n"
    if current:
        current["description"] = current["description"].rstrip()
        entries.append(current)
    return entries


def _parse_event_targets_log(filepath: str) -> list[dict]:
    """Parse event_targets.log — uses ### headers with Input/Output Scopes.
    Format:
    ### name
    description
    Input Scopes: scope1, scope2
    Output Scopes: scope1, scope2
    """
    entries = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Failed to read engine doc {filepath}: {e}")
        return entries

    current = None
    for line in lines:
        stripped = line.rstrip("\n")
        if stripped.startswith("### "):
            if current:
                current["description"] = current["description"].strip()
                entries.append(current)
            current = {
                "name": stripped[4:].strip(),
                "description": "",
                "input_scopes": [],
                "output_scopes": [],
                "requires_data": False,
            }
        elif current:
            if stripped.startswith("Input Scopes:"):
                scopes_text = stripped.split(":", 1)[1].strip()
                current["input_scopes"] = [s.strip() for s in scopes_text.split(",") if s.strip()]
                # Also expose as "scopes" for consistent filtering
                current["scopes"] = current["input_scopes"]
            elif stripped.startswith("Output Scopes:"):
                scopes_text = stripped.split(":", 1)[1].strip()
                current["output_scopes"] = [s.strip() for s in scopes_text.split(",") if s.strip()]
            elif stripped.startswith("Requires Data:"):
                current["requires_data"] = stripped.split(":", 1)[1].strip().lower() == "yes"
            elif stripped.startswith("#"):
                # New section header — ignore
                pass
            else:
                current["description"] += stripped + "\n"
    if current:
        current["description"] = current["description"].strip()
        entries.append(current)
    return entries


def _parse_on_actions_log(filepath: str) -> list[dict]:
    """Parse on_actions.log format:
    --------------------
    name:
    From Code: Yes/No
    Expected Scope: scope
    --------------------
    """
    entries = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Failed to read engine doc {filepath}: {e}")
        return entries

    current = None
    for line in lines:
        stripped = line.rstrip("\n").strip()
        if stripped.startswith("----"):
            if current:
                entries.append(current)
            current = None
            continue
        if stripped.startswith("On Action Documentation"):
            continue
        if not stripped:
            continue
        # Line ending with ':' that's not a known field = new on_action name
        if stripped.endswith(":") and not stripped.startswith("From Code") and not stripped.startswith("Expected Scope"):
            current = {"name": stripped[:-1], "from_code": False, "scopes": []}
        elif current:
            if stripped.startswith("From Code:"):
                current["from_code"] = stripped.split(":", 1)[1].strip().lower() == "yes"
            elif stripped.startswith("Expected Scope:"):
                scope = stripped.split(":", 1)[1].strip()
                current["scopes"] = [scope] if scope and scope != "none" else []
    if current:
        entries.append(current)
    return entries


def _parse_custom_localization_log(filepath: str) -> list[dict]:
    """Parse custom_localization.log format:
    --------------------
    name:
    Scope: scope
    Random Valid: yes/no
    Entries:
    entry1
    entry2
    --------------------
    """
    entries = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Failed to read engine doc {filepath}: {e}")
        return entries

    current = None
    in_entries = False
    for line in lines:
        stripped = line.rstrip("\n").strip()
        if stripped.startswith("----"):
            if current:
                entries.append(current)
            current = None
            in_entries = False
            continue
        if stripped.startswith("Custom Localization Documentation"):
            continue
        if not stripped:
            continue
        # Name line ends with ':' and isn't a field
        if (
            stripped.endswith(":")
            and not stripped.startswith("Scope")
            and not stripped.startswith("Random Valid")
            and not stripped.startswith("Entries")
            and current is None
        ):
            current = {"name": stripped[:-1], "scopes": [], "random_valid": False, "loc_entries": []}
            in_entries = False
        elif current:
            if stripped.startswith("Scope:"):
                scope = stripped.split(":", 1)[1].strip()
                current["scopes"] = [scope] if scope and scope != "none" else []
            elif stripped.startswith("Random Valid:"):
                current["random_valid"] = stripped.split(":", 1)[1].strip().lower() == "yes"
            elif stripped.startswith("Entries:"):
                in_entries = True
            elif in_entries:
                current["loc_entries"].append(stripped)
    if current:
        entries.append(current)
    return entries


_PATTERN_TOKEN_RE = re.compile(r"\{(\w+)\}")


def _group_similar_entries(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    """Group modifier entries by pattern_index (§3).

    Falls back to returning everything as ungrouped if the pattern engine
    hasn't been initialized (e.g. server is starting up).
    """
    if not pattern_index:
        return [], list(entries)

    grouped_names: set[str] = set()
    grouped_entries: list[dict] = []
    name_to_entry = {e.get("name", ""): e for e in entries}

    for pattern, members in pattern_index.items():
        member_names = sorted(members.keys())
        if not member_names:
            continue
        # Use the first concrete entry as the example for description/scope/mask
        first_value = member_names[0]
        first_name = pattern.replace(_pattern_token(pattern), first_value)
        example = name_to_entry.get(first_name) or next(iter(members.values()))
        full_member_names = []
        for v in member_names:
            full_name = pattern.replace(_pattern_token(pattern), v)
            grouped_names.add(full_name)
            full_member_names.append(full_name)
        grouped_entries.append({
            "pattern": pattern,
            "count": len(member_names),
            "members": full_member_names,
            "description": example.get("description", "") if isinstance(example, dict) else "",
            "scopes": example.get("scopes", []) if isinstance(example, dict) else [],
            "mask": example.get("mask", "") if isinstance(example, dict) else "",
        })

    ungrouped = [e for e in entries if e.get("name") not in grouped_names]
    return grouped_entries, ungrouped


def _pattern_token(pattern: str) -> str:
    m = _PATTERN_TOKEN_RE.search(pattern)
    return m.group(0) if m else "{placeholder}"


engine_docs_sources: dict = {}  # {key: filesystem path of source .log}
engine_docs_source_label: str = ""  # "vanilla_snapshot" or "mod_loaded" — which path was read
_vanilla_snapshot_contamination: list = []  # mod-only script_only modifier names found in the "vanilla" snapshot
pattern_catalog: list[dict] = []  # Loaded from common/_meta/modifier_patterns.yml
pattern_index: dict = {}          # {pattern_str: {placeholder_value: engine_doc_entry}}
discovered_patterns: list[dict] = []  # Auto-detected patterns not in catalog
modifier_to_pattern: dict = {}    # {full_modifier_name: (pattern, placeholder_value, source)}

PATTERN_CATALOG_PATH = os.path.join(mod_path, "common", "_meta", "modifier_patterns.yml")
DISCOVERY_MIN_MEMBERS = 3  # auto-discovered patterns need at least this many to register
_last_validation_report: dict | None = None  # cached /validate/engine-coverage output
# Per-load cache for annotator compute() results. Keyed by
# (annotator.name, annotator.entity_type) -> {entity_id: fields}. Populated
# lazily on first request that asks for `?annotate=`. Reset whenever the
# mod state reloads so stale PM flags (etc.) don't survive a /reload.
_annotator_compute_cache: dict[tuple[str, str], dict] = {}
# Cached tech → unlocks inverted index. Same lifecycle as
# `_annotator_compute_cache`.
_tech_unlocks_index_cache: dict[str, dict] | None = None


def _load_pattern_catalog() -> list[dict]:
    """Read common/_meta/modifier_patterns.yml. Tolerant if PyYAML missing or file absent."""
    if not os.path.isfile(PATTERN_CATALOG_PATH):
        logger.info(f"No pattern catalog at {PATTERN_CATALOG_PATH} — patterns auto-discovered only.")
        return []
    try:
        import yaml  # type: ignore
    except ImportError:
        logger.warning("PyYAML not installed; cannot load modifier_patterns.yml. "
                       "Run `pip install pyyaml` to enable the catalog.")
        return []
    try:
        with open(PATTERN_CATALOG_PATH, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load pattern catalog: {e}")
        return []
    raw = doc.get("patterns") or []
    if not isinstance(raw, list):
        logger.warning("Pattern catalog 'patterns' field is not a list; ignoring.")
        return []
    return [entry for entry in raw if isinstance(entry, dict) and entry.get("pattern")]


def _compile_pattern(pattern: str) -> tuple[str, str, str] | None:
    """Split a pattern like 'goods_output_{good}_add' into (prefix, placeholder, suffix).

    Returns None if the pattern doesn't have exactly one `{placeholder}` token.
    """
    m = _PATTERN_TOKEN_RE.search(pattern)
    if not m:
        return None
    placeholder = m.group(1)
    prefix = pattern[: m.start()]
    suffix = pattern[m.end():]
    return prefix, placeholder, suffix


def _match_pattern(name: str, prefix: str, suffix: str) -> str | None:
    """Return the captured placeholder value if `name` matches `prefix<value>suffix`, else None."""
    if not name.startswith(prefix) or not name.endswith(suffix):
        return None
    captured = name[len(prefix): len(name) - len(suffix) if suffix else None]
    if not captured:
        return None
    return captured


_BOUNDARY_RE_CACHE: dict[str, re.Pattern] = {}


def _value_in_name_re(value: str) -> re.Pattern:
    """Underscore-bounded substring match (so 'iron' doesn't fire on 'irony')."""
    if value not in _BOUNDARY_RE_CACHE:
        _BOUNDARY_RE_CACHE[value] = re.compile(rf"(?:^|_){re.escape(value)}(?:_|$)")
    return _BOUNDARY_RE_CACHE[value]


def _build_pattern_indexes(
    engine_modifiers: list[dict],
    catalog: list[dict],
    vocabularies: dict[str, list[str]],
) -> tuple[dict, dict, list[dict]]:
    """Return (pattern_index, modifier_to_pattern, discovered_patterns)."""
    name_to_entry = {m.get("name", ""): m for m in engine_modifiers if m.get("name")}
    all_names = set(name_to_entry.keys())

    p_index: dict[str, dict[str, dict]] = {}
    m_to_p: dict[str, tuple[str, str, str]] = {}
    matched: set[str] = set()

    # ------ Catalog pass ------
    for entry in catalog:
        pattern = entry["pattern"]
        compiled = _compile_pattern(pattern)
        if not compiled:
            logger.warning(f"Catalog pattern lacks {{placeholder}}: {pattern}")
            continue
        prefix, _placeholder_in_pattern, suffix = compiled
        vocab_name = entry.get("vocab") or entry.get("placeholder")
        vocab_values = set(vocabularies.get(vocab_name, []) or [])
        members: dict[str, dict] = {}
        for name in all_names:
            if name in matched:
                continue
            captured = _match_pattern(name, prefix, suffix)
            if captured is None:
                continue
            # Catalog match requires the captured value to be a known vocab member,
            # so we don't collapse unrelated modifiers under the wrong template.
            if vocab_values and captured not in vocab_values:
                continue
            members[captured] = name_to_entry[name]
            matched.add(name)
            m_to_p[name] = (pattern, captured, "catalog")
        if members:
            p_index[pattern] = members

    # ------ Discovery pass ------
    # Walk every engine modifier left over, try every (vocab_value -> placeholder)
    # substitution, group by inferred pattern. Keep patterns with ≥ DISCOVERY_MIN_MEMBERS.
    proposals: dict[str, dict[str, str]] = {}  # pattern_str -> {captured_value: full_name}
    proposal_meta: dict[str, dict] = {}  # pattern_str -> {placeholder, vocab}

    # Sort vocab values by length descending so longer matches win ('iron_mining'
    # before 'iron'), reducing accidental collapses.
    vocab_pairs: list[tuple[str, str]] = []  # (placeholder, value)
    for placeholder, values in vocabularies.items():
        for value in values or []:
            if len(value) < 3:  # skip 1-2 letter vocab values to avoid false matches
                continue
            vocab_pairs.append((placeholder, value))
    vocab_pairs.sort(key=lambda pv: -len(pv[1]))

    leftover = sorted(all_names - matched)
    for name in leftover:
        for placeholder, value in vocab_pairs:
            re_match = _value_in_name_re(value).search(name)
            if not re_match:
                continue
            # Reconstruct pattern with the placeholder substituted in
            start = re_match.start()
            end = re_match.end()
            # The regex captured boundaries; we only want to replace the value itself.
            # Find exact char span of the value within the matched range:
            actual_start = name.find(value, start)
            if actual_start == -1:
                continue
            actual_end = actual_start + len(value)
            pattern_str = name[:actual_start] + "{" + placeholder + "}" + name[actual_end:]
            proposals.setdefault(pattern_str, {})[value] = name
            proposal_meta.setdefault(pattern_str, {"placeholder": placeholder, "vocab": placeholder})
            break  # first match wins (longest value)

    discovered: list[dict] = []
    for pattern_str, members in proposals.items():
        if len(members) < DISCOVERY_MIN_MEMBERS:
            continue
        meta = proposal_meta[pattern_str]
        compiled = _compile_pattern(pattern_str)
        if not compiled:
            continue
        prefix, _ph, suffix = compiled
        existing_members = p_index.get(pattern_str, {})
        for value, full_name in members.items():
            if full_name in matched:
                continue
            existing_members[value] = name_to_entry[full_name]
            matched.add(full_name)
            m_to_p[full_name] = (pattern_str, value, "discovered")
        if existing_members:
            p_index[pattern_str] = existing_members
            discovered.append({
                "pattern": pattern_str,
                "placeholder": meta["placeholder"],
                "vocab": meta["vocab"],
                "members": list(existing_members.keys()),
            })

    return p_index, m_to_p, discovered


# ---------------------------------------------------------------------------
# §4: Mod-vs-engine coverage validation
# ---------------------------------------------------------------------------
# Suffix heuristic for detecting modifier-use keys. Keys ending with these
# suffixes that aren't in the engine modifier set are validation candidates.
# `_bool` / `_boolean` are included so missing boolean modifier type definitions
# get caught — vanilla and mod conventionally suffix booleans this way, and the
# engine silently no-ops references to undeclared booleans (the country_sr_*
# regression of 2026-04-29).
_MODIFIER_SUFFIX_RE = re.compile(r"_(add|mult|max_levels|max_level|set|bool|boolean)$")

# Container keys whose children we walk into but never count as
# effect / trigger / modifier names themselves.
_CONTAINER_KEYS = frozenset({
    "if", "else", "else_if", "while", "limit", "trigger", "immediate",
    "option", "options", "effect", "effects", "ai_chance", "weight",
    "modifier", "modifiers", "factor", "chance", "mean_time_to_happen",
    "every_action", "events", "random_events", "first_valid", "random_list",
    "switch", "calc_true_if", "any_neighboring_state", "any_scope_state",
})

# Entity types whose nested data should NOT be validated. Vocabularies
# (cultures, terrains, country_ranks, …) are heterogeneous data definitions
# that produce many false-positive matches.
_VALIDATION_SKIP_TYPES = frozenset({
    "Cultures", "Terrains", "Country Ranks", "Discrimination Traits",
    "Pop Types", "Religions", "Goods", "Buy Packages",
    "Combat Unit Experience Levels", "Mobilization Option Groups",
    "Mobilization Options",
    # Pop Needs use modifier-shaped field names (`obsession_demand_mult`,
    # `goods_demand_mult`) that are pop-need DSL keys, not country/state
    # modifier reads. Skipping avoids false positives.
    "Pop Needs",
    # Modifier-type definitions ARE the registry, so don't validate names
    # against themselves.
    "Modifier Types",
    # Script values are scalars, not modifiers — their names appear in
    # `multiplier =` and `limit = { X > 0 }` contexts and look modifier-shaped
    # only because authors suffix them with `_mult`/`_add`. Walking them as
    # modifier candidates produces only noise.
    "Script Values",
})


def _walk_dict_keys(node, path: list[str]):
    """Yield (key, path_to_key, value) for every dict key in a parsed AST.

    `path` is a stack of containing entity ids / field names for diagnostics.
    Tuples like ('=', {...}) and lists of dicts are flattened transparently.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            yield key, path, value
            new_path = path + [str(key)]
            yield from _walk_dict_keys(value, new_path)
    elif isinstance(node, tuple):
        # Paradox parser uses ('=', value) tuples; recurse into the value.
        for item in node:
            yield from _walk_dict_keys(item, path)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_dict_keys(item, path)


def _classify_modifier_name(name: str, modifiers_set: set, pattern_pairs: list) -> tuple[str, dict]:
    """Return (status, info) for a candidate modifier name.

    status: 'engine' | 'pattern' | 'suspicious' | 'unknown'
    info: extra details for the validation report.
    """
    if name in modifiers_set:
        return "engine", {}
    pat = modifier_to_pattern.get(name)
    if pat:
        return "pattern", {"pattern": pat[0], "value": pat[1], "source": pat[2]}
    # Try every catalog pattern. A mod-only modifier (not in engine_docs) is
    # still valid if it structurally matches a catalog pattern AND its captured
    # placeholder value is a member of the corresponding vocabulary.
    suspicious_match: dict | None = None
    for pattern_str, prefix, suffix, vocab_values, placeholder in pattern_pairs:
        captured = _match_pattern(name, prefix, suffix)
        if captured is None:
            continue
        if not vocab_values or captured in vocab_values:
            return "pattern", {
                "pattern": pattern_str,
                "value": captured,
                "source": "catalog_runtime",
            }
        # Pattern shape matches but the captured value isn't in the vocab.
        # Hold the first such match as a fallback if no full match is found.
        if suspicious_match is None:
            suspicious_match = {
                "pattern": pattern_str,
                "captured_value": captured,
                "placeholder": placeholder,
                "vocab_did_you_mean": _did_you_mean(captured, vocab_values),
            }
    if suspicious_match:
        return "suspicious", suspicious_match
    return "unknown", {}


def _did_you_mean(captured: str, vocab_values: set, limit: int = 3) -> list[str]:
    """Return up to `limit` vocab values closest to `captured` (substring distance heuristic)."""
    if not vocab_values:
        return []
    captured_lower = captured.lower()
    scored = []
    for v in vocab_values:
        v_lower = v.lower()
        if captured_lower == v_lower:
            score = 0
        elif captured_lower in v_lower or v_lower in captured_lower:
            score = 1
        else:
            # crude prefix overlap
            common = 0
            for a, b in zip(captured_lower, v_lower):
                if a == b:
                    common += 1
                else:
                    break
            score = max(2, len(captured_lower) - common)
        scored.append((score, v))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [v for _, v in scored[:limit]]


def _validate_engine_coverage() -> dict:
    """Walk every loaded mod entity and cross-reference modifier-shaped keys.

    Returns a JSON-shaped report with unknown / suspicious modifier lists and
    a stale_warning if the engine docs are older than the mod's most recent
    edit (which lets the user know post-snapshot additions are expected).
    """
    if not ms or not engine_docs:
        return {"error": "Mod state or engine docs not loaded"}

    # The "valid modifier name" set is the union of:
    #   (a) vanilla engine-doc modifiers (modifiers.log)
    #   (b) modifier-type definitions registered by the mod (or vanilla) under
    #       common/modifier_type_definitions/. Without (b) every dynamic-pattern
    #       registration and every custom mod modifier looks "unknown" even
    #       though the engine accepts it.
    modifiers_set = {e.get("name", "") for e in engine_docs.get("modifiers", [])}
    mod_types = ms.get_data("Modifier Types") or {}
    modifiers_set.update(mod_types.keys())

    # Script values are scalars referenced by name in `multiplier = X` and
    # `limit = { X > 0 }`. They look modifier-shaped (`_mult`, `_add` suffixes)
    # but they're not modifiers — they're computed scalars. Suppress them so
    # the report doesn't drown in false positives like `migration_crowding_mult`
    # being read as a modifier when it's really a script value scaling the
    # `migration_crowding` modifier via `multiplier =`.
    script_values = ms.get_data("Script Values") or {}
    script_values_set = set(script_values.keys())

    # Pre-compile catalog patterns for the suspicious-match check.
    catalog_pairs = []
    vocabularies = _vocabulary_index()
    for entry in pattern_catalog:
        compiled = _compile_pattern(entry["pattern"])
        if not compiled:
            continue
        prefix, _ph, suffix = compiled
        vocab_name = entry.get("vocab") or entry.get("placeholder")
        catalog_pairs.append(
            (entry["pattern"], prefix, suffix,
             set(vocabularies.get(vocab_name, []) or []),
             entry.get("placeholder", vocab_name))
        )

    unknown_modifiers: dict[str, dict] = {}
    suspicious_modifiers: dict[str, dict] = {}

    for etype, parser in ms.mod_parsers.items():
        if etype in _VALIDATION_SKIP_TYPES:
            continue
        if etype in VOCABULARY_TYPES.values():
            # Already covered by the explicit skip list above, but be defensive.
            continue
        data = parser.data
        if not data:
            continue
        for entity_id, entity_data in data.items():
            for key, path, value in _walk_dict_keys(entity_data, [entity_id]):
                if not isinstance(key, str):
                    continue
                if key in _CONTAINER_KEYS:
                    continue
                # Scope accessors (`var:KEY`, `c:TAG`, `s:STATE_X`, `scope:saved`,
                # `cu:culture`, `je:foo`, …) are not modifier names. The one
                # exception: `modifier:NAME` triggers (used in JE possible /
                # scripted_triggers / etc.) read a country/state modifier by
                # name, so the suffix after `modifier:` IS a modifier name and
                # should be validated. Caught here so the country_sr_* regression
                # would be flagged in either the PM or the JE possible-clause path.
                if ":" in key:
                    if key.startswith("modifier:"):
                        bool_name = key[len("modifier:"):]
                        if bool_name and not any(c in bool_name for c in ":${}/") \
                                and bool_name not in script_values_set:
                            tstatus, tinfo = _classify_modifier_name(
                                bool_name, modifiers_set, catalog_pairs)
                            if tstatus not in ("engine", "pattern"):
                                used_in = (
                                    f"{etype}/{entity_id} → "
                                    + " → ".join(str(p) for p in path)
                                    + f" → modifier:{bool_name}"
                                )
                                bucket = (unknown_modifiers
                                          if tstatus == "unknown"
                                          else suspicious_modifiers)
                                if bool_name not in bucket:
                                    bucket[bool_name] = {
                                        "name": bool_name, "used_in": [], **tinfo,
                                    }
                                bucket[bool_name]["used_in"].append(used_in)
                    continue
                # Only flag keys that LOOK like modifier names: ends in _add/_mult/_max/_set
                if not _MODIFIER_SUFFIX_RE.search(key):
                    continue
                # Filter out keys whose value is itself a block (those are usually
                # not modifier *uses* but rather definitions of new modifier types).
                actual_val = value[1] if isinstance(value, tuple) and len(value) >= 2 else value
                if isinstance(actual_val, (dict, list)):
                    # A `modifier = { foo_add = 1 }` block would land at this dict;
                    # skip the outer key, but recursion will catch the inner one.
                    continue
                # Suppress names that are defined as script values — they're
                # scalars referenced in `multiplier =` / `limit = { X > 0 }`,
                # not modifier names.
                if key in script_values_set:
                    continue
                status, info = _classify_modifier_name(key, modifiers_set, catalog_pairs)
                if status in ("engine", "pattern"):
                    continue
                used_in = f"{etype}/{entity_id} → " + " → ".join(str(p) for p in path)
                bucket = unknown_modifiers if status == "unknown" else suspicious_modifiers
                if key not in bucket:
                    bucket[key] = {"name": key, "used_in": [], **info}
                bucket[key]["used_in"].append(used_in)

    # Compute mod recency vs engine doc mtime for the stale_warning
    engine_mtimes = {
        k: _safe_mtime(p) for k, p in engine_docs_sources.items()
    }
    most_recent_engine = max((m for m in engine_mtimes.values() if m), default=None)
    most_recent_mod = _scan_mod_mtime()
    stale_warning = ""
    if most_recent_engine and most_recent_mod and most_recent_mod > most_recent_engine:
        delta_days = int((most_recent_mod - most_recent_engine) // 86400)
        stale_warning = (
            f"Engine docs are {delta_days} days older than the most recent mod edit; "
            "some unknowns may be entries added after the last in-game regeneration."
        )

    return {
        "engine_docs_timestamps": {
            k: datetime.fromtimestamp(m, tz=timezone.utc).isoformat(timespec="seconds")
            for k, m in engine_mtimes.items() if m
        },
        "mod_last_modified": (
            datetime.fromtimestamp(most_recent_mod, tz=timezone.utc).isoformat(timespec="seconds")
            if most_recent_mod else None
        ),
        "stale_warning": stale_warning,
        "summary": {
            "unknown_modifiers": len(unknown_modifiers),
            "suspicious_modifiers": len(suspicious_modifiers),
        },
        "unknown_modifiers": sorted(unknown_modifiers.values(), key=lambda x: x["name"]),
        "suspicious_modifiers": sorted(suspicious_modifiers.values(), key=lambda x: x["name"]),
    }


def _annotate_validation_with_error_log(report: dict) -> None:
    """Cross-reference unknown / suspicious modifier names with the latest error.log
    so the user can see *which engine error line* confirmed the issue.
    """
    try:
        from game_log_reader import list_logs, parse_log
    except Exception:
        return
    infos = list_logs(game_logs_path)
    error_log = next((i for i in infos if i.family == "error" and i.generation == 0), None)
    if error_log is None:
        return
    entries = parse_log(error_log.path)
    # Index error-log lines by mentioned identifiers (anything that looks like a
    # snake_case name). Cheap heuristic — substring check on each unknown name.
    error_lines: list[tuple[str, str]] = [
        (e.time, e.message) for e in entries if e.message
    ]
    for bucket in ("unknown_modifiers", "suspicious_modifiers"):
        for entry in report.get(bucket, []):
            name = entry.get("name", "")
            if not name:
                continue
            for time, message in error_lines:
                if name in message:
                    entry.setdefault("confirmed_by_engine_log", []).append(
                        f"{error_log.label} [{time}] {message[:200]}"
                    )
                    break  # one is enough — we just want to confirm the issue exists at runtime


def _safe_mtime(path: str | None) -> float | None:
    if not path:
        return None
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def _scan_mod_mtime() -> float | None:
    """Walk the mod's `common/` and `events/` dirs once and return the latest mtime."""
    latest = 0.0
    for top in ("common", "events"):
        d = os.path.join(mod_path, top)
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for fname in files:
                if not fname.endswith(".txt"):
                    continue
                try:
                    m = os.path.getmtime(os.path.join(root, fname))
                except OSError:
                    continue
                if m > latest:
                    latest = m
    return latest or None


# ---------------------------------------------------------------------------
# Duplicate-image detection
# ---------------------------------------------------------------------------
# Entity types where vanilla holds the convention "one image per entity" — any
# image reuse inside the mod (or between mod and vanilla) is a likely placeholder
# that was never replaced. Each entry: (entity_type, field_name).
#
# Permissive types (events, journal entries, production methods, ideologies,
# combat units) are deliberately omitted — vanilla shares images across many
# entities of those types by design. They simply aren't scanned.
_IMAGE_FIELDS_BY_TYPE: list[tuple[str, str]] = [
    ("Buildings",       "icon"),
    ("Goods",           "texture"),
    ("Decrees",         "texture"),
    ("Technologies",    "texture"),
    ("Interest Groups", "texture"),
    ("Laws",            "icon"),
]

# YAML file → canonical entity-type-name mapping. The YAML is keyed by lowercase
# slug for ergonomic editing; the in-memory map uses the canonical names.
_ALLOWLIST_TYPE_SLUGS: dict[str, str] = {
    "buildings":       "Buildings",
    "goods":           "Goods",
    "decrees":         "Decrees",
    "technologies":    "Technologies",
    "interest_groups": "Interest Groups",
    "laws":            "Laws",
}

_IMAGE_ALLOWLIST_PATH = os.path.join(
    mod_path, "common", "_meta", "duplicate_image_allowlist.yml"
)


def _load_image_allowlist(path: str | None = None) -> dict:
    """Load the duplicate-image allowlist YAML.

    Each entry may use either form:
      - image: gfx/foo.dds        # singular, for path-only dupes
        entities: [a, b]
        reason: ...
      - images: [gfx/x, gfx/y]    # plural, for content-identical dupes
        entities: [a, b]
        reason: ...

    Returns: {canonical_entity_type: {(frozenset(images), frozenset(entity_ids)): reason}}.
    Returns {} if the file doesn't exist or is empty (allowlist is optional).
    """
    target = path or _IMAGE_ALLOWLIST_PATH
    if not os.path.isfile(target):
        return {}
    try:
        import yaml
        with open(target, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"WARNING: failed to load image allowlist {target}: {e}")
        return {}

    out: dict = {}
    if not isinstance(raw, dict):
        return out
    for slug, entries in raw.items():
        canonical = _ALLOWLIST_TYPE_SLUGS.get(str(slug).lower())
        if not canonical or not isinstance(entries, list):
            continue
        bucket = out.setdefault(canonical, {})
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            # Accept either `image:` (singular string) or `images:` (list).
            images_field = entry.get("images")
            if images_field is None:
                single = entry.get("image")
                images_field = [single] if single else []
            if not isinstance(images_field, list) or not images_field:
                continue
            entities = entry.get("entities") or []
            reason = entry.get("reason", "")
            if not isinstance(entities, list) or len(entities) < 2:
                continue
            images_key = frozenset(str(p) for p in images_field if p)
            entities_key = frozenset(str(e) for e in entities)
            if not images_key or not entities_key:
                continue
            bucket[(images_key, entities_key)] = str(reason)
    return out


def _resolve_image_path(rel_path: str) -> str | None:
    """Resolve a Paradox-relative image path (`gfx/...`) to an absolute file path.

    Mod overlay first (so a mod-shipped icon wins over a vanilla one of the
    same name), vanilla fallback. Returns None if neither location has the file.
    """
    if not rel_path:
        return None
    candidates = (
        os.path.join(mod_path, rel_path),
        os.path.join(base_game_path, "game", rel_path),
    )
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _image_content_hash(rel_path: str) -> str:
    """Return a stable identity for an image path's actual on-disk content.

    Returns 'md5:<hex>' when the file exists. If neither mod nor vanilla has
    the file (missing-asset case, caught elsewhere by the debug.log digest),
    returns 'path:<rel_path>' so two missing distinct paths still cluster
    independently — i.e. the detector falls back to path identity for missing
    files rather than crashing.
    """
    abs_path = _resolve_image_path(rel_path)
    if abs_path is None:
        return f"path:{rel_path}"
    try:
        import hashlib
        h = hashlib.md5()
        with open(abs_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return f"md5:{h.hexdigest()}"
    except OSError:
        return f"path:{rel_path}"


def _collect_image_uses(entity_type: str, field: str, *,
                        include_vanilla: bool) -> tuple[dict[str, list[str]], set[str]]:
    """Return (image_path → [entity_id, …], set_of_mod_only_ids) for one type."""
    if not ms or entity_type not in ms.mod_parsers:
        return {}, set()
    full = ms.mod_parsers[entity_type].data or {}
    base = (ms.base_parsers[entity_type].data
            if entity_type in ms.base_parsers else {}) or {}
    mod_only_ids = set(full.keys()) - set(base.keys())
    uses: dict[str, list[str]] = {}
    for entity_id, raw in full.items():
        data = get_entity_data(raw)
        if not isinstance(data, dict):
            continue
        image = get_field(data, field)
        if not isinstance(image, str) or not image:
            continue
        # Strip surrounding quotes preserved by the parser so the path matches
        # naturally against unquoted entries in the YAML allowlist.
        if len(image) >= 2 and image[0] == image[-1] and image[0] in ('"', "'"):
            image = image[1:-1]
        if image:
            uses.setdefault(image, []).append(entity_id)
    return uses, mod_only_ids


def _find_duplicate_images(*, include_vanilla: bool = False,
                           types: list[str] | None = None,
                           allowlist: dict | None = None,
                           include_allowlisted: bool = False,
                           hasher=None) -> dict:
    """Build the duplicate-image report.

    Groups entities by content-hash (md5 of the resolved file), so two entities
    that point at different filenames but byte-identical .dds files still get
    flagged as a duplicate cluster — the case path-only matching misses.

    Parameters:
      include_vanilla     — include clusters with no mod-side entities.
      types               — restrict scan to these canonical entity-type names.
      allowlist           — pre-built allowlist dict (else loaded from the YAML).
      include_allowlisted — emit the `allowlisted` array in the response.
      hasher              — callable(rel_path) → hash string. Defaults to
                            `_image_content_hash`. Tests inject a fake hasher
                            so they don't need real .dds files on disk.

    Cluster shape:
      {"entity_type": str,
       "images":      [sorted paths, len 1 if pure path-dupe else >1],
       "entities":    [sorted entity ids],
       "kind":        "path" | "content",
       "reason":      <only present for allowlisted clusters>}
    """
    if allowlist is None:
        allowlist = _load_image_allowlist()
    if hasher is None:
        hasher = _image_content_hash

    scanned_types: list[str] = []
    flagged: list[dict] = []
    allowlisted: list[dict] = []

    for entity_type, field in _IMAGE_FIELDS_BY_TYPE:
        if types is not None and entity_type not in types:
            continue
        scanned_types.append(entity_type)
        path_to_entities, mod_only_ids = _collect_image_uses(
            entity_type, field, include_vanilla=include_vanilla
        )
        # Hash each unique path once.
        path_to_hash = {p: hasher(p) for p in path_to_entities}

        # Group entities by content hash.
        hash_to_paths: dict[str, set[str]] = {}
        hash_to_entities: dict[str, list[str]] = {}
        for path, ents in path_to_entities.items():
            h = path_to_hash[path]
            hash_to_paths.setdefault(h, set()).add(path)
            hash_to_entities.setdefault(h, []).extend(ents)

        type_allowlist = allowlist.get(entity_type, {})
        for h, ents in hash_to_entities.items():
            if len(ents) < 2:
                continue
            if not include_vanilla and not (set(ents) & mod_only_ids):
                continue
            paths = hash_to_paths[h]
            kind = "content" if len(paths) > 1 else "path"
            cluster = {
                "entity_type": entity_type,
                "images": sorted(paths),
                "entities": sorted(set(ents)),
                "kind": kind,
            }
            allow_key = (frozenset(paths), frozenset(ents))
            if allow_key in type_allowlist:
                cluster["reason"] = type_allowlist[allow_key]
                allowlisted.append(cluster)
            else:
                flagged.append(cluster)

    flagged.sort(key=lambda c: (c["entity_type"], c["images"]))
    allowlisted.sort(key=lambda c: (c["entity_type"], c["images"]))

    report: dict = {
        "summary": {
            "flagged": len(flagged),
            "allowlisted": len(allowlisted),
            "scanned_entity_types": scanned_types,
        },
        "flagged": flagged,
    }
    if include_allowlisted:
        report["allowlisted"] = allowlisted
    return report


def _render_duplicate_images_text(report: dict, *, include_allowlisted: bool = False) -> str:
    """Render the duplicate-image report as plain text for ?format=text."""
    summary = report.get("summary", {})
    out = [
        f"Duplicate images: {summary.get('flagged', 0)} flagged, "
        f"{summary.get('allowlisted', 0)} allowlisted",
        f"Scanned types: {', '.join(summary.get('scanned_entity_types', []))}",
        "",
    ]

    def _format_cluster(c: dict) -> list[str]:
        kind_tag = "CONTENT" if c.get("kind") == "content" else "PATH"
        lines = [f"  [{c['entity_type']}] [{kind_tag}]"]
        for p in c["images"]:
            lines.append(f"    image: {p}")
        for eid in c["entities"]:
            lines.append(f"      - {eid}")
        return lines

    flagged = report.get("flagged", [])
    if flagged:
        out.append(f"FLAGGED ({len(flagged)}):")
        for c in flagged:
            out.extend(_format_cluster(c))
    else:
        out.append("FLAGGED: none")
    if include_allowlisted and report.get("allowlisted"):
        out.append("")
        out.append(f"ALLOWLISTED ({len(report['allowlisted'])}):")
        for c in report["allowlisted"]:
            reason = c.get("reason") or "(no reason given)"
            out.extend(_format_cluster(c))
            out.append(f"      reason: {reason}")
    return "\n".join(out) + "\n"


def _render_engine_coverage_md(report: dict) -> str:
    """Render the JSON validation report as Markdown for docs/."""
    out = []
    out.append("<!-- Auto-generated by /validate/engine-coverage. Do not hand-edit. -->")
    out.append("")
    out.append("# Engine Coverage Report")
    out.append("")
    if report.get("stale_warning"):
        out.append(f"> ⚠️ {report['stale_warning']}")
        out.append("")
    timestamps = report.get("engine_docs_timestamps") or {}
    if timestamps:
        out.append("## Engine doc snapshot timestamps")
        out.append("")
        for k in sorted(timestamps):
            out.append(f"- `{k}`: {timestamps[k]}")
        out.append("")
    if report.get("mod_last_modified"):
        out.append(f"Most recent mod file mtime: {report['mod_last_modified']}")
        out.append("")
    summary = report.get("summary") or {}
    out.append("## Summary")
    out.append("")
    out.append(f"- Unknown modifiers: **{summary.get('unknown_modifiers', 0)}**")
    out.append(f"- Suspicious modifiers (pattern matched, value not in vocab): "
               f"**{summary.get('suspicious_modifiers', 0)}**")
    out.append("")
    if report.get("suspicious_modifiers"):
        out.append("## Suspicious modifiers")
        out.append("")
        out.append("Pattern matched, but the captured placeholder value is not in the "
                   "corresponding vocabulary — likely a typo.")
        out.append("")
        for entry in report["suspicious_modifiers"]:
            line = f"- `{entry['name']}` — pattern `{entry.get('pattern', '?')}`, captured `{entry.get('captured_value', '?')}`"
            dym = entry.get("vocab_did_you_mean") or []
            if dym:
                line += f" — did you mean: {', '.join(f'`{d}`' for d in dym)}?"
            out.append(line)
            for u in entry.get("used_in", [])[:5]:
                out.append(f"  - {u}")
        out.append("")
    if report.get("unknown_modifiers"):
        out.append("## Unknown modifiers")
        out.append("")
        out.append("Modifier-shaped names (ending in `_add`/`_mult`/`_max`/`_set`) used in mod "
                   "data but absent from both the engine modifier registry and the pattern "
                   "catalog. May indicate typos OR modifiers added after the engine-doc "
                   "snapshot was taken — regenerate the engine docs in-game and `POST /reload` "
                   "to refresh.")
        out.append("")
        for entry in report["unknown_modifiers"]:
            out.append(f"- `{entry['name']}`")
            for u in entry.get("used_in", [])[:5]:
                out.append(f"  - {u}")
        out.append("")
    return "\n".join(out) + "\n"


def _reload_engine_only():
    """§5: re-read engine logs + regenerate reference docs WITHOUT reparsing the
    mod (skips the slow ModState rebuild). Use after the engine regenerates the
    .log files in-game when no mod files have changed.
    """
    global _last_validation_report
    logger.info("Engine-only reload: re-reading engine logs + regenerating reference docs.")
    _load_engine_docs()
    # Re-run the validation pass against the existing mod state.
    try:
        _last_validation_report = _validate_engine_coverage()
        report_md = _render_engine_coverage_md(_last_validation_report)
        with open(os.path.join(doc_path, "engine", "engine_coverage_report.md"), "w", encoding="utf-8") as f:
            f.write(report_md)
        summary = _last_validation_report.get("summary", {})
        logger.info(
            f"Engine coverage after engine-only reload: "
            f"{summary.get('unknown_modifiers', 0)} unknown, "
            f"{summary.get('suspicious_modifiers', 0)} suspicious."
        )
    except Exception as e:
        logger.error(f"Failed to re-run validation: {e}\n{traceback.format_exc()}")


def _refresh_pattern_state():
    """Rebuild pattern_catalog / index / discovered after engine docs reload."""
    global pattern_catalog, pattern_index, discovered_patterns, modifier_to_pattern
    pattern_catalog = _load_pattern_catalog()
    modifiers = engine_docs.get("modifiers") or []
    vocabs = _vocabulary_index() if ms else {}
    pattern_index, modifier_to_pattern, discovered_patterns = _build_pattern_indexes(
        modifiers, pattern_catalog, vocabs
    )
    catalog_patterns = sum(1 for v in modifier_to_pattern.values() if v[2] == "catalog")
    discovered_count = sum(1 for v in modifier_to_pattern.values() if v[2] == "discovered")
    logger.info(
        f"Pattern catalog: {len(pattern_catalog)} declared, {catalog_patterns} engine modifiers matched; "
        f"discovery: {len(discovered_patterns)} new patterns covering {discovered_count} more modifiers."
    )


def _build_pattern_data():
    """Return (catalog, index, discovered, vocabularies) for the doc renderer."""
    vocabs = _vocabulary_index() if ms else {}
    return pattern_catalog, pattern_index, discovered_patterns, vocabs


def _infer_modifier_mask(name: str) -> str:
    """Infer the modifier mask from the name prefix. Mirrors vanilla naming
    conventions; defaults to 'country' since most mod-declared modifiers are
    country-scoped."""
    for prefix, mask in (
        ("state_building_", "state-building"),
        ("building_group_", "building-group"),
        ("building_", "building"),
        ("character_", "character"),
        ("country_", "country"),
        ("interest_group_", "interest-group"),
        ("political_movement_", "political-movement"),
        ("power_bloc_", "power-bloc"),
        ("ship_", "ship"),
        ("state_", "state"),
        ("unit_", "unit"),
        ("battle_condition_", "battle-condition"),
        ("goods_input_", "goods-input"),
        ("goods_output_", "goods-output"),
        ("party_", "party"),
        ("religion_", "religion"),
    ):
        if name.startswith(prefix):
            return mask
    return "country"


def _find_modifier_definition_file(name: str) -> str | None:
    """Best-effort scan of common/modifier_type_definitions/ to find which file
    defines a given modifier-type key. Returns repo-relative path or None."""
    dir_path = mod_paths.get("Modifier Types")
    if not dir_path or not os.path.isdir(dir_path):
        return None
    needle = re.compile(rf"^{re.escape(name)}\s*=\s*\{{", re.MULTILINE)
    for fname in sorted(os.listdir(dir_path)):
        if not fname.endswith(".txt"):
            continue
        full = os.path.join(dir_path, fname)
        try:
            with open(full, "r", encoding="utf-8-sig", errors="replace") as f:
                if needle.search(f.read()):
                    return os.path.relpath(full, mod_path)
        except OSError:
            continue
    return None


def _union_vanilla_modifier_decimals(engine_docs: dict) -> None:
    """Annotate vanilla modifier entries with `decimals` and `percent` fields.

    The engine snapshot (modifiers.log) carries name/mask/display_name/description
    only — the `decimals = N` / `percent = yes` declarations live in the source
    files at <base_game_path>/game/common/modifier_type_definitions/. This pass
    parses those files and patches the existing engine_docs['modifiers'] entries
    so downstream tools (the visibility audit in particular) can compute display
    rounding without re-reading the vanilla files themselves.

    Runs BEFORE _union_mod_modifier_types so mod-side cosmetic redeclarations
    (which may set a different `decimals`) win.
    """
    vanilla_dir = os.path.join(base_game_path, "game", "common", "modifier_type_definitions")
    if not os.path.isdir(vanilla_dir):
        logger.warning(f"Vanilla modifier_type_definitions directory not found: {vanilla_dir}")
        return

    by_name = {e.get("name"): i for i, e in enumerate(engine_docs.get("modifiers", []))}
    annotated = 0

    for fname in sorted(os.listdir(vanilla_dir)):
        if not fname.endswith(".txt"):
            continue
        full = os.path.join(vanilla_dir, fname)
        try:
            local = ParadoxFileParser()
            local.parse_file(full, apply_directives=False)
        except Exception as e:
            logger.warning(f"Failed to parse vanilla {fname}: {e}")
            continue
        for name, raw in local.data.items():
            data = _flatten_entity_data(raw)

            def _unwrap(v):
                return v[1] if isinstance(v, tuple) and len(v) >= 2 else v

            decimals = _try_int(_unwrap(data.get("decimals")))
            percent = _try_bool_yes(_unwrap(data.get("percent")))
            if decimals is None and percent is None:
                continue
            idx = by_name.get(name)
            if idx is None:
                continue
            entry = engine_docs["modifiers"][idx]
            if decimals is not None:
                entry["decimals"] = decimals
            if percent is not None:
                entry["percent"] = percent
            annotated += 1

    logger.info(f"Vanilla modifier-type decimals/percent: {annotated} entries annotated")


def _union_mod_modifier_types(engine_docs: dict) -> None:
    """Walk the mod-only `Modifier Types` declarations and union them into
    engine_docs['modifiers'] with origin='mod'. Mod entries shadow vanilla
    entries on duplicate names (intentional mod redeclaration for cosmetics).

    Vanilla also has modifier_type_definitions, so we diff mod_parsers against
    base_parsers to isolate mod-only declarations — otherwise we'd flag every
    vanilla-defined modifier as `origin: mod`."""
    global _vanilla_snapshot_contamination
    _vanilla_snapshot_contamination = []
    if not ms:
        return
    mod_data = ms.mod_parsers.get("Modifier Types")
    base_data = ms.base_parsers.get("Modifier Types")
    if mod_data is None:
        return
    base_keys = set(base_data.data.keys()) if base_data is not None else set()
    mod_types = {
        k: v for k, v in mod_data.data.items() if k not in base_keys
    }
    if not mod_types:
        return

    # Index existing entries by name for O(1) lookup
    by_name = {e.get("name"): i for i, e in enumerate(engine_docs.get("modifiers", []))}

    def _unwrap(v):
        """Pull the value out of a ('=', X) tuple; pass-through otherwise."""
        if isinstance(v, tuple) and len(v) >= 2:
            return v[1]
        return v

    new_count = 0
    redeclare_count = 0
    for name, raw in mod_types.items():
        data = _flatten_entity_data(raw)
        is_script_only = str(_unwrap(data.get("script_only", ""))).lower() == "yes"
        is_boolean = str(_unwrap(data.get("boolean", ""))).lower() == "yes"
        decimals = _try_int(_unwrap(data.get("decimals")))
        percent = _try_bool_yes(_unwrap(data.get("percent")))
        defined_in = _find_modifier_definition_file(name)

        if name in by_name:
            # The modifier IS in the vanilla snapshot — engine recognizes it
            # natively. The mod's declaration is cosmetic (color, percent,
            # decimals, optionally script_only). Annotate the existing entry
            # rather than replacing it so origin stays "vanilla".
            existing = engine_docs["modifiers"][by_name[name]]
            existing["mod_redeclares"] = True
            existing["mod_redeclared_in"] = defined_in
            # Mod overrides vanilla decimals/percent when explicitly set
            # (e.g. mod sets `decimals = 2` to make sub-1% prestige visible).
            if decimals is not None:
                existing["decimals"] = decimals
            if percent is not None:
                existing["percent"] = percent
            if is_script_only:
                existing["mod_script_only"] = True
                # Contamination signal: a script_only modifier in the "vanilla"
                # snapshot means the snapshot was actually mod-loaded. Track for
                # surfacing in /status.
                _vanilla_snapshot_contamination.append(name)
            redeclare_count += 1
        else:
            # Mod-only declaration — name not in the vanilla snapshot.
            display_name = ms.localize(name) if ms else None
            if display_name == name:
                display_name = None
            entry = {
                "name": name,
                "mask": _infer_modifier_mask(name),
                "display_name": display_name or "",
                "description": "",
                "origin": "mod",
                "is_script_only": is_script_only,
                "is_boolean": is_boolean,
                "defined_in": defined_in,
            }
            if decimals is not None:
                entry["decimals"] = decimals
            if percent is not None:
                entry["percent"] = percent
            engine_docs["modifiers"].append(entry)
            new_count += 1

    logger.info(
        f"Mod modifier-type union: {new_count} mod-only declarations added; "
        f"{redeclare_count} cosmetic redeclarations of vanilla modifiers annotated"
    )


def _union_mod_custom_localization(engine_docs: dict) -> None:
    """Walk common/customizable_localization/ and union entries into
    engine_docs['custom-localization'] with origin='mod'. Skip if the directory
    is empty or absent (mod doesn't define any). MVP: parses by entity-key
    only — display names / scopes come from the engine snapshot when present."""
    cust_dir = os.path.join(mod_path, "common", "customizable_localization")
    if not os.path.isdir(cust_dir):
        return

    by_name = {
        e.get("name"): i
        for i, e in enumerate(engine_docs.get("custom-localization", []))
    }

    new_count = 0
    redeclare_count = 0
    for fname in sorted(os.listdir(cust_dir)):
        if not fname.endswith(".txt"):
            continue
        full = os.path.join(cust_dir, fname)
        try:
            local = ParadoxFileParser()
            local.parse_file(full, apply_directives=False)
        except Exception as e:
            logger.warning(f"Failed to parse customizable_localization/{fname}: {e}")
            continue
        rel = os.path.relpath(full, mod_path)
        for name in local.data.keys():
            if name in by_name:
                existing = engine_docs["custom-localization"][by_name[name]]
                existing["mod_redeclares"] = True
                existing["mod_redeclared_in"] = rel
                redeclare_count += 1
            else:
                engine_docs["custom-localization"].append({
                    "name": name,
                    "scopes": [],
                    "random_valid": "",
                    "loc_entries": [],
                    "origin": "mod",
                    "defined_in": rel,
                })
                new_count += 1

    if new_count or redeclare_count:
        logger.info(
            f"Mod customizable_localization union: {new_count} mod-only added; "
            f"{redeclare_count} cosmetic redeclarations annotated"
        )


def _load_engine_docs():
    """Parse all engine documentation files into structured data.

    Source preference: vanilla_snapshot_docs_path (vanilla-only, authoritative)
    > mod_loaded_docs_path (runtime, may include mod declarations).
    Every entry is tagged with `origin`:
      - "vanilla" when read from the vanilla snapshot
      - "unknown" when read from the fallback runtime path (we can't tell)
      - "mod"     after the mod-source-derived union below
    """
    global engine_docs, engine_docs_sources, engine_docs_source_label
    engine_docs = {}
    engine_docs_sources = {}

    chosen_dir, source_label = _engine_docs_source()
    engine_docs_source_label = source_label
    default_origin = (
        "vanilla" if source_label in ("vanilla_snapshot", "digest_snapshot") else "unknown"
    )
    logger.info(
        f"Engine docs source: {source_label} ({chosen_dir}); default entry origin: {default_origin}"
    )

    doc_files = {
        "effects": ("effects.log", _parse_effects_triggers_log),
        "triggers": ("triggers.log", _parse_effects_triggers_log),
        "modifiers": ("modifiers.log", _parse_modifiers_log),
        "event-targets": ("event_targets.log", _parse_event_targets_log),
        "on-actions": ("on_actions.log", _parse_on_actions_log),
        "custom-localization": ("custom_localization.log", _parse_custom_localization_log),
    }

    for key, (filename, parser_fn) in doc_files.items():
        filepath = os.path.join(chosen_dir, filename)
        if os.path.isfile(filepath):
            try:
                entries = parser_fn(filepath)
                # Tag every entry with its origin. Triggers / effects / event_targets
                # / on_actions aren't moddable; modifiers / custom_localization get
                # mod-source unioning below, which may upgrade origin to "mod".
                for e in entries:
                    e.setdefault("origin", default_origin)
                engine_docs[key] = entries
                engine_docs_sources[key] = filepath
                logger.info(f"Parsed engine doc {filename}: {len(entries)} entries")
            except Exception as e:
                logger.error(f"Failed to parse engine doc {filename}: {e}")
                engine_docs[key] = []
        else:
            logger.warning(f"Engine doc not found: {filepath}")
            engine_docs[key] = []

    # Union in mod-declared modifier types. The mod state already parsed these
    # entities; we shape them like engine-doc modifier entries and tag origin=mod.
    # Names that already exist in the vanilla snapshot get their entry shadowed
    # (mod intentionally redeclares for cosmetic reasons — e.g. setting color +
    # percent on country_leverage_threshold_change_add).
    try:
        _union_vanilla_modifier_decimals(engine_docs)
        _union_mod_modifier_types(engine_docs)
        _union_mod_custom_localization(engine_docs)
    except Exception as e:
        logger.error(f"Failed to union mod-declared engine docs: {e}\n{traceback.format_exc()}")

    # Build the pattern catalog + auto-discovery indexes (§3) before rendering
    # the modifier reference, so the renderer can group dynamic patterns.
    try:
        _refresh_pattern_state()
    except Exception as e:
        logger.error(f"Failed to build pattern state: {e}\n{traceback.format_exc()}")

    # Regenerate the engine-doc reference files in docs/engine/
    try:
        from engine_docs_render import render_all as _render_engine_docs
        catalog, index, discovered, vocabs = _build_pattern_data()
        engine_docs_out = os.path.join(doc_path, "engine")
        written = _render_engine_docs(
            engine_docs,
            engine_docs_out,
            pattern_catalog=catalog,
            pattern_index=index,
            discovered_patterns=discovered,
            vocabularies=vocabs,
            source_paths=engine_docs_sources,
        )
        logger.info(f"Regenerated {len(written)} engine reference files in {engine_docs_out}")
    except Exception as e:
        logger.error(f"Failed to regenerate engine reference docs: {e}\n{traceback.format_exc()}")

    # Run §4 validation pass and write the Markdown report.
    global _last_validation_report
    try:
        _last_validation_report = _validate_engine_coverage()
        _annotate_validation_with_error_log(_last_validation_report)
        report_md = _render_engine_coverage_md(_last_validation_report)
        with open(os.path.join(doc_path, "engine", "engine_coverage_report.md"), "w", encoding="utf-8") as f:
            f.write(report_md)
        summary = _last_validation_report.get("summary", {})
        if summary.get("unknown_modifiers") or summary.get("suspicious_modifiers"):
            logger.warning(
                f"Engine coverage: "
                f"{summary.get('unknown_modifiers', 0)} unknown modifiers, "
                f"{summary.get('suspicious_modifiers', 0)} suspicious — "
                f"see /validate/engine-coverage"
            )
        else:
            logger.info("Engine coverage: clean (all modifier names recognized)")
    except Exception as e:
        logger.error(f"Failed to run engine-coverage validation: {e}\n{traceback.format_exc()}")

    # §6: write the error.log digest alongside the engine reference docs.
    try:
        from game_log_reader import render_error_log_digest
        digest = render_error_log_digest(game_logs_path, mod_path)
        with open(os.path.join(doc_path, "engine", "error_log_digest.md"), "w", encoding="utf-8") as f:
            f.write(digest)
        logger.info(f"Wrote error log digest to {doc_path}/engine/error_log_digest.md")
    except Exception as e:
        logger.error(f"Failed to render error log digest: {e}\n{traceback.format_exc()}")


def _load_dev_reference_docs():
    """Scan base game common/ directories for .md files (developer reference docs).
    Stores them keyed by directory name (e.g. 'buildings', 'production_methods').
    """
    global dev_reference_docs
    dev_reference_docs = {}
    common_dir = os.path.join(base_game_path, "game", "common")
    if not os.path.isdir(common_dir):
        logger.warning(f"Base game common dir not found: {common_dir}")
        return
    for root, dirs, files in os.walk(common_dir):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(root, fname)
            # Key = relative path from common/, e.g. "buildings/buildings.md"
            rel = os.path.relpath(fpath, common_dir).replace("\\", "/")
            # Also derive a short directory key, e.g. "buildings"
            dir_key = os.path.relpath(os.path.dirname(fpath), common_dir).replace("\\", "/")
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                dev_reference_docs[rel] = {
                    "path": rel,
                    "filename": fname,
                    "directory": dir_key,
                    "content": content,
                    "size": len(content),
                }
            except Exception as e:
                logger.error(f"Failed to read dev reference doc {fpath}: {e}")
    logger.info(f"Loaded {len(dev_reference_docs)} developer reference docs from base game")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def serialize(obj):
    """Convert parsed Paradox data (which uses tuples) to JSON-serializable form."""
    if isinstance(obj, tuple):
        return [serialize(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize(item) for item in obj]
    return obj


def get_entity_data(entity_tuple):
    """Extract the inner data dict from a ('=', {...}) entity tuple."""
    if isinstance(entity_tuple, tuple) and len(entity_tuple) >= 2:
        data = entity_tuple[1]
    else:
        data = entity_tuple
    if isinstance(data, list):
        flat = {}
        for item in data:
            if isinstance(item, dict):
                flat.update(item)
        return flat
    return data


def get_field(data, key, default=None):
    """Get a scalar/list value from entity data, unwrapping ('=', value) tuples."""
    val = data.get(key) if isinstance(data, dict) else None
    if val is None:
        return default
    if isinstance(val, tuple) and len(val) >= 2:
        return val[1]
    return val


def _data_contains_string(obj, needle):
    """Recursively check if *needle* appears as a string value anywhere in the data tree."""
    if isinstance(obj, str):
        return needle == obj
    if isinstance(obj, (int, float, bool)) or obj is None:
        return False
    if isinstance(obj, tuple):
        return any(_data_contains_string(item, needle) for item in obj)
    if isinstance(obj, list):
        return any(_data_contains_string(item, needle) for item in obj)
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == needle or _data_contains_string(v, needle):
                return True
    return False


# ---------------------------------------------------------------------------
# Vocabularies — placeholder name → entity type loaded by ModState.
# Used by §3 (pattern matching) and §4 (modifier validation), and exposed
# via the /vocabularies* endpoints.
# ---------------------------------------------------------------------------
VOCABULARY_TYPES: dict[str, str] = {
    "good": "Goods",
    "building": "Buildings",
    "bg": "Building Groups",
    "ig": "Interest Groups",
    "poptype": "Pop Types",
    "culture": "Cultures",
    "religion": "Religions",
    "law": "Laws",
    "law_group": "Law Groups",
    "tech": "Technologies",
    "combat_unit": "Combat Unit Types",
    "combat_unit_group": "Combat Unit Groups",
    "institution": "Institutions",
    "terrain": "Terrains",
    "country_rank": "Country Ranks",
    "ideology": "Ideologies",
    "discrimination_trait": "Discrimination Traits",
}

# When a vocabulary entity ID has a redundant prefix that's already part of
# the modifier-name pattern, strip it before comparing. E.g. building IDs are
# `building_textile_mills`, but the modifier `building_textile_mills_throughput_add`
# captures only `textile_mills`. Without stripping, the catalog match fails.
_VOCAB_STRIP_PREFIXES: dict[str, tuple[str, ...]] = {
    "building": ("building_",),
    "bg": ("bg_",),
    "ig": ("ig_",),
    "law": ("law_",),
    "institution": ("institution_",),
    "combat_unit": ("unit_", "combat_unit_"),
    "combat_unit_group": ("unit_group_", "combat_unit_group_"),
    "ideology": ("ideology_",),
    "law_group": ("law_group_",),
    "country_rank": ("rank_", "country_rank_"),
}


_TOP_LEVEL_KEY_RE = re.compile(r"^([a-z][a-z0-9_]*)\s*=\s*\{", re.MULTILINE)


def _disk_vocabulary_scan(directories: list[str]) -> list[str]:
    """Regex-scan .txt files for top-level `key = {` definitions.

    Used as a fallback when the Paradox parser chokes on a file (e.g. cultures
    with anonymous `color = rgb { 62 77 100 }` blocks). Order is best-effort —
    we only need the set of identifiers."""
    keys: list[str] = []
    seen: set[str] = set()
    for d in directories:
        if not d or not os.path.isdir(d):
            continue
        try:
            files = sorted(os.listdir(d))
        except OSError:
            continue
        for fname in files:
            if not fname.endswith(".txt"):
                continue
            path = os.path.join(d, fname)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            for match in _TOP_LEVEL_KEY_RE.finditer(text):
                key = match.group(1)
                # Filter common false positives — top-level only means
                # the line starts at column 0.
                if match.start() == 0 or text[match.start() - 1] == "\n":
                    if key not in seen:
                        seen.add(key)
                        keys.append(key)
    return keys


_vocab_disk_cache: dict[str, list[str]] = {}


def _vocabulary_values(placeholder: str) -> list[str]:
    """Return the list of valid IDs for a placeholder, or [] if not loaded.

    Falls back to a disk regex scan if the parser couldn't load the entity
    type (e.g. cultures with anonymous color blocks).
    """
    etype = VOCABULARY_TYPES.get(placeholder)
    if not etype:
        return []
    data = ms.get_data(etype) if ms else None
    raw_keys: list[str]
    if data:
        raw_keys = list(data.keys())
    elif placeholder in _vocab_disk_cache:
        raw_keys = _vocab_disk_cache[placeholder]
    else:
        base = base_game_paths.get(etype)
        mod_dir = mod_paths.get(etype)
        raw_keys = _disk_vocabulary_scan([base, mod_dir])
        _vocab_disk_cache[placeholder] = raw_keys
    # If the entity ID has a redundant prefix (e.g. building IDs start with
    # "building_") add the stripped form so it matches its appearance inside
    # modifier names like `building_textile_mills_throughput_add`.
    strip = _VOCAB_STRIP_PREFIXES.get(placeholder, ())
    if not strip:
        return raw_keys
    out: list[str] = []
    seen: set[str] = set()
    for k in raw_keys:
        if k not in seen:
            out.append(k)
            seen.add(k)
        for prefix in strip:
            if k.startswith(prefix):
                stripped = k[len(prefix):]
                if stripped and stripped not in seen:
                    out.append(stripped)
                    seen.add(stripped)
                break
    return out


def _vocabulary_index() -> dict[str, list[str]]:
    """Build the full {placeholder: [values]} map used by /vocabularies."""
    out = {}
    for placeholder in VOCABULARY_TYPES:
        out[placeholder] = _vocabulary_values(placeholder)
    return out


def _extract_modifier_fields(obj, prefix=""):
    """Walk parsed data and collect field names that look like modifiers (contain _ + end with _add/_mult etc)."""
    found = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and "_" in k:
                val = v
                if isinstance(val, tuple) and len(val) >= 2:
                    val = val[1]
                if isinstance(val, (int, float, str)):
                    try:
                        fv = float(val)
                        found[k] = fv
                    except (ValueError, TypeError):
                        pass
            if isinstance(v, (dict, tuple, list)):
                found.update(_extract_modifier_fields(v, prefix))
    elif isinstance(obj, (tuple, list)):
        for item in obj:
            found.update(_extract_modifier_fields(item, prefix))
    return found


# ---------------------------------------------------------------------------
# Event balance helpers — resolve option effects and tag modifier polarity.
# ---------------------------------------------------------------------------

# Keys inside an option block that don't represent player-facing effects.
EVENT_BALANCE_OPTION_META_KEYS = frozenset({
    "name", "default_option", "ai_chance", "trigger", "highlighted_option",
    "clicksound", "exclusive", "fallback", "is_locked", "soundeffect",
})

# Container/control-flow keys whose body should be recursed into (with breadcrumb).
EVENT_BALANCE_CONTAINER_KEYS = frozenset({
    "if", "else", "else_if", "random", "random_list", "random_valid",
    "hidden_effect", "show_as_tooltip", "custom_tooltip", "tooltip",
    "switch", "while", "limit",
})


def _iter_field_values(value):
    """Yield (operator, inner) for either a single ('=', val) tuple or a list of such tuples."""
    if isinstance(value, tuple) and len(value) >= 2:
        yield value[0], value[1]
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, tuple) and len(item) >= 2:
                yield item[0], item[1]


def _flatten_entity_data(raw):
    """Return a flat dict of (key -> value-or-list-of-values) from a parsed entity tuple/dict/list."""
    data = raw
    if isinstance(data, tuple) and len(data) >= 2:
        data = data[1]
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        flat = {}
        for item in data:
            if isinstance(item, dict):
                for k, v in item.items():
                    if k in flat:
                        existing = flat[k]
                        if isinstance(existing, list) and all(
                            isinstance(e, tuple) for e in existing
                        ):
                            existing.append(v if isinstance(v, tuple) else ("=", v))
                        else:
                            flat[k] = [existing, v]
                    else:
                        flat[k] = v
        return flat
    return {}


def _try_float(s):
    if isinstance(s, (int, float)):
        return float(s)
    if isinstance(s, str):
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _try_int(s):
    if isinstance(s, bool):
        return None
    if isinstance(s, int):
        return s
    if isinstance(s, float) and s.is_integer():
        return int(s)
    if isinstance(s, str):
        try:
            return int(s)
        except ValueError:
            return None
    return None


def _try_bool_yes(s):
    """Parse Paradox boolean fields (`yes`/`no`). Returns None when absent/malformed
    so callers can distinguish "explicitly off" from "not specified"."""
    if isinstance(s, bool):
        return s
    if isinstance(s, str):
        low = s.strip().lower()
        if low == "yes":
            return True
        if low == "no":
            return False
    return None


def _modifier_color_lookup(mod_name):
    """Return 'good'/'bad'/'neutral'/None for a modifier_type name (e.g. country_bureaucracy_mult)."""
    mod_types = ms.get_data("Modifier Types")
    if not mod_types or mod_name not in mod_types:
        return None
    data = _flatten_entity_data(mod_types[mod_name])
    color = get_field(data, "color")
    if isinstance(color, str):
        return color
    return None


def _resolve_static_modifier(name):
    """Look up a static modifier and return list of {modifier, value} pairs (numeric fields only)."""
    mods = ms.get_data("Modifiers")
    if not mods or name not in mods:
        return None
    data = _flatten_entity_data(mods[name])
    fields = []
    skip_keys = {"icon", "name", "color", "stack", "stacking"}
    for k, v in data.items():
        if k in skip_keys:
            continue
        for _op, val in _iter_field_values(v):
            num = _try_float(val)
            if num is not None:
                fields.append({"modifier": k, "value": num})
    return fields


def _polarity(value, color):
    """Player-perspective polarity of applying `value` to a modifier with the given color."""
    if value == 0 or color is None or color == "neutral":
        return "neutral" if color == "neutral" else "unknown" if color is None else "neutral"
    if color == "good":
        return "positive" if value > 0 else "negative"
    if color == "bad":
        return "positive" if value < 0 else "negative"
    return "neutral"


def _describe_add_modifier(value, scope):
    """Build an annotated effect dict for an add_modifier effect."""
    if isinstance(value, str):
        mod_name = value
        block = {}
    else:
        block = _flatten_entity_data(value) if not isinstance(value, dict) else value
        mod_name = get_field(block, "name")
        if isinstance(mod_name, str):
            mod_name = mod_name.strip('"')
    duration = get_field(block, "days") or get_field(block, "months") or get_field(block, "years")
    multiplier = get_field(block, "multiplier")
    is_decaying = get_field(block, "is_decaying")
    fields_raw = _resolve_static_modifier(mod_name) if mod_name else None
    annotated = []
    counts = {"positive": 0, "negative": 0, "neutral": 0, "unknown": 0}
    if fields_raw is None:
        resolved = "missing"
    else:
        resolved = "ok"
        for f in fields_raw:
            color = _modifier_color_lookup(f["modifier"])
            polarity = _polarity(f["value"], color)
            annotated.append({
                "modifier": f["modifier"],
                "value": f["value"],
                "color": color or "unknown",
                "polarity": polarity,
            })
            counts[polarity] = counts.get(polarity, 0) + 1
    out = {
        "kind": "add_modifier",
        "name": mod_name,
        "duration": duration,
        "is_decaying": is_decaying,
        "multiplier": multiplier,
        "resolved": resolved,
        "fields": annotated,
        "polarity_counts": counts,
    }
    if scope:
        out["scope"] = list(scope)
    return out


def _describe_change_variable(value, scope):
    block = _flatten_entity_data(value) if not isinstance(value, dict) else value
    var_name = get_field(block, "name")
    add = get_field(block, "add")
    subtract = get_field(block, "subtract")
    multiply = get_field(block, "multiply")
    out = {"kind": "change_variable", "variable": var_name}
    if add is not None:
        out["add"] = _try_float(add) if _try_float(add) is not None else add
    if subtract is not None:
        out["subtract"] = _try_float(subtract) if _try_float(subtract) is not None else subtract
    if multiply is not None:
        out["multiply"] = _try_float(multiply) if _try_float(multiply) is not None else multiply
    if scope:
        out["scope"] = list(scope)
    return out


def _walk_event_effects(node, scope, out):
    """Recursively walk an option body (or sub-block), appending effect dicts to *out*."""
    data = _flatten_entity_data(node) if not isinstance(node, dict) else node
    if not isinstance(data, dict):
        return
    for key, val in data.items():
        if key in EVENT_BALANCE_OPTION_META_KEYS:
            continue
        for _op, inner in _iter_field_values(val):
            _emit_event_effect(key, inner, scope, out)


def _emit_event_effect(key, value, scope, out):
    # `add_modifier` and `add_enactment_modifier` resolve the same way — both
    # take a static-modifier name and apply that modifier's fields to the
    # current scope, so we expand them identically.
    if key in ("add_modifier", "add_enactment_modifier"):
        described = _describe_add_modifier(value, scope)
        described["kind"] = key
        out.append(described)
        return
    if key == "change_variable":
        out.append(_describe_change_variable(value, scope))
        return

    # Container / control-flow blocks: descend with breadcrumb noting the wrapper.
    is_container = (
        key in EVENT_BALANCE_CONTAINER_KEYS
        or key.startswith("every_")
        or key.startswith("ordered_")
        or key.startswith("random_")
    )
    # Scope-change: keys with ":" (e.g. je:je_id, ig:ig_intelligentsia, s:STATE_X, c:TAG)
    is_scope_change = ":" in key
    # Heuristic scope traversals (single-target scope changes by name).
    scope_words = {
        "country", "owner", "ruler", "heir", "currency", "current_law",
        "state_region", "capital", "primary_culture", "religion", "region",
        "interest_group", "interest_group_leader", "overlord", "top_overlord",
        "head_of_state", "trade_center", "scope_state",
    }
    is_scope_word = key in scope_words

    if isinstance(value, dict) and (is_container or is_scope_change or is_scope_word):
        _walk_event_effects(value, scope + [key], out)
        return

    # random_list children: numeric weight keys with sub-blocks. Already handled above
    # because random_list is in CONTAINER_KEYS — its children are numeric-keyed dicts
    # which we'll surface as generic, but we also recurse the dict body so add_modifier
    # inside the weighted branch surfaces.
    if isinstance(value, dict) and key.isdigit():
        _walk_event_effects(value, scope + [f"weight={key}"], out)
        return

    # Generic / unrecognized effect — surface verbatim.
    entry = {"kind": key, "args": serialize(value)}
    if scope:
        entry["scope"] = list(scope)
    out.append(entry)


def _summarize_polarity(effects):
    """Aggregate add_modifier / add_enactment_modifier polarity counts across an option's effects."""
    total = {"positive": 0, "negative": 0, "neutral": 0, "unknown": 0}
    for eff in effects:
        if eff.get("kind") in ("add_modifier", "add_enactment_modifier"):
            for k, v in eff.get("polarity_counts", {}).items():
                total[k] = total.get(k, 0) + v
    return total


def _extract_event_ids_from_file(file_path):
    """Parse a .txt event file and return the list of event IDs declared at top level."""
    if not os.path.isabs(file_path):
        file_path = os.path.join(mod_path, file_path)
    if not os.path.isfile(file_path):
        return None, f"File not found: {file_path}"
    try:
        parser = ParadoxFileParser()
        parser.parse_file(file_path, apply_directives=False)
    except Exception as exc:
        return None, f"Failed to parse {file_path}: {exc}"
    ids = [k for k in parser.data.keys() if k != "namespace"]
    return ids, None


_POLARITY_GLYPHS = {"positive": "+", "negative": "-", "neutral": "·", "unknown": "?"}


def _format_value(v):
    if isinstance(v, float):
        if v == int(v):
            return f"{int(v)}"
        return f"{v:g}"
    return str(v)


def _classify_option_polarity(option):
    """Classify one option's polarity profile from its `polarity_totals`.

    Returns one of: 'pure_positive', 'pure_negative', 'mixed', 'empty'.
    'pure_positive' = ≥1 positive modifier-effect AND 0 negatives.
    'pure_negative' = 0 positives AND ≥1 negative.
    'empty' = no polarized modifier effects at all (may still have non-modifier effects).
    """
    totals = option.get("polarity_totals", {})
    pos = totals.get("positive", 0)
    neg = totals.get("negative", 0)
    if pos and not neg:
        return "pure_positive"
    if neg and not pos:
        return "pure_negative"
    if pos and neg:
        return "mixed"
    return "empty"


def _summarize_balance_option(opt):
    """Compact option summary used in dominance-issue payloads."""
    return {
        "name_key": opt.get("name_key"),
        "name": opt.get("name"),
        "default_option": opt.get("default_option"),
        "polarity_totals": opt.get("polarity_totals"),
        "modifiers": [
            {
                "name": e.get("name"),
                "fields": e.get("fields"),
                "polarity_counts": e.get("polarity_counts"),
            }
            for e in opt.get("effects", [])
            if e.get("kind") in ("add_modifier", "add_enactment_modifier")
        ],
    }


def _find_dominance_issues(event_balance):
    """Strict pure-positive vs pure-negative dominance (first-pass heuristic)."""
    pure_pos = []
    pure_neg = []
    for opt in event_balance.get("options", []):
        cls = _classify_option_polarity(opt)
        if cls == "pure_positive":
            pure_pos.append(opt)
        elif cls == "pure_negative":
            pure_neg.append(opt)
    if not pure_pos or not pure_neg:
        return None
    pos_label = pure_pos[0].get("name_key") or pure_pos[0].get("name") or "?"
    neg_label = pure_neg[0].get("name_key") or pure_neg[0].get("name") or "?"
    reason = (
        f"option '{pos_label}' has only positive modifier effects; "
        f"option '{neg_label}' has only negative modifier effects"
    )
    return {
        "id": event_balance.get("id"),
        "name": event_balance.get("name"),
        "reason": reason,
        "options_pure_positive": [_summarize_balance_option(o) for o in pure_pos],
        "options_pure_negative": [_summarize_balance_option(o) for o in pure_neg],
    }


def _find_soft_dominance_issues(event_balance, threshold=2):
    """Pairwise polarity-count dominance.

    Flags when one option (the *better*) has at least as many positives AND at
    most as many negatives as another (the *worse*), with their combined count
    gap meeting or exceeding `threshold` and at least one strict inequality.
    Catches "mixed-vs-mixed" cases where the strict pure-positive/pure-negative
    test misses a clear winner — e.g. A: pos=3 neg=1 vs B: pos=1 neg=2.
    """
    options = event_balance.get("options", [])
    if len(options) < 2:
        return None
    pairs = []
    n = len(options)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a = options[i]
            b = options[j]
            ap = a.get("polarity_totals") or {}
            bp = b.get("polarity_totals") or {}
            pos_diff = ap.get("positive", 0) - bp.get("positive", 0)   # A more positives than B
            neg_diff = bp.get("negative", 0) - ap.get("negative", 0)   # A fewer negatives than B
            if pos_diff < 0 or neg_diff < 0:
                continue
            if pos_diff == 0 and neg_diff == 0:
                continue
            if (pos_diff + neg_diff) < threshold:
                continue
            # Skip if the "better" option has zero polarized modifier effects
            # (it's an empty option dominating because the worse option is bad,
            # which is usually fine — empty options have non-modifier effects).
            if ap.get("positive", 0) == 0 and ap.get("negative", 0) == 0:
                continue
            pairs.append({
                "better": _summarize_balance_option(a),
                "worse": _summarize_balance_option(b),
                "pos_diff": pos_diff,
                "neg_diff": neg_diff,
            })
    if not pairs:
        return None
    # Deduplicate transitively: if A>B>C, we'd report (A,B), (B,C), (A,C) — keep
    # only the worst dominated option per "better" anchor to keep the report
    # readable.
    return {
        "id": event_balance.get("id"),
        "name": event_balance.get("name"),
        "reason": (
            f"option '{pairs[0]['better'].get('name_key')}' dominates "
            f"option '{pairs[0]['worse'].get('name_key')}' "
            f"(+{pairs[0]['pos_diff']} pos, +{pairs[0]['neg_diff']} fewer neg)"
        ),
        "pairs": pairs,
    }


_EVENT_HEADER_RE = re.compile(r"^([a-z][a-z0-9_]*\.[a-z0-9_]+)\s*=\s*\{")


def _scan_events_for_reviewed_dominance():
    """Walk events/*.txt for `# REVIEWED YYYY-MM-DD: rationale` suppressions on
    top-level event headers. Returns event_id → {date, rationale, file, line}.

    Anchor: a `# REVIEWED ...` comment counts as suppressing an event-balance
    dominance flag if it appears either inline on the header line or in the
    contiguous comment block immediately above the header.
    """
    from event_magnitude_audit import parse_reviewed_comment
    out = {}
    events_dir = os.path.join(mod_path, "events")
    if not os.path.isdir(events_dir):
        return out
    for fname in sorted(os.listdir(events_dir)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(events_dir, fname)
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue
        for i, line in enumerate(lines):
            m = _EVENT_HEADER_RE.match(line)
            if not m:
                continue
            eid = m.group(1)
            rev = parse_reviewed_comment(line)
            if not rev:
                k = i - 1
                while k >= 0 and lines[k].lstrip().startswith("#"):
                    rev = parse_reviewed_comment(lines[k])
                    if rev:
                        break
                    k -= 1
            if rev:
                out[eid] = {**rev, "file": os.path.relpath(path, mod_path), "line": i + 1}
    return out


def _render_event_balance_issues_text(scanned, flagged, mode="strict", reviewed_count=0):
    header = f"event-balance issues ({mode}) — scanned {scanned} events, flagged {len(flagged)}"
    if reviewed_count:
        header += f" ({reviewed_count} reviewed)"
    lines = [header, ""]
    for f in flagged:
        lines.append("=" * 78)
        lines.append(f"{f['id']}  —  {f.get('name') or ''}")
        lines.append(f"  {f['reason']}")
        if mode == "soft":
            for pair in f.get("pairs", []):
                better = pair["better"]
                worse = pair["worse"]
                lines.append(
                    f"  [+] {better.get('name') or better.get('name_key')}  "
                    f"totals={better.get('polarity_totals')}"
                )
                for m in better.get("modifiers", []):
                    lines.append(f"        add_modifier {m.get('name')}")
                    for fld in (m.get("fields") or []):
                        lines.append(
                            f"          {fld['polarity']:<8}  {fld['modifier']} = {fld['value']}  "
                            f"(color={fld['color']})"
                        )
                lines.append(
                    f"  [-] {worse.get('name') or worse.get('name_key')}  "
                    f"totals={worse.get('polarity_totals')}  "
                    f"(+{pair['pos_diff']} pos, +{pair['neg_diff']} fewer neg)"
                )
                for m in worse.get("modifiers", []):
                    lines.append(f"        add_modifier {m.get('name')}")
                    for fld in (m.get("fields") or []):
                        lines.append(
                            f"          {fld['polarity']:<8}  {fld['modifier']} = {fld['value']}  "
                            f"(color={fld['color']})"
                        )
                lines.append("")
        else:
            for o in f.get("options_pure_positive", []):
                lines.append(f"  [+] {o.get('name') or o.get('name_key')}  totals={o.get('polarity_totals')}")
                for m in o.get("modifiers", []):
                    lines.append(f"        add_modifier {m.get('name')}")
                    for fld in (m.get("fields") or []):
                        lines.append(f"          {fld['polarity']:<8}  {fld['modifier']} = {fld['value']}  (color={fld['color']})")
            for o in f.get("options_pure_negative", []):
                lines.append(f"  [-] {o.get('name') or o.get('name_key')}  totals={o.get('polarity_totals')}")
                for m in o.get("modifiers", []):
                    lines.append(f"        add_modifier {m.get('name')}")
                    for fld in (m.get("fields") or []):
                        lines.append(f"          {fld['polarity']:<8}  {fld['modifier']} = {fld['value']}  (color={fld['color']})")
        lines.append("")
    return "\n".join(lines)


def _render_event_balance_text(events, missing=None):
    """Pretty-print event balance results as plain text."""
    lines = []
    for ev in events:
        lines.append("=" * 78)
        lines.append(f"{ev['id']}  —  {ev.get('name') or ev.get('title_key')}")
        lines.append("=" * 78)
        for i, opt in enumerate(ev["options"]):
            tag = " [default]" if opt.get("default_option") else ""
            ai = f" ai_base={opt['ai_chance_base']}" if opt.get("ai_chance_base") is not None else ""
            label = opt.get("name") or opt.get("name_key") or f"option {i+1}"
            lines.append(f"\n  Option {i+1}: {label}{tag}{ai}")
            totals = opt.get("polarity_totals", {})
            lines.append(
                "    polarity: "
                f"+{totals.get('positive', 0)}  "
                f"-{totals.get('negative', 0)}  "
                f"·{totals.get('neutral', 0)}  "
                f"?{totals.get('unknown', 0)}"
            )
            for eff in opt["effects"]:
                _render_effect_text(eff, indent=4, lines=lines)
        lines.append("")
    if missing:
        lines.append(f"missing: {', '.join(missing)}")
    return "\n".join(lines)


def _render_effect_text(eff, indent, lines):
    pad = " " * indent
    scope = eff.get("scope")
    scope_str = f" [{' > '.join(scope)}]" if scope else ""
    kind = eff.get("kind")
    if kind == "add_modifier":
        dur = eff.get("duration")
        mult = eff.get("multiplier")
        decay = " decaying" if eff.get("is_decaying") == "yes" else ""
        suffix = []
        if dur:
            suffix.append(f"days={dur}")
        if mult:
            suffix.append(f"×{mult}")
        suf = f" ({', '.join(suffix)}{decay})" if suffix or decay else ""
        lines.append(f"{pad}add_modifier {eff.get('name')}{suf}{scope_str}")
        if eff.get("resolved") == "missing":
            lines.append(f"{pad}  (modifier definition not found)")
        for f in eff.get("fields", []):
            glyph = _POLARITY_GLYPHS.get(f["polarity"], "?")
            lines.append(
                f"{pad}  [{glyph} {f['polarity']:<8}]"
                f"  {f['modifier']} = {_format_value(f['value'])}"
                f"   (color={f['color']})"
            )
    elif kind == "change_variable":
        parts = []
        if "add" in eff:
            parts.append(f"add={_format_value(eff['add'])}")
        if "subtract" in eff:
            parts.append(f"subtract={_format_value(eff['subtract'])}")
        if "multiply" in eff:
            parts.append(f"multiply={_format_value(eff['multiply'])}")
        lines.append(f"{pad}change_variable {eff.get('variable')} {' '.join(parts)}{scope_str}")
    else:
        args = eff.get("args")
        if isinstance(args, (str, int, float, bool)) or args is None:
            lines.append(f"{pad}{kind} = {args}{scope_str}")
        else:
            args_str = json.dumps(args, ensure_ascii=False)
            if len(args_str) > 120:
                args_str = args_str[:117] + "..."
            lines.append(f"{pad}{kind} = {args_str}{scope_str}")


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------
class ModStateHandler(BaseHTTPRequestHandler):

    # ---- routing ----------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        parts = [unquote(p) for p in parsed.path.strip("/").split("/") if p]
        params = parse_qs(parsed.query)
        try:
            data = self.route(parts, params)
            self._respond_json(data)
        except KeyError as exc:
            self._respond_json(
                {"error": f"Not found: {exc}", "hint": "GET /help for the endpoint inventory."},
                404,
            )
        except Exception as exc:
            logger.error(f"Error handling GET {self.path}: {exc}\n{traceback.format_exc()}")
            self._respond_json({"error": str(exc)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        parts = [unquote(p) for p in parsed.path.strip("/").split("/") if p]
        params = parse_qs(parsed.query)
        if parts == ["reload"]:
            engine_only = (params.get("engine_only") or ["false"])[0].lower() == "true"
            try:
                if engine_only:
                    _reload_engine_only()
                    self._respond_json({"status": "engine-only reload complete"})
                else:
                    _load_mod_state()
                    body = {
                        "status": "reloaded",
                        "startup_seconds": startup_elapsed,
                    }
                    # Surface any actionable findings from the post-load chain
                    # (e.g. modifier_visibility_audit's unreviewed sub-threshold
                    # values). Caller sees them in the same response, not buried
                    # in the server log.
                    warnings = list(_post_load_warnings)
                    # Also surface vanilla_known_bugs.md parse-time warnings
                    # (anchor-or-die rejections, missing tracked-issue cross-refs,
                    # unresolved open_issues.md anchors). Validation runs as part
                    # of load_vanilla_bug_registry; the reload here just forces
                    # a re-read by busting the mtime cache before the next /logs
                    # request, so we call it explicitly and pull the warnings.
                    try:
                        from game_log_reader import (
                            load_vanilla_bug_registry as _load_vbr,
                            load_mod_noise_registry as _load_mnr,
                        )
                        _vbr_doc = os.path.join(mod_path, "docs", "vanilla", "vanilla_known_bugs.md")
                        _mnr_doc = os.path.join(mod_path, "docs", "audits", "mod_known_noise.md")
                        _, _, _, _vbr_warnings = _load_vbr(_vbr_doc)
                        _, _, _, _mnr_warnings = _load_mnr(_mnr_doc)
                        for w in _vbr_warnings:
                            warnings.append({"label": "vanilla_bug_registry", "detail": w})
                        for w in _mnr_warnings:
                            warnings.append({"label": "mod_noise_registry", "detail": w})
                    except Exception as _vbr_exc:  # noqa: BLE001
                        logger.warning(f"known-noise registry warning collection failed: {_vbr_exc}")
                    if warnings:
                        body["warnings"] = warnings
                    self._respond_json(body)
            except Exception as exc:
                logger.error(f"Error during reload: {exc}\n{traceback.format_exc()}")
                self._respond_json({"error": str(exc)}, 500)
        else:
            self._respond_json({"error": "Unknown POST endpoint"}, 404)

    def route(self, parts, params):
        if not parts or parts == ["status"]:
            return self._status()
        ep = parts[0]
        rest = parts[1:]
        dispatch = {
            "help": lambda: self._help(),
            "entity-types": lambda: list(ms.mod_parsers.keys()),
            "keys": lambda: self._keys(rest, params),
            "raw": lambda: self._raw(rest),
            "localize": lambda: self._localize(rest),
            "unlocalize": lambda: self._unlocalize(rest),
            "search": lambda: self._search(params),
            "laws": lambda: self._laws(rest),
            "technologies": lambda: self._technologies(rest, params),
            "buildings": lambda: self._buildings(rest, params),
            "goods": lambda: self._goods(),
            "combat-units": lambda: self._combat_units(),
            "ideologies": lambda: self._ideologies(rest),
            # Analytical endpoints
            "references": lambda: self._references(rest),
            "tech-tree": lambda: self._tech_tree(rest),
            "modifier-search": lambda: self._modifier_search(params),
            "unlocked-by": lambda: self._unlocked_by(rest),
            "tech-unlocks": lambda: self._tech_unlocks(rest, params),
            "annotators": lambda: self._annotators(),
            "filter": lambda: self._filter(rest, params),
            # New structured endpoints
            "events": lambda: self._events(rest, params),
            "event-balance": lambda: self._event_balance(rest, params),
            # Event magnitude audit (hardcoded fast-scaling values)
            "event-magnitude-audit": lambda: self._event_magnitude_audit(params),
            "institutions": lambda: self._institutions(rest),
            "production-methods": lambda: self._production_methods(rest, params),
            "journal-entries": lambda: self._journal_entries(rest),
            "decisions": lambda: self._decisions(rest),
            "script-values": lambda: self._script_values(rest),
            "decrees": lambda: self._decrees(rest),
            "on-actions": lambda: self._on_actions(rest),
            # Technology effects endpoint
            "technology-effects": lambda: self._technology_effects(rest),
            # Engine docs endpoints
            "engine-docs": lambda: self._engine_docs(rest, params),
            # Developer reference docs (.md files from base game)
            "dev-docs": lambda: self._dev_docs(rest, params),
            # Missing localization detection
            "unlocalized": lambda: self._unlocalized(params),
            # Vocabularies (placeholder → values used by pattern matching / validation)
            "vocabularies": lambda: self._vocabularies(rest),
            # Modifier pattern catalog + auto-discovered families
            "modifier-patterns": lambda: self._modifier_patterns(rest, params),
            # Mod-vs-engine validation
            "validate": lambda: self._validate(rest, params),
            # Duplicate-image detector for unique-per-entity image fields
            "duplicate-images": lambda: self._duplicate_images(params),
            # Generator-ownership map for auto-generated mod files
            "auto-generated": lambda: self._auto_generated(),
            # Game logs (debug.log, error.log, game.log, …)
            "logs": lambda: self._logs(rest, params),
            # Convenience endpoints — thin wrappers over /keys/<EntityType>.
            "cultures": lambda: self._vocab_endpoint("culture"),
            "religions": lambda: self._vocab_endpoint("religion"),
            "interest-groups": lambda: self._vocab_endpoint("ig"),
            "law-groups": lambda: self._vocab_endpoint("law_group"),
            "building-groups": lambda: self._vocab_endpoint("bg"),
            "pop-types": lambda: self._vocab_endpoint("poptype"),
            "country-ranks": lambda: self._vocab_endpoint("country_rank"),
            "terrain": lambda: self._vocab_endpoint("terrain"),
            "discrimination-traits": lambda: self._vocab_endpoint("discrimination_trait"),
        }
        handler = dispatch.get(ep)
        if handler is None:
            raise KeyError(ep)
        result = handler()
        # Optional post-process: ?annotate=<name>[,<name>...] enriches every
        # entity entry shaped like {type, id, ...} in the response. When the
        # param is absent or empty the post-processor never runs — pure
        # pass-through. Enables future annotators to plug in without touching
        # any endpoint handler.
        annotate_param = (params.get("annotate") or [""])[0]
        if annotate_param:
            annotators.apply_to_response(
                result, annotate_param, Path(mod_path),
                cache=_annotator_compute_cache,
            )
        return result

    # ---- endpoints --------------------------------------------------------
    def _help(self):
        return {
            "see_also": "docs/guides/python_tools.md for full workflow examples.",
            "post": {
                "/reload": "Re-parse mod + vanilla; runs post-load generators and audits. ?engine_only=true skips the ModState rebuild.",
            },
            "get": [
                {"path": "/status", "desc": "Server uptime, entity-type list, engine-docs freshness, vanilla-snapshot staleness."},
                {"path": "/help", "desc": "This endpoint inventory."},
                {"path": "/entity-types", "desc": "List of every entity type the parser exposes."},
                {"path": "/keys/<EntityType>", "desc": "All entity IDs of a given type (e.g. /keys/Buildings)."},
                {"path": "/raw/<EntityType>/<id>", "desc": "Raw parsed AST for one entity."},
                {"path": "/localize/<key>", "desc": "Resolve a localization key to its English string."},
                {"path": "/unlocalize?q=<text>", "desc": "Reverse-lookup loc keys whose value matches a substring."},
                {"path": "/search?q=<text>", "desc": "Full-text search across mod + vanilla parsed entities."},
                {"path": "/laws/<id?>", "desc": "Laws and law groups; omit id for the index."},
                {"path": "/technologies/<id?>", "desc": "Tech entries and tree relationships."},
                {"path": "/buildings/<id?>", "desc": "Building defs incl. PMG list."},
                {"path": "/goods", "desc": "Goods catalog."},
                {"path": "/combat-units", "desc": "Combat unit type/group catalog."},
                {"path": "/ideologies/<id?>", "desc": "Ideology defs and IG-stance maps."},
                {"path": "/production-methods/<id?>", "desc": "Production methods (and their groups). Pass a PMG or PM id."},
                {"path": "/journal-entries/<id?>", "desc": "Journal entries (mod-only)."},
                {"path": "/decisions/<id?>", "desc": "Decisions catalog."},
                {"path": "/script-values/<id?>", "desc": "Script value definitions."},
                {"path": "/decrees/<id?>", "desc": "Decree catalog."},
                {"path": "/on-actions/<id?>", "desc": "On-action wiring (mod-only)."},
                {"path": "/events/<id?>", "desc": "Events (mod-only)."},
                {"path": "/event-balance/<id?>", "desc": "Event option / fast-scaling magnitude analysis."},
                {"path": "/institutions/<id?>", "desc": "Institutions catalog."},
                {"path": "/references/<entity>", "desc": "Where in the parsed corpus an entity is referenced."},
                {"path": "/tech-tree/<id?>", "desc": "Tech-tree adjacency view."},
                {"path": "/tech-unlocks/<tech>", "desc": "What a tech unlocks (PMs, buildings, laws, etc.)."},
                {"path": "/unlocked-by/<entity>", "desc": "Inverse of tech-unlocks: what gates an entity."},
                {"path": "/modifier-search?q=<name>", "desc": "Validate / discover modifier keys against the engine catalog."},
                {"path": "/modifier-patterns/<sub?>", "desc": "Modifier pattern catalog and discovered families."},
                {"path": "/engine-docs/<section>/<key?>", "desc": "Engine reference (effects/triggers/modifiers/event-targets/on-actions/custom-localization)."},
                {"path": "/dev-docs/<section?>", "desc": "Vanilla developer-reference markdown docs."},
                {"path": "/technology-effects/<tech>", "desc": "Aggregate of all effects applied by a tech."},
                {"path": "/event-magnitude-audit", "desc": "Hardcoded fast-scaling event-value audit."},
                {"path": "/unlocalized", "desc": "Mod-introduced keys missing English loc."},
                {"path": "/vocabularies/<name?>", "desc": "Placeholder vocab tables (cultures, religions, IGs, ...)."},
                {"path": "/validate/<id?>", "desc": "Mod-vs-engine validation report."},
                {"path": "/duplicate-images", "desc": "Detect duplicated unique-per-entity image fields."},
                {"path": "/auto-generated", "desc": "Generator-ownership map for auto-generated mod files."},
                {"path": "/logs/<which?>", "desc": "Game logs (debug / error / game). Use ?include_external=true to keep third-party-mod entries."},
                {"path": "/annotators", "desc": "List of available ?annotate=<name> post-processors."},
                {"path": "/filter/<EntityType>", "desc": "Server-side filter over an entity collection."},
                {"path": "/cultures", "desc": "Culture vocab (thin wrapper over /keys/Cultures)."},
                {"path": "/religions", "desc": "Religion vocab."},
                {"path": "/interest-groups", "desc": "IG vocab."},
                {"path": "/law-groups", "desc": "Law-group vocab."},
                {"path": "/building-groups", "desc": "Building-group vocab."},
                {"path": "/pop-types", "desc": "Pop-type vocab."},
                {"path": "/country-ranks", "desc": "Country-rank vocab."},
                {"path": "/terrain", "desc": "Terrain vocab."},
                {"path": "/discrimination-traits", "desc": "Discrimination-trait vocab."},
            ],
            "global_query_params": {
                "annotate": "Comma-separated annotators to enrich entity entries (see /annotators).",
            },
        }

    def _status(self):
        uptime = time.time() - _server_start_time if _server_start_time else 0
        engine_mtimes = {}
        oldest = None
        for k, p in engine_docs_sources.items():
            m = _safe_mtime(p)
            if m is None:
                continue
            engine_mtimes[k] = datetime.fromtimestamp(m, tz=timezone.utc).isoformat(timespec="seconds")
            if oldest is None or m < oldest:
                oldest = m
        age_days = None
        if oldest:
            age_days = int((time.time() - oldest) // 86400)

        # Vanilla-source-mirror cross-check: if our docs snapshot is older than
        # the mirror's HEAD commit, the snapshot is stale (vanilla updated since
        # the user last ran `script_docs` in vanilla).
        repo_head = _load_vanilla_repo_head_info()

        def _summarize(p: Optional[str]) -> dict:
            """Return {path, exists, oldest_mtime, files} for a docs dir."""
            out = {"path": p, "exists": bool(p) and os.path.isdir(p)}
            if not out["exists"]:
                return out
            mtimes = []
            files = []
            for fn in sorted(os.listdir(p)):
                if not fn.endswith(".log"):
                    continue
                m = _safe_mtime(os.path.join(p, fn))
                if m is not None:
                    mtimes.append(m)
                    files.append(fn)
            if mtimes:
                oldest_m = min(mtimes)
                out["oldest_mtime"] = datetime.fromtimestamp(
                    oldest_m, tz=timezone.utc
                ).isoformat(timespec="seconds")
                out["age_days"] = int((time.time() - oldest_m) // 86400)
                out["files"] = files
            return out

        active_path_by_label = {
            "vanilla_snapshot": vanilla_snapshot_docs_path,
            "digest_snapshot": vanilla_snapshot_docs_path_default,
            "mod_loaded": mod_loaded_docs_path,
        }
        vanilla_block = {
            "source_label": engine_docs_source_label or "unknown",
            "active_path": active_path_by_label.get(
                engine_docs_source_label, mod_loaded_docs_path
            ),
            "vanilla_snapshot": _summarize(vanilla_snapshot_docs_path),
            "digest_snapshot": _summarize(vanilla_snapshot_docs_path_default),
            "mod_loaded_snapshot": _summarize(mod_loaded_docs_path),
            "refresh_workflow": {
                "vanilla": (
                    "Disable the mod in the launcher, launch the game, type "
                    "`script_docs` in the in-game console (~ key), then copy "
                    f"the .log files from {mod_loaded_docs_path}/ to "
                    + (
                        f"{vanilla_snapshot_docs_path}/."
                        if vanilla_snapshot_docs_path
                        else "the directory in `vanilla_snapshot_docs_path` "
                             "(currently unset — leave it unset to keep using "
                             "the digest snapshot below)."
                    )
                ),
                "digest": (
                    "No action needed — the digest snapshot is auto-pulled from "
                    "https://github.com/Victoria-3-Modding-Co-op/Modding-Digests "
                    "on mod_state_server cold start. The highest-version directory "
                    "with engine-doc logs wins."
                ),
                "mod_loaded": (
                    "Enable the mod in the launcher, launch the game, type "
                    f"`script_docs` in the in-game console — files land at "
                    f"{mod_loaded_docs_path}/ directly."
                ),
            },
        }
        if repo_head:
            vanilla_block["repo_head"] = repo_head["sha_short"]
            vanilla_block["repo_head_date"] = repo_head["date_iso"]
            if oldest is not None:
                vanilla_block["is_stale"] = oldest < repo_head["date_unix"]
                if vanilla_block["is_stale"]:
                    vanilla_block["stale_reason"] = (
                        "Vanilla snapshot is older than ~/src/vic3 HEAD — "
                        "re-run `script_docs` in vanilla to refresh."
                    )

        # Contamination check: the snapshot is supposed to be vanilla-only, but
        # if it contains modifiers the mod declares as `script_only = yes`, the
        # snapshot was actually generated with the mod loaded. Re-running
        # `script_docs` in vanilla would clean it.
        if _vanilla_snapshot_contamination:
            vanilla_block["is_contaminated"] = True
            vanilla_block["contamination_count"] = len(_vanilla_snapshot_contamination)
            vanilla_block["contamination_examples"] = sorted(_vanilla_snapshot_contamination)[:5]
            vanilla_block["contamination_reason"] = (
                "Vanilla snapshot contains mod-declared script_only modifiers "
                "— it was likely generated with the mod loaded. Re-run "
                "`script_docs` in pure-vanilla to refresh."
            )

        return {
            "status": "running",
            "pid": os.getpid(),
            "uptime_seconds": round(uptime, 1),
            "startup_seconds": round(startup_elapsed, 1),
            "entity_types": list(ms.mod_parsers.keys()),
            "localization_keys": len(ms.localization),
            "engine_docs_timestamps": engine_mtimes,
            "engine_docs_age_days": age_days,
            "vanilla_snapshot": vanilla_block,
            "pattern_catalog_size": len(pattern_catalog),
            "discovered_patterns": len(discovered_patterns),
        }

    def _keys(self, parts, params):
        """GET /keys/<EntityType>  - list entity IDs with localized names."""
        if not parts:
            return list(ms.mod_parsers.keys())
        etype = parts[0]
        data = ms.get_data(etype)
        if data is None:
            raise KeyError(etype)
        return [
            {"type": etype, "id": eid, "name": ms.localize(eid)}
            for eid in data.keys()
        ]

    # ---- vocabularies -----------------------------------------------------
    def _vocabularies(self, parts):
        """GET /vocabularies            — full {placeholder: [values]} map.
        GET /vocabularies/<placeholder>  — list for a single placeholder."""
        if not parts:
            return {
                p: {
                    "entity_type": VOCABULARY_TYPES[p],
                    "count": len(values),
                    "values": values,
                }
                for p, values in _vocabulary_index().items()
            }
        placeholder = parts[0]
        if placeholder not in VOCABULARY_TYPES:
            raise KeyError(placeholder)
        values = _vocabulary_values(placeholder)
        return {
            "placeholder": placeholder,
            "entity_type": VOCABULARY_TYPES[placeholder],
            "count": len(values),
            "values": values,
        }

    def _vocab_endpoint(self, placeholder: str):
        """Convenience endpoint behind /cultures, /religions, etc."""
        values = _vocabulary_values(placeholder)
        return {
            "placeholder": placeholder,
            "entity_type": VOCABULARY_TYPES[placeholder],
            "count": len(values),
            "entries": [{"id": v, "name": ms.localize(v)} for v in values],
        }

    # ---- modifier patterns -----------------------------------------------
    def _modifier_patterns(self, parts, params):
        """GET /modifier-patterns                — list all patterns.
        GET /modifier-patterns?source=catalog|discovered|all
        GET /modifier-patterns?expand=<pattern>&<placeholder>=<value>
        GET /modifier-patterns/<pattern>        — detail for one pattern."""
        source_filter = (params.get("source") or ["all"])[0]
        expand_pattern = (params.get("expand") or [None])[0]

        if expand_pattern:
            return self._modifier_pattern_expand(expand_pattern, params)

        catalog_set = {entry["pattern"] for entry in pattern_catalog}
        discovered_set = {d["pattern"] for d in discovered_patterns}
        catalog_meta = {entry["pattern"]: entry for entry in pattern_catalog}
        discovered_meta = {d["pattern"]: d for d in discovered_patterns}
        vocabularies = _vocabulary_index()

        if parts:
            pattern = parts[0]
            return self._modifier_pattern_detail(
                pattern, catalog_meta, discovered_meta, vocabularies
            )

        out = []
        for pattern, members in sorted(pattern_index.items()):
            origin = "catalog" if pattern in catalog_set else (
                "discovered" if pattern in discovered_set else "unknown"
            )
            if source_filter != "all" and origin != source_filter:
                continue
            entry_meta = catalog_meta.get(pattern) or discovered_meta.get(pattern) or {}
            placeholder = entry_meta.get("placeholder", "?")
            vocab = entry_meta.get("vocab", placeholder)
            vocab_size = len(vocabularies.get(vocab, []) or [])
            out.append({
                "pattern": pattern,
                "source": origin,
                "placeholder": placeholder,
                "vocab": vocab,
                "members": len(members),
                "vocab_size": vocab_size,
                "missing_count": max(0, vocab_size - len(members)),
            })
        return {"count": len(out), "patterns": out}

    def _modifier_pattern_detail(self, pattern, catalog_meta, discovered_meta, vocabularies):
        if pattern not in pattern_index:
            raise KeyError(pattern)
        members = pattern_index[pattern]
        meta = catalog_meta.get(pattern) or discovered_meta.get(pattern) or {}
        placeholder = meta.get("placeholder", "?")
        vocab_name = meta.get("vocab", placeholder)
        vocab_values = set(vocabularies.get(vocab_name, []) or [])
        present = set(members.keys())
        missing = sorted(vocab_values - present) if vocab_values else []
        origin = "catalog" if pattern in catalog_meta else (
            "discovered" if pattern in discovered_meta else "unknown"
        )
        return {
            "pattern": pattern,
            "source": origin,
            "placeholder": placeholder,
            "vocab": vocab_name,
            "notes": meta.get("notes", ""),
            "members": [
                {"value": v, "name": pattern.replace("{" + placeholder + "}", v),
                 "display_name": entry.get("display_name", ""),
                 "mask": entry.get("mask", "")}
                for v, entry in sorted(members.items())
            ],
            "missing": missing,
            "missing_count": len(missing),
        }

    # ---- game logs --------------------------------------------------------
    def _logs(self, parts, params):
        """GET /logs                       — index of available logs.
        GET /logs/sessions                — cluster log files into launch sessions.
        GET /logs/<family>                — entries for the latest gen.
        GET /logs/<family>?gen=N          — backup gen.
        GET /logs/<family>?summary=true   — category histogram + top repeats.
        GET /logs/<family>/diff[?against=N]
        GET /logs/<family>?q=&file=&source=&category=&since=
        GET /logs/<family>?dedupe=&dedupe_key=&limit=&offset=&raw=
        GET /logs/<family>?mod_only=true|false|unknown
            — true (default for error/debug): keep only entries with at least
              one mod-style script path in `files`.
            — false (default elsewhere): keep all entries.
            — unknown: keep entries unless they're tagged as a registered
              vanilla bug or registered vanilla noise. Includes mod-path
              entries AND entries with empty `files` whose origin can't be
              confirmed vanilla — useful for catching engine errors that
              surface from vanilla cpp source (no mod path attached) but
              are actually caused by mod content (e.g. unregistered concept
              refs, malformed loc).
        GET /logs/<family>?vanilla_bugs=show|hide|only
            — tag (default) / drop / keep-only entries that match a vanilla bug
            registered in docs/vanilla/vanilla_known_bugs.md.
        GET /logs/<family>?mod_noise=show|hide|only
            — same shape, but for mod-side cosmetic entries registered in
            docs/audits/mod_known_noise.md (these are NOT vanilla bugs; they're mod
            issues filtered for triage cleanliness but cross-linked to
            docs/audits/open_issues.md so they remain actionable).
            Tagged entries get a `vanilla_bug_ref: {title, section, kind}`
            field; `kind` is "vanilla", "vanilla_noise", or "mod_low_priority".
            Use `?vanilla_bugs=hide&mod_noise=hide` for a fully-clean triage
            view, or `?mod_only=unknown` to surface uncategorized engine
            entries that the canonical filters hide.
        """
        from game_log_reader import (
            list_logs, parse_log, filter_mod_only, filter_external_mods, filter_entries,
            dedupe, summarize, diff_against_backup, cluster_sessions,
            load_vanilla_bug_registry, load_mod_noise_registry, tag_vanilla_bugs,
        )

        vanilla_bugs_doc = os.path.join(mod_path, "docs", "vanilla", "vanilla_known_bugs.md")
        mod_noise_doc = os.path.join(mod_path, "docs", "audits", "mod_known_noise.md")
        _, vb_by_basename, vb_by_source, _ = load_vanilla_bug_registry(vanilla_bugs_doc)
        _, mn_by_basename, mn_by_source, _ = load_mod_noise_registry(mod_noise_doc)

        def _apply_mod_only_mode(entries, mode):
            """Tristate filter on `mod_only` parameter.

            - 'true'    → keep entries with at least one mod-style script path
                          in `files` (today's default for error/debug).
            - 'false'   → keep all entries.
            - 'unknown' → keep entries unless they're tagged with a
                          `vanilla_bug_ref` of kind 'vanilla' or
                          'vanilla_noise'. Includes mod-path entries AND
                          entries with empty `files` whose origin can't be
                          confirmed vanilla. Surfaces engine errors that
                          come from vanilla cpp source (no mod path attached)
                          but are caused by mod content — e.g. unregistered
                          concept references, malformed loc, custom-loc
                          references to undeclared keys.

            Other values (incl. typos) fall through as 'false' / no filter.

            Caller must invoke `_apply_known_noise_tagging` first so that
            `vanilla_bug_ref` is populated when `mode == 'unknown'`.
            """
            if mode == "true":
                return filter_mod_only(entries)
            if mode == "unknown":
                kept = []
                for e in entries:
                    ref = e.vanilla_bug_ref
                    if ref is not None and ref.get("kind") in ("vanilla", "vanilla_noise"):
                        continue
                    kept.append(e)
                return kept
            return entries

        def _apply_known_noise_tagging(entries, vanilla_mode, mod_noise_mode):
            """Tag entries against both registries, then apply per-kind modes (show|hide|only).

            Two-pass tagging: vanilla registry first, then mod-noise registry on
            entries that didn't match vanilla. Once tagged, an entry's
            vanilla_bug_ref.kind tells us which mode applies for filtering.
            """
            tag_vanilla_bugs(entries, vb_by_basename, vb_by_source)
            tag_vanilla_bugs(entries, mn_by_basename, mn_by_source)

            def _matches_vanilla(e):
                ref = e.vanilla_bug_ref
                return ref is not None and ref.get("kind") != "mod_low_priority"

            def _matches_mod(e):
                ref = e.vanilla_bug_ref
                return ref is not None and ref.get("kind") == "mod_low_priority"

            filtered = []
            for e in entries:
                v_match = _matches_vanilla(e)
                m_match = _matches_mod(e)
                if vanilla_mode == "hide" and v_match:
                    continue
                if mod_noise_mode == "hide" and m_match:
                    continue
                if vanilla_mode == "only" or mod_noise_mode == "only":
                    keep = (
                        (vanilla_mode == "only" and v_match)
                        or (mod_noise_mode == "only" and m_match)
                    )
                    if not keep:
                        continue
                filtered.append(e)
            return filtered

        if not parts:
            include_mp = (params.get("mp_sessions") or ["false"])[0].lower() == "true"
            infos = list_logs(game_logs_path, include_mp_sessions=include_mp)
            grouped: dict = defaultdict(list)
            for info in infos:
                grouped[info.family].append(info.to_dict())
            return {
                "logs_dir": game_logs_path,
                "families": dict(sorted(grouped.items())),
                "session_count_hint": len(cluster_sessions(infos)),
            }

        if parts[0] == "sessions":
            include_mp = (params.get("mp_sessions") or ["false"])[0].lower() == "true"
            infos = list_logs(game_logs_path, include_mp_sessions=include_mp)
            return {"sessions": cluster_sessions(infos)}

        family = parts[0]
        action = parts[1] if len(parts) > 1 else None
        gen = int((params.get("gen") or ["0"])[0])
        infos = list_logs(game_logs_path)
        match = None
        for info in infos:
            if info.family == family and info.generation == gen:
                match = info
                break
        if match is None:
            raise KeyError(f"{family} (gen={gen})")

        # Diff endpoint
        if action == "diff":
            against = int((params.get("against") or ["1"])[0])
            against_match = next(
                (i for i in infos if i.family == family and i.generation == against),
                None,
            )
            if against_match is None:
                return {"error": f"No {family}.{against}.log to diff against"}
            mod_only_mode = (params.get("mod_only") or ["true"])[0].lower()
            default_external = "false" if family in ("error", "debug") else "true"
            include_external = (params.get("include_external") or [default_external])[0].lower() == "true"
            vanilla_bugs_mode = (params.get("vanilla_bugs") or ["show"])[0].lower()
            mod_noise_mode = (params.get("mod_noise") or ["show"])[0].lower()
            current_entries = parse_log(match.path)
            against_entries = parse_log(against_match.path)
            # Tag noise first so the mod_only=unknown filter can examine
            # vanilla_bug_ref. The vanilla_bugs/mod_noise modes also apply
            # their own drop/only filtering inside this call.
            current_entries = _apply_known_noise_tagging(current_entries, vanilla_bugs_mode, mod_noise_mode)
            against_entries = _apply_known_noise_tagging(against_entries, vanilla_bugs_mode, mod_noise_mode)
            current_entries = _apply_mod_only_mode(current_entries, mod_only_mode)
            against_entries = _apply_mod_only_mode(against_entries, mod_only_mode)
            if not include_external:
                current_entries = filter_external_mods(current_entries)
                against_entries = filter_external_mods(against_entries)
            return {
                "current": match.to_dict(),
                "against": against_match.to_dict(),
                "diff": diff_against_backup(current_entries, against_entries),
            }

        # Raw / parsed entries
        entries = parse_log(match.path)
        # mod_only default: true for error/debug, false for the rest
        default_mod_only = "true" if family in ("error", "debug") else "false"
        mod_only_mode = (params.get("mod_only") or [default_mod_only])[0].lower()
        # Tag entries that match docs/vanilla/vanilla_known_bugs.md and docs/audits/mod_known_noise.md,
        # then optionally drop or keep-only by kind. Modes per param: show (default —
        # tag, keep visible), hide, only.
        #   ?vanilla_bugs=hide → drops vanilla / vanilla_noise tagged entries
        #   ?mod_noise=hide    → drops mod_low_priority tagged entries
        # Use both with `hide` for a fully-clean triage view; use `only` on either
        # for an audit of "what's currently being filtered".
        # Tagging is applied BEFORE mod_only so the `mod_only=unknown` mode can
        # examine `vanilla_bug_ref` on each entry.
        vanilla_bugs_mode = (params.get("vanilla_bugs") or ["show"])[0].lower()
        mod_noise_mode = (params.get("mod_noise") or ["show"])[0].lower()
        entries = _apply_known_noise_tagging(entries, vanilla_bugs_mode, mod_noise_mode)
        entries = _apply_mod_only_mode(entries, mod_only_mode)
        # include_external default: drop known third-party-mod spam (Statistics, ...)
        # from error/debug, keep it for everything else.
        default_external = "false" if family in ("error", "debug") else "true"
        include_external = (params.get("include_external") or [default_external])[0].lower() == "true"
        if not include_external:
            entries = filter_external_mods(entries)
        entries = filter_entries(
            entries,
            q=(params.get("q") or [None])[0],
            file_glob=(params.get("file") or [None])[0],
            source=(params.get("source") or [None])[0],
            category=(params.get("category") or [None])[0],
            since=(params.get("since") or [None])[0],
        )
        if (params.get("summary") or ["false"])[0].lower() == "true":
            return {"file": match.to_dict(), **summarize(entries)}

        if (params.get("raw") or ["false"])[0].lower() == "true":
            limit = int((params.get("limit") or ["1000"])[0])
            offset = int((params.get("offset") or ["0"])[0])
            chunk = entries[offset: offset + limit]
            text = "\n".join(
                f"[{e.time}][{e.source}]: {e.message}" if e.time else e.message
                for e in chunk
            )
            return {"file": match.to_dict(), "raw": text, "count": len(chunk)}

        do_dedupe = (params.get("dedupe") or ["true"])[0].lower() == "true"
        if do_dedupe:
            dedupe_key = (params.get("dedupe_key") or ["message+file"])[0]
            deduped = dedupe(entries, key=dedupe_key)
            limit = int((params.get("limit") or ["1000"])[0])
            offset = int((params.get("offset") or ["0"])[0])
            return {
                "file": match.to_dict(),
                "deduped": True,
                "total_unique": len(deduped),
                "entries": deduped[offset: offset + limit],
            }
        limit = int((params.get("limit") or ["1000"])[0])
        offset = int((params.get("offset") or ["0"])[0])
        chunk = entries[offset: offset + limit]
        return {
            "file": match.to_dict(),
            "deduped": False,
            "total": len(entries),
            "entries": [e.to_dict() for e in chunk],
        }

    def _auto_generated(self):
        """GET /auto-generated — return the file → generator-script ownership map.

        Helps Claude / devs answer "is this file safe to hand-edit?" in one
        request. The authoritative source is `docs/auto_generated_files.md`;
        this endpoint mirrors the table in machine-readable form.
        """
        # Curated list mirroring docs/auto_generated_files.md.
        # `pattern` is a glob relative to the mod root.
        # `header_marker` indicates whether the file carries an # AUTO-GENERATED
        # header (true) or relies solely on this map (false).
        return {
            "auto_generated": [
                {
                    "pattern": "common/ideologies/modified.txt",
                    "owner": "apply_ideologies.py",
                    "input": "ideology_modifications.py",
                    "header_marker": True,
                },
                {
                    "pattern": "common/interest_groups/00_*.txt",
                    "owner": "ig_feminism.py",
                    "input": "mod state",
                    "header_marker": True,
                },
                {
                    "pattern": "common/buy_packages/00_buy_packages.txt",
                    "owner": "pop_needs_curves.py",
                    "input": "mod state",
                    "header_marker": True,
                },
                {
                    "pattern": "map_data/state_regions/*.txt",
                    "owner": "resources.py",
                    "input": "deposits_config.json + vanilla state_regions",
                    "header_marker": False,
                },
                {
                    "pattern": "docs/engine/laws.txt",
                    "owner": "mod_state_script.py",
                    "input": "mod state",
                    "header_marker": True,
                },
                {
                    "pattern": "docs/engine/technologies.txt",
                    "owner": "mod_state_script.py",
                    "input": "mod state",
                    "header_marker": True,
                },
                {
                    "pattern": "docs/engine/buildings.txt",
                    "owner": "mod_state_script.py",
                    "input": "mod state",
                    "header_marker": True,
                },
                {
                    "pattern": "docs/engine/goods.txt",
                    "owner": "mod_state_script.py",
                    "input": "mod state",
                    "header_marker": True,
                },
                {
                    "pattern": "docs/engine/combat_units.txt",
                    "owner": "mod_state_script.py",
                    "input": "mod state",
                    "header_marker": True,
                },
                {
                    "pattern": "docs/engine/vic3_*_reference.md",
                    "owner": "engine_docs_render.py",
                    "input": "vanilla engine logs",
                    "header_marker": True,
                },
                {
                    "pattern": "docs/engine/*_summary.txt",
                    "owner": "engine_docs_render.py",
                    "input": "vanilla engine logs",
                    "header_marker": True,
                },
                {
                    "pattern": "docs/engine/engine_coverage_report.md",
                    "owner": "mod_state_server.py /validate/engine-coverage",
                    "input": "mod state",
                    "header_marker": True,
                },
                {
                    "pattern": "docs/engine/modifier_visibility_report.md",
                    "owner": "modifier_visibility_audit.py",
                    "input": "mod scripts + engine modifier registry",
                    "header_marker": True,
                },
                {
                    "pattern": "docs/engine/error_log_digest.md",
                    "owner": "game_log_reader.py",
                    "input": "game logs",
                    "header_marker": True,
                },
            ],
            "one_shot_generators": [
                {
                    "pattern": "common/buildings/company_buildings.txt",
                    "owner": "scripts/generators/gen_vanilla_company_buildings.py",
                    "note": "One-shot bootstrap; output is committed and may be hand-edited afterwards.",
                },
                {
                    "pattern": "common/production_method_groups/unique_pm_groups.txt",
                    "owner": "scripts/generators/gen_vanilla_company_buildings.py",
                    "note": "One-shot.",
                },
                {
                    "pattern": "common/production_methods/unique_pms.txt",
                    "owner": "scripts/generators/gen_vanilla_company_buildings.py",
                    "note": "One-shot. Was hand-edited during the 1.13 migration; running the generator would overwrite those edits.",
                },
                {
                    "pattern": "common/company_types/extra_companies_vanilla_updates.txt",
                    "owner": "scripts/generators/gen_vanilla_company_injects.py + scripts/generators/gen_vanilla_company_buildings.py",
                    "note": "Both scripts write here; coordinate runs.",
                },
                {
                    "pattern": "localization/english/te_buildings_l_english.yml",
                    "owner": "scripts/generators/gen_vanilla_company_buildings.py",
                    "note": "One-shot.",
                },
            ],
            "hint": (
                "Treat anything in `auto_generated` as read-only — edit the input "
                "and re-run the generator. `one_shot_generators` are committed "
                "outputs that can be hand-edited but be aware that re-running "
                "the script will overwrite hand edits."
            ),
        }

    def _validate(self, parts, params):
        """GET /validate/engine-coverage — run mod-vs-engine modifier check.

        Cached on first call after each /reload. Use ?refresh=true to force.

        The default report already cross-references the mod's own
        common/modifier_type_definitions/ and Script Values, so mod-registered
        names and script-value scalars no longer surface as unknowns.

        Filters:
          ?filter=vanilla_breakages — kept for backwards compatibility; now a
            no-op since mod-registered modifier types are folded into the
            base `modifiers_set` before classification.
          ?summary=true — return only the file/summary header, no entity lists.
        """
        if not parts:
            return {
                "available": ["engine-coverage", "modifier-visibility"],
                "hint": (
                    "GET /validate/engine-coverage[?summary=true] | "
                    "GET /validate/modifier-visibility[?include_reviewed=true]"
                ),
            }
        check = parts[0]
        if check == "modifier-visibility":
            return self._validate_modifier_visibility(params)
        if check != "engine-coverage":
            raise KeyError(check)
        global _last_validation_report
        force = (params.get("refresh") or ["false"])[0].lower() == "true"
        if force or _last_validation_report is None:
            _last_validation_report = _validate_engine_coverage()
        report = _last_validation_report

        filt = (params.get("filter") or [""])[0]
        summary_only = (params.get("summary") or ["false"])[0].lower() == "true"

        if filt == "vanilla_breakages":
            # Collect mod-defined modifier-type names from the mod's
            # `common/modifier_type_definitions/` parser.
            mod_defined: set[str] = set()
            mod_types = ms.get_data("Modifier Types") if ms else None
            if mod_types:
                mod_defined = set(mod_types.keys())
            unknown = [
                u for u in report.get("unknown_modifiers", [])
                if u["name"] not in mod_defined
            ]
            suspicious = [
                u for u in report.get("suspicious_modifiers", [])
                if u["name"] not in mod_defined
            ]
            mod_defined_count = sum(
                1 for u in report.get("unknown_modifiers", [])
                if u["name"] in mod_defined
            )
            report = {
                **{k: v for k, v in report.items() if k not in ("unknown_modifiers", "suspicious_modifiers", "summary")},
                "summary": {
                    "unknown_modifiers": len(unknown),
                    "suspicious_modifiers": len(suspicious),
                    "mod_defined_excluded": mod_defined_count,
                },
                "unknown_modifiers": unknown,
                "suspicious_modifiers": suspicious,
            }

        if summary_only:
            return {k: v for k, v in report.items() if k not in ("unknown_modifiers", "suspicious_modifiers")}
        return report

    def _validate_modifier_visibility(self, params):
        """GET /validate/modifier-visibility — flag modifier values too small
        to display given the modifier type's `decimals = N` precision.

        Query params:
          ?include_reviewed=true  — include the reviewed-exemptions list in the
                                    response (default: omit, return count only).
          ?summary=true           — return only counts, no per-flag details.
        """
        import modifier_visibility_audit as mva
        result = mva.audit(ms, mod_path=mod_path)
        unrev = [f for f in result.flags if not f.exemption]
        exemp = [f for f in result.flags if f.exemption]

        def _to_dict(f):
            return {
                "file": f.file,
                "line": f.line,
                "modifier": f.modifier,
                "value": f.value,
                "value_float": f.value_float,
                "decimals": f.decimals,
                "percent": f.percent,
                "min_visible": f.min_visible,
                **({"exemption": f.exemption} if f.exemption else {}),
            }

        summary = {
            "files_audited": result.coverage.get("files_audited", 0),
            "modifiers_in_registry_with_decimals": result.coverage.get(
                "modifiers_in_registry_with_decimals", 0
            ),
            "registry_hits": result.coverage.get("registry_hits", 0),
            "flagged": len(unrev),
            "reviewed": len(exemp),
        }
        summary_only = (params.get("summary") or ["false"])[0].lower() == "true"
        if summary_only:
            return {"summary": summary}
        include_reviewed = (params.get("include_reviewed") or ["false"])[0].lower() == "true"
        out = {
            "summary": summary,
            "flagged": [_to_dict(f) for f in unrev],
        }
        if include_reviewed:
            out["reviewed"] = [_to_dict(f) for f in exemp]
        return out

    def _duplicate_images(self, params):
        """GET /duplicate-images — flag images reused across entities of types
        where vanilla treats one image per entity (Buildings, Goods, Decrees,
        Technologies, Interest Groups, Laws).

        Query params:
          ?include_vanilla=true     — include clusters with no mod-side entities.
          ?include_allowlisted=true — emit the `allowlisted` array.
          ?type=Buildings           — restrict scan (repeatable, comma-separated).
          ?format=text              — human-readable rendering wrapped in {"text": ...}.

        Allowlist file: common/_meta/duplicate_image_allowlist.yml.
        """
        include_vanilla = (params.get("include_vanilla") or ["false"])[0].lower() == "true"
        include_allowlisted = (params.get("include_allowlisted") or ["false"])[0].lower() == "true"
        types_raw = params.get("type") or []
        types: list[str] | None = None
        if types_raw:
            types = []
            for t in types_raw:
                types.extend(s.strip() for s in t.split(",") if s.strip())
            types = types or None

        report = _find_duplicate_images(
            include_vanilla=include_vanilla,
            types=types,
            include_allowlisted=include_allowlisted,
        )

        fmt = (params.get("format") or [""])[0]
        if fmt == "text":
            return {"text": _render_duplicate_images_text(report,
                                                          include_allowlisted=include_allowlisted)}
        return report

    def _modifier_pattern_expand(self, pattern, params):
        """Instantiate a pattern with a given placeholder value."""
        compiled = _compile_pattern(pattern)
        if not compiled:
            return {"error": f"Pattern lacks a {{placeholder}} token: {pattern}"}
        prefix, placeholder, suffix = compiled
        value = (params.get(placeholder) or [None])[0]
        if not value:
            return {"error": f"Provide ?{placeholder}=<value>"}
        concrete = pattern.replace("{" + placeholder + "}", value)
        members = pattern_index.get(pattern, {})
        existing = members.get(value)
        return {
            "pattern": pattern,
            "placeholder": placeholder,
            "value": value,
            "concrete_name": concrete,
            "exists_in_engine_docs": existing is not None,
            "engine_doc_entry": existing,
        }

    def _raw(self, parts):
        """GET /raw/<EntityType>[/<id>]  - raw parsed data."""
        if not parts:
            return list(ms.mod_parsers.keys())
        etype = parts[0]
        data = ms.get_data(etype)
        if data is None:
            raise KeyError(etype)
        if len(parts) > 1:
            eid = parts[1]
            if eid not in data:
                raise KeyError(eid)
            return serialize(data[eid])
        return serialize(data)

    def _localize(self, parts):
        """GET /localize/<key>  - localize a game key to display text."""
        if not parts:
            return {"error": "Provide a key, e.g. /localize/law_monarchy"}
        key = parts[0]
        result = {"key": key, "name": ms.localize(key)}
        desc = ms.get_description(key)
        if desc is not None:
            result["description"] = desc
        return result

    def _unlocalize(self, parts):
        """GET /unlocalize/<text>  - reverse-localize display text to keys."""
        if not parts:
            return {"error": "Provide display text, e.g. /unlocalize/Monarchy"}
        text = parts[0]
        keys = ms.unlocalize(text)
        return {"text": text, "keys": keys}

    def _search(self, params):
        """GET /search?q=<query>[&type=<EntityType>][&limit=<n>]"""
        query = params.get("q", [""])[0].lower()
        if not query:
            return {"error": "Provide ?q=search_term"}
        etype_filter = params.get("type", [None])[0]
        limit = int(params.get("limit", ["50"])[0])

        entities = []
        etypes = [etype_filter] if etype_filter else list(ms.mod_parsers.keys())
        for et in etypes:
            data = ms.get_data(et)
            if data is None:
                continue
            for eid in data:
                if query in eid.lower() or query in ms.localize(eid).lower():
                    entities.append({"type": et, "id": eid, "name": ms.localize(eid)})
                    if len(entities) >= limit:
                        break

        loc_results = ms.search_localization(query, limit=limit)
        return {"entities": entities, "localization": loc_results}

    # ---- structured: laws -------------------------------------------------
    def _laws(self, parts):
        """GET /laws[/<law_id>]"""
        laws = ms.get_data("Laws")
        if not laws:
            return {"error": "Laws data not loaded"}

        if parts:
            law_id = parts[0]
            if law_id not in laws:
                raise KeyError(law_id)
            return self._format_law_detail(law_id, laws[law_id])

        groups: dict = {}
        for law_id, raw in laws.items():
            ld = get_entity_data(raw)
            group_id = get_field(ld, "group", "unknown")
            group_name = ms.localize(group_id)
            if group_name not in groups:
                groups[group_name] = {"group_id": group_id, "laws": []}
            groups[group_name]["laws"].append(self._format_law_summary(law_id, ld))
        return groups

    def _format_law_summary(self, law_id, ld):
        info: dict = {"type": "Laws", "id": law_id, "name": ms.localize(law_id)}
        tech = get_field(ld, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": ms.localize(tech[0])}
        parent = get_field(ld, "parent")
        if parent:
            info["parent"] = {"type": "Laws", "id": parent, "name": ms.localize(parent)}
        return info

    def _format_law_detail(self, law_id, raw):
        ld = get_entity_data(raw)
        group_id = get_field(ld, "group", "")
        info: dict = {
            "type": "Laws",
            "id": law_id,
            "name": ms.localize(law_id),
            "group_id": group_id,
            "group_name": ms.localize(group_id),
        }
        tech = get_field(ld, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": ms.localize(tech[0])}
        parent = get_field(ld, "parent")
        if parent:
            info["parent"] = {"type": "Laws", "id": parent, "name": ms.localize(parent)}
        modifiers = get_field(ld, "modifier")
        if modifiers and isinstance(modifiers, dict):
            info["modifiers"] = {}
            for k, v in modifiers.items():
                info["modifiers"][k] = v[1] if isinstance(v, tuple) else v
        info["raw"] = serialize(raw)
        return info

    # ---- structured: technologies -----------------------------------------
    def _technologies(self, parts, params):
        """GET /technologies[/<tech_id>][?era=<n>]"""
        techs = ms.get_data("Technologies")
        if not techs:
            return {"error": "Technologies data not loaded"}

        if parts:
            tid = parts[0]
            if tid not in techs:
                raise KeyError(tid)
            return self._format_tech_detail(tid, techs[tid])

        era_filter = params.get("era", [None])[0]
        era_filter = int(era_filter) if era_filter else None

        by_era: dict = defaultdict(list)
        for tid, raw in techs.items():
            td = get_entity_data(raw)
            era_str = get_field(td, "era", "era_0")
            era_num = int(era_str.split("_")[-1])
            if era_filter is not None and era_num != era_filter:
                continue
            by_era[era_num].append(self._format_tech_summary(tid, td))

        return {
            f"era_{era}": {"count": len(tlist), "technologies": tlist}
            for era, tlist in sorted(by_era.items())
        }

    def _format_tech_summary(self, tid, td):
        info: dict = {"type": "Technologies", "id": tid, "name": ms.localize(tid)}
        desc = ms.get_description(tid)
        if desc:
            info["description"] = desc
        era_str = get_field(td, "era", "era_0")
        info["era"] = int(era_str.split("_")[-1])
        tech = get_field(td, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technologies"] = [
                {"type": "Technologies", "id": t, "name": ms.localize(t)} for t in tech
            ]
        return info

    def _format_tech_detail(self, tid, raw):
        info = self._format_tech_summary(tid, get_entity_data(raw))
        info["raw"] = serialize(raw)
        return info

    # ---- structured: buildings --------------------------------------------
    def _buildings(self, parts, params=None):
        """GET /buildings[/<building_id>][?detail=true]

        /buildings              - summary list (id, name, pm_group_count)
        /buildings?detail=true  - full detail for ALL buildings (includes PM groups & PMs)
        /buildings/<id>         - full detail for one building
        /buildings/pm-map       - compact building→PM mapping for code generators
        """
        buildings = ms.get_data("Buildings")
        if not buildings:
            return {"error": "Buildings data not loaded"}

        if parts:
            if parts[0] == "pm-map":
                return self._buildings_pm_map(buildings)
            bid = parts[0]
            if bid not in buildings:
                raise KeyError(bid)
            return self._format_building_detail(bid, buildings[bid])

        params = params or {}
        if params.get("detail", ["false"])[0].lower() in ("true", "1", "yes"):
            return [
                self._format_building_detail(bid, raw)
                for bid, raw in buildings.items()
            ]

        return [
            self._format_building_summary(bid, raw)
            for bid, raw in buildings.items()
        ]

    def _buildings_pm_map(self, buildings):
        """GET /buildings/pm-map - compact building→PM group→PM mapping.

        Returns {building_id: [[pm_id, ...], [pm_id, ...], ...], ...}
        where each inner list is the PMs for one PM group, in order.
        Useful for code generators that need the full mapping without per-building calls.
        """
        pmg_data = ms.get_data("PM Groups") or {}
        result = {}
        for bid, raw in buildings.items():
            bd = get_entity_data(raw)
            pmg_ids = get_field(bd, "production_method_groups")
            if not pmg_ids or not isinstance(pmg_ids, list):
                result[bid] = []
                continue
            groups = []
            for pmg_id in pmg_ids:
                if pmg_id not in pmg_data:
                    groups.append([])
                    continue
                pmg_inner = get_entity_data(pmg_data[pmg_id])
                pm_ids = get_field(pmg_inner, "production_methods")
                groups.append(pm_ids if pm_ids and isinstance(pm_ids, list) else [])
            result[bid] = groups
        return result

    def _format_building_summary(self, bid, raw):
        bd = get_entity_data(raw)
        info: dict = {"type": "Buildings", "id": bid, "name": ms.localize(bid)}
        tech = get_field(bd, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": ms.localize(tech[0])}
        pmg_ids = get_field(bd, "production_method_groups")
        if pmg_ids and isinstance(pmg_ids, list):
            info["pm_group_count"] = len(pmg_ids)
        return info

    def _format_building_detail(self, bid, raw):
        bd = get_entity_data(raw)
        info: dict = {"type": "Buildings", "id": bid, "name": ms.localize(bid)}
        tech = get_field(bd, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": ms.localize(tech[0])}

        pmg_data = ms.get_data("PM Groups")
        pm_data = ms.get_data("PMs")
        pmg_ids = get_field(bd, "production_method_groups")
        if pmg_ids and isinstance(pmg_ids, list) and pmg_data and pm_data:
            info["pm_groups"] = []
            for pmg_id in pmg_ids:
                pmg_entry: dict = {
                    "type": "PM Groups", "id": pmg_id, "name": ms.localize(pmg_id),
                }
                if pmg_id in pmg_data:
                    pmg_inner = get_entity_data(pmg_data[pmg_id])
                    pm_ids = get_field(pmg_inner, "production_methods")
                    if pm_ids and isinstance(pm_ids, list):
                        pmg_entry["production_methods"] = [
                            {"type": "PMs", "id": pid, "name": ms.localize(pid)}
                            for pid in pm_ids
                        ]
                info["pm_groups"].append(pmg_entry)

        info["raw"] = serialize(raw)
        return info

    # ---- structured: goods ------------------------------------------------
    def _goods(self):
        """GET /goods"""
        goods = ms.get_data("Goods")
        if not goods:
            return {"error": "Goods data not loaded"}
        return [{"type": "Goods", "id": gid, "name": ms.localize(gid)} for gid in goods]

    # ---- structured: combat units -----------------------------------------
    def _combat_units(self):
        """GET /combat-units"""
        groups = ms.get_data("Combat Unit Groups")
        types = ms.get_data("Combat Unit Types")
        if not groups or not types:
            return {"error": "Combat unit data not loaded"}

        by_group: dict = defaultdict(list)
        for tid, raw in types.items():
            td = get_entity_data(raw)
            gid = get_field(td, "group", "unknown")
            unit_info: dict = {
                "type": "Combat Unit Types", "id": tid, "name": ms.localize(tid),
            }
            tech = get_field(td, "unlocking_technologies")
            if tech and isinstance(tech, list) and tech:
                unit_info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": ms.localize(tech[0])}
            by_group[gid].append(unit_info)

        return {
            gid: {"name": ms.localize(gid), "units": units}
            for gid, units in by_group.items()
        }

    # ---- structured: ideologies -------------------------------------------
    def _ideologies(self, parts):
        """GET /ideologies[/<ideology_id>]"""
        ideologies = ms.get_data("Ideologies")
        if not ideologies:
            return {"error": "Ideologies data not loaded"}
        if parts:
            iid = parts[0]
            if iid not in ideologies:
                raise KeyError(iid)
            return {
                "type": "Ideologies", "id": iid,
                "name": ms.localize(iid), "raw": serialize(ideologies[iid]),
            }
        return [
            {"type": "Ideologies", "id": iid, "name": ms.localize(iid)}
            for iid in ideologies
        ]

    # ---- analytical: references -------------------------------------------
    def _references(self, parts):
        """GET /references/<key>  - find all entities that reference a given key."""
        if not parts:
            return {"error": "Provide a key, e.g. /references/nuclear_fission"}
        key = parts[0]
        results = defaultdict(list)
        for etype in ms.mod_parsers:
            data = ms.get_data(etype)
            if not data:
                continue
            for eid, raw in data.items():
                if _data_contains_string(raw, key):
                    results[etype].append(
                        {"type": etype, "id": eid, "name": ms.localize(eid)}
                    )
        return dict(results) if results else {"message": f"No references found for '{key}'"}

    # ---- analytical: tech tree --------------------------------------------
    def _tech_tree(self, parts):
        """GET /tech-tree/<tech_id>  - prerequisite chain + everything unlocked."""
        if not parts:
            return {"error": "Provide a tech ID, e.g. /tech-tree/nuclear_fission"}
        tid = parts[0]
        techs = ms.get_data("Technologies")
        if not techs:
            return {"error": "Technologies data not loaded"}
        if tid not in techs:
            raise KeyError(tid)

        # Recursive prerequisites
        prereqs = []
        visited = set()
        self._collect_prereqs(tid, techs, prereqs, visited)

        # Everything unlocked by this tech
        unlocked = self._find_unlocked_by_tech(tid)

        td = get_entity_data(techs[tid])
        era_str = get_field(td, "era", "era_0")
        return {
            "type": "Technologies",
            "id": tid,
            "name": ms.localize(tid),
            "era": int(era_str.split("_")[-1]),
            "prerequisites": prereqs,
            "unlocks": unlocked,
        }

    def _collect_prereqs(self, tid, techs, prereqs, visited):
        """Recursively collect all prerequisite technologies."""
        if tid in visited:
            return
        visited.add(tid)
        raw = techs.get(tid)
        if not raw:
            return
        td = get_entity_data(raw)
        parent_techs = get_field(td, "unlocking_technologies")
        if parent_techs and isinstance(parent_techs, list):
            for pt in parent_techs:
                if pt not in visited:
                    self._collect_prereqs(pt, techs, prereqs, visited)
                    era_str = "era_0"
                    pt_raw = techs.get(pt)
                    if pt_raw:
                        pt_td = get_entity_data(pt_raw)
                        era_str = get_field(pt_td, "era", "era_0")
                    prereqs.append({
                        "type": "Technologies",
                        "id": pt,
                        "name": ms.localize(pt),
                        "era": int(era_str.split("_")[-1]),
                    })

    def _find_unlocked_by_tech(self, tid):
        """Find all entities unlocked by a technology across all entity types.

        Each entry carries a `type` field matching its mod_parsers key, so the
        centralized `?annotate=<name>` post-processor in route() picks them up
        automatically (e.g. PM entries gain balance flags when the request
        includes ?annotate=balance).
        """
        unlocked = defaultdict(list)
        for etype in ms.mod_parsers:
            data = ms.get_data(etype)
            if not data:
                continue
            for eid, raw in data.items():
                ed = get_entity_data(raw)
                ut = get_field(ed, "unlocking_technologies")
                if ut and isinstance(ut, list) and tid in ut:
                    unlocked[etype].append(
                        {"type": etype, "id": eid, "name": ms.localize(eid)}
                    )
        return dict(unlocked)

    # ---- analytical: modifier search --------------------------------------
    def _modifier_search(self, params):
        """GET /modifier-search?q=<pattern>  - find modifier field names across entities."""
        query = params.get("q", [""])[0].lower()
        if not query:
            return {"error": "Provide ?q=search_pattern"}
        limit = int(params.get("limit", ["100"])[0])

        results = []
        seen = set()
        for etype in ms.mod_parsers:
            data = ms.get_data(etype)
            if not data:
                continue
            for eid, raw in data.items():
                modifiers = _extract_modifier_fields(raw)
                matching = {k: v for k, v in modifiers.items() if query in k.lower()}
                if matching:
                    results.append({
                        "type": etype,
                        "id": eid,
                        "name": ms.localize(eid),
                        "modifiers": matching,
                    })
                    for k in matching:
                        seen.add(k)
                    if len(results) >= limit:
                        break
            if len(results) >= limit:
                break
        return {
            "matching_modifier_names": sorted(seen),
            "entity_count": len(results),
            "entities": results,
        }

    # ---- analytical: unlocked-by ------------------------------------------
    def _unlocked_by(self, parts):
        """GET /unlocked-by/<tech_id>  - all entities unlocked by a technology."""
        if not parts:
            return {"error": "Provide a tech ID, e.g. /unlocked-by/nuclear_fission"}
        tid = parts[0]
        techs = ms.get_data("Technologies")
        if techs and tid not in techs:
            raise KeyError(tid)
        return self._find_unlocked_by_tech(tid)

    # ---- analytical: tech-unlocks (bulk inverted index) -------------------
    def _tech_unlocks(self, parts, params):
        """GET /tech-unlocks                          - bulk inverted index
        GET /tech-unlocks/<tech_id>               - single-tech entry
        ?source=mod|vanilla|all  (default mod)    - which side of the tree
        ?era=era_6  / ?eras=era_6,era_7           - filter by source tech's era
        ?summary=true                             - drop by_type lists, keep summary
        ?refresh=true                             - rebuild the index cache

        For per-entry annotation (e.g. PM balance flags), append the
        universal `?annotate=<name>[,<name>...]` or `?annotate=all` —
        applied by the centralized post-processor in route().
        """
        global _tech_unlocks_index_cache
        force = (params.get("refresh") or ["false"])[0].lower() == "true"
        source = (params.get("source") or ["mod"])[0].lower()
        era_param = params.get("era", [None])[0]
        eras_param = params.get("eras", [None])[0]
        summary_only = (params.get("summary") or ["false"])[0].lower() == "true"

        # Build (and cache) the full mod-only index. Vanilla side is opt-in
        # via ?source=vanilla|all and rebuilds each request — vanilla data
        # rarely changes during a session so we don't cache it separately.
        if force or _tech_unlocks_index_cache is None:
            _tech_unlocks_index_cache = tech_unlocks_lib.build_tech_unlock_index(
                Path(mod_path),
            )

        # Combine mod + vanilla as requested.
        index: dict[str, dict] = {}
        if source in ("mod", "all"):
            for tid, rec in _tech_unlocks_index_cache.items():
                index[tid] = self._copy_unlocks_record(rec)
        if source in ("vanilla", "all"):
            vanilla_root = Path(base_game_path) / "game" / "common"
            vanilla_idx = tech_unlocks_lib.build_tech_unlock_index(
                Path(mod_path),
                include_vanilla=True,
                vanilla_common_root=vanilla_root,
            )
            for tid, rec in vanilla_idx.items():
                if source == "vanilla":
                    # Filter to vanilla-source entries only.
                    rec = self._filter_unlocks_by_source(rec, "vanilla")
                    if rec["n_total"] == 0:
                        continue
                merged = index.get(tid)
                if merged is None:
                    index[tid] = self._copy_unlocks_record(rec)
                else:
                    self._merge_unlocks_records(merged, rec, source_filter="vanilla")

        # Era filter — applied to the source tech, not the unlocked entries.
        wanted_eras = self._collect_wanted_eras(era_param, eras_param)
        if wanted_eras:
            techs = ms.get_data("Technologies") or {}
            kept = {}
            for tid, rec in index.items():
                td = techs.get(tid)
                if td is None:
                    continue
                era_str = get_field(get_entity_data(td), "era", "era_0")
                if era_str in wanted_eras:
                    kept[tid] = rec
            index = kept

        if parts:
            tid = parts[0]
            rec = index.get(tid)
            if rec is None:
                # Empty record so callers can still see the shape.
                rec = {"by_type": {}, "summary": {}, "n_total": 0}
            if summary_only:
                rec = {"summary": rec["summary"], "n_total": rec["n_total"]}
            return rec

        if summary_only:
            return {
                tid: {"summary": rec["summary"], "n_total": rec["n_total"]}
                for tid, rec in index.items()
            }
        return index

    @staticmethod
    def _copy_unlocks_record(rec: dict) -> dict:
        return {
            "by_type": {k: list(v) for k, v in rec["by_type"].items()},
            "summary": dict(rec["summary"]),
            "n_total": rec["n_total"],
        }

    @staticmethod
    def _filter_unlocks_by_source(rec: dict, src: str) -> dict:
        out = {"by_type": {}, "summary": {}, "n_total": 0}
        for etype, entries in rec["by_type"].items():
            kept = [e for e in entries if e.get("source") == src]
            if kept:
                out["by_type"][etype] = kept
                out["summary"][etype] = len(kept)
                out["n_total"] += len(kept)
        return out

    @staticmethod
    def _merge_unlocks_records(dst: dict, src: dict, source_filter: str | None = None) -> None:
        """Merge `src` into `dst` in place. If `source_filter` is set,
        only entries whose `source` matches it are merged (used to avoid
        double-counting when ?source=all combines mod + vanilla)."""
        for etype, entries in src["by_type"].items():
            for e in entries:
                if source_filter and e.get("source") != source_filter:
                    continue
                dst["by_type"].setdefault(etype, []).append(e)
                dst["summary"][etype] = dst["summary"].get(etype, 0) + 1
                dst["n_total"] += 1

    @staticmethod
    def _collect_wanted_eras(era_param: str | None, eras_param: str | None) -> set[str]:
        out: set[str] = set()
        if era_param:
            out.add(era_param if era_param.startswith("era_") else f"era_{era_param}")
        if eras_param:
            for e in eras_param.split(","):
                e = e.strip()
                if not e:
                    continue
                out.add(e if e.startswith("era_") else f"era_{e}")
        return out

    # ---- analytical: annotators -------------------------------------------
    def _annotators(self):
        """GET /annotators  - list every registered annotator and its
        produced field names. Use to discover what `?annotate=<name>`
        values are valid against entity-listing endpoints."""
        return {
            "annotators": [
                {
                    "name": a.name,
                    "entity_type": a.entity_type,
                    "fields": list(a.fields),
                    "description": a.description,
                }
                for a in sorted(
                    annotators.all_registered(),
                    key=lambda a: (a.entity_type, a.name),
                )
            ],
        }

    # ---- analytical: filter -----------------------------------------------
    def _filter(self, parts, params):
        """GET /filter/<EntityType>?field=<name>&value=<val>
        Filter entities by field value. Supports:
          field=<name>&value=<val>    substring match on field value
          field=has:<name>            check field existence
        """
        if not parts:
            return {"error": "Provide entity type, e.g. /filter/Technologies?field=era&value=era_5"}
        etype = parts[0]
        data = ms.get_data(etype)
        if data is None:
            raise KeyError(etype)

        field = params.get("field", [""])[0]
        value = params.get("value", [""])[0].lower()
        limit = int(params.get("limit", ["200"])[0])

        if not field:
            return {"error": "Provide ?field=<name> (and optionally &value=<val>)"}

        # has:<field> - existence check
        check_exists = field.startswith("has:")
        if check_exists:
            field = field[4:]

        results = []
        for eid, raw in data.items():
            ed = get_entity_data(raw)
            fv = get_field(ed, field)
            if check_exists:
                if fv is not None:
                    results.append({"type": etype, "id": eid, "name": ms.localize(eid)})
            else:
                if fv is not None:
                    fv_str = str(fv).lower() if not isinstance(fv, list) else " ".join(str(x) for x in fv).lower()
                    if value in fv_str:
                        results.append({
                            "type": etype, "id": eid, "name": ms.localize(eid),
                            field: serialize(fv),
                        })
            if len(results) >= limit:
                break
        return {"type": etype, "field": field, "count": len(results), "results": results}

    # ---- structured: events -----------------------------------------------
    def _events(self, parts, params):
        """GET /events              - list all events with type and image
        GET /events/<event_id>   - detail for one event
        GET /events?image=<name> - filter events by image/video
        GET /events?type=<type>  - filter by event type (country_event, etc.)
        """
        events = ms.get_data("Events")
        if not events:
            return {"error": "Events data not loaded"}

        if parts:
            eid = parts[0]
            if eid not in events:
                raise KeyError(eid)
            return self._format_event_detail(eid, events[eid])

        image_filter = params.get("image", [None])[0]
        type_filter = params.get("type", [None])[0]
        limit = int(params.get("limit", ["500"])[0])

        results = []
        for eid, raw in events.items():
            if eid == "namespace":
                continue
            ed = get_entity_data(raw)
            info = self._format_event_summary(eid, ed)
            if type_filter and info.get("type") != type_filter:
                continue
            if image_filter:
                img = info.get("image", "")
                vid = info.get("video", "")
                if image_filter.lower() not in img.lower() and image_filter.lower() not in vid.lower():
                    continue
            results.append(info)
            if len(results) >= limit:
                break
        return {"count": len(results), "events": results}

    def _format_event_summary(self, eid, ed):
        # Events keep their pre-existing `type` field (country_event /
        # state_event / etc.) for backward compatibility with /events?type=
        # filtering. Tagging events with `type="Events"` for the universal
        # annotator post-processor would clobber that meaning. If/when an
        # annotator targets events, rename this field to `event_type` here
        # and in the filter logic at the same time.
        info = {"id": eid, "name": ms.localize(eid + ".t")}
        etype = get_field(ed, "type")
        if etype:
            info["type"] = etype
        event_image = get_field(ed, "event_image")
        if event_image and isinstance(event_image, dict):
            video = get_field(event_image, "video")
            if video:
                info["video"] = video.strip('"')
            texture = get_field(event_image, "texture")
            if texture:
                info["image"] = texture.strip('"')
        icon = get_field(ed, "icon")
        if icon:
            info["icon"] = icon.strip('"')
        return info

    def _format_event_detail(self, eid, raw):
        ed = get_entity_data(raw)
        info = self._format_event_summary(eid, ed)
        info["title_key"] = eid + ".t"
        info["desc_key"] = eid + ".d"
        # Collect option keys
        options = []
        if isinstance(ed, dict):
            for key in ed:
                if key == "option":
                    opt_data = get_field(ed, "option")
                    if isinstance(opt_data, dict):
                        name = get_field(opt_data, "name")
                        if name:
                            options.append(name)
                    elif isinstance(opt_data, list):
                        for opt in opt_data:
                            if isinstance(opt, dict):
                                name = get_field(opt, "name")
                                if name:
                                    options.append(name)
        info["options"] = options
        info["raw"] = serialize(raw)
        return info

    # ---- analytical: event balance ----------------------------------------
    def _event_balance(self, parts, params):
        """GET /event-balance/<event_id>            - annotate one event's options
        GET /event-balance?ids=<id>,<id>,…         - annotate a comma-separated list
        GET /event-balance?prefix=<namespace>      - annotate every event whose id starts with prefix
        GET /event-balance?file=events/foo.txt     - annotate every event declared in a file
        GET /event-balance/issues[?mode=&threshold=&prefix=&file=]
                                                   - audit for dominated options (see _event_balance_issues)
        Optional: ?format=text  to get a human-readable rendering instead of JSON.

        For each option, every effect is surfaced. Effects of kind `add_modifier` and
        `add_enactment_modifier` are expanded: the named static modifier is looked up,
        each numeric field is paired with its `color` (good/bad/neutral) from the
        modifier-type definition, and a per-field polarity (positive/negative/neutral)
        is computed from value sign × color.

        The walker descends into `if`/`else_if`/`else`, `random_list`, `every_*` /
        `ordered_*` / `random_*` scope iterators, scope-change keys (`je:je_X`,
        `ig:ig_X`, `s:STATE_X`), `custom_tooltip`, and `hidden_effect`. Skips
        `name`, `default_option`, `ai_chance`, `trigger`. Limitations: counts modifier
        FIELDS not durations or magnitudes; doesn't track scope changes that target
        OTHER countries (a modifier applied to `scope:rival = { ... }` is counted as
        a positive on the player's option even though it benefits the rival); doesn't
        classify non-modifier effects (`add_treasury`, `add_radicals`, `add_loyalists`,
        `add_momentum`, `change_variable`, `change_relations`, scripted effects).
        """
        events = ms.get_data("Events")
        if not events:
            return {"error": "Events data not loaded"}

        fmt = params.get("format", ["json"])[0]

        if parts and parts[0] == "issues":
            return self._event_balance_issues(params, fmt)

        if parts:
            eid = parts[0]
            if eid not in events:
                raise KeyError(eid)
            built = self._build_event_balance(eid, events[eid])
            if fmt == "text":
                return {"text": _render_event_balance_text([built])}
            return built

        ids_param = params.get("ids", [None])[0]
        prefix = params.get("prefix", [None])[0]
        file_param = params.get("file", [None])[0]

        if ids_param:
            ids = [i.strip() for i in ids_param.split(",") if i.strip()]
        elif prefix:
            ids = [eid for eid in events if eid != "namespace" and eid.startswith(prefix)]
        elif file_param:
            extracted, err = _extract_event_ids_from_file(file_param)
            if err:
                return {"error": err}
            ids = extracted
        else:
            return {
                "error": "Provide an event id (e.g. /event-balance/banking_cycle_events.10), "
                         "or ?ids=, ?prefix=, ?file=",
            }

        results = []
        missing = []
        for eid in ids:
            if eid not in events:
                missing.append(eid)
                continue
            results.append(self._build_event_balance(eid, events[eid]))
        if fmt == "text":
            return {"text": _render_event_balance_text(results, missing=missing)}
        return {"count": len(results), "missing": missing, "events": results}

    def _build_event_balance(self, eid, raw):
        ed = get_entity_data(raw)
        info = {
            "id": eid,
            "name": ms.localize(eid + ".t"),
            "title_key": eid + ".t",
        }
        opt_field = ed.get("option") if isinstance(ed, dict) else None
        options_out = []
        for _op, opt in _iter_field_values(opt_field) if opt_field is not None else []:
            options_out.append(self._format_option_balance(eid, opt))
        info["options"] = options_out
        info["totals"] = {
            "options": len(options_out),
            **{
                k: sum(o["polarity_totals"].get(k, 0) for o in options_out)
                for k in ("positive", "negative", "neutral", "unknown")
            },
        }
        return info

    def _format_option_balance(self, eid, opt):
        opt_data = _flatten_entity_data(opt) if not isinstance(opt, dict) else opt
        name_key = get_field(opt_data, "name")
        default_opt = get_field(opt_data, "default_option")
        ai_chance_block = get_field(opt_data, "ai_chance")
        ai_base = None
        if isinstance(ai_chance_block, dict):
            ai_base = get_field(ai_chance_block, "base")
            if ai_base is not None:
                ai_base = _try_float(ai_base) if _try_float(ai_base) is not None else ai_base
        effects = []
        _walk_event_effects(opt_data, [], effects)
        polarity_totals = _summarize_polarity(effects)
        return {
            "name_key": name_key,
            "name": ms.localize(name_key) if name_key else None,
            "default_option": default_opt == "yes",
            "ai_chance_base": ai_base,
            "effects": effects,
            "polarity_totals": polarity_totals,
        }

    def _event_balance_issues(self, params, fmt):
        """GET /event-balance/issues[?mode=strict|soft&threshold=&prefix=&file=&format=text&include_reviewed=]
        Audit every loaded event (or a filtered subset) and flag dominated options.

        mode=strict (default): one option pure-positive and another pure-negative.
        mode=soft: pairwise polarity-count dominance (one option has ≥ as many
        positives AND ≤ as many negatives as another, with combined gap ≥
        threshold; default threshold=2). Catches mixed-vs-mixed cases the strict
        check misses.

        Suppression: a `# REVIEWED YYYY-MM-DD: rationale` comment on the event
        header line (or in the contiguous comment block directly above it) moves
        the event out of `flagged` into a separate `reviewed` list. Use
        `?include_reviewed=true` to surface that list in the JSON response.
        """
        events = ms.get_data("Events")
        if not events:
            return {"error": "Events data not loaded"}

        mode = params.get("mode", ["strict"])[0]
        try:
            threshold = int(params.get("threshold", ["2"])[0])
        except ValueError:
            threshold = 2

        prefix = params.get("prefix", [None])[0]
        file_param = params.get("file", [None])[0]

        if file_param:
            extracted, err = _extract_event_ids_from_file(file_param)
            if err:
                return {"error": err}
            ids = [e for e in extracted if e in events]
        elif prefix:
            ids = [eid for eid in events if eid != "namespace" and eid.startswith(prefix)]
        else:
            ids = [eid for eid in events if eid != "namespace"]

        reviewed_map = _scan_events_for_reviewed_dominance()
        include_reviewed = (params.get("include_reviewed") or ["false"])[0].lower() in ("true", "1", "yes")
        flagged = []
        reviewed_exemptions = []
        for eid in ids:
            built = self._build_event_balance(eid, events[eid])
            if len(built.get("options", [])) < 2:
                continue
            if mode == "soft":
                issue = _find_soft_dominance_issues(built, threshold=threshold)
            else:
                issue = _find_dominance_issues(built)
            if issue:
                rev = reviewed_map.get(eid)
                if rev:
                    issue["reviewed"] = rev
                    reviewed_exemptions.append(issue)
                else:
                    flagged.append(issue)

        result = {
            "mode": mode,
            "threshold": threshold if mode == "soft" else None,
            "scanned": len(ids),
            "flagged_count": len(flagged),
            "flagged": flagged,
            "reviewed_count": len(reviewed_exemptions),
        }
        if include_reviewed:
            result["reviewed"] = reviewed_exemptions
        if fmt == "text":
            return {"text": _render_event_balance_issues_text(len(ids), flagged, mode=mode, reviewed_count=len(reviewed_exemptions))}
        return result

    def _event_magnitude_audit(self, params):
        """GET /event-magnitude-audit — flag hardcoded fast-scaling resource deltas in events.

        Filters:
          ?resource=prestige           — substring match on resource label
          ?event_id=foo.5              — exact match on event id
          ?show_reviewed=true          — include reviewed exemptions in flags list
          ?format=text                 — return the markdown report instead of JSON
        """
        import event_magnitude_audit as ema
        from path_constants import mod_path as _mod_path

        result = ema.audit(ms, mod_path=_mod_path)
        flags = result.flags

        show_reviewed = (params.get("show_reviewed") or ["false"])[0].lower() in ("true", "1", "yes")
        if not show_reviewed:
            flags = [f for f in flags if not f.exemption]
        resource_filter = (params.get("resource") or [None])[0]
        if resource_filter:
            flags = [f for f in flags if resource_filter in f.resource]
        event_filter = (params.get("event_id") or [None])[0]
        if event_filter:
            flags = [f for f in flags if f.event_id == event_filter]

        fmt = (params.get("format") or ["json"])[0]
        if fmt == "text":
            return {"text": ema.render_report(ema.AuditResult(flags=flags, coverage=result.coverage))}

        return {
            "flags": [
                {
                    "file": f.file, "line": f.line, "event_id": f.event_id,
                    "kind": f.kind, "effect": f.effect, "value": f.value,
                    "resource": f.resource, "fix_hint": f.fix_hint,
                    "exemption": f.exemption,
                }
                for f in flags
            ],
            "coverage": result.coverage,
        }

    # ---- structured: institutions -----------------------------------------
    def _institutions(self, parts):
        """GET /institutions[/<institution_id>]  - institution data with modifiers per level."""
        institutions = ms.get_data("Institutions")
        if not institutions:
            return {"error": "Institutions data not loaded"}

        if parts:
            iid = parts[0]
            if iid not in institutions:
                raise KeyError(iid)
            return self._format_institution_detail(iid, institutions[iid])

        return [
            self._format_institution_summary(iid, institutions[iid])
            for iid in institutions
        ]

    def _format_institution_summary(self, iid, raw):
        ed = get_entity_data(raw)
        info = {"type": "Institutions", "id": iid, "name": ms.localize(iid)}
        tech = get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": ms.localize(tech[0])}
        return info

    def _format_institution_detail(self, iid, raw):
        ed = get_entity_data(raw)
        info = {"type": "Institutions", "id": iid, "name": ms.localize(iid)}
        tech = get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": ms.localize(tech[0])}
        # Extract modifier data
        modifier = get_field(ed, "modifier")
        if modifier and isinstance(modifier, dict):
            info["modifier"] = {}
            for k, v in modifier.items():
                info["modifier"][k] = v[1] if isinstance(v, tuple) else v
        info["raw"] = serialize(raw)
        return info

    # ---- structured: production methods -----------------------------------
    def _production_methods(self, parts, params):
        """GET /production-methods                    - list all PMs
        GET /production-methods/<pm_id>           - PM detail with modifiers
        GET /production-methods?building=<bid>    - PMs for a specific building
        """
        pms = ms.get_data("PMs")
        if not pms:
            return {"error": "PMs data not loaded"}

        if parts:
            pid = parts[0]
            if pid not in pms:
                raise KeyError(pid)
            return self._format_pm_detail(pid, pms[pid])

        building_filter = params.get("building", [None])[0]
        if building_filter:
            return self._pms_for_building(building_filter)

        return [
            self._format_pm_summary(pid, pms[pid])
            for pid in pms
        ]

    def _format_pm_summary(self, pid, raw):
        ed = get_entity_data(raw)
        info = {"type": "PMs", "id": pid, "name": ms.localize(pid)}
        tech = get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": ms.localize(tech[0])}
        return info

    def _format_pm_detail(self, pid, raw):
        ed = get_entity_data(raw)
        info = {"type": "PMs", "id": pid, "name": ms.localize(pid)}
        tech = get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": ms.localize(tech[0])}
        # Building modifiers
        for mod_key in ("building_modifiers", "country_modifiers", "state_modifiers"):
            mod_data = get_field(ed, mod_key)
            if mod_data and isinstance(mod_data, dict):
                info[mod_key] = {}
                for section, section_data in mod_data.items():
                    if isinstance(section_data, tuple) and len(section_data) >= 2:
                        section_data = section_data[1]
                    if isinstance(section_data, dict):
                        info[mod_key][section] = {
                            k: v[1] if isinstance(v, tuple) else v
                            for k, v in section_data.items()
                        }
        info["raw"] = serialize(raw)
        return info

    def _pms_for_building(self, building_id):
        """Return all PMs for a specific building, grouped by PM group."""
        buildings = ms.get_data("Buildings")
        pmg_data = ms.get_data("PM Groups")
        pm_data = ms.get_data("PMs")
        if not buildings or not pmg_data or not pm_data:
            return {"error": "Required data not loaded"}
        if building_id not in buildings:
            raise KeyError(building_id)

        bd = get_entity_data(buildings[building_id])
        pmg_ids = get_field(bd, "production_method_groups")
        if not pmg_ids or not isinstance(pmg_ids, list):
            return {"building": building_id, "pm_groups": []}

        result_groups = []
        for pmg_id in pmg_ids:
            group = {
                "type": "PM Groups", "id": pmg_id,
                "name": ms.localize(pmg_id), "pms": [],
            }
            if pmg_id in pmg_data:
                pmg_inner = get_entity_data(pmg_data[pmg_id])
                pm_ids = get_field(pmg_inner, "production_methods")
                if pm_ids and isinstance(pm_ids, list):
                    for pid in pm_ids:
                        if pid in pm_data:
                            group["pms"].append(self._format_pm_detail(pid, pm_data[pid]))
                        else:
                            group["pms"].append({
                                "type": "PMs", "id": pid, "name": ms.localize(pid),
                            })
            result_groups.append(group)
        return {
            "type": "Buildings", "id": building_id,
            "name": ms.localize(building_id), "pm_groups": result_groups,
        }

    # ---- structured: journal entries --------------------------------------
    def _journal_entries(self, parts):
        """GET /journal-entries[/<je_id>]  - journal entry listing or detail."""
        jes = ms.get_data("Journal Entries")
        if not jes:
            return {"error": "Journal Entries data not loaded"}

        if parts:
            jeid = parts[0]
            if jeid not in jes:
                raise KeyError(jeid)
            return self._format_je_detail(jeid, jes[jeid])

        return [
            self._format_je_summary(jeid, jes[jeid])
            for jeid in jes
        ]

    def _format_je_summary(self, jeid, raw):
        ed = get_entity_data(raw)
        info = {"type": "Journal Entries", "id": jeid, "name": ms.localize(jeid)}
        group = get_field(ed, "group")
        if group:
            info["group"] = group
        return info

    def _format_je_detail(self, jeid, raw):
        ed = get_entity_data(raw)
        info = {"type": "Journal Entries", "id": jeid, "name": ms.localize(jeid)}
        group = get_field(ed, "group")
        if group:
            info["group"] = group
        icon = get_field(ed, "icon")
        if icon:
            info["icon"] = icon
        info["raw"] = serialize(raw)
        return info

    # ---- structured: decisions --------------------------------------------
    def _decisions(self, parts):
        """GET /decisions[/<decision_id>]"""
        decisions = ms.get_data("Decisions")
        if not decisions:
            return {"error": "Decisions data not loaded"}

        if parts:
            did = parts[0]
            if did not in decisions:
                raise KeyError(did)
            ed = get_entity_data(decisions[did])
            return {
                "type": "Decisions", "id": did,
                "name": ms.localize(did), "raw": serialize(decisions[did]),
            }

        return [
            {"type": "Decisions", "id": did, "name": ms.localize(did)}
            for did in decisions
        ]

    # ---- structured: script values ----------------------------------------
    def _script_values(self, parts):
        """GET /script-values[/<sv_id>]"""
        svs = ms.get_data("Script Values")
        if not svs:
            return {"error": "Script Values data not loaded"}

        if parts:
            svid = parts[0]
            if svid not in svs:
                raise KeyError(svid)
            return {"type": "Script Values", "id": svid, "raw": serialize(svs[svid])}

        return [{"type": "Script Values", "id": svid} for svid in svs]

    # ---- structured: decrees ----------------------------------------------
    def _decrees(self, parts):
        """GET /decrees[/<decree_id>]"""
        decrees = ms.get_data("Decrees")
        if not decrees:
            return {"error": "Decrees data not loaded"}

        if parts:
            did = parts[0]
            if did not in decrees:
                raise KeyError(did)
            ed = get_entity_data(decrees[did])
            info = {"type": "Decrees", "id": did, "name": ms.localize(did)}
            modifier = get_field(ed, "modifier")
            if modifier and isinstance(modifier, dict):
                info["modifier"] = {
                    k: v[1] if isinstance(v, tuple) else v
                    for k, v in modifier.items()
                }
            info["raw"] = serialize(decrees[did])
            return info

        return [
            {"type": "Decrees", "id": did, "name": ms.localize(did)}
            for did in decrees
        ]

    # ---- structured: on-actions -------------------------------------------
    def _on_actions(self, parts):
        """GET /on-actions[/<on_action_id>]"""
        oas = ms.get_data("On Actions")
        if not oas:
            return {"error": "On Actions data not loaded"}

        if parts:
            oaid = parts[0]
            if oaid not in oas:
                raise KeyError(oaid)
            return {"type": "On Actions", "id": oaid, "raw": serialize(oas[oaid])}

        return [{"type": "On Actions", "id": oaid} for oaid in oas]

    # ---- technology effects -----------------------------------------------
    def _technology_effects(self, parts):
        """GET /technology-effects/<tech_id>
        Returns ALL effects of a technology: direct modifiers, unlocked PMs,
        buildings, combat units, laws, institutions, etc.
        """
        if not parts:
            return {"error": "Provide a tech ID, e.g. /technology-effects/nuclear_fission"}
        tid = parts[0]
        techs = ms.get_data("Technologies")
        if not techs:
            return {"error": "Technologies data not loaded"}
        if tid not in techs:
            raise KeyError(tid)

        td = get_entity_data(techs[tid])
        era_str = get_field(td, "era", "era_0")
        info: dict = {
            "type": "Technologies",
            "id": tid,
            "name": ms.localize(tid),
            "era": int(era_str.split("_")[-1]),
            "description": ms.get_description(tid) or "",
        }

        # Direct modifiers from the tech definition
        modifier = get_field(td, "modifier")
        if modifier and isinstance(modifier, dict):
            info["direct_modifiers"] = {
                k: v[1] if isinstance(v, tuple) else v
                for k, v in modifier.items()
            }
        else:
            info["direct_modifiers"] = {}

        # Prerequisites
        prereqs = get_field(td, "unlocking_technologies")
        if prereqs and isinstance(prereqs, list):
            info["prerequisites"] = [
                {"type": "Technologies", "id": pt, "name": ms.localize(pt)}
                for pt in prereqs
            ]

        # Find everything this tech unlocks across all entity types
        unlocked = {}
        unlock_types = {
            "Buildings": "buildings",
            "PMs": "production_methods",
            "Combat Unit Types": "combat_units",
            "Laws": "laws",
            "Institutions": "institutions",
            "Decisions": "decisions",
            "Journal Entries": "journal_entries",
            "Diplomatic Actions": "diplomatic_actions",
            "Company Types": "company_types",
            "Mobilization Options": "mobilization_options",
        }

        for etype, output_key in unlock_types.items():
            data = ms.get_data(etype)
            if not data:
                continue
            found = []
            for eid, raw in data.items():
                ed = get_entity_data(raw)
                ut = get_field(ed, "unlocking_technologies")
                if ut and isinstance(ut, list) and tid in ut:
                    entry = {"type": etype, "id": eid, "name": ms.localize(eid)}
                    # For PMs, include modifier details
                    if etype == "PMs":
                        for mod_key in ("building_modifiers", "country_modifiers", "state_modifiers"):
                            mod_data = get_field(ed, mod_key)
                            if mod_data and isinstance(mod_data, dict):
                                entry[mod_key] = {}
                                for section, section_data in mod_data.items():
                                    if isinstance(section_data, tuple) and len(section_data) >= 2:
                                        section_data = section_data[1]
                                    if isinstance(section_data, dict):
                                        entry[mod_key][section] = {
                                            k: v[1] if isinstance(v, tuple) else v
                                            for k, v in section_data.items()
                                        }
                    found.append(entry)
            if found:
                unlocked[output_key] = found

        info["unlocks"] = unlocked

        # Find techs that require this one
        dependents = []
        for other_tid, other_raw in techs.items():
            if other_tid == tid:
                continue
            other_td = get_entity_data(other_raw)
            other_prereqs = get_field(other_td, "unlocking_technologies")
            if other_prereqs and isinstance(other_prereqs, list) and tid in other_prereqs:
                other_era = get_field(other_td, "era", "era_0")
                dependents.append({
                    "type": "Technologies",
                    "id": other_tid,
                    "name": ms.localize(other_tid),
                    "era": int(other_era.split("_")[-1]),
                })
        if dependents:
            info["dependent_technologies"] = dependents

        return info

    # ---- engine docs ------------------------------------------------------
    def _engine_docs(self, parts, params):
        """GET /engine-docs                      - list available doc types
        GET /engine-docs/<type>               - list all entries of a type
        GET /engine-docs/<type>?q=<search>    - search entries
        GET /engine-docs/<type>?scope=<scope> - filter by scope
        GET /engine-docs/<type>?mask=<mask>   - filter by mask (modifiers only)
        GET /engine-docs/<type>?origin=mod|vanilla|unknown - filter by origin tag
        GET /engine-docs/<type>?group=true    - group similar entries
        GET /engine-docs/origin/<name>        - which doc type(s) define <name>,
                                                with the full schema entry
                                                (description, example, traits,
                                                reads, scopes, targets, …).
                                                Replaces ad-hoc grep when checking
                                                "does this trigger exist? what
                                                scope? what's the syntax?".
        GET /engine-docs/usage/<name>         - real-world call sites of <name>
                                                from vanilla `common/`. Returns
                                                file:line + a 4-line snippet per
                                                hit. Definitions and trigger-
                                                localization labels are filtered
                                                out by default. Params:
                                                  limit=N (default 5)
                                                  before=N / after=N (context)
                                                  include_defs=true (keep all)
                                                Useful when the docs don't cover
                                                a trigger or you want canonical
                                                argument shapes from real script.
        """
        if not parts:
            return {
                "available_types": list(engine_docs.keys()),
                "counts": {k: len(v) for k, v in engine_docs.items()},
                "source_label": engine_docs_source_label,
            }

        # /engine-docs/origin/<name> — disambiguation lookup with full schema
        if parts[0] == "origin":
            if len(parts) < 2:
                raise KeyError("Usage: /engine-docs/origin/<name>")
            target = parts[1]
            hits = []
            # Fields surfaced per match. Common to all entry types: name, origin.
            # Trigger/effect: description, example, traits, reads, scopes, targets.
            # Modifier: mask, display_name, defined_in, is_*_flags.
            # custom-localization / on-action / event-target: type-specific subset.
            _surfaced_fields = (
                "description", "example", "traits", "reads",
                "scopes", "targets",
                "defined_in", "is_script_only", "is_boolean",
                "mask", "display_name",
                "mod_redeclares", "mod_redeclared_in", "mod_script_only",
                "input_scopes", "output_scopes",
            )
            for dtype, entries in engine_docs.items():
                for e in entries:
                    if e.get("name") == target:
                        match = {
                            "type": dtype,
                            "origin": e.get("origin", "unknown"),
                        }
                        for k in _surfaced_fields:
                            if k in e and e[k] not in (None, "", [], {}):
                                match[k] = e[k]
                        hits.append(match)
            return {
                "name": target,
                "found": len(hits) > 0,
                "matches": hits,
            }

        # /engine-docs/usage/<name> — find real-world usages in vanilla common/.
        # Returns context-bracketed call sites (definition lines and label
        # cross-references in scripted_triggers/trigger_localization are filtered
        # out — usages are always indented inside a block, definitions are at
        # column 0).
        if parts[0] == "usage":
            if len(parts) < 2:
                raise KeyError("Usage: /engine-docs/usage/<name>?limit=N&include_defs=true")
            target = parts[1]
            limit = int(params.get("limit", ["5"])[0])
            include_defs = params.get("include_defs", ["false"])[0].lower() in ("true", "1", "yes")
            context_before = int(params.get("before", ["1"])[0])
            context_after = int(params.get("after", ["3"])[0])
            return _engine_docs_find_usage(
                target,
                limit=limit,
                include_defs=include_defs,
                context_before=context_before,
                context_after=context_after,
            )

        doc_type = parts[0]
        if doc_type not in engine_docs:
            raise KeyError(f"Unknown engine doc type: {doc_type}. Available: {list(engine_docs.keys())}")

        entries = engine_docs[doc_type]
        query = params.get("q", [""])[0].lower()
        scope_filter = params.get("scope", [""])[0].lower()
        mask_filter = params.get("mask", [""])[0].lower()
        origin_filter = params.get("origin", [""])[0].lower()
        do_group = params.get("group", ["false"])[0].lower() in ("true", "1", "yes")
        limit = int(params.get("limit", ["500"])[0])

        # Apply filters
        filtered = entries
        if query:
            filtered = [
                e for e in filtered
                if query in e.get("name", "").lower()
                or query in e.get("description", "").lower()
                or query in e.get("display_name", "").lower()
            ]
        if scope_filter:
            filtered = [
                e for e in filtered
                if scope_filter in [s.lower() for s in e.get("scopes", [])]
                or scope_filter in [s.lower() for s in e.get("input_scopes", [])]
                or scope_filter in [s.lower() for s in e.get("output_scopes", [])]
            ]
        if mask_filter:
            filtered = [
                e for e in filtered
                if mask_filter in e.get("mask", "").lower()
            ]
        if origin_filter:
            filtered = [
                e for e in filtered
                if e.get("origin", "unknown").lower() == origin_filter
            ]

        # Grouping
        if do_group:
            grouped, ungrouped = _group_similar_entries(filtered)
            return {
                "type": doc_type,
                "grouped_patterns": grouped,
                "ungrouped_count": len(ungrouped),
                "ungrouped": ungrouped[:limit],
            }

        return {
            "type": doc_type,
            "count": len(filtered),
            "entries": filtered[:limit],
        }

    # ---- developer reference docs -----------------------------------------
    def _dev_docs(self, parts, params):
        """GET /dev-docs                       - list available docs by directory
        GET /dev-docs/<directory>           - get all docs in a directory
        GET /dev-docs/<dir>/<file>          - get specific doc content
        GET /dev-docs?q=<search>            - search doc contents
        """
        query = params.get("q", [""])[0].lower()

        if not parts and not query:
            # List all docs grouped by directory
            by_dir: dict[str, list] = {}
            for path, doc in dev_reference_docs.items():
                d = doc["directory"]
                if d not in by_dir:
                    by_dir[d] = []
                by_dir[d].append({"filename": doc["filename"], "path": path, "size": doc["size"]})
            return {
                "directories": sorted(by_dir.keys()),
                "count": len(dev_reference_docs),
                "docs_by_directory": {k: by_dir[k] for k in sorted(by_dir.keys())},
            }

        if not parts and query:
            # Search across all docs
            results = []
            for path, doc in dev_reference_docs.items():
                if query in doc["content"].lower():
                    # Find matching lines for context
                    matching_lines = []
                    for i, line in enumerate(doc["content"].splitlines(), 1):
                        if query in line.lower():
                            matching_lines.append({"line": i, "text": line.rstrip()})
                    results.append({
                        "path": path,
                        "directory": doc["directory"],
                        "match_count": len(matching_lines),
                        "matches": matching_lines[:20],
                    })
            return {"query": query, "count": len(results), "results": results}

        # /dev-docs/<path...> — reconstruct path from parts
        req_path = "/".join(parts)

        # Exact match
        if req_path in dev_reference_docs:
            doc = dev_reference_docs[req_path]
            return {"path": doc["path"], "directory": doc["directory"], "content": doc["content"]}

        # Try as directory — list all docs in that dir
        matches = {
            p: d for p, d in dev_reference_docs.items()
            if d["directory"] == req_path or d["directory"].startswith(req_path + "/")
        }
        if matches:
            docs = []
            for p, d in matches.items():
                docs.append({"path": p, "filename": d["filename"], "size": d["size"]})
            # If only one doc in the directory, return its content directly
            if len(docs) == 1:
                single = dev_reference_docs[docs[0]["path"]]
                return {"path": single["path"], "directory": single["directory"], "content": single["content"]}
            return {"directory": req_path, "count": len(docs), "docs": docs}

        raise KeyError(f"No dev doc found for: {req_path}")

    # ---- unlocalized entity detection -------------------------------------

    # Which entity types need localization and the loc-key pattern:
    #   "self"        → entity ID is the loc key
    #   "self+desc"   → entity ID + ID_desc both needed
    #   "event"       → event-style keys (id.t, id.d, id.a …)
    _LOC_SPECS: list[tuple[str, str]] = [
        ("Modifiers",            "self+desc"),
        ("Modifier Types",       "self+desc"),
        ("Technologies",         "self"),
        ("Buildings",            "self"),
        ("Laws",                 "self"),
        ("Law Groups",           "self"),
        ("PMs",                  "self"),
        ("PM Groups",            "self"),
        ("Goods",                "self"),
        ("Institutions",         "self"),
        ("Interest Groups",      "self"),
        ("Character Traits",     "self"),
        ("Decisions",            "self+desc"),
        ("Decrees",              "self+desc"),
        ("Journal Entries",      "self"),
        ("Diplomatic Actions",   "self"),
        ("Diplomatic Plays",     "self"),
        ("Subject Types",        "self"),
        ("Mobilization Options", "self"),
        ("Company Types",        "self"),
        ("Building Groups",      "self"),
        ("Religions",            "self"),
        ("Combat Unit Types",    "self"),
        ("Events",               "event"),
    ]

    def _unlocalized(self, params):
        """GET /unlocalized?type=<EntityType>&mod_only=true
        Find entities with missing localization keys.
        - type:     filter to one entity type (e.g. "Modifiers")
        - mod_only: if "true" (default), skip entities that exist in vanilla
        """
        type_filter = params.get("type", [""])[0]
        mod_only = params.get("mod_only", ["true"])[0].lower() != "false"

        results: dict[str, list] = {}
        total = 0

        for etype, pattern in self._LOC_SPECS:
            if type_filter and etype != type_filter:
                continue
            data = ms.get_data(etype)
            if not data:
                continue

            base_data = (
                ms.base_parsers[etype].data
                if etype in ms.base_parsers
                else {}
            )

            missing: list[dict] = []
            for eid in data:
                # Skip internal parser artefacts
                if eid == "namespace":
                    continue
                # Skip vanilla entities when mod_only is set
                if mod_only and eid in base_data:
                    continue

                missing_keys: list[str] = []
                if pattern == "event":
                    # Events need .t (title) and .d (description)
                    for suffix in [".t", ".d"]:
                        if not ms.has_localization(eid + suffix):
                            missing_keys.append(eid + suffix)
                    # Check options by parsing the event data
                    ed = get_entity_data(data[eid])
                    if isinstance(ed, dict):
                        options = ed.get("option", [])
                        if isinstance(options, dict):
                            options = [options]
                        if isinstance(options, list):
                            for opt in options:
                                if isinstance(opt, dict):
                                    name = get_field(opt, "name")
                                    if name and not ms.has_localization(name):
                                        missing_keys.append(name)
                elif pattern == "self+desc":
                    if not ms.has_localization(eid):
                        missing_keys.append(eid)
                    if not ms.has_localization(eid + "_desc"):
                        missing_keys.append(eid + "_desc")
                else:  # "self"
                    if not ms.has_localization(eid):
                        missing_keys.append(eid)

                if missing_keys:
                    missing.append({
                        "id": eid,
                        "missing_keys": missing_keys,
                    })

            if missing:
                results[etype] = missing
                total += len(missing)

        return {
            "mod_only": mod_only,
            "total_entities_with_missing_loc": total,
            "total_missing_keys": sum(
                len(m) for ents in results.values() for m in ents
                for _ in [None]  # just counting
            ) if False else sum(
                len(e["missing_keys"]) for ents in results.values() for e in ents
            ),
            "by_type": results,
        }

    # ---- response helpers -------------------------------------------------
    def _respond_json(self, data, status=200):
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionAbortedError, BrokenPipeError) as e:
            # Client disconnected while we were writing headers/body. Log at debug and continue.
            logger.debug(f"Client disconnected while writing response: {e}")

    def log_message(self, format, *args):
        # Log requests at DEBUG level to the file (suppresses console spam)
        logger.debug(f"HTTP {args[0] if args else '?'} {args[1] if len(args) > 1 else ''}")


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

# Idempotent transformers run after ModState loads on startup and /reload.
# Each module must expose `regenerate(mod_state)` and finish in well under a
# second. Set VIC3_SKIP_POST_LOAD_GENERATORS=1 to disable while iterating on
# one of these scripts. Failures are logged and skipped — they don't block
# server startup. The /reload?engine_only=true path bypasses _load_mod_state
# entirely, so these don't run there.
POST_LOAD_GENERATORS = [
    ("pop_needs_curves",              "pop_needs_curves"),
    ("apply_ideologies",              "apply_ideologies"),
    ("ig_feminism",                   "ig_feminism"),
    ("pm_costs",                      "pm_costs"),
    ("resources",                     "resources"),
    ("gen_pb_principle_unlock_descs", "gen_pb_principle_unlock_descs"),
    ("gen_un_button_descs",           "gen_un_button_descs"),
    ("gen_law_consistency",           "gen_law_consistency"),
    ("organize_loc",                  "organize_loc"),
    ("event_magnitude_audit",         "event_magnitude_audit"),
    ("modifier_visibility_audit",     "modifier_visibility_audit"),
    ("kill_character_audit",          "kill_character_audit"),
    ("loc_coverage_audit",            "loc_coverage_audit"),
    ("concept_reference_audit",       "concept_reference_audit"),
    ("localization_accessor_audit",   "localization_accessor_audit"),
    ("mod_structure_audit",           "mod_structure_audit"),
    ("gen_event_inventory",           "gen_event_inventory"),
]


# Return-dict keys whose nonzero values indicate "actionable issue surfaced
# by this generator." Audits use a small set of conventional names; if a new
# audit invents one, add it here so the warning fires automatically.
_POST_LOAD_WARN_KEYS = ("unreviewed", "hard_fails")

# Most-recent post-load run's actionable findings. Reset on every
# _run_post_load_generators call. Read by /reload POST handler so callers
# see "the reload succeeded but you have N new sub-threshold modifiers"
# without having to scrape the server log.
_post_load_warnings: list[dict] = []


def _run_post_load_generators(mod_state):
    global _post_load_warnings
    _post_load_warnings = []
    if os.environ.get("VIC3_SKIP_POST_LOAD_GENERATORS"):
        logger.info("[post-load] skipped via VIC3_SKIP_POST_LOAD_GENERATORS")
        return
    for label, module_name in POST_LOAD_GENERATORS:
        t0 = time.monotonic()
        try:
            mod = importlib.import_module(module_name)
            summary = mod.regenerate(mod_state)
            elapsed = time.monotonic() - t0
            warn_counts = {}
            if isinstance(summary, dict):
                for key in _POST_LOAD_WARN_KEYS:
                    val = summary.get(key)
                    if isinstance(val, int) and val > 0:
                        warn_counts[key] = val
            if warn_counts:
                # Compose the warning line in a way that's easy to grep
                # ([post-load WARN] is the marker) and that names every
                # actionable counter, not just the first.
                detail = ", ".join(f"{k}={v}" for k, v in warn_counts.items())
                logger.warning(
                    f"[post-load WARN] {label} surfaced issues: {detail} "
                    f"(see the audit's report under docs/engine/)"
                )
                _post_load_warnings.append({
                    "label": label,
                    "module": module_name,
                    "counts": warn_counts,
                    "summary": summary,
                })
            else:
                logger.info(f"[post-load] {label} ok ({elapsed:.2f}s)")
        except Exception:
            logger.exception(f"[post-load] {label} FAILED — continuing")
    if _post_load_warnings:
        labels = ", ".join(w["label"] for w in _post_load_warnings)
        logger.warning(
            f"[post-load WARN] {len(_post_load_warnings)} audit(s) surfaced "
            f"actionable issues: {labels}"
        )


_MODDING_DIGESTS_REMOTE = "https://github.com/Victoria-3-Modding-Co-op/Modding-Digests.git"


def _ensure_modding_digests_fresh() -> None:
    """Clone (if missing) or fast-forward the Modding-Digests checkout.

    Called once per process from main(); /reload deliberately does not retrigger.
    All git/network failures are warnings — the server starts regardless. Set
    VIC3_SKIP_DIGESTS_FETCH=1 to skip entirely.
    """
    if os.environ.get("VIC3_SKIP_DIGESTS_FETCH"):
        logger.info("[digests] skipped via VIC3_SKIP_DIGESTS_FETCH")
        return
    if not vic3_modding_digests_path:
        logger.info(
            "[digests] vic3_modding_digests_path not configured; skipping fetch. "
            "Set it via paths.local.json (run scripts/setup.py) or $VIC3_MODDING_DIGESTS_REPO."
        )
        return
    target = Path(vic3_modding_digests_path)

    def _short_sha() -> str:
        try:
            r = subprocess.run(
                ["git", "-C", str(target), "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=10, check=True,
            )
            return r.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            return "?"

    t0 = time.monotonic()
    try:
        if not target.exists():
            logger.info(f"[digests] cloning {_MODDING_DIGESTS_REMOTE} -> {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--depth", "50", _MODDING_DIGESTS_REMOTE, str(target)],
                timeout=60, check=True, capture_output=True, text=True,
            )
            logger.info(f"[digests] cloned at {_short_sha()} ({time.monotonic() - t0:.1f}s)")
            return
        if not (target / ".git").exists():
            logger.warning(
                f"[digests] {target} exists but is not a git repo; skipping fetch"
            )
            return
        subprocess.run(
            ["git", "-C", str(target), "fetch", "--quiet", "origin", "main"],
            timeout=30, check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", str(target), "merge", "--ff-only", "--quiet", "origin/main"],
            timeout=30, check=True, capture_output=True, text=True,
        )
        logger.info(f"[digests] up to date at {_short_sha()} ({time.monotonic() - t0:.1f}s)")
    except subprocess.TimeoutExpired as exc:
        logger.warning(f"[digests] git operation timed out ({exc.cmd}); continuing")
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip().splitlines()[-1:] or ["(no stderr)"]
        logger.warning(f"[digests] git failed (exit {exc.returncode}): {stderr[0]}; continuing")
    except OSError as exc:
        logger.warning(f"[digests] git not invokable: {exc}; continuing")


def _load_mod_state():
    global ms, startup_elapsed, _last_validation_report, _tech_unlocks_index_cache
    logger.info("Loading mod state… (this may take a minute)")
    t0 = time.time()
    try:
        ms = ModState(base_game_paths, mod_paths)
    except Exception as e:
        logger.error(f"Failed to initialize ModState: {e}\n{traceback.format_exc()}")
        raise

    # Invalidate per-load caches so stale annotator outputs / inverted-index
    # entries don't leak across reloads.
    _last_validation_report = None
    _tech_unlocks_index_cache = None
    _annotator_compute_cache.clear()

    # Load localization — wrap each call so one bad directory doesn't kill everything
    for loc_dir in [
        os.path.join(base_game_path, "game", "localization", "english"),
        os.path.join(mod_path, "localization", "english"),
        os.path.join(mod_path, "localization", "english", "replace"),
    ]:
        try:
            if os.path.isdir(loc_dir):
                ms.add_localization(loc_dir)
            else:
                logger.warning(f"Localization directory not found: {loc_dir}")
        except Exception as e:
            logger.error(f"Failed to load localization from {loc_dir}: {e}")

    startup_elapsed = time.time() - t0
    logger.info(
        f"Loaded in {startup_elapsed:.1f}s  "
        f"({len(ms.mod_parsers)} entity types, {len(ms.localization)} loc keys)"
    )

    # Load engine documentation
    try:
        _load_engine_docs()
    except Exception as e:
        logger.error(f"Failed to load engine docs: {e}\n{traceback.format_exc()}")

    # Load developer reference docs (.md files from base game)
    try:
        _load_dev_reference_docs()
    except Exception as e:
        logger.error(f"Failed to load dev reference docs: {e}\n{traceback.format_exc()}")

    # Regenerate docs/engine/ text files from the freshly parsed data
    try:
        from mod_state_script import generate_docs
        generate_docs(ms)
    except Exception as e:
        logger.error(f"Failed to regenerate docs: {e}\n{traceback.format_exc()}")

    # Run idempotent transformers that regenerate mod content from configs
    # + vanilla data (e.g. pop_needs_curves, apply_ideologies). See
    # POST_LOAD_GENERATORS above and docs/guides/python_tools.md for details.
    _run_post_load_generators(ms)


def main():
    global _server_start_time

    replace = "--replace" in sys.argv

    # --- Duplicate instance check (before anything else) ---
    if not _ensure_single_instance(replace=replace):
        sys.exit(0)

    # Rotate the log file at each startup so we get a clean session log
    try:
        _file_handler.doRollover()
    except PermissionError:
        # On Windows the old instance may still hold the file; non-fatal
        logger.debug("Could not rotate log (file locked); appending to existing log")

    logger.info(f"=== Mod State Server starting (PID {os.getpid()}) ===")

    # Write PID file and register cleanup
    _write_pid_file()
    import atexit
    atexit.register(_cleanup_pid_file)

    _ensure_modding_digests_fresh()
    _load_mod_state()

    try:
        server = HTTPServer(("127.0.0.1", PORT), ModStateHandler)
    except OSError as e:
        if "address already in use" in str(e).lower() or e.errno == 10048:  # 10048 = WSAEADDRINUSE on Windows
            logger.error(
                f"Port {PORT} is already in use. Another server may have started between our check "
                f"and bind. Check: Invoke-RestMethod http://localhost:{PORT}/status"
            )
            _cleanup_pid_file()
            sys.exit(1)
        raise

    _server_start_time = time.time()
    logger.info(f"Mod-state server running on http://127.0.0.1:{PORT} (PID {os.getpid()})")
    print(f"\nMod-state server running on http://127.0.0.1:{PORT} (PID {os.getpid()})")
    print("Endpoints: /status  /laws  /technologies  /buildings  /goods")
    print("           /combat-units  /ideologies  /keys/<type>  /raw/<type>")
    print("           /localize/<key>  /unlocalize/<text>  /search?q=...")
    print("           /events  /event-balance/<id>?ids=&prefix=&file=&format=text")
    print("           /event-balance/issues?mode=strict|soft&threshold=&prefix=&file=")
    print("           /institutions  /production-methods  /journal-entries")
    print("           /decisions  /script-values  /decrees  /on-actions")
    print("           /references/<key>  /tech-tree/<id>  /modifier-search?q=...")
    print("           /unlocked-by/<tech>  /filter/<type>?field=&value=")
    print("           /technology-effects/<tech>  /engine-docs/<type>?q=&scope=&group=")
    print("           /dev-docs/<dir>  /dev-docs?q=<search>  POST /reload")
    print(f"Log file: {LOG_FILE}")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
    finally:
        _cleanup_pid_file()


if __name__ == "__main__":
    main()
