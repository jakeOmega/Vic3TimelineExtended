# -*- coding: utf-8 -*-
"""UN votes: late AI ballots, visible leans and lobbying
(docs/superpowers/specs/2026-09-27-un-vote-lobbying-design.md).

The engine checks none of this at load: a casting gate that lost its
condition, a veto that reads the pledged lean, or a row that passes the wrong
slot number to one of its buttons all load cleanly and misbehave in play.
These tests pin the structure the design depends on.
"""

import os
import re
import unittest

from test_un_chamber_mission_slots import _block, _braced, _read, _sub_block

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


VOTE_EVENTS = _path("events", "un_vote_events.txt")
VOTE_EFFECTS = _path("common", "scripted_effects", "un_vote_effects.txt")
DOSSIER_EFFECTS = _path("common", "scripted_effects", "un_dossier_effects.txt")
DOSSIER_TRIGGERS = _path("common", "scripted_triggers", "un_dossier_triggers.txt")
DOSSIER_VALUES = _path("common", "script_values", "un_dossier_values.txt")
LOBBYING_VALUES = _path("common", "script_values", "un_lobbying_values.txt")

_TOP_LEVEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{", re.M)


def _all_script(*dirs):
    """Every top-level name defined under common/<dir> for each dir."""
    names = set()
    for d in dirs:
        root = _path("common", d)
        for name in os.listdir(root):
            if name.endswith(".txt"):
                names |= set(_TOP_LEVEL.findall(_read(os.path.join(root, name))))
    return names


def _event(name):
    return _block(_read(VOTE_EVENTS), name)


def _options(event_body):
    out = []
    for m in re.finditer(r"^\toption\s*=\s*\{", event_body, re.M):
        out.append(_braced(event_body, m.end() - 1))
    return out


class CastingTimingTest(unittest.TestCase):
    """§1: the AI votes at month 9, 10 or 11, by its lean at that time."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _read(DOSSIER_EFFECTS)
        cls.vote_effects = _read(VOTE_EFFECTS)
        cls.draws = _block(cls.effects, "un_vote_ai_draws")
        cls.vote4 = _sub_block(_event("un_vote.4"), "immediate")

    def test_the_casting_month_is_nine_ten_or_eleven(self):
        months = re.findall(r"name\s*=\s*un_vote_cast_month\s+value\s*=\s*(\d+)", self.draws)
        self.assertEqual(months[:3], ["9", "10", "11"])

    def test_the_misreading_is_minus_ten_nought_or_ten(self):
        found = re.findall(r"name\s*=\s*un_lean_misread\s+value\s*=\s*(-?\d+)", self.draws)
        self.assertEqual(found, ["-10", "0", "10"])

    def test_a_late_draw_is_no_earlier_than_next_month(self):
        self.assertRegex(
            self.draws,
            r"un_vote_cast_month\s*<\s*un_res_next_month[\s\S]*?"
            r"name\s*=\s*un_vote_cast_month\s+value\s*=\s*un_res_next_month",
        )

    def test_the_draw_is_once_per_resolution(self):
        self.assertRegex(self.draws, r"NOT\s*=\s*\{\s*var:un_vote_draw_res\s*\?=\s*scope:un_resolution\s*\}")

    def test_un_vote_4_draws_then_snapshots_then_casts_only_when_due(self):
        body = self.vote4
        draw = body.index("un_vote_ai_draws")
        snap = body.index("un_lean_snapshot")
        cast = body.index("un_vote_ai_cast = yes")
        self.assertLess(draw, snap)
        self.assertLess(snap, cast)
        # The cast sits in an `if` whose limit asks whether its month has come.
        cast_if = body.rfind("if = {", 0, cast)
        limit = _sub_block(body[cast_if:], "limit")
        self.assertIn("un_vote_ai_cast_due = yes", limit)
        self.assertIn("un_vote_can_cast_ballot = yes", limit)
        self.assertIn("is_ai = yes", limit)

    def test_the_cast_is_due_at_its_month_or_at_the_last_call(self):
        due = _block(_read(DOSSIER_TRIGGERS), "un_vote_ai_cast_due")
        self.assertIn("un_res_last_call", due)
        self.assertRegex(due, r"var:un_vote_cast_month\s*<=\s*un_res_months_now")

    def test_nothing_dispatches_ballots_at_day_thirty_any_more(self):
        self.assertNotIn("un_vote_dispatch_ai_ballots", _all_script("scripted_effects"))
        self.assertNotIn("un_vote_dispatch_ai_ballots", _read(VOTE_EVENTS))
        vote5 = _event("un_vote.5")
        self.assertNotIn("un_res_ai_cast", vote5)
        self.assertNotIn("un_vote_ai_cast", vote5)

    def test_opening_sends_every_member_its_lean_and_queues_the_last_call(self):
        opening = _block(self.vote_effects, "un_resolution_open")
        self.assertIn("un_vote_refresh_leans = yes", opening)
        self.assertNotIn("un_vote.5", opening)
        last_call = re.search(r"id\s*=\s*un_vote\.6\s+days\s*=\s*(\d+)", opening)
        decision = re.search(r"id\s*=\s*un_vote\.2\s+days\s*=\s*(\d+)", opening)
        self.assertIsNotNone(last_call)
        self.assertLess(int(last_call.group(1)), int(decision.group(1)))

    def test_the_last_call_marks_the_resolution_and_refreshes_the_ai(self):
        immediate = _sub_block(_event("un_vote.6"), "immediate")
        self.assertIn("set_variable = un_res_last_call", immediate)
        self.assertIn("un_vote_refresh_leans = yes", immediate)

    def test_the_monthly_update_refreshes_every_lean_and_calls_the_last_call_at_twelve(self):
        monthly = _block(self.vote_effects, "un_resolutions_monthly_update")
        self.assertIn("un_vote_refresh_leans = yes", monthly)
        self.assertRegex(monthly, r"var:un_res_months\s*>=\s*12[\s\S]*?set_variable\s*=\s*un_res_last_call")

    def test_the_refresh_reaches_every_member(self):
        refresh = _block(self.effects, "un_vote_refresh_leans")
        self.assertNotIn("is_ai", refresh)
        self.assertIn("trigger_event = { id = un_vote.4 }", refresh)


class VetoBasisTest(unittest.TestCase):
    """§4: a pledge never makes a veto and never prevents one it did not promise away."""

    def test_the_veto_reads_the_lean_without_the_pledge(self):
        veto = _block(_read(DOSSIER_TRIGGERS), "un_vote_ai_should_veto")
        self.assertIn("var:un_lean_veto_basis", veto)
        self.assertNotIn("un_lean_total", veto)

    def test_the_snapshot_writes_the_basis_and_the_shown_lean(self):
        snapshot = _block(_read(DOSSIER_EFFECTS), "un_lean_snapshot")
        self.assertRegex(snapshot, r"name\s*=\s*un_lean_veto_basis\s+value\s*=\s*un_lean_veto_basis_value")
        self.assertRegex(snapshot, r"name\s*=\s*un_lean_shown\s+value\s*=\s*un_lean_shown_value")
        values = _read(LOBBYING_VALUES)
        basis = _block(values, "un_lean_veto_basis_value")
        self.assertIn("var:un_lean_total", basis)
        self.assertIn("subtract = var:un_lean_pledge", basis)
        shown = _block(values, "un_lean_shown_value")
        self.assertIn("add = var:un_lean_misread", shown)


class DecideLaterTest(unittest.TestCase):
    """§2: the human vote event can be put off, and comes back at months 9 and 11."""

    @classmethod
    def setUpClass(cls):
        cls.options = _options(_event("un_vote.1"))
        cls.later = [o for o in cls.options if "un_vote.1.later" in o]

    def test_there_is_one_decide_later_option(self):
        self.assertEqual(len(self.later), 1)

    def test_deciding_later_casts_nothing_and_the_ai_never_takes_it(self):
        later = self.later[0]
        self.assertNotIn("un_vote_cast_", later)
        self.assertRegex(later, r"ai_chance\s*=\s*\{\s*base\s*=\s*0\s*\}")
        self.assertIn("name = un_res_deferred", later)

    def test_the_default_option_is_still_the_vote_in_favour(self):
        defaults = [o for o in self.options if "default_option = yes" in o]
        self.assertEqual(len(defaults), 1)
        self.assertIn("un_vote_cast_yes = yes", defaults[0])

    def test_the_monthly_update_asks_again_at_nine_and_eleven(self):
        monthly = _block(_read(VOTE_EFFECTS), "un_resolutions_monthly_update")
        self.assertRegex(
            monthly,
            r"var:un_res_months\s*=\s*9\s+var:un_res_months\s*=\s*11[\s\S]*?"
            r"variable\s*=\s*un_res_deferred[\s\S]*?trigger_event\s*=\s*\{\s*id\s*=\s*un_vote\.1\s*\}",
        )


if __name__ == "__main__":
    unittest.main()
