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
from gui_test_helpers import (READ, _children, assert_wide_matches_narrow, block_defaults, gui_keys, guard_spans,  # noqa: E402
                              in_spans, load_loc, loc_closure, mod_types, panel_loc_keys, panel_view,
                              type_closure, unguarded)
from scripts.generators import gen_te_systems_window as window_gen  # noqa: E402
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

RACING = ["suborbital", "orbital", "moon_landing", "probe", "mars_landing",
          "interstellar_probe"]
CONTROLLED = RACING + ["solar_colonization"]  # the seven with controls, in je_space_race.txt's order
ALL = ["suborbital", "orbital", "moon_landing", "probe", "mars_landing",
       "interstellar_probe", "interstellar_results", "solar_colonization"]  # journal order
# The retired Moon Base has no entry since vanilla 1.15 (#1407): the first lunar
# colony keeps its record, so the programme rows keep its icon and its first.
RETIRED = ["moon_base"]
FIRSTS = ["suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
          "interstellar_probe"]  # the races with a first
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
OLD_FLAGS = [f"sr_panel_rivals_{m}" for m in CONTROLLED] + \
            [f"sr_panel_programme_{m}" for m in ALL]
HOW_KEYS = ["je_space_race_widget_how_approach", "je_space_race_widget_how_funding",
            "je_space_race_widget_how_setbacks", "je_space_race_widget_how_first",
            "je_space_race_widget_how_rivals", "je_space_race_widget_how_programme",
            "je_space_race_widget_how_powers", "je_space_race_widget_how_orbit"]
IS_SHOWN_OP0 = ("ScriptedGui.IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope )"
                ".AddScope( 'op', MakeScopeValue( '(CFixedPoint)0' ) ).End )")
# The overview reads the shown Country (National Info, spec
# 2026-11-02-charts-help-national-info § 6.4); the entry's own sections still
# read the entry.
OV_SHOWN_OP0 = IS_SHOWN_OP0.replace("JournalEntry.GetCountry.MakeScope", "Country.MakeScope")


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


def _instances(section, type_name):
    """The bodies of every `type_name = { ... }` instance in a section."""
    out = []
    for m in re.finditer(rf"\b{type_name} = \{{", section):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(section[i], 0)
            i += 1
        out.append(section[m.end():i])
    return out


def _root(text, name):
    """A journal root as the journal renders it: the wrapper, and the body of the
    milestone's own type it wraps (te_sr_<m>_overview, te_sr_<m>_status), which
    the Timeline Extended window's Space Race tab instances too."""
    m = re.search(rf'name = "{name}"', text)
    assert m, f"no root {name}"
    start = text.rfind("flowcontainer = {", 0, m.start())
    brace = text.index("{", start)
    root = text[start:_close(text, brace) + 1]
    # the root holds it in te_je_country, the entry's Country (test_te_system_tab_bodies.py)
    for wrapped in re.findall(r"^\t\t(te_sr_\w+_(?:overview|status)) = \{\}$", root, re.M):
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
    for m in sorted(ALL + RETIRED, key=len, reverse=True):
        pat = rf"(?<=[_'/]){m}(?![a-z])"
        if re.search(pat, text):
            found.add(m)
            text = re.sub(pat, "", text)
    return found


class OrderTest(unittest.TestCase):
    def test_status_order(self):
        gui = _read(GUI)
        for composer, expected in (("te_sr_status_sections", STATUS),):
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
        as the UN entry attaches them. How the Space Race Works, once a
        reference root in 3, is the Help page the overview's "?" opens."""
        je = _read(JE)
        for m in ALL:
            with self.subTest(milestone=m):
                entry = _block(je, f"je_space_race_{m}")
                widgets = re.findall(r'name = "(\w+)"\s*container = "(\w+)"', entry)
                expected = [(f"widget_je_space_race_{m}_overview", "custom_widget_container_1")]
                if m in CONTROLLED:
                    expected.append((f"widget_je_space_race_{m}", "custom_widget_container_2"))
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
        self.assertNotIn("widget_je_space_race_reference", self.gui + _read(JE))
        self.assertEqual(set(names), expected)
        self.assertEqual(len(names), len(expected))
        for name in names:
            head = _root(self.gui, name).split("\n\n")[0]  # the root's own properties
            self.assertIn('visible = "[JournalEntry.IsActive]"', head, name)
            # round 2: fixed-width roots, never content-sized wrappers centred in the panel
            self.assertIn("minimumsize = { 520 -1 }", head, name)

    def test_composers_and_number_columns_are_fixed_width(self):
        for composer in ("te_sr_overview_milestone", "te_sr_overview_transit",
                         "te_sr_status_sections"):
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
        # Autonomy and Colony Defences showed); the Space Race tab's Space
        # Powers and Orbit; and under Full Colonies Space Command, Space Fleets
        # and Locations (slice 6); and the colony target popup's "show all"
        # (UI pass design § 5); and the colonies another country holds
        # (National Info, te_sr_sec_colonies_brief). How the Space Race Works
        # and How Solar Colonization Works have none: they are the Help page.
        self.assertEqual(len(flags), 2 * len(CONTROLLED) + 11)
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

    def test_live_sections_open_and_how_it_works_the_help_page(self):
        for m in CONTROLLED:
            root = _root(self.text, f"widget_je_space_race_{m}")
            self.assertIn(f"'sr_panel_control_{m}_closed'", root)
            self.assertIn(f"'sr_panel_rivals_{m}_closed'", root)
        self.assertIn("Toggle('sr_panel_colonies_closed')", _type_body(self.text, "te_sr_sec_colonies"))
        # How the Space Race Works and How Solar Colonization Works are the
        # Help page alone (te_space_race_help_popup, on te_popup =
        # help_space_race), which the "?" on each overview and in the tab's
        # header opens: both link sections and the reference composer are gone
        # (test_te_help_pages.py)
        for gone in ("te_sr_sec_how", "te_sr_reference_sections", "sr_panel_how_open", "sr_panel_how_colonies_open"):
            self.assertNotIn(gone, self.text, gone)

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
        self.assertEqual(body.count(f'visible = "[{OV_SHOWN_OP0}]"'), 2)
        self.assertEqual(body.count(f'visible = "[Not( {OV_SHOWN_OP0} )]"'), 1)  # row 1 while idle
        self.assertNotIn("JournalEntry", body)

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
        self.assertEqual(gate, [f"[{OV_SHOWN_OP0}]", f"[Not( {OV_SHOWN_OP0} )]"])
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
            self.assertIn(f"LessThanOrEqualTo_CFixedPoint( Country.MakeScope.{sv}, '(CFixedPoint)1' )", root)
            for code in (2, 3):
                self.assertIn(f"EqualTo_CFixedPoint( Country.MakeScope.{sv}, '(CFixedPoint){code}' )", root)
            # Code 4, shielded, went with the post-setback cooldown (2026-10-31).
            self.assertNotIn(f"EqualTo_CFixedPoint( Country.MakeScope.{sv}, '(CFixedPoint)4' )", root)
            risk = f"ScriptValue('sr_risk_shown_{m}')"
            self.assertIn(f"NotEqualTo_CFixedPoint( Country.MakeScope.{risk}, '(CFixedPoint)0' )", root)
            self.assertIn(f"[EqualTo_CFixedPoint( Country.MakeScope.{risk}, '(CFixedPoint)0' )]", root)


def _colony_sites():
    """[(event number, [the two specializations it grants])] in event order."""
    text = _read(COLONY_EVENTS)
    parts = re.split(r"\n(space_race_colony_events\.(\d+)) = \{", text)
    return [(int(parts[i + 1]), re.findall(r"sr_site_choose_(\w+) = yes", parts[i + 2]))
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
        System (moved down by the owner, 2026-10-31); the old per-aspect
        sections are gone (SPC-5), and How Solar Colonization Works is the
        Help page."""
        status = _type_body(self.gui, "te_sr_solar_colonization_status")
        self.assertIn("direction = vertical", status.split("\n\n")[0])
        # Across the tabs (UI pass design § 11), Mission Control's own launch
        # windows aside.
        self.assertEqual([s for s in re.findall(r"^\t+(te_sr_sec_\w+) = \{\}", status, re.M) if s != "te_sr_sec_windows"],
                         ["te_sr_sec_colony_fleets", "te_sr_sec_space_command", "te_sr_sec_space_fleets",
                          "te_sr_sec_colonies", "te_sr_sec_solar_system"])
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
        stage = "GreaterThanOrEqualTo_CFixedPoint( Country.MakeScope.ScriptValue('sr_current_colonization_stage'), '(CFixedPoint)1' )"
        waits = "EqualTo_CFixedPoint( Country.MakeScope.ScriptValue('sr_disp_held_beyond_moon'), '(CFixedPoint)1' )"
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
        how = _type_body(gui, "te_space_race_help_body")
        for key in HOW_KEYS:
            self.assertIn(f'"{key}"', how, key)
        # audit SPC-4: the colony sections' rules are How Solar Colonization
        # Works, on the same Help page under that name, after the Space Race's
        # own topics, which the "?" opens from every host. The rule's
        # topics are gated on the player, not an entry (test_te_help_pages.py).
        at = how.index('text = "je_space_race_widget_howc_header"')
        self.assertGreater(at, how.index(f'"{HOW_KEYS[-1]}"'))
        how_colonies = how[at:]
        for topic in ("fleets", "windows", "settlers", "modules", "autonomy", "space_command", "defences"):
            self.assertIn(f'"je_space_race_widget_howc_{topic}"', how_colonies, topic)
        for rule, n in (("sr_disp_colonies_contested", 6), ("sr_disp_colonies_full", 4)):
            self.assertEqual(how_colonies.count(f"GetPlayer.MakeScope.ScriptValue('{rule}')"), n, rule)
        for sec in ("te_sr_sec_control", "te_sr_sec_rivals", "te_sr_overview_milestone",
                    "te_sr_overview_transit", "te_sr_sec_colonies", "te_sr_sec_colony_fleets",
                    "te_sr_sec_solar_system", "te_sr_sec_space_command", "te_sr_sec_space_fleets",
                    "te_sr_colony_row", "te_sr_solar_colonization_overview"):
            body = _type_body(gui, sec)
            self.assertNotIn("te_sr_note", body, f"{sec} carries an explanation")
            for key in HOW_KEYS:
                self.assertNotIn(key, body, sec)

    def test_each_colony_topic_shows_under_its_rule(self):
        """Each Solar Colonization topic's heading and note carry its own
        colonies rule (or none), read on the player: swapping two topics'
        gates keeps the counts above but fails here."""
        rules = {"fleets": None, "windows": None, "settlers": "sr_disp_colonies_contested",
                 "modules": "sr_disp_colonies_contested", "autonomy": "sr_disp_colonies_contested",
                 "space_command": "sr_disp_colonies_full", "defences": "sr_disp_colonies_full"}
        how = _strip_comments(_type_body(_read(GUI), "te_space_race_help_body"))
        gates = {}
        for kind, name, inner in _children(how):
            m = re.search(r'text = "je_space_race_widget_howc_(\w+)"', inner) if kind == "widget" else None
            if m and m.group(1) != "header":
                gate = re.search(r'visible = "(.*)"', inner)
                gates[m.group(1)] = gate.group(1) if gate else None
        expected = {}
        for topic, rule in rules.items():
            shown = None if rule is None else f"[EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('{rule}'), '(CFixedPoint)1' )]"
            expected[f"sub_{topic}"] = expected[topic] = shown
        self.assertEqual(gates, expected)

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
                # the player's words, or a neutral twin for another country
                # (I3); solar colonization's says nothing of who was first
                m = re.search(r"tooltip = \"\[SelectLocalization\( Country\.IsLocalPlayer, "
                              r"'je_space_race_widget_prog_(\w+)', 'je_space_race_widget_prog_\1_ni' \)\]\"", cell)
                m = m or re.search(r'tooltip = "je_space_race_widget_prog_(solar_colonization)"', cell)
                names.append(m.group(1))
        self.assertEqual(names, ROW)
        for m, cell in zip(names, cells):
            if m == "interstellar":
                continue
            with self.subTest(milestone=m):
                self.assertIn(f'texture = "gfx/interface/icons/event_icons/je_space_race_{m}.dds"', cell)
                self.assertEqual(_milestones_named(cell), {m})
                self.assertIn(f"ScriptValue('sr_disp_prog_{m}')", cell)
                self.assertEqual('blockoverride "first"' in cell, m in FIRSTS)

    def test_the_row_fits_the_column(self):
        cell = re.search(r"size = \{ (\d+) \d+ \}", _type_body(_read(GUI), "te_sr_ov_prog_cell")).group(1)
        spacing = re.search(r"direction = horizontal\s+spacing = (\d+)",
                            _type_body(_read(GUI), "te_sr_ov_programme")).group(1)
        self.assertLessEqual(len(ROW) * int(cell) + (len(ROW) - 1) * int(spacing), 480)

    def test_the_textures_exist(self):
        tracked = subprocess.run(["git", "-C", REPO, "ls-files", "gfx/interface/icons/event_icons/"],
                                 capture_output=True, text=True, check=True).stdout.split()
        for m in ALL + RETIRED:
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
                m = re.fullmatch(r"\[EqualTo_CFixedPoint\( Country\.MakeScope\."
                                 r"ScriptValue\('sr_disp_prog_interstellar'\), '\(CFixedPoint\)(\d)' \)\]",
                                 visibles[0])
                self.assertIsNotNone(m, visibles[0])
                codes.append(int(m.group(1)))
                self.assertIn(f"tooltip = \"[SelectLocalization( Country.IsLocalPlayer, "
                              f"'je_space_race_widget_prog_interstellar_{n}', "
                              f"'je_space_race_widget_prog_interstellar_{n}_ni' )]\"", icon)
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



# The furthest milestone a Space Powers row estimates, by code (sr_power_lead_code):
# je_space_race.txt's order, 5 (the retired Moon Base, #1407) unused.
LEAD = {1: "suborbital", 2: "orbital", 3: "moon_landing", 4: "probe", 6: "mars_landing",
        7: "interstellar_probe", 8: "solar_colonization"}
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
        # The shown country's row reads Country (National Info); its exact
        # progress column is the player's own.
        self.assertIn('datacontext = "[Country.GetCapital]"', rows[0])
        self.assertRegex(rows[0], r"te_sr_power_lead_own = \{\s*using = te_own_country_only\s*\}")
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
        for m in LEAD.values():
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
        self.assertIn("remove_variable = sr_power_total }", clear)
        # the eight slots from before SPC-9 went with vanilla 1.15 (#1407)
        for n in range(1, 9):
            self.assertNotRegex(effects, rf"\bsr_power_{n}\b")
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
                                 + [(str(c), prefix + m) for c, m in LEAD.items()])
        own = _type_body(self.gui, "te_sr_power_lead_own")
        for m in LEAD.values():
            self.assertIn(f"ScriptValue('sr_disp_progress_frac_{m}')", _loc(f"je_space_race_widget_power_own_{m}"))
            band = _loc(f"je_space_race_widget_power_lead_{m}")
            for end in ("lo", "hi"):
                self.assertIn(f"AddScope( 'sr_rival', State.GetCountry.MakeScope ).ScriptValue('sr_disp_rival_{end}_{m}')", band)
        self.assertNotIn("sr_disp_rival", own)

    def test_the_lead_code_follows_the_journal_order(self):
        body = _strip_comments(_block(_read(VALUES), "sr_power_lead_code"))
        found = re.findall(r"limit = \{ (?:has_variable = sr_active_(\w+)|sr_(solar_colonization)_running = yes) \} value = (\d)", body)
        self.assertEqual([(a or b, int(c)) for a, b, c in found],
                         list(reversed([(m, c) for c, m in LEAD.items()])))

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
                self.assertEqual('blockoverride "first"' in cell, m in FIRSTS)
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
        self.assertEqual(re.findall(r'text = "(?:\[SelectLocalization\( Country\.IsLocalPlayer, \')?'
                                    r'(je_space_race_widget_orbit_\w+_label)', body),
                         [f"je_space_race_widget_orbit_{r}_label" for r in ("satellites", "strikes", "moratorium", "strike")])
        # "Our Satellites" is the player's; another country's reads "Satellites" (I3)
        self.assertIn("text = \"[SelectLocalization( Country.IsLocalPlayer, 'je_space_race_widget_orbit_satellites_label', "
                      "'je_space_race_widget_orbit_satellites_ni_label' )]\"", body)
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
        any journal entry: every key it renders roots on the shown Country,
        which every mount supplies (gotcha #45), so National Info shows another
        country's."""
        for key in ("te_debris_row", "te_debris_row_tt", "te_debris_row_tt_cleaners",
                    "te_debris_row_tt_hazardous", "te_debris_row_tt_kessler"):
            with self.subTest(key=key):
                self.assertNotIn("JournalEntry", _loc(key))
                self.assertNotIn("GetPlayer", _loc(key))
                self.assertIn("Country.", _loc(key))

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
        for anchor, name in (("je_space_race_widget_ov_idle_tt', 'je_space_race_widget_ov_idle_tt_ni' )]\"", "state_idle"),
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
        journal = {f"gfx/interface/icons/event_icons/je_space_race_{m}.dds" for m in ALL + RETIRED}
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
                    text, rf"\(\+\[Country\.MakeScope\.ScriptValue\('sr_pace_rate_{m}'\)\|1\]/mo\)$")

    def test_the_tooltip_breaks_down_both_figures_and_states_the_pace(self):
        tip = _loc("je_space_race_widget_pace_tt")
        for key in (self.ADD, self.MULT):
            self.assertIn(
                f"[Country.GetModifier.GetValueWithBreakdownFor('{key}')]", tip)
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

class TabTest(unittest.TestCase):
    """The colonization status's tabs (UI pass design § 11): a row of four
    buttons on the client-side sr_tab (absent for Mission Control), and one
    wrapper per tab around its sections, inside te_sr_solar_colonization_status
    so both hosts draw them."""

    TABS = (("mission", "[Not( GetVariableSystem.Exists('sr_tab') )]", ["te_sr_status_sections"]),
            ("fleets", "[GetVariableSystem.HasValue('sr_tab', 'fleets')]",
             ["te_sr_sec_colony_fleets", "te_sr_sec_space_command", "te_sr_sec_space_fleets"]),
            ("colonies", "[GetVariableSystem.HasValue('sr_tab', 'colonies')]", ["te_sr_sec_colonies"]),
            ("system", "[GetVariableSystem.HasValue('sr_tab', 'system')]", ["te_sr_sec_solar_system"]))

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.status = _type_body(cls.gui, "te_sr_solar_colonization_status")

    def _wrapper(self, visible):
        i = self.status.index(f'visible = "{visible}"')
        opener = self.status.rindex("flowcontainer = {", 0, i)
        depth, j = 0, opener + len("flowcontainer = ")
        while True:
            depth += {"{": 1, "}": -1}.get(self.status[j], 0)
            if depth == 0:
                return self.status[opener:j]
            j += 1

    def test_each_tab_holds_its_sections(self):
        starts = []
        for key, visible, sections in self.TABS:
            with self.subTest(tab=key):
                body = self._wrapper(visible)
                found = [x for x in re.findall(r"^\t+(te_sr_sec_\w+|te_sr_status_sections) = \{", body, re.M)
                         if x != "te_sr_sec_windows"]
                self.assertEqual(found, sections)
                starts.append(self.status.index(body))
        self.assertEqual(starts, sorted(starts), "the tabs' wrappers are out of order")
        # Every section sits in a tab: none left at the status's own level.
        self.assertEqual(re.findall(r"^\t\t(te_sr_sec_\w+|te_sr_status_sections) = \{", self.status, re.M), [])

    def test_each_wrapper_has_one_visible(self):
        """A second visible on a widget overrides the first (gui gotcha #17)."""
        for key, visible, _ in self.TABS:
            with self.subTest(tab=key):
                body = self._wrapper(visible)
                own = re.search(rf'(?m)^(\t*)visible = "{re.escape(visible)}"', body).group(1)
                self.assertEqual(len(re.findall(rf"(?m)^{own}visible = ", body)), 1)

    def test_the_default_tab_is_mission_control(self):
        first = re.search(r'flowcontainer = \{\s*visible = "([^"]+)"\s*direction = vertical', self.status)
        self.assertEqual(first.group(1), "[Not( GetVariableSystem.Exists('sr_tab') )]")

    def test_each_button_sets_its_tab_and_greys_on_it(self):
        row = self.status[:self.status.index(self._wrapper(self.TABS[0][1]))]
        buttons = _instances(row, r"te_sr_tab_button(?:_wide)?")
        self.assertEqual(len(buttons), 4)
        # Mission Control and Solar System need the wide button (the labels
        # test measures each type, not the instance that uses it).
        types = re.findall(r"\b(te_sr_tab_button(?:_wide)?) = \{", row)
        wants = (("mission", "GetVariableSystem.Exists('sr_tab')", "[GetVariableSystem.Clear('sr_tab')]", "te_sr_tab_button_wide"),
                 ("fleets", "Not( GetVariableSystem.HasValue('sr_tab', 'fleets') )", "[GetVariableSystem.Set('sr_tab', 'fleets')]", "te_sr_tab_button"),
                 ("colonies", "Not( GetVariableSystem.HasValue('sr_tab', 'colonies') )", "[GetVariableSystem.Set('sr_tab', 'colonies')]", "te_sr_tab_button"),
                 ("system", "Not( GetVariableSystem.HasValue('sr_tab', 'system') )", "[GetVariableSystem.Set('sr_tab', 'system')]", "te_sr_tab_button_wide"))
        self.assertEqual(types, [w[3] for w in wants])
        for button, (key, enabled, onclick, _) in zip(buttons, wants):
            with self.subTest(tab=key):
                self.assertIn(f'enabled = "[{enabled}]"', button)
                self.assertIn(f'onclick = "{onclick}"', button)
                self.assertIn(f'text = "je_space_race_widget_tab_{key}"', button)
                self.assertIn(f'tooltip = "je_space_race_widget_tab_{key}_tt"', button)
        # Set and Clear, never Toggle (FlagTest counts Toggle's flags).
        self.assertNotIn("Toggle('sr_tab')", self.gui)

    def test_the_tab_row_shows_while_the_entry_runs(self):
        row = self.status[:self.status.index(self._wrapper(self.TABS[0][1]))]
        m = re.search(r'flowcontainer = \{\s*direction = horizontal\s*parentanchor = hcenter\s*spacing = 4\s*visible = "([^"]+)"', row)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "[JournalEntry.IsActive]")
        # Four buttons in the panel's 520: two of 96, two of 148, three gaps.
        widths = {t: int(re.search(r"size = \{ (\d+) 28 \}", _type_body(self.gui, t)).group(1))
                  for t in ("te_sr_tab_button", "te_sr_tab_button_wide")}
        used = [widths["te_sr_tab_button_wide" if "_wide = {" in m.group(0) else "te_sr_tab_button"]
                for m in re.finditer(r"\bte_sr_tab_button(?:_wide)? = \{", row)]
        self.assertLessEqual(sum(used) + 4 * (len(used) - 1), 520)

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

class EarthAlertCellTest(unittest.TestCase):
    """The overview's Hostile Fleet cell (UI pass design § 9): under Full
    Colonies, while a hostile fleet is bound for Earth; red on 2."""

    def test_the_cell_reads_the_alert_values(self):
        gui = _read(GUI)
        m = re.search(r'te_banking_ov_cell = \{\s*visible = "([^"]+)"\s*tooltip = "je_space_race_widget_ovc_earth_tt"', gui)
        self.assertIsNotNone(m, "no Hostile Fleet cell")
        shows = ("ScriptValue('sr_disp_colonies_full'), '(CFixedPoint)1'",
                 "GreaterThanOrEqualTo_CFixedPoint( Country.MakeScope.ScriptValue('sr_disp_earth_hostile'), "
                 "'(CFixedPoint)1' )")
        # Shown by its own visible, and its row (shared with Base Room) shows
        # while either cell does.
        row = gui.rindex("flowcontainer = {", 0, m.start())
        row_shown = re.match(r'flowcontainer = \{\s*visible = "([^"]+)"', gui[row:]).group(1)
        self.assertTrue(row_shown.startswith("[Or( "), row_shown)
        for cond in shows:
            self.assertIn(cond, m.group(1))
            self.assertIn(cond, row_shown)
        self.assertIn("ScriptValue('sr_disp_ebase_shown')", row_shown)
        brace = gui.index("{", m.start())
        depth, i = 0, brace
        while True:
            depth += {"{": 1, "}": -1}.get(gui[i], 0)
            if depth == 0:
                break
            i += 1
        cell = gui[brace:i]
        loud = "EqualTo_CFixedPoint( Country.MakeScope.ScriptValue('sr_disp_earth_hostile'), '(CFixedPoint)2' )"
        self.assertRegex(cell, rf'visible = "\[{re.escape(loud)}\]"\s*text = "je_space_race_widget_ovc_earth_word_loud"')
        self.assertRegex(cell, rf'visible = "\[Not\( {re.escape(loud)} \)\]"\s*text = "je_space_race_widget_ovc_earth_word"')
        self.assertIn('text = "je_space_race_widget_ovc_earth_fig"', cell)
        loc = "\n".join(_read(p) for p in glob.glob(os.path.join(LOC_DIR, "*.yml")))
        self.assertRegex(loc, r'(?m)^ je_space_race_widget_ovc_earth_word_loud:0 "#R ')


class PrivateTest(unittest.TestCase):
    """What another country's Space Race tab leaves out, and what it keeps
    (National Info; spec 2026-11-02-charts-help-national-info §§ 6.4, 6.7).
    Left out, under te_own_country_only: each milestone's live sections
    (Mission Control's approach, funding and setbacks, the Rivals, the colony
    fleets and Space Command) and Open Journal Entry, which read the player's
    entry; the overview's approach and setback-risk cells and its exact
    progress bar; solar colonization's staging and "what needs us" cells; the
    exact-progress column of the country's own Space Powers row; the other
    powers' rows, which are the viewer's list and the viewer's estimates; and
    the strike readiness row, the player's own case for a strike. What another
    country's panel draws is the walk test_te_system_tab_bodies.py's
    BindingTest makes (panel_view)."""

    ROOT = {"te_sr_wide_sections"}
    PRIVATE = ("te_sr_sec_control", "te_sr_sec_rivals", "te_sr_rival_row", "te_sr_status_sections",
               "te_sr_power_lead_own", "te_sr_power_lead_band", "te_sr_ov_staged", "te_sr_sec_colonies",
               "te_sr_sec_colony_fleets", "te_sr_sec_space_command", "te_sr_sec_space_fleets",
               "te_sr_sec_solar_system", "te_sr_action_button") + tuple(f"te_sr_{m}_status" for m in CONTROLLED)

    @classmethod
    def setUpClass(cls):
        cls.types = mod_types()
        cls.view = panel_view(cls.ROOT, cls.types)
        cls.loc = load_loc()
        cls.keys = panel_loc_keys(cls.ROOT, cls.types, cls.loc)

    def _hidden(self, type_name, anchor):
        """Whether the anchor's end (inside a widget it opens) is left out."""
        body = self.types[type_name].body
        self.assertIn(anchor, body, type_name)
        return in_spans(body.index(anchor) + len(anchor), self.view.skip[type_name])

    def test_the_players_own_parts_are_left_out(self):
        drawn = type_closure(self.ROOT, self.types)
        for name in self.PRIVATE:
            with self.subTest(type=name):
                self.assertIn(name, drawn, "the player's own panel still draws it")
                self.assertNotIn(name, self.view.open, f"another country's panel draws {name}")

    def test_the_entrys_sections_and_link_are_the_players(self):
        body = self.types["te_sr_window_milestones"].body
        spans = self.view.skip["te_sr_window_milestones"]
        # the guards, and the live sections full screen moves to a column of
        # their own (the frame's emptied block), which sit inside a guard
        guards = guard_spans(body)
        moved = [(a, b) for a, b, x in block_defaults(body)
                 if x in {f"sr_window_{m}_live" for m in window_gen.SR_OWN_COLUMN}]
        self.assertEqual(len(moved), len(window_gen.SR_OWN_COLUMN))
        self.assertEqual(sorted(spans), sorted(guards + moved))
        for a, _ in moved:
            self.assertTrue(in_spans(a, guards), "a moved block outside the player's own part")
        frames = [m.start() for m in re.finditer(r"\bte_system_tab_frame = \{", body)] + [len(body)]
        self.assertEqual(len(frames) - 1, len(ALL))
        for m, start, end in zip(ALL, frames, frames[1:]):
            with self.subTest(milestone=m):
                frame = body[start:end]
                self.assertIn('blockoverride "tab_country" {}', frame)
                entry = start + frame.index(f"GetPlayerJournalEntry('je_space_race_{m}')")
                self.assertTrue(in_spans(entry, spans), "the entry's datacontext outside the guard")
                self.assertTrue(in_spans(start + frame.index("OpenJournalEntryPanel"), spans))
                overview = "te_sr_overview_transit = {}" if m in window_gen.SR_TRANSIT else f"te_sr_{m}_overview = {{}}"
                self.assertFalse(in_spans(start + frame.index(overview), spans), "the overview is the player's")

    def test_the_overviews_private_cells_are_the_players(self):
        for anchor in ('block "sr_status_standard"', 'block "sr_risk_lit"', "te_sr_ov_bar_row = {"):
            with self.subTest(anchor=anchor):
                self.assertTrue(self._hidden("te_sr_overview_milestone", anchor))
        for anchor in ('block "sr_third_cells"', "te_sr_ov_band_row = {", "te_sr_ov_programme = {}"):
            with self.subTest(anchor=anchor):
                self.assertFalse(self._hidden("te_sr_overview_milestone", anchor))
        # the band shows only for another country, the bar only for the player:
        # one of the two whenever the row shows
        body = self.types["te_sr_overview_milestone"].body
        band = body[body.index("te_sr_ov_band_row = {"):]
        self.assertEqual(re.search(r'visible = "(.*)"', band).group(1), "[Not( Country.IsLocalPlayer )]")
        solar = "te_sr_solar_colonization_overview"
        for anchor in ("te_sr_ov_staged = {", 'tooltip = "je_space_race_widget_ovc_colonies_tt"',
                       'tooltip = "je_space_race_widget_ovc_earth_tt"'):
            with self.subTest(anchor=anchor):
                self.assertTrue(self._hidden(solar, anchor))
        self.assertFalse(self._hidden(solar, "te_sr_ov_pie = {"))

    def test_the_other_powers_are_the_players(self):
        for anchor in ("GetList('sr_powers_list')", '"je_space_race_widget_powers_others"',
                       "te_sr_power_lead_own = {"):
            with self.subTest(anchor=anchor):
                self.assertTrue(self._hidden("te_sr_sec_powers", anchor))
        self.assertFalse(self._hidden("te_sr_sec_powers", 'datacontext = "[Country.GetCapital]"'))
        self.assertTrue(self._hidden("te_sr_sec_orbit", 'tooltip = "te_orbit_strike_tt"'))
        self.assertFalse(self._hidden("te_sr_sec_orbit", "te_sr_debris_row = {}"))

    def test_no_empty_row_for_another_country(self):
        """A guarded part whose own row has a visible sits in a wrapper that
        also asks Country.IsLocalPlayer, so another country's column keeps no
        empty row (spacing) where it would be."""
        solar = self.types["te_sr_solar_colonization_overview"].body
        for value, inner in (("sr_launch_staged_shown", "te_sr_ov_staged"),
                             ("sr_disp_colonies_contested", "flowcontainer")):
            with self.subTest(part=inner):
                self.assertRegex(solar, rf'flowcontainer = \{{\s*visible = "\[And\( Country\.IsLocalPlayer, [^"]*'
                                        rf"ScriptValue\('{value}'\)[^\"]*\]\"[^{{}}]*{inner} = \{{\s*"
                                        r"using = te_own_country_only")

    # The other half (spec § 6.4's Shown column: "milestones reached, program
    # icons, colonies and a progress band"): what another country's panel
    # still draws, so a guard that hides too much fails too. A type whose root
    # carries the guard is in view.open but draws nothing, so each must also
    # keep its root out of view.skip.
    SHOWN = ("te_sr_window_milestones", "te_sr_overview_milestone", "te_sr_overview_transit", "te_sr_ov_first",
             "te_sr_ov_icon_label", "te_sr_ov_band_row", "te_sr_ov_pie", "te_sr_ov_programme", "te_sr_ov_prog_cell",
             "te_sr_ov_prog_cell_interstellar", "te_sr_sec_powers", "te_sr_power_row", "te_sr_power_cell",
             "te_sr_power_cell_interstellar", "te_sr_sec_orbit", "te_sr_debris_row", "te_sr_sec_colonies_brief",
             "te_sr_colony_brief_rows", "te_sr_colony_brief_row", "te_sr_value_row", "te_sr_panel") \
        + tuple(f"te_sr_{m}_overview" for m in CONTROLLED)

    def test_another_country_sees_its_milestones_program_colonies_and_band(self):
        for name in self.SHOWN:
            with self.subTest(type=name):
                self.assertIn(name, self.view.open, f"another country's panel doesn't draw {name}")
                body = self.types[name].body
                self.assertNotIn((0, len(body)), self.view.skip[name], f"{name}'s root is the player's own")
        shown = [f"je_space_race_widget_band_{m}" for m in CONTROLLED] + ["je_space_race_widget_band_tt"]
        shown += [f"je_space_race_widget_power_prog_{m}" for m in CONTROLLED if m != "interstellar_probe"]
        shown += ["je_space_race_widget_power_prog_interstellar", "je_space_race_widget_ov_first_claimed",
                  "je_space_race_widget_ov_first_open", "je_space_race_widget_ov_programme_tt_ni",
                  "je_space_race_widget_ov_idle", "je_space_race_widget_ov_idle_tt_ni", "je_space_race_widget_ov_stage",
                  "je_space_race_widget_ov_worlds_tt_theirs", "te_window_space_race_idle_note_theirs",
                  "je_space_race_widget_colonies_header", "je_space_race_widget_colonies_held_label",
                  "je_space_race_widget_colonies_held_figure", "je_space_race_widget_colonies_brief_empty",
                  "je_space_race_widget_orbit_satellites_ni_label", "je_space_race_widget_orbit_strikes_label",
                  "je_space_race_widget_orbit_moratorium_label", "te_debris_row", "te_debris_row_tt",
                  "te_debris_row_tt_cleaners_ni", "te_orbit_satellites_tt_ni", "te_orbit_strikes_tt",
                  "te_orbit_moratorium_tt_ni", "je_space_race_widget_profile_solar_colonization_ni"]
        shown += [f"te_orbit_satellites_tt_{w}_ni" for w in ("disrupted", "cooldown", "exposed", "none")]
        shown += [f"je_space_race_widget_prog_{m}_ni" for m in ROW if m not in ("interstellar", "solar_colonization")]
        shown += ["je_space_race_widget_prog_solar_colonization"]
        shown += [f"je_space_race_widget_prog_interstellar_{n}_ni" for n in range(4)]
        self.assertEqual([k for k in shown if k not in self.keys], [], "another country's panel doesn't render these")
        # and the player's own words, which it doesn't: the rewards (what
        # winning would earn us), and the keys whose "we"/"our" the player
        # keeps while another country reads the _ni twin (I3)
        mine = ["je_space_race_widget_ov_worlds_tt_ours", "te_window_space_race_idle_note_ours",
                "je_space_race_widget_ov_risk_tt", "je_space_race_widget_pace_tt",
                "je_space_race_widget_powers_others", "te_orbit_strike_tt"]
        mine += [f"je_space_race_widget_reward_{m}" for m in RACING]
        mine += [k[:-len("_ni")] for k in shown if k.endswith("_ni")]
        mine += ["je_space_race_widget_orbit_satellites_label"]
        # what an overview passes to the guarded cells and bar row through a
        # blockoverride (the exact progress, the risk, the approach's cost):
        # the walk follows the override to its block (#1368)
        mine += [f"je_space_race_widget_{part}_{m}" for m in CONTROLLED
                 for part in ("progress", "risk", "ov_safe", "ov_ambitious")]
        for key in mine:
            with self.subTest(key=key):
                self.assertNotIn(key, self.keys)

    # Another country's progress is the estimate, never the exact figure, and
    # nothing of its plans (spec § 6.4; review of #1367, I4). The band's three
    # values and its text read only the open band, sr_disp_rival_* with the
    # country as viewer and rival; and the parts another country sees (the
    # band row, the Program row, the first-to-finish cell, the country's own
    # Space Powers row, Orbit and the colonies brief, with what the overviews
    # pass into them) read none of the player's own figures. Both branches of
    # a SelectLocalization on Country.IsLocalPlayer count: the parts are
    # shared, and the player's exact figure has its own row, the bar.
    EXACT = re.compile(r"^(sr_progress_\w+|sr_disp_progress_frac_(?!interstellar_results$)\w+|sr_pace_rate_\w+"
                       r"|sr_risk_shown_\w+|sr_disp_status_\w+|sr_funding_\w+|sr_disp_cost_\w+|sr_launch_staged_\w+)$")
    SHARED = ("te_sr_ov_band_row", "te_sr_ov_programme", "te_sr_ov_first", "te_sr_power_row", "te_sr_sec_orbit",
              "te_sr_sec_colonies_brief")
    FED = ("sr_third_cells", "sr_band_text", "sr_band_lo", "sr_band_hi", "sr_band_est")  # overviews' blockoverrides

    @staticmethod
    def _overrides(body, name):
        return [body[m.end() - 1:_close(body, m.end() - 1) + 1]
                for m in re.finditer(rf'blockoverride "{name}" \{{', body)]

    def test_the_band_is_the_estimate(self):
        gui = _read(GUI)
        for m in CONTROLLED:
            body = _type_body(gui, f"te_sr_{m}_overview")
            for part in ("lo", "hi", "est"):
                with self.subTest(milestone=m, value=part):
                    got = [re.sub(r"\s+", " ", o) for o in self._overrides(body, f"sr_band_{part}")]
                    self.assertEqual(got, ["{ value = \"[FixedPointToFloat( GuiScope.SetRoot( Country.MakeScope )."
                                           f"AddScope( 'sr_rival', Country.MakeScope ).ScriptValue('sr_disp_rival_{part}_{m}')"
                                           " )]\" }"])
            with self.subTest(milestone=m, value="text"):
                self.assertEqual([re.sub(r"\s+", " ", o) for o in self._overrides(body, "sr_band_text")],
                                 [f'{{ text = "je_space_race_widget_band_{m}" }}'])
                band = self.loc[f"je_space_race_widget_band_{m}"]
                self.assertEqual(re.findall(r"'(\w+)'", band), ["sr_rival", f"sr_disp_rival_lo_{m}",
                                                                "sr_rival", f"sr_disp_rival_hi_{m}"])
                self.assertEqual(band.count("GuiScope.SetRoot( Country.MakeScope ).AddScope( 'sr_rival', "
                                            "Country.MakeScope )"), 2)
        # the band's hover reads nothing but the band
        for key in loc_closure({"je_space_race_widget_band_tt"}, self.loc):
            with self.subTest(hover=key):
                self.assertEqual([n for n in re.findall(r"'(\w+)'", self.loc[key])
                                  if n != "sr_rival" and not n.startswith("sr_disp_rival_")], [])
        self.assertIn('tooltip = "je_space_race_widget_band_tt"', self.types["te_sr_ov_band_row"].body)

    def test_the_shared_parts_read_no_exact_figure(self):
        drawn = sorted(t for t in type_closure(self.SHARED, self.types) if t in self.view.open)
        texts = {t: unguarded(self.types[t].body, self.view.skip[t]) for t in drawn}
        gui = _read(GUI)
        for m in CONTROLLED:
            body = _type_body(gui, f"te_sr_{m}_overview")
            for name in self.FED:
                for n, text in enumerate(self._overrides(body, name)):
                    texts[f"te_sr_{m}_overview {name} {n}"] = unguarded(text)
        keys = set()
        for text in texts.values():
            keys |= gui_keys(text, self.loc)
        keys = loc_closure(keys, self.loc)
        found = [(where, n) for where, text in sorted(texts.items()) for n in re.findall(r"'([\w.\-]+)'", text)
                 if self.EXACT.match(n)]
        found += [(k, n) for k in sorted(keys) for n in re.findall(r"'([\w.\-]+)'", self.loc[k]) if self.EXACT.match(n)]
        self.assertEqual(found, [], "an exact figure or the player's plans in a part another country sees")
        # what the walk covers, so the check can't pass on nothing
        for name in ("te_sr_ov_band_row", "te_sr_ov_prog_cell", "te_sr_ov_prog_cell_interstellar", "te_sr_ov_first",
                     "te_sr_power_cell", "te_sr_sec_orbit", "te_sr_debris_row", "te_sr_colony_brief_row"):
            self.assertIn(name, drawn)
        for key in ("je_space_race_widget_band_tt", "je_space_race_widget_band_suborbital",
                    "je_space_race_widget_prog_suborbital", "je_space_race_widget_prog_suborbital_ni",
                    "je_space_race_widget_prog_interstellar_2", "je_space_race_widget_power_prog_suborbital",
                    "te_orbit_satellites_tt_ni", "te_debris_row_tt", "je_space_race_widget_ov_first_claimed"):
            self.assertIn(key, keys)
        self.assertTrue(self.EXACT.match("sr_disp_progress_frac_suborbital"))
        self.assertFalse(self.EXACT.match("sr_disp_progress_frac_interstellar_results"))

    # The player's own words (I3, review of #1367): each key that speaks as
    # "we" keeps its text from before National Info, and another country's
    # panel reads a neutral twin, <key>_ni, chosen on Country.IsLocalPlayer
    # where the key is used. The phrase pinned is the one the twin drops.
    OURS = {
        "je_space_race_widget_orbit_satellites_label": "Our Satellites",
        "te_orbit_satellites_tt": "#header Our Satellites#!",
        "te_orbit_satellites_tt_disrupted": "has disrupted our orbital network",
        "te_orbit_satellites_tt_cooldown": "We were struck",
        "te_orbit_satellites_tt_exposed": "at war with us",
        "te_orbit_satellites_tt_none": "We have nothing in orbit",
        "te_asat_moratorium_detail_bound": "In force, and we are a party",
        "te_asat_moratorium_detail_not_bound": "In force, but we are not a party",
        "te_debris_row_tt_cleaners": "Ours: #v [Country.MakeScope.ScriptValue('te_debris_removal_country')|2]#!",
        "je_space_race_widget_ov_programme_tt": "a flag marks one we were first to",
        "je_space_race_widget_ov_idle_tt": "The colonies we hold keep their modifiers.",
        "je_space_race_widget_prog_interstellar_1": "before its data reaches us",
        "je_space_race_widget_prog_interstellar_2": "Its data reaches us in",
        "je_space_race_solar_colonization_status_complete": "Our civilization's presence",
        "sr_prog_state_first": "#G achieved, and we were first#!",
        "sr_prog_state_signal_received": "#G the signal has reached us#!",
    }

    def test_the_player_keeps_ours(self):
        loc, gui = self.loc, _read(GUI)
        for key, phrase in self.OURS.items():
            with self.subTest(key=key):
                self.assertIn(phrase, loc[key])
                self.assertNotIn("JournalEntry", loc[key])
                self.assertNotIn("GetPlayer", loc[key])
        # the twins, and where each is chosen
        label = "je_space_race_widget_orbit_satellites"
        self.assertEqual(loc[f"{label}_ni_label"], "Satellites")
        self.assertIn(f"SelectLocalization( Country.IsLocalPlayer, '{label}_label', '{label}_ni_label' )", gui)
        for key in ("te_orbit_satellites_tt", "te_orbit_moratorium_tt", "je_space_race_widget_ov_programme_tt",
                    "je_space_race_widget_ov_idle_tt", "je_space_race_widget_profile_solar_colonization") + tuple(
                    f"je_space_race_widget_prog_{m}" for m in ROW[:6]) + tuple(
                    f"je_space_race_widget_prog_interstellar_{n}" for n in range(4)):
            with self.subTest(dispatch=key):
                self.assertIn(f"tooltip = \"[SelectLocalization( Country.IsLocalPlayer, '{key}', '{key}_ni' )]\"", gui)
                self.assertIn(f"{key}_ni", loc)
        for word in ("disrupted", "cooldown", "exposed", "none"):
            with self.subTest(sub=word):
                self.assertIn(f"'te_orbit_satellites_tt_{word}' )", loc["te_orbit_satellites_tt"])
                self.assertIn(f"'te_orbit_satellites_tt_{word}_ni' )", loc["te_orbit_satellites_tt_ni"])
                self.assertNotRegex(loc[f"te_orbit_satellites_tt_{word}_ni"], r"\b(we|We|us|our|Our)\b")
        self.assertEqual(loc["te_orbit_satellites_tt_ni"].replace("_ni'", "'"),
                         loc["te_orbit_satellites_tt"].replace("#header Our Satellites#!", "#header Satellites#!"))
        self.assertIn("[AddLocalizationIf( Country.IsLocalPlayer, 'te_debris_row_tt_cleaners' )]"
                      "[AddLocalizationIf( Not( Country.IsLocalPlayer ), 'te_debris_row_tt_cleaners_ni' )]",
                      loc["te_debris_row_tt_cleaners_line"])
        self.assertIn("'te_debris_row_tt_cleaners_line'", loc["te_debris_row_tt"])
        # the Program row's hovers for another country use the third-person
        # sr_power_prog_<m>, the Space Powers row's
        for m in ROW[:6]:
            with self.subTest(prog=m):
                self.assertIn(f"[Country.GetCustom('sr_power_prog_{m}')]", loc[f"je_space_race_widget_prog_{m}_ni"])
        self.assertIn("$sr_power_state_data_received$", loc["je_space_race_widget_prog_interstellar_3_ni"])
        # the custom loc twins: the same branches, the _ni keys in place of the player's
        debris = _read(os.path.join(REPO, "common", "customizable_localization", "te_orbital_debris_custom_loc.txt"))
        self.assertEqual(_block(debris, "te_asat_moratorium_detail_ni").replace("_ni\n", "\n"),
                         _block(debris, "te_asat_moratorium_detail"))
        self.assertIn("GetCustom('te_asat_moratorium_detail_ni')", loc["te_orbit_moratorium_tt_ni"])
        custom = _read(CUSTOM_LOC)
        flat = lambda b: re.sub(r"\s+", " ", _strip_comments(b)).strip()
        self.assertEqual(flat(_block(custom, "sr_solar_colonization_profile_ni")).replace("_complete_ni", "_complete"),
                         flat(_block(custom, "sr_solar_colonization_profile")))
        self.assertIn("GetCustom('sr_solar_colonization_profile_ni')",
                      loc["je_space_race_widget_profile_solar_colonization_ni"])
        # the rewards are the player's alone, as before
        for m in RACING:
            with self.subTest(reward=m):
                self.assertIn("#bold If we are the first nation to do this:#!", loc[f"je_space_race_widget_reward_{m}"])
                self.assertIn(f"SelectLocalization( Country.IsLocalPlayer, 'je_space_race_widget_reward_{m}', "
                              "'te_tt_blank' )", gui)
        self.assertEqual(loc["te_tt_blank"], "")

    def test_another_countrys_colonies_read_it(self):
        """te_sr_colony_brief_rows (gen_solar_sites.py): one row per site,
        shown while the country holds it, with its settlers under Simple and
        Full Colonies, all read on Country."""
        rows = self.types["te_sr_colony_brief_rows"].body
        self.assertEqual(rows.count("te_sr_colony_brief_row = {"), len(gss.SITES))
        for s in gss.SITES:
            with self.subTest(site=s.key):
                self.assertIn(f"[EqualTo_CFixedPoint( Country.MakeScope.ScriptValue('sr_disp_site_{s.key}'), "
                              "'(CFixedPoint)1' )]", rows)
                self.assertIn(f'text = "sr_site_name_{s.key}"', rows)
        self.assertEqual(READ.findall(rows), [])
        brief = self.types["te_sr_sec_colonies_brief"].body
        self.assertIn('visible = "[Not( Country.IsLocalPlayer )]"', brief)
        self.assertEqual(READ.findall(brief), [])


class ScriptTooltipTest(unittest.TestCase):
    """The text a read-only scripted GUI's tooltip prints for another
    country's panel reads the shown country, not the player (spec
    2026-11-02-charts-help-national-info § 6.4). Orbit's Strikes hover is
    te_asat_record_sgui's ExecuteTooltip: its lines come from the effect's
    custom_tooltip keys, which no panel's loc closure reaches, so BindingTest
    can't see them. They read the scripted GUI's root (SCOPE.GetRootScope, the
    form covert_last_exposed_sgui ships), or nothing at all."""

    TOOLTIP = re.compile(r"GetScriptedGui\('(\w+)'\)\.(?:ExecuteTooltip|IsValidTooltip|IsShownTooltip)")
    PRINTS = re.compile(r"\bcustom_tooltip(?:_no_bullet)?\s*=\s*(?:\{[^{}]*?\btext\s*=\s*)?([\w.$\-]+)")

    @classmethod
    def setUpClass(cls):
        cls.types = mod_types()
        cls.view = panel_view(PrivateTest.ROOT, cls.types)
        cls.loc = load_loc()
        cls.sguis = {}
        for path in sorted(glob.glob(os.path.join(REPO, "common", "scripted_guis", "*.txt"))):
            text = _strip_comments(_read(path))
            for m in re.finditer(r"(?m)^(\w+)\s*=\s*\{", text):
                cls.sguis[m.group(1)] = text[m.end():_close(text, m.end() - 1)]

    def test_no_datacontext_tooltip_is_drawn_unguarded(self):
        for name in self.view.open:
            with self.subTest(type=name):
                self.assertNotRegex(unguarded(self.types[name].body, self.view.skip[name]),
                                    r"(?<![\w'])ScriptedGui\.(?:ExecuteTooltip|IsValidTooltip|IsShownTooltip)")

    def test_the_printed_lines_read_the_shown_country(self):
        found = set()
        for name in self.view.open:
            found |= set(self.TOOLTIP.findall(unguarded(self.types[name].body, self.view.skip[name])))
        for key in panel_loc_keys(PrivateTest.ROOT, self.types, self.loc):
            found |= set(self.TOOLTIP.findall(self.loc[key]))
        self.assertEqual(found, {"te_asat_record_sgui"})
        printed = set(self.PRINTS.findall(self.sguis["te_asat_record_sgui"]))
        self.assertEqual(printed, {"te_asat_record_last", "te_asat_record_last_unnamed", "te_asat_record_none"})
        reads = {k: READ.findall(self.loc[k]) for k in loc_closure(printed, self.loc, own=False)}
        self.assertEqual({k: r for k, r in reads.items() if r}, {})


class WideLayoutTest(unittest.TestCase):
    """te_sr_wide_sections, the window's full-screen Space Race (spec
    2026-11-02-te-window-wide-mode § 7), in three columns
    (te_ui_columns_three), each under the gate its narrow run carries: the
    milestones under way; solar colonization's four tabs (Mission Control,
    Fleets, Colonies, Solar System) in a column of their own (owner,
    2026-11-05), split out of its frame, which keeps its overview and Open
    Journal Entry in the first; then Space Powers and Orbit. How the Space
    Race Works is the Help page."""

    LIVE = {f"te_sr_window_{m}_live": m for m in window_gen.SR_OWN_COLUMN}

    def setUp(self):
        self.wide = _strip_comments(_type_body(_read(GUI), "te_sr_wide_sections"))
        self.generated = _strip_comments(_read(window_gen.GUI_OUT))

    def test_the_columns(self):
        columns = assert_wide_matches_narrow(self, "te_sr_wide_sections", layout=("te_sr_tab_body", "te_sr_tab_layout"),
                                             split={name: "te_sr_window_milestones" for name in self.LIVE})
        self.assertEqual(columns, [
            ["te_sr_window_milestones"],
            ["te_sr_window_solar_colonization_live"],
            ["te_sr_sec_powers", "te_sr_sec_orbit"]])
        self.assertIn("type te_sr_wide_sections = te_ui_columns_three", _read(GUI))

    def test_the_tabs_leave_the_first_column(self):
        """The first column's milestones empty each split-out frame block, and
        only those: the frame keeps its header, overview and Open Journal
        Entry. The side panel's te_sr_tab_body leaves the blocks alone."""
        milestones = _instances(self.wide, "te_sr_window_milestones")
        self.assertEqual(len(milestones), 1)
        self.assertEqual(re.findall(r'blockoverride "(\w+)" \{\s*\}', milestones[0]),
                         [f"sr_window_{m}_live" for m in self.LIVE.values()])
        self.assertEqual(re.sub(r'blockoverride "\w+" \{\s*\}', "", milestones[0][:-1]).strip(), "")
        frames = _type_body(self.generated, "te_sr_window_milestones")
        for m in self.LIVE.values():
            with self.subTest(milestone=m):
                opener = f'block "sr_window_{m}_live" {{'
                self.assertEqual(frames.count(opener), 1)
                start = frames.index(opener) + len(opener) - 1
                block = frames[start:_close(frames, start) + 1]
                self.assertEqual(re.findall(r"\b(te_\w+) = \{", block), [f"te_sr_{m}_status"])
                self.assertNotIn("OpenJournalEntryPanel", block)
        narrow = _type_body(_read(GUI), "te_sr_tab_body")
        self.assertIn("te_sr_window_milestones = {}", narrow)
        self.assertNotIn('blockoverride "sr_window_', narrow)

    def test_the_tabs_column_is_the_frames_live_part(self):
        """te_sr_window_<m>_live draws what the frame's block held, under the
        frame's gates: the entry shown for the Country on its root, then the
        player's own, with the entry's datacontext on the guard's child."""
        for name, m in self.LIVE.items():
            with self.subTest(type=name):
                body = _type_body(self.generated, name)
                gate = (f"GetScriptedGui('te_window_space_race_{m}_sgui')"
                        ".IsShown( GuiScope.SetRoot( Country.MakeScope ).End )")
                # its one visible, on the root: the inner levels gate by template
                self.assertEqual(re.findall(r'^\s*visible = "(.*)"$', body, re.M), [f"[{gate}]"])
                self.assertIn("minimumsize = { 520 -1 }", body)
                self.assertRegex(body, re.compile(
                    r"flowcontainer = \{\s*using = te_own_country_only\s*parentanchor = hcenter\s*direction = vertical"
                    r"\s*ignoreinvisible = yes\s*flowcontainer = \{\s*"
                    rf"datacontext = \"\[GetPlayerJournalEntry\('je_space_race_{m}'\)\]\"", re.S))
                self.assertEqual(re.findall(r"\b(te_\w+) = \{", body), [f"te_sr_{m}_status"])
                self.assertRegex(body, rf'te_sr_{m}_status = \{{\s*blockoverride "sr_debris" \{{\}}\s*\}}')

    def test_the_tabs_column_closes_up_without_them(self):
        """Column 2 shows only while its type would draw: the entry shown for
        the Country, and the Country the player's own (te_own_country_only), so
        another milestone, or another country's in National Info, leaves two
        columns, not an empty 520 between them."""
        (name, _), = self.LIVE.items()
        own = re.search(r'^\s*visible = "\[(.*)\]"$', _type_body(self.generated, name), re.M).group(1)
        shown = re.findall(r'blockoverride "column_2_visible" \{\s*visible = "(.*)"\s*\}', self.wide)
        self.assertEqual(shown, [f"[And( {own}, Country.IsLocalPlayer )]"])
        self.assertNotIn("column_1_visible", self.wide)
        self.assertNotIn("column_3_visible", self.wide)

    def test_the_window_mounts_it_full_screen(self):
        tab = next(t for t in window_gen.TABS if t.key == "space_race")
        self.assertEqual((tab.layout, tab.wide), ("te_sr_tab_layout", "te_sr_wide_sections"))


if __name__ == "__main__":
    unittest.main()
