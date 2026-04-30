#!/usr/bin/env python3
"""One-off audit of mod-side technologies for balance review.

Walks common/technology/technologies/era_6.txt through era_9.txt and emits a
table per tech: id, era, category, modifier_count, sum_abs_modifier_value.

Modifier values are summed in absolute terms — a tech with one +0.5 modifier
scores 0.5; a tech with five +0.10 modifiers scores 0.5. Different magnitudes
of different modifier types aren't comparable apples-to-apples (a +0.10
country_mult is much bigger than a +0.10 state_mult), but the ranking
surfaces obvious outliers.

Usage:
    .venv/bin/python scripts/analysis/tech_balance_audit.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterator

REPO = Path(__file__).resolve().parents[2]
TECH_DIR = REPO / "common" / "technology" / "technologies"
ERAS = ["era_6.txt", "era_7.txt", "era_8.txt", "era_9.txt"]


def iter_techs(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (tech_id, body_text) for each top-level tech in a file.

    Tracks brace depth and splits at depth 0 → 1 transitions whose key
    matches a tech-id-shaped identifier.
    """
    text = path.read_text(encoding="utf-8-sig")
    # Strip line comments
    text = re.sub(r"#[^\n]*", "", text)

    pos = 0
    while pos < len(text):
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", text[pos:])
        if not m:
            # advance past whitespace / leftover
            pos += 1
            continue
        tech_id = m.group(1)
        body_start = pos + m.end()
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
        yield tech_id, body
        pos = i


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


def main() -> int:
    rows = []
    for era_file in ERAS:
        path = TECH_DIR / era_file
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            continue
        era_label = era_file.replace(".txt", "")
        for tech_id, body in iter_techs(path):
            cat = extract_field(body, "category") or "?"
            mod_block = extract_modifier_block(body)
            mods = parse_modifiers(mod_block)
            sum_abs = sum(abs(v) for _, v in mods)
            rows.append({
                "id": tech_id,
                "era": era_label,
                "category": cat,
                "modifier_count": len(mods),
                "sum_abs_modifier_value": round(sum_abs, 4),
                "modifiers": mods,
            })

    # Per-era heuristic flags
    by_era = {}
    for r in rows:
        by_era.setdefault(r["era"], []).append(r)

    for era, era_rows in by_era.items():
        # Flag based on within-era distribution
        sums = [r["sum_abs_modifier_value"] for r in era_rows]
        sums_sorted = sorted(sums)
        if not sums_sorted:
            continue
        # Top 15% = STRONG, bottom 15% = WEAK, rest = OK; zero-mods = WEAK
        n = len(sums_sorted)
        top_thresh = sums_sorted[max(0, int(n * 0.85))]
        bot_thresh = sums_sorted[max(0, int(n * 0.15))]
        for r in era_rows:
            if r["modifier_count"] == 0:
                r["flag"] = "WEAK*"
            elif r["sum_abs_modifier_value"] >= top_thresh and r["modifier_count"] >= 2:
                r["flag"] = "STRONG"
            elif r["sum_abs_modifier_value"] <= bot_thresh:
                r["flag"] = "WEAK"
            else:
                r["flag"] = "OK"

    # Print summary stats
    print("# Tech balance audit — modifier-only first pass\n")
    print("Caveat: this only sees `modifier = { }` blocks. Techs that mainly")
    print("unlock buildings / decrees / PMs / units / laws will register as")
    print("WEAK here but are not actually weak. Cross-reference with each")
    print("tech's `unlocking_*` and `era_*` content before judging.\n")
    for era, era_rows in sorted(by_era.items()):
        sums = [r["sum_abs_modifier_value"] for r in era_rows]
        if not sums:
            continue
        print(f"## {era} — {len(era_rows)} techs")
        print(f"  modifier-sum range: {min(sums):.2f} – {max(sums):.2f}, median {sorted(sums)[len(sums)//2]:.2f}")
        cats = {}
        for r in era_rows:
            cats.setdefault(r["category"], 0)
            cats[r["category"]] += 1
        cats_str = ", ".join(f"{c}={n}" for c, n in sorted(cats.items()))
        print(f"  by category: {cats_str}")
        flagged = sorted([r for r in era_rows if r["flag"] in ("STRONG", "WEAK*")],
                         key=lambda r: -r["sum_abs_modifier_value"])
        print(f"  flagged (STRONG or no-modifier): {len(flagged)}")
        print()

    # Full table sorted by era + flag + sum-abs desc
    print("\n## Outlier table (all techs, flagged subset)\n")
    print("| id | era | cat | n_mod | sum_abs | flag |")
    print("|---|---|---|---|---|---|")
    rows_sorted = sorted(rows, key=lambda r: (r["era"], r["flag"], -r["sum_abs_modifier_value"]))
    for r in rows_sorted:
        if r["flag"] in ("STRONG", "WEAK*"):
            print(f"| `{r['id']}` | {r['era']} | {r['category']} | {r['modifier_count']} | "
                  f"{r['sum_abs_modifier_value']:.2f} | {r['flag']} |")

    return 0


if __name__ == "__main__":
    sys.exit(main())
