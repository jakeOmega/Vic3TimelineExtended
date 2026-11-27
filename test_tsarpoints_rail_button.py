"""The Tsar's Heir of Alexander agenda: its Rail Transport button counts Air and Space Transport too (#1796).

Vanilla's je_tp_tsar_heir_of_alexander_button_3 asks for 75% of the army's battalions on Rail Transport. The mod's Air
and Space Transport rule Rail Transport out on the same formation, so a Russia that moved its army onto them lost the
button. common/scripted_buttons/te_vanilla_tsarpoints_buttons.txt restates the button (a REPLACE: an INJECT can't change
a trigger block vanilla declares) with its share test moved into te_army_rail_or_better_share
(common/scripted_triggers/te_tsarpoints_triggers.txt). These tests hold:

- the copy to vanilla's button (vanilla_parsed, 1.15): with vanilla's line back in place of the MOD one it must equal
  vanilla's, so a vanilla patch that moves the button fails here and the copy is rebuilt from the new text;
- the trigger's options to the option files: Rail Transport and every transport option the mod adds that rules it out;
- the ladder: each pair of those options at every split of 75% in 1% steps, and nothing else.
"""

import copy
import itertools
import json
import re
import unittest
from pathlib import Path

from test_tax_code_rule import load, plain

ROOT = Path(__file__).resolve().parent
BUTTONS = "common/scripted_buttons/te_vanilla_tsarpoints_buttons.txt"
TRIGGERS = "common/scripted_triggers/te_tsarpoints_triggers.txt"
OPTIONS = "common/mobilization_options/extra_mobilization_options.txt"
VANILLA_BUTTONS = "vanilla_parsed/common/scripted_buttons.json"
BUTTON = "je_tp_tsar_heir_of_alexander_button_3"
TRIGGER = "te_army_rail_or_better_share"
RAIL = "mobilization_option:mobilization_option_rail_transport"
TOOLTIP = "je_tp_tsar_heir_of_alexander_combined_transport_share_tt"
SHARE = 75

_FRACTION = re.compile(r"army_mobilization_option_fraction\s*=\s*\{\s*target\s*=\s*(\S+)\s+value\s*>=\s*([\d.]+)\s*\}")


def _code(rel):
    with open(ROOT / rel, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _body(text, start):
    """The body of the block whose opening brace is the first at or after ``start``."""
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        if depth == 0:
            return text[i + 1:j]
    raise AssertionError("block is not closed")


def _top(text, name):
    m = re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        raise AssertionError(f"{name} not found")
    return _body(text, m.end() - 1)


def _rail_superseders():
    """The transport options the mod adds (bare definitions, not its REPLACEs of vanilla's) that rule out Rail."""
    text = _code(OPTIONS)
    found = set()
    for m in re.finditer(r"(?m)^(mobilization_option_\w+)\s*=\s*\{", text):
        body = _body(text, m.end() - 1)
        if not re.search(r"\bgroup\s*=\s*transport\b", body):
            continue
        nor = re.search(r"\bNOR\s*=\s*\{", body)
        if nor and f"has_mobilization_option = {RAIL}" in _body(body, nor.end() - 1):
            found.add(f"mobilization_option:{m.group(1)}")
    return found


class ButtonCopyTest(unittest.TestCase):
    def test_the_file_starts_with_one_bom(self):
        raw = (ROOT / BUTTONS).read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))

    def test_the_copy_is_vanilla_but_for_the_share_test(self):
        mod = load(BUTTONS)
        self.assertEqual(set(mod), {f"REPLACE:{BUTTON}"})
        mine = copy.deepcopy(mod[f"REPLACE:{BUTTON}"])
        possible = mine["possible"]
        self.assertEqual(possible.pop(TRIGGER), "yes")
        self.assertNotIn("army_mobilization_option_fraction", possible)
        # vanilla's line, back in its place (the parser keeps no operators, so value is the bare number)
        mine["possible"] = {}
        for key, value in possible.items():
            mine["possible"][key] = value
            if key == "has_technology_researched":
                mine["possible"]["army_mobilization_option_fraction"] = {"target": RAIL, "value": "0.75"}
        with open(ROOT / VANILLA_BUTTONS, encoding="utf-8") as f:
            vanilla = plain(json.load(f))[BUTTON]
        self.assertEqual(mine, vanilla)
        self.assertEqual(list(mine["possible"]), list(vanilla["possible"]), "the share test moved")

    def test_no_other_file_touches_the_button(self):
        hits = [p for p in (ROOT / "common").rglob("*.txt")
                if BUTTON + " =" in p.read_text(encoding="utf-8-sig", errors="replace")
                and p.relative_to(ROOT).as_posix() != BUTTONS]
        self.assertEqual(hits, [])


class ShareTriggerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trigger = _top(_code(TRIGGERS), TRIGGER)
        tooltip = re.search(r"\bcustom_tooltip\s*=\s*\{", cls.trigger)
        cls.ladder = _body(cls.trigger, tooltip.end() - 1)
        cls.singles = cls.trigger.replace(cls.ladder, "")

    def test_the_options_are_rail_and_every_mod_option_that_rules_it_out(self):
        superseders = _rail_superseders()
        self.assertIn("mobilization_option:mobilization_option_air_transport", superseders)
        self.assertIn("mobilization_option:mobilization_option_space_transport", superseders)
        singles = {target: value for target, value in _FRACTION.findall(self.singles)}
        self.assertEqual(set(singles), {RAIL} | superseders,
                         "a transport option that rules out Rail Transport is missing from the trigger")
        self.assertEqual(set(singles.values()), {"0.75"})

    def test_the_ladder_is_every_split_of_two_in_one_percent_steps(self):
        self.assertIn(f"text = {TOOLTIP}", self.ladder)
        options = sorted({RAIL} | _rail_superseders())
        rungs = re.findall(r"\bAND\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", self.ladder)
        found = set()
        for rung in rungs:
            pair = _FRACTION.findall(rung)
            self.assertEqual(len(pair), 2, rung)
            (a, x), (b, y) = pair
            self.assertEqual(round(float(x) * 100) + round(float(y) * 100), SHARE, rung)
            found.add((frozenset((a, b)), frozenset(((a, round(float(x) * 100)), (b, round(float(y) * 100))))))
        expected = set()
        for a, b in itertools.combinations(options, 2):
            for x in range(1, SHARE):
                expected.add((frozenset((a, b)), frozenset(((a, x), (b, SHARE - x)))))
        self.assertEqual(found, expected)
        self.assertEqual(len(rungs), len(expected), "a rung is written twice")

    def test_the_tooltip_has_loc(self):
        loc = "".join(p.read_text(encoding="utf-8-sig") for p in (ROOT / "localization" / "english").rglob("*.yml"))
        self.assertRegex(loc, r"(?m)^ " + TOOLTIP + r':0 "')


if __name__ == "__main__":
    unittest.main()
