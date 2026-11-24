"""The journal entry page's modifier icons, and the journal list's line for an entry.

`gui/journal_entry.gui` is vanilla's page with the mod's changes. Vanilla stacks an entry's scaling and timed
modifier icons four to a row at the right of the 120 px header, centred on it, which holds two rows. The mod's
entries carry more (the United Nations 26 in a game of 2032): the rows ran above the header and below it, over the
page's first lines and its "?" (seen in game, 2026-11-24). The header now draws them only while they fit, and a
strip under it draws them otherwise.

The journal's list prints an entry's `progress_desc` beside its bar. It is a reading ("Global Temperature: 2.75 °C"),
not an explanation: the United Nations' was a six-line paragraph in the list.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PANEL = (ROOT / "gui" / "journal_entry.gui").read_text(encoding="utf-8-sig")
JE_DIR = ROOT / "common" / "journal_entries"
LOC_DIR = ROOT / "localization" / "english"

READING_LIMIT = 60      # characters as drawn; vanilla's are a label and a figure


def _block_after(marker: str) -> str:
    """The first `{ ... }` block after `marker`, braces balanced."""
    start = PANEL.index("{", PANEL.index(marker))
    depth = 0
    for i in range(start, len(PANEL)):
        if PANEL[i] == "{":
            depth += 1
        elif PANEL[i] == "}":
            depth -= 1
            if depth == 0:
                return PANEL[start:i + 1]
    raise AssertionError("unbalanced block after %r" % marker)


def _visible(block: str) -> str:
    return re.search(r'visible = "\[(.*)\]"', block).group(1)


class HeaderModifiersTest(unittest.TestCase):
    HEADER = "### TIMED AND SCALING MODIFIERS\n"
    WIDE = "### TIMED AND SCALING MODIFIERS, WIDE\n"

    def test_the_header_draws_them_only_while_they_fit(self):
        visible = _visible(_block_after(self.HEADER))
        for part in ("LessThan_int32( GetDataModelSize( JournalEntry.GetScalingModifiers ), '(int32)5' )",
                     "LessThan_int32( GetDataModelSize( JournalEntry.GetTimedModifiers ), '(int32)5' )",
                     "And( IsDataModelEmpty( JournalEntry.GetScalingModifiers ), "
                     "LessThan_int32( GetDataModelSize( JournalEntry.GetTimedModifiers ), '(int32)9' ) )",
                     "And( IsDataModelEmpty( JournalEntry.GetTimedModifiers ), "
                     "LessThan_int32( GetDataModelSize( JournalEntry.GetScalingModifiers ), '(int32)9' ) )"):
            self.assertIn(part, visible)

    def test_the_strip_draws_them_when_they_do_not(self):
        wide = _block_after(self.WIDE)
        fits = _visible(_block_after(self.HEADER)).split(", Or( And( LessThan_int32", 1)[1]
        self.assertIn("Not( Or( And( LessThan_int32" + fits[:-2], _visible(wide),
                      "the strip must show exactly when the header's fit test fails")
        self.assertIn("Not( JournalEntry.HasCustomWidget('custom_widget_container_je_icon') )", _visible(wide),
                      "an entry with its own header widget keeps vanilla's ALT block")
        self.assertEqual(wide.count("wrap_count = 12"), 2)
        for datamodel, tooltip in (("JournalEntry.GetScalingModifiers", "ScalingModifier.GetTooltip"),
                                   ("JournalEntry.GetTimedModifiers", "TimedModifier.GetTooltip")):
            self.assertIn('datamodel = "[%s]"' % datamodel, wide)
            self.assertIn('tooltip = "[%s]"' % tooltip, wide)
        self.assertIn("minimumsize = { 475 -1 }", wide, "twelve 35 px icons and their 5 px gaps")
        self.assertNotIn("parentanchor = hcenter\n\t\t\t\t\t\tspacing", wide, "the two lists share a left edge")

    def test_the_strip_sits_between_the_header_and_vanillas_alt_block(self):
        self.assertLess(PANEL.index(self.HEADER), PANEL.index(self.WIDE))
        self.assertLess(PANEL.index(self.WIDE), PANEL.index("### TIMED AND SCALING MODIFIERS ALT\n"))


class ProgressDescIsAReadingTest(unittest.TestCase):
    def test_no_entry_prints_a_paragraph_in_the_journals_list(self):
        loc = {}
        for path in sorted(LOC_DIR.rglob("*.yml")):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r'\s*([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    loc[m.group(1)] = m.group(2)
        keys = set()
        for path in sorted(JE_DIR.glob("*.txt")):
            keys.update(re.findall(r"^\s*progress_desc\s*=\s*([A-Za-z0-9_.]+)", path.read_text(encoding="utf-8-sig"), re.M))
        self.assertIn("un_authority_progress_desc", keys)
        too_long = []
        for key in sorted(keys):
            text = loc[key]
            text = re.sub(r"\[Concept\('[^']*',\s*'([^']*)'\)\]", r"\1", text)
            text = re.sub(r"\[(concept_[a-z0-9_]+)\]", lambda m: loc.get(m.group(1), "Concept"), text)
            text = re.sub(r"\[[^\]]*\]", "0000", text)          # a figure or a short custom word
            text = re.sub(r"#[A-Za-z_;:0-9]+\s", "", text).replace("#!", "")
            if len(text) > READING_LIMIT:
                too_long.append("%s: %d characters: %r" % (key, len(text), text))
        self.assertEqual(too_long, [], "a progress_desc is the reading beside the entry's bar in the journal's list; "
                         "an explanation belongs in a concept or on the Help page")


if __name__ == "__main__":
    unittest.main()
