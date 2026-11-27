"""The ship construction box under the date reads the total, not what is in use.

Vanilla's box (`gui/timemanip.gui`, `text = "SHIP_CONSTRUCTION_VALUE"`) shows
`#v [Country.GetShipConstructionUsage|0]#!/[Country.GetShipConstruction|0]`. It is on screen all the time, and the
game works the usage out again after every tick. Measured on a 2050 game (docs/audits/late_game_performance_2050.md,
finding 5): about 7 s of every game week with the usage in the text, none that can be measured with the total alone.

So the mod overrides `SHIP_CONSTRUCTION_VALUE_WITHOUT_ICON`, the text the box resolves to, without the usage. The
figure "used/total" stays where it is read on request: the box's tooltip (vanilla's, worked out on hover) and the
Construction panel's Ships tab, which the mod's `production_methods.gui` points at a key of its own.
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
GUI = {path.name: path.read_text(encoding="utf-8-sig") for path in sorted((ROOT / "gui").rglob("*.gui"))}
USAGE = "GetShipConstructionUsage"
PANEL_KEY = "TE_SHIP_CONSTRUCTION_VALUE_PANEL"
USED_OF_TOTAL_KEY = "TE_SHIP_CONSTRUCTION_USED_OF_TOTAL"
# The used figure below and from 1,000 (#2093; test_construction_figures.py holds the switch).
USED_FIGURE_KEYS = {"TE_SHIP_CONSTRUCTION_USED_N", "TE_SHIP_CONSTRUCTION_USED_K"}


class ShipConstructionReadoutTest(unittest.TestCase):
    def test_the_box_under_the_date_reads_the_total_alone(self):
        text = LOC["SHIP_CONSTRUCTION_VALUE_WITHOUT_ICON"]
        self.assertNotIn(USAGE, text, "the usage is worked out after every tick while this text is on screen")
        self.assertEqual(text, "#v [Country.GetShipConstruction|0]#!")

    def test_the_ships_tab_keeps_used_of_total(self):
        panel = GUI["production_methods.gui"]
        self.assertIn(f'text = "{PANEL_KEY}"', panel)
        self.assertNotIn('text = "SHIP_CONSTRUCTION_VALUE"', panel,
                         "vanilla's key now reads the total alone; the tab would lose the figure in use")
        for key in USED_FIGURE_KEYS:
            self.assertIn(f"'{key}'", LOC[USED_OF_TOTAL_KEY], "used/total: the figure in use, then the total")
        self.assertIn("'TE_SHIP_CONSTRUCTION_TOTAL_N'", LOC[USED_OF_TOTAL_KEY])
        # Vanilla's SHIP_CONSTRUCTION_VALUE, with the mod's key in place of the one overridden.
        self.assertEqual(LOC[PANEL_KEY], "[SelectLocalization(Country.IsShipConstructionPaused, "
                                         f"'CONSTRUCTION_DURATION_PAUSED', '{USED_OF_TOTAL_KEY}')]")

    def test_only_the_ships_tab_shows_the_usage(self):
        """A second always-shown place for the usage would bring the cost back."""
        keys_with_usage = {key for key, value in LOC.items() if USAGE in value}
        self.assertEqual(keys_with_usage, {USED_OF_TOTAL_KEY} | USED_FIGURE_KEYS)
        for key in USED_FIGURE_KEYS:
            with self.subTest(spliced=key):
                self.assertEqual({k for k, value in LOC.items() if key in value and k != key}, {USED_OF_TOTAL_KEY})
        for name, text in GUI.items():
            with self.subTest(gui=name):
                self.assertNotIn(USAGE, text)
                self.assertNotIn(USED_OF_TOTAL_KEY, text)
                if name != "production_methods.gui":
                    self.assertNotIn(PANEL_KEY, text)


if __name__ == "__main__":
    unittest.main()
