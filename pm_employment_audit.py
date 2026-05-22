"""Detects buildings where some valid PM combination drives a profession's
employment total negative.

Background: a Vic3 building selects exactly one production method from each of
its PM groups. Each PM contributes employment per profession via
`building_employment_<profession>_add` modifiers inside `level_scaled` /
`workforce_scaled` blocks under `building_modifiers`. Negative adds are a
legitimate idiom — automation/refinement PMs *reduce* a profession that a base
PM adds. The bug this catches: a player can pick a **combination** of PMs whose
per-profession total sums **below zero**, which is incoherent (the engine can't
employ a negative headcount). The classic case is a low-employment base PM
(e.g. `GMO_plantation_…`, +1000 laborers) paired with an aggressive automation
PM (e.g. `centrifugal_machine_sugar`, −3500 laborers) → −2500 laborers.

Approach: for each building, enumerate the **valid** combinations (one PM per
group, honoring `unlocking_production_methods` — a PM with that field is only
selectable when at least one referenced PM is also in the combination). For
each scaling bucket (`level_scaled` / `workforce_scaled` / bare) and each
profession, find the minimum total across valid combinations. A negative
minimum means a buggy combination exists; the argmin combination is reported as
the reproduction.

Scope: all merged (mod ∪ vanilla) buildings. A flag is **mod-relevant** if the
building or any contributing PM is defined in a mod file (located under the
mod's `common/buildings` or `common/production_methods`). Flags whose offending
combo touches no mod-defined entity are segregated into an informational
"vanilla-only" section and do **not** count toward `unreviewed`.

`unlocking_technologies` / `unlocking_principles` are ignored — those gate by
research/principle, both reachable late-game, so they don't make a combination
permanently unreachable.

Suppress an intentional negative with a same-line `# REVIEWED` comment on the
opening line of either the building (in `common/buildings`) or the
most-negative contributing PM (in `common/production_methods`):

    centrifugal_machine_sugar = { # REVIEWED 2026-05-22: intentional, base always >= 4000

Note this is broad — a REVIEWED on a PM suppresses every building where that PM
is the worst contributor. The primary remedy is rebalancing the values so no
valid combo goes negative; suppression is the escape hatch for deliberate cases.
"""
import itertools
import os
import re
from dataclasses import dataclass, field


@dataclass
class Contribution:
    group: str
    pm: str
    value: float
    file: str | None
    line: int | None


@dataclass
class EmploymentFlag:
    building: str
    profession: str
    scaling: str
    total: float
    combo: list[Contribution]
    mod_relevant: bool
    file: str | None  # anchor used for suppression / report (building or worst PM)
    line: int | None
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[EmploymentFlag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)

# Guard against pathological Cartesian products. No real building approaches
# this (sugar plantation is 4×4×3×4 = 192); a building exceeding it is recorded
# as skipped rather than enumerated.
_COMBO_CAP = 200_000

_EMP_PREFIX = "building_employment_"
_EMP_SUFFIX = "_add"
# Vic3 building_modifiers sub-blocks. `unscaled` and bare (directly under
# building_modifiers) adds share the "unscaled" bucket.
_SCALING_BLOCKS = ("workforce_scaled", "level_scaled", "unscaled")
_BARE_BUCKET = "unscaled"


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _unwrap(value):
    if (
        isinstance(value, tuple)
        and len(value) == 2
        and value[0] in ("=", "?=", ">=", "<=", ">", "<", "!=")
    ):
        return _unwrap(value[1])
    return value


def _as_list(value) -> list:
    """Normalize a parsed field to a list of unwrapped items. Handles a single
    scalar, a list, or a list nested in `('=', [...])`."""
    v = _unwrap(value)
    if v is None:
        return []
    if isinstance(v, list):
        return [_unwrap(x) for x in v]
    return [v]


def _to_float(value) -> float | None:
    v = _unwrap(value)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


_OPENING_LINE_RE = re.compile(
    r"^[ \t]*(?:REPLACE_OR_CREATE:|REPLACE:|INJECT:|CREATE:)?"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{(?P<comment>\s*#.*)?\s*$"
)


def _build_entity_locations(
    mod_path: str, dir_rel: str, entity_names: set[str]
) -> dict[str, tuple[str, int, str | None]]:
    """For each entity name defined in `<mod_path>/<dir_rel>`, find
    (rel_path, line, opening_line_comment). Presence here means the mod defines
    or overrides the entity. Recognizes Paradox merge prefixes
    (REPLACE_OR_CREATE: etc.) on the opening line."""
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


def _pm_employment(pm_body) -> dict[str, dict[str, float]]:
    """Extract a PM's employment adds, bucketed by scaling context.

    Returns {bucket: {profession: value}} where bucket is `level_scaled`,
    `workforce_scaled`, or `unscaled` (bare `building_modifiers` adds)."""
    out: dict[str, dict[str, float]] = {}
    body = _unwrap(pm_body)
    if not isinstance(body, dict):
        return out
    bm = _unwrap(body.get("building_modifiers"))
    if not isinstance(bm, dict):
        return out

    def collect(bucket: str, block: dict):
        for k, v in block.items():
            if not (isinstance(k, str) and k.startswith(_EMP_PREFIX) and k.endswith(_EMP_SUFFIX)):
                continue
            val = _to_float(v)
            if val is None:
                continue
            prof = k[len(_EMP_PREFIX):-len(_EMP_SUFFIX)]
            out.setdefault(bucket, {})[prof] = out.setdefault(bucket, {}).get(prof, 0.0) + val

    for key, val in bm.items():
        if key in _SCALING_BLOCKS:
            inner = _unwrap(val)
            if isinstance(inner, dict):
                collect(_BARE_BUCKET if key == "unscaled" else key, inner)
        elif isinstance(key, str) and key.startswith(_EMP_PREFIX) and key.endswith(_EMP_SUFFIX):
            f = _to_float(val)
            if f is not None:
                prof = key[len(_EMP_PREFIX):-len(_EMP_SUFFIX)]
                out.setdefault(_BARE_BUCKET, {})[prof] = (
                    out.setdefault(_BARE_BUCKET, {}).get(prof, 0.0) + f
                )
    return out


def _pm_unlock_pms(pm_body) -> list[str]:
    body = _unwrap(pm_body)
    if not isinstance(body, dict):
        return []
    return [str(x) for x in _as_list(body.get("unlocking_production_methods"))]


def _resolve_groups(building_body, pmg_data) -> list[tuple[str, list[str]]]:
    """Return [(group_name, [pm_names])] for a building, in declared order.
    Drops groups that resolve to no PMs."""
    body = _unwrap(building_body)
    if not isinstance(body, dict):
        return []
    groups: list[tuple[str, list[str]]] = []
    for gname in _as_list(body.get("production_method_groups")):
        gname = str(gname)
        gbody = _unwrap(pmg_data.get(gname)) if pmg_data else None
        if not isinstance(gbody, dict):
            continue
        pms = [str(p) for p in _as_list(gbody.get("production_methods"))]
        if pms:
            groups.append((gname, pms))
    return groups


def _audit_building(
    building: str,
    building_body,
    pmg_data,
    pm_data,
    building_locations,
    pm_locations,
) -> tuple[list[EmploymentFlag], bool, bool]:
    """Audit one building. Returns (flags, enumerated, skipped_large)."""
    groups = _resolve_groups(building_body, pmg_data)
    if not groups:
        return [], False, False

    # Per-PM employment buckets and unlock requirements.
    pm_emp: dict[str, dict[str, dict[str, float]]] = {}
    pm_unlock: dict[str, list[str]] = {}
    all_pms_in_building: set[str] = set()
    for _g, pms in groups:
        for pm in pms:
            all_pms_in_building.add(pm)
            if pm not in pm_emp:
                body = pm_data.get(pm) if pm_data else None
                pm_emp[pm] = _pm_employment(body)
                pm_unlock[pm] = _pm_unlock_pms(body)

    # Prune: only enumerate if some PM has a negative employment add somewhere.
    has_negative = any(
        v < 0
        for buckets in pm_emp.values()
        for profmap in buckets.values()
        for v in profmap.values()
    )
    if not has_negative:
        return [], False, False

    # Combination-count guard.
    combo_count = 1
    for _g, pms in groups:
        combo_count *= len(pms)
        if combo_count > _COMBO_CAP:
            return [], False, True

    group_names = [g for g, _ in groups]
    group_pms = [pms for _, pms in groups]
    buckets = {b for buckets in pm_emp.values() for b in buckets}
    professions = {
        p for buckets in pm_emp.values() for profmap in buckets.values() for p in profmap
    }

    # min_total[(bucket, prof)] = (value, combo_tuple)
    min_total: dict[tuple[str, str], tuple[float, tuple[str, ...]]] = {}
    any_valid = False
    for combo in itertools.product(*group_pms):
        combo_set = set(combo)
        # Validity: every selected PM with unlock reqs must have one satisfied.
        valid = True
        for pm in combo:
            reqs = pm_unlock.get(pm)
            if reqs and not any(r in combo_set for r in reqs):
                valid = False
                break
        if not valid:
            continue
        any_valid = True
        for bucket in buckets:
            for prof in professions:
                total = 0.0
                for pm in combo:
                    total += pm_emp.get(pm, {}).get(bucket, {}).get(prof, 0.0)
                key = (bucket, prof)
                cur = min_total.get(key)
                if cur is None or total < cur[0]:
                    min_total[key] = (total, combo)

    if not any_valid:
        return [], True, False

    flags: list[EmploymentFlag] = []
    for (bucket, prof), (total, combo) in min_total.items():
        if total >= 0:
            continue
        contributions: list[Contribution] = []
        worst_pm = None
        worst_val = 0.0
        for gname, pm in zip(group_names, combo):
            val = pm_emp.get(pm, {}).get(bucket, {}).get(prof, 0.0)
            loc = pm_locations.get(pm)
            contributions.append(
                Contribution(
                    group=gname, pm=pm, value=val,
                    file=loc[0] if loc else None, line=loc[1] if loc else None,
                )
            )
            if val < worst_val:
                worst_val = val
                worst_pm = pm

        # mod-relevance: building overridden by mod, or any contributing PM
        # defined in a mod file.
        mod_relevant = building in building_locations or any(
            c.pm in pm_locations for c in contributions
        )

        # Suppression: a REVIEWED on the building's OR the worst PM's opening
        # line exempts the flag. Report anchor: the building's mod location if
        # any, else the most-negative contributing mod PM's.
        bld_loc = building_locations.get(building)
        pm_loc = pm_locations.get(worst_pm)
        exemption = _parse_reviewed(bld_loc[2] if bld_loc else None) or _parse_reviewed(
            pm_loc[2] if pm_loc else None
        )
        anchor = bld_loc or pm_loc
        anchor_file = anchor[0] if anchor else None
        anchor_line = anchor[1] if anchor else None

        flags.append(EmploymentFlag(
            building=building,
            profession=prof,
            scaling=bucket,
            total=total,
            combo=contributions,
            mod_relevant=mod_relevant,
            file=anchor_file,
            line=anchor_line,
            exemption=exemption,
        ))
    return flags, True, False


def audit(ms, mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    buildings = ms.get_data("Buildings") or {}
    pmg_data = ms.get_data("PM Groups") or {}
    pm_data = ms.get_data("PMs") or {}

    building_locations = _build_entity_locations(
        mod_path, "common/buildings", set(buildings.keys())
    )
    pm_locations = _build_entity_locations(
        mod_path, "common/production_methods", set(pm_data.keys())
    )

    all_flags: list[EmploymentFlag] = []
    enumerated = 0
    skipped_large = 0
    for building in sorted(buildings.keys()):
        flags, did_enum, skipped = _audit_building(
            building, buildings[building], pmg_data, pm_data,
            building_locations, pm_locations,
        )
        if did_enum:
            enumerated += 1
        if skipped:
            skipped_large += 1
        all_flags.extend(flags)

    return AuditResult(
        flags=all_flags,
        coverage={
            "buildings_audited": len(buildings),
            "buildings_enumerated": enumerated,
            "buildings_skipped_large": skipped_large,
        },
    )


def _fmt_combo(flag: EmploymentFlag) -> list[str]:
    lines = []
    for c in flag.combo:
        loc = f" (`{c.file}:{c.line}`)" if c.file else ""
        sign = f"{c.value:+.0f}" if c.value else "0"
        lines.append(f"    - {c.group}: `{c.pm}` → {sign}{loc}")
    return lines


def render_report(result: AuditResult) -> str:
    neg = [f for f in result.flags]
    mod_unrev = [f for f in neg if f.mod_relevant and not f.exemption]
    mod_exemp = [f for f in neg if f.mod_relevant and f.exemption]
    vanilla = [f for f in neg if not f.mod_relevant]

    out = [
        "# PM employment combination audit report",
        "",
        "Auto-generated by `pm_employment_audit.py` on every full `POST /reload`",
        "of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a building where some **valid** combination of production",
        "methods (one per PM group, honoring `unlocking_production_methods`)",
        "drives a profession's employment total **below zero** in a given",
        "scaling bucket (`level_scaled` / `workforce_scaled` / `unscaled`). The",
        "engine can't employ a negative headcount, so such a combination is",
        "incoherent. The worst-case combination is shown as the reproduction.",
        "",
        "Fix: rebalance the offending mod PM employment values so no valid combo",
        "goes negative (raise the lowest base PM, or cap the automation",
        "reduction). Suppress a deliberate case with a same-line `# REVIEWED`",
        "comment on the building's or the worst PM's opening line:",
        "`<entity> = { # REVIEWED YYYY-MM-DD: rationale`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not mod_unrev:
        out += ["_None._", ""]
    else:
        by_building: dict[str, list[EmploymentFlag]] = {}
        for f in mod_unrev:
            by_building.setdefault(f.building, []).append(f)
        for building in sorted(by_building):
            anchor = ""
            loc = by_building[building][0]
            if loc.file:
                anchor = f" (`{loc.file}:{loc.line}`)"
            out.append(f"### `{building}`{anchor}")
            out.append("")
            for f in by_building[building]:
                out.append(
                    f"- **{f.profession}** ({f.scaling}): worst total "
                    f"**{f.total:+.0f}** via:"
                )
                out += _fmt_combo(f)
            out.append("")

    out += ["## Reviewed Exemptions", ""]
    if not mod_exemp:
        out += ["_None._", ""]
    else:
        for f in mod_exemp:
            anchor = f"`{f.file}:{f.line}`" if f.file else "(no anchor)"
            out.append(
                f"- {anchor} — `{f.building}` — **{f.profession}** ({f.scaling}) "
                f"total {f.total:+.0f} — **{f.exemption['date']}**: "
                f"{f.exemption['rationale']}"
            )
        out.append("")

    out += ["## Vanilla-only (informational)", ""]
    out += [
        "Combinations whose offending PMs and building are all vanilla — the",
        "mod doesn't define or override any participant. Not counted as",
        "warnings; listed so a vanilla bump that introduces one is visible.",
        "",
    ]
    if not vanilla:
        out += ["_None._", ""]
    else:
        for f in vanilla:
            combo = ", ".join(f"`{c.pm}`{c.value:+.0f}" for c in f.combo if c.value)
            out.append(
                f"- `{f.building}` — **{f.profession}** ({f.scaling}) "
                f"total {f.total:+.0f} via {combo}"
            )
        out.append("")

    out += ["## Coverage", ""]
    cov = result.coverage
    out.append(f"- buildings audited: {cov.get('buildings_audited', 0)}")
    out.append(f"- buildings enumerated (had a negative-employment PM): "
               f"{cov.get('buildings_enumerated', 0)}")
    out.append(f"- buildings skipped (combo count > {_COMBO_CAP}): "
               f"{cov.get('buildings_skipped_large', 0)}")
    out.append(f"- total negative combinations: {len(neg)}")
    out.append(f"- mod-relevant unreviewed: {len(mod_unrev)}")
    out.append(f"- mod-relevant exempted: {len(mod_exemp)}")
    out.append(f"- vanilla-only: {len(vanilla)}")
    out.append("")
    out += ["## Scope notes", ""]
    out += [
        "- Audits all merged (mod ∪ vanilla) buildings. A flag is mod-relevant"
        " if the building or any contributing PM is defined under the mod's"
        " `common/buildings` or `common/production_methods`.",
        "- Honors `unlocking_production_methods` (a PM is selectable only when a"
        " referenced PM is also in the combination); ignores"
        " `unlocking_technologies` / `unlocking_principles` (late-game"
        " reachable).",
        "- Buckets employment by scaling context (`level_scaled` /"
        " `workforce_scaled` / `unscaled`) — a level-scaled negative is not"
        " assumed to cancel a workforce-scaled positive (they scale by"
        " different factors).",
        "- Only enumerates buildings that contain at least one PM with a"
        " negative employment add (no negative add ⇒ no negative total"
        " possible).",
    ]
    return "\n".join(out) + "\n"


def regenerate(mod_state) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "pm_employment_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    mod_unrev = sum(1 for f in result.flags if f.mod_relevant and not f.exemption)
    mod_exemp = sum(1 for f in result.flags if f.mod_relevant and f.exemption)
    vanilla = sum(1 for f in result.flags if not f.mod_relevant)
    return {
        "buildings_audited": result.coverage.get("buildings_audited", 0),
        "buildings_enumerated": result.coverage.get("buildings_enumerated", 0),
        "total_flags": len(result.flags),
        "unreviewed": mod_unrev,
        "exempted": mod_exemp,
        "vanilla_only": vanilla,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mod_state import ModState
    from path_constants import mod_path
    import mod_state_server
    ms = ModState(mod_state_server.base_game_paths, mod_state_server.mod_paths)
    result = audit(ms, mod_path=mod_path)
    print(render_report(result))
