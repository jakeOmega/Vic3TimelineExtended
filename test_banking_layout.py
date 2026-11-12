"""The banking panels' section order, collapse defaults and state gates.

Style-guide pass, 2026-09-29 (docs/guides/gui_style_guide.md), in the spirit
of test_un_layout.py: one layout for the journal entry and the Budget tab, an
overview on top, the live sections open, the history and How Banking Works
at the foot, and every collapse flag named for its default.
"""
import json
import operator
import os
import re
import unittest

import gui_tree
from gui_test_helpers import _block_at, _strip_comments, assert_column_closes_with_its_sections, assert_wide_matches_narrow
from gui_test_helpers import _read as _read_gui

REPO = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(REPO, "gui", "journal_entry_widgets")
LAYOUT = os.path.join(W, "banking_layout_widget.gui")
DASH = os.path.join(W, "banking_dashboard_widget.gui")
HIST = os.path.join(W, "banking_history_widget.gui")
BUDGET = os.path.join(REPO, "gui", "budget_panel.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_banking.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "banking_dashboard_scripted_gui.txt")
LOC = os.path.join(REPO, "localization", "english", "te_miscellaneous_l_english.yml")
CUSTOM_LOC = os.path.join(REPO, "common", "customizable_localization", "banking_dash_custom_loc.txt")
DISP = os.path.join(REPO, "common", "script_values", "banking_overview_display_values.txt")
ICONS_DOC = os.path.join(REPO, "docs", "systems", "banking_gui_icons.md")
BANKING_GUI = [DASH, HIST, LAYOUT, BUDGET]
# The entry's gate on the shown country: te_budget_banking_tab_sgui tests has_journal_entry.
ENTRY_GATE = "[GetScriptedGui('te_budget_banking_tab_sgui').IsShown( GuiScope.SetRoot( Country.MakeScope ).End )]"
# The cycle under way: every country holds the entry, dormant until then, and the record draws nothing before it.
CYCLE = "GetScriptedGui('banking_dash_cycle_running').IsShown( GuiScope.SetRoot( {root}.MakeScope ).End )"

STATUS = ["te_banking_sec_active", "te_banking_sec_monetary", "te_banking_sec_interventions"]
REFERENCE = ["te_banking_history_panel"]
# Available Interventions' categories, by the economic system that shows them.
CATEGORIES = {
    "banking_dash_system_market": ["prudential", "credit", "external", "crisis"],
    "banking_dash_system_command": ["plan", "allocation", "admin", "pool"],
    "banking_dash_system_coop": ["surplus", "investment", "council", "membership"],
}
# The rules the Monetary Policy row tooltips used to teach are here since the
# GUI audit (BNK-1, 2026-10-27): the mandates, gold, the exchange rate, the
# international arrangements and prices.
MONETARY_HOW = ["banking_dash_how_rate", "banking_dash_how_rate_none", "banking_dash_how_stance",
                "banking_dash_how_mandates", "banking_dash_how_mandates_change", "banking_dash_how_mandates_floor",
                "banking_dash_how_gold", "banking_dash_how_gold_flow", "banking_dash_how_peg",
                "banking_dash_how_fx", "banking_dash_how_fx_effects", "banking_dash_how_fx_fixed",
                "banking_dash_how_anchor", "banking_dash_how_treaty_peg", "banking_dash_how_backstops",
                "banking_dash_how_union", "banking_dash_how_union_terms", "banking_dash_how_borrowing",
                "banking_dash_how_prices", "banking_dash_how_expected", "banking_dash_how_printing"]
GENERAL_HOW = ["banking_dash_how_cycle", "banking_dash_how_cycle_moves", "banking_dash_how_crashes",
               "banking_dash_how_budget"]
# The Help page's topics, in order: the subheadings over the notes above.
GENERAL_SUBS = ["banking_dash_how_sub_cycle", "banking_dash_how_sub_crashes", "banking_dash_how_sub_budget"]
MONETARY_SUBS = ["banking_dash_how_sub_rate", "banking_dash_how_sub_mandates", "banking_dash_how_sub_gold",
                 "banking_dash_how_sub_fx", "banking_dash_how_sub_arrangements", "banking_dash_how_sub_borrowing",
                 "banking_dash_how_sub_prices"]


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _block_from(text, start):
    """The brace block that opens at or after `start`, braces included."""
    j = text.index("{", start)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j:k + 1]
    raise AssertionError("unbalanced block")


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return _block_from(text, m.end() - 1)[1:-1]


def _sgui(name):
    text = _read(SGUIS)
    m = re.search(rf"(?m)^{name} = \{{", text)
    assert m, f"no scripted GUI {name}"
    return _block_from(text, m.end() - 1)


def _loc():
    keys = {}
    for line in _read(LOC).splitlines():
        m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*(?:#[^"]*)?$', line)
        if m:
            keys[m.group(1)] = m.group(2)
    return keys


def _tab_block():
    """The Banking tab's body (te_banking_tab_body), which the Budget panel's
    tab and the Timeline Extended window's both mount
    (test_te_system_tab_bodies.py checks the mounts)."""
    return _type_body(_read(LAYOUT), "te_banking_tab_body")


class OrderTest(unittest.TestCase):
    def test_status_order(self):
        body = _type_body(_read(LAYOUT), "te_banking_status_sections")
        self.assertEqual(re.findall(r"^\t\t(te_banking_\w+) = \{", body, re.M), STATUS)

    def test_reference_order_the_history(self):
        body = _type_body(_read(LAYOUT), "te_banking_reference_sections")
        self.assertEqual(re.findall(r"^\t\t(te_banking_\w+) = \{", body, re.M), REFERENCE)
        # one open history shell for both hosts (play-test round 2): no swap left
        self.assertNotIn("block ", body)

    def test_composers_and_roots_are_gated_on_an_active_entry(self):
        # The composers read the shown country (another country's panel has no
        # entry, charts-help-national-info spec § 6.3), so they ask whether it
        # holds the entry; the journal entry's own roots still ask the entry.
        layout = _read(LAYOUT)
        self.assertIn(f'visible = "{ENTRY_GATE}"', _type_body(layout, "te_banking_status_sections"))
        self.assertIn(f'visible = "{ENTRY_GATE}"', _type_body(_read(DASH), "te_banking_overview_panel"))
        self.assertEqual(_type_body(layout, "te_banking_wide_sections").count(f'visible = "{ENTRY_GATE}"'), 2)
        roots = re.findall(r'name = "(widget_je_banking_\w+)"\s*visible = "\[JournalEntry\.IsActive\]"', layout)
        self.assertEqual(roots, ["widget_je_banking_overview", "widget_je_banking_status"])

    def test_the_record_waits_for_the_cycle_in_every_host(self):
        """The record (the history charts) draws nothing while the cycle is
        dormant, which every country's entry is until its financial cycle
        starts. Its composer, its journal root and its full-screen column carry
        the cycle's gate too, so none is left empty: the composer would put a
        gap above Open Journal Entry, the root one at the entry's foot, and the
        column an empty 520 band (review of the help-button-everywhere PR)."""
        layout = _read(LAYOUT)
        country = CYCLE.format(root="Country")
        self.assertIn(f'visible = "[{country}]"', _type_body(_read(HIST), "te_banking_history_panel"))
        self.assertIn(f'visible = "[And( {ENTRY_GATE[1:-1]}, {country} )]"',
                      _type_body(layout, "te_banking_reference_sections"))
        self.assertIn(f'name = "widget_je_banking_reference"\n\tvisible = '
                      f'"[And( JournalEntry.IsActive, {CYCLE.format(root="JournalEntry.GetCountry")} )]"', layout)
        wide = _type_body(layout, "te_banking_wide_sections")
        self.assertRegex(wide, r'blockoverride "column_3_visible" \{\s*visible = "\[' + re.escape(country) + r'\]"\s*\}')

    def test_the_journal_entry_attaches_overview_status_reference(self):
        widgets = re.findall(r'widget = \{\s*gui = "([^"]+)"\s*name = "(\w+)"\s*container = "(\w+)"',
                             _read(JE))
        banking = [(n, c) for g, n, c in widgets if g.endswith("banking_layout_widget.gui")]
        self.assertEqual(banking, [("widget_je_banking_overview", "custom_widget_container_1"),
                                   ("widget_je_banking_status", "custom_widget_container_2"),
                                   ("widget_je_banking_reference", "custom_widget_container_3")])
        # the bars are still drawn once, at the top (the marker stays)
        self.assertIn(("gui/journal_entry_widgets/te_je_bars_on_top_marker.gui",
                       "widget_te_je_bars_on_top_marker", "custom_widget_container_7"), widgets)
        # no widget still names the files' old roots
        self.assertEqual([g for g, _, _ in widgets if "banking_dashboard" in g or "banking_history" in g], [])

    def test_the_tab_composes_the_same_sections_and_ends_with_the_link(self):
        """Owner, 2026-09-28: history at the foot and open in the tab; the
        Open Journal Entry link below everything."""
        tab = _tab_block()
        order = [m.group(1) for m in re.finditer(
            r"\b(te_banking_overview_panel|te_banking_status_sections|te_banking_reference_sections)\b", tab)]
        self.assertEqual(order, ["te_banking_overview_panel", "te_banking_status_sections",
                                 "te_banking_reference_sections"])
        self.assertIn("te_banking_reference_sections = {}", tab)
        # the frame's link, below the content (te_system_tab_frame)
        self.assertNotIn('blockoverride "tab_open_journal" ', tab)

    def test_history_is_open_in_both_hosts(self):
        """The owner's rule since play-test round 2: history charts start open,
        so the journal and the tab share one shell with a CLOSED flag."""
        hist = _read(HIST)
        self.assertIn("Toggle('banking_dash_history_closed')", _type_body(hist, "te_banking_history_panel"))
        text = "\n".join(_read(p) for p in BANKING_GUI)
        for old in ("te_hist_charts_open", "te_banking_tab_hist_closed", "te_banking_history_panel_open"):
            self.assertNotIn(old, text, old)

    def test_the_old_panels_and_roots_are_gone(self):
        text = "\n".join(_read(p) for p in BANKING_GUI + [JE])
        for old in ("te_banking_conditions_panel", "te_banking_policies_panel",
                    "widget_je_banking_conditions", "widget_je_banking_policies",
                    "widget_je_banking_history"):
            self.assertNotIn(old, text, old)


class WideTest(unittest.TestCase):
    """The Timeline Extended window's full-screen Banking tab (spec
    2026-11-02-te-window-wide-mode § 7): the tab's sections in three columns
    of 520, under the gates the narrow tab gives them."""

    def test_the_wide_layout_takes_the_owners_three_columns(self):
        """The owner's columns (2026-11-03): Available Interventions under Active Policies, the dial alone in the
        middle, the record last."""
        assert_wide_matches_narrow(self, "te_banking_wide_sections",
                                   layout=("te_banking_tab_body", "te_banking_tab_layout"),
                                   added_gates=("te_banking_sec_monetary",),
                                   columns=[["te_banking_overview_panel", "te_banking_sec_active",
                                             "te_banking_sec_interventions"],
                                            ["te_banking_sec_monetary"],
                                            REFERENCE])

    def test_the_monetary_column_closes_up_while_its_section_hides(self):
        """Monetary Policy alone in column 2 hides under the simplified rule outside a market economy, while the tab
        still shows: the column takes its gate (column_2_visible), so no empty 520 band sits between the others."""
        assert_column_closes_with_its_sections(self, "te_banking_wide_sections", 2, ["te_banking_sec_monetary"])

    def test_the_registry_names_it(self):
        from scripts.generators import gen_te_systems_window as gen
        self.assertEqual(next(t for t in gen.TABS if t.key == "banking").wide, "te_banking_wide_sections")

    def test_the_header_is_centered_over_the_columns(self):
        """In full screen the frame is as wide as its column row, so a header with no anchor sits at the row's left
        edge (#1335's review). default_list_position centers it; where the header is the widest child (the host
        panels, the side panel) nothing moves."""
        body = _type_body(_strip_comments(_read_gui(LAYOUT)), "te_banking_tab_body")
        header = _block_at(body, body.index('blockoverride "tab_header"'))
        self.assertEqual(header.count("default_header = {"), 2)
        self.assertEqual(header.count("using = default_list_position"), 2)


class FlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = "\n".join(_read(p) for p in BANKING_GUI)

    def test_section_flags_say_their_default(self):
        flags = {f for f in re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.text)
                 if f.startswith(("banking_", "te_banking_", "te_hist_"))}
        self.assertGreaterEqual(len(flags), 15)
        for f in flags:
            self.assertRegex(f, r"_(open|closed)$", f"section flag {f} does not say its default")
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", self.text))
            total = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", self.text))
            bare = total - negated
            if f.endswith("_closed"):   # shown unless closed: one bare (show-more), the rest negated
                self.assertEqual(bare, 1, f)
                self.assertGreaterEqual(negated, 2, f)
            else:                        # shown only when opened: one negated (show-more)
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 2, f)

    def test_no_old_flag_survives(self):
        self.assertNotIn("banking_dash_collapsed_", self.text)

    def test_the_live_sections_start_open(self):
        dash = _read(DASH)
        for sec, flag in (("te_banking_sec_active", "banking_dash_active_closed"),
                          ("te_banking_sec_monetary", "banking_dash_monetary_closed")):
            self.assertIn(f"Toggle('{flag}')", _type_body(dash, sec), sec)

    def test_how_banking_works_is_the_help_page(self):
        """How Banking Works is the Help page (te_banking_help_popup, on
        te_popup = help_banking), which only the "?" opens: the link that stood
        for it at the foot of the panel is gone, and the collapse flag with it
        (test_te_help_pages.py)."""
        layout = _strip_comments(_read(LAYOUT))
        self.assertNotIn("te_banking_sec_how", layout)
        self.assertIn("type te_banking_help_body = flowcontainer {", layout)
        self.assertNotIn("banking_dash_how_open", self.text)


class GateTest(unittest.TestCase):
    """Subsections that only matter in one state are shown only in that state."""

    def test_each_category_is_shown_for_its_economic_system_only(self):
        body = _type_body(_read(DASH), "te_banking_sec_interventions")
        found = {}
        for m in re.finditer(r"^\t\tflowcontainer = \{", body, re.M):
            block = _block_from(body, m.start())
            gate = re.search(r"^\t\t\tvisible = \"\[GetScriptedGui\('(\w+)'\)", block, re.M)
            flag = re.search(r"Toggle\('banking_dash_(\w+)_closed'\)", block)
            self.assertTrue(gate and flag, block[:200])
            found.setdefault(gate.group(1), []).append(flag.group(1))
        self.assertEqual(found, CATEGORIES)

    def test_monetary_policy_is_gated_and_its_blocks_follow_the_rule(self):
        body = _type_body(_read(DASH), "te_banking_sec_monetary")
        self.assertRegex(body, r"(?m)^\t\tvisible = \"\[GetScriptedGui\('banking_dash_monetary_shown'\)")
        self.assertIn("GetScriptedGui('banking_mon_system_shown').IsShown", body)
        self.assertIn("GetScriptedGui('banking_dash_omo_fallback_shown').IsShown", body)

    def test_how_it_works_explains_the_monetary_layer_only_while_it_is_on(self):
        """The Help page's monetary topics, under the player's gate: a page
        reads GetPlayer, never the entry (test_te_help_pages.py)."""
        body = _type_body(_read(LAYOUT), "te_banking_help_body")
        m = re.search(r"flowcontainer = \{\s*visible = \"\[GetScriptedGui\('banking_mon_system_shown'\)"
                      r"\.IsShown\( GuiScope\.SetRoot\( GetPlayer\.MakeScope \)\.End \)\]\"", body)
        self.assertTrue(m, "no monetary block gated on banking_mon_system_shown")
        gated = _block_from(body, m.start())
        for key in MONETARY_HOW:
            self.assertIn(f'text = "{key}"', gated, key)
        for key in GENERAL_HOW:
            self.assertIn(f'text = "{key}"', body, key)
            self.assertNotIn(f'text = "{key}"', gated, key)
        # the topics' subheadings, in order, each on its side of the gate
        subs = re.compile(r'text = "(banking_dash_how_sub_\w+)"')
        self.assertEqual(subs.findall(body.replace(gated, "")), GENERAL_SUBS)
        self.assertEqual(subs.findall(gated), MONETARY_SUBS)


class TidyTest(unittest.TestCase):
    def test_labels_with_a_tooltip_are_plain(self):
        # Style guide rule 3 (owner, 2026-10-30): as in vanilla, a hover's
        # label is not underlined.
        dash = _read(DASH)
        for typ, block in (("banking_dash_condition_row", "condition_label"),
                           ("banking_dash_mon_label", "mon_label_text"),
                           ("banking_dash_policy_row", "row_label")):
            body = _type_body(dash, typ)
            self.assertIn(f'block "{block}"', body, typ)
            self.assertNotIn("#tooltippable", body, typ)

    def test_one_heading_style(self):
        dash = _read(DASH)
        self.assertNotIn("banking_dash_mon_subheader", dash)
        self.assertIn("divider_clean", _type_body(dash, "banking_dash_subheader"))
        loc = _loc()
        for key in re.findall(r'text = "(banking_dash_(?:mon_sub|how_sub)_\w+)"',
                              dash + _read(LAYOUT)):
            self.assertNotEqual(loc[key], loc[key].upper(), f"{key} is in capitals")

    def test_no_block_opens_on_a_gap(self):
        """The first heading of the Monetary Policy block and of How Banking
        Works drops its top margin (style guide rule 8)."""
        for path, typ, key in ((DASH, "type te_banking_sec_", "banking_dash_mon_sub_rates"),
                               (LAYOUT, "type te_banking_help_body", "banking_dash_how_sub_cycle")):
            text = _read(path)
            first = text.index("banking_dash_subheader = {", text.index(typ))
            self.assertRegex(_block_from(text, first),
                             rf'blockoverride "subheader_margin" \{{\}}\s*blockoverride "subheader_text" '
                             rf'\{{\s*text = "{key}"', path)

    def test_how_it_works_loc_is_tidy(self):
        loc = _loc()
        keys = re.findall(r'text = "(banking_dash_how_\w+)"', _read(LAYOUT))
        self.assertGreaterEqual(len(keys), 12)
        for key in keys:
            self.assertIn(key, loc)
            self.assertFalse(loc[key].startswith("\\n") or loc[key].endswith("\\n"), key)

    def test_available_interventions_heading_is_centred(self):
        body = _type_body(_read(DASH), "te_banking_sec_interventions")
        head = _block_from(body, body.index("textbox = {"))
        self.assertIn('text = "banking_dash_available_header"', head)
        self.assertIn("align = center|nobaseline", head)
        self.assertIn("parentanchor = hcenter", head)


# Each band word's customizable localization, the display code that picks its
# icon, and which code each of the word's keys is.
BANDS = {
    "banking_dash_momentum_band": ("banking_disp_momentum_band_code", {
        "banking_dash_momentum_band_overheating": 7, "banking_dash_momentum_band_surging": 6,
        "banking_dash_momentum_band_rising": 5, "banking_dash_momentum_band_steady": 4,
        "banking_dash_momentum_band_falling": 3, "banking_dash_momentum_band_collapsing": 2,
        "banking_dash_momentum_band_freefall": 1}),
    "banking_dash_bubble_band": ("banking_disp_bubble_band_code", {
        "banking_dash_bubble_band_low": 1, "banking_dash_bubble_band_building": 2,
        "banking_dash_bubble_band_elevated": 3, "banking_dash_bubble_band_high": 4,
        "banking_dash_bubble_band_severe": 5}),
    "te_mon_stance_band_name": ("banking_disp_stance_band_code", {
        "banking_dash_stance_band_very_loose": 1, "banking_dash_stance_band_loose": 2,
        "banking_dash_stance_band_neutral": 3, "banking_dash_stance_band_tight": 4,
        "banking_dash_stance_band_very_tight": 5}),
    "te_mon_inflation_band_name": ("banking_disp_price_band_code", {
        "banking_dash_price_band_dollarised": 7, "banking_dash_price_band_command": 8,
        "banking_dash_price_band_deflation": 1, "banking_dash_price_band_comfort": 2,
        "banking_dash_price_band_elevated": 3, "banking_dash_price_band_high": 4,
        "banking_dash_price_band_very_high": 5, "banking_dash_price_band_hyper": 6}),
}
# The overview's cells: tooltip (the Current Conditions row's it replaced),
# caption, and what picks the icon.
CELLS = [
    ("banking_dash_phase_tt", "banking_dash_phase_label", "banking_dash_phase_"),
    ("banking_dash_momentum_tt", "banking_dash_momentum_label", "banking_disp_momentum_band_code"),
    ("banking_dash_bubble_tt", "banking_dash_bubble_label", "banking_disp_bubble_band_code"),
    ("banking_dash_budget_tt", "banking_dash_budget_label", None),
    ("banking_dash_mon_stance_tt", "banking_dash_mon_stance_label", "banking_disp_stance_band_code"),
    ("banking_dash_mon_band_tt", "banking_dash_mon_inflation_label", "banking_disp_price_band_code"),
]
DOC_SECTIONS = {
    "banking_dash_phase_": "Overview row 1: cycle phase",
    "banking_disp_momentum_band_code": "Overview row 1: momentum",
    "banking_disp_bubble_band_code": "Overview row 2: bubble pressure",
    "banking_disp_stance_band_code": "Overview row 3: policy stance",
    "banking_disp_price_band_code": "Overview row 3: inflation (the price band)",
    None: "Overview row 2: intervention budget; tool rows: point cost",
}


def _norm(s):
    return " ".join(s.split())


# The icon stacks the cycle's three readings share with the top bar
# (te_banking_topbar_readings): a cell's "icons" block instances one of these.
ICON_TYPES = ["te_banking_phase_icons", "te_banking_momentum_icons", "te_banking_bubble_icons"]


def _icons(dash, block):
    """An "icons" block, with the icon-stack type it instances inlined."""
    for name in re.findall(r"\b(te_banking_\w+_icons) = \{", block):
        block += _type_body(dash, name)
    return block


def _badge(dash, block):
    """A "badge" block, with the crash-risk badge type it instances inlined."""
    if re.search(r"\bte_banking_crash_risk_badge = \{", block):
        block += _type_body(dash, "te_banking_crash_risk_badge")
    return block


DORMANT_ROW = re.compile(r"flowcontainer = \{\s*visible = \"\[GetScriptedGui\('banking_dash_cycle_dormant'\)")


def _dormant_row(body):
    """The dormant entry's row: its one Not Started cell, drawn in place of the
    cycle's rows until the cycle starts (the banking always-on spec,
    2026-10-17)."""
    m = DORMANT_ROW.search(body)
    assert m, "no dormant row"
    return _block_from(body, m.start())


def _cells():
    """(tooltip, caption, [(picker, key, texture)], block) per overview cell
    of a running cycle: the dormant row's cell is not one of them."""
    dash = _read(DASH)
    body = _type_body(dash, "te_banking_overview_panel")
    body = body.replace(_dormant_row(body), "")
    out = []
    for m in re.finditer(r"te_banking_ov_cell = \{", body):
        block = _block_from(body, m.end() - 1)
        tip = re.search(r'^\t*tooltip = "(\w+)"', block, re.M).group(1)
        cap = re.search(r'blockoverride "caption" \{\s*text = "(\w+)"', block).group(1)
        icons_at = block.index('blockoverride "icons" {')
        icons = _icons(dash, _block_from(block, icons_at))
        found = []
        for im in re.finditer(r"icon = \{", icons):
            ib = _block_from(icons, im.end() - 1)
            tex = re.search(r'texture = "([^"]+)"', ib).group(1)
            vis = re.search(r'visible = "(.*)"', ib)
            vis = vis.group(1) if vis else ""
            sv = re.search(r"ScriptValue\('(\w+)'\), '\(CFixedPoint\)(\d+)'", vis)
            sg = re.search(r"GetScriptedGui\('banking_dash_phase_(\w+)'\)", vis)
            if sv:
                found.append((sv.group(1), sv.group(2), tex))
            elif sg:
                found.append(("banking_dash_phase_", sg.group(1), tex))
            else:
                found.append((None, "budget", tex))
        out.append((tip, cap, found, block))
    return out


class OverviewTest(unittest.TestCase):
    """Play-test round 1 (2026-09-29): the readings as icons with their word
    beneath, in place of the Current Conditions table."""

    def test_the_cells_replace_the_table_rows(self):
        cells = _cells()
        self.assertEqual([(tip, cap) for tip, cap, _, _ in cells], [(t, c) for t, c, _ in CELLS])
        pickers = [{p for p, _, _ in icons} for _, _, icons, _ in cells]
        self.assertEqual(pickers, [{p} for _, _, p in CELLS])
        body = _type_body(_read(DASH), "te_banking_overview_panel")
        self.assertNotIn("banking_dash_condition_row", body)
        self.assertNotIn("banking_dash_conditions_header", body)

    def test_every_state_has_an_icon(self):
        icons = {p: {k for _, k, _ in found} for _, _, found, _ in _cells() for p in {f[0] for f in found}}
        self.assertEqual(icons["banking_dash_phase_"], {"panic", "downturn", "stagnation", "stable",
                                                       "expansion", "boom", "frenzy"})
        for _, (sv, codes) in BANDS.items():
            self.assertEqual(icons[sv], {str(c) for c in codes.values()}, sv)

    def test_the_phase_icon_and_word_share_their_scripted_gui(self):
        tip, _, found, block = _cells()[0]
        words = re.findall(r"te_banking_ov_word = \{\s*visible = \"\[GetScriptedGui\('banking_dash_phase_(\w+)'\)"
                           r"[^\n]*\s*text = \"banking_dash_phase_(\w+)_value\"", block)
        self.assertEqual([k for _, k, _ in found], [a for a, _ in words])
        self.assertTrue(all(a == b for a, b in words))

    def test_monetary_cells_are_gated(self):
        cells = {tip: block for tip, _, _, block in _cells()}
        stance = re.search(r'^\t*visible = "(.*)"', cells["banking_dash_mon_stance_tt"], re.M).group(1)
        self.assertIn("banking_mon_has_dial", stance)
        self.assertIn("banking_mon_display_ready", stance)
        band = re.search(r'^\t*visible = "(.*)"', cells["banking_dash_mon_band_tt"], re.M).group(1)
        self.assertIn("banking_mon_system_shown", band)
        self.assertIn("banking_mon_display_ready", band)

    def test_the_crash_risk_tag_is_a_badge(self):
        block = [b for tip, _, _, b in _cells() if tip == "banking_dash_bubble_tt"][0]
        badge = _badge(_read(DASH), _block_from(block, block.index('blockoverride "badge" {')))
        self.assertIn("GetScriptedGui('banking_dash_bubble_risk_high').IsShown", badge)
        self.assertIn('tooltip = "banking_dash_ov_crash_risk_tt"', badge)
        self.assertIn("banking_dash_ov_crash_risk_tt", _loc())

    def test_the_overview_is_as_wide_as_the_sections(self):
        """Two boxed cells to a row (the owner, 2026-10-17: three looked
        crowded in the overview's type), and each instance sets its size: a row
        sums to at most the bars' 480. A cell with a third line is 70 high, one
        without 50."""
        dash = _read(DASH)
        body = _type_body(dash, "te_banking_overview_panel")
        self.assertRegex(body, r"(?m)^\t\tmargin = \{ 10 8 \}")   # 10 + 480 bars + 10 = 500
        header = _type_body(dash, "banking_dash_category_header")
        self.assertIn("size = { 500 32 }", header)
        rows = []
        for m in re.finditer(r"flowcontainer = \{\s*(?:visible = [^\n]*\s*)?direction = horizontal", body):
            row = _block_from(body, m.start())
            sizes = re.findall(r"te_banking_ov_cell = \{\s*(?:visible = [^\n]*\s*)?(?:tooltip = [^\n]*\s*)?"
                               r"size = \{ (\d+) (\d+) \}", row)
            if not sizes:
                continue
            self.assertEqual(len(sizes), row.count("te_banking_ov_cell = {"), "every instance sets its size")
            spacing = int(re.search(r"spacing = (\d+)", row).group(1))
            widths = [int(w) for w, _ in sizes]
            self.assertLessEqual(sum(widths) + (len(widths) - 1) * spacing, 480, row[:80])
            for m2, (_, height) in zip(re.finditer(r"te_banking_ov_cell = \{", row), sizes):
                third = 'blockoverride "third_line"' in _block_from(row, m2.end() - 1)
                self.assertEqual(int(height), 70 if third else 50)
            rows.append(widths)
        # the dormant entry's Not Started cell; then phase and momentum,
        # bubble pressure and the budget, the stance and the price band
        self.assertEqual([len(w) for w in rows], [1, 2, 2, 2])



class MandateGridTest(unittest.TestCase):
    """The mandates' two-by-two grid: both rows are centred, so each keeps the
    width of two buttons whichever show (gui_modding_guide.md gotcha #43)."""

    def test_the_mandate_rows_keep_their_width(self):
        # One wrapper takes the rows' gate (the mandate by choice) and, inside
        # it, one the own-country guard, so the two rows are its grandchildren.
        tree = gui_tree.parse(_read(DASH))
        (gate,) = [n for n in tree.walk() if n.kind == "flowcontainer" and n.prop("visible")
                   and "banking_mon_mandate_by_choice" in n.prop("visible").value]
        (guard,) = gui_tree.widgets(gate)
        self.assertIn(("using", "te_own_country_only"), [(p.key, p.value) for p in guard.props])
        rows = gui_tree.widgets(guard)
        self.assertEqual(len(rows), 2)
        for row, ops in zip(rows, (["14", "4"], ["5", "6"]), strict=True):
            with self.subTest(ops=ops):
                self.assertEqual(row.prop("parentanchor").value, "hcenter")
                buttons = gui_tree.widgets(row)
                self.assertEqual([re.search(r"\(CFixedPoint\)(\d+)", b.prop("onclick").value).group(1)
                                  for b in buttons], ops)
                widths = {gui_tree.size(b)[0] for b in buttons}
                self.assertEqual(widths, {226})
                full = 2 * 226 + int(row.prop("spacing").value)
                gated = [b for b in buttons if b.prop("visible")]
                if gated:
                    # Peg Defence, on a gold standard only: 226 without it.
                    self.assertEqual(gui_tree.size(row, "minimumsize"), (full, -1))
                self.assertEqual(full, 456)
        self.assertTrue([b for b in gui_tree.widgets(rows[1]) if b.prop("visible")], "Peg Defence is gated")

class BandCodeTest(unittest.TestCase):
    """Each icon's display code repeats its band word's tests, in order, so the
    icon and the word beneath it cannot disagree."""

    def test_codes_follow_the_band_words(self):
        custom, disp = _read(CUSTOM_LOC), _read(DISP)
        for loc_name, (sv, codes) in BANDS.items():
            with self.subTest(band=loc_name):
                loc = _block_from(custom, re.search(rf"(?m)^{loc_name} = \{{", custom).end() - 1)
                branches = re.findall(r"text = \{\s*(?:trigger = \{(.*?)\}\s*)?localization_key = (\w+)\s*\}",
                                      loc, re.S)
                unknown, branches = branches[0], branches[1:]
                self.assertEqual(unknown[1], "banking_dash_band_unknown")
                var = re.search(r"NOT = \{ has_variable = (\w+) \}", unknown[0]).group(1)
                value = _block_from(disp, re.search(rf"(?m)^{sv} = \{{", disp).end() - 1)
                self.assertRegex(value, rf"value = 0\s*if = \{{\s*limit = \{{ has_variable = {var} \}}")
                chain = re.findall(r"(?:if|else_if) = \{\s*limit = \{([^{}]*)\}\s*value = (\d+)\s*\}", value)
                last = re.search(r"else = \{\s*value = (\d+)\s*\}", value).group(1)
                self.assertEqual([_norm(c) for c, _ in chain], [_norm(c) for c, _ in branches[:-1]])
                self.assertEqual(branches[-1][0], "", "the word's last branch is its fallback")
                got = [int(v) for _, v in chain] + [int(last)]
                self.assertEqual(got, [codes[k] for _, k in branches])


class HistoryBandTest(unittest.TestCase):
    """The cycle charts' bars name the month's band, as the overview names
    today's (GUI audit BNK-4, 2026-10-27): each row's AddLocalizationIf chain
    picks exactly one word for any reading, the word the overview would."""
    OPS = {"GreaterThanOrEqualTo": operator.ge, "GreaterThan": operator.gt,
           "LessThan": operator.lt, "LessThanOrEqualTo": operator.le,
           ">=": operator.ge, ">": operator.gt, "<": operator.lt, "<=": operator.le}

    @classmethod
    def setUpClass(cls):
        cls.loc, cls.custom = _loc(), _read(CUSTOM_LOC)

    def chosen(self, key, x):
        out = []
        for m in re.finditer(r"\[AddLocalizationIf\( (.*?), '(\w+)' \)\]", self.loc[key]):
            conds = re.findall(r"(\w+)_CFixedPoint\( ScriptContainer\.GetVariableValue\('\w+'\), "
                               r"'\(CFixedPoint\)(-?[\d.]+)' \)", m.group(1))
            self.assertTrue(conds, m.group(0))
            if all(self.OPS[op](x, float(v)) for op, v in conds):
                out.append(m.group(2))
        return out

    def custom_word(self, name, x):
        loc = _block_from(self.custom, re.search(rf"(?m)^{name} = \{{", self.custom).end() - 1)
        for trigger, key in re.findall(r"text = \{\s*(?:trigger = \{(.*?)\}\s*)?localization_key = (\w+)\s*\}",
                                       loc, re.S)[1:]:
            m = re.fullmatch(r"\s*var:\w+ (>=|>|<=|<) (-?[\d.]+)\s*", trigger)
            if not trigger or self.OPS[m.group(1)](x, float(m.group(2))):
                return key

    def test_each_reading_names_one_band(self):
        triggers = _read(os.path.join(REPO, "common", "scripted_triggers", "market_triggers.txt"))
        phases = {}
        for name, body in re.findall(r"(?m)^banking_cycle_is_(\w+) = \{(.*)\}$", triggers):
            conds = re.findall(r"var:finance_cycle_value (>=|<) (\d+)", body)
            if conds and name in ("panic", "downturn", "stagnation", "stable", "expansion", "boom", "frenzy"):
                phases[name] = conds
        self.assertEqual(len(phases), 7)
        for i in range(-20, 221):
            x = i / 2
            with self.subTest(value=x):
                want = [k for k, conds in phases.items() if all(self.OPS[o](x, float(v)) for o, v in conds)]
                self.assertEqual(self.chosen("te_hist_tt_bank_value_row", x),
                                 ["banking_dash_phase_%s_value" % k for k in want])
                self.assertEqual(self.chosen("te_hist_tt_bank_bubble_row", x),
                                 [self.custom_word("banking_dash_bubble_band", x)])
        for i in range(-40, 41):
            x = i / 4
            with self.subTest(momentum=x):
                self.assertEqual(self.chosen("te_hist_tt_bank_momentum_row", x),
                                 [self.custom_word("banking_dash_momentum_band", x)])


class IconsDocTest(unittest.TestCase):
    """docs/systems/banking_gui_icons.md records each icon's file by its code."""

    @classmethod
    def setUpClass(cls):
        cls.doc = {}
        section = None
        for line in _read(ICONS_DOC).splitlines():
            if line.startswith("## "):
                section = line[3:].strip()
            m = re.match(r"\| ([^|]+?) \|(?: [^|]+ \|)*? `(gfx/[^`]+)` \|", line)
            if m and section:
                cls.doc.setdefault(section, {})[m.group(1)] = m.group(2)

    def test_every_icon_is_listed_with_its_code(self):
        for _, _, found, _ in _cells():
            for picker, key, tex in found:
                table = self.doc.get(DOC_SECTIONS[picker], {})
                self.assertEqual(table.get(key), tex, f"{picker} {key}")

    def test_the_badge_is_listed(self):
        block = [b for tip, _, _, b in _cells() if tip == "banking_dash_bubble_tt"][0]
        badge = _badge(_read(DASH), _block_from(block, block.index('blockoverride "badge" {')))
        tex = re.search(r'texture = "([^"]+)"', badge).group(1)
        self.assertEqual(self.doc["Overview row 2: bubble pressure"].get("crash risk"), tex)

    def test_the_cost_icon_is_listed(self):
        """Play-test round 3: the compact point-cost cell of every tool row."""
        row = _type_body(_read(DASH), "banking_dash_policy_row")
        cost = _block_from(row, row.index('block "cost_icon" {'))
        tex = re.search(r'texture = "([^"]+)"', cost).group(1)
        self.assertEqual(self.doc[DOC_SECTIONS[None]].get("cost"), tex)

    def test_no_row_names_a_state_the_overview_lacks(self):
        listed = {(s, k) for s, rows in self.doc.items() for k in rows}
        drawn = {(DOC_SECTIONS[p], k) for _, _, found, _ in _cells() for p, k, _ in found}
        drawn.add(("Overview row 2: bubble pressure", "crash risk"))
        drawn.add((DOC_SECTIONS[None], "cost"))
        self.assertEqual(listed, drawn)


BANKING_ICONS = "gfx/interface/icons/banking_icons/"
# PR #586's banking set, by the code or scripted GUI that picks each icon.
PHASE_ICONS = {p: f"{BANKING_ICONS}phase_{p}.dds"
               for p in ("panic", "downturn", "stagnation", "stable", "expansion", "boom", "frenzy")}
BAND_ICONS = {
    "banking_disp_bubble_band_code": ["bubble_low", "bubble_building", "bubble_elevated", "bubble_high",
                                      "bubble_severe"],
    "banking_disp_stance_band_code": ["stance_very_loose", "stance_loose", "stance_neutral", "stance_tight",
                                      "stance_very_tight"],
    "banking_disp_price_band_code": ["price_deflation", "price_stable", "price_elevated", "price_high",
                                     "price_very_high", "price_hyper", "price_dollarised", "price_planned"],
}
# Kept as vanilla's marks, as the icon list allowed. Freefall and Overheating,
# past the momentum bar's ends, borrow the double arrows until their own art
# exists (banking_gui_icons.md, placeholders).
# Momentum: vanilla's five arrows, and the mod's red triple arrows for the two outer bands.
MOMENTUM_ICONS = ["banking_icons/momentum_freefall", "generic_icons/down_down", "generic_icons/trend_down",
                  "generic_icons/trend_nochange", "generic_icons/trend_up", "generic_icons/trend_upup",
                  "banking_icons/momentum_overheating"]
VANILLA_KEPT = {f"gfx/interface/icons/{n}.dds" for n in MOMENTUM_ICONS + ["generic_icons/warning"]
                if n.startswith("generic_icons/")}


class BankingIconsTest(unittest.TestCase):
    """The banking GUI's own icons (PR #586) replace every placeholder."""

    def drawn(self):
        out = {}
        for _, _, found, _ in _cells():
            for picker, key, tex in found:
                out.setdefault(picker, {})[key] = tex
        return out

    def test_each_phase_draws_its_own_icon(self):
        self.assertEqual(self.drawn()["banking_dash_phase_"], PHASE_ICONS)

    def test_each_band_draws_its_own_icon(self):
        drawn = self.drawn()
        for value, names in BAND_ICONS.items():
            with self.subTest(value=value):
                self.assertEqual(drawn[value], {str(i): f"{BANKING_ICONS}{n}.dds" for i, n in enumerate(names, 1)})
        self.assertEqual(drawn["banking_disp_momentum_band_code"],
                         {str(i): f"gfx/interface/icons/{n}.dds" for i, n in enumerate(MOMENTUM_ICONS, 1)})

    def test_the_budget_and_the_cost_share_one_icon(self):
        self.assertEqual(self.drawn()[None], {"budget": f"{BANKING_ICONS}budget.dds"})
        row = _type_body(_read(DASH), "banking_dash_policy_row")
        self.assertIn(f'texture = "{BANKING_ICONS}budget.dds"', _block_from(row, row.index('block "cost_icon" {')))

    def test_no_placeholder_is_left(self):
        dash = _read(DASH)
        drawn = "".join(_type_body(dash, t) for t in ["te_banking_overview_panel", "banking_dash_policy_row",
                                                      "te_banking_crash_risk_badge"] + ICON_TYPES)
        for tex in re.findall(r'texture = "([^"]+)"', drawn):
            with self.subTest(texture=tex):
                self.assertTrue(tex.startswith(BANKING_ICONS) or tex in VANILLA_KEPT, tex)


MON_LABELS = ["banking_dash_mon_world_label", "banking_dash_mon_worldrate_label", "banking_dash_mon_rate_label",
              "banking_dash_mon_target_label", "banking_dash_mon_delegation_label", "banking_dash_mon_mandate_label",
              "banking_dash_mon_bankgold_label", "banking_dash_mon_goldgap_label", "banking_dash_mon_goldflow_label",
              "banking_dash_mon_hotmoney_label", "banking_dash_mon_pegconf_label",
              "banking_dash_mon_fx_label", "banking_dash_mon_fx_effect_label", "banking_dash_mon_anchor_label",
              "banking_dash_mon_backstops_label", "banking_dash_mon_union_label", "banking_dash_mon_paid_label",
              "banking_dash_mon_standing_label", "banking_dash_mon_premium_label", "banking_dash_mon_inflation_label",
              "banking_dash_mon_expected_label", "banking_dash_mon_wage_label", "banking_dash_mon_pressure_label",
              "banking_dash_mon_anchoring_label", "banking_dash_mon_monetise_label"]
CONCEPTS_FILE = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
CONCEPT_LOC = os.path.join(REPO, "localization", "english", "te_concepts_l_english.yml")


def _concept_loc():
    """All English loc: organize_loc files a concept's four-token name with the
    miscellaneous keys and its _desc with the concepts (its categorize_key)."""
    keys = {}
    loc_dir = os.path.dirname(CONCEPT_LOC)
    for name in sorted(os.listdir(loc_dir)):
        if not name.endswith(".yml"):
            continue
        for line in _read(os.path.join(loc_dir, name)).splitlines():
            m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*(?:#[^"]*)?$', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


class ShortPanelTest(unittest.TestCase):
    """Play-test round 2: a shorter panel. Readings that repeat the overview
    are gone from Monetary Policy, short related readings share a row, and the
    status text keeps only what the panels do not show."""

    def test_row_labels_are_concepts(self):
        loc, cloc = _loc(), _concept_loc()
        defined = set(re.findall(r"(?m)^(concept_\w+) = \{", _read(CONCEPTS_FILE)))
        captions = [c for _, c, _ in CELLS]
        for key in MON_LABELS + captions:
            with self.subTest(label=key):
                self.assertIn(key, _read(DASH))
                m = re.fullmatch(r"\[(?:(concept_\w+)|Concept\('(concept_\w+)','[^']+'\))\]", loc[key])
                self.assertTrue(m, f"{key} is not a concept link: {loc[key]}")
                concept = m.group(1) or m.group(2)
                self.assertIn(concept, defined)
                self.assertIn(concept, cloc)
                self.assertIn(concept + "_desc", cloc)

    def test_new_concepts_render_anywhere(self):
        """A concept's tooltip has no JournalEntry context: its text is static."""
        cloc = _concept_loc()
        for c in re.findall(r"(?m)^(concept_banking_\w+) = \{", _read(CONCEPTS_FILE)):
            for key in (c, c + "_desc"):
                self.assertNotIn("JournalEntry", cloc.get(key, ""), key)
                self.assertNotIn("ROOT", cloc.get(key, ""), key)

    def test_monetary_policy_does_not_repeat_the_overview(self):
        body = re.sub(r"#[^\n]*", "", _type_body(_read(DASH), "te_banking_sec_monetary"))
        for gone in ("banking_dash_mon_band_tt", "banking_dash_mon_stance_tt",
                     "banking_dash_mon_stance_impact_line", "banking_dash_mon_sub_bank"):
            self.assertNotIn(gone, body, gone)
        overview = _type_body(_read(DASH), "te_banking_overview_panel")
        for kept in ("banking_dash_mon_band_tt", "banking_dash_mon_stance_tt"):
            self.assertIn(kept, overview, kept)

    def test_short_readings_share_rows(self):
        body = _type_body(_read(DASH), "te_banking_sec_monetary")
        pairs = []
        for m in re.finditer(r"banking_dash_pair_row = \{", body):
            row = _block_from(body, m.end() - 1)
            pairs.append(re.findall(r'tooltip = "(banking_dash_mon_\w+_tt)"', row))
        self.assertEqual(pairs, [
            ["banking_dash_mon_world_tt", "banking_dash_mon_worldrate_tt"],
            ["banking_dash_mon_rate_tt", "banking_dash_mon_target_tt"],
            ["banking_dash_mon_standing_tt", "banking_dash_mon_premium_tt"],
            ["banking_dash_mon_inflation_tt", "banking_dash_mon_expected_tt"],
            ["banking_dash_mon_pressure_tt", "banking_dash_mon_wage_tt"],
        ])

    def test_the_dial_sits_together(self):
        """Delegation and mandate follow the rate target, before open-market
        operations; the delegate button shares the Delegation row."""
        body = _type_body(_read(DASH), "te_banking_sec_monetary")
        order = [body.index(k) for k in ('"banking_dash_mon_target_tt"', '"banking_dash_mon_delegation_tt"',
                                         '"banking_dash_mon_mandate_tt"', '"banking_dash_tt_cb_open_market_ops"',
                                         '"banking_dash_mon_sub_gold"')]
        self.assertEqual(order, sorted(order))
        row_at = body.rindex("flowcontainer = {", 0, body.index('tooltip = "banking_dash_mon_delegation_tt"'))
        row = _block_from(body, row_at)
        for btn in ("banking_dash_mon_btn_delegate", "banking_dash_mon_btn_take_control"):
            self.assertIn(btn, row)

    def test_every_row_fits_the_block(self):
        dash = _read(DASH)

        def widths(typ):
            return [int(w) for w in re.findall(r"size = \{ (\d+) \d+ \}", _type_body(dash, typ))]
        label, value = widths("banking_dash_pair")
        right_label, right_value = widths("banking_dash_pair_right")
        self.assertEqual(value, right_value)
        # two to a row: the left cell and the right cell fill the block's 460
        self.assertEqual((label + 4 + value) + (right_label + 4 + right_value), 460)
        self.assertEqual(widths("banking_dash_condition_row"), [label])
        self.assertIn("max_width = %d" % (460 - label - 4), _type_body(dash, "banking_dash_condition_value"))
        (mon_label,), (mon_value,) = widths("banking_dash_mon_label"), widths("banking_dash_mon_value")
        self.assertEqual(mon_label, label)
        (button,) = widths("banking_dash_mon_button")
        self.assertLessEqual(mon_label + 4 + mon_value + 4 + button, 460)  # the Delegation row
        body = _type_body(dash, "te_banking_sec_monetary")
        target = _block_from(body, body.index("flowcontainer = {", body.index('blockoverride "pair_right" {')))
        # The row's own cells: each stepper button sits in a slot of its size,
        # guarded inside it (another country's panel, te_own_country_only).
        parts = [gui_tree.size(c)[0] for c in gui_tree.widgets(gui_tree.parse("flowcontainer = " + target).children[0])]
        self.assertLessEqual(sum(parts) + 2 * (len(parts) - 1), right_label + 4 + right_value, parts)

    def test_status_text_is_empty_while_active(self):
        """The overview shows all it said: the readings as icons, and the
        three monthly modifier totals in the tooltips of the ranges under them
        (test_banking_monthly_change.py). The line the entry kept before its
        cycle started went too: every country holds the entry, and the dormant
        one's overview draws a Not Started cell with the conditions on hover
        (the banking always-on spec, 2026-10-17)."""
        je = _read(JE)
        self.assertNotIn("status_desc = {", je)
        self.assertNotIn("BANKING_CURR_MODIFIERS", _concept_loc())
        self.assertNotIn("banking_cycle_status_not_started", _loc())


# ---------------------------------------------------------------------------
# Play-test round 3: nothing a player reads may end in "...". Every label in a
# fixed-width cell must fit it by the width budget the coordinator measured
# from the owner's screenshots, in GUI units per character, plus 10%.
# ---------------------------------------------------------------------------
UNITS = {"large": 10.0, "medium": 8.6,
         # not measured: the medium/large ratio (0.86) applied once more
         "small": 7.4}
# The panel's own sizes (the banking_dash_fontsize_* templates at the head of
# the dashboard file), scaled from measured ones: the serif face at 10 a
# character in 20, and the overview's tooltip face at 8.6 in 16, measured from
# the owner's screenshot of 2026-10-17 at 1.5 px a unit. Its long lines ran
# 7.1 to 8.5 a character ("Bubble Pressure" 128 units, the widest); short
# words run wider ("Momentum" 11.5) but sit in columns with room to spare.
_SIZES = {m.group(1): int(m.group(2)) for m in re.finditer(
    r"template banking_dash_fontsize_(\w+) \{\s*fontsize = (\d+)", _read(DASH))}
UNITS.update(row=10.0 / 20 * _SIZES["row"], heading=10.0 / 20 * _SIZES["heading"],
             overview=8.6 / 16 * _SIZES["overview"])
MARGIN = 1.1
CUSTOM_LOC_DIR = os.path.join(REPO, "common", "customizable_localization")
# The longest a number printed in a cell can be, named per cell. Rates and
# pressures print one decimal and a sign ("-10.0%" is the widest a rate,
# premium or inflation reading reaches); monetisation is a level out of
# te_mon_monetisation_max (3); points are one or two digits.
NUMBER = "-10.0"
MONETISE = "3"


def _all_loc():
    """The mod's English loc over vanilla's (vanilla_parsed/), for the names
    of vanilla concepts such as [concept_infrastructure]."""
    with open(os.path.join(REPO, "vanilla_parsed", "localization_english.json"), encoding="utf-8") as f:
        keys = dict(json.load(f))
    loc_dir = os.path.dirname(LOC)
    for name in sorted(os.listdir(loc_dir)):
        if name.endswith(".yml"):
            for line in _read(os.path.join(loc_dir, name)).splitlines():
                m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*(?:#[^"]*)?$', line)
                if m:
                    keys[m.group(1)] = m.group(2)
    return keys


def _custom_options():
    """Every customizable-localization key's possible localization keys."""
    out = {}
    for name in sorted(os.listdir(CUSTOM_LOC_DIR)):
        text = _read(os.path.join(CUSTOM_LOC_DIR, name))
        for m in re.finditer(r"(?m)^(\w+) = \{", text):
            block = _block_from(text, m.end() - 1)
            out[m.group(1)] = re.findall(r"localization_key = (\w+)", block)
    return out


class WidthBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = _all_loc()
        cls.custom = _custom_options()
        cls.dash = _read(DASH)

    def shown(self, key, number=NUMBER, depth=0):
        """The widest text the key can show: splices and concepts resolved,
        formatting stripped, a customizable localization at its longest
        option, and any other data read at the cell's longest number."""
        v = self.loc.get(key)
        self.assertIsNotNone(v, key)
        return self._text(v, number, depth)

    def _text(self, v, number, depth):
        v = re.sub(r"\$(\w+)\$", lambda m: self.shown(m.group(1), number, depth + 1), v)
        v = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", r"\1", v)
        v = re.sub(r"\[(concept_\w+)\]", lambda m: self.shown(m.group(1), number, depth + 1), v)

        def custom(m):
            options = [self.shown(k, number, depth + 1) for k in self.custom[m.group(1)]]
            return max(options, key=len)
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
        """(max_width, font) of the textbox around `anchor` in `text`, read
        from the markup, so a narrower cell or a bigger font fails here."""
        at = text.index(anchor)
        start = text.rindex("textbox = {", 0, at)
        tb = _block_from(text, start + len("textbox = "))
        self.assertIn(anchor, tb)
        width = int(re.search(r"max_width = (\d+)", tb).group(1))
        font = re.search(r"using = (?:banking_dash_)?fontsize_(\w+)", tb).group(1)
        return width, font

    def type_box(self, typ, block):
        return self.box(_type_body(self.dash, typ), 'block "%s"' % block)

    def texts(self, block_name, body=None):
        body = self.dash if body is None else body
        return sorted(set(re.findall(r'blockoverride "%s" \{\s*text = "(\w+)"' % block_name, body)))

    def test_tool_names(self):
        """The owner: "a lot of the interventions ... are too long"."""
        names = self.texts("row_label")
        self.assertGreaterEqual(len(names), 40)
        cell = self.type_box("banking_dash_policy_row", "row_label")
        self.assertEqual(cell, (320, "row"))
        for key in names:
            with self.subTest(name=key):
                self.fits(key, cell)

    def test_directed_credit_rows_name_the_sector(self):
        available = _type_body(self.dash, "te_banking_sec_interventions")
        for sector, name in (("infrastructure", "Infrastructure"), ("heavy_industry", "Heavy Industry"),
                             ("agriculture", "Agriculture"), ("armaments", "Armaments"),
                             ("electrification", "Electrification")):
            key = "banking_dash_name_cb_directed_credit_" + sector
            self.assertIn('text = "%s"' % key, available)
            self.assertEqual(self.shown(key), name)
            self.assertIn("banking_dash_name_active_cb_directed_credit_" + sector,
                          _type_body(self.dash, "te_banking_sec_active"))
        self.assertEqual(self.shown("banking_dash_name_cb_countercyclical_buffer"), "Counter-cyclical Buffer")

    def test_costs_are_compact_and_the_full_requirement_is_on_hover(self):
        cell = self.type_box("banking_dash_policy_row", "row_cost")
        for key in self.texts("row_cost"):
            with self.subTest(cost=key):
                self.fits(key, cell)
                tool = key[len("banking_dash_cost_"):]
                tip = self.loc["banking_dash_tt_" + tool]
                if self.shown(key):
                    points = re.search(r"#title Requires:#! \$(\w+_POINTS_\d)\$", tip)
                    self.assertTrue(points, f"{tool}: no Requires line in the tooltip")
                    self.assertEqual(points.group(1)[-1], self.shown(key))
                else:   # the pool transfers: the cost is GDP, which their text states
                    self.assertIn("GDP", self.shown("banking_dash_tt_" + tool))

    def test_monetary_labels(self):
        for typ, block in (("banking_dash_condition_row", "condition_label"), ("banking_dash_pair", "pair_label"),
                           ("banking_dash_mon_label", "mon_label_text")):
            cell = self.type_box(typ, block)
            for key in self.texts(block):
                with self.subTest(label=key):
                    self.fits(key, cell)
        # The right half of a pair row is the narrower cell (144): hold its
        # labels, and only its labels, to it.
        right = self.type_box("banking_dash_pair_right", "pair_label")
        self.assertEqual(right, (144, "row"))
        rights = set()
        for m in re.finditer(r'blockoverride "pair_right" \{\s*banking_dash_pair_right = \{', self.dash):
            cell_block = _block_from(self.dash, m.end() - 1)
            rights.add(re.search(r'blockoverride "pair_label" \{\s*text = "(\w+)"', cell_block).group(1))
        # (the rate target is not a pair cell, and the Budget tab's readout shares the world rate's label)
        self.assertEqual(rights, {"banking_dash_mon_worldrate_label", "banking_dash_mon_premium_label",
                                  "banking_dash_mon_expected_label", "banking_dash_mon_wage_label"})
        for key in sorted(rights):
            with self.subTest(right_label=key):
                self.fits(key, right)
        body = _type_body(self.dash, "te_banking_sec_monetary")
        self.fits("banking_dash_mon_target_label", self.box(body, '"banking_dash_mon_target_label"'))
        self.assertEqual(self.shown("banking_dash_mon_anchoring_label"), "Anchoring")

    def test_monetary_values(self):
        for typ, block in (("banking_dash_pair", "pair_value"), ("banking_dash_mon_value", "mon_value_text")):
            cell = self.type_box(typ, block)
            for key in self.texts(block):
                with self.subTest(value=key):
                    self.fits(key, cell)
        body = _type_body(self.dash, "te_banking_sec_monetary")
        self.fits("banking_dash_mon_target_value", self.box(body, '"banking_dash_mon_target_value"'))
        self.fits("banking_dash_mon_monetise_value", self.box(body, '"banking_dash_mon_monetise_value"'),
                  number=MONETISE)
        # The two mandate rows take the width the row has free (#799):
        # "Inflation Targeting" and "Inflation Targeting Act" run past 160.
        for key in ("banking_dash_mon_mandate_value", "banking_dash_mon_act_value"):
            with self.subTest(value=key):
                self.fits(key, self.box(body, '"%s"' % key))
        value = self.dash[self.dash.index("type banking_dash_condition_value = textbox {"):]
        value = _block_from(value, value.index("{"))
        cell = (int(re.search(r"max_width = (\d+)", value).group(1)),
                re.search(r"using = (?:banking_dash_)?fontsize_(\w+)", value).group(1))
        # the Budget tab's read-only readout shares the type and the cell
        for where in (body, _type_body(self.dash, "te_banking_mon_readout")):
            for m in re.finditer(r"banking_dash_condition_value = \{", where):
                box = _block_from(where, m.end() - 1)
                if "multiline = yes" in box:
                    continue      # wraps rather than eliding
                key = re.search(r'text = "(\w+)"', box).group(1)
                with self.subTest(value=key):
                    self.fits(key, cell)

    def test_overview_cells(self):
        """Each cell's caption and words fit the column its own width leaves
        beside the icon (width - the lines' x - 6 of padding), in the
        overview's type. The type's word box is as wide as the widest column,
        so no cell's word is cut by it."""
        cap = _type_body(self.dash, "te_banking_ov_cell")
        self.assertIn("using = banking_dash_fontsize_overview", cap)
        x = int(re.search(r"position = \{ (\d+) 2 \}", cap).group(1))
        word = _type_body(self.dash, "te_banking_ov_word")
        self.assertIn("using = banking_dash_fontsize_overview", word)
        self.assertIn("position = { %d 24 }" % x, word)
        widest = int(re.search(r"max_width = (\d+)", word).group(1))
        words, columns = set(), []
        for tip, caption, _, block in _cells():
            width = int(re.search(r"size = \{ (\d+) \d+ \}", block).group(1))
            column = width - x - 6
            columns.append(column)
            declared = re.search(r'blockoverride "caption_width" \{\s*max_width = (\d+)', block)
            self.assertEqual(int(declared.group(1)), column, tip)
            with self.subTest(caption=caption):
                self.fits(caption, (column, "overview"))
            for key in re.findall(r'te_banking_ov_word = \{(?:[^{}]|\{[^{}]*\})*?text = "(\w+)"', block):
                words.add(key)
                with self.subTest(word=key):
                    self.fits(key, (column, "overview"))
        self.assertEqual(len(words), 15)   # seven phase words, five readings and three third lines
        self.assertEqual(widest, max(columns))
        # The dormant entry's cell: the same column, its word and third line.
        dormant = _dormant_row(_type_body(self.dash, "te_banking_overview_panel"))
        width = int(re.search(r"size = \{ (\d+) \d+ \}", dormant).group(1))
        keys = re.findall(r'te_banking_ov_word = \{(?:[^{}]|\{[^{}]*\})*?text = "(\w+)"', dormant)
        self.assertEqual(keys, ["banking_dash_not_started_value", "banking_dash_not_started_conditions"])
        for key in keys:
            with self.subTest(word=key):
                self.fits(key, (width - x - 6, "overview"))
        # the longest band word, named: the price band's
        self.assertEqual(self.shown("banking_dash_mon_band_value"), "Hyperinflation")

    def test_overview_change_lines(self):
        """The ranges on the cycle cells' third line (test_banking_monthly_change.py).
        The cycle value and bubble pressure print one decimal; momentum
        prints two, and its monthly change stays well inside +/-10 (a tenth of
        momentum decays, and the pushes come to a few points at most)."""
        body = _type_body(self.dash, "te_banking_overview_panel")
        box = _type_body(self.dash, "te_banking_ov_change_text")
        font = re.search(r"using = (?:banking_dash_)?fontsize_(\w+)", box).group(1)
        self.assertEqual(font, "overview")
        reach = int(re.search(r"max_width = (\d+)", box).group(1))
        line = _type_body(self.dash, "te_banking_ov_change")
        x, y = map(int, re.search(r"position = \{ (\d+) (\d+) \}", line).groups())
        width = int(re.search(r"size = \{ (\d+) 22 \}", line).group(1))
        self.assertEqual(y, 46)                           # the third line, under the word
        self.assertLessEqual(reach, width)                # the text stays inside the line
        self.assertLessEqual(x + width, 238 - 6)          # and the line inside its box
        keys = set()
        for m in re.finditer(r"te_banking_ov_change = \{", body):
            block = _block_from(body, m.end() - 1)
            self.assertNotIn("size =", block.split("blockoverride")[0])   # the type's size
            for key in re.findall(r'te_banking_ov_change_text = \{[^{}]*?text = "(\w+)"', block):
                keys.add(key)
                with self.subTest(line=key):
                    self.fits(key, (width, font), "-9.99" if "_momentum_" in key else NUMBER)
        self.assertEqual(len(keys), 10)   # four shapes each for value and momentum, two for bubble

    def test_buttons(self):
        """A button's label is in the large type (set on the button, as vanilla's
        states_panel.gui and power_bloc_panel.gui do beside default_button_action)."""
        types = {"banking_dash_mon_button": 140, "banking_dash_action_button": 90}
        for typ in types:
            self.assertIn("using = banking_dash_fontsize_row", _type_body(self.dash, typ))
        for typ, default in types.items():
            for m in re.finditer(r"\b%s = \{" % typ, self.dash):
                block = _block_from(self.dash, m.end() - 1)
                size = re.search(r"size = \{ (\d+) \d+ \}", block)
                key = re.search(r'text = "(\w+)"', block)
                if key is None:          # the type's own block slots
                    continue
                with self.subTest(button=key.group(1)):
                    self.fits(key.group(1), (int(size.group(1)) if size else default, "row"))
        for key in ("banking_dash_btn_enable", "banking_dash_btn_disable", "banking_dash_btn_execute"):
            self.fits(key, (90, "row"))



class BudgetPointsTest(unittest.TestCase):
    """The budget cell's "used" line is banking_display_points_total less the
    points free, so the total must list every grant of the budget, at its
    value (a law's modifier block, or a static modifier's)."""

    def test_the_total_lists_every_grant(self):
        sv = _read(os.path.join(REPO, "common", "script_values", "extra_script_values.txt"))
        start = sv.index("banking_display_points_total = {")
        total = _block_from(sv, sv.index("{", start))
        listed = dict(re.findall(r"has_law = law_type:(\w+) \} add = (\d+)", total))
        listed.update(re.findall(r"te_mon_mod_has = \{ NAME = (\w+) \} \} add = (\d+)", total))
        grants = {}
        for sub in ("laws", "static_modifiers"):
            folder = os.path.join(REPO, "common", sub)
            for name in sorted(os.listdir(folder)):
                text = _read(os.path.join(folder, name))
                for m in re.finditer(r"(?m)^country_banking_intervention_max_add|"
                                     r"^\t+country_banking_intervention_max_add = \+?([1-9]\d*)", text):
                    if m.group(1) is None:
                        continue
                    owner = re.findall(r"(?m)^(\w+) = \{", text[:m.start()])[-1]
                    grants[owner] = m.group(1)
        self.assertGreaterEqual(len(grants), 9)
        self.assertEqual(listed, grants)


def _child_blocks(inside):
    """The direct child blocks of a block's inside, each from its name to its
    closing brace, in order (comments included where they sit)."""
    out, depth, start = [], 0, 0
    for m in re.finditer(r"(?<![\w.])\w+ = \{|[{}]", inside):
        if m.group().endswith("{"):
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                out.append(inside[start:m.end()])
    return out


# What another country's Banking tab leaves out (spec 2026-11-02-charts-help-
# national-info § 6.4, Hidden): every control; r* and the estimation error,
# which no country is shown; and, by this PR's call, Available Interventions
# and the notes that tell the player how to start the cycle.
_SCRIPT_CLICK = re.compile(r"\b(?:onclick|ondefault|onctrl|onshift|onrightclick)\s*=\s*\"\[[^\"]*\.Execute\(")
_CONTROL_TYPES = re.compile(r"\b(?:banking_dash_action_button|banking_dash_mon_button|"
                            r"button_icon_minus_action|button_icon_plus_action)\s*=\s*\{")
_HIDDEN_VARS = re.compile(r"(?:\bvar:|\bVar\(\s*')(?:te_neutral_rate|te_neutral_error|te_mon_stance_gap)\b")
_SV_DIR = os.path.join(REPO, "common", "script_values")


class PrivateTest(unittest.TestCase):
    """National Info's Hidden items for Banking. Each sits under
    te_own_country_only, which draws only for the local player, so another
    country's tab shows the readings and none of these. GuardTest
    (test_te_system_tab_bodies.py) checks every control tab-wide; this pins
    the sections, and the parts that aren't controls."""

    def setUp(self):
        self.dash = _strip_comments(_read(DASH))

    def _unguarded(self, body, pattern):
        from gui_test_helpers import guard_spans, in_spans
        spans = guard_spans(body)
        found = list(pattern.finditer(body))
        # An instance's position is its opening brace, so a guard it carries
        # itself counts.
        return found, [body[m.start():m.start() + 90] for m in found if not in_spans(m.end() - 1, spans)]

    def test_each_control_is_the_players(self):
        """A click that runs a scripted GUI, and each control type's instance:
        the Monetary Policy tools, and Enable and Disable on every policy row
        (Active Policies keeps its rows, their slot empty). Available
        Interventions is all policy rows, under its own guard besides."""
        cases = [("te_banking_sec_monetary", _SCRIPT_CLICK, 15), ("te_banking_sec_monetary", _CONTROL_TYPES, 15),
                 ("banking_dash_policy_row", _CONTROL_TYPES, 2)]
        for name, pattern, least in cases:
            with self.subTest(type=name, pattern=pattern.pattern[:30]):
                found, loose = self._unguarded(_type_body(self.dash, name), pattern)
                self.assertGreaterEqual(len(found), least, "is the section still built this way?")
                self.assertEqual(loose, [], "a control another country would see")

    def test_available_interventions_is_the_players(self):
        """The whole section, guarded on its root; an instance that set its own
        visible would lose the guard (gotcha #17)."""
        from gui_test_helpers import GUARD, own_props
        body = _type_body(self.dash, "te_banking_sec_interventions")
        self.assertRegex(own_props(body), rf"\busing\s*=\s*{GUARD}\b")
        layout = _strip_comments(_read(LAYOUT))
        instances = [m.start() for m in re.finditer(r"\bte_banking_sec_interventions\s*=\s*\{", layout)]
        self.assertEqual(len(instances), 2, "the narrow composer and the wide column")
        for at in instances:
            self.assertNotIn("visible", _block_from(layout, at))

    def test_the_start_notes_are_the_players(self):
        """The notes under Monetary Policy and Available Interventions say
        what starts the cycle, with the player's checklist on hover."""
        for name, key in (("te_banking_sec_monetary", "banking_dash_dormant_monetary_note"),
                          ("te_banking_sec_interventions", "banking_dash_dormant_tools_note")):
            with self.subTest(note=key):
                body = _type_body(self.dash, name)
                found, loose = self._unguarded(body, re.compile(rf"text\s*=\s*\"{key}\""))
                self.assertEqual(len(found), 1)
                self.assertEqual(loose, [])

    def test_nothing_draws_r_star_or_the_error(self):
        """The neutral rate, its estimation error and the gap between them
        (monetary_policy_design.md § 8): no Banking GUI, no loc key it names
        (splices followed) and no script value reads one, whoever's tab it is.
        Testing that a variable exists reads nothing."""
        loc = _loc()
        sv_text = "\n".join(_strip_comments(_read(os.path.join(_SV_DIR, f))) for f in sorted(os.listdir(_SV_DIR))
                            if f.endswith(".txt"))
        values = {m.group(1): m.start() for m in re.finditer(r"(?m)^(\w+)\s*=\s*\{", sv_text)}
        gui = "".join(_strip_comments(_read(p)) for p in (DASH, LAYOUT, HIST))
        self.assertIsNone(_HIDDEN_VARS.search(gui))
        words, keys, svs = re.findall(r"\w+", gui), set(), set()
        while words:
            w = words.pop()
            if w in loc and w not in keys:
                keys.add(w)
                self.assertIsNone(_HIDDEN_VARS.search(loc[w]), w)
                words += re.findall(r"\w+", loc[w])
            elif w in values and w not in svs:
                svs.add(w)
                block = _block_from(sv_text, values[w])
                self.assertIsNone(_HIDDEN_VARS.search(block), w)
                words += re.findall(r"\w+", block)
        self.assertGreater(len(keys), 300)
        self.assertGreater(len(svs), 50)

    # The other half (spec § 6.4, Shown): another country's tab still draws the
    # cycle's phase, momentum and bubble, the four bars, Monetary Policy's
    # readings, the interventions in force and the history, and the readout for
    # a country without the entry (which National Info draws beside the wide
    # sections). Over-guarding passes every test above.
    SHOWN = ("te_banking_overview_panel", "te_banking_bars", "te_banking_phase_icons", "te_banking_momentum_icons",
             "te_banking_bubble_icons", "te_banking_sec_active", "banking_dash_policy_row", "te_banking_sec_monetary",
             "banking_dash_mon_value", "te_banking_history_panel", "te_banking_history_charts", "te_hist_bank_value",
             "te_hist_bank_momentum", "te_hist_bank_bubble", "te_hist_mon_policy", "te_hist_mon_inflation",
             "te_hist_mon_fx")
    SHOWN_KEYS = ("banking_cycle_value_bar_desc", "banking_cycle_value_bar_second", "banking_cycle_momentum_bar_name",
                  "banking_policy_stance_bar_name", "banking_bubble_pressure_bar_name", "banking_dash_phase_boom_value",
                  "banking_dash_mon_rate_label", "banking_dash_mon_inflation_label", "banking_dash_mon_fx_label",
                  "banking_dash_active_header",
                  "banking_dash_name_active_cb_bank_holiday", "te_hist_chart_bank_value_title",
                  "te_hist_chart_mon_policy_title", "banking_dash_not_started_other_tt",
                  # the overview's stance and price-band cells, whose keys nothing else names
                  "banking_dash_mon_stance_tt", "banking_dash_mon_stance_label", "banking_dash_mon_stance_value",
                  "banking_dash_mon_stance_word_tt", "banking_dash_ov_rate_line", "banking_dash_mon_band_value",
                  "banking_dash_mon_band_word_tt", "banking_dash_ov_inflation_line")

    def test_what_another_country_still_sees(self):
        """The Shown types are drawn (panel_view, the walk BindingTest makes),
        none guarded on its root; the four bars and every Active Policies row
        outside any guard; the readings' keys in what the panel renders
        (panel_loc_keys). Mutation-checked: a guard on te_banking_bars or
        te_banking_sec_active fails this and nothing else."""
        from gui_test_helpers import guard_spans, in_spans, load_loc, mod_types, panel_loc_keys, panel_view
        types = mod_types()
        view = panel_view({"te_banking_wide_sections"}, types)
        for name in self.SHOWN:
            with self.subTest(type=name):
                self.assertIn(name, view.open)
                self.assertNotIn((0, len(types[name].body)), view.skip[name], "guarded on its root")
        # every bar and every Active Policies row, not just their types
        bars = types["te_banking_bars"].body
        # four bars; the three with a marker read their value twice (1.15's markup)
        self.assertEqual(len(set(re.findall(r"ScriptValue\('(banking_disp_bar_\w+)'\)", bars))), 4)
        self.assertEqual(view.skip["te_banking_bars"], [])
        active = types["te_banking_sec_active"].body
        rows = [m.end() - 1 for m in re.finditer(r"\bbanking_dash_policy_row\s*=\s*\{", active)]
        self.assertGreater(len(rows), 30)
        self.assertEqual([r for r in rows if in_spans(r, view.skip["te_banking_sec_active"])], [])
        row = types["banking_dash_policy_row"].body
        for part in ('block "row_label"', 'block "row_cost"'):
            self.assertFalse(in_spans(row.index(part), guard_spans(row)), part)
        loc = load_loc()
        keys = panel_loc_keys({"te_banking_wide_sections"}, types, loc)
        for key in self.SHOWN_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, keys)
        readout = panel_view({"te_banking_mon_readout"}, types)
        self.assertNotIn((0, len(types["te_banking_mon_readout"].body)), readout.skip["te_banking_mon_readout"])
        self.assertIn("banking_dash_ro_entry_name", panel_loc_keys({"te_banking_mon_readout"}, types, loc))
        # each overview cell, by its tooltip
        overview = types["te_banking_overview_panel"].body
        for tooltip, _, _ in CELLS:
            with self.subTest(cell=tooltip):
                at = overview.index(f'tooltip = "{tooltip}"')
                self.assertFalse(in_spans(at, view.skip["te_banking_overview_panel"]), "the cell is guarded")

    def test_nothing_shown_is_hidden_inline(self):
        """The guard is the one way to keep a part from another country, so the
        Shown half above sees it. A visible that asks Country.IsLocalPlayer
        itself may only gate a wrapper whose every child is under the guard
        (the gap-free wrappers: the dormant note, the mandate grid,
        Recapitalize, the union buttons), or one of a pair that swaps by viewer,
        a sibling for another country beside it (a chart's open button: the
        player's viewer, or National Info's). Not( Country.IsLocalPlayer )
        shows a part to another country, and SelectLocalization's first
        argument picks text; both are fine."""
        from gui_test_helpers import GUARD, enclosing_block, mod_types, panel_view
        types = mod_types()
        view = panel_view({"te_banking_wide_sections"}, types)
        allowed = pairs = 0
        other = re.compile(r'^\w+ = \{\s*visible = "\[Not\( Country\.IsLocalPlayer \)\]"')
        for name in sorted(view.open):
            body = types[name].body
            for m in re.finditer(r"Country\.IsLocalPlayer", body):
                if any(a <= m.start() <= b for a, b in view.skip[name]):
                    continue
                before = body[max(0, m.start() - 40):m.start()]
                if re.search(r"(?:SelectLocalization|AddLocalizationIf)\(\s*$", before) or re.search(r"Not\(\s*$", before):
                    continue
                line = body[body.rindex("\n", 0, m.start()) + 1:body.index("\n", m.start())]
                with self.subTest(type=name, line=line.strip()[:90]):
                    self.assertRegex(line, r"^\s*visible\s*=", "Country.IsLocalPlayer outside a visible: use the guard")
                    a, b = enclosing_block(body, m.start())
                    if line.strip() == 'visible = "[Country.IsLocalPlayer]"':
                        pa, pb = enclosing_block(body, a)
                        if any(other.match(c) for c in _child_blocks(body[pa + 1:pb])):
                            pairs += 1
                            continue
                    children = _child_blocks(body[a + 1:b])
                    self.assertTrue(children, "a gate with nothing under it")
                    for child in children:
                        self.assertRegex(child, rf"^\w+ = \{{\s*(?:#[^\n]*\s*)*using = {GUARD}\b",
                                         "a part another country should see, hidden inline: guard only the player's parts")
                    allowed += 1
        self.assertEqual(allowed, 4, "the four gap-free wrappers")
        self.assertGreaterEqual(pairs, 8, "the history charts' open buttons")


class BlocLeaderRowTest(unittest.TestCase):
    """The union's "received from the leader" row, the one row whose country
    shadows the panel's (spec 2026-11-02-charts-help-national-info § 6.3). Its
    visible and its value read the shown member; only the flag and the name
    read the bloc's leader. On the row, the leader's datacontext would be the
    Country they read, and the leader receives nothing, so a member's row would
    vanish; te_rebind_country.py sees nothing either way (every read is Country)."""

    LEADER = 'datacontext = "[Country.GetPowerBloc.GetLeader]"'

    def test_the_leader_is_the_flag_and_name_only(self):
        from gui_test_helpers import own_props
        dash = _strip_comments(_read(DASH))
        rows = [_block_from(dash, m.start()) for m in re.finditer(r"\bbanking_dash_partner_row\s*=\s*\{", dash)]
        rows = [r[1:-1] for r in rows if "te_mon_bs_union_received_display" in own_props(r[1:-1])]
        self.assertEqual(len(rows), 1, "the row whose visible reads te_mon_bs_union_received_display")
        row = rows[0]
        self.assertNotRegex(own_props(row), r"\bdatacontext\s*=", "a datacontext on the row shadows its visible")
        self.assertRegex(own_props(row), r"visible = \"\[And\( Country\.IsInPowerBloc, ")
        for name in ("flag", "name"):
            with self.subTest(block=name):
                block = _block_from(row, re.search(rf'blockoverride "{name}"\s*\{{', row).start())
                self.assertIn(self.LEADER, block)
        value = _block_from(row, re.search(r'blockoverride "value"\s*\{', row).start())
        self.assertNotIn("datacontext", value)
        self.assertIn("banking_dash_mon_bs_union_from", value)


PROGRESS_BARS = os.path.join(REPO, "common", "scripted_progress_bars", "extra_progress_bars.txt")
BAR_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "banking_cycle_effects.txt")
# The entry's bar look -> the progress bar te_banking_bars draws it with: a ready-made
# look (default_green = yes, default_bad = yes) or, for a bar that declares its own
# textures (1.15), the bar type whose fill is its progress_texture.
BAR_VARIANTS = {"default_green": "green_progressbar_horizontal", "default_bad": "bad_progressbar_horizontal"}
PROGRESS_TEXTURE_BARS = {
    "gfx/interface/progressbar/progressbar_default.dds": "default_progressbar_horizontal",
    "gfx/interface/progressbar/progressbar_green.dds": "green_progressbar_horizontal",
    "gfx/interface/progressbar/progressbar_bad.dds": "bad_progressbar_horizontal",
    "gfx/interface/progressbar/progressbar_gold.dds": "gold_progressbar_horizontal",
    "gfx/interface/progressbar/progressbar_white.dds": "white_progressbar_horizontal",
}
DRAWN_BARS = set(BAR_VARIANTS.values()) | set(PROGRESS_TEXTURE_BARS.values())


def _num(x):
    return float(x)


class BarsTest(unittest.TestCase):
    """te_banking_bars, another country's four bars (National Info), draws what
    the entry's scripted bars draw for the player: bar i is the entry's i-th
    scripted_progress_bar (je_banking.txt), in its variant, with its desc and
    second_desc, at its own banking_disp_bar_* value, which runs from the
    bar's min_value to its max_value over 0 to 1, starts where the bar does,
    and reads the variable banking_cycle_update_progress_bars sets the bar from."""

    @classmethod
    def setUpClass(cls):
        text = _strip_comments(_read(PROGRESS_BARS))
        cls.defs = {}
        for m in re.finditer(r"(?m)^(\w+) = \{", text):
            body = _block_from(text, m.end() - 1)
            get = lambda key: (re.search(rf"\b{key}\s*=\s*\"?([\w.\-]+)\"?", body) or [None, None])[1]
            texture = lambda key: (re.search(rf'\b{key}\s*=\s*"([^"]+)"', body) or [None, None])[1]
            variant = [v for v in BAR_VARIANTS if re.search(rf"\b{v}\s*=\s*yes", body)]
            if texture("progress_texture"):
                variant.append("own_look")
            cls.defs[m.group(1)] = {
                "variant": variant,
                "progress": texture("progress_texture"), "background": texture("background_texture"),
                "marker": bool(re.search(r"\bmarker\s*=\s*yes", body)),
                "start": _num(get("start_value")), "min": _num(get("min_value")), "max": _num(get("max_value")),
                "desc": get("desc"), "second": get("second_desc")}
        cls.order = re.findall(r"scripted_progress_bar = (\w+)", _strip_comments(_read(JE)))
        effects = _strip_comments(_read(BAR_EFFECTS))
        update = _block_from(effects, effects.index("banking_cycle_update_progress_bars = {"))
        cls.sets = {}
        for m in re.finditer(r"set_bar_progress = \{ name = (\w+) value = ([^}]*?) \}", update):
            cls.sets.setdefault(m.group(1), set()).update(re.findall(r"var:(\w+)", m.group(2)))
        cls.containers = [c for c in _child_blocks(_type_body(_strip_comments(_read(DASH)), "te_banking_bars"))]
        cls.values = _strip_comments(_read(DISP))

    def test_the_entrys_bars_in_its_order(self):
        self.assertEqual(len(self.order), 4)
        self.assertEqual(len(self.containers), len(self.order))
        self.assertEqual(set(self.sets), set(self.order), "banking_cycle_update_progress_bars sets every bar")

    def test_each_bar(self):
        used = []
        for i, (bar, box) in enumerate(zip(self.order, self.containers)):
            d = self.defs[bar]
            with self.subTest(bar=bar, position=i):
                self.assertEqual(len(d["variant"]), 1)
                drawn = [v for v in sorted(DRAWN_BARS) if re.search(rf"\b{v}\s*=\s*\{{", box)]
                if d["variant"] == ["own_look"]:
                    self.assertEqual(drawn, [PROGRESS_TEXTURE_BARS[d["progress"]]], "the bar's fill")
                    if d["background"]:
                        self.assertIn(f'noprogresstexture = "{d["background"]}"', box)
                    self.assertEqual("progressbar_marker.dds" in box, d["marker"], "the marker")
                else:
                    self.assertEqual(drawn, [BAR_VARIANTS[d["variant"][0]]], "the bar's look")
                    self.assertNotIn("progressbar_marker.dds", box)
                self.assertEqual(re.findall(r'text = "([\w.\-]+)"', box), [d["desc"]] + ([d["second"]] if d["second"] else []))
                # the marker overlay reads the bar's value too (1.15's markup)
                values = sorted(set(re.findall(r"ScriptValue\('(banking_disp_bar_\w+)'\)", box)))
                self.assertEqual(len(values), 1)
                used.append(values[0])
                self._check_value(values[0], d, self.sets[bar])
        self.assertEqual(len(set(used)), 4, "each bar its own value")

    def _check_value(self, name, d, variables):
        at = re.search(rf"(?m)^{name} = \{{", self.values)
        self.assertTrue(at, f"no script value {name}")
        body = _block_from(self.values, at.end() - 1)
        span = d["max"] - d["min"]
        lines = [ln.strip() for ln in body.strip("{} \n").split("\n") if ln.strip()]
        self.assertEqual(lines[0], f"value = {(d['start'] - d['min']) / span:g}", f"{name}: the bar's start")
        self.assertEqual(lines[-2:], ["min = 0", "max = 1"], f"{name}: clamped to the bar")
        branch = _block_from(body, body.index("if = {"))
        var = re.search(r"limit = \{ has_variable = (\w+) \}", branch).group(1)
        self.assertIn(var, variables, f"{name} reads {var}, not what the entry's bar is set from")
        ops = re.findall(r"^\s*(value|add|divide|multiply|subtract) = (\S+)$", branch, re.M)
        want = [("value", f"var:{var}")] + ([("add", f"{-d['min']:g}")] if d["min"] else []) + \
               ([("divide", f"{span:g}")] if span != 1 else [])
        self.assertEqual(ops, want, f"{name}: (var - min) / (max - min)")


class ScriptedTooltipTest(unittest.TestCase):
    """Text a scripted GUI prints through ExecuteTooltip, IsValidTooltip or
    IsShownTooltip was invisible to BindingTest and te_rebind_country.py when
    this was written; both follow it since #1361, and this holds it by name. What
    another country's panel prints that way (the history markers' lines,
    te_hist_tt_markers) speaks of no one and reads neither the player nor the
    entry; the keys that still read GetPlayer print only under the guard."""

    PRINT = re.compile(r"(?:GetScriptedGui\(\s*'(\w+)'\s*\)|ScriptedGui)\.(?:ExecuteTooltip|IsValidTooltip|IsShownTooltip)\b")
    KEY = re.compile(r"\b(?:custom_tooltip|text|desc|tooltip)\s*=\s*\"?([\w.\-]+)\"?")
    PLAYER_KEYS = ("banking_mon_recapitalise_tt", "banking_mon_tt_can_monetise", "banking_mon_tt_mandate_unlocked",
                   "banking_mon_tt_mandate_locked")

    @classmethod
    def setUpClass(cls):
        from gui_test_helpers import load_loc, mod_types
        cls.types, cls.loc = mod_types(), load_loc()
        cls.defs = {}
        for sub in ("scripted_guis", "scripted_effects", "scripted_triggers"):
            folder = os.path.join(REPO, "common", sub)
            for f in sorted(os.listdir(folder)):
                text = _strip_comments(_read(os.path.join(folder, f)))
                for m in re.finditer(r"(?m)^(\w+) = \{", text):
                    cls.defs[m.group(1)] = _block_from(text, m.end() - 1)

    def _printed(self, sguis):
        """The loc keys the scripted GUIs' bodies name, through every scripted
        effect and trigger they call, with what those keys splice and render."""
        from gui_test_helpers import loc_closure
        seen, todo, keys = set(), list(sguis), set()
        while todo:
            name = todo.pop()
            if name in seen or name not in self.defs:
                continue
            seen.add(name)
            body = self.defs[name]
            keys |= {k for k in self.KEY.findall(body) if k in self.loc}
            todo += [w for w in set(re.findall(r"\b\w+\b", body)) if w in self.defs and w not in seen]
        return loc_closure(keys, self.loc)

    def _public_sguis(self, names):
        """The scripted GUIs another country's panel prints a tooltip of: in the
        parts it draws (none so far), and in the keys it renders."""
        from gui_test_helpers import _OWN_BRANCH, _drawn, panel_loc_keys
        out, inline = set(), []
        for where, td, spans in _drawn(names, self.types):
            from gui_test_helpers import unguarded
            inline += [(where, m.group(0)) for m in self.PRINT.finditer(unguarded(td.body, spans))]
        for key in panel_loc_keys(names, self.types, self.loc):
            out |= {m.group(1) for m in self.PRINT.finditer(_OWN_BRANCH.sub(r"\1''", self.loc[key])) if m.group(1)}
        return out, inline

    def test_what_another_country_prints_is_neutral(self):
        from gui_test_helpers import PERSONAL
        for names in ({"te_banking_wide_sections"}, {"te_banking_mon_readout"}):
            sguis, inline = self._public_sguis(names)
            self.assertEqual(inline, [], "a scripted GUI's tooltip printed in another country's markup: "
                                         "check what it prints, then extend this test")
            if names == {"te_banking_wide_sections"}:
                self.assertEqual(sguis, {"te_history_marker_tooltip"})
            keys = self._printed(sguis)
            for key in sorted(keys):
                text = self.loc[key]
                with self.subTest(key=key):
                    self.assertNotRegex(text, r"GetPlayer|AccessPlayer|JournalEntry\.")
                    self.assertIsNone(PERSONAL.search(re.sub(r"\[[^\]]*\]|\$[\w.\-]+\$|#\w+|\\n", " ", text)))
            if sguis:
                self.assertGreater(len(keys), 30)

    def test_the_player_keys_print_under_the_guard(self):
        gui = "".join(_read(p) for p in BANKING_GUI)
        everything = self._printed(set(re.findall(r"GetScriptedGui\(\s*'(\w+)'", gui)))
        public = set()
        for names in ({"te_banking_wide_sections"}, {"te_banking_mon_readout"}):
            public |= self._printed(self._public_sguis(names)[0])
        for key in self.PLAYER_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, everything, "a Banking scripted GUI prints it")
                self.assertIn("GetPlayer", self.loc[key])
                self.assertNotIn(key, public)
        reads_player = sorted(k for k in everything if re.search(r"GetPlayer|JournalEntry\.", self.loc[k]))
        self.assertEqual([k for k in reads_player if k not in self.PLAYER_KEYS and k != "je_banking_cycle"], [],
                         "a new key reading the player in a scripted GUI's text: guard where it prints, or bind it")


if __name__ == "__main__":
    unittest.main()
