#!/usr/bin/env python3
"""Draw the player guide's generated figures into docs/player_guide/images/.

    .venv/bin/pip install -r requirements-docs.txt
    .venv/bin/python scripts/player_guide_figures.py            # write the PNGs
    .venv/bin/python scripts/player_guide_figures.py --print    # print the numbers only

Figures:

* ``pop_spending_by_wealth.png``: how a pop's spending divides between need
  groups at rising wealth, priced at each need's default good's base price, in
  two panels: wealth 5 to 60 in steps of 5, and the full range to 200. It
  reads the mod's generated ``common/buy_packages/00_buy_packages.txt`` (from
  ``pop_needs_curves.py``), so rerun this after changing the needs curves, then
  rebuild the PDF.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pop_needs_curves as needs  # noqa: E402
from path_constants import base_game_path, mod_path  # noqa: E402

IMAGES = REPO_ROOT / "docs" / "player_guide" / "images"
WEALTH_LEVELS = [10, 20, 30, 40, 50, 60, 80, 100, 150, 200]
# The everyday range: most pops sit at or below wealth 60 for most of a campaign.
WEALTH_LEVELS_LOW = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]

# Need groups in stacking order (bottom to top). Colors are the first six
# categorical slots of the dataviz reference palette, in fixed order, validated
# for adjacent-pair colour-vision separation on a light surface.
GROUPS = [
    ("Basic needs", "#2a78d6", ["basic_food", "simple_clothing", "standard_clothing",
                                "crude_items", "heating", "household_items"]),
    ("Luxuries", "#eb6834", ["luxury_food", "luxury_drinks", "luxury_items",
                             "intoxicants", "stimulants"]),
    ("Services and leisure", "#1baf7a", ["services", "leisure", "communication",
                                          "free_movement"]),
    ("Convenience", "#eda100", ["convenience"]),
    ("Art", "#e87ba4", ["art"]),
    ("Tourism", "#008300", ["tourism"]),
]
SURFACE = "#ffffff"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"


def spending_shares(levels: list[int]) -> dict[int, dict[str, float]]:
    """Share of spending per need group at each wealth level in ``levels``."""
    pop_needs = needs._read_and_combine([
        os.path.join(base_game_path, "game", "common", "pop_needs", "00_pop_needs.txt"),
        os.path.join(mod_path, "common", "pop_needs", "extra_pop_needs.txt"),
    ])
    goods = needs._read_and_combine([
        os.path.join(base_game_path, "game", "common", "goods", "00_goods.txt"),
        os.path.join(mod_path, "common", "goods", "timeline_extended_extra_goods.txt"),
    ])
    defaults = needs._extract_pop_needs_defaults(pop_needs)
    cost = needs._extract_goods_cost(goods)
    packages_path = os.path.join(mod_path, "common", "buy_packages", "00_buy_packages.txt")
    with open(packages_path, encoding="utf-8-sig") as f:
        packages = needs._extract_buy_packages(f.read())

    group_of = {need: name for name, _, members in GROUPS for need in members}
    shares: dict[int, dict[str, float]] = {}
    for wealth in levels:
        spend = {name: 0.0 for name, _, _ in GROUPS}
        for popneed, amount in packages.get(wealth, {}).items():
            need = popneed.replace("popneed_", "")
            if need not in group_of:
                continue
            spend[group_of[need]] += amount * cost.get(defaults.get(need, ""), 0)
        total = sum(spend.values()) or 1.0
        shares[wealth] = {name: value / total for name, value in spend.items()}
    return shares


def _luminance(hex_color: str) -> float:
    """WCAG relative luminance, to pick a legible label color on each segment."""
    def channel(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _panel(ax, shares: dict[int, dict[str, float]], levels: list[int], title: str) -> None:
    x = list(range(len(levels)))
    bottoms = [0.0] * len(x)
    for name, color, _ in GROUPS:
        heights = [shares[w][name] * 100 for w in levels]
        # The white edge is the surface gap between stacked segments.
        ax.bar(x, heights, bottom=bottoms, width=0.74, color=color, label=name,
               edgecolor=SURFACE, linewidth=1.0)
        label_color = SURFACE if _luminance(color) < 0.3 else TEXT_PRIMARY
        for i, (h, b) in enumerate(zip(heights, bottoms)):
            if h >= 12:
                ax.text(i, b + h / 2, "{:.0f}".format(h), ha="center", va="center",
                        fontsize=6, color=label_color)
        bottoms = [b + h for b, h in zip(bottoms, heights)]
    ax.set_title(title, fontsize=8.5, color=TEXT_PRIMARY, loc="left")
    ax.set_xticks(x, [str(w) for w in levels], color=TEXT_SECONDARY, fontsize=7)
    ax.set_xlabel("Wealth level", color=TEXT_SECONDARY, fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"],
                  color=TEXT_SECONDARY, fontsize=7)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0)


def draw(low: dict[int, dict[str, float]], full: dict[int, dict[str, float]], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.4, 3.6), dpi=200,
                                      gridspec_kw={"width_ratios": [1.15, 1]})
    fig.patch.set_facecolor(SURFACE)
    for ax in (left, right):
        ax.set_facecolor(SURFACE)
    _panel(left, low, WEALTH_LEVELS_LOW, "Wealth 5 to 60: most pops, most of the game")
    _panel(right, full, WEALTH_LEVELS, "The full range, to wealth 200")
    left.set_ylabel("Share of spending (%)", color=TEXT_SECONDARY, fontsize=8)
    handles, labels = left.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(GROUPS), frameon=False,
               fontsize=7.5, labelcolor=TEXT_PRIMARY, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=SURFACE, metadata={"Software": None})
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--print", action="store_true", help="print the numbers; write nothing")
    args = parser.parse_args(argv)
    low = spending_shares(WEALTH_LEVELS_LOW)
    full = spending_shares(WEALTH_LEVELS)
    for shares, levels in ((low, WEALTH_LEVELS_LOW), (full, WEALTH_LEVELS)):
        for wealth in levels:
            row = "  ".join("{} {:.0f}%".format(n, shares[wealth][n] * 100) for n, _, _ in GROUPS)
            print("wealth {:>3}: {}".format(wealth, row))
    if not args.print:
        out = IMAGES / "pop_spending_by_wealth.png"
        draw(low, full, out)
        print("wrote " + str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
