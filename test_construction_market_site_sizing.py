"""The weekly sizing of the Construction Sites delivers the purchase, and never many times it.

In a market game the week's construction purchase is delivered by the country's Construction Sites
(te_construction_market_site, level 1): the weekly pulse gives each a throughput modifier, and a site delivers
its throughput times its staffing. The government queue spends whatever the sites deliver and the treasury pays
for it, so sizing past the purchase bills the player for construction they did not order.

Three versions:

- Until 2026-11-13 each site got its share of the purchase divided by its own staffing, and a site under 10%
  staffed got ten times its share, each value written to one country variable that every site re-read between
  pulses (a Workshop report: construction costing millions on a purchase of 50,000).
- #1770 gave every site one throughput, the purchase over the country's site levels, and took each site to be
  full within its first week. A site in fact hires a tenth of its jobs a week, one laborer of ten, whatever its
  group's hiring rates say, and most sites are removed before they fill: a country whose construction moved
  between states got a fifth of its purchase (docs/testing/ai-economy-playtest.md, "First verdict").
- Now, as the Free Market Construction mod does it: once a site has its first week's hires, its state takes a
  modifier that cuts the group's jobs by 90%, to that one laborer, so the site is fully staffed from its first
  hire. The crew pass marks such a site's state, and the purchase is divided over the marked ("crewed") sites
  only; a site still waiting for its laborer gets no throughput. The values still read no staffing (owner,
  2026-11-13): they read the mark.

This runs the script's own text (common/script_values/te_construction_market_sector_placement_values.txt) with
the evaluator of test_construction_market_budget_step, extended with the one building iterator the chain uses,
and checks what the sites deliver against the purchase. The effects are checked as text.

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
PLACEMENT = ROOT / "common/scripted_effects/te_construction_market_sector_placement_effects.txt"
DIRECT = ROOT / "common/scripted_effects/te_construction_market_direct_effects.txt"
MODIFIERS = ROOT / "common/static_modifiers/te_construction_market_modifiers.txt"
MODIFIER_TYPES = ROOT / "common/modifier_type_definitions/mod_entity_modifier_types.txt"
PMS = ROOT / "common/production_methods/te_construction_market_pms.txt"
SITE = "te_construction_market_site"
THROUGHPUT = "te_construction_market_site_throughput"
CREW_MARK = "te_cm_site_crew"
CREW_MODIFIER = "te_construction_market_crew_modifier"
EMPLOYEE_MULT = "building_group_te_construction_market_bg_employee_mult"
# The base game's DEFAULT_MAX_HIRING_RATE: the share of its jobs a building may hire in a week. Measured on
# these sites, 2026-11-13: 119 of 168 sites under ten weeks old held exactly one laborer for each week.
HIRING_RATE = 0.1
# The staffing a site can show.
STAFFINGS = (0.0, 0.1, 0.3, 0.75, 1.0)


def code(path):
    """A script file's text without its comments."""
    return "\n".join(line.split("#", 1)[0] for line in path.read_text(encoding="utf-8-sig").splitlines())


def body_of(text, name):
    """The body of the top-level block `name = { ... }`, to its closing brace in column 0."""
    start = text.index("\n%s = {" % name) + 1
    return text[start:text.index("\n}", start)]


def flat(text):
    return " ".join(text.split())


def load_values():
    items, _ = parse_block(tokenize(VALUES.read_text(encoding="utf-8")), 0)
    return {key: value for key, _op, value in items}


class Evaluator:
    """Script values over a country whose sites have the given staffing (occupancy), level and crew mark."""

    def __init__(self, values, purchase, sites, levels=None, crewed=None):
        self.values = values
        self.purchase = purchase
        self.sites = sites
        self.levels = levels or [1] * len(sites)
        self.crewed = crewed if crewed is not None else [True] * len(sites)
        self.site = None  # the staffing of the building in scope, inside the iterator
        self.level = None  # its level
        self.mark = None  # whether its state carries the crew mark

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
            elif key == "state":
                # The building's state: the one thing read there is the crew mark.
                if self.mark is None:
                    raise AssertionError("state read outside a building's scope")
                for inner, _op, name in value:
                    if (inner, name) != ("has_variable", CREW_MARK):
                        raise AssertionError("the evaluator does not know %r = %r in a state" % (inner, name))
                    if not self.mark:
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
                for staffing, level, mark in zip(self.sites, self.levels, self.crewed):
                    self.site, self.level, self.mark = staffing, level, mark
                    if self.trigger(limit):
                        total = self.block([("value", "=", repr(total))] + rest)
                    self.site = self.level = self.mark = None
            else:
                raise AssertionError("the evaluator does not know %r" % key)
            total = round(total, 5)
        return total


def delivered(values, purchase, staffing, levels=None, crewed=None):
    """Points the sites deliver in the week after a pulse that found them with these crew marks. A crewed
    site carries the throughput modifier on top of the engine's 1; a site without a crew carries none
    (te_construction_market_apply_per_site_modifier). A site makes 1 point a level at full staff."""
    levels = levels or [1] * len(staffing)
    crewed = crewed if crewed is not None else [True] * len(staffing)
    throughput = Evaluator(values, purchase, staffing, levels, crewed).number(THROUGHPUT)
    return sum(((1 + throughput) if mark else 1) * share * level
               for share, level, mark in zip(staffing, levels, crewed))


class CrewTest(unittest.TestCase):
    """What makes a site fully staffed from its first hire."""

    def test_the_cut_leaves_exactly_the_first_weeks_hires(self):
        market = body_of(code(PMS), "pm_te_construction_market_base")
        jobs = float(re.search(r"level_scaled\s*=\s*\{\s*building_employment_laborers_add\s*=\s*([\d.]+)\s*\}",
                               market).group(1))
        modifier = body_of(code(MODIFIERS), CREW_MODIFIER)
        cut = float(re.search(r"%s\s*=\s*(-[\d.]+)" % EMPLOYEE_MULT, modifier).group(1))
        # A building hires a tenth of its jobs a week; the cut must leave exactly that many jobs, or the site
        # is under-staffed (too few cut) or holds more laborers than jobs (too many).
        self.assertAlmostEqual(jobs * (1 + cut), jobs * HIRING_RATE, places=6)
        self.assertGreaterEqual(jobs * HIRING_RATE, 1)  # at least one whole laborer to hire
        # The engine ignores a modifier name nothing registers.
        self.assertRegex(code(MODIFIER_TYPES), r"(?m)^%s\s*=\s*\{" % EMPLOYEE_MULT)

    def test_the_job_attractiveness_stays_on_the_market_method(self):
        pms = code(PMS)
        market = body_of(pms, "pm_te_construction_market_base")
        self.assertRegex(market, r"unscaled\s*=\s*\{\s*building_job_attractiveness_mult\s*=\s*5\s*\}")
        # Not the direct methods: there the site is a sector with a real workforce.
        self.assertEqual(pms.count("building_job_attractiveness_mult"), 1)

    def test_a_site_is_cut_only_at_its_first_hires(self):
        crew = flat(body_of(code(EFFECTS), "te_construction_market_site_crew"))
        # The cut, the mark and the self-check's wait go on together, for a site with no mark that holds at
        # most its first week's hires.
        self.assertIn("if = { limit = { occupancy <= 0.15 } state = { if = { limit = { NOT = { has_modifier = "
                      "%s } } add_modifier = { name = %s } } set_variable = { name = %s value = 1 }"
                      % (CREW_MODIFIER, CREW_MODIFIER, CREW_MARK), crew)
        self.assertEqual(crew.count("add_modifier"), 1)
        threshold = float(re.search(r"occupancy <= ([\d.]+)", crew).group(1))
        # One laborer in ten is 0.1; two in ten (a site from before the crew rule, with up to ten laborers on
        # its ten jobs) must not be cut: ten laborers on one job would deliver ten times the site's share
        # until the engine let nine go.
        self.assertGreater(threshold, HIRING_RATE)
        self.assertLess(threshold, 2 * HIRING_RATE)
        # Such a site is marked as crewed and keeps its jobs.
        self.assertIn("else = { state = { set_variable = { name = %s value = 3 } } }" % CREW_MARK, crew)

    def test_an_overstaffed_cut_site_gets_its_jobs_back(self):
        crew = flat(body_of(code(EFFECTS), "te_construction_market_site_crew"))
        self.assertIn("if = { limit = { occupancy > 1.05 state = { has_modifier = %s } } state = { "
                      "remove_modifier = %s set_variable = { name = %s value = 3 } } }"
                      % (CREW_MODIFIER, CREW_MODIFIER, CREW_MARK), crew)

    def test_a_site_with_no_laborer_loses_the_cut(self):
        # A cut site whose laborer left holds one job and may hire a tenth of a laborer a week: it would
        # never hire again. With no laborer the cut and the mark go, and it has its ten jobs back.
        crew = flat(body_of(code(EFFECTS), "te_construction_market_site_crew"))
        self.assertTrue(crew.startswith("te_construction_market_site_crew = { if = { limit = { occupancy > 0 }"))
        self.assertTrue(crew.endswith("else = { state = { te_construction_market_clear_crew = yes } }"))
        clear = flat(body_of(code(EFFECTS), "te_construction_market_clear_crew"))
        self.assertIn("remove_modifier = %s" % CREW_MODIFIER, clear)
        self.assertIn("remove_variable = %s " % CREW_MARK, clear + " ")

    def test_no_building_is_removed_or_made_by_the_crew_pass(self):
        # The other mod resets an over-staffed site by removing and re-creating it inside the walk over the
        # country's buildings. This one only moves a state's modifier and mark.
        for name in ("te_construction_market_site_crew", "te_construction_market_clear_crew",
                     "te_construction_market_apply_per_site_modifier"):
            body = body_of(code(EFFECTS), name)
            self.assertNotIn("remove_building", body, name)
            self.assertNotIn("create_building", body, name)

    def test_the_crew_goes_wherever_a_site_goes(self):
        # The modifier sits on the state and cuts the whole building group, so a state must not keep it
        # after its site: the next site there would start with one job, and in a direct game the site is a
        # sector in the same group, which the cut would run at full output on a tenth of its workers.
        placement = code(PLACEMENT)
        for match in re.finditer(r"remove_building = %s\b" % SITE, placement):
            self.assertRegex(placement[match.end():match.end() + 60], r"^\s*te_construction_market_clear_crew = yes")
        self.assertRegex(flat(body_of(placement, "te_construction_market_place_site")),
                         r"^te_construction_market_place_site = \{ te_construction_market_clear_crew = yes ")
        direct = code(DIRECT)
        self.assertRegex(flat(body_of(direct, "te_direct_construction_convert_state")),
                         r"^te_direct_construction_convert_state = \{ te_construction_market_clear_crew = yes ")
        # Every state of every country on the switch to direct construction, not only the converted ones.
        self.assertIn("every_scope_state = { te_construction_market_clear_crew = yes } every_scope_state = { "
                      "limit = { any_scope_building = {",
                      flat(body_of(direct, "te_direct_construction_convert_all")))
        # And the switch's self-check counts a state that kept it.
        self.assertIn("limit = { te_free_market_construction_off = yes has_modifier = %s } "
                      "change_global_variable = { name = te_dc_check_stale add = 1 }" % CREW_MODIFIER,
                      flat(body_of(direct, "te_direct_construction_switch_self_check")))


class SiteSizingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = load_values()

    def test_the_sizing_reads_no_staffing(self):
        # Owner, 2026-11-13: no scaling with employment. The values count the sites the crew pass has marked.
        text = code(VALUES)
        self.assertNotIn("occupancy", text)
        self.assertNotIn("has_employee_slots_filled", text)
        self.assertIn("has_variable = %s" % CREW_MARK, text)

    def test_crewed_sites_deliver_the_purchase(self):
        for count, purchase in itertools.product((1, 2, 5), (0.5, 50, 5000)):
            with self.subTest(count=count, purchase=purchase):
                self.assertAlmostEqual(delivered(self.values, purchase, [1.0] * count), purchase, places=2)

    def test_a_site_waiting_for_its_laborer_neither_thins_the_purchase_nor_adds_to_it(self):
        # Construction starts in two new states beside an established site. The crewed site carries the whole
        # purchase; the new ones are not counted and carry no modifier, so when each takes its first laborer
        # in the week (a tenth of its ten jobs) it adds a tenth of a point, not a tenth of a share.
        for waiting in (0.0, HIRING_RATE):
            with self.subTest(waiting=waiting):
                got = delivered(self.values, 50, [1.0, waiting, waiting], crewed=[True, False, False])
                self.assertGreaterEqual(got, 50 - 0.01)
                self.assertLessEqual(got, 50 + 2 * HIRING_RATE + 0.01)

    def test_no_crewed_site_delivers_next_to_nothing(self):
        # A country whose only site has just moved to a new state: nothing until the new site's first hire
        # and the pulse after it. Not delivered, so not paid for.
        self.assertEqual(Evaluator(self.values, 50, [0.0], crewed=[False]).number(THROUGHPUT), 0)
        self.assertLessEqual(delivered(self.values, 50, [HIRING_RATE], crewed=[False]), HIRING_RATE + 0.01)

    def test_the_sites_never_deliver_more_than_the_purchase(self):
        # Whatever the staffing and the marks: the crewed sites together give at most the purchase, and a
        # site without a crew at most its own level's one point.
        for count in (1, 2, 3):
            for staffing in itertools.product(STAFFINGS, repeat=count):
                for crewed in itertools.product((True, False), repeat=count):
                    with self.subTest(staffing=staffing, crewed=crewed):
                        loose = sum(share for share, mark in zip(staffing, crewed) if not mark)
                        self.assertLessEqual(delivered(self.values, 100, list(staffing), crewed=list(crewed)),
                                             100 + loose + 0.01)

    def test_a_crewed_site_short_of_laborers_delivers_in_proportion(self):
        # A site from before the crew rule keeps its ten jobs and is counted as crewed while it fills
        # (te_construction_market_site_crew): its share arrives by its staffing, and what does not arrive is
        # not paid for. Never more.
        self.assertAlmostEqual(delivered(self.values, 50, [0.5]), 25, places=2)
        self.assertAlmostEqual(delivered(self.values, 50, [1.0, 0.5]), 37.5, places=2)

    def test_a_site_of_several_levels_counts_each_level(self):
        # The market places level-1 sites, but one kept from a direct game (an owner without Urbanization,
        # when the rule is switched back) has more: each level has its own laborer and delivers again.
        self.assertAlmostEqual(delivered(self.values, 50, [1.0], levels=[7]), 50, places=2)
        self.assertAlmostEqual(delivered(self.values, 50, [1.0, 1.0], levels=[7, 1]), 50, places=2)
        # A twelve-level site still waiting for its laborers is left out of the count.
        self.assertAlmostEqual(delivered(self.values, 50, [1.0, 0.0], levels=[1, 12], crewed=[True, False]), 50,
                               places=2)

    def test_no_site_and_no_purchase(self):
        self.assertEqual(Evaluator(self.values, 50, []).number(THROUGHPUT), 0)
        # No purchase: throughput -100%, so the sites deliver, and buy, nothing.
        self.assertEqual(delivered(self.values, 0, [1.0]), 0)


class SizingEffectTest(unittest.TestCase):
    def setUp(self):
        self.text = code(EFFECTS)
        self.body = body_of(self.text, "te_construction_market_apply_per_site_modifier")

    def test_the_crews_come_before_the_count_and_the_count_before_the_modifier(self):
        crews = self.body.index("te_construction_market_site_crew = yes")
        write = self.body.index("te_cm_capacity_mult")
        add = self.body.index("add_modifier")
        self.assertLess(crews, write)
        self.assertLess(write, add)

    def test_every_site_reads_one_country_value(self):
        # One value, written once before the walk that adds the modifier: a per-site value in a shared
        # country variable let every site re-read the last site's between pulses.
        self.assertEqual(len(re.findall(r"name\s*=\s*te_cm_capacity_mult", self.body)), 1)
        self.assertLess(self.body.index("te_cm_capacity_mult"), self.body.rindex("every_scope_building"))
        self.assertRegex(self.body, r"value\s*=\s*%s\b" % THROUGHPUT)
        self.assertRegex(self.body, r"multiplier\s*=\s*owner\.var:te_cm_capacity_mult")

    def test_only_a_crewed_site_carries_the_modifier(self):
        # The sites the divisor counts and the sites that carry the modifier are the same ones. The other mod
        # gives every site the multiplier and divides by the staffed ones, so one staffed site beside five
        # new ones that each hire mid-week delivers 150%.
        self.assertIn("remove_modifier = te_construction_market_capacity_modifier if = { limit = { state = { "
                      "has_variable = %s } } add_modifier = { name = te_construction_market_capacity_modifier"
                      % CREW_MARK, flat(self.body))
        self.assertEqual(self.body.count("add_modifier"), 1)

    def test_the_variable_outlives_the_effect(self):
        # The engine re-evaluates the multiplier expression on later ticks.
        self.assertNotIn("remove_variable = te_cm_capacity_mult", self.body)

    def test_the_delivery_check_reads_before_the_sizing_and_arms_after_it(self):
        pulse = flat(body_of(self.text, "te_construction_market_country_update_data"))
        self.assertRegex(pulse, r"te_cm_site_delivery_selfcheck = yes .*"
                                r"te_construction_market_apply_per_site_modifier = yes .*"
                                r"te_cm_site_delivery_selfcheck_arm = yes")
        read = flat(body_of(self.text, "te_cm_site_delivery_selfcheck"))
        # Read only when the crewed levels are what they were when the purchase was stored: a crewed site
        # that went with its construction makes a week that decides nothing.
        self.assertIn("te_construction_market_site_levels = var:te_cm_chk_levels", read)
        arm = flat(body_of(self.text, "te_cm_site_delivery_selfcheck_arm"))
        self.assertIn("if = { limit = { te_construction_market_site_levels >= 1 } set_variable = { name = "
                      "te_cm_chk_target value = te_construction_market_total_use_target } set_variable = { name = "
                      "te_cm_chk_levels value = te_construction_market_site_levels }", arm)
        # A marker of its own: a game that had the first version's verdict gets this check too.
        self.assertNotIn("te_cm_site_delivery_check_done", self.text)
        self.assertEqual(self.text.count("TE_SELF_CHECK OK construction_site_delivery"), 1)
        self.assertEqual(self.text.count("TE_SELF_CHECK BROKEN construction_site_delivery"), 1)

    def test_a_country_whose_sites_never_get_a_crew_gets_a_verdict(self):
        # With no crewed site nothing is delivered and the delivery check never arms, so that failure would
        # give no line at all. The weeks running are counted and the fourth is BROKEN, once a game.
        arm = flat(body_of(self.text, "te_cm_site_delivery_selfcheck_arm"))
        self.assertIn("change_variable = { name = te_cm_chk_skips add = 1 } "
                      "if = { limit = { var:te_cm_chk_skips >= 4 } "
                      "if = { limit = { NOT = { has_global_variable = te_cm_site_unstaffed_check_done } } "
                      "set_global_variable = { name = te_cm_site_unstaffed_check_done value = yes } "
                      "debug_log = \"TE_SELF_CHECK BROKEN construction_site_unstaffed ", arm)
        # The run ends when a site has a crew, and when the country no longer qualifies.
        self.assertGreaterEqual(arm.count("remove_variable = te_cm_chk_skips"), 3)
        self.assertEqual(self.text.count("TE_SELF_CHECK BROKEN construction_site_unstaffed"), 1)

    def test_the_crew_check_reads_a_site_cut_at_a_tenth_after_a_wait(self):
        crew = flat(body_of(self.text, "te_construction_market_site_crew"))
        # Marked 1 at the cut, read once the five-day mark has run out, then marked 2 whatever it read.
        self.assertIn("set_variable = { name = te_cm_site_crew_fresh value = 1 days = 5 }", crew)
        self.assertIn("limit = { state = { var:%s ?= 1 NOT = { has_variable = te_cm_site_crew_fresh } } }"
                      % CREW_MARK, crew)
        self.assertIn("occupancy >= 0.9 }", crew)
        self.assertIn("occupancy <= 0.25 }", crew)
        self.assertEqual(crew.count("TE_SELF_CHECK OK construction_site_crew"), 1)
        self.assertEqual(crew.count("TE_SELF_CHECK BROKEN construction_site_crew"), 1)
        self.assertIn("state = { set_variable = { name = %s value = 2 } }" % CREW_MARK, crew)


if __name__ == "__main__":
    unittest.main()
