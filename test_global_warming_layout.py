"""Global Warming panels: section order, collapse defaults, state-gated lines, the
warming ladder's one definition, and the icons (#586's art, recorded in
docs/systems/global_warming_gui_icons.md)
(docs/guides/gui_style_guide.md; test_un_layout.py is the model)."""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "global_warming_widget.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_global_warming.txt")
VALUES = os.path.join(REPO, "common", "script_values", "global_warming_values.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "global_warming_sguis.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "global_warming_triggers.txt")
CUSTOM_LOC = os.path.join(REPO, "common", "customizable_localization", "global_warming_custom_loc.txt")
ICONS_DOC = os.path.join(REPO, "docs", "systems", "global_warming_gui_icons.md")
LOC_DIR = os.path.join(REPO, "localization", "english")

STATUS = ["te_gw_sec_policies", "te_gw_sec_emitters", "te_gw_sec_transition"]
# National, the player's own (#660): the Market tab shows it on our market only.
OWN_MARKET_ONLY = {"te_gw_sec_transition"}
REFERENCE = ["te_gw_sec_history", "te_gw_sec_how"]
ROOTS = {"widget_je_gw_overview": ("custom_widget_container_1", "te_gw_overview_panel"),
         "widget_je_gw_status": ("custom_widget_container_2", "te_gw_status_sections"),
         "widget_je_gw_reference": ("custom_widget_container_3", "te_gw_reference_sections")}
FLAGS = {"gw_policies_closed", "gw_emitters_closed", "gw_world_closed", "gw_hist_closed", "gw_how_open",
         "rt_transition_closed", "rt_how_open"}
OLD_FLAGS = ["gw_hist_open", "gw_world_open", "gw_emissions_closed"]
MARKET_WIDE = ["carbon_tax", "renewable_investment", "emission_standards"]
NATIONAL = ["climate_adaptation", "reforestation", "public_transit", "fossil_fuel_divestment",
            "green_building_codes"]
NATIONAL.insert(2, "carbon_removal")
# Textures in the widget that are not icons: frames, fills and blanks.
NOT_ICONS = {"gfx/interface/backgrounds/round_frame_dec.dds",
                    "gfx/interface/backgrounds/white.dds",   # the threshold line, a tinted flat fill
                    "gfx/interface/icons/generic_icons/transparent.dds"}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _block_from(text, start):
    """The body of the brace block whose `{` is the last character before `start`."""
    depth = 0
    for j in range(start - 1, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j]
    raise AssertionError("unbalanced braces")


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return _block_from(text, m.end())


def _top_level(text, name):
    m = re.search(rf"(?m)^{name} = \{{", text)
    assert m, f"no {name}"
    return _block_from(text, m.end())


def _loc_value(key):
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        m = re.search(rf'^ {re.escape(key)}:\d* "(.*)"\s*$', _read(path), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


def _loc_keys():
    keys = set()
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        keys |= set(re.findall(r"(?m)^ ([\w.\-]+):\d* \"", _read(path)))
    return keys


class OrderTest(unittest.TestCase):
    def test_status_and_reference_order(self):
        gui = _read(GUI)
        for composer, expected in (("te_gw_status_sections", STATUS),
                                   ("te_gw_reference_sections", REFERENCE)):
            found = re.findall(r"^\t\t(te_gw_sec_\w+) = \{", _type_body(gui, composer), re.M)
            self.assertEqual(found, expected, composer)

    def test_the_entry_attaches_three_thin_roots(self):
        je, gui = _read(JE), _read(GUI)
        attached = dict(re.findall(
            r'gui = "gui/journal_entry_widgets/global_warming_widget\.gui"\s*'
            r'name = "(\w+)"\s*container = "(\w+)"', je))
        self.assertEqual(attached, {name: c for name, (c, _) in ROOTS.items()})
        for name, (_, composer) in ROOTS.items():
            m = re.search(rf'(?m)^flowcontainer = \{{\s*name = "{name}"', gui)
            self.assertTrue(m, name)
            body = _block_from(gui, gui.index("{", m.start()) + 1)
            self.assertIn('visible = "[JournalEntry.IsActive]"', body, name)
            self.assertEqual(re.findall(r"^\t(\w+) = \{", body, re.M), [composer], name)

    def test_the_bars_on_top_marker_is_attached(self):
        """Round 2: the overview draws the temperature bar, so the entry carries
        the marker that hides the panel's own bar block (the goal bar from #582)."""
        self.assertRegex(_read(JE), r'gui = "gui/journal_entry_widgets/te_je_bars_on_top_marker\.gui"\s*'
                                    r'name = "widget_te_je_bars_on_top_marker"\s*'
                                    r'container = "custom_widget_container_7"')

    def test_the_old_root_names_are_gone(self):
        for old in ("widget_je_gw_conditions", "widget_je_gw_policies", "widget_je_gw_history"):
            self.assertNotIn(old, _read(JE))
            self.assertNotIn(old, _read(GUI))


class FlagTest(unittest.TestCase):
    def test_section_flags_say_their_default(self):
        text = _read(GUI)
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", text))
        self.assertEqual(flags, FLAGS)
        for f in flags:
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", text))
            bare = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", text)) - negated
            if f.endswith("_closed"):   # shown unless closed: one bare (show-more), the rest negated
                self.assertEqual(bare, 1, f)
                self.assertGreaterEqual(negated, 2, f)
            else:                        # shown only when opened: one negated (show-more)
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 2, f)

    def test_no_old_flag_survives(self):
        for f in OLD_FLAGS:
            self.assertNotIn(f"'{f}'", _read(GUI), f)


def _visible_of(body, text_key):
    """The `visible` expression of the widget whose text is `text_key`."""
    m = re.search(rf'visible = "\[([^"]*)\]"\s*(?:align = [\w|]+\s*)?text = "{text_key}"', body)
    assert m, f"no gated line {text_key}"
    return m.group(1)


class GatedLinesTest(unittest.TestCase):
    """Lines that matter in one state appear only in that state (style rules 6, 7)."""

    def test_emissions_table_waits_for_the_first_january(self):
        body = _type_body(_read(GUI), "te_gw_overview_panel")
        gate = "GetScriptedGui('gw_has_yearly_figures_sgui').IsShown"
        pending = _visible_of(body, "gw_emis_pending")
        self.assertTrue(pending.startswith("Not(") and gate in pending, pending)
        table = re.search(r'flowcontainer = \{\s*direction = vertical\s*ignoreinvisible = yes\s*'
                          r'(?:minimumsize = \{ 480 -1 \}\s*)?visible = "\[([^"]*)\]"\s*gw_value_row', body)
        self.assertTrue(table, "the table has no gate")
        self.assertTrue(table.group(1).startswith(gate), table.group(1))

    def test_conditions_true_of_every_row_are_said_once_and_only_while_they_hold(self):
        body = _type_body(_read(GUI), "te_gw_sec_policies")
        for key, sgui, negated in (("gw_pol_waiting", "gw_policies_waiting_sgui", False),
                                   ("gw_pol_treaty", "gw_treaty_bound_sgui", False),
                                   ("gw_pol_set_by_leader", "gw_is_market_leader_sgui", True)):
            vis = _visible_of(body, key)
            self.assertIn(f"GetScriptedGui('{sgui}').IsShown", vis, key)
            self.assertEqual(vis.startswith("Not("), negated, key)
            self.assertEqual(body.count(f'"{key}"'), 1, key)
        # The per-row note these replace is gone.
        self.assertNotIn("gw_policy_status_by_leader", _read(GUI))

    def test_treaty_cell_and_marker_are_gated(self):
        body = _type_body(_read(GUI), "te_gw_overview_panel")
        self.assertRegex(body, r"visible = \"\[GetScriptedGui\('gw_treaty_bound_sgui'\)\.IsShown[^\"]*\]\"\s*"
                               r"tooltip = \"gw_ov_treaty_tt\"")
        marker = re.search(r'progressbar = \{\s*visible = "\[([^"]*)\]"', body)
        self.assertTrue(marker)
        self.assertEqual(marker.group(1), "Not( EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope"
                                          ".ScriptValue('gw_disp_tier_code'), '(CFixedPoint)6' ) )")

    def test_waiting_line_uses_the_policies_own_threshold(self):
        waiting = _top_level(_read(SGUIS), "gw_policies_waiting_sgui")
        below = re.search(r"temperature_anomaly_display < ([\d.]+)", waiting)
        adopt = _top_level(_read(TRIGGERS), "gw_possible_carbon_tax")
        needs = re.search(r"temperature_anomaly_display >= ([\d.]+)", adopt)
        self.assertTrue(below and needs)
        self.assertEqual(float(below.group(1)), float(needs.group(1)))


class PolicyRowTest(unittest.TestCase):
    def test_nine_rows_market_wide_first_each_wired_to_its_own_handlers(self):
        body = _type_body(_read(GUI), "te_gw_sec_policies")
        rows = re.findall(r"gw_policy_row = \{\s*datacontext = \"\[GetScriptedGui\('gw_active_(\w+)_sgui'\)\]\"", body)
        self.assertEqual(rows, MARKET_WIDE + NATIONAL)
        national_heading = body.index('"gw_pol_sub_national"')
        for p in rows:
            start = body.index(f"GetScriptedGui('gw_active_{p}_sgui')")
            row = _block_from(body, body.rindex("{", 0, start) + 1)
            self.assertEqual(set(re.findall(r"GetScriptedGui\('gw_policy_(\w+)_sgui'\)", row)), {p}, p)
            self.assertIn(f'text = "GW_{p.upper()}_ROW"', row, p)
            self.assertIn(f'tooltip = "GW_{p.upper()}_DESC"', row, p)
            self.assertIn('blockoverride "row_icon"', row, p)
            self.assertEqual(start < national_heading, p in MARKET_WIDE, p)

    def test_rows_cover_the_entrys_policies(self):
        buttons = set(re.findall(r"(?m)^\s*scripted_button = gw_(\w+)_button", _read(JE)))
        policies = {b for b in buttons if not b.startswith("remove_")}
        self.assertEqual(policies, set(MARKET_WIDE + NATIONAL))

    def test_icon_lit_and_dimmed_on_the_in_force_question(self):
        row = _type_body(_read(GUI), "gw_policy_row")
        icons = re.findall(r"icon = \{(.*?)\n\t\t\t\}", row, re.S)
        self.assertEqual(len(icons), 3)   # lit, dimmed, and the in-force check
        shown = "ScriptedGui.IsShown( GuiScope.SetRoot( Country.MakeScope ).End )"   # the section's Country
        self.assertIn(f'visible = "[{shown}]"', icons[0])
        self.assertNotIn("alpha", icons[0])
        self.assertIn(f'visible = "[Not( {shown} )]"', icons[1])
        self.assertIn("alpha = 0.25", icons[1])

    def test_status_is_a_check_not_a_word(self):
        """Play-test round 3: "Active"/"Inactive" became a green check, freeing
        the width the names needed; the words stay on the icon's hover."""
        row = _type_body(_read(GUI), "gw_policy_row")
        shown = "ScriptedGui.IsShown( GuiScope.SetRoot( Country.MakeScope ).End )"
        self.assertRegex(row, rf'visible = "\[{re.escape(shown)}\]"\s*'
                              r'texture = "gfx/interface/icons/generic_icons/green_checkmark\.dds"\s*'
                              r'tooltip = "gw_policy_status_active"')
        self.assertNotIn('text = "gw_policy_status_', row)
        self.assertIn("'gw_policy_status_active', 'gw_policy_status_inactive'", row)
        cells = [int(w) for w in re.findall(r"^\t\t(?:widget) = \{\s*size = \{ (\d+) \d+ \}", row, re.M)]
        spacing = int(re.search(r"spacing = (\d+)", row).group(1))
        margin = int(re.search(r"margin = \{ (\d+) \d+ \}", row).group(1))
        self.assertEqual(cells, [26, 276, 24, 110])
        self.assertEqual(sum(cells) + spacing * 3 + margin * 2, 466)


class HowItWorksTest(unittest.TestCase):
    def test_explanations_live_in_how_global_warming_works(self):
        gui = _read(GUI)
        how = _type_body(gui, "te_gw_sec_how")
        notes = re.findall(r'gw_note = \{\s*text = "(\w+)"', how)
        self.assertGreaterEqual(len(notes), 6)
        self.assertTrue(all(n.startswith("gw_how_") for n in notes), notes)
        self.assertIn("GetVariableSystem.Toggle('gw_how_open')", how)
        for sec in ("te_gw_overview_panel", "te_gw_sec_policies", "te_gw_sec_history"):
            body = _type_body(gui, sec)
            self.assertNotIn("gw_note", body, sec)
            self.assertNotIn('"gw_how_', body, sec)

    def test_retired_explanation_is_gone(self):
        self.assertNotIn("gw_policies_none_yet", _read(GUI))
        self.assertNotIn("gw_policies_none_yet", _loc_keys())


class TierLadderTest(unittest.TestCase):
    """gw_disp_tier_code is the ladder's one definition."""

    @classmethod
    def setUpClass(cls):
        values = _read(VALUES)
        code = _top_level(values, "gw_disp_tier_code")
        cls.floor = {int(c): float(t) for t, c in re.findall(
            r"temperature_anomaly_display >= ([\d.]+) \}\s*value = (\d+)", code)}
        nxt = _top_level(values, "gw_disp_next_threshold")
        cls.next = {int(c) - 1: float(v) for c, v in re.findall(
            r"gw_disp_tier_code < (\d+) \}\s*value = ([\d.]+)", nxt)}

    def test_ladder_has_six_steps_rising(self):
        self.assertEqual(sorted(self.floor), [1, 2, 3, 4, 5, 6])
        steps = [self.floor[c] for c in range(1, 7)]
        self.assertEqual(steps, sorted(steps))
        self.assertEqual(self.floor[6], 4.0)   # the journal entry's goal

    def test_next_threshold_is_the_ladder_one_step_up(self):
        self.assertEqual(self.next, {c: self.floor[c + 1] for c in range(0, 5)})

    def test_custom_loc_reads_the_code_not_the_temperature(self):
        text = _read(CUSTOM_LOC)
        for name in ("gw_severity_text", "gw_severity_short"):
            body = _top_level(text, name)
            self.assertEqual(re.findall(r"gw_disp_tier_code >= (\d+)", body), ["6", "5", "4", "3", "2", "1"])
            self.assertNotIn("temperature_anomaly_display", body, name)

    def test_every_tier_has_an_icon(self):
        body = _type_body(_read(GUI), "te_gw_overview_panel")
        codes = {int(n) for n in re.findall(
            r"ScriptValue\('gw_disp_tier_code'\), '\(CFixedPoint\)(\d+)' \)\]\"\s*blockoverride \"icon_texture\"", body)}
        self.assertEqual(codes, set(range(7)))


class RoundTwoTest(unittest.TestCase):
    """The owner's answers after play-test round 1 (2026-09-29)."""

    def test_headline_projects_ten_years_at_last_years_rate(self):
        values = _read(VALUES)
        self.assertRegex(_top_level(values, "gw_disp_projection_years"), r"^\s*value = 10\s*$")
        proj = _top_level(values, "gw_disp_temp_projected")
        for line in ("value = gw_yearly_change_display", "multiply = gw_disp_projection_years",
                     "add = temperature_anomaly_display"):
            self.assertIn(line, proj)
        head = _loc_value("gw_ov_temp_value")
        self.assertIn("GetScriptedGui('gw_has_yearly_figures_sgui').IsShown", head)
        self.assertIn("'gw_ov_temp_projected', 'gw_ov_temp_pending'", head)
        self.assertRegex(_loc_value("gw_ov_temp_projected"),
                         r"temperature_anomaly_display'\)\|2\]#! → \[[^\]]*'gw_disp_temp_projected'\)\|2\] °C \(")
        tt = _loc_value("gw_ov_temp_tt")
        for key in ("gw_ov_temp_tt_projection", "gw_ov_temp_tt_years"):
            self.assertIn(f"'{key}'", tt)
        self.assertIn("gw_disp_projection_years", _loc_value("gw_ov_temp_tt_projection"))
        keys = _loc_keys()
        for gone in ("gw_ov_temp_toward", "gw_ov_temp_now", "gw_ov_temp_rate", "gw_ov_temp_rate_pending"):
            self.assertNotIn(gone, keys)

    def test_status_line_only_while_inactive(self):
        je = _read(JE)
        m = re.search(r"(?m)^\tstatus_desc = \{", je)
        self.assertTrue(m, "status_desc is not a block")
        status = _block_from(je, m.end())
        blocks = [_block_from(status, m.end()) for m in re.finditer(r"triggered_desc = \{", status)]
        self.assertEqual([re.search(r"desc = (\w+)", b).group(1) for b in blocks],
                         ["je_global_warming_status_inactive", "je_global_warming_status_none"])
        self.assertRegex(blocks[0], r"trigger = \{\s*NOT = \{ has_journal_entry = je_global_warming \}\s*\}")
        self.assertIn("trigger = { always = yes }", blocks[1])
        self.assertEqual(_loc_value("je_global_warming_status_none"), "")
        self.assertNotIn("je_global_warming_status", _loc_keys())


class OverviewWidthTest(unittest.TestCase):
    """Play-test round 1: the overview sat ~70 px right of the column and ran off
    the panel. It is pinned to the sections' 480 px column, and the temperature
    row is fixed cells that fill it exactly."""

    def test_rows_sit_in_a_480_column(self):
        body = _type_body(_read(GUI), "te_gw_overview_panel")
        self.assertRegex(body, r"gw_panel = \{\s*(?:###[^\n]*\n\s*)*flowcontainer = \{\s*direction = vertical\s*"
                               r"spacing = \d+\s*ignoreinvisible = yes\s*minimumsize = \{ 480 -1 \}")

    def test_temperature_row_is_fixed_cells_filling_the_column(self):
        body = _type_body(_read(GUI), "te_gw_overview_panel")
        start = body.index('tooltip = "gw_ov_temp_tt"')
        row = _block_from(body, body.rindex("{", 0, start) + 1)
        spacing = int(re.search(r"spacing = (\d+)", row).group(1))
        cells = [int(w) for w in re.findall(r"^\t{5}(?:widget|default_progressbar_horizontal) = \{\s*size = \{ (\d+) \d+ \}", row, re.M)]
        self.assertEqual(len(cells), 3, cells)
        self.assertEqual(sum(cells) + spacing * (len(cells) - 1), 480)
        self.assertNotIn("parentanchor = hcenter", row.split("widget = {")[0])
        for key in ("gw_ov_temp_label", "gw_ov_temp_value"):
            cell = re.search(rf"max_width = (\d+)\s*elide = right\s*align = left\|nobaseline\s*text = \"{key}\"", row)
            self.assertTrue(cell, f"{key} does not elide inside its cell")
        self.assertIn(int(re.search(r'max_width = (\d+)\s*elide = right\s*align = left\|nobaseline\s*text = "gw_ov_temp_value"', row).group(1)), cells)

    def test_emissions_table_matches_the_column(self):
        body = _type_body(_read(GUI), "te_gw_overview_panel")
        self.assertRegex(body, r"minimumsize = \{ 480 -1 \}\s*visible = \"\[GetScriptedGui\('gw_has_yearly_figures_sgui'\)")
        # gw_value_row's cells are fixed: min and max width equal.
        row = _type_body(_read(GUI), "gw_value_row")
        for w in re.findall(r"minimumsize = \{ (\d+) -1 \}\s*maximumsize = \{ (\d+) -1 \}", row):
            self.assertEqual(w[0], w[1])
        self.assertEqual(len(re.findall(r"minimumsize = \{ (\d+) -1 \}\s*maximumsize", row)), 2)


class RoundThreeTest(unittest.TestCase):
    """Emissions became a table in the overview (the owner, 2026-09-29)."""

    def test_table_sits_between_the_headline_and_the_pies(self):
        body = _type_body(_read(GUI), "te_gw_overview_panel")
        headline = body.index('tooltip = "gw_ov_temp_tt"')
        pending = body.index('text = "gw_emis_pending"')
        table = body.index('text = "gw_emis_market_label"')
        pies = body.index("te_gw_ov_pie = {")
        self.assertLess(headline, pending)
        self.assertLess(pending, table)
        self.assertLess(table, pies)

    def test_each_row_keeps_its_tooltip(self):
        body = _type_body(_read(GUI), "te_gw_overview_panel")
        rows = re.findall(r'gw_value_row = \{\s*(?:block "gw_market_country" \{[^{}]*\}\s*)?tooltip = "(\w+)"\s*'
                          r'blockoverride "row_label" \{\s*text = "(\w+)"', body)
        self.assertEqual(rows, [("gw_cond_emis_tt", "gw_emis_market_label"), ("gw_emis_capture_tt", "gw_emis_capture_label"),
                                ("gw_emis_world_tt", "gw_emis_world_label"), ("gw_cond_trend_tt", "gw_emis_warming_label")])

    def test_the_section_is_gone(self):
        gui = _read(GUI)
        self.assertNotIn("te_gw_sec_emissions", gui)
        self.assertNotIn("gw_sect_emissions", _loc_keys())


class ProjectionBarTest(unittest.TestCase):
    """Play-test round 3: the bar shows the projection as a segment, not a marker.
    The segment is coloured by whether the change is good or bad for the player
    (the owner's convention: red bad, green good): warming is red, cooling green."""

    @classmethod
    def setUpClass(cls):
        body = _type_body(_read(GUI), "te_gw_overview_panel")
        m = re.search(r"(?m)^\t{5}widget = \{\s*size = \{ 160 18 \}", body)
        assert m, "no 160 x 18 bar cell"
        cls.bar = _block_from(body, body.index("{", m.start()) + 1)

    def test_no_eye_marker(self):
        self.assertNotIn("progressbar_marker.dds", _read(GUI))

    def test_layers_in_order(self):
        tops = [t for t in re.findall(r"^\t{6}(\w+) = \{", self.bar, re.M) if t != "size"]
        self.assertEqual(tops, ["default_progressbar_horizontal", "widget", "widget",
                                "default_progressbar_horizontal", "progressbar"])
        layers = []
        for m in re.finditer(r"(?m)^\t{6}(\w+) = \{", self.bar):
            if m.group(1) != "size":
                layers.append(_block_from(self.bar, m.end()))
        base, warming, cooling, solid, tick = layers
        self.assertRegex(base, r"value = 0\s*min = 0\s*max = 1")
        self.assertNotIn('blockoverride "background" {}', base)
        # Warming is bad: red, past the solid fill, up to the projection.
        self.assertIn("alpha = 0.4", warming)
        self.assertIn("ScriptValue('gw_disp_temp_trend'), '(CFixedPoint)1' )", warming)
        self.assertIn("bad_progressbar_horizontal = {", warming)
        self.assertIn("ScriptValue('gw_disp_bar_high_frac')", warming)
        # Cooling is good: green, the tail from the projection up to the reading.
        self.assertIn("alpha = 0.5", cooling)
        self.assertIn("ScriptValue('gw_disp_temp_trend'), '(CFixedPoint)-1' )", cooling)
        self.assertIn("green_progressbar_horizontal = {", cooling)
        self.assertIn("ScriptValue('gw_disp_bar_high_frac')", cooling)
        for layer in (warming, cooling, solid):
            self.assertIn('blockoverride "background" {}', layer)
            self.assertIn('blockoverride "frame" {}', layer)
        self.assertIn("ScriptValue('gw_disp_bar_low_frac')", solid)
        self.assertIn("ScriptValue('gw_disp_next_frac')", tick)
        self.assertRegex(tick, r"marker = \{\s*icon = \{\s*size = \{ 3 24 \}")
        self.assertIn('texture = "gfx/interface/backgrounds/white.dds"', tick)
        self.assertIn('tooltip = "gw_ov_tick_tt"', tick)

    def test_the_tooltip_explains_the_colours(self):
        tt = _loc_value("gw_ov_temp_tt")
        self.assertIn("#R red#!", tt)
        self.assertIn("#G green#!", tt)
        self.assertNotIn("pale", tt)

    def test_low_and_high_swap_when_cooling(self):
        values = _read(VALUES)
        low = _top_level(values, "gw_disp_bar_low_frac")
        high = _top_level(values, "gw_disp_bar_high_frac")
        self.assertRegex(low, r"^\s*value = gw_disp_temp_frac\s*if = \{\s*limit = \{ gw_disp_temp_trend < 0 \}\s*value = gw_disp_proj_frac")
        self.assertRegex(high, r"^\s*value = gw_disp_proj_frac\s*if = \{\s*limit = \{ gw_disp_temp_trend < 0 \}\s*value = gw_disp_temp_frac")
        self.assertIn("value = gw_disp_temp_projected", _top_level(values, "gw_disp_proj_frac"))

    def test_next_tier_word_is_the_ladder_one_step_up(self):
        body = _top_level(_read(CUSTOM_LOC), "gw_next_tier_short")
        pairs = re.findall(r"gw_disp_tier_code >= (\d+) \}\s*localization_key = gw_tier_short_(\w+)", body)
        order = ["negligible", "slight", "moderate", "significant", "severe", "catastrophic", "apocalyptic"]
        self.assertEqual(len(pairs), 5)
        for code, word in pairs:
            self.assertEqual(order.index(word), int(code) + 1, (code, word))
        self.assertRegex(body, r"always = yes \}\s*localization_key = gw_tier_short_slight")
        self.assertIn("GetCustom('gw_next_tier_short')", _loc_value("gw_ov_tick_tt"))


# Play-test round 3, rule 1: nothing a player reads may end in "...". Units per
# character, from the owner's screenshots: the large row font about 10 and the
# medium table font about 8.6 (the coordinator's measurements), the small font
# about 7 (the overview's "Market Leader", 13 characters in about 90 units, in
# the round-1 screenshot), and digits in the default font about 7.1 (the
# temperature headline, 22 characters in about 155 units, same screenshot; the
# round-2 screenshot showed all 25 characters of "1.61 -> 1.82 C (+0.02/yr)" in
# its 198-unit cell). The default font is otherwise taken as medium. Plus 10%.
UNITS = {"large": 10.0, "medium": 8.6, "small": 7.0, "digits": 7.1}
MARGIN = 1.1


def _visible_text(value):
    """What a loc value shows: concept links become their display text, and
    formatting codes and data reads are dropped (the caller supplies data)."""
    value = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", r"\1", value)
    value = re.sub(r"\[concept_(\w+)\]", lambda m: _loc_value(f"concept_{m.group(1)}"), value)
    value = re.sub(r"#!|#\w+ ?", "", value)
    return value


class WidthBudgetTest(unittest.TestCase):
    """Every label in a fixed-width cell fits it by the round-3 estimate. The
    cell widths are read from the .gui, so narrowing a cell fails here."""

    @classmethod
    def setUpClass(cls):
        gui = _read(GUI)
        row = _type_body(gui, "gw_policy_row")
        cls.name_cell = int(re.search(r"max_width = (\d+)\s*elide = right\s*align = nobaseline\s*"
                                      r"using = fontsize_large", row).group(1))
        table = _type_body(gui, "gw_value_row")
        cls.label_cell, cls.value_cell = (int(w) for w in re.findall(r"maximumsize = \{ (\d+) -1 \}", table))
        cls.pie_cell = int(re.search(r"size = \{ (\d+) \d+ \}", _type_body(gui, "te_gw_ov_pie")).group(1))
        cls.icon_cell = int(re.search(r"max_width = (\d+)", _type_body(gui, "te_gw_ov_icon_label")).group(1))
        ov = _type_body(gui, "te_gw_overview_panel")
        cls.temp_label_cell = int(re.search(r'max_width = (\d+)\s*elide = right\s*align = left\|nobaseline\s*'
                                            r'text = "gw_ov_temp_label"', ov).group(1))
        cls.headline_cell = int(re.search(r'max_width = (\d+)\s*elide = right\s*align = left\|nobaseline\s*'
                                          r'text = "gw_ov_temp_value"', ov).group(1))

    def assertFits(self, text, font, cell, what):
        """`text` is a string in one font, or a list of (string, font) runs."""
        runs = [(text, font)] if isinstance(text, str) else text
        need = sum(len(t) * UNITS[f] for t, f in runs) * MARGIN
        self.assertLessEqual(need, cell, f"{what}: {text!r} needs ~{need:.0f} of {cell} ({font})")

    def test_static_labels(self):
        cases = [
            # (loc key, font, cell width)
            ("gw_ov_temp_label", "medium", self.temp_label_cell),   # "Temperature", default font
            ("gw_ov_treaty_label", "small", self.icon_cell),
            ("gw_market_role_leader", "small", self.icon_cell),
            ("gw_market_role_member", "small", self.icon_cell),
            ("gw_emis_market_label_ours", "medium", self.label_cell),
            ("gw_emis_market_label_theirs", "medium", self.label_cell),
            ("gw_emis_capture_label", "medium", self.label_cell),
            ("gw_emis_world_label", "medium", self.label_cell),
            ("gw_emis_warming_label", "medium", self.label_cell),
            ("gw_sect_world", "medium", 440 - 32),        # nested header, text after its arrow
            ("gw_sect_policies", "large", 480),           # section headers, 520 with the arrow
            ("gw_sect_emitters", "large", 480),
            ("gw_sect_history", "large", 480),
            ("gw_how_header", "large", 480),
            ("gw_btn_adopt", "large", 104),               # the buttons' text, taken as large
            ("gw_btn_repeal", "large", 104),
        ]
        for p in MARKET_WIDE + NATIONAL:
            cases.append((f"GW_{p.upper()}_ROW", "large", self.name_cell))   # the policy row name
            cases.append((f"GW_{p.upper()}_ROW", "medium", self.label_cell))  # Around the World's label
        for key, font, cell in cases:
            self.assertFits(_visible_text(_loc_value(key)), font, cell, key)

    def test_longest_dynamic_texts(self):
        tiers = [_visible_text(_loc_value(f"gw_tier_short_{t}")) for t in
                 ("negligible", "slight", "moderate", "significant", "severe", "catastrophic", "apocalyptic")]
        self.assertEqual(max(tiers, key=len), "Catastrophic")
        cases = [
            (max(tiers, key=len), "small", self.icon_cell, "tier word"),
            ("Penalty ×9.99", "small", self.icon_cell, "penalty cell (anomaly below 10 C)"),
            ("9.99 → 9.99 °C (-0.20/yr)", "digits", self.headline_cell, "temperature headline"),
            ([("9.99 °C ", "digits"), ("(no rate yet)", "medium")], None, self.headline_cell,
             "headline before January"),
            ("Emissions Cut 100%", "medium", self.pie_cell, "cut pie label"),
            ("Our Share 100%", "medium", self.pie_cell, "share pie label"),
            ("Their Share 100%", "medium", self.pie_cell, "share pie label, another market"),
            (_visible_text(_loc_value("gw_ov_share_theirs") + _loc_value("gw_ov_pie_share_pending").split(")]", 1)[1]),
             "medium", self.pie_cell, "share pie label, pending"),
            ("-999.9/yr", "medium", self.value_cell, "an emissions value"),
            ("99999/yr", "medium", self.value_cell, "world emissions"),
            ("+0.20 °C", "medium", self.value_cell, "warming last year"),
            ("136 nations", "medium", self.value_cell, "an adoption count (every country)"),
        ]
        for text, font, cell, what in cases:
            self.assertFits(text, font, cell, what)


    def test_top_emitters(self):
        """The rows' cells, read from the .gui. The name has the whole 480 line:
        the longest country name in vanilla is 48 characters (dyn_c_ussr_californias,
        "United Socialist Council Republics of California")."""
        gui = _read(GUI)
        row = _type_body(gui, "gw_emitter_row")
        name = int(re.search(r'minimumsize = \{ (\d+) -1 \}\s*maximumsize = \{ \d+ -1 \}\s*autoresize = yes\s*'
                             r'elide = right\s*align = left\|nobaseline\s*using = fontsize_medium\s*'
                             r'default_format = "#tooltippable"\s*text = "gw_te_row_name"', row).group(1))
        cell = {k: int(w) for w, k in re.findall(r'max_width = (\d+)\s*elide = right\s*align = right\|nobaseline\s*'
                                                 r'using = fontsize_\w+\s*(?:default_format = "#v"\s*)?'
                                                 r'(?:block "row_ours" \{\}\s*)?text = "(\w+)"', row)}
        head = {k: int(w) for w, k in re.findall(r'max_width = (\d+)\s*elide = right\s*align = right\|nobaseline\s*'
                                                 r'using = fontsize_small\s*default_format = "#tooltippable"\s*'
                                                 r'text = "(\w+)"', _type_body(gui, "gw_emitter_header"))}
        self.assertEqual(set(cell), {"gw_te_row_annual", "gw_te_row_share", "gw_te_row_cum", "gw_te_ours"})
        self.assertEqual(set(head), {"gw_te_head_annual", "gw_te_head_share", "gw_te_head_cum"})
        cases = [
            ("United Socialist Council Republics of California", "medium", name, "the longest country name"),
            ("-9999.9/yr", "medium", cell["gw_te_row_annual"], "a market's annual emissions"),
            ("100%", "medium", cell["gw_te_row_share"], "a share"),
            ("-9,999,999", "medium", cell["gw_te_row_cum"], "a cumulative total"),
            (_visible_text(_loc_value("gw_te_ours")), "small", cell["gw_te_ours"], "our market's mark"),
        ]
        for key, width in head.items():
            cases.append((_visible_text(_loc_value(key)), "small", width, key))
        for text, font, width, what in cases:
            self.assertFits(text, font, width, what)


class LocTest(unittest.TestCase):
    def test_every_key_the_widget_names_exists(self):
        keys = _loc_keys()
        gui = _read(GUI)
        named = set(re.findall(r'\b(?:text|tooltip) = "([A-Za-z]\w*)"', gui))
        named |= set(re.findall(r"(?:Localize|SelectLocalization)\([^\]]*?'(\w+)'", gui))
        missing = sorted(k for k in named if "_" in k and k not in keys)
        self.assertEqual(missing, [])


GW_ICONS = "gfx/interface/icons/gw_icons/"
TIERS = ["negligible", "slight", "moderate", "significant", "severe", "catastrophic", "apocalyptic"]
# Placeholders the #586 art replaced; none may come back.
OLD_PLACEHOLDERS = {
    "gfx/interface/icons/event_icons/je_global_warming.dds",
    "gfx/interface/icons/state_status_icons/state_market_capital_icon.dds",
    "gfx/interface/icons/generic_icons/world_market.dds",
    "gfx/interface/icons/generic_icons/warning.dds",
    "gfx/interface/icons/trade_icons/consumption_tax.dds",
    "gfx/interface/icons/building_icons/renewable_plant.dds",
    "gfx/interface/icons/decree/decree_pollution_control.dds",
    "gfx/interface/icons/state_status_icons/state_infrastructure.dds",
    "gfx/interface/icons/decree/decree_greenest_grass_campaign.dds",
    "gfx/interface/icons/goods_icons/transportation.dds",
    "gfx/interface/icons/generic_icons/money.dds",
    "gfx/interface/icons/production_method_icons/cat_building_green_p1.dds",
    "gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_corporatist.dds",
    "gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_developmentalist_junta.dds",
}
# The two marks that stay vanilla by design.
VANILLA_MARKS = {"gfx/interface/icons/generic_icons/green_checkmark.dds",
                 "gfx/interface/icons/diplomatic_treaties_articles_icons/enforce_emissions_reduction.dds"}
# The Fossil Transition rows (#660) show the buildings' own vanilla icons.
TRANSITION_ICONS = {"coal": "gfx/interface/icons/building_icons/coal_mine.dds",
                    "oil": "gfx/interface/icons/building_icons/oil_rig.dds",
                    "power": "gfx/interface/icons/building_icons/power_plant.dds"}


class GwIconsTest(unittest.TestCase):
    """Each code, role, policy and pie is held to its #586 file (the UN's UnIconsTest)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.overview = _type_body(cls.gui, "te_gw_overview_panel")
        cls.policies = _type_body(cls.gui, "te_gw_sec_policies")

    def test_every_tier_code_has_its_own_file(self):
        found = dict(re.findall(r"ScriptValue\('gw_disp_tier_code'\), '\(CFixedPoint\)(\d)' \)\]\"\s*"
                                r"blockoverride \"icon_texture\" \{\s*texture = \"([^\"]+)\"", self.overview))
        self.assertEqual(found, {str(c): f"{GW_ICONS}tier_{t}.dds" for c, t in enumerate(TIERS)})

    def test_roles_and_penalty(self):
        leader = re.search(r"IsShown\( GuiScope\.SetRoot\( Country\.MakeScope \)\.End \)\]\"\s*"
                           r"blockoverride \"icon_texture\" \{\s*texture = \"([^\"]+)\"", self.overview)
        member = re.search(r"IsShown\( GuiScope\.SetRoot\( Country\.MakeScope \)\.End \) \)\]\"\s*"
                           r"blockoverride \"icon_texture\" \{\s*texture = \"([^\"]+)\"", self.overview)
        self.assertEqual(leader.group(1), f"{GW_ICONS}role_leader.dds")
        self.assertEqual(member.group(1), f"{GW_ICONS}role_member.dds")
        self.assertRegex(self.overview, rf'tooltip = "gw_cond_penalty_tt"\s*blockoverride "icon_texture" \{{\s*'
                                        rf'texture = "{re.escape(GW_ICONS)}penalty\.dds"')

    def test_every_policy_has_its_own_file(self):
        for p in MARKET_WIDE + NATIONAL:
            icon = "renewable_investment" if p == "carbon_removal" else p
            self.assertRegex(self.policies, rf"GetScriptedGui\('gw_active_{p}_sgui'\)\]\"\s*"
                                            rf'blockoverride "row_icon" \{{\s*texture = "{re.escape(GW_ICONS)}policy_{icon}\.dds"', p)

    def test_pies(self):
        for pie, key in (("pie_share", "gw_ov_pie_share"), ("pie_cut", "gw_ov_pie_cut")):
            self.assertRegex(self.overview, rf'texture = "{re.escape(GW_ICONS)}{pie}\.dds"\s*\}}\s*'
                                            rf'blockoverride "label" \{{\s*text = "{key}"')

    def test_every_programme_has_its_buildings_icon(self):
        body = _type_body(self.gui, "te_gw_sec_transition")
        for key, path in TRANSITION_ICONS.items():
            self.assertRegex(body, rf"GetScriptedGui\('rt_active_{key}_sgui'\)\]\"\s*"
                                   rf'blockoverride "row_icon" \{{\s*texture = "{re.escape(path)}"', key)

    def test_no_placeholder_left(self):
        textures = set(re.findall(r'texture = "(gfx/[^"]+)"', self.gui))
        self.assertEqual(textures & OLD_PLACEHOLDERS, set())
        icons = textures - NOT_ICONS - VANILLA_MARKS - set(TRANSITION_ICONS.values()) - {
            "gfx/interface/icons/un_icons/pie_rest.dds", "gfx/interface/icons/un_icons/pie_members.dds"}
        self.assertTrue(all(t.startswith(GW_ICONS) for t in icons), sorted(icons))
        self.assertEqual(len(icons), 7 + 2 + 1 + 8 + 2)   # tiers, roles, penalty, policies, pies


class IconsDocTest(unittest.TestCase):
    def test_every_icon_is_recorded(self):
        textures = set(re.findall(r'texture = "(gfx/[^"]+)"', _read(GUI))) - NOT_ICONS
        doc = _read(ICONS_DOC)
        listed = set(re.findall(r"`(gfx/[^`]+\.dds)`", doc))
        listed |= {GW_ICONS + n for n in re.findall(r"`([a-z_]+\.dds)`", doc)}
        self.assertTrue(textures)
        self.assertEqual(textures - listed, set(), "textures missing from the icons doc")



MARKET = os.path.join(REPO, "gui", "market_panel.gui")
TAB_SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")
TAB_WIDGETS = os.path.join(REPO, "gui", "te_system_tab_widgets.gui")
BUTTONS = os.path.join(REPO, "common", "scripted_buttons", "global_warming_buttons.txt")
RT_BUTTONS = os.path.join(REPO, "common", "scripted_buttons", "resource_transition_buttons.txt")
GW_TAB_GATE = "GetScriptedGui('te_market_global_warming_tab_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"
GW_TAB_UNLOCK = "GetScriptedGui('te_market_global_warming_tab_unlock_sgui')"
OWN_MARKET = "MarketPanel.GetMarket.IsSame( GetPlayer.GetCapital.GetMarket )"
BUTTONS_TAG = "### TE: Climate and Reserve tabs (te_global_warming, te_strategic_reserve) ###"
LEADER = "MarketPanel.GetMarket.GetOwner"   # the shown market's leader, as a Country datacontext
LEADER_GATE = ("GetScriptedGui('te_market_global_warming_leader_sgui').IsShown( "
               "GuiScope.SetRoot( MarketPanel.GetMarket.GetOwner.MakeScope ).End )")
MARKET_BLOCK = 'block "gw_market_country" {'
MARKET_DEFAULT = 'datacontext = "[JournalEntry.GetCountry]"'
# The types whose every read is the section's Country (block gw_market_country on
# te_gw_sec_policies' root; the row and button types are used only there).
COUNTRY_TYPES = ["te_gw_sec_policies", "gw_policy_row", "gw_adopt_button", "gw_repeal_button"]
# The market cells' texts that say "our" or "we", each switched on IsLocalPlayer.
OUR_KEYS = ["gw_cond_role_tt", "gw_ov_treaty_tt", "gw_emis_market_label", "gw_cond_emis_tt",
            "gw_emis_capture_tt", "gw_cond_share_tt"]
# Vanilla's four Market tabs, as market_panel.gui has them: slot, tab name, label,
# tooltip (vanilla gives Members none) and the selected half's label.
VANILLA_TABS = [("first", "default", "MARKET_PANEL_DETAILS_TAB_LABEL", "MARKET_PANEL_DETAILS_TAB_LABEL",
                 "MARKET_PANEL_DETAILS_TAB_LABEL_BOLD"),
                ("second", "world_market_trade", "MARKET_PANEL_WORLD_MARKET_TRADE", "MARKET_PANEL_WORLD_MARKET_TRADE",
                 "MARKET_PANEL_WORLD_MARKET_TRADE"),
                ("third", "food_security", "MARKET_PANEL_FOOD_SECURITY_TAB_LABEL",
                 "MARKET_PANEL_FOOD_SECURITY_TAB_LABEL", "MARKET_PANEL_FOOD_SECURITY_TAB_LABEL"),
                ("fourth", "states", "MARKET_PANEL_STATES_TAB_LABEL", None, "MARKET_PANEL_STATES_TAB_LABEL_BOLD")]
# The width budget (style guide rule 3) at the tab font, and one slot of six: the
# panel's 540 less the strip's 3 + 3 margin and its two 5-wide dividers.
TAB_UNITS, TAB_MARGIN = 10.0, 1.1
SIX_SLOT = (540 - 6 - 10) / 6


def _te_blocks(text, tag):
    """Each block of market_panel.gui opened by `tag`, up to its END TE line."""
    out = []
    start = text.find(tag)
    while start != -1:
        end = text.index("### END TE ###", start)
        out.append(text[start:end])
        start = text.find(tag, end)
    return out


def _widget_with(text, line, start=None):
    """The body of the widget whose own property `line` is: from the opener
    before it to its matching close. `start` picks an occurrence."""
    at = text.index(line) if start is None else start
    depth = 0
    for j in range(at, -1, -1):
        if text[j] == "}":
            depth += 1
        elif text[j] == "{":
            if depth == 0:
                return _block_from(text, j + 1)
            depth -= 1
    raise AssertionError(f"no widget holds {line!r}")


def _market_cells(overview):
    """The bodies of the overview's four market-cell widgets (those carrying
    block "gw_market_country"), with row 1's tier and penalty cells, which read
    the player's own entry, taken out of the first."""
    cells = [_widget_with(overview, MARKET_BLOCK, start=m.start())
             for m in re.finditer(re.escape(MARKET_BLOCK), overview)]
    for world in ('tooltip = "gw_ov_tier_tt"', 'tooltip = "gw_cond_penalty_tt"'):
        cells[0] = cells[0].replace(_widget_with(cells[0], world), "")
    return cells


def _strip(text):
    """The body of the Market panel's tab strip."""
    m = re.search(r"(?m)^\t\t\tte_tab_buttons_six = \{", text)
    assert m, "no te_tab_buttons_six strip"
    return _block_from(text, m.end())


def _overrides(body):
    """{blockoverride name: its body, whitespace collapsed}, for one-level blocks."""
    return {m.group(1): " ".join(m.group(2).split())
            for m in re.finditer(r'blockoverride "(\w+)" \{([^{}]*)\}', body)}


def _label_units(text):
    """A label's width in GUI units, formatting dropped."""
    text = re.sub(r"#\w+ |#!", "", text)
    return len(text) * TAB_UNITS * TAB_MARGIN


def _txt_block(text, name):
    return _top_level(text, name)


class MarketTabTest(unittest.TestCase):
    """The Market panel's Climate tab (style guide rule 9; feasibility §5.1): the
    journal entry's own composers under GetPlayerJournalEntry, gated, greyed
    until the entry runs, and ending with Open Journal Entry. Also the strip it
    sits on: te_tab_buttons_six, with vanilla's four tabs unchanged."""

    @classmethod
    def setUpClass(cls):
        cls.market = _read(MARKET)
        cls.buttons = _te_blocks(cls.market, BUTTONS_TAG)
        cls.content = _te_blocks(cls.market, "### TE: Climate tab (te_global_warming) ###")

    def _gw_buttons(self):
        return {k: v for k, v in _overrides(self.buttons[0]).items() if k.startswith("fifth_button")}

    def test_one_button_block_and_one_content_block(self):
        self.assertEqual(len(self.buttons), 1)
        self.assertEqual(len(self.content), 1)
        self.assertIn('name = "te_market_global_warming_tab"', self.content[0])
        self.assertIn("visible = \"[InformationPanel.IsTabSelected('te_global_warming')]\"", self.content[0])

    def test_the_strip_has_six_slots(self):
        fixed_top = self.market[self.market.index('blockoverride "fixed_top"'):
                                self.market.index('blockoverride "scrollarea_content"')]
        self.assertNotRegex(fixed_top, r"(?<!\w)tab_buttons = \{")
        self.assertIn("te_tab_buttons_six = {", fixed_top)
        self.assertIn("type te_tab_buttons_six = hbox", _read(TAB_WIDGETS))
        # The type change is marked as the mod's, as every changed vanilla line is.
        comment = fixed_top[:fixed_top.index("te_tab_buttons_six = {")]
        self.assertIn("### TE: Climate and Reserve tabs", comment)

    def test_vanillas_four_tabs_are_unchanged(self):
        expected = {}
        for slot, tab, label, tooltip, selected in VANILLA_TABS:
            expected[f"{slot}_button"] = f'text = "{label}"'
            if tooltip:
                expected[f"{slot}_button_tooltip"] = f'tooltip = "{tooltip}"'
            expected[f"{slot}_button_click"] = f"onclick = \"[InformationPanel.SelectTab('{tab}')]\""
            expected[f"{slot}_button_visibility"] = f"visible = \"[InformationPanel.IsTabSelected('{tab}')]\""
            expected[f"{slot}_button_visibility_checked"] = (
                f"visible = \"[Not( InformationPanel.IsTabSelected('{tab}') )]\"")
            expected[f"{slot}_button_selected"] = f'text = "{selected}"'
        expected["first_button_name"] = 'name = "tutorial_highlight_market_details"'
        found = {k: v for k, v in _overrides(_strip(self.market)).items()
                 if k.split("_")[0] in ("first", "second", "third", "fourth")}
        self.assertEqual(found, expected)
        # ...and they come before the mod's two, which are all in the marked block.
        strip = _strip(self.market)
        self.assertLess(strip.index('blockoverride "fourth_button_selected"'), strip.index(BUTTONS_TAG))
        for slot in ("fifth", "sixth"):
            self.assertEqual(strip.count(f'blockoverride "{slot}_button'), self.buttons[0].count(f'blockoverride "{slot}_button'))

    def test_the_climate_tab_is_slot_five(self):
        halves = self._gw_buttons()
        self.assertEqual(set(halves), {"fifth_button", "fifth_button_tooltip", "fifth_button_click",
                                       "fifth_button_visibility", "fifth_button_visibility_checked",
                                       "fifth_button_selected"})
        self.assertEqual(halves["fifth_button"], 'text = "te_market_tab_global_warming"')
        self.assertEqual(halves["fifth_button_selected"], 'text = "te_market_tab_global_warming"')

    def test_the_tab_composes_the_journal_roots_types_in_order(self):
        """On the player's own market, the roots' types in the entry's order;
        on another, the same order with the status composer's two sections
        composed one by one (Mitigation Policies under the leader's entry)."""
        body = self.content[0]
        own = _widget_with(body, f'visible = "[{OWN_MARKET}]"')
        foreign = _widget_with(body, f'visible = "[Not( {OWN_MARKET} )]"')
        roots = [wrapped for _, wrapped in ROOTS.values()]
        self.assertEqual(re.findall(r"^\t+(te_\w+) = \{", own, re.M), roots[:2])
        status = re.findall(r"^\t\t(te_gw_sec_\w+) = \{", _type_body(_read(GUI), "te_gw_status_sections"), re.M)
        self.assertEqual(re.findall(r"^\t+(te_\w+) = \{", foreign, re.M),
                         roots[:1] + [s for s in status if s not in OWN_MARKET_ONLY])
        # The reference sections follow both, as the entry's third root does.
        rest = body[body.index(foreign) + len(foreign):]
        self.assertEqual(re.findall(r"^\t+(te_\w+) = \{\}", rest, re.M), roots[2:])
        # The link back to the entry comes after every section.
        self.assertGreater(body.index('text = "te_system_tab_open_journal"'), body.index("te_gw_reference_sections"))
        self.assertIn("onclick = \"[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]\"", body)

    def test_the_gate_sits_above_the_journal_entry_datacontext(self):
        body = self.content[0]
        dc = body.index("datacontext = \"[GetPlayerJournalEntry('je_global_warming')]\"")
        self.assertLess(body.index(f'visible = "[{GW_TAB_GATE}]"'), dc)
        # The header sits outside the gate.
        self.assertLess(body.index('text = "je_global_warming"'), body.index(f'visible = "[{GW_TAB_GATE}]"'))
        # Never on the widget that carries the datacontext itself.
        opener = body.rindex("flowcontainer = {", 0, dc)
        self.assertNotIn("visible", body[opener:dc])

    def test_the_column_is_as_wide_as_the_journal_roots(self):
        body = self.content[0]
        dc = body.index("GetPlayerJournalEntry('je_global_warming')")
        head = body[dc:body.index("te_gw_overview_panel", dc)]
        self.assertIn("minimumsize = { 520 -1 }", head)
        self.assertIn("parentanchor = hcenter", head)

    def test_the_button_is_greyed_until_the_entry_runs(self):
        halves = self._gw_buttons()
        self.assertEqual(halves["fifth_button_click"],
                         f'enabled = "[{GW_TAB_GATE}]" onclick = "[InformationPanel.SelectTab(\'te_global_warming\')]"')
        self.assertIn(f"{GW_TAB_UNLOCK}.IsValidTooltip(", halves["fifth_button_tooltip"])
        self.assertIn("'te_market_tab_global_warming_tt'", halves["fifth_button_tooltip"])
        self.assertIn("'te_market_tab_global_warming_locked_tt'", halves["fifth_button_tooltip"])
        for half in ("fifth_button_visibility", "fifth_button_visibility_checked"):
            self.assertIn("IsTabSelected('te_global_warming')", halves[half], half)
            self.assertIn(f"{GW_TAB_UNLOCK}.IsShown(", halves[half], half)
        for key in ("te_market_tab_global_warming", "te_market_tab_global_warming_tt",
                    "te_market_tab_global_warming_locked_tt", "te_market_global_warming_open_journal_tt",
                    "gw_entry_unlock_tt"):
            self.assertTrue(_loc_value(key), key)

    def test_climate_shows_on_every_market(self):
        """The tab button does not ask which market the panel shows (the
        Reserve tab's does); the content does, to pick whose market it shows."""
        self.assertNotIn("IsSame", " ".join(self._gw_buttons().values()))
        self.assertEqual(self.content[0].count(f'visible = "[{OWN_MARKET}]"'), 1)
        self.assertEqual(self.content[0].count(f'visible = "[Not( {OWN_MARKET} )]"'), 1)

    def test_another_markets_parts_read_its_leader_as_a_country(self):
        """The market parts on another market read its leader as a Country
        datacontext, never another country's journal entry (gotcha #35): the
        intro line, and the overview and the policies through their
        gw_market_country block. Each sits under the gate on the leader's entry
        running, and never carries a visible of its own."""
        body = self.content[0]
        self.assertEqual(re.findall(r"\.GetJournalEntry\(", body), [])
        self.assertEqual(re.findall(r"GetPlayerJournalEntry\('(\w+)'\)", body), ["je_global_warming"])
        foreign = _widget_with(body, f'visible = "[Not( {OWN_MARKET} )]"')
        sites = [m.start() for m in re.finditer(re.escape(f'datacontext = "[{LEADER}]"'), foreign)]
        self.assertEqual(len(sites), 3)   # the intro line, the overview's market cells, the policies
        for at in sites:
            gate = foreign.rfind(f'visible = "[{LEADER_GATE}]"', 0, at)
            self.assertNotEqual(gate, -1)
            gated = _widget_with(foreign, f'visible = "[{LEADER_GATE}]"', start=gate)
            self.assertIn(foreign[at:at + 50], gated)
            opener = max(foreign.rfind("flowcontainer = {", 0, at), foreign.rfind("blockoverride", 0, at))
            self.assertNotIn("visible", foreign[opener:at])
        for section in ("te_gw_overview_panel", "te_gw_sec_policies"):
            self.assertRegex(foreign, section + r' = \{\s*blockoverride "gw_market_country" \{\s*'
                                      + re.escape(f'datacontext = "[{LEADER}]"') + r"\s*\}\s*\}", section)
        self.assertRegex(foreign, re.escape(f'datacontext = "[{LEADER}]"') + r'\s*parentanchor = hcenter\s*'
                                  r'gw_text = \{\s*align = hcenter\|nobaseline\s*text = "te_market_gw_foreign_intro"')
        # Top Emitters stays the player's: no Country override reaches it.
        self.assertIn("te_gw_sec_emitters = {}", foreign)
        self.assertNotIn("te_gw_sec_emitters", _widget_with(foreign, f'visible = "[{LEADER_GATE}]"', start=foreign.rfind(
            f'visible = "[{LEADER_GATE}]"', 0, foreign.index("te_gw_sec_policies"))))
        # Until the leader's entry runs, one line says so.
        self.assertRegex(foreign, r'visible = "\[Not\( ' + re.escape(LEADER_GATE) + r' \)\]"\s*'
                                  r'align = hcenter\|nobaseline\s*text = "te_market_gw_foreign_pending"')
        gate = _txt_block(_read(TAB_SGUIS), "te_market_global_warming_leader_sgui")
        self.assertIn("is_shown = { has_journal_entry = je_global_warming }", gate)
        self.assertIn(f"{LEADER}.MakeScope", LEADER_GATE)

    def test_each_market_part_reads_country_from_a_block(self):
        """The overview's four market cells and the policies' root carry block
        gw_market_country, whose default is the entry's own country, so the
        journal and the own-market view read as they did. Inside them every
        read is `Country`; outside them, the overview still reads the player's
        JournalEntry (the temperature, the tier, the penalty, the world rows)."""
        gui = _read(GUI)
        ov = _type_body(gui, "te_gw_overview_panel")
        self.assertEqual(ov.count(MARKET_BLOCK), 4)
        cells = [_block_from(ov, m.end()) for m in re.finditer(re.escape(MARKET_BLOCK), ov)]
        self.assertEqual([" ".join(c.split()) for c in cells], [MARKET_DEFAULT] * 4)
        self.assertRegex(ov, r"### Row 1:[^\n]*\n\t+flowcontainer = \{[^{}]*" + re.escape(MARKET_BLOCK))
        self.assertRegex(ov, r"### Row 4:[^\n]*\n[^\n]*\n\t+flowcontainer = \{[^{}]*" + re.escape(MARKET_BLOCK))
        for tip in ("gw_cond_emis_tt", "gw_emis_capture_tt"):
            self.assertRegex(ov, r"gw_value_row = \{\s*" + re.escape(MARKET_BLOCK) + r"\s*" + re.escape(MARKET_DEFAULT)
                             + rf'\s*\}}\s*tooltip = "{tip}"', tip)
        # Inside the market cells every read is Country; outside, none is.
        for cell in _market_cells(ov):
            self.assertNotIn("JournalEntry", cell.replace(MARKET_DEFAULT, ""))
        rest = ov
        for m in re.finditer(re.escape(MARKET_BLOCK), ov):
            rest = rest.replace(_widget_with(ov, MARKET_BLOCK, start=m.start()), "")
        self.assertEqual(re.findall(r"(?<![\w.'])Country\.\w+", rest), [])
        self.assertIn("JournalEntry.GetCountry.MakeScope.ScriptValue('gw_disp_tier_code')", rest)
        # The policies: the block on the root, and nothing but Country below it.
        pol = _type_body(gui, "te_gw_sec_policies")
        self.assertRegex(pol, r"^\s*direction = vertical\s*parentanchor = hcenter\s*ignoreinvisible = yes\s*spacing = 4\s*"
                              + re.escape(MARKET_BLOCK) + r"\s*" + re.escape(MARKET_DEFAULT))
        for name in COUNTRY_TYPES:
            body = _type_body(gui, name).replace(MARKET_DEFAULT, "")
            self.assertNotIn("JournalEntry", body, name)
        # The journal's roots instance both types bare, so the defaults hold there.
        root = gui.split('name = "widget_je_gw_overview"', 1)[1]
        self.assertIn("te_gw_overview_panel = {}", root[:root.index("}") + 1])
        self.assertIn("te_gw_sec_policies = {}", _type_body(gui, "te_gw_status_sections"))

    def test_the_market_parts_loc_reads_country(self):
        """The loc the market parts show reads Country, never JournalEntry, so
        it follows the block's datacontext; the tier and penalty keys in row 1
        stay on the player's JournalEntry."""
        gui = _read(GUI)
        ov = _type_body(gui, "te_gw_overview_panel")
        parts = _market_cells(ov) + [_type_body(gui, n) for n in COUNTRY_TYPES]
        keys = set()
        for part in parts:
            keys |= set(re.findall(r'(?:text|tooltip) = "(\w+)"', part)) | set(re.findall(r"'(gw_\w+)'", part))
        seen, stack = set(), sorted(keys)
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            try:
                value = _loc_value(k)
            except AssertionError:
                continue
            stack += re.findall(r"'(\w+)'", value)
            self.assertNotIn("JournalEntry", value, k)
        self.assertIn("gw_emis_market_value", seen)
        self.assertIn("gw_btn_not_ours_tt", seen)
        self.assertIn("[Country.GetName]", _loc_value("te_market_gw_foreign_intro"))

    def test_the_controls_are_greyed_off_the_players_entry(self):
        """Adopt and Repeal act only for the local player: greyed, with a
        tooltip naming the leader, on anyone else's Country; the handlers'
        effects also require is_player. In the journal the section's Country
        is the player's, so the button reads as before."""
        gui = _read(GUI)
        for name, op in (("gw_adopt_button", "0"), ("gw_repeal_button", "1")):
            body = _type_body(gui, name)
            scope = f"GuiScope.SetRoot( Country.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint){op}' ) ).End"
            self.assertIn(f'enabled = "[And( Country.IsLocalPlayer, ScriptedGui.IsValid( {scope} ) )]"', body, name)
            self.assertIn(f'onclick = "[ScriptedGui.Execute( {scope} )]"', body, name)
            self.assertIn("tooltip = \"[SelectLocalization( Country.IsLocalPlayer, Concatenate( "
                          f"ScriptedGui.IsValidTooltip( {scope} )", body, name)
            self.assertTrue(body.rstrip().endswith("'gw_btn_not_ours_tt' )]\""), name)
        self.assertIn("[Country.GetName]", _loc_value("gw_btn_not_ours_tt"))
        sguis = _read(SGUIS)
        for p in MARKET_WIDE + NATIONAL:
            handler = _top_level(sguis, f"gw_policy_{p}_sgui")
            effect = _block_from(handler, handler.index("effect = {") + len("effect = {"))
            limits = re.findall(r"limit = \{ ([^}]*) \}", effect)
            self.assertEqual(limits, ["scope:op = 0 is_player = yes", "scope:op = 1 is_player = yes"], p)
            valid = _block_from(handler, handler.index("is_valid = {") + len("is_valid = {"))
            self.assertNotIn("is_player", valid, p)   # the tooltip's conditions are unchanged

    def test_our_labels_switch_on_the_same_test(self):
        """A label or tooltip of the market cells that says "our" or "we"
        picks its wording on Country.IsLocalPlayer: the journal's text for the
        player's own country, the market's for a leader's."""
        for key in OUR_KEYS:
            self.assertEqual(_loc_value(key), f"[SelectLocalization( Country.IsLocalPlayer, "
                                              f"'{key}_ours', '{key}_theirs' )]", key)
            theirs = _loc_value(f"{key}_theirs")
            self.assertTrue(_loc_value(f"{key}_ours"), key)
            self.assertNotRegex(theirs, r"\b([Oo]ur|[Oo]urs|[Ww]e|[Uu]s)\b", key)
        for key in ("gw_ov_pie_share_value", "gw_ov_pie_share_pending"):
            self.assertTrue(_loc_value(key).startswith("[SelectLocalization( Country.IsLocalPlayer, "
                                                       "'gw_ov_share_ours', 'gw_ov_share_theirs' )] "), key)
        self.assertIn("[SelectLocalization( Country.IsLocalPlayer, 'gw_ov_cut_policies_ours', "
                      "'gw_ov_cut_policies_theirs' )]", _loc_value("gw_ov_pie_cut_tt"))
        # ...and every one of them is a market cell's.
        ov = _type_body(_read(GUI), "te_gw_overview_panel")
        for key in OUR_KEYS:
            self.assertIn(f'"{key}"', ov, key)

    def test_the_market_cells_read_no_players_only_figure(self):
        """The data audit: what the leader's cells read exists for an AI
        leader. The market figures are written for every market leader each
        year (no is_player on the site that writes them); the players-only
        snapshots (Top Emitters' rows, the history store) feed only sections
        that stay the player's."""
        ov = _type_body(_read(GUI), "te_gw_overview_panel")
        pol = _type_body(_read(GUI), "te_gw_sec_policies")
        for players_only in ("gw_disp_emitters_", "gw_emitter_", "te_hist"):
            self.assertNotIn(players_only, ov + pol, players_only)
        pulse = _read(os.path.join(REPO, "common", "on_actions", "extra_on_actions.txt"))
        at = pulse.index("gw_snapshot_market_emissions_effect = yes")
        site = pulse[pulse.rindex("if = {", 0, at):at]
        self.assertIn("owner.market_capital = THIS", site)
        self.assertNotIn("is_player", site)

    def test_the_tooltip_has_three_branches(self):
        """Open: the tab's own tooltip. Conditions met but the entry not
        running: te_market_tab_met_tt, since IsValidTooltip prints nothing for
        a passing test. Otherwise: the locked line and the checklist."""
        root = "GuiScope.SetRoot( GetPlayer.MakeScope ).End"
        expected = (f"tooltip = \"[SelectLocalization( {GW_TAB_GATE}, 'te_market_tab_global_warming_tt', "
                    f"SelectLocalization( {GW_TAB_UNLOCK}.IsValid( {root} ), 'te_market_tab_met_tt', "
                    f"Concatenate( Localize( 'te_market_tab_global_warming_locked_tt' ), "
                    f"{GW_TAB_UNLOCK}.IsValidTooltip( {root} ) ) ) )]\"")
        self.assertEqual(self._gw_buttons()["fifth_button_tooltip"], expected)
        met = _loc_value("te_market_tab_met_tt")
        self.assertTrue(met.startswith("#b Not open yet#!"), met)
        self.assertIn("conditions are met", met)

    def test_no_tab_icon(self):
        """System tabs carry no icon, as vanilla's tabs don't (the owner, 2026-09-30):
        none in a *_button_icon block, none as a text icon in the label."""
        self.assertEqual([k for k in _overrides(self.buttons[0]) if k.endswith("_icon")], [])
        self.assertNotIn("@", _loc_value("te_market_tab_global_warming"))

    def test_the_label_fits_one_of_six_slots(self):
        self.assertLessEqual(_label_units(_loc_value("te_market_tab_global_warming")), SIX_SLOT)

    def test_the_gates_read_the_rule_and_the_entry(self):
        sguis = _read(TAB_SGUIS)
        gate = _txt_block(sguis, "te_market_global_warming_tab_sgui")
        self.assertIn("has_journal_entry = je_global_warming", gate)
        unlock = _txt_block(sguis, "te_market_global_warming_tab_unlock_sgui")
        self.assertIn("is_valid = { gw_entry_unlocked = yes }", unlock)
        # The tab is on the strip whenever the greyed entry is in the journal:
        # under the rule, or with a restrictive transition law (#660), whose
        # entry opens with the rule off too.
        shown = re.search(r"is_shown = \{\s*OR = \{([^{}]*)\}\s*\}", unlock)
        self.assertTrue(shown, unlock)
        for clause in ("has_game_rule = global_warming_enabled", "rt_restrictive_transition_law = yes"):
            self.assertIn(clause, shown.group(1))
        self.assertRegex(_read(JE), r"is_shown_when_inactive = \{\s*OR = \{\s*has_game_rule = global_warming_enabled\s*"
                                    r"rt_restrictive_transition_law = yes\s*\}\s*\}")

    def test_the_checklist_is_the_entrys_own_test_in_one_line(self):
        trig = _top_level(_read(TRIGGERS), "gw_entry_unlocked")
        m = re.search(r"custom_tooltip = \{\s*text = gw_entry_unlock_tt", trig)
        self.assertTrue(m, trig)
        tested = _block_from(trig, trig.index("{", m.start()) + 1)
        tested = tested.split("text = gw_entry_unlock_tt", 1)[1]
        possible = _top_level(_read(JE), "je_global_warming")
        possible = _block_from(possible, possible.index("possible = {") + len("possible = {"))
        self.assertEqual(" ".join(tested.split()), " ".join(possible.split()))
        self.assertIn("0.1", _loc_value("gw_entry_unlock_tt"))

    def test_what_the_journal_draws_besides_the_roots_needs_nothing_in_the_tab(self):
        """§5.1: the goal bar, scripted bars, status text and human buttons."""
        je = _read(JE)
        # The overview draws the temperature bar; the marker hides the journal's own.
        self.assertIn('container = "custom_widget_container_7"', je)
        self.assertNotIn("scripted_progress_bar", je)
        # The status text is empty while the entry is active.
        self.assertEqual(_loc_value("je_global_warming_status_none"), "")
        # Every scripted button is the AI's.
        # Eighteen climate buttons and six retirement programme buttons (#660).
        names = re.findall(r"(?m)^\tscripted_button = (\w+)", je)
        self.assertEqual(len(names), 24)
        buttons = _read(BUTTONS) + "\n" + _read(RT_BUTTONS)
        for name in names:
            self.assertRegex(_top_level(buttons, name), r"visible = \{\s*is_ai = yes", name)

    def test_top_emitters_needs_nothing_from_the_panel(self):
        """#590's section works in the tab as in the journal: it is composed
        there, its rows set their own State datacontext, its two list tooltips
        take a state root, and no type reads the panel's ambient Market."""
        self.assertIn("te_gw_sec_emitters = {}", _type_body(_read(GUI), "te_gw_status_sections"))
        emitters = _type_body(_read(GUI), "te_gw_sec_emitters")
        self.assertIn("datacontext = \"[JournalEntry.GetCountry.MakeScope.Var('gw_emitter_1').GetState]\"", emitters)
        self.assertIn("GetScriptedGui('gw_top_emitters_sgui').ExecuteTooltip( GuiScope.SetRoot( "
                      "JournalEntry.GetCountry.GetCapital.MakeScope ).End )", emitters)
        self.assertIn("GetScriptedGui('gw_te_members_sgui').ExecuteTooltip( GuiScope.SetRoot( State.MakeScope ).End )",
                      _loc_value("gw_te_row_tt"))
        sguis = _read(SGUIS)
        for name in ("gw_te_members_sgui", "gw_top_emitters_sgui"):
            self.assertIn("scope = state", _top_level(sguis, name), name)
        code = "\n".join(line.split("#", 1)[0] for line in _read(GUI).splitlines())
        ambient = re.findall(r"(?<![\w.'])(Market|GetPlayer|GetMetaPlayer)\.\w+", code)
        self.assertEqual(ambient, [])
        # Country is only ever the section's own (a gw_market_country block's),
        # never the panel's: none in Top Emitters, History or How.
        for name in ("te_gw_sec_emitters", "gw_emitter_row", "gw_emitter_header", "te_gw_sec_history", "te_gw_sec_how"):
            self.assertEqual(re.findall(r"(?<![\w.'])Country\.\w+", _type_body(_read(GUI), name)), [], name)

    def test_one_visible_per_widget(self):
        for i, block in enumerate(self.buttons + self.content):
            stack = [0]
            for line in block.splitlines():
                s = line.strip()
                if s.startswith("visible ="):
                    stack[-1] += 1
                    self.assertLessEqual(stack[-1], 1, f"block {i}: two visibles near {s[:60]}")
                stack.extend([0] * line.count("{"))
                for _ in range(line.count("}")):
                    if len(stack) > 1:
                        stack.pop()


if __name__ == "__main__":
    unittest.main()
