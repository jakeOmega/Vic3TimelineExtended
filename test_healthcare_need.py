"""The Healthcare pop need (drugs phase 2): its curve, its generated buy
packages and its definition.

The owner chose the curve from measured wealth distributions
(docs/testing/drugs-wealth-probe-results-2026-10-02.md, "Decisions"): nothing
below wealth 20, about 15 at 25, about 40 at 30, and a cap of 60 from 40 up, so
the ultra-wealthy buy no more than a pop at wealth 40. pop_needs_curves.py
extrapolates wealth 100-200 with a power-law fit over 90-99; the cap must
survive that fit.

Run: python3 -m unittest test_healthcare_need -v
"""
import re
import unittest
from pathlib import Path

import pop_needs_curves
from pop_needs_curves import NEED_CURVES, healthcare_need

ROOT = Path(__file__).resolve().parent
BUY_PACKAGES = ROOT / "common/buy_packages/00_buy_packages.txt"
POP_NEEDS = ROOT / "common/pop_needs/extra_pop_needs.txt"
CAP = 60


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
        self.assertEqual(healthcare_need(20), 0)
        self.assertEqual(healthcare_need(25), 15)
        self.assertEqual(healthcare_need(30), 40)
        self.assertEqual(healthcare_need(40), CAP)

    def test_nothing_below_wealth_21(self):
        for wl in range(1, 21):
            self.assertEqual(healthcare_need(wl), 0, wl)

    def test_flat_at_the_cap_from_40(self):
        for wl in range(40, 201):
            self.assertEqual(healthcare_need(wl), CAP, wl)

    def test_never_falls_as_wealth_rises(self):
        values = [healthcare_need(wl) for wl in range(1, 100)]
        self.assertEqual(values, sorted(values))

    def test_registered_with_the_generator(self):
        self.assertIs(NEED_CURVES.get("popneed_healthcare"), healthcare_need)
        self.assertIs(pop_needs_curves.healthcare_need, healthcare_need)


class GeneratedBuyPackages(unittest.TestCase):
    """common/buy_packages/00_buy_packages.txt is regenerated on every full
    /reload; these fail when the committed file lags the curve."""

    @classmethod
    def setUpClass(cls):
        cls.blocks = _blocks(BUY_PACKAGES.read_text(encoding="utf-8-sig"))

    def _value(self, wl):
        m = re.search(r"popneed_healthcare\s*=\s*(\d+)", self.blocks[wl])
        return int(m.group(1)) if m else 0

    def test_vanilla_levels_follow_the_curve(self):
        for wl in range(1, 100):
            self.assertEqual(self._value(wl), healthcare_need(wl), wl)

    def test_extrapolated_levels_stay_at_the_cap(self):
        for wl in range(100, 201):
            self.assertEqual(self._value(wl), CAP, wl)


class NeedDefinition(unittest.TestCase):
    def test_drugs_only(self):
        block = _need_block("popneed_healthcare")
        self.assertIsNotNone(block, "popneed_healthcare missing from extra_pop_needs.txt")
        self.assertRegex(block, r"default\s*=\s*opium\b")
        self.assertEqual(re.findall(r"goods\s*=\s*(\w+)", block), ["opium"])

    def test_no_obsession_fields(self):
        # Han's opium obsession multiplies demand only in needs that declare
        # these; healthcare must not inherit it (plan § 2).
        block = _need_block("popneed_healthcare")
        self.assertIsNotNone(block)
        self.assertNotIn("obsession_demand", block)


if __name__ == "__main__":
    unittest.main()
