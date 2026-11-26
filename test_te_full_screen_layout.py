"""The Timeline Extended window's full-screen layouts, every tab at once
(spec docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 7,
the frame rework of 2026-11-24). Each system's own layout test holds its
composer's columns and gates against its narrow layout
(gui_test_helpers.assert_wide_matches_narrow); these hold the rules every
composer shares, read from the window's registry (gen_te_systems_window.TABS):

- the columns are a fixed 520, 30 apart, so a column's sections can't widen it;
- each composer is one row of those columns;
- every section the side panel draws is drawn once full screen, and nothing
  twice;
- no bar, box or row a composer draws is wider than its column, so two
  columns' section headings stand 30 apart instead of meeting across the
  gutter (Nation's and the Space Race milestones' headings, vanilla's 554
  default_header, take their column's 520 through a block the composer fills).
"""
import collections
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import gui_test_helpers as h  # noqa: E402
from scripts.generators import gen_te_systems_window as gen  # noqa: E402

COLUMN = 520
GUTTER = 30
# What the full-screen layout draws that the side panel's doesn't, each with
# why (each system's own test holds it: assert_wide_matches_narrow's `split`
# or `extra`).
WIDE_ONLY = {
    # Solar System Colonization's Colonies and Fleets tabs, in columns of their
    # own full screen (owner, 2026-11-26), inside the milestone's frame behind
    # tab buttons in the side panel
    "te_sr_window_solar_colonization_colonies": "space_race",
    "te_sr_window_solar_colonization_fleets": "space_race",
    # another country's copy of column 3's taboo and Nuclear Powers, in column
    # 2 for National Info, where column 3 (the player's own) closes up
    "te_nuclear_world_column": "nuclear_weapons",
}
# A narrow layout's composer not named *_sections, which the full-screen
# composer splits into its sections (Budget Breakdown's income and expenses).
COMPOSERS = {"te_budget_breakdown_panel"}


class _Composers:
    """What the walk expands: a *_sections type, or one of COMPOSERS."""

    def __contains__(self, name):
        return name.endswith("_sections") or name in COMPOSERS
# A size over the column's width that is not drawn in the column: none today.
# A tooltip widget's width, if one comes, belongs here with its reason.
NOT_IN_COLUMN: set[tuple[str, str]] = set()
HEADER_TYPES = ("default_header", "default_header_2texts")


def _sections(test, walk_body):
    walk = h._Walk(test, "layout", h._all_gui(), _Composers())
    walk_body(walk)
    return walk


class ColumnTypeTest(unittest.TestCase):
    def test_the_columns_are_520_and_30_apart(self):
        text = h._all_gui()
        for name, n in h.COLUMN_TYPES.items():
            with self.subTest(type=name):
                body = h._type_body(text, name)
                props = {k: v for kind, k, v in h._children(body) if kind == "property"}
                self.assertEqual((props.get("direction"), props.get("spacing"), props.get("parentanchor")),
                                 ("horizontal", str(GUTTER), "hcenter"))
                columns = [inner for kind, k, inner in h._children(body) if kind == "widget"]
                self.assertEqual(len(columns), n)
                for i, column in enumerate(columns, 1):
                    own = {k: v for kind, k, v in h._children(column) if kind == "property"}
                    self.assertEqual((own.get("minimumsize"), own.get("maximumsize")),
                                     (f"{{ {COLUMN} -1 }}", f"{{ {COLUMN} -1 }}"), f"column {i}")
                    self.assertEqual(own.get("ignoreinvisible"), "yes")
                    # a column that may be empty closes up on its own visible, then the row is centred without it
                    self.assertIn(f'block "column_{i}_visible"', column)
        # three columns are the frame: the title's width and the window's column
        self.assertEqual(gen.WIDE_WIDTH, 3 * COLUMN + 2 * GUTTER)


class ComposerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = h._all_gui()

    def _rows(self, name):
        """The column rows a composer lays out: its own base, or the
        instances in it (the Census window's, under its pending line)."""
        m = re.search(rf"\btype {name} = (\w+) \{{", self.text)
        self.assertIsNotNone(m, name)
        if m.group(1) in h.COLUMN_TYPES:
            return [m.group(1)]
        return [k for k in re.findall(r"(?<![\w.])(\w+) = \{", h._type_body(self.text, name)) if k in h.COLUMN_TYPES]

    def test_every_composer_is_one_row_of_columns(self):
        for t in gen.TABS:
            with self.subTest(tab=t.key):
                self.assertEqual(len(self._rows(t.wide)), 1, f"{t.wide} lays its sections out on one row of columns")

    def test_every_section_drawn_once(self):
        """The full-screen layout draws each of the side panel's sections
        once, and nothing twice: a section left out of a composer would never
        show full screen."""
        for t in gen.TABS:
            if t.layout is None:
                continue
            with self.subTest(tab=t.key):
                block = h._find_block(h._type_body(self.text, t.body), t.layout)
                self.assertIsNotNone(block, f"{t.body} has no block {t.layout}")
                narrow = _sections(self, lambda w: w.body(block, ()))
                base = re.search(rf"\btype {t.wide} = (\w+) \{{", self.text).group(1)
                if base in h.COLUMN_TYPES:
                    wide = _sections(self, lambda w: w.columns_of(base, h._type_body(self.text, t.wide), ()))
                else:
                    wide = _sections(self, lambda w: w.body(h._type_body(self.text, t.wide), ()))
                counts = collections.Counter(s for s, _, _ in wide.sections)
                self.assertEqual([s for s, n in counts.items() if n > 1], [], "drawn twice")
                narrow_names = {s for s, _, _ in narrow.sections}
                self.assertEqual(sorted(narrow_names - set(counts)), [], "drawn in the side panel only")
                only = {s for s, key in WIDE_ONLY.items() if key == t.key}
                self.assertEqual(sorted(set(counts) - narrow_names - only), [], "drawn full screen only")
                self.assertEqual(sorted(only - set(counts)), [], "WIDE_ONLY names what the layout no longer draws")


class WidthTest(unittest.TestCase):
    """Nothing a composer draws is wider than its column."""

    @classmethod
    def setUpClass(cls):
        cls.types = h.mod_types()
        cls.text = h._all_gui()

    def _filled(self, composer):
        """The size blocks the composer fills, and the widest width it gives
        each (a block it fills on several instances, Nation's headings, is
        held by its widest)."""
        body = h._type_body(self.text, composer)
        out = {}
        for name, w in re.findall(r'blockoverride "(\w+)" \{\s*size = \{ (\d+) \d+ \}\s*\}', body):
            out[name] = max(out.get(name, 0), int(w))
        return out

    @staticmethod
    def _block_around(body, pos):
        """The name of the innermost `block "x"` around pos, or None."""
        name = None
        for m in re.finditer(r'\bblock "(\w+)" \{', body):
            if m.start() > pos:
                break
            end = h._close(body, m.end() - 1)
            if end > pos:
                name = m.group(1)
        return name

    def test_no_bar_wider_than_its_column(self):
        for t in gen.TABS:
            filled = self._filled(t.wide)
            closure = h.type_closure([t.wide], self.types)
            with self.subTest(tab=t.key):
                for name in sorted(closure):
                    td = self.types[name]
                    for m in re.finditer(r"\b(size|minimumsize|maximumsize)\s*=\s*\{\s*(\d+)", td.body):
                        if int(m.group(2)) <= COLUMN or (name, m.group(1)) in NOT_IN_COLUMN:
                            continue
                        block = self._block_around(td.body, m.start())
                        self.assertIn(block, filled, f"{name} ({td.path}:{td.line}) draws {m.group(0)}...}}, wider "
                                                     f"than the column, and {t.wide} doesn't narrow it")
                        self.assertLessEqual(filled[block], COLUMN, f"{t.wide} fills {block} wider than its column")

    def test_every_header_has_a_width_of_its_own(self):
        """A vanilla header is 554 wide (default_header_properties' block
        "size", @panel_width_plus_14), so each one a composer draws sets its
        width: in place, or through a block the composer fills."""
        for t in gen.TABS:
            filled = self._filled(t.wide)
            closure = h.type_closure([t.wide], self.types)
            with self.subTest(tab=t.key):
                for name in sorted(closure):
                    td = self.types[name]
                    sites = [(m.end() - 1, m.group(1)) for m in re.finditer(rf"(?<![\w.])({'|'.join(HEADER_TYPES)}) = \{{",
                                                                            td.body)]
                    if td.base in HEADER_TYPES:
                        sites.append((None, td.base))
                    for brace, kind in sites:
                        header = td.body if brace is None else td.body[brace + 1:h._close(td.body, brace)]
                        size = [inner for k, n, inner in h._children(header) if k == "blockoverride" and n == "size"]
                        self.assertEqual(len(size), 1, f"{name}'s {kind} keeps vanilla's 554")
                        own = re.search(r"\bsize = \{ (\d+)", size[0]).group(1)
                        hook = re.search(r'\bblock "(\w+)"', size[0])
                        if hook:
                            self.assertIn(hook.group(1), filled, f"{t.wide} doesn't fill {name}'s {hook.group(1)}")
                            self.assertLessEqual(filled[hook.group(1)], COLUMN)
                        else:
                            self.assertLessEqual(int(own), COLUMN, f"{name}'s {kind}")


if __name__ == "__main__":
    unittest.main()
