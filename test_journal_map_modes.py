"""Journal entry map modes, second pass (docs/systems/mod_systems/journal_map_modes.md).

The engine says nothing about a map's script: a named color it doesn't know, a tooltip key with no loc or a selector
number no branch reads all fail silently on the map. So this holds the pieces together offline:

- every color a map names is one of the mod's (common/named_colors/te_journal_map_colors.txt), and each is used;
- every Map Room pick (a scripted GUI) sets a selector that map_color and map_tooltip both branch on, has a
  button, and has its loc; the Map Room stays contextless, in no journal, with no scripted buttons (they lock);
- every map_tooltip key has loc;
- the map buttons are mounted, the test strip shows only in debug mode, and every GUI reach into an entry names one
  that exists;
- the listed map mode copy is committed, listed and named.
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
WIDGETS = "gui/te_map_widgets.gui"
DEMOG_LAYOUT = "gui/te_demographics_layout.gui"
BANKING_LAYOUT = "gui/journal_entry_widgets/banking_layout_widget.gui"
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


def enclosing(text, pos):
    """The body of the innermost `{ ... }` around pos."""
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
    return text[i + 1:j - 1]


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
    """Whether git tracks rel. CI checks out without gfx/ (sparse), so a committed file can be absent on disk."""
    return subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO,
                          capture_output=True).returncode == 0


class FilesTest(unittest.TestCase):
    def test_each_new_file_has_one_bom(self):
        for rel in (HOST, COLORS, VALUES, WIDGETS, ROOM_WIDGET, EFFECTS, SGUIS):
            with open(os.path.join(REPO, rel), "rb") as f:
                head = f.read(6)
            self.assertTrue(head.startswith(BOM) and not head[3:].startswith(BOM), rel)


class ColorsTest(unittest.TestCase):
    def test_every_map_color_is_defined(self):
        known = named_colors()
        for rel, name in ((HOST, "je_te_map_room"), (HOST, "je_te_map_potential_probe"), (BANKING, "je_banking_cycle")):
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
        self.assertEqual(sorted(picks.values()), list(range(1, 7)), "selectors 1-6, one pick each")
        color = block(self.room, "map_color")
        tooltip = block(self.room, "map_tooltip")
        for name, sel in picks.items():
            branch = re.compile(r"te_jmap_selector\s*=\s*" + str(sel) + r"\b")
            self.assertRegex(color, branch, f"{name}: map_color has no branch for selector {sel}")
            self.assertRegex(tooltip, branch, f"{name}: map_tooltip has no branch for selector {sel}")

    def test_the_current_pick_is_invalid_so_its_button_draws_pressed(self):
        for name, sel in self.picks().items():
            valid = block(block(self.sguis, name), "is_valid")
            self.assertRegex(valid, r"NOT\s*=\s*\{\s*te_jmap_selector\s*=\s*" + str(sel) + r"\s*\}", name)

    def test_every_pick_has_a_button(self):
        row = block(code(WIDGETS), "te_jmap_pick_row")
        self.assertIsNotNone(row)
        for name in self.picks():
            for call in ("IsShown", "IsValid", "Execute"):
                self.assertIn(f"GetScriptedGui('{name}').{call}(", row, f"{name}: no {call} in te_jmap_pick_row")

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


class PotentialProbeTest(unittest.TestCase):
    def test_the_probe_stays_inactive(self):
        probe = entry(HOST, "je_te_map_potential_probe")
        self.assertRegex(block(probe, "possible"), r"always\s*=\s*no")
        self.assertIn("has_variable = te_jmap_potential_probe", block(probe, "is_shown_when_inactive"))
        self.assertNotRegex(probe, r"\bcontext\s*=", "a country entry, so it can sit in a journal's Potential")


class LocTest(unittest.TestCase):
    def test_tooltips_buttons_and_names_have_loc(self):
        keys = loc_keys()
        wanted = set()
        for rel in MAP_ENTRIES:
            wanted |= set(re.findall(r"custom_tooltip_no_bullet\s*=\s*(\w+)", code(rel)))
        for rel in (WIDGETS, ROOM_WIDGET):
            wanted |= set(re.findall(r'(?:text|tooltip)\s*=\s*"(te_jmap_\w+)"', code(rel)))
        wanted |= {"je_te_map_room", "je_te_map_room_reason", "je_te_map_potential_probe",
                   "je_te_map_potential_probe_reason", "mm_te_journal_entry_map"}
        self.assertEqual(wanted - keys, set(), "loc keys missing")


class GuiTest(unittest.TestCase):
    def test_buttons_are_mounted(self):
        self.assertIn("te_jmap_demog_map_button = {}", code(DEMOG_LAYOUT))
        self.assertIn("te_jmap_test_strip = {}", code(DEMOG_LAYOUT))
        self.assertIn("te_jmap_banking_map_button = {}", code(BANKING_LAYOUT))

    def test_test_strip_is_debug_only(self):
        strip = block(code(WIDGETS), "te_jmap_test_strip")
        self.assertIsNotNone(strip)
        first = re.search(r'visible\s*=\s*"([^"]*)"', strip).group(1)
        self.assertIn("InDebugMode", first, "the strip's own visible must gate it on debug mode")

    def test_every_entry_the_gui_opens_exists(self):
        entries = set(re.findall(r"^([a-z_0-9]+)\s*=\s*\{", code(HOST), re.M)) | {"je_banking_cycle"}
        for name in re.findall(r"GetPlayerJournalEntry\('(\w+)'\)", code(WIDGETS)):
            self.assertIn(name, entries)

    def test_every_open_names_its_entry_by_datacontext(self):
        # GetPlayerJournalEntry fails at load inside a callback, bare (first launch) and ended with .AccessSelf
        # ("requires non const promote", third session): the button carries the entry as its datacontext
        text = code(WIDGETS)
        self.assertNotRegex(text, r'onclick\s*=\s*"[^"]*GetPlayerJournalEntry')
        for m in re.finditer(r"OpenJournalEntryPanel\(([^)]*)\)", text):
            self.assertEqual(m.group(1), "JournalEntry.AccessSelf")
            self.assertIn('datacontext = "[GetPlayerJournalEntry(', enclosing(text, m.start()),
                          "an open with no entry datacontext on its own widget")

    def test_demographics_button_is_one_click(self):
        button = block(code(WIDGETS), "te_jmap_demog_map_button")
        clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', button)
        self.assertEqual(len(clicks), 2, "pick, then open")
        self.assertIn("te_jmap_pick_life_expectancy_sgui", clicks[0])
        self.assertIn("OpenJournalEntryPanel", clicks[1])
        self.assertIn("GetPlayerJournalEntry('je_te_map_room')", button)


class MapModeTest(unittest.TestCase):
    def test_listed_copy_is_committed(self):
        if not os.path.exists(os.path.join(REPO, MAP_MODE)):
            self.assertTrue(tracked(MAP_MODE), MAP_MODE)
            return
        text = code(MAP_MODE)
        body = block(text, "mm_te_journal_entry_map")
        self.assertIsNotNone(body)
        self.assertRegex(body, r"map_painting_mode\s*=\s*journal_entry_map_data\b")
        self.assertRegex(body, r"is_visible\s*=\s*yes")
        with open(os.path.join(REPO, MAP_MODE), "rb") as f:
            self.assertTrue(f.read(3) == BOM)


class DocsTest(unittest.TestCase):
    def test_playtest_names_every_test_piece(self):
        doc = read(PLAYTEST)
        for piece in ("te_jmap_test_strip", "je_te_map_potential_probe", "te_jmap_pick_scope_probe", MAP_MODE,
                      "TE_JMAP"):
            self.assertIn(piece, doc)


if __name__ == "__main__":
    unittest.main()
