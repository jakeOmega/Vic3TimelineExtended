#!/usr/bin/env python3
"""Audit mod-side PMs for balance review using auto-generated cost comments.

Walks common/production_methods/*.txt and parses the cost-comment block that
pm_costs.py emits in front of every PM. Tabulates profit margin, wage
breakeven, profit, and groups by file + by parent building when available.

Surfaces outliers: PMs with extreme profit margin or wage breakeven values,
which are likely either economically broken or compensating for something
the auditor can't see.

Classification + parsing primitives now live in `pm_balance_lib.py` so the
mod state server (and the tech audit) can reuse them. The CLI behavior of
this script is unchanged.

Usage:
    .venv/bin/python scripts/analysis/pm_balance_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import pm_balance_lib as lib  # noqa: E402

PM_DIR = REPO / lib.PM_SUBDIR
PM_FILES = lib.PM_FILES


def main() -> int:
    rows = []
    for fname in PM_FILES:
        path = PM_DIR / fname
        if not path.exists():
            continue
        for pm_id, body in lib.iter_pms(path):
            costs = lib.parse_cost_comments(body)
            flag = lib.classify_pm(body, costs)
            if costs is None:
                rows.append({
                    "id": pm_id,
                    "file": fname,
                    "profit": None,
                    "margin_pct": None,
                    "wage_be": None,
                    "flag": flag,
                })
                continue
            rows.append({
                "id": pm_id,
                "file": fname,
                "profit": costs.get("profit"),
                "margin_pct": costs["profit_margin_pct"],
                "wage_be": costs.get("wage_breakeven"),
                "flag": flag,
            })

    print(f"# PM balance audit — {len(rows)} PMs across {len(PM_FILES)} files\n")

    by_file = {}
    for r in rows:
        by_file.setdefault(r["file"], []).append(r)
    for fname, frows in by_file.items():
        # Margin stats exclude throughput PMs since they are uniformly -100%
        # and would skew the median/range.
        margins = [r["margin_pct"] for r in frows
                   if r["margin_pct"] is not None and r["flag"] != "THROUGHPUT"]
        if not margins:
            print(f"## {fname} — {len(frows)} PMs (no cost comments)")
            continue
        margins_sorted = sorted(margins)
        print(f"## {fname} — {len(frows)} PMs")
        print(f"  margin range (excl. throughput): {min(margins):.1f}% – "
              f"{max(margins):.1f}%, median "
              f"{margins_sorted[len(margins_sorted)//2]:.1f}%")
        flag_counts = {}
        for r in frows:
            flag_counts[r["flag"]] = flag_counts.get(r["flag"], 0) + 1
        print(f"  flags: {flag_counts}")
        print()

    # Outlier table: sorted by file then by margin (extremes first)
    print("\n## Outlier table — flagged subset\n")
    print("| pm_id | file | profit | margin% | wage_be | flag |")
    print("|---|---|---|---|---|---|")

    flagged = [r for r in rows if r["flag"] not in ("OK", "NO-COSTS", "THROUGHPUT")]
    flagged.sort(key=lambda r: (r["file"], r["flag"], -(r["margin_pct"] or 0)))
    for r in flagged:
        m = f"{r['margin_pct']:.1f}" if r["margin_pct"] is not None else "—"
        p = f"{r['profit']:.0f}" if r["profit"] is not None else "—"
        w = f"{r['wage_be']:.3f}" if r["wage_be"] is not None else "—"
        print(f"| `{r['id']}` | {r['file']} | {p} | {m} | {w} | {r['flag']} |")

    print(f"\n({len(flagged)} flagged of {len(rows)} total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
