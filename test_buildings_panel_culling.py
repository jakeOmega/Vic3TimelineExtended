"""The Buildings panel's rows are left out of a frame while they are scrolled out of view.

The sidebar's Buildings panel (`compact_building_browser_panel`) lists a row per building type the country has, 201
in the USA of the 2050 save, in a `flowcontainer`, and the engine works out every child of a flowcontainer every
frame, seen or not. Each row asks for its productivity span, its buttons' states and, per production method group,
whether all its buildings share a method; the mod's strip of groups is a flowcontainer too (test_pm_group_strips.py),
where vanilla's was a `fixedgridbox`, whose items out of view the engine skips. With the panel open the 2050 game
drew a frame in 341 ms. So the fixed-size top of each row sits in a one-item fixedgridbox, as does the header of each
type in the Building Registry, and the panel's list updates at most ten times a second, as the Registry's does: 18 ms
(docs/audits/buildings_panel_performance.md). A vanilla re-merge that drops any of it fails here.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
ONE_ITEM = re.compile(r"datamodel = \"\[DataModelFirst\([^\"]*AccessProductionMethodGroups, '\(int32\)1'\)\]\"")


def _read(name):
    with open(os.path.join(REPO, "gui", name), encoding="utf-8-sig") as f:
        return f.read()


def _block(text, start):
    """The text of the block whose header begins at `start`, braces matched (quotes and # comments skipped)."""
    i, depth = text.index("{", start), 0
    while True:
        c = text[i]
        if c == '"':
            i = text.index('"', i + 1)
        elif c == "#":
            i = text.index("\n", i)
            continue
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1


def _type(text, name):
    m = re.search(r"\btype %s = " % re.escape(name), text)
    assert m, "type %s not found" % name
    return _block(text, m.start())


def _one_item_grids(block):
    """Each `fixedgridbox = { ... }` in the block whose datamodel is one production method group."""
    out = []
    for m in re.finditer(r"\bfixedgridbox = \{", block):
        grid = _block(block, m.start())
        head = grid[:grid.index("item = {")] if "item = {" in grid else grid
        if ONE_ITEM.search(head):
            out.append(grid)
    return out


class BuildingsPanelCulling(unittest.TestCase):
    def test_compact_row_top_is_culled(self):
        row = _type(_read("production_methods.gui"), "buildings_production_method_item")
        grids = _one_item_grids(row)
        self.assertEqual(len(grids), 1, "the row's top item must sit in one one-item fixedgridbox")
        for part in ("section_header_button", "AccessProductionMethodGroups]", "building_type_nationalize_button",
                     "GetProductivitySpanDesc"):
            self.assertIn(part, grids[0], "%s must be inside the culled top item" % part)
        self.assertNotIn("expanded_list", grids[0], "the expanded list varies in height; it stays outside")

    def test_registry_type_header_is_culled(self):
        item = _type(_read("building_browser_panel.gui"), "building_browser_building_type_item")
        grids = _one_item_grids(item)
        self.assertEqual(len(grids), 1, "the type's header row must sit in one one-item fixedgridbox")
        for part in ("section_header_button", "AccessProductionMethodGroups]", "GetTotalFilteredSizeDesc"):
            self.assertIn(part, grids[0], "%s must be inside the culled header" % part)
        self.assertNotIn("BuildingBrowserBuildingTypeItem.GetBuildings]", grids[0],
                         "the type's buildings are their own fixedgridbox, under the header")

    def test_compact_list_updates_at_most_ten_times_a_second(self):
        panel = _type(_read("building_browser_panel.gui"), "compact_building_browser_panel")
        content = _block(panel, panel.index('blockoverride "scrollarea_content"'))
        first = _block(content, content.index("flowcontainer = {"))
        self.assertRegex(first[:first.index("direction")], r"max_update_rate = 10\b")

    def test_hidden_list_asks_for_one_building(self):
        panel = _type(_read("building_browser_panel.gui"), "compact_building_browser_panel")
        self.assertIn("datamodel = \"[DataModelFirst(BuildingBrowserPanel.GetSortedAndFilteredBuildings, '(int32)1')]\"",
                      panel, "the list that fills the rows asks for its first building, not one widget each")
        self.assertNotIn('datamodel = "[BuildingBrowserPanel.GetSortedAndFilteredBuildings]"', panel)


if __name__ == "__main__":
    unittest.main()
