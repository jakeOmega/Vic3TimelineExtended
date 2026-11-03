"""The Grand Monuments panel: section order, collapse defaults, state-gated
lines, icons and display values (style pass 2026-09-29,
docs/guides/gui_style_guide.md; the UN's test_un_layout.py is the model).

Run: python3 -m unittest test_grand_monuments_layout -v
"""
import os
import re
import tempfile
import unittest

from gui_test_helpers import (LOC_DIR, _block_at, _children, _personal_reviewed, assert_column_closes_with_its_sections,
                               assert_wide_matches_narrow, gui_keys,
                               load_loc, loc_closure, mod_types, panel_loc_keys, panel_view, personal_text,
                               type_closure, unguarded)
from scripts.generators import gen_te_systems_window as window_gen

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "grand_monuments_widget.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_grand_monuments.txt")
VALUES = os.path.join(REPO, "common", "script_values", "gm_values.txt")
COM_VALUES = os.path.join(REPO, "common", "script_values", "gm_commission_values.txt")
COM_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "gm_commission_triggers.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "gm_sguis.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "gm_effects.txt")
LOC = os.path.join(REPO, "localization", "english", "te_miscellaneous_l_english.yml")
ICONS_DOC = os.path.join(REPO, "docs", "systems", "grand_monuments_gui_icons.md")
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
CONCEPT_LOC = os.path.join(REPO, "localization", "english", "te_concepts_l_english.yml")

# Trophies and Held Abroad are types in gui/gm_trophy_widgets.gui
# (test_grand_monument_trophies.py holds their flags and gates).
# Archaeological Expeditions is a type in gui/gm_archaeology_widgets.gui.
# The two "act now" sections, Awaiting a Decision and Awaiting Dedication, come
# straight after the Opportunity and before the readout (owner, 2026-10-27:
# GM-3 of the GUI audit, approved as proposed).
STATUS = ["te_gm_sec_commission", "te_gm_sec_decisions", "te_gm_sec_awaiting", "te_gm_sec_archaeology",
          "te_gm_sec_national", "te_gm_sec_monuments", "te_gm_sec_trophies", "te_gm_sec_abroad"]
# root -> (container, what it wraps)
ROOTS = {"widget_je_gm_overview": ("custom_widget_container_1", "te_gm_overview_panel"),
         "widget_je_gm_status": ("custom_widget_container_2", "te_gm_status_sections")}
# The composers' gate: the tab's own, on the shown country (the journal entry's
# roots keep [JournalEntry.IsActive]).
TAB_GATE = "GetScriptedGui('te_window_grand_monuments_tab_sgui').IsShown( GuiScope.SetRoot( Country.MakeScope ).End )"
FLAGS = {"gm_commission_closed", "gm_decisions_closed", "gm_national_closed", "gm_awaiting_closed",
         "gm_monuments_closed"}
LIVE_SECTIONS = ["te_gm_overview_panel", "te_gm_sec_commission", "te_gm_sec_decisions", "te_gm_sec_national",
                 "te_gm_sec_awaiting", "te_gm_sec_monuments", "gm_monument_row"]
HOW_KEYS = ["gm_je_how_grandeur", "gm_je_how_grandeur_age", "gm_je_how_grandeur_national", "gm_je_how_counts",
            "gm_je_how_counts_other", "gm_je_how_contested", "gm_je_how_choices",
            "gm_je_how_hard_times", "gm_je_how_commissions", "gm_je_how_commissions_rewards",
            "gm_je_how_names", "gm_je_how_policy", "gm_je_how_trophies", "gm_je_how_trophies_home",
            "gm_je_how_archaeology"]
# The Help page's topics, in order: its subheadings.
HOW_SUBS = ["gm_je_how_sub_grandeur", "gm_je_how_sub_counts", "gm_je_how_sub_signatures", "gm_je_how_sub_contested",
            "gm_je_how_sub_hard_times", "gm_je_how_sub_commissions", "gm_je_how_sub_names", "gm_je_how_sub_policy",
            "gm_je_how_sub_trophies", "gm_je_how_sub_archaeology"]
# The fading ledgers under National Effects' Fading Legitimacy (v1 §4.3, §5).
FADING = ("teardown", "vanity")
# The opportunity boons under National Effects' Opportunities Seized
# (docs/superpowers/archive/specs/2026-10-12-grand-monument-opportunities-design.md §3.2):
# one row each, shown while its months run.
BOONS = ("reign", "regime", "great_power", "victory", "defeat", "centenary", "ruler_death", "space", "faith",
         "tech_artistic", "tech_scientific", "tech_industrial", "tech_athletic", "tech_naturalist")
# Dedications with a national effect of their own: shown only while in force.
SPECIFIC = ("leader", "religious", "war_memorial", "artistic", "scientific", "industrial")
IGS = ("armed_forces", "devout", "industrialists", "intelligentsia", "landowners",
       "petty_bourgeoisie", "rural_folk", "trade_unions")
# The bars: row key -> the gm_set_steps OUT/NEXT suffix it follows.
FRACS = {"prestige": "standing", "prestige_pct": "standing", "legitimacy": "regime", "culture": "culture",
         "education": "education",
         "leader": "leader", "religious": "religious", "war_memorial": "war_memorial",
         "artistic": "artistic", "scientific": "scientific", "industrial": "industrial"}
# The unique dedications with a national effect (signatures spec 2026-10-16 §8):
# a row each after the dedications', in SIGNATURES' order
# (test_grand_monument_registry.py), each on its own curve (gm_sig_set_steps).
SIG_ROWS = ("antiquity", "archive", "throne", "royal_pantheon", "martial_glory", "liberty", "grande_armee",
            "mandate_of_heaven", "glory_of_athens", "to_victory", "unknown_soldier", "concert_of_nations",
            "conquerors_of_space", "olympic", "heroes")
# The specials, held for the next monument of their dedication, under Opportunities Seized.
SPECIALS = ("to_victory", "unknown_soldier", "concert_of_nations", "conquerors_of_space", "olympic")
SIG_VALUES = os.path.join(REPO, "common", "script_values", "gm_signature_values.txt")
SIG_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "gm_signature_effects.txt")

# The panel's icons (docs/systems/grand_monuments_gui_icons.md; the art is
# PR #586's): status code or cell -> texture. Remaking one keeps its file
# name, so neither this table nor the widget changes.
_GM = "gfx/interface/icons/gm_icons"
ICONS = {1: f"{_GM}/status_undedicated.dds",
         2: f"{_GM}/status_upheld.dds",
         3: f"{_GM}/status_heritage.dds",
         4: f"{_GM}/status_contested.dds",
         "hard_times": f"{_GM}/hard_times.dds"}
# The overview's cells that light on a count: count value -> status code (for
# its icon). Heritage is the Monuments cell's third line; Hard Times lights on
# its scripted GUI (owner, 2026-10-27: Banking's cells).
CELLS = {"gm_disp_count_sites": 1, "gm_disp_count_upheld": 2, "gm_disp_count_contested": 4}
BANKING_GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "banking_dashboard_widget.gui")


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
        for composer, expected in (("te_gm_status_sections", STATUS),):
            found = re.findall(r"^\t\t(te_gm_sec_\w+) = \{", _type_body(gui, composer), re.M)
            self.assertEqual(found, expected, composer)

    def test_roots_are_gated_wrappers_the_entry_mounts(self):
        gui, je = _gui(), _squash(_read(JE))
        for root, (container, inner) in ROOTS.items():
            body = _root_body(gui, root)
            self.assertIn('visible = "[JournalEntry.IsActive]"', body, root)
            self.assertIn(f"{inner} = {{}}", body, root)
            self.assertIn(f'name = "{root}" container = "{container}"', je, root)
            # The composer reads the tab's own gate on the shown country, which
            # another country's National Info has with no entry (charts-help-
            # national-info spec § 6.3); the root keeps the entry's.
            self.assertIn(f'visible = "[{TAB_GATE}]"', _type_body(gui, inner), inner)
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
                          ("te_gm_sec_decisions", "gm_decisions_closed"),
                          ("te_gm_sec_awaiting", "gm_awaiting_closed"),
                          ("te_gm_sec_monuments", "gm_monuments_closed")):
            self.assertIn(f"GetVariableSystem.Toggle('{flag}')", _type_body(gui, sec), sec)

    def test_how_it_works_is_the_help_page(self):
        """How Grand Monuments Work is the Help page alone
        (te_grand_monuments_help_popup, on te_popup = help_grand_monuments),
        which the "?" at the top of the entry opens: the link section is gone
        and its reference composer with it (test_te_help_pages.py)."""
        gui = _gui()
        self.assertNotIn("te_gm_sec_how", gui)
        self.assertNotIn("te_gm_reference_sections", gui)
        self.assertNotIn("widget_je_gm_reference", _read(JE))
        self.assertIn("type te_grand_monuments_help_body", gui)
        self.assertNotIn("gm_how_open", gui)


class HowItWorksTest(unittest.TestCase):
    def test_explanations_live_in_how_it_works(self):
        gui = _gui()
        how = _type_body(gui, "te_grand_monuments_help_body")
        for key in HOW_KEYS:
            self.assertIn(f'"{key}"', how, key)
        self.assertEqual(re.findall(r'text = "(gm_je_how_sub_\w+)"', _strip_comments(how)), HOW_SUBS)
        for sec in LIVE_SECTIONS:
            body = _type_body(gui, sec)
            self.assertNotIn("gm_je_how_", body, sec)
            self.assertNotIn("gm_note", body, f"{sec} carries an explanatory note")

    def test_every_how_key_exists_and_reads_nothing(self):
        loc = _loc()
        for key in HOW_KEYS + HOW_SUBS:
            self.assertIn(key, loc)
            self.assertNotIn("ScriptValue", loc[key], key)

    def test_the_contest_line_is_brief_with_the_reason_on_hover(self):
        loc = _loc()
        self.assertIn("It honors something this government is not", loc["gm_row_contest_tt"])
        self.assertNotIn("It honors", loc["gm_row_contest"])
        self.assertIn('tooltip = "gm_row_contest_tt"', _type_body(_gui(), "gm_monument_row"))

    def test_the_hard_times_sentence_is_the_cells_tooltip(self):
        loc = _loc()
        self.assertNotIn("gm_je_hard_times", loc)
        self.assertIn("Pause monument construction", loc["gm_je_ov_hard_times_tt"])


class StateGatedTest(unittest.TestCase):
    CONTESTED = "EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_status_code'), '(CFixedPoint)4' )"

    def test_contest_line_and_buttons_only_while_contested(self):
        row = _squash(_type_body(_gui(), "gm_monument_row"))
        self.assertIn(f'visible = "[{self.CONTESTED}]" '
                      f'tooltip = "gm_row_contest_tt" text = "gm_row_contest"', row)
        rows = re.findall(r'flowcontainer = \{ direction = horizontal spacing = 4 (?:ignoreinvisible = yes )?'
                          r'parentanchor = hcenter visible = "\[(.*?)\]" ((?:gm_choice_button = \{.*?\} \} )+)\}', row)
        self.assertEqual(len(rows), 3, "Rename's two rows (without and with Clear Name) and the contested "
                                       "choices' row, each centred")
        gates = dict(rows)
        self.assertEqual(gates[self.CONTESTED].count("gm_choice_button = {"), 3)
        self.assertNotIn("gm_rename_sgui", gates[self.CONTESTED])

    def test_rename_only_while_upheld(self):
        """A contested or heritage monument keeps its name (v2 §3.3): Rename
        shows only while the monument fits, and its scripted GUI says so."""
        row = _squash(_type_body(_gui(), "gm_monument_row"))
        upheld = ("And( EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_state_can_rename'), '(CFixedPoint)1' ), "
                  "EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_is_being_named'), '(CFixedPoint)0' ) )")
        # Two rows, so neither changes width when Clear Name comes and goes
        # (gui_modding_guide.md gotcha #43): Rename and Name It, and with a
        # typed name Clear Name as well.
        for typed in (0, 1):
            gate = (f"And( {upheld}, EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_state_has_typed_name'), "
                    f"'(CFixedPoint){typed}' ) )")
            self.assertIn(f'visible = "[{gate}]" gm_choice_button = {{ blockoverride "choice_context" '
                          f'{{ datacontext = "[GetScriptedGui(\'gm_rename_sgui\')]" }}', row)
            buttons = row.split(f'visible = "[{gate}]"', 1)[1].split("flowcontainer = {", 1)[0]
            self.assertIn("GetScriptedGui('gm_name_start_sgui')", buttons)
            self.assertEqual("GetScriptedGui('gm_clear_name_sgui')" in buttons, typed == 1)
            self.assertNotIn("visible", buttons)
        value = _squash(_block(_read(VALUES), "gm_state_can_rename"))
        self.assertEqual(value, "value = 0 if = { limit = { gm_state_status_fits = yes } value = 1 }")
        sgui = _squash(_block(_read(SGUIS), "gm_rename_sgui"))
        self.assertIn("gm_state_status_fits = yes", sgui)
        self.assertIn("ai_is_valid = { always = no }", sgui)

    def test_hard_times_only_while_it_holds(self):
        """A cell of the overview's grid (owner, 2026-10-27: Banking's cells
        where the overview flags something to act on): its icon lit, its red
        word and its remedy shown while it holds, the sentence on hover."""
        ov = _squash(_strip_comments(_type_body(_gui(), "te_gm_overview_panel")))
        shown = "GetScriptedGui('gm_hard_times_sgui').IsShown( GuiScope.SetRoot( Country.MakeScope ).End )"
        head = ('te_banking_ov_cell = { tooltip = "[SelectLocalization( ' + shown
                + ", 'gm_je_ov_hard_times_tt', 'gm_je_ov_hard_times_none_tt' )]\"")
        self.assertIn(head, ov, "no Hard Times cell")
        cell = ov.split(head, 1)[1].split('text = "gm_je_ov_policy"', 1)[0]
        self.assertIn(f'blockoverride "lit" {{ visible = "[{shown}]" }}', cell)
        self.assertIn(f'gm_ov_line = {{ visible = "[{shown}]" text = "gm_je_ov_hard_times" }}', cell)
        self.assertIn(f'gm_ov_line = {{ visible = "[Not( {shown} )]" text = "gm_je_ov_hard_times_off" }}', cell)
        self.assertIn(f'gm_ov_line = {{ visible = "[{shown}]" position = {{ 78 46 }} text = "gm_je_ov_hard_times_act" }}',
                      cell)
        loc = _loc()
        self.assertTrue(loc["gm_je_ov_hard_times"].startswith("#R "), "the word is red")
        self.assertLessEqual(len(loc["gm_je_ov_hard_times"].split()), 4, "a couple of words")

    def test_the_cell_row_never_changes_width(self):
        """Two rows of two Banking cells, none gated: a row whose width comes
        from its content is centred by the width it had at first layout."""
        ov = _squash(_strip_comments(_type_body(_gui(), "te_gm_overview_panel")))
        rows = re.findall(r"flowcontainer = \{ direction = horizontal spacing = 4 ignoreinvisible = yes (.*?)"
                          r"(?= flowcontainer = \{ direction = horizontal| textbox = \{)", ov)
        self.assertEqual([r.count("te_banking_ov_cell = {") for r in rows], [2, 2])
        for r in rows:
            self.assertNotRegex(r, r"te_banking_ov_cell = \{ visible")

    def test_every_total_only_while_in_force(self):
        """Zero rows hide, prestige, legitimacy and cultural pull included
        (owner, play-test round 2)."""
        nat = _squash(_type_body(_gui(), "te_gm_sec_national"))
        for key in FRACS:
            self.assertIn(f"gm_step_row = {{ visible = \"[NotEqualTo_CFixedPoint( Country.MakeScope"
                          f".ScriptValue('gm_display_{key}'), '(CFixedPoint)0' )]\" tooltip = \"gm_je_tt_{key}\"",
                          nat, key)
        for ig in IGS:
            self.assertIn(f"gm_value_row = {{ visible = \"[NotEqualTo_CFixedPoint( Country.MakeScope"
                          f".ScriptValue('gm_display_ig_{ig}'), '(CFixedPoint)0' )]\"", nat, ig)

    def test_headings_over_groups_that_can_be_empty_carry_the_groups_gate(self):
        nat = _squash(_type_body(_gui(), "te_gm_sec_national"))
        # The groups' ledgers are the player's own: the group's gate on a
        # wrapper, the guard inside it, the heading first (owner call 5).
        self.assertIn("flowcontainer = { visible = \"[And( Country.IsLocalPlayer, EqualTo_CFixedPoint( Country.MakeScope"
                      ".ScriptValue('gm_disp_ig_any'), '(CFixedPoint)1' ) )]\" direction = vertical ignoreinvisible = yes "
                      "flowcontainer = { using = te_own_country_only direction = vertical ignoreinvisible = yes "
                      "spacing = 2 gm_subheader = { blockoverride \"subheader_text\" { text = \"gm_je_sub_approval\"", nat)
        fading = re.search(r'gm_subheader = \{ visible = "\[Or\((.*?)\)\]" blockoverride "subheader_text" '
                           r'\{ text = "gm_je_sub_fading" \}', nat)
        self.assertTrue(fading)
        for ledger in FADING:
            self.assertIn(f"ScriptValue('gm_display_{ledger}')", fading.group(1))
        self.assertIn("gm_subheader = { visible = \"[EqualTo_CFixedPoint( Country.MakeScope"
                      ".ScriptValue('gm_disp_boon_any'), '(CFixedPoint)1' )]\" blockoverride \"subheader_text\" "
                      "{ text = \"gm_je_sub_boons\" }", nat)
        for boon in BOONS:
            self.assertIn(f"gm_value_row = {{ visible = \"[NotEqualTo_CFixedPoint( Country.MakeScope"
                          f".ScriptValue('gm_disp_boon_{boon}'), '(CFixedPoint)0' )]\" tooltip = \"gm_je_tt_boon_{boon}\"",
                          nat, boon)

    def test_sections_never_start_empty(self):
        gui = _gui()
        # National Effects opens on the monument policy's heading and buttons
        # (GM-3, owner 2026-10-27), its timing on the heading's hover (GM-2),
        # then the effects under a heading of their own, the empty-state line
        # first when nothing is in force (test_the_empty_state_covers_every_row
        # holds the gate).
        panel = _squash(_strip_comments(_type_body(gui, "te_gm_sec_national")).split("gm_panel = {", 1)[1])
        # The heading and its buttons are the player's own, in one guard.
        self.assertTrue(panel.startswith('visible = "[Not(GetVariableSystem.Exists(\'gm_national_closed\'))]" '
                                         'spacing = 2 flowcontainer = { using = te_own_country_only '
                                         'direction = vertical ignoreinvisible = yes spacing = 2 '
                                         'minimumsize = { 480 -1 } maximumsize = { 480 -1 } '
                                         'gm_subheader = { blockoverride "subheader_margin" {} '
                                         'blockoverride "subheader_text" { text = "gm_je_sub_policy" '
                                         'tooltip = "gm_je_sub_policy_tt" } }'), panel[:300])
        effects = panel.split('text = "gm_je_sub_in_force" } }', 1)[1]
        self.assertTrue(effects.startswith(' gm_text = { visible = "[EqualTo_CFixedPoint( Country'
                                           '.MakeScope.ScriptValue(\'gm_disp_national_any\'), \'(CFixedPoint)0\' )]" '
                                           'text = "gm_je_national_none" }'), effects[:300])
        # What a level is worth is said once, on the overview's last line
        # (GM-5), so it shows before there is a site to dedicate; Awaiting
        # Dedication opens on its rows.
        flat = _strip_comments(gui)
        self.assertEqual(flat.count('text = "gm_je_world_rate"'), 1)
        ov = _squash(_strip_comments(_type_body(gui, "te_gm_overview_panel")))
        last = ov.split('text = "gm_je_ov_policy" }', 1)[1]
        self.assertTrue(last.startswith(' textbox = {'), last[:200])
        self.assertIn('tooltip = "gm_je_world_rate_tt" text = "gm_je_world_rate" }', last)
        awaiting = _squash(_strip_comments(_type_body(gui, "te_gm_sec_awaiting")).split("gm_panel = {", 1)[1])
        self.assertTrue(awaiting.startswith('visible = "[Not(GetVariableSystem.Exists(\'gm_awaiting_closed\'))]" '
                                            'flowcontainer = {'), awaiting[:300])
        self.assertNotIn("gm_site_row_rate", _type_body(gui, "gm_site_row"))
        # Our Monuments: the empty-state line shows exactly when the list is empty.
        mon = _squash(_type_body(gui, "te_gm_sec_monuments"))
        self.assertIn("gm_text = { visible = \"[EqualTo_CFixedPoint( Country.MakeScope"
                      ".ScriptValue('gm_display_count'), '(CFixedPoint)0' )]\" text = \"gm_je_monuments_none\" }", mon)
        # ... and when every monument is contested, in the section above.
        self.assertIn("ScriptValue('gm_disp_count_listed_rest'), '(CFixedPoint)0' ) )]\" "
                      "text = \"gm_je_monuments_all_awaiting\" }", mon)
        # How it Works: the first heading drops its top margin.
        how = _squash(_strip_comments(_type_body(gui, "te_grand_monuments_help_body")))
        self.assertIn('gm_subheader = { blockoverride "subheader_margin" {} blockoverride "subheader_text" '
                      '{ text = "gm_je_how_sub_grandeur" } }', how.split("gm_note", 1)[0])


class DecisionSectionTest(unittest.TestCase):
    """Awaiting a Decision (GM-3, owner 2026-10-27): shown only while a
    monument is contested, Our Monuments' two datamodels filtered on the
    contested status, the row carrying its three choices; Our Monuments then
    lists only the rest."""

    def test_gated_on_the_contested_count(self):
        sec = _squash(_strip_comments(_type_body(_gui(), "te_gm_sec_decisions")))
        self.assertTrue(sec.startswith("direction = vertical parentanchor = hcenter ignoreinvisible = yes spacing = 4 "
                                       "visible = \"[GreaterThan_CFixedPoint( Country.MakeScope"
                                       ".ScriptValue('gm_disp_count_contested'), '(CFixedPoint)0' )]\""))
        self.assertIn('text = "gm_je_decisions_header"', sec)
        self.assertIn("gm_disp_count_contested", _squash(_block(_read(VALUES), "gm_disp_count_listed_rest")))

    def test_the_two_lists_split_on_the_status(self):
        decide = _squash(_strip_comments(_type_body(_gui(), "te_gm_sec_decisions")))
        rest = _squash(_strip_comments(_type_body(_gui(), "te_gm_sec_monuments")))
        self.assertIn("gm_monument_row = { datacontext = \"[Scope.GetState]\" visible = \"[EqualTo_CFixedPoint( "
                      "State.MakeScope.ScriptValue('gm_status_code'), '(CFixedPoint)4' )]\" }", decide)
        self.assertIn("NotEqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_status_code'), '(CFixedPoint)4' )", rest)
        self.assertIn("EqualTo_CFixedPoint( ScriptContainer.MakeScope.ScriptValue('gm_mon_status_code'), '(CFixedPoint)4' )",
                      decide)
        self.assertIn("NotEqualTo_CFixedPoint( ScriptContainer.MakeScope.ScriptValue('gm_mon_status_code'), "
                      "'(CFixedPoint)4' )", rest)
        for sgui in ("gm_mon_tear_down_sgui", "gm_mon_rededicate_sgui", "gm_mon_preserve_sgui"):
            self.assertIn(sgui, decide)
            self.assertNotIn(sgui, rest)

    def test_the_cell_points_at_it(self):
        loc = _loc()
        self.assertIn("Awaiting a Decision", loc["gm_je_ov_contested_tt"])
        self.assertEqual(loc["gm_je_decisions_header"], "Awaiting a Decision")


class RowTooltipTest(unittest.TestCase):
    def test_row_button_tooltips_read_no_journal_entry(self):
        """Gotcha #24: a tooltip inside a datamodel row renders without
        JournalEntry, so the row's buttons root their scripted GUI tooltips at
        the player."""
        keys = re.findall(r'tooltip = "(\w+)"', _type_body(_gui(), "gm_monument_row"))
        loc = _loc()
        checked = sorted({k for k in keys if "ScriptedGui" in loc.get(k, "")})
        self.assertEqual(len(checked), 6)
        for key in checked:
            self.assertNotIn("JournalEntry", loc[key], key)
            self.assertIn("GuiScope.SetRoot( GetPlayer.MakeScope )", loc[key], key)


class TypedNameLayoutTest(unittest.TestCase):
    """Typed names (v2 §3.5): the naming line shows only while its monument is
    being named, holds every read of the carrier company, opens the popup from
    its _show state and names the monument from a watcher."""

    def test_every_carrier_read_sits_in_the_naming_line(self):
        gui = _strip_comments(_gui())
        line = _type_body(gui, "gm_naming_line")
        self.assertEqual(gui.count("Var('gm_name_carrier')"), line.count("Var('gm_name_carrier')"))
        self.assertTrue(_squash(line).startswith(
            "direction = vertical ignoreinvisible = yes spacing = 4 parentanchor = hcenter visible = "
            "\"[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_is_being_named'), '(CFixedPoint)1' )]\""))
        self.assertIn("gm_naming_line = {}", _squash(_type_body(gui, "gm_monument_row")))

    def test_the_show_state_and_the_watcher(self):
        line = _squash(_type_body(_strip_comments(_gui()), "gm_naming_line"))
        show = re.search(r"state = \{ name = _show (.*?) \} widget", line)
        self.assertTrue(show)
        self.assertLess(show.group(1).find("gm_name_mark_old_sgui"), show.group(1).find("ShowCompanyChangeName"),
                        "store the starting name before the popup can change it")
        watcher = re.search(r"widget = \{ size = \{ 1 1 \} state = \{ trigger_when = \"(.*?)\" on_finish = \"(.*?)\" \}", line)
        self.assertTrue(watcher)
        self.assertIn("ScriptValue('gm_has_name_old'), '(CFixedPoint)1' )", watcher.group(1))
        self.assertIn("GetScriptedGui('gm_name_use_sgui').Execute(", watcher.group(2))

    def test_the_title_prints_a_typed_name(self):
        row = _squash(_type_body(_gui(), "gm_monument_row"))
        for value, key in (("0", "gm_row_title"), ("1", "gm_row_title_named")):
            self.assertIn(f"visible = \"[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_state_has_typed_name'), "
                          f"'(CFixedPoint){value}' )]\"", row)
            self.assertIn(f'text = "{key}"', row)


class ChoicePreviewTest(unittest.TestCase):
    """GM-4 (the 2026-10-27 GUI audit): the three contested choices print
    figures. The refresh stores what each would do this month on the
    monument, under a marker (a tooltip walks the refresh writing nothing),
    on the curves the ledgers use; the tooltips read guarded values."""

    def test_the_refresh_previews_under_a_marker(self):
        effects = _read(EFFECTS)
        refresh = _squash(_block(effects, "gm_country_refresh"))
        self.assertLess(refresh.find("gm_compute_totals = yes"), refresh.find("gm_preview_choices = yes"))
        preview = _squash(_block(effects, "gm_preview_choices"))
        self.assertTrue(preview.startswith("set_variable = gm_preview_click if = { limit = { has_variable = "
                                           "gm_preview_click } remove_variable = gm_preview_click"))
        country = _squash(_block(effects, "gm_preview_choices_on_country"))
        self.assertIn("multiply = gm_step_teardown", country)
        self.assertIn("add = var:gm_prev_g add = var:gm_prev_g", country, "Pull Down lifts the resentment too")
        sup = _squash(_block(effects, "gm_preview_supporters_on_country"))
        self.assertIn("multiply = -0.5", sup, "Rededicate takes half off the old supporters")
        steps = _squash(_block(effects, "gm_prev_signed_steps"))
        self.assertEqual(steps.count("gm_curve_steps_f5"), 2, "the approval curve, as gm_compute_ig's")

    def test_the_country_helpers_run_on_the_country(self):
        # They read the country's ledgers and nets; called from the monument's
        # state or container they read nothing, and the figures never computed
        # (2026-10-31, `Failed to fetch variable for 'gm_prev_in'` at seeding).
        effects = _read(EFFECTS)
        for caller in ("gm_state_preview_choices", "gm_mon_preview_choices"):
            body = _squash(_block(effects, caller))
            for helper in ("gm_preview_choices_on_country", "gm_preview_supporters_on_country"):
                self.assertEqual(body.count(f"{helper} = yes"), 1, (caller, helper))
                self.assertIn(f"scope:gm_prev_country = {{ {helper} = yes }}", body, (caller, helper))

    def test_the_tooltips_read_the_guarded_figures(self):
        loc = _loc()
        values = _read(VALUES)
        for key, reads in (("gm_tear_down_tt", ("gm_state_disp_prev_td_legit", "gm_state_disp_prev_td_base",
                                                 "gm_state_disp_prev_td_sup")),
                           ("gm_rededicate_tt", ("gm_state_disp_prev_rd_levels", "gm_state_disp_prev_rd_grandeur",
                                                  "gm_state_disp_prev_rd_sup", "gm_state_rededicate_cost"))):
            for name in reads:
                self.assertIn(f"ScriptValue('{name}')", loc[key], (key, name))
        for name in ("td_legit", "td_base", "td_sup", "rd_sup"):
            self.assertEqual(_squash(_block(values, f"gm_state_disp_prev_{name}")),
                             f"value = 0 if = {{ limit = {{ has_variable = gm_prev_{name} }} value = var:gm_prev_{name} }}")
        for key in ("gm_mon_tear_down_tt", "gm_mon_rededicate_tt", "gm_mon_preserve_tt"):
            self.assertIn("THIS.ScriptValue('gm_mon_", loc[key], key)
        self.assertIn("does not change now", loc["gm_preserve_tt"])


class ApprovalBreakdownTest(unittest.TestCase):
    """GM-13: how a group's total works is said once, on the heading; each
    group's row says where its own total comes from, the parts
    gm_compute_ig keeps beside the net."""

    def test_each_row_has_its_own_breakdown(self):
        nat = _squash(_type_body(_gui(), "te_gm_sec_national"))
        self.assertIn('text = "gm_je_sub_approval" tooltip = "gm_je_tt_ig" }', nat)
        self.assertNotIn('tooltip = "gm_je_tt_ig" blockoverride', nat)
        loc = _loc()
        effects = _squash(_block(_read(EFFECTS), "gm_compute_ig"))
        for part in ("pos", "neg", "res"):
            self.assertIn(f"set_variable = {{ name = gm_ig_{part}_$IG$ value = ", effects, part)
        for ig in IGS:
            self.assertIn(f'tooltip = "gm_je_tt_ig_{ig}"', nat, ig)
            for part in ("pos", "neg", "res", "ledger"):
                self.assertIn(f"ScriptValue('gm_disp_ig_{part}_{ig}')", loc[f"gm_je_tt_ig_{ig}"], (ig, part))


class PolicyLayoutTest(unittest.TestCase):
    """The monument policy (v2 §5): its name on the line under the overview's cells,
    the four buttons at the top of National Effects (GM-3, owner
    2026-10-27), two to a row."""

    def test_the_overview_names_the_policy(self):
        ov = _squash(_strip_comments(_type_body(_gui(), "te_gm_overview_panel")))
        self.assertIn('tooltip = "gm_je_ov_policy_tt" text = "gm_je_ov_policy" }', ov)

    def test_four_buttons_two_to_a_row(self):
        nat = _squash(_type_body(_gui(), "te_gm_sec_national"))
        tail = nat.split('text = "gm_je_sub_policy"', 1)[1]
        rows = re.findall(r"flowcontainer = \{ direction = horizontal spacing = 8 parentanchor = hcenter "
                          r"((?:gm_policy_button = \{.*?\} \} )+)\}", tail)
        self.assertEqual([r.count("gm_policy_button = {") for r in rows], [2, 2])
        order = re.findall(r"GetScriptedGui\('gm_policy_(\w+)_sgui'\)", tail)
        self.assertEqual(order, ["open", "ceremonial", "culture", "education"])
        button = _squash(_type_body(_gui(), "gm_policy_button"))
        self.assertIn("size = { 230 28 }", button)

    def test_each_button_prints_its_modifier_lines(self):
        """GM-2: each policy's effect reads as the engine's lines, through a
        display-only static modifier of script_only types; the shared timing
        is said once, on the heading's hover."""
        loc = _loc()
        mods = _read(os.path.join(REPO, "common", "static_modifiers", "gm_modifiers.txt"))
        types = _read(os.path.join(REPO, "common", "modifier_type_definitions", "gm_policy_modifier_types.txt"))
        for p, display in (("open", "open"), ("ceremonial", "ceremonial"), ("culture", "culture"),
                           ("culture_prestige", "culture_prestige"), ("education", "education")):
            key = f"gm_policy_{p}_effect_tt"
            self.assertIn(f"[GetStaticModifier('gm_policy_{display}_display').GetDesc]", loc[key], key)
            self.assertIn(f"[GetStaticModifier('gm_policy_{display}_display').GetDesc]", loc[f"gm_policy_effects_{p}"])
            for gone in ("60", "cannot change", "next month"):
                self.assertNotIn(gone, loc[key], key)
            body = _block(mods, f"gm_policy_{display}_display")
            self.assertIsNotNone(body, display)
            kinds = re.findall(r"\b(country_gm_monument_\w+) =", body)
            self.assertTrue(kinds, display)
            for kind in kinds:
                self.assertRegex(_block(types, kind) or "", r"script_only = yes", kind)
        self.assertIn("60", loc["gm_je_sub_policy_tt"])
        self.assertIn("next month", loc["gm_je_sub_policy_tt"])


class NationalEmptyStateTest(unittest.TestCase):
    def test_the_empty_state_covers_every_row(self):
        """gm_disp_national_any is 1 exactly when some row of National Effects
        shows: every gm_display_* a row is gated on reads a variable the value
        tests, and gm_disp_ig_any's variables are in it too."""
        values = _read(VALUES) + "\n" + _read(SIG_VALUES)
        nat = _type_body(_gui(), "te_gm_sec_national")
        anyv = _squash(_block(values, "gm_disp_national_any"))
        gates = set(re.findall(r"ScriptValue\('(gm_display_\w+)'\), '\(CFixedPoint\)0' \)", nat))
        self.assertEqual(len(gates), len(FRACS) + len(IGS) + len(FADING) + len(SIG_ROWS))
        for display in gates:
            read_vars = set(re.findall(r"var:(\w+)", _block(values, display)))
            self.assertEqual(len(read_vars), 1, display)
            var = read_vars.pop()
            self.assertIn(f"AND = {{ has_variable = {var} NOT = {{ var:{var} = 0 }} }}", anyv, display)
        for var in re.findall(r"has_variable = (\w+)", _block(values, "gm_disp_ig_any")):
            self.assertIn(f"has_variable = {var} ", anyv, var)
        # The boon rows: gm_disp_boon_any is gm_boons_idle's negation, and the
        # empty state counts it.
        self.assertIn("gm_boons_idle = no", anyv)
        # A special held shows under the boons (signatures spec §8).
        self.assertIn("gm_sig_held_idle = no", anyv)
        self.assertIn("gm_sig_held_idle = yes", _squash(_block(_read(COM_VALUES), "gm_disp_boon_any")))
        idle = _squash(_block(_read(COM_TRIGGERS), "gm_boons_idle"))
        for boon in BOONS:
            self.assertIn(f"NOT = {{ has_variable = gm_boon_{boon} }}", idle, boon)


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
        for key, name in (("gm_je_ov_heritage", "heritage"), ("gm_je_ov_contested_label", "contested"),
                          ("gm_je_ov_monuments_tt", "contested"), ("gm_status_heritage", "heritage"),
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
        self.assertEqual(ov.count("te_banking_ov_cell = {"), 4)
        for value, code in CELLS.items():
            gt = (f"GreaterThan_CFixedPoint( Country.MakeScope.ScriptValue('{value}'), "
                  f"'(CFixedPoint)0' )")
            cell = re.search(r'blockoverride "cell_texture" \{ texture = "([^"]+)" \} '
                             r'blockoverride "lit" \{ visible = "\[' + re.escape(gt) + r'\]" \} '
                             r'blockoverride "unlit" \{ visible = "\[Not\( ' + re.escape(gt) + r' \)\]" \}', ov)
            self.assertTrue(cell, value)
            self.assertEqual(cell.group(1), ICONS[code], value)
        hard = re.search(r'blockoverride "cell_texture" \{ texture = "([^"]+)" \} blockoverride "lit" \{ '
                         r'visible = "\[GetScriptedGui\(\'gm_hard_times_sgui\'\)', ov)
        self.assertEqual(hard.group(1), ICONS["hard_times"])

    def test_every_icon_is_the_mods_own_and_listed(self):
        """The #586 art is wired: every texture in the widget is a
        gm_icons file in ICONS, and the icon list records each one. No vanilla
        placeholder is left."""
        doc = _read(ICONS_DOC)
        for path in set(ICONS.values()):
            self.assertIn(f"`{os.path.basename(path)}`", doc, path)
        self.assertIn(f"`{_GM}/`", doc)
        # The monument pictures (gm_pictures/, spec 2026-10-11) are the registry
        # test's PictureTests, one per picture code.
        gui_textures = {tex for tex in re.findall(r'texture = "([^"]+)"', _strip_comments(_gui()))
                        if "/gm_pictures/" not in tex}
        self.assertEqual(gui_textures, set(ICONS.values()), "a texture in the widget is not in ICONS")
        self.assertNotIn("generic_icons", _strip_comments(_gui()), "a vanilla placeholder is left")


class DisplayValuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES) + "\n" + _read(COM_VALUES) + "\n" + _read(SIG_VALUES)
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
        self.assertIn("gm_state_is_heritage = no", _squash(_block(self.values, "gm_disp_count_upheld")))
        self.assertIn("gm_state_is_dedicated = yes", _squash(_block(self.values, "gm_disp_count_upheld")))
        # The Sites cell counts construction sites (sites spec 2026-10-18), and
        # those Dedicate can finish now.
        self.assertIn("gm_state_has_site = yes", _squash(_block(self.values, "gm_disp_count_sites")))
        ready = _squash(_block(self.values, "gm_disp_count_sites_ready"))
        for test in ("gm_state_awaits_dedication = yes", "gm_state_site_level >= 1", "gm_state_disp_site_building = 0"):
            self.assertIn(test, ready)
        self.assertIn("gm_state_is_contested = yes", _squash(_block(self.values, "gm_disp_count_contested")))

    def test_each_bar_follows_its_curve(self):
        """A bar's first step f and variables must be its gm_set_steps call's;
        a total on the 1/n curve (gm_set_steps_lin_open: prestige and cultural
        pull) reads the step's width instead, (G - N + W) / W."""
        totals = _squash(_block(_read(EFFECTS), "gm_compute_totals"))
        calls = {m.group(3): (m.group(1), int(m.group(4))) for m in re.finditer(
            r"gm_set_steps = \{ IN = (gm_\w+) OUT = gm_s_(\w+) NEXT = gm_n_(\w+) F = (\d+) \}", totals)}
        lin = {m.group(3): (m.group(1), m.group(4)) for m in re.finditer(
            r"gm_set_steps_lin_open = \{ IN = (gm_\w+) OUT = gm_s_(\w+) NEXT = gm_n_(\w+) "
            r"WIDTH = (gm_w_\w+) F = \d+ \}", totals)}
        self.assertEqual(set(lin), {"standing", "culture", "education"})
        gui = _gui()
        for row, suffix in FRACS.items():
            self.assertIn(f"ScriptValue('gm_disp_frac_{row}')", gui, row)
            body = _squash(_block(self.values, f"gm_disp_frac_{row}"))
            if suffix in lin:
                source, width = lin[suffix]
                self.assertIn(f"has_variable = {width}", body, row)
                self.assertIn(f"value = var:{source} subtract = var:gm_n_{suffix} add = var:{width} "
                              f"divide = var:{width}", body, row)
            else:
                source, f = calls[suffix]
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
        # The overview: Banking's cells, two to a row (owner, 2026-10-27).
        cell = int(re.search(r"size = \{ (\d+) ", _type_body(_read(BANKING_GUI), "te_banking_ov_cell")).group(1))
        ov = _squash(_type_body(gui, "te_gm_overview_panel"))
        gap = int(re.search(r"flowcontainer = \{ direction = horizontal spacing = (\d+) ", ov).group(1))
        self.assertEqual(2 * cell + gap, 480)


# ---- Play-test round 3: nothing a player reads may end in "..." ----------
# Units per character of each font, plus a 10% margin. Large and medium were
# measured from the owner's screenshots (round-3 rules); small is an estimate,
# 0.85 of medium, until it is measured. The panel's own sizes (the
# gm_fontsize_* templates at the head of the widget, GM-17: the owner's ladder
# of 2026-10-17) scale from those, as test_banking_layout.py's do: the serif
# face at 10 a character in 20, the overview's tooltip face at 8.6 in 16.
UNITS = {"fontsize_large": 10.0, "fontsize_medium": 8.6, "fontsize_small": 7.3}
MARGIN = 1.1


def _template_sizes():
    gui = _read(GUI)
    return {name: int(size) for name, size in
            re.findall(r"(?m)^template (gm_fontsize_\w+) \{\s*fontsize = (\d+)", gui)}


_SIZES = _template_sizes()
UNITS.update(gm_fontsize_row=10.0 / 20 * _SIZES["gm_fontsize_row"],
             gm_fontsize_heading=10.0 / 20 * _SIZES["gm_fontsize_heading"],
             gm_fontsize_overview=8.6 / 16 * _SIZES["gm_fontsize_overview"],
             banking_dash_fontsize_overview=8.6)
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


def _textbox_cell(body):
    """(width, font) of a type that is itself a textbox."""
    width = re.search(r"(?:maximumsize = \{ |max_width = )(\d+)", body)
    font = re.search(r"using = ((?:gm_)?fontsize_\w+)", body)
    return int(width.group(1)), font.group(1)


def _cells(body):
    """(width, font) of each fixed-width textbox in a type, in order."""
    out = []
    for m in re.finditer(r"textbox = \{", body):
        tb = _match_brace(body, m.end())
        width = re.search(r"(?:maximumsize = \{ |max_width = )(\d+)", tb)
        font = re.search(r"using = ((?:gm_)?fontsize_\w+)", tb)
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
        self.assertEqual(len(steps), len(FRACS) + len(SIG_ROWS))
        for lbl, val in steps:
            self._fits(lbl, label)
            self._fits(val, value, LONGEST_VALUE)
        label, value = _cells(_type_body(self.gui, "gm_value_row"))
        rows = re.findall(r'gm_value_row = \{.*?"row_label" \{ text = "(\w+)" \}.*?"row_value" \{ text = "(\w+)" \}', nat)
        self.assertEqual(len(rows), len(IGS) + len(FADING) + len(BOONS) + len(SPECIALS))
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
        """Banking's cells (owner, 2026-10-27): each caption in the cell's 154
        column, each word and third line in gm_ov_line's, at the overview's
        size."""
        banking = _read(BANKING_GUI)
        caption = (int(re.search(r'block "caption_width" \{\s*max_width = (\d+)',
                                 _type_body(banking, "te_banking_ov_cell")).group(1)), "banking_dash_fontsize_overview")
        line = _textbox_cell(_type_body(self.gui, "gm_ov_line"))
        ov = _type_body(self.gui, "te_gm_overview_panel")
        captions = set(re.findall(r'blockoverride "caption" \{\s*text = "(\w+)"', ov))
        self.assertEqual(len(captions), 4)
        for key in captions:
            self._fits(key, caption)
        words = set(re.findall(r'gm_ov_line = \{(?:[^{}]|\{[^{}]*\})*?text = "(\w+)"', ov))
        self.assertEqual(len(words), 12)
        for key in words:
            self._fits(key, line, LONGEST_COUNT)
        self.assertEqual(line[1], "gm_fontsize_overview")

    def test_the_policy_line(self):
        ov = _type_body(self.gui, "te_gm_overview_panel")
        self.assertIn("using = gm_fontsize_overview", ov.split('text = "gm_je_ov_policy"', 1)[0].rsplit("textbox", 1)[1])

    def test_the_level_rate_line(self):
        """What a level built now adds (GM-5), one line in English under the
        policy at the overview's size; the rate is 5.000 at most. The box
        wraps, for a longer translation."""
        ov = _type_body(self.gui, "te_gm_overview_panel")
        box = ov.split('text = "gm_je_world_rate"', 1)[0].rsplit("textbox", 1)[1]
        self.assertIn("multiline = yes", box)
        width = int(re.search(r"maximumsize = \{ (\d+) ", box).group(1))
        font = re.search(r"using = (gm_fontsize_\w+)", box).group(1)
        self.assertEqual(font, "gm_fontsize_overview")
        # The 1836 figure prints whole (|0); the rate to three places.
        value = self.loc["gm_je_world_rate"].replace(
            "[Country.MakeScope.ScriptValue('gm_level_grandeur_1836')|0]", "5")
        text = _rendered(value, self.loc, "5.000")
        self.assertEqual(text, "A level built now adds 5.000 Grandeur (5 in 1836)")
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, width, f"{text!r} needs {need:.0f} of {width} ({font})")

    def test_row_status_words(self):
        """The row's word is custom loc: the longest word it can pick."""
        (cell,) = _cells(_type_body(self.gui, "gm_row_status"))
        words = re.findall(r"localization_key = (\w+)", _block(_read(CUSTOM_LOC), "gm_status_name"))
        self.assertEqual(len(words), 5)
        for key in words:
            self._fits(key, cell)

    def test_choice_buttons(self):
        (cell,) = _cells(_type_body(self.gui, "gm_choice_button"))
        keys = sorted(set(re.findall(r'"choice_text" \{ text = "(\w+)" \}', _type_body(self.gui, "gm_monument_row"))))
        self.assertEqual(len(keys), 6, "Rename, Name It, Clear Name and the three contested choices")
        for key in keys:
            self._fits(key, cell)

    def test_policy_buttons(self):
        (cell,) = _cells(_type_body(self.gui, "gm_policy_button"))
        keys = re.findall(r'"policy_text" \{ text = "(\w+)" \}', _type_body(self.gui, "te_gm_sec_national"))
        self.assertEqual(len(keys), 4)
        for key in keys:
            self._fits(key, cell)

    def test_naming_buttons(self):
        (cell,) = _cells(_type_body(self.gui, "gm_naming_button"))
        keys = re.findall(r'"naming_text" \{ text = "(\w+)" \}', _type_body(self.gui, "gm_naming_line"))
        self.assertEqual(len(keys), 3)
        for key in keys:
            self._fits(key, cell)

    def test_hard_times_phrase(self):
        self._fits("gm_je_ov_hard_times", _textbox_cell(_type_body(self.gui, "gm_ov_line")))

    def test_every_textbox_names_a_panel_size(self):
        """GM-17: every textbox in the panel's files sizes its type through
        the panel's templates, so a pass on type edits three numbers."""
        for path in (GUI, os.path.join(REPO, "gui", "gm_trophy_widgets.gui"),
                     os.path.join(REPO, "gui", "gm_archaeology_widgets.gui")):
            text = _strip_comments(_read(path))
            self.assertNotRegex(text, r"using = fontsize_", path)
        self.assertEqual(_SIZES, {"gm_fontsize_row": 17, "gm_fontsize_heading": 20, "gm_fontsize_overview": 16})

    def test_trophy_and_dig_buttons(self):
        trophy = _read(os.path.join(REPO, "gui", "gm_trophy_widgets.gui"))
        arch = _read(os.path.join(REPO, "gui", "gm_archaeology_widgets.gui"))
        loc_keys = {
            "gm_tr_button": (trophy, ["gm_button_tr_return_it", "gm_button_tr_bring_home", "gm_button_tr_carry_off"]),
            "gm_tr_take_button": (trophy, ["gm_button_tr_take"]),
            "gm_mon_take_button": (trophy, ["gm_button_tr_take"]),
            "gm_mon_choice_button": (trophy, ["gm_button_tear_down", "gm_button_rededicate", "gm_button_preserve"]),
            "gm_arch_button": (arch, ["gm_arch_launch_antiquarian", "gm_arch_launch_systematic",
                                      "gm_arch_launch_forensic", "gm_arch_suspend"]),
            "gm_dedicate_button": (self.gui, ["gm_button_dedicate"]),
        }
        for typ, (text, keys) in loc_keys.items():
            cells = _cells(_type_body(text, typ))
            if not cells:   # the width is a block with a default (gm_tr_button)
                width = int(re.search(r'block "tr_button_text_width" \{\s*max_width = (\d+)',
                                      _type_body(text, typ)).group(1))
                cells = [(width, re.search(r"using = (gm_fontsize_\w+)", _type_body(text, typ)).group(1))]
            for key in keys:
                self._fits(key, cells[0])
        # The Short view's button, narrower, fits the longest of its two labels.
        short = _type_body(trophy, "gm_tr_row_short")
        width = int(re.search(r'"tr_button_text_width" \{\s*max_width = (\d+)', short).group(1))
        for key in ("gm_button_tr_bring_home", "gm_button_tr_carry_off"):
            self._fits(key, (width, "gm_fontsize_row"))


# ---- The state view's card (te_state_gm_card) ------------------------------
STATE_GUI = os.path.join(REPO, "gui", "te_state_panel_widgets.gui")
STATES_PANEL = os.path.join(REPO, "gui", "states_panel.gui")
WINDOW = os.path.join(REPO, "gui", "te_systems_window.gui")
# the window's strip, templates and tab mounts (scripts/generators/gen_te_systems_window.py)
WINDOW_GENERATED = os.path.join(REPO, "gui", "te_systems_window_generated.gui")


class StateCardTest(unittest.TestCase):
    """The Grand Monument card in the state view: shown only where a monument
    stands, its status as the journal entry's rows show it, display only but
    for a goto to the Timeline Extended window's tab on the player's own
    state."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(STATE_GUI)
        cls.card = _type_body(cls.gui, "te_state_gm_card")
        cls.flat = _squash(_strip_comments(cls.card))
        goto = re.search(r"### OPEN THE WINDOW'S TAB[^\n]*\n(?:\t*###[^\n]*\n)*\t*widget = \{", cls.card)
        cls.goto = _squash(_match_brace(cls.card, goto.end()))
        cls.rest = _squash(_strip_comments(cls.card[:goto.start()]))

    def test_instanced_under_the_tourism_card(self):
        panel = _squash(_strip_comments(_read(STATES_PANEL)))
        self.assertEqual(panel.count("te_state_gm_card = {}"), 1)
        self.assertIn("te_state_tourism_card = {} te_state_gm_card = {}", panel)

    def test_shown_only_while_a_monument_stands(self):
        self.assertTrue(self.flat.startswith(
            "visible = \"[NotEqualTo_CFixedPoint(State.MakeScope.ScriptValue('gm_status_code'), "
            "'(CFixedPoint)0')]\""))

    def test_status_icons_follow_the_code(self):
        found = re.findall(r"gm_row_status = \{ visible = \"\[EqualTo_CFixedPoint\(State\.MakeScope\.ScriptValue"
                           r"\('gm_status_code'\), '\(CFixedPoint\)(\d)'\)\]\" tooltip = \"(\w+)\" "
                           r"blockoverride \"status_texture\" \{ texture = \"([^\"]+)\" \}", self.flat)
        self.assertEqual({int(c): t for c, _, t in found}, {k: v for k, v in ICONS.items() if isinstance(k, int)})
        # The three hidden ones take no room.
        # The picture and details are a horizontal row in a vertical flow that
        # carries the margin, width and background, so the monuments standing
        # beside this one (te_state_gm_beside) can span the card under them.
        self.assertIn("container = { flowcontainer = { direction = vertical ignoreinvisible = yes margin = { 10 8 } "
                      "spacing = 8 minimumsize = { 530 -1 } background = { using = entry_bg_simple } "
                      "flowcontainer = { direction = horizontal ignoreinvisible = yes spacing = 10 ", self.flat)
        row = _squash(_type_body(_gui(), "gm_monument_row"))
        for code, tooltip, _ in found:
            self.assertIn(f"'(CFixedPoint){code}' )]\" tooltip = \"{tooltip}\"", row, "the row's tooltip")

    def test_titles_and_lines_are_the_rows(self):
        for key in ("gm_row_title", "gm_row_title_named", "gm_row_contest", "gm_row_inscription"):
            self.assertIn(f'text = "{key}"', self.rest, key)
        self.assertIn("ScriptValue('gm_state_has_typed_name'), '(CFixedPoint)0')]\" ", self.rest)
        self.assertIn("ScriptValue('gm_state_has_typed_name'), '(CFixedPoint)1')]\" ", self.rest)
        # The contest line only while contested, its reason on hover.
        self.assertRegex(self.rest, r"visible = \"\[EqualTo_CFixedPoint\(State\.MakeScope\.ScriptValue"
                                    r"\('gm_status_code'\), '\(CFixedPoint\)4'\)\]\" (?:(?!textbox = \{).)*?"
                                    r"tooltip = \"gm_state_contest_tt\" text = \"gm_row_contest\"")

    def test_zero_rows_hide(self):
        for value, key in (("gm_state_disp_tourism", "gm_state_lbl_tourism"),
                           ("gm_state_disp_local", "gm_state_lbl_local")):
            self.assertRegex(self.rest, r"te_state_gm_row = \{ visible = \"\[NotEqualTo_CFixedPoint\(State\.MakeScope"
                                        rf"\.ScriptValue\('{value}'\), '\(CFixedPoint\)0'\)\]\".*?"
                                        rf"\"row_label\" \{{ text = \"{key}\" \}}")

    def test_display_only_but_for_the_goto(self):
        """No action and no journal entry outside the goto; the goto shows on
        the player's own state while the window's tab is open, and opens the
        window on that tab, not the journal."""
        for word in ("JournalEntry", "onclick", "ScriptedGui.Execute", "GetPlayerJournalEntry"):
            self.assertNotIn(word, self.rest, word)
        self.assertTrue(self.goto.startswith(
            "visible = \"[And(ObjectsEqual(State.GetOwner, GetPlayer.Self), "
            "GetScriptedGui('te_window_grand_monuments_tab_sgui').IsShown(GuiScope.SetRoot(GetPlayer.MakeScope)"
            ".End))]\""))
        for word in ("JournalEntry", "InformationPanelBar", "datacontext"):
            self.assertNotIn(word, self.goto, word)
        self.assertRegex(self.goto, r"button_icon_goto = \{ size = \{ 25 25 \} tooltip = \"gm_state_open_window_tt\" "
                                    r"onclick = \"\[GetVariableSystem\.Set\('te_systems_window_tab', 'grand_monuments'\)\]\" "
                                    r"onclick = \"\[GetVariableSystem\.Set\('com_open_window', 'te_systems_window'\)\]\" \}")

    def test_the_goto_sets_what_the_window_reads(self):
        """The goto's two values are the ones the window's Grand Monuments tab
        sets and its root shows on, and its gate is the tab content's own: the
        gate of te_gm_tab_body, the body the tab's mount holds."""
        window = _squash(_read(WINDOW))
        generated = _squash(_read(WINDOW_GENERATED))
        self.assertIn("onclick = \"[GetVariableSystem.Set('te_systems_window_tab', 'grand_monuments')]\"", generated)
        self.assertIn("GetVariableSystem.HasValue('com_open_window', 'te_systems_window')", window)
        self.assertIn("GetVariableSystem.HasValue('te_systems_window_tab', 'grand_monuments')", generated)
        mount = re.search(r'name = "te_systems_window_grand_monuments_tab"(.*?)\}', generated).group(1)
        self.assertIn("te_gm_tab_body = {", mount)
        body = _type_body(_read(GUI), "te_gm_tab_body")
        gate = re.search(r'blockoverride "tab_gate" \{(.*?)\}', body, re.S).group(1)
        self.assertIn("GetScriptedGui('te_window_grand_monuments_tab_sgui').IsShown", gate)

    def test_every_rendered_key_exists(self):
        loc = _loc()
        keys = set(re.findall(r'(?:text|tooltip) = "([a-z]\w*)"', self.card))
        self.assertTrue(keys)
        for key in keys:
            self.assertIn(key, loc, key)

    def test_columns_are_the_cards_width(self):
        """120 picture + 10 + 380 = 510, the tourism card's inner width (the
        monument's picture shows at 120 on the card, spec 2026-10-11 §3.4);
        each row is 20 icon + 4 + label + 4 + value = 380, its bar 24 short
        of that; the titles stop short of the goto's 25 + 5 at the corner."""
        row = _squash(_type_body(self.gui, "te_state_gm_row"))
        label = int(re.search(r'"label_size" \{ size = \{ (\d+) ', row).group(1))
        value = int(re.search(r'"value_size" \{ size = \{ (\d+) ', row).group(1))
        self.assertEqual(20 + 4 + label + 4 + value, 380)
        picture = int(re.search(r"gm_picture = \{ size = \{ (\d+) ", self.flat).group(1))
        self.assertIn("spacing = 10", self.flat)
        self.assertEqual(picture + 10 + 380, 510)
        self.assertIn("minimumsize = { 380 -1 }", self.flat)
        self.assertIn("minimumsize = { 530 -1 }", self.flat)
        self.assertIn('"bar_size" { size = { 356 4 } }', self.flat)
        titles = [int(w) for w in re.findall(r"maximumsize = \{ (\d+) -1 \} align = left\|nobaseline "
                                             r"using = fontsize_large", self.flat)]
        self.assertEqual(len(titles), 2)
        for width in titles:
            self.assertLessEqual(width + 25 + 5, 380)

    def test_values_guard_their_reads(self):
        values = _read(VALUES)
        for name in ("gm_state_disp_tourism", "gm_state_disp_local"):
            body = _block(values, name)
            self.assertIsNotNone(body, name)
            for var in set(re.findall(r"var:(\w+)", body)):
                self.assertIn(f"has_variable = {var}", body, f"{name} reads var:{var} unguarded")

    def test_the_step_bar_follows_the_local_curve(self):
        """The local effects step on the 1/n curve (gm_curve_steps_lin_f5,
        owner 2026-10-19), so the card counts the same steps from the live
        level: the next step is the one after the whole steps done, ending at
        5 * n(n+1) / 2, and the bar is the fraction of the step count."""
        values = _read(VALUES)
        # Each dedication's local effect (ageing spec 2026-10-16 §4.2).
        monthly = _squash(_block(_read(EFFECTS), "gm_state_local_steps_one"))
        self.assertIn("value = gm_curve_steps_lin_f5 max = $CAP$", monthly)
        curve = _squash(_block(values, "gm_curve_steps_lin_f5"))
        steps = _squash(_block(values, "gm_state_disp_steps"))
        self.assertEqual(steps, curve.replace("var:gm_curve_in", "gm_state_grandeur"))
        self.assertEqual(_squash(_block(values, "gm_state_disp_step_n")),
                         "value = gm_state_disp_steps floor = yes add = 1 max = gm_curve_lin_steps")
        self.assertEqual(_squash(_block(values, "gm_state_disp_next_step")),
                         "value = gm_state_disp_step_n multiply = { value = gm_state_disp_step_n add = 1 } "
                         "multiply = 2.5")
        pct = _squash(_block(values, "gm_state_disp_step_pct"))
        self.assertEqual(pct, "value = gm_state_disp_steps subtract = { value = gm_state_disp_steps floor = yes } "
                              "multiply = 100 if = { limit = { gm_state_disp_steps >= gm_curve_lin_steps } "
                              "value = 100 } min = 0 max = 100")

    def test_the_card_formulas_match_the_curve(self):
        """The card's next step and bar, transcribed, at a step's start, its
        middle and just short of its end, and past the curve's last step."""
        def steps(g):
            return sum(min(max((g - 5 * k * (k - 1) / 2) / (5 * k), 0), 1) for k in range(1, 31))

        def card(g):
            s = steps(g)
            n = min(int(s) + 1, 30)
            pct = 100 if s >= 30 else (s - int(s)) * 100
            return n * (n + 1) * 2.5, pct
        for k in range(1, 31):
            start, end = 5 * k * (k - 1) / 2, 5 * k * (k + 1) / 2
            self.assertEqual(card(start)[0], end, k)
            self.assertAlmostEqual(card(start)[1], 0.0, msg=k)
            self.assertAlmostEqual(card((start + end) / 2), (end, 50.0), msg=k)
            self.assertAlmostEqual(card(end - 1e-9)[1], 100.0, places=4, msg=k)
        self.assertEqual(card(5000), (2325, 100))


class StateCardLabelBudgetTest(LabelBudgetTest):
    """The card's labels and values fit their cells: every label the local
    effect's custom localization can pick, too."""

    def test_effect_rows(self):
        row = _type_body(_read(STATE_GUI), "te_state_gm_row")
        label = int(re.search(r'"label_max_width" \{\s*max_width = (\d+)', row).group(1))
        value = int(re.search(r'"value_max_width" \{\s*max_width = (\d+)', row).group(1))
        custom = _read(CUSTOM_LOC)
        labels = set(re.findall(r"localization_key = (\w+)", _block(custom, "gm_local_effect_label")))
        values = set(re.findall(r"localization_key = (\w+)", _block(custom, "gm_local_effect_value")))
        self.assertTrue(labels and values)
        # And the unique dedications' rows (signatures spec §2.2, §8).
        for key in labels | {"gm_state_lbl_grandeur", "gm_state_lbl_tourism", "gm_state_lbl_sig_tourism",
                             "gm_state_lbl_sig_university"}:
            self._fits(key, (label, "fontsize_medium"))
        for key in values | {"gm_state_val_grandeur", "gm_state_val_tourism", "gm_state_val_sig_tourism",
                             "gm_state_val_sig_university"}:
            self._fits(key, (value, "fontsize_medium"), "-40,000")

    # The journal entry's own budgets are LabelBudgetTest's.
    test_the_flagged_labels_are_short = test_overview_captions = test_row_status_words = None
    test_choice_buttons = test_policy_buttons = test_naming_buttons = test_hard_times_phrase = None
    test_the_policy_line = test_every_textbox_names_a_panel_size = test_trophy_and_dig_buttons = None
    test_the_level_rate_line = None


class PictureLayoutTests(unittest.TestCase):
    """The monument's picture (spec 2026-10-11 §3.4): 96 px in the row, 120 px on the state card."""

    def test_row_and_card_show_the_picture(self):
        gui = open(GUI, encoding="utf-8-sig").read()
        row = gui[gui.index("type gm_monument_row"):]
        row = row[:row.index("\n\ttype ")] if "\n\ttype " in row else row
        self.assertRegex(row, r"gm_picture = \{\s*size = \{ 96 96 \}")
        card_src = open(os.path.join(REPO, "gui", "te_state_panel_widgets.gui"), encoding="utf-8-sig").read()
        card = card_src[card_src.index("type te_state_gm_card"):]
        self.assertRegex(card, r"gm_picture = \{\s*size = \{ 120 120 \}")
        self.assertRegex(card, r"minimumsize = \{ 380 -1 \}")



class AgeingPanelTests(unittest.TestCase):
    """Ageing rework (spec 2026-10-16 §6): a finished monument's levels and
    years on the card and its row; a monument beside another shows its status
    and grandeur, and its row in Our Monuments carries a contested one's
    three choices."""

    def test_the_finished_line(self):
        loc = _loc()
        card = _type_body(_read(STATE_GUI), "te_state_gm_card")
        row = _type_body(_gui(), "gm_monument_row")
        for body in (card, row):
            self.assertIn("ScriptValue('gm_state_disp_frozen')", body)
            self.assertIn('tooltip = "gm_row_frozen_tt"', body)
            self.assertIn('text = "gm_row_frozen"', body)
        self.assertIn("gm_state_primary_age", loc["gm_row_frozen"])
        self.assertIn("2% of its starting grandeur a year", loc["gm_row_frozen_tt"])
        self.assertIn("gm_state_primary_age", loc["gm_state_grandeur_tt_one"])

    def test_a_secondarys_row(self):
        loc = _loc()
        trophy_gui = _read("gui/gm_trophy_widgets.gui")
        site = _type_body(trophy_gui, "gm_mon_row_site")
        for code, key in ((2, "upheld"), (3, "heritage"), (4, "contested")):
            self.assertIn(f"ScriptValue('gm_mon_status_code'), '(CFixedPoint){code}'", site)
            self.assertIn(f'text = "gm_mon_row_status_{key}"', site)
            self.assertIn(f"gm_mon_row_status_{key}", loc)
        self.assertIn('block "mon_choices" {}', site)
        self.assertIn("ScriptValue('gm_mon_grandeur')", loc["gm_mon_row_value"])
        button = _type_body(trophy_gui, "gm_mon_choice_button")
        self.assertIn("AddScope( 'gm_mon', ScriptContainer.MakeScope )", button)
        je = _gui()
        for sgui in ("gm_mon_tear_down_sgui", "gm_mon_rededicate_sgui", "gm_mon_preserve_sgui"):
            self.assertIn(f"GetScriptedGui('{sgui}')", je)
        for key in ("gm_button_mon_tear_down_tooltip", "gm_button_mon_rededicate_tooltip",
                    "gm_button_mon_preserve_tooltip"):
            self.assertIn("AddScope( 'gm_mon', ScriptContainer.MakeScope )", loc[key])

class SignatureRowsTest(unittest.TestCase):
    """Signatures spec 2026-10-16 §8: a row per unique dedication in force, after
    the dedications' and before approval, each bar on its own curve; a held
    special's row under Opportunities Seized; the card's unique-dedication
    lines, hidden at 0."""

    def test_rows_in_order_between_the_dedications_and_approval(self):
        nat = _squash(_type_body(_gui(), "te_gm_sec_national"))
        positions = [nat.find(f'tooltip = "gm_je_tt_sig_{k}"') for k in SIG_ROWS]
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, sorted(positions))
        self.assertLess(nat.find('tooltip = "gm_je_tt_industrial"'), positions[0])
        self.assertLess(positions[-1], nat.find('text = "gm_je_sub_approval"'))
        for k in SIG_ROWS:
            self.assertIn(f"gm_step_row = {{ visible = \"[NotEqualTo_CFixedPoint( Country.MakeScope"
                          f".ScriptValue('gm_display_sig_{k}'), '(CFixedPoint)0' )]\" tooltip = \"gm_je_tt_sig_{k}\"",
                          nat, k)
            self.assertIn(f"ScriptValue('gm_disp_frac_sig_{k}')", nat, k)

    def test_each_bar_follows_its_curve(self):
        values = _read(SIG_VALUES)
        steps = _squash(_block(_read(SIG_EFFECTS), "gm_sig_set_steps"))
        self.assertIn("gm_set_steps = { IN = gm_g_sig_$SIG$ OUT = gm_s_sig_$SIG$ NEXT = gm_n_sig_$SIG$ F = 5 }", steps)
        sums = _squash(_block(_read(SIG_EFFECTS), "gm_sig_compute_sums"))
        for k in SIG_ROWS:
            body = _squash(_block(values, f"gm_disp_frac_sig_{k}"))
            if k == "antiquity":
                # Cultural pull, on the 1/n curve with no end (owner, 2026-10-19).
                self.assertIn("gm_sig_set_steps_lin_open = { SIG = antiquity }", sums)
                self.assertIn(f"value = var:gm_g_sig_{k} subtract = var:gm_n_sig_{k} add = var:gm_w_sig_{k} "
                              f"divide = var:gm_w_sig_{k}", body, k)
            else:
                self.assertIn(f"gm_sig_set_steps = {{ SIG = {k} }}", sums, k)
                self.assertIn(f"value = var:gm_g_sig_{k} multiply = 2 subtract = var:gm_n_sig_{k} add = 5 "
                              f"divide = {{ value = var:gm_n_sig_{k} add = 5 }}", body, k)
            self.assertTrue(body.endswith("min = 0 max = 1"), k)

    def test_held_specials_under_the_boons(self):
        """The specials held follow the last boon; the monument policy's
        heading and buttons open the section, above every effect row (GM-3,
        owner 2026-10-27)."""
        nat = _squash(_type_body(_gui(), "te_gm_sec_national"))
        last_boon = nat.find('tooltip = "gm_je_tt_boon_tech_naturalist"')
        policy = nat.find('text = "gm_je_sub_policy"')
        first_row = nat.find("gm_step_row = {")
        self.assertNotEqual(policy, -1)
        self.assertLess(policy, first_row)
        self.assertLess(policy, nat.find('text = "gm_je_sub_in_force"'))
        for k in SPECIALS:
            pos = nat.find(f'tooltip = "gm_je_tt_sig_held_{k}"')
            self.assertGreater(pos, last_boon, k)
            self.assertIn(f"ScriptValue('gm_disp_sig_held_{k}')", nat, k)

    def test_the_card_lines_hide_at_zero(self):
        card = _squash(_read(STATE_GUI))
        for value, tip in (("gm_state_disp_sig_tourism", "gm_state_sig_tourism_tt"),
                           ("gm_state_disp_sig_university", "gm_state_sig_university_tt")):
            self.assertIn(f"te_state_gm_row = {{ visible = \"[NotEqualTo_CFixedPoint(State.MakeScope.ScriptValue("
                          f"'{value}'), '(CFixedPoint)0')]\" blockoverride \"row_tooltip\" {{ tooltip = \"{tip}\" }}",
                          card, value)


class WideLayoutTest(unittest.TestCase):
    """te_gm_wide_sections, the window's full-screen Grand Monuments (spec
    2026-11-02-te-window-wide-mode § 7): the tab's sections in the three
    columns the owner set, under the narrow layout's gates."""

    def test_the_columns(self):
        # National Effects straight under the overview (owner, 2026-11-03).
        # Trophies and Held Abroad each show only while there is something in
        # them: column 3 closes up on their two gates, joined.
        assert_wide_matches_narrow(self, "te_gm_wide_sections", layout=("te_gm_tab_body", "te_gm_tab_layout"),
                                   added_gates=("te_gm_sec_trophies", "te_gm_sec_abroad"),
                                   columns=[["te_gm_overview_panel", "te_gm_sec_national", "te_gm_sec_commission",
                                             "te_gm_sec_decisions", "te_gm_sec_awaiting"],
                                            ["te_gm_sec_archaeology", "te_gm_sec_monuments"],
                                            ["te_gm_sec_trophies", "te_gm_sec_abroad"]])
        assert_column_closes_with_its_sections(self, "te_gm_wide_sections", 3, ["te_gm_sec_trophies", "te_gm_sec_abroad"])

    def test_the_window_mounts_it_full_screen(self):
        tab = next(t for t in window_gen.TABS if t.key == "grand_monuments")
        self.assertEqual((tab.layout, tab.wide), ("te_gm_tab_layout", "te_gm_wide_sections"))


class PrivateTest(unittest.TestCase):
    """What another country's National Info leaves out of Grand Monuments
    (owner call 5 of docs/superpowers/plans/2026-11-02-charts-help-national-info.md;
    spec § 6.4): the open opportunity and the interest groups' ledgers sit
    under te_own_country_only. Read as that panel draws te_gm_wide_sections
    (gui_test_helpers.panel_view: guarded parts and overridden block defaults
    left out) and the loc it renders. The gates stay outside the guards, so the
    player's own panel shows each part exactly when it did before."""

    @classmethod
    def setUpClass(cls):
        cls.types = mod_types()
        cls.view = panel_view({"te_gm_wide_sections"}, cls.types)
        cls.keys = panel_loc_keys({"te_gm_wide_sections"}, cls.types, load_loc())

    def _drawn(self, name):
        """A type's body as another country's panel draws it, its guarded parts blanked."""
        self.assertIn(name, self.view.open, f"{name}: another country's panel draws it")
        return _squash(unguarded(self.types[name].body, self.view.skip[name]))

    def test_the_open_opportunity(self):
        sec = self._drawn("te_gm_sec_commission")
        self.assertIn("visible = \"[EqualTo_CFixedPoint( Country.MakeScope.ScriptValue('gm_disp_com_open'), "
                      "'(CFixedPoint)1' )]\"", sec, "the gate stays on the root, read on the shown country")
        for gone in ("gm_je_commission_header", "gm_je_com_", "gm_disp_com_frac", "gm_com_raise_sgui",
                     "gm_com_let_pass_sgui"):
            self.assertNotIn(gone, sec)
        self.assertIn("gm_je_commission_header", self.types["te_gm_sec_commission"].body, "the player's has it")
        # A monument's row says it counts toward the open opportunity: the player's own line.
        row = self._drawn("gm_monument_row")
        self.assertIn("ScriptValue('gm_state_disp_com_counts')", row, "the line's gate is the wrapper's")
        self.assertNotIn("gm_row_com_counts", row)
        self.assertFalse(sorted(k for k in self.keys if k.startswith(("gm_je_com_", "gm_button_com_", "gm_row_com_"))))

    def test_the_interest_groups_ledgers(self):
        nat = self._drawn("te_gm_sec_national")
        self.assertIn("ScriptValue('gm_disp_ig_any')", nat, "the group's gate is the wrapper's")
        for ig in IGS:
            self.assertNotIn(f"gm_display_ig_{ig}", nat, ig)
            self.assertNotIn(f"gm_je_tt_ig_{ig}", self.keys, ig)
        for key in ("gm_je_sub_approval", "gm_je_tt_ig"):
            self.assertNotIn(key, self.keys)
        # The national effects, the fading legitimacy and the boons are the country's, and public.
        for key in ("gm_je_tt_prestige", "gm_je_tt_legitimacy", "gm_je_tt_sig_antiquity", "gm_je_tt_teardown",
                    "gm_je_tt_vanity", "gm_je_tt_boon_reign", "gm_je_tt_sig_held_olympic"):
            self.assertIn(key, self.keys, key)

    def test_the_rest_is_public(self):
        """Monuments built and under way, the national effects, trophies,
        works abroad and archaeology (spec § 6.4), without their controls
        (test_te_system_tab_bodies.py's GuardTest)."""
        for name in ("te_gm_overview_panel", "te_gm_sec_decisions", "te_gm_sec_awaiting", "te_gm_sec_archaeology",
                     "te_gm_sec_national", "te_gm_sec_monuments", "te_gm_sec_trophies", "te_gm_sec_abroad",
                     "gm_monument_row", "gm_site_row", "gm_mon_row_site", "gm_tr_row_held", "gm_tr_row_abroad",
                     "gm_arch_row_digging", "gm_arch_row_open"):
            self.assertIn(name, self.view.open, name)
        for key in ("gm_je_monuments_header_theirs", "gm_je_ov_monuments_label_theirs", "gm_tr_row_held_by",
                    "gm_je_tr_summary", "gm_je_abroad_summary", "gm_je_arch_summary", "gm_site_row_title"):
            self.assertIn(key, self.keys, key)
        for key in ("gm_je_monuments_header_ours", "gm_je_ov_monuments_label_ours", "gm_tr_row_held_by_tt"):
            self.assertNotIn(key, self.keys, f"{key}: the player's own")


_BARE_SGUI = re.compile(r"(?<![\w.'])ScriptedGui\.")


def _controls_gate(guarded, types):
    """The gate of the wrapper round a guarded wrapper: the player's own
    (Country.IsLocalPlayer) and any of its controls shown. Each control's own
    visible as written (a type instance's from its type's root), a bare
    `ScriptedGui.` read through the control's own datacontext, and GetPlayer
    on Country, the same country under that first test. Or nests in pairs."""
    terms = []
    for kind, name, inner in _children(guarded):
        if kind != "widget":
            continue
        own = {k: v for got, k, v in _children(inner) if got == "property"}
        if "visible" not in own and name in types:
            own = {k: v for got, k, v in _children(types[name].body) if got == "property"}
        assert "visible" in own, f"{name}: a control shown always, so the gate would be too"
        expr = own["visible"].strip('"')
        assert expr.startswith("[") and expr.endswith("]"), expr
        expr = expr[1:-1].strip()
        if _BARE_SGUI.search(expr):
            sgui = re.fullmatch(r'"\[(GetScriptedGui\( *\'\w+\' *\))\]"', own["datacontext"]).group(1)
            expr = _BARE_SGUI.sub(sgui + ".", expr)
        terms.append(expr.replace("GetPlayer.", "Country."))
    gate = terms[-1]
    for term in reversed(terms[:-1]):
        gate = f"Or( {term}, {gate} )"
    return f"[And( Country.IsLocalPlayer, {gate} )]"


def _gated_guard(block):
    """The one widget in `block` and its visible, and the te_own_country_only
    wrapper that is that widget's one widget."""
    outer = [(name, inner) for kind, name, inner in _children(block) if kind == "widget"]
    assert len(outer) == 1, [name for name, _ in outer]
    props = {k: v for kind, k, v in _children(outer[0][1]) if kind == "property"}
    inner = [(name, body) for kind, name, body in _children(outer[0][1]) if kind == "widget"]
    assert len(inner) == 1, [name for name, _ in inner]
    guarded = {k: v for kind, k, v in _children(inner[0][1]) if kind == "property"}
    assert guarded.get("using") == "te_own_country_only", guarded
    assert "using" not in props and "visible" not in guarded, (props, guarded)
    return props.get("visible", ""), inner[0][1]


class ControlsGateTest(unittest.TestCase):
    """A wrapper that stands empty still takes its parent's spacing, so the
    wrapper round a row's guarded controls is gated on the player's own country
    and on its controls' own visibles (review of PR #1355, I2): the row is as
    tall as before for the player, and for another country it ends at its
    last line. The gate is pinned to the controls, so the two can't drift."""

    @classmethod
    def setUpClass(cls):
        cls.types = mod_types()

    def test_a_monuments_rows_controls(self):
        row = self.types["gm_monument_row"].body
        widgets = [(name, inner) for kind, name, inner in _children(row) if kind == "widget"]
        self.assertEqual(len(widgets), 2, "the header and the controls")
        gate, guarded = _gated_guard("flowcontainer = {" + widgets[1][1] + "}")
        self.assertEqual(_squash(gate.strip('"')), _squash(_controls_gate(guarded, self.types)))
        names = [name for kind, name, _ in _children(guarded) if kind == "widget"]
        self.assertEqual(names[-3:], ["flowcontainer", "gm_tr_take_button", "gm_clear_button"])
        self.assertIn("gm_naming_line", names)

    def test_our_monuments_beside_rows_controls(self):
        sec = self.types["te_gm_sec_monuments"].body
        m = re.search(r'blockoverride "mon_controls" \{', sec)
        self.assertTrue(m)
        block = _block_at(sec, m.start())
        gate, guarded = _gated_guard(block[block.index("{") + 1:-1])
        self.assertEqual(_squash(gate.strip('"')), _squash(_controls_gate(guarded, self.types)))
        self.assertEqual([name for kind, name, _ in _children(guarded) if kind == "widget"],
                         ["gm_mon_take_button", "gm_mon_clear_button"])
        # The type keeps its default, which the state card draws.
        self.assertIn('block "mon_controls" { gm_mon_take_button = {} gm_mon_clear_button = {} }',
                      _squash(self.types["gm_mon_row_site"].body))

    def test_the_gate_reads_each_controls_own_visible(self):
        guarded = ('flowcontainer = { visible = "[A( GetPlayer.Self )]" }\n'
                   "gm_tr_take_button = {}\n")
        gate = _controls_gate(guarded, self.types)
        self.assertTrue(gate.startswith("[And( Country.IsLocalPlayer, Or( A( Country.Self ), "
                                        "And( Not( GetMetaPlayer.IsObserver ), GetScriptedGui('gm_tr_take_sgui')"
                                        ".IsShown( GuiScope.SetRoot( Country.MakeScope )"), gate)

    def test_another_countrys_empty_wrappers_hide(self):
        """The two gates kept outside a guard (a row's counts-toward line, the
        groups' ledgers) also test the player's own country, so another
        country's panel has no empty wrapper there (review M3)."""
        row = _squash(self.types["gm_monument_row"].body)
        self.assertIn("flowcontainer = { visible = \"[And( Country.IsLocalPlayer, EqualTo_CFixedPoint( State.MakeScope"
                      ".ScriptValue('gm_state_disp_com_counts'), '(CFixedPoint)1' ) )]\" direction = vertical "
                      "ignoreinvisible = yes flowcontainer = { using = te_own_country_only", row)
        nat = _squash(self.types["te_gm_sec_national"].body)
        self.assertIn("flowcontainer = { visible = \"[And( Country.IsLocalPlayer, EqualTo_CFixedPoint( Country"
                      ".MakeScope.ScriptValue('gm_disp_ig_any'), '(CFixedPoint)1' ) )]\" direction = vertical "
                      "ignoreinvisible = yes flowcontainer = { using = te_own_country_only", nat)


class HeldByLineTest(unittest.TestCase):
    """Works Abroad's holder line, twice (review of PR #1355, M1): the player's
    with the ways home on hover, under the guard, and another country's without
    them, shown only there. One line either way."""

    def test_the_pair(self):
        def lines(body):
            for kind, name, inner in _children(body):
                if kind not in ("widget", "block", "blockoverride"):
                    continue
                if any(got == "property" and k == "text" and v == '"gm_tr_row_held_by"'
                       for got, k, v in _children(inner)):
                    yield inner
                else:
                    yield from lines(inner)

        lines = list(lines(mod_types()["gm_tr_row_abroad"].body))
        self.assertEqual(len(lines), 2)
        props = [{k: v for kind, k, v in _children(inner) if kind == "property"} for inner in lines]
        self.assertEqual(props[0], {"using": "te_own_country_only", "tooltip": '"gm_tr_row_held_by_tt"',
                                    "text": '"gm_tr_row_held_by"'})
        self.assertEqual(props[1], {"visible": '"[Not( Country.IsLocalPlayer )]"', "text": '"gm_tr_row_held_by"'})


class StateCardCountryTest(unittest.TestCase):
    """The state panel's Grand Monument cards have a State and no Country
    (states_panel.gui:1458-1459, te_state_gm_card and te_state_gm_site_card set
    none; review of PR #1355, I3). So nothing they draw reads Country: no type's
    markup, no te_own_country_only (it reads Country.IsLocalPlayer), no key they
    render or splice. The five buttons they share with the panel keep GetPlayer;
    in the panel they sit under its guard, where the player is the shown country."""

    CARDS = {"te_state_gm_card", "te_state_gm_site_card"}
    BUTTONS = {"gm_dedicate_button": "gm_button_dedicate_tooltip", "gm_tr_take_button": "gm_button_tr_take_tooltip",
               "gm_mon_take_button": "gm_mon_take_button_tooltip", "gm_clear_button": "gm_button_clear_tooltip",
               "gm_mon_clear_button": "gm_mon_clear_button_tooltip"}
    COUNTRY = re.compile(r"(?<![\w.])Country\.|\busing\s*=\s*te_own_country_only\b")

    @classmethod
    def setUpClass(cls):
        cls.types = mod_types()
        cls.loc = load_loc()
        cls.drawn = type_closure(cls.CARDS, cls.types)

    def _keys(self, names):
        keys = set()
        for name in names:
            keys |= gui_keys(self.types[name].body, self.loc, own=False)
        return loc_closure(keys, self.loc, own=False)

    def test_the_cards_draw_the_five_buttons(self):
        self.assertLessEqual(set(self.BUTTONS), self.drawn)
        for button, key in self.BUTTONS.items():
            self.assertIn(f'tooltip = "{key}"', self.types[button].body, button)

    def test_nothing_the_cards_draw_reads_country(self):
        markup = [(name, self.types[name].body[m.start():m.start() + 60]) for name in sorted(self.drawn)
                  for m in self.COUNTRY.finditer(self.types[name].body)]
        self.assertEqual(markup, [])
        keys = self._keys(self.drawn)
        self.assertLessEqual(set(self.BUTTONS.values()), keys)
        self.assertEqual(sorted(k for k in keys if self.COUNTRY.search(self.loc[k])), [])

    def test_the_five_buttons_read_the_player(self):
        for button, key in self.BUTTONS.items():
            body = self.types[button].body
            self.assertIn("GetPlayer.MakeScope", body, button)
            self.assertIsNone(self.COUNTRY.search(body), button)
            self.assertEqual(sorted(k for k in self._keys({button}) if self.COUNTRY.search(self.loc[k])), [], key)


class ReviewedPersonalTextTest(unittest.TestCase):
    """A loc line tagged `# REVIEWED YYYY-MM-DD (personal_text): why` holds a
    proper name, not the panel speaking as the player
    (gui_test_helpers._personal_reviewed): personal_text leaves it out, and the
    same text untagged still counts. The boon "Lest We Forget" is one."""

    def test_the_tag_is_read_from_the_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "fx_l_english.yml"), "w", encoding="utf-8-sig") as f:
                f.write("l_english:\n"
                        ' fx_tagged:0 "Lest We Forget" # REVIEWED 2026-11-03 (personal_text): a proper name\n'
                        ' fx_other:0 "We Stand" # REVIEWED 2026-11-03 (event_context): another audit\'s\n'
                        ' fx_plain:0 "We Stand"\n'
                        ' fx_in_text:0 "# REVIEWED 2026-11-03 (personal_text): in the value"\n')
            self.assertEqual(_personal_reviewed(tmp), frozenset({"fx_tagged"}))

    def test_a_tagged_key_passes_and_an_untagged_one_fails(self):
        self.assertIn("gm_boon_defeat", _personal_reviewed(LOC_DIR))
        self.assertEqual(load_loc()["gm_boon_defeat"], "Lest We Forget")
        texts = {"gm_boon_defeat": "Lest We Forget", "fx_untagged": "Lest We Forget"}
        self.assertEqual(personal_text(set(texts), texts), {"fx_untagged": "Lest We Forget"})


if __name__ == "__main__":
    unittest.main()
