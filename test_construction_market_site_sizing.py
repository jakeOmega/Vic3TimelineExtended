"""The weekly sizing of the Construction Sites never delivers many times the purchase.

In a market game the week's construction purchase is delivered by the country's Construction Sites
(te_construction_market_site, level 1, ten laborers): the weekly pulse gives each a throughput modifier, and a
site delivers its throughput times its staffing. The government queue spends whatever the sites deliver and the
treasury pays for it, so sizing past the purchase bills the player for construction they did not order.

Until 2026-11-13 each site got its share of the purchase divided by its own staffing, and a site under 10%
staffed got ten times its share. A site is placed unstaffed wherever construction starts, and its building group
hires at a rate of 1.0, so a site sized before its first hiring was full within days and delivered ten times
its share until the next pulse (a Workshop report: construction costing millions on a purchase of 50,000).

Now every site carries one throughput, the purchase over the country's site levels, and staffing is not read
(owner, 2026-11-13): a site is taken to be fully staffed or about to be, which its hiring rate and a large job
attractiveness on its method are there to make true. The sites can then never deliver more than the purchase.

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
PMS = ROOT / "common/production_methods/te_construction_market_pms.txt"
SITE = "te_construction_market_site"
THROUGHPUT = "te_construction_market_site_throughput"
# The staffing a site can show at a pulse, and what it can reach before the next one.
STAFFINGS = (0.0, 0.05, 0.1, 0.19, 0.3, 0.5, 0.75, 0.99, 1.0)


def load_values():
    items, _ = parse_block(tokenize(VALUES.read_text(encoding="utf-8")), 0)
    return {key: value for key, _op, value in items}


class Evaluator:
    """Script values over a country whose sites have the given staffing (occupancy)."""

    def __init__(self, values, purchase, sites, levels=None):
        self.values = values
        self.purchase = purchase
        self.sites = sites
        self.levels = levels or [1] * len(sites)
        self.site = None  # the staffing of the building in scope, inside the iterator
        self.level = None  # and its level

    def number(self, token):
        if isinstance(token, list):
            return self.block(token)
        if token == "te_construction_market_total_use_target":
            return self.purchase
        if token == "level":
            if self.level is None:
                raise AssertionError("level read outside a building's scope")
            return self.level
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
                for staffing, level in zip(self.sites, self.levels):
                    self.site, self.level = staffing, level
                    if self.trigger(limit):
                        total = self.block([("value", "=", repr(total))] + rest)
                    self.site = self.level = None
            else:
                raise AssertionError("the evaluator does not know %r" % key)
            total = round(total, 5)
        return total


def delivered(values, purchase, at_pulse, later, levels=None):
    """Points the sites deliver, sized at the pulse with staffing `at_pulse`, once staffing is `later`."""
    levels = levels or [1] * len(later)
    throughput = Evaluator(values, purchase, at_pulse, levels).number(THROUGHPUT)
    # building_throughput_add on top of the engine's 1; a site makes 1 point a level at full staff.
    return sum((1 + throughput) * staffing * level for staffing, level in zip(later, levels))


class SiteSizingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = load_values()

    def test_the_site_fills_and_stays_filled(self):
        # What the sizing rests on, since it reads no staffing: the group hires a site from empty to full in
        # one employment update, and the market method makes the job very attractive, as the Grid Transfer
        # Station's does.
        text = GROUPS.read_text(encoding="utf-8")
        self.assertRegex(text, r"min_hiring_rate\s*=\s*1\.0")
        self.assertRegex(text, r"max_hiring_rate\s*=\s*1\.0")
        pms = "\n".join(line.split("#", 1)[0] for line in PMS.read_text(encoding="utf-8").splitlines())
        start = pms.index("pm_te_construction_market_base = {")
        market = pms[start:pms.index("\npm_te_direct_construction_wooden = {")]
        self.assertRegex(market, r"unscaled\s*=\s*\{\s*building_job_attractiveness_mult\s*=\s*5\s*\}")
        # Not the direct methods: there the site is a sector with a real workforce.
        self.assertEqual(pms.count("building_job_attractiveness_mult"), 1)

    def test_the_sizing_reads_no_staffing(self):
        # Owner, 2026-11-13: no scaling with employment.
        text = "\n".join(line.split("#", 1)[0] for line in VALUES.read_text(encoding="utf-8").splitlines())
        self.assertNotIn("occupancy", text)
        self.assertNotIn("has_employee_slots_filled", text)

    def test_fully_staffed_sites_deliver_the_purchase(self):
        for count, purchase in itertools.product((1, 2, 5), (0.5, 50, 5000)):
            sites = [1.0] * count
            with self.subTest(count=count, purchase=purchase):
                self.assertAlmostEqual(delivered(self.values, purchase, sites, sites), purchase, places=2)

    def test_a_site_sized_before_it_hires_delivers_its_share_once_full(self):
        # The reported case: construction starts in a new state, the capital's site leaves, and the pulse
        # sizes the one new site before its first hiring. It used to deliver ten times the purchase.
        self.assertAlmostEqual(delivered(self.values, 50, [0.0], [1.0]), 50, places=2)
        # And beside established sites.
        self.assertAlmostEqual(delivered(self.values, 50, [1.0, 0.0, 0.0], [1.0, 1.0, 1.0]), 50, places=2)

    def test_the_sites_never_deliver_more_than_the_purchase(self):
        for count in (1, 2, 3):
            for at_pulse in itertools.product(STAFFINGS, repeat=count):
                for later in ([1.0] * count, list(at_pulse)):
                    with self.subTest(at_pulse=at_pulse, later=later):
                        self.assertLessEqual(delivered(self.values, 100, list(at_pulse), later), 100.01)

    def test_a_site_short_of_laborers_delivers_in_proportion(self):
        # Nothing makes up for a site that stays short: its share arrives by its staffing, and what does not
        # arrive is not paid for.
        self.assertAlmostEqual(delivered(self.values, 50, [0.5], [0.5]), 25, places=2)
        self.assertAlmostEqual(delivered(self.values, 50, [1.0, 0.5], [1.0, 0.5]), 37.5, places=2)

    def test_a_site_of_several_levels_counts_each_level(self):
        # The market places level-1 sites, but one kept from a direct game (an owner without Urbanization,
        # when the rule is switched back) has more: each level has its own laborers and delivers again.
        self.assertAlmostEqual(delivered(self.values, 50, [1.0], [1.0], levels=[7]), 50, places=2)
        self.assertAlmostEqual(delivered(self.values, 50, [1.0, 1.0], [1.0, 1.0], levels=[7, 1]), 50, places=2)
        self.assertAlmostEqual(delivered(self.values, 50, [1.0, 0.0], [1.0, 1.0], levels=[1, 12]), 50, places=2)

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

    def test_a_site_that_never_hires_gets_a_verdict(self):
        # The delivery check put its read off every week a site was under 10% staffed, so a site that never
        # hired, the failure the sizing rests on not happening, gave no line at all (review of #1770). The
        # weeks running are counted and the fourth is BROKEN, once a game.
        text = "\n".join(line.split("#", 1)[0] for line in EFFECTS.read_text(encoding="utf-8").lstrip("\ufeff").splitlines())
        start = text.index("te_cm_site_delivery_selfcheck = {")
        check = " ".join(text[start:text.index("\nte_construction_market_update_price_stabilizer", start)].split())
        self.assertIn("change_variable = { name = te_cm_chk_skips add = 1 } "
                      "if = { limit = { var:te_cm_chk_skips >= 4 } "
                      "set_global_variable = { name = te_cm_site_delivery_check_done value = yes } "
                      "debug_log = \"TE_SELF_CHECK BROKEN construction_site_unstaffed ", check)
        # Counted only while a site is under 10% staffed at the read, and the run ends when the country was
        # not armed the week before or a verdict was given.
        self.assertIn("else_if = { limit = { is_ai = yes any_scope_building = { is_building_type = "
                      "te_construction_market_site occupancy < 0.1 } }", check)
        self.assertGreaterEqual(check.count("remove_variable = te_cm_chk_skips"), 4)
        self.assertEqual(check.count("TE_SELF_CHECK BROKEN construction_site_unstaffed"), 1)

    def test_the_variable_outlives_the_effect(self):
        # The engine re-evaluates the multiplier expression on later ticks.
        self.assertNotIn("remove_variable = te_cm_capacity_mult", self.body)


if __name__ == "__main__":
    unittest.main()
