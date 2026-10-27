"""The Seabed panel, layout A (seabed claims spec § 3): every fixed-width
cell fits its longest text at its font (§ 3.7: the overflow is what started
this), and the panel's structure: the four sections in order, the rivals
through the leaderboard's scripted GUI, flags through a stored capital,
collapse flags named for their default, and every key defined.

The width budget is test_banking_layout.py's (the style guide's rule 3): GUI
units per character for each font, plus 10%, read from this file's own
te_seabed_fontsize_* templates.
"""
import os
import re
import unittest

from test_banking_layout import MARGIN, _all_loc, _block_from, _custom_options, _read, _type_body

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "te_seabed_widgets.gui")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_global_commons_seabed_sguis.txt")
BASINS = ("pacific", "atlantic", "indian", "arctic", "southern")
# The longest a number printed in a cell can be: counts reach four digits (the
# pools sum to 1,000), the readout five ("+99999" navy), a year four.
NUMBER = "9999"
YEAR = "1972"
READOUT = "99999"

_SIZES = {m.group(1): int(m.group(2)) for m in re.finditer(
    r"template te_seabed_fontsize_(\w+) \{\s*fontsize = (\d+)", _read(GUI))}
UNITS = {"row": 10.0 / 20 * _SIZES["row"], "heading": 10.0 / 20 * _SIZES["heading"],
         "overview": 8.6 / 16 * _SIZES["overview"]}


class _Budget:
    @classmethod
    def setUpClass(cls):
        cls.loc = _all_loc()
        cls.custom = _custom_options()
        cls.gui = _read(GUI)

    def shown(self, key, number=NUMBER, depth=0):
        """The widest text the key can show: splices and concepts resolved,
        formatting stripped, a customizable localization at its longest
        option, any other data read at the cell's longest number."""
        v = self.loc.get(key)
        self.assertIsNotNone(v, key)
        self.assertLess(depth, 6, key)
        v = re.sub(r"\$(\w+)\$", lambda m: self.shown(m.group(1), number, depth + 1), v)
        v = re.sub(r"\[(concept_\w+)\]", lambda m: self.shown(m.group(1), number, depth + 1), v)

        def custom(m):
            return max((self.shown(k, number, depth + 1) for k in self.custom[m.group(1)]), key=len)
        v = re.sub(r"\[[^\[\]]*GetCustom\('(\w+)'\)[^\[\]]*\]", custom, v)
        v = re.sub(r"\[[^\[\]]*\]", number, v)
        v = re.sub(r"#[A-Za-z_]+(?:;\S*)? ", "", v).replace("#!", "")
        v = re.sub(r"@\w+!", "", v)
        return v.replace("\\n", "")

    def fits(self, key, cell, number=NUMBER):
        width, font = cell
        text = self.shown(key, number)
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, width, f"{key} shows {text!r}: {need:.0f} units in a {width} {font} cell")

    def box(self, text, anchor):
        """(max_width, font) of the textbox around `anchor`, from the markup."""
        at = text.index(anchor)
        start = text.rindex("textbox = {", 0, at)
        tb = _block_from(text, start + len("textbox = "))
        self.assertIn(anchor, tb)
        width = int(re.search(r"max_width = (\d+)", tb).group(1))
        font = re.search(r"using = te_seabed_fontsize_(\w+)", tb).group(1)
        return width, font

    def type_box(self, typ, block):
        return self.box(_type_body(self.gui, typ), 'block "%s"' % block)


class SeabedWidthTest(_Budget, unittest.TestCase):
    """Every fixed-width seabed cell fits its longest text (spec § 3.7)."""

    def test_policy_buttons(self):
        cell = self.type_box("te_seabed_policy_button", "policy_text")
        for i in (1, 2, 3):
            with self.subTest(policy=i):
                self.assertIn(f'text = "te_seabed_policy_short_{i}"', self.gui)
                self.fits(f"te_seabed_policy_short_{i}", cell)

    def test_overview_cells(self):
        cell = _type_body(self.gui, "te_seabed_ov_cell")
        x = int(re.search(r"position = \{ (\d+) 2 \}", cell).group(1))
        width = int(re.search(r"size = \{ (\d+) 70 \}", cell).group(1))
        column = width - x - 6
        caption = self.type_box("te_seabed_ov_cell", "caption")
        self.assertEqual(caption, (column, "overview"))
        for typ in ("te_seabed_ov_word", "te_seabed_ov_fig"):
            body = _type_body(self.gui, typ)
            self.assertIn("using = te_seabed_fontsize_overview", body)
            self.assertIn(f"max_width = {column}", body)
            self.assertIn(f"position = {{ {x} ", body)
        keys = sorted(set(re.findall(r'"(te_seabed_ov_\w+_(?:cap|word|fig)\w*)"', self.gui)))
        self.assertEqual(len([k for k in keys if k.endswith("_cap")]), 6)
        for key in keys:
            with self.subTest(key=key):
                self.fits(key, (column, "overview"), YEAR if "policy_fig" in key else NUMBER)

    def test_basin_columns(self):
        head = _type_body(self.gui, "te_seabed_basin_head")
        cells = {}
        for col in ("basin", "free", "pool", "weight", "next"):
            cells[col] = self.box(head, f'"te_seabed_col_{col}"')
            with self.subTest(head=col):
                self.fits(f"te_seabed_col_{col}", cells[col])
        self.assertEqual(sum(w for w, _ in cells.values()), 480)
        row = _type_body(self.gui, "te_seabed_basin_row")
        name = self.box(row, 'block "basin_name"')
        for b in BASINS:
            with self.subTest(basin=b):
                self.fits(f"te_seabed_basin_{b}", name)
                self.fits(f"te_seabed_free_{b}", self.box(row, 'block "basin_free"'))
                self.fits(f"te_seabed_weight_pct_{b}", self.box(row, 'block "basin_weight"'), "100")
                self.fits(f"te_seabed_next_{b}", self.box(row, 'block "basin_next"'), READOUT)
        for key in ("te_seabed_next_full", "te_seabed_next_none"):
            self.fits(key, self.box(row, 'block "basin_next"'))
        self.assertEqual(self.box(row, 'block "basin_name"')[0] + 22, cells["basin"][0])

    def test_heading_and_as_of(self):
        body = _type_body(self.gui, "te_seabed_basins_panel")
        self.fits("te_seabed_basins_header", self.box(body, '"te_seabed_basins_header"'))
        cell = self.box(body, "'te_seabed_basins_asof'")
        for key in ("te_seabed_basins_asof", "te_seabed_basins_asof_old"):
            self.fits(key, cell, YEAR)

    def test_rival_rows(self):
        """The claimants sit in fixed columns under their heads (audit SEA-3):
        the name elides, its full form on the flag's hover (vanilla's tiny
        flag), and each figure fits its column. A rival with no stored capital
        keeps the scripted line, which wraps. Our row's button fits its label,
        and the row fits the 480 column."""
        cells = _type_body(self.gui, "te_seabed_rival_cells")
        boxes = [cells[m.start():] for m in re.finditer(r"textbox = \{", cells)]
        widths = [int(re.search(r"max_width = (\d+)", b).group(1)) for b in boxes]
        self.assertIn("elide = right", boxes[0])
        self.assertIn("tiny_flag", cells)
        spacing = int(re.search(r"spacing = (\d+)", cells).group(1))
        flag = int(re.search(r"size = \{ (\d+) 22 \}", cells).group(1))
        head = _type_body(self.gui, "te_seabed_rival_head")
        heads = [int(w) for w in re.findall(r"max_width = (\d+)", head)]
        # the heads end where the columns do
        self.assertEqual(heads, [flag + spacing + widths[0]] + [spacing + w for w in widths[1:]])
        button = self.type_box("te_seabed_claim_button", "claim_text")
        for key in ("te_seabed_relinquish_btn", "te_seabed_claim_again_btn"):
            self.fits(key, button)
        button_w = int(re.search(r"size = \{ (\d+) 26 \}", _type_body(self.gui, "te_seabed_claim_button")).group(1))
        self.assertLessEqual(8 + flag + spacing * 4 + sum(widths) + button_w, 480)
        for key, col in (("te_seabed_rival_col_name", 0), ("te_seabed_rival_col_mines", 1),
                         ("te_seabed_rival_col_claims", 2), ("te_seabed_rival_col_weight", 3)):
            self.fits(key, (heads[col], "row"))
        self.fits("te_seabed_rival_us_name", (widths[0], "row"))
        for col, figure in ((1, "9999"), (2, "9999"), (3, "100%")):
            self.assertLessEqual(len(figure) * UNITS["row"] * MARGIN, widths[col])
        fallback = _type_body(self.gui, "te_seabed_rival_row")
        line = fallback[fallback.rindex("textbox = {"):]
        self.assertIn("multiline = yes", line)
        self.assertNotIn("elide", line)


class SeabedPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)

    def test_four_sections_in_order(self):
        at = [self.gui.index(f"type te_seabed_{s}_panel = ") for s in ("overview", "policy", "basins", "how")]
        self.assertEqual(at, sorted(at))

    def test_rival_rows_use_the_leaderboard_sgui(self):
        self.assertIn("te_seabed_rival_row_sgui", self.gui)
        for i, b in enumerate(BASINS, 1):
            for n in range(1, 7):
                op = 10 * i + n
                self.assertEqual(self.gui.count(f"'(CFixedPoint){op}'"), 2, (b, n))   # visible and text

    def test_flags_go_through_the_capital(self):
        self.assertIn(".Var('te_seabed_rkcap_", self.gui)
        for b in BASINS:
            for n in range(1, 7):
                at = self.gui.index(f"Var('te_seabed_rkcap_{b}_{n}')")
                guard = self.gui.rindex("visible = ", 0, at)
                self.assertIn(f"te_seabed_rkcap_count_disp_{b}", self.gui[guard:at], (b, n))

    def test_rivals_collapse_flags_are_open_named(self):
        """Rule 7: a section that starts collapsed names its flag _open."""
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.gui))
        self.assertEqual(flags, {"te_seabed_how_open"} | {f"te_seabed_rivals_{b}_open" for b in BASINS})

    def test_type_sizes_are_the_templates(self):
        self.assertEqual(_SIZES, {"row": 17, "heading": 20, "overview": 16})
        self.assertNotRegex(self.gui, r"using = fontsize_")

    def test_the_build_in_hover_lists_states(self):
        sguis = _read(SGUIS)
        self.assertIn("te_seabed_build_in_sgui = {", sguis)
        self.assertIn("te_seabed_build_in_sgui", self.gui)

    def test_every_key_exists(self):
        loc = _all_loc()
        keys = set(re.findall(r'\b(?:text|tooltip) = "([A-Za-z]\w*)"', self.gui))
        keys |= set(re.findall(r"Localize\( '(\w+)' \)", self.gui))
        keys |= set(re.findall(r", '(te_seabed_\w+)'", self.gui))
        self.assertEqual(sorted(k for k in keys if k not in loc and not k.endswith("_sgui")), [])


if __name__ == "__main__":
    unittest.main()
