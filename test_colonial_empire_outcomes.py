# -*- coding: utf-8 -*-
"""The Colonial Empire's nine endings, one 1.15 outcome each (#1432).

Until #1432 the entry had one success and one failure outcome, each of which
picked its ending in its effect, so the journal panel could not show which path
the empire was on. Each ending is now an outcome of its own. Pinned here:

- the nine outcomes, in the old dispatch's order (the two Imperial Federation
  capstones, the four paths of a held bar, the voluntary end, the two
  collapses), each firing its one event, with a header and a conclusion_desc;
- their triggers, evaluated over a grid of the inputs, pick exactly the ending
  the old `if` chains picked: of each kind, exactly one outcome holds when the
  old shared condition held, and none when it did not, so the panel ticks one
  ending and the first-declared rule never has to break a tie;
- the counters are read through the guarded `_months_value` script values;
- every success ends through colonial_empire_secured_end, both collapses
  through colonial_empire_collapse_end, and those helpers keep the old effects.
"""

import itertools
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
JE = os.path.join(REPO, "common", "journal_entries", "je_colonial_empire.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "decolonization.txt")
LOC = os.path.join(REPO, "localization", "english", "te_journal_entries_l_english.yml")

BAR = '"scripted_bar_progress(colonial_stability_bar)"'
COMPLETION_MONTHS = 60

SUCCESS = [300, 301, 203, 202, 205, 200]
FAILURE = [206, 204, 201]


def _plain_list(value):
    return value if isinstance(value, list) else [value]


def _outcomes():
    parser = ParadoxFileParser()
    parser.parse_file(JE)
    return [o[1] for o in parser.data["je_colonial_empire"][1]["outcome"]]


def _number(token, world):
    if token in world:
        return world[token]
    if token == "colonial_empire_completion_months":
        return COMPLETION_MONTHS
    return float(token)


def _compare(left, op, right):
    return {"<": left < right, "<=": left <= right, ">": left > right, ">=": left >= right,
            "=": left == right}[op]


def _holds(block, world):
    """Every condition of a trigger block holds (an implicit AND)."""
    for key, entries in block.items():
        for op, value in _plain_list(entries):
            if not _one(key, op, value, world):
                return False
    return True


def _one(key, op, value, world):
    if key == "text":
        return True
    if key in ("custom_tooltip", "AND"):
        return _holds(value, world)
    if key == "OR":
        return any(_one(k, o, v, world) for k, entries in value.items() for o, v in _plain_list(entries))
    if key == "NOT":
        return not _holds(value, world)
    if key == "NAND":
        return not _holds(value, world)
    if key == "has_variable":
        return value in world["vars"]
    if key == "scope:journal_entry":
        return _holds(value, {**world, BAR: world["bar"]})
    if key == "any_scope_state" or key == "country_has_qualifying_colonial_subject":
        return world["colonies"]
    if key.startswith("var:"):
        return _compare(world["vars"][key[4:]], op, _number(value, world))
    return _compare(_number(key, world), op, _number(value, world))


def _old_success(world):
    """The success outcome's old dispatch (before #1432)."""
    g, i, a = world["colonial_garrison_months_value"], world["colonial_invest_months_value"], \
        world["colonial_assimilate_months_value"]
    if "imperial_federation_iron_fist" in world["vars"]:
        return 300
    if "imperial_federation_civilizing" in world["vars"]:
        return 301
    if g >= i and g >= a and g > 24:
        return 203
    if i >= a and i > 24:
        return 202
    if a > 24:
        return 205
    return 200


def _old_failure(world):
    g, i, a = world["colonial_garrison_months_value"], world["colonial_invest_months_value"], \
        world["colonial_assimilate_months_value"]
    if world["bar"] > 0:
        return 206
    if not (g >= i and g >= a) and (i > 24 or a > 24):
        return 204
    return 201


def _old_success_holds(world):
    held = world["vars"].get("colonial_at_100_months", -1) >= COMPLETION_MONTHS
    return held or "imperial_federation_taken" in world["vars"]


def _old_failure_holds(world):
    voluntary = "ce_separation_cached" in world["vars"] and not world["colonies"] and world["bar"] > 0
    return world["bar"] <= 0 or voluntary


def _worlds():
    months = (0, 10, 24, 24.33, 30, 40)
    acts = ((), ("imperial_federation_taken", "imperial_federation_iron_fist"),
            ("imperial_federation_taken", "imperial_federation_civilizing"))
    for g, i, a, act, held, bar, colonies in itertools.product(
            months, months, months, acts, (None, 59, 60), (0, 50, 100), (True, False)):
        vars_ = {name: "yes" for name in act}
        vars_["ce_separation_cached"] = "yes"
        if held is not None:
            vars_["colonial_at_100_months"] = held
        yield {"colonial_garrison_months_value": g, "colonial_invest_months_value": i,
               "colonial_assimilate_months_value": a, "vars": vars_, "bar": bar, "colonies": colonies}


def _event(outcome):
    return int(outcome["effect"][1]["trigger_event"][1]["id"][1].split(".")[1])


class OutcomeShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outcomes = _outcomes()
        with open(LOC, encoding="utf-8-sig") as handle:
            cls.loc = set(re.findall(r"(?m)^ ([\w.]+):\d* ", handle.read()))

    def test_nine_endings_in_the_old_order_then_the_invalid_outcome(self):
        self.assertEqual(len(self.outcomes), 10)
        self.assertEqual([_event(o) for o in self.outcomes[:9]], SUCCESS + FAILURE)
        colors = [o["color"][1].strip('"') for o in self.outcomes[:9]]
        self.assertEqual(colors, ["gold_positive"] * 6 + ["blue_negative"] * 3)
        self.assertEqual(self.outcomes[9]["flags"][1], ["hidden", "invalid_outcome"])

    def test_each_ending_has_its_own_header_and_conclusion(self):
        headers = [o["header"][1] for o in self.outcomes[:9]]
        conclusions = [o["conclusion_desc"][1] for o in self.outcomes[:9]]
        self.assertEqual(len(set(headers)), 9)
        self.assertEqual(len(set(conclusions)), 9)
        for key in headers + conclusions:
            with self.subTest(key=key):
                self.assertIn(key, self.loc)

    def test_every_trigger_test_is_inside_a_custom_tooltip(self):
        # The panel prints a bare script-value comparison as script.
        for index, outcome in enumerate(self.outcomes[:9]):
            with self.subTest(outcome=index):
                self.assertEqual(set(outcome["trigger"][1]), {"custom_tooltip"})

    def test_the_counters_are_read_through_the_guarded_values(self):
        with open(JE, encoding="utf-8-sig") as handle:
            text = re.sub(r"#[^\n]*", "", handle.read())
        self.assertNotRegex(text, r"var:colonial_(invest|garrison|assimilate)_months")
        self.assertRegex(text, r"colonial_garrison_months_value >= colonial_invest_months_value")

    def test_the_endings_go_through_the_helpers(self):
        for outcome in self.outcomes[:6]:
            self.assertEqual(outcome["effect"][1]["colonial_empire_secured_end"][1], "yes")
        self.assertNotIn("colonial_empire_collapse_end", self.outcomes[6]["effect"][1])
        for outcome in self.outcomes[7:9]:
            self.assertEqual(outcome["effect"][1]["colonial_empire_collapse_end"][1], "yes")


class OutcomeTriggerTest(unittest.TestCase):
    """The triggers pick what the old dispatch picked, and never two at once."""

    @classmethod
    def setUpClass(cls):
        cls.outcomes = _outcomes()

    def _true(self, outcomes, world):
        return [_event(o) for o in outcomes if _holds(o["trigger"][1], world)]

    def test_success_matches_the_old_dispatch(self):
        checked = 0
        for world in _worlds():
            true = self._true(self.outcomes[:6], world)
            if _old_success_holds(world):
                self.assertEqual(true, [_old_success(world)], world)
                checked += 1
            else:
                self.assertEqual(true, [], world)
        self.assertGreater(checked, 1000)

    def test_failure_matches_the_old_dispatch(self):
        checked = 0
        for world in _worlds():
            true = self._true(self.outcomes[6:9], world)
            if _old_failure_holds(world):
                self.assertEqual(true, [_old_failure(world)], world)
                checked += 1
            else:
                self.assertEqual(true, [], world)
        self.assertGreater(checked, 1000)


class HelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(EFFECTS, encoding="utf-8-sig") as handle:
            cls.text = re.sub(r"#[^\n]*", "", handle.read())

    def _helper(self, name):
        m = re.search(r"(?m)^" + name + r" = \{\n(.*?)^\}", self.text, re.S)
        self.assertTrue(m, name)
        return " ".join(m.group(1).split())

    def test_a_success_blocks_reentry_and_clears_the_counters(self):
        body = self._helper("colonial_empire_secured_end")
        for line in ("remove_variable = decol_chosen_releases", "colonial_empire_je_cleanup_effect = yes",
                     "colonial_empire_clear_path_months = yes",
                     "set_variable = { name = colonial_empire_completed value = yes }"):
            self.assertIn(line, body)

    def test_a_collapse_sets_the_cooldown_and_the_aftershock_but_keeps_the_counters(self):
        body = self._helper("colonial_empire_collapse_end")
        for line in ("remove_variable = decol_chosen_releases",
                     "set_variable = { name = colonial_empire_collapsed_recently value = yes days = 3650 }",
                     "every_subject_or_below = { limit = { is_qualifying_colonial_subject = yes }",
                     "colonial_empire_je_cleanup_effect = yes"):
            self.assertIn(line, body)
        # The wave the collapse events start reads them (decol_wave_end clears them).
        self.assertNotIn("colonial_empire_clear_path_months", body)


if __name__ == "__main__":
    unittest.main()
