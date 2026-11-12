"""Render engine documentation logs into grep-able reference files.

Consumes the structured `engine_docs` dict produced by mod_state_server's
`_parse_*_log` parsers and writes Markdown / pipe-delimited summaries into
`docs/`. Auto-regenerated on startup and `/reload`; do not hand-edit the
output files.

Public API:
    render_all(engine_docs, mod_state, pattern_index, out_dir, source_paths)

Where:
    engine_docs: dict with keys "effects", "triggers", "modifiers",
                 "event-targets", "on-actions", "custom-localization", each
                 mapping to a list[dict] in the format produced by
                 mod_state_server._parse_*_log.
    mod_state:   ModState instance — used only for the modifier pattern
                 reference to look up vocabulary names. Pass None to skip
                 vocabulary expansion.
    pattern_index: optional dict from §3 (pattern catalog). Pass None to
                 fall back to a flat-by-mask listing.
    out_dir:     directory to write into (typically `docs/`).
    source_paths: dict mapping engine_docs key -> filesystem path of the
                 source `.log`; the version in its directory name (e.g.
                 `.../1.14.4/docs/`) goes into the auto-generated headers.

Command line: `python3 engine_docs_render.py` re-renders `docs/engine/` with no
server running, through the server's own loader (`_cli` below), so the result
is what a server start writes.
"""
from __future__ import annotations

import os
import re
from collections import defaultdict


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------
# A dotted version in the source path — `.../vic3-engine-docs/1.14.4/docs/` or
# `.../Modding-Digests/1.14.4/docs/`. Headers name it instead of the log's
# mtime, so re-copying or re-dumping an unchanged snapshot rewrites no file.
_VERSION_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")


def _source_version(path: str | None) -> str | None:
    """The last dotted version token in `path`'s directory, or None."""
    if not path:
        return None
    matches = _VERSION_RE.findall(os.path.dirname(path))
    return matches[-1] if matches else None


def _source_label(logs: str, version: str | None) -> str:
    return f"{logs} (engine docs {version})" if version else logs


# ---------------------------------------------------------------------------
# Triggers / effects: scope grouping (carried over from parse_triggers_effects.py)
# ---------------------------------------------------------------------------
SCOPE_MAP = {
    "country": "Country",
    "state": "State",
    "state_region": "State Region",
    "pop": "Pop",
    "building": "Building",
    "character": "Character",
    "market": "Market",
    "market_goods": "Market Goods",
    "state_goods": "State Goods",
    "interest_group": "Interest Group",
    "political_movement": "Political Movement",
    "political_lobby": "Political Lobby",
    "party": "Party",
    "culture": "Culture",
    "religion": "Religion",
    "war": "War",
    "diplomatic_play": "Diplomatic Play",
    "diplomatic_pact": "Diplomatic Pact",
    "diplomatic_catalyst": "Diplomatic Catalyst",
    "military_formation": "Military Formation",
    "front": "Front",
    "battle": "Battle",
    "battle_side": "Battle Side",
    "theater": "Theater",
    "power_bloc": "Power Bloc",
    "company": "Company",
    "law": "Law",
    "law_type": "Law Type",
    "journal_entry": "Journal Entry",
    "treaty": "Treaty",
    "treaty_article": "Treaty Article",
    "treaty_options": "Treaty",
    "treaty_article_options": "Treaty Article",
    "goods": "Goods",
    "new_combat_unit": "Combat Unit",
    "province": "Province",
    "strategic_region": "Strategic Region",
    "civil_war": "Civil War",
    "amendment": "Amendment",
    "amendment_type": "Amendment",
    "country_formation": "Country Formation",
    "country_definition": "Country Definition",
    "interest_marker": "Interest Marker",
    "invasion": "Invasion",
    "harvest_condition": "Harvest Condition",
    "hq": "HQ",
    "institution": "Institution",
}

_SCOPE_PRIORITY = [
    "Global / Logic", "Country", "State", "State Region", "Pop", "Building",
    "Character", "Market", "Market Goods", "State Goods", "Interest Group",
    "Political Movement", "Political Lobby", "Party", "Culture", "Religion",
    "War", "Diplomatic Play", "Diplomatic Pact", "Diplomatic Catalyst",
    "Military Formation", "Front", "Battle", "Battle Side", "Theater",
    "Power Bloc", "Company", "Law", "Law Type", "Journal Entry",
    "Treaty", "Treaty Article", "Goods", "Combat Unit", "Province",
    "Strategic Region", "Civil War", "Amendment", "Country Formation",
    "Country Definition", "Interest Marker", "Invasion", "Harvest Condition",
    "HQ", "Institution",
]

_REGIONAL_ITER_RE = re.compile(
    r"^(?:any|every|random|ordered)_(country|state|province|state_region|strategic_region)_in_(\w+)$"
)


def _is_regional_iterator(name: str) -> bool:
    return bool(_REGIONAL_ITER_RE.match(name))


_REGIONAL_ITER_NOUNS = {
    "country": "countries",
    "state": "states",
    "province": "provinces",
    "state_region": "state regions",
    "strategic_region": "strategic regions",
}
REGIONAL_ITERATOR_NOTE = (
    "Regional iterators (<any|every|random|ordered>_<type>_in_<geographic_region>) carry a "
    "fixed description: the engine dump prints unrelated script there, reshuffled on every dump."
)


def _regional_iterator_desc(name: str) -> str:
    m = _REGIONAL_ITER_RE.match(name)
    return f"Iterate through all {_REGIONAL_ITER_NOUNS[m.group(1)]} in geographic region {m.group(2)}"


def _description(entry: dict) -> str:
    """The entry's description, except a regional iterator's, which the engine
    dump fills with unrelated script (a random scripted trigger's body,
    sometimes raw memory) that changes on every dump."""
    name = entry.get("name", "")
    if _is_regional_iterator(name):
        return _regional_iterator_desc(name)
    return entry.get("description") or ""


def _primary_scope(scope_field) -> str:
    if not scope_field:
        return "Global / Logic"
    if isinstance(scope_field, list):
        if not scope_field:
            return "Global / Logic"
        first = scope_field[0]
    elif isinstance(scope_field, str):
        first = scope_field.split(",")[0].strip()
        if not first or first == "none":
            return "Global / Logic"
    else:
        return "Global / Logic"
    return SCOPE_MAP.get(first, first.replace("_", " ").title())


def _compact_desc(desc: str, max_len: int = 200) -> str:
    if not desc:
        return ""
    desc = desc.replace("\n", " ").strip()
    # Cut at first sentence break or usage example
    for sep in [". ", " = {", " = <"]:
        pos = desc.find(sep)
        if 5 < pos < len(desc) - 5:
            if sep == ". ":
                desc = desc[: pos + 1]
            else:
                desc = desc[:pos].rstrip()
            break
    eq_match = re.search(r"\s+[a-z_]+\s*[=><]+\s", desc)
    if eq_match and eq_match.start() > 15:
        desc = desc[: eq_match.start()].rstrip()
    if len(desc) > max_len:
        desc = desc[: max_len - 3] + "..."
    return desc


# ---------------------------------------------------------------------------
# Triggers / effects: full Markdown reference
# ---------------------------------------------------------------------------
def render_triggers_effects_reference(
    triggers: list[dict],
    effects: list[dict],
    source_version: str | None = None,
) -> str:
    """Build the full vic3_triggers_effects_reference.md content."""
    triggers_filtered = [t for t in triggers if not _is_regional_iterator(t.get("name", ""))]
    effects_filtered = [e for e in effects if not _is_regional_iterator(e.get("name", ""))]

    iterator_bases: dict[str, dict] = {}
    plain_triggers: list[dict] = []
    plain_effects: list[dict] = []

    for entry in triggers_filtered:
        name = entry.get("name", "")
        m = re.match(r"^any_(.+)$", name)
        targets = entry.get("targets") or []
        if m and targets:
            base = m.group(1)
            slot = iterator_bases.setdefault(
                base,
                {"scope": entry.get("scopes", []), "target": targets[0],
                 "desc": entry.get("description", ""), "prefixes": set()},
            )
            slot["prefixes"].add("any")
            new_desc = entry.get("description", "")
            if new_desc and len(new_desc) > len(slot["desc"]):
                slot["desc"] = new_desc
        else:
            plain_triggers.append(entry)

    for entry in effects_filtered:
        name = entry.get("name", "")
        matched = False
        for prefix, prefix_len in [("every_", 6), ("random_", 7), ("ordered_", 8)]:
            if name.startswith(prefix):
                base = name[prefix_len:]
                slot = iterator_bases.setdefault(
                    base,
                    {"scope": entry.get("scopes", []), "target": (entry.get("targets") or [""])[0],
                     "desc": entry.get("description", ""), "prefixes": set()},
                )
                slot["prefixes"].add(prefix.rstrip("_"))
                matched = True
                break
        if not matched:
            plain_effects.append(entry)

    trigger_by_scope = defaultdict(list)
    effect_by_scope = defaultdict(list)
    iterator_by_scope = defaultdict(list)
    for entry in plain_triggers:
        trigger_by_scope[_primary_scope(entry.get("scopes"))].append(entry)
    for entry in plain_effects:
        effect_by_scope[_primary_scope(entry.get("scopes"))].append(entry)
    for base, data in iterator_bases.items():
        iterator_by_scope[_primary_scope(data["scope"])].append((base, data))

    all_scopes = (
        set(trigger_by_scope.keys())
        | set(effect_by_scope.keys())
        | set(iterator_by_scope.keys())
    )
    ordered = [s for s in _SCOPE_PRIORITY if s in all_scopes]
    leftover = sorted(all_scopes - set(ordered))
    ordered.extend(leftover)

    out: list[str] = []
    # Header (Markdown comment so it doesn't render visibly)
    src_label = _source_label("triggers.log + effects.log", source_version)
    out.append(f"<!-- Auto-generated from {src_label}. Do not hand-edit. "
               "Run POST /reload after the engine regenerates the source. -->")
    out.append("")
    out.append("# Victoria 3 — Triggers & Effects Compressed Reference")
    out.append("")
    out.append(
        f"*Auto-generated from {len(triggers)} trigger entries and {len(effects)} effect entries.*"
    )
    out.append(
        f"*{len(iterator_bases)} iterator families, {len(plain_triggers)} standalone triggers, "
        f"{len(plain_effects)} standalone effects.*"
    )
    out.append("")

    out.append("## Reading Guide")
    out.append("")
    out.append("| Symbol | Meaning |")
    out.append("|--------|---------|")
    out.append("| **Scope:** | Entity that must be current scope for this to work |")
    out.append("| `[cmp]` | Supports comparison operators: `<, <=, =, !=, >, >=` |")
    out.append("| `[yes/no]` | Boolean trigger |")
    out.append("| `→ type` | Target scope type for iterators / scope targets |")
    out.append("| **(scopes: x, y)** | Works in multiple scope types |")
    out.append("")
    out.append("**Iterator pattern:** for each scope iteration, four variants exist:")
    out.append("- `any_X = { ... }` — **Trigger**: true if ≥1 entity matches inner triggers (supports `count = num/all`, `percent = fixed_point`)")
    out.append("- `every_X = { ... }` — **Effect**: runs inner effects on ALL matching entities (supports `limit = { triggers }`)")
    out.append("- `random_X = { ... }` — **Effect**: picks ONE random matching entity (supports `limit`, `weight`)")
    out.append("- `ordered_X = { ... }` — **Effect**: picks entity by sort order (supports `limit`, `order_by`, `position`, `min/max`)")
    out.append("")
    out.append("**Regional iterators** (`any/every/random/ordered_(country|state|province|state_region|strategic_region)_in_<region>`) are filtered out — apply the pattern to any vanilla region.")
    out.append("")

    for scope_name in ordered:
        t_list = trigger_by_scope.get(scope_name, [])
        e_list = effect_by_scope.get(scope_name, [])
        i_list = iterator_by_scope.get(scope_name, [])
        if not t_list and not e_list and not i_list:
            continue
        out.append("---")
        out.append(f"## {scope_name}")
        out.append("")
        if i_list:
            out.append(f"### Iterators ({len(i_list)})")
            out.append("")
            for base, data in sorted(i_list, key=lambda x: x[0]):
                prefixes = "/".join(sorted(data["prefixes"]))
                target = data["target"] or ""
                desc = _compact_desc(data["desc"], 150)
                scope_field = data["scope"]
                if isinstance(scope_field, list):
                    scope_str = ", ".join(scope_field)
                else:
                    scope_str = str(scope_field) if scope_field else ""
                scope_note = f" (scopes: {scope_str})" if scope_str and "," in scope_str else ""
                line = f"- `{prefixes}_{base}` → {target}{scope_note}"
                if desc:
                    line += f" — {desc}"
                out.append(line)
            out.append("")
        for label, entries in [("Triggers", t_list), ("Effects", e_list)]:
            if not entries:
                continue
            out.append(f"### {label} ({len(entries)})")
            out.append("")
            for entry in sorted(entries, key=lambda x: x.get("name", "")):
                desc = _compact_desc(entry.get("description", ""), 200)
                scopes = entry.get("scopes") or []
                targets = entry.get("targets") or []
                scope_str = ", ".join(scopes) if isinstance(scopes, list) else str(scopes)
                line = f"- `{entry.get('name', '')}`"
                if desc:
                    line += f" — {desc}"
                extras = []
                if targets:
                    extras.append(f"→ {targets[0]}")
                if scope_str and "," in scope_str:
                    extras.append(f"(scopes: {scope_str})")
                if extras:
                    line += " " + " ".join(extras)
                out.append(line)
            out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Modifiers: per-scope reference + pattern-aware sectioning
# ---------------------------------------------------------------------------
def render_modifiers_reference(
    modifiers: list[dict],
    pattern_index: dict | None,
    source_version: str | None = None,
) -> str:
    """Render vic3_modifier_type_definitions_reference.md.

    pattern_index has shape {pattern_str: {placeholder_value: entry}}; if
    provided, modifiers that match a pattern are grouped under their pattern.
    Modifiers not in any pattern are listed flat under their mask section.
    """
    out: list[str] = []
    src_label = _source_label("modifiers.log", source_version)
    out.append(f"<!-- Auto-generated from {src_label}. Do not hand-edit. "
               "Run POST /reload after the engine regenerates the source. -->")
    out.append("")
    out.append("# Victoria 3 — Modifier Type Definitions Reference")
    out.append("")
    out.append(f"*Auto-generated from {len(modifiers)} modifier entries.*")
    out.append("")

    name_to_entry = {m.get("name", ""): m for m in modifiers}
    grouped_into_pattern: set[str] = set()
    pattern_blocks: list[tuple[str, list[str]]] = []  # (pattern, sorted_member_names)

    if pattern_index:
        for pattern, members in pattern_index.items():
            member_names = sorted(members.keys())
            if not member_names:
                continue
            for placeholder_value, entry in members.items():
                # entry might be a placeholder dict referencing a name:
                ref_name = entry.get("name") if isinstance(entry, dict) else None
                if ref_name:
                    grouped_into_pattern.add(ref_name)
                else:
                    # If we only have placeholder values, derive the concrete name
                    concrete = pattern.replace("{" + _placeholder_name(pattern) + "}", placeholder_value)
                    grouped_into_pattern.add(concrete)
            pattern_blocks.append((pattern, member_names))

    # By-mask section
    by_mask: dict[str, list[dict]] = defaultdict(list)
    for m in modifiers:
        name = m.get("name", "")
        if name in grouped_into_pattern:
            continue
        mask = m.get("mask", "") or "(no mask)"
        by_mask[mask].append(m)

    if pattern_blocks:
        out.append("## Dynamic Patterns")
        out.append("")
        out.append("Modifier names parameterized over a vocabulary (good, building, IG, etc.). "
                   "Members are listed compactly; query `/modifier-patterns/<pattern>` for full detail.")
        out.append("")
        for pattern, members in sorted(pattern_blocks):
            out.append(f"### `{pattern}` ({len(members)} members)")
            out.append("")
            # Resolve each placeholder value back to its concrete modifier name
            # so the listing is greppable.
            token = _placeholder_name(pattern)
            full_names = sorted(
                pattern.replace("{" + token + "}", v) for v in members
            )
            example = _example_member(pattern, full_names, name_to_entry)
            if example and example.get("description"):
                out.append(f"_{_compact_desc(example['description'], 200)}_")
                out.append("")
            # List in compact form
            chunked = [full_names[i:i + 6] for i in range(0, len(full_names), 6)]
            for chunk in chunked:
                out.append("- " + ", ".join(f"`{n}`" for n in chunk))
            out.append("")

    out.append("## By Mask")
    out.append("")
    for mask in sorted(by_mask.keys()):
        entries = by_mask[mask]
        out.append(f"### {mask} ({len(entries)})")
        out.append("")
        for entry in sorted(entries, key=lambda e: e.get("name", "")):
            name = entry.get("name", "")
            display = entry.get("display_name", "")
            desc = _compact_desc(entry.get("description", ""), 160)
            line = f"- `{name}`"
            if display:
                line += f" — **{display}**"
            if desc:
                line += f" — {desc}"
            out.append(line)
        out.append("")
    return "\n".join(out) + "\n"


def _placeholder_name(pattern: str) -> str:
    m = re.search(r"\{(\w+)\}", pattern)
    return m.group(1) if m else "name"


def _example_member(pattern: str, member_names: list[str], name_to_entry: dict) -> dict | None:
    for name in member_names:
        if name in name_to_entry:
            return name_to_entry[name]
    return None


# ---------------------------------------------------------------------------
# Modifier patterns Markdown (separate from the reference above)
# ---------------------------------------------------------------------------
def render_modifier_patterns(
    pattern_catalog: list[dict],
    pattern_index: dict,
    discovered_patterns: list[dict] | None = None,
    vocabularies: dict | None = None,
    source_version: str | None = None,
) -> str:
    """Render docs/engine/modifier_patterns.md.

    pattern_catalog: list of catalog entries from common/_meta/modifier_patterns.yml.
    pattern_index: {pattern_str: {placeholder_value: entry}}.
    discovered_patterns: list of {pattern, placeholder, vocab, members} for
        auto-discovered patterns not in the catalog.
    vocabularies: {placeholder_name: [valid_values]} for missing-value computation.
    """
    out: list[str] = []
    src_label = _source_label("modifiers.log", source_version) + " + common/_meta/modifier_patterns.yml"
    out.append(f"<!-- Auto-generated from {src_label}. Do not hand-edit. "
               "Run POST /reload after the engine regenerates the source. -->")
    out.append("")
    out.append("# Modifier Patterns")
    out.append("")
    out.append("Dynamic-modifier templates parameterized over canonical vocabularies "
               "(goods, buildings, IGs, etc.). The catalog in "
               "`common/_meta/modifier_patterns.yml` lists patterns we guarantee tracking; "
               "the discovery pass below extends that with patterns inferred from engine docs.")
    out.append("")

    catalog_patterns = {entry["pattern"]: entry for entry in pattern_catalog}
    out.append(f"## Catalog ({len(catalog_patterns)} patterns)")
    out.append("")
    for pattern in sorted(catalog_patterns.keys()):
        cat = catalog_patterns[pattern]
        members = pattern_index.get(pattern, {})
        vocab_name = cat.get("vocab", "")
        vocab_values = (vocabularies or {}).get(vocab_name, []) or []
        present = set(members.keys())
        missing = sorted(set(vocab_values) - present)
        out.append(f"### `{pattern}`")
        out.append("")
        if cat.get("notes"):
            out.append(f"_{cat['notes']}_")
            out.append("")
        out.append(f"- Placeholder: `{cat.get('placeholder', '?')}` (vocab: `{vocab_name}`)")
        out.append(f"- Members in engine docs: **{len(members)}**")
        if vocab_values:
            out.append(f"- Vocab size: {len(vocab_values)}; missing entries: {len(missing)}")
            if missing and len(missing) <= 25:
                out.append(f"  - Missing values: {', '.join(f'`{v}`' for v in missing)}")
        out.append("")

    if discovered_patterns:
        out.append(f"## Discovered (not yet in catalog) — {len(discovered_patterns)} patterns")
        out.append("")
        out.append("These patterns were auto-detected by matching engine modifiers against "
                   "loaded vocabulary values. Review and promote desired ones into "
                   "`common/_meta/modifier_patterns.yml`.")
        out.append("")
        for d in sorted(discovered_patterns, key=lambda x: x["pattern"]):
            out.append(f"### `{d['pattern']}`")
            out.append("")
            out.append(f"- Placeholder: `{d.get('placeholder', '?')}` (vocab: `{d.get('vocab', '?')}`)")
            out.append(f"- Members: **{len(d.get('members', []))}**")
            if d.get("members"):
                preview = sorted(d["members"])[:6]
                out.append(f"  - Examples: {', '.join(f'`{m}`' for m in preview)}")
            out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Plain pipe-delimited summaries
# ---------------------------------------------------------------------------
def render_summary_triggers_effects(entries: list[dict]) -> str:
    lines = []
    for entry in sorted(entries, key=lambda e: e.get("name", "")):
        name = entry.get("name", "")
        scopes = entry.get("scopes") or []
        scope_str = ",".join(scopes) if isinstance(scopes, list) else str(scopes)
        desc = _compact_desc(_description(entry), 150)
        lines.append(f"{scope_str}|{name}|{desc}")
    return "\n".join(lines) + "\n"


def render_summary_modifiers(entries: list[dict]) -> str:
    lines = []
    for entry in sorted(entries, key=lambda e: e.get("name", "")):
        name = entry.get("name", "")
        mask = entry.get("mask", "")
        desc = _compact_desc(entry.get("description", ""), 150)
        lines.append(f"{mask}|{name}|{desc}")
    return "\n".join(lines) + "\n"


def render_summary_event_targets(entries: list[dict]) -> str:
    lines = []
    for entry in sorted(entries, key=lambda e: e.get("name", "")):
        name = entry.get("name", "")
        ins = ",".join(entry.get("input_scopes") or [])
        outs = ",".join(entry.get("output_scopes") or [])
        desc = _compact_desc(entry.get("description", ""), 150)
        lines.append(f"{ins}|{name}|{outs}|{desc}")
    return "\n".join(lines) + "\n"


def render_summary_on_actions(entries: list[dict]) -> str:
    lines = []
    for entry in sorted(entries, key=lambda e: e.get("name", "")):
        name = entry.get("name", "")
        scopes = ",".join(entry.get("scopes") or [])
        from_code = "yes" if entry.get("from_code") else "no"
        lines.append(f"{name}|{scopes}|from_code={from_code}")
    return "\n".join(lines) + "\n"


def render_summary_custom_localization(entries: list[dict]) -> str:
    lines = []
    for entry in sorted(entries, key=lambda e: e.get("name", "")):
        name = entry.get("name", "")
        scopes = ",".join(entry.get("scopes") or [])
        random_valid = "yes" if entry.get("random_valid") else "no"
        lines.append(f"{scopes}|{name}|random_valid={random_valid}")
    return "\n".join(lines) + "\n"


def render_country_triggers(triggers: list[dict]) -> str:
    """Country-scope triggers with descriptions, sorted alphabetically."""
    lines = []
    for entry in sorted(triggers, key=lambda e: e.get("name", "")):
        scopes = entry.get("scopes") or []
        if "country" not in (scopes if isinstance(scopes, list) else [scopes]):
            continue
        name = entry.get("name", "")
        desc = _compact_desc(_description(entry), 200)
        lines.append(f"{name}: {desc}")
    return "\n".join(lines) + "\n"


def render_triggers_parsed(triggers: list[dict]) -> str:
    """Full parsed triggers, one per block, with examples and traits if present."""
    out = []
    for entry in sorted(triggers, key=lambda e: e.get("name", "")):
        name = entry.get("name", "")
        scopes = ", ".join(entry.get("scopes") or []) or "(none)"
        targets = ", ".join(entry.get("targets") or [])
        desc = _description(entry).strip()
        out.append(f"## {name}")
        out.append(f"Scopes: {scopes}")
        if targets:
            out.append(f"Targets: {targets}")
        if desc:
            out.append("")
            out.append(desc)
        out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Public driver: write everything to disk
# ---------------------------------------------------------------------------
def render_all(
    engine_docs: dict,
    out_dir: str,
    pattern_catalog: list[dict] | None = None,
    pattern_index: dict | None = None,
    discovered_patterns: list[dict] | None = None,
    vocabularies: dict | None = None,
    source_paths: dict | None = None,
) -> dict:
    """Write all engine-doc reference files into `out_dir`.

    Returns a dict {filename: bytes_written} for logging.
    """
    os.makedirs(out_dir, exist_ok=True)
    written: dict[str, int] = {}

    def _write(name: str, content: str):
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        written[name] = len(content)

    triggers = engine_docs.get("triggers", []) or []
    effects = engine_docs.get("effects", []) or []
    # The server unions the mod's own modifier types and custom localization
    # into engine_docs with origin="mod" before rendering. These files are the
    # engine's reference, so they list only what the script_docs dump carries.
    # Including the union churned them on every /reload, and a vanilla bump
    # that committed them (39cf48af9) failed the tests asserting a script-only
    # mod type is absent from the engine list.
    modifiers = [
        e for e in (engine_docs.get("modifiers", []) or []) if e.get("origin") != "mod"
    ]
    event_targets = engine_docs.get("event-targets", []) or []
    on_actions = engine_docs.get("on-actions", []) or []
    custom_loc = [
        e for e in (engine_docs.get("custom-localization", []) or [])
        if e.get("origin") != "mod"
    ]

    src = source_paths or {}
    triggers_version = _source_version(src.get("triggers"))
    effects_version = _source_version(src.get("effects"))
    modifiers_version = _source_version(src.get("modifiers"))

    # Markdown references
    _write(
        "vic3_triggers_effects_reference.md",
        render_triggers_effects_reference(triggers, effects, triggers_version or effects_version),
    )
    _write(
        "vic3_modifier_type_definitions_reference.md",
        render_modifiers_reference(modifiers, pattern_index, modifiers_version),
    )

    # Pipe-delimited summaries
    _write(
        "triggers_summary.txt",
        _txt_header("triggers.log", triggers_version, REGIONAL_ITERATOR_NOTE)
        + render_summary_triggers_effects(triggers),
    )
    _write(
        "effects_summary.txt",
        _txt_header("effects.log", effects_version, REGIONAL_ITERATOR_NOTE)
        + render_summary_triggers_effects(effects),
    )
    _write("modifiers_summary.txt", _txt_header("modifiers.log", modifiers_version) + render_summary_modifiers(modifiers))
    _write(
        "event_targets_summary.txt",
        _txt_header("event_targets.log", _source_version(src.get("event-targets")))
        + render_summary_event_targets(event_targets),
    )
    _write(
        "on_actions_summary.txt",
        _txt_header("on_actions.log", _source_version(src.get("on-actions")))
        + render_summary_on_actions(on_actions),
    )
    _write(
        "custom_localization_summary.txt",
        _txt_header("custom_localization.log", _source_version(src.get("custom-localization")))
        + render_summary_custom_localization(custom_loc),
    )

    # Existing-format files (kept for greppability)
    _write(
        "country_triggers.txt",
        _txt_header("triggers.log", triggers_version) + render_country_triggers(triggers),
    )
    _write(
        "triggers_parsed.txt",
        _txt_header("triggers.log", triggers_version, REGIONAL_ITERATOR_NOTE) + render_triggers_parsed(triggers),
    )

    # Modifier patterns
    if pattern_catalog is not None:
        _write(
            "modifier_patterns.md",
            render_modifier_patterns(
                pattern_catalog,
                pattern_index or {},
                discovered_patterns,
                vocabularies,
                modifiers_version,
            ),
        )

    return written


def _txt_header(logs: str, version: str | None, note: str | None = None) -> str:
    out = (
        f"# Auto-generated from {_source_label(logs, version)}. "
        f"Do not hand-edit. Run POST /reload after the engine regenerates the source.\n"
    )
    if note:
        out += f"# {note}\n"
    return out + "\n"


# ---------------------------------------------------------------------------
# Command line: render docs/engine/ the way a server start does
# ---------------------------------------------------------------------------
def _cli(argv: list[str] | None = None) -> int:
    """`python3 engine_docs_render.py`: re-render docs/engine/ with no server.

    Runs the server's own loader, `mod_state_server._load_engine_docs`, after
    the steps a cold start takes before it (the Modding-Digests pull, then the
    vanilla + mod parse), so the files are the ones a server start writes: from
    the source `_engine_docs_source` picks, with its version in every header
    and the dynamic-pattern grouping. It used to be a second code path that
    read `vanilla_docs_path`, the dump the game last wrote with whatever mods
    were on, and rendered with no pattern data: no versions, no
    `modifier_patterns.md`, an ungrouped modifier reference (#1592).

    Like the server, it leaves the files alone when the source can't reproduce
    them (`_engine_docs_render_blockers`). Returns the exit status: 0 when the
    files were written, 1 when they were not, with the reason on stderr.
    """
    import argparse
    import sys

    argparse.ArgumentParser(
        prog="engine_docs_render.py",
        description=(
            "Re-render the engine reference files in docs/engine/ exactly as a "
            "mod_state_server start does, without starting one. The source is "
            "`vanilla_snapshot_docs_path` if set, else the newest Modding-Digests "
            "version (the checkout is cloned or pulled first, as on a server "
            "start; VIC3_SKIP_DIGESTS_FETCH=1 skips that), else the dump the game "
            "last wrote. Exits 1 if nothing was rendered."
        ),
    ).parse_args(argv)

    # Imported here: the server imports this module for render_all.
    import mod_state_server as mss

    mss._ensure_modding_digests_fresh()
    mss._refresh_digest_snapshot_path()
    mss.ms = mss.cli_mod_state()
    written = mss._load_engine_docs()

    chosen_dir, source_label = mss._engine_docs_source()
    out_dir = os.path.join(mss.doc_path, "engine")
    print(f"Engine docs source: {source_label} ({chosen_dir})")
    for warning in mss._version_mismatch_warnings():
        print(f"WARNING: {warning.get('detail') or warning.get('error')}", file=sys.stderr)
    if mss._engine_docs_warnings:
        print(f"ERROR: {mss._engine_docs_warnings[0]['detail']}", file=sys.stderr)
        return 1
    if written is None:
        print(
            f"ERROR: the render failed, so {out_dir} may be half-written; the "
            "traceback is in the log lines above.",
            file=sys.stderr,
        )
        return 1
    if source_label == "mod_loaded":
        print(
            f"WARNING: rendered from {chosen_dir}, the dump the game last wrote, "
            "because there is no vanilla-only snapshot and no Modding-Digests "
            "version to read. A dump taken with mods on lists their modifier "
            "types as the engine's, and its path names no version for the "
            "headers. Set `vanilla_snapshot_docs_path` to a vanilla-only dump "
            "and run this again before committing the result.",
            file=sys.stderr,
        )
    for name, size in written.items():
        print(f"  {name}: {size:,} bytes")
    print(f"Done — wrote {len(written)} files to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
