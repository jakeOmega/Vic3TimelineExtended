"""Journal entry map modes, fifth pass (docs/systems/mod_systems/journal_map_modes.md).

The engine says nothing about a map's script: a named color it doesn't know, a tooltip key with no loc or a selector
number no branch reads all fail silently on the map. So this holds the pieces together offline:

- every color a map names is one of the mod's (common/named_colors/te_journal_map_colors.txt), and each is used;
- every Map Room pick (a scripted GUI) sets a selector that map_color and map_tooltip both branch on, has a
  button, and has its loc; the Map Room stays contextless, in no journal, with no scripted buttons (they lock);
- every map that needs a stored figure has a "no data" branch, and a year's figures wait for a state's first step;
- the leading-cause map's colors are the Causes of Death pie's;
- every map_tooltip key has loc;
- each pick reopens the Map Room's page a beat after its click, so a paused map repaints (check 4), from a
  widget outside the page (te_jmap_repainter), since a widget on it dies with the close (fifth session);
- the map buttons are mounted, Banking's shows while its entry is inactive (check 7), and every GUI reach into an
  entry names one that exists;
- every journal page has the see-through eye (gui/journal_entry.gui): a pick's reopen keeps it, closing clears it;
- the systems' maps (selectors 18-25): each system entry's map and the Map Room's branch for it ask the same triggers
  in the same order (the parity test), each pick waits for its system's rule, each system tab's button picks its map
  and opens the Map Room, and the "your" maps follow the viewer the picks note;
- the Timeline Extended window's Map Room button opens the page before it closes the window.
"""
import os
import re
import subprocess
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
HOST = "common/journal_entries/te_journal_maps.txt"
EFFECTS = "common/scripted_effects/te_journal_map_effects.txt"
SGUIS = "common/scripted_guis/te_journal_map_sguis.txt"
ROOM_WIDGET = "gui/journal_entry_widgets/te_map_room_widget.gui"
BANKING = "common/journal_entries/je_banking.txt"
# The systems' maps: (selector, entry file, entry key, Map Room pick, tab button, tab file, rule gate). The Seabed has
# no entry, so the Map Room alone draws it.
SYSTEM_MAPS = (
    (18, "common/journal_entries/je_global_warming.txt", "je_global_warming", "emissions", "gw",
     "gui/journal_entry_widgets/global_warming_widget.gui", "has_game_rule = global_warming_enabled"),
    (19, "common/journal_entries/je_nuclear_program.txt", "je_nuclear_program", "nuclear", "nuclear",
     "gui/journal_entry_widgets/nuclear_layout_widget.gui", "has_game_rule = nuclear_weapons_enabled"),
    (20, "common/journal_entries/je_covert_warfare.txt", "je_covert_warfare", "networks", "covert",
     "gui/journal_entry_widgets/covert_operations_widget.gui", "has_game_rule = covert_warfare_enabled"),
    (21, "common/journal_entries/je_united_nations.txt", "je_united_nations", "united_nations", "un",
     "gui/journal_entry_widgets/un_layout_widget.gui", "has_game_rule = united_nations_enabled"),
    (22, "common/journal_entries/je_cultural_hegemony.txt", "je_cultural_hegemony", "political_models", "ch",
     "gui/journal_entry_widgets/cultural_hegemony_widget.gui", "has_game_rule = cultural_hegemony_enabled"),
    (23, None, None, "ocean_basins", "seabed", "gui/te_seabed_widgets.gui", "te_global_commons_enabled = yes"),
    (24, "common/journal_entries/je_grand_monuments.txt", "je_grand_monuments", "grandeur", "gm",
     "gui/journal_entry_widgets/grand_monuments_widget.gui", "gm_system_enabled = yes"),
    (25, "common/journal_entries/je_colonial_empire.txt", "je_colonial_empire", "colonies", "ce",
     "gui/journal_entry_widgets/colonial_empire_widget.gui", "has_game_rule = decolonization_enabled"),
)
SYSTEM_ENTRIES = tuple((rel, key) for _sel, rel, key, *_ in SYSTEM_MAPS if rel)
MAP_ENTRIES = (HOST, BANKING) + tuple(rel for rel, _key in SYSTEM_ENTRIES)
TRIGGERS = "common/scripted_triggers/te_journal_map_triggers.txt"
ON_ACTIONS = "common/on_actions/te_journal_map_on_actions.txt"
SYSTEMS_WINDOW = "gui/te_systems_window.gui"
COLORS = "common/named_colors/te_journal_map_colors.txt"
VALUES = "common/script_values/te_journal_map_values.txt"
SCALES = "common/script_values/te_journal_map_scales_generated.txt"
WIDGETS = "gui/te_map_widgets.gui"
REPAINTER = "te_jmap_repainter"
REGISTRATION = "gui/scripted_widgets/te_systems_window.txt"
DEMOG_LAYOUT = "gui/te_demographics_layout.gui"
BANKING_LAYOUT = "gui/journal_entry_widgets/banking_layout_widget.gui"
JE_PANEL = "gui/journal_entry.gui"
MAP_MODE = "gfx/map/map_modes/te_map_modes.txt"
LOC_DIR = "localization/english"
PLAYTEST = "docs/testing/journal-map-modes-playtest.md"
BOM = b"\xef\xbb\xbf"


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


def code(rel):
    """The file with comments removed (a `#` inside a quoted string is kept)."""
    out = []
    for line in read(rel).splitlines():
        kept, quoted = [], False
        for ch in line:
            if ch == '"':
                quoted = not quoted
            if ch == "#" and not quoted:
                break
            kept.append(ch)
        out.append("".join(kept))
    return "\n".join(out)


def block(text, key):
    """The body of the first `key = { ... }` in text (or `type key = base { ... }`), braces balanced."""
    m = re.search(r"\b" + re.escape(key) + r"\s*=\s*(?:\w+\s*)?\{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def override(text, name):
    """The body of `blockoverride "name" { ... }` in text."""
    m = re.search(r'\bblockoverride\s+"' + re.escape(name) + r'"\s*\{', text)
    if not m:
        return None
    start, end = enclosing_span(text, m.end())
    return text[start:end]


def enclosing(text, pos):
    """The body of the innermost `{ ... }` around pos."""
    start, end = enclosing_span(text, pos)
    return text[start:end]


def enclosing_span(text, pos):
    """(start, end) of the body of the innermost `{ ... }` around pos."""
    depth, i = 0, pos
    while i > 0:
        i -= 1
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                break
            depth -= 1
    j, depth = i + 1, 1
    while depth:
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        j += 1
    return i + 1, j - 1


def top_level_widget(text, name):
    """The body of the top-level widget named `name` (a scripted widget's root)."""
    m = re.search(r'^\tname\s*=\s*"' + re.escape(name) + r'"', text, re.M)
    if not m:
        raise AssertionError(f"no top-level widget {name}")
    start, end = enclosing_span(text, m.start())
    assert re.search(r"^widget\s*=\s*\{\s*$", text[:start], re.M), name
    return text[start:end]


def entry(rel, name):
    return block(code(rel), name)


def loc_keys():
    keys = set()
    for name in os.listdir(os.path.join(REPO, LOC_DIR)):
        if name.endswith(".yml"):
            for line in read(os.path.join(LOC_DIR, name)).splitlines():
                m = re.match(r"\s+([A-Za-z0-9_.\-]+):\d*\s", line)
                if m:
                    keys.add(m.group(1))
    return keys


def named_colors():
    return set(re.findall(r"^\s*([a-z0-9_]+)\s*=\s*(?:hsv360|hsv|rgb)\s*\{", code(COLORS), re.M))


def tracked(rel):
    """Whether git tracks rel. CI checks out without gfx/ (sparse), so a file can be absent on disk yet committed."""
    return subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO,
                          capture_output=True).returncode == 0


class FilesTest(unittest.TestCase):
    def test_each_new_file_has_one_bom(self):
        for rel in (HOST, COLORS, VALUES, SCALES, WIDGETS, ROOM_WIDGET, EFFECTS, SGUIS, TRIGGERS, ON_ACTIONS):
            with open(os.path.join(REPO, rel), "rb") as f:
                head = f.read(6)
            self.assertTrue(head.startswith(BOM) and not head[3:].startswith(BOM), rel)


class ColorsTest(unittest.TestCase):
    def test_every_map_color_is_defined(self):
        known = named_colors()
        for rel, name in ((HOST, "je_te_map_room"), (BANKING, "je_banking_cycle")) + SYSTEM_ENTRIES:
            body = entry(rel, name)
            for key in ("map_color", "map_color_second"):
                part = block(body, key)
                if part is None:
                    continue
                used = set(re.findall(r'\b(?:value|min_color|max_color)\s*=\s*"([a-z0-9_]+)"', part))
                self.assertTrue(used, f"{name}.{key} names no color")
                self.assertEqual(used - known, set(), f"{name}.{key}: colors not in {COLORS}")

    def test_every_defined_color_is_used(self):
        defined = set(re.findall(r"^\s*([a-z0-9_]+)\s*=\s*hsv360", code(COLORS), re.M))
        used = set()
        for rel in MAP_ENTRIES:
            used |= set(re.findall(r'"(te_jmap_[a-z0-9_]+)"', code(rel)))
        self.assertEqual(defined - used, set(), "named colors no map uses")


class CauseColorsTest(unittest.TestCase):
    PIE = "scripts/image_pipeline/gen_ch_model_pie_textures.py"

    def test_leading_cause_colors_are_the_pies(self):
        # the leading-cause map draws in the Causes of Death pie's colors, so the pie's legend reads the map too
        import colorsys
        pie = dict(re.findall(r'"icons/demographics_icons/pie_(\w+)\.dds",\s*"(#[0-9a-f]{6})"', read(self.PIE)))
        names = {"inf": "infection", "chr": "chronic", "ext": "external", "work": "work", "mat": "maternal",
                 "kill": "killed", "war": "war"}
        text = code(COLORS)
        for short, long in names.items():
            h = pie[long]
            hsv = colorsys.rgb_to_hsv(*(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)))
            m = re.search(r"\bte_jmap_cause_" + short + r"\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}", text)
            self.assertIsNotNone(m, short)
            want = (round(hsv[0] * 360), round(hsv[1] * 100), round(hsv[2] * 100))
            self.assertEqual(tuple(int(x) for x in m.groups()), want, f"te_jmap_cause_{short} vs the pie's {h}")

    def test_each_cause_fades_by_its_share(self):
        # each cause's branch fades from a pale end of its own hue to the pie's color by the leading share, so a
        # state where a cause barely leads reads apart from one where it takes nearly every death
        text, host = code(COLORS), code(HOST)
        for short in ("inf", "chr", "ext", "work", "mat", "kill", "war"):
            full = re.search(r"\bte_jmap_cause_" + short + r"\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", text)
            pale = re.search(r"\bte_jmap_cause_" + short + r"_pale\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", text)
            self.assertIsNotNone(pale, short)
            self.assertEqual(pale.group(1), full.group(1), f"te_jmap_cause_{short}_pale keeps the cause's hue")
            self.assertLess(int(pale.group(2)), int(full.group(2)), f"te_jmap_cause_{short}_pale is paler")
            self.assertRegex(host, r'lerp = \{\s*min_color = "te_jmap_cause_' + short + r'_pale"\s*max_color = '
                             r'"te_jmap_cause_' + short + r'"\s*factor = te_jmap_cause_factor\s*\}', short)
        self.assertNotRegex(host, r'value = "te_jmap_cause_', "a cause drawn flat, not by its share")


class MapRoomTest(unittest.TestCase):
    def setUp(self):
        self.room = entry(HOST, "je_te_map_room")
        self.sguis = code(SGUIS)

    def picks(self):
        """{scripted GUI: selector} for every Map Room pick."""
        out = {}
        for name in re.findall(r"^(te_jmap_pick_\w+_sgui)\s*=\s*\{", self.sguis, re.M):
            m = re.search(r"te_jmap_set_selector\s*=\s*\{\s*SEL\s*=\s*(\d+)\s*\}", block(self.sguis, name))
            self.assertIsNotNone(m, f"{name} sets no selector")
            out[name] = int(m.group(1))
        return out

    def test_every_pick_has_a_map_and_a_tooltip(self):
        picks = self.picks()
        # 2 was literacy, retired (vanilla's literacy map mode shows it): a save holding it shows "Pick a map"
        self.assertEqual(sorted(picks.values()), [1] + list(range(3, 31)), "one pick per selector, 2 unused")
        # the "no data" branch names the figure maps in an OR; a pick needs a branch of its own
        color = re.sub(r"\bOR\s*=\s*\{[^{}]*\}", "", block(self.room, "map_color"))
        tooltip = re.sub(r"\bOR\s*=\s*\{[^{}]*\}", "", block(self.room, "map_tooltip"))
        for name, sel in picks.items():
            branch = re.compile(r"te_jmap_selector\s*=\s*" + str(sel) + r"\b")
            self.assertRegex(color, branch, f"{name}: map_color has no branch for selector {sel}")
            self.assertRegex(tooltip, branch, f"{name}: map_tooltip has no branch for selector {sel}")

    def branches(self, key, sel):
        """The bodies of key's branches (if / else_if) that name selector sel outside an OR."""
        part = block(self.room, key)
        out = []
        for m in re.finditer(r"\b(?:if|else_if)\s*=\s*\{", part):
            body = enclosing(part, m.end())
            limit = re.sub(r"\bOR\s*=\s*\{[^{}]*\}", "", block(body, "limit") or "")
            if re.search(r"te_jmap_selector\s*=\s*" + str(sel) + r"\b", limit):
                out.append(body)
        return out

    def no_data(self, key):
        """The selectors key's OR-only branches list: the maps that show grey for a state with no figure. map_color has
        one; map_tooltip one for the census and walk figures and one for the tourism and climate refreshes' figures,
        whose wait is a month, not a census year."""
        part = block(self.room, key)
        ors = re.findall(r"\bOR\s*=\s*\{([^{}]*te_jmap_selector[^{}]*)\}", part)
        self.assertTrue(ors, f"{key}: no 'no data' branch")
        found = [int(n) for body in ors for n in re.findall(r"te_jmap_selector\s*=\s*(\d+)", body)]
        self.assertEqual(len(found), len(set(found)), f"{key}: a selector in two 'no data' branches")
        return set(found)

    def test_every_figure_map_has_a_no_data_branch(self):
        # a map whose branches all need a stored figure (has_variable) leaves a state with none unpainted (dark grey)
        # and with the "Pick a map" tooltip, unless the OR lists it
        gated = set()
        for sel in self.picks().values():
            bodies = self.branches("map_color", sel)
            self.assertTrue(bodies, sel)
            if all("has_variable" in b for b in bodies):
                gated.add(sel)
        self.assertIn(3, gated)
        self.assertTrue({26, 27, 28} <= gated, "tourism and the two climate maps read stored figures")
        self.assertEqual(self.no_data("map_color"), gated, "map_color's 'no data' OR")
        self.assertEqual(self.no_data("map_tooltip"), gated, "map_tooltip's 'no data' OR")

    def test_a_years_figures_wait_for_a_step(self):
        # a seed writes births, deaths and migration as 0, and no causes of death (te_demog_state_stepped_sgui): those
        # maps show grey until the state's first full year
        for sel in (7, 8, 9, 11, 13):
            for key in ("map_color", "map_tooltip"):
                for body in self.branches(key, sel):
                    self.assertRegex(body, r"var:te_dg_stepped\s*>\s*0", f"{key}, selector {sel}")

    def test_the_stored_figures_are_written(self):
        # tourism's Base Appeal and Local Climate's penalties are state_region chains too dear to evaluate per state as
        # the map paints, so each refresh stores the figure the map reads (and the map's guard names it)
        writes = {
            "te_tourism_base_appeal": ("common/scripted_effects/extra_effects.txt", "te_update_tourism_modifier",
                                       "tourism_bonus_from_base_appeal"),
            "te_climate_base_penalty": ("common/scripted_effects/local_climate_effects.txt",
                                        "te_update_local_climate_modifier", "te_climate_penalty_raw"),
            "te_climate_penalty_applied": ("common/scripted_effects/local_climate_effects.txt",
                                           "te_update_local_climate_modifier", "te_climate_penalty"),
        }
        for var, (rel, effect, value) in writes.items():
            body = block(code(rel), effect)
            self.assertRegex(body, r"set_variable\s*=\s*\{\s*name\s*=\s*" + var + r"\s+value\s*=\s*" + value + r"\s*\}",
                             f"{effect} doesn't store {var}")
            self.assertIn(f"has_variable = {var}", self.room, f"no map reads {var}")

    def test_the_current_pick_is_invalid_so_its_button_draws_pressed(self):
        for name, sel in self.picks().items():
            valid = block(block(self.sguis, name), "is_valid")
            self.assertRegex(valid, r"NOT\s*=\s*\{\s*te_jmap_selector\s*=\s*" + str(sel) + r"\s*\}", name)

    def test_every_pick_has_a_button(self):
        row = block(code(WIDGETS), "te_jmap_pick_row")
        self.assertIsNotNone(row)
        seen = []
        for m in re.finditer(r"\bte_jmap_pick_button\s*=\s*\{", row):
            button = enclosing(row, m.end())
            sguis = set(re.findall(r"GetScriptedGui\('(\w+)'\)", button))
            self.assertEqual(len(sguis), 1, f"one scripted GUI per button: {sguis}")
            name = sguis.pop()
            for call in ("IsShown", "IsValid", "Execute"):
                self.assertIn(f"GetScriptedGui('{name}').{call}(", button, f"{name}: no {call} on its button")
            key = name[:-len("_sgui")]
            self.assertIn(f'text = "{key}"', button, f"{name}: its button shows another pick's name")
            self.assertIn(f'tooltip = "{key}_desc"', button, f"{name}: its button shows another pick's tooltip")
            clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', button)
            self.assertEqual(len(clicks), 2, f"{name}: pick, then the repaint")
            self.assertIn(".Execute(", clicks[0], f"{name}: the pick runs first")
            # PdxGuiTriggerAllAnimations, not PdxGuiWidget.TriggerAnimation: the repaint's states sit on a widget
            # outside the page, which outlives the close (fifth session)
            self.assertEqual(clicks[1], "[PdxGuiTriggerAllAnimations('te_jmap_repaint')]", name)
            seen.append(name)
        self.assertEqual(sorted(seen), sorted(self.picks()), "one button per pick")

    def test_a_pick_reopens_the_page_to_repaint(self):
        # check 4 (2026-11-05): paused, reopening the page repainted the map. Fifth session: a state on the pick button
        # itself closed the page and never reopened it (ClosePanel then the DontToggle open, one on_finish after the
        # other). So the states sit on a scripted widget outside the page, which outlives the close, and the close and
        # the open are two states, so the open runs frames after the close has landed.
        host = top_level_widget(code(WIDGETS), REPAINTER)
        self.assertIn('datacontext = "[GetPlayerJournalEntry(\'je_te_map_room\')]"', host,
                      "the host names the entry itself: the pick button's datacontext goes with the page")
        states = {}
        for m in re.finditer(r"\bstate\s*=\s*\{", host):
            body = enclosing(host, m.end())
            states[re.search(r"name\s*=\s*(\w+)", body).group(1)] = body
        self.assertEqual(sorted(states), ["te_jmap_repaint", "te_jmap_repaint_open"])
        close, reopen = states["te_jmap_repaint"], states["te_jmap_repaint_open"]
        self.assertRegex(close, r"\bnext\s*=\s*te_jmap_repaint_open\b")
        for body in (close, reopen):
            self.assertRegex(body, r"duration\s*=\s*0?\.\d*[1-9]", "each state waits a beat")
        self.assertEqual(re.findall(r'on_finish\s*=\s*"([^"]*)"', close), ["[InformationPanelBar.ClosePanel]"])
        finish = re.findall(r'on_finish\s*=\s*"([^"]*)"', reopen)
        # the plain open, proven in game from a widget outside the page (the Demographics and Banking buttons); the
        # page is closed by now, so its toggle opens it. DontToggle has never been seen to work.
        self.assertEqual(finish[-1], "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]")
        self.assertIn("te_jmap_reopen_log_sgui", finish[0], "the reopen logs before it opens")
        # the pick button keeps no repaint state of its own: TriggerAllAnimations would fire it too
        self.assertNotRegex(block(code(WIDGETS), "te_jmap_pick_button"), r"\bstate\s*=")

    def test_the_repainter_is_registered(self):
        self.assertIn(f"{WIDGETS} = {REPAINTER}", code(REGISTRATION))

    def test_the_room_is_contextless_and_in_no_journal(self):
        # check 7 (2026-11-05): a contextless entry nobody is involved in is active from the start, in no journal, and
        # a button opens its page at the first click
        self.assertRegex(self.room, r"\bcontext\s*=\s*none\b")
        self.assertRegex(block(self.room, "should_be_involved"), r"always\s*=\s*no")
        self.assertRegex(block(self.room, "should_show_when_not_involved"), r"always\s*=\s*no")
        self.assertNotRegex(self.room, r"\bpossible\s*=", "possible defaults to yes: the room is active from the start")
        self.assertNotRegex(self.room, r"\boutcome\s*=", "the Map Room never concludes")

    def test_the_room_has_no_scripted_buttons(self):
        # check 14 (2026-11-05): the engine locks a contextless entry's scripted buttons for a country not involved
        self.assertNotRegex(self.room, r"\bscripted_button\s*=")

    def test_the_widget_is_mounted_and_defined(self):
        mount = block(self.room, "widget")
        self.assertIsNotNone(mount)
        self.assertIn(f'gui = "{ROOM_WIDGET}"', mount)
        name = re.search(r'name\s*=\s*"(\w+)"', mount).group(1)
        self.assertRegex(code(ROOM_WIDGET), r'name\s*=\s*"' + name + '"')
        self.assertIn("te_jmap_pick_row = {}", code(ROOM_WIDGET))

    def test_no_ai_use(self):
        for name in re.findall(r"^(te_jmap_\w+_sgui)\s*=\s*\{", self.sguis, re.M):
            self.assertRegex(block(self.sguis, name), r"ai_is_valid\s*=\s*\{\s*always\s*=\s*no\s*\}", name)


def branches_of(part):
    """[(limit, body)] for the top-level if / else_if / else of a map_color or map_tooltip block, whitespace collapsed;
    an else's limit is ""."""
    out = []
    for m in re.finditer(r"\b(if|else_if|else)\s*=\s*\{", part):
        start, end = enclosing_span(part, m.end())
        if part[:m.start()].count("{") - part[:m.start()].count("}") != 0:
            continue    # nested
        body = part[start:end]
        limit = block(body, "limit") if m.group(1) != "else" else ""
        rest = body
        if limit is not None and m.group(1) != "else":
            lm = re.search(r"\blimit\s*=\s*\{", body)
            ls, le = enclosing_span(body, lm.end())
            rest = body[:lm.start()] + body[le + 1:]
        out.append((" ".join((limit or "").split()), " ".join(rest.split())))
    return out


class SystemMapsTest(unittest.TestCase):
    """The systems' maps: each on its own entry and in the Map Room (selectors 18-25)."""

    def setUp(self):
        self.room = entry(HOST, "je_te_map_room")
        self.sguis = code(SGUIS)
        self.widgets = code(WIDGETS)

    def room_branches(self, key, sel):
        """The Map Room's branches for selector sel, the selector taken out of each limit."""
        out = []
        for limit, body in branches_of(block(self.room, key)):
            if re.search(r"(^| )te_jmap_selector = " + str(sel) + r"( |$)", limit) and "OR = {" not in limit:
                out.append((" ".join(re.sub(r"\bte_jmap_selector = " + str(sel) + r"\b", "", limit).split()), body))
        return out

    def test_each_entry_draws_the_map_room_s_map(self):
        # one map, two hosts: the entry's ladder and the Map Room's branches for its selector, in the same order, from
        # the same triggers and colors (te_journal_map_triggers.txt). A drift paints the two pages differently, silently.
        for sel, rel, key, *_ in SYSTEM_MAPS:
            for part in ("map_color", "map_tooltip"):
                with self.subTest(selector=sel, block=part):
                    room = self.room_branches(part, sel)
                    self.assertTrue(room, "no Map Room branch")
                    self.assertEqual(room[-1][0], "", "the map's last branch takes every state left")
                    if rel is None:
                        continue
                    mine = branches_of(block(entry(rel, key), part))
                    self.assertEqual(mine, room)

    def test_the_systems_maps_read_only_shared_triggers(self):
        # every limit of a system map is the shared triggers (yes, or a parameter block), so the entry and the Map Room
        # can't each grow their own reading
        names = set(re.findall(r"^(te_jmap_\w+)\s*=\s*\{", code(TRIGGERS), re.M))
        for sel, *_ in SYSTEM_MAPS:
            for part in ("map_color", "map_tooltip"):
                for limit, _body in self.room_branches(part, sel):
                    for call in re.findall(r"(\w+) = (?:yes|\{)", limit):
                        self.assertIn(call, names, f"selector {sel}, {part}: {call} is not a shared map trigger")

    def test_each_pick_waits_for_its_system(self):
        for sel, _rel, _key, pick, *_rest, gate in SYSTEM_MAPS:
            body = block(self.sguis, f"te_jmap_pick_{pick}_sgui")
            self.assertIsNotNone(body, pick)
            self.assertIn(gate, block(body, "is_shown"), pick)
            self.assertRegex(body, r"te_jmap_set_selector\s*=\s*\{\s*SEL\s*=\s*" + str(sel) + r"\s*\}")

    def test_each_system_tab_has_a_one_click_map_button(self):
        # the Map Room, not the system's own entry: several entries are held by only some countries, or not yet, and a
        # button on an entry nobody holds has nothing to open
        for _sel, _rel, _key, pick, button, tab, _gate in SYSTEM_MAPS:
            with self.subTest(button=button):
                name = f"te_jmap_{button}_map_button"
                self.assertIn(f"{name} = {{}}", code(tab), f"{name} isn't mounted in {tab}")
                body = block(self.widgets, name)
                self.assertIn("GetPlayerJournalEntry('je_te_map_room')", body)
                clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', body)
                self.assertEqual(len(clicks), 4, "unfade, note the viewer, pick, then open")
                self.assertEqual(clicks[0], "[GetVariableSystem.Clear('te_je_see_through')]")
                # the viewer first: a pick already made is invalid, and its effect (which notes it too) doesn't run
                self.assertIn("te_jmap_note_viewer_sgui", clicks[1])
                self.assertIn(f"te_jmap_pick_{pick}_sgui", clicks[2])
                self.assertEqual(clicks[3], "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]")

    def test_the_your_maps_follow_the_viewer(self):
        # a paint can't reach the player (is_player drew nothing, 2026-11-05): every pick and map button notes the
        # player's country as the viewer, and each month a player's pulse does too
        effects = code(EFFECTS)
        self.assertIn("te_jmap_note_viewer = yes", block(effects, "te_jmap_set_selector"))
        self.assertRegex(block(effects, "te_jmap_note_viewer"),
                         r"set_global_variable\s*=\s*\{\s*name\s*=\s*te_jmap_viewer\s*value\s*=\s*root\s*\}")
        self.assertIn("te_jmap_monthly_viewer", block(code(ON_ACTIONS), "on_monthly_pulse_country"))
        self.assertRegex(block(code(ON_ACTIONS), "te_jmap_monthly_viewer"), r"is_player\s*=\s*yes")
        self.assertIn("te_jmap_note_viewer_sgui", block(self.widgets, "te_jmap_window_button"))

    def test_the_nuclear_map_shows_the_world_s_view_of_others(self):
        # nuclear.md's privacy rule: another country's true count never shows. The owner is read only through
        # nd_believed_armed and the public estimate; nd_is_armed is the viewer's own
        # nd_is_armed is read on nobody, the viewer included: in multiplayer another player sees the viewer's map
        trig = code(TRIGGERS)
        secret = ("nuclear_weapon_stockpile", "nd_is_armed", "nd_display_public_estimate", "nd_believed_stockpile",
                  "nd_stockpile")
        names = [n for n in re.findall(r"^(te_jmap_\w+)\s*=\s*\{", trig, re.M) if n.startswith(("te_jmap_nuke_",
                                                                                                "te_jmap_owner_"))]
        self.assertIn("te_jmap_nuke_guaranteed", names)
        for name in names:
            for word in secret:
                self.assertNotRegex(block(trig, name), r"\b" + word + r"\b", f"{name} reads {word}")
        for key, text in loc_values().items():
            if key.startswith("te_jmap_tt_nuke_"):
                for word in secret:
                    self.assertNotRegex(text, r"\b" + word + r"\b", key)
                if "ScriptValue(" in text:
                    self.assertIn("ScriptValue('nd_shown_public_estimate')", text, key)

    def test_the_political_models_are_the_pie_s_colors(self):
        import colorsys
        pie = dict(re.findall(r'\("(\w+)", "(#[0-9a-f]{6})"\)', read(CauseColorsTest.PIE)))
        text = code(COLORS)
        models = re.findall(r"te_jmap_ch_model = \{ MODEL = (\d+) \}\s*\}\s*value = \"te_jmap_ch_(\w+)\"",
                            code(HOST))
        self.assertEqual([int(n) for n, _ in models], list(range(1, 16)), "one branch per model code")
        for _n, model in models:
            h = pie[model]
            hsv = colorsys.rgb_to_hsv(*(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)))
            m = re.search(r"\bte_jmap_ch_" + model + r"\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}", text)
            self.assertIsNotNone(m, model)
            want = (round(hsv[0] * 360), round(hsv[1] * 100), round(hsv[2] * 100))
            self.assertEqual(tuple(int(x) for x in m.groups()), want, f"te_jmap_ch_{model} vs the pie's {h}")

    def test_the_model_codes_are_the_census_s(self):
        # ch_set_political_model's codes, in order (cultural_hegemony_effects.txt's code table)
        table = read("common/scripted_effects/cultural_hegemony_effects.txt")
        for n, model in re.findall(r"te_jmap_ch_model = \{ MODEL = (\d+) \}\s*\}\s*value = \"te_jmap_ch_(\w+)\"",
                                   code(HOST)):
            self.assertRegex(table, r"\b" + n + r"\s*=?\s*" + model + r"\b", f"code {n} is not {model}")


class ScriptChangesTest(unittest.TestCase):
    """The maps' figures the systems keep for them, since a paint can't walk pops."""

    def test_emissions_are_kept_per_state_in_the_one_yearly_walk(self):
        body = block(code("common/scripted_effects/global_warming_effects.txt"), "gw_snapshot_country_emissions_effect")
        state = body.index("name = gw_state_emis")
        country = body.index("name = gw_disp_country_emis")
        self.assertLess(state, country, "each state's figure first, then the country's as their sum")
        self.assertIn("value = gw_country_emis_from_states", body)
        self.assertNotIn("country_greenhouse_gas_emissions_script_value", body, "a second walk of the pops")

    def test_colonies_are_marked_in_the_pass_that_counts_them(self):
        body = block(code("common/scripted_effects/colonial_empire_display_effects.txt"),
                     "colonial_empire_refresh_display")
        mark = body.index("name = te_jmap_ce_colony")
        self.assertLess(mark, body.index("name = colonial_empire_colony_count"))
        self.assertIn("value = te_jmap_ce_colony_count", body)
        self.assertEqual(body.count("is_overseas_colonial_state"), 1, "one colony test per state")

    def test_the_basins_are_set_from_the_first_month_and_each_january(self):
        # each January too: a coastal state made after the first month (a colony) would otherwise wait for a claimant
        effects = code("common/scripted_effects/te_global_commons_seabed_effects.txt")
        at = effects.index("set_global_variable = te_seabed_basins_set")
        limit = enclosing(effects, effects.rindex("limit = {", 0, at) + len("limit = {"))
        self.assertNotIn("abyssal_plain_mining", limit)
        self.assertIn("NOT = { has_global_variable = te_seabed_basins_set }", limit)
        self.assertRegex(limit, r"\bmonth = 0\b")
        self.assertIn("te_seabed_ensure_state_basin = yes", enclosing(effects, at))

    def test_the_emissions_map_reads_nothing_beside_its_guard(self):
        # a multi-child NOT reads every child (scripting_best_practices.md), so a figure an OR guards is read anyway
        trig = code(TRIGGERS)
        for name in ("te_jmap_gw_no_data", "te_jmap_gw_removal"):
            self.assertNotRegex(block(trig, name), r"\b(?:var|global_var):", name)


class WindowButtonTest(unittest.TestCase):
    def test_the_map_room_button_sits_by_the_width_toggle(self):
        text = code(SYSTEMS_WINDOW)
        toggle = enclosing(text, re.search(r"type te_systems_window_toggle = hbox \{", text).end())
        self.assertIn("te_jmap_window_button = {}", toggle)

    def test_it_opens_the_page_then_closes_the_window(self):
        # the close comes last: a button whose own window hides mid-click may lose the lines after it
        body = block(code(WIDGETS), "te_jmap_window_button")
        self.assertIn("GetPlayerJournalEntry('je_te_map_room')", body)
        clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', body)
        self.assertEqual(clicks[0], "[GetVariableSystem.Clear('te_je_see_through')]")
        self.assertIn("te_jmap_note_viewer_sgui", clicks[1])
        self.assertEqual(clicks[2], "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]")
        self.assertEqual(clicks[3], "[GetVariableSystem.Clear('com_open_window')]")


def loc_values():
    out = {}
    for name in os.listdir(os.path.join(REPO, LOC_DIR)):
        if name.endswith(".yml"):
            for line in read(os.path.join(LOC_DIR, name)).splitlines():
                m = re.match(r'\s+([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    out[m.group(1)] = m.group(2)
    return out


class LocTest(unittest.TestCase):
    def test_tooltips_buttons_and_names_have_loc(self):
        keys = loc_keys()
        wanted = set()
        for rel in MAP_ENTRIES:
            wanted |= set(re.findall(r"custom_tooltip_no_bullet\s*=\s*(\w+)", code(rel)))
        for rel in (WIDGETS, ROOM_WIDGET, JE_PANEL):
            wanted |= set(re.findall(r'(?:text|tooltip)\s*=\s*"(te_j(?:map|e)_\w+)"', code(rel)))
        self.assertIn("te_je_see_through_tt", wanted)
        wanted |= {"je_te_map_room", "je_te_map_room_reason"}
        self.assertEqual(wanted - keys, set(), "loc keys missing")

    def test_retired_test_pieces_left_no_loc(self):
        keys = loc_keys()
        gone = {k for k in keys if k.startswith(("te_jmap_strip_", "te_jmap_tt_probe_", "je_te_map_potential_probe"))}
        gone |= keys & {"te_jmap_pick_scope_probe", "te_jmap_pick_scope_probe_desc", "te_jmap_tt_potential_probe",
                        "mm_te_journal_entry_map",
                        # literacy, retired: vanilla's literacy map mode shows it
                        "te_jmap_pick_literacy", "te_jmap_pick_literacy_desc", "te_jmap_tt_literacy"}
        self.assertEqual(gone, set())

    def test_literacy_is_gone(self):
        self.assertNotIn("te_jmap_pick_literacy_sgui", code(SGUIS))
        self.assertNotIn("literacy", code(VALUES))
        self.assertNotIn("literacy", code(COLORS))


class GuiTest(unittest.TestCase):
    def test_buttons_are_mounted(self):
        self.assertIn("te_jmap_demog_map_button = {}", code(DEMOG_LAYOUT))
        self.assertIn("te_jmap_banking_map_button = {}", code(BANKING_LAYOUT))
        self.assertIn("te_jmap_window_button = {}", code(SYSTEMS_WINDOW))

    def test_banking_button_has_no_activity_gate(self):
        # the entry is active from the engine's first check (possible = yes), and an inactive page would open and
        # paint too (check 7, 2026-11-05), so the button needs no IsActive gate
        self.assertNotIn("IsActive", block(code(WIDGETS), "te_jmap_banking_map_button"))
        self.assertRegex(block(code(BANKING), "je_banking_cycle"), r"\bpossible\s*=\s*\{\s*always\s*=\s*yes\s*\}")

    def test_map_buttons_open_pages_whole(self):
        names = ["te_jmap_demog_map_button", "te_jmap_banking_map_button", "te_jmap_window_button"]
        names += [f"te_jmap_{button}_map_button" for *_head, button, _tab, _gate in SYSTEM_MAPS]
        for name in names:
            clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', block(code(WIDGETS), name))
            self.assertEqual(clicks[0], "[GetVariableSystem.Clear('te_je_see_through')]", name)

    def test_every_entry_the_gui_opens_exists(self):
        entries = set(re.findall(r"^([a-z_0-9]+)\s*=\s*\{", code(HOST), re.M)) | {"je_banking_cycle"}
        for name in re.findall(r"GetPlayerJournalEntry\('(\w+)'\)", code(WIDGETS)):
            self.assertIn(name, entries)

    def test_every_open_names_its_entry_by_datacontext(self):
        # GetPlayerJournalEntry fails at load inside a callback, bare (first launch) and ended with .AccessSelf
        # ("requires non const promote", third session): the button carries the entry as its datacontext
        text = code(WIDGETS)
        self.assertNotRegex(text, r'onclick\s*=\s*"[^"]*GetPlayerJournalEntry')
        for m in re.finditer(r"OpenJournalEntryPanel(?:DontToggle)?\(([^)]*)\)", text):
            self.assertEqual(m.group(1), "JournalEntry.AccessSelf")
            start, end = enclosing_span(text, m.start())
            if re.search(r"\bstate\s*=\s*\{\s*$", text[:start]):
                # an animation state's callback: the entry sits on the widget the state belongs to
                start, end = enclosing_span(text, start - 1)
            self.assertIn('datacontext = "[GetPlayerJournalEntry(', text[start:end],
                          "an open with no entry datacontext on its own widget")

    def test_demographics_button_is_one_click(self):
        button = block(code(WIDGETS), "te_jmap_demog_map_button")
        clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', button)
        self.assertEqual(len(clicks), 3, "unfade, pick, then open")
        self.assertIn("te_jmap_pick_life_expectancy_sgui", clicks[1])
        self.assertIn("OpenJournalEntryPanel", clicks[2])
        self.assertIn("GetPlayerJournalEntry('je_te_map_room')", button)


class SeeThroughTest(unittest.TestCase):
    """The eye on every journal page fades it so its map shows (owner's ask, 2026-11-05)."""

    def setUp(self):
        self.panel = block(code(JE_PANEL), "journal_entry_panel")

    def test_the_page_fades_on_the_flag(self):
        alpha = re.findall(r'^\t\talpha\s*=\s*"([^"]*)"', self.panel, re.M)
        self.assertEqual(len(alpha), 1, "one alpha on the panel's root")
        self.assertIn("GetVariableSystem.Exists('te_je_see_through')", alpha[0])

    def test_the_eye_toggles_the_flag(self):
        props = override(self.panel, "top_left_button_properties")
        self.assertIsNotNone(props)
        self.assertIn("[GetVariableSystem.Toggle('te_je_see_through')]", props)
        self.assertIn("JournalEntryPanel.HasJournalEntry", override(self.panel, "top_left_button_visibility"))

    def test_closing_clears_it_but_a_reopen_keeps_it(self):
        # a Map Room pick reopens the page (te_jmap_repaint), which fires _show: clearing there would unfade the page
        # at every pick
        self.assertNotIn("te_je_see_through", override(self.panel, "animation_state_block"))
        close = re.findall(r'onclick\s*=\s*"([^"]*)"', override(self.panel, "header_close_button"))
        self.assertEqual(close, ["[InformationPanelBar.ClosePanel]", "[GetVariableSystem.Clear('te_je_see_through')]"])
        back = override(self.panel, "header_back_button")
        self.assertEqual(re.findall(r'onclick\s*=\s*"([^"]*)"', back),
                         ["[InformationPanelBar.OpenPreviousPanel]", "[GetVariableSystem.Clear('te_je_see_through')]"])
        self.assertRegex(back, r'input_action\s*=\s*"back"', "vanilla's back shortcut kept")


class MapModeTest(unittest.TestCase):
    def test_listed_copy_is_gone(self):
        # check 5 (2026-11-05): with no page open it painted nothing, and with one open it showed that page's map
        self.assertFalse(os.path.exists(os.path.join(REPO, MAP_MODE)) or tracked(MAP_MODE), MAP_MODE)


class DocsTest(unittest.TestCase):
    def test_playtest_names_every_test_piece(self):
        doc = read(PLAYTEST)
        for piece in ("TE_JMAP", "te_jmap_repaint", "te_je_see_through"):
            self.assertIn(piece, doc)


if __name__ == "__main__":
    unittest.main()
