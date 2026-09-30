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
# Textures the overview keeps from vanilla on purpose.
VANILLA_KEPT = {"gfx/interface/backgrounds/round_frame_dec.dds", "gfx/interface/icons/generic_icons/trend_up.dds",
                "gfx/interface/icons/generic_icons/trend_down.dds", "gfx/interface/icons/generic_icons/trend_nochange.dds"}


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
        for part in ("art", "prestige", "sol", "tech", "monuments", "megaprojects", "modifiers", "mult"):
            with self.subTest(part=part):
                self.assertTrue(loc[f"je_ch_widget_bd_{part}_value"].startswith("#G "))
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
# Units per character, from the owner's screenshots (round3_rules.md): the large
# row-name font about 10, the medium table font about 8.6. The small font is not
# measured; 7.4 scales medium by the large/medium ratio. Plus 10% margin.
UNITS = {"large": 10.0, "medium": 8.6, "small": 7.4}
MARGIN = 1.1
MODEL_KEYS = ["communist", "anarchist", "fascist", "corporatist", "socialist", "royalist_absolutist",
              "royalist_constitutional", "religious", "reactionary", "military_junta", "liberal", "other",
              "technocratic", "republican", "developmentalist_junta"]
# (key, cell width, font, worst-case data values in order)
STATIC_LABELS = (
    [(f"je_ch_widget_bd_{p}_label", 176, "medium", ()) for p in
     ("art", "prestige", "sol", "tech", "monuments", "megaprojects", "modifiers", "infamy", "instability", "raw", "mult")]
    + [("je_ch_widget_bd_art_mult_label", 332, "medium", ())]
    + [(f"je_ch_widget_prog_{p}", 250, "large", ()) for p in ("outreach", "institutes", "media", "protectionism")]
    + [("je_ch_widget_funding_label", 250, "large", ()),
       ("ch_policy_status_active", 80, "medium", ()), ("ch_policy_status_idle", 80, "medium", ())]
    + [(f"ch_policy_{p}_{s}", 112, "large", ()) for p in ("outreach", "institutes", "media", "protectionism") for s in ("on", "off")]
    + [(f"je_ch_ov_tier_{n}", 108, "small", ()) for n in range(6)]
    + [("je_ch_ov_rank_label", 108, "small", ()), ("je_ch_ov_benchmark_label", 108, "small", ()),
       ("je_ch_ov_leaders_label", 222, "medium", ())]
    + [(k, 440, "large", ()) for k in ("je_ch_widget_programmes_header", "je_ch_widget_breakdown_header",
                                        "je_ch_widget_board_header", "je_ch_widget_models_header",
                                        "je_ch_widget_history_header", "je_ch_how_header")]
)
# Dynamic text, at its longest: the political models' short names (the longest are
# "Constitutional", "Military Junta" and "Technocratic"; the full names, up to
# "Liberal / Progressive Democratic", are on hover), and numbers at their widest.
DYNAMIC_LABELS = (
    [(f"je_ch_ov_model_{m}", 116, "small", ()) for m in MODEL_KEYS]          # the overview's model cell
    + [(f"je_ch_ov_model_{m}", 216, "medium", ()) for m in MODEL_KEYS]       # the models legend
    + [("je_ch_ov_rank_value", 108, "large", ("999", "999")),
       ("je_ch_ov_share_label", 156, "medium", ("100.0",)),                 # 180 cell less the 20 px arrow and 4 spacing
       ("je_ch_widget_funding_value", 80, "medium", ("10", "10")),
       ("je_ch_widget_board_us", 474, "medium", ("999", "999")),
       ("je_ch_widget_bd_art_value", 60, "medium", ("150.0",)),
       ("je_ch_widget_bd_prestige_value", 60, "medium", ("100.0",)),
       ("je_ch_widget_bd_sol_value", 60, "medium", ("-5.0",)),
       ("je_ch_widget_bd_tech_value", 60, "medium", ("40.0",)),
       ("je_ch_widget_bd_monuments_value", 60, "medium", ("150",)),
       ("je_ch_widget_bd_megaprojects_value", 60, "medium", ("21",)),
       ("je_ch_widget_bd_modifiers_value", 60, "medium", ("30.0",)),
       ("je_ch_widget_bd_infamy_value", 60, "medium", ("-20.0",)),
       ("je_ch_widget_bd_instability_value", 60, "medium", ("-30.0",)),
       ("je_ch_widget_bd_raw_value", 60, "medium", ("9999.9",)),
       ("je_ch_widget_bd_mult_value", 60, "medium", ("999",)),
       ("je_ch_widget_bd_art_mult_value", 60, "medium", ("+100",))]
    + [(f"je_ch_widget_models_share_{m}", 60, "medium", ("100.0",)) for m in MODEL_KEYS]
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
                                 ("te_ch_ov_pie", ["180 108"])):
            body = _type_body(gui, type_name)
            for size in sizes:
                with self.subTest(type=type_name, size=size):
                    self.assertIn(f"size = {{ {size} }}", body)
        self.assertEqual(_read(WIDGET).count("size = { 118 58 }"), 15)   # the model cells


if __name__ == "__main__":
    unittest.main()
