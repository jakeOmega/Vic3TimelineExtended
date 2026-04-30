#!/usr/bin/env python3
"""Audit mod-side combat units for balance review.

Walks common/combat_unit_types/extra_combat_units.txt, extracts each unit's
offense, defense, max_manpower, total upkeep cost (from auto-generated
comments), and unlocking tech. Computes power-to-cost ratios within era to
surface outliers.

Usage:
    .venv/bin/python scripts/analysis/combat_unit_balance_audit.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COMBAT_FILE = REPO / "common" / "combat_unit_types" / "extra_combat_units.txt"

# Tech-to-era mapping (from in-file comments + tech file headers — manually
# curated since unlocking technologies are recorded inline as comments).
TECH_ERA = {
    # era 5 (vanilla baseline)
    "mobile_armor": "era_5",
    # era 6
    "combined_arms": "era_6",
    "motorized_artillery": "era_6",
    "bombing_aircraft": "era_6",
    "advanced_machine_guns": "era_6",
    "armored_personnel_carriers": "era_6",
    # era 7
    "guided_missiles": "era_7",
    "inertial_navigation_systems": "era_7",
    "advanced_military_aircraft": "era_7",
    "advanced_submarine_technology": "era_7",
    # era 8
    "advanced_materials_armor": "era_8",
    "augmented_reality_warfare": "era_8",
    "stealth_aircraft": "era_8",
    # era 9
    "network_centric_warfare": "era_9",
    "rapid_deployment_forces": "era_9",
    # era 10
    "jadc2": "era_10",
    "swarm_technology": "era_10",
    "space_militarization": "era_10",
    "hypersonic_weapons": "era_10",
    "directed_energy_weapons": "era_10",
    "augmented_reality_warfare": "era_10",
    # era 11
    "molecular_assemblers": "era_11",
    "compact_fusion_reactors": "era_11",
    "antimatter_production": "era_11",
    "bioenhanced_soldiers": "era_11",
}


def iter_units(path: Path):
    """Yield (unit_id, body) for each combat_unit_type_X = { ... }."""
    text = path.read_text(encoding="utf-8-sig")
    pos = 0
    while pos < len(text):
        m = re.search(r"^(combat_unit_type_[A-Za-z0-9_]+)\s*=\s*\{", text[pos:],
                      re.MULTILINE)
        if not m:
            break
        unit_id = m.group(1)
        body_start = pos + m.end()
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
        yield unit_id, body
        pos = i


def parse_battle_modifier(body: str) -> dict:
    """Get unit_offense_add, unit_defense_add etc. from battle_modifier block."""
    m = re.search(r"battle_modifier\s*=\s*\{([^}]*)\}", body, re.DOTALL)
    if not m:
        return {}
    block = m.group(1)
    out = {}
    for kv in re.finditer(r"([a-z_][a-z0-9_]*)\s*=\s*(-?[0-9.]+)", block):
        out[kv.group(1)] = float(kv.group(2))
    return out


def parse_upkeep_cost(body: str) -> float | None:
    """Extract total upkeep cost from auto-generated comment '# Total cost: X'."""
    m = re.search(r"#\s*Total cost:\s*([-\d.]+)", body)
    return float(m.group(1)) if m else None


def parse_max_manpower(body: str) -> int | None:
    m = re.search(r"max_manpower\s*=\s*(\d+)", body)
    return int(m.group(1)) if m else None


def parse_unlocking_tech(body: str) -> str | None:
    m = re.search(r"unlocking_technologies\s*=\s*\{\s*([A-Za-z_][A-Za-z0-9_]*)",
                  body)
    return m.group(1) if m else None


def parse_group(body: str) -> str | None:
    m = re.search(r"group\s*=\s*([A-Za-z_][A-Za-z0-9_]*)", body)
    return m.group(1) if m else None


def main() -> int:
    rows = []
    for uid, body in iter_units(COMBAT_FILE):
        battle = parse_battle_modifier(body)
        upkeep_total = parse_upkeep_cost(body)
        manpower = parse_max_manpower(body)
        tech = parse_unlocking_tech(body)
        era = TECH_ERA.get(tech, "?")
        group = parse_group(body)

        offense = battle.get("unit_offense_add", 0)
        defense = battle.get("unit_defense_add", 0)
        power = offense + defense  # rough scalar; ignore other axes

        # Power-to-cost ratio (per-cost-per-manpower view)
        if upkeep_total and upkeep_total > 0 and manpower:
            cost_per_man = upkeep_total / manpower * 1000  # per 1k men
            ptc = power / cost_per_man if cost_per_man > 0 else None
        else:
            cost_per_man = None
            ptc = None

        rows.append({
            "id": uid,
            "tech": tech,
            "era": era,
            "group": group,
            "offense": offense,
            "defense": defense,
            "power": power,
            "max_manpower": manpower,
            "upkeep_total": upkeep_total,
            "cost_per_1k": cost_per_man,
            "ptc": ptc,
        })

    print(f"# Combat unit balance audit — {len(rows)} units\n")

    # Per-era summary
    by_era = {}
    for r in rows:
        by_era.setdefault(r["era"], []).append(r)
    for era in sorted(by_era.keys()):
        erows = by_era[era]
        print(f"## {era} — {len(erows)} units")
        for r in erows:
            ptc = f"{r['ptc']:.2f}" if r['ptc'] is not None else "—"
            cost = f"{r['cost_per_1k']:.0f}" if r['cost_per_1k'] is not None else "—"
            mp = r['max_manpower'] or "?"
            print(f"  {r['id']:<60s} ofs={r['offense']:>5g} def={r['defense']:>5g} "
                  f"mp={mp:>5} cost/1k={cost:>6} ptc={ptc}")
        print()

    # Per-group power progression
    print("\n## Per-group power progression\n")
    by_group = {}
    for r in rows:
        by_group.setdefault(r["group"], []).append(r)
    for grp in sorted(by_group.keys()):
        grows = sorted(by_group[grp], key=lambda r: r["era"])
        print(f"### {grp}")
        for r in grows:
            ptc = f"{r['ptc']:.2f}" if r['ptc'] is not None else "—"
            print(f"  {r['era']:<7} {r['id']:<55s} pwr={r['power']:>5g} ptc={ptc}")
        print()

    # Outlier flags
    print("\n## Outlier table\n")
    print("| unit | era | group | ofs+def | upkeep_total | cost/1k | power_per_cost1k |")
    print("|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (r["era"], r["group"] or "", -r["power"])):
        ptc = f"{r['ptc']:.2f}" if r['ptc'] is not None else "—"
        cost = f"{r['cost_per_1k']:.0f}" if r['cost_per_1k'] is not None else "—"
        upk = f"{r['upkeep_total']:.0f}" if r['upkeep_total'] is not None else "—"
        print(f"| `{r['id']}` | {r['era']} | {r['group']} | "
              f"{r['power']:.0f} | {upk} | {cost} | {ptc} |")

    return 0


if __name__ == "__main__":
    sys.exit(main())
