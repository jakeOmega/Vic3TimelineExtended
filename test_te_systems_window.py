"""The Timeline Extended window (gui/te_systems_window.gui): the mod's own
window for the systems with no vanilla home, a tab each for the Space Race, the
Colonial Empire and Grand Monuments, opened from a button under the sidebar
(docs/systems/system_panels_feasibility.md §3.1, §3.5, §3.6; style guide rule 9).

These tests hold the registration to the file, the launcher's and the window's
gates, the panel-stack clearing, the tab selection (evaluated for every case),
the strip, each tab's composition, and the loc and icons the window uses.
"""
import glob
import itertools
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "te_systems_window.gui")
REGISTRATION = os.path.join(REPO, "gui", "scripted_widgets", "te_systems_window.txt")
TAB_SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers")
JE_DIR = os.path.join(REPO, "common", "journal_entries")
WIDGETS = os.path.join(REPO, "gui", "journal_entry_widgets")
LOC_DIR = os.path.join(REPO, "localization", "english")
ICON_DOC = os.path.join(REPO, "docs", "systems", "te_systems_window_gui_icons.md")

# (tab key, the rule its gates read, its slot on the strip)
TABS = [("space_race", "has_game_rule = space_race_enabled", "first"),
        ("colonial_empire", "has_game_rule = decolonization_enabled", "second"),
        ("grand_monuments", "gm_system_enabled = yes", "third")]
SR = ["suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
      "interstellar_probe", "interstellar_results", "solar_colonization"]   # je_space_race.txt order
# The systems' full names, and the width a tab's name gets: three tabs share
# about 540, less tab_text_properties' 10 px margin each side (no icon).
FULL_NAMES = {"space_race": "Space Race", "colonial_empire": "Colonial Empire",
              "grand_monuments": "Grand Monuments"}
NAME_WIDTH = 540 / 3 - 2 * 10
# Tab labels are budgeted at the medium rate, 8.6 units a character plus 10%,
# not the large row font's 10. Vanilla's tab text is the default EB Garamond 17
# (tab_text_properties; #title unselected, #variable bold selected), and the
# Covert branch measured "Mobilization" at 84.7 regular and 91.9 bold for 12
# characters, about 7.7 a character (the measured table is in PR #593).
TAB_UNITS_PER_CHAR = 8.6
OPEN = "GetVariableSystem.HasValue('com_open_window', 'te_systems_window')"
PLAYED = "GetMetaPlayer.GetPlayedOrObservedCountry.IsValid"
NOT_OBSERVER = "Not( GetMetaPlayer.IsObserver )"


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
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


def _block_at(text, start):
    """The block whose opening brace is the first after `start`, braces included."""
    brace = text.index("{", start)
    return text[start:_close(text, brace) + 1]


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


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return text[m.end():_close(text, m.end() - 1)]


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

_ATOM = re.compile(r"GetScriptedGui\('(\w+)'\)\.IsShown\( GuiScope\.SetRoot\( GetPlayer\.MakeScope \)\.End \)"
                   r"|GetVariableSystem\.HasValue\('(\w+)', '(\w+)'\)")


def _evaluate(expr, shown, stored):
    """Evaluate an And/Or/Not expression of scripted-GUI gates and one stored
    GetVariableSystem value. `shown` is the set of gates that pass."""
    def atom(m):
        if m.group(1):
            return "T" if m.group(1) in shown else "F"
        assert m.group(2) == "te_systems_window_tab", m.group(0)
        return "T" if stored == m.group(3) else "F"
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
        self.assertEqual(found, ["te_systems_window_launcher", "te_systems_window"])

    def test_the_files_carry_a_bom(self):
        for path in (REGISTRATION, GUI):
            with open(path, "rb") as f:
                self.assertEqual(f.read(3), b"\xef\xbb\xbf", path)


class LauncherTest(unittest.TestCase):
    """The button under Map List: for a played country, on the HUD, while any
    of the three systems' rules is on."""

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

    def test_the_button_is_on_the_hud_and_gated_on_the_rules(self):
        hud = self.root.index("using = hud_visibility")
        button = _named(self.gui, "te_systems_window_launcher_button")
        self.assertLess(hud, self.root.index(button))
        self.assertIn(f'visible = "[{_gate("te_window_launcher_sgui")}]"', button)
        sgui = _txt_block(_read(TAB_SGUIS), "te_window_launcher_sgui")
        for _, rule, _ in TABS:
            self.assertIn(rule, sgui)
        self.assertIn("OR = {", sgui)

    def test_it_opens_and_closes_the_window(self):
        button = _named(self.gui, "te_systems_window_launcher_button")
        self.assertIn(f'visible = "[Not( {OPEN} )]"', button)
        self.assertIn(f'visible = "[{OPEN}]"', button)
        self.assertIn("onclick = \"[GetVariableSystem.Set('com_open_window', 'te_systems_window')]\"", button)
        self.assertIn("onclick = \"[GetVariableSystem.Clear('com_open_window')]\"", button)
        self.assertEqual(button.count("sidepanel_button_small = {"), 2)
        self.assertIn('tooltip = "te_systems_window_launcher_tt"', button)

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
    while open, closing vanilla's panels as it opens."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.root = _top_level(cls.gui, "te_systems_window")
        cls.panel = _type_body(cls.gui, "te_systems_window_panel")

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

    def test_the_header_title_close_and_no_back_button(self):
        self.assertRegex(self.panel, r'blockoverride "window_header_name" \{\s*text = "te_systems_window_title"')
        self.assertRegex(self.panel, r'blockoverride "entire_back_button" \{\}')
        self.assertRegex(self.panel, r'blockoverride "header_close_button" \{\s*'
                                     r"onclick = \"\[GetVariableSystem\.Clear\('com_open_window'\)\]\"\s*\}")
        self.assertEqual(_all_loc()["te_systems_window_title"], "Timeline Extended")

    def test_the_content_column_is_panel_wide(self):
        content = _named(self.gui, "te_systems_window_content")
        self.assertIn("minimumsize = { 540 -1 }", content.split("\n\n")[0])

    def test_one_visible_per_widget(self):
        stack = [0]
        for line in _strip_comments(self.gui).splitlines():
            s = line.strip()
            if s.startswith("visible =") or s.startswith("using = te_systems_window_") and "selected" in s:
                stack[-1] += 1
                self.assertLessEqual(stack[-1], 1, f"two visibles near {s[:70]}")
            stack.extend([0] * line.count("{"))
            for _ in range(line.count("}")):
                if len(stack) > 1:
                    stack.pop()


class SelectionTest(unittest.TestCase):
    """The tab shown: the last one chosen while it is open, otherwise the first
    open one. Every combination of open tabs and stored choice."""

    @classmethod
    def setUpClass(cls):
        gui = _read(GUI)
        cls.sel = {t: _template(gui, f"te_systems_window_{t}_selected") for t, _, _ in TABS}
        cls.unsel = {t: _template(gui, f"te_systems_window_{t}_unselected") for t, _, _ in TABS}
        cls.none = _template(gui, "te_systems_window_none_open")

    def _cases(self):
        order = [t for t, _, _ in TABS]
        for opened in itertools.product([False, True], repeat=3):
            for on_strip in itertools.product([False, True], repeat=3):
                if any(o and not s for o, s in zip(opened, on_strip)):
                    continue    # a tab opens only while its rule is on
                for stored in [None] + order:
                    shown = {f"te_window_{t}_tab_sgui" for t, o in zip(order, opened) if o}
                    shown |= {f"te_window_{t}_tab_unlock_sgui" for t, s in zip(order, on_strip) if s}
                    yield dict(zip(order, opened)), dict(zip(order, on_strip)), stored, shown

    def test_exactly_the_right_tab_is_shown(self):
        order = [t for t, _, _ in TABS]
        for opened, _, stored, shown in self._cases():
            if stored and opened[stored]:
                expected = stored
            else:
                expected = next((t for t in order if opened[t]), None)
            for t in order:
                with self.subTest(opened=opened, stored=stored, tab=t):
                    self.assertEqual(_evaluate(self.sel[t], shown, stored), t == expected)
            self.assertEqual(_evaluate(self.none, shown, stored), expected is None)

    def test_a_tab_on_the_strip_shows_one_half(self):
        for opened, on_strip, stored, shown in self._cases():
            for t in opened:
                with self.subTest(opened=opened, on_strip=on_strip, stored=stored, tab=t):
                    selected = _evaluate(self.sel[t], shown, stored)
                    unselected = _evaluate(self.unsel[t], shown, stored)
                    self.assertFalse(selected and unselected)
                    self.assertEqual(selected or unselected, on_strip[t])


class StripTest(unittest.TestCase):
    """The strip: each tab greyed until its entry runs, its tooltip the unlock
    checklist while greyed, and choosing it stores the choice."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.panel = _type_body(cls.gui, "te_systems_window_panel")
        cls.sguis = _read(TAB_SGUIS)

    def _override(self, name):
        m = re.search(rf'blockoverride "{name}" \{{', self.panel)
        self.assertTrue(m, name)
        return self.panel[m.end():_close(self.panel, m.end() - 1)]

    def test_each_tab_is_greyed_until_open_and_stores_the_choice(self):
        for tab, _, slot in TABS:
            with self.subTest(tab=tab):
                click = self._override(f"{slot}_button_click")
                self.assertIn(f'enabled = "[{_gate(f"te_window_{tab}_tab_sgui")}]"', click)
                self.assertIn(f"onclick = \"[GetVariableSystem.Set('te_systems_window_tab', '{tab}')]\"", click)
                self.assertIn(f"using = te_systems_window_{tab}_selected", self._override(f"{slot}_button_visibility"))
                self.assertIn(f"using = te_systems_window_{tab}_unselected",
                              self._override(f"{slot}_button_visibility_checked"))
                tooltip = self._override(f"{slot}_button_tooltip")
                self.assertIn(f"'te_window_tab_{tab}_tt'", tooltip)
                self.assertIn(f"Localize( 'te_window_tab_{tab}_locked_tt' )", tooltip)
                self.assertIn(f"GetScriptedGui('te_window_{tab}_tab_unlock_sgui').IsValidTooltip(", tooltip)
                for half in (f"{slot}_button", f"{slot}_button_selected"):
                    self.assertIn(f'text = "te_window_tab_{tab}"', self._override(half))

    def test_the_gates_read_the_rule_and_the_entries(self):
        for tab, rule, _ in TABS:
            with self.subTest(tab=tab):
                gate = _txt_block(self.sguis, f"te_window_{tab}_tab_sgui")
                self.assertIn(rule, gate)
                unlock = _txt_block(self.sguis, f"te_window_{tab}_tab_unlock_sgui")
                self.assertIn(f"is_shown = {{ {rule} }}", unlock)
                for body in (gate, unlock):
                    self.assertIn("is_valid", body)
                    self.assertNotIn("scope:", body)    # scope-free (gotcha #22)
        sr = _txt_block(self.sguis, "te_window_space_race_tab_sgui")
        self.assertEqual(re.findall(r"has_journal_entry = je_space_race_(\w+)", sr), SR)
        self.assertIn("has_journal_entry = je_colonial_empire", _txt_block(self.sguis, "te_window_colonial_empire_tab_sgui"))
        self.assertIn("has_journal_entry = je_grand_monuments", _txt_block(self.sguis, "te_window_grand_monuments_tab_sgui"))
        for m in SR:
            gate = _txt_block(self.sguis, f"te_window_space_race_{m}_sgui")
            self.assertIn("has_game_rule = space_race_enabled", gate)
            self.assertIn(f"has_journal_entry = je_space_race_{m}\n", gate)

    def test_the_checklists_are_the_entries_own_tests(self):
        unlocks = {"space_race": "sr_entry_unlocked", "colonial_empire": "ce_entry_unlocked",
                   "grand_monuments": "gm_entry_unlocked"}
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
    (the bars-on-top marker is not content)."""
    entry = _txt_block(_read(os.path.join(JE_DIR, je_file)), entry_key)
    widgets = _read(os.path.join(WIDGETS, widget_file))
    types = []
    for name in re.findall(r'name = "(\w+)"\s*container', entry):
        if name == "widget_te_je_bars_on_top_marker" or name in skip:
            continue
        types += re.findall(r"^\t(te_\w+) = \{\}", _top_level(widgets, name), re.M)
    return types


def _entry_blocks(tab_block):
    """Each GetPlayerJournalEntry datacontext in a tab: (entry key, the widget
    carrying it, the text of the tab before that widget)."""
    for m in re.finditer(r"datacontext = \"\[GetPlayerJournalEntry\('(\w+)'\)\]\"", tab_block):
        opener = tab_block.rindex("flowcontainer = {", 0, m.start())
        yield m.group(1), _block_at(tab_block, opener), tab_block[:opener]


class TabContentTest(unittest.TestCase):
    """Style guide rule 9 and feasibility §5.1: each tab shows its entries' own
    composers under GetPlayerJournalEntry, in the journal's order, gated on a
    parent, in a fixed 520 column, and ends with Open Journal Entry."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)

    def _tab(self, tab):
        block = _named(self.gui, f"te_systems_window_{tab}_tab")
        self.assertIn(f"using = te_systems_window_{tab}_selected", block.split("\n\n")[0])
        return block

    def _check_entry(self, widget, before, gate, types, link_tooltip):
        # the gate on a parent, never on the widget carrying the datacontext
        gates = re.findall(r'visible = "\[(GetScriptedGui\(\'\w+\'\)\.IsShown\( GuiScope\.SetRoot\( '
                           r'GetPlayer\.MakeScope \)\.End \))\]"', before)
        self.assertEqual(gates[-1], _gate(gate))
        head = widget[:widget.index("\n\n")]
        self.assertNotRegex(head, r"\bvisible =")
        self.assertIn("minimumsize = { 520 -1 }", head)
        self.assertIn("parentanchor = hcenter", head)
        # the journal roots' types, in order, then the link
        self.assertEqual(re.findall(r"^\t+(te_\w+) = \{\}", widget, re.M), types)
        link = widget.index('text = "te_system_tab_open_journal"')
        self.assertGreater(link, widget.index(f"{types[-1]} = {{}}"))
        button = widget[widget.rindex("button = {", 0, link):]
        self.assertIn('visible = "[JournalEntry.IsActive]"', button)
        self.assertIn(f'tooltip = "{link_tooltip}"', button)
        self.assertIn("onclick = \"[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]\"", button)
        # nothing the journal hides behind the bars-on-top marker comes back
        self.assertNotIn("te_je_goal_bar", widget)

    def test_space_race(self):
        """Nine entries, nine gated blocks in the journal's order, each under its
        own header; the shared reference once, at the end."""
        tab = self._tab("space_race")
        blocks = list(_entry_blocks(tab))
        self.assertEqual([key for key, _, _ in blocks], [f"je_space_race_{m}" for m in SR])
        for m, (key, widget, before) in zip(SR, blocks):
            with self.subTest(entry=key):
                # the entry's own header, inside its gate and above its datacontext
                block_start = before.rindex(f"visible = \"[{_gate(f'te_window_space_race_{m}_sgui')}]\"")
                self.assertRegex(before[block_start:], re.compile(rf'default_header = \{{.*?text = "{key}"', re.S))
                self._check_entry(widget, before, f"te_window_space_race_{m}_sgui",
                                  _journal_types(key, "je_space_race.txt", "space_race_widget.gui",
                                                 skip=("widget_je_space_race_reference",)),
                                  "te_window_space_race_open_journal_tt")
        # How the Space Race Works: once, after every entry, the section the
        # journal's shared reference root composes.
        reference = _named(self.gui, "te_systems_window_space_race_reference")
        self.assertGreater(tab.index(reference), tab.index(blocks[-1][1]))
        self.assertEqual(re.findall(r"^\t+(te_\w+) = \{\}", reference, re.M), ["te_sr_sec_how"])
        self.assertIn("minimumsize = { 520 -1 }", reference)
        self.assertIn(f'visible = "[{_gate("te_window_space_race_tab_sgui")}]"', reference)
        widgets = _read(os.path.join(WIDGETS, "space_race_widget.gui"))
        self.assertEqual(re.findall(r"^\t\t(te_\w+) = \{\}", _type_body(widgets, "te_sr_reference_sections"), re.M),
                         ["te_sr_sec_how"])
        self.assertEqual(tab.count("te_sr_sec_how"), 1)
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
                    self.assertEqual(re.findall(r"^\t(\w+) = \{\}$", wrapper, re.M), [f"te_sr_{m}_{kind}"])
                    self.assertNotIn("datacontext", wrapper)
                    body = _type_body(widgets, f"te_sr_{m}_{kind}")
                    self.assertIn(f"datacontext = \"[GetScriptedGui('sr_milestone_{m}_sgui')]\"", body)
                    self.assertIn("minimumsize = { 520 -1 }", body)

    def test_colonial_empire(self):
        tab = self._tab("colonial_empire")
        blocks = list(_entry_blocks(tab))
        self.assertEqual([key for key, _, _ in blocks], ["je_colonial_empire"])
        _, widget, before = blocks[0]
        self.assertRegex(before, re.compile(r'default_header = \{.*?text = "je_colonial_empire"', re.S))
        self.assertLess(before.index("default_header"), before.index("te_window_colonial_empire_tab_sgui"))
        self._check_entry(widget, before, "te_window_colonial_empire_tab_sgui",
                          _journal_types("je_colonial_empire", "je_colonial_empire.txt", "colonial_empire_widget.gui"),
                          "te_window_colonial_empire_open_journal_tt")
        # The overview draws the stability bar, so the entry mounts the marker and
        # the tab draws no bar of its own; every scripted button is the AI's.
        entry = _read(os.path.join(JE_DIR, "je_colonial_empire.txt"))
        self.assertIn('name = "widget_te_je_bars_on_top_marker"', entry)
        self.assertIn("progressbar = no", entry)
        overview = _type_body(_read(os.path.join(WIDGETS, "colonial_empire_widget.gui")), "te_ce_overview_panel")
        self.assertIn("JournalEntry.GetScriptedProgressBars", overview)
        self.assertNotIn("te_je_scripted_bars", widget)
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
        tab = self._tab("grand_monuments")
        blocks = list(_entry_blocks(tab))
        self.assertEqual([key for key, _, _ in blocks], ["je_grand_monuments"])
        _, widget, before = blocks[0]
        # the header outside the gate
        self.assertRegex(before, re.compile(r'default_header = \{.*?text = "je_grand_monuments"', re.S))
        self.assertLess(before.index("default_header"), before.index("te_window_grand_monuments_tab_sgui"))
        self._check_entry(widget, before, "te_window_grand_monuments_tab_sgui",
                          _journal_types("je_grand_monuments", "je_grand_monuments.txt", "grand_monuments_widget.gui"),
                          "te_window_grand_monuments_open_journal_tt")
        # no status line, bar or button of its own to draw
        entry = _read(os.path.join(JE_DIR, "je_grand_monuments.txt"))
        for absent in ("status_desc", "scripted_button", "scripted_progress_bar", "progressbar"):
            self.assertNotRegex(_strip_comments(entry), rf"\b{absent} =")


class LocTest(unittest.TestCase):
    def test_every_key_the_window_uses_exists(self):
        gui = _strip_comments(_read(GUI))
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
        """The tabs carry no icon, so a name gets its tab less
        tab_text_properties' 10 px margins: three tabs share about 540. Each
        tab shows the system's full name, which fits at the medium budget."""
        loc = _all_loc()
        for tab, full in FULL_NAMES.items():
            with self.subTest(tab=tab):
                name = loc[f"te_window_tab_{tab}"]
                self.assertEqual(name, full)
                self.assertLessEqual(len(name) * TAB_UNITS_PER_CHAR * 1.1, NAME_WIDTH, name)


class IconsTest(unittest.TestCase):
    LAUNCHER = "gfx/interface/main_hud/journal_btn.dds"   # the placeholder

    def test_no_tab_sets_an_icon(self):
        """System tabs carry no icon, as vanilla's tabs and the mod's other
        tabs don't (owner, 2026-09-30)."""
        panel = _strip_comments(_type_body(_read(GUI), "te_systems_window_panel"))
        m = re.search(r"\btab_buttons = \{", panel)
        strip = panel[m.end():_close(panel, m.end() - 1)]
        self.assertNotRegex(panel, r'blockoverride "\w+_button_icon"')
        self.assertNotRegex(strip, r"\bicon = \{|\btexture =|\bbutton_icon")

    def test_the_launcher_draws_its_placeholder(self):
        gui = _read(GUI)
        button = _named(gui, "te_systems_window_launcher_button")
        self.assertEqual(re.findall(r'texture = "([^"]+)"', button), [self.LAUNCHER] * 2)
        # ...and it is the window's only texture
        self.assertEqual(set(re.findall(r'texture = "([^"]+)"', gui)), {self.LAUNCHER})

    def test_every_texture_is_listed(self):
        doc = _read(ICON_DOC)
        for path in set(re.findall(r'texture = "([^"]+)"', _read(GUI))):
            with self.subTest(path=path):
                self.assertIn(f"`{path}`", doc)


if __name__ == "__main__":
    unittest.main()
