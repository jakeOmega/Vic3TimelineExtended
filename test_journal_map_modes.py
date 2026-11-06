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
- every journal page has the see-through eye (gui/journal_entry.gui): a pick's reopen keeps it, closing clears it.
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
MAP_ENTRIES = (HOST, BANKING)
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
        for rel in (HOST, COLORS, VALUES, SCALES, WIDGETS, ROOM_WIDGET, EFFECTS, SGUIS):
            with open(os.path.join(REPO, rel), "rb") as f:
                head = f.read(6)
            self.assertTrue(head.startswith(BOM) and not head[3:].startswith(BOM), rel)


class ColorsTest(unittest.TestCase):
    def test_every_map_color_is_defined(self):
        known = named_colors()
        for rel, name in ((HOST, "je_te_map_room"), (BANKING, "je_banking_cycle")):
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
        self.assertEqual(sorted(picks.values()), [1] + list(range(3, 18)), "one pick per selector, 2 unused")
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
        """The selectors the last OR-only branch of key lists: the maps that show grey for a state with no figure."""
        part = block(self.room, key)
        ors = re.findall(r"\bOR\s*=\s*\{([^{}]*te_jmap_selector[^{}]*)\}", part)
        self.assertTrue(ors, f"{key}: no 'no data' branch")
        return {int(n) for n in re.findall(r"te_jmap_selector\s*=\s*(\d+)", ors[-1])}

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
        self.assertEqual(self.no_data("map_color"), gated, "map_color's 'no data' OR")
        self.assertEqual(self.no_data("map_tooltip"), gated, "map_tooltip's 'no data' OR")

    def test_a_years_figures_wait_for_a_step(self):
        # a seed writes births, deaths and migration as 0, and no causes of death (te_demog_state_stepped_sgui): those
        # maps show grey until the state's first full year
        for sel in (7, 8, 9, 11, 13):
            for key in ("map_color", "map_tooltip"):
                for body in self.branches(key, sel):
                    self.assertRegex(body, r"var:te_dg_stepped\s*>\s*0", f"{key}, selector {sel}")

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

    def test_banking_button_has_no_activity_gate(self):
        # the entry is active from the engine's first check (possible = yes), and an inactive page would open and
        # paint too (check 7, 2026-11-05), so the button needs no IsActive gate
        self.assertNotIn("IsActive", block(code(WIDGETS), "te_jmap_banking_map_button"))
        self.assertRegex(block(code(BANKING), "je_banking_cycle"), r"\bpossible\s*=\s*\{\s*always\s*=\s*yes\s*\}")

    def test_map_buttons_open_pages_whole(self):
        for name in ("te_jmap_demog_map_button", "te_jmap_banking_map_button"):
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
