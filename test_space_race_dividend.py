# -*- coding: utf-8 -*-
"""Commercial Space Industry: the space race's leftover progress after the race.

Once a country has nothing left to race for (every single-goal milestone done,
every world claimed, nothing running), the flat progress its sources still give
pays Extraplanetary Base throughput: sr_commercial_space_dividend at multiplier
= sr_space_dividend_points, re-applied by the monthly country pulse. None of the
choices below is visible to the engine, which accepts any of them silently:

- the points read the flat ``country_space_race_progress_add``, not sr_progress
  (its 0.5 floor pays everyone) nor the progress multiplier (Antimatter Engines
  alone reach +250%), and are capped;
- the 5% a point in the text is the modifier's unit value;
- the modifier carries no space race progress, so it cannot feed itself;
- one refresh site, the monthly pulse;
- Solar System Colonization finishes for every colony holder once the last
  world is claimed, not only on a bar fill, or the dividend waits years.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "moon_base",
              "mars_landing", "interstellar_probe")


def _path(*parts):
    return os.path.join(REPO, *parts)


def _raw(*parts):
    with open(_path(*parts), encoding="utf-8-sig") as f:
        return f.read()


def _read(*parts):
    return re.sub(r"#[^\n]*", "", _raw(*parts))


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


def _loc(key):
    for name in sorted(os.listdir(_path("localization", "english"))):
        if not name.endswith(".yml"):
            continue
        m = re.search(r"(?m)^ " + re.escape(key) + r':\d* "(.*)"\s*$',
                      _raw("localization", "english", name))
        if m:
            return m.group(1)
    raise AssertionError(f"no loc for {key}")


VALUES = _read("common", "script_values", "space_race_values.txt")
MODIFIERS = _read("common", "static_modifiers", "space_race_modifiers.txt")
TRIGGERS = _read("common", "scripted_triggers", "space_race_triggers.txt")
EFFECTS = _read("common", "scripted_effects", "space_race_effects.txt")
ON_ACTIONS = _read("common", "on_actions", "space_race_on_actions.txt")
JE = _read("common", "journal_entries", "je_space_race.txt")
EVENTS = _read("events", "space_race_events.txt")


def _unit():
    body = _block(MODIFIERS, "sr_commercial_space_dividend")
    return float(re.search(r"building_space_mine_throughput_add\s*=\s*([\d.]+)", body).group(1))


def _max_points():
    return float(re.search(r"value\s*=\s*([\d.]+)",
                           _block(VALUES, "sr_space_dividend_max_points")).group(1))


class ValueTests(unittest.TestCase):
    def test_points_are_the_flat_progress_capped(self):
        body = _block(VALUES, "sr_space_dividend_points")
        self.assertRegex(body, r"^\s*value\s*=\s*modifier:country_space_race_progress_add\s")
        self.assertNotIn("sr_progress", body)
        self.assertNotIn("country_space_race_progress_mult", body)
        self.assertRegex(body, r"\bmin\s*=\s*0\b")
        self.assertRegex(body, r"\bmax\s*=\s*sr_space_dividend_max_points\b")

    def test_the_cap_is_fifty_percent(self):
        self.assertAlmostEqual(_max_points() * _unit(), 0.5)

    def test_display_percent_follows_the_unit(self):
        for value, source in (("sr_space_dividend_pct", "sr_space_dividend_points"),
                              ("sr_space_dividend_max_pct", "sr_space_dividend_max_points")):
            with self.subTest(value=value):
                body = _block(VALUES, value)
                self.assertRegex(body, r"value\s*=\s*" + source + r"\b")
                factor = float(re.search(r"multiply\s*=\s*([\d.]+)", body).group(1))
                self.assertAlmostEqual(factor, _unit() * 100)

    def test_text_states_the_unit_and_cap(self):
        pct = f"+{round(_unit() * 100):d}%"
        cap = f"+{round(_unit() * _max_points() * 100):d}%"
        tooltip = _loc("sr_space_dividend_tt")
        self.assertIn(pct, tooltip)
        self.assertIn("sr_space_dividend_max_pct", tooltip)
        self.assertIn("sr_space_dividend_pct", tooltip)
        desc = _loc("sr_commercial_space_dividend_desc")
        self.assertIn(pct, desc)
        self.assertIn(cap, desc)


class ModifierTests(unittest.TestCase):
    def test_modifier_only_pays_throughput(self):
        body = _block(MODIFIERS, "sr_commercial_space_dividend")
        keys = re.findall(r"^\s*(\w+)\s*=", body, re.M)
        self.assertEqual(sorted(keys), ["building_space_mine_throughput_add", "icon"])

    def test_one_refresh_site(self):
        sites = []
        for folder in ("common", "events"):
            for root, _dirs, files in os.walk(_path(folder)):
                for name in files:
                    if not name.endswith(".txt"):
                        continue
                    rel = os.path.relpath(os.path.join(root, name), REPO)
                    text = _read(rel)
                    if re.search(r"name\s*=\s*sr_commercial_space_dividend\b", text):
                        sites.append(rel)
        self.assertEqual(sites, [os.path.join("common", "scripted_effects", "space_race_effects.txt")])
        self.assertEqual(len(re.findall(r"name\s*=\s*sr_commercial_space_dividend\b", EFFECTS)), 1)


class ConcludedTests(unittest.TestCase):
    def test_needs_every_milestone_every_world_and_nothing_running(self):
        body = _block(TRIGGERS, "sr_space_race_concluded")
        for m in MILESTONES:
            with self.subTest(milestone=m):
                self.assertRegex(body, r"has_variable\s*=\s*sr_completed_" + m + r"\b")
        self.assertIn("has_global_variable = sr_all_colonies_complete", body)
        self.assertRegex(body, r"NOT\s*=\s*\{\s*sr_has_running_milestone\s*=\s*yes\s*\}")


class RefreshTests(unittest.TestCase):
    def test_removes_then_applies_only_when_concluded(self):
        body = _block(EFFECTS, "sr_refresh_space_dividend")
        remove = body.index("remove_modifier = sr_commercial_space_dividend")
        add = re.search(r"add_modifier\s*=\s*\{\s*name\s*=\s*sr_commercial_space_dividend\s+"
                        r"multiplier\s*=\s*sr_space_dividend_points\s*\}", body)
        self.assertIsNotNone(add)
        self.assertLess(remove, add.start())
        limits = " ".join(_if_limits_around(body, add.start()))
        self.assertIn("sr_space_race_concluded = yes", limits)
        self.assertIn("sr_space_dividend_points > 0", limits)

    def test_announces_once_to_players(self):
        body = _block(EFFECTS, "sr_refresh_space_dividend")
        pos = body.index("id = space_race_events.77")
        limits = " ".join(_if_limits_around(body, pos))
        self.assertIn("NOT = { has_variable = sr_space_dividend_announced }", limits)
        self.assertIn("is_player = yes", limits)
        self.assertIn("set_variable = { name = sr_space_dividend_announced value = yes }", body)
        self.assertIn("space_race_events.77", EVENTS)

    def test_called_from_the_monthly_pulse(self):
        self.assertRegex(ON_ACTIONS, r"on_monthly_pulse_country\s*=\s*\{\s*on_actions\s*=\s*\{\s*space_race_on_action")
        pulse = _block(ON_ACTIONS, "space_race_on_action")
        pos = pulse.index("sr_refresh_space_dividend = yes")
        self.assertIn("sr_space_race_participant = yes", " ".join(_if_limits_around(pulse, pos)))


class ColonizationEndTests(unittest.TestCase):
    """Every colony holder finishes the month the last world is claimed."""

    def test_completion_is_not_tied_to_a_bar_fill(self):
        pulse = _block(_block(_block(JE, "je_space_race_solar_colonization"), "on_monthly_pulse"), "effect")
        pos = pulse.index("set_variable = { name = sr_completed_solar_colonization value = yes }")
        limits = _if_limits_around(pulse, pos)
        self.assertEqual(len(limits), 1, "the completion must sit in one top-level if")
        self.assertIn("has_variable = sr_active_solar_colonization", limits[0])
        self.assertIn("has_global_variable = sr_all_colonies_complete", limits[0])
        self.assertIn("sr_has_space_colony = yes", limits[0])


if __name__ == "__main__":
    unittest.main()
