"""A scripted progress bar's text has to fit on the bar.

`gui/journal_entry.gui` draws every scripted bar's `desc` (and a green bar's
`second_desc`) inside the bar, as one autoresizing line with no wrap, on a bar
504 wide. About 80 characters fill it, and the rest runs off the panel's edge:
the culture merges' bar shipped a 224-character explanation that way
(2026-11-08). Vanilla keeps every bar's text under about 50 characters, a label
and the bar's figure ("Bolshevik Support: 42%"); an explanation belongs in the
entry's status text or its reason.

The length counted is roughly what the player sees: a data function counts as
a short figure, a concept as its text, a `$key$` as the text it splices in, and
text markup as nothing.
"""

import json
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
BARS = ROOT / "common/scripted_progress_bars"
LOC = ROOT / "localization/english"
VANILLA_LOC = ROOT / "vanilla_parsed/localization_english.json"

# Room to spare under the ~80 characters that fill the bar, for a long culture or country name.
MAX_CHARS = 60

# Bars whose text is known to run off the bar. Remove a bar from here when its text is shortened;
# the test fails on an entry that no longer needs to be here.
KNOWN_TOO_LONG = set()


def _unwrap(value):
    """The parser's ``('=', value)`` pair, or a list of them for a repeated key, down to the last value."""
    while True:
        if isinstance(value, list) and value:
            value = value[-1]
        elif isinstance(value, tuple) and len(value) == 2:
            value = value[1]
        else:
            return value


def mod_loc():
    out = {}
    for path in sorted(LOC.rglob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r'^\s+([\w.\-]+):\d*\s+"(.*)"(?:\s*#.*)?$', line)
            if match:
                out[match.group(1)] = match.group(2)
    return out


def bar_text_keys():
    """(bar, field, loc key) for every desc and second_desc of the mod's scripted bars."""
    out = []
    for path in sorted(BARS.glob("*.txt")):
        parser = ParadoxFileParser()
        parser.parse_file(path)
        for bar, body in parser.data.items():
            body = _unwrap(body)
            if not isinstance(body, dict):
                continue
            for field in ("desc", "second_desc"):
                key = _unwrap(body.get(field))
                if isinstance(key, str):
                    out.append((bar, field, key.strip('"')))
    return out


def shown_length(text, loc, depth=0):
    """Roughly how many characters `text` takes on screen."""
    text = re.sub(r"\[Concept\('[^']*',\s*'([^']*)'\)\]", r"\1", text)
    text = re.sub(r"\[[^\]]*\]", "000%", text)

    def splice(match):
        inner = loc.get(match.group(1))
        if inner is None or depth > 3:
            return "x" * 10
        return "x" * shown_length(inner, loc, depth + 1)

    text = re.sub(r"\$([\w.\-]+)(?:\|[^$]*)?\$", splice, text)
    text = re.sub(r"#[\w;:.,\-]+ |#!", "", text)
    return len(text)


class ProgressBarDescLengthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = {**json.loads(VANILLA_LOC.read_text(encoding="utf-8")), **mod_loc()}
        cls.keys = bar_text_keys()

    def test_the_bars_are_found(self):
        self.assertGreater(len(self.keys), 30)
        self.assertIn(("te_cmg_german_bar", "desc", "te_cm_bar_desc"), self.keys)

    def test_every_bar_text_fits_on_the_bar(self):
        too_long = []
        for bar, field, key in self.keys:
            if key in KNOWN_TOO_LONG or key not in self.loc:
                continue
            length = shown_length(self.loc[key], self.loc)
            if length > MAX_CHARS:
                too_long.append("%s.%s = %s: %d characters" % (bar, field, key, length))
        self.assertEqual(sorted(set(too_long)), [], "shorten the bar's text to %d characters or fewer" % MAX_CHARS)

    def test_every_known_offender_is_still_too_long(self):
        for key in sorted(KNOWN_TOO_LONG):
            self.assertIn(key, {k for _, _, k in self.keys}, "%s is no longer a bar's text" % key)
            self.assertGreater(shown_length(self.loc[key], self.loc), MAX_CHARS,
                               "%s fits now: remove it from KNOWN_TOO_LONG" % key)

    def test_the_length_counts_what_the_player_sees(self):
        loc = {"x_name": "German"}
        self.assertEqual(shown_length("Support: #v [JournalEntry.GetCurrentBarProgress(ScriptedProgressBar.Self)|%]#!", loc),
                         len("Support: 000%"))
        self.assertEqual(shown_length("$x_name$ share", loc), len("German share"))
        self.assertEqual(shown_length("[Concept('concept_x','Control')] here", loc), len("Control here"))


if __name__ == "__main__":
    unittest.main()
