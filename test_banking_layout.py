"""The banking panels' section order, collapse defaults and state gates.

Style-guide pass, 2026-09-29 (docs/guides/gui_style_guide.md), in the spirit
of test_un_layout.py: one layout for the journal entry and the Budget tab, an
overview on top, the live sections open, the history and How Banking Works
at the foot, and every collapse flag named for its default.
"""
import json
import os
import re
import unittest

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

STATUS = ["te_banking_sec_active", "te_banking_sec_monetary", "te_banking_sec_interventions"]
REFERENCE = ["te_banking_history_panel", "te_banking_sec_how"]
# Available Interventions' categories, by the economic system that shows them.
CATEGORIES = {
    "banking_dash_system_market": ["prudential", "credit", "external", "crisis"],
    "banking_dash_system_command": ["plan", "allocation", "admin", "pool"],
    "banking_dash_system_coop": ["surplus", "investment", "council", "membership"],
}
MONETARY_HOW = ["banking_dash_how_rate", "banking_dash_how_stance", "banking_dash_how_borrowing"]
GENERAL_HOW = ["banking_dash_how_cycle", "banking_dash_how_cycle_moves", "banking_dash_how_crashes",
               "banking_dash_how_budget"]


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
        m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2)
    return keys


def _tab_block():
    text = _read(BUDGET)
    start = text.index('name = "te_budget_banking_tab"')
    return text[start:text.index("### END MOD ###", start)]


class OrderTest(unittest.TestCase):
    def test_status_order(self):
        body = _type_body(_read(LAYOUT), "te_banking_status_sections")
        self.assertEqual(re.findall(r"^\t\t(te_banking_\w+) = \{", body, re.M), STATUS)

    def test_reference_order_history_then_how(self):
        body = _type_body(_read(LAYOUT), "te_banking_reference_sections")
        self.assertEqual(re.findall(r"^\t\t(te_banking_\w+) = \{", body, re.M), REFERENCE)
        # one open history shell for both hosts (play-test round 2): no swap left
        self.assertNotIn("block ", body)

    def test_composers_and_roots_are_gated_on_an_active_entry(self):
        layout = _read(LAYOUT)
        for composer in ("te_banking_status_sections", "te_banking_reference_sections"):
            self.assertIn('visible = "[JournalEntry.IsActive]"', _type_body(layout, composer), composer)
        self.assertIn('visible = "[JournalEntry.IsActive]"', _type_body(_read(DASH), "te_banking_overview_panel"))
        roots = re.findall(r'name = "(widget_je_banking_\w+)"\s*visible = "\[JournalEntry\.IsActive\]"', layout)
        self.assertEqual(roots, ["widget_je_banking_overview", "widget_je_banking_status",
                                 "widget_je_banking_reference"])

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
            r"\b(te_banking_overview_panel|te_banking_status_sections|te_banking_reference_sections"
            r"|te_system_tab_open_journal)\b", tab)]
        self.assertEqual(order, ["te_banking_overview_panel", "te_banking_status_sections",
                                 "te_banking_reference_sections", "te_system_tab_open_journal"])
        self.assertIn("te_banking_reference_sections = {}", tab)

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


class FlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = "\n".join(_read(p) for p in BANKING_GUI)

    def test_section_flags_say_their_default(self):
        flags = {f for f in re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.text)
                 if f.startswith(("banking_", "te_banking_", "te_hist_"))}
        self.assertGreaterEqual(len(flags), 16)
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

    def test_the_live_sections_start_open_and_how_it_works_collapsed(self):
        dash = _read(DASH)
        for sec, flag in (("te_banking_sec_active", "banking_dash_active_closed"),
                          ("te_banking_sec_monetary", "banking_dash_monetary_closed")):
            self.assertIn(f"Toggle('{flag}')", _type_body(dash, sec), sec)
        self.assertIn("Toggle('banking_dash_how_open')", _type_body(_read(LAYOUT), "te_banking_sec_how"))


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
        body = _type_body(_read(LAYOUT), "te_banking_sec_how")
        m = re.search(r"flowcontainer = \{\s*visible = \"\[GetScriptedGui\('banking_mon_system_shown'\)", body)
        self.assertTrue(m, "no monetary block gated on banking_mon_system_shown")
        gated = _block_from(body, m.start())
        for key in MONETARY_HOW:
            self.assertIn(f'text = "{key}"', gated, key)
        for key in GENERAL_HOW:
            self.assertIn(f'text = "{key}"', body, key)
            self.assertNotIn(f'text = "{key}"', gated, key)


class TidyTest(unittest.TestCase):
    def test_labels_with_a_tooltip_look_hoverable(self):
        dash = _read(DASH)
        for typ, block in (("banking_dash_condition_row", "condition_label"),
                           ("banking_dash_mon_label", "mon_label_text"),
                           ("banking_dash_policy_row", "row_label")):
            self.assertRegex(_type_body(dash, typ),
                             rf'default_format = "#tooltippable"\s*block "{block}"', typ)

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
        for path, key in ((DASH, "banking_dash_mon_sub_rates"), (LAYOUT, "banking_dash_how_sub_cycle")):
            text = _read(path)
            first = text.index("banking_dash_subheader = {", text.index("type te_banking_sec_"))
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
    ("banking_dash_mon_stance_tt", "banking_dash_mon_stance_label", "banking_disp_stance_band_code"),
    ("banking_dash_mon_band_tt", "banking_dash_mon_inflation_label", "banking_disp_price_band_code"),
    ("banking_dash_budget_tt", "banking_dash_budget_label", None),
]
DOC_SECTIONS = {
    "banking_dash_phase_": "Overview row 1: cycle phase",
    "banking_disp_momentum_band_code": "Overview row 1: momentum",
    "banking_disp_bubble_band_code": "Overview row 1: bubble pressure",
    "banking_disp_stance_band_code": "Overview row 2: policy stance",
    "banking_disp_price_band_code": "Overview row 2: inflation (the price band)",
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


def _cells():
    """(tooltip, caption, [(picker, key, texture)], block) per overview cell."""
    dash = _read(DASH)
    body = _type_body(dash, "te_banking_overview_panel")
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
        dash = _read(DASH)
        cell = _type_body(dash, "te_banking_ov_cell")
        w = int(re.search(r"size = \{ (\d+) \d+ \}", cell).group(1))
        body = _type_body(dash, "te_banking_overview_panel")
        self.assertRegex(body, r"(?m)^\t\tmargin = \{ 10 8 \}")   # 10 + 480 bars + 10 = 500
        header = _type_body(dash, "banking_dash_category_header")
        self.assertIn("size = { 500 32 }", header)
        change = _type_body(dash, "te_banking_ov_change")
        self.assertEqual(int(re.search(r"size = \{ (\d+) \d+ \}", change).group(1)), w)
        rows = 0
        for m in re.finditer(r"flowcontainer = \{\s*direction = horizontal", body):
            row = _block_from(body, m.start())
            n = len(re.findall(r"te_banking_ov_(?:cell|change) = \{", row))
            if not n:
                continue
            rows += 1
            spacing = int(re.search(r"spacing = (\d+)", row).group(1))
            self.assertLessEqual(n * w + (n - 1) * spacing, 480, row[:80])
        self.assertEqual(rows, 3)   # the readings, their changes, what the player sets
        for textbox in re.findall(r"max_width = (\d+)", cell) + \
                re.findall(r"max_width = (\d+)", _type_body(dash, "te_banking_ov_word")):
            self.assertLessEqual(int(textbox), w)


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
        self.assertEqual(self.doc["Overview row 1: bubble pressure"].get("crash risk"), tex)

    def test_the_cost_icon_is_listed(self):
        """Play-test round 3: the compact point-cost cell of every tool row."""
        row = _type_body(_read(DASH), "banking_dash_policy_row")
        cost = _block_from(row, row.index('block "cost_icon" {'))
        tex = re.search(r'texture = "([^"]+)"', cost).group(1)
        self.assertEqual(self.doc[DOC_SECTIONS[None]].get("cost"), tex)

    def test_no_row_names_a_state_the_overview_lacks(self):
        listed = {(s, k) for s, rows in self.doc.items() for k in rows}
        drawn = {(DOC_SECTIONS[p], k) for _, _, found, _ in _cells() for p, k, _ in found}
        drawn.add(("Overview row 1: bubble pressure", "crash risk"))
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
MOMENTUM_ICONS = ["down_down", "down_down", "trend_down", "trend_nochange", "trend_up", "trend_upup", "trend_upup"]
VANILLA_KEPT = {f"gfx/interface/icons/generic_icons/{n}.dds" for n in MOMENTUM_ICONS + ["warning"]}


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
                         {str(i): f"gfx/interface/icons/generic_icons/{n}.dds" for i, n in enumerate(MOMENTUM_ICONS, 1)})

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
            m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
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
            ["banking_dash_mon_wage_tt", "banking_dash_mon_pressure_tt"],
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
        self.assertEqual(label + 4 + value, 230)                     # two to a row: 460
        self.assertEqual(widths("banking_dash_condition_row"), [label])
        self.assertIn("max_width = %d" % (460 - label - 4), _type_body(dash, "banking_dash_condition_value"))
        (mon_label,), (mon_value,) = widths("banking_dash_mon_label"), widths("banking_dash_mon_value")
        (button,) = widths("banking_dash_mon_button")
        self.assertLessEqual(mon_label + 4 + mon_value + 4 + button, 460)  # the Delegation row
        body = _type_body(dash, "te_banking_sec_monetary")
        target = _block_from(body, body.index("flowcontainer = {", body.index('blockoverride "pair_right" {')))
        parts = [int(w) for w in re.findall(r"size = \{ (\d+) \d+ \}", target)]
        self.assertLessEqual(sum(parts) + 2 * (len(parts) - 1), 230, parts)

    def test_status_text_is_empty_while_active(self):
        """The overview shows all it said: the readings as icons, and the
        three monthly modifier totals in the tooltips of the ranges under them
        (test_banking_monthly_change.py). One line remains for the entry
        before it starts, when the overview draws nothing."""
        je = _read(JE)
        status = _block_from(je, je.index("status_desc = {"))
        self.assertEqual(re.findall(r"desc = (\w+)", status), ["banking_cycle_status_not_started"])
        self.assertIn("NOT = { has_variable = finance_cycle_value }", status)
        self.assertNotIn("BANKING_CURR_MODIFIERS", _concept_loc())
        self.assertIn("banking_cycle_status_not_started", _loc())


# ---------------------------------------------------------------------------
# Play-test round 3: nothing a player reads may end in "...". Every label in a
# fixed-width cell must fit it by the width budget the coordinator measured
# from the owner's screenshots, in GUI units per character, plus 10%.
# ---------------------------------------------------------------------------
UNITS = {"large": 10.0, "medium": 8.6,
         # not measured: the medium/large ratio (0.86) applied once more
         "small": 7.4}
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
                m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
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
        font = re.search(r"using = fontsize_(small|medium|large)", tb).group(1)
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
        self.assertEqual(cell, (288, "medium"))
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
        value = self.dash[self.dash.index("type banking_dash_condition_value = textbox {"):]
        value = _block_from(value, value.index("{"))
        cell = (int(re.search(r"max_width = (\d+)", value).group(1)),
                re.search(r"using = fontsize_(\w+)", value).group(1))
        for m in re.finditer(r"banking_dash_condition_value = \{", body):
            box = _block_from(body, m.end() - 1)
            if "multiline = yes" in box:
                continue      # wraps rather than eliding
            key = re.search(r'text = "(\w+)"', box).group(1)
            with self.subTest(value=key):
                self.fits(key, cell)

    def test_overview_cells(self):
        body = _type_body(self.dash, "te_banking_overview_panel")
        cell = self.type_box("te_banking_ov_cell", "caption")
        for key in self.texts("caption", body):
            with self.subTest(caption=key):
                self.fits(key, cell)
        word = _type_body(self.dash, "te_banking_ov_word")
        cell = (int(re.search(r"max_width = (\d+)", word).group(1)),
                re.search(r"using = fontsize_(\w+)", word).group(1))
        words = sorted(set(re.findall(r'te_banking_ov_word = \{[^{}]*?text = "(\w+)"', body)))
        self.assertEqual(len(words), 12)   # seven phase words and five readings
        for key in words:
            with self.subTest(word=key):
                self.fits(key, cell)
        # the longest band word, named: the price band's
        self.assertEqual(self.shown("banking_dash_mon_band_value"), "Hyperinflation")

    def test_overview_change_lines(self):
        """The ranges under the first row (test_banking_monthly_change.py).
        The cycle value and bubble pressure print one decimal; momentum
        prints two, and its monthly change stays well inside +/-10 (a tenth of
        momentum decays, and the pushes come to a few points at most)."""
        body = _type_body(self.dash, "te_banking_overview_panel")
        box = _type_body(self.dash, "te_banking_ov_change_text")
        cell = (int(re.search(r"max_width = (\d+)", box).group(1)),
                re.search(r"using = fontsize_(\w+)", box).group(1))
        keys = sorted(set(re.findall(r'te_banking_ov_change_text = \{[^{}]*?text = "(\w+)"', body)))
        self.assertEqual(len(keys), 10)   # four shapes each for value and momentum, two for bubble
        for key in keys:
            with self.subTest(line=key):
                self.fits(key, cell, "-9.99" if "_momentum_" in key else NUMBER)

    def test_buttons(self):
        """A button's label is in the medium type (assumed: its font is the
        button template's)."""
        types = {"banking_dash_mon_button": 128, "banking_dash_action_button": 100}
        for typ, default in types.items():
            for m in re.finditer(r"\b%s = \{" % typ, self.dash):
                block = _block_from(self.dash, m.end() - 1)
                size = re.search(r"size = \{ (\d+) \d+ \}", block)
                key = re.search(r'text = "(\w+)"', block)
                if key is None:          # the type's own block slots
                    continue
                with self.subTest(button=key.group(1)):
                    self.fits(key.group(1), (int(size.group(1)) if size else default, "medium"))
        for key in ("banking_dash_btn_enable", "banking_dash_btn_disable", "banking_dash_btn_execute"):
            self.fits(key, (100, "medium"))


if __name__ == "__main__":
    unittest.main()
