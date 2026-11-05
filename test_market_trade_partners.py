"""The Market panel's Trade tab additions (the GUI and localization audit,
docs/audits/gui_audit/climate_reserve_market.md, MKT-1 to MKT-4): Top Trade
Partners is a datamodel over a list script builds, the additions' English is
in loc, the partner charts say their unit, and the table's text is set through
one template at the style guide's row size, with every cell's longest reading
held to its width (test_banking_layout.py's WidthBudgetTest is the model)."""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
MARKET = os.path.join(REPO, "gui", "market_panel.gui")
TOOLTIPS = os.path.join(REPO, "gui", "te_trade_partner_tooltips.gui")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "trade_partner_effects.txt")
VALUES = os.path.join(REPO, "common", "script_values", "gui_chart_script_values.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")
LIST = "MarketPanel.GetMarket.GetOwner.MakeScope.GetList('te_tp_top_markets')"
PAIR = ("GuiScope.SetRoot( MarketPanel.GetMarket.GetOwner.MakeScope ).AddScope( 'tp_partner_country', "
        "Country.MakeScope )")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _block_from(text, start):
    """The body of the brace block whose `{` is at or after `start`."""
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
    raise AssertionError("unbalanced braces")


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
        for m in re.finditer(r'^ ([\w.\-]+):\d* "(.*)"\s*$', _read(path), re.M):
            keys[m.group(1)] = m.group(2)
    return keys


def _te_trade_blocks():
    """The mod's three additions to the Trade tab: the value charts, and the
    partner charts with the table."""
    text = _read(MARKET)
    out = []
    for tag in ("### TE: Export/Import by Value", "### TE: Import/Export Partners charts"):
        at = text.index(tag)
        out.append(_block_from(text, at))
    return out


def _table():
    text = _read(MARKET)
    at = text.index("### TE: Top Trade Partners table")
    return _block_from(text, at)


class ListTest(unittest.TestCase):
    """MKT-1: one row, drawn per item of te_tp_top_markets, in place of five
    copied rows over fifteen rank variables."""

    def test_the_rows_are_a_datamodel_over_the_list(self):
        table = _table()
        self.assertIn(f'visible = "[Not( IsDataModelEmpty( {LIST} ) )]"', table)
        self.assertRegex(table, rf'datamodel = "\[{re.escape(LIST)}\]"\s*item = \{{\s*flowcontainer = \{{\s*'
                                r'margin = \{ 10 2 \}\s*datacontext = "\[Scope\.GetMarket\.GetOwner\]"')
        self.assertNotIn("Var('tp_", _read(MARKET))
        self.assertNotIn("gui_tp_count", _read(MARKET))
        for value in ("gui_tp_annual_trade", "gui_tp_trade_pct_gdp"):
            self.assertIn(f"{PAIR}.ScriptValue('{value}')", table, value)
        values = _read(VALUES)
        self.assertIn("scope:tp_partner_country", _block_from(values, values.index("gui_tp_annual_trade = {")))
        self.assertIn("value = gui_tp_annual_trade", _block_from(values, values.index("gui_tp_trade_pct_gdp = {")))

    def test_script_builds_the_list_largest_first(self):
        effects = _read(EFFECTS)
        body = _block_from(effects, effects.index("update_market_trade_partners = {"))
        self.assertRegex(body, r"if = \{\s*limit = \{ has_variable_list = te_tp_top_markets \}\s*"
                               r"clear_variable_list = te_tp_top_markets\s*\}")
        self.assertRegex(body, r"ordered_market = \{\s*limit = \{\s*NOT = \{ this = scope:tp_current_market \}\s*"
                               r"gui_trade_with_market_owner > 0\s*\}\s*order_by = gui_trade_with_market_owner\s*"
                               r"max = 5\s*check_range_bounds = no\s*save_temporary_scope_as = tp_iter_mkt\s*"
                               r"scope:tp_market_owner = \{\s*add_to_variable_list = \{ name = te_tp_top_markets "
                               r"target = scope:tp_iter_mkt \}")
        self.assertNotIn("store_trade_partner_data", effects)
        self.assertNotRegex(effects, r"set_variable = \{ name = tp_")
        # Older saves' rank variables are dropped, each only if it is there.
        drop = _block_from(effects, effects.index("te_tp_drop_rank_variables = {"))
        for n in range(1, 6):
            for f in ("tc", "total", "gdp_pct"):
                self.assertRegex(drop, rf"limit = \{{ has_variable = tp_{n}_{f} \}}\s*remove_variable = tp_{n}_{f}")


class LocTest(unittest.TestCase):
    """MKT-3: none of the additions' words is hard-coded English."""

    def test_no_english_raw_text(self):
        for block in _te_trade_blocks() + [_read(TOOLTIPS)]:
            for m in re.finditer(r'raw_(?:text|tooltip) = "([^"]*)"', block):
                words = re.sub(r"\[[^\]]*\]|@\w+!|#\w+ ?|#!", "", m.group(1))
                self.assertNotRegex(words, r"[A-Za-z]{2,}", m.group(0))

    def test_every_key_exists(self):
        loc = _loc()
        for block in _te_trade_blocks() + [_read(TOOLTIPS)]:
            for key in re.findall(r'(?:text|tooltip) = "([A-Za-z]\w+)"', block):
                self.assertIn(key, loc, key)

    def test_the_partner_charts_say_their_unit(self):
        """MKT-2: the partner charts count units, not money, so they say so,
        in the heading's hover. The legend row is the flag and the figure
        only: vanilla's compact_chart slot has no room for a unit, and
        "units/wk" ran past it (play-test, 2026-10-28)."""
        loc = _loc()
        for d, value in (("export", "gui_exports_to_target"), ("import", "gui_imports_from_target")):
            self.assertIn(value, loc[f"te_market_{d}_partner_units"])
            self.assertTrue(loc[f"te_market_{d}_partner_units"].endswith(f"ScriptValue('{value}')|v0]"))
            self.assertIn("units a week", loc[f"te_market_{d}_partners_tt"])
            self.assertIn("by value", loc[f"te_market_{d}_partners_tt"])

    def test_the_hover_opens_with_the_tables_figure(self):
        """MKT-2: the partner hover reconciles with the row: its yearly figure
        at base prices first, then the weekly breakdown at market prices."""
        loc = _loc()
        self.assertIn("ScriptValue('gui_tp_annual_trade')", loc["te_market_tp_tt_year"])
        tips = _read(TOOLTIPS)
        self.assertLess(tips.index('text = "te_market_tp_tt_year"'), tips.index('text = "te_market_tp_tt_per_week"'))
        self.assertNotIn("Hover a figure", loc["TP_TRADE_TOOLTIP"])


# The serif row face at 17, scaled from the measured 10 units a character at 20
# (gui_style_guide.md rule 3), plus 10%; a @texticon! is about two characters.
SIZE = int(re.search(r"template te_tp_fontsize_row \{\s*fontsize = (\d+)", _read(TOOLTIPS)).group(1))
UNITS = 10.0 / 20 * SIZE
MARGIN = 1.1


class WidthBudgetTest(unittest.TestCase):
    """MKT-4: the table's cells at the row size, each holding its longest
    reading; every text names the template."""

    def setUp(self):
        self.table = _table()
        self.widths = [int(w) for w in re.findall(r"minimumsize = \{ (\d+) -1 \}\s*maximumsize = \{ \d+ -1 \}",
                                                  self.table)]

    def fits(self, text, width):
        need = len(text) * UNITS * MARGIN
        self.assertLessEqual(need, width, f"{text!r}: {need:.0f} > {width}")

    def test_the_cells_are_named_and_fill_the_panel(self):
        self.assertEqual(SIZE, 17)
        self.assertNotIn("fontsize = 13", self.table)
        # the three headings, the name button and the two figures
        self.assertEqual(len(re.findall(r"using = te_tp_fontsize_row", self.table)), 6)
        # heads, then the row's two figure cells; the name cell is a 324 widget
        self.assertEqual(self.widths, [324, 110, 100, 110, 100])
        self.assertIn("size = { 324 24 }", self.table)
        self.assertEqual(324 + 110 + 100 + 2 * 10, int(re.search(r"@panel_width_plus_14 = (\d+)",
                                                                  _read(MARKET)).group(1)))

    def test_the_longest_readings_fit(self):
        self.fits("Market", 324)            # vanilla's concept_market
        self.fits("Trade / yr", 110)
        self.fits("% of GDP", 100)
        self.fits("XX999.9M", 110)          # @money! and a yearly figure
        self.fits("100.0%", 100)

    def test_the_figure_with_a_hover_is_plain_and_the_other_has_none(self):
        # Style guide rule 3 (owner, 2026-10-30): a figure's hover is not underlined.
        row = self.table[self.table.index("item = {"):]
        trade = row[row.index("gui_tp_annual_trade"):]
        self.assertIn("tooltip", trade[:600])
        self.assertNotIn("#tooltippable", trade[:600])
        gdp = row[row.index("gui_tp_trade_pct_gdp"):]
        self.assertNotIn("tooltip", gdp[:400])


if __name__ == "__main__":
    unittest.main()
