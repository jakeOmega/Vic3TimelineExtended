"""A crisis's High Alert is offered back when the crisis ends, and a long one is flagged.

A hold at a crisis's deadline puts the forces on High Alert and a
counter-threat on Heightened. Before 2026-11-19 nothing took them off once
the crisis was over, and only the Nuclear tab showed the level: a player
left on High Alert for two years, at strain 100, met four false warnings in
six weeks of a war with an armed power. Two fixes, each pinned here:

- Each side's ordered readiness is recorded when the crisis opens, and the
  outcome notice (nuclear_crisis.6) offers to stand back down to it.
- Six months at High Alert with no crisis under way posts one notice to a
  human player, re-armed when a crisis or a readiness step restarts the count.

Run: python3 -m unittest test_nuclear_alert_standdown -v
"""

import re
import unittest
from pathlib import Path

from test_nuclear_deterrence import block, loc_value, read, strip_comments

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
CRISIS_EFFECTS = ROOT / "common/scripted_effects/nuclear_crisis_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
CRISIS_EVENTS = ROOT / "events/nuclear_crisis_events.txt"
MESSAGES = ROOT / "common/messages/extra_messages.txt"


def options(event_body):
    """Each `option = { … }` body of an event, in order."""
    found = []
    for m in re.finditer(r"(?m)^\toption = \{", event_body):
        found.append(block(event_body[m.start():], "option"))
    return found


class TestRecordAtOpen(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_both_sides_recorded_before_anything_moves_readiness(self):
        body = block(self.effects, "nd_crisis_open")
        issuer = body.index("\tnd_record_pre_crisis_readiness = yes")
        target = body.index("scope:nd_target = { nd_record_pre_crisis_readiness = yes }")
        # The AIs' posture review at the open may raise readiness itself.
        review = body.index("scope:nd_issuer = { nd_crisis_ai_review = yes }")
        self.assertLess(issuer, review)
        self.assertLess(target, review)

    def test_record_is_the_ordered_level_and_a_stale_one_is_dropped(self):
        body = block(self.effects, "nd_record_pre_crisis_readiness")
        self.assertIn("set_variable = { name = nd_pre_crisis_readiness value = var:nd_readiness_target }", body)
        self.assertIn("remove_variable = nd_pre_crisis_readiness", body)

    def test_fallback_is_routine(self):
        body = block(strip_comments(read(VALUES)), "nd_pre_crisis_readiness_value")
        self.assertRegex(body, r"^\s*value = 1\b")
        self.assertIn("value = var:nd_pre_crisis_readiness", body)


class TestOutcomeNoticeStandDown(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.triggers = strip_comments(read(TRIGGERS))
        self.notice = block(strip_comments(read(CRISIS_EVENTS)), "nuclear_crisis.6")
        self.keep, self.stand_down = options(self.notice)

    def test_offer_compares_the_ordered_level_with_the_record(self):
        body = block(self.triggers, "nd_crisis_notice_offers_standdown")
        self.assertIn("nd_is_armed = yes", body)
        # A notice left open into a second crisis loses the option.
        self.assertIn("nd_in_crisis = no", body)
        self.assertIn("var:nd_readiness_target > nd_pre_crisis_readiness_value", body)

    def test_crisis_records_are_cleared_before_the_notices_fire(self):
        # The offer's nd_in_crisis = no holds at the close only because each
        # side's crisis record is cleared before nuclear_crisis.6 is sent.
        body = block(self.effects, "nd_crisis_close")
        clear = body.rindex("nd_crisis_clear_vars = yes")
        self.assertLess(clear, body.index("trigger_event = { id = nuclear_crisis.6 popup = yes }"))

    def test_stand_down_option_is_gated_and_settles_first(self):
        self.assertIn("name = nuclear_crisis.6.b", self.stand_down)
        self.assertIn("trigger = { nd_crisis_notice_offers_standdown = yes }", self.stand_down)
        settle = self.stand_down.index("nd_crisis_notice_settle = yes")
        lower = self.stand_down.index("nd_stand_down_to_pre_crisis = yes")
        self.assertLess(settle, lower)
        self.assertNotIn("default_option", self.stand_down)

    def test_ai_keeps_its_own_posture_review(self):
        self.assertIn("ai_chance = { base = 0 }", self.stand_down)
        self.assertIn("default_option = yes", self.keep)

    def test_keep_option_says_so_when_a_stand_down_is_offered(self):
        names = re.findall(r"name = \{\s*trigger = \{ ([^}]*) \}\s*text = (\S+)\s*\}", self.keep)
        self.assertEqual(names, [("nd_crisis_notice_offers_standdown = yes", "nuclear_crisis.6.a_keep"),
                                 ("always = yes", "nuclear_crisis.6.a")])

    def test_stand_down_returns_to_each_recorded_level(self):
        body = block(self.effects, "nd_stand_down_to_pre_crisis")
        ladder = re.findall(r"nd_pre_crisis_readiness_value < (\d)\s*\}\s*nd_set_readiness_target_(\d) = yes", body)
        self.assertEqual(ladder, [("1", "0"), ("2", "1")])
        self.assertRegex(body, r"else = \{\s*nd_set_readiness_target_2 = yes\s*\}")

    def test_the_outcome_lowers_readiness_before_the_notice_opens(self):
        # The offer's comment rests on this: a concession or an agreed
        # stand-down sets the target at the close, and applying the outcome
        # in the option never touches readiness.
        self.assertNotIn("readiness", block(self.effects, "nd_crisis_apply_outcome_side"))
        self.assertIn("nd_set_readiness_target_1 = yes", block(self.effects, "nd_standdown_one_side"))

    def test_loc(self):
        for key in ("nuclear_crisis.6.a_keep", "nuclear_crisis.6.b"):
            self.assertTrue(loc_value(key), key)


class TestHighAlertReminder(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(EFFECTS))
        self.triggers = strip_comments(read(TRIGGERS))

    def test_monthly_update_reminds(self):
        self.assertIn("nd_remind_high_alert = yes", block(self.effects, "nd_monthly_update"))

    def test_one_notice_per_stint_for_players(self):
        body = block(self.effects, "nd_remind_high_alert")
        self.assertRegex(body, r"^\s*if = \{\s*limit = \{ is_ai = no \}")
        self.assertEqual(body.count("post_notification = nd_high_alert_reminder"), 1)
        self.assertIn("NOT = { has_variable = nd_high_alert_reminded }", body)
        self.assertIn("set_variable = nd_high_alert_reminded", body)
        rearm = body.index("remove_variable = nd_high_alert_reminded")
        self.assertLess(rearm, body.index("post_notification"))
        self.assertRegex(body, r"var:nd_high_alert_quiet_months < (\d+)\s*\}\s*remove_variable = nd_high_alert_reminded")

    def test_quiet_months_count_only_outside_a_crisis(self):
        body = block(self.effects, "nd_remind_high_alert")
        quiet = block(self.triggers, "nd_high_alert_quiet")
        for line in ("nd_readiness_high_alert = yes", "var:nd_readiness_target = 3", "nd_in_crisis = no",
                     "has_variable = nd_readiness_months"):
            self.assertIn(line, quiet)
        # Seeded before the first change (change_variable creates nothing).
        seed = body.index("NOT = { has_variable = nd_high_alert_quiet_months }")
        self.assertLess(seed, body.index("change_variable = { name = nd_high_alert_quiet_months add = 1 }"))
        # A readiness step during the month restarts the count.
        self.assertRegex(body, r"var:nd_high_alert_quiet_months > var:nd_readiness_months \}\s*"
                               r"set_variable = \{ name = nd_high_alert_quiet_months value = var:nd_readiness_months \}")
        # Anything but a quiet High Alert zeroes it.
        self.assertRegex(body, r"else = \{\s*set_variable = \{ name = nd_high_alert_quiet_months value = 0 \}\s*\}")

    def test_months_match_the_permanent_alert_threshold(self):
        body = block(self.effects, "nd_remind_high_alert")
        theirs = re.findall(r"var:nd_readiness_months >= (\d+)",
                            block(self.triggers, "nd_incident_eligible_permanent_alert"))
        self.assertEqual(len(theirs), 1)
        self.assertEqual(re.findall(r"var:nd_high_alert_quiet_months >= (\d+)", body), theirs)
        self.assertEqual(re.findall(r"var:nd_high_alert_quiet_months < (\d+)", body), theirs)

    def test_message_is_a_toast(self):
        body = block(strip_comments(read(MESSAGES)), "nd_high_alert_reminder")
        self.assertIn("notification_type = toast", body)
        self.assertIn("type = country", body)

    def test_notice_text_reads_the_live_figures(self):
        desc = loc_value("notification_nd_high_alert_reminder_desc")
        self.assertIn("Var('nd_high_alert_quiet_months')", desc)
        self.assertIn("ScriptValue('nd_display_strain')", desc)
        self.assertIn("$nd_w_posture_header$", desc)
        self.assertIn("$te_military_tab_nuclear$", desc)
        for key in ("notification_nd_high_alert_reminder_name", "notification_nd_high_alert_reminder_tooltip",
                    "nd_w_posture_header", "te_military_tab_nuclear"):
            self.assertTrue(loc_value(key), key)

    def test_ten_times_routine(self):
        # The notice says that in peacetime incidents at High Alert are ten
        # times as likely as at Routine: the base monthly rates, 10 against 1
        # (with no crisis or war the surcharge is 0). In a war the commander
        # misreading can be eligible at Routine, so the ratio is lower there.
        self.assertIn("In peacetime, incidents at High Alert are ten times as likely as at Routine",
                      loc_value("notification_nd_high_alert_reminder_desc"))
        body = block(strip_comments(read(VALUES)), "nd_incident_base_monthly_permille")
        self.assertRegex(body, r"^\s*value = 1\b")
        self.assertRegex(body, r"nd_readiness_high_alert = yes \} value = 10\b")


if __name__ == "__main__":
    unittest.main()
