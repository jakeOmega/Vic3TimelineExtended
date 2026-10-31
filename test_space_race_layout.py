"""The Space Race panels' layout (gui_style_guide.md; the UN's test_un_layout.py).

The nine milestone entries each attach an overview, their live sections and one
shared reference from gui/journal_entry_widgets/space_race_widget.gui. These
tests hold the section order, that collapse flags say their default, that the
parts which only matter while a programme runs are gated on it, that the
explanations live in How the Space Race Works, that each milestone's root reads
only its own milestone's data, and that the overview's display values are
guarded and follow the single derivation sites they mirror.
"""
import functools
import glob
import os
import re
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
import gen_solar_sites as gss  # noqa: E402
import gui_tree  # noqa: E402
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_space_race.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "space_race_sguis.txt")
DISPLAY = os.path.join(REPO, "common", "script_values", "space_race_display_values.txt")
# The Solar System rows' values, generated from the site table (gen_solar_sites.py).
SITES_DISPLAY = os.path.join(REPO, "common", "script_values", "sr_sites_display_generated.txt")
# The per-world and per-slot rows that read them (gen_solar_sites.py too).
SITES_ROWS = os.path.join(REPO, "gui", "journal_entry_widgets", "sr_sites_generated_rows.gui")
WINDOWS_GUI = os.path.join(REPO, "gui", "sr_launch_window_widgets.gui")  # Next Windows (colony management § 6)
# The fleets (slice 6): a hand-written file of panel figures and a generated one.
FLEETS_DISPLAY = (os.path.join(REPO, "common", "script_values", "sr_fleet_display_values.txt"),
                  os.path.join(REPO, "common", "script_values", "sr_fleets_display_generated.txt"))
FLEETS_ROWS = os.path.join(REPO, "gui", "journal_entry_widgets", "sr_fleets_generated_rows.gui")
CUSTOM_LOC = os.path.join(REPO, "common", "customizable_localization", "space_race_custom_loc.txt")
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

RACING = ["suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
          "interstellar_probe"]
CONTROLLED = RACING + ["solar_colonization"]  # the eight with controls, in je_space_race.txt's order
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
COLONY_STAGES = {0: range(35, 41), 1: range(1, 11), 2: range(11, 18), 3: range(18, 24), 4: range(24, 30),
                 5: range(30, 35)}
# The kind of world each colony is, and so which space_race_icons/colony_<kind>.dds its row shows.
COLONY_KINDS = {
    "moon": ["shackleton", "peary", "tranquility", "marius", "daedalus", "imbrium"],
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
            "je_space_race_widget_how_rivals", "je_space_race_widget_how_programme",
            "je_space_race_widget_how_powers", "je_space_race_widget_how_orbit"]
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


@functools.lru_cache(maxsize=None)
def _all_loc():
    """Every English loc key and its text, the last file in name order winning."""
    out = {}
    for path in sorted(glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True)):
        for m in re.finditer(r'^ (\w+):\d* "(.*)"\s*$', _read(path), re.M):
            out[m.group(1)] = m.group(2)
    return out


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

    def test_each_root_lists_its_own_rivals(self):
        """Audit SPC-9: Rivals is a datamodel of the milestone's own list, so
        the "+N more" scripted GUI went."""
        self.assertNotIn("sr_rivals_sgui", _read(SGUIS))
        for m in CONTROLLED:
            with self.subTest(milestone=m):
                root = _root(self.gui, f"widget_je_space_race_{m}")
                lists = set(re.findall(r"GetList\('sr_rivals_list_(\w+)'\)", root))
                self.assertEqual(lists, {m})

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
        # two live sections per milestone; solar colonization's Colony Fleets,
        # Solar System and its "show all" toggle, Colonies (audit SPC-5: one
        # table for what Our Colonies, Settlers, Colony Modules, Colony
        # Autonomy and Colony Defences showed) and How Solar Colonization
        # Works; the shared reference; the Space Race tab's Space Powers and
        # Orbit; and under Full Colonies Space Command, Space Fleets and
        # Locations (slice 6); and the colony target popup's "show all"
        # (UI pass design § 5)
        self.assertEqual(len(flags), 2 * len(CONTROLLED) + 12)
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
        # row 1 while running (the state cells and the risk cell) and the progress row
        self.assertEqual(body.count(f'visible = "[{IS_SHOWN_OP0}]"'), 2)
        self.assertEqual(body.count(f'visible = "[Not( {IS_SHOWN_OP0} )]"'), 1)  # row 1 while idle

    def test_row_1_is_two_rows_of_fixed_contents(self):
        # One row, 318 idle and 480 running, was centred at its first width and
        # ran past the 480 column when a programme resumed with the panel open
        # (gui_modding_guide.md gotcha #43). Now a running row and an idle row,
        # each gated whole, each one width: every group in it shows one cell.
        tree = gui_tree.parse(self.gui)
        types = {n.name: n for n in tree.walk() if n.kind == "type"}
        cell = gui_tree.size(types["te_sr_ov_icon_label"])[0]
        panel = next(c for c in gui_tree.widgets(types["te_sr_overview_milestone"]) if c.kind == "te_sr_panel")
        running, idle = gui_tree.widgets(panel)[:2]
        gate = [(row.prop("visible") or gui_tree.Prop("visible", "", 0, True)).value for row in (running, idle)]
        self.assertEqual(gate, [f"[{IS_SHOWN_OP0}]", f"[Not( {IS_SHOWN_OP0} )]"])
        for row in (running, idle):
            self.assertEqual((row.prop("direction").value, row.prop("parentanchor").value), ("horizontal", "hcenter"))
            self.assertEqual([(c.kind, c.name) for c in row.children if c.kind == "block"], [("block", "sr_third_cells")])
        state, risk = gui_tree.widgets(running)
        for group, prefix in ((state, "sr_status_"), (risk, "sr_risk_")):
            with self.subTest(group=prefix):
                self.assertIsNone(group.prop("visible"))
                cells = gui_tree.widgets(group)
                self.assertTrue(cells)
                for c in cells:
                    self.assertEqual(c.kind, "te_sr_ov_icon_label")
                    self.assertIsNone(c.prop("visible"))
                    self.assertTrue(any(b.kind == "block" and b.name.startswith(prefix) for b in c.children))
        ((idle_kind, idle_gate),) = [(c.kind, c.prop("visible")) for c in gui_tree.widgets(idle)]
        self.assertEqual((idle_kind, idle_gate), ("te_sr_ov_icon_label", None))
        spacing = int(running.prop("spacing").value)
        self.assertEqual(3 * cell + 2 * spacing, 480)
        self.assertEqual(2 * cell + spacing, 318)

    def test_state_cells_cover_every_code(self):
        for m in CONTROLLED:
            root = _root(self.gui, f"widget_je_space_race_{m}_overview")
            sv = f"ScriptValue('sr_disp_status_{m}')"
            self.assertIn(f"LessThanOrEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.{sv}, '(CFixedPoint)1' )", root)
            for code in (2, 3):
                self.assertIn(f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.{sv}, '(CFixedPoint){code}' )", root)
            # Code 4, shielded, went with the post-setback cooldown (2026-10-31).
            self.assertNotIn(f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.{sv}, '(CFixedPoint)4' )", root)
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
    """The Colonies table of the solar colonization panel (audit SPC-5, SPC-19):
    one generated row per world, shown while ours, its views' cells reading its
    own values, and the name's hover its held specializations' effects."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.rows_file = _read(SITES_ROWS)
        cls.values = _read(DISPLAY)
        cls.sites = _colony_sites()
        cls.section = _type_body(cls.gui, "te_sr_sec_colonies")
        cls.mods = [m for _, ms in cls.sites for m in ms]
        rows = cls.rows_file[cls.rows_file.index("type te_sr_colony_rows = flowcontainer {"):]
        cls.rows = rows[:rows.index("\ttype ", 1)]
        cls.loc = {}
        for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
            cls.loc.update(re.findall(r'^ ([\w.]+):\d* "(.*)"\s*$', _read(path), re.M))

    def _row_of(self, world):
        for row in self.rows.split("te_sr_colony_row = {")[1:]:
            if f'text = "sr_site_name_{world}"' in row:
                return row
        raise AssertionError(f"no colony row for {world}")

    def test_every_specialization_is_an_event_option_and_a_modifier(self):
        self.assertEqual(len(self.sites), 40)
        self.assertTrue(all(len(ms) == 2 for _, ms in self.sites))
        static = re.findall(r"(?m)^(sr_colony_\w+) = \{", _read(COLONY_MODIFIERS))
        self.assertEqual(sorted(self.mods), sorted(static), "a colony modifier no event grants, or the reverse")

    def test_one_generated_row_per_world(self):
        """The rows are the generator's (SPC-19): every world once, in the
        panel's order, so a new world can't go missing."""
        names = re.findall(r'text = "sr_site_name_(\w+)"', self.rows)
        self.assertEqual(len(names), 40)
        self.assertEqual(len(set(names)), 40)
        self.assertIn("te_sr_colony_rows = {}", self.section)

    def test_a_row_reads_its_own_held_record(self):
        """The name's hover names the world's two specializations, each shown
        while its sr_disp_colony_<spec> reads 1, which reads <modifier>_held."""
        for _, mods in self.sites:
            sxs = [m[len("sr_colony_"):] for m in mods]
            world = None
            for row in self.rows.split("te_sr_colony_row = {")[1:]:
                tt = re.search(r'tooltip = "je_space_race_widget_colony_site_tt_(\w+)"', row).group(1)
                hover = self.loc[f"je_space_race_widget_colony_site_tt_{tt}"]
                if all(f"'je_space_race_widget_colony_{sx}_tt'" in hover for sx in sxs):
                    world = tt
            self.assertIsNotNone(world, f"no row's hover names {mods}")
            hover = self.loc[f"je_space_race_widget_colony_site_tt_{world}"]
            for mod, sx in zip(mods, sxs):
                with self.subTest(modifier=mod):
                    self.assertIn(f"ScriptValue('sr_disp_colony_{sx}'), '(CFixedPoint)1' ), 'je_space_race_widget_colony_{sx}_tt'", hover)
                    body = _strip_comments(_block(self.values, f"sr_disp_colony_{sx}"))
                    self.assertRegex(body, rf"limit = \{{ has_variable = {mod}_held \}} value = 1")
                    self.assertEqual(self.loc[f"je_space_race_widget_colony_{sx}_tt"],
                                     f"#header ${mod}$#!\\n[GetStaticModifier('{mod}').GetDesc]")
        held = _strip_comments(_block(self.values, "sr_disp_colonies_held"))
        self.assertEqual(sorted(re.findall(r"add = sr_disp_colony_(\w+)", held)),
                         sorted(m[len("sr_colony_"):] for m in self.mods))

    def test_the_section_is_solar_colonizations_alone(self):
        self.assertEqual(len(re.findall(r"te_sr_sec_colonies = \{\}", self.gui)), 1)
        self.assertIn("te_sr_sec_colonies = {}", _type_body(self.gui, "te_sr_solar_colonization_status"))
        for m in ALL:
            if m != "solar_colonization" and m != "interstellar_results":
                self.assertNotIn("te_sr_sec_colonies", _type_body(self.gui, f"te_sr_{m}_status"), m)

    def test_the_colonization_panel_order(self):
        """Colony Fleets, Colonies, Space Command, Space Fleets, then Solar
        System (moved down by the owner, 2026-10-31) just above How Solar
        Colonization Works; the old per-aspect sections are gone (SPC-5)."""
        status = _type_body(self.gui, "te_sr_solar_colonization_status")
        self.assertIn("direction = vertical", status.split("\n\n")[0])
        self.assertEqual(re.findall(r"^\t\t(te_sr_sec_\w+) = \{\}", status, re.M),
                         ["te_sr_sec_colony_fleets", "te_sr_sec_colonies", "te_sr_sec_space_command",
                          "te_sr_sec_space_fleets", "te_sr_sec_solar_system", "te_sr_sec_how_colonies"])
        self.assertLess(status.index("te_sr_status_sections = {"), status.index("te_sr_sec_colony_fleets = {}"))
        for gone in ("te_sr_sec_settlers", "te_sr_sec_modules", "te_sr_sec_autonomy", "te_sr_sec_colony_defences",
                     "te_sr_settler_row", "te_sr_module_row", "te_sr_autonomy_row", "te_sr_defence_row"):
            self.assertNotIn(gone, self.gui + self.rows_file + _read(FLEETS_ROWS), gone)
        # not behind the controls' is_shown: a finished programme still lists its colonies
        self.assertNotIn("ScriptedGui.IsShown", self.section)
        self.assertIn('visible = "[JournalEntry.IsActive]"', self.section.split("\n\n")[0])

    def test_the_view_switch(self):
        """Four views (Defenses under Full Colonies only), picked by
        GetVariableSystem's sr_colony_view; the switch's button for the view
        shown is greyed. Each view's section items, heads and row cells are
        gated on the same test."""
        views = {"people": "GetVariableSystem.Clear('sr_colony_view')",
                 "modules": "GetVariableSystem.Set('sr_colony_view', 'modules')",
                 "autonomy": "GetVariableSystem.Set('sr_colony_view', 'autonomy')",
                 "defences": "GetVariableSystem.Set('sr_colony_view', 'defences')"}
        for view, onclick in views.items():
            with self.subTest(view=view):
                self.assertIn(f'onclick = "[{onclick}]"', self.section)
                self.assertIn(f'text = "je_space_race_widget_cv_{view}"', self.section)
        row = _type_body(self.gui, "te_sr_colony_row")
        head = _type_body(self.gui, "te_sr_colony_head_row")
        for view in ("modules", "autonomy", "defences"):
            test = f"GetVariableSystem.HasValue('sr_colony_view', '{view}')"
            # line 1's part and line 2's cells; the heads; the switch and the
            # section's own items
            self.assertGreaterEqual(row.count(test), 2, view)
            self.assertGreaterEqual(head.count(test), 1, view)
        # the People view is the default: no value, or one the rule doesn't offer
        self.assertIn("Not( Or( GetVariableSystem.HasValue('sr_colony_view', 'modules')", row)
        self.assertIn("ScriptValue('sr_disp_colonies_full')", self.section)

    def test_a_row_reads_its_own_world(self):
        for site in gss.panel_order():
            k = site.key
            row = self._row_of(k)
            with self.subTest(world=k):
                self.assertIn(f"ScriptValue('sr_disp_site_{k}')", row)
                self.assertIn(f"ScriptValue('sr_disp_def_{k}')", row)   # Defenses: ours, occupied too
                self.assertIn(f"ScriptValue('sr_disp_site_pop_{k}')", row)
                self.assertIn(f"ScriptValue('sr_disp_site_aut_{k}')", row)
                self.assertIn(f"ScriptValue('sr_disp_def_integrity_{k}')", row)
                self.assertIn(f'tooltip = "je_space_race_widget_autonomy_drift_tt_{k}"', row)
                self.assertEqual(set(re.findall(r"AddScope\( 'site', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \)", row)),
                                 {str(site.index)})
                for slot, mod in zip(("a", "b"), gss.spec_modifiers(site)):
                    self.assertIn(f'tooltip = "je_space_race_widget_colony_{mod[len("sr_colony_"):]}_tt"', row)

    def test_every_name_fits_its_row(self):
        row = _type_body(self.gui, "te_sr_colony_row")
        self.assertIn("size = { 180 24 }", row)
        self.assertIn("max_width = 180", row)
        for site in gss.SITES:
            with self.subTest(world=site.key):
                need = len(self.loc[f"sr_site_name_{site.key}"]) * 8.5 * 1.1  # the row font's budget
                self.assertLessEqual(need, 180, self.loc[f"sr_site_name_{site.key}"])

    def test_a_row_shows_the_icon_of_its_kind_of_world(self):
        """Ten kinds of world, not 40 icons: a row's icon follows its world."""
        kind_of = {w: k for k, ws in COLONY_KINDS.items() for w in ws}
        self.assertEqual((len(COLONY_KINDS), len(kind_of)), (10, 40))
        for site in gss.SITES:
            with self.subTest(world=site.key):
                self.assertRegex(self._row_of(site.key), rf'blockoverride "colony_icon" \{{\s*texture = '
                                                         rf'"{SR_ICONS}colony_{site.kind}\.dds"\s*\}}')

    def test_a_kind_of_world_sits_in_one_stage(self):
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

    def test_each_world_has_its_hovers(self):
        """The Solar System name's hover (SPC-7: stage, both specializations,
        our transit and window) and the drift's own terms (SPC-15)."""
        for site in gss.SITES:
            k = site.key
            with self.subTest(world=k):
                ss = self.loc[f"je_space_race_widget_ss_site_tt_{k}"]
                for mod in gss.spec_modifiers(site):
                    # each specialization's name heads its own effects, indented
                    # beneath it, so the two lists can't run together
                    self.assertIn(f"#bold ${mod}$#!#indent_newline:3 \\n[GetStaticModifier('{mod}').GetDesc]#!", ss)
                self.assertIn(f"$je_space_race_widget_colonies_stage_{site.stage}$", ss)
                if site in gss.LUNAR:  # no transit to show: founded the month a fleet leaves
                    self.assertIn("founds its colony the month it leaves", ss)
                    self.assertNotIn("sr_transit_months_", ss)
                else:
                    self.assertIn(f"ScriptValue('sr_transit_months_{gss.transit_body(site)}')", ss)
                self.assertEqual(f"'sr_ss_window_line_{site.body}'" in ss, site.body is not None)
                drift = self.loc[f"je_space_race_widget_autonomy_drift_tt_{k}"]
                for term in (f"sr_disp_site_aut_drift_{k}", f"sr_disp_aut_people_{k}", f"sr_disp_aut_distance_{k}",
                             f"sr_disp_aut_nocontact_{k}", "sr_disp_aut_war", "sr_disp_aut_destroyed",
                             f"sr_disp_site_aut_status_{k}"):
                    self.assertIn(f"ScriptValue('{term}')", drift)
                self.assertIn("[concept_sr_colony_autonomy]", drift)

    def test_the_slots_hover_reads_the_slots_modifier(self):
        """Colony management design § 5: a world's Slots hover gives its size's
        slots and our Colony Module Slots from the modifier itself, so a new
        source of the modifier shows there without an edit."""
        for site in gss.SITES:
            k = site.key
            with self.subTest(world=k):
                hover = self.loc[f"je_space_race_widget_slots_tt_{k}"]
                self.assertIn(f"#v {site.slots}#! here for its size", hover)
                self.assertIn(f"GetModifier.GetValueWithBreakdownFor('{gss.SLOTS_MODIFIER}')", hover)
                self.assertIn(f"${gss.SLOTS_MODIFIER}$", hover)

    def test_the_drift_and_its_terms_are_colored_as_a_cost(self):
        """Colony management design § 4.1: more autonomy is the holder's loss, so
        the drift and every term in its hover, the conditional lines too, read
        signed with positive red (|=-2), never |+=2's positive green."""
        lines = sorted(k for k in self.loc if k.startswith("sr_aut_line_"))
        self.assertEqual(lines, ["sr_aut_line_charter", "sr_aut_line_destroyed", "sr_aut_line_garrison",
                                 "sr_aut_line_nocontact", "sr_aut_line_war"])
        for key in lines:
            with self.subTest(line=key):
                self.assertEqual(re.findall(r"\|([^\]]*)\]", self.loc[key]), ["=-2"])
        for site in gss.SITES:
            k = site.key
            drift = self.loc[f"je_space_race_widget_autonomy_drift_tt_{k}"]
            with self.subTest(world=k):
                self.assertEqual(set(re.findall(r"'(sr_aut_line_\w+)'", drift)), set(lines))
                # Every figure but the last line's level, where it settles.
                formats = re.findall(r"ScriptValue\('(\w+)'\)\|([^\]]*)\]", drift)
                self.assertEqual([f for v, f in formats if v != f"sr_disp_aut_target_{k}"],
                                 ["=-2"] * (len(formats) - 1))
                self.assertIn(f"ScriptValue('sr_disp_aut_target_{k}')|0]", drift)

    def test_next_window_reads_the_moon_at_stage_0(self):
        """Lunar colonization 2b: at stage 0 the Next Window cell's third line
        names the Moon, which needs no window, not 'stage 0 of 5'."""
        cell = _enclosing(self.gui, 'tooltip = "je_space_race_widget_ovc_window_tt"', "te_banking_ov_cell = {")
        third = cell[cell.index('blockoverride "third_line"'):]
        stage = "GreaterThanOrEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_current_colonization_stage'), '(CFixedPoint)1' )"
        waits = "EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_held_beyond_moon'), '(CFixedPoint)1' )"
        # and, the Moon full without our Mars Landing, why the bar holds (design § 4)
        self.assertEqual(re.findall(r'visible = "\[(.*)\]"\n\s*text = "(\w+)"', third),
                         [(f"And( {stage}, Not( {waits} ) )", "je_space_race_widget_ovc_window_fig"),
                          (f"And( {stage}, {waits} )", "je_space_race_widget_ovc_window_fig_mars"),
                          (f"Not( {stage} )", "je_space_race_widget_ovc_window_fig_moon")])
        self.assertEqual(self.loc["je_space_race_widget_ovc_window_fig_moon"], "the Moon")
        waits_value = _block(_read(DISPLAY), "sr_disp_held_beyond_moon")
        self.assertIn("NOT = { sr_colonization_beyond_moon = yes }", waits_value)
        self.assertIn("NOT = { sr_sites_lunar_open = yes }", waits_value)


class HowItWorksTest(unittest.TestCase):
    def test_explanations_live_in_how_the_space_race_works(self):
        gui = _read(GUI)
        how = _type_body(gui, "te_sr_sec_how")
        for key in HOW_KEYS:
            self.assertIn(f'"{key}"', how, key)
        # audit SPC-4: the colony sections' rules are in How Solar Colonization
        # Works, collapsed, at the foot of the colonization panel
        how_colonies = _type_body(gui, "te_sr_sec_how_colonies")
        self.assertIn("Toggle('sr_panel_how_colonies_open')", how_colonies)
        for topic in ("fleets", "windows", "settlers", "modules", "autonomy", "space_command", "defences"):
            self.assertIn(f'"je_space_race_widget_howc_{topic}"', how_colonies, topic)
        for sec in ("te_sr_sec_control", "te_sr_sec_rivals", "te_sr_overview_milestone",
                    "te_sr_overview_transit", "te_sr_sec_colonies", "te_sr_sec_colony_fleets",
                    "te_sr_sec_solar_system", "te_sr_sec_space_command", "te_sr_sec_space_fleets",
                    "te_sr_colony_row", "te_sr_solar_colonization_overview"):
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


class NoUnderlineTest(unittest.TestCase):
    """Style guide rule 3 (owner, 2026-10-30): as in vanilla, a hover's label
    or figure is not underlined. The Space Race panel underlined nearly every
    hover under the rule of 2026-10-27; only a word inside running text may
    open its own tooltip, through a concept link or the inline
    #tooltippable;tooltip: form."""

    FILES = (GUI, os.path.join(REPO, "gui", "sr_launch_window_widgets.gui"),
             os.path.join(REPO, "gui", "journal_entry_widgets", "sr_sites_generated_rows.gui"),
             os.path.join(REPO, "gui", "journal_entry_widgets", "sr_fleets_generated_rows.gui"))

    def test_no_widget_underlines_its_text(self):
        for path in self.FILES:
            with self.subTest(file=os.path.basename(path)):
                text = re.sub(r"#[^\n]*", "", _read(path).replace("#tooltippable", "@TT@"))
                self.assertNotIn("@TT@", text)

    def test_no_panel_text_wraps_itself_in_an_underline(self):
        keys = [k for k in _all_loc() if re.match(r"(je_space_race|sr_|te_sr)", k)]
        self.assertGreater(len(keys), 500)
        for key in keys:
            with self.subTest(key=key):
                self.assertNotRegex(_all_loc()[key], r"#tooltippable(?!;tooltip:)")


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



# The furthest milestone a Space Powers row estimates, by code (sr_power_lead_code).
LEAD = ["suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
        "interstellar_probe", "solar_colonization"]
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "space_race_effects.txt")
VALUES = os.path.join(REPO, "common", "script_values", "space_race_values.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "space_race_triggers.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "space_race_on_actions.txt")


class SpacePowersTest(unittest.TestCase):
    """The Space Race tab's Space Powers (owner, 2026-10-25: see the AI rivals'
    progress with or without a milestone running): our row, then every other
    power, a datamodel of the list the monthly refresh fills (audit SPC-9)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.section = _type_body(cls.gui, "te_sr_sec_powers")

    def test_our_row_then_the_list(self):
        rows = re.split(r"\bte_sr_power_row = \{", self.section)[1:]
        self.assertEqual(len(rows), 2)
        self.assertIn('datacontext = "[GetPlayer.GetCapital]"', rows[0])
        self.assertIn("te_sr_power_lead_own = {}", rows[0])
        self.assertRegex(self.section, r'datamodel = "\[GetPlayer\.MakeScope\.GetList\(\'sr_powers_list\'\)\]"\s*'
                                       r'item = \{\s*te_sr_power_row = \{\s*datacontext = "\[Scope\.GetState\]"')
        self.assertIn("te_sr_power_lead_band = {}", rows[1])
        self.assertNotIn("row_visible", _type_body(self.gui, "te_sr_power_row"))
        self.assertNotIn("sr_powers_sgui", self.gui)
        self.assertNotIn("powers_more", self.section)
        # pending (the refresh has not run) and none still read the count
        self.assertIn("ScriptValue('sr_disp_power_total'), '(CFixedPoint)0' )", self.section)

    def test_the_refresh_fills_the_list(self):
        effects = _read(EFFECTS)
        refresh = _block(effects, "sr_powers_refresh")
        for m in LEAD:
            self.assertIn(f"sr_power_fuzz_base = {{ MILESTONE = {m}", refresh)
        self.assertLess(refresh.index("sr_powers_clear = yes"), refresh.index("ordered_country"))
        walk = refresh[refresh.index("ordered_country"):]
        for line in ("limit = { sr_is_space_power = yes }", "order_by = sr_power_rank_score", "min = 0",
                     "max = 40", "check_range_bounds = no",
                     "add_to_variable_list = { name = sr_powers_list target = scope:sr_power_capital }"):
            self.assertIn(line, walk)
        self.assertNotIn("sr_power_slot", effects)
        self.assertIn("sr_powers_list_selfcheck = yes", refresh)
        clear = _block(effects, "sr_powers_clear")
        self.assertIn("clear_variable_list = sr_powers_list", clear)
        for name in ["sr_power_total"] + [f"sr_power_{n}" for n in range(1, 9)]:
            self.assertIn(f"remove_variable = {name} }}", clear)
        # players in the race, monthly
        pulse = _read(ON_ACTIONS)
        self.assertRegex(pulse, r"is_player = yes\s+sr_space_race_on = yes\s+sr_in_space_race = yes\s+\}\s+"
                                r"sr_powers_refresh = yes")
        listed = _block(_read(TRIGGERS), "sr_is_space_power")
        for cond in ("NOT = { THIS = ROOT }", "sr_in_space_race = yes", "exists = capital"):
            self.assertIn(cond, listed)

    def test_the_list_self_check(self):
        """TE_SELF_CHECK sr_powers_list: once a game, OK and BROKEN, with the
        count, and only when two or more powers can tell a walk from a pick."""
        check = _block(_read(EFFECTS), "sr_powers_list_selfcheck")
        self.assertIn("NOT = { has_global_variable = sr_selfcheck_powers_list_done }", check)
        self.assertIn("set_global_variable = { name = sr_selfcheck_powers_list_done value = yes }", check)
        self.assertIn("var:sr_power_total >= 2", check)
        self.assertIn('debug_log = "TE_SELF_CHECK OK sr_powers_list', check)
        self.assertIn('debug_log = "TE_SELF_CHECK BROKEN sr_powers_list', check)
        self.assertIn("docs/testing/space-race-playtest.md", check)

    def test_each_estimate_column_shows_one_text_per_code(self):
        for column, prefix in (("te_sr_power_lead_band", "je_space_race_widget_power_lead_"),
                               ("te_sr_power_lead_own", "je_space_race_widget_power_own_")):
            with self.subTest(column=column):
                body = _type_body(self.gui, column)
                found = re.findall(r"ScriptValue\('sr_disp_power_lead'\), '\(CFixedPoint\)(\d)' \)\]\"\s+"
                                   r"text = \"(\w+)\"", body)
                self.assertEqual(found, [("0", "je_space_race_widget_power_lead_none")]
                                 + [(str(c), prefix + m) for c, m in enumerate(LEAD, start=1)])
        own = _type_body(self.gui, "te_sr_power_lead_own")
        for m in LEAD:
            self.assertIn(f"ScriptValue('sr_disp_progress_frac_{m}')", _loc(f"je_space_race_widget_power_own_{m}"))
            band = _loc(f"je_space_race_widget_power_lead_{m}")
            for end in ("lo", "hi"):
                self.assertIn(f"AddScope( 'sr_rival', State.GetCountry.MakeScope ).ScriptValue('sr_disp_rival_{end}_{m}')", band)
        self.assertNotIn("sr_disp_rival", own)

    def test_the_lead_code_follows_the_journal_order(self):
        body = _strip_comments(_block(_read(VALUES), "sr_power_lead_code"))
        found = re.findall(r"limit = \{ (?:has_variable = sr_active_(\w+)|sr_(solar_colonization)_running = yes) \} value = (\d)", body)
        self.assertEqual([(a or b, int(c)) for a, b, c in found],
                         list(reversed([(m, c) for c, m in enumerate(LEAD, start=1)])))

    def test_eight_icons_in_journal_order(self):
        row = _type_body(self.gui, "te_sr_power_row")
        found = re.findall(r"\bte_sr_power_cell(_interstellar)? = \{", row)
        cells = re.split(r"\bte_sr_power_cell(?:_interstellar)? = \{", row)[1:]
        names = []
        for suffix, cell in zip(found, cells):
            if suffix:
                names.append("interstellar")
            else:
                names.append(re.search(r'tooltip = "je_space_race_widget_power_prog_(\w+)"', cell).group(1))
        self.assertEqual(names, ROW)
        for m, cell in zip(names, cells):
            if m == "interstellar":
                continue
            with self.subTest(milestone=m):
                self.assertIn(f'texture = "gfx/interface/icons/event_icons/je_space_race_{m}.dds"', cell)
                self.assertEqual(_milestones_named(cell), {m})
                self.assertIn(f"State.GetCountry.MakeScope.ScriptValue('sr_disp_prog_{m}')", cell)
                self.assertEqual('blockoverride "first"' in cell, m in RACING)
        # 8 cells and their spacing, then the estimate column, inside the 480 row
        cell = int(re.search(r"size = \{ (\d+) \d+ \}", _type_body(self.gui, "te_sr_power_cell")).group(1))
        column = int(re.search(r"size = \{ (\d+) \d+ \}", _type_body(self.gui, "te_sr_power_lead_band")).group(1))
        spacing = int(re.search(r"direction = horizontal\s+spacing = (\d+)", row).group(1))
        self.assertLessEqual(len(ROW) * cell + len(ROW) * spacing + column, 480)

    def test_a_rows_hover_names_its_own_powers_state(self):
        """In the third person: a row says what its own power holds, never
        "another power got there first", which is the viewer's word."""
        custom = _read(CUSTOM_LOC)
        for m in [r for r in ROW if r != "interstellar"] + ["interstellar"]:
            with self.subTest(milestone=m):
                body = _block(custom, f"sr_power_prog_{m}")
                self.assertNotIn("sr_global_first", body)
                self.assertNotIn("sr_prog_state_taken", body)
                key = "je_space_race_widget_power_prog_" + m
                self.assertIn(f"State.GetCountry.GetCustom('sr_power_prog_{m}')", _loc(key))


class OrbitTest(unittest.TestCase):
    """The Space Race tab's Orbit section: debris and the anti-satellite strike,
    read on the player, so it shows with no journal entry behind it."""

    def test_rows_and_their_sources(self):
        body = _type_body(_read(GUI), "te_sr_sec_orbit")
        self.assertIn("te_sr_debris_row = {}", body)
        self.assertEqual(re.findall(r'text = "(je_space_race_widget_orbit_\w+_label)"', body),
                         [f"je_space_race_widget_orbit_{r}_label" for r in ("satellites", "strikes", "moratorium", "strike")])
        self.assertNotIn("JournalEntry", body)

    def test_debris_shows_once_in_the_tab(self):
        """SPC-8 (owner, 2026-10-27): Mission Control's debris row sits in a
        block each milestone's status type passes up as "sr_debris", which the
        Space Race tab overrides empty (test_te_systems_window.py), so the tab
        shows debris once, in Orbit; the journal keeps it in Mission Control."""
        gui = _read(GUI)
        self.assertRegex(_type_body(gui, "te_sr_sec_control"),
                         r'block "control_debris" \{\s*te_sr_debris_row = \{\}\s*\}')
        self.assertRegex(_type_body(gui, "te_sr_status_sections"),
                         r'blockoverride "control_debris" \{\s*block "status_debris" \{\s*te_sr_debris_row = \{\}\s*\}\s*\}')
        for m in CONTROLLED:
            with self.subTest(milestone=m):
                self.assertRegex(_type_body(gui, f"te_sr_{m}_status"),
                                 r'blockoverride "status_debris" \{\s*block "sr_debris" \{\s*te_sr_debris_row = \{\}\s*\}\s*\}')

    def test_the_debris_row_reads_the_player(self):
        """Mission Control's debris row is also the Orbit section's, outside
        any journal entry: every key it renders roots on GetPlayer."""
        for key in ("te_debris_row", "te_debris_row_tt", "te_debris_row_tt_cleaners",
                    "te_debris_row_tt_hazardous", "te_debris_row_tt_kessler"):
            with self.subTest(key=key):
                self.assertNotIn("JournalEntry", _loc(key))
                self.assertIn("GetPlayer", _loc(key))

    def test_the_satellite_codes_match_the_hover(self):
        values = _read(os.path.join(REPO, "common", "script_values", "te_orbital_debris_values.txt"))
        body = _strip_comments(_block(values, "te_asat_disp_satellites"))
        self.assertEqual(re.findall(r"value = (\d)", body), ["0", "3", "2", "1"])
        hover = _loc("te_orbit_satellites_tt")
        for code, word in ((3, "disrupted"), (2, "cooldown"), (1, "exposed"), (0, "none")):
            self.assertIn(f"'(CFixedPoint){code}' ), 'te_orbit_satellites_tt_{word}' )", hover)
            self.assertTrue(_loc(f"te_orbit_satellites_tt_{word}"))

    def test_the_strike_records_who_struck_whom(self):
        effect = _read(os.path.join(REPO, "common", "scripted_effects", "te_orbital_debris_effects.txt"))
        strike = _block(effect, "te_asat_strike_effect")
        self.assertIn("set_global_variable = { name = te_asat_last_striker value = ROOT }", strike)
        self.assertIn("set_global_variable = { name = te_asat_last_target value = scope:te_asat_target }", strike)
        sguis = _read(os.path.join(REPO, "common", "scripted_guis", "te_orbital_debris_sguis.txt"))
        record = _block(sguis, "te_asat_record_sgui")
        for name in ("te_asat_last_striker", "te_asat_last_target"):
            self.assertIn(f"exists = global_var:{name}", record)
        # the readiness check is the action's own: what it asks of the striker
        ready = _block(sguis, "te_asat_strike_ready_sgui")
        action = _read(os.path.join(REPO, "common", "diplomatic_actions", "te_asat_strike_action.txt"))
        for cond in ("has_technology_researched = guided_missiles", "sr_has_space_program = yes"):
            self.assertIn(cond, ready)
            self.assertIn(cond, action)
        self.assertIn("te_asat_has_orbital_assets = yes", ready)


# Textures the widget uses as they are: vanilla's, used as vanilla uses them.
# Everything else is the Space Race's own art or a #571 journal icon.
VANILLA_KEPT = {"gfx/interface/backgrounds/round_frame_dec.dds",
                # the rival rows' band marker, drawn as the UN's authority bar draws it
                "gfx/interface/icons/generic_icons/transparent.dds",
                # the module queue's move-up button, the base game's ship construction queue's (#1159)
                "gfx/interface/icons/generic_icons/up_up.dds",
                "gfx/interface/progressbar/progressbar_marker.dds"}
# A colony's page (space_race_gui_icons.md, "A colony's page"): art that already
# shows the thing, vanilla's or the mod's, and the page's own icons (icon batch 8).
PAGE_KEPT = {f"gfx/interface/icons/{p}" for p in (
    "generic_icons/population.dds", "generic_icons/battalions.dds", "state_status_icons/has_construction.dds",
    "generic_icons/trend_nochange.dds", "building_icons/building_government_administration.dds",
    "building_icons/building_space_mine.dds", "building_icons/building_space_command.dds",
    "building_icons/building_tourism_industry.dds", "covert_icons/operation_slot.dds",
    "building_icons/building_advanced_material_fabricator.dds")}
# In page order: the caption or module name that follows each icon, its file in
# SR_ICONS, and the placeholder it replaced. The Defenses icon is on the module
# row and the Defenses tile.
PAGE_ICONS = (
    ("je_space_race_widget_ch_crews", "page_crews.dds", "character_trait_icons/engineer.dds"),
    ("je_space_race_widget_page_staffing", "page_crewed.dds", "generic_icons/employment_not_full.dds"),
    ("je_space_race_widget_mod_name_hab", "module_hab.dds", "building_icons/urban_center.dds"),
    ("je_space_race_widget_mod_name_port", "module_port.dds", "building_icons/building_port.dds"),
    ("je_space_race_widget_mod_name_def", "module_def.dds", "building_icons/building_naval_fortification.dds"),
    ("je_space_race_widget_mod_name_lab", "module_lab.dds", "building_icons/building_university.dds"),
    ("je_space_race_widget_mod_name_culture", "module_culture.dds", "building_icons/building_arts_academy.dds"),
    ("je_space_race_widget_mod_name_train", "module_train.dds", "building_icons/building_barracks.dds"),
    ("je_space_race_widget_mod_name_bunker", "module_bunker.dds", "building_icons/building_nuclear_plant.dds"),
    ("je_space_race_widget_ch_autonomy", "page_autonomy.dds", "diplomatic_action_icons/liberty_desire.dds"),
    ("je_space_race_widget_page_status", "page_aut_status.dds", "ai_strategy_icons/subject_maintain_autonomy.dds"),
    ("je_space_race_widget_ch_defences", "module_def.dds", "building_icons/building_naval_fortification.dds"),
    ("je_space_race_widget_ch_integrity", "page_integrity.dds", "state_status_icons/has_devastation.dds"),
    ("je_space_race_widget_page_status", "page_def_status.dds", "state_status_icons/colony.dds"),
)


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
                             ('block "sr_risk_lit"', "risk"),
                             ('block "sr_risk_unlit"', "risk"),
                             ('tooltip = "sr_rivals_first_open"', "first"),
                             ('tooltip = "sr_rivals_first_claimed"', "first"),
                             ("'je_space_race_widget_ov_stage_moon'", "stage")):
            with self.subTest(cell=anchor):
                self.assertEqual(self._cell_texture(anchor), [f"{SR_ICONS}{name}.dds"])

    def test_the_first_to_finish_mark(self):
        for cell in ("te_sr_ov_prog_cell", "te_sr_ov_prog_cell_interstellar"):
            with self.subTest(cell=cell):
                mark = _enclosing(_type_body(self.gui, cell), "size = { 18 18 }", "icon = {")
                self.assertIn(f'texture = "{SR_ICONS}first_mark.dds"', mark)

    def test_colony_and_war_fleets_wear_different_icons(self):
        """Audit SPC-16: Solar System's inbound colony fleets keep the
        colonization rocket; Locations' inbound warships wear the warship."""
        site = _type_body(self.gui, "te_sr_site_row")
        loc = _type_body(self.gui, "te_sr_location_row")
        self.assertIn('texture = "gfx/interface/icons/event_icons/je_space_race_solar_colonization.dds"', site)
        self.assertEqual(re.findall(r'texture = "([^"]+)"', loc), [f"{SR_ICONS}warship.dds"])

    def test_the_pies(self):
        pie = _type_body(self.gui, "te_sr_ov_pie")
        self.assertEqual(re.findall(r'texture = "([^"]+)"', pie)[-3:],
                         [f"{SR_ICONS}pie_unclaimed.dds", f"{SR_ICONS}pie_claimed.dds", f"{SR_ICONS}pie_ours.dds"])
        self.assertEqual(pie.count("framesize = { 128 128 }\n\t\t\t\tframe = 2"), 3)

    def test_no_placeholder_left(self):
        journal = {f"gfx/interface/icons/event_icons/je_space_race_{m}.dds" for m in ALL}
        for path in re.findall(r'texture = "(gfx/interface/[^"]+)"', self.gui):
            with self.subTest(path=path):
                self.assertTrue(path.startswith(SR_ICONS) or path in journal or path in VANILLA_KEPT
                                or path in PAGE_KEPT,
                                f"placeholder left: {path}")

    def test_a_colony_page_s_own_icons(self):
        """Icon batch 8: each tile and module row on a colony's page draws its own
        icon (the caption or module name after it says which), and the placeholder
        it replaced is gone from the page."""
        page = _type_body(self.gui, "te_sr_colony_row")
        pairs, icon = [], None
        for line in page.splitlines():
            m = re.search(rf'texture = "{re.escape(SR_ICONS)}((?:page|module)_\w+\.dds)"', line)
            if m:
                icon = m.group(1)
                continue
            m = re.search(r'text = "([^"]+)"', line)
            if m and icon:
                pairs.append((m.group(1), icon))
                icon = None
        self.assertEqual(pairs, [(caption, f) for caption, f, _ in PAGE_ICONS])
        for _, f, old in PAGE_ICONS:
            with self.subTest(placeholder=old):
                self.assertNotIn(f'texture = "gfx/interface/icons/{old}"', page)

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
        cls.site_names = set(re.findall(r"(?m)^(sr_disp_\w+) = \{", _read(SITES_DISPLAY)))
        cls.site_names |= set(re.findall(r"(?m)^(sr_disp_\w+) = \{", "\n".join(_read(p) for p in FLEETS_DISPLAY)))

    def test_every_value_the_panel_reads_exists(self):
        used = set(re.findall(r"ScriptValue\('(sr_disp_\w+)'\)",
                              _read(GUI) + _read(SITES_ROWS) + _read(FLEETS_ROWS) + _read(WINDOWS_GUI)))
        for key in re.findall(r"ScriptValue\('(sr_disp_\w+)'\)",
                              "\n".join(_read(p) for p in glob.glob(os.path.join(LOC_DIR, "*.yml")))):
            used.add(key)
        self.assertTrue(used)
        self.assertEqual(used - self.names - self.site_names, set())
        self.assertEqual((self.names | self.site_names) - used, set(), "a display value nothing reads")

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
            self.assertIn("max = 3", body)

    def test_programme_codes_follow_the_tooltip_order(self):
        """first (4) → done (3) → running (1) → taken (2), as sr_prog_<m> tests.
        The Moon Base's icon is the first lunar colony's (lunar colonization
        design § 3.6): no separate bar, so no "under way" state."""
        custom = _read(CUSTOM_LOC)
        for m in RACING:
            with self.subTest(milestone=m):
                body = _block(self.values, f"sr_disp_prog_{m}")
                tests = re.findall(r"(has_(?:global_)?variable = (\w+)) \} value = (\d)", body)
                expected = [(f"sr_was_first_{m}", 4), (f"sr_completed_{m}", 3),
                            (f"sr_active_{m}", 1), (f"sr_global_first_{m}", 2)]
                if m == "moon_base":
                    expected.remove(("sr_active_moon_base", 1))
                self.assertEqual([(v, int(c)) for _, v, c in tests], expected)
                loc = _block(custom, f"sr_prog_{m}")
                order = re.findall(r"has_(?:global_)?variable = (\w+)", loc)
                self.assertEqual(order, [v for _, v, _ in tests])

    def test_no_value_is_read_by_script(self):
        for sub in ("common", "events"):
            for path in glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True):
                if any(os.path.samefile(path, p) for p in (DISPLAY, SITES_DISPLAY, *FLEETS_DISPLAY)):
                    continue
                hit = re.search(r"\bsr_disp_\w+", _strip_comments(_read(path)))
                self.assertIsNone(hit, f"{path} reads {hit and hit.group(0)}")


class PaceBreakdownTest(unittest.TestCase):
    """Hovering a headline's "+N/mo" shows where the pace comes from.

    The pace is one number for the whole country (sr_progress: the added
    progress modifier times one plus the multiplier, floored at 0.5), so one
    tooltip serves all eight milestone overviews, through the shared composer.
    The breakdown is the engine's own (GetValueWithBreakdownFor), which lists
    every modifier that feeds the two figures; nothing is re-derived by hand.
    """

    ADD = "country_space_race_progress_add"
    MULT = "country_space_race_progress_mult"

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)

    def test_the_headline_cell_carries_the_breakdown_tooltip(self):
        composer = _type_body(self.gui, "te_sr_overview_milestone")
        def override(name):
            start = composer.index(f'blockoverride "{name}" {{')
            brace = composer.index("{", start)
            return composer[brace + 1:_close(composer, brace)]

        cell = override("bar_text")
        self.assertIn('tooltip = "je_space_race_widget_pace_tt"', cell)
        self.assertIn('block "sr_progress_text" {}', cell)
        # the rest of the row keeps the reward preview: the tooltip is set on
        # the headline's own textbox, not on the row
        row = override("row_tooltip")
        self.assertNotIn("pace_tt", row)
        self.assertIn('block "sr_progress_tooltip" {}', row)

    def test_every_milestone_headline_ends_on_its_rate(self):
        for m in CONTROLLED:
            with self.subTest(milestone=m):
                text = _loc(f"je_space_race_widget_progress_{m}")
                self.assertRegex(
                    text, rf"\(\+\[JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('sr_pace_rate_{m}'\)\|1\]/mo\)$")

    def test_the_tooltip_breaks_down_both_figures_and_states_the_pace(self):
        tip = _loc("je_space_race_widget_pace_tt")
        for key in (self.ADD, self.MULT):
            self.assertIn(
                f"[JournalEntry.GetCountry.GetModifier.GetValueWithBreakdownFor('{key}')]", tip)
        self.assertLess(tip.index(self.ADD), tip.index(self.MULT))
        self.assertIn("ScriptValue('sr_progress')", tip)

    def test_both_keys_are_registered_modifier_types(self):
        # GetValueWithBreakdownFor works on modifier keys and nothing else
        types = _read(os.path.join(REPO, "common", "modifier_type_definitions", "space_race_modifier_types.txt"))
        for key in (self.ADD, self.MULT):
            self.assertRegex(types, rf"(?m)^{key} = \{{")

    def test_the_pace_shown_is_the_pace_the_pulse_applies(self):
        values = _read(os.path.join(REPO, "common", "script_values", "space_race_values.txt"))
        progress = _block(values, "sr_progress")
        self.assertIn(f"modifier:{self.ADD}", progress)
        self.assertIn(f"modifier:{self.MULT}", progress)
        self.assertIn("min = 0.5", progress)
        for m in CONTROLLED:
            self.assertEqual(_block(values, f"sr_pace_rate_{m}").split()[:3], ["value", "=", "sr_progress"])


class LocTest(unittest.TestCase):
    def test_no_panel_line_starts_or_ends_with_a_break(self):
        for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
            for key, value in re.findall(r'^ (je_space_race_widget_\w+):\d* "(.*)"\s*$', _read(path), re.M):
                with self.subTest(key=key):
                    self.assertFalse(value.startswith("\\n") or value.endswith("\\n"), key)

    def test_the_pace_sentence_is_the_state_icon_tooltip(self):
        overview = _type_body(_read(GUI), "te_sr_overview_milestone")
        for note in ("standard", "safe", "ambitious"):
            self.assertIn(f'tooltip = "sr_pace_note_{note}"', overview)
        self.assertNotRegex(_read(CUSTOM_LOC), r"(?m)^sr_\w+_pace = \{")


class QueueNextModuleTest(unittest.TestCase):
    """The queue's Next module row (the owner, 2026-10-31) follows how
    sr_mod_month builds: its loop asks the launch site, the stock against the
    head's price, a free shipment slot and the queue, never the month's rate,
    so a head the stock covers is built with no fabrication and must not read
    "stopped" (review of #1274)."""

    def test_the_build_loop_never_asks_the_rate(self):
        effects = _read(os.path.join(REPO, "common", "scripted_effects", "sr_colony_module_effects.txt"))
        loop = _block(effects, "sr_mod_month").split("while = {", 1)[1]
        start = loop.index("limit = {") + len("limit = {")
        depth, end = 1, start
        while depth:
            depth += {"{": 1, "}": -1}.get(loop[end], 0)
            end += 1
        limit = loop[start:end]
        for term in ("sr_launch_site_lost", "sr_mq_head_cost", "sr_ms_has_free_slot", "sr_mq_1_site"):
            self.assertIn(term, limit)
        self.assertNotIn("sr_mod_fab_rate", limit)

    def test_stopped_only_when_nothing_can_build(self):
        state = _block(_read(DISPLAY), "sr_disp_mq_next_state")
        lost, covered, no_rate = (state.index("sr_launch_site_lost = yes"),
                                  state.index("sr_mod_fab_stock_value >= sr_mq_head_cost"),
                                  state.index("NOT = { sr_mod_fab_rate > 0 }"))
        # The launch site first, then a covered head (built, or waiting for a
        # slot), and only then no rate: stopped.
        self.assertLess(lost, covered)
        self.assertLess(covered, no_rate)
        self.assertEqual(re.findall(r"value = (\d)", state), ["0", "1", "3", "2", "3"])


class ColonyTargetOpenerTest(unittest.TestCase):
    """Colony Fleets opens the colony target popup (UI pass design § 5): Change
    beside our target, with Clear kept; Choose on the two automatic rows."""

    OPEN = "onclick = \"[GetVariableSystem.Set('te_popup', 'sr_target')]\""

    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(_read(GUI))

    def _rows(self):
        section = _type_body(self.text, "te_sr_sec_colony_fleets")
        out = []
        for m in re.finditer(r"\bte_sr_cf_dest_row = \{", section):
            out.append(section[m.end():_close(section, m.end() - 1)])
        return out

    def test_each_destination_row_opens_the_picker(self):
        rows = self._rows()
        self.assertEqual(len(rows), 3)
        target, *automatic = rows
        self.assertIn(self.OPEN, target)
        self.assertIn('text = "je_space_race_widget_cf_change"', target)
        self.assertIn("GetScriptedGui('sr_cf_target_clear_sgui').Execute", target)
        self.assertLess(target.index("je_space_race_widget_cf_change"), target.index("sr_cf_target_clear_sgui"))
        for row in automatic:
            with self.subTest(row=row[:80]):
                self.assertIn(self.OPEN, row)
                self.assertIn('text = "je_space_race_widget_cf_choose"', row)
                self.assertNotIn("sr_cf_target_clear_sgui", row)

    def test_the_row_fits(self):
        row = _type_body(self.text, "te_sr_cf_dest_row")
        widths = [int(w) for w in re.findall(r"minimumsize = \{ (\d+) -1 \}", row)]
        self.assertEqual(len(widths), 2)            # the label and the value
        spacing = int(re.search(r"spacing = (\d+)", row).group(1))
        margin = int(re.search(r"margin = \{ (\d+) \d+ \}", row).group(1))
        # Two 66-wide buttons on the target row, the most it holds.
        self.assertLessEqual(sum(widths) + 2 * 66 + 3 * spacing + 2 * margin, 480)


if __name__ == "__main__":
    unittest.main()
