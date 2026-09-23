"""Structural tests for the covert operations widget's per-row stand-down.

Stand-down is always shown on its row: there is no panel-level arming toggle.
Each row carries one stand-down instance per operation type, and only
the one whose tag matches the row's container may be visible.
"""

import re
import unittest
from pathlib import Path

from test_covert_op_registry import TYPES

ROOT = Path(__file__).resolve().parent
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
LOC_DIR = ROOT / "localization/english"


class StandDownTests(unittest.TestCase):
    def test_no_arming_toggle(self):
        gui = WIDGET.read_text(encoding="utf-8-sig")
        self.assertNotIn("covert_stand_down_armed", gui)
        self.assertNotIn("je_iw_stand_down_toggle", gui)
        loc = "".join(p.read_text(encoding="utf-8-sig") for p in LOC_DIR.rglob("*.yml"))
        self.assertNotRegex(loc, r"(?m)^ je_iw_stand_down_toggle")

    def test_each_type_visible_on_its_own_tag_only(self):
        gui = WIDGET.read_text(encoding="utf-8-sig")
        # Instances (not the type definition): `covert_op_stand_down_button = {`
        # indented under the row, each up to the next instance or the row's end.
        starts = [m.start() for m in re.finditer(r"(?m)^\t\tcovert_op_stand_down_button = \{", gui)]
        self.assertEqual(len(starts), len(TYPES))
        blocks = [gui[a:b] for a, b in zip(starts, starts[1:] + [gui.index("\n\t}\n", starts[-1])])]
        for t, block in zip(TYPES, blocks):
            self.assertIn("covert_stand_down_%s_sgui" % t, block)
            self.assertIn("visible = \"[ScriptContainer.HasTag('iw_op_%s')]\"" % t, block)


if __name__ == "__main__":
    unittest.main()
