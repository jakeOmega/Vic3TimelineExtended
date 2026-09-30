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


def _coded(text, value):
    """{code: [textures]} for the icons gated on ScriptValue(value) == code."""
    found = {}
    pat = (rf"visible = \"\[EqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('{value}'\), "
           rf"'\(CFixedPoint\)(-?\d+)' \)\]\"(.*?)texture = \"([^\"]+)\"")
    for m in re.finditer(pat, text, re.S):
        found.setdefault(int(m.group(1)), []).append(m.group(3))
    return found


class OverviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ov = _read(OVERVIEW)

    def test_every_state_has_one_icon(self):
        for value, codes in (("nuclear_program_display_state", range(0, 9)),
                             ("nd_display_doctrine_code", range(1, 6)),
                             ("nd_display_readiness_code", range(0, 4)),
                             ("nd_display_authority_code", range(1, 5)),
                             ("nd_disp_taboo_trend", range(-1, 2))):
            with self.subTest(value=value):
                found = _coded(self.ov, value)
                self.assertEqual(sorted(found), list(codes))
                for code, textures in found.items():
                    self.assertEqual(len(textures), 1, f"{value} {code}")

    def test_the_rows_are_gated(self):
        body = _type_body(self.ov, "te_nuclear_overview_panel")
        self.assertIn('visible = "[JournalEntry.IsActive]"', body)
        posture = body.index("nd_display_doctrine_code")
        self.assertIn(_sgui("nd_armed_sgui"), body[:posture])
        taboo = body.index("ScriptValue('nd_disp_taboo_bar_low')")
        self.assertIn(_sgui("nd_taboo_exists_sgui"), body[posture:taboo])
        crisis = body.index('text = "je_nuclear_ov_crisis_label"')
        self.assertIn(_sgui("nd_in_crisis_sgui"), body[crisis - 900:crisis])
        cred = body.index('text = "je_nuclear_ov_credibility_label"')
        self.assertIn(_sgui("nd_has_reputation_sgui"), body[cred - 900:cred])

    def _bar(self, text, start_key, end_key):
        """The fixed cell holding a projection bar: from its first layer to the next text."""
        i = text.index(start_key)
        return text[text.rfind("widget = {", 0, text.index("# 1. Background and frame.", i)):text.index(end_key, i)]

    def test_the_taboo_bar_projects_its_target(self):
        """Round 3 (owner, 2026-09-30): no eye marker. The shared projection bar:
        background, the change in the bar's own fill at 40% to the higher of
        score and target (neutral: the taboo is two-sided for the player), and
        the solid fill to the lower."""
        body = _type_body(self.ov, "te_nuclear_overview_panel")
        bar = self._bar(body, 'text = "je_nuclear_ov_taboo_label"', 'text = "je_nuclear_ov_taboo_value"')
        self.assertNotIn("progressbar_marker.dds", self.ov)
        layers = re.findall(r"^\t+(default_progressbar_horizontal|green_progressbar_horizontal|bad_progressbar_horizontal) = \{",
                            bar, re.M)
        self.assertEqual(layers, ["default_progressbar_horizontal"] * 3)
        self.assertIn("alpha = 0.4", bar)
        self.assertLess(bar.index("ScriptValue('nd_disp_taboo_bar_high')"), bar.index("ScriptValue('nd_disp_taboo_bar_low')"))
        values = _read(os.path.join(REPO, "common", "script_values", "nuclear_taboo_values.txt"))
        for name, op in (("nd_disp_taboo_bar_low", "<"), ("nd_disp_taboo_bar_high", ">")):
            self.assertIn(f"nd_disp_taboo_target {op} nd_taboo_value", _value_body(name), name)
        self.assertIn("nd_disp_taboo_bar_low", values)
        self.assertIn("two-sided", _loc("je_nuclear_ov_taboo_bar_tt"))
        value = _loc("je_nuclear_ov_taboo_value")
        for sv in ("nd_disp_taboo", "nd_disp_taboo_target", "nd_disp_taboo_step"):
            self.assertIn(f"ScriptValue('{sv}')", value, sv)
        self.assertIn("/mo)", value)

    def test_survivability_projects_green_up_and_red_down(self):
        """More survivability is always good for us: green while rising to where
        it is heading, red while falling (owner, 2026-09-30: red bad, green good);
        the ceiling a thin line with its own hover."""
        body = _type_body(ALL_GUI, "te_nuclear_sec_forces")
        bar = self._bar(body, 'text = "nd_w_survivability_label"', 'text = "nd_w_survivability_value"')
        self.assertNotIn("progressbar_marker.dds", body)
        cur = "JournalEntry.GetCountry.MakeScope.ScriptValue('nd_display_survivability')"
        head = "JournalEntry.GetCountry.MakeScope.ScriptValue('nd_display_survivability_heading')"
        green = bar[bar.index("green_progressbar_horizontal"):]
        red = bar[bar.index("bad_progressbar_horizontal"):]
        self.assertIn(f"GreaterThan_CFixedPoint( {head}, {cur} )", bar[:bar.index("green_progressbar_horizontal")])
        self.assertIn(f"GreaterThan_CFixedPoint( {cur}, {head} )",
                      bar[bar.index("green_progressbar_horizontal"):bar.index("bad_progressbar_horizontal")])
        self.assertIn("nd_display_survivability_bar_high", green[:300])
        self.assertIn("nd_display_survivability_bar_high", red[:300])
        self.assertIn("alpha = 0.5", bar)
        solid = bar[bar.index("# 4. Solid"):]
        self.assertIn("nd_display_survivability_bar_low", solid[:600])
        line = bar[bar.index("# 5."):]
        for needle in ("ScriptValue('nd_display_survivability_cap')", "size = { 3 24 }",
                       "gfx/interface/backgrounds/white.dds", 'tooltip = "nd_w_survivability_cap_tt"'):
            self.assertIn(needle, line, needle)
        heading = _value_body("nd_display_survivability_heading")
        for needle in ("value = nd_survivability_cap", "value = nd_survivability_floor", "var:nd_hardening >= 1"):
            self.assertIn(needle, heading, needle)
        self.assertIn("green", _loc("nd_w_survivability_bar_tt"))

    def test_every_row_fits_the_column(self):
        """The overview is a section's width: a fixed 480 column in a frame with
        20 px margins, and no row wider than the column (play-test 2026-09-29)."""
        frame = _type_body(self.ov, "te_nuclear_ov_frame")
        self.assertIn("margin = { 20 8 }", frame)
        panel = _type_body(self.ov, "te_nuclear_overview_panel")
        self.assertIn("minimumsize = { 480 -1 }", panel)

        def width(type_name):
            return int(re.search(r"\n\t\tsize = \{ (\d+) \d+ \}", _type_body(self.ov, type_name)).group(1))
        credibility = int(re.search(r"size = \{ (\d+) 58 \}\n\t+visible = \"\[GetScriptedGui\('nd_has_reputation_sgui'\)",
                                    panel).group(1))
        self.assertLessEqual(3 * width("te_nuclear_ov_icon_label") + credibility + 3 * 6, 480)
        self.assertLessEqual(3 * width("te_nuclear_ov_posture_cell") + 2 * 6, 480)
        row3 = panel[panel.index("Row 3"):]
        cells = [int(w) for w in re.findall(r"maximumsize = \{ (\d+) -1 \}", row3)]
        bar = int(re.search(r"widget = \{\s*size = \{ (\d+) 18 \}", row3).group(1))
        self.assertEqual(len(cells), 2)
        self.assertLessEqual(sum(cells) + bar + 24 + 3 * 8, 480)

    def test_cells_have_a_fixed_width(self):
        for t, bound in (("te_nuclear_ov_icon_label", "max_width = 112"),
                         ("te_nuclear_ov_posture_cell", "maximumsize = { 150 -1 }")):
            body = _type_body(self.ov, t)
            self.assertRegex(body, r"\n\t\tsize = \{ \d+ \d+ \}\n", t)
            self.assertIn(bound, body, t)


NUCLEAR_ICONS = "gfx/interface/icons/nuclear_icons/"
# The overview's own icons (PR #586), per display value, in code order.
CODED_ICONS = {
    "nuclear_program_display_state": {0: "programme_unfunded", 1: "programme_developing", 2: "programme_producing",
                                      3: "programme_frozen", 4: "programme_at_ceiling", 5: "programme_dismantling",
                                      6: "programme_none", 7: "programme_renounced", 8: "programme_disarmed"},
    "nd_display_doctrine_code": {1: "doctrine_nfu", 2: "doctrine_existential", 3: "doctrine_flexible",
                                 4: "doctrine_compellence", 5: "doctrine_warfighting"},
    "nd_display_readiness_code": {0: "readiness_recessed", 1: "readiness_routine", 2: "readiness_heightened",
                                  3: "readiness_high_alert"},
    "nd_display_authority_code": {1: "authority_central", 2: "authority_delegation", 3: "authority_on_warning",
                                  4: "authority_automatic"},
}
# Vanilla marks the overview uses as vanilla does: the taboo's trend arrows.
VANILLA_KEPT = {"gfx/interface/icons/generic_icons/trend_up.dds", "gfx/interface/icons/generic_icons/trend_down.dds",
                "gfx/interface/icons/generic_icons/trend_nochange.dds"}


def _all_icon_names():
    names = [n for codes in CODED_ICONS.values() for n in codes.values()]
    return names + ["warheads", "crisis"]


class NuclearIconsTest(unittest.TestCase):
    """The overview's own icons (PR #586) replace every placeholder (UnIconsTest's shape)."""

    @classmethod
    def setUpClass(cls):
        cls.ov = _read(OVERVIEW)

    def test_each_code_draws_its_own_icon(self):
        for value, names in CODED_ICONS.items():
            with self.subTest(value=value):
                self.assertEqual(_coded(self.ov, value),
                                 {code: [f"{NUCLEAR_ICONS}{n}.dds"] for code, n in names.items()})

    def test_warheads_and_crisis(self):
        for name, tooltip in (("warheads", "je_nuclear_ov_warheads_tt"), ("crisis", "je_nuclear_ov_crisis_tt")):
            with self.subTest(cell=name):
                m = re.search(rf'tooltip = "{tooltip}".*?texture = "([^"]+)"', self.ov, re.S)
                self.assertEqual(m.group(1), f"{NUCLEAR_ICONS}{name}.dds")

    def test_no_placeholder_left(self):
        for path in re.findall(r'texture = "(gfx/interface/[^"]+)"', self.ov):
            with self.subTest(path=path):
                self.assertTrue(path.startswith(NUCLEAR_ICONS) or path in VANILLA_KEPT, f"placeholder left: {path}")

    def test_no_icon_is_faded(self):
        # The placeholders faded No Programme and Disarmed to 30% to tell them from
        # Developing and Dismantling; the art draws those states itself.
        for body in re.findall(r'blockoverride "icon_texture" \{(.*?)\}', self.ov, re.S):
            self.assertNotIn("alpha", body)

    def test_every_icon_is_listed(self):
        doc = _read(ICON_DOC)
        for name in _all_icon_names():
            with self.subTest(icon=name):
                self.assertIn(f"`{name}.dds`", doc)

    def test_every_icon_is_in_the_repo(self):
        import subprocess
        out = subprocess.run(["git", "ls-files", NUCLEAR_ICONS], cwd=REPO, capture_output=True, text=True)
        tracked = set(out.stdout.split())
        if out.returncode != 0 or not tracked:
            self.skipTest(f"{NUCLEAR_ICONS} is not in this tree: the art lands with PR #586")
        for name in _all_icon_names():
            with self.subTest(icon=name):
                self.assertIn(f"{NUCLEAR_ICONS}{name}.dds", tracked)

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


# ---- Play-test round 3: nothing a player reads may end in "..." ------------------
# The coordinator's width budget, measured from the owner's screenshots in GUI
# units per character: the large font about 10, the medium table font about 8.6,
# plus 10%. The rules give no figure for fontsize_small; it is scaled from the
# medium one by the ratio measured on the owner's round-1 screenshot of this
# panel ("Central Authorization" at small and "Launch authority" at medium:
# 6.4 and 7.2 there), so 8.6 x 6.4 / 7.2 = 7.6.
LARGE, MEDIUM, SMALL, MARGIN = 10.0, 8.6, 7.6, 1.1
LONGEST_IG_NAME = "Petty Bourgeoisie"   # the longest vanilla interest-group name
# Numbers read as 999 unless their range is narrower (the widest they print).
WIDEST_NUMBER = {"nd_display_safeguards": "3", "nd_display_hardening": "3"}
CUSTOM_DIR = os.path.join(REPO, "common", "customizable_localization")


def _all_loc():
    loc = {}
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        for m in re.finditer(r'^ ([\w.\-]+):\d* "(.*)"\s*$', _read(path), re.M):
            loc[m.group(1)] = m.group(2)
    return loc


def _custom_blocks():
    blocks = {}
    for path in glob.glob(os.path.join(CUSTOM_DIR, "*.txt")):
        text = _read(path)
        for m in re.finditer(r"^(\w+) = \{", text, re.M):
            blocks[m.group(1)] = re.findall(r"localization_key = (\w+)", _type_body_generic(text, m.end() - 1))
    return blocks


LOC, CUSTOM = _all_loc(), _custom_blocks()


def _renderings(key, depth=0):
    """Every way a loc key can read: GetCustom blocks expanded to each target,
    a number as its widest likely form (999, or 99.9M for a |D money figure),
    an interest group's name as the longest one, a concept as its name, and the
    formatting codes and text icons stripped (an icon counts as one letter)."""
    value = LOC.get(key, key)
    outs = [""]
    for part in re.split(r"(\[[^\]]*\])", value):
        if not part.startswith("["):
            options = [part]
        elif "GetCustom(" in part and depth < 3:
            name = re.search(r"GetCustom\('(\w+)'\)", part).group(1)
            options = [r for k in CUSTOM.get(name, []) for r in _renderings(k, depth + 1)] or [""]
        elif "Concept(" in part:
            options = [re.search(r"Concept\('\w+',\s*'([^']*)'\)", part).group(1)]
        elif re.search(r"\[concept_\w+\]", part):
            name = part[1:-1]
            options = [LOC.get(name, name)]
        elif "GetName" in part:
            options = [LONGEST_IG_NAME]
        else:
            sv = re.search(r"ScriptValue\('(\w+)'\)", part)
            if sv and sv.group(1) in WIDEST_NUMBER:
                options = [WIDEST_NUMBER[sv.group(1)]]
            else:
                options = ["99.9M" if re.search(r"\|[^\]]*D", part) else "999"]
        outs = [o + x for o in outs for x in options]
    cleaned = []
    for o in outs:
        o = re.sub(r"#[A-Za-z_]+(;\S*)? ?", "", o).replace("#!", "")
        o = re.sub(r"@\w+!", "X", o).replace("\\n", " ")
        cleaned.append(o.strip())
    return cleaned


def _wraps_into(text, width, per_char, lines):
    """Greedy word wrap: every word fits the width, in at most `lines` lines."""
    words, used, n = text.split(), 0.0, 1
    for w in words:
        w_len = len(w) * per_char
        if w_len > width:
            return False
        extra = w_len if used == 0 else w_len + per_char
        if used + extra > width:
            n, used = n + 1, w_len
        else:
            used += extra
    return n <= lines


class LabelBudgetTest(unittest.TestCase):
    """Every static label, and every dynamic word, in a fixed-width cell fits it."""

    def _fits(self, keys, width, font, where):
        self.assertTrue(keys, where)
        for key in keys:
            for text in _renderings(key):
                need = len(text) * font * MARGIN
                self.assertLessEqual(need, width, f"{where}: {key} reads {text!r} ({need:.0f} > {width})")

    def _gui_keys(self, text, block_name):
        return set(re.findall(rf'blockoverride "{block_name}" \{{\s*text = "(\w+)"', text))

    def test_table_rows(self):
        det, prog = _read(DETERRENCE), _read(PROGRAM)
        for path, type_name, label_w, value_w in ((det, "nd_row", 210, 266), (prog, "nuclear_program_row", 200, 276)):
            body = _type_body(path, type_name)
            self.assertEqual([int(w) for w in re.findall(r"size = \{ (\d+) 24 \}", body)], [label_w, value_w])
            self._fits(self._gui_keys(path, "row_label"), label_w, MEDIUM, f"{type_name} label")
            self._fits(self._gui_keys(path, "row_value"), value_w, MEDIUM, f"{type_name} value")

    def test_steppers_choices_and_buttons(self):
        both = _read(DETERRENCE) + _read(PROGRAM)
        labels = set(re.findall(r'text = "(\w+)"\n\t+size = \{ 170 24 \}', both))
        values = set(re.findall(r'text = "(\w+)"\n\t+tooltip = "\w+"\n\t+size = \{ 246 24 \}', both))
        self.assertEqual(len(labels), 4, labels)
        self.assertEqual(len(values), 4, values)
        self._fits(labels, 170, MEDIUM, "stepper label")
        self._fits(values, 246, MEDIUM, "stepper value")
        choices = set(re.findall(r'size = \{ 360 30 \}[^}]*?text = "(\w+)"', both, re.S))
        buttons = set(re.findall(r'size = \{ 110 30 \}[^}]*?text = "(\w+)"', both, re.S))
        self._fits(choices, 360, MEDIUM, "choice")
        self._fits(buttons, 110, MEDIUM, "button")

    def test_overview(self):
        ov = _read(OVERVIEW)
        self.assertIn("size = { 112 58 }", _type_body(ov, "te_nuclear_ov_icon_label"))
        row1 = [f"je_nuclear_ov_prog_{n}" for n in range(9)] + ["je_nuclear_ov_warheads_label",
                                                                 "je_nuclear_ov_crisis_label"]
        self._fits(row1, 112, SMALL, "overview row 1")
        self.assertIn("size = { 126 58 }", ov)
        self._fits(["je_nuclear_ov_credibility_label"], 126, SMALL, "credibility meter")
        self._fits(["je_nuclear_ov_taboo_label"], 60, MEDIUM, "taboo label")
        self._fits(["je_nuclear_ov_taboo_value"], 190, MEDIUM, "taboo headline")
        # The posture's names may wrap: each word fits, in at most two lines.
        cell = _type_body(ov, "te_nuclear_ov_posture_cell")
        self.assertIn("multiline = yes", cell)
        self.assertIn("maximumsize = { 150 -1 }", cell)
        names = ([f"nd_doctrine_{n}" for n in range(1, 6)] + [f"nd_readiness_{n}" for n in range(4)]
                 + [f"nd_authority_{n}" for n in range(1, 5)])
        for key in names:
            for text in _renderings(key):
                self.assertTrue(_wraps_into(text, 150, SMALL * MARGIN, 2), f"{key} {text!r}")

    def test_forces_and_at_home(self):
        det = _read(DETERRENCE)
        self._fits(["nd_w_survivability_label"], 170, MEDIUM, "survivability label")
        self._fits(["nd_w_survivability_value"], 94, MEDIUM, "survivability value")
        self._fits(["nd_home_ig_name"], 280, MEDIUM, "At Home group")
        self._fits([f"nd_home_view_{n}" for n in range(1, 11)], 200, MEDIUM, "At Home class")
        table = _type_body(det, "nd_home_term_row")
        self.assertEqual([int(w) for w in re.findall(r"size = \{ (\d+) 22 \}", table)], [220, 60])
        terms = ("approval", "doctrine", "readiness", "authority", "strain", "possession", "business")
        self._fits([f"nd_home_row_{t}" for t in terms], 220, MEDIUM, "At Home row")
        self._fits([f"nd_home_row_{t}_value" for t in terms], 60, MEDIUM, "At Home value")


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



MILITARY = os.path.join(REPO, "gui", "panel_military.gui")
TAB_SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")
TAB_WIDGETS = os.path.join(REPO, "gui", "te_system_tab_widgets.gui")
NUKE_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "nuke_triggers.txt")
TAB_GATE = "GetScriptedGui('te_military_nuclear_tab_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"
TAB_UNLOCK = "GetScriptedGui('te_military_nuclear_tab_unlock_sgui')"


def _mod_blocks(text, tag="### MOD: Nuclear tab (te_nuclear) ###"):
    """Each marked block of panel_military.gui, up to its END MOD line."""
    out = []
    start = text.find(tag)
    while start != -1:
        end = text.index("### END MOD ###", start)
        out.append(text[start:end])
        start = text.find(tag, end)
    return out


def _txt_block(text, name):
    m = re.search(rf"^{name} = \{{", text, re.M)
    assert m, f"no {name}"
    depth = 0
    for j in range(m.end() - 1, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():j]


class MilitaryTabTest(unittest.TestCase):
    """The Military panel's Nuclear tab (style guide rule 9): the journal entry's
    own composers under GetPlayerJournalEntry, gated, greyed until the entry
    runs, and ending with Open Journal Entry."""

    @classmethod
    def setUpClass(cls):
        cls.military = _read(MILITARY)
        cls.blocks = _mod_blocks(cls.military)

    def _content(self):
        body = self.blocks[1]
        self.assertIn('name = "te_military_nuclear_tab"', body)
        return body

    def test_two_marked_blocks_the_button_and_the_content(self):
        self.assertEqual(len(self.blocks), 2)
        self.assertIn('blockoverride "fourth_button"', self.blocks[0])
        self.assertIn("visible = \"[InformationPanel.IsTabSelected('te_nuclear')]\"", self._content())

    def test_the_tab_composes_the_journal_roots_types_in_order(self):
        body = self._content()
        found = re.findall(r"^\t+(te_\w+) = \{\}", body, re.M)
        roots = [wrapped for _, _, wrapped in ROOTS]
        # The journal's roots, with the entry's own bar under The Programme, as in the journal.
        self.assertEqual(found, roots[:2] + ["te_je_goal_bar"] + roots[2:])
        # The link back to the entry comes after every section.
        self.assertGreater(body.index('text = "te_system_tab_open_journal"'), body.index("te_nuclear_reference_sections"))
        self.assertIn("onclick = \"[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]\"", body)

    def test_the_gate_sits_above_the_journal_entry_datacontext(self):
        body = self._content()
        dc = body.index("datacontext = \"[GetPlayerJournalEntry('je_nuclear_program')]\"")
        self.assertLess(body.index(f'visible = "[{TAB_GATE}]"'), dc)
        # Never on the widget that carries the datacontext itself.
        opener = body.rindex("flowcontainer = {", 0, dc)
        self.assertNotIn("visible", body[opener:dc])

    def test_the_column_is_as_wide_as_the_journal_roots(self):
        body = self._content()
        dc = body.index("GetPlayerJournalEntry('je_nuclear_program')")
        self.assertIn("minimumsize = { 520 -1 }", body[dc:body.index("te_nuclear_overview_panel", dc)])
        self.assertIn("parentanchor = hcenter", body[dc:body.index("te_nuclear_overview_panel", dc)])

    def test_the_bar_shows_with_a_programme_only(self):
        body = self._content()
        bar = body.index("te_je_goal_bar = {}")
        wrapper = body[body.rindex("flowcontainer = {", 0, bar):bar]
        self.assertIn(_sgui("nuclear_program_has_programme_sgui"), wrapper)
        self.assertIn("type te_je_goal_bar = flowcontainer", _read(TAB_WIDGETS))

    def test_the_button_is_greyed_until_the_entry_runs(self):
        button = self.blocks[0]
        self.assertIn(f'enabled = "[{TAB_GATE}]"', button)
        self.assertIn("onclick = \"[InformationPanel.SelectTab('te_nuclear')]\"", button)
        self.assertIn(f"{TAB_UNLOCK}.IsValidTooltip(", button)
        for half in ("fourth_button_visibility", "fourth_button_visibility_checked"):
            m = re.search(rf'blockoverride "{half}" \{{\s*visible = "(.*)"', button)
            self.assertTrue(m, half)
            self.assertIn("IsTabSelected('te_nuclear')", m.group(1))
            self.assertIn(f"{TAB_UNLOCK}.IsShown(", m.group(1))
        for key in ("te_military_tab_nuclear", "te_military_tab_nuclear_tt", "te_military_tab_nuclear_locked_tt",
                    "te_military_nuclear_open_journal_tt"):
            self.assertTrue(_loc(key), key)

    def test_the_tab_icon_is_the_warhead(self):
        # In the name block: tab_buttons draws fourth_button_icon on slot 5's
        # selected half too, where the Covert tab is (test_covert_layout.py).
        m = re.search(r'blockoverride "fourth_button_name" \{.*?texture = "([^"]+)"', self.blocks[0], re.S)
        self.assertEqual(m.group(1), "gfx/interface/icons/nuclear_icons/warheads.dds")
        self.assertNotIn('blockoverride "fourth_button_icon"', self.military)

    def test_the_gates_read_the_rule_and_the_entry(self):
        sguis = _read(TAB_SGUIS)
        gate = _txt_block(sguis, "te_military_nuclear_tab_sgui")
        self.assertIn("has_game_rule = nuclear_weapons_enabled", gate)
        self.assertIn("has_journal_entry = je_nuclear_program", gate)
        unlock = _txt_block(sguis, "te_military_nuclear_tab_unlock_sgui")
        self.assertIn("is_shown = { has_game_rule = nuclear_weapons_enabled }", unlock)
        self.assertIn("is_valid = { nuclear_program_entry_unlocked = yes }", unlock)

    def test_the_checklist_is_the_entrys_own_test_in_one_line(self):
        trig = _txt_block(_read(NUKE_TRIGGERS), "nuclear_program_entry_unlocked")
        self.assertRegex(trig, r"custom_tooltip = \{\s*text = nuclear_program_unlock_tt\s*"
                               r"nuclear_program_entry_applies = yes\s*\}")
        # ...and that is the entry's `possible`, so the two cannot drift apart.
        self.assertRegex(_read(JE), r"possible = \{\s*nuclear_program_entry_applies = yes\s*\}")
        line = _loc("nuclear_program_unlock_tt")
        for part in ("$nuclear_weapons$", "$ICBMs$", "warheads", "crisis"):
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
