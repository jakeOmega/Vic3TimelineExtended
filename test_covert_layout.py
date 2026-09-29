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

STATUS = ["te_covert_sec_operations", "te_covert_sec_networks", "te_covert_sec_funding",
          "te_covert_sec_detection", "te_covert_sec_counterintel"]
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
OTHER_ICONS = {
    "funding_dormant": GENERIC + "warning.dds",
    "funding": GENERIC + "gdp.dds",
    "tradecraft": "gfx/interface/icons/formation_order_icons/upgrade.dds",
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
                                 "covert_detection_closed", "covert_counterintel_closed", "covert_how_open"})
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
        net = _type_body(self.text, "widget_je_covert_network_row")
        self.assertIn("visible = \"[And( ScriptContainer.HasVariable('iw_net_intel_tier'), NotEqualTo_CFixedPoint( ScriptContainer.GetVariableValue('iw_net_intel_tier'), '(CFixedPoint)2' ) )]\"", net)

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

    def test_row_tooltips_need_no_journal_entry(self):
        # A tooltip inside a datamodel item renders with the item's
        # ScriptContainer only (gui_modding_guide.md gotcha #24).
        loc = _loc()
        for key in ("je_iw_op_row_phase_prep_tt", "je_iw_op_row_phase_est_tt", "je_iw_op_row_phase_full_tt",
                    "je_iw_op_row_detection_tt", "je_iw_net_row_trend_growing", "je_iw_net_row_trend_decaying",
                    "je_iw_net_row_trend_holding", "je_iw_net_row_intel_service_tooltip",
                    "je_iw_net_row_intel_ops_tooltip"):
            self.assertNotIn("JournalEntry", loc[key], key)


def _git_files():
    import subprocess
    out = subprocess.run(["git", "ls-files", "gfx/interface/icons/diplomatic_action_icons"], cwd=REPO,
                         capture_output=True, text=True).stdout
    return out.split("\n")


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
        keys |= {f"je_iw_ladder_row_{n}{s}" for n in range(6) for s in ("", "_current")}
        keys |= {"concept_tradecraft_desc", "concept_agent_network_desc", "concept_covert_funding_desc",
                 "concept_operation_slots_desc"}
        for key in keys:
            value = self.loc[key]
            self.assertFalse(value.startswith("\\n") or value.endswith("\\n"), key)
            self.assertFalse(value.startswith(" "), key)

    def test_new_terms_are_concepts(self):
        concepts = _read(CONCEPTS)
        for c in ("concept_tradecraft", "concept_agent_network", "concept_covert_funding", "concept_operation_slots"):
            self.assertRegex(concepts, rf"(?m)^{c} = \{{\}}", c)
            self.assertIn(f"{c}_desc", self.loc, c)
        self.assertIn("concept_tradecraft", self.loc["je_iw_tradecraft_header"])
        self.assertIn("concept_operation_slots", self.loc["je_iw_slots_detail"])

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
        # Nothing in script reads them; the panels and their loc do.
        text = _read(GUI) + "".join(_loc().values())
        for name in self.blocks:
            self.assertIn(f"'{name}'", text, name)

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
        for path in list(STANDING_ICONS.values()) + list(OTHER_ICONS.values()):
            self.assertIn(f"`{path}`", doc, path)

    def test_the_overview_uses_only_listed_textures(self):
        gui = _read(GUI)
        used = set(re.findall(r'texture = "([^"]+)"', _type_body(gui, "te_covert_overview_panel")))
        used |= set(re.findall(r'texture = "([^"]+)"', _type_body(gui, "covert_ov_slot")))
        known = set(STANDING_ICONS.values()) | set(OTHER_ICONS.values()) | NOT_PLACEHOLDERS
        self.assertEqual(used - known, set())


if __name__ == "__main__":
    unittest.main()
