#!/usr/bin/env python3
"""Tech balance audit: modifier density + unlock annotations.

Walks `common/technology/technologies/era_6.txt` … `era_9.txt` and emits a
table per tech with: id, era, category, modifier_count, sum_abs_modifier_value,
flag, plus an unlock summary (counts per entity type, with PM `balance`
annotator output where applicable).

Modifier values are summed in absolute terms — a tech with one +0.5 modifier
scores 0.5; a tech with five +0.10 modifiers scores 0.5. Different magnitudes
of different modifier types aren't comparable apples-to-apples (a +0.10
country_mult is much bigger than a +0.10 state_mult), but the ranking
surfaces obvious outliers.

Unlock annotation comes from the shared `tech_unlocks_lib` (also used by
the mod state server) and the annotator registry. PM unlocks pick up their
balance flag (`HIGH-PROFIT` / `THROUGHPUT` / etc.) from `pm_balance_lib`.

Usage:
    .venv/bin/python scripts/analysis/tech_balance_audit.py
    .venv/bin/python scripts/analysis/tech_balance_audit.py --include-vanilla
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import annotators                # noqa: E402
import pm_balance_lib            # noqa: E402, F401  (registers `balance` annotator)
import tech_unlocks_lib          # noqa: E402

TECH_DIR = REPO / "common" / "technology" / "technologies"
ERAS = ["era_6.txt", "era_7.txt", "era_8.txt", "era_9.txt"]

VANILLA_COMMON_DIR = Path(
    "/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3"
    "/game/common"
)
VANILLA_TECH_DIR = VANILLA_COMMON_DIR / "technology" / "technologies"
VANILLA_FILES = ["10_production.txt", "20_military.txt", "30_society.txt"]


# ---------------------------------------------------------------------------
# Tech body parsers (reuse tech_unlocks_lib for the brace walker)
# ---------------------------------------------------------------------------

def iter_techs(path: Path):
    """Yield (tech_id, body_text) for each top-level tech in a file.

    Strips line comments before walking (matches pre-refactor behavior so
    `era = era_X` lines aren't accidentally seen inside a comment).
    """
    text = path.read_text(encoding="utf-8-sig")
    text = re.sub(r"#[^\n]*", "", text)
    yield from tech_unlocks_lib.iter_top_level_blocks(text)


def extract_modifier_block(body: str) -> str:
    """Return the contents of the top-level `modifier = { ... }` block, or ''."""
    m = re.search(r"\bmodifier\s*=\s*\{", body)
    if not m:
        return ""
    start = m.end()
    depth = 1
    i = start
    while i < len(body) and depth > 0:
        c = body[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return body[start:i - 1]


def parse_modifiers(mod_block: str) -> list[tuple[str, float]]:
    """Extract (name, value) pairs from a modifier block."""
    out = []
    for m in re.finditer(r"([a-z_][a-z0-9_]*)\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)", mod_block):
        out.append((m.group(1), float(m.group(2))))
    return out


def extract_field(body: str, field: str) -> str | None:
    """Get the simple value of a top-level `field = value` (no braces)."""
    m = re.search(rf"\b{re.escape(field)}\s*=\s*([A-Za-z_][A-Za-z0-9_]*)", body)
    return m.group(1) if m else None


def collect_techs_from_file(path: Path, era_override: str | None,
                            source: str, rows: list) -> None:
    """Parse `path` and append a row per tech."""
    for tech_id, body in iter_techs(path):
        cat = extract_field(body, "category") or "?"
        era = era_override or extract_field(body, "era") or "?"
        mod_block = extract_modifier_block(body)
        mods = parse_modifiers(mod_block)
        sum_abs = sum(abs(v) for _, v in mods)
        rows.append({
            "id": tech_id,
            "era": era,
            "category": cat,
            "source": source,
            "modifier_count": len(mods),
            "sum_abs_modifier_value": round(sum_abs, 4),
            "modifiers": mods,
        })


# ---------------------------------------------------------------------------
# Unlock annotation
# ---------------------------------------------------------------------------

def attach_unlocks(rows: list[dict], include_vanilla: bool) -> None:
    """Walk every UNLOCK_SOURCES dir, build the inverted index, annotate PM
    unlocks via the registry, and merge per-tech summary onto each row."""
    vanilla_root = VANILLA_COMMON_DIR if include_vanilla else None
    index = tech_unlocks_lib.build_tech_unlock_index(
        REPO,
        include_vanilla=include_vanilla,
        vanilla_common_root=vanilla_root,
    )

    # Apply annotators in place. Walks every entry list under by_type and
    # annotates anything with a registered annotator (today: PMs/balance).
    annotator_cache: dict = {}
    for rec in index.values():
        for etype, entries in rec["by_type"].items():
            annotators.annotate_entries(
                etype, entries, "all", REPO, cache=annotator_cache,
            )

    for r in rows:
        rec = index.get(r["id"])
        if rec is None:
            r["unlocks"] = []
            r["unlocks_summary"] = {}
            r["n_unlocks"] = 0
            r["unlock_pm_flags"] = {}
            continue
        # Flatten unlocks for printing; keep the by_type breakdown for the
        # detail table.
        r["unlocks_by_type"] = rec["by_type"]
        r["unlocks_summary"] = dict(rec["summary"])
        r["n_unlocks"] = rec["n_total"]
        # Roll up PM flag counts when present.
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
    """Compact entity-type label for the unlocks column."""
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
    """Render `4 PMs (3 OK, 1 HIGH-PROFIT) · 1 building · 1 decree`."""
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
        help="Also pull vanilla era_1–5 techs as a baseline.",
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

    # ---- flag heuristics -------------------------------------------------
    by_era: dict[str, list[dict]] = {}
    for r in rows:
        by_era.setdefault(r["era"], []).append(r)

    for era_rows in by_era.values():
        sums = [r["sum_abs_modifier_value"] for r in era_rows]
        sums_sorted = sorted(sums)
        if not sums_sorted:
            continue
        n = len(sums_sorted)
        top_thresh = sums_sorted[max(0, int(n * 0.85))]
        bot_thresh = sums_sorted[max(0, int(n * 0.15))]
        for r in era_rows:
            if r["modifier_count"] == 0 and r["n_unlocks"] > 0:
                r["flag"] = "UNLOCK-ONLY"
            elif r["modifier_count"] == 0:
                r["flag"] = "WEAK*"
            elif r["sum_abs_modifier_value"] >= top_thresh and r["modifier_count"] >= 2:
                r["flag"] = "STRONG"
            elif r["sum_abs_modifier_value"] <= bot_thresh:
                r["flag"] = "WEAK"
            else:
                r["flag"] = "OK"

    # ---- print summary ---------------------------------------------------
    print("# Tech balance audit — modifier density + unlock annotation\n")
    print("Caveat: the `sum_abs` metric only sees `modifier = { }` blocks.")
    print("Techs that mainly unlock entities are now flagged UNLOCK-ONLY (zero")
    print("modifier sum, non-zero unlocks) instead of WEAK*. The `unlocks`")
    print("column shows what each tech actually gates, with PM balance flags")
    print("rolled up via the annotator registry.\n")

    for era in sorted(by_era.keys(), key=_era_sort_key):
        era_rows = by_era[era]
        sums = [r["sum_abs_modifier_value"] for r in era_rows]
        if not sums:
            continue
        sources = sorted({r.get("source", "mod") for r in era_rows})
        src_label = f" [{','.join(sources)}]" if sources != ["mod"] else ""
        unlocks_total = sum(r["n_unlocks"] for r in era_rows)
        top_unlocker = max(era_rows, key=lambda r: r["n_unlocks"])
        print(f"## {era}{src_label} — {len(era_rows)} techs")
        print(f"  modifier-sum range: {min(sums):.2f} – {max(sums):.2f}, "
              f"median {sorted(sums)[len(sums)//2]:.2f}")
        cats: dict[str, int] = {}
        for r in era_rows:
            cats[r["category"]] = cats.get(r["category"], 0) + 1
        cats_str = ", ".join(f"{c}={n}" for c, n in sorted(cats.items()))
        print(f"  by category: {cats_str}")
        flag_counts: Counter = Counter(r["flag"] for r in era_rows)
        flag_str = ", ".join(
            f"{flag}={n}" for flag, n in sorted(flag_counts.items())
        )
        print(f"  flags: {flag_str}")
        if unlocks_total:
            print(f"  unlocks: {unlocks_total} total · top: "
                  f"{top_unlocker['id']} ({top_unlocker['n_unlocks']})")
        print()

    # ---- outlier table ---------------------------------------------------
    print("\n## Outlier table (STRONG / WEAK* / UNLOCK-ONLY)\n")
    print("| id | era | cat | n_mod | sum_abs | flag | unlocks |")
    print("|---|---|---|---|---|---|---|")
    rows_sorted = sorted(
        rows,
        key=lambda r: (_era_sort_key(r["era"]), r["flag"],
                       -r["sum_abs_modifier_value"]),
    )
    for r in rows_sorted:
        if r["flag"] in ("STRONG", "WEAK*", "UNLOCK-ONLY"):
            print(
                f"| `{r['id']}` | {r['era']} | {r['category']} | "
                f"{r['modifier_count']} | {r['sum_abs_modifier_value']:.2f} | "
                f"{r['flag']} | {format_unlocks_summary(r)} |"
            )

    # ---- unlock-only detail ---------------------------------------------
    unlock_only = [r for r in rows_sorted if r["flag"] == "UNLOCK-ONLY"]
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
