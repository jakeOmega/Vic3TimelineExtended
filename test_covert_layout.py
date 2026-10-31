"""The Covert Warfare panels' layout (style-guide pass, docs/guides/gui_style_guide.md).

In the spirit of test_un_layout.py: the composers' section order; each named
root a gated wrapper the journal entry mounts; collapse flags that say their
default; explanations only in "How Covert Warfare Works"; subsections shown
only in the state they describe; what the overview draws for each code; the
display values' guards; loc tidiness; and the covert icons (PR #586) held
to docs/systems/covert_gui_icons.md, each code to its file.
"""
import glob
import os
import re
import unittest

import gui_tree
from test_covert_op_registry import HOSTILE_TYPES, PLACEHOLDER_ICON
from test_covert_op_registry import TYPES as OP_TYPES

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "covert_operations_widget.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_covert_warfare.txt")
VALUES = os.path.join(REPO, "common", "script_values", "covert_display_values.txt")
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")
ICONS_DOC = os.path.join(REPO, "docs", "systems", "covert_gui_icons.md")
SGUIS_FILE = os.path.join(REPO, "common", "scripted_guis", "covert_warfare_sguis.txt")

# Owner, round 2: Funding second, next to its overview icon; Detection Risk
# is a table at the top of Operations, not a section of its own.
STATUS = ["te_covert_sec_operations", "te_covert_sec_funding", "te_covert_sec_networks",
          "te_covert_sec_counterintel", "te_covert_sec_known"]
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
            "je_iw_how_tradecraft", "je_iw_how_ci", "je_iw_how_watching", "je_iw_how_standing"]

DORMANT = "GetScriptedGui('covert_ops_dormant_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )"
CAUGHT = "GetScriptedGui('covert_last_exposed_known_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )"
NO_OPS = "IsDataModelEmpty( JournalEntry.GetCountry.MakeScope.GetList('iw_ops') )"

# The overview's icons, the covert set from PR #586 (docs/systems/
# covert_gui_icons.md): what each one stands for -> its file.
GENERIC = "gfx/interface/icons/generic_icons/"
COVERT_ICONS = "gfx/interface/icons/covert_icons/"
STANDING_ICONS = {
    4: COVERT_ICONS + "standing_fortress.dds",
    3: COVERT_ICONS + "standing_hardened.dds",
    2: COVERT_ICONS + "standing_defended.dds",
    1: COVERT_ICONS + "standing_exposed.dds",
    0: COVERT_ICONS + "standing_vulnerable.dds",
}
# Owner, round 2: an icon per Tradecraft tier (covert_tradecraft_tier).
TRADECRAFT_ICONS = {n: COVERT_ICONS + f"tradecraft_{n}.dds" for n in range(5)}
OTHER_ICONS = {
    "funding_dormant": COVERT_ICONS + "funding_dormant.dds",
    "funding": COVERT_ICONS + "funding.dds",
    "caught": COVERT_ICONS + "spy_caught.dds",
    "slot": COVERT_ICONS + "operation_slot.dds",
}
# Vanilla's own marks, kept as the UN's panels keep them.
# The eye-shaped progressbar_marker is not among them: rule 5 retired it, and
# the bars' thresholds are thin lines (COV-6, covert_bar_line).
VANILLA_MARKS = {GENERIC + "trend_up.dds", GENERIC + "trend_down.dds", GENERIC + "trend_nochange.dds",
                 GENERIC + "transparent.dds"}


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


def _shown_raw(loc, key, depth=0):
    """A key's value with its $splices$ resolved, recursively: a tooltip's
    context is lost through a splice as surely as in the key itself
    (gui_modding_guide.md gotcha #24)."""
    value = loc[key]
    if depth > 5:
        return value
    return re.sub(r"\$([\w.]+)\$", lambda m: _shown_raw(loc, m.group(1), depth + 1) if m.group(1) in loc else m.group(0), value)


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
                                 "covert_counterintel_closed", "covert_known_closed", "covert_how_open"})
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

    def test_bar_thresholds_are_lines_with_hovers(self):
        # Rule 5: a fixed threshold on a bar is a thin line with its own hover,
        # never the eye-shaped marker (COV-6). Each Tradecraft tier's floor
        # and each standing floor, placed by a display value.
        ov = _type_body(self.text, "te_covert_overview_panel")
        self.assertNotIn("progressbar_marker", self.text)
        line = _type_body(self.text, "covert_bar_line")
        self.assertIn('texture = "gfx/interface/backgrounds/white.dds"', line)
        self.assertIn('block "line_tooltip" {}', line)
        loc = _loc()
        for n in range(1, 5):
            for value, tip in ((f"covert_disp_tc_floor_{n}_frac", f"je_iw_tc_floor_{n}_tt"),
                               (f"covert_disp_standing_floor_{n}_frac", f"je_iw_standing_floor_{n}_tt")):
                with self.subTest(value=value):
                    self.assertIn(f"ScriptValue('{value}')", ov)
                    self.assertIn(f'tooltip = "{tip}"', ov)
                    self.assertIn(tip, loc)
        # The headline names the next floor, never with the arrow rule 5
        # keeps for where a value is heading.
        self.assertNotIn("→", loc["je_iw_tradecraft_line"])

    def test_markers_hide_when_there_is_nothing_further(self):
        # The network bar's marker went in round 3 (owner: "just the
        # strength, the bar filling up, and the trend").
        net = _type_body(self.text, "widget_je_covert_network_row")
        self.assertNotIn("marker = {", net)
        self.assertNotIn("covert_disp_net_next_intel_frac", self.text)

    def test_no_section_opens_on_a_line_that_can_be_empty(self):
        # Funding opens on the state line, shown only while funded with
        # nothing running (COV-11: zero funding is said in the overview and
        # above the operations), then the stepper, which is never empty.
        fund = _type_body(self.text, "te_covert_sec_funding")
        panel = fund[fund.index("covert_panel = {"):]
        first = re.search(r"\n\t\t\t(\w+) = \{\s*\n\s*visible = \"([^\"]*)\"\s*\n\s*text = \"([^\"]*)\"", panel)
        self.assertEqual(first.group(1, 3), ("covert_text", "je_iw_funding_state"))
        self.assertIn("GetScriptedGui('covert_funding_ready_sgui').IsShown", first.group(2))
        self.assertLess(panel.index("je_iw_funding_state"), panel.index("covert_cc_funding_stepper = { }"))
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
        # Distinct from every other icon in the row.
        self.assertFalse(set(TRADECRAFT_ICONS.values()) & (set(STANDING_ICONS.values()) | set(OTHER_ICONS.values())))

    def test_ten_slots_lit_by_the_slots_filled(self):
        # An operation fills one slot per level of its priority, so the icons
        # lit are the slots filled, not the operations running.
        for n in range(1, 11):
            self.assertIn(f"ScriptValue('covert_disp_slots_shown'), '(CFixedPoint){n}' )", self.ov, n)
            self.assertEqual(self.ov.count(f"ScriptValue('covert_slots_used_display'), '(CFixedPoint){n}' )"), 2, n)
        self.assertNotIn("ScriptValue('covert_active_display'), '(CFixedPoint)", self.ov)
        self.assertNotIn("(CFixedPoint)11' )", self.ov)

    def test_the_rows_keep_their_width_whichever_cells_show(self):
        # Both rows are centred, so each must be one width whatever shows
        # (gui_modding_guide.md gotcha #43).
        text = _read(GUI)
        tree = gui_tree.parse(text)
        cell = gui_tree.size(next(n for n in tree.walk() if n.kind == "type" and n.name == "covert_ov_icon_label"))
        # Row 1: one standing, funding and Tradecraft cell each always shows
        # (codes 0-4, zero or not, tiers 0-4); the catch, which comes and goes,
        # sits in an ungated slot of a cell's size. Centred at 342, it ended near 527.
        row = gui_tree.node_after(tree, text, "### Row 1: standing", "flowcontainer")
        self.assertEqual(row.prop("parentanchor").value, "hcenter")
        groups = {}
        for child in gui_tree.widgets(row):
            gate = child.prop("visible") and re.search(r"ScriptValue\('(\w+)'\), '\(CFixedPoint\)(\d+)'",
                                                       child.prop("visible").value)
            if child.kind == "covert_ov_icon_label" and gate:
                groups.setdefault(gate.group(1), set()).add(child.prop("visible").value.startswith("[Not(") or int(gate.group(2)))
            else:
                self.assertEqual((child.kind, child.prop("visible")), ("widget", None))
                self.assertEqual(gui_tree.size(child), cell)
                (caught,) = gui_tree.widgets(child)
                self.assertEqual(caught.prop("visible").value, f"[{CAUGHT}]")
                groups["caught"] = {"slot"}
        self.assertEqual(groups, {"covert_disp_standing_code": set(range(5)), "covert_funding_level_display": {0, True},
                                  "covert_tradecraft_tier": set(range(5)), "caught": {"slot"}})
        # Row 2's strip: up to ten 30 slots at 2 apart, held at the ten's width.
        strip = next(n for n in gui_tree.node_after(tree, text, "### Row 2: operation slots", "flowcontainer").walk()
                     if n.kind == "flowcontainer" and n.prop("direction") and n.prop("direction").value == "horizontal")
        slots = gui_tree.widgets(strip)
        self.assertEqual([s.kind for s in slots], ["covert_ov_slot"] * 10)
        self.assertEqual(strip.prop("parentanchor").value, "hcenter")
        slot = gui_tree.size(next(n for n in tree.walk() if n.kind == "type" and n.name == "covert_ov_slot"))[0]
        spacing = int(strip.prop("spacing").value)
        self.assertEqual(gui_tree.size(strip, "minimumsize"), (10 * slot + 9 * spacing, -1))

    def test_the_trend_arrow_covers_every_code(self):
        self.assertEqual(self._coded("covert_disp_tc_trend"),
                         {1: GENERIC + "trend_up.dds", -1: GENERIC + "trend_down.dds", 0: GENERIC + "trend_nochange.dds"})

    def test_funding_warns_at_zero(self):
        self.assertEqual(self._coded("covert_funding_level_display"), {0: OTHER_ICONS["funding_dormant"]})
        self.assertIn(OTHER_ICONS["funding"], self.ov)

    def test_bars_read_display_fractions(self):
        for sv in ("covert_disp_capacity_frac", "covert_disp_tc_frac"):
            self.assertIn(f"FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('{sv}') )", self.ov, sv)

    def test_the_bar_rows_line_up(self):
        # Label 100, bar 180, value 140 and a 24 px trend cell in both rows
        # (COV-14: the value is at 16 now, and the top tier's line is longest).
        rows = re.findall(r"minimumsize = \{ 100 -1 \}.*?size = \{ 180 18 \}.*?minimumsize = \{ 140 -1 \}.*?size = \{ 24 24 \}",
                          self.ov, re.S)
        self.assertEqual(len(rows), 2)


class OperationRowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row = _type_body(_read(GUI), "widget_je_covert_operation_row")

    def test_each_type_has_its_own_icon(self):
        # A type still waiting for its own art borrows another type's
        # (PLACEHOLDER_ICON); the icon pass deletes its entry.
        found = re.findall(r"visible = \"\[ScriptContainer\.HasTag\('iw_op_(\w+)'\)\]\"\s*"
                           r"texture = \"gfx/interface/icons/diplomatic_action_icons/covert_(\w+)_action\.dds\"", self.row)
        self.assertEqual([a for a, _ in found], list(OP_TYPES))
        self.assertTrue(all(PLACEHOLDER_ICON.get(a, a) == b for a, b in found))
        for t in OP_TYPES:
            art = PLACEHOLDER_ICON.get(t, t)
            self.assertIn(f"gfx/interface/icons/diplomatic_action_icons/covert_{art}_action.dds",
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
        self.assertNotIn("#tooltippable", stepper)  # style guide rule 3

    def test_row_tooltips_need_no_journal_entry(self):
        # A tooltip inside a datamodel item renders with the item's
        # ScriptContainer only (gui_modding_guide.md gotcha #24).
        loc = _loc()
        for key in ("je_iw_op_row_phase_prep_tt", "je_iw_op_row_phase_est_tt", "je_iw_op_row_phase_full_tt",
                    "je_iw_op_row_detection_tt", "je_iw_net_row_trend_growing", "je_iw_net_row_trend_decaying",
                    "je_iw_net_row_trend_holding", "je_iw_net_row_intel_service_tooltip",
                    "je_iw_net_row_intel_ops_tooltip", "je_iw_net_report_tt", "je_iw_net_row_tt",
                    "je_iw_net_row_report_1_tt", "je_iw_net_row_report_2_tt", "je_iw_net_row_country",
                    "je_iw_net_row_head_start",
                    "je_iw_op_row_priority_1", "je_iw_op_row_priority_2", "je_iw_op_row_priority_3",
                    "je_iw_known_row_tt", "je_iw_known_row_months", "je_iw_known_row_attacker",
                    "je_iw_known_ordered", "je_iw_known_ordered_tt", "je_iw_known_expose_tooltip",
                    # The row's buttons (COV-9a) and the hovers COV-1 and COV-4 added.
                    "je_iw_stand_down_tooltip", "je_iw_priority_step_up_tooltip",
                    "je_iw_priority_step_down_tooltip", "je_iw_op_row_strength_line",
                    *(f"je_iw_op_row_{t}_tt" for t in OP_TYPES),
                    *(f"je_iw_op_row_exposure_{n}_tt" for n in range(1, 5))):
            self.assertNotIn("JournalEntry", _shown_raw(loc, key), key)



class NetworkTableTest(unittest.TestCase):
    """The Agent Networks table (COV-12, the owner's 2026-10-27 call over
    round 3's two-line rows): a head, then one line a network, in shared
    columns: the target's flag, the country, strength (the figure, the bar
    filling up and the trend; round 3: no marker and no "45 -> 50"
    headline), our operations there, the head start and the report's word.
    The Report head's hover says what each part of the report reveals."""

    COLUMNS = [28, 120, 112, 40, 94, 66]

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.row = _type_body(cls.gui, "widget_je_covert_network_row")
        cls.head = _type_body(cls.gui, "covert_net_head")
        cls.loc = _loc()

    @staticmethod
    def _cells(body):
        """The widths of the direct children, in order: each child's first
        `size = { w` or `minimumsize = { w`."""
        widths, depth, child = [], 0, None
        for line in body.split("\n"):
            s = line.strip()
            if depth == 0 and s.endswith("= {") and not s.startswith(("background", "blockoverride")):
                child = []
            if child == []:
                m = re.match(r"(?:size|minimumsize) = \{ (\d+)", s)
                if m:
                    child.append(int(m.group(1)))
            depth += s.count("{") - s.count("}")
            if depth == 0 and child is not None:
                if child:
                    widths.append(child[0])
                child = None
        return widths

    def test_head_and_rows_share_the_columns(self):
        self.assertEqual(self._cells(self.row), self.COLUMNS)
        head = [28] + [int(m) for m in re.findall(r"size = \{ (\d+) 24 \}", self.head)[1:]]
        # The head's Ops cell keeps the cell type's default size, 40.
        cell = _type_body(self.gui, "covert_net_head_cell")
        self.assertIn("size = { 40 24 }", cell)
        head.insert(3, 40)
        self.assertEqual(head, self.COLUMNS)
        for body in (self.row, self.head):
            self.assertIn("spacing = 2", body[:200])
        # 5 + the columns + 2 between + 5 is the panel's 480 column, the
        # width of the Known Foreign Operations rows.
        self.assertEqual(sum(self.COLUMNS) + 2 * (len(self.COLUMNS) - 1) + 10, 480)
        self.assertIn("margin = { 5 2 }", self.row[:200])
        self.assertIn("margin = { 5 1 }", self.head[:200])

    def test_the_section_is_the_head_then_the_rows(self):
        sec = _type_body(self.gui, "te_covert_sec_networks")
        panel = sec[sec.index("covert_panel = {"):]
        self.assertIn("visible = \"[Not(GetVariableSystem.Exists('covert_nets_closed'))]\"", panel[:200])
        self.assertLess(panel.index("covert_net_head = {}"), panel.index("datamodel = \"[JournalEntry.GetCountry.MakeScope.GetList('iw_nets')]\""))
        self.assertIn("widget_je_covert_network_row = {", panel)

    def test_the_row_leads_with_the_targets_flag(self):
        # Vanilla's tiny_flag, as the Cultural Hegemony board draws its rows,
        # from the stored capital, gated on the variable.
        head = self.row[: self.row.index('text = "je_iw_net_row_country"')]
        self.assertIn("tiny_flag = {", head)
        wrapper = head[head.rindex("widget = {", 0, head.index("tiny_flag")):]
        self.assertIn("visible = \"[ScriptContainer.HasVariable('iw_target_capital')]\"", wrapper[:wrapper.index("tiny_flag = {")])
        self.assertIn("datacontext = \"[ScriptContainer.MakeScope.Var('iw_target_capital').GetState.GetCountry]\"", wrapper)

    def test_the_country_wraps_and_carries_the_networks_hover(self):
        cell = self.row[self.row.rindex("textbox = {", 0, self.row.index('text = "je_iw_net_row_country"')):]
        cell = cell[:cell.index("\n\t\t}")]
        self.assertIn("multiline = yes", cell)
        self.assertNotIn("elide", cell)
        self.assertIn('tooltip = "je_iw_net_row_tt"', cell)
        self.assertNotIn("#tooltippable", cell)  # style guide rule 3
        hover = _shown_raw(self.loc, "je_iw_net_row_tt")
        self.assertIn("covert_net_catch_display", hover)
        self.assertIn("covert_net_catch_max_display", hover)

    def test_strength_bar_and_trend_share_one_cell(self):
        start = self.row.index('text = "je_iw_net_row_strength_value"')
        cell = self.row[self.row.rindex("size = { 112 24 }", 0, start):self.row.index('text = "je_iw_net_row_ops_value"')]
        self.assertIn("direction = horizontal", cell)
        self.assertLess(cell.index("je_iw_net_row_strength_value"), cell.index("default_progressbar_horizontal"))
        self.assertLess(cell.index("default_progressbar_horizontal"), cell.index("iw_net_trend"))
        self.assertIn("ScriptValue('covert_disp_net_strength_frac')", cell)
        self.assertNotIn("marker", cell)
        for trend in ("growing", "decaying", "holding"):
            self.assertIn(f'tooltip = "je_iw_net_row_trend_{trend}"', cell, trend)
        self.assertRegex(self.loc["je_iw_net_row_strength_value"],
                         r"^#v \[ScriptContainer\.GetVariableValue\('iw_net_strength'\)\|0\]#!$")

    def test_the_head_cells_say_what_their_columns_are(self):
        for key, tip in (("je_iw_net_head_strength", "je_iw_net_head_strength_tt"),
                         ("je_iw_net_head_ops", "je_iw_net_head_ops_tt"),
                         ("je_iw_net_head_start", "je_iw_net_head_start_tt"),
                         ("je_iw_net_head_report", "je_iw_net_report_tt")):
            with self.subTest(key=key):
                block = self.head[self.head.rindex("covert_net_head_cell = {", 0, self.head.index(f'"{key}"')):]
                self.assertIn(f'tooltip = "{tip}"', block[:block.index("}\n\t\t}")])
                self.assertIn(tip, self.loc)
        self.assertIn("covert_net_head_start_max", self.loc["je_iw_net_head_start_tt"])

    def test_the_report_hover_names_the_marks(self):
        hover = self.loc["je_iw_net_report_tt"]
        for name in ("covert_net_intel_tier_1_strength", "covert_net_intel_tier_2_strength"):
            self.assertIn(name, hover, name)
        self.assertNotIn("marker", hover)
        # The two-line row's keys are gone with it.
        for gone in ("je_iw_net_row_strength", "je_iw_net_row_strength_tt", "je_iw_net_row_ops",
                     "je_iw_net_row_benefit", "je_iw_net_row_intel_none",
                     "je_iw_net_row_strength_to_service", "je_iw_net_row_strength_to_ops", "je_iw_net_row_strength_full"):
            self.assertNotIn(gone, self.loc, gone)
            self.assertNotIn(f'"{gone}"', self.gui, gone)

    def test_the_head_start_says_month_once(self):
        value = self.loc["je_iw_net_row_head_start"]
        self.assertIn("GetVariableValue('iw_net_head_start_offer'), '(CFixedPoint)1'", value)
        self.assertEqual(self.loc["je_iw_net_row_head_start_one"], "#v 1#! month")
        self.assertTrue(self.loc["je_iw_net_row_head_start_many"].endswith("#! months"))
        # Either ending fits the 94 column at the row size (WidthBudgetTest
        # reads the SelectLocalization as one number).
        for key in ("je_iw_net_row_head_start_one", "je_iw_net_row_head_start_many"):
            text = _shown(self.loc[key], self.loc)
            self.assertLessEqual(len(text) * UNITS["row"] * MARGIN, 94, text)


def _git_files():
    import subprocess
    out = subprocess.run(["git", "ls-files", "gfx/interface/icons/diplomatic_action_icons"], cwd=REPO,
                         capture_output=True, text=True).stdout
    return out.split("\n")


HOSTILE = HOSTILE_TYPES   # the types a defender can watch
KNOWN_TT_KEYS = ("iw_expose_known_exists_tt", "iw_expose_known_ours_tt", "iw_expose_known_unordered_tt",
                 "iw_expose_known_free_tt", "covert_known_expose_effect_tt")


class KnownSectionTest(unittest.TestCase):
    """Known Foreign Operations (watching a caught operation): one row per
    record in the viewer's iw_known_ops, hidden while it is empty, with an
    Expose button that hands the row's record to covert_expose_known_sgui."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.sec = _type_body(cls.gui, "te_covert_sec_known")
        cls.row = _type_body(cls.gui, "widget_je_covert_known_row")
        cls.sgui = _braced(_read(SGUIS_FILE), r"^covert_expose_known_sgui = \{")
        cls.loc = _loc()

    def test_the_composer_instances_it_after_counterintelligence(self):
        composer = _type_body(self.gui, "te_covert_status_sections")
        self.assertLess(composer.index("te_covert_sec_counterintel = {}"), composer.index("te_covert_sec_known = {}"))

    def test_the_military_tab_gets_it_from_the_composer(self):
        # The Covert tab instances te_covert_status_sections, so it needs no edit of its own.
        self.assertNotIn("te_covert_sec_known", _read(MILITARY))
        self.assertIn("te_covert_status_sections = {}", _read(MILITARY))

    def test_hidden_while_nothing_is_watched(self):
        self.assertIn("visible = \"[Not( IsDataModelEmpty( JournalEntry.GetCountry.MakeScope.GetList('iw_known_ops') ) )]\"",
                      self.sec[:260])

    def test_rows_come_from_the_known_list_and_read_their_record(self):
        self.assertEqual(self.sec.count("datamodel ="), 1)
        self.assertIn("datamodel = \"[JournalEntry.GetCountry.MakeScope.GetList('iw_known_ops')]\"", self.sec)
        item = self.sec[self.sec.index("item = {"):]
        self.assertIn("widget_je_covert_known_row = {", item)
        self.assertIn("datacontext = \"[Scope.GetScriptContainer]\"", item)

    def test_the_header_toggles_an_open_by_default_flag(self):
        self.assertEqual(len(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.sec)), 1)
        self.assertIn("GetVariableSystem.Toggle('covert_known_closed')", self.sec)
        self.assertIn('text = "je_iw_known_header"', self.sec)

    def test_each_hostile_type_has_its_icon_name_and_effect_hover(self):
        icons = re.findall(r"visible = \"\[ScriptContainer\.HasTag\('iw_known_(\w+)'\)\]\"\s*"
                           r"texture = \"gfx/interface/icons/diplomatic_action_icons/covert_(\w+)_action\.dds\"", self.row)
        self.assertEqual([a for a, _ in icons], list(HOSTILE))
        self.assertTrue(all(a == b for a, b in icons))
        tracked = "\n".join(_git_files())
        for t in HOSTILE:
            self.assertIn(f"gfx/interface/icons/diplomatic_action_icons/covert_{t}_action.dds", tracked, t)
        names = re.findall(r"visible = \"\[ScriptContainer\.HasTag\('iw_known_(\w+)'\)\]\"\s*"
                           r"text = \"iw_op_name_(\w+)\"\s*tooltip = \"iw_op_exposed_desc_(\w+)\"", self.row)
        self.assertEqual([a for a, _, _ in names], list(HOSTILE))
        self.assertTrue(all(a == b == c for a, b, c in names))
        # The old operation rows' own tags are not reused here.
        self.assertNotIn("HasTag('iw_op_", self.row)

    def test_the_flag_and_the_attackers_name_wait_for_the_stored_capital(self):
        head = self.row[: self.row.index('text = "je_iw_known_row_attacker"')]
        wrapper = head[head.rindex("widget = {"):]
        self.assertIn("flag = {", wrapper)
        self.assertIn("visible = \"[ScriptContainer.HasVariable('iw_attacker_capital')]\"", wrapper[:wrapper.index("flag = {")])
        self.assertIn("datacontext = \"[ScriptContainer.MakeScope.Var('iw_attacker_capital').GetState.GetCountry]\"", wrapper)
        title = self.row[self.row.rindex("visible =", 0, self.row.index('text = "je_iw_known_row_attacker"')):]
        self.assertIn("ScriptContainer.HasVariable('iw_attacker_capital')", title[:160])
        self.assertIn("Var('iw_attacker_capital').GetState.GetCountry.GetName", self.loc["je_iw_known_row_attacker"])

    def test_the_row_says_how_long_and_the_hover_what_it_earns_and_costs(self):
        self.assertIn("GetVariableValue('iw_watch_months')", self.loc["je_iw_known_row_months"])
        # The row's hover is under the months line; as in vanilla, the line
        # is not underlined (style guide rule 3).
        line = self.row[self.row.rindex("widget_je_covert_operation_detail = {", 0, self.row.index('text = "je_iw_known_row_months"')):]
        self.assertNotIn("#tooltippable", line[:120])
        self.assertIn('tooltip = "je_iw_known_row_tt"', self.row)
        hover = self.loc["je_iw_known_row_tt"]
        for part in ("iw_watch_months", "iw_watch_net", "covert_net_watch_gain_p1", "covert_net_watch_gain_p3"):
            self.assertIn(part, hover, part)

    def test_an_ordered_exposure_is_a_line_of_its_own(self):
        line = self.row[self.row.rindex("visible =", 0, self.row.index('text = "je_iw_known_ordered"')):]
        self.assertIn("ScriptContainer.HasVariable('iw_expose_ordered')", line[:120])
        self.assertIn('tooltip = "je_iw_known_ordered_tt"', line[:260])

    def test_the_button_hands_its_record_to_the_scripted_gui(self):
        button = self.row[self.row.index("button = {"):]
        self.assertEqual(len(re.findall(r"^\t+button = \{", self.row, re.M)), 1)
        self.assertIn("datacontext = \"[GetScriptedGui('covert_expose_known_sgui')]\"", button)
        scope = "GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( 'iw_known', ScriptContainer.MakeScope ).End"
        self.assertIn(f"enabled = \"[ScriptedGui.IsValid( {scope} )]\"", button)
        self.assertIn(f"onclick = \"[ScriptedGui.Execute( {scope} )]\"", button)
        self.assertIn('tooltip = "je_iw_known_expose_tooltip"', button)
        self.assertIn('text = "je_iw_known_expose_button"', button)
        # Below every line of the row, centred.
        self.assertGreater(self.row.index("button = {"), self.row.index('text = "je_iw_known_row_months"'))
        # The tooltip reads the same scope, and the engine's reasons and effect lines.
        tip = self.loc["je_iw_known_expose_tooltip"]
        self.assertIn(f"ScriptedGui.IsValidTooltip( {scope} )", tip)
        self.assertIn(f"ScriptedGui.ExecuteTooltip( {scope} )", tip)
        self.assertNotIn("JournalEntry", tip)

    def test_the_scripted_gui_fails_closed_and_only_orders_the_work(self):
        s = _words(self.sgui)
        self.assertIn("saved_scopes = { iw_known }", s)
        valid = _words(_braced(self.sgui, r"^\tis_valid = \{"))
        for part in ("exists = scope:iw_known", "has_variable_list = iw_known_ops",
                     "is_target_in_variable_list = { name = iw_known_ops target = scope:iw_known }",
                     "has_tag = iw_known_rec", "NOT = { has_variable = iw_expose_ordered }",
                     "var:iw_attacker ?= { NOT = { covert_exposure_in_flight = yes } }"):
            self.assertIn(part, valid, part)
        effect = _words(_braced(self.sgui, r"^\teffect = \{"))
        self.assertTrue(effect.startswith("custom_tooltip = { text = covert_known_expose_effect_tt"), effect)
        # `?=`: the tooltip walks the effect every hover frame, and a link that
        # failed to bind would otherwise log an undefined scope each time.
        self.assertIn("scope:iw_known ?= { set_variable = { name = iw_expose_ordered value = 1 } }", effect)
        self.assertIn("trigger_event = { id = covert_warfare.4 }", effect)
        # Nothing else: the exposure itself is the hidden event's work.
        self.assertNotIn("covert_exposure_fire", effect)
        self.assertIn("ai_is_valid = { always = no }", s)
        for key in KNOWN_TT_KEYS:
            self.assertIn(key, self.sgui, key)
            self.assertIn(key, self.loc, key)

    def test_how_it_works_explains_watching(self):
        how = _type_body(self.gui, "te_covert_sec_how")
        self.assertIn('text = "je_iw_how_sub_watching"', how)
        self.assertLess(how.index("je_iw_how_ci"), how.index("je_iw_how_sub_watching"))
        self.assertLess(how.index("je_iw_how_sub_watching"), how.index("je_iw_how_sub_standing"))
        # Names the section the exposure comes from.
        self.assertIn("Known Foreign Operations", self.loc["je_iw_how_watching"])
        # The Counterintelligence text no longer says a catch is named in Last
        # Caught (only an exposure is) or that nothing else names a sponsor.
        ci = self.loc["je_iw_how_ci"]
        self.assertNotIn("When our counterintelligence catches a foreign operation, its sponsor is named", ci)
        self.assertIn("Known Foreign Operations", ci)


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
# The owner's measurements, in GUI units per character: the serif face about
# 10 at 20 (0.5 a point, so 8.5 at the 17 row size), the overview's tooltip
# face 8.6 at 16. Plus 10% margin. The panel's sizes are its own
# covert_fontsize_* templates (COV-14, the 17 / 20 / 16 ladder), read from
# the file, so a change of type re-budgets every cell; "large" is the
# section headers' vanilla font, which is not the panel's.
_SIZES = {m.group(1): int(m.group(2)) for m in re.finditer(
    r"template covert_fontsize_(\w+) \{\s*fontsize = (\d+)", _read(GUI))}
UNITS = {"row": 10.0 / 20 * _SIZES["row"], "heading": 10.0 / 20 * _SIZES["heading"],
         "overview": 8.6 / 16 * _SIZES["overview"], "large": 10.0}
MARGIN = 1.1
# The longest names a dynamic label can show.
LONGEST = {
    "covert_funding_level_name": "Covert Network",   # iw_funding_name_3
    "covert_tradecraft_tier_name": "Established",    # iw_tradecraft_tier_name_2
}
# Fixed-width cells whose text is set outside a row type: (key, width, font).
FIXED_CELLS = [
    ("je_iw_ov_standing_0", 108, "overview"), ("je_iw_ov_standing_1", 108, "overview"),
    ("je_iw_ov_standing_2", 108, "overview"), ("je_iw_ov_standing_3", 108, "overview"),
    ("je_iw_ov_standing_4", 108, "overview"), ("je_iw_ov_funding_label", 108, "overview"),
    ("je_iw_ov_tc_label", 108, "overview"), ("je_iw_ov_caught_label", 108, "overview"),
    ("je_iw_capacity_header", 100, "overview"), ("je_iw_tradecraft_header", 100, "overview"),
    ("je_iw_capacity_total", 140, "overview"), ("je_iw_tradecraft_line", 140, "overview"),
    ("je_iw_funding_stepper_label", 80, "row"), ("je_iw_funding_stepper_value", 180, "row"),
    ("je_iw_priority_stepper_label", 80, "row"), ("je_iw_stand_down_button", 140, "row"),
    # The Agent Networks table (COV-12): heads and values in their columns.
    ("je_iw_net_head_country", 120, "row"), ("je_iw_net_head_strength", 112, "row"),
    ("je_iw_net_head_ops", 40, "row"), ("je_iw_net_head_start", 94, "row"),
    ("je_iw_net_head_report", 66, "row"), ("je_iw_net_row_strength_value", 30, "row"),
    ("je_iw_net_row_ops_value", 40, "row"), ("je_iw_net_row_head_start", 94, "row"),
    ("je_iw_net_row_report_0", 66, "row"),
    ("je_iw_net_row_report_1", 66, "row"), ("je_iw_net_row_report_2", 66, "row"),
    # Section headers: 520 wide, less the arrow.
    ("je_iw_sec_ops_header", 440, "large"), ("je_iw_funding_header", 440, "large"),
    ("je_iw_net_header", 440, "large"), ("je_iw_defense_header", 440, "large"),
    ("je_iw_known_header", 440, "large"), ("je_iw_how_header", 440, "large"),
    # The Known Foreign Operations button: 150 wide, less the margin.
    ("je_iw_known_expose_button", 140, "row"), ("je_iw_known_ordered", 460, "row"),
]
# Columns of the row types, by block name: (width, font).
ROW_COLUMNS = {
    "covert_value_row": {"row_label": (320, "row"), "row_value": (140, "row")},
    "covert_levels_row": {"level_text": (170, "row"), "stealth_text": (80, "row"),
                          "capacity_text": (80, "row"), "cost_text": (130, "row")},
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


def _font_of(gui, key):
    """The covert_fontsize_* template the textbox showing `key` reads: its
    own `using`, or, when the key is set in a blockoverride of a type
    instance, the type's."""
    at = gui.index(f'text = "{key}"')
    depth, i = 0, at
    openers = []
    while i > 0 and len(openers) < 3:
        i -= 1
        if gui[i] == "}":
            depth += 1
        elif gui[i] == "{":
            if depth == 0:
                line = gui[gui.rindex("\n", 0, i) + 1:i]
                openers.append((line.strip(), i))
            else:
                depth -= 1
    name, start = openers[0]
    body = gui[start:]
    body = body[:body.index("\n" + gui[gui.rindex("\n", 0, start) + 1:start].split(name.split()[0])[0] + "}")]
    m = re.search(r"using = covert_fontsize_(\w+)", body)
    if m and not name.startswith("blockoverride"):
        return m.group(1)
    instance = openers[1][0].split(" =")[0] if name.startswith("blockoverride") else name.split(" =")[0]
    m = re.search(r"using = covert_fontsize_(\w+)", _type_body(gui, instance))
    return m and m.group(1)


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

    def test_every_textbox_reads_a_panel_template(self):
        # COV-14: no textbox in the panel sets its own size from vanilla's
        # ladder; each reads one of the three templates.
        self.assertEqual(set(_SIZES), {"row", "heading", "overview"})
        self.assertEqual((_SIZES["row"], _SIZES["heading"], _SIZES["overview"]), (17, 20, 16))
        self.assertNotRegex(self.gui, r"using = fontsize_(small|medium|large|xl)\b")

    def test_the_fixed_cells_fonts_are_the_markups(self):
        # The font each FIXED_CELLS entry is budgeted at is the one its
        # textbox (or, for a type instance's block, the type) reads.
        for key, _, font in FIXED_CELLS:
            if font == "large":
                continue
            with self.subTest(key=key):
                self.assertEqual(_font_of(self.gui, key), font)

    def test_the_tradecraft_line_fits_with_either_ending(self):
        # Its ending is a SelectLocalization, which _shown reads as one number.
        for option in ("je_iw_tradecraft_line_next", "je_iw_tradecraft_line_top"):
            with self.subTest(option=option):
                text = "100 " + _shown(self.loc[option], self.loc)
                self.assertLessEqual(len(text) * UNITS["overview"] * MARGIN, 140, text)

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
    """The covert icons (PR #586, the UN's UnIconsTest shape): each code
    draws its own file, the icon list records every file, and the overview
    draws nothing else but vanilla's trend and bar marks."""

    def test_the_doc_records_every_icon(self):
        doc = _read(ICONS_DOC)
        for path in list(STANDING_ICONS.values()) + list(TRADECRAFT_ICONS.values()) + list(OTHER_ICONS.values()):
            self.assertIn(f"`{path.rsplit('/', 1)[1]}`", doc, path)
        self.assertIn(f"`{COVERT_ICONS}`", doc)

    def test_the_overview_uses_only_the_covert_icons_and_vanilla_marks(self):
        gui = _read(GUI)
        used = set(re.findall(r'texture = "([^"]+)"', _type_body(gui, "te_covert_overview_panel")))
        used |= set(re.findall(r'texture = "([^"]+)"', _type_body(gui, "covert_ov_slot")))
        known = set(STANDING_ICONS.values()) | set(TRADECRAFT_ICONS.values()) | set(OTHER_ICONS.values()) | VANILLA_MARKS
        self.assertEqual(used - known, set())
        self.assertEqual(set(STANDING_ICONS.values()) | set(TRADECRAFT_ICONS.values()) | set(OTHER_ICONS.values()),
                         {p for p in used if p.startswith(COVERT_ICONS)})

    def test_the_slot_keeps_its_fade_and_draws_one_file(self):
        slot = _type_body(_read(GUI), "covert_ov_slot")
        self.assertEqual(slot.count(f'texture = "{OTHER_ICONS["slot"]}"'), 2)
        self.assertEqual(slot.count("alpha = 0.25"), 1)

    def test_no_placeholder_is_left(self):
        gui = _read(GUI)
        for gone in ("green_checkmark", "approval_icon", "undecided_icon", "disapproval_icon", "red_cross",
                     "warning.dds", "gdp.dds", "maybe_icon", "population.dds", "institution_level_icon",
                     "formation_order_icons/upgrade", "most_senior_front_commander", "detection_navy",
                     "event_icons/je_covert_warfare"):
            self.assertNotIn(gone, gui, gone)


MILITARY = os.path.join(REPO, "gui", "panel_military.gui")
TAB_SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "covert_warfare_triggers.txt")
BUTTONS = os.path.join(REPO, "common", "scripted_buttons", "covert_warfare_scripted_buttons.txt")
TAB_TAG = "### MOD: Covert tab (te_covert) ###"
NUCLEAR_TAG = "### MOD: Nuclear tab (te_nuclear) ###"
TAB_GATE = "GetScriptedGui('te_military_covert_tab_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"
TAB_UNLOCK = "GetScriptedGui('te_military_covert_tab_unlock_sgui')"
SLOTS = ("first", "second", "third", "fourth", "fifth")


def _marked(text, tag):
    """Each block of panel_military.gui marked with `tag`, up to its END MOD line."""
    out = []
    start = text.find(tag)
    while start != -1:
        end = text.index("### END MOD ###", start)
        out.append(text[start:end])
        start = text.find(tag, end)
    return out


def _braced(text, opener):
    """The body of the first `opener` block (the text between its braces)."""
    m = re.search(opener, text, re.M)
    assert m, opener
    depth = 0
    for j in range(m.end() - 1, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():j]
    raise AssertionError(f"{opener} never closes")


def _words(script):
    """Script with comments dropped and whitespace collapsed, for comparing."""
    return " ".join(re.sub(r"#[^\n]*", "", script).split())


class MilitaryCovertTabTest(unittest.TestCase):
    """The Military panel's Covert tab, the fifth slot (style guide rule 9; a
    copy of the Nuclear tab, MilitaryTabTest in test_nuclear_layout.py): the
    journal entry's own composers under GetPlayerJournalEntry, gated, greyed
    until the entry runs, and ending with Open Journal Entry."""

    @classmethod
    def setUpClass(cls):
        cls.military = _read(MILITARY)
        cls.blocks = _marked(cls.military, TAB_TAG)

    def _content(self):
        body = self.blocks[1]
        self.assertIn('name = "te_military_covert_tab"', body)
        return body

    def test_two_marked_blocks_the_button_and_the_content(self):
        self.assertEqual(len(self.blocks), 2)
        self.assertIn('blockoverride "fifth_button"', self.blocks[0])
        self.assertIn("visible = \"[InformationPanel.IsTabSelected('te_covert')]\"", self._content())

    def test_the_tab_composes_the_journal_roots_types_in_order(self):
        body = self._content()
        mounted = re.findall(r'name = "(widget_je_covert_\w+)"', _read(JE))
        wrapped = [ROOTS[name][1] for name in mounted]
        self.assertEqual(wrapped, ["te_covert_overview_panel", "te_covert_status_sections",
                                   "te_covert_reference_sections"])
        self.assertEqual(re.findall(r"^\t+(te_\w+) = \{\}", body, re.M), wrapped)
        # The link back to the entry comes after every section.
        self.assertGreater(body.index('text = "te_system_tab_open_journal"'), body.index(wrapped[-1]))
        self.assertIn("onclick = \"[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]\"", body)

    def test_the_journal_draws_nothing_the_composers_do_not(self):
        """No te_je_* piece is needed (feasibility study 5.1): no goal bar, no
        scripted bars, no status text, and no scripted button a human sees."""
        je = re.sub(r"#[^\n]*", "", _read(JE))
        for absent in ("progressbar", "scripted_progress_bar", "status_desc", "current_value"):
            self.assertNotIn(absent, je, absent)
        buttons = re.sub(r"#[^\n]*", "", _read(BUTTONS))
        names = re.findall(r"^\tscripted_button = (\w+)", je, re.M)
        self.assertEqual(len(names), 2)
        for name in names:
            self.assertRegex(_braced(buttons, rf"^{name} = \{{"), r"visible = \{\s*is_ai = yes\s*\}", name)
        self.assertNotIn("te_je_", self._content())

    def test_the_gate_sits_above_the_journal_entry_datacontext(self):
        body = self._content()
        dc = body.index("datacontext = \"[GetPlayerJournalEntry('je_covert_warfare')]\"")
        self.assertLess(body.index(f'visible = "[{TAB_GATE}]"'), dc)
        # Never on the widget that carries the datacontext itself.
        opener = body.rindex("flowcontainer = {", 0, dc)
        self.assertNotIn("visible", body[opener:dc])
        # The header sits outside the gate.
        self.assertLess(body.index('text = "je_covert_warfare"'), body.index(f'visible = "[{TAB_GATE}]"'))

    def test_the_column_is_as_wide_as_the_journal_roots(self):
        body = self._content()
        dc = body.index("GetPlayerJournalEntry('je_covert_warfare')")
        head = body[dc:body.index("te_covert_overview_panel", dc)]
        self.assertIn("minimumsize = { 520 -1 }", head)
        self.assertIn("parentanchor = hcenter", head)

    def test_the_button_is_greyed_until_the_entry_runs(self):
        button = self.blocks[0]
        self.assertIn(f'enabled = "[{TAB_GATE}]"', button)
        self.assertIn("onclick = \"[InformationPanel.SelectTab('te_covert')]\"", button)
        self.assertIn(f"{TAB_UNLOCK}.IsValidTooltip(", button)
        for half in ("fifth_button_visibility", "fifth_button_visibility_checked"):
            m = re.search(rf'blockoverride "{half}" \{{\s*visible = "(.*)"', button)
            self.assertTrue(m, half)
            self.assertIn("IsTabSelected('te_covert')", m.group(1))
            self.assertIn(f"{TAB_UNLOCK}.IsShown(", m.group(1))
        loc = _loc()
        for key in ("te_military_tab_covert", "te_military_tab_covert_tt", "te_military_tab_covert_locked_tt",
                    "te_military_covert_open_journal_tt", "covert_warfare_unlock_tt"):
            self.assertIn(key, loc)

    def test_the_nuclear_and_covert_tabs_do_not_share_a_slot(self):
        def slots(blocks):
            found = set()
            for block in blocks:
                found |= set(re.findall(r'blockoverride "(\w+?)_button', block))
            return found
        nuclear = _marked(self.military, NUCLEAR_TAG)
        self.assertEqual(slots(nuclear[:1]), {"fourth"})
        self.assertEqual(slots(self.blocks[:1]), {"fifth"})
        # And no other tab of the strip is on the fifth slot.
        strip = _braced(self.military, r"^\t\t\ttab_buttons = \{")
        self.assertEqual(strip.count('blockoverride "fifth_button"'), 1)
        self.assertEqual({s for s in SLOTS if f'blockoverride "{s}_button"' in strip}, set(SLOTS))
        self.assertNotIn("IsTabSelected('te_covert')", "".join(nuclear))

    def test_no_tab_on_the_strip_carries_an_icon(self):
        """System tabs carry no icon, as vanilla's tabs don't (gui_style_guide.md
        rule 9): no mod block in the Military panel's tab strip draws one, in
        any slot block (*_button_icon, *_button_name or another)."""
        strip = _braced(self.military, r"^\t\t\ttab_buttons = \{")
        tabs = re.findall(r"### MOD: [^\n]*tab[^\n]*###.*?### END MOD ###", strip, re.S)
        self.assertEqual(len(tabs), 2)   # Nuclear and Covert
        for block in tabs:
            code = re.sub(r"#[^\n]*", "", block)
            with self.subTest(tab=block.split("\n", 1)[0]):
                self.assertNotRegex(code, r"\bicon = \{")
                self.assertNotIn("texture =", code)

    def test_the_mod_labels_fit_five_slots(self):
        """Five tabs in 540 are (540 - 2 x 3 margin - 2 x 5 dividers) / 5 = 104.8
        wide, and tab_text_properties keeps 10 each side for the name: 84.8, at
        the large-font budget (10 a character, plus 10%)."""
        loc = _loc()
        for key in ("te_military_tab_nuclear", "te_military_tab_covert"):
            self.assertLessEqual(len(loc[key]) * 10 * 1.1, 84.8, key)

    def test_the_gates_read_the_rule_and_the_entry(self):
        sguis = _read(TAB_SGUIS)
        gate = _braced(sguis, r"^te_military_covert_tab_sgui = \{")
        self.assertIn("has_game_rule = covert_warfare_enabled", gate)
        self.assertIn("has_journal_entry = je_covert_warfare", gate)
        unlock = _braced(sguis, r"^te_military_covert_tab_unlock_sgui = \{")
        self.assertIn("is_shown = { has_game_rule = covert_warfare_enabled }", unlock)
        self.assertIn("is_valid = { covert_warfare_entry_unlocked = yes }", unlock)
        # The entry is shown on the same rule.
        self.assertIn("has_game_rule = covert_warfare_enabled", _braced(_read(JE), r"is_shown_when_inactive = \{"))

    def test_the_checklist_is_the_entrys_own_possible_in_one_line(self):
        trig = _braced(_read(TRIGGERS), r"^covert_warfare_entry_unlocked = \{")
        tooltip = _braced(trig, r"custom_tooltip = \{")
        self.assertEqual(_words(trig), f"custom_tooltip = {{ {_words(tooltip)} }}")
        m = re.match(r"text = (\w+) (.*)", _words(tooltip))
        self.assertEqual(m.group(1), "covert_warfare_unlock_tt")
        # A verbatim copy of the entry's `possible`, which is left as it is.
        self.assertEqual(m.group(2), _words(_braced(_read(JE), r"^\tpossible = \{")))
        line = _loc()["covert_warfare_unlock_tt"]
        for part in ("concept_operation_slots", "concept_great_power", "concept_major_power", "4", "3", "2"):
            self.assertIn(part, line)

    def test_one_visible_per_widget(self):
        for i, block in enumerate(self.blocks):
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
