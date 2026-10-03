"""Audit for company prestige goods the company's own buildings cannot make.

A company at full prosperity produces the prestige goods listed in its
`possible_prestige_goods` in place of their base good, in the buildings it
owns. A prestige good whose base good no `building_types` building produces
therefore never appears. The engine accepts the definition and logs nothing.
Google listed Precision Robotics (base good robotics) while robotics came only
from an extension building, and five more mod companies carried seven more.

An `extension_building_types` building does not close the gap. Extensions
join the roster only through an industry charter, a company holds one such
charter at a time, and each grant has a cooldown, so a prestige good that
depends on one is dead for most of the game.

Checks
------
Per prestige good of every company the mod defines, replaces or injects into:

- `extension_only`: only an extension building produces the base good.
- `not_produced`: no roster or extension building produces it.

A building produces a good when any production method of any of its PM groups
carries `goods_output_<good>_add`.

Base goods
----------
A mod prestige good's `base_good` comes from `common/prestige_goods/`. A
vanilla `prestige_good_generic_<good>` is taken to have base good `<good>` when
`<good>` is a known good. Vanilla's named prestige goods (Tailored Suits and
the like) are not in the `vanilla_parsed/` snapshot, so their base good is
unknown and they are counted in the report's coverage, never flagged.

Companies the mod leaves untouched are not judged: vanilla's choices are
vanilla's design, and the mod has no line to carry a suppression on.

Suppression
-----------
A trailing `# REVIEWED YYYY-MM-DD: rationale` comment on the prestige good's
line inside `possible_prestige_goods`, or on the company's opening
`<name> = {` line (also `REPLACE:` / `INJECT:`) in `common/company_types/`,
which covers every flag on that company.

Data source
-----------
Companies, buildings, PM groups, PMs and goods are judged on merged vanilla +
mod data. On a post-load run that is the server's ModState. Run from the
command line, the audit builds a small ModState of its own with vanilla from
the committed `vanilla_parsed/` snapshot, so it needs no game install and runs
in CI. Suppression comments and line numbers come from a raw-text scan of the
mod's company files, because the parser drops both.
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

# Offset-preserving comment/string blanking, shared with the iterator audit so
# the audits agree on what "a commented-out line" means.
from iterator_limit_audit import blank_comments_and_strings

# ModState entity type -> directory under common/.
ENTITY_TYPES = {
    "Company Types": "company_types",
    "Buildings": "buildings",
    "PM Groups": "production_method_groups",
    "PMs": "production_methods",
    "Goods": "goods",
}

COMPANIES_DIR = os.path.join("common", "company_types")
PRESTIGE_GOODS_DIR = os.path.join("common", "prestige_goods")
REPORT_PATH = os.path.join("docs", "engine", "prestige_good_roster_report.md")

KIND_ORDER = ("not_produced", "extension_only")

GENERIC_PREFIX = "prestige_good_generic_"

_OPERATORS = ("=", "?=", "<", ">", "<=", ">=", "!=", "==")
_OUTPUT_RE = re.compile(r"goods_output_(\w+)_add")

_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+)$"
)

_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[^\s{}#]+))?"
    r"|(?P<word>[A-Za-z_][A-Za-z0-9_.:\-]*)"
    r"|(?P<anon>\{)"
)


# ---------------------------------------------------------------------------
# Source scan: where each company and prestige good line lives in the mod
# ---------------------------------------------------------------------------

@dataclass
class Source:
    """Where the mod writes one company. A company can be opened more than
    once (a `REPLACE:` in one file, an `INJECT:` in another)."""

    # Sites are (file, line, comment-or-None).
    openers: list = field(default_factory=list)
    # prestige good -> [site] inside `possible_prestige_goods`.
    prestige_goods: dict = field(default_factory=dict)


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _entity_name(key: str) -> str:
    # `REPLACE:company_x`, `INJECT:company_x`, `TRY_INJECT:company_x`, ...
    return key.rsplit(":", 1)[-1]


def scan_text(text: str, rel_path: str, sources: dict | None = None) -> dict:
    """Record every company opener and prestige good line in one file's raw
    text into `sources` ({name: Source}) and return it."""
    if sources is None:
        sources = {}
    clean, comments = blank_comments_and_strings(text)
    starts = _line_starts(clean)
    stack: list = []
    current: Source | None = None

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
            continue
        if m.group("anon"):
            if stack:
                stack.append(None)
            continue

        line = bisect_right(starts, m.start())
        site = (rel_path, line, comments.get(line))

        if m.group("word"):
            if current is not None and stack[1:] == ["possible_prestige_goods"]:
                current.prestige_goods.setdefault(m.group("word"), []).append(site)
            continue

        key = m.group("key")
        if m.group("open"):
            if not stack:
                current = sources.setdefault(_entity_name(key), Source())
                current.openers.append(site)
            stack.append(key)
    return sources


def scan_sources(mod_path: str) -> dict:
    sources: dict = {}
    root_dir = os.path.join(mod_path, COMPANIES_DIR)
    if not os.path.isdir(root_dir):
        return sources
    for root, _dirs, files in os.walk(root_dir):
        for fname in sorted(files):
            if not fname.endswith(".txt"):
                continue
            abs_p = os.path.join(root, fname)
            rel_p = os.path.relpath(abs_p, mod_path).replace(os.sep, "/")
            try:
                with open(abs_p, "r", encoding="utf-8-sig", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            scan_text(text, rel_p, sources)
    return sources


# ---------------------------------------------------------------------------
# Parsed-data helpers
# ---------------------------------------------------------------------------


def _unwrap(v):
    """`('=', value)` -> value. Lists (bare `{ a b }` blocks, repeated keys)
    are left as lists."""
    while isinstance(v, tuple) and len(v) == 2 and v[0] in _OPERATORS:
        v = v[1]
    return v


def _names(v) -> list[str]:
    """The identifiers in a `{ a b c }` block, however the parser shaped it
    (a list, a repeated key's list of tuples, a lone string)."""
    v = _unwrap(v)
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        return list(v)
    if isinstance(v, (list, tuple)):
        out: list[str] = []
        for x in v:
            out += _names(x)
        return out
    return []


def _outputs(pm) -> set:
    """Goods a production method outputs (`goods_output_<good>_add`)."""
    out: set = set()

    def walk(v):
        v = _unwrap(v)
        if isinstance(v, dict):
            for k, x in v.items():
                m = _OUTPUT_RE.fullmatch(k)
                if m:
                    out.add(m.group(1))
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)

    walk(pm)
    return out


def building_outputs(buildings: dict, pm_groups: dict, pms: dict) -> dict:
    """{building: set of goods any of its production methods outputs}."""
    pm_out: dict = {}
    result: dict = {}
    for name, raw in buildings.items():
        body = _unwrap(raw)
        if not isinstance(body, dict):
            continue
        goods: set = set()
        for group in _names(body.get("production_method_groups")):
            g = _unwrap(pm_groups.get(group))
            if not isinstance(g, dict):
                continue
            for pm in _names(g.get("production_methods")):
                if pm not in pm_out:
                    pm_out[pm] = _outputs(_unwrap(pms.get(pm)))
                goods |= pm_out[pm]
        result[name] = goods
    return result


def load_prestige_bases(mod_path: str) -> dict:
    """{prestige good: base good} for the mod's own prestige goods."""
    from paradox_file_parser import ParadoxFileParser

    bases: dict = {}
    root_dir = os.path.join(mod_path, PRESTIGE_GOODS_DIR)
    if not os.path.isdir(root_dir):
        return bases
    for fname in sorted(os.listdir(root_dir)):
        if not fname.endswith(".txt"):
            continue
        parser = ParadoxFileParser()
        parser.parse_file(os.path.join(root_dir, fname))
        for name, raw in (parser.data or {}).items():
            body = _unwrap(raw)
            if isinstance(body, dict):
                base = _names(body.get("base_good"))
                if base:
                    bases[_entity_name(name)] = base[-1]
    return bases


def base_good(prestige_good: str, bases: dict, goods: dict) -> str | None:
    if prestige_good in bases:
        return bases[prestige_good]
    if prestige_good.startswith(GENERIC_PREFIX):
        good = prestige_good[len(GENERIC_PREFIX):]
        if good in goods:
            return good
    return None


# ---------------------------------------------------------------------------
# The audit
# ---------------------------------------------------------------------------


@dataclass
class Flag:
    kind: str
    company: str
    prestige_good: str
    base_good: str
    detail: str
    file: str | None = None
    line: int | None = None
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    companies_checked: int = 0
    companies_vanilla_only: int = 0
    prestige_goods_checked: int = 0
    # Prestige goods whose base good could not be resolved: {name: [company]}.
    unresolved: dict = field(default_factory=dict)


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def check(companies: dict, outputs: dict, bases: dict, goods: dict, sources: dict) -> AuditResult:
    """Judge merged `companies` against building `outputs` for every company
    the mod's `sources` touch."""
    result = AuditResult()
    for name in sorted(companies):
        src = sources.get(name)
        if src is None:
            result.companies_vanilla_only += 1
            continue
        body = _unwrap(companies[name])
        if not isinstance(body, dict):
            continue
        result.companies_checked += 1
        roster = _names(body.get("building_types"))
        extensions = _names(body.get("extension_building_types"))
        made = set().union(*(outputs.get(b, set()) for b in roster)) if roster else set()
        for pg in dict.fromkeys(_names(body.get("possible_prestige_goods"))):
            good = base_good(pg, bases, goods)
            if good is None:
                result.unresolved.setdefault(pg, []).append(name)
                continue
            result.prestige_goods_checked += 1
            if good in made:
                continue
            ext_makers = [b for b in extensions if good in outputs.get(b, set())]
            if ext_makers:
                kind = "extension_only"
                detail = f"`{good}` comes only from extension {', '.join(f'`{b}`' for b in ext_makers)}"
            else:
                kind = "not_produced"
                detail = f"no roster or extension building makes `{good}`"
            flag = Flag(kind, name, pg, good, detail)
            lines = src.prestige_goods.get(pg, [])
            for site in lines + src.openers:
                flag.file, flag.line = site[0], site[1]
                break
            for site in src.openers + lines:
                reviewed = _parse_reviewed(site[2])
                if reviewed:
                    flag.exemption = reviewed
                    break
            result.flags.append(flag)
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


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    if mod_state is None:
        mod_state = load_state(mod_path)
    outputs = building_outputs(
        mod_state.get_data("Buildings") or {},
        mod_state.get_data("PM Groups") or {},
        mod_state.get_data("PMs") or {},
    )
    return check(
        mod_state.get_data("Company Types") or {},
        outputs,
        load_prestige_bases(mod_path),
        mod_state.get_data("Goods") or {},
        scan_sources(mod_path),
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _describe(f: Flag) -> str:
    return f"`{f.company}`: `{f.prestige_good}` — {f.detail}"


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Prestige good roster audit report",
        "",
        "Auto-generated by `prestige_good_roster_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "A company makes its prestige goods in place of their base good, in",
        "its own buildings. A prestige good whose base good none of the",
        "company's `building_types` buildings produce never appears, and the",
        "engine logs nothing.",
        "",
        "Flagged, per prestige good of every company the mod touches:",
        "`not_produced` (no roster or extension building makes the base good)",
        "and `extension_only` (only an `extension_building_types` building",
        "does, which needs an industry charter; a company holds one at a time).",
        "",
        "Suppress a deliberate case with a trailing",
        "`# REVIEWED YYYY-MM-DD: rationale` comment on the prestige good's line",
        "in `possible_prestige_goods` or on the company's opening `<name> = {`",
        "line (covers every flag on that company).",
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
                where = f" ({f.file}:{f.line})" if f.file else ""
                out.append(f"- {_describe(f)}{where}")
            out.append("")

    out += ["## Reviewed Exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        # No line numbers: the company names the site, and an edit above it
        # would otherwise churn the report.
        for f in exemp:
            out.append(
                f"- {f.kind}: {_describe(f)} — **{f.exemption['date']}**: "
                f"{f.exemption['rationale']}"
            )
        out.append("")

    out += [
        "## Coverage",
        "",
        f"- mod-touched companies checked: {result.companies_checked}",
        f"- vanilla-only companies not judged: {result.companies_vanilla_only}",
        f"- prestige goods checked: {result.prestige_goods_checked}",
        f"- prestige goods with an unknown base good (vanilla named goods, not in"
        f" the snapshot), not judged: {len(result.unresolved)}",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        "",
    ]
    if result.unresolved:
        out += ["### Unknown base goods", ""]
        for pg in sorted(result.unresolved):
            out.append(f"- `{pg}`: {', '.join(f'`{c}`' for c in sorted(result.unresolved[pg]))}")
        out.append("")
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    unrev = sum(1 for f in result.flags if not f.exemption)
    return {
        "companies_checked": result.companies_checked,
        "prestige_goods_checked": result.prestige_goods_checked,
        "unresolved": len(result.unresolved),
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": len(result.flags) - unrev,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    print(render_report(result))
    # --strict: CI mode. Exit 1 if any flag lacks a `# REVIEWED ...` exemption.
    if "--strict" in sys.argv:
        raise SystemExit(1 if any(not f.exemption for f in result.flags) else 0)
