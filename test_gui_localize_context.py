"""A key passed to Localize() in a GUI expression renders without the widget's
journal entry, so its text must not read JournalEntry.

The nuclear widget's survivability row built its tooltip as
Concatenate( Localize( 'nd_w_survivability_tt' ), ... ), and that key showed
the effective survivability through JournalEntry.GetCountry. The figure came
out blank, and each render logged "Wrong context supplied, wanted context of
type 'JournalEntry' for 'JournalEntry.GetCountry...', got context 'Container'"
(2026-10-06). A plain tooltip key does get the journal entry, and it can pull
other keys in with $key$, whose data functions then evaluate in that context.
Localize() is for context-free text, such as te_tt_break.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

_LOCALIZE = re.compile(r"Localize\(\s*'([A-Za-z0-9_.]+)'\s*\)")
_STRING_OR_COMMENT = re.compile(r'("[^"\n]*")|#[^\n]*')
_LOC_LINE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d*\s*"(.*)"\s*$')


def english_loc():
    values = {}
    for path in sorted((ROOT / "localization" / "english").glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = _LOC_LINE.match(line)
            if m:
                values[m[1]] = m[2]
    return values


def expanded(key, loc, seen=()):
    """The key's text with every $other_key$ it includes spliced in."""
    text = loc.get(key, "")
    if key in seen:
        return text
    return re.sub(r"\$([A-Za-z0-9_.\-]+)\$",
                  lambda m: expanded(m[1], loc, seen + (key,)) if m[1] in loc else m[0], text)


def localized_keys(gui_text):
    # Drop comments but keep quoted strings whole: tooltip text carries #v and #!.
    lines = [_STRING_OR_COMMENT.sub(lambda m: m[1] or "", line) for line in gui_text.splitlines()]
    return [(n, key) for n, line in enumerate(lines, 1) for key in _LOCALIZE.findall(line)]


class TestGuiLocalizeContext(unittest.TestCase):
    def test_no_localized_key_reads_the_journal_entry(self):
        loc = english_loc()
        bad = []
        for path in sorted((ROOT / "gui").rglob("*.gui")):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            for line, key in localized_keys(text):
                if "JournalEntry." in expanded(key, loc):
                    bad.append(f"{path.relative_to(ROOT).as_posix()}:{line} Localize( '{key}' )")
        self.assertEqual(bad, [], "use the key as a plain tooltip/text, pulling other keys in with $key$")

    def test_the_check_sees_what_it_rejects(self):
        loc = {"a_tt": "x [JournalEntry.GetCountry.GetName]", "b_tt": "$a_tt$ and more",
               "c_tt": "#v [GetPlayer.GetName]#!", "brk": "\\n\\n"}
        gui = ("tooltip = \"[Concatenate( Localize( 'b_tt' ), Localize( 'brk' ) )]\"\n"
               "# tooltip = \"[Localize( 'a_tt' )]\"\n"
               "text = \"[Localize('c_tt')]\"\n"
               "tooltip = \"#v x#! [Localize( 'a_tt' )]\"\n")
        keys = localized_keys(gui)
        self.assertEqual(keys, [(1, "b_tt"), (1, "brk"), (3, "c_tt"), (4, "a_tt")])
        self.assertEqual([k for _, k in keys if "JournalEntry." in expanded(k, loc)], ["b_tt", "a_tt"])


if __name__ == "__main__":
    unittest.main()
