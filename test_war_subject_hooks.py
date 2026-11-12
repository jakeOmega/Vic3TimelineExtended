# -*- coding: utf-8 -*-
"""1.15 war and subject hooks (#1449, #1455, #287).

The engine accepts a trigger that is never read and an on-action that is never
wired without a word, so where each hook is read is pinned here:
war_is_in_stalemate (World War .31, the UN ceasefire AI, a decolonization
war's AI talks), the subject reads (is_subject_of_and_not_being_freed,
can_start_play_against_overlord, leave_plays_supporting), and the covert AI's
step-down on weeks_until_bankruptcy. Docs: mod_systems/war.md,
mod_systems/decolonization.md, mod_systems/covert_warfare.md.
"""

import os
import re
import unittest

from test_decolonization_wars import _block, _def, _loc_keys, _read

WW = _read("events", "world_war_events.txt")
DECOL_EVENTS = _read("events", "decolonization_events.txt")
UN_VALUES = _read("common", "script_values", "un_order_values.txt")
UN_TRIGGERS = _read("common", "scripted_triggers", "un_order_triggers.txt")
WAR_EFFECTS = _read("common", "scripted_effects", "decolonization_war_effects.txt")
DECOL = _read("common", "scripted_effects", "decolonization.txt")
PLAY = _read("common", "diplomatic_plays", "te_colonial_war_play.txt")
ON_ACTIONS = _read("common", "on_actions", "extra_on_actions.txt")
COVERT_JE = _read("common", "journal_entries", "je_covert_warfare.txt")
COVERT_VALUES = _read("common", "script_values", "covert_warfare_script_values.txt")


class StalemateTests(unittest.TestCase):
    def test_the_world_war_stalemate_reads_the_engine_first(self):
        event = _def(WW, "world_war_events.31")
        war = _block(_block(event, "trigger"), "any_scope_war")
        self.assertIn("war_is_in_stalemate = yes", _block(war, "OR"))
        # The 1.14 reads stay as the fallback.
        self.assertIn("has_stalled_wargoal_held_by = ROOT", _block(war, "AND"))
        immediate = _block(event, "immediate")
        first = _block(immediate, "random_scope_war")
        self.assertIn("war_is_in_stalemate = yes", first)

    def test_the_un_ceasefire_weighs_a_stalemate_up(self):
        for value in ("un_lean_interests_ceasefire", "un_ceasefire_ai_chance"):
            with self.subTest(value=value):
                self.assertIn("war_is_in_stalemate = yes", _def(UN_VALUES, value))

    def test_a_stalled_war_of_independence_opens_ai_talks(self):
        call = WAR_EFFECTS.index("decol_iw_open_talks = { N = $N$ }")
        talks = WAR_EFFECTS[WAR_EFFECTS.rindex("is_ai = yes", 0, call):call]
        self.assertIn("war_is_in_stalemate = yes", talks)

    def test_late_entry_weighs_connecting_the_theaters(self):
        event = _def(WW, "world_war_events.20")
        join = event[event.index("name = world_war_events.20.a"):event.index("name = world_war_events.20.b")]
        self.assertIn("connects_important_war_theaters = ROOT", _block(join, "ai_chance"))

    def test_reconstruction_aid_reads_devastation(self):
        event = _def(WW, "world_war_events.102")
        for option in ("a", "b"):
            with self.subTest(option=option):
                start = event.index(f"name = world_war_events.102.{option}")
                self.assertIn("average_devastation", _block(event[start:], "ai_chance"))


class SubjectTests(unittest.TestCase):
    def test_a_subject_being_freed_is_not_picked(self):
        self.assertIn("is_subject_of_and_not_being_freed = overlord",
                      _def(UN_TRIGGERS, "un_referendum_subject_eligible"))
        for event, saved in (("decolonization_events.1", "restless_subject"),
                             ("decolonization_events.3", "rebellious_subject")):
            body = _def(DECOL_EVENTS, event)
            with self.subTest(event=event):
                self.assertIn("is_subject_of_and_not_being_freed = overlord",
                              _block(_block(body, "trigger"), "any_subject_or_below"))
                pick = _block(_block(body, "immediate"), "random_subject_or_below")
                self.assertIn("is_subject_of_and_not_being_freed = overlord", pick)
                self.assertIn(f"save_scope_as = {saved}", pick)

    def test_holding_the_line_opens_a_real_independence_play(self):
        event = _def(DECOL_EVENTS, "decolonization_events.3")
        hold = event[event.index("name = decolonization_events.3.b"):event.index("name = decolonization_events.3.c")]
        self.assertIn("can_start_play_against_overlord = yes", hold)
        self.assertIn("is_direct_subject_of = root", hold)
        create = _block(hold, "create_diplomatic_play")
        self.assertIn("type = dp_te_colonial_uprising", create)
        self.assertIn("target_country = root", create)
        self.assertIn("decolonization_events.3.b_uprising_tt", hold)
        self.assertIn("TE_SELF_CHECK OK decol_uprising_play", _raw_events())

    def test_the_uprising_play_is_script_only_independence(self):
        play = _def(PLAY, "dp_te_colonial_uprising")
        self.assertIn("war_goal = independence", play)
        self.assertIn("selectable_in_lens = { always = no }", play)
        self.assertIn("is_direct_subject_of = scope:target_country", _block(play, "possible"))
        keys = _loc_keys()
        for key in ("dp_te_colonial_uprising", "dp_te_colonial_uprising_desc",
                    "decolonization_events.3.b_uprising_tt"):
            with self.subTest(key=key):
                self.assertIn(key, keys)

    def test_independence_leaves_the_former_overlords_wars(self):
        self.assertIn("decol_leave_overlord_plays_on_action",
                      _block(_def(ON_ACTIONS, "on_become_independent"), "on_actions"))
        self.assertIn("decol_leave_former_overlord_plays = yes",
                      _def(ON_ACTIONS, "decol_leave_overlord_plays_on_action"))
        effect = _def(DECOL, "decol_leave_former_overlord_plays")
        self.assertIn("leave_plays_supporting = scope:decol_freed_from", effect)
        self.assertIn("is_subject = no", _block(effect, "limit"))

    def test_every_freeing_sets_the_former_overlord_first(self):
        # The on-action reads var:former_overlord, so each make_independent in
        # the decolonization events comes straight after decol_mark_former_colony.
        lines = [line.strip() for line in DECOL_EVENTS.splitlines() if line.strip()]
        for i, line in enumerate(lines):
            if line == "make_independent = yes":
                with self.subTest(at=i):
                    self.assertTrue(lines[i - 1].startswith("decol_mark_former_colony"), lines[i - 1])


class CovertFundingTests(unittest.TestCase):
    def test_the_ai_steps_down_before_bankruptcy(self):
        start = COVERT_JE.index("has_modifier = declared_bankruptcy")
        body = COVERT_JE[start:COVERT_JE.index("country_rank >= rank_value:major_power", start)]
        self.assertIn("weeks_until_bankruptcy < iw_ai_funding_bankruptcy_weeks", body)
        # Read behind taking_loans, as vanilla does: the figure means nothing in surplus.
        self.assertIn("taking_loans = yes", body)
        self.assertRegex(COVERT_VALUES, r"(?m)^iw_ai_funding_bankruptcy_weeks = \d+$")


def _raw_events():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "events", "decolonization_events.txt"),
              encoding="utf-8-sig") as f:
        return f.read()


if __name__ == "__main__":
    unittest.main()
