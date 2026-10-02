# -*- coding: utf-8 -*-
"""The AI mandate holder's war-goal strike stays in the mandate's own play.

``un_mandate_ai_strike_prohibited`` (common/scripted_effects/
un_mandate_effects.txt) runs from ``on_wargoal_added`` for every goal any
country adds to any play, and strikes the goal types a mandate prohibits with
``remove_war_goal = { who = initiator type = ... }``, which cannot tell one goal
of a type from another. Ungated, it struck the opening goal of a bound AI
holder's unrelated play (a ``dp_conquer_state`` against a third country), and
whether a play survives losing its opening goal is unproven. The gate limits
it to a ``dp_te_un_mandate_restore_state`` play against the mandate's target;
that play opens with ``te_un_mandate_restore_state``, which is never struck.
The engine checks none of this at load, so these tests pin it.

Run: python3 -m unittest test_un_mandate_strike -v
"""

import os
import re
import unittest

from test_un_chamber_mission_slots import _block, _braced, _read, _sub_block

REPO = os.path.dirname(os.path.abspath(__file__))
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_mandate_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "un_mandate_triggers.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "un_mandate_on_actions.txt")
PLAY = os.path.join(REPO, "common", "diplomatic_plays", "te_un_mandate_play.txt")

MANDATE_PLAY = "dp_te_un_mandate_restore_state"
MANDATE_GOAL = "te_un_mandate_restore_state"

_STRIKE_CALL = re.compile(r"\bun_mandate_strike_goal_type\s*=\s*\{\s*TYPE\s*=\s*(\w+)\s*\}")


def _top_level_keys(body):
    """``[(key, start)]`` for each ``key = {`` at the top level of ``body``."""
    keys, depth = [], 0
    for m in re.finditer(r"(\w+)\s*=\s*\{|\{|\}", body):
        if m.group(1) and depth == 0:
            keys.append((m.group(1), m.start()))
        if m.group(0).endswith("{"):
            depth += 1
        else:
            depth -= 1
    return keys


class MandateStrikeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        effects = _read(EFFECTS)
        cls.effects = effects
        cls.strike = _block(effects, "un_mandate_ai_strike_prohibited")
        top = _top_level_keys(cls.strike)
        if [k for k, _ in top] != ["if"]:
            raise AssertionError(f"un_mandate_ai_strike_prohibited should be one gated if, not {top}")
        cls.gated = _braced(cls.strike, top[0][1])
        cls.limit = _sub_block(cls.gated, "limit")
        cls.struck = _STRIKE_CALL.findall(cls.gated)
        prohibited = _block(_read(TRIGGERS), "un_mandate_has_prohibited_goal")
        cls.prohibited_play = re.findall(
            r"play_participant_has_war_goal_of_type_against\s*=\s*\{\s*type\s*=\s*(\w+)", prohibited)
        cls.prohibited_war = re.findall(
            r"war_participant_has_war_goal_of_type_against\s*=\s*\{\s*type\s*=\s*(\w+)", prohibited)

    def test_the_strike_runs_only_in_the_mandates_own_play(self):
        self.assertRegex(self.limit, r"\bis_diplomatic_play_type\s*=\s*" + MANDATE_PLAY + r"\b")
        self.assertRegex(self.limit, r"\btarget\s*\?=\s*scope:actor\.var:un_mandate_current\.var:un_mnd_target\b")

    def test_the_strike_is_for_a_bound_ai_initiator(self):
        self.assertRegex(self.limit, r"\binitiator\s*\?=\s*scope:actor\b")
        self.assertRegex(self.limit, r"\bis_ai\s*=\s*yes\b")
        self.assertRegex(self.limit, r"\bhas_tag\s*=\s*un_mandate_bound\b")

    def test_every_strike_is_behind_the_gate(self):
        outside = self.effects.replace(self.gated, "")
        self.assertEqual(_STRIKE_CALL.findall(outside), [],
                         "un_mandate_strike_goal_type is called outside the gated strike")
        self.assertTrue(self.struck)

    def test_the_mandates_play_opens_with_a_goal_that_is_never_struck(self):
        play = _block(_read(PLAY), MANDATE_PLAY)
        self.assertRegex(play, r"\bwar_goal\s*=\s*" + MANDATE_GOAL + r"\b")
        self.assertNotIn(MANDATE_GOAL, self.struck)

    def test_the_struck_types_are_the_prohibited_types(self):
        self.assertEqual(len(self.struck), len(set(self.struck)), "a type is struck twice")
        self.assertEqual(set(self.struck), set(self.prohibited_play))
        self.assertEqual(set(self.prohibited_play), set(self.prohibited_war))

    def test_the_hook_binds_then_strikes_then_checks(self):
        hook = _block(_read(ON_ACTIONS), "un_mandate_on_wargoal_added")
        order = [hook.index(name) for name in (
            "un_mandate_try_bind", "un_mandate_ai_strike_prohibited", "un_mandate_check_prohibited")]
        self.assertEqual(order, sorted(order))


if __name__ == "__main__":
    unittest.main()
