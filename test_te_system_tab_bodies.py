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

from test_te_systems_window import _close, _read, _strip_comments, _type_body

REPO = os.path.dirname(os.path.abspath(__file__))
WIDGETS = os.path.join(REPO, "gui", "te_system_tab_widgets.gui")
JE_WIDGETS = os.path.join(REPO, "gui", "journal_entry_widgets")

OPEN_JOURNAL = "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]"


def _children(body):
    """The top-level items of a block's body, in order: (kind, name, text).
    kind is "block" for `block "x" {…}`, "widget" for `name = {…}`, and
    "property" for a one-line `key = value`."""
    items = []
    i = 0
    while i < len(body):
        m = re.compile(r'\s*(?:block "(\w+)" \{|(\w+) = \{|(\w+) = ([^\n{]+))').match(body, i)
        if not m or m.end() == i:
            rest = body[i:].strip()
            assert not rest, f"unparsed: {rest[:60]}"
            break
        if m.group(1) or m.group(2):
            end = _close(body, m.end() - 1)
            inner = body[m.end():end]
            if m.group(2) and "\n" not in inner:    # a one-line value: size = { 480 32 }
                items.append(("property", m.group(2), "{" + inner + "}"))
            else:
                items.append(("block" if m.group(1) else "widget", m.group(1) or m.group(2), inner))
            i = end + 1
        else:
            items.append(("property", m.group(3), m.group(4).strip()))
            i = m.end()
    return items


def _gate(sgui):
    return f"GetScriptedGui('{sgui}').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"


def _override(body, name):
    """A blockoverride's contents in a type body, or None when it has none."""
    m = re.search(rf'blockoverride "{name}" \{{', body)
    return None if m is None else body[m.end():_close(body, m.end() - 1)]


def _instances(text):
    """The te_* types a block instances, in order (one level or deeper)."""
    return re.findall(r"^\t+(te_\w+) = \{", text, re.M)


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
        self.assertEqual(blocks, ["tab_header", "tab_before_gate"])
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
                # the header outside the gate, as every tab's is
                head = _override(body, "tab_header")
                self.assertRegex(head, rf'default_header = \{{\s*using = default_list_position\s*'
                                       rf'blockoverride "text" \{{\s*text = "{header}"\s*\}}\s*\}}')
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
        self.assertEqual(parts[0], ("property", "te_sr_window_milestones", "{}"))
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
    # the entry's status text as a Status section, after the overview
    ("te_un_tab_body", os.path.join(JE_WIDGETS, "un_layout_widget.gui"),
     "te_diplomacy_un_tab_sgui", "je_united_nations", "te_un_tab_layout",
     ["te_un_overview_panel", "te_je_status_desc", "te_un_status_sections", "te_un_reference_sections"],
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
                # (`te_x = {}` parses as a one-line value)
                self.assertEqual([n for kind, n, _ in items
                                  if (kind != "property" or n.startswith("te_")) and n != "state"], [body])
                self.assertNotIn("datacontext", [n for n, _ in props])


# What only a tab's vanilla host has: its panel's own datacontext. A body is
# shown by the window too, which has none of them, so none may read them; a
# host's extras that do (the Market panel's map-mode reset, Global Warming's
# other-market view) stay in the host (spec § 3, plan Review Focus 2).
HOST_PANELS = re.compile(r"\bInformationPanel\.|\b(?:MarketPanel|PopsOverviewPanel|BudgetPanel|SocietyPanel|MilitaryPanel)\b")


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


if __name__ == "__main__":
    unittest.main()
