"""The Nuclear Weapons panel's section order, collapse defaults, state gates and
overview (docs/guides/gui_style_guide.md; nuclear_layout_widget.gui)."""
import functools
import glob
import os
import re
import unittest

import gui_test_helpers as gh
import gui_tree
from gui_test_helpers import assert_wide_matches_narrow
from scripts.generators import gen_te_systems_window as gen

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

STATUS = ["te_nuclear_sec_crisis", "te_nuclear_sec_strike", "te_nuclear_sec_world_crises", "te_nuclear_sec_posture",
          "te_nuclear_sec_forces", "te_nuclear_sec_home", "te_nuclear_sec_reputation",
          "te_nuclear_sec_taboo", "te_nuclear_sec_delivery", "te_nuclear_sec_powers"]
# Another country's copy of column 3's world sections, in its column 2, and
# the sections the player's columns 2 and 3 gate on Country.IsLocalPlayer
# (column 1's Nuclear Posture carries it on its own type's root).
WORLD_COLUMN = "te_nuclear_world_column"
WIDE_OWN = ("te_nuclear_sec_forces", "te_nuclear_sec_home", "te_nuclear_sec_reputation",
            "te_nuclear_sec_taboo", "te_nuclear_sec_delivery", "te_nuclear_sec_powers")
# The full-screen columns (spec 2026-11-02-te-window-wide-mode § 7): the goal
# bar stays under The Programme, in its own gated wrapper; Nuclear Posture at
# the foot of column 1 (owner, 2026-11-03), the narrow order kept.
WIDE_COLUMNS = [["te_nuclear_overview_panel", "te_nuclear_sec_programme", "te_nuclear_programme_bar",
                 "te_nuclear_sec_crisis", "te_nuclear_sec_strike", "te_nuclear_sec_world_crises",
                 "te_nuclear_sec_posture"],
                ["te_nuclear_sec_forces", "te_nuclear_sec_home", "te_nuclear_sec_reputation"],
                ["te_nuclear_sec_taboo", "te_nuclear_sec_delivery", "te_nuclear_sec_powers"]]
# (root name, container, the one type it wraps), in the entry's declaration order.
ROOTS = [("widget_je_nuclear_overview", "custom_widget_container_1", "te_nuclear_overview_panel"),
         ("widget_je_nuclear_programme", "custom_widget_container_3", "te_nuclear_sec_programme"),
         ("widget_je_nuclear_status", "custom_widget_container_4", "te_nuclear_status_sections")]
OLD_FLAGS = ["nuclear_program_powers", "nuclear_program_odds", "nd_capabilities_open", "nd_home_open",
             "nd_reputation_open", "nuclear_program_powers_open", "nd_taboo_hist_open"]
# widget_je_nuclear_reference held How Nuclear Weapons Work, now the Help page
# the overview's "?" opens (test_te_help_pages.py).
OLD_ROOTS = ["widget_je_nuclear_posture", "widget_je_nuclear_crisis", "widget_je_nuclear_balance",
             "widget_je_nuclear_reference"]


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


def _sgui(name, root="Country"):
    """A display handler's IsShown on the panel's Country (spec
    2026-11-02-charts-help-national-info § 6.3); the journal's roots, outside
    te_je_country, read the entry's (root="JournalEntry.GetCountry")."""
    return f"GetScriptedGui('{name}').IsShown( GuiScope.SetRoot( {root}.MakeScope ).End )"


# The composers' gate: the tab's own, the entry, on the panel's Country (has_journal_entry
# for any country; spec 2026-11-02-charts-help-national-info § 6.3). The journal's roots
# keep JournalEntry.IsActive.
ENTRY_GATE = _sgui("te_military_nuclear_tab_sgui")


def _cell_tip(body):
    """A cell's tooltip key: the plain key, or the player's branch of a
    SelectLocalization( Country.IsLocalPlayer, ... )."""
    return re.search(r"tooltip = \"(?:\[SelectLocalization\( Country\.IsLocalPlayer, ')?(\w+)", body).group(1)


ALL_GUI = "\n".join(_read(p) for p in NUCLEAR_GUI)


class OrderTest(unittest.TestCase):
    def test_status_order(self):
        layout = _read(LAYOUT)
        for composer, expected in (("te_nuclear_status_sections", STATUS),):
            body = _type_body(layout, composer)
            found = re.findall(r"^\t\t(te_nuclear_sec_\w+) = \{", body, re.M)
            self.assertEqual(found, expected, composer)
            self.assertIn(f'visible = "[{ENTRY_GATE}]"', body, composer)

    def test_every_section_is_a_type(self):
        for sec in STATUS + ["te_nuclear_sec_programme"]:
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
            # the section in te_je_country, the entry's Country (test_te_system_tab_bodies.py),
            # after the "?" on the overview (test_te_help_pages.py)
            first = ["te_help_row"] if name == "widget_je_nuclear_overview" else []
            self.assertEqual(re.findall(r"^\t(\w+) = \{\}?$", body, re.M), first + ["te_je_country"], name)
            self.assertEqual(re.findall(r"^\tte_je_country = \{\n\t\t(\w+) = \{\}$", body, re.M), [wrapped], name)

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
        self.assertIn(_sgui("nuclear_program_has_programme_sgui", root="JournalEntry.GetCountry"), body)


class GateTest(unittest.TestCase):
    """Sections that only matter in one state are shown only in that state (rule 7)."""

    GATES = {
        "te_nuclear_sec_programme": [_sgui("nuclear_program_has_programme_sgui")],
        "te_nuclear_sec_crisis": [_sgui("nd_in_crisis_sgui")],
        "te_nuclear_sec_strike": [_sgui("nd_plan_shown_sgui")],
        "te_nuclear_sec_world_crises": [_sgui("nd_world_crises_sgui")],
        "te_nuclear_sec_posture": [_sgui("nd_armed_sgui")],
        "te_nuclear_sec_forces": [_sgui("nd_armed_sgui")],
        "te_nuclear_sec_home": [_sgui("nd_armed_sgui")],
        "te_nuclear_sec_reputation": [_sgui("nd_has_reputation_sgui"), _sgui("nd_last_crisis_sgui")],
        "te_nuclear_sec_taboo": [_sgui("nd_taboo_exists_sgui")],
        "te_nuclear_sec_powers": [_sgui("nd_taboo_exists_sgui"), _sgui("nd_powers_listed_sgui")],
        "te_nuclear_sec_delivery": None,
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
        cred = body.index('text = "nd_w_pledge_label"')   # credibility is the overview's (NUC-13)
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



def _types(*paths):
    out = {}
    for path in paths:
        out.update({n.name: n for n in gui_tree.parse(_read(path)).walk() if n.kind == "type"})
    return out


def _row_width(node):
    """A horizontal row of fixed-width children: margins, cells and spacing."""
    cells = [gui_tree.size(c)[0] for c in gui_tree.widgets(node)]
    spacing = int(node.prop("spacing").value) if node.prop("spacing") else 0
    margin = gui_tree.size(node, "margin")
    return 2 * (margin[0] if margin else 0) + sum(cells) + spacing * (len(cells) - 1)


class WidthTest(unittest.TestCase):
    """A centred panel sized by its content is centred at its first width
    (gui_modding_guide.md gotcha #43), so each holds the width it grows to."""

    def test_the_powers_head_is_as_wide_as_its_rows(self):
        # With no rows yet (up to a month after the first warhead) the panel
        # was centred at the head's 414 and ran past the section once rows came.
        types = _types(PROGRAM)
        head, row = types["nuclear_program_powers_head"], types["nuclear_program_power_row"]
        self.assertEqual(_row_width(head), 414)
        self.assertEqual(gui_tree.size(head, "minimumsize"), (gui_tree.size(row)[0], -1))

    def test_the_reputation_panel_keeps_one_width(self):
        # 512 with the pledges' nd_row, 500 with the last crisis's lines alone.
        types = _types(DETERRENCE)
        margin = gui_tree.size(types["nd_panel"], "margin")[0]
        row = _row_width(types["nd_row"])
        lines = max(gui_tree.size(types["nd_text"], "minimumsize")[0],
                    2 * gui_tree.size(types["nd_script_line"], "margin")[0]
                    + gui_tree.size(next(c for c in types["nd_script_line"].children if c.kind == "textbox"),
                                    "minimumsize")[0])
        self.assertEqual((row, lines), (492, 480))
        (panel,) = [c for c in types["te_nuclear_sec_reputation"].walk() if c.kind == "nd_panel"]
        self.assertEqual(gui_tree.size(panel, "minimumsize"), (2 * margin + row, -1))

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
            else:                        # shown only when opened: one negated (a header's show-more
                # arrow, or an in-row toggle's "Change" word), the content bare
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 1, f)

    def test_live_sections_open_reference_collapsed(self):
        opened = {"te_nuclear_sec_programme": "nuclear_program_programme_closed",
                  "te_nuclear_sec_crisis": "nd_crisis_closed",
                  "te_nuclear_sec_strike": "nd_strike_closed",
                  "te_nuclear_sec_world_crises": "nd_world_crises_closed",
                  "te_nuclear_sec_posture": "nd_posture_closed",
                  "te_nuclear_sec_forces": "nd_capabilities_closed",
                  "te_nuclear_sec_home": "nd_home_closed",
                  "te_nuclear_sec_reputation": "nd_reputation_closed",
                  "te_nuclear_sec_taboo": "nd_taboo_panel_closed",
                  "te_nuclear_sec_delivery": "nuclear_program_odds_closed",
                  "te_nuclear_sec_powers": "nuclear_program_powers_closed"}
        for sec, flag in opened.items():
            body = _type_body(ALL_GUI, sec)
            toggles = re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", body)
            self.assertEqual(toggles[0], flag, sec)

    def test_how_it_works_is_the_help_page(self):
        """How Nuclear Weapons Work is the Help page alone
        (te_nuclear_weapons_help_popup, on te_popup = help_nuclear_weapons),
        which the "?" at the top of the entry and in the tab's header opens: the
        link section is gone, and its reference composer and root with it
        (test_te_help_pages.py)."""
        for name in ("te_nuclear_sec_how", "te_nuclear_reference_sections", "nuclear_how_open"):
            self.assertNotIn(name, ALL_GUI, name)
        self.assertIn("type te_nuclear_weapons_help_body", _read(LAYOUT))

    def test_subsections_are_nested(self):
        """The taboo's chart is a nested subsection, open (owner, 2026-09-29:
        history charts open by default)."""
        body = _type_body(ALL_GUI, "te_nuclear_sec_taboo")
        i = body.index("GetVariableSystem.Toggle('nd_taboo_hist_closed')")
        header = body.rfind("_header = {", 0, i)
        self.assertEqual(body[header - len("nd_subsection"):header], "nd_subsection")

    def test_each_posture_axis_opens_its_own_choices(self):
        """NUC-3: one row per axis, a Change toggle beside it (rule 6), and the
        axis's choices directly beneath it, collapsed by default; three flags,
        not one subsection mixing readiness and authority."""
        body = _type_body(ALL_GUI, "te_nuclear_sec_posture")
        rows = [m.start() for m in re.finditer(r"\bnd_axis_row = \{", body)]
        self.assertEqual(len(rows), 3)
        for n, (flag, label, first) in enumerate((("nd_doctrine_open", "nd_w_doctrine_label", "nd_w_doctrine_choice_1"),
                                                  ("nd_readiness_open", "nd_w_readiness_label", "nd_w_readiness_choice_0"),
                                                  ("nd_authority_open", "nd_w_authority_label", "nd_w_authority_choice_1"))):
            row = body[rows[n]:]
            toggle = row.index(f"GetVariableSystem.Toggle('{flag}')")
            self.assertLess(row.index(f'text = "{label}"'), toggle, flag)
            self.assertIn(f"SelectLocalization( Not( GetVariableSystem.Exists('{flag}') ), 'nd_w_btn_change', 'nd_w_btn_hide' )",
                          row[:toggle])
            opened = row.index(f'visible = "[GetVariableSystem.Exists(\'{flag}\')]"')
            self.assertLess(toggle, opened, flag)
            self.assertLess(opened, row.index(f'text = "{first}"'), flag)
            if n < 2:
                self.assertLess(row.index(f'text = "{first}"'), rows[n + 1] - rows[n], flag)
            self.assertIn("[Concept('concept_", _loc(label), label)
        for old in ("nd_forces_open", "nd_w_forces_header", "nd_w_doctrine_header"):
            self.assertNotIn(old, ALL_GUI, old)

    def test_the_option_in_force_is_tinted(self):
        """NUC-5: each list marks its option in force, as Covert's Funding Levels
        do; readiness marks the level ordered, the one its Order button greys."""
        body = _type_body(ALL_GUI, "te_nuclear_sec_posture")
        for value, codes, key in (("nd_display_doctrine_code", range(1, 6), "nd_w_doctrine_choice_{}"),
                                  ("nd_display_readiness_target_code", range(4), "nd_w_readiness_choice_{}"),
                                  ("nd_display_authority_code", range(1, 5), "nd_w_authority_choice_{}")):
            for code in codes:
                i = body.index(f'text = "{key.format(code)}"')
                row = body[body.rfind("_row = {", 0, i):i]
                self.assertIn(f"ScriptValue('{value}'), '(CFixedPoint){code}' )", row, key.format(code))
                self.assertIn('blockoverride "row_current"', row)
        for t in ("nd_choice_row", "nd_readiness_row"):
            self.assertRegex(_type_body(ALL_GUI, t), r'block "row_current" \{\s*visible = no\s*\}', t)

    def test_the_readiness_table(self):
        """NUC-5: the four levels as rows of a table, upkeep and the survivability
        a crisis counts side by side, under a head row."""
        body = _type_body(ALL_GUI, "te_nuclear_sec_posture")
        self.assertLess(body.index("nd_readiness_head = {}"), body.index('text = "nd_w_readiness_choice_0"'))
        for r in range(4):
            self.assertIn(f'text = "nd_w_readiness_upkeep_{r}"', body)
            self.assertIn(f'text = "nd_w_readiness_survivability_{r}"', body)
            self.assertIn(f"nd_upkeep_weekly_at_readiness_{r}", _loc(f"nd_w_readiness_upkeep_{r}"))
            self.assertNotIn("Upkeep at this level", _loc(f"nd_w_readiness_choice_{r}_tt"), r)

    def test_when_the_posture_can_change_is_said(self):
        """NUC-4: the values script already computes are drawn, above each list
        and in each axis's hover."""
        for key, value in (("nd_w_doctrine_legend", "nd_display_doctrine_months_left"),
                           ("nd_w_authority_legend", "nd_display_authority_months_left"),
                           ("nd_w_readiness_legend", "nd_display_readiness_lock_months"),
                           ("nd_w_doctrine_tt", "nd_display_doctrine_months_left"),
                           ("nd_w_authority_tt", "nd_display_authority_months_left"),
                           ("nd_w_readiness_tt", "nd_display_readiness_lock_months")):
            self.assertIn(f"ScriptValue('{value}')", _loc(key), key)

    def test_no_old_flag_survives(self):
        for f in OLD_FLAGS:
            self.assertNotRegex(ALL_GUI, rf"'{f}'", f)


# Explanations that live in "How Nuclear Weapons Work", and the live sections they left.
HOW_KEYS = ["nd_w_home_legend", "nd_w_reputation_legend", "nd_w_crisis_actions_legend",
            "je_nuclear_program_widget_odds_note", "je_nuclear_program_widget_powers_legend",
            "je_nuclear_how_programme", "je_nuclear_how_posture", "je_nuclear_how_taboo", "je_nuclear_how_strike"]


class HowItWorksTest(unittest.TestCase):
    def test_explanations_live_in_how_it_works(self):
        how = _type_body(_read(LAYOUT), "te_nuclear_weapons_help_body")
        for key in HOW_KEYS:
            self.assertIn(f'"{key}"', how, key)
        self.assertEqual(how.count("nd_subheader = {"), how.count("nd_note = {"))

    def test_live_sections_carry_no_explanations(self):
        for sec in STATUS + ["te_nuclear_sec_programme"]:
            body = _type_body(ALL_GUI, sec)
            for key in HOW_KEYS:
                self.assertNotIn(f'"{key}"', body, f"{sec} still explains ({key})")

    def test_the_first_heading_has_no_top_margin(self):
        how = _type_body(_read(LAYOUT), "te_nuclear_weapons_help_body")
        first = how[how.index("nd_subheader = {"):]
        first = first[:first.index("nd_note = {")]
        self.assertIn('blockoverride "subheader_margin" {}', first)


def _coded(text, value):
    """{code: [textures]} for the icons gated on ScriptValue(value) == code."""
    found = {}
    pat = (rf"visible = \"\[EqualTo_CFixedPoint\( Country\.MakeScope\.ScriptValue\('{value}'\), "
           rf"'\(CFixedPoint\)(-?\d+)' \)\]\"(\s*)texture = \"([^\"]+)\"")
    for m in re.finditer(pat, text, re.S):
        found.setdefault(int(m.group(1)), []).append(m.group(3))
    return found


def _cells(text):
    """Each te_banking_ov_cell instance of the overview, as its body."""
    out = []
    for m in re.finditer(r"te_banking_ov_cell = \{", text):
        depth = 0
        for k in range(m.end() - 1, len(text)):
            depth += (text[k] == "{") - (text[k] == "}")
            if depth == 0:
                out.append(text[m.end():k])
                break
    return out


class OverviewTest(unittest.TestCase):
    """NUC-21 (owner, 2026-10-27): Banking's cells in place of the round-3 rows
    of icons, each saying what needs the returning player: the weeks to the
    crisis deadline, the time to the next warhead, when the doctrine can next
    change."""

    @classmethod
    def setUpClass(cls):
        cls.ov = _read(OVERVIEW)
        cls.panel = _type_body(cls.ov, "te_nuclear_overview_panel")

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

    def test_the_cells_are_bankings(self):
        """Banking's own cell, reused as it is: a size, a tooltip, the caption in
        the 154 column, an icon, the word and the figure."""
        cells = _cells(self.panel)
        self.assertEqual(len(cells), 9)   # 7 for the player, 2 for another country (Row 2's own)
        for body in cells:
            tip = _cell_tip(body)
            with self.subTest(cell=tip):
                self.assertIn("size = { 238 70 }", body)
                self.assertRegex(body, r'blockoverride "caption_width" \{\s*max_width = 154\s*\}')
                for block in ("caption", "icons", "word", "third_line"):
                    self.assertIn(f'blockoverride "{block}"', body)
                self.assertIn("te_nuclear_ov_figure = {", body)
                self.assertTrue(_loc(tip), tip)
        self.assertNotIn("type te_banking_ov_cell", self.ov, "the cell is Banking's, not redefined here")
        for t in ("te_nuclear_ov_word", "te_nuclear_ov_figure"):
            self.assertIn("using = te_nuclear_fontsize_overview", _type_body(self.ov, t), t)

    def test_what_needs_the_player_is_on_the_face(self):
        figure = {_cell_tip(b): re.search(r'te_nuclear_ov_figure = \{\s*text = "(\w+)"', b).group(1)
                  for b in _cells(self.panel)}
        self.assertIn("nd_display_crisis_weeks_left", _loc(figure["je_nuclear_ov_crisis_tt"]))
        self.assertIn("je_nuclear_ov_crisis_deadline_soon", _loc(figure["je_nuclear_ov_crisis_tt"]))
        self.assertTrue(_loc("je_nuclear_ov_crisis_deadline_soon").startswith("#R "))
        self.assertIn("GetCustom('nuclear_program_next_short')", _loc(figure["je_nuclear_ov_prog_tt"]))
        self.assertIn("nuclear_program_display_months_to_next", _loc("nuclear_program_next_short_estimate"))
        self.assertIn("nd_display_doctrine_months_left", _loc(figure["nd_w_doctrine_tt"]))
        self.assertIn("nd_display_authority_months_left", _loc(figure["nd_w_authority_tt"]))
        self.assertIn("nd_display_public_estimate", _loc(figure["je_nuclear_ov_warheads_tt"]))

    def test_the_rows_are_gated(self):
        body = self.panel
        self.assertIn(f'visible = "[{ENTRY_GATE}]"', body)
        crisis = body.index("'je_nuclear_ov_crisis_tt'")
        self.assertIn(_sgui("nd_in_crisis_sgui"), body[:crisis])
        posture = body.index('tooltip = "nd_w_doctrine_tt"')
        self.assertIn(_sgui("nd_armed_sgui"), body[crisis:posture])
        for tip, gate in (("nd_w_authority_tt", "nd_armed_sgui"), ("nd_w_credibility_tt", "nd_has_reputation_sgui")):
            i = body.index(f'tooltip = "{tip}"')
            self.assertIn(_sgui(gate), body[i - 300:i], tip)
        taboo = body.index("ScriptValue('nd_disp_taboo_bar_low')")
        self.assertIn(_sgui("nd_taboo_exists_sgui"), body[posture:taboo])

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
        cur = "Country.MakeScope.ScriptValue('nd_display_survivability')"
        head = "Country.MakeScope.ScriptValue('nd_display_survivability_heading')"
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
        self.assertIn("minimumsize = { 480 -1 }", self.panel)
        rows = [r for r in re.split(r"### Row \d", self.panel)[1:]]
        self.assertEqual(len(rows), 6)   # Rows 1 to 5, and Row 2 for another country
        for row in rows[:5]:
            n = row.count("te_banking_ov_cell = {")
            self.assertIn(n, (1, 2))
            self.assertLessEqual(n * 238 + (n - 1) * int(re.search(r"spacing = (\d+)", row).group(1)), 480)
        taboo = rows[5]
        cells = [int(w) for w in re.findall(r"maximumsize = \{ (\d+) -1 \}", taboo)]
        bar = int(re.search(r"widget = \{\s*size = \{ (\d+) 18 \}", taboo).group(1))
        self.assertEqual(len(cells), 2)
        self.assertLessEqual(sum(cells) + bar + 24 + 3 * 8, 480)


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
# The mod's own icons from elsewhere: another country's guarantees cell draws the
# nuclear_guarantee treaty article's (115_nuclear_guarantee.txt).
MOD_KEPT = {"gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_guarantee.dds"}
# Placeholders until the art exists (style guide rule 10), each listed in
# docs/systems/nuclear_gui_icons.md. None since icon batch 7 painted credibility's.
PLACEHOLDERS = set()


def _all_icon_names():
    names = [n for codes in CODED_ICONS.values() for n in codes.values()]
    return names + ["warheads", "crisis", "credibility"]


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

    def test_warheads_crisis_and_credibility(self):
        for name, tooltip in (("warheads", "je_nuclear_ov_warheads_tt"), ("crisis", "je_nuclear_ov_crisis_tt"),
                              ("credibility", "nd_w_credibility_tt")):
            with self.subTest(cell=name):
                m = re.search(rf'tooltip = "[^"]*\b{tooltip}\b[^"]*".*?texture = "([^"]+)"', self.ov, re.S)
                self.assertEqual(m.group(1), f"{NUCLEAR_ICONS}{name}.dds")

    def test_no_placeholder_left(self):
        for path in re.findall(r'texture = "(gfx/interface/[^"]+)"', self.ov):
            with self.subTest(path=path):
                self.assertTrue(path.startswith(NUCLEAR_ICONS) or path in VANILLA_KEPT | MOD_KEPT | PLACEHOLDERS,
                                f"placeholder left: {path}")
        for path in PLACEHOLDERS:
            self.assertIn(path, _read(ICON_DOC), path)

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
# The style guide's width budget (rule 3), in GUI units per character: the
# serif row font about half its size (8.5 at 17, 10 at 20), and 8.6 for the
# 16-point tooltip face of the overview, plus 10%. Each size is read from the
# panel's own font templates (NUC-20), so a pass on type moves the budget.
_TEMPLATES = {m.group(1): int(m.group(2)) for m in re.finditer(
    r"template te_nuclear_fontsize_(\w+) \{\s*fontsize = (\d+)", _read(DETERRENCE))}
ROW = 10.0 / 20 * _TEMPLATES["row"]
HEADING = 10.0 / 20 * _TEMPLATES["heading"]
OVERVIEW_UNIT = 8.6 / 16 * _TEMPLATES["overview"]
MARGIN = 1.1
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
        elif "SelectLocalization(" in part and depth < 3:
            keys = re.findall(r"'(\w+)'", part.split("SelectLocalization(", 1)[1])[-2:]
            options = [r for k in keys for r in _renderings(k, depth + 1)]
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


def _block_texts(text, block_name):
    return set(re.findall(rf'blockoverride "{block_name}" \{{\s*text = "(\w+)"', text))


class LabelBudgetTest(unittest.TestCase):
    """Every static label, and every dynamic word, in a fixed-width cell fits it,
    at the panel's type sizes (rows 17, subheadings 20, the overview 16)."""

    def _fits(self, keys, width, font, where):
        self.assertTrue(keys, where)
        for key in keys:
            for text in _renderings(key):
                need = len(text) * font * MARGIN
                self.assertLessEqual(need, width, f"{where}: {key} reads {text!r} ({need:.0f} > {width})")

    def test_the_ladder(self):
        self.assertEqual(_TEMPLATES, {"row": 17, "heading": 20, "overview": 16})
        for path in NUCLEAR_GUI:
            text = _read(path)
            self.assertNotRegex(text, r"using = fontsize_(small|medium|large)\b", os.path.basename(path))
        self.assertIn("using = te_nuclear_fontsize_heading", _type_body(_read(DETERRENCE), "nd_subheader"))

    def test_table_rows(self):
        det, prog = _read(DETERRENCE), _read(PROGRAM)
        for path, type_name, label_w, value_w in ((det, "nd_row", 210, 266), (prog, "nuclear_program_row", 200, 276)):
            body = _type_body(path, type_name)
            self.assertEqual([int(w) for w in re.findall(r"size = \{ (\d+) 24 \}", body)], [label_w, value_w])
            self.assertEqual(body.count("using = te_nuclear_fontsize_row"), 2)
            self._fits(_block_texts(path, "row_label"), label_w, ROW, f"{type_name} label")
            self._fits(_block_texts(path, "row_value"), value_w, ROW, f"{type_name} value")

    def test_the_posture_axes(self):
        det = _read(DETERRENCE)
        body = _type_body(det, "nd_axis_row")
        self.assertEqual([int(w) for w in re.findall(r"size = \{ (\d+) 30 \}", body)], [160, 218, 90])
        self._fits(_block_texts(det, "axis_label"), 160, ROW, "axis label")
        self._fits(_block_texts(det, "axis_value"), 218, ROW, "axis value")
        self._fits(["nd_w_btn_change", "nd_w_btn_hide"], 90, ROW, "axis toggle")

    def test_steppers_choices_and_buttons(self):
        both = _read(DETERRENCE) + _read(PROGRAM)
        labels = set(re.findall(r'text = "(\w+)"\n\t+size = \{ 170 24 \}', both))
        values = set(re.findall(r'text = "(\w+)"\n\t+tooltip = "\w+"\n\t+size = \{ 246 24 \}', both))
        # Safeguards, hardening, the arsenal ceiling and the programme's own,
        # then the Strike section's target and warheads (rework phase 3).
        self.assertEqual(len(labels), 6, labels)
        self.assertEqual(len(values), 5, values)
        self._fits(labels, 170, ROW, "stepper label")
        self._fits(values, 246, ROW, "stepper value")
        det = _read(DETERRENCE)
        self.assertEqual([int(w) for w in re.findall(r"size = \{ (\d+) 30 \}", _type_body(det, "nd_choice_row"))], [358, 110])
        self._fits(_block_texts(det, "choice_name"), 358, ROW, "choice")
        self._fits(_block_texts(det, "button_text"), 110, ROW, "button")
        # Every instance fills the type's blocks: a child added straight into the
        # widget would sit at 0,0 over the type's own row.
        for t, block in (("nd_choice_row", "choice_name"), ("nd_readiness_row", "level_name")):
            self.assertEqual(len(re.findall(rf"\b{t} = \{{", det)), det.count(f'blockoverride "{block}"'), t)

    def test_the_readiness_table(self):
        det = _read(DETERRENCE)
        self.assertEqual([int(w) for w in re.findall(r"size = \{ (\d+) 30 \}", _type_body(det, "nd_readiness_row"))],
                         [120, 100, 124, 110])
        self._fits(_block_texts(det, "level_name"), 120, ROW, "readiness level")
        self._fits(_block_texts(det, "level_upkeep"), 100, ROW, "readiness upkeep")
        self._fits(_block_texts(det, "level_survivability"), 124, ROW, "readiness survivability")
        head = _type_body(det, "nd_readiness_head")
        for key, width in zip(re.findall(r'text = "(\w+)"', head), (120, 100, 124)):
            self._fits([key], width, ROW, "readiness head")

    def test_the_crisis(self):
        det = _read(DETERRENCE)
        cell = _type_body(det, "nd_crisis_cell") + _type_body(det, "nd_crisis_cell_figure")
        self.assertEqual(set(re.findall(r"max_width = (\d+)", cell)), {"218"})
        sec = _type_body(det, "te_nuclear_sec_crisis")
        for block in ("caption", "word"):
            self._fits({k for k in _block_texts(sec, block)}, 218, ROW, f"crisis cell {block}")
        figures = set(re.findall(r'nd_crisis_cell_figure = \{\s*text = "(\w+)"', sec))
        self.assertEqual(len(figures), 4)
        self._fits(figures, 218, ROW, "crisis cell figure")
        self._fits(["nd_next_pressure_none", "nd_next_pressure_paused", "nd_next_pressure_weeks"], 218, ROW, "next pressure")
        row = _type_body(det, "nd_outcome_row")
        self.assertEqual([int(w) for w in re.findall(r"size = \{ (\d+) 24 \}", row)], [170, 192, 104])
        self._fits(_block_texts(sec, "outcome_label"), 170, ROW, "outcome")
        self._fits(_block_texts(sec, "outcome_effect"), 192, ROW, "outcome effect")
        self._fits(_block_texts(sec, "outcome_credibility"), 104, ROW, "outcome credibility")
        head = _type_body(det, "nd_outcome_head")
        for key, width in zip(re.findall(r'text = "(\w+)"', head), (170, 192, 104)):
            self._fits([key], width, ROW, "outcome head")

    def test_the_lists(self):
        det, prog = _read(DETERRENCE), _read(PROGRAM)
        wc = _type_body(det, "nd_world_crisis_row")
        self._fits(["nd_wc_item_stage"], 168, ROW, "world crisis stage")
        self._fits(["nd_wc_item_danger"], 180, ROW, "world crisis danger")
        for key, width in zip(re.findall(r'text = "(\w+)"', _type_body(det, "nd_world_crisis_head")), (108, 168, 180)):
            self._fits([key], width, ROW, "world crisis head")
        self.assertIn("size = { 168 28 }", wc)
        self._fits(["nuclear_program_power_estimate"], 110, ROW, "power estimate")
        for key, width in zip(re.findall(r'text = "(\w+)"', _type_body(prog, "nuclear_program_powers_head")), (286, 110)):
            self._fits([key], width, ROW, "powers head")

    def test_overview(self):
        ov = _read(OVERVIEW)
        dash = _read(os.path.join(W, "banking_dashboard_widget.gui"))
        self.assertIn("using = banking_dash_fontsize_overview", _type_body(dash, "te_banking_ov_cell"))
        self.assertRegex(dash, r"template banking_dash_fontsize_overview \{\s*fontsize = 16")
        panel = _type_body(ov, "te_nuclear_overview_panel")
        for body in _cells(panel):
            tip = _cell_tip(body)
            with self.subTest(cell=tip):
                self._fits(_block_texts(body, "caption"), 154, OVERVIEW_UNIT, f"{tip} caption")
                words = set(re.findall(r'te_nuclear_ov_word = \{\s*(?:visible = "[^"]*"\s*)?text = "(\w+)"', body))
                self._fits(words, 154, OVERVIEW_UNIT, f"{tip} word")
                figures = set(re.findall(r'te_nuclear_ov_figure = \{\s*text = "(\w+)"', body))
                self._fits(figures, 154, OVERVIEW_UNIT, f"{tip} figure")
        for t in ("te_nuclear_ov_word", "te_nuclear_ov_figure"):
            self.assertIn("max_width = 154", _type_body(ov, t), t)
        self._fits(["je_nuclear_ov_taboo_label"], 60, OVERVIEW_UNIT, "taboo label")
        self._fits(["je_nuclear_ov_taboo_value"], 190, OVERVIEW_UNIT, "taboo headline")

    def test_forces_and_at_home(self):
        det = _read(DETERRENCE)
        self._fits(["nd_w_survivability_label"], 170, ROW, "survivability label")
        self._fits(["nd_w_survivability_value"], 94, ROW, "survivability value")
        self._fits(["nd_home_ig_name"], 280, ROW, "At Home group")
        self._fits([f"nd_home_view_{n}" for n in range(1, 11)], 200, ROW, "At Home class")
        table = _type_body(det, "nd_home_term_row")
        self.assertEqual([int(w) for w in re.findall(r"size = \{ (\d+) 22 \}", table)], [220, 60])
        terms = ("approval", "doctrine", "readiness", "authority", "strain", "possession", "business", "cap")
        self._fits([f"nd_home_row_{t}" for t in terms], 220, ROW, "At Home row")
        self._fits([f"nd_home_row_{t}_value" for t in terms], 60, ROW, "At Home value")


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

    def _host(self):
        body = self.blocks[1]
        self.assertIn('name = "te_military_nuclear_tab"', body)
        return body

    def _content(self):
        """The tab's body (te_nuclear_tab_body), which the Military panel's tab
        and the Timeline Extended window's both mount
        (test_te_system_tab_bodies.py checks the mounts)."""
        self.assertIn("te_nuclear_tab_body = {}", self._host())
        return _type_body(_read(LAYOUT), "te_nuclear_tab_body")

    def test_two_marked_blocks_the_button_and_the_content(self):
        self.assertEqual(len(self.blocks), 2)
        self.assertIn('blockoverride "fourth_button"', self.blocks[0])
        self.assertIn("visible = \"[InformationPanel.IsTabSelected('te_nuclear')]\"", self._host())

    def test_the_tab_composes_the_journal_roots_types_in_order(self):
        body = self._content()
        # the header's map button (te_jmap_nuclear_map_button, journal_map_modes.md) is not a journal root
        # nor is the entry's modifier strip, the frame's (test_te_entry_modifier_strip.py)
        found = [n for n in re.findall(r"^\t+(te_\w+) = \{\}", body, re.M)
                 if not n.startswith("te_jmap_") and n != "te_je_modifier_strip"]
        roots = [wrapped for _, _, wrapped in ROOTS]
        # The journal's roots, with the entry's own bar under The Programme, as in the journal.
        self.assertEqual(found, roots[:2] + ["te_nuclear_programme_bar"] + roots[2:])
        # The link back to the entry is the frame's, after every section.
        self.assertNotIn('blockoverride "tab_open_journal" ', body)

    def test_the_gate_sits_above_the_journal_entry_datacontext(self):
        body = self._content()
        dc = body.index("datacontext = \"[GetPlayerJournalEntry('je_nuclear_program')]\"")
        self.assertLess(body.index(f'visible = "[{TAB_GATE}]"'), dc)
        # Never on the widget that carries the datacontext itself (the
        # frame's tab_entry block holds it alone).
        self.assertNotIn("visible", body[body.index('blockoverride "tab_entry"'):dc])

    def test_the_column_is_as_wide_as_the_journal_roots(self):
        """The frame's column, a fixed 520 (test_te_system_tab_bodies.py)."""
        self._content()
        self.assertRegex(_read(LAYOUT), r"type te_nuclear_tab_body = te_system_tab_frame \{")

    def test_the_bar_shows_with_a_programme_only(self):
        """The bar's type, which both tab layouts draw: shown with a programme,
        and the player's own (progress is hidden from another country)."""
        self.assertIn("te_nuclear_programme_bar = {}", self._content())
        bar = _type_body(_read(LAYOUT), "te_nuclear_programme_bar")
        self.assertEqual(_root_visible(bar),
                         f"And( Country.IsLocalPlayer, {_sgui('nuclear_program_has_programme_sgui')} )")
        self.assertRegex(bar, r"flowcontainer = \{\s*using = te_own_country_only\b[^{}]*te_je_goal_bar = \{\}")
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


class TestSurvivorsRow(unittest.TestCase):
    """Forces: survivors against the main rival, shown while there is one
    (2026-10-28 rework spec §10)."""

    def test_survivors_row_present(self):
        text = _read(DETERRENCE)
        i = text.index('text = "nd_w_survivors_label"')
        row = text[text.rindex("nd_row = {", 0, i):i + 400]
        self.assertIn("nd_has_main_rival_sgui", row)
        self.assertIn('text = "nd_w_survivors_value"', row)
        self.assertIn('tooltip = "nd_w_survivors_tt"', row)


class WideTest(unittest.TestCase):
    """The full-screen columns (spec 2026-11-02-te-window-wide-mode §§ 7, 9.4,
    9.5): te_nuclear_wide_sections places the tab's sections, under the same
    gates, in fixed 520 columns read down each and then across, and the
    window's wide mount holds it in place of te_nuclear_tab_layout."""

    def test_the_wide_layout_is_the_tabs_in_three_columns(self):
        """For the player: columns 2 and 3 carry Country.IsLocalPlayer on top of
        the tab's gate, which is always true there (column 1's Nuclear Posture
        carries it on its type's own root); another country's copy of
        column 3's world sections (te_nuclear_world_column) is skipped here and
        held by the next test."""
        columns = assert_wide_matches_narrow(self, "te_nuclear_wide_sections",
                                             layout=("te_nuclear_tab_body", "te_nuclear_tab_layout"),
                                             extra=(WORLD_COLUMN,), added_gates=WIDE_OWN)
        self.assertEqual(columns, WIDE_COLUMNS)
        # Nuclear Posture shares column 1's wrapper, which shows for another country too: its own root keeps it the
        # player's (owner, 2026-11-03)
        posture = gh._type_body(gh._all_gui(), "te_nuclear_sec_posture")
        self.assertTrue(_root_visible(posture).startswith("And( Country.IsLocalPlayer, "), _root_visible(posture))

    def test_another_country_gets_the_world_sections_in_column_2(self):
        """Another country's columns 2 and 3 are the player's own, so column 2
        holds its copy of column 3's world sections instead: exactly the taboo
        and Nuclear Powers, under Not( Country.IsLocalPlayer ) and the tab's
        gate, spaced as column 3 spaces them. The player's copies sit under
        Country.IsLocalPlayer, the one gate they gained."""
        text = gh._all_gui()
        gate = "GetScriptedGui('te_military_nuclear_tab_sgui').IsShown( GuiScope.SetRoot( Country.MakeScope ).End )"
        body = gh._type_body(text, WORLD_COLUMN)
        self.assertEqual(_root_visible(body), f"And( Not( Country.IsLocalPlayer ), {gate} )")
        self.assertEqual(re.findall(r"\b(te_\w+) = \{\}", body),
                         ["te_nuclear_sec_taboo", "te_nuclear_sec_powers"])
        self.assertEqual(re.findall(r"spacing = (\d+)", body), ["10", "4"], "column 3's spacing, then its composer's")
        wide = gh._type_body(text, "te_nuclear_wide_sections")
        m = re.search(r'blockoverride "column_2" \{', wide)
        col2 = wide[m.end():gh._close(wide, m.end() - 1)]
        self.assertTrue(col2.rstrip().endswith(f"{WORLD_COLUMN} = {{}}"), "the copy closes column 2")
        self.assertEqual(wide.count(f"{WORLD_COLUMN} = {{}}"), 1)
        visibles = re.findall(r'visible = "\[(.*)\]"', wide)
        self.assertEqual(visibles.count(f"And( Country.IsLocalPlayer, {gate} )"), 2, "columns 2 and 3's composers")
        self.assertNotIn("Country.IsLocalPlayer", visibles, "column 3's How wrapper is gone")
        self.assertEqual(visibles.count(gate), 1, "column 1's composer, open for both")

    def test_the_window_registers_it(self):
        tab = {t.key: t for t in gen.TABS}["nuclear_weapons"]
        self.assertEqual((tab.body, tab.layout, tab.wide), ("te_nuclear_tab_body", "te_nuclear_tab_layout", "te_nuclear_wide_sections"))



# ---- Another country's panel (National Info; spec 2026-11-02-charts-help-national-info § 6.4) --------
# The owner's rule: Nuclear is public through the public estimate, and the true stockpile never
# reaches another country's view, whether through markup, a tooltip, a loc splice or a chart.
# Another country sees the public estimate (nd_believed_stockpile: the estimate once the country
# has tested, nothing before), its crisis (stage, danger and deadline, as World Crises already
# shows every government), the nuclear guarantees it gives and holds, and the world's own lists
# (World Crises, Nuclear Powers, the taboo and its chart). Read as that panel draws
# te_nuclear_wide_sections (gui_test_helpers.panel_view: te_own_country_only parts left out).

WIDE = "te_nuclear_wide_sections"
# A section whose root is And( Country.IsLocalPlayer, <its gate> ) collapses for another country,
# and its children sit in a te_own_country_only wrapper: nothing of it is drawn there, and the
# player's panel shows it exactly when it did before.
COLLAPSED = ["te_nuclear_sec_programme", "te_nuclear_programme_bar", "te_nuclear_sec_crisis",
             "te_nuclear_sec_strike", "te_nuclear_sec_posture", "te_nuclear_sec_forces", "te_nuclear_sec_home",
             "te_nuclear_sec_reputation"]
_COLLAPSE = re.compile(r'visible = "\[And\( Country\.IsLocalPlayer, .*\)\]"')
# What says how many warheads a country truly holds, how close the next one is, its posture or its
# custody, or whether it is armed at all (nd_armed_sgui reads the true count, nd_has_reputation_sgui
# the posture's credibility, created with the first warhead), and the handlers whose hovers print
# them. None may reach another country's panel. A listed base: _leaks() adds every script value,
# scripted trigger and scripted GUI that reads the true state at any depth.
LEAKS = re.compile(
    r"\b(nd_display_stockpile|nuclear_weapon_stockpile|nd_stockpile|nd_display_public_estimate"
    r"|nd_display_survivab\w*|nd_display_safeguards|nd_display_hardening|nd_display_readiness\w*"
    r"|nd_display_reliability|nd_display_strain|nd_display_upkeep\w*|nd_display_authority\w*"
    r"|nd_display_doctrine_months_left|nd_display_hold\w*|nd_display_loose\w*|nd_display_survivors\w*"
    r"|nuclear_program_display_\w+|nuclear_weapons_program_funding|nuclear_weapon_program_progress"
    r"|nd_disp_taboo_burden\w*|nd_disp_taboo_(?:prestige|leverage)_cost\w*|nd_ar_\w+|nd_custody\w*"
    r"|nd_armed_sgui|nd_has_reputation_sgui|nuclear_program_has_programme_sgui|nd_plan_\w+_sgui"
    r"|nd_loose_sgui|nd_disavowing_sgui|nd_home_\w+_sgui|nd_risk_breakdown_sgui|nd_crisis_\w+_breakdown_sgui"
    r"|nd_crisis_next_pressure_sgui|nd_crisis_opponent_sgui|nd_last_crisis_sgui|nd_reach_\w+_sgui"
    r"|nd_posture_sgui|nd_crisis_action_sgui|nuclear_program_funding_sgui|nd_has_main_rival_sgui)\b")
# The true state's variables: the stockpile, the programme's progress and funding, readiness,
# survivability, command (reliability, strain, launch authority), the upkeep cached from the arsenal,
# the ceiling and dismantling, and custody (loose warheads, safeguards, hardening, the arsenal
# records, the custody transfers). A script value or scripted trigger that reads one, or reads one
# that does, is true state too (_true_state).
TRUE_VARS = re.compile(
    r"\b(nuclear_weapon_stockpile|nuclear_weapon_program_progress|nuclear_weapons_program_funding"
    r"|nd_readiness\w*|nd_survivability|nd_reliability|nd_strain|nd_authority|nd_upkeep_weekly_cached"
    r"|nd_warhead_ceiling|nd_dismantle_\w+|nd_safeguards|nd_hardening|nd_loose_\w+|nd_custody_\w+|nd_ar_\w+)\b")
# A bare name in a script body: a script value, trigger or scripted GUI it may call (not var:x, x.y).
_NAME_REF = re.compile(r"(?<![:.\w])([a-z_]\w*)\b")
# A key another country's panel renders that may name one of the estimate's two script values, and
# why it cannot leak. Both fall back to the live count while nd_public_estimate is unset, so a
# display reads nd_shown_public_estimate instead, and none is allowed today.
LEAK_SAFE = {}
ESTIMATE_VALUES = {"nd_believed_stockpile", "nd_display_public_estimate"}


@functools.lru_cache(maxsize=1)
def _true_state():
    """Every script value, scripted trigger and scripted GUI (by its
    is_shown) that reads a TRUE_VARS variable, directly or through script
    values and scripted triggers, at any depth."""
    graph = {**_scripts("script_values"), **_scripts("scripted_triggers")}
    for name, body in _scripts("scripted_guis").items():
        m = re.search(r"\bis_shown = \{", body)
        graph[name] = body[m.end():gh._close(body, m.end() - 1)] if m else ""
    refs = {n: (set(_NAME_REF.findall(b)) & graph.keys()) - {n} for n, b in graph.items()}
    out = {n for n, b in graph.items() if TRUE_VARS.search(b)}
    grew = True
    while grew:
        grew = False
        for n, r in refs.items():
            if n not in out and r & out:
                out.add(n)
                grew = True
    return frozenset(out)


@functools.lru_cache(maxsize=1)
def _leaks():
    """LEAKS, TRUE_VARS and every name _true_state derives, as one pattern."""
    derived = "|".join(sorted(map(re.escape, _true_state()), key=len, reverse=True))
    return re.compile(rf"{LEAKS.pattern}|{TRUE_VARS.pattern}|\b({derived})\b")


def _found(pattern, text):
    return sorted({m.group(0) for m in pattern.finditer(text)})


def _drawn(view, types, name):
    """A type's body as another country's panel draws it: its guarded parts
    blanked, and nothing at all for a root that collapses there."""
    body = gh.unguarded(types[name].body, view.skip.get(name, []))
    root_visible = [ln for ln in body.split("\n") if re.match(r'^\t\tvisible = ', ln)]
    if root_visible and _COLLAPSE.search(root_visible[0]):
        return ""
    return body


def _scripts(pattern):
    out = {}
    for path in glob.glob(os.path.join(REPO, "common", pattern, "*.txt")):
        text = gh._strip_comments(_read(path))
        for m in re.finditer(r"(?m)^(\w+) = \{", text):
            out[m.group(1)] = text[m.end() - 1:gh._close(text, m.end() - 1) + 1]
    return out


class PrivateTest(unittest.TestCase):
    """Both directions: what spec § 6.4 hides is under te_own_country_only, and
    what it shows is still drawn for another country (an over-guarded panel
    passes every binding test)."""

    @classmethod
    def setUpClass(cls):
        cls.types = gh.mod_types()
        cls.view = gh.panel_view({WIDE}, cls.types)
        cls.loc = gh.load_loc()
        cls.keys = gh.panel_loc_keys({WIDE}, cls.types, cls.loc)
        cls.markup = {n: _drawn(cls.view, cls.types, n) for n in cls.view.open}
        cls.leaks = _leaks()

    def test_the_hidden_sections_collapse(self):
        """The program, the goal bar, the crisis's readings and moves, Strike,
        Posture, Forces, At Home and Reputation: each root collapses for another
        country, and everything under it is guarded."""
        for name in COLLAPSED:
            with self.subTest(section=name):
                body = self.types[name].body
                self.assertIsNotNone(_root_visible(body), name)
                self.assertTrue(_COLLAPSE.search(f'visible = "[{_root_visible(body)}]"'),
                                f"{name}: its root is And( Country.IsLocalPlayer, <gate> )")
                drawn = gh.unguarded(body, self.view.skip[name])
                self.assertNotIn("{", drawn, f"{name}: a child outside te_own_country_only")
        # Delivery and Defence has no gate: its root takes the guard.
        delivery = self.types["te_nuclear_sec_delivery"].body
        self.assertIn("using = te_own_country_only", delivery)
        self.assertEqual(gh.unguarded(delivery, self.view.skip["te_nuclear_sec_delivery"]).strip(), "")
        for name in ("te_je_goal_bar", "nuclear_program_funding_row", "nd_choice_row", "nd_axis_row",
                     "nd_readiness_row", "nd_stepper_row", "nd_home_ig_table", "nd_crisis_cell", "nd_outcome_row"):
            self.assertNotIn(name, self.view.open, name)

    def test_the_overview_shows_the_estimate_not_the_count(self):
        ov = self.markup["te_nuclear_overview_panel"]
        for key in ("je_nuclear_ov_public_word", "je_nuclear_ov_public_figure", "je_nuclear_ov_public_tt",
                    "je_nuclear_ov_guarantees_word", "je_nuclear_ov_guarantees_figure",
                    "je_nuclear_ov_guarantees_tt", "je_nuclear_ov_crisis_label", "je_nuclear_ov_crisis_figure",
                    "je_nuclear_ov_crisis_tt_theirs", "je_nuclear_ov_taboo_value"):
            self.assertIn(key, ov, key)
        for key in ("je_nuclear_ov_warheads_label", "je_nuclear_ov_warheads_figure", "je_nuclear_ov_prog_tt",
                    "nd_w_doctrine_tt", "nd_w_readiness_tt", "nd_w_authority_tt", "nd_w_credibility_tt"):
            self.assertNotIn(key, ov, f"{key}: the player's own")
        self.assertIn('visible = "[Not( Country.IsLocalPlayer )]"', ov, "another country's row is its own")
        # The estimate is the seeded one, gated on a test: nothing before it, and never the live count.
        for key in ("je_nuclear_ov_public_count", "je_nuclear_ov_public_tt_known"):
            self.assertIn("ScriptValue('nd_shown_public_estimate')", self.loc[key], key)
        self.assertIn("nd_believed_armed_sgui", self.loc["je_nuclear_ov_public_word"])
        self.assertIn("nd_believed_armed = yes", _scripts("scripted_guis")["nd_believed_armed_sgui"])
        shown = _value_body("nd_shown_public_estimate")
        self.assertRegex(shown, r"value = 0\s+if = \{\s+limit = \{\s+nd_believed_armed = yes\s+"
                                r"has_variable = nd_public_estimate\s+\}\s+value = var:nd_public_estimate\s+\}")
        self.assertNotIn("nd_shown_public_estimate", _true_state())

    def test_the_public_parts_are_drawn(self):
        """Spec § 6.4's Shown column: the public estimate, crises, guarantees,
        and the world's own lists."""
        for name in ("te_nuclear_overview_panel", "te_banking_ov_cell", "te_nuclear_sec_world_crises",
                     "nd_world_crisis_row", "te_nuclear_sec_powers", "nuclear_program_power_row",
                     "te_nuclear_sec_taboo", "te_hist_nd_taboo", "te_hist_nd_taboo_tgt"):
            with self.subTest(type=name):
                self.assertIn(name, self.view.open)
                self.assertTrue(self.markup[name].strip(), f"{name} draws for another country")
        for key in ("je_nuclear_ov_public_count", "je_nuclear_ov_public_none", "je_nuclear_ov_public_tt_known",
                    "je_nuclear_ov_public_tt_none", "je_nuclear_ov_crisis_tt_theirs", "nd_crisis_stage_1",
                    "nd_public_guarantee_word_both", "nd_public_guarantee_word_none", "nd_public_guarantee_line_gives",
                    "nd_public_guarantee_line_holds", "je_nuclear_ov_guarantees_umbrella",
                    "nd_public_guarantee_figure_under", "nd_public_guarantee_figure_treaty",
                    "nd_w_world_crises_header", "nd_wc_item_stage", "nd_wc_item_danger",
                    "je_nuclear_program_widget_powers_header", "nuclear_program_power_estimate",
                    "je_nuclear_program_widget_taboo_score_value", "nd_taboo_hist_tt"):
            self.assertIn(key, self.keys, key)
        for key in ("je_nuclear_ov_crisis_tt", "je_nuclear_ov_warheads_tt", "nd_w_arsenal_value",
                    "je_nuclear_program_widget_taboo_burden_value", "je_nuclear_program_widget_taboo_strategic_value",
                    "nd_w_umbrella_value", "nd_w_loose_value"):
            self.assertNotIn(key, self.keys, f"{key}: the player's own")

    def test_nothing_drawn_reads_the_true_count(self):
        """No markup another country's panel draws, and no key it renders, reads
        the true stockpile, progress, funding, readiness or custody, or asks
        whether the country is armed (spec § 6.4's Hidden column)."""
        for name, text in sorted(self.markup.items()):
            with self.subTest(type=name):
                self.assertFalse(_found(self.leaks, text), "in another country's panel")
        for key in sorted(self.keys):
            with self.subTest(key=key):
                found = _found(self.leaks, self.loc[key])
                if key in LEAK_SAFE:
                    found = [f for f in found if f not in ESTIMATE_VALUES]
                self.assertFalse(found, "in another country's panel")
        self.assertFalse(set(LEAK_SAFE) - self.keys, "LEAK_SAFE names a key another country's panel no longer renders")
        # Nuclear Powers' rows show the seeded estimate, never the live count.
        self.assertIn("ScriptValue('nd_shown_public_estimate')", self.loc["nuclear_program_power_estimate"])

    def test_the_true_state_is_derived(self):
        """_true_state follows script values and triggers: what the stockpile
        feeds is true state, and what the world sees is not."""
        derived = _true_state()
        for name in ("nd_stockpile", "nd_stockpile_capped", "nd_public_estimate_observed", "nd_upkeep_size_factor",
                     "nd_is_armed", "nd_armed_sgui", "nd_believed_stockpile", "nd_display_public_estimate"):
            self.assertIn(name, derived, name)
        for name in ("nd_believed_armed", "nd_under_an_umbrella", "nd_protects_anyone", "nd_is_guaranteed",
                     "nd_believed_armed_sgui", "nd_shown_public_estimate", "nd_taboo_exists_sgui"):
            self.assertNotIn(name, derived, name)

    def test_no_custom_loc_asks_the_true_count(self):
        """The GetCustom calls another country's panel makes (the guarantees'
        word, figure and line; the crisis's stage and danger) pick their text
        on triggers. None of them, or of the scripted triggers they call, reads
        the true count or asks nd_is_armed: the umbrella asks nd_believed_armed,
        and treaties are public."""
        texts = list(self.markup.values()) + [self.loc[k] for k in self.keys]
        names = {n for t in texts for n in re.findall(r"GetCustom\(\s*'(\w+)'\s*\)", t)}
        self.assertTrue({"nd_public_guarantee_word", "nd_public_guarantee_figure", "nd_public_guarantee_line"} <= names)
        custom = _scripts("customizable_localization")
        calls = {**_scripts("scripted_triggers"), **_scripts("script_values")}
        for name in sorted(names):
            seen, todo = set(), [custom[name]]
            while todo:
                body = todo.pop()
                with self.subTest(custom=name):
                    self.assertFalse(_found(self.leaks, body))
                for called in set(_NAME_REF.findall(body)) & calls.keys():
                    if called not in seen:
                        seen.add(called)
                        todo.append(calls[called])
        self.assertIn("nd_believed_armed = yes", calls["nd_under_an_umbrella"])

    def test_no_chart_plots_a_stockpile(self):
        """Nuclear's charts are the taboo and its target, the world's: none plots
        an arsenal (scripts/generators/gen_te_history_charts.py's registry)."""
        from scripts.generators import gen_te_history_charts as charts
        self.assertEqual(sorted(c.id for c in charts.CHARTS if c.system == "nuclear_weapons"), ["nd_taboo", "nd_taboo_tgt"])
        fragment = _read(os.path.join(REPO, "scripts", "generators", "te_history_charts", "nuclear_weapons.gui.in"))
        self.assertEqual(set(re.findall(r"te_hist_v_\w+", fragment)), {"te_hist_v_nd_taboo", "te_hist_v_nd_taboo_tgt"})
        self.assertFalse(_found(_leaks(), fragment))
        self.assertEqual(sorted(n for n in self.view.open if n.startswith("te_hist_nd_")),
                         ["te_hist_nd_taboo", "te_hist_nd_taboo_tgt"])


class TooltipKeysTest(unittest.TestCase):
    """The keys a scripted GUI's effect prints into a hover (custom_tooltip)
    are invisible to test_te_system_tab_bodies.py's BindingTest and to the
    rebinding tool. Every handler another country's panel asks for a tooltip
    (ExecuteTooltip, IsValidTooltip, IsShownTooltip) prints keys that read no
    entry and no player (the root is the shown country), and nothing of the
    true count. The private sections' breakdowns are not asked there at all."""

    PUBLIC = {"nd_taboo_breakdown_sgui", "nd_world_crisis_item_detail_sgui"}
    PRIVATE = {"nd_risk_breakdown_sgui", "nd_crisis_pressure_breakdown_sgui", "nd_crisis_danger_breakdown_sgui",
               "nd_crisis_next_pressure_sgui", "nd_reach_list_sgui", "nd_plan_enemy_sgui", "nd_crisis_opponent_sgui",
               "nd_last_crisis_sgui", "nd_home_list_sgui", "nd_home_footer_sgui", "nd_posture_sgui",
               "nd_crisis_action_sgui", "nuclear_program_funding_sgui"}

    @classmethod
    def setUpClass(cls):
        cls.types = gh.mod_types()
        cls.view = gh.panel_view({WIDE}, cls.types)
        cls.loc = gh.load_loc()
        keys = gh.panel_loc_keys({WIDE}, cls.types, cls.loc)
        texts = [_drawn(cls.view, cls.types, n) for n in cls.view.open] + [cls.loc[k] for k in keys]
        asked = set()
        for text in texts:
            asked |= set(re.findall(r"GetScriptedGui\('(\w+)'\)\.(?:ExecuteTooltip|IsValidTooltip|IsShownTooltip)", text))
            if re.search(r"ScriptedGui\.(?:ExecuteTooltip|IsValidTooltip|IsShownTooltip)", text):
                asked |= set(re.findall(r"datacontext = \"\[GetScriptedGui\('(\w+)'\)\]\"", text))
        cls.asked = asked
        cls.sguis = _scripts("scripted_guis")
        cls.calls = {**_scripts("scripted_triggers"), **_scripts("scripted_effects")}

    def _printed(self, body, seen):
        """The loc keys a block prints: custom_tooltip keys and any loc key
        passed as a value (a helper's KEY = x), following the scripted effects
        and triggers it calls."""
        keys = {w for w in re.findall(r"=\s*(\w+)", body) if w in self.loc}
        for name in re.findall(r"\b(\w+)\s*=\s*(?:yes|\{)", body):
            if name in self.calls and name not in seen:
                seen.add(name)
                keys |= self._printed(self.calls[name], seen)
        return keys

    def test_the_handlers_another_country_asks(self):
        nd = {n for n in self.asked if n.startswith(("nd_", "nuclear_"))}
        self.assertEqual(nd, self.PUBLIC)
        self.assertFalse(self.asked & self.PRIVATE)

    def test_their_keys_read_no_entry_player_or_count(self):
        for name in sorted(self.asked):
            keys = gh.loc_closure(self._printed(self.sguis[name], set()), self.loc)
            self.assertTrue(keys, name)
            for key in sorted(keys):
                with self.subTest(sgui=name, key=key):
                    value = self.loc[key]
                    self.assertNotRegex(value, r"\b(?:GetPlayer|AccessPlayer|JournalEntry)\b")
                    self.assertFalse(_found(_leaks(), value))

    def test_the_tradition_line_reads_the_root(self):
        """nd_taboo_bd_tradition read GetPlayer for a constant: no country for an
        observer. It reads the handler's root, as covert_last_exposed_sgui's lines do."""
        self.assertIn("SCOPE.GetRootScope.ScriptValue('nd_taboo_tradition_cap')", self.loc["nd_taboo_bd_tradition"])


# An observer's gate: what a world read (`# world:`) needs, since an observer has no GetPlayer.
OBSERVER_GATE = re.compile(r"Not\( GetMetaPlayer\.IsObserver \)|GetPlayer\.IsValid")


def _observer_gated(body, pos):
    """Whether a body offset sits under an observer gate: on its own line, or
    on the `visible` of a block around it."""
    line = body[body.rfind("\n", 0, pos) + 1:body.find("\n", pos)]
    if OBSERVER_GATE.search(line):
        return True
    a, b = gh.enclosing_block(body, pos)
    while True:
        inside = body if (a, b) == (0, len(body)) else body[a + 1:b]
        if any(OBSERVER_GATE.search(v) for v in re.findall(r'visible = "[^"]*"', gh.own_props(inside))):
            return True
        if a == 0:
            return False
        a, b = gh.enclosing_block(body, a)


class ObserverTest(unittest.TestCase):
    """National Info opens this panel for an observer too, for whom GetPlayer is
    no country and Country.IsLocalPlayer is false for every country, so an
    observer sees another country's panel. A player read there logs every
    frame (gui_modding_guide.md, "An observer has no GetPlayer"). So nothing
    another country's panel draws reads the player or the entry, in markup or
    in a key it renders, but a world read (`# world:`), and a world read sits
    under Not( GetMetaPlayer.IsObserver ) or behind GetPlayer.IsValid. Nuclear
    has no world read: World Crises, Nuclear Powers and the taboo read global
    lists and variables."""

    @classmethod
    def setUpClass(cls):
        cls.types = gh.mod_types()
        cls.templates = gh.mod_templates()
        cls.reads = gh.markup_reads({WIDE}, cls.types, cls.templates)
        loc = gh.load_loc()
        cls.keys = gh.panel_loc_keys({WIDE}, cls.types, loc)
        cls.index = gh.loc_index()

    def test_every_world_read_is_gated(self):
        for f in self.reads:
            with self.subTest(read=str(f)):
                self.assertTrue(f.world, "a player read another country's panel draws")
                name = f.where.removeprefix("template ")
                td = (self.templates if f.where.startswith("template ") else self.types)[name]
                k = f.line - td.line
                pos = gh._line_starts(td.body)[k] + f.col - (td.col if k == 0 else 0)
                self.assertTrue(_observer_gated(td.body, pos), "a world read with no observer gate")

    def test_no_key_another_country_renders_reads_the_player(self):
        self.assertEqual([str(f) for f in gh.loc_reads(self.keys, self.index)], [])

    def test_the_gate_check(self):
        """_observer_gated finds a gate on the read's line or on a block around
        it, and none elsewhere."""
        gated = 'a = {\n\tvisible = "[Not( GetMetaPlayer.IsObserver )]"\n\tb = {\n\t\ttext = "[GetPlayer.GetName]"\n\t}\n}'
        self.assertTrue(_observer_gated(gated, gated.index("GetPlayer.GetName")))
        sibling = 'a = {\n\tb = {\n\t\tvisible = "[Not( GetMetaPlayer.IsObserver )]"\n\t}\n\tc = {\n\t\ttext = "[GetPlayer.GetName]"\n\t}\n}'
        self.assertFalse(_observer_gated(sibling, sibling.index("GetPlayer.GetName")))
        inline = 'a = {\n\ttext = "[GetPlayer.IsValid]"\n}'
        self.assertTrue(_observer_gated(inline, inline.index("GetPlayer.IsValid")))


if __name__ == "__main__":
    unittest.main()
