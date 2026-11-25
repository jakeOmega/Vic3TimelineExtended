"""An overview cell's word must fit its cell: nothing a player reads ends in "..." (gui_style_guide.md § 3).

Every system's overview is a grid of Banking's `te_banking_ov_cell`, whose lines are `te_banking_ov_word` textboxes
154 px wide that elide on the right. A word that is too long is cut with no log line: on a December 2032 save the
United Nations' Membership cell read "Permanent Mem..." for a permanent member (2026-11-24), sixteen characters in
the bold face the `#v` / `#G` / `#R` / `#Y` formats draw. Measured on that shot, the bold face runs 8 to 10.5 px a
character, so fourteen characters is what 154 px holds whatever the letters; the plain face holds seventeen.

The test reads each word's text as far as it is fixed: a loc key, or the keys a `SelectLocalization` picks between,
followed down to the strings. A string with a figure in it (`[...]`) is left out, since its width is the figure's.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOC_DIR = ROOT / "localization" / "english"
GUI_DIR = ROOT / "gui"

BOLD_LIMIT = 14     # characters of a word in a bold format in a 154 px line
PLAIN_LIMIT = 17    # characters of a plain word there
DEFAULT_WIDTH = 154
# `#bold;yellow` and `#blue_value` are the bold yellow and blue of a ladder whose other states are
# `#G` / `#R` / `#v` (PR #2031).
_BOLD = re.compile(r"#(?:v|G|R|Y|b|bold|N|P|bold;yellow|blue_value)\s")
_LOC_LINE = re.compile(r'\s*([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$')
_WORD_BLOCK = re.compile(r"te_banking_ov_word\s*=\s*\{(.*?)\n\t*\}", re.S)
_QUOTED_KEY = re.compile(r"'([A-Za-z0-9_.]+)'")


def _loc() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(LOC_DIR.rglob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = _LOC_LINE.match(line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def _leaves(key: str, loc: dict[str, str], seen: set[str] | None = None) -> list[tuple[str, str]]:
    """The fixed strings `key` can show: itself, or the strings of the keys its SelectLocalization picks between."""
    seen = set() if seen is None else seen
    if key in seen or key not in loc:
        return []
    seen.add(key)
    value = loc[key]
    if "SelectLocalization" in value or "Localize(" in value:
        found: list[tuple[str, str]] = []
        for sub in _QUOTED_KEY.findall(value):
            found += _leaves(sub, loc, seen)
        return found
    return [(key, value)]


def _spliced(value: str, loc: dict[str, str], depth: int = 0) -> str:
    """`value` with each `$key$` replaced by that key's text."""
    if depth > 5:
        return value
    return re.sub(r"\$([A-Za-z0-9_]+)\$", lambda m: _spliced(loc.get(m.group(1), "X"), loc, depth + 1), value)


def _shown(value: str, loc: dict[str, str]) -> str:
    """A spliced `value` as drawn, formats and concept links replaced by their words."""
    value = re.sub(r"\[Concept\('[^']*',\s*'([^']*)'\)\]", r"\1", value)
    value = re.sub(r"\[(concept_[a-z0-9_]+)\]", lambda m: _shown(loc.get(m.group(1), "Concept"), loc), value)
    value = re.sub(r"#[A-Za-z_;:0-9]+\s", "", value).replace("#!", "")
    return re.sub(r"@[a-z_0-9]+!", "M", value)


def overview_words() -> list[tuple[str, str, str, bool, int]]:
    """(file, key, text as drawn, bold, width) for every fixed string an overview cell's word line can show."""
    loc = _loc()
    out = []
    for path in sorted(GUI_DIR.rglob("*.gui")):
        for block in _WORD_BLOCK.findall(path.read_text(encoding="utf-8-sig")):
            text = re.search(r'text\s*=\s*"([^"]*)"', block)
            if not text:
                continue
            width = re.search(r"max_width\s*=\s*(\d+)", block)
            keys = _QUOTED_KEY.findall(text.group(1)) if text.group(1).startswith("[") else [text.group(1)]
            for key in keys:
                for leaf, value in _leaves(key, loc):
                    value = _spliced(value, loc)
                    if "[" in re.sub(r"\[Concept\('[^']*',\s*'[^']*'\)\]|\[concept_[a-z0-9_]+\]", "", value):
                        continue        # a figure: its width is not the string's
                    out.append((path.name, leaf, _shown(value, loc), bool(_BOLD.search(value)),
                                int(width.group(1)) if width else DEFAULT_WIDTH))
    return sorted(set(out))


class OverviewWordsFitTest(unittest.TestCase):
    def test_the_scan_finds_the_cells(self):
        words = overview_words()
        self.assertGreater(len(words), 60, "the scan no longer finds the overview cells' words")
        self.assertIn("je_un_ov_member_4", {key for _, key, _, _, _ in words})

    def test_no_fixed_word_is_longer_than_its_line_holds(self):
        too_long = []
        for name, key, shown, bold, width in overview_words():
            limit = (BOLD_LIMIT if bold else PLAIN_LIMIT) * width // DEFAULT_WIDTH
            if len(shown) > limit:
                too_long.append(f"{name}: {key} = {shown!r} ({len(shown)} characters, {limit} fit{' in bold' if bold else ''})")
        self.assertEqual(too_long, [], "an overview cell would cut these with '...': shorten the word (drop what the "
                         "caption already says) and keep the full text in the cell's hover\n" + "\n".join(too_long))


if __name__ == "__main__":
    unittest.main()
