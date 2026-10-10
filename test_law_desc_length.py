"""Every law description the mod writes fits the enactment popup.

The "We now have <law>!" popup prints `<law>_desc` in a frame beside the art
that holds nine lines, centered vertically, and does not scroll or grow. A
longer text runs off both ends: the top lines slide under the header and the
bottom ones over the modifier list. `law_limited_war_desc` shipped at 493
rendered characters and lost a line at each end (2026-10-10 screenshot).

The popup wraps at about 46 characters a line. Wrapping the rendered text
greedily at 46 reproduces that screenshot line for line: twelve lines, with
breaks after "with", "and", "in a", "so we", "aims", "become", "from", "and",
"country", "face" and "are". The check wraps at WRAP_WIDTH, a little narrower,
so text with wide letters still fits, and allows MAX_LINES. Every vanilla law
description fits that budget too (the longest, `law_strict_edo_system`, is 294
characters and eight lines).

Rendering expands `$key$` references and `[concept_x]` links to their text
(mod over vanilla loc), keeps a `Concept('x', 'text')` link's display text,
drops `#x ` / `#!` formatting, and turns `\\n` into a line break. A data
expression the model can't size (`[GetPlayer.GetName]`) fails the test so
someone decides how long it renders.

Fix a failure by cutting the description to flavor, with no figures, and
putting the rules in the law's effects (scripting_best_practices.md, "A Law's
Description Is Flavor"). Run: python3 test_law_desc_length.py
"""

import json
import os
import re
import textwrap
import unittest

from mod_state import split_loc_line

REPO = os.path.dirname(os.path.abspath(__file__))
LAWS_DIR = os.path.join(REPO, "common", "laws")
LOC_DIR = os.path.join(REPO, "localization", "english")
VANILLA_LOC = os.path.join(REPO, "vanilla_parsed", "localization_english.json")
VANILLA_LAWS = os.path.join(REPO, "vanilla_parsed", "common", "laws.json")

WRAP_WIDTH = 44
MAX_LINES = 9

_LAW_RE = re.compile(r"^(?:INJECT:|REPLACE:)?(\w+)\s*=\s*\{", re.MULTILINE)
_REF_RE = re.compile(r"\$([\w.]+)(?:\|[^$]*)?\$")
_CONCEPT_LINK_RE = re.compile(r"\[(concept_\w+)\]")
_CONCEPT_CALL_RE = re.compile(r"\[Concept\(\s*'[^']*'\s*,\s*'([^']*)'\s*\)\]")
_FORMAT_RE = re.compile(r"#[A-Za-z_;]+ |#!")


def _mod_loc():
    out = {}
    for fname in sorted(os.listdir(LOC_DIR)):
        if not fname.endswith(".yml"):
            continue
        with open(os.path.join(LOC_DIR, fname), encoding="utf-8-sig") as f:
            for line in f:
                parsed = split_loc_line(line)
                if parsed:
                    out[parsed[0]] = parsed[1]
    return out


def _mod_laws():
    laws = set()
    for fname in os.listdir(LAWS_DIR):
        if fname.endswith(".txt"):
            with open(os.path.join(LAWS_DIR, fname), encoding="utf-8-sig") as f:
                laws.update(_LAW_RE.findall(f.read()))
    return laws


def render(value, loc, depth=0):
    """The text a loc value shows, as far as a static read can tell."""
    if depth > 8:
        raise ValueError("loc references nest too deep")
    expand = lambda key: render(loc[key], loc, depth + 1) if key in loc else key  # noqa: E731
    value = _CONCEPT_CALL_RE.sub(lambda m: render(m.group(1), loc, depth + 1), value)
    value = _CONCEPT_LINK_RE.sub(lambda m: expand(m.group(1)), value)
    value = _REF_RE.sub(lambda m: expand(m.group(1)), value)
    return _FORMAT_RE.sub("", value)


def wrapped_lines(text, width=WRAP_WIDTH):
    """The lines a greedy word wrap at `width` characters gives, with `\\n`
    starting a new line (an empty paragraph still takes one)."""
    lines = []
    for paragraph in text.split("\\n"):
        lines.extend(textwrap.wrap(paragraph, width, break_long_words=False) or [""])
    return lines


class LawDescriptionLengthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(VANILLA_LOC, encoding="utf-8") as f:
            cls.vanilla_loc = json.load(f)
        with open(VANILLA_LAWS, encoding="utf-8") as f:
            cls.vanilla_laws = set(json.load(f))
        cls.mod_loc = _mod_loc()
        cls.loc = {**cls.vanilla_loc, **cls.mod_loc}
        cls.mod_laws = _mod_laws()

    def _check(self, keys, loc):
        self.assertTrue(keys)
        for key in sorted(keys):
            with self.subTest(key=key):
                text = render(loc[key], self.loc)
                self.assertNotRegex(text, r"\[", f"{key}: a data expression the model can't size")
                lines = wrapped_lines(text)
                self.assertLessEqual(
                    len(lines), MAX_LINES,
                    f"{key} wraps to {len(lines)} lines ({len(text)} characters); the enactment "
                    f"popup shows {MAX_LINES}. Cut it to flavor and leave the rules to the effects.",
                )

    def test_every_mod_law_description_fits_the_enactment_popup(self):
        laws = self.mod_laws | self.vanilla_laws
        self._check({f"{law}_desc" for law in laws} & self.mod_loc.keys(), self.mod_loc)

    def test_every_vanilla_law_description_fits(self):
        """Calibration: the budget passes the base game's own descriptions."""
        keys = {f"{law}_desc" for law in self.vanilla_laws} & self.vanilla_loc.keys()
        self._check(keys, self.vanilla_loc)

    def test_the_text_that_overflowed_fails(self):
        """The model wraps the screenshot's text as the game did, and fails it."""
        text = render(OVERFLOWED, self.loc)
        at_game_width = wrapped_lines(text, 46)
        self.assertEqual(len(at_game_width), 12)
        self.assertEqual(at_game_width[1], "proportionate force, sparing civilians and")
        self.assertEqual(at_game_width[-1], "fighting.")
        self.assertGreater(len(wrapped_lines(text)), MAX_LINES)


# law_limited_war_desc as it overflowed the popup (2026-10-10 screenshot).
OVERFLOWED = (
    "War is fought for limited aims with proportionate force, sparing civilians and civilian "
    "[concept_infrastructure]. Each [concept_war_goal] in a play we start costs twice the "
    "[Concept('concept_maneuver', '$concept_maneuvers$')], so we take less at once, and the world "
    "forgives aims that stay limited. Crises are slow to become wars and the public follows the "
    "fighting from a distance. All nuclear strikes, strategic and tactical, are forbidden unless we "
    "or a country we protect have been struck, or we face annexation or subjugation in a war we "
    "are fighting."
)


if __name__ == "__main__":
    unittest.main()
