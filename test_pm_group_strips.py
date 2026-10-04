"""Every strip of production-method groups in the mod's GUI scrolls sideways.

The mod's buildings carry up to seven visible PM groups (the discoverable
mines; the automotive industry six), where vanilla's carry at most four.
Vanilla lays the groups out in a fixed-width row (a `fixedgridbox` in the
building browser's type rows and the construction panel, a plain
`flowcontainer` in the goods-by-state cards), so from the fifth group on they
ran under the row's action buttons. Each strip is therefore a horizontal
`flowcontainer` in the `scrollwidget` of a capped `scrollarea`, as
`condensed_building_information_pms` (building_details_panel.gui) is. The 1.13
re-merge once dropped this wrapper from production_methods.gui
(docs/guides/gui_modding_guide.md, gotcha #38); this test fails if a re-merge
drops it again.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui")
STRIP = re.compile(r'datamodel = "\[[^"\]]*ProductionMethodGroups\]"')
# The key before an opening brace: `scrollarea = {`, `blockoverride "x" {`.
OPENER = re.compile(r"([\w:]+)\s*(?:\"[^\"]*\"\s*)?=?\s*$")


def _strip_comments(text):
    """The text with `# ...` comments blanked, keeping a quoted `#` (as in
    `raw_text = "#bold ...#!"`) and every offset unchanged."""
    out = []
    in_string = in_comment = False
    for ch in text:
        if in_comment:
            if ch == "\n":
                in_comment = False
                out.append(ch)
            else:
                out.append(" ")
            continue
        if ch == '"':
            in_string = not in_string
        elif ch == "#" and not in_string:
            in_comment = True
            out.append(" ")
            continue
        elif ch == "\n":
            in_string = False
        out.append(ch)
    return "".join(out)


def _enclosing_blocks(text, pos):
    """[(name, open_index)] of the blocks around `pos`, innermost last."""
    stack = []
    for i, ch in enumerate(text[:pos]):
        if ch == "{":
            m = OPENER.search(text[max(0, i - 200):i])
            stack.append((m.group(1) if m else "", i))
        elif ch == "}":
            stack.pop()
    return stack


def _strips():
    """One dict per PM-group strip in gui/*.gui."""
    found = []
    for fn in sorted(os.listdir(GUI)):
        if not fn.endswith(".gui"):
            continue
        with open(os.path.join(GUI, fn), encoding="utf-8-sig") as f:
            text = _strip_comments(f.read())
        for m in STRIP.finditer(text):
            chain = _enclosing_blocks(text, m.start())
            strip = {
                "where": f"{fn}:{text.count(chr(10), 0, m.start()) + 1}",
                "chain": [name for name, _ in chain],
                "container": text[chain[-1][1]:text.index("item", m.end())],
                "scrollarea": None,
            }
            if len(chain) >= 3 and chain[-3][0] == "scrollarea":
                start = chain[-3][1]
                strip["scrollarea"] = text[start:text.index("scrollwidget", start)]
            found.append(strip)
    return found


class PmGroupStrips(unittest.TestCase):
    def test_strips_found(self):
        # production_methods.gui (3), building_browser_panel.gui,
        # building_details_panel.gui and goods_state_panel.gui (1 each).
        self.assertGreaterEqual(len(_strips()), 6)

    def test_every_strip_is_a_flowcontainer_in_a_scrollarea(self):
        for strip in _strips():
            with self.subTest(strip["where"]):
                self.assertEqual(
                    strip["chain"][-3:], ["scrollarea", "scrollwidget", "flowcontainer"],
                    f"{strip['where']}: a PM-group strip must be a flowcontainer in "
                    "a scrollarea's scrollwidget; see this file's docstring")

    def test_every_strip_runs_horizontally(self):
        for strip in _strips():
            with self.subTest(strip["where"]):
                self.assertNotIn("direction = vertical", strip["container"])

    def test_every_scrollarea_is_capped_and_scrolls_sideways(self):
        for strip in _strips():
            body = strip["scrollarea"]
            if body is None:
                continue  # the chain test reports it
            with self.subTest(strip["where"]):
                self.assertRegex(body, r"maximumsize = \{ \d+ -1 \}")
                self.assertIn("autoresizescrollarea = yes", body)
                self.assertIn("scrollbarpolicy_horizontal = as_needed", body)
                self.assertIn("using = horizontal_scrollbar", body)
                self.assertIn("using = vertical_scrollbar", body)


if __name__ == "__main__":
    unittest.main()
