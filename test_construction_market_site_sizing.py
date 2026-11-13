"""The weekly sizing of the Construction Sites never delivers many times the purchase.

In a market game the week's construction purchase is delivered by the country's Construction Sites
(te_construction_market_site, level 1, ten laborers): the weekly pulse gives each a throughput modifier, and a
site delivers its throughput times its staffing. The government queue spends whatever the sites deliver and the
treasury pays for it, so sizing past the purchase bills the player for construction they did not order.

Until 2026-11-13 each site got its share of the purchase divided by its own staffing, and a site under 10%
staffed got ten times its share. A site is placed unstaffed wherever construction starts, and its building group
hires at a rate of 1.0, so a site sized before its first hiring was full within days and delivered ten times
its share until the next pulse (a Workshop report: construction costing millions on a purchase of 50,000).

This runs the script's own text (common/script_values/te_construction_market_sector_placement_values.txt) with
the evaluator of test_construction_market_budget_step, extended with the one building iterator the chain uses,
and checks what the sites deliver once their staffing has moved, against the purchase.

Run: python3 -m unittest test_construction_market_site_sizing -v
"""
import itertools
import re
import unittest
from pathlib import Path

from test_construction_market_budget_step import parse_block, tokenize

ROOT = Path(__file__).resolve().parent
VALUES = ROOT / "common/script_values/te_construction_market_sector_placement_values.txt"
EFFECTS = ROOT / "common/scripted_effects/te_construction_market_update_effects.txt"
GROUPS = ROOT / "common/building_groups/te_construction_market_groups.txt"
SITE = "te_construction_market_site"
THROUGHPUT = "te_construction_market_site_throughput"
# The staffing a site can show at a pulse, and what it can reach before the next one.
STAFFINGS = (0.0, 0.05, 0.1, 0.19, 0.3, 0.5, 0.75, 0.99, 1.0)


def load_values():
    items, _ = parse_block(tokenize(VALUES.read_text(encoding="utf-8")), 0)
    return {key: value for key, _op, value in items}


class Evaluator:
    """Script values over a country whose sites have the given staffing (occupancy)."""

    def __init__(self, values, purchase, sites):
        self.values = values
        self.purchase = purchase
        self.sites = sites
        self.site = None  # the building in scope, inside the iterator

    def number(self, token):
        if isinstance(token, list):
            return self.block(token)
        if token == "te_construction_market_total_use_target":
            return self.purchase
        if token in self.values:
            return self.number(self.values[token])
        return float(token)

    def trigger(self, items):
        for key, op, value in items:
            if key == "occupancy":
                if self.site is None:
                    raise AssertionError("occupancy read outside a building's scope")
                left = self.site
            elif key == "is_building_type":
                if value != SITE:
                    return False
                continue
            else:
                left = self.number(key)
            right = self.number(value)
            ok = {">=": left >= right, "<=": left <= right, ">": left > right, "<": left < right,
                  "=": left == right}[op]
            if not ok:
                return False
        return True

    def block(self, items):
        total = 0.0
        for key, _op, value in items:
            if key == "value":
                total = self.number(value)
            elif key == "add":
                total += self.number(value)
            elif key == "subtract":
                total -= self.number(value)
            elif key == "multiply":
                total *= self.number(value)
            elif key == "divide":
                total /= self.number(value)
            elif key == "min":
                total = max(total, self.number(value))
            elif key == "max":
                total = min(total, self.number(value))
            elif key == "if":
                limit = next(v for k, _o, v in value if k == "limit")
                if self.trigger(limit):
                    rest = [item for item in value if item[0] != "limit"]
                    # An if block continues the running value.
                    total = self.block([("value", "=", repr(total))] + rest)
            elif key == "every_scope_building":
                limit = next((v for k, _o, v in value if k == "limit"), [])
                rest = [item for item in value if item[0] != "limit"]
                for staffing in self.sites:
                    self.site = staffing
                    if self.trigger(limit):
                        total = self.block([("value", "=", repr(total))] + rest)
                    self.site = None
            else:
                raise AssertionError("the evaluator does not know %r" % key)
            total = round(total, 5)
        return total


def delivered(values, purchase, at_pulse, later):
    """Points the sites deliver, sized at the pulse with staffing `at_pulse`, once staffing is `later`."""
    throughput = Evaluator(values, purchase, at_pulse).number(THROUGHPUT)
    # building_throughput_add on top of the engine's 1; a level-1 site makes 1 point at full staff.
    return sum((1 + throughput) * staffing for staffing in later)


class SiteSizingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = load_values()

    def test_the_site_group_hires_at_once(self):
        # The premise: a site goes from empty to full in one employment update, between two pulses.
        text = GROUPS.read_text(encoding="utf-8")
        self.assertRegex(text, r"min_hiring_rate\s*=\s*1\.0")
        self.assertRegex(text, r"max_hiring_rate\s*=\s*1\.0")

    def test_fully_staffed_sites_deliver_the_purchase(self):
        for count, purchase in itertools.product((1, 2, 5), (0.5, 50, 5000)):
            sites = [1.0] * count
            with self.subTest(count=count, purchase=purchase):
                self.assertAlmostEqual(delivered(self.values, purchase, sites, sites), purchase, places=2)

    def test_a_site_sized_before_it_hires_delivers_its_share_once_full(self):
        # The reported case: construction starts in a new state, the capital's site leaves, and the pulse
        # sizes the one new site before its first hiring.
        self.assertAlmostEqual(delivered(self.values, 50, [0.0], [1.0]), 50, places=2)
        # And beside established sites.
        self.assertAlmostEqual(delivered(self.values, 50, [1.0, 0.0, 0.0], [1.0, 1.0, 1.0]), 50, places=2)

    def test_no_change_in_staffing_within_the_week_delivers_more_than_twice_the_purchase(self):
        for count in (1, 2, 3):
            for at_pulse in itertools.product(STAFFINGS, repeat=count):
                # The worst week: every site full before the next pulse.
                full = [1.0] * count
                with self.subTest(at_pulse=at_pulse):
                    self.assertLessEqual(delivered(self.values, 100, list(at_pulse), full), 200.01)

    def test_steady_staffing_never_delivers_much_more_than_the_purchase(self):
        # The staircase reads a site's staffing down to the tenth below, so a site between two steps is made
        # up for a little too much: at most the 0.59 a 0.5 reading can hide.
        for count in (1, 2, 3):
            for staffing in itertools.product(STAFFINGS, repeat=count):
                with self.subTest(staffing=staffing):
                    self.assertLessEqual(delivered(self.values, 100, list(staffing), list(staffing)), 120)

    def test_a_site_short_of_laborers_is_made_up_for(self):
        # Half staffed and staying so: the purchase still arrives.
        self.assertAlmostEqual(delivered(self.values, 50, [0.5], [0.5]), 50, places=2)
        self.assertAlmostEqual(delivered(self.values, 50, [1.0, 0.5], [1.0, 0.5]), 50, places=2)

    def test_no_site_and_no_purchase(self):
        self.assertEqual(Evaluator(self.values, 50, []).number(THROUGHPUT), 0)
        # No purchase: throughput -100%, so the sites deliver, and buy, nothing.
        self.assertEqual(delivered(self.values, 0, [1.0], [1.0]), 0)


class SizingEffectTest(unittest.TestCase):
    def setUp(self):
        text = EFFECTS.read_text(encoding="utf-8")
        text = "\n".join(line.split("#", 1)[0] for line in text.lstrip("﻿").splitlines())
        start = text.index("te_construction_market_apply_per_site_modifier = {")
        self.body = text[start:text.index("\n}", start)]

    def test_every_site_reads_one_country_value(self):
        # One value, written once before the walk: a per-site value in a shared country variable let every
        # site re-read the last site's between pulses.
        self.assertEqual(len(re.findall(r"name\s*=\s*te_cm_capacity_mult", self.body)), 1)
        write = self.body.index("te_cm_capacity_mult")
        self.assertLess(write, self.body.index("every_scope_building"))
        self.assertRegex(self.body, r"value\s*=\s*%s\b" % THROUGHPUT)
        self.assertRegex(self.body, r"multiplier\s*=\s*owner\.var:te_cm_capacity_mult")

    def test_the_variable_outlives_the_effect(self):
        # The engine re-evaluates the multiplier expression on later ticks.
        self.assertNotIn("remove_variable = te_cm_capacity_mult", self.body)


if __name__ == "__main__":
    unittest.main()
