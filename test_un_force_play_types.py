# -*- coding: utf-8 -*-
"""The Standing UN Force's war-goal strike (redesign phase 7, §0.12 ruling 4)
tells the goal a play opened with from the play's type: a play opens with the
war_goal its type names. un_force_has_strikeable_goal
(common/scripted_triggers/un_force_triggers.txt) therefore lists, by hand,
which play types open with which goal. A list that drifts from the plays
would strike a play's own opening goal (unproven to leave a working play) or
leave a later goal unstruck, both engine-silent. This test reads the play
types from vanilla_parsed/common/diplomatic_plays.json and the mod's
common/diplomatic_plays/, and checks every list against them, so a vanilla
patch that adds or changes a play fails here.

Run: python3 -m unittest test_un_force_play_types -v
"""

import collections
import glob
import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "un_force_triggers.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_force_effects.txt")

# Goals no play is listed for on purpose: a play that opens with one is never
# struck (every formable adds such a play), and the mandate's own goal.
NEVER_STRUCK = {"unification", "unification_leadership", "te_un_mandate_restore_state"}
# Goals only a subject can hold against its overlord; the struck actor is never
# a subject (un_teeth_war_goal_surcharge leaves subjects alone).
SUBJECT_ONLY = {"independence", "increase_autonomy"}


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return _strip(f.read())


def _block(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth, i = 0, m.end() - 1
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    raise AssertionError(f"{name} unbalanced")


def _opening_goals():
    """{play type: the war goal it opens with}, the mod's over vanilla's."""
    with open(os.path.join(REPO, "vanilla_parsed", "common", "diplomatic_plays.json"), encoding="utf-8") as f:
        vanilla = json.load(f)
    plays = {}
    for name, entry in vanilla.items():
        body = entry[1] if isinstance(entry, list) else entry
        if isinstance(body, dict) and "war_goal" in body:
            goal = body["war_goal"]
            plays[name] = goal[1] if isinstance(goal, list) else goal
    for path in sorted(glob.glob(os.path.join(REPO, "common", "diplomatic_plays", "*.txt"))):
        text = _read(path)
        for m in re.finditer(r"^(?:REPLACE:)?(\w+)\s*=\s*\{", text, re.M):
            goal = re.search(r"\bwar_goal\s*=\s*(\w+)", _block(text[m.start():].replace("REPLACE:", "", 1), m.group(1)))
            if goal:
                plays[m.group(1)] = goal.group(1)
    return plays


class PlayTypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plays = _opening_goals()
        cls.by_goal = collections.defaultdict(set)
        for play, goal in cls.plays.items():
            cls.by_goal[goal].add(play)
        triggers = _read(TRIGGERS)
        cls.strikeable = _block(triggers, "un_force_has_strikeable_goal")
        cls.one = re.findall(r"un_force_goal_strikeable = \{ TYPE = (\w+) PLAY = (\w+) \}", cls.strikeable)
        cls.held = set(re.findall(r"un_force_goal_held = \{ TYPE = (\w+) \}", cls.strikeable))
        cls.annexation = set(re.findall(r"is_diplomatic_play_type = (\w+)",
                                        _block(triggers, "un_force_play_opens_with_annexation")))
        cls.humiliation = set(re.findall(r"is_diplomatic_play_type = (\w+)",
                                         _block(triggers, "un_force_play_opens_with_humiliation")))

    def test_the_plays_were_read(self):
        self.assertIn("dp_conquer_state", self.plays)
        self.assertEqual(self.plays["dp_te_un_mandate_restore_state"], "te_un_mandate_restore_state")

    def test_each_single_play_type_opens_with_its_goal_and_is_the_only_one(self):
        for goal, play in self.one:
            with self.subTest(goal=goal):
                self.assertEqual(self.by_goal[goal], {play})

    def test_the_annexation_and_humiliation_lists_are_every_play_that_opens_with_them(self):
        self.assertEqual(self.annexation, self.by_goal["annex_country"])
        self.assertEqual(self.humiliation, self.by_goal["humiliation"])
        self.assertTrue({"annex_country", "humiliation"} <= self.held)

    def test_the_always_struck_goals_open_no_play(self):
        for goal in self.held - {"annex_country", "humiliation"}:
            with self.subTest(goal=goal):
                self.assertEqual(self.by_goal.get(goal, set()), set())

    def test_every_opening_goal_is_classified(self):
        listed = {goal for goal, _ in self.one} | self.held
        for goal in self.by_goal:
            with self.subTest(goal=goal):
                self.assertTrue(goal in listed or goal in NEVER_STRUCK | SUBJECT_ONLY, goal)

    def test_the_effect_strikes_the_same_goals(self):
        effects = _read(EFFECTS)
        one = set(re.findall(r"un_force_strike_goal_type = \{ TYPE = (\w+) PLAY = (\w+) \}", effects))
        self.assertEqual(one, set(self.one))
        held = set(re.findall(r"un_force_strike_goal = \{ TYPE = (\w+) \}", effects))
        self.assertEqual(held, self.held)


if __name__ == "__main__":
    unittest.main()
