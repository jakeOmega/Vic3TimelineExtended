"""The shared system-tab frame and the tab bodies built on it
(gui/te_system_tab_widgets.gui; spec
docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 9.1).

One shape for every journal-entry tab, in the window and in the vanilla
panels that host a system's tab: the header, the tab's gate on a parent of the
GetPlayerJournalEntry datacontext (gotcha #29), a fixed 520 column, the
content, and Open Journal Entry. Each body type derives from the frame and
fills its blocks, so two hosts of one tab can't drift apart.
"""
import glob
import os
import re
import unittest

from gui_test_helpers import (GUARD, _children, _close, _instances, _read, _strip_comments, _type_body,
                              mod_types, type_closure)

REPO = os.path.dirname(os.path.abspath(__file__))
WIDGETS = os.path.join(REPO, "gui", "te_system_tab_widgets.gui")
JE_WIDGETS = os.path.join(REPO, "gui", "journal_entry_widgets")

OPEN_JOURNAL = "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]"


def _gate(sgui):
    return f"GetScriptedGui('{sgui}').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"


def _override(body, name):
    """A blockoverride's contents in a type body, or None when it has none."""
    m = re.search(rf'blockoverride "{name}" \{{', body)
    return None if m is None else body[m.end():_close(body, m.end() - 1)]


class FrameTest(unittest.TestCase):
    """te_system_tab_frame: the shape every frame-based tab body shares."""

    @classmethod
    def setUpClass(cls):
        cls.body = _strip_comments(_type_body(_read(WIDGETS), "te_system_tab_frame"))

    def test_the_frame_shape(self):
        self.assertRegex(_read(WIDGETS), r"type te_system_tab_frame = flowcontainer \{")
        top = _children(self.body)
        # the header, then what goes before the gate (Banking's readout), then the gate
        blocks = [name for kind, name, _ in top if kind == "block"]
        # the Country the sections read (MountContextTest), then the header
        self.assertEqual(blocks, ["tab_country", "tab_header", "tab_before_gate"])
        widgets = [(name, text) for kind, name, text in top if kind == "widget"]
        self.assertEqual([name for name, _ in widgets], ["flowcontainer"])
        names = [name for _, name, _ in top]
        self.assertLess(names.index("tab_before_gate"), names.index("flowcontainer"))
        self.assertNotIn("visible", names)   # the root's visible is the instance's
        # the gate: on the parent's own properties, never with the datacontext
        gate = _children(widgets[0][1])
        own = [(kind, name) for kind, name, _ in gate if kind != "widget"]
        self.assertIn(("block", "tab_gate"), own)
        self.assertNotIn("datacontext", [name for _, name in own])
        inner = [text for kind, name, text in gate if kind == "widget"]
        self.assertEqual(len(inner), 1)
        # the entry's column: its datacontext block, a fixed 520, the content,
        # then the link
        column = _children(inner[0])
        self.assertEqual([name for kind, name, _ in column if kind == "block"],
                         ["tab_entry", "tab_content", "tab_open_journal"])
        self.assertIn(("property", "minimumsize", "{ 520 -1 }"), column)
        self.assertNotIn("visible", [name for kind, name, _ in column if kind == "property"])
        # the layout the window's tabs had inline (no visible change): spacing
        # between the header and the gate, none in the gate, the column's own
        props = lambda items: {(name, text) for kind, name, text in items if kind == "property"}  # noqa: E731
        self.assertLessEqual({("direction", "vertical"), ("parentanchor", "hcenter"), ("ignoreinvisible", "yes"),
                              ("spacing", "10")}, props(top))
        self.assertLessEqual({("direction", "vertical"), ("parentanchor", "hcenter"), ("ignoreinvisible", "yes")},
                             props(gate))
        self.assertNotIn("spacing", {name for name, _ in props(gate)})
        self.assertLessEqual({("direction", "vertical"), ("parentanchor", "hcenter"), ("ignoreinvisible", "yes"),
                              ("spacing", "10")}, props(column))
        link = [text for kind, name, text in column if kind == "block" and name == "tab_open_journal"][0]
        self.assertEqual([name for kind, name, _ in _children(link)], ["button"])

    def test_the_link(self):
        """Open Journal Entry: shown while the entry runs, at the width every
        host uses, with its font and tooltip left to the body."""
        m = re.search(r'block "tab_open_journal" \{', self.body)
        self.assertTrue(m)
        link = self.body[m.end():_close(self.body, m.end() - 1)]
        button = _children(link)[0][2]
        for line in ('visible = "[JournalEntry.IsActive]"', "using = default_button", "size = { 480 32 }",
                     'text = "te_system_tab_open_journal"', f'onclick = "{OPEN_JOURNAL}"',
                     'block "tab_open_journal_font" {}', 'block "tab_open_journal_tooltip" {}'):
            self.assertIn(line, button)
        # the font block after default_button, so a body's font wins
        self.assertLess(button.index("using = default_button"), button.index('block "tab_open_journal_font"'))


# The window's journal-entry and seabed tabs, as the frame's blocks fill them:
# (body type, file, header text, gate, journal entry or None, layout block,
# composers in order, Open Journal Entry's tooltip or None).
WINDOW_BODIES = [
    ("te_gm_tab_body", os.path.join(JE_WIDGETS, "grand_monuments_widget.gui"),
     "te_window_tab_grand_monuments", "te_window_grand_monuments_tab_sgui", "je_grand_monuments",
     "te_gm_tab_layout", ["te_gm_overview_panel", "te_gm_status_sections", "te_gm_reference_sections"],
     "te_window_grand_monuments_open_journal_tt"),
    ("te_ce_tab_body", os.path.join(JE_WIDGETS, "colonial_empire_widget.gui"),
     "je_colonial_empire", "te_window_colonial_empire_tab_sgui", "je_colonial_empire",
     "te_ce_tab_layout", ["te_ce_overview_panel", "te_ce_status_sections", "te_ce_reference_sections"],
     "te_window_colonial_empire_open_journal_tt"),
    ("te_seabed_tab_body", os.path.join(REPO, "gui", "te_seabed_widgets.gui"),
     "te_seabed_tab_header", "te_window_seabed_tab_sgui", None,
     "te_seabed_tab_layout", ["te_seabed_overview_panel", "te_seabed_policy_panel", "te_seabed_basins_panel",
                              "te_seabed_how_panel"],
     None),
]


class BodyTest(unittest.TestCase):
    """Each tab's body: the frame with its blocks filled, the content the
    window's tab drew inline before the frame (spec § 9.1)."""

    def test_window_bodies(self):
        for name, path, header, gate, entry, layout, composers, tooltip in WINDOW_BODIES:
            with self.subTest(body=name):
                text = _strip_comments(_read(path))
                self.assertTrue(re.search(rf"type {name} = te_system_tab_frame \{{", text), f"no type {name}")
                body = _type_body(text, name)
                # the header outside the gate, as every tab's is, with the
                # Help page's "?" once the system has one (test_te_help_pages.py)
                head = _override(body, "tab_header")
                self.assertRegex(head, rf'default_header = \{{\s*using = default_list_position\s*'
                                       rf'blockoverride "text" \{{\s*text = "{header}"\s*\}}\s*'
                                       rf'(?:te_help_button = \{{[^{{}}]*\}}\s*)?\}}')
                self.assertEqual(_override(body, "tab_gate").strip(), f'visible = "[{_gate(gate)}]"')
                if entry:
                    self.assertEqual(_override(body, "tab_entry").strip(),
                                     f"datacontext = \"[GetPlayerJournalEntry('{entry}')]\"")
                    self.assertIsNone(_override(body, "tab_open_journal"))
                    self.assertEqual(_override(body, "tab_open_journal_tooltip").strip(), f'tooltip = "{tooltip}"')
                else:
                    # no entry: no datacontext and no link, whose JournalEntry would not resolve
                    self.assertIsNone(_override(body, "tab_entry"))
                    self.assertEqual(_override(body, "tab_open_journal").strip(), "")
                    self.assertNotIn("JournalEntry", body)
                # the composers, inside the layout block a wide mount overrides
                content = _override(body, "tab_content")
                m = re.fullmatch(rf'\s*block "{layout}" \{{(.*)\}}\s*', content, re.S)
                self.assertTrue(m, content)
                self.assertEqual(re.findall(r"^\t+(te_\w+) = \{\}$", m.group(1), re.M), composers)
                self.assertNotIn("visible", body.replace(_override(body, "tab_gate"), ""))

    def test_the_space_race_body(self):
        """Nine entries, each its own frame (te_sr_window_milestones, generated),
        then the tab's own sections, which read no entry, then How the Space
        Race Works once, all in the layout block a wide mount overrides."""
        text = _strip_comments(_read(os.path.join(JE_WIDGETS, "space_race_widget.gui")))
        self.assertTrue(re.search(r"type te_sr_tab_body = flowcontainer \{", text), "no type te_sr_tab_body")
        body = _type_body(text, "te_sr_tab_body")
        top = _children(body)
        props = [(name, value) for kind, name, value in top if kind == "property"]
        for prop in (("direction", "vertical"), ("parentanchor", "hcenter"), ("ignoreinvisible", "yes"),
                     ("spacing", "10")):
            self.assertIn(prop, props)
        self.assertNotIn("visible", [name for name, _ in props])
        self.assertEqual([(kind, name) for kind, name, _ in top if kind != "property"], [("block", "te_sr_tab_layout")])
        layout = [text for kind, _, text in top if kind == "block"][0]
        parts = _children(layout)
        self.assertEqual([name for _, name, _ in parts], ["te_sr_window_milestones", "flowcontainer", "flowcontainer"])
        self.assertEqual(parts[0], ("widget", "te_sr_window_milestones", ""))
        for (_, _, part), name, spacing, sections in (
                (parts[1], "te_systems_window_space_race_summary", "4", ["te_sr_sec_powers", "te_sr_sec_orbit"]),
                (parts[2], "te_systems_window_space_race_reference", None, ["te_sr_sec_how"])):
            with self.subTest(part=name):
                own = dict((n, v) for kind, n, v in _children(part) if kind == "property")
                self.assertEqual(own["name"], f'"{name}"')
                self.assertEqual(own["visible"], f'"[{_gate("te_window_space_race_tab_sgui")}]"')
                self.assertEqual(own["minimumsize"], "{ 520 -1 }")
                self.assertEqual(own.get("spacing"), spacing)
                self.assertEqual([n for kind, n, _ in _children(part) if kind != "property" or n.startswith("te_")],
                                 sections)
                self.assertNotIn("JournalEntry", part)


# The vanilla panels' system tabs, each now on its body (plan Tasks C1–C6):
# (host file, the host's outer flowcontainer, the tab's key, the body). The
# host keeps that flowcontainer's name, IsTabSelected gate, fade, position and
# margins, and anything that reads the host panel; the body holds the rest.
HOST_MOUNTS = [
    ("budget_panel.gui", "te_budget_banking_tab", "te_banking", "te_banking_tab_body"),
    ("budget_panel.gui", "te_budget_tax_tab", "te_tax_code", "te_tax_tab_body"),
    ("market_panel.gui", "te_market_global_warming_tab", "te_global_warming", "te_gw_tab_body"),
    ("market_panel.gui", "te_market_strategic_reserve_tab", "te_strategic_reserve", "te_st_res_tab_body"),
    ("culture_panel.gui", "te_society_ch_tab", "te_ch", "te_ch_tab_body"),
    ("diplomatic_overview.gui", "te_diplomacy_un_tab", "te_un", "te_un_tab_body"),
    ("panel_military.gui", "te_military_nuclear_tab", "te_nuclear", "te_nuclear_tab_body"),
    ("panel_military.gui", "te_military_covert_tab", "te_covert", "te_covert_tab_body"),
]

# The hosts' bodies, as the frame's blocks fill them: (body type, file, gate,
# journal entry, layout block, composers in order, Open Journal Entry's
# tooltip, its font). Headers vary (Banking has two) and are each system's
# own test's to check; the hosts' headers carry no position template, as
# before (no visible change in the hosts).
HOST_BODIES = [
    ("te_banking_tab_body", os.path.join(JE_WIDGETS, "banking_layout_widget.gui"),
     "te_budget_banking_tab_sgui", "je_banking_cycle", "te_banking_tab_layout",
     ["te_banking_overview_panel", "te_banking_status_sections", "te_banking_reference_sections"],
     "te_budget_banking_open_journal_tt", "fontsize_large"),
    ("te_tax_tab_body", os.path.join(JE_WIDGETS, "te_tax_layout_widget.gui"),
     "te_budget_tax_tab_sgui", "je_tax_code", "te_tax_tab_layout",
     ["te_tax_overview_panel", "te_tax_status_sections", "te_tax_reference_sections"],
     "te_tax_open_journal_tt", "te_tax_fontsize_row"),
    # the host overrides te_gw_tab_market_view with its two markets' views
    ("te_gw_tab_body", os.path.join(JE_WIDGETS, "global_warming_widget.gui"),
     "te_market_global_warming_tab_sgui", "je_global_warming", "te_gw_tab_layout",
     ["te_gw_overview_panel", "te_gw_status_sections", "te_gw_reference_sections"],
     "te_market_global_warming_open_journal_tt", None),
    # the host adds the own-market test to the gate (te_st_res_tab_gate)
    ("te_st_res_tab_body", os.path.join(JE_WIDGETS, "strategic_reserve_widget.gui"),
     "te_market_strategic_reserve_tab_sgui", "je_strategic_reserve", "te_st_res_tab_layout",
     ["te_st_res_overview_panel", "te_st_res_status_sections", "te_st_res_reference_sections"],
     "te_market_strategic_reserve_open_journal_tt", None),
    ("te_ch_tab_body", os.path.join(JE_WIDGETS, "cultural_hegemony_widget.gui"),
     "te_society_ch_tab_sgui", "je_cultural_hegemony", "te_ch_tab_layout",
     ["te_ch_overview_panel", "te_ch_status_sections", "te_ch_reference_sections"],
     "te_society_ch_open_journal_tt", None),
    # the entry's status text as a Status section (te_un_sec_status), after the overview
    ("te_un_tab_body", os.path.join(JE_WIDGETS, "un_layout_widget.gui"),
     "te_diplomacy_un_tab_sgui", "je_united_nations", "te_un_tab_layout",
     ["te_un_overview_panel", "te_un_sec_status", "te_un_status_sections", "te_un_reference_sections"],
     "te_diplomacy_un_open_journal_tt", None),
    # the entry's goal bar under The Programme, while there is one
    ("te_nuclear_tab_body", os.path.join(JE_WIDGETS, "nuclear_layout_widget.gui"),
     "te_military_nuclear_tab_sgui", "je_nuclear_program", "te_nuclear_tab_layout",
     ["te_nuclear_overview_panel", "te_nuclear_sec_programme", "te_je_goal_bar", "te_nuclear_status_sections",
      "te_nuclear_reference_sections"],
     "te_military_nuclear_open_journal_tt", None),
    ("te_covert_tab_body", os.path.join(JE_WIDGETS, "covert_operations_widget.gui"),
     "te_military_covert_tab_sgui", "je_covert_warfare", "te_covert_tab_layout",
     ["te_covert_overview_panel", "te_covert_status_sections", "te_covert_reference_sections"],
     "te_military_covert_open_journal_tt", None),
]


def _named_block(text, name):
    """The block whose own `name = "<name>"` line it carries, its body only."""
    at = text.index(f'name = "{name}"')
    start = text.rindex("{", 0, at)
    return text[start + 1:_close(text, start)]


class HostBodyTest(unittest.TestCase):
    def test_host_bodies(self):
        for name, path, gate, entry, layout, composers, tooltip, font in HOST_BODIES:
            with self.subTest(body=name):
                text = _strip_comments(_read(path))
                self.assertTrue(re.search(rf"^\ttype {name} = te_system_tab_frame \{{", text, re.M), f"no type {name}")
                body = _type_body(text, name)
                self.assertIsNotNone(_override(body, "tab_header"))
                # the gate, as is or as a block's default a host may override
                own_gate = re.sub(r'^\s*block "\w+" \{(.*)\}\s*$', r"\1", _override(body, "tab_gate"), flags=re.S)
                self.assertEqual(own_gate.strip(), f'visible = "[{_gate(gate)}]"')
                self.assertEqual(_override(body, "tab_entry").strip(),
                                 f"datacontext = \"[GetPlayerJournalEntry('{entry}')]\"")
                self.assertIsNone(_override(body, "tab_open_journal"))    # the frame's link
                self.assertEqual(_override(body, "tab_open_journal_tooltip").strip(), f'tooltip = "{tooltip}"')
                if font:
                    self.assertEqual(_override(body, "tab_open_journal_font").strip(), f"using = {font}")
                else:
                    self.assertIsNone(_override(body, "tab_open_journal_font"))
                content = _override(body, "tab_content")
                m = re.fullmatch(rf'\s*block "{layout}" \{{(.*)\}}\s*', content, re.S)
                self.assertTrue(m, content)
                self.assertEqual(_instances(m.group(1)), composers)

    def test_each_host_tab_mounts_its_body(self):
        for host, outer, key, body in HOST_MOUNTS:
            with self.subTest(tab=key):
                block = _named_block(_strip_comments(_read(os.path.join(REPO, "gui", host))), outer)
                items = _children(block)
                props = [(n, v) for kind, n, v in items if kind == "property"]
                self.assertIn(("visible", f"\"[InformationPanel.IsTabSelected('{key}')]\""), props)
                # the body is its only child but for a state the host keeps
                self.assertEqual([n for kind, n, _ in items
                                  if (kind != "property" or n.startswith("te_")) and n != "state"], [body])
                self.assertNotIn("datacontext", [n for n, _ in props])


class DemogWindowBodyTest(unittest.TestCase):
    """The window's Demographics tab (plan C7): no entry, so the Country its
    sections read is the player's (datacontext GetPlayer, as the Population
    panel's window supplies it) and there is no link; the gate is the
    Population panel tab's."""

    def test_the_demographics_window_body(self):
        text = _strip_comments(_read(os.path.join(REPO, "gui", "te_demographics_layout.gui")))
        self.assertTrue(re.search(r"^\ttype te_demog_window_body = te_system_tab_frame \{", text, re.M))
        body = _type_body(text, "te_demog_window_body")
        self.assertEqual(_override(body, "tab_gate").strip(), f'visible = "[{_gate("te_pops_demog_tab_sgui")}]"')
        self.assertEqual(_override(body, "tab_entry").strip(), 'datacontext = "[GetPlayer]"')
        self.assertEqual(_override(body, "tab_open_journal").strip(), "")
        self.assertRegex(_override(body, "tab_content"),
                         r'^\s*block "te_demog_tab_layout" \{\s*te_demog_window_sections = \{\}\s*\}\s*$')
        self.assertNotIn("JournalEntry", body)


# What only a tab's vanilla host has: its panel's own datacontext. A body is
# shown by the window too, which has none of them, so none may read them; a
# host's extras that do (the Market panel's map-mode reset, Global Warming's
# other-market view) stay in the host (spec § 3, plan Review Focus 2).
HOST_PANELS = re.compile(r"\bInformationPanel\.|\b(?:MarketPanel|PopsOverviewPanel|PopBrowserPanel|BudgetPanel|"
                         r"SocietyPanel|MilitaryPanel|DiplomaticOverviewPanel)\b")


class HostPanelTest(unittest.TestCase):
    def test_no_body_reads_a_host_panel(self):
        """Every te_*_tab_body type, the frame, and what the window's
        generated file draws."""
        checked = []
        for path in sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)):
            text = _strip_comments(_read(path))
            names = re.findall(r"^\ttype (te_\w+_tab_body|te_system_tab_frame) = ", text, re.M)
            if path.endswith("te_systems_window_generated.gui"):
                names += re.findall(r"^\ttype (\w+) = ", text, re.M)
            for name in names:
                with self.subTest(type=name):
                    hit = HOST_PANELS.search(_type_body(text, name))
                    self.assertIsNone(hit, f"{name} reads {hit and hit.group(0)}")
                checked.append(name)
        for name in ("te_system_tab_frame", "te_gm_tab_body", "te_ce_tab_body", "te_seabed_tab_body", "te_sr_tab_body",
                     "te_systems_window_tabs_narrow", "te_sr_window_milestones", *(b[0] for b in HOST_BODIES)):
            self.assertIn(name, checked)

    def test_no_window_tab_reads_a_host_panel(self):
        """What each of the window's tabs mounts (the registry's bodies and
        wide layouts, whatever their names), and every type those reach
        through instances and base types, all the way down (composers,
        sections, rows, cells), read none of the hosts' panels. The Census
        Data window's own panel (PopBrowserPanel) counts: Demographics' wide
        layout is that window's composer. A block a tab blanks with a
        blockoverride is still read, so its default may not read one either."""
        from scripts.generators import gen_te_systems_window as gen
        types, bases = {}, {}
        for path in sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)):
            text = _strip_comments(_read(path))
            for name, base in re.findall(r"^\ttype (\w+) = (\w+) \{", text, re.M):
                types[name], bases[name] = _type_body(text, name), base
        for t in gen.TABS:
            with self.subTest(tab=t.key):
                self.assertIn(t.body, types)
                self.assertIn(t.wide, types)
                reached, todo = set(), [t.body, t.wide]
                while todo:
                    name = todo.pop()
                    if name in reached:
                        continue
                    reached.add(name)
                    todo += [c for c in [bases[name], *_instances(types[name])] if c in types]
                for name in sorted(reached):
                    hit = HOST_PANELS.search(types[name])
                    self.assertIsNone(hit, f"{t.key}: {name} reads {hit and hit.group(0)}")
                # the walk goes past the composers: Strategic Reserve's
                # sections sit inside the status composer its wide layout
                # places whole
                if t.key == "strategic_reserve":
                    self.assertIn("te_st_res_sec_inventory", reached)


# --- Other countries' panels (charts-help-national-info plan, PR F0) ---------------------------------
# docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md §§ 6.3, 6.5, 7.1, 7.2.


def _templates():
    """Every template in the mod's GUI, by name: its body, comments cut."""
    out = {}
    for path in sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)):
        text = _strip_comments(_read(path))
        for m in re.finditer(r"(?m)^\s*template (\w+) \{", text):
            out[m.group(1)] = text[m.end():_close(text, m.end() - 1)]
    return out


def _enclosing_block(text, pos):
    """The offset of the opening brace of the innermost block around pos, or -1."""
    depth = 0
    for i in range(pos - 1, -1, -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                return i
            depth -= 1
    return -1


class GuardTemplateTest(unittest.TestCase):
    """te_own_country_only, the one own-country guard (spec § 7.2), and the
    closure the binding tests walk."""

    def test_the_template(self):
        raw = _read(WIDGETS)
        self.assertIn(f'template {GUARD} {{\n\tvisible = "[Country.IsLocalPlayer]"\n}}', raw)
        # a template sits outside the types block
        self.assertLess(raw.index(f"template {GUARD}"), raw.index("types te_system_tab_widgets"))
        self.assertEqual(_templates()[GUARD].strip(), 'visible = "[Country.IsLocalPlayer]"')

    def test_the_closure_follows_every_mod_type(self):
        """Grand Monuments' wide layout reaches its sections and their gm_* rows
        (types the mod writes without te_), and nothing of another system's."""
        types = mod_types()
        reached = type_closure({"te_gm_wide_sections"}, types)
        for name in ("te_gm_wide_sections", "te_gm_sec_commission", "te_gm_overview_panel", "te_ui_columns_three"):
            self.assertIn(name, reached)
        self.assertTrue(any(name.startswith("gm_") for name in reached), "the gm_* rows")
        self.assertEqual([name for name in reached if name.startswith("te_ce_")], [])
        # vanilla's types (a file that copies vanilla's markup) are vanilla's own reads
        self.assertNotIn("FancyTooltip_Law", type_closure({"te_demog_browser_sections"}, types))

    def test_the_guard_is_its_widgets_only_visible(self):
        """A widget that takes the guard has no visible of its own, through
        another template neither, and isn't an instance of a type whose root
        has one: in game the instance's visible replaces the type's (gotcha
        #17). Such a widget gets a wrapper that takes the guard."""
        templates = {name for name, body in _templates().items() if re.search(r"^\s*visible\s*=", body, re.M)}
        types = mod_types()
        found = 0
        for path in sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)):
            text = _strip_comments(_read(path))
            for m in re.finditer(rf"\busing\s*=\s*{GUARD}\b", text):
                found += 1
                where = f"{os.path.relpath(path, REPO)}:{text.count(chr(10), 0, m.start()) + 1}"
                brace = _enclosing_block(text, m.start())
                self.assertGreaterEqual(brace, 0, where)
                own = _children(text[brace + 1:_close(text, brace)])
                props = [(k, v) for kind, k, v in own if kind == "property"]
                with self.subTest(at=where):
                    self.assertNotIn("visible", [k for k, _ in props], f"{where}: a widget with its own visible "
                                     f"takes the guard on a wrapper (one visible per widget)")
                    others = [v for k, v in props if k == "using" and v in templates and v != GUARD]
                    self.assertEqual(others, [], f"{where}: {others} sets a visible too; wrap one of them")
                    opener = re.search(r"(\w+) = \{$", text[:brace + 1])
                    instance = opener.group(1) if opener else ""
                    if instance in types:
                        root = [k for kind, k, _ in _children(types[instance].body) if kind == "property"]
                        self.assertNotIn("visible", root, f"{where}: {instance}'s root has its own visible, which "
                                                          f"the guard would replace (gotcha #17); wrap the instance")
        self.assertGreater(found, 0, "the guard is used")



# Every file with journal-entry roots, the private systems' included: the chart
# type reads Country (F0.3), and Global Warming, the UN and the Strategic Reserve
# draw charts in their entries.
JOURNAL_ROOT_FILES = ["banking_layout_widget.gui", "colonial_empire_widget.gui", "covert_operations_widget.gui",
                      "cultural_hegemony_widget.gui", "global_warming_widget.gui", "grand_monuments_widget.gui",
                      "nuclear_layout_widget.gui", "space_race_widget.gui", "strategic_reserve_widget.gui",
                      "te_tax_layout_widget.gui", "un_layout_widget.gui"]
JE_COUNTRY = {"datacontext": '"[JournalEntry.GetCountry]"', "parentanchor": "hcenter", "direction": "vertical",
              "ignoreinvisible": "yes"}


def _journal_roots():
    """Every journal-entry root: (file, line, name, body), the top-level
    widgets named widget_je_* in gui/journal_entry_widgets/."""
    out = []
    for path in sorted(glob.glob(os.path.join(JE_WIDGETS, "*.gui"))):
        text = _strip_comments(_read(path))
        for m in re.finditer(r"(?m)^(\w+) = \{", text):
            body = text[m.end():_close(text, m.end() - 1)]
            name = re.search(r'^\tname = "(widget_je_\w+)"', body, re.M)
            if name:
                out.append((os.path.basename(path), text.count("\n", 0, m.start()) + 1, name.group(1), body))
    return out


class MountContextTest(unittest.TestCase):
    """Every mount supplies the Country its sections read (spec § 6.3), the
    player's in every host before another country's panels (F1), so nothing
    changes in game (plan Review Focus 5)."""

    def test_the_frame_supplies_the_player(self):
        body = _strip_comments(_type_body(_read(WIDGETS), "te_system_tab_frame"))
        top = _children(body)
        names = [name for _, name, _ in top]
        self.assertIn("tab_country", names)
        self.assertLess(names.index("tab_country"), names.index("tab_header"),
                        "the header and Banking's readout (tab_before_gate) read it too")
        country = [text for kind, name, text in top if kind == "block" and name == "tab_country"]
        self.assertEqual([c.strip() for c in country], ['datacontext = "[GetPlayer]"'])
        self.assertNotIn("datacontext", [name for kind, name, _ in top if kind == "property"])

    def test_every_window_mount_supplies_the_player(self):
        from scripts.generators import gen_te_systems_window as gen
        generated = _strip_comments(_read(os.path.join(REPO, "gui", "te_systems_window_generated.gui")))
        for t in gen.TABS:
            for name in (f"te_systems_window_{t.key}_tab", f"te_systems_window_{t.key}_tab_wide"):
                with self.subTest(mount=name):
                    at = generated.index(f'name = "{name}"')
                    start = generated.rindex("{", 0, at)
                    own = _children(generated[start + 1:_close(generated, start)])
                    props = [(k, v) for kind, k, v in own if kind == "property"]
                    self.assertIn(("datacontext", '"[GetPlayer]"'), props)

    def test_the_journal_wrapper(self):
        """te_je_country only sets the Country: it adds no spacing, margin,
        size or gate of its own, and anchors as every composer does."""
        body = _strip_comments(_type_body(_read(WIDGETS), "te_je_country"))
        self.assertRegex(_read(WIDGETS), r"(?m)^\ttype te_je_country = flowcontainer \{")
        items = _children(body)
        self.assertEqual({k: v for kind, k, v in items if kind == "property"}, JE_COUNTRY)
        self.assertEqual([k for kind, k, _ in items if kind != "property"], [])

    def test_every_journal_root_supplies_its_country(self):
        """Each root holds its te_* instances inside te_je_country, so the
        root's own visible keeps reading the entry. A non-te_ widget beside it
        (Tax Code's link to the Budget tab) reads no Country and stays out, so
        the root's spacing between them is kept."""
        types = mod_types()
        roots = _journal_roots()
        self.assertEqual(sorted({f for f, _, _, _ in roots}), JOURNAL_ROOT_FILES)
        self.assertGreaterEqual(len(roots), 49)
        for path, line, name, body in roots:
            with self.subTest(root=f"{path}:{line} {name}"):
                items = _children(body)
                direct = [k for kind, k, _ in items if kind == "widget" and k.startswith("te_")]
                self.assertEqual(direct, ["te_je_country"], "the root's te_* instances sit in te_je_country")
                inner = [text for kind, k, text in items if k == "te_je_country"][0]
                wrapped = [(k, text) for kind, k, text in _children(inner)]
                self.assertTrue(wrapped)
                for k, text in wrapped:
                    self.assertTrue(k.startswith("te_"), f"te_je_country holds only the composer: {k}")
                    self.assertEqual(text.strip(), "", f"{k}: the instance as it was, nothing added")
                    # the wrapper anchors as the composer it holds, so the composer sits where it did
                    root = {kk: v for kind, kk, v in _children(types[k].body) if kind == "property"}
                    self.assertEqual(root.get("parentanchor"), JE_COUNTRY["parentanchor"], k)


if __name__ == "__main__":
    unittest.main()
