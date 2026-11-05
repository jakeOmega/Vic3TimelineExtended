"""Journal entry map modes, first pass (docs/systems/mod_systems/journal_map_modes.md).

The engine says nothing about a map's script: a named color it doesn't know, a tooltip key with no loc or a selector
number no branch reads all fail silently on the map. So this holds the pieces together offline:

- every color a map names is one of the mod's (common/named_colors/te_journal_map_colors.txt), and each is used;
- every Map Room pick sets a selector that map_color and map_tooltip both branch on, and each pick has its loc;
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
BANKING = "common/journal_entries/je_banking.txt"
MAP_ENTRIES = (HOST, BANKING)
BUTTONS = "common/scripted_buttons/te_journal_map_buttons.txt"
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
        for rel in (HOST, BUTTONS, COLORS, VALUES, WIDGETS,
                    "common/scripted_effects/te_journal_map_effects.txt",
                    "common/scripted_guis/te_journal_map_sguis.txt"):
            with open(os.path.join(REPO, rel), "rb") as f:
                head = f.read(6)
            self.assertTrue(head.startswith(BOM) and not head[3:].startswith(BOM), rel)


class ColorsTest(unittest.TestCase):
    def test_every_map_color_is_defined(self):
        known = named_colors()
        for rel, name in ((HOST, "je_te_map_host"), (HOST, "je_te_map_hidden_world"), (BANKING, "je_banking_cycle")):
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
        self.host = entry(HOST, "je_te_map_host")
        self.buttons = code(BUTTONS)

    def picks(self):
        """{button: selector} for every pick button the entry lists."""
        listed = re.findall(r"scripted_button\s*=\s*(\w+)", self.host)
        out = {}
        for name in listed:
            body = block(self.buttons, name)
            self.assertIsNotNone(body, f"{name}: listed on the entry, not defined")
            m = re.search(r"te_jmap_set_selector\s*=\s*\{\s*SEL\s*=\s*(\d+)\s*\}", body)
            if m:
                out[name] = int(m.group(1))
        return out

    def test_every_pick_has_a_map_and_a_tooltip(self):
        picks = self.picks()
        self.assertEqual(sorted(picks.values()), list(range(1, 8)), "selectors 1-7, one button each")
        color = block(self.host, "map_color")
        tooltip = block(self.host, "map_tooltip")
        for name, sel in picks.items():
            branch = re.compile(r"te_jmap_selector\s*=\s*" + str(sel) + r"\b")
            self.assertRegex(color, branch, f"{name}: map_color has no branch for selector {sel}")
            self.assertRegex(tooltip, branch, f"{name}: map_tooltip has no branch for selector {sel}")

    def test_every_pick_marks_itself_selected(self):
        for name, sel in self.picks().items():
            body = block(self.buttons, name)
            self.assertRegex(body, r"selected\s*=\s*\{\s*var:te_jmap_sel\s*\?=\s*" + str(sel) + r"\s*\}", name)

    def test_the_entry_hides_itself_on_its_variable(self):
        for key in ("is_shown_when_inactive", "possible"):
            self.assertIn("has_variable = te_jmap_host_on", block(self.host, key), key)
        self.assertRegex(self.host, r"can_deactivate\s*=\s*yes")
        self.assertNotRegex(self.host, r"\boutcome\s*=", "the Map Room never concludes; Close deactivates it")

    def test_no_ai_weight(self):
        for name in re.findall(r"^(te_jmap_\w+)\s*=\s*\{", self.buttons, re.M):
            self.assertRegex(block(self.buttons, name), r"ai_chance\s*=\s*\{\s*value\s*=\s*0\s*\}", name)


class LocTest(unittest.TestCase):
    def test_tooltips_buttons_and_names_have_loc(self):
        keys = loc_keys()
        wanted = set()
        for rel in MAP_ENTRIES:
            wanted |= set(re.findall(r"custom_tooltip_no_bullet\s*=\s*(\w+)", code(rel)))
        buttons = code(BUTTONS)
        wanted |= set(re.findall(r'\b(?:name|desc)\s*=\s*"(\w+)"', buttons))
        wanted |= set(re.findall(r'(?:text|tooltip)\s*=\s*"(te_jmap_\w+)"', code(WIDGETS)))
        wanted |= {"je_te_map_host", "je_te_map_host_reason", "je_te_map_hidden_world",
                   "je_te_map_hidden_world_reason", "mm_te_journal_entry_map"}
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
        for piece in ("te_jmap_test_strip", "je_te_map_hidden_world", MAP_MODE, "TE_JMAP"):
            self.assertIn(piece, doc)


if __name__ == "__main__":
    unittest.main()
