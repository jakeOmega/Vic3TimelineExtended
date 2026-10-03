"""A buy-package value is a cost at base prices, per 10,000 working adults: a
pop buys value / base price units of a good (Paradox wiki, "Buy packages").
pop_needs_curves.py's expenditure table and plot and the player guide's
spending chart once multiplied each value by its default good's base price
again, which overstated Art (fine_art, 200) and Tourism (100) about fourfold.

Run: python3 -m unittest test_pop_spending_valuation -v
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

import player_guide_figures as figures  # noqa: E402
from pop_needs_curves import _extract_buy_packages, _package_cost  # noqa: E402

BUY_PACKAGES = ROOT / "common/buy_packages/00_buy_packages.txt"


class PackageParsing(unittest.TestCase):
    def test_comments_are_not_needs(self):
        text = (
            "wealth_1 = {\n\tpolitical_strength = 1\n"
            "\tgoods = { # Sum = 5\n\t\tpopneed_a = 2\n\t\tpopneed_b = 3 # note\n\t}\n}\n"
        )
        self.assertEqual(_extract_buy_packages(text), {1: {"popneed_a": 2, "popneed_b": 3}})

    def test_cost_is_the_sum_of_values(self):
        self.assertEqual(_package_cost({"popneed_a": 2, "popneed_b": 3}), 5)


class GuideChart(unittest.TestCase):
    def test_shares_follow_values_not_prices(self):
        packages = _extract_buy_packages(BUY_PACKAGES.read_text(encoding="utf-8-sig"))
        group_of = {need: name for name, _, members in figures.GROUPS for need in members}
        for wl in (30, 60, 100):
            spend = {}
            for popneed, value in packages[wl].items():
                group = group_of.get(popneed.replace("popneed_", ""))
                if group:
                    spend[group] = spend.get(group, 0) + value
            total = sum(spend.values())
            shares = figures.spending_shares([wl])[wl]
            for group, value in spend.items():
                self.assertAlmostEqual(shares[group], value / total, places=9, msg=(wl, group))


if __name__ == "__main__":
    unittest.main()
