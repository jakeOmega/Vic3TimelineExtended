"""The Power Grids tab of the Timeline Extended window and a Grid Transfer
Station's building panel section (gui/te_grid_widgets.gui): every fixed-width
cell fits its longest text at its font, the tab's structure (four sections,
the full-screen columns), what it reads (the grid record of
te_grid_record_effect, through guarded script values and the country's and
hubs' lists), its gates and checklist, every key defined, and the Generation
panel's table of what each power plant method makes (GenerationTableTest).

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
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "power_grid_on_actions.txt")
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
# The Generation panel's sources, in the panel's order (te_grid_mix_panel).
SOURCES = ("coal", "oil", "hydro", "nuclear", "renewable", "fusion", "space_solar")

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

    def test_generation_rows(self):
        row = _type_body(self.gui, "te_grid_mix_row")
        widths = [int(w) for w in re.findall(r"maximumsize = \{ (\d+) -1 \}", row)]
        icon = int(re.search(r"icon = \{\s*size = \{ (\d+) \d+ \}", row).group(1))
        bar = int(re.search(r"default_progressbar_horizontal = \{\s*size = \{ (\d+) \d+ \}", row).group(1))
        spacing = int(re.search(r"spacing = (\d+)", row).group(1))
        self.assertEqual(icon + bar + sum(widths) + 4 * spacing, 480)
        label, amount, share = (self.box(row, f'block "row_{b}"') for b in ("label", "amount", "share"))
        for src in SOURCES:
            with self.subTest(source=src):
                self.fits(f"te_grid_mix_{src}", label)
                self.fits(f"te_grid_mix_{src}_amount", amount, KILO)
                self.fits(f"te_grid_mix_{src}_share", share, SHARE)
        panel = _type_body(self.gui, "te_grid_mix_panel")
        self.assertIn('text = "te_grid_mix_header"', panel)
        self.assertIn('text = "te_grid_mix_total"', panel)
        self.fits("te_grid_mix_header", self.type_box("te_grid_heading", "heading_text"))
        self.fits("te_grid_mix_total", self.type_box("te_grid_heading", "heading_right"), KILO)

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

    def test_four_sections_in_order(self):
        body = _type_body(self.gui, "te_grid_tab_body")
        content = body[body.index('block "te_grid_tab_layout"'):]
        self.assertEqual(re.findall(r"^\t+(te_grid_\w+_panel) = \{\}", content, re.M),
                         ["te_grid_overview_panel", "te_grid_mix_panel", "te_grid_grids_panel",
                          "te_grid_stations_panel"])
        self.assertIn("GetVariableSystem.Set('te_popup', 'help_power_grids')", body)
        self.assertIn('blockoverride "tab_open_journal" {}', body)
        self.assertIn("te_window_power_grids_tab_sgui", body[body.index('blockoverride "tab_gate"'):])

    def test_the_columns(self):
        columns = assert_wide_matches_narrow(self, "te_grid_wide_sections",
                                             layout=("te_grid_tab_body", "te_grid_tab_layout"))
        self.assertEqual(columns, [["te_grid_overview_panel", "te_grid_mix_panel", "te_grid_grids_panel"],
                                   ["te_grid_stations_panel"]])

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
        for name in ("te_grid_overview_panel", "te_grid_mix_panel", "te_grid_mix_row", "te_grid_grids_panel",
                     "te_grid_stations_panel", "te_grid_card", "te_grid_station_row", "te_grid_station_cells"):
            with self.subTest(type=name):
                body = _type_body(self.gui, name)
                self.assertNotIn("Execute", body)
                self.assertNotIn("onclick", body)


def _unwrap(value):
    while isinstance(value, (tuple, list)) and len(value) == 2 and value[0] == "=":
        value = value[1]
    return value


def _as_list(value):
    value = _unwrap(value)
    if value is None:
        return []
    return [_unwrap(v) for v in value] if isinstance(value, list) else [value]


def _plant_methods():
    """{building: {method: (block, Electricity a level)}} for every building
    with a method that makes Electricity, vanilla's and the mod's, but the Grid
    Transfer Station; and {method: its building_modifiers' goods inputs}."""
    from mod_state import VANILLA_COMMON_DIRS, ModState
    from vanilla_parsed import load

    kinds = ("Buildings", "PMs", "PM Groups")
    state = ModState({kind: "/nonexistent" for kind in kinds},
                     {kind: os.path.join(REPO, "common", VANILLA_COMMON_DIRS[kind]) for kind in kinds},
                     vanilla_data=load(os.path.join(REPO, "vanilla_parsed")).data)
    assert not state.parse_failures, state.parse_failures
    pms, groups, buildings = (state.get_data(k) for k in ("PMs", "PM Groups", "Buildings"))
    plants, inputs = {}, {}
    for building, body in buildings.items():
        if building == "building_grid_transfer_station":
            continue
        for group in _as_list(_unwrap(body).get("production_method_groups")):
            for pm in _as_list(_unwrap(groups.get(group, {})).get("production_methods")):
                mods = _unwrap(_unwrap(pms.get(pm, {})).get("building_modifiers", {}))
                for block, lines in (mods.items() if isinstance(mods, dict) else ()):
                    lines = _unwrap(lines)
                    if not isinstance(lines, dict):
                        continue
                    inputs.setdefault(pm, set()).update(
                        k[len("goods_input_"):-len("_add")] for k in lines if k.startswith("goods_input_"))
                    if "goods_output_electricity_add" in lines:
                        value = float(_unwrap(lines["goods_output_electricity_add"]))
                        plants.setdefault(building, {})[pm] = (block, value)
    return plants, inputs


class GenerationTableTest(unittest.TestCase):
    """The Generation panel splits each state's measured Electricity among its
    plants by what their methods make (te_grid_mix_output_per_level_value), so
    the table must hold every method that makes Electricity, at its figure, and
    every plant must count towards one source (te_grid_mix_add_building_effect)."""

    @classmethod
    def setUpClass(cls):
        cls.plants, cls.inputs = _plant_methods()
        values = _no_comments(_read(VALUES))
        cls.table_text = _txt_block(values, "te_grid_mix_output_per_level_value")
        cls.effects = _no_comments(_read(EFFECTS))
        cls.add = _txt_block(cls.effects, "te_grid_mix_add_building_effect")

    def table(self):
        """{building: {method: figure}} as the script value reads it."""
        table = {}
        for m in re.finditer(r"limit = \{ is_building_type = (\w+) \}", self.table_text):
            branch = _block_from(self.table_text, self.table_text.rindex("{", 0, m.start()))
            for pm, value in re.findall(
                    r"if = \{ limit = \{ has_active_production_method = (\S+) \} add = (-?\d+(?:\.\d+)?) \}", branch):
                table.setdefault(m.group(1), {})[pm] = float(value)
        return table

    def test_every_method_at_its_figure(self):
        expected = {b: {pm: v for pm, (_, v) in methods.items()} for b, methods in self.plants.items()}
        self.assertTrue(expected)
        got = self.table()
        missing = [f"{b}: if = {{ limit = {{ has_active_production_method = {pm} }} add = {v:g} }}"
                   for b, methods in sorted(expected.items()) for pm, v in methods.items()
                   if got.get(b, {}).get(pm) != v]
        self.assertEqual(missing, [], "te_grid_mix_output_per_level_value lacks or misstates these")
        self.assertEqual(sorted(got), sorted(expected), "a building in the table makes no Electricity")
        for b in got:
            self.assertEqual(sorted(got[b]), sorted(expected[b]), b)

    def test_every_line_is_workforce_scaled(self):
        """The weight is a level's figure times the levels and the staffing."""
        for building, methods in self.plants.items():
            for pm, (block, _) in methods.items():
                self.assertEqual(block, "workforce_scaled", f"{pm} ({building}): a {block} line needs its own weight")
        self.assertIn("multiply = level\n\tmultiply = occupancy",
                      _txt_block(_no_comments(_read(VALUES)), "te_grid_mix_staffed_output_value"))

    def branches(self):
        """[(local variable, {building types}, {methods})] of te_grid_mix_add_building_effect."""
        out = []
        for m in re.finditer(r"change_local_variable = \{ name = te_grid_mix_w_(\w+) add = \$WEIGHT\$ \}", self.add):
            head = self.add[:m.start()]
            start = max(head.rfind("\tif = {"), head.rfind("else_if = {"))
            limit = head[start:]
            out.append((m.group(1), set(re.findall(r"is_building_type = (\w+)", limit)),
                        set(re.findall(r"has_active_production_method = (\S+)", limit))))
        return out

    def test_every_plant_has_a_source(self):
        branches = self.branches()
        self.assertEqual([src for src, _, _ in branches], ["oil", "coal", "hydro", "nuclear", "renewable", "fusion",
                                                          "space_solar"])
        self.assertNotIn("else = {", self.add)
        named = [b for _, types, _ in branches for b in types]
        for building in self.plants:
            with self.subTest(building=building):
                # A Power Plant is Oil on an oil-fired method (the first branch), Coal on any other.
                self.assertEqual(named.count(building), 2 if building == "building_power_plant" else 1)
        self.assertEqual(set(named), set(self.plants))

    def test_the_fuel_names_the_source(self):
        """A plant that burns oil is Oil and one that burns coal Coal."""
        branches = {src: (types, methods) for src, types, methods in self.branches()}
        oil_types, oil_methods = branches["oil"]
        self.assertEqual(oil_types, {"building_power_plant"})
        plant = self.plants["building_power_plant"]
        self.assertEqual(oil_methods, {pm for pm in plant if "oil" in self.inputs.get(pm, ()) and
                                       not pm.startswith("pm_carbon_capture")})
        for src, (types, _) in branches.items():
            for building in types - {"building_power_plant"}:
                burns = set().union(*(self.inputs.get(pm, set()) for pm in self.plants[building]))
                with self.subTest(building=building):
                    if "coal" in burns:
                        self.assertEqual(src, "coal")
                    if "oil" in burns:
                        self.assertEqual(src, "oil")

    def test_the_sources_agree(self):
        """The same seven sources in the record, the split, the tab's values and the panel."""
        record = _txt_block(self.effects, "te_grid_mix_record_effect")
        state = _txt_block(self.effects, "te_grid_mix_state_effect")
        clear = _txt_block(self.effects, "te_grid_mix_clear_weights_effect")
        weights = _txt_block(self.effects, "te_grid_mix_sum_weights_effect")
        values = _no_comments(_read(VALUES))
        gui = _read(GUI)
        self.assertEqual(tuple(re.findall(r"te_grid_mix_split_effect = \{ SOURCE = (\w+) \}", state)), SOURCES)
        self.assertEqual(tuple(re.findall(r"name = te_grid_mix_sum_(\w+) value = 0", record)), SOURCES)
        self.assertEqual(tuple(re.findall(r"set_variable = \{ name = te_grid_mix_(\w+) value = local_var:", record)),
                         SOURCES)
        total = record[record.index("name = te_grid_mix_total"):]
        self.assertEqual(tuple(re.findall(r"local_var:te_grid_mix_sum_(\w+)", total)), SOURCES)
        self.assertEqual(tuple(re.findall(r"name = te_grid_mix_w_(\w+) value = 0", clear)), SOURCES)
        self.assertEqual(tuple(re.findall(r"local_var:te_grid_mix_w_(\w+)", weights)), SOURCES)
        panel = _type_body(gui, "te_grid_mix_panel")
        self.assertEqual(tuple(re.findall(r'text = "te_grid_mix_(\w+)_amount"', panel)), SOURCES)
        for src in SOURCES:
            with self.subTest(source=src):
                self.assertIn(f"te_grid_tab_mix_{src}_disp = {{", values)
                self.assertIn(f"te_grid_tab_mix_{src}_share_disp = {{", values)
                self.assertIn(f"ScriptValue('te_grid_tab_mix_{src}_disp'), '(CFixedPoint)0' )]", panel)

    def test_the_split(self):
        """A share of the state's own generation (its station's delivery taken out), the share
        first so the product stays under the fixed-point ceiling; a state with no staffed plant
        falls back to full-staff weights."""
        state = _txt_block(self.effects, "te_grid_mix_state_effect")
        self.assertIn("set_local_variable = { name = te_grid_mix_gen value = te_grid_local_production_value }", state)
        self.assertIn("WEIGHT = te_grid_mix_staffed_output_value", state)
        self.assertIn("WEIGHT = te_grid_mix_capacity_output_value", state)
        self.assertLess(state.index("te_grid_mix_staffed_output_value"), state.index("te_grid_mix_capacity_output_value"))
        split = _txt_block(self.effects, "te_grid_mix_split_effect")
        self.assertRegex(split, r"value = local_var:te_grid_mix_w_\$SOURCE\$\s*divide = local_var:te_grid_mix_w_all"
                                r"\s*multiply = local_var:te_grid_mix_gen")
        # A named script value isn't known to read a caller's local variables.
        for name in re.findall(r"(?m)^(\w+) = \{", _read(VALUES)):
            self.assertNotIn("local_var:", _txt_block(_read(VALUES), name), name)

    def test_monthly_once_the_tab_is_open(self):
        on_actions = _no_comments(_read(ON_ACTIONS))
        pulse = _txt_block(on_actions, "on_monthly_pulse_country")
        self.assertIn("te_grid_mix_on_action", pulse)
        hook = _txt_block(on_actions, "te_grid_mix_on_action")
        self.assertRegex(hook, r"limit = \{ te_grid_tab_unlocked = yes \}\s*te_grid_mix_record_effect = yes")


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
