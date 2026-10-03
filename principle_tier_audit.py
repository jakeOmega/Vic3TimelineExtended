"""Audit for power bloc principle tiers that lose a lower tier's modifier.

Principle tiers do not stack. A group's tiers are mutually exclusive: when a
bloc moves from tier III to tier IV, tier III's `member_modifier`,
`leader_modifier`, `non_leader_modifier`, `power_bloc_modifier` and
`institution_modifier` all stop applying and tier IV's blocks replace them.
Each tier must therefore restate every modifier the tier below it carried, at
its full value. Vanilla marks the restated lines `# Modifiers from previous
level(s)`.

Writing a tier as a delta ("tier IV adds X") is engine-silent. Every modifier
name is valid and every block is valid, so nothing reaches any log; the
upgrade just takes the missing modifiers away. 62aa550 shipped the education
and advanced research ladders that way (tier III dropped tier II's
assimilation, tier V dropped tier IV's military research speed), and five
other mod ladders had carried the same kind of gap since they were written.

Checks
------
Per consecutive tier pair (lower -> higher) of every principle group:

- `dropped`: a modifier in any block of the lower tier appears in no block of
  the higher tier.
- `moved`: it appears, but in a different block (a flat `member_modifier`
  value that becomes a per-level `institution_modifier` one, say).
- `weaker`: same block, smaller magnitude (sign-aware: -0.25 -> -0.1 is
  weaker, as is 0.2 -> 0.1).
- `changed`: same block, a different non-numeric value (`yes` -> `no`).
- `institution_changed`: the lower tier names an `institution` and has an
  `institution_modifier`, and the higher tier names another or none.

Per mod-touched principle:

- `wrong_block`: a `power_bloc_*` modifier in a country-level block, or any
  other modifier in `power_bloc_modifier`. The first does nothing: modifiers
  flow down the graph (bloc -> country -> state), never up. The second
  probably works, since vanilla's `modifier_types.md` says a `country_` or
  `state_` key on a power bloc's modifier flows to its members, but no
  vanilla principle writes one there, and it hides the key from the tier
  comparison. `principle_divine_economics_4/5` restated tier III's
  `state_trade_advantage_same_religion_add` in `power_bloc_modifier`.
- `duplicate_block`: the same modifier block opened twice in one definition.
  Merge the two.

A pair is judged only when the mod defines, replaces or injects into at least
one of its two tiers. Vanilla-only pairs are left alone: vanilla's own drops
(Market Unification I -> II swaps the embargo ban and trade advantage for a
customs union; Defensive Cooperation II -> III ends army-model imposition) are
vanilla's design, and the mod has no line to carry a suppression on.

Suppression
-----------
A trailing `# REVIEWED YYYY-MM-DD: rationale` comment on any of:

- the higher tier's opening `<name> = {` line (also `REPLACE:` / `INJECT:`)
  in `common/power_bloc_principles/` — this covers every flag on that tier;
- the modifier's line in the higher tier (`moved`, `weaker`, `changed`,
  `wrong_block`) or in the lower tier (`dropped`, `moved`, `weaker`);
- for `institution_changed`, the higher tier's `institution = ...` line;
- for `duplicate_block`, either block's opening line.

Data source
-----------
The ladders are judged on merged data: vanilla tiers I-III with every mod
`REPLACE:` / `INJECT:` applied, plus the mod's own tiers. On a post-load run
that is the server's ModState. Run from the command line, the audit builds a
small ModState of its own (principles and principle groups only, vanilla from
the committed `vanilla_parsed/` snapshot), so it needs no game install and
runs in CI. Suppression comments and line numbers come from a raw-text scan of
the mod's principle files, because the parser drops both.
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

# Offset-preserving comment/string blanking, shared with the iterator audit so
# the audits agree on what "a commented-out line" means.
from iterator_limit_audit import blank_comments_and_strings

# The modifier blocks a principle can carry, in the order the report lists them.
BLOCKS = (
    "member_modifier",
    "leader_modifier",
    "non_leader_modifier",
    "power_bloc_modifier",
    "institution_modifier",
)

# ModState entity type -> directory under common/.
ENTITY_TYPES = {
    "Principles": "power_bloc_principles",
    "Principle Groups": "power_bloc_principle_groups",
}

PRINCIPLES_DIR = os.path.join("common", "power_bloc_principles")
REPORT_PATH = os.path.join("docs", "engine", "principle_tier_report.md")

KIND_ORDER = (
    "dropped",
    "moved",
    "weaker",
    "changed",
    "institution_changed",
    "wrong_block",
    "duplicate_block",
)

_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+)$"
)

_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[^\s{}#]+))?"
    r"|(?P<anon>\{)"
)


# ---------------------------------------------------------------------------
# Source scan: where each principle, block and modifier line lives in the mod
# ---------------------------------------------------------------------------

@dataclass
class Source:
    """Where the mod writes one principle. A principle can be opened more than
    once (a `REPLACE:` in one file, an `INJECT:` in another)."""

    # Sites are (file, line, comment-or-None).
    openers: list = field(default_factory=list)
    # (block, key) -> [site]; block None for a direct child (`institution`).
    keys: dict = field(default_factory=dict)
    # [(block, first site, second site)] for a block opened twice in one definition.
    duplicate_blocks: list = field(default_factory=list)


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _entity_name(key: str) -> str:
    # `REPLACE:principle_x`, `INJECT:principle_x`, `TRY_INJECT:principle_x`, ...
    return key.rsplit(":", 1)[-1]


def scan_text(text: str, rel_path: str, sources: dict | None = None) -> dict:
    """Record every principle opener, block opener and modifier line in one
    file's raw text into `sources` ({name: Source}) and return it."""
    if sources is None:
        sources = {}
    clean, comments = blank_comments_and_strings(text)
    starts = _line_starts(clean)
    stack: list = []
    current: Source | None = None
    blocks_seen: dict = {}  # block -> site, reset per definition

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
            continue
        if m.group("anon"):
            if stack:
                stack.append(None)
            continue

        key = m.group("key")
        line = bisect_right(starts, m.start())
        site = (rel_path, line, comments.get(line))

        if m.group("open"):
            if not stack:
                current = sources.setdefault(_entity_name(key), Source())
                current.openers.append(site)
                blocks_seen = {}
            elif len(stack) == 1 and key in BLOCKS and current is not None:
                if key in blocks_seen:
                    current.duplicate_blocks.append((key, blocks_seen[key], site))
                else:
                    blocks_seen[key] = site
            stack.append(key)
            continue

        if current is None:
            continue
        if len(stack) == 1:
            current.keys.setdefault((None, key), []).append(site)
        elif len(stack) == 2 and stack[1] in BLOCKS:
            current.keys.setdefault((stack[1], key), []).append(site)

    return sources


def scan_sources(mod_path: str) -> dict:
    sources: dict = {}
    root_dir = os.path.join(mod_path, PRINCIPLES_DIR)
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


def _is_pair(v) -> bool:
    return isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], str)


def _unwrap(v):
    """`('=', value)` -> value; a list of such (a repeated key) -> list of values."""
    if _is_pair(v):
        return v[1]
    if isinstance(v, (list, tuple)):
        return [_unwrap(x) for x in v]
    return v


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _block(principle: dict, blk: str) -> dict:
    """The modifiers in one block as {key: value-string}. A block repeated in
    the merged data is folded together, summing numbers the way an INJECT
    sums in game."""
    raw = principle.get(blk)
    if raw is None:
        return {}
    parts = [raw[1]] if _is_pair(raw) else [_unwrap(x) for x in raw]
    out: dict = {}
    for part in parts:
        if not isinstance(part, dict):
            continue
        for k, v in part.items():
            v = _unwrap(v)
            if isinstance(v, list):  # a repeated key: duplicate_key_audit's job
                v = v[-1]
            if k in out and _num(out[k]) is not None and _num(v) is not None:
                v = repr(_num(out[k]) + _num(v))
            out[k] = v
    return out


def _scalar(principle: dict, key: str):
    v = _unwrap(principle.get(key))
    if isinstance(v, list):
        v = v[-1] if v else None
    return v if isinstance(v, str) else None


def _levels(group: dict) -> list[str]:
    out: list[str] = []

    def walk(v):
        v = _unwrap(v)
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)

    walk(group.get("levels"))
    return out


def _weaker(lo: float, hi: float) -> bool:
    return (lo > 0 and hi < lo) or (lo < 0 and hi > lo)


# ---------------------------------------------------------------------------
# The audit
# ---------------------------------------------------------------------------


@dataclass
class Flag:
    kind: str
    group: str | None
    lower: str | None  # the tier below, for the pair checks
    principle: str  # the tier the flag is about (the higher one in a pair)
    block: str | None
    key: str
    detail: str
    file: str | None = None
    line: int | None = None
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    groups_checked: int = 0
    pairs_checked: int = 0
    pairs_vanilla_only: int = 0
    principles_touched: int = 0


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _resolve(flag: Flag, locate: list, exempt: list) -> Flag:
    """Point the flag at the first site in `locate` and exempt it if any site
    in `exempt` carries a REVIEWED comment."""
    for site in locate:
        flag.file, flag.line = site[0], site[1]
        break
    for site in exempt:
        reviewed = _parse_reviewed(site[2])
        if reviewed:
            flag.exemption = reviewed
            break
    return flag


def _compare(group, lower, higher, p_lo, p_hi, sources) -> list[Flag]:
    src_lo = sources.get(lower, Source())
    src_hi = sources.get(higher, Source())
    lo = {blk: _block(p_lo, blk) for blk in BLOCKS}
    hi = {blk: _block(p_hi, blk) for blk in BLOCKS}
    flags: list[Flag] = []

    def emit(kind, blk_lo, blk_hi, key, detail):
        hi_sites = src_hi.keys.get((blk_hi, key), []) if blk_hi or key == "institution" else []
        lo_sites = src_lo.keys.get((blk_lo, key), []) if blk_lo else []
        flag = Flag(kind, group, lower, higher, blk_hi or blk_lo, key, detail)
        flags.append(_resolve(
            flag,
            locate=hi_sites + src_hi.openers + lo_sites + src_lo.openers,
            exempt=src_hi.openers + hi_sites + lo_sites,
        ))

    inst_lo, inst_hi = _scalar(p_lo, "institution"), _scalar(p_hi, "institution")
    if inst_lo and inst_hi != inst_lo and lo["institution_modifier"]:
        emit("institution_changed", None, None, "institution",
             f"`{inst_lo}` -> `{inst_hi or 'none'}`")

    for blk in BLOCKS:
        for key, v in lo[blk].items():
            if key in hi[blk]:
                w = hi[blk][key]
                n_lo, n_hi = _num(v), _num(w)
                if n_lo is not None and n_hi is not None:
                    if _weaker(n_lo, n_hi):
                        emit("weaker", blk, blk, key, f"{v} -> {w}")
                elif v != w:
                    emit("changed", blk, blk, key, f"{v} -> {w}")
                continue
            elsewhere = [b for b in BLOCKS if b != blk and key in hi[b]]
            if elsewhere:
                emit("moved", blk, elsewhere[0], key,
                     f"`{blk}` {v} -> `{elsewhere[0]}` {hi[elsewhere[0]][key]}")
            else:
                emit("dropped", blk, None, key, f"`{blk}` {v} -> absent")
    return flags


def _wrong_blocks(name, principle, src) -> list[Flag]:
    flags = []
    for blk in BLOCKS:
        for key in _block(principle, blk):
            if (blk == "power_bloc_modifier") == key.startswith("power_bloc_"):
                continue
            sites = src.keys.get((blk, key), [])
            if blk == "power_bloc_modifier":
                detail = "in `power_bloc_modifier`; vanilla keeps member effects in `member_modifier`"
            else:
                detail = f"in `{blk}`, where a bloc-level key does nothing; belongs in `power_bloc_modifier`"
            flag = Flag("wrong_block", None, None, name, blk, key, detail)
            flags.append(_resolve(flag, sites + src.openers, src.openers + sites))
    return flags


def _duplicate_blocks(name, src) -> list[Flag]:
    flags = []
    for blk, first, second in src.duplicate_blocks:
        flag = Flag("duplicate_block", None, None, name, blk, blk,
                    f"opened twice, at lines {first[1]} and {second[1]}")
        flags.append(_resolve(flag, [second], [first, second] + src.openers))
    return flags


def check(principles: dict, groups: dict, sources: dict) -> AuditResult:
    """Judge merged `principles` / `groups` data against the mod's `sources`."""
    result = AuditResult(principles_touched=sum(1 for n in sources if n in principles))
    for gname in sorted(groups):
        levels = _levels(_unwrap(groups[gname]))
        judged = False
        for lower, higher in zip(levels, levels[1:]):
            if lower not in sources and higher not in sources:
                result.pairs_vanilla_only += 1
                continue
            if lower not in principles or higher not in principles:
                continue  # a missing principle is mod_structure_audit's to report
            judged = True
            result.pairs_checked += 1
            result.flags.extend(_compare(
                gname, lower, higher,
                _unwrap(principles[lower]), _unwrap(principles[higher]), sources,
            ))
        result.groups_checked += judged

    for name in sorted(sources):
        if name in principles:
            result.flags.extend(_wrong_blocks(name, _unwrap(principles[name]), sources[name]))
        result.flags.extend(_duplicate_blocks(name, sources[name]))
    return result


def load_state(mod_path: str, vanilla_data: dict | None = None):
    """A ModState holding only principles and principle groups: vanilla from
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
    principles = mod_state.get_data("Principles") or {}
    groups = mod_state.get_data("Principle Groups") or {}
    return check(principles, groups, scan_sources(mod_path))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _describe(f: Flag) -> str:
    if f.lower:
        return f"`{f.lower}` -> `{f.principle}`: `{f.key}` {f.detail}"
    return f"`{f.principle}`: `{f.key}` {f.detail}"


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Principle tier audit report",
        "",
        "Auto-generated by `principle_tier_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Power bloc principle tiers do not stack: a higher tier's blocks",
        "replace the lower tier's, so each tier must restate every modifier",
        "the tier below carried. A tier that leaves one out takes it away on",
        "upgrade, and the engine logs nothing.",
        "",
        "Flagged, per consecutive tier pair the mod touches: a modifier the",
        "higher tier `dropped`, `moved` to another block, made `weaker` or",
        "`changed`, and an `institution_changed` that strands the lower tier's",
        "`institution_modifier`. Per mod-touched principle: a modifier in the",
        "`wrong_block` (a `power_bloc_*` key outside `power_bloc_modifier` does",
        "nothing; any other key inside it is unlike every vanilla principle)",
        "and a `duplicate_block`. Pairs where both tiers are untouched vanilla",
        "are not judged.",
        "",
        "Suppress a deliberate case with a trailing",
        "`# REVIEWED YYYY-MM-DD: rationale` comment on the higher tier's opening",
        "`<name> = {` line (covers every flag on that tier) or on the",
        "modifier's line in either tier.",
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
        # No line numbers: the principle names the site, and an edit above it
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
        f"- vanilla-only tier pairs not judged: {result.pairs_vanilla_only}",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        "",
    ]
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
        "groups_checked": result.groups_checked,
        "pairs_checked": result.pairs_checked,
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
