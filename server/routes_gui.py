"""The GUI routes: GET /gui/render-sites/<loc_key>, /gui/render-paths/<EntityType>
and /gui/placeholder-textures, with the GUI render-site index they read.
Moved out of mod_state_server.py unchanged (#1537).

A route module holds code only (server/__init__.py says why): the state these
routes read stays in mod_state_server and is read as `srv.<name>` through
`server_state()` at call time. mod_state_server re-exports every name below.
"""
import difflib
import os
import re

from server import server_state


# ---------------------------------------------------------------------------
# Entity-type -> engine GUI datatype map. Seeded from data_types_script.txt
# (e.g. Scope.GetTreatyArticle -> Article). Used by /gui/render-paths to
# resolve which [Type.GetX] chains render a given entity's fields.
# ---------------------------------------------------------------------------
ENTITY_TYPE_TO_DATATYPE: dict[str, str] = {
    "Treaty Articles": "Article",
    "Decisions": "Decision",
    "Decrees": "Decree",
    "Journal Entries": "JournalEntry",
    "Laws": "Law",
    "Buildings": "Building",
    "Character Interactions": "CharacterInteraction",
    "Diplomatic Actions": "DiplomaticAction",
    "Diplomatic Plays": "DiplomaticPlay",
    "Interest Groups": "InterestGroup",
    "Goods": "Goods",
    "Production Methods": "ProductionMethod",
    "PMs": "ProductionMethod",
    "Pop Types": "PopType",
    "Cultures": "Culture",
    "Religions": "Religion",
    "Technologies": "Technology",
    "Institutions": "Institution",
    "Game Concepts": "Concept",
    "Glossary": "GlossaryType",
    "Regional Exile Pools": "RegionalExilePool",
    "Country Formation": "CountryFormation",
    "Parties": "Party",
}


# Field role -> set of GUI accessor method names that render that field.
# Broad sets cover the various GetXDesc naming conventions: e.g. Article uses
# GetEffectsDesc / GetShortDesc / GetImmediateEffectsDesc — not GetDesc.
FIELD_TO_METHODS: dict[str, set[str]] = {
    "name": {"GetName", "GetNameNoFormatting", "GetNameForListbox", "GetDisplayName"},
    "desc": {
        "GetDesc", "GetDescription", "GetDescriptionNoFormatting",
        "GetEffectsDesc", "GetShortDesc", "GetImmediateEffectsDesc",
        "GetEffectDesc", "GetBriefDesc",
    },
    "icon": {"GetIcon", "GetIconPath", "GetIconKey", "GetTexture"},
    "tooltip": {"GetTooltip", "GetTooltipText"},
}


# Match `<attr> = "<loc_key>"` where the value is a bare snake_case loc key
# (no whitespace, no concept tags). Avoids false positives on free-text labels
# that happen to be quoted (e.g. `text = "Some literal."`).
_GUI_TEXT_ATTR_RE = re.compile(
    r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*"([a-z][a-zA-Z0-9_]*)"'
)


# Attributes that the engine treats as loc references (the value gets resolved
# against the loc dict). Everything else is dropped — most GUI attrs hold
# literal strings (widget names, paths, colors).
_GUI_LOC_ATTRS: set[str] = {
    "text", "tooltip", "tooltip_text", "raw_text", "default_text",
    "description", "name_tooltip", "button_text", "header", "title",
    "loc_key", "tooltip_on_focus", "loctext",
}


# Match `<DataType>.<Method>` anywhere inside a `[...]` expression. We don't
# anchor on `[` because vanilla nests calls — e.g. `[Not(StringIsEmpty(Article.GetEffectsDesc))]`
# — and the inner DataType.Method is the part we care about. False positives
# are minimal in `.gui` files (which rarely use bare uppercase dotted refs
# outside data-system expressions); the index is only consulted when both
# DataType and Method match the lookup.
_GUI_DATAREF_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\.([A-Z][A-Za-z0-9_]*)")


def _build_gui_render_index(scan_roots: list[tuple[str, str]]) -> dict:
    """Scan GUI files and produce two indexes: by loc key (direct refs) and by
    (DataType, Method) pair (entity-method walker support).

    `scan_roots` is a list of `(root_path, rel_to)` pairs. Each `rel_to`
    anchors the path-relative output (e.g. `(base/game, base)` -> "game/gui/..").
    Parameterized so unit tests can feed a tempdir without touching globals.
    """
    srv = server_state()
    by_key: dict[str, list[dict]] = {}
    by_method: dict[tuple[str, str], list[dict]] = {}

    for root, rel_to in scan_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for fname in files:
                if not fname.endswith(".gui"):
                    continue
                path = os.path.join(dirpath, fname)
                rel = os.path.relpath(path, rel_to).replace(os.sep, "/")
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        for line_no, line in enumerate(f, start=1):
                            for m in _GUI_TEXT_ATTR_RE.finditer(line):
                                attr, key = m.group(1), m.group(2)
                                if attr not in _GUI_LOC_ATTRS:
                                    continue
                                by_key.setdefault(key, []).append({
                                    "file": rel,
                                    "line": line_no,
                                    "attr": attr,
                                    "expression": m.group(0),
                                })
                            if "[" in line:
                                # Walk each `[...]` expression; scan for
                                # DataType.Method refs inside (handles nested
                                # calls like Not(StringIsEmpty(Article.GetX))).
                                for outer in srv._LOC_EXPR_RE.finditer(line):
                                    body = outer.group(1)
                                    for m in _GUI_DATAREF_RE.finditer(body):
                                        dtype, method = m.group(1), m.group(2)
                                        by_method.setdefault((dtype, method), []).append({
                                            "file": rel,
                                            "line": line_no,
                                            "expression": f"[...{dtype}.{method}...]",
                                        })
                except OSError:
                    continue
    return {"by_key": by_key, "by_method": by_method}


def _get_gui_render_index() -> dict:
    """Return the cached GUI render index, building it on first access. Scans
    vanilla `<base>/game/gui/` AND mod `<mod_path>/gui/`."""
    srv = server_state()
    if srv._GUI_RENDER_INDEX is None:
        srv._GUI_RENDER_INDEX = _build_gui_render_index([
            (os.path.join(srv.base_game_path, "game", "gui"), srv.base_game_path),
            (os.path.join(srv.mod_path, "gui"), srv.mod_path),
        ])
    return srv._GUI_RENDER_INDEX


class GuiRoutes:
    """GET /gui and its sub-routes. A mixin of ModStateHandler."""

    # ---- GUI render-site lookup --------------------------------------------
    def _gui_placeholder_textures(self, params):
        """GET /gui/placeholder-textures[?include_overrides=true&unlisted_only=true&file=<gui/…>&format=text]
        (#1484): vanilla textures the mod's own GUI widgets draw, and the icons doc that accounts for each."""
        srv = server_state()
        import gui_placeholder_textures as gpt
        import texture_reference_audit as tra

        def flag(name):
            return (params.get(name) or ["false"])[0].lower() in ("1", "true", "yes")

        try:
            vanilla_gui = gpt.load_gui_files(srv.mod_path)
        except FileNotFoundError:
            raise srv._ServiceNotReady({
                "error": f"{gpt.GUI_FILES_REL} is missing",
                "hint": "Write it on the machine with the game: python3 texture_reference_audit.py --bootstrap",
            })
        index, _stale = tra.build_index(srv.mod_path)

        def resolve(path):
            status = index.resolve_path(path)[0]
            return status if status in ("mod", "vanilla") else "vanilla" if status == "dlc_only" else "missing"

        files = params.get("file")
        if files:
            known = set(gpt.mod_gui_files(srv.mod_path))
            unknown = [f for f in files if f not in known]
            if unknown:
                raise srv.NotFound(unknown[0], did_you_mean=difflib.get_close_matches(unknown[0], sorted(known), n=5))
        body = gpt.report(srv.mod_path, vanilla_gui, resolve, include_overrides=flag("include_overrides"),
                          unlisted_only=flag("unlisted_only"), files=files or None)
        body["vanilla_source"] = index.source
        try:
            body["gui_file_list_stale"] = gpt.list_is_stale(srv.base_game_path if srv._vanilla_tree_present() else None,
                                                             srv.mod_path)
        except RuntimeError:
            body["gui_file_list_stale"] = None
        if (params.get("format") or [""])[0] == "text":
            return {"text": gpt.render_text(body), "summary": body["summary"]}
        return body

    def _gui(self, parts, params):
        """GET /gui/render-sites/<loc_key>
        GET /gui/render-paths/<EntityType>?field=<role>
        GET /gui/placeholder-textures (#1484, gui_placeholder_textures.py)

        The first two endpoints under the /gui/ prefix:
        - render-sites: every GUI file:line that quotes <loc_key> as a known
          localized attr (text/tooltip/raw_text/...).
        - render-paths: every GUI file:line that renders <field> of an entity
          via [DataType.GetX]. Resolves EntityType -> DataType via
          ENTITY_TYPE_TO_DATATYPE, field -> {GetX, ...} via FIELD_TO_METHODS.

        Both share a single lazily-built GUI index covering mod + vanilla.
        """
        srv = server_state()
        if not parts:
            raise srv.BadRequest(
                "Usage: /gui/render-sites/<loc_key>, /gui/render-paths/<EntityType>?field=<role> "
                "or /gui/placeholder-textures",
                supported_fields=sorted(FIELD_TO_METHODS.keys()),
                supported_entity_types=sorted(ENTITY_TYPE_TO_DATATYPE.keys()),
            )
        sub = parts[0]
        if sub == "placeholder-textures":
            return self._gui_placeholder_textures(params)
        index = _get_gui_render_index()

        if sub == "render-sites":
            if len(parts) < 2:
                raise srv.BadRequest("Usage: /gui/render-sites/<loc_key>")
            key = parts[1]
            sites = index["by_key"].get(key, [])
            return {"key": key, "sites": sites, "count": len(sites)}

        if sub == "render-paths":
            if len(parts) < 2:
                raise srv.BadRequest(
                    "Usage: /gui/render-paths/<EntityType>?field=<role>",
                    supported_entity_types=sorted(ENTITY_TYPE_TO_DATATYPE.keys()),
                    supported_fields=sorted(FIELD_TO_METHODS.keys()),
                )
            etype = parts[1]
            field = (params.get("field") or ["name"])[0]
            datatype = ENTITY_TYPE_TO_DATATYPE.get(etype)
            if datatype is None:
                raise srv._EndpointError({
                    "error": f"No GUI datatype mapped for entity type {etype!r}",
                    "supported_entity_types": sorted(ENTITY_TYPE_TO_DATATYPE.keys()),
                    "hint": "Add an entry to ENTITY_TYPE_TO_DATATYPE in mod_state_server.py to extend.",
                }, 404)
            methods = FIELD_TO_METHODS.get(field)
            if methods is None:
                raise srv.BadRequest(
                    f"Unknown field {field!r}",
                    supported_fields=sorted(FIELD_TO_METHODS.keys()),
                )
            sites: list[dict] = []
            matched: set[str] = set()
            for method in methods:
                hits = index["by_method"].get((datatype, method))
                if not hits:
                    continue
                matched.add(method)
                for hit in hits:
                    sites.append({**hit, "method": method})
            return {
                "entity_type": etype,
                "datatype": datatype,
                "field": field,
                "methods_matched": sorted(matched),
                "sites": sites,
                "count": len(sites),
            }

        raise srv.NotFound(sub)
