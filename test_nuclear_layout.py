"""The Nuclear Weapons panel's section order, collapse defaults, state gates and
overview (docs/guides/gui_style_guide.md; nuclear_layout_widget.gui)."""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(REPO, "gui", "journal_entry_widgets")
LAYOUT = os.path.join(W, "nuclear_layout_widget.gui")
OVERVIEW = os.path.join(W, "nuclear_overview_widget.gui")
PROGRAM = os.path.join(W, "nuclear_program_widget.gui")
DETERRENCE = os.path.join(W, "nuclear_deterrence_widget.gui")
NUCLEAR_GUI = [LAYOUT, OVERVIEW, PROGRAM, DETERRENCE]
JE = os.path.join(REPO, "common", "journal_entries", "je_nuclear_program.txt")
ICON_DOC = os.path.join(REPO, "docs", "systems", "nuclear_gui_icons.md")
LOC_DIR = os.path.join(REPO, "localization", "english")

STATUS = ["te_nuclear_sec_crisis", "te_nuclear_sec_posture", "te_nuclear_sec_forces",
          "te_nuclear_sec_home", "te_nuclear_sec_reputation", "te_nuclear_sec_taboo",
          "te_nuclear_sec_delivery", "te_nuclear_sec_powers"]
REFERENCE = ["te_nuclear_sec_how"]
# (root name, container, the one type it wraps), in the entry's declaration order.
ROOTS = [("widget_je_nuclear_overview", "custom_widget_container_1", "te_nuclear_overview_panel"),
         ("widget_je_nuclear_programme", "custom_widget_container_3", "te_nuclear_sec_programme"),
         ("widget_je_nuclear_status", "custom_widget_container_4", "te_nuclear_status_sections"),
         ("widget_je_nuclear_reference", "custom_widget_container_4", "te_nuclear_reference_sections")]
OLD_FLAGS = ["nuclear_program_powers", "nuclear_program_odds", "nd_capabilities_open", "nd_home_open",
             "nd_reputation_open", "nuclear_program_powers_open", "nd_taboo_hist_open"]
OLD_ROOTS = ["widget_je_nuclear_posture", "widget_je_nuclear_crisis", "widget_je_nuclear_balance"]


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


def _root_visible(body):
    """The section type's own `visible` (two tabs deep), or None."""
    m = re.search(r'^\t\tvisible = "\[(.*)\]"$', body, re.M)
    return m.group(1) if m else None


def _loc(key):
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        m = re.search(rf'^ {key}:\d* "(.*)"\s*$', _read(path), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


def _sgui(name):
    return f"GetScriptedGui('{name}').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )"


ALL_GUI = "\n".join(_read(p) for p in NUCLEAR_GUI)


class OrderTest(unittest.TestCase):
    def test_status_and_reference_order(self):
        layout = _read(LAYOUT)
        for composer, expected in (("te_nuclear_status_sections", STATUS),
                                   ("te_nuclear_reference_sections", REFERENCE)):
            body = _type_body(layout, composer)
            found = re.findall(r"^\t\t(te_nuclear_sec_\w+) = \{", body, re.M)
            self.assertEqual(found, expected, composer)
            self.assertIn('visible = "[JournalEntry.IsActive]"', body, composer)

    def test_every_section_is_a_type(self):
        for sec in STATUS + REFERENCE + ["te_nuclear_sec_programme"]:
            self.assertEqual(len(re.findall(rf"type {sec} = flowcontainer \{{", ALL_GUI)), 1, sec)

    def test_the_entry_attaches_the_layout_roots_in_order(self):
        je = _read(JE)
        found = re.findall(r'widget = \{\s*gui = "gui/journal_entry_widgets/(\w+\.gui)"\s*'
                           r'name = "(\w+)"\s*container = "(\w+)"', je)
        self.assertEqual(found, [("nuclear_layout_widget.gui", n, c) for n, c, _ in ROOTS])
        for old in OLD_ROOTS:
            self.assertNotIn(old, je)
            self.assertNotIn(old, ALL_GUI)

    def test_each_root_is_a_gated_wrapper(self):
        layout = _read(LAYOUT)
        for name, _, wrapped in ROOTS:
            m = re.search(rf'^flowcontainer = \{{\n\tname = "{name}"\n(.*?)^\}}', layout, re.S | re.M)
            self.assertTrue(m, name)
            body = m.group(1)
            visible = re.findall(r'^\tvisible = "\[(.*)\]"$', body, re.M)
            self.assertEqual(len(visible), 1, name)
            self.assertTrue(visible[0] == "JournalEntry.IsActive"
                            or visible[0].startswith("And( JournalEntry.IsActive, "), name)
            self.assertEqual(re.findall(r"^\t(\w+) = \{\}?$", body, re.M), [wrapped], name)

    def test_roots_are_a_section_wide(self):
        """A wrapper sized by its one child was centred by the width it had at its
        first layout; the programme drew half off the column (play-test 2026-09-29)."""
        layout = _read(LAYOUT)
        for name, _, _ in ROOTS:
            body = re.search(rf'^flowcontainer = \{{\n\tname = "{name}"\n(.*?)^\}}', layout, re.S | re.M).group(1)
            self.assertIn("\tdirection = vertical\n", body, name)
            self.assertIn("\tminimumsize = { 520 -1 }\n", body, name)

    def test_the_programme_root_carries_its_gate(self):
        """As on main: the root is laid out only once the section has something in it."""
        layout = _read(LAYOUT)
        body = re.search(r'^flowcontainer = \{\n\tname = "widget_je_nuclear_programme"\n(.*?)^\}', layout, re.S | re.M).group(1)
        self.assertIn(_sgui("nuclear_program_has_programme_sgui"), body)


class GateTest(unittest.TestCase):
    """Sections that only matter in one state are shown only in that state (rule 7)."""

    GATES = {
        "te_nuclear_sec_programme": [_sgui("nuclear_program_has_programme_sgui")],
        "te_nuclear_sec_crisis": [_sgui("nd_in_crisis_sgui")],
        "te_nuclear_sec_posture": [_sgui("nd_armed_sgui")],
        "te_nuclear_sec_forces": [_sgui("nd_armed_sgui")],
        "te_nuclear_sec_home": [_sgui("nd_armed_sgui")],
        "te_nuclear_sec_reputation": [_sgui("nd_has_reputation_sgui"), _sgui("nd_last_crisis_sgui")],
        "te_nuclear_sec_taboo": [_sgui("nd_taboo_exists_sgui")],
        "te_nuclear_sec_powers": [_sgui("nd_taboo_exists_sgui")],
        "te_nuclear_sec_delivery": None,
        "te_nuclear_sec_how": None,
    }

    def test_state_gated_sections_are_gated_on_their_root(self):
        for sec, gates in self.GATES.items():
            body = _type_body(ALL_GUI, sec)
            visible = _root_visible(body)
            if gates is None:
                self.assertIsNone(visible, f"{sec} is always shown")
                continue
            self.assertTrue(visible, f"{sec} has no gate")
            for gate in gates:
                self.assertIn(gate, visible, sec)
            self.assertNotIn("GetVariableSystem", visible, f"{sec}: the collapse flag belongs on the panel")

    def test_reputation_parts_are_gated_separately(self):
        body = _type_body(ALL_GUI, "te_nuclear_sec_reputation")
        last = body.index("nd_last_crisis_sgui')]")      # the last-crisis line's datacontext
        cred = body.index('text = "nd_w_credibility_label"')
        self.assertIn(f'visible = "[{_sgui("nd_last_crisis_sgui")}]"', body[:last])
        between = body[last:cred]
        self.assertIn(f'visible = "[{_sgui("nd_has_reputation_sgui")}]"', between)

    def test_one_visible_per_widget(self):
        """Gotcha #17: two `visible` lines on one widget is a bug."""
        for path in NUCLEAR_GUI:
            lines = _read(path).split("\n")
            for i, ln in enumerate(lines):
                if not ln.rstrip().endswith("{"):
                    continue
                depth = len(ln) - len(ln.lstrip("\t"))
                seen = 0
                for nxt in lines[i + 1:]:
                    d = len(nxt) - len(nxt.lstrip("\t"))
                    if nxt.strip() and d <= depth:
                        break
                    if d == depth + 1 and nxt.strip().startswith("visible = "):
                        seen += 1
                self.assertLessEqual(seen, 1, f"{os.path.basename(path)}:{i + 1}")


class FlagTest(unittest.TestCase):
    def test_section_flags_say_their_default(self):
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", ALL_GUI))
        self.assertTrue(flags)
        for f in flags:
            self.assertRegex(f, r"_(open|closed)$", f"section flag {f} does not say its default")
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", ALL_GUI))
            total = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", ALL_GUI))
            bare = total - negated
            if f.endswith("_closed"):   # shown unless closed: one bare (show-more), the rest negated
                self.assertEqual(bare, 1, f)
                self.assertGreaterEqual(negated, 2, f)
            else:                        # shown only when opened: one negated (show-more)
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 2, f)

    def test_live_sections_open_reference_collapsed(self):
        opened = {"te_nuclear_sec_programme": "nuclear_program_programme_closed",
                  "te_nuclear_sec_crisis": "nd_crisis_closed",
                  "te_nuclear_sec_posture": "nd_posture_closed",
                  "te_nuclear_sec_forces": "nd_capabilities_closed",
                  "te_nuclear_sec_home": "nd_home_closed",
                  "te_nuclear_sec_reputation": "nd_reputation_closed",
                  "te_nuclear_sec_taboo": "nd_taboo_panel_closed",
                  "te_nuclear_sec_delivery": "nuclear_program_odds_closed",
                  "te_nuclear_sec_powers": "nuclear_program_powers_closed",
                  "te_nuclear_sec_how": "nuclear_how_open"}
        for sec, flag in opened.items():
            body = _type_body(ALL_GUI, sec)
            toggles = re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", body)
            self.assertEqual(toggles[0], flag, sec)

    def test_subsections_are_nested(self):
        """The choices start collapsed; the taboo's chart is open (owner, 2026-09-29:
        history charts open by default)."""
        for sec, flags in (("te_nuclear_sec_posture", ["nd_doctrine_open", "nd_forces_open"]),
                           ("te_nuclear_sec_taboo", ["nd_taboo_hist_closed"])):
            body = _type_body(ALL_GUI, sec)
            for f in flags:
                self.assertIn(f"GetVariableSystem.Toggle('{f}')", body, f)
                i = body.index(f"GetVariableSystem.Toggle('{f}')")
                header = body.rfind("_header = {", 0, i)
                self.assertEqual(body[header - len("nd_subsection"):header], "nd_subsection",
                                 f"{f} is not a nested subsection")

    def test_no_old_flag_survives(self):
        for f in OLD_FLAGS:
            self.assertNotRegex(ALL_GUI, rf"'{f}'", f)


# Explanations that live in "How Nuclear Weapons Work", and the live sections they left.
HOW_KEYS = ["nd_w_home_legend", "nd_w_reputation_legend", "nd_w_crisis_actions_legend",
            "je_nuclear_program_widget_odds_note", "je_nuclear_program_widget_powers_legend",
            "je_nuclear_how_programme", "je_nuclear_how_posture", "je_nuclear_how_taboo"]


class HowItWorksTest(unittest.TestCase):
    def test_explanations_live_in_how_it_works(self):
        how = _type_body(_read(LAYOUT), "te_nuclear_sec_how")
        for key in HOW_KEYS:
            self.assertIn(f'"{key}"', how, key)
        self.assertEqual(how.count("nd_subheader = {"), how.count("nd_note = {"))

    def test_live_sections_carry_no_explanations(self):
        for sec in STATUS + ["te_nuclear_sec_programme"]:
            body = _type_body(ALL_GUI, sec)
            for key in HOW_KEYS:
                self.assertNotIn(f'"{key}"', body, f"{sec} still explains ({key})")

    def test_the_first_heading_has_no_top_margin(self):
        how = _type_body(_read(LAYOUT), "te_nuclear_sec_how")
        first = how[how.index("nd_subheader = {"):]
        first = first[:first.index("nd_note = {")]
        self.assertIn('blockoverride "subheader_margin" {}', first)


class OverviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ov = _read(OVERVIEW)

    def _coded(self, value):
        """{code: [textures]} for the icons gated on ScriptValue(value) == code."""
        found = {}
        pat = (rf"visible = \"\[EqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('{value}'\), "
               rf"'\(CFixedPoint\)(-?\d+)' \)\]\"(.*?)texture = \"([^\"]+)\"")
        for m in re.finditer(pat, self.ov, re.S):
            found.setdefault(int(m.group(1)), []).append(m.group(3))
        return found

    def test_every_state_has_one_icon(self):
        for value, codes in (("nuclear_program_display_state", range(0, 9)),
                             ("nd_display_doctrine_code", range(1, 6)),
                             ("nd_display_readiness_code", range(0, 4)),
                             ("nd_display_authority_code", range(1, 5)),
                             ("nd_disp_taboo_trend", range(-1, 2))):
            with self.subTest(value=value):
                found = self._coded(value)
                self.assertEqual(sorted(found), list(codes))
                for code, textures in found.items():
                    self.assertEqual(len(textures), 1, f"{value} {code}")

    def test_the_rows_are_gated(self):
        body = _type_body(self.ov, "te_nuclear_overview_panel")
        self.assertIn('visible = "[JournalEntry.IsActive]"', body)
        posture = body.index("nd_display_doctrine_code")
        self.assertIn(_sgui("nd_armed_sgui"), body[:posture])
        taboo = body.index("ScriptValue('nd_disp_taboo')")
        self.assertIn(_sgui("nd_taboo_exists_sgui"), body[posture:taboo])
        crisis = body.index('text = "je_nuclear_ov_crisis_label"')
        self.assertIn(_sgui("nd_in_crisis_sgui"), body[crisis - 900:crisis])
        cred = body.index('text = "je_nuclear_ov_credibility_label"')
        self.assertIn(_sgui("nd_has_reputation_sgui"), body[cred - 900:cred])

    def test_the_taboo_bar_marks_its_target(self):
        body = _type_body(self.ov, "te_nuclear_overview_panel")
        taboo = body[body.index("ScriptValue('nd_disp_taboo')"):]
        self.assertIn("ScriptValue('nd_disp_taboo_target')", taboo[:taboo.index("progressbar_marker.dds")])
        value = _loc("je_nuclear_ov_taboo_value")
        for sv in ("nd_disp_taboo", "nd_disp_taboo_target", "nd_disp_taboo_step"):
            self.assertIn(f"ScriptValue('{sv}')", value, sv)
        self.assertIn("/mo)", value)

    def test_survivability_is_a_bar_marking_its_ceiling(self):
        body = _type_body(ALL_GUI, "te_nuclear_sec_forces")
        row = body[body.index('tooltip = "nd_w_survivability_tt"'):]
        row = row[:row.index('text = "nd_w_survivability_value"')]
        self.assertIn("ScriptValue('nd_display_survivability')", row)
        cap = row.index("ScriptValue('nd_display_survivability_cap')")
        self.assertLess(cap, row.index("progressbar_marker.dds"))

    def test_every_row_fits_the_column(self):
        """The overview is a section's width: a fixed 480 column in a frame with
        20 px margins, and no row wider than the column (play-test 2026-09-29)."""
        frame = _type_body(self.ov, "te_nuclear_ov_frame")
        self.assertIn("margin = { 20 8 }", frame)
        panel = _type_body(self.ov, "te_nuclear_overview_panel")
        self.assertIn("minimumsize = { 480 -1 }", panel)

        def width(type_name):
            return int(re.search(r"\n\t\tsize = \{ (\d+) \d+ \}", _type_body(self.ov, type_name)).group(1))
        self.assertLessEqual(4 * width("te_nuclear_ov_icon_label") + 3 * 6, 480)
        self.assertLessEqual(3 * width("te_nuclear_ov_posture_cell") + 2 * 6, 480)
        row3 = panel[panel.index("Row 3"):]
        cells = [int(w) for w in re.findall(r"maximumsize = \{ (\d+) -1 \}", row3)]
        bar = int(re.search(r"default_progressbar_horizontal = \{\s*size = \{ (\d+) \d+ \}", row3).group(1))
        self.assertEqual(len(cells), 2)
        self.assertLessEqual(sum(cells) + bar + 24 + 3 * 8, 480)

    def test_cells_have_a_fixed_width(self):
        for t in ("te_nuclear_ov_icon_label", "te_nuclear_ov_posture_cell"):
            body = _type_body(self.ov, t)
            self.assertRegex(body, r"\n\t\tsize = \{ \d+ \d+ \}\n", t)
            self.assertIn("max_width = ", body, t)

    def test_every_placeholder_is_listed(self):
        doc = _read(ICON_DOC)
        textures = set(re.findall(r'texture = "([^"]+)"', self.ov))
        textures -= {"gfx/interface/icons/generic_icons/transparent.dds",
                     "gfx/interface/progressbar/progressbar_marker.dds",
                     "gfx/interface/icons/generic_icons/trend_up.dds",
                     "gfx/interface/icons/generic_icons/trend_down.dds",
                     "gfx/interface/icons/generic_icons/trend_nochange.dds"}
        self.assertTrue(textures)
        for t in textures:
            self.assertIn(f"`{t}`", doc, f"placeholder {t} is not in nuclear_gui_icons.md")


VALUES = os.path.join(REPO, "common", "script_values")


def _value_body(name):
    for path in glob.glob(os.path.join(VALUES, "*.txt")):
        text = _read(path)
        m = re.search(rf"^{name} = \{{", text, re.M)
        if m:
            return _type_body_generic(text, m.end() - 1)
    raise AssertionError(f"no script value {name}")


def _type_body_generic(text, start):
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:j]


class DisplayValueTest(unittest.TestCase):
    """Display-only values: every variable read guarded; fallbacks agree with the words."""

    def test_reads_are_guarded(self):
        for name in ("nuclear_program_display_state", "nd_display_doctrine_code",
                     "nd_display_readiness_code", "nd_display_authority_code"):
            body = _value_body(name)
            for var in re.findall(r"var:(\w+)", body):
                self.assertIn(f"has_variable = {var}", body, f"{name} reads {var} unguarded")
        for name in ("nd_disp_taboo_step", "nd_disp_taboo_trend"):
            self.assertNotIn("global_var:", _value_body(name), name)

    def test_posture_fallbacks_match_the_name_blocks(self):
        custom = _read(os.path.join(REPO, "common", "customizable_localization",
                                    "nuclear_deterrence_custom_loc.txt"))
        for value, block, key in (("nd_display_doctrine_code", "nd_doctrine_name", "nd_doctrine_"),
                                  ("nd_display_readiness_code", "nd_readiness_name", "nd_readiness_"),
                                  ("nd_display_authority_code", "nd_authority_name", "nd_authority_")):
            m = re.search(rf"^{block} = \{{", custom, re.M)
            body = _type_body_generic(custom, m.end() - 1)
            fallback = re.search(r"trigger = \{ always = yes \}\s*localization_key = (\w+)", body).group(1)
            default = re.search(r"^\tvalue = (\d+)$", _value_body(value), re.M).group(1)
            self.assertEqual(fallback, f"{key}{default}", value)

    def test_programme_state_covers_the_status_line(self):
        body = _value_body("nuclear_program_display_state")
        order = [body.index(s) for s in ("var:nuclear_program_last_status", "nuclear_program_has_programme = no",
                                          "modifier:country_nuclear_disarmament_bool", "nd_taboo_renounced")]
        self.assertEqual(order, sorted(order), "later ifs must be the status line's earlier branches")
        for code in range(9):
            self.assertTrue(_loc(f"je_nuclear_ov_prog_{code}"))


class StatusDescTest(unittest.TestCase):
    """Status text that repeats the overview goes (owner, 2026-09-29): the
    entry's status line is drawn only for an inactive entry, which has no
    overview."""

    def test_the_status_line_is_for_an_inactive_entry_only(self):
        je = _read(JE)
        m = re.search(r"^\tstatus_desc = \{(.*?)^\t\}", je, re.S | re.M)
        self.assertTrue(m, "status_desc is not a block")
        branches = re.findall(r"desc = (\w+)\s*trigger = \{ (.*?) \}", m.group(1))
        self.assertEqual(branches, [("nuke_line_empty", "has_journal_entry = je_nuclear_program"),
                                    ("je_nuclear_program_status_line", "always = yes")])
        self.assertIn("first_valid = {", m.group(1))
        self.assertEqual(_loc("nuke_line_empty"), "")


class TidinessTest(unittest.TestCase):
    NEW_KEYS = ["je_nuclear_ov_prog_tt", "je_nuclear_ov_warheads_tt", "je_nuclear_ov_crisis_tt",
                "je_nuclear_how_programme", "je_nuclear_how_posture", "je_nuclear_how_taboo",
                "nd_w_crisis_actions_legend"]

    def test_no_tooltip_or_note_starts_or_ends_with_a_line_break(self):
        for key in self.NEW_KEYS:
            value = _loc(key)
            self.assertFalse(value.startswith("\\n") or value.endswith("\\n"), key)

    def test_the_moves_have_a_heading_not_a_note(self):
        body = _type_body(ALL_GUI, "te_nuclear_sec_crisis")
        head = body.index('text = "nd_w_crisis_moves_sub"')
        self.assertLess(head, body.index('text = "nd_w_crisis_act_public"'))


if __name__ == "__main__":
    unittest.main()
