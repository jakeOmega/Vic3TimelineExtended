"""Crisis talks: a waiting proposal, and the talks an exercise notice opens (#1230).

Talks are open on the issuer's record in two cases. A proposal to stand down
or to trade awaits an answer (nd_crisis_talks = 1), and only that blocks
another proposal; its answer always clears it. Or an exercise notice opened
them (nuclear_incident.10.a, .12.a), for nd_crisis_notice_talks_weeks_value
weeks that the weekly tick counts down (nd_crisis_talks_weeks).

Before #1230 the notice set nd_crisis_talks = 1 with no proposal behind it, so
nothing ever cleared it: no pressure events, no stand-down and no trade for
the rest of the crisis.
"""

import re
import unittest
from pathlib import Path

from test_nuclear_deterrence import (
    CRISIS_EFFECTS,
    INCIDENT_EVENTS,
    TRIGGERS,
    VALUES,
    block,
    loc_value,
    option_body,
    read,
    strip_comments,
)

ROOT = Path(__file__).resolve().parent
SCRIPT_DIRS = ("common", "events")
SETS_PROPOSAL = re.compile(r"name = nd_crisis_talks value = 1\b")
# The two acts that make a proposal; the answer to each (accept, refuse, or a
# trade gone stale) clears the flag or closes the crisis.
PROPOSAL_ACTS = {"nd_crisis_act_propose_talks", "nd_crisis_act_offer_trade"}


def top_level_owner(text, pos):
    """The name of the top-level `name = {` definition that encloses pos."""
    owner = None
    for m in re.finditer(r"(?m)^([\w.]+)\s*=\s*\{", text):
        if m.start() > pos:
            break
        owner = m.group(1)
    return owner


def squash(text):
    return " ".join(text.split())


class TestOnlyProposalsSetTheFlag(unittest.TestCase):
    def test_only_a_proposal_sets_nd_crisis_talks(self):
        writers = set()
        for d in SCRIPT_DIRS:
            for path in sorted((ROOT / d).rglob("*.txt")):
                text = strip_comments(read(path))
                for m in SETS_PROPOSAL.finditer(text):
                    writers.add(top_level_owner(text, m.start()))
        self.assertEqual(writers, PROPOSAL_ACTS,
                         "nd_crisis_talks = 1 means a proposal awaits an answer; anything else that "
                         "opens talks sets nd_crisis_talks_weeks, or nothing clears the flag (#1230)")


class TestNoticeTalks(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.triggers = strip_comments(read(TRIGGERS))
        self.values = strip_comments(read(VALUES))
        self.incidents = strip_comments(read(INCIDENT_EVENTS))

    def test_notices_open_timed_talks(self):
        notice = "set_variable = { name = nd_crisis_talks_weeks value = nd_crisis_notice_talks_weeks_value }"
        for option in ("nuclear_incident.10.a", "nuclear_incident.12.a"):
            body = option_body(self.incidents, option)
            self.assertIn(notice, body, option)
            self.assertNotIn("name = nd_crisis_talks value", body, option)

    def test_target_invites_only_while_talks_are_closed(self):
        body = option_body(self.incidents, "nuclear_incident.10.a")
        invite = body[:body.index("EVENT = nuclear_incident.12")]
        self.assertIn("nd_crisis_talks_open = no", invite[invite.rindex("else_if"):])

    def test_six_weeks_and_the_tooltips_say_so(self):
        self.assertRegex(self.values, r"(?m)^nd_crisis_notice_talks_weeks_value = 6\b")
        for key in ("nd_tt_exercise_notified", "nd_tt_exercise_invitation_accepted"):
            self.assertIn("#v 6#! weeks", loc_value(key), key)

    def test_weekly_tick_counts_them_down(self):
        tick = block(self.effects, "nd_crisis_weekly_tick")
        countdown = squash(tick[tick.index("change_variable = { name = nd_crisis_talks_weeks"):])
        self.assertTrue(countdown.startswith(
            "change_variable = { name = nd_crisis_talks_weeks subtract = 1 } "
            "if = { limit = { var:nd_crisis_talks_weeks <= 0 } remove_variable = nd_crisis_talks_weeks }"))
        # The countdown runs before the pressure gate reads it, in the same tick.
        self.assertLess(tick.index("nd_crisis_talks_weeks subtract = 1"), tick.index("EVENT = nuclear_crisis.5"))

    def test_pressure_waits_for_either_kind_of_talks(self):
        tick = block(self.effects, "nd_crisis_weekly_tick")
        gate = tick[tick.rindex("else_if", 0, tick.index("EVENT = nuclear_crisis.5")):]
        self.assertIn("nd_crisis_talks_open = no", block(gate, "limit"))
        self.assertNotRegex(tick, r"var:nd_crisis_talks\b")

    def test_open_talks_read_both(self):
        body = squash(block(self.triggers, "nd_crisis_talks_open"))
        self.assertIn("has_variable = nd_crisis_talks var:nd_crisis_talks = 1", body)
        self.assertIn("has_variable = nd_crisis_talks_weeks var:nd_crisis_talks_weeks > 0", body)
        either = squash(block(self.triggers, "nd_crisis_talks_open_either"))
        self.assertEqual(either.count("nd_crisis_talks_open = yes"), 2)
        self.assertNotRegex(either, r"var:nd_crisis_talks\b")
        self.assertIn("nd_crisis_talks_open = yes", block(self.values, "nd_cd_talks_value"))

    def test_notice_talks_leave_proposals_open(self):
        self.assertNotIn("nd_crisis_talks_weeks", block(self.triggers, "nd_crisis_no_proposal_pending"))

    def test_a_refusal_or_a_lapse_closes_them(self):
        refused = squash(block(block(self.effects, "nd_crisis_talks_refused"), "hidden_effect"))
        lapse = squash(block(self.effects, "nd_crisis_act_accept_trade"))
        lapse = lapse[lapse.rindex("else_if"):]
        for name, body in (("refusal", refused), ("lapse", lapse)):
            self.assertIn("set_variable = { name = nd_crisis_talks value = 0 }", body, name)
            self.assertIn("if = { limit = { has_variable = nd_crisis_talks_weeks } "
                          "remove_variable = nd_crisis_talks_weeks }", body, name)

    def test_cleared_with_the_record(self):
        self.assertIn("remove_variable = nd_crisis_talks_weeks", block(self.effects, "nd_crisis_clear_vars"))

    def test_world_crises_name_notice_talks(self):
        body = squash(block(self.effects, "nd_world_crisis_detail_lines"))
        self.assertIn("else_if = { limit = { nd_crisis_talks_open = yes } "
                      "custom_tooltip_no_bullet = nd_wc_detail_talks_notice }", body)
        self.assertIn("exercise", loc_value("nd_wc_detail_talks_notice"))


if __name__ == "__main__":
    unittest.main()
