"""The Private Actors tab of the Timeline Extended window (gui/te_pa_widgets.gui;
plan Task 3, spec § 14): the tab's place (the economy strip's sixth, public in
National Info), its gates (the game rule: off the strip with the rule off), its
full-screen columns, the roster's rows and the firm detail, the posture
buttons and their scripted GUIs (te_pa_sguis.txt), the ledger, each fixed cell
against its longest text, and what a row's hovers may read.

The width budget is test_banking_layout.py's (the style guide's rule 3): GUI
units per character for each font, plus 10%, read from this file's own
te_pa_fontsize_* templates.

Run: python3 -m pytest test_private_actors_tab.py -q
"""
import os
import re
import unittest

from gui_test_helpers import assert_wide_matches_narrow
from scripts.generators import gen_te_systems_window as window_gen
from test_banking_layout import MARGIN, _all_loc, _block_from, _read, _type_body

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "te_pa_widgets.gui")
POPUPS = os.path.join(REPO, "gui", "te_popups.gui")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_pa_sguis.txt")
TAB_SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")
CORE_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_pa_core_effects.txt")
LEDGER_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_pa_ledger_effects.txt")
CORE_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "te_pa_core_triggers.txt")
CORE_VALUES = os.path.join(REPO, "common", "script_values", "te_pa_core_values.txt")

# The longest a printed figure can be: a count two digits, a currency (0 to
# 100) three, a share four ("100%"), money five ("99.9K").
NUMBER = "99"
CURRENCY = "100"
SHARE = "100%"
MONEY = "999.9M"
# The holdings a company holds (§ 4.4), each a strength te_pa_r_<h> on the row.
HOLDINGS = ("cartel", "reg", "press", "town", "lab", "found")
# The goals in code order (te_pa_goal 1-8).
GOALS = ("inputs", "market", "abroad", "law", "dominance", "labor", "tech", "survival")
# Task 2's posture codes and their ledger verbs (te_pa_set_posture).
POSTURES = {"favored": ("1", "14"), "tolerated": ("0", "15"), "restrained": ("-1", "16")}

_SIZES = {m.group(1): int(m.group(2)) for m in re.finditer(
    r"template te_pa_fontsize_(\w+) \{\s*fontsize = (\d+)", _read(GUI))}
UNITS = {"row": 10.0 / 20 * _SIZES["row"], "heading": 10.0 / 20 * _SIZES["heading"],
         "overview": 8.6 / 16 * _SIZES["overview"]}


def _txt_block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, f"no {name}"
    return _block_from(text, m.end() - 1)


def _no_comments(text):
    return re.sub(r"#[^\n]*", "", text)


class _Budget:
    @classmethod
    def setUpClass(cls):
        cls.loc = _all_loc()
        cls.gui = _read(GUI)

    def shown(self, key, number=NUMBER, depth=0):
        """The widest text the key can show: splices and concepts resolved,
        formatting stripped, any data read at the cell's longest figure."""
        v = self.loc.get(key)
        self.assertIsNotNone(v, key)
        self.assertLess(depth, 6, key)
        v = re.sub(r"\$(\w+)\$", lambda m: self.shown(m.group(1), number, depth + 1), v)
        v = re.sub(r"\[(concept_\w+)\]", lambda m: self.shown(m.group(1), number, depth + 1), v)
        v = re.sub(r"\[[^\[\]]*\]", number, v)
        v = re.sub(r"@\w+!", "£", v)
        v = re.sub(r"#[A-Za-z_]+(?:;\S*)? ", "", v).replace("#!", "")
        return v.replace("\\n", "")

    def fits(self, key, width, font, number=NUMBER):
        text = self.shown(key, number)
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, width, f"{key} shows {text!r}: {need:.0f} units in a {width} {font} cell")


class WidthTest(_Budget, unittest.TestCase):
    """Every fixed-width cell fits its longest text (style guide rule 3: no
    "..." on anything a player reads), and each row of cells sums to 480."""

    def test_type_sizes_are_the_templates(self):
        self.assertEqual(_SIZES, {"row": 17, "heading": 20, "overview": 16})
        self.assertNotRegex(self.gui, r"using = fontsize_")

    def test_overview_cells(self):
        cell = _type_body(self.gui, "te_pa_ov_cell")
        x = int(re.search(r"position = \{ (\d+) 2 \}", cell).group(1))
        width = int(re.search(r"size = \{ (\d+) 70 \}", cell).group(1))
        column = width - x - 6
        self.assertEqual(column, 154)
        self.assertEqual(cell.count("max_width = 154"), 2)
        self.assertIn("size = { 154 22 }", cell)
        keys = sorted(set(re.findall(r"['\"](te_pa_ov_\w+_(?:cap|word|fig)\w*)['\"]", self.gui)))
        self.assertEqual(len([k for k in keys if k.endswith("_cap")]), 4)
        for key in keys:
            if key == "te_pa_ov_top_fig":
                continue    # the firm's name, shrunk toward 12 before it elides (the type's comment)
            with self.subTest(key=key):
                number = SHARE if key == "te_pa_ov_top_word" else NUMBER
                self.fits(key, column, "overview", number)
        # the goal's short names, which the box's word prints (te_pa_ov_goal_short)
        for n in range(1, 9):
            with self.subTest(goal=n):
                self.fits(f"te_pa_goal_short_{n}", column, "overview")

    def test_the_firms_first_line(self):
        """Icon 40, 4, the name 248, 4, then the chips' slot (seven at 20 with 2 between) and the condition's 28:
        480."""
        row = _type_body(self.gui, "te_pa_firm_row")
        self.assertIn("size = { 480 44 }", row)
        self.assertIn("size = { 296 44 }", row)
        self.assertIn("size = { 40 40 }", row)
        self.assertIn("position = { 44 0 }", row)
        self.assertIn("maximumsize = { 248 44 }", row)
        self.assertIn("position = { 296 0 }", row)
        self.assertEqual(40 + 4 + 248 + 4, 296)
        chip = _type_body(self.gui, "te_pa_holding_chip")
        self.assertIn("size = { 20 20 }", chip)
        self.assertIn("spacing = 2", _type_body(self.gui, "te_pa_holding_chips"))
        self.assertLessEqual(296 + 7 * 20 + 6 * 2, 480 - 28)

    def test_executive_and_goal(self):
        cell = _type_body(self.gui, "te_pa_cell")
        self.assertIn("maximumsize = { 236 -1 }", cell)
        self.assertIn("multiline = yes", cell)     # a goal's name or an executive's wraps
        self.fits("te_pa_row_exec_none", 236, "row")

    def test_the_currencies(self):
        cur = _type_body(self.gui, "te_pa_currency")
        self.assertIn("maximumsize = { 156 -1 }", cur)
        self.assertIn("size = { 156 8 }", cur)
        self.assertEqual(3 * 156 + 2 * 6, 480)
        self.fits("te_pa_row_funds", 156, "row", MONEY)
        self.fits("te_pa_row_funds_small", 156, "row", "999")
        self.fits("te_pa_row_conn", 156, "row", CURRENCY)
        self.fits("te_pa_row_stand", 156, "row", CURRENCY)

    def test_the_posture_line(self):
        """Posture 192, then three buttons of 92, 4 between: 480."""
        row = _type_body(self.gui, "te_pa_firm_row")
        self.assertIn("maximumsize = { 192 -1 }", row)
        self.assertIn("size = { 284 28 }", row)
        self.assertEqual(row.count("size = { 92 28 }"), 3)
        self.assertEqual(192 + 4 + 284, 480)
        self.assertEqual(3 * 92 + 2 * 4, 284)
        for name in ("favored", "tolerated", "restrained"):
            with self.subTest(posture=name):
                self.fits("te_pa_row_posture", 192, "row", self.shown(f"te_pa_posture_{name}"))
                self.fits(f"te_pa_posture_{name}_btn", 84, "row")

    def test_the_goals_table(self):
        """The held mark 20, the goal 184 (wraps), Pressure, Weight and Score 84 each, 6 between: 480."""
        cells = _type_body(self.gui, "te_pa_goal_cells")
        self.assertIn("size = { 20 22 }", cells)
        self.assertIn("maximumsize = { 184 -1 }", cells)
        self.assertEqual(cells.count("maximumsize = { 84 -1 }"), 3)
        self.assertEqual(20 + 184 + 3 * 84 + 4 * 6, 480)
        for key in ("te_pa_det_pressure_head", "te_pa_det_weight_head", "te_pa_det_score_head"):
            self.fits(key, 84, "row")

    def test_the_detail_cells(self):
        self.fits("te_pa_det_share", 236, "row", SHARE)
        self.fits("te_pa_det_seat_none", 236, "row")


class StructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.loc = _all_loc()

    def test_the_bom(self):
        for path in (GUI, SGUIS):
            with self.subTest(path=os.path.relpath(path, REPO)):
                with open(path, "rb") as f:
                    head = f.read(6)
                self.assertEqual(head[:3], b"\xef\xbb\xbf")
                self.assertNotEqual(head[3:6], b"\xef\xbb\xbf")

    def test_the_sections_in_order(self):
        body = _type_body(self.gui, "te_pa_tab_body")
        content = _no_comments(body[body.index('block "te_pa_tab_layout"'):])
        self.assertEqual(re.findall(r"^\t+(te_pa_\w+_panel) = \{\}", content, re.M),
                         ["te_pa_overview_panel", "te_pa_roster_panel", "te_pa_ledger_panel"])
        self.assertIn("GetVariableSystem.Set('te_popup', 'help_private_actors')", body)
        self.assertIn('blockoverride "tab_open_journal" {}', body)
        self.assertIn("te_window_private_actors_tab_sgui", body[body.index('blockoverride "tab_gate"'):])

    def test_the_columns(self):
        columns = assert_wide_matches_narrow(self, "te_pa_wide_sections",
                                             layout=("te_pa_tab_body", "te_pa_tab_layout"))
        # a section a column, in the tab's order; none hides while the tab is open
        self.assertEqual(columns, [["te_pa_overview_panel"], ["te_pa_roster_panel"], ["te_pa_ledger_panel"]])
        self.assertNotIn("_visible", _type_body(self.gui, "te_pa_wide_sections"))

    def test_the_registry(self):
        tab = next(t for t in window_gen.TABS if t.key == "private_actors")
        self.assertEqual((tab.row, tab.body, tab.layout, tab.wide),
                         (2, "te_pa_tab_body", "te_pa_tab_layout", "te_pa_wide_sections"))
        self.assertEqual(tab.label, "te_window_tab_private_actors")
        self.assertEqual(self.loc[tab.label], "$te_pa_system_name$")
        # public: National Info shows any country's firms (§ 12.2 rule 4)
        self.assertTrue(tab.public)
        self.assertIn("private_actors", window_gen.NI_ORDER)
        # on its strip only while the rule is on, as every rule-gated tab; the economy strip's sixth
        self.assertEqual(tab.strip, window_gen.shown("te_window_private_actors_tab_unlock_sgui"))
        self.assertEqual(tab.unlock, "te_window_private_actors_tab_unlock_sgui")
        self.assertEqual([t.key for t in window_gen.TABS if t.row == 2][-1], "private_actors")
        self.assertEqual(len([t for t in window_gen.TABS if t.row == 2]), len(window_gen.SLOTS_SIX))

    def test_the_gates(self):
        sguis = _read(TAB_SGUIS)
        gate = _no_comments(_txt_block(sguis, "te_window_private_actors_tab_sgui"))
        self.assertRegex(gate, r"is_shown = \{ te_pa_on = yes \}")
        unlock = _no_comments(_txt_block(sguis, "te_window_private_actors_tab_unlock_sgui"))
        self.assertIn("is_shown = { te_pa_on = yes }", unlock)
        self.assertIn("is_valid = { te_pa_on = yes }", unlock)
        for block in (gate, unlock):
            self.assertNotIn("has_game_rule", block)    # the rule is read through te_pa_on alone
            self.assertNotIn("scope:", block)

    def test_the_help_popup_is_in_the_root(self):
        popups = _read(POPUPS)
        self.assertIn("te_private_actors_help_popup = {}", popups)
        popup = _type_body(self.gui, "te_private_actors_help_popup")
        self.assertIn("GetVariableSystem.HasValue('te_popup', 'help_private_actors')", popup)
        self.assertIn("te_private_actors_help_body = {}", popup)

    def test_the_rows_read_the_rows_list(self):
        roster = _type_body(self.gui, "te_pa_roster_panel")
        self.assertIn("datamodel = \"[Country.MakeScope.GetList('te_pa_rows')]\"", roster)
        self.assertRegex(roster, r"te_pa_firm_row = \{\s*datacontext = \"\[Scope\.GetScriptContainer\]\"")
        row = _type_body(self.gui, "te_pa_firm_row")
        # the company through the row's copy, never Company.MakeScope (unproven)
        self.assertIn("ScriptContainer.MakeScope.Var('te_pa_r_firm').GetCompany", row)
        self.assertNotIn("Company.MakeScope", self.gui)
        self.assertIn("FancyTooltip_Company = {}", row)

    def test_the_posture_buttons(self):
        """Three buttons, one scripted GUI a posture, the row passed as te_pa_row, under the own-country guard
        and the observer test; each scripted GUI sets its posture with Task 2's verb, grays the posture held and
        says in a custom_tooltip what the posture does."""
        row = _type_body(self.gui, "te_pa_firm_row")
        slot = _block_from(row, row.index("using = te_own_country_only") - 40)
        self.assertIn('visible = "[Not( GetMetaPlayer.IsObserver )]"', slot)
        sguis = _read(SGUIS)
        for name, (code, verb) in POSTURES.items():
            with self.subTest(posture=name):
                sgui = f"te_pa_posture_{name}_sgui"
                self.assertIn(f"datacontext = \"[GetScriptedGui('{sgui}')]\"", slot)
                block = _no_comments(_txt_block(sguis, sgui))
                self.assertIn("saved_scopes = { te_pa_row }", block)
                self.assertIn("ai_is_valid = { always = no }", block)
                self.assertIn(f"te_pa_can_set_posture = {{ POSTURE = {code} NAME = {name} }}", block)
                self.assertRegex(block, rf"custom_tooltip = \{{\s*text = te_pa_posture_{name}_does_tt\s*"
                                        rf"te_pa_cmd_set_posture = \{{ POSTURE = {code} VERB = {verb} \}}\s*\}}")
                tooltip = self.loc[f"te_pa_posture_{name}_btn_tt"]
                self.assertIn("ScriptedGui.IsValidTooltip( GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( "
                              "'te_pa_row', ScriptContainer.MakeScope ).End )", tooltip)
                self.assertIn("ScriptedGui.ExecuteTooltip(", tooltip)
                for key in (f"te_pa_posture_{name}_does_tt", f"te_pa_posture_not_held_{name}_tt"):
                    self.assertIn(key, self.loc)
        self.assertEqual(slot.count("AddScope( 'te_pa_row', ScriptContainer.MakeScope )"), 6)
        # the command saves the owner as te_pa_home before te_pa_set_posture, and copies the row again
        cmd = _txt_block(_read(CORE_EFFECTS), "te_pa_cmd_set_posture")
        self.assertLess(cmd.index("save_scope_as = te_pa_home"), cmd.index("te_pa_set_posture = {"))
        self.assertLess(cmd.index("te_pa_set_posture = {"), cmd.index("te_pa_row_sync = yes"))
        # the check fails closed with no row, and asks that the firm is the country's
        can = _txt_block(_read(CORE_TRIGGERS), "te_pa_can_set_posture")
        self.assertEqual(can.count("exists = scope:te_pa_row"), 2)
        self.assertIn("owner = root", can)
        self.assertIn("NOT = { var:te_pa_posture ?= $POSTURE$ }", can)

    def test_the_ledger_starts_collapsed_newest_first(self):
        ledger = _type_body(self.gui, "te_pa_ledger_panel")
        self.assertIn("GetVariableSystem.Toggle('te_pa_ledger_open')", ledger)
        panel = _block_from(ledger, ledger.index("te_pa_panel = {") + len("te_pa_panel = "))
        self.assertIn("visible = \"[GetVariableSystem.Exists('te_pa_ledger_open')]\"", panel)
        self.assertIn("datamodel = \"[Country.MakeScope.GetList('te_pa_ledger_view')]\"", panel)
        # the view is rebuilt newest first after each line, past the eviction
        add = _txt_block(_read(LEDGER_EFFECTS), "te_pa_ledger_add")
        self.assertLess(add.index("destroy_container = yes"), add.index("te_pa_ledger_view_rebuild = yes"))
        view = _txt_block(_read(LEDGER_EFFECTS), "te_pa_ledger_view_rebuild")
        self.assertIn("order_by = te_pa_ledger_recency_order", view)
        self.assertIn("max = 20", view)
        # a line names its firm, "author unknown" for a secret one, a fallback for a firm that has gone
        line = _type_body(self.gui, "te_pa_ledger_row")
        for key in ("te_pa_ledger_row_unknown", "te_pa_ledger_row_gone", "te_pa_ledger_row_named"):
            self.assertIn(f"'{key}'", line)
            self.assertIn("ScriptContainer.GetCustom('te_pa_ledger_line')", self.loc[key])
        self.assertIn("Author unknown", self.loc["te_pa_ledger_row_unknown"])
        self.assertIn("Var('te_pa_l_actor').GetCompany.IsValid", line)
        self.assertIn("HasVariable('te_pa_l_gone')", line)
        clear = _txt_block(_read(CORE_EFFECTS), "te_pa_clear_firm")
        self.assertIn("set_variable = { name = te_pa_l_gone value = 1 }", clear)

    def test_every_holding_has_a_chip_a_line_and_a_count(self):
        chips = _type_body(self.gui, "te_pa_holding_chips")
        lines = _type_body(self.gui, "te_pa_firm_holdings")
        count = _txt_block(_read(CORE_VALUES), "te_pa_row_holdings_count")
        for h in HOLDINGS:
            with self.subTest(holding=h):
                shown = f"[GreaterThan_CFixedPoint( ScriptContainer.GetVariableValue('te_pa_r_{h}'), '(CFixedPoint)0' )]"
                self.assertIn(f'visible = "{shown}"', chips)
                self.assertIn(f'visible = "{shown}"', lines)
                self.assertIn(f"var:te_pa_r_{h} > 0", count)
                for key in (f"te_pa_chip_{h}_tt", f"te_pa_det_{h}", f"te_pa_holding_{h}"):
                    self.assertIn(key, self.loc)

    def test_the_goals_table_has_every_goal(self):
        table = _type_body(self.gui, "te_pa_goals_table")
        for n, g in enumerate(GOALS, 1):
            with self.subTest(goal=g):
                self.assertIn(f"'(CFixedPoint){n}' )]", table)
                self.assertIn(f'text = "te_pa_goal_{n}"', table)
                for kind in ("p", "w", "s"):
                    self.assertIn(f"GetVariableValue('te_pa_r_{kind}_{g}')", table)

    def test_the_detail_opens_per_firm(self):
        """A GetVariableSystem key per firm, named for its company (te_pa_firm_open_<name>), collapsed until
        opened; the detail is built only while it is open."""
        row = _type_body(self.gui, "te_pa_firm_row")
        key = "Concatenate( 'te_pa_firm_open_', ScriptContainer.MakeScope.Var('te_pa_r_firm').GetCompany.GetNameNoFormatting )"
        self.assertIn(f"GetVariableSystem.Toggle( {key} )", row)
        self.assertIn(f'visible = "[GetVariableSystem.Exists( {key} )]"', row)
        self.assertIn("te_pa_firm_detail = {}", row)

    def test_a_rows_hovers_read_the_row_alone(self):
        """A tooltip inside a datamodel item renders with the item's datacontext only (gotcha #24): each hover
        key a row or a ledger line shows reads its ScriptContainer (or a company or state reached from it), or
        GetPlayer under the guard, never the tab's Country."""
        types = ("te_pa_firm_row", "te_pa_firm_detail", "te_pa_goals_table", "te_pa_goal_held_icon",
                 "te_pa_firm_holdings", "te_pa_holding_chips", "te_pa_currency", "te_pa_ledger_row")
        seen = set()
        for name in types:
            body = _type_body(self.gui, name)
            for key in re.findall(r'\btooltip = "(\w+)"', body):
                seen.add(key)
                with self.subTest(key=key):
                    text = self._closure(key)
                    self.assertNotIn("Country.", text)
        self.assertGreater(len(seen), 15)

    def _closure(self, key, depth=0):
        v = self.loc.get(key, "")
        out = [v]
        for k in re.findall(r"\$(\w+)\$", v) + re.findall(r"'(te_pa_\w+)'", v):
            if depth < 5:
                out.append(self._closure(k, depth + 1))
        return "\n".join(out)

    def test_every_key_exists(self):
        keys = set(re.findall(r'\b(?:text|tooltip) = "(te_\w+)"', self.gui))
        keys |= set(re.findall(r"'(te_pa_\w+)'", self.gui)) - {"te_pa_row", "te_pa_rows", "te_pa_ledger_view",
                                                                  "te_pa_ledger_open", "te_pa_firm_open_"}
        keys = {k for k in keys if not k.startswith(("te_pa_r_", "te_pa_l_", "te_pa_tab_", "te_pa_row_holdings"))
                and not k.endswith("_sgui")}
        self.assertGreater(len(keys), 60)
        for key in sorted(keys):
            with self.subTest(key=key):
                self.assertTrue(key in self.loc, f"{key} has no loc")


if __name__ == "__main__":
    unittest.main()
