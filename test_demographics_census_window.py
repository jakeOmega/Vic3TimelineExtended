"""National Info, the Census Data window, and the country its Demographics tab reads.

Vanilla's Census Data window (gui/pop_browser_panel.gui, the pop browser) lists
the pops of whichever country it was opened for. The mod renames it National
Info ("French National Info" for France) and adds a strip over it: Pops
(vanilla's window), then a tab for each system another country's panel may show
(gen_te_systems_window.TABS' public tabs: Demographics so far), generated into
gui/te_national_info_generated.gui (test_national_info.py holds what it writes).
Demographics is the census of that same country, from the sections the
Population panel's Demographics tab draws.

For that, the country's sections read the Country in their context rather than
the player: the Population panel's window sets it to the player (AccessPlayer),
the Census Data window to its own country (PopBrowserPanel.GetCountry). So this
file holds:

* the override to vanilla's file (test_fixtures/vanilla_gui/pop_browser_panel.gui):
  lines added inside `### MOD: National Info` blocks, none removed;
* the strip, its gates and the tab key (te_ni_tab), as the window places them;
* that nothing the country's sections draw reads GetPlayer, in the markup or in
  any loc key they reach (that none of that text says "our" or "your" is
  test_te_system_tab_bodies.py's BindingTest's, for every public tab);
* that the controls which change a country (the pension and Family Policy
  buttons) show only for the player's own;
* that nothing the Census Data window draws reads the Population panel's own
  data (PopsOverviewPanel), which only that panel's window holds.
"""
import difflib
import json
import os
import re
import unittest
from pathlib import Path

from gui_test_helpers import gui_keys, history_charts, load_loc, loc_closure, type_bodies
from scripts.generators import gen_te_systems_window as gen

ROOT = Path(__file__).resolve().parent
OVERRIDE = ROOT / "gui" / "pop_browser_panel.gui"
FIXTURE = ROOT / "test_fixtures" / "vanilla_gui" / "pop_browser_panel.gui"
WIDGETS = ROOT / "gui" / "te_demographics_widgets.gui"
LAYOUT = ROOT / "gui" / "te_demographics_layout.gui"
SGUIS = ROOT / "common" / "scripted_guis" / "te_demog_sguis.txt"
VANILLA_LOC = ROOT / "vanilla_parsed" / "localization_english.json"

MOD_OPEN = "### MOD: National Info"
MOD_CLOSE = "### END MOD ###"
GENERATED = ROOT / "gui" / "te_national_info_generated.gui"
FLAG, FLAG_VALUE = "te_ni_tab", "demographics"
RULE = "GetScriptedGui('te_pops_demog_tab_sgui').IsShown( GuiScope.SetRoot( Country.MakeScope ).End )"
UNLOCK = "GetScriptedGui('te_pops_demog_tab_unlock_sgui').IsValid( GuiScope.SetRoot( Country.MakeScope ).End )"
# Demographics is shown: chosen last, the rule on and the country's first census taken
SHOWN = f"And( GetVariableSystem.HasValue('{FLAG}', '{FLAG_VALUE}'), And( {RULE}, {UNLOCK} ) )"

# The composers of the country's sections, one a host.
COMPOSERS = ("te_demog_tab_sections", "te_demog_browser_sections")
# Loc keys the Help page reaches that read GetPlayer, as a popup must (it has no Country in context, spec
# 2026-11-02-charts-help-national-info § 5.2), and read only a constant (te_demog_k_conscription_ref).
HELP_PAGE_GETPLAYER = {"te_demog_fam_rule"}
# The Help page's types (te_demographics_help_body, _popup): not a section of the panel, so not read for its country.
# Its keys are left out of the pronoun rule (test_te_system_tab_bodies.py's test_the_text_is_not_the_players) on
# purpose: the page explains the player's own rules and never shows another country (Covert Warfare's page says "our"
# too).
HELP_PAGE = re.compile(r"^te_demographics_help_")
# The Population panel's own data: its window holds it and the Census Data window doesn't, so a key that reads it (as
# vanilla's POPS_OVERVIEW_AVERAGE_INCOME_* keys do) renders only in the Population panel.
POPULATION_PANEL_ONLY = "PopsOverviewPanel."


def read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def block_from(text, start):
    j = text.index("{", start)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j:k + 1]
    raise AssertionError("unbalanced block")



def code(text):
    """The markup less its comments (no quoted value here holds a #)."""
    return "\n".join(line.split("#", 1)[0] if not re.search(r'"[^"]*#', line) else line
                     for line in text.splitlines() if not line.lstrip().startswith("#"))





def without_blocks(text, names):
    """`text` less each `block "<name>" { ... }` for a name in `names`: what a host draws that blanks them."""
    for name in names:
        while (m := re.search(rf'(?<![\w"])block "{name}" \{{', text)):
            body = block_from(text, m.end() - 1)
            text = text[:m.start()] + text[m.end() - 1 + len(body):]
    return text


def blanked_blocks(composer, sections):
    """For each of `sections` a composer instances, the blocks it blanks with an empty blockoverride."""
    out = {}
    for m in re.finditer(r"(?m)^\s*(\w+) = \{", composer):
        if m.group(1) not in sections:
            continue
        instance = block_from(composer, m.end() - 1)
        names = re.findall(r'blockoverride "(\w+)" \{\s*\}', instance)
        if names:
            out.setdefault(m.group(1), set()).update(names)
    return out


def installed_game():
    """The installed game's `game/` folder, or None (CI, dummy VIC3_BASE_GAME)."""
    base = os.environ.get("VIC3_BASE_GAME")
    if base is None:
        try:
            import path_constants
            base = path_constants.base_game_path
        except Exception:
            return None
    game = Path(base) / "game"
    return game if (game / "gui").is_dir() else None


class OverrideTest(unittest.TestCase):
    """Vanilla's file, with lines added inside MOD blocks and none taken away."""

    @classmethod
    def setUpClass(cls):
        cls.vanilla = FIXTURE.read_text(encoding="utf-8").splitlines()
        cls.mod = read(OVERRIDE).splitlines()

    def test_the_override_carries_the_bom_and_the_fixture_none(self):
        self.assertTrue(OVERRIDE.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertFalse(FIXTURE.read_bytes().startswith(b"\xef\xbb\xbf"), "the fixture is vanilla's bytes")

    def test_every_change_is_an_addition_inside_a_mod_block(self):
        regions, opened = [], None
        for i, line in enumerate(self.mod):
            if line.strip().startswith(MOD_OPEN):
                self.assertIsNone(opened, f"line {i + 1}: nested MOD block")
                opened = i
            elif line.strip() == MOD_CLOSE:
                self.assertIsNotNone(opened, f"line {i + 1}: END MOD without MOD")
                regions.append((opened, i))
                opened = None
        self.assertIsNone(opened, "unclosed MOD block")
        self.assertEqual(len(regions), 7, "the header, the show state's clear, the strip, two vanilla rows' gates, "
                                          "the tabs' column and the chart viewers")
        # Without its MOD blocks the override is vanilla's file, line for line (blank lines aside): nothing changed,
        # nothing removed, nothing added outside a block.
        inside = {i for a, b in regions for i in range(a, b + 1)}
        rest = [line for i, line in enumerate(self.mod) if i not in inside and line.strip()]
        vanilla = [line for line in self.vanilla if line.strip()]
        diff = list(difflib.unified_diff(vanilla, rest, "vanilla", "override less its MOD blocks", lineterm="", n=1))
        self.assertEqual(rest, vanilla, "\n".join(diff[:40]))

    def test_the_fixture_is_the_installed_file(self):
        game = installed_game()
        if game is None:
            self.skipTest("installed game not found")
        self.assertEqual(FIXTURE.read_bytes(), (game / "gui" / "pop_browser_panel.gui").read_bytes(),
                         "vanilla changed: merge it into gui/pop_browser_panel.gui and refresh the fixture")


def _template(text, name):
    m = re.search(rf'^template {name} \{{\n\tvisible = "\[(.*)\]"\n\}}', text, re.M)
    assert m, f"no template {name}"
    return m.group(1)


class StripTest(unittest.TestCase):
    """The window's strip and its column, as it places the generated pieces
    (test_national_info.py holds the pieces themselves)."""

    @classmethod
    def setUpClass(cls):
        cls.text = code(read(OVERRIDE))
        cls.generated = code(read(GENERATED))

    def test_the_strip_shows_while_the_rule_runs(self):
        self.assertEqual(self.text.count("te_ni_strips = {}"), 1)
        row = block_from(self.text, self.text[:self.text.index("te_ni_strips = {}")].rindex("hbox = {"))
        self.assertIn("using = te_ni_strip_shown", row)
        self.assertNotIn("tab_buttons", self.text, "the strip is generated")
        # Demographics the one public tab: the strip shows while its rule runs the census
        self.assertEqual(_template(self.generated, "te_ni_strip_shown"),
                         "GetScriptedGui('te_pops_demog_tab_unlock_sgui').IsShown( GuiScope.SetRoot( "
                         "Country.MakeScope ).End )")
        strip = block_from(self.generated, self.generated.index("type te_ni_strips"))
        self.assertEqual(set(re.findall(r'blockoverride "(\w+?)_button', strip)), {"first", "second"},
                         "the other slots stay hidden")
        self.assertIn('text = "te_pop_browser_tab_pops"', strip)
        self.assertIn('text = "te_window_tab_demographics"', strip)

    def test_the_demographics_tab_opens_with_the_countrys_first_census(self):
        strip = block_from(self.generated, self.generated.index("type te_ni_strips"))
        click = block_from(strip, strip.index('blockoverride "second_button_click"'))
        self.assertIn(f'enabled = "[And( {RULE}, {UNLOCK} )]"', click)
        self.assertIn(f"GetVariableSystem.Set('{FLAG}', '{FLAG_VALUE}')", click)
        first = block_from(strip, strip.index('blockoverride "first_button_click"'))
        self.assertIn(f"GetVariableSystem.Set('{FLAG}', 'pops')", first)
        self.assertEqual(_template(self.generated, "te_ni_demographics_selected"), SHOWN)

    def test_the_tabs_take_the_place_of_vanillas_rows(self):
        # vanilla's header row and its filters, charts and table: each shown exactly while Pops is
        self.assertEqual(self.text.count("using = te_ni_pops_selected"), 2)
        self.assertEqual(_template(self.generated, "te_ni_pops_selected"), f"Not( {SHOWN} )")
        content = block_from(self.text, self.text.index('name = "te_ni_content"') - 40)
        self.assertIn("using = te_ni_content_shown", content)
        self.assertIn("te_ni_tabs = {}", content)
        self.assertEqual(self.text.count("te_ni_tabs = {}"), 1)
        self.assertEqual(_template(self.generated, "te_ni_content_shown"), SHOWN)
        # the census: the player's own country's mount and another country's, each the browser's three columns
        self.assertNotIn("te_demog_browser_sections", self.text)
        self.assertEqual(self.generated.count("te_demog_browser_sections = {}"), 2)

    def test_the_old_flag_is_gone(self):
        for path in (OVERRIDE, GENERATED, LAYOUT, WIDGETS):
            self.assertNotIn("te_pop_browser_demog", read(path))

    def test_a_viewer_left_open_never_reopens_with_the_window(self):
        show = self.text[self.text.index('blockoverride "animation_state_block"'):]
        show = block_from(show, show.index("state = {"))
        self.assertIn("name = _show", show)
        self.assertIn("on_start = \"[GetVariableSystem.Clear('te_ni_chart')]\"", show)

    def test_the_window_keeps_its_country(self):
        self.assertIn('datacontext = "[PopBrowserPanel.GetCountry]"', self.text)
        self.assertNotIn("GetPlayer", self.text, "the window's tabs read its own country")
        self.assertEqual([t.key for t in gen.ni_tabs()], ["demographics"])


class NameTest(unittest.TestCase):
    """The window's name (spec § 6.2): POP_BROWSER, its title, the Population panel's button and the Politics tab's,
    renamed in the replace loc, with vanilla's adjective for another country kept."""

    def test_the_window_is_national_info(self):
        loc = load_loc()
        self.assertEqual(loc["POP_BROWSER"], "[AddLocalizationIf(Not(Country.IsLocalPlayer), "
                                             "Concatenate(Country.GetAdjective, ' '))]National Info")
        with open(VANILLA_LOC, encoding="utf-8") as f:
            vanilla = dict(json.load(f))["POP_BROWSER"]
        self.assertEqual(vanilla.replace("Census Data", "National Info"), loc["POP_BROWSER"], "vanilla's splice kept")
        self.assertIn('text = "POP_BROWSER"', read(OVERRIDE))
        for key in ("te_pop_browser_tab_demog_tt", "te_pop_browser_tab_demog_pending_tt"):
            self.assertNotIn(key, loc, "the strip's tooltips are the generated ones now")


class CountryContextTest(unittest.TestCase):
    """The country's sections read the Country in their context, so the Census Data window shows its own country's
    figures; GetPlayer there would show the player's."""

    @classmethod
    def setUpClass(cls):
        cls.loc = load_loc()
        widgets = type_bodies(read(WIDGETS))
        layout = type_bodies(read(LAYOUT))
        cls.country = {name: code(body) for name, body in widgets.items()
                       if not name.startswith("te_state_") and not HELP_PAGE.match(name)}
        cls.help = {name: code(body) for name, body in widgets.items() if HELP_PAGE.match(name)}
        cls.country.update({name: code(layout[name]) for name in COMPOSERS})
        cls.state = {name: code(body) for name, body in widgets.items() if name.startswith("te_state_")}
        cls.state["te_state_demog_content"] = code(layout["te_state_demog_content"])
        cls.keys = loc_closure(set().union(*(gui_keys(b, cls.loc) for b in cls.country.values())), cls.loc)

    def test_the_markup_reads_the_context_country(self):
        for name, body in self.country.items():
            with self.subTest(type=name):
                # the charts' one read of the year, the same for every country, is in their generated wrappers,
                # under a `# world:` line (test_te_system_tab_bodies.py's BindingTest)
                self.assertEqual(body.count("GetPlayer"), 0)
                self.assertNotIn("AccessPlayer", body)
        self.assertGreater(sum(b.count("Country.MakeScope") for b in self.country.values()), 300)

    def test_the_loc_reads_the_context_country(self):
        self.assertGreater(len(self.keys), 500)
        for key in sorted(self.keys):
            with self.subTest(key=key):
                self.assertNotIn("GetPlayer", self.loc[key])
                self.assertNotIn("AccessPlayer", self.loc[key])

    def test_the_help_pages_player_reads_are_constants(self):
        help_keys = loc_closure(set().union(*(gui_keys(b, self.loc) for b in self.help.values())), self.loc)
        self.assertIn("te_demographics_help_body", self.help)
        self.assertEqual({k for k in help_keys if "GetPlayer" in self.loc[k]}, HELP_PAGE_GETPLAYER)
        for key in HELP_PAGE_GETPLAYER:
            with self.subTest(key=key):
                self.assertNotIn(key, self.keys, "a live section reads it too")
                for read_ in re.findall(r"GetPlayer\.MakeScope\.(\w+\('[\w]+'\))", self.loc[key]):
                    self.assertRegex(read_, r"^ScriptValue\('te_demog_k_\w+'\)$")

    def test_the_state_never_reads_the_context_country(self):
        # the state panel has a State, not a Country, in context
        for name, body in self.state.items():
            with self.subTest(type=name):
                self.assertNotRegex(body, r"(?<![\w.])Country\.")

    def test_the_new_keys_exist(self):
        for key in ("te_pop_browser_tab_pops", "te_pop_browser_tab_pops_tt", "te_history_untracked",
                    "te_demog_pyr_outline_next",
                    "te_demog_pyr_outline_played"):
            with self.subTest(key=key):
                self.assertIn(key, self.loc)


class BrowserContextTest(unittest.TestCase):
    """The Census Data window has no Population panel in its context, so nothing it draws may read that panel's data.
    Vanilla's POPS_OVERVIEW_AVERAGE_INCOME_* keys read PopsOverviewPanel: in the window's Wealth section they logged nine
    lines a frame, about 40,000 in two minutes (2026-10-31). The checks above read only the mod's loc, so vanilla's keys
    passed them; these read vanilla's under the mod's."""

    @classmethod
    def setUpClass(cls):
        with open(VANILLA_LOC, encoding="utf-8") as f:
            cls.loc = dict(json.load(f))
        cls.loc.update(load_loc())
        widgets = {name: body for name, body in type_bodies(read(WIDGETS)).items() if not name.startswith("te_state_")}
        layout = type_bodies(read(LAYOUT))
        cls.browser = cls.host(widgets, code(layout["te_demog_browser_sections"]), "te_demog_browser_sections")
        cls.tab = cls.host(widgets, code(layout["te_demog_tab_sections"]), "te_demog_tab_sections")
        # the Timeline Extended window's tab, which has no Population panel either
        cls.window = cls.host(widgets, code(layout["te_demog_window_sections"]), "te_demog_window_sections")
        cls.window["te_demog_window_body"] = code(layout["te_demog_window_body"])

    @staticmethod
    def host(widgets, composer, name):
        """What a host draws: the sections less the blocks its composer blanks, and the composer."""
        blanked = blanked_blocks(composer, widgets)
        out = {section: code(without_blocks(body, blanked.get(section, ()))) for section, body in widgets.items()}
        out[name] = composer
        return out

    def reached(self, bodies):
        return loc_closure(set().union(*(gui_keys(b, self.loc) for b in bodies.values())), self.loc)

    def test_the_window_draws_nothing_that_reads_the_population_panel(self):
        for name, body in self.browser.items():
            with self.subTest(type=name):
                self.assertNotIn(POPULATION_PANEL_ONLY, body)
        for key in sorted(self.reached(self.browser)):
            with self.subTest(key=key):
                self.assertNotIn(POPULATION_PANEL_ONLY, self.loc[key])

    def test_the_te_window_draws_nothing_that_reads_the_population_panel(self):
        for name, body in self.window.items():
            with self.subTest(type=name):
                self.assertNotIn(POPULATION_PANEL_ONLY, body)
        for key in sorted(self.reached(self.window)):
            with self.subTest(key=key):
                self.assertNotIn(POPULATION_PANEL_ONLY, self.loc[key])

    def test_the_population_panel_keeps_the_strata_incomes(self):
        keys = self.reached(self.tab)
        for strata in ("LOW", "MIDDLE", "UPPER"):
            for suffix in ("", "_TOOLTIP"):
                with self.subTest(key=f"POPS_OVERVIEW_AVERAGE_INCOME_{strata}_LABEL{suffix}"):
                    self.assertIn(f"POPS_OVERVIEW_AVERAGE_INCOME_{strata}_LABEL{suffix}", keys)


class ControlsTest(unittest.TestCase):
    """A control that changes a country shows only for the player's own."""

    @classmethod
    def setUpClass(cls):
        cls.widgets = type_bodies(read(WIDGETS))

    def test_every_execute_is_the_players(self):
        for name, body in self.widgets.items():
            if name.startswith("te_state_"):
                continue
            for m in re.finditer(r"ScriptedGui\.Execute", body):
                with self.subTest(type=name, at=m.start()):
                    self.assertIn(name, ("te_demog_measure_row", "te_demog_pension_button"))

    def test_the_measure_button_keeps_its_slot(self):
        row = self.widgets["te_demog_measure_row"]
        button = block_from(row, row.index("button = {"))
        self.assertIn("using = te_own_country_only", button)
        slot = row[:row.index("button = {")].rsplit("widget = {", 1)[1]
        self.assertIn("size = { 72 24 }", slot, "an empty slot of the button's size for another country")

    def test_the_pension_buttons_and_notes_are_the_players(self):
        work = self.widgets["te_demog_sec_work"]
        rows = [block_from(work, m.start()) for m in re.finditer(r"flowcontainer = \{", work)
                if "te_demog_pension_button = {" in block_from(work, m.start())
                and "te_demog_figure_row" not in block_from(work, m.start())]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIn("using = te_own_country_only", row)
        for note in ("te_demog_wk_buttons_full_only", "te_demog_wk_buttons_term"):
            at = work.index(f'text = "{note}"')
            box = work[:at].rsplit("te_demog_text = {", 1)[1]
            with self.subTest(note=note):
                self.assertIn('visible = "[And( Country.IsLocalPlayer, ', box)


class GatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sguis = read(SGUIS)

    def test_the_outline_is_a_played_countrys(self):
        body = block_from(self.sguis, self.sguis.index("te_demog_outline_ready_sgui = {"))
        self.assertIn("is_ai = no", body)
        self.assertIn("has_variable = te_dg_pjf0", body)

    def test_the_history_gate_asks_whether_the_country_is_tracked(self):
        # the shared gate and key every chart's empty state uses (te_history_chart.gui, plan F1.5)
        sguis = read(ROOT / "common" / "scripted_guis" / "te_history_scripted_gui.txt")
        body = block_from(sguis, sguis.index("te_history_tracked_sgui = {"))
        self.assertIn("te_history_country_is_tracked = yes", body)
        self.assertNotIn("te_demog_hist_tracked_sgui", self.sguis)
        charts = history_charts(type_bodies(read(WIDGETS))["te_demog_sec_history"])
        self.assertEqual(len(charts), 8)
        for chart in charts:
            self.assertEqual(chart.count("GetScriptedGui('te_history_tracked_sgui').IsShown( GuiScope.SetRoot( "
                                         "Country.MakeScope ).End ), 'te_demog_hist_empty', 'te_history_untracked'"), 1)


if __name__ == "__main__":
    unittest.main()
