"""The history charts: one registry entry per chart, drawn at two sizes (spec
docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md § 4.3).

te_history_chart (gui/journal_entry_widgets/te_history_chart.gui) is the chart
type. Its widths are blocks, so an instance can draw it at another size.
"""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
from gui_test_helpers import _close, _read, _strip_comments, _type_body  # noqa: E402

CHART_GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "te_history_chart.gui")


def _block_bodies(text, name):
    """The body of each `block "name" { … }` in text, in order."""
    return [text[m.end():_close(text, m.end() - 1)] for m in re.finditer(rf'block "{name}" \{{', text)]


def _unblocked(text, pattern):
    """Each line matching `pattern` that no `block "…" { … }` encloses."""
    out, stack = [], []
    for line in _strip_comments(text).split("\n"):
        if re.search(pattern, line) and not any(stack):
            out.append(line.strip())
        for ch in line:
            if ch == "{":
                stack.append(bool(re.search(r'\bblock "\w+" \{', line)))
            elif ch == "}":
                stack.pop()
    return out


class ChartTypeTest(unittest.TestCase):
    """The chart's own widths are blocks with today's values as their defaults,
    so the panel's charts draw as before and the viewer's can set them."""

    @classmethod
    def setUpClass(cls):
        cls.chart = _type_body(_read(CHART_GUI), "te_history_chart")

    def test_the_text_width_is_a_block_on_the_title_and_the_legend(self):
        self.assertEqual([b.strip() for b in _block_bodies(self.chart, "chart_text_width")],
                         ["max_width = 484", "max_width = 484"])
        for font in ("chart_title_font", "chart_legend_font"):
            box = self.chart[self.chart.rindex("textbox = {", 0, self.chart.index(f'block "{font}"')):]
            self.assertIn('block "chart_text_width"', box[:box.index(f'block "{font}"')], font)

    def test_the_empty_states_width_is_a_block(self):
        self.assertEqual([b.strip() for b in _block_bodies(self.chart, "empty_width")], ["max_width = 420"])
        box = self.chart[self.chart.rindex("textbox = {", 0, self.chart.index('block "empty_text"')):]
        self.assertIn('block "empty_width"', box)

    def test_no_other_literal_width_in_the_type(self):
        """Every pixel width or size the chart draws at is a block an instance
        can override: the text, the empty state, the frame (plot_size) and the
        bars (plot_layouts)."""
        self.assertEqual(_unblocked(self.chart, r"\b(max_width|size) = \{?\s*\d"), [])
        self.assertTrue(_block_bodies(self.chart, "plot_size"))
        self.assertTrue(_block_bodies(self.chart, "plot_layouts"))


if __name__ == "__main__":
    unittest.main()
