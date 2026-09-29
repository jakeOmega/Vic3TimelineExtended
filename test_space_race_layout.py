"""The Space Race panels' layout (gui_style_guide.md; the UN's test_un_layout.py).

The nine milestone entries each attach an overview, their live sections and one
shared reference from gui/journal_entry_widgets/space_race_widget.gui. These
tests hold the section order, that collapse flags say their default, that the
parts which only matter while a programme runs are gated on it, that the
explanations live in How the Space Race Works, that each milestone's root reads
only its own milestone's data, and that the overview's display values are
guarded and follow the single derivation sites they mirror.
"""
import glob
import os
import re
import subprocess
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_space_race.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "space_race_sguis.txt")
DISPLAY = os.path.join(REPO, "common", "script_values", "space_race_display_values.txt")
CUSTOM_LOC = os.path.join(REPO, "common", "customizable_localization", "space_race_custom_loc.txt")
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

RACING = ["suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
          "interstellar_probe"]
CONTROLLED = RACING + ["solar_colonization"]  # the eight with controls, in sr_rivals_sgui op order
ALL = ["suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
       "interstellar_probe", "interstellar_results", "solar_colonization"]  # programme row order

STATUS = ["te_sr_sec_control", "te_sr_sec_rivals"]
REFERENCE = ["te_sr_sec_how"]
OLD_FLAGS = [f"sr_panel_rivals_{m}" for m in CONTROLLED] + \
            [f"sr_panel_programme_{m}" for m in ALL]
HOW_KEYS = ["je_space_race_widget_how_approach", "je_space_race_widget_how_funding",
            "je_space_race_widget_how_setbacks", "je_space_race_widget_how_first",
            "je_space_race_widget_how_rivals", "je_space_race_widget_how_programme"]
IS_SHOWN_OP0 = ("ScriptedGui.IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope )"
                ".AddScope( 'op', MakeScopeValue( '(CFixedPoint)0' ) ).End )")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    """Drop each line's comment: from the first # outside a quoted string."""
    out = []
    for line in text.split("\n"):
        quoted = False
        for i, ch in enumerate(line):
            if ch == '"':
                quoted = not quoted
            elif ch == "#" and not quoted:
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return text[m.end():_close(text, m.end() - 1)]


def _root(text, name):
    m = re.search(rf'name = "{name}"', text)
    assert m, f"no root {name}"
    start = text.rfind("flowcontainer = {", 0, m.start())
    brace = text.index("{", start)
    return text[start:_close(text, brace) + 1]


def _block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, f"{name} not found"
    return text[m.end():_close(text, m.end() - 1)]


def _loc(key):
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        m = re.search(rf'^ {re.escape(key)}:\d* "(.*)"\s*$', _read(path), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


def _milestones_named(text):
    """The milestone tokens a stretch of text mentions, longest names first so
    'interstellar_probe' is not also read as 'probe'."""
    found = set()
    for m in sorted(ALL, key=len, reverse=True):
        pat = rf"(?<=[_'/]){m}(?![a-z])"
        if re.search(pat, text):
            found.add(m)
            text = re.sub(pat, "", text)
    return found


class OrderTest(unittest.TestCase):
    def test_status_and_reference_order(self):
        gui = _read(GUI)
        for composer, expected in (("te_sr_status_sections", STATUS),
                                   ("te_sr_reference_sections", REFERENCE)):
            found = re.findall(r"^\t\t(te_sr_sec_\w+) = \{", _type_body(gui, composer), re.M)
            self.assertEqual(found, expected, composer)

    def test_overview_rows_in_order(self):
        body = _type_body(_read(GUI), "te_sr_overview_milestone")
        marks = ['block "sr_status_drifting"', 'block "sr_risk_lit"', 'block "sr_third_cells"',
                 "te_sr_ov_bar_row = {", 'block "sr_extra_rows"', "te_sr_ov_programme = {}"]
        positions = [body.find(m) for m in marks]
        self.assertNotIn(-1, positions, dict(zip(marks, positions)))
        self.assertEqual(positions, sorted(positions))

    def test_the_overview_is_the_top_container(self):
        """Overview in container 1 (above the status line), live sections in 2,
        the reference in 3, as the UN entry attaches them."""
        je = _read(JE)
        for m in ALL:
            with self.subTest(milestone=m):
                entry = _block(je, f"je_space_race_{m}")
                widgets = re.findall(r'name = "(\w+)"\s*container = "(\w+)"', entry)
                expected = [(f"widget_je_space_race_{m}_overview", "custom_widget_container_1")]
                if m in CONTROLLED:
                    expected.append((f"widget_je_space_race_{m}", "custom_widget_container_2"))
                expected.append(("widget_je_space_race_reference", "custom_widget_container_3"))
                # the bars-on-top marker: the overview draws the progress, so the
                # entry's own goal bar at the foot is hidden (gui/journal_entry.gui)
                expected.append(("widget_te_je_bars_on_top_marker", "custom_widget_container_7"))
                self.assertEqual(widgets, expected)
                self.assertIn("progressbar = yes", entry)  # the journal list still uses it

    def test_the_status_line_shows_only_while_inactive(self):
        """Round 2 (owner): an active entry's overview shows its state, and the
        reason text repeats the rest, so the status line is for inactive entries."""
        je = _read(JE)
        for m in ALL:
            with self.subTest(milestone=m):
                status = _block(_block(je, f"je_space_race_{m}").replace("\n\t", "\n"), "status_desc")
                self.assertIn(f"desc = je_space_race_{m}_status", status)
                self.assertIn(f"trigger = {{ NOT = {{ has_journal_entry = je_space_race_{m} }} }}", status)
                self.assertEqual(status.count("triggered_desc"), 1)


class RootTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)

    def test_every_root_is_gated_on_the_active_entry(self):
        names = re.findall(r'name = "(widget_je_space_race_\w+)"', self.gui)
        expected = {f"widget_je_space_race_{m}_overview" for m in ALL}
        expected |= {f"widget_je_space_race_{m}" for m in CONTROLLED}
        expected.add("widget_je_space_race_reference")
        self.assertEqual(set(names), expected)
        self.assertEqual(len(names), len(expected))
        for name in names:
            head = _root(self.gui, name).split("\n\n")[0]  # the root's own properties
            self.assertIn('visible = "[JournalEntry.IsActive]"', head, name)

    def test_each_root_reads_only_its_own_milestone(self):
        for m in CONTROLLED:
            for name in (f"widget_je_space_race_{m}_overview", f"widget_je_space_race_{m}"):
                with self.subTest(root=name):
                    root = _root(self.gui, name)
                    self.assertIn(f"datacontext = \"[GetScriptedGui('sr_milestone_{m}_sgui')]\"", root)
                    self.assertEqual(_milestones_named(root), {m})

    def test_rivals_op_matches_the_scripted_gui(self):
        sgui = _block(_read(SGUIS), "sr_rivals_sgui")
        for op, m in enumerate(CONTROLLED):
            with self.subTest(milestone=m):
                root = _root(self.gui, f"widget_je_space_race_{m}")
                self.assertIn(f"MakeScopeValue( '(CFixedPoint){op}' )", root)
                if op < len(CONTROLLED) - 1:
                    self.assertRegex(sgui, rf"scope:op = {op} \}}\s*sr_rivals_participants_base = \{{ MILESTONE = {m} \}}")
        self.assertRegex(sgui, r"else = \{\s*sr_rivals_participants_base = \{ MILESTONE = solar_colonization \}")

    def test_the_first_line_left_the_rivals_list(self):
        """The overview's First cell carries it; the list names participants only."""
        self.assertNotIn("sr_rivals_line_base", _read(SGUIS))
        first = _type_body(self.gui, "te_sr_ov_first")
        for key in ("sr_rivals_first_open", "sr_rivals_first_claimed"):
            self.assertIn(f'tooltip = "{key}"', first)
        for m in RACING:
            overview = _root(self.gui, f"widget_je_space_race_{m}_overview")
            self.assertIn(f"sr_disp_first_claimed_{m}", overview)
        self.assertNotIn("te_sr_ov_first", _root(self.gui, "widget_je_space_race_solar_colonization_overview"))


class FlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _read(GUI)

    def test_section_flags_say_their_default(self):
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.text))
        self.assertEqual(len(flags), 2 * len(CONTROLLED) + 1)
        for f in flags:
            self.assertRegex(f, r"^sr_panel_\w+_(open|closed)$", f"section flag {f} does not say its default")
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", self.text))
            total = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", self.text))
            bare = total - negated
            if f.endswith("_closed"):   # shown unless closed: one bare (show-more), the rest negated
                self.assertEqual(bare, 1, f)
                self.assertGreaterEqual(negated, 2, f)
            else:                        # shown only when opened: one negated (show-more)
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 2, f)

    def test_live_sections_open_and_how_it_works_collapsed(self):
        for m in CONTROLLED:
            root = _root(self.text, f"widget_je_space_race_{m}")
            self.assertIn(f"'sr_panel_control_{m}_closed'", root)
            self.assertIn(f"'sr_panel_rivals_{m}_closed'", root)
        self.assertIn("Toggle('sr_panel_how_open')", _type_body(self.text, "te_sr_sec_how"))

    def test_no_old_flag_survives(self):
        for f in OLD_FLAGS:
            self.assertNotRegex(self.text, rf"'{f}'", f)


class GatingTest(unittest.TestCase):
    """What only matters while a programme runs is shown only then: solar
    colonization stays open, controls hidden, once every world is claimed or
    its production method is off."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)

    def test_controls_and_figures_follow_the_scripted_gui(self):
        control = _type_body(self.gui, "te_sr_sec_control")
        # the controls' container, the Safe button's own binding, the two table
        # rows and the margined heading
        self.assertEqual(control.count(f'visible = "[{IS_SHOWN_OP0}]"'), 5)
        self.assertEqual(control.count(f'visible = "[Not( {IS_SHOWN_OP0} )]"'), 1)
        for op in range(4):
            self.assertIn(f"MakeScopeValue( '(CFixedPoint){op}' ) ).End )]\"", control)
        self.assertEqual(control.count("Concatenate( ScriptedGui.IsValidTooltip("), 4)

    def test_overview_risk_and_progress_follow_the_scripted_gui(self):
        body = _type_body(self.gui, "te_sr_overview_milestone")
        # the state cells' container, the risk cell and the progress row
        self.assertEqual(body.count(f'visible = "[{IS_SHOWN_OP0}]"'), 3)
        self.assertEqual(body.count(f'visible = "[Not( {IS_SHOWN_OP0} )]"'), 1)  # Idle

    def test_state_cells_cover_every_code(self):
        for m in CONTROLLED:
            root = _root(self.gui, f"widget_je_space_race_{m}_overview")
            sv = f"ScriptValue('sr_disp_status_{m}')"
            self.assertIn(f"LessThanOrEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.{sv}, '(CFixedPoint)1' )", root)
            for code in (2, 3, 4):
                self.assertIn(f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.{sv}, '(CFixedPoint){code}' )", root)
            risk = f"ScriptValue('sr_risk_shown_{m}')"
            self.assertIn(f"NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.{risk}, '(CFixedPoint)0' )", root)
            self.assertIn(f"[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.{risk}, '(CFixedPoint)0' )]", root)


class HowItWorksTest(unittest.TestCase):
    def test_explanations_live_in_how_the_space_race_works(self):
        gui = _read(GUI)
        how = _type_body(gui, "te_sr_sec_how")
        for key in HOW_KEYS:
            self.assertIn(f'"{key}"', how, key)
        for sec in ("te_sr_sec_control", "te_sr_sec_rivals", "te_sr_overview_milestone",
                    "te_sr_overview_transit"):
            body = _type_body(gui, sec)
            self.assertNotIn("te_sr_note", body, f"{sec} carries an explanation")
            for key in HOW_KEYS:
                self.assertNotIn(key, body, sec)

    def test_the_old_long_labels_are_gone(self):
        """The funding label's "(each level draws on innovation)" is in the concept
        and in How the Space Race Works; the labels are concepts."""
        self.assertEqual(_loc("je_space_race_widget_approach_label"), "[concept_sr_approach]")
        self.assertEqual(_loc("je_space_race_widget_funding_label"), "[Concept('concept_sr_funding','Funding')]")
        concepts = _read(CONCEPTS)
        for c in ("concept_sr_approach", "concept_sr_funding", "concept_sr_setback_risk"):
            self.assertRegex(concepts, rf"(?m)^{c} = \{{\}}", c)
            self.assertTrue(_loc(c) and _loc(f"{c}_desc"), c)


class ProgrammeRowTest(unittest.TestCase):
    def test_nine_icons_each_its_own(self):
        row = _type_body(_read(GUI), "te_sr_ov_programme")
        cells = row.split("te_sr_ov_prog_cell = {")[1:]
        self.assertEqual([re.search(r'tooltip = "je_space_race_widget_prog_(\w+)"', c).group(1) for c in cells], ALL)
        for m, cell in zip(ALL, cells):
            with self.subTest(milestone=m):
                self.assertIn(f'texture = "gfx/interface/icons/event_icons/je_space_race_{m}.dds"', cell)
                self.assertEqual(_milestones_named(cell), {m})
                self.assertIn(f"ScriptValue('sr_disp_prog_{m}')", cell)
                self.assertEqual('blockoverride "first"' in cell, m in RACING)

    def test_the_textures_exist(self):
        tracked = subprocess.run(["git", "-C", REPO, "ls-files", "gfx/interface/icons/event_icons/"],
                                 capture_output=True, text=True, check=True).stdout.split()
        for m in ALL:
            self.assertIn(f"gfx/interface/icons/event_icons/je_space_race_{m}.dds", tracked)

    def test_every_entry_has_an_overview_that_draws_the_row(self):
        gui = _read(GUI)
        for composer in ("te_sr_overview_milestone", "te_sr_overview_transit"):
            self.assertIn("te_sr_ov_programme = {}", _type_body(gui, composer))


class DisplayValuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = _read(DISPLAY)
        cls.names = set(re.findall(r"(?m)^(sr_disp_\w+) = \{", cls.values))

    def test_every_value_the_panel_reads_exists(self):
        used = set(re.findall(r"ScriptValue\('(sr_disp_\w+)'\)", _read(GUI)))
        for key in re.findall(r"ScriptValue\('(sr_disp_\w+)'\)",
                              "\n".join(_read(p) for p in glob.glob(os.path.join(LOC_DIR, "*.yml")))):
            used.add(key)
        self.assertTrue(used)
        self.assertEqual(used - self.names, set())
        self.assertEqual(self.names - used, set(), "a display value nothing reads")

    def test_every_variable_read_is_guarded(self):
        for name in self.names:
            body = _strip_comments(_block(self.values, name))
            for var in re.findall(r"var:(\w+)", body):
                with self.subTest(value=name, var=var):
                    self.assertRegex(body, rf"limit = \{{ has_variable = {var} \}}[^\n]*var:{var}")

    def test_state_reads_the_single_derivation_site(self):
        for m in CONTROLLED:
            body = _block(self.values, f"sr_disp_status_{m}")
            self.assertIn(f"var:sr_{m}_last_status", body)
            self.assertIn("max = 4", body)

    def test_programme_codes_follow_the_tooltip_order(self):
        """first (4) → done (3) → running (1) → taken (2), as sr_prog_<m> tests."""
        custom = _read(CUSTOM_LOC)
        for m in RACING:
            with self.subTest(milestone=m):
                body = _block(self.values, f"sr_disp_prog_{m}")
                tests = re.findall(r"(has_(?:global_)?variable = (\w+)) \} value = (\d)", body)
                self.assertEqual([(v, int(c)) for _, v, c in tests],
                                 [(f"sr_was_first_{m}", 4), (f"sr_completed_{m}", 3),
                                  (f"sr_active_{m}", 1), (f"sr_global_first_{m}", 2)])
                loc = _block(custom, f"sr_prog_{m}")
                order = re.findall(r"has_(?:global_)?variable = (\w+)", loc)
                self.assertEqual(order, [v for _, v, _ in tests])

    def test_no_value_is_read_by_script(self):
        for sub in ("common", "events"):
            for path in glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True):
                if os.path.samefile(path, DISPLAY):
                    continue
                hit = re.search(r"\bsr_disp_\w+", _strip_comments(_read(path)))
                self.assertIsNone(hit, f"{path} reads {hit and hit.group(0)}")


class LocTest(unittest.TestCase):
    def test_no_panel_line_starts_or_ends_with_a_break(self):
        for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
            for key, value in re.findall(r'^ (je_space_race_widget_\w+):\d* "(.*)"\s*$', _read(path), re.M):
                with self.subTest(key=key):
                    self.assertFalse(value.startswith("\\n") or value.endswith("\\n"), key)

    def test_the_pace_sentence_is_the_state_icon_tooltip(self):
        overview = _type_body(_read(GUI), "te_sr_overview_milestone")
        for note in ("drift", "safe", "ambitious", "shielded"):
            self.assertIn(f'tooltip = "sr_pace_note_{note}"', overview)
        self.assertNotRegex(_read(CUSTOM_LOC), r"(?m)^sr_\w+_pace = \{")


if __name__ == "__main__":
    unittest.main()
