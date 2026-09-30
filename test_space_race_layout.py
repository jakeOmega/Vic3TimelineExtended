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
       "interstellar_probe", "interstellar_results", "solar_colonization"]  # journal order
# The programme row: one icon per entry, except that the Interstellar Probe and
# the wait for its data share one four-state icon (owner's play-test, round 3).
ROW = ["suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
       "interstellar", "solar_colonization"]
SR_ICONS = "gfx/interface/icons/space_race_icons/"   # the Space Race's own art (PR #586)
INTERSTELLAR_STATES = {0: "interstellar_not_begun", 1: "interstellar_under_way",
                       2: "interstellar_awaiting_data", 3: "interstellar_data_received"}
ICONS_DOC = os.path.join(REPO, "docs", "systems", "space_race_gui_icons.md")
COLONY_EVENTS = os.path.join(REPO, "events", "space_race_colony_events.txt")
COLONY_MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "space_race_modifiers.txt")
# The events that offer each stage's worlds (space_race_colony_events.<n>).
COLONY_STAGES = {1: range(1, 11), 2: range(11, 18), 3: range(18, 24), 4: range(24, 30), 5: range(30, 35)}
# The kind of world each colony is, and so which space_race_icons/colony_<kind>.dds its row shows.
COLONY_KINDS = {
    "mars": ["valles_marineris", "olympus_mons", "hellas", "utopia", "arcadia"],
    "asteroid": ["ceres", "vesta", "psyche", "pallas", "hygiea"],
    "jovian": ["io", "europa", "ganymede", "callisto", "himalia", "amalthea"],
    "venus": ["venus"],
    "mercury": ["mercury"],
    "saturnian": ["titan", "enceladus", "rhea", "mimas", "iapetus"],
    "uranian": ["titania", "oberon", "miranda", "ariel"],
    "neptunian": ["triton", "proteus"],
    "dwarf": ["pluto", "eris", "makemake", "haumea", "sedna"],
}

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
    """A journal root as the journal renders it: the wrapper, and the body of the
    milestone's own type it wraps (te_sr_<m>_overview, te_sr_<m>_status), which
    the Timeline Extended window's Space Race tab instances too."""
    m = re.search(rf'name = "{name}"', text)
    assert m, f"no root {name}"
    start = text.rfind("flowcontainer = {", 0, m.start())
    brace = text.index("{", start)
    root = text[start:_close(text, brace) + 1]
    for wrapped in re.findall(r"^\t(te_sr_\w+_(?:overview|status)) = \{\}$", root, re.M):
        root += "\n" + _type_body(text, wrapped)
    return root


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
        marks = ['block "sr_status_standard"', 'block "sr_risk_lit"', 'block "sr_third_cells"',
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
            # round 2: fixed-width roots, never content-sized wrappers centred in the panel
            self.assertIn("minimumsize = { 520 -1 }", head, name)

    def test_composers_and_number_columns_are_fixed_width(self):
        for composer in ("te_sr_overview_milestone", "te_sr_overview_transit",
                         "te_sr_status_sections", "te_sr_reference_sections"):
            self.assertIn("minimumsize = { 520 -1 }", _type_body(self.gui, composer).split("\n\n")[0], composer)
        bar = _type_body(self.gui, "te_sr_ov_bar_row")
        # round 3: the label column fits "Next Colony" (test_space_race_labels.py)
        for width in (110, 210):
            self.assertIn(f"minimumsize = {{ {width} -1 }}\n\t\t\tmaximumsize = {{ {width} -1 }}", bar)
        self.assertIn("size = { 140 18 }", bar)
        self.assertIn("spacing = 8", bar)  # 110 + 140 + 210 + 2 × 8 = 476, inside the 480 column

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
        # two live sections per milestone, solar colonization's Our Colonies, and the shared reference
        self.assertEqual(len(flags), 2 * len(CONTROLLED) + 2)
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
        self.assertIn("Toggle('sr_panel_colonies_closed')", _type_body(self.text, "te_sr_sec_colonies"))

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
        for op in range(5):  # 4 is Standard (round 2)
            self.assertIn(f"MakeScopeValue( '(CFixedPoint){op}' ) ).End )]\"", control)
        self.assertEqual(control.count("Concatenate( ScriptedGui.IsValidTooltip("), 5)

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


def _colony_sites():
    """[(event number, [the two specializations it grants])] in event order."""
    text = _read(COLONY_EVENTS)
    parts = re.split(r"\n(space_race_colony_events\.(\d+)) = \{", text)
    return [(int(parts[i + 1]), re.findall(r"sr_grant_colony_modifier = \{ MODIFIER = (\w+) \}", parts[i + 2]))
            for i in range(1, len(parts), 3)]


class ColoniesTest(unittest.TestCase):
    """The Our Colonies section of the solar colonization panel: one row for each
    of the 68 specializations, shown while the country holds it."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.values = _read(DISPLAY)
        cls.sites = _colony_sites()
        cls.section = _type_body(cls.gui, "te_sr_sec_colonies")
        cls.mods = [m for _, ms in cls.sites for m in ms]

    def _order(self, text):
        return re.findall(r"text = \"(sr_colony_\w+)\"", text)

    def test_every_specialization_has_a_row_in_the_order_the_events_offer_them(self):
        self.assertEqual(len(self.sites), 34)
        self.assertTrue(all(len(ms) == 2 for _, ms in self.sites))
        self.assertEqual(self._order(self.section), self.mods)
        static = re.findall(r"(?m)^(sr_colony_\w+) = \{", _read(COLONY_MODIFIERS))
        self.assertEqual(sorted(self.mods), sorted(static), "a colony modifier no event grants, or the reverse")

    def test_a_row_reads_its_own_held_record(self):
        """The row's value, its tooltip and its name are one modifier's, and the
        value reads that modifier's <modifier>_held (sr_grant_colony_modifier)."""
        rows = self.section.split("te_sr_colony_row = {")[1:]
        self.assertEqual(len(rows), 68)
        for row, mod in zip(rows, self.mods):
            sx = mod[len("sr_colony_"):]
            with self.subTest(modifier=mod):
                self.assertIn(f"ScriptValue('sr_disp_colony_{sx}'), '(CFixedPoint)1' )", row)
                self.assertIn(f'tooltip = "je_space_race_widget_colony_{sx}_tt"', row)
                body = _strip_comments(_block(self.values, f"sr_disp_colony_{sx}"))
                self.assertRegex(body, rf"limit = \{{ has_variable = {mod}_held \}} value = 1")
                self.assertEqual(_loc(f"je_space_race_widget_colony_{sx}_tt"),
                                 f"#header ${mod}$#!\\n[GetStaticModifier('{mod}').GetDesc]")

    def test_stage_counts_and_headings_follow_the_events(self):
        for stage, numbers in COLONY_STAGES.items():
            mods = [m for n, ms in self.sites if n in numbers for m in ms]
            with self.subTest(stage=stage):
                body = _strip_comments(_block(self.values, f"sr_disp_colonies_stage_{stage}"))
                self.assertEqual(re.findall(r"add = sr_disp_colony_(\w+)", body),
                                 [m[len("sr_colony_"):] for m in mods])
                self.assertIn(f"ScriptValue('sr_disp_colonies_stage_{stage}'), '(CFixedPoint)1' )", self.section)
                self.assertEqual(_loc(f"je_space_race_widget_colonies_stage_{stage}").split(":")[0], f"Stage {stage}")
        held = _strip_comments(_block(self.values, "sr_disp_colonies_held"))
        self.assertEqual(re.findall(r"add = (\w+)", held), [f"sr_disp_colonies_stage_{s}" for s in COLONY_STAGES])

    def test_a_stage_heading_sits_above_its_own_rows(self):
        headings = [m.start() for m in re.finditer(r"sr_disp_colonies_stage_\d", self.section)]
        self.assertEqual(len(headings), 5)
        for stage, numbers in COLONY_STAGES.items():
            first = next(m for n, ms in self.sites if n in numbers for m in ms)
            last = [m for n, ms in self.sites if n in numbers for m in ms][-1]
            self.assertLess(self.section.index(f"sr_disp_colonies_stage_{stage}"),
                            self.section.index(f'text = "{first}"'))
            self.assertLess(self.section.index(f'text = "{last}"'),
                            self.section.index(f"sr_disp_colonies_stage_{stage + 1}") if stage < 5 else len(self.section))

    def test_the_section_is_solar_colonizations_alone(self):
        self.assertEqual(len(re.findall(r"te_sr_sec_colonies = \{\}", self.gui)), 1)
        self.assertIn("te_sr_sec_colonies = {}", _type_body(self.gui, "te_sr_solar_colonization_status"))
        for m in ALL:
            if m != "solar_colonization" and m != "interstellar_results":
                self.assertNotIn("te_sr_sec_colonies", _type_body(self.gui, f"te_sr_{m}_status"), m)

    def test_it_stacks_below_the_live_sections_and_shows_in_passive_mode(self):
        status = _type_body(self.gui, "te_sr_solar_colonization_status")
        self.assertIn("direction = vertical", status.split("\n\n")[0])
        self.assertLess(status.index("te_sr_status_sections = {"), status.index("te_sr_sec_colonies = {}"))
        # not behind the controls' is_shown: a finished programme still lists its colonies
        self.assertNotIn("ScriptedGui.IsShown", self.section)
        self.assertIn('visible = "[JournalEntry.IsActive]"', self.section.split("\n\n")[0])

    def test_every_name_fits_its_row(self):
        row = _type_body(self.gui, "te_sr_colony_row")
        self.assertIn("size = { 442 24 }", row)
        self.assertIn("max_width = 442", row)
        self.assertIn("spacing = 4", row)
        self.assertIn("margin = { 4 1 }", row)  # 24 icon + 4 + 442 name + 2 x 4 = the 480 column
        self.assertIn("using = fontsize_medium", row)
        for mod in self.mods:
            with self.subTest(modifier=mod):
                need = len(_loc(mod)) * 8.6 * 1.1  # the labels test's medium-font budget
                self.assertLessEqual(need, 442, _loc(mod))

    def test_a_row_shows_the_icon_of_its_kind_of_world(self):
        """Nine kinds of world, not 34 icons: a row's icon follows its world, and
        the second specialization of a world shows the same one."""
        kind_of = {w: k for k, ws in COLONY_KINDS.items() for w in ws}
        self.assertEqual((len(COLONY_KINDS), len(kind_of)), (9, 34))
        rows = self.section.split("te_sr_colony_row = {")[1:]
        seen = set()
        for row, mod in zip(rows, self.mods):
            sx = mod[len("sr_colony_"):]
            worlds = [w for w in kind_of if sx.startswith(w + "_")]
            with self.subTest(modifier=mod):
                self.assertEqual(len(worlds), 1, f"{sx} names no world, or two")
                seen.add(worlds[0])
                self.assertRegex(row, rf'blockoverride "colony_icon" \{{\s*texture = '
                                      rf'"{SR_ICONS}colony_{kind_of[worlds[0]]}\.dds"\s*\}}')
        self.assertEqual(seen, set(kind_of), "a world in the table has no colony")

    def test_a_kind_of_world_sits_under_one_stage_heading(self):
        kind_of = {w: k for k, ws in COLONY_KINDS.items() for w in ws}
        stage_of = {n: st for st, ns in COLONY_STAGES.items() for n in ns}
        stages = {}
        for n, mods in self.sites:
            for mod in mods:
                sx = mod[len("sr_colony_"):]
                kind = kind_of[next(w for w in kind_of if sx.startswith(w + "_"))]
                stages.setdefault(kind, set()).add(stage_of[n])
        self.assertEqual(set(stages), set(COLONY_KINDS))
        for kind, found in stages.items():
            with self.subTest(kind=kind):
                self.assertEqual(len(found), 1, f"{kind} spans stages {sorted(found)}")


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
    def test_eight_icons_in_journal_order(self):
        row = _type_body(_read(GUI), "te_sr_ov_programme")
        found = re.findall(r"\bte_sr_ov_prog_cell(_interstellar)? = \{", row)
        cells = re.split(r"\bte_sr_ov_prog_cell(?:_interstellar)? = \{", row)[1:]
        names = []
        for suffix, cell in zip(found, cells):
            if suffix:
                self.assertTrue(cell.lstrip().startswith("}"), "the interstellar cell takes no overrides")
                names.append("interstellar")
            else:
                names.append(re.search(r'tooltip = "je_space_race_widget_prog_(\w+)"', cell).group(1))
        self.assertEqual(names, ROW)
        for m, cell in zip(names, cells):
            if m == "interstellar":
                continue
            with self.subTest(milestone=m):
                self.assertIn(f'texture = "gfx/interface/icons/event_icons/je_space_race_{m}.dds"', cell)
                self.assertEqual(_milestones_named(cell), {m})
                self.assertIn(f"ScriptValue('sr_disp_prog_{m}')", cell)
                self.assertEqual('blockoverride "first"' in cell, m in RACING)

    def test_the_row_fits_the_column(self):
        cell = re.search(r"size = \{ (\d+) \d+ \}", _type_body(_read(GUI), "te_sr_ov_prog_cell")).group(1)
        spacing = re.search(r"direction = horizontal\s+spacing = (\d+)",
                            _type_body(_read(GUI), "te_sr_ov_programme")).group(1)
        self.assertLessEqual(len(ROW) * int(cell) + (len(ROW) - 1) * int(spacing), 480)

    def test_the_textures_exist(self):
        tracked = subprocess.run(["git", "-C", REPO, "ls-files", "gfx/interface/icons/event_icons/"],
                                 capture_output=True, text=True, check=True).stdout.split()
        for m in ALL:
            self.assertIn(f"gfx/interface/icons/event_icons/je_space_race_{m}.dds", tracked)

    def test_every_entry_has_an_overview_that_draws_the_row(self):
        gui = _read(GUI)
        for composer in ("te_sr_overview_milestone", "te_sr_overview_transit"):
            self.assertIn("te_sr_ov_programme = {}", _type_body(gui, composer))


class InterstellarCellTest(unittest.TestCase):
    """The Interstellar Probe and its wait for data: one cell, four states, each
    its own icon, texture and hover, never two at once (round 3)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _type_body(_read(GUI), "te_sr_ov_prog_cell_interstellar")
        starts = [m.start() for m in re.finditer(r"(?m)^\t\ticon = \{", cls.body)]
        cls.icons = [cls.body[i:_close(cls.body, cls.body.index("{", i)) + 1] for i in starts]

    def test_four_states_and_the_flag(self):
        self.assertEqual(len(self.icons), 5)
        codes = []
        for n, icon in enumerate(self.icons[:4]):
            with self.subTest(state=n):
                visibles = re.findall(r'visible = "(.*)"', icon)
                self.assertEqual(len(visibles), 1, "one visible per widget")
                m = re.fullmatch(r"\[EqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\."
                                 r"ScriptValue\('sr_disp_prog_interstellar'\), '\(CFixedPoint\)(\d)' \)\]",
                                 visibles[0])
                self.assertIsNotNone(m, visibles[0])
                codes.append(int(m.group(1)))
                self.assertIn(f'tooltip = "je_space_race_widget_prog_interstellar_{n}"', icon)
                self.assertIn(f'texture = "{SR_ICONS}{INTERSTELLAR_STATES[n]}.dds"', icon)
                self.assertNotIn("alpha", icon, "the art carries the state; no state is faded")
        # Each state tests equality with a code of its own, so no two show at once.
        self.assertEqual(codes, [0, 1, 2, 3])
        flag = self.icons[4]
        self.assertIn("ScriptValue('sr_disp_prog_interstellar_probe'), '(CFixedPoint)4'", flag)
        self.assertIn("alwaystransparent = yes", flag)
        self.assertNotIn("tooltip", flag)

    def test_the_code_covers_every_state_once(self):
        body = _strip_comments(_block(_read(DISPLAY), "sr_disp_prog_interstellar"))
        self.assertRegex(body, r"^\s*value = 0")
        tests = re.findall(r"has_variable = (\w+) \} value = (\d)", body)
        self.assertEqual(tests, [("sr_interstellar_results_received", "3"), ("sr_probe_launched", "2"),
                                 ("sr_active_interstellar_probe", "1")])

    def test_the_flags_it_reads_are_set(self):
        script = "\n".join(_strip_comments(_read(p)) for sub in ("common", "events")
                           for p in glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True))
        for flag in ("sr_interstellar_results_received", "sr_probe_launched", "sr_active_interstellar_probe"):
            self.assertRegex(script, rf"set_variable = \{{ name = {flag}\b", flag)

    def test_every_state_has_its_hover(self):
        for n in range(4):
            self.assertTrue(_loc(f"je_space_race_widget_prog_interstellar_{n}"))

    def test_every_state_has_a_row_in_the_icon_list(self):
        doc = _read(ICONS_DOC)
        for n, texture in INTERSTELLAR_STATES.items():
            with self.subTest(state=n):
                self.assertRegex(doc, rf"(?m)^\| {n} \| [^|]+\| [^|]+\| `{texture}\.dds` \|$")



# Textures the widget uses as they are: vanilla's, used as vanilla uses them.
# Everything else is the Space Race's own art or a #571 journal icon.
VANILLA_KEPT = {"gfx/interface/backgrounds/round_frame_dec.dds",
                # the rival rows' band marker, drawn as the UN's authority bar draws it
                "gfx/interface/icons/generic_icons/transparent.dds",
                "gfx/interface/progressbar/progressbar_marker.dds"}


def _enclosing(text, anchor, opener):
    """The block opened by the last `opener` before `anchor` (e.g. the icon
    cell holding a given tooltip)."""
    i = text.index(anchor)
    start = text.rindex(opener, 0, i)
    brace = text.index("{", start)
    return text[start:_close(text, brace) + 1]


class SpaceRaceIconsTest(unittest.TestCase):
    """The Space Race's own icons (PR #586) replace every placeholder."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)

    def _cell_texture(self, anchor):
        cell = _enclosing(self.gui, anchor, "te_sr_ov_icon_label = {")
        return re.findall(r'texture = "([^"]+)"', cell)

    def test_each_state_draws_its_own_icon(self):
        for anchor, name in (('tooltip = "je_space_race_widget_ov_idle_tt"', "state_idle"),
                             ('tooltip = "sr_pace_note_standard"', "state_standard"),
                             ('tooltip = "sr_pace_note_safe"', "state_safe"),
                             ('tooltip = "sr_pace_note_ambitious"', "state_ambitious"),
                             ('tooltip = "sr_pace_note_shielded"', "state_shielded"),
                             ('block "sr_risk_lit"', "risk"),
                             ('block "sr_risk_unlit"', "risk"),
                             ('tooltip = "sr_rivals_first_open"', "first"),
                             ('tooltip = "sr_rivals_first_claimed"', "first"),
                             ('text = "je_space_race_widget_ov_stage"', "stage")):
            with self.subTest(cell=anchor):
                self.assertEqual(self._cell_texture(anchor), [f"{SR_ICONS}{name}.dds"])

    def test_the_first_to_finish_mark(self):
        for cell in ("te_sr_ov_prog_cell", "te_sr_ov_prog_cell_interstellar"):
            with self.subTest(cell=cell):
                mark = _enclosing(_type_body(self.gui, cell), "size = { 18 18 }", "icon = {")
                self.assertIn(f'texture = "{SR_ICONS}first_mark.dds"', mark)

    def test_the_pies(self):
        pie = _type_body(self.gui, "te_sr_ov_pie")
        self.assertEqual(re.findall(r'texture = "([^"]+)"', pie)[-3:],
                         [f"{SR_ICONS}pie_unclaimed.dds", f"{SR_ICONS}pie_claimed.dds", f"{SR_ICONS}pie_ours.dds"])
        self.assertEqual(pie.count("framesize = { 128 128 }\n\t\t\t\tframe = 2"), 3)

    def test_no_placeholder_left(self):
        journal = {f"gfx/interface/icons/event_icons/je_space_race_{m}.dds" for m in ALL}
        for path in re.findall(r'texture = "(gfx/interface/[^"]+)"', self.gui):
            with self.subTest(path=path):
                self.assertTrue(path.startswith(SR_ICONS) or path in journal or path in VANILLA_KEPT,
                                f"placeholder left: {path}")

    def test_every_icon_exists_once_the_art_is_in(self):
        tracked = set(subprocess.run(["git", "-C", REPO, "ls-files", SR_ICONS],
                                     capture_output=True, text=True, check=True).stdout.split())
        if not tracked:
            self.skipTest("the #586 art is not on this branch yet")
        for path in sorted(set(re.findall(rf'texture = "({re.escape(SR_ICONS)}[^"]+)"', self.gui))):
            with self.subTest(path=path):
                self.assertIn(path, tracked)

    def test_every_icon_has_a_row_in_the_list(self):
        doc = _read(ICONS_DOC)
        for path in sorted(set(re.findall(rf'texture = "{re.escape(SR_ICONS)}([^"]+)"', self.gui))):
            with self.subTest(file=path):
                self.assertRegex(doc, rf"(?m)^\|.*\| `{re.escape(path)}` \|$")


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
                    # the read sits straight after its own guard, in the same `if`
                    self.assertRegex(body, rf"limit = \{{ has_variable = {var} \}}\s*(?:value = 1\s+)?"
                                           rf"(?:add|value) = (?:\{{\s*value = )?var:{var}\b")

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
        for note in ("standard", "safe", "ambitious", "shielded"):
            self.assertIn(f'tooltip = "sr_pace_note_{note}"', overview)
        self.assertNotRegex(_read(CUSTOM_LOC), r"(?m)^sr_\w+_pace = \{")


if __name__ == "__main__":
    unittest.main()
