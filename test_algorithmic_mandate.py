# -*- coding: utf-8 -*-
"""Algorithmic Governance's legitimacy: a flat base plus the Algorithmic Mandate.

The law is a Distribution of Power law with no clout, votes or head-of-state
term, so it has no legitimacy of its own beyond the base it carries, and the
mandate (algorithmic_mandate_value, 5 per point of the SoL expectations gap,
capped at +-40) is an adjustment on top of that base. Play-testing #623 found a
country on Algorithmic Governance in Unstable Government with the mandate at its
old +25 cap; a first fix (base 50, cap 25) still peaked at 92 on very low taxes,
short of the 100 the other laws reach with room to spare for higher taxes. So the
test pins headroom (base plus cap) as well as the two numbers.

The law's tooltip quotes the mandate's rate and cap by hand, and nothing in the
engine checks that the loc and the script value agree. This pins them.

Spec: docs/superpowers/specs/2026-10-01-bureaucracy-laws-design.md

Run: python3 -m unittest test_algorithmic_mandate -v
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

LAWS = os.path.join(REPO, "common", "laws", "extra_laws.txt")
SCRIPT_VALUES = os.path.join(REPO, "common", "script_values", "extra_script_values.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

TOOLTIP_KEY = "ALGORITHMIC_GOVERNANCE_TT_MANDATE"
# Dropped when the tooltip was replaced: Automated Bureaucracy's installation is
# already the "enables law" line the engine writes from on_activate.
RETIRED_TOOLTIP_KEY = "ALGORITHMIC_GOVERNANCE_TT_INSTALLS_AUTOMATED_BUREAUCRACY"


def _read(path):
    """Script text with comments stripped (not for loc: `#b` is markup there)."""
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
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _inner(text, name):
    m = re.search(r"(?<![\w.:])" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _loc():
    out = {}
    line = re.compile(r'^\s*([\w.]+):\d*\s*"(.*)"\s*$')
    for name in os.listdir(LOC_DIR):
        if name.endswith(".yml"):
            with open(os.path.join(LOC_DIR, name), encoding="utf-8-sig") as f:
                for text in f:
                    m = line.match(text)
                    if m:
                        out[m.group(1)] = m.group(2)
    return out


class MandateValueTests(unittest.TestCase):
    def setUp(self):
        self.body = _block(_read(SCRIPT_VALUES), "algorithmic_mandate_value")

    def test_reads_the_cached_gap(self):
        self.assertIn("value = var:sol_expectations_gap_cached", self.body)

    def test_rate_and_cap(self):
        self.assertEqual(float(re.search(r"multiply\s*=\s*(-?[\d.]+)", self.body).group(1)), 5)
        self.assertEqual(float(re.search(r"\bmax\s*=\s*(-?[\d.]+)", self.body).group(1)), 40)
        self.assertEqual(float(re.search(r"\bmin\s*=\s*(-?[\d.]+)", self.body).group(1)), -40)


class LawTests(unittest.TestCase):
    def setUp(self):
        self.law = _block(_read(LAWS), "law_algorithmic_governance")
        self.modifier = _inner(self.law, "modifier")

    def _base(self):
        m = re.search(r"country_legitimacy_base_add\s*=\s*(-?[\d.]+)", self.modifier)
        self.assertIsNotNone(m, "no legitimacy base: the mandate alone leaves the country in Unstable Government")
        return float(m.group(1))

    def test_carries_a_flat_legitimacy_base(self):
        self.assertGreaterEqual(self._base(), 70)

    def test_base_plus_mandate_cap_leaves_headroom_over_100(self):
        # Taxes (tax_modifier_*: +10 very low, 0 medium, -10 high, -20 very high),
        # a head of state's group and timed modifiers are added to this, and
        # legitimacy tops out at 100: a boom must reach it with room to absorb
        # them (92 on very low taxes was reported short).
        body = _block(_read(SCRIPT_VALUES), "algorithmic_mandate_value")
        cap = float(re.search(r"\bmax\s*=\s*(-?[\d.]+)", body).group(1))
        self.assertGreaterEqual(self._base() + cap, 110)

    def test_tooltip_is_the_mandate_explainer(self):
        on_enact = " ".join(_inner(self.law, "on_enact").split())
        self.assertEqual(on_enact, f"custom_tooltip = {TOOLTIP_KEY}")
        self.assertNotIn(RETIRED_TOOLTIP_KEY, self.law)

    def test_still_installs_automated_bureaucracy(self):
        # What the retired tooltip said; the engine's own "enables law" line now carries it.
        self.assertIn("activate_law = law_type:law_automated_bureaucracy", _inner(self.law, "on_activate"))


class LocTests(unittest.TestCase):
    def setUp(self):
        self.loc = _loc()

    def test_keys(self):
        self.assertIn(TOOLTIP_KEY, self.loc)
        self.assertNotIn(RETIRED_TOOLTIP_KEY, self.loc)

    def test_tooltip_quotes_the_script_values(self):
        text = self.loc[TOOLTIP_KEY]
        self.assertIn("#v +5#!", text)
        self.assertIn("#v -5#!", text)
        self.assertIn("#v 40#!", text)
        self.assertIn("[concept_sol_expectations]", text)

    def test_modifier_has_loc(self):
        for key in ("algorithmic_mandate", "algorithmic_mandate_desc"):
            with self.subTest(key=key):
                self.assertIn(key, self.loc)


if __name__ == "__main__":
    unittest.main()
