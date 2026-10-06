"""The Grand Monuments panel: section order, collapse defaults, state-gated
lines, icons and display values (style pass 2026-09-29,
docs/guides/gui_style_guide.md; the UN's test_un_layout.py is the model).

Run: python3 -m unittest test_grand_monuments_layout -v
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "grand_monuments_widget.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_grand_monuments.txt")
VALUES = os.path.join(REPO, "common", "script_values", "gm_values.txt")
COM_VALUES = os.path.join(REPO, "common", "script_values", "gm_commission_values.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "gm_sguis.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "gm_effects.txt")
LOC = os.path.join(REPO, "localization", "english", "te_miscellaneous_l_english.yml")
ICONS_DOC = os.path.join(REPO, "docs", "systems", "grand_monuments_gui_icons.md")
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
CONCEPT_LOC = os.path.join(REPO, "localization", "english", "te_concepts_l_english.yml")

STATUS = ["te_gm_sec_commission", "te_gm_sec_national", "te_gm_sec_monuments"]
REFERENCE = ["te_gm_sec_how"]
# root -> (container, what it wraps)
ROOTS = {"widget_je_gm_overview": ("custom_widget_container_1", "te_gm_overview_panel"),
         "widget_je_gm_status": ("custom_widget_container_2", "te_gm_status_sections"),
         "widget_je_gm_reference": ("custom_widget_container_3", "te_gm_reference_sections")}
FLAGS = {"gm_commission_closed", "gm_national_closed", "gm_monuments_closed", "gm_how_open"}
LIVE_SECTIONS = ["te_gm_overview_panel", "te_gm_sec_commission", "te_gm_sec_national", "te_gm_sec_monuments",
                 "gm_monument_row"]
HOW_KEYS = ["gm_je_how_grandeur", "gm_je_how_grandeur_national", "gm_je_how_counts",
            "gm_je_how_counts_other", "gm_je_how_contested", "gm_je_how_choices",
            "gm_je_how_hard_times", "gm_je_how_commissions", "gm_je_how_commissions_rewards",
            "gm_je_how_names", "gm_je_how_policy"]
# The fading ledgers under National Effects' Fading Legitimacy (v1 §4.3, §5; v2 §2.4).
FADING = ("teardown", "vanity", "promise")
# Dedications with a national effect of their own: shown only while in force.
SPECIFIC = ("leader", "religious", "war_memorial", "artistic", "scientific", "industrial")
IGS = ("armed_forces", "devout", "industrialists", "intelligentsia", "landowners",
       "petty_bourgeoisie", "rural_folk", "trade_unions")
# The bars: row key -> the gm_set_steps OUT/NEXT suffix it follows.
FRACS = {"prestige": "standing", "legitimacy": "regime", "culture": "culture",
         "leader": "leader", "religious": "religious", "war_memorial": "war_memorial",
         "artistic": "artistic", "scientific": "scientific", "industrial": "industrial"}

# The panel's icons (docs/systems/grand_monuments_gui_icons.md; the art is
# PR #586's): status code or cell -> texture. Remaking one keeps its file
# name, so neither this table nor the widget changes.
_GM = "gfx/interface/icons/gm_icons"
ICONS = {1: f"{_GM}/status_undedicated.dds",
         2: f"{_GM}/status_upheld.dds",
         3: f"{_GM}/status_heritage.dds",
         4: f"{_GM}/status_contested.dds",
         "hard_times": f"{_GM}/hard_times.dds"}
# The overview's four status cells: count value -> status code (for its icon).
CELLS = {"gm_disp_count_undedicated": 1, "gm_disp_count_upheld": 2,
         "gm_disp_count_heritage": 3, "gm_disp_count_contested": 4}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    """Drop each line's comment: from a `#` outside quotes to the line end."""
    out = []
    for line in text.split("\n"):
        quoted = False
        for i, ch in enumerate(line):
            if ch == '"':
                quoted = not quoted
            elif ch == "#" and not quoted:
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def _match_brace(text, open_end):
    depth, i = 1, open_end
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[open_end:i - 1]


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return _match_brace(text, m.end())


def _root_body(text, name):
    m = re.search(rf"(?m)^flowcontainer = \{{\n\tname = \"{name}\"", text)
    assert m, f"no root {name}"
    return _match_brace(text, text.index("{", m.start()) + 1)


def _block(text, name):
    m = re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*\{", _strip_comments(text))
    return _match_brace(_strip_comments(text), m.end()) if m else None


def _squash(text):
    return " ".join((text or "").split())


def _loc():
    out = {}
    for line in _read(LOC).splitlines():
        m = re.match(r'\s*([\w.]+):\d*\s+"(.*)"\s*$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def _gui():
    return _read(GUI)


class OrderTest(unittest.TestCase):
    def test_composers_set_the_order(self):
        gui = _gui()
        for composer, expected in (("te_gm_status_sections", STATUS),
                                   ("te_gm_reference_sections", REFERENCE)):
            found = re.findall(r"^\t\t(te_gm_sec_\w+) = \{", _type_body(gui, composer), re.M)
            self.assertEqual(found, expected, composer)

    def test_roots_are_gated_wrappers_the_entry_mounts(self):
        gui, je = _gui(), _squash(_read(JE))
        for root, (container, inner) in ROOTS.items():
            body = _root_body(gui, root)
            self.assertIn('visible = "[JournalEntry.IsActive]"', body, root)
            self.assertIn(f"{inner} = {{}}", body, root)
            self.assertIn(f'name = "{root}" container = "{container}"', je, root)
            self.assertIn('visible = "[JournalEntry.IsActive]"', _type_body(gui, inner), inner)
        self.assertEqual(len(re.findall(r'(?m)^\tname = "', gui)), len(ROOTS))


class FlagTest(unittest.TestCase):
    """Collapse flags say their default: _closed open until closed, _open
    collapsed until opened (style rule 7)."""

    def test_flags_say_their_default(self):
        text = _strip_comments(_gui())
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", text))
        self.assertEqual(flags, FLAGS)
        for f in flags:
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", text))
            bare = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", text)) - negated
            if f.endswith("_closed"):   # shown unless closed: one bare (show-more), the rest negated
                self.assertEqual((bare, negated), (1, 2), f)
            else:                        # shown only when opened: one negated (show-more)
                self.assertEqual((negated, bare), (1, 2), f)

    def test_each_section_owns_its_flag(self):
        gui = _gui()
        for sec, flag in (("te_gm_sec_national", "gm_national_closed"),
                          ("te_gm_sec_monuments", "gm_monuments_closed"),
                          ("te_gm_sec_how", "gm_how_open")):
            self.assertIn(f"GetVariableSystem.Toggle('{flag}')", _type_body(gui, sec), sec)


class HowItWorksTest(unittest.TestCase):
    def test_explanations_live_in_how_it_works(self):
        gui = _gui()
        how = _type_body(gui, "te_gm_sec_how")
        for key in HOW_KEYS:
            self.assertIn(f'"{key}"', how, key)
        for sec in LIVE_SECTIONS:
            body = _type_body(gui, sec)
            self.assertNotIn("gm_je_how_", body, sec)
            self.assertNotIn("gm_note", body, f"{sec} carries an explanatory note")

    def test_every_how_key_exists_and_reads_nothing(self):
        loc = _loc()
        for key in HOW_KEYS:
            self.assertIn(key, loc)
            self.assertNotIn("ScriptValue", loc[key], key)

    def test_the_contest_line_is_brief_with_the_reason_on_hover(self):
        loc = _loc()
        self.assertIn("It honours something this government is not", loc["gm_row_contest_tt"])
        self.assertNotIn("It honours", loc["gm_row_contest"])
        self.assertIn('tooltip = "gm_row_contest_tt"', _type_body(_gui(), "gm_monument_row"))

    def test_the_hard_times_sentence_is_the_cells_tooltip(self):
        loc = _loc()
        self.assertNotIn("gm_je_hard_times", loc)
        self.assertIn("Pause monument construction", loc["gm_je_ov_hard_times_tt"])


class StateGatedTest(unittest.TestCase):
    CONTESTED = "EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_status_code'), '(CFixedPoint)4' )"

    def test_contest_line_and_buttons_only_while_contested(self):
        row = _squash(_type_body(_gui(), "gm_monument_row"))
        self.assertIn(f'visible = "[{self.CONTESTED}]" default_format = "#tooltippable" '
                      f'tooltip = "gm_row_contest_tt" text = "gm_row_contest"', row)
        rows = re.findall(r'flowcontainer = \{ direction = horizontal spacing = 4 parentanchor = hcenter '
                          r'visible = "\[(.*?)\]" ((?:gm_choice_button = \{.*?\} \} )+)\}', row)
        self.assertEqual(len(rows), 2, "Rename's row and the contested choices' row, each centred")
        gates = dict(rows)
        self.assertEqual(gates[self.CONTESTED].count("gm_choice_button = {"), 3)
        self.assertNotIn("gm_rename_sgui", gates[self.CONTESTED])

    def test_rename_only_while_upheld(self):
        """A contested or heritage monument keeps its name (v2 §3.3): Rename
        shows only while the monument fits, and its scripted GUI says so."""
        row = _squash(_type_body(_gui(), "gm_monument_row"))
        upheld = "EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_state_can_rename'), '(CFixedPoint)1' )"
        self.assertIn(f'visible = "[{upheld}]" gm_choice_button = {{ blockoverride "choice_context" '
                      f'{{ datacontext = "[GetScriptedGui(\'gm_rename_sgui\')]" }}', row)
        value = _squash(_block(_read(VALUES), "gm_state_can_rename"))
        self.assertEqual(value, "value = 0 if = { limit = { gm_state_status_fits = yes } value = 1 }")
        sgui = _squash(_block(_read(SGUIS), "gm_rename_sgui"))
        self.assertIn("gm_state_status_fits = yes", sgui)
        self.assertIn("ai_is_valid = { always = no }", sgui)

    def test_hard_times_only_while_it_holds(self):
        """The icon over a red phrase, both explaining on hover, in a line of
        its own under the cells with every width fixed (play-test round 2)."""
        ov = _squash(_strip_comments(_type_body(_gui(), "te_gm_overview_panel")))
        m = re.search(r'flowcontainer = \{ direction = vertical ignoreinvisible = yes spacing = 2 '
                      r'minimumsize = \{ 480 -1 \} margin_top = 4 visible = "\[GetScriptedGui\(\'gm_hard_times_sgui\'\)'
                      r'\.IsShown\( GuiScope\.SetRoot\( JournalEntry\.GetCountry\.MakeScope \)\.End \)\]" (.*)', ov)
        self.assertTrue(m, "no pinned Hard Times line")
        line = m.group(1)
        self.assertRegex(line, r'^icon = \{ size = \{ 32 32 \} parentanchor = hcenter tooltip = "gm_je_ov_hard_times_tt"')
        self.assertIn('minimumsize = { 480 -1 } maximumsize = { 480 -1 } align = hcenter|nobaseline using = fontsize_large '
                      'default_format = "#tooltippable" tooltip = "gm_je_ov_hard_times_tt" text = "gm_je_ov_hard_times"', line)
        loc = _loc()
        self.assertTrue(loc["gm_je_ov_hard_times"].startswith("#R "), "the phrase is red")
        self.assertLessEqual(len(loc["gm_je_ov_hard_times"].split()), 4, "a couple of words")

    def test_the_cell_row_never_changes_width(self):
        """Four fixed cells, none gated: a row whose width comes from its
        content is centred by the width it had at first layout."""
        ov = _squash(_strip_comments(_type_body(_gui(), "te_gm_overview_panel")))
        row = re.search(r"flowcontainer = \{ direction = horizontal spacing = \d+ ignoreinvisible = yes "
                        r"parentanchor = hcenter (.*?) \} flowcontainer = \{ direction = vertical", ov)
        self.assertTrue(row)
        self.assertEqual(row.group(1).count("gm_ov_cell = {"), 4)
        self.assertNotRegex(row.group(1), r"gm_ov_cell = \{ visible")

    def test_every_total_only_while_in_force(self):
        """Zero rows hide, prestige, legitimacy and cultural pull included
        (owner, play-test round 2)."""
        nat = _squash(_type_body(_gui(), "te_gm_sec_national"))
        for key in FRACS:
            self.assertIn(f"gm_step_row = {{ visible = \"[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope"
                          f".ScriptValue('gm_display_{key}'), '(CFixedPoint)0' )]\" tooltip = \"gm_je_tt_{key}\"",
                          nat, key)
        for ig in IGS:
            self.assertIn(f"gm_value_row = {{ visible = \"[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope"
                          f".ScriptValue('gm_display_ig_{ig}'), '(CFixedPoint)0' )]\"", nat, ig)

    def test_headings_over_groups_that_can_be_empty_carry_the_groups_gate(self):
        nat = _squash(_type_body(_gui(), "te_gm_sec_national"))
        self.assertIn("gm_subheader = { visible = \"[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope"
                      ".ScriptValue('gm_disp_ig_any'), '(CFixedPoint)1' )]\"", nat)
        fading = re.search(r'gm_subheader = \{ visible = "\[Or\((.*?)\)\]" blockoverride "subheader_text" '
                           r'\{ text = "gm_je_sub_fading" \}', nat)
        self.assertTrue(fading)
        for ledger in FADING:
            self.assertIn(f"ScriptValue('gm_display_{ledger}')", fading.group(1))

    def test_sections_never_start_empty(self):
        gui = _gui()
        # National Effects opens on its empty-state line when nothing is in
        # force (test_the_empty_state_covers_every_row holds the gate).
        panel = _squash(_strip_comments(_type_body(gui, "te_gm_sec_national")).split("gm_panel = {", 1)[1])
        self.assertTrue(panel.startswith('visible = "[Not(GetVariableSystem.Exists(\'gm_national_closed\'))]" '
                                         'spacing = 2 gm_text = { visible = "[EqualTo_CFixedPoint( JournalEntry.GetCountry'
                                         '.MakeScope.ScriptValue(\'gm_disp_national_any\'), \'(CFixedPoint)0\' )]" '
                                         'text = "gm_je_national_none" }'), panel[:300])
        # Our Monuments: the empty-state line shows exactly when the list is empty.
        mon = _squash(_type_body(gui, "te_gm_sec_monuments"))
        self.assertIn("gm_text = { visible = \"[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope"
                      ".ScriptValue('gm_display_count'), '(CFixedPoint)0' )]\" text = \"gm_je_monuments_none\" }", mon)
        # How it Works: the first heading drops its top margin.
        how = _squash(_type_body(gui, "te_gm_sec_how").split("gm_panel = {", 1)[1])
        self.assertIn('gm_subheader = { blockoverride "subheader_margin" {} blockoverride "subheader_text" '
                      '{ text = "gm_je_how_sub_grandeur" } }', how.split("gm_note", 1)[0])


class PolicyLayoutTest(unittest.TestCase):
    """The monument policy (v2 §5): its name on the overview's last line,
    the four buttons at the foot of National Effects, two to a row."""

    def test_the_overview_names_the_policy(self):
        ov = _squash(_strip_comments(_type_body(_gui(), "te_gm_overview_panel")))
        self.assertIn('default_format = "#tooltippable" tooltip = "gm_je_ov_policy_tt" text = "gm_je_ov_policy" }', ov)

    def test_four_buttons_two_to_a_row(self):
        nat = _squash(_type_body(_gui(), "te_gm_sec_national"))
        tail = nat.split('text = "gm_je_sub_policy"', 1)[1]
        rows = re.findall(r"flowcontainer = \{ direction = horizontal spacing = 8 parentanchor = hcenter "
                          r"((?:gm_policy_button = \{.*?\} \} )+)\}", tail)
        self.assertEqual([r.count("gm_policy_button = {") for r in rows], [2, 2])
        order = re.findall(r"GetScriptedGui\('gm_policy_(\w+)_sgui'\)", tail)
        self.assertEqual(order, ["standard", "open", "ceremonial", "mothballed"])
        button = _squash(_type_body(_gui(), "gm_policy_button"))
        self.assertIn("size = { 230 24 }", button)


class NationalEmptyStateTest(unittest.TestCase):
    def test_the_empty_state_covers_every_row(self):
        """gm_disp_national_any is 1 exactly when some row of National Effects
        shows: every gm_display_* a row is gated on reads a variable the value
        tests, and gm_disp_ig_any's variables are in it too."""
        values = _read(VALUES)
        nat = _type_body(_gui(), "te_gm_sec_national")
        anyv = _squash(_block(values, "gm_disp_national_any"))
        gates = set(re.findall(r"ScriptValue\('(gm_display_\w+)'\), '\(CFixedPoint\)0' \)", nat))
        self.assertEqual(len(gates), len(FRACS) + len(IGS) + len(FADING))
        for display in gates:
            read_vars = set(re.findall(r"var:(\w+)", _block(values, display)))
            self.assertEqual(len(read_vars), 1, display)
            var = read_vars.pop()
            self.assertIn(f"AND = {{ has_variable = {var} NOT = {{ var:{var} = 0 }} }}", anyv, display)
        for var in re.findall(r"has_variable = (\w+)", _block(values, "gm_disp_ig_any")):
            self.assertIn(f"has_variable = {var} ", anyv, var)


class ConceptsTest(unittest.TestCase):
    """Contested and Heritage are concepts (owner, play-test round 2)."""
    NAMES = ("contested_monument", "heritage_monument")

    def test_defined_beside_grandeur_with_name_and_desc(self):
        concepts = _strip_comments(_read(CONCEPTS))
        tail = concepts[concepts.index("concept_grandeur = {"):]
        loc = {}
        for line in _read(CONCEPT_LOC).splitlines():
            m = re.match(r'\s*([\w.]+):\d*\s+"(.*)"\s*$', line)
            if m:
                loc[m.group(1)] = m.group(2)
        for name in self.NAMES:
            self.assertRegex(tail, rf"(?m)^concept_{name} = \{{", name)
            self.assertIn(f"concept_{name}", loc)
            self.assertIn(f"concept_{name}_desc", loc)

    def test_used_in_the_words_and_how_it_works(self):
        loc = _loc()
        for key, name in (("gm_je_ov_heritage", "heritage"), ("gm_je_ov_contested_none", "contested"),
                          ("gm_je_ov_contested_some", "contested"), ("gm_status_heritage", "heritage"),
                          ("gm_status_contested", "contested"), ("gm_je_how_contested", "contested"),
                          ("gm_je_how_contested", "heritage"), ("gm_je_how_counts_other", "heritage")):
            self.assertIn(f"Concept('concept_{name}_monument',", loc[key], key)


class StatusWordTest(unittest.TestCase):
    def test_the_fitting_status_is_upheld(self):
        """"Stands" became "Upheld" (owner, play-test round 3): the cell's
        caption, the rows' word and the status tooltip's title."""
        loc = _loc()
        self.assertTrue(loc["gm_je_ov_upheld"].startswith("Upheld #v "))
        self.assertEqual(loc["gm_status_fits"], "#G Upheld#!")
        self.assertTrue(loc["gm_je_status_upheld_tt"].startswith("#b Upheld#!"))
        for key, value in loc.items():
            if key.startswith(("gm_je_", "gm_row_", "gm_status_")):
                self.assertNotRegex(value, r"\bStands\b", key)


class IconsTest(unittest.TestCase):
    def test_row_status_icons_follow_the_code(self):
        row = _squash(_type_body(_gui(), "gm_monument_row"))
        found = re.findall(r"gm_row_status = \{ visible = \"\[EqualTo_CFixedPoint\( State\.MakeScope\.ScriptValue"
                           r"\('gm_status_code'\), '\(CFixedPoint\)(\d)' \)\]\" tooltip = \"(\w+)\" "
                           r"blockoverride \"status_texture\" \{ texture = \"([^\"]+)\" \}", row)
        self.assertEqual({int(c): t for c, _, t in found}, {k: v for k, v in ICONS.items() if isinstance(k, int)})

    def test_overview_cells_light_on_their_count(self):
        ov = _squash(_type_body(_gui(), "te_gm_overview_panel"))
        for value, code in CELLS.items():
            gt = (f"GreaterThan_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('{value}'), "
                  f"'(CFixedPoint)0' )")
            cell = re.search(r'blockoverride "cell_texture" \{ texture = "([^"]+)" \} '
                             r'blockoverride "lit" \{ visible = "\[' + re.escape(gt) + r'\]" \} '
                             r'blockoverride "unlit" \{ visible = "\[Not\( ' + re.escape(gt) + r' \)\]" \}', ov)
            self.assertTrue(cell, value)
            self.assertEqual(cell.group(1), ICONS[code], value)
        hard = re.search(r'tooltip = "gm_je_ov_hard_times_tt" texture = "([^"]+)" \}', ov)
        self.assertEqual(hard.group(1), ICONS["hard_times"])

    def test_every_icon_is_the_mods_own_and_listed(self):
        """The #586 art is wired: every texture in the widget is a
        gm_icons file in ICONS, and the icon list records each one. No vanilla
        placeholder is left."""
        doc = _read(ICONS_DOC)
        for path in set(ICONS.values()):
            self.assertIn(f"`{os.path.basename(path)}`", doc, path)
        self.assertIn(f"`{_GM}/`", doc)
        gui_textures = set(re.findall(r'texture = "([^"]+)"', _strip_comments(_gui())))
        self.assertEqual(gui_textures, set(ICONS.values()), "a texture in the widget is not in ICONS")
        self.assertNotIn("generic_icons", _strip_comments(_gui()), "a vanilla placeholder is left")


class DisplayValuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES) + "\n" + _read(COM_VALUES)
        cls.loc = _loc()
        gui = _gui()
        keys = set(re.findall(r'(?:text|tooltip) = "([a-z]\w*)"', gui))
        keys |= set(re.findall(r"'(gm_je_\w+)'", gui))
        cls.shown = gui + "\n".join(cls.loc.get(k, "") for k in keys)

    def test_every_disp_value_exists_and_guards_its_reads(self):
        used = set(re.findall(r"ScriptValue\('(gm_disp_\w+)'\)", self.shown))
        self.assertTrue(used)
        for name in used:
            body = _block(self.values, name)
            self.assertIsNotNone(body, name)
            for var in set(re.findall(r"var:(\w+)", body)):
                self.assertIn(f"has_variable = {var}", body, f"{name} reads var:{var} unguarded")

    def test_status_counts_follow_the_status_codes_precedence(self):
        for name in ("gm_disp_count_upheld", "gm_disp_count_heritage", "gm_disp_count_undedicated"):
            self.assertIn("gm_state_is_contested = no", _squash(_block(self.values, name)), name)
        for name in ("gm_disp_count_upheld", "gm_disp_count_undedicated"):
            self.assertIn("gm_state_is_heritage = no", _squash(_block(self.values, name)), name)
        self.assertIn("gm_state_is_dedicated = yes", _squash(_block(self.values, "gm_disp_count_upheld")))
        self.assertIn("gm_state_is_dedicated = no", _squash(_block(self.values, "gm_disp_count_undedicated")))
        self.assertIn("gm_state_is_contested = yes", _squash(_block(self.values, "gm_disp_count_contested")))

    def test_each_bar_follows_its_curve(self):
        """A bar's first step f and variables must be its gm_set_steps call's."""
        totals = _squash(_block(_read(EFFECTS), "gm_compute_totals"))
        calls = {m.group(3): (m.group(1), int(m.group(4))) for m in re.finditer(
            r"gm_set_steps = \{ IN = (gm_\w+) OUT = gm_s_(\w+) NEXT = gm_n_(\w+) F = (\d+) \}", totals)}
        gui = _gui()
        for row, suffix in FRACS.items():
            self.assertIn(f"ScriptValue('gm_disp_frac_{row}')", gui, row)
            source, f = calls[suffix]
            body = _squash(_block(self.values, f"gm_disp_frac_{row}"))
            self.assertIn(f"value = var:{source} multiply = 2 subtract = var:gm_n_{suffix} add = {f} "
                          f"divide = {{ value = var:gm_n_{suffix} add = {f} }}", body, row)
            self.assertTrue(body.endswith("min = 0 max = 1"), row)

    def test_the_bar_formula_matches_the_curve(self):
        """(2G - N + f) / (N + f) is 0 where a step begins and 1 where it ends,
        for the step ends gm_curve_next_f* returns."""
        for f in (5, 10):
            body = _squash(_block(self.values, f"gm_curve_next_f{f}"))
            ends = sorted(int(n) for n in re.findall(r"var:gm_curve_in < \d+ \} value = (\d+)", body))
            last = int(re.match(r"value = (\d+)", body).group(1))

            def nxt(g):
                return next((e for e in ends if g < e), last)
            start = 0
            for end in ends:
                for g in (start, (start + end) / 2):
                    n = nxt(g)
                    self.assertEqual(n, end, (f, g))
                frac = lambda g: (2 * g - nxt(g) + f) / (nxt(g) + f)
                self.assertAlmostEqual(frac(start), 0.0, msg=(f, start))
                self.assertAlmostEqual(frac((start + end) / 2), 0.5, msg=(f, start, end))
                self.assertAlmostEqual(frac(end - 1e-9), 1.0, places=6, msg=(f, end))
                start = end


class StatusDescTest(unittest.TestCase):
    def test_no_status_line_repeats_the_overview(self):
        """The status description's counts were the overview's (owner,
        play-test round 2)."""
        self.assertNotIn("status_desc", _strip_comments(_read(JE)))


class TidinessTest(unittest.TestCase):
    def test_no_panel_loc_starts_or_ends_with_a_newline(self):
        for key, value in _loc().items():
            if key.startswith(("gm_je_", "gm_row_")):
                self.assertFalse(value.startswith("\\n") or value.endswith("\\n"), key)

    def test_every_rendered_key_exists(self):
        loc, gui = _loc(), _gui()
        keys = set(re.findall(r'(?:text|tooltip) = "([a-z]\w*)"', gui)) | set(re.findall(r"'(gm_je_\w+)'", gui))
        for key in keys:
            self.assertIn(key, loc, key)

    def test_rows_are_the_panels_width(self):
        """Fixed widths, so no cell can widen its row (style rule 8)."""
        gui = _gui()
        for name in ("gm_step_row", "gm_value_row"):
            body = _type_body(gui, name)
            widths = [int(w) for w in re.findall(r"\b(?:minimumsize|size) = \{ (\d+) ", body)]
            margin = int(re.search(r"margin = \{ (\d+) ", body).group(1))
            spacing = re.search(r"^\t\tspacing = (\d+)", body, re.M)
            gaps = int(spacing.group(1)) * (len(widths) - 1) if spacing else 0
            self.assertEqual(sum(widths) + gaps + 2 * margin, 480, name)
        row = _type_body(gui, "gm_monument_row")
        self.assertEqual(int(re.search(r"size = \{ (\d+) ", _type_body(gui, "gm_row_status")).group(1)) + 8
                         + int(re.search(r"minimumsize = \{ (\d+) ", _type_body(gui, "gm_row_line")).group(1)), 480)
        self.assertIn("spacing = 8", row)
        cell = int(re.search(r"size = \{ (\d+) ", _type_body(gui, "gm_ov_cell")).group(1))
        ov = _squash(_type_body(gui, "te_gm_overview_panel"))
        gap = int(re.search(r"flowcontainer = \{ direction = horizontal spacing = (\d+) ", ov).group(1))
        self.assertLessEqual(4 * cell + 3 * gap, 480)


# ---- Play-test round 3: nothing a player reads may end in "..." ----------
# Units per character of each font, plus a 10% margin. Large and medium were
# measured from the owner's screenshots (round-3 rules); small is an estimate,
# 0.85 of medium, until it is measured.
UNITS = {"fontsize_large": 10.0, "fontsize_medium": 8.6, "fontsize_small": 7.3}
MARGIN = 1.1
VANILLA_LOC = os.path.join(REPO, "vanilla_parsed", "localization_english.json")
CUSTOM_LOC = os.path.join(REPO, "common", "customizable_localization", "gm_custom_loc.txt")
# The longest a number printed in a cell can be: counts reach two digits, and
# no effect or ledger value is wider than "+1000.0".
LONGEST_COUNT = "99"
LONGEST_VALUE = "1000.0"


def _all_loc():
    import json
    loc = {}
    with open(VANILLA_LOC, encoding="utf-8") as f:
        loc.update(json.load(f))
    for path in sorted(os.listdir(os.path.dirname(LOC))):
        if path.endswith(".yml"):
            for line in _read(os.path.join(os.path.dirname(LOC), path)).splitlines():
                m = re.match(r'\s*([\w.]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    loc[m.group(1)] = m.group(2)
    return loc


def _rendered(value, loc, data):
    """The text a loc value shows: $splices$ and concept links resolved to
    their words, a text icon counted as two characters, every data expression
    replaced by `data`, formatting codes dropped."""
    for _ in range(6):
        value = re.sub(r"\$(\w+)\$", lambda m: loc.get(m.group(1), m.group(0)), value)
        value = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", r"\1", value)
        value = re.sub(r"\[(concept_\w+)\]", lambda m: loc[m.group(1)], value)
    value = value.replace("[Nbsp]", " ")
    value = re.sub(r"@\w+!", "XX", value)
    value = re.sub(r"\[[^\[\]]*\]", data, value)
    value = re.sub(r"#[\w;:.,']+ ", "", value)
    return value.replace("#!", "")


def _cells(body):
    """(width, font) of each fixed-width textbox in a type, in order."""
    out = []
    for m in re.finditer(r"textbox = \{", body):
        tb = _match_brace(body, m.end())
        width = re.search(r"(?:maximumsize = \{ |max_width = )(\d+)", tb)
        font = re.search(r"using = (fontsize_\w+)", tb)
        if width and font:
            out.append((int(width.group(1)), font.group(1)))
    return out


class LabelBudgetTest(unittest.TestCase):
    """Every label in a fixed-width cell fits it: characters x units per
    character x 1.1 <= the cell's width (play-test round 3, rule 1). The
    effect rows' labels are static words; each row's tooltip names the full,
    country-dependent modifier name."""

    @classmethod
    def setUpClass(cls):
        cls.loc = _all_loc()
        cls.gui = _gui()

    def _fits(self, key, cell, data=""):
        width, font = cell
        text = _rendered(self.loc[key], self.loc, data)
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, width, f"{key}: {text!r} needs {need:.0f} of {width} ({font})")

    def test_effect_rows(self):
        nat = _squash(_type_body(self.gui, "te_gm_sec_national"))
        label, value = _cells(_type_body(self.gui, "gm_step_row"))
        steps = re.findall(r'gm_step_row = \{.*?"row_label" \{ text = "(\w+)" \}.*?"row_value" \{ text = "(\w+)" \}', nat)
        self.assertEqual(len(steps), len(FRACS))
        for lbl, val in steps:
            self._fits(lbl, label)
            self._fits(val, value, LONGEST_VALUE)
        label, value = _cells(_type_body(self.gui, "gm_value_row"))
        rows = re.findall(r'gm_value_row = \{.*?"row_label" \{ text = "(\w+)" \}.*?"row_value" \{ text = "(\w+)" \}', nat)
        self.assertEqual(len(rows), len(IGS) + len(FADING))
        for lbl, val in rows:
            self._fits(lbl, label)
            self._fits(val, value, LONGEST_VALUE)

    def test_the_flagged_labels_are_short(self):
        """The owner saw these two overrun (round 3)."""
        for key, words in (("gm_je_lbl_artistic", "Intelligentsia Attraction"),
                           ("gm_je_lbl_scientific", "Max Innovation")):
            self.assertEqual(_rendered(self.loc[key], self.loc, ""), words)
        for key, modifier in (("gm_je_tt_artistic", "interest_group_ig_intelligentsia_pop_attraction_mult"),
                              ("gm_je_tt_scientific", "country_weekly_innovation_max_add"),
                              ("gm_je_tt_religious", "interest_group_ig_devout_pop_attraction_mult"),
                              ("gm_je_tt_industrial", "interest_group_ig_industrialists_pop_attraction_mult"),
                              ("gm_je_tt_war_memorial", "country_war_support_casualties_mult")):
            self.assertTrue(self.loc[key].startswith(f"#b ${modifier}$#!"), f"{key} lost the full name")

    def test_overview_captions(self):
        (cell,) = _cells(_type_body(self.gui, "gm_ov_cell"))
        ov = _type_body(self.gui, "te_gm_overview_panel")
        keys = set(re.findall(r'"label" \{\s*text = "(\w+)"', ov)) | set(re.findall(r"'(gm_je_ov_\w+)'", ov))
        self.assertEqual(len(keys), 5)
        for key in keys:
            self._fits(key, cell, LONGEST_COUNT)

    def test_row_status_words(self):
        """The row's word is custom loc: the longest word it can pick."""
        (cell,) = _cells(_type_body(self.gui, "gm_row_status"))
        words = re.findall(r"localization_key = (\w+)", _block(_read(CUSTOM_LOC), "gm_status_name"))
        self.assertEqual(len(words), 5)
        for key in words:
            self._fits(key, cell)

    def test_choice_buttons(self):
        (cell,) = _cells(_type_body(self.gui, "gm_choice_button"))
        keys = re.findall(r'"choice_text" \{ text = "(\w+)" \}', _type_body(self.gui, "gm_monument_row"))
        self.assertEqual(len(keys), 4, "Rename and the three contested choices")
        for key in keys:
            self._fits(key, cell)

    def test_policy_buttons(self):
        (cell,) = _cells(_type_body(self.gui, "gm_policy_button"))
        keys = re.findall(r'"policy_text" \{ text = "(\w+)" \}', _type_body(self.gui, "te_gm_sec_national"))
        self.assertEqual(len(keys), 4)
        for key in keys:
            self._fits(key, cell)

    def test_hard_times_phrase(self):
        self._fits("gm_je_ov_hard_times", (480, "fontsize_large"))


if __name__ == "__main__":
    unittest.main()
