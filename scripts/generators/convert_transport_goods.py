"""One-off conversion of the transport goods' production methods (#1050).

Transportation (local, base 30) becomes all movement inside a state, and
merchant marine (market-wide, base 50) movement between markets. This script
moves every mod production method's freight input from merchant marine to
transportation, and the listed producers' output with it, scaling each
quantity by 50/30 so the method's spend at base prices stays the same.
Design: docs/superpowers/specs/2026-10-21-transport-goods-design.md.

Run it from the repo root; it rewrites the files in FILES in place:

    python3 scripts/generators/convert_transport_goods.py
    python3 scripts/generators/convert_transport_goods.py --construction-good merchant_marine

The second form is the spec's fallback (§ 2): it hands the construction
methods' freight back to merchant marine and touches nothing else. Change
CONSTRUCTION_GOOD below to match, so test_transport_goods.py checks the tree
you chose. The `# Price:` comments on the lines it rewrites are dropped;
pm_costs puts them back on the next /reload.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = (
    "common/production_methods/extra_pms.txt",
    "common/production_methods/te_construction_market_pms.txt",
    "common/production_methods/unique_pms.txt",
)
PRICE = {"merchant_marine": 50, "transportation": 30}

# Which good the construction methods buy their freight in.
CONSTRUCTION_GOOD = "transportation"

# The only mod methods that keep a merchant marine input: trade between
# markets. Vanilla's four Trade Centre methods take it too.
KEEP_MM_INPUT = frozenset({
    "pm_trade_center_trade_quantity_advanced_1",
    "pm_trade_center_trade_quantity_advanced_2",
    "pm_trade_center_trade_quantity_advanced_3",
    "pm_trade_center_trade_quantity_advanced_4",
})

# Construction Sector tiers, the sector tooling group and the Construction
# Site's twins of the tiers (te_construction_market_pms.txt).
CONSTRUCTION_PMS = frozenset({
    "pm_iron_frame_buildings",
    "pm_steel_frame_buildings",
    "pm_arc_welded_buildings",
    "pm_reinforced_concrete_buildings",
    "pm_advanced_construction",
    "pm_nanomaterial_buildings",
    "pm_prefabricated_building_components",
    "pm_tower_cranes",
    "pm_computer_aided_design",
    "pm_3d_printed_buildings",
    "pm_te_direct_construction_iron_frame",
    "pm_te_direct_construction_steel_frame",
    "pm_te_direct_construction_arc_welded",
    "pm_te_direct_construction_reinforced_concrete",
    "pm_te_direct_construction_advanced",
    "pm_te_direct_construction_nanomaterial",
})

RAILWAY_BASE_PMS = frozenset({
    "pm_early_trains",
    "pm_steam_trains",
    "pm_steam_trains_principle_transport_3",
    "pm_electric_trains",
    "pm_electric_trains_principle_transport_3",
    "pm_diesel_trains",
    "pm_diesel_trains_principle_transport_3",
    "pm_centralized_traffic_control",
    "pm_containerized_cargo",
    "pm_automated_loading_and_unloading",
    "pm_autonomous_trains",
})

HIGHWAY_PMS = frozenset({
    "pm_civil_highway",
    "pm_industrial_highway",
    "pm_electric_civil_highway",
    "pm_electric_industrial_highway",
    "pm_autonomous_highway",
})

# Company buildings for logistics, fulfilment, rail and road. Trading houses,
# shipping lines, docks, wharves, shipyards and canals keep merchant marine.
LAND_COMPANY_PMS = frozenset({
    "pm_generic_logistics_hub",
    "pm_generic_rail_nexus",
    "pm_alibaba_cainiao_park",
    "pm_amazon_fulfillment_center",
    "pm_shopify_fulfillment_hub",
    "pm_volkswagen_autostadt",
})

MM_OUTPUT_TO_TRANSPORTATION = RAILWAY_BASE_PMS | HIGHWAY_PMS | LAND_COMPANY_PMS

_HEADER = re.compile(r"^(?:REPLACE:|REPLACE_OR_CREATE:|INJECT:)?([A-Za-z0-9_\-]+)\s*=\s*\{")
_GOODS = re.compile(r"^(\s*)goods_(input|output)_(merchant_marine|transportation)_add\s*=\s*([0-9.]+)")


def _depth_change(line):
    code = line.split("#", 1)[0]
    return code.count("{") - code.count("}")


def pm_blocks(text):
    """{name: [first_line, end_line)} for every top-level block in `text` (BOM stripped)."""
    blocks, depth, start, name = {}, 0, None, None
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if depth == 0:
            m = _HEADER.match(line)
            if m:
                start, name = i, m.group(1)
        depth += _depth_change(line)
        if depth == 0 and start is not None:
            blocks[name] = (start, i + 1)
            start = None
    return blocks


def _fmt(x):
    x = round(x * 2) / 2
    return str(int(x)) if x == int(x) else f"{x:g}"


def _move(lines, lo, hi, direction, src, dst):
    """Move every `goods_<direction>_<src>_add` line in lines[lo:hi] onto `dst`,
    scaled by price and merged into an existing `dst` line. Returns the lines."""
    block = lines[lo:hi]
    src_at = [i for i, l in enumerate(block) if (m := _GOODS.match(l)) and m.group(2) == direction and m.group(3) == src]
    if not src_at:
        return lines
    amount = sum(float(_GOODS.match(block[i]).group(4)) for i in src_at) * PRICE[src] / PRICE[dst]
    dst_at = [i for i, l in enumerate(block) if (m := _GOODS.match(l)) and m.group(2) == direction and m.group(3) == dst]
    if dst_at:
        amount += float(_GOODS.match(block[dst_at[0]]).group(4))
        keep_at = dst_at[0]
    else:
        keep_at = src_at[0]
    indent = _GOODS.match(block[keep_at]).group(1)
    block[keep_at] = f"{indent}goods_{direction}_{dst}_add = {_fmt(amount)}"
    block = [l for i, l in enumerate(block) if i == keep_at or i not in src_at]
    return lines[:lo] + block + lines[hi:]


def convert(text, construction_good=CONSTRUCTION_GOOD):
    bom = text.startswith("﻿")
    body = text.lstrip("﻿")
    lines = body.split("\n")
    # Work from the bottom so earlier blocks' line numbers stay valid.
    for name, (lo, hi) in sorted(pm_blocks(body).items(), key=lambda kv: -kv[1][0]):
        if construction_good == "merchant_marine":
            if name in CONSTRUCTION_PMS:
                lines = _move(lines, lo, hi, "input", "transportation", "merchant_marine")
            continue
        if name not in KEEP_MM_INPUT:
            before = len(lines)
            lines = _move(lines, lo, hi, "input", "merchant_marine", "transportation")
            hi += len(lines) - before
        if name in MM_OUTPUT_TO_TRANSPORTATION:
            lines = _move(lines, lo, hi, "output", "merchant_marine", "transportation")
    return ("﻿" if bom else "") + "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--construction-good", choices=sorted(PRICE), default="transportation")
    args = ap.parse_args(argv)
    for rel in FILES:
        path = ROOT / rel
        old = path.read_text(encoding="utf-8")
        new = convert(old, args.construction_good)
        if new != old:
            path.write_text(new, encoding="utf-8", newline="")
            print(f"rewrote {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
