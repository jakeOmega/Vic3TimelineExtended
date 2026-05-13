"""Detects mod-introduced entities missing their conventional localization keys.

Background: Vic3 silently displays raw entity names when the corresponding
loc key is absent. The Clausewitz engine emits no warning, so an unlocalized
modifier (e.g. `prestige_loss_tiny`) leaks the raw key into player tooltips
without anything firing in the logs. This audit walks each
`mod_state.mod_parsers[type].data` (filtered to mod-only via subtraction from
`base_parsers[type].data`), derives the expected loc key(s), and flags any
that are missing from `mod_state.localization`.

Suppress an intentional missing loc key with a same-line comment on the
entity's opening line:

    prestige_loss_tiny = { # REVIEWED 2026-05-08: backwards-compat alias

Coverage: static modifiers, character traits, journal entries, laws, decrees,
scripted buttons, buildings, production methods, goods, company types,
combat unit types, ship types, ideologies, interest groups, institutions,
subject types, mobilization options, diplomatic actions, pop needs,
decisions, events. Skips scripted_effects/triggers, on_actions, modifier
type definitions, script values (most are arithmetic helpers — only those
referenced in `custom_tooltip` need loc, deferred until reports show gaps).
"""
import os
import re
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class LocFlag:
    category: str
    entity: str
    missing_keys: list[str]
    file: str
    line: int
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[LocFlag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


# The Paradox parser wraps every assignment as `('=', value)`. Strip that
# wrapping recursively before reading nested fields.
def _unwrap(value):
    if isinstance(value, tuple) and len(value) == 2 and value[0] in ("=", "?=", ">=", "<=", ">", "<", "!="):
        return _unwrap(value[1])
    return value


def _strip_quotes(s: str) -> str:
    """Many Paradox string values keep their surrounding quotes. Strip if
    they bracket the entire value."""
    if isinstance(s, str) and len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


# Loc-key derivation functions. Each takes (entity_name, entity_body_unwrapped)
# and returns list of (key, required, label). `required=False` keys are checked
# but a miss isn't flagged — they cover optional keys like `_desc` that mod
# authors may legitimately omit.
def _simple_name(name: str, body) -> list[tuple[str, bool, str]]:
    return [(name, True, "name")]


def _name_and_desc(name: str, body) -> list[tuple[str, bool, str]]:
    return [(name, True, "name"), (f"{name}_desc", False, "desc")]


def _je_keys(name: str, body) -> list[tuple[str, bool, str]]:
    return [
        (name, True, "title"),
        (f"{name}_desc", True, "desc"),
        (f"{name}_reason", False, "reason"),
    ]


def _explicit_name_field(name: str, body) -> list[tuple[str, bool, str]]:
    """For entities that declare loc via `name = "KEY"` and `desc = "KEY"`
    fields (scripted_buttons), not via the entity name itself."""
    keys: list[tuple[str, bool, str]] = []
    if not isinstance(body, dict):
        return keys
    n = _strip_quotes(_unwrap(body.get("name", "")))
    if isinstance(n, str) and n:
        keys.append((n, True, "name"))
    d = _strip_quotes(_unwrap(body.get("desc", "")))
    if isinstance(d, str) and d:
        keys.append((d, False, "desc"))
    return keys


# entity_type → derivation fn(name, body). Categories deliberately absent
# (code-only or noisy): Scripted Effects/Triggers, On Actions, Script Values.
#
# Modifier Types (the schema entries that register names like
# `country_X_add` for use in modifier blocks) are scanned here -- their loc
# key is the modifier name itself (shown in stat-panel hover) plus an
# optional `_desc`. A missing display name leaks the raw modifier name into
# every law/IG/building tooltip that declares it.
_REQUIREMENTS: dict[str, Callable[[str, object], list[tuple[str, bool, str]]]] = {
    "Modifiers":              _simple_name,
    "Modifier Types":         _name_and_desc,
    "Battle Conditions":      _name_and_desc,
    "Character Traits":       _name_and_desc,
    "Journal Entries":        _je_keys,
    "Laws":                   _name_and_desc,
    "Decrees":                _name_and_desc,
    "Scripted Buttons":       _explicit_name_field,
    "Buildings":              _name_and_desc,
    "PMs":                    _name_and_desc,
    "Goods":                  _simple_name,
    "Company Types":          _name_and_desc,
    "Combat Unit Types":      _simple_name,
    "Ship Types":             _simple_name,
    "Ideologies":             _simple_name,
    "Interest Groups":        _simple_name,
    "Institutions":           _simple_name,
    "Subject Types":          _simple_name,
    "Mobilization Options":   _name_and_desc,
    "Diplomatic Actions":     _simple_name,
    "Pop Needs":              _simple_name,
    "Decisions":              _name_and_desc,
}


# entity_type → mod source dir under mod_path (used for file-and-line scan
# and for finding the suppression comment on the entity's opening line).
_DIR_MAP: dict[str, str] = {
    "Modifiers":              "common/static_modifiers",
    "Modifier Types":         "common/modifier_type_definitions",
    "Battle Conditions":      "common/battle_conditions",
    "Character Traits":       "common/character_traits",
    "Journal Entries":        "common/journal_entries",
    "Laws":                   "common/laws",
    "Decrees":                "common/decrees",
    "Scripted Buttons":       "common/scripted_buttons",
    "Buildings":              "common/buildings",
    "PMs":                    "common/production_methods",
    "Goods":                  "common/goods",
    "Company Types":          "common/company_types",
    "Combat Unit Types":      "common/combat_unit_types",
    "Ship Types":             "common/ship_types",
    "Ideologies":             "common/ideologies",
    "Interest Groups":        "common/interest_groups",
    "Institutions":           "common/institutions",
    "Subject Types":          "common/subject_types",
    "Mobilization Options":   "common/mobilization_options",
    "Diplomatic Actions":     "common/diplomatic_actions",
    "Pop Needs":              "common/pop_needs",
    "Decisions":              "common/decisions",
    "Events":                 "events",
}


def _event_loc_keys(event_id: str, event_body) -> list[tuple[str, bool, str]]:
    """Read the explicit loc-key references from the event body.

    Vic3 events declare loc keys explicitly via `title = some_key`,
    `desc = some_key`, `flavor = some_key`, and per-option `name = some_key`.
    Reads what the event actually points to rather than guessing from the id.

    Returns an empty list for non-event entries (e.g. parser top-level
    `namespace = X` directives or events that declare no display fields).
    """
    keys: list[tuple[str, bool, str]] = []
    body = _unwrap(event_body)
    if not isinstance(body, dict):
        return keys
    # Skip non-event top-level entries from event files (e.g. `namespace`).
    # Real events declare a `type` field (country_event, state_event, etc.).
    if "type" not in body:
        return keys
    for fld in ("title", "desc", "flavor"):
        v = _strip_quotes(_unwrap(body.get(fld, "")))
        if isinstance(v, str) and v:
            keys.append((v, fld != "flavor", fld))
    options = body.get("option", [])
    if isinstance(options, tuple):
        options = _unwrap(options)
    if isinstance(options, dict):
        options = [options]
    if not isinstance(options, list):
        return keys
    for idx, opt in enumerate(options):
        opt = _unwrap(opt)
        if not isinstance(opt, dict):
            continue
        name = _strip_quotes(_unwrap(opt.get("name", "")))
        if isinstance(name, str) and name:
            keys.append((name, True, f"option_{idx}"))
    return keys


_OPENING_LINE_RE = re.compile(
    r"^[ \t]*(?P<name>[A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{(?P<comment>\s*#.*)?\s*$"
)


def _build_entity_locations(
    mod_path: str, dir_rel: str, entity_names: set[str]
) -> dict[str, tuple[str, int, str | None]]:
    """For each entity name, find (rel_path, line, opening_line_comment).

    Walks `<mod_path>/<dir_rel>` recursively. Comment carries the trailing
    `# ...` on the entity-opening line, used for REVIEWED suppression.
    """
    abs_dir = os.path.join(mod_path, dir_rel)
    locations: dict[str, tuple[str, int, str | None]] = {}
    if not os.path.isdir(abs_dir):
        return locations
    for root, _dirs, files in os.walk(abs_dir):
        for fname in sorted(files):
            if not fname.endswith(".txt"):
                continue
            abs_p = os.path.join(root, fname)
            rel_p = os.path.relpath(abs_p, mod_path)
            try:
                with open(abs_p, encoding="utf-8-sig", errors="replace") as fh:
                    for i, line in enumerate(fh, start=1):
                        m = _OPENING_LINE_RE.match(line.rstrip("\n"))
                        if not m:
                            continue
                        name = m.group("name")
                        if name in entity_names and name not in locations:
                            locations[name] = (rel_p, i, m.group("comment"))
            except OSError:
                pass
    return locations


def _scan_category(
    ms,
    mod_path: str,
    category: str,
    key_fn: Callable[[str, object], list[tuple[str, bool, str]]] | None,
) -> tuple[list[LocFlag], set[str]]:
    """Return (flags, scanned_files_rel) for one category."""
    base = ms.base_parsers.get(category)
    mod = ms.mod_parsers.get(category)
    if mod is None:
        return [], set()
    base_keys = set(base.data.keys()) if base else set()
    mod_keys = set(mod.data.keys())
    new_keys = mod_keys - base_keys
    if not new_keys:
        return [], set()
    dir_rel = _DIR_MAP.get(category)
    if dir_rel is None:
        return [], set()
    locations = _build_entity_locations(mod_path, dir_rel, new_keys)
    flags: list[LocFlag] = []
    for entity in sorted(new_keys):
        body = _unwrap(mod.data.get(entity))
        if category == "Events":
            expected = _event_loc_keys(entity, body)
        elif key_fn is not None:
            expected = key_fn(entity, body)
        else:
            expected = []
        if not expected:
            continue
        missing = [k for k, req, _label in expected if req and not ms.has_localization(k)]
        if not missing:
            continue
        file_line = locations.get(entity)
        if not file_line:
            # Entity in parser but its opening line not found — could be an
            # inline-defined entity (`X = { ... }` on a single line) or one
            # whose source file moved. Skip rather than risk a misattribution.
            continue
        rel_p, line, comment = file_line
        flags.append(LocFlag(
            category=category,
            entity=entity,
            missing_keys=missing,
            file=rel_p,
            line=line,
            exemption=_parse_reviewed(comment),
        ))
    files_seen = {loc[0] for loc in locations.values()}
    return flags, files_seen


def audit(ms, mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    all_flags: list[LocFlag] = []
    all_files: set[str] = set()
    by_category: dict[str, int] = {}

    for category, key_fn in _REQUIREMENTS.items():
        flags, files_seen = _scan_category(ms, mod_path, category, key_fn)
        if flags:
            by_category[category] = len(flags)
        all_flags.extend(flags)
        all_files |= files_seen

    flags, files_seen = _scan_category(ms, mod_path, "Events", None)
    if flags:
        by_category["Events"] = len(flags)
    all_flags.extend(flags)
    all_files |= files_seen

    return AuditResult(
        flags=all_flags,
        coverage={
            "files_audited": len(all_files),
            "by_category": by_category,
        },
    )


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Localization coverage audit report",
        "",
        "Auto-generated by `loc_coverage_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a mod-introduced entity (newly defined by this mod, not a",
        "vanilla override) whose conventional localization key is missing.",
        "The engine emits no warning for unlocalized entities — the raw",
        "key leaks into player tooltips silently.",
        "",
        "Fix: add the missing key(s) to a `localization/english/*_l_english.yml`",
        "file. For static modifiers and most simple entities the key is the",
        "entity name itself; for journal entries also `<name>_desc`; for",
        "events the keys are whatever `title`/`desc`/`flavor`/option `name`",
        "fields point at.",
        "",
        "Suppress an intentional missing key with a same-line comment on the",
        "entity's opening line:",
        "`<entity_name> = { # REVIEWED YYYY-MM-DD: rationale`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        by_category: dict[str, list[LocFlag]] = {}
        for f in unrev:
            by_category.setdefault(f.category, []).append(f)
        for category in sorted(by_category):
            entries = by_category[category]
            out.append(f"### {category} ({len(entries)})")
            out.append("")
            for f in entries:
                missing_str = ", ".join(f"`{k}`" for k in f.missing_keys)
                out.append(
                    f"- `{f.file}:{f.line}` — `{f.entity}` — missing: {missing_str}"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            missing_str = ", ".join(f"`{k}`" for k in f.missing_keys)
            out.append(
                f"- `{f.file}:{f.line}` — `{f.entity}` ({f.category}) — "
                f"missing: {missing_str} — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    out.append(f"- files audited: {result.coverage.get('files_audited', 0)}")
    by_cat = result.coverage.get("by_category", {})
    if by_cat:
        out.append("- flags by category:")
        for cat in sorted(by_cat):
            out.append(f"  - {cat}: {by_cat[cat]}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")
    out.append("## Scope notes")
    out.append("")
    out.append(
        "- Only flags **mod-introduced** entities (present in mod_parsers but"
        " not base_parsers). Vanilla overrides inherit vanilla loc and are"
        " skipped — the failure mode this audit catches is unlocalized"
        " net-new mod entities."
    )
    out.append(
        "- Skips Scripted Effects/Triggers, On Actions (code-only),"
        " Script Values (mostly arithmetic). Add categories to"
        " `_REQUIREMENTS` if reports surface a gap."
    )
    out.append(
        "- Skips entities whose opening-line `<name> = {` couldn't be located"
        " in mod source (inline-defined or relocated files) — preferred over"
        " misattributing file:line."
    )

    return "\n".join(out) + "\n"


def regenerate(mod_state) -> dict:
    """POST_LOAD_GENERATORS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "loc_coverage_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    return {
        "files_audited": result.coverage.get("files_audited", 0),
        "by_category": result.coverage.get("by_category", {}),
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }


if __name__ == "__main__":
    # CLI entry: run against the live mod state.
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mod_state import ModState
    from path_constants import mod_path
    import mod_state_server  # for base_game_paths / mod_paths
    ms = ModState(mod_state_server.base_game_paths, mod_state_server.mod_paths)
    result = audit(ms, mod_path=mod_path)
    print(render_report(result))
