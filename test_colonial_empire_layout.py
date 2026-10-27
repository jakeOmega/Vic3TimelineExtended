"""The Colonial Empire panels' layout (docs/guides/gui_style_guide.md): the
section order, the collapse defaults, the overview and its gates, and where
the explanations went. Modelled on test_un_layout.py."""
import glob
import os
import re
import subprocess
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "colonial_empire_widget.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_colonial_empire.txt")
VALUES = os.path.join(REPO, "common", "script_values", "colonial_empire_values.txt")
DISPLAY = os.path.join(REPO, "common", "scripted_effects", "colonial_empire_display_effects.txt")
DECOLONIZATION = os.path.join(REPO, "common", "scripted_effects", "decolonization.txt")
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

STATUS = ["te_ce_sec_holdings", "te_ce_sec_stability", "te_ce_sec_pressure", "te_ce_sec_programmes"]
REFERENCE = ["te_ce_sec_history", "te_ce_sec_how"]
ROOTS = {   # root name -> (what it instances, the journal container it is attached to)
    "widget_je_colonial_empire_overview": ("te_ce_overview_panel", "custom_widget_container_1"),
    "widget_je_colonial_empire_status": ("te_ce_status_sections", "custom_widget_container_2"),
    "widget_je_colonial_empire_reference": ("te_ce_reference_sections", "custom_widget_container_3"),
}
OLD_ROOTS = ["widget_je_colonial_empire", "widget_je_colonial_empire_history"]
OLD_FLAGS = ["colonial_empire_history_open", "colonial_empire_pressure_open",
             "colonial_empire_decisions_closed", "colonial_empire_territories_open"]
PROGRAMMES = ("invest", "garrison", "assimilation")

# The explanations "How the Colonial Empire Works" holds, and the live
# sections they must not reappear in.
HOW_KEYS = ["je_colonial_empire_how_bar_1", "je_colonial_empire_how_bar_2", "je_colonial_empire_how_bar_3",
            "je_colonial_empire_how_moves", "je_colonial_empire_how_pressure",
            "je_colonial_empire_how_programmes", "je_colonial_empire_how_decolonization"]
RETIRED_KEYS = ["je_colonial_empire_status_summary", "je_colonial_empire_ov_pie_label",
                "je_colonial_empire_bar_headline", "je_colonial_empire_band_headline",
                "je_colonial_empire_conditions_body", "je_colonial_empire_phase_row",
                "je_colonial_empire_candidates_row",
                # The Decolonization section and its candidate counts, and the
                # territory list's People column and nested header (2026-10-24:
                # Colonial Holdings, a button beside each target).
                "je_colonial_empire_candidates_eligible", "je_colonial_empire_candidates_eligible_tt",
                "je_colonial_empire_candidates_largest", "je_colonial_empire_candidates_largest_tt",
                "je_colonial_empire_candidates_round_table", "je_colonial_empire_candidates_round_table_tt",
                "je_colonial_empire_decision_release", "je_colonial_empire_decision_release_tt",
                "je_colonial_empire_decision_round_table", "je_colonial_empire_decision_round_table_tt",
                "je_colonial_empire_decisions_header", "je_colonial_empire_territories_header",
                "je_colonial_empire_territory_head_pop", "je_colonial_empire_territory_head_pop_tt",
                "je_colonial_empire_territory_pop",
                # The eight-slot lists' "+N more" hovers and captions, International
                # Pressure's text roster, the overview's holdings line and legend
                # note, and the programme rows' cost lines (the 2026-10-27 GUI
                # audit, CE-1 to CE-7).
                "je_colonial_empire_territories_more", "je_colonial_empire_territories_more_head",
                "je_colonial_empire_territories_more_tail", "je_colonial_empire_subjects_more",
                "je_colonial_empire_subjects_more_head", "je_colonial_empire_territory_more_line",
                "je_colonial_empire_territory_more_line_bloc", "je_colonial_empire_subject_more_line",
                "je_colonial_empire_territories_caption", "je_colonial_empire_subjects_caption",
                "je_colonial_empire_wars_caption", "je_colonial_empire_pressure_scaling_tt",
                "je_colonial_empire_pressure_share_tt", "je_colonial_empire_pressure_support_share_tt",
                "je_colonial_empire_pressure_share_note", "je_colonial_empire_pressure_support_share_note",
                "je_colonial_empire_condemner_entry_tt", "je_colonial_empire_supporter_entry_tt",
                "je_colonial_empire_pressure_quiet_tt", "je_colonial_empire_ov_legend_note",
                "je_colonial_empire_ov_held", "je_colonial_empire_cost_invest",
                "je_colonial_empire_cost_garrison", "je_colonial_empire_cost_assimilation"]
# The nine drift groups, the monthly limit and the total, and where each reads.
# The three that iterate read the snapshot through guarded values.
TABLE = [("base", "ScriptValue('colonial_stability_drift_base')"),
         ("laws", "ScriptValue('colonial_stability_drift_laws')"),
         ("igs", "ScriptValue('colonial_stability_drift_igs')"),
         ("rank", "ScriptValue('colonial_stability_drift_rank')"),
         ("policies", "ScriptValue('colonial_stability_drift_policies')"),
         ("domestic", "ScriptValue('colonial_stability_drift_domestic')"),
         ("overreach", "ScriptValue('colonial_empire_disp_d_overreach')"),
         ("gp", "ScriptValue('colonial_empire_disp_d_gp')"),
         ("acceptance", "ScriptValue('colonial_empire_disp_d_acceptance')"),
         ("cap", "ScriptValue('colonial_stability_drift_cap_display')"),
         ("total", "ScriptValue('colonial_stability_drift_total_display')")]
# The eight terms drawn as pillar bars; the base decline is a constant, and the
# monthly limit and the total are sums, so those three rows have no bar.
PILLARS = ["laws", "igs", "rank", "policies", "domestic", "overreach", "gp", "acceptance"]
READY = "GetScriptedGui('colonial_empire_display_ready').IsShown"


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    """The text with every `#` comment blanked out (a `#` inside quotes is loc markup)."""
    out = []
    for line in text.split("\n"):
        in_quotes = False
        for i, ch in enumerate(line):
            if ch == '"':
                in_quotes = not in_quotes
            elif ch == "#" and not in_quotes:
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def _span(text, start):
    """Offsets of the brace block that opens at or after `start`."""
    open_at = text.index("{", start)
    depth = 0
    for j in range(open_at, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return open_at, j
    raise AssertionError("unbalanced braces")


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    a, b = _span(text, m.end() - 1)
    return text[a + 1:b]


def _block(text, name):
    m = re.search(rf"(?m)^{name} = \{{", text)
    assert m, f"no {name}"
    a, b = _span(text, m.end() - 1)
    return text[a + 1:b]


def _own_properties(body):
    """A block's text with its nested blocks cut out."""
    out, depth = [], 0
    for ch in body:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def _enclosing_visibles(text, pos):
    """The `visible` of every block around `pos`, innermost first."""
    found = []
    stack = []
    spans = []
    for i, ch in enumerate(text):
        if ch == "{":
            stack.append(i)
        elif ch == "}":
            spans.append((stack.pop(), i))
    for a, b in sorted((s for s in spans if s[0] < pos < s[1]), key=lambda s: s[0], reverse=True):
        m = re.search(r'\bvisible = "([^"]*)"', _own_properties(text[a + 1:b]))
        if m:
            found.append(m.group(1))
    return found


def _assert_rooted_at_the_player(case, row_type):
    """Gotcha #24: a hover inside a datamodel item sees the item's datacontext
    and nothing above it, so no tooltip of a list row may read JournalEntry,
    inline or through the loc key it names."""
    loc = _loc()
    for m in re.finditer(r'\btooltip = "([^"]*)"', row_type):
        value = m.group(1)
        reads = value if "[" in value else loc.get(value, "")
        with case.subTest(tooltip=value[:60]):
            case.assertNotIn("JournalEntry", reads)


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        for m in re.finditer(r'(?m)^ ([\w.\-]+):\d* "(.*)"\s*$', _read(path)):
            keys[m.group(1)] = m.group(2)
    return keys


class OrderTest(unittest.TestCase):
    def test_status_and_reference_order(self):
        gui = _read(GUI)
        for composer, expected in (("te_ce_status_sections", STATUS), ("te_ce_reference_sections", REFERENCE)):
            found = re.findall(r"^\t\t(te_ce_sec_\w+) = \{", _type_body(gui, composer), re.M)
            self.assertEqual(found, expected, composer)

    def test_composers_and_overview_are_gated_on_the_entry(self):
        gui = _read(GUI)
        for name in ("te_ce_status_sections", "te_ce_reference_sections", "te_ce_overview_panel"):
            self.assertIn('visible = "[JournalEntry.IsActive]"', _own_properties(_type_body(gui, name)), name)


class RootsTest(unittest.TestCase):
    def test_roots_are_thin_gated_wrappers(self):
        gui = _read(GUI)
        for root, (inner, _container) in ROOTS.items():
            with self.subTest(root=root):
                m = re.search(rf'(?m)^flowcontainer = \{{\s*name = "{root}"', gui)
                self.assertTrue(m, f"no root {root}")
                a, b = _span(gui, m.start())
                body = gui[a + 1:b]
                self.assertIn('visible = "[JournalEntry.IsActive]"', body)
                self.assertEqual(re.findall(r"(?m)^\t(\w+) = \{", body), [inner])
        for old in OLD_ROOTS:
            self.assertNotIn(f'name = "{old}"', gui, old)

    def test_the_entry_attaches_each_root_and_the_bar_marker(self):
        je = _read(JE)
        widgets = re.findall(r'widget = \{\s*gui = "([^"]+)"\s*name = "(\w+)"\s*container = "(\w+)"\s*\}', je)
        attached = {name: (gui, container) for gui, name, container in widgets}
        for root, (_inner, container) in ROOTS.items():
            self.assertEqual(attached.get(root),
                             ("gui/journal_entry_widgets/colonial_empire_widget.gui", container), root)
        # The overview draws the bar, so the journal panel's own bar block goes.
        self.assertEqual(attached.get("widget_te_je_bars_on_top_marker"),
                         ("gui/journal_entry_widgets/te_je_bars_on_top_marker.gui", "custom_widget_container_7"))
        self.assertEqual(len(widgets), 4)


class FlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _read(GUI)

    def test_section_flags_say_their_default(self):
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.text))
        self.assertEqual(len(flags), 6)
        for f in flags:
            self.assertRegex(f, r"^colonial_empire_\w+_(open|closed)$", f"section flag {f} does not say its default")
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", self.text))
            bare = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", self.text)) - negated
            if f.endswith("_closed"):   # shown unless closed: one bare (show-more), the rest negated
                self.assertEqual(bare, 1, f)
                self.assertGreaterEqual(negated, 2, f)
            else:                        # shown only when opened: one negated (show-more)
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 2, f)

    def test_live_sections_open_and_explanations_collapsed(self):
        for sec, flag in (("te_ce_sec_stability", "colonial_empire_stability_closed"),
                          ("te_ce_sec_pressure", "colonial_empire_pressure_closed"),
                          ("te_ce_sec_programmes", "colonial_empire_programmes_closed"),
                          ("te_ce_sec_holdings", "colonial_empire_holdings_closed"),
                          ("te_ce_sec_history", "colonial_empire_history_closed"),
                          ("te_ce_sec_how", "colonial_empire_how_open")):
            self.assertIn(f"GetVariableSystem.Toggle('{flag}')", _type_body(self.text, sec), sec)

    def test_no_section_is_an_exception(self):
        """Live lists stay open (owner, play-test round 2): International
        Pressure's old collapsed-for-cost exception is gone."""
        self.assertNotIn("AGAINST style rule 1", self.text)
        self.assertNotIn("except International Pressure", self.text)

    def test_no_old_flag_survives(self):
        for f in OLD_FLAGS:
            self.assertNotIn(f"'{f}'", self.text, f)


class OverviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = _type_body(_read(GUI), "te_ce_overview_panel")

    def test_every_band_has_an_icon(self):
        codes = {int(n) for n in re.findall(
            r"ScriptValue\('colonial_empire_disp_tier'\), '\(CFixedPoint\)(\d+)'", self.body)}
        self.assertEqual(codes, {1, 2, 3, 4, 5})
        for band in ("solidified", "stable", "strained", "crumbling", "collapsing"):
            self.assertIn(f'text = "je_colonial_empire_band_{band}"', self.body, band)

    def test_programmes_light_from_the_scope_free_handlers(self):
        cells = [self.body[slice(*_span(self.body, m.start()))]
                 for m in re.finditer(r"te_ce_ov_programme = \{", self.body)]
        self.assertEqual(len(cells), len(PROGRAMMES))
        for p, cell in zip(PROGRAMMES, cells):
            with self.subTest(programme=p):
                gate = rf"GetScriptedGui\('colonial_empire_active_{p}_sgui'\)\.IsShown"
                self.assertRegex(cell, rf'blockoverride "lit" \{{\s*visible = "\[{gate}[^"]*"\s*'
                                       rf'tooltip = "je_colonial_empire_ov_{p}_on_tt"')
                self.assertRegex(cell, rf'blockoverride "unlit" \{{\s*visible = "\[Not\({gate}[^"]*"\s*'
                                       rf'tooltip = "je_colonial_empire_ov_{p}_off_tt"')

    def test_the_bar_row(self):
        m = re.search(r'datamodel = "\[JournalEntry\.GetScriptedProgressBars\]"\s*item = \{', self.body)
        self.assertTrue(m, "the bar is not read through the entry's own datamodel")
        a, b = _span(self.body, m.end() - 1)
        item = self.body[a:b]
        # Gotcha #24: a tooltip inside a datamodel item has no JournalEntry, so
        # the row's is the engine's breakdown and the two of our own read GetPlayer.
        self.assertEqual(re.findall(r'tooltip = "([^"]*)"', item),
                         ["[ScriptedProgressBar.GetPeriodicProgressBreakdown]",
                          "je_colonial_empire_ov_tick_tt", "je_colonial_empire_ov_heading_tt"])
        loc = _loc()
        for key in ("je_colonial_empire_ov_tick_tt", "je_colonial_empire_ov_tick_eta",
                    "je_colonial_empire_ov_tick_no_eta", "je_colonial_empire_ov_heading_tt"):
            with self.subTest(key=key):
                self.assertNotIn("JournalEntry", loc[key])
                self.assertNotIn("ROOT", loc[key])
        self.assertIn("GetPlayer.", loc["je_colonial_empire_ov_heading_tt"])
        self.assertNotIn("progressbar_marker.dds", item, "the eye marker is gone (play-test round 3)")
        codes = {int(n) for n in re.findall(
            r"ScriptValue\('colonial_empire_disp_trend'\), '\(CFixedPoint\)(-?\d+)'", item)}
        self.assertEqual(codes, {-1, 0, 1})
        for arrow in ("trend_up", "trend_down", "trend_nochange"):
            self.assertIn(f"generic_icons/{arrow}.dds", item)

    def test_pressure_pie_and_alerts(self):
        pie = _type_body(_read(GUI), "te_ce_ov_pie")
        # Largest first: the supporters' layer (the sum) under the condemners'.
        self.assertLess(pie.index('block "pie_value_cum"'), pie.index('block "pie_value"'))
        self.assertLess(pie.index("pie_supporters.dds"), pie.index("pie_condemners.dds"))
        self.assertIn("ScriptValue('colonial_empire_disp_pressure_cum')", self.body)
        self.assertIn("ScriptValue('colonial_empire_disp_condemner_share')", self.body)
        # CE-7: what each share does sits on its own legend line's hover, not in a
        # note under the legend; the pie's hover says what it shows.
        for key in ("je_colonial_empire_ov_legend_condemn", "je_colonial_empire_ov_legend_support"):
            self.assertRegex(self.body, rf'tooltip = "{key}_tt"\s*blockoverride "legend_swatch" \{{[^}}]*\}}\s*'
                                        rf'blockoverride "legend_text" \{{\s*text = "{key}"', key)
        loc = _loc()
        self.assertIn("colonial_empire_disp_supporter_share", loc["je_colonial_empire_ov_legend_support"])
        self.assertIn("does not offset", loc["je_colonial_empire_ov_legend_support_tt"])
        self.assertIn("two thirds", loc["je_colonial_empire_ov_legend_condemn_tt"])
        self.assertNotIn("je_colonial_empire_ov_legend_note", loc)
        self.assertIn('tooltip = "je_colonial_empire_ov_pie_tt"', self.body)
        self.assertNotIn("colonial_empire_pressure_sgui", self.body)
        # The escalation in force is the Great Powers cell's word, by code.
        codes = {int(n) for n in re.findall(
            r"ScriptValue\('colonial_empire_disp_pressure_level'\), '\(CFixedPoint\)(\d+)'", self.body)}
        self.assertEqual(codes, {0, 1, 2})

    def test_four_banking_cells(self):
        """The owner's call (2026-10-27): Banking's cells where the overview flags
        something to act on, te_banking_ov_cell as it is, two to a row."""
        gui = _read(GUI)
        self.assertNotRegex(gui, r"type te_banking_ov_cell\b", "only the Banking panel defines the cell")
        cells = [self.body[slice(*_span(self.body, m.start()))]
                 for m in re.finditer(r"te_banking_ov_cell = \{", self.body)]
        self.assertEqual([re.search(r'blockoverride "caption" \{\s*text = "(\w+)"', c).group(1) for c in cells],
                         ["je_colonial_empire_ov_band_label", "je_colonial_empire_ov_gp_label",
                          "je_colonial_empire_ov_held_label", "je_colonial_empire_ov_programmes_label"])
        for cell, tt in zip(cells, ("je_colonial_empire_ov_band_tt", "je_colonial_empire_ov_gp_tt",
                                    "je_colonial_empire_ov_held_tt", "je_colonial_empire_ov_programmes_tt")):
            with self.subTest(cell=tt):
                self.assertIn(f'tooltip = "{tt}"', _own_properties(cell[1:-1]))
                self.assertIn('blockoverride "word"', cell)
                self.assertIn('blockoverride "third_line"', cell)
                third = cell[slice(*_span(cell, cell.index('blockoverride "third_line"')))]
                self.assertIn("position = { 78 46 }", third)
        # Not formulaic: no cell's word or line tells the player what to do.
        loc = _loc()
        for m in re.finditer(r'text = "(je_colonial_empire_\w+)"', "".join(cells)):
            with self.subTest(key=m.group(1)):
                self.assertNotRegex(loc[m.group(1)], r"(?i)\byou need\b|\bneeds you\b")
        # Two to a row: 238 + 4 + 238 = 480, the overview's column.
        rows = re.findall(r"flowcontainer = \{\s*direction = horizontal\s*spacing = 4\s*ignoreinvisible = yes\s*"
                          r"(?:###.*\n\s*)*te_banking_ov_cell = \{", self.body)
        self.assertEqual(len(rows), 2)
        held = loc["je_colonial_empire_ov_held_colonies"] + loc["je_colonial_empire_ov_held_subjects"]
        self.assertIn("colonial_empire_disp_colonies", held)
        self.assertIn("colonial_empire_disp_subjects", held)
        self.assertIn("colonial_empire_disp_programmes_running", loc["je_colonial_empire_ov_programmes_running"])
        self.assertIn("colonial_stability_drift_policies", loc["je_colonial_empire_ov_programmes_net"])
        self.assertIn("colonial_empire_disp_d_gp", loc["je_colonial_empire_ov_gp_net"])
        for side in ("condemners", "supporters"):
            self.assertIn(f"colonial_empire_disp_gp_{side}", loc["je_colonial_empire_ov_gp_tt"])
        # The next band's edge moved into the band cell, under the band.
        self.assertIn('text = "je_colonial_empire_ov_next"', cells[0])


class DisplayScriptTest(unittest.TestCase):
    def test_display_values_guard_every_variable(self):
        values = _read(VALUES)
        names = re.findall(r"(?m)^(colonial_empire_disp_\w+) = \{", values)
        self.assertEqual(len(names), 43)
        panel = _read(GUI) + "\n".join(v for k, v in _loc().items() if k.startswith("je_colonial_empire_"))
        for name in names:
            with self.subTest(value=name):
                self.assertIn(f"ScriptValue('{name}')", panel, f"{name} is not read by the panel or its loc")
                body = _block(values, name)
                for var in re.findall(r"var:(\w+)", body):
                    self.assertIn(f"has_variable = {var}", body, f"{name} reads var:{var} unguarded")

    def test_the_pressure_level_reads_the_bars_own_leaves(self):
        refresh = _block(_read(DISPLAY), "colonial_empire_refresh_display")
        start = refresh.index("name = colonial_empire_pressure_level value = 0")
        chunk = refresh[start:start + 600]
        self.assertIn("colonial_stability_term_gp_extreme_pressure < 0", chunk)
        self.assertIn("colonial_stability_term_gp_high_pressure < 0", chunk)
        self.assertNotRegex(chunk, r"0\.33|0\.66", "a share threshold copied out of colonial_empire_values.txt")

    def test_cleanup_removes_every_display_variable(self):
        refresh = _block(_read(DISPLAY), "colonial_empire_refresh_display")
        cleanup = _block(_read(DECOLONIZATION), "colonial_empire_je_cleanup_effect")
        written = set(re.findall(r"set_variable = \{\s*name = (\w+)", refresh))
        self.assertIn("colonial_empire_pressure_level", written)
        for var in written:
            self.assertRegex(cleanup, rf"remove_variable = {var}\b", var)
        # And the lists the panel's datamodels draw, and the great powers' rows.
        for lst in re.findall(r"clear_variable_list = (\w+)", refresh):
            self.assertIn(f"clear_variable_list = {lst}", cleanup, lst)
        self.assertIn("colonial_empire_clear_gp_rows = yes", cleanup)
        self.assertNotRegex(cleanup, r"remove_variable = colonial_empire_(territory|subject)_\d", "nothing sets the slots")


class StabilityTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.body = _type_body(cls.gui, "te_ce_sec_stability")

    def _rows(self):
        return [self.body[slice(*_span(self.body, m.start()))]
                for m in re.finditer(r"colonial_empire_pillar_row = \{", self.body)]

    def test_the_groups_are_pillar_rows(self):
        rows = self._rows()
        self.assertEqual(len(rows), len(TABLE))
        self.assertNotIn("colonial_empire_value_row = {", self.body)
        for (group, read), row in zip(TABLE, rows):
            with self.subTest(group=group):
                self.assertIn(f'tooltip = "je_colonial_empire_drift_{group}_tt"', row)
                self.assertIn(f'text = "je_colonial_empire_drift_{group}"', row)
                self.assertIn(f"MakeScope.{read}|=+2]", row)
                if group in PILLARS:
                    self.assertRegex(row, r'blockoverride "row_bar" \{\s*double_direction_progressbar = \{')
                    self.assertIn(f"ScriptValue('colonial_empire_disp_pillar_{group}_neg')", row)
                    self.assertIn(f"ScriptValue('colonial_empire_disp_pillar_{group}_pos')", row)
                    self.assertLess(row.index("value_left"), row.index("_neg')"))
                else:
                    self.assertNotIn("row_bar", row, f"{group} has no range to draw")

    def test_the_bar_cell_is_fixed_whether_or_not_it_holds_a_bar(self):
        row = _type_body(self.gui, "colonial_empire_pillar_row")
        self.assertRegex(row, r'widget = \{\s*size = \{ 190 14 \}\s*parentanchor = vcenter\s*block "row_bar" \{\}')

    def test_every_variable_read_is_gated(self):
        """Every .Var( read in the panel, in a text, in the loc it names or in a
        datacontext, sits under the display_ready gate: the entry is shown while
        inactive (gotcha #14). A great power's row reads its own script
        container, which exists only with its variables, behind
        ScriptContainer.HasVariable."""
        loc = _loc()
        text = _strip_comments(self.gui)
        checked = 0
        for m in re.finditer(r'\b(?:text|datacontext) = "([^"]*)"', text):
            value = m.group(1)
            reads = value if "[" in value else loc.get(value, "")
            if ".Var(" not in reads:
                continue
            checked += 1
            with self.subTest(text=value):
                gates = " ".join(_enclosing_visibles(text, m.start()))
                if reads.count("ScriptContainer.MakeScope.Var(") == reads.count(".Var("):
                    for var in re.findall(r"ScriptContainer\.MakeScope\.Var\('(\w+)'\)", reads):
                        self.assertIn(f"ScriptContainer.HasVariable('{var}')", gates, value)
                else:
                    self.assertIn(READY, gates, value)
        self.assertEqual(checked, 3 + 2)   # three war rows; a great power's flag and name
        for row in self._rows():
            self.assertNotIn(".Var(", row, "the drift rows read the guarded disp values")



class PillarRangeTest(unittest.TestCase):
    """Play-test round 3 (owner, 2026-09-30): Why Stability Is Moving as the UN's
    pillar bars. Each term's range is a named script value with where it comes
    from noted above it, and each half of the bar is clamped to 0-1."""

    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES)

    def test_each_range_is_named_and_explained(self):
        for g in PILLARS:
            with self.subTest(term=g):
                lo = re.search(rf"(?m)^colonial_pillar_{g}_min = (-?[\d.]+)$", self.values)
                hi = re.search(rf"(?m)^colonial_pillar_{g}_max = (-?[\d.]+)$", self.values)
                self.assertTrue(lo and hi, g)
                self.assertLess(float(lo.group(1)), 0)
                self.assertGreaterEqual(float(hi.group(1)), 0)
                before = self.values[:lo.start()].rstrip("\n").split("\n")[-1]
                self.assertTrue(before.startswith("#"), f"no derivation comment above colonial_pillar_{g}_min")

    def test_each_half_is_clamped_to_its_range(self):
        for g in PILLARS:
            with self.subTest(term=g):
                pos = _block(self.values, f"colonial_empire_disp_pillar_{g}_pos")
                neg = _block(self.values, f"colonial_empire_disp_pillar_{g}_neg")
                self.assertRegex(neg, rf"divide = colonial_pillar_{g}_min\s*multiply = -1\s*min = -1\s*max = 0")
                if float(re.search(rf"(?m)^colonial_pillar_{g}_max = (-?[\d.]+)$", self.values).group(1)) > 0:
                    self.assertRegex(pos, rf"divide = colonial_pillar_{g}_max\s*min = 0\s*max = 1")
                else:
                    self.assertRegex(pos, r"^\s*value = 0\s*$", "a term that is never positive draws no green")

    def test_the_bars_read_what_the_rows_print(self):
        for g, read in TABLE:
            if g not in PILLARS:
                continue
            with self.subTest(term=g):
                src = re.search(r"'(\w+)'", read).group(1)
                self.assertIn(f"value = {src}", _block(self.values, f"colonial_empire_disp_pillar_{g}_neg"))


class DecisionsTest(unittest.TestCase):
    def test_the_button_sits_beside_its_decision(self):
        gui = _read(GUI)
        self.assertRegex(gui, r"type colonial_empire_decision_row = flowcontainer \{\s*direction = horizontal")
        self.assertIn("datacontext = \"[GetScriptedGui('colonial_empire_planned_sgui')]\"",
                      _type_body(gui, "colonial_empire_decision_row"))
        body = _type_body(gui, "te_ce_sec_holdings")
        loc = _loc()
        # One decision row: Planned Full Decolonization. Releasing one territory
        # or one subject is a button on its own row (HoldingsTest).
        self.assertEqual(body.count("colonial_empire_decision_row = {"), 1)
        self.assertRegex(body, r'text = "je_colonial_empire_decision_planned"\s*'
                               r'tooltip = "je_colonial_empire_decision_planned_tt"')
        self.assertNotIn("#lore", loc["je_colonial_empire_decision_planned"])
        self.assertNotIn("\\n", loc["je_colonial_empire_decision_planned"])
        self.assertNotIn("AddScope( 'op'", body[body.index("colonial_empire_decision_row = {"):])
        self.assertNotIn("colonial_empire_decision_sgui", _read(SGUIS))


# The per-target buttons of Colonial Holdings: the handler, its saved scope,
# its gate and effect, and the confirmation event the effect opens.
PER_TARGET = [("colonial_empire_release_state_sgui", "ce_state", "STATE", "release_state", "402"),
              ("colonial_empire_free_subject_sgui", "ce_capital", "CAPITAL", "free_subject", "403"),
              ("colonial_empire_dominion_subject_sgui", "ce_capital", "CAPITAL", "dominion_subject", "404")]
EVENTS = os.path.join(REPO, "events", "decolonization_events.txt")


def _options(event_body):
    return [event_body[slice(*_span(event_body, m.start()))]
            for m in re.finditer(r"(?m)^\toption = \{", event_body)]


class HoldingsTest(unittest.TestCase):
    """The owner's request (2026-10-24): the panel shows why the entry runs, the
    territories and the colonial subjects, and an action that targets one of
    them sits beside it, opening a confirmation for that one target."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.body = _type_body(cls.gui, "te_ce_sec_holdings")
        cls.sguis = _read(SGUIS)
        cls.effects = _read(DECOLONIZATION)
        cls.triggers = _read(TRIGGERS)
        cls.events = _read(EVENTS)
        cls.loc = _loc()

    def test_territories_then_subjects_then_the_whole_empire(self):
        order = [self.body.index(k) for k in ('"je_colonial_empire_holdings_territories"',
                                               '"je_colonial_empire_holdings_subjects"',
                                               '"je_colonial_empire_holdings_whole"')]
        self.assertEqual(order, sorted(order))
        self.assertLess(self.body.index("te_ce_territory_row = {"), order[1])
        self.assertLess(order[1], self.body.index("te_ce_subject_row = {"))
        self.assertLess(self.body.index("te_ce_subject_row = {"), order[2])

    def test_each_button_passes_its_own_target(self):
        rows = {"te_ce_territory_row": [PER_TARGET[0]], "te_ce_subject_row": PER_TARGET[1:]}
        for row_type, handlers in rows.items():
            row = _type_body(self.gui, row_type)
            for sgui, scope, *_ in handlers:
                with self.subTest(sgui=sgui):
                    m = re.search(rf"datacontext = \"\[GetScriptedGui\('{sgui}'\)\]\"", row)
                    self.assertTrue(m, f"{sgui} is not on a row of {row_type}")
                    button = row[slice(*_span(row, row.rindex("button = {", 0, m.start())))]
                    for prop in ("enabled", "onclick", "tooltip"):
                        self.assertRegex(button, rf"\b{prop} = \"[^\"]*AddScope\( '{scope}', State\.MakeScope \)")
                    self.assertNotRegex(_own_properties(button), r"\bvisible = ", "a row's button is always drawn")

    def test_one_subject_row_per_stored_capital(self):
        """CE-1 (2026-10-27): every colonial subject has its row and its buttons, a
        datamodel over the stored capitals (eight fixed rows and a "+N more"
        hover before)."""
        m = re.search(r'datamodel = "\[JournalEntry\.GetCountry\.MakeScope\.GetList\(\'colonial_empire_subject_capitals\'\)\]"'
                      r'\s*item = \{\s*te_ce_subject_row = \{\s*datacontext = "\[Scope\.GetState\]"', self.body)
        self.assertTrue(m, "the subject rows are not a datamodel over the stored capitals")
        self.assertEqual(self.body.count("te_ce_subject_row = {"), 1)
        row_type = _type_body(self.gui, "te_ce_subject_row")
        self.assertNotIn('block "row_visible"', row_type)
        self.assertNotIn('block "row_context"', row_type)
        # The cells reach the subject through its stored capital (gotcha #11).
        self.assertIn('datacontext = "[State.GetCountry]"', row_type)
        self.assertNotIn("Var(", row_type)
        _assert_rooted_at_the_player(self, row_type)


    def test_the_handlers_delegate_and_fail_closed(self):
        for sgui, scope, param, action, _ in PER_TARGET:
            with self.subTest(sgui=sgui):
                body = _block(self.sguis, sgui)
                self.assertIn(f"saved_scopes = {{ {scope} }}", body)
                self.assertIn("ai_is_valid = { always = no }", body)
                valid = body[slice(*_span(body, re.search(r"(?m)^\tis_valid = \{", body).start()))]
                self.assertLess(valid.index(f"exists = scope:{scope}"),
                                valid.index(f"colonial_empire_possible_{action} = {{ {param} = scope:{scope} }}"))
                self.assertIn(f"colonial_empire_effect_{action} = {{ {param} = scope:{scope} }}", body)

    def test_each_effect_opens_its_confirmation_under_the_lock(self):
        for _, _, _, action, event in PER_TARGET:
            with self.subTest(action=action):
                body = _block(self.effects, f"colonial_empire_effect_{action}")
                hidden = body[slice(*_span(body, body.index("hidden_effect = {")))]
                self.assertIn("set_variable = { name = decol_offer_pending days = 7 }", hidden)
                self.assertIn(f"trigger_event = {{ id = decolonization_events.{event} popup = yes }}", hidden)
                self.assertRegex(body, r"^\s*custom_tooltip = CE_\w+_TT", "the hover's line sits outside the wrapper")
                gate = _block(self.triggers, f"colonial_empire_possible_{action}")
                self.assertTrue("colonial_empire_no_offer_pending = yes" in gate
                                or "colonial_empire_subject_action_base" in gate, action)
        self.assertIn("colonial_empire_no_offer_pending = yes",
                      _block(self.triggers, "colonial_empire_subject_action_base"))
        self.assertIn("colonial_empire_no_offer_pending = yes",
                      _block(self.triggers, "colonial_empire_possible_planned_decolonization"))

    def test_every_option_clears_the_lock_and_reconsider_is_the_default(self):
        for event in ("401", "402", "403", "404"):
            options = _options(_block(self.events, f"decolonization_events.{event}"))
            with self.subTest(event=event):
                self.assertGreaterEqual(len(options), 2)
                for option in options:
                    self.assertIn("decol_offer_clear = yes", option)
                if event != "401":
                    last = options[-1]
                    self.assertIn("default_option = yes", last)
                    self.assertEqual(sum("default_option = yes" in o for o in options), 1)
                    for act in ("form_decolonized_country", "make_independent", "increase_autonomy"):
                        self.assertNotIn(act, last)

    def test_the_round_table_option_reads_the_shared_tests(self):
        options = _options(_block(self.events, "decolonization_events.402"))
        rt = options[1]
        self.assertIn("colonial_state_round_table_ready = yes", rt)
        self.assertIn("authority > colonial_round_table_authority", rt)
        self.assertIn("show_as_unavailable = { always = yes }", rt)
        self.assertIn("highlighted_option = yes", rt)
        gate = _block(self.triggers, "colonial_empire_possible_round_table_state")
        self.assertIn("colonial_state_round_table_ready = yes", gate)
        self.assertIn("authority > colonial_round_table_authority", gate)
        self.assertIn("authority > colonial_round_table_authority",
                      _block(self.triggers, "colonial_empire_possible_round_table"))
        self.assertNotRegex(self.triggers, r"authority > 200")

    def test_dominion_is_vanillas_step_up_for_a_colony(self):
        gate = _block(self.triggers, "colonial_empire_possible_dominion_subject")
        self.assertIn("is_subject_type = subject_type_colony", gate)
        self.assertIn("can_increase_autonomy = yes", gate)
        self.assertIn("catalyst_autonomy_change_imposed", gate)
        grant = _options(_block(self.events, "decolonization_events.404"))[0]
        for line in ("increase_autonomy = yes", "add_liberty_desire = -30",
                     "type = catalyst_autonomy_change_imposed", "create_unidirectional_truce",
                     "decol_clear_subject_pressure = yes"):
            self.assertIn(line, grant)

    def test_freed_subjects_are_former_colonies_without_the_band_pressure(self):
        options = _options(_block(self.events, "decolonization_events.403"))
        for option in options[:2]:
            self.assertIn("decol_mark_former_colony = { OVERLORD = root }", option)
            self.assertIn("make_independent = yes", option)
            self.assertIn("decol_clear_subject_pressure = yes", option)
        self.assertIn("has_law = law_type:law_neocolonialism", options[1])
        clear = _block(self.effects, "decol_clear_subject_pressure")
        for band in ("strained", "crumbling", "collapsing"):
            self.assertIn(f"has_modifier = colonial_overlord_{band}_subject_ld_modifier", clear)

    def test_the_prestige_reward_does_not_stack(self):
        rewards = _block(self.effects, "decol_chosen_release_rewards")
        self.assertRegex(rewards, r"limit = \{ NOT = \{ has_modifier = peaceful_decolonization_modifier \} \}"
                                  r"\s*add_modifier = \{\s*name = peaceful_decolonization_modifier")
        self.assertIn("decol_record_chosen_release = yes", rewards)

    def test_the_subject_snapshot(self):
        refresh = _block(_read(DISPLAY), "colonial_empire_refresh_display")
        chunk = refresh[refresh.index("clear_variable_list = colonial_empire_subject_capitals"):]
        chunk = chunk[:chunk.index("colonial_empire_refresh_gp_rows")]
        self.assertIn("is_player = yes", chunk)
        self.assertRegex(chunk, r"ordered_subject_or_below = \{\s*limit = \{\s*is_qualifying_colonial_subject = yes\s*"
                                r"exists = capital\s*\}\s*order_by = gdp\s*max = \d+\s*check_range_bounds = no")
        self.assertIn("add_to_variable_list = { name = colonial_empire_subject_capitals target = scope:colonial_empire_subject_capital }",
                      chunk)
        self.assertNotIn("colonial_empire_subject_slot", _read(DISPLAY))
        cleanup = _block(self.effects, "colonial_empire_je_cleanup_effect")
        self.assertIn("clear_variable_list = colonial_empire_subject_capitals", cleanup)
        self.assertIn("is_qualifying_colonial_subject = yes",
                      _block(_read(VALUES), "colonial_subject_count"))


    def test_the_overview_says_what_holds_the_entry(self):
        overview = _type_body(self.gui, "te_ce_overview_panel")
        cell = overview[overview.index('tooltip = "je_colonial_empire_ov_held_tt"'):]
        cell = cell[:cell.index("te_banking_ov_cell = {")]
        self.assertIn('text = "je_colonial_empire_ov_held_colonies"', cell)
        self.assertIn('text = "je_colonial_empire_ov_held_subjects"', cell)
        tt = self.loc["je_colonial_empire_ov_held_tt"]
        # CE-4: the terms link their concepts, which hold the thresholds once.
        for concept in ("concept_overseas_colony", "concept_colonial_subject", "concept_colonial_territory"):
            self.assertIn(concept, tt)
        for concept, values in (("concept_colonial_territory", ("colonial_territory_min_population",
                                                                "colonial_state_indigenous_min_share",
                                                                "colonial_settler_majority_share")),
                                ("concept_overseas_colony", ("colonial_state_indigenous_min_share", "acceptance_status_4",
                                                             "colonial_state_sol_floor_share"))):
            desc = self.loc[f"{concept}_desc"]
            for value in values:
                self.assertIn(f"GetPlayer.MakeScope.ScriptValue('{value}')", desc, (concept, value))
            self.assertNotRegex(re.sub(r"\[[^\]]*\]|#\w+", "", desc), r"\d", "editing rule 1: no number typed in loc")
        self.assertIn("concept_unincorporated_state", self.loc["concept_overseas_colony_desc"])
        # The colonies it counts are the entry's own test.
        self.assertIn("value = colonial_state_count", _block(_read(DISPLAY), "colonial_empire_refresh_display"))

    def test_each_definition_is_written_once(self):
        """CE-4: the hovers that wrote out what a territory, a colony and a
        colonial subject are link the concepts instead."""
        for key in ("je_colonial_empire_ov_held_tt", "je_colonial_empire_holdings_territories_tt",
                    "je_colonial_empire_territory_head_name_tt", "je_colonial_empire_holdings_subjects_tt"):
            with self.subTest(key=key):
                value = self.loc[key]
                self.assertNotIn("colonial_territory_min_population", value)
                self.assertNotIn("heritage", value)
        misc = {k: self.loc[k] for k in ("CE_STATE_IS_ELIGIBLE", "IS_DECOLONIZATION_ELIGIBLE_STATE_TT",
                                         "IS_OVERSEAS_COLONIAL_STATE_TT")}
        self.assertIn("concept_colonial_territory", misc["CE_STATE_IS_ELIGIBLE"])
        self.assertIn("concept_colonial_territory", misc["IS_DECOLONIZATION_ELIGIBLE_STATE_TT"])
        self.assertIn("concept_overseas_colony", misc["IS_OVERSEAS_COLONIAL_STATE_TT"])
        for key, value in misc.items():
            self.assertNotRegex(re.sub(r"\[[^\]]*\]|#\w+", "", value), r"\d", key)



class HowItWorksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.loc = _loc()

    def test_explanations_live_in_how_it_works(self):
        how = _type_body(self.gui, "te_ce_sec_how")
        for key in HOW_KEYS:
            self.assertIn(f'text = "{key}"', how, key)
        self.assertNotIn("ExecuteTooltip", how)
        self.assertNotRegex(how, r"\bcolonial_empire_text = \{")

    def test_live_sections_carry_no_explanations(self):
        for sec in STATUS + ["te_ce_sec_history"]:
            body = _type_body(self.gui, sec)
            for key in HOW_KEYS:
                self.assertNotIn(f'"{key}"', body, f"{sec} explains ({key})")
        overview = _type_body(self.gui, "te_ce_overview_panel")
        for key in HOW_KEYS:
            self.assertNotIn(f'"{key}"', overview, key)

    def test_the_pressure_lines_are_brief(self):
        """The weighting explanation lives in How it Works; a great power's row
        gives its own weight, reading only its container and the player."""
        self.assertIn("quarter", self.loc["je_colonial_empire_how_pressure"])
        tt = self.loc["je_colonial_empire_gp_row_tt"]
        self.assertIn("colonial_gp_row_disp_weight", tt)
        self.assertIn("colonial_gp_row_disp_factor", tt)
        for token in ("ROOT", "THIS.", "JournalEntry"):
            self.assertNotIn(token, tt, "a datamodel row's hover has no other context (gotcha #24)")

    def test_pillar_hovers_carry_no_boilerplate(self):
        """CE-5: how a pillar bar is drawn is said once, in How it Works."""
        for group, _ in TABLE:
            with self.subTest(group=group):
                value = self.loc[f"je_colonial_empire_drift_{group}_tt"]
                self.assertNotIn("The bar spans", value)
                self.assertNotIn("Updated monthly", value)
        self.assertIn("usual range", self.loc["je_colonial_empire_how_moves"])

    def test_no_caption_repeats_the_heads(self):
        """CE-3: the lists open on their heads; the one mechanic the wars caption
        held moved to the wars' hover and How it Works."""
        body = _type_body(self.gui, "te_ce_sec_holdings")
        self.assertNotRegex(body, r'text = "je_colonial_empire_\w+_caption"')
        for key in ("je_colonial_empire_holdings_wars_tt", "je_colonial_empire_how_decolonization"):
            self.assertIn("does not end", self.loc[key], key)
        self.assertIn("Open Talks", self.loc["je_colonial_empire_how_decolonization"])


    def test_retired_keys_are_gone(self):
        for key in RETIRED_KEYS:
            self.assertNotIn(key, self.loc, key)
            self.assertNotIn(f'"{key}"', self.gui, key)


ICONS_DOC = os.path.join(REPO, "docs", "systems", "colonial_empire_gui_icons.md")
CE_ICONS = "gfx/interface/icons/colonial_empire_icons/"
# The system's own art (PR #586), by the code or cell that draws it.
BAND_ICONS = {5: "band_solidified", 4: "band_stable", 3: "band_strained", 2: "band_crumbling", 1: "band_collapsing"}
ALERT_ICONS = {0: "alert_isolation", 1: "alert_isolation", 2: "alert_consensus"}   # 0 dimmed
PROGRAMME_ICONS = {"invest": "programme_invest", "garrison": "programme_garrison",
                   "assimilation": "programme_assimilation"}
# Vanilla textures the panel keeps as mechanics (frame, line, arrows), not art.
VANILLA_KEPT = {"gfx/interface/backgrounds/round_frame_dec.dds",
                "gfx/interface/backgrounds/white.dds",
                "gfx/interface/icons/generic_icons/transparent.dds",
                "gfx/interface/icons/generic_icons/trend_up.dds",
                "gfx/interface/icons/generic_icons/trend_down.dds",
                "gfx/interface/icons/generic_icons/trend_nochange.dds",
                # Vanilla's own art for vanilla things in the subject list: the
                # liberty-desire concept's icon and each subject type's icon.
                "gfx/interface/icons/diplomatic_action_icons/liberty_desire.dds",
                "[State.GetCountry.GetSubjectType.GetTexture]"}


def _tracked(path):
    return subprocess.run(["git", "ls-files", "--error-unmatch", path], cwd=REPO,
                          capture_output=True).returncode == 0


class ColonialIconsTest(unittest.TestCase):
    """The system's own icons (PR #586) replace every placeholder, each code
    drawing its own file (the UN's UnIconsTest)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.overview = _type_body(cls.gui, "te_ce_overview_panel")

    def _coded(self, value):
        """{code: texture} for the icons gated on ScriptValue(value) == code."""
        gate = (rf"visible = \"\[EqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('{value}'\), "
                rf"'\(CFixedPoint\)(\d+)' \)\]\"")
        found = {}
        for m in re.finditer(r"\bicon = \{", self.overview):
            icon = _own_properties(self.overview[slice(*_span(self.overview, m.start()))][1:-1])
            code, texture = re.search(gate, icon), re.search(r'texture = "([^"]+)"', icon)
            if code and texture:
                self.assertNotIn(int(code.group(1)), found, "two icons for one code")
                found[int(code.group(1))] = texture.group(1)
        return found

    def test_each_code_draws_its_own_icon(self):
        for value, names in (("colonial_empire_disp_tier", BAND_ICONS),
                             ("colonial_empire_disp_pressure_level", ALERT_ICONS)):
            with self.subTest(value=value):
                self.assertEqual(self._coded(value), {k: f"{CE_ICONS}{n}.dds" for k, n in names.items()})

    def test_each_programme_draws_its_own_icon(self):
        cells = [self.overview[slice(*_span(self.overview, m.start()))]
                 for m in re.finditer(r"te_ce_ov_programme = \{", self.overview)]
        for p, cell in zip(PROGRAMMES, cells):
            with self.subTest(programme=p):
                self.assertRegex(cell, rf'blockoverride "programme_texture" \{{\s*texture = "{CE_ICONS}{PROGRAMME_ICONS[p]}\.dds"')
        # Lit and dimmed are one texture; the 25% fade is the design.
        self.assertIn("alpha = 0.25", _type_body(self.gui, "te_ce_ov_programme"))

    def test_pies_legend_and_territory_icon(self):
        pie = _type_body(self.gui, "te_ce_ov_pie")
        self.assertEqual(re.findall(r'texture = "([^"]+)"', pie),
                         ["gfx/interface/backgrounds/round_frame_dec.dds", f"{CE_ICONS}pie_rest.dds",
                          f"{CE_ICONS}pie_supporters.dds", f"{CE_ICONS}pie_condemners.dds"])
        swatches = re.findall(r'blockoverride "legend_swatch" \{\s*texture = "([^"]+)"', self.overview)
        self.assertEqual(swatches, [f"{CE_ICONS}pie_condemners.dds", f"{CE_ICONS}pie_supporters.dds"])
        row = _type_body(self.gui, "te_ce_territory_row")
        self.assertEqual(re.findall(r'texture = "([^"]+)"', row), [f"{CE_ICONS}territory_colony.dds"] * 2)
        self.assertEqual(row.count("alpha = 0.25"), 1, "dimmed while not a colony, by the widget")

    def test_no_placeholder_left(self):
        for path in set(re.findall(r'texture = "([^"]+)"', self.gui)):
            with self.subTest(path=path):
                self.assertTrue(path.startswith(CE_ICONS) or path in VANILLA_KEPT, f"placeholder left: {path}")

    def test_every_icon_is_listed_and_in_the_repo(self):
        doc = _read(ICONS_DOC)
        ours = sorted({p for p in re.findall(r'texture = "([^"]+)"', self.gui) if p.startswith(CE_ICONS)})
        self.assertEqual(len(ours), 14)   # 5 bands, 2 alerts, 3 programmes, 3 pie discs, the colony
        for path in ours:
            self.assertIn(f"`{path}`", doc, path)
        if not any(_tracked(p) for p in ours):
            self.skipTest("the art lands with PR #586")
        for path in ours:
            self.assertTrue(_tracked(path), f"{path} is not in the repo")


CUSTOM_LOC = os.path.join(REPO, "common", "customizable_localization", "colonial_empire_custom_loc.txt")
MONTHS = ("invest", "garrison", "assimilate")


class LiveBandTest(unittest.TestCase):
    """Play-test round 1 (2026-09-29): a newly activated entry at 50 read
    "Collapsing", because every display read the var:colonial_empire_tier
    snapshot, which the entry's `immediate` takes before the bar holds its
    start value. The displays now read the band ladder live."""

    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES)

    def test_the_ladder_reads_the_bar_live(self):
        tier = _block(self.values, "colonial_empire_live_tier")
        self.assertIn("has_journal_entry = je_colonial_empire", tier)
        for edge in (90, 65, 40, 20):
            self.assertIn(f'je:je_colonial_empire ?= {{ "scripted_bar_progress(colonial_stability_bar)" >= {edge} }}',
                          tier, edge)
        self.assertNotIn("var:", tier)
        nxt = _block(self.values, "colonial_empire_live_next_boundary")
        self.assertIn("colonial_empire_live_tier", nxt)
        self.assertNotIn("var:", nxt)
        self.assertNotIn("scripted_bar_progress", nxt, "a second copy of the ladder")

    def test_the_displays_read_the_live_ladder(self):
        self.assertIn("value = colonial_empire_live_tier", _block(self.values, "colonial_empire_disp_tier"))
        frac = _block(self.values, "colonial_empire_disp_next_boundary_frac")
        self.assertIn("value = colonial_empire_live_next_boundary", frac)
        self.assertNotIn("var:", frac)
        custom = _read(CUSTOM_LOC)
        for name in ("colonial_empire_status_custom", "colonial_empire_tier_name",
                     "colonial_empire_next_band_name", "colonial_empire_phase_modifier"):
            with self.subTest(custom=name):
                body = _block(custom, name)
                triggers = re.findall(r"trigger = \{ (.*?) \}", body)
                self.assertEqual(triggers, ["colonial_empire_live_tier < 1"] +
                                 [f"colonial_empire_live_tier >= {t}" for t in (5, 4, 3, 2)])
        loc = _loc()["je_colonial_empire_ov_next"]
        self.assertIn("ScriptValue('colonial_empire_live_next_boundary')", loc)
        self.assertNotIn("Var('colonial_empire_next_boundary')", loc)

    def test_the_snapshot_comes_from_the_ladder(self):
        refresh = _block(_read(DISPLAY), "colonial_empire_refresh_display")
        self.assertIn("set_variable = { name = colonial_empire_tier value = colonial_empire_live_tier }", refresh)
        self.assertIn("set_variable = { name = colonial_empire_next_boundary value = colonial_empire_live_next_boundary }",
                      refresh)
        self.assertEqual(len(re.findall(r"name = colonial_empire_tier\b", refresh)), 1)


class QuietTooltipsTest(unittest.TestCase):
    """Play-test round 1 (2026-09-29): the journal panel renders on_complete and
    on_fail as tooltips every frame, so a bare var: read of a counter that does
    not exist yet, or a remove_modifier of a modifier the scope lacks, logged an
    error per frame."""

    def test_no_bare_read_of_the_programme_months(self):
        je = _read(JE)
        decol = _read(DECOLONIZATION)
        for name, body in (("on_complete", _block_in(je, "on_complete")), ("on_fail", _block_in(je, "on_fail")),
                           ("decol_path_legacy", _block(decol, "decol_path_legacy"))):
            with self.subTest(block=name):
                self.assertNotRegex(body, r"var:colonial_(invest|garrison|assimilate)_months")
                self.assertRegex(body, r"colonial_(invest|garrison|assimilate)_months_value")
        values = _read(VALUES)
        for m in MONTHS:
            with self.subTest(counter=m):
                body = _block(values, f"colonial_{m}_months_value")
                self.assertIn(f"has_variable = colonial_{m}_months", body)
                self.assertIn(f"value = var:colonial_{m}_months", body)

    def test_every_remove_modifier_in_the_cleanup_is_guarded(self):
        cleanup = _strip_comments(_block(_read(DECOLONIZATION), "colonial_empire_je_cleanup_effect"))
        removes = re.findall(r"remove_modifier = (\w+)", cleanup)
        self.assertEqual(len(removes), 9)
        for mod in removes:
            with self.subTest(modifier=mod):
                self.assertEqual(len(re.findall(rf"remove_modifier = {mod}\b", cleanup)),
                                 len(re.findall(rf"if = \{{ limit = \{{ has_modifier = {mod} \}} remove_modifier = {mod} \}}",
                                                cleanup)))


def _block_in(text, name):
    """A block opened at one tab of indentation (a journal entry's own field)."""
    m = re.search(rf"(?m)^\t{name} = \{{", text)
    assert m, f"no {name}"
    a, b = _span(text, m.end() - 1)
    return text[a + 1:b]


DECISIONS = os.path.join(REPO, "common", "decisions", "extra_decisions.txt")


class CompletionClocksTest(unittest.TestCase):
    """Play-test round 2 (owner, 2026-09-29): in the top band the overview shows
    months held at 100 and, for a great power, months Solidified, each a bar
    whose end is its target. The targets are script values the triggers share."""

    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES)
        cls.body = _type_body(_read(GUI), "te_ce_overview_panel")

    def test_the_targets_are_shared_and_unchanged(self):
        self.assertRegex(self.values, r"(?m)^colonial_empire_completion_months = 60$")
        self.assertRegex(self.values, r"(?m)^colonial_empire_federation_months = 36$")
        complete = _block_in(_read(JE), "complete")
        self.assertIn("var:colonial_at_100_months >= colonial_empire_completion_months", complete)
        self.assertNotRegex(complete, r">= 60\b")
        decisions = _read(DECISIONS)
        for d in ("imperial_federation_act_iron_fist", "imperial_federation_act_civilizing_mission"):
            with self.subTest(decision=d):
                body = _block(decisions, d)
                # The guarded value: the decision panel evaluates `possible` for a
                # country whose entry has not pulsed yet (a bare var: read logged).
                self.assertIn("colonial_solidified_months_value >= colonial_empire_federation_months", body)
                self.assertNotIn("var:colonial_solidified_months", body)
                self.assertNotRegex(body, r"colonial_solidified_months(_value)? >= 36")
        self.assertRegex(self.values, r"(?s)colonial_solidified_months_value = \{\s*value = 0\s*if = \{\s*"
                                      r"limit = \{ has_variable = colonial_solidified_months \}")
        tt = _loc()["je_colonial_empire_complete_tt"]
        for sv in ("colonial_empire_completion_months", "colonial_empire_federation_months"):
            self.assertIn(f"ScriptValue('{sv}')", tt, sv)
        self.assertNotIn(".Var(", tt, "the completion tooltip reads the guarded counts")

    def test_the_clocks_show_in_the_top_band_only(self):
        m = re.search(r"### Row 4, in the top band only", self.body)
        self.assertTrue(m)
        a, b = _span(self.body, m.end())
        block = self.body[a:b]
        self.assertIn(
            "visible = \"[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('colonial_empire_disp_tier'), "
            "'(CFixedPoint)5' )]\"", self.body[m.end():a + 400])
        for frac in ("colonial_empire_disp_at_100_frac", "colonial_empire_disp_solidified_frac"):
            self.assertIn(f"ScriptValue('{frac}')", block, frac)
        self.assertIn("ScriptValue('colonial_empire_disp_act_in_reach'), '(CFixedPoint)1'", block)
        loc = _loc()
        self.assertTrue(loc["je_colonial_empire_ov_hold"].startswith("Months at 100: "))
        self.assertIn("ScriptValue('colonial_empire_completion_months')", loc["je_colonial_empire_ov_hold"])
        self.assertIn("ScriptValue('colonial_empire_federation_months')", loc["je_colonial_empire_ov_act"])

    def test_the_overview_is_pinned_to_the_column(self):
        """A frame sized by its content is centred by its first layout; the
        clocks and the alert appear later (play-test round 2)."""
        m = re.search(r"colonial_empire_panel = \{\s*(?:###.*\n\s*)*flowcontainer = \{\s*direction = vertical\s*"
                      r"spacing = 10\s*ignoreinvisible = yes\s*minimumsize = \{ 480 -1 \}\s*maximumsize = \{ 480 -1 \}",
                      self.body)
        self.assertTrue(m, "the overview's rows are not in a fixed 480 column")


class StatusLineTest(unittest.TestCase):
    """Status text that repeats the overview goes (owner, play-test round 2): an
    active entry has no status line; an inactive one says why it is not running."""

    def test_only_an_inactive_entry_has_a_status_line(self):
        status = _block_in(_read(JE), "status_desc")
        descs = re.findall(r"desc = (\w+)\s*trigger = \{(.*?)\n\t\t\t\t\}", status, re.S)
        self.assertEqual([d for d, _ in descs], ["je_colonial_empire_status_completed",
                                                 "je_colonial_empire_status_cooldown",
                                                 "je_colonial_empire_status_no_colonies"])
        for desc, trigger in descs:
            with self.subTest(desc=desc):
                self.assertIn("NOT = { has_journal_entry = je_colonial_empire }", trigger)
        self.assertIn("first_valid = {", status)
        loc = _loc()
        for desc, _ in descs:
            self.assertTrue(loc.get(desc), desc)


SGUIS = os.path.join(REPO, "common", "scripted_guis", "colonial_empire_sguis.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "colonial_empire_triggers.txt")


class TerritoryListTest(unittest.TestCase):
    """Play-test round 3 (owner, 2026-09-30): the eligible territories as a
    list, largest GDP first, each row showing how it scores on the tests, read
    through the entry's own triggers. Since 2026-10-24 it is Colonial Holdings'
    first list, open, each row with its Release button."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.body = _type_body(cls.gui, "te_ce_sec_holdings")
        cls.values = _read(VALUES)
        cls.refresh = _block(_read(DISPLAY), "colonial_empire_refresh_display")

    def test_the_list_is_open_under_the_ready_gate(self):
        m = re.search(r"te_ce_territory_row = \{", self.body)
        gates = " ".join(_enclosing_visibles(self.body, m.end()))
        self.assertIn(READY, gates)
        self.assertNotIn("GetVariableSystem.Exists('colonial_empire_holdings_closed')]", gates.replace("Not(", ""),
                         "the list sits only under the section's own (open-by-default) flag")
        self.assertNotIn("territories_open", self.gui)
        self.assertNotIn("territor", _type_body(self.gui, "te_ce_sec_stability"))

    def test_one_row_per_bloc(self):
        """CE-1 (2026-10-27): every release bloc has its row and its Release
        button, a datamodel over the stored seeds (eight fixed rows before)."""
        m = re.search(r'datamodel = "\[JournalEntry\.GetCountry\.MakeScope\.GetList\(\'colonial_empire_blocs\'\)\]"'
                      r'\s*item = \{\s*te_ce_territory_row = \{\s*datacontext = "\[Scope\.GetState\]"', self.body)
        self.assertTrue(m, "the territory rows are not a datamodel over the stored seeds")
        self.assertEqual(self.body.count("te_ce_territory_row = {"), 1)
        row_type = _type_body(self.gui, "te_ce_territory_row")
        self.assertNotIn('block "row_visible"', row_type)
        self.assertNotIn('block "row_context"', row_type)
        self.assertNotIn("Var(", row_type)
        _assert_rooted_at_the_player(self, row_type)


    def test_the_snapshot_is_by_gdp_for_players(self):
        start = self.refresh.index("clear_variable_list = colonial_empire_blocs")
        chunk = self.refresh[start:self.refresh.index("clear_variable_list = colonial_empire_subject_capitals")]
        self.assertIn("is_player = yes", chunk)
        self.assertIn("colonial_empire_mark_release_blocs = yes", chunk)
        self.assertRegex(chunk, r"ordered_scope_state = \{\s*limit = \{ has_variable = colonial_bloc_seed \}\s*"
                                r"order_by = colonial_bloc_disp_gdp\s*max = \d+\s*check_range_bounds = no\s*owner = \{\s*"
                                r"add_to_variable_list = \{ name = colonial_empire_blocs target = prev \}")
        self.assertNotIn("colonial_empire_territory_slot", _read(DISPLAY))
        self.assertIn("has_variable_list = colonial_empire_blocs",
                      _block(self.values, "colonial_empire_territory_rows_stored"))
        # The holdings line still prints the count of eligible states.
        self.assertIn("set_variable = { name = colonial_empire_eligible_count value = colonial_eligible_state_count }",
                      self.refresh)
        self.assertIn("limit = { is_decolonization_eligible_state = yes }",
                      _block(self.values, "colonial_eligible_state_count"))


    def test_the_rows_read_the_entrys_own_tests(self):
        triggers = _read(TRIGGERS)
        colonial = _block(triggers, "is_overseas_colonial_state")
        self.assertRegex(colonial, r"OR = \{\s*colonial_state_unincorporated_signal = yes\s*"
                                   r"colonial_state_indigenous_signal = yes\s*colonial_state_disparity_signal = yes\s*\}")
        # The prima facie case: separated and distinct, in the strict and the loose test alike.
        for t in ("is_overseas_colonial_state", "is_decolonization_eligible_state"):
            with self.subTest(prima_facie=t):
                self.assertIn("is_separated_from_capital = yes", _block(triggers, t))
                self.assertIn("colonial_state_distinct_people = yes", _block(triggers, t))
        for name, trig in (("indigenous", "colonial_state_indigenous_signal"),
                           ("disparity", "colonial_state_disparity_signal"),
                           ("unincorporated", "colonial_state_unincorporated_signal"),
                           ("separated", "is_separated_from_capital"),
                           ("distinct", "colonial_state_distinct_people"),
                           ("eligible", "is_decolonization_eligible_state"),
                           ("colony", "is_overseas_colonial_state")):
            with self.subTest(value=name):
                self.assertIn(f"limit = {{ {trig} = yes }}", _block(self.values, f"colonial_territory_disp_{name}"))
        self.assertIn("value = colonial_state_sol_qualifying_floor", _block(self.values, "colonial_territory_disp_sol_floor"))
        for t in ("is_overseas_colonial_state", "is_decolonization_eligible_state"):
            self.assertIn("state_population >= colonial_territory_min_population", _block(triggers, t))
        self.assertNotRegex(triggers, r"state_population >= \d")
        # The other two thresholds the hovers print are named values the tests read.
        self.assertIn("value > colonial_state_indigenous_min_share", _block(triggers, "colonial_state_indigenous_signal"))
        self.assertNotRegex(triggers, r"culture_percent_state = \{ target = prev value > \d")
        self.assertIn("multiply = colonial_state_sol_floor_share",
                      _block(self.values, "colonial_state_sol_qualifying_floor"))
        self.assertIn("average_sol < colonial_state_sol_qualifying_floor",
                      _block(triggers, "colonial_state_disparity_signal"))

    def test_each_criterion_has_its_threshold_on_hover(self):
        loc = _loc()
        row = _type_body(self.gui, "te_ce_territory_row")
        for cell, value in (("primary", "colonial_bloc_disp_indigenous"), ("sol", "colonial_bloc_disp_disparity")):
            with self.subTest(cell=cell):
                self.assertRegex(row, rf"ScriptValue\('{value}'\), '\(CFixedPoint\)1' \)\]\"\s*"
                                      rf"text = \"je_colonial_empire_territory_{cell}_bad\"\s*"
                                      rf"tooltip = \"je_colonial_empire_territory_{cell}_bad_tt\"")
                self.assertTrue(loc[f"je_colonial_empire_territory_{cell}_bad"].startswith("#R "))
                self.assertIn("#R Met", loc[f"je_colonial_empire_territory_{cell}_bad_tt"])
                self.assertIn("#G Not met", loc[f"je_colonial_empire_territory_{cell}_tt"])
        self.assertIn("colonial_territory_disp_sol_floor", loc["je_colonial_empire_territory_sol_tt"])
        self.assertIn("acceptance_status_4", loc["je_colonial_empire_territory_primary_tt"])
        self.assertIn("concept_colonial_territory", loc["je_colonial_empire_territory_head_name_tt"])
        self.assertIn("colonial_territory_min_population", loc["concept_colonial_territory_desc"])
        self.assertIn("colonial_bloc_disp_weight", loc["je_colonial_empire_bloc_weight"])
        self.assertIn("colonial_state_sol_floor_share", loc["je_colonial_empire_territory_sol_tt"])
        self.assertIn("colonial_state_indigenous_min_share", loc["je_colonial_empire_territory_primary_tt"])
        # Gotcha #24: a row's hover has no JournalEntry.
        for cell in ("primary", "sol"):
            for key in (f"je_colonial_empire_territory_{cell}_tt", f"je_colonial_empire_territory_{cell}_bad_tt"):
                self.assertNotIn("JournalEntry", loc[key], key)
        for key, value in loc.items():
            if key.startswith("je_colonial_empire_territor"):
                with self.subTest(key=key):   # editing rule 1: no number typed in a loc string
                    self.assertNotRegex(re.sub(r"\[[^\]]*\]|#\w+|\(CFixedPoint\)", "", value), r"\d")

    def test_no_row_is_left_to_a_hover(self):
        """CE-1: the "+N more" hovers and the sguis behind them are gone."""
        sguis = _read(SGUIS)
        for gone in ("colonial_empire_territories_sgui", "colonial_empire_subjects_sgui", "colonial_empire_pressure_sgui"):
            self.assertNotIn(f"{gone} = {{", sguis, gone)
            self.assertNotIn(gone, self.gui, gone)
        self.assertNotIn("colonial_empire_more_territory_line", _read(DISPLAY))
        self.assertNotIn("_more'", self.gui)
        self.assertNotIn("colonial_empire_disp_territories_more", self.values)
        self.assertNotIn("colonial_empire_disp_subjects_more", self.values)


    def test_the_cleanup_clears_the_blocs(self):
        cleanup = _block(_read(DECOLONIZATION), "colonial_empire_je_cleanup_effect")
        self.assertIn("colonial_bloc_clear_state = yes", cleanup)
        self.assertNotIn("colonial_territory_primary_share", cleanup, "nothing sets it any more")


class ReleaseBlocTest(unittest.TestCase):
    """Owner's request (2026-10-24): Henan and Southern Anhui, neighbours and
    both homelands of the Han alone, were two rows, though releasing either
    takes the other. The list shows one row per release bloc: a territory and
    the states its release would take with it."""

    @classmethod
    def setUpClass(cls):
        cls.display = _read(DISPLAY)
        cls.values = _read(VALUES)
        cls.mark = _block(cls.display, "colonial_empire_mark_release_blocs")
        cls.seed = _block(cls.display, "colonial_bloc_seed_here")
        cls.member = _block(cls.display, "colonial_bloc_add_member")
        cls.clear = _block(cls.display, "colonial_bloc_clear_state")

    def test_seeds_are_taken_largest_first_and_skip_covered_states(self):
        self.assertRegex(self.mark, r"ordered_scope_state = \{\s*limit = \{ is_decolonization_eligible_state = yes \}"
                                    r"\s*order_by = gdp\s*max = \d+\s*check_range_bounds = no")
        self.assertRegex(self.mark, r"limit = \{ NOT = \{ has_variable = colonial_bloc_covered \} \}\s*colonial_bloc_seed_here = yes")
        # Last month's marks go first.
        self.assertLess(self.mark.index("colonial_bloc_clear_state = yes"), self.mark.index("ordered_scope_state"))

    def test_the_region_is_the_one_a_release_takes(self):
        # The same flood-fill and culture pick .402's preview and the release use.
        self.assertIn("_decolonization_preview_region = {", self.seed)
        self.assertIn("decol_choose_release_culture = { CULTURE_SCOPE = colonial_bloc_member_culture }", self.member)

    def test_a_member_is_covered_only_if_its_own_release_forms_with_the_same_people(self):
        self.assertRegex(self.member, r"scope:colonial_bloc_member_culture = \{ this = scope:colonial_bloc_culture_pick \}"
                                      r"\s*\}\s*set_variable = colonial_bloc_covered")
        self.assertIn("is_decolonization_eligible_state = yes", self.member)

    def test_the_sums_read_each_states_own_tests(self):
        for value in ("colonial_territory_disp_gdp", "colonial_territory_disp_population",
                      "colonial_territory_disp_colony", "colonial_territory_disp_indigenous",
                      "colonial_territory_disp_disparity", "colonial_territory_disp_weight_acceptance"):
            with self.subTest(value=value):
                self.assertIn(f"value = {value} }}", self.member)

    def test_the_clear_removes_every_bloc_variable(self):
        written = set(re.findall(r"set_variable = \{ name = (colonial_bloc_\w+)", self.seed + self.member))
        written |= set(re.findall(r"set_variable = (colonial_bloc_\w+)", self.seed + self.member))
        written |= set(re.findall(r"change_variable = \{ name = (colonial_bloc_\w+)", self.member))
        self.assertGreater(len(written), 10)
        for var in written:
            with self.subTest(var=var):
                self.assertIn(f"remove_variable = {var}\n", self.clear + "\n")
        self.assertIn("clear_variable_list = colonial_bloc_members", self.clear)

    def test_the_bloc_values_guard_their_variables(self):
        names = re.findall(r"(?m)^(colonial_bloc_disp_\w+) = \{", self.values)
        self.assertGreater(len(names), 8)
        for name in names:
            body = _block(self.values, name)
            for var in re.findall(r"(?<!owner\.)var:(\w+)", body):
                with self.subTest(value=name, var=var):
                    self.assertIn(f"has_variable = {var}", body)

    def test_the_name_hover_lists_the_bloc(self):
        row = _type_body(_read(GUI), "te_ce_territory_row")
        self.assertIn("datacontext = \"[GetScriptedGui('colonial_empire_bloc_sgui')]\"", row)
        self.assertIn("AddScope( 'ce_state', State.MakeScope )", row)
        self.assertIn("je_colonial_empire_territory_name_extra", row)
        # A bloc's name and its "+N" share the name cell.
        widths = [int(w) for w in re.findall(r"max_width = (\d+)", row[row.index("flowcontainer = {", row.index("colonial_empire_bloc_sgui")):row.index("je_colonial_empire_territory_name_extra")])]
        name_cell = int(re.search(r"size = \{ (\d+) \d+ \}\s*parentanchor = vcenter\s*datacontext = \"\[GetScriptedGui\('colonial_empire_bloc_sgui'\)\]\"",
                                  row).group(1))
        self.assertEqual(widths[-2] + 4 + widths[-1], name_cell)
        sgui = _block(_read(SGUIS), "colonial_empire_bloc_sgui")
        self.assertEqual([int(n) for n in re.findall(r"colonial_empire_bloc_member_line = \{ POS = (\d+) \}", sgui)],
                         list(range(8)))
        line = _block(self.display, "colonial_empire_bloc_member_line")
        self.assertIn("colonial_bloc_disp_states > $POS$", line)


class ProjectionBarTest(unittest.TestCase):
    """Play-test round 3: the overview's bar in the Global Warming bar's five
    layers, green while stability rises (good) and red while it falls (bad),
    with the next band's edge as a thin line. No eye marker."""

    @classmethod
    def setUpClass(cls):
        body = _type_body(_read(GUI), "te_ce_overview_panel")
        m = re.search(r"widget = \{\s*size = \{ 180 18 \}", body)
        assert m, "no 180 x 18 bar cell"
        a, b = _span(body, m.start())
        cls.bar = body[a + 1:b]
        cls.values = _read(VALUES)

    LAYER = r"(?m)^\t{8}(?!size\b)(\w+) = \{"

    def _layers(self):
        return [self.bar[slice(*_span(self.bar, m.start()))] for m in re.finditer(self.LAYER, self.bar)]

    def test_five_layers_in_order(self):
        names = re.findall(self.LAYER, self.bar)
        self.assertEqual(names, ["default_progressbar_horizontal", "widget", "widget",
                                 "default_progressbar_horizontal", "progressbar"])
        base, rising, falling, solid, tick = self._layers()
        self.assertRegex(base, r"value = 0\s*min = 0\s*max = 1")
        self.assertNotIn('blockoverride "background" {}', base)
        # Rising is good: green, the stretch up to where it is heading.
        self.assertIn("alpha = 0.4", rising)
        self.assertIn("ScriptValue('colonial_empire_disp_trend'), '(CFixedPoint)1' )", rising)
        self.assertIn("green_progressbar_horizontal = {", rising)
        self.assertIn("ScriptValue('colonial_empire_disp_bar_high_frac')", rising)
        # Falling is bad: red, the stretch from where it is heading up to today.
        self.assertIn("alpha = 0.5", falling)
        self.assertIn("ScriptValue('colonial_empire_disp_trend'), '(CFixedPoint)-1' )", falling)
        self.assertIn("bad_progressbar_horizontal = {", falling)
        self.assertIn("ScriptValue('colonial_empire_disp_bar_high_frac')", falling)
        for layer in (rising, falling, solid):
            self.assertIn('blockoverride "background" {}', layer)
            self.assertIn('blockoverride "frame" {}', layer)
        self.assertIn("ScriptValue('colonial_empire_disp_bar_low_frac')", solid)
        self.assertIn("ScriptValue('colonial_empire_disp_next_boundary_frac')", tick)
        self.assertIn("ScriptValue('colonial_empire_disp_next_tick'), '(CFixedPoint)1' )", tick)
        self.assertRegex(tick, r"marker = \{\s*icon = \{\s*size = \{ 3 24 \}")
        self.assertIn('texture = "gfx/interface/backgrounds/white.dds"', tick)
        self.assertIn("color = { 0.96 0.90 0.72 0.95 }", tick)
        self.assertIn('tooltip = "je_colonial_empire_ov_tick_tt"', tick)

    def test_low_and_high_are_today_and_the_projection(self):
        low = _block(self.values, "colonial_empire_disp_bar_low_frac")
        high = _block(self.values, "colonial_empire_disp_bar_high_frac")
        self.assertRegex(low, r"^\s*value = colonial_empire_live_bar\s*if = \{\s*limit = \{ colonial_empire_disp_projected < "
                              r"colonial_empire_live_bar \}\s*value = colonial_empire_disp_projected")
        self.assertRegex(high, r"^\s*value = colonial_empire_live_bar\s*if = \{\s*limit = \{ colonial_empire_disp_projected > "
                               r"colonial_empire_live_bar \}\s*value = colonial_empire_disp_projected")
        proj = _block(self.values, "colonial_empire_disp_projected")
        self.assertIn("value = colonial_stability_drift_total_display", proj)
        self.assertIn("multiply = colonial_empire_projection_months", proj)
        self.assertIn("add = colonial_empire_live_bar", proj)

    def test_the_whole_number_ladder_reads_the_bar(self):
        live = _block(self.values, "colonial_empire_live_bar")
        ns = {int(n) for n in re.findall(r"colonial_stability_bar_at_least = \{ N = (\d+) \}", live)}
        self.assertEqual(ns, set(range(0, 101)))
        trig = _block(_read(TRIGGERS), "colonial_stability_bar_at_least")
        self.assertIn('je:je_colonial_empire ?= { "scripted_bar_progress(colonial_stability_bar)" >= $N$ }', trig)

    def test_the_tooltips_explain_the_colours(self):
        # CE-11: the value's hover is the projection; How it Works explains the colours.
        tt = _loc()["je_colonial_empire_ov_heading_tt"]
        self.assertIn("colonial_empire_disp_projected", tt)
        self.assertIn("assessed again every month", tt)
        self.assertNotIn("green", tt)
        how = _loc()["je_colonial_empire_how_bar_2"]
        self.assertIn("#G green#!", how)
        self.assertIn("#R red#!", how)
        self.assertNotIn("marker", how)
        self.assertIn("thin line", how)
        # The band's own rule is the concept's, linked rather than repeated.
        self.assertIn("[concept_colonial_band]", how)
        self.assertNotIn("radicalize", how)
        self.assertTrue(_loc()["je_colonial_empire_status_stable"].startswith("#G "), "the Stable band reads green")


# Play-test round 3, rule 1: nothing a player reads may end in "...". Units per
# character, from the owner's screenshots (the coordinator's measurements): the
# serif face about 10 a character at 20, the tooltip face about 8.6 at 16 (the
# Banking panel's WidthBudgetTest). The panel's sizes are its own templates
# (colonial_empire_fontsize_row, _heading, _overview: 17, 20 and 16 since the
# 2026-10-27 GUI audit, CE-11), read from the file, so a change of type is
# followed here. Plus 10%.
def _template_sizes():
    return {m.group(1): int(m.group(2)) for m in re.finditer(
        r"(?m)^template colonial_empire_fontsize_(\w+) \{\s*fontsize = (\d+)", _read(GUI))}


_SIZES = _template_sizes()
UNITS = {"row": 10.0 / 20 * _SIZES["row"], "heading": 10.0 / 20 * _SIZES["heading"],
         "overview": 8.6 / 16 * _SIZES["overview"]}
MARGIN = 1.1
# The longest name each dynamic cell can show. State names: the longest land
# state region's, "South Atlantic Islands" and "Indian Ocean Territory", 22
# characters (vanilla's map_data/state_regions, seas left out).
LONGEST_STATE = "South Atlantic Islands"


def _visible_text(value):
    """What a loc value shows: concept links become their display text, and
    formatting codes and data reads are dropped (the caller supplies data)."""
    value = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", r"\1", value)
    names = {"concept_turmoil": "Turmoil", "concept_great_power": "Great Power", "concept_interest_group": "Interest Group",
             "concept_acceptance": "Acceptance", "concept_colonial_overreach": _loc()["concept_colonial_overreach"],
             "concept_colonial_stability": _loc()["concept_colonial_stability"]}
    value = re.sub(r"\[(concept_\w+)(?:\|\w+)?\]", lambda m: names[m.group(1)], value)
    value = re.sub(r"#!|#\w+ ?", "", value)
    return value


def _cells(body, key_prefix, keys=None):
    """{suffix: (width, font)} for each textbox in `body` whose text is a key
    starting with `key_prefix` (only those suffixes in `keys`, when given),
    the width its max_width (or maximumsize)."""
    found = {}
    for m in re.finditer(r"textbox = \{", body):
        box = body[slice(*_span(body, m.start()))]
        text = re.search(rf'text = "{key_prefix}(\w+)"', box)
        if not text or (keys is not None and text.group(1) not in keys):
            continue
        width = re.search(r"max_width = (\d+)|maximumsize = \{ (\d+) -1 \}", box)
        font = re.search(r"using = colonial_empire_fontsize_(\w+)", box)
        assert width and font, box
        found[text.group(1)] = (int(width.group(1) or width.group(2)), font.group(1))
    return found


class WidthBudgetTest(unittest.TestCase):
    """Every label in a fixed-width cell fits it by the round-3 estimate. The
    cell widths and fonts are read from the .gui, so narrowing a cell or
    raising its type fails here."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.loc = _loc()
        g = cls.gui
        cls.pillar = _type_body(g, "colonial_empire_pillar_row")
        cls.territory_head = _cells(_type_body(g, "te_ce_territory_head"), "je_colonial_empire_territory_head_")
        cls.subject_head = _cells(_type_body(g, "te_ce_subject_head"), "je_colonial_empire_subject_head_")
        cls.war_head = _cells(_type_body(g, "te_ce_war_head"), "je_colonial_empire_war_head_")
        cls.gp_head = _cells(_type_body(g, "te_ce_gp_head"), "je_colonial_empire_gp_head_")
        cls.territory_row = _cells(_type_body(g, "te_ce_territory_row"), "je_colonial_empire_territory_")
        cls.subject_row = _cells(_type_body(g, "te_ce_subject_row"), "je_colonial_empire_subject_")
        cls.war_row = _cells(_type_body(g, "te_ce_war_row"), "je_colonial_empire_war_")
        cls.gp_row = _cells(_type_body(g, "te_ce_gp_row"), "je_colonial_empire_gp_")
        cls.buttons = {}
        for t in ("te_ce_territory_row", "te_ce_subject_row", "te_ce_war_row", "colonial_empire_decision_row"):
            cls.buttons.update(_cells(_type_body(g, t), "je_colonial_empire_btn_"))
        row = _type_body(g, "te_ce_territory_row")
        cls.name_cell = int(re.search(r'max_width = (\d+)[^}]*?text = "\[State\.GetName\]"', row, re.S).group(1))
        ov = _type_body(g, "te_ce_overview_panel")
        cls.ov = ov
        cls.ov_cells = _cells(ov, "je_colonial_empire_ov_", keys=("stability_label", "stability_value"))
        cls.policy = _type_body(g, "colonial_empire_policy_row")
        cls.escalation = _type_body(g, "te_ce_escalation_row")

    def assertFits(self, text, font, cell, what):
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, cell, f"{what}: {text!r} needs ~{need:.0f} of {cell} ({font})")

    def _check(self, key, width, font):
        text = _visible_text(self.loc[key])
        self.assertNotIn("...", text)
        self.assertNotIn("…", text)
        self.assertFits(text, font, width, key)

    def test_the_templates_are_the_house_ladder(self):
        self.assertEqual(_SIZES, {"row": 17, "heading": 20, "overview": 16})
        self.assertNotRegex(self.gui, r"using = fontsize_(small|medium|large)\b",
                            "every textbox uses the panel's own templates")

    def test_static_labels(self):
        label = re.findall(r"maximumsize = \{ (\d+) -1 \}", self.pillar)
        self.assertIn("using = colonial_empire_fontsize_row", self.pillar)
        for g, _ in TABLE:
            with self.subTest(key=g):
                self._check(f"je_colonial_empire_drift_{g}", int(label[0]), "row")
        self.assertEqual(set(self.territory_head), {"name", "primary", "sol", "gdp"})
        self.assertEqual(set(self.subject_head), {"name", "kind", "gdp"})
        self.assertEqual(set(self.war_head), {"name", "months", "backers"})
        self.assertEqual(set(self.gp_head), {"name", "stance", "prestige", "effect"})
        for prefix, cells in (("territory_head", self.territory_head), ("subject_head", self.subject_head),
                              ("war_head", self.war_head), ("gp_head", self.gp_head), ("btn", self.buttons)):
            for k, (w, font) in cells.items():
                with self.subTest(key=f"{prefix}_{k}"):
                    self.assertEqual(font, "row", "column heads and buttons are at the row size")
                    self._check(f"je_colonial_empire_{prefix}_{k}", w, font)
        self.assertEqual(set(self.buttons), {"release", "dominion", "open_talks", "in_talks", "accords", "open_choice"})
        for k in ("condemning", "supporting"):
            with self.subTest(key=k):
                self._check(f"je_colonial_empire_gp_{k}", *self.gp_row[k])
        label_w = int(re.search(r"maximumsize = \{ (\d+) -1 \}", self.policy).group(1))
        for p in ("invest", "garrison", "assimilation"):
            with self.subTest(programme=p):
                self._check(f"je_colonial_empire_row_{p}_short", label_w, "row")
        esc_w = int(re.search(r"maximumsize = \{ (\d+) -1 \}", self.escalation).group(1))
        for k in ("isolation", "consensus"):
            with self.subTest(escalation=k):
                self._check(f"je_colonial_empire_pressure_{k}", esc_w, "row")

    def test_overview_cells(self):
        """The four cells' captions, words and figures fit the cell's 154 column
        at the overview's size, as Banking's do."""
        captions = re.findall(r'blockoverride "caption" \{\s*text = "(\w+)"', self.ov)
        self.assertEqual(len(captions), 4)
        for key in captions:
            with self.subTest(key=key):
                self._check(key, 154, "overview")
        lines = [re.search(r'text = "(\w+)"', self.ov[slice(*_span(self.ov, m.start()))]).group(1)
                 for m in re.finditer(r"te_ce_ov_line = \{", self.ov)]
        self.assertEqual(len(lines), 14)   # band 5 + 1, great powers 3 + 1, holdings 2, programmes 2
        line = _type_body(self.gui, "te_ce_ov_line")
        self.assertIn("max_width = 154", line)
        self.assertIn("using = colonial_empire_fontsize_overview", line)
        static = [k for k in lines if "[" not in self.loc[k] or k.startswith("je_colonial_empire_band_")]
        for key in static:
            with self.subTest(key=key):
                self._check(key, 154, "overview")
        dynamic = [("Solidified at 90", "the next band"), ("Colonies: 99", "the colonies"),
                   ("Subjects: 99", "the subjects"), ("3 of 3 running", "the programmes running"),
                   ("+12.34/mo", "the programmes' figure"), ("-12.34/mo", "the great powers' figure")]
        for text, what in dynamic:
            with self.subTest(what=what):
                self.assertFits(text, "overview", 154, what)

    def test_longest_dynamic_texts(self):
        self.assertEqual(set(self.territory_row), {"name_extra", "primary", "primary_bad", "sol", "sol_bad", "gdp"})
        for cell in ("primary", "sol"):   # the red figure takes its cell's width
            self.assertEqual(self.territory_row[cell], self.territory_row[f"{cell}_bad"])
        self.assertEqual(set(self.subject_row), {"name", "ld", "gdp"})
        pillar_value = int(re.findall(r"maximumsize = \{ (\d+) -1 \}", self.pillar)[1])
        ov_value = self.ov_cells["stability_value"]
        ov_label = self.ov_cells["stability_label"]
        legend = _cells(_type_body(self.gui, "te_ce_ov_legend_row").replace('block "legend_text" {}',
                                                                            'text = "je_colonial_empire_x"'),
                        "je_colonial_empire_")["x"]
        level = int(re.search(r'max_width = (\d+)[^}]*?block "row_level"', self.policy, re.S).group(1))
        term = int(re.search(r'max_width = (\d+)[^}]*?block "row_term"', self.policy, re.S).group(1))
        gp_prestige = int(re.search(r"max_width = (\d+)[^}]*?colonial_gp_row_disp_prestige", _type_body(self.gui, "te_ce_gp_row"),
                                    re.S).group(1))
        esc_value = int(re.findall(r"maximumsize = \{ (\d+) -1 \}", self.escalation)[1])
        cases = [
            (LONGEST_STATE, "row", self.name_cell, "a territory's name"),
            ("+99", *self.territory_row["name_extra"][::-1], "a bloc's other states"),
            ("100%", *self.territory_row["primary"][::-1], "primary share"),
            ("99.9", *self.territory_row["sol"][::-1], "standard of living"),
            ("999.99M", *self.territory_row["gdp"][::-1], "a territory's GDP"),
            ("999.99M", *self.subject_row["gdp"][::-1], "a subject's GDP"),
            ("100", *self.subject_row["ld"][::-1], "a subject's liberty desire"),
            ("120", *self.war_row["months"][::-1], "months at war"),
            ("3", *self.war_row["backers"][::-1], "backers"),
            ("-1.20/mo", *self.gp_row["effect"][::-1], "a great power's weight"),
            ("9999", "row", gp_prestige, "a great power's prestige"),
            ("-2.00/mo", "row", esc_value, "an escalation's loss"),
            ("Stability", ov_label[1], ov_label[0], "the bar's label"),
            ("100% (-1.67/mo)", ov_value[1], ov_value[0], "the overview's value"),
            ("-10.00", "row", pillar_value, "a term's value"),
            ("Supporting: 100%", legend[1], legend[0], "the pie's legend"),
            ("3 / 3", "row", level, "a programme's level"),
            ("+1.50/mo", "row", term, "a programme's stability"),
        ]
        for text, font, cell, what in cases:
            with self.subTest(what=what):
                self.assertFits(text, font, cell, what)


SGUIS = os.path.join(REPO, "common", "scripted_guis", "colonial_empire_sguis.txt")
# Each programme's row in te_ce_sec_programmes, its op codes (raise, lower) and
# the helpers colonial_empire_policy_sgui calls for them.
STEPPERS = [("invest", 0, 1), ("garrison", 2, 3), ("assimilation", 4, 5)]


class ProgrammeStepperTest(unittest.TestCase):
    """Each programme is a level, 0-3, with a minus and a plus (2026-10). Both
    controls are always drawn and grey out through IsValid; each addresses the
    op codes the scripted GUI maps to that programme's down and up steps."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.section = _type_body(cls.gui, "te_ce_sec_programmes")
        sgui = _read(SGUIS)
        cls.policy = _block(sgui, "colonial_empire_policy_sgui")

    def _rows(self):
        return [self.section[slice(*_span(self.section, m.start()))]
                for m in re.finditer(r"colonial_empire_policy_row = \{", self.section)]

    def test_each_row_steps_its_own_programme(self):
        rows = self._rows()
        self.assertEqual(len(rows), len(STEPPERS))
        for (p, up, down), row in zip(STEPPERS, rows):
            with self.subTest(programme=p):
                self.assertIn(f'text = "je_colonial_empire_level_{p}"', row)
                for block, op in (("up_action", up), ("down_action", down)):
                    body = row[slice(*_span(row, row.index(f'blockoverride "{block}"')))]
                    ops = set(re.findall(r"\(CFixedPoint\)(\d+)", body))
                    self.assertEqual(ops, {str(op)}, block)
                    self.assertNotIn("visible", body, "a stepper is always drawn")
                    for prop in ("enabled", "onclick", "tooltip"):
                        self.assertRegex(body, rf"\b{prop} = ")

    def test_the_op_table_maps_to_the_steps(self):
        for p, up, down in STEPPERS:
            for op, way in ((up, "up"), (down, "down")):
                with self.subTest(op=op):
                    self.assertRegex(self.policy, rf"scope:op = {op} \}}\s*colonial_empire_possible_{p}_{way} = yes")
                    self.assertRegex(self.policy, rf"scope:op = {op} \}}\s*colonial_empire_effect_{p}_{way} = yes")

    def test_the_level_reads_the_guarded_value(self):
        loc = _loc()
        for p, value in (("invest", "colonial_invest_level_value"), ("garrison", "colonial_garrison_level_value"),
                         ("assimilation", "colonial_assim_level_value")):
            with self.subTest(programme=p):
                self.assertIn(f"ScriptValue('{value}')", loc[f"je_colonial_empire_level_{p}"])
                self.assertNotIn("Var(", loc[f"je_colonial_empire_level_{p}"])


class PressureTableTest(unittest.TestCase):
    """CE-2 (2026-10-27): International Pressure is a row per great power with
    a stance and what it does to stability a month, built at the monthly
    assessment, the same weight the bar's own terms give it."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.section = _type_body(cls.gui, "te_ce_sec_pressure")
        cls.display = _read(DISPLAY)
        cls.values = _read(VALUES)

    def test_a_row_per_container(self):
        self.assertRegex(self.section, r'datamodel = "\[JournalEntry\.GetCountry\.MakeScope\.GetList\(\'colonial_empire_gp_rows\'\)\]"'
                                       r'\s*item = \{\s*te_ce_gp_row = \{\s*datacontext = "\[Scope\.GetScriptContainer\]"')
        self.assertIn("IsDataModelEmpty( JournalEntry.GetCountry.MakeScope.GetList('colonial_empire_gp_rows') )", self.section)
        self.assertIn('text = "je_colonial_empire_pressure_none"', self.section)
        self.assertNotIn("ExecuteTooltip", self.section, "no script-built text")
        row = _type_body(self.gui, "te_ce_gp_row")
        # The covert rows' proven chain to a country (gotcha #15).
        self.assertIn('datacontext = "[ScriptContainer.MakeScope.Var(\'ce_gp_capital\').GetState.GetCountry]"', row)
        for value in ("colonial_gp_row_disp_stance", "colonial_gp_row_disp_prestige"):
            self.assertIn(f"ScriptValue('{value}')", row)
        self.assertIn("colonial_gp_row_disp_weight", _loc()["je_colonial_empire_gp_effect"])
        _assert_rooted_at_the_player(self, row)

    def test_the_rows_weigh_each_power_as_the_bar_does(self):
        refresh = _block(self.display, "colonial_empire_refresh_gp_rows")
        for stance, per in (("gp_anti_colonial_stance", "colonial_gp_condemnation_per_power"),
                            ("gp_pro_colonial_stance", "colonial_gp_support_per_power")):
            with self.subTest(stance=stance):
                self.assertRegex(refresh, rf"limit = \{{\s*NOT = \{{ this = scope:ce_gp_empire \}}\s*"
                                          rf"country_rank >= rank_value:great_power\s*has_variable = {stance}\s*\}}"
                                          rf"\s*order_by = prestige[^}}]*?PER = {per} \}}")
        for term, per in (("colonial_stability_term_gp_condemnation", "colonial_gp_condemnation_per_power"),
                          ("colonial_stability_term_gp_support", "colonial_gp_support_per_power")):
            self.assertIn(f"multiply = {per}", _block(self.values, term))
        # Condemners first.
        self.assertLess(refresh.index("gp_anti_colonial_stance"), refresh.index("gp_pro_colonial_stance"))
        row = _block(self.display, "colonial_empire_gp_row")
        weight = _block(_read(VALUES), "colonial_gp_condemnation_weight")
        for clamp in ("min = 0.25", "max = 2"):
            self.assertIn(clamp, row)
            self.assertIn(clamp, weight)
        self.assertIn("multiply = $PER$", row)
        self.assertIn("exists = scope:ce_gp_new", row, "every use of a new container is guarded")

    def test_the_rows_are_rebuilt_not_stacked(self):
        refresh = _block(self.display, "colonial_empire_refresh_gp_rows")
        self.assertLess(refresh.index("colonial_empire_clear_gp_rows = yes"), refresh.index("is_player = yes"))
        clear = _block(self.display, "colonial_empire_clear_gp_rows")
        self.assertIn("hidden_effect = {", clear)
        self.assertLess(clear.index("add_to_temporary_list = ce_gp_old_rows"), clear.index("clear_variable_list = colonial_empire_gp_rows"))
        self.assertLess(clear.index("clear_variable_list = colonial_empire_gp_rows"), clear.index("destroy_container = yes"))
        self.assertIn("colonial_empire_refresh_gp_rows = yes", _block(self.display, "colonial_empire_refresh_display"))

    def test_the_escalations_read_the_bars_own_losses(self):
        for name, term in (("isolation", "colonial_stability_term_gp_high_pressure"),
                           ("consensus", "colonial_stability_term_gp_extreme_pressure")):
            with self.subTest(escalation=name):
                self.assertIn(f"add = colonial_gp_{name}_loss", _block(self.values, term))
                self.assertIn(f"ScriptValue('colonial_gp_{name}_loss')", _loc()[f"je_colonial_empire_pressure_{name}_value"])
                self.assertIn(f'text = "je_colonial_empire_pressure_{name}"', self.section)


class ProgrammeRowTest(unittest.TestCase):
    """CE-6 (2026-10-27): a programme's row is its name, level, stability a
    month and the stepper, all at the row size; its costs are on the hover."""

    def test_the_row_and_its_hover(self):
        gui = _read(GUI)
        self.assertNotIn('"row_cost"', gui)
        section = _type_body(gui, "te_ce_sec_programmes")
        loc = _loc()
        for p, term in (("invest", "colonial_stability_term_invest"), ("garrison", "colonial_stability_term_garrison"),
                        ("assimilation", "colonial_stability_term_assim")):
            with self.subTest(programme=p):
                self.assertIn(f'text = "je_colonial_empire_term_{p}"', section)
                self.assertIn(f"ScriptValue('{term}')", loc[f"je_colonial_empire_term_{p}"])
                self.assertIn(f'text = "je_colonial_empire_row_{p}_short"', section)
                tt = loc[f"je_colonial_empire_tt_{p}"]
                self.assertIn("\\nUpkeep: ", tt)
                self.assertIn("\\nOne-off: ", tt)
                self.assertNotIn("Bar contribution", tt, "the row shows it")
                self.assertIn(".GetDesc]", tt)
        self.assertIn("change_infamy = colonial_garrison_start_infamy",
                      _block(_read(DECOLONIZATION), "colonial_programme_garrison_up"))
        self.assertIn("colonial_garrison_start_infamy", loc["je_colonial_empire_tt_garrison"])


class SubjectRowSelfCheckTest(unittest.TestCase):
    """CE-1 rests on State.GetCountry from a datamodel item, which nothing in
    this mod had proven (gotcha #15). The first subject row drawn reports once a
    game, TE_SELF_CHECK OK|BROKEN ce_subject_row, and the play-test list names
    the fallback (CLAUDE.md "In-game checks")."""

    def test_the_row_reports_once(self):
        row = _type_body(_read(GUI), "te_ce_subject_row")
        flag = "GetVariableSystem.Exists('colonial_empire_selfcheck_subject')"
        for check, name_gate in (("1", "Not( EqualTo_string( State.GetCountry.GetNameNoFormatting, '' ) )"),
                                 ("0", "EqualTo_string( State.GetCountry.GetNameNoFormatting, '' )")):
            with self.subTest(check=check):
                m = re.search(r"widget = \{\s*size = \{ 1 1 \}\s*visible = \"\[And\( Not\( " + re.escape(flag) + r" \), "
                              + re.escape(name_gate) + r" \)\]\"\s*state = \{\s*name = _show\s*on_start = \"([^\"]*)\"\s*"
                              r"on_start = \"\[GetVariableSystem\.Set\( 'colonial_empire_selfcheck_subject', '1' \)\]\"", row)
                self.assertTrue(m, check)
                self.assertIn("GetScriptedGui('colonial_empire_selfcheck_subject_sgui').Execute(", m.group(1))
                self.assertIn(f"AddScope( 'ce_check', MakeScopeValue( '(CFixedPoint){check}' ) )", m.group(1))
                self.assertIn("AddScope( 'ce_capital', State.MakeScope )", m.group(1))
        # Outside the row's flow, so the two 1x1 widgets take no room.
        self.assertLess(row.rindex("size = { 1 1 }"), row.index("flowcontainer = {"))

    def test_the_handler_logs_once_a_game(self):
        sgui = _block(_read(SGUIS), "colonial_empire_selfcheck_subject_sgui")
        self.assertIn("saved_scopes = { ce_capital ce_check }", sgui)
        self.assertIn("ai_is_valid = { always = no }", sgui)
        self.assertIn("NOT = { has_global_variable = te_selfcheck_ce_subject_row }", sgui)
        self.assertIn("set_global_variable = te_selfcheck_ce_subject_row", sgui)
        self.assertIn("scope:ce_capital = { exists = owner }", sgui, "a capital with no owner is no test")
        self.assertIn('debug_log = "TE_SELF_CHECK OK ce_subject_row', sgui)
        self.assertIn('debug_log = "TE_SELF_CHECK BROKEN ce_subject_row', sgui)
        self.assertNotIn("SCOPE.s", sgui, "a saved scope does not print reliably in debug_log")
        playtest = _read(os.path.join(REPO, "docs", "testing", "colonial-holdings-playtest.md"))
        self.assertIn("ce_subject_row", playtest)


class LocHygieneTest(unittest.TestCase):
    def test_new_concepts_are_defined_and_named(self):
        concepts = _read(CONCEPTS)
        loc = _loc()
        for c in ("concept_colonial_band", "concept_colonial_overreach", "concept_colonial_territory",
                  "concept_overseas_colony", "concept_colonial_subject"):
            self.assertRegex(concepts, rf"(?m)^{c} = \{{\}}", c)
            self.assertTrue(loc.get(c) and loc.get(f"{c}_desc"), c)

    def test_no_tooltip_or_line_ends_in_a_blank_line(self):
        for key, value in _loc().items():
            if key.startswith(("je_colonial_empire_", "concept_colonial_")):
                with self.subTest(key=key):
                    self.assertFalse(value.startswith("\\n") or value.endswith("\\n"), value)

    def test_no_text_mixes_words_and_data(self):
        # `text = "[X] / 100"` logs "Unlocalized text": a text is a loc key or one binding.
        for n, line in enumerate(_read(GUI).splitlines(), 1):
            for m in re.finditer(r'(?<![\w])text\s*=\s*"([^"]*)"', line):
                if "[" in m.group(1):
                    with self.subTest(line=n):
                        self.assertTrue(m.group(1).startswith("[") and m.group(1).endswith("]")
                                        and m.group(1).count("[") == 1, m.group(1))


class LiberationContagionTest(unittest.TestCase):
    """2026-10-10 report: ~20 Colonial Crisis modifiers at once. Every country
    form_decolonized_country creates runs apply_decolonization_path, which hands
    the other empires a 12-month Colonial Crisis, and Planned Full Decolonization
    (decolonization_events.401.a, the AI's ce_planned_decolonization) forms one
    country per eligible state in a single effect. A same-name add_modifier
    stacks, so each empire must take one copy at a time, guarded by a variable
    the loop's next pass can read at once."""

    def setUp(self):
        decol = _read(DECOLONIZATION)
        # apply_decolonization_path calls the contagion once for every country it forms.
        self.assertIn("decol_path_contagion = yes", _block(decol, "apply_decolonization_path"))
        self.path = _strip_comments(_block(decol, "decol_path_contagion"))

    def _contagion_blocks(self):
        blocks = []
        for m in re.finditer(r"every_country = \{", self.path):
            a, b = _span(self.path, m.end() - 1)
            if "colonial_stability_negative_event" in self.path[a:b]:
                blocks.append(self.path[a + 1:b])
        return blocks

    def test_the_crisis_is_handed_out_once_and_only_by_the_guarded_walk(self):
        self.assertEqual(len(re.findall(r"colonial_stability_negative_event", self.path)), 1)
        self.assertEqual(len(self._contagion_blocks()), 1)

    def test_an_empire_holds_one_contagion_at_a_time(self):
        body = self._contagion_blocks()[0]
        a, b = _span(body, body.index("limit = {") + len("limit = {") - 1)
        self.assertRegex(body[a:b], r"NOT = \{ has_variable = decol_liberation_contagion \}")
        guard = re.search(r"set_variable = \{ name = decol_liberation_contagion months = (\d+) \}", body)
        crisis = re.search(r"name = colonial_stability_negative_event\s+months = (\d+)", body)
        self.assertTrue(guard and crisis, body)
        self.assertEqual(guard.group(1), crisis.group(1))


class DecolonizedCultureScopeTest(unittest.TestCase):
    """A saved scope lasts until the whole effect chain ends, and decolonization
    events .201 / .204 (up to three) and .401.a (one per marked state) call
    form_decolonized_country more than once in one option. The culture used to
    be saved only when a branch found one, so a capital with no homeland culture
    found the previous country's still set, skipped both fallbacks and formed
    with it. The pick is decol_choose_release_culture now (2026-10-24), shared
    with .402's preview: it clears its scope first, and its steps test what the
    call has found in a local variable, never the scope's `exists`."""

    # Saved by the helper's first two statements on every call, and read after
    # the create (the helper's tail, apply_decolonization_path), so never cleared.
    FRESH = ("new_country_capital", "decolonizing_parent")

    @classmethod
    def setUpClass(cls):
        decol = _read(DECOLONIZATION)
        cls.helper = _strip_comments(_block(decol, "form_decolonized_country"))
        cls.legacy = _strip_comments(_block(decol, "apply_decolonization_path") + _block(decol, "decol_path_legacy")
                                     + _block(decol, "decol_path_contagion"))
        cls.pick = _strip_comments(_block(decol, "decol_choose_release_culture"))

    def test_the_capital_and_parent_are_saved_on_every_call(self):
        self.assertRegex(self.helper, r"\A\s*save_scope_as = new_country_capital\s+"
                                      r"owner = \{ save_scope_as = decolonizing_parent \}")
        for name in self.FRESH:
            with self.subTest(scope=name):
                self.assertNotIn(f"clear_saved_scope = {name}", self.helper + self.legacy)

    def test_the_culture_is_picked_afresh_before_its_first_use(self):
        tested = set(re.findall(r"exists = scope:(\w+)", self.helper + self.legacy)) - set(self.FRESH)
        self.assertEqual(tested, {"new_country_culture"}, "a new scope tested by exists needs a clear")
        first = re.search(r"\bnew_country_culture\b", self.helper)
        self.assertEqual(first.start(), self.helper.index(
            "decol_choose_release_culture = { CULTURE_SCOPE = new_country_culture }") + len(
            "decol_choose_release_culture = { CULTURE_SCOPE = "))

    def test_the_pick_clears_its_scope_first_and_never_tests_it(self):
        clear = re.search(r"if = \{\s*limit = \{ exists = scope:\$CULTURE_SCOPE\$ \}\s*"
                          r"clear_saved_scope = \$CULTURE_SCOPE\$\s*\}", self.pick)
        self.assertIsNotNone(clear)
        self.assertEqual(self.pick.count("exists = scope:$CULTURE_SCOPE$"), 1, "the steps read local_var, not exists")
        self.assertLess(clear.start(), self.pick.index("every_scope_culture"))
        self.assertIn("local_var:decol_release_culture_best <= 0", self.pick)

if __name__ == "__main__":
    unittest.main()
