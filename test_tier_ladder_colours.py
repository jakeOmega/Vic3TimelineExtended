"""A tier ladder's colors run one way, worst to best: red, gold, yellow, white, green, blue (Banking's phases).

The owner, 2026-11-24, on Cultural Hegemony's tiers reading red, plain, yellow, yellow, green, green: "make the
color tiering of the banking phases the canonical one". Banking's Cycle Phase cell prints Panic red, Downturn
gold, Stagnation yellow, Stable white, Expansion green, Boom blue and Frenzy red again, and its history chart
colors each month's bar the same. The rule is `docs/guides/scripting_best_practices.md` § "A Tier Ladder's
Colors Run Red, Gold, Yellow, White, Green, Blue".

Each ladder below lists its keys worst to best (a two-sided one: its healthy middle, then each side outward),
and the test holds the color of the word each key prints to the rule:

- one-sided: the colors never step back toward red (neighbours may share one, rungs may skip one);
- two-sided: on each side, from the middle out, a rung is never calmer than the one before, and the far end
  is red;
- weight: every rung is in the ladder's weight, the bold set (`#R`, `#bold;gold`, `#bold;yellow`, `#v`, `#G`,
  `#blue_value`) or the plain one (`#red`, `#gold`, `#yellow`, `#white`, `#green`, `#blue`). An unformatted
  word counts as plain white, so it fits a plain ladder; in a bold one only an alert's calm top rung may be
  unformatted (`calm_plain`).

The color is read from the first format in the value that names one, so a label before the word
(`#bold Warming:#! #o Significant#!`) does not count. A ladder that is not a scale (a mode, a category, an
outcome) does not belong here: the PR that added this test (gui/tier-colours) lists those it left alone.
To add a ladder, list its keys worst to best in ONE_SIDED, or its middle and both sides in TWO_SIDED.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOC_DIR = ROOT / "localization" / "english"

# The scale, worst to best, and the two weights each color comes in.
CANON = ["red", "gold", "yellow", "white", "green", "blue"]
RANK = {c: i for i, c in enumerate(CANON)}
# How alarming a color reads; white, green and blue are all calm.
ALARM = {"red": 3, "gold": 2, "yellow": 1, "white": 0, "green": 0, "blue": 0}

# A format name, lower-cased as the engine matches it, to (color, bold).
FORMATS = {
    "r": ("red", True), "n": ("red", True), "negative_value": ("red", True), "red": ("red", False),
    "gold_value": ("gold", True), "o": ("gold", False), "gold": ("gold", False),
    "yellow": ("yellow", False),
    "v": ("white", True), "variable": ("white", True), "y": ("white", True), "zero_value": ("white", True),
    "white": ("white", False),
    "g": ("green", True), "p": ("green", True), "positive_value": ("green", True), "green": ("green", False),
    "blue_value": ("blue", True), "blue": ("blue", False),
}
_TAG = re.compile(r"#([A-Za-z_]+(?:;[A-Za-z_]+)*)[ ]")
_LOC_LINE = re.compile(r'\s*([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$')

# name: (weight, keys worst to best, calm_plain)
ONE_SIDED: dict[str, tuple[str, list[str], bool]] = {
    "Cultural Hegemony: influence tier": ("bold", [
        "ch_tier_negligible", "ch_tier_minor", "ch_tier_moderate", "ch_tier_significant", "ch_tier_major",
        "ch_tier_hegemon"], False),
    "Banking: Bubble Pressure": ("plain", [
        "banking_dash_bubble_band_severe", "banking_dash_bubble_band_high", "banking_dash_bubble_band_elevated",
        "banking_dash_bubble_band_building", "banking_dash_bubble_band_low"], False),
    "Banking: peg confidence band": ("bold", [
        "banking_dash_mon_peg_state_breaking", "banking_dash_mon_peg_state_doubted",
        "banking_dash_mon_peg_state_watched", "banking_dash_mon_peg_state_trusted"], False),
    "UN: Authority, overview": ("bold", [f"je_un_ov_tier_{i}" for i in range(5)], False),
    "UN: Authority, tier line": ("bold", [
        "je_un_tier_line_moribund", "je_un_tier_line_contested", "je_un_tier_line_established",
        "je_un_tier_line_strong", "je_un_tier_line_supranational"], False),
    "UN: Standing, overview": ("bold", [f"je_un_ov_standing_{i}" for i in range(2, 7)], False),
    "UN: Standing, tier line": ("bold", [
        "je_un_standing_tier_disgraced", "je_un_standing_tier_poor", "je_un_standing_tier_neutral",
        "je_un_standing_tier_respected", "je_un_standing_tier_exemplary"], False),
    "UN: case against us": ("bold", [f"je_un_ov_record_{i}" for i in (3, 2, 1, 0)], False),
    "Global Warming: status": ("bold", [
        f"je_global_warming_status_{t}" for t in
        ("apocalyptic", "catastrophic", "severe", "significant", "moderate", "slight", "negligible")], False),
    "Global Warming: overview tier": ("bold", [
        f"gw_tier_short_{t}" for t in
        ("apocalyptic", "catastrophic", "severe", "significant", "moderate", "slight", "negligible")], False),
    "Covert: counterintelligence status": ("bold", [
        f"je_iw_status_{t}" for t in ("vulnerable", "exposed", "defended", "hardened", "fortress")], False),
    "Colonial Empire: band": ("bold", [
        f"je_colonial_empire_band_{t}" for t in ("collapsing", "crumbling", "strained", "stable", "solidified")],
        False),
    "Colonial Empire: status, ours": ("bold", [
        "je_colonial_empire_status_collapsing_ours", "je_colonial_empire_status_crumbling",
        "je_colonial_empire_status_strained_ours", "je_colonial_empire_status_stable",
        "je_colonial_empire_status_solidified"], False),
    "Colonial Empire: status, theirs": ("bold", [
        "je_colonial_empire_status_collapsing_theirs", "je_colonial_empire_status_crumbling",
        "je_colonial_empire_status_strained_theirs", "je_colonial_empire_status_stable",
        "je_colonial_empire_status_solidified"], False),
    "Colonial Empire: pressure, overview": ("bold", [
        "je_colonial_empire_ov_consensus", "je_colonial_empire_ov_isolation", "je_colonial_empire_ov_gp_calm"],
        True),
    "Colonial Empire: pressure": ("bold", [
        "je_colonial_empire_pressure_consensus", "je_colonial_empire_pressure_isolation",
        "je_colonial_empire_pressure_none_ours"], False),
    "Nuclear: danger": ("bold", [f"nd_danger_word_{i}" for i in (3, 2, 1, 0)], False),
    "Nuclear: risk": ("bold", [f"nd_risk_band_{i}" for i in (4, 3, 2, 1, 0)], False),
    "Nuclear: credibility": ("bold", [
        "nd_credibility_band_low", "nd_credibility_band_mid", "nd_credibility_band_high"], False),
    "Nuclear: doctrine word": ("bold", ["nd_ft_word_bluff", "nd_ft_word_uncertain", "nd_ft_word_backed"], False),
    "Strategic Reserve: Blocked cell": ("bold", [
        "je_strategic_reserve_ov_held_word_empty", "je_strategic_reserve_ov_held_word_full",
        "je_strategic_reserve_ov_held_word_none"], False),
}

# name: (weight or None, middle, down side outward, up side outward). A None weight leaves the ladder's
# weight unchecked, with the reason beside it.
TWO_SIDED: dict[str, tuple[str | None, str, list[str], list[str]]] = {
    "Banking: Cycle Phase": ("plain", "banking_dash_phase_stable_value", [
        "banking_dash_phase_stagnation_value", "banking_dash_phase_downturn_value", "banking_dash_phase_panic_value"],
        ["banking_dash_phase_expansion_value", "banking_dash_phase_boom_value", "banking_dash_phase_frenzy_value"]),
    # Bold #R / #G at its ends and plain gold and yellow between, kept as it is (PR #2031's coordinator call:
    # its yellow matches the plain words of the Cycle Phase and Bubble cells beside it).
    "Banking: Momentum": (None, "banking_dash_momentum_band_steady", [
        "banking_dash_momentum_band_falling", "banking_dash_momentum_band_collapsing",
        "banking_dash_momentum_band_freefall"],
        ["banking_dash_momentum_band_rising", "banking_dash_momentum_band_surging",
         "banking_dash_momentum_band_overheating"]),
}

# The canon itself: Banking's phases, Panic to Boom, print the six colors in order, and Cultural Hegemony's
# six tiers take them all.
EXACT: dict[str, tuple[list[str], list[str]]] = {
    "Banking: Cycle Phase, Panic to Boom": ([
        "banking_dash_phase_panic_value", "banking_dash_phase_downturn_value", "banking_dash_phase_stagnation_value",
        "banking_dash_phase_stable_value", "banking_dash_phase_expansion_value", "banking_dash_phase_boom_value"],
        CANON),
    "Banking: Bubble Pressure": (ONE_SIDED["Banking: Bubble Pressure"][1], CANON[:5]),
    "Cultural Hegemony: influence tier": (ONE_SIDED["Cultural Hegemony: influence tier"][1], CANON),
}


def word_format(value: str) -> tuple[str, bool, bool]:
    """(color, bold, formatted) of the word `value` prints: its first format that names a color, or plain white
    for a value with none."""
    for header in _TAG.findall(value):
        names = [n.lower() for n in header.split(";")]
        colors = [FORMATS[n] for n in names if n in FORMATS]
        if colors:
            color, bold = colors[0]
            return color, bold or "bold" in names or "b" in names, True
    return "white", False, False


def one_sided_problems(values: list[tuple[str, str]], weight: str, calm_plain: bool = False) -> list[str]:
    """What breaks the rule in a ladder of (key, value), worst to best."""
    out = []
    fmts = [(key, *word_format(value)) for key, value in values]
    for (k1, c1, _b1, _f1), (k2, c2, _b2, _f2) in zip(fmts, fmts[1:]):
        if RANK[c2] < RANK[c1]:
            out.append(f"{k2} ({c2}) is better than {k1} ({c1}) but draws more alarming")
    out += weight_problems(fmts, weight, calm_plain)
    return out


def weight_problems(fmts: list[tuple[str, str, bool, bool]], weight: str, calm_plain: bool = False) -> list[str]:
    out = []
    for i, (key, _color, bold, formatted) in enumerate(fmts):
        if weight == "bold" and not formatted and calm_plain and i == len(fmts) - 1:
            continue
        if bold != (weight == "bold"):
            how = "bold" if bold else ("unformatted" if not formatted else "plain")
            out.append(f"{key} is {how} in a {weight} ladder")
    return out


def two_sided_problems(middle: tuple[str, str], down: list[tuple[str, str]], up: list[tuple[str, str]],
                       weight: str | None) -> list[str]:
    out = []
    mid = (middle[0], *word_format(middle[1]))
    if ALARM[mid[1]]:
        out.append(f"the middle, {mid[0]}, draws a warning color ({mid[1]})")
    for side in (down, up):
        fmts = [mid] + [(key, *word_format(value)) for key, value in side]
        for (k1, c1, _b1, _f1), (k2, c2, _b2, _f2) in zip(fmts, fmts[1:]):
            if ALARM[c2] < ALARM[c1]:
                out.append(f"{k2} ({c2}) is further from the middle than {k1} ({c1}) but draws calmer")
        if fmts[-1][1] != "red":
            out.append(f"{fmts[-1][0]}, the far end, is {fmts[-1][1]}, not red")
    if weight is not None:
        every = [mid] + [(key, *word_format(value)) for key, value in down + up]
        out += weight_problems(every, weight)
    return out


def _loc() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(LOC_DIR.glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = _LOC_LINE.match(line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


class TierLadderColourTests(unittest.TestCase):
    loc: dict[str, str]

    @classmethod
    def setUpClass(cls):
        cls.loc = _loc()

    def _values(self, keys: list[str]) -> list[tuple[str, str]]:
        missing = [k for k in keys if k not in self.loc]
        self.assertFalse(missing, f"keys gone from localization/english (renamed? update the ladder): {missing}")
        return [(k, self.loc[k]) for k in keys]

    def test_one_sided_ladders_run_worst_to_best(self):
        for name, (weight, keys, calm_plain) in ONE_SIDED.items():
            with self.subTest(ladder=name):
                self.assertEqual(one_sided_problems(self._values(keys), weight, calm_plain), [])

    def test_two_sided_ladders_grow_more_alarming_outward(self):
        for name, (weight, middle, down, up) in TWO_SIDED.items():
            with self.subTest(ladder=name):
                (mid,) = self._values([middle])
                self.assertEqual(two_sided_problems(mid, self._values(down), self._values(up), weight), [])

    def test_banking_and_cultural_hegemony_print_the_canon(self):
        for name, (keys, colors) in EXACT.items():
            with self.subTest(ladder=name):
                self.assertEqual([word_format(v)[0] for _k, v in self._values(keys)], colors)


class CheckerTests(unittest.TestCase):
    """The checks catch what they are for."""

    def test_the_old_cultural_hegemony_ladder_fails(self):
        old = ["#R Negligible#!", "Minor", "#bold;yellow Moderate#!", "#bold;yellow Significant#!", "#G Major#!",
               "#G Hegemon#!"]
        problems = one_sided_problems([(f"k{i}", v) for i, v in enumerate(old)], "bold")
        self.assertIn("k2 (yellow) is better than k1 (white) but draws more alarming", problems)
        self.assertIn("k1 is unformatted in a bold ladder", problems)

    def test_a_plain_gold_in_a_bold_ladder_fails(self):
        problems = one_sided_problems([("a", "#R x#!"), ("b", "#o y#!"), ("c", "#G z#!")], "bold")
        self.assertEqual(problems, ["b is plain in a bold ladder"])

    def test_a_label_before_the_word_is_skipped(self):
        self.assertEqual(word_format("#bold Warming:#! #bold;gold Significant#! - text"), ("gold", True, True))
        self.assertEqual(word_format("Status: #R Contested#!"), ("red", True, True))
        self.assertEqual(word_format("Steady"), ("white", False, False))

    def test_shared_and_skipped_colors_pass(self):
        ladder = [("a", "#R x#!"), ("b", "#R y#!"), ("c", "#bold;yellow z#!"), ("d", "#G w#!")]
        self.assertEqual(one_sided_problems(ladder, "bold"), [])

    def test_an_alert_may_leave_its_calm_plain(self):
        ladder = [("a", "#R x#!"), ("b", "#bold;gold y#!"), ("c", "No escalation")]
        self.assertEqual(one_sided_problems(ladder, "bold", calm_plain=True), [])
        self.assertEqual(one_sided_problems(ladder, "bold"), ["c is unformatted in a bold ladder"])

    def test_a_two_sided_scale_calmer_outward_fails(self):
        problems = two_sided_problems(("m", "Steady"), [("d1", "#gold a#!"), ("d2", "#yellow b#!")],
                                      [("u1", "#green c#!"), ("u2", "#red d#!")], "plain")
        self.assertIn("d2 (yellow) is further from the middle than d1 (gold) but draws calmer", problems)
        self.assertIn("d2, the far end, is yellow, not red", problems)


if __name__ == "__main__":
    unittest.main()
