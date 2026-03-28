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
import matplotlib
import numpy as np
matplotlib.use("TkAgg")

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


def political_strength(wealth_level: int) -> int:
    """Default political strength function (linear baseline).

    The default mirrors the previous extrapolation formula used for new
    wealth levels: `25 * wl - 975`, clamped to >= 0. Override this function
    in code if you want a different curve.
    """
    if wealth_level < 1:
        return 0
    elif wealth_level <= 49:
        p = wealth_level ** 3.5 / 50**2 + 0.015
        if p < 1:
            return round(p, 2)
        elif p < 8:
            return round(p, 1)
        return int(p)
    return max(0, int(wealth_level ** 2.5 / 50))


POLITICAL_STRENGTH_FUNC = political_strength


def _format_number(v) -> str:
    """Format numeric value for insertion into Paradox script.

    Use integer formatting when value is an integer, otherwise preserve
    decimal representation.
    """
    try:
        if isinstance(v, int):
            return str(v)
        if isinstance(v, float):
            if v.is_integer():
                return str(int(v))
            return str(v)
        # fallback for other numeric-like types
        return str(v)
    except Exception:
        return str(v)


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


def generate_buy_packages(dry_run: bool = False, replace_political: bool = False) -> str:
    """Read vanilla buy_packages, apply modded need curves, optionally replace
    political strength values, and write output.

    Returns the generated content as a string.
    """
    input_file = os.path.join(base_game_path, "game", "common", "buy_packages", "00_buy_packages.txt")
    output_file = os.path.join(mod_path, "common", "buy_packages", "00_buy_packages.txt")

    with open(input_file, "r", encoding="utf-8-sig") as f:
        file_text = f.read()

    # Parse wealth blocks robustly using brace matching
    blocks = {}
    for m in re.finditer(r"wealth_(\d+)\s*=", file_text):
        wl = int(m.group(1))
        start = m.start()
        brace = file_text.find("{", start)
        if brace == -1:
            continue
        depth = 1
        pos = brace + 1
        n = len(file_text)
        while pos < n and depth > 0:
            c = file_text[pos]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            pos += 1
        end = pos
        blocks[wl] = file_text[start:end]

    # Apply need curve replacements and insertions
    for wl in list(blocks.keys()):
        block = blocks[wl]
        for need_name, need_func in NEED_CURVES.items():
            need_val = need_func(wl)
            # replace existing need value (allow decimals)
            if re.search(rf"{need_name}\s*=\s*[-+]?[0-9]+(?:\.[0-9]+)?", block):
                block = re.sub(
                    rf"({need_name}\s*=\s*)[-+]?[0-9]+(?:\.[0-9]+)?",
                    lambda m, nv=need_val: m.group(1) + str(int(nv)),
                    block,
                    count=1,
                )
            else:
                if need_val == 0:
                    continue
                # insert into goods block
                gm = re.search(r"goods\s*=\s*\{", block)
                if gm:
                    goods_start = block.find("{", gm.start())
                    depth = 1
                    pos = goods_start + 1
                    while pos < len(block) and depth > 0:
                        c = block[pos]
                        if c == "{":
                            depth += 1
                        elif c == "}":
                            depth -= 1
                        pos += 1
                    goods_end = pos
                    insert_at = goods_end - 1
                    block = block[:insert_at] + f"\t\t{need_name} = {int(need_val)}\n" + block[insert_at:]
                else:
                    # fallback: append a goods block
                    block = block.rstrip()[:-1] + f"\n\tgoods = {{\n\t\t{need_name} = {int(need_val)}\n\t}}\n}}"
        blocks[wl] = block

    # Extrapolate for wealth levels 100-200
    all_needs = _extract_all_needs(list(blocks.values()))

    def _get_need_value(need, wealth_level):
        block = blocks.get(wealth_level)
        if not block:
            return 0
        m = re.search(rf"{need}\s*=\s*([0-9]+)", block)
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
                if i in blocks:
                    block = blocks[i]
                    if re.search(rf"{need}\s*=\s*[-+]?[0-9]+(?:\.[0-9]+)?", block):
                        block = re.sub(
                            rf"({need}\s*=\s*)[-+]?[0-9]+(?:\.[0-9]+)?",
                            lambda m, nv=extrapolated: m.group(1) + str(int(nv)),
                            block,
                            count=1,
                        )
                    else:
                        gm = re.search(r"goods\s*=\s*\{", block)
                        if gm:
                            goods_start = block.find("{", gm.start())
                            depth = 1
                            pos = goods_start + 1
                            while pos < len(block) and depth > 0:
                                c = block[pos]
                                if c == "{":
                                    depth += 1
                                elif c == "}":
                                    depth -= 1
                                pos += 1
                            goods_end = pos
                            insert_at = goods_end - 1
                            block = block[:insert_at] + f"\t\t{need} = {extrapolated}\n" + block[insert_at:]
                        else:
                            block = block.rstrip()[:-1] + f"\n\tgoods = {{\n\t\t{need} = {extrapolated}\n\t}}\n}}"
                    blocks[i] = block
                else:
                    ps_val = POLITICAL_STRENGTH_FUNC(i) if replace_political else 25 * i - 975
                    ps_str = _format_number(ps_val)
                    blocks[i] = (
                        f"wealth_{i} = {{\n\tpolitical_strength = {ps_str}\n"
                        f"\tgoods = {{\n\t\t{need} = {extrapolated}\n\t}}\n}}"
                    )

    # Replace or insert political_strength/political_power for existing wealth levels if requested
    if replace_political:
        for wl in list(blocks.keys()):
            block = blocks[wl]
            ps_val = POLITICAL_STRENGTH_FUNC(wl)
            ps_str = _format_number(ps_val)
            if re.search(r"political_(?:strength|power)\s*=\s*[-+]?[0-9]+(?:\.[0-9]+)?", block):
                block = re.sub(
                    r"(political_(?:strength|power)\s*=\s*)[-+]?[0-9]+(?:\.[0-9]+)?",
                    lambda m, s=ps_str: m.group(1) + s,
                    block,
                    count=1,
                )
            else:
                block = re.sub(
                    r"(wealth_\d+\s*=\s*\{)",
                    lambda m, s=ps_str: f"{m.group(1)}\n\tpolitical_strength = {s}",
                    block,
                    count=1,
                )
            blocks[wl] = block

    # Assemble final content
    entries = [blocks[wl] for wl in sorted(blocks.keys())]
    result = "# AUTO-GENERATED by pop_needs_curves.py - Do not edit manually\n\n" + "\n\n".join(entries)

    if dry_run:
        print(f"[dry-run] Would write {len(result)} bytes to {output_file}")
    else:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
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
    """Robustly extract goods dict for each wealth level using brace matching."""
    pkgs = {}
    for m in re.finditer(r"wealth_(\d+)\s*=", content):
        wl = int(m.group(1))
        block = _extract_wealth_block(content, wl)
        if not block:
            continue
        goods = {}
        gm = re.search(r"goods\s*=\s*\{", block)
        if gm:
            goods_start = block.find("{", gm.start())
            depth = 1
            pos = goods_start + 1
            while pos < len(block) and depth > 0:
                c = block[pos]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                pos += 1
            goods_content = block[goods_start+1:pos-1]
            for line in goods_content.strip().splitlines():
                parts = line.split("=")
                if len(parts) >= 2:
                    key = parts[0].strip()
                    val = parts[1].split("#")[0].strip()
                    try:
                        goods[key] = int(val)
                    except Exception:
                        # ignore non-integer values
                        continue
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


def _extract_wealth_block(content: str, wl: int) -> str | None:
    idx = content.find(f"wealth_{wl}")
    if idx == -1:
        return None
    start = content.find("{", idx)
    if start == -1:
        return None
    depth = 1
    pos = start + 1
    n = len(content)
    while pos < n and depth > 0:
        c = content[pos]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        pos += 1
    return content[start+1:pos-1]


def extract_political_strengths_from_buy_packages(content: str) -> dict:
    """Return dict mapping wealth level -> political_strength (int)."""
    wls = [int(m) for m in re.findall(r"wealth_(\d+)\s*=", content)]
    strengths = {}
    for wl in sorted(set(wls)):
        block = _extract_wealth_block(content, wl)
        if not block:
            continue
        m = re.search(r"political_(?:strength|power)\s*=\s*([-+]?[0-9]+(?:\.[0-9]+)?)", block)
        if m:
            try:
                strengths[wl] = float(m.group(1))
            except Exception:
                strengths[wl] = float(m.group(1))
    return strengths


def plot_political_strength():
    """Extract vanilla political strength per wealth level and plot it."""
    import matplotlib.pyplot as plt

    vanilla_path = os.path.join(base_game_path, "game", "common", "buy_packages", "00_buy_packages.txt")
    if not os.path.exists(vanilla_path):
        print(f"Vanilla buy_packages not found at {vanilla_path}")
        return
    with open(vanilla_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    strengths = extract_political_strengths_from_buy_packages(content)
    if not strengths:
        print("No political strength entries found in vanilla buy_packages.")
        return

    items = sorted(strengths.items())
    wls = [wl for wl, _ in items]
    vals = [v for _, v in items]

    # semilog plot with a power-law reference line for comparison
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_yscale("log")
    ax.plot(wls, vals, marker="o", linestyle="-")
    wfun = np.linspace(min(wls), max(wls), 2000)
    vfun = [POLITICAL_STRENGTH_FUNC(int(w)) for w in wfun]
    ax.plot(wfun, vfun, linestyle="--", label="test (for comparison)")
    ax.set_title("Vanilla Political Strength by Wealth Level", fontsize=14)
    ax.set_xlabel("Wealth Level", fontsize=12)
    ax.set_ylabel("Political Strength", fontsize=12)
    ax.grid(True)
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
    parser.add_argument("--plot-political", action="store_true",
                        help="Plot vanilla political strength by wealth level")
    parser.add_argument("--replace-political", action="store_true", default=True,
                        help="Replace political_strength in generated buy_packages with values from political_strength()")
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
    elif args.plot_political:
        plot_political_strength()
    elif args.plot:
        generate_buy_packages(dry_run=args.dry_run, replace_political=args.replace_political)
        plot_expenditure()
    else:
        generate_buy_packages(dry_run=args.dry_run, replace_political=args.replace_political)
        print_expenditure_table()


if __name__ == "__main__":
    main()
