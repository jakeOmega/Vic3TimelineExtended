"""Solar colonization is billed only while its programme runs (owner, 2026-09-29).

Its journal entry stays open with the production method switched off, because
the colonies' modifiers live on it. It used to keep billing its funding and
approach cost then, and its funding kept adding to the programme's pace, while
its controls were hidden so the player could not lower it. Each milestone's
entry declares its cost and funding modifiers only while it is billed (#1404),
and the engine re-reads the gate every few days, so a method switched off,
which no button reports, needs no recalculation. The values are evaluated in
test_space_race_scaling_modifiers.py.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
JE = os.path.join(REPO, "common", "journal_entries", "je_space_race.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "space_race_triggers.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "space_race_on_actions.txt")

MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "mars_landing",
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

    def test_costs_are_declared_only_on_a_billed_milestone(self):
        je = _read(JE)
        for m in MILESTONES:
            entry = _block(je, f"je_space_race_{m}")
            for name in ("sr_space_program_cost", "sr_funding_progress", "sr_funding_throughput"):
                with self.subTest(milestone=m, modifier=name):
                    declared = re.search(r"scaling_modifiers_while_active = \{\s*modifier = " + name
                                         + r"\s*value = \{\s*value = 0\s*if = \{\s*limit = \{ (.*?) \}", entry)
                    self.assertIsNotNone(declared)
                    self.assertEqual(declared.group(1), f"sr_milestone_billed_{m} = yes")
                    self.assertNotIn("has_variable = sr_active_", declared.group(1))

    def test_nothing_caches_the_billing_state(self):
        """sr_cost_solar_running recorded what the last recalculation billed, and
        the monthly pulse recalculated when it went stale. The declaration reads
        the trigger itself."""
        for path in (JE, TRIGGERS, ON_ACTIONS,
                     os.path.join(REPO, "common", "scripted_effects", "space_race_effects.txt")):
            with self.subTest(path=os.path.relpath(path, REPO)):
                self.assertNotIn("sr_cost_solar_running", _read(path))


if __name__ == "__main__":
    unittest.main()
