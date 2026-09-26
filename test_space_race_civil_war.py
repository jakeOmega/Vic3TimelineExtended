# -*- coding: utf-8 -*-
"""Space race across a revolution (docs/audits/civil_war_inheritance_audit.md F5).

A civil war's winner inherits the loser's variables but none of its modifiers,
and every journal entry it inherits active runs `immediate` again. So the space
race records every reward in a variable and rebuilds it, and its `immediate`
blocks create only what is missing. None of this is visible to the engine,
which logs nothing when a reward silently vanishes. These tests pin it.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "moon_base",
              "mars_landing", "interstellar_probe")
ENTRIES = MILESTONES + ("solar_colonization",)
CHOICE_EVENTS = {"80": "orbital", "5": "moon_landing", "81": "probe",
                 "82": "moon_base", "83": "mars_landing"}


def _path(*parts):
    return os.path.join(REPO, *parts)


def _read(*parts):
    with open(_path(*parts), encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block(text, name, start=0):
    """The body of the first ``name = { ... }`` block at or after ``start``."""
    m = re.compile(r"(?<![\w.])" + re.escape(name) + r"\s*=\s*\{").search(text, start)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _if_limits_around(body, pos):
    """The limit text of every ``if``/``else_if`` whose block encloses ``pos``."""
    limits = []
    for m in re.finditer(r"\b(?:if|else_if)\s*=\s*\{", body):
        if m.start() > pos:
            break
        end = _close(body, m.end() - 1)
        if end > pos:
            limits.append(_block(body[m.start():end + 1], "limit"))
    return limits


JE = _read("common", "journal_entries", "je_space_race.txt")
EFFECTS = _read("common", "scripted_effects", "space_race_effects.txt")
TRIGGERS = _read("common", "scripted_triggers", "space_race_triggers.txt")
ON_ACTIONS = _read("common", "on_actions", "space_race_on_actions.txt")
EVENTS = _read("events", "space_race_events.txt")
MODIFIERS = _read("common", "static_modifiers", "space_race_modifiers.txt")


def _immediate(entry):
    return _block(_block(JE, f"je_space_race_{entry}"), "immediate")


class ImmediateTests(unittest.TestCase):
    """`immediate` re-runs on re-activation and on an inherited entry."""

    def test_progress_and_funding_are_only_created(self):
        cases = [(e, v) for e in ENTRIES for v in (f"sr_progress_{e}", f"sr_funding_{e}")]
        cases.append(("interstellar_results", "sr_interstellar_transit_progress"))
        for entry, var in cases:
            with self.subTest(entry=entry, var=var):
                body = _immediate(entry)
                sets = [m.start() for m in re.finditer(
                    r"set_variable\s*=\s*\{\s*name\s*=\s*" + var + r"\b", body)]
                self.assertTrue(sets, f"{var} is not initialised")
                for pos in sets:
                    guarded = any(re.search(r"has_variable\s*=\s*" + var + r"\b", lim)
                                  for lim in _if_limits_around(body, pos))
                    self.assertTrue(guarded, f"{var} is set without a has_variable guard")

    def test_a_finished_colonization_is_not_reopened(self):
        body = _immediate("solar_colonization")
        pos = re.search(r"set_variable\s*=\s*\{\s*name\s*=\s*sr_active_solar_colonization\b", body).start()
        self.assertTrue(any("has_variable = sr_completed_solar_colonization" in lim
                            for lim in _if_limits_around(body, pos)))

    def test_choice_events_are_asked_once(self):
        for ev, entry in CHOICE_EVENTS.items():
            with self.subTest(event=ev):
                body = _immediate(entry)
                pos = body.index(f"id = space_race_events.{ev} ")
                self.assertTrue(any(f"sr_{entry}_choice_made = yes" in lim
                                    for lim in _if_limits_around(body, pos)))
                event = _block(EVENTS, f"space_race_events.{ev}")
                self.assertRegex(_block(event, "trigger"),
                                 r"NOT\s*=\s*\{\s*sr_" + entry + r"_choice_made = yes\s*\}")

    def test_no_other_event_is_fired_from_a_milestone_immediate(self):
        for entry in ENTRIES:
            fired = re.findall(r"trigger_event\s*=\s*\{\s*id\s*=\s*([\w.]+)", _immediate(entry))
            expected = [f"space_race_events.{ev}" for ev, e in CHOICE_EVENTS.items() if e == entry]
            self.assertEqual(fired, expected, entry)

    def test_goal_is_pinned(self):
        for entry in MILESTONES:
            with self.subTest(entry=entry):
                goal = _block(_block(JE, f"je_space_race_{entry}"), "goal_add_value")
                self.assertIn(f"value = sr_{entry}_goal", goal)
                self.assertIn(f"subtract = sr_progress_{entry}_value", goal)
        goal = _block(_block(JE, "je_space_race_interstellar_results"), "goal_add_value")
        self.assertIn("subtract = sr_interstellar_transit_value", goal)

    def test_every_entry_rebuilds_its_own_modifiers(self):
        for entry in ENTRIES:
            with self.subTest(entry=entry):
                self.assertIn(f"sr_sync_{entry}_entry = yes", _immediate(entry))
        pulse = _block(EFFECTS, "sr_sync_space_race_entries")
        self.assertEqual(re.findall(r"sr_sync_(\w+)_entry = yes", pulse), list(ENTRIES))
        monthly = _block(ON_ACTIONS, "space_race_on_action")
        self.assertIn("sr_sync_space_race_entries = yes", monthly)
        self.assertIn("sr_sync_probe_data = yes", monthly)


class RewardTests(unittest.TestCase):
    """Every reward modifier is recorded in a variable and rebuilt from it."""

    def test_milestone_rewards_come_back_at_civil_war_won(self):
        hook = _block(ON_ACTIONS, "on_civil_war_won")
        self.assertIn("sr_on_civil_war_won", hook)
        handler = _block(ON_ACTIONS, "sr_on_civil_war_won")
        self.assertIn("sr_restore_milestone_rewards = yes", handler)
        self.assertIn("sr_sync_probe_data = yes", handler)
        rewarded = set(re.findall(r"^sr_first_(\w+) = \{", MODIFIERS, re.M))
        self.assertEqual(rewarded, set(MILESTONES))
        restored = re.findall(r"MILESTONE = (\w+)", _block(EFFECTS, "sr_restore_milestone_rewards"))
        self.assertEqual(sorted(restored), sorted(MILESTONES))

    def test_milestone_reward_is_modifier_only(self):
        body = _block(EFFECTS, "sr_apply_milestone_reward_base")
        effects = set(re.findall(r"\b(\w+)\s*=", body)) - {"if", "else", "limit", "has_variable", "name"}
        self.assertEqual(effects, {"add_modifier"})

    def test_choice_modifiers_are_rebuilt_from_the_choice(self):
        for ev, entry in CHOICE_EVENTS.items():
            event = _block(EVENTS, f"space_race_events.{ev}")
            pairs = re.findall(
                r"set_variable\s*=\s*\{\s*name\s*=\s*(\w+)\s+value\s*=\s*yes\s*\}\s*"
                r"je:je_space_race_" + entry + r"\s*=\s*\{\s*add_modifier\s*=\s*(\w+)\s*\}", event)
            self.assertGreaterEqual(len(pairs), 3, ev)
            sync = _block(EFFECTS, f"sr_sync_{entry}_entry")
            made = _block(TRIGGERS, f"sr_{entry}_choice_made")
            for var, mod in pairs:
                with self.subTest(event=ev, choice=var):
                    self.assertRegex(sync, r"CHOICE = " + var + r"\s+MODIFIER = " + mod + r"\b")
                    self.assertIn(f"has_variable = {var}", made)

    def test_probe_results_are_recorded(self):
        text = _read("events", "probe_result_events.txt")
        self.assertNotRegex(text, r"add_modifier\s*=\s*\{\s*name\s*=\s*sr_probe_\w+_data")
        granted = set(re.findall(r"sr_grant_probe_data = \{ MODIFIER = (\w+) \}", text))
        defined = set(re.findall(r"^(sr_probe_\w+_data) = \{", MODIFIERS, re.M))
        self.assertEqual(granted, defined)
        synced = set(re.findall(r"MODIFIER = (\w+)", _block(EFFECTS, "sr_sync_probe_data")))
        self.assertEqual(synced, defined)

    def test_colony_modifiers_are_recorded(self):
        text = _read("events", "space_race_colony_events.txt")
        self.assertNotRegex(text, r"je:je_space_race_solar_colonization\s*=\s*\{\s*add_modifier")
        granted = re.findall(r"sr_grant_colony_modifier = \{ MODIFIER = (\w+) \}", text)
        self.assertEqual(len(granted), 68)
        synced = re.findall(r"sr_sync_colony_modifier_base = \{ MODIFIER = (\w+)\s*\}",
                            _block(EFFECTS, "sr_sync_solar_colonization_entry"))
        self.assertEqual(sorted(synced), sorted(set(granted)))
        defined = set(re.findall(r"^(sr_colony_\w+) = \{", MODIFIERS, re.M))
        self.assertEqual(set(granted), defined)


if __name__ == "__main__":
    unittest.main()
