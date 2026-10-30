"""No mod panel underlines a hover's label or figure (gui_style_guide.md rule 3,
owner 2026-10-30).

Vanilla underlines a hoverable word in running text, not a hover's label or
value: 10 of the 693 text hovers in the mod's copies of its panels, 3 of the 68
in untouched ones. The mod's panels underlined nearly every hover under the
rule of 2026-10-27 (a label's default_format = "#tooltippable", a label_format
block toggling it, labels written "#tooltippable Word#!" in loc); the Space
Race's came into line in PR #1258 and the rest on 2026-10-30.

What stays underlined: vanilla's own markup in the mod's copies of its panels,
a nested tooltip on a word (`#tooltippable;tooltip:<key> Word#!`, or vanilla's
`#tooltippable #tooltip:<tag>,<key> ...` form), and a word inside a sentence
whose line carries the hover (the Banking notes' "Banking Cycle").
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
LOC_DIR = os.path.join(REPO, "localization", "english")

# Vanilla's own underlines in the mod's copies of its panels, left as vanilla
# has them: the treaty acceptance lines, unused arable land, the government
# type's nested tooltip.
VANILLA_OWN = {
    "gui/right_click_menu.gui": 2,
    "gui/states_panel_buildings.gui": 1,
    "gui/politics_panel_overview.gui": 1,
}

# A nested tooltip: the underline marks the one word that opens it.
NESTED = re.compile(r"#tooltippable(?:;tooltip:| #tooltip:)")

# A word inside a sentence, the line's hover about that word: the rule's case.
WORD_IN_TEXT = {
    "banking_dash_dormant_monetary_note",
    "banking_dash_dormant_tools_note",
    "banking_dash_ro_note",
}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _code(text):
    """A .gui file without its comments, keeping a `#` inside a string."""
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


def _loc():
    out = {}
    for path in sorted(glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True)):
        for m in re.finditer(r'^ (\w+):\d* "(.*)"\s*$', _read(path), re.M):
            out[m.group(1)] = m.group(2)
    return out


class GuiTest(unittest.TestCase):
    def test_no_mod_widget_underlines_its_text(self):
        files = sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True))
        self.assertGreater(len(files), 60)
        for path in files:
            rel = os.path.relpath(path, REPO).replace(os.sep, "/")
            code = _code(_read(path))
            with self.subTest(file=rel):
                if rel in VANILLA_OWN:
                    self.assertEqual(code.count("#tooltippable"), VANILLA_OWN[rel],
                                     "an underline the mod added to vanilla's panel, or vanilla's count changed")
                else:
                    self.assertNotIn("#tooltippable", NESTED.sub("", code))

    def test_no_underline_toggle_is_left(self):
        for path in glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True):
            code = _code(_read(path))
            with self.subTest(file=os.path.basename(path)):
                self.assertNotRegex(code, r'block(?:override)? "(?:label|row|cell|name)_format"')


class LocTest(unittest.TestCase):
    def test_no_panel_text_wraps_itself_in_an_underline(self):
        loc = _loc()
        self.assertGreater(len(loc), 10000)
        for key, value in loc.items():
            if key in WORD_IN_TEXT:
                continue
            with self.subTest(key=key):
                self.assertNotIn("#tooltippable", NESTED.sub("", value))

    def test_the_kept_words_sit_in_a_sentence(self):
        loc = _loc()
        for key in WORD_IN_TEXT:
            with self.subTest(key=key):
                value = loc[key]
                word = re.search(r"#tooltippable (.*?)#!", value)
                self.assertIsNotNone(word, "drop the key from WORD_IN_TEXT")
                self.assertTrue(value[:word.start()].strip() and value[word.end():].strip(),
                                "the underlined word is the whole line")


if __name__ == "__main__":
    unittest.main()
