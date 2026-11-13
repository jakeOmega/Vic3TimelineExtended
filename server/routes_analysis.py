"""The analytical routes: GET /references, /tech-tree, /unlocked-by, /tech-unlocks,
/technology-effects, /modifier-search, /modifier-grants, /annotators,
/movement-stances, /event-balance, /scripted-helpers/unresolved, /script-args,
/variable-usage, /loc-accessors, /on-action-callers, /pm-employment and
/unlocalized, with the helpers only they use. Moved out of mod_state_server.py
unchanged (#1537).

A route module holds code only (server/__init__.py says why): the state these
routes read stays in mod_state_server and is read as `srv.<name>` through
`server_state()` at call time. mod_state_server re-exports every name below.
"""
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import annotators
import effect_trigger_validity_audit
import loc_accessor_usage
import pm_employment_audit
import script_argument_audit
import tech_unlocks_lib
import variable_usage
from paradox_file_parser import ParadoxFileParser

from server import server_state


# ---------------------------------------------------------------------------
# Reverse modifier-GRANT lookup  (issues #128, #327)
#
# `/engine-docs/usage/<name>` greps for effect/trigger CALL sites and is blind
# to `modifier = { <name> = <value> }` APPLICATION blocks inside laws, techs,
# country ranks, institutions, company types, production methods, ... This
# scans the entity files directly (the parser discards file/line, so a file
# scan is the only way to satisfy the {entity_type, entity_id, file, line,
# value} contract) and answers "which entities GRANT modifier X, and at what
# value?".
#
# It walks EVERY `common/` entity directory (minus _GRANT_SKIP_DIRS) rather
# than an allow-list, because an allow-list fails silently: the first version
# covered seven types and a monetary-policy inventory found 16 of 88 grant
# sites missing with `truncated: false` (#327). A directory missing from
# MODIFIER_GRANT_SOURCES is still scanned, under a name derived from the
# directory. `mode`:
#   "wrapped" — modifier keys live inside a named bag block (`modifier`,
#               `member_modifier`, `prosperity_modifier`, `country_modifiers`
#               ...; see _is_modifier_bag).
#   "direct"  — modifier keys are direct fields of the entity (static
#               modifiers have no wrapper).
# ---------------------------------------------------------------------------
MODIFIER_GRANT_SOURCES: list[tuple[str, str, str]] = [
    ("Laws",                  "laws",                                      "wrapped"),
    ("Technologies",          "technology/technologies",                   "wrapped"),
    ("Decrees",               "decrees",                                   "wrapped"),
    ("Amendments",            "amendments",                                "wrapped"),
    ("Principles",            "power_bloc_principles",                     "wrapped"),
    ("Buildings",             "buildings",                                 "wrapped"),
    ("Modifiers",             "static_modifiers",                          "direct"),
    ("Country Ranks",         "country_ranks",                             "wrapped"),
    ("Institutions",          "institutions",                              "wrapped"),
    ("Company Types",         "company_types",                             "wrapped"),
    ("Interest Group Traits", "interest_group_traits",                     "wrapped"),
    ("PMs",                   "production_methods",                        "wrapped"),
    ("Character Traits",      "character_traits",                          "wrapped"),
    ("Power Bloc Identities", "power_bloc_identities",                     "wrapped"),
    ("Treaty Articles",       "treaty_articles",                           "wrapped"),
    ("State Traits",          "state_traits",                              "wrapped"),
    ("Diplomatic Actions",    "diplomatic_actions",                        "wrapped"),
    ("Mobilization Options",  "mobilization_options",                      "wrapped"),
    ("Combat Unit Types",     "combat_unit_types",                         "wrapped"),
    ("Combat Unit Experience Levels", "combat_unit_experience_levels",     "wrapped"),
    ("Ship Types",            "ship_types",                                "wrapped"),
    ("Ship Modifications",    "ship_modifications",                        "wrapped"),
    ("Battle Conditions",     "battle_conditions",                         "wrapped"),
    ("Harvest Condition Types", "harvest_condition_types",                 "wrapped"),
]


# `common/` directories that hold script (effects, triggers, weights, GUIs,
# config), not entities that carry modifier bags. A `modifier = { add = 1 }`
# weight block or a `*_modifier = { ... }` argument list in these would look
# like a bag, so they stay out of the walk. Everything else is scanned.
_GRANT_SKIP_DIRS: frozenset[str] = frozenset({
    "scripted_effects", "scripted_triggers", "scripted_modifiers",
    "scripted_guis", "scripted_buttons", "scripted_progress_bars",
    "scripted_rules", "script_values", "on_actions",
    "customizable_localization", "defines", "modifier_type_definitions",
    "game_rules", "history", "flag_definitions", "named_colors",
    "dynamic_country_names", "dynamic_treaty_names", "ai_strategies",
})


# Entity directories that sit one level down (`technology/technologies`,
# `technology/eras`, ...) instead of directly under common/.
_GRANT_NESTED_PARENTS: frozenset[str] = frozenset({"technology"})


# Per-unit scaling sub-wrappers that may sit between a bag and its grant lines.
_SCALING_WRAPPERS: frozenset[str] = frozenset({
    "workforce_scaled", "level_scaled", "unscaled", "throughput_scaled",
    "timed_modifier",
})


# Blocks that hold bags without being one (`pact = { first_modifier = {...} }`
# in diplomatic actions).
_BAG_CONTAINERS: frozenset[str] = frozenset({"pact"})


# Entity ids may contain `-` (`post-scarcity_economy`, `law_post-scarcity`,
# `e-commerce`, #327); the first character stays a letter/underscore so a
# `-1 = {` or `value = -1` line can never open an entity. An optional
# directive prefix (`INJECT:`, `REPLACE:`, `REPLACE_OR_CREATE:`, ...) is
# captured separately: with only `INJECT:`/`REPLACE:` allowed, an entity opened
# by `REPLACE_OR_CREATE:` (158 in the mod's building, building group and PM group
# files) never opened, and any grant in it would have been dropped (#327).
_GRANT_OPENER_RE = re.compile(
    r"^\s*(?:(?P<directive>[A-Z][A-Z_]*):)?(?P<name>[A-Za-z_][\w-]*)\s*=\s*\{"
)


_GRANT_LINE_RE = re.compile(
    r"^\s*([a-z_][a-z0-9_]*)\s*=\s*(-?\d+(?:\.\d+)?|yes|no)\s*$"
)


# A mod entity that REPLACEs a vanilla one wholesale (the vanilla copy's grants
# are not in effect).
_GRANT_REPLACE_RE = re.compile(
    r"^\s*REPLACE(?:_OR_CREATE)?:(?P<name>[A-Za-z_][\w-]*)\s*=\s*\{"
)


def _grant_block_label(name_stack: list, mode: str):
    """Return the block label if `name_stack` (one frame per open brace, [0] =
    entity) places the current line inside a modifier-grant context, else None.

    direct: keys must be direct entity fields (stack == [entity]).
    wrapped: the first block inside the entity (or inside a _BAG_CONTAINERS
             block) must be a modifier bag; only per-unit scaling wrappers may
             nest between it and the line."""
    srv = server_state()
    if mode == "direct":
        return "direct" if len(name_stack) == 1 else None
    idx = 1
    label = ""
    if len(name_stack) > 1 and name_stack[1] in _BAG_CONTAINERS:
        label = name_stack[1] + "/"
        idx = 2
    if len(name_stack) <= idx or not srv._is_modifier_bag(name_stack[idx]):
        return None
    label += name_stack[idx]
    for extra in name_stack[idx + 1:]:
        if extra not in _SCALING_WRAPPERS:
            return None
        label += "/" + extra
    return label


def _scan_file_for_grants(abs_path: str, rel: str, entity_type: str, mode: str,
                          origin: str, target):
    """Yield grant dicts for one file. Line-by-line state machine: tracks the
    column-0 entity opener and a name stack parallel to brace depth. Paradox
    files are one-token-per-line, so a line is an opener, a grant, or a closer;
    single-line `bag = { k = v }` with inline numerics, several `k = v` pairs on
    one line and `k = @constant` values do not occur in the entity dirs
    (verified) and are a documented blind spot.

    A file that does not contain `target` at all is skipped without the line
    scan: walking every entity directory per query stays cheap that way."""
    try:
        with open(abs_path, "r", encoding="utf-8-sig", errors="replace") as f:
            content = f.read()
    except OSError:
        return
    if target is not None and target not in content:
        return
    depth = 0
    name_stack: list = []
    current_entity = None
    for lineno, raw in enumerate(content.split("\n"), 1):
        text = raw.split("#", 1)[0]

        # Grant candidate (no brace on the line) — test in current context.
        gm = _GRANT_LINE_RE.match(text)
        if gm and current_entity is not None and "{" not in text and "}" not in text:
            key, value = gm.group(1), gm.group(2)
            if target is None or key == target:
                label = _grant_block_label(name_stack, mode)
                if label is not None:
                    if value in ("yes", "no"):
                        coerced = value
                    else:
                        coerced = float(value) if "." in value else int(value)
                    yield {
                        "entity_type": entity_type,
                        "entity_id": current_entity,
                        "origin": origin,
                        "file": rel,
                        "line": lineno,
                        "value": coerced,
                        "block": label,
                    }

        # Update brace depth + name stack from this line.
        opener = _GRANT_OPENER_RE.match(text)
        opens = text.count("{")
        closes = text.count("}")
        if opener and opens:
            name = opener.group("name")
            if depth == 0:
                current_entity = name
            name_stack.append(name)
            for _ in range(opens - 1):
                name_stack.append(None)
            depth += opens
        elif opens:
            for _ in range(opens):
                name_stack.append(None)
            depth += opens
        for _ in range(closes):
            if name_stack:
                name_stack.pop()
            depth -= 1
            if depth <= 0:
                depth = 0
                current_entity = None
                name_stack = []


def _grant_entity_dirs(common_root: str) -> list[str]:
    """Every entity directory under a `common/` root, as '/'-joined paths
    relative to it (`laws`, `technology/technologies`)."""
    try:
        names = sorted(os.listdir(common_root))
    except OSError:
        return []
    found: list[str] = []
    for name in names:
        if name in _GRANT_SKIP_DIRS or name.startswith(("_", ".")):
            continue
        path = os.path.join(common_root, name)
        if not os.path.isdir(path):
            continue
        if name in _GRANT_NESTED_PARENTS:
            for sub in sorted(os.listdir(path)):
                if os.path.isdir(os.path.join(path, sub)):
                    found.append(f"{name}/{sub}")
        else:
            found.append(name)
    return found


def _grant_entity_type_name(subdir: str) -> str:
    """Display name for an entity directory: the MODIFIER_GRANT_SOURCES name,
    else the directory path title-cased (`interest_group_traits` ->
    `Interest Group Traits`)."""
    for entity_type, known_dir, _mode in MODIFIER_GRANT_SOURCES:
        if known_dir == subdir:
            return entity_type
    return subdir.replace("/", " ").replace("_", " ").title()


def _grant_scan_plan(common_roots: list[str]) -> list[tuple[str, str, str]]:
    """[(entity_type, subdir, mode)] for every entity directory present under
    any of `common_roots`: the MODIFIER_GRANT_SOURCES order first, then every
    other directory alphabetically."""
    present: set[str] = set()
    for root in common_roots:
        present.update(_grant_entity_dirs(root))
    plan = [(et, sub, mode) for et, sub, mode in MODIFIER_GRANT_SOURCES
            if sub in present]
    known = {sub for _, sub, _ in plan}
    plan.extend((_grant_entity_type_name(sub), sub, "wrapped")
                for sub in sorted(present - known))
    return plan


def _grant_type_key(name: str) -> str:
    """Normal form for matching an entity-type filter: case, spaces and
    underscores don't matter (`PMs`, `pms`, `Country Ranks`, `country_ranks`)."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _mod_replaced_entity_ids(scan_dir: str) -> set[str]:
    """Ids of the vanilla entities the mod `REPLACE:`s (or `REPLACE_OR_CREATE:`s)
    in one entity directory."""
    ids: set[str] = set()
    for dirpath, dirs, files in os.walk(scan_dir):
        dirs.sort()
        for fname in sorted(files):
            if not fname.endswith(".txt") or fname.startswith("_"):
                continue
            try:
                with open(os.path.join(dirpath, fname), "r",
                          encoding="utf-8-sig", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue
            if "REPLACE" not in content:
                continue
            for raw in content.split("\n"):
                m = _GRANT_REPLACE_RE.match(raw.split("#", 1)[0])
                if m:
                    ids.add(m.group("name"))
    return ids


def _find_modifier_grants(target: str, *, scope: str = "both",
                          limit: int = 200, entity_types=None,
                          effective: bool = False) -> dict:
    """Enumerate every entity that GRANTS modifier `target` across every
    `common/` entity directory. `scope` in {mod, vanilla, both}.

    `entity_types` (iterable of names, e.g. ["Laws", "pms"]) restricts the walk
    to those types; an unknown name is an error (unless no tree was found at all,
    where the answer is the empty result plus `warnings`). The whole walk always runs, so
    `total` is the true number of grant sites and `truncated` is exactly
    `total > returned`; `limit` only caps the rows returned.

    Under scope=both a vanilla row whose entity the mod replaces is still
    listed, marked `"shadowed_by": "mod"`: the mod `REPLACE:`s the entity, or
    ships a file at the same path as the vanilla file (which replaces the whole
    file). `effective=True` drops those rows."""
    srv = server_state()
    if not target or not re.match(r"^[a-z_][a-z0-9_]*$", target):
        return {
            "name": target,
            "error": "Invalid target name (expected snake_case identifier).",
            "grants": [],
        }
    if scope not in ("mod", "vanilla", "both"):
        return {
            "name": target,
            "error": "scope must be one of: mod, vanilla, both.",
            "grants": [],
        }

    # (origin, common-root, repo-root-for-relpath)
    roots: list[tuple[str, str, str]] = []
    if scope in ("mod", "both"):
        roots.append(("mod", srv._MOD_COMMON, srv.mod_path))
    if scope in ("vanilla", "both"):
        roots.append(("vanilla", srv._BASE_COMMON, os.path.join(srv.base_game_path, "game")))
    present_roots = [r for r in roots if os.path.isdir(r[1])]
    warnings = [
        f"{origin} common/ directory not found: {origin} grants were NOT scanned"
        for origin, common_root, _ in roots if not os.path.isdir(common_root)
    ]

    plan = _grant_scan_plan([r[1] for r in present_roots])
    wanted = {_grant_type_key(t) for t in entity_types or () if t.strip()}
    if wanted and plan:
        known = {}
        for et, sub, _mode in plan:
            known[_grant_type_key(et)] = et
            known[_grant_type_key(sub)] = et
        unknown = sorted(t for t in wanted if t not in known)
        if unknown:
            return {
                "name": target,
                "error": "Unknown entity type(s): " + ", ".join(unknown),
                "known_types": [et for et, _s, _m in plan],
                "grants": [],
            }
        plan = [(et, sub, mode) for et, sub, mode in plan
                if _grant_type_key(et) in wanted or _grant_type_key(sub) in wanted]

    # Mod entity ids / files that shadow vanilla ones, computed per directory
    # the first time a vanilla row needs them.
    replaced_cache: dict[str, set[str]] = {}

    def shadowed(row: dict, subdir: str) -> bool:
        if row["origin"] != "vanilla" or not os.path.isdir(srv._MOD_COMMON):
            return False
        if os.path.isfile(os.path.join(srv.mod_path, row["file"])):
            return True
        if subdir not in replaced_cache:
            replaced_cache[subdir] = _mod_replaced_entity_ids(
                os.path.join(srv._MOD_COMMON, *subdir.split("/")))
        return row["entity_id"] in replaced_cache[subdir]

    grants: list[dict] = []
    total = 0
    scanned_types: list[str] = []
    for entity_type, subdir, mode in plan:
        seen_dir = False
        for origin, common_root, repo_root in present_roots:
            scan_dir = os.path.join(common_root, *subdir.split("/"))
            if not os.path.isdir(scan_dir):
                continue
            seen_dir = True
            for dirpath, dirs, files in os.walk(scan_dir):
                dirs.sort()
                for fname in sorted(files):
                    if not fname.endswith(".txt") or fname.startswith("_"):
                        continue
                    abs_path = os.path.join(dirpath, fname)
                    rel = os.path.relpath(abs_path, repo_root).replace(os.sep, "/")
                    for grant in _scan_file_for_grants(
                        abs_path, rel, entity_type, mode, origin, target
                    ):
                        if shadowed(grant, subdir):
                            if effective:
                                continue
                            grant["shadowed_by"] = "mod"
                        total += 1
                        if len(grants) < limit:
                            grants.append(grant)
        if seen_dir and entity_type not in scanned_types:
            scanned_types.append(entity_type)

    return {
        "name": target,
        "scope": scope,
        "effective": effective,
        "entity_types_scanned": scanned_types,
        "origins_scanned": [r[0] for r in present_roots],
        "warnings": warnings,
        "total": total,
        "returned": len(grants),
        "truncated": total > len(grants),
        "grants": grants,
    }


def _get_script_args_result():
    srv = server_state()
    with srv._script_args_lock:
        gen = srv._call_index_generation
        cached = srv._script_args_cache
        if cached is not None and cached[0] == gen:
            return cached[1]
        result = script_argument_audit.audit(mod_path=srv.mod_path)
        srv._script_args_cache = (gen, result)
        return result


def _get_variable_usage_index():
    srv = server_state()
    with srv._variable_usage_lock:
        gen = srv._call_index_generation
        cached = srv._variable_usage_cache
        if cached is not None and cached[0] == gen:
            return cached[1]
        index = variable_usage.build_index(srv.mod_path)
        srv._variable_usage_cache = (gen, index)
        return index


def _get_loc_accessor_index():
    srv = server_state()
    loc = srv._VANILLA_LOC_CACHE
    if loc is None:
        raise srv.DataNotLoaded("Localization")
    with srv._loc_accessor_lock:
        cached = srv._loc_accessor_cache
        if cached is not None and cached[0] is loc:
            return cached[1], cached[2]
        catalog = loc_accessor_usage.load_catalog(os.path.join(srv.mod_path, "docs", "engine"))
        actions = srv.ms.base_parsers.get("Diplomatic Actions") if srv.ms else None
        index = loc_accessor_usage.build_index(
            loc, catalog,
            diplo_keys=set(actions.data or {}) if actions else set(),
            gui_dirs=[os.path.join(srv.base_game_path, "game", "gui")],
        )
        srv._loc_accessor_cache = (loc, index, catalog)
        return index, catalog


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


def _extract_modifier_fields(obj, prefix="", bool_keys=None):
    """Walk parsed data and collect field names that look like modifiers (contain _ + end with _add/_mult etc).

    Numeric values are kept as floats. A `yes`/`no` value is kept (as the
    string) only when its key is in `bool_keys`, the registered modifier types:
    boolean modifiers are granted as `country_x_bool = yes`, and restricting
    them to registered names keeps the ~15k trigger/flag lines like
    `is_at_war = yes` or `default_option = yes` out (#336)."""
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
                        if (bool_keys and isinstance(val, str)
                                and val.lower() in ("yes", "no") and k in bool_keys):
                            found[k] = val.lower()
            if isinstance(v, (dict, tuple, list)):
                found.update(_extract_modifier_fields(v, prefix, bool_keys))
    elif isinstance(obj, (tuple, list)):
        for item in obj:
            found.update(_extract_modifier_fields(item, prefix, bool_keys))
    return found


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


def _try_float(s):
    if isinstance(s, (int, float)):
        return float(s)
    if isinstance(s, str):
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _modifier_color_lookup(mod_name):
    """Return 'good'/'bad'/'neutral'/None for a modifier_type name (e.g. country_bureaucracy_mult)."""
    srv = server_state()
    mod_types = srv.ms.get_data("Modifier Types")
    if not mod_types or mod_name not in mod_types:
        return None
    data = srv._flatten_entity_data(mod_types[mod_name])
    color = srv.get_field(data, "color")
    if isinstance(color, str):
        return color
    return None


def _resolve_static_modifier(name):
    """Look up a static modifier and return list of {modifier, value} pairs (numeric fields only)."""
    srv = server_state()
    mods = srv.ms.get_data("Modifiers")
    if not mods or name not in mods:
        return None
    data = srv._flatten_entity_data(mods[name])
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
    srv = server_state()
    if isinstance(value, str):
        mod_name = value
        block = {}
    else:
        block = srv._flatten_entity_data(value) if not isinstance(value, dict) else value
        mod_name = srv.get_field(block, "name")
        if isinstance(mod_name, str):
            mod_name = mod_name.strip('"')
    duration = srv.get_field(block, "days") or srv.get_field(block, "months") or srv.get_field(block, "years")
    multiplier = srv.get_field(block, "multiplier")
    is_decaying = srv.get_field(block, "is_decaying")
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
    srv = server_state()
    block = srv._flatten_entity_data(value) if not isinstance(value, dict) else value
    var_name = srv.get_field(block, "name")
    add = srv.get_field(block, "add")
    subtract = srv.get_field(block, "subtract")
    multiply = srv.get_field(block, "multiply")
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
    srv = server_state()
    data = srv._flatten_entity_data(node) if not isinstance(node, dict) else node
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
    srv = server_state()
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
    entry = {"kind": key, "args": srv.serialize(value)}
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
    """Parse a .txt event file and return the list of event IDs declared at top level.

    Request-supplied paths must come through `_event_ids_from_mod_file`, which
    contains them inside the mod tree first (#254)."""
    srv = server_state()
    if not os.path.isabs(file_path):
        file_path = os.path.join(srv.mod_path, file_path)
    if not os.path.isfile(file_path):
        return None, f"File not found: {file_path}"
    try:
        parser = ParadoxFileParser()
        parser.parse_file(file_path, apply_directives=False)
    except Exception as exc:
        return None, f"Failed to parse {file_path}: {exc}"
    ids = [k for k in parser.data.keys() if k != "namespace"]
    return ids, None


def _event_ids_from_mod_file(file_param):
    """Request-facing wrapper around _extract_event_ids_from_file: contains the
    caller-supplied path inside the mod tree (400 on an escape) and maps the
    helper's in-band error to a status — missing file 404, unparseable 400. (#254)"""
    srv = server_state()
    resolved = _resolve_mod_relative_path(file_param)
    ids, err = _extract_event_ids_from_file(resolved)
    if err:
        raise srv._EndpointError({"error": err}, 404 if err.startswith("File not found") else 400)
    return ids


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
        **({"name_variants": opt["name_variants"]} if opt.get("name_variants") else {}),
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
    srv = server_state()
    from event_magnitude_audit import parse_reviewed_comment
    out = {}
    events_dir = os.path.join(srv.mod_path, "events")
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
                out[eid] = {**rev, "file": os.path.relpath(path, srv.mod_path), "line": i + 1}
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
            for variant in (opt.get("name_variants") or [])[1:]:
                lines.append(f"    or, by its trigger: {variant.get('name') or variant.get('key')}")
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


def _resolve_mod_relative_path(raw: str, *, param: str = "file") -> str:
    """Resolve a caller-supplied path param to an absolute path guaranteed to
    live under `mod_path`. Raises BadRequest (400) otherwise.

    Before #254 `/event-balance?file=` passed absolute paths straight through
    and joined `..` segments onto mod_path, so any Paradox-parsable file on the
    machine was readable through the (localhost-only, GET-only) server. Every
    request-supplied filesystem path must go through this gate.
    """
    srv = server_state()
    value = (raw or "").strip()
    if not value:
        raise srv.BadRequest(f"Provide ?{param}=<path relative to the mod root>")
    if "\x00" in value:
        # `?file=x%00y` makes os.path.realpath raise ValueError; that's
        # malformed input, so answer 400 instead of letting it reach the
        # generic 500 handler. (#254)
        raise srv.BadRequest(f"?{param}= contains an embedded NUL byte")
    if value.startswith(("/", "\\")) or os.path.isabs(value) or re.match(r"^[A-Za-z]:", value):
        raise srv.BadRequest(
            f"?{param}= must be relative to the mod root (absolute paths are rejected)",
            got=value,
        )
    root = os.path.realpath(srv.mod_path)
    resolved = ""
    try:
        resolved = os.path.realpath(os.path.join(root, value))
        inside = resolved == root or os.path.commonpath([root, resolved]) == root
    except ValueError:
        # Different drives on Windows, or any other un-resolvable spelling:
        # treat as outside rather than letting it become a 500.
        inside = False
    if not inside:
        raise srv.BadRequest(
            f"?{param}= must stay inside the mod tree", got=value, resolved_outside=True,
        )
    return resolved


def _option_name_keys(name) -> list[str]:
    """The loc keys an option's `name` can show, in source order.

    A plain `name = KEY` is one key. A triggered name, `name = { trigger =
    {...} text = KEY }`, parses as a dict, and written once per case (the
    engine shows the first whose trigger holds) as a list of `(op, dict)`
    pairs. Anything without a `text` is left out."""
    if name is None:
        return []
    entries = name if isinstance(name, list) else [name]
    keys = []
    for entry in entries:
        if isinstance(entry, tuple) and len(entry) >= 2:
            entry = entry[1]
        if isinstance(entry, dict):
            entry = entry.get("text")
            if isinstance(entry, tuple) and len(entry) >= 2:
                entry = entry[1]
        if isinstance(entry, str) and entry:
            keys.append(entry)
    return keys


class AnalysisRoutes:
    """The analytical and annotator routes. A mixin of ModStateHandler."""

    def _movement_stances(self, parts, params):
        """GET /movement-stances?lawgroup=<g>|law=<l>[&current=<law>],
        GET /movement-stances/gaps"""
        srv = server_state()
        import movement_stances
        from ideology_lawgroup_audit import carrier_laws, law_groups

        movements = srv.ms.get_data("Political Movements")
        laws = srv.ms.get_data("Laws")
        if not movements or not laws:
            raise srv.DataNotLoaded("Political Movements" if not movements else "Laws")
        ideologies = srv.ms.get_data("Ideologies") or {}
        carriers = carrier_laws(srv.mod_path)
        if parts == ["gaps"]:
            vanilla_groups = srv.ms.base_parsers.get("Law Groups")
            return movement_stances.stance_gaps(
                movements, ideologies, laws, carriers,
                set(vanilla_groups.data) if vanilla_groups is not None else None,
            )
        if parts:
            raise srv.NotFound("/movement-stances/" + "/".join(parts))
        lawgroup = (params.get("lawgroup") or [None])[0]
        law = (params.get("law") or [None])[0]
        current = (params.get("current") or [None])[0]
        mode = (params.get("mode") or [None])[0]
        if mode not in (None, "comparative"):
            raise srv.BadRequest(f"unknown mode {mode!r}; the only mode is 'comparative'")
        if mode == "comparative" and not current:
            raise srv.BadRequest("mode=comparative needs current=<law>")
        if bool(lawgroup) == bool(law):
            raise srv.BadRequest("Pass exactly one of lawgroup=<lawgroup_x> or law=<law_x>, "
                             "or use /movement-stances/gaps")
        if law:
            lawgroup = law_groups(laws).get(law)
            if lawgroup is None:
                raise srv.NotFound(law)
        try:
            out = movement_stances.lawgroup_stances(
                lawgroup, movements, ideologies, laws, carriers, current)
        except ValueError as exc:
            raise srv.BadRequest(str(exc))
        if out is None:
            raise srv.NotFound(lawgroup)
        return out

    # ---- analytical: references -------------------------------------------
    def _references(self, parts):
        """GET /references/<key>  - find all entities that reference a given key."""
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide a key, e.g. /references/nuclear_fission")
        key = parts[0]
        results = defaultdict(list)
        for etype in srv.ms.mod_parsers:
            data = srv.ms.get_data(etype)
            if not data:
                continue
            for eid, raw in data.items():
                if _data_contains_string(raw, key):
                    results[etype].append(
                        {"type": etype, "id": eid, "name": srv.ms.localize(eid)}
                    )
        return dict(results) if results else {"message": f"No references found for '{key}'"}

    # ---- analytical: tech tree --------------------------------------------
    def _tech_tree(self, parts):
        """GET /tech-tree/<tech_id>  - prerequisite chain + everything unlocked."""
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide a tech ID, e.g. /tech-tree/nuclear_fission")
        tid = parts[0]
        techs = srv.ms.get_data("Technologies")
        if not techs:
            raise srv.DataNotLoaded("Technologies")
        if tid not in techs:
            raise srv.NotFound(tid)

        # Recursive prerequisites
        prereqs = []
        visited = set()
        self._collect_prereqs(tid, techs, prereqs, visited)

        # Everything unlocked by this tech
        unlocked = self._find_unlocked_by_tech(tid)

        td = srv.get_entity_data(techs[tid])
        era_str = srv.get_field(td, "era", "era_0")
        return {
            "type": "Technologies",
            "id": tid,
            "name": srv.ms.localize(tid),
            "era": int(era_str.split("_")[-1]),
            "prerequisites": prereqs,
            "unlocks": unlocked,
        }

    def _collect_prereqs(self, tid, techs, prereqs, visited):
        """Recursively collect all prerequisite technologies."""
        srv = server_state()
        if tid in visited:
            return
        visited.add(tid)
        raw = techs.get(tid)
        if not raw:
            return
        td = srv.get_entity_data(raw)
        parent_techs = srv.get_field(td, "unlocking_technologies")
        if parent_techs and isinstance(parent_techs, list):
            for pt in parent_techs:
                if pt not in visited:
                    self._collect_prereqs(pt, techs, prereqs, visited)
                    era_str = "era_0"
                    pt_raw = techs.get(pt)
                    if pt_raw:
                        pt_td = srv.get_entity_data(pt_raw)
                        era_str = srv.get_field(pt_td, "era", "era_0")
                    prereqs.append({
                        "type": "Technologies",
                        "id": pt,
                        "name": srv.ms.localize(pt),
                        "era": int(era_str.split("_")[-1]),
                    })

    def _find_unlocked_by_tech(self, tid):
        """Find all entities unlocked by a technology across all entity types.

        Each entry carries a `type` field matching its mod_parsers key, so the
        centralized `?annotate=<name>` post-processor in route() picks them up
        automatically (e.g. PM entries gain balance flags when the request
        includes ?annotate=balance).
        """
        srv = server_state()
        unlocked = defaultdict(list)
        for etype in srv.ms.mod_parsers:
            data = srv.ms.get_data(etype)
            if not data:
                continue
            for eid, raw in data.items():
                ed = srv.get_entity_data(raw)
                ut = srv.get_field(ed, "unlocking_technologies")
                if ut and isinstance(ut, list) and tid in ut:
                    unlocked[etype].append(
                        {"type": etype, "id": eid, "name": srv.ms.localize(eid)}
                    )
        return dict(unlocked)

    # ---- analytical: modifier search --------------------------------------
    def _modifier_search(self, params):
        """GET /modifier-search?q=<pattern>  - find modifier field names across entities."""
        srv = server_state()
        query = params.get("q", [""])[0].lower()
        if not query:
            raise srv.BadRequest("Provide ?q=search_pattern")
        limit = int(params.get("limit", ["100"])[0])

        results = []
        seen = set()
        # Registered modifier types (mod + vanilla), so boolean grants
        # (`country_x_bool = yes`) are indexed too (#336).
        modifier_types = set((srv.ms.get_data("Modifier Types") or {}).keys())
        for etype in srv.ms.mod_parsers:
            data = srv.ms.get_data(etype)
            if not data:
                continue
            for eid, raw in data.items():
                modifiers = _extract_modifier_fields(raw, bool_keys=modifier_types)
                matching = {k: v for k, v in modifiers.items() if query in k.lower()}
                if matching:
                    results.append({
                        "type": etype,
                        "id": eid,
                        "name": srv.ms.localize(eid),
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
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide a tech ID, e.g. /unlocked-by/nuclear_fission")
        tid = parts[0]
        techs = srv.ms.get_data("Technologies")
        if techs and tid not in techs:
            raise srv.NotFound(tid)
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
        srv = server_state()
        force = (params.get("refresh") or ["false"])[0].lower() == "true"
        source = (params.get("source") or ["mod"])[0].lower()
        era_param = params.get("era", [None])[0]
        eras_param = params.get("eras", [None])[0]
        summary_only = (params.get("summary") or ["false"])[0].lower() == "true"

        # Build (and cache) the full mod-only index. Vanilla side is opt-in
        # via ?source=vanilla|all and rebuilds each request — vanilla data
        # rarely changes during a session so we don't cache it separately.
        if force or srv._tech_unlocks_index_cache is None:
            srv._tech_unlocks_index_cache = tech_unlocks_lib.build_tech_unlock_index(
                Path(srv.mod_path),
            )

        # Combine mod + vanilla as requested.
        index: dict[str, dict] = {}
        if source in ("mod", "all"):
            for tid, rec in srv._tech_unlocks_index_cache.items():
                index[tid] = self._copy_unlocks_record(rec)
        if source in ("vanilla", "all"):
            vanilla_root = Path(srv.base_game_path) / "game" / "common"
            vanilla_idx = tech_unlocks_lib.build_tech_unlock_index(
                Path(srv.mod_path),
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
            techs = srv.ms.get_data("Technologies") or {}
            kept = {}
            for tid, rec in index.items():
                td = techs.get(tid)
                if td is None:
                    continue
                era_str = srv.get_field(srv.get_entity_data(td), "era", "era_0")
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
        # Copy the entry dicts too, not just the lists: `?annotate=` mutates
        # entries in place, and a shallow copy would stamp annotator fields
        # onto `_tech_unlocks_index_cache` for every later request.
        return {
            "by_type": {k: [dict(e) for e in v] for k, v in rec["by_type"].items()},
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
        srv = server_state()
        events = srv.ms.get_data("Events")
        if not events:
            raise srv.DataNotLoaded("Events")

        fmt = params.get("format", ["json"])[0]

        if parts and parts[0] == "issues":
            return self._event_balance_issues(params, fmt)

        if parts:
            eid = parts[0]
            if eid not in events:
                raise srv.NotFound(eid)
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
            ids = _event_ids_from_mod_file(file_param)
        else:
            raise srv.BadRequest(
                "Provide an event id (e.g. /event-balance/banking_cycle_events.10), "
                "or ?ids=, ?prefix=, ?file="
            )

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
        srv = server_state()
        ed = srv.get_entity_data(raw)
        info = {
            "id": eid,
            "name": srv.ms.localize(eid + ".t"),
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
        srv = server_state()
        opt_data = srv._flatten_entity_data(opt) if not isinstance(opt, dict) else opt
        raw_name = srv.get_field(opt_data, "name")
        name_keys = _option_name_keys(raw_name)
        name_key = name_keys[0] if name_keys else None
        default_opt = srv.get_field(opt_data, "default_option")
        ai_chance_block = srv.get_field(opt_data, "ai_chance")
        ai_base = None
        if isinstance(ai_chance_block, dict):
            ai_base = srv.get_field(ai_chance_block, "base")
            if ai_base is not None:
                ai_base = _try_float(ai_base) if _try_float(ai_base) is not None else ai_base
        effects = []
        _walk_event_effects(opt_data, [], effects)
        polarity_totals = _summarize_polarity(effects)
        out = {
            "name_key": name_key,
            "name": srv.ms.localize(name_key) if name_key else None,
            "default_option": default_opt == "yes",
            "ai_chance_base": ai_base,
            "effects": effects,
            "polarity_totals": polarity_totals,
        }
        if name_keys and not isinstance(raw_name, str):
            # Triggered names (`name = { trigger = {...} text = KEY }`, once
            # per case; the first whose trigger holds is shown): every case,
            # in source order, even a single one. `name_key` is the first.
            out["name_variants"] = [{"key": k, "name": srv.ms.localize(k)} for k in name_keys]
        return out

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
        srv = server_state()
        events = srv.ms.get_data("Events")
        if not events:
            raise srv.DataNotLoaded("Events")

        mode = params.get("mode", ["strict"])[0]
        try:
            threshold = int(params.get("threshold", ["2"])[0])
        except ValueError:
            threshold = 2

        prefix = params.get("prefix", [None])[0]
        file_param = params.get("file", [None])[0]

        if file_param:
            ids = [e for e in _event_ids_from_mod_file(file_param) if e in events]
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

    def _scripted_helpers(self, parts, params):
        """GET /scripted-helpers/unresolved — dangling scripted-helper calls.

        The inverse of the callers index `/scripted-effects/<id>` builds: every
        `name = yes` / `name = { ... }` call site in the mod whose callee is
        defined by neither vanilla nor the mod, so the engine silently ignores
        the line (#288). Backed by `effect_trigger_validity_audit`, which reads
        the files rather than the parse, so it sees call sites in every
        script-bearing directory — including the ones no endpoint indexes.

        `?include_reviewed=true` also returns sites suppressed with an inline
        `# REVIEWED YYYY-MM-DD: rationale` comment."""
        srv = server_state()
        if not parts or parts[0] != "unresolved":
            raise srv.BadRequest("Use /scripted-helpers/unresolved")
        include_reviewed = (
            (params.get("include_reviewed") or ["false"])[0].lower() == "true"
        )
        rows = effect_trigger_validity_audit.unresolved_helper_calls(srv.mod_path)
        if not include_reviewed:
            rows = [r for r in rows if not r.get("reviewed")]
        return {
            "count": len(rows),
            "include_reviewed": include_reviewed,
            "unresolved_helper_calls": rows,
        }

    def _script_args(self, parts, params):
        """GET /script-args[/<helper>] — argument checks for scripted effect
        and trigger calls (#732), from script_argument_audit's index.

        Bare: every flagged call (`?include_reviewed=true` adds the ones
        suppressed with `# REVIEWED YYYY-MM-DD (script_argument): ...`).
        With a helper: its `$X$` names and every call that reaches it,
        dispatcher calls included, each with the `unknown` arguments it passes
        and the `missing` ones it doesn't. Vanilla helpers are indexed only
        when the game files are on disk (`vanilla_indexed`)."""
        srv = server_state()
        result = _get_script_args_result()
        if parts:
            info = script_argument_audit.helper_callers(result, parts[0])
            if info is None:
                raise srv.NotFound(parts[0])
            return info
        include_reviewed = (
            (params.get("include_reviewed") or ["false"])[0].lower() == "true"
        )
        flags = [f for f in result.flags if include_reviewed or not f.exemption]
        return {
            "vanilla_indexed": result.vanilla_indexed,
            "helpers_indexed": result.helpers_indexed,
            "calls_checked": result.calls_checked,
            "include_reviewed": include_reviewed,
            "count": len(flags),
            "flags": [script_argument_audit.flag_dict(f) for f in flags],
            "stale_tags": [{"file": t.file, "line": t.line} for t in result.stale],
        }

    def _loc_accessors(self, parts, params):
        """GET /loc-accessors[/<Type>] — which accessors vanilla loc and GUI
        chain on a data type (#1246), from loc_accessor_usage's index.

        Bare: every type with its accessor and use counts. With a type
        (`PoliticalLobby`, `political_lobby`, …): each accessor with `uses`,
        per-context counts, the catalog's `returns` type (null when
        localization_accessor_audit doesn't list it) and `examples`, plus the
        `scope_accessor` that builds the type from `SCOPE`. `?context=` keeps
        one context's uses, `?min_uses=` drops rarer accessors, `?examples=`
        caps the examples per accessor. `gui_scanned` says whether vanilla
        `.gui` files were on disk."""
        srv = server_state()
        def one(key):
            return (params.get(key) or [None])[0] or None

        def number(key, default, low, high):
            raw = one(key)
            if raw is None:
                return default
            try:
                return min(max(int(raw), low), high)
            except ValueError:
                raise srv.BadRequest(f"{key} must be an integer, not {raw!r}")

        index, catalog = _get_loc_accessor_index()
        if not parts:
            return loc_accessor_usage.list_types(index)
        if len(parts) > 1:
            raise srv.NotFound("/loc-accessors/" + "/".join(parts))
        context = one("context")
        seen = loc_accessor_usage.contexts_seen(index)
        if context is not None and context not in seen:
            raise srv.BadRequest(f"unknown context {context!r}; use one of " + ", ".join(seen))
        out = loc_accessor_usage.lookup(
            index, catalog, parts[0], context=context,
            examples=number("examples", loc_accessor_usage.DEFAULT_EXAMPLES, 0,
                            loc_accessor_usage.MAX_EXAMPLES),
            min_uses=number("min_uses", 1, 1, 10 ** 9))
        if out is None:
            raise srv.NotFound(parts[0], did_you_mean=loc_accessor_usage.suggest(index, catalog, parts[0]))
        return out

    def _variable_usage(self, parts, params):
        """GET /variable-usage[/<name>] — how each mod site uses a variable or
        variable list (#973), from variable_usage's index."""
        srv = server_state()
        def one(key):
            return (params.get(key) or [None])[0] or None
        kind, store = one("kind"), one("store")
        if kind not in (None, "var", "list"):
            raise srv.BadRequest(f"kind must be var or list, not {kind!r}")
        if store not in (None, "scope", "global", "local"):
            raise srv.BadRequest(f"store must be scope, global or local, not {store!r}")
        index = _get_variable_usage_index()
        if not parts:
            return variable_usage.names(index, one("prefix"), kind)
        if len(parts) > 1:
            raise srv.NotFound("/variable-usage/" + "/".join(parts))
        patterns = (one("patterns") or "true").lower() != "false"
        out = variable_usage.usage(index, parts[0], kind, store, one("unfiltered_by"),
                                   patterns)
        if out is None:
            raise srv.NotFound(parts[0])
        return out

    # ---- PM combination employment (#990) ----------------------------------
    def _pm_employment(self, parts, params):
        """GET /pm-employment/<building>[?select=&bucket=&limit=],
        GET /pm-employment?select=<pm|glob>[,...]"""
        srv = server_state()
        buildings = srv.ms.get_data("Buildings")
        if not buildings:
            raise srv.DataNotLoaded("Buildings")
        pmg_data = srv.ms.get_data("PM Groups") or {}
        pm_data = srv.ms.get_data("PMs") or {}
        select = [s.strip() for v in params.get("select", []) for s in v.split(",") if s.strip()]
        bucket_args = [b.strip() for v in params.get("bucket", []) for b in v.split(",") if b.strip()]
        if not bucket_args or "all" in bucket_args:
            buckets = pm_employment_audit.BUCKETS
        else:
            unknown = [b for b in bucket_args if b not in pm_employment_audit.BUCKETS]
            if unknown:
                raise srv.BadRequest(f"unknown bucket {unknown[0]!r}; use "
                                 + ", ".join(pm_employment_audit.BUCKETS) + " or all")
            buckets = tuple(b for b in pm_employment_audit.BUCKETS if b in bucket_args)
        limit_arg = (params.get("limit") or ["50"])[0]
        try:
            limit = int(limit_arg)
        except ValueError:
            raise srv.BadRequest(f"limit must be an integer, not {limit_arg!r}")
        if limit < 0:
            raise srv.BadRequest("limit must be 0 (no limit) or more")
        if len(parts) > 1:
            raise srv.NotFound("/pm-employment/" + "/".join(parts))
        if not parts:
            if not select:
                raise srv.BadRequest("Pass a building (/pm-employment/building_x) "
                                 "or ?select=<pm or glob>[,...]")
            return pm_employment_audit.employment_by_select(
                select, buildings, pmg_data, pm_data, buckets, limit)
        out = pm_employment_audit.employment_combinations(
            parts[0], buildings, pmg_data, pm_data, select, buckets, limit)
        if out is None:
            raise srv.NotFound(parts[0])
        if select and not out["select_matched"]:
            raise srv.BadRequest(f"no production method of {parts[0]} matches "
                             f"select={','.join(select)}")
        return out

    # ---- reverse modifier-grant lookup ------------------------------------
    def _modifier_grants(self, parts, params):
        """GET /modifier-grants/<modifier_name>?scope=both&limit=200
                 &entity_types=Laws,PMs&effective=true

        Enumerate every entity that GRANTS the modifier, across every
        `common/` entity directory (laws, techs, principles, amendments,
        decrees, buildings, static modifiers, country ranks, institutions,
        company types, interest group traits, production methods, character
        traits, power bloc identities, treaty articles, ...), returning
        {entity_type, entity_id, origin, file, line, value, block} per site.
        `entity_types_scanned` and `origins_scanned` in the response say what
        was covered. Complements /engine-docs/usage, which only finds
        effect/trigger call sites. scope: mod | vanilla | both.
        `entity_types` (comma-separated names or directory names) restricts the
        walk. `total` is the true number of sites; `limit` only caps the rows.

        Note: under scope=both a modifier the mod INJECTs into a vanilla entity
        is reported twice (vanilla original + mod patch) for the same
        entity_id; `origin` disambiguates. A vanilla row the mod REPLACEs (the
        entity, or the whole file by shipping the same path) is marked
        `"shadowed_by": "mod"`; `effective=true` drops those rows. Use
        scope=mod for the mod's own additions only."""
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide a modifier name, e.g. "
                             "/modifier-grants/state_homeland_creation_threshold_add")
        scope = params.get("scope", ["both"])[0]
        try:
            limit = int(params.get("limit", ["200"])[0])
        except ValueError:
            limit = 200
        entity_types = [t.strip()
                        for raw in params.get("entity_types", [])
                        for t in raw.split(",") if t.strip()] or None
        effective = params.get("effective", ["false"])[0].lower() in ("1", "true", "yes")
        result = srv._find_modifier_grants(parts[0], scope=scope, limit=limit,
                                       entity_types=entity_types,
                                       effective=effective)
        # The finder rejects a malformed name / scope / entity type in-band;
        # that's a 400. Pass the whole payload through so the body keeps `name`
        # and the empty `grants` list callers already parse. (#254)
        if isinstance(result, dict) and "error" in result:
            raise srv._EndpointError(result, 400)
        return result

    def _on_action_callers(self, parts):
        """GET /on-action-callers/<scripted_effect | event_id | on_action> (#333)

        The mod on-actions that reach the scripted effect, the event or the
        on-action, through any chain of scripted effects and events (an
        event's immediate, after or option). `callers` rows: {on_action, file,
        line, via (effect | trigger_event | events | random_events |
        first_valid | on_actions), through (the effects and events between the
        on-action and the target), guards (one entry per hop, the on-action's
        own call first), guards_complete, other_routes, through_option, hops
        (each call site: in, kind, file, line, path, guards, via, other_sites),
        roots (the on-actions nothing in the mod lists that it hangs from) and
        engine_hooks (those of them the engine fires from code; null when the
        engine docs are not loaded)}.

        A row is the shortest route from that on-action call site, not the
        only one. `guards_complete` is false when a link on it calls the next
        from another site too, or reaches the target through another link as
        well (`other_routes` names them): the guards shown are then not the
        whole condition. `through_option` marks a route that runs through an
        event option. An effect a caller passes by name (`helper = { EFFECT =
        x }`, run as `$EFFECT$ = yes`) is followed through the helper;
        `passed_as_parameter` lists those call sites.

        It follows on-actions, scripted effects and events only. Every other
        entity the graph knows calls the target or a link of a chain (a
        journal entry's pulse, a scripted button, a decision, ...) is in
        `not_followed` ({kind, id, file, line, path, sites, through}), counted
        in `not_followed_count` / `not_followed_kinds`; `unreached` lists the
        links nothing in the mod calls or fires. So `count: 0` means "nothing
        calls it" only when those and `passed_as_parameter` are empty:
        `summary` says which.

        Built from event_context_audit's graph on each call (several seconds,
        as /event-dispatch), console harness files included. Mod script only."""
        srv = server_state()
        import on_action_index

        if not parts:
            raise srv.BadRequest("usage: /on-action-callers/<scripted_effect|event_id|on_action>")
        hooks = srv.engine_docs.get("on-actions") or []
        code = {e.get("name") for e in hooks if e.get("from_code")} if hooks else None
        out = on_action_index.callers(srv.mod_path, parts[0], code)
        if out is None:
            raise srv.NotFound(parts[0])
        return out

    # ---- technology effects -----------------------------------------------
    def _technology_effects(self, parts):
        """GET /technology-effects/<tech_id>
        Returns ALL effects of a technology: direct modifiers, unlocked PMs,
        buildings, combat units, laws, institutions, etc.
        """
        srv = server_state()
        if not parts:
            raise srv.BadRequest("Provide a tech ID, e.g. /technology-effects/nuclear_fission")
        tid = parts[0]
        techs = srv.ms.get_data("Technologies")
        if not techs:
            raise srv.DataNotLoaded("Technologies")
        if tid not in techs:
            raise srv.NotFound(tid)

        td = srv.get_entity_data(techs[tid])
        era_str = srv.get_field(td, "era", "era_0")
        info: dict = {
            "type": "Technologies",
            "id": tid,
            "name": srv.ms.localize(tid),
            "era": int(era_str.split("_")[-1]),
            "description": srv.ms.get_description(tid) or "",
        }

        # Direct modifiers from the tech definition
        modifier = srv.get_field(td, "modifier")
        if modifier and isinstance(modifier, dict):
            info["direct_modifiers"] = {
                k: v[1] if isinstance(v, tuple) else v
                for k, v in modifier.items()
            }
        else:
            info["direct_modifiers"] = {}

        # Prerequisites
        prereqs = srv.get_field(td, "unlocking_technologies")
        if prereqs and isinstance(prereqs, list):
            info["prerequisites"] = [
                {"type": "Technologies", "id": pt, "name": srv.ms.localize(pt)}
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
            data = srv.ms.get_data(etype)
            if not data:
                continue
            found = []
            for eid, raw in data.items():
                ed = srv.get_entity_data(raw)
                ut = srv.get_field(ed, "unlocking_technologies")
                if ut and isinstance(ut, list) and tid in ut:
                    entry = {"type": etype, "id": eid, "name": srv.ms.localize(eid)}
                    # For PMs, include modifier details
                    if etype == "PMs":
                        for mod_key in ("building_modifiers", "country_modifiers", "state_modifiers"):
                            mod_data = srv.get_field(ed, mod_key)
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
            other_td = srv.get_entity_data(other_raw)
            other_prereqs = srv.get_field(other_td, "unlocking_technologies")
            if other_prereqs and isinstance(other_prereqs, list) and tid in other_prereqs:
                other_era = srv.get_field(other_td, "era", "era_0")
                dependents.append({
                    "type": "Technologies",
                    "id": other_tid,
                    "name": srv.ms.localize(other_tid),
                    "era": int(other_era.split("_")[-1]),
                })
        if dependents:
            info["dependent_technologies"] = dependents

        return info

    def _unlocalized(self, params):
        """GET /unlocalized?type=<EntityType>&mod_only=true
        Find entities with missing localization keys.
        - type:     filter to one entity type (e.g. "Modifiers")
        - mod_only: if "true" (default), skip entities that exist in vanilla
        """
        srv = server_state()
        type_filter = params.get("type", [""])[0]
        mod_only = params.get("mod_only", ["true"])[0].lower() != "false"

        results: dict[str, list] = {}
        total = 0

        for etype, pattern in self._LOC_SPECS:
            if type_filter and etype != type_filter:
                continue
            data = srv.ms.get_data(etype)
            if not data:
                continue

            base_data = (
                srv.ms.base_parsers[etype].data
                if etype in srv.ms.base_parsers
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
                        if not srv.ms.has_localization(eid + suffix):
                            missing_keys.append(eid + suffix)
                    # Check options by parsing the event data
                    ed = srv.get_entity_data(data[eid])
                    if isinstance(ed, dict):
                        options = ed.get("option", [])
                        if isinstance(options, dict):
                            options = [options]
                        if isinstance(options, list):
                            for opt in options:
                                if isinstance(opt, dict):
                                    name = srv.get_field(opt, "name")
                                    if name and not srv.ms.has_localization(name):
                                        missing_keys.append(name)
                elif pattern == "self+desc":
                    if not srv.ms.has_localization(eid):
                        missing_keys.append(eid)
                    if not srv.ms.has_localization(eid + "_desc"):
                        missing_keys.append(eid + "_desc")
                else:  # "self"
                    if not srv.ms.has_localization(eid):
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
