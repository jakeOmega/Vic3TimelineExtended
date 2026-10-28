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

STATUS = ["te_ch_sec_board", "te_ch_sec_programmes", "te_ch_sec_breakdown", "te_ch_sec_models"]   # board first (owner, 2026-09-29)
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

# The overview's art (PR #586; docs/systems/cultural_hegemony_gui_icons.md).
CH_ICONS = "gfx/interface/icons/ch_icons/"
CH_PIES = "gfx/interface/journal_entry_widgets/ch_model_pie/"
TIER_ICONS = ["tier_negligible", "tier_minor", "tier_moderate", "tier_significant", "tier_major", "tier_hegemon"]
# Textures the overview keeps from vanilla on purpose, and the Ministry of
# Culture's own institution icon on the programs cell (CH-9): the programs
# need the Ministry, so its icon is the cell's, not a placeholder.
VANILLA_KEPT = {"gfx/interface/backgrounds/round_frame_dec.dds", "gfx/interface/icons/generic_icons/trend_up.dds",
                "gfx/interface/icons/generic_icons/trend_down.dds", "gfx/interface/icons/generic_icons/trend_nochange.dds",
                "gfx/interface/icons/institution_icons/institution_ministry_of_culture.dds"}


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

    def test_the_boards_change_is_explained_once(self):
        # The board's Change column says what it measures once, on its head
        # (CH-2), where every row's hover used to append the same hint.
        head = _type_body(self.gui, "ch_board_head")
        self.assertIn('tooltip = "je_ch_board_head_change_tt"', head)
        self.assertNotIn("je_ch_board_row_hint_tt", self.gui)
        self.assertNotIn("je_ch_board_row_hint_tt", _loc())


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
        # The annual world history also uses the shared history clock and
        # its own guarded readers. Check actual definitions in all files.
        values = set()
        for path in glob.glob(os.path.join(REPO, "common", "script_values", "*.txt")):
            values.update(re.findall(r"^(\w+) = ", _read(path), re.M))
        text = _read(WIDGET) + "\n".join(v for k, v in _loc().items() if k.startswith(("je_ch_", "ch_policy_", "ch_model_hist_")))
        for sv in set(re.findall(r"ScriptValue\('(\w+)'\)", text)):
            with self.subTest(value=sv):
                self.assertIn(sv, values)

    def test_every_read_is_guarded(self):
        values = _read(VALUES)
        for name in ("ch_disp_tier_code", "ch_disp_share_delta", "ch_disp_model_code", "ch_disp_leader_count"):
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


class ChIconsTest(unittest.TestCase):
    """The #586 art replaces every placeholder (as test_un_overview_data.UnIconsTest)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(WIDGET)
        cls.ov = _type_body(cls.gui, "te_ch_overview_panel")
        cls.doc = _read(ICONS_DOC)

    def test_each_tier_draws_its_own_icon(self):
        found = {}
        pat = (r"visible = \"\[EqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('ch_disp_tier_code'\), "
               r"'\(CFixedPoint\)(\d+)' \)\]\"\s*blockoverride \"icon_texture\" \{\s*texture = \"([^\"]+)\"")
        for m in re.finditer(pat, self.ov):
            found[int(m.group(1))] = m.group(2)
        self.assertEqual(found, {i: f"{CH_ICONS}{n}.dds" for i, n in enumerate(TIER_ICONS)})

    def test_the_benchmark_and_the_share_pie(self):
        cell = self.ov[self.ov.index("GetScriptedGui('ch_benchmark_sgui').IsShown"):]
        self.assertEqual(re.search(r'texture = "([^"]+)"', cell).group(1), f"{CH_ICONS}benchmark.dds")
        pie = _type_body(self.gui, "te_ch_ov_pie")
        self.assertEqual(re.findall(r'texture = "([^"]+)"', pie)[-2:],
                         [f"{CH_PIES}ch_share_rest.dds", f"{CH_PIES}ch_share_fill.dds"])

    def test_no_placeholder_left(self):
        for name, text in (("overview", self.ov), ("pie", _type_body(self.gui, "te_ch_ov_pie"))):
            for path in re.findall(r'texture = "(gfx/[^"]+)"', text):
                with self.subTest(part=name, path=path):
                    self.assertTrue(path.startswith((CH_ICONS, CH_PIES)) or path in VANILLA_KEPT,
                                    f"placeholder left: {path}")

    def test_the_doc_records_each_file(self):
        for n in TIER_ICONS + ["benchmark"]:
            self.assertIn(f"`{n}.dds`", self.doc, n)
        for n in ("ch_share_fill", "ch_share_rest"):
            self.assertIn(f"`{n}.dds`", self.doc, n)
        self.assertNotIn("Placeholder now", self.doc)


class LeaderFlagsTest(unittest.TestCase):
    """The three leading powers as vanilla flags, the UN council's shape (owner, 2026-09-29)."""

    @classmethod
    def setUpClass(cls):
        cls.ov = _type_body(_read(WIDGET), "te_ch_overview_panel")
        cls.effects = _read(EFFECTS)

    def test_each_flag_reads_its_seat_behind_a_gate_on_its_parent(self):
        for n in (1, 2, 3):
            with self.subTest(seat=n):
                m = re.search(
                    r"visible = \"\[GreaterThanOrEqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('ch_disp_leader_count'\), "
                    rf"'\(CFixedPoint\){n}' \)\]\"\s*flag = \{{\s*parentanchor = center\s*"
                    rf"datacontext = \"\[JournalEntry\.GetCountry\.MakeScope\.Var\('ch_leader_seat_{n}'\)\.GetState\.GetCountry\]\"",
                    self.ov)
                self.assertTrue(m, f"seat {n}")
        self.assertEqual(len(re.findall(r"\bflag = \{", self.ov)), 3)

    def test_the_slots_keep_their_width(self):
        # each gated 70x48 widget sits in an ungated 70x48 slot
        self.assertEqual(len(re.findall(r"widget = \{\s*size = \{ 70 48 \}\s*widget = \{\s*size = \{ 70 48 \}\s*visible", self.ov)), 3)
        # and the block holding them is never hidden, or row 2 is centred
        # without it and runs past the panel when it appears (gotcha #43)
        block = self.ov[:self.ov.index('text = "je_ch_ov_leaders_label"')]
        block = block[block.rindex("flowcontainer = {"):]
        self.assertNotRegex(block, r"\bvisible = ")

    def test_seats_fill_in_order_from_guarded_ranks(self):
        seat = _block(self.effects, "ch_leaders_display_seat")
        self.assertIn("var:ch_leader_seat_count = $PREV$", seat)
        self.assertIn("has_global_variable = ch_rank_$N$", seat)
        self.assertIn("global_var:ch_rank_$N$ ?= { exists = capital }", seat)
        write = _block(self.effects, "ch_leaders_display_write")
        self.assertEqual(re.findall(r"ch_leaders_display_seat = \{ N = (\d) PREV = (\d) \}", write),
                         [("1", "0"), ("2", "1"), ("3", "2")])
        self.assertLess(write.index("set_variable = { name = ch_leader_seat_count value = 0 }"),
                        write.index("ch_leaders_display_seat"))

    def test_written_after_the_census_and_monthly_for_players(self):
        census = _block(self.effects, "ch_yearly_global_update")
        sweep = census.index("ch_leaders_display_write = yes")
        self.assertGreater(sweep, census.index("set_global_variable = { name = ch_ranked_total"))
        self.assertIn("is_player = yes", census[census.rindex("every_country", 0, sweep):sweep])
        monthly = _block(self.effects, "ch_monthly_country_update")
        m = re.search(r"limit = \{ is_player = yes \}\s*ch_leaders_display_write = yes", monthly)
        self.assertTrue(m)

    def test_nothing_but_the_display_reads_the_seats(self):
        readers = []
        for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True) + \
                glob.glob(os.path.join(REPO, "events", "**", "*.txt"), recursive=True):
            if "ch_leader_seat" in _read(path):
                readers.append(os.path.relpath(path, REPO))
        self.assertEqual(sorted(readers), sorted([os.path.relpath(EFFECTS, REPO), os.path.relpath(VALUES, REPO)]))


class StatusTextTest(unittest.TestCase):
    """Status text that repeats the overview goes (owner, 2026-09-29); the
    inactive entry, whose panels are hidden, keeps one line."""

    def test_only_the_inactive_entry_has_status_text(self):
        body = _braced(_read(JE), _read(JE).index("status_desc = {") + len("status_desc = "))
        self.assertNotRegex(body, r"^\t\tdesc = ", "an unconditional status line")
        m = re.search(r"triggered_desc = \{\s*desc = (\w+)\s*trigger = \{ NOT = \{ has_journal_entry = je_cultural_hegemony \} \}", body)
        self.assertTrue(m)
        self.assertEqual(len(re.findall(r"(?<!\w)desc = ", body)), 1)
        val = _loc()[m.group(1)]
        self.assertNotIn("\\n", val)


class ValueColourTest(unittest.TestCase):
    """Good numbers green, penalties red (style rule 5; owner, 2026-09-29)."""

    def test_breakdown_values(self):
        loc = _loc()
        for part in ("art", "prestige", "tech", "monuments", "megaprojects", "modifiers"):
            with self.subTest(part=part):
                self.assertTrue(loc[f"je_ch_widget_bd_{part}_value"].startswith("#G "))
        # The Pull Multiplier is signed and sign-coloured, as the art
        # multiplier beside it is (CH-3): "+25%", green.
        self.assertIn("|+=0]%", loc["je_ch_widget_bd_mult_value"])
        # Standard of living can be either sign (a country below the world average loses pull), so its value
        # carries the signed, sign-coloured format rather than a fixed green.
        self.assertIn("|+=1]", loc["je_ch_widget_bd_sol_value"])
        self.assertNotIn("#G", loc["je_ch_widget_bd_sol_value"])
        for part in ("infamy", "instability"):
            with self.subTest(part=part):
                self.assertTrue(loc[f"je_ch_widget_bd_{part}_value"].startswith("#R "))


COMPONENT_BARS = {   # breakdown row -> (right-half fraction, left-half fraction) script values
    "art": ("ch_disp_bar_art_pos", None),
    "prestige": ("ch_disp_bar_prestige_pos", None),
    "sol": ("ch_disp_bar_sol_pos", "ch_disp_bar_sol_neg"),
    "tech": ("ch_disp_bar_tech_pos", None),
    "monuments": ("ch_disp_bar_monuments_pos", None),
    "megaprojects": ("ch_disp_bar_megaprojects_pos", None),
    "modifiers": ("ch_disp_bar_modifiers_pos", None),
    "infamy": (None, "ch_disp_bar_infamy_neg"),
    "instability": (None, "ch_disp_bar_instability_neg"),
}


class PullBarTest(unittest.TestCase):
    """The breakdown as UN pillar rows (owner, 2026-09-30): a bar per component,
    zero at the centre line, the ranges in script values."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(WIDGET)
        cls.sec = _type_body(cls.gui, "te_ch_sec_breakdown")
        cls.values = _read(VALUES)

    def _row(self, part):
        m = re.search(rf'ch_bar_row = \{{\s*tooltip = "je_ch_widget_bd_{part}_tt"', self.sec)
        self.assertTrue(m, part)
        return _braced(self.sec, self.sec.index("{", m.start()))

    def test_each_component_has_its_bar_and_tooltip(self):
        for part, (pos, neg) in COMPONENT_BARS.items():
            with self.subTest(part=part):
                row = self._row(part)
                self.assertIn("ch_pull_bar = {", row)
                for block, value in (("pos_value", pos), ("neg_value", neg)):
                    if value:
                        self.assertIn(f"ScriptValue('{value}')", row)
                    else:
                        self.assertNotIn(f'blockoverride "{block}"', row)
                self.assertIn(f"je_ch_widget_bd_{part}_tt", _loc())

    def test_totals_have_no_bar(self):
        for part in ("raw", "mult"):
            with self.subTest(part=part):
                self.assertNotIn("ch_pull_bar", self._row(part))

    def test_the_fractions_are_clamped_and_scaled_by_named_ranges(self):
        for part, (pos, neg) in COMPONENT_BARS.items():
            for value, side, lo, hi in ((pos, "max", "0", "1"), (neg, "min", "-1", "0")):
                if not value:
                    continue
                with self.subTest(value=value):
                    body = _block(self.values, value)
                    self.assertIn(f"divide = ch_bar_{part}_{side}", body)
                    self.assertIn(f"min = {lo}", body)
                    self.assertIn(f"max = {hi}", body)
                    self.assertRegex(self.values, rf"(?m)^ch_bar_{part}_{side} = \{{")

    def test_the_owners_ranges(self):
        """Art and Prestige 0-100, SoL -5 to 20 (its own clamp), Instability -30 (turmoil
        -10 plus civil war -20); Infamy -10, the owner's "about -100" read as infamy points."""
        for name, body in (("ch_bar_art_max", "value = 100"), ("ch_bar_prestige_max", "value = 100"),
                           ("ch_bar_sol_min", "value = cultural_pull_sol_min"),
                           ("ch_bar_sol_max", "value = cultural_pull_sol_max"),
                           ("ch_bar_instability_min", "value = cultural_pull_turmoil_factor"),
                           ("ch_bar_infamy_min", "multiply = cultural_pull_infamy_factor")):
            with self.subTest(range=name):
                self.assertIn(body, _block(self.values, name))

    def test_the_bar_draws_red_left_and_green_right(self):
        bar = _type_body(self.gui, "ch_pull_bar")
        neg = bar[bar.index('block "neg_value"') - 600:bar.index('block "neg_value"')]
        self.assertIn('noprogresstexture = "gfx/interface/backgrounds/white.dds"', neg)   # the reverse hack
        self.assertIn("min = -1", neg)
        self.assertIn("color = { 0.78 0.31 0.28 1.0 }", neg)
        pos = bar[bar.index('block "pos_value"') - 600:bar.index('block "pos_value"')]
        self.assertIn('progresstexture = "gfx/interface/backgrounds/white.dds"', pos)
        self.assertIn("color = { 0.36 0.68 0.40 1.0 }", pos)
        self.assertNotRegex(self.sec, r"\bmin = |\bmax = ", "a range in the .gui")


class ArtMultiplierTest(unittest.TestCase):
    """The art multiplier on its own line, under a name that says what it boosts."""

    def test_its_line_follows_the_art_row(self):
        sec = _type_body(_read(WIDGET), "te_ch_sec_breakdown")
        m = re.search(r"ch_bar_subrow = \{\s*tooltip = \"je_ch_widget_bd_art_mult_tt\"\s*blockoverride \"row_visible\" \{\s*visible = \"\[(.*?)\]\"", sec, re.S)
        self.assertTrue(m)
        self.assertIn("NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('ch_art_mult_pct_display'), '(CFixedPoint)0' )", m.group(1))
        self.assertLess(sec.index("je_ch_widget_bd_art_dr_tt"), m.start())
        self.assertLess(m.start(), sec.index("je_ch_widget_bd_prestige_tt"))

    def test_the_modifier_is_named_for_what_it_boosts(self):
        loc = _loc()
        self.assertEqual(loc["country_cultural_hegemony_art_mult"], "Cultural Pull from Art")
        self.assertEqual(loc["je_ch_widget_bd_art_mult_label"], "$country_cultural_hegemony_art_mult$")


# ---- Rule 1 (round 3): nothing a player reads ends in "..." ----------------------
# Units per character, from the owner's screenshots (round3_rules.md and the
# style guide): the serif face about 10 at 20, so 0.5 a point (8.5 at the 17
# row size); the overview's tooltip face 8.6 at 16. Plus 10% margin. The
# panel's sizes are its ch_fontsize_* templates (CH-15), read from the file,
# so a change of type re-budgets every cell. "large" is vanilla's: the section
# headers' and the action buttons' own fonts, which are not the panel's.
_SIZES = {m.group(1): int(m.group(2)) for m in re.finditer(
    r"template ch_fontsize_(\w+) \{\s*fontsize = (\d+)", _read(WIDGET))}
UNITS = {"row": 10.0 / 20 * _SIZES["row"], "heading": 10.0 / 20 * _SIZES["heading"],
         "overview": 8.6 / 16 * _SIZES["overview"], "large": 10.0}
MARGIN = 1.1
MODEL_KEYS = ["communist", "anarchist", "fascist", "corporatist", "socialist", "royalist_absolutist",
              "royalist_constitutional", "religious", "reactionary", "military_junta", "liberal", "other",
              "technocratic", "republican", "developmentalist_junta"]
# (key, cell width, font, worst-case data values in order)
STATIC_LABELS = (
    [(f"je_ch_widget_bd_{p}_label", 176, "row", ()) for p in
     ("art", "prestige", "sol", "tech", "monuments", "megaprojects", "modifiers", "infamy", "instability", "raw", "mult")]
    + [("je_ch_widget_bd_art_mult_label", 332, "row", ())]
    + [(f"je_ch_widget_prog_{p}", 250, "row", ()) for p in ("outreach", "institutes", "media", "protectionism")]
    + [("je_ch_widget_funding_label", 250, "row", ()),
       ("ch_policy_status_active", 80, "row", ()), ("ch_policy_status_idle", 80, "row", ())]
    + [(f"ch_policy_{p}_{s}", 112, "large", ()) for p in ("outreach", "institutes", "media", "protectionism") for s in ("on", "off")]
    + [(f"je_ch_ov_tier_{n}", 106, "overview", ()) for n in range(6)]
    + [("je_ch_ov_rank_label", 106, "overview", ()), ("je_ch_ov_benchmark_label", 106, "overview", ()),
       ("je_ch_ov_leaders_label", 222, "overview", ())]
    + [(k, 440, "large", ()) for k in ("je_ch_widget_programmes_header", "je_ch_widget_breakdown_header",
                                        "je_ch_widget_board_header", "je_ch_widget_models_header",
                                        "je_ch_widget_history_header", "je_ch_how_header")]
    # The board's head (CH-2), in its columns.
    + [("je_ch_board_head_rank", 26, "row", ()), ("je_ch_board_head_country", 208, "row", ()),
       ("je_ch_board_head_share", 60, "row", ()), ("je_ch_board_head_change", 66, "row", ()),
       ("je_ch_board_head_model", 50, "row", ())]
    # The programs cell (CH-9): Banking's cell, its lines in a 154 column at 16.
    + [("je_ch_ov_prog_label", 154, "overview", ()), ("je_ch_ov_prog_no_ministry", 154, "overview", ())]
)
# Dynamic text, at its longest: the political models' short names (the longest are
# "Constitutional", "Military Junta" and "Technocratic"; the full names, up to
# "Liberal / Progressive Democratic", are on hover), and numbers at their widest.
DYNAMIC_LABELS = (
    [(f"je_ch_ov_model_{m}", 134, "overview", ()) for m in MODEL_KEYS]       # the overview's model cell
    + [(f"je_ch_ov_model_{m}", 216, "row", ()) for m in MODEL_KEYS]          # the models legend
    + [(f"je_ch_ov_model_{m}", 200, "row", ()) for m in MODEL_KEYS]          # the history legend (CH-12)
    + [("je_ch_ov_rank_value", 106, "heading", ("999", "999")),
       ("je_ch_ov_share_label", 156, "overview", ("100.0",)),               # 180 cell less the 20 px arrow and 4 spacing
       ("je_ch_widget_funding_value", 80, "row", ("10", "10")),
       ("je_ch_widget_board_us", 474, "row", ("999", "999")),
       ("je_ch_widget_bd_art_value", 60, "row", ("150.0",)),
       ("je_ch_widget_bd_prestige_value", 60, "row", ("100.0",)),
       ("je_ch_widget_bd_sol_value", 60, "row", ("-5.0",)),
       ("je_ch_widget_bd_tech_value", 60, "row", ("40.0",)),
       ("je_ch_widget_bd_monuments_value", 60, "row", ("150",)),
       ("je_ch_widget_bd_megaprojects_value", 60, "row", ("21",)),
       ("je_ch_widget_bd_modifiers_value", 60, "row", ("30.0",)),
       ("je_ch_widget_bd_infamy_value", 60, "row", ("-20.0",)),
       ("je_ch_widget_bd_instability_value", 60, "row", ("-30.0",)),
       ("je_ch_widget_bd_raw_value", 60, "row", ("9999.9",)),
       ("je_ch_widget_bd_mult_value", 60, "row", ("+999",)),
       ("je_ch_widget_bd_art_mult_value", 60, "row", ("+100",)),
       # The board's rows: rank, share, and the change beside its 16 px arrow.
       ("ch_board_row_rank", 26, "row", ("10",)), ("ch_board_row_share", 60, "row", ("100.0",)),
       ("ch_board_row_change", 48, "row", ("+12.3",)),
       # The programs cell's word and funding line.
       ("je_ch_ov_prog_running", 154, "overview", ("4",)), ("je_ch_ov_prog_funding", 154, "overview", ("10", "10"))]
    + [(f"je_ch_widget_models_share_{m}", 60, "row", ("100.0",)) for m in MODEL_KEYS]
)


def _visible(loc, key, data=(), depth=0):
    """The text a key shows: splices and concept names resolved, data replaced by
    the worst case, formatting codes stripped."""
    val = loc[key]
    val = re.sub(r"\$([\w.]+)\$", lambda m: _visible(loc, m.group(1), (), depth + 1), val)
    val = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", r"\1", val)
    val = re.sub(r"\[(concept_\w+)\]", lambda m: _visible(loc, m.group(1), (), depth + 1), val)
    it = iter(data)
    val = re.sub(r"\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]", lambda m: next(it, "0"), val)
    val = val.replace("#!", "")
    val = re.sub(r"#[A-Za-z]+ ", "", val)
    return val


class LabelBudgetTest(unittest.TestCase):
    def test_every_label_fits_its_cell(self):
        loc = _loc()
        for key, width, font, data in STATIC_LABELS + DYNAMIC_LABELS:
            text = _visible(loc, key, data)
            with self.subTest(key=key, text=text):
                self.assertLessEqual(len(text) * UNITS[font] * MARGIN, width)

    def test_the_cells_are_the_widths_the_budget_assumes(self):
        gui = _read(WIDGET)
        for type_name, sizes in (("ch_bar_row", ["176 22", "164 22", "60 22"]),
                                 ("ch_bar_subrow", ["348 20", "60 20"]),
                                 ("ch_programme_row", ["250 26", "80 26"]),
                                 ("ch_model_legend_row", ["216 20", "60 20"]),
                                 ("ch_board_row", ["14 24", "26 24", "28 24", "60 24", "66 24", "50 24"]),
                                 ("te_ch_ov_icon_label", ["108 58"]),
                                 ("te_ch_ov_pie", ["180 108"])):
            body = _type_body(gui, type_name)
            for size in sizes:
                with self.subTest(type=type_name, size=size):
                    self.assertIn(f"size = {{ {size} }}", body)
        self.assertIn("minimumsize = { 208 -1 }", _type_body(gui, "ch_board_row"))
        self.assertEqual(_read(WIDGET).count("size = { 136 58 }"), 15)   # the model cells

    def test_the_overviews_first_row_fits_its_column(self):
        # tier, rank and benchmark at 108, the model cell at 136, 4 between: 472 of 474.
        ov = _type_body(_read(WIDGET), "te_ch_overview_panel")
        row = ov[ov.index("### Row 1:"):ov.index("### The influence tier")]
        self.assertIn("spacing = 4", row)
        self.assertLessEqual(108 * 3 + 136 + 3 * 4, 474)


class TypeSizeTest(unittest.TestCase):
    """CH-15: the 17 / 20 / 16 ladder through the panel's own templates (the
    owner lifted the panel's grandfathering for this rework, 2026-10-27)."""

    def test_the_templates_and_their_sizes(self):
        self.assertEqual(_SIZES, {"row": 17, "heading": 20, "overview": 16})
        gui = _read(WIDGET)
        self.assertRegex(gui, r"template ch_fontsize_overview \{\s*fontsize = 16\s*using = tooltip_font")
        self.assertNotRegex(gui, r"using = fontsize_(small|medium|large|xl)\b")

    def test_the_overview_reads_the_overview_size(self):
        gui = _read(WIDGET)
        for type_name in ("te_ch_ov_icon_label", "te_ch_ov_pie"):
            with self.subTest(type=type_name):
                self.assertIn("using = ch_fontsize_overview", _type_body(gui, type_name))
        self.assertIn("using = ch_fontsize_heading", _type_body(gui, "ch_subheader"))
        for type_name in ("ch_note", "ch_bar_row", "ch_programme_row", "ch_board_row", "ch_model_legend_row"):
            with self.subTest(type=type_name):
                self.assertIn("using = ch_fontsize_row", _type_body(gui, type_name))


class BoardTest(unittest.TestCase):
    """CH-2: the Top Cultural Powers board as a one-line table, a datamodel over
    the board store's rows (the political-model history's shape)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(WIDGET)
        cls.sec = _type_body(cls.gui, "te_ch_sec_board")
        cls.row = _type_body(cls.gui, "ch_board_row")
        cls.head = _type_body(cls.gui, "ch_board_head")
        cls.effects = _read(EFFECTS)
        cls.loc = _loc()

    def test_rows_come_from_the_store_once_it_has_some(self):
        self.assertIn("datamodel = \"[GetGlobalVariable('ch_board_store').GetList('ch_board')]\"", self.sec)
        item = self.sec[self.sec.index("item = {"):]
        self.assertIn("ch_board_row = {", item)
        self.assertIn('datacontext = "[Scope.GetScriptContainer]"', item)
        table = self.sec[self.sec.rindex("flowcontainer = {", 0, self.sec.index("ch_board_head = {}")):]
        self.assertIn("ScriptValue('ch_board_has_rows'), '(CFixedPoint)1'", table[:300])
        self.assertIn("ScriptValue('ch_board_has_rows'), '(CFixedPoint)0'", self.sec[:self.sec.index("ch_board_head = {}")])
        self.assertLess(self.sec.index("ch_board_head = {}"), self.sec.index("datamodel ="))
        # No row is an ExecuteTooltip string any more, and the old handlers went.
        self.assertNotIn("ExecuteTooltip", self.sec + self.row)
        sguis = _read(SGUIS)
        for gone in ("ch_board_row_sgui", "ch_board_detail_sgui", "ch_board_is_us_sgui"):
            self.assertNotRegex(sguis, rf"(?m)^{gone} = ")
            self.assertNotIn(f"GetScriptedGui('{gone}')", self.gui)

    def test_the_head_and_the_rows_share_their_columns(self):
        widths = lambda body: [int(w) for w in re.findall(r"size = \{ (\d+) 24 \}", body)]
        head = [w for w in widths(self.head)]
        head_cells = re.findall(r'blockoverride "cell_size" \{\s*size = \{ (\d+) 24 \}', self.head)
        self.assertEqual(head_cells, ["26", "208", "66", "50"])
        # the row: marker, rank, flag (and its gated inner widget), share, change, model
        self.assertEqual(widths(self.row), [14, 26, 28, 28, 60, 66, 50])
        self.assertIn(14, head)
        self.assertIn(28, head)

    def test_the_flag_and_name_read_the_stored_capital(self):
        flag = self.row[self.row.index("tiny_flag = {") - 200:self.row.index("tiny_flag = {") + 200]
        self.assertIn("visible = \"[ScriptContainer.HasVariable('ch_board_capital')]\"", flag)
        self.assertIn("datacontext = \"[ScriptContainer.MakeScope.Var('ch_board_capital').GetState.GetCountry]\"", flag)
        self.assertIn("ScriptContainer.HasVariable('ch_board_capital')", self.loc["ch_board_row_name"])
        self.assertIn("Var('ch_board_capital').GetState.GetCountry.GetName", self.loc["ch_board_row_name_known"])

    def test_the_us_marker_compares_ranks_without_a_saved_scope(self):
        self.assertIn("EqualTo_CFixedPoint( ScriptContainer.GetVariableValue('ch_board_rank'), "
                      "JournalEntry.GetCountry.MakeScope.ScriptValue('ch_rank_self_display') )", self.row)

    def test_every_model_has_its_swatch_and_hover(self):
        for code, model in enumerate(MODEL_KEYS, 1):
            with self.subTest(model=model):
                self.assertRegex(self.row, rf"GetVariableValue\('ch_board_model'\), '\(CFixedPoint\){code}' \)\]\"\s*"
                                           rf"texture = \"gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_{model}\.dds\"")
                self.assertIn(f'tooltip = "ch_model_{model}_tt"', self.row)

    def test_the_row_hover_reads_only_its_container(self):
        # A datamodel item's tooltip has no JournalEntry (gotcha #24); follow
        # splices and SelectLocalization keys.
        seen, todo = set(), ["ch_board_row_tt"]
        while todo:
            key = todo.pop()
            if key in seen:
                continue
            seen.add(key)
            val = self.loc[key]
            self.assertNotIn("JournalEntry", val, key)
            todo += [k for k in re.findall(r"\$(\w+)\$", val) + re.findall(r"'(\w+)'", val) if k in self.loc]
        self.assertIn("ch_board_tt_bonus", seen)

    def test_the_rows_hold_every_component_the_hover_prints(self):
        write = _block(self.effects, "ch_board_row_write")
        read = set(re.findall(r"GetVariableValue\('(ch_board_\w+)'\)", "".join(
            v for k, v in self.loc.items() if k.startswith(("ch_board_", "je_ch_board_"))) + self.row))
        for var in read:
            with self.subTest(var=var):
                self.assertIn(f"name = {var} ", write)
        for comp in ("art", "prs", "sol", "tech", "mon", "mega", "mods", "infamy", "instab", "bonus", "raw"):
            self.assertIn(f"ch_board_{comp}", read)

    def test_built_after_the_census_and_refreshed_for_players(self):
        census = _block(self.effects, "ch_yearly_global_update")
        self.assertLess(census.index("ch_finish_all_model_buckets = yes"), census.index("ch_board_rebuild = yes"))
        self.assertLess(census.index("set_global_variable = { name = ch_ranked_total"), census.index("ch_board_rebuild = yes"))
        monthly = _block(self.effects, "ch_monthly_country_update")
        self.assertRegex(monthly, r"limit = \{ is_player = yes \}\s*ch_leaders_display_write = yes\s*ch_board_refresh_capitals = yes")
        rebuild = _block(self.effects, "ch_board_rebuild")
        self.assertEqual(re.findall(r"ch_board_row_write = \{ N = (\d+) \}", rebuild), [str(n) for n in range(1, 11)])
        self.assertLess(rebuild.index("clear_variable_list = ch_board"), rebuild.index("ch_board_row_write"))

    def test_the_change_is_the_countrys_own(self):
        # The board printed a slot's change, so a new occupant was measured
        # against whoever held the rank before.
        census = _block(self.effects, "ch_yearly_global_update")
        self.assertIn("set_variable = { name = ch_board_share_prev value = cultural_pull_display }", census)
        self.assertLess(census.index("subtract = var:ch_board_share_prev"),
                        census.index("set_variable = { name = ch_board_share_prev value = cultural_pull_display }"))
        self.assertNotIn("_delta", re.sub(r"ch_board_delta\w*", "", census))

    def test_how_describes_the_table(self):
        how = self.loc["je_ch_how_board"]
        self.assertNotIn("bracketed", how)
        self.assertIn("swatch", how)


class BreakdownOrderTest(unittest.TestCase):
    """CH-3: the parts of a total, then the total. The Pull Multiplier scales the
    components' sum, so it closes them, and the Raw Score stands under the rule."""

    def test_the_multiplier_closes_the_components(self):
        sec = _type_body(_read(WIDGET), "te_ch_sec_breakdown")
        self.assertLess(sec.index("je_ch_widget_bd_instability_tt"), sec.index("je_ch_widget_bd_mult_tt"))
        self.assertLess(sec.index("je_ch_widget_bd_mult_tt"), sec.index("divider_clean"))
        self.assertLess(sec.index("divider_clean"), sec.index("je_ch_widget_bd_raw_tt"))
        self.assertIn("components above", _loc()["je_ch_widget_bd_mult_tt"])


class FundingCapTest(unittest.TestCase):
    """CH-4: where the funding cap comes from, on the level's hover and in How."""

    def test_the_level_says_where_its_cap_comes_from(self):
        progs = _type_body(_read(WIDGET), "te_ch_sec_programmes")
        cell = progs[progs.index('text = "je_ch_widget_funding_value"') - 300:progs.index('text = "je_ch_widget_funding_value"') + 120]
        self.assertIn('tooltip = "je_ch_widget_funding_value_tt"', cell)
        self.assertIn('default_format = "#tooltippable"', cell)
        loc = _loc()
        tip = loc["je_ch_widget_funding_value_tt"]
        for part in ("institution_ministry_of_culture", "mass_media", "television",
                     "GetValueWithBreakdownFor('country_cultural_program_max_funding_add')"):
            self.assertIn(part, tip)
        self.assertIn("institution_ministry_of_culture", loc["je_ch_how_programmes"])


class TierFloorTest(unittest.TestCase):
    """CH-5: the tier thresholds have one copy, which the tooltip and the
    concept print; the tooltip names the next tier."""

    def test_one_copy_of_the_floors(self):
        values = _read(VALUES)
        floors = {int(n): int(v) for n, v in re.findall(r"(?m)^ch_tier_(\d)_floor = (\d+)$", values)}
        self.assertEqual(floors, {1: 2, 2: 5, 3: 10, 4: 15, 5: 25})
        state = _block(_read(EFFECTS), "ch_set_display_state")
        for n in range(1, 6):
            self.assertIn(f"var:ch_total >= ch_tier_{n}_floor", state)
        self.assertNotRegex(state, r"var:ch_total >= \d")

    def test_the_tooltip_names_the_next_tier_and_the_concept_prints_the_ladder(self):
        loc = _loc()
        self.assertIn("je_ch_ov_tier_next", loc["je_ch_ov_tier_tt"])
        self.assertIn("ch_disp_next_tier_floor", loc["je_ch_ov_tier_next"])
        self.assertIn("GetCustom('ch_next_tier_name')", loc["je_ch_ov_tier_next"])
        concept = loc["concept_ch_influence_tier_desc"]
        for n in range(1, 6):
            self.assertIn(f"ch_tier_{n}_floor", concept)
        self.assertNotRegex(re.sub(r"\[[^\]]*\]", "", concept), r"\d")


class SolRankFactorTest(unittest.TestCase):
    """CH-1: the rank factor on the standard-of-living component is said."""

    def test_the_factor_is_one_value_the_hover_prints(self):
        values = _read(VALUES)
        self.assertIn("multiply = ch_sol_rank_factor", _block(values, "cultural_pull_from_sol"))
        factor = _block(values, "ch_sol_rank_factor")
        for rank, value in (("great_power", "1"), ("major_power", "0.5"), ("minor_power", "0.25")):
            self.assertIn(f"rank_value:{rank}", factor)
            self.assertIn(f"value = {value}", factor)
        self.assertIn("ScriptValue('ch_sol_rank_factor')", _loc()["je_ch_widget_bd_sol_tt"])


class ProgramsCellTest(unittest.TestCase):
    """CH-9: the overview's programs cell, Banking's te_banking_ov_cell."""

    def test_the_cell(self):
        ov = _type_body(_read(WIDGET), "te_ch_overview_panel")
        cell = ov[ov.index("te_banking_ov_cell = {"):]
        self.assertIn('tooltip = "je_ch_ov_prog_tt"', cell[:200])
        for key in ("je_ch_ov_prog_label", "je_ch_ov_prog_running", "je_ch_ov_prog_no_ministry", "je_ch_ov_prog_funding"):
            self.assertIn(f'text = "{key}"', cell)
        self.assertEqual(cell.count("GetScriptedGui('ch_ministry_missing_sgui').IsShown"), 4)
        self.assertIn("alpha = 0.4", cell)
        loc = _loc()
        self.assertIn("ScriptValue('ch_prog_count_display')", loc["je_ch_ov_prog_running"])
        self.assertTrue(loc["je_ch_ov_prog_no_ministry"].startswith("#R "))
        listing = loc["je_ch_ov_prog_tt_list"]
        for p in ("outreach", "institutes", "media", "protectionism"):
            self.assertIn(f"$je_ch_widget_prog_{p}_status$", listing)
        # Below the leaders: the owner's board-first order and leader flags stand.
        self.assertLess(ov.index("ch_leader_seat_3"), ov.index("te_banking_ov_cell = {"))

if __name__ == "__main__":
    unittest.main()
