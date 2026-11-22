"""Every game rule setting the mod defines has a description that fits the Game Rules screen.

Each rule's card on the Game Rules screen prints the chosen setting's `setting_<name>_desc` in a fixed box under the
selector. The box shrinks the type for a longer text, down to a floor, and at the floor holds four lines; past that
it cuts the text off with an ellipsis, and nothing on the screen shows the rest. In the owner's screenshot of
2026-11-13, Internal Resettlement Enabled (186 characters) sat in three lines of the larger type, Grand Monuments
Enabled (306) filled four lines at the floor, and Space Race: Full Colonies (360), Universal Aptitude Traits
Disabled (422) and Free Market Construction Disabled (648) were cut off in their fourth line. The last lost the
one sentence a player most needed: that Construction Sites must be built from the state view.

At the floor a line held 69 to 86 characters of that screenshot's text (the font is proportional), and the
shortest line that would not take its next word would have been 82 characters with it. The check wraps at
WRAP_WIDTH, a little under that, and allows MAX_LINES. The screenshot's texts sort as the game sorted them (`test_the_screenshot_sorts_as_the_game_did`),
and every vanilla description fits with room to spare (the longest, `setting_use_custom_rng_seed_desc`, is 227
characters and three lines).

Rendering is `test_law_desc_length.render`: `$key$` references and `[concept_x]` links become their text (mod over
vanilla loc), a `Concept('x', 'text')` link keeps its display text, `#x ` / `#!` formatting is dropped and `\\n`
starts a new line. A data expression the model can't size fails the test so someone decides how long it renders.

Fix a failure by cutting the description to what a player choosing the setting needs: what it switches on or off,
and anything they must do differently. The rest belongs in the system's concept, journal entry or the player guide
(`docs/player_guide/01-introduction.md` has a row for every rule). Run: python3 -m pytest test_game_rule_desc_length.py
"""

import json
import os
import unittest

from mod_state import split_loc_line
from paradox_file_parser import ParadoxFileParser
from test_law_desc_length import _mod_loc, render, wrapped_lines

REPO = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.join(REPO, "common", "game_rules")
VANILLA_LOC = os.path.join(REPO, "vanilla_parsed", "localization_english.json")
REPLACE_LOC_DIR = os.path.join(REPO, "localization", "english", "replace")


def _mod_loc_with_overrides():
    """The mod's English loc with its `replace/` overrides on top, as the engine reads it. A vanilla rule the mod
    redefines (`00_a_te_free_construction.txt`) keeps vanilla's setting name, so its text is a `replace/` key."""
    out = _mod_loc()
    for fname in sorted(os.listdir(REPLACE_LOC_DIR)):
        if fname.endswith(".yml"):
            with open(os.path.join(REPLACE_LOC_DIR, fname), encoding="utf-8-sig") as f:
                for line in f:
                    parsed = split_loc_line(line)
                    if parsed:
                        out[parsed[0]] = parsed[1]
    return out

WRAP_WIDTH = 78
MAX_LINES = 4


def _unwrap(node):
    """The parser's ('=', value) pair, or a list of them for a repeated key, as the last value."""
    if isinstance(node, list):
        node = node[-1]
    return node[1] if isinstance(node, tuple) else node


def mod_rule_settings():
    """{setting name: rule name} for every setting of every rule in the mod's `common/game_rules/`."""
    settings = {}
    for fname in sorted(os.listdir(RULES_DIR)):
        if not fname.endswith(".txt"):
            continue
        parser = ParadoxFileParser()
        parser.parse_file(os.path.join(RULES_DIR, fname))
        for rule, body in parser.data.items():
            body = _unwrap(body)
            if not isinstance(body, dict):
                continue
            for setting, value in body.items():
                if setting != "default" and isinstance(_unwrap(value), dict):
                    settings[setting] = rule
    return settings


class GameRuleDescriptionLengthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(VANILLA_LOC, encoding="utf-8") as f:
            cls.vanilla_loc = json.load(f)
        cls.mod_loc = _mod_loc_with_overrides()
        cls.loc = {**cls.vanilla_loc, **cls.mod_loc}
        cls.settings = mod_rule_settings()

    def lines(self, value, width=WRAP_WIDTH):
        text = render(value, self.loc)
        self.assertNotRegex(text, r"\[", f"a data expression the model can't size: {text}")
        return wrapped_lines(text, width)

    def test_the_mod_defines_rules(self):
        self.assertGreater(len(self.settings), 40)
        self.assertEqual(self.settings["free_market_construction_disabled"], "free_market_construction_rule")

    def test_every_setting_description_fits_the_rule_card(self):
        for setting, rule in sorted(self.settings.items()):
            key = f"setting_{setting}_desc"
            with self.subTest(key=key):
                self.assertIn(key, self.mod_loc, f"{rule}: setting {setting} has no description")
                lines = self.lines(self.mod_loc[key])
                self.assertLessEqual(
                    len(lines), MAX_LINES,
                    f"{key} wraps to {len(lines)} lines at {WRAP_WIDTH} characters; the {rule} card shows "
                    f"{MAX_LINES} and cuts the rest off. Keep what a player choosing the setting needs and "
                    f"leave the rest to the system's concept or the player guide.",
                )

    def test_every_vanilla_setting_description_fits(self):
        """Calibration: the budget passes the base game's own descriptions."""
        keys = [k for k in self.vanilla_loc if k.startswith("setting_") and k.endswith("_desc")]
        self.assertGreater(len(keys), 30)
        for key in keys:
            with self.subTest(key=key):
                self.assertLessEqual(len(self.lines(self.vanilla_loc[key])), MAX_LINES)

    def test_the_screenshot_sorts_as_the_game_did(self):
        """The texts the 2026-11-13 screenshot showed whole pass, and the ones it cut off fail."""
        for name, text in SHOWN_WHOLE.items():
            with self.subTest(name=name):
                self.assertLessEqual(len(self.lines(text)), MAX_LINES)
        for name, text in CUT_OFF.items():
            with self.subTest(name=name):
                self.assertGreater(len(self.lines(text)), MAX_LINES)

    def test_direct_construction_no_longer_sends_the_player_to_the_state_view(self):
        """With the market off, Construction Sites could be queued only from the state view, and the description
        said so inside its four lines. Since 2026-11-13 the production lens's Development tab offers them
        (`lens = development` on te_construction_market_bg, test_construction_rule_switch.py), so the note is
        gone. What a player choosing the setting does need is that it can be chosen in a running game."""
        text = render(self.mod_loc["setting_free_market_construction_disabled_desc"], self.loc)
        self.assertNotIn("state view", text)
        self.assertIn("changed in a running game", text)


# The descriptions as the 2026-11-13 screenshot showed them.
SHOWN_WHOLE = {
    "grand_monuments_enabled": (
        "Countries may raise Grand Monuments to their crown, republic, revolution, leader, faith or nation. What a "
        "monument honors can fall with the regime that raised it, and the next government decides whether to pull "
        "it down, rededicate it or keep it as heritage. An occupying army can carry one off as a trophy."
    ),
    "social_movements_enabled": (
        "The social movement journal entries are active. As nations research the relevant technologies, they work "
        "through civil rights, the human augmentation and morphological freedom debates, digital rights and "
        "surveillance, the post-scarcity transition, and mental health awareness."
    ),
}
CUT_OFF = {
    "space_race_colonies_full": (
        "As Simple Colonies, and wars reach space. Space Command builds warships that fly between the planets, "
        "fight, blockade colonies, and seize or destroy them; marines garrison colonies; an enemy fleet in Earth "
        "orbit stops your launches until you put up your reserve, and ground-to-orbit batteries fire on it. Holding "
        "Earth orbit supports your troops on the ground."
    ),
    "universal_aptitude_traits_disabled": (
        "Administrative, diplomatic, and military aptitude traits only exist alongside Heir Education. With Heir "
        "Education enabled, only rulers and heirs have them: a character who leaves the throne loses their aptitude "
        "traits, and regains the same ones if they return to power. Other characters (such as "
        "[concept_interest_group] leaders and generals) remain without them. With Heir Education also disabled, no "
        "character has aptitude traits."
    ),
    "free_market_construction_disabled": (
        "Construction works as in the base game. The $te_construction_market_site$ is your construction sector: the "
        "government builds and expands it, and each level provides construction points according to its production "
        "method. There is no construction good and no construction maintenance, and your economic-system law sets "
        "the private share of construction. The materials for each construction point spent are bought as in the "
        "base game. Every country gets a small base of construction, and AI countries keep the Construction Sites "
        "they have.\\n\\n#b Construction Sites must currently be built from the state view.#! This is a technical "
        "limitation that is being worked on."
    ),
}


if __name__ == "__main__":
    unittest.main()
