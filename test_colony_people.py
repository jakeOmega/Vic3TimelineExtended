# -*- coding: utf-8 -*-
"""Colony people limit modules (Part B of #1954).

Design: docs/superpowers/specs/2026-11-22-colony-people-limit-modules-design.md.
Slots go and crews limit a colony's modules: a crew is 10,000 people (5,000
with Artificial Intelligence), the Habitat is the one capped module, the five
slot technologies make Habitats roomier, settlers are an open-ended amount
drawn from every state and billed in Launch Capacity, and an Administration
costs authority. These tests hold the generated and hand-written script to
that rule.
"""

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import gen_solar_sites as gss  # noqa: E402


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


class CrewTest(unittest.TestCase):
    """Design § 4.2: a crew is 10,000 people, 5,000 with Artificial
    Intelligence, read through the world's holder; AI no longer waives crews."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.triggers = _strip(_raw(str(gss.TRIGGERS_OUT)))
        cls.effects = _strip(_raw(str(gss.EFFECTS_OUT)))
        cls.gui = _raw("gui", "journal_entry_widgets", "space_race_widget.gui")
        cls.display = _strip(_raw("common", "script_values", "space_race_display_values.txt"))

    def test_a_crew_is_ten_thousand_halved_by_ai(self):
        self.assertEqual(gss.CREW_PER_LEVEL, 10000)
        self.assertEqual(gss.AI_CREW_PER_LEVEL, 5000)
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                per = _block(self.values, f"sr_site_crew_per_level_{k}")
                self.assertIn("value = 10000", per)
                self.assertIn(f"global_var:sr_site_holder_{k} ?= {{ has_technology_researched = artificial_intelligence }}",
                              per)
                self.assertIn("value = 5000", per)
                crews = _block(self.values, f"sr_site_crews_{k}")
                self.assertIn(f"divide = sr_site_crew_per_level_{k}", crews)
        self.assertNotRegex(self.values, r"(?m)^sr_site_crew_per_level = ")

    def test_ai_no_longer_waives_crews(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertNotIn("artificial_intelligence", _block(self.values, f"sr_site_staffing_{k}"))
                self.assertNotIn("artificial_intelligence", _block(self.effects, f"sr_mod_ai_plan_{k}"))
        self.assertNotIn("sr_disp_agi", self.gui)
        self.assertNotIn("je_space_race_widget_settlers_agi", self.gui)
        self.assertNotRegex(self.display, r"(?m)^sr_disp_agi = ")


if __name__ == "__main__":
    unittest.main()
