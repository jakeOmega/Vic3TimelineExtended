"""The entity routes: the lookups and listings over the parsed mod and vanilla
(GET /entity-types, /keys, /raw, /loc-keys, /localize, /unlocalize, /search,
/filter, /diff, and the typed endpoints from /laws to /on-actions), with the
helpers only they use. Moved out of mod_state_server.py unchanged (#1537).

A route module holds code only (server/__init__.py says why): the state these
routes read stays in mod_state_server and is read as `srv.<name>` through
`server_state()` at call time. mod_state_server re-exports every name below.
"""
import difflib
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Optional

import state_history
import strategic_regions
import vanilla_parsed
from mod_state import iter_script_files
from paradox_file_parser import ParadoxFileParser

from server import server_state


# ---------------------------------------------------------------------------
# Loc-key families: entity type -> [(role, suffix), ...]. Used by /loc-keys
# to enumerate the stable family of loc keys an entity exposes. Extend as
# new entity types acquire well-known suffix patterns.
# ---------------------------------------------------------------------------
LOC_KEY_FAMILIES: dict[str, list[tuple[str, str]]] = {
    "Treaty Articles":   [("name", ""), ("desc", "_desc"), ("article_short_desc", "_article_short_desc"), ("effects_desc", "_effects_desc")],
    "Decisions":         [("name", ""), ("desc", "_desc")],
    # 1.15: `_concluded` is the static name a concluded entry shows when its
    # name reads scoped data (journal_entries.md); the four conclusion texts
    # follow the converter's naming (vanilla's own custom keys). The keys an
    # entry's outcomes actually name are added from its body (_loc_keys_for).
    "Journal Entries":   [("name", ""), ("desc", "_desc"), ("reason", "_reason"), ("goal", "_goal"),
                          ("concluded", "_concluded"),
                          ("complete_conclusion", "_complete_conclusion_desc"),
                          ("fail_conclusion", "_fail_conclusion_desc"),
                          ("timeout_conclusion", "_timeout_conclusion_desc"),
                          ("invalid_conclusion", "_invalid_conclusion_desc")],
    "Decrees":           [("name", ""), ("desc", "_desc")],
    "Diplomatic Actions":[("name", ""), ("desc", "_desc")],
    "Diplomatic Plays":  [("name", ""), ("desc", "_desc"), ("goal", "_goal")],
    "Laws":              [("name", ""), ("desc", "_desc")],
    "Country Formation": [("name", ""), ("desc", "_desc")],
    "Modifiers":         [("name", ""), ("desc", "_desc")],
    "Institutions":      [("name", ""), ("desc", "_desc")],
    # 1.15: a glossary entry needs both (common/glossary/glossary.md); an
    # exile pool's name is its tab in the Invite Exile screen.
    "Glossary":          [("name", ""), ("desc", "_desc")],
    "Regional Exile Pools": [("name", "")],
}


def _loc_keys_for(etype: str, eid: str, loc_dict: dict[str, str], body=None) -> dict:
    """Pure helper for the /loc-keys endpoint — no ms dependency, so unit tests
    can pass a hand-built loc dict. With the entity's parsed `body`, a 1.15
    journal entry also lists the keys its outcomes name, as
    `outcome<N>_header`, `outcome<N>_effect_header` and
    `outcome<N>_conclusion_desc`."""
    family = LOC_KEY_FAMILIES.get(etype)
    if family is None:
        return {
            "error": f"No loc-key family seeded for entity type {etype!r}",
            "known_types": sorted(LOC_KEY_FAMILIES.keys()),
            "hint": "Add an entry to LOC_KEY_FAMILIES in mod_state_server.py to extend.",
        }
    keys: dict[str, dict] = {}
    roles = [(role, eid + suffix) for role, suffix in family]
    if etype == "Journal Entries" and body is not None:
        from loc_coverage_audit import je_outcomes
        for i, outcome in enumerate(je_outcomes(body), 1):
            for fld in ("header", "effect_header", "conclusion_desc"):
                if outcome[fld]:
                    roles.append((f"outcome{i}_{fld}", outcome[fld]))
    for role, full_key in roles:
        found = full_key in loc_dict
        keys[role] = {
            "key": full_key,
            "value": loc_dict.get(full_key, ""),
            "found": found,
        }
    return {"type": etype, "id": eid, "keys": keys}


_PARAM_RE = re.compile(r"\$([A-Za-z0-9_]+)\$")


def _extract_parameters(raw) -> list:
    """Detect $X$ placeholders in a helper body via its serialized form."""
    srv = server_state()
    blob = json.dumps(srv.serialize(raw))
    return sorted(set(_PARAM_RE.findall(blob)))


# ---------------------------------------------------------------------------
# Mod-vs-vanilla entity diff (issue #133)
# ---------------------------------------------------------------------------
# ModState holds both parses — base_parsers (vanilla) and mod_parsers (merged,
# with INJECT:/REPLACE: applied). This is an in-memory, merge-directive-aware
# field-level comparison; _compare_dicts in the parser drops the vanilla side
# for scalar changes, so we walk both dicts here to keep both values.
def _unwrap_val(v):
    return v[1] if isinstance(v, tuple) and len(v) >= 2 else v


def _diff_entity_fields(vanilla, mod, prefix=""):
    """Recursive field-level diff of two entity-data dicts, returning
    (added, removed, changed) with flattened dotted keys
    (e.g. `modifier.state_homeland_creation_threshold_add`). `changed[key]`
    is `{"vanilla": v, "mod": m}` with both sides serialized."""
    srv = server_state()
    added: dict = {}
    removed: dict = {}
    changed: dict = {}
    vkeys = set(vanilla) if isinstance(vanilla, dict) else set()
    mkeys = set(mod) if isinstance(mod, dict) else set()
    for k in mkeys - vkeys:
        added[prefix + k] = srv.serialize(_unwrap_val(mod[k]))
    for k in vkeys - mkeys:
        removed[prefix + k] = srv.serialize(_unwrap_val(vanilla[k]))
    for k in vkeys & mkeys:
        vv = _unwrap_val(vanilla[k])
        mv = _unwrap_val(mod[k])
        if isinstance(vv, dict) and isinstance(mv, dict):
            a, r, c = _diff_entity_fields(vv, mv, prefix + k + ".")
            added.update(a)
            removed.update(r)
            changed.update(c)
        else:
            sv = srv.serialize(vv)
            smv = srv.serialize(mv)
            if sv != smv:
                changed[prefix + k] = {"vanilla": sv, "mod": smv}
    return added, removed, changed


def _paradox_text(name, entity, indent=0):
    """Render a parsed entity back to Paradox-ish script text (for ?format=text
    unified diffs). Not a faithful writer — readable, stable field ordering."""
    pad = "\t" * indent
    val = _unwrap_val(entity)
    if isinstance(val, dict):
        lines = [f"{pad}{name} = {{"]
        for k, v in val.items():
            lines.append(_paradox_text(k, v, indent + 1))
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if isinstance(val, list):
        if all(not isinstance(x, (dict, tuple, list)) for x in val):
            inner = " ".join(str(x) for x in val)
            return f"{pad}{name} = {{ {inner} }}"
        return "\n".join(_paradox_text(name, x, indent) for x in val)
    return f"{pad}{name} = {val}"


def _unwrap_modifiers(block_dict):
    """Flatten a modifier-bag dict {key: ('=', value)} to {key: value}.

    Scalars are returned as-is (matching _format_law_detail's modifier handling);
    nested dicts/lists (e.g. scaling wrappers) are serialized for JSON safety.
    """
    srv = server_state()
    out = {}
    if not isinstance(block_dict, dict):
        return out
    for k, v in block_dict.items():
        val = v[1] if isinstance(v, tuple) and len(v) >= 2 else v
        out[k] = srv.serialize(val) if isinstance(val, (dict, list, tuple)) else val
    return out


def _company_catalog():
    """Merged company rows; raw files supply declaration locations only.

    A mod INJECT (even a no-op) counts as mod-touched. Snapshot provenance
    names the JSON backing file rather than guessing a vanilla script path.
    """
    srv = server_state()
    companies = srv.ms.get_data("Company Types") if srv.ms is not None else None
    if companies is None:
        raise srv.DataNotLoaded("Company Types")
    if srv._company_catalog_cache is not None and srv._company_catalog_cache[0] is srv.ms:
        return srv._company_catalog_cache[1]

    vanilla_parser = srv.ms.base_parsers.get("Company Types")
    vanilla = vanilla_parser.data if vanilla_parser is not None else {}
    sources = defaultdict(list)
    for origin, directories, root in (
        ("mod", srv.mod_paths, srv.mod_path),
        ("vanilla", srv.base_game_paths, srv.base_game_path),
    ):
        if origin == "vanilla" and srv._vanilla_source.get("kind") == "vanilla_parsed":
            for cid in vanilla:
                sources[cid].append({
                    "source": "vanilla",
                    "file": "vanilla_parsed/common/company_types.json",
                })
            continue
        directory = directories.get("Company Types")
        if not directory or not os.path.isdir(directory):
            continue
        for path in iter_script_files(directory):
            parser = ParadoxFileParser()
            try:
                parser.parse_file(path, apply_directives=False)
            except Exception as exc:
                srv.logger.warning("Company provenance scan skipped %s: %s", path, exc)
                continue
            location = {"source": origin, "file": os.path.relpath(path, root).replace(os.sep, "/")}
            for key in parser.data:
                cid = key.split(":", 1)[-1]
                if location not in sources[cid]:
                    sources[cid].append(location)

    def attainable_techs(value, is_tech=False):
        if isinstance(value, tuple) and len(value) >= 2:
            return attainable_techs(value[1], is_tech)
        if isinstance(value, str):
            return {value} if is_tech else set()
        found = set()
        if isinstance(value, dict):
            for key, child in value.items():
                found.update(attainable_techs(child, key == "has_technology_researched"))
        elif isinstance(value, list):
            for child in value:
                found.update(attainable_techs(child, is_tech))
        return found

    rows = []
    for cid, raw in sorted(companies.items()):
        cd = srv.get_entity_data(raw)
        modifiers = _unwrap_modifiers(srv.get_entity_data(srv.get_field(cd, "prosperity_modifier", {})))
        flagship = {k: v for k, v in modifiers.items()
                    if k.startswith("state_building_") and k.endswith("_max_level_add")}
        prosperity = {k: v for k, v in modifiers.items() if k not in flagship}
        locations = sources[cid]
        touched = any(s["source"] == "mod" for s in locations)
        # Keep source filtering useful for in-memory states without raw files.
        source = "mod" if touched or cid not in vanilla or raw != vanilla[cid] else "vanilla"
        roster = srv.get_field(cd, "building_types", [])
        extensions = srv.get_field(cd, "extension_building_types", [])
        rows.append({
            "type": "Company Types", "id": cid, "name": srv.ms.localize(cid),
            "flavored": srv.get_field(cd, "flavored_company", "no") == "yes",
            "source": source, "source_files": locations,
            "building_types": roster, "extension_building_types": extensions,
            "roster_size": len(roster), "extension_count": len(extensions),
            "prosperity_modifier": prosperity, "flagship": flagship,
            "effect_count": len(prosperity),
            "possible_prestige_goods": srv.get_field(cd, "possible_prestige_goods", []),
            "attainable_techs": sorted(attainable_techs(srv.get_field(cd, "attainable", {}))),
        })
    srv._company_catalog_cache = (srv.ms, rows)
    return rows


def _party_catalog():
    """party_catalog rows for the loaded state, cached on `ms` like
    _company_catalog (a reload clears it). The vanilla side's files are the
    game's, or the snapshot's JSON when vanilla came from vanilla_parsed/."""
    srv = server_state()
    import party_catalog

    parties = srv.ms.get_data("Parties") if srv.ms is not None else None
    if not parties:
        raise srv.DataNotLoaded("Parties")
    if srv._party_catalog_cache is not None and srv._party_catalog_cache[0] is srv.ms:
        return srv._party_catalog_cache[1]
    vanilla_parser = srv.ms.base_parsers.get("Parties")
    vanilla = (vanilla_parser.data if vanilla_parser is not None else None) or {}
    if srv._vanilla_source.get("kind") == "vanilla_parsed":
        sites = [party_catalog.snapshot_site(vanilla)] if vanilla else []
    else:
        sites = party_catalog.directory_sites(
            srv.base_game_paths.get("Parties"), srv.base_game_path, "vanilla")
    sites += party_catalog.directory_sites(srv.mod_paths.get("Parties"), srv.mod_path, "mod")
    rows = party_catalog.party_rows(parties, vanilla, sites)
    srv._party_catalog_cache = (srv.ms, rows)
    return rows


def _state_history_tables():
    """(states, regions, source) for /state-history (#901): the start map
    with the mod's own history files layered on (state_history.merge), the
    hub table from `map_data/state_regions`, and where vanilla's history came
    from. Vanilla follows the load's vanilla source: the snapshot's
    `history/states.json`, or the game's files. Cached on `ms`."""
    srv = server_state()
    if srv.ms is None:
        raise srv.DataNotLoaded("State history")
    if srv._state_history_cache is not None and srv._state_history_cache[0] is srv.ms:
        return srv._state_history_cache[1:]
    rel = state_history.REL_DIR.split("/")
    regions_rel = state_history.STATE_REGIONS_REL_DIR.split("/")
    tree = srv._vanilla_tree_present()
    if srv._vanilla_source.get("kind") == "vanilla_parsed" or not tree:
        vanilla = vanilla_parsed.load_state_history(srv.VANILLA_PARSED_DIR)
        source = "vanilla_parsed"
    else:
        vanilla = state_history.parse_dir(os.path.join(srv.base_game_path, "game", *rel))
        source = "game_files"
    if not vanilla:
        raise srv.DataNotLoaded("State history")
    states = state_history.merge(vanilla, state_history.parse_dir(os.path.join(srv.mod_path, *rel)))
    regions = state_history.state_regions(
        os.path.join(srv.base_game_path, "game", *regions_rel) if tree else None,
        os.path.join(srv.mod_path, *regions_rel),
    )
    srv._state_history_cache = (srv.ms, states, regions, source)
    return states, regions, source


# Entity-type name resolution. `get_data()` is exact-key, but /raw and /keys take
# user-typed type names — resolve them case-insensitively and singular/plural-
# insensitively so `/raw/law group`, `/raw/Technology`, `/keys/PMs` all work.


def _singularize_word(word: str) -> str:
    """Best-effort singular of a single word: `Groups`->`Group`, `Technologies`
    ->`Technology`. Only the crude rules the entity-type keyspace needs."""
    w = word.lower()
    if w.endswith("ies") and len(w) > 3:
        return w[:-3] + "y"
    if w.endswith("s") and len(w) > 1:
        return w[:-1]
    return w


def _normalize_entity_type(name: str) -> str:
    """Lowercase a (possibly multi-word) type name and singularize its LAST word,
    so `Law Groups` and `law group` both normalize to `law group`."""
    words = name.split()
    if words:
        words[-1] = _singularize_word(words[-1])
    return " ".join(w.lower() for w in words)


def _resolve_entity_type(etype: str, known) -> Optional[str]:
    """Resolve a user-supplied entity-type name to a canonical member of `known`.
    Exact match wins, then case-insensitive, then singular/plural-insensitive.
    Returns None on no match."""
    known = list(known)
    if etype in known:
        return etype
    lower_map = {k.lower(): k for k in known}
    if etype.lower() in lower_map:
        return lower_map[etype.lower()]
    norm_map = {_normalize_entity_type(k): k for k in known}
    return norm_map.get(_normalize_entity_type(etype))


class EntityRoutes:
    """The entity lookups and listings. A mixin of ModStateHandler."""

    def _entity_types(self, params):
        """GET /entity-types            — {"entity_types": [...]} (structured).
        GET /entity-types?bare=true     — the old bare list, for compatibility."""
        srv = server_state()
        names = list(srv.ms.mod_parsers.keys())
        bare = (params.get("bare") or ["false"])[0].lower() == "true"
        return names if bare else {"entity_types": names}

    def _resolve_entity_type_or_404(self, etype):
        """Resolve `etype` (case-/plural-insensitive) to a canonical mod_parsers
        key, or raise _EndpointError(404) with `did_you_mean` suggestions."""
        srv = server_state()
        known = list(srv.ms.mod_parsers.keys())
        resolved = _resolve_entity_type(etype, known)
        if resolved is None:
            raise srv._EndpointError({
                "error": f"Unknown entity type: {etype!r}",
                "did_you_mean": difflib.get_close_matches(etype, known, n=5, cutoff=0.5),
                "hint": "GET /entity-types for the full list. "
                        "Matching is case- and singular/plural-insensitive.",
            }, 404)
        return resolved

    def _keys(self, parts, params):
        """GET /keys/<EntityType>  - list entity IDs with localized names."""
        srv = server_state()
        if not parts:
            return list(srv.ms.mod_parsers.keys())
        etype = self._resolve_entity_type_or_404(parts[0])
        data = srv.ms.get_data(etype)
        if data is None:
            raise srv.NotFound(etype)
        return [
            {"type": etype, "id": eid, "name": srv.ms.localize(eid)}
            for eid in data.keys()
        ]

    def _raw(self, parts):
        """GET /raw/<EntityType>[/<id>]  - raw parsed data."""
        srv = server_state()
        if not parts:
            return list(srv.ms.mod_parsers.keys())
        etype = self._resolve_entity_type_or_404(parts[0])
        data = srv.ms.get_data(etype)
        if data is None:
            raise srv.NotFound(etype)
        if len(parts) > 1:
            eid = parts[1]
            if eid not in data:
                raise srv.NotFound(eid)
            return srv.serialize(data[eid])
        return srv.serialize(data)

    def _loc_keys(self, parts):
        """GET /loc-keys/<EntityType>/<id>  - resolve the family of loc keys
        an entity exposes (name, desc, article_short_desc, ...) against the
        loaded localization map. Stable suffix patterns per type are seeded in
        LOC_KEY_FAMILIES.

        Returns {"type", "id", "keys": {role: {"key", "value", "found"}}}.
        A key with `found=true, value=""` is intentionally blank in vanilla
        (real and common — e.g. money_transfer_desc).
        """
        srv = server_state()
        if len(parts) < 2:
            raise srv.BadRequest(
                "Usage: /loc-keys/<EntityType>/<id>",
                known_types=sorted(LOC_KEY_FAMILIES.keys()),
            )
        parser = srv.ms.mod_parsers.get(parts[0])
        body = parser.data.get(parts[1]) if parser is not None else None
        result = _loc_keys_for(parts[0], parts[1], srv.ms.localization, body)
        # The helper reports an unseeded entity type in-band (its own callers
        # rely on that shape); surface it as a 404 over HTTP. (#254)
        if isinstance(result, dict) and "error" in result:
            raise srv._EndpointError(result, 404)
        return result

    def _localize(self, parts):
        """GET /localize/<key>  - localize a game key to display text."""
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide a key, e.g. /localize/law_monarchy")
        key = parts[0]
        result = {"key": key, "name": srv.ms.localize(key)}
        desc = srv.ms.get_description(key)
        if desc is not None:
            result["description"] = desc
        return result

    def _unlocalize(self, parts, params=None):
        """GET /unlocalize/<text>  - reverse-localize display text to keys.
        GET /unlocalize?q=<text>   - same, for text with slashes/spaces. (#254)"""
        srv = server_state()
        text = ((params or {}).get("q") or [""])[0]
        if not text and parts:
            text = parts[0]
        if not text:
            raise srv.BadRequest(
                "Provide display text, e.g. /unlocalize/Monarchy or /unlocalize?q=Monarchy"
            )
        keys = srv.ms.unlocalize(text)
        return {"text": text, "keys": keys}

    def _search(self, params):
        """GET /search?q=<query>[&type=<EntityType>][&limit=<n>]"""
        srv = server_state()
        query = params.get("q", [""])[0].lower()
        if not query:
            raise srv.BadRequest("Provide ?q=search_term")
        etype_filter = params.get("type", [None])[0]
        limit = int(params.get("limit", ["50"])[0])

        entities = []
        etypes = [etype_filter] if etype_filter else list(srv.ms.mod_parsers.keys())
        for et in etypes:
            data = srv.ms.get_data(et)
            if data is None:
                continue
            for eid in data:
                if query in eid.lower() or query in srv.ms.localize(eid).lower():
                    entities.append({"type": et, "id": eid, "name": srv.ms.localize(eid)})
                    if len(entities) >= limit:
                        break

        loc_results = srv.ms.search_localization(query, limit=limit)
        return {"entities": entities, "localization": loc_results}

    # ---- structured: laws -------------------------------------------------
    def _laws(self, parts):
        """GET /laws[/<law_id>]"""
        srv = server_state()
        laws = srv.ms.get_data("Laws")
        if not laws:
            raise srv.DataNotLoaded("Laws")

        if parts:
            law_id = parts[0]
            if law_id not in laws:
                raise srv.NotFound(law_id)
            return self._format_law_detail(law_id, laws[law_id])

        groups: dict = {}
        for law_id, raw in laws.items():
            ld = srv.get_entity_data(raw)
            group_id = srv.get_field(ld, "group", "unknown")
            group_name = srv.ms.localize(group_id)
            if group_name not in groups:
                groups[group_name] = {"group_id": group_id, "laws": []}
            groups[group_name]["laws"].append(self._format_law_summary(law_id, ld))
        return groups

    def _format_law_summary(self, law_id, ld):
        srv = server_state()
        info: dict = {"type": "Laws", "id": law_id, "name": srv.ms.localize(law_id)}
        tech = srv.get_field(ld, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": srv.ms.localize(tech[0])}
        parent = srv.get_field(ld, "parent")
        if parent:
            info["parent"] = {"type": "Laws", "id": parent, "name": srv.ms.localize(parent)}
        return info

    def _format_law_detail(self, law_id, raw):
        srv = server_state()
        ld = srv.get_entity_data(raw)
        group_id = srv.get_field(ld, "group", "")
        info: dict = {
            "type": "Laws",
            "id": law_id,
            "name": srv.ms.localize(law_id),
            "group_id": group_id,
            "group_name": srv.ms.localize(group_id),
        }
        desc = srv.ms.get_description(law_id)
        if desc:
            info["description"] = desc
        tech = srv.get_field(ld, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": srv.ms.localize(tech[0])}
        parent = srv.get_field(ld, "parent")
        if parent:
            info["parent"] = {"type": "Laws", "id": parent, "name": srv.ms.localize(parent)}
        modifiers = srv.get_field(ld, "modifier")
        if modifiers and isinstance(modifiers, dict):
            info["modifiers"] = {}
            for k, v in modifiers.items():
                info["modifiers"][k] = v[1] if isinstance(v, tuple) else v
        info["raw"] = srv.serialize(raw)
        return info

    # ---- structured: power bloc principles --------------------------------
    def _principles(self, parts):
        """GET /principles[/<principle_id>]"""
        srv = server_state()
        principles = srv.ms.get_data("Principles")
        if not principles:
            raise srv.DataNotLoaded("Principles")
        if parts:
            pid = parts[0]
            if pid not in principles:
                raise srv.NotFound(pid)
            return self._format_principle_detail(pid, principles[pid])
        return [
            {"type": "Principles", "id": pid, "name": srv.ms.localize(pid)}
            for pid in principles
        ]

    def _principle_group_index(self):
        """principle_id -> {group_id, levels:[...]} from Principle Groups' levels lists."""
        srv = server_state()
        out: dict = {}
        groups = srv.ms.get_data("Principle Groups") or {}
        for gid, raw in groups.items():
            levels = srv.get_field(srv.get_entity_data(raw), "levels")
            if isinstance(levels, list):
                for lvl in levels:
                    out[lvl] = {"group_id": gid, "levels": list(levels)}
        return out

    def _format_principle_detail(self, pid, raw):
        srv = server_state()
        pd = srv.get_entity_data(raw)
        info: dict = {"type": "Principles", "id": pid, "name": srv.ms.localize(pid)}
        desc = srv.ms.get_description(pid)
        if desc:
            info["description"] = desc
        grp = self._principle_group_index().get(pid)
        if grp:
            info["group_id"] = grp["group_id"]
            info["group_name"] = srv.ms.localize(grp["group_id"])
            info["group_levels"] = grp["levels"]
        # Emit each present modifier-bag block (member_modifier, institution_modifier,
        # power_bloc_modifier, leader_modifier, …) in file order.
        blocks = []
        if isinstance(pd, dict):
            for k, v in pd.items():
                if not srv._is_modifier_bag(k):
                    continue
                val = v[1] if isinstance(v, tuple) and len(v) >= 2 else v
                if isinstance(val, dict):
                    blocks.append({"block": k, "modifiers": _unwrap_modifiers(val)})
        if blocks:
            info["modifier_blocks"] = blocks
        info["raw"] = srv.serialize(raw)
        return info

    # ---- structured: power bloc amendments --------------------------------
    def _amendments(self, parts):
        """GET /amendments[/<amendment_id>]"""
        srv = server_state()
        amendments = srv.ms.get_data("Amendments")
        if not amendments:
            raise srv.DataNotLoaded("Amendments")
        if parts:
            aid = parts[0]
            if aid not in amendments:
                raise srv.NotFound(aid)
            return self._format_amendment_detail(aid, amendments[aid])
        return [
            {"type": "Amendments", "id": aid, "name": srv.ms.localize(aid)}
            for aid in amendments
        ]

    def _format_amendment_detail(self, aid, raw):
        srv = server_state()
        ad = srv.get_entity_data(raw)
        info: dict = {"type": "Amendments", "id": aid, "name": srv.ms.localize(aid)}
        desc = srv.ms.get_description(aid)
        if desc:
            info["description"] = desc
        parent = srv.get_field(ad, "parent")
        if parent:
            info["parent"] = {"type": "Laws", "id": parent, "name": srv.ms.localize(parent)}
        allowed = srv.get_field(ad, "allowed_laws")
        if isinstance(allowed, list):
            info["allowed_laws"] = [
                {"type": "Laws", "id": lw, "name": srv.ms.localize(lw)} for lw in allowed
            ]
        mods = srv.get_field(ad, "modifier")
        if isinstance(mods, dict):
            info["modifiers"] = _unwrap_modifiers(mods)
        info["raw"] = srv.serialize(raw)
        return info

    # ---- structured: technologies -----------------------------------------
    def _technologies(self, parts, params):
        """GET /technologies[/<tech_id>][?era=<n>]"""
        srv = server_state()
        techs = srv.ms.get_data("Technologies")
        if not techs:
            raise srv.DataNotLoaded("Technologies")

        if parts:
            tid = parts[0]
            if tid not in techs:
                raise srv.NotFound(tid)
            return self._format_tech_detail(tid, techs[tid])

        era_filter = params.get("era", [None])[0]
        if era_filter:
            # The listing's keys are `era_<n>`, so take that spelling too.
            number = era_filter[len("era_"):] if era_filter.startswith("era_") else era_filter
            if not (number.isascii() and number.isdigit()):
                raise srv.BadRequest(f"?era= takes an era number (3 or era_3), not {era_filter!r}")
            era_filter = int(number)
        else:
            era_filter = None

        by_era: dict = defaultdict(list)
        for tid, raw in techs.items():
            td = srv.get_entity_data(raw)
            era_str = srv.get_field(td, "era", "era_0")
            era_num = int(era_str.split("_")[-1])
            if era_filter is not None and era_num != era_filter:
                continue
            by_era[era_num].append(self._format_tech_summary(tid, td))

        return {
            f"era_{era}": {"count": len(tlist), "technologies": tlist}
            for era, tlist in sorted(by_era.items())
        }

    def _format_tech_summary(self, tid, td):
        srv = server_state()
        info: dict = {"type": "Technologies", "id": tid, "name": srv.ms.localize(tid)}
        desc = srv.ms.get_description(tid)
        if desc:
            info["description"] = desc
        era_str = srv.get_field(td, "era", "era_0")
        info["era"] = int(era_str.split("_")[-1])
        tech = srv.get_field(td, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technologies"] = [
                {"type": "Technologies", "id": t, "name": srv.ms.localize(t)} for t in tech
            ]
        return info

    def _format_tech_detail(self, tid, raw):
        srv = server_state()
        info = self._format_tech_summary(tid, srv.get_entity_data(raw))
        info["raw"] = srv.serialize(raw)
        return info

    # ---- structured: buildings --------------------------------------------
    def _buildings(self, parts, params=None):
        """GET /buildings[/<building_id>][?detail=true]

        /buildings              - summary list (id, name, pm_group_count)
        /buildings?detail=true  - full detail for ALL buildings (includes PM groups & PMs)
        /buildings/<id>         - full detail for one building
        /buildings/pm-map       - compact building→PM mapping for code generators
        """
        srv = server_state()
        buildings = srv.ms.get_data("Buildings")
        if not buildings:
            raise srv.DataNotLoaded("Buildings")

        if parts:
            if parts[0] == "pm-map":
                return self._buildings_pm_map(buildings)
            bid = parts[0]
            if bid not in buildings:
                raise srv.NotFound(bid)
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
        srv = server_state()
        pmg_data = srv.ms.get_data("PM Groups") or {}
        result = {}
        for bid, raw in buildings.items():
            bd = srv.get_entity_data(raw)
            pmg_ids = srv.get_field(bd, "production_method_groups")
            if not pmg_ids or not isinstance(pmg_ids, list):
                result[bid] = []
                continue
            groups = []
            for pmg_id in pmg_ids:
                if pmg_id not in pmg_data:
                    groups.append([])
                    continue
                pmg_inner = srv.get_entity_data(pmg_data[pmg_id])
                pm_ids = srv.get_field(pmg_inner, "production_methods")
                groups.append(pm_ids if pm_ids and isinstance(pm_ids, list) else [])
            result[bid] = groups
        return result

    def _format_building_summary(self, bid, raw):
        srv = server_state()
        bd = srv.get_entity_data(raw)
        info: dict = {"type": "Buildings", "id": bid, "name": srv.ms.localize(bid)}
        tech = srv.get_field(bd, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": srv.ms.localize(tech[0])}
        pmg_ids = srv.get_field(bd, "production_method_groups")
        if pmg_ids and isinstance(pmg_ids, list):
            info["pm_group_count"] = len(pmg_ids)
        return info

    def _format_building_detail(self, bid, raw):
        srv = server_state()
        bd = srv.get_entity_data(raw)
        info: dict = {"type": "Buildings", "id": bid, "name": srv.ms.localize(bid)}
        tech = srv.get_field(bd, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": srv.ms.localize(tech[0])}

        pmg_data = srv.ms.get_data("PM Groups")
        pm_data = srv.ms.get_data("PMs")
        pmg_ids = srv.get_field(bd, "production_method_groups")
        if pmg_ids and isinstance(pmg_ids, list) and pmg_data and pm_data:
            info["pm_groups"] = []
            for pmg_id in pmg_ids:
                pmg_entry: dict = {
                    "type": "PM Groups", "id": pmg_id, "name": srv.ms.localize(pmg_id),
                }
                if pmg_id in pmg_data:
                    pmg_inner = srv.get_entity_data(pmg_data[pmg_id])
                    pm_ids = srv.get_field(pmg_inner, "production_methods")
                    if pm_ids and isinstance(pm_ids, list):
                        pmg_entry["production_methods"] = [
                            {"type": "PMs", "id": pid, "name": srv.ms.localize(pid)}
                            for pid in pm_ids
                        ]
                info["pm_groups"].append(pmg_entry)

        info["raw"] = srv.serialize(raw)
        return info

    # ---- structured: companies --------------------------------------------
    def _companies(self, parts, params):
        """GET /companies?flavored=yes|no&source=mod|vanilla|all."""
        srv = server_state()
        if parts:
            raise srv.NotFound("/companies/" + "/".join(parts))
        flavored = (params.get("flavored") or [None])[0]
        source = (params.get("source") or ["all"])[0]
        if flavored not in (None, "yes", "no"):
            raise srv.BadRequest("flavored must be yes or no")
        if source not in ("mod", "vanilla", "all"):
            raise srv.BadRequest("source must be mod, vanilla or all")
        companies = [c for c in _company_catalog()
                     if (flavored is None or c["flavored"] == (flavored == "yes"))
                     and (source == "all" or c["source"] == source)]
        stats = {}
        for label in ("yes", "no"):
            bucket = [c for c in companies if c["flavored"] == (label == "yes")]
            stats[label] = {
                "count": len(bucket),
                "roster_size_median": median(c["roster_size"] for c in bucket) if bucket else None,
                "roster_size_max": max((c["roster_size"] for c in bucket), default=None),
                "effect_count_median": median(c["effect_count"] for c in bucket) if bucket else None,
            }
        # Annotation mutates rows, so never expose the cached dictionaries.
        return {"count": len(companies), "companies": srv.serialize(companies), "stats": stats}

    def _building_companies(self, parts):
        """GET /building-companies/<building_id> over the merged company data."""
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide a building ID, e.g. /building-companies/building_synthetics_plant")
        if len(parts) != 1:
            raise srv.NotFound("/building-companies/" + "/".join(parts))
        buildings = srv.ms.get_data("Buildings") if srv.ms is not None else None
        if buildings is None:
            raise srv.DataNotLoaded("Buildings")
        bid = parts[0]
        if bid not in buildings:
            raise srv.NotFound(bid)
        companies = _company_catalog()
        return {
            "building": {"type": "Buildings", "id": bid, "name": srv.ms.localize(bid)},
            "roster": [c["id"] for c in companies if bid in c["building_types"]],
            "extension": [c["id"] for c in companies if bid in c["extension_building_types"]],
        }

    # ---- structured: goods ------------------------------------------------
    def _goods(self):
        """GET /goods"""
        srv = server_state()
        goods = srv.ms.get_data("Goods")
        if not goods:
            raise srv.DataNotLoaded("Goods")
        return [{"type": "Goods", "id": gid, "name": srv.ms.localize(gid)} for gid in goods]

    # ---- structured: combat units -----------------------------------------
    def _combat_units(self):
        """GET /combat-units"""
        srv = server_state()
        groups = srv.ms.get_data("Combat Unit Groups")
        types = srv.ms.get_data("Combat Unit Types")
        if not groups or not types:
            raise srv.DataNotLoaded("Combat unit")

        by_group: dict = defaultdict(list)
        for tid, raw in types.items():
            td = srv.get_entity_data(raw)
            gid = srv.get_field(td, "group", "unknown")
            unit_info: dict = {
                "type": "Combat Unit Types", "id": tid, "name": srv.ms.localize(tid),
            }
            tech = srv.get_field(td, "unlocking_technologies")
            if tech and isinstance(tech, list) and tech:
                unit_info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": srv.ms.localize(tech[0])}
            by_group[gid].append(unit_info)

        return {
            gid: {"name": srv.ms.localize(gid), "units": units}
            for gid, units in by_group.items()
        }

    # ---- structured: ideologies -------------------------------------------
    def _ideologies(self, parts):
        """GET /ideologies[/<ideology_id>]"""
        srv = server_state()
        ideologies = srv.ms.get_data("Ideologies")
        if not ideologies:
            raise srv.DataNotLoaded("Ideologies")
        if parts:
            iid = parts[0]
            if iid not in ideologies:
                raise srv.NotFound(iid)
            return {
                "type": "Ideologies", "id": iid,
                "name": srv.ms.localize(iid), "raw": srv.serialize(ideologies[iid]),
            }
        return [
            {"type": "Ideologies", "id": iid, "name": srv.ms.localize(iid)}
            for iid in ideologies
        ]

    # ---- structured: political movements (#838) ---------------------------
    def _movements(self, parts):
        """GET /movements[/<movement_id>]"""
        srv = server_state()
        import movement_stances

        movements = srv.ms.get_data("Political Movements")
        if not movements:
            raise srv.DataNotLoaded("Political Movements")
        ideologies = srv.ms.get_data("Ideologies") or {}
        if parts:
            mid = parts[0]
            if mid not in movements:
                raise srv.NotFound(mid)
            row = movement_stances.movement_summary(mid, movements[mid], ideologies)
            return {"type": "Political Movements", "id": mid, "name": srv.ms.localize(mid),
                    **row, "raw": srv.serialize(movements[mid])}
        return [
            {"type": "Political Movements", "id": row["name"], "name": srv.ms.localize(row["name"]),
             **{k: v for k, v in row.items() if k != "name"}}
            for row in movement_stances.movement_catalog(movements, ideologies)
        ]

    def _parties(self, parts, params):
        """GET /parties[?desc=<desc>], GET /parties/<key> (#1164): who defines
        each party and the descs of its merged join_weight, in source order
        (party_catalog.py)."""
        srv = server_state()
        rows = _party_catalog()
        if parts:
            row = next((r for r in rows if r["key"] == parts[0]), None)
            if row is None:
                raise srv.NotFound(parts[0])
            return json.loads(json.dumps(row))  # a copy: the cached row stays as built
        desc = (params.get("desc") or [None])[0]
        return [
            {k: v for k, v in row.items() if k != "terms"}
            for row in rows
            if desc is None or desc in row["join_weight_terms"]
        ]

    def _strategic_region_data(self):
        srv = server_state()
        data = srv.ms.get_data("Strategic Regions") if srv.ms is not None else None
        if not data:
            raise srv.DataNotLoaded("Strategic Regions")
        return data

    def _strategic_regions(self, parts):
        """GET /strategic-regions, GET /strategic-regions/<name> (#917): the
        state regions a strategic region holds, mod REPLACEs applied."""
        srv = server_state()
        table = strategic_regions.region_states(self._strategic_region_data())
        if not parts:
            return [
                {"name": name, "localized": srv.ms.localize(name), "states": len(states)}
                for name, states in table.items()
            ]
        name = parts[0]
        if name not in table:
            raise srv.NotFound(name, did_you_mean=difflib.get_close_matches(name, list(table), n=5))
        return {"name": name, "localized": srv.ms.localize(name), "states": list(table[name])}

    def _state_region(self, parts):
        """GET /state-region/<STATE_X> (#917): its strategic region."""
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide a state region, e.g. /state-region/STATE_SVEALAND")
        state = parts[0]
        of = strategic_regions.region_of(self._strategic_region_data())
        if state not in of:
            raise srv.NotFound(state, did_you_mean=difflib.get_close_matches(state, list(of), n=5))
        region = of[state]
        return {
            "state": state, "localized": srv.ms.localize(state),
            "strategic_region": region, "strategic_region_localized": srv.ms.localize(region),
        }

    def _state_history(self, parts, params):
        """GET /state-history/<STATE_X>[?provinces=true], GET
        /state-history?country=<TAG>, GET /state-history (#901): who owns each
        state on the start date, part by part for a split state, with the hub
        provinces (city, port, farm, mine, wood) each part holds."""
        srv = server_state()
        states, regions, source = _state_history_tables()
        region_of = strategic_regions.region_of(srv.ms.get_data("Strategic Regions"))

        def name(row, key="country"):
            row[f"{key}_name"] = srv.ms.localize(row[key]) if row.get(key) else None
            return row

        if parts:
            state = parts[0]
            if state not in states:
                raise srv.NotFound(state, did_you_mean=difflib.get_close_matches(state, list(states), n=5))
            with_provinces = (params.get("provinces") or ["false"])[0].lower() in ("1", "true", "yes")
            out = state_history.describe(state, states[state], regions, provinces=with_provinces)
            out["parts"] = [name(p) for p in out["parts"]]
            out["localized"] = srv.ms.localize(state)
            out["strategic_region"] = region_of.get(state)
            out["vanilla_source"] = source
            return out
        tag = (params.get("country") or [None])[0]
        if tag:
            rows = state_history.owned_by(states, tag, regions)
            if not rows:
                raise srv.NotFound(tag, hint="No state names this tag as an owner on the start date.")
            return {
                "country": tag, "country_name": srv.ms.localize(tag),
                "states": [dict(r, strategic_region=region_of.get(r["state"])) for r in rows],
                "vanilla_source": source,
            }
        return {
            **state_history.summary(states),
            "vanilla_source": source,
            "owners": {state: [p.get("country") for p in rec["parts"]]
                       for state, rec in sorted(states.items())},
        }

    def _prestige_goods(self, params):
        """GET /prestige-goods[?base_good=<good>] (#749): the prestige goods
        that share each base good, who defines them and which companies list
        them, against the engine's cap of three per base good."""
        srv = server_state()
        import prestige_good_roster_audit as roster

        merged = srv.ms.get_data("Prestige Goods") if srv.ms is not None else None
        if not merged:
            raise srv.DataNotLoaded("Prestige Goods")
        vanilla = getattr(srv.ms.base_parsers.get("Prestige Goods"), "data", None) or {}
        rows = roster.prestige_slots(merged, vanilla, srv.ms.get_data("Company Types") or {})
        good = (params.get("base_good") or [None])[0]
        if good is None:
            return rows
        row = next((r for r in rows if r["base_good"] == good), None)
        if row is None:
            if good not in (srv.ms.get_data("Goods") or {}):
                raise srv.NotFound(good)
            row = {"base_good": good, "count": 0, "cap": roster.PRESTIGE_GOODS_PER_BASE_GOOD,
                   "free": roster.PRESTIGE_GOODS_PER_BASE_GOOD, "prestige_goods": []}
        return row

    def _vanilla_script(self):
        """The installed game's script for the /vanilla-refs family (#1563), read once per install state. A
        machine without the game gets a 503 that says so: these folders are not in vanilla_parsed/."""
        srv = server_state()
        import vanilla_refs

        try:
            game = Path(srv.base_game_path) / "game" if srv._vanilla_tree_present() else None
            return vanilla_refs, vanilla_refs.cached(game)
        except (vanilla_refs.NoGame, RuntimeError) as exc:
            raise srv._ServiceNotReady({
                "error": "needs the installed game",
                "detail": str(exc),
                "hint": "Run this on the machine with Victoria 3 installed. For the culture merges' part "
                        "cultures, scripts/generators/culture_merge_primary_reads.json holds a committed scan.",
            })

    def _vanilla_refs(self, parts, params):
        """GET /vanilla-refs/<name>[?depth=N] (#1563): the vanilla entities whose body mentions <name>, N steps
        up, and the journal entries, on-actions and decisions among them."""
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide a name, e.g. /vanilla-refs/je_meiji_restoration?depth=3")
        vanilla_refs, vs = self._vanilla_script()
        try:
            depth = int((params.get("depth") or [vanilla_refs.DEFAULT_DEPTH])[0])
        except ValueError:
            raise srv.BadRequest("?depth= is a whole number")
        return vanilla_refs.refs(vs, parts[0], depth)

    def _culture_reads(self, parts, params):
        """GET /culture-reads/<culture>[?as=primary|pop|homeland|any] (#1563): the vanilla entities that test
        cu:<culture> that way, with the journal entries each belongs to or is reached from."""
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide a culture, e.g. /culture-reads/north_german?as=primary")
        vanilla_refs, vs = self._vanilla_script()
        mode = (params.get("as") or ["primary"])[0]
        try:
            rows = vanilla_refs.culture_reads(vs, parts[0], mode)
        except ValueError as exc:
            raise srv.BadRequest(str(exc))
        return {"culture": parts[0], "as": mode, "count": sum(r["count"] for r in rows), "reads": rows}

    def _formables(self, params):
        """GET /formables[?lists_culture=<culture>] (#1563): country_formation tags, vanilla's and the mod's,
        with the cultures their country definition lists and whether the tag owns a state at the start."""
        srv = server_state()
        vanilla_refs, vs = self._vanilla_script()
        culture = (params.get("lists_culture") or [None])[0]
        return vanilla_refs.formables(vs, culture, Path(srv.mod_path))

    # ---- analytical: filter -----------------------------------------------
    def _filter(self, parts, params):
        """GET /filter/<EntityType>?field=<name>&value=<val>
        Filter entities by field value. Supports:
          field=<name>&value=<val>    substring match on field value
          field=has:<name>            check field existence
        """
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide entity type, e.g. /filter/Technologies?field=era&value=era_5")
        etype = parts[0]
        data = srv.ms.get_data(etype)
        if data is None:
            raise srv.NotFound(etype)

        field = params.get("field", [""])[0]
        value = params.get("value", [""])[0].lower()
        limit = int(params.get("limit", ["200"])[0])

        if not field:
            raise srv.BadRequest("Provide ?field=<name> (and optionally &value=<val>)")

        # has:<field> - existence check
        check_exists = field.startswith("has:")
        if check_exists:
            field = field[4:]

        results = []
        for eid, raw in data.items():
            ed = srv.get_entity_data(raw)
            fv = srv.get_field(ed, field)
            if check_exists:
                if fv is not None:
                    results.append({"type": etype, "id": eid, "name": srv.ms.localize(eid)})
            else:
                if fv is not None:
                    fv_str = str(fv).lower() if not isinstance(fv, list) else " ".join(str(x) for x in fv).lower()
                    if value in fv_str:
                        results.append({
                            "type": etype, "id": eid, "name": srv.ms.localize(eid),
                            field: srv.serialize(fv),
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
        srv = server_state()
        events = srv.ms.get_data("Events")
        if not events:
            raise srv.DataNotLoaded("Events")

        if parts:
            eid = parts[0]
            if eid not in events:
                raise srv.NotFound(eid)
            return self._format_event_detail(eid, events[eid])

        image_filter = params.get("image", [None])[0]
        type_filter = params.get("type", [None])[0]
        limit = int(params.get("limit", ["500"])[0])

        results = []
        for eid, raw in events.items():
            if eid == "namespace":
                continue
            ed = srv.get_entity_data(raw)
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
        srv = server_state()
        info = {"id": eid, "name": srv.ms.localize(eid + ".t")}
        etype = srv.get_field(ed, "type")
        if etype:
            info["type"] = etype
        event_image = srv.get_field(ed, "event_image")
        if event_image and isinstance(event_image, dict):
            video = srv.get_field(event_image, "video")
            if video:
                info["video"] = video.strip('"')
            texture = srv.get_field(event_image, "texture")
            if texture:
                info["image"] = texture.strip('"')
        icon = srv.get_field(ed, "icon")
        if icon:
            info["icon"] = icon.strip('"')
        return info

    def _format_event_detail(self, eid, raw):
        srv = server_state()
        ed = srv.get_entity_data(raw)
        info = self._format_event_summary(eid, ed)
        info["title_key"] = eid + ".t"
        info["desc_key"] = eid + ".d"
        # Collect option keys
        options = []
        if isinstance(ed, dict):
            for key in ed:
                if key == "option":
                    opt_data = srv.get_field(ed, "option")
                    if isinstance(opt_data, dict):
                        name = srv.get_field(opt_data, "name")
                        if name:
                            options.append(name)
                    elif isinstance(opt_data, list):
                        for opt in opt_data:
                            if isinstance(opt, dict):
                                name = srv.get_field(opt, "name")
                                if name:
                                    options.append(name)
        info["options"] = options
        info["raw"] = srv.serialize(raw)
        return info

    # ---- structured: institutions -----------------------------------------
    def _institutions(self, parts):
        """GET /institutions[/<institution_id>]  - institution data with modifiers per level."""
        srv = server_state()
        institutions = srv.ms.get_data("Institutions")
        if not institutions:
            raise srv.DataNotLoaded("Institutions")

        if parts:
            iid = parts[0]
            if iid not in institutions:
                raise srv.NotFound(iid)
            return self._format_institution_detail(iid, institutions[iid])

        return [
            self._format_institution_summary(iid, institutions[iid])
            for iid in institutions
        ]

    def _format_institution_summary(self, iid, raw):
        srv = server_state()
        ed = srv.get_entity_data(raw)
        info = {"type": "Institutions", "id": iid, "name": srv.ms.localize(iid)}
        tech = srv.get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": srv.ms.localize(tech[0])}
        return info

    def _format_institution_detail(self, iid, raw):
        srv = server_state()
        ed = srv.get_entity_data(raw)
        info = {"type": "Institutions", "id": iid, "name": srv.ms.localize(iid)}
        desc = srv.ms.get_description(iid)
        if desc:
            info["description"] = desc
        tech = srv.get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": srv.ms.localize(tech[0])}
        # Extract modifier data
        modifier = srv.get_field(ed, "modifier")
        if modifier and isinstance(modifier, dict):
            info["modifier"] = {}
            for k, v in modifier.items():
                info["modifier"][k] = v[1] if isinstance(v, tuple) else v
        info["raw"] = srv.serialize(raw)
        return info

    # ---- structured: production methods -----------------------------------
    def _production_methods(self, parts, params):
        """GET /production-methods                    - list all PMs
        GET /production-methods/<pm_id>           - PM detail with modifiers
        GET /production-methods?building=<bid>    - PMs for a specific building
        """
        srv = server_state()
        pms = srv.ms.get_data("PMs")
        if not pms:
            raise srv.DataNotLoaded("PMs")

        if parts:
            pid = parts[0]
            if pid not in pms:
                raise srv.NotFound(pid)
            return self._format_pm_detail(pid, pms[pid])

        building_filter = params.get("building", [None])[0]
        if building_filter:
            return self._pms_for_building(building_filter)

        return [
            self._format_pm_summary(pid, pms[pid])
            for pid in pms
        ]

    def _format_pm_summary(self, pid, raw):
        srv = server_state()
        ed = srv.get_entity_data(raw)
        info = {"type": "PMs", "id": pid, "name": srv.ms.localize(pid)}
        tech = srv.get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": srv.ms.localize(tech[0])}
        return info

    def _format_pm_detail(self, pid, raw):
        srv = server_state()
        ed = srv.get_entity_data(raw)
        info = {"type": "PMs", "id": pid, "name": srv.ms.localize(pid)}
        tech = srv.get_field(ed, "unlocking_technologies")
        if tech and isinstance(tech, list) and tech:
            info["unlocking_technology"] = {"type": "Technologies", "id": tech[0], "name": srv.ms.localize(tech[0])}
        # Building modifiers
        for mod_key in ("building_modifiers", "country_modifiers", "state_modifiers"):
            mod_data = srv.get_field(ed, mod_key)
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
        info["raw"] = srv.serialize(raw)
        return info

    def _pms_for_building(self, building_id):
        """Return all PMs for a specific building, grouped by PM group."""
        srv = server_state()
        buildings = srv.ms.get_data("Buildings")
        pmg_data = srv.ms.get_data("PM Groups")
        pm_data = srv.ms.get_data("PMs")
        if not buildings or not pmg_data or not pm_data:
            raise srv.DataNotLoaded("Required")
        if building_id not in buildings:
            raise srv.NotFound(building_id)

        bd = srv.get_entity_data(buildings[building_id])
        pmg_ids = srv.get_field(bd, "production_method_groups")
        if not pmg_ids or not isinstance(pmg_ids, list):
            return {"building": building_id, "pm_groups": []}

        result_groups = []
        for pmg_id in pmg_ids:
            group = {
                "type": "PM Groups", "id": pmg_id,
                "name": srv.ms.localize(pmg_id), "pms": [],
            }
            if pmg_id in pmg_data:
                pmg_inner = srv.get_entity_data(pmg_data[pmg_id])
                pm_ids = srv.get_field(pmg_inner, "production_methods")
                if pm_ids and isinstance(pm_ids, list):
                    for pid in pm_ids:
                        if pid in pm_data:
                            group["pms"].append(self._format_pm_detail(pid, pm_data[pid]))
                        else:
                            group["pms"].append({
                                "type": "PMs", "id": pid, "name": srv.ms.localize(pid),
                            })
            result_groups.append(group)
        return {
            "type": "Buildings", "id": building_id,
            "name": srv.ms.localize(building_id), "pm_groups": result_groups,
        }

    # ---- structured: journal entries --------------------------------------
    def _journal_entries(self, parts):
        """GET /journal-entries[/<je_id>]  - journal entry listing or detail."""
        srv = server_state()
        jes = srv.ms.get_data("Journal Entries")
        if not jes:
            raise srv.DataNotLoaded("Journal Entries")

        if parts:
            jeid = parts[0]
            if jeid not in jes:
                raise srv.NotFound(jeid)
            return self._format_je_detail(jeid, jes[jeid])

        return [
            self._format_je_summary(jeid, jes[jeid])
            for jeid in jes
        ]

    def _format_je_summary(self, jeid, raw):
        srv = server_state()
        ed = srv.get_entity_data(raw)
        info = {"type": "Journal Entries", "id": jeid, "name": srv.ms.localize(jeid)}
        group = srv.get_field(ed, "group")
        if group:
            info["group"] = group
        return info

    def _format_je_detail(self, jeid, raw):
        srv = server_state()
        ed = srv.get_entity_data(raw)
        info = {"type": "Journal Entries", "id": jeid, "name": srv.ms.localize(jeid)}
        group = srv.get_field(ed, "group")
        if group:
            info["group"] = group
        icon = srv.get_field(ed, "icon")
        if icon:
            info["icon"] = icon
        info["raw"] = srv.serialize(raw)
        return info

    # ---- structured: diplomatic actions -----------------------------------
    def _diplomatic_actions(self, parts):
        """GET /diplomatic-actions[/<id>]

        Catalog of `common/diplomatic_actions/` — the `type` vocabulary that
        feeds `has_diplomatic_pact = { who = X type = Y }`. List form returns
        summary rows; detail form adds the full `pact` block + raw AST.
        """
        srv = server_state()
        actions = srv.ms.get_data("Diplomatic Actions")
        if not actions:
            raise srv.DataNotLoaded("Diplomatic Actions")

        def _summary(aid):
            ed = srv.get_entity_data(actions[aid])
            ed_dict = ed if isinstance(ed, dict) else {}

            raw_groups = srv.get_field(ed_dict, "groups", []) or []
            if isinstance(raw_groups, str):
                group_list = [raw_groups]
            elif isinstance(raw_groups, list):
                group_list = [g for g in raw_groups if isinstance(g, str)]
            else:
                group_list = []

            pact = srv.get_field(ed_dict, "pact")
            if isinstance(pact, list):
                pact_dict: dict = {}
                for item in pact:
                    if isinstance(item, dict):
                        pact_dict.update(item)
            elif isinstance(pact, dict):
                pact_dict = pact
            else:
                pact_dict = {}

            subject_type = srv.get_field(pact_dict, "subject_type")
            is_subject_relation = bool(subject_type) or any(
                g in ("subject", "overlord") for g in group_list
            )
            if is_subject_relation:
                category = "subject_relation"
            elif "power_bloc" in group_list:
                category = "power_bloc"
            elif group_list:
                category = group_list[0]
            else:
                category = "uncategorized"

            return {
                "type": "Diplomatic Actions",
                "id": aid,
                "name": srv.ms.localize(aid),
                "category": category,
                "groups": group_list,
                "requires_approval": srv.get_field(ed_dict, "requires_approval"),
                "is_subject_relation": is_subject_relation,
                "is_two_sided_pact": srv.get_field(pact_dict, "is_two_sided_pact"),
                "subject_type": subject_type,
            }

        if parts:
            aid = parts[0]
            if aid not in actions:
                raise srv.NotFound(aid)
            info = _summary(aid)
            ed = srv.get_entity_data(actions[aid])
            ed_dict = ed if isinstance(ed, dict) else {}
            info["pact"] = srv.serialize(ed_dict.get("pact"))
            info["raw"] = srv.serialize(actions[aid])
            return info

        return [_summary(aid) for aid in actions]

    # ---- structured: treaty articles --------------------------------------
    def _treaty_articles(self, parts):
        """GET /treaty-articles                       - list all
           GET /treaty-articles/<id>                  - detail
           GET /treaty-articles/<id>/loc-keys         - loc-key family"""
        srv = server_state()
        arts = srv.ms.get_data("Treaty Articles")
        if not arts:
            raise srv.DataNotLoaded("Treaty Articles")

        if not parts:
            return [
                {"type": "Treaty Articles", "id": aid, "name": srv.ms.localize(aid)}
                for aid in arts
            ]

        aid = parts[0]
        if aid not in arts:
            raise srv.NotFound(aid)

        if len(parts) >= 2:
            if parts[1] == "loc-keys":
                return self._loc_keys(["Treaty Articles", aid])
            raise srv.NotFound(parts[1])

        return {
            "type": "Treaty Articles", "id": aid,
            "name": srv.ms.localize(aid),
            "raw": srv.serialize(arts[aid]),
        }

    # ---- structured: decisions --------------------------------------------
    def _decisions(self, parts):
        """GET /decisions[/<decision_id>]"""
        srv = server_state()
        decisions = srv.ms.get_data("Decisions")
        if not decisions:
            raise srv.DataNotLoaded("Decisions")

        if parts:
            did = parts[0]
            if did not in decisions:
                raise srv.NotFound(did)
            return {
                "type": "Decisions", "id": did,
                "name": srv.ms.localize(did), "raw": srv.serialize(decisions[did]),
            }

        return [
            {"type": "Decisions", "id": did, "name": srv.ms.localize(did)}
            for did in decisions
        ]

    # ---- structured: script values ----------------------------------------
    def _script_values(self, parts):
        """GET /script-values[/<sv_id>]"""
        srv = server_state()
        svs = srv.ms.get_data("Script Values")
        if not svs:
            raise srv.DataNotLoaded("Script Values")

        if parts:
            svid = parts[0]
            if svid not in svs:
                raise srv.NotFound(svid)
            return {"type": "Script Values", "id": svid, "raw": srv.serialize(svs[svid])}

        return [{"type": "Script Values", "id": svid} for svid in svs]

    # ---- mod-vs-vanilla diff ----------------------------------------------
    def _diff(self, parts, params):
        """GET /diff/<EntityType>/<id>[?format=text]"""
        srv = server_state()
        if len(parts) < 2:
            raise srv.BadRequest("Provide /diff/<EntityType>/<id>")
        etype, eid = parts[0], parts[1]
        if etype not in srv.ms.mod_parsers:
            raise srv.NotFound(etype)
        mod_data = srv.ms.get_data(etype) or {}
        if eid not in mod_data:
            raise srv.NotFound(eid)
        base_parser = srv.ms.base_parsers.get(etype)
        base_data = base_parser.data if base_parser is not None else {}
        in_vanilla = eid in base_data

        fmt = (params.get("format", [""])[0] or "").lower()
        if fmt == "text":
            van_text = _paradox_text(eid, base_data[eid]) if in_vanilla else ""
            mod_text = _paradox_text(eid, mod_data[eid])
            diff = difflib.unified_diff(
                van_text.splitlines(), mod_text.splitlines(),
                fromfile=f"vanilla/{etype}/{eid}",
                tofile=f"mod/{etype}/{eid}", lineterm="",
            )
            return {
                "type": etype, "id": eid, "in_vanilla": in_vanilla,
                "format": "text", "diff": "\n".join(diff),
            }

        mod_entity = srv.get_entity_data(mod_data[eid])
        van_entity = srv.get_entity_data(base_data[eid]) if in_vanilla else {}
        added, removed, changed = _diff_entity_fields(van_entity, mod_entity)
        return {
            "type": etype, "id": eid, "in_vanilla": in_vanilla,
            "added": added, "removed": removed, "changed": changed,
        }

    # ---- structured: scripted effects / triggers --------------------------
    def _scripted_effects(self, parts):
        """GET /scripted-effects[/<id>]"""
        return self._scripted_helper("Scripted Effects", parts)

    def _scripted_triggers(self, parts):
        """GET /scripted-triggers[/<id>]"""
        return self._scripted_helper("Scripted Triggers", parts)

    def _scripted_helper(self, etype, parts):
        srv = server_state()
        data = srv.ms.get_data(etype)
        if not data:
            raise srv.DataNotLoaded(etype)
        if parts:
            hid = parts[0]
            if hid not in data:
                raise srv.NotFound(hid)
            return {
                "type": etype,
                "id": hid,
                "parameters": _extract_parameters(data[hid]),
                "callers": srv._get_call_index().get(hid, []),
                "raw": srv.serialize(data[hid]),
            }
        return [
            {"type": etype, "id": hid, "parameters": _extract_parameters(raw)}
            for hid, raw in data.items()
        ]

    # ---- structured: decrees ----------------------------------------------
    def _decrees(self, parts):
        """GET /decrees[/<decree_id>]"""
        srv = server_state()
        decrees = srv.ms.get_data("Decrees")
        if not decrees:
            raise srv.DataNotLoaded("Decrees")

        if parts:
            did = parts[0]
            if did not in decrees:
                raise srv.NotFound(did)
            ed = srv.get_entity_data(decrees[did])
            info = {"type": "Decrees", "id": did, "name": srv.ms.localize(did)}
            desc = srv.ms.get_description(did)
            if desc:
                info["description"] = desc
            modifier = srv.get_field(ed, "modifier")
            if modifier and isinstance(modifier, dict):
                info["modifier"] = {
                    k: v[1] if isinstance(v, tuple) else v
                    for k, v in modifier.items()
                }
            info["raw"] = srv.serialize(decrees[did])
            return info

        return [
            {"type": "Decrees", "id": did, "name": srv.ms.localize(did)}
            for did in decrees
        ]

    # ---- structured: on-actions -------------------------------------------
    def _on_actions(self, parts):
        """GET /on-actions[/<on_action_id>] (#333)

        The engine merges every declaration of an on-action; the parsed store
        keeps the last one read. So one on-action comes back with every
        declaration on disk (`sources`, in load order: file, line, origin, its
        `on_actions`, `events` and `random_events`, its `chance_to_happen`,
        and the fields it sets), `merged`, `fields_set_more_than_once` and
        `fired_by`, the declarations whose `on_actions` list names it. `raw`
        is still the store's block, i.e. the last declaration only.

        `merged` holds what the recorded rules allow: `on_actions` and
        `events` added up, and `random_events` only when one declaration sets
        it (several are separate pools, each with its own chance_to_happen,
        and how they combine is not recorded: null, with a note). It is null
        altogether when a declaration carries a directive. For an `effect` two
        declarations set, `fields_set_more_than_once` names the later file's
        as `winner` and gives the rule's status (documented, not probed); any
        other field set twice has no recorded rule and no winner.

        Load order is one list by file name, vanilla's files and the mod's
        together (probed). Reads `common/on_actions` from disk on each call
        (about 40 ms), so it follows edits without a /reload. Vanilla's
        declarations are read only where the game is installed (they are not
        in vanilla_parsed/): `vanilla_indexed` says which, and without them
        `origin` reads "mod (vanilla not indexed)". The bare listing is the
        on-actions a mod file declares, each with its declaration count and
        files. A file the scan warned about (an unclosed brace swallows the
        on-actions after it) shows as `warnings` on the rows and entries that
        name it, and in the 404 body of a lookup that finds nothing."""
        srv = server_state()
        import on_action_index

        oas = (srv.ms.get_data("On Actions") if srv.ms else None) or {}
        index = on_action_index.scan(srv.mod_path, os.path.join(srv.base_game_path, "game"))
        if not oas and not index.declarations:
            raise srv.DataNotLoaded("On Actions")

        if not parts:
            listing = index.listing()
            listed = {row["id"] for row in listing}
            # In the loaded store but no longer declared on disk.
            listing.extend({"type": "On Actions", "id": oaid, "declarations": 0, "files": []}
                           for oaid in oas if oaid not in listed)
            return listing

        oaid = parts[0]
        entry = index.entry(oaid)
        if entry is None:
            if oaid not in oas:
                if index.warnings:
                    # A broken file can hide the on-action asked for.
                    raise srv.NotFound(oaid, scan_warnings=index.warnings)
                raise srv.NotFound(oaid)
            entry = {
                "type": "On Actions", "id": oaid, "origin": index.origin_of(oaid),
                "vanilla_indexed": index.vanilla_indexed, "declarations": 0, "sources": [],
                "note": "In the server's loaded store, but no file under common/on_actions "
                        "declares it now: the store predates an edit (POST /reload).",
            }
            if index.warnings:
                entry["warnings"] = index.warnings
        hook = next((e for e in srv.engine_docs.get("on-actions") or []
                     if e.get("name") == oaid), None)
        if hook is not None:
            # on_actions.log: an on-action the engine itself knows.
            entry["engine"] = {"from_code": bool(hook.get("from_code")),
                               "scopes": hook.get("scopes") or []}
        if oaid in oas:
            entry["raw"] = srv.serialize(oas[oaid])
            if entry["declarations"] > 1:
                entry["raw_note"] = ("raw is the parsed store's block, which keeps one per "
                                     "name: the last declaration read. Read sources and merged.")
        return entry
