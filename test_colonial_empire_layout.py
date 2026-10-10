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

STATUS = ["te_ce_sec_stability", "te_ce_sec_pressure", "te_ce_sec_programmes", "te_ce_sec_decisions"]
REFERENCE = ["te_ce_sec_history", "te_ce_sec_how"]
ROOTS = {   # root name -> (what it instances, the journal container it is attached to)
    "widget_je_colonial_empire_overview": ("te_ce_overview_panel", "custom_widget_container_1"),
    "widget_je_colonial_empire_status": ("te_ce_status_sections", "custom_widget_container_2"),
    "widget_je_colonial_empire_reference": ("te_ce_reference_sections", "custom_widget_container_3"),
}
OLD_ROOTS = ["widget_je_colonial_empire", "widget_je_colonial_empire_history"]
OLD_FLAGS = ["colonial_empire_history_open", "colonial_empire_pressure_open"]
PROGRAMMES = ("invest", "garrison", "assimilation")

# The explanations "How the Colonial Empire Works" holds, and the live
# sections they must not reappear in.
HOW_KEYS = ["je_colonial_empire_how_bar_1", "je_colonial_empire_how_bar_2", "je_colonial_empire_how_bar_3",
            "je_colonial_empire_how_moves", "je_colonial_empire_how_pressure",
            "je_colonial_empire_how_programmes", "je_colonial_empire_how_decolonization"]
RETIRED_KEYS = ["je_colonial_empire_status_summary", "je_colonial_empire_ov_pie_label",
                "je_colonial_empire_bar_headline", "je_colonial_empire_band_headline",
                "je_colonial_empire_conditions_body", "je_colonial_empire_phase_row",
                "je_colonial_empire_candidates_row"]
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
HAS_CANDIDATES = "GetScriptedGui('colonial_empire_has_candidates').IsShown"


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
        self.assertEqual(len(flags), 7)
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
                          ("te_ce_sec_decisions", "colonial_empire_decisions_closed"),
                          ("te_ce_sec_history", "colonial_empire_history_closed"),
                          ("te_ce_sec_how", "colonial_empire_how_open"),
                          # A list, so collapsed (play-test round 3).
                          ("te_ce_sec_stability", "colonial_empire_territories_open")):
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
        for key in ("je_colonial_empire_ov_legend_condemn", "je_colonial_empire_ov_legend_support",
                    "je_colonial_empire_ov_legend_note"):
            self.assertIn(f'text = "{key}"', self.body, key)
        loc = _loc()
        self.assertIn("colonial_empire_disp_supporter_share", loc["je_colonial_empire_ov_legend_support"])
        # The label and the hovers say the escalations count only the condemners.
        self.assertIn("only the condemning share", loc["je_colonial_empire_ov_legend_note"])
        self.assertIn("only the condemning share", loc["je_colonial_empire_pressure_support_share_note"])
        self.assertIn("does not offset", loc["je_colonial_empire_pressure_share_note"])
        self.assertIn("je_colonial_empire_pressure_support_share_tt",
                      _read(os.path.join(REPO, "common", "scripted_guis", "colonial_empire_sguis.txt")))
        self.assertIn("GetScriptedGui('colonial_empire_pressure_sgui').ExecuteTooltip", self.body)
        codes = {int(n) for n in re.findall(
            r"ScriptValue\('colonial_empire_disp_pressure_level'\), '\(CFixedPoint\)(\d+)'", self.body)}
        self.assertEqual(codes, {1, 2})


class DisplayScriptTest(unittest.TestCase):
    def test_display_values_guard_every_variable(self):
        values = _read(VALUES)
        names = re.findall(r"(?m)^(colonial_empire_disp_\w+) = \{", values)
        self.assertEqual(len(names), 40)
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
        datacontext, sits under the display_ready (or has_candidates) gate: the
        entry is shown while inactive (gotcha #14)."""
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
                self.assertTrue(READY in gates or HAS_CANDIDATES in gates, value)
        self.assertEqual(checked, 3 + 8)   # three candidate rows, eight territory rows
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
        body = _type_body(gui, "te_ce_sec_decisions")
        loc = _loc()
        for d in ("release", "round_table", "planned"):
            with self.subTest(decision=d):
                self.assertRegex(body, rf'text = "je_colonial_empire_decision_{d}"\s*'
                                       rf'tooltip = "je_colonial_empire_decision_{d}_tt"')
                self.assertNotIn("#lore", loc[f"je_colonial_empire_decision_{d}"])
                self.assertNotIn("\\n", loc[f"je_colonial_empire_decision_{d}"])
        # The counts are said once, above the three rows they grey.
        self.assertLess(body.index("je_colonial_empire_candidates_eligible"),
                        body.index("colonial_empire_decision_row = {"))


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
        """The weighting explanation moved to How it Works; the roster keeps
        our prestige and the share, the thresholds on hover."""
        self.assertNotIn("quarter", self.loc["je_colonial_empire_pressure_scaling_tt"])
        self.assertIn("quarter", self.loc["je_colonial_empire_how_pressure"])
        share = self.loc["je_colonial_empire_pressure_share_tt"]
        m = re.match(r"#tooltippable;tooltip:(\w+) ", share)
        self.assertTrue(m, share)
        note = self.loc[m.group(1)]
        for token in ("ROOT", "THIS.", "JournalEntry"):
            self.assertNotIn(token, note, "a plain-form hover has no scope (gotcha #32)")

    def test_retired_keys_are_gone(self):
        for key in RETIRED_KEYS:
            self.assertNotIn(key, self.loc, key)
            self.assertNotIn(f'"{key}"', self.gui, key)


ICONS_DOC = os.path.join(REPO, "docs", "systems", "colonial_empire_gui_icons.md")
CE_ICONS = "gfx/interface/icons/colonial_empire_icons/"
# The system's own art (PR #586), by the code or cell that draws it.
BAND_ICONS = {5: "band_solidified", 4: "band_stable", 3: "band_strained", 2: "band_crumbling", 1: "band_collapsing"}
ALERT_ICONS = {1: "alert_isolation", 2: "alert_consensus"}
PROGRAMME_ICONS = {"invest": "programme_invest", "garrison": "programme_garrison",
                   "assimilation": "programme_assimilation"}
# Vanilla textures the panel keeps as mechanics (frame, line, arrows), not art.
VANILLA_KEPT = {"gfx/interface/backgrounds/round_frame_dec.dds",
                "gfx/interface/backgrounds/white.dds",
                "gfx/interface/icons/generic_icons/transparent.dds",
                "gfx/interface/icons/generic_icons/trend_up.dds",
                "gfx/interface/icons/generic_icons/trend_down.dds",
                "gfx/interface/icons/generic_icons/trend_nochange.dds"}


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
        pat = (rf"visible = \"\[EqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('{value}'\), "
               rf"'\(CFixedPoint\)(\d+)' \)\]\"(.*?)texture = \"([^\"]+)\"")
        found = {}
        for m in re.finditer(pat, self.overview, re.S):
            found.setdefault(int(m.group(1)), m.group(3))   # the first; the clocks share code 5's gate
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
                           ("apply_decolonization_path", _block(decol, "apply_decolonization_path"))):
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
    collapsed list, largest GDP first, each row showing how it scores on the
    tests, read through the entry's own triggers."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.body = _type_body(cls.gui, "te_ce_sec_stability")
        cls.values = _read(VALUES)
        cls.refresh = _block(_read(DISPLAY), "colonial_empire_refresh_display")

    def test_the_list_is_collapsed_under_the_ready_gate(self):
        m = re.search(r"flowcontainer = \{\s*direction = vertical\s*ignoreinvisible = yes\s*spacing = 2\s*"
                      r"visible = \"\[GetVariableSystem\.Exists\('colonial_empire_territories_open'\)\]\"", self.body)
        self.assertTrue(m, "the list is not behind its _open flag")
        gates = " ".join(_enclosing_visibles(self.body, m.end()))
        self.assertIn(READY, gates)
        self.assertIn("colonial_empire_subsection_header = {", self.body)

    def test_eight_rows_each_gated_on_the_count(self):
        rows = [self.body[slice(*_span(self.body, m.start()))]
                for m in re.finditer(r"te_ce_territory_row = \{", self.body)]
        self.assertEqual(len(rows), 8)
        for k, row in enumerate(rows, 1):
            with self.subTest(row=k):
                self.assertIn(f"ScriptValue('colonial_empire_disp_territory_rows'), '(CFixedPoint){k}' )", row)
                self.assertIn(f"Var('colonial_empire_territory_{k}').GetState", row)
                # The context sits on the inner container, read only while the row is shown.
                self.assertLess(row.index('"row_visible"'), row.index('"row_context"'))
        row_type = _type_body(self.gui, "te_ce_territory_row")
        self.assertLess(row_type.index('block "row_visible"'), row_type.index("flowcontainer = {"))
        self.assertGreater(row_type.index('block "row_context"'), row_type.index("flowcontainer = {"))

    def test_the_snapshot_is_by_gdp_for_players_and_count_gated(self):
        start = self.refresh.index("remove_variable = colonial_empire_territory_1")
        chunk = self.refresh[start:]
        self.assertIn("is_player = yes", chunk)
        picks = re.findall(r"limit = \{ var:colonial_empire_eligible_count >= (\d+) \}\s*ordered_scope_state = \{"
                           r"\s*limit = \{ is_decolonization_eligible_state = yes \}\s*order_by = gdp\s*"
                           r"position = (\d+)\s*check_range_bounds = no", chunk)
        self.assertEqual([(int(a), int(b)) for a, b in picks], [(k, k - 1) for k in range(1, 9)])
        for k in range(1, 9):
            self.assertIn(f"remove_variable = colonial_empire_territory_{k}", chunk)
            self.assertIn(f"name = colonial_empire_territory_{k}", chunk)
        # The count the rows and "+N more" read is the one the decisions section prints.
        self.assertIn("set_variable = { name = colonial_empire_eligible_count value = colonial_eligible_state_count }",
                      self.refresh)
        self.assertIn("limit = { is_decolonization_eligible_state = yes }",
                      _block(self.values, "colonial_eligible_state_count"))

    def test_the_rows_read_the_entrys_own_tests(self):
        triggers = _read(TRIGGERS)
        colonial = _block(triggers, "is_overseas_colonial_state")
        self.assertRegex(colonial, r"OR = \{\s*colonial_state_indigenous_signal = yes\s*colonial_state_disparity_signal = yes\s*\}")
        for name, trig in (("indigenous", "colonial_state_indigenous_signal"),
                           ("disparity", "colonial_state_disparity_signal"),
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
        for cell, value in (("primary", "colonial_territory_disp_indigenous"), ("sol", "colonial_territory_disp_disparity")):
            with self.subTest(cell=cell):
                self.assertRegex(row, rf"ScriptValue\('{value}'\), '\(CFixedPoint\)1' \)\]\"\s*"
                                      rf"text = \"je_colonial_empire_territory_{cell}_bad\"\s*"
                                      rf"tooltip = \"je_colonial_empire_territory_{cell}_bad_tt\"")
                self.assertTrue(loc[f"je_colonial_empire_territory_{cell}_bad"].startswith("#R "))
                self.assertIn("#R Met", loc[f"je_colonial_empire_territory_{cell}_bad_tt"])
                self.assertIn("#G Not met", loc[f"je_colonial_empire_territory_{cell}_tt"])
        self.assertIn("colonial_territory_disp_sol_floor", loc["je_colonial_empire_territory_sol_tt"])
        self.assertIn("acceptance_status_4", loc["je_colonial_empire_territory_primary_tt"])
        self.assertIn("colonial_territory_min_population", loc["je_colonial_empire_territory_pop_tt"])
        self.assertIn("colonial_state_sol_floor_share", loc["je_colonial_empire_territory_sol_tt"])
        self.assertIn("colonial_state_indigenous_min_share", loc["je_colonial_empire_territory_primary_tt"])
        for key, value in loc.items():
            if key.startswith("je_colonial_empire_territor"):
                with self.subTest(key=key):   # editing rule 1: no number typed in a loc string
                    self.assertNotRegex(re.sub(r"\[[^\]]*\]|#\w+|\(CFixedPoint\)", "", value), r"\d")

    def test_more_names_the_rest_on_hover(self):
        self.assertIn("GetScriptedGui('colonial_empire_territories_sgui').ExecuteTooltip", self.body)
        sgui = _block(_read(SGUIS), "colonial_empire_territories_sgui")
        self.assertEqual([int(n) for n in re.findall(r"colonial_empire_more_territory_line = \{ POS = (\d+) \}", sgui)],
                         list(range(8, 24)))
        line = _block(_read(DISPLAY), "colonial_empire_more_territory_line")
        self.assertIn("var:colonial_empire_eligible_count > $POS$", line)
        self.assertIn("order_by = gdp", line)
        self.assertIn("is_decolonization_eligible_state = yes", line)

    def test_the_cleanup_removes_the_primary_shares(self):
        cleanup = _block(_read(DECOLONIZATION), "colonial_empire_je_cleanup_effect")
        self.assertRegex(cleanup, r"every_scope_state = \{\s*limit = \{ has_variable = colonial_territory_primary_share \}"
                                  r"\s*remove_variable = colonial_territory_primary_share")


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
        tt = _loc()["je_colonial_empire_ov_heading_tt"]
        self.assertIn("#G green#!", tt)
        self.assertIn("#R red#!", tt)
        how = _loc()["je_colonial_empire_how_bar_2"]
        self.assertNotIn("marker", how)
        self.assertIn("thin line", how)


# Play-test round 3, rule 1: nothing a player reads may end in "...". Units per
# character, from the owner's screenshots (the coordinator's measurements): the
# large row font about 10, the medium table font about 8.6; the small font about
# 7 (Global Warming's measurement, round 3). A textbox with no `using` is taken
# as medium. Plus 10%.
UNITS = {"large": 10.0, "medium": 8.6, "small": 7.0}
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


class WidthBudgetTest(unittest.TestCase):
    """Every label in a fixed-width cell fits it by the round-3 estimate. The
    cell widths are read from the .gui, so narrowing a cell fails here."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.loc = _loc()
        pillar = _type_body(cls.gui, "colonial_empire_pillar_row")
        cls.pillar_label, cls.pillar_value = (int(w) for w in re.findall(r"maximumsize = \{ (\d+) -1 \}", pillar))
        table = _type_body(cls.gui, "colonial_empire_value_row")
        cls.label_cell, cls.value_cell = (int(w) for w in re.findall(r"maximumsize = \{ (\d+) -1 \}", table))
        head = _type_body(cls.gui, "te_ce_territory_head")
        cls.head_cells = dict(re.findall(r'max_width = (\d+)[^}]*?text = "je_colonial_empire_territory_head_(\w+)"', head,
                                         re.S))
        cls.head_cells = {k: int(v) for v, k in cls.head_cells.items()} if False else \
            {k: int(v) for v, k in re.findall(r'max_width = (\d+)[^}]*?text = "je_colonial_empire_territory_head_(\w+)"',
                                              head, re.S)}
        row = _type_body(cls.gui, "te_ce_territory_row")
        cls.name_cell = int(re.search(r'max_width = (\d+)[^}]*?text = "\[State\.GetName\]"', row, re.S).group(1))
        cls.row_cells = {k: int(v) for v, k in re.findall(
            r'max_width = (\d+)[^}]*?text = "je_colonial_empire_territory_(\w+?)(?:_bad)?"', row, re.S)}
        ov = _type_body(cls.gui, "te_ce_overview_panel")
        cls.ov_label = int(re.search(r'maximumsize = \{ (\d+) -1 \}[^}]*?text = "je_colonial_empire_ov_stability_label"',
                                     ov, re.S).group(1))
        cls.ov_value = int(re.search(r'maximumsize = \{ (\d+) -1 \}[^}]*?text = "je_colonial_empire_ov_stability_value"',
                                     ov, re.S).group(1))
        cls.icon_cell = int(re.search(r"max_width = (\d+)", _type_body(cls.gui, "te_ce_ov_icon_label")).group(1))
        cls.legend_cell = int(re.search(r"max_width = (\d+)", _type_body(cls.gui, "te_ce_ov_legend_row")).group(1))
        button = _type_body(cls.gui, "colonial_empire_decision_row")
        cls.choice_cell = int(re.search(r"max_width = (\d+)", button).group(1))
        cls.level_cell = int(re.search(r'max_width = (\d+)[^}]*?block "row_level"',
                                       _type_body(cls.gui, "colonial_empire_policy_row"), re.S).group(1))

    def assertFits(self, text, font, cell, what):
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, cell, f"{what}: {text!r} needs ~{need:.0f} of {cell} ({font})")

    def test_static_labels(self):
        cases = [(f"je_colonial_empire_drift_{g}", "medium", self.pillar_label) for g, _ in TABLE]
        cases += [
            ("je_colonial_empire_candidates_eligible", "medium", self.label_cell),
            ("je_colonial_empire_candidates_round_table", "medium", self.label_cell),
            ("je_colonial_empire_candidates_largest", "medium", self.label_cell),
            ("je_colonial_empire_ov_stability_label", "medium", self.ov_label),
            ("je_colonial_empire_btn_open_choice", "small", self.choice_cell),
            ("je_colonial_empire_ov_isolation", "small", self.icon_cell),
            ("je_colonial_empire_ov_consensus", "small", self.icon_cell),
            ("je_colonial_empire_territories_header", "medium", 440 - 32),   # nested header, after its arrow
        ]
        cases += [(f"je_colonial_empire_band_{b}", "small", self.icon_cell)
                  for b in ("solidified", "stable", "strained", "crumbling", "collapsing")]
        self.assertEqual(set(self.head_cells), {"name", "pop", "primary", "sol", "gdp"})
        cases += [(f"je_colonial_empire_territory_head_{k}", "small", w) for k, w in self.head_cells.items()]
        for key, font, cell in cases:
            with self.subTest(key=key):
                text = _visible_text(self.loc[key])
                self.assertNotIn("...", text)
                self.assertNotIn("…", text)
                self.assertFits(text, font, cell, key)

    def test_longest_dynamic_texts(self):
        self.assertEqual(set(self.row_cells), {"pop", "primary", "sol", "gdp"})
        cases = [
            (LONGEST_STATE, "medium", self.name_cell, "a territory's name"),
            (LONGEST_STATE, "medium", self.value_cell, "Decolonization's Largest row"),
            ("99.99M", "medium", self.row_cells["pop"], "a territory's people"),
            ("100%", "medium", self.row_cells["primary"], "primary share"),
            ("99.9", "medium", self.row_cells["sol"], "standard of living"),
            ("999.99M", "medium", self.row_cells["gdp"], "a territory's GDP"),
            ("100% (-1.67/mo)", "medium", self.ov_value, "the overview's value"),
            ("-10.00", "medium", self.pillar_value, "a term's value"),
            ("Supporting: 100%", "medium", self.legend_cell, "the pie's legend"),
            ("999", "medium", self.value_cell, "a candidate count"),
            ("3 / 3", "medium", self.level_cell, "a programme's level"),
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


class LocHygieneTest(unittest.TestCase):
    def test_new_concepts_are_defined_and_named(self):
        concepts = _read(CONCEPTS)
        loc = _loc()
        for c in ("concept_colonial_band", "concept_colonial_overreach"):
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


class DecolonizedCultureScopeTest(unittest.TestCase):
    """A saved scope lasts until the whole effect chain ends, and decolonization
    events .201 / .204 (up to three) and .401.a (one per marked state) call
    form_decolonized_country more than once in one option. The culture is saved
    only when a branch finds one, so a capital with no homeland culture found
    the previous country's still set, skipped both fallbacks and formed with it."""

    # Saved by the helper's first two statements on every call, and read after
    # the create (the helper's tail, apply_decolonization_path), so never cleared.
    FRESH = ("new_country_capital", "decolonizing_parent")

    @classmethod
    def setUpClass(cls):
        decol = _read(DECOLONIZATION)
        cls.helper = _strip_comments(_block(decol, "form_decolonized_country"))
        cls.legacy = _strip_comments(_block(decol, "apply_decolonization_path"))

    def test_the_capital_and_parent_are_saved_on_every_call(self):
        self.assertRegex(self.helper, r"\A\s*save_scope_as = new_country_capital\s+"
                                      r"owner = \{ save_scope_as = decolonizing_parent \}")
        for name in self.FRESH:
            with self.subTest(scope=name):
                self.assertNotIn(f"clear_saved_scope = {name}", self.helper + self.legacy)

    def test_every_other_tested_scope_is_cleared_before_its_first_use(self):
        tested = set(re.findall(r"exists = scope:(\w+)", self.helper + self.legacy)) - set(self.FRESH)
        self.assertIn("new_country_culture", tested)
        for name in tested:
            with self.subTest(scope=name):
                clear = re.search(rf"if = \{{\s*limit = \{{ exists = scope:{name} \}}\s*"
                                  rf"clear_saved_scope = {name}\s*\}}", self.helper)
                self.assertIsNotNone(clear, f"form_decolonized_country never clears scope:{name}")
                first = re.search(rf"\b{name}\b", self.helper).start()
                self.assertTrue(clear.start() <= first < clear.end(),
                                f"scope:{name} is used before the clear")


if __name__ == "__main__":
    unittest.main()
