#!/usr/bin/env python3
"""Snapshot the mod's balance-relevant modifier values to JSON.

Capture key gameplay values from combat unit types, ship types, technologies,
and laws so that — after a vanilla patch update or major rebalance — the
intended progression curve can be diffed against this snapshot.

Usage:
    python3 scripts/snapshot_balance.py            # writes docs/data/balance_snapshot.json
    python3 scripts/snapshot_balance.py --print    # also prints a summary to stdout

The output is a JSON dict keyed by category, each containing a list of
{name, modifiers} entries. Only the values that matter for gameplay
balance — combat stats, construction costs, key tech bonuses — are captured.
Cosmetic fields (icon paths, textures) are excluded.

Why this exists: pre-1.13 the mod's hypersonic missile platform had
unit_offense_add = 4000; post-1.13 the equivalent is ship_hull_damage_add.
Translating between systems requires knowing the original values. Without a
snapshot, that knowledge lives only in human memory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Canonical mod root — script lives under scripts/, snapshot lives under docs/data/.
MOD_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = MOD_ROOT / "docs" / "data" / "balance_snapshot.json"

# Modifier name patterns that are balance-relevant. Anything matching is captured.
RELEVANT_PATTERNS = [
    # Combat / unit stats
    r"^unit_(offense|defense|morale|kill_rate|experience_gain)_(add|mult)$",
    r"^unit_devastation_mult$",
    r"^unit_occupation_mult$",
    # Formation
    r"^military_formation_(army|fleet)_movement_speed_(add|mult)$",
    r"^military_formation_(mobilization_speed|organization_gain)_(add|mult)$",
    # Ship-type stats (1.13+)
    r"^ship_(hit_points_max|crew_max|movement_speed|supply_capacity|hull_damage|crew_damage|armor|critical_hit_chance|critical_hit_multiplier|vulnerability|screening|readiness_gain|accuracy|visibility|detection|blockade_strength|carrying_capacity|marine_capacity|construction_progress_max)_(add|mult)$",
    r"^ship_battle_against_ship_type_[a-z_]+_(accuracy|hull_damage)_(add|mult)$",
    # Country-level military
    r"^country_(general|admiral)_rank_impact_mult$",
    r"^country_max_unassigned_(generals|admirals)_add$",
    r"^country_admiral_rank_impact_mult$",
    r"^country_(army|navy)_goods_cost_mult$",
    r"^country_ship_construction_(progress_max|efficiency)_(add|mult)$",
    r"^country_ship_(group|type)_[a-z_]+_construction_(efficiency|progress_max)_(add|mult)$",
    r"^country_supply_ship_construction_(progress_max|ratio)_(add|mult)$",
    r"^country_max_supply_ships_add$",
    r"^character_(command_limit|convoy_protection|convoy_raiding|raid_supply|piracy_goods_capacity|naval_mission_area|max_offensive_battles|loyalty|prominence)_(add|mult)$",
    # Construction goods cost
    r"^goods_input_[a-z_]+_(add|mult)$",
    # Modification / construction cost (ship designer)
    r"^modification_construction_cost$",
    r"^combat_power_multiplier$",
    # Building / state
    r"^building_(shipyard|naval_administration|naval_fortification|naval_logistics_center|barrack|port)_throughput_add$",
    r"^state_building_(shipyard|naval_administration|naval_fortification|naval_logistics_center|barrack)_max_level_(add|mult)$",
]
RELEVANT_RE = re.compile("|".join(f"(?:{p})" for p in RELEVANT_PATTERNS))


def is_relevant(modifier_name: str) -> bool:
    """Return True if a modifier name is balance-relevant."""
    return bool(RELEVANT_RE.match(modifier_name))


_BLOCK_RE = re.compile(r"^([a-z_][a-z_0-9]*)\s*=\s*\{", re.MULTILINE)


def find_balance_for_block(text: str, block_start: int) -> dict[str, str]:
    """Walk a brace-balanced block starting at `block_start` (the position of the
    opening `{`) and return relevant modifier_name → value pairs anywhere inside.
    Stops at the matching close brace.
    """
    depth = 0
    end = block_start
    n = len(text)
    while end < n:
        c = text[end]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end += 1
                break
        end += 1
    body = text[block_start + 1 : end - 1]
    out: dict[str, str] = {}
    for m in re.finditer(r"^\s*([a-z_][a-z_0-9]*)\s*=\s*([^\s\n][^\n]*?)\s*$", body, re.MULTILINE):
        name, val = m.group(1), m.group(2).strip()
        if is_relevant(name):
            out[name] = val
    return out


def snapshot_dir(dir_path: Path) -> list[dict]:
    """Walk every top-level entity in every .txt under dir_path and capture
    balance-relevant modifiers.
    """
    if not dir_path.is_dir():
        return []
    entries = []
    for f in sorted(dir_path.glob("*.txt")):
        text = f.read_text(encoding="utf-8-sig")
        # Strip line comments
        text = re.sub(r"#[^\n]*", "", text)
        # Find each top-level (column-0) "name = {" — we only want the entity
        # blocks, not nested ones.
        for m in re.finditer(r"^([a-z_][a-z_0-9]*)\s*=\s*\{", text, re.MULTILINE):
            name = m.group(1)
            block_start = m.end() - 1  # position of the `{`
            modifiers = find_balance_for_block(text, block_start)
            if modifiers:
                entries.append({
                    "name": name,
                    "file": str(f.relative_to(MOD_ROOT)),
                    "modifiers": modifiers,
                })
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--print", action="store_true", help="Also print a summary to stdout")
    args = parser.parse_args()

    snapshot = {
        "combat_unit_types": snapshot_dir(MOD_ROOT / "common" / "combat_unit_types"),
        "ship_types": snapshot_dir(MOD_ROOT / "common" / "ship_types"),
        "technologies": [
            entry
            for sub in [
                snapshot_dir(MOD_ROOT / "common" / "technology" / "technologies"),
            ]
            for entry in sub
        ],
        "static_modifiers": snapshot_dir(MOD_ROOT / "common" / "static_modifiers"),
        "production_methods": snapshot_dir(MOD_ROOT / "common" / "production_methods"),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")

    if args.print:
        for category, entries in snapshot.items():
            print(f"{category}: {len(entries)} entries with relevant modifiers")
            for e in entries[:3]:
                summary = ", ".join(f"{k}={v}" for k, v in list(e["modifiers"].items())[:3])
                print(f"  {e['name']:40s} {summary}")
    print(f"wrote {out_path} (combat_unit_types={len(snapshot['combat_unit_types'])}, "
          f"ship_types={len(snapshot['ship_types'])}, "
          f"technologies={len(snapshot['technologies'])}, "
          f"static_modifiers={len(snapshot['static_modifiers'])}, "
          f"production_methods={len(snapshot['production_methods'])})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
