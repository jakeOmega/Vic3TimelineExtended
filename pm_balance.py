"""Production method balance calculator — find input goods amounts for a target profit.

Uses a Newton-Raphson solver to determine how much of each input good a production
method should consume to achieve a desired profit, given fixed output goods.

Usage:
    python pm_balance.py --inputs steel:11 glass:11 tools:5 --outputs services:1000 --profit 1000
    python pm_balance.py --inputs steel:11 glass:11 --outputs services:500 --profit 200 --round 5
    python pm_balance.py --list-goods          # List all goods and their prices

Functions are importable:
    from pm_balance import calculate_input_goods_amounts, load_goods_prices
"""

import argparse
import os
import sys
from typing import List, Tuple

from path_constants import base_game_path, mod_path


# ── Goods Parsing ─────────────────────────────────────────────────────────────

def load_goods_prices(extra_files: list[str] | None = None) -> dict[str, int]:
    """Parse goods files and return {good_name: cost} dict.

    By default loads vanilla + mod goods. Pass extra_files to add more.
    """
    files = [
        os.path.join(base_game_path, "game", "common", "goods", "00_goods.txt"),
        os.path.join(mod_path, "common", "goods", "timeline_extended_extra_goods.txt"),
    ]
    if extra_files:
        files.extend(extra_files)

    goods = {}
    for filepath in files:
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8-sig") as f:
            good_name = None
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    continue
                parts = line.split("=", 1)
                if len(parts) != 2:
                    continue
                key = parts[0].strip()
                val = parts[1].strip()
                if val == "{":
                    good_name = key
                elif key == "cost" and good_name:
                    try:
                        goods[good_name] = int(val)
                    except ValueError:
                        pass
                elif "}" in val:
                    good_name = None
    return goods


# ── Solver ────────────────────────────────────────────────────────────────────

def calculate_total_cost(goods_prices: dict, goods: List[Tuple[str, float]]) -> float:
    """Sum of amount * price for each (good, amount) pair."""
    return sum(amount * goods_prices[good] for good, amount in goods)


def calculate_input_goods_amounts(
    goods_prices: dict,
    input_goods: List[Tuple[str, float]],
    output_goods: List[Tuple[str, float]],
    desired_profit: float,
    rounding_base: float = 1,
) -> Tuple[dict, float]:
    """Newton-Raphson solver: find input amounts that yield desired_profit.

    Args:
        goods_prices: {good_name: base_price}
        input_goods: [(good_name, ratio), ...] — relative proportions of inputs
        output_goods: [(good_name, fixed_amount), ...] — fixed output quantities
        desired_profit: target profit (output_revenue - input_cost)
        rounding_base: round each input amount to nearest multiple of this

    Returns:
        (input_amounts_dict, actual_profit)
    """
    total_output_revenue = calculate_total_cost(goods_prices, output_goods)
    min_input_amount = 0
    max_input_amount = total_output_revenue / min(
        goods_prices[good] for good, _ in input_goods
    )
    total_input_amount = (min_input_amount + max_input_amount) / 2
    step_size = 0.001

    for _ in range(1_000_000):
        cost = calculate_total_cost(
            goods_prices,
            [(good, total_input_amount * ratio) for good, ratio in input_goods],
        )
        profit = total_output_revenue - cost
        if abs(profit - desired_profit) < 1e-6:
            break
        delta = 1e-6
        cost_delta = calculate_total_cost(
            goods_prices,
            [(good, (total_input_amount + delta) * ratio) for good, ratio in input_goods],
        )
        derivative = (total_output_revenue - cost_delta - profit) / delta
        total_input_amount -= step_size * (profit - desired_profit) / derivative

    # Round
    input_amounts = {
        good: round(total_input_amount * ratio / rounding_base) * rounding_base
        for good, ratio in input_goods
    }
    actual_profit = total_output_revenue - calculate_total_cost(
        goods_prices, list(input_amounts.items())
    )
    return input_amounts, actual_profit


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_goods_arg(arg_list: list[str]) -> List[Tuple[str, float]]:
    """Parse 'good:amount' pairs from CLI args."""
    result = []
    for item in arg_list:
        parts = item.split(":")
        if len(parts) != 2:
            print(f"Error: '{item}' should be 'good_name:amount'", file=sys.stderr)
            sys.exit(1)
        result.append((parts[0], float(parts[1])))
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Calculate input goods amounts for a target profit in a production method"
    )
    parser.add_argument("--list-goods", action="store_true",
                        help="List all goods and their base prices")
    parser.add_argument("--inputs", nargs="+", metavar="GOOD:RATIO",
                        help="Input goods with ratio weights (e.g. steel:11 glass:11)")
    parser.add_argument("--outputs", nargs="+", metavar="GOOD:AMOUNT",
                        help="Output goods with fixed amounts (e.g. services:1000)")
    parser.add_argument("--profit", type=float, default=0,
                        help="Desired profit (output revenue - input cost)")
    parser.add_argument("--round", type=float, default=1,
                        help="Round input amounts to nearest multiple (default: 1)")
    args = parser.parse_args()

    goods_prices = load_goods_prices()

    if args.list_goods:
        print(f"{'Good':<35} {'Price':>6}")
        print(f"{'-' * 35} {'-' * 6}")
        for good, price in sorted(goods_prices.items()):
            print(f"{good:<35} {price:>6}")
        return

    if not args.inputs or not args.outputs:
        parser.print_help()
        return

    input_goods = _parse_goods_arg(args.inputs)
    output_goods = _parse_goods_arg(args.outputs)

    # Validate goods exist
    for good, _ in input_goods + output_goods:
        if good not in goods_prices:
            print(f"Error: '{good}' not found in goods. Use --list-goods to see available.", file=sys.stderr)
            sys.exit(1)

    input_amounts, actual_profit = calculate_input_goods_amounts(
        goods_prices, input_goods, output_goods, args.profit, args.round
    )
    output_revenue = calculate_total_cost(goods_prices, output_goods)
    input_cost = calculate_total_cost(goods_prices, list(input_amounts.items()))

    # Print results
    print("\n=== Output Goods (fixed) ===")
    for good, amount in output_goods:
        print(f"  {good:<30} {amount:>8.1f}  x {goods_prices[good]:>4} = {amount * goods_prices[good]:>10.1f}")
    print(f"  {'Total revenue':<30} {'':>8}  {'':>6}   {output_revenue:>10.1f}")

    print("\n=== Input Goods (calculated) ===")
    for good, amount in input_amounts.items():
        print(f"  {good:<30} {amount:>8.1f}  x {goods_prices[good]:>4} = {amount * goods_prices[good]:>10.1f}")
    print(f"  {'Total cost':<30} {'':>8}  {'':>6}   {input_cost:>10.1f}")

    margin = (actual_profit / input_cost * 100) if input_cost else 0
    print(f"\n  Profit: {actual_profit:.1f}  (margin: {margin:+.1f}%)")


if __name__ == "__main__":
    main()
