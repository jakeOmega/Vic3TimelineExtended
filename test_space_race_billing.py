"""Solar colonization is billed only while its programme runs (owner, 2026-09-29).

Its journal entry stays open with the production method switched off, because
the colonies' modifiers live on it. It used to keep billing its funding and
approach cost then, and its funding kept adding to the programme's pace, while
its controls were hidden so the player could not lower it. The cost and the
funding-progress modifiers are now applied only to a billed milestone, and the
monthly pulse recalculates when the method changes, which no button reports.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "space_race_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "space_race_triggers.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "space_race_on_actions.txt")

MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
              "interstellar_probe", "solar_colonization")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, f"{name} not found"
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError("unclosed block")


class BilledTest(unittest.TestCase):
    def test_every_milestone_has_a_billing_test(self):
        triggers = _read(TRIGGERS)
        for m in MILESTONES:
            body = _block(triggers, f"sr_milestone_billed_{m}").strip()
            if m == "solar_colonization":
                self.assertEqual(body, "sr_solar_colonization_running = yes")
            else:
                self.assertEqual(body, f"has_variable = sr_active_{m}", m)

    def test_solar_running_needs_the_method(self):
        body = _block(_read(TRIGGERS), "sr_solar_colonization_running")
        self.assertIn("has_variable = sr_active_solar_colonization", body)
        self.assertIn("modifier:country_sr_solar_colonization_program_bool = yes", body)

    def test_costs_are_applied_only_to_a_billed_milestone(self):
        body = _block(_read(EFFECTS), "sr_apply_milestone_cost_modifiers_base")
        self.assertRegex(body, r"limit = \{ sr_milestone_billed_\$MILESTONE\$ = yes \}")
        self.assertNotIn("has_variable = sr_active_$MILESTONE$", body)
        for name in ("sr_space_program_cost", "sr_funding_progress"):
            self.assertIn(f"name = {name}", body)

    def test_the_billing_state_is_recorded_and_rechecked_monthly(self):
        recalc = _block(_read(EFFECTS), "sr_recalculate_cost")
        self.assertIn("limit = { sr_milestone_billed_solar_colonization = yes }", recalc)
        self.assertIn("set_variable = { name = sr_cost_solar_running value = 1 }", recalc)
        self.assertIn("set_variable = { name = sr_cost_solar_running value = 0 }", recalc)
        pulse = _block(_read(ON_ACTIONS), "space_race_on_action")
        self.assertIn("limit = { NOT = { has_variable = sr_cost_solar_running } }", pulse)
        self.assertRegex(pulse, r"sr_milestone_billed_solar_colonization = yes\s*var:sr_cost_solar_running = 0")
        self.assertRegex(pulse, r"NOT = \{ sr_milestone_billed_solar_colonization = yes \}\s*var:sr_cost_solar_running = 1")


if __name__ == "__main__":
    unittest.main()
