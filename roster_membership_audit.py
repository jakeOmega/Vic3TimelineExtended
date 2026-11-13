"""Audit for definitions that must name, or be named by, another list.

Three kinds of entity do nothing useful on their own. Each has to point at a
list, or be listed by a container, and the engine says little or nothing when
the link is missing.

Checks
------
Per ship type the mod defines in `common/ship_types/` (a plain block, or a
`REPLACE:` of a vanilla type; an `INJECT:` onto a vanilla type adds fields to
vanilla's definition and is judged only on a category it writes):

- `missing_ai_category`: no `ai_ship_category`. Required since vanilla
  1.14.4. The engine logs `ship_type.cpp: Ship Type is missing
  ai_ship_category!` once in `error.log` and keeps loading; on 2026-09-23 all
  19 mod ship types lacked it and every session crashed on the month tick
  (#386, #390). Judged on the merged ship type, so a category that a later
  `INJECT:` adds to the mod's own type counts, and one injected before the
  definition, which then replaces it, does not.
- `unknown_ai_category`: an `ai_ship_category` that names no entry of
  `common/ai_ship_categories/`, vanilla or mod: any value the mod writes
  (bare or quoted), and the merged type's.
- `no_fleet_entity`: a ship type that is new with the mod and has no row in
  the `SHIPS` table of `scripts/generators/gen_fleet_entities.py`, which
  writes `gfx/map/fleet_entities/02_extra_fleet_entities.txt`. Without a
  fleet entity the ship has no model on the map. Where `gfx/` is on disk the
  generated blocks are read too, so a row added without re-running the
  generator is caught; CI checks out without `gfx/` and reads the table alone.

Per ship modification the mod defines in `common/ship_modifications/`:

- `unlisted_modification`: no ship type, vanilla or mod, lists it under
  `modifications = { ship_mod_slot_<slot> = { ... } }`. A modification can
  only be fitted where a ship type lists it, so this one has an icon, loc and
  an unlocking technology and can never be chosen (#509: four utility modules
  sat in no slot list for five months).

Per production method the mod defines in `common/production_methods/`:

- `unlisted_pm`: no production method group lists it under
  `production_methods`, so no building can use it.

Suppression
-----------
The three ship type flags take none: a missing category or model is never
intended. The two `unlisted_*` flags take a check-tagged comment,
`# REVIEWED YYYY-MM-DD (roster_membership): rationale`, trailing on the
opening `<name> = {` line of the modification or production method (content
parked for a later release, say). A tag that suppresses nothing is reported
as `stale_review` (in `AuditResult.stale`) and fails `--strict`.

Data source
-----------
Which blocks the mod writes, with their lines and comments, comes from a
raw-text scan of the three mod directories, because the parser drops lines
and comments. Category names, each ship type's category and slot lists, and
PM group lists are merged vanilla + mod data: on a post-load run the server's
ModState, from the command line a small ModState with vanilla from the
committed `vanilla_parsed/` snapshot, so the audit needs no game install and
runs in CI. A key written twice in one block (`modifications`, a slot,
`production_methods`) is read at every occurrence.

A field-level directive inside an `INJECT:` block
(`REPLACE:ai_ship_category = x`) is read as the parser reads it, as that
field. Neither vanilla nor the mod writes one and the engine's handling is
unverified (`paradox_file_parser.py`), so this only keeps a bad value in
that spelling from passing unseen.
"""
import ast
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from audit_common import AuditResult as _AuditResult
from audit_common import StaleTag as _StaleTag
from audit_common import cli_main, parse_reviewed, write_text

# Offset-preserving comment/string blanking, shared with the iterator audit so
# the audits agree on what "a commented-out line" means.
from iterator_limit_audit import blank_comments_and_strings
from paradox_file_parser import INJECT_DIRECTIVES, REPLACE_DIRECTIVES

# The parsed-value helpers the company roster audit already has.
from prestige_good_roster_audit import _names, _unwrap

# ModState entity type -> directory under common/.
ENTITY_TYPES = {
    "Ship Types": "ship_types",
    "Ship Modifications": "ship_modifications",
    "AI Ship Categories": "ai_ship_categories",
    "PMs": "production_methods",
    "PM Groups": "production_method_groups",
}

SHIP_TYPES_DIR = os.path.join("common", "ship_types")
SHIP_MODS_DIR = os.path.join("common", "ship_modifications")
PMS_DIR = os.path.join("common", "production_methods")
FLEET_ENTITY_GENERATOR = os.path.join("scripts", "generators", "gen_fleet_entities.py")
FLEET_ENTITIES_DIR = os.path.join("gfx", "map", "fleet_entities")
REPORT_PATH = os.path.join("docs", "engine", "roster_membership_report.md")

CHECK = "roster_membership"
KIND_ORDER = (
    "missing_ai_category", "unknown_ai_category", "no_fleet_entity",
    "unlisted_modification", "unlisted_pm", "stale_review",
)
# The kinds a `# REVIEWED` comment can cover.
SUPPRESSIBLE = ("unlisted_modification", "unlisted_pm")

_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[^\s{}#]+))?"
    r"|(?P<anon>\{)"
)


# ---------------------------------------------------------------------------
# Source scan: the top-level blocks the mod writes
# ---------------------------------------------------------------------------


@dataclass
class Opener:
    """One top-level `<name> = {` block in a mod file."""

    name: str
    directive: str | None
    file: str
    line: int
    comment: str | None
    # `ai_ship_category = X` lines directly inside the block: [(X, line)].
    categories: list = field(default_factory=list)


def _split_directive(key: str) -> tuple[str | None, str]:
    head, sep, tail = key.partition(":")
    if sep and (head in INJECT_DIRECTIVES or head in REPLACE_DIRECTIVES):
        return head, tail
    return None, key


def scan_text(text: str, rel_path: str) -> list[Opener]:
    """Every top-level block of one file's raw text, in file order."""
    clean, comments = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]
    openers: list[Opener] = []
    depth = 0
    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            depth = max(0, depth - 1)
        elif m.group("anon"):
            depth += 1
        elif m.group("open"):
            if depth == 0:
                line = bisect_right(starts, m.start())
                directive, name = _split_directive(m.group("key"))
                openers.append(Opener(name, directive, rel_path, line, comments.get(line)))
            depth += 1
        elif (
            depth == 1 and openers and m.group("value")
            and _split_directive(m.group("key"))[1] == "ai_ship_category"
        ):
            value = m.group("value")
            if value.startswith('"'):
                # The string's body is blanked in `clean`; read it from `text`.
                start = m.start("value") + 1
                end = text.find('"', start)
                value = text[start:end if end >= 0 else len(text)].split("\n")[0].strip()
            openers[-1].categories.append((value, bisect_right(starts, m.start())))
    return openers


def scan_dir(mod_path: str, rel_dir: str) -> list[Opener]:
    openers: list[Opener] = []
    root_dir = os.path.join(mod_path, rel_dir)
    if not os.path.isdir(root_dir):
        return openers
    for root, _dirs, files in sorted(os.walk(root_dir)):
        for fname in sorted(files):
            if not fname.endswith(".txt"):
                continue
            abs_p = os.path.join(root, fname)
            rel_p = os.path.relpath(abs_p, mod_path).replace(os.sep, "/")
            with open(abs_p, "r", encoding="utf-8-sig", errors="replace") as fh:
                openers += scan_text(fh.read(), rel_p)
    return openers


def defines(opener: Opener, vanilla_names) -> bool:
    """Whether the block is the entity's whole definition, as opposed to
    fields added to one that vanilla defines. The `TRY_` and `_OR_CREATE`
    forms depend on whether vanilla has the entity. (An `INJECT_OR_CREATE:`
    onto an entity the mod defines elsewhere also answers True; callers
    judge an entity once, by name, on the merged data.)"""
    d = opener.directive
    if d is None or d in ("REPLACE", "REPLACE_OR_CREATE"):
        return True
    if d == "TRY_REPLACE":
        return opener.name in vanilla_names
    if d == "INJECT_OR_CREATE":
        return opener.name not in vanilla_names
    return False


# ---------------------------------------------------------------------------
# Fleet entities
# ---------------------------------------------------------------------------


def fleet_entity_table(mod_path: str) -> set | None:
    """The ship types in the fleet entity generator's `SHIPS` table, read
    with `ast` so the generator (which resolves a vanilla path on import) is
    never run. None when the generator is not there or `SHIPS` is not a
    literal list of `(ship type, template)` rows: the check is then reported
    as not run, where raising would fail the whole audit on a reload."""
    path = os.path.join(mod_path, FLEET_ENTITY_GENERATOR)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "SHIPS" for t in node.targets
        ):
            try:
                rows = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError):
                return None
            if not isinstance(rows, (list, tuple)) or not all(
                isinstance(row, (list, tuple)) and row and isinstance(row[0], str) for row in rows
            ):
                return None
            return {row[0] for row in rows}
    return None


def fleet_entity_blocks(mod_path: str) -> set | None:
    """The fleet entities the mod's `gfx/map/fleet_entities/` files define,
    or None in a checkout without `gfx/` (CI's)."""
    if not os.path.isdir(os.path.join(mod_path, FLEET_ENTITIES_DIR)):
        return None
    return {o.name for o in scan_dir(mod_path, FLEET_ENTITIES_DIR)}


# ---------------------------------------------------------------------------
# The audit
# ---------------------------------------------------------------------------


@dataclass
class Flag:
    kind: str
    name: str
    detail: str
    file: str | None = None
    line: int | None = None
    exemption: dict | None = None


@dataclass
class StaleTag(_StaleTag):
    """A `(roster_membership)` tag that suppresses nothing (`stale_review`),
    on the opening line of the block `name`; `why` says what to do."""

    name: str = ""
    why: str = ""


@dataclass
class AuditResult(_AuditResult):
    """The flags, and in `stale` the `stale_review` tags."""

    flags: list[Flag] = field(default_factory=list)
    ship_types_checked: int = 0
    modifications_checked: int = 0
    pms_checked: int = 0
    # False when the SHIPS table could not be read, so no ship was judged on it.
    fleet_entities_checked: bool = False


def _blocks(v):
    """Every `{ }` block a key holds: one, or one per time the key is written
    (the parser turns a repeated key into a list)."""
    v = _unwrap(v)
    if isinstance(v, dict):
        yield v
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from _blocks(x)


def listed_modifications(ship_types: dict) -> set:
    """Every modification some ship type lists in a slot."""
    listed: set = set()
    for raw in ship_types.values():
        for body in _blocks(raw):
            for slots in _blocks(body.get("modifications")):
                for names in slots.values():
                    listed.update(_names(names))
    return listed


def merged_categories(ship_type) -> list[str]:
    """The `ai_ship_category` value(s) of one merged ship type."""
    values: list[str] = []
    for body in _blocks(ship_type):
        values += [v.strip('"') for v in _names(body.get("ai_ship_category"))]
    return values


def listed_pms(pm_groups: dict) -> set:
    """Every production method some PM group lists."""
    listed: set = set()
    for raw in pm_groups.values():
        body = _unwrap(raw)
        if isinstance(body, dict):
            listed.update(_names(body.get("production_methods")))
    return listed


def _modification_detail(body) -> str:
    """The slot a modification is for and the technologies that advertise it."""
    body = _unwrap(body)
    if not isinstance(body, dict):
        return ""
    parts = []
    slot = _names(body.get("type"))
    if slot:
        parts.append(f"a `{slot[-1]}` module")
    techs = _names(body.get("unlocking_technologies"))
    if techs:
        parts.append("unlocked by " + ", ".join(f"`{t}`" for t in techs))
    return " (" + ", ".join(parts) + ")" if parts else ""


def check(
    ship_type_openers: list,
    modification_openers: list,
    pm_openers: list,
    *,
    categories,
    vanilla_ship_types,
    ship_types: dict,
    listed_pm_names: set,
    modifications: dict | None = None,
    vanilla_modifications=(),
    vanilla_pms=(),
    fleet_table: set | None = None,
    fleet_blocks: set | None = None,
) -> AuditResult:
    """Judge the mod's scanned blocks against the merged data.

    `categories` is every AI ship category name; `ship_types` the merged
    ship types (their category and slot lists); `listed_pm_names` what PM
    groups list; `fleet_table` and `fleet_blocks` the ship types with a fleet
    entity (None: not available, so not checked)."""
    result = AuditResult(fleet_entities_checked=fleet_table is not None)
    categories = set(categories)
    generator = FLEET_ENTITY_GENERATOR.replace(os.sep, "/")

    by_name: dict = {}
    for o in ship_type_openers:
        by_name.setdefault(o.name, []).append(o)
    for name, openers in by_name.items():
        definers = [o for o in openers if defines(o, vanilla_ship_types)]
        # The block to point at: an `INJECT_OR_CREATE:` only when nothing
        # else defines the type.
        site = next((o for o in definers if o.directive != "INJECT_OR_CREATE"), None) or (
            definers[0] if definers else None)
        written = [(value, o.file, line) for o in openers for value, line in o.categories]
        if name in ship_types:
            merged = merged_categories(ship_types[name])
        else:
            merged = [value for o in definers for value, _line in o.categories]
        if site is not None:
            result.ship_types_checked += 1
            if not merged:
                result.flags.append(Flag(
                    "missing_ai_category", name,
                    "declares no `ai_ship_category`, a required field since vanilla 1.14.4",
                    site.file, site.line,
                ))
        flagged: set = set()
        for value, file, line in written + [(v, openers[0].file, openers[0].line) for v in merged]:
            if value in categories or value in flagged:
                continue
            flagged.add(value)
            result.flags.append(Flag(
                "unknown_ai_category", name,
                f"`ai_ship_category = {value}` names no entry of `common/ai_ship_categories/`",
                file, line,
            ))
        if site is not None and name not in vanilla_ship_types:
            if fleet_table is not None and name not in fleet_table:
                result.flags.append(Flag(
                    "no_fleet_entity", name,
                    f"has no row in `SHIPS` in `{generator}`, so it gets no fleet entity and no "
                    "model on the map",
                    site.file, site.line,
                ))
            elif fleet_blocks is not None and name not in fleet_blocks:
                result.flags.append(Flag(
                    "no_fleet_entity", name,
                    f"has no block under `{FLEET_ENTITIES_DIR.replace(os.sep, '/')}/`: re-run `{generator}`",
                    site.file, site.line,
                ))

    # Openers whose comment suppressed a flag, by identity, for the stale check.
    used: set = set()

    def unlisted(openers, vanilla_names, listed, kind, describe):
        count = 0
        judged: set = set()
        for o in openers:
            if not defines(o, vanilla_names) or o.name in judged:
                continue
            judged.add(o.name)
            count += 1
            if o.name in listed:
                continue
            # A copy of the entity in another file may carry the comment.
            tagged = [x for x in openers if x.name == o.name and parse_reviewed(x.comment, (CHECK,))]
            used.update(id(x) for x in tagged)
            reviewed = parse_reviewed(tagged[0].comment, (CHECK,)) if tagged else None
            result.flags.append(Flag(kind, o.name, describe(o.name), o.file, o.line, reviewed))
        return count

    result.modifications_checked = unlisted(
        modification_openers, vanilla_modifications, listed_modifications(ship_types),
        "unlisted_modification",
        lambda name: "no ship type lists it in a `modifications` slot, so it can never be fitted"
                     + _modification_detail((modifications or {}).get(name)),
    )
    result.pms_checked = unlisted(
        pm_openers, vanilla_pms, listed_pm_names, "unlisted_pm",
        lambda name: "no production method group lists it, so no building can use it",
    )

    # A tag that suppresses nothing: on a block that is not flagged, or on a
    # ship type, whose flags take no comment.
    for openers, why in (
        (ship_type_openers, "a ship type flag takes no comment"),
        (modification_openers, "remove it"),
        (pm_openers, "remove it"),
    ):
        for o in openers:
            if parse_reviewed(o.comment, (CHECK,)) and id(o) not in used:
                result.stale.append(StaleTag(o.file, o.line, CHECK, o.name, why))
    return result


def load_state(mod_path: str, vanilla_data: dict | None = None):
    """A ModState holding only the entity types this audit reads: vanilla from
    `vanilla_data` (default: the committed `vanilla_parsed/` snapshot), the mod
    from `mod_path`."""
    from mod_state import ModState

    if vanilla_data is None:
        import json

        import vanilla_parsed

        snap_dir = os.path.join(mod_path, "vanilla_parsed")
        manifest = vanilla_parsed.read_manifest(snap_dir) or {}
        vanilla_data = {}
        for et in ENTITY_TYPES:
            info = manifest.get("entity_types", {}).get(et)
            if not info:
                continue
            with open(os.path.join(snap_dir, info["file"]), "r", encoding="utf-8") as fh:
                vanilla_data[et] = vanilla_parsed.decode(json.load(fh))
    base = {et: "" for et in ENTITY_TYPES}
    mod = {et: os.path.join(mod_path, "common", d) for et, d in ENTITY_TYPES.items()}
    return ModState(base, mod, vanilla_data=vanilla_data)


def _vanilla_names(mod_state, entity_type: str) -> set:
    parser = getattr(mod_state, "base_parsers", {}).get(entity_type)
    return set(getattr(parser, "data", None) or {})


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    if mod_state is None:
        mod_state = load_state(mod_path)
    return check(
        scan_dir(mod_path, SHIP_TYPES_DIR),
        scan_dir(mod_path, SHIP_MODS_DIR),
        scan_dir(mod_path, PMS_DIR),
        categories=mod_state.get_data("AI Ship Categories") or {},
        vanilla_ship_types=_vanilla_names(mod_state, "Ship Types"),
        ship_types=mod_state.get_data("Ship Types") or {},
        listed_pm_names=listed_pms(mod_state.get_data("PM Groups") or {}),
        modifications=mod_state.get_data("Ship Modifications") or {},
        vanilla_modifications=_vanilla_names(mod_state, "Ship Modifications"),
        vanilla_pms=_vanilla_names(mod_state, "PMs"),
        fleet_table=fleet_entity_table(mod_path),
        fleet_blocks=fleet_entity_blocks(mod_path),
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def render_report(result: AuditResult) -> str:
    unrev = result.unreviewed
    exemp = result.exemptions

    out = [
        "# Roster membership audit report",
        "",
        "Auto-generated by `roster_membership_audit.py` on every `POST /reload`",
        "of the mod state server. Do not hand-edit.",
        "",
        "Definitions that must name, or be named by, another list, where the",
        "engine says little or nothing about a missing link:",
        "",
        "- `missing_ai_category`, `unknown_ai_category`: a mod ship type with no",
        "  `ai_ship_category` (required since vanilla 1.14.4; the engine logs one",
        "  line in `error.log`), or one naming no entry of",
        "  `common/ai_ship_categories/`.",
        "- `no_fleet_entity`: a ship type new with the mod and absent from the",
        "  `SHIPS` table of `scripts/generators/gen_fleet_entities.py`, so it has",
        "  no model on the map.",
        "- `unlisted_modification`: a mod ship modification no ship type lists in",
        "  a `modifications` slot. It can never be fitted.",
        "- `unlisted_pm`: a mod production method no production method group",
        "  lists. No building can use it.",
        "",
        "The ship type flags take no suppression. For an `unlisted_*` flag that",
        f"is intended, add `# REVIEWED YYYY-MM-DD ({CHECK}): rationale` trailing on",
        "the opening line of the modification or production method. A tag that",
        "suppresses nothing is flagged `stale_review`.",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not result.failing:
        out += ["_None._", ""]
    else:
        for kind in KIND_ORDER:
            if kind == "stale_review":
                rows = [f"- `{t.name}` — a `({CHECK})` comment that suppresses nothing: {t.why} "
                        f"({t.file}:{t.line})" for t in result.stale]
            else:
                rows = [f"- `{f.name}` — {f.detail} ({f.file}:{f.line})" for f in unrev if f.kind == kind]
            if rows:
                out += [f"### {kind}", "", *rows, ""]

    out += ["## Reviewed Exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        # No line numbers: an edit above the block would churn the report.
        for f in exemp:
            out.append(
                f"- {f.kind}: `{f.name}` ({f.file}) — **{f.exemption['date']}**: "
                f"{f.exemption['rationale']}"
            )
        out.append("")
    if not result.fleet_entities_checked:
        out += [
            "## Not checked",
            "",
            f"- `no_fleet_entity`: `SHIPS` could not be read from `{FLEET_ENTITY_GENERATOR.replace(os.sep, '/')}`"
            " as a list of `(ship type, template)` rows.",
            "",
        ]
    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    write_text(os.path.join(mod_path, REPORT_PATH), render_report(result))
    return {
        "ship_types_checked": result.ship_types_checked,
        "modifications_checked": result.modifications_checked,
        "pms_checked": result.pms_checked,
        "fleet_entities_checked": result.fleet_entities_checked,
        # A stale tag counts as a flag, and as unreviewed.
        "total_flags": len(result.flags) + len(result.stale),
        "unreviewed": len(result.failing),
        "exempted": len(result.exemptions),
    }


def main(argv=None, mod_path: str | None = None) -> int:
    """Print the report. With `--strict` (CI), exit 1 on any flag without a
    `# REVIEWED ...` exemption, a stale tag included."""
    if mod_path is None:
        from path_constants import mod_path
    return cli_main(lambda args: audit(mod_path=mod_path), lambda result, args: render_report(result),
                    argv=argv, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    raise SystemExit(main())
