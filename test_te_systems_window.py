"""The Timeline Extended window (gui/te_systems_window.gui): the mod's own
window. One strip of five tabs: Nation (always open), the Space Race, Grand
Monuments, the Colonial Empire and the Seabed (Global Commons).
Opened from a button under the sidebar
(docs/systems/system_panels_feasibility.md §3.1, §3.5, §3.6; style guide rule 9).
The strip, the selection templates and the tabs' mounts are generated from the
TABS registry in scripts/generators/gen_te_systems_window.py into
gui/te_systems_window_generated.gui; each tab's content is a body type in its
system's file (spec 2026-11-02-te-window-wide-mode § 9.3).

These tests hold the registration to the file, the launcher's and the window's
gates, the panel-stack clearing, the tab selection (evaluated per stored
value), the strip, each tab's composition, the generated file, and the loc and
icons the window uses. The helpers _evaluate, _strip_comments, _template and
_txt_block are imported by test_tax_code_probes.py.
"""
import glob
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
from scripts.generators import gen_te_systems_window as gen  # noqa: E402
from gui_test_helpers import _block_at, _close, _read, _strip_comments, _type_body  # noqa: E402,F401 (re-exported)

GENERATED = os.path.join(REPO, "gui", "te_systems_window_generated.gui")
GUI = os.path.join(REPO, "gui", "te_systems_window.gui")
REGISTRATION = os.path.join(REPO, "gui", "scripted_widgets", "te_systems_window.txt")
TAB_SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers")
JE_DIR = os.path.join(REPO, "common", "journal_entries")
WIDGETS = os.path.join(REPO, "gui", "journal_entry_widgets")
LOC_DIR = os.path.join(REPO, "localization", "english")
ICON_DOC = os.path.join(REPO, "docs", "systems", "te_systems_window_gui_icons.md")

# The rule each system tab's gates read (common/scripted_guis/te_system_tab_sguis.txt).
RULES = {"space_race": "sr_space_race_on = yes",
         "grand_monuments": "gm_system_enabled = yes",
         "colonial_empire": "has_game_rule = decolonization_enabled",
         "seabed": "te_global_commons_enabled = yes"}
# The system tabs, from the generator's registry: (tab key, the rule its gates
# read, its slot on its strip). Nation (always open, no rule) is the first
# slot of the first strip, then these.
SLOTS = ["first", "second", "third", "fourth", "fifth"]
ALL_TABS = [(t.key, RULES[t.key], SLOTS[[u.key for u in gen.TABS if u.row == t.row].index(t.key)])
            for t in gen.TABS[1:] if t.key in RULES]


def _shown(sgui):
    return f"GetScriptedGui('{sgui}').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"


def _valid(sgui):
    return f"GetScriptedGui('{sgui}').IsValid( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"


# The ten tabs mirrored from vanilla panels (spec § 5.1, § 6, § 9.6): (key,
# strip, tooltip key, locked key, open gate, unlock scripted GUI, body). The
# gates are the host tab's own; the tooltip is the host's where its text fits
# the window, and the window's own for Global Warming and the Strategic
# Reserve, whose host tooltips speak of another market. The grayed line is the
# window's where the host's tab name differs from the window's.
MIRRORED = [
    ("banking", 2, "te_budget_tab_banking_tt", "te_budget_tab_banking_locked_tt",
     f"Or( {_shown('te_budget_banking_tab_sgui')}, {_shown('te_budget_banking_readout_sgui')} )",
     "te_budget_banking_tab_unlock_sgui", "te_banking_tab_body"),
    ("tax_code", 2, "te_tax_tab_tt", "te_tax_tab_locked_tt", _shown("te_budget_tax_tab_sgui"),
     "te_budget_tax_tab_unlock_sgui", "te_tax_tab_body"),
    ("budget_breakdown", 2, "te_budget_chart_tab_tt", None, None, None, "te_budget_breakdown_panel"),
    ("strategic_reserve", 2, "te_window_tab_strategic_reserve_tt", "te_window_tab_strategic_reserve_locked_tt",
     _shown("te_market_strategic_reserve_tab_sgui"), "te_market_strategic_reserve_tab_unlock_sgui",
     "te_st_res_tab_body"),
    ("global_warming", 2, "te_window_tab_global_warming_tt", "te_window_tab_global_warming_locked_tt",
     _shown("te_market_global_warming_tab_sgui"), "te_market_global_warming_tab_unlock_sgui", "te_gw_tab_body"),
    ("demographics", 3, "te_pops_tab_demog_tt", "te_pops_tab_demog_locked_tt",
     f"And( {_shown('te_pops_demog_tab_sgui')}, {_valid('te_pops_demog_tab_unlock_sgui')} )",
     "te_pops_demog_tab_unlock_sgui", "te_demog_window_body"),
    ("cultural_hegemony", 3, "te_society_tab_ch_tt", "te_window_tab_cultural_hegemony_locked_tt",
     _shown("te_society_ch_tab_sgui"), "te_society_ch_tab_unlock_sgui", "te_ch_tab_body"),
    ("united_nations", 3, "te_diplomacy_tab_un_tt", "te_window_tab_united_nations_locked_tt",
     _shown("te_diplomacy_un_tab_sgui"), "te_diplomacy_un_tab_unlock_sgui", "te_un_tab_body"),
    ("nuclear_weapons", 3, "te_military_tab_nuclear_tt", "te_window_tab_nuclear_weapons_locked_tt",
     _shown("te_military_nuclear_tab_sgui"), "te_military_nuclear_tab_unlock_sgui", "te_nuclear_tab_body"),
    ("covert_warfare", 3, "te_military_tab_covert_tt", "te_window_tab_covert_warfare_locked_tt",
     _shown("te_military_covert_tab_sgui"), "te_military_covert_tab_unlock_sgui", "te_covert_tab_body"),
]
# spec § 5.1: three strips of five
STRIP_ORDER = {1: ["nation", "space_race", "grand_monuments", "colonial_empire", "seabed"],
               2: ["banking", "tax_code", "budget_breakdown", "strategic_reserve", "global_warming"],
               3: ["demographics", "cultural_hegemony", "united_nations", "nuclear_weapons", "covert_warfare"]}
SR = gen.SR_MILESTONES   # je_space_race.txt order (test_the_gates_read_the_rule_and_the_entries)
# The systems' full names (owner, 2026-09-30), and the width a tab's name gets:
# five slots share 540 less vanilla tab_buttons' 3 px margins and two 5 px
# dividers, 104.8 each, less tab_text_properties' 10 px margin each side (no
# icon): 84.8.
FULL_NAMES = {"nation": "Nation", "space_race": "Space Race", "colonial_empire": "Colonial Empire",
              "grand_monuments": "Grand Monuments", "seabed": "Seabed",
              # the mirrored tabs: the entries' names (owner, 2026-11-02), not
              # the Market tabs' Climate and Reserve
              "banking": "Banking", "tax_code": "Tax Code", "budget_breakdown": "Budget Breakdown",
              "strategic_reserve": "Strategic Reserve", "global_warming": "Global Warming",
              "demographics": "Demographics", "cultural_hegemony": "Cultural Hegemony",
              "united_nations": "United Nations", "nuclear_weapons": "Nuclear Weapons",
              "covert_warfare": "Covert Warfare"}
NAME_WIDTH = (540 - 2 * 3 - 2 * 5) / 5 - 2 * 10
# tab_text_properties wraps a name (multiline = yes) and shrinks it from the
# tab font's 17 down to fontsize_min = 12 before it elides.
TAB_FONT, TAB_FONT_MIN = 17, 12
# The longest name vanilla puts on its own five-slot strip in this same 540
# window (diplomatic_overview.gui, plain tab_buttons, no size override).
VANILLA_FIVE_SLOT_NAME = "Nation Formation"
# Tab labels are budgeted at the medium rate, 8.6 units a character plus 10%,
# not the large row font's 10. Vanilla's tab text is the default EB Garamond 17
# (tab_text_properties; #title unselected, #variable bold selected), and the
# Covert branch measured "Mobilization" at 84.7 regular and 91.9 bold for 12
# characters, about 7.7 a character (the measured table is in PR #593).
TAB_UNITS_PER_CHAR = 8.6
OPEN = "GetVariableSystem.HasValue('com_open_window', 'te_systems_window')"
PLAYED = "GetMetaPlayer.GetPlayedOrObservedCountry.IsValid"
NOT_OBSERVER = "Not( GetMetaPlayer.IsObserver )"


def _named(text, name):
    """The widget carrying `name = "<name>"`, from its opening line."""
    m = re.search(rf'^(\t*)name = "{name}"$', text, re.M)
    assert m, f"no widget named {name}"
    depth = len(m.group(1)) - 1
    opener = list(re.finditer(rf"^\t{{{depth}}}\w+ = \{{$", text[:m.start()], re.M))[-1]
    return _block_at(text, opener.start())


def _top_level(text, name):
    """A top-level widget (a registered root) by its name."""
    for m in re.finditer(r"^(\w+) = \{$", text, re.M):
        block = _block_at(text, m.start())
        if re.search(rf'^\tname = "{name}"$', block, re.M):
            return block
    raise AssertionError(f"no top-level widget {name}")


def _txt_block(text, name):
    m = re.search(rf"^{name} = \{{", text, re.M)
    assert m, f"no {name}"
    return text[m.end():_close(text, m.end() - 1)]


def _template(text, name):
    m = re.search(rf'^template {name} \{{\n\tvisible = "\[(.*)\]"\n\}}', text, re.M)
    assert m, f"no template {name}"
    return m.group(1)


def _all_loc():
    keys = {}
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        for m in re.finditer(r'^ ([\w.\-]+):\d* "(.*)"\s*$', _read(path), re.M):
            keys[m.group(1)] = m.group(2)
    return keys


def _gate(sgui):
    return f"GetScriptedGui('{sgui}').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"


# --- a small evaluator for the selection templates ----------------------------------

_ATOM = re.compile(r"GetScriptedGui\('(\w+)'\)\.(IsShown|IsValid)\( GuiScope\.SetRoot\( GetPlayer\.MakeScope \)\.End \)"
                   r"|GetVariableSystem\.HasValue\('(\w+)', '(\w+)'\)")


def _evaluate(expr, shown, stored):
    """Evaluate an And/Or/Not expression of scripted-GUI gates and one stored
    GetVariableSystem value. `shown` is the set of gates that pass: a bare
    name for its IsShown, `<name>:valid` for its IsValid."""
    def atom(m):
        if m.group(1):
            name = m.group(1) if m.group(2) == "IsShown" else f"{m.group(1)}:valid"
            return "T" if name in shown else "F"
        assert m.group(3) == "te_systems_window_tab", m.group(0)
        return "T" if stored == m.group(4) else "F"
    s = _ATOM.sub(atom, expr)
    s = s.replace("And(", "_and(").replace("Or(", "_or(").replace("Not(", "_not(")
    assert re.fullmatch(r"[\s_andortTF(),]*", s), s   # nothing left but the logic
    return eval(s, {"_and": lambda a, b: a and b, "_or": lambda a, b: a or b,  # noqa: S307
                    "_not": lambda a: not a, "T": True, "F": False})


class RegistrationTest(unittest.TestCase):
    """§3.1: each line of the registration names an existing .gui and a
    top-level widget of that name in it."""

    def test_each_line_names_a_file_and_a_widget_in_it(self):
        lines = [ln for ln in _strip_comments(_read(REGISTRATION)).splitlines() if ln.strip()]
        found = []
        for line in lines:
            m = re.fullmatch(r"(gui/[\w/]+\.gui) = (\w+)", line.strip())
            self.assertTrue(m, line)
            path = os.path.join(REPO, m.group(1))
            self.assertTrue(os.path.isfile(path), m.group(1))
            _top_level(_read(path), m.group(2))
            found.append(m.group(2))
        self.assertEqual(found, ["te_systems_window_launcher", "te_systems_window", "te_popups"])

    def test_the_files_carry_a_bom(self):
        for path in (REGISTRATION, GUI, GENERATED):
            with open(path, "rb") as f:
                self.assertEqual(f.read(3), b"\xef\xbb\xbf", path)


class LauncherTest(unittest.TestCase):
    """The button under Map List: for a played country, on the HUD. No rule
    gates it: the Nation tab is always open."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.root = _top_level(cls.gui, "te_systems_window_launcher")

    def test_the_root_is_gated_on_a_played_country(self):
        head = self.root.split("\n\n")[0]
        self.assertIn(f'visible = "[And( {PLAYED}, {NOT_OBSERVER} )]"', head)
        # the next small slot under Map List: 200 + 5 + 620
        self.assertIn("position = { 0 825 }", head)
        self.assertIn("size = { 42 40 }", head)

    def test_the_button_is_on_the_hud_with_no_rule_gate(self):
        hud = self.root.index("using = hud_visibility")
        button = _named(self.gui, "te_systems_window_launcher_button")
        self.assertLess(hud, self.root.index(button))
        self.assertNotIn("te_window_launcher_sgui", self.gui)
        self.assertNotIn("te_window_launcher_sgui", _read(TAB_SGUIS))

    def test_it_opens_and_closes_the_window(self):
        button = _named(self.gui, "te_systems_window_launcher_button")
        self.assertIn(f'visible = "[Not( {OPEN} )]"', button)
        self.assertIn(f'visible = "[{OPEN}]"', button)
        self.assertIn("onclick = \"[GetVariableSystem.Set('com_open_window', 'te_systems_window')]\"", button)
        self.assertIn("onclick = \"[GetVariableSystem.Clear('com_open_window')]\"", button)
        self.assertEqual(button.count("sidepanel_button_small = {"), 2)
        self.assertIn('tooltip = "te_systems_window_launcher_tt"', button)
        # fifteen tabs: the tooltip names none of them (plan C8)
        self.assertEqual(_all_loc()["te_systems_window_launcher_tt"],
                         "#b Timeline Extended#!\\nYour nation's lasting scores and modifiers, and a tab for each of "
                         "the mod's systems.")

    def test_it_has_vanillas_hover_label(self):
        """The sidebar's label: a strip and a label pair that slide out on the
        mouse entering the button's flowcontainer, on vanilla's state names."""
        button = _named(self.gui, "te_systems_window_launcher_button")
        for state in ("show_sidebar_labels", "hide_sidebar_labels"):
            self.assertIn(f"name = {state}", button)
        self.assertIn("onmousehierarchyenter = \"[PdxGuiInterruptThenTriggerAllAnimations("
                      "'hide_sidebar_labels','show_sidebar_labels')]\"", button)
        self.assertIn("onmousehierarchyleave = \"[PdxGuiInterruptThenTriggerAllAnimations("
                      "'show_sidebar_labels','hide_sidebar_labels')]\"", button)
        # the strip is a sibling of the hover container, as vanilla's is
        self.assertLess(button.index("name = show_sidebar_labels"),
                        button.index("te_systems_window_launcher_hover"))
        hover = _named(self.gui, "te_systems_window_launcher_hover")
        self.assertEqual(hover.count("sidebar_label_button_small = {"), 2)
        self.assertIn('text = "te_systems_window_launcher_label"', hover)
        # one label button per state, each doing what the button does
        self.assertRegex(hover, r"sidebar_label_button_small = \{\s*visible = \"\[Not\( " + re.escape(OPEN))
        self.assertIn("onclick = \"[GetVariableSystem.Set('com_open_window', 'te_systems_window')]\"", hover)
        self.assertIn("onclick = \"[GetVariableSystem.Clear('com_open_window')]\"", hover)

    def test_the_panel_stack_clearing_widgets(self):
        """§3.6: a vanilla panel or the ledger opening closes the window."""
        for condition in ("InformationPanelBar.IsAnyPanelOpen", "MapListPanelManager.IsVisible"):
            with self.subTest(condition=condition):
                self.assertRegex(self.root, r"widget = \{\s*state = \{\s*"
                                            rf'trigger_when = "\[{re.escape(condition)}\]"\s*'
                                            r"on_finish = \"\[GetVariableSystem\.Clear\('com_open_window'\)\]\"")
        # outside the HUD gate, so they work whenever the window can be open
        self.assertLess(self.root.index("MapListPanelManager.IsVisible"), self.root.index("using = hud_visibility"))


class WindowTest(unittest.TestCase):
    """The window: default_block_window where vanilla's panels sit, up only
    while open, closing vanilla's panels as it opens. Its strip and its tabs'
    column are the generated types (scripts/generators/gen_te_systems_window.py)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.generated = _read(GENERATED)
        cls.root = _top_level(cls.gui, "te_systems_window")
        cls.panel = _type_body(cls.gui, "te_systems_window_panel")
        cls.strips = _type_body(cls.generated, "te_systems_window_strips_narrow")

    def test_the_root_is_up_only_while_open_for_a_played_country(self):
        head = self.root.split("\n\n")[0]
        self.assertIn(f'visible = "[And( And( {PLAYED}, {NOT_OBSERVER} ), {OPEN} )]"', head)

    def test_opening_it_closes_vanilla_panels_and_the_ledger(self):
        m = re.search(r"state = \{\s*name = _show\s*(.*?)\}", self.root, re.S)
        self.assertTrue(m)
        self.assertIn('on_start = "[InformationPanelBar.ClosePanel]"', m.group(1))
        self.assertIn('on_start = "[MapListPanelManager.CloseCurrentPanel]"', m.group(1))

    def test_it_sits_where_vanilla_panels_do(self):
        self.assertIn("margin_top = 85", self.root)
        self.assertIn("te_systems_window_panel = {}", self.root)
        self.assertIn("type te_systems_window_panel = default_block_window {", self.gui)

    def test_the_header_title_close_and_back_button(self):
        self.assertRegex(self.panel, r'blockoverride "window_header_name" \{\s*text = "te_systems_window_title"')
        # The back button stays (its socket is in the header art) and closes
        # the window. OpenPreviousPanel reopened nothing in game, since the
        # window's own ClosePanel leaves no history (play-test 2026-09-30).
        self.assertNotIn('"entire_back_button"', self.panel)
        self.assertRegex(self.panel, r'blockoverride "header_back_button" \{\s*'
                                     r"onclick = \"\[GetVariableSystem\.Clear\('com_open_window'\)\]\"\s*"
                                     r'input_action = "back"\s*\}')
        self.assertNotIn("[InformationPanelBar.OpenPreviousPanel]", self.panel)

    def test_a_greyed_tabs_tooltip_has_three_branches(self):
        # Running: the open tooltip. Greyed with every unlock condition met
        # (an entry that has run its course): te_system_tab_met_tt, the line
        # every system tab shares (WIN-5), since IsValidTooltip then renders
        # nothing (play-test 2026-09-30).
        # Otherwise: the locked line and the checklist.
        for sys_ in ("space_race", "colonial_empire", "grand_monuments", "seabed"):
            with self.subTest(tab=sys_):
                m = re.search(r"tooltip = \"(\[SelectLocalization\( GetScriptedGui\('te_window_%s_tab_sgui'\)[^\"]*)\"" % sys_,
                              self.strips)
                self.assertIsNotNone(m)
                tt = m.group(1)
                self.assertIn("'te_window_tab_%s_tt'" % sys_, tt)
                self.assertIn("GetScriptedGui('te_window_%s_tab_unlock_sgui').IsValid(" % sys_, tt)
                # the Seabed tab has no journal entry, so its own "met" line
                met = "'te_window_tab_seabed_met_tt'" if sys_ == "seabed" else "'te_system_tab_met_tt'"
                self.assertIn(met, tt)
                self.assertIn("Localize( 'te_window_tab_%s_locked_tt' )" % sys_, tt)
                self.assertIn("GetScriptedGui('te_window_%s_tab_unlock_sgui').IsValidTooltip(" % sys_, tt)
                self.assertLess(tt.index(".IsValid("), tt.index(met))
        self.assertIn("te_system_tab_met_tt", _all_loc())
        for gone in ("te_window_tab_met_tt", "te_market_tab_met_tt"):
            self.assertNotIn(gone, _all_loc())
        self.assertRegex(self.panel, r'blockoverride "header_close_button" \{\s*'
                                     r"onclick = \"\[GetVariableSystem\.Clear\('com_open_window'\)\]\"\s*\}")
        self.assertEqual(_all_loc()["te_systems_window_title"], "Timeline Extended")

    def test_the_panel_instances_the_generated_pieces(self):
        """The strips, the templates and the tabs' mounts come from the
        registry; this file keeps the frame, the launcher and the root."""
        self.assertRegex(self.panel, re.compile(r'blockoverride "fixed_top" \{\s*vbox = \{[^{}]*te_systems_window_toggle = \{'
                                                r'.*?te_systems_window_strips_narrow = \{\}\s*\}\s*\}', re.S))
        self.assertRegex(self.panel, r'blockoverride "scrollarea_content" \{\s*te_systems_window_tabs_narrow = \{\}\s*\}')
        code = _strip_comments(self.gui)
        self.assertIsNone(re.search(r"^template ", code, re.M))
        for gone in ("tab_buttons", "GetPlayerJournalEntry", "te_systems_window_tab'"):
            self.assertNotIn(gone, code)

    def test_the_content_column_is_panel_wide(self):
        head = _type_body(self.generated, "te_systems_window_tabs_narrow").split("\n\n")[0]
        self.assertIn('name = "te_systems_window_content"', head)
        self.assertIn("using = default_list_position", head)
        self.assertIn("minimumsize = { 540 -1 }", head)

    def test_one_visible_per_widget(self):
        for path in (GUI, GENERATED):
            stack = [0]
            for line in _strip_comments(_read(path)).splitlines():
                s = line.strip()
                if s.startswith("visible =") or s.startswith("using = te_systems_window_") and "selected" in s:
                    stack[-1] += 1
                    self.assertLessEqual(stack[-1], 1, f"{path}: two visibles near {s[:70]}")
                stack.extend([0] * line.count("{"))
                for _ in range(line.count("}")):
                    if len(stack) > 1:
                        stack.pop()


def _atoms(expr):
    """The gates an expression reads, named as _evaluate looks them up."""
    if expr is None:
        return set()
    return {m.group(1) if m.group(2) == "IsShown" else f"{m.group(1)}:valid"
            for m in _ATOM.finditer(expr) if m.group(1)}


def _stored_reads(expr):
    return {m.group(4) for m in _ATOM.finditer(expr) if m.group(3)}


def _call_args(expr, start):
    """The arguments of the And/Or/Not call whose name starts at `start`."""
    i = expr.index("(", start) + 1
    depth, args, begin = 1, [], i
    while depth:
        ch = expr[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0 or (ch == "," and depth == 1):
            args.append(expr[begin:i].strip())
            begin = i + 1
        i += 1
    return args


def _tab(key):
    return next(t for t in gen.TABS if t.key == key)


class SelectionTest(unittest.TestCase):
    """The tab shown: the last one chosen while it is open, otherwise Nation,
    which always is. Enumerated per stored value: each template reads only its
    own tab's gates, the stored tab's and the tax probes'
    (test_templates_read_only_their_gates), so the stored tab in each of its
    states, every other tab in one shared state, and the probe gate on and off
    cover every case, at any number of tabs."""

    # (open, on the strip): a tab opens only while its rule is on
    STATES = [(False, False), (False, True), (True, True)]

    @classmethod
    def setUpClass(cls):
        gui = _read(GENERATED)
        cls.tabs = [t.key for t in gen.TABS]
        cls.sel = {t: _template(gui, f"te_systems_window_{t}_selected") for t in cls.tabs}
        cls.unsel = {t: _template(gui, f"te_systems_window_{t}_unselected") for t in cls.tabs}
        cls.probe = _template(gui, "te_systems_window_tax_probes_selected")
        cls.gui = gui

    def _cases(self):
        systems = self.tabs[1:]
        for stored in [None, "nation", "tax_probes", "unknown"] + systems:
            for own in (self.STATES if stored in systems else [None]):
                for rest in self.STATES:
                    for probe in (False, True):
                        states = {k: own if k == stored else rest for k in systems}
                        shown = {"te_tp_tab_sgui"} if probe else set()
                        for k, (opened, on_strip) in states.items():
                            if opened:
                                shown |= _atoms(_tab(k).open_)
                            if on_strip:
                                shown |= _atoms(_tab(k).strip)
                        # each state is the one enumerated, compound gates too
                        for k, (opened, on_strip) in states.items():
                            for gate, want in ((_tab(k).open_, opened), (_tab(k).strip, on_strip)):
                                if gate is not None:
                                    self.assertEqual(_evaluate(gate, shown, stored), want, (k, gate))
                        yield states, stored, shown, probe

    def _expected(self, stored, shown, probe):
        if stored == "tax_probes" and probe:
            return "tax_probes"
        if stored in self.tabs[1:] and (_tab(stored).open_ is None or _evaluate(_tab(stored).open_, shown, stored)):
            return stored
        return "nation"

    def test_exactly_the_right_tab_is_shown(self):
        cases = 0
        for states, stored, shown, probe in self._cases():
            cases += 1
            expected = self._expected(stored, shown, probe)
            for t in self.tabs:
                with self.subTest(states=states, stored=stored, probe=probe, tab=t):
                    self.assertEqual(_evaluate(self.sel[t], shown, stored), t == expected)
            self.assertEqual(_evaluate(self.probe, shown, stored), expected == "tax_probes")
        self.assertEqual(cases, 2 * (4 * 3 + 9 * (len(self.tabs) - 1)))

    def test_a_tab_on_the_strip_shows_one_half(self):
        for states, stored, shown, probe in self._cases():
            for t in self.tabs:
                with self.subTest(states=states, stored=stored, probe=probe, tab=t):
                    selected = _evaluate(self.sel[t], shown, stored)
                    unselected = _evaluate(self.unsel[t], shown, stored)
                    self.assertFalse(selected and unselected)
                    # Nation is always on the strip
                    strip = _tab(t).strip
                    on_strip = strip is None or _evaluate(strip, shown, stored)
                    self.assertEqual(selected or unselected, on_strip)

    def test_templates_read_only_their_gates(self):
        """What makes the per-stored-value enumeration enough: a system tab's
        templates read its own gates, its own stored value and the tax probes'
        only; Nation's reads each other tab's open gate only under that tab's
        stored value."""
        probe = {"te_tp_tab_sgui"}
        for t in gen.TABS[1:]:
            with self.subTest(tab=t.key):
                expr = self.sel[t.key] + self.unsel[t.key]
                self.assertLessEqual(_atoms(expr), _atoms(t.open_) | _atoms(t.strip) | probe)
                # each gate as written, so a dropped term of a compound gate shows
                if t.open_ is not None:
                    self.assertIn(t.open_, self.sel[t.key])
                if t.strip is not None:
                    self.assertIn(t.strip, self.unsel[t.key])
                self.assertLessEqual(_stored_reads(expr), {t.key, "tax_probes"})
        for half in (self.sel["nation"], self.unsel["nation"]):
            guarded = set()
            for m in re.finditer(r"And\( GetVariableSystem\.HasValue\('te_systems_window_tab', '(\w+)'\), ", half):
                if m.group(1) == "tax_probes":
                    continue
                args = _call_args(half, m.start())
                self.assertEqual(len(args), 2)
                self.assertEqual(args[1], _tab(m.group(1)).open_, m.group(1))
                guarded |= _atoms(args[1])
            self.assertEqual(_atoms(half) - probe, guarded)
            self.assertEqual(_stored_reads(half), {t.key for t in gen.TABS[1:]} | {"tax_probes"})

    def test_nothing_is_left_for_an_empty_window(self):
        for text in (_read(GUI), self.gui):
            self.assertNotIn("te_systems_window_none_open", text)
        self.assertNotIn("te_systems_window_none", _all_loc())


class StripTest(unittest.TestCase):
    """The strip: each tab greyed until its entry runs, its tooltip the unlock
    checklist while greyed, and choosing it stores the choice."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.strips = _type_body(_read(GENERATED), "te_systems_window_strips_narrow")
        cls.sguis = _read(TAB_SGUIS)

    def _strip(self, row=1):
        """A strip of the registry: the strips type's row-th tab_buttons."""
        at = [m.start() for m in re.finditer(r"\btab_buttons = \{", self.strips)]
        return _block_at(self.strips, at[row - 1])

    def _override(self, name, within):
        m = re.search(rf'blockoverride "{name}" \{{', within)
        self.assertTrue(m, name)
        return within[m.end():_close(within, m.end() - 1)]

    def test_each_tab_is_greyed_until_open_and_stores_the_choice(self):
        for tab, _, slot in ALL_TABS:
            with self.subTest(tab=tab):
                within = self._strip(_tab(tab).row)
                click = self._override(f"{slot}_button_click", within)
                self.assertIn(f'enabled = "[{_gate(f"te_window_{tab}_tab_sgui")}]"', click)
                self.assertIn(f"onclick = \"[GetVariableSystem.Set('te_systems_window_tab', '{tab}')]\"", click)
                self.assertIn(f"using = te_systems_window_{tab}_selected",
                              self._override(f"{slot}_button_visibility", within))
                self.assertIn(f"using = te_systems_window_{tab}_unselected",
                              self._override(f"{slot}_button_visibility_checked", within))
                tooltip = self._override(f"{slot}_button_tooltip", within)
                self.assertIn(f"'te_window_tab_{tab}_tt'", tooltip)
                self.assertIn(f"Localize( 'te_window_tab_{tab}_locked_tt' )", tooltip)
                self.assertIn(f"GetScriptedGui('te_window_{tab}_tab_unlock_sgui').IsValidTooltip(", tooltip)
                for half in (f"{slot}_button", f"{slot}_button_selected"):
                    self.assertIn(f'text = "te_window_tab_{tab}"', self._override(half, within))

    def test_nation_is_first_and_always_open(self):
        first = self._strip()
        self.assertRegex(first, r'^tab_buttons = \{\s*### nation\s*blockoverride "first_button" \{\s*text = "te_window_tab_nation"')
        click = self._override("first_button_click", first)
        self.assertNotIn("enabled =", click)
        self.assertIn("onclick = \"[GetVariableSystem.Set('te_systems_window_tab', 'nation')]\"", click)
        self.assertIn('tooltip = "te_window_tab_nation_tt"', self._override("first_button_tooltip", first))
        self.assertIn("using = te_systems_window_nation_selected", self._override("first_button_visibility", first))
        self.assertIn("using = te_systems_window_nation_unselected",
                      self._override("first_button_visibility_checked", first))

    def test_three_strips_of_five(self):
        """Spec § 5.1 (owner, 2026-11-02): the window's own five, then the
        Budget and Market panels' five, then the Population, Society,
        Diplomacy and Military panels' five, each vanilla's five-slot
        tab_buttons with no gate of its own (Nation always shows). Only the
        developer tax-probes tab keeps a strip of its own, after them."""
        self.assertEqual({row: [t.key for t in gen.TABS if t.row == row] for row in (1, 2, 3)}, STRIP_ORDER)
        self.assertEqual(len(gen.TABS), 15)
        for row, keys in STRIP_ORDER.items():
            with self.subTest(strip=row):
                strip = self._strip(row)
                self.assertTrue(strip.startswith("tab_buttons = {"))
                self.assertNotIn("visible =", strip.split("blockoverride")[0])
                at = [strip.index(f'text = "{_tab(k).label}"') for k in keys]
                self.assertEqual(at, sorted(at))
                for slot in SLOTS:
                    self.assertIn(f'blockoverride "{slot}_button"', strip)
                self.assertNotIn("sixth_button", strip)
        self.assertEqual(len(re.findall(r"\btab_buttons = \{", _strip_comments(self.strips))), 4)
        last = self._strip(3)
        rest = self.strips[self.strips.index(last) + len(last):]
        self.assertNotIn("te_window_tab_", rest)
        self.assertIn("te_tp_tab_sgui", rest)
        self.assertNotIn("tab_buttons", _strip_comments(self.gui))
        self.assertNotIn("second_strip", self.gui)

    def test_each_mirrored_tab_takes_its_hosts_gates_and_text(self):
        for key, row, tooltip, locked, open_, unlock, body in MIRRORED:
            with self.subTest(tab=key):
                t = _tab(key)
                self.assertEqual((t.row, t.body, t.label), (row, body, f"te_window_tab_{key}"))
                slot = SLOTS[STRIP_ORDER[row].index(key)]
                within = self._strip(row)
                click = self._override(f"{slot}_button_click", within)
                self.assertIn(f"onclick = \"[GetVariableSystem.Set('te_systems_window_tab', '{key}')]\"", click)
                tt = self._override(f"{slot}_button_tooltip", within)
                for half in (f"{slot}_button", f"{slot}_button_selected"):
                    self.assertIn(f'text = "te_window_tab_{key}"', self._override(half, within))
                if open_ is None:
                    # always open: no gate, no checklist
                    self.assertNotIn("enabled", click)
                    self.assertEqual(tt.strip(), f'tooltip = "{tooltip}"')
                    self.assertIsNone(t.strip)
                    continue
                self.assertIn(f'enabled = "[{open_}]"', click)
                self.assertEqual(t.strip, _shown(unlock))
                if key == "banking":
                    # the Budget tab's two-branch form: no checklist, the
                    # readout's line for a country with no entry (#805)
                    self.assertEqual(tt.strip(), (
                        f"tooltip = \"[SelectLocalization( {_shown('te_budget_banking_tab_sgui')}, '{tooltip}', "
                        f"SelectLocalization( {_shown('te_budget_banking_readout_sgui')}, "
                        f"'te_budget_tab_banking_readout_tt', '{locked}' ) )]\""))
                    continue
                self.assertEqual(tt.strip(), (
                    f"tooltip = \"[SelectLocalization( {open_}, '{tooltip}', SelectLocalization( {_valid(unlock)}, "
                    f"'te_system_tab_met_tt', Concatenate( Localize( '{locked}' ), "
                    f"GetScriptedGui('{unlock}').IsValidTooltip( GuiScope.SetRoot( GetPlayer.MakeScope ).End ) ) ) )]\""))

    def test_the_new_grayed_lines_name_the_window_tab(self):
        """Rule 9's one shape (WIN-1), where the host's tab name differs."""
        loc = _all_loc()
        for key, _, _, locked, _, _, _ in MIRRORED:
            if locked and locked.startswith("te_window_tab_"):
                with self.subTest(tab=key):
                    self.assertEqual(loc[locked], f"#b $te_window_tab_{key}$#!\\nNot open yet. It opens once:\\n")

    def test_banking_opens_on_either_branch_and_never_off_the_strip(self):
        """The entry's gate or the #805 readout's opens Banking. The readout
        needs the full banking rule, which puts the tab on the strip, so an
        open Banking is never off the strip."""
        banking = _tab("banking")
        tab, readout, unlock = "te_budget_banking_tab_sgui", "te_budget_banking_readout_sgui", "te_budget_banking_tab_unlock_sgui"
        for shown, want in (({tab, unlock}, True), ({readout, unlock}, True), ({unlock}, False), (set(), False)):
            with self.subTest(shown=sorted(shown)):
                self.assertEqual(_evaluate(banking.open_, shown, "banking"), want)
        self.assertIn("te_mon_full_system = yes", _txt_block(self.sguis, readout))
        self.assertIn("is_shown = { te_banking_system_on = yes }", _txt_block(self.sguis, unlock))
        full = _txt_block(_read(os.path.join(TRIGGERS, "te_monetary_triggers.txt")), "te_mon_full_system")
        on = _txt_block(_read(os.path.join(TRIGGERS, "banking_policy_triggers.txt")), "te_banking_system_on")
        self.assertIn("has_game_rule = banking_system_enabled", full)
        self.assertIn("has_game_rule = banking_system_enabled", on)

    def test_demographics_opens_with_its_first_census(self):
        """As the Population panel's tab: its gate and its checklist passing."""
        demog = _tab("demographics")
        for shown, want in (({"te_pops_demog_tab_sgui", "te_pops_demog_tab_unlock_sgui:valid"}, True),
                            ({"te_pops_demog_tab_sgui"}, False), ({"te_pops_demog_tab_unlock_sgui:valid"}, False)):
            with self.subTest(shown=sorted(shown)):
                self.assertEqual(_evaluate(demog.open_, shown, "demographics"), want)

    def test_the_gates_read_the_rule_and_the_entries(self):
        for tab, rule, _ in ALL_TABS:
            with self.subTest(tab=tab):
                gate = _txt_block(self.sguis, f"te_window_{tab}_tab_sgui")
                self.assertIn(rule, gate)
                unlock = _txt_block(self.sguis, f"te_window_{tab}_tab_unlock_sgui")
                self.assertIn(f"is_shown = {{ {rule} }}", unlock)
                for body in (gate, unlock):
                    self.assertIn("is_valid", body)
                    self.assertNotIn("scope:", body)    # scope-free (gotcha #22)
        # The Space Race tab stays open once the country is in the race: it has
        # run a milestone, or holds one of the nine entries (owner, 2026-10-25).
        sr = _txt_block(self.sguis, "te_window_space_race_tab_sgui")
        self.assertIn("sr_in_space_race = yes", sr)
        sr_triggers = _read(os.path.join(TRIGGERS, "space_race_triggers.txt"))
        self.assertEqual(re.findall(r"has_journal_entry = je_space_race_(\w+)",
                                    _txt_block(sr_triggers, "sr_holds_space_race_entry")), SR)
        in_race = _txt_block(sr_triggers, "sr_in_space_race")
        for cond in ("sr_space_race_participant = yes", "sr_holds_space_race_entry = yes"):
            self.assertIn(cond, in_race)
        idle = _txt_block(self.sguis, "te_window_space_race_idle_sgui")
        for cond in ("sr_space_race_on = yes", "sr_in_space_race = yes", "NOT = { sr_holds_space_race_entry = yes }"):
            self.assertIn(cond, idle)
        self.assertNotIn("scope:", idle)
        self.assertIn("has_journal_entry = je_colonial_empire", _txt_block(self.sguis, "te_window_colonial_empire_tab_sgui"))
        self.assertIn("has_journal_entry = je_grand_monuments", _txt_block(self.sguis, "te_window_grand_monuments_tab_sgui"))
        # no journal entry: open once the country has taken part in a sharing
        self.assertIn("has_variable = te_seabed_shared", _txt_block(self.sguis, "te_window_seabed_tab_sgui"))
        for m in SR:
            gate = _txt_block(self.sguis, f"te_window_space_race_{m}_sgui")
            self.assertIn("sr_space_race_on = yes", gate)
            self.assertIn(f"has_journal_entry = je_space_race_{m}\n", gate)

    def test_the_checklists_are_the_entries_own_tests(self):
        unlocks = {"space_race": "sr_entry_unlocked", "colonial_empire": "ce_entry_unlocked",
                   "grand_monuments": "gm_entry_unlocked", "seabed": "te_seabed_tab_unlocked"}
        for tab, trigger in unlocks.items():
            self.assertIn(f"is_valid = {{ {trigger} = yes }}", _txt_block(self.sguis, f"te_window_{tab}_tab_unlock_sgui"))
        # Suborbital Flight's `possible`, less its completion guard.
        sr = _txt_block(_read(os.path.join(TRIGGERS, "space_race_triggers.txt")), "sr_entry_unlocked")
        possible = _txt_block(_read(os.path.join(JE_DIR, "je_space_race.txt")).replace("\n\t", "\n"), "je_space_race_suborbital")
        possible = _txt_block(possible, "possible")
        for cond in ("has_technology_researched = rocketry", "modifier:country_sr_earth_orbit_program_bool = yes",
                     "is_great_or_major_power = yes"):
            self.assertIn(cond, possible)
            self.assertIn(cond, sr)
        # The colonial entry's technology and its `possible`.
        ce = _txt_block(_read(os.path.join(TRIGGERS, "colonial_empire_triggers.txt")), "ce_entry_unlocked")
        entry = _read(os.path.join(JE_DIR, "je_colonial_empire.txt"))
        self.assertIn("has_technology_researched = decolonization", entry)
        self.assertIn("has_technology_researched = decolonization", ce)
        for cond in ("is_overseas_colonial_state = yes", "country_has_qualifying_colonial_subject = yes",
                     "NOT = { has_variable = colonial_empire_completed }",
                     "NOT = { has_variable = colonial_empire_collapsed_recently }"):
            self.assertIn(cond, entry)
            self.assertIn(cond, ce)
        gm = _txt_block(_read(os.path.join(TRIGGERS, "monument_triggers.txt")), "gm_entry_unlocked")
        self.assertIn("any_scope_state = { has_building = building_grand_monument }", gm)
        self.assertIn("any_scope_state = { has_building = building_grand_monument }",
                      _read(os.path.join(JE_DIR, "je_grand_monuments.txt")))

def _journal_types(entry_key, je_file, widget_file, skip=()):
    """The types the entry's journal roots wrap, in the order it attaches them
    (the bars-on-top marker is not content), each inside its root's
    te_je_country (the entry's Country, test_te_system_tab_bodies.py)."""
    entry = _txt_block(_read(os.path.join(JE_DIR, je_file)), entry_key)
    widgets = _read(os.path.join(WIDGETS, widget_file))
    types = []
    for name in re.findall(r'name = "(\w+)"\s*container', entry):
        if name == "widget_te_je_bars_on_top_marker" or name in skip:
            continue
        types += re.findall(r"^\t\t(te_\w+) = \{\}", _top_level(widgets, name), re.M)
    return types


def _override(text, name):
    """A blockoverride's contents, or None when the text has none."""
    m = re.search(rf'blockoverride "{name}" \{{', text)
    return None if m is None else text[m.end():_close(text, m.end() - 1)]


class TabContentTest(unittest.TestCase):
    """Style guide rule 9 and feasibility §5.1: each tab shows its entries' own
    composers under GetPlayerJournalEntry, in the journal's order, gated on a
    parent, in a fixed 520 column, and ends with Open Journal Entry. That shape
    is te_system_tab_frame's (test_te_system_tab_bodies.py); here, what each
    tab fills it with, and that its mount holds its body."""

    @classmethod
    def setUpClass(cls):
        cls.generated = _read(GENERATED)
        cls.sr = _read(os.path.join(WIDGETS, "space_race_widget.gui"))

    def _tab(self, key):
        """The tab's mount, shown with its template, holding its registry body."""
        block = _named(self.generated, f"te_systems_window_{key}_tab")
        self.assertIn(f"using = te_systems_window_{key}_selected", block.split("\n\n")[0])
        self.assertEqual(re.findall(r"^\t+(\w+) = \{\}$", block, re.M), [_tab(key).body])
        return _tab(key).body

    def _check_frame(self, frame, header, gate, entry, types, link_tooltip, gate_on_root=False):
        root = frame.split("blockoverride")[0]
        if gate_on_root:
            # the whole frame, its header too, shows only with the entry
            self.assertIn(f'visible = "[{_gate(gate)}]"', root)
            self.assertIsNone(_override(frame, "tab_gate"))
        else:
            # the header outside the gate; the gate on a parent of the datacontext
            self.assertNotIn("visible", root)
            self.assertEqual(_override(frame, "tab_gate").strip(), f'visible = "[{_gate(gate)}]"')
        self.assertRegex(_override(frame, "tab_header"), re.compile(rf'default_header = \{{.*?text = "{header}"', re.S))
        self.assertEqual(_override(frame, "tab_entry").strip(), f"datacontext = \"[GetPlayerJournalEntry('{entry}')]\"")
        # the journal roots' types, in order; a Space Race milestone's live
        # sections drop the debris row, which Orbit shows (SPC-8:
        # `blockoverride "sr_debris" {}`)
        self.assertEqual(re.findall(r'^\t+(te_\w+) = \{(?:\}|\n\t+blockoverride "sr_debris" \{\}\n\t+\})$',
                                    _override(frame, "tab_content"), re.M), types)
        # the frame's link, with the tab's tooltip
        self.assertIsNone(_override(frame, "tab_open_journal"))
        self.assertEqual(_override(frame, "tab_open_journal_tooltip").strip(), f'tooltip = "{link_tooltip}"')
        # nothing the journal hides behind the bars-on-top marker comes back
        self.assertNotIn("te_je_goal_bar", frame)

    def test_space_race(self):
        """Nine entries, nine frames in the journal's order, each under its own
        header and gated whole; the shared reference once, at the end."""
        self.assertEqual(self._tab("space_race"), "te_sr_tab_body")
        milestones = _type_body(self.generated, "te_sr_window_milestones")
        frames = [_block_at(milestones, m.start()) for m in re.finditer(r"^\t+te_system_tab_frame = \{$", milestones, re.M)]
        self.assertEqual(len(frames), len(SR))
        for m, frame in zip(SR, frames):
            key = f"je_space_race_{m}"
            with self.subTest(entry=key):
                self._check_frame(frame, key, f"te_window_space_race_{m}_sgui", key,
                                  _journal_types(key, "je_space_race.txt", "space_race_widget.gui",
                                                 skip=("widget_je_space_race_reference",)),
                                  "te_window_space_race_open_journal_tt", gate_on_root=True)
        # How the Space Race Works: once, after every entry, the section the
        # journal's shared reference root composes.
        body = _type_body(self.sr, "te_sr_tab_body")
        reference = _named(self.sr, "te_systems_window_space_race_reference")
        self.assertGreater(body.index(reference), body.index("te_sr_window_milestones = {}"))
        self.assertEqual(re.findall(r"^\t+(te_\w+) = \{\}", reference, re.M), ["te_sr_sec_how"])
        self.assertIn("minimumsize = { 520 -1 }", reference)
        self.assertIn(f'visible = "[{_gate("te_window_space_race_tab_sgui")}]"', reference)
        self.assertEqual(re.findall(r"^\t\t(te_\w+) = \{\}", _type_body(self.sr, "te_sr_reference_sections"), re.M),
                         ["te_sr_sec_how"])
        self.assertEqual(body.count("te_sr_sec_how"), 1)
        self.assertNotIn("te_sr_sec_how", milestones)
        # every entry mounts the bars-on-top marker (its overview draws the
        # progress), shows its status line only while inactive, and every
        # scripted button is the AI's
        je = _read(os.path.join(JE_DIR, "je_space_race.txt"))
        buttons = _read(os.path.join(REPO, "common", "scripted_buttons", "space_race_buttons.txt"))
        for m in SR:
            entry = _txt_block(je, f"je_space_race_{m}")
            self.assertIn('name = "widget_te_je_bars_on_top_marker"', entry)
            self.assertIn(f"trigger = {{ NOT = {{ has_journal_entry = je_space_race_{m} }} }}", entry)
            self.assertNotIn("scripted_progress_bar", entry)
            for name in re.findall(r"scripted_button = (\w+)", entry):
                self.assertRegex(_txt_block(buttons, name), r"visible = \{[^}]*is_ai = yes", name)

    def test_space_powers_and_orbit_follow_the_entries_and_read_no_entry(self):
        """The tab's own sections, under its gate, below every entry's frame
        and above How (owner, 2026-10-27: the milestones we run first): they
        read the player, so they show between milestones too. Orbit carries the
        debris row, so every milestone's live sections drop theirs."""
        body = _type_body(self.sr, "te_sr_tab_body")
        summary = _named(self.sr, "te_systems_window_space_race_summary")
        self.assertIn(f'visible = "[{_gate("te_window_space_race_tab_sgui")}]"', summary)
        self.assertEqual(re.findall(r"^\t+(te_\w+) = \{\}", summary, re.M), ["te_sr_sec_powers", "te_sr_sec_orbit"])
        self.assertIn("minimumsize = { 520 -1 }", summary)
        self.assertNotIn("GetPlayerJournalEntry", summary)
        self.assertGreater(body.index(summary), body.index("te_sr_window_milestones = {}"))
        self.assertLess(body.index(summary), body.index(_named(self.sr, "te_systems_window_space_race_reference")))
        milestones = _type_body(self.generated, "te_sr_window_milestones")
        for m in SR:
            if m != "interstellar_results":
                self.assertRegex(milestones, rf'te_sr_{m}_status = \{{\n\t+blockoverride "sr_debris" \{{\}}', m)
        # one note in the entries' place while none runs
        idle = _named(self.generated, "te_systems_window_space_race_idle")
        self.assertIn(f'visible = "[{_gate("te_window_space_race_idle_sgui")}]"', idle)
        self.assertLess(milestones.index(idle), milestones.index("te_system_tab_frame = {"))
        self.assertIn('text = "te_window_space_race_idle_note"', idle)
        for name in ("te_sr_sec_powers", "te_sr_sec_orbit"):
            self.assertIn(f"type {name} = flowcontainer", self.sr)
            self.assertNotIn("JournalEntry", _type_body(self.sr, name))
            # never mounted in the journal: only the tab's body and its
            # full-screen layout (te_sr_wide_sections) compose them, once each
            wide = _type_body(self.sr, "te_sr_wide_sections")
            self.assertEqual(self.sr.count(f"{name} = {{}}"), 2)
            self.assertEqual((body.count(f"{name} = {{}}"), wide.count(f"{name} = {{}}")), (1, 1))

    def test_the_milestone_types_are_the_journal_roots_bodies(self):
        """Each controlled milestone's roots are thin wrappers around its own
        types, which set its scripted GUI as the datacontext."""
        widgets = _read(os.path.join(WIDGETS, "space_race_widget.gui"))
        for m in SR:
            if m == "interstellar_results":
                continue
            for kind, root in (("overview", f"widget_je_space_race_{m}_overview"), ("status", f"widget_je_space_race_{m}")):
                with self.subTest(root=root):
                    wrapper = _top_level(widgets, root)
                    # the type in the root's te_je_country, which only supplies the Country
                    self.assertEqual(re.findall(r"^\tte_je_country = \{\n\t\t(\w+) = \{\}\n\t\}$", wrapper, re.M),
                                     [f"te_sr_{m}_{kind}"])
                    self.assertNotIn("datacontext", wrapper)
                    body = _type_body(widgets, f"te_sr_{m}_{kind}")
                    self.assertIn(f"datacontext = \"[GetScriptedGui('sr_milestone_{m}_sgui')]\"", body)
                    self.assertIn("minimumsize = { 520 -1 }", body)

    def _body(self, key, widget_file):
        body = self._tab(key)
        text = _read(os.path.join(WIDGETS, widget_file))
        self.assertIn(f"type {body} = te_system_tab_frame {{", text)
        return _type_body(text, body)

    def test_colonial_empire(self):
        frame = self._body("colonial_empire", "colonial_empire_widget.gui")
        self._check_frame(frame, "je_colonial_empire", "te_window_colonial_empire_tab_sgui", "je_colonial_empire",
                          _journal_types("je_colonial_empire", "je_colonial_empire.txt", "colonial_empire_widget.gui"),
                          "te_window_colonial_empire_open_journal_tt")
        # The overview draws the stability bar, so the entry mounts the marker and
        # the tab draws no bar of its own; every scripted button is the AI's.
        entry = _read(os.path.join(JE_DIR, "je_colonial_empire.txt"))
        self.assertIn('name = "widget_te_je_bars_on_top_marker"', entry)
        self.assertIn("progressbar = no", entry)
        overview = _type_body(_read(os.path.join(WIDGETS, "colonial_empire_widget.gui")), "te_ce_overview_panel")
        self.assertIn("JournalEntry.GetScriptedProgressBars", overview)
        self.assertNotIn("te_je_scripted_bars", frame)
        # The status line is for an inactive entry only.
        status = _txt_block(_strip_comments(entry).replace("\n\t", "\n"), "status_desc")
        triggers = re.findall(r"trigger = \{(.*?)\n\t\t\}", status, re.S)
        self.assertTrue(triggers)
        for trigger in triggers:
            self.assertIn("NOT = { has_journal_entry = je_colonial_empire }", trigger)
        buttons = _read(os.path.join(REPO, "common", "scripted_buttons", "colonial_empire_buttons.txt"))
        for name in re.findall(r"scripted_button = (\w+)", entry):
            self.assertRegex(_txt_block(buttons, name), r"visible = \{[^}]*is_ai = yes", name)

    def test_grand_monuments(self):
        frame = self._body("grand_monuments", "grand_monuments_widget.gui")
        # the header outside the gate: the tab's own name, as every other tab's
        # header is (WIN-4; the entry is "Monuments" in the journal)
        self._check_frame(frame, "te_window_tab_grand_monuments", "te_window_grand_monuments_tab_sgui",
                          "je_grand_monuments",
                          _journal_types("je_grand_monuments", "je_grand_monuments.txt", "grand_monuments_widget.gui"),
                          "te_window_grand_monuments_open_journal_tt")
        # no status line, bar or button of its own to draw
        entry = _read(os.path.join(JE_DIR, "je_grand_monuments.txt"))
        for absent in ("status_desc", "scripted_button", "scripted_progress_bar", "progressbar"):
            self.assertNotRegex(_strip_comments(entry), rf"\b{absent} =")


class SeabedTabTest(unittest.TestCase):
    """The Seabed tab: no journal entry, so its sections read GetPlayer, under
    the tab's gate on a parent, in the frame's fixed 520 column, the header
    outside the gate (gui/te_seabed_widgets.gui holds the types)."""

    def test_the_seabed_tab(self):
        self.assertEqual(re.findall(r"^\t+(\w+) = \{\}$", _named(_read(GENERATED), "te_systems_window_seabed_tab"), re.M),
                         ["te_seabed_tab_body"])
        widgets = _read(os.path.join(REPO, "gui", "te_seabed_widgets.gui"))
        self.assertIn("type te_seabed_tab_body = te_system_tab_frame {", widgets)
        body = _type_body(widgets, "te_seabed_tab_body")
        self.assertEqual(_override(body, "tab_gate").strip(), f'visible = "[{_gate("te_window_seabed_tab_sgui")}]"')
        self.assertIn("default_header", _override(body, "tab_header"))
        self.assertIsNone(_override(body, "tab_entry"))
        self.assertEqual(_override(body, "tab_open_journal").strip(), "")
        self.assertEqual(re.findall(r"^\t+(te_seabed_\w+) = \{\}", _override(body, "tab_content"), re.M),
                         ["te_seabed_overview_panel", "te_seabed_policy_panel", "te_seabed_basins_panel",
                          "te_seabed_how_panel"])
        for name in ("te_seabed_overview_panel", "te_seabed_policy_panel", "te_seabed_basins_panel",
                     "te_seabed_how_panel"):
            self.assertIn(f"type {name} = ", widgets)
        # the reference a link to the Help page (test_te_help_pages.py)
        self.assertIn("GetVariableSystem.Set('te_popup', 'help_seabed')", _type_body(widgets, "te_seabed_how_panel"))
        with open(os.path.join(REPO, "gui", "te_seabed_widgets.gui"), "rb") as f:
            self.assertEqual(f.read(3), b"\xef\xbb\xbf")

    def test_the_tabs_content_in_the_strips_order(self):
        generated = _read(GENERATED)
        at = [generated.index(f'name = "te_systems_window_{t.key}_tab"') for t in gen.TABS]
        self.assertEqual(at, sorted(at))
        nation = _named(generated, "te_systems_window_nation_tab")
        self.assertIn("using = te_systems_window_nation_selected", nation.split("\n\n")[0])
        self.assertIn("te_nation_tab_sections = {}", nation)


WIDE = "GetVariableSystem.Exists('te_systems_window_wide')"


class WideTest(unittest.TestCase):
    """The toggle between the side-panel frame and the full-screen one (spec
    § 4): one client-side key, te_systems_window_wide, the root showing one
    frame or the other; the chosen tab a separate key, so it survives."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.generated = _read(GENERATED)
        cls.root = _top_level(cls.gui, "te_systems_window")
        cls.narrow = _type_body(cls.gui, "te_systems_window_panel")
        cls.wide = _type_body(cls.gui, "te_systems_window_panel_wide")

    def _child(self, opener):
        """The root's direct child opening with `opener`."""
        m = re.search(rf"^\t{re.escape(opener)} = \{{$", self.root, re.M)
        self.assertTrue(m, opener)
        return _block_at(self.root, m.start())

    def test_the_root_switches(self):
        """Narrow: where vanilla's side panels sit, its vbox under the top bar.
        Wide: at the root's origin, full size, as vanilla's full-screen panels
        sit in ingame_hud.gui, the frame's own top filler under the top bar."""
        narrow = self._child("widget")
        self.assertIn(f'visible = "[Not( {WIDE} )]"', narrow.split("\n\n")[0])
        self.assertIn("size = { 100% 100% }", narrow.split("\n\n")[0])
        self.assertRegex(narrow, r"vbox = \{[^}]*margin_top = 85")
        self.assertIn("te_systems_window_panel = {}", narrow)
        wide = self._child("te_systems_window_panel_wide")
        self.assertEqual(wide.strip(), f'te_systems_window_panel_wide = {{\n\t\tvisible = "[{WIDE}]"\n\t}}')
        self.assertIn("type te_systems_window_panel_wide = te_fullscreen_block_window {", self.gui)
        self.assertNotIn("margin_widget", _strip_comments(self.gui))
        # the state that closes vanilla's panels stays on the root: switching
        # width doesn't rerun it
        self.assertEqual(self.root.count("name = _show"), 1)

    def test_the_toggle_keeps_the_tab(self):
        on = _override(self.narrow, "fixed_top")
        off = _override(self.wide, "fixed_top")
        for frame, text, onclick in ((on, "te_systems_window_wide_on", "GetVariableSystem.Set('te_systems_window_wide', 'yes')"),
                                     (off, "te_systems_window_wide_off", "GetVariableSystem.Clear('te_systems_window_wide')")):
            with self.subTest(toggle=text):
                toggle = _override(frame, "toggle")
                self.assertIn(f'text = "{text}"', toggle)
                self.assertIn(f'tooltip = "{text}_tt"', toggle)
                self.assertIn(f'onclick = "[{onclick}]"', toggle)
                self.assertNotIn("te_systems_window_tab", toggle)
                self.assertNotIn("com_open_window", toggle)
                # first in fixed_top, above the strips
                self.assertLess(frame.index("te_systems_window_toggle = {"), frame.index("te_systems_window_strips_"))
        self.assertIn("using = default_button", _type_body(self.gui, "te_systems_window_toggle"))
        loc = _all_loc()
        self.assertEqual(loc["te_systems_window_wide_on"], "Full Screen")
        self.assertEqual(loc["te_systems_window_wide_off"], "Side Panel")

    def test_the_full_screen_toggle_sits_clear_of_the_outliner(self):
        """Vanilla's outliner, on the HUD layer above this window, covers the
        screen's right 360 px from y = 155 (ingame_hud.gui) and hides only for
        vanilla's own full screens (half_and_fullscreen_hide reads
        InformationPanelBar.IsPanelOpen), and the full-screen width is kept
        for the session. So the full-screen frame's toggle sits at the left,
        under Back; the side panel's stays at its right."""
        toggle_type = _type_body(self.gui, "te_systems_window_toggle")
        self.assertRegex(toggle_type, r'block "toggle_lead" \{\s*expand = \{\}\s*\}\s*button = \{')
        button = toggle_type.index("button = {")
        self.assertRegex(toggle_type[_close(toggle_type, button + len("button = {") - 1):],
                         r'^\}\s*block "toggle_trail" \{\}\s*$')
        narrow = _override(self.narrow, "fixed_top")
        self.assertIsNone(_override(narrow, "toggle_lead"))    # right-aligned
        self.assertIsNone(_override(narrow, "toggle_trail"))
        wide = _override(self.wide, "fixed_top")
        self.assertEqual(_override(wide, "toggle_lead").strip(), "")    # left-aligned
        self.assertEqual(_override(wide, "toggle_trail").strip(), "expand = {}")

    def test_both_frames_close_alike(self):
        clear = "onclick = \"[GetVariableSystem.Clear('com_open_window')]\""
        for block in ("header_back_button", "header_close_button"):
            self.assertIn(clear, _override(self.narrow, block))
        frame = _type_body(self.generated, "te_fullscreen_block_window")
        self.assertEqual(frame.count(clear), 2)    # Back and Close (test_te_fullscreen_frame.py)
        for block in ("back_button_fullscreen", "entire_content_area"):
            self.assertIsNone(_override(self.wide, block))
        for panel in (self.narrow, self.wide):
            self.assertRegex(panel, r'blockoverride "window_header_name" \{\s*text = "te_systems_window_title"')

    def test_the_wide_strip_is_the_narrow_strips_side_by_side(self):
        narrow = _type_body(self.generated, "te_systems_window_strips_narrow")
        wide = _type_body(self.generated, "te_systems_window_strips_wide")
        n = [_block_at(narrow, m.start()) for m in re.finditer(r"\btab_buttons = \{", narrow)]
        w = [_block_at(wide, m.start()) for m in re.finditer(r"\btab_buttons = \{", wide)]
        self.assertEqual(len(n), len(w))
        size = "minimumsize = { 540 -1 }\nmaximumsize = { 540 -1 }"
        for a, b in zip(n, w):
            lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
            self.assertIn(size, "\n".join(lines))
            # the same slots, but for the width (and the developer strip's
            # gate, which its wide row carries)
            self.assertEqual([ln for ln in lines if not ln.endswith("size = { 540 -1 }") and not ln.startswith("visible")],
                             [ln.strip() for ln in a.splitlines() if ln.strip() and not ln.strip().startswith("visible")])
        # the system strips in one centered row, then the developer strip
        row = _block_at(wide, wide.index("hbox = {"))
        self.assertRegex(row, r"^hbox = \{[^{}]*expand = \{\}\s*tab_buttons = \{")
        self.assertRegex(row, r"\}\s*expand = \{\}\s*\}$")
        self.assertEqual(row.count("tab_buttons = {"), len({t.row for t in gen.TABS}))
        self.assertNotIn("visible", row.split("tab_buttons = {")[0])    # the system strips show to all
        # the developer strip's row carries its gate (its strip, as the wide
        # strips do, carries none)
        dev = _block_at(wide, wide.index("hbox = {", wide.index("TEMPORARY")))
        self.assertIn(f'visible = "[{gen.shown("te_tp_tab_sgui")}]"', dev.split("tab_buttons = {")[0])
        self.assertIn('text = "te_tp_tab"', dev)

    def test_the_wide_column(self):
        """The full-screen frame's column: three 520 columns' width, centered,
        each tab's mount as narrow, holding its wide layout: every tab has one
        (spec § 7). It sits in place of the body for a tab with no layout
        block, else in the body with its layout block overridden."""
        column = _type_body(self.generated, "te_systems_window_tabs_wide")
        head = column.split("\n\n")[0]
        for line in ('name = "te_systems_window_content_wide"', "minimumsize = { 1620 -1 }", "parentanchor = hcenter"):
            self.assertIn(line, head)
        self.assertRegex(_override(self.wide, "scrollarea_content"), r"^\s*te_systems_window_tabs_wide = \{\}\s*$")
        for t in gen.TABS:
            with self.subTest(tab=t.key):
                mount = _named(self.generated, f"te_systems_window_{t.key}_tab_wide")
                self.assertIn(f"using = te_systems_window_{t.key}_selected", mount)
                # the mount's properties, a blank line, then its content (the generator's _mount)
                self.assertIn("\n\n", mount)
                content = mount.split("\n\n", 1)[1]
                self.assertIsNotNone(t.wide, f"{t.key} has no full-screen layout (spec § 7)")
                if t.layout is None:
                    self.assertEqual(re.findall(r"^\t+(\w+) = \{\}$", mount, re.M), [t.wide])
                    self.assertNotIn(t.body, content)
                else:
                    # ^ and $ without re.M: the whole content is the body and its one override
                    self.assertRegex(content, rf'^\t+{t.body} = \{{\n\t+blockoverride "{t.layout}" \{{\n'
                                              rf'\t+{t.wide} = \{{\}}\n\t+\}}\n\t+\}}\n\t+\}}$')
        at = [column.index(f'name = "te_systems_window_{t.key}_tab_wide"') for t in gen.TABS]
        self.assertEqual(at, sorted(at))


class TaxFooterTest(unittest.TestCase):
    """Tax Code's footer in both frames (plan C9): Budget's (budget_panel.gui
    fixed_bottom), the draft summary or the bill under debate's, below the
    scrolling content so their buttons stay on screen. Only on the Tax Code
    tab (its selected template, which carries the tab's open gate) and only
    while a draft or a bill is; the tab's body leaves its own copy out."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.footer = _type_body(cls.gui, "te_systems_window_tax_footer")

    def test_both_frames_show_it(self):
        for frame in ("te_systems_window_panel", "te_systems_window_panel_wide"):
            with self.subTest(frame=frame):
                self.assertRegex(_override(_type_body(self.gui, frame), "fixed_bottom"),
                                 r"^\s*te_systems_window_tax_footer = \{\}\s*$")

    def test_only_on_the_tax_code_tab_while_a_draft_or_a_bill_is(self):
        head = self.footer[:self.footer.index("flowcontainer = {")]
        self.assertIn("using = te_systems_window_tax_code_selected", head)
        self.assertNotRegex(head, r"(?m)^\s*visible =")    # one visible per widget: the template's
        inner = _block_at(self.footer, self.footer.index("flowcontainer = {"))
        self.assertIn(f'visible = "[Or( {_shown("te_tax_show_draft_sgui")}, {_shown("te_tax_show_bill_sgui")} )]"',
                      inner.split("divider_clean")[0])
        at = [inner.index(t) for t in ("divider_clean", "using = dark_area", "te_tax_draft_summary = {}",
                                        "te_tax_bill_summary = {}")]
        self.assertEqual(at, sorted(at))
        self.assertIn("size = { 554 4 }", inner)    # Budget's @panel_width_plus_14
        # the tab's gate rides on the template
        self.assertIn(_tab("tax_code").open_, _template(_read(GENERATED), "te_systems_window_tax_code_selected"))
        # the body draws none of its own
        body = _type_body(_read(os.path.join(WIDGETS, "te_tax_layout_widget.gui")), "te_tax_tab_body")
        self.assertRegex(body, r'te_tax_status_sections = \{\s*blockoverride "draft_summary" \{\s*\}\s*\}')


class GeneratorTest(unittest.TestCase):
    """scripts/generators/gen_te_systems_window.py writes the window's strip,
    selection templates and tab mounts from its TABS registry (spec § 9.3)."""

    def test_generated_file_is_current(self):
        with open(GENERATED, "rb") as f:
            committed = f.read()
        self.assertTrue(committed.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(committed[3:].startswith(b"\xef\xbb\xbf"))    # exactly one BOM
        self.assertEqual(committed.decode("utf-8-sig"), gen.render(),
                         "stale: run python3 scripts/generators/gen_te_systems_window.py")
        self.assertEqual(gen.main(["--check"]), 0)

    def test_the_gates_take_a_root(self):
        """The gates root on the player by default, the window's as before
        (the committed file, above), and on another root when asked: National
        Info roots them on the shown country (charts-help-national-info plan,
        F0.3 and F1.1). Only the developer tax-probes gate stays the player's."""
        self.assertEqual(gen._root(), "GuiScope.SetRoot( GetPlayer.MakeScope ).End")
        self.assertEqual(gen.shown("x"), gen.shown("x", gen.PLAYER_ROOT))
        self.assertEqual(gen.shown("x", gen.COUNTRY_ROOT),
                         "GetScriptedGui('x').IsShown( GuiScope.SetRoot( Country.MakeScope ).End )")
        for t in gen.TABS:
            with self.subTest(tab=t.key):
                for gate in (t.open_, t.strip, t.tooltip_expr):
                    self.assertEqual(gen.rooted(gate), gate)
                    if gate:
                        self.assertNotIn("GetPlayer", gen.rooted(gate, gen.COUNTRY_ROOT))
                country = [gen._tooltip(t, gen.COUNTRY_ROOT), *gen._slot("first", t, gen.COUNTRY_ROOT),
                           gen.selected(t, gen.COUNTRY_ROOT), gen.unselected(t, gen.COUNTRY_ROOT)]
                text = "\n".join(country).replace(gen.TAX_PROBES, "")
                self.assertNotIn("GetPlayer", text)
                if t.open_:
                    self.assertIn("Country.MakeScope", text)
                self.assertEqual(gen._tooltip(t), gen._tooltip(t, gen.PLAYER_ROOT))

    def test_nation_is_first_and_the_fallback(self):
        self.assertEqual(gen.TABS[0].key, "nation")
        self.assertIsNone(gen.TABS[0].open_)
        self.assertIsNone(gen.TABS[0].strip)
        # every other tab has an open gate, but Budget Breakdown, which has no
        # entry and no rule (always open, as on the Budget panel)
        self.assertTrue(all(t.open_ for t in gen.TABS[1:] if t.key != "budget_breakdown"), "every other tab has an open gate")
        self.assertIsNone(_tab("budget_breakdown").open_)
        self.assertIsNone(_tab("budget_breakdown").strip)
        self.assertEqual(len({t.key for t in gen.TABS}), len(gen.TABS))
        self.assertNotIn("tax_probes", {t.key for t in gen.TABS})

    def test_an_always_open_tab_reads_only_its_stored_value(self):
        """A tab with no open gate (as Budget Breakdown) is shown whenever it
        was last chosen, and Nation's fallback reads it so. (On a strip of its
        own: the three are full.)"""
        extra = gen.Tab("always_open", 4, label="te_x", tooltip="te_x_tt", body="te_x_body")
        with mock.patch.object(gen, "TABS", gen.TABS + [extra]):
            text = gen.render()
        self.assertNotIn("None", text)
        stored = "GetVariableSystem.HasValue('te_systems_window_tab', 'always_open')"
        self.assertEqual(_template(text, "te_systems_window_always_open_selected"),
                         f"And( Not( {gen.TAX_PROBES} ), {stored} )")
        for half in ("selected", "unselected"):
            nation = _template(text, f"te_systems_window_nation_{half}")
            self.assertIn(stored, nation)
            self.assertNotIn(f"And( {stored}", nation)
        self.assertIn('tooltip = "te_x_tt"', text)

    def test_a_gated_tab_needs_its_checklist(self):
        """A tab with an open gate shows a checklist while grayed, so it names
        the scripted GUI and the locked line, unless it brings its own tooltip."""
        bad = gen.Tab("no_checklist", 4, label="te_x", tooltip="te_x_tt", body="te_x_body", open_=gen.shown("te_x_sgui"))
        with mock.patch.object(gen, "TABS", gen.TABS + [bad]):
            with self.assertRaisesRegex(ValueError, "no_checklist"):
                gen.render()
        own = gen.Tab("own_tooltip", 4, label="te_x", tooltip="te_x_tt", body="te_x_body",
                      open_=gen.shown("te_x_sgui"), tooltip_expr="Localize( 'te_x_tt' )")
        with mock.patch.object(gen, "TABS", gen.TABS + [own]):
            self.assertIn("tooltip = \"[Localize( 'te_x_tt' )]\"", gen.render())

    def test_a_system_tab_can_sit_on_any_strip(self):
        self.assertEqual(gen._system("x", "te_x_tab_body", "te_x_tab_layout", row=3).row, 3)
        self.assertEqual(gen._system("x", "te_x_tab_body", "te_x_tab_layout").row, 1)

    def test_check_fails_on_a_file_without_its_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = gen.Path(tmp) / "generated.gui"
            with mock.patch.object(gen, "GUI_OUT", path):
                path.write_bytes(gen.render().encode("utf-8"))
                self.assertEqual(gen.main(["--check"]), 1)
                path.write_bytes(b"\xef\xbb\xbf" + gen.render().encode("utf-8"))
                self.assertEqual(gen.main(["--check"]), 0)
                path.write_bytes(b"\xef\xbb\xbf\xef\xbb\xbf" + gen.render().encode("utf-8"))
                self.assertEqual(gen.main(["--check"]), 1)

    def test_templates_are_binary(self):
        """And and Or take exactly two arguments (gui_modding_guide.md)."""
        text = _strip_comments(_read(GENERATED))
        exprs = re.findall(r'"\[(.*?)\]"', text)
        self.assertGreater(len(exprs), 2 * len(gen.TABS))
        for expr in exprs:
            for m in re.finditer(r"\b(And|Or)\( ", expr):
                depth, args, i = 1, 1, m.end()
                while depth:
                    ch = expr[i]
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                    elif ch == "," and depth == 1:
                        args += 1
                    i += 1
                self.assertEqual(args, 2, expr[m.start():i][:120])


class LocTest(unittest.TestCase):
    def test_every_key_the_window_uses_exists(self):
        """The window's file, the generated one, and each tab's body."""
        bodies = []
        for path in glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True):
            text = _read(path)
            bodies += [_type_body(text, t.body) for t in gen.TABS if f"type {t.body} = " in text]
        self.assertEqual(len(bodies), len(gen.TABS))
        bodies.append(_type_body(_read(os.path.join(REPO, "gui", "te_system_tab_widgets.gui")), "te_system_tab_frame"))
        gui = _strip_comments("\n".join([_read(GUI), _read(GENERATED)] + bodies))
        keys = set(re.findall(r'\b(?:text|tooltip) = "([A-Za-z]\w*)"', gui))
        keys |= set(re.findall(r"Localize\( '(\w+)' \)", gui))
        keys |= set(re.findall(r"SelectLocalization\( .*?, '(\w+)',", gui))
        loc = _all_loc()
        self.assertTrue(keys)
        for key in sorted(keys):
            with self.subTest(key=key):
                self.assertIn(key, loc)
        for key in ("sr_unlock_rank_tt", "sr_unlock_earth_orbit_tt", "ce_unlock_colonies_tt",
                    "ce_unlock_not_secured_tt", "ce_unlock_no_collapse_tt", "gm_unlock_tt"):
            self.assertIn(key, loc)

    def test_each_tab_shows_its_full_name(self):
        """The tabs carry no icon, so a name gets its slot less
        tab_text_properties' 10 px margins: 84.8 with five on the strip. A
        two-word name such as "Colonial Empire" is wider than that on one line
        at 17, as vanilla's "Release Subject" and "Nation Formation" are on
        its own five-slot Diplomacy strip in this window; tab_text_properties
        wraps it and shrinks it toward 12. So each word fits one line at
        fontsize_min (the medium budget), no name runs to a third line, and
        none is longer, or has a longer word, than vanilla's longest."""
        loc = _all_loc()
        per_char = TAB_UNITS_PER_CHAR * 1.1 * TAB_FONT_MIN / TAB_FONT
        vanilla_word = max(len(w) for w in VANILLA_FIVE_SLOT_NAME.split())
        self.assertEqual(set(FULL_NAMES), {t.key for t in gen.TABS})
        for tab, full in FULL_NAMES.items():
            with self.subTest(tab=tab):
                # a label may splice its entry's name ($je_x$), single-sourced
                name = re.sub(r"\$(\w+)\$", lambda m: loc[m.group(1)], loc[_tab(tab).label])
                self.assertEqual(name, full)
                words = name.split()
                self.assertLessEqual(len(words), 2, name)
                for word in words:
                    self.assertLessEqual(len(word) * per_char, NAME_WIDTH, word)
                if tab in RULES or tab == "nation":
                    # the mirrored tabs take the entries' names, the owner's
                    # call, however long; "Demographics" shrinks toward 12
                    self.assertLessEqual(len(name), len(VANILLA_FIVE_SLOT_NAME), name)
                    self.assertLessEqual(max(len(w) for w in words), vanilla_word, name)


class IconsTest(unittest.TestCase):
    LAUNCHER = "gfx/interface/main_hud/te_systems_window_btn.dds"   # the mod's own (icon pipeline)
    FADE_MASK = "gfx/interface/masks/fade_horizontal_right.dds"   # vanilla's, for the hover strip

    def test_no_tab_sets_an_icon(self):
        """System tabs carry no icon, as vanilla's tabs and the mod's other
        tabs don't (owner, 2026-09-30)."""
        strips = _strip_comments(_type_body(_read(GENERATED), "te_systems_window_strips_narrow"))
        self.assertNotRegex(strips, r'blockoverride "\w+_button_icon"')
        self.assertNotRegex(strips, r"\bicon = \{|\btexture =|\bbutton_icon")
        self.assertNotIn("tab_buttons", _strip_comments(_read(GUI)))

    def test_the_launcher_draws_its_own_icon(self):
        gui = _read(GUI)
        button = _named(gui, "te_systems_window_launcher_button")
        # the hover strip's fade is vanilla's mask, not the window's art
        textures = [t for t in re.findall(r'texture = "([^"]+)"', button) if t != self.FADE_MASK]
        self.assertEqual(textures, [self.LAUNCHER] * 2)
        # ...and it is the window's only icon: the generated file's textures
        # are vanilla's full-screen frame's (test_te_fullscreen_frame.py)
        self.assertEqual(set(re.findall(r'texture = "([^"]+)"', gui)) - {self.FADE_MASK}, {self.LAUNCHER})
        frame = _type_body(_read(GENERATED), "te_fullscreen_block_window")
        vanilla = _type_body(_read(os.path.join(REPO, "test_fixtures", "vanilla_gui", "block_windows.gui")),
                             "fullscreen_block_window")
        self.assertEqual(re.findall(r'texture = "([^"]+)"', _read(GENERATED)),
                         re.findall(r'texture = "([^"]+)"', frame))
        self.assertEqual(re.findall(r'texture = "([^"]+)"', frame), re.findall(r'texture = "([^"]+)"', vanilla))

    def test_every_texture_is_listed(self):
        doc = _read(ICON_DOC)
        for path in set(re.findall(r'texture = "([^"]+)"', _read(GUI))) - {self.FADE_MASK}:
            with self.subTest(path=path):
                self.assertIn(f"`{path}`", doc)


if __name__ == "__main__":
    unittest.main()
