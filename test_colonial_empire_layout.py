"""The Colonial Empire panels' layout (docs/guides/gui_style_guide.md): the
section order, the collapse defaults, the overview and its gates, and where
the explanations went. Modelled on test_un_layout.py."""
import glob
import os
import re
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
OLD_FLAGS = ["colonial_empire_history_open"]
PROGRAMMES = ("invest", "garrison", "assimilation")

# The explanations "How the Colonial Empire Works" holds, and the live
# sections they must not reappear in.
HOW_KEYS = ["je_colonial_empire_how_bar_1", "je_colonial_empire_how_bar_2", "je_colonial_empire_how_bar_3",
            "je_colonial_empire_how_moves", "je_colonial_empire_how_pressure",
            "je_colonial_empire_how_programmes", "je_colonial_empire_how_decolonization"]
RETIRED_KEYS = ["je_colonial_empire_bar_headline", "je_colonial_empire_band_headline",
                "je_colonial_empire_conditions_body", "je_colonial_empire_phase_row",
                "je_colonial_empire_candidates_row"]
# The nine drift groups, the monthly limit and the total, and where each reads.
TABLE = [("base", "ScriptValue('colonial_stability_drift_base')"),
         ("laws", "ScriptValue('colonial_stability_drift_laws')"),
         ("igs", "ScriptValue('colonial_stability_drift_igs')"),
         ("rank", "ScriptValue('colonial_stability_drift_rank')"),
         ("policies", "ScriptValue('colonial_stability_drift_policies')"),
         ("domestic", "ScriptValue('colonial_stability_drift_domestic')"),
         ("overreach", "Var('colonial_empire_d_overreach')"),
         ("gp", "Var('colonial_empire_d_gp')"),
         ("acceptance", "Var('colonial_empire_d_acceptance')"),
         ("cap", "ScriptValue('colonial_stability_drift_cap_display')"),
         ("total", "ScriptValue('colonial_stability_drift_total_display')")]
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
                          ("te_ce_sec_programmes", "colonial_empire_programmes_closed"),
                          ("te_ce_sec_decisions", "colonial_empire_decisions_closed"),
                          ("te_ce_sec_history", "colonial_empire_history_closed"),
                          ("te_ce_sec_how", "colonial_empire_how_open")):
            self.assertIn(f"GetVariableSystem.Toggle('{flag}')", _type_body(self.text, sec), sec)

    def test_international_pressure_says_why_it_is_collapsed(self):
        """The one exception to rule 1: its roster walks every country per frame."""
        self.assertIn("GetVariableSystem.Toggle('colonial_empire_pressure_open')",
                      _type_body(self.text, "te_ce_sec_pressure"))
        m = re.search(r"((?:\t### .*\n)+)\ttype te_ce_sec_pressure = ", self.text)
        self.assertTrue(m)
        self.assertIn("AGAINST style rule 1", m.group(1))
        self.assertIn("every_country", m.group(1))

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
        self.assertIn("JournalEntry.GetCurrentBarProgress(ScriptedProgressBar.Self)", item)
        self.assertIn("ScriptValue('colonial_empire_disp_next_boundary_frac')", item)
        self.assertIn('blockoverride "on_top_of_the_progressbar"', item)
        # Gotcha #24: a tooltip inside a datamodel item has no JournalEntry.
        self.assertEqual(re.findall(r'tooltip = "([^"]*)"', item), ["[ScriptedProgressBar.GetPeriodicProgressBreakdown]"])
        codes = {int(n) for n in re.findall(
            r"ScriptValue\('colonial_empire_disp_trend'\), '\(CFixedPoint\)(-?\d+)'", item)}
        self.assertEqual(codes, {-1, 0, 1})
        for arrow in ("trend_up", "trend_down", "trend_nochange"):
            self.assertIn(f"generic_icons/{arrow}.dds", item)

    def test_pressure_pie_and_alerts(self):
        self.assertIn("ScriptValue('colonial_empire_disp_condemner_share')", self.body)
        self.assertIn("GetScriptedGui('colonial_empire_pressure_sgui').ExecuteTooltip", self.body)
        codes = {int(n) for n in re.findall(
            r"ScriptValue\('colonial_empire_disp_pressure_level'\), '\(CFixedPoint\)(\d+)'", self.body)}
        self.assertEqual(codes, {1, 2})


class DisplayScriptTest(unittest.TestCase):
    def test_display_values_guard_every_variable(self):
        values = _read(VALUES)
        names = re.findall(r"(?m)^(colonial_empire_disp_\w+) = \{", values)
        self.assertEqual(len(names), 5)
        gui = _read(GUI)
        for name in names:
            with self.subTest(value=name):
                self.assertIn(f"ScriptValue('{name}')", gui, f"{name} is not read by the panel")
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

    def test_the_groups_are_a_table(self):
        self.assertEqual(self.body.count("colonial_empire_value_row = {"), len(TABLE))
        order = []
        for group, read in TABLE:
            with self.subTest(group=group):
                self.assertIn(f'tooltip = "je_colonial_empire_drift_{group}_tt"', self.body)
                self.assertIn(f'text = "je_colonial_empire_drift_{group}"', self.body)
                self.assertIn(f"MakeScope.{read}", self.body)
                order.append(self.body.index(f'text = "je_colonial_empire_drift_{group}"'))
        self.assertEqual(order, sorted(order))

    def test_every_variable_read_is_gated(self):
        """Every .Var( read in the panel, in a text or in the loc it names, sits
        under the display_ready (or has_candidates) gate: the entry is shown
        while inactive (gotcha #14)."""
        loc = _loc()
        text = _strip_comments(self.gui)
        checked = 0
        for m in re.finditer(r'\btext = "([^"]*)"', text):
            value = m.group(1)
            reads = value if "[" in value else loc.get(value, "")
            if ".Var(" not in reads:
                continue
            checked += 1
            with self.subTest(text=value):
                gates = " ".join(_enclosing_visibles(text, m.start()))
                self.assertTrue(READY in gates or HAS_CANDIDATES in gates, value)
        self.assertGreaterEqual(checked, 7)   # three drift groups, three candidate rows, the next band


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


if __name__ == "__main__":
    unittest.main()
