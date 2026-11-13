"""Audit: every modifier type name the mod writes or reads is registered, and a written one has a name to show.

A modifier block is a list of `<modifier type> = <value>` lines: the body of a
static modifier, a law's or technology's `modifier = { }`, a production
method's `building_modifiers`, a principle's `member_modifier`, a company's
`prosperity_modifier`, and so on. The engine reads each key as the name of a
modifier type and says almost nothing when the name is wrong.

Checks
------
`unregistered`: the name is of no modifier type that a file in
`common/modifier_type_definitions/` registers, vanilla's or the mod's. Written
as a field in a modifier block, the engine drops the line (`Unknown modifier
type`, in `debug.log` only) and the modifier loads without it. Vanilla 1.14.4
renamed two modifiers the mod used and nothing in the tooling noticed (#391);
a production method granted a throughput bonus for a mod building whose type
was never registered and CI stayed green (#681). Read as `modifier:<name>`,
it reads as nothing: a trigger on an undeclared boolean is always false, with
no log line (the space programs' booleans, 2026-04-29).

Registered means defined, and nothing else. A name that fits a dynamic family
(`building_<building>_throughput_add`, `goods_input_<good>_mult`) is not valid
because the building or the good exists: vanilla registers the throughput type
for under half of its own buildings, and the mod must register every one it
uses. The engine's `modifiers.log` listing a name (the catalog committed as
`docs/engine/modifiers_summary.txt`) does not make it valid either. The game
said so: `building_financial_district_throughput_add`, #1072's own example of
a name "the engine generates for every building", is in `modifiers.log` and
registered nowhere, and the game dropped it at load as `Unknown modifier
type` (#1096: `docs/testing/demographics-playtest.md` § "Resettlement events
load again; Metropolis without the Financial District",
`test_demographics_metro.py`'s `test_every_field_is_an_engine_modifier`). A
read fares no better: `modifier:` of a mortality key only `modifiers.log`
lists gave `'none'` on every pop (`docs/guides/scripting_best_practices.md` §
"`modifiers.log` listing ≠ script-usable"). About 4,700 of the names the log
lists are registered by nobody, the mod has had to register 96 of them
itself, and vanilla 1.15.1 writes no unregistered name in any of its own
modifier blocks (about 16,100 fields in 21 entity directories, held by
`test_vanilla_writes_no_field_this_audit_would_flag`). The pattern catalog
(`common/_meta/modifier_patterns.yml`) and the engine's list are used only to
say, in the flag, that the name can be registered.

`no_loc`: the field's type is one vanilla registers and no loc key of that
name exists, in vanilla's English loc or the mod's. The engine names a
modifier line from the loc key equal to the type's name (`country_prestige_mult`),
and prints the raw key when there is none, with no log line (#1072). A type
only the mod registers is not judged here: `loc_coverage_audit` already
requires its key, at the definition. So this check is for the types vanilla
registers and leaves without a name, which vanilla itself never writes in a
block. Two families are exempt because the engine names them from their
entity, through one shared key: a culture's three types
(`loc_coverage_audit.engine_named_culture_type`) and a vanilla religion's
`state_<religion>_standard_of_living_add` (`STATE_RELIGION_SOL_MODIFIER`;
vanilla's seventeen have no key of their own). Only the name is required; a
missing `_desc` leaves the nested tooltip empty and is not flagged, as in
`loc_coverage_audit`.

Every field of every block is judged for loc. A type's `script_only = yes`
does not hide its line, and `hidden = yes` (1.15, on three vanilla types the
mod does not use) has not been tried in game; vanilla gives those three a name
anyway, so a hidden type is asked for one too.

What is scanned
---------------
Fields: every `.txt` file under each entity directory of the mod's `common/`.
Which directories, and which blocks in them are modifier blocks, are the mod
state server's rules for `GET /modifier-grants` (`_grant_scan_plan`,
`_grant_block_label`): a static modifier's direct fields, and elsewhere the
first block inside an entity whose name says `modifier`, with only the
per-unit scaling wrappers nested inside it. This module reads the files token
by token instead of line by line, because the server's own line scan skips a
block written on one line (`tax_modifier_high = { tax_income_add = 0.05 }`),
which the mod does about 700 times (the generated tax amendments and 25
hand-written ship modifications); `test_modifier_field_audit` holds the two
scans to the same sites otherwise. A journal entry's
`modifiers_while_active` and `scaling_modifiers_while_active` name static
modifiers, whose own fields are checked where they are defined. Script
directories (effects, triggers, events) hold no modifier block. A field whose
name is built from a `$PARAM$` is skipped, as such a read is: the name is
known only once the parameter is filled in. The rule for one line is
`site_label`.

Costs: a ship type's or ship modification's `construction_goods` and
`materiel_goods` are written with modifier type names too
(`goods_input_steel_add = 1700`), the only other place the mod or vanilla
writes one. They are checked for registration and not for loc: a cost is not
a modifier line.

Reads: every `modifier:<name>` in the mod's `common/` and `events/` script,
quoted or not (a comparison quotes it), outside comments. A name built from a
`$PARAM$` is skipped.

Together these are every place a mod file names a modifier type (on
2026-11-12 no registered type's name was written anywhere else in the mod's
`common/` or `events/`), which is what `/validate/engine-coverage` judges by
walking every key that ends in a modifier suffix; that endpoint only logs on
a reload, and this audit puts the same judgment in the reload's `warnings`
and in CI.

Suppression
-----------
An `unregistered` flag takes none: the line does nothing in game. A `no_loc`
flag takes a check-tagged comment trailing on a modifier block's line that
writes the field,

    country_je_korea_action_cost = 1 # REVIEWED 2026-11-12 (modifier_field_loc): why

and one comment covers every use of that field. A tag on a line with no
`no_loc` flag is reported as `stale_review` and fails `--strict`.

Data source
-----------
On a post-load run, the server's ModState: its merged `Modifier Types` and its
loc, so on a machine with the game a vanilla patch that renames a type shows
on the first reload. From the command line, a small ModState with vanilla from
the committed `vanilla_parsed/` snapshot and the loc the other offline audits
read, so the audit needs no game install and runs in CI.
"""
from __future__ import annotations

import difflib
import os
import re
import sys
from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Callable

from audit_common import AuditResult as _AuditResult
from audit_common import cli_main, parse_reviewed, write_text
from loc_coverage_audit import _culture_names, engine_named_culture_type
from paradox_file_parser import INJECT_DIRECTIVES, REPLACE_DIRECTIVES

REPORT_PATH = os.path.join("docs", "engine", "modifier_field_report.md")
ENGINE_LIST_PATH = os.path.join("docs", "engine", "modifiers_summary.txt")

CHECK = "modifier_field_loc"
KIND_ORDER = ("unregistered", "no_loc", "stale_review")

# ModState entity types the offline run loads.
ENTITY_TYPES = {
    "Modifier Types": "modifier_type_definitions",
    "Cultures": "cultures",
    "Religions": "religions",
}

# A static modifier's only field that is not a modifier type, in vanilla and in the mod.
NOT_A_FIELD = frozenset({"icon"})

# Blocks of a ship type or ship modification that list goods costs under
# modifier type names. Not modifier blocks: nothing applies them as modifiers.
COST_BLOCKS = frozenset({"construction_goods", "materiel_goods"})

# The `block` of a `modifier:<name>` read.
READ = "modifier: read"
READ_DIRS = ("common", "events")

_RELIGION_SOL_RE = re.compile(r"state_(?P<r>\w+)_standard_of_living_add")

# A quoted string (kept, its body blanked) or a comment (blanked).
_STRING_OR_COMMENT_RE = re.compile(r'"[^"\n]*"|#[^\n]*')

# `modifier:<name>`, as a trigger or a value; `$` marks a name built from a parameter.
_READ_RE = re.compile(r"(?<![A-Za-z0-9_])modifier:(?P<name>[A-Za-z0-9_$]+)")

_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[^\s{}]+))?"
    r"|(?P<anon>\{)"
)


@dataclass
class Site:
    """One place a modifier type is named: a `<field> = <value>` line in a
    modifier block or a cost block, or a `modifier:<field>` read."""

    field: str
    file: str
    line: int
    block: str   # "direct", "modifier", "building_modifiers/workforce_scaled", a cost block, READ
    entity: str
    reviewed: dict | None = None

    @property
    def shown(self) -> bool:
        """Whether the line is one the game prints as a modifier line."""
        return self.block != READ and self.block not in COST_BLOCKS


@dataclass
class Flag:
    kind: str
    name: str
    detail: str
    sites: list
    exemption: dict | None = None

    @property
    def file(self) -> str:
        return self.sites[0].file

    @property
    def line(self) -> int:
        return self.sites[0].line


@dataclass
class Sources:
    """What a name is judged against."""

    registered: set          # every modifier type name, vanilla's and the mod's
    vanilla_types: set       # the ones vanilla registers
    cultures: set
    vanilla_religions: set
    has_loc: Callable[[str], bool]


@dataclass
class AuditResult(_AuditResult):
    """A tag that suppresses nothing is a `stale_review` flag, so `stale`
    stays empty and `failing` is every unreviewed flag."""

    flags: list = field(default_factory=list)
    files_audited: int = 0
    uses: int = 0     # lines written in a modifier block or a cost block
    reads: int = 0    # `modifier:<name>` reads
    fields: int = 0   # distinct names, written or read


# ---------------------------------------------------------------------------
# Source scan
# ---------------------------------------------------------------------------


def grant_rules():
    """The mod state server module, for its rules on where modifier blocks are
    (`_grant_scan_plan`, `_grant_block_label`). The server runs as `__main__`,
    so a post-load run takes the running module instead of importing a second
    copy of it."""
    main = sys.modules.get("__main__")
    if hasattr(main, "_grant_block_label") and hasattr(main, "_grant_scan_plan"):
        return main
    import mod_state_server
    return mod_state_server


def _blank(text: str) -> str:
    """`text` with comments and string bodies replaced by spaces, offsets kept."""
    def repl(m):
        s = m.group(0)
        if s[0] == "#":
            return " " * len(s)
        return '"' + " " * (len(s) - 2) + '"'
    return _STRING_OR_COMMENT_RE.sub(repl, text)


def _bare(key: str) -> str:
    """`key` without an `INJECT:` / `REPLACE:` directive in front of it."""
    head, sep, tail = key.partition(":")
    if sep and (head in INJECT_DIRECTIVES or head in REPLACE_DIRECTIVES):
        return tail
    return key


def site_label(stack: list, key: str, mode: str, rules=None) -> str | None:
    """The `block` of a `<key> = <value>` line whose enclosing blocks are
    `stack` ([0] the entity, directives stripped), or None when the line names
    no modifier type: the server's modifier-block rule, then a ship's cost
    blocks. A key built from a `$PARAM$` is skipped, as a read of one is."""
    if "$" in key or (mode == "direct" and key in NOT_A_FIELD):
        return None
    label = (rules or grant_rules())._grant_block_label(stack, mode)
    if label is None and len(stack) == 2 and stack[1] in COST_BLOCKS:
        label = stack[1]
    return label


def scan_text(text: str, rel_path: str, mode: str, rules=None) -> tuple[list, list]:
    """(sites, tag_lines) of one file's raw text.

    `mode` is the server's: "direct" for a static modifier file, whose fields
    sit directly in the entity, "wrapped" for every other entity directory.
    `tag_lines` are the lines that carry this audit's `# REVIEWED` tag."""
    rules = rules or grant_rules()
    clean = _blank(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]
    raw_lines = text.split("\n")
    sites: list = []
    stack: list = []   # one frame per open brace, [0] the entity
    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
        elif m.group("anon"):
            stack.append(None)
        elif m.group("open"):
            stack.append(_bare(m.group("key")))
        elif m.group("value") and stack and stack[0] is not None:
            key = _bare(m.group("key"))
            label = site_label(stack, key, mode, rules)
            if label is None:
                continue
            line = bisect_right(starts, m.start())
            sites.append(Site(key, rel_path, line, label, stack[0], parse_reviewed(raw_lines[line - 1], (CHECK,))))
    tag_lines = []
    if "REVIEWED" in text:
        tag_lines = [i for i, raw in enumerate(raw_lines, 1) if parse_reviewed(raw, (CHECK,))]
    return sites, tag_lines


def scan_reads(text: str, rel_path: str) -> list:
    """Every `modifier:<name>` read in one file's raw text, comments aside. A
    quoted read counts (`"modifier:x" >= 2`)."""
    sites: list = []
    if "modifier:" not in text:
        return sites
    for number, raw in enumerate(text.split("\n"), 1):
        if "modifier:" not in raw:
            continue
        code = _STRING_OR_COMMENT_RE.sub(lambda m: "" if m.group(0)[0] == "#" else m.group(0), raw)
        for m in _READ_RE.finditer(code):
            if "$" not in m.group("name"):
                sites.append(Site(m.group("name"), rel_path, number, READ, ""))
    return sites


def scan_mod(mod_path: str, rules=None) -> tuple[list, list, int]:
    """(sites, tags, files): the fields of every entity directory of the mod's
    `common/`, then the reads of its `common/` and `events/`. `tags` is
    [(file, line)] for each entity-file line carrying this audit's tag;
    `files` counts the entity files."""
    rules = rules or grant_rules()
    common = os.path.join(mod_path, "common")
    sites: list = []
    tags: list = []
    files = 0
    for _entity_type, subdir, mode in rules._grant_scan_plan([common]):
        for root, dirs, names in os.walk(os.path.join(common, *subdir.split("/"))):
            dirs.sort()
            for name in sorted(names):
                if not name.endswith(".txt") or name.startswith("_"):
                    continue
                abs_p = os.path.join(root, name)
                rel_p = os.path.relpath(abs_p, mod_path).replace(os.sep, "/")
                with open(abs_p, "r", encoding="utf-8-sig", errors="replace") as fh:
                    found, tag_lines = scan_text(fh.read(), rel_p, mode, rules)
                files += 1
                sites += found
                tags += [(rel_p, line) for line in tag_lines]
    for top in READ_DIRS:
        for root, dirs, names in os.walk(os.path.join(mod_path, top)):
            dirs.sort()
            for name in sorted(names):
                if not name.endswith(".txt") or name.startswith("_"):
                    continue
                abs_p = os.path.join(root, name)
                rel_p = os.path.relpath(abs_p, mod_path).replace(os.sep, "/")
                with open(abs_p, "r", encoding="utf-8-sig", errors="replace") as fh:
                    sites += scan_reads(fh.read(), rel_p)
    return sites, tags, files


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------


def engine_named(name: str, cultures, vanilla_religions) -> bool:
    """True when the engine names the type from its entity, so it needs no loc key of its own."""
    if engine_named_culture_type(name, cultures):
        return True
    m = _RELIGION_SOL_RE.fullmatch(name)
    return bool(m and m.group("r") in vanilla_religions)


def pattern_of(name: str, patterns) -> str | None:
    """The catalog pattern `name` has the shape of, if any. `patterns` is the
    `patterns` list of `common/_meta/modifier_patterns.yml`."""
    for entry in patterns or ():
        pattern = entry.get("pattern") or ""
        prefix, brace, rest = pattern.partition("{")
        suffix = rest.partition("}")[2]
        if brace and name.startswith(prefix) and name.endswith(suffix) and len(name) > len(prefix) + len(suffix):
            return pattern
    return None


def _unregistered_detail(name: str, uses: list, src: Sources, patterns, engine_listed) -> str:
    written = any(s.block != READ for s in uses)
    read = any(s.block == READ for s in uses)
    effect = " and ".join(filter(None, (
        "the engine drops the line" if written else "",
        "a `modifier:` read of it reads nothing" if read else "",
    )))
    parts = [f"no modifier type definition registers it, so {effect}"]
    pattern = pattern_of(name, patterns)
    if pattern:
        parts.append(
            f"it has the shape of `{pattern}`, a family the engine takes one definition at a time: "
            "add this name to `common/modifier_type_definitions/`"
        )
    elif name in engine_listed:
        parts.append(
            "the engine's `modifiers.log` lists it, so it can be registered: add it to "
            "`common/modifier_type_definitions/`"
        )
    close = difflib.get_close_matches(name, src.registered, n=3, cutoff=0.75)
    if close:
        parts.append("closest registered: " + ", ".join(f"`{c}`" for c in close))
    return "; ".join(parts)


def check(sites, tags, src: Sources, patterns=(), engine_listed=frozenset()) -> AuditResult:
    """Judge scanned sites. Pure: no file is read."""
    result = AuditResult(
        uses=sum(1 for s in sites if s.block != READ),
        reads=sum(1 for s in sites if s.block == READ),
    )
    by_field: dict = {}
    for site in sites:
        by_field.setdefault(site.field, []).append(site)
    result.fields = len(by_field)

    covered: set = set()   # (file, line) of every site of a `no_loc` field
    for name in sorted(by_field):
        uses = by_field[name]
        if name not in src.registered:
            result.flags.append(Flag(
                "unregistered", name, _unregistered_detail(name, uses, src, patterns, engine_listed), uses,
            ))
            continue
        shown = [s for s in uses if s.shown]
        if not shown:
            continue   # only read, or only a cost: no modifier line to name
        if name not in src.vanilla_types:
            continue   # a type only the mod registers: loc_coverage_audit asks for its key
        if src.has_loc(name) or engine_named(name, src.cultures, src.vanilla_religions):
            continue
        covered.update((s.file, s.line) for s in shown)
        reviewed = next((s.reviewed for s in shown if s.reviewed), None)
        result.flags.append(Flag(
            "no_loc", name,
            f"vanilla registers the type but no loc key `{name}` exists, so its line shows the raw key",
            shown, reviewed,
        ))

    # Every shown site of a line: a block written on one line has several.
    sites_at: dict = {}
    for s in sites:
        if s.shown:
            sites_at.setdefault((s.file, s.line), []).append(s)
    for file, line in tags:
        if (file, line) in covered:
            continue
        here = sites_at.get((file, line), [])
        unreg = [s for s in here if s.field not in src.registered]
        if not here:
            why, named = "the line writes no field of a modifier block", ""
        elif unreg:
            why, named = "an unregistered field takes no comment", unreg[0].field
        else:
            why = "no field on the line is flagged; remove it"
            named = ", ".join(dict.fromkeys(s.field for s in here))
        result.flags.append(Flag(
            "stale_review", named,
            f"a `({CHECK})` comment that suppresses nothing: {why}",
            unreg[:1] or here or [Site("", file, line, "", "")],
        ))
    return result


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------


def load_state(mod_path: str, vanilla_data: dict | None = None):
    """A ModState holding only the entity types this audit reads: vanilla from
    `vanilla_data` (default: the committed `vanilla_parsed/` snapshot under
    `mod_path`), the mod from `mod_path`."""
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


def sources_from_state(mod_state, has_loc: Callable[[str], bool] | None = None) -> Sources:
    return Sources(
        registered=set(mod_state.get_data("Modifier Types") or {}),
        vanilla_types=_vanilla_names(mod_state, "Modifier Types"),
        cultures=_culture_names(mod_state),
        vanilla_religions=_vanilla_names(mod_state, "Religions"),
        has_loc=has_loc or mod_state.has_localization,
    )


def offline_sources(mod_path: str) -> Sources:
    """Vanilla from the committed snapshot, the mod from `mod_path`; the loc is
    what `script_loc_reference_audit` checks against offline."""
    from script_loc_reference_audit import offline_localization

    return sources_from_state(load_state(mod_path), offline_localization(mod_path).__contains__)


def load_patterns(rules=None) -> list:
    """The pattern catalog, read by the server's loader ([] without PyYAML)."""
    try:
        return (rules or grant_rules())._load_pattern_catalog()
    except Exception:
        return []


def load_engine_listed(mod_path: str) -> set:
    """Names in the committed render of the engine's `modifiers.log`."""
    names: set = set()
    try:
        with open(os.path.join(mod_path, ENGINE_LIST_PATH), "r", encoding="utf-8") as fh:
            for raw in fh:
                parts = raw.split("|")
                if len(parts) >= 2 and not raw.startswith("#"):
                    names.add(parts[1])
    except OSError:
        pass
    return names


def audit(mod_state=None, mod_path: str | None = None, sources: Sources | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    if sources is None:
        sources = sources_from_state(mod_state) if mod_state is not None else offline_sources(mod_path)
    rules = grant_rules()
    sites, tags, files = scan_mod(mod_path, rules)
    result = check(sites, tags, sources, load_patterns(rules), load_engine_listed(mod_path))
    result.files_audited = files
    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

_SITES_SHOWN = 5


def _where(flag: Flag) -> str:
    shown = ", ".join(f"{s.file}:{s.line}" for s in flag.sites[:_SITES_SHOWN])
    more = len(flag.sites) - _SITES_SHOWN
    return shown + (f" and {more} more" if more > 0 else "")


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Modifier field audit report",
        "",
        "Auto-generated by `modifier_field_audit.py` on every `POST /reload`",
        "of the mod state server. Do not hand-edit.",
        "",
        "Every place a mod file names a modifier type: a `<modifier type> =",
        "<value>` line in a modifier block of `common/` (a static modifier's body,",
        "a law's or technology's `modifier`, a production method's",
        "`building_modifiers`, a principle's `member_modifier`, ...) or in a ship's",
        "`construction_goods` / `materiel_goods`, and a `modifier:<name>` read in",
        "`common/` or `events/`.",
        "",
        "- `unregistered`: the name is of no modifier type that",
        "  `common/modifier_type_definitions/` registers, in vanilla or the mod.",
        "  The engine drops a line that writes it and logs that in `debug.log`",
        "  only; a read of it reads nothing. A name that fits a dynamic family, or",
        "  that the engine's `modifiers.log` lists, still needs its own definition.",
        "- `no_loc`: a modifier block writes a type vanilla registers and no loc",
        "  key of that name exists, so the line shows the raw key. (A type only",
        "  the mod registers is `loc_coverage_audit`'s.)",
        "",
        "An `unregistered` flag takes no suppression. For a `no_loc` flag that is",
        f"intended, add `# REVIEWED YYYY-MM-DD ({CHECK}): rationale` trailing on a",
        "modifier block's line that writes the field; one comment covers every",
        "use. A tag that suppresses nothing is flagged `stale_review`.",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out += ["_None._", ""]
    else:
        for kind in KIND_ORDER:
            rows = [f for f in unrev if f.kind == kind]
            if not rows:
                continue
            out += [f"### {kind}", ""]
            for f in rows:
                label = f"`{f.name}` — " if f.name else ""
                uses = f", {len(f.sites)} uses" if len(f.sites) > 1 else ""
                out.append(f"- {label}{f.detail} ({_where(f)}{uses})")
            out.append("")

    out += ["## Reviewed Exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        # No line numbers: an edit above the line would churn the report.
        for f in exemp:
            out.append(
                f"- {f.kind}: `{f.name}` ({f.file}) — **{f.exemption['date']}**: "
                f"{f.exemption['rationale']}"
            )
        out.append("")
    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    write_text(os.path.join(mod_path, REPORT_PATH), render_report(result))
    unrev = len(result.unreviewed)
    return {
        "files_audited": result.files_audited,
        "fields_checked": result.fields,
        "uses_checked": result.uses,
        "reads_checked": result.reads,
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": len(result.flags) - unrev,
    }


def main(argv=None, mod_path: str | None = None) -> int:
    """Print the report. With `--strict` (CI), exit 1 on any flag without a
    `# REVIEWED ...` exemption: every `unregistered` flag, an unreviewed
    `no_loc`, a stale tag."""
    if mod_path is None:
        from path_constants import mod_path

    def render(result: AuditResult, args) -> None:
        print(render_report(result))
        print(
            f"{result.fields} distinct names: {result.uses} lines written in {result.files_audited} entity files, "
            f"{result.reads} reads.",
            file=sys.stderr,
        )

    return cli_main(lambda args: audit(mod_path=mod_path), render, argv=argv,
                    description=__doc__.splitlines()[0],
                    strict_help="CI mode: exit 1 on any flag without a `# REVIEWED` exemption, "
                                "a stale tag included.")


if __name__ == "__main__":
    raise SystemExit(main())
