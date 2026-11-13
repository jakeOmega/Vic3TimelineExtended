"""The validation and mod-hygiene routes: GET /validate/<check>,
/external-mod-overlap[/state], /duplicate-images, /placeholder-icons,
/auto-generated, /event-magnitude-audit, /event-dispatch/<event_id> and
/event-context-audit, with the helpers only they use. Moved out of
mod_state_server.py unchanged (#1537).

A route module holds code only (server/__init__.py says why): the state these
routes read stays in mod_state_server and is read as `srv.<name>` through
`server_state()` at call time. mod_state_server re-exports every name below.
"""
import fnmatch
import os
import re
import subprocess
from typing import Optional

import external_mod_overlap
import external_mod_state
from mod_state import iter_loc_lines, iter_script_files

from server import server_state


# ---------------------------------------------------------------------------
# Duplicate-image detection
# ---------------------------------------------------------------------------
# Entity types where vanilla holds the convention "one image per entity" — any
# image reuse inside the mod (or between mod and vanilla) is a likely placeholder
# that was never replaced. Each entry: (entity_type, field_name).
#
# Principles are clustered per principle group, not per tier: vanilla gives a
# group one icon and every tier shares it.
#
# Permissive types (events, journal entries, production methods, PM groups,
# static modifiers, messages, ships, diplomatic plays, religions) are
# deliberately omitted — vanilla shares images across many entities of those
# types by design. /duplicate-images doesn't scan them; /placeholder-icons
# checks them for paths that resolve nowhere (_SHARED_BY_DESIGN_ICON_FIELDS).
_IMAGE_FIELDS_BY_TYPE: list[tuple[str, str]] = [
    ("Buildings",               "icon"),
    ("Goods",                   "texture"),
    ("Decrees",                 "texture"),
    ("Technologies",            "texture"),
    ("Interest Groups",         "texture"),
    ("Laws",                    "icon"),
    ("Principles",              "icon"),
    ("Ideologies",              "icon"),
    ("Mobilization Options",    "texture"),
    ("Institutions",            "icon"),
    ("Character Traits",        "texture"),
    ("Treaty Articles",         "icon"),
    ("Diplomatic Actions",      "texture"),
    ("Company Types",           "icon"),
    ("Interest Group Traits",   "icon"),
    ("Harvest Condition Types", "icon"),
    ("Power Bloc Identities",   "icon"),
    ("Parties",                 "icon"),
]


# YAML file → canonical entity-type-name mapping. The YAML is keyed by lowercase
# slug for ergonomic editing (`interest_groups`, `treaty_articles`); the
# in-memory map uses the canonical names.
_ALLOWLIST_TYPE_SLUGS: dict[str, str] = {
    entity_type.lower().replace(" ", "_"): entity_type
    for entity_type, _ in _IMAGE_FIELDS_BY_TYPE
}


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
    srv = server_state()
    target = path or srv._IMAGE_ALLOWLIST_PATH
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
    origin = _image_origin(rel_path)
    return origin[1] if origin else None


def _image_origin(rel_path: str) -> tuple[str, str] | None:
    """("mod" | "vanilla", absolute path) for a Paradox-relative image path,
    the mod's file first, as the engine overlays it. None when neither has it."""
    srv = server_state()
    if not rel_path:
        return None
    for origin, root in (("mod", srv.mod_path),
                         ("vanilla", os.path.join(srv.base_game_path, "game"))):
        candidate = os.path.join(root, rel_path)
        if os.path.isfile(candidate):
            return origin, candidate
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


def _entity_image(raw, field: str) -> str | None:
    """An entity's `field` as a path, without the quotes the parser keeps (so
    it matches the unquoted paths in the YAML allowlist), or None.

    A party's icon is a block, `icon = { default = "/gfx/…" }`: its `default`
    is the path. A leading `/` is dropped, as the engine reads the path from
    the game root either way; joined as is, it would resolve nowhere."""
    srv = server_state()
    data = srv.get_entity_data(raw)
    if not isinstance(data, dict):
        return None
    image = srv.get_field(data, field)
    if isinstance(image, dict):
        image = srv.get_field(image, "default")
    if not isinstance(image, str):
        return None
    if len(image) >= 2 and image[0] == image[-1] and image[0] in ('"', "'"):
        image = image[1:-1]
    return image.lstrip("/") or None


def _principle_group_of() -> dict[str, str]:
    """principle id → the id of the principle group whose `levels` lists it.

    The mod's groups first, then vanilla's for a tier no mod group lists: a
    group the mod REPLACEs with renamed tiers (sacred civics' `_mod`
    variants) leaves the vanilla tiers in no group, still on its icon."""
    srv = server_state()
    out: dict[str, str] = {}
    for parsers in (srv.ms.mod_parsers, srv.ms.base_parsers):
        parser = parsers.get("Principle Groups")
        for gid, raw in ((parser.data if parser else None) or {}).items():
            levels = srv.get_field(srv.get_entity_data(raw), "levels")
            if isinstance(levels, list):
                for pid in levels:
                    if isinstance(pid, str):
                        out.setdefault(pid, gid)
    return out


def _image_entity_uses(entity_type: str, field: str) -> list[dict]:
    """Every entity of one type that sets `field`, as
    {"key", "image", "mod_side", "members"}.

    `mod_side` is true when the mod added the entity or changed the field from
    vanilla's value. Principles collapse to their group: `key` is the group,
    `members` the tiers on that image, and the group's image counts as
    mod-side only when a mod-side tier uses it and no vanilla tier of the
    group does — a tier IV the mod adds on its group's vanilla icon follows
    vanilla's convention, it isn't a placeholder. For every other type
    `members` is [key]."""
    srv = server_state()
    if not srv.ms or entity_type not in srv.ms.mod_parsers:
        return []
    full = srv.ms.mod_parsers[entity_type].data or {}
    base = (srv.ms.base_parsers[entity_type].data
            if entity_type in srv.ms.base_parsers else {}) or {}
    group_of = _principle_group_of() if entity_type == "Principles" else {}
    vanilla_group_images: dict[str, set[str]] = {}
    if group_of:
        for pid, raw in base.items():
            image = _entity_image(raw, field)
            if image and pid in group_of:
                vanilla_group_images.setdefault(group_of[pid], set()).add(image)

    records: dict[tuple[str, str], dict] = {}
    for entity_id, raw in full.items():
        image = _entity_image(raw, field)
        if not image:
            continue
        vanilla_raw = base.get(entity_id)
        mod_side = vanilla_raw is None or _entity_image(vanilla_raw, field) != image
        key = group_of.get(entity_id, entity_id)
        if group_of and image in vanilla_group_images.get(key, ()):
            mod_side = False
        rec = records.setdefault((key, image), {
            "key": key, "image": image, "mod_side": False, "members": []})
        rec["members"].append(entity_id)
        rec["mod_side"] = rec["mod_side"] or mod_side
    return list(records.values())


def _collect_image_uses(entity_type: str, field: str) -> tuple[dict[str, list[str]], set[str]]:
    """Return (image_path → [entity_id, …], set_of_mod_side_ids) for one type.
    Principles are listed by group (see _image_entity_uses)."""
    uses: dict[str, list[str]] = {}
    mod_side: set[str] = set()
    for rec in _image_entity_uses(entity_type, field):
        uses.setdefault(rec["image"], []).append(rec["key"])
        if rec["mod_side"]:
            mod_side.add(rec["key"])
    return uses, mod_side


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
      include_allowlisted — emit the `allowlisted` array.
      hasher              — callable(rel_path) → hash string. Defaults to
                            `_image_content_hash`. Tests inject a fake hasher
                            so they don't need real .dds files on disk.

    Cluster shape:
      {"entity_type": str,
       "images":      [sorted paths, len 1 if pure path-dupe else >1],
       "entities":    [sorted entity ids],
       "kind":        "path" | "content",
       "reason":      <only present for allowlisted clusters>}

    `stale_allowlist` lists the allowlist entries of the scanned types that
    match no cluster, vanilla-only ones included: an entry whose entity list
    went out of date hides nothing and should be deleted or rewritten.
    """
    if allowlist is None:
        allowlist = _load_image_allowlist()
    if hasher is None:
        hasher = _image_content_hash

    scanned_types: list[str] = []
    flagged: list[dict] = []
    allowlisted: list[dict] = []
    matched: set[tuple[str, tuple]] = set()

    for entity_type, field in _IMAGE_FIELDS_BY_TYPE:
        if types is not None and entity_type not in types:
            continue
        scanned_types.append(entity_type)
        path_to_entities, mod_only_ids = _collect_image_uses(entity_type, field)
        # Hash each unique path once.
        path_to_hash = {p: hasher(p) for p in path_to_entities}

        # Group entities by content hash.
        hash_to_paths: dict[str, set[str]] = {}
        hash_to_entities: dict[str, set[str]] = {}
        for path, ents in path_to_entities.items():
            h = path_to_hash[path]
            hash_to_paths.setdefault(h, set()).add(path)
            hash_to_entities.setdefault(h, set()).update(ents)

        type_allowlist = allowlist.get(entity_type, {})
        for h, ents in hash_to_entities.items():
            if len(ents) < 2:
                continue
            paths = hash_to_paths[h]
            allow_key = (frozenset(paths), frozenset(ents))
            if allow_key in type_allowlist:
                matched.add((entity_type, allow_key))
            if not include_vanilla and not (ents & mod_only_ids):
                continue
            kind = "content" if len(paths) > 1 else "path"
            cluster = {
                "entity_type": entity_type,
                "images": sorted(paths),
                "entities": sorted(ents),
                "kind": kind,
            }
            if allow_key in type_allowlist:
                cluster["reason"] = type_allowlist[allow_key]
                allowlisted.append(cluster)
            else:
                flagged.append(cluster)

    flagged.sort(key=lambda c: (c["entity_type"], c["images"]))
    allowlisted.sort(key=lambda c: (c["entity_type"], c["images"]))
    stale = sorted(
        ({"entity_type": entity_type, "images": sorted(images),
          "entities": sorted(ents), "reason": reason}
         for entity_type in scanned_types
         for (images, ents), reason in allowlist.get(entity_type, {}).items()
         if (entity_type, (images, ents)) not in matched),
        key=lambda c: (c["entity_type"], c["images"]),
    )

    report: dict = {
        "summary": {
            "flagged": len(flagged),
            "allowlisted": len(allowlisted),
            "stale_allowlist": len(stale),
            "scanned_entity_types": scanned_types,
        },
        "flagged": flagged,
        "stale_allowlist": stale,
    }
    if include_allowlisted:
        report["allowlisted"] = allowlisted
    return report


def _render_duplicate_images_text(report: dict, *, include_allowlisted: bool = False) -> str:
    """Render the duplicate-image report as plain text for ?format=text."""
    summary = report.get("summary", {})
    out = [
        f"Duplicate images: {summary.get('flagged', 0)} flagged, "
        f"{summary.get('allowlisted', 0)} allowlisted, "
        f"{summary.get('stale_allowlist', 0)} stale allowlist entries",
        f"Scanned types: {', '.join(summary.get('scanned_entity_types', []))}",
        "",
    ]

    def _format_cluster(c: dict) -> list[str]:
        kind_tag = {"content": " [CONTENT]", "path": " [PATH]"}.get(c.get("kind"), "")
        lines = [f"  [{c['entity_type']}]{kind_tag}"]
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
    stale = report.get("stale_allowlist", [])
    if stale:
        out.append("")
        out.append(f"STALE ALLOWLIST ENTRIES ({len(stale)}), matching no cluster:")
        for c in stale:
            out.extend(_format_cluster(c))
            out.append(f"      reason: {c.get('reason') or '(no reason given)'}")
    if include_allowlisted and report.get("allowlisted"):
        out.append("")
        out.append(f"ALLOWLISTED ({len(report['allowlisted'])}):")
        for c in report["allowlisted"]:
            reason = c.get("reason") or "(no reason given)"
            out.extend(_format_cluster(c))
            out.append(f"      reason: {reason}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Placeholder-icon classification (/placeholder-icons)
# ---------------------------------------------------------------------------
# Image fields of the types (and the `background` fields) where vanilla shares
# art by design. They are classified only under ?include_shared_by_design=true;
# a path in one that resolves nowhere is reported as `missing` either way.
_SHARED_BY_DESIGN_ICON_FIELDS: list[tuple[str, str]] = [
    ("Battle Conditions",          "icon"),
    ("Buildings",                  "background"),
    ("Character Interactions",     "icon"),
    ("Combat Unit Groups",         "icon"),
    ("Company Types",              "background"),
    ("Cultures",                   "seal_and_signature_texture"),
    ("Diplomatic Plays",           "texture"),
    ("Events",                     "icon"),
    ("Game Concepts",              "texture"),
    ("Harvest Condition Types",    "map_texture"),
    ("Institutions",               "background_texture"),
    ("Journal Entries",            "icon"),
    ("Messages",                   "texture"),
    ("Journal Entry Groups",       "illustration"),
    ("Mobilization Option Groups", "background"),  # `icon` until 1.15
    ("Modifiers",                  "icon"),
    ("PM Groups",                  "texture"),
    ("PMs",                        "texture"),
    ("Pop Types",                  "texture"),
    ("Power Bloc Identities",      "background"),
    ("Principles",                 "background"),
    ("Religions",                  "icon"),
    ("Ship Groups",                "icon"),
    ("Ship Modification Slots",    "icon"),
    ("Ship Modifications",         "icon"),
    ("Ship Types",                 "icon"),
    ("Ship Types",                 "profile_texture"),
]


# `shared_with` names at most this many sharers (`shared_count` has the total):
# a vanilla modifier icon has over a thousand.
_SHARED_WITH_LIMIT = 20


# Report order, most actionable first.
_PLACEHOLDER_STATUSES = ("missing", "generated_standin", "borrowed_vanilla",
                         "shared_mod", "unique_mod", "unresolved")


_TOP_LEVEL_OPENER_RE = re.compile(
    r"^(?:INJECT:|REPLACE:|INJECT_OR_CREATE:|REPLACE_OR_CREATE:)?([\w.\-]+)\s*=\s*\{")


def _load_standin_patterns(path: str | None = None) -> list[str]:
    """The `pattern:` globs of common/_meta/generated_standin_icons.yml, or []."""
    srv = server_state()
    target = path or srv._STANDIN_PATTERNS_PATH
    if not os.path.isfile(target):
        return []
    try:
        import yaml
        with open(target, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or []
    except Exception as e:
        print(f"WARNING: failed to load stand-in icon patterns {target}: {e}")
        return []
    if not isinstance(raw, list):
        return []
    return [str(e["pattern"]) for e in raw
            if isinstance(e, dict) and e.get("pattern")]


def _icon_definition_sites(entity_type: str, field: str) -> dict[str, tuple[str, int]]:
    """entity id → (repo-relative file, line) of the `field = …` line in its
    mod top-level block, or of the block's opener when no mod block sets the
    field. When several blocks set it (a definition and an INJECT), the last
    in load order wins, as it does in game."""
    srv = server_state()
    directory = srv.mod_paths.get(entity_type)
    if not directory or not os.path.isdir(directory):
        return {}
    field_re = re.compile(rf"^\s*{re.escape(field)}\s*=")
    field_sites: dict[str, tuple[str, int]] = {}
    opener_sites: dict[str, tuple[str, int]] = {}
    for path in iter_script_files(directory):
        rel = os.path.relpath(path, srv.mod_path)
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue
        depth = 0
        current = None
        for lineno, line in enumerate(lines, 1):
            code = line.split("#", 1)[0]
            if depth == 0:
                m = _TOP_LEVEL_OPENER_RE.match(code)
                if m:
                    current = m.group(1)
                    opener_sites.setdefault(current, (rel, lineno))
            elif depth == 1 and current and field_re.match(code):
                field_sites[current] = (rel, lineno)
            depth += code.count("{") - code.count("}")
            if depth <= 0:
                depth, current = 0, None
    return {**opener_sites, **field_sites}


def _flagships_on_company_logo() -> set[str]:
    """Company flagships that show their own company's logo: buildings in
    `bg_company_buildings` that a company type lists in `building_types`, with
    the company's `icon` path as their own. That is the convention, so
    /placeholder-icons leaves them to the company's entry."""
    srv = server_state()
    buildings = srv.ms.get_data("Buildings") or {}
    out: set[str] = set()
    for raw in (srv.ms.get_data("Company Types") or {}).values():
        logo = _entity_image(raw, "icon")
        members = srv.get_field(srv.get_entity_data(raw), "building_types")
        if not logo or not isinstance(members, list):
            continue
        for bid in members:
            braw = buildings.get(bid)
            if (braw is not None
                    and srv.get_field(srv.get_entity_data(braw), "building_group") == "bg_company_buildings"
                    and _entity_image(braw, "icon") == logo):
                out.add(bid)
    return out


def _find_placeholder_icons(*, types: list[str] | None = None,
                            statuses: list[str] | None = None,
                            include_shared_by_design: bool = False,
                            standin_patterns: list[str] | None = None,
                            allowlist: dict | None = None,
                            origin=None, hasher=None,
                            vanilla_gfx: bool | None = None) -> dict:
    """Classify every mod-set image across entity types (GET /placeholder-icons).

    A mod-set image is one on an entity the mod added, or one the mod changed
    from vanilla's value (principles: by group, see _image_entity_uses). Each
    gets a status:
      missing           — the path resolves to no file, in the mod or vanilla.
      generated_standin — matches a glob in common/_meta/generated_standin_icons.yml.
      borrowed_vanilla  — resolves only to a vanilla file.
      shared_mod        — a mod file whose bytes another entity's image also has.
      unique_mod        — a mod file no other entity uses.
      unresolved        — only without a game install: not in the mod, and
                          vanilla's gfx can't be checked.

    Sharing is counted across types, over every entity (vanilla's too) of the
    classified fields, so a law icon on a treaty article shows: `shared_with`
    names up to _SHARED_WITH_LIMIT of them (same type first, a bare key; another
    type as `Type:key`), `shared_count` all of them. Mod files are
    compared by content (`hasher`), vanilla files by path. A company flagship
    on its own company's logo (_flagships_on_company_logo) is left out, and
    doesn't make the company's logo count as shared. An entry the
    /duplicate-images allowlist covers (its entity and path in one entry)
    carries that entry's reason as `allowlisted`: a reviewed share, not work.

    `types` / `statuses` filter the `entities` list; the summary counts every
    status of the filtered types. `origin(rel_path)` → ("mod" | "vanilla",
    abs path) | None and `hasher(rel_path)` default to the filesystem; tests
    inject fakes. `vanilla_gfx` defaults to whether the game's gfx is present.
    """
    srv = server_state()
    if standin_patterns is None:
        standin_patterns = _load_standin_patterns()
    if origin is None:
        origin = _image_origin
    if hasher is None:
        hasher = _image_content_hash
    if vanilla_gfx is None:
        vanilla_gfx = os.path.isdir(os.path.join(srv.base_game_path, "game", "gfx"))
    if allowlist is None:
        allowlist = _load_image_allowlist()
    reviewed = {(entity_type, key, image): reason
                for entity_type, entries in allowlist.items()
                for (images, keys), reason in entries.items()
                for key in keys for image in images}

    fields = ([(et, f, False) for et, f in _IMAGE_FIELDS_BY_TYPE]
              + [(et, f, True) for et, f in _SHARED_BY_DESIGN_ICON_FIELDS])

    # Every use of every field, so a share across types (or with a vanilla
    # entity) is visible whichever type the request filters on.
    flagships = _flagships_on_company_logo()
    uses = []
    for entity_type, field, by_design in fields:
        for rec in _image_entity_uses(entity_type, field):
            if entity_type == "Buildings" and field == "icon" and rec["key"] in flagships:
                continue
            uses.append((entity_type, field, by_design, rec))

    origin_cache: dict[str, tuple[str, str] | None] = {}

    def _origin(path: str):
        if path not in origin_cache:
            origin_cache[path] = origin(path)
        return origin_cache[path]

    identity_cache: dict[str, str] = {}

    def _identity(path: str) -> str:
        if path not in identity_cache:
            found = _origin(path)
            if found and found[0] == "mod":
                identity_cache[path] = hasher(path)
            else:
                identity_cache[path] = f"path:{path}"
        return identity_cache[path]

    users: dict[str, set[tuple[str, str]]] = {}
    for entity_type, _field, by_design, rec in uses:
        if by_design and not include_shared_by_design:
            continue
        users.setdefault(_identity(rec["image"]), set()).add((entity_type, rec["key"]))

    def _status(path: str, by_design: bool) -> str | None:
        found = _origin(path)
        if found is None:
            if not vanilla_gfx:
                return None if by_design and not include_shared_by_design else "unresolved"
            return "missing"
        if by_design and not include_shared_by_design:
            return None
        if any(fnmatch.fnmatchcase(path, p) for p in standin_patterns):
            return "generated_standin"
        if found[0] == "vanilla":
            return "borrowed_vanilla"
        return "shared_mod" if len(users.get(_identity(path), ())) > 1 else "unique_mod"

    summary: dict[str, dict[str, int]] = {}
    entities: list[dict] = []
    sites_cache: dict[tuple[str, str], dict] = {}
    for entity_type, field, by_design, rec in uses:
        if not rec["mod_side"]:
            continue
        if types is not None and entity_type not in types:
            continue
        status = _status(rec["image"], by_design)
        if status is None:
            continue
        counts = summary.setdefault(entity_type, {s: 0 for s in _PLACEHOLDER_STATUSES})
        counts[status] += 1
        if statuses is not None and status not in statuses:
            continue
        me = (entity_type, rec["key"])
        sharers = sorted(
            (et != entity_type, key if et == entity_type else f"{et}:{key}")
            for et, key in users.get(_identity(rec["image"]), ())
            if (et, key) != me
        ) if status not in ("missing", "unresolved") else []
        if (entity_type, field) not in sites_cache:
            sites_cache[(entity_type, field)] = _icon_definition_sites(entity_type, field)
        sites = sites_cache[(entity_type, field)]
        site = next((sites[m] for m in rec["members"] if m in sites), None)
        entry = {
            "entity_type": entity_type,
            "key": rec["key"],
            "field": field,
            "path": rec["image"],
            "status": status,
            "shared_with": [label for _, label in sharers[:_SHARED_WITH_LIMIT]],
            "shared_count": len(sharers),
            "file": site[0] if site else None,
            "line": site[1] if site else None,
        }
        if rec["members"] != [rec["key"]]:
            entry["members"] = sorted(rec["members"])
        reason = reviewed.get((entity_type, rec["key"], rec["image"]))
        if reason and status not in ("missing", "unresolved"):
            entry["allowlisted"] = reason
        entities.append(entry)

    order = {s: i for i, s in enumerate(_PLACEHOLDER_STATUSES)}
    entities.sort(key=lambda e: (order[e["status"]], e["entity_type"], e["key"], e["field"]))
    for entity_type in summary:
        summary[entity_type] = {s: n for s, n in summary[entity_type].items()
                                if n or s != "unresolved"}
    report: dict = {"summary": dict(sorted(summary.items())), "entities": entities}
    if not vanilla_gfx:
        report["warnings"] = [
            f"no vanilla gfx at {os.path.join(srv.base_game_path, 'game', 'gfx')}: a "
            "path outside the mod is `unresolved` (borrowed or missing can't be "
            "told apart) and vanilla files are compared by path only"]
    return report


def _render_placeholder_icons_text(report: dict, *, list_unique: bool = False) -> str:
    """Render the placeholder-icon report for ?format=text. `unique_mod`
    entities are counted but listed only when `list_unique` (a ?status= that
    asks for them): they are the finished state."""
    totals = {s: 0 for s in _PLACEHOLDER_STATUSES}
    for counts in report.get("summary", {}).values():
        for s, n in counts.items():
            totals[s] += n
    out = ["Placeholder icons: " + ", ".join(
        f"{s} {n}" for s, n in totals.items() if n or s != "unresolved")]
    for w in report.get("warnings", []):
        out.append(f"WARNING: {w}")
    out.append("")
    out.append("By type:")
    for entity_type, counts in report.get("summary", {}).items():
        out.append(f"  {entity_type}: " + ", ".join(
            f"{s} {n}" for s, n in counts.items() if n))
    by_status: dict[str, list[dict]] = {}
    for e in report.get("entities", []):
        by_status.setdefault(e["status"], []).append(e)
    for status in _PLACEHOLDER_STATUSES:
        rows = by_status.get(status)
        if not rows:
            continue
        out.append("")
        if status == "unique_mod" and not list_unique:
            out.append(f"UNIQUE_MOD ({len(rows)}): not listed; ask with ?status=unique_mod")
            continue
        out.append(f"{status.upper()} ({len(rows)}):")
        for e in rows:
            where = f"  ({e['file']}:{e['line']})" if e.get("file") else ""
            field = "" if e["field"] in ("icon", "texture") else f" [{e['field']}]"
            out.append(f"  [{e['entity_type']}] {e['key']}{field}  {e['path']}{where}")
            if e.get("members"):
                out.append(f"      principles: {', '.join(e['members'])}")
            if e.get("allowlisted"):
                out.append(f"      allowlisted: {e['allowlisted']}")
            if e.get("shared_with"):
                more = e.get("shared_count", 0) - len(e["shared_with"])
                tail = f" and {more} more" if more > 0 else ""
                out.append(f"      shared with: {', '.join(e['shared_with'])}{tail}")
    return "\n".join(out) + "\n"


def _overlap_vanilla_index():
    """Vanilla for /external-mod-overlap: the game files when installed (with
    file names), else the committed vanilla_parsed/ snapshot (#1170). Kept
    until a reload that re-reads vanilla (not mod_only), so a folder read
    from /mnt/c once is not read again on the next request.

    A server loaded from a snapshot that isn't fresh against the installed
    game (VIC3_VANILLA_SOURCE=vanilla_parsed) reads the snapshot here too, so
    /state's vanilla values are the vanilla behind server_value (#1184). A
    fresh snapshot is the game files' parse, so the game files serve."""
    srv = server_state()
    game_common = os.path.join(srv.base_game_path, "game", "common")
    if (srv._vanilla_source.get("kind") == "vanilla_parsed"
            and not (srv._vanilla_source.get("freshness") or {}).get("fresh")):
        game_common = None
    key = game_common or "<vanilla_parsed>"
    if key not in srv._overlap_vanilla_cache:
        srv._overlap_vanilla_cache[key] = external_mod_overlap.VanillaIndex(game_common=game_common)
    return srv._overlap_vanilla_cache[key]


_OVERLAP_STATE_CACHE_SIZE = 4


def _overlap_state(root: str, refresh: bool = False):
    """(the LayeredState for the mod at `root`, whether it came from the
    cache): this mod's ModState with that mod's common/ entries layered in by
    the probed load order (#1184)."""
    srv = server_state()
    key = os.path.realpath(root)
    if not refresh and key in srv._overlap_state_cache:
        srv._overlap_state_cache[key] = srv._overlap_state_cache.pop(key)
        return srv._overlap_state_cache[key], True
    state = external_mod_state.build(srv.ms, root, srv.mod_path, vanilla=srv._overlap_vanilla_index())
    srv._overlap_state_cache.pop(key, None)
    srv._overlap_state_cache[key] = state
    while len(srv._overlap_state_cache) > _OVERLAP_STATE_CACHE_SIZE:
        srv._overlap_state_cache.pop(next(iter(srv._overlap_state_cache)))
    return state, False


# ---------------------------------------------------------------------------
# Patch-migration toolkit (issue #228)
#
# Three read-only, ref-parameterized (?old_ref=<git-ref>) validators that diff a
# prior vanilla version against the current one to surface what a vanilla bump
# changed under the mod's feet. Each slots into the /validate/* dispatch ladder.
#
# The OLD side is always read from the vanilla clone (`vanilla_source_repo_path`)
# at the supplied ref, via `git show`/`git ls-tree`/`git diff`/`git archive`.
# The NEW side depends on the endpoint:
#   * vanilla-surface-diff  — reads the LIVE install (`base_game_path`) directly,
#     as the task specifies ("clone@old_ref vs the live install"). Key-set
#     comparison, so BOM/whitespace/line-ending skew is irrelevant.
#   * gui-at-risk           — uses the clone's HEAD as the live proxy and
#     `git diff --name-only old_ref..HEAD` (the batched, net-difference form of
#     the runbook §5 per-file `git log old..NEW` loop). Verified byte-identical
#     to the live install during development, so the proxy is exact for the
#     standard workflow (clone fast-forwarded to match the running game first).
#   * loc-override-drift    — compares old_ref vanilla strings against the LIVE
#     vanilla loc snapshot (`_VANILLA_LOC_CACHE`), which is the pure-vanilla loc
#     captured before mod loc is layered on. Both sides parsed with the same
#     quote-extraction rule so multi-quote values can't produce false drift.
#
# All git failures degrade to "clear error / empty result", never a crash. A
# bad/absent ref raises _EndpointError(400); an absent path at a valid ref is a
# normal empty/None (the file simply didn't exist yet at that version).
# ---------------------------------------------------------------------------


# category label -> (repo-relative dir, extractor kind). Top-level unindented
# `key = {` declarations for everything except defines (nested namespaces).
_MIGRATION_SURFACE_CATEGORIES = [
    ("modifier_type_definitions", "game/common/modifier_type_definitions", "toplevel"),
    ("laws",                      "game/common/laws",                      "toplevel"),
    ("law_groups",                "game/common/law_groups",                "toplevel"),
    ("institutions",              "game/common/institutions",              "toplevel"),
    ("technologies",              "game/common/technology/technologies",   "toplevel"),
    ("harvest_condition_types",   "game/common/harvest_condition_types",   "toplevel"),
    ("defines",                   "game/common/defines",                   "defines"),
]


# Mod content dirs grepped for uses of removed vanilla names. gfx (binary) and
# non-content trees (docs/, scripts/, .git) are excluded.
_MOD_GREP_DIRS = ["common", "events", "gui", "localization", "map_data"]


# Column-0 `key = {` (or `key={`), BOM already stripped by the reader.
_TOPLEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.\-]*)\s*=\s*\{", re.MULTILINE)


def _validate_git_ref(ref: str) -> str:
    """Resolve <ref> to a commit SHA in the vanilla clone, or raise
    _EndpointError. Empty/missing -> 400 with usage hint; a ref that git can't
    resolve -> 400; not a git repo -> 500. Guards refs that look like git flags
    (leading '-') so a crafted value can't smuggle options into git."""
    srv = server_state()
    if not ref:
        raise srv._EndpointError({
            "error": "old_ref query parameter is required",
            "hint": "?old_ref=<git-ref in the vanilla clone> — a commit sha, tag, "
                    "or branch, e.g. the commit that bumped to the prior patch.",
        }, 400)
    if ref.startswith("-"):
        raise srv._EndpointError({"error": f"invalid ref: {ref!r}"}, 400)
    repo = srv.vanilla_source_repo_path
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise srv._EndpointError(
            {"error": f"vanilla clone is not a git repo: {repo}"}, 500)
    try:
        r = subprocess.run(
            ["git", "-C", repo, "rev-parse", "--verify", "--quiet",
             f"{ref}^{{commit}}"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.SubprocessError, OSError) as e:
        raise srv._EndpointError({"error": f"git rev-parse failed: {e}"}, 500)
    if r.returncode != 0 or not r.stdout.strip():
        raise srv._EndpointError({
            "error": f"ref not found in vanilla clone: {ref!r}",
            "repo": repo,
            "hint": "Pass a commit sha, tag, or branch present in "
                    "vanilla_source_repo_path.",
        }, 400)
    return r.stdout.strip()


def _git_show_at_ref(ref: str, relpath: str) -> Optional[str]:
    """Text of <relpath> (repo-relative, e.g. 'game/common/laws/00_x.txt') at
    <ref>, decoded utf-8-sig (BOM-stripped), or None if the path is absent at
    that ref / git fails. Assumes <ref> already validated."""
    srv = server_state()
    repo = srv.vanilla_source_repo_path
    try:
        r = subprocess.run(
            ["git", "-C", repo, "show", f"{ref}:{relpath}"],
            capture_output=True, timeout=20,
        )
    except (subprocess.SubprocessError, OSError) as e:
        srv.logger.warning(f"git show {ref}:{relpath} failed: {e}")
        return None
    if r.returncode != 0:
        return None  # path absent at ref — normal
    return r.stdout.decode("utf-8-sig", errors="replace")


def _git_lstree_at_ref(ref: str, reldir: str,
                       suffix: Optional[str] = None) -> list:
    """Sorted repo-relative file paths under <reldir> (recursive) at <ref>,
    optionally filtered by <suffix>. Empty list if the dir is absent."""
    srv = server_state()
    repo = srv.vanilla_source_repo_path
    try:
        r = subprocess.run(
            ["git", "-C", repo, "ls-tree", "-r", "--name-only", ref, "--", reldir],
            capture_output=True, text=True, timeout=20,
        )
    except (subprocess.SubprocessError, OSError) as e:
        srv.logger.warning(f"git ls-tree {ref}:{reldir} failed: {e}")
        return []
    if r.returncode != 0:
        return []
    files = [ln for ln in r.stdout.splitlines() if ln.strip()]
    if suffix:
        files = [f for f in files if f.endswith(suffix)]
    return sorted(files)


def _git_diff_names(ref: str, pathspecs: list) -> set:
    """Repo-relative paths that differ (added/modified/deleted) between <ref>
    and the clone's HEAD, restricted to <pathspecs>. One git call — the batched
    equivalent of the runbook §5 per-file `git log old..NEW -- path` loop."""
    srv = server_state()
    repo = srv.vanilla_source_repo_path
    try:
        r = subprocess.run(
            ["git", "-C", repo, "diff", "--name-only", ref, "HEAD", "--",
             *pathspecs],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as e:
        srv.logger.warning(f"git diff {ref}..HEAD failed: {e}")
        return set()
    if r.returncode != 0:
        return set()
    return {ln for ln in r.stdout.splitlines() if ln.strip()}


def _git_log_touched(ref: str, repo_rel: str) -> Optional[str]:
    """`<short-sha> <subject>` of the most-recent commit that touched <repo_rel>
    in <ref>..HEAD, or None. Cheap per-flagged-file context annotation."""
    srv = server_state()
    repo = srv.vanilla_source_repo_path
    try:
        r = subprocess.run(
            ["git", "-C", repo, "log", "--oneline", "-1", f"{ref}..HEAD",
             "--", repo_rel],
            capture_output=True, text=True, timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    line = r.stdout.strip().splitlines()
    return line[0] if line else None


def _read_live_file(relpath: str) -> Optional[str]:
    """Text of <relpath> (game-relative, e.g. 'game/common/laws/00_x.txt') from
    the LIVE install, decoded utf-8-sig, or None if absent."""
    srv = server_state()
    p = os.path.join(srv.base_game_path, relpath)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "rb") as f:
            return f.read().decode("utf-8-sig", errors="replace")
    except OSError as e:
        srv.logger.warning(f"read live {relpath} failed: {e}")
        return None


def _code_part(line: str) -> str:
    """<line> up to its first `#` outside a double-quoted string — the part a
    Paradox script or loc line executes. `#` inside quotes is loc markup
    (`#b …#!`) or string text, not a comment; a backslash escapes the next
    character inside quotes, as in loc values."""
    in_quote = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_quote and ch == "\\":
            i += 2
            continue
        if ch == '"':
            in_quote = not in_quote
        elif ch == "#" and not in_quote:
            return line[:i]
        i += 1
    return line


def _mod_grep_mentions(name: str) -> tuple:
    """(use_files, comment_only_files): mod-relative files in the mod content
    dirs that mention <name> (whole-word, fixed-string), via `git grep`. A file
    is a use if any matching line has the name outside a `#` comment; it is
    comment-only if every match sits in a comment (#485: a header comment
    explaining a vanilla rename is not a use of the old name). Both empty on no
    match (git grep exits 1) or error. Only searches tracked files — matches
    the mod's committed state.

    A define's surface name is `Namespace.KEY`, a spelling no mod file uses:
    script reads the define as `define:Namespace|KEY`, and a GUI or loc string
    as `GetDefine('Namespace', 'KEY')`. For a dotted name those two forms are
    mentions too; grepping the dotted name alone missed the mod's read of a
    define 1.14.4 removed (#391). The grep is then on the key, and a line
    counts only where one of the three forms is on it, so the same key under
    another namespace is not a mention."""
    srv = server_state()
    repo = srv.mod_path
    dirs = [d for d in _MOD_GREP_DIRS if os.path.isdir(os.path.join(repo, d))]
    if not dirs:
        return [], []
    forms = [re.escape(name)]
    needle = name
    if "." in name:
        parts = name.split(".")
        needle = parts[-1]
        forms.append(re.escape("|".join(parts)))
        if len(parts) == 2:
            forms.append(
                r"GetDefine\(\s*['\"]" + re.escape(parts[0]) + r"['\"]\s*,\s*['\"]"
                + re.escape(parts[1]) + r"['\"]\s*\)"
            )
    try:
        r = subprocess.run(
            ["git", "-C", repo, "grep", "--no-color", "-z", "-w", "-F",
             "-e", needle, "--", *dirs],
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return [], []
    # git grep's -w word boundary, re-applied to the code part: a plain
    # substring test would count `<name>_extra` in code when the whole-word
    # match was only in the comment.
    word = re.compile(
        r"(?<![A-Za-z0-9_])(?:" + "|".join(forms) + r")(?![A-Za-z0-9_])"
    )
    used: set = set()
    mentioned: set = set()
    # Split on "\n" only: git ends each record with it, and splitlines() would
    # also break a record at \x0c, \x85,   and the like inside the line.
    for ln in r.stdout.split("\n"):
        path, sep, text = ln.partition("\0")
        if not sep or not word.search(text):
            continue
        mentioned.add(path)
        if word.search(_code_part(text)):
            used.add(path)
    return sorted(used), sorted(mentioned - used)


def _extract_toplevel_keys(text: Optional[str]) -> set:
    """Top-level (column-0) `key = {` declarations — the entity-declaration
    surface for laws / modifier_type_definitions / institutions / technologies /
    harvest_condition_types / law_groups. Nested/indented blocks are skipped by
    the column-0 (^, MULTILINE) anchor. BOM-aware even if the reader didn't
    strip it (Python str.strip does not treat U+FEFF as whitespace)."""
    if not text:
        return set()
    text = text.lstrip("﻿")
    return {m.group(1) for m in _TOPLEVEL_KEY_RE.finditer(text)}


def _extract_define_names(text: Optional[str]) -> set:
    """Best-effort qualified define names (`Namespace.LEAF`) from a defines .txt.
    Tracks the current `Nxxx = {` block path by brace depth and emits one name
    per leaf assignment. Handles the 2-3-level nesting Vic3 defines use; not a
    full parser (single-line `k = { ... }` blocks are pushed/popped naively).
    BOM-aware (see _extract_toplevel_keys)."""
    if not text:
        return set()
    text = text.lstrip("﻿")
    names: set = set()
    stack: list = []
    assign_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line == "}":
            if stack:
                stack.pop()
            continue
        m = assign_re.match(line)
        if m:
            key, rest = m.group(1), m.group(2).strip()
            if rest.startswith("{"):
                stack.append(key)
                if rest.count("}") >= rest.count("{"):  # single-line block
                    stack.pop()
            else:
                names.add(".".join(stack + [key]))
        elif "}" in line and stack:
            stack.pop()
    return names


def _extract_surface_keys(kind: str, text: Optional[str]) -> set:
    return _extract_define_names(text) if kind == "defines" \
        else _extract_toplevel_keys(text)


def _parse_loc_lines(text: str):
    """Yield (key, value) from Paradox loc text via the shared
    `mod_state.parse_loc_line` rule — the one ModState.add_localization uses
    to build `_VANILLA_LOC_CACHE` — so the OLD-ref parse and the NEW side
    extract identically and escaped-quote / multi-quote values never
    false-drift. Skips the `l_english:` header and comment lines."""
    yield from iter_loc_lines(text)


def _iter_loc_at_ref(ref: str, reldir: str = "game/localization/english"):
    """Yield (member_name, text) for every .yml under <reldir> at <ref>, via a
    single `git archive | tar` stream (one subprocess vs ~170 git-show calls)."""
    srv = server_state()
    import io
    import tarfile
    repo = srv.vanilla_source_repo_path
    try:
        r = subprocess.run(
            ["git", "-C", repo, "archive", ref, "--", reldir],
            capture_output=True, timeout=60,
        )
    except (subprocess.SubprocessError, OSError) as e:
        srv.logger.warning(f"git archive {ref}:{reldir} failed: {e}")
        return
    if r.returncode != 0 or not r.stdout:
        return
    try:
        with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
            for m in tf.getmembers():
                if not m.isfile() or not m.name.endswith(".yml"):
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                yield m.name, f.read().decode("utf-8-sig", errors="replace")
    except (tarfile.TarError, OSError) as e:
        srv.logger.warning(f"tar extract of {ref}:{reldir} failed: {e}")


def _live_vanilla_loc_map() -> dict:
    """Pure-vanilla LIVE loc key->string. Prefers `_VANILLA_LOC_CACHE` (captured
    before mod loc is layered on the first full load); falls back to reading the
    live vanilla loc dir if the cache isn't populated yet."""
    srv = server_state()
    if srv._VANILLA_LOC_CACHE is not None:
        return srv._VANILLA_LOC_CACHE
    m: dict = {}
    d = os.path.join(srv.base_game_path, "game", "localization", "english")
    if not os.path.isdir(d):
        return m
    for root, _dirs, files in os.walk(d):
        for fn in files:
            if not fn.endswith(".yml"):
                continue
            try:
                with open(os.path.join(root, fn), "rb") as fh:
                    txt = fh.read().decode("utf-8-sig", errors="replace")
            except OSError:
                continue
            for k, v in _parse_loc_lines(txt):
                m[k] = v
    return m


def _mod_loc_keys() -> set:
    """Keys the mod defines in localization/english/ + its replace/ subdir —
    exactly the two dirs the server layers over vanilla loc (non-recursive,
    matching that load)."""
    srv = server_state()
    keys: set = set()
    for sub in ("", "replace"):
        d = os.path.join(srv.mod_path, "localization", "english", sub)
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.endswith(".yml"):
                continue
            try:
                with open(os.path.join(d, fn), "rb") as fh:
                    txt = fh.read().decode("utf-8-sig", errors="replace")
            except OSError:
                continue
            for k, _v in _parse_loc_lines(txt):
                keys.add(k)
    return keys


def _migration_surface_diff(old_ref: str) -> dict:
    """GET /validate/vanilla-surface-diff — see handler docstring."""
    srv = server_state()
    ref = _validate_git_ref(old_ref)
    added: dict = {}
    removed: dict = {}
    removed_join: list = []
    commented_join: list = []
    for label, reldir, kind in _MIGRATION_SURFACE_CATEGORIES:
        old_keys: set = set()
        for f in _git_lstree_at_ref(ref, reldir, ".txt"):
            old_keys |= _extract_surface_keys(kind, _git_show_at_ref(ref, f))
        # NEW side: the live install, read directly (task #1 wording).
        new_keys: set = set()
        live_dir = os.path.join(srv.base_game_path, reldir)
        if os.path.isdir(live_dir):
            for root, _d, files in os.walk(live_dir):
                for fn in files:
                    if not fn.endswith(".txt"):
                        continue
                    rel = os.path.relpath(os.path.join(root, fn),
                                          srv.base_game_path).replace(os.sep, "/")
                    new_keys |= _extract_surface_keys(kind, _read_live_file(rel))
        cat_added = sorted(new_keys - old_keys)
        cat_removed = sorted(old_keys - new_keys)
        if cat_added:
            added[label] = cat_added
        if cat_removed:
            removed[label] = cat_removed
        # The payoff: for each removed name, does the mod still reference it?
        # `re_registered_by_mod` disambiguates the two cases this join conflates:
        # a genuine silent-no-op (mod uses a name vanilla dropped) vs the mod
        # having already re-registered the dropped name in its own
        # modifier_type_definitions/ (the documented 1.13.9 harvest-condition
        # fix) — the latter is safe, not a fire. A name the mod mentions only
        # in `#` comments (say, a note on the rename) is not a use; it goes to
        # the separate `removed_and_only_commented_in_mod` list instead.
        for name in cat_removed:
            files, comment_files = _mod_grep_mentions(name)
            if files:
                entry = {"name": name, "category": label, "mod_files": files}
                if label == "modifier_type_definitions" and any(
                        "modifier_type_definitions/" in f for f in files):
                    entry["re_registered_by_mod"] = True
                removed_join.append(entry)
            elif comment_files:
                commented_join.append({"name": name, "category": label,
                                       "mod_files": comment_files})
    return {
        "old_ref": old_ref,
        "old_ref_sha": ref,
        "added": added,
        "removed": removed,
        "removed_and_used_by_mod": removed_join,
        "removed_and_only_commented_in_mod": commented_join,
        "summary": {
            "added": sum(len(v) for v in added.values()),
            "removed": sum(len(v) for v in removed.values()),
            "removed_and_used_by_mod": len(removed_join),
            "removed_and_only_commented_in_mod": len(commented_join),
        },
    }


def _migration_gui_at_risk(old_ref: str) -> dict:
    """GET /validate/gui-at-risk — see handler docstring."""
    srv = server_state()
    ref = _validate_git_ref(old_ref)
    changed = _git_diff_names(ref, ["game/gui", "game/common"])

    def _scan(subdir: str, suffix: str) -> tuple:
        root = os.path.join(srv.mod_path, subdir)
        at_risk: list = []
        checked = 0
        if os.path.isdir(root):
            for dirpath, _d, files in os.walk(root):
                for fn in files:
                    if not fn.endswith(suffix):
                        continue
                    rel = os.path.relpath(os.path.join(dirpath, fn),
                                          srv.mod_path).replace(os.sep, "/")
                    checked += 1
                    if "game/" + rel in changed:
                        at_risk.append({
                            "rel": rel, "changed": True,
                            "last_vanilla_commit": _git_log_touched(
                                ref, "game/" + rel),
                        })
        at_risk.sort(key=lambda e: e["rel"])
        return at_risk, checked

    gui_at_risk, gui_checked = _scan("gui", ".gui")
    common_at_risk, common_checked = _scan("common", ".txt")
    return {
        "old_ref": old_ref,
        "old_ref_sha": ref,
        "gui_at_risk": gui_at_risk,
        "common_overrides_at_risk": common_at_risk,
        "summary": {
            "gui_files_scanned": gui_checked,
            "gui_at_risk": len(gui_at_risk),
            "common_files_scanned": common_checked,
            "common_overrides_at_risk": len(common_at_risk),
        },
    }


def _migration_loc_drift(old_ref: str) -> dict:
    """GET /validate/loc-override-drift — see handler docstring."""
    ref = _validate_git_ref(old_ref)
    live = _live_vanilla_loc_map()
    shadowed = {k for k in _mod_loc_keys() if k in live}
    # Known limitation: the OLD side (below) is first-file-wins while the live
    # side (_VANILLA_LOC_CACHE, built by add_localization) is last-file-wins.
    # A vanilla key duplicated across files with divergent values could thus
    # report spurious drift; near-impossible in practice (real data: 0) and true
    # symmetry would require matching file-iteration order, not just the quote
    # rule — not worth it.
    old_strings: dict = {}
    for _name, text in _iter_loc_at_ref(ref):
        for k, v in _parse_loc_lines(text):
            if k in shadowed and k not in old_strings:
                old_strings[k] = v
    drifted: list = []
    for k in sorted(shadowed):
        old = old_strings.get(k)
        new = live.get(k)
        if old is not None and old != new:
            drifted.append({"key": k, "old": old, "new": new})
    return {
        "old_ref": old_ref,
        "old_ref_sha": ref,
        "shadowed_key_count": len(shadowed),
        "drifted": drifted,
        "summary": {
            "shadowed_keys": len(shadowed),
            "old_ref_keys_found": len(old_strings),
            "drifted": len(drifted),
        },
    }


class ValidationRoutes:
    """GET /validate/*, /external-mod-overlap, /duplicate-images, /placeholder-icons, /auto-generated and the event audits. A mixin of ModStateHandler."""

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
                    "pattern": "common/production_methods/carbon_capture_generated_pms.txt",
                    "owner": "gen_carbon_capture_pms.py",
                    "input": "merged building/PM graph + capture tiers, costs and exclusions",
                    "header_marker": True,
                },
                {
                    "pattern": "common/production_method_groups/carbon_capture_generated_groups.txt",
                    "owner": "gen_carbon_capture_pms.py",
                    "input": "merged building/PM graph + capture tiers, costs and exclusions",
                    "header_marker": True,
                },
                {
                    "pattern": "common/buildings/zz_te_carbon_capture_injects.txt",
                    "owner": "gen_carbon_capture_pms.py",
                    "input": "merged building/PM graph + capture tiers, costs and exclusions",
                    "header_marker": True,
                },
                {
                    "pattern": "common/production_methods/greenhouse_gas_generated_injects.txt",
                    "owner": "gen_carbon_capture_pms.py",
                    "input": "merged PM coal/oil inputs + shared greenhouse-gas factors",
                    "header_marker": True,
                },
                {
                    "pattern": "common/script_values/household_emissions_generated_values.txt",
                    "owner": "gen_carbon_capture_pms.py",
                    "input": "merged buy packages, heating weights/caps, pop types, coal/oil prices",
                    "header_marker": True,
                },
                {
                    "pattern": "common/ideologies/modified.txt",
                    "owner": "apply_ideologies.py",
                    "input": "ideology_modifications.py",
                    "header_marker": True,
                },
                {
                    "pattern": "common/interest_groups/zz_te_ig_female_chance.txt",
                    "owner": "ig_feminism.py",
                    "input": "profiles in ig_feminism.py + vanilla interest groups",
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
        srv = server_state()
        if not parts:
            return {
                "available": [
                    "engine-coverage", "modifier-visibility",
                    "vanilla-surface-diff", "gui-at-risk", "loc-override-drift",
                ],
                "hint": (
                    "GET /validate/engine-coverage[?summary=true] | "
                    "GET /validate/modifier-visibility[?include_reviewed=true] | "
                    "GET /validate/vanilla-surface-diff?old_ref=<git-ref> | "
                    "GET /validate/gui-at-risk?old_ref=<git-ref> | "
                    "GET /validate/loc-override-drift?old_ref=<git-ref>"
                ),
            }
        check = parts[0]
        if check == "modifier-visibility":
            return self._validate_modifier_visibility(params)
        if check == "vanilla-surface-diff":
            return self._validate_vanilla_surface_diff(params)
        if check == "gui-at-risk":
            return self._validate_gui_at_risk(params)
        if check == "loc-override-drift":
            return self._validate_loc_override_drift(params)
        if check != "engine-coverage":
            raise srv.NotFound(check)
        force = (params.get("refresh") or ["false"])[0].lower() == "true"
        if force or srv._last_validation_report is None:
            srv._last_validation_report = srv._validate_engine_coverage()
        report = srv._last_validation_report
        # The validator reports a cold/degraded server in-band; over HTTP that
        # is a 503, not a 200 with an error body. (#254)
        if isinstance(report, dict) and "error" in report and "summary" not in report:
            raise srv._ServiceNotReady(report, 503)

        filt = (params.get("filter") or [""])[0]
        summary_only = (params.get("summary") or ["false"])[0].lower() == "true"

        if filt == "vanilla_breakages":
            # Collect mod-defined modifier-type names from the mod's
            # `common/modifier_type_definitions/` parser.
            mod_defined: set[str] = set()
            mod_types = srv.ms.get_data("Modifier Types") if srv.ms else None
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
        srv = server_state()
        import modifier_visibility_audit as mva
        result = mva.audit(srv.ms, mod_path=srv.mod_path)
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

    def _validate_vanilla_surface_diff(self, params):
        """GET /validate/vanilla-surface-diff?old_ref=<git-ref> — diff the
        entity-key *surfaces* (modifier_type_definitions, defines, laws,
        law_groups, institutions, technologies, harvest_condition_types) between
        the vanilla clone at <old_ref> and the LIVE install. The payoff is
        `removed_and_used_by_mod`: for every name that vanilla dropped, whether
        the mod still references it (silent no-op / broken inject). This join
        surfaced both 1.13.9 breakage classes (the law-enactment rename and the
        harvest-condition deregistration) without launching the game. Only
        matches outside `#` comments count as uses; a removed name the mod
        mentions only in comments is listed in
        `removed_and_only_commented_in_mod` instead (#485).

        Returns {old_ref, old_ref_sha, added:{cat:[...]}, removed:{cat:[...]},
        removed_and_used_by_mod:[{name, category, mod_files:[...]}],
        removed_and_only_commented_in_mod:[{name, category, mod_files:[...]}],
        summary}.
        """
        old_ref = (params.get("old_ref") or [""])[0]
        return _migration_surface_diff(old_ref)

    def _validate_gui_at_risk(self, params):
        """GET /validate/gui-at-risk?old_ref=<git-ref> — mod gui/*.gui overrides
        (and wholesale same-path common/*.txt overrides) whose same-relative-path
        vanilla file changed between <old_ref> and the current vanilla (clone
        HEAD as live proxy). Batched form of the runbook §5 per-file
        `git log old..NEW` loop. A conflict-free merge is not a clean merge — the
        engine logs no GUI script errors, so an unrebased override manifests as a
        silently dead button, not a debug.log entry.

        Returns {old_ref, old_ref_sha, gui_at_risk:[{rel, changed, ...}],
        common_overrides_at_risk:[...], summary}.
        """
        old_ref = (params.get("old_ref") or [""])[0]
        return _migration_gui_at_risk(old_ref)

    def _validate_loc_override_drift(self, params):
        """GET /validate/loc-override-drift?old_ref=<git-ref> — for the vanilla
        loc keys the mod shadows (via localization/**/replace/ + same-key
        stragglers), which ones' *vanilla* string changed between <old_ref> and
        the live game. A drifted key means the mod's override was written against
        vanilla text that has since moved — the override may now be stale. Cheap
        to know; expensive to check by hand (last migration: 0 drifted).

        Returns {old_ref, old_ref_sha, shadowed_key_count, drifted:[{key, old,
        new}], summary}.
        """
        old_ref = (params.get("old_ref") or [""])[0]
        return _migration_loc_drift(old_ref)

    @staticmethod
    def _multi_param(params, name) -> list[str] | None:
        """A repeatable, comma-separated query param as a list, or None."""
        values = []
        for raw in params.get(name) or []:
            values.extend(v.strip() for v in raw.split(",") if v.strip())
        return values or None

    def _duplicate_images(self, params):
        """GET /duplicate-images — flag images reused across entities of types
        where vanilla treats one image per entity (`_IMAGE_FIELDS_BY_TYPE`;
        principles by group).

        Query params:
          ?include_vanilla=true     — include clusters with no mod-side entities.
          ?include_allowlisted=true — emit the `allowlisted` array.
          ?type=Buildings           — restrict scan (repeatable, comma-separated).
          ?format=text              — human-readable rendering wrapped in {"text": ...}.

        Allowlist file: common/_meta/duplicate_image_allowlist.yml. Entries
        that match no cluster come back in `stale_allowlist`.
        """
        include_vanilla = (params.get("include_vanilla") or ["false"])[0].lower() == "true"
        include_allowlisted = (params.get("include_allowlisted") or ["false"])[0].lower() == "true"
        types = self._multi_param(params, "type")

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

    def _placeholder_icons(self, params):
        """GET /placeholder-icons — classify every mod-set icon across entity
        types as missing, generated_standin, borrowed_vanilla, shared_mod or
        unique_mod (see `_find_placeholder_icons`).

        Query params:
          ?type=Decrees                   — only these types (repeatable, comma-separated).
          ?status=borrowed_vanilla        — only these statuses (repeatable, comma-separated).
          ?include_shared_by_design=true  — also classify the types vanilla shares
                                            art in (PMs, static modifiers, messages,
                                            `background` fields, …); without it they
                                            are checked for `missing` only.
          ?format=text                    — human-readable rendering wrapped in {"text": ...}.

        Stand-in globs: common/_meta/generated_standin_icons.yml.
        """
        srv = server_state()
        statuses = self._multi_param(params, "status")
        unknown = sorted(set(statuses or ()) - set(_PLACEHOLDER_STATUSES))
        if unknown:
            raise srv.BadRequest(f"Unknown status {', '.join(unknown)}; expected one of "
                             f"{', '.join(_PLACEHOLDER_STATUSES)}")
        report = _find_placeholder_icons(
            types=self._multi_param(params, "type"),
            statuses=statuses,
            include_shared_by_design=(
                (params.get("include_shared_by_design") or ["false"])[0].lower() == "true"),
        )
        if (params.get("format") or [""])[0] == "text":
            return {"text": _render_placeholder_icons_text(
                report, list_unique=bool(statuses and "unique_mod" in statuses))}
        return report

    def _event_dispatch(self, rest):
        """GET /event-dispatch/<event_id> — who fires this event, from where, in
        which scope and under which guard (event_context_audit's graph).

        Reads the mod tree from disk on each call (~1 s), so it reflects edits
        without a /reload. `chosen` says whether the recipient country reached
        the event through its own choice (own option, decision, button, law…);
        `gated_systems` lists the mod systems every dispatch path is gated on.
        """
        srv = server_state()
        import event_context_audit as eca
        from path_constants import mod_path as _mod_path

        if not rest:
            raise srv.BadRequest("usage: /event-dispatch/<event_id>")
        eid = rest[0]
        g = eca.build_graph(_mod_path)
        r = eca.Resolver(g)
        if eid not in g.events and eid not in g.sites_by_event:
            raise srv.NotFound(eid)
        sites = []
        for s in g.sites_by_event.get(eid, []):
            status, reason = r.site_choice(s)
            sites.append({
                "file": s.file, "line": s.line, "entity": s.entity,
                "entity_kind": s.entity_kind, "via": s.via, "path": s.path,
                "scope_switches": s.switches, "in_option": s.in_option,
                "guards": s.conds.strip(), "chosen": status == eca.CHOSEN,
                "reason": reason,
            })
        status, reason = r.event_choice(eid)
        ev = g.events.get(eid)
        return {
            "event_id": eid,
            "defined_in": f"{ev.file}:{ev.line}" if ev else None,
            "hidden": ev.hidden if ev else None,
            "chosen_by_recipient": status == eca.CHOSEN,
            "reason": reason,
            "gated_systems": [sysm.key for sysm in eca.SYSTEMS if r.event_gated(eid, sysm)],
            "sites": sites,
        }

    def _event_context_audit(self, params):
        """GET /event-context-audit — event_context_audit flags as JSON.

        Filters: ?check=system_ungated|unchosen_self_action|imputed_foreign_action,
        ?event_id=foo.5, ?show_reviewed=true, ?format=text (markdown report).
        """
        srv = server_state()
        import event_context_audit as eca
        from path_constants import mod_path as _mod_path

        result = eca.audit(_mod_path)
        flags = result.flags
        show_reviewed = (params.get("show_reviewed") or ["false"])[0].lower() in ("true", "1", "yes")
        if not show_reviewed:
            flags = [f for f in flags if not f.exemption]
        check = (params.get("check") or [None])[0]
        if check:
            if check not in eca.CHECKS:
                raise srv.BadRequest(f"unknown check {check!r}", valid=list(eca.CHECKS))
            flags = [f for f in flags if f.check == check]
        event_filter = (params.get("event_id") or [None])[0]
        if event_filter:
            flags = [f for f in flags if f.event_id == event_filter]
        if (params.get("format") or ["json"])[0] == "text":
            return {"text": eca.render_report(eca.AuditResult(
                flags=flags, coverage=result.coverage,
                stale_tags=result.stale_tags, unknown_tags=result.unknown_tags))}
        return {
            "flags": [
                {"check": f.check, "event_id": f.event_id, "file": f.file, "line": f.line,
                 "detail": f.detail, "evidence": f.evidence, "dispatch": f.dispatch,
                 "exemption": f.exemption}
                for f in flags
            ],
            "coverage": result.coverage,
            "stale_tags": [{"event_id": t.event_id, "check": t.check, "file": t.file, "line": t.line}
                           for t in result.stale_tags + result.unknown_tags],
        }

    def _event_magnitude_audit(self, params):
        """GET /event-magnitude-audit — flag hardcoded fast-scaling resource deltas in events.

        Filters:
          ?resource=prestige           — substring match on resource label
          ?event_id=foo.5              — exact match on event id
          ?show_reviewed=true          — include reviewed exemptions in flags list
          ?format=text                 — return the markdown report instead of JSON
        """
        srv = server_state()
        import event_magnitude_audit as ema
        from path_constants import mod_path as _mod_path

        result = ema.audit(srv.ms, mod_path=_mod_path)
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

    # ---- another mod's overlap with ours (#1170) ---------------------------
    def _external_mod_overlap(self, parts, params):
        """GET /external-mod-overlap?path=<mod root>[&trace=true]
        GET /external-mod-overlap/state[/<EntityType>[/<key>]]?path=<mod root>[&refresh=true]

        Read-only: scans the other mod's folder and this mod's, reports the
        entries both define and which side the load order keeps. The logic and
        the load-order model live in external_mod_overlap.py. `/state` is
        this mod's ModState with the other mod's common/ entries layered in by
        that model (external_mod_state.py, #1184): the summary, one entity
        type's recomputed keys, or one key's merged entry (its value as /raw
        gives it, the server's value, every definition and the simulated
        load, and every candidate when an unknown decides it)."""
        srv = server_state()
        if parts and parts[0] == "state":
            return self._external_mod_state(parts[1:], params)
        if parts:
            raise srv.NotFound("/".join(["external-mod-overlap", *parts]))
        usage = "GET /external-mod-overlap?path=<mod root>[&trace=true]"
        root = self._overlap_root(params, usage)
        trace = self._bool_param(params, "trace", usage)
        return external_mod_overlap.analyze(
            root, srv.mod_path, vanilla=srv._overlap_vanilla_index(), include_trace=trace)

    def _overlap_root(self, params, usage):
        srv = server_state()
        try:
            root = external_mod_overlap.validate_root((params.get("path") or [""])[0])
        except ValueError as exc:
            raise srv.BadRequest(str(exc), usage=usage)
        if os.path.realpath(root) == os.path.realpath(srv.mod_path):
            raise srv.BadRequest(f"{root} is this mod; pass another mod's root", usage=usage)
        return root

    @staticmethod
    def _bool_param(params, name, usage):
        srv = server_state()
        value = (params.get(name) or ["false"])[0].lower()
        if value not in ("true", "false"):
            raise srv.BadRequest(f"{name} must be true or false, got {value!r}", usage=usage)
        return value == "true"

    def _external_mod_state(self, parts, params):
        srv = server_state()
        usage = ("GET /external-mod-overlap/state[/<EntityType>[/<key>]]"
                 "?path=<mod root>[&refresh=true]")
        if len(parts) > 2:
            raise srv.NotFound("/".join(["external-mod-overlap", "state", *parts]))
        root = self._overlap_root(params, usage)
        refresh = self._bool_param(params, "refresh", usage)
        if srv.ms is None:
            raise srv.DataNotLoaded("ModState")
        etype = self._resolve_entity_type_or_404(parts[0]) if parts else None
        state, cached = _overlap_state(root, refresh)
        if etype is None:
            return {**state.summary(), "cached": cached}
        if len(parts) == 1:
            return {**state.entity_type(etype), "cached": cached}
        entry = state.entity(etype, parts[1])
        if entry is None:
            raise srv.NotFound(parts[1])
        return {**entry, "cached": cached}
