"""Pop needs curve definitions and buy_packages generator.

Defines mathematical functions for how pop consumption of convenience, services,
art, and tourism scale with wealth level. Generates modified buy_packages files
and can display expenditure tables or plots.

Usage:
    python pop_needs_curves.py                # Generate buy_packages + print expenditure table
    python pop_needs_curves.py --table        # Print needs amounts at each wealth level (no file writes)
    python pop_needs_curves.py --table --need services  # Just one need
    python pop_needs_curves.py --plot         # Also show expenditure plots
    python pop_needs_curves.py --dry-run      # Show what would be written without writing

Functions are importable:
    from pop_needs_curves import convenience_need, services_need, art_need, tourism_need
"""

import argparse
import math
import os
import re
import sys

from path_constants import base_game_path, mod_path


# ── Need Curve Functions ──────────────────────────────────────────────────────

def convenience_need(wealth_level: int) -> int:
    """Convenience goods demand at a given wealth level."""
    if wealth_level < 20:
        return 0
    return int(0.7 * ((wealth_level - 19) ** 3 / 4 + 1) * (1 + 3 * math.tanh(wealth_level / 200)))


def services_need(wealth_level: int) -> int:
    """Services demand at a given wealth level."""
    if wealth_level < 9:
        return 0
    elif wealth_level == 9:
        return 24
    elif wealth_level == 10:
        return 30
    elif wealth_level == 11:
        return 39
    elif wealth_level == 12:
        return 46
    elif wealth_level == 13:
        return 58
    elif wealth_level == 14:
        return 64
    else:
        return 75 + int(50 * (math.exp(0.14 * (wealth_level - 15)) - 1))


def art_need(wealth_level: int) -> int:
    """Art/luxury goods demand at a given wealth level."""
    if wealth_level < 25:
        return 0
    elif wealth_level < 50:
        return int(0.02 * (wealth_level - 24) ** 3.2 + 1)
    elif wealth_level < 75:
        base = int(0.02 * (25) ** 3.2 + 1)
        exp = math.exp(0.12 * (wealth_level - 49))
        return int(base * exp)
    else:
        base = art_need(74)
        exp = math.exp(0.15 * (wealth_level - 74))
        return int(base * exp)


def tourism_need(wealth_level: int) -> int:
    """Tourism demand at a given wealth level."""
    if wealth_level < 25:
        return 0
    elif wealth_level < 35:
        return int((wealth_level - 24) ** 1.5)
    elif wealth_level < 40:
        base = tourism_need(34)
        exp = math.exp(0.4 * (wealth_level - 34))
        return int(base * exp)
    elif wealth_level < 45:
        base = tourism_need(39)
        exp = math.exp(0.2 * (wealth_level - 39))
        return int(base * exp)
    else:
        base = tourism_need(44)
        exp = math.exp(0.14 * (wealth_level - 44))
        return int(base * exp)


# All modded need curves
NEED_CURVES = {
    "popneed_convenience": convenience_need,
    "popneed_services": services_need,
    "popneed_art": art_need,
    "popneed_tourism": tourism_need,
}


# ── Text Output ───────────────────────────────────────────────────────────────

def print_needs_table(need_filter: str | None = None, wl_min: int = 1, wl_max: int = 100):
    """Print a text table of need amounts at each wealth level."""
    curves = NEED_CURVES
    if need_filter:
        key = need_filter if need_filter.startswith("popneed_") else f"popneed_{need_filter}"
        if key in curves:
            curves = {key: curves[key]}
        else:
            print(f"Unknown need '{need_filter}'. Available: {', '.join(curves.keys())}")
            return

    # Header
    headers = ["WL"] + [k.replace("popneed_", "") for k in curves]
    widths = [max(4, len(h) + 2) for h in headers]
    header_line = "  ".join(h.rjust(w) for h, w in zip(headers, widths))
    print(header_line)
    print("  ".join("-" * w for w in widths))

    for wl in range(wl_min, wl_max + 1):
        values = [str(wl)] + [str(func(wl)) for func in curves.values()]
        print("  ".join(v.rjust(w) for v, w in zip(values, widths)))


# ── Buy Package Generation ───────────────────────────────────────────────────

def _change_one(wealth_level, input_match, need_func):
    """Regex substitution helper: replace a need value in a buy_package entry."""
    text = input_match.group(0)
    match = re.match(r"([a-zA-Z_]+) = ([0-9\.]+)", text)
    key = match.group(1)
    return f"{key} = {need_func(wealth_level)}"


def _extract_all_needs(matches):
    all_needs = set()
    for match in matches:
        goods = re.findall(r"popneed_\w+ = \d+", match)
        for good in goods:
            need = good.split(" = ")[0]
            all_needs.add(need)
    return list(all_needs)


def _fit_power_law(x, y):
    import numpy as np
    x, y = np.array(x), np.array(y)
    if len(x) < 2 or np.any(y <= 0):
        return None
    try:
        log_x, log_y = np.log(x), np.log(y)
        slope, intercept = np.polyfit(log_x, log_y, 1)
        return np.exp(intercept), slope
    except Exception:
        return None


def _extrapolate_power_law(x, a, b):
    return a * (x ** b)


def generate_buy_packages(dry_run: bool = False) -> str:
    """Read vanilla buy_packages, apply modded need curves, and write output.

    Returns the generated content as a string.
    """
    input_file = os.path.join(base_game_path, "game", "common", "buy_packages", "00_buy_packages.txt")
    output_file = os.path.join(mod_path, "common", "buy_packages", "00_buy_packages.txt")

    with open(input_file, "r", encoding="utf-8-sig") as f:
        file_text = f.read()

    matches = re.findall(r"wealth_[0-9]+ = \{.*?\n\}", file_text, re.DOTALL)

    # Apply modded need curves to existing wealth levels
    for need_name, need_func in NEED_CURVES.items():
        for i in range(len(matches)):
            if re.findall(need_name + r" = [0-9\.]+", matches[i]):
                func = lambda x, _i=i, _nf=need_func: _change_one(_i, x, _nf)
                matches[i] = re.sub(need_name + r" = [0-9\.]+", func, matches[i])
            else:
                if need_func(i) == 0:
                    continue
                lines = [l for l in matches[i].split("\n") if l]
                matches[i] = (
                    "\n".join(lines[:-2])
                    + f"\n\t\t{need_name} = {need_func(i)}"
                    + "\n\t}\n}"
                )

    # Extrapolate for wealth levels 100-200
    all_needs = _extract_all_needs(matches)

    def _get_need_value(need, wealth_level):
        for match in matches:
            if f"wealth_{wealth_level}" in match:
                m = re.search(f"{need} = (\\d+)", match)
                if m:
                    return int(m.group(1))
        return 0

    for need in all_needs:
        x_data = list(range(90, 100))
        y_data = [_get_need_value(need, i) for i in x_data]
        if any(y_data):
            params = _fit_power_law(x_data, y_data)
            if params is None:
                continue
            for i in range(100, 201):
                extrapolated = max(0, int(_extrapolate_power_law(i, *params)))
                entry = next((e for e in matches if f"wealth_{i} = {{" in e), None)
                if entry:
                    updated = re.sub(
                        r"(wealth_\d+ = \{.*?goods = \{)(.*?)(\}.*?\})",
                        rf"\1\2\t{need} = {extrapolated}\n\t\3",
                        entry, flags=re.DOTALL,
                    )
                    matches[matches.index(entry)] = updated
                else:
                    matches.append(
                        f"wealth_{i} = {{\n    political_strength = {25 * i - 975:}\n"
                        f"    goods = {{\n\t\t{need} = {extrapolated}\n    }}\n}}"
                    )

    matches.sort(key=lambda x: int(re.search(r"wealth_(\d+)", x).group(1)))
    result = "\n\n".join(matches)

    if dry_run:
        print(f"[dry-run] Would write {len(result)} bytes to {output_file}")
    else:
        with open(output_file, "w", encoding="utf-8-sig") as f:
            f.write(result)
        print(f"Wrote {output_file}")

    return result


# ── Expenditure Analysis ──────────────────────────────────────────────────────

def _read_and_combine(file_paths):
    combined = ""
    for fp in file_paths:
        with open(fp, "r", encoding="utf-8-sig") as f:
            combined += f.read() + "\n"
    return combined


def _extract_buy_packages(content):
    pattern = re.compile(r"wealth_(\d+) = {.*?goods = {(.*?)\n\t}", re.DOTALL)
    pkgs = {}
    for m in pattern.finditer(content):
        wl = int(m.group(1))
        goods = {}
        for line in m.group(2).strip().split("\n"):
            parts = line.split(" = ")
            if len(parts) == 2:
                goods[parts[0].strip()] = int(parts[1].split("#")[0].strip())
        pkgs[wl] = goods
    return pkgs


def _extract_pop_needs_defaults(content):
    pattern = re.compile(r"popneed_(\w+) = {.*?default = (\w+)", re.DOTALL)
    return {m.group(1): m.group(2) for m in pattern.finditer(content)}


def _extract_goods_cost(content):
    pattern = re.compile(r"(\w+) = {.*?cost = (\d+)", re.DOTALL)
    return {m.group(1): int(m.group(2)) for m in pattern.finditer(content)}


def print_expenditure_table():
    """Print a text table comparing vanilla vs modded weekly expenditure per wealth level."""
    vanilla_path = os.path.join(base_game_path, "game", "common", "buy_packages", "00_buy_packages.txt")
    modded_path = os.path.join(mod_path, "common", "buy_packages", "00_buy_packages.txt")
    pop_needs_paths = [
        os.path.join(base_game_path, "game", "common", "pop_needs", "00_pop_needs.txt"),
        os.path.join(mod_path, "common", "pop_needs", "extra_pop_needs.txt"),
    ]
    goods_paths = [
        os.path.join(base_game_path, "game", "common", "goods", "00_goods.txt"),
        os.path.join(mod_path, "common", "goods", "timeline_extended_extra_goods.txt"),
    ]

    pop_needs_content = _read_and_combine(pop_needs_paths)
    goods_content = _read_and_combine(goods_paths)
    defaults = _extract_pop_needs_defaults(pop_needs_content)
    goods_cost = _extract_goods_cost(goods_content)

    with open(vanilla_path, "r", encoding="utf-8-sig") as f:
        vanilla_pkgs = _extract_buy_packages(f.read())

    if not os.path.exists(modded_path):
        print(f"Modded buy_packages not found at {modded_path}. Run without --table first to generate.")
        return

    with open(modded_path, "r", encoding="utf-8-sig") as f:
        modded_pkgs = _extract_buy_packages(f.read())

    def _cost(pkgs, wl):
        pkg = pkgs.get(wl, {})
        total = 0
        for need, amount in pkg.items():
            good = defaults.get(need.replace("popneed_", ""))
            if good and good in goods_cost:
                total += amount * goods_cost[good]
        return total / 10000  # per 10k working adults

    max_wl = max(max(vanilla_pkgs.keys(), default=0), max(modded_pkgs.keys(), default=0))
    print(f"{'WL':>4}  {'Vanilla':>10}  {'Modded':>10}  {'Diff':>10}  {'Diff%':>8}")
    print(f"{'---':>4}  {'----------':>10}  {'----------':>10}  {'----------':>10}  {'--------':>8}")
    for wl in range(1, min(max_wl + 1, 101)):
        v = _cost(vanilla_pkgs, wl)
        m = _cost(modded_pkgs, wl)
        d = m - v
        pct = (d / v * 100) if v else 0
        print(f"{wl:>4}  {v:>10.1f}  {m:>10.1f}  {d:>+10.1f}  {pct:>+7.1f}%")


# ── Plot ──────────────────────────────────────────────────────────────────────

def plot_expenditure():
    """Show matplotlib plots comparing vanilla vs modded expenditure."""
    import matplotlib.pyplot as plt

    vanilla_path = os.path.join(base_game_path, "game", "common", "buy_packages", "00_buy_packages.txt")
    modded_path = os.path.join(mod_path, "common", "buy_packages", "00_buy_packages.txt")
    pop_needs_paths = [
        os.path.join(base_game_path, "game", "common", "pop_needs", "00_pop_needs.txt"),
        os.path.join(mod_path, "common", "pop_needs", "extra_pop_needs.txt"),
    ]
    goods_paths = [
        os.path.join(base_game_path, "game", "common", "goods", "00_goods.txt"),
        os.path.join(mod_path, "common", "goods", "timeline_extended_extra_goods.txt"),
    ]

    pop_needs_content = _read_and_combine(pop_needs_paths)
    goods_content = _read_and_combine(goods_paths)
    defaults = _extract_pop_needs_defaults(pop_needs_content)
    goods_cost = _extract_goods_cost(goods_content)

    with open(vanilla_path, "r", encoding="utf-8-sig") as f:
        vanilla_pkgs = _extract_buy_packages(f.read())
    with open(modded_path, "r", encoding="utf-8-sig") as f:
        modded_pkgs = _extract_buy_packages(f.read())

    def _pkg_cost(pkgs, wl):
        pkg = pkgs.get(wl, {})
        total = 0
        for need, amount in pkg.items():
            good = defaults.get(need.replace("popneed_", ""))
            if good and good in goods_cost:
                total += amount * goods_cost[good]
        return total / 10000

    max_wl = max(max(vanilla_pkgs.keys(), default=0), max(modded_pkgs.keys(), default=0))
    wl_range = list(range(1, max_wl + 1))
    vanilla_costs = [_pkg_cost(vanilla_pkgs, wl) for wl in wl_range]
    modded_costs = [_pkg_cost(modded_pkgs, wl) for wl in wl_range]

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(vanilla_costs, wl_range, marker="o", markersize=2, label="Vanilla")
    ax.plot(modded_costs, wl_range, marker="x", markersize=2, label="Modified")
    ax.set_title("Wealth Level vs. Annual Pop Need Expenditure", fontsize=16)
    ax.set_xlabel("Annual Expenditure (pounds)", fontsize=12)
    ax.set_ylabel("Wealth Level", fontsize=12)
    ax.legend()
    ax.grid(True)
    ax.set_xscale("log")
    plt.tight_layout()
    plt.show()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pop needs curve definitions and buy_packages generator for Victoria 3"
    )
    parser.add_argument("--table", action="store_true",
                        help="Print needs amounts table (no file writes)")
    parser.add_argument("--need", type=str, default=None,
                        help="Filter --table to one need (e.g. 'services', 'art')")
    parser.add_argument("--expenditure", action="store_true",
                        help="Print vanilla vs modded expenditure comparison table")
    parser.add_argument("--plot", action="store_true",
                        help="Show matplotlib expenditure plots")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate buy_packages but don't write to disk")
    parser.add_argument("--range", nargs=2, type=int, metavar=("MIN", "MAX"),
                        help="Wealth level range for --table (default: 1-100)")
    args = parser.parse_args()

    if args.table:
        rng = args.range or [1, 100]
        print_needs_table(args.need, rng[0], rng[1])
    elif args.expenditure:
        print_expenditure_table()
    elif args.plot:
        generate_buy_packages(dry_run=args.dry_run)
        plot_expenditure()
    else:
        generate_buy_packages(dry_run=args.dry_run)
        print_expenditure_table()


if __name__ == "__main__":
    main()
