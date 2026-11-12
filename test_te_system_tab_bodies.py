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
import tempfile
import unittest

import functools

from gui_test_helpers import (GUARD, _children, _close, _instances, _read, _strip_comments, _type_body, custom_loc,
                              file_templates, file_types, is_entry_read, load_loc, loc_closure, loc_index, loc_reads,
                              markup_reads, mod_gui_paths, mod_types, open_types, panel_loc_keys, panel_view,
                              personal_text, skipped_overrides, type_closure, ungated_world_reads, unguarded_controls,
                              guard_visible_overrides, mod_templates, _on_guard_widgets, WORLD, READ, ScriptedGuis,
                              NOT_THE_MODS_BLOCK, NOT_THE_MODS_TYPE)
from scripts.generators import gen_te_systems_window as gen

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
        # the entry's modifier strip (empty by default: a body with no entry
        # has no JournalEntry; test_te_entry_modifier_strip.py), then the link
        column = _children(inner[0])
        self.assertEqual([name for kind, name, _ in column if kind == "block"],
                         ["tab_entry", "tab_content", "tab_entry_modifiers", "tab_open_journal"])
        strip = [text for kind, name, text in column if kind == "block" and name == "tab_entry_modifiers"][0]
        self.assertEqual(strip.strip(), "")
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


# The window's journal-entry, seabed and power grids tabs, as the frame's blocks fill them:
# (body type, file, header text, gate, journal entry or None, layout block,
# composers in order, Open Journal Entry's tooltip or None).
WINDOW_BODIES = [
    ("te_gm_tab_body", os.path.join(JE_WIDGETS, "grand_monuments_widget.gui"),
     "te_window_tab_grand_monuments", "te_window_grand_monuments_tab_sgui", "je_grand_monuments",
     "te_gm_tab_layout", ["te_gm_overview_panel", "te_gm_status_sections"],
     "te_window_grand_monuments_open_journal_tt"),
    ("te_ce_tab_body", os.path.join(JE_WIDGETS, "colonial_empire_widget.gui"),
     "je_colonial_empire", "te_window_colonial_empire_tab_sgui", "je_colonial_empire",
     "te_ce_tab_layout", ["te_ce_overview_panel", "te_ce_status_sections", "te_ce_reference_sections"],
     "te_window_colonial_empire_open_journal_tt"),
    ("te_seabed_tab_body", os.path.join(REPO, "gui", "te_seabed_widgets.gui"),
     "te_seabed_tab_header", "te_window_seabed_tab_sgui", None,
     "te_seabed_tab_layout", ["te_seabed_overview_panel", "te_seabed_policy_panel", "te_seabed_basins_panel"],
     None),
    ("te_grid_tab_body", os.path.join(REPO, "gui", "te_grid_widgets.gui"),
     "te_grid_tab_header", "te_window_power_grids_tab_sgui", None,
     "te_grid_tab_layout", ["te_grid_overview_panel", "te_grid_grids_panel", "te_grid_stations_panel"],
     None),
]


# Window bodies that open without their entry too (owner, 2026-11-03), on a
# readout in tab_before_gate: (its gate, the type it shows).
READOUTS = {"te_ce_tab_body": ("te_window_colonial_empire_readout_sgui", "te_ce_readout")}


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
                                       rf'(?:te_jmap_\w+_map_button = \{{\}}\s*)?'    # its map (journal_map_modes.md)
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
                # the gate is the body's one visible, but for the "?"'s
                # observer gate, once, on the button in the header
                # (test_te_help_pages.py): any other visible, the header's
                # included, still fails
                observer = 'visible = "[Not( GetMetaPlayer.IsObserver )]"'
                self.assertEqual(body.count(observer), head.count(observer), "the observer gate is the header's")
                self.assertLessEqual(head.count(observer), 1)
                rest = body.replace(_override(body, "tab_gate"), "").replace(observer, "", 1)
                if name in READOUTS:
                    # the tab without the entry, before the gate: its own gate,
                    # never true with the entry's (Banking's #805 shape)
                    gate, readout = READOUTS[name]
                    before = _override(body, "tab_before_gate")
                    self.assertIn(f'visible = "[{_gate(gate)}]"', before)
                    self.assertIn(f"{readout} = {{}}", before)
                    self.assertNotIn("JournalEntry", before)
                    rest = rest.replace(before, "")
                self.assertNotIn("visible", rest)

    def test_the_space_race_body(self):
        """Nine entries, each its own frame (te_sr_window_milestones, generated),
        then the tab's own sections, which read no entry, all in the layout
        block a wide mount overrides. How the Space Race Works, once after
        them, is the Help page each frame's header "?" opens."""
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
        self.assertEqual([name for _, name, _ in parts], ["te_sr_window_milestones", "flowcontainer"])
        self.assertEqual(parts[0], ("widget", "te_sr_window_milestones", ""))
        for (_, _, part), name, spacing, sections in (
                (parts[1], "te_systems_window_space_race_summary", "4", ["te_sr_sec_powers", "te_sr_sec_orbit"]),):
            with self.subTest(part=name):
                own = dict((n, v) for kind, n, v in _children(part) if kind == "property")
                self.assertEqual(own["name"], f'"{name}"')
                self.assertEqual(own["visible"], f'"[{_gate("te_window_space_race_tab_sgui").replace("GetPlayer.MakeScope", "Country.MakeScope")}]"')
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
     ["te_st_res_overview_panel", "te_st_res_status_sections"],
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
     ["te_nuclear_overview_panel", "te_nuclear_sec_programme", "te_nuclear_programme_bar", "te_nuclear_status_sections"],
     "te_military_nuclear_open_journal_tt", None),
    ("te_covert_tab_body", os.path.join(JE_WIDGETS, "covert_operations_widget.gui"),
     "te_military_covert_tab_sgui", "je_covert_warfare", "te_covert_tab_layout",
     ["te_covert_overview_panel", "te_covert_status_sections"],
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
# Journal-entry roots on a contextless entry, which has no Country (JournalEntry.GetCountry would be null): they read
# the player through scripted GUIs instead, as vanilla's contextless great_game_widgets.gui reads AccessPlayer. The
# Map Room's picks (docs/systems/mod_systems/journal_map_modes.md).
CONTEXTLESS_ROOT_FILES = ["te_map_room_widget.gui"]
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
        the root's spacing between them is kept; so does an overview root's
        "?" (te_help_row, first), which reads no Country either
        (test_te_help_pages.py)."""
        types = mod_types()
        roots = _journal_roots()
        self.assertEqual(sorted({f for f, _, _, _ in roots}), sorted(JOURNAL_ROOT_FILES + CONTEXTLESS_ROOT_FILES))
        roots = [r for r in roots if r[0] not in CONTEXTLESS_ROOT_FILES]
        self.assertGreaterEqual(len(roots), 42)
        for path, line, name, body in roots:
            with self.subTest(root=f"{path}:{line} {name}"):
                items = _children(body)
                direct = [k for kind, k, _ in items if kind == "widget" and k.startswith("te_")]
                if direct[:1] == ["te_help_row"]:
                    direct = direct[1:]
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



# --- What another country's panel draws (spec §§ 6.3, 6.5, 7.1; plan Review Focus 3 and 4) --------------------------

# The tabs another country's panel may show (National Info, PR F1): each Tab with public=True in
# gen_te_systems_window.TABS. BindingTest and GuardTest run over what National Info's mount for another country draws
# (gen.ni_types: the wide layout, Tab.wide, and the readout a tab opens on without its entry, Tab.readout), every type
# it draws all the way down (gui_test_helpers.type_closure over the mod's own GUI files), and the loc that reaches.
PUBLIC = [t for t in gen.TABS if t.public]

# The systems National Info is to show (spec § 6.4) whose panels aren't bound yet: off the binding tests until their
# PR binds them. A system's PR sets its Tab's public=True and deletes its own `"key",` line here, and only that line:
# keep the blank lines, or two parallel PRs' deletions touch and conflict. One still here that passes every check
# fails test_unbound_is_honest, so this list only shrinks. A set() call, not a {...} literal, so it stays a set when
# the last system goes.
UNBOUND = set([








])

# The systems National Info doesn't show in this work (spec § 6.4): never public.
PRIVATE = {
    "budget_breakdown",
    "strategic_reserve",
    "global_warming",
    "united_nations",
    "covert_warfare",
}

# A world read in loc (spec § 6.7): a key a public panel renders that reads the player's copy of what is the same
# for every country (a world list written for players only), with why. Markup marks its world reads with a
# `# world: <why>` line over the read instead. An entry read is never a world read. Each system's PR adds its keys
# under its own heading, one a line, in order, so parallel PRs merge cleanly. A key that more than one system's
# panel reaches goes under Shared, once (two PRs adding it under their own headings would repeat a dict key, which
# ruff's F601 fails on main): test_a_shared_world_key_is_under_shared. A key no public or unbound panel renders, or
# that reads no player, fails test_world_loc_is_live. te_rebind_country.py names the other tabs that reach a key.
WORLD_LOC = {
    # Shared: keys more than one system's panel reaches.
    "te_hist_tt_markers": "a chart bar's tooltip has only the bar's context (gotcha #24), and the scripted GUI it "
                          "asks roots on GetPlayer only to have a root: its handler reads scope:te_hist_sample",

    # Demographics: none.

    # Nation (F2)
    "state_birth_limit_relief_add": "a modifier type's name, which the engine renders wherever it names the type, "
                                    "mostly with no Country in context (breakdowns, law tooltips, loading tips): "
                                    "GetPlayer is a root, behind vanilla's GetPlayer.IsValid guard, only to ask a "
                                    "game rule, the same for every country (te_demog_custom_loc.txt's header)",
    "state_birth_limit_relief_add_desc": "its description: as state_birth_limit_relief_add",
    "state_demog_womens_work_ratio_add": "a modifier type's name: as state_birth_limit_relief_add",
    "state_demog_womens_work_ratio_add_desc": "its description: as state_birth_limit_relief_add",
    "state_desired_fertility_mult": "a modifier type's name: as state_birth_limit_relief_add",
    "state_desired_fertility_mult_desc": "its description: as state_birth_limit_relief_add",
    "state_fertility_means_add": "a modifier type's name: as state_birth_limit_relief_add",
    "state_fertility_means_add_desc": "its description: as state_birth_limit_relief_add",
    "state_maternal_mortality_mult": "a modifier type's name: as state_birth_limit_relief_add",
    "state_maternal_mortality_mult_desc": "its description: as state_birth_limit_relief_add",
    "state_means_literacy_add": "a modifier type's name: as state_birth_limit_relief_add",
    "state_means_literacy_add_desc": "its description: as state_birth_limit_relief_add",
    "state_sex_ratio_at_birth_add": "a modifier type's name: as state_birth_limit_relief_add",
    "state_sex_ratio_at_birth_add_desc": "its description: as state_birth_limit_relief_add",
    "state_urban_fertility_relief_add": "a modifier type's name: as state_birth_limit_relief_add",
    "state_urban_fertility_relief_add_desc": "its description: as state_birth_limit_relief_add",
    "te_demog_census_off_name_ingame": "those names' custom loc, which asks the Demographics rule "
                                       "(te_demog_cohorts_run)",
    "te_demog_census_off_desc_ingame": "those descriptions' custom loc, which asks the Demographics rule "
                                       "(te_demog_cohorts_run)",
    "te_demog_wf_womens_name_ingame": "a name's custom loc, which asks the Demographics rule (te_demog_effects_run)",
    "te_demog_wf_womens_desc_ingame": "a description's custom loc, which asks the Demographics rule "
                                      "(te_demog_effects_run)",
    "te_demog_wf_womens_desc_full": "that description's text under the rule: a constant "
                                    "(te_demog_k_womens_work_full), read through GetPlayer for a root",

    # Banking (F2)

    # Tax Code (F2)

    # Grand Monuments (F3)

    # Colonial Empire (F3)

    # Seabed (F3)

    # Cultural Hegemony (F4)

    # Nuclear Weapons (F4)

    # Space Race (F5)
}

HOW_TO_BIND = (
    "Each line: file:line, the type (or loc key), the read, the line. Bind each: run "
    "`python3 scripts/analysis/te_rebind_country.py {key}` for the list by class, and --write for the mechanical "
    "reads (JournalEntry.GetCountry. and GetPlayer. to Country.); put an entry-only part or a control under "
    "`using = te_own_country_only` (on a wrapper where the widget has its own visible; gui/te_system_tab_widgets.gui); "
    "a read of the player's copy of what is the same for every country takes a `# world: <why>` line over it "
    "(a loc key: an entry in WORLD_LOC, under Shared if another system's panel reaches it too). Then set its Tab's "
    "public=True and delete only its `\"{key}\",` line from UNBOUND, keeping the blank lines.")


def _report(findings, key, limit=60):
    lines = [str(f) for f in findings[:limit]]
    if len(findings) > limit:
        lines.append(f"... and {len(findings) - limit} more")
    return "\n" + "\n".join(lines) + "\n" + HOW_TO_BIND.format(key=key)


def _candidates():
    """The tabs another country's panel shows or will: public, and UNBOUND."""
    return sorted({t.key for t in PUBLIC} | UNBOUND)


def _world_loc_headings():
    """Each WORLD_LOC key and the heading comment it sits under, from this
    file's source."""
    src = _read(os.path.abspath(__file__))
    block = src[src.index("\nWORLD_LOC = {"):]
    block = block[:block.index("\n}\n")]
    heads, head = {}, None
    for line in block.split("\n"):
        m = re.match(r"\s*#\s*(.+)", line)
        if m:
            head = m.group(1).strip()
            continue
        m = re.match(r'\s*"([\w.\-]+)"\s*:', line)
        if m:
            heads[m.group(1)] = head
    return heads


@functools.lru_cache(maxsize=None)
def _mod():
    """The mod's types, one dict for the tests below: panel_view keeps a view
    by the dict it was drawn from (mod_types() gives a new one each call)."""
    return mod_types()


@functools.lru_cache(maxsize=None)
def _panel(key):
    """What tab `key`'s panel shows another country (its wide layout, and its
    readout where it has one): its markup reads, its loc reads, its controls
    and its loc keys."""
    tab = next(t for t in gen.TABS if t.key == key)
    types, loc = _mod(), load_loc()
    roots = gen.ni_types(tab)
    keys = panel_loc_keys(roots, types, loc)
    markup = [f for f in markup_reads(roots, types) if not f.world or is_entry_read(f.what)]
    reads = [f for f in loc_reads(keys, loc_index()) if f.where not in WORLD_LOC or is_entry_read(f.what)]
    return {"markup": markup, "loc": reads, "controls": unguarded_controls(roots, types),
            "text": personal_text(keys, loc), "keys": keys, "types": type_closure(roots, types)}


class BindingTest(unittest.TestCase):
    """A public tab's sections read the shown country, Country, and nothing
    else (spec § 7.1): no JournalEntry and no player read outside
    te_own_country_only, but a marked world read."""

    def test_a_public_tab_is_bound(self):
        self.assertTrue(PUBLIC, "Demographics at least")
        for t in PUBLIC:
            with self.subTest(tab=t.key):
                self.assertNotIn(t.key, UNBOUND, f"{t.key} is public, so bound: take it off UNBOUND")
                panel = _panel(t.key)
                # the walk reaches the sections and their loc (guard the guard)
                self.assertGreater(len(panel["types"]), 5)
                self.assertGreater(len(panel["keys"]), 20)

    def test_no_entry_or_player_read(self):
        for t in PUBLIC:
            with self.subTest(tab=t.key):
                found = _panel(t.key)["markup"]
                if found:
                    self.fail(_report(found, t.key))

    def test_the_loc_reads_no_entry_or_player(self):
        for t in PUBLIC:
            with self.subTest(tab=t.key):
                found = _panel(t.key)["loc"]
                if found:
                    self.fail(_report(found, t.key))

    def test_the_text_is_not_the_players(self):
        """Another country's panel shows the same text, so none of it says
        "our" or "you" (spec § 6.8): a label goes neutral, and a sentence that
        needs its subject takes SelectLocalization( Country.IsLocalPlayer,
        '<the player's>', '<the country's>' ), whose first branch is left out
        here. (The census test's rule, moved here in PR F0.)"""
        for t in PUBLIC:
            with self.subTest(tab=t.key):
                text = _panel(t.key)["text"]
                if text:
                    self.fail("\n" + "\n".join(f"{k}: {' '.join(v.split())[:140]}" for k, v in text.items()))

    def test_every_world_line_marks_a_player_read(self):
        """A `# world:` line sits directly over a line that reads the player,
        and never over an entry read, which another country's panel can't
        reach: a stale marker can't hide a read that moved. None is left on
        main since the charts' date reads moved to Country (GetPlayer is no
        country for an observer); MutationTest holds the rule on a fixture."""
        for path in mod_gui_paths():
            lines = _read(os.path.join(REPO, path)).split("\n")
            for i, line in enumerate(lines):
                if not WORLD.match(line):
                    continue
                below = _strip_comments(lines[i + 1]) if i + 1 < len(lines) else ""
                reads = READ.findall(below)
                with self.subTest(at=f"{path}:{i + 1}"):
                    self.assertTrue(reads, f"{path}:{i + 1}: a world marker over a line that reads no player")
                    self.assertFalse([r for r in reads if is_entry_read(r)],
                                     f"{path}:{i + 1}: an entry read is never a world read")

    def test_world_loc_is_live(self):
        """A WORLD_LOC key is one a public panel, or one still to bind, renders,
        and it reads the player, never the entry."""
        index = loc_index()
        reached = set().union(*(_panel(key)["keys"] for key in _candidates()))
        for key, why in WORLD_LOC.items():
            with self.subTest(key=key):
                self.assertTrue(why.strip(), "say why")
                self.assertIn(key, reached, f"{key}: no public or unbound panel renders it")
                reads = READ.findall(index[key][0])
                self.assertTrue(reads and not [r for r in reads if is_entry_read(r)],
                                f"{key}: a world key reads the player, never the entry")

    def test_a_shared_world_key_is_under_shared(self):
        """A WORLD_LOC key more than one system's panel reaches sits under the
        Shared heading, so two systems' PRs can't each add it."""
        heads = _world_loc_headings()
        for key in WORLD_LOC:
            tabs = [t for t in _candidates() if key in _panel(t)["keys"]]
            with self.subTest(key=key):
                self.assertIn(key, heads, "a WORLD_LOC key sits under a heading comment")
                if len(tabs) > 1:
                    self.assertTrue(heads[key].startswith("Shared"),
                                    f"{key}: {', '.join(tabs)} reach it, so it goes under Shared, not {heads[key]!r}")

    def test_the_walk_reaches_a_scripted_tooltips_lines(self):
        """The lines a scripted GUI's tooltip prints are the panel's text too
        (#1361): Seabed's Free hover (te_seabed_build_in_sgui's effect, a
        scripted effect's `te_seabed_build_in_head_$B$`), Nuclear Weapons'
        taboo breakdown, the Colonial Empire readout's unlock checklist (an
        is_valid), and the Space Race's strike record, which a loc key asks
        for. Guard the guard: a walk that stopped following them would pass
        every other test here."""
        for tab, key in (("seabed", "te_seabed_build_in_head_pacific"), ("seabed", "te_seabed_build_in_state_1"),
                         ("nuclear_weapons", "nd_taboo_bd_tradition"), ("colonial_empire", "ce_unlock_colonies_tt"),
                         ("space_race", "te_asat_record_none")):
            with self.subTest(tab=tab, key=key):
                self.assertIn(key, _panel(tab)["keys"])

    def test_the_walk_reaches_a_readout(self):
        """A tab that opens without its entry on a readout (Tab.readout) has
        it walked too: National Info's mount for another country draws it
        under the readout's gate, above the wide composer under the entry's
        gate, as the body's frame does (test_national_info.py's MountTest)."""
        for t in gen.TABS:
            if t.readout and t.key in _candidates():
                with self.subTest(tab=t.key):
                    self.assertIn(t.readout.panel, _panel(t.key)["types"])


class GuardTest(unittest.TestCase):
    """No control for another country (spec § 6.5): every scripted GUI's
    Execute in a public tab sits under te_own_country_only, and so does an
    opener of a popup that holds controls (the Space Race's pickers). The "?",
    the Help links and the chart buttons open pages that only read."""

    def test_every_control_is_the_players(self):
        for t in PUBLIC:
            with self.subTest(tab=t.key):
                found = _panel(t.key)["controls"]
                if found:
                    self.fail(_report(found, t.key))


class SkippedOverrideTest(unittest.TestCase):
    """A blockoverride into a guarded block is read as the player's own while
    every block of its name that the mod's types declare is one another
    country's panel doesn't draw (gui_test_helpers._dead_overrides). The walk
    doesn't read vanilla's types, so a vanilla type inside the instanced one
    with a block of the same name would be missed, and the override read as
    not drawn when it is. Vanilla's files are not in the repo; the copies of
    its markup under gui/ are, and no name skipped today is one of theirs."""

    def test_no_skipped_override_names_a_block_a_vanilla_copy_declares(self):
        types = _mod()
        skipped = {}
        for t in PUBLIC:
            for name, block in skipped_overrides(panel_view(gen.ni_types(t), types), types):
                skipped.setdefault(block, f"{t.key}: {name}")
        # guard the guard: Banking's action buttons, the Space Race's exact progress
        for block in ("enable_action", "sr_progress_tooltip"):
            self.assertIn(block, skipped)
        mod = set(mod_gui_paths())
        copies = [p for p in sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True))
                  if os.path.relpath(p, REPO) not in mod]
        self.assertGreater(len(copies), 20)
        for path in copies:
            declared = set(re.findall(r'\bblock\s+"(\w+)"', _strip_comments(_read(path))))
            for block in sorted(declared & set(skipped)):
                with self.subTest(file=os.path.relpath(path, REPO), block=block):
                    self.fail(f'{skipped[block]} overrides "{block}" into a guarded block, and this copy of vanilla '
                              f"markup declares a block of that name too: if the instanced type draws the vanilla "
                              f"type, the override is drawn there. Rename the mod's block.")


    def test_no_override_puts_a_visible_on_a_guards_widget(self):
        """The seal the guard rests on. te_own_country_only is a `visible`,
        and a second `visible` on the same widget replaces it (gotcha #17).
        A blockoverride reaches a guard's widget from any instance level, so
        this goes by name: no blockoverride anywhere under gui/ of a block
        that sits on a guard's widget (at its own level, or at the root of
        the mod type it instances) sets a `visible`, uses a template or holds
        another blockoverride there. A guard written in a blockoverride sits
        on its block's widget (the Colonial Empire's down_action), one in a
        block's default on the widget around the block. Where the mod's types
        can't say which widget a block is on (a vanilla type's), no
        blockoverride written on the guard's own widget does either. The
        binding tests read a guard as hiding what is written inside the
        widget (or the override) it is written in, and follow such a
        `visible` only from an instance's own overrides, so they are right
        about the rest only while this holds: don't drop it as covered
        elsewhere."""
        types, templates = _mod(), mod_templates()
        names, _, unread = _on_guard_widgets(types, templates)
        # guard the guard: the Space Race's exact bar row (the guard on an instance), Seabed's chevron (on a button),
        # the Colonial Empire's steppers (the guard in an override), and the instances of vanilla's types that carry it
        for block in ("row_tooltip", "basin_toggle", "down_action", "up_action"):
            self.assertIn(block, names)
        self.assertGreaterEqual(sum(1 for _, _, _, every in unread if every), 6)
        texts = {os.path.relpath(p, REPO): _strip_comments(_read(p))
                 for p in glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)}
        found = guard_visible_overrides(types, templates, texts)
        if found:
            self.fail("\n" + "\n".join(
                f'{path}:{line}  {"block" if why.startswith("its default") else "blockoverride"} "{block}" {why}; '
                f"the guarded widget is at {where[0]}:{where[1]} ({where[2]})" for path, line, block, why, where in found)
                + "\nThat would replace te_own_country_only on the widget, and another country would see what it "
                  "holds. Put what the override adds in a child widget of its own (a `visible` there is the "
                  "child's), or move the guard to a container around the widget.")


class ObserverTest(unittest.TestCase):
    """National Info opens to an observer, who has no GetPlayer, and
    Country.IsLocalPlayer is false for every country one opens: an observer
    sees another country's panel. A `# world:` read there (the player's copy
    of what is the same for every country, which BindingTest lets through)
    logs a null-country line every frame it is evaluated, so each sits under
    an observer gate (gui_modding_guide.md, "An observer has no GetPlayer"):
    Not( GetMetaPlayer.IsObserver ), or GetPlayer.IsValid, first in the
    `visible` of a widget around the read. One check for every public tab
    (#1368); MutationTest holds it on a fixture."""

    def test_every_world_read_is_gated_for_an_observer(self):
        types = _mod()
        for t in PUBLIC:
            with self.subTest(tab=t.key):
                found = ungated_world_reads(gen.ni_types(t), types)
                if found:
                    self.fail("\n" + "\n".join(str(f) for f in found) + "\nA `# world:` read with no observer gate: "
                              "put it in a container with `visible = \"[Not( GetMetaPlayer.IsObserver )]\"`, or put "
                              "that test first in an And in the read's own `visible`.")


class PublicTest(unittest.TestCase):
    """The public flags and UNBOUND (one line each per system, so the
    systems' parallel PRs merge cleanly)."""

    def test_every_tab_is_public_unbound_or_private(self):
        keys = [t.key for t in gen.TABS]
        public = {t.key for t in PUBLIC}
        for key in keys:
            with self.subTest(tab=key):
                where = [name for name, group in (("public", public), ("UNBOUND", UNBOUND), ("PRIVATE", PRIVATE))
                         if key in group]
                self.assertEqual(len(where), 1, f"{key} is {where or 'none of them'}: a shown system is public "
                                                f"once bound and on UNBOUND until then; a private one is neither")
        self.assertLessEqual(UNBOUND | PRIVATE, set(keys), "a name that is no tab")
        self.assertEqual(public, {"demographics"} | (set(keys) - UNBOUND - PRIVATE))

    def test_unbound_is_honest(self):
        """A system still on UNBOUND still draws something another country
        mustn't see; once it passes every check, it comes off the list."""
        for key in sorted(UNBOUND):
            with self.subTest(tab=key):
                panel = _panel(key)
                left = len(panel["markup"]) + len(panel["loc"]) + len(panel["controls"]) + len(panel["text"])
                self.assertGreater(left, 0, f"{key} passes BindingTest and GuardTest: set its Tab's public=True in "
                                            f"gen_te_systems_window.TABS and take it off UNBOUND")


# A panel's fixture: a wide layout, a section, a control row and a popup, as test_unbound_is_honest's mutation
# checks plant them (the files' own runs are in the PR).
FIXTURE = """types fixture
{
	type fx_wide = flowcontainer {
		fx_section = {}
		widget = {
			using = te_own_country_only
			fx_controls = {}
		}
	}
	type fx_section = flowcontainer {
		textbox = { text = "fx_label" }
		@READ@
	}
	type fx_controls = flowcontainer {
		button = { onclick = "[GetScriptedGui('x').Execute( GuiScope.SetRoot( Country.MakeScope ).End )]" }
	}
	type fx_picker_popup = te_ui_popup {
		blockoverride "popup_visible" {
			visible = "[GetVariableSystem.HasValue('te_popup', 'fx_picker')]"
		}
		blockoverride "popup_list" {
			fx_controls = {}
		}
	}
	type fx_help_popup = te_ui_popup {
		blockoverride "popup_visible" {
			visible = "[GetVariableSystem.HasValue('te_popup', 'fx_help')]"
		}
	}
}
"""


def _fixture(read):
    return file_types(FIXTURE.replace("@READ@", read), "fixture.gui")


class MutationTest(unittest.TestCase):
    """The checks BindingTest and GuardTest make, each on a planted read or
    control: each fails where it should and passes where it shouldn't."""

    def test_an_entry_read_fails(self):
        found = markup_reads({"fx_wide"}, _fixture('textbox = { text = "[JournalEntry.GetCountry.GetName]" }'))
        self.assertEqual([(f.where, f.what, f.world) for f in found], [("fx_section", "JournalEntry.GetCountry", False)])
        self.assertEqual(found[0].line, 12)

    def test_a_player_read_fails_unless_a_world_line_marks_it(self):
        bare = markup_reads({"fx_wide"}, _fixture("visible = \"[GetPlayer.MakeScope.ScriptValue('y')]\""))
        self.assertEqual([(f.what, f.world) for f in bare], [("GetPlayer", False)])
        marked = markup_reads({"fx_wide"}, _fixture("# world: the year\n\t\tvisible = \"[GetPlayer.MakeScope.ScriptValue('y')]\""))
        self.assertEqual([(f.what, f.world) for f in marked], [("GetPlayer", True)])
        entry = markup_reads({"fx_wide"}, _fixture("# world: no\n\t\tvisible = \"[JournalEntry.IsActive]\""))
        self.assertTrue(entry[0].world and is_entry_read(entry[0].what), "BindingTest fails it all the same")
        self.assertTrue(is_entry_read("GetPlayerJournalEntry"))
        own = markup_reads({"fx_wide"}, _fixture("widget = {\n\t\t\tusing = te_own_country_only\n"
                                                 "\t\t\tvisible = \"[GetPlayer.IsAtWar]\"\n\t\t}"))
        self.assertEqual(own, [], "a read under the guard is the player's own")

    def test_an_unguarded_control_fails(self):
        self.assertEqual(unguarded_controls({"fx_wide"}, _fixture("")), [], "fx_controls sits under the guard")
        found = unguarded_controls({"fx_wide"}, _fixture("fx_controls = {}"))
        self.assertEqual([(f.where, f.what) for f in found], [("fx_controls", "Execute")])

    def test_an_opener_of_controls_fails(self):
        found = unguarded_controls({"fx_wide"}, _fixture(
            "button = { onclick = \"[GetVariableSystem.Set('te_popup', 'fx_picker')]\" }"))
        self.assertEqual(len(found), 1)
        self.assertIn("fx_picker, whose popup holds controls", found[0].what)
        self.assertEqual(unguarded_controls({"fx_wide"}, _fixture(
            "button = { onclick = \"[GetVariableSystem.Set('te_popup', 'fx_help')]\" }")), [], "a page only reads")
        self.assertIn("no popup shows on", unguarded_controls({"fx_wide"}, _fixture(
            "button = { onclick = \"[GetVariableSystem.Set('te_popup', 'fx_gone')]\" }"))[0].what)

    def test_the_players_own_text_is_left_out(self):
        loc = {"fx_label": "Arsenal", "fx_mine": "Our arsenal", "fx_theirs": "The country's arsenal",
               "fx_says": "We hold [GetPlayer.GetName]"}
        types = _fixture("textbox = { text = \"[SelectLocalization( Country.IsLocalPlayer, 'fx_mine', 'fx_theirs' )]\" }")
        keys = panel_loc_keys({"fx_wide"}, types, loc)
        self.assertEqual(keys, {"fx_label", "fx_theirs"})
        self.assertEqual(personal_text(keys | {"fx_says"}, loc), {"fx_says": "We hold  "})

    SCRIPT = (("scripted_guis", "fx_hover_sgui = {\n\tis_valid = { custom_tooltip = fx_why }\n\teffect = {\n"
                                "\t\tcustom_tooltip = fx_says\n\t\tfx_lines = { B = pacific }\n\t}\n}\n"),
              ("scripted_effects", "fx_lines = {\n\tcustom_tooltip_no_bullet = fx_head_$B$\n}\n"))
    HOVER = "GetScriptedGui('fx_hover_sgui').ExecuteTooltip( GuiScope.SetRoot( Country.MakeScope ).End )"

    def test_a_scripted_tooltips_lines_are_the_panels_text(self):
        """A hover that asks a scripted GUI for its tooltip prints the
        script's custom_tooltip keys for whoever looks (#1361): they are the
        panel's keys, so a player or entry read in one fails BindingTest, and
        "we" in one fails the text check. Under the guard, or in the player's
        own branch of a SelectLocalization, the hover is the player's."""
        with tempfile.TemporaryDirectory() as tmp:
            for folder, text in self.SCRIPT:
                os.makedirs(os.path.join(tmp, "common", folder))
                with open(os.path.join(tmp, "common", folder, "fx.txt"), "w", encoding="utf-8-sig") as fh:
                    fh.write(text)
            scripted = ScriptedGuis(tmp)
        loc = {"fx_label": "Arsenal", "fx_says": "We hold [GetPlayer.GetName]", "fx_why": "Why not",
               "fx_head_pacific": "[JournalEntry.GetCountry.GetName]'s basin", "fx_asks": "Header\n[%s]" % self.HOVER}

        def keys(read):
            return panel_loc_keys({"fx_wide"}, _fixture(read), loc, scripted=scripted)

        hover = 'textbox = { tooltip = "[%s]" }' % self.HOVER
        printed = {"fx_label", "fx_says", "fx_head_pacific"}
        self.assertEqual(keys(hover), printed)
        index = {k: (v, "fx_l_english.yml", 1) for k, v in loc.items()}
        self.assertEqual(sorted((f.where, f.what) for f in loc_reads(keys(hover), index)),
                         [("fx_head_pacific", "JournalEntry.GetCountry"), ("fx_says", "GetPlayer")])
        self.assertEqual(list(personal_text(keys(hover), loc)), ["fx_says"])
        self.assertEqual(panel_loc_keys({"fx_wide"}, _fixture(hover), loc, scripted=ScriptedGuis(None)), {"fx_label"},
                         "what the walk saw before")
        # each function its own block; a key that asks; the scripted GUI in context
        self.assertEqual(keys(hover.replace("ExecuteTooltip", "IsValidTooltip")), {"fx_label", "fx_why"})
        self.assertEqual(keys('textbox = { tooltip = "fx_asks" }'), printed | {"fx_asks"})
        self.assertEqual(keys("widget = {\n\t\t\tdatacontext = \"[GetScriptedGui('fx_hover_sgui')]\"\n\t\t\ttextbox = { "
                              'tooltip = "[ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( Country.MakeScope ).End )]" }'
                              "\n\t\t}"), printed)
        # the player's own
        self.assertEqual(keys("widget = {\n\t\t\tusing = te_own_country_only\n\t\t\t%s\n\t\t}" % hover), {"fx_label"})
        self.assertEqual(keys('textbox = { tooltip = "[SelectLocalization( Country.IsLocalPlayer, %s, \'fx_label\' )]" }'
                              % self.HOVER), {"fx_label"})
        self.assertEqual(keys('textbox = { tooltip = "[SelectLocalization( Country.IsAtWar, %s, \'fx_label\' )]" }'
                              % self.HOVER), printed)

    FRAME = """types fixture
{
	type fx_wide = flowcontainer {
		fx_frame = {
			blockoverride "tab_country" {}
		}
		@SECOND@
	}
	type fx_frame = flowcontainer {
		block "tab_country" {
			datacontext = "[GetPlayer]"
		}
		block "tab_open" {
			button = { onclick = "[GetScriptedGui('x').Execute( GuiScope.SetRoot( Country.MakeScope ).End )]" }
		}
	}
	type fx_derived = fx_frame {
		blockoverride "tab_country" {}
	}
}
"""

    def frame(self, second=""):
        return file_types(self.FRAME.replace("@SECOND@", second), "fixture.gui")

    def test_an_overridden_block_default_is_not_drawn(self):
        """A block default every place that draws the type overrides is not
        drawn there (the frame's tab_country under the Space Race's
        milestones); one place that leaves it draws it."""
        self.assertEqual(markup_reads({"fx_wide"}, self.frame()), [], "the only instance overrides it")
        self.assertEqual(markup_reads({"fx_wide"}, self.frame("fx_derived = {}")), [],
                         "a derived type that overrides it at its root")
        found = markup_reads({"fx_wide"}, self.frame("fx_frame = {}"))
        self.assertEqual([(f.where, f.what) for f in found], [("fx_frame", "GetPlayer")], "a second, plain instance")
        self.assertEqual([f.what for f in unguarded_controls({"fx_wide"}, self.frame())], ["Execute"],
                         "a block no instance overrides is still drawn")

    ROW = """types fixture
{
	type fx_wide = flowcontainer {
		fx_row = {
			blockoverride "row_label" { text = "fx_label" }
			blockoverride "row_button" {
				onclick = "[GetScriptedGui('x').Execute( GuiScope.SetRoot( Country.MakeScope ).End )]"
				enabled = "[JournalEntry.IsActive]"
				tooltip = "fx_mine"
				@HELD@
			}
			@INSTANCE@
		}
		@SECOND@
	}
	type fx_row = flowcontainer {
		textbox = { block "row_label" {} }
		widget = {
			@GUARD@
			button = { block "row_button" {} }
			@GUARDED@
		}
		@OPEN@
	}
	type fx_derived = fx_row {
		blockoverride "row_button" {
			onclick = "[GetScriptedGui('y').Execute( GuiScope.SetRoot( Country.MakeScope ).End )]"
		}
		@DERIVED@
	}
	type fx_slot = widget {
		block "row_slot" {}
	}
	type fx_dslot = fx_slot {
	}
	type fx_gslot = widget {
		using = te_own_country_only
		block "row_slot" {}
	}
	type fx_gd = fx_gslot {
		@GD@
	}
	type fx_inner = flowcontainer {
		widget = {
			using = te_own_country_only
			block "row_y" {}
		}
	}
	type fx_gcell = flowcontainer {
		widget = {
			using = te_own_country_only
			block "row_shown" {}
			button = { block "row_button" {} }
		}
	}
	type fx_mid = flowcontainer {
		fx_row = {
			blockoverride "row_button" {
				onclick = "[GetScriptedGui('m').Execute( GuiScope.SetRoot( Country.MakeScope ).End )]"
			}
			blockoverride "row_label" { block "row_extra" {} }
		}
	}
	type fx_cell = flowcontainer {
		button = { block "row_button" {} }
	}
	type fx_held = flowcontainer {
		textbox = { text = "fx_held_label" }
	}
}
"""

    ROW_TEMPLATES = file_templates('template fx_tmpl {\n\tblock "row_button" {}\n}\n', "fixture.gui")

    def row(self, guard="using = te_own_country_only", **parts):
        text = self.ROW.replace("@GUARD@", guard)
        for part in ("HELD", "INSTANCE", "SECOND", "GUARDED", "OPEN", "DERIVED", "GD"):
            text = text.replace(f"@{part}@", parts.get(part.lower(), ""))
        return file_types(text, "fixture.gui")

    def row_draws(self, types):
        """What another country's panel draws of the row fixture: its
        controls, its reads and its loc keys."""
        loc = {"fx_label": "Arsenal", "fx_mine": "Our arsenal"}
        return ([(f.where, f.what) for f in unguarded_controls({"fx_wide"}, types, self.ROW_TEMPLATES)],
                [(f.where, f.what) for f in markup_reads({"fx_wide"}, types, self.ROW_TEMPLATES)],
                panel_loc_keys({"fx_wide"}, types, loc, self.ROW_TEMPLATES))

    def test_an_override_into_a_guarded_block_is_the_players(self):
        """An instance's blockoverride lands where its block is. One whose
        only block sits under te_own_country_only is guarded as if the guard
        were written around it (#1363), and its text is not another country's
        (#1368); with the type's guard removed it is drawn again."""
        self.assertEqual(self.row_draws(self.row()), ([], [], {"fx_label"}))
        self.assertEqual(self.row_draws(self.row(guard="")),
                         ([("fx_wide", "Execute")], [("fx_wide", "JournalEntry.IsActive")], {"fx_label", "fx_mine"}))
        # a derived type's override at its root, the same
        self.assertEqual(self.row_draws(self.row(second="fx_derived = {}"))[0], [])
        self.assertEqual(self.row_draws(self.row(guard="", second="fx_derived = {}"))[0],
                         [("fx_derived", "Execute"), ("fx_wide", "Execute")])

    def test_an_override_that_fills_a_drawn_block_is_drawn(self):
        """One block of the name outside the guard keeps the override drawn:
        in the type itself, or in a type it draws (an override reaches the
        blocks of nested types). A nested type under the guard draws none."""
        mine = ([], [], {"fx_label"})
        self.assertEqual(self.row_draws(self.row(open='button = { block "row_button" {} }'))[0],
                         [("fx_wide", "Execute")], "a second block of the name, unguarded")
        self.assertEqual(self.row_draws(self.row(open="fx_cell = {}"))[0], [("fx_wide", "Execute")],
                         "a nested type's block, unguarded")
        self.assertEqual(self.row_draws(self.row(guarded="fx_cell = {}")), mine, "a nested type's, under the guard")
        # the instance's own contents declare the block: not known to be the type's guarded one alone
        self.assertEqual(self.row_draws(self.row(instance='blockoverride "row_label" { block "row_button" {} }'))[0],
                         [("fx_wide", "Execute")])

    def test_a_block_in_what_the_instance_itself_holds_keeps_the_override_drawn(self):
        """The instance's own contents may put a block of the name where the
        panel draws it: a mod type in another slot, a template used there, or,
        for a derived type's override at its root, a type in the derived
        body. Each keeps the override drawn (review of #1639, X1 to X3)."""
        drawn = [("fx_wide", "Execute")]
        self.assertEqual(self.row_draws(self.row(instance='blockoverride "row_label" { fx_cell = {} }'))[0], drawn)
        self.assertEqual(self.row_draws(self.row(instance='blockoverride "row_label" { using = fx_tmpl }'))[0], drawn)
        both = [("fx_derived", "Execute"), ("fx_wide", "Execute")]  # a block of the name drawn anywhere keeps both
        self.assertEqual(self.row_draws(self.row(second="fx_derived = {}", derived="fx_cell = {}"))[0], both)
        self.assertEqual(self.row_draws(self.row(second="fx_derived = {}", derived="widget = { using = fx_tmpl }"))[0], both)

    def test_a_guard_in_what_the_instance_itself_holds_can_be_replaced_too(self):
        """The guard a `visible` replaces may be one in the instance's own
        contents: in a mod type put in a slot, or on a widget written there
        that declares the block."""
        shown = 'blockoverride "row_shown" { visible = "[Country.IsAtWar]" }'
        cell = 'blockoverride "row_label" { fx_gcell = {} }\n\t\t\t'
        self.assertEqual(self.row_draws(self.row(instance=cell))[0], [])
        self.assertEqual(self.row_draws(self.row(instance=cell + shown))[0], [("fx_wide", "Execute")])
        slot = ('blockoverride "row_slot" {\n\t\t\t\t%s\n\t\t\t\tbutton = { onclick = "[GetScriptedGui(\'z\').Execute( '
                'GuiScope.SetRoot( Country.MakeScope ).End )]" }\n\t\t\t}\n\t\t\t')
        written = 'blockoverride "row_label" { widget = { using = te_own_country_only  block "row_slot" {} } }'
        deep = 'widget = { block "row_slot" {} }'
        self.assertEqual(self.row_draws(self.row(guarded=deep, instance=slot % "" + written))[0], [])
        self.assertEqual(self.row_draws(self.row(guarded=deep, instance=slot % 'visible = "[Country.IsAtWar]"' + written))[0],
                         [("fx_wide", "Execute")])

    def test_a_drawn_block_of_the_name_anywhere_in_the_panel_keeps_the_override_drawn(self):
        """A block of the name can reach an instance from another level: an
        instance of a derived type fills a slot, or the instance of the type
        that holds the row fills a slot the row passes on. The walk doesn't
        trace those, so one drawn block of the name anywhere in the panel
        keeps every override of it drawn (review of #1639, X4 and X5)."""
        derived = self.row(second='fx_derived = {\n\t\t\tblockoverride "row_label" { fx_cell = {} }\n\t\t}')
        self.assertEqual(self.row_draws(derived)[0], [("fx_derived", "Execute"), ("fx_wide", "Execute")])
        self.assertEqual(self.row_draws(self.row(second="fx_mid = {}"))[0], [])
        passed = self.row(second='fx_mid = {\n\t\t\tblockoverride "row_extra" { fx_cell = {} }\n\t\t}')
        self.assertEqual(self.row_draws(passed)[0], [("fx_mid", "Execute"), ("fx_wide", "Execute")])

    def test_a_templates_block_counts_where_the_template_is_used(self):
        """A block a template declares is one at each `using`: drawn outside
        the guard, the player's own under it."""
        used = "widget = { using = fx_tmpl }"
        self.assertEqual(self.row_draws(self.row(open=used))[0], [("fx_wide", "Execute")])
        self.assertEqual(self.row_draws(self.row(guarded=used)), ([], [], {"fx_label"}))
        self.assertEqual(self.row_draws(self.row(guard="", guarded=used))[0], [("fx_wide", "Execute")])

    def test_an_override_of_no_block_the_mod_defines_is_drawn(self):
        """A blockoverride whose block no mod type has (a vanilla type's, which
        the walk doesn't read) stays drawn, and so does one on a widget that
        is no mod type."""
        other = ('blockoverride "row_other" {\n\t\t\t\tonclick = "[GetScriptedGui(\'z\').Execute( '
                 'GuiScope.SetRoot( Country.MakeScope ).End )]"\n\t\t\t}')
        self.assertEqual(self.row_draws(self.row(instance=other))[0], [("fx_wide", "Execute")])
        self.assertEqual(self.row_draws(self.row(second="default_header = {\n\t\t\t" + other.replace(
            "row_other", "row_button") + "\n\t\t}"))[0], [("fx_wide", "Execute")])
        # a name another type guards, overridden on a mod type that has no block of it
        self.assertEqual(self.row_draws(self.row(second="fx_held = {\n\t\t\t" + other.replace(
            "row_other", "row_button") + "\n\t\t}"))[0], [("fx_wide", "Execute")])

    def test_an_override_that_sets_the_guards_own_widgets_visible_is_drawn(self):
        """An override's `visible` is its block's widget's. On the widget
        that carries the guard it replaces the guard's (gotcha #17), so the
        override is drawn; on a widget inside the guarded one it changes
        nothing."""
        slot = ('blockoverride "row_slot" {\n\t\t\t\t%s\n\t\t\t\tbutton = { onclick = "[GetScriptedGui(\'z\').Execute( '
                'GuiScope.SetRoot( Country.MakeScope ).End )]" }\n\t\t\t}')
        block = 'block "row_slot" {}'
        self.assertEqual(self.row_draws(self.row(guarded=block, instance=slot % ""))[0], [])
        both = [("fx_wide", "Execute")] * 2  # the guard gone, the row's own button is drawn too
        self.assertEqual(self.row_draws(self.row(guarded=block, instance=slot % 'visible = "[Country.IsAtWar]"'))[0], both)
        self.assertEqual(self.row_draws(self.row(guarded=block, instance=slot % "using = fx_shown"))[0], both,
                         "a template may set one")
        self.assertEqual(self.row_draws(self.row(held='visible = "[Country.IsAtWar]"')), ([], [], {"fx_label"}),
                         "the button's own visible, inside the guarded widget")

    def test_a_block_at_a_types_root_lands_on_the_widget_that_instances_it(self):
        """The mod's usual guard form, `row = { using = te_own_country_only }`
        on an instance of a type: a block at that type's root is the
        instance's own, so an override's `visible` there replaces the guard
        (review of #1639, G1); without one the override is the player's."""
        slot = ('blockoverride "row_slot" {\n\t\t\t\t%s\n\t\t\t\tbutton = { onclick = "[GetScriptedGui(\'z\').Execute( '
                'GuiScope.SetRoot( Country.MakeScope ).End )]" }\n\t\t\t}')
        carried = "fx_slot = { using = te_own_country_only }"
        self.assertEqual(self.row_draws(self.row(open=carried, instance=slot % ""))[0], [])
        self.assertEqual(self.row_draws(self.row(open=carried, instance=slot % 'visible = "[Country.IsAtWar]"'))[0],
                         [("fx_wide", "Execute")])
        inside = "widget = {\n\t\t\tusing = te_own_country_only\n\t\t\tfx_slot = {}\n\t\t}"
        self.assertEqual(self.row_draws(self.row(open=inside, instance=slot % 'visible = "[Country.IsAtWar]"'))[0], [],
                         "the guard is a container's: the instance's visible is its own")

    def test_the_guard_a_visible_replaces_may_be_a_types_own_or_a_derived_types(self):
        """The widget a root-level block lands on may carry the guard as an
        instance of a derived type, or as the type's own root guard (a
        derived type's root being the same widget); and the block may reach
        a nested type's guard widget through that instance's blockoverride.
        With a `visible` the guard is replaced; without one the override is
        the player's."""
        slot = ('blockoverride "row_slot" {\n\t\t\t\t%s\n\t\t\t\tbutton = { onclick = "[GetScriptedGui(\'z\').Execute( '
                'GuiScope.SetRoot( Country.MakeScope ).End )]" }\n\t\t\t}')
        shown = 'visible = "[Country.IsAtWar]"'
        for name, parts in (("an instance of a derived type", {"open": "fx_dslot = { using = te_own_country_only }"}),
                            ("through a nested instance's blockoverride",
                             {"open": 'fx_inner = { blockoverride "row_y" { block "row_slot" {} } }'})):
            with self.subTest(guard=name):
                self.assertEqual(self.row_draws(self.row(instance=slot % "", **parts))[0], [])
                self.assertEqual(self.row_draws(self.row(instance=slot % shown, **parts))[0], [("fx_wide", "Execute")])
        with self.subTest(guard="the type's own root"):
            rooted = "fx_gslot = {\n\t\t\t%s\n\t\t}"
            self.assertEqual(self.row_draws(self.row(second=rooted % (slot % "")))[0], [])
            self.assertEqual(self.row_draws(self.row(second=rooted % (slot % shown)))[0], [("fx_wide", "Execute")])
        with self.subTest(guard="a base's root, the override at the derived type's root"):
            self.assertEqual(self.row_draws(self.row(second="fx_gd = {}", gd=slot % ""))[0], [])
            self.assertEqual(self.row_draws(self.row(second="fx_gd = {}", gd=slot % shown))[0], [("fx_gd", "Execute")])

    def test_a_visible_set_at_the_types_root_counts_for_its_instances(self):
        """A derived type's override at its root puts a `visible` on the
        guard's widget: the guard is gone for an instance of that type too."""
        slot = ('blockoverride "row_slot" {\n\t\t\t\tbutton = { onclick = "[GetScriptedGui(\'z\').Execute( '
                'GuiScope.SetRoot( Country.MakeScope ).End )]" }\n\t\t\t}')
        blocks = 'block "row_slot" {}\n\t\t\tblock "row_shown" {}'
        instance = "fx_derived = {\n\t\t\t%s\n\t\t}" % slot
        self.assertEqual(self.row_draws(self.row(guarded=blocks, second=instance))[0], [])
        setter = 'blockoverride "row_shown" { visible = "[Country.IsAtWar]" }'
        self.assertEqual(self.row_draws(self.row(guarded=blocks, second=instance, derived=setter))[0],
                         [("fx_derived", "Execute"), ("fx_wide", "Execute")])

    SEAL = """template fx_blocks {
	block "t_block" {}
}
template fx_guarded {
	using = te_own_country_only
	block "t_slot" {}
}
types fixture
{
	type fx_wide = flowcontainer {
		@WIDE@
	}
	type fx_row = flowcontainer {
		widget = {
			using = te_own_country_only
			block "slot" {}
			block "shown" {}
			button = { block "button" {} }
			@GUARDED@
		}
	}
	type fx_slot = widget {
		block "root_slot" {}
	}
	type fx_gslot = widget {
		using = te_own_country_only
		block "g_slot" {}
	}
	type fx_dslot = fx_slot {
	}
	type fx_plain = flowcontainer {
		button = {
			block "p_slot" {}
			block "p_shown" {}
		}
		vanilla_button = {
			block "v_slot" {}
			@VANILLA@
		}
		widget = {
			block "d_guard" {
				using = te_own_country_only
			}
			block "d_shown" {}
		}
	}
	@TYPES@
}
"""

    def sealed(self, wide="", types="", guarded="", vanilla="", rows=False, top=""):
        text = top + self.SEAL.replace("@WIDE@", wide).replace("@TYPES@", types).replace("@GUARDED@", guarded)
        text = text.replace("@VANILLA@", vanilla)
        found = guard_visible_overrides(file_types(text, "f.gui"), file_templates(text, "f.gui"), {"f.gui": text})
        return found if rows else [(block, why) for _, _, block, why, _ in found]

    def test_an_override_that_puts_a_visible_on_a_guards_widget_fails_the_seal(self):
        """SkippedOverrideTest's seal (guard_visible_overrides), on what the
        walk doesn't follow (review of #1639: I6, I7, I8, I11, I12) and what
        it does: by name, wherever the override is written."""
        shown = 'visible = "[Country.IsAtWar]"'
        sets = "sets a visible"
        row = "fx_row = {\n\t\t\t%s\n\t\t}"
        self.assertEqual(self.sealed(row % ('blockoverride "slot" { button = { %s } }\n\t\t\tblockoverride "button" { %s }'
                                            % (shown, shown))), [], "a child's visible, and one on a widget inside")
        self.assertEqual(self.sealed(row % ('blockoverride "shown" { %s }' % shown)), [("shown", sets)])
        self.assertEqual(self.sealed(row % ('blockoverride "slot" { block "v" { %s } }' % shown)), [("slot", sets)])
        self.assertEqual(self.sealed(row % 'blockoverride "slot" { using = fx_tmpl }'),
                         [("slot", "uses a template, which may set a visible")])
        # an override nested in the override (I6)
        self.assertEqual(self.sealed(row % ('blockoverride "slot" { blockoverride "shown" { %s } }' % shown)),
                         [("shown", sets), ("slot", "holds a blockoverride, which may set a visible")])
        # from an instance further out or further in (I7, I11): wherever it is written, drawn or not
        other = 'type fx_other = flowcontainer {\n\t\tfx_mid = { blockoverride "shown" { %s } }\n\t}' % shown
        self.assertEqual(self.sealed(row % 'blockoverride "slot" {}', types=other), [("shown", sets)])
        # a block an override declares on the guard's widget is on it too
        self.assertEqual(self.sealed(row % ('blockoverride "slot" { block "more" {} }'),
                                     types='type fx_other = fx_row {\n\t\tblockoverride "more" { %s }\n\t}' % shown),
                         [("more", sets)])
        # the instance carries the guard: the root of the type it instances (I8)
        slot = 'fx_slot = {\n\t\t\t%s\n\t\t\tblockoverride "root_slot" { %s }\n\t\t}'
        self.assertEqual(self.sealed(slot % ("", shown)), [])
        self.assertEqual(self.sealed(slot % ("using = te_own_country_only", shown)), [("root_slot", sets)])
        # a type whose own root carries it, and a type derived from that one
        self.assertEqual(self.sealed('fx_gslot = { blockoverride "g_slot" { %s } }' % shown), [("g_slot", sets)])
        derived = 'type fx_gd = fx_gslot {\n\t\tblock "gd_slot" {}\n\t}'
        self.assertEqual(self.sealed('fx_gd = { blockoverride "gd_slot" { %s } }' % shown, types=derived), [("gd_slot", sets)])
        # a block a template declares: one the guard's widget uses, and a template that takes the guard itself
        self.assertEqual(self.sealed(row % ('blockoverride "t_block" { %s }' % shown)), [])
        self.assertEqual(self.sealed(row % ('blockoverride "t_block" { %s }' % shown), guarded="using = fx_blocks"),
                         [("t_block", sets)])
        self.assertEqual(self.sealed('widget = {\n\t\t\tusing = fx_guarded\n\t\t\tblockoverride "t_slot" { %s }\n\t\t}' % shown),
                         [("t_slot", sets)])
        # the block's own default
        self.assertEqual(self.sealed(guarded='block "late" { %s }' % shown), [("late", "its default sets a visible")])

    def test_a_guard_written_in_an_override_sits_on_its_blocks_widget(self):
        """The Colonial Empire's form: `blockoverride "down_action" { using =
        te_own_country_only ... }`. The guard lands where the block is, so a
        second override into that widget which sets a `visible` replaces it,
        from the same instance or any other (review of #1639, L1)."""
        shown = 'visible = "[Country.IsAtWar]"'
        sets = "sets a visible"
        guard = ('blockoverride "p_slot" {\n\t\t\t\tusing = te_own_country_only\n\t\t\t\tonclick = "[GetScriptedGui(\'a\')'
                 '.Execute( GuiScope.SetRoot( Country.MakeScope ).End )]"\n\t\t\t}')
        plain = "fx_plain = {\n\t\t\t%s\n\t\t\t%s\n\t\t}"
        self.assertEqual(self.sealed(plain % (guard, "")), [], "the guard alone is no second visible")
        self.assertEqual(self.sealed(plain % (guard, 'blockoverride "p_shown" { %s }' % shown)), [("p_shown", sets)])
        self.assertEqual(self.sealed(plain % ("", 'blockoverride "p_shown" { %s }' % shown)), [], "no guard there")
        other = 'type fx_other = flowcontainer {\n\t\tfx_plain = { blockoverride "p_shown" { %s } }\n\t}' % shown
        self.assertEqual(self.sealed(plain % (guard, ""), types=other), [("p_shown", sets)], "by name, from anywhere")
        self.assertEqual(self.sealed(plain % (guard.replace("using", "using = fx_tmpl\n\t\t\t\tusing"), "")),
                         [("p_slot", "uses a template, which may set a visible")], "a second template beside the guard")
        # its block is on an instance of a vanilla type (the Colonial Empire's buttons): that instance carries it
        on_vanilla = guard.replace("p_slot", "v_slot")
        self.assertEqual(self.sealed(plain % (on_vanilla, "")), [])
        self.assertEqual(self.sealed(plain % (on_vanilla, ""), vanilla='blockoverride "anything" { %s }' % shown),
                         [("anything", sets + NOT_THE_MODS_TYPE)])
        # a block the mod doesn't declare: the widget is unknown, so nothing else the instance overrides may set one
        unknown = "%s = {\n\t\t\t" + guard.replace("p_slot", "v_any") + '\n\t\t\tblockoverride "%s" { ' + shown + " }\n\t\t}"
        self.assertEqual(self.sealed(unknown % ("vanilla_button", "p_shown")), [("p_shown", sets + NOT_THE_MODS_TYPE)])
        self.assertEqual(self.sealed(unknown % ("fx_plain", "p_shown")), [("p_shown", sets + NOT_THE_MODS_TYPE)])
        self.assertEqual(self.sealed(plain % (guard, 'blockoverride "v_other" { %s }' % shown)),
                         [("v_other", sets + NOT_THE_MODS_BLOCK)], "beside a guard on a mod block: a vanilla block only")
        # a mod block's name on an instance of a vanilla type: that type's block, wherever the mod has one too
        self.assertEqual(self.sealed(unknown.replace("v_any", "p_slot") % ("vanilla_button", "root_slot")),
                         [("root_slot", sets + NOT_THE_MODS_TYPE)])
        # the block is at a type's root: the widget is the instance, a derived type's too, with that type's root blocks
        derived = 'type fx_dblock = fx_slot {\n\t\tblock "d_root" {}\n\t}'
        rooted = "fx_dblock = {\n\t\t\t%s\n\t\t\t%s\n\t\t}" % (guard.replace("p_slot", "root_slot"), "%s")
        self.assertEqual(self.sealed(rooted % "", types=derived), [])
        self.assertEqual(self.sealed(rooted % ('blockoverride "d_root" { %s }' % shown), types=derived), [("d_root", sets)])
        # the block is itself written in a blockoverride: it sits where that override's block is
        via = 'type fx_via = flowcontainer {\n\t\tfx_plain = { blockoverride "p_shown" { block "via_slot" {} } }\n\t}'
        held = "fx_via = {\n\t\t\t%s\n\t\t\t%s\n\t\t}" % (guard.replace("p_slot", "via_slot"), "%s")
        self.assertEqual(self.sealed(held % "", types=via), [])
        self.assertEqual(self.sealed(held % ('blockoverride "p_slot" { %s }' % shown), types=via), [("p_slot", sets)])

    def test_a_guard_written_in_a_blocks_default_sits_on_the_widget_around_it(self):
        shown = 'visible = "[Country.IsAtWar]"'
        self.assertEqual(self.sealed('fx_plain = { blockoverride "d_shown" { button = { %s } } }' % shown), [])
        self.assertEqual(self.sealed('fx_plain = { blockoverride "d_shown" { %s } }' % shown), [("d_shown", "sets a visible")])

    def test_an_override_of_a_vanilla_types_block_on_a_guards_widget_fails_the_seal(self):
        """Vanilla's types are not read, so the seal has no names for the
        blocks at a vanilla type's root. On an instance of one that carries
        the guard, no blockoverride written there may set a `visible`, use a
        template or hold another (review of #1639, L2: six such instances on
        main, button_icon_minus_action and button_icon_plus_action, none with
        an override). On a guard-carrying instance of a mod type, on a type's
        guarded root and on an instance of such a type, the same for a block
        no mod type declares."""
        shown = 'visible = "[Country.IsAtWar]"'
        sets = "sets a visible"
        button = "vanilla_button = {\n\t\t\tusing = te_own_country_only\n\t\t\t%s\n\t\t}"
        self.assertEqual(self.sealed(button % 'onclick = "[Country.IsAtWar]"'), [])
        self.assertEqual(self.sealed(button % 'blockoverride "anything" { text = "fx_label" }'), [], "it sets none")
        self.assertEqual(self.sealed(button % ('blockoverride "anything" { %s }' % shown)),
                         [("anything", sets + NOT_THE_MODS_TYPE)])
        self.assertEqual(self.sealed(button % ('blockoverride "root_slot" { %s }' % shown)),
                         [("root_slot", sets + NOT_THE_MODS_TYPE)], "whatever the mod calls a block of its own")
        self.assertEqual(self.sealed(button % 'blockoverride "anything" { using = fx_tmpl }'),
                         [("anything", "uses a template, which may set a visible" + NOT_THE_MODS_TYPE)])
        self.assertEqual(self.sealed(button % ('blockoverride "anything" { blockoverride "inner" { %s } }' % shown)),
                         [("anything", "holds a blockoverride, which may set a visible" + NOT_THE_MODS_TYPE)])
        self.assertEqual(self.sealed("vanilla_button = {\n\t\t\tblockoverride \"anything\" { %s }\n\t\t}" % shown), [],
                         "no guard on it")
        # a mod type's instance: its own blocks are placed by name, a vanilla block is not
        slot = "%s = {\n\t\t\t%s\n\t\t\tblockoverride \"%s\" { " + shown + " }\n\t\t}"
        own = "using = te_own_country_only"
        self.assertEqual(self.sealed(slot % ("fx_slot", own, "v_other")), [("v_other", sets + NOT_THE_MODS_BLOCK)])
        self.assertEqual(self.sealed(slot % ("fx_slot", "", "v_other")), [])
        self.assertEqual(self.sealed(slot % ("fx_slot", own, "p_shown")), [], "a mod block on another widget")
        self.assertEqual(self.sealed(slot % ("fx_gslot", "", "v_other")), [("v_other", sets + NOT_THE_MODS_BLOCK)])
        derived = 'type fx_gv = fx_gslot {\n\t\tblockoverride "v_other" { %s }\n\t}' % shown
        self.assertEqual(self.sealed(types=derived), [("v_other", sets + NOT_THE_MODS_BLOCK)], "at a guarded root")
        template = 'template fx_gt {\n\tusing = te_own_country_only\n\tblockoverride "v_other" { %s }\n}\n' % shown
        self.assertEqual(self.sealed(top=template), [("v_other", sets + NOT_THE_MODS_BLOCK)], "at a template's")
        # a root that carries a guard written elsewhere, in an override of its block
        rooted = 'type fx_vroot = vanilla_button {\n\t\tblock "vr_slot" {}\n\t\tblockoverride "v_other" { %s }\n\t}' % shown
        self.assertEqual(self.sealed(types=rooted), [])
        self.assertEqual(self.sealed('fx_vroot = { blockoverride "vr_slot" { using = te_own_country_only } }', types=rooted),
                         [("v_other", sets + NOT_THE_MODS_BLOCK)])

    def test_a_block_at_a_bases_root_is_on_the_guards_widget_too(self):
        """An instance of a derived type that carries the guard, and a derived
        type whose own root does: the base's root blocks sit on that widget."""
        shown = 'visible = "[Country.IsAtWar]"'
        over = 'blockoverride "root_slot" { %s }' % shown
        self.assertEqual(self.sealed("fx_dslot = {\n\t\t\tusing = te_own_country_only\n\t\t\t%s\n\t\t}" % over),
                         [("root_slot", "sets a visible")])
        self.assertEqual(self.sealed("fx_dslot = {\n\t\t\t%s\n\t\t}" % over), [])
        rooted = "type fx_gd2 = fx_slot {\n\t\tusing = te_own_country_only\n\t}"
        self.assertEqual(self.sealed("fx_gd2 = {\n\t\t\t%s\n\t\t}" % over, types=rooted), [("root_slot", "sets a visible")])

    def test_a_seal_hit_names_its_line(self):
        """A block's own default is reported at the block's line, an override
        at its own, each with the guard's widget."""
        (path, line, block, why, where), = self.sealed(guarded='block "late" { visible = "[Country.IsAtWar]" }', rows=True)
        text = self.SEAL.replace("@GUARDED@", 'block "late" { visible = "[Country.IsAtWar]" }')
        late = text[:text.index('block "late"')].count("\n") + 1
        self.assertEqual((path, line, block, why), ("f.gui", late, "late", "its default sets a visible"))
        self.assertEqual(where, ("f.gui", late - 5, "fx_row"), "the widget that takes the guard, five lines up")
        (path, line, block, _, where), = self.sealed('vanilla_button = {\n\t\t\tusing = te_own_country_only\n\t\t\t'
                                                     'blockoverride "anything" { visible = "[Country.IsAtWar]" }\n\t\t}',
                                                     rows=True)
        self.assertEqual((path, line, block, where), ("f.gui", 13, "anything", ("f.gui", 11, "fx_wide")))

    def test_a_visible_reaches_the_guards_widget_by_another_way(self):
        """Through a block default nested in the override, or through a
        second override of the same instance into the same widget: the guard
        is replaced for everything on it (review of #1639, U14 and U15)."""
        slot = ('blockoverride "row_slot" {\n\t\t\t\t%s\n\t\t\t\tbutton = { onclick = "[GetScriptedGui(\'z\').Execute( '
                'GuiScope.SetRoot( Country.MakeScope ).End )]" }\n\t\t\t}')
        shown = 'visible = "[Country.IsAtWar]"'
        block = 'block "row_slot" {}'
        both = [("fx_wide", "Execute")] * 2  # the slot's button and the row's own
        self.assertEqual(self.row_draws(self.row(guarded=block, instance=slot % ('block "row_slot_shown" { %s }' % shown)))[0],
                         both)
        second = '\n\t\t\tblockoverride "row_shown" { %s }' % shown
        self.assertEqual(self.row_draws(self.row(guarded=block + '\n\t\t\tblock "row_shown" {}',
                                                 instance=slot % "" + second))[0], both)
        self.assertEqual(self.row_draws(self.row(guarded=block, open='block "row_shown" {}',
                                                 instance=slot % "" + second))[0], [], "on another widget")

    def test_an_override_into_a_guarded_block_hides_what_it_holds(self):
        """The walk doesn't follow an instance inside such an override: a
        type drawn only there is not another country's (panel_view's open)."""
        self.assertNotIn("fx_held", open_types({"fx_wide"}, self.row(held="fx_held = {}")))
        self.assertIn("fx_held", open_types({"fx_wide"}, self.row(guard="", held="fx_held = {}")))

    GATE = """types fixture
{
	type fx_wide = flowcontainer {
		@WIDE@
	}
	type fx_list = flowcontainer {
		@ROOT@
		flowcontainer = {
			# world: the list is the world's, kept on the player
			datamodel = "[GetPlayer.MakeScope.GetList('fx_rows')]"
		}
	}
}
"""
    OBSERVER = 'visible = "[Not( GetMetaPlayer.IsObserver )]"'

    def ungated(self, wide="fx_list = {}", root=""):
        types = file_types(self.GATE.replace("@WIDE@", wide).replace("@ROOT@", root), "fixture.gui")
        return [(f.where, f.what) for f in ungated_world_reads({"fx_wide"}, types)]

    def test_a_world_read_with_no_observer_gate_fails(self):
        """ObserverTest's check: a `# world:` read needs an observer gate on a
        widget around it, in its own type or around every place that draws
        the type; a gate beside it, or one whose test isn't first, is none."""
        read = [("fx_list", "GetPlayer")]
        self.assertEqual(self.ungated(), read, "no gate")
        box = "widget = {\n\t\t\t%s\n\t\t\tfx_list = {}\n\t\t}"
        self.assertEqual(self.ungated(box % self.OBSERVER), [], "a container around the only place that draws it")
        self.assertEqual(self.ungated(box % self.OBSERVER + "\n\t\tfx_list = {}"), read, "a second place, bare")
        self.assertEqual(self.ungated("widget = { %s }\n\t\tfx_list = {}" % self.OBSERVER), read, "a gate beside it")
        self.assertEqual(self.ungated(box % 'visible = "[And( Not( GetMetaPlayer.IsObserver ), Country.IsAtWar )]"'), [])
        self.assertEqual(self.ungated(box % 'visible = "[And( GetPlayer.IsValid, Country.IsAtWar )]"'), [])
        self.assertEqual(self.ungated(box % 'visible = "[And( Country.IsAtWar, Not( GetMetaPlayer.IsObserver ) )]"'), read,
                         "the test isn't first")
        self.assertEqual(self.ungated(box % 'visible = "[Or( Not( GetMetaPlayer.IsObserver ), Country.IsAtWar )]"'), read)
        self.assertEqual(self.ungated("widget = {\n\t\t\tusing = te_own_country_only\n\t\t\tfx_list = {}\n\t\t}"), [],
                         "the player's own: an observer's panel doesn't draw it")

    def test_a_gate_on_a_types_root_holds_until_an_instance_sets_its_visible(self):
        """Colonial Powers' form: the gate on the section type's root, every
        instance {} (an instance's own visible replaces the type's, gotcha
        #17). The panel's own top type's root is not counted: its mount sets
        a visible."""
        read = [("fx_list", "GetPlayer")]
        self.assertEqual(self.ungated(root=self.OBSERVER), [])
        self.assertEqual(self.ungated('fx_list = { visible = "[Country.IsAtWar]" }', self.OBSERVER), read)
        self.assertEqual(self.ungated('fx_list = {}\n\t\tfx_list = { visible = "[Country.IsAtWar]" }', self.OBSERVER),
                         read, "one of two")
        self.assertEqual(self.ungated("fx_list = { %s }" % self.OBSERVER), [], "the instance's own is the gate")
        types = file_types(self.GATE.replace("@WIDE@", "").replace("@ROOT@", self.OBSERVER), "fixture.gui")
        self.assertEqual(len(ungated_world_reads({"fx_list"}, types)), 1)

    def test_a_world_read_gated_on_its_own_line(self):
        """The observer test first in the read's own visible, or the read
        behind GetPlayer.IsValid; an unmarked read is BindingTest's."""
        def found(read):
            return [f.what for f in ungated_world_reads({"fx_wide"}, _fixture(read))]
        self.assertEqual(found("# world: w\n\t\tvisible = \"[GetPlayer.MakeScope.ScriptValue('y')]\""), ["GetPlayer"])
        self.assertEqual(found("# world: w\n\t\tvisible = \"[And( Not( GetMetaPlayer.IsObserver ), "
                               "GetPlayer.MakeScope.ScriptValue('y') )]\""), [])
        self.assertEqual(found("# world: w\n\t\tvisible = \"[And( GetPlayer.MakeScope.ScriptValue('y'), "
                               "Not( GetMetaPlayer.IsObserver ) )]\""), ["GetPlayer"])
        self.assertEqual(found("# world: w\n\t\ttext = \"[SelectLocalization( GetPlayer.IsValid, "
                               "GetPlayer.GetName, '' )]\""), [])
        self.assertEqual(found("# world: w\n\t\ttext = \"[GetPlayer.GetName]\""), ["GetPlayer"])
        self.assertEqual(found("# world: w\n\t\ttext = \"[Concatenate( GetPlayer.GetName, SelectLocalization( "
                               "GetPlayer.IsValid, 'a', 'b' ) )]\""), ["GetPlayer"], "the test comes after the read")
        self.assertEqual(found("visible = \"[GetPlayer.MakeScope.ScriptValue('y')]\""), [])
        text = ("template fx_tmpl {\n\t# world: w\n\ttooltip = \"[GetPlayer.GetName]\"\n}\ntypes fixture\n{\n"
                "\ttype fx_wide = flowcontainer {\n\t\twidget = { using = fx_tmpl }\n\t}\n}\n")
        self.assertEqual([f.where for f in ungated_world_reads({"fx_wide"}, file_types(text, "f.gui"),
                                                               file_templates(text, "f.gui"))], ["template fx_tmpl"])

    def test_a_guarded_type_given_its_own_visible_is_open(self):
        """A type whose root takes te_own_country_only loses the guard where an
        instance sets its own visible: the instance's replaces the template's
        (gotcha #17)."""
        text = """types fixture
{
	type fx_wide = flowcontainer {
		fx_ctl = {@VIS@}
	}
	type fx_ctl = flowcontainer {
		using = te_own_country_only
		button = { onclick = "[GetScriptedGui('x').Execute( GuiScope.SetRoot( Country.MakeScope ).End )]" }
	}
}
"""
        self.assertEqual(unguarded_controls({"fx_wide"}, file_types(text.replace("@VIS@", ""), "f.gui")), [])
        found = unguarded_controls({"fx_wide"}, file_types(text.replace("@VIS@", ' visible = "[Country.IsAtWar]" '),
                                                           "f.gui"))
        self.assertEqual([(f.where, f.what) for f in found], [("fx_ctl", "Execute")])

    def test_a_template_the_panel_uses_is_read(self):
        text = """template fx_tmpl {
	tooltip = "[GetPlayer.GetName]"
}
types fixture
{
	type fx_wide = flowcontainer {
		widget = { using = fx_tmpl }
		widget = {
			using = te_own_country_only
			using = fx_tmpl_mine
		}
	}
}
template fx_tmpl_mine {
	tooltip = "[JournalEntry.GetCountry.GetName]"
}
"""
        found = markup_reads({"fx_wide"}, file_types(text, "f.gui"), file_templates(text, "f.gui"))
        self.assertEqual([(f.where, f.what, f.line) for f in found], [("template fx_tmpl", "GetPlayer", 2)])

    def test_a_dialog_and_a_toggled_popup_are_controls(self):
        found = unguarded_controls({"fx_wide"}, _fixture(
            "button = { onclick = \"[PopupManager.ShowCompanyChangeName( Country.MakeScope.Var('c').GetCompany.Self )]\" }"))
        self.assertEqual([f.what for f in found], ["PopupManager.ShowCompanyChangeName"])
        found = unguarded_controls({"fx_wide"}, _fixture(
            "button = { onclick = \"[GetVariableSystem.Toggle('te_popup', 'fx_picker')]\" }"))
        self.assertIn("fx_picker, whose popup holds controls", found[0].what)

    def test_every_loc_line_shape_is_read(self):
        """`key:"v"` (no space) and a line with a trailing REVIEWED comment are
        loc lines too: the game reads both."""
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "fx_l_english.yml"), "w", encoding="utf-8-sig") as fh:
                fh.write('l_english:\n'
                         ' fx_tight:"[GetPlayer.GetName] and our name"\n'
                         ' fx_long:0 "[JournalEntry.GetCountry.GetName]" # REVIEWED 2026-11-02 (long_tooltip): long\n'
                         ' fx_plain:0 "Plain"\n')
            index = loc_index(tmp, tmp)
        self.assertEqual(sorted(index), ["fx_long", "fx_plain", "fx_tight"])
        self.assertEqual(index["fx_long"][0], "[JournalEntry.GetCountry.GetName]")
        self.assertEqual(sorted((f.where, f.what) for f in loc_reads(set(index), index)),
                         [("fx_long", "JournalEntry.GetCountry"), ("fx_tight", "GetPlayer")])

    def test_a_custom_localization_key_is_reached(self):
        """`[X.GetCustom('name')]` renders the entry's localization_keys
        (common/customizable_localization/), in the caller's context."""
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "common", "customizable_localization"))
            with open(os.path.join(tmp, "common", "customizable_localization", "fx.txt"), "w",
                      encoding="utf-8-sig") as fh:
                fh.write("fx_custom = {\n\ttype = country\n\ttext = {\n\t\ttrigger = { always = yes }\n"
                         "\t\tlocalization_key = fx_picked\n\t}\n}\n")
            custom = custom_loc(tmp)
        loc = {"fx_label": "Arsenal [Country.GetCustom('fx_custom')]", "fx_picked": "[GetPlayer.GetName]'s"}
        types = _fixture('textbox = { text = "[Country.GetCustom(\'fx_custom\')]" }')
        self.assertEqual(panel_loc_keys({"fx_wide"}, types, loc, custom=custom), {"fx_label", "fx_picked"})
        self.assertEqual(loc_closure({"fx_label"}, loc, custom=custom), {"fx_label", "fx_picked"})
        self.assertEqual(loc_closure({"fx_label"}, loc, custom={}), {"fx_label"})

    def test_unbound_stays_a_set_when_it_empties(self):
        """The last system's PR leaves UNBOUND with no entries: still a set
        (a bare {} would be a dict, and UNBOUND | PRIVATE would raise)."""
        src = _read(os.path.abspath(__file__))
        block = src[src.index("\nUNBOUND = ") + 1:]
        block = block[:block.index("\n])\n") + 3]
        emptied = re.sub(r'(?m)^\s*"\w+",\n', "", block)
        scope = {}
        exec(emptied, scope)
        self.assertEqual(scope["UNBOUND"], set())
        self.assertIsInstance(scope["UNBOUND"] | PRIVATE, set)


if __name__ == "__main__":
    unittest.main()
