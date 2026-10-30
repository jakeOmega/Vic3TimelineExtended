# -*- coding: utf-8 -*-
"""The UN proposal pace's two marks run for literal durations.

Tabling a resolution adds the sponsor mark (``un_ga_resolution_modifier``, five
years at the base pace) and the bar on the next own-motion proposal
(``un_request_cooldown``, ten), each for its base times ``un_propose_pace_mult``.
They once took ``days = un_propose_sponsor_days`` / ``un_propose_cooldown_days``,
script values that computed that product, and ``add_modifier``'s ``days`` reads
a computed script value as 0 (``scripting_best_practices.md``, "Modifier &
Cooldown Duration Units"). ``un_propose_add_sponsor_mark`` and
``un_propose_add_request_cooldown`` now branch over the multiplier's values with
a literal each. These tests recompute the values from the tuning, so a retuned
multiplier fails here until the ladders follow.

Run: python3 -m unittest test_un_propose_pace -v
"""

import glob
import json
import math
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
PACE_VALUES = os.path.join(REPO, "common", "script_values", "un_propose_pace_values.txt")
UN_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_propose_effects.txt")
VANILLA_VALUES = os.path.join(REPO, "vanilla_parsed", "common", "script_values.json")

# The two ladders: the helper, the modifier it adds, and the vanilla script
# value its base duration was.
LADDERS = {
    "un_propose_add_sponsor_mark": ("un_ga_resolution_modifier", "normal_modifier_time"),
    "un_propose_add_request_cooldown": ("un_request_cooldown", "long_modifier_time"),
}
TIER_FACTORS = ("un_propose_pace_exemplary", "un_propose_pace_respected",
                "un_propose_pace_poor", "un_propose_pace_disgraced")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    assert m, f"{name} not found"
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def _constant(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{\s*value\s*=\s*(-?[\d.]+)\s*\}", text, re.M)
    assert m, f"{name} is not a one-line constant"
    return float(m.group(1))


def _vanilla(name):
    with open(VANILLA_VALUES, encoding="utf-8") as f:
        op, value = json.load(f)[name]
    assert op == "=", name
    return float(value)


def _nearest_day(x):
    return math.floor(x + 0.5)


class PaceLadderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = _read(PACE_VALUES)
        cls.effects = _read(UN_EFFECTS)
        gp = _constant(cls.values, "un_propose_pace_great_power")
        tiers = [_constant(cls.values, name) for name in TIER_FACTORS]
        floor = _constant(cls.values, "un_propose_pace_floor")
        # A great power's factor or none, times one standing tier or none
        # (Neutral, or a positive tier with its benefits suspended).
        cls.reachable = sorted({round(max(g * t, floor), 6) for g in (1, gp) for t in [1, *tiers]})
        cls.min_days = _constant(cls.values, "un_propose_min_days")

    def test_the_multiplier_has_the_factors_the_ladders_assume(self):
        body = _block(self.values, "un_propose_pace_mult")
        self.assertEqual(re.findall(r"\bvalue = (\S+)", body), ["1"])
        self.assertEqual(sorted(re.findall(r"\bmultiply = (\w+)", body)),
                         sorted(["un_propose_pace_great_power", *TIER_FACTORS]))
        self.assertEqual(re.findall(r"\b(min|max) = (\w+)", body), [("min", "un_propose_pace_floor")])

    def test_each_band_holds_one_value_and_its_duration(self):
        for helper, (modifier, base_name) in LADDERS.items():
            base = _vanilla(base_name)
            body = _block(self.effects, helper)
            # Each branch also mirrors its days in a variable the panel counts
            # down (the 2026-10-27 audit, UN-8); the mirror holds the same days.
            branches = re.findall(
                r"\b(if|else_if|else) = \{\s*"
                r"(?:limit = \{ un_propose_pace_mult < ([\d.]+) \}\s*)?"
                r"add_modifier = \{ name = (\w+) days = (\d+) is_decaying = yes \}\s*"
                r"set_variable = \{ name = \w+_days value = (\d+) \}\s*\}",
                body)
            self.assertEqual(len(branches), len(re.findall(r"\badd_modifier\b", body)), helper)
            self.assertEqual([b[0] for b in branches],
                             ["if"] + ["else_if"] * (len(self.reachable) - 2) + ["else"], helper)
            lower = 0.0
            for kind, upper, name, days, mirror in branches:
                self.assertEqual(days, mirror, helper)
                upper = float(upper) if upper else math.inf
                inside = [m for m in self.reachable if lower <= m < upper]
                with self.subTest(helper=helper, band=(lower, upper)):
                    self.assertEqual(name, modifier)
                    self.assertEqual(len(inside), 1, f"{inside} in [{lower}, {upper})")
                    self.assertEqual(int(days), _nearest_day(max(base * inside[0], self.min_days)))
                lower = upper

    def test_the_base_pace_is_five_and_ten_years(self):
        for helper, years in (("un_propose_add_sponsor_mark", 5), ("un_propose_add_request_cooldown", 10)):
            body = _block(self.effects, helper)
            m = re.search(r"un_propose_pace_mult < 1\.\d+ \}\s*add_modifier = \{ name = \w+ days = (\d+)", body)
            self.assertIsNotNone(m, helper)
            self.assertEqual(int(m.group(1)), years * 365)

    def test_every_site_goes_through_the_helpers(self):
        """No other add of either mark, so none can drift from the pace."""
        for path in sorted(glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True)
                           + glob.glob(os.path.join(REPO, "events", "**", "*.txt"), recursive=True)):
            text = _read(path)
            for modifier in ("un_ga_resolution_modifier", "un_request_cooldown"):
                adds = len(re.findall(r"\badd_modifier = \{\s*name = " + modifier + r"\b", text))
                if path == UN_EFFECTS:
                    adds -= sum(_block(text, h).count(f"name = {modifier} ") for h in LADDERS)
                with self.subTest(path=os.path.relpath(path, REPO), modifier=modifier):
                    self.assertEqual(adds, 0)


if __name__ == "__main__":
    unittest.main()
