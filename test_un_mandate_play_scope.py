# -*- coding: utf-8 -*-
"""A bound UN mandate reaches only the play it is exercised in.

Three things run from ``on_wargoal_added`` for every goal any country adds to
any play, and each must act only in the mandate's own play:

* the AI holder's strike, ``un_mandate_ai_strike_prohibited``
  (common/scripted_effects/un_mandate_effects.txt). It strikes with
  ``remove_war_goal = { who = scope:actor type = ... }``, which takes the
  holder's first goal of the type, whatever it targets. Ungated, it struck the
  opening goal of a bound AI holder's unrelated play (a ``dp_conquer_state``
  against a third country). It runs only in a
  ``dp_te_un_mandate_restore_state`` play against the mandate's target, which
  opens with ``te_un_mandate_restore_state``, never struck; it strikes a type
  only when the holder holds one against that target; and it repeats the call
  while one is left (#1892: one call took an older, allowed goal of the type
  and left the prohibited one).
* the violation check, ``un_mandate_has_prohibited_goal``
  (common/scripted_triggers/un_mandate_triggers.txt). It counted a
  prohibited goal against the target from any play or war; the player is
  told "in that play", and now that is what it counts. A goal to take one of
  the target's subjects (``transfer_subject``, ``targets_enemy_subject``)
  targets the subject, not the target, so the check and the strike read that
  type against each of the target's direct subjects too (#1899).
* the war-goal surcharge, ``un_teeth_war_goal_surcharge``
  (common/scripted_effects/un_teeth_effects.txt). It exempted a bound holder
  in every play, so every other war it began went surcharge-free.

Two monthly readers excused a bound holder's every war the same way, and now
excuse only the mandate's own (``un_mandate_is_other_war_of``):

* the UN record's war detector in ``un_dossier_monthly_update``
  (common/scripted_effects/un_dossier_effects.txt);
* the docket's war item, ``un_docket_war_candidate`` and
  ``un_docket_war_victim`` (common/scripted_triggers/un_docket_triggers.txt).

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
DOSSIER = os.path.join(REPO, "common", "scripted_effects", "un_dossier_effects.txt")
DOCKET = os.path.join(REPO, "common", "scripted_triggers", "un_docket_triggers.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "un_mandate_on_actions.txt")
PLAY = os.path.join(REPO, "common", "diplomatic_plays", "te_un_mandate_play.txt")

MANDATE_PLAY = "dp_te_un_mandate_restore_state"
MANDATE_GOAL = "te_un_mandate_restore_state"

_STRIKE_CALL = re.compile(r"\bun_mandate_strike_goal_type\s*=\s*\{\s*TYPE\s*=\s*(\w+)\s*\}")
_HELD_CALL = re.compile(r"\bun_mandate_prohibited_goal_held\s*=\s*\{\s*TYPE\s*=\s*(\w+)\s+TARGET\s*=\s*\$TARGET\$\s*\}")
_SUBJECT_STRIKE_CALL = re.compile(r"\bun_mandate_strike_subject_goal_type\s*=\s*\{\s*TYPE\s*=\s*(\w+)\s*\}")
_SUBJECT_HELD_CALL = re.compile(
    r"\bun_mandate_prohibited_goal_on_subject_held\s*=\s*\{\s*TYPE\s*=\s*(\w+)\s+TARGET\s*=\s*\$TARGET\$\s*\}")

# The war goal types whose definition carries targets_enemy_subject (vanilla's
# common/war_goal_types/; none of the mod's): their goal targets the subject,
# not its overlord. liberate_subject takes nothing for the holder, so it is not
# prohibited.
SUBJECT_GOAL_TYPES = {"liberate_subject", "transfer_subject"}


def _squash(text):
    return re.sub(r"\s+", " ", text)


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
        cls.subject_helper = _block(effects, "un_mandate_strike_subject_goal_type")
        cls.struck_on_subject = _SUBJECT_STRIKE_CALL.findall(cls.gated)
        has_prohibited = _block(_read(TRIGGERS), "un_mandate_has_prohibited_goal")
        cls.prohibited = _HELD_CALL.findall(has_prohibited)
        cls.prohibited_on_subject = _SUBJECT_HELD_CALL.findall(has_prohibited)

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
        self.assertEqual(_SUBJECT_STRIKE_CALL.findall(outside), [],
                         "un_mandate_strike_subject_goal_type is called outside the gated strike")
        self.assertTrue(self.struck)

    def test_a_type_is_struck_only_for_a_goal_against_the_mandates_target(self):
        first_call = self.gated.index("un_mandate_strike_goal_type")
        self.assertRegex(self.gated[:first_call],
                         r"\btarget\s*=\s*\{\s*save_temporary_scope_as\s*=\s*un_mandate_strike_target\s*\}")
        limit = _sub_block(self.helper, "limit")
        self.assertRegex(limit, r"\bhas_play_goal\s*=\s*\$TYPE\$")
        self.assertRegex(limit, r"play_participant_has_war_goal_of_type_against\s*=\s*\{\s*type\s*=\s*\$TYPE\$"
                                r"\s+target\s*=\s*scope:un_mandate_strike_target\s*\}")

    def test_the_strike_repeats_while_a_goal_against_the_target_is_left(self):
        # remove_war_goal takes the holder's first goal of the type, whatever it
        # targets: one call took an allowed goal against the target's ally and
        # left the prohibited one (#1892).
        helper = _squash(self.helper)
        held = ("scope:actor = { play_participant_has_war_goal_of_type_against = "
                "{ type = $TYPE$ target = scope:un_mandate_strike_target } }")
        self.assertIn("while = { count = 30 if = { limit = { " + held + " } "
                      "remove_war_goal = { who = scope:actor type = $TYPE$ }", helper)
        self.assertEqual(helper.count("remove_war_goal"), 1, "a call outside the loop")

    def test_the_loop_is_counted_for_the_self_check(self):
        helper = _squash(self.helper)
        order = [helper.index(x) for x in (
            "scope:actor = { set_variable = { name = un_strike_chk_calls value = 0 } }",
            "while = {",
            "remove_war_goal",
            "scope:actor = { change_variable = { name = un_strike_chk_calls add = 1 } }",
            "un_strike_goals_self_check = { STRIKE = mandate TYPE = $TYPE$ TARGET = scope:un_mandate_strike_target }")]
        self.assertEqual(order, sorted(order))

    def test_the_mandates_play_opens_with_a_goal_that_is_never_struck(self):
        play = _block(_read(PLAY), MANDATE_PLAY)
        self.assertRegex(play, r"\bwar_goal\s*=\s*" + MANDATE_GOAL + r"\b")
        self.assertNotIn(MANDATE_GOAL, self.struck)

    def test_the_struck_types_are_the_prohibited_types(self):
        self.assertEqual(len(self.struck), len(set(self.struck)), "a type is struck twice")
        self.assertEqual(len(self.prohibited), len(set(self.prohibited)), "a type is prohibited twice")
        self.assertEqual(set(self.struck), set(self.prohibited))
        self.assertEqual(len(self.struck_on_subject), len(set(self.struck_on_subject)))
        self.assertEqual(set(self.struck_on_subject), set(self.prohibited_on_subject))

    def test_a_prohibited_subject_goal_is_read_on_the_targets_subjects(self):
        # A goal to take one of the target's subjects targets the subject, so
        # a read against the target alone lets it through (#1899). Both reads
        # stay until TE_SELF_CHECK nd_play_subject_goal says how a play reads it.
        expected = SUBJECT_GOAL_TYPES & set(self.prohibited)
        self.assertIn("transfer_subject", expected)
        self.assertEqual(set(self.prohibited_on_subject), expected)
        self.assertEqual(set(self.struck_on_subject), expected)

    def test_the_subject_strike_points_the_strike_at_each_subject_then_back(self):
        helper = _squash(self.subject_helper)
        self.assertIn("save_temporary_scope_as = un_mandate_strike_play "
                      "scope:un_mandate_strike_target = { save_temporary_scope_as = un_mandate_strike_overlord } "
                      "scope:un_mandate_strike_overlord = { every_direct_subject = { "
                      "save_temporary_scope_as = un_mandate_strike_target "
                      "scope:un_mandate_strike_play = { un_mandate_strike_goal_type = { TYPE = $TYPE$ } } } }",
                      helper)
        # The types struck after it read the mandate's target again.
        self.assertTrue(helper.rstrip().endswith(
            "scope:un_mandate_strike_overlord = { save_temporary_scope_as = un_mandate_strike_target }"))

    def test_the_hook_binds_then_strikes_then_checks(self):
        hook = _block(_read(ON_ACTIONS), "un_mandate_on_wargoal_added")
        order = [hook.index(name) for name in (
            "un_mandate_try_bind", "un_mandate_ai_strike_prohibited", "un_mandate_check_prohibited")]
        self.assertEqual(order, sorted(order))


class StrikeSelfCheckTest(unittest.TestCase):
    """``un_strike_goals_self_check``, after the mandate's and the Standing UN
    Force's strike loops: once a game for each, whether the holder's play test
    saw each removal at once. The verdict reads the play test again after the
    loop: the Force's loop also stops when ``has_play_goal`` goes false, so the
    count alone could read OK either way (review of #1897)."""

    @classmethod
    def setUpClass(cls):
        cls.check = _squash(_block(_read(EFFECTS), "un_strike_goals_self_check"))

    def test_once_a_game_for_each_kind(self):
        self.assertIn("if = { limit = { NOT = { has_global_variable = un_strike_goals_self_check_done_$STRIKE$ } } "
                      "set_global_variable = un_strike_goals_self_check_done_$STRIKE$", self.check)

    def test_ok_below_the_cap_broken_at_it(self):
        self.assertIn("if = { limit = { un_strike_goals_loop_clean = { TYPE = $TYPE$ TARGET = $TARGET$ } } "
                      "debug_log = \"TE_SELF_CHECK OK un_strike_goals:", self.check)
        self.assertIn("else = { debug_log = \"TE_SELF_CHECK BROKEN un_strike_goals:", self.check)
        for verdict in ("OK", "BROKEN"):
            with self.subTest(verdict=verdict):
                line = self.check[self.check.index("TE_SELF_CHECK " + verdict):]
                line = line[:line.index('"')]
                for field in ("strike=$STRIKE$", "type=$TYPE$",
                              "calls=[THIS.Var('un_strike_chk_calls').GetValue|0]"):
                    self.assertIn(field, line)

    def test_clean_means_no_goal_left_by_the_play_test_and_below_the_cap(self):
        clean = _squash(_block(_read(TRIGGERS), "un_strike_goals_loop_clean"))
        self.assertEqual(clean.strip(), "var:un_strike_chk_calls < 30 NOT = { "
                         "play_participant_has_war_goal_of_type_against = { type = $TYPE$ target = $TARGET$ } }")

    def test_the_count_goes_whether_or_not_the_check_reads(self):
        self.assertTrue(self.check.rstrip().endswith("remove_variable = un_strike_chk_calls }"),
                        "the count must be dropped after the once-a-game branch, not inside it")

    def test_the_play_test_list_names_it(self):
        with open(os.path.join(REPO, "docs", "testing", "un-tooltips-playtest.md"), encoding="utf-8") as f:
            self.assertIn("TE_SELF_CHECK OK\\|BROKEN un_strike_goals", f.read())


class ViolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        triggers = _read(TRIGGERS)
        cls.prohibited = _block(triggers, "un_mandate_has_prohibited_goal")
        cls.held = _block(triggers, "un_mandate_prohibited_goal_held")
        cls.on_subject = _block(triggers, "un_mandate_prohibited_goal_on_subject_held")
        cls.bound_play = _block(triggers, "un_mandate_is_bound_play_of")

    def test_the_subject_read_is_the_play_scoped_read_against_each_subject(self):
        self.assertIn("save_temporary_scope_as = un_mpg_holder_t $TARGET$ = { any_direct_subject = { "
                      "save_temporary_scope_as = un_mpg_subject_t scope:un_mpg_holder_t = { "
                      "un_mandate_prohibited_goal_held = { TYPE = $TYPE$ TARGET = scope:un_mpg_subject_t } } } }",
                      _squash(self.on_subject))
        self.assertNotRegex(self.on_subject, r"_participant_has_war_goal_of_type_against")

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


class OtherWarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        triggers = _read(TRIGGERS)
        cls.other_war = _block(triggers, "un_mandate_is_other_war_of")
        cls.began = _block(triggers, "un_mandate_began_other_war")

    def test_a_war_it_began_that_is_not_its_mandates(self):
        self.assertRegex(self.other_war, r"\binitiator\s*\?=\s*\$AGGRESSOR\$")
        self.assertRegex(self.other_war, r"\bis_war\s*=\s*yes\b")
        self.assertRegex(self.other_war, r"\bNOT\s*=\s*\{\s*un_mandate_is_bound_play_of\s*=\s*\{\s*ACTOR\s*=\s*\$AGGRESSOR\$\s*\}\s*\}")
        play = _sub_block(self.began, "any_diplomatic_play")
        self.assertRegex(play, r"\bun_mandate_is_other_war_of\s*=\s*\{\s*AGGRESSOR\s*=\s*prev\s*\}")


class DossierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.update = _block(_read(DOSSIER), "un_dossier_monthly_update")

    def test_the_mandates_war_alone_is_logged_unrecorded(self):
        first = re.search(r"limit\s*=\s*\{\s*var:un_mandate_current\s*\?=\s*\{\s*has_tag\s*=\s*un_mandate_bound\s*\}"
                          r"\s*NOT\s*=\s*\{\s*un_mandate_began_other_war\s*=\s*yes\s*\}\s*\}\s*set_variable\s*=\s*un_dos_war_mandate_only",
                          self.update)
        self.assertIsNotNone(first, "a bound holder's every war is still excused")

    def test_a_war_begun_beside_it_is_recorded(self):
        later = _sub_block(self.update, "else_if")
        self.assertRegex(later, r"\bun_mandate_began_other_war\s*=\s*yes\b")
        self.assertRegex(later, r"\bremove_variable\s*=\s*un_dos_war_mandate_only\b")
        self.assertRegex(later, r"un_dossier_record\s*=\s*\{\s*RECORD\s*=\s*aggression\b")

    def test_peace_clears_the_marker_with_the_flag(self):
        clear = re.search(r"remove_variable\s*=\s*un_dos_war_logged\s*remove_variable\s*=\s*un_dos_war_mandate_only", self.update)
        self.assertIsNotNone(clear)


class DocketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        docket = _read(DOCKET)
        cls.candidate = _block(docket, "un_docket_war_candidate")
        cls.victim = _block(docket, "un_docket_war_victim")

    def test_a_holder_is_taken_up_only_for_another_war_it_began(self):
        play = _sub_block(self.candidate, "any_diplomatic_play")
        self.assertRegex(play, r"\bun_mandate_is_other_war_of\s*=\s*\{\s*AGGRESSOR\s*=\s*prev\s*\}")
        self.assertRegex(play, r"\btarget\s*\?=\s*\{\s*un_docket_war_victim_standing\s*=\s*yes\s*\}")
        country = _sub_block(self.candidate, "AND")
        self.assertRegex(country, r"\bNOT\s*=\s*\{\s*var:un_mandate_current\s*\?=\s*\{\s*has_tag\s*=\s*un_mandate_bound\s*\}\s*\}")
        self.assertRegex(country, r"\bany_country\s*=\s*\{")

    def test_the_victim_named_is_that_wars_target(self):
        play = _sub_block(self.victim, "any_diplomatic_play")
        self.assertRegex(play, r"\btarget\s*\?=\s*prev\b")
        self.assertRegex(play, r"\bun_mandate_is_other_war_of\s*=\s*\{\s*AGGRESSOR\s*=\s*scope:condemned_country\s*\}")


if __name__ == "__main__":
    unittest.main()
