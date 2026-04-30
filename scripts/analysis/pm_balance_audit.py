#!/usr/bin/env python3
"""Audit mod-side PMs for balance review using auto-generated cost comments.

Walks common/production_methods/*.txt and parses the cost-comment block that
pm_costs.py emits in front of every PM. Tabulates profit margin, wage
breakeven, profit, and groups by file + by parent building when available.

Surfaces outliers: PMs with extreme profit margin or wage breakeven values,
which are likely either economically broken or compensating for something
the auditor can't see.

Usage:
    .venv/bin/python scripts/analysis/pm_balance_audit.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PM_DIR = REPO / "common" / "production_methods"
PM_FILES = [
    "extra_pms.txt",
    "unique_pms.txt",
    "strategic_reserve_pms.txt",
    "resettlement_pms.txt",
    "fmc_construction.txt",
]


def iter_pms(path: Path):
    """Yield (pm_id, body_with_comments) for each top-level PM in a file.

    Includes the leading comment block that precedes the PM's `= {` so we
    can parse the auto-generated cost summary.
    """
    text = path.read_text(encoding="utf-8-sig")
    pos = 0
    while pos < len(text):
        # skip leading whitespace at top of search range
        m = re.search(r"^pm_[A-Za-z0-9_]+\s*=\s*\{", text[pos:], re.MULTILINE)
        if not m:
            break
        pm_start = pos + m.start()
        pm_id_match = re.match(r"(pm_[A-Za-z0-9_]+)", text[pm_start:])
        pm_id = pm_id_match.group(1) if pm_id_match else "?"
        body_start = pm_start + m.end() - m.start()
        # walk to matching close brace
        depth = 1
        i = body_start
        while i < len(text) and depth > 0:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            i += 1
        body = text[body_start:i - 1]
        yield pm_id, body
        pos = i


def parse_cost_comments(body: str) -> dict | None:
    """Extract auto-generated cost summary from PM body comments.

    Returns dict with keys: total_input, total_output, profit, profit_margin,
    wage_breakeven. None if comments not found.
    """
    out = {}
    for line in body.split("\n"):
        line = line.strip()
        m = re.match(r"#\s*Total input cost:\s*([-\d.]+)", line)
        if m:
            out["total_input"] = float(m.group(1))
            continue
        m = re.match(r"#\s*Total output cost:\s*([-\d.]+)", line)
        if m:
            out["total_output"] = float(m.group(1))
            continue
        m = re.match(r"#\s*Profit:\s*([-\d.]+)", line)
        if m:
            out["profit"] = float(m.group(1))
            continue
        m = re.match(r"#\s*Profit margin:\s*([-\d.]+)%", line)
        if m:
            out["profit_margin_pct"] = float(m.group(1))
            continue
        m = re.match(r"#\s*Wage breakeven:\s*([-\d.]+)", line)
        if m:
            out["wage_breakeven"] = float(m.group(1))
            continue
    return out if "profit_margin_pct" in out else None


def main() -> int:
    rows = []
    for fname in PM_FILES:
        path = PM_DIR / fname
        if not path.exists():
            continue
        for pm_id, body in iter_pms(path):
            costs = parse_cost_comments(body)
            if costs is None:
                # PM has no cost comment (probably a no-input/output service PM)
                rows.append({
                    "id": pm_id,
                    "file": fname,
                    "profit": None,
                    "margin_pct": None,
                    "wage_be": None,
                    "flag": "NO-COSTS",
                })
                continue
            margin = costs["profit_margin_pct"]
            wage_be = costs.get("wage_breakeven")
            # Flag heuristics: extreme margin or wage_breakeven
            flag = "OK"
            if margin > 100:
                flag = "HIGH-PROFIT"
            elif margin < -50:
                flag = "DEEP-LOSS"
            elif wage_be is not None and wage_be > 0.30:
                flag = "HIGH-WAGE"
            elif wage_be is not None and wage_be < 0.01 and margin > 0:
                flag = "LOW-WAGE"
            rows.append({
                "id": pm_id,
                "file": fname,
                "profit": costs.get("profit"),
                "margin_pct": margin,
                "wage_be": wage_be,
                "flag": flag,
            })

    print(f"# PM balance audit — {len(rows)} PMs across {len(PM_FILES)} files\n")

    by_file = {}
    for r in rows:
        by_file.setdefault(r["file"], []).append(r)
    for fname, frows in by_file.items():
        margins = [r["margin_pct"] for r in frows if r["margin_pct"] is not None]
        if not margins:
            print(f"## {fname} — {len(frows)} PMs (no cost comments)")
            continue
        margins_sorted = sorted(margins)
        print(f"## {fname} — {len(frows)} PMs")
        print(f"  margin range: {min(margins):.1f}% – {max(margins):.1f}%, "
              f"median {margins_sorted[len(margins_sorted)//2]:.1f}%")
        flag_counts = {}
        for r in frows:
            flag_counts[r["flag"]] = flag_counts.get(r["flag"], 0) + 1
        print(f"  flags: {flag_counts}")
        print()

    # Outlier table: sorted by file then by margin (extremes first)
    print("\n## Outlier table — flagged subset\n")
    print("| pm_id | file | profit | margin% | wage_be | flag |")
    print("|---|---|---|---|---|---|")

    flagged = [r for r in rows if r["flag"] not in ("OK", "NO-COSTS")]
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
