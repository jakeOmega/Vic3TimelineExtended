"""
Mod State Server - persistent HTTP API for querying parsed mod/vanilla data.

Start:  python mod_state_server.py
        (loads all data once, then listens on http://127.0.0.1:8950)

Query:  Invoke-RestMethod http://localhost:8950/status
        Invoke-RestMethod http://localhost:8950/laws
        python mod_state_client.py laws
"""

import json
import logging
import os
import re
import sys
import time
import traceback
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

from mod_state import ModState
from path_constants import base_game_path, doc_path, mod_path

PORT = 8950

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_FILE = os.path.join(mod_path, "mod_state_server.log")

logger = logging.getLogger("mod_state_server")
logger.setLevel(logging.DEBUG)

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

_file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))

logger.addHandler(_console_handler)
logger.addHandler(_file_handler)

# ---------------------------------------------------------------------------
# Path configuration (mirrors mod_state_script.py)
# ---------------------------------------------------------------------------
base_game_paths = {
    "Building Groups": base_game_path + r"\game\common\building_groups",
    "Buildings": base_game_path + r"\game\common\buildings",
    "Technologies": base_game_path + r"\game\common\technology\technologies",
    "PM Groups": base_game_path + r"\game\common\production_method_groups",
    "PMs": base_game_path + r"\game\common\production_methods",
    "Ideologies": base_game_path + r"\game\common\ideologies",
    "Buy Packages": base_game_path + r"\game\common\buy_packages",
    "Character Interactions": base_game_path + r"\game\common\character_interactions",
    "Character Traits": base_game_path + r"\game\common\character_traits",
    "Combat Unit Groups": base_game_path + r"\game\common\combat_unit_groups",
    "Combat Unit Types": base_game_path + r"\game\common\combat_unit_types",
    "Company Types": base_game_path + r"\game\common\company_types",
    "Diplomatic Actions": base_game_path + r"\game\common\diplomatic_actions",
    "Diplomatic Plays": base_game_path + r"\game\common\diplomatic_plays",
    "Goods": base_game_path + r"\game\common\goods",
    "Institutions": base_game_path + r"\game\common\institutions",
    "Interest Groups": base_game_path + r"\game\common\interest_groups",
    "Law Groups": base_game_path + r"\game\common\law_groups",
    "Laws": base_game_path + r"\game\common\laws",
    "Mobilization Option Groups": base_game_path
    + r"\game\common\mobilization_option_groups",
    "Mobilization Options": base_game_path + r"\game\common\mobilization_options",
    "Modifier Types": base_game_path + r"\game\common\modifier_type_definitions",
    "Modifiers": base_game_path + r"\game\common\static_modifiers",
    "Pop Needs": base_game_path + r"\game\common\pop_needs",
    "Subject Types": base_game_path + r"\game\common\subject_types",
    "Script Values": base_game_path + r"\game\common\script_values",
    "Scripted Buttons": base_game_path + r"\game\common\scripted_buttons",
    "Journal Entries": base_game_path + r"\game\common\journal_entries",
    "Journal Entry Groups": base_game_path + r"\game\common\journal_entry_groups",
    "Decisions": base_game_path + r"\game\common\decisions",
    "Treaty Articles": base_game_path + r"\game\common\treaty_articles",
    "Religions": base_game_path + r"\game\common\religions",
    "Decrees": base_game_path + r"\game\common\decrees",
}

mod_paths = {
    "Building Groups": mod_path + r"\common\building_groups",
    "Buildings": mod_path + r"\common\buildings",
    "Technologies": mod_path + r"\common\technology\technologies",
    "PM Groups": mod_path + r"\common\production_method_groups",
    "PMs": mod_path + r"\common\production_methods",
    "Ideologies": mod_path + r"\common\ideologies",
    "Buy Packages": mod_path + r"\common\buy_packages",
    "Character Interactions": mod_path + r"\common\character_interactions",
    "Character Traits": mod_path + r"\common\character_traits",
    "Combat Unit Groups": mod_path + r"\common\combat_unit_groups",
    "Combat Unit Types": mod_path + r"\common\combat_unit_types",
    "Company Types": mod_path + r"\common\company_types",
    "Diplomatic Actions": mod_path + r"\common\diplomatic_actions",
    "Diplomatic Plays": mod_path + r"\common\diplomatic_plays",
    "Goods": mod_path + r"\common\goods",
    "Institutions": mod_path + r"\common\institutions",
    "Interest Groups": mod_path + r"\common\interest_groups",
    "Laws": mod_path + r"\common\laws",
    "Law Groups": mod_path + r"\common\law_groups",
    "Mobilization Option Groups": mod_path + r"\common\mobilization_option_groups",
    "Mobilization Options": mod_path + r"\common\mobilization_options",
    "Modifier Types": mod_path + r"\common\modifier_type_definitions",
    "Modifiers": mod_path + r"\common\static_modifiers",
    "Pop Needs": mod_path + r"\common\pop_needs",
    "Subject Types": mod_path + r"\common\subject_types",
    "Script Values": mod_path + r"\common\script_values",
    "Scripted Effects": mod_path + r"\common\scripted_effects",
    "Scripted Triggers": mod_path + r"\common\scripted_triggers",
    "Scripted Buttons": mod_path + r"\common\scripted_buttons",
    "Journal Entries": mod_path + r"\common\journal_entries",
    "Journal Entry Groups": mod_path + r"\common\journal_entry_groups",
    "Decisions": mod_path + r"\common\decisions",
    "On Actions": mod_path + r"\common\on_actions",
    "Treaty Articles": mod_path + r"\common\treaty_articles",
    "Religions": mod_path + r"\common\religions",
    "Decrees": mod_path + r"\common\decrees",
    "Events": mod_path + r"\events",
}

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
ms: ModState = None  # type: ignore[assignment]
startup_elapsed: float = 0.0
engine_docs: dict = {}  # Parsed engine documentation (effects, triggers, etc.)
dev_reference_docs: dict = {}  # .md files from base game common/ dirs


# ---------------------------------------------------------------------------
# Engine docs parser
# ---------------------------------------------------------------------------
ENGINE_DOCS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(mod_path)),  # Victoria 3 user dir
    "docs",
)

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


def _parse_modifiers_log(filepath: str) -> list[dict]:
    """Parse modifiers.log format:
    modifier_name:
      Mask: mask_type
      Name: Display Name
      Description: ...
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
        if stripped.startswith("---"):
            continue
        # New modifier entry: starts at column 0 and ends with ':'
        if stripped and not stripped[0].isspace() and stripped.endswith(":"):
            if current:
                entries.append(current)
            current = {"name": stripped[:-1], "mask": "", "display_name": "", "description": ""}
        elif current and stripped.startswith("  "):
            kv = stripped.strip()
            if kv.startswith("Mask:"):
                current["mask"] = kv.split(":", 1)[1].strip()
            elif kv.startswith("Name:"):
                current["display_name"] = kv.split(":", 1)[1].strip()
            elif kv.startswith("Description:"):
                current["description"] = kv.split(":", 1)[1].strip()
    if current:
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


def _group_similar_entries(entries: list[dict]) -> list[dict]:
    """Group entries that differ only by a building/entity name in the middle.
    E.g., building_coal_mine_throughput_add and building_iron_mine_throughput_add
    become a single pattern entry: building_{name}_throughput_add
    """
    # Build pattern groups by trying to find common prefix+suffix
    pattern_groups: dict[str, list[dict]] = {}
    ungrouped = []

    # Known patterns: building_{name}_something, interest_group_ig_{name}_something
    patterns = [
        (r'^(building_)(.+?)(_throughput_add|_throughput_mult|_max_level_add|_employees_add|_employees_mult|_mortality_mult|_unincorporated_throughput_add)$', 'building_{name}_{suffix}'),
        (r'^(building_group_bg_)(.+?)(_throughput_add|_throughput_mult|_tax_mult|_employee_mult|_urbanization_mult|_wages_mult|_fertility_mult|_expected_sol_mult)$', 'building_group_bg_{group}_{suffix}'),
        (r'^(interest_group_ig_)(.+?)(_pol_str_mult|_approval_add|_pop_attraction_mult)$', 'interest_group_ig_{ig}_{suffix}'),
        (r'^(country_institution_impact_)(.+?)(_mult)$', 'country_institution_impact_{institution}_mult'),
        (r'^(pop_)(.+?)(_political_strength_mult|_mortality_mult|_pol_str_mult)$', 'pop_{pop_type}_{suffix}'),
        (r'^(state_pop_type_)(.+?)(_mortality_mult)$', 'state_pop_type_{pop_type}_mortality_mult'),
    ]

    for entry in entries:
        name = entry.get("name", "")
        grouped = False
        for regex, template in patterns:
            m = re.match(regex, name)
            if m:
                # Build pattern key from prefix + placeholder + suffix
                suffix = m.group(3).lstrip("_") if m.lastindex >= 3 else ""
                pattern_key = template.replace("{suffix}", suffix)
                if pattern_key not in pattern_groups:
                    pattern_groups[pattern_key] = []
                pattern_groups[pattern_key].append(entry)
                grouped = True
                break
        if not grouped:
            ungrouped.append(entry)

    # Convert groups to summary entries
    grouped_entries = []
    for pattern_key, members in pattern_groups.items():
        example = members[0]
        member_names = sorted(set(m["name"] for m in members))
        grouped_entries.append({
            "pattern": pattern_key,
            "count": len(members),
            "members": member_names,
            "description": example.get("description", ""),
            "scopes": example.get("scopes", []),
            "mask": example.get("mask", ""),
        })

    return grouped_entries, ungrouped


def _load_engine_docs():
    """Parse all engine documentation files into structured data."""
    global engine_docs
    engine_docs = {}

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
                logger.info(f"Parsed engine doc {filename}: {len(engine_docs[key])} entries")
            except Exception as e:
                logger.error(f"Failed to parse engine doc {filename}: {e}")
                engine_docs[key] = []
        else:
            logger.warning(f"Engine doc not found: {filepath}")
            engine_docs[key] = []


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
        if parts == ["reload"]:
            try:
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
        }
        handler = dispatch.get(ep)
        if handler is None:
            raise KeyError(ep)
        return handler()

    # ---- endpoints --------------------------------------------------------
    def _status(self):
        return {
            "status": "running",
            "startup_seconds": round(startup_elapsed, 1),
            "entity_types": list(ms.mod_parsers.keys()),
            "localization_keys": len(ms.localization),
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

    # ---- response helpers -------------------------------------------------
    def _respond_json(self, data, status=200):
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Suppress default access-log noise
        pass


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
        base_game_path + r"\game\localization\english",
        mod_path + r"\localization\english",
        mod_path + r"\localization\english\replace",
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
    _load_mod_state()
    server = HTTPServer(("127.0.0.1", PORT), ModStateHandler)
    logger.info(f"Mod-state server running on http://127.0.0.1:{PORT}")
    print(f"\nMod-state server running on http://127.0.0.1:{PORT}")
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


if __name__ == "__main__":
    main()
