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

STATUS = ["te_gw_sec_policies"]
REFERENCE = ["te_gw_sec_history", "te_gw_sec_how"]
ROOTS = {"widget_je_gw_overview": ("custom_widget_container_1", "te_gw_overview_panel"),
         "widget_je_gw_status": ("custom_widget_container_2", "te_gw_status_sections"),
         "widget_je_gw_reference": ("custom_widget_container_3", "te_gw_reference_sections")}
FLAGS = {"gw_policies_closed", "gw_world_closed", "gw_hist_closed", "gw_how_open"}
OLD_FLAGS = ["gw_hist_open", "gw_world_open", "gw_emissions_closed"]
MARKET_WIDE = ["carbon_tax", "renewable_investment", "emission_standards"]
NATIONAL = ["climate_adaptation", "reforestation", "public_transit", "fossil_fuel_divestment",
            "green_building_codes"]
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
    def test_eight_rows_market_wide_first_each_wired_to_its_own_handlers(self):
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
        shown = "ScriptedGui.IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )"
        self.assertIn(f'visible = "[{shown}]"', icons[0])
        self.assertNotIn("alpha", icons[0])
        self.assertIn(f'visible = "[Not( {shown} )]"', icons[1])
        self.assertIn("alpha = 0.25", icons[1])

    def test_status_is_a_check_not_a_word(self):
        """Play-test round 3: "Active"/"Inactive" became a green check, freeing
        the width the names needed; the words stay on the icon's hover."""
        row = _type_body(_read(GUI), "gw_policy_row")
        shown = "ScriptedGui.IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )"
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
        rows = re.findall(r'gw_value_row = \{\s*tooltip = "(\w+)"\s*blockoverride "row_label" \{\s*text = "(\w+)"', body)
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
            ("gw_emis_market_label", "medium", self.label_cell),
            ("gw_emis_capture_label", "medium", self.label_cell),
            ("gw_emis_world_label", "medium", self.label_cell),
            ("gw_emis_warming_label", "medium", self.label_cell),
            ("gw_sect_world", "medium", 440 - 32),        # nested header, text after its arrow
            ("gw_sect_policies", "large", 480),           # section headers, 520 with the arrow
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
            (_visible_text(_loc_value("gw_ov_pie_share_pending")), "medium", self.pie_cell,
             "share pie label, pending"),
            ("-999.9/yr", "medium", self.value_cell, "an emissions value"),
            ("99999/yr", "medium", self.value_cell, "world emissions"),
            ("+0.20 °C", "medium", self.value_cell, "warming last year"),
            ("136 nations", "medium", self.value_cell, "an adoption count (every country)"),
        ]
        for text, font, cell, what in cases:
            self.assertFits(text, font, cell, what)


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
        leader = re.search(r"IsShown\( GuiScope\.SetRoot\( JournalEntry\.GetCountry\.MakeScope \)\.End \)\]\"\s*"
                           r"blockoverride \"icon_texture\" \{\s*texture = \"([^\"]+)\"", self.overview)
        member = re.search(r"IsShown\( GuiScope\.SetRoot\( JournalEntry\.GetCountry\.MakeScope \)\.End \) \)\]\"\s*"
                           r"blockoverride \"icon_texture\" \{\s*texture = \"([^\"]+)\"", self.overview)
        self.assertEqual(leader.group(1), f"{GW_ICONS}role_leader.dds")
        self.assertEqual(member.group(1), f"{GW_ICONS}role_member.dds")
        self.assertRegex(self.overview, rf'tooltip = "gw_cond_penalty_tt"\s*blockoverride "icon_texture" \{{\s*'
                                        rf'texture = "{re.escape(GW_ICONS)}penalty\.dds"')

    def test_every_policy_has_its_own_file(self):
        for p in MARKET_WIDE + NATIONAL:
            self.assertRegex(self.policies, rf"GetScriptedGui\('gw_active_{p}_sgui'\)\]\"\s*"
                                            rf'blockoverride "row_icon" \{{\s*texture = "{re.escape(GW_ICONS)}policy_{p}\.dds"', p)

    def test_pies(self):
        for pie, key in (("pie_share", "gw_ov_pie_share"), ("pie_cut", "gw_ov_pie_cut")):
            self.assertRegex(self.overview, rf'texture = "{re.escape(GW_ICONS)}{pie}\.dds"\s*\}}\s*'
                                            rf'blockoverride "label" \{{\s*text = "{key}"')

    def test_no_placeholder_left(self):
        textures = set(re.findall(r'texture = "(gfx/[^"]+)"', self.gui))
        self.assertEqual(textures & OLD_PLACEHOLDERS, set())
        icons = textures - NOT_ICONS - VANILLA_MARKS - {"gfx/interface/icons/un_icons/pie_rest.dds",
                                                        "gfx/interface/icons/un_icons/pie_members.dds"}
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


if __name__ == "__main__":
    unittest.main()
