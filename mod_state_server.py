"""
Mod State Server - persistent HTTP API for querying parsed mod/vanilla data.

Start:  python mod_state_server.py            # normal start (skips if already running)
        python mod_state_server.py --replace   # kill existing instance, take over port

Query:  Invoke-RestMethod http://localhost:8950/status
        Invoke-RestMethod http://localhost:8950/laws
        python mod_state_client.py laws

Logs:   mod_state_server.log (rotated each startup, previous kept as .log.1)
"""

import json
import logging
import logging.handlers
import os
import re
import signal
import socket
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from urllib.request import urlopen
from urllib.error import URLError

from mod_state import ModState
from path_constants import (
    base_game_path,
    doc_path,
    mod_path,
    vanilla_docs_path,
    game_logs_path,
)

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
}

mod_paths = {
    "Building Groups": os.path.join(_MOD_COMMON, "building_groups"),
    "Buildings": os.path.join(_MOD_COMMON, "buildings"),
    "Technologies": os.path.join(_MOD_COMMON, "technology", "technologies"),
    "PM Groups": os.path.join(_MOD_COMMON, "production_method_groups"),
    "PMs": os.path.join(_MOD_COMMON, "production_methods"),
    "Ideologies": os.path.join(_MOD_COMMON, "ideologies"),
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
    """Check if the port is available for binding."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
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
ENGINE_DOCS_DIR = vanilla_docs_path

def _parse_effects_triggers_log(filepath: str) -> list[dict]:
    """Parse effects.log / triggers.log format:
    ## name
    description lines...
    **Supported Scopes**: scope1, scope2
    **Supported Targets**: target1, target2
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
        line = line.rstrip("\n")
        if line.startswith("## "):
            if current:
                current["description"] = current["description"].strip()
                entries.append(current)
            current = {"name": line[3:].strip(), "description": "", "scopes": [], "targets": []}
        elif current:
            if line.startswith("**Supported Scopes**:"):
                scopes_text = line.split(":", 1)[1].strip()
                current["scopes"] = [s.strip() for s in scopes_text.split(",") if s.strip()]
            elif line.startswith("**Supported Targets**:"):
                targets_text = line.split(":", 1)[1].strip()
                current["targets"] = [t.strip() for t in targets_text.split(",") if t.strip()]
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
pattern_catalog: list[dict] = []  # Loaded from common/_meta/modifier_patterns.yml
pattern_index: dict = {}          # {pattern_str: {placeholder_value: engine_doc_entry}}
discovered_patterns: list[dict] = []  # Auto-detected patterns not in catalog
modifier_to_pattern: dict = {}    # {full_modifier_name: (pattern, placeholder_value, source)}

PATTERN_CATALOG_PATH = os.path.join(mod_path, "common", "_meta", "modifier_patterns.yml")
DISCOVERY_MIN_MEMBERS = 3  # auto-discovered patterns need at least this many to register
_last_validation_report: dict | None = None  # cached /validate/engine-coverage output


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
_MODIFIER_SUFFIX_RE = re.compile(r"_(add|mult|max_levels|max_level|set)$")

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
    # Modifier-type definitions ARE the registry, so don't validate names
    # against themselves.
    "Modifier Types",
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

    modifiers_set = {e.get("name", "") for e in engine_docs.get("modifiers", [])}

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
                # Skip scope/value accessors: `modifier:KEY`, `var:KEY`, `c:TAG`,
                # `s:STATE_X`, `scope:saved`, `cu:culture`, etc. These contain
                # a colon and aren't modifier names.
                if ":" in key:
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
        with open(os.path.join(doc_path, "engine_coverage_report.md"), "w", encoding="utf-8") as f:
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


def _load_engine_docs():
    """Parse all engine documentation files into structured data."""
    global engine_docs, engine_docs_sources
    engine_docs = {}
    engine_docs_sources = {}

    doc_files = {
        "effects": ("effects.log", _parse_effects_triggers_log),
        "triggers": ("triggers.log", _parse_effects_triggers_log),
        "modifiers": ("modifiers.log", _parse_modifiers_log),
        "event-targets": ("event_targets.log", _parse_event_targets_log),
        "on-actions": ("on_actions.log", _parse_on_actions_log),
        "custom-localization": ("custom_localization.log", _parse_custom_localization_log),
    }

    for key, (filename, parser_fn) in doc_files.items():
        filepath = os.path.join(ENGINE_DOCS_DIR, filename)
        if os.path.isfile(filepath):
            try:
                engine_docs[key] = parser_fn(filepath)
                engine_docs_sources[key] = filepath
                logger.info(f"Parsed engine doc {filename}: {len(engine_docs[key])} entries")
            except Exception as e:
                logger.error(f"Failed to parse engine doc {filename}: {e}")
                engine_docs[key] = []
        else:
            logger.warning(f"Engine doc not found: {filepath}")
            engine_docs[key] = []

    # Build the pattern catalog + auto-discovery indexes (§3) before rendering
    # the modifier reference, so the renderer can group dynamic patterns.
    try:
        _refresh_pattern_state()
    except Exception as e:
        logger.error(f"Failed to build pattern state: {e}\n{traceback.format_exc()}")

    # Regenerate the engine-doc reference files in docs/
    try:
        from engine_docs_render import render_all as _render_engine_docs
        catalog, index, discovered, vocabs = _build_pattern_data()
        written = _render_engine_docs(
            engine_docs,
            doc_path,
            pattern_catalog=catalog,
            pattern_index=index,
            discovered_patterns=discovered,
            vocabularies=vocabs,
            source_paths=engine_docs_sources,
        )
        logger.info(f"Regenerated {len(written)} engine reference files in {doc_path}")
    except Exception as e:
        logger.error(f"Failed to regenerate engine reference docs: {e}\n{traceback.format_exc()}")

    # Run §4 validation pass and write the Markdown report.
    global _last_validation_report
    try:
        _last_validation_report = _validate_engine_coverage()
        _annotate_validation_with_error_log(_last_validation_report)
        report_md = _render_engine_coverage_md(_last_validation_report)
        with open(os.path.join(doc_path, "engine_coverage_report.md"), "w", encoding="utf-8") as f:
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
        with open(os.path.join(doc_path, "error_log_digest.md"), "w", encoding="utf-8") as f:
            f.write(digest)
        logger.info(f"Wrote error log digest to {doc_path}/error_log_digest.md")
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
            self._respond_json({"error": f"Not found: {exc}"}, 404)
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
                    self._respond_json({"status": "reloaded", "startup_seconds": startup_elapsed})
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
            "filter": lambda: self._filter(rest, params),
            # New structured endpoints
            "events": lambda: self._events(rest, params),
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
        return handler()

    # ---- endpoints --------------------------------------------------------
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
        return {
            "status": "running",
            "pid": os.getpid(),
            "uptime_seconds": round(uptime, 1),
            "startup_seconds": round(startup_elapsed, 1),
            "entity_types": list(ms.mod_parsers.keys()),
            "localization_keys": len(ms.localization),
            "engine_docs_timestamps": engine_mtimes,
            "engine_docs_age_days": age_days,
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
            {"id": eid, "name": ms.localize(eid)}
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
        GET /logs/<family>?dedupe=&dedupe_key=&limit=&offset=&raw=&mod_only=
        """
        from game_log_reader import (
            list_logs, parse_log, filter_mod_only, filter_entries,
            dedupe, summarize, diff_against_backup, cluster_sessions,
        )

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
            mod_only = (params.get("mod_only") or ["true"])[0].lower() == "true"
            current_entries = parse_log(match.path)
            against_entries = parse_log(against_match.path)
            if mod_only:
                current_entries = filter_mod_only(current_entries)
                against_entries = filter_mod_only(against_entries)
            return {
                "current": match.to_dict(),
                "against": against_match.to_dict(),
                "diff": diff_against_backup(current_entries, against_entries),
            }

        # Raw / parsed entries
        entries = parse_log(match.path)
        # mod_only default: true for error/debug, false for the rest
        default_mod_only = "true" if family in ("error", "debug") else "false"
        mod_only = (params.get("mod_only") or [default_mod_only])[0].lower() == "true"
        if mod_only:
            entries = filter_mod_only(entries)
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

    def _validate(self, parts, params):
        """GET /validate/engine-coverage — run mod-vs-engine modifier check.

        Cached on first call after each /reload. Use ?refresh=true to force.
        """
        if not parts:
            return {
                "available": ["engine-coverage"],
                "hint": "GET /validate/engine-coverage",
            }
        check = parts[0]
        if check != "engine-coverage":
            raise KeyError(check)
        global _last_validation_report
        force = (params.get("refresh") or ["false"])[0].lower() == "true"
        if force or _last_validation_report is None:
            _last_validation_report = _validate_engine_coverage()
        return _last_validation_report

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
        info: dict = {"id": law_id, "name": ms.localize(law_id)}
        tech = get_field(ld, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"id": tech[0], "name": ms.localize(tech[0])}
        parent = get_field(ld, "parent")
        if parent:
            info["parent"] = {"id": parent, "name": ms.localize(parent)}
        return info

    def _format_law_detail(self, law_id, raw):
        ld = get_entity_data(raw)
        group_id = get_field(ld, "group", "")
        info: dict = {
            "id": law_id,
            "name": ms.localize(law_id),
            "group_id": group_id,
            "group_name": ms.localize(group_id),
        }
        tech = get_field(ld, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"id": tech[0], "name": ms.localize(tech[0])}
        parent = get_field(ld, "parent")
        if parent:
            info["parent"] = {"id": parent, "name": ms.localize(parent)}
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
        info: dict = {"id": tid, "name": ms.localize(tid)}
        desc = ms.get_description(tid)
        if desc:
            info["description"] = desc
        era_str = get_field(td, "era", "era_0")
        info["era"] = int(era_str.split("_")[-1])
        tech = get_field(td, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technologies"] = [
                {"id": t, "name": ms.localize(t)} for t in tech
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
        info: dict = {"id": bid, "name": ms.localize(bid)}
        tech = get_field(bd, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"id": tech[0], "name": ms.localize(tech[0])}
        pmg_ids = get_field(bd, "production_method_groups")
        if pmg_ids and isinstance(pmg_ids, list):
            info["pm_group_count"] = len(pmg_ids)
        return info

    def _format_building_detail(self, bid, raw):
        bd = get_entity_data(raw)
        info: dict = {"id": bid, "name": ms.localize(bid)}
        tech = get_field(bd, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"id": tech[0], "name": ms.localize(tech[0])}

        pmg_data = ms.get_data("PM Groups")
        pm_data = ms.get_data("PMs")
        pmg_ids = get_field(bd, "production_method_groups")
        if pmg_ids and isinstance(pmg_ids, list) and pmg_data and pm_data:
            info["pm_groups"] = []
            for pmg_id in pmg_ids:
                pmg_entry: dict = {"id": pmg_id, "name": ms.localize(pmg_id)}
                if pmg_id in pmg_data:
                    pmg_inner = get_entity_data(pmg_data[pmg_id])
                    pm_ids = get_field(pmg_inner, "production_methods")
                    if pm_ids and isinstance(pm_ids, list):
                        pmg_entry["production_methods"] = [
                            {"id": pid, "name": ms.localize(pid)} for pid in pm_ids
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
        return [{"id": gid, "name": ms.localize(gid)} for gid in goods]

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
            unit_info: dict = {"id": tid, "name": ms.localize(tid)}
            tech = get_field(td, "unlocking_technologies")
            if tech and isinstance(tech, list) and tech:
                unit_info["unlocking_technology"] = {"id": tech[0], "name": ms.localize(tech[0])}
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
            return {"id": iid, "name": ms.localize(iid), "raw": serialize(ideologies[iid])}
        return [{"id": iid, "name": ms.localize(iid)} for iid in ideologies]

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
                    results[etype].append({"id": eid, "name": ms.localize(eid)})
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
                        "id": pt,
                        "name": ms.localize(pt),
                        "era": int(era_str.split("_")[-1]),
                    })

    def _find_unlocked_by_tech(self, tid):
        """Find all entities unlocked by a technology across all entity types."""
        unlocked = defaultdict(list)
        for etype in ms.mod_parsers:
            data = ms.get_data(etype)
            if not data:
                continue
            for eid, raw in data.items():
                ed = get_entity_data(raw)
                ut = get_field(ed, "unlocking_technologies")
                if ut and isinstance(ut, list) and tid in ut:
                    unlocked[etype].append({"id": eid, "name": ms.localize(eid)})
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
                    results.append({"id": eid, "name": ms.localize(eid)})
            else:
                if fv is not None:
                    fv_str = str(fv).lower() if not isinstance(fv, list) else " ".join(str(x) for x in fv).lower()
                    if value in fv_str:
                        results.append({"id": eid, "name": ms.localize(eid), field: serialize(fv)})
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
        info = {"id": iid, "name": ms.localize(iid)}
        tech = get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"id": tech[0], "name": ms.localize(tech[0])}
        return info

    def _format_institution_detail(self, iid, raw):
        ed = get_entity_data(raw)
        info = {"id": iid, "name": ms.localize(iid)}
        tech = get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"id": tech[0], "name": ms.localize(tech[0])}
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
        info = {"id": pid, "name": ms.localize(pid)}
        tech = get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"id": tech[0], "name": ms.localize(tech[0])}
        return info

    def _format_pm_detail(self, pid, raw):
        ed = get_entity_data(raw)
        info = {"id": pid, "name": ms.localize(pid)}
        tech = get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"id": tech[0], "name": ms.localize(tech[0])}
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
            group = {"id": pmg_id, "name": ms.localize(pmg_id), "pms": []}
            if pmg_id in pmg_data:
                pmg_inner = get_entity_data(pmg_data[pmg_id])
                pm_ids = get_field(pmg_inner, "production_methods")
                if pm_ids and isinstance(pm_ids, list):
                    for pid in pm_ids:
                        if pid in pm_data:
                            group["pms"].append(self._format_pm_detail(pid, pm_data[pid]))
                        else:
                            group["pms"].append({"id": pid, "name": ms.localize(pid)})
            result_groups.append(group)
        return {"building": building_id, "name": ms.localize(building_id), "pm_groups": result_groups}

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
        info = {"id": jeid, "name": ms.localize(jeid)}
        group = get_field(ed, "group")
        if group:
            info["group"] = group
        return info

    def _format_je_detail(self, jeid, raw):
        ed = get_entity_data(raw)
        info = {"id": jeid, "name": ms.localize(jeid)}
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
            return {"id": did, "name": ms.localize(did), "raw": serialize(decisions[did])}

        return [{"id": did, "name": ms.localize(did)} for did in decisions]

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
            return {"id": svid, "raw": serialize(svs[svid])}

        return [{"id": svid} for svid in svs]

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
            info = {"id": did, "name": ms.localize(did)}
            modifier = get_field(ed, "modifier")
            if modifier and isinstance(modifier, dict):
                info["modifier"] = {
                    k: v[1] if isinstance(v, tuple) else v
                    for k, v in modifier.items()
                }
            info["raw"] = serialize(decrees[did])
            return info

        return [{"id": did, "name": ms.localize(did)} for did in decrees]

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
            return {"id": oaid, "raw": serialize(oas[oaid])}

        return [{"id": oaid} for oaid in oas]

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
                {"id": pt, "name": ms.localize(pt)} for pt in prereqs
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
                    entry = {"id": eid, "name": ms.localize(eid)}
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
        GET /engine-docs/<type>?group=true    - group similar entries
        """
        if not parts:
            return {
                "available_types": list(engine_docs.keys()),
                "counts": {k: len(v) for k, v in engine_docs.items()},
            }

        doc_type = parts[0]
        if doc_type not in engine_docs:
            raise KeyError(f"Unknown engine doc type: {doc_type}. Available: {list(engine_docs.keys())}")

        entries = engine_docs[doc_type]
        query = params.get("q", [""])[0].lower()
        scope_filter = params.get("scope", [""])[0].lower()
        mask_filter = params.get("mask", [""])[0].lower()
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
def _load_mod_state():
    global ms, startup_elapsed
    logger.info("Loading mod state… (this may take a minute)")
    t0 = time.time()
    try:
        ms = ModState(base_game_paths, mod_paths)
    except Exception as e:
        logger.error(f"Failed to initialize ModState: {e}\n{traceback.format_exc()}")
        raise

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

    # Regenerate docs/ text files from the freshly parsed data
    try:
        from mod_state_script import generate_docs
        generate_docs(ms)
    except Exception as e:
        logger.error(f"Failed to regenerate docs: {e}\n{traceback.format_exc()}")


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
    print("           /events  /institutions  /production-methods  /journal-entries")
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
