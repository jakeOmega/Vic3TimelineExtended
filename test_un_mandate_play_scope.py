# -*- coding: utf-8 -*-
"""A bound UN mandate reaches only the play it is exercised in.

Three things run from ``on_wargoal_added`` for every goal any country adds to
any play, and each must act only in the mandate's own play:

* the AI holder's strike, ``un_mandate_ai_strike_prohibited``
  (common/scripted_effects/un_mandate_effects.txt). It strikes with
  ``remove_war_goal = { who = initiator type = ... }``, which cannot tell one
  goal of a type from another. Ungated, it struck the opening goal of a bound
  AI holder's unrelated play (a ``dp_conquer_state`` against a third country),
  and whether a play survives that is unproven. It runs only in a
  ``dp_te_un_mandate_restore_state`` play against the mandate's target, which
  opens with ``te_un_mandate_restore_state``, never struck; and it strikes a
  type only when the holder holds one against that target.
* the violation check, ``un_mandate_has_prohibited_goal``
  (common/scripted_triggers/un_mandate_triggers.txt). It counted a
  prohibited goal against the target from any play or war; the player is
  told "in that play", and now that is what it counts.
* the war-goal surcharge, ``un_teeth_war_goal_surcharge``
  (common/scripted_effects/un_teeth_effects.txt). It exempted a bound holder
  in every play, so every other war it began went surcharge-free.

The engine checks none of this at load, so these tests pin it.

Run: python3 -m unittest test_un_mandate_play_scope -v
"""

import os
import re
import unittest

from test_un_chamber_mission_slots import _block, _braced, _read, _sub_block

REPO = os.path.dirname(os.path.abspath(__file__))
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_mandate_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "un_mandate_triggers.txt")
TEETH = os.path.join(REPO, "common", "scripted_effects", "un_teeth_effects.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "un_mandate_on_actions.txt")
PLAY = os.path.join(REPO, "common", "diplomatic_plays", "te_un_mandate_play.txt")

MANDATE_PLAY = "dp_te_un_mandate_restore_state"
MANDATE_GOAL = "te_un_mandate_restore_state"

_STRIKE_CALL = re.compile(r"\bun_mandate_strike_goal_type\s*=\s*\{\s*TYPE\s*=\s*(\w+)\s*\}")
_HELD_CALL = re.compile(r"\bun_mandate_prohibited_goal_held\s*=\s*\{\s*TYPE\s*=\s*(\w+)\s+TARGET\s*=\s*\$TARGET\$\s*\}")


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


class StrikeTest(unittest.TestCase):
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
        cls.helper = _block(effects, "un_mandate_strike_goal_type")
        cls.prohibited = _HELD_CALL.findall(_block(_read(TRIGGERS), "un_mandate_has_prohibited_goal"))

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

    def test_a_type_is_struck_only_for_a_goal_against_the_mandates_target(self):
        first_call = self.gated.index("un_mandate_strike_goal_type")
        self.assertRegex(self.gated[:first_call],
                         r"\btarget\s*=\s*\{\s*save_temporary_scope_as\s*=\s*un_mandate_strike_target\s*\}")
        limit = _sub_block(self.helper, "limit")
        self.assertRegex(limit, r"\bhas_play_goal\s*=\s*\$TYPE\$")
        self.assertRegex(limit, r"play_participant_has_war_goal_of_type_against\s*=\s*\{\s*type\s*=\s*\$TYPE\$"
                                r"\s+target\s*=\s*scope:un_mandate_strike_target\s*\}")

    def test_the_mandates_play_opens_with_a_goal_that_is_never_struck(self):
        play = _block(_read(PLAY), MANDATE_PLAY)
        self.assertRegex(play, r"\bwar_goal\s*=\s*" + MANDATE_GOAL + r"\b")
        self.assertNotIn(MANDATE_GOAL, self.struck)

    def test_the_struck_types_are_the_prohibited_types(self):
        self.assertEqual(len(self.struck), len(set(self.struck)), "a type is struck twice")
        self.assertEqual(len(self.prohibited), len(set(self.prohibited)), "a type is prohibited twice")
        self.assertEqual(set(self.struck), set(self.prohibited))

    def test_the_hook_binds_then_strikes_then_checks(self):
        hook = _block(_read(ON_ACTIONS), "un_mandate_on_wargoal_added")
        order = [hook.index(name) for name in (
            "un_mandate_try_bind", "un_mandate_ai_strike_prohibited", "un_mandate_check_prohibited")]
        self.assertEqual(order, sorted(order))


class ViolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        triggers = _read(TRIGGERS)
        cls.prohibited = _block(triggers, "un_mandate_has_prohibited_goal")
        cls.held = _block(triggers, "un_mandate_prohibited_goal_held")
        cls.bound_play = _block(triggers, "un_mandate_is_bound_play_of")

    def test_every_prohibited_type_goes_through_the_play_scoped_read(self):
        self.assertNotRegex(self.prohibited, r"_participant_has_war_goal_of_type_against",
                            "a prohibited type is read across every play and war")
        self.assertTrue(_HELD_CALL.findall(self.prohibited))

    def test_the_goal_is_held_against_the_target_and_carried_by_the_mandates_play(self):
        for form in ("play", "war"):
            with self.subTest(form=form):
                self.assertRegex(self.held, form + r"_participant_has_war_goal_of_type_against\s*=\s*\{\s*"
                                            r"type\s*=\s*\$TYPE\$\s+target\s*=\s*\$TARGET\$\s*\}")
        play = _sub_block(self.held, "any_diplomatic_play")
        self.assertRegex(play, r"\bun_mandate_is_bound_play_of\s*=\s*\{\s*ACTOR\s*=\s*prev\s*\}")
        self.assertRegex(play, r"\bhas_play_goal\s*=\s*\$TYPE\$")

    def test_the_mandates_play_is_the_holders_play_carrying_the_authorized_goal(self):
        self.assertRegex(self.bound_play, r"\bhas_tag\s*=\s*un_mandate_bound\b")
        self.assertRegex(self.bound_play, r"\binitiator\s*\?=\s*\$ACTOR\$")
        self.assertRegex(self.bound_play, r"\btarget\s*\?=\s*\$ACTOR\$")
        self.assertRegex(self.bound_play, r"\bhas_play_goal\s*=\s*" + MANDATE_GOAL + r"\b")


class SurchargeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.surcharge = _block(_read(TEETH), "un_teeth_war_goal_surcharge")
        cls.limit = _sub_block(cls.surcharge, "limit")

    def test_only_the_mandates_own_play_is_exempt(self):
        self.assertRegex(self.limit, r"\bNOT\s*=\s*\{\s*un_mandate_is_bound_play_of\s*=\s*\{\s*ACTOR\s*=\s*scope:actor\s*\}\s*\}")
        self.assertNotIn("un_mandate_current", self.limit,
                         "the surcharge exempts a bound holder outside its mandate's play")


if __name__ == "__main__":
    unittest.main()
