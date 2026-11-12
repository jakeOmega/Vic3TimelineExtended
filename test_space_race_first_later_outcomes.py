# -*- coding: utf-8 -*-
"""Each Space Race milestone with a first and a later reward has an outcome for each (#1433).

Pinned here, for suborbital, orbital, Moon landing, probe, Mars landing and
interstellar probe (common/journal_entries/je_space_race.txt):
- two completion outcomes, first then later, ahead of the failure outcome;
- both require the goal; first requires sr_global_first_<m> unset, later set,
  each inside a custom_tooltip whose loc key exists;
- both run the same effect, so the effect's own check of the global variable
  (sr_complete_milestone_effect_base) stays what pays the reward;
- each previews its own reward modifier, and every header and conclusion
  key it names exists in English.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "mars_landing", "interstellar_probe")


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, start):
    """The text of the brace block whose `{` is at or after `start`."""
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i : j + 1]
    raise AssertionError("unclosed block")


def _entry(text, name):
    m = re.search(rf"^{name} = \{{", text, re.M)
    assert m, name
    return _block(text, m.start())


def _outcomes(entry):
    return [_block(entry, m.start()) for m in re.finditer(r"^\toutcome = \{", entry, re.M)]


def _loc_keys():
    keys = set()
    folder = os.path.join(REPO, "localization", "english")
    for name in os.listdir(folder):
        if name.endswith(".yml"):
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                keys.update(re.findall(r"^ ([A-Za-z0-9_.]+):\d* ", f.read(), re.M))
    return keys


def _field(block, key):
    m = re.search(rf"\b{key} = (\S+)", block)
    return m.group(1) if m else None


class FirstAndLaterOutcomes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _read("common", "journal_entries", "je_space_race.txt")
        cls.loc = _loc_keys()

    def test_each_milestone_has_first_then_later_then_failure(self):
        for m in MILESTONES:
            with self.subTest(milestone=m):
                outs = _outcomes(_entry(self.text, f"je_space_race_{m}"))
                visible = [o for o in outs if "invalid_outcome" not in o]
                self.assertEqual(len(visible), 3, "first, later and failure")
                first, later, failure = visible
                goal = f"var:sr_progress_{m} >= sr_{m}_goal"
                for o in (first, later):
                    self.assertIn(goal, o)
                self.assertNotIn(goal, failure)
                self.assertRegex(
                    first,
                    rf"text = sr_milestone_first_open_tt\s+NOT = \{{ has_global_variable = sr_global_first_{m} \}}",
                )
                self.assertRegex(
                    later, rf"text = sr_milestone_first_claimed_tt\s+has_global_variable = sr_global_first_{m}\s"
                )
                self.assertEqual(_block(first, first.index("effect = {")), _block(later, later.index("effect = {")))
                self.assertIn(f"sr_complete_{m}_effect = yes", first)
                self.assertIn(f"add_modifier = {{ name = sr_first_{m} }}", first)
                self.assertNotIn(f"name = sr_{m} }}", first)
                self.assertIn(f"add_modifier = {{ name = sr_{m} }}", later)
                self.assertNotIn(f"sr_first_{m}", later)

    def test_loc_keys_exist(self):
        needed = {"sr_milestone_first_open_tt", "sr_milestone_first_claimed_tt"}
        for m in MILESTONES:
            for o in _outcomes(_entry(self.text, f"je_space_race_{m}"))[:2]:
                for key in ("header", "effect_header", "conclusion_desc"):
                    needed.add(_field(o, key))
                needed.update(re.findall(r"custom_tooltip = (\S+_tt)\b", o))
        missing = sorted(k for k in needed if k not in self.loc)
        self.assertEqual(missing, [])

    def test_reward_check_stays_in_the_effect(self):
        effects = _read("common", "scripted_effects", "space_race_effects.txt")
        base = _block(effects, effects.index("sr_complete_milestone_effect_base = {"))
        self.assertIn("NOT = { has_global_variable = sr_global_first_$MILESTONE$ }", base)
        self.assertIn("set_variable = { name = sr_was_first_$MILESTONE$ value = yes }", base)


if __name__ == "__main__":
    unittest.main()
