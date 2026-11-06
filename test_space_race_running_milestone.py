# -*- coding: utf-8 -*-
""""Is a milestone under way?" has one answer: sr_has_running_milestone (#480).

A shared sr_active_milestone flag used to answer it. Each milestone's journal
entry set it on activation, and the completion of *any* milestone cleared it.
After the moon landing, probe, moon base and Mars landing can run together, so
finishing one switched the flag off while the other two ran on. That silenced
space_race_events.44/.49/.50/.52/.55 and the space-espionage covert op's AI gate,
and the engine logs nothing when an event's trigger just stops holding.

These tests keep the flag retired and keep the trigger in step with
sr_boost_active_milestones, so an event can offer progress when the trigger
holds and something else when it does not (space_race_events.20.a).
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

# The single-goal milestones with an entry (the Moon Base's went with vanilla
# 1.15, #1407).
MILESTONES = ("suborbital", "orbital", "moon_landing", "probe",
              "mars_landing", "interstellar_probe")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
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


def _block(text, name):
    m = re.compile(r"(?<![\w.])" + re.escape(name) + r"\s*=\s*\{").search(text)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _script_files():
    for sub in ("common", "events"):
        for root, _dirs, files in os.walk(os.path.join(REPO, sub)):
            for name in files:
                if name.endswith(".txt"):
                    yield os.path.join(root, name)


class RetiredFlagTests(unittest.TestCase):
    def test_nothing_mentions_the_retired_flag(self):
        # The old-save strip went with vanilla 1.15, which loads no older save
        # (#1407): no script sets, reads or removes the flag.
        for path in _script_files():
            self.assertNotRegex(_read(path), r"\bsr_active_milestone\b", os.path.relpath(path, REPO))

    def test_retired_triggers_are_gone(self):
        for path in _script_files():
            text = _read(path)
            for name in ("sr_is_pursuing_milestone", "sr_can_start_space_race"):
                self.assertNotRegex(text, r"\b" + name + r"\b", os.path.relpath(path, REPO))


class RunningMilestoneTests(unittest.TestCase):
    def test_trigger_covers_what_the_boost_pushes(self):
        triggers = _read(os.path.join(REPO, "common", "scripted_triggers", "space_race_triggers.txt"))
        effects = _read(os.path.join(REPO, "common", "scripted_effects", "space_race_effects.txt"))

        trigger = _block(triggers, "sr_has_running_milestone")
        read = set(re.findall(r"has_variable\s*=\s*sr_active_(\w+)", trigger))
        self.assertEqual(read, set(MILESTONES))
        self.assertIn("sr_solar_colonization_running = yes", trigger)

        boost = _block(effects, "sr_boost_active_milestones")
        pushed = set(re.findall(r"sr_boost_active_milestone_base\s*=\s*\{\s*MILESTONE\s*=\s*(\w+)", boost))
        self.assertEqual(pushed, set(MILESTONES) | {"solar_colonization"})
        # Solar colonization is pushed only while it runs, the same condition
        # the trigger uses for it.
        self.assertRegex(
            boost,
            r"limit\s*=\s*\{\s*sr_solar_colonization_running\s*=\s*yes\s*\}\s*"
            r"sr_boost_active_milestone_base\s*=\s*\{\s*MILESTONE\s*=\s*solar_colonization",
        )

    def test_gated_events_use_the_trigger(self):
        events = _read(os.path.join(REPO, "events", "space_race_events.txt"))
        for n in ("44", "49", "50", "52", "55"):
            trigger = _block(_block(events, f"space_race_events.{n}"), "trigger")
            self.assertIn("sr_has_running_milestone = yes", trigger, f"space_race_events.{n}")



class MoonBaseRetiredTests(unittest.TestCase):
    """The Moon Base milestone is retired (lunar colonization design § 7): the
    first lunar colony takes its place. The entry stayed defined for older
    saves until vanilla 1.15, which loads none (#1407): now nothing of it is
    left, and the flavor events that ran while it did narrate colonization
    before a first lunar colony instead."""

    @classmethod
    def setUpClass(cls):
        cls.events = _read(os.path.join(REPO, "events", "space_race_events.txt"))

    def test_nothing_of_the_entry_is_left(self):
        """Its entry, purpose event, controls, panel and old-save carry are gone;
        the programme rows still draw its icon, the first lunar colony's record."""
        gone = ("je_space_race_moon_base = {", "je:je_space_race_moon_base", "has_journal_entry = je_space_race_moon_base",
                "space_race_events.82", "sr_milestone_moon_base_sgui", "sr_btn_safe_moon_base",
                "sr_sync_moon_base_entry", "sr_moon_base_choice_made", "sr_lunar_carry", "sr_lunar_migrate")
        for path in _script_files():
            text = _read(path)
            for name in gone:
                with self.subTest(path=os.path.relpath(path, REPO), name=name):
                    self.assertNotIn(name, text)

    def test_no_event_waits_on_the_moon_base(self):
        # .20's notice (MILESTONE = moon_base: the first lunar colony's) and .76's
        # program loss read their own markers, not these.
        for name in ("sr_active_moon_base", "sr_progress_moon_base"):
            self.assertNotIn(name, self.events)
        self.assertNotRegex(self.events, r"_progress_months\s*=\s*\{\s*MILESTONE\s*=\s*moon_base")

    def test_the_flavor_events_narrate_the_moon_first(self):
        moon_first = _block(_read(os.path.join(REPO, "common", "scripted_triggers",
                                               "space_race_triggers.txt")), "sr_colonizing_moon_first")
        self.assertEqual(moon_first.split(), ["sr_solar_colonization_running", "=", "yes",
                                              "NOT", "=", "{", "has_variable", "=", "sr_completed_moon_base", "}",
                                              "sr_sites_lunar_open", "=", "yes"])
        for n in ("36", "40", "41", "43", "46"):
            event = _block(self.events, f"space_race_events.{n}")
            with self.subTest(event=n):
                self.assertIn("sr_colonizing_moon_first = yes", _block(event, "trigger"))
                self.assertIn("MILESTONE = solar_colonization", event)

if __name__ == "__main__":
    unittest.main()
