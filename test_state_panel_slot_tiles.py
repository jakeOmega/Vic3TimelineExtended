"""The state view's Solar Collector and Antimatter tiles, and the tourism card's footer (seen in game, 2026-11-24).

- A slot pool is a sum of fractions (a part-staffed level gives part of its slots), and `|0` cuts toward zero: a
  country 0.9 of a slot over its pool read a green "Available -0". The figure now follows its sign: green whole
  slots from 1, a plain 0 below that, and a shortfall in red with one decimal.
- The card's footer prints every tourism modifier's total ("+415.70%"), which the row type's 60 px value cell cut to
  "+415.7 ...".
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATES = (ROOT / "gui" / "states_panel.gui").read_text(encoding="utf-8-sig")
WIDGETS = (ROOT / "gui" / "te_state_panel_widgets.gui").read_text(encoding="utf-8-sig")
LOC = {}
for _path in sorted((ROOT / "localization" / "english").rglob("*.yml")):
    for _line in _path.read_text(encoding="utf-8-sig").splitlines():
        _m = re.match(r'\s*([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$', _line)
        if _m:
            LOC[_m.group(1)] = _m.group(2)

TILES = (("TE_STATE_SOLAR_AVAILABLE", "solar_receiver_slots_remaining"),
         ("TE_STATE_ANTIMATTER_AVAILABLE", "antimatter_sub_building_slots_remaining"))


class SlotTileTest(unittest.TestCase):
    def test_each_tile_reads_its_figure_through_the_key(self):
        for key, value in TILES:
            with self.subTest(key=key):
                self.assertIn('text = "%s"' % key, STATES)
                self.assertNotIn("ScriptValue('%s')|0]" % value, STATES, "the bare |0 printed a shortfall as -0")

    def test_the_figure_follows_its_sign(self):
        for key, value in TILES:
            with self.subTest(key=key):
                read = "State.GetOwner.MakeScope.ScriptValue('%s')" % value
                self.assertEqual(LOC[key],
                                 "[SelectLocalization( LessThan_CFixedPoint( %s, '(CFixedPoint)-0.05' ), '%s_SHORT', "
                                 "SelectLocalization( LessThan_CFixedPoint( %s, '(CFixedPoint)1' ), '%s_NONE', "
                                 "'%s_FREE' ) )]" % (read, key, read, key, key))
                self.assertEqual(LOC[key + "_FREE"], "#G [%s|0]#!" % read, "whole slots: |0 cuts 3.9 to the 3 usable")
                self.assertEqual(LOC[key + "_NONE"], "#v 0#!")
                self.assertEqual(LOC[key + "_SHORT"], "#R [%s|1]#!" % read, "one decimal: |0 would print -0.9 as -0")


class TourismFooterTest(unittest.TestCase):
    def test_both_totals_get_a_hundred_px(self):
        for modifier in ("goods_output_tourism_mult", "building_tourism_industry_throughput_add"):
            with self.subTest(modifier=modifier):
                start = WIDGETS.index("GetValueWithBreakdownFor('%s')" % modifier)
                row = WIDGETS[start:WIDGETS.index("\n\t\t\t\t}\n", start)]
                self.assertIn("size = { 146 24 }", row)
                self.assertIn("max_width = 146", row)
                self.assertIn("size = { 100 24 }", row)
                self.assertIn("max_width = 100", row)

    def test_the_row_is_still_the_cards_250_column(self):
        self.assertEqual(146 + 4 + 100, 186 + 4 + 60)       # label + the row's spacing + value, as te_state_wide_row


if __name__ == "__main__":
    unittest.main()
