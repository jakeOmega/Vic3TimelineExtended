"""The Cultural Hegemony panels' layout (gui_style_guide.md pass, after test_un_layout.py).

One order of sections for both hosts (the journal entry and the Society panel's
Hegemony tab), collapse flags that say their default, explanations gathered in
How Cultural Hegemony Works, state-gated lines gated, and an overview whose
codes, textures and display values agree with the script behind them.
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
WIDGET = os.path.join(REPO, "gui", "journal_entry_widgets", "cultural_hegemony_widget.gui")
TAB = os.path.join(REPO, "gui", "culture_panel.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_cultural_hegemony.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "cultural_hegemony_sguis.txt")
VALUES = os.path.join(REPO, "common", "script_values", "cultural_hegemony_script_values.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "cultural_hegemony_effects.txt")
CUSTOM_LOC = os.path.join(REPO, "common", "customizable_localization", "cultural_hegemony_custom_loc.txt")
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")
ICONS_DOC = os.path.join(REPO, "docs", "systems", "cultural_hegemony_gui_icons.md")

STATUS = ["te_ch_sec_programmes", "te_ch_sec_breakdown", "te_ch_sec_board", "te_ch_sec_models"]
REFERENCE = ["te_ch_sec_history", "te_ch_sec_how"]
COMPOSERS = ["te_ch_overview_panel", "te_ch_status_sections", "te_ch_reference_sections"]
ROOTS = {   # named root -> (container, composer)
    "widget_je_ch_overview": ("custom_widget_container_1", "te_ch_overview_panel"),
    "widget_je_ch_status": ("custom_widget_container_2", "te_ch_status_sections"),
    "widget_je_ch_reference": ("custom_widget_container_3", "te_ch_reference_sections"),
}
OLD_FLAGS = ["ch_breakdown_open", "ch_board_open", "ch_models_open", "ch_hist_open"]
OLD_TYPES = ["te_ch_summary_panel", "te_ch_programmes_panel", "te_ch_standing_panel", "ch_reading_row"]

# Explanations that live in How Cultural Hegemony Works, never in a live section.
HOW_KEYS = ["je_ch_how_share", "je_ch_how_programmes", "je_ch_how_pull", "je_ch_how_board",
            "je_ch_widget_models_legend", "je_ch_how_models", "je_ch_how_benchmark"]

# Placeholder art (docs/systems/cultural_hegemony_gui_icons.md): what is set now,
# and the path the final art is proposed for. Swapping one in changes both.
PLACEHOLDERS = {
    "tier": ("gfx/interface/icons/event_icons/je_cultural_hegemony.dds", "gfx/interface/icons/ch_icons/tier_"),
    "benchmark": ("gfx/interface/icons/generic_icons/warning.dds", "gfx/interface/icons/ch_icons/benchmark.dds"),
    "share pie fill": ("gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_liberal.dds",
                       "gfx/interface/journal_entry_widgets/ch_model_pie/ch_share_fill.dds"),
    "share pie rest": ("gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_other.dds",
                       "gfx/interface/journal_entry_widgets/ch_model_pie/ch_share_rest.dds"),
}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return _braced(text, m.end() - 1)


def _braced(text, open_idx):
    depth = 0
    for j in range(open_idx, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:j]
    raise AssertionError("unbalanced")


def _block(text, name):
    m = re.search(rf"^{name} = \{{", text, re.M)
    assert m, f"no block {name}"
    return _braced(text, m.end() - 1)


def _root(text, name):
    m = re.search(rf'flowcontainer = \{{\s*name = "{name}"', text)
    assert m, f"no root {name}"
    return _braced(text, text.index("{", m.start()))


def _loc():
    vals = {}
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        for line in _read(path).splitlines():
            m = re.match(r'^ ([\w.\-]+):\d* "(.*)"\s*$', line)
            if m:
                vals[m.group(1)] = m.group(2)
    return vals


class OrderTest(unittest.TestCase):
    """One order of sections, for the journal entry and the Society tab alike."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(WIDGET)

    def test_status_and_reference_order(self):
        for composer, expected in (("te_ch_status_sections", STATUS), ("te_ch_reference_sections", REFERENCE)):
            found = re.findall(r"^\t\t(te_ch_sec_\w+) = \{", _type_body(self.gui, composer), re.M)
            self.assertEqual(found, expected, composer)

    def test_composers_gate_on_an_active_entry(self):
        for composer in COMPOSERS:
            with self.subTest(composer=composer):
                self.assertIn('visible = "[JournalEntry.IsActive]"', _type_body(self.gui, composer))

    def test_the_entry_attaches_three_thin_roots(self):
        je = _read(JE)
        for root, (container, composer) in ROOTS.items():
            with self.subTest(root=root):
                self.assertRegex(je, rf'name = "{root}"\s*container = "{container}"')
                body = _root(self.gui, root)
                self.assertIn('visible = "[JournalEntry.IsActive]"', body)
                self.assertEqual(re.findall(r"^\t(\w+) = \{", body, re.M), [composer])
        self.assertEqual(je.count('gui = "gui/journal_entry_widgets/cultural_hegemony_widget.gui"'), 3)

    def test_the_tab_composes_the_same_sections_then_the_link(self):
        tab = _read(TAB)
        start = tab.index('name = "te_society_ch_tab"')
        body = tab[start:tab.index("### END MOD ###", start)]
        found = re.findall(r"^\t+(te_ch_\w+) = \{\}", body, re.M)
        self.assertEqual(found, COMPOSERS)
        # The link back to the entry comes after every section.
        self.assertGreater(body.index('text = "te_system_tab_open_journal"'), body.index("te_ch_reference_sections"))
        # The gate sits on a parent of the widget carrying the GetPlayerJournalEntry datacontext.
        gate = body.index("GetScriptedGui('te_society_ch_tab_sgui').IsShown")
        self.assertLess(gate, body.index("GetPlayerJournalEntry('je_cultural_hegemony')"))

    def test_the_greyed_tab_keeps_its_unlock_checklist(self):
        tab = _read(TAB)
        self.assertIn("GetScriptedGui('te_society_ch_tab_unlock_sgui').IsValidTooltip", tab)
        self.assertIn("enabled = \"[GetScriptedGui('te_society_ch_tab_sgui').IsShown", tab)

    def test_no_old_type_survives(self):
        for path in (WIDGET, TAB):
            for name in OLD_TYPES:
                with self.subTest(file=os.path.basename(path), name=name):
                    self.assertNotRegex(_read(path), rf"\b{name}\b")


class FlagTest(unittest.TestCase):
    """_closed: open until closed; _open: collapsed until opened (as test_un_layout.FlagTest)."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(WIDGET)

    def test_section_flags_say_their_default(self):
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.text))
        self.assertEqual(flags, {"ch_programmes_closed", "ch_breakdown_closed", "ch_board_closed",
                                 "ch_models_closed", "ch_hist_closed", "ch_how_open"})
        for f in flags:
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", self.text))
            bare = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", self.text)) - negated
            if f.endswith("_closed"):
                self.assertEqual(bare, 1, f)
                self.assertGreaterEqual(negated, 2, f)
            else:
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 2, f)

    def test_each_section_owns_its_flag(self):
        for sec, flag in (("te_ch_sec_programmes", "ch_programmes_closed"), ("te_ch_sec_breakdown", "ch_breakdown_closed"),
                          ("te_ch_sec_board", "ch_board_closed"), ("te_ch_sec_models", "ch_models_closed"),
                          ("te_ch_sec_history", "ch_hist_closed"), ("te_ch_sec_how", "ch_how_open")):
            with self.subTest(section=sec):
                self.assertIn(f"GetVariableSystem.Toggle('{flag}')", _type_body(self.text, sec))

    def test_no_old_flag_survives(self):
        for path in (WIDGET, TAB):
            for f in OLD_FLAGS:
                self.assertNotIn(f"'{f}'", _read(path), f)


class HowItWorksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(WIDGET)

    def test_explanations_live_in_how_it_works(self):
        how = _type_body(self.gui, "te_ch_sec_how")
        for key in HOW_KEYS:
            self.assertIn(f'"{key}"', how, key)
        # It opens on a heading, not an empty line.
        first = re.search(r'ch_subheader = \{\s*blockoverride "subheader_margin" \{\}', how)
        self.assertTrue(first and how.index("ch_subheader") == first.start())

    def test_live_sections_carry_no_explanations(self):
        for sec in ["te_ch_overview_panel"] + STATUS + ["te_ch_sec_history"]:
            body = _type_body(self.gui, sec)
            for key in HOW_KEYS + ["je_ch_widget_board_legend"]:
                with self.subTest(section=sec, key=key):
                    self.assertNotIn(f'"{key}"', body)

    def test_the_boards_bracket_is_one_hover_away(self):
        board = _type_body(self.gui, "te_ch_sec_board")
        self.assertEqual(board.count("Localize( 'je_ch_board_row_hint_tt' )"), 10)


class StateGatedTest(unittest.TestCase):
    """Lines that matter in one state are shown only in it (style rule 7)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(WIDGET)

    def _visible_of(self, body, marker):
        i = body.index(marker)
        opener = [m.start() for m in re.finditer(r"\w+ = \{[ \t]*\n", body[:i])][-1]
        m = re.search(r'visible = "\[(.*?)\]"', body[opener:i])
        self.assertTrue(m, f"no visible before {marker}")
        return m.group(1)

    def test_our_rank_line_only_outside_the_top_ten(self):
        board = _type_body(self.gui, "te_ch_sec_board")
        gate = self._visible_of(board, 'text = "je_ch_widget_board_us"')
        self.assertEqual(gate, "GreaterThanOrEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope"
                               ".ScriptValue('ch_rank_self_display'), '(CFixedPoint)11' )")

    def test_ministry_line_only_without_the_ministry(self):
        progs = _type_body(self.gui, "te_ch_sec_programmes")
        gate = self._visible_of(progs, 'text = "je_ch_prog_needs_ministry"')
        self.assertIn("GetScriptedGui('ch_ministry_missing_sgui').IsShown", gate)
        # Said once, above the rows.
        self.assertLess(progs.index("je_ch_prog_needs_ministry"), progs.index("button_icon_minus_action"))

    def test_models_pending_only_before_the_first_census(self):
        models = _type_body(self.gui, "te_ch_sec_models")
        gate = self._visible_of(models, 'text = "je_ch_widget_models_pending"')
        self.assertTrue(gate.startswith("Not( ScriptedGui.IsShown("), gate)
        self.assertIn("'(CFixedPoint)12'", gate)

    def test_overview_cells_gated(self):
        ov = _type_body(self.gui, "te_ch_overview_panel")
        self.assertIn("GetScriptedGui('ch_benchmark_sgui').IsShown", self._visible_of(ov, "je_ch_ov_benchmark_tt"))
        rank = self._visible_of(ov, 'tooltip = "je_ch_widget_rank_tt"')
        self.assertIn("ScriptValue('ch_rank_self_display'), '(CFixedPoint)1'", rank)
        self.assertIn("ScriptValue('ch_ranked_total_display'), '(CFixedPoint)1'", rank)
        model = self._visible_of(ov, 'tooltip = "je_ch_ov_model_tt"')
        self.assertIn("ScriptValue('ch_disp_model_code'), '(CFixedPoint)1'", model)

    def test_scope_free_gates_are_display_only(self):
        sguis = _read(SGUIS)
        for name, trigger in (("ch_ministry_missing_sgui", "has_law = law_type:law_ministry_of_culture"),
                              ("ch_benchmark_sgui", "has_modifier = cultural_hegemony_foreign_benchmark")):
            with self.subTest(sgui=name):
                body = _block(sguis, name)
                self.assertNotIn("saved_scopes", body)
                self.assertIn(trigger, body)
                self.assertRegex(body, r"is_valid = \{\s*always = no\s*\}")
                self.assertRegex(body, r"ai_is_valid = \{\s*always = no\s*\}")
                self.assertRegex(body, r"effect = \{ \}")


class OverviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ov = _type_body(_read(WIDGET), "te_ch_overview_panel")

    def _coded(self, value):
        """{code: (texture, label key)} for the cells gated on ScriptValue(value) == code."""
        found = {}
        pat = (rf"visible = \"\[EqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('{value}'\), "
               rf"'\(CFixedPoint\)(-?\d+)' \)\]\"")
        for m in re.finditer(pat, self.ov):
            # the cell whose `visible` this is: the block opened on the line above
            opener = [o.start() + o.group(0).index("{") for o in re.finditer(r"\w+ = \{[ \t]*\n", self.ov[:m.start()])][-1]
            cell = _braced(self.ov, opener)
            tex = re.search(r'texture = "([^"]+)"', cell)
            label = re.search(r'text = "(\w+)"', cell)
            found[int(m.group(1))] = (tex and tex.group(1), label and label.group(1))
        return found

    def test_every_tier_has_a_cell(self):
        cells = self._coded("ch_disp_tier_code")
        self.assertEqual(sorted(cells), list(range(6)))
        for n, (_, label) in cells.items():
            self.assertEqual(label, f"je_ch_ov_tier_{n}")

    def test_each_model_code_draws_its_own_slice_colour(self):
        # code -> model, as the exported-model custom loc reads global_var:ch_rank_1_ideology
        text = _block(_read(CUSTOM_LOC), "ch_exported_model_text")
        codes = {int(c): m for c, m in re.findall(
            r"global_var:ch_rank_1_ideology = (\d+) \}\s*localization_key = ch_model_(\w+)", text)}
        self.assertEqual(sorted(codes), list(range(1, 16)))
        cells = self._coded("ch_disp_model_code")
        self.assertEqual(sorted(cells), list(range(1, 16)))
        for n, model in codes.items():
            with self.subTest(code=n):
                tex, label = cells[n]
                self.assertEqual(tex, f"gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_{model}.dds")
                self.assertEqual(label, f"je_ch_ov_model_{model}")

    def test_the_trend_has_three_arrows(self):
        cells = self._coded("ch_disp_share_trend")
        self.assertEqual({n: t for n, (t, _) in cells.items()},
                         {1: "gfx/interface/icons/generic_icons/trend_up.dds",
                          -1: "gfx/interface/icons/generic_icons/trend_down.dds",
                          0: "gfx/interface/icons/generic_icons/trend_nochange.dds"})

    def test_the_share_is_a_pie_fed_a_fraction(self):
        self.assertIn("te_ch_ov_pie = {", self.ov)
        self.assertIn("ScriptValue('ch_disp_share_frac')", self.ov)
        pie = _type_body(_read(WIDGET), "te_ch_ov_pie")
        self.assertIn('texture = "gfx/interface/backgrounds/round_frame_dec.dds"', pie)
        self.assertEqual(pie.count("max = 1"), 2)


class DisplayDataTest(unittest.TestCase):
    """The overview's numbers come from guarded, display-only script values."""

    def test_every_script_value_the_panels_read_exists(self):
        values = set(re.findall(r"^(\w+) = ", _read(VALUES), re.M))
        text = _read(WIDGET) + "\n".join(v for k, v in _loc().items() if k.startswith(("je_ch_", "ch_policy_")))
        for sv in set(re.findall(r"ScriptValue\('(\w+)'\)", text)):
            with self.subTest(value=sv):
                self.assertIn(sv, values)

    def test_every_read_is_guarded(self):
        values = _read(VALUES)
        for name in ("ch_disp_tier_code", "ch_disp_share_delta", "ch_disp_model_code"):
            body = _block(values, name)
            for kind, var in re.findall(r"\b(var|global_var):(\w+)", body):
                with self.subTest(value=name, var=var):
                    guard = "has_variable" if kind == "var" else "has_global_variable"
                    self.assertIn(f"{guard} = {var}", body)

    def test_the_snapshot_is_taken_before_the_share_is_recomputed(self):
        body = _block(_read(EFFECTS), "ch_monthly_country_update")
        snap = body.index("set_variable = { name = ch_total_prev value = var:ch_total }")
        self.assertLess(snap, body.index("set_variable = { name = ch_total value = cultural_pull_total }"))
        self.assertIn("has_variable = ch_total", body[:snap])

    def test_nothing_but_the_display_reads_the_snapshot(self):
        readers = []
        for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True) + \
                glob.glob(os.path.join(REPO, "events", "**", "*.txt"), recursive=True):
            if "ch_total_prev" in _read(path):
                readers.append(os.path.relpath(path, REPO))
        self.assertEqual(sorted(readers), sorted([os.path.relpath(EFFECTS, REPO), os.path.relpath(VALUES, REPO)]))


class ControlsTest(unittest.TestCase):
    """Buttons carry their own reasons (style rule 6, gotcha #16)."""

    def test_every_policy_control_composes_its_tooltip(self):
        gui = _read(WIDGET)
        for op in range(10):
            scope = f"AddScope( 'op', MakeScopeValue( '(CFixedPoint){op}' ) ).End"
            with self.subTest(op=op):
                self.assertIn(f"enabled = \"[ScriptedGui.IsValid( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).{scope} )]\"", gui)
                self.assertIn(f"onclick = \"[ScriptedGui.Execute( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).{scope} )]\"", gui)
                self.assertIn(f"tooltip = \"[Concatenate( ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).{scope} ), "
                              f"Concatenate( Localize( 'te_tt_break' ), ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).{scope} ) ) )]\"", gui)

    def test_the_enable_disable_swap_never_rests_on_a_saved_scope(self):
        gui = _read(WIDGET)
        for prog in ("world_exposition", "cultural_institutes", "global_media_campaign", "cultural_protectionism"):
            with self.subTest(programme=prog):
                self.assertIn(f"visible = \"[Not(GetScriptedGui('ch_active_{prog}_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ))]\"", gui)
                self.assertIn(f"visible = \"[GetScriptedGui('ch_active_{prog}_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]\"", gui)

    def test_the_funding_row_shares_the_programme_rows_columns(self):
        gui = _read(WIDGET)
        row = _type_body(gui, "ch_programme_row")
        progs = _type_body(gui, "te_ch_sec_programmes")
        funding = progs[progs.index("### Funding stepper"):progs.index("ch_programme_row = {")]
        cols = [int(w) for w in re.findall(r"size = \{ (\d+) 2[68] \}", row)] + [112]   # ch_action_button is 112 wide
        self.assertEqual([int(w) for w in re.findall(r"^\t{4}widget = \{\s*size = \{ (\d+) \d+ \}", funding, re.M)], cols)


class LocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = _loc()

    def test_every_key_the_panels_name_exists(self):
        for path in (WIDGET,):
            for key in set(re.findall(r'\b(?:text|tooltip) = "([a-z]\w+)"', _read(path))):
                with self.subTest(key=key):
                    self.assertIn(key, self.loc)
            for key in set(re.findall(r"Localize\( '(\w+)' \)", _read(path))):
                self.assertIn(key, self.loc)

    def test_no_new_line_starts_or_ends_blank(self):
        for key, val in self.loc.items():
            if key.startswith(("je_ch_ov_", "je_ch_how_", "je_ch_prog_", "je_ch_board_row_hint", "concept_ch_influence_tier",
                               "concept_ch_exported_model")):
                with self.subTest(key=key):
                    self.assertFalse(val.startswith("\\n") or val.endswith("\\n"), val)

    def test_new_concepts_are_registered_and_named(self):
        concepts = _read(CONCEPTS)
        for c in ("concept_ch_influence_tier", "concept_ch_exported_model"):
            with self.subTest(concept=c):
                self.assertRegex(concepts, re.compile(rf"^{c} = \{{\}}", re.M))
                self.assertIn(c, self.loc)
                self.assertIn(f"{c}_desc", self.loc)

    def test_the_pull_multiplier_is_a_concept(self):
        self.assertIn("Concept('concept_ch_modifier_bonus'", self.loc["je_ch_widget_bd_mult_label"])


class PlaceholderTest(unittest.TestCase):
    """Every placeholder is set where the doc says, and the doc names its final path."""

    def test_each_placeholder_is_listed(self):
        gui = _read(WIDGET)
        doc = _read(ICONS_DOC)
        for what, (now, proposed) in PLACEHOLDERS.items():
            with self.subTest(placeholder=what):
                self.assertIn(f'texture = "{now}"', gui)
                self.assertIn(now, doc)
                self.assertIn(proposed, doc)


if __name__ == "__main__":
    unittest.main()
