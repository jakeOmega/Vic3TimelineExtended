"""The Construction panel's figures in a late economy (seen in game, 2026-11-24, a save of December 2032).

Under the construction market the points a country buys run to six and seven digits. Three things read wrong:

- The market's live read-out printed them in full with a decimal ("650050.9 a week", "1698482.3 / 1059423.5").
- Vanilla's points text, "used/speed", read "238189/654603" in the Construction panel's site row and in the HUD's
  construction box. The mod overrides `CONSTRUCTION_VALUE_WITHOUT_ICON` to abbreviate it from 1,000.
- In the site row that text ran into the week's cost beside it ("238189/6546£3703M"): the row has a third method
  group here, so less room than vanilla's. The cost now sits under the points.

`|K` alone abbreviates at every size (0 prints "0.00K"), so each figure is a key that switches at 1,000.

The Ships tab's row had the same overlap at five digits a side ("35015/5054£-1.37M", a game of February 2050,
#2093): its "used/total" switches at 1,000 the same way, and its cost sits under it as the site row's does.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOC = {}
for _path in sorted((ROOT / "localization" / "english").rglob("*.yml")):
    for _line in _path.read_text(encoding="utf-8-sig").splitlines():
        _m = re.match(r'\s*([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$', _line)
        if _m:
            LOC[_m.group(1)] = _m.group(2)
PM_GUI = (ROOT / "gui" / "production_methods.gui").read_text(encoding="utf-8-sig")

MARKET = {"PUBLIC_USE": "public_use", "BUDGET_TARGET": "budget_quantity_target", "PRIVATE_USE": "private_use",
          "SUPPLY": "market_supply", "DEMAND": "market_demand"}
ROWS = {"TE_CM_STAT_GOVERNMENT_VALUE": ("PUBLIC_USE",), "TE_CM_STAT_BUDGET_VALUE": ("BUDGET_TARGET",),
        "TE_CM_STAT_PRIVATE_VALUE": ("PRIVATE_USE",), "TE_CM_STAT_MARKET_VALUE": ("SUPPLY", "DEMAND")}


class MarketReadOutTest(unittest.TestCase):
    def test_each_figure_switches_at_a_thousand(self):
        for name, value in MARKET.items():
            with self.subTest(name=name):
                read = f"GetPlayer.MakeScope.ScriptValue('te_construction_market_display_{value}')"
                self.assertEqual(LOC[f"TE_CM_FIG_{name}"],
                                 f"[SelectLocalization( LessThan_CFixedPoint( {read}, '(CFixedPoint)1000' ), "
                                 f"'TE_CM_FIG_{name}_N', 'TE_CM_FIG_{name}_K' )]")
                self.assertEqual(LOC[f"TE_CM_FIG_{name}_N"], f"#v [{read}|1]#!")
                self.assertEqual(LOC[f"TE_CM_FIG_{name}_K"], f"#v [{read}|K]#!")

    def test_the_rows_print_the_switched_figures(self):
        for row, names in ROWS.items():
            with self.subTest(row=row):
                for name in names:
                    self.assertIn(f"$TE_CM_FIG_{name}$", LOC[row])
                    self.assertNotIn(f"display_{MARKET[name]}')|1]", LOC[row], "the raw figure with its decimal")


class PointsTextTest(unittest.TestCase):
    def test_vanillas_points_text_is_abbreviated_from_a_thousand(self):
        text = LOC["CONSTRUCTION_VALUE_WITHOUT_ICON"]
        for part, read in (("USED", "Country.CalcUsedConstruction"), ("SPEED", "Country.CalcBaseConstructionSpeed")):
            self.assertIn(f"SelectLocalization( LessThan_CFixedPoint( {read}, '(CFixedPoint)1000' ), "
                          f"'TE_CONSTRUCTION_{part}_N', 'TE_CONSTRUCTION_{part}_K' )", text)
            self.assertEqual(LOC[f"TE_CONSTRUCTION_{part}_N"], f"[{read}|0]", "vanilla's own form below 1,000")
            self.assertEqual(LOC[f"TE_CONSTRUCTION_{part}_K"], f"[{read}|K]")
        self.assertTrue(text.startswith("#v ") and "#!/" in text, "vanilla's shape: the used figure bold, then /speed")


class SiteRowTest(unittest.TestCase):
    def test_the_cost_sits_under_the_points(self):
        start = PM_GUI.index("type construction_queue_sector_actions = hbox {")
        row = PM_GUI[start:PM_GUI.index("### expand", start)]
        points = row.index('name = "construction_points"')
        cost = row.index("GetPlayer.GetConstructionGoodsExpenses|D-]")
        pause = row.index('name = "pause_construction"')
        self.assertLess(points, cost)
        self.assertLess(cost, pause)
        between = row[:points]
        self.assertRegex(between, r"flowcontainer = \{\s+direction = vertical\s+parentanchor = center",
                         "the points and the cost share one vertical flow")
        self.assertEqual(row[cost:pause].count("widget = {"), 1, "the cost is in the first half, the button the second")
        self.assertIn("using = construction_goods_expense_tooltip_with_graph", row[cost:pause], "the cost keeps its hover")
        self.assertIn('tooltip = "CONSTRUCTION_SPEED_BASE_TOOLTIP"', row[points:cost], "the points keep theirs")


class ShipsRowTest(unittest.TestCase):
    def test_used_of_total_switches_at_a_thousand(self):
        text = LOC["TE_SHIP_CONSTRUCTION_USED_OF_TOTAL"]
        for part, read in (("USED", "Country.GetShipConstructionUsage"), ("TOTAL", "Country.GetShipConstruction")):
            with self.subTest(part=part):
                self.assertIn(f"SelectLocalization( LessThan_CFixedPoint( {read}, '(CFixedPoint)1000' ), "
                              f"'TE_SHIP_CONSTRUCTION_{part}_N', 'TE_SHIP_CONSTRUCTION_{part}_K' )", text)
                self.assertEqual(LOC[f"TE_SHIP_CONSTRUCTION_{part}_N"], f"[{read}|0]", "vanilla's own form below 1,000")
                self.assertEqual(LOC[f"TE_SHIP_CONSTRUCTION_{part}_K"], f"[{read}|K]")
        self.assertTrue(text.startswith("#v ") and "#!/" in text, "vanilla's shape: the used figure bold, then /total")
        self.assertIn("'TE_SHIP_CONSTRUCTION_USED_OF_TOTAL'", LOC["TE_SHIP_CONSTRUCTION_VALUE_PANEL"])

    def test_the_cost_sits_under_the_figure(self):
        start = PM_GUI.index("type ship_construction_sector_actions = hbox {")
        row = PM_GUI[start:PM_GUI.index("### expand", start)]
        points = row.index('name = "ship_construction_points"')
        figure = row.index('text = "TE_SHIP_CONSTRUCTION_VALUE_PANEL"')
        cost = row.index("Country.GetShipConstructionGoodsExpenses)|D+]")
        pause = row.index('tooltip = "SHIP_CONSTRUCTION_BUTTON_PAUSE_TOOLTIP"')
        self.assertLess(points, figure)
        self.assertLess(figure, cost)
        self.assertLess(cost, pause)
        self.assertRegex(row[:points], r"flowcontainer = \{\s+direction = vertical\s+parentanchor = center",
                         "the figure and the cost share one vertical flow")
        self.assertEqual(row[cost:pause].count("widget = {"), 1, "the cost is in the first half, the button the second")
        self.assertIn('tooltip = "SHIP_CONSTRUCTION_GOODS_EXPENSES_BREAKDOWN"', row[cost:pause], "the cost keeps its hover")
        self.assertIn('tooltip = "SHIP_CONSTRUCTION_SPEED_BASE_TOOLTIP"', row[points:figure], "the figure keeps its")
        self.assertNotIn("fontsize_large", row, "both in the body size, as in the site row")


if __name__ == "__main__":
    unittest.main()
