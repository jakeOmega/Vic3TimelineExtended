"""The Healthcare pop need (drugs phase 2): its curve, its generated buy
packages, its definition, and Leisure without Drugs.

The owner's target (2026-10-02, docs/testing/drugs-wealth-probe-results-2026-10-02.md,
"Decisions"): Pharmaceutical Industries are 1.5-2% of GDP in a modern rich
country, overwhelmingly from healthcare. That is about 3% of consumption, so
Healthcare holds about 3% of the buy package (a cost at base prices) from wealth
29 to 50, ramping up from wealth 16. Past 50 it rises linearly, so the share
falls but richer pops still buy more. Wealth 100-200 come from the curve itself,
not the power-law fit the generator uses for other needs.

Run: python3 -m unittest test_healthcare_need -v
"""
import re
import unittest
from pathlib import Path

from pop_needs_curves import (CURVES_PAST_99, NEED_CURVES, _extrapolate_power_law,
                              _extrapolation_params, healthcare_need)

ROOT = Path(__file__).resolve().parent
BUY_PACKAGES = ROOT / "common/buy_packages/00_buy_packages.txt"
POP_NEEDS = ROOT / "common/pop_needs/extra_pop_needs.txt"
ANCHORS = {15: 0, 20: 10, 25: 30, 30: 85, 35: 160, 40: 290, 45: 520, 50: 900}
SLOPE_PAST_50 = 76  # the 45-50 segment's slope, continued


def _blocks(text):
    """{wealth level: block text} for every wealth_N block."""
    out = {}
    for m in re.finditer(r"wealth_(\d+)\s*=\s*\{", text):
        depth, pos = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[pos], 0)
            pos += 1
        out[int(m.group(1))] = text[m.end():pos]
    return out


def _need_block(name):
    text = POP_NEEDS.read_text(encoding="utf-8-sig")
    m = re.search(rf"^{name}\s*=\s*\{{", text, re.M)
    if not m:
        return None
    depth, pos = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[pos], 0)
        pos += 1
    return text[m.end():pos]


class HealthcareCurve(unittest.TestCase):
    def test_owner_anchors(self):
        for wl, value in ANCHORS.items():
            self.assertEqual(healthcare_need(wl), value, wl)

    def test_nothing_below_wealth_16(self):
        for wl in range(1, 16):
            self.assertEqual(healthcare_need(wl), 0, wl)
        self.assertGreater(healthcare_need(16), 0)

    def test_linear_past_50(self):
        for wl in range(50, 200):
            self.assertEqual(healthcare_need(wl + 1) - healthcare_need(wl), SLOPE_PAST_50, wl)

    def test_never_falls_as_wealth_rises(self):
        values = [healthcare_need(wl) for wl in range(1, 201)]
        self.assertEqual(values, sorted(values))

    def test_registered_with_the_generator(self):
        self.assertIs(NEED_CURVES.get("popneed_healthcare"), healthcare_need)
        self.assertIn("popneed_healthcare", CURVES_PAST_99)


class Extrapolation(unittest.TestCase):
    """Wealth 100-200 come from a power-law fit over 90-99. CI can't rerun the
    generator (it reads the game's buy packages), so the fit rule is tested
    here directly."""

    WEALTH = list(range(90, 100))

    def test_flat_need_stays_flat(self):
        # A fit of a flat 60 returned 59.99..., which int() made 59.
        for flat in (26, 60, 216):
            a, b = _extrapolation_params(self.WEALTH, [flat] * 10)
            for wl in (100, 150, 200):
                self.assertEqual(int(_extrapolate_power_law(wl, a, b)), flat, (flat, wl))

    def test_rising_need_keeps_rising(self):
        y = [int(0.5 * wl ** 2) for wl in self.WEALTH]
        a, b = _extrapolation_params(self.WEALTH, y)
        self.assertGreater(_extrapolate_power_law(150, a, b), y[-1])


class GeneratedBuyPackages(unittest.TestCase):
    """common/buy_packages/00_buy_packages.txt is regenerated on every full
    /reload; these fail when the committed file lags the curve."""

    @classmethod
    def setUpClass(cls):
        cls.blocks = _blocks(BUY_PACKAGES.read_text(encoding="utf-8-sig"))

    def _needs(self, wl):
        body = "\n".join(line.split("#")[0] for line in self.blocks[wl].splitlines())
        return {k: int(v) for k, v in re.findall(r"(popneed_\w+)\s*=\s*(\d+)", body)}

    def _value(self, wl):
        return self._needs(wl).get("popneed_healthcare", 0)

    def test_every_level_follows_the_curve(self):
        for wl in range(1, 201):
            self.assertEqual(self._value(wl), healthcare_need(wl), wl)

    def test_about_three_percent_of_spending_from_29_to_50(self):
        # A need's value is its cost at base prices, so the share of a pop's
        # spending is the need's value over the package total.
        for wl in range(29, 51):
            needs = self._needs(wl)
            share = needs["popneed_healthcare"] / sum(needs.values())
            self.assertTrue(0.0275 <= share <= 0.0325, (wl, round(share, 4)))

    def test_share_falls_past_50(self):
        shares = []
        for wl in (50, 60, 80, 99):
            needs = self._needs(wl)
            shares.append(needs["popneed_healthcare"] / sum(needs.values()))
        self.assertEqual(shares, sorted(shares, reverse=True))


class NeedDefinition(unittest.TestCase):
    def test_drugs_only(self):
        block = _need_block("popneed_healthcare")
        self.assertIsNotNone(block, "popneed_healthcare missing from extra_pop_needs.txt")
        self.assertRegex(block, r"default\s*=\s*opium\b")
        self.assertEqual(re.findall(r"goods\s*=\s*(\w+)", block), ["opium"])



class LeisureWithoutDrugs(unittest.TestCase):
    """Leisure grows without limit with wealth; with Drugs in it, a market full
    of Pharmaceutical Industries' output would pull ever more of it into Drugs.
    Rich pops buy their Drugs through Healthcare instead."""

    VANILLA_REST = ["services", "fine_art", "small_arms", "aeroplanes", "automobiles",
                    "radios", "clippers", "steamers"]

    def test_replaced_without_drugs(self):
        block = _need_block("REPLACE:popneed_leisure")
        self.assertIsNotNone(block, "REPLACE:popneed_leisure missing from extra_pop_needs.txt")
        self.assertEqual(re.findall(r"goods\s*=\s*(\w+)", block), self.VANILLA_REST)
        self.assertRegex(block, r"default\s*=\s*services\b")


if __name__ == "__main__":
    unittest.main()
