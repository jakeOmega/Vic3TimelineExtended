#!/usr/bin/env python3
"""Audit mod-side combat units for balance review.

Walks common/combat_unit_types/extra_combat_units.txt, extracts each unit's
offense, defense, max_manpower, total upkeep cost (from auto-generated
comments), and unlocking tech. Computes:

- `power` = unit_offense_add + unit_defense_add (raw stat sum, manpower-blind)
- `eff_pwr` = (off+def)/2 × max_manpower/1000 (effective per-battalion combat
  contribution; this is vanilla's POWER_PROJECTION formula and roughly tracks
  battalion-selection-weight × per-tick casualty exchange)
- `ptc` = power × manpower / (upkeep × 1000), i.e. eff_pwr × 2 / upkeep — a
  cost-effectiveness metric (combat output per unit upkeep). NOTE: this is NOT
  per-1000-men efficiency; the manpower term is already in the numerator.

Usage:
    .venv/bin/python scripts/analysis/combat_unit_balance_audit.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from path_constants import base_game_path  # noqa: E402

COMBAT_FILE = REPO / "common" / "combat_unit_types" / "extra_combat_units.txt"
MOD_TECH_DIR = REPO / "common" / "technology" / "technologies"
# Vanilla tech directory — era_5 entries only matter here, but pulling the whole
# tree means the audit auto-tracks any vanilla tech a mod-side unit happens to
# unlock from.
VANILLA_TECH_DIR = Path(base_game_path) / "game" / "common" / "technology" / "technologies"


def build_tech_era_map() -> dict[str, str]:
    """Walk mod + vanilla tech files and read each tech's `era = era_X` field.

    Avoids the maintenance burden of a hand-curated dict (which previously
    drifted out of date — `augmented_reality_warfare`/`swarm_technology`/
    `space_militarization` had moved eras, and four mod-side techs weren't
    listed at all).
    """
    pat = re.compile(
        r"^([a-z_][a-z0-9_]*)\s*=\s*\{",
        re.MULTILINE,
    )
    era_pat = re.compile(r"\bera\s*=\s*(era_\d+)")

    out: dict[str, str] = {}
    for tech_dir in (VANILLA_TECH_DIR, MOD_TECH_DIR):
        if not tech_dir.exists():
            continue
        for txt in sorted(tech_dir.glob("*.txt")):
            try:
                text = txt.read_text(encoding="utf-8-sig")
            except OSError:
                continue
            # Walk each top-level `<tech_id> = { ... era = era_X ... }` block.
            i = 0
            while i < len(text):
                m = pat.search(text, i)
                if not m:
                    break
                tech_id = m.group(1)
                body_start = m.end()
                depth = 1
                j = body_start
                while j < len(text) and depth > 0:
                    c = text[j]
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                    j += 1
                era_m = era_pat.search(text, body_start, j)
                if era_m:
                    out[tech_id] = era_m.group(1)
                i = j
    return out


TECH_ERA = build_tech_era_map()


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
        power = offense + defense  # raw stat sum, manpower-blind
        # Effective per-battalion combat contribution (vanilla POWER_PROJECTION
        # formula: (off+def)/2 × manpower/1000). Two units with identical raw
        # stats but different max_manpower deliver effective power in proportion
        # to their manpower — this is what battles actually exchange.
        eff_pwr = (power / 2) * (manpower / 1000) if manpower else None

        # Cost-effectiveness: combat output per unit upkeep.
        # ptc = power × manpower / (upkeep × 1000) = eff_pwr × 2 / upkeep.
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
            "eff_pwr": eff_pwr,
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

    def era_key(e: str) -> tuple[int, str]:
        m = re.match(r"era_(\d+)", e)
        return (int(m.group(1)) if m else 9999, e)

    for era in sorted(by_era.keys(), key=era_key):
        erows = by_era[era]
        print(f"## {era} — {len(erows)} units")
        for r in erows:
            ptc = f"{r['ptc']:.2f}" if r['ptc'] is not None else "—"
            cost = f"{r['cost_per_1k']:.0f}" if r['cost_per_1k'] is not None else "—"
            eff = f"{r['eff_pwr']:.0f}" if r['eff_pwr'] is not None else "—"
            mp = r['max_manpower'] or "?"
            print(f"  {r['id']:<60s} ofs={r['offense']:>5g} def={r['defense']:>5g} "
                  f"mp={mp:>5} eff_pwr={eff:>5} cost/1k={cost:>6} ptc={ptc}")
        print()

    # Per-group power progression
    print("\n## Per-group power progression\n")
    by_group = {}
    for r in rows:
        by_group.setdefault(r["group"], []).append(r)
    for grp in sorted(by_group.keys()):
        grows = sorted(by_group[grp], key=lambda r: era_key(r["era"]))
        print(f"### {grp}")
        for r in grows:
            ptc = f"{r['ptc']:.2f}" if r['ptc'] is not None else "—"
            eff = f"{r['eff_pwr']:.0f}" if r['eff_pwr'] is not None else "—"
            print(f"  {r['era']:<7} {r['id']:<55s} pwr={r['power']:>5g} "
                  f"eff_pwr={eff:>5} ptc={ptc}")
        print()

    # Outlier flags
    print("\n## Outlier table\n")
    print("| unit | era | group | ofs+def | mp | eff_pwr | upkeep | ptc |")
    print("|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (era_key(r["era"]), r["group"] or "", -r["power"])):
        ptc = f"{r['ptc']:.2f}" if r['ptc'] is not None else "—"
        eff = f"{r['eff_pwr']:.0f}" if r['eff_pwr'] is not None else "—"
        upk = f"{r['upkeep_total']:.0f}" if r['upkeep_total'] is not None else "—"
        mp = r['max_manpower'] or "?"
        print(f"| `{r['id']}` | {r['era']} | {r['group']} | "
              f"{r['power']:.0f} | {mp} | {eff} | {upk} | {ptc} |")

    return 0


if __name__ == "__main__":
    sys.exit(main())
