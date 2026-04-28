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
                 source `.log`, used to embed mtimes in the auto-generated
                 headers.

The module also retains a `parse_log` shim for backwards-compat with the
old `docs/parse_triggers_effects.py` callers, but new code should use the
shared parsers in mod_state_server.
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------
def _auto_header(source_label: str, source_mtime: float | None, comment_prefix: str = "<!--") -> str:
    """Build a do-not-hand-edit header. comment_prefix='#' for plain-text outputs."""
    ts = "<unknown>"
    if source_mtime:
        ts = datetime.fromtimestamp(source_mtime, tz=timezone.utc).isoformat(timespec="seconds")
    msg = (
        f"Auto-generated from {source_label} at {ts}. "
        f"Do not hand-edit. Run POST /reload after the engine regenerates the source."
    )
    if comment_prefix == "#":
        return f"# {msg}\n\n"
    return f"{comment_prefix} {msg} -->\n\n"


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
    r"^(any|every|random|ordered)_(country|state|province|state_region|strategic_region)_in_\w+$"
)


def _is_regional_iterator(name: str) -> bool:
    return bool(_REGIONAL_ITER_RE.match(name))


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
    triggers_mtime: float | None = None,
    effects_mtime: float | None = None,
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
    sources = []
    if triggers_mtime:
        sources.append(f"triggers.log @ {datetime.fromtimestamp(triggers_mtime, tz=timezone.utc).isoformat(timespec='seconds')}")
    if effects_mtime:
        sources.append(f"effects.log @ {datetime.fromtimestamp(effects_mtime, tz=timezone.utc).isoformat(timespec='seconds')}")
    src_label = "; ".join(sources) if sources else "triggers.log + effects.log"
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
    modifiers_mtime: float | None = None,
) -> str:
    """Render vic3_modifier_type_definitions_reference.md.

    pattern_index has shape {pattern_str: {placeholder_value: entry}}; if
    provided, modifiers that match a pattern are grouped under their pattern.
    Modifiers not in any pattern are listed flat under their mask section.
    """
    out: list[str] = []
    src_label = "modifiers.log"
    if modifiers_mtime:
        src_label = f"modifiers.log @ {datetime.fromtimestamp(modifiers_mtime, tz=timezone.utc).isoformat(timespec='seconds')}"
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
    modifiers_mtime: float | None = None,
) -> str:
    """Render docs/modifier_patterns.md.

    pattern_catalog: list of catalog entries from common/_meta/modifier_patterns.yml.
    pattern_index: {pattern_str: {placeholder_value: entry}}.
    discovered_patterns: list of {pattern, placeholder, vocab, members} for
        auto-discovered patterns not in the catalog.
    vocabularies: {placeholder_name: [valid_values]} for missing-value computation.
    """
    out: list[str] = []
    src_label = "modifiers.log + common/_meta/modifier_patterns.yml"
    if modifiers_mtime:
        src_label += f" (modifiers.log @ {datetime.fromtimestamp(modifiers_mtime, tz=timezone.utc).isoformat(timespec='seconds')})"
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
        desc = _compact_desc(entry.get("description", ""), 150)
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
        desc = _compact_desc(entry.get("description", ""), 200)
        lines.append(f"{name}: {desc}")
    return "\n".join(lines) + "\n"


def render_triggers_parsed(triggers: list[dict]) -> str:
    """Full parsed triggers, one per block, with examples and traits if present."""
    out = []
    for entry in sorted(triggers, key=lambda e: e.get("name", "")):
        name = entry.get("name", "")
        scopes = ", ".join(entry.get("scopes") or []) or "(none)"
        targets = ", ".join(entry.get("targets") or [])
        desc = (entry.get("description") or "").strip()
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
    modifiers = engine_docs.get("modifiers", []) or []
    event_targets = engine_docs.get("event-targets", []) or []
    on_actions = engine_docs.get("on-actions", []) or []
    custom_loc = engine_docs.get("custom-localization", []) or []

    src = source_paths or {}
    triggers_mtime = _mtime(src.get("triggers"))
    effects_mtime = _mtime(src.get("effects"))
    modifiers_mtime = _mtime(src.get("modifiers"))

    # Markdown references
    _write(
        "vic3_triggers_effects_reference.md",
        render_triggers_effects_reference(triggers, effects, triggers_mtime, effects_mtime),
    )
    _write(
        "vic3_modifier_type_definitions_reference.md",
        render_modifiers_reference(modifiers, pattern_index, modifiers_mtime),
    )

    # Pipe-delimited summaries
    _write("triggers_summary.txt", _txt_header("triggers.log", triggers_mtime) + render_summary_triggers_effects(triggers))
    _write("effects_summary.txt", _txt_header("effects.log", effects_mtime) + render_summary_triggers_effects(effects))
    _write("modifiers_summary.txt", _txt_header("modifiers.log", modifiers_mtime) + render_summary_modifiers(modifiers))
    _write(
        "event_targets_summary.txt",
        _txt_header("event_targets.log", _mtime(src.get("event-targets")))
        + render_summary_event_targets(event_targets),
    )
    _write(
        "on_actions_summary.txt",
        _txt_header("on_actions.log", _mtime(src.get("on-actions")))
        + render_summary_on_actions(on_actions),
    )
    _write(
        "custom_localization_summary.txt",
        _txt_header("custom_localization.log", _mtime(src.get("custom-localization")))
        + render_summary_custom_localization(custom_loc),
    )

    # Existing-format files (kept for greppability)
    _write(
        "country_triggers.txt",
        _txt_header("triggers.log", triggers_mtime) + render_country_triggers(triggers),
    )
    _write(
        "triggers_parsed.txt",
        _txt_header("triggers.log", triggers_mtime) + render_triggers_parsed(triggers),
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
                modifiers_mtime,
            ),
        )

    return written


def _mtime(path: str | None) -> float | None:
    if not path:
        return None
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def _txt_header(source_label: str, source_mtime: float | None) -> str:
    ts = ""
    if source_mtime:
        ts = f" @ {datetime.fromtimestamp(source_mtime, tz=timezone.utc).isoformat(timespec='seconds')}"
    return (
        f"# Auto-generated from {source_label}{ts}. "
        f"Do not hand-edit. Run POST /reload after the engine regenerates the source.\n\n"
    )


# ---------------------------------------------------------------------------
# Backwards-compat: light wrapper for the old parse_triggers_effects.py CLI
# ---------------------------------------------------------------------------
def _cli():
    """Standalone fallback: regenerate from disk without the server."""
    import sys

    from path_constants import vanilla_docs_path, doc_path

    # Lazy import so the module doesn't require the server at import time
    from mod_state_server import (
        _parse_effects_triggers_log,
        _parse_modifiers_log,
        _parse_event_targets_log,
        _parse_on_actions_log,
        _parse_custom_localization_log,
    )

    sources = {
        "triggers": os.path.join(vanilla_docs_path, "triggers.log"),
        "effects": os.path.join(vanilla_docs_path, "effects.log"),
        "modifiers": os.path.join(vanilla_docs_path, "modifiers.log"),
        "event-targets": os.path.join(vanilla_docs_path, "event_targets.log"),
        "on-actions": os.path.join(vanilla_docs_path, "on_actions.log"),
        "custom-localization": os.path.join(vanilla_docs_path, "custom_localization.log"),
    }
    engine_docs = {
        "triggers": _parse_effects_triggers_log(sources["triggers"]),
        "effects": _parse_effects_triggers_log(sources["effects"]),
        "modifiers": _parse_modifiers_log(sources["modifiers"]),
        "event-targets": _parse_event_targets_log(sources["event-targets"]),
        "on-actions": _parse_on_actions_log(sources["on-actions"]),
        "custom-localization": _parse_custom_localization_log(sources["custom-localization"]),
    }
    written = render_all(engine_docs, doc_path, source_paths=sources)
    for name, size in written.items():
        print(f"  {name}: {size:,} bytes")
    print(f"Done — wrote {len(written)} files to {doc_path}")


if __name__ == "__main__":
    _cli()
