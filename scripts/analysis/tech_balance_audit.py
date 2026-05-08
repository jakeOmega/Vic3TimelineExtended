#!/usr/bin/env python3
"""Tech balance audit: vanilla-normalized modifier density + structure checks.

Walks `common/technology/technologies/era_6.txt` … `era_12.txt` and emits a
table per tech with: id, era, category, modifier_count, sum_abs, scaled_sum,
polarity counts, flag, plus an unlock summary (counts per entity type, with
PM `balance` annotator output where applicable).

The headline metric is `scaled_sum` — Σ |value| / vanilla_median(name) —
which expresses each tech as a multiple of "one vanilla tech's worth of
modifier value". A vanilla median of 0.25 (the overall vanilla anchor)
means a `+0.25 country_innovation_mult` scores 1.0, while a `+10
country_diplomatic_play_maneuvers_add` is normalized against vanilla
adds of similar magnitude rather than naively summed. Mod-only modifiers
fall through to user-supplied targets in `docs/audits/mod_only_tech_modifier_baseline.md`
or, absent those, the current-mod median (marked imputed in output).

The old `sum_abs` metric stays in each row for diff-checking against the
pre-normalization audit, but no longer drives the STRONG / WEAK flags.

Usage:
    .venv/bin/python scripts/analysis/tech_balance_audit.py
    .venv/bin/python scripts/analysis/tech_balance_audit.py --include-vanilla
    .venv/bin/python scripts/analysis/tech_balance_audit.py --refresh-baseline
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import annotators                # noqa: E402
import pm_balance_lib            # noqa: E402, F401  (registers `balance` annotator)
import tech_unlocks_lib          # noqa: E402
from path_constants import base_game_path  # noqa: E402

from tech_modifier_baseline import (  # noqa: E402
    classify_pattern,
    extract_field,
    extract_modifier_block,
    get_or_build_baseline,
    get_or_build_pattern_baseline,
    iter_techs,
    parse_modifiers,
)

TECH_DIR = REPO / "common" / "technology" / "technologies"
ERAS = [
    "era_6.txt",
    "era_7.txt",
    "era_8.txt",
    "era_9.txt",
    "era_10.txt",
    "era_11.txt",
    "era_12.txt",
]

VANILLA_COMMON_DIR = Path(base_game_path) / "game" / "common"
VANILLA_TECH_DIR = VANILLA_COMMON_DIR / "technology" / "technologies"
VANILLA_FILES = ["10_production.txt", "20_military.txt", "30_society.txt"]

MOD_ONLY_DOC = REPO / "docs" / "audits" / "mod_only_tech_modifier_baseline.md"


# ---------------------------------------------------------------------------
# Tech collection
# ---------------------------------------------------------------------------

def collect_techs_from_file(path: Path, era_override: str | None,
                            source: str, rows: list) -> None:
    """Parse `path` and append a row per tech."""
    for tech_id, body in iter_techs(path):
        cat = extract_field(body, "category") or "?"
        era = era_override or extract_field(body, "era") or "?"
        mod_block = extract_modifier_block(body)
        mods = parse_modifiers(mod_block)
        sum_abs = sum(abs(v) for _, v in mods)
        prereqs = tech_unlocks_lib.parse_unlocking_techs(body)
        rows.append({
            "id": tech_id,
            "era": era,
            "category": cat,
            "source": source,
            "modifier_count": len(mods),
            "sum_abs_modifier_value": round(sum_abs, 4),
            "modifiers": mods,
            "prereqs": prereqs,
        })


# ---------------------------------------------------------------------------
# Baseline normalization (scaled_sum + polarity)
# ---------------------------------------------------------------------------

def _build_mod_modifier_index(rows: list[dict]) -> dict[str, list[float]]:
    """{name: [values used in mod tech blocks]}."""
    out: dict[str, list[float]] = {}
    for r in rows:
        if r.get("source") != "mod":
            continue
        for name, value in r["modifiers"]:
            out.setdefault(name, []).append(value)
    return out


def _read_mod_only_targets(path: Path = MOD_ONLY_DOC) -> dict[str, float]:
    """Read user-supplied target values from the mod-only baseline markdown.

    Multi-section table support: re-parses headers each time we see a header
    row, so both the parametric and bespoke sections are picked up. Cells
    ending with `†` are pattern-derived defaults (not user targets) and are
    skipped — the audit recomputes those itself.
    """
    if not path.exists():
        return {}
    targets: dict[str, float] = {}
    headers: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip()
        if not line.startswith("|"):
            headers = None
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        # Header row
        if headers is None:
            candidate = [c.strip("`").lower() for c in cells]
            if "modifier" in candidate and "target_typical_value" in candidate:
                headers = candidate
            continue
        # Skip the divider row "| --- | --- |"
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if len(cells) < len(headers):
            continue
        row = dict(zip(headers, cells))
        name = row.get("modifier", "").strip("` ")
        target = row.get("target_typical_value", "").strip()
        if not name or not target:
            continue
        # Skip auto-suggestion markers — audit re-derives those at runtime.
        # `†` = pattern median, `‡` = mod median.
        if target.endswith("†") or target.endswith("‡"):
            continue
        try:
            targets[name] = float(target)
        except ValueError:
            continue
    return targets


def _annotate_modifiers_with_baseline(
    rows: list[dict],
    baseline: dict[str, dict],
    pattern_baseline: dict[str, dict],
    mod_index: dict[str, list[float]],
    mod_only_targets: dict[str, float],
) -> dict[str, dict]:
    """Compute scaled_sum, polarity counts, and per-modifier annotations on
    each row in place. Returns the merged baseline used (vanilla + pattern +
    user-target + imputed) so the caller can emit the mod-only registry."""
    merged: dict[str, dict] = {}

    def baseline_for(name: str) -> tuple[float, str, str]:
        """Return (anchor_value, source_tag, polarity).

        Resolution order:
          1. exact vanilla tech baseline (`docs/data/tech_modifier_baseline.json`)
          2. user-supplied target in mod_only_tech_modifier_baseline.md
          3. parametric pattern baseline (vanilla median for the `_<X>_`
             family — e.g. all vanilla `building_*_throughput_add` values)
          4. imputed (median of the mod's own usage of this name)
        """
        if name in baseline:
            info = baseline[name]
            anchor = info["vanilla_median"] or 0.0
            return (anchor, "vanilla", info.get("polarity", "positive-good"))
        if name in mod_only_targets:
            anchor = mod_only_targets[name]
            return (anchor, "user-target", _classify_mod_only_polarity(name))
        pattern = classify_pattern(name)
        if pattern is not None:
            info = pattern_baseline.get(pattern)
            if info and info.get("vanilla_median"):
                return (
                    info["vanilla_median"],
                    f"pattern:{pattern}",
                    _classify_mod_only_polarity(name),
                )
        # Imputed: median of the mod's own usage
        vals = mod_index.get(name, [])
        if vals:
            anchor = statistics.median([abs(v) for v in vals])
        else:
            anchor = 0.0
        return (anchor, "imputed", _classify_mod_only_polarity(name))

    for r in rows:
        scaled = 0.0
        n_pos = n_neg = n_unk = 0
        any_imputed = False
        for name, value in r["modifiers"]:
            anchor, src, pol = baseline_for(name)
            # Count effective effect = polarity × sign(value), not raw
            # polarity. So `state_radicals_mult = -0.05` on a negative-good
            # modifier scores as a GOOD effect (player is reducing radicals);
            # `state_radicals_mult = +0.05` scores as a BAD effect.
            if pol == "unknown" or value == 0:
                n_unk += 1
            elif (pol == "positive-good" and value > 0) or \
                 (pol == "negative-good" and value < 0):
                n_pos += 1
            else:
                n_neg += 1
            if anchor > 0:
                scaled += abs(value) / anchor
            else:
                # No anchor at all → fall back to absolute for visibility,
                # but mark imputed.
                scaled += abs(value)
                any_imputed = True
            if src == "imputed":
                any_imputed = True
            # Treat pattern-derived anchors as solid (not imputed) — they're
            # backed by 100s of vanilla instances.
            merged.setdefault(name, {
                "polarity": pol,
                "anchor": anchor,
                "anchor_source": src,
            })
        r["scaled_sum"] = round(scaled, 4)
        r["n_pos_mods"] = n_pos
        r["n_neg_mods"] = n_neg
        r["n_unknown_mods"] = n_unk
        r["scaled_imputed"] = any_imputed
    return merged


def _classify_mod_only_polarity(name: str) -> str:
    """Reuse the heuristic from baseline lib for mod-only names."""
    from tech_modifier_baseline import classify_polarity, load_polarity_overrides
    overrides = load_polarity_overrides()
    if name in overrides:
        return overrides[name]
    return classify_polarity(name)


# ---------------------------------------------------------------------------
# Mod-only modifier registry (template emission)
# ---------------------------------------------------------------------------

def emit_mod_only_baseline_doc(
    mod_index: dict[str, list[float]],
    baseline: dict[str, dict],
    pattern_baseline: dict[str, dict],
    existing_targets: dict[str, float],
    path: Path = MOD_ONLY_DOC,
) -> int:
    """Write `docs/audits/mod_only_tech_modifier_baseline.md` listing every modifier
    used in mod tech blocks but NOT in vanilla, with a `target_typical_value`
    column the user fills in. Preserves any already-filled target values.
    For modifiers matching a known parametric pattern (e.g.
    `building_<X>_throughput_add`), surfaces the vanilla-pattern median as
    a suggested target so the user can accept or override.
    Returns count of mod-only modifier names written."""
    from tech_modifier_baseline import (
        classify_polarity,
        classify_pattern,
        load_polarity_overrides,
    )
    overrides = load_polarity_overrides()
    mod_only = {n: v for n, v in mod_index.items() if n not in baseline}

    # Group rows: those auto-resolved by a parametric pattern come first
    # (with the suggested anchor pre-filled in target_typical_value), then
    # fully mod-only names that need user attention.
    pattern_rows: list[tuple] = []
    bespoke_rows: list[tuple] = []
    for name, vals in sorted(mod_only.items()):
        abs_vals = [abs(v) for v in vals]
        mod_median = statistics.median(abs_vals)
        polarity = overrides.get(name, classify_polarity(name))
        existing = existing_targets.get(name)
        pattern = classify_pattern(name)
        suggested_pattern = None
        if pattern is not None:
            info = pattern_baseline.get(pattern)
            if info and info.get("vanilla_median"):
                suggested_pattern = info["vanilla_median"]
        # Cell shows:
        #   - user value if filled (numeric, picked up by the parser)
        #   - else `<pattern_median>†` if the modifier matches a pattern
        #   - else `<mod_median>‡` so bespoke modifiers default to the
        #     mod's own median (the imputed fallback) but the suggestion
        #     is visible in the doc and easy to override.
        if existing is not None:
            target_cell = f"{existing:g}"
        elif suggested_pattern is not None:
            target_cell = f"{suggested_pattern:g}†"
        else:
            target_cell = f"{mod_median:g}‡"
        row = (name, len(vals), min(vals), mod_median,
               max(vals), polarity, target_cell, pattern or "")
        if pattern is not None:
            pattern_rows.append(row)
        else:
            bespoke_rows.append(row)

    lines = [
        "# Mod-only tech modifiers — baseline targets",
        "",
        "Auto-generated by `scripts/analysis/tech_balance_audit.py`. Each row",
        "lists a modifier name that appears in mod tech `modifier = { }`",
        "blocks but not in any vanilla tech (era_1–5).",
        "",
        "**Two sections:**",
        "1. *Parametric pattern matches* — the modifier name fits a known",
        "   vanilla pattern (e.g. `building_<X>_throughput_add`); the",
        "   suggested target is the vanilla-wide median across all",
        "   matching instances. The `†` mark signals a pattern-derived",
        "   default. Override pattern medians in",
        "   `docs/data/tech_modifier_pattern_overrides.yml`, or set a per-modifier",
        "   target by replacing the `<value>†` cell with a plain number.",
        "2. *Bespoke mod modifiers* — no pattern match. Default suggestion",
        "   is the mod's own median for the modifier (`<value>‡`). Replace",
        "   with a designed target if you want a sharper anchor; vanilla's",
        "   overall tech-modifier median is ~0.25 for `_mult` and ~1.0 for",
        "   discrete `_add` slots, but your subsystem may use a different",
        "   scale.",
        "",
        "The audit reads `target_typical_value` on subsequent runs and uses",
        "it as the normalization anchor.",
        "",
        "Polarity is heuristically classified; override in",
        "`docs/data/tech_modifier_polarity.yml` if wrong.",
        "",
        "## Parametric pattern matches",
        "",
        "| modifier | pattern | mod_uses | min | median | max | polarity | target_typical_value |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, count, mn, med, mx, polarity, target, pattern in pattern_rows:
        lines.append(
            f"| `{name}` | `{pattern}` | {count} | {mn:g} | {med:g} | "
            f"{mx:g} | {polarity} | {target} |"
        )
    lines.extend([
        "",
        "## Bespoke mod modifiers (no pattern match)",
        "",
        "| modifier | mod_uses | min | median | max | polarity | target_typical_value |",
        "|---|---|---|---|---|---|---|",
    ])
    for name, count, mn, med, mx, polarity, target, _pattern in bespoke_rows:
        lines.append(
            f"| `{name}` | {count} | {mn:g} | {med:g} | {mx:g} | "
            f"{polarity} | {target} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return len(pattern_rows) + len(bespoke_rows)


# ---------------------------------------------------------------------------
# Inverse prereq graph + structural flags
# ---------------------------------------------------------------------------

def build_prereq_structure(rows: list[dict]) -> dict:
    """Build category/era/source maps, the inverse prereq graph, and detect
    cross-category and era-skip prereqs. Returns:

    {
        'cat': {tech_id: category},
        'era': {tech_id: era},
        'descendants': {tech_id: set(child_ids)},
        'leaves': set(tech_id),  # zero descendants
        'xcat': {tech_id: [bad_prereq, ...]},
        'eraskip': {tech_id: [(prereq, era_gap), ...]},
    }
    """
    cat = {r["id"]: r["category"] for r in rows}
    era = {r["id"]: r["era"] for r in rows}

    descendants: dict[str, set[str]] = defaultdict(set)
    xcat: dict[str, list[str]] = {}
    eraskip: dict[str, list[tuple[str, int]]] = {}

    def era_num(label: str) -> int | None:
        m = re.match(r"era_(\d+)", label or "")
        return int(m.group(1)) if m else None

    for r in rows:
        child = r["id"]
        child_cat = cat.get(child, "?")
        child_era = era_num(era.get(child))
        for p in r["prereqs"]:
            descendants[p].add(child)
            p_cat = cat.get(p)
            p_era = era_num(era.get(p))
            if p_cat is not None and child_cat != "?" and p_cat != child_cat:
                xcat.setdefault(child, []).append(p)
            if (
                p_era is not None
                and child_era is not None
                and child_era - p_era >= 2
                # only flag mod-side era-skips (vanilla→mod boundary tolerated)
                and p_era >= 5
            ):
                eraskip.setdefault(child, []).append((p, child_era - p_era))

    leaves = {
        r["id"] for r in rows
        if r.get("source") == "mod"
        and not descendants.get(r["id"])
    }

    return {
        "cat": cat,
        "era": era,
        "descendants": dict(descendants),
        "leaves": leaves,
        "xcat": xcat,
        "eraskip": eraskip,
    }


# ---------------------------------------------------------------------------
# Unlock annotation
# ---------------------------------------------------------------------------

def attach_unlocks(rows: list[dict], include_vanilla: bool) -> None:
    vanilla_root = VANILLA_COMMON_DIR if include_vanilla else None
    index = tech_unlocks_lib.build_tech_unlock_index(
        REPO,
        include_vanilla=include_vanilla,
        vanilla_common_root=vanilla_root,
    )
    annotator_cache: dict = {}
    for rec in index.values():
        for etype, entries in rec["by_type"].items():
            annotators.annotate_entries(
                etype, entries, "all", REPO, cache=annotator_cache,
            )
    for r in rows:
        rec = index.get(r["id"])
        if rec is None:
            r["unlocks_by_type"] = {}
            r["unlocks_summary"] = {}
            r["n_unlocks"] = 0
            r["unlock_pm_flags"] = {}
            continue
        r["unlocks_by_type"] = rec["by_type"]
        r["unlocks_summary"] = dict(rec["summary"])
        r["n_unlocks"] = rec["n_total"]
        pm_entries = rec["by_type"].get("PMs", [])
        flag_counts = Counter(
            e.get("flag") for e in pm_entries if e.get("flag") is not None
        )
        r["unlock_pm_flags"] = dict(flag_counts)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _era_sort_key(e: str) -> tuple[int, str]:
    m = re.match(r"era_(\d+)", e)
    return (int(m.group(1)) if m else 9999, e)


def _short_etype(etype: str) -> str:
    return {
        "Buildings": "building",
        "Combat Unit Types": "combat unit",
        "Decrees": "decree",
        "Laws": "law",
        "Mobilization Options": "mob option",
        "Parties": "party",
        "PMs": "PM",
        "Ship Modifications": "ship mod",
        "Ship Types": "ship type",
    }.get(etype, etype.lower())


def format_unlocks_summary(row: dict) -> str:
    if not row.get("unlocks_summary"):
        return "—"
    parts = []
    for etype, count in sorted(row["unlocks_summary"].items()):
        label = _short_etype(etype) + ("s" if count > 1 else "")
        suffix = ""
        if etype == "PMs" and row.get("unlock_pm_flags"):
            flags = ", ".join(
                f"{n} {flag}"
                for flag, n in sorted(row["unlock_pm_flags"].items(),
                                      key=lambda kv: -kv[1])
            )
            if flags:
                suffix = f" ({flags})"
        parts.append(f"{count} {label}{suffix}")
    return " · ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-vanilla",
        action="store_true",
        help="Also pull vanilla era_1–5 techs into the audit table.",
    )
    parser.add_argument(
        "--refresh-baseline",
        action="store_true",
        help="Rebuild docs/data/tech_modifier_baseline.json from vanilla files.",
    )
    args = parser.parse_args()

    # ---- collect ---------------------------------------------------------
    rows: list[dict] = []
    for era_file in ERAS:
        path = TECH_DIR / era_file
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            continue
        era_label = era_file.replace(".txt", "")
        collect_techs_from_file(path, era_label, "mod", rows)

    if args.include_vanilla:
        if not VANILLA_TECH_DIR.exists():
            print(f"--include-vanilla requested but vanilla dir not found: "
                  f"{VANILLA_TECH_DIR}", file=sys.stderr)
        else:
            for fname in VANILLA_FILES:
                vpath = VANILLA_TECH_DIR / fname
                if not vpath.exists():
                    continue
                collect_techs_from_file(vpath, None, "vanilla", rows)

    attach_unlocks(rows, args.include_vanilla)

    # ---- baseline normalization -----------------------------------------
    baseline = get_or_build_baseline(refresh=args.refresh_baseline)
    pattern_baseline = get_or_build_pattern_baseline(
        refresh=args.refresh_baseline
    )
    mod_index = _build_mod_modifier_index(rows)
    mod_only_targets = _read_mod_only_targets()
    _annotate_modifiers_with_baseline(
        rows, baseline, pattern_baseline, mod_index, mod_only_targets
    )
    n_mod_only = emit_mod_only_baseline_doc(
        mod_index, baseline, pattern_baseline, mod_only_targets
    )

    # ---- structural checks (LEAF / XCAT / ERA-SKIP) ---------------------
    struct = build_prereq_structure(rows)

    # ---- flag heuristics (now driven by scaled_sum) ----------------------
    by_era: dict[str, list[dict]] = {}
    for r in rows:
        by_era.setdefault(r["era"], []).append(r)

    for era_rows in by_era.values():
        sums = [r["scaled_sum"] for r in era_rows]
        sums_sorted = sorted(sums)
        if not sums_sorted:
            continue
        n = len(sums_sorted)
        top_thresh = sums_sorted[max(0, int(n * 0.85))]
        bot_thresh = sums_sorted[max(0, int(n * 0.15))]
        for r in era_rows:
            flags = []
            if r["modifier_count"] == 0 and r["n_unlocks"] > 0:
                flags.append("UNLOCK-ONLY")
            elif r["modifier_count"] == 0:
                flags.append("WEAK*")
            elif r["scaled_sum"] >= top_thresh and r["modifier_count"] >= 2:
                flags.append("STRONG")
            elif r["scaled_sum"] <= bot_thresh:
                flags.append("WEAK")
            else:
                flags.append("OK")
            if r["n_pos_mods"] >= 1 and r["n_neg_mods"] >= 1:
                flags.append("MIXED")
            if r["id"] in struct["leaves"]:
                flags.append("LEAF")
            if r["id"] in struct["xcat"]:
                flags.append("XCAT-PREREQ")
            if r["id"] in struct["eraskip"]:
                flags.append("ERA-SKIP-PREREQ")
            r["flags"] = flags
            r["flag"] = flags[0]  # primary flag for back-compat

    # ---- print summary ---------------------------------------------------
    print("# Tech balance audit — vanilla-normalized (scaled_sum)\n")
    print("Headline metric: `scaled_sum` = Σ |value| / vanilla_median(name)")
    print("expressing each tech as a multiple of one vanilla-tech's worth")
    print("of modifier value. Mod-only modifiers fall through to user")
    print("targets in `docs/audits/mod_only_tech_modifier_baseline.md` (or the")
    print("current-mod median, marked imputed). The legacy `sum_abs`")
    print("metric stays in each row for diff-checking but no longer drives")
    print("flags.\n")
    print(f"Mod-only modifier count: {n_mod_only} "
          f"(see {MOD_ONLY_DOC.relative_to(REPO)})\n")

    for era in sorted(by_era.keys(), key=_era_sort_key):
        era_rows = by_era[era]
        if not era_rows:
            continue
        scaled = [r["scaled_sum"] for r in era_rows]
        legacy = [r["sum_abs_modifier_value"] for r in era_rows]
        sources = sorted({r.get("source", "mod") for r in era_rows})
        src_label = f" [{','.join(sources)}]" if sources != ["mod"] else ""
        unlocks_total = sum(r["n_unlocks"] for r in era_rows)
        top_unlocker = max(era_rows, key=lambda r: r["n_unlocks"])
        print(f"## {era}{src_label} — {len(era_rows)} techs")
        print(f"  scaled_sum range: {min(scaled):.2f} – {max(scaled):.2f}, "
              f"median {sorted(scaled)[len(scaled)//2]:.2f}")
        print(f"  legacy sum_abs range: {min(legacy):.2f} – {max(legacy):.2f}, "
              f"median {sorted(legacy)[len(legacy)//2]:.2f}")
        cats: dict[str, int] = {}
        for r in era_rows:
            cats[r["category"]] = cats.get(r["category"], 0) + 1
        cats_str = ", ".join(f"{c}={n}" for c, n in sorted(cats.items()))
        print(f"  by category: {cats_str}")
        flag_counts: Counter = Counter()
        for r in era_rows:
            for f in r["flags"]:
                flag_counts[f] += 1
        flag_str = ", ".join(
            f"{flag}={n}" for flag, n in sorted(flag_counts.items())
        )
        print(f"  flags: {flag_str}")
        if unlocks_total:
            print(f"  unlocks: {unlocks_total} total · top: "
                  f"{top_unlocker['id']} ({top_unlocker['n_unlocks']})")
        print()

    # ---- outlier table ---------------------------------------------------
    print("\n## Outlier table (STRONG / WEAK* / UNLOCK-ONLY / MIXED)\n")
    print("| id | era | cat | n_mod | scaled | sum_abs | flags | unlocks |")
    print("|---|---|---|---|---|---|---|---|")
    rows_sorted = sorted(
        rows,
        key=lambda r: (_era_sort_key(r["era"]), r["flag"],
                       -r["scaled_sum"]),
    )
    for r in rows_sorted:
        if any(f in r["flags"] for f in
               ("STRONG", "WEAK*", "WEAK", "UNLOCK-ONLY", "MIXED")):
            flags = " · ".join(r["flags"])
            scaled_repr = (
                f"{r['scaled_sum']:.2f}"
                + ("?" if r.get("scaled_imputed") else "")
            )
            print(
                f"| `{r['id']}` | {r['era']} | {r['category']} | "
                f"{r['modifier_count']} | {scaled_repr} | "
                f"{r['sum_abs_modifier_value']:.2f} | "
                f"{flags} | {format_unlocks_summary(r)} |"
            )

    # ---- structural sections --------------------------------------------
    leaves_by_era: dict[str, list[str]] = {}
    for r in rows:
        if r.get("source") != "mod":
            continue
        if r["id"] in struct["leaves"]:
            leaves_by_era.setdefault(r["era"], []).append(r["id"])
    if leaves_by_era:
        print("\n## Dead-end techs (LEAF — not a prereq for any other tech)\n")
        for era in sorted(leaves_by_era, key=_era_sort_key):
            ids = leaves_by_era[era]
            print(f"### {era} ({len(ids)} leaves)")
            for tid in sorted(ids):
                rec = next((r for r in rows if r["id"] == tid), None)
                cat = rec["category"] if rec else "?"
                print(f"  - `{tid}` ({cat})")
            print()

    if struct["xcat"]:
        print("\n## Cross-category prereqs (XCAT-PREREQ)\n")
        print("Vanilla never crosses category in `unlocking_technologies`.")
        print("These techs do:\n")
        for tid, bad in sorted(struct["xcat"].items()):
            rec = next((r for r in rows if r["id"] == tid), None)
            child_cat = rec["category"] if rec else "?"
            for p in bad:
                p_rec = next((r for r in rows if r["id"] == p), None)
                p_cat = p_rec["category"] if p_rec else "?"
                p_era = p_rec["era"] if p_rec else "?"
                print(f"  - `{tid}` ({child_cat}) ← `{p}` ({p_cat}, {p_era})")
        print()

    if struct["eraskip"]:
        print("\n## Era-skip prereqs (≥2 eras earlier)\n")
        for tid, skips in sorted(struct["eraskip"].items()):
            rec = next((r for r in rows if r["id"] == tid), None)
            child_era = rec["era"] if rec else "?"
            for p, gap in skips:
                p_rec = next((r for r in rows if r["id"] == p), None)
                p_era = p_rec["era"] if p_rec else "?"
                print(f"  - `{tid}` ({child_era}) ← `{p}` ({p_era}) [gap={gap}]")
        print()

    # ---- unlock-only detail ---------------------------------------------
    unlock_only = [r for r in rows_sorted
                   if "UNLOCK-ONLY" in r.get("flags", [])]
    if unlock_only:
        print("\n## Unlock-only techs (zero modifier block; value is in unlocks)\n")
        for r in unlock_only:
            print(f"### {r['id']} — {r['era']} ({r['category']})")
            for etype, entries in sorted(r.get("unlocks_by_type", {}).items()):
                ids = []
                for e in entries:
                    if etype == "PMs" and e.get("flag"):
                        ids.append(f"{e['id']} [{e['flag']}]")
                    else:
                        ids.append(e["id"])
                print(f"  - {len(entries)} {_short_etype(etype)}"
                      f"{'s' if len(entries) > 1 else ''}: "
                      + ", ".join(ids))
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
