"""Global Warming panels: section order, collapse defaults, state-gated lines, the
warming ladder's one definition, and the placeholder icon list
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

STATUS = ["te_gw_sec_emissions", "te_gw_sec_policies"]
REFERENCE = ["te_gw_sec_history", "te_gw_sec_how"]
ROOTS = {"widget_je_gw_overview": ("custom_widget_container_1", "te_gw_overview_panel"),
         "widget_je_gw_status": ("custom_widget_container_2", "te_gw_status_sections"),
         "widget_je_gw_reference": ("custom_widget_container_3", "te_gw_reference_sections")}
FLAGS = {"gw_emissions_closed", "gw_policies_closed", "gw_world_closed", "gw_hist_closed", "gw_how_open"}
OLD_FLAGS = ["gw_hist_open", "gw_world_open"]
MARKET_WIDE = ["carbon_tax", "renewable_investment", "emission_standards"]
NATIONAL = ["climate_adaptation", "reforestation", "public_transit", "fossil_fuel_divestment",
            "green_building_codes"]
# Textures in the widget that are not placeholders for art still to come.
NOT_PLACEHOLDERS = {"gfx/interface/backgrounds/round_frame_dec.dds",
                    "gfx/interface/progressbar/progressbar_marker.dds",
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
        body = _type_body(_read(GUI), "te_gw_sec_emissions")
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
        self.assertEqual(len(icons), 2)
        shown = "ScriptedGui.IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )"
        self.assertIn(f'visible = "[{shown}]"', icons[0])
        self.assertNotIn("alpha", icons[0])
        self.assertIn(f'visible = "[Not( {shown} )]"', icons[1])
        self.assertIn("alpha = 0.25", icons[1])


class HowItWorksTest(unittest.TestCase):
    def test_explanations_live_in_how_global_warming_works(self):
        gui = _read(GUI)
        how = _type_body(gui, "te_gw_sec_how")
        notes = re.findall(r'gw_note = \{\s*text = "(\w+)"', how)
        self.assertGreaterEqual(len(notes), 6)
        self.assertTrue(all(n.startswith("gw_how_") for n in notes), notes)
        self.assertIn("GetVariableSystem.Toggle('gw_how_open')", how)
        for sec in ("te_gw_overview_panel", "te_gw_sec_emissions", "te_gw_sec_policies", "te_gw_sec_history"):
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
        body = _type_body(_read(GUI), "te_gw_sec_emissions")
        self.assertRegex(body, r"minimumsize = \{ 480 -1 \}\s*visible = \"\[GetScriptedGui\('gw_has_yearly_figures_sgui'\)")


class LocTest(unittest.TestCase):
    def test_every_key_the_widget_names_exists(self):
        keys = _loc_keys()
        gui = _read(GUI)
        named = set(re.findall(r'\b(?:text|tooltip) = "([A-Za-z]\w*)"', gui))
        named |= set(re.findall(r"(?:Localize|SelectLocalization)\([^\]]*?'(\w+)'", gui))
        missing = sorted(k for k in named if "_" in k and k not in keys)
        self.assertEqual(missing, [])


class IconsDocTest(unittest.TestCase):
    def test_every_placeholder_is_listed(self):
        textures = set(re.findall(r'texture = "(gfx/[^"]+)"', _read(GUI))) - NOT_PLACEHOLDERS
        doc = _read(ICONS_DOC)
        listed = set(re.findall(r"`(gfx/[^`]+\.dds)`", doc))
        self.assertTrue(textures)
        self.assertEqual(textures - listed, set(), "placeholder textures missing from the icons doc")


if __name__ == "__main__":
    unittest.main()
