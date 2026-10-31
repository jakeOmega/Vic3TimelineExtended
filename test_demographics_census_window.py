"""The Demographics tab of the Census Data window, and the country it reads.

Vanilla's Census Data window (gui/pop_browser_panel.gui, the pop browser) lists
the pops of whichever country it was opened for: "Census Data" for the player's,
"French Census Data" for France. The mod's override adds a strip of two tabs over
it, Pops (vanilla's window) and Demographics, the census of that same country,
from the sections the Population panel's Demographics tab draws.

For that, the country's sections read the Country in their context rather than
the player: the Population panel's window sets it to the player (AccessPlayer),
the Census Data window to its own country (PopBrowserPanel.GetCountry). So this
file holds:

* the override to vanilla's file (test_fixtures/vanilla_gui/pop_browser_panel.gui):
  lines added inside `### MOD: Demographics tab` blocks, none removed;
* the strip, its gates and the tab flag;
* that nothing the country's sections draw reads GetPlayer, in the markup or in
  any loc key they reach, and that none of that text says "our" or "your";
* that the controls which change a country (the pension and Family Policy
  buttons) show only for the player's own;
* that nothing the Census Data window draws reads the Population panel's own
  data (PopsOverviewPanel), which only that panel's window holds.
"""
import difflib
import glob
import json
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OVERRIDE = ROOT / "gui" / "pop_browser_panel.gui"
FIXTURE = ROOT / "test_fixtures" / "vanilla_gui" / "pop_browser_panel.gui"
WIDGETS = ROOT / "gui" / "te_demographics_widgets.gui"
LAYOUT = ROOT / "gui" / "te_demographics_layout.gui"
SGUIS = ROOT / "common" / "scripted_guis" / "te_demog_sguis.txt"
LOC_DIR = ROOT / "localization" / "english"
VANILLA_LOC = ROOT / "vanilla_parsed" / "localization_english.json"

MOD_OPEN = "### MOD: Demographics tab"
MOD_CLOSE = "### END MOD ###"
FLAG = "te_pop_browser_demog"
RULE = "GetScriptedGui('te_pops_demog_tab_sgui').IsShown( GuiScope.SetRoot( Country.MakeScope ).End )"
UNLOCK = "GetScriptedGui('te_pops_demog_tab_unlock_sgui').IsValid( GuiScope.SetRoot( Country.MakeScope ).End )"
SHOWN = f"And( GetVariableSystem.Exists('{FLAG}'), {RULE} )"

# The composers of the country's sections, one a host.
COMPOSERS = ("te_demog_tab_sections", "te_demog_browser_sections")
# The one GetPlayer read the country's markup keeps: the current year, the same for every country, in the history
# charts' sample_visible.
KEPT_GETPLAYER = "GetPlayer.MakeScope.ScriptValue('te_history_current_year')"
# Loc keys the country's sections reach that keep GetPlayer: shared with the state panel's How section, where no
# Country is in context, and read only a constant (te_demog_k_conscription_ref).
SHARED_WITH_THE_STATE = {"te_demog_fam_rule"}
PERSONAL = re.compile(r"\b(you|your|yours|we|our|ours|us)\b", re.I)
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


def type_bodies(text):
    """Each `type X = Y { ... }` in a types file, by name."""
    return {m.group(1): block_from(text, m.end() - 1)
            for m in re.finditer(r"(?m)^\ttype (\w+) = \w+ \{", text)}


def code(text):
    """The markup less its comments (no quoted value here holds a #)."""
    return "\n".join(line.split("#", 1)[0] if not re.search(r'"[^"]*#', line) else line
                     for line in text.splitlines() if not line.lstrip().startswith("#"))


def load_loc():
    keys = {}
    for path in sorted(glob.glob(str(LOC_DIR / "**" / "*.yml"), recursive=True)):
        for line in read(path).splitlines():
            m = re.match(r'^\s*([\w.\-]+):\d*\s+"(.*)"\s*$', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


def gui_keys(text, loc):
    out = set(re.findall(r'(?:text|tooltip|raw_text)\s*=\s*"([\w.\-]+)"', text))
    for expr in re.findall(r'"\[(.*?)\]"', text):
        out |= {k for k in re.findall(r"'([\w.\-]+)'", expr) if k in loc}
    return out & set(loc)


def loc_closure(keys, loc):
    seen, stack = set(), list(keys)
    while stack:
        key = stack.pop()
        if key in seen or key not in loc:
            continue
        seen.add(key)
        value = loc[key]
        stack.extend(re.findall(r"\$([\w.\-]+)\$", value))
        stack.extend(k for k in re.findall(r"'([\w.\-]+)'", value) if k in loc)
    return seen


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
        self.assertEqual(len(regions), 5, "the header, the strip, two vanilla rows' gates and the census")
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


class StripTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = code(read(OVERRIDE))
        cls.flat = re.sub(r"\s+", " ", cls.text)

    def test_the_strip_shows_while_the_rule_runs_and_holds_two_tabs(self):
        strip = block_from(self.text, self.text.index("tab_buttons = {"))
        self.assertEqual(self.text.count("tab_buttons = {"), 1)
        self.assertIn(f'visible = "[{RULE}]"', self.text[:self.text.index("tab_buttons = {")].rsplit("hbox = {", 1)[1])
        slots = set(re.findall(r'blockoverride "(\w+?)_button', strip))
        self.assertEqual(slots, {"first", "second"}, "the other slots stay hidden")
        self.assertIn('text = "te_pop_browser_tab_pops"', strip)
        self.assertIn('text = "te_pops_tab_demog"', strip)

    def test_the_demographics_tab_opens_with_the_countrys_first_census(self):
        strip = block_from(self.text, self.text.index("tab_buttons = {"))
        click = block_from(strip, strip.index('blockoverride "second_button_click"'))
        self.assertIn(f'enabled = "[{UNLOCK}]"', click)
        self.assertIn(f"GetVariableSystem.Set('{FLAG}', 'yes')", click)
        first = block_from(strip, strip.index('blockoverride "first_button_click"'))
        self.assertIn(f"GetVariableSystem.Clear('{FLAG}')", first)
        tooltip = block_from(strip, strip.index('blockoverride "second_button_tooltip"'))
        self.assertIn(f"SelectLocalization( {UNLOCK}, 'te_pop_browser_tab_demog_tt', "
                      f"'te_pop_browser_tab_demog_pending_tt' )", tooltip)

    def test_the_census_takes_the_place_of_vanillas_rows(self):
        # vanilla's header row and its filters, charts and table: each hidden exactly while the census shows
        self.assertEqual(self.text.count(f'visible = "[Not( {SHOWN} )]"'), 2)
        census = block_from(self.text, self.text.index('name = "te_pop_browser_demog_tab"') - 40)
        self.assertIn(f'visible = "[{SHOWN}]"', census)
        self.assertIn("te_demog_browser_sections = {}", census)
        self.assertEqual(self.text.count("te_demog_browser_sections = {}"), 1)

    def test_the_window_keeps_its_country(self):
        self.assertIn('datacontext = "[PopBrowserPanel.GetCountry]"', self.text)
        self.assertNotIn("GetPlayer", self.text, "the window's tabs read its own country")


class CountryContextTest(unittest.TestCase):
    """The country's sections read the Country in their context, so the Census Data window shows its own country's
    figures; GetPlayer there would show the player's."""

    @classmethod
    def setUpClass(cls):
        cls.loc = load_loc()
        widgets = type_bodies(read(WIDGETS))
        layout = type_bodies(read(LAYOUT))
        cls.country = {name: code(body) for name, body in widgets.items() if not name.startswith("te_state_")}
        cls.country.update({name: code(layout[name]) for name in COMPOSERS})
        cls.state = {name: code(body) for name, body in widgets.items() if name.startswith("te_state_")}
        cls.state["te_state_demog_content"] = code(layout["te_state_demog_content"])
        cls.keys = loc_closure(set().union(*(gui_keys(b, cls.loc) for b in cls.country.values())), cls.loc)

    def test_the_markup_reads_the_context_country(self):
        for name, body in self.country.items():
            with self.subTest(type=name):
                self.assertEqual(body.replace(KEPT_GETPLAYER, "").count("GetPlayer"), 0)
                self.assertNotIn("AccessPlayer", body)
        self.assertGreater(sum(b.count("Country.MakeScope") for b in self.country.values()), 300)

    def test_the_loc_reads_the_context_country(self):
        self.assertGreater(len(self.keys), 500)
        for key in sorted(self.keys - SHARED_WITH_THE_STATE):
            with self.subTest(key=key):
                self.assertNotIn("GetPlayer", self.loc[key])
                self.assertNotIn("AccessPlayer", self.loc[key])

    def test_the_kept_keys_read_only_constants(self):
        state_keys = loc_closure(set().union(*(gui_keys(b, self.loc) for b in self.state.values())), self.loc)
        for key in SHARED_WITH_THE_STATE:
            with self.subTest(key=key):
                self.assertIn(key, self.keys & state_keys)
                for read_ in re.findall(r"GetPlayer\.MakeScope\.(\w+\('[\w]+'\))", self.loc[key]):
                    self.assertRegex(read_, r"^ScriptValue\('te_demog_k_\w+'\)$")

    def test_the_state_never_reads_the_context_country(self):
        # the state panel has a State, not a Country, in context
        for name, body in self.state.items():
            with self.subTest(type=name):
                self.assertNotRegex(body, r"(?<![\w.])Country\.")

    def test_the_text_is_not_the_players(self):
        """The same sections show another country in the Census Data window, so none of their text says 'our'."""
        for key in sorted(self.keys):
            text = re.sub(r"\[[^\]]*\]|\$[\w.\-]+\$|#\w+|\\n", " ", self.loc[key])
            with self.subTest(key=key):
                self.assertIsNone(PERSONAL.search(text), text)

    def test_the_new_keys_exist(self):
        for key in ("te_pop_browser_tab_pops", "te_pop_browser_tab_pops_tt", "te_pop_browser_tab_demog_tt",
                    "te_pop_browser_tab_demog_pending_tt", "te_demog_hist_untracked", "te_demog_pyr_outline_next",
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
        self.assertIn('visible = "[Country.IsLocalPlayer]"', button)
        slot = row[:row.index("button = {")].rsplit("widget = {", 1)[1]
        self.assertIn("size = { 72 24 }", slot, "an empty slot of the button's size for another country")

    def test_the_pension_buttons_and_notes_are_the_players(self):
        work = self.widgets["te_demog_sec_work"]
        rows = [block_from(work, m.start()) for m in re.finditer(r"flowcontainer = \{", work)
                if "te_demog_pension_button = {" in block_from(work, m.start())
                and "te_demog_figure_row" not in block_from(work, m.start())]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIn('visible = "[Country.IsLocalPlayer]"', row)
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
        body = block_from(self.sguis, self.sguis.index("te_demog_hist_tracked_sgui = {"))
        self.assertIn("te_history_country_is_tracked = yes", body)
        history = type_bodies(read(WIDGETS))["te_demog_sec_history"]
        self.assertEqual(history.count("'te_demog_hist_empty', 'te_demog_hist_untracked'"), 8)


if __name__ == "__main__":
    unittest.main()
