"""Detects mod modifier values too small to display given the modifier type's
`decimals = N` rounding precision.

Background: Vic3 modifier types declare a `decimals` field controlling display
rounding. With `decimals = 0` and `percent = yes` (the case for vanilla
`country_prestige_mult` and ~37% of all vanilla modifier types), any value with
|value| < 0.005 displays as "+0%" — silently invisible while still applying
mechanically. Mod authors who forget to anchor against the type's display
precision quietly ship invisible bonuses.

Suppress an intentional sub-threshold value with a same-line comment:

    country_prestige_mult = 0.001  # REVIEWED 2026-05-06: stacks with N copies

The registry of `decimals` / `percent` per modifier name is built by
mod_state_server's _union_vanilla_modifier_decimals + _union_mod_modifier_types
passes; this module reads the merged engine_docs['modifiers'] table.
"""
import os
import re
from dataclasses import dataclass, field


@dataclass
class VisibilityFlag:
    file: str
    line: int
    modifier: str
    value: str          # original literal as written
    value_float: float
    decimals: int
    percent: bool
    min_visible: float  # smallest |value| that renders non-zero
    exemption: dict | None = None  # {date, rationale} when REVIEWED


@dataclass
class AuditResult:
    flags: list[VisibilityFlag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


# Matches `key = literal_number` as the entire content of a line (allowing
# leading whitespace and trailing comment). The regex is intentionally strict:
# - LHS must be a snake_case identifier with no `:` (excludes scope accessors).
# - RHS must be the only value (excludes block bodies, multi-value lines).
# This way the registry filter (key in modifier registry) is the only thing
# distinguishing modifier uses from arbitrary `<key> = <number>` lines.
_LINE_RE = re.compile(
    r"^[ \t]*(?P<key>[a-z_][a-z0-9_]*)\s*=\s*(?P<value>-?\d+(?:\.\d+)?)"
    r"(?:\s*(?P<comment>#.*))?\s*$"
)

# Wrapper blocks where modifier values are deliberately small per-unit numbers
# multiplied at runtime by pop count / level / throughput. Vanilla pattern:
# `country_modifiers = { workforce_scaled = { country_authority_add = 0.1 } }`
# applies 0.1 × workforce, often pushing the displayed value far above the
# decimals threshold even though the literal is sub-threshold. Suppressing
# these blocks avoids systematic false positives across PMs and buildings.
_SCALING_WRAPPER_RE = re.compile(
    r"(?P<key>workforce_scaled|level_scaled|throughput_scaled)\s*=\s*\{"
)

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


def _min_visible_abs(decimals: int, percent: bool) -> float:
    """Smallest |value| that displays as non-zero given decimals + percent.

    Engine displays `value * (100 if percent else 1)` rounded to `decimals`
    places. Anything below `0.5 * 10^-decimals` of the displayed magnitude
    rounds to 0.
    """
    base = 0.5 * (10 ** (-decimals))
    return base / 100.0 if percent else base


def _build_registry(engine_modifiers: list[dict]) -> dict[str, tuple[int, bool]]:
    """{name: (decimals, percent_bool)} for every modifier with captured decimals."""
    reg: dict[str, tuple[int, bool]] = {}
    for entry in engine_modifiers:
        decimals = entry.get("decimals")
        if decimals is None:
            continue
        try:
            decimals_int = int(decimals)
        except (TypeError, ValueError):
            continue
        percent = bool(entry.get("percent", False))
        reg[entry.get("name", "")] = (decimals_int, percent)
    return reg


# Subdirectories under common/ that don't contain modifier USES (only registry
# definitions or scalar value definitions). Scanning them produces only noise.
_SKIP_COMMON_SUBDIRS = frozenset({
    "modifier_type_definitions",  # the registry itself
    "script_values",              # scalar definitions; field names look modifier-shaped
    "scripted_progress_bars",     # progress bar fields, not modifier uses
    "scripted_triggers",          # `key > value` shape, not `key = value`
    "scripted_guis",              # GUI bindings
    "pop_needs",                  # uses pop-need DSL keys that overlap modifier names
    # Pure data definitions:
    "cultures", "religions", "country_ranks", "discrimination_traits",
    "pop_types", "goods", "buy_packages",
    # Heritage entries: harmless to scan but no modifier uses
    "country_creation",
    "coat_of_arms",
})


def _scan_file(file_path: str, rel_path: str, registry: dict[str, tuple[int, bool]]) -> tuple[list[VisibilityFlag], int]:
    """Scan one file for sub-threshold modifier-value lines.

    Returns (flags, registry_hits) where registry_hits counts how many lines
    matched a registry key (regardless of whether they were flagged) — useful
    for coverage reporting.
    """
    flags: list[VisibilityFlag] = []
    hits = 0
    try:
        with open(file_path, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return flags, 0

    # Brace-depth state for scaling-wrapper suppression. When we see
    # `workforce_scaled = {`, remember the depth-after-opening; we're inside
    # the wrapper until depth drops back to that level.
    depth = 0
    scaling_depths: list[int] = []  # stack of depths-after-opening for active wrappers

    for i, line in enumerate(text.splitlines(), start=1):
        # Strip line comments before brace counting so `# foo {` doesn't
        # corrupt the depth.
        nocomment = line.split("#", 1)[0]

        # Detect scaling-wrapper openings on this line BEFORE applying its
        # own brace deltas — the wrapper's `{` is part of those deltas.
        for wm in _SCALING_WRAPPER_RE.finditer(nocomment):
            # `wm.end()` is the position right after the wrapper's `{`, so the
            # opens count up through wm.end() already includes that brace.
            # depth-after-opening = previous depth + opens_so_far − closes_so_far.
            opens_before = nocomment[:wm.end()].count("{")
            closes_before = nocomment[:wm.end()].count("}")
            scaling_depths.append(depth + opens_before - closes_before)

        opens = nocomment.count("{")
        closes = nocomment.count("}")
        new_depth = depth + opens - closes

        # Pop any scaling wrappers we've now exited.
        while scaling_depths and new_depth < scaling_depths[-1]:
            scaling_depths.pop()

        in_scaling = bool(scaling_depths)

        m = _LINE_RE.match(line)
        if m:
            key = m.group("key")
            spec = registry.get(key)
            if spec is not None and not in_scaling:
                hits += 1
                decimals, percent = spec
                try:
                    value_float = float(m.group("value"))
                except ValueError:
                    value_float = None
                if value_float is not None and value_float != 0.0:
                    min_visible = _min_visible_abs(decimals, percent)
                    if abs(value_float) < min_visible:
                        flags.append(VisibilityFlag(
                            file=rel_path,
                            line=i,
                            modifier=key,
                            value=m.group("value"),
                            value_float=value_float,
                            decimals=decimals,
                            percent=percent,
                            min_visible=min_visible,
                            exemption=_parse_reviewed(m.group("comment")),
                        ))

        depth = new_depth
    return flags, hits


def _iter_scan_files(mod_path: str):
    """Yield (abs_path, rel_path) for every .txt file we want to audit."""
    events_dir = os.path.join(mod_path, "events")
    if os.path.isdir(events_dir):
        for fname in sorted(os.listdir(events_dir)):
            if fname.endswith(".txt"):
                yield os.path.join(events_dir, fname), os.path.join("events", fname)

    common_dir = os.path.join(mod_path, "common")
    if os.path.isdir(common_dir):
        for sub in sorted(os.listdir(common_dir)):
            if sub in _SKIP_COMMON_SUBDIRS:
                continue
            sub_path = os.path.join(common_dir, sub)
            if not os.path.isdir(sub_path):
                continue
            for root, _dirs, files in os.walk(sub_path):
                for fname in sorted(files):
                    if not fname.endswith(".txt"):
                        continue
                    abs_p = os.path.join(root, fname)
                    rel_p = os.path.relpath(abs_p, mod_path)
                    yield abs_p, rel_p


def _resolve_engine_modifiers() -> list[dict]:
    """Find the running server's engine_docs['modifiers'] list.

    `mod_state_server.py` runs as `__main__`, so a plain `import mod_state_server`
    creates a SECOND module instance with its own (empty) globals. To reach the
    live engine_docs, look up the running module via sys.modules first.
    """
    import sys
    main_mod = sys.modules.get("__main__")
    docs = getattr(main_mod, "engine_docs", None) if main_mod else None
    if docs:
        return docs.get("modifiers", []) or []
    # Fallback for callers that imported mod_state_server normally
    # (e.g. ad-hoc scripts, tests).
    try:
        import mod_state_server
    except ImportError:
        return []
    docs = getattr(mod_state_server, "engine_docs", None) or {}
    return docs.get("modifiers", []) or []


def audit(ms, mod_path: str | None = None, engine_modifiers: list[dict] | None = None) -> AuditResult:
    """Walk events/ + common/ for sub-threshold modifier values.

    `engine_modifiers` defaults to the live engine_docs['modifiers'] table
    inside the running mod_state_server. Tests can pass an explicit list.
    """
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    if engine_modifiers is None:
        engine_modifiers = _resolve_engine_modifiers()

    registry = _build_registry(engine_modifiers)
    flags: list[VisibilityFlag] = []
    files_audited = 0
    registry_hits = 0
    for abs_p, rel_p in _iter_scan_files(mod_path):
        f, hits = _scan_file(abs_p, rel_p, registry)
        flags.extend(f)
        registry_hits += hits
        files_audited += 1

    return AuditResult(
        flags=flags,
        coverage={
            "files_audited": files_audited,
            "modifiers_in_registry_with_decimals": len(registry),
            "registry_hits": registry_hits,
        },
    )


def _format_displayed(flag: VisibilityFlag) -> str:
    """How the value renders in tooltips (always rounds to 0 here, by construction)."""
    return "+0%" if flag.percent else "+0"


def _format_intended(flag: VisibilityFlag) -> str:
    """The author's likely intent — the literal value with one extra decimal
    place so the hidden magnitude is visible."""
    extra = flag.decimals + (2 if flag.percent else 1)
    if flag.percent:
        return f"{flag.value_float * 100:+.{extra}f}%"
    return f"{flag.value_float:+.{extra}f}"


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Modifier visibility audit report",
        "",
        "Auto-generated by `modifier_visibility_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a literal modifier value too small to display non-zero given",
        "the modifier type's `decimals = N` (and `percent = yes/no`) precision.",
        "The modifier still applies mechanically — only the tooltip rounds to 0.",
        "",
        "Two ways to fix:",
        "1. **Bump the value** above the visibility threshold (preferred —",
        "   small-by-design effects probably aren't doing what you want).",
        "2. **Override the modifier type's `decimals`** in",
        "   `common/modifier_type_definitions/`.",
        "",
        "Suppress an intentional sub-threshold value with a same-line comment:",
        "`# REVIEWED YYYY-MM-DD: rationale`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        by_modifier: dict[str, list[VisibilityFlag]] = {}
        for f in unrev:
            by_modifier.setdefault(f.modifier, []).append(f)
        for modifier in sorted(by_modifier):
            sample = by_modifier[modifier][0]
            pct = " percent=yes" if sample.percent else ""
            out.append(
                f"### `{modifier}` ({len(by_modifier[modifier])}) — "
                f"decimals={sample.decimals}{pct}, threshold |value| ≥ {sample.min_visible:g}"
            )
            out.append("")
            for f in by_modifier[modifier]:
                out.append(
                    f"- `{f.file}:{f.line}` — `{f.modifier} = {f.value}` "
                    f"(intended: {_format_intended(f)}) → displays as "
                    f"{_format_displayed(f)}"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.line}` — `{f.modifier} = {f.value}` "
                f"(displays as {_format_displayed(f)}) — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    for k, v in result.coverage.items():
        out.append(f"- {k}: {v}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")
    out.append("## Scope notes")
    out.append("")
    out.append(
        "- Skips literal `multiplier = N` inside `add_modifier { name = X "
        "multiplier = N }`. The static modifier X's own field values are "
        "audited when its body is walked; multiplier-stack analysis (where "
        "X's value × N is sub-threshold) is out of scope for v1."
    )
    out.append(
        "- Skips script-value references (`sv_*`, any non-numeric RHS) — "
        "they're evaluated at runtime."
    )
    out.append(
        "- Skips modifier types with no captured `decimals` (defensive — no "
        "false positives on unknown precision)."
    )

    return "\n".join(out) + "\n"


def regenerate(mod_state) -> dict:
    """POST_LOAD_GENERATORS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "modifier_visibility_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    return {
        "files_audited": result.coverage.get("files_audited", 0),
        "modifiers_in_registry_with_decimals": result.coverage.get(
            "modifiers_in_registry_with_decimals", 0
        ),
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }
