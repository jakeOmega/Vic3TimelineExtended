"""The legislated tax code's journal entry and Budget > Tax Code tab (plan Task 7).

Structural checks on the committed GUI and script (no game install needed), in
the spirit of test_banking_layout.py:

* the Budget panel's fifth tab slot carries the Tax Code tab, gated by the
  te_budget_tax_tab_sgui / te_budget_tax_tab_unlock_sgui pair, and its content
  block (tab name te_tax_code) composes the overview, te_tax_status_sections and
  te_tax_reference_sections, in that order, ending with Open Journal Entry;
* je_tax_code mounts the three named roots in custom_widget_container_1/2/3,
  every root and composer is gated on JournalEntry.IsActive, the entry exists
  only under the rule (positively) for a migrated country, never completes and
  writes nothing on activation;
* every collapse flag is named for its default (gui_style_guide.md rule 7);
* every number the panels show is a guarded display value: each
  ScriptValue('x') in the new .gui files, and in the loc they print, names a
  te_tax_view_* value whose body tests every variable it reads with
  has_variable and holds no world iterator and no effect;
* the history rows read the ring newest first, and their text covers every
  history kind.

Run: python3 -m unittest test_tax_code_layout -v
"""

import json
import re
import unittest
from pathlib import Path

from test_tax_code_state import KEYS, block, close, gen, top_level_names

ROOT = Path(__file__).resolve().parent

OVERVIEW = "gui/journal_entry_widgets/te_tax_overview_widget.gui"
LAYOUT = "gui/journal_entry_widgets/te_tax_layout_widget.gui"
WORKBENCH = "gui/journal_entry_widgets/te_tax_workbench_widget.gui"
REVIEW = "gui/journal_entry_widgets/te_tax_review_widget.gui"
POLITICS = "gui/journal_entry_widgets/te_tax_politics_widget.gui"
GEN_ROWS = "gui/journal_entry_widgets/te_tax_generated_rows.gui"
BUDGET = "gui/budget_panel.gui"
LIGHT_GUI = "gui/journal_entry_widgets/te_tax_light_widget.gui"
NEW_GUI = (OVERVIEW, LAYOUT, WORKBENCH, REVIEW, POLITICS, GEN_ROWS, LIGHT_GUI)
LIGHT_SGUIS = "common/scripted_guis/te_tax_light_sguis.txt"
LIGHT_GEN_SGUIS = "common/scripted_guis/te_tax_light_generated_sguis.txt"
# The light setting's display gate, as the composers test it.
LIGHT_SHOWN = "GetScriptedGui('te_tax_show_light_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"
JE = "common/journal_entries/je_tax_code.txt"
TAB_SGUIS = "common/scripted_guis/te_system_tab_sguis.txt"
TAX_SGUIS = "common/scripted_guis/te_tax_sguis.txt"
GEN_SGUIS = "common/scripted_guis/te_tax_generated_sguis.txt"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
DISPLAY = "common/script_values/te_tax_display_values.txt"
GEN_VALUES = "common/script_values/te_tax_generated_values.txt"
SUPPORT = "common/script_values/te_tax_support_values.txt"
GEN_CUSTOM_LOC = "common/customizable_localization/te_tax_generated_custom_loc.txt"
CONCEPTS = "common/game_concepts/extra_concepts.txt"
LOC_DIR = "localization/english"
TAX_LOC = "localization/english/te_tax_l_english.yml"
GUIDE = "docs/guides/gui_modding_guide.md"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"

TAB = "te_tax_code"
# The live sections, in order: the ones to watch first, the editor last (GUI
# audit TAX-14; the owner, 2026-10-27). The draft's summary sits in the
# composer's "draft_summary" block after the workbench; the Budget tab empties
# that block and shows the summary in its fixed_bottom instead.
STATUS = ["te_tax_politics_section", "te_tax_pending_section", "te_tax_obligations_section",
          "te_tax_enacted_table", "te_tax_workbench_section", "te_tax_review_section"]
# Collapse flags, each named for its default (style guide rule 7).
FLAGS = {"te_tax_enacted_closed", "te_tax_history_open", "te_tax_how_open",
         "te_tax_workbench_closed", "te_tax_wb_income_closed", "te_tax_wb_land_closed",
         "te_tax_wb_cons_closed", "te_tax_wb_goods_open", "te_tax_wb_relief_closed", "te_tax_wb_customs_open",
         "te_tax_wb_relief_states_closed", "te_tax_wb_dates_closed", "te_tax_review_open", "te_tax_politics_closed",
         "te_tax_pending_closed", "te_tax_obligations_closed", "te_tax_light_closed", "te_tax_light_how_open"}
REFERENCE = ["te_tax_history_section", "te_tax_how_section"]
ROOTS = [("widget_je_tax_code_overview", "custom_widget_container_1"),
         ("widget_je_tax_code_status", "custom_widget_container_2"),
         ("widget_je_tax_code_reference", "custom_widget_container_3")]
FIFTH = ("fifth_button", "fifth_button_tooltip", "fifth_button_click", "fifth_button_visibility",
         "fifth_button_visibility_checked", "fifth_button_selected")
HISTORY_SIZE = 8
# History kinds (docs/systems/tax_code_schema.md, te_tax_h<n>_kind): 1-10 the code's,
# 11-14 the policy obligations' (Task 12), 15-18 the customs schedule's (Task 15).
KINDS = range(1, 19)
SUNSET_KIND = 2
FORBIDDEN_IN_VALUES = re.compile(
    r"\b(set_variable|change_variable|remove_variable|save_scope_as|save_temporary_scope_as|"
    r"every_\w+|any_\w+|random_\w+|ordered_\w+|add_modifier|trigger_event)\b")


def raw(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def uncomment(text):
    """Drop `#` comments outside double quotes (loc formatting like "#title" stays)."""
    out = []
    for line in text.split("\n"):
        in_quotes = False
        for i, char in enumerate(line):
            if char == '"':
                in_quotes = not in_quotes
            elif char == "#" and not in_quotes:
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def gui(path):
    return uncomment(raw(path))


def script(path):
    return uncomment(raw(path))


def brace_block(text, start):
    """The `{ ... }` block opening at or after `start`, braces included."""
    j = text.index("{", start)
    return text[j:close(text, j) + 1]


def type_body(text, name):
    match = re.search(rf"\btype {name} = \w+ \{{", text)
    assert match, f"no type {name}"
    return brace_block(text, match.end() - 1)[1:-1]


def loc():
    keys = {}
    for path in sorted((ROOT / LOC_DIR).glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
            if match:
                keys[match.group(1)] = match.group(2)
    return keys


def tax_loc():
    keys = {}
    for line in raw(TAX_LOC).splitlines():
        match = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
        if match:
            keys[match.group(1)] = match.group(2)
    return keys


def mod_block(text, marker="### MOD: Tax Code tab"):
    """Every `### MOD: Tax Code tab` ... `### END MOD ###` region, in order."""
    regions = []
    start = text.find(marker)
    while start != -1:
        end = text.index("### END MOD ###", start)
        regions.append(text[start:end])
        start = text.find(marker, end)
    return regions


def loc_keys_named_in(text):
    """Loc keys a .gui names: text/tooltip = "key", Localize('key') and the
    comma-led quoted arguments of SelectLocalization (a quoted argument opening
    a call, such as ScriptValue('x'), is not one; check_gui_lint.loc_args)."""
    keys = set(re.findall(r'\b(?:text|tooltip)\s*=\s*"([A-Za-z_][\w.]*)"', text))
    for match in re.finditer(r"\b(Localize|SelectLocalization)\(", text):
        depth, end = 1, len(text)
        for j in range(match.end(), len(text)):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        lead = r"^\s*" if match.group(1) == "Localize" else r",\s*"
        keys |= set(re.findall(lead + r"'([A-Za-z_]\w*)'", text[match.end():end]))
    return keys


def reachable_loc(keys, table):
    """`keys` and every key their values splice in with $key$, transitively."""
    seen, todo = set(), list(keys)
    while todo:
        key = todo.pop()
        if key in seen or key not in table:
            continue
        seen.add(key)
        todo += re.findall(r"\$(\w+)\$", table[key])
    return seen


def value_bodies():
    """{name: body or None} for the tax code's script values; None = a constant."""
    values = {}
    for path in (DISPLAY, GEN_VALUES, SUPPORT, "common/script_values/te_tax_generated_support_values.txt",
                 "common/script_values/te_tax_obligation_values.txt",
                 "common/script_values/te_tax_light_generated_values.txt"):
        text = script(path)
        for match in re.finditer(r"(?m)^(\w+) = (\{|-?[\d.]+)", text):
            name = match.group(1)
            values[name] = text[match.end(2):close(text, match.end(2) - 1)] if match.group(2) == "{" else None
    return values


class TabStripTest(unittest.TestCase):
    """Budget's tab strip: the fifth slot, greyed until the entry runs."""

    @classmethod
    def setUpClass(cls):
        cls.text = gui(BUDGET)
        cls.regions = mod_block(raw(BUDGET))

    def test_three_marked_blocks(self):
        """The tab strip, the tab's content and the draft summary's footer."""
        self.assertEqual(len(self.regions), 3)

    def test_strip_block_follows_banking_inside_tab_buttons(self):
        text = raw(BUDGET)
        strip = text.index("### MOD: Tax Code tab")
        banking_end = text.index("### END MOD ###", text.index("### MOD: Banking tab"))
        self.assertGreater(strip, banking_end)
        tab_buttons = text.index("te_tab_buttons_six = {")
        self.assertLess(strip, close(text, text.index("{", tab_buttons)))

    def test_the_six_fifth_slot_blocks_and_no_icon(self):
        strip = uncomment(self.regions[0])
        found = re.findall(r'blockoverride "(fifth_button\w*)"', strip)
        self.assertEqual(sorted(found), sorted(FIFTH))
        self.assertNotIn("_icon", strip)

    def _override(self, name):
        strip = uncomment(self.regions[0])
        return brace_block(strip, strip.index(f'blockoverride "{name}"'))

    def test_click_selects_the_tab_and_is_enabled_by_the_running_entry(self):
        click = self._override("fifth_button_click")
        self.assertIn("enabled = \"[GetScriptedGui('te_budget_tax_tab_sgui').IsShown(", click)
        self.assertIn(f"onclick = \"[InformationPanel.SelectTab('{TAB}')]\"", click)

    def test_both_halves_test_the_tab_and_the_unlock_gate(self):
        gate = "GetScriptedGui('te_budget_tax_tab_unlock_sgui').IsShown("
        selected = self._override("fifth_button_visibility")
        self.assertIn(f"InformationPanel.IsTabSelected('{TAB}')", selected)
        self.assertIn(gate, selected)
        self.assertNotIn("Not(", selected)
        unselected = self._override("fifth_button_visibility_checked")
        self.assertIn(f"Not( InformationPanel.IsTabSelected('{TAB}') )", unselected)
        self.assertIn(gate, unselected)

    def test_tooltip_has_three_branches(self):
        tooltip = self._override("fifth_button_tooltip")
        self.assertIn("GetScriptedGui('te_budget_tax_tab_sgui').IsShown(", tooltip)
        self.assertIn("GetScriptedGui('te_budget_tax_tab_unlock_sgui').IsValid(", tooltip)
        self.assertIn("'te_system_tab_met_tt'", tooltip)
        self.assertIn("GetScriptedGui('te_budget_tax_tab_unlock_sgui').IsValidTooltip(", tooltip)
        self.assertIn("'te_tax_tab_locked_tt'", tooltip)

    def test_the_native_control_gates_stay_outside_the_tab(self):
        # The 20 native-control gates (plan Task 9, test_tax_code_bypass.py) sit on
        # vanilla's buttons, never in the Tax Code tab's MOD blocks: the five tax
        # levels, the consumption-tax "+" (the goods gate) and the 14 tariffs. Each
        # greys its control in `enabled` and says why first in its tooltip, as the
        # locked line and the break after it (GUI audit TAX-11).
        for gate, count, reason in (("te_tax_native_controls_sgui", 5, "level"),
                                    ("te_tax_native_goods_controls_sgui", 1, "goods"),
                                    ("te_tax_native_tariff_controls_sgui", 14, "tariff")):
            with self.subTest(gate=gate):
                self.assertEqual(len(re.findall(rf'enabled = "[^"\n]*{gate}', self.text)), count)
                tooltips = re.findall(rf'tooltip = "[^"\n]*{gate}[^"\n]*"', self.text)
                self.assertEqual(len(tooltips), count)
                for tooltip in tooltips:
                    self.assertEqual(tooltip.count(gate), 2)
                    self.assertIn(f"'te_tax_empty', 'te_tax_tt_native_locked_{reason}' )", tooltip)
                    self.assertIn("'te_tax_empty', 'te_tt_break' )", tooltip)
                self.assertEqual(self.text.count(gate), 3 * count)
        self.assertNotIn("te_tp_native_controls_sgui", self.text)
        for region in self.regions:
            self.assertNotIn("te_tp_", region)
            self.assertNotIn("te_tax_native_", region)


class TabContentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.region = uncomment(mod_block(raw(BUDGET))[1])

    def test_content_follows_banking_inside_scrollarea_content(self):
        text = raw(BUDGET)
        content = text.index('name = "te_budget_tax_tab"')
        self.assertGreater(content, text.index('name = "te_budget_banking_tab"'))
        scroll = text.index('blockoverride "scrollarea_content"')
        self.assertLess(content, close(text, text.index("{", scroll)))

    def test_shown_only_on_its_tab(self):
        head = self.region[self.region.index('name = "te_budget_tax_tab"'):]
        self.assertRegex(head, rf"^name = \"te_budget_tax_tab\"\s*visible = \"\[InformationPanel\.IsTabSelected\('{TAB}'\)\]\"")

    def test_gate_is_a_parent_of_the_journal_entry_datacontext(self):
        gate = self.region.index("GetScriptedGui('te_budget_tax_tab_sgui').IsShown(")
        context = self.region.index("datacontext = \"[GetPlayerJournalEntry('je_tax_code')]\"")
        self.assertLess(gate, context)
        gate_block = brace_block(self.region, self.region.rindex("flowcontainer = {", 0, gate))
        self.assertIn("GetPlayerJournalEntry('je_tax_code')", gate_block)
        # the gate's own properties: everything before its first child container
        own = gate_block[:gate_block.index("flowcontainer = {")]
        self.assertNotIn("datacontext", own, "the datacontext sits on the gate itself")

    def test_composes_overview_status_reference_then_the_link(self):
        order = re.findall(r"\b(te_tax_overview_panel|te_tax_status_sections|te_tax_reference_sections"
                           r"|te_system_tab_open_journal)\b", self.region)
        self.assertEqual(order, ["te_tax_overview_panel", "te_tax_status_sections",
                                 "te_tax_reference_sections", "te_system_tab_open_journal"])
        button = brace_block(self.region, self.region.rindex("button = {", 0,
                                                             self.region.index("te_system_tab_open_journal")))
        self.assertIn('visible = "[JournalEntry.IsActive]"', button)
        self.assertIn("InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)", button)
        self.assertIn('tooltip = "te_tax_open_journal_tt"', button)

    def test_the_column_has_a_fixed_width(self):
        context = brace_block(self.region, self.region.rindex(
            "flowcontainer = {", 0, self.region.index("GetPlayerJournalEntry('je_tax_code')")))
        self.assertIn("minimumsize = { 520 -1 }", context)

    def test_the_summary_moves_to_the_footer(self):
        """The tab draws the draft summary in fixed_bottom, so the live sections
        it composes leave their own copy out."""
        status = brace_block(self.region, self.region.index("te_tax_status_sections = {"))
        self.assertRegex(status, r'^\{\s*blockoverride "draft_summary" \{\s*\}\s*\}$')


class FooterTest(unittest.TestCase):
    """Budget's fixed_bottom: the draft summary, only on the Tax Code tab, only
    while the tab is open and a draft is."""

    @classmethod
    def setUpClass(cls):
        cls.region = uncomment(mod_block(raw(BUDGET))[2])

    def test_is_the_fixed_bottom_block_after_the_content(self):
        text = raw(BUDGET)
        footer = text.index('blockoverride "fixed_bottom"')
        scroll = text.index('blockoverride "scrollarea_content"')
        self.assertGreater(footer, close(text, text.index("{", scroll)))
        self.assertLess(text.rindex("### MOD: Tax Code tab", 0, footer), footer)
        self.assertEqual(text.count('blockoverride "fixed_bottom"'), 1)

    def test_gate_and_contents(self):
        """The draft's summary while a draft is open, else the bill's (GUI audit
        TAX-2); each summary gates itself."""
        self.assertIn("InformationPanel.IsTabSelected('te_tax_code')", self.region)
        self.assertIn("GetScriptedGui('te_budget_tax_tab_sgui').IsShown(", self.region)
        self.assertIn("Or( GetScriptedGui('te_tax_show_draft_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End ), "
                      "GetScriptedGui('te_tax_show_bill_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End ) )",
                      self.region)
        self.assertEqual(re.findall(r"\b(te_tax_\w+) = \{", self.region), ["te_tax_draft_summary", "te_tax_bill_summary"])
        self.assertNotIn("JournalEntry", self.region)

    def test_the_bill_summary_needs_no_journal_entry_and_yields_to_the_draft(self):
        body = type_body(gui(POLITICS), "te_tax_bill_summary")
        self.assertNotIn("JournalEntry", body)
        self.assertIn("visible = \"[And( GetScriptedGui('te_tax_show_bill_sgui').IsShown( GuiScope.SetRoot( "
                      "GetPlayer.MakeScope ).End ), Not( GetScriptedGui('te_tax_show_draft_sgui').IsShown( GuiScope.SetRoot( "
                      "GetPlayer.MakeScope ).End ) ) )]\"", body)
        for name in ("te_tax_cmd_pass_sgui", "te_tax_cmd_force_through_sgui", "te_tax_cmd_withdraw_sgui"):
            self.assertIn(f"GetScriptedGui('{name}').Execute(", body)
        force = brace_block(body, body.rindex("button = {", 0, body.index("te_tax_cmd_force_through_sgui")))
        self.assertIn("visible = \"[Not( GetScriptedGui('te_tax_show_pass_support_sgui').IsShown(", force)

    def test_the_summary_type_needs_no_journal_entry(self):
        body = type_body(gui(WORKBENCH), "te_tax_draft_summary")
        self.assertNotIn("JournalEntry", body)
        for name in ("te_tax_cmd_draft_discard_sgui", "te_tax_cmd_introduce_sgui", "te_tax_cmd_revise_sgui"):
            self.assertIn(f"GetScriptedGui('{name}')", body)
        self.assertIn("GetVariableSystem.Toggle('te_tax_review_open')", body)


class LayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = gui(LAYOUT)
        cls.overview = gui(OVERVIEW)
        cls.all = "\n".join(gui(path) for path in NEW_GUI)

    def test_status_sections(self):
        # The legislated code's sections in a wrapper hidden under the light
        # setting, then the light code's own section, which gates itself.
        body = type_body(self.layout, "te_tax_status_sections")
        self.assertEqual(re.findall(r"^\t\t\t(te_tax_\w+) = \{", body, re.M), STATUS)
        self.assertEqual(re.findall(r"^\t\t(te_tax_\w+) = \{", body, re.M), ["te_tax_light_section"])
        self.assertIn(f'visible = "[Not( {LIGHT_SHOWN} )]"', body)

    def test_status_sections_carry_the_summary_after_the_workbench(self):
        body = type_body(self.layout, "te_tax_status_sections")
        summary = body.index('block "draft_summary"')
        self.assertLess(body.index("te_tax_workbench_section = {}"), summary)
        self.assertLess(summary, body.index("te_tax_review_section = {}"))
        self.assertRegex(body, r'block "draft_summary" \{\s*te_tax_draft_summary = \{\}\s*\}')

    def test_reference_sections_history_then_how(self):
        body = type_body(self.layout, "te_tax_reference_sections")
        self.assertEqual(re.findall(r"^\t\t\t(te_tax_\w+) = \{", body, re.M), REFERENCE)
        self.assertEqual(re.findall(r"^\t\t(te_tax_\w+) = \{", body, re.M), ["te_tax_light_how_section"])
        self.assertIn(f'visible = "[Not( {LIGHT_SHOWN} )]"', body)

    def test_the_brief_types_exist(self):
        for name in ("te_tax_overview_panel", "te_tax_enacted_table", "te_tax_how_section",
                     "te_tax_history_section", "te_tax_status_sections", "te_tax_reference_sections",
                     "te_tax_workbench_section", "te_tax_instrument_row", "te_tax_sunset_row",
                     "te_tax_good_row", "te_tax_draft_summary", "te_tax_review_section",
                     "te_tax_politics_section", "te_tax_ig_card", "te_tax_pending_section",
                     "te_tax_wb_goods_rows", "te_tax_rv_goods_rows", "te_tax_obligations_section",
                     "te_tax_obligation_row"):
            with self.subTest(name=name):
                type_body(self.all, name)

    def test_composers_and_overview_are_gated_on_an_active_entry(self):
        for name in ("te_tax_status_sections", "te_tax_reference_sections"):
            self.assertIn('visible = "[JournalEntry.IsActive]"', type_body(self.layout, name), name)
        self.assertIn('visible = "[JournalEntry.IsActive]"', type_body(self.overview, "te_tax_overview_panel"))

    def test_roots_are_gated_and_fixed_width(self):
        roots = re.findall(r'^flowcontainer = \{\s*name = "(widget_je_tax_code_\w+)"\s*'
                           r'visible = "\[JournalEntry\.IsActive\]"', self.layout, re.M)
        self.assertEqual(roots, [name for name, _ in ROOTS])
        for name, _ in ROOTS:
            root = brace_block(self.layout, self.layout.index(f'name = "{name}"') - len("flowcontainer = "))
            with self.subTest(root=name):
                self.assertIn("minimumsize = { 520 -1 }", root)

    def test_root_contents(self):
        def root(name):
            return brace_block(self.layout, self.layout.index(f'name = "{name}"') - len("flowcontainer = "))
        self.assertIn("te_tax_overview_panel = {}", root("widget_je_tax_code_overview"))
        self.assertIn("te_tax_status_sections = {}", root("widget_je_tax_code_status"))
        self.assertIn("te_tax_reference_sections = {}", root("widget_je_tax_code_reference"))

    def test_the_entry_opens_the_budget_tab(self):
        overview_root = brace_block(self.layout, self.layout.index('name = "widget_je_tax_code_overview"')
                                    - len("flowcontainer = "))
        self.assertIn(f"onclick = \"[InformationPanelBar.OpenPanelTab('budget', '{TAB}')]\"", overview_root)
        self.assertIn('text = "te_tax_open_budget"', overview_root)
        self.assertIn('tooltip = "te_tax_open_budget_tt"', overview_root)
        # the Budget tab never shows a button that opens itself
        self.assertNotIn("OpenPanelTab", type_body(self.overview, "te_tax_overview_panel"))
        self.assertEqual(self.all.count("OpenPanelTab"), 1)

    def test_draft_and_bill_sections_are_gated_on_their_record(self):
        """Opening the panel shows a record's rows only while it is open."""
        workbench = gui(WORKBENCH)
        self.assertIn("GetScriptedGui('te_tax_show_draft_sgui').IsShown(", type_body(workbench, "te_tax_draft_summary"))
        self.assertIn("GetScriptedGui('te_tax_show_draft_sgui').IsShown(", type_body(gui(REVIEW), "te_tax_review_section"))
        self.assertIn("GetScriptedGui('te_tax_show_bill_sgui').IsShown(", type_body(gui(POLITICS), "te_tax_politics_section"))

    def test_one_root_for_every_type_reader(self):
        """Every number the shared types read comes from the player's country
        (GetPlayer), never JournalEntry.GetCountry: the Budget tab and a
        datamodel item's tooltip have no JournalEntry to start from."""
        self.assertNotIn("JournalEntry.GetCountry", self.all)
        self.assertNotIn("GetCountry", re.sub(r"GetPlayerJournalEntry", "", self.all))


class JournalEntryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = script(JE)
        cls.body = block(cls.text, "je_tax_code")

    def test_mounts_the_three_roots(self):
        widgets = re.findall(r'widget = \{\s*gui = "([^"]+)"\s*name = "(\w+)"\s*container = "(\w+)"\s*\}', self.body)
        self.assertEqual(widgets, [(LAYOUT, name, container) for name, container in ROOTS])

    def test_shown_only_under_the_rule_and_active_once_migrated(self):
        # Under either code, full or light (te_tax_code_on).
        shown = brace_block(self.body, self.body.index("is_shown_when_inactive"))
        self.assertIn("te_tax_code_on = yes", shown)
        self.assertNotIn("NOT", shown)
        possible = brace_block(self.body, self.body.index("possible"))
        self.assertIn("te_tax_entry_unlocked = yes", possible)
        unlocked = block(script(TRIGGERS), "te_tax_entry_unlocked")
        self.assertRegex(unlocked, r"^\s*custom_tooltip = \{\s*text = te_tax_tt_code_in_force\s*"
                                   r"OR = \{\s*te_tax_code_in_force = yes\s*te_tax_light_in_force = yes\s*\}\s*\}\s*$")
        in_force = block(script(TRIGGERS), "te_tax_code_in_force")
        self.assertIn("te_tax_code_full = yes", in_force)
        self.assertIn("var:te_tax_migrated >= 1", in_force)

    def test_never_completes_fails_or_times_out(self):
        for field in ("complete", "on_complete", "fail", "on_fail", "invalid", "timeout", "can_deactivate"):
            with self.subTest(field=field):
                self.assertNotRegex(self.body, rf"(?m)^\t{field} =")

    def test_activation_writes_nothing(self):
        """A revolution's winner re-runs `immediate` on the inherited entry
        (CLAUDE.md "Top gotchas"); the entry is display only, so it has none,
        and none of its blocks writes a variable."""
        self.assertNotRegex(self.body, r"(?m)^\timmediate =")
        self.assertIsNone(re.search(r"\b(set_variable|change_variable|remove_variable)\b", self.body))

    def test_status_text_is_empty_while_active(self):
        status = brace_block(self.body, self.body.index("status_desc"))
        descs = re.findall(r"desc = (\w+)", status)
        self.assertEqual(descs, ["je_tax_code_status_inactive", "je_tax_code_status_none"])
        table = loc()
        self.assertEqual(table["je_tax_code_status_none"], "")
        self.assertTrue(table["je_tax_code_status_inactive"])

    def test_names_and_icon(self):
        table = loc()
        for key in ("je_tax_code", "je_tax_code_desc", "je_tax_code_reason"):
            with self.subTest(key=key):
                self.assertTrue(table.get(key))
        self.assertIn('icon = "gfx/interface/icons/event_icons/je_tax_code.dds"', self.body)


class SguiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tab = script(TAB_SGUIS)
        cls.tax = script(TAX_SGUIS)

    def test_tab_gate_pair(self):
        tab = block(self.tab, "te_budget_tax_tab_sgui")
        shown = brace_block(tab, tab.index("is_shown"))
        self.assertIn("te_tax_code_on = yes", shown)
        self.assertIn("has_journal_entry = je_tax_code", shown)
        self.assertRegex(tab, r"is_valid = \{ always = no \}")
        self.assertRegex(tab, r"effect = \{ \}")
        unlock = block(self.tab, "te_budget_tax_tab_unlock_sgui")
        self.assertRegex(unlock, r"is_shown = \{ te_tax_code_on = yes \}")
        self.assertRegex(unlock, r"is_valid = \{ te_tax_entry_unlocked = yes \}")
        self.assertRegex(unlock, r"effect = \{ \}")

    def test_display_gates_are_scope_free_and_inert(self):
        """The te_tax_show_* gates (the action handlers beside them are checked
        in test_tax_code_sguis.py)."""
        names = [name for name in top_level_names(self.tax) if name.startswith("te_tax_show_")]
        self.assertGreaterEqual(len(names), 14)
        for name in names:
            body = block(self.tax, name)
            with self.subTest(name=name):
                self.assertTrue(name.startswith("te_tax_") and name.endswith("_sgui"))
                self.assertIn("scope = country", body)
                self.assertNotIn("saved_scopes", body)
                self.assertNotIn("scope:", body)
                self.assertRegex(body, r"ai_is_valid = \{ always = no \}")
                self.assertRegex(body, r"(?m)^\tis_valid = \{ always = no \}")
                self.assertRegex(body, r"effect = \{ \}")
                shown = brace_block(body, body.index("is_shown"))
                self.assertIn("te_tax_code_in_force = yes", shown)
                self.assertIsNone(FORBIDDEN_IN_VALUES.search(body))

    def test_every_scripted_gui_named_by_the_panels_exists(self):
        defined = set(top_level_names(self.tab)) | set(top_level_names(self.tax)) | set(
            top_level_names(script(GEN_SGUIS))) | set(top_level_names(script(LIGHT_SGUIS))) | set(
            top_level_names(script(LIGHT_GEN_SGUIS)))
        text = "\n".join(gui(path) for path in NEW_GUI) + "\n".join(uncomment(r) for r in mod_block(raw(BUDGET)))
        for name in set(re.findall(r"GetScriptedGui\('(\w+)'\)", text)):
            with self.subTest(name=name):
                self.assertIn(name, defined)


class NameWidthTest(unittest.TestCase):
    """Final review B-I2: no catalog good name and no customs level name elides in its cell
    at 7 px a character, and every good-name cell carries the name as a hover in case a font
    draws it wider. Measured against the names the game prints: the mod's loc, then the
    committed vanilla 1.14.5 snapshot."""

    PX = 7

    @classmethod
    def setUpClass(cls):
        vanilla = json.loads((ROOT / "vanilla_parsed" / "localization_english.json").read_text(encoding="utf-8"))
        mod = loc()

        def name(key):
            text = mod.get(key, vanilla.get(key))
            for _ in range(3):
                text = re.sub(r"\$(\w+)\$", lambda m: str(mod.get(m.group(1), vanilla.get(m.group(1), ""))), text)
            return text

        cls.name = staticmethod(name)
        cls.workbench = gui(WORKBENCH)
        cls.review = gui(REVIEW)

    def width(self, body, pattern):
        match = re.search(pattern, body)
        self.assertIsNotNone(match, pattern)
        return int(match.group(1))

    def assert_fits(self, goods, cell):
        for good in goods:
            with self.subTest(good=good, cell=cell):
                self.assertLessEqual(len(self.name(good)) * self.PX, cell, self.name(good))

    def test_goods_names_fit_their_cells(self):
        goods_row = type_body(self.workbench, "te_tax_good_row")
        self.assert_fits(gen.consumption_catalog(), self.width(goods_row, r"max_width = (\d+)"))
        customs_row = type_body(self.workbench, "te_tax_customs_row")
        self.assert_fits(gen.customs_catalog(), self.width(customs_row, r"max_width = (\d+)"))
        label = type_body(self.review, "te_tax_review_line")
        cell = self.width(label, r"maximumsize = \{ (\d+) -1 \}")
        self.assert_fits(gen.consumption_catalog(), cell)
        self.assert_fits(gen.customs_catalog(), cell)
        customs_line = type_body(self.review, "te_tax_review_customs_line")
        self.assert_fits(gen.customs_catalog(), self.width(customs_line, r"max_width = (\d+)"))

    def test_levels_are_vanilla_tariff_icons_with_their_word_on_hover(self):
        """GUI audit TAX-26: each level is vanilla's own tariff icon (the Market
        panel's and set_level_bar's), one per level, with its word on hover; each
        direction's level cell holds the icon, in the row and in the review."""
        icon = type_body(self.workbench, "te_tax_cu_level_icon")
        size = int(re.search(r"size = \{ (\d+) \1 \}", icon).group(1))
        rows = gui(GEN_ROWS)
        budget = gui(BUDGET)
        for idx, suffix in gen.CUSTOMS_LEVEL_SUFFIX.items():
            texture = f"gfx/interface/icons/trade_icons/{gen.CUSTOMS_LEVEL_TEXTURES[idx]}.dds"
            with self.subTest(level=idx):
                self.assertIn(texture, budget)
                self.assertTrue(self.name(f"te_tax_cu_lv_{suffix}"))
                self.assertIn(f'texture = "{texture}" tooltip = "te_tax_cu_lv_{suffix}"', rows)
        self.assertNotIn("te_tax_cu_level_text", rows)
        cell = size + 4
        self.assertEqual(type_body(self.workbench, "te_tax_customs_row").count(f"size = {{ {cell} 26 }}"), 2)
        self.assertEqual(type_body(self.review, "te_tax_review_customs_line").count(f"size = {{ {cell} 26 }}"), 2)

    def test_every_good_name_cell_has_the_name_as_its_hover(self):
        rows = gui(GEN_ROWS)
        names = re.findall(r'blockoverride "(?:good_name|line_label)" \{\s*text = "(\w+)"\s*tooltip = "(\w+)"', rows)
        expected = 2 * len(gen.consumption_catalog()) + 5 * len(gen.customs_catalog())
        self.assertEqual(len(names), expected)
        self.assertTrue(all(text == tooltip for text, tooltip in names))

    def test_a_label_without_a_hover_is_not_drawn_hoverable(self):
        self.assertNotIn("#tooltippable", type_body(self.review, "te_tax_review_line"))
        for path in (REVIEW, POLITICS):
            for body in re.findall(r'blockoverride "line_label" \{([^}]*)\}', gui(path)):
                with self.subTest(path=path, body=" ".join(body.split())):
                    self.assertEqual("tooltip =" in body, '#tooltippable' in body)

    def test_rows_fit_the_section(self):
        # 4 + 156 + 4 + 154 + 4 + 154 + 4 = 480, the heads in the same cells.
        for name in ("te_tax_customs_row", "te_tax_customs_head"):
            body = type_body(self.workbench, name)
            with self.subTest(name=name):
                cells = [int(w) for w in re.findall(r"(?m)^\t\twidget = \{\s*size = \{ (\d+) ", body)]
                self.assertEqual(sum(cells) + 4 * (len(cells) + 1), 480, cells)


# ---------------------------------------------------------------------------
# Type sizes and width budgets (GUI audit TAX-15; style guide rule 3)
# ---------------------------------------------------------------------------

# The panel's own sizes (the te_tax_fontsize_* templates at the head of the
# overview file), in GUI units a character: the serif at 0.5 a point (8.5 at
# 17, 10 at 20) and the overview's 16-point tooltip face at 8.6, plus 10%: the
# budget test_banking_layout.WidthBudgetTest and test_seabed_layout use.
_FONT_SIZES = {m.group(1): int(m.group(2)) for m in re.finditer(
    r"template te_tax_fontsize_(\w+) \{\s*fontsize = (\d+)", raw(OVERVIEW))}
UNITS = {"row": 10.0 / 20 * _FONT_SIZES.get("row", 17), "heading": 10.0 / 20 * _FONT_SIZES.get("heading", 20),
         "overview": 8.6 / 16 * _FONT_SIZES.get("overview", 16)}
MARGIN = 1.1
# What a number prints at its widest, by its format and the value it reads.
_FORMATS = {"%0": "100%", "%1": "12.5%", "+%0": "+50%", "+%1": "+12.5%", "2": "1.50", "3": "1.200",
            "+2": "+0.50", "+3": "+0.150", "+0": "+50", "=+0": "+100", "K": "99.9K", "+K": "+99.9K",
            "+=K": "+99.9K", "Kv": "99.9K", "D": "99.9"}


# Values with a known ceiling: the passage threshold is the rule's (te_tax_passage_share,
# 50%); there are eight scored groups, four promise slots, eight parts a draft can need
# to accept and a version or a count of two digits.
_BY_NAME = {"te_tax_view_passage_share": "50%", "te_tax_view_offers_open": "8", "te_tax_view_obl_failing": "4",
            "te_tax_view_obl_binding": "4", "te_tax_view_obl_pending": "4", "te_tax_view_dr_rebase_count": "8"}


def _number(name, fmt):
    if name in _BY_NAME:
        return _BY_NAME[name]
    if name.endswith("_y"):
        return "1840"
    if name.endswith("_mo"):
        return "12"
    if fmt in _FORMATS:
        return _FORMATS[fmt]
    return "99"


class WidthBudgetTest(unittest.TestCase):
    """Every fixed-width cell of the Tax Code panels fits the longest text it
    can show at its font: no label, value, button or overview word ends in
    "..." (style guide rule 3). Widths and fonts are read from the markup, so a
    narrower cell or a bigger template fails here."""

    @classmethod
    def setUpClass(cls):
        vanilla = json.loads((ROOT / "vanilla_parsed" / "localization_english.json").read_text(encoding="utf-8"))
        cls.loc = dict(vanilla)
        cls.loc.update(loc())
        custom = {}
        for path in sorted((ROOT / "common" / "customizable_localization").glob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            for match in re.finditer(r"(?m)^(\w+) = \{", text):
                body = brace_block(text, match.end() - 1)
                custom[match.group(1)] = re.findall(r"localization_key = (\w+)", body)
        cls.custom = custom
        cls.files = {path: gui(path) for path in NEW_GUI}

    def shown(self, key, depth=0):
        """The widest text `key` can show: splices, concepts and customizable
        localizations at their longest, each number at its widest, formatting
        and icons stripped."""
        value = self.loc.get(key)
        self.assertIsNotNone(value, key)
        self.assertLess(depth, 8, key)
        return self._text(value, depth)

    def _text(self, v, depth):
        v = re.sub(r"\$(\w+)\$", lambda m: self.shown(m.group(1), depth + 1), v)
        v = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", lambda m: self._text(m.group(1), depth + 1), v)
        v = re.sub(r"\[(concept_\w+)\]", lambda m: self.shown(m.group(1), depth + 1), v)

        def custom(m):
            return max((self.shown(k, depth + 1) for k in self.custom[m.group(1)]), key=len)
        v = re.sub(r"\[[^\[\]]*GetCustom\('(\w+)'\)[^\[\]]*\]", custom, v)

        def select(m):
            return max((self.shown(k, depth + 1) for k in re.findall(r"'(\w+)'", m.group(0))
                        if k in self.loc and not k.startswith("te_tax_view")), key=len, default="")
        v = re.sub(r"\[SelectLocalization\((?:[^\[\]])*\]", select, v)
        v = re.sub(r"\[InterestGroup\.GetName\]", "Petite Bourgeoisie", v)

        def number(m):
            name = re.findall(r"ScriptValue\('(\w+)'\)", m.group(0))
            fmt = m.group(1) if m.group(1) is not None else ""
            return _number(name[-1] if name else "", fmt)
        v = re.sub(r"\[(?:[^\[\]|]|\[[^\[\]]*\])*(?:\|([^\]]*))?\]", number, v)
        v = re.sub(r"#[A-Za-z_]+(?:;\S*)? ", "", v).replace("#!", "")
        v = re.sub(r"@\w+!", "", v)
        return v.replace("\\n", "")

    def fits(self, key, cell):
        width, font = cell
        text = self.shown(key)
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, width, f"{key} shows {text!r}: {need:.0f} units in a {width} {font} cell")

    def keys_in(self, expression):
        """The loc keys a text expression can print: the key itself, or a
        SelectLocalization's quoted options."""
        if not expression.startswith("["):
            return [expression]
        return [k for k in re.findall(r"'(\w+)'", expression) if k in self.loc]

    def cell(self, body, anchor):
        """(width, font) of the textbox holding `anchor` in `body`."""
        at = body.index(anchor)
        start = body.rindex("textbox = {", 0, at)
        box = brace_block(body, start)
        width = (re.search(r"max_width = (\d+)", box) or re.search(r"maximumsize = \{ (\d+)", box)
                 or re.search(r"size = \{ (\d+)", box))
        font = re.search(r"using = te_tax_fontsize_(\w+)", box)
        self.assertIsNotNone(width, anchor)
        self.assertIsNotNone(font, anchor)
        return int(width.group(1)), font.group(1)

    def type_cell(self, path, typ, block):
        return self.cell(type_body(self.files[path], typ), f'block "{block}"')

    def instances(self, typ):
        """Every `typ = { ... }` instance body across the panels (not the type)."""
        out = []
        for path, text in self.files.items():
            for match in re.finditer(rf"(?<![\w.]){typ} = \{{", text):
                if text[max(0, match.start() - 5):match.start()].endswith("type "):
                    continue
                out.append(brace_block(text, match.end() - 1))
        return out

    def overrides(self, body, block):
        """The text expressions of `blockoverride "<block>" { text = "..." }` in `body`."""
        return re.findall(rf'blockoverride "{block}" \{{[^{{}}]*?\btext = "([^"]+)"', body)

    def check_rows(self, typ, blocks):
        rows = self.instances(typ)
        self.assertTrue(rows, typ)
        for name, cell in blocks.items():
            for body in rows:
                for expression in self.overrides(body, name):
                    for key in self.keys_in(expression):
                        with self.subTest(row=typ, block=name, key=key):
                            self.fits(key, cell)

    def test_type_sizes_are_the_templates(self):
        self.assertEqual(_FONT_SIZES, {"row": 17, "heading": 20, "overview": 16})
        for path, text in self.files.items():
            with self.subTest(path=path):
                self.assertNotRegex(text, r"using = fontsize_")
        # Every button with a label sets the row font, as Banking's do.
        for path, text in self.files.items():
            for match in re.finditer(r"(?<![\w.])button = \{", text):
                body = brace_block(text, match.end() - 1)
                with self.subTest(path=path, button=body[:60]):
                    self.assertIn("using = te_tax_fontsize_row", body)

    def test_overview_cells(self):
        """Banking's cell, its 154 column at the overview's 16 (rule 4)."""
        cells = self.instances("te_banking_ov_cell")
        self.assertGreaterEqual(len(cells), 11)
        for name in ("te_tax_ov_word", "te_tax_ov_fig"):
            body = type_body(self.files[OVERVIEW], name)
            self.assertIn("using = te_tax_fontsize_overview", body)
            self.assertIn("max_width = 154", body)
        for body in cells:
            self.assertIn("size = { 238 70 }", body)
            self.assertRegex(body, r'blockoverride "caption_width" \{\s*max_width = 154')
            texts = self.overrides(body, "caption") + re.findall(r'te_tax_ov_(?:word|fig) = \{\s*text = "([^"]+)"', body)
            self.assertGreaterEqual(len(texts), 2, body[:80])
            for expression in texts:
                for key in self.keys_in(expression):
                    with self.subTest(key=key):
                        self.fits(key, (154, "overview"))

    def test_table_rows(self):
        self.check_rows("te_tax_value_row", {
            "row_label": self.type_cell(OVERVIEW, "te_tax_value_row", "row_label"),
            "row_value": self.type_cell(OVERVIEW, "te_tax_value_row", "row_value")})
        self.check_rows("te_tax_rate_row", {
            "row_label": self.type_cell(OVERVIEW, "te_tax_rate_row", "row_label"),
            "row_rate": self.type_cell(OVERVIEW, "te_tax_rate_row", "row_rate"),
            "row_sunset": self.type_cell(OVERVIEW, "te_tax_rate_row", "row_sunset")})
        self.check_rows("te_tax_condition_row", {
            "row_label": self.type_cell(POLITICS, "te_tax_condition_row", "row_label"),
            "row_value": self.type_cell(POLITICS, "te_tax_condition_row", "row_value"),
            "row_mark": self.type_cell(POLITICS, "te_tax_condition_row", "row_mark")})
        self.check_rows("te_tax_ig_reason_row", {
            "row_label": self.type_cell(POLITICS, "te_tax_ig_reason_row", "row_label"),
            "row_value": self.type_cell(POLITICS, "te_tax_ig_reason_row", "row_value")})
        self.check_rows("te_tax_sunset_row", {
            "row_label": self.type_cell(WORKBENCH, "te_tax_sunset_row", "row_label"),
            "row_value": self.type_cell(WORKBENCH, "te_tax_sunset_row", "row_value")})
        self.check_rows("te_tax_estimate_row", {
            block: self.type_cell(REVIEW, "te_tax_estimate_row", block)
            for block in ("est_label", "est_law", "est_bill", "est_delta")})
        # The committed share beside its bar, in the first condition row.
        politics = self.files[POLITICS]
        self.fits("te_tax_pol_bar_value", self.cell(politics, '"te_tax_pol_bar_value"'))

    def test_instrument_rows(self):
        """The workbench's taxes and reliefs and the light code's rows share one row type."""
        cells = {block: self.type_cell(WORKBENCH, "te_tax_instrument_row", block)
                 for block in ("row_label", "row_law", "row_draft", "row_delta")}
        self.check_rows("te_tax_instrument_row", cells)
        for typ, path, keys in (("te_tax_instrument_head", WORKBENCH, ("te_tax_wb_col_law", "te_tax_wb_col_draft",
                                                                       "te_tax_wb_col_change")),
                                ("te_tax_light_head", LIGHT_GUI, ("te_tax_lt_col_range", "te_tax_lt_col_rate",
                                                                   "te_tax_lt_col_step"))):
            body = type_body(self.files[path], typ)
            for key in keys:
                with self.subTest(head=key):
                    self.fits(key, self.cell(body, f'"{key}"'))
        # the heads sit over the rows' cells
        row = type_body(self.files[WORKBENCH], "te_tax_instrument_row")
        widths = [int(w) for w in re.findall(r"(?m)^\t\twidget = \{\s*size = \{ (\d+) ", row)]
        for typ, path in (("te_tax_instrument_head", WORKBENCH), ("te_tax_light_head", LIGHT_GUI)):
            head = [int(w) for w in re.findall(r"(?m)^\t\twidget = \{\s*size = \{ (\d+) ", type_body(self.files[path], typ))]
            with self.subTest(head=typ):
                self.assertEqual(head[:4] + head[5:], widths[:4] + widths[4:])
                self.assertEqual(head[4], 22 + 4 + 22)

    def test_goods_and_customs_names(self):
        """Every catalog good's name in its cell; a name a font draws wider has
        itself on hover (NameWidthTest)."""
        for typ, path, name, goods in (("te_tax_good_row", WORKBENCH, "good_name", gen.consumption_catalog()),
                                        ("te_tax_customs_row", WORKBENCH, "good_name", gen.customs_catalog()),
                                        ("te_tax_review_customs_line", REVIEW, "good_name", gen.customs_catalog()),
                                        ("te_tax_review_line", REVIEW, "line_label", gen.consumption_catalog())):
            cell = self.type_cell(path, typ, name)
            for good in goods:
                with self.subTest(row=typ, good=good):
                    self.fits(good, cell)
        good_row = type_body(self.files[WORKBENCH], "te_tax_good_row")
        for key in ("te_tax_wb_good_taxed", "te_tax_wb_good_untaxed", "te_tax_wb_good_taxed_changed"):
            self.fits(key, self.cell(good_row, 'block "good_law"'))
            self.fits(key, self.cell(good_row, 'block "good_draft"'))
        for key in ("te_tax_wb_cu_cat_staple", "te_tax_wb_cu_cat_industrial", "te_tax_wb_cu_cat_luxury",
                    "te_tax_wb_cu_cat_military"):
            self.assertIn(f'te_tax_wb_goods_heading = {{ text = "{key}" }}', gui(GEN_ROWS))

    def test_interest_group_card(self):
        card = type_body(self.files[POLITICS], "te_tax_ig_card")
        for ig in gen.IGS:
            with self.subTest(ig=ig):
                self.fits(f"ig_{ig}", self.cell(card, '"te_tax_ig_name"'))
        self.assertIn('tooltip = "te_tax_ig_name"', card)
        self.fits("te_tax_ig_clout", self.cell(card, '"te_tax_ig_clout"'))
        self.fits("te_tax_ig_score", self.cell(card, '"te_tax_ig_score"'))
        for n in range(1, 6):
            self.fits(f"te_tax_ig_stance_{n}", self.cell(card, "'te_tax_ig_stance_1'"))
        # A promise's group, in its row (the rest wraps).
        row = type_body(self.files[POLITICS], "te_tax_obligation_row")
        for ig in gen.IGS:
            with self.subTest(promise_ig=ig):
                self.fits(f"ig_{ig}", self.cell(row, 'block "obl_ig"'))
        for name in ("obl_what", "obl_state"):
            box = brace_block(row, row.rindex("textbox = {", 0, row.index(f'block "{name}"')))
            self.assertIn("multiline = yes", box)
            self.assertNotIn("elide", box)

    def test_relief_states_history_and_labels(self):
        row = type_body(self.files[WORKBENCH], "te_tax_relief_state_row")
        for key in ("te_tax_wb_relief_state_named", "te_tax_wb_relief_state_dropped"):
            self.fits(key, self.cell(row, 'block "state_status"'))
        self.assertIn('tooltip = "te_tax_wb_relief_state_name"', row)
        history = type_body(self.files[OVERVIEW], "te_tax_history_row")
        for i in range(1, HISTORY_SIZE + 1):
            self.fits(f"te_tax_hist_version_{i}", self.cell(history, 'block "row_version"'))
            self.fits(f"te_tax_hist_date_{i}", self.cell(history, 'block "row_date"'))
        label = type_body(self.files[OVERVIEW], "te_tax_goods_icons_label")
        width = int(re.search(r"maximumsize = \{ (\d+)", label).group(1))
        for key in ("te_tax_pk_goods_taxed", "te_tax_pk_goods_exempt"):
            self.fits(key, (width, "row"))

    def test_buttons(self):
        """A button's label fits its width, less a little padding."""
        for path, text in self.files.items():
            for match in re.finditer(r"(?<![\w.])button = \{", text):
                body = brace_block(text, match.end() - 1)
                size = re.search(r"size = \{ (\d+) \d+ \}", body)
                label = re.search(r'\btext = "([^"]+)"', body)
                if not size or not label:
                    continue
                for key in self.keys_in(label.group(1)):
                    with self.subTest(path=path, button=key):
                        self.fits(key, (int(size.group(1)) - 8, "row"))


class FlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = "\n".join(gui(path) for path in NEW_GUI)

    def test_section_flags_say_their_default(self):
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.text))
        self.assertEqual(flags, FLAGS)
        for flag in flags:
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{flag}'\)\s*\)", self.text))
            bare = len(re.findall(rf"GetVariableSystem\.Exists\('{flag}'\)", self.text)) - negated
            with self.subTest(flag=flag):
                if flag.endswith("_closed"):     # shown unless closed
                    self.assertEqual(bare, 1)
                    self.assertGreaterEqual(negated, 2)
                else:                            # shown only when opened
                    self.assertEqual(negated, 1)
                    self.assertGreaterEqual(bare, 2)

    def test_live_open_past_and_explanations_collapsed(self):
        overview = gui(OVERVIEW)
        layout = gui(LAYOUT)
        self.assertIn("Toggle('te_tax_enacted_closed')", type_body(overview, "te_tax_enacted_table"))
        self.assertIn("Toggle('te_tax_history_open')", type_body(overview, "te_tax_history_section"))
        self.assertIn("Toggle('te_tax_how_open')", type_body(layout, "te_tax_how_section"))

    def test_how_section_subheadings(self):
        body = type_body(gui(LAYOUT), "te_tax_how_section")
        subs = re.findall(r'text = "(te_tax_how_sub_\w+)"', body)
        self.assertEqual(subs, ["te_tax_how_sub_drafting", "te_tax_how_sub_passage",
                                "te_tax_how_sub_commencement", "te_tax_how_sub_promises", "te_tax_how_sub_replaces",
                                "te_tax_how_sub_customs"])
        table = loc()
        self.assertEqual([table[key] for key in subs],
                         ["Drafting", "Passage", "Commencement", "Promises", "What the Code Replaces", "Customs"])
        notes = re.findall(r'text = "(te_tax_how_(?!sub_|header)\w+)"', body)
        self.assertGreaterEqual(len(notes), 4)
        for key in notes:
            with self.subTest(key=key):
                self.assertFalse(table[key].startswith("\\n") or table[key].endswith("\\n"))


    def test_customs_is_explained_only_under_the_customs_option(self):
        # Final review B-I1: under the customs option the monthly sync sets tariffs too, so
        # the line that says it does not is swapped, and a Customs topic shows.
        body = type_body(gui(LAYOUT), "te_tax_how_section")
        gate = "GetScriptedGui('te_tax_show_customs_option_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"
        self.assertIn(f"text = \"[SelectLocalization( {gate}, 'te_tax_how_replaces_monthly_customs', "
                      "'te_tax_how_replaces_monthly' )]\"", body)
        customs = body[body.index('text = "te_tax_how_sub_customs"') - 300:]
        self.assertEqual(customs.count(f'visible = "[{gate}]"'), 3)
        for key in ("te_tax_how_customs", "te_tax_how_customs_sync"):
            self.assertIn(f'text = "{key}"', customs)
        sgui = block(script(TAX_SGUIS), "te_tax_show_customs_option_sgui")
        self.assertIn("te_tax_customs_on = yes", brace_block(sgui, sgui.index("is_shown")))
        table = loc()
        self.assertIn("Tariffs and subsidies are not part of these rates", table["te_tax_how_replaces_monthly"])
        self.assertIn("tariffs and subsidies", table["te_tax_how_replaces_monthly_customs"])
        self.assertNotIn("not part", table["te_tax_how_replaces_monthly_customs"])
        self.assertIn("te_tax_customs_adopt_after", table["te_tax_how_customs_sync"])
        self.assertIn("tariffs and subsidies", table["concept_tax_code_desc"])


class DisplayValueTest(unittest.TestCase):
    """Every number on the panels goes through a guarded display value."""

    @classmethod
    def setUpClass(cls):
        cls.values = value_bodies()
        cls.gui_text = "\n".join(gui(path) for path in NEW_GUI) + "\n".join(
            uncomment(region) for region in mod_block(raw(BUDGET)))
        table = loc()
        cls.loc = table
        cls.printed = reachable_loc(loc_keys_named_in(cls.gui_text), table)

    def assert_guarded(self, name, seen=None):
        seen = seen if seen is not None else set()
        if name in seen:
            return
        seen.add(name)
        self.assertIn(name, self.values, f"{name} is not a tax code script value")
        body = self.values[name]
        if body is None:
            return  # a constant
        self.assertIsNone(FORBIDDEN_IN_VALUES.search(body), name)
        for var in set(re.findall(r"var:(\w+)", body)):
            self.assertIn(f"has_variable = {var}", body, f"{name} reads var:{var} unguarded")
        for ref in set(re.findall(r"\b(te_tax_\w+)\b", body)) & set(self.values):
            self.assert_guarded(ref, seen)

    def test_every_script_value_in_the_gui_is_a_guarded_view(self):
        """Country views (te_tax_view_*), plus the interest-group cards' values
        (te_tax_disp_ig_*), which only an InterestGroup scope reads."""
        names = set(re.findall(r"ScriptValue\('(\w+)'\)", self.gui_text))
        self.assertTrue(names)
        group = set(re.findall(r"InterestGroup\.MakeScope\.ScriptValue\('(\w+)'\)", self.gui_text))
        self.assertTrue(group)
        for name in group:
            with self.subTest(name=name):
                self.assertTrue(name.startswith("te_tax_disp_ig_"), name)
                self.assert_guarded(name)
        self.assertNotRegex(self.gui_text, r"(GetPlayer|State)\.MakeScope\.ScriptValue\('te_tax_disp_ig_")
        for name in names - group:
            with self.subTest(name=name):
                self.assertTrue(name.startswith("te_tax_view_"), name)
                self.assertTrue(name in self.values and self.values[name] is not None, name)
                self.assertIn("has_variable", self.values[name])
                self.assert_guarded(name)

    def test_every_script_value_in_the_printed_loc_is_guarded(self):
        names = set()
        for key in self.printed:
            names |= set(re.findall(r"ScriptValue\('(\w+)'\)", self.loc[key]))
        self.assertTrue(names)
        for name in names:
            with self.subTest(name=name):
                if self.values.get(name) is not None:
                    self.assertTrue(name.startswith(("te_tax_view_", "te_tax_disp_ig_")), name)
                self.assert_guarded(name)
        # an interest-group card's value is read only through the group
        for key in self.printed:
            with self.subTest(key=key):
                self.assertNotRegex(self.loc[key], r"(GetPlayer|State)\.MakeScope\.ScriptValue\('te_tax_disp_ig_")

    def test_printed_loc_reads_the_player_never_the_entry(self):
        for key in self.printed:
            with self.subTest(key=key):
                self.assertNotIn("JournalEntry", self.loc[key])
                self.assertNotIn("[b]", self.loc[key])

    def test_every_loc_key_the_panels_name_exists(self):
        """In the mod's loc, or vanilla's for a good's own name (the goods
        catalog rows and the customs rows, Task 15, print each good by its key;
        a mod good's name is in the mod's loc)."""
        import json
        vanilla = json.loads((ROOT / "vanilla_parsed/localization_english.json").read_text(encoding="utf-8"))
        catalog = set(gen.consumption_catalog()) | set(gen.customs_catalog())
        for key in loc_keys_named_in(self.gui_text):
            with self.subTest(key=key):
                self.assertTrue(key in self.loc or (key in catalog and key in vanilla), key)

    def test_record_views_read_their_payload_only_while_the_record_is_open(self):
        """A closed record's payload is removed (or, after a civil war, may be
        a loser's stale copy): a view of it must test the record's own token."""
        for record, token in (("dr", "te_tax_dr_on"), ("bl", "te_tax_bl_on"),
                              ("pa", "te_tax_pa_on"), ("pb", "te_tax_pb_on"),
                              *((f"o{n}", f"te_tax_o{n}_on") for n in gen.OBLIGATION_SLOTS)):
            for name, body in self.values.items():
                if not name.startswith(f"te_tax_view_{record}_") or name == f"te_tax_view_{record}_on":
                    continue
                with self.subTest(name=name):
                    self.assertIn(f"var:{token} = 1", body)

    def test_debate_days_left_is_a_guarded_wrapper(self):
        body = self.values["te_tax_view_debate_days_left"]
        self.assertIn("has_variable = te_tax_bl_on", body)
        self.assertIn("value = te_tax_debate_days_left", body)

    def test_last_change_reads_code_changes_only(self):
        body = self.values["te_tax_view_last_change"]
        for n in range(1, HISTORY_SIZE + 1):
            self.assertIn(f"min = var:te_tax_h{n}_month", body)
        for key in KEYS:
            self.assertIn(f"min = var:te_tax_en_{key}_since", body)
        # kinds that changed the code: commenced, sunset, migrated, civil-war repair,
        # and the customs schedule's adopted level and market gained (Task 15)
        kinds = set(re.findall(r"var:te_tax_h1_kind = (\d+)", body))
        self.assertEqual(kinds, {"1", "2", "5", "7", "15", "17"})


class HistoryTest(unittest.TestCase):
    """The history list: eight rows, newest first, one line per entry."""

    @classmethod
    def setUpClass(cls):
        cls.values = value_bodies()
        cls.custom = script(GEN_CUSTOM_LOC)

    def test_rows_read_the_ring_newest_first(self):
        for i in range(1, HISTORY_SIZE + 1):
            for field in ("kind", "inst", "month"):
                body = self.values[f"te_tax_view_hist_{i}_{field}"]
                pairs = re.findall(r"var:te_tax_h_head = (\d) has_variable = te_tax_h(\d)_" + field, body)
                with self.subTest(position=i, field=field):
                    self.assertEqual(len(pairs), HISTORY_SIZE)
                    for head, entry in pairs:
                        self.assertEqual(int(entry), (int(head) - i) % HISTORY_SIZE + 1)

    def test_each_row_has_its_date_and_line(self):
        overview = gui(OVERVIEW)
        section = type_body(overview, "te_tax_history_section")
        table = loc()
        for i in range(1, HISTORY_SIZE + 1):
            with self.subTest(position=i):
                self.assertIn(f"te_tax_view_hist_{i}_kind", section)
                self.assertIn(f'"te_tax_hist_date_{i}"', section)
                self.assertIn(f"GetPlayer.GetCustom('te_tax_hist_event_{i}')", section)
                self.assertIn(f"te_tax_view_hist_{i}_month_y", table[f"te_tax_hist_date_{i}"])
                self.assertIn(f"te_tax_view_hist_{i}_month_mo", table[f"te_tax_hist_date_{i}"])

    def test_every_kind_has_a_line(self):
        table = loc()
        for i in range(1, HISTORY_SIZE + 1):
            body = block(self.custom, f"te_tax_hist_event_{i}")
            texts = re.findall(r"text = \{\s*trigger = \{([^}]*)\}\s*localization_key = (\w+)", body)
            kinds = {}
            for trigger, key in texts:
                kind = int(re.search(rf"te_tax_view_hist_{i}_kind = (\d+)", trigger).group(1))
                inst = re.search(rf"te_tax_view_hist_{i}_inst = (\d+)", trigger)
                kinds.setdefault(kind, []).append((int(inst.group(1)) if inst else None, key))
                self.assertNotRegex(trigger, r"var:|has_variable", "custom loc reads only the guarded views")
            with self.subTest(position=i):
                self.assertEqual(set(kinds), set(KINDS))
                self.assertEqual(sorted(inst for inst, _ in kinds[SUNSET_KIND]), [1, 2, 3, 4, 5])
                for entries in kinds.values():
                    for _, key in entries:
                        self.assertTrue(table.get(key), key)

    def test_sunset_lines_name_their_instrument_in_inst_order(self):
        body = block(self.custom, "te_tax_hist_event_1")
        for idx, key in enumerate(KEYS, start=1):
            self.assertRegex(body, rf"te_tax_view_hist_1_inst = {idx} \}}\s*localization_key = te_tax_hist_kind_sunset_{key}")

    def test_the_custom_loc_is_generated_and_registered(self):
        self.assertIn(GEN_CUSTOM_LOC, gen.OUTPUTS)
        self.assertIn(gen.HEADER, raw(GEN_CUSTOM_LOC).splitlines()[:3])
        self.assertIn(GEN_CUSTOM_LOC, raw("docs/auto_generated_files.md"))
        self.assertIn(f'"{GEN_CUSTOM_LOC}"', raw("scripts/nightly_audit_select.py"))


_TOKEN = re.compile(r'"[^"]*"|[{}]|[<>!?]=|==|[=<>]|[^\s{}=<>!?"]+')
_OPERATORS = {"=", "<", ">", "<=", ">=", "!=", "?=", "=="}


def multi_child_nots(text):
    """Line numbers of every `NOT = { ... }` holding more than one condition.

    What a multi-child NOT means is untested (NAND or NOR;
    docs/guides/scripting_best_practices.md, "Write NOR or NAND, Never a
    Multi-Child NOT"). A child is one operator at the block's own depth, so
    `NOT = { AND = { a = 1 b = 2 } }` has one."""
    text = uncomment(text)
    tokens = [(m.group(0), m.start()) for m in _TOKEN.finditer(text)]
    found = []
    for i in range(len(tokens) - 2):
        if [t for t, _ in tokens[i:i + 3]] != ["NOT", "=", "{"]:
            continue
        depth, children = 1, 0
        for token, _ in tokens[i + 3:]:
            if token == "{":
                depth += 1
            elif token == "}":
                depth -= 1
                if depth == 0:
                    break
            elif depth == 1 and token in _OPERATORS:
                children += 1
        if children > 1:
            found.append(text.count("\n", 0, tokens[i][1]) + 1)
    return found


class NoMultiChildNotTest(unittest.TestCase):
    """Every tax code script writes NOR = { } ("none of these") or NAND = { }
    ("not all of these"), never a NOT with several children."""

    def test_the_scanner(self):
        self.assertEqual(multi_child_nots("x = {\n\tNOT = { a = 1 b = 2 }\n}"), [2])
        self.assertEqual(multi_child_nots("NOT = {\n\thas_variable = v\n\tvar:v = 1\n}"), [1])
        self.assertEqual(multi_child_nots("NOT = { AND = { a = 1 b = 2 } }"), [])
        self.assertEqual(multi_child_nots("NOT = { a = { b = 1 c = 2 } }"), [])
        self.assertEqual(multi_child_nots("NAND = { a = 1 b = 2 } NOR = { c = 1 d = 2 }"), [])
        self.assertEqual(multi_child_nots("NOT = { a = 1 } # NOT = { b = 1 c = 2 }"), [])

    def test_no_tax_code_script_has_one(self):
        paths = sorted({str(p.relative_to(ROOT)) for pattern in ("common/**/te_tax_*.txt", "events/te_tax_*.txt")
                        for p in ROOT.glob(pattern)} | {JE})
        self.assertIn(TAX_SGUIS, paths)
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(multi_child_nots(raw(path)), [])

    def test_no_generator_output_has_one(self):
        """The generator's templates, rendered (so a template change is caught
        before the committed files are regenerated)."""
        rendered = gen.render_all()
        self.assertTrue(rendered)
        for path, data in rendered.items():
            if path.endswith(".txt"):
                with self.subTest(path=path):
                    self.assertEqual(multi_child_nots(data.decode("utf-8-sig")), [])


class LocTest(unittest.TestCase):
    def test_new_keys_live_in_the_tax_file(self):
        """organize_loc files je_tax_code* with the te_tax_ family (TAX)."""
        keys = tax_loc()
        for key in ("je_tax_code", "je_tax_code_desc", "je_tax_code_reason", "je_tax_code_status_none",
                    "te_tax_tab", "te_tax_tab_tt", "te_tax_tab_locked_tt", "te_tax_open_journal_tt",
                    "te_tax_open_budget", "te_tax_open_budget_tt", "te_tax_how_header"):
            with self.subTest(key=key):
                self.assertIn(key, keys)

    def test_concepts(self):
        concepts = script(CONCEPTS)
        table = loc()
        for name in ("concept_tax_code", "concept_tax_bill", "concept_tax_commencement"):
            with self.subTest(name=name):
                self.assertRegex(concepts, rf"(?m)^{name} = \{{")
                self.assertTrue(table.get(name))
                self.assertTrue(table.get(f"{name}_desc"))

    def test_no_new_tax_loc_ends_in_a_line_break_or_uses_brackets_for_bold(self):
        # The locked tab tooltip's header is concatenated straight onto the
        # unlock checklist (IsValidTooltip), so its trailing break separates
        # the two lines, as te_budget_tab_banking_locked_tt's does.
        joined = {"te_tax_tab_locked_tt"}
        for key, value in tax_loc().items():
            with self.subTest(key=key):
                self.assertEqual(value.endswith("\\n"), key in joined, key)
                self.assertNotIn("[b]", value)

    def test_amount_taxes_print_at_their_step_precision(self):
        """Rural assessment moves in steps of 0.025, so every land amount prints
        three decimals (two would show 0.425 as 0.43 and one step as +0.03);
        head tax moves in 0.05 and prints two."""
        text = "\n".join(f"{key}: {value}" for key, value in tax_loc().items())
        text += "\n" + "\n".join(gui(path) for path in NEW_GUI)
        found = {"land": 0, "head": 0}
        for name, fmt in re.findall(r"ScriptValue\('(\w+)'\)\|([^\]]*)\]", text):
            for key, digits in (("land", "3"), ("head", "2")):
                if re.fullmatch(rf"te_tax_view_\w*{key}\w*_rate|te_tax_step_{key}", name):
                    found[key] += 1
                    with self.subTest(name=name, fmt=fmt):
                        self.assertIn(fmt, (digits, "+" + digits))
        self.assertGreaterEqual(found["land"], 19)  # every land site today (the scan must see them)
        self.assertGreaterEqual(found["head"], 19)

    def test_destructive_actions_say_what_is_lost(self):
        keys = tax_loc()
        withdraw = keys["te_tax_tt_cmd_withdraw"]
        for phrase in ("commitment", "debate", "lost", "draft is kept"):
            self.assertIn(phrase, withdraw)
        discard = keys["te_tax_tt_cmd_draft_discard"]
        for phrase in ("every change made in it", "cannot be recovered"):
            self.assertIn(phrase, discard)

    def test_the_locked_tooltip_runs_into_the_checklist_on_the_next_line(self):
        tooltip = uncomment(mod_block(raw(BUDGET))[0])
        self.assertIn("Concatenate( Localize( 'te_tax_tab_locked_tt' ), "
                      "GetScriptedGui('te_budget_tax_tab_unlock_sgui').IsValidTooltip(", tooltip)
        self.assertNotIn("te_tt_break", tooltip)


class GuideTest(unittest.TestCase):
    def test_tables_list_the_tab_and_the_widgets(self):
        text = raw(GUIDE)
        self.assertRegex(text, r"\| `budget_panel\.gui` \| Budget \|[^\n]*Tax Code[^\n]*je_tax_code")
        for name in ("te_tax_overview_widget.gui", "te_tax_layout_widget.gui", "te_tax_workbench_widget.gui",
                     "te_tax_review_widget.gui", "te_tax_politics_widget.gui", "te_tax_generated_rows.gui"):
            self.assertRegex(text, rf"\| `{name}` \| `je_tax_code` \|")

    def test_guide_keeps_crlf(self):
        data = (ROOT / GUIDE).read_bytes()
        self.assertEqual(data.count(b"\r\n"), data.count(b"\n"))


if __name__ == "__main__":
    unittest.main()
