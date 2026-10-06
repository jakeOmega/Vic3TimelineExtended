"""Nuclear crisis pacing and the taboo's weight on threats (owner rulings 2026-10-06).

- The opening threat reaches the target after 14, 17 or 21 days, and the crisis
  clock waits for it, so the deadline, the pressure cadence and the year's
  expiry start from the delivery. In the 2026-10-06 observer run 23 of 31
  yields came the day the threat arrived.
- Every other armed country hears of the threat at once.
- The taboo scales how often the AI threatens (defensive disputes exempt) and
  how readily it carries a threat out; Warfighting at a low taboo carries one
  out more readily, and an insurgency is a poor target.
- nd_log_strike_eligibility records when the AI's wartime strike is open.
"""

import re
import unittest
from pathlib import Path

from test_nuclear_deterrence import block, option_body, read, strip_comments

ROOT = Path(__file__).resolve().parent
CRISIS_EFFECTS = ROOT / "common/scripted_effects/nuclear_crisis_effects.txt"
CRISIS_EVENTS = ROOT / "events/nuclear_crisis_events.txt"
ACTIONS = ROOT / "common/diplomatic_actions/nuclear_crisis_actions.txt"
VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
OBSERVER = ROOT / "common/scripted_effects/nuclear_observer_effects.txt"
DETERRENCE = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
MESSAGES = ROOT / "common/messages/extra_messages.txt"
LOC = ROOT / "localization/english/te_notifications_l_english.yml"


class TestCrisisTransit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_the_opening_threat_arrives_after_two_or_three_weeks(self):
        sender = block(self.effects, "nd_crisis_send_event_in_transit")
        self.assertEqual(sorted(int(d) for d in re.findall(r"days = (\d+)", sender)), [14, 17, 21])
        self.assertIn("random_list", sender)
        self.assertIn("nd_crisis_event_token", sender)
        opening = block(self.effects, "nd_crisis_open")
        self.assertIn("nd_crisis_send_event_in_transit = { WHO = scope:nd_target EVENT = nuclear_crisis.1 }", opening)
        self.assertNotIn("nd_crisis_send_event = { WHO = scope:nd_target EVENT = nuclear_crisis.1 }", opening)

    def test_the_clock_waits_for_the_delivery(self):
        opening = block(self.effects, "nd_crisis_open")
        self.assertIn("name = nd_crisis_transit_weeks value = nd_crisis_transit_weeks_value", opening)
        self.assertRegex(strip_comments(read(VALUES)), r"nd_crisis_transit_weeks_value = 3\b")
        tick = block(self.effects, "nd_crisis_weekly_tick")
        transit = tick.index("var:nd_crisis_transit_weeks > 0")
        counter = tick.index("name = nd_crisis_weeks add = 1")
        self.assertLess(transit, counter)
        # The counters sit in the else of the transit branch.
        self.assertRegex(tick[transit:counter], r"subtract = 1\s*\}\s*\}\s*else = \{")
        self.assertIn("name = nd_crisis_pressure_weeks add = 1", tick[counter:counter + 200])

    def test_a_closed_crisis_clears_its_transit(self):
        self.assertIn("remove_variable = nd_crisis_transit_weeks", block(self.effects, "nd_crisis_clear_vars"))


class TestNuclearPowersNotice(unittest.TestCase):
    def test_every_other_armed_country_hears_of_it(self):
        effects = strip_comments(read(CRISIS_EFFECTS))
        notice = block(effects, "nd_crisis_notify_nuclear_powers")
        for needle in ("nd_is_armed = yes", "NOT = { this = scope:nd_issuer }", "NOT = { this = scope:nd_target }",
                       "post_notification = nd_crisis_ultimatum_issued", "post_notification = nd_crisis_warning_reported"):
            self.assertIn(needle, notice, needle)
        self.assertIn("nd_crisis_notify_nuclear_powers = { PUBLIC = $PUBLIC$ }", block(effects, "nd_crisis_open"))

    def test_the_notices_are_defined_and_worded(self):
        messages = strip_comments(read(MESSAGES))
        loc = read(LOC)
        for name in ("nd_crisis_ultimatum_issued", "nd_crisis_warning_reported"):
            self.assertRegex(messages, r"(?m)^" + name + r" = \{", name)
            for suffix in ("_name", "_desc", "_tooltip"):
                self.assertRegex(loc, r"(?m)^ notification_" + name + suffix + r":0 ", name + suffix)


class TestTabooInThreats(unittest.TestCase):
    def test_both_opening_actions_scale_with_the_taboo_except_in_defence(self):
        text = strip_comments(read(ACTIONS))
        for name in ("nd_nuclear_warning_action", "nd_nuclear_ultimatum_action"):
            chance = block(block(block(text, name), "ai"), "evaluation_chance")
            i = chance.index("multiply = nd_taboo_ai_use_factor")
            guard = chance[chance.rfind("limit", 0, i):i]
            for exempt in ("nd_dispute_guarantee_against", "nd_enemy_threatens_existence", "nd_core_threatened_by"):
                self.assertIn(exempt, guard, f"{name}: {exempt}")
            self.assertRegex(guard, r"NOT = \{\s*AND = \{", name)

    def test_carrying_out_a_threat_follows_the_taboo(self):
        body = option_body(strip_comments(read(CRISIS_EVENTS)), "nuclear_crisis.4.g")
        chance = block(body, "ai_chance")
        factors = [float(f) for f in re.findall(r"factor = ([\d.]+)", chance)]
        # The taboo rungs, falling from x1.8 below 10 to x0.75 from 50.
        self.assertEqual(factors[:5], [1.8, 1.6, 1.25, 0.92, 0.75])
        self.assertIn("nd_taboo_value < 25", chance)
        # An insurgency is a fifth as likely, and the justification still zeroes last.
        self.assertRegex(chance, r"is_revolutionary = yes\s*is_secessionist = yes\s*\}\s*\}\s*\}\s*factor = 0\.2")
        self.assertRegex(chance, r"nd_ai_nuclear_use_justified = \{ ENEMY = scope:nd_target \} \} \}\s*factor = 0\s*\}\s*$")


class TestStrikeEligibilityRecord(unittest.TestCase):
    def test_recorded_once_per_enemy_from_the_weekly_update(self):
        observer = strip_comments(read(OBSERVER))
        trace = block(observer, "nd_log_strike_eligibility")
        for gate in ("nd_doctrine_permits_strike", "nd_pledge_permits_strike", "nd_war_law_permits_strategic_strike",
                     "nd_forces_assembled = yes", "nd_ai_nuclear_use_justified",
                     "is_target_in_variable_list = { name = nd_sel_logged", "add_to_variable_list = { name = nd_sel_logged",
                     "clear_variable_list = nd_sel_logged", "action=strike_eligible"):
            self.assertIn(gate, trace, gate)
        self.assertIn("nd_log_strike_eligibility = yes", block(strip_comments(read(DETERRENCE)), "nd_weekly_update"))


if __name__ == "__main__":
    unittest.main()
