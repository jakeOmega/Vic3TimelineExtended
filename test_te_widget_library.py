"""The shared column types for wide layouts (gui/te_widget_library.gui;
spec docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 9.4).

te_ui_columns_three and te_ui_columns_two: a horizontal row of fixed 520
columns, 30 apart, read down each column and then across, as the Census Data
window's Demographics tab lays them out (te_demog_browser_sections). Each
column is a block (column_1 … column_3) that a wide composer fills, after a
block (column_1_visible …) where it may gate the column, so a column whose
sections all hide closes up and the rest recentre. The properties are the
Census window's, so rebasing it onto the type keeps its widget tree.
"""
import os
import unittest

from gui_test_helpers import _children, _read, _type_body

REPO = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(REPO, "gui", "te_widget_library.gui")

ROW = {("direction", "horizontal"), ("spacing", "30"), ("parentanchor", "hcenter"), ("ignoreinvisible", "yes")}
COLUMN = {("direction", "vertical"), ("ignoreinvisible", "yes"), ("spacing", "10"),
          ("minimumsize", "{ 520 -1 }"), ("maximumsize", "{ 520 -1 }")}


class ColumnsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _read(LIBRARY)

    def _check(self, name, n):
        self.assertRegex(self.text, rf"(?m)^\ttype {name} = flowcontainer \{{", f"no type {name}")
        top = _children(_type_body(self.text, name))
        props = {(k, v) for kind, k, v in top if kind == "property"}
        self.assertEqual(props, ROW)
        self.assertNotIn("visible", {k for k, _ in props})    # an instance may gate the row
        columns = [text for kind, k, text in top if kind == "widget"]
        self.assertEqual([k for kind, k, _ in top if kind != "property"], ["flowcontainer"] * n)
        for i, column in enumerate(columns, 1):
            with self.subTest(type=name, column=i):
                items = _children(column)
                self.assertEqual({(k, v) for kind, k, v in items if kind == "property"}, COLUMN)
                # the gate's block first, so a visible lands on the column itself
                self.assertEqual([(kind, k) for kind, k, _ in items if kind != "property"],
                                 [("block", f"column_{i}_visible"), ("block", f"column_{i}")])

    def test_three_columns(self):
        self._check("te_ui_columns_three", 3)

    def test_two_columns(self):
        self._check("te_ui_columns_two", 2)

    def test_the_header_names_them(self):
        header = self.text[:self.text.index("types te_widget_library_types")]
        for name in ("te_ui_columns_three", "te_ui_columns_two"):
            self.assertIn(name, header)
        # an empty column keeps its 520, so two columns of content take the two-column type
        self.assertRegex(header, r"(?s)empty column.*te_ui_columns_two")


if __name__ == "__main__":
    unittest.main()
