"""The Power Grids tab of the Timeline Extended window and a Grid Transfer
Station's building panel section (gui/te_grid_widgets.gui): every fixed-width
cell fits its longest text at its font, the tab's structure (three sections,
the full-screen columns), what it reads (the grid record of
te_grid_record_effect, through guarded script values and the country's and
hubs' lists), its gates and checklist, and every key defined.

The width budget is test_banking_layout.py's (the style guide's rule 3): GUI
units per character for each font, plus 10%, read from this file's own
te_grid_fontsize_* templates.

Run: python3 test_power_grid_tab.py
"""
import os
import re
import unittest

from gui_test_helpers import assert_wide_matches_narrow
from scripts.generators import gen_te_systems_window as window_gen
from test_banking_layout import MARGIN, _all_loc, _block_from, _read, _type_body

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "te_grid_widgets.gui")
BUILDING_PANEL = os.path.join(REPO, "gui", "building_details_panel.gui")
POPUPS = os.path.join(REPO, "gui", "te_popups.gui")
VALUES = os.path.join(REPO, "common", "script_values", "power_grid_values.txt")
TAB_SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "power_grid_triggers.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "power_grid_effects.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")
# The longest a printed figure can be: a count four digits, a `|K` figure five
# characters ("99.9K"), a share four ("100%").
NUMBER = "9999"
KILO = "99.9K"
SHARE = "100%"
# The longest state name a cell is held to: vanilla's longest English ones run
# about 20 characters ("North Rhine-Westphalia" is 22, and wraps: the State and
# Grid columns are multiline).
STATE = "Mecklenburg-Pomerania"

_SIZES = {m.group(1): int(m.group(2)) for m in re.finditer(
    r"template te_grid_fontsize_(\w+) \{\s*fontsize = (\d+)", _read(GUI))}
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
        v = re.sub(r"#[A-Za-z_]+(?:;\S*)? ", "", v).replace("#!", "")
        return v.replace("\\n", "")

    def fits(self, key, cell, number=NUMBER):
        width, font = cell
        text = self.shown(key, number)
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, width, f"{key} shows {text!r}: {need:.0f} units in a {width} {font} cell")

    def box(self, text, anchor):
        """(width, font) of the textbox around `anchor`, from the markup: its
        max_width, or its maximumsize's width."""
        at = text.index(anchor)
        start = text.rindex("textbox = {", 0, at)
        tb = _block_from(text, start + len("textbox = "))
        self.assertIn(anchor, tb)
        m = re.search(r"max_width = (\d+)", tb) or re.search(r"maximumsize = \{ (\d+) -1 \}", tb)
        font = re.search(r"using = te_grid_fontsize_(\w+)", tb).group(1)
        return int(m.group(1)), font

    def type_box(self, typ, block):
        return self.box(_type_body(self.gui, typ), 'block "%s"' % block)


class WidthTest(_Budget, unittest.TestCase):
    """Every fixed-width cell fits its longest text (style guide rule 3: no
    "..." on anything a player reads)."""

    def test_type_sizes_are_the_templates(self):
        self.assertEqual(_SIZES, {"row": 17, "heading": 20, "overview": 16})
        self.assertNotRegex(self.gui, r"using = fontsize_")

    def test_overview_cells(self):
        cell = _type_body(self.gui, "te_grid_ov_cell")
        x = int(re.search(r"position = \{ (\d+) 2 \}", cell).group(1))
        width = int(re.search(r"size = \{ (\d+) 70 \}", cell).group(1))
        column = width - x - 6
        for block in ("caption", "word", "fig"):
            self.assertEqual(self.type_box("te_grid_ov_cell", block), (column, "overview"))
        keys = sorted(set(re.findall(r"['\"](te_grid_ov_\w+_(?:cap|word|fig)\w*)['\"]", self.gui)))
        self.assertEqual(len([k for k in keys if k.endswith("_cap")]), 6)
        for key in keys:
            with self.subTest(key=key):
                number = KILO if key in ("te_grid_ov_sent_fig", "te_grid_ov_received_fig") else (
                    SHARE if key.startswith("te_grid_ov_efficiency") else NUMBER)
                self.fits(key, (column, "overview"), number)

    def test_headings(self):
        for panel, key, right, number in (("te_grid_grids_panel", "te_grid_grids_header", "te_grid_grids_asof", NUMBER),
                                          ("te_grid_stations_panel", "te_grid_stations_header", "te_grid_stations_count",
                                           NUMBER)):
            with self.subTest(panel=panel):
                self.assertIn(f'text = "{key}"', _type_body(self.gui, panel))
                self.assertIn(f'text = "{right}"', _type_body(self.gui, panel))
                self.fits(key, self.type_box("te_grid_heading", "heading_text"))
                self.fits(right, self.type_box("te_grid_heading", "heading_right"), number)

    def test_grid_card(self):
        card = _type_body(self.gui, "te_grid_card")
        self.fits("te_grid_card_name", self.box(card, '"te_grid_card_name"'), STATE)
        self.fits("te_grid_card_size", self.box(card, '"te_grid_card_size"'))
        half = (int(re.search(r"maximumsize = \{ (\d+) -1 \}", _type_body(self.gui, "te_grid_cell")).group(1)), "row")
        for key, number in (("te_grid_card_supply", SHARE), ("te_grid_card_supply_no_demand", NUMBER),
                            ("te_grid_card_price", SHARE), ("te_grid_card_sent", KILO),
                            ("te_grid_card_delivered", KILO)):
            with self.subTest(key=key):
                self.assertRegex(card, rf"['\"]{key}['\"]")
                self.fits(key, half, number)
        self.fits("te_grid_card_countries", self.box(card, '"te_grid_card_countries"'))
        self.fits("te_grid_card_markets", self.box(card, '"te_grid_card_markets"'))
        # two halves and their spacing fill the row
        self.assertEqual(2 * half[0] + 8, 480)

    def test_station_columns(self):
        cells = _type_body(self.gui, "te_grid_station_cells")
        widths = [int(w) for w in re.findall(r"maximumsize = \{ (\d+) -1 \}", cells)]
        self.assertEqual(sum(widths) + 2 * (len(widths) - 1), 480)
        head = {"state": "te_grid_st_col_state", "mode": "te_grid_st_col_mode", "flow": "te_grid_st_col_flow",
                "grid": "te_grid_st_col_grid", "staff": "te_grid_st_col_staff"}
        for col, key in head.items():
            with self.subTest(head=col):
                self.fits(key, self.type_box("te_grid_station_cells", f"cell_{col}"))
        for key in ("te_grid_mode_sending", "te_grid_mode_receiving", "te_grid_mode_idle", "te_grid_mode_offline"):
            self.fits(key, self.type_box("te_grid_station_cells", "cell_mode"))
        self.fits("te_grid_st_flow", self.type_box("te_grid_station_cells", "cell_flow"), KILO)
        self.fits("te_grid_st_staff", self.type_box("te_grid_station_cells", "cell_staff"), SHARE)
        self.fits("te_grid_st_none", self.type_box("te_grid_station_cells", "cell_grid"))
        # A state's or a hub's name wraps rather than elides.
        for col in ("state", "grid"):
            box = _block_from(cells, cells.rindex("textbox = {", 0, cells.index(f'block "cell_{col}"')) + len("textbox = "))
            self.assertIn("multiline = yes", box)
            self.assertNotIn("elide", box)

    def test_building_rows(self):
        row = _type_body(self.gui, "te_grid_kv_row")
        label = self.box(row, 'block "row_label"')
        value = self.box(row, 'block "row_value"')
        self.assertEqual(label[0] + value[0], 480)
        for key in ("TE_STATE_GRID_ROW_MODE", "TE_STATE_GRID_ROW_MOVED", "TE_STATE_GRID_ROW_HUB",
                    "te_grid_bld_supply_label", "te_grid_bld_price_label", "TE_STATE_GRID_ROW_EFFICIENCY",
                    "te_grid_st_col_staff"):
            with self.subTest(key=key):
                self.fits(key, label)
        for key, number in (("te_grid_bld_flow", KILO), ("te_grid_bld_supply", SHARE), ("te_grid_bld_price", SHARE),
                            ("te_grid_bld_efficiency", SHARE)):
            with self.subTest(key=key):
                self.fits(key, value, number)


class StructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)

    def test_the_bom(self):
        with open(GUI, "rb") as f:
            head = f.read(6)
        self.assertEqual(head[:3], b"\xef\xbb\xbf")
        self.assertNotEqual(head[3:6], b"\xef\xbb\xbf")

    def test_three_sections_in_order(self):
        body = _type_body(self.gui, "te_grid_tab_body")
        content = body[body.index('block "te_grid_tab_layout"'):]
        self.assertEqual(re.findall(r"^\t+(te_grid_\w+_panel) = \{\}", content, re.M),
                         ["te_grid_overview_panel", "te_grid_grids_panel", "te_grid_stations_panel"])
        self.assertIn("GetVariableSystem.Set('te_popup', 'help_power_grids')", body)
        self.assertIn('blockoverride "tab_open_journal" {}', body)
        self.assertIn("te_window_power_grids_tab_sgui", body[body.index('blockoverride "tab_gate"'):])

    def test_the_columns(self):
        columns = assert_wide_matches_narrow(self, "te_grid_wide_sections",
                                             layout=("te_grid_tab_body", "te_grid_tab_layout"))
        self.assertEqual(columns, [["te_grid_overview_panel", "te_grid_grids_panel"], ["te_grid_stations_panel"]])

    def test_the_registry(self):
        tab = next(t for t in window_gen.TABS if t.key == "power_grids")
        self.assertEqual((tab.row, tab.body, tab.layout, tab.wide),
                         (1, "te_grid_tab_body", "te_grid_tab_layout", "te_grid_wide_sections"))
        self.assertTrue(tab.public)
        # No game rule: always on the strip, greyed with its checklist until a station is built or queued.
        self.assertIsNone(tab.strip)
        self.assertEqual(tab.unlock, "te_window_power_grids_tab_unlock_sgui")
        self.assertEqual([t.key for t in window_gen.TABS if t.row == 1][-1], "power_grids")
        self.assertIn("power_grids", window_gen.NI_ORDER)

    def test_the_gates(self):
        sguis = _read(TAB_SGUIS)
        gate = _no_comments(_txt_block(sguis, "te_window_power_grids_tab_sgui"))
        shown = gate[gate.index("is_shown"):gate.index("ai_is_valid")]
        # The research, or a station held without it; nothing that walks buildings, since the
        # gate is read several times a frame while the window is open (the PR's review).
        self.assertIn("has_technology_researched = electrical_capacitors", shown)
        self.assertIn("any_scope_state = { has_building = building_grid_transfer_station }", shown)
        for walk in ("any_scope_building", "te_grid_state_has_station", "every_", "ordered_"):
            self.assertNotIn(walk, shown)
        unlock = _txt_block(sguis, "te_window_power_grids_tab_unlock_sgui")
        self.assertIn("is_valid = { te_grid_tab_unlocked = yes }", unlock)
        checklist = _no_comments(_txt_block(_read(TRIGGERS), "te_grid_tab_unlocked"))
        # One line, the gate itself, so a met checklist is an open tab.
        self.assertEqual(checklist.count("custom_tooltip = {"), 1)
        gate_or = re.sub(r"\s+", " ", shown[shown.index("OR = {"):])
        check_or = re.sub(r"\s+", " ", checklist[checklist.index("OR = {"):])
        self.assertTrue(gate_or.startswith(check_or.rstrip(" }")), (gate_or, check_or))
        for body in (gate, unlock):
            self.assertNotIn("scope:", body)

    def test_the_help_popup_is_in_the_root(self):
        self.assertEqual(len(re.findall(r"^\tte_power_grids_help_popup = \{\}$", _read(POPUPS), re.M)), 1)
        popup = _type_body(self.gui, "te_power_grids_help_popup")
        self.assertIn("te_power_grids_help_body = {}", popup)
        self.assertIn("help_power_grids", popup)

    def test_lists_read_the_record(self):
        grids = _type_body(self.gui, "te_grid_grids_panel")
        self.assertIn("datamodel = \"[Country.MakeScope.GetList('te_grid_hubs')]\"", grids)
        self.assertRegex(grids, r'te_grid_card = \{\s*datacontext = "\[Scope\.GetState\]"')
        stations = _type_body(self.gui, "te_grid_stations_panel")
        self.assertIn("datamodel = \"[Country.MakeScope.GetList('te_grid_stations')]\"", stations)
        self.assertRegex(stations, r'te_grid_station_row = \{\s*datacontext = "\[Scope\.GetState\]"')
        # A row whose state changed hands since the last run waits for the next one.
        row = _type_body(self.gui, "te_grid_station_row")
        self.assertIn('visible = "[ObjectsEqual( State.GetOwner, Country.Self )]"', row)
        card = _type_body(self.gui, "te_grid_card")
        self.assertIn("datamodel = \"[State.MakeScope.GetList('te_grid_rec_capitals')]\"", card)
        # A country through its capital (gotcha #15).
        self.assertRegex(card, r'datacontext = "\[Scope\.GetState\]"[\s\S]*tiny_flag = \{\s*datacontext = "\[State\.GetCountry\]"')
        effects = _read(EFFECTS)
        for name in ("te_grid_hubs", "te_grid_stations", "te_grid_rec_capitals"):
            self.assertIn(f"add_to_variable_list = {{ name = {name} ", effects)

    def test_the_stations_table_follows_its_list(self):
        """A station built since the last run is in the live count but not yet in the list,
        so the note and the table read the list, or the section is a header with no rows."""
        panel = _type_body(self.gui, "te_grid_stations_panel")
        empty = "IsDataModelEmpty( Country.MakeScope.GetList('te_grid_stations') )"
        note = panel[panel.rindex("te_grid_note = {", 0, panel.index('"te_grid_stations_none"')):]
        self.assertIn(f'visible = "[{empty}]"', note[:note.index("}")])
        table = panel[panel.index("flowcontainer = {", panel.index('"te_grid_stations_none"')):]
        self.assertIn(f'visible = "[Not( {empty} )]"', table[:table.index("te_grid_station_head")])

    def test_the_selections(self):
        """Each two-way text picks the right branch."""
        card = _type_body(self.gui, "te_grid_card")
        self.assertIn("text = \"[SelectLocalization( GreaterThan_CFixedPoint( State.MakeScope.ScriptValue('te_grid_rec_demand_disp'), "
                      "'(CFixedPoint)0' ), 'te_grid_card_supply', 'te_grid_card_supply_no_demand' )]\"", card)
        section = _type_body(self.gui, "te_grid_building_section")
        self.assertIn("text = \"[SelectLocalization( GreaterThan_CFixedPoint( State.MakeScope.ScriptValue('te_grid_region_demand_disp'), "
                      "'(CFixedPoint)0' ), 'te_grid_bld_supply', 'te_grid_bld_supply_no_demand' )]\"", section)
        row = _type_body(self.gui, "te_grid_station_row")
        self.assertIn("'(CFixedPoint)0' ), 'te_grid_st_flow', 'te_grid_st_none' )", row)
        self.assertIn("ScriptValue('te_grid_hub_disp'), '(CFixedPoint)0' ), 'te_grid_st_grid', 'te_grid_st_none' )", row)
        self.assertIn("'(CFixedPoint)0' ), 'TE_STATE_GRID_ROW_HUB_TT', 'te_grid_st_no_grid_tt' )", row)
        overview = _type_body(self.gui, "te_grid_overview_panel")
        for good, none in (("te_grid_ov_grids_word", "te_grid_ov_grids_word_none"),
                           ("te_grid_ov_grids_fig", "te_grid_ov_grids_fig_none"),
                           ("te_grid_ov_agreements_word", "te_grid_ov_agreements_word_none")):
            self.assertIn(f"'(CFixedPoint)0' ), '{good}', '{none}' )", overview)
        # no count printed beside a plural noun ("1 stations"): such figures are "Label: N"
        loc = _all_loc()
        for key in ("te_grid_card_size", "te_grid_ov_grids_fig", "te_grid_ov_agreements_word", "te_grid_bld_hub"):
            self.assertNotRegex(loc[key], r"\]#?!? (stations|partners|grids)\b", key)

    def test_the_tabs_figures(self):
        """What each figure counts (each a mutation the review named)."""
        values = _no_comments(_read(VALUES))
        sent, received = _txt_block(values, "te_grid_tab_sent_disp"), _txt_block(values, "te_grid_tab_received_disp")
        self.assertIn("te_grid_mode_disp = 1", sent)
        self.assertIn("te_grid_mode_disp = 2", received)
        self.assertIn("te_grid_mode_disp = 1", _txt_block(values, "te_grid_tab_senders_disp"))
        self.assertIn("te_grid_mode_disp = 2", _txt_block(values, "te_grid_tab_receivers_disp"))
        for body in (sent, received):
            self.assertIn("add = te_grid_electricity_moved_disp", body)
        reach = _txt_block(values, "te_grid_tab_reach_disp")
        self.assertIn("NOT = { is_target_in_variable_list = { name = te_grid_partners target = root } }", reach)
        self.assertIn("exists = this", reach)
        on_grid = _txt_block(values, "te_grid_tab_on_grid_disp")
        for cond in ("has_building = building_grid_transfer_station", "has_variable = te_grid_hub"):
            self.assertIn(cond, on_grid)
        staffing = _txt_block(values, "te_grid_station_staffing_disp")
        self.assertIn("is_building_type = building_grid_transfer_station", staffing)
        self.assertIn("add = occupancy", staffing)
        # Agreements live from the treaties, not the run's list (refreshed only while the country has a station).
        partners = _txt_block(values, "te_grid_tab_partners_disp")
        self.assertIn("every_scope_treaty", partners)
        self.assertIn("any_scope_article = { has_type = grid_interconnection_agreement }", partners)
        self.assertIn("subtract = te_grid_rec_delivered_disp", _txt_block(values, "te_grid_rec_losses_disp"))
        self.assertIn("value = te_grid_rec_sent_disp", _txt_block(values, "te_grid_rec_losses_disp"))

    def test_the_grids_demand_is_on_every_member(self):
        """A grid nothing uses power on has a ratio of 0, as has one with demand and no supply,
        so the building panel's Supply reads the grid's demand, stored beside the ratio."""
        effects = _no_comments(_read(EFFECTS))
        balance = _txt_block(effects, "te_grid_balance_region_effect")
        self.assertIn("set_variable = { name = te_grid_region_demand value = local_var:te_grid_sum_consumption }", balance)
        for name in ("te_grid_idle_station_effect", "te_grid_clear_state_effect"):
            self.assertIn("remove_variable = te_grid_region_demand", _txt_block(effects, name))

    def test_every_value_read_is_defined_and_guarded(self):
        values = _read(VALUES)
        defined = set(re.findall(r"(?m)^(\w+) = \{", values))
        loc = _all_loc()
        keys = set(re.findall(r'"(\w+)"', self.gui)) | set(re.findall(r"'(\w+)'", self.gui))
        text = self.gui + "\n".join(loc[k] for k in keys if k in loc)
        reads = set(re.findall(r"ScriptValue\('(\w+)'\)", text))
        self.assertTrue(reads)
        self.assertLessEqual(reads, defined)
        # Each of the tab's own reads a variable only behind a has_variable (or reads none).
        for name in sorted(r for r in reads if r.startswith(("te_grid_rec_", "te_grid_tab_"))):
            with self.subTest(value=name):
                body = _no_comments(_txt_block(values, name))
                for var in set(re.findall(r"\bvar:(\w+)", body)):
                    # read only under the if that tests it
                    self.assertRegex(body, rf"limit = \{{ has_variable = {var} \}}\s*value = var:{var}\b")
                    self.assertEqual(body.count(f"var:{var}"), 1, var)
                for lst in set(re.findall(r"\n\s*variable = (\w+)", body)):
                    self.assertIn(f"has_variable_list = {lst}", body)

    def test_every_key_exists(self):
        loc = _all_loc()
        keys = set(re.findall(r'\b(?:text|tooltip) = "([A-Za-z]\w*)"', self.gui))
        keys |= set(re.findall(r", '((?:te_grid|TE_STATE_GRID)\w*)'", self.gui))
        keys |= {"te_window_tab_power_grids", "te_window_tab_power_grids_tt", "te_window_tab_power_grids_locked_tt",
                 "te_grid_tab_unlock_tech_tt"}
        self.assertEqual(sorted(k for k in keys if k not in loc and not k.endswith("_sgui")), [])

    def test_no_control_in_the_tab(self):
        """The tab shows another country all of it (National Info), so it has
        no control: no scripted GUI's Execute, no onclick but the "?"."""
        for name in ("te_grid_overview_panel", "te_grid_grids_panel", "te_grid_stations_panel", "te_grid_card",
                     "te_grid_station_row", "te_grid_station_cells"):
            with self.subTest(type=name):
                body = _type_body(self.gui, name)
                self.assertNotIn("Execute", body)
                self.assertNotIn("onclick", body)


class BuildingPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = _read(BUILDING_PANEL)
        cls.gui = _read(GUI)

    def test_only_on_a_station(self):
        start = self.panel.index("### MOD: Power Grids")
        block = self.panel[start:self.panel.index("### END MOD: Power Grids", start)]
        self.assertIn("visible = \"[Building.IsBuildingType('building_grid_transfer_station')]\"", block)
        self.assertRegex(block, r'te_grid_building_section = \{\s*datacontext = "\[Building\.GetState\]"')
        self.assertEqual(len(re.findall(r"te_grid_building_section = \{", self.panel)), 1)
        # In the overview, before the building's assets.
        self.assertLess(start, self.panel.index("### BUILDING ASSETS"))

    def test_the_link_is_the_players_own(self):
        section = _type_body(self.gui, "te_grid_building_section")
        button = _block_from(section, section.index("button = {") + len("button = "))
        visible = re.search(r'visible = "\[(.*)\]"', button).group(1)
        # An observer has no GetPlayer: its test first (gotcha on observers).
        self.assertTrue(visible.startswith("And( Not( GetMetaPlayer.IsObserver ),"))
        self.assertIn("ObjectsEqual( State.GetOwner, GetPlayer.Self )", visible)
        self.assertIn("GetScriptedGui('te_window_power_grids_tab_sgui').IsShown", visible)
        self.assertIn("GetVariableSystem.Set('te_systems_window_tab', 'power_grids')", button)
        self.assertIn("GetVariableSystem.Set('com_open_window', 'te_systems_window')", button)
        self.assertLess(button.index("te_systems_window_tab"), button.index("com_open_window"))


if __name__ == "__main__":
    unittest.main()
