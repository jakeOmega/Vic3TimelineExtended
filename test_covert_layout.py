"""The Covert Warfare panels' layout (style-guide pass, docs/guides/gui_style_guide.md).

In the spirit of test_un_layout.py: the composers' section order; each named
root a gated wrapper the journal entry mounts; collapse flags that say their
default; explanations only in "How Covert Warfare Works"; subsections shown
only in the state they describe; what the overview draws for each code; the
display values' guards; loc tidiness; and the placeholder icons held to
docs/systems/covert_gui_icons.md.
"""
import glob
import os
import re
import unittest

from test_covert_op_registry import TYPES as OP_TYPES

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "covert_operations_widget.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_covert_warfare.txt")
VALUES = os.path.join(REPO, "common", "script_values", "covert_display_values.txt")
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")
ICONS_DOC = os.path.join(REPO, "docs", "systems", "covert_gui_icons.md")

# Owner, round 2: Funding second, next to its overview icon; Detection Risk
# is a table at the top of Operations, not a section of its own.
STATUS = ["te_covert_sec_operations", "te_covert_sec_funding", "te_covert_sec_networks",
          "te_covert_sec_counterintel"]
REFERENCE = ["te_covert_sec_how"]
# root name -> (container, what it wraps)
ROOTS = {
    "widget_je_covert_overview": ("custom_widget_container_1", "te_covert_overview_panel"),
    "widget_je_covert_status": ("custom_widget_container_2", "te_covert_status_sections"),
    "widget_je_covert_reference": ("custom_widget_container_3", "te_covert_reference_sections"),
}
OLD_ROOTS = ["widget_je_covert_command_centre", "widget_je_covert_operations", "widget_je_covert_networks"]

# Explanations that live in "How Covert Warfare Works" only.
HOW_KEYS = ["je_iw_how_ops", "je_iw_how_funding", "je_iw_how_detection", "je_iw_net_header_tooltip",
            "je_iw_how_tradecraft", "je_iw_how_ci", "je_iw_how_standing"]

DORMANT = "GetScriptedGui('covert_ops_dormant_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )"
CAUGHT = "GetScriptedGui('covert_last_exposed_known_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )"
NO_OPS = "IsDataModelEmpty( JournalEntry.GetCountry.MakeScope.GetList('iw_ops') )"

# The overview's placeholder icons (docs/systems/covert_gui_icons.md): what
# each one stands for -> the texture it uses now.
GENERIC = "gfx/interface/icons/generic_icons/"
STANDING_ICONS = {
    4: GENERIC + "green_checkmark.dds",
    3: GENERIC + "approval_icon.dds",
    2: GENERIC + "undecided_icon.dds",
    1: GENERIC + "disapproval_icon.dds",
    0: GENERIC + "red_cross.dds",
}
# Owner, round 2: an icon per Tradecraft tier (covert_tradecraft_tier).
TRADECRAFT_ICONS = {
    0: GENERIC + "maybe_icon.dds",
    1: GENERIC + "population.dds",
    2: "gfx/interface/politics_view/institution_level_icon.dds",
    3: "gfx/interface/icons/formation_order_icons/upgrade.dds",
    4: GENERIC + "most_senior_front_commander.dds",
}
OTHER_ICONS = {
    "funding_dormant": GENERIC + "warning.dds",
    "funding": GENERIC + "gdp.dds",
    "caught": "gfx/interface/icons/military_icons/navy_icons/detection_navy.dds",
    "slot": "gfx/interface/icons/event_icons/je_covert_warfare.dds",
}
# Final art, not placeholders: vanilla's own marks.
NOT_PLACEHOLDERS = {GENERIC + "trend_up.dds", GENERIC + "trend_down.dds", GENERIC + "trend_nochange.dds",
                    GENERIC + "transparent.dds", "gfx/interface/progressbar/progressbar_marker.dds"}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    depth = 0
    for j in range(m.end() - 1, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():j]
    raise AssertionError(f"type {name} never closes")


def _root(text, name):
    start = text.index(f'name = "{name}"')
    start = text.rindex("\nflowcontainer = {", 0, start)
    return text[start:text.index("\n}\n", start) + 3]


def _loc():
    out = {}
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        for m in re.finditer(r'^ ([\w.\-]+):\d* "(.*)"\s*$', _read(path), re.M):
            out[m.group(1)] = m.group(2)
    return out


def _gate_before(body, key):
    """The `visible` of the widget whose `text` is `key`: the last visible
    before the key, which the markup always puts first in the block."""
    head = body[: body.index(f'text = "{key}"')]
    return head.rsplit("visible = ", 1)[1].split("\n", 1)[0]


class OrderTest(unittest.TestCase):
    def test_status_and_reference_order(self):
        gui = _read(GUI)
        for composer, expected in (("te_covert_status_sections", STATUS),
                                   ("te_covert_reference_sections", REFERENCE)):
            found = re.findall(r"^\t\t(te_covert_sec_\w+) = \{", _type_body(gui, composer), re.M)
            self.assertEqual(found, expected, composer)

    def test_composers_and_overview_are_gated_on_the_active_entry(self):
        gui = _read(GUI)
        for t in ("te_covert_overview_panel", "te_covert_status_sections", "te_covert_reference_sections"):
            self.assertIn('visible = "[JournalEntry.IsActive]"', _type_body(gui, t)[:300], t)


class RootTest(unittest.TestCase):
    def test_the_entry_mounts_each_root_in_its_container(self):
        je = _read(JE)
        for name, (container, _) in ROOTS.items():
            self.assertRegex(je, rf'name = "{name}"\s*\n\s*container = "{container}"', name)
        self.assertEqual(len(re.findall(r"^\twidget = \{", je, re.M)), len(ROOTS))

    def test_each_root_is_a_gated_wrapper(self):
        gui = _read(GUI)
        for name, (_, inner) in ROOTS.items():
            root = _root(gui, name)
            self.assertIn('visible = "[JournalEntry.IsActive]"', root, name)
            self.assertIn(f"{inner} = {{}}", root, name)
            # A bare wrapper: nothing else in it.
            self.assertEqual(len(re.findall(r"^\t\w+ = \{", root, re.M)), 1, name)

    def test_the_old_roots_are_gone(self):
        text = _read(GUI) + _read(JE)
        for name in OLD_ROOTS:
            self.assertNotIn(f'"{name}"', text, name)

    def test_the_entry_has_no_status_text_and_its_lines_moved(self):
        self.assertNotIn("status_desc", re.sub(r"#[^\n]*", "", _read(JE)))
        ov = _type_body(_read(GUI), "te_covert_overview_panel")
        for tier in ("fortress", "hardened", "defended", "exposed", "vulnerable"):
            self.assertIn(f'tooltip = "je_iw_status_{tier}"', ov, tier)
        ops = _type_body(_read(GUI), "te_covert_sec_operations")
        self.assertIn('text = "je_iw_no_operations"', ops)
        # Widget loc, so the JournalEntry root, never ROOT (gotcha #20).
        loc = _loc()
        for tier in ("fortress", "hardened", "defended", "exposed", "vulnerable"):
            self.assertNotIn("ROOT.", loc[f"je_iw_status_{tier}"], tier)


class FlagTest(unittest.TestCase):
    """Collapse flags say their default (test_un_layout.FlagTest)."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(GUI)

    def test_section_flags_say_their_default(self):
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.text))
        self.assertEqual(flags, {"covert_ops_closed", "covert_nets_closed", "covert_funding_closed",
                                 "covert_counterintel_closed", "covert_how_open"})
        for f in flags:
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", self.text))
            bare = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", self.text)) - negated
            if f.endswith("_closed"):   # shown unless closed: one bare (show-more), the rest negated
                self.assertEqual(bare, 1, f)
                self.assertGreaterEqual(negated, 2, f)
            else:                        # shown only when opened: one negated (show-more)
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 2, f)

    def test_each_section_has_its_own_flag(self):
        for sec in STATUS + REFERENCE:
            body = _type_body(self.text, sec)
            self.assertEqual(len(re.findall(r"GetVariableSystem\.Toggle\('", body)), 1, sec)

    def test_only_how_it_works_starts_collapsed(self):
        how = _type_body(self.text, "te_covert_sec_how")
        self.assertIn("GetVariableSystem.Toggle('covert_how_open')", how)
        for sec in STATUS:
            self.assertRegex(_type_body(self.text, sec), r"Toggle\('covert_\w+_closed'\)", sec)


class StateGateTest(unittest.TestCase):
    """Subsections that only matter in one state are shown only in it."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(GUI)

    def test_networks_wait_for_a_network(self):
        body = _type_body(self.text, "te_covert_sec_networks")
        self.assertIn("visible = \"[Not( IsDataModelEmpty( JournalEntry.GetCountry.MakeScope.GetList('iw_nets') ) )]\"",
                      body[:200])

    def test_dormancy_is_said_once_above_the_rows(self):
        self.assertEqual(self.text.count('text = "je_iw_funding_dormant_banner"'), 1)
        ops = _type_body(self.text, "te_covert_sec_operations")
        self.assertIn(DORMANT, _gate_before(ops, "je_iw_funding_dormant_banner"))
        self.assertLess(ops.index("je_iw_funding_dormant_banner"), ops.index("datamodel ="))
        row = _type_body(self.text, "widget_je_covert_operation_row")
        self.assertNotIn("covert_ops_dormant_sgui", row)
        self.assertNotIn("je_iw_op_row_dormant", self.text)

    def test_detection_factors_are_said_once_above_the_rows(self):
        self.assertNotIn("te_covert_sec_detection", self.text)
        ops = _type_body(self.text, "te_covert_sec_operations")
        rows = ops.index("datamodel =")
        for key in ("je_iw_detection_header", "je_iw_detection_base", "je_iw_detection_funding",
                    "je_iw_detection_efficiency"):
            self.assertEqual(self.text.count(f'text = "{key}"'), 1, key)
            self.assertLess(ops.index(f'text = "{key}"'), rows, key)
        self.assertIn('tooltip = "je_iw_detection_factors_tooltip"', ops[:rows])
        # The table's card is not gated: every operation, and the next one
        # launched, shares these factors.
        card = ops[ops.rindex("covert_panel = {", 0, ops.index('text = "je_iw_detection_header"')):]
        self.assertNotRegex(card[:card.index("covert_subheader")], r"visible =")

    def test_the_empty_state_shows_only_with_no_rows(self):
        ops = _type_body(self.text, "te_covert_sec_operations")
        self.assertIn(NO_OPS, _gate_before(ops, "je_iw_no_operations"))
        # The card around the two lines shows only when one of them does.
        card = ops[ops.index("covert_panel = {"):ops.index('text = "je_iw_funding_dormant_banner"')]
        self.assertIn(f"Or( {DORMANT}, {NO_OPS} )", card)

    def test_last_caught_heading_and_line_follow_the_catch(self):
        ci = _type_body(self.text, "te_covert_sec_counterintel")
        heading = ci[ci.index("covert_subheader = {"):ci.index('text = "je_iw_ci_sub_caught"')]
        self.assertIn(CAUGHT, heading)
        line = ci[ci.index('text = "je_iw_ci_sub_caught"'):]
        self.assertIn(CAUGHT, line[:line.index("covert_last_exposed_sgui')")])

    def test_markers_hide_when_there_is_nothing_further(self):
        ov = _type_body(self.text, "te_covert_overview_panel")
        self.assertIn("visible = \"[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_tier'), '(CFixedPoint)4' )]\"", ov)
        # The network bar's marker went in round 3 (owner: "just the
        # strength, the bar filling up, and the trend").
        net = _type_body(self.text, "widget_je_covert_network_row")
        self.assertNotIn("marker = {", net)
        self.assertNotIn("covert_disp_net_next_intel_frac", self.text)

    def test_no_section_opens_on_a_line_that_can_be_empty(self):
        # Funding opens on the state line, which the custom loc always fills.
        fund = _type_body(self.text, "te_covert_sec_funding")
        panel = fund[fund.index("covert_panel = {"):]
        first = re.search(r"\n\t\t\t(\w+) = \{\s*\n\s*(\w+) = \"([^\"]*)\"", panel)
        self.assertEqual(first.group(1, 2, 3), ("covert_text", "text", "je_iw_funding_state"))
        self.assertIn("GetCustom('covert_funding_state_line')", _loc()["je_iw_funding_state"])


class OverviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ov = _type_body(_read(GUI), "te_covert_overview_panel")

    def _coded(self, value):
        """{code: texture} for the icons gated on ScriptValue(value) == code."""
        pat = (rf"visible = \"\[EqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('{value}'\), "
               rf"'\(CFixedPoint\)(-?\d+)' \)\]\"(.*?)texture = \"([^\"]+)\"")
        return {int(m.group(1)): m.group(3) for m in re.finditer(pat, self.ov, re.S)}

    def test_each_standing_code_draws_its_own_icon(self):
        self.assertEqual(self._coded("covert_disp_standing_code"), STANDING_ICONS)

    def test_each_tradecraft_tier_draws_its_own_icon(self):
        self.assertEqual(self._coded("covert_tradecraft_tier"), TRADECRAFT_ICONS)
        self.assertEqual(len(set(TRADECRAFT_ICONS.values())), 5)
        # Distinct from every other placeholder in the row.
        self.assertFalse(set(TRADECRAFT_ICONS.values()) & (set(STANDING_ICONS.values()) | set(OTHER_ICONS.values())))

    def test_ten_slots_lit_by_the_operations_running(self):
        for n in range(1, 11):
            self.assertIn(f"ScriptValue('covert_disp_slots_shown'), '(CFixedPoint){n}' )", self.ov, n)
            self.assertEqual(self.ov.count(f"ScriptValue('covert_active_display'), '(CFixedPoint){n}' )"), 2, n)
        self.assertNotIn("(CFixedPoint)11' )", self.ov)

    def test_the_trend_arrow_covers_every_code(self):
        self.assertEqual(self._coded("covert_disp_tc_trend"),
                         {1: GENERIC + "trend_up.dds", -1: GENERIC + "trend_down.dds", 0: GENERIC + "trend_nochange.dds"})

    def test_funding_warns_at_zero(self):
        self.assertEqual(self._coded("covert_funding_level_display"), {0: OTHER_ICONS["funding_dormant"]})
        self.assertIn(OTHER_ICONS["funding"], self.ov)

    def test_bars_read_display_fractions(self):
        for sv in ("covert_disp_capacity_frac", "covert_disp_tc_frac", "covert_disp_tc_next_frac"):
            self.assertIn(f"FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('{sv}') )", self.ov, sv)

    def test_the_bar_rows_line_up(self):
        # Label 100, bar 200, value 120 and a 24 px trend cell in both rows.
        rows = re.findall(r"minimumsize = \{ 100 -1 \}.*?size = \{ 200 18 \}.*?minimumsize = \{ 120 -1 \}.*?size = \{ 24 24 \}",
                          self.ov, re.S)
        self.assertEqual(len(rows), 2)


class OperationRowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row = _type_body(_read(GUI), "widget_je_covert_operation_row")

    def test_each_type_has_its_own_icon(self):
        found = re.findall(r"visible = \"\[ScriptContainer\.HasTag\('iw_op_(\w+)'\)\]\"\s*"
                           r"texture = \"gfx/interface/icons/diplomatic_action_icons/covert_(\w+)_action\.dds\"", self.row)
        self.assertEqual([a for a, _ in found], list(OP_TYPES))
        self.assertTrue(all(a == b for a, b in found))
        for t in OP_TYPES:
            self.assertIn(f"gfx/interface/icons/diplomatic_action_icons/covert_{t}_action.dds",
                          "\n".join(_git_files()), t)

    def test_controls_are_centred_beneath_the_lines(self):
        strip = self.row[self.row.index("covert_op_priority_stepper = { }") - 200:]
        self.assertIn("parentanchor = hcenter", strip[:200])
        self.assertIn("direction = horizontal", strip[:200])
        self.assertGreater(self.row.index("covert_op_priority_stepper = { }"), self.row.index('text = "je_iw_op_row_detection"'))

    def test_priority_meaning_is_the_stepper_labels_hover(self):
        # Owner, round 2: the "Priority: effect ..." line moved into the
        # stepper's hover. One label per level, gated on the level and on
        # every container having one.
        stepper = _type_body(_read(GUI), "covert_op_priority_stepper")
        self.assertIn("ignoreinvisible = yes", stepper)
        for n in (1, 2, 3):
            label = stepper[: stepper.index(f'tooltip = "je_iw_op_row_priority_{n}"')]
            gate = label.rsplit("visible = ", 1)[1].split("\n", 1)[0]
            self.assertIn("covert_ops_priority_ready_sgui", gate, n)
            self.assertIn(f"GetVariableValue('iw_priority'), '(CFixedPoint){n}')", gate, n)
            self.assertNotIn(f'text = "je_iw_op_row_priority_{n}"', self.row, n)
        self.assertEqual(stepper.count('default_format = "#tooltippable"'), 3)

    def test_row_tooltips_need_no_journal_entry(self):
        # A tooltip inside a datamodel item renders with the item's
        # ScriptContainer only (gui_modding_guide.md gotcha #24).
        loc = _loc()
        for key in ("je_iw_op_row_phase_prep_tt", "je_iw_op_row_phase_est_tt", "je_iw_op_row_phase_full_tt",
                    "je_iw_op_row_detection_tt", "je_iw_net_row_trend_growing", "je_iw_net_row_trend_decaying",
                    "je_iw_net_row_trend_holding", "je_iw_net_row_intel_service_tooltip",
                    "je_iw_net_row_intel_ops_tooltip", "je_iw_net_row_strength_tt",
                    "je_iw_op_row_priority_1", "je_iw_op_row_priority_2", "je_iw_op_row_priority_3"):
            self.assertNotIn("JournalEntry", loc[key], key)



class NetworkRowTest(unittest.TestCase):
    """The network row: the target's flag and title (round 2), then the
    strength, the bar filling up and the trend (round 3: no marker and no
    "45 -> 50" headline), then the report lines. The strength's hover says
    what each part of the report reveals."""

    @classmethod
    def setUpClass(cls):
        cls.row = _type_body(_read(GUI), "widget_je_covert_network_row")
        cls.loc = _loc()

    def test_the_row_leads_with_the_targets_flag(self):
        # Owner, round 2: vanilla's flag widget, as the UN overview's council
        # seats use it, from the stored capital, gated on the variable.
        head = self.row[: self.row.index('text = "je_iw_net_row_title"')]
        self.assertIn("flag = {", head)
        wrapper = head[head.rindex("widget = {"):]
        self.assertIn("visible = \"[ScriptContainer.HasVariable('iw_target_capital')]\"", wrapper[:wrapper.index("flag = {")])
        self.assertIn("datacontext = \"[ScriptContainer.MakeScope.Var('iw_target_capital').GetState.GetCountry]\"", wrapper)
        self.assertLess(self.row.index("flag = {"), self.row.index("je_iw_net_row_strength"))

    def test_strength_bar_and_trend_share_one_line(self):
        start = self.row.rindex("flowcontainer = {", 0, self.row.index('text = "je_iw_net_row_strength"'))
        line = self.row[start:self.row.index('text = "je_iw_net_row_ops"')]
        self.assertIn("direction = horizontal", line[:120])
        self.assertIn('tooltip = "je_iw_net_row_strength_tt"', line[:300])
        self.assertLess(line.index("je_iw_net_row_strength"), line.index("default_progressbar_horizontal"))
        self.assertLess(line.index("default_progressbar_horizontal"), line.index("iw_net_trend"))
        self.assertIn("ScriptValue('covert_disp_net_strength_frac')", line)
        self.assertNotIn("marker", line)
        self.assertEqual(self.row.count('text = "je_iw_net_row_strength'), 1)

    def test_strength_reads_the_figure_and_the_hover_names_the_marks(self):
        self.assertRegex(self.loc["je_iw_net_row_strength"], r"^Strength #v \[ScriptContainer\.GetVariableValue\('iw_net_strength'\)\|0\]#!$")
        hover = self.loc["je_iw_net_row_strength_tt"]
        for name in ("covert_net_intel_tier_1_strength", "covert_net_intel_tier_2_strength"):
            self.assertIn(name, hover, name)
        self.assertNotIn("marker", hover)
        for gone in ("je_iw_net_row_strength_to_service", "je_iw_net_row_strength_to_ops", "je_iw_net_row_strength_full"):
            self.assertNotIn(gone, self.loc, gone)


def _git_files():
    import subprocess
    out = subprocess.run(["git", "ls-files", "gfx/interface/icons/diplomatic_action_icons"], cwd=REPO,
                         capture_output=True, text=True).stdout
    return out.split("\n")


class FundingTableTest(unittest.TestCase):
    """Owner, round 3: the funding levels as a table, one row per level, with
    what each gives and its weekly cost, the level in force highlighted."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.fund = _type_body(cls.gui, "te_covert_sec_funding")
        cls.loc = _loc()

    def _rows(self):
        return re.findall(r"\n\t\t\tcovert_levels_row = \{(.*?)\n\t\t\t\}", self.fund, re.S)

    def test_a_header_and_a_row_per_level_under_the_stepper(self):
        rows = self._rows()
        self.assertEqual(len(rows), 7)
        self.assertIn('text = "je_iw_fund_tbl_head_level"', rows[0])
        self.assertNotIn("row_current", rows[0])
        self.assertLess(self.fund.index("covert_cc_funding_stepper = { }"), self.fund.index("covert_levels_row = {"))
        for n, row in enumerate(rows[1:]):
            self.assertIn(f"visible = \"[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('covert_funding_level_display'), '(CFixedPoint){n}' )]\"", row, n)
            self.assertIn(f'text = "je_iw_fund_tbl_level_{n}"', row, n)
            self.assertIn(f'"je_iw_fund_tbl_cost_{n}"' if n else '"je_iw_fund_tbl_none"', row, n)
            if n >= 2:
                self.assertIn(f'"je_iw_fund_tbl_stealth_{n}"', row, n)
                self.assertIn(f'"je_iw_fund_tbl_capacity_{n}"', row, n)

    def test_the_tint_is_one_visible_defaulting_to_hidden(self):
        body = _type_body(self.gui, "covert_levels_row")
        tint = body[body.index("icon = {"):body.index("flowcontainer = {")]
        self.assertEqual(tint.count("visible"), 1)
        self.assertIn('block "row_current" {\n\t\t\t\tvisible = no', tint)

    def test_every_figure_is_read_never_typed(self):
        for n in range(1, 6):
            self.assertIn(f"ScriptValue('covert_disp_cost_at_{n}')|D]", self.loc[f"je_iw_fund_tbl_cost_{n}"], n)
        for n in range(2, 6):
            self.assertIn(f"ScriptValue('covert_funding_detect_reduction_at_{n}')", self.loc[f"je_iw_fund_tbl_stealth_{n}"])
            self.assertIn(f"ScriptValue('covert_funding_ci_ic_at_{n}')", self.loc[f"je_iw_fund_tbl_capacity_{n}"])
        for n in range(6):
            self.assertEqual(self.loc[f"je_iw_fund_tbl_level_{n}"], f"#v {n}#! $iw_funding_name_{n}$")
        for key in [k for k in self.loc if k.startswith("je_iw_fund_tbl_")]:
            if key.startswith("je_iw_fund_tbl_level_"):
                continue
            outside = re.sub(r"\[[^\[\]]*\]", "", self.loc[key])
            self.assertNotRegex(outside, r"\d", key)

    def test_the_costs_are_the_cost_formulas_terms(self):
        values = _read(VALUES)
        per = values[values.index("covert_disp_cost_per_level = {"):]
        per = per[:per.index("\n}\n")]
        for term in ("value = covert_priority_cost_units", "add = 1", "multiply = covert_operations_cost_scale"):
            self.assertIn(term, per)
        for n in range(1, 6):
            block = values[values.index(f"covert_disp_cost_at_{n} = {{"):]
            block = block[:block.index("\n}\n")]
            self.assertIn("value = covert_disp_cost_per_level", block)
            if n > 1:
                self.assertIn(f"multiply = {n}", block)

    def test_the_ladder_and_the_separate_cost_rows_are_gone(self):
        sguis = _read(os.path.join(REPO, "common", "scripted_guis", "covert_warfare_sguis.txt"))
        self.assertNotIn("covert_funding_ladder_sgui", sguis + self.gui)
        for key in ("je_iw_funding_cost_now", "je_iw_funding_cost_next", "je_iw_ladder_row_0"):
            self.assertNotIn(f'"{key}"', self.gui, key)
            self.assertNotIn(key, self.loc, key)
        # The cost's explanation stays, on the cost column's header.
        self.assertIn('tooltip = "je_iw_funding_cost_tt"', self._rows()[0])


# ---- Round 3, rule 1: nothing a player reads ends in "..." ----------------
# The owner's measurements, in GUI units per character: the large font about
# 10, the medium (table) font about 8.6. The small font was not measured; it
# is taken at the medium rate, which overstates it. Plus 10% margin.
UNITS = {"small": 8.6, "medium": 8.6, "large": 10.0}
MARGIN = 1.1
# The longest names a dynamic label can show.
LONGEST = {
    "covert_funding_level_name": "Covert Network",   # iw_funding_name_3
    "covert_tradecraft_tier_name": "Established",    # iw_tradecraft_tier_name_2
}
# Fixed-width cells whose text is set outside a row type: (key, width, font).
FIXED_CELLS = [
    ("je_iw_ov_standing_0", 108, "small"), ("je_iw_ov_standing_1", 108, "small"),
    ("je_iw_ov_standing_2", 108, "small"), ("je_iw_ov_standing_3", 108, "small"),
    ("je_iw_ov_standing_4", 108, "small"), ("je_iw_ov_funding_label", 108, "small"),
    ("je_iw_ov_tc_label", 108, "small"), ("je_iw_ov_caught_label", 108, "small"),
    ("je_iw_capacity_header", 100, "medium"), ("je_iw_tradecraft_header", 100, "medium"),
    ("je_iw_capacity_total", 120, "medium"), ("je_iw_tradecraft_line", 120, "medium"),
    ("je_iw_funding_stepper_label", 80, "medium"), ("je_iw_funding_stepper_value", 180, "medium"),
    ("je_iw_priority_stepper_label", 80, "small"), ("je_iw_stand_down_button", 140, "small"),
    ("je_iw_net_row_strength", 120, "medium"),
    # Section headers: 520 wide, less the arrow.
    ("je_iw_sec_ops_header", 440, "large"), ("je_iw_funding_header", 440, "large"),
    ("je_iw_net_header", 440, "large"), ("je_iw_defense_header", 440, "large"),
    ("je_iw_how_header", 440, "large"),
]
# Columns of the row types, by block name: (width, font).
ROW_COLUMNS = {
    "covert_value_row": {"row_label": (320, "medium"), "row_value": (140, "medium")},
    "covert_levels_row": {"level_text": (170, "medium"), "stealth_text": (80, "medium"),
                          "capacity_text": (80, "medium"), "cost_text": (130, "medium")},
}


def _shown(value, loc):
    """What a player reads, with every dynamic part at its longest."""
    for _ in range(2):
        value = re.sub(r"\$([\w.]+)\$", lambda m: loc.get(m.group(1), m.group(0)), value)
    value = re.sub(r"\[Concept\('\w+', ?'([^']*)'\)\]", r"\1", value)
    value = re.sub(r"\[(concept_\w+)\]", lambda m: loc[m.group(1)], value)

    def data(m):
        expr = m.group(0)
        for name, longest in LONGEST.items():
            if f"GetCustom('{name}')" in expr:
                return longest
        return "123.4K" if "|D]" in expr else "100"
    for _ in range(3):
        value = re.sub(r"\[[^\[\]]*\]", data, value)
    value = re.sub(r"@\w+!", "@@", value)                    # a text icon: about two characters
    value = re.sub(r"#[A-Za-z_]+(?:;[^ ]*)? ?", "", value)    # format openers
    return value.replace("#!", "")


class WidthBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = _loc()
        cls.gui = _read(GUI)

    def _fits(self, key, width, font):
        text = _shown(self.loc[key], self.loc) if key in self.loc else _shown(key, self.loc)
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, width, f"{key}: {text!r} needs {need:.0f} of {width}")

    def test_the_longest_dynamic_names_are_named(self):
        funding = [self.loc[f"iw_funding_name_{n}"] for n in range(6)]
        tiers = [self.loc[f"iw_tradecraft_tier_name_{n}"] for n in range(5)]
        self.assertEqual(max(funding, key=len), LONGEST["covert_funding_level_name"])
        self.assertEqual(max(tiers, key=len), LONGEST["covert_tradecraft_tier_name"])

    def test_fixed_cells(self):
        for key, width, font in FIXED_CELLS:
            with self.subTest(key=key):
                self.assertIn(f'"{key}"', self.gui, key)
                self._fits(key, width, font)

    def test_row_columns(self):
        checked = 0
        for row_type, columns in ROW_COLUMNS.items():
            for m in re.finditer(rf"\n\t+{row_type} = \{{", self.gui):
                end = self.gui.index("\n" + m.group(0)[1:].split(row_type)[0] + "}", m.end())
                block = self.gui[m.end():end]
                for column, (width, font) in columns.items():
                    b = re.search(rf'blockoverride "{column}" \{{(.*?)\}}', block, re.S)
                    if not b:
                        continue
                    text = re.search(r'\btext = "([^"]*)"', b.group(1))
                    if text:
                        with self.subTest(row=row_type, column=column, text=text.group(1)):
                            self._fits(text.group(1), width, font)
                            checked += 1
        self.assertGreater(checked, 40)

    def test_the_overview_funding_word_is_short(self):
        # "Covert Network" does not fit a 108-unit cell, so the cell says
        # "Funding 3" and the name is on hover.
        self.assertIn("covert_funding_level_name", self.loc["je_iw_ov_funding_tt"])
        self.assertNotIn("covert_funding_level_name", self.loc["je_iw_ov_funding_label"])


class HowItWorksTest(unittest.TestCase):
    def test_explanations_live_in_how_it_works(self):
        gui = _read(GUI)
        how = _type_body(gui, "te_covert_sec_how")
        for key in HOW_KEYS:
            self.assertIn(f'"{key}"', how, key)
        for sec in STATUS + ["te_covert_overview_panel", "widget_je_covert_operation_row",
                             "widget_je_covert_network_row"]:
            body = _type_body(gui, sec)
            for key in HOW_KEYS:
                self.assertNotIn(f'"{key}"', body, f"{sec} still explains ({key})")

    def test_every_topic_has_a_heading(self):
        how = _type_body(_read(GUI), "te_covert_sec_how")
        self.assertEqual(how.count("covert_subheader = {"), len(HOW_KEYS))
        self.assertEqual(how.count("covert_note = {"), len(HOW_KEYS))


class LocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = _loc()
        cls.gui = _read(GUI)

    def test_every_key_the_panels_name_exists(self):
        for key in set(re.findall(r'\b(?:text|tooltip) = "([a-z]\w+)"', self.gui)):
            self.assertIn(key, self.loc, key)

    def test_no_blank_lines_at_either_end(self):
        # Style rule 8: no tooltip or line starts or ends with an empty line,
        # and a line that is its own row needs no leading spaces.
        keys = set(re.findall(r'\b(?:text|tooltip) = "([a-z]\w+)"', self.gui))
        keys |= {"concept_tradecraft_desc", "concept_agent_network_desc", "concept_covert_funding_desc",
                 "concept_operation_slots_desc", "concept_funding_stealth_desc"}
        for key in keys:
            value = self.loc[key]
            self.assertFalse(value.startswith("\\n") or value.endswith("\\n"), key)
            self.assertFalse(value.startswith(" "), key)

    def test_new_terms_are_concepts(self):
        concepts = _read(CONCEPTS)
        for c in ("concept_tradecraft", "concept_agent_network", "concept_covert_funding", "concept_operation_slots",
                  "concept_funding_stealth"):
            self.assertRegex(concepts, rf"(?m)^{c} = \{{\}}", c)
            self.assertIn(f"{c}_desc", self.loc, c)
        self.assertIn("concept_tradecraft", self.loc["je_iw_tradecraft_header"])
        self.assertIn("concept_operation_slots", self.loc["je_iw_slots_detail"])

    def test_detection_risk_and_funding_stealth_are_concepts(self):
        # Owner, round 3. Detection Risk is the existing detection concept
        # renamed, not a second concept meaning the same thing.
        concepts = _read(CONCEPTS)
        self.assertEqual(self.loc["concept_operation_detection"], "Detection Risk")
        self.assertNotRegex(concepts, r"(?m)^concept_detection_risk = ")
        self.assertEqual(self.loc["je_iw_detection_header"], "[concept_operation_detection]")
        self.assertEqual(self.loc["je_iw_detection_funding_label"], "[concept_funding_stealth]")
        self.assertIn("concept_operation_detection", self.loc["je_iw_op_row_detection"])
        for key in ("je_iw_how_detection", "je_iw_how_funding"):
            self.assertIn("[concept_funding_stealth]", self.loc[key], key)
            self.assertIn("[concept_operation_detection]", self.loc[key], key)
        self.assertIn("Stealth", self.loc["je_iw_fund_tbl_head_stealth"])
        self.assertIn("concept_funding_stealth", self.loc["je_iw_fund_tbl_head_stealth"])
        # No "Detection Risk risk" once the name changed.
        for key, value in self.loc.items():
            self.assertNotIn("[concept_operation_detection] risk", value, key)

    def test_no_raw_modifier_keys_in_covert_text(self):
        # Owner, round 3: Efficiency Factor showed the raw modifier key. Any
        # country_/state_ key in what a player reads must be a $splice$ (the
        # modifier's own name) or inside a data expression.
        for key, value in self.loc.items():
            if not any(w in (key + value).lower() for w in ("covert", "iw_", "intelligence", "tradecraft", "espionage")):
                continue
            shown = re.sub(r"\$[\w.]+\$", "", value)
            for _ in range(3):
                shown = re.sub(r"\[[^\[\]]*\]", "", shown)
            shown = re.sub(r"#tooltippable;tooltip:\S+", "", shown)
            self.assertNotRegex(shown, r"\b(?:country|state|building|unit)_[a-z_]+_(?:add|mult)\b", key)
        self.assertIn("$country_covert_operation_efficiency_mult$", self.loc["concept_covert_efficiency_desc"])

    def test_standing_floors_are_printed_not_typed(self):
        how = self.loc["je_iw_how_standing"]
        for n in range(1, 5):
            self.assertIn(f"covert_disp_standing_floor_{n}", how)


class DisplayValueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = _read(VALUES)
        cls.blocks = {}
        for m in re.finditer(r"^(covert_disp_\w+) = \{\n(.*?)^\}", text, re.M | re.S):
            cls.blocks[m.group(1)] = m.group(2)

    def test_every_variable_read_is_guarded(self):
        self.assertTrue(self.blocks)
        for name, body in self.blocks.items():
            for var in set(re.findall(r"var:(\w+)", body)):
                self.assertIn(f"has_variable = {var}", body, f"{name} reads var:{var} unguarded")

    def test_every_display_value_is_read(self):
        # Nothing in script reads them; the panels and their loc do, or
        # another display value does (the per-level cost).
        text = _read(GUI) + "".join(_loc().values())
        others = "\n".join(self.blocks.values())
        for name in self.blocks:
            self.assertTrue(f"'{name}'" in text or re.search(rf"\b{name}\b", others), name)

    def test_the_standing_floors_live_only_here(self):
        for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True):
            if os.path.abspath(path) == VALUES:
                continue
            self.assertNotRegex(_read(path), r"intelligence_capacity_relative\s*>=", path)


class IconsTest(unittest.TestCase):
    """Every placeholder is listed in covert_gui_icons.md with the path it
    uses now, and the overview uses no texture the list doesn't know."""

    def test_the_doc_lists_every_placeholder(self):
        doc = _read(ICONS_DOC)
        for path in list(STANDING_ICONS.values()) + list(TRADECRAFT_ICONS.values()) + list(OTHER_ICONS.values()):
            self.assertIn(f"`{path}`", doc, path)

    def test_the_overview_uses_only_listed_textures(self):
        gui = _read(GUI)
        used = set(re.findall(r'texture = "([^"]+)"', _type_body(gui, "te_covert_overview_panel")))
        used |= set(re.findall(r'texture = "([^"]+)"', _type_body(gui, "covert_ov_slot")))
        known = set(STANDING_ICONS.values()) | set(TRADECRAFT_ICONS.values()) | set(OTHER_ICONS.values()) | NOT_PLACEHOLDERS
        self.assertEqual(used - known, set())


if __name__ == "__main__":
    unittest.main()
