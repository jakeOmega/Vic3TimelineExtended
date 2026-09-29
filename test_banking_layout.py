"""The banking panels' section order, collapse defaults and state gates.

Style-guide pass, 2026-09-29 (docs/guides/gui_style_guide.md), in the spirit
of test_un_layout.py: one layout for the journal entry and the Budget tab, an
overview on top, the live sections open, the history and How Banking Works
at the foot, and every collapse flag named for its default.
"""
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
        self.assertEqual(re.findall(r"\b(te_banking_\w+) = \{", body), REFERENCE)
        # the journal's history is the block's default, so the tab can swap it
        self.assertIn('block "history" {', body, "the history charts are not in a \"history\" block")
        block = _block_from(body, body.index('block "history" {'))
        self.assertIn("te_banking_history_panel = {}", block)

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
        ref = _block_from(tab, tab.index("te_banking_reference_sections = {"))
        self.assertRegex(ref, r'blockoverride "history" \{\s*te_banking_history_panel_open = \{\}\s*\}')

    def test_history_is_collapsed_in_the_journal_and_open_in_the_tab(self):
        hist = _read(HIST)
        self.assertIn("Toggle('te_hist_charts_open')", _type_body(hist, "te_banking_history_panel"))
        self.assertIn("Toggle('te_banking_tab_hist_closed')", _type_body(hist, "te_banking_history_panel_open"))

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
        self.assertGreaterEqual(len(flags), 17)
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
        "banking_dash_momentum_band_surging": 5, "banking_dash_momentum_band_rising": 4,
        "banking_dash_momentum_band_steady": 3, "banking_dash_momentum_band_falling": 2,
        "banking_dash_momentum_band_collapsing": 1}),
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
    None: "Overview row 2: intervention budget",
}


def _norm(s):
    return " ".join(s.split())


def _cells():
    """(tooltip, caption, [(picker, key, texture)], block) per overview cell."""
    body = _type_body(_read(DASH), "te_banking_overview_panel")
    out = []
    for m in re.finditer(r"te_banking_ov_cell = \{", body):
        block = _block_from(body, m.end() - 1)
        tip = re.search(r'^\t*tooltip = "(\w+)"', block, re.M).group(1)
        cap = re.search(r'blockoverride "caption" \{\s*text = "(\w+)"', block).group(1)
        icons_at = block.index('blockoverride "icons" {')
        icons = _block_from(block, icons_at)
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
        badge = _block_from(block, block.index('blockoverride "badge" {'))
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
        for m in re.finditer(r"(?m)^\t\t### Row \d", body):
            row = _block_from(body, body.index("flowcontainer = {", m.end()))
            n = len(re.findall(r"te_banking_ov_cell = \{", row))
            spacing = int(re.search(r"spacing = (\d+)", row).group(1))
            self.assertLessEqual(n * w + (n - 1) * spacing, 480, row[:80])
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
    """docs/systems/banking_gui_icons.md holds each placeholder to its code."""

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
        tex = re.search(r'blockoverride "badge" \{.*?texture = "([^"]+)"', block, re.S).group(1)
        self.assertEqual(self.doc["Overview row 1: bubble pressure"].get("crash risk"), tex)

    def test_no_row_names_a_state_the_overview_lacks(self):
        listed = {(s, k) for s, rows in self.doc.items() for k in rows}
        drawn = {(DOC_SECTIONS[p], k) for _, _, found, _ in _cells() for p, k, _ in found}
        drawn.add(("Overview row 1: bubble pressure", "crash risk"))
        self.assertEqual(listed, drawn)


if __name__ == "__main__":
    unittest.main()
