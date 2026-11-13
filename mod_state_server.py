"""
Mod State Server - persistent HTTP API for querying parsed mod/vanilla data.

Start:  python mod_state_server.py            # normal start (skips if already running)
        python mod_state_server.py --replace   # kill existing instance, take over port

Query:  Invoke-RestMethod http://localhost:8950/status
        Invoke-RestMethod http://localhost:8950/laws
        python mod_state_client.py laws

Logs:   mod_state_server.log (rotated each startup, previous kept as .log.1)
"""

import hashlib
import importlib
import json
import logging
import logging.handlers
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs, unquote
from urllib.request import urlopen

from mod_state import ModState, entity_paths
from paradox_file_parser import ParadoxFileParser
import path_constants
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
import vanilla_parsed

# Also loaded by name in POST_LOAD_AUDITS. The routes that call them directly
# (/scripted-helpers/unresolved, /script-args, /pm-employment, /variable-usage,
# /loc-accessors: #288, #732, #990, #973, #1246) are in server/routes_analysis.py;
# they stay importable here as mod_state_server.<module>, which tests patch.
import effect_trigger_validity_audit  # noqa: F401
import pm_employment_audit  # noqa: F401
import script_argument_audit  # noqa: F401
import variable_usage  # noqa: F401
import loc_accessor_usage  # noqa: F401

# Route groups moved into server/ (#1537). Each module reads this file's
# state through server.server_state() at call time, from the globals this file
# registers just below (however it was run: as __main__, imported, or exec'd
# into a dict by cProfile); the names are re-exported here because tests and
# tools import them from mod_state_server.
import server as _server_pkg
from server.routes_engine_docs import (  # noqa: F401 — re-exported
    EngineDocsRoutes,
    _LOC_IDENT_RE,
    _build_loc_function_index,
    _engine_docs_find_usage,
    _get_loc_function_index,
    _group_similar_entries,
    _is_function_like_ident,
)
from server.routes_logs import (  # noqa: F401 — re-exported
    LogRoutes,
)
from server.routes_gui import (  # noqa: F401 — re-exported
    GuiRoutes,
    _build_gui_render_index,
    _get_gui_render_index,
    _GUI_DATAREF_RE,
    _GUI_LOC_ATTRS,
    _GUI_TEXT_ATTR_RE,
    ENTITY_TYPE_TO_DATATYPE,
    FIELD_TO_METHODS,
)
from server.routes_vocabulary import (  # noqa: F401 — re-exported
    VocabularyRoutes,
)
from server.routes_validation import (  # noqa: F401 — re-exported
    ValidationRoutes,
    _ALLOWLIST_TYPE_SLUGS,
    _code_part,
    _collect_image_uses,
    _entity_image,
    _extract_define_names,
    _extract_surface_keys,
    _extract_toplevel_keys,
    _find_duplicate_images,
    _find_placeholder_icons,
    _flagships_on_company_logo,
    _git_diff_names,
    _git_log_touched,
    _git_lstree_at_ref,
    _git_show_at_ref,
    _icon_definition_sites,
    _image_content_hash,
    _image_entity_uses,
    _IMAGE_FIELDS_BY_TYPE,
    _image_origin,
    _iter_loc_at_ref,
    _live_vanilla_loc_map,
    _load_image_allowlist,
    _load_standin_patterns,
    _migration_gui_at_risk,
    _migration_loc_drift,
    _MIGRATION_SURFACE_CATEGORIES,
    _migration_surface_diff,
    _MOD_GREP_DIRS,
    _mod_grep_mentions,
    _mod_loc_keys,
    _overlap_state,
    _OVERLAP_STATE_CACHE_SIZE,
    _overlap_vanilla_index,
    _parse_loc_lines,
    _PLACEHOLDER_STATUSES,
    _principle_group_of,
    _read_live_file,
    _render_duplicate_images_text,
    _render_placeholder_icons_text,
    _resolve_image_path,
    _SHARED_BY_DESIGN_ICON_FIELDS,
    _SHARED_WITH_LIMIT,
    _TOP_LEVEL_OPENER_RE,
    _TOPLEVEL_KEY_RE,
    _validate_git_ref,
)
from server.routes_analysis import (  # noqa: F401 — re-exported
    AnalysisRoutes,
    _BAG_CONTAINERS,
    _classify_option_polarity,
    _data_contains_string,
    _describe_add_modifier,
    _describe_change_variable,
    _emit_event_effect,
    _EVENT_HEADER_RE,
    _event_ids_from_mod_file,
    _extract_event_ids_from_file,
    _extract_modifier_fields,
    _find_dominance_issues,
    _find_modifier_grants,
    _find_soft_dominance_issues,
    _format_value,
    _get_loc_accessor_index,
    _get_script_args_result,
    _get_variable_usage_index,
    _grant_block_label,
    _grant_entity_dirs,
    _grant_entity_type_name,
    _GRANT_LINE_RE,
    _GRANT_NESTED_PARENTS,
    _GRANT_OPENER_RE,
    _GRANT_REPLACE_RE,
    _grant_scan_plan,
    _GRANT_SKIP_DIRS,
    _grant_type_key,
    _iter_field_values,
    _mod_replaced_entity_ids,
    _modifier_color_lookup,
    _polarity,
    _POLARITY_GLYPHS,
    _render_effect_text,
    _render_event_balance_issues_text,
    _render_event_balance_text,
    _resolve_mod_relative_path,
    _resolve_static_modifier,
    _SCALING_WRAPPERS,
    _scan_events_for_reviewed_dominance,
    _scan_file_for_grants,
    _summarize_balance_option,
    _summarize_polarity,
    _try_float,
    _walk_event_effects,
    EVENT_BALANCE_CONTAINER_KEYS,
    EVENT_BALANCE_OPTION_META_KEYS,
    MODIFIER_GRANT_SOURCES,
)
from server.routes_entities import (  # noqa: F401 — re-exported
    EntityRoutes,
    _company_catalog,
    _diff_entity_fields,
    _extract_parameters,
    _loc_keys_for,
    _normalize_entity_type,
    _paradox_text,
    _PARAM_RE,
    _party_catalog,
    _resolve_entity_type,
    _singularize_word,
    _state_history_tables,
    _unwrap_modifiers,
    _unwrap_val,
    LOC_KEY_FAMILIES,
)

_server_pkg.register_state(globals())

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

# ModState logs its parse diagnostics (including per-file parse failures) to the
# "mod_state" logger. Route it through the same handlers so those land in
# mod_state_server.log instead of stderr-only. INFO keeps the per-file DEBUG
# chatter out of the log file.
_mod_state_logger = logging.getLogger("mod_state")
_mod_state_logger.setLevel(logging.INFO)
_mod_state_logger.addHandler(_console_handler)
_mod_state_logger.addHandler(_file_handler)

# The parser warns on the "paradox_file_parser" logger when a file defines a
# top-level key more than once (last definition kept). Same routing so it
# reaches mod_state_server.log; INFO drops its DEBUG note on folded INJECT: keys.
_parser_logger = logging.getLogger("paradox_file_parser")
_parser_logger.setLevel(logging.INFO)
_parser_logger.addHandler(_console_handler)
_parser_logger.addHandler(_file_handler)

_server_start_time: float = 0.0  # set in main()

# ---------------------------------------------------------------------------
# Path configuration
#
# Built by mod_state.entity_paths from VANILLA_COMMON_DIRS (the one list of
# vanilla entity types; vanilla_parsed snapshots exactly the same set) and
# MOD_ONLY_DIRS. mod_state_script.py builds the same pair.
#
# Use forward slashes everywhere; path_constants exposes Linux-rooted paths,
# and the win-style backslash trick from the pre-WSL repo no longer works.
# ---------------------------------------------------------------------------
_BASE_COMMON = os.path.join(base_game_path, "game", "common")
_MOD_COMMON = os.path.join(mod_path, "common")

base_game_paths, mod_paths = entity_paths(base_game_path, mod_path)

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
ms: ModState = None  # type: ignore[assignment]
startup_elapsed: float = 0.0
engine_docs: dict = {}  # Parsed engine documentation (effects, triggers, etc.)
dev_reference_docs: dict = {}  # .md files from base game common/ dirs
_company_catalog_cache: tuple[ModState, list[dict]] | None = None
_party_catalog_cache: tuple[ModState, list[dict]] | None = None
# (ModState, {state: record}, state-region table, vanilla source) for
# /state-history; cleared with the catalogs on every load.
_state_history_cache: tuple | None = None


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


# Loc-function index — lazily built on first /engine-docs/loc-functions request.
# Maps token -> {"count": N, "examples": [{file, line, expression}], "kind": ...}.
_LOC_FUNCTION_INDEX: Optional[dict] = None
_LOC_EXPR_RE = re.compile(r"\[([^\]]+)\]")
# The index's builder and the /engine-docs/usage scanner moved to
# server/routes_engine_docs.py (#1537); their caches above stay here.


# ---------------------------------------------------------------------------
# GUI render-site index — lazily built on first /gui/render-* request.
# Maps:
#   by_key[loc_key]                 -> [{file, line, attr, expression}]
#   by_method[(DataType, Method)]   -> [{file, line, expression}]
# Powers /gui/render-sites/<loc_key> (mechanical text=... scan) and
# /gui/render-paths/<EntityType>?field=<role> (entity-method walker).
# ---------------------------------------------------------------------------
_GUI_RENDER_INDEX: Optional[dict] = None


# A bag is the first block inside an entity whose name says "modifier":
# `modifier`, `member_modifier`, `acceptance_modifier`, `prosperity_modifier`,
# `country_modifiers`, `upkeep_modifier_unscaled`, `tax_modifier_very_high`.
# Matching on the name (not a fixed list) is what stops a new bag name, such as
# the law-level `acceptance_modifier` the first version never knew, from being
# silently dropped. `ai_*` blocks are AI-weight modifiers, not grants.
_MODIFIER_BAG_RE = re.compile(
    r"^(?:tax_modifier_[a-z_]+|(?:[a-z0-9_]+_)?modifiers?(?:_unscaled)?)$"
)


def _is_modifier_bag(name) -> bool:
    return (isinstance(name, str) and not name.startswith("ai_")
            and _MODIFIER_BAG_RE.match(name) is not None)


# ---------------------------------------------------------------------------
# Scripted-effect / scripted-trigger caller index (issue #132)
# ---------------------------------------------------------------------------
# The parser discards file/line, so call sites come from a raw, brace-aware scan
# of every script-bearing .txt in the mod and vanilla — the same reason
# _scan_file_for_grants exists. Built lazily on first request and cached in
# _call_index_cache; invalidated on /reload (see _load_mod_state). One pass
# populates the index for *all* helpers, so any subsequent lookup is a dict hit.
_call_index_cache: dict | None = None
# The vanilla half of that scan is the bulk of the cost and cannot change while
# the process lives (vanilla files are read-only; a vanilla bump means
# restarting the server), so it is built once per process and reused across
# reloads — only the mod tree is rescanned per reload (#296). Without this the
# background warm re-walked all of vanilla after every reload, including the
# fast `?mod_only=true&audits_only=true` iteration path.
_vanilla_call_index_cache: dict | None = None
# Bumped by _invalidate_call_index on every reload. A build that started before
# an invalidation must not write its now-stale result into the cache.
_call_index_generation = 0
# Serializes index builds so a request racing the background warm waits for the
# in-flight scan instead of running a second copy of it (#296).
_call_index_build_lock = threading.Lock()

# Superset of every LHS name the three call regexes below can match. One
# pass over a whole file answers "could this file call any mod helper at
# all?" — most vanilla files can't, and skipping their line-by-line scan is
# what keeps the cold index build off a request's critical path (#293).
_ANY_LHS_RE = re.compile(r"([a-z_]\w*)\s*=")
_CALL_FLAG_RE = re.compile(r"^\s*([a-z_]\w*)\s*=\s*(yes|no)\s*$")
_CALL_INLINE_RE = re.compile(r"^\s*([a-z_]\w*)\s*=\s*\{(.*)\}\s*$")
_CALL_OPENER_RE = re.compile(r"^\s*([a-z_]\w*)\s*=\s*\{")
_ENTITY_OPENER_RE = re.compile(
    r"^\s*(?:INJECT:|REPLACE:|REPLACE_OR_CREATE:)?([A-Za-z_][\w.]*)\s*=\s*\{"
)
_ARG_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*$")
_INLINE_ARG_RE = re.compile(r"([A-Za-z_]\w*)\s*=\s*([^\s{}]+)")


def _coerce_arg(v: str):
    v = v.strip().strip('"')
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def _caller_type(rel: str) -> str:
    """Best-effort entity-type label for a call-site file path."""
    parts = rel.replace("\\", "/").split("/")
    if parts and parts[0] == "events":
        return "Events"
    pretty = {
        "on_actions": "On Actions",
        "scripted_effects": "Scripted Effects",
        "scripted_triggers": "Scripted Triggers",
        "scripted_buttons": "Scripted Buttons",
        "journal_entries": "Journal Entries",
        "decisions": "Decisions",
    }
    if "common" in parts:
        i = parts.index("common")
        if i + 1 < len(parts):
            return pretty.get(parts[i + 1], parts[i + 1])
    return parts[-1] if parts else "?"


def _scan_file_for_calls(abs_path: str, rel: str, origin: str,
                         callables: frozenset, index: dict) -> None:
    """Brace-aware scan of one file; append every call site of a known helper to
    *index* keyed by helper name. Tracks the depth-0 enclosing entity and parses
    scalar args passed to multi-line and inline `helper = { ARG = v }` calls."""
    try:
        with open(abs_path, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return
    # Cheap reject: a file that never writes `<known helper> =` has no call site
    # for the brace-aware pass to find. Behaviour-preserving — every form the
    # scan detects is `name` + `=`, which _ANY_LHS_RE also matches.
    if callables.isdisjoint(_ANY_LHS_RE.findall(text)):
        return
    lines = text.splitlines(keepends=True)
    ctype = _caller_type(rel)
    depth = 0
    current_entity = None
    call_stack: list = []  # [{"inner": <depth where args live>, "rec": <caller>}]
    for lineno, raw in enumerate(lines, 1):
        text = raw.split("#", 1)[0]
        opens = text.count("{")
        closes = text.count("}")

        # 1) capture scalar args for the innermost open multi-line call block
        if (call_stack and opens == 0 and closes == 0
                and depth == call_stack[-1]["inner"]):
            am = _ARG_RE.match(text)
            if am:
                call_stack[-1]["rec"]["args"][am.group(1)] = _coerce_arg(am.group(2))

        # 2) flag-form call: helper = yes / no
        fm = _CALL_FLAG_RE.match(text)
        if fm and fm.group(1) in callables and current_entity is not None:
            index[fm.group(1)].append({
                "type": ctype, "id": current_entity, "origin": origin,
                "file": rel, "line": lineno, "args": {}})
        # 3) inline call: helper = { ARG = v ... } balanced on one line
        elif opens == closes and opens >= 1:
            im = _CALL_INLINE_RE.match(text)
            if im and im.group(1) in callables and current_entity is not None:
                args = {k: _coerce_arg(v)
                        for k, v in _INLINE_ARG_RE.findall(im.group(2))}
                index[im.group(1)].append({
                    "type": ctype, "id": current_entity, "origin": origin,
                    "file": rel, "line": lineno, "args": args})

        # 4) block opener (opens>closes): depth-0 entity, or a multi-line call
        if opens > closes:
            if depth == 0:
                em = _ENTITY_OPENER_RE.match(text)
                current_entity = em.group(1) if em else None
            else:
                cm = _CALL_OPENER_RE.match(text)
                if cm and cm.group(1) in callables and current_entity is not None:
                    rec = {"type": ctype, "id": current_entity, "origin": origin,
                           "file": rel, "line": lineno, "args": {}}
                    index[cm.group(1)].append(rec)
                    call_stack.append({"inner": depth + 1, "rec": rec})

        # 5) advance depth; pop call blocks that have closed; reset at top level
        depth += opens - closes
        while call_stack and depth < call_stack[-1]["inner"]:
            call_stack.pop()
        if depth <= 0:
            depth = 0
            current_entity = None
            call_stack = []


def _scan_tree_for_calls(origin: str, base: str, repo_root: str,
                         callables: frozenset, index: dict) -> None:
    """Scan one tree's `events/` + `common/` for call sites into *index*."""
    for sub in ("events", "common"):
        scan_dir = os.path.join(base, sub)
        if not os.path.isdir(scan_dir):
            continue
        for dirpath, _dirs, files in os.walk(scan_dir):
            for fname in files:
                if not fname.endswith(".txt"):
                    continue
                abs_path = os.path.join(dirpath, fname)
                rel = os.path.relpath(abs_path, repo_root)
                _scan_file_for_calls(abs_path, rel, origin, callables, index)


def _get_vanilla_call_index(callables: frozenset) -> dict:
    """{helper: [vanilla caller, ...]}, built once per process (#296).

    Safe to reuse across reloads even as `callables` changes: vanilla script is
    immutable here, and a mod-defined helper appearing in `callables` can't add
    vanilla call sites — vanilla only ever calls helpers vanilla itself defines.
    """
    global _vanilla_call_index_cache
    if _vanilla_call_index_cache is None:
        index: dict = defaultdict(list)
        _vanilla_game = os.path.join(base_game_path, "game")
        if os.path.isdir(_vanilla_game):
            t0 = time.monotonic()
            _scan_tree_for_calls("vanilla", _vanilla_game, _vanilla_game,
                                 callables, index)
            logger.info(
                f"[call-index] vanilla scan built in {time.monotonic() - t0:.1f}s "
                f"({len(index)} helpers with callers) — reused for this process"
            )
        _vanilla_call_index_cache = dict(index)
    return _vanilla_call_index_cache


def _build_call_index() -> dict:
    """Scan mod + vanilla script-bearing trees, returning
    {helper_name: [caller, ...]} for every scripted effect/trigger."""
    callables: frozenset = frozenset(
        set((ms.get_data("Scripted Effects") or {}).keys())
        | set((ms.get_data("Scripted Triggers") or {}).keys())
    )
    index: dict = defaultdict(list)
    if not callables:
        return index
    for helper, callers in _get_vanilla_call_index(callables).items():
        index[helper].extend(callers)
    _scan_tree_for_calls("mod", mod_path, mod_path, callables, index)
    return dict(index)


def _invalidate_call_index() -> None:
    """Drop the cached callers index and invalidate any build in flight."""
    global _call_index_cache, _call_index_generation
    _call_index_cache = None
    _call_index_generation += 1


# /script-args (#732): one script_argument_audit run, reused until the next
# reload bumps _call_index_generation. (generation, AuditResult) or None.
_script_args_cache: tuple | None = None
_script_args_lock = threading.Lock()


# /variable-usage (#973): one variable_usage scan of the mod (a few seconds),
# reused until the next reload bumps _call_index_generation.
# (generation, Index) or None.
_variable_usage_cache: tuple | None = None
_variable_usage_lock = threading.Lock()


# /loc-accessors (#1246): vanilla loc (and vanilla `.gui` when the game is
# installed) indexed by data type, about 2 s. Vanilla changes only on a full
# load, which replaces _VANILLA_LOC_CACHE, so the index is kept until that
# object changes; a mod-only reload leaves it. (loc, Index, catalog) or None.
_loc_accessor_cache: tuple | None = None
_loc_accessor_lock = threading.Lock()


def _get_call_index() -> dict:
    global _call_index_cache
    cached = _call_index_cache
    if cached is not None:
        return cached
    # Build under a lock so a request that races the background warm waits for
    # that scan rather than duplicating it (#296) — two concurrent full scans
    # contend on the GIL and make both slower. Re-check inside: the warm we
    # queued behind may have just filled the cache.
    with _call_index_build_lock:
        cached = _call_index_cache
        if cached is not None:
            return cached
        gen = _call_index_generation
        index = _build_call_index()
        # A reload landed while we were scanning: serve this result to the
        # caller who asked before it, but don't cache data that no longer
        # matches ModState.
        if gen == _call_index_generation:
            _call_index_cache = index
        return index


_call_index_warm_thread: Optional[threading.Thread] = None


def _warm_call_index_async() -> None:
    """Build the callers index off the request path after a (re)load.

    The index is already cached per reload, but it is built lazily — so the
    whole cold cost (a walk of mod + vanilla `events/` and `common/`) landed on
    whoever asked for `/scripted-effects/<id>` first, which is long enough to
    blow a client's 10 s timeout (#293). A daemon thread absorbs it instead,
    without delaying `ready`. A request that arrives mid-warm blocks on the
    in-flight scan rather than starting a second one (#296), and a build
    started before a reload is discarded by the generation check in
    _get_call_index. After the first build only the mod tree is rescanned, so
    the warm that follows a reload costs a fraction of the cold one."""
    global _call_index_warm_thread

    def _warm() -> None:
        try:
            t0 = time.monotonic()
            _get_call_index()
            logger.info(
                f"[warm] scripted-helper callers index ready "
                f"({time.monotonic() - t0:.1f}s)"
            )
        except Exception:  # noqa: BLE001 — a warm failure must never kill the server
            logger.exception("[warm] callers index build failed; will build on demand")

    if _call_index_warm_thread is not None and _call_index_warm_thread.is_alive():
        return
    _call_index_warm_thread = threading.Thread(
        target=_warm, name="warm-call-index", daemon=True
    )
    _call_index_warm_thread.start()


def _vanilla_tree_present() -> bool:
    """Does base_game_path resolve to a populated `game/common` directory —
    vanilla FILES on disk, as opposed to vanilla data (see
    _vanilla_data_loaded)? Vanilla `game/common/` ships hundreds of subdirs,
    so fewer than ~10 entries means the path is empty/broken."""
    try:
        common = os.path.join(base_game_path, "game", "common")
        if not os.path.isdir(common):
            return False
        return len(os.listdir(common)) > 10
    except OSError:
        return False


def _vanilla_data_loaded() -> bool:
    """Cheap precondition: is vanilla data available — parsed from the game
    files, or loaded from the committed vanilla_parsed/ snapshot? Used by
    /status to refuse `ready` when neither materialized (typical bootstrap
    failure mode — see issue #93)."""
    return _vanilla_source.get("kind") == "vanilla_parsed" or _vanilla_tree_present()


def _vanilla_files_unusable_reason() -> Optional[str]:
    """Why the vanilla game FILES must not feed generate_docs and
    VANILLA_FILE_REGENERATORS, or None when they can: there are none, or they
    are an older vanilla than the vanilla_parsed/ snapshot the load used."""
    if not _vanilla_tree_present():
        return f"no vanilla game files under {base_game_path}/game"
    if _vanilla_source.get("game_files_outdated"):
        return (
            f"the vanilla game files under {base_game_path}/game are "
            f"{_vanilla_source.get('game_files_version')}, older than "
            f"vanilla_parsed/ ({_vanilla_source.get('game_version')})"
        )
    return None


# Where the vanilla half of `ms` comes from. VIC3_VANILLA_SOURCE picks:
#   auto (default)  — vanilla_parsed/ when it matches the code and (when one
#                     is on disk) the game files; parse the game files when
#                     they are present and the snapshot is stale or missing;
#                     vanilla_parsed/ even if stale when there are no files,
#                     or when the files are an OLDER vanilla than the snapshot
#                     (e.g. an out-of-date vanilla clone in a cloud session).
#   game_files      — always parse <base_game_path>/game (pre-snapshot behavior).
#   vanilla_parsed  — always load vanilla_parsed/, even if stale.
VANILLA_SOURCE_MODES = ("auto", "game_files", "vanilla_parsed")
VANILLA_PARSED_DIR = vanilla_parsed.DEFAULT_DIR

# Set by _choose_vanilla_source on every full load; reported by /status
# `vanilla_source`. `kind` is "game_files" or "vanilla_parsed".
_vanilla_source: dict = {}


def _choose_vanilla_source() -> tuple[dict, list[dict]]:
    """Decide where this full load takes vanilla from. Returns
    (source, warnings) with warnings in the POST /reload `{label, detail}`
    shape."""
    raw_mode = (os.environ.get("VIC3_VANILLA_SOURCE") or "auto").strip().lower()
    warnings: list[dict] = []
    mode = raw_mode if raw_mode in VANILLA_SOURCE_MODES else "auto"
    if mode != raw_mode:
        warnings.append({
            "label": "vanilla_source",
            "detail": f"VIC3_VANILLA_SOURCE={raw_mode!r} is not one of "
                      f"{', '.join(VANILLA_SOURCE_MODES)}; using auto",
        })
    tree = _vanilla_tree_present()
    manifest = vanilla_parsed.read_manifest(VANILLA_PARSED_DIR)
    source = {"mode": mode, "game_files_present": tree}
    if manifest is None or mode == "game_files":
        source.update(
            kind="game_files",
            reason="VIC3_VANILLA_SOURCE=game_files" if mode == "game_files"
            else f"no snapshot at {VANILLA_PARSED_DIR}",
        )
        return source, warnings

    fresh = vanilla_parsed.check(
        VANILLA_PARSED_DIR, base_game_path if tree else None, manifest=manifest,
    )
    source.update(
        game_version=manifest.get("game_version"),
        built_at=manifest.get("built_at"),
        parser_fingerprint=manifest.get("parser_fingerprint"),
        freshness=fresh.as_dict(),
    )
    loadable = manifest.get("format_version") == vanilla_parsed.FORMAT_VERSION
    rebuild = "Rebuild: python3 vanilla_parsed.py build (on a machine with the game)."
    if tree:
        files_version = vanilla_parsed.game_files_version(base_game_path)
        source["game_files_version"] = files_version
        files_key = vanilla_parsed.version_key(files_version)
        snap_key = vanilla_parsed.version_key(manifest.get("game_version"))
        if loadable and mode == "auto" and files_key and snap_key and files_key < snap_key:
            # The files are behind the snapshot, not ahead of it: the snapshot
            # is the vanilla the mod targets. Keep them away from the
            # raw-vanilla generators too (_vanilla_files_unusable_reason).
            source.update(
                kind="vanilla_parsed",
                reason=f"game files are vanilla {files_version}, older than the snapshot",
                game_files_outdated=True,
            )
            warnings.append({
                "label": "vanilla_source",
                "detail": f"the vanilla game files under {base_game_path}/game are "
                          f"{files_version}, older than vanilla_parsed/ "
                          f"({manifest.get('game_version')}): loaded vanilla_parsed/. "
                          "Update or drop that vanilla tree; set "
                          "VIC3_VANILLA_SOURCE=game_files to parse it anyway.",
            })
            if fresh.code_reasons:
                warnings.append({
                    "label": "vanilla_source",
                    "detail": "vanilla_parsed/ does not match the code: "
                              + "; ".join(fresh.code_reasons) + f". {rebuild}",
                })
            return source, warnings
    if loadable and (mode == "vanilla_parsed" or fresh.fresh or not tree):
        source["kind"] = "vanilla_parsed"
        source["reason"] = (
            "fresh" if fresh.fresh else
            "VIC3_VANILLA_SOURCE=vanilla_parsed" if mode == "vanilla_parsed" else
            "no vanilla game files on disk"
        )
        if not fresh.fresh:
            warnings.append({
                "label": "vanilla_source",
                "detail": "loaded vanilla_parsed/ although it is stale: "
                          + "; ".join(fresh.reasons) + f". {rebuild}",
            })
        return source, warnings

    source["kind"] = "game_files"
    source["reason"] = "vanilla_parsed/ is stale" if loadable else (
        f"vanilla_parsed/ format {manifest.get('format_version')!r} is unreadable"
    )
    warnings.append({
        "label": "vanilla_source",
        "detail": f"{source['reason']} ("
                  + ("; ".join(fresh.reasons) or "format") + "); "
                  + ("parsed the game files instead. " if tree else
                     "and there are no game files to parse — vanilla data is empty. ")
                  + rebuild,
    })
    return source, warnings


def cli_mod_state() -> ModState:
    """A ModState for an audit run from the command line, with vanilla taken
    from where a full server load takes it (`_choose_vanilla_source`) and the
    English loc loaded, vanilla then mod. A bare `ModState(base_game_paths,
    mod_paths)` has no vanilla at all without a game install, and no loc: the
    concept audit then flagged every concept reference, the mod's own included
    (3,522 on 2026-09-29)."""
    source, warnings = _choose_vanilla_source()
    for w in warnings:
        print(f"[vanilla] {w['detail']}", file=sys.stderr)
    if source["kind"] == "vanilla_parsed":
        snapshot = vanilla_parsed.load(VANILLA_PARSED_DIR)
        ms = ModState(base_game_paths, mod_paths, vanilla_data=snapshot.data)
        ms.parse_failures[:0] = snapshot.parse_failures
        ms.localization = dict(snapshot.localization)
    else:
        ms = ModState(base_game_paths, mod_paths)
        vanilla_loc_dir = os.path.join(base_game_path, "game", "localization", "english")
        if os.path.isdir(vanilla_loc_dir):
            ms.add_localization(vanilla_loc_dir)
    for loc_dir in (os.path.join(mod_path, "localization", "english"),
                    os.path.join(mod_path, "localization", "english", "replace")):
        if os.path.isdir(loc_dir):
            ms.add_localization(loc_dir)
    return ms


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


# Matches a dotted-numeric version token, e.g. `1.13.9` or `1.13`. Used to pull
# a comparable version out of a git commit subject ("1.13.9 (Matcha)") or a docs
# snapshot path (".../Modding-Digests/1.13.9/docs").
_VERSION_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")


def _version_from_text(text: Optional[str]) -> Optional[str]:
    """Extract the last dotted-numeric version token from a string, or None.

    The *last* match is preferred so a path like `/home/.../vic3/1.13.9` yields
    the trailing version dir rather than an incidental earlier match."""
    if not text:
        return None
    matches = _VERSION_RE.findall(text)
    return matches[-1] if matches else None


def _read_live_game_version() -> Optional[str]:
    """Read `rawVersion` from `<base_game_path>/launcher/launcher-settings.json`
    — the ground truth for which vanilla build the engine will actually run.

    Nothing else in the server reads this file. Returns None if it's missing or
    unparseable (guarded so /status never crashes on a bad install)."""
    path = os.path.join(base_game_path, "launcher", "launcher-settings.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    v = data.get("rawVersion")
    return v if isinstance(v, str) and v else None


def _versions_mismatch(*versions: Optional[str]) -> bool:
    """True when the supplied version tokens (None entries ignored) disagree."""
    present = {v for v in versions if v}
    return len(present) > 1


def _load_vanilla_repo_head_info() -> dict:
    """Return {sha, sha_short, date_iso, date_unix, subject, version} for the
    HEAD commit of the vanilla source mirror, or {} if not a git repo / not
    available. `version` is parsed from the commit subject (convention
    "1.13.9 (Matcha)" -> "1.13.9")."""
    repo = vanilla_source_repo_path
    if not os.path.isdir(os.path.join(repo, ".git")):
        return {}
    try:
        # Subject (%s) goes on its own line (%n) so the space-separated
        # `%H %ct %ai` prefix parses cleanly — %ai itself contains spaces.
        result = subprocess.run(
            ["git", "-C", repo, "log", "-1", "--format=%H %ct %ai%n%s"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        out = result.stdout.rstrip("\n")
        head_line, _, subject = out.partition("\n")
        parts = head_line.strip().split(maxsplit=2)
        if len(parts) >= 3:
            sha, ct, ai = parts
            return {
                "sha": sha,
                "sha_short": sha[:8],
                "date_unix": int(ct),
                "date_iso": ai,
                "subject": subject,
                "version": _version_from_text(subject),
            }
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        logger.warning(f"Failed to read vanilla repo HEAD: {e}")
    return {}


def _compute_version_status(repo_head: Optional[dict] = None) -> dict:
    """Cross-check the three places a vanilla version shows up:
      - `live_game`         — launcher-settings.json rawVersion (what runs)
      - `vanilla_clone_head`— HEAD commit subject of the ~/src/vic3 mirror
      - `engine_docs_source`— version encoded in the resolved engine-docs dir
    `mismatch` is True when the parseable version tokens disagree — the signal
    that you bumped one but forgot to refresh the others."""
    if repo_head is None:
        repo_head = _load_vanilla_repo_head_info()
    live_version = _read_live_game_version()
    clone_version = repo_head.get("version") if repo_head else None
    docs_dir, docs_label = _engine_docs_source()
    docs_version = _version_from_text(docs_dir)
    return {
        "live_game": live_version,
        "vanilla_clone_head": clone_version,
        "engine_docs_source": docs_version or (docs_label or None),
        "engine_docs_source_label": docs_label,
        "mismatch": _versions_mismatch(live_version, clone_version, docs_version),
    }


def _version_mismatch_warnings() -> list[dict]:
    """A one-entry reload-warning list when `_compute_version_status` reports a
    mismatch, else [].

    The same finding as the `[VERSION MISMATCH]` startup log line and /status
    `versions`, in the `warnings` array of every POST /reload (#332): the
    startup log is not re-read mid-session, and a stale engine-docs baseline
    makes every engine-doc-backed validation quietly wrong. A cross-check that
    crashes is reported the same way, never raised into the reload."""
    try:
        status = _compute_version_status()
        if not status.get("mismatch"):
            return []
        docs_dir, _label = _engine_docs_source()
    except Exception as e:  # noqa: BLE001
        return [_failure_warning("version_mismatch",
                                 "mod_state_server._compute_version_status", e)]
    return [{
        "label": "version_mismatch",
        "detail": (
            "vanilla versions disagree: "
            f"live_game={status.get('live_game')} "
            f"vanilla_clone_head={status.get('vanilla_clone_head')} "
            f"engine_docs_source={status.get('engine_docs_source')} "
            f"({status.get('engine_docs_source_label')}, {docs_dir}). "
            "Engine-doc-backed checks (/modifier-search, /engine-docs/origin, "
            "the effect/trigger and modifier audits) judge the mod by the "
            "engine-docs version. Refresh whichever is stale; GET /status "
            "`versions` has the same fields."
        ),
        "live_game": status.get("live_game"),
        "vanilla_clone_head": status.get("vanilla_clone_head"),
        "engine_docs_source": status.get("engine_docs_source"),
        "engine_docs_source_label": status.get("engine_docs_source_label"),
        "engine_docs_dir": docs_dir,
    }]


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
        if stripped.startswith("----"):
            # The documented targets end at a `----` rule, followed by a bare
            # "Event Targets Saved from Code:" name list. Keep `current` open
            # past it and that list lands in the description of whichever
            # entry the engine printed last, which differs between dumps.
            if current:
                current["description"] = current["description"].strip()
                entries.append(current)
            current = None
            continue
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


def _pattern_token(pattern: str) -> str:
    m = _PATTERN_TOKEN_RE.search(pattern)
    return m.group(0) if m else "{placeholder}"


engine_docs_sources: dict = {}  # {key: filesystem path of source .log}
engine_docs_source_label: str = ""  # "vanilla_snapshot" or "mod_loaded" — which path was read
_vanilla_snapshot_contamination: list = []  # mod-only script_only modifier names found in the "vanilla" snapshot
# Why the last _load_engine_docs left docs/engine/ unrendered, as reload
# warnings ([] when it rendered). A list of its own because the post-load chain
# resets _post_load_warnings after this runs. Folded into POST /reload
# `warnings` and shown in /status `vanilla_snapshot`.
_engine_docs_warnings: list[dict] = []
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

    status: 'engine' | 'suspicious' | 'unknown'
    info: extra details for the validation report.

    'engine' means a modifier type definition registers the name: vanilla's
    `common/modifier_type_definitions/` or the mod's, the merged `Modifier
    Types` of the loaded ModState, read here. `modifiers_set` is every name
    the caller knows of, the engine-docs dump and the definitions together; it
    no longer decides validity, only whether the dump lists the name. Nothing
    but a definition makes a name valid (#391):

    * The engine-docs dump (`modifiers.log`) lists every name the engine
      could register, about 4,700 of which nobody registers, and a dump older
      than the game still lists names a patch removed. Such a name is
      'unknown', with `listed_in_engine_docs`.
    * A name with a catalog pattern's shape whose captured value is in the
      vocabulary (`building_<building>_throughput_add` for a building that
      exists) is 'unknown' too, with the `pattern` and `value` it matched and
      `unregistered_pattern_instance`: the engine takes each name of a family
      from its own definition and silently ignores the rest. Vanilla defines
      the throughput type for under half of its own buildings.

    'suspicious' is unchanged: the shape of a pattern with a value outside its
    vocabulary, likely a typo.
    """
    registered = (ms.get_data("Modifier Types") or {}) if ms else {}
    if name in registered:
        return "engine", {}
    info: dict = {}
    if name in modifiers_set:
        info["listed_in_engine_docs"] = True
    pat = modifier_to_pattern.get(name)
    if pat:
        return "unknown", {
            **info, "pattern": pat[0], "value": pat[1], "source": pat[2],
            "unregistered_pattern_instance": True,
        }
    suspicious_match: dict | None = None
    for pattern_str, prefix, suffix, vocab_values, placeholder in pattern_pairs:
        captured = _match_pattern(name, prefix, suffix)
        if captured is None:
            continue
        if not vocab_values or captured in vocab_values:
            return "unknown", {
                **info, "pattern": pattern_str, "value": captured,
                "source": "catalog_runtime",
                "unregistered_pattern_instance": True,
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
    return "unknown", info


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

    # Every modifier name known to exist: the engine-docs dump (modifiers.log)
    # and the modifier type definitions, vanilla's and the mod's. It does not
    # decide validity: `_classify_modifier_name` accepts only a name a
    # definition registers, and uses this set to say whether the dump lists an
    # unregistered one (#391).
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

    # A scripted effect or trigger whose name ends in a modifier suffix
    # (`un_veto_record_add`, `nd_log_doctrine_set`) is called as `name = yes`,
    # which the walker below cannot tell from a boolean modifier line. Only
    # that form is suppressed: `name = 5` is not a call, so a modifier that
    # merely shares a scripted name is still checked (#1403).
    scripted_call_names = (
        set(ms.get_data("Scripted Effects") or {})
        | set(ms.get_data("Scripted Triggers") or {})
    )

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
                            if tstatus != "engine":
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
                # A scripted effect or trigger call, not a modifier line.
                if key in scripted_call_names and actual_val in ("yes", "no"):
                    continue
                status, info = _classify_modifier_name(key, modifiers_set, catalog_pairs)
                if status == "engine":
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
            "an unknown's `listed_in_engine_docs` may be out of date. Validity comes from "
            "the modifier type definitions alone."
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
            for entry_time, message in error_lines:
                if name in message:
                    entry.setdefault("confirmed_by_engine_log", []).append(
                        f"{error_log.label} [{entry_time}] {message[:200]}"
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


_IMAGE_ALLOWLIST_PATH = os.path.join(
    mod_path, "common", "_meta", "duplicate_image_allowlist.yml"
)


_STANDIN_PATTERNS_PATH = os.path.join(
    mod_path, "common", "_meta", "generated_standin_icons.yml"
)


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
        out.append("Modifier-shaped names (ending in `_add`, `_mult`, `_max_level(s)`, `_set`, "
                   "`_bool` or `_boolean`) used in mod data that no modifier type definition "
                   "registers, vanilla's or the mod's. The engine drops such a field at load "
                   "(`Unknown modifier type`, in `debug.log` only) and a `modifier:` read of it "
                   "reads nothing: register the name in `common/modifier_type_definitions/` or "
                   "fix it. Neither the engine's `modifiers.log` listing a name nor a name "
                   "fitting a pattern-catalog family makes it valid (#391); either one only "
                   "says the name can be registered, and is noted on its line. Regenerating "
                   "the engine docs changes no verdict.")
        out.append("")
        for entry in report["unknown_modifiers"]:
            notes = []
            if entry.get("unregistered_pattern_instance"):
                notes.append(f"unregistered instance of `{entry.get('pattern', '?')}` "
                             f"(`{entry.get('value', '?')}`)")
            if entry.get("listed_in_engine_docs"):
                notes.append("listed in the engine docs (`modifiers.log`)")
            tail = f" — {'; '.join(notes)}" if notes else ""
            out.append(f"- `{entry['name']}`{tail}")
            for u in entry.get("used_in", [])[:5]:
                out.append(f"  - {u}")
        out.append("")
    return "\n".join(out) + "\n"


def _reload_engine_only():
    """§5: re-read engine logs + regenerate reference docs WITHOUT reparsing the
    mod (skips the slow ModState rebuild). Use after the engine regenerates the
    .log files in-game when no mod files have changed.

    Returns the step failures as [{label, module, error, traceback_tail}] — the
    same shape _run_post_load_generators uses — so POST /reload?engine_only=true
    can put them in its `warnings` array instead of reporting a clean reload
    while the log carries an exception (#242).
    """
    global _last_validation_report
    logger.info("Engine-only reload: re-reading engine logs + regenerating reference docs.")
    errors: list[dict] = []
    try:
        _load_engine_docs()
    except Exception as e:
        logger.exception("Failed to reload engine docs")
        errors.append(_failure_warning("engine_docs", "mod_state_server._load_engine_docs", e))
    errors.extend(_engine_docs_warnings)
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
        errors.append(
            _failure_warning("engine_coverage_validation",
                             "mod_state_server._validate_engine_coverage", e)
        )
    return errors


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
    only — the `decimals = N` / `percent = yes` declarations live in vanilla
    common/modifier_type_definitions/, which ModState already holds as the
    vanilla `Modifier Types` (from the install or from vanilla_parsed/). This
    pass patches the existing engine_docs['modifiers'] entries with them so
    downstream tools (the visibility audit in particular) can compute display
    rounding without re-reading the vanilla files themselves.

    Runs BEFORE _union_mod_modifier_types so mod-side cosmetic redeclarations
    (which may set a different `decimals`) win.
    """
    base = ms.base_parsers.get("Modifier Types") if ms else None
    vanilla_types = base.data if base is not None else {}
    if not vanilla_types:
        logger.warning("Vanilla Modifier Types not loaded; no decimals/percent annotation")
        return

    by_name = {e.get("name"): i for i, e in enumerate(engine_docs.get("modifiers", []))}
    annotated = 0

    def _unwrap(v):
        return v[1] if isinstance(v, tuple) and len(v) >= 2 else v

    for name, raw in vanilla_types.items():
        data = _flatten_entity_data(raw)
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


# The engine-doc reference files name the version they were rendered from in
# their first line: "# Auto-generated from modifiers.log (engine docs 1.14.5)."
_RENDERED_ENGINE_DOCS_VERSION_RE = re.compile(r"\(engine docs (\d+(?:\.\d+)+)\)")


def _rendered_engine_docs_version(engine_dir: str) -> Optional[str]:
    """The engine-docs version docs/engine/ was last rendered from, read from
    the modifiers_summary.txt header; None when the file or version is absent."""
    try:
        with open(os.path.join(engine_dir, "modifiers_summary.txt"), "r", encoding="utf-8") as f:
            header = f.readline()
    except OSError:
        return None
    m = _RENDERED_ENGINE_DOCS_VERSION_RE.search(header)
    return m.group(1) if m else None


def _vanilla_reference_versions() -> tuple[Optional[str], Optional[str]]:
    """(vanilla_parsed snapshot's game_version, installed game's version), each
    None when unknown: the vanilla the mod is checked against."""
    manifest = vanilla_parsed.read_manifest(vanilla_parsed.DEFAULT_DIR) or {}
    return (_version_from_text(manifest.get("game_version")),
            _version_from_text(_read_live_game_version()))


def _engine_docs_render_blockers(
    chosen_dir: str, source_label: str, failed_logs: list, engine_dir: str,
    reference_versions: Optional[tuple] = None,
) -> list[dict]:
    """Return a one-entry reload-warning list when the parsed engine docs must
    not be rendered over docs/engine/, else [].

    render_all rewrites the ~30k committed lines of engine reference from
    whatever parsed. With a log missing (no game install, or a fresh machine's
    digest snapshot not cloned yet), that is mod-only content. With a snapshot
    older than the one the files came from (a stale snapshot pin, or a digest
    clone not pulled), it is a silent downgrade. With one newer than both the
    vanilla_parsed snapshot and the installed game (the digest publishes a
    patch before the game updates), the audits would judge the mod by names the
    game doesn't have yet. Either way the audits that read those files change
    their verdicts. Rendering from a version in between still goes ahead. The
    files list the engine's entries only: render_all drops the mod's own
    modifier types and custom localization, which the endpoints still serve.

    `reference_versions` is (snapshot game_version, live game version), read
    by `_vanilla_reference_versions` when not given; with neither known the
    newer-source check is skipped.
    """
    source_version = _version_from_text(chosen_dir)
    rendered_version = _rendered_engine_docs_version(engine_dir)
    snapshot_version, game_version = (
        reference_versions if reference_versions is not None
        else _vanilla_reference_versions()
    )
    known = [v for v in (snapshot_version, game_version) if v]
    newest_vanilla = max(known, key=vanilla_parsed.version_key) if known else None
    if failed_logs:
        reason = (
            f"engine docs incomplete in {chosen_dir} ({source_label}): "
            f"{', '.join(failed_logs)} missing, unparseable or empty"
        )
    elif (
        source_version and rendered_version
        and vanilla_parsed.version_key(source_version)
        < vanilla_parsed.version_key(rendered_version)
    ):
        reason = (
            f"engine docs in {chosen_dir} ({source_label}) are {source_version}, "
            f"older than {rendered_version}, the version docs/engine/ was rendered from"
        )
    elif (
        source_version and newest_vanilla
        and vanilla_parsed.version_key(source_version)
        > vanilla_parsed.version_key(newest_vanilla)
    ):
        reason = (
            f"engine docs in {chosen_dir} ({source_label}) are {source_version}, "
            f"newer than vanilla {newest_vanilla} (vanilla_parsed snapshot "
            f"{snapshot_version or 'absent'}, installed game {game_version or 'absent'})"
        )
    else:
        return []
    warning = {
        "label": "engine_docs_render_skipped",
        "detail": (
            f"{reason}, so the docs/engine/ reference files were left as they "
            "were, not re-rendered. Endpoints serve whatever did parse. Set "
            "`vanilla_snapshot_docs_path` to a complete script_docs dump of the "
            "current vanilla version, then reload"
            + (" (or, once the game has updated, rebuild the snapshot with "
               "`python3 vanilla_parsed.py build`)." if "newer than vanilla" in reason
               else ".")
        ),
        "source_label": source_label,
        "source_dir": chosen_dir,
        "source_version": source_version,
        "rendered_version": rendered_version,
        "snapshot_version": snapshot_version,
        "game_version": game_version,
    }
    if failed_logs:
        warning["missing"] = list(failed_logs)
    return [warning]


def _load_engine_docs():
    """Parse all engine documentation files into structured data.

    Source preference: vanilla_snapshot_docs_path (vanilla-only, authoritative)
    > mod_loaded_docs_path (runtime, may include mod declarations).
    Every entry is tagged with `origin`:
      - "vanilla" when read from the vanilla snapshot
      - "unknown" when read from the fallback runtime path (we can't tell)
      - "mod"     after the mod-source-derived union below

    Returns render_all's {filename: size} for the docs/engine/ reference files
    it wrote, or None when they were left alone (`_engine_docs_warnings` says
    why) or the render crashed (logged). `python3 engine_docs_render.py` reads
    it; the server's own callers don't.
    """
    global engine_docs, engine_docs_sources, engine_docs_source_label, _engine_docs_warnings
    engine_docs = {}
    engine_docs_sources = {}
    _engine_docs_warnings = []

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

    failed_logs: list[str] = []  # missing, unparseable or empty
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
        if not engine_docs[key]:
            failed_logs.append(filename)

    engine_docs_out = os.path.join(doc_path, "engine")
    _engine_docs_warnings = _engine_docs_render_blockers(
        chosen_dir, source_label, failed_logs, engine_docs_out
    )

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

    # Regenerate the engine-doc reference files in docs/engine/, unless the
    # parse can't reproduce them (_engine_docs_render_blockers).
    written = None
    if _engine_docs_warnings:
        logger.warning(f"[engine-docs WARN] {_engine_docs_warnings[0]['detail']}")
    else:
        try:
            from engine_docs_render import render_all as _render_engine_docs
            catalog, index, discovered, vocabs = _build_pattern_data()
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

    return written


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


# ---------------------------------------------------------------------------
# Event balance helpers — resolve option effects and tag modifier polarity.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------
class _ServiceNotReady(Exception):
    """Raised by an endpoint when the server is in a degraded state. Caught
    in do_GET and translated to an HTTP non-200 response (defaults to 503)."""
    def __init__(self, payload: dict, status: int = 503):
        self.payload = payload
        self.status = status


class _EndpointError(Exception):
    """Raised by an endpoint to return a rich error body at a chosen status
    (default 404) — e.g. an unknown entity type with `did_you_mean` suggestions,
    rather than the generic KeyError 404 hint. Caught in do_GET."""
    def __init__(self, payload: dict, status: int = 404):
        self.payload = payload
        self.status = status


class NotFound(_EndpointError):
    """404 — the requested route/entity genuinely doesn't exist.

    Endpoints used to signal this with `raise KeyError(<id>)`, and do_GET mapped
    EVERY KeyError to 404, so an internal bug (a parsed record missing a field)
    was indistinguishable from a missing entity. Raise this instead; a bare
    KeyError now surfaces as a 500. (#254)
    """
    def __init__(self, what, **extra):
        payload = {
            # `{what!r}` keeps the pre-#254 body byte-for-byte: the old handler
            # rendered `str(KeyError(x))`, which is `repr(x)`.
            "error": f"Not found: {what!r}" if isinstance(what, str) else f"Not found: {what}",
            "hint": "GET /help for the endpoint inventory.",
        }
        payload.update(extra)
        super().__init__(payload, 404)


class BadRequest(_EndpointError):
    """400 — the caller's input is wrong (missing/malformed query param, a
    usage error, a path that escapes the mod tree)."""
    def __init__(self, message: str, **extra):
        payload = {"error": message}
        payload.update(extra)
        super().__init__(payload, 400)


class DataNotLoaded(_ServiceNotReady):
    """503 — the server is up but the requested collection isn't in memory.
    Previously returned HTTP 200 with an `{"error": ...}` body, so `curl -f`
    readiness probes passed on failure. (#254)"""
    def __init__(self, what: str):
        super().__init__({
            "error": f"{what} data not loaded",
            "hint": "POST /reload, then check /status (parse_failures) if it persists.",
        }, 503)


_overlap_vanilla_cache: dict = {}


# GET /external-mod-overlap/state: one LayeredState per mod root, newest
# last. It holds the server's ModState's parsers, so every reload drops it.
_overlap_state_cache: dict = {}


# Hostnames that can only mean "this machine". A DNS-rebinding page reaches the
# server with the attacker's hostname in `Host`, so anything else is refused.
_LOCAL_HOSTNAMES = frozenset({"127.0.0.1", "localhost", "[::1]", "::1"})


def _local_request_rejection(host, origin, port: int):
    """Return a human-readable rejection reason, or None if the request may
    proceed. Pure function so it can be unit-tested without a live server.

    `Host` must name this loopback server. Every mainstream client sends one —
    curl/urllib/requests/PowerShell all send `Host: <host>:<port>` — and the
    port-less spelling is accepted too in case a client omits it. Any `Origin`
    header at all means a browser context: only this server's own origin passes,
    and `null` (sandboxed iframe, file:// page) is refused. (#254)
    """
    host_value = (host or "").strip()
    if not host_value:
        return "missing Host header"
    if host_value.startswith("["):  # IPv6 literal: [::1] or [::1]:8950
        close = host_value.find("]")
        if close == -1:
            return f"non-local Host header {host_value!r}"
        hostname, rest = host_value[:close + 1], host_value[close + 1:]
        if rest and not rest.startswith(":"):
            return f"non-local Host header {host_value!r}"
        port_str = rest[1:] if rest else ""
    elif host_value.count(":") == 1:
        hostname, _, port_str = host_value.rpartition(":")
    else:
        # No colon (port omitted) or a bare IPv6 literal like `::1`.
        hostname, port_str = host_value, ""
    if hostname.lower() not in _LOCAL_HOSTNAMES:
        return f"non-local Host header {host_value!r}"
    if port_str and port_str != str(port):
        return f"Host header {host_value!r} does not match the bind port {port}"

    origin_value = (origin or "").strip()
    if origin_value:
        allowed_origins = {
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
            f"http://[::1]:{port}",
        }
        if origin_value.lower() not in allowed_origins:
            return f"cross-site Origin header {origin_value!r}"
    return None


def json_body(data) -> bytes:
    """The bytes of a JSON response: what the server sends and what
    `scripts/query.py` prints, so the two match byte for byte (#1538)."""
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


def encode_response(data, status: int = 200, what: str = "response") -> tuple[bytes, int]:
    """(bytes, status) for a response body. One json can't encode (a set, a
    Path) becomes the 500 body do_GET gives any other failure, so the client
    gets an answer rather than a dropped connection. `what` names the request
    in the log line."""
    try:
        return json_body(data), status
    except Exception as exc:
        logger.error(f"Error handling {what}: {exc}\n{traceback.format_exc()}")
        return json_body({"error": f"{type(exc).__name__}: {exc}"}), 500


class ModStateHandler(EngineDocsRoutes, LogRoutes, GuiRoutes, VocabularyRoutes, ValidationRoutes, AnalysisRoutes, EntityRoutes, BaseHTTPRequestHandler):

    # ---- local-origin gate ------------------------------------------------
    def _bind_port(self) -> int:
        """The port this server actually bound to (falls back to PORT when the
        handler isn't attached to a live HTTPServer, e.g. in unit tests)."""
        return int(getattr(getattr(self, "server", None), "server_port", None) or PORT)

    def _local_request_ok(self, method: str) -> bool:
        """Gate every request on Host/Origin so a page in the user's browser
        can't drive this server (CSRF / DNS rebinding). Rejections are 403 and
        logged at WARNING with the offending header. (#254)"""
        headers = getattr(self, "headers", None)
        host = headers.get("Host") if headers is not None else None
        origin = headers.get("Origin") if headers is not None else None
        reason = _local_request_rejection(host, origin, self._bind_port())
        if reason is None:
            return True
        logger.warning(
            f"Rejected {method} {getattr(self, 'path', '?')} — {reason} "
            f"(Host={host!r} Origin={origin!r})"
        )
        self._respond_json({
            "error": f"Forbidden: {reason}",
            "hint": (
                "The mod-state server only answers requests addressed to "
                f"localhost:{self._bind_port()} with no cross-site Origin."
            ),
        }, 403)
        return False

    # ---- routing ----------------------------------------------------------
    def do_GET(self):
        if not self._local_request_ok("GET"):
            return
        data, status = self.get_result(self.path)
        self._respond_json(data, status)

    def get_result(self, path):
        """(body, status) for GET `path`, with no socket: do_GET's routing and
        error mapping, shared with the offline `scripts/query.py` (#1538)."""
        parsed = urlparse(path)
        parts = [unquote(p) for p in parsed.path.strip("/").split("/") if p]
        params = parse_qs(parsed.query)
        try:
            return self.route(parts, params), 200
        except _EndpointError as exc:
            # NotFound (404) / BadRequest (400) and the richer payload variants.
            return exc.payload, exc.status
        except _ServiceNotReady as exc:
            return exc.payload, exc.status
        except Exception as exc:
            # A bare KeyError lands here on purpose since #254: it means a
            # parsed record was missing a field, which is a server bug, not a
            # missing entity. Endpoints signal the latter with NotFound.
            logger.error(f"Error handling GET {path}: {exc}\n{traceback.format_exc()}")
            return {"error": f"{type(exc).__name__}: {exc}"}, 500

    def do_POST(self):
        if not self._local_request_ok("POST"):
            return
        parsed = urlparse(self.path)
        parts = [unquote(p) for p in parsed.path.strip("/").split("/") if p]
        params = parse_qs(parsed.query)
        if parts == ["reload"]:
            engine_only = (params.get("engine_only") or ["false"])[0].lower() == "true"
            audits_only = (params.get("audits_only") or ["false"])[0].lower() == "true"
            mod_only = (params.get("mod_only") or ["false"])[0].lower() == "true"
            flags = {"engine_only": engine_only, "audits_only": audits_only, "mod_only": mod_only}
            try:
                if engine_only:
                    # A failed engine-docs load or validation pass used to be
                    # logged and dropped; report it in the same `warnings`
                    # array the full reload uses. (#242)
                    warnings = _reload_engine_only() + _version_mismatch_warnings()
                    _record_reload_warnings(flags, warnings)
                    body = {"status": "engine-only reload complete"}
                    if warnings:
                        body["warnings"] = warnings
                    self._respond_json(body)
                else:
                    _load_mod_state(audits_only=audits_only, mod_only=mod_only)
                    body = {
                        "status": "reloaded",
                        "startup_seconds": startup_elapsed,
                        "mode": (
                            "mod_only+audits_only" if mod_only and audits_only
                            else "mod_only" if mod_only
                            else "audits_only" if audits_only
                            else "full"
                        ),
                    }
                    # Surface any actionable findings from the post-load chain
                    # (e.g. modifier_visibility_audit's unreviewed sub-threshold
                    # values). Caller sees them in the same response, not buried
                    # in the server log. Also fold in the known-noise registry
                    # parse-time warnings (anchor-or-die rejections, missing
                    # tracked-issue cross-refs, unresolved open_issues.md anchors)
                    # via the shared collector used by POST /validate/registries.
                    warnings = (
                        list(_vanilla_source_warnings)
                        + list(_engine_docs_warnings)
                        + _version_mismatch_warnings()
                        + list(_post_load_warnings)
                        + _collect_registry_warnings()
                    )
                    _record_reload_warnings(
                        flags, warnings,
                        wrote_files=_post_load_wrote_files,
                        reparsed=_post_load_reparsed,
                    )
                    if warnings:
                        body["warnings"] = warnings
                    # Which mod files the file-writing generators changed on
                    # this run, and whether the mod side was re-parsed after
                    # them (so the audits and /raw saw the new content). When
                    # the re-parse failed, a second reload is needed. (#242)
                    if _post_load_wrote_files:
                        body["generators_wrote_files"] = list(_post_load_wrote_files)
                        body["reparsed_after_generators"] = _post_load_reparsed
                    parse_failures = list(getattr(ms, "parse_failures", []) or [])
                    if parse_failures:
                        body["parse_failures"] = parse_failures
                    self._respond_json(body)
            except Exception as exc:
                logger.error(f"Error during reload: {exc}\n{traceback.format_exc()}")
                self._respond_json({"error": str(exc)}, 500)
        elif parts == ["validate", "registries"]:
            # Re-validate the known-noise registries WITHOUT a full reload —
            # cheap way to check vanilla_known_bugs.md / mod_known_noise.md edits
            # (anchor resolution, cross-references) in ~milliseconds.
            try:
                warnings = _collect_registry_warnings()
                self._respond_json({
                    "status": "validated",
                    "warning_count": len(warnings),
                    "warnings": warnings,
                    "helper_anchor_check": _helper_anchor_check_state(),
                })
            except Exception as exc:
                logger.error(f"Error validating registries: {exc}\n{traceback.format_exc()}")
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
            "entity-types": lambda: self._entity_types(params),
            "keys": lambda: self._keys(rest, params),
            "raw": lambda: self._raw(rest),
            "loc-keys": lambda: self._loc_keys(rest),
            "localize": lambda: self._localize(rest),
            "unlocalize": lambda: self._unlocalize(rest, params),
            "search": lambda: self._search(params),
            "laws": lambda: self._laws(rest),
            "technologies": lambda: self._technologies(rest, params),
            "buildings": lambda: self._buildings(rest, params),
            "companies": lambda: self._companies(rest, params),
            "building-companies": lambda: self._building_companies(rest),
            "goods": lambda: self._goods(),
            "combat-units": lambda: self._combat_units(),
            "ideologies": lambda: self._ideologies(rest),
            "movements": lambda: self._movements(rest),
            # Analytical endpoints
            "movement-stances": lambda: self._movement_stances(rest, params),
            # Party types and their merged join_weight terms (#1164)
            "parties": lambda: self._parties(rest, params),
            # Strategic region <-> state region (#917)
            "strategic-regions": lambda: self._strategic_regions(rest),
            "state-region": lambda: self._state_region(rest),
            # Who owns each state at game start (#901)
            "state-history": lambda: self._state_history(rest, params),
            # Prestige goods per base good, against the engine's cap (#749)
            "prestige-goods": lambda: self._prestige_goods(params),
            "references": lambda: self._references(rest),
            # Vanilla's own script, read from the installed game (#1563)
            "vanilla-refs": lambda: self._vanilla_refs(rest, params),
            "culture-reads": lambda: self._culture_reads(rest, params),
            "formables": lambda: self._formables(params),
            "diff": lambda: self._diff(rest, params),
            # Another mod's entries that land on ours, and which side wins (#1170)
            "external-mod-overlap": lambda: self._external_mod_overlap(rest, params),
            "tech-tree": lambda: self._tech_tree(rest),
            "modifier-search": lambda: self._modifier_search(params),
            "modifier-grants": lambda: self._modifier_grants(rest, params),
            "unlocked-by": lambda: self._unlocked_by(rest),
            "tech-unlocks": lambda: self._tech_unlocks(rest, params),
            "annotators": lambda: self._annotators(),
            "filter": lambda: self._filter(rest, params),
            # New structured endpoints
            "events": lambda: self._events(rest, params),
            "event-balance": lambda: self._event_balance(rest, params),
            # Event magnitude audit (hardcoded fast-scaling values)
            "event-magnitude-audit": lambda: self._event_magnitude_audit(params),
            # Event dispatch graph + context audit (system gating, unchosen actions)
            "event-dispatch": lambda: self._event_dispatch(rest),
            "event-context-audit": lambda: self._event_context_audit(params),
            "institutions": lambda: self._institutions(rest),
            "production-methods": lambda: self._production_methods(rest, params),
            # Employment per valid PM combination, by profession (#990)
            "pm-employment": lambda: self._pm_employment(rest, params),
            "journal-entries": lambda: self._journal_entries(rest),
            "treaty-articles": lambda: self._treaty_articles(rest),
            "diplomatic-actions": lambda: self._diplomatic_actions(rest),
            "decisions": lambda: self._decisions(rest),
            "script-values": lambda: self._script_values(rest),
            "scripted-effects": lambda: self._scripted_effects(rest),
            "scripted-triggers": lambda: self._scripted_triggers(rest),
            # Inverse of the callers index: call sites whose callee is gone
            "scripted-helpers": lambda: self._scripted_helpers(rest, params),
            # Calls whose arguments don't match the callee's $X$ names (#732)
            "script-args": lambda: self._script_args(rest, params),
            # How each site uses a variable or variable list (#973)
            "variable-usage": lambda: self._variable_usage(rest, params),
            # Which accessors vanilla loc and GUI chain on a data type (#1246)
            "loc-accessors": lambda: self._loc_accessors(rest, params),
            "decrees": lambda: self._decrees(rest),
            "principles": lambda: self._principles(rest),
            "amendments": lambda: self._amendments(rest),
            "on-actions": lambda: self._on_actions(rest),
            # Inverse: the on-actions that run an effect / fire an event (#333)
            "on-action-callers": lambda: self._on_action_callers(rest),
            # Technology effects endpoint
            "technology-effects": lambda: self._technology_effects(rest),
            # Engine docs endpoints
            "engine-docs": lambda: self._engine_docs(rest, params),
            # Developer reference docs (.md files from base game)
            "dev-docs": lambda: self._dev_docs(rest, params),
            # GUI render-site lookup (loc key -> GUI files; entity field -> GUI files)
            "gui": lambda: self._gui(rest, params),
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
            "placeholder-icons": lambda: self._placeholder_icons(params),
            # Generator-ownership map for auto-generated mod files
            "auto-generated": lambda: self._auto_generated(),
            # Game logs (debug.log, error.log, game.log, …)
            "logs": lambda: self._logs(rest, params),
            # Convenience endpoints — thin wrappers over /keys/<EntityType>.
            "cultures": lambda: self._vocab_endpoint("culture"),
            "religions": lambda: self._vocab_endpoint("religion"),
            "interest-groups": lambda: self._vocab_endpoint("ig"),
            "law-groups": lambda: self._vocab_endpoint("law_group"),
            # The vocab wrapper plus the parent_group hierarchy (#383)
            "building-groups": lambda: self._building_groups(rest),
            "pop-types": lambda: self._vocab_endpoint("poptype"),
            "country-ranks": lambda: self._vocab_endpoint("country_rank"),
            "terrain": lambda: self._vocab_endpoint("terrain"),
            "discrimination-traits": lambda: self._vocab_endpoint("discrimination_trait"),
        }
        handler = dispatch.get(ep)
        if handler is None:
            raise NotFound(ep)
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
            "access": (
                "Loopback only: a request whose Host header doesn't name this "
                f"server (127.0.0.1/localhost/[::1], port {self._bind_port()}), or "
                "that carries a cross-site Origin, is refused with 403. (#254)"
            ),
            "post": {
                "/reload": (
                    "Re-parse mod + vanilla; runs post-load generators and audits. "
                    "Flags: ?engine_only=true skips ModState rebuild; "
                    "?mod_only=true reuses the cached vanilla parse (fast); "
                    "?audits_only=true skips the file-rewriting generators (only runs the audits). "
                    "?mod_only=true&audits_only=true is the fast 'verify my edits' path "
                    "(~25s vs ~90s full, no working-tree side effects beyond docs/engine/*_report.md)."
                ),
            },
            "get": [
                {"path": "/status", "desc": "Server uptime, entity-type list, engine-docs freshness, vanilla-snapshot staleness."},
                {"path": "/help", "desc": "This endpoint inventory."},
                {"path": "/entity-types", "desc": "List of every entity type the parser exposes."},
                {"path": "/keys/<EntityType>", "desc": "All entity IDs of a given type (e.g. /keys/Buildings)."},
                {"path": "/raw/<EntityType>/<id>", "desc": "Raw parsed AST for one entity."},
                {"path": "/loc-keys/<EntityType>/<id>", "desc": "Resolve the stable family of loc keys an entity exposes (name/desc/...) — see LOC_KEY_FAMILIES."},
                {"path": "/localize/<key>", "desc": "Resolve a localization key to its English string."},
                {"path": "/unlocalize/<text>", "desc": "Reverse-lookup loc keys whose value matches a substring. Also accepts ?q=<text> (use it when the text contains a slash)."},
                {"path": "/search?q=<text>", "desc": "Full-text search across mod + vanilla parsed entities."},
                {"path": "/laws/<id?>", "desc": "Laws and law groups; omit id for the index."},
                {"path": "/technologies/<id?>", "desc": "Tech entries and tree relationships."},
                {"path": "/buildings/<id?>", "desc": "Building defs incl. PMG list."},
                {"path": "/companies?flavored=yes|no&source=mod|vanilla|all", "desc": "Merged company rosters, prosperity effects, flagships and per-flavored-bucket statistics."},
                {"path": "/building-companies/<building_id>", "desc": "Companies listing a building in their roster or extension roster."},
                {"path": "/goods", "desc": "Goods catalog."},
                {"path": "/vanilla-refs/<name>?depth=N", "desc": "Vanilla's own script, read from the installed game (#1563; 503 without one): the top-level vanilla entities in common/ and events/ whose body mentions <name>, N steps up, and the journal entries, on-actions and decisions among them. The first call reads the install (half a minute or more)."},
                {"path": "/culture-reads/<culture>?as=primary|pop|homeland|any", "desc": "Where vanilla tests cu:<culture> (#1563, needs the game): one row per file and entity with count, the keys the tests sit under, and the journal entries the entity belongs to or is reached from."},
                {"path": "/formables?lists_culture=<culture>", "desc": "country_formation tags, vanilla's and the mod's (#1563, needs the game): the cultures the tag's country definition lists, exists_at_start, use_culture_states, source vanilla|mod|both."},
                {"path": "/combat-units", "desc": "Combat unit type/group catalog."},
                {"path": "/ideologies/<id?>", "desc": "Ideology defs and IG-stance maps."},
                {"path": "/movements/<id?>", "desc": "Political movements (mod ∪ vanilla): category, ideology, set_core_ideology alternates, creation_trigger keys and tech gate (#838)."},
                {"path": "/movement-stances?lawgroup=<g>|law=<l>[&current=<law>]", "desc": "Each movement's stance on every law of a group (variants take the parent's; unnamed laws neutral) and two readings of backing: unbacked_laws (no movement rates the law approve or better) and never_backed_laws (no movement rates it above any other law of the group); current= (mode=comparative) lists the laws each rates above it. /movement-stances/gaps: law groups no movement rates, and every group's unbacked and never-backed laws (#838)."},
                {"path": "/parties/<key?>?desc=<desc>", "desc": "Party types (mod ∪ vanilla, #1164): source vanilla|mod|both, defining files, the file whose join_weight the merged party carries (an injected join_weight replaces the field), and join_weight_terms, the desc of each term in source order (a desc-less term as `value = 0` / `if = {...}`). ?desc= keeps the parties naming it; /<key> adds per-term detail. Merged AST: /raw/Parties/<key>."},
                {"path": "/strategic-regions/<name?>", "desc": "Strategic regions (mod ∪ vanilla, #917): the state regions each holds. /state-region/<STATE_X> is the inverse."},
                {"path": "/state-region/<STATE_X>", "desc": "The strategic region a state region is in (#917)."},
                {"path": "/state-history/<STATE_X?>?country=<TAG>&provinces=true", "desc": "Who owns each state on the start date (#901): one part per owning country, with its province count and the hubs (city, port, farm, mine, wood) it holds, plus homelands and claims. ?country= lists what a tag starts with. Works from vanilla_parsed/ with no game install."},
                {"path": "/prestige-goods?base_good=<good>", "desc": "Prestige goods per base good (#749): origin vanilla|mod, prestige_bonus, the companies listing each, and count against the engine's cap of 3 per base good."},
                {"path": "/production-methods/<id?>", "desc": "Production methods (and their groups). Pass a PMG or PM id."},
                {"path": "/pm-employment/<building>?select=<pm|glob>[,...]&bucket=level_scaled|workforce_scaled|unscaled|all&limit=", "desc": "Per-profession employment of every valid PM combination (pm_employment_audit's rules), grouped by identical totals with a count and an example combination, plus min/max totals per bucket (#990). Without a building, ?select= runs it for every building with a matching PM."},
                {"path": "/journal-entries/<id?>", "desc": "Journal entries (mod-only)."},
                {"path": "/treaty-articles/<id?>[/loc-keys]", "desc": "Treaty articles catalog; /<id>/loc-keys returns the article's loc-key family."},
                {"path": "/diplomatic-actions/<id?>", "desc": "Diplomatic-action catalog with category (subject_relation/power_bloc/general) + pact metadata."},
                {"path": "/decisions/<id?>", "desc": "Decisions catalog."},
                {"path": "/script-values/<id?>", "desc": "Script value definitions."},
                {"path": "/script-args/<helper?>", "desc": "Scripted effect/trigger calls whose arguments don't match the callee's $X$ names (#732); with a helper, its params and every caller's unknown/missing args."},
                {"path": "/variable-usage/<name?>?kind=var|list&store=scope|global|local&unfiltered_by=<trigger>&patterns=false", "desc": "Every mod site that writes, reads or iterates a variable or variable list, with file:line, entity, op, scope hint and an iterator's limit (#973). unfiltered_by keeps the iterations whose limit names neither the trigger nor a scripted trigger that names it. Bare: every name with its counts (?prefix=)."},
                {"path": "/loc-accessors/<Type?>?context=&examples=&min_uses=", "desc": "Which accessors vanilla loc (and vanilla .gui when the game is installed) chains on a data type (#1246): each with its use count, per-context counts (events, notification, ui, gui, ...), the type it returns, and example expressions, plus the SCOPE.sX / gsX saved-scope accessor for the type. <Type> is PoliticalLobby, political_lobby or politicallobby. ?context= keeps only uses in that context. Bare: every type with its use count."},
                {"path": "/decrees/<id?>", "desc": "Decree catalog."},
                {"path": "/on-actions/<id?>", "desc": "On-actions as the engine merges them (#333): every declaration of <id> in load order (sources: file, line, on_actions, events, random_events, chance_to_happen, fields), merged (on_actions and events added up; random_events only when one declaration sets it; null under a directive), fields_set_more_than_once (effect: the later file's wins, a documented rule), fired_by, warnings, and raw (the store's last-read block). Vanilla's declarations are read only with a game install: check vanilla_indexed / origin. Bare: the on-actions the mod declares, with their files."},
                {"path": "/on-action-callers/<scripted_effect|event_id|on_action>", "desc": "The mod on-actions that reach a scripted effect, an event or an on-action, through any chain of scripted effects and events, each with file:line, per-hop guards and the roots it hangs from (#333). Callers of other kinds (journal-entry pulses, buttons, decisions) are not followed: they are in not_followed, so count 0 is 'nothing calls it' only when not_followed, unreached and passed_as_parameter are empty. A row is the shortest route, not the only one: guards_complete false means other_routes exist. Mod script only; several seconds a call."},
                {"path": "/events/<id?>", "desc": "Events (mod-only)."},
                {"path": "/event-balance/<id?>", "desc": "Event option / fast-scaling magnitude analysis."},
                {"path": "/institutions/<id?>", "desc": "Institutions catalog."},
                {"path": "/references/<entity>", "desc": "Where in the parsed corpus an entity is referenced."},
                {"path": "/tech-tree/<id?>", "desc": "Tech-tree adjacency view."},
                {"path": "/tech-unlocks/<tech>", "desc": "What a tech unlocks (PMs, buildings, laws, etc.)."},
                {"path": "/unlocked-by/<entity>", "desc": "Inverse of tech-unlocks: what gates an entity."},
                {"path": "/modifier-search?q=<name>", "desc": "Validate / discover modifier keys against the engine catalog."},
                {"path": "/modifier-grants/<name>?scope=both&entity_types=&effective=", "desc": "Reverse lookup: every entity in any common/ directory (law, tech, principle, country rank, institution, company, PM, trait, static modifier, ...) that GRANTS modifier <name>, with file:line + value + block. Reports entity_types_scanned; vanilla rows the mod REPLACEs carry shadowed_by."},
                {"path": "/modifier-patterns/<sub?>", "desc": "Modifier pattern catalog and discovered families."},
                {"path": "/engine-docs/<type>/<name?>", "desc": "Engine reference (effects/triggers/modifiers/event-targets/on-actions/custom-localization). With <name>: that one entry, or 404 with did_you_mean. Listing: ?q=&scope=&mask=&origin=&group=, capped at ?limit= (default 500); check `truncated` (`count` is the filtered total, `returned` the entries sent). Also /engine-docs/origin/<name> (every type), /engine-docs/usage/<name> (vanilla call sites), /engine-docs/loc-functions/<name?>."},
                {"path": "/dev-docs/<section?>", "desc": "Vanilla developer-reference markdown docs."},
                {"path": "/technology-effects/<tech>", "desc": "Aggregate of all effects applied by a tech."},
                {"path": "/event-magnitude-audit", "desc": "Hardcoded fast-scaling event-value audit."},
                {"path": "/event-dispatch/<event_id>", "desc": "Every site that fires a mod event (trigger_event, on-action lists, via scripted effects incl. $EVENT$ helpers), with scope switches, enclosing limit/trigger guards, whether the recipient chose it, and which mod systems gate it."},
                {"path": "/event-context-audit?check=&event_id=&show_reviewed=", "desc": "event_context_audit flags: system_ungated / unchosen_self_action / imputed_foreign_action."},
                {"path": "/gui/placeholder-textures?include_overrides=true&unlisted_only=true&file=<gui/…>&format=text", "desc": "Vanilla textures the mod's own GUI widgets draw (#1484): per file, each texture path with where it resolves (vanilla|missing), its kind (icon|ui_mark|chrome), its lines, and the *_gui_icons.md line that accounts for it. summary.unlisted is the work list: vanilla icons no icons doc names. Overrides of vanilla panels are left out by default."},
                {"path": "/gui/render-sites/<loc_key>", "desc": "Every GUI file:line that references <loc_key> via text/tooltip/raw_text/... — mod + vanilla."},
                {"path": "/gui/render-paths/<EntityType>?field=<role>", "desc": "Every GUI file:line that renders <field> of <EntityType> via [DataType.GetX]. Fields: name/desc/icon/tooltip."},
                {"path": "/unlocalized", "desc": "Mod-introduced keys missing English loc."},
                {"path": "/vocabularies/<name?>", "desc": "Placeholder vocab tables (cultures, religions, IGs, ...)."},
                {"path": "/validate/<id?>", "desc": "Mod-vs-engine validation report."},
                {"path": "/external-mod-overlap?path=<mod root>&trace=true", "desc": "Read-only compatibility check of another mod (a Workshop folder or any mod root) against this one (#1170): keys of common/ databases both define with a load-order verdict (ours_wiped / theirs_wiped / both_merge / both_wiped / depends_on_playset / undetermined; facts: scripting_best_practices.md § Load Order (probed 2026-10-26)), defines both set, shared on_action hooks and effect conflicts, event namespaces and ids, English loc keys, and same-path files (gui/ included). Also `python3 external_mod_overlap.py <root>`."},
                {"path": "/external-mod-overlap/state[/<EntityType>[/<key>]]?path=<mod root>&refresh=true", "desc": "This mod's ModState with another mod's common/ entries layered in by the probed load order (#1184): the summary (keys recomputed per entity type, by status: changed / added / removed / undetermined / parse_failed / unchanged / not_created), one type's keys, or one key's merged entry (value as /raw gives it, the server's value, every definition, the simulated load, and every candidate when an unknown decides it). Cached per path until a reload."},
                {"path": "/duplicate-images", "desc": "Detect duplicated unique-per-entity image fields."},
                {"path": "/placeholder-icons", "desc": "Classify every mod-set icon: borrowed vanilla, shared, unique, stand-in or missing."},
                {"path": "/auto-generated", "desc": "Generator-ownership map for auto-generated mod files."},
                {"path": "/logs/<which?>", "desc": "Game logs (debug / error / game). Use ?include_external=true to keep third-party-mod entries."},
                {"path": "/annotators", "desc": "List of available ?annotate=<name> post-processors."},
                {"path": "/filter/<EntityType>", "desc": "Server-side filter over an entity collection."},
                {"path": "/cultures", "desc": "Culture vocab (thin wrapper over /keys/Cultures)."},
                {"path": "/religions", "desc": "Religion vocab."},
                {"path": "/interest-groups", "desc": "IG vocab."},
                {"path": "/law-groups", "desc": "Law-group vocab."},
                {"path": "/building-groups", "desc": "Building-group vocab; each group also carries parent_group (merged), origin (vanilla / mod / mod-injected / mod-replaced) and construction_efficiency_modifier (#383). An entry with alias_of is the prefix-less spelling, not a group."},
                {"path": "/building-groups/<id>[/reach]", "desc": "One group: ancestors, children, descendants, the buildings directly in it and the mod files defining it. /reach: every building a building_group_<id>_* modifier applies to, walking descendants (#383)."},
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
        # Bootstrap precondition: refuse `ready` (HTTP 503) when vanilla data
        # didn't materialize. cloud_setup.sh's existing `curl -sf` readiness
        # gate then naturally fails loud after the 180 s ceiling instead of
        # running the audit blind. See issue #93 for the failure mode.
        if not _vanilla_data_loaded():
            raise _ServiceNotReady({
                "status": "degraded",
                "ready": False,
                "pid": os.getpid(),
                "mod_path": mod_path,
                "reason": (
                    f"Vanilla data not loaded — {base_game_path}/game/common "
                    "is missing or empty and no usable vanilla_parsed/ "
                    "snapshot was loaded. Check VIC3_BASE_GAME (local dev), "
                    "or build the snapshot: python3 vanilla_parsed.py build."
                ),
                "vanilla_source": _vanilla_source or None,
            })

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

        # docs/engine/ left unrendered by the last engine-docs load. A cold
        # start records no `last_reload`, so this is where a skip at startup
        # shows.
        if _engine_docs_warnings:
            skipped = _engine_docs_warnings[0]
            vanilla_block["render_skipped"] = True
            vanilla_block["render_skipped_reason"] = skipped["detail"]
            if skipped.get("missing"):
                vanilla_block["missing_logs"] = skipped["missing"]

        # Files ModState skipped because they failed to parse. Empty is the
        # expected state; anything here means that file's entities are missing
        # from every endpoint. Capped so a mass breakage can't bloat /status.
        parse_failures = list(getattr(ms, "parse_failures", []) or [])

        return {
            "status": "running",
            "ready": True,
            "pid": os.getpid(),
            # The checkout this server parses and regenerates. Lets a client
            # in another checkout (a worktree) tell it is not its own server:
            # test_reload_post_load only fires POST /reload on a match (#306).
            "mod_path": mod_path,
            "uptime_seconds": round(uptime, 1),
            "startup_seconds": round(startup_elapsed, 1),
            "entity_types": list(ms.mod_parsers.keys()),
            "localization_keys": len(ms.localization),
            "parse_failure_count": len(parse_failures),
            "parse_failures": parse_failures[:20],
            "engine_docs_timestamps": engine_mtimes,
            "engine_docs_age_days": age_days,
            "vanilla_snapshot": vanilla_block,
            # Where ModState's vanilla half came from — the committed
            # vanilla_parsed/ snapshot or a parse of the game files — and,
            # for the snapshot, whether it is fresh. Not to be confused with
            # `vanilla_snapshot` above (the engine-docs .log snapshot).
            "vanilla_source": dict(
                _vanilla_source,
                game_files_present=_vanilla_tree_present(),
                warnings=[w["detail"] for w in _vanilla_source_warnings],
            ),
            "versions": _compute_version_status(repo_head),
            "last_reload": _last_reload_warnings or None,
            "pattern_catalog_size": len(pattern_catalog),
            "discovered_patterns": len(discovered_patterns),
            # False means /scripted-effects/<id> and /scripted-helpers/unresolved
            # will pay the cold index build on this request (#293).
            "call_index_ready": _call_index_cache is not None,
        }

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

    # ---- response helpers -------------------------------------------------
    def _respond_json(self, data, status=200):
        what = f"{getattr(self, 'command', None) or 'request'} {getattr(self, 'path', '?')}"
        body, status = encode_response(data, status, what)
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
# File-rewriting generators. They regenerate mod content on disk from configs
# + vanilla data, so running them mid-audit dirties the working tree.
POST_LOAD_REGENERATORS = [
    ("pop_needs_curves",              "pop_needs_curves"),
    ("apply_ideologies",              "apply_ideologies"),
    ("ig_feminism",                   "ig_feminism"),
    ("pm_costs",                      "pm_costs"),
    ("resources",                     "resources"),
    ("gen_pb_principle_unlock_descs", "gen_pb_principle_unlock_descs"),
    ("gen_un_button_descs",           "gen_un_button_descs"),
    ("gen_carbon_capture_pms",        "gen_carbon_capture_pms"),
    ("gen_law_consistency",           "gen_law_consistency"),
    ("gen_company_building_cleanup",  "scripts.generators.gen_company_building_cleanup"),
    ("gen_covert_tech_theft",         "scripts.generators.gen_covert_tech_theft"),
    ("gen_seabed_basins",             "scripts.generators.gen_seabed_basins"),
    ("gen_launch_windows",            "scripts.generators.gen_launch_windows"),
    ("gen_solar_sites",               "scripts.generators.gen_solar_sites"),
    ("gen_space_fleets",              "scripts.generators.gen_space_fleets"),
    ("gen_culture_merges",            "scripts.generators.gen_culture_merges"),
    ("organize_loc",                  "organize_loc"),
    ("gen_event_inventory",           "gen_event_inventory"),
    # Keep LAST: prepend UTF-8 BOM to any mod .txt the generators above (or a
    # hand-authored file) left without one, so the engine stops warning. It's a
    # file-rewriting generator, so it lives here (not in POST_LOAD_AUDITS) and
    # is skipped on audits_only / mod_only fast reloads. (#148)
    ("bom_normalizer",                "bom_normalizer"),
]

# Read-only audits that surface findings without writing files. Safe to run
# repeatedly mid-audit (see POST /reload?audits_only=true).
POST_LOAD_AUDITS = [
    ("event_magnitude_audit",         "event_magnitude_audit"),
    ("modifier_visibility_audit",     "modifier_visibility_audit"),
    ("kill_character_audit",          "kill_character_audit"),
    ("loc_coverage_audit",            "loc_coverage_audit"),
    ("gui_reference_audit",           "gui_reference_audit"),
    ("concept_reference_audit",       "concept_reference_audit"),
    ("localization_accessor_audit",   "localization_accessor_audit"),
    ("mod_structure_audit",           "mod_structure_audit"),
    ("load_order_audit",              "load_order_audit"),
    ("loc_render_audit",              "loc_render_audit"),
    ("any_limit_audit",               "any_limit_audit"),
    ("iterator_limit_audit",          "iterator_limit_audit"),
    ("modifier_multiplier_var_audit", "modifier_multiplier_var_audit"),
    ("je_multiplier_scope_audit",    "je_multiplier_scope_audit"),
    ("pm_employment_audit",           "pm_employment_audit"),
    ("orphaned_event_audit",          "orphaned_event_audit"),
    ("effect_trigger_validity_audit", "effect_trigger_validity_audit"),
    ("duplicate_key_audit",           "duplicate_key_audit"),
    ("modifier_field_audit",          "modifier_field_audit"),
    ("attitude_key_audit",            "attitude_key_audit"),
    ("event_image_audit",             "event_image_audit"),
    ("treaty_leverage_side_audit",    "treaty_leverage_side_audit"),
    ("event_context_audit",           "event_context_audit"),
    ("trigger_event_cycle_audit",     "trigger_event_cycle_audit"),
    ("silent_variable_audit",         "silent_variable_audit"),
    ("prev_scope_audit",              "prev_scope_audit"),
    ("container_timed_variable_audit", "container_timed_variable_audit"),
    ("je_immediate_reset_audit",      "je_immediate_reset_audit"),
    ("script_loc_reference_audit",    "script_loc_reference_audit"),
    ("empty_effect_audit",            "empty_effect_audit"),
    ("change_variable_clamp_audit",   "change_variable_clamp_audit"),
    ("building_scope_variable_audit", "building_scope_variable_audit"),
    ("variable_guard_audit",          "variable_guard_audit"),
    ("principle_tier_audit",          "principle_tier_audit"),
    ("prestige_good_roster_audit",    "prestige_good_roster_audit"),
    ("amendment_reachability_audit",  "amendment_reachability_audit"),
    ("ideology_lawgroup_audit",       "ideology_lawgroup_audit"),
    ("roster_membership_audit",      "roster_membership_audit"),
    ("script_argument_audit",         "script_argument_audit"),
    ("modifier_duration_audit",       "modifier_duration_audit"),
    ("loc_script_value_audit",        "loc_script_value_audit"),
    ("loc_root_context_audit",        "loc_root_context_audit"),
    ("texture_reference_audit",       "texture_reference_audit"),
    ("long_tooltip_audit",            "long_tooltip_audit"),
    ("hidden_modifier_audit",         "hidden_modifier_audit"),
    ("button_reason_audit",           "button_reason_audit"),
    ("faith_scene_audit",             "faith_scene_audit"),
    ("sol_fraction_audit",            "sol_fraction_audit"),
    ("delayed_event_trigger_audit",   "delayed_event_trigger_audit"),
]

POST_LOAD_GENERATORS = POST_LOAD_REGENERATORS + POST_LOAD_AUDITS

# Regenerators that read vanilla game FILES under <base_game_path>/game rather
# than ModState's parsed vanilla, so vanilla_parsed/ cannot stand in for them.
# With no game files on disk (a cloud session running from vanilla_parsed/)
# they are skipped, and the reload says so: run blind, apply_ideologies would
# rewrite common/ideologies/modified.txt as a bare header and the rest would
# crash. gen_law_consistency and pm_costs are not here: they read only parsed
# vanilla (law and ideology structure, goods prices), taken from
# `mod_state.base_parsers`, so they run either way and reproduce their
# committed outputs from the snapshot byte for byte (#624).
VANILLA_FILE_REGENERATORS = frozenset({
    "pop_needs_curves",
    "apply_ideologies",
    "ig_feminism",
    "resources",
})

# Regenerators that run without vanilla files but also write outputs cut from
# raw vanilla text. Without usable files the chain calls
# `regenerate(mod_state, vanilla_files=False)`, which leaves those outputs as
# committed; the reload warning names them. {label: those outputs}.
PARTIAL_VANILLA_FILE_REGENERATORS = {
    "pm_costs": (
        "docs/engine/commented_vanilla_pms.txt",
        "docs/engine/commented_vanilla_military_units.txt",
    ),
}


# Return-dict keys whose nonzero values indicate "actionable issue surfaced
# by this generator." Audits use a small set of conventional names; if a new
# audit invents one, add it here so the warning fires automatically. A bool
# True counts (it is an int): texture_reference_audit's `catalog_stale` says
# the committed asset catalog no longer matches the install, so CI resolves
# against stale vanilla until `--bootstrap` reruns.
_POST_LOAD_WARN_KEYS = ("unreviewed", "hard_fails", "catalog_stale")

# Most-recent post-load run's actionable findings. Reset on every
# _run_post_load_generators call. Read by /reload POST handler so callers
# see "the reload succeeded but you have N new sub-threshold modifiers"
# without having to scrape the server log.
_post_load_warnings: list[dict] = []

# Most-recent POST /reload's full warning set (post-load audits + registry
# validation), stamped with when it ran and the flags used. Surfaced as
# `last_reload` in /status so an operator can see the previous reload's findings
# without re-triggering a ~90s reload. Mirrors the _post_load_warnings pattern.
_last_reload_warnings: dict = {}

# Mod-relative paths the file-writing post-load regenerators changed on the most
# recent run (content-compared, so an unconditional rewrite of identical bytes
# doesn't count). Reset on every _run_post_load_generators call; surfaced as
# `generators_wrote_files` in the POST /reload body. (#242)
_post_load_wrote_files: list[str] = []

# True when the mod side was re-parsed after those writes, so the audits in the
# same chain (and /raw, /localize) saw the regenerated content.
_post_load_reparsed: bool = False

# How many trailing traceback lines a failure warning carries. Enough to name
# the raising frame without dumping the whole stack into every reload response.
_POST_LOAD_TRACEBACK_TAIL_LINES = 6

# Subtrees and suffixes the file-writing generators can touch. Snapshotted
# before/after the regenerator chain to detect writers that ran after the parse.
# map_data/ is deliberately out: `resources` rewrites state_regions there, but
# ModState registers no entity type for it, so a write can't stale the parse and
# re-parsing wouldn't pick it up. docs/engine/ is audit output, not mod content.
_WRITER_WATCH_DIRS = ("common", "events", "localization")
_WRITER_WATCH_SUFFIXES = (".txt", ".yml")


def _failure_warning(label: str, module_name: str, exc: BaseException) -> dict:
    """Shape a crashed post-load step as a reload warning entry."""
    tail = traceback.format_exc().rstrip().splitlines()[-_POST_LOAD_TRACEBACK_TAIL_LINES:]
    return {
        "label": label,
        "module": module_name,
        "error": f"{type(exc).__name__}: {exc}",
        "traceback_tail": "\n".join(tail),
    }


def _snapshot_mod_text_files(root: Optional[str] = None) -> dict:
    """Map mod-relative path -> content digest for every tracked text file the
    post-load regenerators could rewrite.

    Content-hashed rather than stat-compared on purpose: several generators
    (apply_ideologies, pop_needs_curves, …) rewrite their output file
    unconditionally, so mtime/size alone would report a write on every single
    reload and trigger a pointless re-parse. ~350 files / ~10 MB, so both
    snapshots together cost well under a second. Unreadable files are skipped.
    """
    root = root or mod_path
    snapshot: dict = {}
    for sub in _WRITER_WATCH_DIRS:
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for file_name in filenames:
                if not file_name.endswith(_WRITER_WATCH_SUFFIXES):
                    continue
                file_path = os.path.join(dirpath, file_name)
                try:
                    with open(file_path, "rb") as fh:
                        digest = hashlib.blake2b(fh.read(), digest_size=16).hexdigest()
                except OSError:
                    continue
                rel = os.path.relpath(file_path, root).replace(os.sep, "/")
                snapshot[rel] = digest
    return snapshot


def _changed_files(before: dict, after: dict) -> list:
    """Mod-relative paths whose content differs between two snapshots."""
    changed = {p for p, digest in after.items() if before.get(p) != digest}
    changed |= {p for p in before if p not in after}
    return sorted(changed)


def _reparse_mod_after_writes(mod_state) -> Optional[dict]:
    """Re-parse the mod side ONCE after the file-writing generators wrote, so
    the read-only audits in the same chain evaluate what was just generated
    (rather than the pre-generation parse) and /raw + /localize serve it without
    a second reload.

    Called at most once per _run_post_load_generators — it never re-runs the
    generators, so there is no loop. Returns a warning dict on failure, else
    None.
    """
    global _tech_unlocks_index_cache, _last_validation_report, _company_catalog_cache
    global _party_catalog_cache, _state_history_cache
    t0 = time.monotonic()
    try:
        mod_state.reload_mod(mod_paths)
        # Rebuild loc the same way _load_mod_state's mod_only path does:
        # cached vanilla snapshot, then the mod layers on top.
        if _VANILLA_LOC_CACHE is not None:
            mod_state.localization = dict(_VANILLA_LOC_CACHE)
            mod_state._reverse_loc = None
        for loc_dir in [
            os.path.join(mod_path, "localization", "english"),
            os.path.join(mod_path, "localization", "english", "replace"),
        ]:
            if os.path.isdir(loc_dir):
                mod_state.add_localization(loc_dir)
        _tech_unlocks_index_cache = None
        _company_catalog_cache = None
        _party_catalog_cache = None
        _state_history_cache = None
        _overlap_state_cache.clear()
        _invalidate_call_index()
        _last_validation_report = None
        _annotator_compute_cache.clear()
    except Exception as exc:  # noqa: BLE001
        logger.exception("[post-load] re-parse after generator writes FAILED")
        return _failure_warning(
            "post_load_reparse", "mod_state_server._reparse_mod_after_writes", exc
        )
    logger.info(
        f"[post-load] re-parsed mod state after generator writes "
        f"({time.monotonic() - t0:.1f}s)"
    )
    return None


def _collect_registry_warnings() -> list[dict]:
    """Load both known-noise registries and return their validation warnings as
    [{label, detail}]. Shared by POST /reload and POST /validate/registries so
    the two stay in lockstep. Best-effort: logs and returns [] on failure.

    Also runs the helper-anchor check (#730): an entry anchored on a vanilla
    scripted effect, trigger or script value file the mod calls adds a
    `kind: "helper_anchor_mod_calls"` warning with its `entry`, `anchor`,
    `helper_file`, `mod_uses` and `advice` beside the `{label, detail}` pair.
    And the mod-only anchor check (#873): a vanilla entry anchored on a file
    only the mod has adds `kind: "mod_only_anchor"` with its `anchors`. Both
    need the vanilla game files and are skipped without them
    (`_helper_anchor_check_state`)."""
    warnings: list[dict] = []
    try:
        from game_log_reader import (
            helper_anchor_warnings as _helper_anchor_warnings,
            mod_only_anchor_warnings as _mod_only_anchor_warnings,
            load_vanilla_bug_registry as _load_vbr,
            load_mod_noise_registry as _load_mnr,
        )
        from script_helper_index import vanilla_game_dir
        _vbr_doc = os.path.join(mod_path, "docs", "vanilla", "vanilla_known_bugs.md")
        _mnr_doc = os.path.join(mod_path, "docs", "audits", "mod_known_noise.md")
        _vbr_refs, _, _, _vbr_warnings = _load_vbr(_vbr_doc)
        _mnr_refs, _, _, _mnr_warnings = _load_mnr(_mnr_doc)
        for w in _vbr_warnings:
            warnings.append({"label": "vanilla_bug_registry", "detail": w})
        for w in _mnr_warnings:
            warnings.append({"label": "mod_noise_registry", "detail": w})
        _vanilla_game = vanilla_game_dir()
        warnings += _helper_anchor_warnings(_vbr_refs, mod_path, _vanilla_game, "vanilla_bug_registry")
        warnings += _helper_anchor_warnings(_mnr_refs, mod_path, _vanilla_game, "mod_noise_registry")
        warnings += _mod_only_anchor_warnings(_vbr_refs, mod_path, _vanilla_game, "vanilla_bug_registry")
    except Exception as _exc:  # noqa: BLE001
        logger.warning(f"known-noise registry warning collection failed: {_exc}")
    return warnings


def _helper_anchor_check_state() -> str:
    """"ran", or why the helper-anchor registry check was skipped."""
    from script_helper_index import vanilla_game_dir
    if vanilla_game_dir():
        return "ran"
    return f"skipped: no vanilla game files under {base_game_path}/game"


def _record_reload_warnings(flags: dict, warnings: list, *,
                            wrote_files: Optional[list] = None,
                            reparsed: bool = False) -> None:
    """Persist the most recent reload's warning set for /status `last_reload`."""
    global _last_reload_warnings
    _last_reload_warnings = {
        "at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "flags": flags,
        "count": len(warnings),
        "warnings": warnings,
    }
    if wrote_files:
        _last_reload_warnings["generators_wrote_files"] = list(wrote_files)
        _last_reload_warnings["reparsed_after_generators"] = reparsed


def _run_generator_chain(mod_state, generators, *, vanilla_files=True) -> None:
    """Import and run each (label, module) in order, appending both actionable
    findings and hard failures to _post_load_warnings. One bad generator never
    stops the chain. With `vanilla_files=False` a PARTIAL_VANILLA_FILE_REGENERATORS
    member is told so (`regenerate(mod_state, vanilla_files=False)`)."""
    for label, module_name in generators:
        t0 = time.monotonic()
        try:
            mod = importlib.import_module(module_name)
            regenerate = getattr(mod, "regenerate", None)
            if not callable(regenerate):
                raise AttributeError(
                    f"module {module_name!r} has no callable `regenerate` "
                    f"(POST_LOAD_GENERATORS contract)"
                )
            partial = not vanilla_files and label in PARTIAL_VANILLA_FILE_REGENERATORS
            summary = regenerate(mod_state, vanilla_files=False) if partial else regenerate(mod_state)
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
                # Coverage counts (files audited, references checked, …) live
                # here rather than in the committed reports, where they would
                # re-diff on every PR that adds a file.
                counts = ""
                if isinstance(summary, dict):
                    counts = "".join(
                        f" {k}={v}" for k, v in summary.items()
                        if isinstance(v, int) and not isinstance(v, bool)
                    )
                logger.info(f"[post-load] {label} ok ({elapsed:.2f}s){counts}")
        except Exception as exc:  # noqa: BLE001
            # An ImportError, a crash inside regenerate(), or a missing
            # `regenerate` used to be logged and forgotten, so POST /reload
            # still answered `{"status": "reloaded"}` with no warnings while a
            # whole audit had silently not run. Record it as a warning. (#242)
            logger.exception(f"[post-load] {label} FAILED — continuing")
            _post_load_warnings.append(_failure_warning(label, module_name, exc))


def _run_post_load_generators(mod_state, *, audits_only=False, vanilla_files=True):
    """Run the post-load chain. `vanilla_files=False` (no usable vanilla game
    files; see _vanilla_files_unusable_reason) drops VANILLA_FILE_REGENERATORS,
    keeps PARTIAL_VANILLA_FILE_REGENERATORS off their raw-vanilla outputs, and
    records one `vanilla_files_missing` warning naming everything skipped —
    including generate_docs, which _load_mod_state skips for the same reason."""
    global _post_load_warnings, _post_load_wrote_files, _post_load_reparsed
    _post_load_warnings = []
    _post_load_wrote_files = []
    _post_load_reparsed = False
    regenerators = POST_LOAD_REGENERATORS
    if not vanilla_files:
        regenerators = [
            (label, module) for label, module in POST_LOAD_REGENERATORS
            if label not in VANILLA_FILE_REGENERATORS
        ]
        skipped = ["generate_docs"] + (
            [] if audits_only else
            [label for label, _ in POST_LOAD_REGENERATORS if label in VANILLA_FILE_REGENERATORS]
        )
        partial = {} if audits_only else {
            label: list(outputs)
            for label, outputs in PARTIAL_VANILLA_FILE_REGENERATORS.items()
        }
        detail = (
            f"{_vanilla_files_unusable_reason() or 'vanilla game files unusable'}, "
            f"so skipped {', '.join(skipped)}: they read those files "
            "directly, and vanilla_parsed/ holds only the parsed data. "
            "Their outputs on disk were left as they were, not regenerated."
        )
        if partial:
            detail += (
                " Also left as committed (cut from raw vanilla text; the rest of "
                "the generator ran from parsed vanilla): "
                + "; ".join(f"{label}: {', '.join(outs)}" for label, outs in partial.items())
                + "."
            )
        _post_load_warnings.append({
            "label": "vanilla_files_missing",
            "detail": detail,
            "skipped": skipped,
            "partially_skipped": partial,
        })
        logger.warning(f"[post-load WARN] {_post_load_warnings[-1]['detail']}")
    if os.environ.get("VIC3_SKIP_POST_LOAD_GENERATORS"):
        logger.info("[post-load] skipped via VIC3_SKIP_POST_LOAD_GENERATORS")
        return
    if audits_only:
        # No file-writing generators run, so nothing can invalidate the parse.
        _run_generator_chain(mod_state, POST_LOAD_AUDITS)
    else:
        before = _snapshot_mod_text_files()
        _run_generator_chain(mod_state, regenerators, vanilla_files=vanilla_files)
        _post_load_wrote_files = _changed_files(before, _snapshot_mod_text_files())
        if _post_load_wrote_files:
            logger.info(
                f"[post-load] regenerators rewrote {len(_post_load_wrote_files)} "
                f"file(s): {', '.join(_post_load_wrote_files[:5])}"
                + (" …" if len(_post_load_wrote_files) > 5 else "")
            )
            failure = _reparse_mod_after_writes(mod_state)
            if failure:
                _post_load_warnings.append(failure)
            else:
                _post_load_reparsed = True
        _run_generator_chain(mod_state, POST_LOAD_AUDITS)
    if _post_load_warnings:
        labels = ", ".join(w["label"] for w in _post_load_warnings)
        failures = sum(1 for w in _post_load_warnings if "error" in w)
        logger.warning(
            f"[post-load WARN] {len(_post_load_warnings)} post-load step(s) "
            f"surfaced actionable issues ({failures} crashed): {labels}"
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


def _refresh_digest_snapshot_path() -> None:
    """Re-resolve the Modding-Digests engine-docs snapshot after the digests step.

    This module's `from path_constants import` resolved it at import, before
    _ensure_modding_digests_fresh ran. On a fresh machine's first cold start
    the checkout didn't exist yet, so it was None and the engine docs fell back
    to the runtime path. A fast-forward can also add a newer version directory.
    """
    global vanilla_snapshot_docs_path_default
    fresh = path_constants.refresh("vanilla_snapshot_docs_path_default")
    if fresh != vanilla_snapshot_docs_path_default:
        logger.info(
            f"[digests] engine-docs snapshot now resolves to {fresh} "
            f"(was {vanilla_snapshot_docs_path_default})"
        )
    vanilla_snapshot_docs_path_default = fresh


# Snapshot of vanilla loc (English), populated on the first full load and
# reused by /reload?mod_only=true to skip re-reading vanilla .yml files.
# Refreshed on every full /reload (no flags) so vanilla bumps propagate.
_VANILLA_LOC_CACHE: Optional[dict] = None

# Warnings about where vanilla came from (stale vanilla_parsed/, unreadable
# snapshot, bad VIC3_VANILLA_SOURCE), set on every full load and repeated in
# every POST /reload `warnings` until the next full load clears them.
_vanilla_source_warnings: list[dict] = []


def _load_mod_state(*, audits_only: bool = False, mod_only: bool = False):
    global ms, startup_elapsed, _last_validation_report, _tech_unlocks_index_cache
    global _company_catalog_cache, _party_catalog_cache, _state_history_cache
    global _VANILLA_LOC_CACHE, _vanilla_source, _vanilla_source_warnings

    if mod_only and (ms is None or _VANILLA_LOC_CACHE is None):
        # mod_only is a fast incremental path; without cached state it has
        # no meaning. Fall back rather than failing so /reload?mod_only=true
        # always behaves usefully.
        logger.info("[reload] mod_only requested but no cached state; doing full load")
        mod_only = False

    mode_tag = " (mod-only)" if mod_only else ""
    if audits_only:
        mode_tag += " (audits-only)"
    logger.info(f"Loading mod state{mode_tag}…")
    t0 = time.time()
    # Layered states hold the old ModState's parsers (#1184).
    _overlap_state_cache.clear()

    if mod_only:
        try:
            ms.reload_mod(mod_paths)
        except Exception as e:
            logger.error(f"Failed to reload mod state: {e}\n{traceback.format_exc()}")
            raise
    else:
        # Vanilla is re-read: drop the overlap endpoint's vanilla index too.
        _overlap_vanilla_cache.clear()
        _vanilla_source, _vanilla_source_warnings = _choose_vanilla_source()
        for w in _vanilla_source_warnings:
            logger.warning(f"[vanilla] {w['detail']}")
        logger.info(
            f"[vanilla] source: {_vanilla_source['kind']} ({_vanilla_source['reason']})"
        )
        try:
            if _vanilla_source["kind"] == "vanilla_parsed":
                snapshot = vanilla_parsed.load(VANILLA_PARSED_DIR)
                ms = ModState(base_game_paths, mod_paths, vanilla_data=snapshot.data)
                # Vanilla files the snapshot build skipped, listed like the
                # ones a live parse skips.
                ms.parse_failures[:0] = snapshot.parse_failures
                ms.localization = dict(snapshot.localization)
            else:
                ms = ModState(base_game_paths, mod_paths)
        except Exception as e:
            logger.error(f"Failed to initialize ModState: {e}\n{traceback.format_exc()}")
            raise

    # Invalidate per-load caches so stale annotator outputs / inverted-index
    # entries don't leak across reloads.
    _last_validation_report = None
    _tech_unlocks_index_cache = None
    _company_catalog_cache = None
    _party_catalog_cache = None
    _state_history_cache = None
    _invalidate_call_index()
    _annotator_compute_cache.clear()

    # Localization: cache vanilla once, then layer mod (+ replace) on top
    # each load. On mod_only we reuse the snapshot to skip re-reading the
    # vanilla .yml files (typically the second-largest cost in a reload).
    if mod_only:
        ms.localization = dict(_VANILLA_LOC_CACHE)
        ms._reverse_loc = None
    elif _vanilla_source["kind"] == "vanilla_parsed":
        # Vanilla loc came with the snapshot (set above).
        _VANILLA_LOC_CACHE = dict(ms.localization)
    else:
        vanilla_loc_dir = os.path.join(base_game_path, "game", "localization", "english")
        try:
            if os.path.isdir(vanilla_loc_dir):
                ms.add_localization(vanilla_loc_dir)
            else:
                logger.warning(f"Localization directory not found: {vanilla_loc_dir}")
        except Exception as e:
            logger.error(f"Failed to load localization from {vanilla_loc_dir}: {e}")
        _VANILLA_LOC_CACHE = dict(ms.localization)
    for loc_dir in [
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

    if not mod_only:
        # Engine docs and dev reference docs come from vanilla / Modding-Digests
        # and don't change with mod edits — skip on mod_only reloads.
        try:
            _load_engine_docs()
        except Exception as e:
            logger.error(f"Failed to load engine docs: {e}\n{traceback.format_exc()}")

        try:
            _load_dev_reference_docs()
        except Exception as e:
            logger.error(f"Failed to load dev reference docs: {e}\n{traceback.format_exc()}")

    # Regenerate docs/engine/ text files from the freshly parsed data. Its
    # tech-unlock lines come from a raw scan of the vanilla files, so with none
    # (or outdated ones) on disk it would rewrite docs/engine/technologies.txt
    # from the wrong vanilla: skip it then, like VANILLA_FILE_REGENERATORS.
    vanilla_files = _vanilla_files_unusable_reason() is None
    if vanilla_files:
        try:
            from mod_state_script import generate_docs
            generate_docs(ms)
        except Exception as e:
            logger.error(f"Failed to regenerate docs: {e}\n{traceback.format_exc()}")

    # Run idempotent transformers that regenerate mod content from configs
    # + vanilla data (e.g. pop_needs_curves, apply_ideologies). See
    # POST_LOAD_GENERATORS above and docs/guides/python_tools.md for details.
    _run_post_load_generators(ms, audits_only=audits_only, vanilla_files=vanilla_files)

    # Last: the post-load chain's re-parse clears the callers index, so warm it
    # after that, not before (#293).
    _warm_call_index_async()


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
    _refresh_digest_snapshot_path()
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

    # Vanilla-version cross-check: loudly flag when the running game, the
    # ~/src/vic3 mirror HEAD, and the engine-docs snapshot don't agree — that
    # usually means a vanilla bump landed in one place but not the others, and
    # every engine-doc-backed validation is then quietly wrong.
    try:
        _vstat = _compute_version_status()
        if _vstat.get("mismatch"):
            logger.warning(
                "[VERSION MISMATCH] vanilla versions disagree — "
                f"live_game={_vstat.get('live_game')} "
                f"vanilla_clone_head={_vstat.get('vanilla_clone_head')} "
                f"engine_docs_source={_vstat.get('engine_docs_source')}. "
                "Refresh whichever is stale (see GET /status `versions`)."
            )
    except Exception as _vexc:  # noqa: BLE001
        logger.warning(f"version cross-check failed at startup: {_vexc}")
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
