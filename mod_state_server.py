"""
Mod State Server - persistent HTTP API for querying parsed mod/vanilla data.

Start:  python mod_state_server.py
        (loads all data once, then listens on http://127.0.0.1:8765)

Query:  Invoke-RestMethod http://localhost:8765/status
        Invoke-RestMethod http://localhost:8765/laws
        python mod_state_client.py laws
"""

import json
import re
import sys
import time
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

from mod_state import ModState
from path_constants import base_game_path, doc_path, mod_path

PORT = 8765

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
}

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
ms: ModState = None  # type: ignore[assignment]
startup_elapsed: float = 0.0


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
            self._respond_json({"error": str(exc)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        parts = [unquote(p) for p in parsed.path.strip("/").split("/") if p]
        if parts == ["reload"]:
            try:
                _load_mod_state()
                self._respond_json({"status": "reloaded", "startup_seconds": startup_elapsed})
            except Exception as exc:
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
            "buildings": lambda: self._buildings(rest),
            "goods": lambda: self._goods(),
            "combat-units": lambda: self._combat_units(),
            "ideologies": lambda: self._ideologies(rest),
            # Analytical endpoints
            "references": lambda: self._references(rest),
            "tech-tree": lambda: self._tech_tree(rest),
            "modifier-search": lambda: self._modifier_search(params),
            "unlocked-by": lambda: self._unlocked_by(rest),
            "filter": lambda: self._filter(rest, params),
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
    def _buildings(self, parts):
        """GET /buildings[/<building_id>]"""
        buildings = ms.get_data("Buildings")
        if not buildings:
            return {"error": "Buildings data not loaded"}

        if parts:
            bid = parts[0]
            if bid not in buildings:
                raise KeyError(bid)
            return self._format_building_detail(bid, buildings[bid])

        return [
            self._format_building_summary(bid, raw)
            for bid, raw in buildings.items()
        ]

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
    print("Loading mod state… (this may take a minute)")
    t0 = time.time()
    ms = ModState(base_game_paths, mod_paths)
    ms.add_localization(base_game_path + r"\game\localization\english")
    ms.add_localization(mod_path + r"\localization\english")
    ms.add_localization(mod_path + r"\localization\english\replace")
    startup_elapsed = time.time() - t0
    print(f"Loaded in {startup_elapsed:.1f}s  "
          f"({len(ms.mod_parsers)} entity types, {len(ms.localization)} loc keys)")


def main():
    _load_mod_state()
    server = HTTPServer(("127.0.0.1", PORT), ModStateHandler)
    print(f"\nMod-state server running on http://127.0.0.1:{PORT}")
    print("Endpoints: /status  /laws  /technologies  /buildings  /goods")
    print("           /combat-units  /ideologies  /keys/<type>  /raw/<type>")
    print("           /localize/<key>  /unlocalize/<text>  /search?q=...")
    print("           POST /reload")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
